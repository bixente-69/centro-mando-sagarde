# -*- coding: utf-8 -*-
"""OBRA PRUEBA dada de baja (decision 7 de Bixente, 04/11/2026).

Era una obra de ensayo. «Dar de baja» tiene tres piezas que tienen que ir juntas: si queda
una sola, el entorno sigue creyendo que existe o muestra una obra fantasma:
- el registro: si sigue, el motor la procesa y la cuenta en el inicio;
- su adaptador: si queda suelto es codigo huerfano;
- su carpeta: `carpetas_obra()` recorre el disco y la mostraria como «pendiente de alta».
"""
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SISTEMA = os.path.dirname(AQUI)
OBRAS_ABIERTAS = os.path.dirname(SISTEMA)
if SISTEMA not in sys.path:
    sys.path.insert(0, SISTEMA)

import registro_obras  # noqa: E402


class ObraPruebaDadaDeBaja(unittest.TestCase):
    def test_ya_no_esta_en_el_registro(self):
        self.assertNotIn("prueba", [o["id"] for o in registro_obras.OBRAS])
        self.assertFalse([o for o in registro_obras.OBRAS if "PRUEBA" in o["nombre"].upper()])

    def test_ya_no_queda_su_adaptador(self):
        self.assertFalse(os.path.exists(os.path.join(SISTEMA, "adaptadores", "adaptador_prueba.py")))

    def test_ya_no_queda_su_carpeta_versionada(self):
        import subprocess
        out = subprocess.run(["git", "ls-files", "--", "2026 OBRA PRUEBA"],
                             capture_output=True, text=True, cwd=OBRAS_ABIERTAS)
        if out.returncode != 0:
            self.skipTest("no es un clon de git: no se puede comprobar lo versionado")
        self.assertEqual(out.stdout.strip(), "")

    def test_cada_obra_registrada_tiene_su_carpeta(self):
        """El registro no puede declarar una obra cuya carpeta no existe (obra fantasma)."""
        faltan = [o["nombre"] for o in registro_obras.OBRAS
                  if not os.path.isdir(os.path.join(OBRAS_ABIERTAS, o["carpeta_obra"]))]
        self.assertEqual(faltan, [])


if __name__ == "__main__":
    unittest.main()
