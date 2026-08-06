# -*- coding: utf-8 -*-
"""El generador es la fuente de la traduccion nombre impreso -> catalogo.

`rejilla_hoja.tabla_de_tajos()` parsea `generador_revisiones.html` buscando
`let CAT = [...];` y `const BASE_SOURCE_ID = {...};`. Cualquier edicion del
generador que altere esas dos formas deja la lectura de hojas marcadas sin
traduccion, y el sintoma no aparece hasta que alguien intenta leer una hoja
real: exactamente la familia de fallos de este proyecto.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rejilla_hoja


class ContratoConElGenerador(unittest.TestCase):

    def test_el_generador_sigue_traduciendo_sus_tajos_al_catalogo(self):
        tabla = rejilla_hoja.tabla_de_tajos()
        self.assertGreater(len(tabla), 40,
                           'la tabla de traduccion se ha quedado vacia o corta')
        self.assertIn('tabicado', tabla)
        self.assertEqual(tabla['tabicado']['id'], 'tabicado')

    def test_ningun_tajo_del_generador_queda_fuera_del_catalogo(self):
        # tabla_de_tajos() lanza HojaIlegible si hay huerfanos: que no lance
        # es la afirmacion.
        rejilla_hoja.tabla_de_tajos()


if __name__ == '__main__':
    unittest.main()
