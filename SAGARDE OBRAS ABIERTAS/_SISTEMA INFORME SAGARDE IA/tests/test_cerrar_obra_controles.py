# -*- coding: utf-8 -*-
"""Pruebas del freno de cierre de obra por controles horarios sin aplicar.

Una obra con controles horarios pendientes en REVISIONES no se puede cerrar
porque, al salir del registro, nadie aplicaria esos controles y las jornadas
nunca llegarian al ranking ni al historico.

Todo se prueba sobre un arbol temporal con tempfile.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SISTEMA_DIR = os.path.dirname(_TESTS_DIR)
if _SISTEMA_DIR not in sys.path:
    sys.path.insert(0, _SISTEMA_DIR)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

import cerrar_obra
import lector_control_horario as lector
import personal_obra as po

try:
    from tests.test_cerrar_obra import REGISTRO_DE_JUGUETE, _obra_falsa
except ImportError:
    from test_cerrar_obra import REGISTRO_DE_JUGUETE, _obra_falsa


def _contenido_control(fecha="2026-10-20", nombre="Ana", horas=7.5, obra="falsa"):
    """Contenido JSON valido de un CONTROL HORARIO para la obra."""
    return json.dumps({
        "tipo": "lote_personal",
        "version": 1,
        "obra": obra,
        "jornadas": [
            {
                "ambito": "vivienda",
                "fecha": fecha,
                "presentes": [{"nombre": nombre, "horas": horas, "extra": 0}],
            }
        ],
    })


def _montar_entorno(raiz, con_revisiones=True):
    """Monta una obra minima en un arbol temporal con registro, adaptador y cerradas."""
    obra = _obra_falsa(raiz)
    motor = raiz / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
    (motor / "adaptadores").mkdir(parents=True, exist_ok=True)
    (motor / "adaptadores" / "adaptador_falsa.py").write_text("#", encoding="utf-8")
    registro_txt = (
        REGISTRO_DE_JUGUETE.replace("'una'", "'falsa'")
        .replace("2026 UNA", "2026 OBRA FALSA")
        .replace("adaptador_una", "adaptador_falsa")
    )
    (motor / "registro_obras.py").write_text(registro_txt, encoding="utf-8")
    (raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS").mkdir(parents=True, exist_ok=True)
    revisiones = raiz / "SAGARDE OBRAS ABIERTAS" / "2026 OBRA FALSA" / "REVISIONES"
    if con_revisiones:
        revisiones.mkdir(parents=True, exist_ok=True)
    return obra, motor, revisiones


def _aplicar_controles(raiz, obra_id="falsa", carpeta="2026 OBRA FALSA", fecha_hoy="2026-10-26"):
    """Aplica de verdad los controles de REVISIONES usando lector.aplicar."""
    rev = raiz / "SAGARDE OBRAS ABIERTAS" / carpeta / "REVISIONES"
    ficheros = lector.listar(str(rev))
    return lector.aplicar(
        obra_id,
        ficheros,
        fecha_hoy,
        str(raiz / "SAGARDE OBRAS ABIERTAS"),
        {obra_id: carpeta},
        ahora=f"{fecha_hoy}T10:00:00+01:00",
    )


class TestDeteccionControlesSinAplicar(unittest.TestCase):
    """Comprueba la deteccion y clasificacion de ficheros en REVISIONES."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra, self.motor, self.revisiones = _montar_entorno(self.raiz, con_revisiones=True)
        self.addCleanup(self._tmp.cleanup)

    def test_01_sin_carpeta_revisiones_no_hay_pendientes_y_ejecutar_cierra(self):
        # Si no existe REVISIONES, no hay nada pendiente ni aplicado y cerrar ejecuta con normalidad.
        if self.revisiones.exists():
            self.revisiones.rmdir()
        info = cerrar_obra.controles_sin_aplicar(self.raiz, self.obra)
        self.assertEqual([], info["pendientes"])
        self.assertEqual(0, info["aplicados"])
        self.assertIsNone(info["error"])

        resultado = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertTrue(resultado["movida"])

    def test_02_control_aplicado_consta_en_aplicados_y_ejecutar_cierra(self):
        # Un control aplicado con lector.aplicar deja su SHA256 en la traza: cuenta como aplicado.
        ruta_control = self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json"
        ruta_control.write_text(_contenido_control("2026-10-20", "Ana"), encoding="utf-8")
        _aplicar_controles(self.raiz)

        info = cerrar_obra.controles_sin_aplicar(self.raiz, self.obra)
        self.assertEqual([], info["pendientes"])
        self.assertEqual(1, info["aplicados"])
        self.assertIsNone(info["error"])

        resultado = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertTrue(resultado["movida"])

    def test_03_control_sin_aplicar_detecta_pendiente_listo_para_aplicar(self):
        # Un fichero valido que aun no se ha aplicado aparece como pendiente en situacion 'listo para aplicar'.
        ruta_control = self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json"
        ruta_control.write_text(_contenido_control("2026-10-20", "Ana"), encoding="utf-8")

        info = cerrar_obra.controles_sin_aplicar(self.raiz, self.obra)
        self.assertEqual(0, info["aplicados"])
        self.assertEqual(1, len(info["pendientes"]))
        p = info["pendientes"][0]
        self.assertEqual("CONTROL HORARIO 2026 OBRA FALSA 20102026.json", p["nombre"])
        self.assertEqual("listo para aplicar", p["situacion"])

    def test_04_copia_con_otro_nombre_mismo_contenido_cuenta_como_aplicada(self):
        # Si un fichero tiene el mismo contenido (mismo SHA256) que uno aplicado, cuenta como aplicado.
        contenido = _contenido_control("2026-10-20", "Ana")
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json").write_text(
            contenido, encoding="utf-8"
        )
        _aplicar_controles(self.raiz)

        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026 (1).json").write_text(
            contenido, encoding="utf-8"
        )
        info = cerrar_obra.controles_sin_aplicar(self.raiz, self.obra)
        self.assertEqual([], info["pendientes"])
        self.assertEqual(2, info["aplicados"])

        resultado = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertTrue(resultado["movida"])

    def test_05_fichero_control_que_no_es_json_figura_como_no_vale(self):
        # Un fichero con nombre de control pero contenido no JSON queda pendiente con situacion 'no vale...'.
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA corrupto.json").write_text(
            "{esto no es un json valido", encoding="utf-8"
        )
        info = cerrar_obra.controles_sin_aplicar(self.raiz, self.obra)
        self.assertEqual(0, info["aplicados"])
        self.assertEqual(1, len(info["pendientes"]))
        p = info["pendientes"][0]
        self.assertEqual("CONTROL HORARIO 2026 OBRA FALSA corrupto.json", p["nombre"])
        self.assertTrue(p["situacion"].startswith("no vale tal como esta"))

    def test_06_control_con_fecha_futura_figura_como_hay_que_mirarlo(self):
        # Una jornada con fecha en el futuro exige revision y su situacion empieza por 'hay que mirarlo...'.
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA futuro.json").write_text(
            _contenido_control("2099-01-01", "Ana"), encoding="utf-8"
        )
        info = cerrar_obra.controles_sin_aplicar(self.raiz, self.obra)
        self.assertEqual(1, len(info["pendientes"]))
        p = info["pendientes"][0]
        self.assertEqual("CONTROL HORARIO 2026 OBRA FALSA futuro.json", p["nombre"])
        self.assertTrue(p["situacion"].startswith("hay que mirarlo antes de aplicarlo"))

    def test_07_ficheros_ajenos_se_ignoran_y_variantes_de_nombre_cuentan(self):
        # Otros ficheros (.html, otros .json) se ignoran; mayusculas/minusculas y sufijos en el nombre si cuentan.
        (self.revisiones / "hoja_revision_01.html").write_text("<html/>", encoding="utf-8")
        (self.revisiones / "resumen_semanal.json").write_text("{}", encoding="utf-8")
        (self.revisiones / "control_horario_mal.txt").write_text("texto", encoding="utf-8")

        (self.revisiones / "control horario minusculas 20102026.json").write_text(
            _contenido_control("2026-10-20", "Ana"), encoding="utf-8"
        )
        (self.revisiones / "CONTROL HORARIO mayusculas 21102026 (1).json").write_text(
            _contenido_control("2026-10-21", "Pedro"), encoding="utf-8"
        )

        info = cerrar_obra.controles_sin_aplicar(self.raiz, self.obra)
        nombres = [p["nombre"] for p in info["pendientes"]]
        self.assertEqual(2, len(nombres))
        self.assertIn("control horario minusculas 20102026.json", nombres)
        self.assertIn("CONTROL HORARIO mayusculas 21102026 (1).json", nombres)
        self.assertNotIn("hoja_revision_01.html", nombres)
        self.assertNotIn("resumen_semanal.json", nombres)
        self.assertNotIn("control_horario_mal.txt", nombres)

    def test_17_control_que_no_se_deja_leer_indica_situacion_especifica(self):
        # Si un fichero de control da error de lectura, se senala como 'no se puede leer (...)'.
        ficha_error = {
            "nombre": "CONTROL HORARIO inaccesible.json",
            "ruta": str(self.revisiones / "CONTROL HORARIO inaccesible.json"),
            "sha256": None,
            "fecha_nombre": None,
            "copia": 0,
            "bytes": None,
            "error": "PermissionError: Acceso denegado",
        }
        with patch.object(lector, "listar", return_value=[ficha_error]):
            info = cerrar_obra.controles_sin_aplicar(self.raiz, self.obra)
            self.assertEqual(1, len(info["pendientes"]))
            p = info["pendientes"][0]
            self.assertEqual("CONTROL HORARIO inaccesible.json", p["nombre"])
            self.assertIn("no se puede leer", p["situacion"])
            self.assertIn("PermissionError: Acceso denegado", p["situacion"])

            texto = cerrar_obra.texto_de_controles(self.obra, info)
            self.assertIn("no se puede leer", texto)
            self.assertIn("PermissionError: Acceso denegado", texto)


class TestTextoDeControles(unittest.TestCase):
    """Comprueba la generacion del mensaje informativo y de bloqueo."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = _obra_falsa(self.raiz)
        self.addCleanup(self._tmp.cleanup)

    def test_texto_vacio_si_no_hay_pendientes_ni_error(self):
        info = {"pendientes": [], "aplicados": 3, "error": None}
        texto = cerrar_obra.texto_de_controles(self.obra, info)
        self.assertEqual("", texto)

    def test_10_singular_y_plural_del_texto_y_una_linea_por_cada_fichero(self):
        # Singular: 'Queda 1 control horario'.
        info_singular = {
            "pendientes": [
                {"nombre": "CONTROL HORARIO 2026 OBRA FALSA 20102026.json", "situacion": "listo para aplicar"}
            ],
            "aplicados": 0,
            "error": None,
        }
        txt_1 = cerrar_obra.texto_de_controles(self.obra, info_singular)
        self.assertIn("Queda 1 control horario sin aplicar", txt_1)
        self.assertIn("  - «CONTROL HORARIO 2026 OBRA FALSA 20102026.json»: listo para aplicar", txt_1)
        self.assertIn("actualiza la obra falsa", txt_1)

        # Plural: 'Quedan N controles horarios' y una linea por cada uno.
        info_plural = {
            "pendientes": [
                {"nombre": "CONTROL HORARIO 1.json", "situacion": "listo para aplicar"},
                {"nombre": "CONTROL HORARIO 2.json", "situacion": "hay que mirarlo antes de aplicarlo"},
            ],
            "aplicados": 1,
            "error": None,
        }
        txt_2 = cerrar_obra.texto_de_controles(self.obra, info_plural)
        self.assertIn("Quedan 2 controles horarios sin aplicar", txt_2)
        self.assertIn("  - «CONTROL HORARIO 1.json»: listo para aplicar", txt_2)
        self.assertIn("  - «CONTROL HORARIO 2.json»: hay que mirarlo antes de aplicarlo", txt_2)
        self.assertIn("actualiza la obra falsa", txt_2)

    def test_texto_con_error_indica_prudencia_y_no_cierra(self):
        info_err = {"pendientes": [], "aplicados": 0, "error": "OSError: Permiso denegado"}
        txt = cerrar_obra.texto_de_controles(self.obra, info_err)
        self.assertIn("No se ha podido comprobar", txt)
        self.assertIn("Por prudencia no se cierra la obra", txt)


class TestFrenoCierreOrquestador(unittest.TestCase):
    """Comprueba que cerrar() frene el cierre antes de realizar ninguna mutacion."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra, self.motor, self.revisiones = _montar_entorno(self.raiz, con_revisiones=True)
        self.registro = self.motor / "registro_obras.py"
        self.adaptador = self.motor / "adaptadores" / "adaptador_falsa.py"
        self.carpeta_obra = self.raiz / "SAGARDE OBRAS ABIERTAS" / "2026 OBRA FALSA"
        self.carpeta_cerrada = self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS" / "2026 OBRA FALSA"
        self.addCleanup(self._tmp.cleanup)

    def test_08_ejecutar_con_control_sin_aplicar_aborta_sin_tocar_nada(self):
        # Con ejecutar=True, si hay controles pendientes lanza CierreAbortado y nada se modifica.
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json").write_text(
            _contenido_control("2026-10-20", "Ana"), encoding="utf-8"
        )
        bytes_registro_antes = self.registro.read_bytes()

        with self.assertRaises(cerrar_obra.CierreAbortado) as ctx:
            cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)

        self.assertIn("Queda 1 control horario sin aplicar", str(ctx.exception))
        # Verificacion estricta: nada se ha movido ni modificado.
        self.assertTrue(self.carpeta_obra.exists(), "La carpeta de la obra debe seguir en abiertas")
        self.assertEqual(bytes_registro_antes, self.registro.read_bytes(), "El registro no debe cambiar")
        self.assertTrue(self.adaptador.exists(), "El adaptador no debe moverse si aborta")
        self.assertFalse(self.carpeta_cerrada.exists(), "No debe existir carpeta en obras cerradas")

    def test_09_vista_previa_con_control_sin_aplicar_no_lanza_e_informa(self):
        # La vista previa (ejecutar=False) nunca lanza CierreAbortado: informa del bloqueo en los datos.
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json").write_text(
            _contenido_control("2026-10-20", "Ana"), encoding="utf-8"
        )
        resultado = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=False)
        self.assertFalse(resultado["movida"])
        self.assertIsNone(resultado["destino"])
        self.assertTrue(resultado["bloqueo_controles"])
        self.assertIn("CONTROL HORARIO 2026 OBRA FALSA 20102026.json", resultado["bloqueo_controles"])
        self.assertIn("actualiza la obra falsa", resultado["bloqueo_controles"])

    def test_11_error_en_listar_informa_prudencia_y_aborta_ejecucion(self):
        # Si listar lanza una excepcion, se captura, informa 'Por prudencia' y aborta al ejecutar.
        with patch.object(lector, "listar", side_effect=OSError("fallo de lectura en REVISIONES")):
            r_prev = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=False)
            self.assertIn("Por prudencia no se cierra la obra", r_prev["bloqueo_controles"])
            self.assertIn("OSError", r_prev["controles"]["error"])

            with self.assertRaises(cerrar_obra.CierreAbortado) as ctx:
                cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
            self.assertIn("Por prudencia no se cierra la obra", str(ctx.exception))

    def test_12_error_en_shas_recibidos_informa_prudencia_y_aborta_ejecucion(self):
        # Si shas_recibidos falla (traza ilegible), no se da por bueno y aborta por prudencia.
        with patch.object(po, "shas_recibidos", side_effect=OSError("traza danada")):
            r_prev = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=False)
            self.assertIn("Por prudencia no se cierra la obra", r_prev["bloqueo_controles"])
            self.assertIn("OSError", r_prev["controles"]["error"])

            with self.assertRaises(cerrar_obra.CierreAbortado) as ctx:
                cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
            self.assertIn("Por prudencia no se cierra la obra", str(ctx.exception))

    def test_13_flujo_completo_bloquea_y_al_aplicar_permite_cerrar(self):
        # Flujo real: al inicio hay un control pendiente que frena el cierre; tras aplicarlo, se cierra.
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json").write_text(
            _contenido_control("2026-10-20", "Ana"), encoding="utf-8"
        )
        with self.assertRaises(cerrar_obra.CierreAbortado):
            cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)

        _aplicar_controles(self.raiz)

        resultado = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertTrue(resultado["movida"])
        self.assertTrue(self.carpeta_cerrada.exists())
        self.assertFalse(self.carpeta_obra.exists())


class TestMainCLIControles(unittest.TestCase):
    """Comprueba la interfaz CLI main() de cerrar_obra frente a controles horarios."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra, self.motor, self.revisiones = _montar_entorno(self.raiz, con_revisiones=True)
        self.addCleanup(self._tmp.cleanup)

    def test_14_main_vista_previa_con_y_sin_pendientes(self):
        # Con control pendiente: salida contiene [NO SE PUEDE CERRAR], el fichero, no muestra --ejecutar, sale con 1.
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json").write_text(
            _contenido_control("2026-10-20", "Ana"), encoding="utf-8"
        )
        buf_bloqueo = io.StringIO()
        with patch.object(cerrar_obra, "RAIZ", self.raiz), contextlib.redirect_stdout(buf_bloqueo):
            ret_bloqueo = cerrar_obra.main(["falsa"])
        self.assertEqual(1, ret_bloqueo)
        salida_bloqueo = buf_bloqueo.getvalue()
        self.assertIn("[NO SE PUEDE CERRAR]", salida_bloqueo)
        self.assertIn("CONTROL HORARIO 2026 OBRA FALSA 20102026.json", salida_bloqueo)
        self.assertNotIn("--ejecutar", salida_bloqueo)

        # Sin controles en REVISIONES: devuelve 0, dice 'no hay ninguno en REVISIONES' y sugiere --ejecutar.
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json").unlink()
        buf_vacio = io.StringIO()
        with patch.object(cerrar_obra, "RAIZ", self.raiz), contextlib.redirect_stdout(buf_vacio):
            ret_vacio = cerrar_obra.main(["falsa"])
        self.assertEqual(0, ret_vacio)
        salida_vacio = buf_vacio.getvalue()
        self.assertNotIn("[NO SE PUEDE CERRAR]", salida_vacio)
        self.assertIn("Controles horarios: no hay ninguno en REVISIONES", salida_vacio)
        self.assertIn("--ejecutar", salida_vacio)

        # Con control ya aplicado: devuelve 0, dice '1 en REVISIONES, todos aplicados' y sugiere --ejecutar.
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json").write_text(
            _contenido_control("2026-10-20", "Ana"), encoding="utf-8"
        )
        _aplicar_controles(self.raiz)
        buf_aplicado = io.StringIO()
        with patch.object(cerrar_obra, "RAIZ", self.raiz), contextlib.redirect_stdout(buf_aplicado):
            ret_aplicado = cerrar_obra.main(["falsa"])
        self.assertEqual(0, ret_aplicado)
        salida_aplicado = buf_aplicado.getvalue()
        self.assertNotIn("[NO SE PUEDE CERRAR]", salida_aplicado)
        self.assertIn("Controles horarios: 1 en REVISIONES, todos aplicados", salida_aplicado)
        self.assertIn("--ejecutar", salida_aplicado)

    def test_15_main_ejecutar_con_pendiente_aborta_y_no_mueve(self):
        # main con --ejecutar y control pendiente: devuelve 1, imprime [ABORTADO] y la obra sigue intacta.
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json").write_text(
            _contenido_control("2026-10-20", "Ana"), encoding="utf-8"
        )
        buf = io.StringIO()
        with patch.object(cerrar_obra, "RAIZ", self.raiz), contextlib.redirect_stdout(buf):
            ret = cerrar_obra.main(["falsa", "--ejecutar"])
        self.assertEqual(1, ret)
        salida = buf.getvalue()
        self.assertIn("[ABORTADO]", salida)
        self.assertIn("CONTROL HORARIO 2026 OBRA FALSA 20102026.json", salida)

        carpeta_abierta = self.raiz / "SAGARDE OBRAS ABIERTAS" / "2026 OBRA FALSA"
        carpeta_cerrada = self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS" / "2026 OBRA FALSA"
        self.assertTrue(carpeta_abierta.exists())
        self.assertFalse(carpeta_cerrada.exists())

    def test_16_salida_main_codificable_en_cp850_y_cp1252(self):
        # Todo lo que imprime main (bloqueos, avisos, informes y abortos) debe codificarse en la consola de Windows.
        (self.revisiones / "CONTROL HORARIO 2026 OBRA FALSA 20102026.json").write_text(
            _contenido_control("2026-10-20", "Ana"), encoding="utf-8"
        )

        casos = []

        # 1. Bloqueo en vista previa
        buf1 = io.StringIO()
        with patch.object(cerrar_obra, "RAIZ", self.raiz), contextlib.redirect_stdout(buf1):
            cerrar_obra.main(["falsa"])
        casos.append(buf1.getvalue())

        # 2. Aborto con --ejecutar
        buf2 = io.StringIO()
        with patch.object(cerrar_obra, "RAIZ", self.raiz), contextlib.redirect_stdout(buf2):
            cerrar_obra.main(["falsa", "--ejecutar"])
        casos.append(buf2.getvalue())

        # 3. Vista previa con control aplicado
        _aplicar_controles(self.raiz)
        buf3 = io.StringIO()
        with patch.object(cerrar_obra, "RAIZ", self.raiz), contextlib.redirect_stdout(buf3):
            cerrar_obra.main(["falsa"])
        casos.append(buf3.getvalue())

        # 4. Error de lectura (por prudencia)
        with patch.object(lector, "listar", side_effect=OSError("fallo de lectura")):
            buf4 = io.StringIO()
            with patch.object(cerrar_obra, "RAIZ", self.raiz), contextlib.redirect_stdout(buf4):
                cerrar_obra.main(["falsa"])
            casos.append(buf4.getvalue())

        for texto in casos:
            self.assertTrue(len(texto) > 0)
            for codificacion in ("cp850", "cp1252"):
                texto.encode(codificacion)


if __name__ == "__main__":
    unittest.main()
