# -*- coding: utf-8 -*-
"""El lector de hojas marcadas no puede cambiar nada en silencio.

Todo lo que se prueba aqui protege la misma frontera: el codigo pone la clave
de la celda, la vista pone la letra, y ninguna de las dos puede colarse en la
base sin que se vea.
"""
import json
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
        self.assertEqual(indice[('p1', 'PB', 'A')], ('pb', 'A'))
        self.assertEqual(indice[('p1', '1', 'B')], ('1', 'B'))

    def test_una_ubicacion_que_la_ficha_no_conoce_no_esta_en_el_indice(self):
        indice = lector.indice_de_ficha(fixtures.ficha_minima())
        self.assertNotIn(('p1', 'PB', 'Z'), indice)

    def test_la_vivienda_se_encuentra_tambien_por_su_alias(self):
        """La hoja imprime 'A2' (vivienda A de 2 habitaciones, Mungia) donde
        la ficha guarda 'A'. Buscar solo por id pierde la revision entera."""
        ficha = fixtures.ficha_minima()
        ficha['estructura']['alias_historico'] = {'p1__pb__A': 'A2'}
        indice = lector.indice_de_ficha(ficha)
        self.assertEqual(indice[('p1', 'PB', 'A2')], ('pb', 'A'))
        self.assertEqual(indice[('p1', 'PB', 'A')], ('pb', 'A'))


class TestResolverElPortal(unittest.TestCase):
    """La identificacion de la hoja no tiene formato estable. En la de
    Bolueta, 'BOLUETA' es lo que la ficha guarda como PORTAL y 'PORTAL UNICO'
    es solo una etiqueta: tomar la posicion como buena pondria las marcas en
    otro portal."""

    def test_casa_por_bloque_y_portal(self):
        self.assertEqual(
            lector.resolver_portal(fixtures.ficha_minima(),
                                   ['Bloque 1', 'P1']), 'p1')

    def test_casa_aunque_solo_aparezca_el_portal(self):
        self.assertEqual(
            lector.resolver_portal(fixtures.ficha_minima(),
                                   ['BOLUETA', 'P1', 'lo que sea']), 'p1')

    def test_si_no_casa_ninguno_se_para(self):
        with self.assertRaises(lector.LecturaImposible) as caso:
            lector.resolver_portal(fixtures.ficha_minima(), ['ZR9', 'ZR9.9'])
        self.assertIn('no casa', str(caso.exception))

    def test_dos_bloques_con_el_mismo_nombre_de_portal_exigen_el_bloque(self):
        ficha = fixtures.ficha_minima()
        segundo = json.loads(json.dumps(ficha['estructura']['bloques'][0]))
        segundo['id'] = 'b2'
        segundo['nombre'] = 'Bloque 2'
        segundo['portales'][0]['id'] = 'p2'
        ficha['estructura']['bloques'].append(segundo)
        self.assertEqual(
            lector.resolver_portal(ficha, ['Bloque 2', 'P1']), 'p2')
        with self.assertRaises(lector.LecturaImposible):
            lector.resolver_portal(ficha, ['P1'])


class TestCorrectorNoEsUnaMarca(unittest.TestCase):
    """Blanco borra, negro escribe. Tratarlos igual invierte el significado."""

    class _Anot:
        def __init__(self, stroke):
            self.colors = {'stroke': stroke}

    def test_el_trazo_blanco_es_corrector(self):
        self.assertEqual(
            lector.tipo_de_trazo(self._Anot([1.0, 1.0, 1.0])), 'corrector')

    def test_el_trazo_negro_es_una_marca(self):
        self.assertEqual(
            lector.tipo_de_trazo(self._Anot([0.0, 0.0, 0.0])), 'marca')

    def test_un_trazo_sin_color_se_trata_como_marca(self):
        self.assertEqual(lector.tipo_de_trazo(self._Anot([])), 'marca')


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


class TestAgruparPorColumnaParaHojaDigital(unittest.TestCase):
    """Bolueta 24/08/2026, planta 17: la hoja imprime dos plantas por
    pagina desde el 07/08/2026, y las dos repiten los mismos rotulos de
    vivienda ('A','B','C','D'). Agrupar solo por 'viv' fundia la columna A
    de la planta de la izquierda con la A de la derecha; 'Rozas de
    timbres' de la planta 17 se quedo en 'P' con la hoja en 'X' delante
    porque sus glifos se buscaban en la banda x de la planta 16."""

    def _celda(self, planta, viv, x0, tajo='rozas_timbres'):
        return {'planta': planta, 'viv': viv, 'tajo': tajo,
                'bbox': (x0, 83.2, x0 + 37.7, 95.9)}

    def test_la_misma_letra_en_dos_plantas_no_se_funde(self):
        celdas = [self._celda('16', 'A', 265.8), self._celda('17', 'A', 416.1)]
        columnas = lector._agrupar_por_columna(celdas)
        self.assertEqual(set(columnas.keys()), {('16', 'A'), ('17', 'A')})

    def test_cada_columna_conserva_su_propia_banda_x(self):
        celdas = [self._celda('16', 'A', 265.8), self._celda('17', 'A', 416.1)]
        columnas = lector._agrupar_por_columna(celdas)
        self.assertEqual(columnas[('16', 'A')][0]['bbox'][0], 265.8)
        self.assertEqual(columnas[('17', 'A')][0]['bbox'][0], 416.1)


class TestFilaMasCercanaParaHojaDigital(unittest.TestCase):
    """La hoja de Bolueta del 24/08/2026 (rellenada en el generador y
    exportada sin tinta) imprime el glifo 'X' hasta 1.4pt por encima del
    bbox de su propia fila. Los numeros son los medidos en el PDF real."""

    FILAS = [
        {'bbox': (0, 77.80, 400, 86.77), 'tajo': 'grupo'},
        {'bbox': (0, 86.77, 400, 99.42), 'tajo': 'tabicado'},
        {'bbox': (0, 99.42, 400, 112.09), 'tajo': 'rozas_timbres'},
    ]

    def test_un_glifo_que_desborda_su_fila_por_arriba_gana_su_propia_fila(self):
        centro_glifo = (85.4 + 91.4) / 2  # top/bottom reales de la 'X' medida
        fila = lector._fila_mas_cercana(centro_glifo, self.FILAS)
        self.assertEqual(fila['tajo'], 'tabicado')

    def test_no_se_cuela_en_la_fila_de_arriba_ni_la_de_abajo(self):
        centro_arriba = (77.80 + 86.77) / 2
        centro_abajo = (99.42 + 112.09) / 2
        self.assertEqual(
            lector._fila_mas_cercana(centro_arriba, self.FILAS)['tajo'], 'grupo')
        self.assertEqual(
            lector._fila_mas_cercana(centro_abajo, self.FILAS)['tajo'],
            'rozas_timbres')


class TestAplicarDigital(unittest.TestCase):
    """Hoja rellenada en el generador y exportada sin tinta: solo se aplica
    lo impreso explicito. Decision de Bixente el 24/08/2026: una celda en
    blanco no se toca (a diferencia de una hoja marcada a boli, que si lleva
    sus blancos a 'P')."""

    def test_una_celda_marcada_avanza(self):
        ficha = _ficha({'p1__pb__tubeado__A': 'P'})
        estados, cambios = lector.aplicar_digital(
            ficha, {'p1__pb__tubeado__A': 'X'}, '24/08/2026', 'rev_24082026')
        self.assertEqual(cambios, [('p1__pb__tubeado__A', 'P', 'X')])
        self.assertEqual(estados['p1__pb__tubeado__A']['v'], 'X')
        self.assertEqual(estados['p1__pb__tubeado__A']['origen'],
                         'hoja generada rellenada digitalmente')

    def test_lo_que_no_imprime_marca_no_se_toca(self):
        """Solo se pasan las celdas de VALIDOS_IMPRESOS: una celda que en el
        PDF sale en blanco ni siquiera llega a esta funcion."""
        ficha = _ficha({'p1__pb__tubeado__A': 'P', 'p1__pb__tubeado__B': '?'})
        estados, cambios = lector.aplicar_digital(
            ficha, {'p1__pb__tubeado__A': 'X'}, '24/08/2026', 'rev_24082026')
        self.assertEqual(cambios, [('p1__pb__tubeado__A', 'P', 'X')])
        self.assertEqual(estados['p1__pb__tubeado__B']['v'], '?')

    def test_remarcar_lo_mismo_no_es_un_cambio(self):
        ficha = _ficha({'p1__pb__tubeado__A': 'X'})
        _estados, cambios = lector.aplicar_digital(
            ficha, {'p1__pb__tubeado__A': 'X'}, '24/08/2026', 'rev_24082026')
        self.assertEqual(cambios, [])

    def test_una_celda_que_la_ficha_no_tiene_para_la_lectura(self):
        ficha = _ficha({})
        with self.assertRaises(lector.LecturaImposible):
            lector.aplicar_digital(
                ficha, {'p1__pb__tubeado__A': 'X'}, '24/08/2026', 'rev_24082026')


if __name__ == '__main__':
    unittest.main()
