# -*- coding: utf-8 -*-
"""Paridad del adaptador PDF digital con ``TestAplicarDigital``."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import adaptar_revision_pdf_digital as adaptador
import aplicar_revision
import fixtures
import leer_hoja_marcada as lector
import validar_revision as validador


FECHA = '24/08/2026'
REVISION_ANTIGUA = 'rev_24082026'


def _catalogo():
    return {
        'version': 'test',
        'tajos': [{'id': 'tubeado'}, {'id': 'cableado'}],
        'obras': {},
    }


def _ficha(estados=None):
    ficha = fixtures.ficha_minima()
    ficha['estados'] = {
        clave: {'v': valor, 'f': '27/07/2026', 'r': 'rev_27072026'}
        for clave, valor in (estados or {}).items()
    }
    return ficha


def _valores(estados):
    return {
        clave: registro.get('v')
        for clave, registro in estados.items()
    }


class TestAdaptarRevisionPdfDigital(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta_pdf = os.path.join(
            self.temporal.name, 'REVISION PRUEBAS 24082026.pdf')
        with open(self.ruta_pdf, 'wb') as fichero:
            fichero.write(b'%PDF-1.4\ncontenido sintetico\n%%EOF\n')
        self.catalogo = _catalogo()

    def _revision(self, ficha, impresos, fecha=FECHA):
        with patch.object(
                adaptador.leer_hoja_marcada,
                'estados_impresos', return_value=dict(impresos)) as leer:
            revision = adaptador.construir_revision_normalizada_pdf_digital(
                self.ruta_pdf, 'pruebas', ficha, fecha)
        leer.assert_called_once_with(
            os.path.abspath(self.ruta_pdf), {'id': 'pruebas'}, ficha)
        return revision

    def _camino_nuevo(self, ficha, impresos):
        revision = self._revision(ficha, impresos)
        validacion = validador.validar(revision, ficha, self.catalogo)
        aplicacion = aplicar_revision.apply_revision(
            revision, ficha, self.catalogo, dry_run=False)
        return revision, validacion, aplicacion

    def test_una_celda_marcada_avanza_con_la_misma_decision_final(self):
        ficha = _ficha({'p1__pb__tubeado__A': 'P'})
        impresos = {'p1__pb__tubeado__A': 'X'}

        estados_antiguos, cambios_antiguos = lector.aplicar_digital(
            ficha, impresos, FECHA, REVISION_ANTIGUA)
        _revision, validacion, aplicacion = self._camino_nuevo(
            ficha, impresos)

        self.assertTrue(validacion['aplicable'])
        self.assertEqual(validacion['resumen']['cambios'], 1)
        self.assertEqual(cambios_antiguos,
                         [('p1__pb__tubeado__A', 'P', 'X')])
        self.assertEqual(
            _valores(aplicacion['ficha_actualizada']['estados']),
            _valores(estados_antiguos),
        )

    def test_lo_que_no_imprime_marca_no_se_toca_en_ningun_camino(self):
        ficha = _ficha({
            'p1__pb__tubeado__A': 'P',
            'p1__pb__tubeado__B': '?',
        })
        impresos = {'p1__pb__tubeado__A': 'X'}

        estados_antiguos, cambios_antiguos = lector.aplicar_digital(
            ficha, impresos, FECHA, REVISION_ANTIGUA)
        revision, validacion, aplicacion = self._camino_nuevo(ficha, impresos)

        self.assertEqual(len(revision['celdas']), 1)
        self.assertEqual(validacion['resumen']['cambios'], 1)
        self.assertEqual(cambios_antiguos,
                         [('p1__pb__tubeado__A', 'P', 'X')])
        self.assertEqual(
            _valores(aplicacion['ficha_actualizada']['estados']),
            _valores(estados_antiguos),
        )
        self.assertEqual(
            aplicacion['ficha_actualizada']['estados'][
                'p1__pb__tubeado__B']['v'], '?')

    def test_remarcar_lo_mismo_no_es_un_cambio_en_ningun_camino(self):
        ficha = _ficha({'p1__pb__tubeado__A': 'X'})
        impresos = {'p1__pb__tubeado__A': 'X'}

        estados_antiguos, cambios_antiguos = lector.aplicar_digital(
            ficha, impresos, FECHA, REVISION_ANTIGUA)
        _revision, validacion, aplicacion = self._camino_nuevo(
            ficha, impresos)

        self.assertEqual(cambios_antiguos, [])
        self.assertEqual(validacion['resumen']['cambios'], 0)
        self.assertEqual(validacion['aceptadas'][0]['accion'], 'conservar')
        self.assertEqual(
            _valores(aplicacion['ficha_actualizada']['estados']),
            _valores(estados_antiguos),
        )

    def test_discrepancia_documentada_si_falta_el_registro_de_estado(self):
        """El lector antiguo aborta; el motor nuevo crea una celda estructural.

        No se declara una falsa paridad: esta asercion mantiene visible la
        diferencia real encontrada al reconstruir el cuarto caso historico.
        """
        ficha = _ficha({})
        impresos = {'p1__pb__tubeado__A': 'X'}

        with self.assertRaises(lector.LecturaImposible):
            lector.aplicar_digital(
                ficha, impresos, FECHA, REVISION_ANTIGUA)

        _revision, validacion, aplicacion = self._camino_nuevo(
            ficha, impresos)
        self.assertTrue(validacion['aplicable'])
        self.assertEqual(validacion['aceptadas'][0]['antes'], None)
        self.assertEqual(validacion['aceptadas'][0]['accion'], 'actualizar')
        self.assertEqual(
            aplicacion['ficha_actualizada']['estados'][
                'p1__pb__tubeado__A']['v'], 'X')

    def test_contrato_normalizado_fecha_id_origen_y_alfabeto(self):
        ficha = _ficha({
            'p1__pb__tubeado__A': 'P',
            'p1__pb__tubeado__B': 'P',
            'p1__1__tubeado__A': 'P',
            'p1__1__tubeado__B': 'P',
            'p1__pb__cableado__A': 'P',
        })
        impresos = {
            'p1__pb__tubeado__A': 'X',
            'p1__pb__tubeado__B': 'M',
            'p1__1__tubeado__A': '/',
            'p1__1__tubeado__B': '',
            'p1__pb__cableado__A': 'N',
        }

        revision = self._revision(ficha, impresos)

        self.assertEqual(revision['fecha'], FECHA)
        self.assertEqual(revision['origen'], 'pdf_digital')
        self.assertEqual(revision['fuente'], os.path.abspath(self.ruta_pdf))
        self.assertEqual(
            {celda['estado_leido'] for celda in revision['celdas']},
            {'X', 'M', '/', '', 'N'},
        )
        self.assertTrue(all(celda['confianza'] == 'cierta'
                            for celda in revision['celdas']))
        self.assertTrue(revision['metadata']['hoja_usada'])
        self.assertEqual(
            revision['revision_id'],
            validador.generar_revision_id(
                'pruebas', FECHA, 'pdf_digital',
                os.path.abspath(self.ruta_pdf)),
        )

    def test_sin_marca_explicita_la_hoja_no_se_declara_usada(self):
        ficha = _ficha({})

        revision = self._revision(ficha, {})

        self.assertEqual(revision['celdas'], [])
        self.assertFalse(revision['metadata']['hoja_usada'])

    def test_la_fecha_es_obligatoria_y_no_se_infiere_del_nombre(self):
        ficha = _ficha({})
        with patch.object(
                adaptador.leer_hoja_marcada,
                'estados_impresos') as leer:
            with self.assertRaisesRegex(ValueError, 'no se deduce'):
                adaptador.construir_revision_normalizada_pdf_digital(
                    self.ruta_pdf, 'pruebas', ficha, '')
        leer.assert_not_called()


if __name__ == '__main__':
    unittest.main()
