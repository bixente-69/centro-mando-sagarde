# -*- coding: utf-8 -*-
"""Integración de «Personal en obra» con el entorno real (paso 06).

Todo sobre árboles temporales y con datos inventados: ninguna prueba toca una obra real. Se
comprueba lo que NO debe ocurrir tanto como lo que sí: un fallo de personal no tumba un panel,
regenerar una sola obra no encoge el estado, y el .bat se detiene si la auditoría dice «error».
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_BASE = Path(__file__).resolve().parent.parent  # _SISTEMA INFORME SAGARDE IA
_REPO = _BASE.parent.parent
_SCRIPTS = _REPO / "_SISTEMA" / "MOTOR" / "scripts"
for ruta in (str(_BASE), str(_SCRIPTS)):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

import personal_integracion as pi  # noqa: E402
import personal_obra as po  # noqa: E402

HAY_NODE = shutil.which("node") is not None

# Dos obras abiertas de juguete: las pruebas no dependen del registro real.
ABIERTAS = {"obraa": "2026 OBRA A", "obrab": "2026 OBRA B"}
NOMBRES = {"obraa": "2026 OBRA A", "obrab": "2026 OBRA B"}


def lote(obra, *jornadas, **extra):
    d = {"tipo": "lote_personal", "version": 1, "obra": obra, "jornadas": list(jornadas)}
    d.update(extra)
    return d


def jornada(ambito, fecha, *presentes, **extra):
    d = {"ambito": ambito, "fecha": fecha,
         "presentes": [{"nombre": n, "horas": h, "extra": e} for n, h, e in presentes]}
    d.update(extra)
    return d


L_A = lote("obraa",
           jornada("vivienda", "2026-10-19", ("Mikel", 7.5, 0), ("Txomin", 7.5, 0)),
           jornada("vivienda", "2026-10-20", ("Mikel", 9.5, 2)),
           jornada("garaje", "2026-10-20", ("Andoni", 7.5, 0)))
L_B = lote("obrab", jornada("vivienda", "2026-10-21", ("Mikel", 7.5, 0)))


class Base(unittest.TestCase):
    """Un árbol temporal `SAGARDE OBRAS ABIERTAS` con los ficheros declarados y dos obras."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.top = Path(self._tmp.name)
        self.raiz = self.top / "SAGARDE OBRAS ABIERTAS"
        self.motor = self.raiz / "_SISTEMA INFORME SAGARDE IA"
        self.motor.mkdir(parents=True)
        for nombre in pi.FICHEROS_DECLARADOS:
            shutil.copy(_BASE / nombre, self.motor / nombre)
        for carpeta in ABIERTAS.values():
            (self.raiz / carpeta / "INFORME SAGARDE IA").mkdir(parents=True)
        p = mock.patch.object(pi, "obras_registro", return_value=(dict(ABIERTAS), dict(NOMBRES)))
        p.start()
        self.addCleanup(p.stop)

    def ingerir(self, l, hoy="2026-10-23"):
        r = po.ingerir_lote(l, str(self.raiz), ABIERTAS, hoy, escribir=True, ahora="2026-10-23T22:00:00+02:00")
        self.assertTrue(r["ok"] and r["escrito"], r)

    def ruta_obra(self, oid, nombre="personal_obra.json"):
        return self.raiz / ABIERTAS[oid] / "INFORME SAGARDE IA" / nombre

    def estado(self):
        texto = (self.motor / "personal_estado.js").read_text(encoding="utf-8")
        return json.loads(texto[len("window.SAGARDE_PERSONAL = "):].rstrip().rstrip(";"))

    def codigos(self, incidencias, nivel=None):
        return sorted({i["codigo"] for i in incidencias if nivel is None or i["nivel"] == nivel})


class TestFilasParaPanel(Base):
    def obra(self, oid="obraa"):
        return {"id": oid, "nombre": NOMBRES[oid], "carpeta_obra": ABIERTAS[oid]}

    def test_sin_personal_obra_json_no_hay_filas_ni_aviso(self):
        self.assertEqual(([], None), pi.filas_para_panel(self.obra(), self.raiz))

    def test_con_datos_devuelve_las_filas_planas_con_el_nombre_canonico(self):
        self.ingerir(L_A)
        filas, aviso = pi.filas_para_panel(self.obra(), self.raiz)
        self.assertIsNone(aviso)
        self.assertEqual(4, len(filas))
        self.assertIn({"fecha": "2026-10-20", "ambito": "vivienda", "nombre": "Mikel", "horas": 9.5, "extra": 2}, filas)

    def test_un_json_ilegible_no_lanza_y_avisa(self):
        self.ruta_obra("obraa").write_text("{esto no es json", encoding="utf-8")
        filas, aviso = pi.filas_para_panel(self.obra(), self.raiz)
        self.assertEqual([], filas)
        self.assertTrue(aviso)

    def test_un_id_que_no_esta_en_el_catalogo_no_lanza_y_avisa(self):
        self.ingerir(L_A)
        (self.motor / "personal_catalogo.json").write_text('{"version":1,"trabajadores":[]}', encoding="utf-8")
        filas, aviso = pi.filas_para_panel(self.obra(), self.raiz)
        self.assertEqual([], filas)
        self.assertIn("KeyError", aviso)


class TestExportarEstado(Base):
    def test_sin_datos_en_ninguna_obra_no_crea_el_fichero(self):
        r = pi.exportar_estado_real(self.raiz)
        self.assertFalse(r["escrito"])
        self.assertFalse((self.motor / "personal_estado.js").exists())
        self.assertIn("sin datos", r["motivo"])

    def test_escribe_con_todas_las_obras_del_registro_aunque_solo_una_tenga_datos(self):
        pi.iniciar_obra("obrab", self.raiz, escribir=True)
        self.ingerir(L_A)
        r = pi.exportar_estado_real(self.raiz)
        self.assertTrue(r["escrito"])
        e = self.estado()
        self.assertEqual({"obraa", "obrab"}, set(e["obras"]))
        self.assertEqual(4, len(e["obras"]["obraa"]["jornadas"]))
        self.assertEqual([], e["obras"]["obrab"]["jornadas"])
        self.assertFalse(e["obras"]["obraa"]["cerrada"])
        self.assertEqual({"obraa": 4, "obrab": 0}, r["obras"])

    def test_una_segunda_exportacion_sin_cambios_no_toca_el_fichero(self):
        self.ingerir(L_A)
        pi.exportar_estado_real(self.raiz, ahora="2026-10-23T22:00:00+02:00")
        antes = (self.motor / "personal_estado.js").read_bytes()
        r = pi.exportar_estado_real(self.raiz, ahora="2030-01-01T00:00:00+01:00")
        self.assertFalse(r["escrito"])
        self.assertEqual("sin cambios", r["motivo"])
        self.assertEqual(antes, (self.motor / "personal_estado.js").read_bytes())

    def test_un_dato_nuevo_si_reescribe(self):
        self.ingerir(L_A)
        pi.exportar_estado_real(self.raiz, ahora="2026-10-23T22:00:00+02:00")
        self.ingerir(lote("obraa", jornada("vivienda", "2026-10-21", ("Mikel", 7.5, 0))))
        r = pi.exportar_estado_real(self.raiz, ahora="2026-10-24T08:00:00+02:00")
        self.assertTrue(r["escrito"])
        self.assertEqual("2026-10-24T08:00:00+02:00", self.estado()["generado"])
        self.assertEqual(5, len(self.estado()["obras"]["obraa"]["jornadas"]))

    def test_una_obra_archivada_sigue_contando_marcada_como_cerrada(self):
        self.ingerir(L_A)
        archivada = self.top / "SAGARDE (OLD)" / "OBRAS CERRADAS" / "2025 OBRA VIEJA" / "INFORME SAGARDE IA"
        archivada.mkdir(parents=True)
        # Una obra archivada con sus datos, escritos con el mismo módulo que usa el resto.
        po.ingerir_lote(lote("vieja", jornada("vivienda", "2025-03-03", ("Mikel", 7.5, 0))), str(self.raiz),
                        {"vieja": os.path.join(os.pardir, "SAGARDE (OLD)", "OBRAS CERRADAS", "2025 OBRA VIEJA")},
                        "2026-10-23", escribir=True)
        pi.exportar_estado_real(self.raiz)
        e = self.estado()
        self.assertTrue(e["obras"]["vieja"]["cerrada"])
        self.assertEqual("2025 OBRA VIEJA", e["obras"]["vieja"]["nombre"])
        self.assertEqual(1, len(e["obras"]["vieja"]["jornadas"]))
        self.assertFalse(e["obras"]["obraa"]["cerrada"])

    def test_cerrar_una_obra_conserva_su_fichero_y_el_ranking_la_sigue_contando(self):
        """cerrar_obra.py mueve la carpeta entera: personal_obra.json viaja con ella."""
        import cerrar_obra
        self.ingerir(L_A)
        obra = {"id": "obraa", "nombre": "2026 OBRA A", "carpeta_obra": ABIERTAS["obraa"]}
        destino = cerrar_obra.mover_a_cerradas(self.top, obra)
        self.assertTrue((destino / "INFORME SAGARDE IA" / "personal_obra.json").is_file())
        with mock.patch.object(pi, "obras_registro",
                               return_value=({"obrab": ABIERTAS["obrab"]}, {"obrab": NOMBRES["obrab"]})):
            pi.exportar_estado_real(self.raiz)
        e = self.estado()
        self.assertTrue(e["obras"]["obraa"]["cerrada"])
        self.assertEqual(4, len(e["obras"]["obraa"]["jornadas"]))

    def test_fusionar_mira_tambien_las_obras_archivadas(self):
        """Dos personas que coinciden el mismo día en una obra cerrada no se pueden fusionar."""
        carpeta = "2025 OBRA VIEJA"
        po.ingerir_lote(lote("vieja", jornada("vivienda", "2025-03-03", ("Mikel", 7.5, 0), ("Mikell", 7.5, 0))),
                        str(self.raiz), {"vieja": os.path.join(os.pardir, "SAGARDE (OLD)", "OBRAS CERRADAS", carpeta)},
                        "2026-10-23", escribir=True)
        cat = po.cargar_catalogo(str(self.raiz))
        ids = {t["nombre"]: t["id"] for t in cat["trabajadores"]}
        r = po.fusionar(str(self.raiz), ids["Mikell"], ids["Mikel"])
        self.assertFalse(r["ok"])
        self.assertEqual("conflicto_en_jornada", r["error"])


class TestIniciarObra(Base):
    def test_crea_un_fichero_valido_y_sin_jornadas(self):
        r = pi.iniciar_obra("obraa", self.raiz, escribir=True)
        self.assertTrue(r["creada"])
        self.assertEqual([], po.cargar_obra(str(self.raiz), ABIERTAS, "obraa")["jornadas"])
        self.assertEqual([], po.comprobar(str(self.raiz), ABIERTAS))

    def test_simulacion_no_escribe(self):
        r = pi.iniciar_obra("obraa", self.raiz)
        self.assertFalse(r["creada"])
        self.assertFalse(self.ruta_obra("obraa").exists())

    def test_no_pisa_una_obra_que_ya_tiene_datos(self):
        self.ingerir(L_A)
        antes = self.ruta_obra("obraa").read_bytes()
        r = pi.iniciar_obra("obraa", self.raiz, escribir=True)
        self.assertFalse(r["creada"])
        self.assertEqual(antes, self.ruta_obra("obraa").read_bytes())

    def test_una_obra_que_no_es_del_registro_se_rechaza(self):
        with self.assertRaises(ValueError):
            pi.iniciar_obra("no_existe", self.raiz, escribir=True)

    def test_la_obra_iniciada_aparece_en_el_estado_para_la_tablet(self):
        pi.iniciar_obra("obraa", self.raiz, escribir=True)
        pi.exportar_estado_real(self.raiz)
        self.assertEqual([], self.estado()["obras"]["obraa"]["jornadas"])


class TestAuditar(Base):
    def editar_obra(self, oid, f):
        d = json.loads(self.ruta_obra(oid).read_text(encoding="utf-8"))
        f(d)
        self.ruta_obra(oid).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    def test_sin_datos_de_personal_esta_dormida(self):
        (self.motor / "personal_calculo.js").unlink()
        self.assertEqual([], pi.auditar(self.raiz))

    @unittest.skipUnless(HAY_NODE, "falta node")
    def test_datos_validos_no_dan_ninguna_incidencia(self):
        self.ingerir(L_A)
        self.ingerir(L_B)
        self.assertEqual([], pi.auditar(self.raiz))

    def test_una_clave_fuera_del_esquema_es_un_error(self):
        self.ingerir(L_A)
        self.editar_obra("obraa", lambda d: d["jornadas"][0].update(telefono_movil="x"))
        self.assertIn("PERSONAL_ESQUEMA", self.codigos(pi.auditar(self.raiz), "error"))

    def test_un_dni_en_las_notas_es_un_error_y_no_se_repite_en_el_mensaje(self):
        self.ingerir(L_A)
        self.editar_obra("obraa", lambda d: d["jornadas"][0].update(notas="Mikel 12345678Z"))
        inc = [i for i in pi.auditar(self.raiz) if i["codigo"] == "PERSONAL_DATO_PRIVADO"]
        self.assertEqual(1, len(inc))
        self.assertNotIn("12345678", inc[0]["mensaje"])

    def test_telefono_correo_y_nie_son_errores(self):
        self.ingerir(L_A)
        for texto, tipo in (("llamar al 612 345 678", "telefono"), ("+34 944 123 456", "telefono"),
                            ("mikel@correo.es", "correo"), ("X1234567L", "NIE")):
            with self.subTest(texto=texto):
                self.editar_obra("obraa", lambda d: d["jornadas"][0].update(notas=texto))
                inc = [i for i in pi.auditar(self.raiz) if i["codigo"] == "PERSONAL_DATO_PRIVADO"]
                self.assertTrue(inc and tipo in inc[0]["mensaje"], (texto, inc))

    def test_los_datos_normales_no_parecen_privados(self):
        """Fechas, horas, ids y marcas de hora no son teléfonos ni DNI."""
        self.ingerir(L_A)
        self.editar_obra("obraa", lambda d: d["jornadas"][0].update(notas="Llueve. Hormigón 2026-10-19 07:30 T0001"))
        self.assertNotIn("PERSONAL_DATO_PRIVADO", self.codigos(pi.auditar(self.raiz)))

    def test_falta_un_fichero_declarado(self):
        self.ingerir(L_A)
        (self.motor / "personal_sagarde.html").unlink()
        inc = [i for i in pi.auditar(self.raiz) if i["codigo"] == "PERSONAL_FICHERO_FALTA"]
        self.assertEqual(1, len(inc))
        self.assertIn("personal_sagarde.html", inc[0]["mensaje"])

    def test_una_traza_dañada_es_un_error(self):
        self.ingerir(L_A)
        with open(self.ruta_obra("obraa", "personal_jornadas.jsonl"), "ab") as f:
            f.write(b'{"ts": "x", "clave_rara": 1}\n')
        self.assertIn("PERSONAL_TRAZA", self.codigos(pi.auditar(self.raiz), "error"))

    @unittest.skipUnless(HAY_NODE, "falta node")
    def test_el_doble_calculo_salta_si_el_calculo_de_pantalla_se_desvia(self):
        self.ingerir(L_A)
        js = self.motor / "personal_calculo.js"
        texto = js.read_text(encoding="utf-8")
        self.assertIn("totalHoras += horasVal;", texto)
        js.write_text(texto.replace("totalHoras += horasVal;", "totalHoras += horasVal + 1;"), encoding="utf-8")
        self.assertIn("PERSONAL_DOBLE_CALCULO", self.codigos(pi.auditar(self.raiz), "error"))

    def test_unas_horas_fuera_de_rango_son_un_error_de_esquema(self):
        """30 h en un día: P1 las rechazaría al ingerir; si llegan a mano, la auditoría las ve."""
        self.ingerir(L_A)
        self.editar_obra("obraa", lambda d: d["jornadas"][0]["presentes"][0].update(horas=30))
        self.assertIn("PERSONAL_ESQUEMA", self.codigos(pi.auditar(self.raiz), "error"))

    def test_comparar_senala_cada_tipo_de_diferencia(self):
        """El comparador de totales, aislado: horas, días, un trabajador que falta y filas no contadas."""
        esperado = {"horas": 15.0, "extra": 2.0, "dias": 2, "trabajadores": 1,
                    "por_trabajador": {"Mikel": {"horas": 15.0, "extra": 2.0, "dias": 2}}}
        js = {"total": {"horas": 15.0, "extra": 2.0, "dias": 2, "trabajadores": 1},
              "avisos": {"filasSinHoras": 0, "filasInvalidas": 0},
              "trabajadores": {"Mikel": {"horas": 15.0, "extra": 2.0, "dias": 2}}}
        self.assertEqual([], pi._comparar(esperado, js))
        self.assertEqual([], pi._comparar(None, {"total": None, "avisos": {}, "trabajadores": {}}))
        casos = {
            "horas": dict(js, total=dict(js["total"], horas=16.0)),
            "dias": dict(js, total=dict(js["total"], dias=3)),
            "trabajadores": dict(js, total=dict(js["total"], trabajadores=2)),
            "no aparece": dict(js, trabajadores={}),
            "· JS": dict(js, trabajadores={"Mikel": {"horas": 14.0, "extra": 3.0, "dias": 2}}),  # el total cuadra, la persona no
            "no cuenta": dict(js, avisos={"filasSinHoras": 0, "filasInvalidas": 1}),
            "Python": {"total": None, "avisos": {}, "trabajadores": {}},
            "no devolvió": None,
        }
        for clave, calculado in casos.items():
            with self.subTest(clave=clave):
                self.assertTrue([d for d in pi._comparar(esperado, calculado) if clave in d], clave)

    def test_sin_node_avisa_y_no_calla(self):
        self.ingerir(L_A)
        with mock.patch.object(pi.shutil, "which", return_value=None):
            inc = pi.auditar(self.raiz)
        self.assertEqual(["PERSONAL_NODE_AUSENTE"], self.codigos(inc))
        self.assertEqual("warning", inc[0]["nivel"])

    def test_si_node_falla_avisa_y_no_calla(self):
        self.ingerir(L_A)
        (self.motor / "personal_calculo.js").write_text("esto no es javascript (", encoding="utf-8")
        if not HAY_NODE:
            self.skipTest("falta node")
        self.assertEqual(["PERSONAL_NODE_FALLA"], self.codigos(pi.auditar(self.raiz)))

    def test_el_auditor_del_bat_usa_estas_comprobaciones_y_cuenta_los_errores(self):
        import auditor_sagarde
        self.ingerir(L_A)
        self.editar_obra("obraa", lambda d: d["jornadas"][0].update(notas="correo mikel@x.es"))
        with mock.patch.object(auditor_sagarde, "ROOT", self.top), \
                mock.patch.object(auditor_sagarde, "DIAGNOSTICO_JSON", self.top / "d.json"), \
                mock.patch.object(auditor_sagarde, "audit_obras_abiertas", return_value=[]), \
                mock.patch.object(auditor_sagarde, "audit_mantenimientos", return_value=[]), \
                mock.patch.object(auditor_sagarde, "audit_materiales", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()) as salida:
            resultado = auditor_sagarde.run_audit()
        self.assertEqual(1, resultado["totales"]["errors"])
        self.assertIn("NO SE PUBLICA", salida.getvalue())


class TestHooksDelMotor(unittest.TestCase):
    """generar_todos.py y regenerar_obra.py: un fallo de personal nunca tumba lo demás."""

    @classmethod
    def setUpClass(cls):
        import generar_todos
        cls.gt = generar_todos

    def test_un_fallo_inesperado_con_personal_no_tumba_el_panel(self):
        obra = {"id": "x", "nombre": "2026 X", "carpeta_obra": "2026 X"}
        with mock.patch.object(pi, "filas_para_panel", side_effect=RuntimeError("boom")), \
                contextlib.redirect_stdout(io.StringIO()) as salida:
            self.assertEqual([], self.gt._personal_para_panel(obra))
        self.assertIn("[AVISO PERSONAL]", salida.getvalue())
        self.assertIn("boom", salida.getvalue())

    def test_un_aviso_de_datos_ilegibles_se_imprime_y_devuelve_vacio(self):
        obra = {"id": "x", "nombre": "2026 X", "carpeta_obra": "2026 X"}
        with mock.patch.object(pi, "filas_para_panel", return_value=([], "ValueError: mal")), \
                contextlib.redirect_stdout(io.StringIO()) as salida:
            self.assertEqual([], self.gt._personal_para_panel(obra))
        self.assertIn("2026 X", salida.getvalue())

    def test_con_datos_pasa_las_filas_y_lo_dice(self):
        obra = {"id": "x", "nombre": "2026 X", "carpeta_obra": "2026 X"}
        filas = [{"fecha": "2026-10-19", "ambito": "vivienda", "nombre": "Mikel", "horas": 7.5, "extra": 0}]
        with mock.patch.object(pi, "filas_para_panel", return_value=(filas, None)), \
                contextlib.redirect_stdout(io.StringIO()) as salida:
            self.assertEqual(filas, self.gt._personal_para_panel(obra))
        self.assertIn("[PERSONAL]", salida.getvalue())

    def test_un_fallo_al_exportar_el_estado_avisa_y_no_lanza(self):
        with mock.patch.object(pi, "exportar_estado_real", side_effect=OSError("disco lleno")), \
                contextlib.redirect_stdout(io.StringIO()) as salida:
            self.assertIsNone(self.gt.exportar_personal_estado())
        self.assertIn("disco lleno", salida.getvalue())

    @staticmethod
    def _funcion(fuente, nombre):
        import ast
        return next(n for n in ast.parse(fuente).body if isinstance(n, ast.FunctionDef) and n.name == nombre)

    def test_main_obtiene_las_filas_del_ayudante_y_se_las_pasa_al_panel(self):
        """Lo declarado tiene que producir efecto: si main() calculase `personal` de otra forma
        (p. ej. `personal = []`) o no se lo pasase a generar_panel, todo lo anterior sería letra muerta."""
        import ast
        main = self._funcion((_BASE / "generar_todos.py").read_text(encoding="utf-8"), "main")
        origen = [n for n in ast.walk(main) if isinstance(n, ast.Assign)
                  and [t.id for t in n.targets if isinstance(t, ast.Name)] == ["personal"]]
        self.assertEqual(1, len(origen), "main() debe asignar `personal` una sola vez")
        self.assertIsInstance(origen[0].value, ast.Call)
        self.assertEqual("_personal_para_panel", origen[0].value.func.id)
        llamadas = [n for n in ast.walk(main) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute) and n.func.attr == "generar_panel"]
        self.assertEqual(1, len(llamadas))
        kw = {k.arg: k.value for k in llamadas[0].keywords}
        self.assertIsInstance(kw.get("personal"), ast.Name)
        self.assertEqual("personal", kw["personal"].id)
        self.assertEqual("id", kw["personal_obra_id"].slice.value)  # obra['id']

    def test_main_exporta_el_estado_despues_de_publicar_el_registro(self):
        import ast
        main = self._funcion((_BASE / "generar_todos.py").read_text(encoding="utf-8"), "main")
        orden = [s.value.func.id for s in main.body
                 if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Name)]
        self.assertIn("exportar_personal_estado", orden)
        self.assertLess(orden.index("publicar_registro_revisiones"), orden.index("exportar_personal_estado"))

    def test_regenerar_una_obra_no_exporta_el_estado_y_lo_restaura(self):
        import regenerar_obra
        visto = {}

        def falso_main(hacer_pdf=False):
            visto["durante"] = regenerar_obra.gt.exportar_personal_estado
            regenerar_obra.gt.generar_index([])
            return []

        original = regenerar_obra.gt.exportar_personal_estado
        with mock.patch.object(regenerar_obra.gt, "main", falso_main), \
                mock.patch.object(regenerar_obra, "_cargar_cache", return_value={}), \
                mock.patch.object(regenerar_obra, "_guardar_cache"), \
                contextlib.redirect_stdout(io.StringIO()):
            regenerar_obra.regenerar_una_obra(regenerar_obra.gt.OBRAS[0]["id"])
        self.assertIsNot(original, visto["durante"])
        self.assertIsNone(visto["durante"]())
        self.assertIs(original, regenerar_obra.gt.exportar_personal_estado)

    def test_finalizar_exporta_el_estado_con_la_funcion_real(self):
        import ast
        fuente = (_SCRIPTS / "regenerar_obra.py").read_text(encoding="utf-8")
        fin = self._funcion(fuente, "finalizar")
        llamadas = [n.func.id for n in ast.walk(fin) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertIn("_exportar_personal_estado_original", llamadas)
        asignaciones = [n for n in ast.parse(fuente).body if isinstance(n, ast.Assign)
                        and [t.id for t in n.targets if isinstance(t, ast.Name)] == ["_exportar_personal_estado_original"]]
        self.assertEqual("exportar_personal_estado", asignaciones[0].value.attr)

    def test_el_auditor_devuelve_3_con_errores_y_0_sin_ellos(self):
        import auditor_sagarde
        for errores, esperado in ((1, 3), (0, 0)):
            with self.subTest(errores=errores),                     mock.patch.object(auditor_sagarde, "run_audit", return_value={"totales": {"errors": errores}}):
                self.assertEqual(esperado, auditor_sagarde.main())


class TestLineaDeComandos(Base):
    def correr(self, *argv, entrada=None):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            if entrada is None:
                codigo = pi.main(list(argv))
            else:
                with mock.patch("builtins.input", return_value=entrada):
                    codigo = pi.main(list(argv))
        return codigo, salida.getvalue()

    def escribir_lote(self, l):
        ruta = self.top / "lote.json"
        ruta.write_text(json.dumps(l), encoding="utf-8")
        return str(ruta)

    def test_ingerir_con_confirmacion_escribe_exporta_y_no_publica(self):
        fichero = self.escribir_lote(L_A)
        codigo, texto = self.correr("ingerir", fichero, "--raiz", str(self.raiz), "--hoy", "2026-10-23",
                                    "--sin-panel", entrada="s")
        self.assertEqual(0, codigo, texto)
        self.assertIn("SIMULACI", texto)
        self.assertTrue(self.ruta_obra("obraa").is_file())
        self.assertEqual(4, len(self.estado()["obras"]["obraa"]["jornadas"]))
        self.assertIn("NO se ha publicado nada", texto)

    def test_ingerir_regenera_el_panel_de_la_obra_solo_si_hay_datos_nuevos(self):
        """El .bat regenera la obra del lote; un lote repetido no cambia nada y no regenera."""
        scripts = self.top / "_SISTEMA" / "MOTOR" / "scripts"
        scripts.mkdir(parents=True)
        marca = self.top / "regenerada.txt"
        (scripts / "regenerar_obra.py").write_text(
            "import sys\nopen(%r, 'a').write(sys.argv[1] + '\\n')\n" % str(marca), encoding="utf-8")
        fichero = self.escribir_lote(L_A)
        args = ("ingerir", fichero, "--raiz", str(self.raiz), "--hoy", "2026-10-23", "--si")
        self.assertEqual(0, self.correr(*args)[0])
        self.assertEqual("obraa\n", marca.read_text(encoding="utf-8"))
        marca.unlink()
        codigo, texto = self.correr(*args)
        self.assertEqual(0, codigo)
        self.assertFalse(marca.exists(), "un lote ya ingerido no debe regenerar nada")
        self.assertIn("No hay datos nuevos", texto)

    def test_ingerir_sin_confirmar_no_escribe_nada(self):
        fichero = self.escribir_lote(L_A)
        codigo, texto = self.correr("ingerir", fichero, "--raiz", str(self.raiz), "--hoy", "2026-10-23",
                                    "--sin-panel", entrada="n")
        self.assertEqual(3, codigo)
        self.assertFalse(self.ruta_obra("obraa").exists())
        self.assertFalse((self.motor / "personal_estado.js").exists())

    def test_ingerir_un_fichero_que_no_es_json_no_escribe(self):
        ruta = self.top / "roto.json"
        ruta.write_text("{no", encoding="utf-8")
        codigo, _ = self.correr("ingerir", str(ruta), "--raiz", str(self.raiz), "--si", "--sin-panel")
        self.assertEqual(1, codigo)
        self.assertFalse((self.motor / "personal_estado.js").exists())

    def test_auditar_devuelve_2_si_hay_errores(self):
        self.ingerir(L_A)
        (self.motor / "personal_sagarde.html").unlink()
        codigo, texto = self.correr("auditar", "--raiz", str(self.raiz))
        self.assertEqual(2, codigo)
        self.assertIn("PERSONAL_FICHERO_FALTA", texto)

    def test_el_exportar_estado_de_personal_obra_py_usa_los_nombres_y_las_cerradas_reales(self):
        """La CLI de P1 por sí sola exportaba sin nombres de obra ni marca `cerrada`."""
        self.ingerir(L_A)
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = po.main(["exportar-estado", "--raiz", str(self.raiz), "--escribir"])
        self.assertEqual(0, codigo)
        self.assertEqual("2026 OBRA A", self.estado()["obras"]["obraa"]["nombre"])


@unittest.skipUnless(os.name == "nt", "el .bat solo corre en Windows")
class TestElBatSeDetieneConErrores(unittest.TestCase):
    """El paso 0 de Actualizar_Sagarde.bat: código 3 de la auditoría = no se sigue ni se publica."""

    def _correr(self, codigo):
        bat = (_REPO / "Actualizar_Sagarde.bat").read_text(encoding="utf-8").splitlines()
        i0 = next(i for i, l in enumerate(bat) if l.startswith("echo [0/6]"))
        i1 = next(i for i, l in enumerate(bat) if l.startswith("echo [1/6]"))
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "_SISTEMA" / "MOTOR" / "scripts").mkdir(parents=True)
            (tmp / "_SISTEMA" / "MOTOR" / "scripts" / "auditor_sagarde.py").write_text(
                "import os, sys\nsys.exit(int(os.environ['CODIGO_FALSO']))\n", encoding="utf-8")
            prueba = tmp / "prueba.bat"
            prueba.write_text("\r\n".join(
                ["@echo off", "setlocal", f'cd /d "{tmp}"', f'set "PY={sys.executable}"']
                + bat[i0:i1] + ["echo LLEGO_AL_PASO_1", "exit /b 0", ""]), encoding="utf-8")
            p = subprocess.run(["cmd", "/c", str(prueba)], capture_output=True, stdin=subprocess.DEVNULL,
                               env=dict(os.environ, CODIGO_FALSO=str(codigo)), timeout=60)
            return p.returncode, p.stdout.decode("cp850", "replace")

    def test_codigo_3_detiene_el_bat_antes_de_publicar(self):
        retorno, texto = self._correr(3)
        self.assertEqual(1, retorno)
        self.assertNotIn("LLEGO_AL_PASO_1", texto)
        self.assertIn("NO se ha publicado nada", texto)

    def test_sin_errores_el_bat_sigue(self):
        for codigo in (0, 1, 2):
            with self.subTest(codigo=codigo):
                retorno, texto = self._correr(codigo)
                self.assertEqual(0, retorno)
                self.assertIn("LLEGO_AL_PASO_1", texto)


if __name__ == "__main__":
    unittest.main()
