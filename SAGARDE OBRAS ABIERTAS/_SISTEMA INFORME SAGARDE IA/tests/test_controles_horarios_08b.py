# -*- coding: utf-8 -*-
"""Paso 08b de «Personal en obra»: los CONTROL HORARIO entran en el entorno como entra una revisión.

Se prueba el enganche en tres sitios (todo sobre árboles temporales y con datos INVENTADOS; ninguna prueba toca una
obra real): el puente `personal_integracion` (vista previa, aplicación, textos en llano, auditor), «actualiza la
obra» (`actualizar_obra.py`: guarda, `--aceptar-controles N`, informe H) y `generar_todos.py` (el .bat).
"""
import ast
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_personal_integracion import ABIERTAS, NOMBRES, Base, L_A, pi, po  # noqa: E402

import lector_control_horario as lector  # noqa: E402

_BASE = Path(__file__).resolve().parent.parent  # _SISTEMA INFORME SAGARDE IA
_SCRIPTS = _BASE.parent.parent / "_SISTEMA" / "MOTOR" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import actualizar_obra as ao  # noqa: E402

NOM = "CONTROL HORARIO 2026 OBRA A %s.json"
HOY = "2026-10-25"
AHORA = "2026-10-25T22:00:00+02:00"
PALABRAS = re.compile(r"\b(exportar|exportad\w*|importar|importad\w*|lotes?|ingerir|ingesta|json|pendientes?|alta|altas|"
                      r"simulaci\w+|estado|base de datos)\b", re.I)


def jor(ambito, fecha, *presentes, **extra):
    d = {"ambito": ambito, "fecha": fecha,
         "presentes": [{"nombre": n, "horas": h, "extra": 0} for n, h in presentes]}
    d.update(extra)
    return d


def control(*jornadas, obra="obraa", **extra):
    d = {"tipo": "lote_personal", "version": 1, "obra": obra, "jornadas": list(jornadas)}
    d.update(extra)
    return d


LIMPIO = control(jor("vivienda", "2026-10-22", ("Mikel", 7.5), ("Txomin", 8)))
DUDOSO = control(jor("vivienda", "2026-10-23", ("Mikell", 7.5)))        # se parece a Mikel
SUMA_ALTA = control(jor("vivienda", "2026-10-23", ("Mikel", 13)))       # > 12 h


class BaseControles(Base):
    def setUp(self):
        super().setUp()
        self.rev = self.raiz / ABIERTAS["obraa"] / "REVISIONES"
        self.rev.mkdir(parents=True)

    def fichero(self, fecha, contenido, nombre=None):
        ruta = self.rev / (nombre or NOM % fecha)
        if isinstance(contenido, (dict, list)):
            contenido = json.dumps(contenido, ensure_ascii=False)
        ruta.write_bytes(contenido if isinstance(contenido, bytes) else contenido.encode("utf-8"))
        return ruta

    def hashes(self):
        out = {}
        for d, _, fs in os.walk(self.raiz):
            for f in fs:
                p = Path(d) / f
                out[str(p.relative_to(self.raiz)).replace(os.sep, "/")] = hashlib.sha256(p.read_bytes()).hexdigest()
        return out

    def vista(self, **kw):
        return pi.controles_horarios("obraa", self.raiz, hoy=HOY, ahora=AHORA, **kw)

    def texto(self, res):
        return "\n".join(pi.lineas_controles(res))


class TestControlesHorarios(BaseControles):
    def test_sin_controles_dice_que_no_hay_y_no_escribe_nada(self):
        antes = self.hashes()
        res = self.vista()
        self.assertEqual((0, ["No hay controles horarios nuevos."]), (res["n_ficheros"], pi.lineas_controles(res)))
        self.assertEqual(antes, self.hashes())

    def test_carpeta_revisiones_inexistente_tampoco_calla(self):
        res = pi.controles_horarios("obrab", self.raiz, hoy=HOY)
        self.assertEqual(["No hay controles horarios nuevos."], pi.lineas_controles(res))

    def test_una_obra_que_no_es_del_registro_se_rechaza(self):
        with self.assertRaises(ValueError):
            pi.controles_horarios("no_existe", self.raiz)
        with self.assertRaises(ValueError):
            pi.carpeta_revisiones("no_existe", self.raiz)

    def test_vista_previa_de_un_control_limpio_no_escribe_y_lo_cuenta_en_llano(self):
        self.fichero("23102026", LIMPIO)
        antes = self.hashes()
        res = self.vista()
        self.assertEqual(antes, self.hashes(), "la vista previa no escribe NADA")
        self.assertEqual(({"listo": 1, "ya_aplicado": 0, "a_revisar": 0, "rechazado": 0, "aplicado": 0}, 0),
                         (res["cuenta"], res["avisos_a_revisar"]))
        t = self.texto(res)
        self.assertIn("se aplicaría", t)
        self.assertIn("personas nuevas: Mikel, Txomin", t)
        self.assertIn("Horas de la obra: antes sin jornadas; quedarían 15,5 h en 1 día con 2 personas.", t)

    def test_aplicar_escribe_deja_el_sha_y_la_segunda_vez_dice_que_ya_estaba(self):
        ruta = self.fichero("23102026", LIMPIO)
        res = self.vista(escribir=True)
        self.assertEqual(1, res["cuenta"]["aplicado"])
        self.assertIn("APLICADO", self.texto(res))
        self.assertIn("después 15,5 h en 1 día con 2 personas", self.texto(res))
        self.assertEqual({hashlib.sha256(ruta.read_bytes()).hexdigest()},
                         po.shas_recibidos(str(self.raiz), ABIERTAS, "obraa"))
        self.assertEqual(2, len(po.aplanar(str(self.raiz), ABIERTAS, "obraa")))
        despues = self.hashes()
        res2 = self.vista(escribir=True)
        self.assertEqual(["No hay controles horarios nuevos (1 fichero ya estaba aplicado)."], pi.lineas_controles(res2))
        self.assertEqual(despues, self.hashes(), "aplicar dos veces no cambia ni un byte")

    def test_un_control_dudoso_no_se_aplica_sin_aceptar_y_dice_cuantos_avisos_son(self):
        self.ingerir(L_A)
        self.fichero("23102026", DUDOSO)
        antes = self.hashes()
        res = self.vista(escribir=True)
        self.assertEqual(antes, self.hashes(), "un dudoso no se aplica")
        self.assertEqual(1, res["cuenta"]["a_revisar"])
        self.assertEqual(1, res["avisos_a_revisar"])
        self.assertTrue(res["frena"])
        t = self.texto(res)
        self.assertIn("HAY QUE MIRARLO, no se aplica", t)
        self.assertIn("! Se parecen: «Mikell» y «Mikel». ¿Es la misma persona? (viviendas del 23/10)", t)

    def test_aceptando_se_aplica_con_su_visto_bueno(self):
        self.ingerir(L_A)
        self.fichero("23102026", SUMA_ALTA)
        res = self.vista(escribir=True, aceptar=True)
        self.assertEqual((1, 0), (res["cuenta"]["aplicado"], res["cuenta"]["a_revisar"]))
        self.assertIn("APLICADO (con tu visto bueno)", self.texto(res))
        self.assertEqual(13, [f["horas"] for f in po.aplanar(str(self.raiz), ABIERTAS, "obraa")
                              if f["fecha"] == "2026-10-23"][0])

    def test_la_cifra_de_la_guarda_cuenta_avisos_y_no_ficheros(self):
        self.ingerir(L_A)
        # una jornada que sustituye a otra distinta Y un nombre parecido Y más de 12 h: 3 avisos en 1 fichero
        self.fichero("23102026", control(jor("vivienda", "2026-10-20", ("Mikell", 13), ("Txomin", 7.5))))
        res = self.vista()
        self.assertEqual(1, res["cuenta"]["a_revisar"])
        self.assertEqual(3, res["avisos_a_revisar"])

    def test_un_fichero_que_no_vale_se_dice_y_no_frena_a_los_demas(self):
        self.fichero("22102026", b"{no")
        self.fichero("23102026", LIMPIO)
        self.fichero("24102026", control(jor("vivienda", "2026-10-22", ("Mikel", 7.5)), obra="obrab"))
        res = self.vista(escribir=True)
        self.assertEqual((1, 2), (res["cuenta"]["aplicado"], res["cuenta"]["rechazado"]))
        t = self.texto(res)
        self.assertIn("NO VALE, no se aplica: No se puede leer este fichero", t)
        self.assertIn("es de «2026 OBRA B», no de esta obra: no se aplica para no mezclar obras", t)

    def test_un_fichero_ya_aplicado_no_se_repite_a_si_mismo_pero_una_copia_se_explica(self):
        self.fichero("23102026", LIMPIO)
        self.vista(escribir=True)
        self.fichero("25102026", LIMPIO)                      # los mismos bytes con otro nombre: ya aplicado
        rafa = control(jor("vivienda", "2026-10-25", ("Rafa", 7.5)))
        self.fichero("26102026", rafa)                        # dos ficheros iguales y nuevos a la vez
        self.fichero("27102026", rafa)
        lineas = pi.lineas_controles(self.vista())
        propia = next(l for l in lineas if NOM % "25102026" in l)
        self.assertTrue(propia.endswith("— ya estaba aplicado"), propia)
        copia = next(l for l in lineas if NOM % "27102026" in l)
        self.assertTrue(copia.endswith("ya estaba aplicado: Es una copia de «%s», que ya se aplica: no se hace nada."
                                       % (NOM % "26102026")), copia)

    def test_una_jornada_que_no_vale_se_enseña_aunque_el_resto_del_fichero_entre(self):
        self.fichero("23102026", control(jor("vivienda", "2026-10-22", ("Mikel", 7.5)),
                                         jor("garaje", "2026-10-22", ("Andoni", 99))))
        lineas = pi.lineas_controles(self.vista())
        self.assertIn("      ✗ no vale (garajes del 22/10): Hay unas horas que no valen (deben estar entre 0 y 24).", lineas)
        self.assertIn("1 jornada que no vale", "\n".join(lineas))

    def test_los_textos_no_llevan_palabras_de_programador_ni_codigos(self):
        self.ingerir(L_A)
        self.fichero("20102026", control(jor("vivienda", "2026-10-30", ("Mikell", 13)), jor("garaje", "2026-10-21", ("Andoni", 99))))
        self.fichero("21102026", b"{no")
        self.fichero("22102026", control(jor("vivienda", "2026-10-22", ("12345678Z", 7.5))))
        self.fichero("23102026", LIMPIO)
        for escribir in (False, True):
            # el nombre del fichero lleva «.json» (es el nombre real que ve Bixente en su carpeta): no cuenta
            texto = self.texto(self.vista(escribir=escribir)).replace(".json", "")
            self.assertIsNone(PALABRAS.search(texto), PALABRAS.search(texto) and PALABRAS.search(texto).group(0))
            self.assertNotRegex(texto, r"[a-z]+_[a-z]+")
            self.assertNotIn("12345678Z", texto)

    def test_muchos_avisos_informativos_se_recortan_pero_los_que_obligan_a_mirar_salen_todos(self):
        self.ingerir(L_A)
        po.ingerir_lote(control(jor("vivienda", "2026-10-21", ("Andoni", 7.5)), renombres=[{"de": "Mikel", "a": "Mikel B"}]),
                        str(self.raiz), ABIERTAS, "2026-10-23", escribir=True)
        # 12 jornadas con el nombre antiguo: 12 avisos informativos distintos (uno por fecha)
        viejas = [jor("vivienda", "2026-10-%02d" % d, ("Mikel", 7.5)) for d in range(1, 13)]
        self.fichero("23102026", control(*viejas))
        lineas = pi.lineas_controles(self.vista())
        self.assertEqual(8, sum(1 for l in lineas if l.startswith("      · ") and "es un nombre antiguo" in l))
        self.assertTrue(any(l == "      · … y 4 avisos más" for l in lineas), lineas)
        # los que obligan a mirar (aquí 20 de «más de 12 horas») se enseñan todos: se acepta una cifra tras leerlos
        self.fichero("24102026", control(*[jor("vivienda", "2026-09-%02d" % d, ("Andoni", 13)) for d in range(1, 21)]))
        res = self.vista()
        self.assertEqual(20, res["avisos_a_revisar"])
        self.assertEqual(20, sum(1 for l in pi.lineas_controles(res) if l.startswith("      ! Andoni suma más de 12 horas")))


class TestAplicarControlesLimpios(BaseControles):
    """Lo que hace generar_todos.py (y con él el .bat) para cada obra antes de construir su panel."""

    def aplicar(self, oid="obraa"):
        return pi.aplicar_controles_limpios(oid, self.raiz, hoy=HOY, ahora=AHORA)

    def test_sin_controles_imprime_una_linea_nunca_silencio(self):
        r = self.aplicar()
        self.assertEqual(["  [PERSONAL] sin controles horarios en 2026 OBRA A"], r["lineas"])
        self.assertEqual((0, 0), (r["aplicados"], r["avisos"]))

    def test_aplica_los_limpios_y_lo_dice(self):
        self.fichero("23102026", LIMPIO)
        r = self.aplicar()
        self.assertEqual(1, r["aplicados"])
        self.assertEqual("  [PERSONAL] 2026 OBRA A: control horario aplicado «%s» (1 jornada de viviendas, 2 personas nuevas)"
                         % (NOM % "23102026"), r["lineas"][0])
        self.assertEqual(2, len(po.aplanar(str(self.raiz), ABIERTAS, "obraa")))

    def test_los_dudosos_no_se_aplican_y_salen_avisados_con_el_nombre_del_fichero(self):
        self.ingerir(L_A)
        self.fichero("23102026", DUDOSO)
        antes = self.hashes()
        r = self.aplicar()
        self.assertEqual(antes, self.hashes())
        self.assertEqual((0, 1), (r["aplicados"], r["avisos"]))
        self.assertTrue(r["lineas"][0].startswith("  [AVISO PERSONAL] 2026 OBRA A: el control horario «%s» NO se aplica" % (NOM % "23102026")))
        self.assertIn("Dile «actualiza la obra»", r["lineas"][0])

    def test_un_fichero_malo_no_impide_aplicar_los_buenos(self):
        self.fichero("22102026", b"{no")
        self.fichero("23102026", LIMPIO)
        r = self.aplicar()
        self.assertEqual((1, 1), (r["aplicados"], r["avisos"]))
        self.assertTrue(any("NO vale y no se aplica" in l for l in r["lineas"]))

    def test_todo_ya_aplicado_dice_nada_nuevo(self):
        self.fichero("23102026", LIMPIO)
        self.aplicar()
        r = self.aplicar()
        self.assertEqual(["  [PERSONAL] controles horarios de 2026 OBRA A: nada nuevo (1 fichero ya aplicado)"], r["lineas"])

    def test_solo_toca_la_obra_pedida(self):
        self.fichero("23102026", LIMPIO)
        carpeta_b = self.raiz / ABIERTAS["obrab"] / "REVISIONES"
        carpeta_b.mkdir(parents=True)
        (carpeta_b / (NOM % "23102026")).write_text(json.dumps(control(jor("vivienda", "2026-10-22", ("Rafa", 7.5)), obra="obrab")))
        self.aplicar("obraa")
        self.assertFalse(self.ruta_obra("obrab").exists())
        self.assertEqual([], po.aplanar(str(self.raiz), ABIERTAS, "obrab"))


class TestAuditorDeControles(BaseControles):
    def inc(self):
        return [i for i in pi.auditar(self.raiz) if i["codigo"].startswith("PERSONAL_CONTROL")]

    def test_sin_controles_no_dice_nada(self):
        self.assertEqual([], pi.auditar(self.raiz))

    def test_un_aviso_por_cada_control_sin_aplicar_aunque_no_haya_datos_de_personal(self):
        """Antes de aplicar nada no existe ningún personal_obra.json: el auditor tiene que verlo igualmente."""
        self.fichero("23102026", LIMPIO)
        inc = self.inc()
        self.assertEqual(["PERSONAL_CONTROL_SIN_APLICAR"], [i["codigo"] for i in inc])
        self.assertEqual(("warning", "2026 OBRA A", "Personal"), (inc[0]["nivel"], inc[0]["obra"], inc[0]["area"]))
        self.assertIn(NOM % "23102026", inc[0]["mensaje"])

    def test_dudoso_y_rechazado_tienen_su_propio_codigo_y_ninguno_frena_el_bat(self):
        self.ingerir(L_A)
        self.fichero("22102026", b"{no")
        self.fichero("23102026", DUDOSO)
        inc = pi.auditar(self.raiz)
        codigos = sorted(i["codigo"] for i in inc if i["codigo"].startswith("PERSONAL_CONTROL"))
        self.assertEqual(["PERSONAL_CONTROL_A_REVISAR", "PERSONAL_CONTROL_RECHAZADO"], codigos)
        self.assertEqual(set(), {i["nivel"] for i in inc} - {"warning"}, "avisos, no errores: el .bat sigue")

    def test_un_control_ya_aplicado_deja_de_avisar(self):
        self.fichero("23102026", LIMPIO)
        pi.aplicar_controles_limpios("obraa", self.raiz, hoy=HOY, ahora=AHORA)
        self.assertEqual([], self.inc())

    def test_si_no_se_puede_comprobar_una_obra_lo_dice(self):
        self.fichero("23102026", LIMPIO)
        with mock.patch.object(lector, "analizar", side_effect=RuntimeError("boom")):
            inc = self.inc()
        self.assertEqual(["PERSONAL_CONTROL_NO_COMPROBADO"], [i["codigo"] for i in inc])
        self.assertIn("boom", inc[0]["mensaje"])

    def test_el_auditor_del_bat_cuenta_los_avisos_y_no_los_errores(self):
        import auditor_sagarde
        self.fichero("23102026", LIMPIO)
        with mock.patch.object(auditor_sagarde, "ROOT", self.top), \
                mock.patch.object(auditor_sagarde, "DIAGNOSTICO_JSON", self.top / "d.json"), \
                mock.patch.object(auditor_sagarde, "audit_obras_abiertas", return_value=[]), \
                mock.patch.object(auditor_sagarde, "audit_mantenimientos", return_value=[]), \
                mock.patch.object(auditor_sagarde, "audit_materiales", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()) as salida:
            resultado = auditor_sagarde.run_audit()
        self.assertEqual((0, 1), (resultado["totales"]["errors"], resultado["totales"]["warnings"]))
        self.assertIn("PERSONAL", salida.getvalue() + json.dumps(resultado["issues"]))


class TestEstadoDeLaTablet(BaseControles):
    def test_ofrece_todas_las_obras_abiertas_aunque_ninguna_tenga_datos(self):
        r = pi.exportar_estado_real(self.raiz)
        self.assertTrue(r["escrito"])
        self.assertEqual({"obraa", "obrab"}, set(self.estado()["obras"]))

    def test_el_primer_control_de_una_obra_nueva_aparece_sin_alta_manual(self):
        pi.exportar_estado_real(self.raiz)
        self.fichero("23102026", LIMPIO)
        pi.aplicar_controles_limpios("obraa", self.raiz, hoy=HOY, ahora=AHORA)
        pi.exportar_estado_real(self.raiz)
        e = self.estado()
        self.assertEqual(2, len(e["obras"]["obraa"]["jornadas"]))
        self.assertEqual("2026-10-22", e["obras"]["obraa"]["ultima"]["vivienda"]["fecha"])
        self.assertEqual([], e["obras"]["obrab"]["jornadas"])
        self.assertEqual(sorted(p["nombre"] for p in e["catalogo"]), ["Mikel", "Txomin"])

    def test_no_se_reescribe_si_no_hay_cambios_ni_encoge_al_regenerar_una_obra(self):
        pi.exportar_estado_real(self.raiz, ahora="2026-10-23T22:00:00+02:00")
        antes = (self.motor / "personal_estado.js").read_bytes()
        r = pi.exportar_estado_real(self.raiz, ahora="2030-01-01T00:00:00+01:00")
        self.assertEqual(("sin cambios", False), (r["motivo"], r["escrito"]))
        self.assertEqual(antes, (self.motor / "personal_estado.js").read_bytes())
        # el registro entero manda aunque se regenere una sola obra
        with mock.patch.object(pi, "obras_registro", return_value=(dict(ABIERTAS), dict(NOMBRES))):
            pi.exportar_estado_real(self.raiz)
        self.assertEqual({"obraa", "obrab"}, set(self.estado()["obras"]))


class TestCaminoViejoRetirado(unittest.TestCase):
    def test_el_bat_viejo_no_existe_ni_se_versiona(self):
        self.assertFalse((_BASE / "Ingerir_Personal.bat").exists())
        gitignore = (_BASE.parent.parent / ".gitignore")
        if gitignore.is_file():
            self.assertNotIn("Ingerir_Personal", gitignore.read_text(encoding="utf-8"))

    def test_los_comandos_viejos_ya_no_estan_en_ningun_modulo(self):
        for nombre in ("iniciar_obra", "cmd_ingerir"):
            self.assertFalse(hasattr(pi, nombre), nombre)
        fuente = (_BASE / "personal_integracion.py").read_text(encoding="utf-8")
        self.assertNotIn("Ingerir_Personal", fuente)

    def test_ningun_fichero_del_motor_cita_el_camino_viejo(self):
        for ruta in list(_BASE.glob("*.py")) + list(_SCRIPTS.glob("*.py")):
            texto = ruta.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("Ingerir_Personal", texto, ruta.name)


# ─── «actualiza la obra» ──────────────────────────────────────────────────────────────────────────
def _controles_falsos(listo=0, a_revisar=0, rechazado=0, ya=0, avisos=0, aplicado=0):
    return {"obra": "x", "carpeta": "", "n_ficheros": listo + a_revisar + rechazado + ya + aplicado,
            "aplicado": False, "ficheros": [],
            "cuenta": {"listo": listo, "a_revisar": a_revisar, "rechazado": rechazado, "ya_aplicado": ya, "aplicado": aplicado},
            "avisos_a_revisar": avisos, "frena": bool(a_revisar or rechazado), "antes": None, "despues": None}


class TestGuardaDeControles(unittest.TestCase):
    def test_sin_avisos_no_hay_guarda(self):
        self.assertEqual((False, []), ao._guarda_controles(_controles_falsos(listo=2), []))
        self.assertEqual((False, []), ao._guarda_controles(None, [5]))

    def test_con_avisos_la_guarda_para_y_dice_el_numero(self):
        aceptar, lineas = ao._guarda_controles(_controles_falsos(a_revisar=1, avisos=3), [])
        self.assertFalse(aceptar)
        self.assertEqual("REVISION HUMANA OBLIGATORIA: CONTROL HORARIO", lineas[0])
        self.assertIn("Hay 3 avisos", lineas[1])
        self.assertEqual("Para aceptarlos, tras leerlos: --aceptar-controles 3", lineas[-1])

    def test_solo_se_libera_con_la_cifra_exacta(self):
        c = _controles_falsos(a_revisar=2, avisos=4)
        self.assertEqual((True, []), ao._guarda_controles(c, [4]))
        self.assertEqual((True, []), ao._guarda_controles(c, [1, 4]))
        for mala in ([3], [5], [0], [1]):
            aceptar, lineas = ao._guarda_controles(c, mala)
            self.assertFalse(aceptar, mala)
            self.assertIn("no coincide con la de la guarda (4): la guarda sigue", lineas[-1])

    def test_un_aviso_singular(self):
        _, lineas = ao._guarda_controles(_controles_falsos(a_revisar=1, avisos=1), [])
        self.assertIn("Hay 1 aviso en", lineas[1])

    def test_controles_aplicables_cuenta_los_listos_y_los_aceptados(self):
        c = _controles_falsos(listo=2, a_revisar=1, avisos=1)
        self.assertEqual(2, ao._controles_aplicables(c, False))
        self.assertEqual(3, ao._controles_aplicables(c, True))
        self.assertEqual(0, ao._controles_aplicables(None, True))


class TestShaPersonalOtrasObras(unittest.TestCase):
    def test_sin_datos_con_datos_y_cambios(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            obras = [{"id": "a", "carpeta_obra": "A"}, {"id": "b", "carpeta_obra": "B"}, {"id": "c", "carpeta_obra": "C"}]
            (Path(tmp) / "B" / "INFORME SAGARDE IA").mkdir(parents=True)
            self.assertEqual({"b": "SIN DATOS", "c": "SIN DATOS"}, ao.sha_personal_otras_obras(obras, "a", tmp))
            f = Path(tmp) / "B" / "INFORME SAGARDE IA" / "personal_obra.json"
            f.write_text("{}", encoding="utf-8")
            uno = ao.sha_personal_otras_obras(obras, "a", tmp)
            self.assertNotEqual("SIN DATOS", uno["b"])
            self.assertEqual("SIN DATOS", uno["c"])
            self.assertNotIn("a", uno)
            f.write_text('{"x": 1}', encoding="utf-8")
            sin_traza = ao.sha_personal_otras_obras(obras, "a", tmp)["b"]
            self.assertNotEqual(uno["b"], sin_traza)
            (f.parent / "personal_jornadas.jsonl").write_text("{}\n", encoding="utf-8")
            self.assertNotEqual(sin_traza, ao.sha_personal_otras_obras(obras, "a", tmp)["b"], "la traza también cuenta")


class TestSeccionH(unittest.TestCase):
    def llamar(self, controles, error=None, antes=None, despues=None, personas=(None, None)):
        antes = {"b": "x" * 64} if antes is None else antes
        despues = {"b": "x" * 64} if despues is None else despues
        return ao._seccion_h(controles, error, antes, despues, *personas)

    def test_sin_controles_lo_dice_y_las_demas_obras_son_identicas(self):
        with mock.patch.object(ao, "_lineas_controles", return_value=["No hay controles horarios nuevos."]):
            lineas, motivos = self.llamar(_controles_falsos())
        self.assertEqual("H) CONTROL HORARIO", lineas[0])
        self.assertIn("  No hay controles horarios nuevos.", lineas)
        self.assertTrue(any("[IDENTICO]" in l for l in lineas))
        self.assertEqual([], motivos)

    def test_un_cambio_en_otra_obra_es_un_error_de_efecto_colateral(self):
        with mock.patch.object(ao, "_lineas_controles", return_value=["x"]):
            lineas, motivos = self.llamar(_controles_falsos(), despues={"b": "y" * 64})
        self.assertTrue(any("[CAMBIO]" in l for l in lineas))
        self.assertEqual(1, len(motivos))
        self.assertTrue(motivos[0].startswith("ERROR (efecto colateral) en los datos de personal de: b"))

    def test_una_obra_que_aparece_o_desaparece_tambien_cuenta(self):
        with mock.patch.object(ao, "_lineas_controles", return_value=["x"]):
            _, motivos = self.llamar(_controles_falsos(), despues={"b": "x" * 64, "c": "z"})
            self.assertEqual(1, len(motivos))
            _, motivos = self.llamar(_controles_falsos(), despues={})
            self.assertEqual(1, len(motivos))

    def test_los_rechazados_dejan_el_informe_en_revisar(self):
        with mock.patch.object(ao, "_lineas_controles", return_value=["x"]):
            _, motivos = self.llamar(_controles_falsos(rechazado=2))
        self.assertEqual(["2 controles horarios NO valen y no se han aplicado (ver H)"], motivos)
        with mock.patch.object(ao, "_lineas_controles", return_value=["x"]):
            _, motivos = self.llamar(_controles_falsos(rechazado=1))
        self.assertEqual(["1 control horario NO vale y no se han aplicado (ver H)"], motivos)

    def test_un_error_al_revisar_se_cuenta(self):
        lineas, motivos = self.llamar(None, error="No se pudieron revisar los controles horarios: boom")
        self.assertIn("  ERROR: No se pudieron revisar los controles horarios: boom", lineas)
        self.assertEqual(["No se pudieron revisar los controles horarios: boom"], motivos)

    def test_las_personas_de_la_lista(self):
        with mock.patch.object(ao, "_lineas_controles", return_value=["x"]):
            lineas, _ = self.llamar(_controles_falsos(), personas=(3, 5))
        self.assertIn("  Personas en la lista de trabajadores: antes 3; después 5.", lineas)


class TestMainConControles(unittest.TestCase):
    """El flujo de main(): qué se simula, qué se escribe y con qué código sale."""

    OBRA = {"id": "obraa", "nombre": "2026 OBRA A", "carpeta_obra": "2026 OBRA A", "subtitulo": ""}

    def correr(self, argv, controles, error=None, hojas=False):
        deteccion = ao.DeteccionHojas()
        if hojas:
            deteccion.vivienda.append(ao.Hoja(Path("h.html"), "10/10/2026", "x", "vivienda", "a" * 64))
        salida = io.StringIO()
        with mock.patch.object(ao, "_obra_por_id", return_value=self.OBRA), \
                mock.patch.object(ao, "_detectar_actual",
                                  return_value=(Path("/no/existe"), None, None, deteccion)), \
                mock.patch.object(Path, "is_dir", return_value=True), \
                mock.patch.object(ao, "_revisar_controles", return_value=(controles, error)), \
                mock.patch.object(ao, "_lineas_controles", return_value=["  (lineas de control)"]), \
                mock.patch.object(ao, "_simular", return_value=0) as simular, \
                mock.patch.object(ao, "_escribir", return_value=0) as escribir, \
                contextlib.redirect_stdout(salida):
            codigo = ao.main(argv)
        return codigo, salida.getvalue(), simular, escribir

    def test_sin_hojas_ni_controles_dice_las_dos_cosas_y_sale_con_0(self):
        codigo, texto, simular, escribir = self.correr(["obraa"], _controles_falsos())
        self.assertEqual(0, codigo)
        self.assertIn("NO hay hojas nuevas.", texto)
        self.assertIn("CONTROL HORARIO", texto)
        simular.assert_not_called()
        escribir.assert_not_called()

    def test_sin_hojas_y_con_escribir_tampoco_calla(self):
        codigo, texto, _, escribir = self.correr(["obraa", "--escribir"], _controles_falsos())
        self.assertEqual(0, codigo)
        self.assertIn("NO hay hojas nuevas.", texto)
        self.assertIn("CONTROL HORARIO", texto)
        escribir.assert_not_called()

    def test_un_control_limpio_en_vista_previa_no_escribe_y_sale_con_0(self):
        codigo, texto, simular, escribir = self.correr(["obraa"], _controles_falsos(listo=1))
        self.assertEqual(0, codigo)
        self.assertIn("(lineas de control)", texto)
        escribir.assert_not_called()

    def test_un_control_limpio_con_escribir_llama_a_escribir_aunque_no_haya_hojas(self):
        codigo, _, _, escribir = self.correr(["obraa", "--escribir"], _controles_falsos(listo=1))
        self.assertEqual(0, codigo)
        escribir.assert_called_once()
        args = escribir.call_args.args
        self.assertEqual((False,), (args[5],), "aceptar_controles")
        self.assertEqual(_controles_falsos(listo=1), args[3], "main() le pasa a _escribir los controles revisados")
        self.assertIsNone(args[4])

    def test_la_guarda_sale_con_3_en_vista_previa_y_en_escritura_y_no_escribe_nada(self):
        c = _controles_falsos(a_revisar=1, avisos=2)
        codigo, texto, _, escribir = self.correr(["obraa"], c)
        self.assertEqual(3, codigo)
        self.assertIn("--aceptar-controles 2", texto)
        codigo, texto, _, escribir = self.correr(["obraa", "--escribir"], c, hojas=True)
        self.assertEqual(3, codigo)
        self.assertIn("No se ha escrito nada.", texto)
        escribir.assert_not_called()

    def test_la_vista_previa_con_guarda_no_repite_la_lista_de_controles(self):
        _, texto, _, _ = self.correr(["obraa"], _controles_falsos(a_revisar=1, avisos=2))
        self.assertEqual(1, texto.count("(lineas de control)"))
        self.assertNotIn("CONTROL HORARIO", texto.splitlines())

    def test_la_guarda_tambien_para_las_hojas_cuando_se_escribe(self):
        _, _, _, escribir = self.correr(["obraa", "--escribir"], _controles_falsos(a_revisar=1, avisos=1), hojas=True)
        escribir.assert_not_called()

    def test_con_la_cifra_exacta_se_libera_y_se_escribe_aceptando(self):
        c = _controles_falsos(a_revisar=1, avisos=2)
        codigo, _, _, escribir = self.correr(["obraa", "--escribir", "--aceptar-controles", "2"], c)
        self.assertEqual(0, codigo)
        escribir.assert_called_once()
        self.assertEqual(True, escribir.call_args.args[5])

    def test_con_otra_cifra_la_guarda_sigue(self):
        c = _controles_falsos(a_revisar=1, avisos=2)
        codigo, texto, _, escribir = self.correr(["obraa", "--escribir", "--aceptar-controles", "5"], c)
        self.assertEqual(3, codigo)
        self.assertIn("no coincide", texto)
        escribir.assert_not_called()

    def test_un_control_que_no_vale_sale_con_2_y_no_bloquea_las_hojas(self):
        codigo, texto, _, _ = self.correr(["obraa"], _controles_falsos(rechazado=1))
        self.assertEqual(2, codigo)
        codigo, _, _, escribir = self.correr(["obraa", "--escribir"], _controles_falsos(rechazado=1), hojas=True)
        escribir.assert_called_once()

    def test_sin_hojas_con_escribir_y_solo_un_control_que_no_vale_sale_con_2_sin_escribir(self):
        codigo, texto, _, escribir = self.correr(["obraa", "--escribir"], _controles_falsos(rechazado=1))
        self.assertEqual(2, codigo)
        self.assertIn("NO hay hojas nuevas.", texto)
        escribir.assert_not_called()

    def test_si_no_se_pueden_revisar_los_controles_se_dice_y_sale_con_2(self):
        codigo, texto, _, _ = self.correr(["obraa"], None, error="No se pudieron revisar los controles horarios: boom")
        self.assertEqual(2, codigo)
        self.assertIn("ERROR: No se pudieron revisar los controles horarios: boom", texto)

    def test_con_hojas_la_vista_previa_sigue_simulandolas(self):
        codigo, _, simular, _ = self.correr(["obraa"], _controles_falsos(), hojas=True)
        self.assertEqual(0, codigo)
        simular.assert_called_once()

    def test_forzar_fecha_sin_hojas_sigue_siendo_un_error(self):
        codigo, texto, _, _ = self.correr(["obraa", "--forzar-fecha", "01/01/2026"], _controles_falsos(listo=1))
        self.assertEqual(2, codigo)
        self.assertIn("No hay ninguna hoja seleccionable", texto)


class TestEscribirConControles(BaseControles):
    """`_escribir` de «actualiza la obra» con las piezas pesadas (regeneración, PDF, índice) simuladas: lo que se
    prueba es el cableado de los controles: se aplican antes de regenerar, salen en la sección H del informe,
    las demás obras no se mueven y un fallo deja el informe en REVISAR."""

    OBRA = {"id": "obraa", "nombre": "2026 OBRA A", "carpeta_obra": "2026 OBRA A", "subtitulo": ""}

    def setUp(self):
        super().setUp()
        import argparse
        import tempfile
        self.logs = Path(tempfile.mkdtemp(prefix="logs08b_", dir=str(self.top)))
        info = self.raiz / ABIERTAS["obraa"] / "INFORME SAGARDE IA"
        info.mkdir(parents=True, exist_ok=True)
        (info / "ficha_obra.json").write_text(
            json.dumps({"revisiones": [], "estados": {}, "estructura": {}}), encoding="utf-8")
        (self.raiz / "index.html").write_text("<html></html>", encoding="utf-8")
        self.args = argparse.Namespace(forzar_fecha=None, aceptar_estructura=False, aceptar_hoja_grande=[],
                                       aceptar_controles=[])
        self.llamadas = []
        self.efecto_en_regeneracion = None
        registro = [{"id": oid, "nombre": NOMBRES[oid], "carpeta_obra": ABIERTAS[oid]} for oid in ABIERTAS]
        parches = [
            mock.patch.object(ao, "OBRAS_DIR", self.raiz),
            mock.patch.object(ao, "INDEX_PATH", self.raiz / "index.html"),
            mock.patch.object(ao, "LOGS_DIR", self.logs),
            mock.patch.object(ao, "MOTOR_IA_DIR", self.motor),
            mock.patch.object(ao, "OBRAS", registro),
            mock.patch.object(ao, "_ejecutar_regeneracion", side_effect=self._regenerar),
            mock.patch.object(ao, "_ejecutar_finalizar", return_value=""),
            mock.patch.object(ao, "verificar_pdf", return_value=ao.VerificacionPdf(None, 1, 1, "x", [], [], [])),
            mock.patch.object(ao, "comparar_tarjetas_indice", return_value=ao.ComparacionTarjetas([], True)),
            contextlib.redirect_stdout(io.StringIO()),
        ]
        for p in parches:
            p.__enter__()
            self.addCleanup(p.__exit__, None, None, None)

    def _regenerar(self, obra_id):
        filas = len(po.aplanar(str(self.raiz), ABIERTAS, "obraa"))
        self.llamadas.append(("regenerar", obra_id, filas))
        if self.efecto_en_regeneracion:
            self.efecto_en_regeneracion()
        return "", 1

    def informe(self):
        informes = sorted(self.logs.glob("actualizacion_obraa_*.txt"))
        return informes[-1].read_text(encoding="utf-8") if informes else ""

    def escribir(self, aceptar=False):
        codigo = ao._escribir(self.OBRA, self.args, ao.DeteccionHojas(), ao._controles(self.OBRA), None, aceptar)
        return codigo, self.informe()

    def test_un_control_limpio_se_aplica_antes_de_regenerar_y_sale_en_la_seccion_h(self):
        self.fichero("23102026", LIMPIO)
        codigo, informe = self.escribir()
        self.assertEqual(0, codigo, informe)
        self.assertEqual([("regenerar", "obraa", 2)], self.llamadas, "se aplica ANTES de regenerar el panel")
        self.assertIn("Control horario aplicado: 1 fichero (la sección H lo detalla).", informe)
        self.assertIn("H) CONTROL HORARIO", informe)
        self.assertIn("APLICADO: 1 jornada de viviendas, 2 personas nuevas", informe)
        self.assertIn("Horas de la obra: antes sin jornadas; después 15,5 h en 1 día con 2 personas.", informe)
        self.assertIn("Personas en la lista de trabajadores: antes None; después 2.", informe)
        self.assertIn("obrab: SIN DATOS -> SIN DATOS [IDENTICO]", informe)
        self.assertIn("G) OK", informe)
        self.assertLess(informe.index("G) OK"), informe.index("H) CONTROL HORARIO"))

    def test_sin_hojas_ni_controles_aplicables_no_hay_nada_que_hacer(self):
        codigo, _ = self.escribir()
        self.assertEqual(2, codigo, "como siempre: se llamó a escribir sin nada que escribir")
        self.assertEqual([], self.llamadas)
        self.assertIn("ninguna hoja ni control horario", self.informe())

    def test_un_dudoso_aceptado_se_aplica_y_dice_que_fue_con_su_visto_bueno(self):
        self.ingerir(L_A)
        self.fichero("23102026", DUDOSO)
        codigo, informe = self.escribir(aceptar=True)
        self.assertEqual(0, codigo, informe)
        self.assertIn("APLICADO (con tu visto bueno)", informe)

    def test_un_dudoso_sin_aceptar_no_se_aplica_aunque_llegue_a_escribir(self):
        self.ingerir(L_A)
        self.fichero("23102026", DUDOSO)
        codigo, _ = self.escribir(aceptar=False)
        self.assertEqual(2, codigo, "no hay nada aplicable")
        self.assertEqual(4, len(po.aplanar(str(self.raiz), ABIERTAS, "obraa")), "los datos no se tocaron")

    def test_un_control_que_no_vale_deja_el_informe_en_revisar_pero_aplica_el_limpio(self):
        self.fichero("22102026", b"{no")
        self.fichero("23102026", LIMPIO)
        codigo, informe = self.escribir()
        self.assertEqual(2, codigo)
        self.assertIn("G) REVISAR", informe)
        self.assertIn("1 control horario NO vale y no se han aplicado (ver H)", informe)
        self.assertEqual(1, len(self.llamadas), "el limpio sí se aplicó y se regeneró")
        self.assertEqual(2, len(po.aplanar(str(self.raiz), ABIERTAS, "obraa")))

    def test_si_al_regenerar_se_mueve_el_personal_de_otra_obra_es_un_error_de_efecto_colateral(self):
        self.fichero("23102026", LIMPIO)

        def toca_la_otra():
            otra = self.raiz / ABIERTAS["obrab"] / "INFORME SAGARDE IA"
            otra.mkdir(parents=True, exist_ok=True)
            (otra / "personal_obra.json").write_text("{}", encoding="utf-8")
        self.efecto_en_regeneracion = toca_la_otra
        codigo, informe = self.escribir()
        self.assertEqual(2, codigo)
        self.assertIn("[CAMBIO]", informe)
        self.assertIn("ERROR (efecto colateral) en los datos de personal de: obrab", informe)

    def test_si_los_controles_no_se_pudieron_revisar_se_cuenta_en_el_informe(self):
        self.fichero("23102026", LIMPIO)
        codigo = ao._escribir(self.OBRA, self.args, ao.DeteccionHojas(), ao._controles(self.OBRA),
                              "No se pudieron revisar los controles horarios: boom", False)
        self.assertEqual(2, codigo)
        self.assertIn("ERROR: No se pudieron revisar los controles horarios: boom", self.informe())

    def test_un_fallo_al_aplicar_deja_informe_de_fallo_y_sale_con_2(self):
        self.fichero("23102026", LIMPIO)
        controles = ao._controles(self.OBRA)
        with mock.patch.object(ao, "_controles", side_effect=ao.ErrorActualizacion("disco lleno")):
            codigo = ao._escribir(self.OBRA, self.args, ao.DeteccionHojas(), controles, None, False)
        self.assertEqual(2, codigo)
        self.assertIn("G) REVISAR: disco lleno", self.informe())
        self.assertEqual([], self.llamadas, "si falla al aplicar no se regenera nada")


class TestDocumentosDeLaObra(unittest.TestCase):
    """Decisión de Bixente (25/10/2026): un CONTROL HORARIO de REVISIONES es un dato de entrada, no un papel de la
    obra, y no cuenta ni sale en la lista de Documentos (ni en la ficha ni en el panel). H10: una carpeta REVISIONES
    con un control horario da la misma lista de documentos que sin él."""

    def arbol(self, *rutas):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        obra = base / "2026 OBRA A"
        for ruta in rutas:
            f = obra / ruta
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("x", encoding="utf-8")
        return str(obra), str(base)

    def nombres(self, *rutas):
        import lectores
        obra, base = self.arbol(*rutas)
        return sorted(d["nombre"] for d in lectores.listar_documentos(obra, base))

    def test_los_controles_horarios_de_revisiones_no_son_documentos(self):
        con = self.nombres("REVISIONES/REVISION OBRA 01012026.html", "PLANOS/p1.pdf",
                           "REVISIONES/CONTROL HORARIO 2026 OBRA A 25102026.json",
                           "REVISIONES/CONTROL HORARIO 2026 OBRA A 25102026 (1).json",
                           "REVISIONES/control horario 2026 obra a 24102026.JSON")
        sin = self.nombres("REVISIONES/REVISION OBRA 01012026.html", "PLANOS/p1.pdf")
        self.assertEqual(sin, con)
        self.assertEqual(["REVISION OBRA 01012026.html", "p1.pdf"], con)

    def test_la_carpeta_se_reconoce_sin_importar_mayusculas(self):
        self.assertEqual([], self.nombres("revisiones/CONTROL HORARIO a.json"))

    def test_otros_json_de_revisiones_y_controles_fuera_de_revisiones_siguen_contando(self):
        """Solo se aparta lo que de verdad entra por «actualiza la obra»: un control horario fuera de REVISIONES no
        lo lee nadie, así que se ve (y se puede encontrar y mover)."""
        self.assertEqual(["CONTROL HORARIO suelto.json", "notas.json"],
                         self.nombres("REVISIONES/notas.json", "CONTROL HORARIO suelto.json"))
        self.assertEqual(["CONTROL HORARIO en planos.json"], self.nombres("PLANOS/CONTROL HORARIO en planos.json"))

    def test_la_regla_es_una_sola_y_la_comparte_el_lector(self):
        import lector_control_horario as lc
        for bueno in ("CONTROL HORARIO a.json", "control horario.JSON", "Control Horario 2026 OLABEAGA 25102026 (1).json"):
            self.assertTrue(lc.es_control_horario(bueno), bueno)
        for malo in ("CONTROL HORARIO a.txt", "MI CONTROL HORARIO.json", "REVISION 25102026.json", "control.json", ""):
            self.assertFalse(lc.es_control_horario(malo), malo)

    def test_listar_del_lector_usa_la_misma_regla(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            for n in ("CONTROL HORARIO a.json", "control horario b.JSON", "MI CONTROL HORARIO.json", "notas.json"):
                (Path(tmp) / n).write_text("{}", encoding="utf-8")
            self.assertEqual(["CONTROL HORARIO a.json", "control horario b.JSON"],
                             sorted(f["nombre"] for f in lector.listar(tmp)))


class TestRevisarControles(unittest.TestCase):
    def test_un_fallo_se_devuelve_como_texto_y_no_lanza(self):
        with mock.patch.object(ao, "_controles", side_effect=ao.ErrorActualizacion("boom")):
            self.assertEqual((None, "boom"), ao._revisar_controles({"id": "x"}))

    def test_hay_problema_si_hay_error_o_rechazados(self):
        self.assertFalse(ao._hay_problema_controles(_controles_falsos(listo=1, ya=2), None))
        self.assertTrue(ao._hay_problema_controles(_controles_falsos(rechazado=1), None))
        self.assertTrue(ao._hay_problema_controles(None, "boom"))
        self.assertFalse(ao._hay_problema_controles(None, None))

    def test_controles_pasa_escribir_y_aceptar_a_personal_integracion(self):
        with mock.patch.object(pi, "controles_horarios", return_value={"x": 1}) as ch:
            self.assertEqual({"x": 1}, ao._controles({"id": "obraa"}, escribir=True, aceptar=True))
            ao._controles({"id": "obraa"})
        self.assertEqual({"escribir": True, "aceptar": True}, ch.call_args_list[0].kwargs)
        self.assertEqual({"escribir": False, "aceptar": False}, ch.call_args_list[1].kwargs)

    def test_controles_traduce_cualquier_excepcion_a_error_de_actualizacion(self):
        with mock.patch.object(pi, "controles_horarios", side_effect=RuntimeError("zas")):
            with self.assertRaises(ao.ErrorActualizacion) as cm:
                ao._controles({"id": "obraa"})
        self.assertIn("RuntimeError: zas", str(cm.exception))


# ─── el .bat: generar_todos.py ────────────────────────────────────────────────────────────────────
class TestGanchoDeGenerarTodos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import generar_todos
        cls.gt = generar_todos

    OBRA = {"id": "x", "nombre": "2026 X", "carpeta_obra": "2026 X"}

    def test_imprime_las_lineas_que_le_da_personal_integracion(self):
        r = {"lineas": ["  [PERSONAL] sin controles horarios en 2026 X"], "aplicados": 0, "avisos": 0}
        with mock.patch.object(pi, "aplicar_controles_limpios", return_value=r) as ap, \
                contextlib.redirect_stdout(io.StringIO()) as salida:
            self.assertIs(r, self.gt._controles_horarios_de_obra(self.OBRA))
        self.assertIn("sin controles horarios en 2026 X", salida.getvalue())
        self.assertEqual("x", ap.call_args.args[0])

    def test_un_fallo_inesperado_avisa_y_no_lanza(self):
        with mock.patch.object(pi, "aplicar_controles_limpios", side_effect=RuntimeError("boom")), \
                contextlib.redirect_stdout(io.StringIO()) as salida:
            self.assertIsNone(self.gt._controles_horarios_de_obra(self.OBRA))
        self.assertIn("[AVISO PERSONAL]", salida.getvalue())
        self.assertIn("boom", salida.getvalue())
        self.assertIn("2026 X", salida.getvalue())

    def test_main_aplica_los_controles_de_cada_obra_antes_de_leer_sus_filas(self):
        """Lo declarado tiene que producir efecto: si main() no llamase al gancho, todo lo anterior sería letra muerta."""
        fuente = (_BASE / "generar_todos.py").read_text(encoding="utf-8")
        main = next(n for n in ast.parse(fuente).body if isinstance(n, ast.FunctionDef) and n.name == "main")
        bucle = next(n for n in ast.walk(main) if isinstance(n, ast.For)
                     and isinstance(n.iter, ast.Name) and n.iter.id == "OBRAS")
        llamadas = []
        for n in ast.walk(bucle):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                llamadas.append((n.lineno, n.func.id))
        nombres = [nombre for _, nombre in sorted(llamadas)]
        self.assertIn("_controles_horarios_de_obra", nombres)
        self.assertIn("_personal_para_panel", nombres)
        self.assertLess(nombres.index("_controles_horarios_de_obra"), nombres.index("_personal_para_panel"))
        # y dentro del try de cada obra: un fallo del gancho nunca debe saltarse el except de «Fallo al generar»
        intentos = [t for t in ast.walk(bucle) if isinstance(t, ast.Try)]
        dentro = [t for t in intentos if any(isinstance(c, ast.Call) and getattr(c.func, "id", "") == "_controles_horarios_de_obra"
                                             for c in ast.walk(t))]
        self.assertTrue(dentro, "el gancho debe estar dentro del try de la obra")

    def test_regenerar_una_obra_pasa_por_el_mismo_gancho(self):
        """`regenerar_obra.py <obra>` llama a generar_todos.main() con el registro limitado a esa obra."""
        fuente = (_SCRIPTS / "regenerar_obra.py").read_text(encoding="utf-8")
        regenerar = next(n for n in ast.parse(fuente).body if isinstance(n, ast.FunctionDef) and n.name == "regenerar_una_obra")
        llamadas = [ast.unparse(n.func) for n in ast.walk(regenerar) if isinstance(n, ast.Call)]
        self.assertIn("gt.main", llamadas)


if __name__ == "__main__":
    unittest.main()
