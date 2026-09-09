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


class TestFechaBaseSnapshot(unittest.TestCase):
    """La etiqueta de fecha del snapshot no puede quedarse desfasada.

    Bug real encontrado el 09/09/2026: la ficha de Bolueta ya tenia una
    revision del 09/09 (escrita via HTML, sin PDF que el adaptador viera),
    pero el informe ejecutivo seguia imprimiendo 'Datos: 31/08/2026' -- la
    ultima fecha que conocia el adaptador -- aunque el snapshot usado SI
    era el estado actual y completo de la ficha.
    """

    def test_prefiere_la_fecha_mas_reciente_aunque_el_adaptador_no_la_conozca(self):
        self.assertEqual(
            gie._fecha_base_snapshot('31/08/2026', '09/09/2026'),
            '09/09/2026')

    def test_conserva_la_fecha_del_adaptador_si_es_la_mas_reciente(self):
        self.assertEqual(
            gie._fecha_base_snapshot('31/08/2026', '24/08/2026'),
            '31/08/2026')

    def test_comparacion_no_es_alfabetica(self):
        # '09/09/2026' < '31/08/2026' como texto plano (el '0' inicial
        # gana); la comparacion real de fechas tiene que dar lo contrario.
        self.assertGreater(
            gie._fecha_ordenable('09/09/2026'),
            gie._fecha_ordenable('31/08/2026'))

    def test_sin_fecha_de_ficha_usa_la_del_adaptador(self):
        self.assertEqual(
            gie._fecha_base_snapshot('31/08/2026', ''), '31/08/2026')

    def test_fecha_de_adaptador_invalida_usa_la_de_la_ficha(self):
        self.assertEqual(
            gie._fecha_base_snapshot('', '09/09/2026'), '09/09/2026')


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
