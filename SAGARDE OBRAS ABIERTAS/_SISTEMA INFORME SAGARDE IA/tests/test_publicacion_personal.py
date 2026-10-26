# -*- coding: utf-8 -*-
"""Los ficheros de «Personal en obra» se publican DE VERDAD (y solo los declarados).

El `.gitignore` de este repositorio es una lista blanca (`*` ignora todo). Un tipo de fichero
nuevo que no tenga su línea se genera sin ningún error y nunca llega a la web: ya pasó con
`obras_revisiones.js`. Aquí se comprueba, para cada fichero de personal que el sistema declara:

1. `git check-ignore` dice que NO está ignorado y la regla que lo deja pasar es la suya
   (no un `!*.html` genérico);
2. `git add -A --dry-run` en un repositorio de prueba con el `.gitignore` real lo incluye;
3. un fichero de personal que NO está declarado se queda fuera.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent  # _SISTEMA INFORME SAGARDE IA
_HAY_GIT = shutil.which("git") is not None


def _raiz_repo():
    if not _HAY_GIT:
        return None
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(_BASE), capture_output=True, text=True)
    return Path(p.stdout.strip()) if p.returncode == 0 else None


MOTOR = "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA"
OBRA = "SAGARDE OBRAS ABIERTAS/2026 OLABEAGA BILBAO/INFORME SAGARDE IA"
OTRA_OBRA = "SAGARDE OBRAS ABIERTAS/2025 GERNIKA 32V/INFORME SAGARDE IA"  # una regla solo para una obra no vale

# Cada fichero de DATOS o de ejecución que debe llegar a la web, con la parte de la regla que lo
# permite. Los .py y .html entran por las reglas generales de siempre.
CON_REGLA_PROPIA = {
    f"{MOTOR}/personal_calculo.js": "personal_calculo.js",
    f"{MOTOR}/personal_estado.js": "personal_estado.js",
    f"{MOTOR}/personal_catalogo.json": "personal_catalogo.json",
    f"{OBRA}/personal_obra.json": "personal_obra.json",
    f"{OBRA}/personal_jornadas.jsonl": "personal_jornadas.jsonl",
    f"{OTRA_OBRA}/personal_obra.json": "personal_obra.json",
    f"{OTRA_OBRA}/personal_jornadas.jsonl": "personal_jornadas.jsonl",
    f"{MOTOR}/tests/verificar_personal_calculo.js": "verificar_personal_calculo.js",
}
POR_REGLA_GENERAL = [
    f"{MOTOR}/personal_obra.py",
    f"{MOTOR}/panel_personal.py",
    f"{MOTOR}/personal_integracion.py",
    f"{MOTOR}/lector_control_horario.py",
    f"{MOTOR}/generador_personal.html",
    f"{MOTOR}/personal_sagarde.html",
]
# Ficheros de personal que NO están declarados: no deben publicarse sin que alguien lo decida.
NO_DECLARADOS = [
    f"{MOTOR}/personal_borrador.json",
    f"{MOTOR}/personal_estado.json",
    f"{MOTOR}/personal_copia.js",
    f"{OBRA}/personal_notas.json",
    f"{OBRA}/personal_jornadas.json",
    f"{OBRA}/personal_obra.json.bak",
    # 08b: el camino viejo («Ingerir_Personal.bat») se retiró y ya no se versiona.
    f"{MOTOR}/Ingerir_Personal.bat",
    # Los CONTROL HORARIO que Bixente deja en REVISIONES llevan nombres y horas: NO se publican (sus datos ya
    # están en personal_jornadas.jsonl). Se prueban con varias formas del nombre que puede dar el navegador.
    "SAGARDE OBRAS ABIERTAS/2026 OLABEAGA BILBAO/REVISIONES/CONTROL HORARIO 2026 OLABEAGA BILBAO 25102026.json",
    "SAGARDE OBRAS ABIERTAS/2026 OLABEAGA BILBAO/REVISIONES/CONTROL HORARIO 2026 OLABEAGA BILBAO 25102026 (1).json",
    "SAGARDE OBRAS ABIERTAS/2026 OLABEAGA BILBAO/REVISIONES/control horario 2026 olabeaga bilbao 25102026.JSON",
    "SAGARDE OBRAS ABIERTAS/2025 GERNIKA 32V/REVISIONES/CONTROL HORARIO 2025 GERNIKA 32V 01112026.json",
    "SAGARDE OBRAS ABIERTAS/personal_obra.json",  # fuera de «INFORME SAGARDE IA»
    "SAGARDE (OLD)/OBRAS CERRADAS/2025 X/INFORME SAGARDE IA/personal_obra.json",
]


@unittest.skipUnless(_raiz_repo(), "no hay git o esto no es un repositorio")
class TestPublicacionPersonal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = _raiz_repo()

    def _ignorado(self, ruta):
        """True si git ignoraría la ruta. Sin `-v`: con `-v` git sale con 0 también cuando casa
        una regla de permiso («!…»). Con `--no-index`: sin él, un fichero ya versionado nunca
        cuenta como ignorado y la prueba no mordería nunca."""
        p = subprocess.run(["git", "check-ignore", "--no-index", "--", ruta],
                           cwd=str(self.repo), capture_output=True, text=True, encoding="utf-8")
        return p.returncode == 0

    def _regla(self, ruta):
        """Línea `.gitignore:N:regla` que decide la suerte de la ruta."""
        p = subprocess.run(["git", "check-ignore", "-v", "--no-index", "--", ruta],
                           cwd=str(self.repo), capture_output=True, text=True, encoding="utf-8")
        return p.stdout.split("\t")[0]

    def test_cada_fichero_de_datos_tiene_su_propia_regla_y_no_esta_ignorado(self):
        for ruta, nombre in CON_REGLA_PROPIA.items():
            with self.subTest(ruta=ruta):
                self.assertFalse(self._ignorado(ruta), f"{ruta} está ignorado: no se publicaría")
                regla = self._regla(ruta)
                self.assertIn(":!", regla, f"{ruta}: ninguna regla de permiso lo cubre ({regla})")
                self.assertIn(nombre, regla, f"{ruta}: lo deja pasar una regla genérica, no la suya ({regla})")

    def test_el_codigo_y_las_paginas_de_personal_no_estan_ignorados(self):
        for ruta in POR_REGLA_GENERAL:
            with self.subTest(ruta=ruta):
                self.assertFalse(self._ignorado(ruta), f"{ruta} está ignorado")

    def test_un_fichero_de_personal_no_declarado_se_queda_fuera(self):
        for ruta in NO_DECLARADOS:
            with self.subTest(ruta=ruta):
                self.assertTrue(self._ignorado(ruta), f"{ruta} se publicaría sin estar declarado")

    def test_git_add_en_un_repositorio_de_prueba_incluye_justo_lo_declarado(self):
        """Lo que hace el .bat (`git add -A`), sobre un repositorio nuevo con el .gitignore REAL."""
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            shutil.copy(self.repo / ".gitignore", raiz / ".gitignore")
            for ruta in list(CON_REGLA_PROPIA) + POR_REGLA_GENERAL + NO_DECLARADOS:
                destino = raiz / ruta
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text("x\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            p = subprocess.run(["git", "add", "-A", "--dry-run"], cwd=tmp, capture_output=True,
                               text=True, encoding="utf-8")
            anadidos = {linea.strip()[5:-1] for linea in p.stdout.splitlines() if linea.startswith("add '")}
            esperados = set(CON_REGLA_PROPIA) | set(POR_REGLA_GENERAL) | {".gitignore"}
            self.assertEqual(anadidos, esperados)


if __name__ == "__main__":
    unittest.main()
