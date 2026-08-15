# -*- coding: utf-8 -*-
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import cierre_expediente as ce
from panel_obra import bloque_cierre


class TestBloqueCierre(unittest.TestCase):

    def test_cierre_vacio_muestra_los_cuatro_hitos_pendientes(self):
        html = bloque_cierre(ce.vacio('OBRA X'))
        self.assertIn('Ensayos instrumentales', html)
        self.assertIn('Inspección OCA', html)
        self.assertIn('CIE / Boletín eléctrico', html)
        self.assertIn('Libro del Edificio', html)
        self.assertEqual(html.count('pendiente'), 4)

    def test_hito_hecho_se_refleja_en_el_html(self):
        datos = ce.vacio('OBRA X')
        datos['hitos']['libro_edificio'] = {
            'estado': 'hecho', 'fecha': '12/08/2026', 'nota': 'entregado'}
        html = bloque_cierre(datos)
        self.assertIn('hecho', html)
        self.assertIn('12/08/2026', html)
        self.assertIn('entregado', html)

    def test_avisos_se_muestran_como_banner(self):
        html = bloque_cierre(ce.vacio('OBRA X'), avisos=['dato raro en el fichero'])
        self.assertIn('dato raro en el fichero', html)

    def test_sin_avisos_no_hay_banner_de_aviso(self):
        html = bloque_cierre(ce.vacio('OBRA X'), avisos=[])
        self.assertNotIn('banner bad', html)


if __name__ == '__main__':
    unittest.main()


class TestGenerarPanelConCierre(unittest.TestCase):

    def test_generar_panel_incluye_la_pestana_cierre_sin_reventar(self):
        import tempfile
        from panel_obra import generar_panel

        with tempfile.TemporaryDirectory() as tmp:
            salida = os.path.join(tmp, 'panel.html')
            resultado = generar_panel(
                obra='OBRA DE PRUEBAS', subtitulo='Prueba',
                historial=[], materiales={'disponible': False},
                ficha={'_disponible': False}, documentos=[],
                output_path=salida,
                cierre=ce.vacio('OBRA DE PRUEBAS'),
                cierre_avisos=[],
            )
            with open(salida, encoding='utf-8') as f:
                contenido = f.read()
            self.assertIn('data-view="v-cierre"', contenido)
            self.assertIn('id="v-cierre"', contenido)
            self.assertIn('Cierre de expediente', contenido)
