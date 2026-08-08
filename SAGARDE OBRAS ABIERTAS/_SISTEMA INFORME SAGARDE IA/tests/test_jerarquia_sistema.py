# -*- coding: utf-8 -*-
"""La norma de jerarquia: lo informatico vive en una carpeta _SISTEMA.

Norma del 07/08/2026. Cada apartado y cada obra tiene como mucho una
carpeta tecnica llamada _SISTEMA. 'INFORME SAGARDE IA' y '_SISTEMA
INFORME SAGARDE IA' son alias historicos: ya la implementan con otro
nombre y no se renombran porque sus panel.html estan publicados.

PENDIENTES es un trinquete: cada tarea del plan del 07/08/2026 borra sus
entradas. Cuando quede vacia, la norma esta aplicada. Anadir una entrada
nueva en vez de mover el fichero es saltarse la norma.
"""
import os
import unittest

SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBRAS_DIR = os.path.dirname(SISTEMA_DIR)
ROOT_DIR = os.path.dirname(OBRAS_DIR)

CARPETAS_SISTEMA = {"_SISTEMA", "_SISTEMA INFORME SAGARDE IA",
                    "INFORME SAGARDE IA"}

# Ramas que no se auditan.
RAMAS_EXCLUIDAS = {
    ".git",                # interno de git
    "SAGARDE (OLD)",       # archivo historico, 46 GB, fuera de alcance
    ".claude", ".gemini", ".agents", ".superpowers",  # ancladas a su raiz
    # __pycache__ NO se audita, y no es un descuido (08/08/2026). Nadie lo
    # escribe: Python lo genera junto al .py que importa. Su sitio es una
    # consecuencia automatica de donde este el codigo, que es justo lo que
    # esta prueba ya gobierna -movido el .py, la cache le sigue sola-.
    # Auditarlo ademas hacia la prueba no determinista: la propia suite
    # regenera _MOTOR_SAGARDE/__pycache__ al importar sus modulos, asi que
    # pasaba en un arbol limpio y fallaba al terminar de ejecutarse.
    # Declararlo en PENDIENTES fallaria al reves, en una maquina que no
    # hubiera corrido la suite todavia. Se limpia como mantenimiento (lo
    # hizo la tarea 5) y lo cubre .gitignore, no el trinquete.
    "__pycache__",
}

EXT_CODIGO = {".py", ".bat", ".cmd", ".ps1"}


def _es_tecnico(nombre):
    """Un fichero es tecnico si es codigo, o el respaldo de un codigo.

    Ojo con .bak y .log: AutoCAD deja un '<plano>.bak' (cabecera AC1027)
    junto a cada .dwg y un 'plot.log' con que plano se imprimio, cuando y
    en que impresora. Eso es DATO DE OBRA -vive donde debe, junto a su
    plano- y la norma no lo cubre. Decision de Bixente del 08/08/2026,
    tomada al descubrir que el inventario del plan metia 30 ficheros de
    AutoCAD en la misma bolsa que el codigo.

    Por eso .bak solo cuenta cuando el propio nombre delata que respalda
    codigo ('sagarde_portal.py.ANTES_MEJORA_ALERTAS_20260725.bak') y .log
    no cuenta nunca.
    """
    base, ext = os.path.splitext(nombre)
    ext = ext.lower()
    if ext in EXT_CODIGO:
        return True
    if ext == ".bak":
        base = base.lower()
        return any(e in base for e in EXT_CODIGO)
    return False


# Excepciones permanentes. Cada una es una decision, no un descuido.
EXCEPCIONES = {
    # Bixente lo quiere a la vista en la raiz: es el boton que pulsa.
    "Actualizar_Sagarde.bat",
    # VARIOS/APPS SAGARDE, TIERRAS, BATERIAS y MANUALES son subproyectos con
    # su propia raiz y su propio .claude. Reordenarlos es un trabajo aparte,
    # declarado fuera de alcance en la spec del 07/08/2026.
    "VARIOS",
    # APP_CARDIVA es una app autocontenida con su propio skills/ y tools/,
    # igual que los subproyectos de VARIOS. Ademas el CLAUDE.md declara
    # APP_CARDIVA/skills/generate-cardiva-report fuente canonica y
    # sync_cardiva_skill_agents.ps1 depende de esa ruta: moverlo rompe la
    # skill. Decision de Bixente del 08/08/2026; el plan no la inventario.
    "APP_CARDIVA",
}


def _violaciones():
    """Devuelve rutas relativas a ROOT_DIR que incumplen la norma."""
    malas = []
    for dirpath, dirnames, filenames in os.walk(ROOT_DIR):
        rel = os.path.relpath(dirpath, ROOT_DIR)
        partes = set() if rel == "." else set(rel.split(os.sep))
        if partes & RAMAS_EXCLUIDAS or partes & EXCEPCIONES:
            dirnames[:] = []
            continue
        if partes & CARPETAS_SISTEMA:
            dirnames[:] = []          # dentro de una carpeta tecnica todo vale
            continue
        for fn in filenames:
            if fn in EXCEPCIONES:
                continue
            if _es_tecnico(fn):
                r = fn if rel == "." else os.path.join(rel, fn)
                malas.append(r.replace("\\", "/"))
    return sorted(malas)


# Violaciones conocidas al escribir el plan. Se vacian tarea a tarea.
PENDIENTES = {
    # tarea 6 (raiz con referencias)
    "Servidor_Local.bat",
    "ABRIR_CLAUDE_SAGARDE.cmd",
    "ABRIR_GEMINI_SAGARDE.cmd",
    # tarea 8 (_MOTOR_SAGARDE -> _SISTEMA/MOTOR)
    # Los 3 .bak los recogio la tarea 5 en _bak/, pero eso no los saca de la
    # norma: _MOTOR_SAGARDE no es una carpeta _SISTEMA. Los absorbe esta.
    "_MOTOR_SAGARDE/_bak/sagarde_portal.py.ANTES_FASE3_MANTENIMIENTOS_20260725.bak",
    "_MOTOR_SAGARDE/_bak/sagarde_portal.py.ANTES_FIX_APPS_DUPLICADOS_20260725.bak",
    "_MOTOR_SAGARDE/_bak/sagarde_portal.py.ANTES_MEJORA_ALERTAS_20260725.bak",
    "_MOTOR_SAGARDE/avisos.py",
    "_MOTOR_SAGARDE/sagarde_portal.py",
    "_MOTOR_SAGARDE/scripts/auditor_sagarde.py",
    "_MOTOR_SAGARDE/scripts/generar_informe_ejecutivo.py",
    "_MOTOR_SAGARDE/scripts/generar_parte_incidencia.py",
    "_MOTOR_SAGARDE/scripts/regenerar_obra.py",
    "_MOTOR_SAGARDE/scripts/validar_revision_pdf.py",
    "_MOTOR_SAGARDE/tests/__init__.py",
    "_MOTOR_SAGARDE/tests/test_avisos.py",
    # tarea 10 (POST-VENTAS)
    "POST-VENTAS/Actualizar_Postventas.bat",
    "POST-VENTAS/postventas_index.py",
    "POST-VENTAS/postventas_sync.py",
    # tarea 11 (MANTENIMIENTOS)
    "MANTENIMIENTOS/mantenimientos_index.py",
}


class TestJerarquiaSistema(unittest.TestCase):

    def test_no_hay_violaciones_nuevas(self):
        """Ningun fichero tecnico fuera de _SISTEMA que no este declarado."""
        nuevas = set(_violaciones()) - PENDIENTES
        self.assertEqual(
            sorted(nuevas), [],
            "\nFicheros tecnicos fuera de una carpeta _SISTEMA que nadie "
            "declaro.\nMuevelos, o si hay una razon, anadela a EXCEPCIONES "
            "con el porque.")

    def test_pendientes_no_caduca(self):
        """PENDIENTES no puede citar algo que ya se movio."""
        fantasmas = PENDIENTES - set(_violaciones())
        self.assertEqual(
            sorted(fantasmas), [],
            "\nEstas entradas de PENDIENTES ya no existen en disco. "
            "Borralas: una lista con fantasmas deja de avisar de nada.")
