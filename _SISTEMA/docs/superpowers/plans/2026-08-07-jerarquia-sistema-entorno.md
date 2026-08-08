# Jerarquía `_SISTEMA` — Plan de implementación

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `superpowers:subagent-driven-development`
> para ejecutar este plan tarea a tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** separar lo informático de lo visible en todo el entorno Sagarde,
dejando en cada apartado y cada obra una única carpeta técnica `_SISTEMA`, sin
que se rompa ni una función.

**Arquitectura:** trece tareas secuenciales. Las cuatro primeras no mueven ni
un fichero: arreglan las guardas que el propio traslado destaparía y montan una
prueba-trinquete con una lista `PENDIENTES` que las tareas siguientes van
vaciando. Cuando esa lista queda vacía, la norma está aplicada y verificada.

**Herramientas:** Python 3 (stdlib), `unittest`. **No introducir pytest ni
dependencias nuevas.** Git desde el Bash tool (no está en el PATH de PowerShell).

## Restricciones globales

- **No se ejecuta `Actualizar_Sagarde.bat` en ninguna tarea.** Hace `git add -A`
  y push a `main`. Los componentes se invocan por su `.py`. Publica Bixente.
- **No se paralelizan tareas.** Todas escriben en el mismo repositorio.
- Pruebas con `unittest` de la biblioteca estándar.
- Commits pequeños, en español, explicando **por qué**.
- Al mover: `mv` de sistema de ficheros y luego `git add -A <ruta>`. El repo es
  mixto (234 ficheros rastreados de miles); `git mv` falla en los no rastreados.
- Ninguna tarea empieza si la anterior no cerró en verde.
- **Comparar el desglose `x`/`m`/`/`/vacío, no el porcentaje redondeado.**
- Reportar antes/después a Bixente en cada tarea.

## Rutas

```
RAIZ  = D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE
MOTOR = RAIZ\_MOTOR_SAGARDE                              (pasa a RAIZ\_SISTEMA\MOTOR)
OBRAS = RAIZ\SAGARDE OBRAS ABIERTAS
SIS   = OBRAS\_SISTEMA INFORME SAGARDE IA                (alias histórico, NO se renombra)
```

Suite de referencia, se ejecuta en casi todas las tareas:

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Esperado siempre: `OK`, y **nunca menos de 191 pruebas**.

---

## Tarea 0: Congelar la línea base

**Ficheros:**
- Crear: `docs/superpowers/plans/2026-08-07-linea-base.md`

**Produce:** el fichero de línea base que consultan todas las tareas siguientes.

- [ ] **Paso 1: Confirmar árbol limpio**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git status --short && git log --oneline -1
```

Esperado: sin salida en `status`; el commit es `d9ad986` o posterior.
Si hay cambios sin confirmar, **parar** y avisar a Bixente.

- [ ] **Paso 2: Suite en verde**

Ejecutar la suite de referencia. Esperado: `Ran 191 tests` … `OK`.
Anotar el número exacto.

- [ ] **Paso 3: Volcar el desglose real de las 5 obras con ficha**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python - <<'PY'
import json, glob, os, collections
base = "SAGARDE OBRAS ABIERTAS"
for f in sorted(glob.glob(os.path.join(base, "*", "INFORME SAGARDE IA", "ficha_obra.json"))):
    obra = f.split(os.sep)[1]
    d = json.load(open(f, encoding="utf-8"))
    c = collections.Counter()
    for ub in d.get("ubicaciones", []):
        for v in (ub.get("tajos") or {}).values():
            c[v if v not in (None, "") else "vacio"] += 1
    print(f"{obra:38} ubic={len(d.get('ubicaciones', [])):4}  {dict(sorted(c.items()))}")
PY
```

Si el JSON no tiene esa forma, ajustar el recorrido hasta obtener el recuento
por letra. **El recuento es el dato; el porcentaje no vale como prueba.**

- [ ] **Paso 4: Inventariar los enlaces que hoy funcionan**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python - <<'PY'
import re, os, urllib.parse
raiz = "."
rotos, ok = [], 0
for dirp, dirs, files in os.walk(raiz):
    if any(x in dirp for x in (".git", "SAGARDE (OLD)", "_PREVIEWS_WORD")):
        continue
    for fn in files:
        if not fn.endswith(".html"):
            continue
        p = os.path.join(dirp, fn)
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for href in re.findall(r'href="([^"#?:]+)"', t):
            dest = os.path.normpath(os.path.join(dirp, urllib.parse.unquote(href)))
            if os.path.exists(dest):
                ok += 1
            else:
                rotos.append(f"{p} -> {href}")
print("enlaces internos que resuelven:", ok)
print("enlaces rotos YA existentes:", len(rotos))
for r in rotos[:40]:
    print("   ", r)
PY
```

Guardar ambos números. Los enlaces ya rotos hoy no son culpa de este trabajo,
pero **el recuento no puede subir**.

- [ ] **Paso 5: Escribir la línea base y confirmar**

Volcar los resultados de los pasos 2-4 en
`docs/superpowers/plans/2026-08-07-linea-base.md`, incluyendo:
`Orueta 99.7 · Mungia 80.1 · Gernika 76.3 · Bolueta 43.5 · OBRA PRUEBA 6.4`.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add docs/superpowers/plans/2026-08-07-linea-base.md && git commit -m "Congelar la linea base antes de reordenar el entorno

Sin recuento por letra no hay forma de saber si un traslado ha movido
cifras: en Mungia, 3 celdas sobre 2309 no mueven el pct_ponderado."
```

---

## Tarea 1: `_SISTEMA` en las tres listas de ignorados

Los tres generadores construyen sus páginas recorriendo el disco. Ninguno
conoce `_SISTEMA`. **Esta tarea va antes de crear la carpeta**, no después.

**Ficheros:**
- Modificar: `_MOTOR_SAGARDE/sagarde_portal.py:19`
- Modificar: `POST-VENTAS/postventas_index.py:26`
- Modificar: `MANTENIMIENTOS/mantenimientos_index.py:32`

**Produce:** la constante `_SISTEMA` reconocida como carpeta técnica por los
tres generadores de índice.

- [ ] **Paso 1: Modificar las tres listas**

`_MOTOR_SAGARDE/sagarde_portal.py` línea 19, de:

```python
IGNORE_DIRS = {".git", ".memory", "__pycache__", "_PREVIEWS_WORD", "_MOTOR_SAGARDE"}
```

a:

```python
# "_SISTEMA" es la carpeta tecnica de cada apartado (norma del 07/08/2026).
# El portal publica como area de negocio TODO lo que encuentra: sin esta
# entrada, _SISTEMA saldria en la portada como si fuera documentacion.
IGNORE_DIRS = {".git", ".memory", "__pycache__", "_PREVIEWS_WORD",
               "_MOTOR_SAGARDE", "_SISTEMA", "docs", "scratch"}
```

`POST-VENTAS/postventas_index.py` línea 26, de:

```python
IGNORE_DIRS = {".memory", "__pycache__", PREVIEW_DIR_NAME}
```

a:

```python
IGNORE_DIRS = {".memory", "__pycache__", PREVIEW_DIR_NAME, "_SISTEMA"}
```

`MANTENIMIENTOS/mantenimientos_index.py` línea 32, de:

```python
IGNORE_DIRS = {".memory", "__pycache__"}
```

a:

```python
IGNORE_DIRS = {".memory", "__pycache__", "_SISTEMA"}
```

- [ ] **Paso 2: Crear las carpetas vacías y comprobar que NO aparecen**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && mkdir -p "_SISTEMA" "POST-VENTAS/_SISTEMA" "MANTENIMIENTOS/_SISTEMA" && python "_MOTOR_SAGARDE/sagarde_portal.py" && python "POST-VENTAS/postventas_index.py" && python "MANTENIMIENTOS/mantenimientos_index.py" && grep -c "_SISTEMA" index.html "POST-VENTAS/index.html" "MANTENIMIENTOS/index.html"
```

Esperado: `0` en los tres. Si sale distinto de 0, la guarda no ha tenido efecto.

- [ ] **Paso 3: Prueba por mutación — romper la guarda a propósito**

Quitar `"_SISTEMA"` de `IGNORE_DIRS` en `sagarde_portal.py`, poner un fichero
señuelo dentro y regenerar:

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && echo x > "_SISTEMA/señuelo.txt" && python "_MOTOR_SAGARDE/sagarde_portal.py" && grep -c "_SISTEMA" index.html
```

Esperado: **mayor que 0**. Si sigue saliendo 0, la comprobación del paso 2 no
verificaba nada y hay que rehacerla antes de continuar.

Restaurar `"_SISTEMA"` en la lista, borrar el señuelo, regenerar, confirmar `0`.

> `docs` y `scratch` entran en la lista ya en esta tarea: hoy el portal los
> publica como áreas, y la tarea 6 los mueve. Añadirlos ahora hace que la
> tarea 6 sea sólo un traslado, sin cambio de comportamiento visible.

- [ ] **Paso 4: Suite en verde**

Ejecutar la suite de referencia. Esperado: `Ran 191 tests` … `OK`.

- [ ] **Paso 5: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add "_MOTOR_SAGARDE/sagarde_portal.py" "POST-VENTAS/postventas_index.py" "MANTENIMIENTOS/mantenimientos_index.py" index.html "POST-VENTAS/index.html" "MANTENIMIENTOS/index.html" && git commit -m "Declarar _SISTEMA como carpeta tecnica en los tres generadores

Los tres construyen su indice recorriendo el disco y publican como area
de negocio todo lo que encuentran; hoy publican docs y scratch por eso.
Sin esta entrada, _SISTEMA habria salido en la portada al crearla.

La guarda se ha probado por mutacion: quitandola, la carpeta aparece."
```

---

## Tarea 2: La guarda de raíz de los dos índices de apartado

`postventas_index.py:20` y `mantenimientos_index.py:22` deducen su raíz de
`__file__`. Al mover el script a `_SISTEMA/`, la raíz pasaría a ser `_SISTEMA/`,
no encontrarían ninguna carpeta de negocio y **generarían un índice vacío
devolviendo código 0**. `Actualizar_Sagarde.bat` sólo mira `errorlevel`.

Esta tarea añade la guarda **mientras los scripts siguen en su sitio**, para
que la tarea 9 sea un traslado y no un salto de fe.

**Ficheros:**
- Modificar: `POST-VENTAS/postventas_index.py:90-96`
- Modificar: `MANTENIMIENTOS/mantenimientos_index.py:82-88`

**Consume:** nada.
**Produce:** `scan_obras()` y `scan_mantenimientos()` abortan con `SystemExit`
si el recuento de carpetas de negocio es 0.

- [ ] **Paso 1: Guarda en POST-VENTAS**

En `POST-VENTAS/postventas_index.py`, al final de `scan_obras()` (después del
bucle `for folder in ROOT.iterdir()`, antes del `return`), añadir:

```python
    # Un recuento de 0 es senal de alarma, no de "no aplica". Si este script
    # se mueve de carpeta, ROOT deja de apuntar a POST-VENTAS y el indice
    # saldria vacio con codigo de salida 0: el .bat solo mira errorlevel.
    if not obras:
        raise SystemExit(
            f"[ERROR] Ninguna carpeta de incidencias bajo {ROOT}. "
            f"Si el script se ha movido, ROOT esta mal calculado. "
            f"No se reescribe index.html con un indice vacio.")
```

- [ ] **Paso 2: Guarda en MANTENIMIENTOS**

Lo mismo al final de `scan_mantenimientos()` en
`MANTENIMIENTOS/mantenimientos_index.py`:

```python
    if not contratos:
        raise SystemExit(
            f"[ERROR] Ningun contrato de mantenimiento bajo {ROOT}. "
            f"Si el script se ha movido, ROOT esta mal calculado. "
            f"No se reescribe index.html con un indice vacio.")
```

- [ ] **Paso 3: Probar la guarda por mutación**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/POST-VENTAS" && cp postventas_index.py /tmp/pv.bak && sed -i 's|^ROOT = Path(__file__).resolve().parent$|ROOT = Path(__file__).resolve().parent / "_SISTEMA"|' postventas_index.py && python postventas_index.py; echo "codigo de salida: $?"
```

Esperado: mensaje `[ERROR] Ninguna carpeta de incidencias...` y **código
distinto de 0**. Si sale 0, la guarda no sirve.

Restaurar y confirmar que vuelve a funcionar:

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/POST-VENTAS" && cp /tmp/pv.bak postventas_index.py && python postventas_index.py; echo "codigo de salida: $?"
```

Esperado: código 0 y el índice regenerado.

**Restaurar siempre el fichero mutado.** El CLAUDE.md registra dos mutaciones
de prueba publicadas por olvidarlo.

- [ ] **Paso 4: Comprobar que los índices no han cambiado de contenido**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python "MANTENIMIENTOS/mantenimientos_index.py" && git diff --stat "POST-VENTAS/index.html" "MANTENIMIENTOS/index.html"
```

Esperado: sin cambios, o sólo la marca de fecha de generación.

- [ ] **Paso 5: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add "POST-VENTAS/postventas_index.py" "MANTENIMIENTOS/mantenimientos_index.py" && git commit -m "Abortar si el indice de apartado sale vacio

Los dos scripts deducen su raiz de __file__. Al moverlos a _SISTEMA la
raiz apuntaria a _SISTEMA, no encontrarian ninguna carpeta de negocio y
reescribirian index.html vacio devolviendo codigo 0. El .bat solo mira
errorlevel: no se habria enterado nadie.

Probado por mutacion: con ROOT mal calculado, ahora sale codigo != 0."
```

---

## Tarea 3: La guarda muerta del auditor

`auditor_sagarde.py:58` comprueba `"_SISTEMA" in f.parts`. `in f.parts` es
igualdad exacta sobre un tramo de ruta, y la carpeta real se llama
`_SISTEMA INFORME SAGARDE IA`: **esa condición no ha filtrado nunca nada.**

**Ficheros:**
- Modificar: `_MOTOR_SAGARDE/scripts/auditor_sagarde.py:55-59`

- [ ] **Paso 1: Demostrar que hoy está muerta**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python - <<'PY'
from pathlib import Path
raiz = Path(".").resolve()
n = 0
for f in (raiz / "SAGARDE OBRAS ABIERTAS").rglob("*"):
    if f.is_file() and "_SISTEMA" in f.parts:
        n += 1
print("ficheros que hoy casan con '_SISTEMA' in f.parts:", n)
PY
```

Esperado: `0`. Ese es el fallo.

- [ ] **Paso 2: Dejar la condición operativa y documentada**

En `_MOTOR_SAGARDE/scripts/auditor_sagarde.py`, sustituir la línea 58:

```python
                if "_SISTEMA" in f.parts or "INFORME SAGARDE IA" in str(f):
```

por:

```python
                # Carpetas tecnicas: la norma "_SISTEMA" (07/08/2026) y sus
                # dos alias historicos. Hasta hoy la primera condicion no
                # casaba con nada: '_SISTEMA' in f.parts es igualdad exacta
                # y la carpeta se llama '_SISTEMA INFORME SAGARDE IA'.
                # Funcionaba solo por la segunda.
                if CARPETAS_SISTEMA & set(f.parts):
                    continue
```

Y junto a las constantes de cabecera (después de la línea 29):

```python
# Carpetas tecnicas reconocidas en todo el entorno.
CARPETAS_SISTEMA = {"_SISTEMA", "_SISTEMA INFORME SAGARDE IA",
                    "INFORME SAGARDE IA"}
```

- [ ] **Paso 3: Comprobar que el diagnóstico no cambia**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && cp "_MOTOR_SAGARDE/auditoria_diagnostico.json" /tmp/audit_antes.json && python "_MOTOR_SAGARDE/scripts/auditor_sagarde.py" && python -c "
import json
a=json.load(open('/tmp/audit_antes.json',encoding='utf-8'))
b=json.load(open('_MOTOR_SAGARDE/auditoria_diagnostico.json',encoding='utf-8'))
print('IDENTICO' if a==b else 'CAMBIA -> revisar que el nuevo filtro no excluye de mas')
"
```

Esperado: `IDENTICO`. La corrección hace la guarda *equivalente*, no más
estricta: `INFORME SAGARDE IA` ya estaba cubierta por la segunda condición.

- [ ] **Paso 4: Suite en verde y commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add "_MOTOR_SAGARDE/scripts/auditor_sagarde.py" && git commit -m "Revivir la guarda de carpetas tecnicas del auditor

'_SISTEMA' in f.parts es igualdad exacta sobre un tramo de ruta, y la
carpeta se llama '_SISTEMA INFORME SAGARDE IA': esa condicion no filtro
nunca nada. La auditoria funcionaba solo por la segunda.

Se sustituye por un conjunto explicito con la norma y sus dos alias. El
diagnostico generado es identico byte a byte."
```

---

## Tarea 4: La prueba-trinquete de la norma

Una norma escrita en un `.md` que nadie ejecuta es "algo declarado que el
motor ignora en silencio". Esta prueba se escribe **ahora**, fallando, con la
lista completa de violaciones. Cada tarea siguiente vacía su parte.

**Ficheros:**
- Crear: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_jerarquia_sistema.py`

**Produce:** `PENDIENTES`, la lista que las tareas 5-11 van vaciando y que la
tarea 12 deja a cero.

> **Ejecutada el 08/08/2026. El código de abajo NO es el que quedó**, y el
> fichero real manda. Escrito tal cual, fallaba las dos pruebas y el inventario
> era erróneo en tres puntos:
>
> 1. **`EXT_TECNICAS` con `.bak` y `.log` metía 30 ficheros de AutoCAD en la
>    misma bolsa que el código**: 17 `.bak` con cabecera `AC1027` (el respaldo
>    del unifilar, junto a su `.dwg`) y 13 `plot.log` (qué plano se imprimió,
>    cuándo y en qué impresora). Eso es dato de obra. Decisión de Bixente: se
>    estrecha la regla a `_es_tecnico()` — `.bak` solo cuenta si el nombre
>    delata que respalda código, `.log` no cuenta nunca.
> 2. **El plan nunca inventarió `APP_CARDIVA`**: sus 3 `.ps1` salían como
>    violaciones no declaradas. Decisión de Bixente: excepción permanente, como
>    los subproyectos de `VARIOS`. El `CLAUDE.md` declara canónica la ruta
>    `APP_CARDIVA/skills/generate-cardiva-report` y `sync_cardiva_skill_agents.ps1`
>    depende de ella: moverlos rompe la skill.
> 3. **`VARIOS/plot.log` era un fantasma por contradicción del propio plan**:
>    `VARIOS` está en `EXCEPCIONES`, así que su subárbol nunca se recorre y esa
>    entrada no podía aparecer jamás. Fuera, junto a la de `SAGARDE OBRAS
>    ABIERTAS`.
>
> Resultado: `PENDIENTES` queda en **24 entradas**, no 26, y cuadra exactamente
> con las 24 violaciones en disco.

- [ ] **Paso 1: Escribir la prueba**

```python
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
    "__pycache__",         # se comprueba aparte, como carpeta
}

EXT_TECNICAS = {".py", ".bat", ".cmd", ".ps1", ".bak", ".log"}

# Excepciones permanentes. Cada una es una decision, no un descuido.
EXCEPCIONES = {
    # Bixente lo quiere a la vista en la raiz: es el boton que pulsa.
    "Actualizar_Sagarde.bat",
    # VARIOS/APPS SAGARDE, TIERRAS, BATERIAS y MANUALES son subproyectos con
    # su propia raiz y su propio .claude. Reordenarlos es un trabajo aparte,
    # declarado fuera de alcance en la spec del 07/08/2026.
    "VARIOS",
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
        for d in dirnames:
            if d == "__pycache__":
                malas.append(os.path.join(rel, d).replace("\\", "/"))
        for fn in filenames:
            if fn in EXCEPCIONES:
                continue
            if os.path.splitext(fn)[1].lower() in EXT_TECNICAS:
                r = fn if rel == "." else os.path.join(rel, fn)
                malas.append(r.replace("\\", "/"))
    return sorted(malas)


# Violaciones conocidas al escribir el plan. Se vacian tarea a tarea.
PENDIENTES = {
    # tarea 5 (raiz, riesgo nulo)
    "SAGARDE OBRAS ABIERTAS/plot.log",
    "VARIOS/plot.log",
    "_MOTOR_SAGARDE/sagarde_portal.py.ANTES_FASE3_MANTENIMIENTOS_20260725.bak",
    "_MOTOR_SAGARDE/sagarde_portal.py.ANTES_FIX_APPS_DUPLICADOS_20260725.bak",
    "_MOTOR_SAGARDE/sagarde_portal.py.ANTES_MEJORA_ALERTAS_20260725.bak",
    "MANTENIMIENTOS/__pycache__",
    "POST-VENTAS/__pycache__",
    "_MOTOR_SAGARDE/__pycache__",
    "_MOTOR_SAGARDE/scripts/__pycache__",
    "_MOTOR_SAGARDE/tests/__pycache__",
    # tarea 6 (raiz con referencias)
    "Servidor_Local.bat",
    "ABRIR_CLAUDE_SAGARDE.cmd",
    "ABRIR_GEMINI_SAGARDE.cmd",
    # tarea 8 (_MOTOR_SAGARDE -> _SISTEMA/MOTOR)
    "_MOTOR_SAGARDE/avisos.py",
    "_MOTOR_SAGARDE/sagarde_portal.py",
    "_MOTOR_SAGARDE/scripts/auditor_sagarde.py",
    "_MOTOR_SAGARDE/scripts/generar_informe_ejecutivo.py",
    "_MOTOR_SAGARDE/scripts/generar_parte_incidencia.py",
    "_MOTOR_SAGARDE/scripts/regenerar_obra.py",
    "_MOTOR_SAGARDE/scripts/validar_revision_pdf.py",
    "_MOTOR_SAGARDE/tests/__init__.py",
    "_MOTOR_SAGARDE/tests/test_avisos.py",
    # tarea 9 (POST-VENTAS)
    "POST-VENTAS/Actualizar_Postventas.bat",
    "POST-VENTAS/postventas_index.py",
    "POST-VENTAS/postventas_sync.py",
    # tarea 10 (MANTENIMIENTOS)
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
```

- [ ] **Paso 2: Ejecutar y comprobar que PASA con la lista llena**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_jerarquia_sistema -v
```

Esperado: 2 pruebas, `OK`. Si `test_no_hay_violaciones_nuevas` falla, la lista
`PENDIENTES` está incompleta: **añadir lo que falte y anotarlo**, porque
significa que el inventario del plan se dejó algo.

Si `test_pendientes_no_caduca` falla, hay entradas que no existen: corregirlas.

- [ ] **Paso 3: Probar por mutación que detecta algo nuevo**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && echo "print(1)" > "APLICACIONES/colado.py" && cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_jerarquia_sistema 2>&1 | tail -5
```

Esperado: **FALLA** citando `APLICACIONES/colado.py`.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && rm "APLICACIONES/colado.py"
```

- [ ] **Paso 4: Suite completa y commit**

Ejecutar la suite de referencia. Esperado: `Ran 200 tests` … `OK` (198 + 2).
Son 198 y no 191 porque la Tarea 3 movió su regresión del auditor a esta misma
suite, sumando 7.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_jerarquia_sistema.py" && git commit -m "Prueba-trinquete de la norma de jerarquia

Una norma escrita en un .md que nadie ejecuta es exactamente la familia
de fallos de este proyecto: algo declarado que el motor ignora.

PENDIENTES arranca con las 26 violaciones conocidas y cada tarea del plan
borra las suyas. La segunda prueba impide que la lista se llene de
fantasmas y deje de avisar."
```

---

## Tarea 5: Lo que no referencia nadie

Comprobado en la exploración: ningún `.py`, `.bat`, `.cmd`, `.ps1`, `.html`,
`.js`, `.json` ni `.md` del entorno menciona estos ficheros.

> **Corregido el 08/08/2026, al ejecutar la Tarea 4.** Dos cosas de este
> apartado estaban mal y se arreglan aquí:
>
> 1. **Los `plot.log` salen del alcance.** Son registros de impresión de
>    AutoCAD (plano, impresora, fecha, escala), no informática. Decisión de
>    Bixente: la norma no los cubre. Ya no se mueven ni figuran en
>    `PENDIENTES`.
> 2. **Mover los 3 `.bak` a `_MOTOR_SAGARDE/_bak/` no los saca de la norma.**
>    `_MOTOR_SAGARDE` no es una carpeta `_SISTEMA`, así que seguirían siendo
>    violaciones en una ruta nueva y sin declarar: la prueba fallaría. Sus
>    entradas de `PENDIENTES` se **actualizan a la ruta nueva**, no se borran;
>    las absorbe la Tarea 8 al mover `_MOTOR_SAGARDE` dentro de `_SISTEMA`.
> 3. **El trinquete deja de auditar `__pycache__`** (visto al ejecutar esta
>    tarea: la suite pasó a fallar sola). Nadie escribe un `__pycache__` —
>    Python lo genera junto al `.py` que importa, y la propia suite regeneraba
>    `_MOTOR_SAGARDE/__pycache__` al terminar. La prueba pasaba en un árbol
>    limpio y fallaba justo después de correrla; declararlo en `PENDIENTES`
>    fallaría al revés en una máquina que no la hubiera ejecutado. Su
>    ubicación es una consecuencia automática de dónde esté el código, que es
>    lo que la prueba ya gobierna. Se limpia como mantenimiento y lo cubre
>    `.gitignore`, no el trinquete.

**Ficheros:**
- Mover: 7 PNG de la raíz → `_SISTEMA/capturas/`
- Mover: 3 `.bak` → `_MOTOR_SAGARDE/_bak/`
- Borrar: 9 `__pycache__`, `PARA SOBREESCRIBIR/`
- Modificar: `tests/test_jerarquia_sistema.py` (5 `__pycache__` fuera, 3 `.bak`
  reapuntados)

- [ ] **Paso 1: Verificar de nuevo que nadie los referencia**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && for f in bol_p2.png bol_p6.png bol_p6_zoom.png mun_contactos.png mun_p2_mec.png mun_p3_cm.png mun_planta1.png plot.log; do n=$(grep -rIl --exclude-dir=.git --exclude-dir="SAGARDE (OLD)" --exclude-dir=_PREVIEWS_WORD -F "$f" . 2>/dev/null | wc -l); echo "$f -> $n referencias"; done
```

Esperado: `0` en todos. Si alguno sale distinto de 0, **parar** y tratarlo como
la tarea 6, no como riesgo nulo.

- [ ] **Paso 2: Mover**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && mkdir -p "_SISTEMA/capturas" "_MOTOR_SAGARDE/_bak" && mv bol_p2.png bol_p6.png bol_p6_zoom.png mun_contactos.png mun_p2_mec.png mun_p3_cm.png mun_planta1.png "_SISTEMA/capturas/" && mv _MOTOR_SAGARDE/*.bak "_MOTOR_SAGARDE/_bak/" && ls "_SISTEMA/capturas" | wc -l
```

Esperado: `7`.

- [ ] **Paso 3: Borrar cachés y la carpeta vacía**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && find . -path ./.git -prune -o -name __pycache__ -type d -print -exec rm -rf {} + 2>/dev/null; rmdir "PARA SOBREESCRIBIR" && echo "PARA SOBREESCRIBIR eliminada"
```

Si `rmdir` falla, la carpeta **no estaba vacía**: parar, listar el contenido y
preguntar a Bixente. No usar `rm -rf` sobre ella.

- [ ] **Paso 4: Actualizar PENDIENTES**

En `tests/test_jerarquia_sistema.py`, bloque `# tarea 5` (8 entradas):

- **Borrar** las 5 de `__pycache__`: dejan de existir.
- **Reapuntar** las 3 de `.bak` a `_MOTOR_SAGARDE/_bak/…`: siguen fuera de una
  carpeta `_SISTEMA` hasta la Tarea 8. Mover el comentario a `# tarea 8`, que
  es la que de verdad las resuelve.

- [ ] **Paso 5: Verificar**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Esperado: `Ran 200 tests` … `OK`. Comprobar además que `PENDIENTES` y las
violaciones en disco siguen cuadrando exactamente: si `test_pendientes_no_caduca`
falla, algún `.bak` se reapuntó mal.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python "_MOTOR_SAGARDE/sagarde_portal.py" && git diff --stat index.html
```

Esperado: sin cambios salvo la fecha de generación. Las 7 capturas no salían
en el portal y no deben salir ahora desde `_SISTEMA`.

- [ ] **Paso 6: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git commit -m "Recoger de la raiz lo que no referencia nadie

7 capturas de depuracion del lector de hojas (Bolueta y Mungia), 2
plot.log, 3 copias .bak de sagarde_portal.py anteriores a tenerlo en git,
9 __pycache__ y PARA SOBREESCRIBIR, que estaba vacia.

Verificado antes de mover: cero referencias en todo el entorno."
```

---

## Tarea 6: Los tres lanzadores de la raíz

**Ficheros:**
- Mover: `Servidor_Local.bat`, `ABRIR_CLAUDE_SAGARDE.cmd`, `ABRIR_GEMINI_SAGARDE.cmd` → `_SISTEMA/`
- Modificar: los tres, para que suban un nivel antes de trabajar
- Modificar: `docs/SAGARDE_ENTORNO_IA_Y_SKILLS.md:75-76`
- Modificar: `tests/test_jerarquia_sistema.py`

- [ ] **Paso 1: Mover y corregir el `cd`**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && mv Servidor_Local.bat ABRIR_CLAUDE_SAGARDE.cmd ABRIR_GEMINI_SAGARDE.cmd "_SISTEMA/"
```

En los tres, sustituir `cd /d "%~dp0"` por:

```bat
rem El fichero vive en _SISTEMA\ pero opera sobre la raiz del entorno.
cd /d "%~dp0.."
```

- [ ] **Paso 2: Probar que el servidor local sigue sirviendo la raíz**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/_SISTEMA" && (python -m http.server 8099 --directory .. &) && sleep 2 && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8099/index.html && curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8099/POST-VENTAS/index.html"; pkill -f "http.server 8099"
```

Esperado: `200` en ambos. Confirma que servir desde `%~dp0..` alcanza la raíz.

- [ ] **Paso 3: Actualizar la documentación**

En `docs/SAGARDE_ENTORNO_IA_Y_SKILLS.md`, líneas 75-76, poner las rutas nuevas
`_SISTEMA\ABRIR_CLAUDE_SAGARDE.cmd` y `_SISTEMA\ABRIR_GEMINI_SAGARDE.cmd`.

- [ ] **Paso 4: Vaciar sus 3 entradas de PENDIENTES, suite y commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Esperado: `Ran 193 tests` … `OK`.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git commit -m "Recoger los tres lanzadores en _SISTEMA

Servidor_Local.bat y los dos ABRIR_*.cmd hacian cd al directorio del
propio fichero; desde _SISTEMA eso ya no es la raiz del entorno, asi que
pasan a 'cd /d \"%~dp0..\"'.

Comprobado sirviendo la raiz por HTTP desde la ubicacion nueva: index.html
y POST-VENTAS/index.html responden 200."
```

---

## Tarea 7: `PORTAL SAGARDE.html`, `docs/` y `scratch/`

`PORTAL SAGARDE.html` **lo genera** `sagarde_portal.py:571`. No se edita a
mano: se cambia el destino en el `.py` y se regenera.

**Ficheros:**
- Modificar: `_MOTOR_SAGARDE/sagarde_portal.py:571`
- Mover: `PORTAL SAGARDE.html`, `docs/`, `scratch/` → `_SISTEMA/`
- Modificar: `.gitignore:49-50`
- Modificar: `CLAUDE.md:190,241`, `GEMINI.md:18`
- Modificar: `tests/test_jerarquia_sistema.py`

- [ ] **Paso 1: Cambiar el destino en el generador**

`_MOTOR_SAGARDE/sagarde_portal.py` línea 571, de:

```python
    output = ROOT / "PORTAL SAGARDE.html"
```

a:

```python
    # Norma _SISTEMA (07/08/2026): el portal movil es una vista generada,
    # no un documento que Bixente abra desde la raiz.
    output = ROOT / "_SISTEMA" / "PORTAL SAGARDE.html"
```

- [ ] **Paso 2: Localizar el enlace desde la portada**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && grep -n "PORTAL SAGARDE" "_MOTOR_SAGARDE/sagarde_portal.py"
```

Corregir toda construcción de `href` hacia `PORTAL SAGARDE.html` para que
apunte a `_SISTEMA/PORTAL%20SAGARDE.html`.

- [ ] **Paso 3: Mover las tres cosas**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && rm -f "PORTAL SAGARDE.html" && mv docs scratch "_SISTEMA/" && ls "_SISTEMA"
```

- [ ] **Paso 4: Corregir `.gitignore`**

Líneas 49-50, de:

```
!docs/superpowers/specs/*.md
!docs/superpowers/plans/*.md
```

a:

```
!_SISTEMA/docs/superpowers/specs/*.md
!_SISTEMA/docs/superpowers/plans/*.md
```

- [ ] **Paso 5: Comprobar que los planes SIGUEN rastreados**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git ls-files "_SISTEMA/docs/superpowers" | wc -l
```

Esperado: **mayor que 0**. Si sale `0`, la lista blanca del `.gitignore` no
alcanza la ruta nueva y la documentación de diseño dejaría de publicarse en
silencio. Es el fallo del commit selectivo, ya registrado en memoria.

- [ ] **Paso 6: Corregir las referencias en CLAUDE.md y GEMINI.md**

`CLAUDE.md` líneas 190 y 241, `GEMINI.md` línea 18: cambiar `docs/` por
`_SISTEMA/docs/`.

- [ ] **Paso 7: Regenerar y verificar**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python "_MOTOR_SAGARDE/sagarde_portal.py" && test -f "_SISTEMA/PORTAL SAGARDE.html" && echo "portal movil OK" && grep -c 'href="docs/"' index.html; grep -c 'href="scratch/"' index.html
```

Esperado: el fichero existe; ambos `grep` dan `0`. Las tarjetas de `docs` y
`scratch` desaparecen de la portada — **es el efecto buscado**. Comprobar en el
recuento de áreas que no ha desaparecido **ninguna más**.

- [ ] **Paso 8: Recuento de enlaces rotos**

Repetir el script del paso 4 de la tarea 0. El número de enlaces rotos **no
puede haber subido** respecto a la línea base.

- [ ] **Paso 9: Vaciar PENDIENTES, suite y commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Esperado: `Ran 193 tests` … `OK`.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git commit -m "Recoger el portal movil, docs y scratch en _SISTEMA

PORTAL SAGARDE.html lo genera sagarde_portal.py:571, asi que se cambia el
destino en el .py y se regenera: editarlo a mano no habria durado hasta
el siguiente Actualizar_Sagarde.

docs y scratch salian como areas de negocio en la portada por el barrido
del portal; ya no. .gitignore pasa a permitir _SISTEMA/docs/superpowers:
comprobado con git ls-files que las specs siguen rastreadas, que es
justo lo que se pierde en silencio cuando cambia una ruta."
```

---

## Tarea 8: `_MOTOR_SAGARDE` → `_SISTEMA/MOTOR`

La tarea más delicada de la raíz: ocho ficheros calculan rutas contra ella.

**Ficheros:**
- Mover: `_MOTOR_SAGARDE/` → `_SISTEMA/MOTOR/`
- Modificar: `Actualizar_Sagarde.bat:16,38`
- Modificar: `_SISTEMA/MOTOR/sagarde_portal.py:17`
- Modificar: `_SISTEMA/MOTOR/scripts/auditor_sagarde.py:27-28`
- Modificar: `MANTENIMIENTOS/mantenimientos_index.py:23`
- Modificar: `SIS/generar_todos.py:29`
- Modificar: `SIS/tests/test_registro_obras.py:11`
- Modificar (comentarios): `SIS/lector_hoja_tajos_pdf.py:29`, `SIS/adaptadores/adaptador_mungia.py:177`

- [ ] **Paso 1: Inventariar TODAS las referencias antes de mover**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && grep -rn --exclude-dir=.git --exclude-dir="SAGARDE (OLD)" --exclude-dir=_PREVIEWS_WORD -F "_MOTOR_SAGARDE" . | grep -v "^./_MOTOR_SAGARDE/_bak/"
```

Guardar la lista completa. Al final de la tarea, este mismo comando sólo puede
devolver líneas dentro de documentación histórica.

- [ ] **Paso 2: Mover**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && mv _MOTOR_SAGARDE "_SISTEMA/MOTOR" && ls "_SISTEMA/MOTOR"
```

- [ ] **Paso 3: Corregir el cálculo de raíz de los dos scripts movidos**

`_SISTEMA/MOTOR/sagarde_portal.py` línea 17, de:

```python
ROOT = Path(__file__).resolve().parent.parent
```

a:

```python
# _SISTEMA/MOTOR/sagarde_portal.py -> tres niveles hasta la raiz del entorno.
ROOT = Path(__file__).resolve().parent.parent.parent
```

`_SISTEMA/MOTOR/scripts/auditor_sagarde.py` líneas 27-28, de:

```python
ROOT = Path(__file__).resolve().parent.parent.parent
MOTOR_DIR = ROOT / "_MOTOR_SAGARDE"
```

a:

```python
# _SISTEMA/MOTOR/scripts/auditor_sagarde.py -> cuatro niveles hasta la raiz.
ROOT = Path(__file__).resolve().parent.parent.parent.parent
MOTOR_DIR = ROOT / "_SISTEMA" / "MOTOR"
```

- [ ] **Paso 4: Comprobar que ROOT apunta de verdad a la raíz**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python -c "
import sys; sys.path.insert(0,'_SISTEMA/MOTOR')
import sagarde_portal as s
print('ROOT   =', s.ROOT)
print('OUTPUT =', s.OUTPUT)
assert s.OUTPUT.name == 'index.html'
assert (s.ROOT / 'SAGARDE OBRAS ABIERTAS').is_dir(), 'ROOT NO es la raiz'
print('OK')
"
```

Esperado: `OK`. Un `ROOT` mal calculado aquí generaría el portal en el sitio
equivocado sin dar error.

- [ ] **Paso 5: Corregir los cuatro consumidores**

`Actualizar_Sagarde.bat` líneas 16 y 38:

```bat
%PY% "_SISTEMA\MOTOR\scripts\auditor_sagarde.py"
%PY% "_SISTEMA\MOTOR\sagarde_portal.py"
```

Y la línea 95, que cita la ruta del `Actualizar_Obras.bat`: dejarla como está,
esa carpeta no se mueve.

`MANTENIMIENTOS/mantenimientos_index.py` línea 23:

```python
MOTOR_DIR = ROOT.parent / "_SISTEMA" / "MOTOR"
```

`SIS/generar_todos.py` línea 29:

```python
sys.path.insert(0, os.path.join(ROOT_DIR, "_SISTEMA", "MOTOR", "scripts"))
```

`SIS/tests/test_registro_obras.py` línea 11:

```python
sys.path.insert(0, os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'scripts'))
```

**No te fíes de esta lista: búscalos.** Hay más de un fichero de prueba con
ese `sys.path.insert` (la tarea 3 añadió `SIS/tests/test_auditor_sagarde.py`
con el mismo patrón). Antes de dar el paso por terminado:

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && grep -rn "_MOTOR_SAGARDE" --include=*.py --include=*.bat --include=*.cmd . | grep -v "^./_SISTEMA/MOTOR/_bak/"
```

Tiene que devolver **cero líneas de código** — sólo comentarios o
documentación histórica, si acaso.

Y los dos comentarios: `SIS/lector_hoja_tajos_pdf.py:29` y
`SIS/adaptadores/adaptador_mungia.py:177`, donde dicen
`_MOTOR_SAGARDE/CLAUDE.md`, poner `_SISTEMA/MOTOR/CLAUDE.md`.

- [ ] **Paso 6: Ejecutar la cadena completa**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python "_SISTEMA/MOTOR/scripts/auditor_sagarde.py" && python "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py" --no-pdf && python "POST-VENTAS/postventas_index.py" && python "MANTENIMIENTOS/mantenimientos_index.py" && python "_SISTEMA/MOTOR/sagarde_portal.py" && echo "CADENA COMPLETA OK"
```

Esperado: `CADENA COMPLETA OK`, sin trazas de error.

- [ ] **Paso 7: Comparar el desglose contra la línea base**

Repetir el script del paso 3 de la tarea 0. El recuento por letra de las 5
obras con ficha debe salir **idéntico**. Si cambia una sola celda, parar.

- [ ] **Paso 8: Suite, PENDIENTES y commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Esperado: `Ran 193 tests` … `OK`.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git commit -m "Mover el motor a _SISTEMA/MOTOR

Ocho ficheros calculaban rutas contra _MOTOR_SAGARDE. Los dos scripts que
viven dentro deducen su raiz de __file__ y necesitan un nivel mas; un
ROOT mal calculado aqui habria generado el portal en otro sitio sin dar
error, asi que se comprueba con un assert de que ROOT ve la carpeta de
obras.

Verificado el desglose x/m//-vacio de las 5 obras con ficha: identico."
```

---

## Tarea 9: Ocultar lo que no puede moverse

Nueve elementos de la raíz están anclados por requisitos de herramienta.

**Ficheros:** ninguno se mueve ni se edita. Sólo cambia un atributo.

- [ ] **Paso 1: Ocultar**

```powershell
Set-Location "D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE"
foreach ($n in @('.gitignore','.nojekyll','CLAUDE.md','GEMINI.md','.claudeignore','.claude','.gemini','.agents','.superpowers')) {
  if (Test-Path $n) { (Get-Item $n -Force).Attributes = (Get-Item $n -Force).Attributes -bor [IO.FileAttributes]::Hidden; "oculto: $n" }
  else { "NO EXISTE: $n" }
}
```

Y las carpetas de herramienta anidadas en subproyectos de `VARIOS`:

```powershell
Set-Location "D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE"
Get-ChildItem -Path "VARIOS" -Filter ".claude" -Directory -Recurse -Force | ForEach-Object {
  $_.Attributes = $_.Attributes -bor [IO.FileAttributes]::Hidden; "oculto: $($_.FullName)"
}
```

- [ ] **Paso 2: Comprobar que git y Python los siguen leyendo**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git status --short | head -5 && echo "(git lee .gitignore: si no hubiera, saldrian miles de lineas)" && git ls-files ".claude/skills" | wc -l && test -f .nojekyll && echo ".nojekyll presente"
```

Esperado: `git status` corto (la lista blanca sigue activa); las skills siguen
rastreadas; `.nojekyll` presente.

- [ ] **Paso 3: Comprobar la raíz visible**

```powershell
Set-Location "D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE"
Get-ChildItem | Select-Object -ExpandProperty Name
```

Esperado, exactamente: `APLICACIONES`, `MANTENIMIENTOS`, `POST-VENTAS`,
`SAGARDE (OLD)`, `SAGARDE OBRAS ABIERTAS`, `VARIOS`, `_SISTEMA`,
`Actualizar_Sagarde.bat`, `index.html`.

- [ ] **Paso 4: Documentar cómo se revierte, y commit**

Añadir al final de `_SISTEMA/docs/SAGARDE_ENTORNO_IA_Y_SKILLS.md` el comando
para volver a hacerlos visibles (`-bxor` en lugar de `-bor`).

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git commit -m "Ocultar los nueve elementos anclados a la raiz

.gitignore, .nojekyll, CLAUDE.md, GEMINI.md, .claudeignore y las cuatro
carpetas de configuracion de las IA no pueden moverse: git y las tres
herramientas las buscan en la raiz del proyecto. Se les pone el atributo
oculto de Windows en vez de moverlas: no se desplaza un byte y es
reversible con un comando, que queda documentado."
```

---

## Tarea 10: POST-VENTAS

La guarda de la tarea 2 ya está puesta. Ahora se mueve.

**Ficheros:**
- Mover a `POST-VENTAS/_SISTEMA/`: `postventas_index.py`, `postventas_sync.py`,
  `postventas_resumen.json`, `Actualizar_Postventas.bat`, `.memory/`, `_PREVIEWS_WORD/`
- Modificar: `postventas_index.py` (ROOT, PREVIEW_DIR), `Actualizar_Postventas.bat`
- Modificar: `_SISTEMA/MOTOR/sagarde_portal.py:50`
- Modificar: `.claudeignore`

- [ ] **Paso 1: Mover**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/POST-VENTAS" && mkdir -p _SISTEMA && mv postventas_index.py postventas_sync.py postventas_resumen.json Actualizar_Postventas.bat .memory _PREVIEWS_WORD _SISTEMA/ && ls
```

Esperado: sólo las 31 carpetas `INCIDENCIAS *`, `index.html`,
`logo_sagarde.jpg`, los dos `.docx`, `citas postventa.docx`, el fichero
`INCIDENCIAS` de 0 bytes y `_SISTEMA`.

> `logo_sagarde.jpg` **no se mueve**: lo referencian todas las páginas
> generadas como `../POST-VENTAS/logo_sagarde.jpg` y está en la lista blanca
> del `.gitignore:14`.

- [ ] **Paso 2: Corregir ROOT y la ruta de previews**

`POST-VENTAS/_SISTEMA/postventas_index.py` líneas 20-24, de:

```python
ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "index.html"
RESUMEN_JSON = ROOT / "postventas_resumen.json"
PREVIEW_DIR_NAME = "_PREVIEWS_WORD"
PREVIEW_DIR = ROOT / PREVIEW_DIR_NAME
```

a:

```python
# El script vive en POST-VENTAS/_SISTEMA/ pero ROOT es POST-VENTAS: es la
# carpeta que recorre. Si esto queda mal, scan_obras aborta (guarda del
# 07/08/2026) en vez de escribir un index.html vacio.
SISTEMA_DIR = Path(__file__).resolve().parent
ROOT = SISTEMA_DIR.parent
INDEX_PATH = ROOT / "index.html"
RESUMEN_JSON = SISTEMA_DIR / "postventas_resumen.json"
PREVIEW_DIR_NAME = "_PREVIEWS_WORD"
PREVIEW_DIR = SISTEMA_DIR / PREVIEW_DIR_NAME
```

- [ ] **Paso 3: Comprobar que los enlaces a los previews siguen resolviendo**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/POST-VENTAS" && grep -n "_PREVIEWS_WORD" _SISTEMA/postventas_index.py
```

Toda construcción de `href` hacia un preview debe llevar ahora el prefijo
`_SISTEMA/`, porque `index.html` sigue en `POST-VENTAS/` y el preview ha bajado
un nivel. Corregir donde haga falta.

- [ ] **Paso 4: Corregir el `.bat` y el portal**

`POST-VENTAS/_SISTEMA/Actualizar_Postventas.bat`: el `cd /d "%~dp0"` **se queda
como está** — el script Python está ahora en esa misma carpeta, así que
`%PY% postventas_index.py` sigue resolviendo. Lo único que cambia es la última
línea, porque el índice que abre subió un nivel:

```bat
start "" "..\index.html"
```

`_SISTEMA/MOTOR/sagarde_portal.py` línea 50:

```python
RESUMEN_POSTVENTAS_JSON = ROOT / "POST-VENTAS" / "_SISTEMA" / "postventas_resumen.json"
```

`.claudeignore`: cambiar `POST-VENTAS/_PREVIEWS_WORD/` por
`POST-VENTAS/_SISTEMA/_PREVIEWS_WORD/`.

- [ ] **Paso 5: Regenerar y comparar recuentos, no apariencia**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && cp "POST-VENTAS/index.html" /tmp/pv_antes.html && python "POST-VENTAS/_SISTEMA/postventas_index.py"; echo "codigo: $?" && python - <<'PY'
import re
a = open('/tmp/pv_antes.html', encoding='utf-8').read()
b = open('POST-VENTAS/index.html', encoding='utf-8').read()
for nom, t in (('antes', a), ('despues', b)):
    print(nom, 'obras:', len(re.findall(r'INCIDENCIAS', t)), ' enlaces:', len(re.findall(r'href="', t)))
PY
```

Esperado: los dos recuentos **iguales**. Un índice vacío es el fallo que
persigue este plan: comprobar el número, no que la página "se vea bien".

- [ ] **Paso 6: Enlaces rotos, PENDIENTES, suite y commit**

Repetir el recuento de enlaces rotos de la tarea 0. No puede subir.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python "_SISTEMA/MOTOR/sagarde_portal.py" && cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Esperado: `Ran 193 tests` … `OK`.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git commit -m "Recoger la maquinaria de post-ventas en POST-VENTAS/_SISTEMA

Dos scripts, el resumen JSON, el .bat, .memory y los 88 previews Word
generados. En POST-VENTAS quedan las 31 carpetas de incidencias, su
index.html y los documentos que Bixente abre.

ROOT del indice pasa a ser el padre del script, no su carpeta. La guarda
del 07/08/2026 aborta si el recuento sale 0. Verificado que el numero de
obras y de enlaces del index es el mismo que antes de mover.

logo_sagarde.jpg se queda: lo referencian todas las paginas generadas."
```

---

## Tarea 11: MANTENIMIENTOS

**Ficheros:**
- Mover a `MANTENIMIENTOS/_SISTEMA/`: `mantenimientos_index.py`,
  `mantenimientos_resumen.json`
- Modificar: `mantenimientos_index.py` (ROOT, MOTOR_DIR, RESUMEN_JSON)
- Modificar: `_SISTEMA/MOTOR/sagarde_portal.py:152` **y su fallback**
- Modificar: `Actualizar_Sagarde.bat:31`

> **Aviso descubierto en la revisión de la tarea 1 — léelo antes de mover nada.**
>
> `sagarde_portal.py:152` hace:
> ```python
> json_path = ROOT / "MANTENIMIENTOS" / "mantenimientos_resumen.json"
> ```
> Al mover ese JSON a `_SISTEMA/`, `json_path.is_file()` da falso y el código
> **cae a un fallback** (≈ línea 176) que itera `base.iterdir()` **sin aplicar
> `IGNORE_DIRS` ni ningún filtro**: publicaría `_SISTEMA` como un contrato de
> mantenimiento más. Y el `except Exception: pass` de la línea 172 se traga
> cualquier error por el camino, así que degradaría en silencio.
>
> Hay que corregir **las dos cosas**: la ruta de la línea 152 y el filtro del
> fallback. Y comprobar que el fallback funciona, forzándolo (renombrando el
> JSON un momento) en vez de suponerlo.
>
> **Además:** dos generadores escriben `MANTENIMIENTOS/index.html` —
> `mantenimientos_index.py:262` con plantilla `card` y
> `sagarde_portal.py:443` con plantilla `pv-list`. Como el `.bat` ejecuta el
> portal en último lugar, **la plantilla `card` no ha llegado nunca a verse**
> desde que se escribió el 27/07. Los datos son idénticos en ambas; sólo
> cambia el aspecto. Qué plantilla debe ganar lo decide Bixente: preguntar
> antes de tocar, y no borrar ninguna de las dos por iniciativa propia.

- [ ] **Paso 1: Mover**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/MANTENIMIENTOS" && mkdir -p _SISTEMA && mv mantenimientos_index.py mantenimientos_resumen.json _SISTEMA/ && ls
```

Esperado: las 4 carpetas `MANTENIMIENTO *`, `index.html`,
`MANTENIMIENTO typo.docx` y `_SISTEMA`.

- [ ] **Paso 2: Corregir las rutas**

`MANTENIMIENTOS/_SISTEMA/mantenimientos_index.py` líneas 22-30, de:

```python
ROOT = Path(__file__).resolve().parent
MOTOR_DIR = ROOT.parent / "_SISTEMA" / "MOTOR"
...
INDEX_PATH = ROOT / "index.html"
RESUMEN_JSON = ROOT / "mantenimientos_resumen.json"
```

a:

```python
# El script vive en MANTENIMIENTOS/_SISTEMA/ pero ROOT es MANTENIMIENTOS.
SISTEMA_DIR = Path(__file__).resolve().parent
ROOT = SISTEMA_DIR.parent
MOTOR_DIR = ROOT.parent / "_SISTEMA" / "MOTOR"
...
INDEX_PATH = ROOT / "index.html"
RESUMEN_JSON = SISTEMA_DIR / "mantenimientos_resumen.json"
```

`Actualizar_Sagarde.bat` línea 31:

```bat
%PY% "MANTENIMIENTOS\_SISTEMA\mantenimientos_index.py"
```

Y la línea 27, que ya apunta a post-ventas:

```bat
%PY% "POST-VENTAS\_SISTEMA\postventas_index.py"
```

- [ ] **Paso 3: Comprobar que sigue encontrando el motor y los 4 contratos**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && cp "MANTENIMIENTOS/index.html" /tmp/mant_antes.html && python "MANTENIMIENTOS/_SISTEMA/mantenimientos_index.py"; echo "codigo: $?" && python - <<'PY'
import re
a = open('/tmp/mant_antes.html', encoding='utf-8').read()
b = open('MANTENIMIENTOS/index.html', encoding='utf-8').read()
for nom, t in (('antes', a), ('despues', b)):
    print(nom, 'contratos:', len(re.findall(r'MANTENIMIENTO ', t)))
PY
```

Esperado: mismo recuento, y código 0. El `import avisos` viene de `MOTOR_DIR`:
si esa ruta está mal, el script revienta con `ModuleNotFoundError` — un fallo
ruidoso, que es el bueno.

- [ ] **Paso 4: PENDIENTES, suite y commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Esperado: `Ran 193 tests` … `OK`. `PENDIENTES` queda **vacía**: borrar también
el comentario y dejar `PENDIENTES = set()`.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git commit -m "Recoger la maquinaria de mantenimientos y vaciar PENDIENTES

Ultimo apartado con scripts sueltos. Actualizar_Sagarde.bat pasa a
llamar a los dos indices por su ruta nueva.

Con esto PENDIENTES queda a cero: la prueba-trinquete ya no tolera ningun
fichero tecnico fuera de una carpeta _SISTEMA."
```

---

## Tarea 12: Los sidecars dentro de las obras

**El punto más peligroso del plan.** `generar_todos.py:68` busca las
correcciones con `glob(carpeta/'REVISIONES'/'*.correcciones.json')`. Si los
sidecars se mueven sin tocar ese glob, devuelve `{}` y **las marcas a boli
desaparecen**: Bolueta y Mungia caerían a los valores crudos del adaptador.
Es la línea "corrección X→M revertida por el motor, 22 celdas por revisión"
del CLAUDE.md, repetida.

**Ficheros:**
- Modificar: `SIS/generar_todos.py:68-70`
- Modificar: `SIS/leer_hoja_marcada.py:448-452,527`
- Modificar: `.gitignore:45-46`
- Mover: 14 sidecars + 3 carpetas `.recortes` a `<obra>/REVISIONES*/\_SISTEMA/`

- [ ] **Paso 1: Ampliar el glob ANTES de mover, aceptando las dos ubicaciones**

`SIS/generar_todos.py`, en `_correcciones_mas_recientes`, sustituir:

```python
    patron = os.path.join(carpeta_abs, 'REVISIONES', '*.correcciones.json')
    ficheros = glob.glob(patron) + glob.glob(
        os.path.join(carpeta_abs, 'REVISIONES SAGARDE', '*.correcciones.json'))
```

por:

```python
    # Norma _SISTEMA (07/08/2026): los sidecars viven en REVISIONES*/_SISTEMA/.
    # Se siguen aceptando los sueltos en REVISIONES* por si queda alguno de
    # antes: perder un .correcciones.json es perder marcas escritas a boli,
    # el dato mas directo que hay.
    ficheros = []
    for carpeta_rev in ('REVISIONES', 'REVISIONES SAGARDE'):
        ficheros += glob.glob(
            os.path.join(carpeta_abs, carpeta_rev, '*.correcciones.json'))
        ficheros += glob.glob(
            os.path.join(carpeta_abs, carpeta_rev, '_SISTEMA',
                         '*.correcciones.json'))
```

- [ ] **Paso 2: Comprobar que con el glob nuevo NADA cambia todavía**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py" --no-pdf
```

Después, repetir el script del paso 3 de la tarea 0: desglose **idéntico** a la
línea base. Los sidecars todavía no se han movido; si algo cambia aquí, el
glob nuevo está mal escrito.

- [ ] **Paso 3: Mover los sidecars**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS" && for obra in "2025 BILBAO OBISPO ORUETA" "2026 BOLUETA ACR" "2026 MUNGIA ACR NEINOR" "2026 OBRA PRUEBA"; do for rev in "REVISIONES" "REVISIONES SAGARDE"; do d="$obra/$rev"; [ -d "$d" ] || continue; mkdir -p "$d/_SISTEMA"; find "$d" -maxdepth 1 \( -name "*.candidatas.json" -o -name "*.clasificacion.json" -o -name "*.correcciones.json" -o -name "*.recortes" \) -exec mv {} "$d/_SISTEMA/" \; ; done; done; find . -maxdepth 3 -name "_SISTEMA" -path "*REVISION*" -exec sh -c 'echo "$1: $(ls "$1" | wc -l) elementos"' _ {} \;
```

Esperado: 4 carpetas `_SISTEMA` con 1, 4, 5 y 4 elementos respectivamente.

- [ ] **Paso 4: LA PRUEBA QUE IMPORTA — el desglose no se mueve**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py" --no-pdf
```

Repetir el script del paso 3 de la tarea 0. El recuento por letra de las 5
obras **tiene que ser idéntico** al de la línea base, y los porcentajes seguir
en `Orueta 99.7 · Mungia 80.1 · Gernika 76.3 · Bolueta 43.5 · OBRA PRUEBA 6.4`.

**Si Bolueta o Mungia bajan, el glob no está encontrando los sidecars: revertir
el movimiento y arreglarlo antes de seguir.**

- [ ] **Paso 5: Prueba por mutación del glob**

Quitar temporalmente la rama `_SISTEMA` del glob y regenerar. Bolueta y Mungia
**tienen que bajar**. Si no bajan, el paso 4 no estaba probando nada.
Restaurar el glob y volver a comprobar que suben.

- [ ] **Paso 6: Corregir el lector para que escriba en la ubicación nueva**

`SIS/leer_hoja_marcada.py`, sustituir las líneas 448-452:

```python
    base = os.path.splitext(args.hoja)[0]
    ruta_candidatas = base + '.candidatas.json'

    if args.preparar:
        recortes = base + '.recortes'
```

por:

```python
    # Norma _SISTEMA (07/08/2026): la traza tecnica de una hoja no se mezcla
    # con los DOCX y PDF de revision que Bixente abre.
    dir_sistema = os.path.join(os.path.dirname(args.hoja), '_SISTEMA')
    os.makedirs(dir_sistema, exist_ok=True)
    base = os.path.join(dir_sistema,
                        os.path.splitext(os.path.basename(args.hoja))[0])
    ruta_candidatas = base + '.candidatas.json'

    if args.preparar:
        recortes = base + '.recortes'
```

Y la línea 527:

```python
    sidecar = base + os.path.splitext(args.hoja)[1] + '.correcciones.json'
```

- [ ] **Paso 7: Reproducir una hoja ya procesada**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python leer_hoja_marcada.py "../2026 BOLUETA ACR/REVISIONES/REVISION BOLUETA 26072026.pdf" bolueta --preparar
```

Esperado: escribe en `REVISIONES/_SISTEMA/` y el recuento de candidatas
coincide con el `.candidatas.json` que ya estaba. Comparar:

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/REVISIONES/_SISTEMA" && python -c "
import json
d = json.load(open('REVISION BOLUETA 26072026.candidatas.json', encoding='utf-8'))
print('candidatas:', len(d['candidatas']))
"
```

Si el número no coincide con el de antes, **parar**: el lector está leyendo la
rejilla de otra manera.

- [ ] **Paso 8: `.gitignore`**

Líneas 45-46, de:

```
!SAGARDE OBRAS ABIERTAS/*/REVISIONES*/*.correcciones.json
!SAGARDE OBRAS ABIERTAS/*/REVISIONES*/*.clasificacion.json
```

a:

```
!SAGARDE OBRAS ABIERTAS/*/REVISIONES*/_SISTEMA/*.correcciones.json
!SAGARDE OBRAS ABIERTAS/*/REVISIONES*/_SISTEMA/*.clasificacion.json
```

Comprobar que siguen rastreados:

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git ls-files "SAGARDE OBRAS ABIERTAS/*/REVISIONES*/_SISTEMA/*.json" | wc -l
```

Esperado: **mayor que 0**.

- [ ] **Paso 9: Suite y commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Esperado: `Ran 193 tests` … `OK`.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git commit -m "Separar la traza tecnica de las hojas de los DOCX de revision

14 sidecars y 3 carpetas .recortes (319 archivos) pasan a
REVISIONES*/_SISTEMA/. En REVISIONES quedan los DOCX y PDF que Bixente
abre.

El glob de _correcciones_mas_recientes se amplio ANTES de mover y se
probo por mutacion: sin la rama _SISTEMA, Bolueta y Mungia caen a los
valores crudos del adaptador. Perder un .correcciones.json es perder
marcas escritas a boli.

Verificado el desglose x/m//-vacio de las 5 obras: identico a la linea
base, y reproducida con --preparar una hoja ya procesada."
```

---

## Tarea 13: La norma escrita y la verificación final

**Ficheros:**
- Modificar: `CLAUDE.md` (sección nueva)
- Modificar: `GEMINI.md`
- Modificar: `_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`,
  `SAGARDE_GLOSARIO_OPERATIVO.md`, `SAGARDE_ENTORNO_IA_Y_SKILLS.md`
- Modificar: `tests/test_jerarquia_sistema.py` (comprobar `PENDIENTES` vacía)

- [ ] **Paso 1: La norma en CLAUDE.md**

Añadir una sección numerada, después de la §7 «Datos de obra»:

```markdown
## 8. Jerarquía de carpetas: la norma `_SISTEMA`

**Cada apartado y cada obra tiene como mucho una carpeta técnica, llamada
`_SISTEMA`. Dentro va todo lo informático. Fuera queda sólo lo que abriría
una persona.** (Norma del 07/08/2026, permanente.)

Es informático: `.py`, `.bat`, `.cmd`, `.ps1`, `__pycache__`, `.bak`, `.log`,
JSON de trabajo del motor, HTML de preview generado, memorias `.memory`,
capturas de depuración, documentación técnica.

No lo es: DOCX y PDF de revisión, planos, fotos, XLSX de materiales,
catálogos, el `index.html` de navegación y los paneles de obra.

**Dos alias históricos**, que ya implementan la norma con otro nombre y **no
se renombran**: `_SISTEMA INFORME SAGARDE IA` (el motor de obras) e
`INFORME SAGARDE IA` (dentro de cada obra; sus `panel.html` están publicados
y renombrarlos rompería las URL del móvil).

**Nueve elementos de la raíz están anclados** por requisitos de herramienta y
sólo se ocultan, nunca se mueven: `.gitignore`, `.nojekyll`, `CLAUDE.md`,
`GEMINI.md`, `.claudeignore`, `.claude\`, `.gemini\`, `.agents\`,
`.superpowers\`. Lo mismo con las `.claude\` de los subproyectos de `VARIOS`.

La norma **se comprueba sola**: `tests/test_jerarquia_sistema.py` falla si
aparece un fichero técnico fuera de una carpeta `_SISTEMA`. Las excepciones
viven en la lista `EXCEPCIONES` de esa prueba, con su razón escrita al lado.
Un fichero nuevo que no cumpla la norma no llega a `main`.

**Al crear una obra o un apartado nuevo**, su carpeta técnica se llama
`_SISTEMA`. Al añadir un script, va dentro de una. Si un generador recorre el
disco, `_SISTEMA` tiene que estar en su lista de ignorados **antes** de que
la carpeta exista.
```

- [ ] **Paso 2: Reflejarla en GEMINI.md y en los tres documentos de `docs/`**

En `GEMINI.md`, un párrafo remitiendo a la §8 del CLAUDE.md. En
`SAGARDE_MAPA_MENTAL_ENTORNO.md` y `SAGARDE_GLOSARIO_OPERATIVO.md`, actualizar
los árboles de carpetas que hoy citan `_MOTOR_SAGARDE`, `docs/` y `scratch/`
en la raíz.

- [ ] **Paso 3: Cerrar el trinquete**

En `tests/test_jerarquia_sistema.py`, comprobar que `PENDIENTES = set()` y
añadir una tercera prueba:

```python
    def test_la_norma_esta_aplicada(self):
        """PENDIENTES vacia: no queda deuda de la reordenacion del 07/08/2026."""
        self.assertEqual(
            PENDIENTES, set(),
            "Quedan violaciones declaradas sin resolver: la reordenacion "
            "no esta terminada.")
```

- [ ] **Paso 4: Verificación completa de punta a punta**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python "_SISTEMA/MOTOR/scripts/auditor_sagarde.py" && python "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py" --no-pdf && python "POST-VENTAS/_SISTEMA/postventas_index.py" && python "MANTENIMIENTOS/_SISTEMA/mantenimientos_index.py" && python "_SISTEMA/MOTOR/sagarde_portal.py" && cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Esperado: la cadena entera sin error y `Ran 194 tests` … `OK`.

- [ ] **Paso 5: Comparación final contra la línea base**

Repetir los pasos 3 y 4 de la tarea 0:
- desglose por letra de las 5 obras: **idéntico**
- enlaces rotos: **no ha subido** respecto a la línea base
- `Orueta 99.7 · Mungia 80.1 · Gernika 76.3 · Bolueta 43.5 · OBRA PRUEBA 6.4`

- [ ] **Paso 6: Comprobar la raíz visible una última vez**

```powershell
Set-Location "D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE"; Get-ChildItem | Select-Object -ExpandProperty Name
```

Esperado: 9 nombres, ni uno más.

- [ ] **Paso 7: Commit final y reporte a Bixente**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A . && git commit -m "Fijar la norma _SISTEMA como permanente

La jerarquia queda escrita en CLAUDE.md §8, en GEMINI.md y en los tres
documentos de docs/, y comprobada por test_jerarquia_sistema.py, que
falla si aparece un fichero tecnico fuera de una carpeta _SISTEMA.

Escribirla solo en un .md la habria dejado en 'algo declarado que el
motor ignora en silencio', que es la familia de fallos de este proyecto."
```

Reportar a Bixente: raíz antes (19 elementos) / después (9), desglose de las 5
obras sin cambios, 194 pruebas en verde, y **que falta su `Actualizar_Sagarde.bat`
para publicar**.

- [ ] **Paso 8: Guardar en memoria**

Escribir la norma en la memoria del proyecto y enlazarla desde `MEMORY.md`.

---

## Notas sobre lo que queda fuera

- `SAGARDE (OLD)\` — 17.000 ficheros, 46 GB. No se toca.
- Los subproyectos de `VARIOS\` (APPS SAGARDE, TIERRAS, BATERÍAS, MANUALES)
  tienen su propia raíz y su propio `.claude`. Declarados en `EXCEPCIONES`.
- El fichero `INCIDENCIAS` de 0 bytes en POST-VENTAS: se reporta, no se borra.
- La suite escribe un PDF real en `2026 MUNGIA ACR NEINOR\INFORME SAGARDE IA\`.
  Reportado en la spec §8; no se corrige aquí.
