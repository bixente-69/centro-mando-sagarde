# -*- coding: utf-8 -*-
"""Pruebas que matan mutaciones supervivientes de `rejilla_hoja.py`.

Origen: auditoria por mutacion del 04/11/2026
(`_SISTEMA/docs/auditorias_nube_2026-11-04/B_mutaciones.md`). El error caro de
leer una hoja no es confundir una X con una M: es atribuir la marca a la fila
o columna equivocada (`rejilla_hoja.py`, cabecera del modulo). Al romper a
proposito la asignacion de planta a cada celda y la tolerancia en x, la suite
siguio en verde. Cada prueba dice que mutacion mata (RHxx, ver el informe).

Son funciones puras: se monta la estructura que devolveria pdfplumber, sin PDF.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rejilla_hoja as rejilla


TAJOS = {
    rejilla.fold('Tabicado'): {'id': 'tabicado', 'nombre': 'Tabicado'},
}

IDENT = 'OBRA X · 05/08/2026 · BLOQUE 1 · PORTAL 2 · PLANTAS PB · 1ª'
CELDA_TAJO = (0, 10, 100, 30)     # la de la esquina, con rowspan 2


def _tabla(cabecera_plantas, cabecera_vivs, filas_tajo, textos, ident=IDENT):
    """Misma estructura que `test_rejilla_hoja._tabla` (no se importa de alli
    para no acoplar dos ficheros de prueba)."""
    filas = [((0, 0, 400, 10), [(0, 0, 400, 10)])]
    filas.append(((0, 10, 400, 20), [CELDA_TAJO] + cabecera_plantas))
    filas.append(((0, 20, 400, 30), cabecera_vivs))
    for top, celdas in filas_tajo:
        filas.append(((0, top, 400, top + 10), celdas))
    completo = {(0, 0, 400, 10): ident, CELDA_TAJO: 'TAJO'}
    completo.update(textos)
    return filas, lambda b: completo.get(tuple(b), '')


class TestLimpio(unittest.TestCase):

    def test_colapsa_cualquier_racha_de_espacios_en_uno(self):
        # Mata RH02 (`\s+` -> `\s`): la racha entera, no cada blanco suelto.
        self.assertEqual(rejilla.limpio('  a \n  b\t\tc  '), 'a b c')
        self.assertEqual(rejilla.limpio(None), '')


class TestCeldaDeCadaPlanta(unittest.TestCase):
    """Cada celda lleva la planta de SU columna, no la de la primera."""

    def test_las_celdas_de_la_segunda_planta_no_se_atribuyen_a_la_primera(self):
        # Mata RH23. Dos plantas con una y dos viviendas: si todas las celdas
        # cayeran en PB, la marca de '1ª/B' se escribiria en el sitio
        # equivocado y nadie se enteraria.
        plantas = [(100, 10, 150, 20), (150, 10, 400, 20)]
        vivs = [(0, 20, 100, 30), (100, 20, 150, 30),
                (150, 20, 270, 30), (270, 20, 400, 30)]
        textos = {
            (100, 10, 150, 20): 'PLANTA PB · 1 VIV.',
            (150, 10, 400, 20): 'PLANTA 1ª · 2 VIV.',
            (0, 20, 100, 30): 'TAJO',
            (100, 20, 150, 30): 'A',
            (150, 20, 270, 30): 'A', (270, 20, 400, 30): 'B',
            (0, 40, 100, 50): 'Tabicado',
        }
        filas, texto = _tabla(plantas, vivs, [
            (40, [(0, 40, 100, 50), (100, 40, 150, 50),
                  (150, 40, 270, 50), (270, 40, 400, 50)]),
        ], textos)
        tabla = rejilla.leer_tabla(filas, texto, TAJOS)
        self.assertEqual(
            [(c['planta'], c['viv'], c['tajo']) for c in tabla['celdas']],
            [('PB', 'A', 'tabicado'), ('1ª', 'A', 'tabicado'),
             ('1ª', 'B', 'tabicado')])


class TestToleranciaEnX(unittest.TestCase):
    """Una columna pertenece a la planta cuyo rango x contiene su centro, con
    medio punto de tolerancia. Mas alla no se coloca "a ojo": se para."""

    def _con_columna(self, x0, x1):
        plantas = [(100, 10, 400, 20)]
        vivs = [(0, 20, 100, 30), (x0, 20, x1, 30)]
        textos = {(100, 10, 400, 20): 'PLANTA 1ª · 1 VIV.',
                  (0, 20, 100, 30): 'TAJO', (x0, 20, x1, 30): 'A'}
        filas, texto = _tabla(plantas, vivs, [], textos)
        return rejilla.leer_tabla(filas, texto, TAJOS)

    def test_centro_dentro_de_la_tolerancia_por_la_izquierda_se_acepta(self):
        # Mata RH14. Centro 99.6; el rango empieza en 100 y tolera 0.5.
        tabla = self._con_columna(99.2, 100.0)
        self.assertEqual(tabla['plantas'][0]['vivs'], ['A'])

    def test_centro_fuera_de_la_tolerancia_por_la_izquierda_se_para(self):
        # Centro 99.4: 0.6 fuera. Colocarla a ojo seria el error caro.
        with self.assertRaises(rejilla.HojaIlegible):
            self._con_columna(98.8, 100.0)

    def test_centro_dentro_de_la_tolerancia_por_la_derecha_se_acepta(self):
        # Mata RH15. Centro 400.4; el rango acaba en 400 y tolera 0.5.
        tabla = self._con_columna(400.0, 400.8)
        self.assertEqual(tabla['plantas'][0]['vivs'], ['A'])

    def test_centro_fuera_de_la_tolerancia_por_la_derecha_se_para(self):
        with self.assertRaises(rejilla.HojaIlegible):
            self._con_columna(400.2, 401.0)


class TestFilaDeObservaciones(unittest.TestCase):

    def test_una_fila_obs_no_se_toma_por_un_tajo(self):
        # Mata RH20: la fila 'Obs: ...' (con celdas por vivienda) se salta;
        # con otra capitalizacion se intentaria resolver como tajo y la hoja
        # entera dejaria de leerse.
        plantas = [(100, 10, 400, 20)]
        vivs = [(0, 20, 100, 30), (100, 20, 400, 30)]
        textos = {(100, 10, 400, 20): 'PLANTA 1ª · 1 VIV.',
                  (0, 20, 100, 30): 'TAJO', (100, 20, 400, 30): 'A',
                  (0, 40, 100, 50): 'Obs: falta material de otra empresa'}
        filas, texto = _tabla(plantas, vivs, [
            (40, [(0, 40, 100, 50), (100, 40, 400, 50)]),
        ], textos)
        tabla = rejilla.leer_tabla(filas, texto, TAJOS)
        self.assertEqual(tabla['tajos'], [])
        self.assertEqual(tabla['celdas'], [])


class TestIdentificacionDeLaTabla(unittest.TestCase):

    def test_dos_filas_no_bastan_para_ser_una_tabla_de_revision(self):
        # Mata RH05: identificacion + plantas y nada mas no es una hoja
        # (faltaria la fila de viviendas). Es "no es tabla", no un error.
        filas = [((0, 0, 400, 10), [(0, 0, 400, 10)]),
                 ((0, 10, 400, 20), [CELDA_TAJO, (100, 10, 400, 20)])]
        textos = {(0, 0, 400, 10): IDENT}
        self.assertIsNone(rejilla.leer_tabla(
            filas, lambda b: textos.get(tuple(b), ''), TAJOS))

    def test_la_fila_siguiente_a_la_identificacion_debe_ser_la_de_plantas(self):
        # Mata RH08: una fila de una sola celda tras la identificacion no es
        # la cabecera de plantas (esa tiene varias): no es una tabla.
        filas = [((0, 0, 400, 10), [(0, 0, 400, 10)]),
                 ((0, 10, 400, 20), [(0, 10, 400, 20)]),
                 ((0, 20, 400, 30), [(0, 20, 400, 30)]),
                 ((0, 30, 400, 40), [(0, 30, 400, 40)])]
        textos = {(0, 0, 400, 10): IDENT}
        self.assertIsNone(rejilla.leer_tabla(
            filas, lambda b: textos.get(tuple(b), ''), TAJOS))

    def test_una_identificacion_con_una_sola_etiqueta_se_para(self):
        # Mata RH09: sin al menos dos etiquetas no hay bloque ni portal, y
        # adivinar la posicion pondria las marcas en otro portal.
        plantas = [(100, 10, 400, 20)]
        vivs = [(0, 20, 100, 30), (100, 20, 400, 30)]
        textos = {(100, 10, 400, 20): 'PLANTA 1ª · 1 VIV.',
                  (0, 20, 100, 30): 'TAJO', (100, 20, 400, 30): 'A'}
        filas, texto = _tabla(plantas, vivs, [], textos,
                              ident='OBRA X · PLANTAS PB · 1ª')
        with self.assertRaises(rejilla.HojaIlegible) as caso:
            rejilla.leer_tabla(filas, texto, TAJOS)
        self.assertIn('identificacion incompleta', str(caso.exception))

    def _leer(self, ident):
        plantas = [(100, 10, 400, 20)]
        vivs = [(0, 20, 100, 30), (100, 20, 400, 30)]
        textos = {(100, 10, 400, 20): 'PLANTA 1ª · 1 VIV.',
                  (0, 20, 100, 30): 'TAJO', (100, 20, 400, 30): 'A'}
        filas, texto = _tabla(plantas, vivs, [], textos, ident=ident)
        return rejilla.leer_tabla(filas, texto, TAJOS)

    def test_con_tres_etiquetas_la_primera_es_la_obra(self):
        tabla = self._leer(IDENT)
        self.assertEqual(
            (tabla['obra'], tabla['bloque'], tabla['portal'], tabla['fecha']),
            ('OBRA X', 'BLOQUE 1', 'PORTAL 2', '05/08/2026'))

    def test_con_dos_etiquetas_no_hay_obra_y_son_bloque_y_portal(self):
        # Mata RH10: el formato viejo (Bolueta 26/07/2026) solo trae
        # "BOLUETA · PORTAL UNICO"; la primera etiqueta es el bloque, no la
        # obra. Tomarla por la obra la quitaria de bloque.
        tabla = self._leer('BOLUETA · PORTAL UNICO · PLANTAS PB · 1')
        self.assertIsNone(tabla['obra'])
        self.assertIsNone(tabla['fecha'])
        self.assertEqual((tabla['bloque'], tabla['portal']),
                         ('BOLUETA', 'PORTAL UNICO'))


if __name__ == '__main__':
    unittest.main()
