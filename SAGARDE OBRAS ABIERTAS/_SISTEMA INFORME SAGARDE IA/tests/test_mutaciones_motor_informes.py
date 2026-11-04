# -*- coding: utf-8 -*-
"""Pruebas que matan mutaciones supervivientes de `motor_informes.py`.

Origen: auditoria por mutacion del 04/11/2026
(`_SISTEMA/docs/auditorias_nube_2026-11-04/B_mutaciones.md`). Se rompio el
motor a proposito y la suite siguio en verde en estos casos: nadie fijaba el
DESGLOSE de `kpis_snapshot` (`CLAUDE.md` §3: "el porcentaje redondeado es un
criterio ciego"), ni los umbrales de `detectar_bloqueos`, ni el orden de los
rankings. Cada prueba dice que mutacion mata (MIxx, ver el informe).

Aqui no se prueba nada del PDF ni del panel: son funciones puras sobre
registros `{'task','floor','building','unit','status'}`.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import motor_informes as mi


def _r(tarea='T', planta='1', edificio='E1', unidad='A', estado='X'):
    return {'task': tarea, 'floor': planta, 'building': edificio,
            'unit': unidad, 'status': estado}


def _unidad(edificio, planta, unidad, estados):
    """Una vivienda con un registro por estado (tarea t0, t1, ...)."""
    return [_r(f't{i}', planta, edificio, unidad, e)
            for i, e in enumerate(estados)]


class TestKpisSnapshotDesglose(unittest.TestCase):
    """El desglose x/m/slash/vacio es lo que hay que comparar entre
    consumidores; un porcentaje redondeado no se entera de nada."""

    def test_cada_estado_se_cuenta_en_su_propia_casilla(self):
        # Recuentos distintos (2, 3, 1, 4) para que ninguna casilla pueda
        # confundirse con otra sin que cambie el resultado. Mata MI09, MI10.
        snap = ([_r(estado='X')] * 2 + [_r(estado='M')] * 3
                + [_r(estado='/')] * 1 + [_r(estado='')] * 4)
        k = mi.kpis_snapshot(snap)
        self.assertEqual(
            (k['total'], k['x'], k['m'], k['slash'], k['vacio']),
            (10, 2, 3, 1, 4))

    def test_los_pesos_de_cada_estado(self):
        # X=100, M=60, /=25, vacio=0 en el ponderado; solo X cuenta en el
        # estricto. Mata MI01-MI03 y MI07 sin depender del panel de garaje.
        esperado = {'X': (100.0, 100.0), 'M': (0.0, 60.0),
                    '/': (0.0, 25.0), '': (0.0, 0.0)}
        for estado, (estricto, ponderado) in esperado.items():
            with self.subTest(estado=estado):
                k = mi.kpis_snapshot([_r(estado=estado)])
                self.assertEqual(k['pct_estricto'], estricto)
                self.assertEqual(k['pct_ponderado'], ponderado)

    def test_un_snapshot_vacio_no_inventa_avance(self):
        # Mata MI04: sin celdas el avance es 0, no 100. Y el total es 0, no
        # un None que otro consumidor tendria que adivinar.
        k = mi.kpis_snapshot([])
        self.assertEqual(k['total'], 0)
        self.assertEqual(k['pct_estricto'], 0.0)
        self.assertEqual(k['pct_ponderado'], 0.0)
        self.assertEqual(mi._pct_ponderado([]), 0.0)
        self.assertEqual(mi._pct_estricto([]), 0.0)

    def test_un_estado_desconocido_no_suma_avance(self):
        # Mata MI06: lo que el motor no entiende vale 0 (y cae en `vacio`),
        # nunca cuenta como hecho.
        k = mi.kpis_snapshot([_r(estado='Z'), _r(estado='X')])
        self.assertEqual(k['pct_ponderado'], 50.0)
        self.assertEqual(k['vacio'], 1)

    def test_redondeo_a_un_decimal(self):
        # Mata MI11: 1 terminada de 3 = 33.3 (no 33.0); X+M+vacio = 53.3.
        k = mi.kpis_snapshot([_r(estado='X'), _r(estado='M'), _r(estado='')])
        self.assertEqual(k['pct_estricto'], 33.3)
        self.assertEqual(k['pct_ponderado'], 53.3)


class TestCoberturaEncogidaEnElUmbral(unittest.TestCase):

    def _hist(self, antes, ahora):
        previos = [_r(unidad=f'U{i}') for i in range(antes)]
        ultimos = [_r(unidad=f'U{i}') for i in range(ahora)]
        return [('01/01/2026', previos), ('08/01/2026', ultimos)]

    def test_justo_en_el_umbral_no_avisa(self):
        # Mata MI14. 2 de 4 ubicaciones es EXACTAMENTE el 50 %: la regla dice
        # "bastantes menos", asi que el borde no avisa.
        self.assertIsNone(mi.cobertura_encogida(self._hist(4, 2)))

    def test_por_debajo_del_umbral_si_avisa(self):
        self.assertIsNotNone(mi.cobertura_encogida(self._hist(4, 1)))


class TestDetectarBloqueos(unittest.TestCase):
    """Los umbrales (60/15 por planta, 15/30 por vivienda) son lo que decide
    que algo se publique como 'bloqueado'. Ninguna prueba los fijaba."""

    def test_planta_rezagada_se_detecta_con_sus_cifras(self):
        snap = (_unidad('E1', '1', 'A', [''] * 4)
                + _unidad('E1', '2', 'A', ['X'] * 4))
        b = mi.detectar_bloqueos(snap)
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]['tipo'], 'Planta rezagada')
        self.assertEqual((b[0]['edificio'], b[0]['planta']), ('E1', '1'))
        self.assertEqual((b[0]['avance'], b[0]['referencia']), (0.0, 50.0))

    def test_planta_justo_en_el_60_no_es_rezagada(self):
        # Mata MI16 (<=) y MI19 (and->or). Planta al 60.0 exacto frente a una
        # media de edificio del 96: la diferencia (36) supera 15, pero el 60
        # ya no es "por debajo de 60".
        snap = (_unidad('E1', '1', 'A', ['M'])
                + _unidad('E1', '2', 'A', ['X'] * 9))
        self.assertEqual(mi.detectar_bloqueos(snap), [])

    def test_planta_con_diferencia_justo_de_15_no_es_rezagada(self):
        # Mata MI17 (>=), MI18 (> 5) y MI19. Planta al 0 % y media del
        # edificio 15.0 exacto (3 X de 20): diferencia == 15, no > 15.
        snap = (_unidad('E1', '1', 'A', [''] * 17)
                + _unidad('E1', '2', 'A', ['X'] * 3))
        self.assertEqual(mi.detectar_bloqueos(snap), [])

    def test_vivienda_sin_iniciar_se_detecta_con_sus_cifras(self):
        # Mata MI23 (<= 2): con EXACTAMENTE dos viviendas en la planta ya se
        # compara la una con la otra.
        snap = (_unidad('E1', '1', 'A', [''] * 2)
                + _unidad('E1', '1', 'B', ['X'] * 2))
        b = mi.detectar_bloqueos(snap)
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]['tipo'], 'Vivienda/mano sin iniciar')
        self.assertEqual(b[0]['unidad'], 'A')
        self.assertEqual((b[0]['avance'], b[0]['referencia']), (0.0, 50.0))

    def test_vivienda_justo_en_el_15_no_esta_sin_iniciar(self):
        # Mata MI20 (<=). Vivienda A al 15.0 exacto (3 X de 20) junto a una B
        # al 100: la diferencia con la media (42.5) supera 30, pero 15 no es
        # "menos de 15".
        snap = (_unidad('E1', '1', 'A', ['X'] * 3 + [''] * 17)
                + _unidad('E1', '1', 'B', ['X'] * 20))
        self.assertEqual(mi.detectar_bloqueos(snap), [])

    def test_vivienda_con_diferencia_justo_de_30_no_esta_sin_iniciar(self):
        # Mata MI21 (> 20) y MI22 (and->or). A al 0, B al 60: media 30.0 y
        # diferencia 30.0 exacta, no > 30.
        snap = (_unidad('E1', '1', 'A', [''])
                + _unidad('E1', '1', 'B', ['M']))
        self.assertEqual(mi.detectar_bloqueos(snap), [])

    def test_vivienda_con_avance_normal_no_se_marca_aunque_la_otra_vaya_muy_por_delante(self):
        # Mata MI22: A al 25 % no es "menos de 15" aunque la media la deje
        # 37.5 puntos por debajo. Con `or` se publicaria un bloqueo falso.
        snap = (_unidad('E1', '1', 'A', ['/'])
                + _unidad('E1', '1', 'B', ['X']))
        self.assertEqual(mi.detectar_bloqueos(snap), [])

    def test_los_bloqueos_salen_del_menos_avanzado_al_mas_avanzado(self):
        # Mata MI24. E1 se inserta antes (avance 25) que E2 (avance 0): sin
        # ordenar, o ordenando al reves, saldrian [25, 0].
        snap = (_unidad('E1', '1', 'A', ['/'] * 4)
                + _unidad('E1', '2', 'A', ['X'] * 4)
                + _unidad('E2', '1', 'A', [''] * 4)
                + _unidad('E2', '2', 'A', ['X'] * 4))
        b = mi.detectar_bloqueos(snap)
        self.assertEqual([x['avance'] for x in b], [0.0, 25.0])
        self.assertEqual([x['edificio'] for x in b], ['E2', 'E1'])


class TestSinCambiosEntreUltimas(unittest.TestCase):

    def test_una_sola_revision_no_es_comparable(self):
        self.assertFalse(mi.sin_cambios_entre_ultimas(
            [('01/01/2026', [_r()])]))

    def test_dos_revisiones_identicas_no_tienen_cambios(self):
        # Mata MI25 (<= 2) y MI26 (== -> !=).
        hist = [('01/01/2026', [_r(estado='X'), _r(tarea='U', estado='M')]),
                ('08/01/2026', [_r(estado='X'), _r(tarea='U', estado='M')])]
        self.assertTrue(mi.sin_cambios_entre_ultimas(hist))

    def test_un_estado_distinto_es_un_cambio(self):
        hist = [('01/01/2026', [_r(estado='M')]),
                ('08/01/2026', [_r(estado='X')])]
        self.assertFalse(mi.sin_cambios_entre_ultimas(hist))

    def test_una_celda_nueva_es_un_cambio(self):
        hist = [('01/01/2026', [_r()]),
                ('08/01/2026', [_r(), _r(tarea='U')])]
        self.assertFalse(mi.sin_cambios_entre_ultimas(hist))


class TestRankingsYSeries(unittest.TestCase):

    def test_ranking_de_tareas_va_de_menos_a_mas_avanzada(self):
        # Mata MI29. 'A' (100 %) se inserta antes que 'B' (0 %).
        snap = [_r(tarea='A', estado='X'), _r(tarea='A', unidad='B', estado='X'),
                _r(tarea='B', estado='')]
        self.assertEqual(mi.ranking_tareas(snap),
                         [('B', 0.0, 1), ('A', 100.0, 2)])

    def test_ranking_con_memoria_anade_solo_lo_terminado_y_ausente(self):
        # Mata MI27 y MI28. 'Cerrado' desapareció de la hoja porque se dio por
        # terminado: vuelve al 100 % con su recuento. 'Activa' ya esta en la
        # hoja y no se duplica. 'Abierto' no esta terminado y no se anade.
        snap = [_r(tarea='Activa', estado='X')]
        memoria = {
            'Cerrado': {'terminado': True, 'n_registros_ultima_activa': 7},
            'Activa': {'terminado': True, 'n_registros_ultima_activa': 3},
            'Abierto': {'terminado': False, 'n_registros_ultima_activa': 5},
        }
        filas = mi.ranking_tareas_con_memoria(snap, memoria)
        self.assertEqual(sorted(filas),
                         [('Activa', 100.0, 1), ('Cerrado', 100.0, 7)])

    def test_serie_de_tiempo_lleva_total_y_porcentajes_de_cada_revision(self):
        # Mata MI30.
        hist = [('01/01/2026', [_r(estado=''), _r(tarea='U', estado='X'),
                                _r(tarea='V', estado='M')]),
                ('08/01/2026', [_r(estado='X')] * 4)]
        self.assertEqual(mi.serie_tiempo(hist), [
            {'fecha': '01/01/2026', 'pct_estricto': 33.3,
             'pct_ponderado': 53.3, 'total': 3},
            {'fecha': '08/01/2026', 'pct_estricto': 100.0,
             'pct_ponderado': 100.0, 'total': 4},
        ])


if __name__ == '__main__':
    unittest.main()
