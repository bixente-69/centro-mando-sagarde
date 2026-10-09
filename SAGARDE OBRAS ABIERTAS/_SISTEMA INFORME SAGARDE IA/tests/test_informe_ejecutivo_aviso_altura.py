# -*- coding: utf-8 -*-
"""Regresiones del aviso final de altura del informe ejecutivo."""

import io
import os
import sys
import unittest
from contextlib import redirect_stdout


SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(SISTEMA_DIR))
sys.path.insert(0, SISTEMA_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'scripts'))

from reportlab.lib.units import mm
from reportlab.platypus import Spacer

import generar_informe_ejecutivo as gie


class TestAvisoAlturaInformeEjecutivo(unittest.TestCase):

    def _ajustar_y_capturar(self, alto_necesario_mm):
        salida = io.StringIO()
        with redirect_stdout(salida):
            ajuste = gie._ajustar_pagina(
                lambda _escala: [Spacer(1, alto_necesario_mm * mm)],
                ancho=100 * mm,
                alto=100 * mm,
                etiqueta='fixture de altura',
                ocupacion_max=.96,
            )
        return ajuste, salida.getvalue()

    def test_si_supera_el_margen_pero_cabe_en_la_pagina_lo_dice(self):
        ajuste, aviso = self._ajustar_y_capturar(98)

        self.assertTrue(ajuste['forzado'])
        self.assertIn('[AVISO INFORME EJECUTIVO]', aviso)
        self.assertIn('limite de ocupacion: 96.0 mm (96.0%)', aviso)
        self.assertIn('98.0 mm necesarios', aviso)
        self.assertIn('altura total de la pagina: 100.0 mm', aviso)
        self.assertIn('CABE en la pagina fisica', aviso)
        self.assertIn(
            'Se genera igualmente; no se conserva un PDF antiguo en silencio.',
            aviso,
        )

    def test_si_supera_la_altura_fisica_dice_que_no_cabe(self):
        ajuste, aviso = self._ajustar_y_capturar(101)

        self.assertTrue(ajuste['forzado'])
        self.assertIn('[AVISO INFORME EJECUTIVO]', aviso)
        self.assertIn('limite de ocupacion: 96.0 mm (96.0%)', aviso)
        self.assertIn('101.0 mm necesarios', aviso)
        self.assertIn('altura total de la pagina: 100.0 mm', aviso)
        self.assertIn('NO CABE en la pagina fisica', aviso)
        self.assertIn(
            'Se genera igualmente; no se conserva un PDF antiguo en silencio.',
            aviso,
        )


if __name__ == '__main__':
    unittest.main()
