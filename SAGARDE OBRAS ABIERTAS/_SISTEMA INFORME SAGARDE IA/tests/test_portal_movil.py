# -*- coding: utf-8 -*-
"""Regresion para generar_portal_movil().

Por que existe esta prueba: entre el 25/07/2026 y el 08/08/2026 la funcion
NO ESCRIBIA NADA. Calculaba los KPI y las alertas y terminaba, sin ningun
write_text. El 'PORTAL SAGARDE.html' que quedaba en disco era un resto
congelado del 25/07 que el portal seguia enlazando como si estuviera al dia:
dos semanas ensenando cifras viejas sin un solo error por pantalla.

Nadie se entero porque nada lo comprobaba. La funcion se llamaba, no fallaba
y no producia fichero. Estas pruebas cierran exactamente ese hueco: no miran
que la pagina "se vea bien", miran que SE ESCRIBE y que lleva dentro los
datos que se le pasaron.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(SISTEMA_DIR))
sys.path.insert(0, SISTEMA_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR'))

import sagarde_portal


def _datos():
    """Un juego minimo pero realista: 2 obras (una con panel), 1 contrato de
    post-venta, 1 mantenimiento y 1 obra cerrada."""
    ro = {
        "totales": {"n_obras": 2, "n_con_panel": 1, "avance_medio_ponderado": 80.1,
                    "bloqueos_totales": 3},
        "obras": [
            {"nombre": "2026 OBRA CON PANEL", "con_panel": True,
             "pct_ponderado": 80.1, "n_rev": 26, "n_docs": 326,
             "n_bloqueos": 3, "sin_cambios": False,
             "ultima_revision": "28/07/2026",
             "href": "SAGARDE OBRAS ABIERTAS/x/panel.html"},
            {"nombre": "2026 OBRA SIN PANEL", "con_panel": False},
        ],
    }
    rp = {"totales": {"n_contratos": 1},
          "contratos": [{"nombre": "CONTRATO PV", "href": "POST-VENTAS/X/",
                         "ultimo_archivo_ts": 1785357549.0}]}
    mant = [{"nombre": "CARDIVA", "url": "MANTENIMIENTOS/M/index.html",
             "sub_url": "M/index.html", "n_archivos": 496,
             "ultima_ts": 1785357549.0}]
    cerradas = [{"nombre": "2025 OBRA CERRADA", "url": "SAGARDE (OLD)/X/",
                 "sub_url": "X/", "ultima_ts": 1785357549.0}]
    return ro, rp, mant, cerradas


class TestPortalMovilSeEscribe(unittest.TestCase):

    def _generar(self, ro=None, rp=None, mant=None, cerradas=None):
        """Genera el portal movil en un directorio temporal y devuelve el HTML."""
        d_ro, d_rp, d_mant, d_cer = _datos()
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            with patch.object(sagarde_portal, "ROOT", raiz):
                sagarde_portal.generar_portal_movil(
                    ro if ro is not None else d_ro,
                    rp if rp is not None else d_rp,
                    mant if mant is not None else d_mant,
                    cerradas if cerradas is not None else d_cer)
            destino = raiz / "_SISTEMA" / "PORTAL SAGARDE.html"
            if not destino.is_file():
                return None
            return destino.read_text(encoding="utf-8")

    def test_escribe_el_fichero(self):
        # LA prueba que faltaba: que produce un fichero. Si generar_portal_movil
        # vuelve a quedarse sin write_text, esto falla.
        html = self._generar()
        self.assertIsNotNone(
            html, "generar_portal_movil() no ha escrito PORTAL SAGARDE.html")
        self.assertGreater(len(html), 1000, "El portal movil sale casi vacio.")

    def test_tiene_las_cinco_pestanas(self):
        html = self._generar()
        for tab in range(5):
            self.assertIn(f'id="tab{tab}"', html, f"Falta la pestana tab{tab}.")

    def test_los_datos_llegan_a_la_pagina(self):
        # No basta con que escriba algo: tiene que llevar lo que se le paso.
        html = self._generar()
        self.assertIn("2026 OBRA CON PANEL", html)
        self.assertIn("CONTRATO PV", html)
        self.assertIn("CARDIVA", html)
        self.assertIn("2025 OBRA CERRADA", html)
        self.assertIn("80%", html)          # pct_ponderado redondeado
        self.assertIn("3 bloqueo(s)", html)

    def test_la_obra_sin_panel_no_sale_en_obras(self):
        # Solo las obras con seguimiento IA tienen tarjeta.
        html = self._generar()
        self.assertNotIn("2026 OBRA SIN PANEL", html)

    def test_los_enlaces_suben_un_nivel(self):
        """El fichero vive en _SISTEMA/, asi que todo href relativo a la raiz
        necesita '../'. Sin esto la pagina se genera igual y no abre nada."""
        html = self._generar()
        self.assertIn('href="../SAGARDE OBRAS ABIERTAS/x/panel.html"', html)
        self.assertIn('src="../POST-VENTAS/logo_sagarde.jpg"', html)

    def test_aguanta_sin_datos(self):
        """Con ro/rp a None el .bat sigue teniendo que producir la pagina:
        que falten resumenes no puede dejar al movil sin portal."""
        html = self._generar(ro={}, rp={}, mant=[], cerradas=[])
        self.assertIsNotNone(html, "Sin datos no se ha escrito el portal.")
        self.assertIn('id="tab0"', html)


if __name__ == "__main__":
    unittest.main()
