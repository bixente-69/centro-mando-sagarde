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
        # Dos llamadas por diseno: una detecta lo que la hoja ya no trae,
        # la otra lee las marcas.
        self.assertEqual(adaptar_html.call_count, 2)
        adaptar_pdf.assert_not_called()
        guardar.assert_called_once()
        self.assertEqual(
            guardar.call_args.args[1]['estados'][CLAVE]['v'], 'X')
        self.assertEqual(
            guardar.call_args.args[1]['revisiones'][-1]['fecha'], FECHA)

    def test_digital_escribir_html_sin_pdf_omite_salvaguarda(self):
        """Revision exportada solo en HTML (nunca hubo PDF, no que se
        perdiera): no existe "camino antiguo" que reproducir, asi que se
        omite esa comprobacion cruzada -- sin reventar intentando abrir un
        PDF que no existe -- y se escribe apoyandose solo en el motor
        comun. La omision queda registrada, no oculta."""
        html = self._crear_html_gemelo()
        with (
                mock.patch.object(lector, 'estados_impresos') as impresos,
                mock.patch.object(
                    adaptar_revision_html,
                    'construir_revision_normalizada_html',
                    wraps=(adaptar_revision_html
                           .construir_revision_normalizada_html)
                ) as adaptar_html):
            salida, guardar = self._ejecutar([
                html, 'pruebas', '--digital', '--fecha', FECHA,
                '--escribir'], _ficha('P'))

        impresos.assert_not_called()
        # Dos llamadas por diseno: una detecta lo que la hoja ya no trae,
        # la otra lee las marcas.
        self.assertEqual(adaptar_html.call_count, 2)
        self.assertIn('sin PDF real que releer', salida)
        self.assertIn('[SALVAGUARDA OMITIDA]', salida)
        self.assertNotIn('[SALVAGUARDA]', salida)
        guardar.assert_called_once()
        ficha_guardada = guardar.call_args.args[1]
        self.assertEqual(ficha_guardada['estados'][CLAVE]['v'], 'X')

    def test_digital_pasa_al_html_los_mapas_explicitos_de_la_obra(self):
        self._crear_html_gemelo()
        self.obra['mapa_portales_revision_html'] = {
            'src_pruebas_p1': 'p1',
        }
        impresos = {CLAVE: 'X'}
        with (
                mock.patch.object(
                    lector, 'estados_impresos', return_value=impresos),
                mock.patch.object(
                    adaptar_revision_html,
                    'construir_revision_normalizada_html',
                    wraps=(adaptar_revision_html
                           .construir_revision_normalizada_html)
                ) as adaptar_html):
            _salida, guardar = self._ejecutar([
                self.pdf, 'pruebas', '--digital', '--fecha', FECHA,
                '--escribir'], _ficha('P'))

        self.assertEqual(
            adaptar_html.call_args.kwargs['portal_id_a_real'],
            {'src_pruebas_p1': 'p1'},
        )
        guardar.assert_called_once()

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


class TestDigitalEstructuraYBlancos(unittest.TestCase):
    """04/10/2026: la ultima hoja manda, tambien en su estructura, y un
    blanco de hoja usada es "tajo no empezado" (P), no "sin revisar" (?)."""

    # Mismo montaje que la clase de arriba, sin heredar sus pruebas.
    setUp = TestCutoverLeerHojaMarcada.setUp
    tearDown = TestCutoverLeerHojaMarcada.tearDown
    _ejecutar = TestCutoverLeerHojaMarcada._ejecutar

    A = 'p1__pb__tubeado__A'
    B = 'p1__pb__tubeado__B'
    C = 'p1__pb__tubeado__C'
    PORTAL = 'src_pruebas_p1__src_pruebas_p1_f1__tube-viv__'

    def _ficha_ab(self):
        ficha = fixtures.ficha_minima()
        ficha['estados'] = {
            self.A: {'v': '?', 'f': None, 'r': None},
            self.B: {'v': '?', 'f': None, 'r': None},
        }
        return ficha

    def _html(self, celdas):
        html = self.pdf.with_suffix('.html')
        html.write_text(''.join(
            f'<td data-k="{k}" data-st="{s}"></td>' for k, s in celdas),
            encoding='utf-8')
        return html

    def _correr(self, extra, ficha=None, impresos=None):
        with mock.patch.object(
                lector, 'estados_impresos', return_value=impresos or {}):
            return self._ejecutar([
                self.pdf, 'pruebas', '--digital', '--fecha', FECHA,
                *extra], ficha or self._ficha_ab())

    def test_blanco_de_hoja_usada_pasa_a_P_y_la_marca_se_aplica(self):
        self._html([(self.PORTAL + 'A', 'X'), (self.PORTAL + 'B', '')])
        salida, guardar = self._correr(
            ['--escribir'], impresos={self.A: 'X'})

        estados = guardar.call_args.args[1]['estados']
        self.assertEqual(estados[self.A]['v'], 'X')
        self.assertEqual(estados[self.B]['v'], 'P')
        self.assertIn('tajo no empezado (P): 1', salida)

    def test_sin_marca_desconocido_deja_el_blanco_como_estaba(self):
        self._html([(self.PORTAL + 'A', 'X'), (self.PORTAL + 'B', '')])
        salida, guardar = self._correr(
            ['--escribir', '--sin-marca', 'desconocido'],
            impresos={self.A: 'X'})

        estados = guardar.call_args.args[1]['estados']
        self.assertEqual(estados[self.A]['v'], 'X')
        self.assertEqual(estados[self.B]['v'], '?')

    def test_hoja_sin_ninguna_marca_no_cambia_nada(self):
        self._html([(self.PORTAL + 'A', ''), (self.PORTAL + 'B', '')])
        salida, guardar = self._correr(['--escribir'])

        estados = guardar.call_args.args[1]['estados']
        self.assertEqual(estados[self.A]['v'], '?')
        self.assertEqual(estados[self.B]['v'], '?')

    def test_vivienda_nueva_de_la_hoja_entra_en_la_base_y_su_marca_se_aplica(
            self):
        self._html([(self.PORTAL + 'A', ''), (self.PORTAL + 'B', ''),
                    (self.PORTAL + 'C', 'X')])
        salida, guardar = self._correr(
            ['--escribir'], impresos={self.C: 'X'})

        guardada = guardar.call_args.args[1]
        self.assertIn('ESTRUCTURA NUEVA EN LA HOJA', salida)
        self.assertEqual(guardada['estados'][self.C]['v'], 'X')
        unidades = [u['id'] for u in guardada['estructura']['bloques'][0][
            'portales'][0]['plantas'][0]['ubicaciones']]
        self.assertEqual(unidades, ['A', 'B', 'C'])
        self.assertEqual(guardada['revisiones'][-1]['ubicaciones_nuevas'], 1)

    def test_simulacion_muestra_la_estructura_nueva_y_no_guarda(self):
        self._html([(self.PORTAL + 'A', ''), (self.PORTAL + 'C', 'X')])
        salida, guardar = self._correr([])

        self.assertIn('ESTRUCTURA NUEVA EN LA HOJA', salida)
        self.assertIn('unidad C', salida)
        guardar.assert_not_called()

    def test_marca_que_la_base_no_reconoce_aborta_al_escribir(self):
        # Control: la misma hoja con una planta que la ficha SI tiene escribe.
        self._html([(self.PORTAL + 'A', 'X'),
                    ('src_pruebas_p1__src_pruebas_p1_f9__tube-viv__A', 'X')])
        with self.assertRaises(SystemExit) as ctx:
            self._correr(['--escribir'], impresos={self.A: 'X'})
        self.assertIn('ABORTADO', str(ctx.exception))

    def test_marca_sin_aplicar_se_lista_en_simulacion_y_no_aborta(self):
        self._html([(self.PORTAL + 'A', 'X'),
                    ('src_pruebas_p1__src_pruebas_p1_f9__tube-viv__A', 'X')])
        salida, guardar = self._correr([])

        self.assertIn('[MARCA SIN APLICAR]', salida)
        guardar.assert_not_called()

    def test_permitir_marcas_sin_aplicar_escribe_igualmente(self):
        self._html([(self.PORTAL + 'A', 'X'),
                    ('src_pruebas_p1__src_pruebas_p1_f9__tube-viv__A', 'X')])
        salida, guardar = self._correr(
            ['--escribir', '--permitir-marcas-sin-aplicar'],
            impresos={self.A: 'X'})

        self.assertIn('[MARCA SIN APLICAR]', salida)
        guardar.assert_called_once()


class TestDigitalLaUltimaHojaTambienQuita(unittest.TestCase):
    """04/10/2026: la ultima hoja manda tambien para QUITAR. Lo que ya no
    trae (una vivienda que desaparece, un tajo que no imprime) se retira de
    la base y deja una exclusion para que no lo resucite una regeneracion."""

    setUp = TestCutoverLeerHojaMarcada.setUp
    tearDown = TestCutoverLeerHojaMarcada.tearDown
    _ejecutar = TestCutoverLeerHojaMarcada._ejecutar

    A = 'p1__pb__tubeado__A'
    B = 'p1__pb__tubeado__B'
    PB = 'src_pruebas_p1__src_pruebas_p1_f1__'
    P1 = 'src_pruebas_p1__src_pruebas_p1_f2__'

    def _ficha(self, estado_b='?'):
        ficha = fixtures.ficha_minima()
        ficha['estados'] = {
            'p1__pb__tubeado__A': {'v': '?', 'f': None, 'r': None},
            'p1__pb__tubeado__B': {'v': estado_b, 'f': None, 'r': None},
            'p1__pb__cableado__A': {'v': '?', 'f': None, 'r': None},
            'p1__1__tubeado__A': {'v': '?', 'f': None, 'r': None},
            'p1__1__tubeado__B': {'v': '?', 'f': None, 'r': None},
        }
        return ficha

    def _html(self, celdas):
        html = self.pdf.with_suffix('.html')
        html.write_text(''.join(
            f'<td data-k="{k}" data-st="{s}"></td>' for k, s in celdas),
            encoding='utf-8')

    def _correr(self, extra, ficha):
        # El PDF gemelo imprime la misma unica marca explicita que el HTML.
        with mock.patch.object(
                lector, 'estados_impresos', return_value={self.A: 'X'}):
            return self._ejecutar([
                self.pdf, 'pruebas', '--digital', '--fecha', FECHA,
                *extra], ficha)

    def _hoja_sin_la_B_de_pb(self):
        # Control positivo: la hoja trae la A de PB y las dos de la planta 1.
        self._html([
            (self.PB + 'tube-viv__A', 'X'), (self.PB + 'cabl-elec__A', ''),
            (self.P1 + 'tube-viv__A', ''), (self.P1 + 'tube-viv__B', ''),
        ])

    def test_unidad_que_la_hoja_ya_no_trae_se_retira_con_su_exclusion(self):
        self._hoja_sin_la_B_de_pb()
        salida, guardar = self._correr(['--escribir'], self._ficha())

        guardada = guardar.call_args.args[1]
        self.assertIn('YA NO ESTA EN LA HOJA', salida)
        pb = guardada['estructura']['bloques'][0]['portales'][0]['plantas'][0]
        self.assertEqual([u['id'] for u in pb['ubicaciones']], ['A'])
        self.assertNotIn(self.B, guardada['estados'])
        self.assertEqual(
            [(e['portal'], e['planta'], e['unidad'])
             for e in guardada['estructura']['exclusiones']],
            [('P1', 'PB', 'B')])
        # Control: lo que la hoja SI trae sigue ahi.
        self.assertIn(self.A, guardada['estados'])
        self.assertIn('p1__1__tubeado__B', guardada['estados'])
        self.assertEqual(guardada['revisiones'][-1]['ubicaciones_retiradas'], 1)

    def test_tajo_que_la_hoja_no_imprime_para_una_unidad_se_retira(self):
        # La hoja imprime tubeado pero no cableado para la A de PB.
        self._html([
            (self.PB + 'tube-viv__A', 'X'), (self.PB + 'tube-viv__B', ''),
            (self.P1 + 'tube-viv__A', ''), (self.P1 + 'tube-viv__B', ''),
        ])
        salida, guardar = self._correr(['--escribir'], self._ficha())

        estados = guardar.call_args.args[1]['estados']
        self.assertNotIn('p1__pb__cableado__A', estados)
        self.assertIn(self.A, estados)
        self.assertIn(self.B, estados)

    def test_no_se_retira_nada_si_lo_retirado_guarda_avance_medido(self):
        self._hoja_sin_la_B_de_pb()
        with self.assertRaises(SystemExit) as ctx:
            self._correr(['--escribir'], self._ficha(estado_b='X'))
        self.assertIn('ABORTADO', str(ctx.exception))

    def test_simulacion_lista_lo_que_se_retira_y_no_guarda(self):
        self._hoja_sin_la_B_de_pb()
        salida, guardar = self._correr([], self._ficha())

        self.assertIn('YA NO ESTA EN LA HOJA', salida)
        self.assertIn('unidad B', salida)
        guardar.assert_not_called()

    def test_un_portal_que_la_hoja_no_cubre_no_se_toca(self):
        ficha = self._ficha()
        portal2 = {'id': 'p2', 'nombre': 'P2', 'referencia': 'P2', 'plantas': [
            {'id': 'pb', 'nombre': 'PB', 'orden': 0, 'ubicaciones': [
                {'id': 'A', 'tipo': 'vivienda', 'origen': 'campo'}]}]}
        ficha['estructura']['bloques'][0]['portales'].append(portal2)
        ficha['estados']['p2__pb__tubeado__A'] = {'v': '?', 'f': None, 'r': None}
        self._hoja_sin_la_B_de_pb()
        salida, guardar = self._correr(['--escribir'], ficha)

        guardada = guardar.call_args.args[1]
        self.assertIn('p2__pb__tubeado__A', guardada['estados'])
        self.assertEqual(len(guardada['estructura']['bloques'][0]['portales']), 2)

    def test_hoja_con_claves_sin_resolver_no_retira_nada(self):
        # Una clave de planta desconocida: la base no puede saber si la B
        # falta de verdad o si es un alias que no entiende. No se quita nada.
        self._html([
            (self.PB + 'tube-viv__A', 'X'),
            ('src_pruebas_p1__src_pruebas_p1_f9__tube-viv__A', ''),
            (self.P1 + 'tube-viv__A', ''), (self.P1 + 'tube-viv__B', ''),
        ])
        salida, guardar = self._correr(['--escribir'], self._ficha())

        self.assertIn('no se retira nada de la base', salida)
        self.assertIn(self.B, guardar.call_args.args[1]['estados'])


if __name__ == '__main__':
    unittest.main()
