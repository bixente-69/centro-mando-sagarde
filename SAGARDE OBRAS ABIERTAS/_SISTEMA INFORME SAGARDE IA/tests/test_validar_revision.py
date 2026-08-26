# -*- coding: utf-8 -*-
"""Pruebas del modelo y validador comun de revisiones normalizadas."""
import copy
import os
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ficha_obra
import fixtures
import leer_hoja_marcada as lector
import validar_revision as validador


CLAVE = 'p1__pb__tubeado__a'
CLAVE_VIVIENDA_MAYUSCULA = 'p1__pb__tubeado__A'


def _catalogo():
    return {
        'version': 'test',
        'tajos': [{'id': 'tubeado'}, {'id': 'cableado'}],
        'obras': {
            'obra_prueba': {'tajos': [{'id': 'tajo_especial'}]},
        },
    }


def _ficha(estado='?', obra='obra_prueba'):
    ficha = fixtures.ficha_minima()
    ficha['id'] = obra
    for bloque in ficha['estructura']['bloques']:
        for portal in bloque['portales']:
            portal['id'] = portal['id'].lower()
            for planta in portal['plantas']:
                planta['id'] = planta['id'].lower()
                for ubicacion in planta['ubicaciones']:
                    ubicacion['id'] = ubicacion['id'].lower()
    ficha['estados'] = {}
    if estado != 'sin_celda':
        ficha['estados'][CLAVE] = {
            'v': estado, 'f': '24/08/2026', 'r': 'rev_anterior'}
    return ficha


def _ficha_con_viviendas_mayusculas(estado='?', obra='obra_prueba'):
    ficha = fixtures.ficha_minima()
    ficha['id'] = obra
    ficha['estados'] = {}
    if estado != 'sin_celda':
        ficha['estados'][CLAVE_VIVIENDA_MAYUSCULA] = {
            'v': estado, 'f': '24/08/2026', 'r': 'rev_anterior'}
    return ficha


def _celda(clave=CLAVE, estado='X', confianza='cierta'):
    return {
        'clave': clave,
        'estado_leido': estado,
        'confianza': confianza,
    }


def _revision(celdas=None, obra='obra_prueba', fecha='25/08/2026',
              origen='tinta', hoja_usada=True, avisos=None):
    return {
        'revision_id': f'{obra}__{fecha}__{origen}__12345678',
        'obra': obra,
        'fecha': fecha,
        'origen': origen,
        'fuente': 'fuente-sintetica.pdf',
        'celdas': list(celdas if celdas is not None else [_celda()]),
        'metadata': {
            'generado_por': 'test_validar_revision',
            'generado_en': '2026-08-25T12:00:00+02:00',
            'avisos': list(avisos or []),
            'hoja_usada': hoja_usada,
        },
    }


def _una_aceptada(resultado):
    if resultado['rechazadas']:
        raise AssertionError(resultado['rechazadas'])
    return resultado['aceptadas'][0]


class TestEstructuras(unittest.TestCase):

    def test_constructor_revision_celda_devuelve_dict_simple(self):
        celda = validador.crear_revision_celda(CLAVE, 'X', 'cierta')
        self.assertIs(type(celda), dict)
        self.assertEqual(celda, _celda())

    def test_validador_forma_celda_detecta_campos_y_tipos(self):
        errores = validador.validar_forma_revision_celda(
            {'clave': 3, 'estado_leido': None})
        self.assertTrue(any('confianza' in error for error in errores))
        self.assertTrue(any("'clave' debe ser str" in error for error in errores))
        self.assertTrue(any("'estado_leido' debe ser str" in error
                            for error in errores))

    def test_constructor_revision_celda_rechaza_confianza_desconocida(self):
        with self.assertRaisesRegex(ValueError, 'confianza'):
            validador.crear_revision_celda(CLAVE, 'X', 'inventada')

    def test_constructor_revision_normalizada_devuelve_dict_simple(self):
        revision = _revision()
        construida = validador.crear_revision_normalizada(
            revision['revision_id'], revision['obra'], revision['fecha'],
            revision['origen'], revision['fuente'], revision['celdas'],
            revision['metadata'])
        self.assertIs(type(construida), dict)
        self.assertEqual(construida, revision)

    def test_validador_forma_revision_detecta_campo_y_tipo_incorrectos(self):
        revision = _revision()
        del revision['fuente']
        revision['celdas'] = 'no-es-lista'
        errores = validador.validar_forma_revision_normalizada(revision)
        self.assertTrue(any('fuente' in error for error in errores))
        self.assertTrue(any("'celdas' debe ser list" in error for error in errores))

    def test_constructor_revision_rechaza_metadata_sin_hoja_usada(self):
        revision = _revision()
        del revision['metadata']['hoja_usada']
        with self.assertRaisesRegex(ValueError, 'hoja_usada'):
            validador.crear_revision_normalizada(
                revision['revision_id'], revision['obra'], revision['fecha'],
                revision['origen'], revision['fuente'], revision['celdas'],
                revision['metadata'])


class TestRevisionId(unittest.TestCase):

    def test_mismo_fichero_procesado_dos_veces_da_el_mismo_id(self):
        with tempfile.TemporaryDirectory() as carpeta:
            fuente = os.path.join(carpeta, 'revision.pdf')
            with open(fuente, 'wb') as fichero:
                fichero.write(b'contenido estable\x00\x01')
            primero = validador.generar_revision_id(
                'obra', '25/08/2026', 'tinta', fuente)
            segundo = validador.generar_revision_id(
                'obra', '25/08/2026', 'tinta', fuente)
        self.assertEqual(primero, segundo)
        self.assertRegex(
            primero, r'^obra__25/08/2026__tinta__[0-9a-f]{8}$')

    def test_mismo_contenido_en_rutas_distintas_da_el_mismo_id(self):
        with tempfile.TemporaryDirectory() as carpeta:
            rutas = [os.path.join(carpeta, nombre) for nombre in ('a.pdf', 'b.pdf')]
            for ruta in rutas:
                with open(ruta, 'wb') as fichero:
                    fichero.write(b'los mismos bytes')
            ids = [validador.generar_revision_id(
                'obra', '25/08/2026', 'tinta', ruta) for ruta in rutas]
        self.assertEqual(ids[0], ids[1])

    def test_ficheros_con_contenido_distinto_dan_ids_distintos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            rutas = [os.path.join(carpeta, nombre) for nombre in ('a.pdf', 'b.pdf')]
            for ruta, contenido in zip(rutas, (b'contenido A', b'contenido B')):
                with open(ruta, 'wb') as fichero:
                    fichero.write(contenido)
            ids = [validador.generar_revision_id(
                'obra', '25/08/2026', 'tinta', ruta) for ruta in rutas]
        self.assertNotEqual(ids[0], ids[1])


class TestRegla1ObraCoincide(unittest.TestCase):

    def test_regla_1_pasa_si_la_obra_coincide(self):
        resultado = validador.validar(_revision(), _ficha(), _catalogo())
        self.assertTrue(resultado['aplicable'])

    def test_regla_1_falla_si_la_obra_no_coincide(self):
        resultado = validador.validar(
            _revision(obra='otra_obra'), _ficha(), _catalogo())
        self.assertFalse(resultado['aplicable'])
        self.assertTrue(any('regla 1' in error for error in resultado['errores']))
        self.assertEqual(len(resultado['rechazadas']), 1)


class TestRegla2FormatoClave(unittest.TestCase):

    def test_regla_2_pasa_con_cuatro_partes_en_minusculas(self):
        resultado = validador.validar(_revision(), _ficha(), _catalogo())
        self.assertEqual(_una_aceptada(resultado)['clave'], CLAVE)

    def test_regla_2_acepta_el_case_original_de_la_vivienda(self):
        resultado = validador.validar(
            _revision([_celda(clave=CLAVE_VIVIENDA_MAYUSCULA)]),
            _ficha_con_viviendas_mayusculas(), _catalogo())

        aceptada = _una_aceptada(resultado)
        self.assertTrue(resultado['aplicable'])
        self.assertEqual(aceptada['clave'], CLAVE_VIVIENDA_MAYUSCULA)
        self.assertEqual(aceptada['antes'], '?')

    def test_regla_2_falla_con_formas_incorrectas(self):
        claves = [
            'p1__pb__tubeado',
            'p1__pb____a',
            'p1__pb__tubeado__a__extra',
            'P1__pb__tubeado__a',
            'p1__PB__tubeado__a',
            'p1__pb__Tubeado__a',
        ]
        for clave in claves:
            with self.subTest(clave=clave):
                resultado = validador.validar(
                    _revision([_celda(clave=clave)]), _ficha(), _catalogo())
                self.assertEqual(resultado['rechazadas'][0]['regla'], 2)


class TestRegla3UbicacionExiste(unittest.TestCase):

    def test_regla_3_pasa_si_portal_planta_y_vivienda_existen(self):
        resultado = validador.validar(_revision(), _ficha(), _catalogo())
        self.assertTrue(resultado['aplicable'])

    def test_regla_3_exige_el_case_exacto_de_la_vivienda(self):
        resultado = validador.validar(
            _revision([_celda(clave=CLAVE)]),
            _ficha_con_viviendas_mayusculas(), _catalogo())

        self.assertFalse(resultado['aplicable'])
        self.assertEqual(resultado['rechazadas'][0]['regla'], 3)

    def test_regla_3_falla_si_falta_cualquier_nivel(self):
        claves = [
            'p9__pb__tubeado__a',
            'p1__9__tubeado__a',
            'p1__pb__tubeado__z',
        ]
        for clave in claves:
            with self.subTest(clave=clave):
                resultado = validador.validar(
                    _revision([_celda(clave=clave)]), _ficha(), _catalogo())
                self.assertEqual(resultado['rechazadas'][0]['regla'], 3)


class TestRegla4TajoEnCatalogo(unittest.TestCase):

    def test_regla_4_pasa_con_tajo_comun(self):
        resultado = validador.validar(_revision(), _ficha(), _catalogo())
        self.assertTrue(resultado['aplicable'])

    def test_regla_4_pasa_con_tajo_propio_de_la_obra(self):
        clave = 'p1__pb__tajo_especial__a'
        resultado = validador.validar(
            _revision([_celda(clave=clave)]), _ficha(), _catalogo())
        self.assertTrue(resultado['aplicable'])

    def test_regla_4_falla_con_tajo_desconocido(self):
        clave = 'p1__pb__inventado__a'
        resultado = validador.validar(
            _revision([_celda(clave=clave)]), _ficha(), _catalogo())
        self.assertEqual(resultado['rechazadas'][0]['regla'], 4)

    def test_carga_el_catalogo_real_y_su_override_de_obra(self):
        catalogo = validador.cargar_catalogo_tajos()
        self.assertEqual(catalogo['version'], '1.3')
        obra = '2025 BILBAO OBISPO ORUETA'
        clave = 'p1__pb__ventilacion__a'
        resultado = validador.validar(
            _revision([_celda(clave=clave)], obra=obra),
            _ficha(obra=obra), catalogo)
        self.assertTrue(resultado['aplicable'], resultado)


class TestRegla5AlfabetoHoja(unittest.TestCase):

    def test_regla_5_el_alfabeto_depende_del_origen(self):
        alfabetos_esperados = {
            'tinta': {'X', 'M', '/', '', 'N', 'P'},
            'pdf_digital': {'X', 'M', '/', '', 'N'},
            'html_digital': {'X', 'M', '/', '', 'N'},
        }
        self.assertEqual(validador.ALFABETOS_HOJA, alfabetos_esperados)
        for origen, alfabeto in alfabetos_esperados.items():
            for estado in alfabeto:
                with self.subTest(origen=origen, estado=estado):
                    resultado = validador.validar(
                        _revision([_celda(estado=estado)], origen=origen),
                        _ficha(), _catalogo())
                    self.assertEqual(resultado['rechazadas'], [])

    def test_regla_5_falla_con_estado_fuera_del_alfabeto_de_hoja(self):
        invalidos_por_origen = {
            'tinta': ('?', 'x', 'Z'),
            'pdf_digital': ('P', '?', 'x', 'Z'),
            'html_digital': ('P', '?', 'x', 'Z'),
        }
        for origen, estados in invalidos_por_origen.items():
            for estado in estados:
                with self.subTest(origen=origen, estado=estado):
                    resultado = validador.validar(
                        _revision([_celda(estado=estado)], origen=origen),
                        _ficha(), _catalogo())
                    self.assertEqual(resultado['rechazadas'][0]['regla'], 5)

    def test_la_traduccion_de_marcas_reutiliza_mapa_estado(self):
        for estado in ('X', 'M', '/', 'P'):
            with self.subTest(estado=estado):
                resultado = validador.validar(
                    _revision([_celda(estado=estado)]), _ficha(), _catalogo())
                self.assertEqual(
                    _una_aceptada(resultado)['despues'],
                    ficha_obra.MAPA_ESTADO[estado.lower()])


class TestRegla6TraduccionSegunOrigen(unittest.TestCase):

    def test_regla_6_blanco_de_tinta_usada_convierte_desconocido_en_P(self):
        resultado = validador.validar(
            _revision([_celda(estado='')]), _ficha('?'), _catalogo())
        aceptada = _una_aceptada(resultado)
        self.assertEqual((aceptada['antes'], aceptada['despues']), ('?', 'P'))
        self.assertEqual(aceptada['accion'], 'actualizar')

    def test_regla_6_blanco_digital_no_toca_para_ningun_origen_digital(self):
        for origen in ('pdf_digital', 'html_digital'):
            with self.subTest(origen=origen):
                resultado = validador.validar(
                    _revision([_celda(estado='')], origen=origen,
                              hoja_usada=False),
                    _ficha('?'), _catalogo())
                aceptada = _una_aceptada(resultado)
                self.assertEqual((aceptada['antes'], aceptada['despues']),
                                 ('?', '?'))
                self.assertEqual(aceptada['accion'], 'conservar')

    def test_regla_6_N_se_descarta_y_no_se_guarda(self):
        resultado = validador.validar(
            _revision([_celda(estado='N')]), _ficha('M'), _catalogo())
        aceptada = _una_aceptada(resultado)
        self.assertEqual((aceptada['antes'], aceptada['despues']), ('M', 'M'))
        self.assertEqual(aceptada['accion'], 'descartar')

    def test_regla_6_no_traduce_blanco_de_tinta_si_la_hoja_no_fue_usada(self):
        resultado = validador.validar(
            _revision([_celda(estado='')], hoja_usada=False),
            _ficha('?'), _catalogo())
        aceptada = _una_aceptada(resultado)
        self.assertEqual((aceptada['antes'], aceptada['despues']), ('?', '?'))
        self.assertEqual(aceptada['accion'], 'conservar')


class TestRegla7BlancoNoBaja(unittest.TestCase):

    def test_regla_7_pasa_blanco_conservando_cualquier_estado_conocido(self):
        for estado in ('X', 'M', '/', 'P', 'N'):
            with self.subTest(estado=estado):
                resultado = validador.validar(
                    _revision([_celda(estado='')]), _ficha(estado), _catalogo())
                aceptada = _una_aceptada(resultado)
                self.assertEqual((aceptada['antes'], aceptada['despues']),
                                 (estado, estado))
                self.assertEqual(aceptada['accion'], 'conservar')

    def test_regla_7_no_protege_un_estado_desconocido(self):
        resultado = validador.validar(
            _revision([_celda(estado='')]), _ficha('?'), _catalogo())
        aceptada = _una_aceptada(resultado)
        self.assertEqual(aceptada['despues'], 'P')
        self.assertEqual(aceptada['accion'], 'actualizar')


class TestRegla8RetrocesoExplicito(unittest.TestCase):

    def test_regla_8_pasa_y_acepta_X_a_M_a_la_primera(self):
        resultado = validador.validar(
            _revision([_celda(estado='M')]), _ficha('X'), _catalogo())
        aceptada = _una_aceptada(resultado)
        self.assertEqual((aceptada['antes'], aceptada['despues']), ('X', 'M'))
        self.assertEqual(aceptada['accion'], 'actualizar')

    def test_regla_8_no_trata_un_blanco_como_retroceso_explicito(self):
        resultado = validador.validar(
            _revision([_celda(estado='')]), _ficha('X'), _catalogo())
        aceptada = _una_aceptada(resultado)
        self.assertEqual((aceptada['antes'], aceptada['despues']), ('X', 'X'))
        self.assertEqual(aceptada['accion'], 'conservar')

    def test_regla_8_P_de_tinta_es_marca_explicita_y_no_blanco(self):
        casos = (
            ('M', 'actualizar',
             'regla 8: la marca explicita se acepta a la primera'),
            ('P', 'conservar', 'mismo estado; no hay cambio'),
        )
        for antes, accion, motivo in casos:
            with self.subTest(antes=antes):
                resultado = validador.validar(
                    _revision([_celda(estado='P')], origen='tinta'),
                    _ficha(antes), _catalogo())
                aceptada = _una_aceptada(resultado)
                self.assertEqual(
                    (aceptada['antes'], aceptada['despues']), (antes, 'P'))
                self.assertEqual(aceptada['accion'], accion)
                self.assertEqual(aceptada['motivo'], motivo)


class TestRegla9SinTintaNoHayCambio(unittest.TestCase):

    def test_regla_9_pasa_con_marca_en_hoja_de_tinta_usada(self):
        resultado = validador.validar(
            _revision([_celda(estado='X')], hoja_usada=True),
            _ficha('?'), _catalogo())
        self.assertTrue(resultado['aplicable'])
        self.assertEqual(_una_aceptada(resultado)['despues'], 'X')

    def test_regla_9_falla_con_marca_en_hoja_de_tinta_no_usada(self):
        resultado = validador.validar(
            _revision([_celda(estado='X')], hoja_usada=False),
            _ficha('?'), _catalogo())
        self.assertFalse(resultado['aplicable'])
        self.assertEqual(resultado['rechazadas'][0]['regla'], 9)
        self.assertIn('sin tinta no hay cambio',
                      resultado['rechazadas'][0]['motivo'])

    def test_regla_9_no_bloquea_una_marca_de_origen_digital(self):
        resultado = validador.validar(
            _revision([_celda(estado='X')], origen='pdf_digital',
                      hoja_usada=False),
            _ficha('?'), _catalogo())
        self.assertTrue(resultado['aplicable'])


class TestRegla10FechaObligatoria(unittest.TestCase):

    def test_regla_10_pasa_con_fecha_explicita_DD_MM_AAAA(self):
        resultado = validador.validar(
            _revision(fecha='05/08/2026'), _ficha(), _catalogo())
        self.assertTrue(resultado['aplicable'])

    def test_regla_10_falla_si_falta_aunque_haya_timestamp_en_metadata(self):
        revision = _revision(fecha='')
        revision['metadata']['generado_en'] = '2026-08-25T12:00:00+02:00'
        resultado = validador.validar(revision, _ficha(), _catalogo())
        self.assertFalse(resultado['aplicable'])
        self.assertTrue(any('regla 10' in error for error in resultado['errores']))

    def test_regla_10_falla_si_la_fecha_no_tiene_el_formato_aprobado(self):
        resultado = validador.validar(
            _revision(fecha='2026-08-25'), _ficha(), _catalogo())
        self.assertTrue(any('regla 10' in error for error in resultado['errores']))


class TestCruceConComportamientoExistente(unittest.TestCase):

    def test_blanco_sobre_X_toma_la_misma_decision_que_marcar_no_empezados(self):
        estados_legacy = {
            CLAVE: {'v': 'X', 'f': '24/08/2026', 'r': 'rev_anterior'}}
        cambios_legacy = lector.marcar_no_empezados(
            estados_legacy, [CLAVE], set(), '25/08/2026', 'rev_nueva')

        resultado = validador.validar(
            _revision([_celda(estado='')]), _ficha('X'), _catalogo())
        aceptada = _una_aceptada(resultado)

        self.assertEqual(cambios_legacy, [])
        self.assertEqual(estados_legacy[CLAVE]['v'], aceptada['despues'])
        self.assertEqual(aceptada['accion'], 'conservar')

    def test_blanco_sobre_desconocido_toma_la_misma_decision_que_legacy(self):
        estados_legacy = {
            CLAVE: {'v': '?', 'f': '24/08/2026', 'r': 'rev_anterior'}}
        cambios_legacy = lector.marcar_no_empezados(
            estados_legacy, [CLAVE], set(), '25/08/2026', 'rev_nueva')

        resultado = validador.validar(
            _revision([_celda(estado='')]), _ficha('?'), _catalogo())
        aceptada = _una_aceptada(resultado)

        self.assertEqual(cambios_legacy, [(CLAVE, '?', 'P')])
        self.assertEqual(estados_legacy[CLAVE]['v'], aceptada['despues'])
        self.assertEqual(aceptada['accion'], 'actualizar')


class TestResultadoYAislamiento(unittest.TestCase):

    def test_resultado_es_consumible_y_resume_acciones(self):
        celdas = [
            _celda(estado='X'),
            _celda(clave='p1__pb__cableado__a', estado=''),
            _celda(clave='p1__pb__tajo_especial__a', estado='N'),
        ]
        resultado = validador.validar(
            _revision(celdas, origen='html_digital', hoja_usada=False),
            _ficha('?'), _catalogo())
        self.assertEqual(
            [celda['accion'] for celda in resultado['aceptadas']],
            ['actualizar', 'conservar', 'descartar'])
        self.assertEqual(resultado['resumen'], {
            'total': 3, 'aceptadas': 3, 'rechazadas': 0,
            'cambios': 1, 'sin_cambio': 1, 'descartadas': 1,
        })

    def test_una_celda_rechazada_hace_el_resultado_no_aplicable(self):
        resultado = validador.validar(
            _revision([_celda(), _celda(clave='mal')]),
            _ficha(), _catalogo())
        self.assertEqual(len(resultado['aceptadas']), 1)
        self.assertEqual(len(resultado['rechazadas']), 1)
        self.assertFalse(resultado['aplicable'])

    def test_avisos_de_metadata_se_propagan_sin_bloquear(self):
        resultado = validador.validar(
            _revision(avisos=['clave sin resolver en pagina 2']),
            _ficha(), _catalogo())
        self.assertTrue(resultado['aplicable'])
        self.assertIn('clave sin resolver en pagina 2', resultado['avisos'])

    def test_confianza_dudosa_genera_aviso_no_bloqueante(self):
        resultado = validador.validar(
            _revision([_celda(confianza='dudosa')]), _ficha(), _catalogo())
        self.assertTrue(resultado['aplicable'])
        self.assertTrue(any('confianza dudosa' in aviso
                            for aviso in resultado['avisos']))

    def test_validar_no_modifica_revision_ficha_ni_catalogo(self):
        revision, ficha, catalogo = _revision(), _ficha(), _catalogo()
        copias = copy.deepcopy((revision, ficha, catalogo))
        validador.validar(revision, ficha, catalogo)
        self.assertEqual((revision, ficha, catalogo), copias)

    def test_forma_invalida_de_celda_se_rechaza_con_motivo(self):
        revision = _revision([{'clave': CLAVE, 'estado_leido': 'X'}])
        resultado = validador.validar(revision, _ficha(), _catalogo())
        self.assertFalse(resultado['aplicable'])
        self.assertIn('confianza', resultado['rechazadas'][0]['motivo'])

    def test_origen_desconocido_bloquea_la_revision(self):
        resultado = validador.validar(
            _revision(origen='inventado'), _ficha(), _catalogo())
        self.assertFalse(resultado['aplicable'])
        self.assertTrue(any('origen' in error for error in resultado['errores']))


if __name__ == '__main__':
    unittest.main()
