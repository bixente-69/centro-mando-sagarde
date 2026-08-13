# -*- coding: utf-8 -*-
"""Pruebas del selector de obras del verificador PDF manual."""
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SISTEMA = os.path.dirname(AQUI)
if SISTEMA not in sys.path:
    sys.path.insert(0, SISTEMA)

import registro_obras
import verificar_hojas_pdf


class ObrasPorDefecto(unittest.TestCase):

    def test_solo_incluye_obras_abiertas_con_rejilla_configurada(self):
        abiertas = {obra['id'] for obra in registro_obras.OBRAS}
        esperadas = [
            obra for obra in verificar_hojas_pdf.ESPERADAS
            if obra in abiertas
        ]

        self.assertEqual(verificar_hojas_pdf.obras_por_defecto(), esperadas)

    def test_no_incluye_la_obra_archivada_obisporueta(self):
        self.assertNotIn(
            'obisporueta', verificar_hojas_pdf.obras_por_defecto())


if __name__ == '__main__':
    unittest.main()
