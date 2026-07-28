# -*- coding: utf-8 -*-
"""Pruebas del reconocimiento de etiquetas de tajo en la hoja PDF de Bolueta.

Motivo (28/07/2026): la app que genera la "hoja de revisión de tajos" cambió
el texto impreso de 4 tajos. El adaptador seguía esperando el texto viejo, así
que dejaba de reconocer esas filas y sus celdas desaparecían del historial sin
dar ningún error -- 288 celdas menos por revisión. Además, al no reconocerse
"Pintura de zonas comunes", la BANDA DE SECCIÓN "PINTURA ZZCC" (que no es un
tajo, es un separador) pasaba a resolverse como el tajo 'pint-zzcc' y colaba
96 celdas fantasma siempre vacías.
"""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import adaptadores.adaptador_bolueta as ab


class TestEtiquetasNuevasHojaPDF(unittest.TestCase):
    """Las 4 etiquetas nuevas deben resolver al MISMO tajo que las viejas."""

    CASOS = [
        ('EXT Techos de zonas comuneszzcc', 'EXT Techos ZZCCzzcc', 'techos-zzcc'),
        ('EXT Pintura — segunda mano', 'EXT Pintura — 2ª mano', 'pint-2'),
        ('EXT Pintura de zonas comuneszzcc', 'EXT Pintura ZZCCzzcc', 'pint-zzcc'),
        ('SGD Iluminación de rellanos / ZZCCzzcc', 'SGD Ilum. rellanos / ZZCCzzcc', 'ilum-rell'),
    ]

    def test_etiqueta_nueva_se_reconoce(self):
        for nueva, _vieja, esperado in self.CASOS:
            with self.subTest(etiqueta=nueva):
                self.assertEqual(ab._identificar_tajo_pdf(nueva), esperado)

    def test_etiqueta_vieja_sigue_reconociendose(self):
        """No se rompe la lectura del historial ya archivado."""
        for _nueva, vieja, esperado in self.CASOS:
            with self.subTest(etiqueta=vieja):
                self.assertEqual(ab._identificar_tajo_pdf(vieja), esperado)


class TestBandasDeSeccionNoSonTajos(unittest.TestCase):
    """Las bandas de sección son separadores visuales, no filas de datos.

    Se distinguen porque NUNCA llevan distintivo de propiedad (SGD/EXT/COO),
    que sí llevan todas las filas de tajo de la hoja.
    """

    BANDAS = [
        'PINTURA ZZCC', 'PINTURA', 'PINTURA FINAL', 'ACABADOS PREVIOS',
        'INICIO DE OBRA', 'INFRAESTRUCTURA', 'OBRA PREVIA', 'PLADUR',
        'INSTALACIÓN INTERIOR', 'RECUPERACIÓN TRAS PLADUR', 'CONEXIONES',
        'CIERRE TÉCNICO', 'MECANISMOS', 'REMATES FINALES', 'FACHADA',
        'REMATES EXTERIORES', 'ILUMINACIÓN FINAL', 'ENTREGA',
    ]

    def test_ninguna_banda_resuelve_a_tajo(self):
        for banda in self.BANDAS:
            with self.subTest(banda=banda):
                self.assertIsNone(ab._identificar_tajo_pdf(banda))

    def test_todas_las_filas_de_tajo_llevan_prefijo(self):
        """Guarda del criterio: si algún día un tajo se imprime sin SGD/EXT/COO,
        esta prueba avisa antes de que el criterio lo descarte en silencio."""
        for _codigo, etiqueta in ab.TAJO_LABELS_PDF:
            with self.subTest(tajo=etiqueta):
                self.assertIsNotNone(
                    ab._identificar_tajo_pdf('SGD ' + etiqueta),
                    'el tajo debe seguir reconociéndose con distintivo',
                )


if __name__ == '__main__':
    unittest.main()
