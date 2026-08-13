# -*- coding: utf-8 -*-
"""Regresiones de las portadas Herramientas y Archivo historico."""

import sys
import tempfile
import unittest
from pathlib import Path


MOTOR_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MOTOR_DIR))

import sagarde_portal as portal


class TestPortadasAreas(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        self._root_original = portal.ROOT
        self._output_original = portal.OUTPUT
        portal.ROOT = self.raiz
        portal.OUTPUT = self.raiz / "index.html"
        self.addCleanup(self._restaurar_rutas)

        (self.raiz / "VARIOS" / "TIERRAS").mkdir(parents=True)
        (self.raiz / "VARIOS" / "TIERRAS" / "app_informe_tierras.html").write_text(
            "<html></html>", encoding="utf-8"
        )
        (self.raiz / "VARIOS" / "CATALOGOS").mkdir()
        (self.raiz / "VARIOS" / "CATALOGOS" / "catalogo.pdf").write_bytes(b"pdf")
        (self.raiz / "VARIOS" / "APPS SAGARDE").mkdir()
        (self.raiz / "VARIOS" / "APPS SAGARDE" / "informe_nominas_sagarde_2026.html").write_text(
            "privado", encoding="utf-8"
        )

        cerradas = self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS"
        (cerradas / "2024 OBRA DEMO").mkdir(parents=True)

    def _restaurar_rutas(self):
        portal.ROOT = self._root_original
        portal.OUTPUT = self._output_original

    def test_scan_area_usa_landing_profesional_aunque_aun_no_exista(self):
        herramientas = portal.scan_area(self.raiz / "VARIOS")
        archivo = portal.scan_area(self.raiz / "SAGARDE (OLD)")

        self.assertEqual("VARIOS/index.html", herramientas["url"])
        self.assertEqual("SAGARDE%20(OLD)/index.html", archivo["url"])

    def test_catalogo_y_descubrimiento_no_filtran_area_personal(self):
        catalogo = portal.escanear_herramientas()
        apps = portal.discover_apps()
        texto = repr(catalogo) + repr(apps)

        self.assertIn("TIERRAS", texto)
        self.assertIn("CATALOGOS", texto)
        self.assertNotIn("APPS SAGARDE", texto)
        self.assertNotIn("informe_nominas_sagarde", texto)

    def test_portada_principal_enlaza_las_dos_landings_en_una_sola_pasada(self):
        areas = [
            portal.scan_area(self.raiz / "VARIOS"),
            portal.scan_area(self.raiz / "SAGARDE (OLD)"),
        ]
        html = portal.build_html(areas, [], None, None, [], None, [])

        self.assertIn('href="VARIOS/index.html"', html)
        self.assertIn('href="SAGARDE%20(OLD)/index.html"', html)

    def test_genera_ambas_paginas_con_identidad_sagarde_y_busqueda(self):
        catalogo = portal.escanear_herramientas()
        apps = portal.discover_apps()
        obras = portal.escanear_obras_cerradas()

        portal.generar_index_herramientas(catalogo, apps)
        portal.generar_index_archivo_historico(obras)

        herramientas = (self.raiz / "VARIOS" / "index.html").read_text(encoding="utf-8")
        archivo = (self.raiz / "SAGARDE (OLD)" / "index.html").read_text(encoding="utf-8")

        for html in (herramientas, archivo):
            self.assertIn("class=\"top\"", html)
            self.assertIn("class=\"search\"", html)
            self.assertIn("Centro de mando", html)
        self.assertIn("Biblioteca técnica", herramientas)
        self.assertIn("app_informe_tierras.html", herramientas)
        self.assertNotIn("APPS SAGARDE", herramientas)
        self.assertNotIn("informe_nominas_sagarde", herramientas)
        self.assertIn("Archivo histórico", archivo)
        self.assertIn("2024 OBRA DEMO", archivo)
        self.assertIn("OBRAS%20CERRADAS/2024%20OBRA%20DEMO/", archivo)


if __name__ == "__main__":
    unittest.main()
