# -*- coding: utf-8 -*-
"""Pruebas que matan mutaciones supervivientes de `claves_correcciones.py`.

Origen: auditoria por mutacion del 04/11/2026
(`_SISTEMA/docs/auditorias_nube_2026-11-04/B_mutaciones.md`). De las 7
mutaciones, 2 son EQUIVALENTES (no hay prueba que las distinga):
`\\s+` -> `\\s` (el sustituto es '', asi que quitar la racha o quitar cada
blanco da el mismo texto) y `clave or ''` -> `clave` (`str(None)` da 'None',
que tampoco tiene cuatro tramos). La que si distingue una prueba es CC04.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import claves_correcciones as cc


class TestNormalizarUnidad(unittest.TestCase):

    def test_una_unidad_ausente_es_texto_vacio_no_la_palabra_None(self):
        # Mata CC04: sin esto una unidad None acabaria como la unidad 'None'.
        self.assertEqual(cc.normalizar_unidad(None), '')
        self.assertEqual(cc.normalizar_unidad(''), '')

    def test_quita_los_espacios_que_mete_el_extractor(self):
        self.assertEqual(cc.normalizar_unidad('PORT  AL 1'), 'PORTAL1')


class TestPartirClave(unittest.TestCase):

    def test_cuatro_tramos_con_la_unidad_normalizada(self):
        self.assertEqual(cc.partir_clave('p1__pb__tubeado__A 1'),
                         ('p1', 'pb', 'tubeado', 'A1'))

    def test_una_clave_mal_formada_no_se_parte(self):
        for clave in (None, '', 'p1__pb__tubeado', 'p1__pb__tubeado__A__x'):
            with self.subTest(clave=clave):
                self.assertIsNone(cc.partir_clave(clave))


if __name__ == '__main__':
    unittest.main()
