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
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        # Verificar que se guardó como P
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'P')
        # Verificar que no aparece en estados no reconocidos (porque es reconocido)
        self.assertNotIn('pendiente', cambios['estados_no_reconocidos'])

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

    def test_variantes_de_mayusculas_de_pendiente_se_reconocen(self):
        """'pendiente', 'PENDIENTE', 'Pendiente' deben convertirse todas a 'P'."""
        for estado_variante in ('pendiente', 'PENDIENTE', 'Pendiente', 'PeNdIeNtE'):
            ficha = fixtures.ficha_minima()
            prio = fixtures.prioridades([fixtures.item(estado=estado_variante)])
            ficha, cambios = ficha_obra.actualizar(ficha, prio)
            self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'P',
                           msg=f"Variante '{estado_variante}' no se convirtió a P")
            self.assertEqual(cambios['estados_no_reconocidos'], [],
                           msg=f"Variante '{estado_variante}' apareció como no reconocida")

    def test_estado_desconocido_se_guarda_como_desconocido(self):
        """Un estado que no se reconoce debe guardarse como '?' (desconocido),
        no como 'P', y debe aparecer en estados_no_reconocidos."""
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='ZZZ')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        # Debe guardarse como ?
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], '?')
        # Debe aparecer en estados_no_reconocidos
        self.assertIn('zzz', cambios['estados_no_reconocidos'])
        # Debe aparecer en el resumen de cambios
        resumen = ficha_obra.resumen_cambios(cambios)
        self.assertTrue(any('ESTADOS NO RECONOCIDOS' in linea for linea in resumen),
                       msg="Estado no reconocido no aparece en el resumen de cambios")

    def test_correcciones_manuales_mayuscula_X_se_normalizan(self):
        """Una corrección manual con 'X' en mayúscula debe normalizarse y aplicarse.
        Las correcciones son marcas que el jefe de obra escribe a boli sobre
        la hoja de campo — el dato más directo que existe."""
        ficha = fixtures.ficha_minima()
        # Estado base: 'M' en p1__pb__tubeado__A
        prio = fixtures.prioridades([fixtures.item(unidad='A', estado='M')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        # Segunda revisión: procesa un item diferente (B), y aplica corrección en A
        prio2 = fixtures.prioridades([fixtures.item(unidad='B', estado='X')],
                                    revision='28/07/2026')
        correcciones = {'p1__pb__tubeado__A': 'X'}  # mayúscula
        ficha, cambios = ficha_obra.actualizar(ficha, prio2, correcciones=correcciones)
        # Debe cambiar A a 'X' (normalizado)
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')
        # Debe registrarse en correcciones_reclamadas
        self.assertIn(('p1__pb__tubeado__A', 'M', 'X'), cambios['correcciones_reclamadas'])
        # No debe aparecer en estados_no_reconocidos (porque se reconoció)
        self.assertNotIn('x', cambios['estados_no_reconocidos'])

    def test_correcciones_manuales_mayuscula_M_y_Pendiente(self):
        """Correcciones con variantes de 'M', 'Pendiente' en mayúscula también se normalizan."""
        ficha = fixtures.ficha_minima()
        # Estado base: '?' en ambas celdas (sin datos)
        prio = fixtures.prioridades([])  # Sin items, solo estructura
        # Forzar creación de estados con estado_base
        prio_base = fixtures.prioridades([fixtures.item(unidad='A', estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio_base)

        # Correcciones: una con 'M' mayúscula, otra con 'Pendiente' mayúscula
        prio_rev2 = fixtures.prioridades([fixtures.item(unidad='B', estado='X')],
                                        revision='29/07/2026')
        correcciones = {
            'p1__pb__tubeado__A': 'M',          # mayúscula
            'p1__1__cableado__B': 'Pendiente',  # mayúscula
        }
        ficha, cambios = ficha_obra.actualizar(ficha, prio_rev2, correcciones=correcciones)

        # Ambas correcciones deben aplicarse
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')
        self.assertEqual(ficha['estados']['p1__1__cableado__B']['v'], 'P')

        # Ambas deben estar en correcciones_reclamadas
        self.assertEqual(len(cambios['correcciones_reclamadas']), 2)

        # Ninguna debe aparecer en estados_no_reconocidos
        self.assertEqual(cambios['estados_no_reconocidos'], [])

    def test_correcciones_manuales_no_reconocidas_son_visibles(self):
        """Una corrección con estado no reconocido no se aplica, pero aparece en estados_no_reconocidos."""
        ficha = fixtures.ficha_minima()
        # Estado base
        prio = fixtures.prioridades([fixtures.item(unidad='A', estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)

        # Corrección con estado inventado
        prio_rev2 = fixtures.prioridades([fixtures.item(unidad='B', estado='X')],
                                        revision='29/07/2026')
        correcciones = {'p1__pb__tubeado__A': 'INVENTADO'}
        ficha, cambios = ficha_obra.actualizar(ficha, prio_rev2, correcciones=correcciones)

        # La celda debe mantener su estado anterior (X)
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')

        # NO debe estar en correcciones_reclamadas
        self.assertEqual(len(cambios['correcciones_reclamadas']), 0)

        # DEBE aparecer en estados_no_reconocidos
        self.assertIn('inventado', cambios['estados_no_reconocidos'])

        # DEBE aparecer en el resumen
        resumen = ficha_obra.resumen_cambios(cambios)
        self.assertTrue(any('ESTADOS NO RECONOCIDOS' in linea for linea in resumen))


if __name__ == '__main__':
    unittest.main()
