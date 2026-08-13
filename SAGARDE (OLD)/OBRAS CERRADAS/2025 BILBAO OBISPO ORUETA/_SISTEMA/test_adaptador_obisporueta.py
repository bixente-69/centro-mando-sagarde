# -*- coding: utf-8 -*-
"""Pruebas de los símbolos históricos propios de Obispo Orueta."""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import adaptadores.adaptador_obisporueta as ao


class TestEstadosHistoricosObispoOrueta(unittest.TestCase):

    def test_pintura_habitaciones_usa_escala_confirmada(self):
        self.assertEqual(ao._normalizar_estado('Pintura Hab', '1'), '/')
        self.assertEqual(ao._normalizar_estado('Pintura Hab', '2'), 'M')
        self.assertEqual(ao._normalizar_estado('Pintura Hab', 'X'), 'X')

    def test_pintura_pasillos_usa_escala_confirmada(self):
        self.assertEqual(ao._normalizar_estado('Pintura Pasillos', '1'), '/')
        self.assertEqual(ao._normalizar_estado('Pintura Pasillos', '2'), 'M')
        self.assertEqual(ao._normalizar_estado('Pintura Pasillos', 'X'), 'X')

    def test_t_y_c_de_mecanismos_wc_se_conservan_de_forma_conservadora(self):
        # Uno significaba iniciado y el otro M, pero el historial disponible
        # no permite saber cuál. Ambos se dejan en "/" para no sobrevalorar.
        self.assertEqual(ao._normalizar_estado('Mecanismos WC', 'T'), '/')
        self.assertEqual(ao._normalizar_estado('Mecanismos WC', 'C'), '/')
        self.assertEqual(ao._normalizar_estado('Mecanismos WC', 'X'), 'X')


if __name__ == '__main__':
    unittest.main()
