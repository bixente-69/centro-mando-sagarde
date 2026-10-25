# -*- coding: utf-8 -*-
"""personal_calculo.js (P2 de «Personal en obra»): el cálculo que comparten la pestaña, el informe,
la tablet y el ranking. Lo prueba un script de node (tests/verificar_personal_calculo.js, con las
cifras escritas a mano y repetido en tres zonas horarias). Sin node la prueba se SALTA y lo dice:
sin esa prueba nadie comprueba el cálculo que sale en pantalla."""
import shutil
import subprocess
import unittest
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_MOTOR = _TESTS.parent  # _SISTEMA INFORME SAGARDE IA
_NODE = shutil.which("node")


@unittest.skipUnless(_NODE, "falta node en el PATH: NO se ha probado personal_calculo.js")
class TestPersonalCalculo(unittest.TestCase):
    def test_verificador_de_node(self):
        p = subprocess.run([_NODE, str(_TESTS / "verificar_personal_calculo.js")], cwd=str(_MOTOR),
                           capture_output=True, timeout=300)
        salida = (p.stdout + p.stderr).decode("utf-8", "replace")
        self.assertEqual(0, p.returncode, "\n".join(salida.splitlines()[-25:]))
        self.assertNotIn("FALLO", salida)


if __name__ == "__main__":
    unittest.main()
