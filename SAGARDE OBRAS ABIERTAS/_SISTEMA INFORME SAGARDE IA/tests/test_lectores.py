# -*- coding: utf-8 -*-
from datetime import date
import os
import sys
import tempfile
import unittest

from openpyxl import Workbook

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lectores import leer_ficha, listar_documentos


class TestListarDocumentosIgnoraLoTecnico(unittest.TestCase):
    """Bolueta 24/08/2026: leer una hoja de revision escribe sidecars JSON en
    REVISIONES/_SISTEMA/ (candidatas, correcciones, recortes). Sin excluir
    esa carpeta, 'Documentos' los contaba como si Bixente pudiera abrirlos:
    9 ficheros de sobra, y la pestaña parecia no haberse actualizado nunca
    porque el ruido tapaba el cambio real."""

    def _obra(self, carpeta):
        os.makedirs(os.path.join(carpeta, 'REVISIONES', '_SISTEMA'))
        os.makedirs(os.path.join(carpeta, 'INFORME SAGARDE IA'))
        with open(os.path.join(carpeta, 'REVISIONES', 'hoja.pdf'), 'w') as f:
            f.write('x')
        with open(os.path.join(carpeta, 'REVISIONES', '_SISTEMA',
                               'hoja.pdf.correcciones.json'), 'w') as f:
            f.write('{}')
        with open(os.path.join(carpeta, 'INFORME SAGARDE IA', 'panel.html'),
                 'w') as f:
            f.write('<html></html>')

    def test_lo_tecnico_de_sistema_no_cuenta_como_documento(self):
        with tempfile.TemporaryDirectory() as carpeta:
            self._obra(carpeta)
            docs = listar_documentos(carpeta, carpeta)
        nombres = [d['nombre'] for d in docs]
        self.assertIn('hoja.pdf', nombres)
        self.assertNotIn('hoja.pdf.correcciones.json', nombres)

    def test_informe_sagarde_ia_sigue_sin_contar_como_antes(self):
        with tempfile.TemporaryDirectory() as carpeta:
            self._obra(carpeta)
            docs = listar_documentos(carpeta, carpeta)
        nombres = [d['nombre'] for d in docs]
        self.assertNotIn('panel.html', nombres)


class TestTareasDeFicha(unittest.TestCase):

    def _crear_ficha(self, carpeta, filas_tareas=None):
        ruta = os.path.join(carpeta, 'FICHA DE OBRA.xlsx')
        wb = Workbook()
        wb.active.title = 'Datos'
        if filas_tareas is not None:
            ws = wb.create_sheet('Tareas')
            ws.append(['Tarea', 'Origen', 'Fecha', 'Archivo', 'Estado'])
            for fila in filas_tareas:
                ws.append(fila)
        wb.save(ruta)
        return ruta

    def test_lee_tareas_pendiente_y_hecha(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = self._crear_ficha(carpeta, [
                ['Revisar cuadro', 'Parte de obra', date(2026, 8, 21),
                 'parte-21-08.pdf', 'Pendiente'],
                ['Cerrar incidencia', 'Correo', date(2026, 8, 22),
                 'correo-22-08.msg', 'Hecho'],
            ])
            ficha = leer_ficha(ruta)

        self.assertEqual(ficha['tareas'], [
            {'Tarea': 'Revisar cuadro', 'Origen': 'Parte de obra',
             'Fecha': '21/08/2026', 'Archivo': 'parte-21-08.pdf',
             'Estado': 'Pendiente'},
            {'Tarea': 'Cerrar incidencia', 'Origen': 'Correo',
             'Fecha': '22/08/2026', 'Archivo': 'correo-22-08.msg',
             'Estado': 'Hecho'},
        ])

    def test_sin_hoja_tareas_devuelve_lista_vacia(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = self._crear_ficha(carpeta)
            ficha = leer_ficha(ruta)

        self.assertEqual(ficha['tareas'], [])

    def test_descarta_la_fila_de_ejemplo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = self._crear_ficha(carpeta, [
                ['(ejemplo: revisar documentacion)', 'Manual',
                 date(2026, 8, 23), 'ejemplo.pdf', 'Pendiente'],
            ])
            ficha = leer_ficha(ruta)

        self.assertEqual(ficha['tareas'], [])


if __name__ == '__main__':
    unittest.main()
