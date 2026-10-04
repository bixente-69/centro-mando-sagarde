# -*- coding: utf-8 -*-
"""Regresiones de la vista de zonas especiales del informe ejecutivo."""

import copy
import os
import sys
import unittest


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

import ficha_obra
import fixtures
import generar_todos


def _ficha_con_vivienda_medida_y_zesp_desconocida():
    ficha = fixtures.ficha_minima()
    portal = ficha['estructura']['bloques'][0]['portales'][0]
    portal['plantas'].append({
        'id': ficha_obra.ID_PLANTA_ZONAS_ESPECIALES,
        'nombre': ficha_obra.NOMBRE_PLANTA_ZONAS_ESPECIALES,
        'orden': ficha_obra.ORDEN_PLANTA_ZONAS_ESPECIALES,
        'ubicaciones': [
            {'id': 'riti', 'tipo': 'cuarto_tecnico', 'nombre': 'RITI'},
            {'id': 'cubierta', 'tipo': 'cubierta', 'nombre': 'Cubierta'},
        ],
    })
    ficha['estados'].update({
        'p1__pb__tubeado__A': {
            'v': 'X', 'f': '04/10/2026', 'r': 'rev_04102026',
        },
        'p1__zesp__tubeado__riti': {'v': '?', 'f': None, 'r': None},
        'p1__zesp__cableado__riti': {'v': '?', 'f': None, 'r': None},
        'p1__zesp__tubeado__cubierta': {'v': 'N', 'f': None, 'r': None},
        'p1__zesp__cableado__cubierta': {'v': 'N', 'f': None, 'r': None},
    })
    ficha['revisiones'] = [{
        'id': 'rev_04102026', 'fecha': '04/10/2026',
    }]
    return ficha


class TestSnapshotZonasEspecialesParaInforme(unittest.TestCase):
    def test_con_vivienda_medida_y_zesp_desconocida_el_informe_presenta_pendientes(self):
        ficha = _ficha_con_vivienda_medida_y_zesp_desconocida()
        estados_reales = copy.deepcopy(ficha['estados'])

        self.assertTrue(ficha_obra.snapshot_desde_ficha(ficha))
        self.assertEqual(generar_todos.snapshot_zonas_especiales(ficha), [])

        snapshot = generar_todos.snapshot_zonas_especiales_para_informe(ficha)

        self.assertEqual(len(snapshot), 2)
        self.assertEqual({fila['unit'] for fila in snapshot}, {'riti'})
        self.assertEqual({fila['status'] for fila in snapshot}, {''})
        self.assertEqual(ficha['estados'], estados_reales)

    def test_con_zesp_medido_conserva_el_snapshot_real(self):
        ficha = _ficha_con_vivienda_medida_y_zesp_desconocida()
        ficha['estados']['p1__zesp__tubeado__riti'] = {
            'v': 'X', 'f': '04/10/2026', 'r': 'rev_04102026',
        }
        snapshot_real = generar_todos.snapshot_zonas_especiales(ficha)

        snapshot_informe = (
            generar_todos.snapshot_zonas_especiales_para_informe(ficha))

        self.assertEqual(snapshot_informe, snapshot_real)
        self.assertEqual(len(snapshot_informe), 1)
        self.assertEqual(snapshot_informe[0]['status'], 'X')


if __name__ == '__main__':
    unittest.main()
