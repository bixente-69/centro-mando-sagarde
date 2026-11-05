# -*- coding: utf-8 -*-
"""P1 sesion 1: guardar las transiciones celda a celda y resumirlas.

Datos exclusivamente sinteticos. Regla del proyecto: un desconocido no se
convierte en cero; una revision antigua sin transiciones guardadas dice
"no se puede saber", nunca "0 cambios".
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cambios_revision as cr
import trazabilidad_revisiones as tr


def _celda(clave, antes, despues, accion='actualizar'):
    return {'clave': clave, 'antes': antes, 'despues': despues,
            'accion': accion}


def _aplicacion(aceptadas, cambios=None):
    n = sum(1 for c in aceptadas if c['accion'] == 'actualizar')
    return {
        'escrito': True,
        'aceptadas': aceptadas,
        'resumen': {'total': len(aceptadas), 'aceptadas': len(aceptadas),
                    'rechazadas': 0,
                    'cambios': n if cambios is None else cambios,
                    'sin_cambio': len(aceptadas) - n, 'descartadas': 0},
    }


def _revision(rid='o__01/09/2026__x__1', fecha='01/09/2026'):
    return {'revision_id': rid, 'obra': 'o', 'fecha': fecha,
            'origen': 'html_digital', 'fuente': 'f.html', 'metadata': {}}


class TestGuardarTransiciones(unittest.TestCase):

    def test_entrada_guarda_solo_las_celdas_que_cambian(self):
        ap = _aplicacion([
            _celda('p1__pb__tubos__A', 'P', 'X'),
            _celda('p1__pb__tubos__B', 'X', 'X', accion='sin_cambio'),
            _celda('p1__p1__cajas__A', '/', 'M'),
        ])
        e = tr._entrada(_revision(), ap, True, 3)
        self.assertEqual(e['transiciones'],
                         [['p1__pb__tubos__A', 'P', 'X'],
                          ['p1__p1__cajas__A', '/', 'M']])

    def test_sin_detalle_aceptadas_es_desconocido_no_lista_vacia(self):
        ap = _aplicacion([])
        del ap['aceptadas']
        e = tr._entrada(_revision(), ap, True, 0)
        self.assertIsNone(e['transiciones'])

    def test_transiciones_incoherentes_con_el_resumen_no_se_dan_por_buenas(self):
        ap = _aplicacion([_celda('p1__pb__tubos__A', 'P', 'X')], cambios=5)
        e = tr._entrada(_revision(), ap, True, 1)
        self.assertIsNone(e['transiciones'])

    def test_celda_nueva_guarda_antes_none(self):
        ap = _aplicacion([_celda('p1__pb__tubos__A', None, 'P')])
        e = tr._entrada(_revision(), ap, True, 1)
        self.assertEqual(e['transiciones'], [['p1__pb__tubos__A', None, 'P']])


class TestResumirTransiciones(unittest.TestCase):

    def test_suben_bajan_y_reparto(self):
        t = [['p1__pb__tubos__A', 'P', 'X'],
             ['p1__pb__tubos__B', '/', 'M'],
             ['p1__p1__cajas__A', 'X', 'P'],      # baja
             ['p1__p1__cajas__B', '?', 'P']]      # promocion, NO baja
        r = cr.resumir_transiciones(t)
        self.assertTrue(r['conocido'])
        self.assertEqual(r['total'], 4)
        self.assertEqual(r['bajan'], [['p1__p1__cajas__A', 'X', 'P']])
        self.assertEqual(r['a_estado'], {'X': 1, 'M': 1, 'P': 2})
        self.assertEqual(r['por_tajo'], {'tubos': 2, 'cajas': 2})
        self.assertEqual(r['por_planta'], {('p1', 'pb'): 2, ('p1', 'p1'): 2})

    def test_cero_cambios_conocidos_no_es_desconocido(self):
        r = cr.resumir_transiciones([])
        self.assertTrue(r['conocido'])
        self.assertEqual(r['total'], 0)

    def test_none_es_desconocido(self):
        r = cr.resumir_transiciones(None)
        self.assertFalse(r['conocido'])
        self.assertNotIn('total', r)

    def test_mismo_estado_no_es_bajada(self):
        r = cr.resumir_transiciones([['p1__pb__tubos__A', 'M', 'M']])
        self.assertEqual(r['bajan'], [])

    def test_n_no_cuenta_como_bajada(self):
        r = cr.resumir_transiciones([['p1__pb__tubos__A', 'X', 'N']])
        self.assertEqual(r['bajan'], [])


class TestUltimaRevisionDelLog(unittest.TestCase):

    def _log(self, entradas):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ruta = Path(tmp.name) / 'log.jsonl'
        ruta.write_text(
            ''.join(json.dumps(e) + '\n' for e in entradas), encoding='utf-8')
        return ruta

    def test_reaplicar_la_misma_revision_sin_cambios_no_borra_sus_transiciones(self):
        ruta = self._log([
            {'revision_id': 'r2', 'fecha': '10/10/2026',
             'origen': 'html_digital',
             'transiciones': [['p1__pb__tubos__A', 'P', 'X']]},
            {'revision_id': 'r2', 'fecha': '10/10/2026',
             'origen': 'html_digital', 'transiciones': []},
        ])
        u = cr.ultima_revision(ruta)
        self.assertEqual(u['revision_id'], 'r2')
        self.assertTrue(u['conocido'])
        self.assertEqual(u['transiciones'], [['p1__pb__tubos__A', 'P', 'X']])

    def test_manda_la_fecha_mas_reciente_no_el_orden_del_fichero(self):
        ruta = self._log([
            {'revision_id': 'a_nueva', 'fecha': '02/11/2026',
             'origen': 'html_digital', 'transiciones': []},
            {'revision_id': 'z_vieja', 'fecha': '09/10/2026',
             'origen': 'html_digital', 'transiciones': []},
        ])
        # 'z_vieja' > 'a_nueva' alfabeticamente: debe mandar la FECHA.
        self.assertEqual(cr.ultima_revision(ruta)['revision_id'], 'a_nueva')

    def test_el_historial_consolidado_no_es_una_revision_de_campo(self):
        ruta = self._log([
            {'revision_id': 'h', 'fecha': '30/10/2026',
             'origen': 'historial_consolidado', 'transiciones': []},
            {'revision_id': 'r1', 'fecha': '09/10/2026',
             'origen': 'html_digital', 'transiciones': []},
        ])
        self.assertEqual(cr.ultima_revision(ruta)['revision_id'], 'r1')

    def test_entradas_antiguas_sin_clave_son_desconocido_no_cero(self):
        ruta = self._log([
            {'revision_id': 'r1', 'fecha': '09/10/2026',
             'origen': 'html_digital', 'celdas_cambiadas': 7},
        ])
        u = cr.ultima_revision(ruta)
        self.assertFalse(u['conocido'])
        self.assertEqual(u['celdas_cambiadas_sin_detalle'], 7)

    def test_sin_log_o_vacio_devuelve_none(self):
        self.assertIsNone(cr.ultima_revision(Path('/no/existe.jsonl')))
        self.assertIsNone(cr.ultima_revision(self._log([])))


if __name__ == '__main__':
    unittest.main()
