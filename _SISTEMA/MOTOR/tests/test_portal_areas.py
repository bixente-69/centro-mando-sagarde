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
        (self.raiz / "VARIOS" / "BATERIAS DE CONDENSADORES").mkdir()
        (self.raiz / "VARIOS" / "BATERIAS DE CONDENSADORES" / "app_informes.html").write_text(
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
            self.assertIn("[hidden]{display:none!important}", html)
            self.assertIn(".normalize('NFD')", html)
        self.assertIn("Biblioteca técnica", herramientas)
        self.assertIn(
            'href="BATERIAS%20DE%20CONDENSADORES/app_informes.html"',
            herramientas,
        )
        self.assertIn(
            'href="TIERRAS/app_informe_tierras.html"',
            herramientas,
        )
        self.assertNotIn("%2Fapp_informes.html", herramientas)
        self.assertNotIn("%2Fapp_informe_tierras.html", herramientas)
        self.assertIn("app_informe_tierras.html", herramientas)
        self.assertNotIn("APPS SAGARDE", herramientas)
        self.assertNotIn("informe_nominas_sagarde", herramientas)
        self.assertIn("Archivo histórico", archivo)
        self.assertIn("2024 OBRA DEMO", archivo)
        self.assertIn("OBRAS%20CERRADAS/2024%20OBRA%20DEMO/", archivo)



class TestPaginaPersonalSagarde(unittest.TestCase):
    """La pagina del ranking de personal sale como acceso del portal (y solo ella)."""

    RUTA = "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/personal_sagarde.html"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self._root_original = portal.ROOT
        self._output_original = portal.OUTPUT
        portal.ROOT = self.raiz
        portal.OUTPUT = self.raiz / "index.html"
        self.addCleanup(self._restaurar_rutas)
        self.motor = self.raiz / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
        self.motor.mkdir(parents=True)
        (self.motor / "generador_revisiones.html").write_text("<html></html>", encoding="utf-8")
        (self.motor / "panel_borrador.html").write_text("<html></html>", encoding="utf-8")

    def _restaurar_rutas(self):
        portal.ROOT = self._root_original
        portal.OUTPUT = self._output_original

    def _con_pagina(self):
        (self.motor / "personal_sagarde.html").write_text("<html></html>", encoding="utf-8")

    def test_la_pagina_declarada_sale_como_aplicacion(self):
        self._con_pagina()
        apps = {a["path"]: a for a in portal.discover_apps()}

        self.assertIn(self.RUTA, apps)
        self.assertEqual("Personal Sagarde · ranking", apps[self.RUTA]["name"])
        self.assertEqual("SAGARDE OBRAS ABIERTAS", apps[self.RUTA]["area"])

    def test_sin_la_pagina_no_sale_nada_nuevo_y_el_resto_no_cambia(self):
        apps = {a["path"] for a in portal.discover_apps()}

        self.assertNotIn(self.RUTA, apps)
        # El generador de revisiones sigue saliendo y cualquier otro html de obras abiertas sigue fuera.
        self.assertEqual({"SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html"}, apps)

    def test_se_pinta_en_la_portada_y_en_el_indice_de_aplicaciones(self):
        self._con_pagina()
        apps = portal.discover_apps()
        html = portal.build_html([], apps, None, None, [], None, [])
        portal.generar_index_aplicaciones(apps)
        indice = (self.raiz / "APLICACIONES" / "index.html").read_text(encoding="utf-8")

        enlace = 'href="SAGARDE%20OBRAS%20ABIERTAS/_SISTEMA%20INFORME%20SAGARDE%20IA/personal_sagarde.html"'
        self.assertIn(enlace, html)
        self.assertIn("Personal Sagarde · ranking", html)
        self.assertIn("Personal Sagarde · ranking", indice)

    RUTA_APP = "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_personal.html"

    def test_la_app_de_la_tablet_sale_con_su_nombre_y_no_como_generador_personal(self):
        (self.motor / "generador_personal.html").write_text("<html></html>", encoding="utf-8")
        apps = {a["path"]: a for a in portal.discover_apps()}

        self.assertEqual("Personal en obra · jornada", apps[self.RUTA_APP]["name"])
        self.assertEqual("SAGARDE OBRAS ABIERTAS", apps[self.RUTA_APP]["area"])
        html = portal.build_html([], list(apps.values()), None, None, [], None, [])
        self.assertIn("Personal en obra · jornada", html)
        self.assertNotIn("generador personal", html.lower())

    def test_cada_pagina_declarada_existe_en_el_repositorio(self):
        # Una ruta declarada que ya no existe haria desaparecer el acceso sin ningun aviso.
        self.assertTrue(portal.APPS_OBRAS_ABIERTAS)
        for ruta in portal.APPS_OBRAS_ABIERTAS:
            self.assertTrue((self._root_original / ruta).is_file(), f"no existe {ruta}")

if __name__ == "__main__":
    unittest.main()
