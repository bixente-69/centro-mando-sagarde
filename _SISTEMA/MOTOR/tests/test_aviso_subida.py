# -*- coding: utf-8 -*-
"""Aviso de antigüedad de la ultima subida del portal (decisiones 3 y 4, 04/11/2026).

Plazos de Bixente: amarillo a mas de 8 dias, rojo a mas de 14. Los numeros viven en
UN solo sitio (avisos.py) y el aviso que ve Bixente tiene que usarlos: aqui se ejecuta
de verdad el JavaScript de la pagina (Node) con fechas fijas, no se mira solo que el
texto exista.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MOTOR_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MOTOR_DIR))

import avisos  # noqa: E402
import sagarde_portal as portal  # noqa: E402

GENERADO_TS = 1_793_000_000.0  # fecha fija cualquiera
DIA = 86400


class NivelSubida(unittest.TestCase):
    def test_umbrales_de_bixente(self):
        self.assertEqual((avisos.DIAS_SUBIDA_AMARILLO, avisos.DIAS_SUBIDA_ROJO), (8, 14))

    def test_limites(self):
        n = avisos.nivel_subida
        self.assertIsNone(n(0))
        self.assertIsNone(n(8))        # 8 dias todavia es normal
        self.assertEqual(n(9), "warn")
        self.assertEqual(n(14), "warn")  # 14 todavia amarillo: rojo es MAS de 14
        self.assertEqual(n(15), "bad")

    def test_sin_fecha_no_se_inventa_un_nivel(self):
        self.assertIsNone(avisos.nivel_subida(None))


@unittest.skipUnless(shutil.which("node"), "hace falta Node para ejecutar el JavaScript de la pagina")
class AvisoEnLaPagina(unittest.TestCase):
    def _ejecutar(self, dias_despues, prefijo="alerta"):
        """Ejecuta el <script> del bloque con 'hoy' = generacion + N dias (a mediodia)."""
        bloque = portal.bloque_aviso_subida(GENERADO_TS, "01/01/2027 10:00", prefijo)
        script = bloque.split("<script>")[1].split("</script>")[0]
        ahora_ms = (GENERADO_TS + dias_despues * DIA) * 1000
        harness = """
const REAL = Date;
const AHORA = %d;
global.Date = class extends REAL { constructor(...a){ if(a.length===0) super(AHORA); else super(...a);} static now(){return AHORA;} };
const attrs = %s;
const el = { hidden: true, className: '', textContent: '', getAttribute(k){ return attrs[k]; } };
global.document = { getElementById(id){ return id === 'aviso-subida' ? el : null; } };
%s
console.log(JSON.stringify({hidden: el.hidden, cls: el.className, txt: el.textContent}));
""" % (ahora_ms, json.dumps(self._atributos(bloque)), script)
        out = subprocess.run(["node", "-e", harness], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    @staticmethod
    def _atributos(bloque):
        import re
        return dict(re.findall(r'(data-[a-z-]+)="([^"]*)"', bloque.split("<script>")[0]))

    def test_hasta_8_dias_no_se_muestra(self):
        for d in (0, 3, 8):
            self.assertTrue(self._ejecutar(d)["hidden"], f"a {d} dias no debe avisar")

    def test_9_dias_amarillo(self):
        r = self._ejecutar(9)
        self.assertFalse(r["hidden"])
        self.assertIn("warn", r["cls"])
        self.assertIn("9 d", r["txt"])

    def test_15_dias_rojo(self):
        r = self._ejecutar(15)
        self.assertFalse(r["hidden"])
        self.assertIn("bad", r["cls"])

    def test_14_dias_sigue_amarillo(self):
        self.assertIn("warn", self._ejecutar(14)["cls"])

    def test_el_estilo_del_movil_usa_su_propio_prefijo(self):
        self.assertIn("al warn", self._ejecutar(9, prefijo="al")["cls"])

    def test_los_umbrales_de_la_pagina_son_los_de_avisos(self):
        original = (avisos.DIAS_SUBIDA_AMARILLO, avisos.DIAS_SUBIDA_ROJO)
        try:
            avisos.DIAS_SUBIDA_AMARILLO, avisos.DIAS_SUBIDA_ROJO = 2, 4
            self.assertFalse(self._ejecutar(3)["hidden"])
            self.assertIn("bad", self._ejecutar(5)["cls"])
        finally:
            avisos.DIAS_SUBIDA_AMARILLO, avisos.DIAS_SUBIDA_ROJO = original


class AvisoEstaEnLasPortadas(unittest.TestCase):
    def test_el_inicio_de_escritorio_lleva_el_aviso(self):
        html_ = portal.build_html([], [], None, None, [], None, [])
        self.assertIn('id="aviso-subida"', html_)
        self.assertIn(f'data-amarillo="{avisos.DIAS_SUBIDA_AMARILLO}"', html_)

    def test_el_aviso_se_suma_a_los_demas_no_los_sustituye(self):
        ro = {"generado": "x", "totales": {"n_obras": 1, "n_con_panel": 1, "bloqueos_totales": 3,
                                           "avance_medio_ponderado": 50.0},
              "obras": [{"nombre": "OBRA X", "carpeta": "X", "con_panel": True, "panel_actualizado": True,
                         "pct_ponderado": 50.0, "n_bloqueos": 3, "href": "x/panel.html"}]}
        html_ = portal.build_html([], [], ro, None, [], None, [])
        self.assertIn('id="aviso-subida"', html_)
        self.assertIn("3 bloqueo(s) detectado(s)", html_)
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import patch
            with patch.object(portal, "ROOT", Path(tmp)):
                portal.generar_portal_movil(ro, None, [], [])
            movil = (Path(tmp) / "_SISTEMA" / "PORTAL SAGARDE.html").read_text(encoding="utf-8")
        self.assertIn('id="aviso-subida"', movil)
        self.assertIn("3 bloqueo(s) detectado(s)", movil)

    def test_el_portal_movil_lleva_el_aviso(self):
        with tempfile.TemporaryDirectory() as tmp:
            from unittest.mock import patch
            with patch.object(portal, "ROOT", Path(tmp)):
                portal.generar_portal_movil(None, None, [], [])
            html_ = (Path(tmp) / "_SISTEMA" / "PORTAL SAGARDE.html").read_text(encoding="utf-8")
        self.assertIn('id="aviso-subida"', html_)


if __name__ == "__main__":
    unittest.main()
