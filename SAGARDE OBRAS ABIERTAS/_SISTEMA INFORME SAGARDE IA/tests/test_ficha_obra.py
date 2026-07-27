# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ficha_obra
import fixtures


class TestApartados(unittest.TestCase):

    def test_crea_los_apartados_que_faltan(self):
        ficha = {'id': 'pruebas'}
        creados = ficha_obra.asegurar_apartados(ficha)
        for nombre in ficha_obra.APARTADOS:
            self.assertIn(nombre, ficha)
        self.assertIn('materiales', creados)

    def test_no_pisa_los_apartados_que_ya_existen(self):
        ficha = fixtures.ficha_minima()
        ficha['materiales'] = {'algo': 1}
        creados = ficha_obra.asegurar_apartados(ficha)
        self.assertEqual(creados, [])
        self.assertEqual(ficha['materiales'], {'algo': 1})


if __name__ == '__main__':
    unittest.main()
