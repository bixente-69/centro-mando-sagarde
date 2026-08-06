# -*- coding: utf-8 -*-
"""La rejilla de la hoja se resuelve por geometria, no leyendo texto.

Las trampas que se prueban aqui no son hipoteticas: las tres aparecieron el
05/08/2026 leyendo la primera hoja de OBRA PRUEBA, y las tres producian un
dato plausible en el sitio equivocado, que es el error caro de este proyecto.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rejilla_hoja as rejilla


# Un tajo de juguete por cada nombre que usan las tablas de abajo.
TAJOS = {
    rejilla.fold('Tabicado'): {'id': 'tabicado', 'nombre': 'Tabicado'},
    rejilla.fold('Apliques terraza'): {'id': 'apliques', 'nombre': 'Apliques'},
}


IDENT = 'OBRA X · 05/08/2026 · BLOQUE 1 · PORTAL 2 · PLANTAS PB · 1ª'
CELDA_TAJO = (0, 10, 100, 30)     # la de la esquina, con rowspan 2


def _tabla(cabecera_plantas, cabecera_vivs, filas_tajo, textos, ident=IDENT):
    """Monta la estructura que devuelve pdfplumber, sin PDF de por medio.

    Cada celda es (x0, top, x1, bottom). Solo importan las x en las cabeceras
    y el numero de celdas en las filas de tajo. Devuelve (filas, texto), donde
    `texto` es la funcion que el modulo usa para leer un recorte.
    """
    filas = [((0, 0, 400, 10), [(0, 0, 400, 10)])]          # identificacion
    filas.append(((0, 10, 400, 20), [CELDA_TAJO] + cabecera_plantas))
    filas.append(((0, 20, 400, 30), cabecera_vivs))
    for top, celdas in filas_tajo:
        filas.append(((0, top, 400, top + 10), celdas))
    completo = {(0, 0, 400, 10): ident, CELDA_TAJO: 'TAJO'}
    completo.update(textos)
    return filas, lambda b: completo.get(tuple(b), '')


class TestColumnaEnSuPlanta(unittest.TestCase):
    """Cada columna de vivienda pertenece a la planta cuyo rango x la
    contiene. Repartirlas por orden de lectura las desplaza cuando una
    cabecera viene partida en varias lineas."""

    def test_las_viviendas_van_a_la_planta_que_las_contiene(self):
        plantas = [(100, 10, 150, 20), (150, 10, 400, 20)]
        vivs = [(0, 20, 100, 30),                       # celda TAJO
                (100, 20, 150, 30),                     # PB: 1 vivienda
                (150, 20, 210, 30), (210, 20, 270, 30),
                (270, 20, 330, 30), (330, 20, 400, 30)]  # 1ª: 4 viviendas
        textos = {
            (100, 10, 150, 20): 'PLANPB · 1 VIV.',      # texto contaminado
            (150, 10, 400, 20): 'APLANTA 1ª · 4 VIV.',  # texto contaminado
            (0, 20, 100, 30): 'TAJO',
            (100, 20, 150, 30): 'A',
            (150, 20, 210, 30): 'A', (210, 20, 270, 30): 'B',
            (270, 20, 330, 30): 'C', (330, 20, 400, 30): 'D',
        }
        filas, texto = _tabla(plantas, vivs, [], textos)
        tabla = rejilla.leer_tabla(filas, texto, TAJOS)
        self.assertEqual(
            [(p['nombre'], p['vivs']) for p in tabla['plantas']],
            [('PB', ['A']), ('1ª', ['A', 'B', 'C', 'D'])])

    def test_si_la_cabecera_no_cuadra_con_la_rejilla_se_para(self):
        """La cabecera declara 4 viviendas y solo hay 2 columnas: la hoja se
        contradice a si misma y eso se ve antes de equivocarse."""
        plantas = [(100, 10, 400, 20)]
        vivs = [(0, 20, 100, 30), (100, 20, 250, 30), (250, 20, 400, 30)]
        textos = {(100, 10, 400, 20): 'PLANTA 1ª · 4 VIV.',
                  (0, 20, 100, 30): 'TAJO',
                  (100, 20, 250, 30): 'A', (250, 20, 400, 30): 'B'}
        filas, texto = _tabla(plantas, vivs, [], textos)
        with self.assertRaises(rejilla.HojaIlegible) as caso:
            rejilla.leer_tabla(filas, texto, TAJOS)
        self.assertIn('declara 4', str(caso.exception))


class TestCabeceraDeGrupoNoEsUnTajo(unittest.TestCase):
    """"REMATES EXTERIORES" contiene "EXT", el distintivo de propiedad. Por
    texto se colaba como un tajo llamado "REMATES ERIORES"; se distingue
    porque una cabecera de grupo ocupa toda la fila."""

    def _tabla_con(self, filas_tajo):
        plantas = [(100, 10, 400, 20)]
        vivs = [(0, 20, 100, 30), (100, 20, 400, 30)]
        textos = {(100, 10, 400, 20): 'PLANTA 1ª · 1 VIV.',
                  (0, 20, 100, 30): 'TAJO', (100, 20, 400, 30): 'A',
                  (0, 40, 100, 50): 'REMATES EXTERIORES',
                  (0, 50, 100, 60): 'SGDApliques terraza'}
        return _tabla(plantas, vivs, filas_tajo, textos)

    def test_la_cabecera_de_grupo_no_produce_un_tajo(self):
        filas, texto = self._tabla_con([
            (40, [(0, 40, 400, 50)]),                     # grupo: 1 celda
            (50, [(0, 50, 100, 60), (100, 50, 400, 60)]),  # tajo: 2 celdas
        ])
        tabla = rejilla.leer_tabla(filas, texto, TAJOS)
        self.assertEqual([t['id'] for t in tabla['tajos']], ['apliques'])

    def test_un_tajo_desconocido_para_la_lectura(self):
        """Antes que inventarle un id, que lo dejaria fuera de los calculos
        sin avisar, se para."""
        filas, texto = self._tabla_con([
            (50, [(0, 50, 100, 60), (100, 50, 400, 60)]),
        ])
        with self.assertRaises(rejilla.HojaIlegible):
            rejilla.leer_tabla(filas, texto, {})


class TestUnaCeldaPorTajoYVivienda(unittest.TestCase):

    def test_se_genera_la_celda_con_su_clave_completa(self):
        plantas = [(100, 10, 400, 20)]
        vivs = [(0, 20, 100, 30), (100, 20, 250, 30), (250, 20, 400, 30)]
        textos = {(100, 10, 400, 20): 'PLANTA 1ª · 2 VIV.',
                  (0, 20, 100, 30): 'TAJO',
                  (100, 20, 250, 30): 'A', (250, 20, 400, 30): 'B',
                  (0, 40, 100, 50): 'EXTTabicado'}
        filas, texto = _tabla(plantas, vivs, [
            (40, [(0, 40, 100, 50), (100, 40, 250, 50), (250, 40, 400, 50)]),
        ], textos)
        tabla = rejilla.leer_tabla(filas, texto, TAJOS)
        self.assertEqual(len(tabla['celdas']), 2)
        self.assertEqual(
            [(c['portal'], c['planta'], c['viv'], c['tajo'])
             for c in tabla['celdas']],
            [('PORTAL 2', '1ª', 'A', 'tabicado'),
             ('PORTAL 2', '1ª', 'B', 'tabicado')])

    def test_una_tabla_sin_identificacion_no_es_de_revision(self):
        """La portada y el pie tambien traen 'tabla'. No son un error."""
        filas = [((0, 0, 400, 10), [(0, 0, 400, 10)])]
        self.assertIsNone(
            rejilla.leer_tabla(filas, lambda b: 'BLOQUE 2 Portal 1', TAJOS))


class TestTraduccionDeTajos(unittest.TestCase):
    """La hoja imprime nombres cortos y el catalogo guarda los largos."""

    def test_los_nombres_cortos_de_la_hoja_llegan_al_catalogo(self):
        indice = rejilla.tabla_de_tajos()
        for corto, esperado in [('Montante teleco', 'montante_teleco'),
                                ('1ªs caras Pladur', 'primera_cara_pladur'),
                                ('Tubeado vivienda', 'tubeado'),
                                ('Pintura — 1ª mano', 'pintura_primera'),
                                ('Ilum. rellanos / ZZCC', 'iluminacion_rellanos')]:
            with self.subTest(corto):
                self.assertEqual(indice[rejilla.fold(corto)]['id'], esperado)


if __name__ == '__main__':
    unittest.main()
