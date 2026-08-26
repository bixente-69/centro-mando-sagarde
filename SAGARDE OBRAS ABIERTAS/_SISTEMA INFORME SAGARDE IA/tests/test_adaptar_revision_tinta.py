# -*- coding: utf-8 -*-
"""Paridad del adaptador de tinta con el flujo A historico."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import adaptar_revision_tinta as adaptador
import aplicar_revision
import fixtures
import leer_hoja_marcada as lector
import validar_revision as validador


FECHA = '05/08/2026'
REVISION_ANTIGUA = 'rev_05082026'
CLAVE_A = 'p1__pb__tubeado__A'
CLAVE_B = 'p1__pb__tubeado__B'
RAIZ_REPOSITORIO = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..'))
RUTA_OBRA_MUNGIA = os.path.join(
    RAIZ_REPOSITORIO, 'SAGARDE OBRAS ABIERTAS', '2026 MUNGIA ACR NEINOR')
RUTA_REVISIONES_MUNGIA = os.path.join(RUTA_OBRA_MUNGIA, 'REVISIONES')
NOMBRE_REVISION_MUNGIA = 'REVISION MUNGIA 27072026'
RUTA_FICHA_MUNGIA_GIT = (
    'SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/'
    'INFORME SAGARDE IA/ficha_obra.json'
)


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


def _candidata(clave, puntos=12, dudosa=None, antes='?'):
    return {
        'clave': clave,
        'puntos': puntos,
        'dudosa': puntos < lector.PUNTOS_DUDOSA if dudosa is None else dudosa,
        'antes': antes,
        'pagina': 1,
        'bloque': 'Bloque 1',
        'portal': 'P1',
        'planta': 'PB',
        'vivienda': clave.split('__')[-1],
        'tajo': 'tubeado',
        'tajo_nombre': 'Tubeado',
        'recorte': None,
        'valor': None,
    }


def _valores(estados):
    return {clave: registro.get('v') for clave, registro in estados.items()}


class CasoAdaptadorTinta(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta_pdf = os.path.join(
            self.temporal.name, 'REVISION PRUEBAS 05082026.pdf')
        with open(self.ruta_pdf, 'wb') as fichero:
            fichero.write(b'%PDF-1.4\nhoja con tinta sintetica\n%%EOF\n')
        self.ruta_sistema = os.path.join(self.temporal.name, '_SISTEMA')
        os.mkdir(self.ruta_sistema)
        self.ruta_candidatas = os.path.join(
            self.ruta_sistema, 'REVISION PRUEBAS 05082026.candidatas.json')
        self.ruta_clasificacion = os.path.join(
            self.ruta_sistema, 'REVISION PRUEBAS 05082026.clasificacion.json')
        self.catalogo = _catalogo()

    def _fuentes(self, candidatas, clasificacion, celdas_hoja=None):
        with open(self.ruta_candidatas, 'w', encoding='utf-8') as fichero:
            json.dump({
                'version': 1,
                'hoja': os.path.basename(self.ruta_pdf),
                'obra': 'pruebas',
                'celdas_hoja': list(celdas_hoja or []),
                'columnas_sin_mapear': [],
                'candidatas': candidatas,
            }, fichero, ensure_ascii=False)
        with open(self.ruta_clasificacion, 'w', encoding='utf-8') as fichero:
            json.dump({'celdas': clasificacion}, fichero, ensure_ascii=False)

    def _revision(self, ficha, sin_marca='pendiente'):
        return adaptador.construir_revision_normalizada_tinta(
            self.ruta_pdf, self.ruta_clasificacion, 'pruebas', ficha,
            FECHA, sin_marca=sin_marca)

    def _camino_nuevo(self, ficha, sin_marca='pendiente'):
        revision = self._revision(ficha, sin_marca=sin_marca)
        validacion = validador.validar(revision, ficha, self.catalogo)
        aplicacion = aplicar_revision.apply_revision(
            revision, ficha, self.catalogo, dry_run=False)
        return revision, validacion, aplicacion

    def _camino_antiguo(self, ficha, candidatas, clasificacion,
                        celdas_hoja=None, sin_marca='pendiente'):
        estados, cambios, dudas = lector.aplicar(
            ficha, candidatas, clasificacion, FECHA, REVISION_ANTIGUA)
        if sin_marca == 'pendiente':
            con_marca = {
                c['clave'] for c in candidatas
                if clasificacion.get(c['clave']) != lector.DESCARTADA
            }
            cambios = cambios + lector.marcar_no_empezados(
                estados, list(celdas_hoja or []), con_marca,
                FECHA, REVISION_ANTIGUA)
        return estados, cambios, dudas


class TestNadaSeDescartaSolo(CasoAdaptadorTinta):
    def test_una_candidata_sin_clasificar_aborta_en_ambos_caminos(self):
        ficha = _ficha({CLAVE_A: '?', CLAVE_B: '?'})
        candidatas = [_candidata(CLAVE_A), _candidata(CLAVE_B)]
        clasificacion = {CLAVE_A: 'X'}
        self._fuentes(candidatas, clasificacion)

        with self.assertRaisesRegex(lector.LecturaImposible, 'sin clasificar'):
            lector.aplicar(
                ficha, candidatas, clasificacion, FECHA, REVISION_ANTIGUA)
        with self.assertRaisesRegex(lector.LecturaImposible, 'sin clasificar'):
            self._revision(ficha)

    def test_descartar_es_explicito_y_no_genera_revision_celda(self):
        ficha = _ficha({CLAVE_A: '?'})
        candidatas = [_candidata(CLAVE_A, puntos=1)]
        clasificacion = {CLAVE_A: lector.DESCARTADA}
        self._fuentes(candidatas, clasificacion)

        estados_antiguos, cambios_antiguos, dudas = self._camino_antiguo(
            ficha, candidatas, clasificacion)
        revision, validacion, aplicacion = self._camino_nuevo(ficha)

        self.assertEqual(cambios_antiguos, [])
        self.assertEqual(len(dudas), 1)
        self.assertEqual(revision['celdas'], [])
        self.assertFalse(revision['metadata']['hoja_usada'])
        self.assertTrue(validacion['aplicable'])
        self.assertEqual(
            _valores(aplicacion['ficha_actualizada']['estados']),
            _valores(estados_antiguos))


class TestSinTintaNoHayCambio(CasoAdaptadorTinta):
    def test_clasificar_una_clave_sin_candidata_aborta_en_ambos(self):
        ficha = _ficha({CLAVE_A: '?', CLAVE_B: '?'})
        candidatas = [_candidata(CLAVE_A)]
        clasificacion = {CLAVE_A: 'X', CLAVE_B: 'X'}
        self._fuentes(candidatas, clasificacion)

        with self.assertRaisesRegex(lector.LecturaImposible,
                                    'Sin tinta no hay cambio'):
            lector.aplicar(
                ficha, candidatas, clasificacion, FECHA, REVISION_ANTIGUA)
        with self.assertRaisesRegex(lector.LecturaImposible,
                                    'Sin tinta no hay cambio'):
            self._revision(ficha)

    def test_un_valor_desconocido_aborta_en_ambos(self):
        ficha = _ficha({CLAVE_A: '?'})
        candidatas = [_candidata(CLAVE_A)]
        clasificacion = {CLAVE_A: 'Z'}
        self._fuentes(candidatas, clasificacion)

        with self.assertRaises(lector.LecturaImposible):
            lector.aplicar(
                ficha, candidatas, clasificacion, FECHA, REVISION_ANTIGUA)
        with self.assertRaises(lector.LecturaImposible):
            self._revision(ficha)

    def test_una_clave_que_no_esta_en_estados_aborta_antes_de_normalizar(self):
        """Aqui no reaparece ``antes=None``: aplicar() conserva la guarda."""
        ficha = _ficha({})
        candidatas = [_candidata(CLAVE_A)]
        clasificacion = {CLAVE_A: 'X'}
        self._fuentes(candidatas, clasificacion)

        with self.assertRaisesRegex(lector.LecturaImposible,
                                    'no tiene esa celda'):
            lector.aplicar(
                ficha, candidatas, clasificacion, FECHA, REVISION_ANTIGUA)
        with self.assertRaisesRegex(lector.LecturaImposible,
                                    'no tiene esa celda'):
            self._revision(ficha)


class TestNormaDeObra(CasoAdaptadorTinta):
    def test_un_retroceso_marcado_se_acepta_a_la_primera_en_ambos(self):
        ficha = _ficha({CLAVE_A: 'X'})
        candidatas = [_candidata(CLAVE_A, antes='X')]
        clasificacion = {CLAVE_A: 'M'}
        self._fuentes(candidatas, clasificacion)

        estados_antiguos, cambios_antiguos, _ = self._camino_antiguo(
            ficha, candidatas, clasificacion)
        revision, validacion, aplicacion = self._camino_nuevo(ficha)

        self.assertEqual(cambios_antiguos, [(CLAVE_A, 'X', 'M')])
        self.assertTrue(validacion['aplicable'])
        self.assertEqual(validacion['resumen']['cambios'], 1)
        self.assertEqual(revision['celdas'][0]['confianza'], 'cierta')
        self.assertEqual(
            _valores(aplicacion['ficha_actualizada']['estados']),
            _valores(estados_antiguos))

    def test_remarcar_lo_mismo_se_conserva_en_ambos(self):
        ficha = _ficha({CLAVE_A: 'X'})
        candidatas = [_candidata(CLAVE_A, antes='X')]
        clasificacion = {CLAVE_A: 'X'}
        self._fuentes(candidatas, clasificacion)

        estados_antiguos, cambios_antiguos, _ = self._camino_antiguo(
            ficha, candidatas, clasificacion)
        revision, validacion, aplicacion = self._camino_nuevo(ficha)

        self.assertEqual(cambios_antiguos, [])
        self.assertEqual(len(revision['celdas']), 1)
        self.assertEqual(validacion['aceptadas'][0]['accion'], 'conservar')
        self.assertEqual(
            _valores(aplicacion['ficha_actualizada']['estados']),
            _valores(estados_antiguos))

    def test_el_adaptador_no_muta_la_ficha(self):
        ficha = _ficha({CLAVE_A: '?', CLAVE_B: '?'})
        copia = copy.deepcopy(ficha)
        candidatas = [_candidata(CLAVE_A)]
        self._fuentes(candidatas, {CLAVE_A: 'X'}, [CLAVE_A, CLAVE_B])

        self._revision(ficha)

        self.assertEqual(ficha, copia)

    def test_sin_marca_pendiente_y_desconocido_replican_el_cli(self):
        ficha = _ficha({CLAVE_A: 'X', CLAVE_B: '?'})
        candidatas = [_candidata(CLAVE_A, antes='X')]
        clasificacion = {CLAVE_A: 'X'}
        celdas_hoja = [CLAVE_A, CLAVE_B]
        self._fuentes(candidatas, clasificacion, celdas_hoja)

        antiguos_p, _, _ = self._camino_antiguo(
            ficha, candidatas, clasificacion, celdas_hoja, 'pendiente')
        revision_p, _, aplicacion_p = self._camino_nuevo(ficha, 'pendiente')
        antiguos_d, _, _ = self._camino_antiguo(
            ficha, candidatas, clasificacion, celdas_hoja, 'desconocido')
        revision_d, _, aplicacion_d = self._camino_nuevo(
            ficha, 'desconocido')

        self.assertEqual({c['estado_leido'] for c in revision_p['celdas']},
                         {'X', ''})
        self.assertEqual([c['estado_leido'] for c in revision_d['celdas']],
                         ['X'])
        self.assertEqual(
            _valores(aplicacion_p['ficha_actualizada']['estados']),
            _valores(antiguos_p))
        self.assertEqual(
            _valores(aplicacion_d['ficha_actualizada']['estados']),
            _valores(antiguos_d))

    def test_corrector_M_a_P_coincide_en_ambos_caminos(self):
        ficha = _ficha({CLAVE_A: 'M'})
        candidatas = [_candidata(CLAVE_A, antes='M')]
        clasificacion = {CLAVE_A: 'P'}
        self._fuentes(candidatas, clasificacion)

        estados_antiguos, cambios_antiguos, _ = self._camino_antiguo(
            ficha, candidatas, clasificacion, sin_marca='desconocido')
        revision, validacion, aplicacion = self._camino_nuevo(
            ficha, 'desconocido')

        self.assertEqual(cambios_antiguos, [(CLAVE_A, 'M', 'P')])
        self.assertEqual(estados_antiguos[CLAVE_A]['v'], 'P')
        self.assertEqual(revision['celdas'][0]['estado_leido'], 'P')
        self.assertEqual(validacion['aceptadas'][0]['accion'], 'actualizar')
        self.assertEqual(
            _valores(aplicacion['ficha_actualizada']['estados']),
            _valores(estados_antiguos))

    def test_descartada_participa_en_el_barrido_como_en_el_cli(self):
        ficha = _ficha({CLAVE_A: '?', CLAVE_B: 'X'})
        candidatas = [_candidata(CLAVE_A, puntos=1),
                      _candidata(CLAVE_B, antes='X')]
        clasificacion = {CLAVE_A: lector.DESCARTADA, CLAVE_B: 'X'}
        celdas_hoja = [CLAVE_A, CLAVE_B]
        self._fuentes(candidatas, clasificacion, celdas_hoja)

        estados_antiguos, _, _ = self._camino_antiguo(
            ficha, candidatas, clasificacion, celdas_hoja)
        revision, validacion, aplicacion = self._camino_nuevo(ficha)

        self.assertEqual(estados_antiguos[CLAVE_A]['v'], 'P')
        self.assertEqual(
            [c['clave'] for c in revision['celdas']], [CLAVE_B, CLAVE_A])
        self.assertEqual(
            [c['estado_leido'] for c in revision['celdas']], ['X', ''])
        self.assertEqual(validacion['resumen']['cambios'], 1)
        self.assertEqual(
            _valores(aplicacion['ficha_actualizada']['estados']),
            _valores(estados_antiguos))

    def test_una_candidata_previa_dudosa_resuelta_se_emite_como_cierta(self):
        ficha = _ficha({CLAVE_A: '?'})
        candidatas = [_candidata(CLAVE_A, puntos=1, dudosa=True)]
        self._fuentes(candidatas, {CLAVE_A: 'X'})

        revision = self._revision(ficha, 'desconocido')

        self.assertEqual(revision['celdas'][0]['confianza'], 'cierta')


class TestContratoAdaptadorTinta(CasoAdaptadorTinta):
    def test_revision_id_es_determinista_y_cambia_con_clasificacion_o_modo(self):
        ficha = _ficha({CLAVE_A: '?'})
        candidatas = [_candidata(CLAVE_A)]
        self._fuentes(candidatas, {CLAVE_A: 'X'})

        revision_1 = self._revision(ficha, 'desconocido')
        revision_2 = self._revision(ficha, 'desconocido')
        revision_pendiente = self._revision(ficha, 'pendiente')
        self._fuentes(candidatas, {CLAVE_A: 'M'})
        revision_distinta = self._revision(ficha, 'desconocido')

        self.assertEqual(revision_1['revision_id'], revision_2['revision_id'])
        self.assertNotEqual(
            revision_1['revision_id'], revision_pendiente['revision_id'])
        self.assertNotEqual(
            revision_1['revision_id'], revision_distinta['revision_id'])

    def test_fecha_obligatoria_y_no_inferida_del_nombre(self):
        with self.assertRaisesRegex(ValueError, 'no se deduce'):
            adaptador.construir_revision_normalizada_tinta(
                self.ruta_pdf, self.ruta_clasificacion, 'pruebas',
                _ficha({}), '')


class TestCasoRealMungia(unittest.TestCase):
    """Regresion empirica de Fase 6, siempre en lectura y memoria."""

    def test_mungia_27_07_propone_las_12_correcciones_completas(self):
        ficha_antes = json.loads(subprocess.run(
            ['git', 'show', f'5c90dec:{RUTA_FICHA_MUNGIA_GIT}'],
            cwd=RAIZ_REPOSITORIO,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.decode('utf-8'))

        ruta_pdf = os.path.join(
            RUTA_REVISIONES_MUNGIA, NOMBRE_REVISION_MUNGIA + '.pdf')
        ruta_sistema = os.path.join(RUTA_REVISIONES_MUNGIA, '_SISTEMA')
        ruta_candidatas = os.path.join(
            ruta_sistema, NOMBRE_REVISION_MUNGIA + '.candidatas.json')
        ruta_clasificacion = os.path.join(
            ruta_sistema, NOMBRE_REVISION_MUNGIA + '.clasificacion.json')
        ruta_correcciones = os.path.join(
            ruta_sistema, NOMBRE_REVISION_MUNGIA + '.pdf.correcciones.json')

        with open(ruta_candidatas, encoding='utf-8') as fichero:
            datos = json.load(fichero)
        with open(ruta_clasificacion, encoding='utf-8') as fichero:
            clasificacion = json.load(fichero)
        clasificacion = clasificacion.get('celdas', clasificacion)
        with open(ruta_correcciones, encoding='utf-8') as fichero:
            correcciones_publicadas = json.load(fichero)['estados']

        revision = adaptador.construir_revision_normalizada_tinta(
            ruta_pdf, ruta_clasificacion, 'mungia', ficha_antes,
            '27/07/2026')
        validacion = validador.validar(
            revision, ficha_antes, validador.cargar_catalogo_tajos())

        estados_antiguos, cambios_antiguos, _dudas = lector.aplicar(
            ficha_antes, datos['candidatas'], clasificacion, '27/07/2026',
            'rev_27072026')
        con_marca = {
            candidata['clave'] for candidata in datos['candidatas']
            if clasificacion.get(candidata['clave']) != lector.DESCARTADA
        }
        cambios_antiguos += lector.marcar_no_empezados(
            estados_antiguos, datos.get('celdas_hoja') or [], con_marca,
            '27/07/2026', 'rev_27072026')

        propuestas_antiguas = {
            clave: despues for clave, _antes, despues in cambios_antiguos}
        propuestas_comunes = {
            celda['clave']: celda['despues']
            for celda in validacion['aceptadas']
            if celda['accion'] == 'actualizar'
        }

        self.assertTrue(validacion['aplicable'], validacion)
        self.assertEqual(validacion['rechazadas'], [])
        self.assertEqual(len(correcciones_publicadas), 12)
        self.assertEqual(validacion['resumen']['cambios'], 12)
        self.assertEqual(propuestas_antiguas, correcciones_publicadas)
        self.assertEqual(propuestas_comunes, correcciones_publicadas)
        self.assertEqual(propuestas_comunes, propuestas_antiguas)


if __name__ == '__main__':
    unittest.main()
