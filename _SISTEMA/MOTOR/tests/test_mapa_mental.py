# -*- coding: utf-8 -*-
"""El mapa mental es lectura obligatoria al empezar sesion.

Si declara una ruta que ya no existe, manda a ciegas a quien lo lee: el
08/08/2026 el motor bajo a `_SISTEMA/MOTOR/` y el mapa siguio diciendo
`_MOTOR_SAGARDE/` 23 veces. Nadie se entero hasta el 12/08.

Estas pruebas fijan el contrato del actualizador que corre desde
Actualizar_Sagarde.bat: que sabe leer una ruta declarada, que no confunde el
alfabeto de estados con una carpeta, y que un bloque generado que no encuentra
su marca es un error y no un silencio.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

MOTOR_DIR = Path(__file__).resolve().parent.parent
ROOT = MOTOR_DIR.parent.parent
sys.path.insert(0, str(MOTOR_DIR / "scripts"))

import actualizar_mapa_mental as amm


MAPA = ROOT / "_SISTEMA" / "docs" / "SAGARDE_MAPA_MENTAL_ENTORNO.md"


class TestExtraerRutas(unittest.TestCase):
    """Que cuenta como ruta declarada dentro del documento."""

    def test_una_ruta_entre_comillas_se_reconoce(self):
        self.assertIn(
            "_SISTEMA/MOTOR/avisos.py",
            amm.extraer_rutas("La regla vive en `_SISTEMA/MOTOR/avisos.py` y se comparte."),
        )

    def test_el_alfabeto_de_estados_no_es_una_ruta(self):
        # `X M / P ? N` lleva barra, pero es el alfabeto de la ficha.
        self.assertEqual([], amm.extraer_rutas("Ficha `X M / P ? N` | `ficha_obra.py:33-44`"))

    def test_el_snapshot_con_barra_suelta_tampoco(self):
        self.assertEqual([], amm.extraer_rutas("Snapshot `X M / vacio`"))

    def test_un_comando_no_es_una_ruta(self):
        self.assertEqual([], amm.extraer_rutas("El BAT termina en `git add -A`, commit y push."))

    def test_se_recorta_la_referencia_de_linea(self):
        self.assertEqual(
            ["_SISTEMA/MOTOR/sagarde_portal.py"],
            amm.extraer_rutas("Ver `_SISTEMA/MOTOR/sagarde_portal.py:147-183`."),
        )

    def test_la_abreviatura_declarada_por_el_mapa_se_expande(self):
        # El propio documento declara que `_SISTEMA...` es esa carpeta.
        self.assertEqual(
            ["SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/ficha_obra.py"],
            amm.extraer_rutas("Persistencia en `_SISTEMA.../ficha_obra.py`."),
        )

    def test_una_plantilla_con_marcadores_no_se_audita(self):
        self.assertEqual([], amm.extraer_rutas("Sidecar `<obra>/.../ficha_obra.json`"))

    def test_un_nombre_suelto_sin_carpeta_no_se_audita(self):
        # `AAAA-MM-DD-descripcion.md` es una convencion de nombre, no un fichero.
        self.assertEqual([], amm.extraer_rutas("Plan fechado `AAAA-MM-DD-descripcion.md`"))

    def test_una_carpeta_oculta_conserva_su_punto(self):
        # `.claude/launch.json` no es `claude/launch.json`.
        self.assertEqual(
            [".claude/launch.json"],
            amm.extraer_rutas("Cuatro servidores en `.claude/launch.json`."),
        )

    def test_un_comando_de_skill_no_es_una_ruta(self):
        self.assertEqual([], amm.extraer_rutas("Se invoca como `/sagarde-revision`."))

    def test_una_enumeracion_de_campos_no_es_una_ruta(self):
        # El esquema comun se escribe con barras, y no es una carpeta.
        self.assertEqual([], amm.extraer_rutas("Se normaliza a `task/floor/building/unit/status`."))
        self.assertEqual([], amm.extraer_rutas("Filtros `all/recent/vencido/pdf/word/images`."))

    def test_una_plantilla_con_puntos_suspensivos_no_se_audita(self):
        self.assertEqual([], amm.extraer_rutas("Fuente `SAGARDE OBRAS ABIERTAS/X/REVISION/.../*.md`"))

    def test_lo_que_escribe_el_propio_generador_no_se_audita(self):
        # El bloque generado nombra la ruta del script que lo escribe. Si se
        # auditara, el documento se denunciaria a si mismo y la segunda pasada
        # nunca coincidiria con la primera.
        texto = (
            "Prosa con `_SISTEMA/MOTOR/avisos.py`.\n"
            "<!-- AUTO:estado -->\n"
            "Generado por `_SISTEMA/MOTOR/scripts/actualizar_mapa_mental.py`.\n"
            "<!-- /AUTO:estado -->\n"
        )
        self.assertEqual(["_SISTEMA/MOTOR/avisos.py"], amm.extraer_rutas(texto))

    def test_una_carpeta_narrada_como_inexistente_no_se_audita(self):
        # El mapa cuenta que `PARA SOBREESCRIBIR/` ya no existe; no es una
        # promesa de que exista.
        self.assertEqual([], amm.extraer_rutas("`PARA SOBREESCRIBIR/` ya no existe: estaba vacia."))


class TestRutasMuertas(unittest.TestCase):
    """Una ruta declarada que no existe en disco."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        (self.raiz / "_SISTEMA" / "MOTOR").mkdir(parents=True)
        (self.raiz / "_SISTEMA" / "MOTOR" / "avisos.py").write_text("# vivo", encoding="utf-8")
        self.addCleanup(self._tmp.cleanup)

    def test_una_ruta_que_no_existe_sale_como_muerta(self):
        self.assertEqual(
            ["_MOTOR_SAGARDE/avisos.py"],
            amm.rutas_muertas("La regla vive en `_MOTOR_SAGARDE/avisos.py`.", self.raiz),
        )

    def test_una_ruta_que_existe_no_sale(self):
        self.assertEqual(
            [],
            amm.rutas_muertas("La regla vive en `_SISTEMA/MOTOR/avisos.py`.", self.raiz),
        )

    def test_un_comodin_que_casa_con_algo_cuenta_como_viva(self):
        self.assertEqual([], amm.rutas_muertas("Codigo en `_SISTEMA/MOTOR/*.py`.", self.raiz))

    def test_un_comodin_que_no_casa_con_nada_sale_como_muerto(self):
        self.assertEqual(
            ["_SISTEMA/MOTOR/*.rb"],
            amm.rutas_muertas("Codigo en `_SISTEMA/MOTOR/*.rb`.", self.raiz),
        )

    def test_cada_ruta_muerta_se_reporta_una_sola_vez(self):
        texto = "`_MOTOR_SAGARDE/x.py` y otra vez `_MOTOR_SAGARDE/x.py`"
        self.assertEqual(["_MOTOR_SAGARDE/x.py"], amm.rutas_muertas(texto, self.raiz))

    def test_una_ruta_relativa_que_existe_en_otro_sitio_no_esta_muerta(self):
        # El mapa cita `reglas/CATALOGO_TAJOS.json` sin la carpeta que lo
        # contiene. El fichero existe y el lector lo encuentra: no es un error.
        (self.raiz / "obras" / "reglas").mkdir(parents=True)
        (self.raiz / "obras" / "reglas" / "CATALOGO.json").write_text("{}", encoding="utf-8")
        self.assertEqual(
            [], amm.rutas_muertas("Catalogo en `reglas/CATALOGO.json`.", self.raiz))

    def test_una_ruta_que_no_existe_en_ninguna_parte_si_esta_muerta(self):
        self.assertEqual(
            ["reglas/INVENTADO.json"],
            amm.rutas_muertas("Catalogo en `reglas/INVENTADO.json`.", self.raiz))

    def test_una_carpeta_de_primer_nivel_que_existe_se_audita_aunque_no_lleve_extension(self):
        (self.raiz / ".claude").mkdir()
        self.assertEqual(
            [".claude/agents"],
            amm.rutas_muertas("Agentes en `.claude/agents`.", self.raiz))


class TestBloquesGenerados(unittest.TestCase):
    """El actualizador solo escribe entre marcas, nunca sobre la prosa."""

    TEXTO = (
        "# Titulo\n\nProsa que se conserva.\n\n"
        "<!-- AUTO:estado -->\nviejo\n<!-- /AUTO:estado -->\n\n"
        "Mas prosa que se conserva.\n"
    )

    def test_reemplaza_solo_el_interior_del_bloque(self):
        salida = amm.reemplazar_bloque(self.TEXTO, "estado", "nuevo")
        self.assertIn("nuevo", salida)
        self.assertNotIn("viejo", salida)
        self.assertIn("Prosa que se conserva.", salida)
        self.assertIn("Mas prosa que se conserva.", salida)

    def test_las_marcas_sobreviven_para_la_siguiente_pasada(self):
        salida = amm.reemplazar_bloque(self.TEXTO, "estado", "nuevo")
        self.assertIn("<!-- AUTO:estado -->", salida)
        self.assertIn("<!-- /AUTO:estado -->", salida)
        otra = amm.reemplazar_bloque(salida, "estado", "tercero")
        self.assertIn("tercero", otra)
        self.assertNotIn("nuevo", otra)

    def test_un_bloque_que_no_existe_es_un_error_y_no_un_silencio(self):
        # La familia de fallos de este proyecto: algo declarado que el motor
        # ignora sin avisar. Un nombre de bloque mal escrito tiene que doler.
        with self.assertRaises(amm.BloqueAusente):
            amm.reemplazar_bloque(self.TEXTO, "no_existe", "nuevo")


class TestEstadoDeObras(unittest.TestCase):
    """Las cifras del mapa salen de las fichas, no de la memoria de nadie."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        carpeta = self.raiz / "SAGARDE OBRAS ABIERTAS" / "2026 OBRA FALSA" / "INFORME SAGARDE IA"
        carpeta.mkdir(parents=True)
        estados = {}
        for portal in ("p1", "p2"):
            for unidad in ("A", "B"):
                for tajo in ("tabicado", "tubeado", "mecanizado"):
                    estados[f"{portal}__pb__{tajo}__{unidad}"] = {"v": "X", "f": "01/01/2026"}
        estados["p1__pb__tabicado__A"]["v"] = "P"
        (carpeta / "ficha_obra.json").write_text(
            json.dumps({
                "id": "falsa",
                "tajos": {"aplicables": ["tabicado", "tubeado", "mecanizado"]},
                "estados": estados,
            }),
            encoding="utf-8",
        )
        self.addCleanup(self._tmp.cleanup)

    def test_cuenta_ubicaciones_tajos_y_celdas(self):
        obras = amm.estado_obras(self.raiz)
        self.assertEqual(1, len(obras))
        obra = obras[0]
        self.assertEqual("2026 OBRA FALSA", obra["obra"])
        self.assertEqual(4, obra["ubicaciones"])   # 2 portales x 2 unidades
        self.assertEqual(3, obra["tajos"])
        self.assertEqual(12, obra["celdas"])

    def test_desglosa_los_estados_en_vez_de_resumirlos_en_un_porcentaje(self):
        # El porcentaje redondeado es un criterio ciego (CLAUDE.md seccion 3).
        obra = amm.estado_obras(self.raiz)[0]
        self.assertEqual({"X": 11, "P": 1}, obra["desglose"])


class TestNoEscribirPorEscribir(unittest.TestCase):
    """Una pasada que no cambia nada no puede ensuciar el repositorio.

    `Actualizar_Sagarde.bat` hace `git add -A` y solo commitea si hay
    diferencias. Si el mapa se reescribiera en cada pasada solo por sellar la
    hora, cada ejecucion crearia un commit vacio y el "No hay cambios nuevos
    que subir" del BAT dejaria de ser cierto.
    """

    MAPA_MINIMO = (
        "# Mapa\n\n"
        "<!-- AUTO:estado -->\nx\n<!-- /AUTO:estado -->\n\n"
        "<!-- AUTO:rutas_muertas -->\nx\n<!-- /AUTO:rutas_muertas -->\n"
    )

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.mapa = self.raiz / "mapa.md"
        self.mapa.write_text(self.MAPA_MINIMO, encoding="utf-8")
        self.addCleanup(self._tmp.cleanup)

    def test_la_primera_pasada_escribe(self):
        self.assertTrue(amm.actualizar_mapa(self.mapa, self.raiz)["cambiado"])

    def test_la_segunda_pasada_sin_cambios_reales_no_toca_el_fichero(self):
        amm.actualizar_mapa(self.mapa, self.raiz)
        antes = self.mapa.read_text(encoding="utf-8")
        resultado = amm.actualizar_mapa(self.mapa, self.raiz)
        self.assertFalse(resultado["cambiado"])
        self.assertEqual(antes, self.mapa.read_text(encoding="utf-8"))

    def test_un_cambio_real_si_reescribe_aunque_la_hora_sea_la_misma(self):
        amm.actualizar_mapa(self.mapa, self.raiz)
        carpeta = self.raiz / "SAGARDE OBRAS ABIERTAS" / "2026 NUEVA" / "INFORME SAGARDE IA"
        carpeta.mkdir(parents=True)
        (carpeta / "ficha_obra.json").write_text(
            json.dumps({"tajos": {"aplicables": ["t"]}, "estados": {"p1__pb__t__A": {"v": "X"}}}),
            encoding="utf-8")
        self.assertTrue(amm.actualizar_mapa(self.mapa, self.raiz)["cambiado"])
        self.assertIn("2026 NUEVA", self.mapa.read_text(encoding="utf-8"))


class TestElMapaRealEstaAlDia(unittest.TestCase):
    """Trinquete: el mapa publicado no puede volver a declarar rutas muertas."""

    def test_el_mapa_real_no_declara_ninguna_ruta_muerta(self):
        texto = MAPA.read_text(encoding="utf-8")
        muertas = amm.rutas_muertas(texto, ROOT)
        self.assertEqual(
            [], muertas,
            "El mapa declara rutas que no existen en disco:\n  " + "\n  ".join(muertas),
        )

    def test_el_mapa_real_tiene_los_bloques_que_el_actualizador_rellena(self):
        texto = MAPA.read_text(encoding="utf-8")
        for bloque in amm.BLOQUES:
            self.assertIn(f"<!-- AUTO:{bloque} -->", texto)
            self.assertIn(f"<!-- /AUTO:{bloque} -->", texto)


if __name__ == "__main__":
    unittest.main()
