# -*- coding: utf-8 -*-
"""El inicio muestra lo que espera sin aplicar en REVISIONES (decision 4, 04/11/2026)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MOTOR_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MOTOR_DIR))

import avisos  # noqa: E402
import sagarde_portal as portal  # noqa: E402


def issue(codigo, obra, n, ficheros, nivel="warning"):
    return {"nivel": nivel, "area": "Obras Abiertas", "obra": obra, "codigo": codigo,
            "n": n, "ficheros": ficheros, "mensaje": "m", "solucion": "s"}


class PendientesEnElInicio(unittest.TestCase):
    def _alertas(self, issues):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "_SISTEMA" / "MOTOR").mkdir(parents=True)
            (raiz / "_SISTEMA" / "MOTOR" / "auditoria_diagnostico.json").write_text(
                json.dumps({"issues": issues}), encoding="utf-8")
            with patch.object(portal, "ROOT", raiz):
                return portal.construir_alertas(None, None, [])

    def test_hojas_y_controles_salen_con_obra_y_cantidad(self):
        alertas = self._alertas([
            issue(avisos.CODIGO_HOJAS_SIN_APLICAR, "2026 OLABEAGA BILBAO", 1, ["a.html"]),
            issue(avisos.CODIGO_CONTROLES_SIN_APLICAR, "2026 OLABEAGA BILBAO", 2, ["c1.json", "c2.json"]),
            issue(avisos.CODIGO_HOJAS_SIN_APLICAR, "2025 GERNIKA 32V", 2, ["g1.html", "g2.html"]),
        ])
        textos = [t for _, t in alertas if "sin aplicar" in t.lower()]
        self.assertEqual(len(textos), 1)
        t = textos[0]
        self.assertIn("2026 OLABEAGA BILBAO", t)
        self.assertIn("1 hoja", t)
        self.assertIn("2 controles horarios", t)
        self.assertIn("2025 GERNIKA 32V", t)
        self.assertIn("2 hojas", t)

    def test_no_se_cuentan_dos_veces_como_aviso_de_formato(self):
        alertas = self._alertas([issue(avisos.CODIGO_HOJAS_SIN_APLICAR, "X", 1, ["a.html"])])
        self.assertFalse([t for _, t in alertas if "Salud de Datos" in t])

    def test_un_aviso_de_formato_de_verdad_sigue_saliendo(self):
        alertas = self._alertas([
            issue("NOMBRE_FECHA_INVALIDA", "OBRA Y", 0, []),
            issue(avisos.CODIGO_HOJAS_SIN_APLICAR, "X", 1, ["a.html"]),
        ])
        salud = [t for _, t in alertas if "Salud de Datos" in t]
        self.assertEqual(len(salud), 1)
        self.assertIn("1 aviso(s) de formato", salud[0])

    def test_si_no_se_pudo_comprobar_se_dice(self):
        alertas = self._alertas([issue(avisos.CODIGO_PENDIENTES_NO_COMPROBADO, "OBRA Z", 0, [])])
        textos = [t for _, t in alertas if "no se pudo comprobar" in t.lower()]
        self.assertEqual(len(textos), 1)
        self.assertIn("OBRA Z", textos[0])

    def test_sin_pendientes_no_hay_aviso(self):
        self.assertFalse([t for _, t in self._alertas([]) if "sin aplicar" in t.lower()])

    def test_los_enlaces_a_hojas_no_se_inyectan(self):
        alertas = self._alertas([issue(avisos.CODIGO_HOJAS_SIN_APLICAR, "<b>X</b>", 1, ["<i>a</i>.html"])])
        t = " ".join(txt for _, txt in alertas)
        self.assertNotIn("<i>a</i>", t)


if __name__ == "__main__":
    unittest.main()
