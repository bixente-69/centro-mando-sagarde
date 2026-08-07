# -*- coding: utf-8 -*-
"""Regresion para la guarda de carpetas tecnicas de auditor_sagarde.py.

Hasta el 07/08/2026 la linea `"_SISTEMA" in f.parts or "INFORME SAGARDE IA"
in str(f)` solo filtraba de verdad por la segunda mitad: la carpeta real se
llama '_SISTEMA INFORME SAGARDE IA' y '"_SISTEMA" in f.parts' exige que un
tramo de ruta sea EXACTAMENTE '_SISTEMA', cosa que no ocurria en ningun
fichero real (ver Tarea 3 del plan 2026-08-07-jerarquia-sistema-entorno).

Esta prueba fija el comportamiento correcto para los tres nombres que debe
reconocer CARPETAS_SISTEMA -incluido el caso '_SISTEMA' a secas, la norma
nueva- y, con un control fuera de esas carpetas, demuestra que la propia
prueba SI se entera si alguien vuelve a romper el filtro.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MOTOR_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MOTOR_DIR))
sys.path.insert(0, str(MOTOR_DIR / "scripts"))

import auditor_sagarde


class TestGuardaCarpetasSistema(unittest.TestCase):
    """audit_obras_abiertas() no debe generar avisos por ficheros que
    cuelguen de una carpeta tecnica reconocida."""

    def _auditar_fichero_en(self, *carpetas_tecnicas):
        """Crea 'SAGARDE OBRAS ABIERTAS/OBRA PRUEBA/<carpetas_tecnicas>/
        REVISION SIN FECHA.docx' en un directorio temporal y audita."""
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            destino = raiz / "SAGARDE OBRAS ABIERTAS" / "OBRA PRUEBA"
            for carpeta in carpetas_tecnicas:
                destino = destino / carpeta
            destino.mkdir(parents=True)
            (destino / "REVISION SIN FECHA.docx").write_bytes(b"contenido")
            with patch.object(auditor_sagarde, "ROOT", raiz):
                return auditor_sagarde.audit_obras_abiertas()

    def test_carpeta_SISTEMA_a_secas_se_filtra(self):
        # El caso que la Tarea 3 pide demostrar explicitamente: un tramo de
        # ruta llamado EXACTAMENTE '_SISTEMA' (la norma nueva del 07/08,
        # todavia sin ficheros reales dentro de SAGARDE OBRAS ABIERTAS).
        self.assertEqual(self._auditar_fichero_en("_SISTEMA"), [])

    def test_carpeta_nombre_real_se_filtra(self):
        # El alias que de verdad existe hoy en el repo.
        self.assertEqual(
            self._auditar_fichero_en("_SISTEMA INFORME SAGARDE IA"), [])

    def test_carpeta_alias_por_obra_se_filtra(self):
        # El alias historico por obra (ej. '2025 GERNIKA 32V/INFORME SAGARDE IA').
        self.assertEqual(self._auditar_fichero_en("INFORME SAGARDE IA"), [])

    def test_carpeta_tecnica_anidada_tambien_se_filtra(self):
        # Un fichero varios niveles por debajo de la carpeta tecnica tambien
        # debe quedar cubierto (rglob desciende, la guarda mira todo f.parts).
        self.assertEqual(
            self._auditar_fichero_en("_SISTEMA", "sub", "otra"), [])

    def test_control_fuera_de_carpeta_tecnica_si_genera_aviso(self):
        # Mutacion manual: el mismo fichero, sin ninguna carpeta tecnica de
        # por medio, SI debe producir aviso. Si este control tambien saliera
        # en blanco, las pruebas de arriba no probarian nada (el auditor
        # podria estar ignorando la obra entera por otro motivo).
        issues = self._auditar_fichero_en()
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["codigo"], "NOMBRE_FECHA_INVALIDA")


if __name__ == "__main__":
    unittest.main()
