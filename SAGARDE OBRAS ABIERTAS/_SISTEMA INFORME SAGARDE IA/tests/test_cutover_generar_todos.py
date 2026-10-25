# -*- coding: utf-8 -*-
"""Cutover de generar_todos al motor comun, con datos sinteticos minimos."""
import contextlib
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aplicar_revision
import fixtures
import generar_todos as gt


CLAVE = 'p1__pb__tubeado__A'
FECHA = '01/09/2026'
SNAPSHOT = [{
    'task': 'Tubeado',
    'building': 'P1',
    'floor': 'PB',
    'unit': 'A',
    'status': 'X',
}]


def _ficha(obra_id, estado='?'):
    ficha = fixtures.ficha_minima()
    ficha['id'] = obra_id
    estados = {}
    for bloque in ficha['estructura']['bloques']:
        for portal in bloque['portales']:
            for planta in portal['plantas']:
                for ubicacion in planta['ubicaciones']:
                    for tajo in ficha['tajos']['detalle']:
                        clave = (f"{portal['id']}__{planta['id']}__"
                                 f"{tajo['id']}__{ubicacion['id']}")
                        estados[clave] = {
                            'v': estado, 'f': '31/08/2026',
                            'r': 'rev_31082026',
                        }
    ficha['estados'] = estados
    return ficha


def _obra(obra_id, nombre):
    return {
        'id': obra_id,
        'nombre': nombre,
        'adaptador': f'adaptador_{obra_id}',
    }


class TestLaUltimaRevisionManda(unittest.TestCase):
    """28/09/2026 (Bixente): "un tajo se puede revertir en cualquier momento;
    hay que tener en cuenta lo que este reflejado en la ultima revision".

    Caso real de Mungia: la ficha tenia M, las hojas del 04/09 y del 10/09
    marcaron X, pero un fichero de correcciones del 25/08 se aplicaba DESPUES
    de la ultima hoja ("la correccion es el valor final") y devolvia la celda
    a M. Los dos caminos (antiguo y motor comun) lo hacian igual, asi que la
    salvaguarda de doble calculo no podia verlo.
    """

    def _aplicar(self, fecha_correcciones, fecha_hoja='10/09/2026'):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as carpeta:
            os.makedirs(os.path.join(carpeta, 'REVISIONES', '_SISTEMA'))
            ruta = os.path.join(
                carpeta, 'REVISIONES', '_SISTEMA',
                f'REVISION {fecha_correcciones}.pdf.correcciones.json')
            with open(ruta, 'w', encoding='utf-8') as f:
                json.dump({'estados': {CLAVE: 'M'}}, f)
            ficha = _ficha('pruebas', estado='M')
            with (
                    mock.patch.object(gt, '_mapa_tajos_cortos', return_value={}),
                    mock.patch.object(gt.fichas, 'guardar'),
                    contextlib.redirect_stdout(io.StringIO())):
                resultado, aplicada = gt.actualizar_ficha_con_salvaguarda(
                    _obra('pruebas', 'OBRA CORRECCIONES'), carpeta, ficha,
                    SNAPSHOT, fecha_hoja)
        self.assertTrue(aplicada)
        return resultado['estados'][CLAVE]['v']

    def test_una_correccion_mas_vieja_que_la_ultima_hoja_no_la_pisa(self):
        # SNAPSHOT dice X (hoja del 10/09); la correccion del 25/08 dice M.
        self.assertEqual(self._aplicar('25082026'), 'X')

    def test_una_correccion_de_la_fecha_de_la_hoja_sigue_siendo_el_valor_final(self):
        self.assertEqual(self._aplicar('10092026'), 'M')

    def test_una_correccion_posterior_a_la_ultima_hoja_sigue_siendo_el_valor_final(self):
        self.assertEqual(self._aplicar('12092026'), 'M')


class TestCutoverGenerarTodos(unittest.TestCase):

    def _parches_entrada(self, correcciones=None):
        return (
            mock.patch.object(
                gt, '_correcciones_mas_recientes',
                return_value=correcciones or {}),
            mock.patch.object(gt, '_mapa_tajos_cortos', return_value={}),
        )

    def test_paridad_exacta_guarda_el_resultado_del_motor_nuevo(self):
        ficha = _ficha('pruebas')
        parche_correcciones, parche_mapa = self._parches_entrada(
            {CLAVE: 'P'})
        with (
                parche_correcciones,
                parche_mapa,
                mock.patch.object(gt.fichas, 'guardar') as guardar):
            ficha_resultado, aplicada = gt.actualizar_ficha_con_salvaguarda(
                _obra('pruebas', 'OBRA PARIDAD'), 'carpeta-sintetica',
                ficha, SNAPSHOT, FECHA)

        self.assertTrue(aplicada)
        guardar.assert_called_once_with('carpeta-sintetica', ficha_resultado)
        estado = ficha_resultado['estados'][CLAVE]
        self.assertEqual(estado['v'], 'P')
        self.assertIn('historial_consolidado', estado['r'])
        # apply_revision (motor comun) solo toca 'estados', nunca
        # 'revisiones' -- por eso se adopta el valor ya calculado por el
        # camino antiguo (ficha_antigua, via ficha_obra.actualizar), que si
        # lo mantiene. Bug real encontrado en Gernika el 11/09/2026: 155
        # celdas avanzaban pero 'revisiones' se quedaba en su ultima entrada
        # de julio, asi que resumen_obras.json (la tarjeta del portal)
        # seguia mostrando la fecha vieja aunque el panel de la obra ya
        # tuviera los datos frescos.
        self.assertEqual(
            [r['id'] for r in ficha_resultado['revisiones']],
            ['rev_01092026'])
        self.assertEqual(ficha_resultado['revisiones'][0]['fecha'], FECHA)

    def test_discrepancia_de_una_obra_no_impide_actualizar_la_siguiente(self):
        obras = [
            (_obra('pruebas', 'OBRA DISCREPANTE'), _ficha('pruebas')),
            (_obra('gernika', 'OBRA CON PARIDAD'), _ficha('gernika')),
        ]
        aplicar_real = aplicar_revision.apply_revision

        def aplicar_divergente(revision, ficha, catalogo, dry_run=True):
            resultado = aplicar_real(
                revision, ficha, catalogo, dry_run=dry_run)
            if (revision['obra'] == 'pruebas'
                    and resultado.get('ficha_actualizada')):
                resultado['ficha_actualizada']['estados'][CLAVE]['v'] = 'M'
            return resultado

        resultados = {}
        salida = io.StringIO()
        parche_correcciones, parche_mapa = self._parches_entrada()
        with (
                parche_correcciones,
                parche_mapa,
                mock.patch.object(
                    aplicar_revision, 'apply_revision',
                    side_effect=aplicar_divergente) as aplicar,
                mock.patch.object(gt.fichas, 'guardar') as guardar,
                contextlib.redirect_stdout(salida)):
            for obra, ficha in obras:
                resultados[obra['id']] = gt.actualizar_ficha_con_salvaguarda(
                    obra, f"carpeta-{obra['id']}", ficha, SNAPSHOT, FECHA)

        ficha_discrepante, aplicada_discrepante = resultados['pruebas']
        ficha_par, aplicada_par = resultados['gernika']
        self.assertFalse(aplicada_discrepante)
        self.assertEqual(ficha_discrepante['estados'][CLAVE]['v'], '?')
        self.assertTrue(aplicada_par)
        self.assertEqual(ficha_par['estados'][CLAVE]['v'], 'X')
        self.assertEqual(aplicar.call_count, 2)
        guardar.assert_called_once_with('carpeta-gernika', ficha_par)

        texto = salida.getvalue()
        self.assertIn('OBRA DISCREPANTE', texto)
        self.assertIn(CLAVE, texto)
        self.assertIn("antiguo='X'; nuevo='M'", texto)
        self.assertIn('las demas obras continuan', texto)
        self.assertIn('OBRA CON PARIDAD', texto)


class TestDiferenciasEstados(unittest.TestCase):
    """Que cuenta y que NO cuenta como diferencia entre los dos caminos.

    Olabeaga (1.225 claves) y Barakaldo (3.286) daban el aviso CUTOVER en cada
    pasada por celdas "fantasma": el camino antiguo (`_completar_matriz`) rellena
    con '?' los tajos del catalogo en viviendas cuya hoja no los imprime, y el
    motor comun, fiel a "la ultima hoja manda", no las crea. Una celda '?' que
    solo existe en el camino antiguo no es un dato medido: no es una
    discrepancia. Cualquier otra diferencia SIGUE siendo discrepancia."""

    @staticmethod
    def _est(**valores):
        return {k: {'v': v, 'f': '01/01/2026', 'r': 'rev'} for k, v in valores.items()}

    def _comparar(self, antiguos, nuevos):
        return gt._diferencias_estados(antiguos, nuevos)

    def test_un_interrogante_solo_del_camino_antiguo_no_es_diferencia(self):
        claves, diferencias, fantasmas = self._comparar(
            self._est(a='?', b='X'), self._est(b='X'))
        self.assertEqual(diferencias, [])
        self.assertEqual(fantasmas, ['a'])
        # Solo cuenta como comparada la celda que existe en los dos.
        self.assertEqual(len(claves), 1)

    def test_los_fantasmas_se_cuentan_para_decirlo(self):
        _claves, _dif, fantasmas = self._comparar(
            self._est(a='?', b='?', c='?', d='X'), self._est(d='X'))
        self.assertEqual(sorted(fantasmas), ['a', 'b', 'c'])

    def test_una_celda_con_dato_que_falta_en_el_motor_comun_si_es_diferencia(self):
        # El camino antiguo tiene X y el motor comun la perdio: grave.
        for valor in ('X', 'M', '/', 'P', 'N'):
            _claves, diferencias, fantasmas = self._comparar(
                self._est(a=valor), {})
            self.assertEqual([d[0] for d in diferencias], ['a'], valor)
            self.assertEqual(fantasmas, [], valor)

    def test_la_direccion_contraria_sigue_siendo_diferencia(self):
        # Solo se perdona '?' que sobra en el camino ANTIGUO. Un '?' que
        # aparece unicamente en el motor comun es otra cosa y se sigue viendo.
        _claves, diferencias, fantasmas = self._comparar({}, self._est(a='?'))
        self.assertEqual([d[0] for d in diferencias], ['a'])
        self.assertEqual(fantasmas, [])

    def test_interrogante_frente_a_un_valor_real_sigue_siendo_diferencia(self):
        for valor in ('X', 'M', '/', 'P', 'N'):
            _claves, diferencias, _f = self._comparar(
                self._est(a='?'), self._est(a=valor))
            self.assertEqual([d[0] for d in diferencias], ['a'], valor)

    def test_dos_valores_reales_distintos_siguen_siendo_diferencia(self):
        _claves, diferencias, _f = self._comparar(
            self._est(a='X'), self._est(a='M'))
        self.assertEqual(diferencias, [('a', 'X', 'M')])

    def test_valores_iguales_y_vacio_no_dan_diferencias(self):
        self.assertEqual(self._comparar({}, {})[1], [])
        self.assertEqual(self._comparar(self._est(a='X'), self._est(a='X'))[1], [])
        self.assertEqual(self._comparar(self._est(a='?'), self._est(a='?'))[1], [])


class TestSalvaguardaConCeldasFantasma(unittest.TestCase):
    """La salvaguarda completa con fantasmas, sin tocar disco."""

    def _ejecutar(self, fantasmas=0, divergir=False):
        ficha = _ficha('pruebas')
        real = gt.fichas.actualizar_desde_snapshot

        def con_fantasmas(ficha_entrada, snapshot, fecha, **kwargs):
            ficha_antigua, cambios = real(ficha_entrada, snapshot, fecha, **kwargs)
            for i in range(fantasmas):
                ficha_antigua['estados'][f'p1__pb__cub_antena_cableado__F{i}'] = {
                    'v': '?', 'f': '31/08/2026', 'r': 'rev_31082026'}
            if divergir:
                ficha_antigua['estados'][CLAVE]['v'] = 'M'
            return ficha_antigua, cambios

        salida = io.StringIO()
        with (
                mock.patch.object(gt, '_correcciones_mas_recientes', return_value={}),
                mock.patch.object(gt, '_mapa_tajos_cortos', return_value={}),
                mock.patch.object(
                    gt.fichas, 'actualizar_desde_snapshot',
                    side_effect=con_fantasmas),
                mock.patch.object(gt.fichas, 'guardar') as guardar,
                contextlib.redirect_stdout(salida)):
            resultado = gt.actualizar_ficha_con_salvaguarda(
                _obra('pruebas', 'OBRA PRUEBA FICHA'), 'carpeta-sintetica',
                ficha, SNAPSHOT, FECHA)
        return resultado, guardar, salida.getvalue()

    def test_con_solo_fantasmas_coincide_y_guarda_sin_crearlos(self):
        (ficha, aplicada), guardar, texto = self._ejecutar(fantasmas=3)
        self.assertTrue(aplicada)
        guardar.assert_called_once()
        # Se guarda el resultado del motor comun: los fantasmas no se escriben.
        self.assertFalse(any('cub_antena_cableado' in k for k in ficha['estados']))
        self.assertEqual(ficha['estados'][CLAVE]['v'], 'X')
        self.assertNotIn('AVISO CUTOVER', texto)

    def test_el_mensaje_dice_cuantos_fantasmas_se_han_ignorado(self):
        _res, _guardar, texto = self._ejecutar(fantasmas=3)
        self.assertIn('3', texto)
        self.assertIn('fantasma', texto)

    def test_sin_fantasmas_el_mensaje_no_los_menciona(self):
        _res, _guardar, texto = self._ejecutar(fantasmas=0)
        self.assertNotIn('fantasma', texto)

    def test_una_diferencia_real_con_fantasmas_sigue_bloqueando_la_ficha(self):
        (ficha, aplicada), guardar, texto = self._ejecutar(
            fantasmas=5, divergir=True)
        self.assertFalse(aplicada)
        guardar.assert_not_called()
        self.assertIn('AVISO CUTOVER FICHA', texto)
        self.assertIn("antiguo='M'; nuevo='X'", texto)
        # El ruido ya no tapa la diferencia real: solo se lista esa.
        self.assertNotIn('cub_antena_cableado', texto)
        self.assertIn('difieren en 1 clave', texto)

    def test_el_resultado_expone_cuantos_fantasmas_ignoro(self):
        ficha = _ficha('pruebas')
        real = gt.fichas.actualizar_desde_snapshot

        def con_dos(ficha_entrada, snapshot, fecha, **kwargs):
            ficha_antigua, cambios = real(ficha_entrada, snapshot, fecha, **kwargs)
            for i in range(2):
                ficha_antigua['estados'][f'x__y__z__{i}'] = {'v': '?'}
            return ficha_antigua, cambios

        with mock.patch.object(
                gt.fichas, 'actualizar_desde_snapshot', side_effect=con_dos):
            res = gt.calcular_actualizacion_ficha_con_salvaguarda(
                _obra('pruebas', 'OBRA'), ficha, SNAPSHOT, FECHA,
                correcciones={}, mapa_tajos_cortos={})
        self.assertTrue(res['coincide'])
        self.assertEqual(res['fantasmas_ignoradas'], 2)
        self.assertEqual(res['claves_comparadas'], len(ficha['estados']))


if __name__ == '__main__':
    unittest.main()
