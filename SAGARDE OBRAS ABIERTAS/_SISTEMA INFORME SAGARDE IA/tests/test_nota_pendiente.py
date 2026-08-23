# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from nota_pendiente import CABECERA_TAREAS, anadir_tarea_pendiente


class TestNotaPendiente(unittest.TestCase):

    def _crear_ficha(self, carpeta, preparar=None):
        ruta = os.path.join(carpeta, 'FICHA DE OBRA.xlsx')
        wb = Workbook()
        wb.active.title = 'Datos'
        if preparar:
            preparar(wb)
        wb.save(ruta)
        wb.close()
        return ruta

    def _anadir(self, ruta):
        anadir_tarea_pendiente(
            ruta,
            tarea='Revisar temas del correo de obra',
            origen='Correo reenviado por Iker',
            fecha='20/08/2026',
            archivo='TEMAS PENDIENTES 20-08-2026.txt',
        )

    def test_crea_hoja_con_cabecera_y_fila_si_no_existe(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = self._crear_ficha(carpeta)
            self._anadir(ruta)
            wb = load_workbook(ruta, data_only=False)
            filas = list(wb['Tareas'].iter_rows(values_only=True))
            wb.close()

        self.assertEqual(filas, [
            tuple(CABECERA_TAREAS),
            ('Revisar temas del correo de obra',
             'Correo reenviado por Iker', '20/08/2026',
             'TEMAS PENDIENTES 20-08-2026.txt', 'Pendiente'),
        ])

    def test_anade_al_final_sin_tocar_filas_existentes(self):
        def preparar(wb):
            ws = wb.create_sheet('Tareas')
            ws.append(CABECERA_TAREAS)
            ws.append([
                'Tarea anterior', 'WhatsApp', '19/08/2026',
                'NOTA ANTERIOR.txt', 'Hecho',
            ])

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = self._crear_ficha(carpeta, preparar)
            self._anadir(ruta)
            wb = load_workbook(ruta, data_only=False)
            filas = list(wb['Tareas'].iter_rows(values_only=True))
            wb.close()

        self.assertEqual(filas[0], tuple(CABECERA_TAREAS))
        self.assertEqual(filas[1], (
            'Tarea anterior', 'WhatsApp', '19/08/2026',
            'NOTA ANTERIOR.txt', 'Hecho'))
        self.assertEqual(filas[2], (
            'Revisar temas del correo de obra',
            'Correo reenviado por Iker', '20/08/2026',
            'TEMAS PENDIENTES 20-08-2026.txt', 'Pendiente'))

    def test_otra_hoja_con_datos_formula_y_estilo_sobrevive(self):
        def preparar(wb):
            ws = wb.create_sheet('Riesgos')
            ws.append(['Riesgo', 'Estado', 'Control'])
            ws.append(['Retraso de suministro', 'Abierto', '=1+1'])
            ws['A2'].font = Font(bold=True)

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = self._crear_ficha(carpeta, preparar)
            self._anadir(ruta)
            wb = load_workbook(ruta, data_only=False)
            riesgos = list(wb['Riesgos'].iter_rows(values_only=True))
            formula = wb['Riesgos']['C2'].value
            negrita = wb['Riesgos']['A2'].font.bold
            wb.close()

        self.assertEqual(riesgos, [
            ('Riesgo', 'Estado', 'Control'),
            ('Retraso de suministro', 'Abierto', '=1+1'),
        ])
        self.assertEqual(formula, '=1+1')
        self.assertTrue(negrita)


if __name__ == '__main__':
    unittest.main()
