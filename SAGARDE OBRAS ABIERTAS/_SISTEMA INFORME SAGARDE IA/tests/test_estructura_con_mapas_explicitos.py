# -*- coding: utf-8 -*-
"""Regresion de estructura HTML con mapas explicitos de portal y planta."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup


MOTOR = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.fspath(MOTOR))

import adaptar_revision_html as adaptador
import registro_obras
import validar_revision


OBRA_BARAKALDO = MOTOR.parent / '2026 BARAKALDO 104V OBRAS ESPECIALES'
HTML_BARAKALDO = (
    OBRA_BARAKALDO / 'REVISIONES'
    / 'REVISION 104V BARAKALDO OBRAS ESPECIALES 08102026.html'
)
FICHA_BARAKALDO = OBRA_BARAKALDO / 'INFORME SAGARDE IA' / 'ficha_obra.json'


def _catalogo():
    return {
        'version': 'test',
        'tajos': [
            {'id': 'tubeado'},
            {'id': 'cableado'},
        ],
        'obras': {},
    }


def _ubicaciones():
    return [
        {'id': 'A', 'tipo': 'vivienda', 'origen': 'campo'},
        {'id': 'B', 'tipo': 'vivienda', 'origen': 'campo'},
    ]


def _ficha_con_ids_ambiguos():
    """El orden natural y el estructural discrepan en portal y planta."""
    ficha = {
        'version': 1,
        'id': 'mapas',
        'modo': 'nativa',
        'identidad': {
            'nombre': 'OBRA MAPAS',
            'carpeta': 'OBRA MAPAS',
            'tipo_obra': 'viviendas',
            '_meta': {},
        },
        'estructura': {
            'bloques': [{
                'id': 'b1',
                'nombre': 'Bloque 1',
                'portales': [
                    {
                        'id': 'p10',
                        'nombre': 'Portal 10',
                        'referencia': 'Portal 10',
                        'plantas': [{
                            'id': '10',
                            'nombre': '10',
                            'orden': 10,
                            'ubicaciones': _ubicaciones(),
                        }],
                    },
                    {
                        'id': 'p2',
                        'nombre': 'Portal 2',
                        'referencia': 'Portal 2',
                        'plantas': [
                            {
                                'id': 'pb',
                                'nombre': 'PB',
                                'orden': 0,
                                'ubicaciones': _ubicaciones(),
                            },
                            {
                                'id': '1',
                                'nombre': '1',
                                'orden': 1,
                                'ubicaciones': _ubicaciones(),
                            },
                        ],
                    },
                ],
            }],
            'alias_historico': {},
            '_meta': {},
        },
        'tajos': {
            'aplicables': ['tubeado', 'cableado'],
            'detalle': [
                {
                    'id': 'tubeado',
                    'nombre': 'Tubeado',
                    'ambito': 'vivienda',
                    'propiedad': 'propio',
                    'fase': 'Interior',
                    'orden': 10,
                },
                {
                    'id': 'cableado',
                    'nombre': 'Cableado',
                    'ambito': 'vivienda',
                    'propiedad': 'propio',
                    'fase': 'Interior',
                    'orden': 20,
                },
            ],
            '_meta': {},
        },
        'estados': {},
        'revisiones': [],
        'dudas': [],
        'materiales': {},
        'documentos': {},
        'contactos': [],
    }
    for portal_id, planta_id in (('p10', '10'), ('p2', 'pb'), ('p2', '1')):
        for unidad in ('A', 'B'):
            for tajo in ('tubeado', 'cableado'):
                ficha['estados'][
                    f'{portal_id}__{planta_id}__{tajo}__{unidad}'
                ] = {'v': '?', 'f': None, 'r': None}
    return ficha


def _html(celdas):
    return '<html><body>{}</body></html>'.format(''.join(
        '<td data-k="{}" data-st="{}"></td>'.format(clave, estado)
        for clave, estado in celdas
    ))


class TestEstructuraConMapasExplicitos(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ficha = _ficha_con_ids_ambiguos()
        self.catalogo = _catalogo()
        self.mapa_portales = {'src_mapas_p1': 'p2'}
        self.mapa_plantas = {'src_mapas_p1_f1': 'pb'}

    def _escribir_html(self, celdas):
        ruta = Path(self.temporal.name) / 'REVISION MAPAS 08102026.html'
        ruta.write_text(_html(celdas), encoding='utf-8')
        return ruta

    def test_ausente_necesita_mapas_explicitos_para_retirar(self):
        ruta = self._escribir_html([
            (f'src_mapas_p1__src_mapas_p1_f1__{tajo}__{unidad}', '')
            for unidad in ('A', 'B')
            for tajo in ('tubeado', 'cableado')
        ])

        sin_mapas = adaptador.estructura_ausente_en_hoja(
            ruta, 'mapas', self.ficha, self.catalogo,
            fecha='08/10/2026')
        con_mapas = adaptador.estructura_ausente_en_hoja(
            ruta, 'mapas', self.ficha, self.catalogo,
            fecha='08/10/2026',
            portal_id_a_real=self.mapa_portales,
            planta_id_a_real=self.mapa_plantas)

        self.assertIsNotNone(sin_mapas['no_fiable'])
        self.assertEqual(sin_mapas['unidades'], [])
        self.assertEqual(sin_mapas['tajos'], [])
        self.assertIsNone(con_mapas['no_fiable'])
        self.assertEqual(
            [(item['portal_id'], item['planta_id'], item['unidad'])
             for item in con_mapas['unidades']],
            [('p2', '1', 'A'), ('p2', '1', 'B')],
        )
        self.assertEqual(con_mapas['tajos'], [])

    def test_nueva_extiende_derivados_y_el_mapa_gana_a_la_ambiguedad(self):
        ruta = self._escribir_html([
            ('src_mapas_p1__src_mapas_p1_f1__tubeado__A', ''),
            ('src_mapas_p1__src_mapas_p1_f1__tubeado__C', ''),
            ('src_mapas_p1__src_mapas_p1_f1__cableado__C', ''),
        ])

        sin_mapas = adaptador.estructura_nueva_en_hoja(
            ruta, 'mapas', self.ficha, self.catalogo)
        con_mapas = adaptador.estructura_nueva_en_hoja(
            ruta, 'mapas', self.ficha, self.catalogo,
            portal_id_a_real=self.mapa_portales,
            planta_id_a_real=self.mapa_plantas)

        self.assertEqual(sin_mapas, [])
        self.assertEqual(con_mapas, [{
            'edificio': 'Portal 2',
            'planta': 'PB',
            'planta_id': 'pb',
            'portal_id': 'p2',
            'unidad': 'C',
            'tajos': ['tubeado', 'cableado'],
            'tajos_sin_traducir': [],
        }])

    @unittest.skipUnless(
        HTML_BARAKALDO.is_file() and FICHA_BARAKALDO.is_file(),
        'no estan disponibles la hoja y la ficha reales de Barakaldo',
    )
    def test_barakaldo_real_y_copia_sin_planta_2_13(self):
        with FICHA_BARAKALDO.open(encoding='utf-8') as fichero:
            ficha = json.load(fichero)
        obra = next(
            item for item in registro_obras.OBRAS
            if item['id'] == 'barakaldo'
        )
        catalogo = validar_revision.cargar_catalogo_tajos()
        mapas = {
            'portal_id_a_real': obra.get('mapa_portales_revision_html'),
            'planta_id_a_real': obra.get('mapa_plantas_revision_html'),
            'tarea_id_a_real': obra.get('mapa_tajos_revision_html'),
        }

        completa = adaptador.estructura_ausente_en_hoja(
            HTML_BARAKALDO, 'barakaldo', ficha, catalogo,
            fecha='08/10/2026', **mapas)

        self.assertIsNone(completa['no_fiable'])
        self.assertEqual(completa['unidades'], [])
        self.assertEqual(completa['tajos'], [])

        with HTML_BARAKALDO.open(encoding='utf-8') as fichero:
            soup = BeautifulSoup(fichero.read(), 'html.parser')
        celda_213 = soup.find(attrs={
            'data-k': lambda valor: (
                valor is not None and '__f_muzjscxe_49__' in valor),
        })
        self.assertIsNotNone(celda_213)
        tabla_213 = celda_213.find_parent('table')
        celdas_213 = tabla_213.find_all(attrs={
            'data-k': lambda valor: (
                valor is not None and '__f_muzjscxe_49__' in valor),
        })
        self.assertGreater(len(celdas_213), 0)
        for celda in celdas_213:
            celda.decompose()

        copia = Path(self.temporal.name) / HTML_BARAKALDO.name
        copia.write_text(str(soup), encoding='utf-8')
        sin_213 = adaptador.estructura_ausente_en_hoja(
            copia, 'barakaldo', ficha, catalogo,
            fecha='08/10/2026', **mapas)

        self.assertIsNone(sin_213['no_fiable'])
        self.assertEqual(
            [(item['portal_id'], item['planta_id'], item['unidad'])
             for item in sin_213['unidades']],
            [('p2', '2.13', 'A'), ('p2', '2.13', 'B')],
        )
        self.assertEqual(sin_213['tajos'], [])


if __name__ == '__main__':
    unittest.main()
