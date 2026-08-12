# -*- coding: utf-8 -*-
"""La linea base tiene que medir lo mismo que se midio a mano el 11/08/2026."""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from linea_base_prioridades import medir_prioridades


class TestLineaBase(unittest.TestCase):

    def test_cuenta_preguntas_unidades_y_ubicaciones(self):
        datos = {
            'resumen': {'preguntas_pendientes': 3},
            'items': [
                {'situacion': 'VERIFICAR', 'n_unidades': 4, 'ambito': 'vivienda'},
                {'situacion': 'LISTO', 'n_unidades': 7, 'ambito': 'edificio'},
            ],
            'detalle_items': [
                {'edificio': 'P1', 'planta': 'PB', 'unidad': 'A'},
                {'edificio': 'P1', 'planta': 'PB', 'unidad': 'A'},
                {'edificio': 'P1', 'planta': '1', 'unidad': 'B'},
            ],
        }
        medida = medir_prioridades(datos)
        self.assertEqual(medida['preguntas'], 3)
        self.assertEqual(medida['unidades_verificar'], 4)
        self.assertEqual(medida['unidades_listas'], 7)
        self.assertEqual(medida['ubicaciones'], 2)
        self.assertEqual(medida['unidades_no_vivienda'], 7)
        self.assertEqual(medida['celdas'], 3)

    def test_dos_portales_con_las_mismas_letras_no_se_colapsan(self):
        """Gernika tiene dos portales con las mismas plantas y las mismas
        letras. Contar sin el edificio daba 16 ubicaciones donde hay 32."""
        datos = {'detalle_items': [
            {'edificio': 'PORTAL 1', 'planta': 'PB', 'unidad': 'A'},
            {'edificio': 'PORTAL 2', 'planta': 'PB', 'unidad': 'A'},
        ]}
        self.assertEqual(medir_prioridades(datos)['ubicaciones'], 2)

    def test_una_salida_vacia_no_revienta(self):
        medida = medir_prioridades({})
        self.assertEqual(medida['preguntas'], 0)
        self.assertEqual(medida['ubicaciones'], 0)
        self.assertEqual(medida['celdas'], 0)


if __name__ == '__main__':
    unittest.main()
