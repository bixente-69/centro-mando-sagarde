# -*- coding: utf-8 -*-
"""Pruebas de la siembra desde lo MEDIDO.

El sembrador nacio leyendo prioridades_trabajos.json, que es una fuente
DERIVADA. Mientras la ultima revision cubria la obra entera daba igual, pero
con una revision parcial el priorizador arrastra 'Terminado segun la ultima
confirmacion valida' y declara terminadas celdas que nadie ha medido: en
Obispo Orueta, 1444 de 2404. Sembrar de ahi seria inventar datos.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sembrar_ficha_obra as sfo


class TestIdDeTajo(unittest.TestCase):

    def test_un_tajo_del_catalogo_conserva_su_id(self):
        resolver = sfo.resolver_tajo({})
        self.assertEqual(resolver('Tabicado')[0], 'tabicado')
        self.assertFalse(resolver('Tabicado')[1], 'no deberia ser propio')

    def test_un_tajo_que_no_esta_en_el_catalogo_es_propio_de_la_obra(self):
        """Obispo Orueta usa vocabulario suyo: Ventilacion, Techos WC..."""
        resolver = sfo.resolver_tajo({})
        tid, propio = resolver('Cableado Extractor')
        self.assertTrue(propio)
        self.assertEqual(tid, 'cableado_extractor')

    def test_dos_grafias_del_mismo_tajo_propio_caen_en_el_mismo_id(self):
        """'Lucido Paredes' y 'Lucido paredes' son el mismo trabajo."""
        resolver = sfo.resolver_tajo({})
        self.assertEqual(resolver('Lucido Paredes')[0],
                         resolver('Lucido paredes')[0])

    def test_los_acentos_y_signos_no_rompen_el_id(self):
        resolver = sfo.resolver_tajo({})
        tid, _ = resolver('Placas + Tps. Cuadro')
        self.assertRegex(tid, r'^[a-z0-9_]+$')


class TestEstadosDesdeHistorial(unittest.TestCase):

    def _hist(self):
        return [
            ('01/01/2025', [
                {'floor': '1', 'unit': 'A', 'task': 'Tabicado', 'status': 'M'},
                {'floor': '1', 'unit': 'B', 'task': 'Tabicado', 'status': 'X'},
            ]),
            ('02/02/2025', [
                {'floor': '1', 'unit': 'A', 'task': 'Tabicado', 'status': 'X'},
                {'floor': '1', 'unit': 'B', 'task': 'Tabicado', 'status': ''},
            ]),
        ]

    def test_manda_la_ultima_revision_que_trae_marca(self):
        est = sfo.estados_desde_historial(self._hist(), sfo.resolver_tajo({}))
        self.assertEqual(est[('1', 'A', 'tabicado')][0], 'X')

    def test_una_celda_sin_marca_no_pisa_la_marca_anterior(self):
        """Una casilla en blanco es 'no se leyo', no 'se comprobo y no esta'.

        Es la confusion P/? que ha causado casi todo lo que ha fallado aqui.
        """
        est = sfo.estados_desde_historial(self._hist(), sfo.resolver_tajo({}))
        self.assertEqual(est[('1', 'B', 'tabicado')][0], 'X')

    def test_guarda_la_fecha_de_la_revision_que_lo_midio(self):
        est = sfo.estados_desde_historial(self._hist(), sfo.resolver_tajo({}))
        self.assertEqual(est[('1', 'A', 'tabicado')][1], '02/02/2025')

    def test_una_celda_que_nadie_midio_nunca_no_aparece(self):
        """No aparecer es lo correcto: el sembrador la pondra como '?'."""
        est = sfo.estados_desde_historial(self._hist(), sfo.resolver_tajo({}))
        self.assertNotIn(('1', 'C', 'tabicado'), est)


class TestNoAplica(unittest.TestCase):
    """La hoja declara que tajos tiene cada ubicacion imprimiendo su fila.

    En Obispo Orueta un 'Montantes 2' lleva UN tajo y unas 'Zonas Comunes'
    llevan cinco, frente a los 38 de la obra. Si la ficha monta la matriz
    completa, la hoja que genera la app imprimiria 38 filas por montante:
    papel que nadie va a rellenar y celdas que no significan nada.
    """

    def _hist(self):
        ed = 'Obispo Orueta 2'
        return [('01/01/2025', [
            {'building': ed, 'floor': '1', 'unit': 'Montantes 2',
             'task': 'Tabicado', 'status': 'X'},
            {'building': ed, 'floor': '1', 'unit': 'A',
             'task': 'Tabicado', 'status': 'X'},
            {'building': ed, 'floor': '1', 'unit': 'A',
             'task': 'Cableado', 'status': ''},
        ])]

    def test_un_tajo_que_la_hoja_nunca_imprime_ahi_es_N(self):
        estados = {
            'p1__1__tabicado__Montantes 2': {'v': '?', 'f': None, 'r': None},
            'p1__1__cableado__Montantes 2': {'v': '?', 'f': None, 'r': None},
        }
        n = sfo.marcar_no_aplica(
            estados, self._hist(), sfo.resolver_tajo(),
            {('Obispo Orueta 2', '1'): ('p1', '1')}, lambda u: u)
        self.assertEqual(estados['p1__1__cableado__Montantes 2']['v'], 'N')
        self.assertEqual(estados['p1__1__tabicado__Montantes 2']['v'], '?')
        self.assertEqual(n, 1)

    def test_una_fila_impresa_en_blanco_NO_es_N(self):
        """Impresa y sin marca significa 'aplica y no se ha leido'."""
        estados = {'p1__1__cableado__A': {'v': '?', 'f': None, 'r': None}}
        sfo.marcar_no_aplica(
            estados, self._hist(), sfo.resolver_tajo(),
            {('Obispo Orueta 2', '1'): ('p1', '1')}, lambda u: u)
        self.assertEqual(estados['p1__1__cableado__A']['v'], '?')

    def test_no_pisa_una_medida(self):
        estados = {'p1__1__cableado__Montantes 2':
                   {'v': 'X', 'f': '01/01/2025', 'r': 'rev_01012025'}}
        sfo.marcar_no_aplica(
            estados, self._hist(), sfo.resolver_tajo(),
            {('Obispo Orueta 2', '1'): ('p1', '1')}, lambda u: u)
        self.assertEqual(estados['p1__1__cableado__Montantes 2']['v'], 'X')


class TestTerminadoCompleto(unittest.TestCase):
    """Obispo Orueta, textual de Bixente el 04/08/2026:

    'TODO TERMINADO A FALTA DE LA SEGUNDA FASE. A DUDA QUE TENGAS ESTA
    TERMINADO. SE HAYA MARCADO O NO. DESDE LA ULTIMA QUE SE HIZO A TERMINADO
    NO HA HABIDO INTERMEDIAS.'

    O sea: la obra acabo despues de la ultima revision y no hubo hoja que lo
    recogiera. Las marcas de septiembre de 2025 estan viejas y mandan sus
    palabras, que es la norma de obra: lo que dice la ultima confirmacion es
    lo que vale.
    """

    def _estados(self):
        return {
            'p1__1__tabicado__Apartamento 1': {'v': 'M', 'f': '01/09/2025', 'r': 'r1'},
            'p1__1__cableado__Apartamento 1': {'v': '?', 'f': None, 'r': None},
            'p1__1__techos__Apartamento 1': {'v': '/', 'f': '01/09/2025', 'r': 'r1'},
            'p1__1__pintura__Apartamento 1': {'v': 'N', 'f': None, 'r': None},
            'p1__pb__tabicado__A': {'v': 'X', 'f': '27/07/2026', 'r': 'r2'},
            'p1__pb__cableado__A': {'v': '?', 'f': None, 'r': None},
        }

    def _aplicar(self, estados):
        return sfo.aplicar_terminado_completo(
            estados,
            {'excepto': {'Obispo Orueta 2': {'PB': ['A', 'B']}}},
            {('Obispo Orueta 2', 'PB'): ('p1', 'pb')},
            '04/08/2026')

    def test_lo_dudoso_y_lo_a_medias_pasa_a_X(self):
        est = self._estados()
        self._aplicar(est)
        self.assertEqual(est['p1__1__tabicado__Apartamento 1']['v'], 'X')
        self.assertEqual(est['p1__1__cableado__Apartamento 1']['v'], 'X')
        self.assertEqual(est['p1__1__techos__Apartamento 1']['v'], 'X')

    def test_lo_que_no_aplica_sigue_sin_aplicar(self):
        """Terminar la obra no inventa trabajo donde no lo hay."""
        est = self._estados()
        self._aplicar(est)
        self.assertEqual(est['p1__1__pintura__Apartamento 1']['v'], 'N')

    def test_la_segunda_fase_queda_intacta(self):
        est = self._estados()
        self._aplicar(est)
        self.assertEqual(est['p1__pb__cableado__A']['v'], '?')
        self.assertEqual(est['p1__pb__tabicado__A']['v'], 'X')
        self.assertEqual(est['p1__pb__tabicado__A']['f'], '27/07/2026')

    def test_deja_traza_de_que_es_una_confirmacion(self):
        est = self._estados()
        self._aplicar(est)
        celda = est['p1__1__cableado__Apartamento 1']
        self.assertEqual(celda['origen'], 'confirmado_usuario')
        self.assertEqual(celda['f'], '04/08/2026')


class TestTerminadasAl100(unittest.TestCase):

    def test_marca_X_solo_las_ubicaciones_declaradas(self):
        estados = {
            'p1__-1__tabicado__Apartamento GYM': {'v': '?', 'f': None, 'r': None},
            'p1__1__tabicado__Apartamento 1': {'v': '?', 'f': None, 'r': None},
        }
        n = sfo.aplicar_terminadas(
            estados,
            {'Obispo Orueta 2': {'-1': ['Apartamento GYM']}},
            {('Obispo Orueta 2', '-1'): ('p1', '-1')},
            '04/08/2026')
        self.assertEqual(n, 1)
        self.assertEqual(estados['p1__-1__tabicado__Apartamento GYM']['v'], 'X')
        self.assertEqual(estados['p1__1__tabicado__Apartamento 1']['v'], '?')

    def test_no_pisa_una_medida_real(self):
        """Lo declarado rellena huecos; no borra lo que se fue a ver."""
        estados = {'p1__-1__tabicado__Apartamento GYM':
                   {'v': 'M', 'f': '01/01/2025', 'r': 'rev_01012025'}}
        n = sfo.aplicar_terminadas(
            estados,
            {'Obispo Orueta 2': {'-1': ['Apartamento GYM']}},
            {('Obispo Orueta 2', '-1'): ('p1', '-1')},
            '04/08/2026')
        self.assertEqual(n, 0)
        self.assertEqual(estados['p1__-1__tabicado__Apartamento GYM']['v'], 'M')

    def test_deja_traza_de_que_es_una_confirmacion_no_una_medida(self):
        estados = {'p1__-1__tabicado__Apartamento GYM':
                   {'v': '?', 'f': None, 'r': None}}
        sfo.aplicar_terminadas(
            estados,
            {'Obispo Orueta 2': {'-1': ['Apartamento GYM']}},
            {('Obispo Orueta 2', '-1'): ('p1', '-1')},
            '04/08/2026')
        celda = estados['p1__-1__tabicado__Apartamento GYM']
        self.assertEqual(celda['origen'], 'confirmado_usuario')
        self.assertEqual(celda['f'], '04/08/2026')


if __name__ == '__main__':
    unittest.main()
