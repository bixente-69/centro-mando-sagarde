# -*- coding: utf-8 -*-
"""Regresiones del cache de extraccion cruda de hojas PDF."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle


MOTOR = Path(__file__).resolve().parent.parent
ADAPTADORES = MOTOR / "adaptadores"
sys.path.insert(0, str(MOTOR))
sys.path.insert(0, str(ADAPTADORES))

import cache_pdf
import lector_hoja_tajos_pdf as lector
import adaptador_bolueta


PDFS_BOLUETA = sorted(
    Path(adaptador_bolueta.CARPETA_REVISIONES).glob("*BOLUETA*.pdf")
)


def _crear_pdf(ruta, marca="X"):
    """Crea una hoja minima con una tabla vectorial extraible."""
    doc = canvas.Canvas(str(ruta), pagesize=A4, invariant=1)
    tabla = Table(
        [
            ["BOLUETA - PLANTA PB", "A", "B"],
            ["Tajo", "A", "B"],
            ["Mecanizado", marca, ""],
        ],
        colWidths=[220, 70, 70],
        rowHeights=[24, 24, 24],
    )
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    tabla.wrapOn(doc, 360, 72)
    tabla.drawOn(doc, 72, 700)
    doc.save()


class TestCacheExtraccionPdf(unittest.TestCase):

    def setUp(self):
        cache_pdf._reiniciar_estado_para_pruebas()

    def _extraer(self, pdf, cache_dir):
        with mock.patch.object(cache_pdf, "CARPETA_CACHE_PDF", Path(cache_dir)):
            return lector.extraer_pdf_crudo(str(pdf))

    def test_frio_y_caliente_devuelven_exactamente_lo_mismo_y_no_reabre_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pdf = raiz / "hoja.pdf"
            cache_dir = raiz / "cache"
            _crear_pdf(pdf)

            abrir_real = lector.pdfplumber.open
            with mock.patch.object(lector.pdfplumber, "open", wraps=abrir_real) as abrir:
                frio = self._extraer(pdf, cache_dir)
                caliente = self._extraer(pdf, cache_dir)

            self.assertEqual(frio, caliente)
            self.assertEqual(abrir.call_count, 1)

    def test_cambiar_contenido_del_pdf_invalida(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pdf = raiz / "hoja.pdf"
            cache_dir = raiz / "cache"
            abrir_real = lector.pdfplumber.open

            with mock.patch.object(lector.pdfplumber, "open", wraps=abrir_real) as abrir:
                _crear_pdf(pdf, "X")
                primero = self._extraer(pdf, cache_dir)
                _crear_pdf(pdf, "M")
                segundo = self._extraer(pdf, cache_dir)

            self.assertNotEqual(primero, segundo)
            self.assertEqual(abrir.call_count, 2)
            self.assertEqual(len(list(cache_dir.glob("*.json"))), 2)

    def test_cambiar_huella_del_codigo_de_extraccion_invalida(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pdf = raiz / "hoja.pdf"
            cache_dir = raiz / "cache"
            _crear_pdf(pdf)
            abrir_real = lector.pdfplumber.open

            with mock.patch.object(lector.pdfplumber, "open", wraps=abrir_real) as abrir:
                with mock.patch.object(
                    cache_pdf, "huella_codigo_extraccion", return_value="a" * 64
                ):
                    primero = self._extraer(pdf, cache_dir)
                with mock.patch.object(
                    cache_pdf, "huella_codigo_extraccion", return_value="b" * 64
                ):
                    segundo = self._extraer(pdf, cache_dir)

            self.assertEqual(primero, segundo)
            self.assertEqual(abrir.call_count, 2)
            self.assertEqual(len(list(cache_dir.glob("*.json"))), 2)

    def test_cache_corrupta_se_ignora_reextrae_y_avisa(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pdf = raiz / "hoja.pdf"
            cache_dir = raiz / "cache"
            _crear_pdf(pdf)
            esperado = self._extraer(pdf, cache_dir)
            fichero_cache = next(cache_dir.glob("*.json"))
            fichero_cache.write_text("{esto no es json", encoding="utf-8")

            salida = io.StringIO()
            abrir_real = lector.pdfplumber.open
            with contextlib.redirect_stdout(salida):
                with mock.patch.object(lector.pdfplumber, "open", wraps=abrir_real) as abrir:
                    obtenido = self._extraer(pdf, cache_dir)

            self.assertEqual(obtenido, esperado)
            self.assertEqual(abrir.call_count, 1)
            self.assertIn("cache PDF corrupta", salida.getvalue())

    def test_variable_sin_cache_no_lee_ni_escribe(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            pdf = raiz / "hoja.pdf"
            cache_dir = raiz / "cache"
            _crear_pdf(pdf)
            esperado = self._extraer(pdf, cache_dir)
            antes = {p.name: p.read_bytes() for p in cache_dir.glob("*.json")}
            abrir_real = lector.pdfplumber.open

            with mock.patch.dict(os.environ, {"SAGARDE_SIN_CACHE_PDF": "1"}):
                with mock.patch.object(lector.pdfplumber, "open", wraps=abrir_real) as abrir:
                    obtenido = self._extraer(pdf, cache_dir)

            despues = {p.name: p.read_bytes() for p in cache_dir.glob("*.json")}
            self.assertEqual(obtenido, esperado)
            self.assertEqual(abrir.call_count, 1)
            self.assertEqual(despues, antes)

    @unittest.skipUnless(PDFS_BOLUETA, "no existe una hoja PDF real de Bolueta")
    def test_bolueta_frio_y_caliente_iguales_y_reinterpreta_ambos(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp) / "cache"
            portal_real = adaptador_bolueta._portal_id_pdf
            tajo_real = adaptador_bolueta._identificar_tajo_pdf

            with mock.patch.object(cache_pdf, "CARPETA_CACHE_PDF", cache_dir):
                with mock.patch.object(
                    adaptador_bolueta, "_portal_id_pdf", wraps=portal_real
                ) as identificar_portal:
                    with mock.patch.object(
                        adaptador_bolueta, "_identificar_tajo_pdf", wraps=tajo_real
                    ) as identificar_tajo:
                        frio = adaptador_bolueta.cargar_historial()
                        self.assertGreater(identificar_portal.call_count, 0)
                        self.assertGreater(identificar_tajo.call_count, 0)

                        identificar_portal.reset_mock()
                        identificar_tajo.reset_mock()
                        with mock.patch.object(
                            lector.pdfplumber,
                            "open",
                            side_effect=AssertionError("el PDF caliente no debe reabrirse"),
                        ):
                            caliente = adaptador_bolueta.cargar_historial()

                        self.assertGreater(identificar_portal.call_count, 0)
                        self.assertGreater(identificar_tajo.call_count, 0)

            self.assertEqual(caliente, frio)


if __name__ == "__main__":
    unittest.main()
