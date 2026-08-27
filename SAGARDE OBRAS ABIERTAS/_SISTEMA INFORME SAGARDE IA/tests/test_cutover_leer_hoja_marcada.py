# -*- coding: utf-8 -*-
"""Cutover del CLI al motor comun, siempre sobre datos sinteticos."""
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import adaptar_revision_html
import adaptar_revision_pdf_digital
import aplicar_revision
import fixtures
import leer_hoja_marcada as lector
import validar_revision


CLAVE = 'p1__pb__tubeado__A'
FECHA = '01/09/2026'


def _ficha(estado='?'):
    ficha = fixtures.ficha_minima()
    ficha['estados'] = {
        CLAVE: {'v': estado, 'f': '31/08/2026', 'r': 'rev_31082026'}
    }
    return ficha


def _ficha_con_revision_previa_no_relacionada(estado='?'):
    """Una revision REAL, de otra fuente, que por casualidad de fecha
    comparte el id heredado ``rev_DDMMYYYY`` que esta relectura recalcula
    para su propia salvaguarda en memoria."""
    ficha = _ficha(estado)
    ficha['revisiones'] = [{
        'id': 'rev_' + FECHA.replace('/', ''),
        'fecha': FECHA,
        'procesada': '01/09/2026 08:00',
        'celdas': 999,
        'cambios': 999,
    }]
    return ficha


def _candidata():
    return {
        'clave': CLAVE,
        'puntos': 12,
        'antes': '?',
        'dudosa': False,
        'pagina': 1,
        'bloque': 'Bloque 1',
        'portal': 'P1',
        'planta': 'PB',
        'vivienda': 'A',
        'tajo': 'tubeado',
        'tajo_nombre': 'Tubeado',
        'recorte': None,
        'valor': None,
    }


class TestCutoverLeerHojaMarcada(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)
        # El CLI recibe la fecha de forma explicita: ni el PDF ni su HTML
        # gemelo necesitan codificarla en el nombre.
        self.pdf = self.raiz / 'REVISION SINTETICA.pdf'
        self.pdf.write_bytes(b'%PDF-sintetico-para-hash')
        self.obra = {
            'id': 'pruebas',
            'nombre': 'OBRA DE PRUEBAS',
            'carpeta_obra': 'OBRA DE PRUEBAS',
        }

    def tearDown(self):
        self.temporal.cleanup()

    def _preparar_tinta(self):
        carpeta_sistema = self.raiz / '_SISTEMA'
        carpeta_sistema.mkdir(exist_ok=True)
        candidatas = carpeta_sistema / (
            self.pdf.stem + '.candidatas.json')
        candidatas.write_text(json.dumps({
            'version': 1,
            'hoja': self.pdf.name,
            'obra': 'pruebas',
            'celdas_hoja': [CLAVE],
            'columnas_sin_mapear': [],
            'candidatas': [_candidata()],
        }), encoding='utf-8')
        clasificacion = self.raiz / 'clasificacion.json'
        clasificacion.write_text(
            json.dumps({'celdas': {CLAVE: 'X'}}), encoding='utf-8')
        return clasificacion

    def _crear_html_gemelo(self):
        html = self.pdf.with_suffix('.html')
        html.write_text(
            '<td data-k="src_pruebas_p1__src_pruebas_p1_f1__'
            'tube-viv__A" data-st="X"></td>',
            encoding='utf-8')
        return html

    def _ejecutar(self, argumentos, ficha):
        salida = io.StringIO()
        with (
                mock.patch.object(sys, 'argv', [
                    'leer_hoja_marcada.py', *map(str, argumentos)]),
                mock.patch.object(lector, '_obra_de', return_value=self.obra),
                mock.patch.object(
                    lector.fichas, 'cargar', return_value=copy.deepcopy(ficha)),
                mock.patch.object(lector.fichas, 'guardar') as guardar,
                contextlib.redirect_stdout(salida)):
            lector.main()
        return salida.getvalue(), guardar

    def test_aplicar_escribir_guarda_solo_tras_paridad_exacta(self):
        clasificacion = self._preparar_tinta()
        with (
                mock.patch.object(
                    validar_revision, 'validar', wraps=validar_revision.validar
                ) as validar,
                mock.patch.object(
                    aplicar_revision, 'apply_revision',
                    wraps=aplicar_revision.apply_revision
                ) as aplicar_comun):
            salida, guardar = self._ejecutar([
                self.pdf, 'pruebas', '--aplicar', clasificacion,
                '--fecha', FECHA, '--escribir'], _ficha())

        self.assertIn('[SALVAGUARDA]', salida)
        self.assertIn('coinciden exactamente en 1 celda', salida)
        guardar.assert_called_once()
        ficha_guardada = guardar.call_args.args[1]
        self.assertEqual(ficha_guardada['estados'][CLAVE]['v'], 'X')
        self.assertNotIn('origen', ficha_guardada['estados'][CLAVE])
        self.assertTrue(validar.called)
        self.assertEqual(aplicar_comun.call_args.kwargs['dry_run'], False)

    def test_digital_escribir_prefiere_html_gemelo(self):
        html = self._crear_html_gemelo()
        impresos = {CLAVE: 'X'}
        with (
                mock.patch.object(
                    lector, 'estados_impresos', return_value=impresos),
                mock.patch.object(
                    adaptar_revision_html,
                    'construir_revision_normalizada_html',
                    wraps=(adaptar_revision_html
                           .construir_revision_normalizada_html)
                ) as adaptar_html,
                mock.patch.object(
                    adaptar_revision_pdf_digital,
                    'construir_revision_normalizada_pdf_digital',
                    wraps=(adaptar_revision_pdf_digital
                           .construir_revision_normalizada_pdf_digital)
                ) as adaptar_pdf):
            salida, guardar = self._ejecutar([
                self.pdf, 'pruebas', '--digital', '--fecha', FECHA,
                '--escribir'], _ficha('P'))

        self.assertIn(f'usando el HTML gemelo: {html}', salida)
        self.assertIn('[SALVAGUARDA]', salida)
        adaptar_html.assert_called_once()
        adaptar_pdf.assert_not_called()
        guardar.assert_called_once()
        self.assertEqual(
            guardar.call_args.args[1]['estados'][CLAVE]['v'], 'X')
        self.assertEqual(
            guardar.call_args.args[1]['revisiones'][-1]['fecha'], FECHA)

    def test_digital_escribir_sin_html_usa_pdf(self):
        impresos = {CLAVE: 'X'}
        with (
                mock.patch.object(
                    lector, 'estados_impresos', return_value=impresos),
                mock.patch.object(
                    adaptar_revision_html,
                    'construir_revision_normalizada_html',
                    wraps=(adaptar_revision_html
                           .construir_revision_normalizada_html)
                ) as adaptar_html,
                mock.patch.object(
                    adaptar_revision_pdf_digital,
                    'construir_revision_normalizada_pdf_digital',
                    wraps=(adaptar_revision_pdf_digital
                           .construir_revision_normalizada_pdf_digital)
                ) as adaptar_pdf):
            salida, guardar = self._ejecutar([
                self.pdf, 'pruebas', '--digital', '--fecha', FECHA,
                '--escribir'], _ficha('P'))

        self.assertIn('sin HTML gemelo, usando lectura del PDF', salida)
        self.assertIn('[SALVAGUARDA]', salida)
        adaptar_html.assert_not_called()
        adaptar_pdf.assert_called_once()
        guardar.assert_called_once()

    def test_forzar_pdf_ignora_html_gemelo(self):
        self._crear_html_gemelo()
        impresos = {CLAVE: 'X'}
        with (
                mock.patch.object(
                    lector, 'estados_impresos', return_value=impresos),
                mock.patch.object(
                    adaptar_revision_html,
                    'construir_revision_normalizada_html',
                    wraps=(adaptar_revision_html
                           .construir_revision_normalizada_html)
                ) as adaptar_html,
                mock.patch.object(
                    adaptar_revision_pdf_digital,
                    'construir_revision_normalizada_pdf_digital',
                    wraps=(adaptar_revision_pdf_digital
                           .construir_revision_normalizada_pdf_digital)
                ) as adaptar_pdf):
            salida, guardar = self._ejecutar([
                self.pdf, 'pruebas', '--digital', '--fecha', FECHA,
                '--forzar-pdf', '--escribir'], _ficha('P'))

        self.assertIn('HTML gemelo ignorado por --forzar-pdf', salida)
        adaptar_html.assert_not_called()
        adaptar_pdf.assert_called_once()
        guardar.assert_called_once()

    def test_digital_no_borra_revision_previa_no_relacionada(self):
        """rev_25082026 real (569 cambios, de otra fuente) no debe
        desaparecer solo porque el nombre heredado de HOY coincide por
        fecha. Bug encontrado el 27/08/2026 en Mungia: 472 celdas se
        quedaron apuntando a un id ya retirado de 'revisiones'."""
        html = self._crear_html_gemelo()
        impresos = {CLAVE: 'X'}
        with (
                mock.patch.object(
                    lector, 'estados_impresos', return_value=impresos)):
            salida, guardar = self._ejecutar([
                self.pdf, 'pruebas', '--digital', '--fecha', FECHA,
                '--escribir'],
                _ficha_con_revision_previa_no_relacionada('P'))

        del html
        ficha_guardada = guardar.call_args.args[1]
        ids = {r['id'] for r in ficha_guardada['revisiones']}
        self.assertIn('rev_' + FECHA.replace('/', ''), ids,
                       'se ha borrado una revision real de otra fuente '
                       'por coincidir el nombre heredado con el de hoy')
        self.assertIn('[AVISO]', salida)

    def test_digital_retira_revision_previa_si_es_el_mismo_calculo(self):
        """Si la entrada heredada SI coincide con lo que recalcula el
        camino antiguo de esta misma pasada, es un duplicado legitimo del
        cutover y se retira para no dejar dos entradas de la misma cosa."""
        html = self._crear_html_gemelo()
        impresos = {CLAVE: 'X'}
        ficha = _ficha('P')
        ficha['revisiones'] = [{
            'id': 'rev_' + FECHA.replace('/', ''),
            'fecha': FECHA, 'celdas': 1, 'cambios': 1,
        }]
        with (
                mock.patch.object(
                    lector, 'estados_impresos', return_value=impresos)):
            salida, guardar = self._ejecutar([
                self.pdf, 'pruebas', '--digital', '--fecha', FECHA,
                '--escribir'], ficha)

        del html, salida
        ficha_guardada = guardar.call_args.args[1]
        ids = [r['id'] for r in ficha_guardada['revisiones']]
        self.assertEqual(ids.count('rev_' + FECHA.replace('/', '')), 0)
        self.assertEqual(len(ficha_guardada['revisiones']), 1)

    def test_discrepancia_aborta_sin_sidecar_ni_ficha(self):
        clasificacion = self._preparar_tinta()
        aplicar_real = aplicar_revision.apply_revision

        def aplicar_divergente(revision, ficha, catalogo, dry_run=True):
            resultado = aplicar_real(
                revision, ficha, catalogo, dry_run=dry_run)
            if not dry_run and resultado.get('ficha_actualizada'):
                resultado['ficha_actualizada']['estados'][CLAVE]['v'] = 'M'
            return resultado

        salida = io.StringIO()
        with (
                mock.patch.object(sys, 'argv', [
                    'leer_hoja_marcada.py', str(self.pdf), 'pruebas',
                    '--aplicar', str(clasificacion), '--fecha', FECHA,
                    '--escribir']),
                mock.patch.object(lector, '_obra_de', return_value=self.obra),
                mock.patch.object(
                    lector.fichas, 'cargar', return_value=_ficha()),
                mock.patch.object(lector.fichas, 'guardar') as guardar,
                mock.patch.object(
                    aplicar_revision, 'apply_revision',
                    side_effect=aplicar_divergente),
                contextlib.redirect_stdout(salida)):
            with self.assertRaises(SystemExit) as caso:
                lector.main()

        self.assertEqual(caso.exception.code, 2)
        texto = salida.getvalue()
        self.assertIn('[ABORTADO]', texto)
        self.assertIn('antiguo=\'X\'; nuevo=\'M\'', texto)
        self.assertIn(CLAVE, texto)
        guardar.assert_not_called()
        sidecar = self.raiz / '_SISTEMA' / (
            self.pdf.name + '.correcciones.json')
        self.assertFalse(sidecar.exists())


if __name__ == '__main__':
    unittest.main()
