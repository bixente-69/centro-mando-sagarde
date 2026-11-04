# -*- coding: utf-8 -*-
"""Pruebas que matan mutaciones supervivientes de `ficha_obra.py`.

Origen: auditoria por mutacion del 04/11/2026
(`_SISTEMA/docs/auditorias_nube_2026-11-04/B_mutaciones.md`). `ficha_obra` esta
bien cubierta (19 de 24 mutaciones murieron), pero cinco sobrevivieron; entre
ellas una que la prueba existente de "planta que se queda vacia" no distingue
por casualidad: marca la planta tras quitar la PRIMERA unidad y el resultado
final sale igual. Cada prueba dice que mutacion mata (FOxx).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ficha_obra
import fixtures


class TestNormalizarEstado(unittest.TestCase):

    def test_quita_espacios_y_pasa_a_minusculas(self):
        # Mata FO04: una casilla " X " (espacios de un sidecar o de un Excel)
        # es una X, no un estado no reconocido que acaba guardado como '?'.
        self.assertEqual(ficha_obra._normalizar_estado(' X '), 'x')
        self.assertEqual(ficha_obra._normalizar_estado('  '), '')
        self.assertEqual(ficha_obra._normalizar_estado(None), '')

    def test_un_estado_con_espacios_se_guarda_como_su_letra(self):
        ficha = fixtures.ficha_minima()
        ficha, cambios = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado=' M ')]))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')
        self.assertEqual(cambios['estados_no_reconocidos'], [])


class TestMismoEstadoEnOtraRevision(unittest.TestCase):

    def test_confirmar_el_mismo_estado_actualiza_fecha_y_revision(self):
        # Mata FO15: si la revision del 30/07 vuelve a ver la X, la celda
        # queda fechada y atribuida a ESA revision (la ultima que la vio), no
        # a la primera. Sin esto la trazabilidad miente en silencio.
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='X')]))
        nueva = fixtures.item(estado='X')
        nueva['ultima_fecha'] = '30/07/2026'
        ficha, cambios = ficha_obra.actualizar(
            ficha, fixtures.prioridades([nueva], revision='30/07/2026'))
        celda = ficha['estados']['p1__pb__tubeado__A']
        self.assertEqual(celda, {'v': 'X', 'f': '30/07/2026',
                                 'r': 'rev_30072026'})
        self.assertEqual(cambios['estados_cambiados'], [])


class TestTajoNuevoSinOrden(unittest.TestCase):

    def test_un_tajo_sin_orden_se_coloca_el_ultimo(self):
        # Mata FO22: sin escalafon declarado no se cuela el primero (orden 0);
        # va al final (9999), tras los que si lo tienen (10 y 20).
        ficha = fixtures.ficha_minima()
        nuevo = fixtures.item(tarea='nuevo', trabajo='Nuevo', estado='X',
                              orden=None)
        ficha, cambios = ficha_obra.actualizar(
            ficha, fixtures.prioridades([nuevo]))
        self.assertEqual(cambios['tajos_nuevos'], ['nuevo'])
        self.assertEqual([t['id'] for t in ficha['tajos']['detalle']],
                         ['tubeado', 'cableado', 'nuevo'])
        self.assertEqual(ficha['tajos']['aplicables'],
                         ['tubeado', 'cableado', 'nuevo'])


class TestRetirarEstructuraCasosLimite(unittest.TestCase):

    def _ficha(self):
        ficha = fixtures.ficha_minima()
        ficha['estados'] = {
            'p1__pb__tubeado__A': {'v': '?', 'f': None, 'r': None},
            'p1__pb__tubeado__B': {'v': '?', 'f': None, 'r': None},
            'p1__pb__cableado__A': {'v': 'P', 'f': None, 'r': None},
        }
        return ficha

    def test_una_planta_que_conserva_una_unidad_no_se_marca_retirada(self):
        # Mata FO20. Se retira solo la B de PB: la A sigue ahi y la planta NO
        # esta retirada. La prueba existente quita las DOS unidades y no
        # distingue "marcar al quedar vacia" de "marcar tras quitar la
        # primera", porque el resultado final es el mismo.
        ausentes = {'no_fiable': None, 'tajos': [], 'unidades': [{
            'portal_id': 'p1', 'planta_id': 'pb', 'unidad': 'B',
            'edificio': 'P1', 'planta': 'PB', 'tipo': 'vivienda',
            'nombre': None, 'celdas': {}}]}
        nueva, _ = ficha_obra.retirar_estructura_ausente_en_hoja(
            self._ficha(), ausentes, '04/10/2026', 'rev_x')
        plantas = nueva['estructura']['bloques'][0]['portales'][0]['plantas']
        self.assertEqual([u['id'] for u in plantas[0]['ubicaciones']], ['A'])
        self.assertNotIn('retirada', plantas[0])
        self.assertNotIn('retirada', plantas[1])

    def test_retirar_solo_un_tajo_cuenta_como_retirado(self):
        # Mata FO21. Ninguna unidad se va, solo una celda de tajo (en P, sin
        # avance): el informe tiene que decir que SE RETIRO algo; si no, el
        # llamador cree que no cambio nada y no guarda ni avisa.
        ficha = self._ficha()
        ausentes = {'no_fiable': None, 'unidades': [], 'tajos': [{
            'portal_id': 'p1', 'planta_id': 'pb', 'unidad': 'A',
            'tajo': 'cableado', 'clave': 'p1__pb__cableado__A',
            'estado': 'P'}]}
        nueva, informe = ficha_obra.retirar_estructura_ausente_en_hoja(
            ficha, ausentes, '04/10/2026', 'rev_x')
        self.assertTrue(informe['retirado'])
        self.assertEqual(informe['celdas_retiradas'], ['p1__pb__cableado__A'])
        self.assertEqual(informe['unidades_retiradas'], [])
        self.assertNotIn('p1__pb__cableado__A', nueva['estados'])
        # y la original no se toca
        self.assertIn('p1__pb__cableado__A', ficha['estados'])


if __name__ == '__main__':
    unittest.main()
