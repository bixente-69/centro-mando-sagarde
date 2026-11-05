# -*- coding: utf-8 -*-
"""Regla de Bixente (05/11/2026): la MARCA informa, no divide.

Un material se identifica por categoria + material + tipo (+ unidad). Si el
mismo cable 1,5 azul llega de dos marcas, el total es UNO y la marca dice
las dos. Solo otro tipo (p. ej. libre de halogenos) abre otro total.
Datos inventados.
"""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import entregas_materiales as em


def _e(fila, f, mat, tipo, marca, cant, sumi='Sagarde', alb=None, uni='200',
      cat='CABLE 1,5'):
    return {'fila': fila, 'fecha': f, 'suministrador': sumi, 'albaran': alb,
            'categoria': cat, 'material': mat, 'tipo': tipo, 'marca': marca,
            'uni': uni, 'cantidad': cant}


E = [
    _e(2, date(2026, 10, 29), 'AZUL', 'H07V-K', 'REVI', 400),
    _e(3, date(2026, 10, 30), 'AZUL', 'H07V-K', 'GENERAL CABLE', 200,
       sumi='Electrovizcaya', alb='A1'),
    _e(4, date(2026, 10, 30), 'AZUL', 'LIBRE DE HALOGENOS', 'REVI', 100,
       sumi='Electrovizcaya', alb='A1'),
    _e(5, date(2026, 11, 2), 'AZUL', 'H07V-K', 'revi', 100),  # otra grafia
    _e(6, date(2026, 11, 2), 'AZUL', 'H07V-K', 'PRYSMIAN', 50),  # en mano, otra marca
]


class TestMarcaNoDivide(unittest.TestCase):

    def setUp(self):
        self.g = em.agrupar(E)

    def test_mismo_tipo_de_dos_marcas_es_un_solo_total(self):
        filas = [f for f in self.g['acumulado']['filas']
                 if f['tipo'] == 'H07V-K']
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['total'], 400 + 200 + 100 + 50)

    def test_la_marca_de_ese_total_lista_las_dos_sin_repetir_grafias(self):
        f = next(f for f in self.g['acumulado']['filas']
                 if f['tipo'] == 'H07V-K')
        self.assertEqual(f['marca'], 'REVI, GENERAL CABLE, PRYSMIAN')
        # y su desglose por mes llega al total (la fila no se pierde al buscarla)
        self.assertEqual(f['por_mes'], [600, 150])

    def test_otro_tipo_si_abre_otro_total(self):
        tipos = sorted(f['tipo'] for f in self.g['acumulado']['filas'])
        self.assertEqual(tipos, ['H07V-K', 'LIBRE DE HALOGENOS'])

    def test_el_total_del_mes_tampoco_se_divide_y_su_marca_es_la_del_mes(self):
        octubre = next(m for m in self.g['meses'] if m['mes'] == 10)
        f = next(f for f in octubre['filas'] if f['tipo'] == 'H07V-K')
        self.assertEqual(f['total_mes'], 600)
        self.assertEqual(f['marca'], 'REVI, GENERAL CABLE')
        noviembre = next(m for m in self.g['meses'] if m['mes'] == 11)
        fn = noviembre['filas'][0]
        self.assertEqual(fn['marca'], 'REVI, PRYSMIAN')   # solo las de ese mes
        self.assertEqual(fn['mes_ant'], 600)
        self.assertEqual(fn['acumulado'], 750)

    def test_las_lineas_conservan_su_marca_exacta(self):
        marcas = [l['marca'] for l in self.g['lineas']]
        self.assertCountEqual(
            marcas, ['REVI', 'GENERAL CABLE', 'REVI', 'revi', 'PRYSMIAN'])

    def test_sin_marca_el_campo_queda_vacio_no_inventado(self):
        g = em.agrupar([_e(2, date(2026, 10, 1), 'AZUL', 'H07V-K', None, 5)])
        self.assertIsNone(g['acumulado']['filas'][0]['marca'])

    def test_por_suministrador_tampoco_divide_por_marca(self):
        por = em.totales_por_suministrador(self.g['lineas'])
        sagarde = next(p for p in por if p['suministrador'] == 'Sagarde')
        mats = [m for m in sagarde['materiales'] if m['tipo'] == 'H07V-K']
        self.assertEqual(len(mats), 1)
        self.assertEqual(mats[0]['total'], 550)
        self.assertEqual(mats[0]['marca'], 'REVI, PRYSMIAN')

    def test_el_total_acumulado_cuadra_con_la_suma_de_lineas(self):
        suma_lineas = sum(l['cantidad'] for l in self.g['lineas'])
        suma_acum = sum(f['total'] for f in self.g['acumulado']['filas'])
        self.assertEqual(suma_lineas, suma_acum)


class TestMarcaEnSuPropiaColumna(unittest.TestCase):

    def _res(self):
        return {'detalle': em.agrupar(E)}

    def test_cabeceras_de_las_tablas_llevan_columna_marca(self):
        res = self._res()
        for html in (em.render_total(res), em.render_por_mes(res),
                     em.render_entregas(res), em.render_por_albaran(res),
                     em.render_por_suministrador(res)):
            self.assertIn('Marca', html)

    def test_la_marca_ya_no_va_pegada_al_tipo(self):
        res = self._res()
        for html in (em.render_total(res), em.render_por_mes(res),
                     em.render_entregas(res), em.render_por_albaran(res),
                     em.render_por_suministrador(res)):
            self.assertNotIn('H07V-K · ', html)

    def test_el_tipo_de_aislante_se_ve_en_su_columna(self):
        self.assertIn('LIBRE DE HALOGENOS', em.render_total(self._res()))


if __name__ == '__main__':
    unittest.main()
