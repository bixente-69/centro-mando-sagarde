# -*- coding: utf-8 -*-
"""Pruebas de la guarda de cobertura de `motor_informes.py`.

Nacen de un fallo real (Obispo Orueta, 28/07/2026): la hoja "2A FASE" del
27/07/2026 cubria 40 celdas de dos viviendas nuevas de PB, y como todo el
calculo se hace sobre `historial[-1]`, el panel paso a publicar un 80.0%
calculado sobre esas 40 celdas en vez de sobre las 1288 de la revision
anterior. Se perdieron 107 ubicaciones del historico Y NO SALTO NINGUN AVISO.

La guarda no corrige el porcentaje -- eso lo hace la ficha de obra, que
acumula-- pero impide que vuelva a pasar en silencio en las obras que
todavia no tienen ficha.
"""
import os
import sys
import unittest

_SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SISTEMA_DIR)

import motor_informes as mi


def _rec(edificio='E1', planta='PB', unidad='A', tarea='Tubeado', estado='X'):
    return {'building': edificio, 'floor': planta, 'unit': unidad,
            'task': tarea, 'status': estado}


def _ubicaciones(edificio, planta, unidades):
    return [_rec(edificio, planta, u) for u in unidades]


class TestCoberturaEncogida(unittest.TestCase):

    def test_avisa_cuando_la_ultima_hoja_cubre_mucho_menos(self):
        """El caso Obispo Orueta: de 10 ubicaciones a 1."""
        antes = _ubicaciones('E1', 'PB', 'ABCDEFGHIJ')
        ahora = _ubicaciones('E1', 'PB', 'A')
        motivo = mi.cobertura_encogida(
            [('24/09/2025', antes), ('27/07/2026', ahora)])
        self.assertIsNotNone(motivo)
        self.assertIn('27/07/2026', motivo)
        self.assertIn('1', motivo)
        self.assertIn('10', motivo)

    def test_el_aviso_dice_cuantas_ubicaciones_se_quedan_sin_datos(self):
        antes = _ubicaciones('E1', 'PB', 'ABCDEFGHIJ')
        ahora = _ubicaciones('E1', 'PB', 'A')
        self.assertIn('9', mi.cobertura_encogida(
            [('24/09/2025', antes), ('27/07/2026', ahora)]))

    def test_no_avisa_si_la_cobertura_se_mantiene(self):
        regs = _ubicaciones('E1', 'PB', 'ABCDEFGHIJ')
        self.assertIsNone(mi.cobertura_encogida(
            [('01/01/2026', regs), ('02/01/2026', list(regs))]))

    def test_no_avisa_si_la_obra_crece(self):
        """Una obra que gana ubicaciones es normal, no es una alarma."""
        antes = _ubicaciones('E1', 'PB', 'ABCDE')
        ahora = _ubicaciones('E1', 'PB', 'ABCDEFGHIJ')
        self.assertIsNone(mi.cobertura_encogida(
            [('01/01/2026', antes), ('02/01/2026', ahora)]))

    def test_no_avisa_por_una_perdida_pequena(self):
        """Perder una vivienda de diez puede ser una hoja mal leida, no una
        revision parcial. La guarda busca el desplome, no el ruido."""
        antes = _ubicaciones('E1', 'PB', 'ABCDEFGHIJ')
        ahora = _ubicaciones('E1', 'PB', 'ABCDEFGHI')
        self.assertIsNone(mi.cobertura_encogida(
            [('01/01/2026', antes), ('02/01/2026', ahora)]))

    def test_una_sola_revision_no_tiene_con_que_comparar(self):
        self.assertIsNone(mi.cobertura_encogida(
            [('01/01/2026', _ubicaciones('E1', 'PB', 'ABC'))]))

    def test_historial_vacio_no_revienta(self):
        self.assertIsNone(mi.cobertura_encogida([]))

    def test_una_revision_anterior_vacia_no_revienta(self):
        self.assertIsNone(mi.cobertura_encogida(
            [('01/01/2026', []), ('02/01/2026', _ubicaciones('E1', 'PB', 'A'))]))

    def test_cuenta_ubicaciones_y_no_celdas(self):
        """Dos hojas con las mismas viviendas no encogen aunque una traiga
        menos tajos: lo que importa es que no desaparezcan ubicaciones."""
        antes = [_rec('E1', 'PB', u, t)
                 for u in 'ABCDE' for t in ('Tubeado', 'Cableado', 'Techos')]
        ahora = [_rec('E1', 'PB', u, 'Tubeado') for u in 'ABCDE']
        self.assertIsNone(mi.cobertura_encogida(
            [('01/01/2026', antes), ('02/01/2026', ahora)]))


if __name__ == '__main__':
    unittest.main()
