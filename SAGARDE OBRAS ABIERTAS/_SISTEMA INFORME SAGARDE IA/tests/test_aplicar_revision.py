# -*- coding: utf-8 -*-
"""Paridad y aislamiento del aplicador puro de revisiones normalizadas."""
import copy
import os
import sys
import unittest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aplicar_revision
import ficha_obra
import fixtures
import leer_hoja_marcada as lector
import validar_revision


CLAVE_A = 'p1__pb__tubeado__a'
CLAVE_B = 'p1__pb__tubeado__b'
CLAVE_CABLEADO_A = 'p1__pb__cableado__a'
CLAVE_LEGACY_A = 'p1__pb__tubeado__A'
CLAVE_LEGACY_B = 'p1__pb__tubeado__B'


def _catalogo():
    return {
        'version': 'test',
        'tajos': [{'id': 'tubeado'}, {'id': 'cableado'}],
        'obras': {},
    }


def _registro(estado, fecha='27/07/2026', revision='rev_27072026'):
    return {'v': estado, 'f': fecha, 'r': revision}


def _ficha_normalizada(estados=None):
    """Fixture existente con claves de estado admitidas por el validador."""
    ficha = fixtures.ficha_minima()
    for bloque in ficha['estructura']['bloques']:
        for portal in bloque['portales']:
            for planta in portal['plantas']:
                for ubicacion in planta['ubicaciones']:
                    ubicacion['id'] = ubicacion['id'].lower()
    ficha['estados'] = {
        clave: _registro(estado) for clave, estado in (estados or {}).items()
    }
    return ficha


def _ficha_legacy(estados=None):
    """Misma forma que usan los tests historicos del lector."""
    ficha = fixtures.ficha_minima()
    ficha['estados'] = {
        clave: _registro(estado) for clave, estado in (estados or {}).items()
    }
    return ficha


def _celda(clave=CLAVE_A, estado='X'):
    return {'clave': clave, 'estado_leido': estado, 'confianza': 'cierta'}


def _revision(celdas=None, origen='tinta', hoja_usada=True,
              fecha='05/08/2026', revision_id='rev_05082026'):
    return {
        'revision_id': revision_id,
        'obra': 'pruebas',
        'fecha': fecha,
        'origen': origen,
        'fuente': 'fuente-sintetica.pdf',
        'celdas': list(celdas if celdas is not None else [_celda()]),
        'metadata': {
            'generado_por': 'test_aplicar_revision',
            'generado_en': '2026-08-25T12:00:00+02:00',
            'avisos': [],
            'hoja_usada': hoja_usada,
        },
    }


def _estado_resultante(resultado, clave):
    return resultado['ficha_actualizada']['estados'][clave]['v']


class TestParidadConLectorMarcado(unittest.TestCase):

    def test_norma_de_obra_retroceso_X_a_M_coincide(self):
        ficha_legacy = _ficha_legacy({CLAVE_LEGACY_A: 'X'})
        estados_legacy, cambios, _ = lector.aplicar(
            ficha_legacy, [{'clave': CLAVE_LEGACY_A}],
            {CLAVE_LEGACY_A: 'M'}, '05/08/2026', 'rev_05082026')

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='M')]),
            _ficha_normalizada({CLAVE_A: 'X'}), _catalogo(), dry_run=False)

        self.assertEqual(cambios, [(CLAVE_LEGACY_A, 'X', 'M')])
        self.assertEqual(
            _estado_resultante(resultado, CLAVE_A),
            estados_legacy[CLAVE_LEGACY_A]['v'])

    def test_norma_de_obra_blanco_no_baja_un_estado_conocido(self):
        estados_legacy = {CLAVE_LEGACY_A: _registro('X')}
        cambios = lector.marcar_no_empezados(
            estados_legacy, [CLAVE_LEGACY_A], set(),
            '05/08/2026', 'rev_05082026')

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='')]),
            _ficha_normalizada({CLAVE_A: 'X'}), _catalogo(), dry_run=False)

        self.assertEqual(cambios, [])
        self.assertEqual(
            _estado_resultante(resultado, CLAVE_A),
            estados_legacy[CLAVE_LEGACY_A]['v'])

    def test_blanco_de_tinta_convierte_interrogacion_en_P_como_el_lector(self):
        estados_legacy = {CLAVE_LEGACY_A: _registro('?')}
        cambios = lector.marcar_no_empezados(
            estados_legacy, [CLAVE_LEGACY_A], set(),
            '05/08/2026', 'rev_05082026')

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='')]),
            _ficha_normalizada({CLAVE_A: '?'}), _catalogo(), dry_run=False)

        self.assertEqual(cambios, [(CLAVE_LEGACY_A, '?', 'P')])
        self.assertEqual(
            _estado_resultante(resultado, CLAVE_A),
            estados_legacy[CLAVE_LEGACY_A]['v'])

    def test_sin_tinta_no_hay_cambio_coincide(self):
        ficha_legacy = _ficha_legacy({CLAVE_LEGACY_A: '?'})
        with self.assertRaisesRegex(lector.LecturaImposible,
                                    'Sin tinta no hay cambio'):
            lector.aplicar(
                ficha_legacy, [], {CLAVE_LEGACY_A: 'X'},
                '05/08/2026', 'rev_05082026')

        ficha_nueva = _ficha_normalizada({CLAVE_A: '?'})
        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='X')], hoja_usada=False),
            ficha_nueva, _catalogo(), dry_run=False)

        self.assertFalse(resultado['aplicable'])
        self.assertFalse(resultado['escrito'])
        self.assertEqual(ficha_nueva['estados'][CLAVE_A]['v'],
                         ficha_legacy['estados'][CLAVE_LEGACY_A]['v'])


class TestParidadConFlujoDigital(unittest.TestCase):

    def test_solo_la_marca_explicita_se_aplica(self):
        ficha_legacy = _ficha_legacy({CLAVE_LEGACY_A: 'P'})
        estados_legacy, cambios = lector.aplicar_digital(
            ficha_legacy, {CLAVE_LEGACY_A: 'X'},
            '24/08/2026', 'rev_24082026')

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='X')], origen='pdf_digital',
                      hoja_usada=False, fecha='24/08/2026',
                      revision_id='rev_24082026'),
            _ficha_normalizada({CLAVE_A: 'P'}), _catalogo(), dry_run=False)

        self.assertEqual(cambios, [(CLAVE_LEGACY_A, 'P', 'X')])
        self.assertEqual(
            _estado_resultante(resultado, CLAVE_A),
            estados_legacy[CLAVE_LEGACY_A]['v'])

    def test_blanco_digital_no_toca_la_celda(self):
        ficha_legacy = _ficha_legacy({
            CLAVE_LEGACY_A: 'P', CLAVE_LEGACY_B: '?'})
        estados_legacy, _ = lector.aplicar_digital(
            ficha_legacy, {CLAVE_LEGACY_A: 'X'},
            '24/08/2026', 'rev_24082026')

        resultado = aplicar_revision.apply_revision(
            _revision(
                [_celda(estado='X'), _celda(CLAVE_B, '')],
                origen='pdf_digital', hoja_usada=False,
                fecha='24/08/2026', revision_id='rev_24082026'),
            _ficha_normalizada({CLAVE_A: 'P', CLAVE_B: '?'}),
            _catalogo(), dry_run=False)

        self.assertEqual(
            _estado_resultante(resultado, CLAVE_B),
            estados_legacy[CLAVE_LEGACY_B]['v'])


class TestParidadConFichaObra(unittest.TestCase):

    def test_blanco_no_baja_X_como_actualizar(self):
        ficha_legacy = fixtures.ficha_minima()
        ficha_legacy, _ = ficha_obra.actualizar(
            ficha_legacy,
            fixtures.prioridades([fixtures.item(estado='X')]))
        ficha_legacy, _ = ficha_obra.actualizar(
            ficha_legacy,
            fixtures.prioridades([fixtures.item(estado='')],
                                  revision='30/07/2026'))

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='')], fecha='30/07/2026',
                      revision_id='rev_30072026'),
            _ficha_normalizada({CLAVE_A: 'X'}), _catalogo(), dry_run=False)

        self.assertEqual(
            _estado_resultante(resultado, CLAVE_A),
            ficha_legacy['estados'][CLAVE_LEGACY_A]['v'])

    def test_blanco_sin_estado_previo_produce_P_como_actualizar(self):
        ficha_legacy, _ = ficha_obra.actualizar(
            fixtures.ficha_minima(),
            fixtures.prioridades([fixtures.item(estado='')]))

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='')], fecha='27/07/2026',
                      revision_id='rev_27072026'),
            _ficha_normalizada(), _catalogo(), dry_run=False)

        self.assertEqual(
            _estado_resultante(resultado, CLAVE_A),
            ficha_legacy['estados'][CLAVE_LEGACY_A]['v'])

    def test_blanco_digital_sobre_interrogacion_se_conserva_como_actualizar(self):
        ficha_legacy = fixtures.ficha_minima()
        ficha_legacy['estados'][CLAVE_LEGACY_A] = _registro('?')
        ficha_legacy, _ = ficha_obra.actualizar(
            ficha_legacy,
            fixtures.prioridades([fixtures.item(estado='')]))

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='')], origen='pdf_digital',
                      hoja_usada=False, fecha='27/07/2026',
                      revision_id='rev_27072026'),
            _ficha_normalizada({CLAVE_A: '?'}), _catalogo(), dry_run=False)

        self.assertEqual(
            _estado_resultante(resultado, CLAVE_A),
            ficha_legacy['estados'][CLAVE_LEGACY_A]['v'])


class TestDiscrepanciaDeClavesExistentes(unittest.TestCase):

    def test_paridad_exacta_con_clave_de_fixture_en_mayuscula(self):
        """La clave de produccion conserva el case original de la vivienda."""
        ficha = _ficha_legacy({CLAVE_LEGACY_A: 'X'})
        estados_legacy, _, _ = lector.aplicar(
            ficha, [{'clave': CLAVE_LEGACY_A}],
            {CLAVE_LEGACY_A: 'M'}, '05/08/2026', 'rev_05082026')

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(CLAVE_LEGACY_A, 'M')]),
            _ficha_legacy({CLAVE_LEGACY_A: 'X'}),
            _catalogo(), dry_run=False)

        self.assertTrue(resultado['escrito'], resultado)
        self.assertEqual(
            _estado_resultante(resultado, CLAVE_LEGACY_A),
            estados_legacy[CLAVE_LEGACY_A]['v'])
        self.assertNotIn(CLAVE_A, resultado['ficha_actualizada']['estados'])

    def test_case_distinto_se_rechaza_sin_crear_una_clave_paralela(self):
        """Una vivienda ``a`` no resuelve la vivienda ``A`` de la estructura."""
        ficha = _ficha_legacy({CLAVE_LEGACY_A: 'X'})
        copia = copy.deepcopy(ficha)

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(CLAVE_A, 'M')]),
            ficha, _catalogo(), dry_run=False)

        self.assertFalse(resultado['aplicable'])
        self.assertFalse(resultado['escrito'])
        self.assertNotIn('ficha_actualizada', resultado)
        self.assertEqual(resultado['rechazadas'][0]['regla'], 3)
        self.assertEqual(ficha, copia)

    def test_vivienda_mayuscula_valida_y_actualiza_la_misma_clave(self):
        ficha = _ficha_legacy({CLAVE_LEGACY_A: 'X'})
        revision = _revision([_celda(CLAVE_LEGACY_A, 'M')])

        validacion = validar_revision.validar(revision, ficha, _catalogo())
        resultado = aplicar_revision.apply_revision(
            revision, ficha, _catalogo(), dry_run=False)

        self.assertTrue(validacion['aplicable'], validacion)
        self.assertEqual(validacion['aceptadas'][0]['antes'], 'X')
        self.assertEqual(validacion['aceptadas'][0]['clave'], CLAVE_LEGACY_A)
        self.assertTrue(resultado['escrito'], resultado)
        self.assertEqual(
            set(resultado['ficha_actualizada']['estados']), {CLAVE_LEGACY_A})
        self.assertEqual(
            _estado_resultante(resultado, CLAVE_LEGACY_A), 'M')
        self.assertNotIn(CLAVE_A, resultado['ficha_actualizada']['estados'])


class TestAplicacionPura(unittest.TestCase):

    def test_dry_run_por_defecto_no_muta_ni_devuelve_ficha_actualizada(self):
        ficha = _ficha_normalizada({CLAVE_A: '?'})
        copia = copy.deepcopy(ficha)

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='X')]), ficha, _catalogo())

        self.assertTrue(resultado['aplicable'])
        self.assertFalse(resultado['escrito'])
        self.assertNotIn('ficha_actualizada', resultado)
        self.assertEqual(ficha, copia)

    def test_revision_no_aplicable_no_muta_aunque_no_sea_dry_run(self):
        ficha = _ficha_normalizada({CLAVE_A: '?'})
        copia = copy.deepcopy(ficha)

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='X')], hoja_usada=False),
            ficha, _catalogo(), dry_run=False)

        self.assertFalse(resultado['aplicable'])
        self.assertFalse(resultado['escrito'])
        self.assertNotIn('ficha_actualizada', resultado)
        self.assertEqual(ficha, copia)

    def test_aplicacion_no_muta_ficha_actual_y_devuelve_copia_profunda(self):
        ficha = _ficha_normalizada({CLAVE_A: '?'})
        copia = copy.deepcopy(ficha)

        resultado = aplicar_revision.apply_revision(
            _revision([_celda(estado='X')]),
            ficha, _catalogo(), dry_run=False)

        actualizada = resultado['ficha_actualizada']
        self.assertTrue(resultado['escrito'])
        self.assertEqual(ficha, copia)
        self.assertIsNot(actualizada, ficha)
        self.assertIsNot(actualizada['estructura'], ficha['estructura'])
        self.assertEqual(actualizada['estados'][CLAVE_A], {
            'v': 'X', 'f': '05/08/2026', 'r': 'rev_05082026'})

    def test_varias_celdas_combinan_actualizar_conservar_y_descartar(self):
        ficha = _ficha_normalizada({
            CLAVE_A: '?',
            CLAVE_CABLEADO_A: 'M',
            CLAVE_B: '/',
        })
        anteriores = copy.deepcopy(ficha['estados'])
        revision = _revision(
            [_celda(CLAVE_A, 'X'), _celda(CLAVE_CABLEADO_A, ''),
             _celda(CLAVE_B, 'N')],
            origen='html_digital', hoja_usada=False,
            fecha='25/08/2026', revision_id='rev_mixta')

        resultado = aplicar_revision.apply_revision(
            revision, ficha, _catalogo(), dry_run=False)
        actualizados = resultado['ficha_actualizada']['estados']

        self.assertEqual(
            [celda['accion'] for celda in resultado['aceptadas']],
            ['actualizar', 'conservar', 'descartar'])
        self.assertEqual(actualizados[CLAVE_A], {
            'v': 'X', 'f': '25/08/2026', 'r': 'rev_mixta'})
        self.assertEqual(actualizados[CLAVE_CABLEADO_A],
                         anteriores[CLAVE_CABLEADO_A])
        self.assertEqual(actualizados[CLAVE_B], anteriores[CLAVE_B])
        self.assertEqual(ficha['estados'], anteriores)


if __name__ == '__main__':
    unittest.main()
