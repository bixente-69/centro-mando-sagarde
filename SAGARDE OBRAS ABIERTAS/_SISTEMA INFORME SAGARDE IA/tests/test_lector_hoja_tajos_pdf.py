# -*- coding: utf-8 -*-
"""Regresiones del cruce entre la hoja PDF y sus correcciones manuales."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lector_hoja_tajos_pdf as lector


TABLA_PORTAL = [
    ['ZR1 · ZR1.2 · PLANTA PB', None],
    [None, 'PLANTA PB'],
    [None, 'PORT\nAL'],
    ['Suelo radiante', ''],
    ['Agujeros ilum ZZCC', 'X'],
]


def _portal(texto):
    return 'p2' if 'ZR1.2' in (texto or '') else None


def _tajo(etiqueta):
    return {
        'Suelo radiante': 'suelo-rad',
        'Agujeros ilum ZZCC': 'aguj-zzcc',
    }.get((etiqueta or '').strip())


def _parsear(correcciones):
    portal_id, registros, dudas = lector._parsear_tabla_pagina(
        TABLA_PORTAL, _portal, _tajo)
    indice, _ = lector._indice_correcciones(correcciones)
    usadas = set()
    celdas, sin_corregir = lector._resolver_celdas(
        portal_id, registros, dudas, indice, usadas)
    huerfanas = [indice[k][0] for k in indice if k not in usadas]
    return celdas, sin_corregir, huerfanas


class TestUnidadPartidaPorElExtractor(unittest.TestCase):

    def test_port_al_casa_con_la_celda_portal(self):
        celdas, _, _ = _parsear({'p2__pb__suelo-rad__PORT AL': 'X'})
        self.assertEqual(celdas[('p2', 'pb', 'suelo-rad', 'PORTAL')], 'X')

    def test_la_correccion_manual_gana_al_valor_impreso(self):
        celdas, _, _ = _parsear({'p2__pb__aguj-zzcc__PORT AL': 'M'})
        self.assertEqual(celdas[('p2', 'pb', 'aguj-zzcc', 'PORTAL')], 'M')

    def test_una_clave_que_casa_no_deja_duda_ni_huerfana(self):
        _, sin_corregir, huerfanas = _parsear(
            {'p2__pb__suelo-rad__PORT AL': 'X'})
        self.assertEqual(sin_corregir, 0)
        self.assertEqual(huerfanas, [])


class TestCorreccionesNoAplicables(unittest.TestCase):

    def test_celda_sin_correccion_queda_pendiente(self):
        celdas, sin_corregir, _ = _parsear({})
        self.assertEqual(celdas[('p2', 'pb', 'suelo-rad', 'PORTAL')], '')
        self.assertEqual(sin_corregir, 1)

    def test_correccion_sin_destino_se_reporta_como_huerfana(self):
        _, _, huerfanas = _parsear(
            {'p2__pb__suelo-rad__NO_EXISTE': 'X'})
        self.assertEqual(huerfanas, ['p2__pb__suelo-rad__NO_EXISTE'])

    def test_clave_mal_formada_se_separa_y_no_rompe(self):
        indice, malformadas = lector._indice_correcciones(
            {'p2__pb__suelo-rad': 'X'})
        self.assertEqual(indice, {})
        self.assertEqual(malformadas, ['p2__pb__suelo-rad'])


class TestHojaSinUsar(unittest.TestCase):
    """Una hoja recien impresa NO es una revision.

    Caso real: REVISION MUNGIA 28072026.pdf. La app la genero desde la ficha,
    nadie la llevo a obra y aun asi entro como revision oficial. Como la app
    imprime en blanco lo que no sabe, sus celdas vacias se leyeron como
    'pendiente confirmado' y tumbaron 35 celdas de la vivienda E de '?' a 'P'.
    Mungia bajaba de 79.8 a 78.6 sin que nadie hubiera pisado la obra.

    El protocolo del HTML ya se defiende de las plantillas en blanco; el del
    PDF no tenia guarda equivalente.
    """

    def test_sin_marcas_y_sin_sidecar_no_aporta_nada(self):
        self.assertFalse(lector.aporta_datos_de_campo(
            'x.pdf', n_anotaciones=0, hay_sidecar=False))

    def test_con_pen_digital_si_aporta(self):
        self.assertTrue(lector.aporta_datos_de_campo(
            'x.pdf', n_anotaciones=56, hay_sidecar=False))

    def test_un_escaneo_transcrito_si_aporta(self):
        """Un escaneo no lleva anotaciones: lo que vale es su sidecar."""
        self.assertTrue(lector.aporta_datos_de_campo(
            'x.pdf', n_anotaciones=0, hay_sidecar=True))

    def test_con_marcas_y_sidecar_tambien(self):
        self.assertTrue(lector.aporta_datos_de_campo(
            'x.pdf', n_anotaciones=12, hay_sidecar=True))


class TestNormalizacionCompartida(unittest.TestCase):

    def test_lector_y_ficha_usan_el_mismo_contrato(self):
        import claves_correcciones
        import ficha_obra
        self.assertIs(
            lector.normalizar_unidad,
            claves_correcciones.normalizar_unidad,
        )
        self.assertIs(
            ficha_obra.partir_clave,
            claves_correcciones.partir_clave,
        )


if __name__ == '__main__':
    unittest.main()
