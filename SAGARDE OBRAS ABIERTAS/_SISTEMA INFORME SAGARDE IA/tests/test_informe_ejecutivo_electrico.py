# -*- coding: utf-8 -*-
'''Contrato del informe ejecutivo eléctrico basado en la base de obra.'''
import os
import sys
import unittest


SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(SISTEMA_DIR))
sys.path.insert(0, SISTEMA_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'scripts'))

import generar_informe_ejecutivo as gie


class TestAlcanceSagarde(unittest.TestCase):

    def setUp(self):
        self.meta = {
            'tubeado interior': {'id': 'tubeado', 'propiedad': 'propio'},
            'tabicado': {'id': 'tabicado', 'propiedad': 'externo'},
            'suelo radiante': {'id': 'suelo_radiante', 'propiedad': 'coordinacion'},
        }

    def test_el_kpi_excluye_tajos_no_sagarde(self):
        snapshot = [
            {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
             'unit': 'A', 'status': 'M'},
            {'task': 'Tabicado', 'building': 'P1', 'floor': '1',
             'unit': 'A', 'status': 'X'},
            {'task': 'Suelo radiante', 'building': 'P1', 'floor': '1',
             'unit': 'A', 'status': 'X'},
        ]
        propios = gie._filtrar_snapshot_sagarde(snapshot, self.meta)
        self.assertEqual([r['task'] for r in propios], ['Tubeado interior'])

    def test_el_filtro_por_portal_se_aplica_al_alcance_propio(self):
        snapshot = [
            {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
             'unit': 'A', 'status': 'X'},
            {'task': 'Tubeado interior', 'building': 'P2', 'floor': '1',
             'unit': 'A', 'status': 'M'},
        ]
        propios = gie._filtrar_snapshot_sagarde(snapshot, self.meta, {'P2'})
        self.assertEqual(len(propios), 1)
        self.assertEqual(propios[0]['building'], 'P2')

    def test_la_serie_historica_tambien_es_sagarde_only(self):
        historial = [
            ('01/08/2026', [
                {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
                 'unit': 'A', 'status': ''},
                {'task': 'Tabicado', 'building': 'P1', 'floor': '1',
                 'unit': 'A', 'status': 'X'},
            ]),
            ('08/08/2026', [
                {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
                 'unit': 'A', 'status': 'X'},
                {'task': 'Tabicado', 'building': 'P1', 'floor': '1',
                 'unit': 'A', 'status': 'X'},
            ]),
        ]
        serie = gie._serie_avance_sagarde(historial, self.meta)
        self.assertEqual([p['pct'] for p in serie], [0.0, 100.0])
        self.assertEqual([p['total'] for p in serie], [1, 1])


class TestCondicionantesSagarde(unittest.TestCase):

    def test_resume_solo_dependencias_incumplidas_de_tajos_propios(self):
        prioridades = {'detalle_items': [{
            'tarea_id': 'mecanizado',
            'trabajo': 'Mecanizado eléctrico',
            'propiedad': 'propio',
            'categoria': 'BLOQUEADO',
            'edificio': 'P1',
            'planta': '2',
            'dependencias_detalle': [
                {'id': 'pintura_primera', 'nombre': 'Pintura primera',
                 'estado': 'Pendiente', 'cumplida': False},
                {'id': 'doblar_cajas', 'nombre': 'Doblar cajas',
                 'estado': 'X', 'cumplida': True},
            ],
        }]}
        metadatos = {
            'pintura_primera': {'propiedad': 'externo'},
            'doblar_cajas': {'propiedad': 'propio'},
        }
        bloqueos = gie._bloqueadores_sagarde(prioridades, metadatos)
        self.assertEqual(len(bloqueos), 1)
        self.assertEqual(bloqueos[0]['trabajo'], 'Pintura primera')
        self.assertEqual(bloqueos[0]['propiedad'], 'externo')
        self.assertEqual(bloqueos[0]['afecta_celdas'], 1)
        self.assertEqual(bloqueos[0]['tajos_sagarde'], {'Mecanizado eléctrico'})


if __name__ == '__main__':
    unittest.main()
