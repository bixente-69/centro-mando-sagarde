# -*- coding: utf-8 -*-
"""El aviso «Sin aplicar en REVISIONES» no puede quedar atrasado (defecto del 05/11/2026, 06/11/2026 reparado).

Antes el auditor del paso 0 del .bat calculaba lo que esperaba sin aplicar, el paso 1 lo aplicaba y el portal pintaba el aviso
con lo calculado ANTES: un control que el propio .bat acababa de aplicar seguia saliendo como pendiente hasta la pasada
siguiente. Ahora, entre aplicar y pintar, `auditor_sagarde.py --solo-pendientes` vuelve a mirarlo y reescribe SOLO esa parte del
diagnostico. Datos INVENTADOS."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MOTOR_DIR = Path(__file__).resolve().parent.parent
RAIZ = MOTOR_DIR.parent.parent
sys.path.insert(0, str(MOTOR_DIR))
sys.path.insert(0, str(MOTOR_DIR / "scripts"))

import avisos  # noqa: E402
import auditor_sagarde as A  # noqa: E402
import sagarde_portal as portal  # noqa: E402


def issue(codigo, obra, n=1, ficheros=(), nivel="warning"):
    return {"nivel": nivel, "area": "Obras Abiertas", "obra": obra, "codigo": codigo, "n": n,
            "ficheros": list(ficheros), "mensaje": "m", "solucion": "s"}


ANTIGUOS = [
    issue(avisos.CODIGO_CONTROLES_SIN_APLICAR, "2026 OLABEAGA BILBAO", 1, ["c.json"]),
    issue(avisos.CODIGO_HOJAS_SIN_APLICAR, "2025 GERNIKA 32V", 2, ["g1.html", "g2.html"]),
    issue("NOMBRE_FECHA_INVALIDA", "OBRA Y", 0),
    issue("PERSONAL_ESQUEMA", "Personal", 0, nivel="error"),
]


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="refrescar_")
        self.ruta = Path(self._tmp.name) / "auditoria_diagnostico.json"
        self.ruta.write_text(json.dumps({"generado": "05/11/2026 13:50", "issues": ANTIGUOS,
                                         "totales": {"total_issues": 4}, "salud_score": 1}), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def refrescar(self, nuevos=None, error=None):
        def falso(*a, **k):
            if error:
                raise error
            return list(nuevos or [])
        with patch.object(A, "audit_pendientes_revisiones", falso):
            return A.refrescar_pendientes(self.ruta)

    def leer(self):
        return json.loads(self.ruta.read_text(encoding="utf-8"))

    def codigos(self):
        return [i["codigo"] for i in self.leer()["issues"]]


class TestRefrescar(Base):
    def test_lo_ya_aplicado_deja_de_salir(self):
        self.refrescar(nuevos=[])
        c = self.codigos()
        self.assertNotIn(avisos.CODIGO_CONTROLES_SIN_APLICAR, c)
        self.assertNotIn(avisos.CODIGO_HOJAS_SIN_APLICAR, c)

    def test_no_toca_lo_que_no_es_pendiente(self):
        self.refrescar(nuevos=[])
        c = self.codigos()
        self.assertIn("NOMBRE_FECHA_INVALIDA", c)
        self.assertIn("PERSONAL_ESQUEMA", c)

    def test_lo_que_sigue_sin_aplicar_sigue_avisando_y_no_se_duplica(self):
        nuevo = issue(avisos.CODIGO_CONTROLES_SIN_APLICAR, "2026 OLABEAGA BILBAO", 1, ["dudoso.json"])
        self.refrescar(nuevos=[nuevo])
        controles = [i for i in self.leer()["issues"] if i["codigo"] == avisos.CODIGO_CONTROLES_SIN_APLICAR]
        self.assertEqual(1, len(controles))
        self.assertEqual(["dudoso.json"], controles[0]["ficheros"], "sale lo de AHORA, no lo de antes")

    def test_un_fallo_al_comprobar_se_dice_no_se_queda_en_cero(self):
        self.refrescar(error=RuntimeError("se cayo"))
        issues = [i for i in self.leer()["issues"] if i["codigo"] == avisos.CODIGO_PENDIENTES_NO_COMPROBADO]
        self.assertEqual(1, len(issues))
        self.assertIn("se cayo", issues[0]["mensaje"])
        self.assertNotIn(avisos.CODIGO_CONTROLES_SIN_APLICAR, self.codigos())

    def test_totales_y_nota_salud_se_recalculan_igual_que_en_la_auditoria(self):
        self.refrescar(nuevos=[])
        d = self.leer()
        # quedan 1 error y 1 aviso: 100 - (1*30 + 1*15)
        self.assertEqual({"total_issues": 2, "errors": 1, "warnings": 1, "infos": 0}, d["totales"])
        self.assertEqual(55, d["salud_score"])
        self.assertEqual("05/11/2026 13:50", d["generado"], "la hora de la auditoria no se toca")
        self.assertIn("pendientes_refrescados", d)

    def test_sin_diagnostico_no_se_inventa_ninguno(self):
        self.ruta.unlink()
        self.assertIsNone(A.refrescar_pendientes(self.ruta))
        self.assertFalse(self.ruta.exists())

    def test_diagnostico_ilegible_no_se_traga(self):
        self.ruta.write_text("{ roto", encoding="utf-8")
        with self.assertRaises(ValueError):
            A.refrescar_pendientes(self.ruta)


class TestElPortalYaNoEnseñaElAvisoAtrasado(Base):
    def alertas(self):
        raiz = Path(self._tmp.name) / "raiz"
        (raiz / "_SISTEMA" / "MOTOR").mkdir(parents=True)
        (raiz / "_SISTEMA" / "MOTOR" / "auditoria_diagnostico.json").write_text(self.ruta.read_text(encoding="utf-8"), encoding="utf-8")
        with patch.object(portal, "ROOT", raiz):
            return [t for _, t in portal.construir_alertas(None, None, []) if "sin aplicar" in t.lower()]

    def test_antes_de_refrescar_sale_el_aviso_atrasado(self):
        self.assertEqual(1, len(self.alertas()), "es el defecto: el aviso describe lo de antes de aplicar")

    def test_despues_de_refrescar_con_todo_aplicado_no_sale(self):
        self.refrescar(nuevos=[])
        self.assertEqual([], self.alertas())

    def test_un_control_dudoso_que_el_bat_no_aplica_SI_sigue_saliendo(self):
        self.refrescar(nuevos=[issue(avisos.CODIGO_CONTROLES_SIN_APLICAR, "2026 OLABEAGA BILBAO", 1, ["dudoso.json"])])
        textos = self.alertas()
        self.assertEqual(1, len(textos))
        self.assertIn("2026 OLABEAGA BILBAO", textos[0])
        self.assertIn("1 control horario", textos[0])


class TestLaLineaDeComandos(Base):
    def test_solo_pendientes_no_frena_aunque_haya_errores(self):
        with patch.object(A, "DIAGNOSTICO_JSON", self.ruta), patch.object(A, "audit_pendientes_revisiones", lambda *a, **k: []):
            self.assertEqual(0, A.main(["--solo-pendientes"]), "el que frena la publicacion es el paso 0, no este")
        self.assertNotIn(avisos.CODIGO_CONTROLES_SIN_APLICAR, self.codigos())

    def test_si_no_se_puede_refrescar_sale_con_codigo_1_y_lo_dice(self):
        self.ruta.write_text("{ roto", encoding="utf-8")
        with patch.object(A, "DIAGNOSTICO_JSON", self.ruta):
            self.assertEqual(1, A.main(["--solo-pendientes"]))

    def test_sin_argumentos_sigue_siendo_la_auditoria_completa(self):
        with patch.object(A, "run_audit", lambda: {"totales": {"errors": 2}}):
            self.assertEqual(3, A.main([]))
        with patch.object(A, "run_audit", lambda: {"totales": {"errors": 0}}):
            self.assertEqual(0, A.main([]))


class TestElOrdenDelBat(unittest.TestCase):
    """Lo que de verdad arregla el defecto: el orden de los pasos."""

    def setUp(self):
        self.bat = (RAIZ / "Actualizar_Sagarde.bat").read_text(encoding="utf-8", errors="replace")

    def pos(self, trozo):
        i = self.bat.find(trozo)
        self.assertGreaterEqual(i, 0, f"falta en el .bat: {trozo}")
        return i

    def test_se_vuelve_a_mirar_despues_de_aplicar_y_antes_de_pintar_el_portal(self):
        aplicar = self.pos("generar_todos.py")
        refrescar = self.pos("auditor_sagarde.py\" --solo-pendientes")
        portal_ = self.pos("sagarde_portal.py")
        self.assertLess(aplicar, refrescar)
        self.assertLess(refrescar, portal_)

    def test_la_auditoria_completa_sigue_siendo_el_paso_cero(self):
        completa = [m.start() for m in re.finditer(r'auditor_sagarde\.py"\s*\r?\n', self.bat)]
        self.assertEqual(1, len(completa))
        self.assertLess(completa[0], self.pos("generar_todos.py"))

    def test_si_falla_el_refresco_no_se_para_pero_se_avisa(self):
        i = self.pos("--solo-pendientes")
        trozo = self.bat[i:self.pos("echo [3/6]")]   # solo el bloque del refresco: no se cuela el «if» del paso siguiente
        self.assertIn("if %errorlevel% neq 0 (", trozo, "el aviso sale cuando el refresco da un código distinto de 0")
        self.assertIn("AVISO", trozo)
        self.assertNotIn("exit /b", trozo.split("echo.")[0])


if __name__ == "__main__":
    unittest.main()
