# Cierre de obra — plan de implementación

> **Para quien ejecute esto:** usar `superpowers:subagent-driven-development` o
> `superpowers:executing-plans`, tarea por tarea. Los pasos van con casilla
> `- [ ]` para ir marcando.

**Objetivo:** que `python cerrar_obra.py <id>` cierre una obra dejando el
entorno limpio: la saca del registro, archiva su adaptador con ella, mueve su
carpeta a `SAGARDE (OLD)/OBRAS CERRADAS` y deja escrito cómo terminó.

**Arquitectura:** un módulo con funciones pequeñas y puras donde se puede
(leer estado, calcular el informe, reescribir el registro) y un orquestador
que las encadena tras pasar las guardas. Nada se mueve sin `--ejecutar`.

**Diseño aprobado:** `_SISTEMA/docs/superpowers/specs/2026-08-13-cierre-de-obra-design.md`

## Restricciones globales

- **`unittest` de la biblioteca estándar.** No introducir pytest ni ninguna
  dependencia nueva: Bixente ejecuta todo con ficheros `.bat`.
- **Las pruebas trabajan sobre un árbol temporal**, nunca sobre obras reales.
- **No tocar `reglas/CATALOGO_TAJOS.json`.** No está en git; si se estropea no
  hay forma de restaurarlo.
- **No tocar `.gitignore`.**
- **El script no regenera ni publica.** Eso lo hace `Actualizar_Sagarde.bat`.
- Ruta del motor de obras, que aquí se abrevia `_SISTEMA...`:
  `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`
- Comentarios y mensajes en castellano, como el resto del motor.

## Ficheros

| Fichero | Responsabilidad |
|---|---|
| `_SISTEMA.../cerrar_obra.py` | Todo el cierre: lectura de estado, informe, retirada del registro, archivado y movimiento |
| `_SISTEMA.../tests/test_cerrar_obra.py` | Las 8 pruebas del contrato |
| `.claude/skills/sagarde-cerrar-obra/SKILL.md` | Cuándo usarlo y qué verificar después |

Ejecutar la suite de obras:

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

---

### Tarea 1: Leer cómo está la obra antes de cerrarla

**Ficheros:**
- Crear: `_SISTEMA.../cerrar_obra.py`
- Crear: `_SISTEMA.../tests/test_cerrar_obra.py`

**Interfaces:**
- Produce: `estado_de_cierre(raiz, obra) -> dict` con las claves
  `obra`, `id`, `carpeta`, `ubicaciones`, `tajos`, `celdas`, `desglose`,
  `ultima_revision`, `pct`. `obra` es una entrada del registro (dict con
  `id`, `nombre`, `carpeta_obra`, `adaptador`).
- Produce: `CierreAbortado(Exception)`.

- [ ] **Paso 1: escribir la prueba que falla**

```python
# -*- coding: utf-8 -*-
"""El cierre de una obra mueve datos reales: cada paso se prueba antes."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SISTEMA_DIR)

import cerrar_obra


def _obra_falsa(raiz, carpeta="2026 OBRA FALSA", con_ficha=True):
    """Monta una obra mínima en un árbol temporal."""
    salida = raiz / "SAGARDE OBRAS ABIERTAS" / carpeta / "INFORME SAGARDE IA"
    salida.mkdir(parents=True)
    if con_ficha:
        estados = {}
        for portal in ("p1", "p2"):
            for unidad in ("A", "B"):
                for tajo in ("tabicado", "tubeado", "mecanizado"):
                    estados[f"{portal}__pb__{tajo}__{unidad}"] = {
                        "v": "X", "f": "01/06/2026", "r": "rev_01062026"}
        estados["p1__pb__tabicado__A"]["v"] = "P"
        (salida / "ficha_obra.json").write_text(json.dumps({
            "id": "falsa",
            "tajos": {"aplicables": ["tabicado", "tubeado", "mecanizado"]},
            "estados": estados,
            "revisiones": [{"fecha": "01/06/2026"}],
        }), encoding="utf-8")
    return {
        "id": "falsa",
        "nombre": "2026 OBRA FALSA",
        "carpeta_obra": carpeta,
        "adaptador": "adaptador_falsa",
    }


class TestEstadoDeCierre(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = _obra_falsa(self.raiz)
        self.addCleanup(self._tmp.cleanup)

    def test_mide_la_obra_desde_su_ficha(self):
        e = cerrar_obra.estado_de_cierre(self.raiz, self.obra)
        self.assertEqual(4, e["ubicaciones"])
        self.assertEqual(3, e["tajos"])
        self.assertEqual(12, e["celdas"])

    def test_guarda_el_desglose_y_no_solo_un_porcentaje(self):
        # El porcentaje redondeado es un criterio ciego (CLAUDE.md seccion 3).
        e = cerrar_obra.estado_de_cierre(self.raiz, self.obra)
        self.assertEqual({"X": 11, "P": 1}, e["desglose"])

    def test_una_obra_sin_ficha_no_se_inventa_cifras(self):
        obra = _obra_falsa(self.raiz, carpeta="2026 SIN FICHA", con_ficha=False)
        e = cerrar_obra.estado_de_cierre(self.raiz, obra)
        self.assertEqual({}, e["desglose"])
        self.assertIsNone(e["celdas"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Paso 2: ejecutarla y ver que falla**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_cerrar_obra -v
```

Se espera: `ModuleNotFoundError: No module named 'cerrar_obra'`.

- [ ] **Paso 3: escribir el mínimo para que pase**

```python
# -*- coding: utf-8 -*-
"""Cierra una obra y la manda al archivo, dejando el entorno limpio.

Cerrar una obra a mano —mover la carpeta y ya— parece funcionar: el motor la
salta con un aviso y el portal la recoge sola como cerrada. Pero deja la obra
en `registro_obras.py` avisando en cada publicacion, y su adaptador huerfano
en `adaptadores/`, que es como llevan Egurrola y Zorrozaure desde que se
cerraron.

Uso:
    python cerrar_obra.py <id_obra>              # informa, no toca nada
    python cerrar_obra.py <id_obra> --ejecutar   # lo hace

Diseno: _SISTEMA/docs/superpowers/specs/2026-08-13-cierre-de-obra-design.md
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
OBRAS_ABIERTAS = "SAGARDE OBRAS ABIERTAS"
OBRAS_CERRADAS = os.path.join("SAGARDE (OLD)", "OBRAS CERRADAS")
SALIDA_OBRA = "INFORME SAGARDE IA"


class CierreAbortado(Exception):
    """El cierre no puede seguir. Nada se ha movido."""


def _carpeta_obra(raiz: Path, obra: dict) -> Path:
    return Path(raiz) / OBRAS_ABIERTAS / obra["carpeta_obra"]


def estado_de_cierre(raiz: Path, obra: dict) -> dict:
    """Como esta la obra ahora mismo, leido de su ficha.

    Sin ficha no se inventa nada: `celdas` sale None y el desglose vacio.
    """
    raiz = Path(raiz)
    ficha_ruta = _carpeta_obra(raiz, obra) / SALIDA_OBRA / "ficha_obra.json"
    desglose: Counter = Counter()
    ubicaciones: set = set()
    celdas = None
    tajos = None
    ultima = None
    if ficha_ruta.exists():
        ficha = json.loads(ficha_ruta.read_text(encoding="utf-8"))
        estados = ficha.get("estados") or {}
        celdas = len(estados)
        tajos = len(ficha.get("tajos", {}).get("aplicables", []))
        for clave, celda in estados.items():
            valor = celda.get("v") if isinstance(celda, dict) else celda
            if valor:
                desglose[valor] += 1
            partes = clave.split("__")
            if len(partes) == 4:
                ubicaciones.add((partes[0], partes[1], partes[3]))
        revisiones = ficha.get("revisiones") or []
        if revisiones:
            ultima = revisiones[-1].get("fecha")
    return {
        "obra": obra["nombre"],
        "id": obra["id"],
        "carpeta": obra["carpeta_obra"],
        "ubicaciones": len(ubicaciones) if ficha_ruta.exists() else None,
        "tajos": tajos,
        "celdas": celdas,
        "desglose": dict(desglose),
        "ultima_revision": ultima,
        "pct": _pct_publicado(raiz, obra["nombre"]),
    }


def _pct_publicado(raiz: Path, nombre: str):
    """pct_ponderado que publica el motor, si existe el resumen."""
    resumen = (Path(raiz) / OBRAS_ABIERTAS / "_SISTEMA INFORME SAGARDE IA"
               / "resumen_obras.json")
    if not resumen.exists():
        return None
    try:
        datos = json.loads(resumen.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    obras = datos if isinstance(datos, list) else datos.get("obras", [])
    for o in obras:
        if isinstance(o, dict) and o.get("nombre") == nombre:
            return o.get("pct_ponderado")
    return None
```

- [ ] **Paso 4: ejecutar y ver que pasa**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_cerrar_obra -v
```

Se esperan 3 pruebas en verde.

- [ ] **Paso 5: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/cerrar_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_cerrar_obra.py"
git commit -m "Medir como esta una obra antes de cerrarla"
```

---

### Tarea 2: Retirar la obra del registro sin romperlo

Reescribir código con expresiones regulares es frágil. Se usa `ast` para
localizar las **líneas exactas** del diccionario de esa obra, se borran, y
después se vuelve a ejecutar el fichero resultante para comprobar que sigue
siendo Python válido y que solo ha desaparecido esa obra. Si la comprobación
falla, no se escribe nada.

**Ficheros:**
- Modificar: `_SISTEMA.../cerrar_obra.py`
- Modificar: `_SISTEMA.../tests/test_cerrar_obra.py`

**Interfaces:**
- Consume: `CierreAbortado` de la tarea 1.
- Produce: `registro_sin_obra(fuente: str, id_obra: str) -> str` — devuelve el
  texto nuevo del registro, no escribe.
- Produce: `ids_declarados(fuente: str) -> list[str]`.

- [ ] **Paso 1: escribir la prueba que falla**

Añadir a `tests/test_cerrar_obra.py`:

```python
REGISTRO_DE_JUGUETE = '''# -*- coding: utf-8 -*-
import os


OBRAS = [
    {
        'id': 'una',
        'nombre': '2026 UNA',
        'carpeta_obra': '2026 UNA',
        'adaptador': 'adaptador_una',
    },
    {
        # Un comentario dentro del bloque, como el de OBRA PRUEBA.
        'id': 'otra',
        'nombre': '2026 OTRA',
        'carpeta_obra': '2026 OTRA',
        'adaptador': 'adaptador_otra',
        'materiales_rel': os.path.join('REVISIONES', 'x.xlsx'),
    },
    {
        'id': 'tercera',
        'nombre': '2026 TERCERA',
        'carpeta_obra': '2026 TERCERA',
        'adaptador': 'adaptador_tercera',
    },
]
'''


class TestRetirarDelRegistro(unittest.TestCase):

    def test_quita_solo_esa_obra(self):
        nuevo = cerrar_obra.registro_sin_obra(REGISTRO_DE_JUGUETE, "otra")
        self.assertEqual(["una", "tercera"], cerrar_obra.ids_declarados(nuevo))

    def test_el_resultado_sigue_siendo_python_valido(self):
        nuevo = cerrar_obra.registro_sin_obra(REGISTRO_DE_JUGUETE, "otra")
        compile(nuevo, "registro_obras.py", "exec")

    def test_se_lleva_los_comentarios_de_dentro_del_bloque(self):
        nuevo = cerrar_obra.registro_sin_obra(REGISTRO_DE_JUGUETE, "otra")
        self.assertNotIn("Un comentario dentro del bloque", nuevo)
        self.assertNotIn("adaptador_otra", nuevo)

    def test_las_demas_obras_quedan_intactas(self):
        nuevo = cerrar_obra.registro_sin_obra(REGISTRO_DE_JUGUETE, "otra")
        self.assertIn("'adaptador': 'adaptador_una',", nuevo)
        self.assertIn("'adaptador': 'adaptador_tercera',", nuevo)

    def test_una_obra_que_no_esta_es_un_error_y_no_un_silencio(self):
        with self.assertRaises(cerrar_obra.CierreAbortado):
            cerrar_obra.registro_sin_obra(REGISTRO_DE_JUGUETE, "inexistente")
```

- [ ] **Paso 2: ejecutarla y ver que falla**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_cerrar_obra.TestRetirarDelRegistro -v
```

Se espera: `AttributeError: module 'cerrar_obra' has no attribute 'registro_sin_obra'`.

- [ ] **Paso 3: escribir el mínimo para que pase**

Añadir a `cerrar_obra.py` (y `import ast` arriba):

```python
def ids_declarados(fuente: str) -> list[str]:
    """Los id de OBRAS, ejecutando el registro en un espacio aparte."""
    espacio: dict = {}
    exec(compile(fuente, "registro_obras.py", "exec"), espacio)
    return [o["id"] for o in espacio["OBRAS"]]


def registro_sin_obra(fuente: str, id_obra: str) -> str:
    """Devuelve el registro sin esa obra. No escribe nada.

    Se localiza el bloque con `ast`, no con expresiones regulares: el nodo del
    diccionario ya sabe en que linea empieza y acaba, comentarios de dentro
    incluidos. Despues se comprueba que lo que queda sigue siendo Python y que
    solo ha desaparecido la obra pedida.
    """
    arbol = ast.parse(fuente)
    lista = None
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign):
            for destino in nodo.targets:
                if getattr(destino, "id", None) == "OBRAS":
                    lista = nodo.value
    if not isinstance(lista, ast.List):
        raise CierreAbortado(
            "registro_obras.py no declara una lista OBRAS; no se toca.")

    objetivo = None
    for elemento in lista.elts:
        if not isinstance(elemento, ast.Dict):
            continue
        for clave, valor in zip(elemento.keys, elemento.values):
            if (getattr(clave, "value", None) == "id"
                    and getattr(valor, "value", None) == id_obra):
                objetivo = elemento
    if objetivo is None:
        raise CierreAbortado(
            f"El registro no declara ninguna obra con id '{id_obra}'.")

    lineas = fuente.splitlines(keepends=True)
    nuevo = "".join(lineas[:objetivo.lineno - 1] + lineas[objetivo.end_lineno:])

    antes = ids_declarados(fuente)
    despues = ids_declarados(nuevo)
    esperado = [i for i in antes if i != id_obra]
    if despues != esperado:
        raise CierreAbortado(
            "Retirar la obra del registro habria cambiado algo mas: "
            f"esperaba {esperado} y queda {despues}. No se escribe nada.")
    return nuevo
```

- [ ] **Paso 4: ejecutar y ver que pasa**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_cerrar_obra -v
```

Se esperan 8 pruebas en verde.

- [ ] **Paso 5: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/cerrar_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_cerrar_obra.py"
git commit -m "Retirar una obra del registro por AST y verificar el resultado"
```

---

### Tarea 3: Archivar el adaptador y mover la carpeta

**Ficheros:**
- Modificar: `_SISTEMA.../cerrar_obra.py`
- Modificar: `_SISTEMA.../tests/test_cerrar_obra.py`

**Interfaces:**
- Produce: `archivar_adaptador(raiz, obra) -> Path | None` — mueve
  `adaptadores/<adaptador>.py` a `<carpeta_obra>/_SISTEMA/`. Devuelve el
  destino, o None si el adaptador no existía.
- Produce: `mover_a_cerradas(raiz, obra) -> Path` — devuelve la ruta nueva.

- [ ] **Paso 1: escribir la prueba que falla**

```python
class TestArchivarYMover(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = _obra_falsa(self.raiz)
        adaptadores = (self.raiz / "SAGARDE OBRAS ABIERTAS"
                       / "_SISTEMA INFORME SAGARDE IA" / "adaptadores")
        adaptadores.mkdir(parents=True)
        (adaptadores / "adaptador_falsa.py").write_text("# lee sus hojas",
                                                        encoding="utf-8")
        (self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS").mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def test_el_adaptador_viaja_dentro_del_SISTEMA_de_la_obra(self):
        destino = cerrar_obra.archivar_adaptador(self.raiz, self.obra)
        self.assertTrue(destino.exists())
        self.assertEqual("_SISTEMA", destino.parent.name)
        origen = (self.raiz / "SAGARDE OBRAS ABIERTAS"
                  / "_SISTEMA INFORME SAGARDE IA" / "adaptadores"
                  / "adaptador_falsa.py")
        self.assertFalse(origen.exists())

    def test_sin_adaptador_no_es_un_error(self):
        cerrar_obra.archivar_adaptador(self.raiz, self.obra)
        self.assertIsNone(cerrar_obra.archivar_adaptador(self.raiz, self.obra))

    def test_la_carpeta_acaba_en_obras_cerradas(self):
        destino = cerrar_obra.mover_a_cerradas(self.raiz, self.obra)
        self.assertTrue((destino / "INFORME SAGARDE IA" / "ficha_obra.json").exists())
        self.assertFalse((self.raiz / "SAGARDE OBRAS ABIERTAS"
                          / "2026 OBRA FALSA").exists())

    def test_si_el_destino_ya_existe_aborta_sin_tocar_nada(self):
        (self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS" / "2026 OBRA FALSA").mkdir()
        with self.assertRaises(cerrar_obra.CierreAbortado):
            cerrar_obra.mover_a_cerradas(self.raiz, self.obra)
        self.assertTrue((self.raiz / "SAGARDE OBRAS ABIERTAS"
                         / "2026 OBRA FALSA").exists())
```

- [ ] **Paso 2: ejecutarla y ver que falla**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_cerrar_obra.TestArchivarYMover -v
```

Se espera: `AttributeError: ... has no attribute 'archivar_adaptador'`.

- [ ] **Paso 3: escribir el mínimo para que pase**

Añadir a `cerrar_obra.py` (y `import shutil` arriba):

```python
def archivar_adaptador(raiz: Path, obra: dict):
    """Mueve el adaptador dentro de la obra, a su carpeta `_SISTEMA`.

    Asi no queda un huerfano en `adaptadores/` —como Egurrola y Zorrozaure—
    pero el codigo que sabe leer sus hojas viaja con la obra por si algun dia
    hay que releerlas.
    """
    raiz = Path(raiz)
    nombre = obra.get("adaptador")
    if not nombre:
        return None
    origen = (raiz / OBRAS_ABIERTAS / "_SISTEMA INFORME SAGARDE IA"
              / "adaptadores" / f"{nombre}.py")
    if not origen.exists():
        return None
    destino_dir = _carpeta_obra(raiz, obra) / "_SISTEMA"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / origen.name
    shutil.move(str(origen), str(destino))
    return destino


def mover_a_cerradas(raiz: Path, obra: dict) -> Path:
    """Mueve la carpeta entera al archivo historico."""
    raiz = Path(raiz)
    origen = _carpeta_obra(raiz, obra)
    if not origen.is_dir():
        raise CierreAbortado(f"La carpeta de la obra no existe: {origen}")
    destino = raiz / OBRAS_CERRADAS / obra["carpeta_obra"]
    if destino.exists():
        raise CierreAbortado(
            f"Ya hay una obra archivada con ese nombre: {destino}. "
            "No se sobrescribe.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(origen), str(destino))
    return destino
```

- [ ] **Paso 4: ejecutar y ver que pasa**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_cerrar_obra -v
```

Se esperan 12 pruebas en verde.

- [ ] **Paso 5: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/cerrar_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_cerrar_obra.py"
git commit -m "Archivar el adaptador con su obra y mover la carpeta a cerradas"
```

---

### Tarea 4: Dejar escrito cómo terminó la obra

**Ficheros:**
- Modificar: `_SISTEMA.../cerrar_obra.py`
- Modificar: `_SISTEMA.../tests/test_cerrar_obra.py`

**Interfaces:**
- Consume: `estado_de_cierre` de la tarea 1.
- Produce: `escribir_cierre(destino: Path, estado: dict, commit: str | None) -> Path`
  — escribe `<destino>/_SISTEMA/cierre.json`.

- [ ] **Paso 1: escribir la prueba que falla**

```python
class TestFichaDeCierre(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = _obra_falsa(self.raiz)
        self.addCleanup(self._tmp.cleanup)

    def test_recoge_el_desglose_medido_y_no_un_resumen(self):
        estado = cerrar_obra.estado_de_cierre(self.raiz, self.obra)
        destino = self.raiz / "archivada"
        destino.mkdir()
        ruta = cerrar_obra.escribir_cierre(destino, estado, "abc1234")
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        self.assertEqual({"X": 11, "P": 1}, datos["estado_final"]["desglose"])
        self.assertEqual(12, datos["estado_final"]["celdas"])
        self.assertEqual("abc1234", datos["commit_al_cerrar"])
        self.assertIn("fecha_cierre", datos)

    def test_vive_dentro_del_SISTEMA_de_la_obra_archivada(self):
        estado = cerrar_obra.estado_de_cierre(self.raiz, self.obra)
        destino = self.raiz / "archivada"
        destino.mkdir()
        ruta = cerrar_obra.escribir_cierre(destino, estado, None)
        self.assertEqual("_SISTEMA", ruta.parent.name)
        self.assertEqual("cierre.json", ruta.name)
```

- [ ] **Paso 2: ejecutarla y ver que falla**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_cerrar_obra.TestFichaDeCierre -v
```

Se espera: `AttributeError: ... has no attribute 'escribir_cierre'`.

- [ ] **Paso 3: escribir el mínimo para que pase**

Añadir a `cerrar_obra.py` (y `from datetime import datetime` arriba):

```python
def escribir_cierre(destino: Path, estado: dict, commit) -> Path:
    """Deja dentro de la obra archivada como termino.

    Es lo que hace que cerrar no sea perder: dentro de dos anos la carpeta
    dice como acabo sin tener que bucear en el historial de git.
    """
    carpeta = Path(destino) / "_SISTEMA"
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "cierre.json"
    ruta.write_text(json.dumps({
        "obra": estado["obra"],
        "id": estado["id"],
        "fecha_cierre": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "commit_al_cerrar": commit,
        "estado_final": {
            "pct_ponderado": estado["pct"],
            "ubicaciones": estado["ubicaciones"],
            "tajos": estado["tajos"],
            "celdas": estado["celdas"],
            "desglose": estado["desglose"],
            "ultima_revision": estado["ultima_revision"],
        },
        "alfabeto": {
            "X": "terminado", "M": "mas del 50%", "/": "iniciado",
            "P": "pendiente confirmado", "?": "sin mirar", "N": "no aplica",
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta
```

- [ ] **Paso 4: ejecutar y ver que pasa**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_cerrar_obra -v
```

Se esperan 14 pruebas en verde.

- [ ] **Paso 5: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/cerrar_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_cerrar_obra.py"
git commit -m "Dejar escrito dentro de la obra archivada como termino"
```

---

### Tarea 5: Las guardas, el orquestador y la línea de órdenes

**Ficheros:**
- Modificar: `_SISTEMA.../cerrar_obra.py`
- Modificar: `_SISTEMA.../tests/test_cerrar_obra.py`

**Interfaces:**
- Consume: todo lo anterior.
- Produce: `cambios_pendientes(raiz, rutas) -> list[str]` — rutas con cambios
  sin commitear, de entre las que se le pasan.
- Produce: `cerrar(raiz, id_obra, ejecutar=False) -> dict` con las claves
  `estado`, `movida` (bool), `destino`, `adaptador`, `cierre`.
- Produce: `main(argv=None) -> int`.

La guarda mira **solo lo que el cierre va a tocar**. Una guarda de «árbol
entero limpio» bloquearía el primer uso, porque el propio `cerrar_obra.py` y
sus pruebas estarán sin publicar.

- [ ] **Paso 1: escribir la prueba que falla**

```python
class TestOrquestador(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = _obra_falsa(self.raiz)
        motor = self.raiz / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
        (motor / "adaptadores").mkdir(parents=True)
        (motor / "adaptadores" / "adaptador_falsa.py").write_text("#", encoding="utf-8")
        (motor / "registro_obras.py").write_text(
            REGISTRO_DE_JUGUETE.replace("'una'", "'falsa'")
                               .replace("2026 UNA", "2026 OBRA FALSA")
                               .replace("adaptador_una", "adaptador_falsa"),
            encoding="utf-8")
        (self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS").mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def test_sin_ejecutar_no_se_mueve_ni_un_fichero(self):
        antes = sorted(p.name for p in (self.raiz / "SAGARDE OBRAS ABIERTAS").iterdir())
        r = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=False)
        self.assertFalse(r["movida"])
        self.assertEqual(
            antes,
            sorted(p.name for p in (self.raiz / "SAGARDE OBRAS ABIERTAS").iterdir()))
        self.assertIn("falsa", cerrar_obra.ids_declarados(
            (self.raiz / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
             / "registro_obras.py").read_text(encoding="utf-8")))

    def test_al_ejecutar_deja_el_entorno_limpio(self):
        r = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        motor = self.raiz / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
        self.assertTrue(r["movida"])
        # fuera del registro
        self.assertNotIn("falsa", cerrar_obra.ids_declarados(
            (motor / "registro_obras.py").read_text(encoding="utf-8")))
        # sin adaptador huerfano
        self.assertFalse((motor / "adaptadores" / "adaptador_falsa.py").exists())
        # la carpeta, archivada, con el adaptador y el cierre dentro
        archivada = self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS" / "2026 OBRA FALSA"
        self.assertTrue((archivada / "_SISTEMA" / "adaptador_falsa.py").exists())
        self.assertTrue((archivada / "_SISTEMA" / "cierre.json").exists())

    def test_una_obra_que_no_esta_en_el_registro_aborta(self):
        with self.assertRaises(cerrar_obra.CierreAbortado):
            cerrar_obra.cerrar(self.raiz, "inexistente", ejecutar=True)

    def test_el_catalogo_de_tajos_no_se_toca(self):
        reglas = (self.raiz / "SAGARDE OBRAS ABIERTAS"
                  / "_SISTEMA INFORME SAGARDE IA" / "reglas")
        reglas.mkdir()
        catalogo = reglas / "CATALOGO_TAJOS.json"
        catalogo.write_text('{"version": "1.3"}', encoding="utf-8")
        antes = catalogo.read_bytes()
        cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertEqual(antes, catalogo.read_bytes())

    def test_con_cambios_sin_commitear_en_lo_implicado_aborta(self):
        # La guarda tiene que consultarse de verdad: una guarda declarada que
        # el codigo no mira es la familia de fallos de este proyecto.
        with patch.object(cerrar_obra, "cambios_pendientes",
                          return_value=["SAGARDE OBRAS ABIERTAS/2026 OBRA FALSA/x.pdf"]):
            with self.assertRaises(cerrar_obra.CierreAbortado):
                cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertTrue((self.raiz / "SAGARDE OBRAS ABIERTAS"
                         / "2026 OBRA FALSA").exists())

    def test_la_guarda_solo_pregunta_por_lo_que_va_a_mover(self):
        # Exigir el arbol entero limpio bloquearia el primer uso: el propio
        # cerrar_obra.py estara sin publicar la primera vez que se use.
        vistas = []

        def espia(raiz, rutas):
            vistas.append(rutas)
            return []

        with patch.object(cerrar_obra, "cambios_pendientes", espia):
            cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertEqual(1, len(vistas))
        rutas = vistas[0]
        self.assertTrue(any("2026 OBRA FALSA" in r for r in rutas))
        self.assertTrue(any("registro_obras.py" in r for r in rutas))
        self.assertTrue(any("adaptador_falsa.py" in r for r in rutas))
        self.assertEqual(3, len(rutas), "la guarda no debe mirar el arbol entero")
```

Y añadir el import arriba del fichero de pruebas:

```python
from unittest.mock import patch
```

- [ ] **Paso 2: ejecutarla y ver que falla**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_cerrar_obra.TestOrquestador -v
```

Se espera: `AttributeError: ... has no attribute 'cerrar'`.

- [ ] **Paso 3: escribir el mínimo para que pase**

Añadir a `cerrar_obra.py` (y `import argparse`, `import subprocess`, `import sys` arriba):

```python
def _registro_ruta(raiz: Path) -> Path:
    return (Path(raiz) / OBRAS_ABIERTAS / "_SISTEMA INFORME SAGARDE IA"
            / "registro_obras.py")


def _obra_del_registro(raiz: Path, id_obra: str) -> dict:
    fuente = _registro_ruta(raiz).read_text(encoding="utf-8")
    espacio: dict = {}
    exec(compile(fuente, "registro_obras.py", "exec"), espacio)
    for obra in espacio["OBRAS"]:
        if obra["id"] == id_obra:
            return obra
    raise CierreAbortado(
        f"El registro no declara ninguna obra con id '{id_obra}'. "
        f"Hay estas: {', '.join(o['id'] for o in espacio['OBRAS'])}")


def cambios_pendientes(raiz: Path, rutas: list[str]) -> list[str]:
    """Cuales de esas rutas tienen cambios sin commitear.

    Solo se mira lo que el cierre va a tocar: exigir el arbol entero limpio
    bloquearia el primer uso, porque este mismo script estara sin publicar.
    """
    try:
        salida = subprocess.run(
            ["git", "status", "--porcelain", "--"] + rutas,
            cwd=str(raiz), capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []          # sin git no se bloquea el cierre; se avisa aparte
    return [l[3:].strip().strip('"') for l in salida.stdout.splitlines() if l.strip()]


def _commit_actual(raiz: Path):
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=str(raiz), capture_output=True, text=True,
                           timeout=60)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def cerrar(raiz: Path, id_obra: str, ejecutar: bool = False) -> dict:
    """Cierra la obra. Sin `ejecutar`, solo mide y devuelve el informe."""
    raiz = Path(raiz)
    obra = _obra_del_registro(raiz, id_obra)
    carpeta = _carpeta_obra(raiz, obra)
    if not carpeta.is_dir():
        raise CierreAbortado(
            f"La obra esta en el registro pero su carpeta no existe: {carpeta}")
    destino_previsto = raiz / OBRAS_CERRADAS / obra["carpeta_obra"]
    if destino_previsto.exists():
        raise CierreAbortado(
            f"Ya hay una obra archivada con ese nombre: {destino_previsto}.")

    estado = estado_de_cierre(raiz, obra)
    resultado = {"estado": estado, "movida": False, "destino": None,
                 "adaptador": None, "cierre": None}
    if not ejecutar:
        return resultado

    implicadas = [
        f"{OBRAS_ABIERTAS}/{obra['carpeta_obra']}",
        f"{OBRAS_ABIERTAS}/_SISTEMA INFORME SAGARDE IA/registro_obras.py",
        f"{OBRAS_ABIERTAS}/_SISTEMA INFORME SAGARDE IA/adaptadores/"
        f"{obra.get('adaptador', '')}.py",
    ]
    sucias = cambios_pendientes(raiz, implicadas)
    if sucias:
        raise CierreAbortado(
            "Hay cambios sin commitear en lo que el cierre va a mover:\n  "
            + "\n  ".join(sucias)
            + "\nCommitealos o descartalos antes de cerrar la obra.")

    commit = _commit_actual(raiz)
    resultado["adaptador"] = archivar_adaptador(raiz, obra)

    registro = _registro_ruta(raiz)
    nuevo = registro_sin_obra(registro.read_text(encoding="utf-8"), id_obra)
    registro.write_text(nuevo, encoding="utf-8")

    destino = mover_a_cerradas(raiz, obra)
    resultado["destino"] = destino
    resultado["movida"] = True
    resultado["cierre"] = escribir_cierre(destino, estado, commit)
    return resultado


def _informe(estado: dict) -> str:
    orden = ("X", "M", "/", "P", "?", "N")
    desglose = " · ".join(
        f"{e}={estado['desglose'][e]}" for e in orden if estado["desglose"].get(e))
    return "\n".join([
        f"  Obra            : {estado['obra']}  (id {estado['id']})",
        f"  Carpeta         : {estado['carpeta']}",
        f"  Avance publicado: {estado['pct'] if estado['pct'] is not None else '—'}",
        f"  Ultima revision : {estado['ultima_revision'] or '—'}",
        f"  Ubicaciones     : {estado['ubicaciones'] if estado['ubicaciones'] is not None else '—'}",
        f"  Tajos           : {estado['tajos'] if estado['tajos'] is not None else '—'}",
        f"  Celdas          : {estado['celdas'] if estado['celdas'] is not None else '—'}",
        f"  Desglose        : {desglose or '—'}",
    ])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Cierra una obra y la manda a SAGARDE (OLD)/OBRAS CERRADAS.")
    parser.add_argument("id_obra", help="id de la obra en registro_obras.py")
    parser.add_argument("--ejecutar", action="store_true",
                        help="Hace el cierre. Sin esto solo informa.")
    args = parser.parse_args(argv)

    try:
        resultado = cerrar(RAIZ, args.id_obra, ejecutar=args.ejecutar)
    except CierreAbortado as err:
        print(f"[ABORTADO] {err}")
        return 1

    estado = resultado["estado"]
    print("\nAsi esta la obra ahora mismo:\n")
    print(_informe(estado))

    if not resultado["movida"]:
        print("\n  No se ha movido nada. Para cerrarla de verdad:")
        print(f"    python cerrar_obra.py {args.id_obra} --ejecutar\n")
        return 0

    print("\n  Cerrada:")
    print(f"    Carpeta archivada en : {resultado['destino']}")
    print(f"    Adaptador archivado  : {resultado['adaptador'] or 'no tenia'}")
    print(f"    Ficha de cierre      : {resultado['cierre']}")
    print("\n  Para deshacer el movimiento de la carpeta:")
    print(f'    move "{resultado["destino"]}" '
          f'"{RAIZ / OBRAS_ABIERTAS / estado["carpeta"]}"')
    print("    (y `git checkout -- registro_obras.py` para devolverla al registro)")
    print("\n  Ahora: lanza Actualizar_Sagarde.bat y comprueba que la obra ya no")
    print("  sale en resumen_obras.json, que aparece en el indice de cerradas,")
    print("  y que las dos suites siguen verdes.")
    print("  El seguimiento posterior de esta obra, si lo hay, va por postventa.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Paso 4: ejecutar y ver que pasa**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_cerrar_obra -v
```

Se esperan 20 pruebas en verde.

- [ ] **Paso 5: ejecutar la suite entera, que no haya regresión**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Se espera: OK, con 20 pruebas más que antes (308 → 328).

- [ ] **Paso 6: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/cerrar_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_cerrar_obra.py"
git commit -m "Orquestar el cierre de obra con guardas y linea de ordenes"
```

---

### Tarea 6: La skill

**Ficheros:**
- Crear: `.claude/skills/sagarde-cerrar-obra/SKILL.md`

No lleva prueba automática: es el procedimiento que rodea al script. Se
verifica leyéndolo y comprobando que los comandos que cita existen.

- [ ] **Paso 1: escribir la skill**

```markdown
---
name: sagarde-cerrar-obra
description: Cerrar una obra de Sagarde y mandarla al archivo de obras cerradas dejando el entorno limpio. Usar cuando Bixente diga que una obra ha terminado, que se cierra, que pasa a obras cerradas, o pida retirarla del panel de seguimiento.
---

# Cerrar una obra

El panel es solo para obra en curso. Cuando una obra acaba, desaparece del
seguimiento y queda como carpeta consultable en Obras cerradas. El seguimiento
posterior, si lo hay, va por **postventa**, que es otro apartado.

## Antes de tocar nada

1. **Preguntar a Bixente si la obra está realmente cerrada.** El histórico no
   lo sabe: Orueta llevaba tiempo terminada y el sistema la daba al 99.7 %.
2. Mirar el informe, que no mueve nada:

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA"
python cerrar_obra.py <id_obra>
```

3. Enseñarle ese informe —avance, última revisión y desglose `X/M///P/?/N`— y
   que confirme.

## Cerrarla

```bash
python cerrar_obra.py <id_obra> --ejecutar
```

Hace cuatro cosas: archiva el adaptador dentro de la obra, la saca de
`registro_obras.py`, mueve la carpeta a `SAGARDE (OLD)/OBRAS CERRADAS` y
escribe `_SISTEMA/cierre.json` con cómo terminó.

Aborta, sin mover nada, si la obra no está en el registro, si su carpeta no
existe, si ya hay una obra archivada con ese nombre, o si hay cambios sin
commitear en la carpeta de la obra, su adaptador o el registro.

## Después

1. Lanzar `Actualizar_Sagarde.bat` — **con la autorización de Bixente**, que
   hace `git add -A` y publica.
2. Comprobar, y reportarle el antes/después:
   - la obra ya **no** está en `resumen_obras.json`
   - **sí** aparece en el índice de obras cerradas
   - las obras que quedan **no se han movido** de avance
   - las dos suites siguen verdes:

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
cd "_SISTEMA/MOTOR" && python -m unittest discover -s tests
```

## Lo que no se toca

- **`reglas/CATALOGO_TAJOS.json`.** Los tajos propios de una obra viven ahí y
  hay pruebas que dependen de ellos. El fichero **no está en git**: si se
  estropea, no hay forma de restaurarlo.
- **El `.gitignore`.** Sus reglas de lista blanca dejan de casar solas cuando
  la carpeta se mueve, que es justo el efecto buscado.
- **Postventa.** Otro apartado.

## Si hay que deshacerlo

El script imprime el comando exacto para devolver la carpeta a su sitio. Para
devolver la obra al registro, `git checkout -- registro_obras.py` mientras no
se haya publicado.
```

- [ ] **Paso 2: comprobar que la skill se descubre**

```bash
ls .claude/skills/
```

Se espera ver `sagarde-cerrar-obra` junto a `sagarde-revision` y
`generate-cardiva-report`.

- [ ] **Paso 3: commit**

```bash
git add .claude/skills/sagarde-cerrar-obra/SKILL.md
git commit -m "Skill para cerrar una obra y archivarla"
```

---

## Al terminar

- [ ] Las dos suites en verde.
- [ ] Reflejar en el mapa mental (`_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`)
      el script nuevo en §5.2 y la skill nueva en §5.1. Lo exige el `CLAUDE.md`:
      la sesión que añade un script o una skill lo refleja en el mapa.
- [ ] **Solo entonces**, y con Orueta como primera obra real, seguir la skill.
