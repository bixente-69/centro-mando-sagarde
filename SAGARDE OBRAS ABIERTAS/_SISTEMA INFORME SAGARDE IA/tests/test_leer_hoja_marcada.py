# -*- coding: utf-8 -*-
"""El lector de hojas marcadas no puede cambiar nada en silencio.

Todo lo que se prueba aqui protege la misma frontera: el codigo pone la clave
de la celda, la vista pone la letra, y ninguna de las dos puede colarse en la
base sin que se vea.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fixtures
import leer_hoja_marcada as lector


def _candidata(clave, puntos=12, antes='?'):
    return {'clave': clave, 'puntos': puntos, 'antes': antes,
            'dudosa': puntos < lector.PUNTOS_DUDOSA, 'pagina': 1,
            'bloque': 'Bloque 1', 'portal': 'P1', 'planta': 'PB',
            'vivienda': clave.split('__')[-1], 'tajo': 'tubeado',
            'tajo_nombre': 'Tubeado', 'recorte': None, 'valor': None}


def _ficha(estados=None):
    ficha = fixtures.ficha_minima()
    ficha['estados'] = {
        clave: {'v': valor, 'f': '27/07/2026', 'r': 'rev_27072026'}
        for clave, valor in (estados or {}).items()
    }
    return ficha


class TestNadaSeDescartaSolo(unittest.TestCase):

    def test_una_candidata_sin_clasificar_para_la_lectura(self):
        """Si se dejara pasar, esa celda quedaria sin medir y nadie lo
        sabria: la hoja tenia tinta y la base no se entero."""
        ficha = _ficha({'p1__pb__tubeado__A': '?', 'p1__pb__tubeado__B': '?'})
        cand = [_candidata('p1__pb__tubeado__A'),
                _candidata('p1__pb__tubeado__B')]
        with self.assertRaises(lector.LecturaImposible) as caso:
            lector.aplicar(ficha, cand, {'p1__pb__tubeado__A': 'X'},
                           '05/08/2026', 'rev_05082026')
        self.assertIn('sin clasificar', str(caso.exception))

    def test_descartar_es_una_decision_explicita(self):
        """El rabo de una X que baja a la fila de abajo deja 1 punto. Se
        descarta a mano y queda registrado, no se pierde."""
        ficha = _ficha({'p1__pb__tubeado__A': '?'})
        cand = [_candidata('p1__pb__tubeado__A', puntos=1)]
        estados, cambios, dudas = lector.aplicar(
            ficha, cand, {'p1__pb__tubeado__A': lector.DESCARTADA},
            '05/08/2026', 'rev_05082026')
        self.assertEqual(cambios, [])
        self.assertEqual(len(dudas), 1)
        self.assertEqual(estados['p1__pb__tubeado__A']['v'], '?')


class TestSinTintaNoHayCambio(unittest.TestCase):

    def test_clasificar_una_celda_que_no_tiene_tinta_para_la_lectura(self):
        ficha = _ficha({'p1__pb__tubeado__A': '?', 'p1__pb__tubeado__B': '?'})
        cand = [_candidata('p1__pb__tubeado__A')]
        with self.assertRaises(lector.LecturaImposible) as caso:
            lector.aplicar(ficha, cand,
                           {'p1__pb__tubeado__A': 'X',
                            'p1__pb__tubeado__B': 'X'},
                           '05/08/2026', 'rev_05082026')
        self.assertIn('Sin tinta no hay cambio', str(caso.exception))

    def test_un_valor_desconocido_para_la_lectura(self):
        ficha = _ficha({'p1__pb__tubeado__A': '?'})
        cand = [_candidata('p1__pb__tubeado__A')]
        with self.assertRaises(lector.LecturaImposible):
            lector.aplicar(ficha, cand, {'p1__pb__tubeado__A': 'Z'},
                           '05/08/2026', 'rev_05082026')

    def test_una_celda_que_la_ficha_no_tiene_para_la_lectura(self):
        ficha = _ficha({})
        cand = [_candidata('p1__pb__tubeado__A')]
        with self.assertRaises(lector.LecturaImposible):
            lector.aplicar(ficha, cand, {'p1__pb__tubeado__A': 'X'},
                           '05/08/2026', 'rev_05082026')


class TestNormaDeObra(unittest.TestCase):
    """Lo que se apunta en la ultima revision es lo que vale."""

    def test_un_retroceso_marcado_a_boli_se_acepta_a_la_primera(self):
        """Tachar una X y escribir M es una marca explicita: ha ido y ha
        visto que faltaba algo."""
        ficha = _ficha({'p1__pb__tubeado__A': 'X'})
        cand = [_candidata('p1__pb__tubeado__A', antes='X')]
        estados, cambios, _dudas = lector.aplicar(
            ficha, cand, {'p1__pb__tubeado__A': 'M'},
            '05/08/2026', 'rev_05082026')
        self.assertEqual(cambios, [('p1__pb__tubeado__A', 'X', 'M')])
        self.assertEqual(estados['p1__pb__tubeado__A']['v'], 'M')
        self.assertEqual(estados['p1__pb__tubeado__A']['origen'], 'hoja marcada')

    def test_remarcar_lo_mismo_no_es_un_cambio(self):
        ficha = _ficha({'p1__pb__tubeado__A': 'X'})
        cand = [_candidata('p1__pb__tubeado__A', antes='X')]
        _estados, cambios, _dudas = lector.aplicar(
            ficha, cand, {'p1__pb__tubeado__A': 'X'},
            '05/08/2026', 'rev_05082026')
        self.assertEqual(cambios, [])

    def test_la_ficha_no_se_toca_al_calcular(self):
        """`aplicar` devuelve estados nuevos; quien escribe decide cuando."""
        ficha = _ficha({'p1__pb__tubeado__A': '?'})
        cand = [_candidata('p1__pb__tubeado__A')]
        lector.aplicar(ficha, cand, {'p1__pb__tubeado__A': 'X'},
                       '05/08/2026', 'rev_05082026')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], '?')


class TestClaveDesdeLaGeometria(unittest.TestCase):
    """La hoja trae nombres y la ficha ids. Si no casan, no se inventa."""

    def test_el_indice_traduce_nombres_a_ids(self):
        indice = lector.indice_de_ficha(fixtures.ficha_minima())
        self.assertEqual(indice[('Bloque 1', 'P1', 'PB', 'A')],
                         ('p1', 'pb', 'A'))
        self.assertEqual(indice[('Bloque 1', 'P1', '1', 'B')],
                         ('p1', '1', 'B'))

    def test_una_ubicacion_que_la_ficha_no_conoce_no_esta_en_el_indice(self):
        indice = lector.indice_de_ficha(fixtures.ficha_minima())
        self.assertNotIn(('Bloque 1', 'P1', 'PB', 'Z'), indice)


class TestRepartoDeLaTinta(unittest.TestCase):
    """Un trazo es grueso y cruza varias celdas: gana donde caen sus puntos."""

    CELDAS = [
        {'bbox': (0, 0, 10, 10), 'planta': 'PB', 'viv': 'A', 'tajo': 'tubeado'},
        {'bbox': (10, 0, 20, 10), 'planta': 'PB', 'viv': 'B', 'tajo': 'tubeado'},
    ]

    def test_cada_punto_cuenta_en_su_celda(self):
        puntos = [(1, 1), (2, 2), (3, 3), (15, 5)]
        reparto, fuera = lector.repartir(puntos, self.CELDAS)
        self.assertEqual(reparto[('PB', 'A', 'tubeado')], 3)
        self.assertEqual(reparto[('PB', 'B', 'tubeado')], 1)
        self.assertEqual(fuera, 0)

    def test_lo_que_cae_fuera_de_la_rejilla_se_cuenta_aparte(self):
        """Marcar fuera de la rejilla no es un estado, pero tampoco se
        ignora sin decirlo."""
        reparto, fuera = lector.repartir([(1, 1), (99, 99)], self.CELDAS)
        self.assertEqual(sum(reparto.values()), 1)
        self.assertEqual(fuera, 1)


if __name__ == '__main__':
    unittest.main()
