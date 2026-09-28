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


if __name__ == '__main__':
    unittest.main()
