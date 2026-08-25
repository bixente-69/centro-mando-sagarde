# Comprobador de enlaces publicados — Plan de ejecución

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detectar, en cada publicación, enlaces internos rotos en el portal de Sagarde ya generado — igual que `actualizar_mapa_mental.py` ya detecta rutas muertas en su propia prosa, pero aplicado al HTML publicado.

**Architecture:** Un script de una sola responsabilidad, `_SISTEMA/MOTOR/scripts/comprobar_enlaces.py`, que recorre un conjunto fijo de páginas de nivel superior (portal raíz, índices de área, paneles de obra), extrae sus `href`/`src` con `html.parser` de la biblioteca estándar, descarta lo externo/anclas, y comprueba que el resto resuelva en disco. Se integra en `Actualizar_Sagarde.bat` como paso nuevo tras generar el portal, con el mismo contrato de códigos de salida (`0`/`1`/`2`) que ya usa el paso del mapa mental.

**Tech Stack:** Python 3, biblioteca estándar únicamente (`html.parser`, `pathlib`, `urllib.parse`). Pruebas con `unittest` de la biblioteca estándar.

## Global Constraints

- Sin dependencias nuevas: nada de `pip install` para este script. Coherente con `CLAUDE.md`: "No introducir pytest ni dependencias nuevas".
- Pruebas primero (TDD): cada tarea escribe el test, lo ve fallar, implementa lo mínimo, lo ve pasar.
- Los enlaces externos (`http`, `https`, `mailto`, `tel`, `javascript:`) y las anclas (`#id`) NO se comprueban — fuera de alcance por decisión de Bixente (spec §2).
- Sólo las páginas de nivel superior listadas en la spec — nada de recorrer las 128 obras cerradas ni los previews de postventa (spec §2).
- El resultado sólo se imprime por consola. Sin JSON nuevo que mantener (spec §2).
- **No ejecutar `Actualizar_Sagarde.bat` completo en ninguna tarea de este plan** — hace `git add -A`, commit y `push origin main`. Es el botón de Bixente; lo pulsa él. Las tareas verifican el script nuevo invocándolo directamente (`python _SISTEMA/MOTOR/scripts/comprobar_enlaces.py`) y revisando el diff del `.bat` a mano, no ejecutándolo de punta a punta.
- Suite del motor raíz: `cd "_SISTEMA/MOTOR" && python -m unittest discover -s tests` (48 casos en verde hoy, línea base). Debe seguir en verde tras cada tarea.

---

## Referencia de interfaces (fijada aquí, no se repite en cada tarea)

`_SISTEMA/MOTOR/scripts/comprobar_enlaces.py` expondrá, en este orden a través de las tareas:

```python
ROOT: Path                                  # raiz real del repo, fijada por __file__
PAGINAS_FIJAS: list[str]                    # 6 rutas relativas, con '/' como separador

def extraer_enlaces(html_texto: str) -> list[tuple[str, int]]
def es_enlace_interno(valor: str) -> bool
def resolver_ruta(valor: str, archivo_html: Path, raiz: Path) -> Path
def enlaces_rotos_de_pagina(archivo_html: Path, raiz: Path) -> list[dict]   # [{'destino': str, 'linea': int}, ...]
def paginas_a_comprobar(raiz: Path) -> list[Path]
def comprobar_enlaces(raiz: Path = ROOT) -> dict                            # {'ausentes': list[Path], 'rotos': dict[Path, list[dict]]}
def main(argv=None) -> int                                                  # 0 ok, 1 aviso, 2 error
```

---

### Task 1: Extracción y filtrado de enlaces

**Files:**
- Create: `_SISTEMA/MOTOR/scripts/comprobar_enlaces.py`
- Create: `_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py`

**Interfaces:**
- Produces: `extraer_enlaces(html_texto: str) -> list[tuple[str, int]]`, `es_enlace_interno(valor: str) -> bool`, `resolver_ruta(valor: str, archivo_html: Path, raiz: Path) -> Path`

- [ ] **Step 1: Escribir los tests que fallan**

Crear `_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py`:

```python
# -*- coding: utf-8 -*-
"""Enlaces internos rotos en el portal publicado de Sagarde.

Complementa el chequeo de rutas muertas de actualizar_mapa_mental.py: aquel
comprueba la prosa del mapa mental, este comprueba el HTML publicado de
verdad. Misma familia de fallo que el resto del proyecto: algo declarado
(un href) que nadie vuelve a mirar tras regenerarse.
"""
import sys
import tempfile
import unittest
from pathlib import Path

MOTOR_DIR = Path(__file__).resolve().parent.parent
ROOT = MOTOR_DIR.parent.parent
sys.path.insert(0, str(MOTOR_DIR / "scripts"))

import comprobar_enlaces as ce


class TestExtraerEnlaces(unittest.TestCase):
    def test_extrae_href_y_src_con_comillas_dobles_y_simples(self):
        html = '<a href="a.html">x</a><img src=\'b.png\'>'
        self.assertEqual([("a.html", 1), ("b.png", 1)], ce.extraer_enlaces(html))

    def test_ignora_atributos_que_no_son_href_ni_src(self):
        html = '<a href="a.html" data-search="a.html buscado">x</a>'
        self.assertEqual([("a.html", 1)], ce.extraer_enlaces(html))

    def test_numero_de_linea_correcto_en_html_multilinea(self):
        html = "<html>\n<body>\n<a href=\"c.html\">x</a>\n</body>\n</html>"
        self.assertEqual([("c.html", 3)], ce.extraer_enlaces(html))


class TestEsEnlaceInterno(unittest.TestCase):
    def test_relativo_es_interno(self):
        self.assertTrue(ce.es_enlace_interno("POST-VENTAS/index.html"))

    def test_http_y_https_no_son_internos(self):
        self.assertFalse(ce.es_enlace_interno("https://cdn.jsdelivr.net/chart.js"))
        self.assertFalse(ce.es_enlace_interno("http://example.com"))

    def test_mailto_tel_javascript_no_son_internos(self):
        self.assertFalse(ce.es_enlace_interno("mailto:a@b.com"))
        self.assertFalse(ce.es_enlace_interno("tel:+34600000000"))
        self.assertFalse(ce.es_enlace_interno("javascript:void(0)"))

    def test_ancla_no_es_interna(self):
        self.assertFalse(ce.es_enlace_interno("#kpis"))


class TestResolverRuta(unittest.TestCase):
    def test_decodifica_espacios_url_encoded(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            html = raiz / "index.html"
            html.write_text("<html></html>", encoding="utf-8")
            ruta = ce.resolver_ruta(
                "SAGARDE%20OBRAS%20ABIERTAS/index.html", html, raiz)
            self.assertEqual(
                raiz / "SAGARDE OBRAS ABIERTAS" / "index.html", ruta)

    def test_resuelve_relativo_a_la_carpeta_del_html_no_al_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "POST-VENTAS").mkdir()
            html = raiz / "POST-VENTAS" / "index.html"
            html.write_text("<html></html>", encoding="utf-8")
            ruta = ce.resolver_ruta("../APLICACIONES/index.html", html, raiz)
            self.assertEqual(raiz / "APLICACIONES" / "index.html", ruta)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Comprobar que falla**

Run: `cd "_SISTEMA/MOTOR" && python -m unittest tests.test_comprobar_enlaces -v`
Expected: `ModuleNotFoundError: No module named 'comprobar_enlaces'` (el archivo aún no existe).

- [ ] **Step 3: Implementación mínima**

Crear `_SISTEMA/MOTOR/scripts/comprobar_enlaces.py`:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
comprobar_enlaces.py — Enlaces internos rotos en el portal publicado de Sagarde

Recorre un conjunto fijo de paginas de nivel superior (portal raiz, indices
de area, paneles de obra) y comprueba que cada enlace interno relativo
(href/src) apunte a un archivo que existe. No comprueba enlaces externos
(http/https/mailto/tel/javascript:) ni anclas (#id).

Uso:
  python _SISTEMA/MOTOR/scripts/comprobar_enlaces.py
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
import sys

# _SISTEMA/MOTOR/scripts/comprobar_enlaces.py -> cuatro niveles hasta la raiz.
ROOT = Path(__file__).resolve().parent.parent.parent.parent

ESQUEMAS_EXTERNOS = ("http:", "https:", "mailto:", "tel:", "javascript:")

PAGINAS_FIJAS = [
    "index.html",
    "SAGARDE OBRAS ABIERTAS/index.html",
    "POST-VENTAS/index.html",
    "MANTENIMIENTOS/index.html",
    "APLICACIONES/index.html",
    "SAGARDE (OLD)/index.html",
]


class _ExtractorEnlaces(HTMLParser):
    """Recoge (valor, linea) de cada href/src de las etiquetas del HTML."""

    def __init__(self):
        super().__init__()
        self.enlaces: list[tuple[str, int]] = []

    def handle_starttag(self, tag, attrs):
        for nombre, valor in attrs:
            if nombre in ("href", "src") and valor:
                self.enlaces.append((valor, self.getpos()[0]))


def extraer_enlaces(html_texto: str) -> list[tuple[str, int]]:
    """Devuelve [(valor_bruto, linea), ...] de cada href/src del HTML."""
    parser = _ExtractorEnlaces()
    parser.feed(html_texto)
    return parser.enlaces


def es_enlace_interno(valor: str) -> bool:
    """True si el enlace es una ruta relativa que hay que comprobar en disco."""
    if valor.startswith("#"):
        return False
    return not valor.strip().lower().startswith(ESQUEMAS_EXTERNOS)


def resolver_ruta(valor: str, archivo_html: Path, raiz: Path) -> Path:
    """Resuelve un enlace interno relativo a la carpeta del HTML que lo contiene."""
    destino = unquote(valor.split("#", 1)[0].split("?", 1)[0])
    return (archivo_html.parent / destino).resolve()


if __name__ == "__main__":
    sys.exit(0)
```

- [ ] **Step 4: Comprobar que pasa**

Run: `cd "_SISTEMA/MOTOR" && python -m unittest tests.test_comprobar_enlaces -v`
Expected: 9 tests, todos `ok`.

- [ ] **Step 5: Commit**

```bash
git add "_SISTEMA/MOTOR/scripts/comprobar_enlaces.py" "_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py"
git commit -m "Extraccion y filtrado de enlaces internos para el comprobador de enlaces"
```

---

### Task 2: Enlaces rotos de una página real

**Files:**
- Modify: `_SISTEMA/MOTOR/scripts/comprobar_enlaces.py`
- Modify: `_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py`

**Interfaces:**
- Consumes: `extraer_enlaces`, `es_enlace_interno`, `resolver_ruta` (Task 1)
- Produces: `enlaces_rotos_de_pagina(archivo_html: Path, raiz: Path) -> list[dict]`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py` (antes de `if __name__ == "__main__":`):

```python
def _crear_html(raiz, ruta_rel, contenido):
    archivo = raiz / ruta_rel
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(contenido, encoding="utf-8")
    return archivo


class TestEnlacesRotosDePagina(unittest.TestCase):
    def test_detecta_un_enlace_roto(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            html = _crear_html(
                raiz, "index.html", '<a href="POST-VENTAS/index.html">x</a>')
            rotos = ce.enlaces_rotos_de_pagina(html, raiz)
            self.assertEqual(1, len(rotos))
            self.assertEqual("POST-VENTAS/index.html", rotos[0]["destino"])
            self.assertEqual(1, rotos[0]["linea"])

    def test_no_marca_un_enlace_correcto(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            _crear_html(raiz, "POST-VENTAS/index.html", "<html></html>")
            html = _crear_html(
                raiz, "index.html", '<a href="POST-VENTAS/index.html">x</a>')
            self.assertEqual([], ce.enlaces_rotos_de_pagina(html, raiz))

    def test_enlace_correcto_con_espacios_codificados_no_se_marca(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            _crear_html(raiz, "SAGARDE OBRAS ABIERTAS/index.html", "<html></html>")
            html = _crear_html(
                raiz, "index.html",
                '<a href="SAGARDE%20OBRAS%20ABIERTAS/index.html">x</a>')
            self.assertEqual([], ce.enlaces_rotos_de_pagina(html, raiz))

    def test_ignora_enlaces_externos_y_anclas(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            html = _crear_html(
                raiz, "index.html",
                '<a href="https://cdn.jsdelivr.net/chart.js">x</a>'
                '<a href="#kpis">y</a>')
            self.assertEqual([], ce.enlaces_rotos_de_pagina(html, raiz))
```

- [ ] **Step 2: Comprobar que falla**

Run: `cd "_SISTEMA/MOTOR" && python -m unittest tests.test_comprobar_enlaces.TestEnlacesRotosDePagina -v`
Expected: `AttributeError: module 'comprobar_enlaces' has no attribute 'enlaces_rotos_de_pagina'`

- [ ] **Step 3: Implementación mínima**

Añadir a `_SISTEMA/MOTOR/scripts/comprobar_enlaces.py`, después de `resolver_ruta`:

```python
def enlaces_rotos_de_pagina(archivo_html: Path, raiz: Path) -> list[dict]:
    """[{'destino': str, 'linea': int}, ...] de los enlaces internos rotos."""
    texto = archivo_html.read_text(encoding="utf-8")
    rotos = []
    for valor, linea in extraer_enlaces(texto):
        if not es_enlace_interno(valor):
            continue
        ruta = resolver_ruta(valor, archivo_html, raiz)
        if not ruta.exists():
            rotos.append({"destino": valor, "linea": linea})
    return rotos
```

- [ ] **Step 4: Comprobar que pasa**

Run: `cd "_SISTEMA/MOTOR" && python -m unittest tests.test_comprobar_enlaces -v`
Expected: 13 tests, todos `ok`.

- [ ] **Step 5: Commit**

```bash
git add "_SISTEMA/MOTOR/scripts/comprobar_enlaces.py" "_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py"
git commit -m "Detectar enlaces internos rotos dentro de una pagina publicada"
```

---

### Task 3: Lista de páginas a comprobar

**Files:**
- Modify: `_SISTEMA/MOTOR/scripts/comprobar_enlaces.py`
- Modify: `_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py`

**Interfaces:**
- Consumes: `registro_obras.OBRAS` — lista de dicts, cada uno con clave `'carpeta_obra'` (ej. `'2025 GERNIKA 32V'`), importado desde `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/registro_obras.py`
- Produces: `paginas_a_comprobar(raiz: Path) -> list[Path]`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py`, junto a los demás imports del principio del fichero:

```python
OBRA_MOTOR_DIR = ROOT / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
sys.path.insert(0, str(OBRA_MOTOR_DIR))

import registro_obras
```

Y esta clase de test (antes de `if __name__ == "__main__":`):

```python
class TestPaginasAComprobar(unittest.TestCase):
    def test_incluye_las_seis_paginas_fijas(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            paginas = ce.paginas_a_comprobar(raiz)
            relativas = {str(p.relative_to(raiz)).replace("\\", "/") for p in paginas}
            for fija in ce.PAGINAS_FIJAS:
                self.assertIn(fija, relativas)

    def test_incluye_el_panel_de_cada_obra_del_registro(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            paginas = ce.paginas_a_comprobar(raiz)
            relativas = {str(p.relative_to(raiz)).replace("\\", "/") for p in paginas}
            for obra in registro_obras.OBRAS:
                esperada = (
                    f"SAGARDE OBRAS ABIERTAS/{obra['carpeta_obra']}"
                    f"/INFORME SAGARDE IA/panel.html")
                self.assertIn(esperada, relativas)

    def test_no_hay_paginas_duplicadas(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            paginas = ce.paginas_a_comprobar(raiz)
            self.assertEqual(len(paginas), len(set(paginas)))
```

- [ ] **Step 2: Comprobar que falla**

Run: `cd "_SISTEMA/MOTOR" && python -m unittest tests.test_comprobar_enlaces.TestPaginasAComprobar -v`
Expected: `AttributeError: module 'comprobar_enlaces' has no attribute 'paginas_a_comprobar'`

- [ ] **Step 3: Implementación mínima**

En `_SISTEMA/MOTOR/scripts/comprobar_enlaces.py`, añadir tras los imports existentes (después de `import sys`):

```python
OBRA_MOTOR_DIR = ROOT / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
if str(OBRA_MOTOR_DIR) not in sys.path:
    sys.path.insert(0, str(OBRA_MOTOR_DIR))

from registro_obras import OBRAS
```

Y añadir, después de `enlaces_rotos_de_pagina`:

```python
def paginas_a_comprobar(raiz: Path) -> list[Path]:
    """Paginas fijas de nivel superior + panel.html de cada obra registrada."""
    paginas = [raiz / rel for rel in PAGINAS_FIJAS]
    for obra in OBRAS:
        paginas.append(
            raiz / "SAGARDE OBRAS ABIERTAS" / obra["carpeta_obra"]
            / "INFORME SAGARDE IA" / "panel.html"
        )
    return paginas
```

- [ ] **Step 4: Comprobar que pasa**

Run: `cd "_SISTEMA/MOTOR" && python -m unittest tests.test_comprobar_enlaces -v`
Expected: 16 tests, todos `ok`.

- [ ] **Step 5: Commit**

```bash
git add "_SISTEMA/MOTOR/scripts/comprobar_enlaces.py" "_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py"
git commit -m "Derivar la lista de paginas a comprobar desde registro_obras.OBRAS"
```

---

### Task 4: Orquestación y códigos de salida

**Files:**
- Modify: `_SISTEMA/MOTOR/scripts/comprobar_enlaces.py`
- Modify: `_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py`

**Interfaces:**
- Consumes: `paginas_a_comprobar`, `enlaces_rotos_de_pagina` (Tasks 2-3)
- Produces: `comprobar_enlaces(raiz: Path = ROOT) -> dict`, `main(argv=None) -> int`

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py` (antes de `if __name__ == "__main__":`):

```python
class TestComprobarEnlaces(unittest.TestCase):
    def test_devuelve_pagina_ausente_si_falta_una_pagina_fija(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            resultado = ce.comprobar_enlaces(raiz)
            self.assertGreaterEqual(len(resultado["ausentes"]), 1)

    def test_devuelve_vacio_cuando_todo_resuelve(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            for pagina in ce.paginas_a_comprobar(raiz):
                pagina.parent.mkdir(parents=True, exist_ok=True)
                pagina.write_text("<html></html>", encoding="utf-8")
            resultado = ce.comprobar_enlaces(raiz)
            self.assertEqual([], resultado["ausentes"])
            self.assertEqual({}, resultado["rotos"])

    def test_devuelve_rotos_si_una_pagina_existente_enlaza_a_la_nada(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            for pagina in ce.paginas_a_comprobar(raiz):
                pagina.parent.mkdir(parents=True, exist_ok=True)
                pagina.write_text("<html></html>", encoding="utf-8")
            raiz_index = raiz / "index.html"
            raiz_index.write_text('<a href="no_existe.html">x</a>', encoding="utf-8")
            resultado = ce.comprobar_enlaces(raiz)
            self.assertEqual([], resultado["ausentes"])
            self.assertIn(raiz_index, resultado["rotos"])


class TestMain(unittest.TestCase):
    def setUp(self):
        self._root_original = ce.ROOT
        self.addCleanup(self._restaurar)

    def _restaurar(self):
        ce.ROOT = self._root_original

    def _preparar_arbol_completo(self, raiz):
        for pagina in ce.paginas_a_comprobar(raiz):
            pagina.parent.mkdir(parents=True, exist_ok=True)
            pagina.write_text("<html></html>", encoding="utf-8")

    def test_codigo_0_cuando_todo_resuelve(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            self._preparar_arbol_completo(raiz)
            ce.ROOT = raiz
            self.assertEqual(0, ce.main([]))

    def test_codigo_1_cuando_hay_enlaces_rotos(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            self._preparar_arbol_completo(raiz)
            (raiz / "index.html").write_text(
                '<a href="no_existe.html">x</a>', encoding="utf-8")
            ce.ROOT = raiz
            self.assertEqual(1, ce.main([]))

    def test_codigo_2_cuando_falta_una_pagina_fija(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            ce.ROOT = raiz
            self.assertEqual(2, ce.main([]))
```

- [ ] **Step 2: Comprobar que falla**

Run: `cd "_SISTEMA/MOTOR" && python -m unittest tests.test_comprobar_enlaces.TestComprobarEnlaces tests.test_comprobar_enlaces.TestMain -v`
Expected: `AttributeError: module 'comprobar_enlaces' has no attribute 'comprobar_enlaces'`

- [ ] **Step 3: Implementación mínima**

Añadir a `_SISTEMA/MOTOR/scripts/comprobar_enlaces.py`, después de `paginas_a_comprobar`, y sustituir el bloque final `if __name__ == "__main__": sys.exit(0)` por lo siguiente:

```python
def comprobar_enlaces(raiz: Path = ROOT) -> dict:
    """{'ausentes': [Path,...], 'rotos': {Path: [dict,...]}}"""
    ausentes = []
    rotos = {}
    for pagina in paginas_a_comprobar(raiz):
        if not pagina.is_file():
            ausentes.append(pagina)
            continue
        encontrados = enlaces_rotos_de_pagina(pagina, raiz)
        if encontrados:
            rotos[pagina] = encontrados
    return {"ausentes": ausentes, "rotos": rotos}


def main(argv=None) -> int:
    resultado = comprobar_enlaces(ROOT)
    ausentes = resultado["ausentes"]
    rotos = resultado["rotos"]

    if ausentes:
        print("  [ERROR] Faltan paginas que deberian existir tras publicar el portal:")
        for pagina in ausentes:
            print(f"    - {pagina}")
        return 2

    if rotos:
        total = sum(len(v) for v in rotos.values())
        print(f"  [AVISO] {total} enlace(s) roto(s) en el portal publicado:")
        for pagina, items in rotos.items():
            for item in items:
                print(f"    - {pagina.name} -> {item['destino']} (linea {item['linea']})")
        return 1

    print("  Todos los enlaces del portal publicado resuelven.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Nota: `main()` llama a `comprobar_enlaces(ROOT)` leyendo el global `ROOT` en el cuerpo de la función — no como valor por defecto del parámetro — para que un test pueda sustituir `ce.ROOT` antes de llamar a `ce.main([])` y que el cambio se note (un valor por defecto se fijaría una sola vez, al definir la función, y el monkeypatch no tendría efecto).

- [ ] **Step 4: Comprobar que pasa**

Run: `cd "_SISTEMA/MOTOR" && python -m unittest tests.test_comprobar_enlaces -v`
Expected: 22 tests, todos `ok`.

Run también, sobre el árbol real, para ver el comportamiento de verdad:
Run: `python "_SISTEMA/MOTOR/scripts/comprobar_enlaces.py"; echo "codigo: $?"`
Expected: `Todos los enlaces del portal publicado resuelven.` y `codigo: 0` (según lo comprobado a mano en la auditoría del 25/08/2026 — si aparece algo distinto, es una regresión real a investigar antes de seguir, no un fallo del test).

- [ ] **Step 5: Commit**

```bash
git add "_SISTEMA/MOTOR/scripts/comprobar_enlaces.py" "_SISTEMA/MOTOR/tests/test_comprobar_enlaces.py"
git commit -m "Orquestar el comprobador de enlaces con codigos de salida 0/1/2"
```

---

### Task 5: Enganchar en Actualizar_Sagarde.bat

**Files:**
- Modify: `Actualizar_Sagarde.bat`

**Interfaces:**
- Consumes: `comprobar_enlaces.py` ejecutado como proceso (`%PY% "_SISTEMA\MOTOR\scripts\comprobar_enlaces.py"`), códigos de salida `0`/`1`/`2` (Task 4)

- [ ] **Step 1: Renumerar los pasos existentes de `/5` a `/6`**

En `Actualizar_Sagarde.bat`, sustituir:

```bat
echo [0/5] Ejecutando Auditoria Pre-Vuelo de Salud de Datos...
```
por
```bat
echo [0/6] Ejecutando Auditoria Pre-Vuelo de Salud de Datos...
```

Sustituir:
```bat
echo [1/5] Actualizando Informe Sagarde IA (Obras abiertas)...
```
por
```bat
echo [1/6] Actualizando Informe Sagarde IA (Obras abiertas)...
```

Sustituir:
```bat
echo [2/5] Actualizando Post-ventas y Mantenimientos...
```
por
```bat
echo [2/6] Actualizando Post-ventas y Mantenimientos...
```

Sustituir:
```bat
echo [3/5] Generando portal principal...
```
por
```bat
echo [3/6] Generando portal principal...
```

- [ ] **Step 2: Insertar el paso nuevo justo después del portal**

Sustituir el bloque:

```bat
echo [4/5] Actualizando el mapa mental del entorno...
%PY% "_SISTEMA\MOTOR\scripts\actualizar_mapa_mental.py"
if errorlevel 2 (
  echo   [ERROR] No se pudo actualizar el mapa mental. Se publica sin tocarlo.
) else if errorlevel 1 (
  echo   [AVISO] El mapa mental declara rutas que ya no existen. Quedan escritas
  echo           dentro del propio mapa. Se publica igual, pero corrigelas: es la
  echo           lectura obligatoria al empezar sesion y manda a un sitio vacio.
)

echo.
echo [5/5] Subiendo a la nube (GitHub Pages)...
```

por:

```bat
echo [4/6] Comprobando enlaces del portal publicado...
%PY% "_SISTEMA\MOTOR\scripts\comprobar_enlaces.py"
if errorlevel 2 (
  echo   [ERROR] Faltan paginas que deberian existir tras publicar. Revisa el
  echo           paso anterior.
) else if errorlevel 1 (
  echo   [AVISO] Hay enlaces internos rotos en el portal publicado. Quedan
  echo           listados arriba. Se publica igual, pero conviene corregirlos.
)

echo.
echo [5/6] Actualizando el mapa mental del entorno...
%PY% "_SISTEMA\MOTOR\scripts\actualizar_mapa_mental.py"
if errorlevel 2 (
  echo   [ERROR] No se pudo actualizar el mapa mental. Se publica sin tocarlo.
) else if errorlevel 1 (
  echo   [AVISO] El mapa mental declara rutas que ya no existen. Quedan escritas
  echo           dentro del propio mapa. Se publica igual, pero corrigelas: es la
  echo           lectura obligatoria al empezar sesion y manda a un sitio vacio.
)

echo.
echo [6/6] Subiendo a la nube (GitHub Pages)...
```

- [ ] **Step 3: Verificar el script nuevo directamente — NO ejecutar el `.bat` completo**

`Actualizar_Sagarde.bat` termina en `git add -A` + commit + `push origin main`: no se ejecuta de punta a punta en una tarea de este plan. En su lugar:

Run: `python "_SISTEMA/MOTOR/scripts/comprobar_enlaces.py"; echo "codigo: $?"`
Expected: mismo resultado que en la Task 4 (`Todos los enlaces del portal publicado resuelven.`, código `0`).

Revisar a mano el diff completo de `Actualizar_Sagarde.bat` (`git diff Actualizar_Sagarde.bat`) y confirmar:
- Los pasos `[0/6]` a `[3/6]` y `[5/6]`-`[6/6]` conservan exactamente el mismo contenido que antes, solo cambia el numerador.
- El paso `[4/6]` nuevo sigue el mismo patrón de `errorlevel` que el resto del `.bat`.

- [ ] **Step 4: Confirmar que la suite completa del motor sigue en verde**

Run: `cd "_SISTEMA/MOTOR" && python -m unittest discover -s tests`
Expected: `OK` (48 + 22 = 70 tests; el `.bat` no tiene pruebas propias, pero no debe haber roto nada de `_SISTEMA/MOTOR`).

- [ ] **Step 5: Commit**

```bash
git add "Actualizar_Sagarde.bat"
git commit -m "Enganchar el comprobador de enlaces en Actualizar_Sagarde.bat, paso 4/6"
```

**No hacer push.** Igual que el resto de este plan: el commit queda en local; publicar (`Actualizar_Sagarde.bat` o `git push`) lo decide Bixente.

---

## Verificación final del plan completo

1. `cd "_SISTEMA/MOTOR" && python -m unittest discover -s tests` → `OK`, 70 casos.
2. `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests` → sigue en `OK` (445 casos) — este plan no toca ese árbol, pero se confirma que nada se rompió por proximidad.
3. `python "_SISTEMA/MOTOR/scripts/comprobar_enlaces.py"` sobre el árbol real → código `0`, coincide con la auditoría del 25/08/2026.
4. Prueba por mutación manual: copiar `index.html` a un scratch temporal, romper un `href` a propósito, ejecutar el script contra esa copia y confirmar que devuelve `1` con el enlace roto señalado — no basta con que el código "parezca" correcto (regla del proyecto).
5. `git log --oneline -6` muestra los 5 commits de este plan, ninguno pusheado.
6. Reportar a Bixente: 6 commits locales listos, nada publicado, y que la próxima vez que él ejecute `Actualizar_Sagarde.bat` verá el nuevo paso `[4/6]` en la ventana.
