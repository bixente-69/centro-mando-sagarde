# -*- coding: utf-8 -*-
"""El panel y el informe ejecutivo deben compartir un solo registro."""
import os
import sys
import unittest

SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(SISTEMA_DIR))
sys.path.insert(0, SISTEMA_DIR)
sys.path.insert(0, os.path.join(SISTEMA_DIR, 'adaptadores'))
sys.path.insert(0, os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'scripts'))

import generar_todos
import generar_informe_ejecutivo
import registro_obras


class TestRegistroUnico(unittest.TestCase):

    def test_ids_y_nombres_oficiales_son_unicos(self):
        ids = [obra['id'] for obra in registro_obras.OBRAS]
        nombres = [obra['nombre'] for obra in registro_obras.OBRAS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(nombres), len(set(nombres)))

    def test_nombre_oficial_y_alias_resuelven_la_misma_obra(self):
        for obra in registro_obras.OBRAS:
            self.assertIs(registro_obras.resolver_obra(obra['nombre']), obra)
            for alias in obra.get('aliases', []):
                self.assertIs(registro_obras.resolver_obra(alias), obra)

    def test_generador_importa_la_lista_compartida(self):
        self.assertIs(generar_todos.OBRAS, registro_obras.OBRAS)

    def test_informe_deriva_todos_sus_adaptadores_del_registro(self):
        claves_esperadas = {
            nombre
            for obra in registro_obras.OBRAS
            for nombre in [obra['nombre'], *obra.get('aliases', [])]
        }
        self.assertEqual(
            set(generar_informe_ejecutivo.ADAPTADORES),
            claves_esperadas,
        )
        for obra in registro_obras.OBRAS:
            modulo = generar_informe_ejecutivo.ADAPTADORES[obra['nombre']]
            self.assertEqual(modulo.__name__.split('.')[-1], obra['adaptador'])


if __name__ == '__main__':
    unittest.main()
