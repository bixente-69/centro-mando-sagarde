# -*- coding: utf-8 -*-
"""Pruebas del adaptador aislado HTML -> REVISION_NORMALIZADA."""
import copy
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import adaptar_revision_html as adaptador
import fixtures
import validar_revision as validador


def _catalogo():
    return {
        'version': 'test',
        'tajos': [
            {'id': 'tubeado'},
            {'id': 'cableado'},
            {'id': 'montante_electrica'},
        ],
        'obras': {},
    }


def _html(celdas):
    return '<html><body>{}</body></html>'.format(''.join(
        '<td data-k="{}" data-st="{}"></td>'.format(clave, estado)
        for clave, estado in celdas
    ))


class TestAdaptarRevisionHtml(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ficha = fixtures.ficha_minima()
        self.catalogo = _catalogo()

    def _escribir(self, contenido, nombre='REVISION PRUEBAS 25082026.html'):
        ruta = os.path.join(self.temporal.name, nombre)
        with open(ruta, 'w', encoding='utf-8') as fichero:
            fichero.write(contenido)
        return ruta

    def _construir(self, ruta, ficha=None, **kwargs):
        return adaptador.construir_revision_normalizada_html(
            ruta,
            'pruebas',
            ficha if ficha is not None else self.ficha,
            self.catalogo,
            **kwargs,
        )

    def test_traduce_ids_src_tarea_corta_y_vivienda_sin_perder_case(self):
        ruta = self._escribir(_html([
            ('src_pruebas_p1__src_pruebas_p1_f1__tube-viv__A', 'X'),
            ('src_pruebas_p1__src_pruebas_p1_f2__cableado__B', 'M'),
        ]))

        with patch.object(
                adaptador.lector_hoja_tajos_html,
                'extraer_pares',
                wraps=adaptador.lector_hoja_tajos_html.extraer_pares) as extraer:
            revision = self._construir(ruta)

        extraer.assert_called_once_with(os.path.abspath(ruta))
        self.assertEqual(
            [celda['clave'] for celda in revision['celdas']],
            ['p1__pb__tubeado__A', 'p1__1__cableado__B'],
        )
        self.assertEqual(
            [celda['estado_leido'] for celda in revision['celdas']],
            ['X', 'M'],
        )
        self.assertEqual(revision['metadata']['avisos'], [])
        self.assertTrue(revision['metadata']['hoja_usada'])
        self.assertEqual(revision['origen'], 'html_digital')

    def test_ids_largos_y_cortos_del_generador_resuelven_al_catalogo(self):
        ruta = self._escribir(_html([
            ('src_pruebas_p1__src_pruebas_p1_f1__montante_electrica__A', 'X'),
            ('src_pruebas_p1__src_pruebas_p1_f1__mont-elec__B', '/'),
        ]))

        revision = self._construir(ruta)

        self.assertEqual(
            [celda['clave'] for celda in revision['celdas']],
            ['p1__pb__montante_electrica__A',
             'p1__pb__montante_electrica__B'],
        )

    def test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas(self):
        ruta = self._escribir(_html([
            ('src_pruebas_p1__src_pruebas_p1_f1__tubeado__A', 'X'),
            ('src_pruebas_p9__src_pruebas_p9_f1__tubeado__A', 'X'),
            ('src_pruebas_p1__src_pruebas_p1_f9__tubeado__A', 'M'),
            ('src_pruebas_p1__src_pruebas_p1_f1__tajo-inexistente__B', '/'),
        ]))

        revision = self._construir(ruta)
        resultado = validador.validar(revision, self.ficha, self.catalogo)

        self.assertEqual(len(revision['celdas']), 1)
        self.assertEqual(len(revision['metadata']['avisos']), 3)
        self.assertTrue(any('portal desconocido' in aviso
                            for aviso in revision['metadata']['avisos']))
        self.assertTrue(any('planta desconocida' in aviso
                            for aviso in revision['metadata']['avisos']))
        self.assertTrue(any('tajo desconocido' in aviso
                            for aviso in revision['metadata']['avisos']))
        self.assertTrue(resultado['aplicable'])
        self.assertEqual(resultado['resumen']['aceptadas'], 1)
        self.assertEqual(resultado['avisos'], revision['metadata']['avisos'])

    def test_revision_id_es_determinista_y_reutiliza_generar_revision_id(self):
        ruta = self._escribir(_html([
            ('src_pruebas_p1__src_pruebas_p1_f1__tubeado__A', 'X'),
        ]))

        primera = self._construir(ruta)
        segunda = self._construir(ruta)

        esperado = validador.generar_revision_id(
            'pruebas', '25/08/2026', 'html_digital', os.path.abspath(ruta))
        self.assertEqual(primera['revision_id'], segunda['revision_id'])
        self.assertEqual(primera['revision_id'], esperado)

    def test_fecha_se_extrae_del_nombre_con_formato_ddmmaaaa(self):
        ruta = self._escribir(
            _html([('src_pruebas_p1__src_pruebas_p1_f1__tubeado__A', 'X')]),
            nombre='REVISION OBRA 03092026 copia.html',
        )

        revision = self._construir(ruta)

        self.assertEqual(revision['fecha'], '03/09/2026')

    def test_nombre_sin_fecha_no_inventa_una(self):
        ruta = self._escribir(_html([]), nombre='REVISION SIN FECHA.html')

        with self.assertRaisesRegex(ValueError, 'DDMMAAAA'):
            self._construir(ruta)

    def test_n_se_conserva_para_que_la_descarte_el_validador(self):
        ruta = self._escribir(_html([
            ('src_pruebas_p1__src_pruebas_p1_f1__tubeado__A', 'N'),
        ]))

        revision = self._construir(ruta)
        resultado = validador.validar(revision, self.ficha, self.catalogo)

        self.assertEqual(revision['celdas'][0]['estado_leido'], 'N')
        self.assertEqual(resultado['aceptadas'][0]['accion'], 'descartar')

    def test_alias_historico_impreso_vuelve_al_id_canonico(self):
        ficha = copy.deepcopy(self.ficha)
        ficha['estructura']['alias_historico'] = {'p1__pb__A': 'A2'}
        ruta = self._escribir(_html([
            ('src_pruebas_p1__src_pruebas_p1_f1__tubeado__A2', 'X'),
        ]))

        revision = self._construir(ruta, ficha=ficha)

        self.assertEqual(revision['celdas'][0]['clave'], 'p1__pb__tubeado__A')

    def test_orden_ambiguo_no_se_adivina_y_acepta_mapa_explicito(self):
        ficha = copy.deepcopy(self.ficha)
        portal_10 = ficha['estructura']['bloques'][0]['portales'][0]
        portal_10['id'] = 'p10'
        portal_10['nombre'] = 'Portal 10'
        portal_10['referencia'] = 'Portal 10'
        portal_2 = copy.deepcopy(portal_10)
        portal_2['id'] = 'p2'
        portal_2['nombre'] = 'Portal 2'
        portal_2['referencia'] = 'Portal 2'
        ficha['estructura']['bloques'][0]['portales'] = [portal_10, portal_2]
        ruta = self._escribir(_html([
            ('src_pruebas_p1__src_pruebas_p1_f1__tubeado__A', 'X'),
        ]))

        sin_mapa = self._construir(ruta, ficha=ficha)
        con_mapa = self._construir(
            ruta,
            ficha=ficha,
            portal_id_a_real={'src_pruebas_p1': 'p2'},
        )

        self.assertEqual(sin_mapa['celdas'], [])
        self.assertIn('portal ambiguo', sin_mapa['metadata']['avisos'][0])
        self.assertEqual(
            con_mapa['celdas'][0]['clave'], 'p2__pb__tubeado__A')


if __name__ == '__main__':
    unittest.main()
