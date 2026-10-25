# -*- coding: utf-8 -*-
"""generador_personal.html (P3 de «Personal en obra»): la app de la tablet, en un navegador de verdad.

Lanza tests/verificar_generador_personal.py (Playwright, Chromium): ≈ 7 minutos, con una fecha fija y
datos inventados. Recorre las escenas de la app (anotar, horarios propios, jornadas, informe, sin red,
datos dañados…) y valida el lote que exporta con personal_obra.py.

Se SALTA, diciendo por qué, si no hay Playwright con Chromium. Para saltarla a propósito (por ejemplo, en
una pasada rápida de la suite): SAGARDE_SIN_NAVEGADOR=1. No probada en un Safari de iPad real: eso solo
se comprueba en la tablet."""
import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_HAY_PLAYWRIGHT = importlib.util.find_spec("playwright") is not None


def _chromium_disponible():
    """(True, '') si Playwright puede abrir Chromium; si no, (False, motivo)."""
    if not _HAY_PLAYWRIGHT:
        return False, "falta Playwright (pip install playwright && playwright install chromium)"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch().close()
        return True, ""
    except Exception as exc:  # noqa: BLE001 - cualquier fallo de arranque es un motivo para saltar
        return False, f"Playwright no puede abrir Chromium ({type(exc).__name__})"


_SALTAR_A_PROPOSITO = os.environ.get("SAGARDE_SIN_NAVEGADOR") == "1"
_OK, _MOTIVO = (False, "saltada a propósito (SAGARDE_SIN_NAVEGADOR=1)") if _SALTAR_A_PROPOSITO else _chromium_disponible()


@unittest.skipUnless(_OK, f"NO se han probado las pantallas de la tablet: {_MOTIVO}")
class TestGeneradorPersonalEnNavegador(unittest.TestCase):
    def test_escenas_completas(self):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", P3_RAPIDO="1")
        p = subprocess.run([sys.executable, str(_TESTS / "verificar_generador_personal.py")], cwd=str(_TESTS),
                           capture_output=True, env=env, timeout=1800)
        salida = (p.stdout + p.stderr).decode("utf-8", "replace")
        self.assertEqual(0, p.returncode, "\n".join(salida.splitlines()[-30:]))


if __name__ == "__main__":
    unittest.main()
