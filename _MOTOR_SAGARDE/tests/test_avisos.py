# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

MOTOR_DIR = Path(__file__).resolve().parent.parent
ROOT = MOTOR_DIR.parent
sys.path.insert(0, str(MOTOR_DIR))
sys.path.insert(0, str(MOTOR_DIR / "scripts"))

import avisos
import auditor_sagarde
import sagarde_portal


def _timestamp_hace(dias):
    return (datetime.now() - timedelta(days=dias)).timestamp()


class TestCaducidadAvisos(unittest.TestCase):

    def test_un_aviso_de_399_dias_sigue_visible(self):
        self.assertTrue(avisos.es_aviso_por_antiguedad(399, desde_dias=90))

    def test_un_aviso_de_400_dias_desaparece(self):
        self.assertFalse(avisos.es_aviso_por_antiguedad(400, desde_dias=90))

    def test_un_aviso_mas_antiguo_tampoco_reaparece(self):
        self.assertFalse(avisos.es_aviso_por_antiguedad(800, desde_dias=90))

    def test_el_umbral_inicial_sigue_siendo_estricto(self):
        self.assertFalse(avisos.es_aviso_por_antiguedad(90, desde_dias=90))
        self.assertTrue(avisos.es_aviso_por_antiguedad(91, desde_dias=90))


class TestPortalAvisos(unittest.TestCase):

    def _alertas_mantenimiento(self, dias):
        contrato = {
            "nombre": "CONTRATO PRUEBA",
            "sub_url": "CONTRATO/index.html",
            "ultima_ts": _timestamp_hace(dias),
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sagarde_portal, "ROOT", Path(tmp)):
                return sagarde_portal.construir_alertas(mant=[contrato])

    def test_el_portal_muestra_399_dias(self):
        alertas = self._alertas_mantenimiento(399)
        self.assertTrue(any("CONTRATO PRUEBA" in texto for _, texto in alertas))

    def test_el_portal_oculta_400_dias(self):
        alertas = self._alertas_mantenimiento(400)
        self.assertFalse(any("CONTRATO PRUEBA" in texto for _, texto in alertas))


class TestAuditoriaAvisos(unittest.TestCase):

    def _auditar_contrato(self, dias):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            contrato = raiz / "MANTENIMIENTOS" / "MANTENIMIENTO PRUEBA"
            contrato.mkdir(parents=True)
            parte = contrato / "parte.pdf"
            parte.write_bytes(b"prueba")
            ts = _timestamp_hace(dias)
            os.utime(parte, (ts, ts))
            with patch.object(auditor_sagarde, "ROOT", raiz):
                return auditor_sagarde.audit_mantenimientos()

    def test_la_auditoria_mantiene_399_dias(self):
        issues = self._auditar_contrato(399)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["dias_antiguedad"], 399)

    def test_la_auditoria_descarta_400_dias(self):
        self.assertEqual(self._auditar_contrato(400), [])


if __name__ == "__main__":
    unittest.main()
