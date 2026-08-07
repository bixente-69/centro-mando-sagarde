# -*- coding: utf-8 -*-
"""Regresion para la guarda de carpetas tecnicas de auditor_sagarde.py.

Hasta el commit 1c11e97 (Tarea 3, 07/08/2026) la linea
`"_SISTEMA" in f.parts or "INFORME SAGARDE IA" in str(f)` ya filtraba los
tres nombres reales, pero solo gracias a la SEGUNDA clausula (substring
sobre la ruta completa). La primera, `"_SISTEMA" in f.parts`, exige que un
tramo de ruta sea EXACTAMENTE '_SISTEMA' y no caso nunca con nada en el
arbol real porque la carpeta se llama '_SISTEMA INFORME SAGARDE IA'.

Que SI detectan las 5 pruebas de comportamiento de mas abajo (Grupo A):
que alguien deje de reconocer alguno de los tres nombres -en particular
'_SISTEMA' a secas, la norma nueva del 07/08- al tocar CARPETAS_SISTEMA o
la forma en que se comprueban los tramos de ruta.

Que NO detectan esas 5: revertir el fichero ENTERO al codigo anterior a
1c11e97. Comprobado a mano (ver task-3-report.md, ronda 1): la guarda vieja
de dos clausulas con "or" tambien filtra correctamente los tres nombres via
su segunda clausula, asi que las 5 pruebas de comportamiento pasarian igual
contra ese codigo -no distinguen "arreglado" de "funciona por accidente".
Por eso el Grupo B es una sexta prueba, deliberadamente redundante con el
diagnostico de comportamiento: comprueba que la constante CARPETAS_SISTEMA
existe. Esa constante no existe en el codigo pre-fix, asi que revertir el
fichero entero SI la hace fallar.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(SISTEMA_DIR))
sys.path.insert(0, SISTEMA_DIR)
sys.path.insert(0, os.path.join(SISTEMA_DIR, 'adaptadores'))
sys.path.insert(0, os.path.join(ROOT_DIR, '_MOTOR_SAGARDE', 'scripts'))

import auditor_sagarde


class TestGuardaCarpetasSistema(unittest.TestCase):
    """Grupo A: comportamiento de audit_obras_abiertas() ante carpetas
    tecnicas. No distinguen el fix de la guarda vieja (ver docstring del
    modulo) - fijan el comportamiento correcto hacia adelante."""

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


class TestConstanteCarpetasSistema(unittest.TestCase):
    """Grupo B: la asercion barata que SI distingue el fix de un revert
    completo del fichero. CARPETAS_SISTEMA no existe en el codigo anterior
    a 1c11e97 (esa version solo tiene el 'or' de dos clausulas inline)."""

    def test_la_constante_CARPETAS_SISTEMA_existe(self):
        self.assertTrue(
            hasattr(auditor_sagarde, "CARPETAS_SISTEMA"),
            "CARPETAS_SISTEMA no existe: el fichero parece revertido al "
            "codigo anterior a la Tarea 3 (commit 1c11e97).")

    def test_CARPETAS_SISTEMA_reconoce_los_tres_nombres(self):
        self.assertEqual(
            auditor_sagarde.CARPETAS_SISTEMA,
            {"_SISTEMA", "_SISTEMA INFORME SAGARDE IA", "INFORME SAGARDE IA"})


if __name__ == "__main__":
    unittest.main()
