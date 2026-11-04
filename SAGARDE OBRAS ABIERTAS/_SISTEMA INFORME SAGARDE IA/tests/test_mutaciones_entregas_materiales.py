# -*- coding: utf-8 -*-
"""Pruebas que matan mutaciones supervivientes de `entregas_materiales.py`.

Origen: auditoria por mutacion del 04/11/2026
(`_SISTEMA/docs/auditorias_nube_2026-11-04/B_mutaciones.md`). Las cifras de
material salen del registro ENTREGAS y el panel no recalcula nada; aun asi, al
romper a proposito la suma de lineas de una misma entrega, el aviso de "sin
entregas desde hace mas de 30 dias" y la lectura de cantidades y fechas, la
suite siguio en verde. Cada prueba dice que mutacion mata (EMxx).
"""
import os
import sys
import unittest
from datetime import date, datetime

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import entregas_materiales as em

HOY = date(2027, 1, 31)


def _fila(fecha, sumi, alb, cat, mat, tipo, marca, uni, cant, notas=None):
    return [fecha, sumi, alb, cat, mat, tipo, marca, uni, cant, notas]


def _wb(filas):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'ENTREGAS'
    ws.append(em.CABECERA)
    for f in filas:
        ws.append(f)
    return wb


class TestVariasLineasDeLaMismaEntrega(unittest.TestCase):

    def test_dos_lineas_del_mismo_material_y_albaran_se_suman(self):
        # Mata EM17. Mismo dia, suministrador, albaran y material, cantidades
        # distintas (10 y 5): son dos lineas de verdad (no una repetida) y el
        # mes tiene que decir 15. Si la segunda pisara a la primera, el panel
        # publicaria 5 sin ningun aviso.
        ent, avisos = em.leer_registro(_wb([
            _fila(datetime(2026, 10, 1), 'Sumi A', '111', 'TUBO', 'PVC',
                  'GRIS', None, 20, 10),
            _fila(datetime(2026, 10, 1), 'Sumi A', '111', 'TUBO', 'PVC',
                  'GRIS', None, 20, 5),
        ]), HOY)
        self.assertEqual(avisos, [])
        mes = em.agrupar(ent)['meses'][0]
        self.assertEqual(len(mes['filas']), 1)
        fila = mes['filas'][0]
        self.assertEqual(fila['cantidades'], [15])
        self.assertEqual((fila['total_mes'], fila['acumulado']), (15, 15))


class TestAvisoDeEntregasAntiguas(unittest.TestCase):
    """Pasados 30 dias sin entregas el panel avisa de que el consumo y el
    stock pueden estar desfasados. Ninguna prueba fijaba el umbral ni el
    signo de `dias_desde`."""

    def _leer(self, ultima):
        return em.leer_materiales_wb(_wb([
            _fila(ultima, 'Sagarde', None, 'TUBO', 'PVC', 'GRIS', None, 20, 5),
        ]), HOY)

    def test_cuarenta_dias_sin_entregas_avisa_con_los_dias_en_positivo(self):
        # Mata EM22 (signo) y EM23 (umbral).
        res = self._leer(datetime(2026, 12, 22))
        self.assertEqual(res['dias_desde'], 40)
        self.assertEqual(res['ultima_fecha'], '22/12/2026')
        self.assertIn('No hay entregas registradas desde 22/12/2026 (40 dias)',
                      res['aviso'])

    def test_treinta_dias_exactos_todavia_no_avisan(self):
        res = self._leer(datetime(2027, 1, 1))
        self.assertEqual(res['dias_desde'], 30)
        self.assertIsNone(res['aviso'])

    def test_treinta_y_un_dias_ya_avisan(self):
        res = self._leer(datetime(2026, 12, 31))
        self.assertEqual(res['dias_desde'], 31)
        self.assertIsNotNone(res['aviso'])


class TestCantidadYFechaDeCelda(unittest.TestCase):

    def test_una_casilla_booleana_no_es_una_cantidad(self):
        # Mata EM04. Un VERDADERO de Excel no es "1 unidad": la fila no se
        # cuenta y sale en el aviso, igual que una cantidad vacia.
        self.assertEqual(em._cantidad(True), (None, 'esta vacia'))
        self.assertEqual(em._cantidad(False), (None, 'esta vacia'))
        ent, avisos = em.leer_registro(_wb([
            _fila(datetime(2026, 10, 1), 'Sagarde', None, 'TUBO', 'PVC',
                  'GRIS', None, 20, True),
        ]), HOY)
        self.assertEqual(ent, [])
        self.assertEqual(len(avisos), 1)
        self.assertIn('la fila no se cuenta', avisos[0])

    def test_una_serie_de_excel_dentro_del_rango_es_una_fecha(self):
        # Mata EM01. 45000 es el 15/03/2023; fuera de 30000-80000 no se
        # interpreta como fecha (podria ser una cantidad escrita en la
        # columna equivocada) y no se inventa.
        self.assertEqual(em._fecha(45000), date(2023, 3, 15))
        self.assertIsNone(em._fecha(29999))
        self.assertIsNone(em._fecha(90000))
        self.assertIsNone(em._fecha(True))


if __name__ == '__main__':
    unittest.main()
