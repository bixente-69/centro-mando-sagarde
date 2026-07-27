# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ficha_obra
import fixtures


class TestApartados(unittest.TestCase):

    def test_crea_los_apartados_que_faltan(self):
        ficha = {'id': 'pruebas'}
        creados = ficha_obra.asegurar_apartados(ficha)
        for nombre in ficha_obra.APARTADOS:
            self.assertIn(nombre, ficha)
        self.assertIn('materiales', creados)

    def test_no_pisa_los_apartados_que_ya_existen(self):
        ficha = fixtures.ficha_minima()
        ficha['materiales'] = {'algo': 1}
        creados = ficha_obra.asegurar_apartados(ficha)
        self.assertEqual(creados, [])
        self.assertEqual(ficha['materiales'], {'algo': 1})


class TestEstados(unittest.TestCase):

    def test_una_celda_medida_se_guarda_con_su_fecha(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='X')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        celda = ficha['estados']['p1__pb__tubeado__A']
        self.assertEqual(celda['v'], 'X')
        self.assertEqual(celda['f'], '27/07/2026')
        self.assertEqual(celda['r'], 'rev_27072026')

    def test_pendiente_se_guarda_como_P_no_como_ausencia(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='Pendiente')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'P')

    def test_las_celdas_sin_dato_nacen_como_desconocido(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        # 1 portal x 2 plantas x 2 viviendas x 2 tajos = 8 celdas
        self.assertEqual(len(ficha['estados']), 8)
        self.assertEqual(ficha['estados']['p1__1__cableado__B']['v'], '?')

    def test_la_ultima_revision_manda_aunque_baje_de_X(self):
        """Norma de obra: si el revisor escribe M sobre algo que figuraba
        terminado, es que ha ido y ha visto que faltaba algo."""
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='X')]))
        ficha, cambios = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='M')],
                                        revision='30/07/2026'))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')
        self.assertIn(('p1__pb__tubeado__A', 'X', 'M'), cambios['estados_cambiados'])

    def test_no_toca_las_celdas_que_la_revision_no_menciona(self):
        """Si la hoja no cubre una celda, su dato anterior se conserva.
        Una revision parcial no puede borrar lo que no ha mirado."""
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(ficha, fixtures.prioridades([
            fixtures.item(unidad='A', estado='X'),
            fixtures.item(unidad='B', estado='X'),
        ]))
        ficha, _ = ficha_obra.actualizar(ficha, fixtures.prioridades(
            [fixtures.item(unidad='A', estado='M')], revision='30/07/2026'))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__B']['v'], 'X')


if __name__ == '__main__':
    unittest.main()
