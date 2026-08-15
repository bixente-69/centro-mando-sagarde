# -*- coding: utf-8 -*-
"""Fotovoltaica no lleva codigo propio en el priorizador: al ser un tajo
'propio' sin dependencias, tiene que comportarse igual que cualquier otro
tajo de esa forma. Esta prueba demuestra que el catalogo (Task 1) basta,
sin tocar priorizador_trabajos.py."""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import fixtures
from priorizador_trabajos import priorizar_ficha


def _ficha_con_fotovoltaica(estado):
    ficha = fixtures.ficha_minima()
    ficha['tajos']['aplicables'].append('fotovoltaica')
    ficha['tajos']['detalle'].append({
        'id': 'fotovoltaica', 'nombre': 'Fotovoltaica',
    })
    ficha['estados'] = {
        'p1__pb__fotovoltaica__A': {'v': estado, 'f': '15/08/2026', 'r': 1},
    }
    ficha['revisiones'] = [{'fecha': '15/08/2026', 'numero': 1}]
    return ficha


class TestFotovoltaicaEnPriorizador(unittest.TestCase):

    def test_sin_marca_sale_viable_no_bloqueada(self):
        ficha = _ficha_con_fotovoltaica('')
        resultado = priorizar_ficha(ficha, obra='OBRA DE PRUEBAS')
        items = [i for i in resultado['detalle_items']
                 if i['tarea_id'] == 'fotovoltaica']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['categoria'], 'VIABLE')

    def test_en_x_se_computa_terminado(self):
        ficha = _ficha_con_fotovoltaica('X')
        resultado = priorizar_ficha(ficha, obra='OBRA DE PRUEBAS')
        items = [i for i in resultado['detalle_items']
                 if i['tarea_id'] == 'fotovoltaica']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['categoria'], 'TERMINADO')

    def test_sembrar_reglas_rellena_orden_y_ambito_desde_el_catalogo(self):
        ficha = _ficha_con_fotovoltaica('')
        priorizar_ficha(ficha, obra='OBRA DE PRUEBAS')
        detalle = ficha['tajos']['detalle']
        tajo = next(t for t in detalle if t['id'] == 'fotovoltaica')
        self.assertEqual(tajo['orden'], 306)
        self.assertEqual(tajo['ambito'], 'edificio')
        self.assertEqual(tajo['deps'], [])


if __name__ == '__main__':
    unittest.main()
