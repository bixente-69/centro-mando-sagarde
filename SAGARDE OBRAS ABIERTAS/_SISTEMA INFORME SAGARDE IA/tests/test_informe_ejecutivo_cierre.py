# -*- coding: utf-8 -*-
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT = os.path.dirname(os.path.dirname(_BASE))  # -> raiz del repo
_SCRIPTS = os.path.join(_ROOT, '_SISTEMA', 'MOTOR', 'scripts')
for ruta in (_BASE, _SCRIPTS):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

import cierre_expediente as ce
from generar_informe_ejecutivo import _tabla_cierre_expediente
from reportlab.platypus import Table, Paragraph


class TestTablaCierreExpediente(unittest.TestCase):

    def test_sin_datos_devuelve_parrafo_informativo(self):
        resultado = _tabla_cierre_expediente(None, [], content_w=170)
        self.assertIsInstance(resultado, Paragraph)

    def test_con_datos_devuelve_una_tabla_de_cuatro_filas_mas_cabecera(self):
        cierre = ce.vacio('OBRA X')
        cierre['hitos']['libro_edificio'] = {
            'estado': 'hecho', 'fecha': '12/08/2026', 'nota': 'entregado'}
        resultado = _tabla_cierre_expediente(cierre, [], content_w=170)
        self.assertIsInstance(resultado, Table)
        self.assertEqual(len(resultado._cellvalues), 5)  # cabecera + 4 hitos

    def test_con_avisos_no_revienta_y_devuelve_flowables(self):
        from reportlab.platypus import KeepTogether
        cierre = ce.vacio('OBRA X')
        resultado = _tabla_cierre_expediente(
            cierre, ["cierre_expediente.json: 'inspeccion_oca' tiene un "
                     "estado no reconocido ('revisar'); revisar a mano."],
            content_w=170)
        self.assertIsInstance(resultado, KeepTogether)


if __name__ == '__main__':
    unittest.main()
