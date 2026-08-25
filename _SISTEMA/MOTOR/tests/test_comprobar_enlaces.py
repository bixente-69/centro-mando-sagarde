# -*- coding: utf-8 -*-
"""Enlaces internos rotos en el portal publicado de Sagarde.

Complementa el chequeo de rutas muertas de actualizar_mapa_mental.py: aquel
comprueba la prosa del mapa mental, este comprueba el HTML publicado de
verdad. Misma familia de fallo que el resto del proyecto: algo declarado
(un href) que nadie vuelve a mirar tras regenerarse.
"""
import sys
import tempfile
import unittest
from pathlib import Path

MOTOR_DIR = Path(__file__).resolve().parent.parent
ROOT = MOTOR_DIR.parent.parent
sys.path.insert(0, str(MOTOR_DIR / "scripts"))

import comprobar_enlaces as ce

OBRA_MOTOR_DIR = ROOT / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
sys.path.insert(0, str(OBRA_MOTOR_DIR))

import registro_obras


class TestExtraerEnlaces(unittest.TestCase):
    def test_extrae_href_y_src_con_comillas_dobles_y_simples(self):
        html = '<a href="a.html">x</a><img src=\'b.png\'>'
        self.assertEqual([("a.html", 1), ("b.png", 1)], ce.extraer_enlaces(html))

    def test_ignora_atributos_que_no_son_href_ni_src(self):
        html = '<a href="a.html" data-search="a.html buscado">x</a>'
        self.assertEqual([("a.html", 1)], ce.extraer_enlaces(html))

    def test_numero_de_linea_correcto_en_html_multilinea(self):
        html = "<html>\n<body>\n<a href=\"c.html\">x</a>\n</body>\n</html>"
        self.assertEqual([("c.html", 3)], ce.extraer_enlaces(html))


class TestEsEnlaceInterno(unittest.TestCase):
    def test_relativo_es_interno(self):
        self.assertTrue(ce.es_enlace_interno("POST-VENTAS/index.html"))

    def test_http_y_https_no_son_internos(self):
        self.assertFalse(ce.es_enlace_interno("https://cdn.jsdelivr.net/chart.js"))
        self.assertFalse(ce.es_enlace_interno("http://example.com"))

    def test_mailto_tel_javascript_no_son_internos(self):
        self.assertFalse(ce.es_enlace_interno("mailto:a@b.com"))
        self.assertFalse(ce.es_enlace_interno("tel:+34600000000"))
        self.assertFalse(ce.es_enlace_interno("javascript:void(0)"))

    def test_ancla_no_es_interna(self):
        self.assertFalse(ce.es_enlace_interno("#kpis"))


class TestResolverRuta(unittest.TestCase):
    def test_decodifica_espacios_url_encoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            html = raiz / "index.html"
            html.write_text("<html></html>", encoding="utf-8")
            ruta = ce.resolver_ruta(
                "SAGARDE%20OBRAS%20ABIERTAS/index.html", html)
            self.assertEqual(
                raiz / "SAGARDE OBRAS ABIERTAS" / "index.html", ruta)

    def test_resuelve_relativo_a_la_carpeta_del_html_no_al_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "POST-VENTAS").mkdir()
            html = raiz / "POST-VENTAS" / "index.html"
            html.write_text("<html></html>", encoding="utf-8")
            ruta = ce.resolver_ruta("../APLICACIONES/index.html", html)
            self.assertEqual(raiz / "APLICACIONES" / "index.html", ruta)


def _crear_html(raiz, ruta_rel, contenido):
    archivo = raiz / ruta_rel
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(contenido, encoding="utf-8")
    return archivo


class TestEnlacesRotosDePagina(unittest.TestCase):
    def test_detecta_un_enlace_roto(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            html = _crear_html(
                raiz, "index.html", '<a href="POST-VENTAS/index.html">x</a>')
            rotos = ce.enlaces_rotos_de_pagina(html, raiz)
            self.assertEqual(1, len(rotos))
            self.assertEqual("POST-VENTAS/index.html", rotos[0]["destino"])
            self.assertEqual(1, rotos[0]["linea"])

    def test_no_marca_un_enlace_correcto(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            _crear_html(raiz, "POST-VENTAS/index.html", "<html></html>")
            html = _crear_html(
                raiz, "index.html", '<a href="POST-VENTAS/index.html">x</a>')
            self.assertEqual([], ce.enlaces_rotos_de_pagina(html, raiz))

    def test_enlace_correcto_con_espacios_codificados_no_se_marca(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            _crear_html(raiz, "SAGARDE OBRAS ABIERTAS/index.html", "<html></html>")
            html = _crear_html(
                raiz, "index.html",
                '<a href="SAGARDE%20OBRAS%20ABIERTAS/index.html">x</a>')
            self.assertEqual([], ce.enlaces_rotos_de_pagina(html, raiz))

    def test_ignora_enlaces_externos_y_anclas(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            html = _crear_html(
                raiz, "index.html",
                '<a href="https://cdn.jsdelivr.net/chart.js">x</a>'
                '<a href="#kpis">y</a>')
            self.assertEqual([], ce.enlaces_rotos_de_pagina(html, raiz))

    def test_enlace_que_escapa_de_raiz_se_marca_como_roto(self):
        # Un enlace con suficientes '../' puede resolver a un archivo real
        # que existe fuera del sitio (el repo vive dentro de OneDrive, con
        # miles de archivos alrededor). Que exista en disco no basta: si
        # queda fuera de raiz, en el portal publicado no lleva a nada.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raiz = base / "repo"
            raiz.mkdir()
            (base / "fuera.html").write_text("<html></html>", encoding="utf-8")
            html = _crear_html(raiz, "index.html", '<a href="../fuera.html">x</a>')
            rotos = ce.enlaces_rotos_de_pagina(html, raiz)
            self.assertEqual(1, len(rotos))
            self.assertEqual("../fuera.html", rotos[0]["destino"])


class TestPaginasAComprobar(unittest.TestCase):
    def test_incluye_las_seis_paginas_fijas(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            paginas = ce.paginas_a_comprobar(raiz)
            relativas = {str(p.relative_to(raiz)).replace("\\", "/") for p in paginas}
            for fija in ce.PAGINAS_FIJAS:
                self.assertIn(fija, relativas)

    def test_incluye_el_panel_de_cada_obra_del_registro(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            paginas = ce.paginas_a_comprobar(raiz)
            relativas = {str(p.relative_to(raiz)).replace("\\", "/") for p in paginas}
            for obra in registro_obras.OBRAS:
                esperada = (
                    f"SAGARDE OBRAS ABIERTAS/{obra['carpeta_obra']}"
                    f"/INFORME SAGARDE IA/panel.html")
                self.assertIn(esperada, relativas)

    def test_no_hay_paginas_duplicadas(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            paginas = ce.paginas_a_comprobar(raiz)
            self.assertEqual(len(paginas), len(set(paginas)))


class TestComprobarEnlaces(unittest.TestCase):
    def test_devuelve_pagina_ausente_si_falta_una_pagina_fija(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            resultado = ce.comprobar_enlaces(raiz)
            self.assertGreaterEqual(len(resultado["ausentes"]), 1)

    def test_devuelve_vacio_cuando_todo_resuelve(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            for pagina in ce.paginas_a_comprobar(raiz):
                pagina.parent.mkdir(parents=True, exist_ok=True)
                pagina.write_text("<html></html>", encoding="utf-8")
            resultado = ce.comprobar_enlaces(raiz)
            self.assertEqual([], resultado["ausentes"])
            self.assertEqual({}, resultado["rotos"])

    def test_devuelve_rotos_si_una_pagina_existente_enlaza_a_la_nada(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            for pagina in ce.paginas_a_comprobar(raiz):
                pagina.parent.mkdir(parents=True, exist_ok=True)
                pagina.write_text("<html></html>", encoding="utf-8")
            raiz_index = raiz / "index.html"
            raiz_index.write_text('<a href="no_existe.html">x</a>', encoding="utf-8")
            resultado = ce.comprobar_enlaces(raiz)
            self.assertEqual([], resultado["ausentes"])
            self.assertIn(raiz_index, resultado["rotos"])


class TestMain(unittest.TestCase):
    def setUp(self):
        self._root_original = ce.ROOT
        self.addCleanup(self._restaurar)

    def _restaurar(self):
        ce.ROOT = self._root_original

    def _preparar_arbol_completo(self, raiz):
        for pagina in ce.paginas_a_comprobar(raiz):
            pagina.parent.mkdir(parents=True, exist_ok=True)
            pagina.write_text("<html></html>", encoding="utf-8")

    def test_codigo_0_cuando_todo_resuelve(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            self._preparar_arbol_completo(raiz)
            ce.ROOT = raiz
            self.assertEqual(0, ce.main([]))

    def test_codigo_1_cuando_hay_enlaces_rotos(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            self._preparar_arbol_completo(raiz)
            (raiz / "index.html").write_text(
                '<a href="no_existe.html">x</a>', encoding="utf-8")
            ce.ROOT = raiz
            self.assertEqual(1, ce.main([]))

    def test_codigo_2_cuando_falta_una_pagina_fija(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            ce.ROOT = raiz
            self.assertEqual(2, ce.main([]))


if __name__ == "__main__":
    unittest.main()
