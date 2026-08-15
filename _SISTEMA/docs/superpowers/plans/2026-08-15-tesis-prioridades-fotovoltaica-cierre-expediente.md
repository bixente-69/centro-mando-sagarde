# Fotovoltaica + Cierre de expediente Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Nota de este proyecto:** en Sagarde la programación la ejecuta Codex, no
> Claude. Cada tarea de este plan tiene un prompt autocontenido equivalente
> en el mensaje de chat que acompaña a este fichero — pégalo en Codex tarea
> por tarea, revisa el resultado (ejecuta los tests indicados) antes de pasar
> a la siguiente. No pegues dos tareas a la vez: comparten `panel_obra.py` y
> `generar_todos.py`, y el CLAUDE.md de este proyecto prohíbe paralelizar
> trabajo sobre los mismos ficheros.

**Goal:** Añadir el tajo `fotovoltaica` al catálogo común y construir un
"cierre de expediente" (ensayos, OCA, CIE/Boletín, Libro del Edificio) por
obra, separado de la rejilla de revisiones, visible en el panel y en el
informe ejecutivo.

**Architecture:** Dos piezas independientes. (1) Una entrada más en
`CATALOGO_TAJOS.json`, sin dependencias — el priorizador ya es genérico y no
necesita código nuevo para clasificarla. (2) Un módulo nuevo,
`cierre_expediente.py`, que lee/escribe un JSON pequeño por obra al margen de
`ficha_obra.json`; `panel_obra.py` y `generar_informe_ejecutivo.py` lo leen
para renderizar una pestaña y una sección de PDF respectivamente;
`generar_todos.py` los conecta.

**Tech Stack:** Python 3 estándar (sin dependencias nuevas), `unittest`,
ReportLab (ya en uso) para el PDF.

## Global Constraints

- Nada de este cambio toca `generador_revisiones.html` ni la rejilla
  ubicaciones×tajos: el cierre de expediente es dato de obra, no un tajo
  revisable semana a semana (restricción explícita de Bixente).
- No se toca la lógica de `deps`/`minimo` de `priorizador_trabajos.py`: ya es
  correcta (ver spec, hallazgos 1 y 2).
- `reglas/CATALOGO_TAJOS.json` no está en git: cuidado al editarlo, no hay
  `git checkout` que lo recupere si algo sale mal.
- Pruebas con `unittest` de la biblioteca estándar. Sin pytest ni
  dependencias nuevas.
- Commits pequeños, uno por tarea, mensaje explicando el porqué.
- Todas las pruebas de esta plan se ejecutan desde
  `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/` con
  `python -m unittest tests.<modulo> -v`, salvo que se indique otra ruta.
- Spec de referencia:
  `_SISTEMA/docs/superpowers/specs/2026-08-15-tesis-prioridades-instalacion-electrica-design.md`.

---

### Task 1: Catálogo — nuevo tajo Fotovoltaica

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/reglas/CATALOGO_TAJOS.json`
- Test: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_catalogo_tajos.py`

**Interfaces:**
- Produces: tajo `"fotovoltaica"` en `CATALOGO_TAJOS.json` con
  `propiedad="propio"`, `ambito="edificio"`, `orden=306`, `deps=[]`. Las
  tareas 2, 4 y 5 dan por hecho que este tajo existe con esta forma exacta.

- [ ] **Step 1: Escribir el test que falla**

Abre `tests/test_catalogo_tajos.py` y añade este método dentro de la clase
`TestCatalogoTajosConfirmado`, como último método antes del cierre de la
clase (antes de la línea `if __name__ == '__main__':`):

```python
    def test_fotovoltaica_existe_como_tajo_propio_sin_dependencia(self):
        tajo = self.tajos.get('fotovoltaica')
        self.assertIsNotNone(
            tajo, "falta el tajo 'fotovoltaica' en el catálogo común")
        self.assertEqual(tajo['propiedad'], 'propio')
        self.assertEqual(tajo['ambito'], 'edificio')
        self.assertEqual(tajo['orden'], 306)
        self.assertEqual(tajo['deps'], [])
        self.assertIn('Fotovoltaica', tajo['aliases'])
```

- [ ] **Step 2: Confirmar que falla**

Run: `python -m unittest tests.test_catalogo_tajos -v`
Expected: `FAIL` — `test_fotovoltaica_existe_como_tajo_propio_sin_dependencia`
falla porque `self.tajos.get('fotovoltaica')` es `None`.

- [ ] **Step 3: Añadir el tajo al catálogo**

Abre `reglas/CATALOGO_TAJOS.json`. Busca el objeto cuyo `"id"` es
`"fachada_terminada"` (tiene `"orden": 305`). Justo después de su `}` de
cierre (y de la coma que lo separa del siguiente elemento del array
`"tajos"`), inserta este objeto completo, antes del objeto
`"agujeros_iluminacion_zzcc"`:

```json
    {
      "id": "fotovoltaica",
      "nombre": "Fotovoltaica",
      "aliases": [
        "Fotovoltaica",
        "FV",
        "Placas solares"
      ],
      "propiedad": "propio",
      "ambito": "edificio",
      "orden": 306,
      "fase": "Cubierta",
      "deps": [],
      "estado_m": "Más del 50 %",
      "estado_x": "Instalación fotovoltaica terminada",
      "impacto": "Se ejecuta cuando procede la cubierta; no espera a ningún otro tajo y nada espera a él, igual que Cuarto técnico."
    },
```

Guarda y valida que el fichero sigue siendo JSON válido:

Run: `python -c "import json; json.load(open('reglas/CATALOGO_TAJOS.json', encoding='utf-8'))"`
Expected: sin salida, sin traceback (exit code 0).

- [ ] **Step 4: Confirmar que pasa, y que no rompe nada más**

Run: `python -m unittest tests.test_catalogo_tajos tests.test_catalogo_invariantes -v`
Expected: `OK`, todos los tests en verde — incluidos los 5 de
`test_catalogo_invariantes.py` (orden único, dependencias existentes,
alias sin colisión, mínimos válidos), que ahora también recorren
`fotovoltaica` automáticamente.

- [ ] **Step 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/reglas/CATALOGO_TAJOS.json" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_catalogo_tajos.py"
git commit -m "Catalogo: nuevo tajo Fotovoltaica, sin dependencia a proposito"
```

---

### Task 2: Priorizador — verificar que Fotovoltaica se clasifica como cualquier tajo propio

**Files:**
- Create: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_prioridades_fotovoltaica.py`

**Interfaces:**
- Consumes: `fixtures.ficha_minima()` (en `tests/fixtures.py`, ya existe),
  `priorizador_trabajos.priorizar_ficha(ficha, obra="")` → dict con clave
  `detalle_items`, cada item con `tarea_id` y `categoria`.
- No modifica ningún fichero de producción: esta tarea es solo la prueba que
  demuestra que el Task 1 ya basta (el priorizador es genérico, no hace
  falta código específico por tajo — ver spec, "Contraste realizado").

- [ ] **Step 1: Escribir el test (ya en verde, sin necesitar más código)**

Crea el fichero completo:

```python
# -*- coding: utf-8 -*-
"""Fotovoltaica no lleva codigo propio en el priorizador: al ser un tajo
'propio' sin dependencias, tiene que comportarse igual que cualquier otro
tajo de esa forma. Esta prueba demuestra que el catalogo (Task 1) basta,
sin tocar priorizador_trabajos.py."""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import fixtures
from priorizador_trabajos import priorizar_ficha


def _ficha_con_fotovoltaica(estado):
    ficha = fixtures.ficha_minima()
    ficha['tajos']['aplicables'].append('fotovoltaica')
    ficha['tajos']['detalle'].append({
        'id': 'fotovoltaica', 'nombre': 'Fotovoltaica',
    })
    ficha['estados'] = {
        'p1__pb__fotovoltaica__A': {'v': estado, 'f': '15/08/2026', 'r': 1},
    }
    ficha['revisiones'] = [{'fecha': '15/08/2026', 'numero': 1}]
    return ficha


class TestFotovoltaicaEnPriorizador(unittest.TestCase):

    def test_sin_marca_sale_viable_no_bloqueada(self):
        ficha = _ficha_con_fotovoltaica('')
        resultado = priorizar_ficha(ficha, obra='OBRA DE PRUEBAS')
        items = [i for i in resultado['detalle_items']
                 if i['tarea_id'] == 'fotovoltaica']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['categoria'], 'VIABLE')

    def test_en_x_se_computa_terminado(self):
        ficha = _ficha_con_fotovoltaica('X')
        resultado = priorizar_ficha(ficha, obra='OBRA DE PRUEBAS')
        items = [i for i in resultado['detalle_items']
                 if i['tarea_id'] == 'fotovoltaica']
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['categoria'], 'TERMINADO')

    def test_sembrar_reglas_rellena_orden_y_ambito_desde_el_catalogo(self):
        ficha = _ficha_con_fotovoltaica('')
        priorizar_ficha(ficha, obra='OBRA DE PRUEBAS')
        detalle = ficha['tajos']['detalle']
        tajo = next(t for t in detalle if t['id'] == 'fotovoltaica')
        self.assertEqual(tajo['orden'], 306)
        self.assertEqual(tajo['ambito'], 'edificio')
        self.assertEqual(tajo['deps'], [])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Ejecutar y confirmar que pasa (requiere el Task 1 ya aplicado)**

Run: `python -m unittest tests.test_prioridades_fotovoltaica -v`
Expected: `OK`, 3 tests en verde. Si falla con `KeyError` o categoría
distinta de `VIABLE`/`TERMINADO`, el Task 1 no se aplicó correctamente —
revisar antes de continuar, no ajustar este test para que pase.

- [ ] **Step 3: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_prioridades_fotovoltaica.py"
git commit -m "Prioridades: demostrar que Fotovoltaica no necesita codigo propio"
```

---

### Task 3: Módulo `cierre_expediente.py`

**Files:**
- Create: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/cierre_expediente.py`
- Test: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_cierre_expediente.py`

**Interfaces:**
- Produces (usado por las Tasks 4, 5, 6):
  - `HITOS_ORDEN: tuple[str, ...]` — 4 ids en orden de presentación.
  - `HITOS_NOMBRE: dict[str, str]` — id → etiqueta legible.
  - `ESTADOS_POR_HITO: dict[str, tuple[str, ...]]` — estados válidos por hito.
  - `vacio(obra: str = "") -> dict` — estructura por defecto, todo pendiente.
  - `cargar(ruta_json: str, obra: str = "") -> tuple[dict, list[str]]` —
    nunca lanza excepción; devuelve `(datos, avisos)`.
  - `guardar(ruta_json: str, datos: dict) -> None`.
  - `actualizar_hito(ruta_json, obra, hito, estado, fecha=None, nota="") -> dict`
    — lanza `ValueError` si `hito` o `estado` no son válidos.
  - `main()` — CLI: `python cierre_expediente.py <obra> --hito <id> --estado <valor> [--fecha DD/MM/AAAA] [--nota "..."]`.

- [ ] **Step 1: Escribir las pruebas que fallan**

Crea el fichero completo:

```python
# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import cierre_expediente as ce


class TestCierreExpedienteVacioYCarga(unittest.TestCase):

    def test_vacio_tiene_los_cuatro_hitos_en_pendiente(self):
        datos = ce.vacio('OBRA X')
        self.assertEqual(set(datos['hitos']), set(ce.HITOS_ORDEN))
        for hito in ce.HITOS_ORDEN:
            self.assertEqual(datos['hitos'][hito]['estado'], 'pendiente')

    def test_cargar_fichero_ausente_no_lanza_y_devuelve_vacio(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'no_existe', 'cierre_expediente.json')
            datos, avisos = ce.cargar(ruta, obra='OBRA X')
            self.assertEqual(avisos, [])
            self.assertEqual(datos['hitos']['ensayos_instrumentales']['estado'],
                              'pendiente')

    def test_cargar_json_corrupto_no_lanza_y_avisa(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'cierre_expediente.json')
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write('{ esto no es json valido')
            datos, avisos = ce.cargar(ruta, obra='OBRA X')
            self.assertTrue(avisos)
            self.assertEqual(datos['hitos']['inspeccion_oca']['estado'],
                              'pendiente')

    def test_cargar_estado_no_reconocido_avisa_pero_conserva_el_dato(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'cierre_expediente.json')
            with open(ruta, 'w', encoding='utf-8') as f:
                json.dump({
                    'obra': 'OBRA X', 'actualizado': '15/08/2026',
                    'hitos': {'inspeccion_oca': {
                        'estado': 'valor_raro', 'fecha': '01/01/2026', 'nota': ''}},
                }, f)
            datos, avisos = ce.cargar(ruta, obra='OBRA X')
            self.assertTrue(any('valor_raro' in a for a in avisos))
            self.assertEqual(
                datos['hitos']['inspeccion_oca']['estado'], 'valor_raro')

    def test_guardar_y_recargar_conserva_los_datos(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'sub', 'cierre_expediente.json')
            datos = ce.vacio('OBRA X')
            datos['hitos']['cie_boletin'] = {
                'estado': 'hecho', 'fecha': '10/08/2026', 'nota': 'ok'}
            ce.guardar(ruta, datos)
            recargado, avisos = ce.cargar(ruta, obra='OBRA X')
            self.assertEqual(avisos, [])
            self.assertEqual(recargado['hitos']['cie_boletin']['estado'], 'hecho')
            self.assertEqual(recargado['hitos']['cie_boletin']['fecha'], '10/08/2026')


class TestActualizarHito(unittest.TestCase):

    def test_actualizar_hito_valido_escribe_y_devuelve_los_datos(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'cierre_expediente.json')
            datos = ce.actualizar_hito(
                ruta, 'OBRA X', 'libro_edificio', 'hecho',
                fecha='12/08/2026', nota='entregado en mano')
            self.assertEqual(datos['hitos']['libro_edificio']['estado'], 'hecho')
            self.assertTrue(os.path.isfile(ruta))

    def test_actualizar_hito_desconocido_lanza_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'cierre_expediente.json')
            with self.assertRaises(ValueError):
                ce.actualizar_hito(ruta, 'OBRA X', 'hito_que_no_existe', 'hecho')

    def test_actualizar_estado_no_valido_para_ese_hito_lanza_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'cierre_expediente.json')
            with self.assertRaises(ValueError):
                ce.actualizar_hito(ruta, 'OBRA X', 'cie_boletin', 'favorable')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Confirmar que fallan (el módulo no existe todavía)**

Run: `python -m unittest tests.test_cierre_expediente -v`
Expected: `ERROR` — `ModuleNotFoundError: No module named 'cierre_expediente'`.

- [ ] **Step 3: Escribir el módulo**

Crea el fichero completo:

```python
# -*- coding: utf-8 -*-
"""Cierre de expediente: ensayos, OCA, CIE/Boletin y Libro del Edificio.

Datos de obra a mano, al margen de la rejilla ubicaciones x tajos. No lo
toca ningun adaptador, no lo siembra sembrar_reglas, no lo lee el generador
de hojas ni el priorizador. Panel e informe ejecutivo lo leen para mostrar
el cierre administrativo de la obra, no su avance fisico.
"""
from datetime import datetime
import argparse
import json
import os

HITOS_ORDEN = (
    "ensayos_instrumentales",
    "inspeccion_oca",
    "cie_boletin",
    "libro_edificio",
)

HITOS_NOMBRE = {
    "ensayos_instrumentales": "Ensayos instrumentales",
    "inspeccion_oca": "Inspección OCA",
    "cie_boletin": "CIE / Boletín eléctrico",
    "libro_edificio": "Libro del Edificio",
}

ESTADOS_POR_HITO = {
    "ensayos_instrumentales": ("pendiente", "hecho", "no_aplica"),
    "inspeccion_oca": ("pendiente", "favorable", "condicionada", "negativa", "no_aplica"),
    "cie_boletin": ("pendiente", "hecho", "no_aplica"),
    "libro_edificio": ("pendiente", "hecho", "no_aplica"),
}


def _hito_vacio():
    return {"estado": "pendiente", "fecha": None, "nota": ""}


def vacio(obra=""):
    return {
        "obra": obra,
        "actualizado": None,
        "hitos": {h: _hito_vacio() for h in HITOS_ORDEN},
    }


def cargar(ruta_json, obra=""):
    """Lee cierre_expediente.json. Nunca lanza: fichero ausente o corrupto
    se trata como "sin datos todavia", con un aviso legible en el segundo
    valor devuelto. No se inventa ni se corrige un estado desconocido: se
    conserva tal cual y se avisa, para no ocultar un dato raro."""
    avisos = []
    base = vacio(obra)
    if not os.path.isfile(ruta_json):
        return base, avisos

    try:
        with open(ruta_json, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError) as e:
        avisos.append(
            f"cierre_expediente.json no se pudo leer ({e}); se trata como sin datos.")
        return base, avisos

    if not isinstance(datos, dict):
        avisos.append(
            "cierre_expediente.json no tiene la forma esperada (no es un "
            "objeto); se trata como sin datos.")
        return base, avisos

    base["obra"] = datos.get("obra") or obra
    base["actualizado"] = datos.get("actualizado")
    hitos_guardados = datos.get("hitos")
    if not isinstance(hitos_guardados, dict):
        avisos.append(
            "cierre_expediente.json: 'hitos' no es un objeto; se trata como sin datos.")
        return base, avisos

    for clave, valor in hitos_guardados.items():
        if clave not in ESTADOS_POR_HITO:
            avisos.append(f"cierre_expediente.json: hito desconocido '{clave}', se ignora.")
            continue
        if not isinstance(valor, dict):
            avisos.append(
                f"cierre_expediente.json: el hito '{clave}' no tiene la forma "
                f"esperada, se ignora.")
            continue
        estado = valor.get("estado", "pendiente")
        if estado not in ESTADOS_POR_HITO[clave]:
            avisos.append(
                f"cierre_expediente.json: '{clave}' tiene un estado no "
                f"reconocido ('{estado}'); revisar a mano.")
        base["hitos"][clave] = {
            "estado": estado,
            "fecha": valor.get("fecha"),
            "nota": valor.get("nota", ""),
        }
    return base, avisos


def guardar(ruta_json, datos):
    directorio = os.path.dirname(ruta_json)
    if directorio:
        os.makedirs(directorio, exist_ok=True)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def actualizar_hito(ruta_json, obra, hito, estado, fecha=None, nota=""):
    """Cambia un hito y guarda. Lanza ValueError si el hito o el estado no
    son validos: es una accion explicita de quien lo llama, no una lectura
    pasiva, asi que aqui si conviene fallar alto en vez de avisar y seguir."""
    if hito not in ESTADOS_POR_HITO:
        raise ValueError(
            f"hito desconocido: {hito!r}. Validos: {', '.join(HITOS_ORDEN)}")
    if estado not in ESTADOS_POR_HITO[hito]:
        raise ValueError(
            f"estado {estado!r} no valido para {hito!r}. "
            f"Validos: {', '.join(ESTADOS_POR_HITO[hito])}")
    datos, _avisos = cargar(ruta_json, obra=obra)
    datos["obra"] = obra or datos.get("obra", "")
    datos["hitos"][hito] = {"estado": estado, "fecha": fecha, "nota": nota}
    datos["actualizado"] = datetime.now().strftime("%d/%m/%Y")
    guardar(ruta_json, datos)
    return datos


def main():
    from registro_obras import resolver_obra

    parser = argparse.ArgumentParser(
        description="Actualiza un hito de cierre de expediente de una obra.")
    parser.add_argument("obra", help="nombre oficial o alias de la obra (registro_obras.py)")
    parser.add_argument("--hito", required=True, choices=HITOS_ORDEN)
    parser.add_argument("--estado", required=True)
    parser.add_argument("--fecha", default=None, help="DD/MM/AAAA")
    parser.add_argument("--nota", default="")
    args = parser.parse_args()

    obra = resolver_obra(args.obra)
    if obra is None:
        print(f"[ERROR] No hay obra registrada con el nombre '{args.obra}'.")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    obras_abiertas_dir = os.path.dirname(base_dir)
    carpeta_abs = os.path.join(obras_abiertas_dir, obra["carpeta_obra"])
    ruta_json = os.path.join(carpeta_abs, "INFORME SAGARDE IA", "cierre_expediente.json")

    try:
        datos = actualizar_hito(
            ruta_json, obra["nombre"], args.hito, args.estado,
            fecha=args.fecha, nota=args.nota)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return

    print(f"[OK] {HITOS_NOMBRE[args.hito]} -> {args.estado} ({obra['nombre']})")
    print(json.dumps(datos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Confirmar que las pruebas pasan**

Run: `python -m unittest tests.test_cierre_expediente -v`
Expected: `OK`, 8 tests en verde.

- [ ] **Step 5: Probar el CLI a mano contra una carpeta temporal (no una obra real)**

Run:
```bash
python -c "
import tempfile, os, cierre_expediente as ce
with tempfile.TemporaryDirectory() as tmp:
    ruta = os.path.join(tmp, 'cierre_expediente.json')
    ce.actualizar_hito(ruta, 'OBRA X', 'ensayos_instrumentales', 'hecho', fecha='15/08/2026', nota='prueba manual')
    datos, avisos = ce.cargar(ruta, obra='OBRA X')
    print(datos['hitos']['ensayos_instrumentales'], avisos)
"
```
Expected: imprime `{'estado': 'hecho', 'fecha': '15/08/2026', 'nota': 'prueba manual'} []` sin traceback.

- [ ] **Step 6: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/cierre_expediente.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_cierre_expediente.py"
git commit -m "Nuevo modulo cierre_expediente.py: ensayos, OCA, CIE, Libro del Edificio"
```

---

### Task 4: `panel_obra.py` — pestaña "Cierre de expediente"

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py`
- Test: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_cierre_expediente.py`

**Interfaces:**
- Consumes: `cierre_expediente.HITOS_ORDEN`, `HITOS_NOMBRE` (Task 3).
- Produces: `bloque_cierre(cierre: dict, avisos: list[str] | None = None) -> str`
  (HTML), y un nuevo parámetro `cierre=None, cierre_avisos=None` en
  `generar_panel(...)`. La Task 6 pasa estos dos parámetros desde
  `generar_todos.py`.

- [ ] **Step 1: Escribir el test que falla**

Crea el fichero completo:

```python
# -*- coding: utf-8 -*-
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import cierre_expediente as ce
from panel_obra import bloque_cierre


class TestBloqueCierre(unittest.TestCase):

    def test_cierre_vacio_muestra_los_cuatro_hitos_pendientes(self):
        html = bloque_cierre(ce.vacio('OBRA X'))
        self.assertIn('Ensayos instrumentales', html)
        self.assertIn('Inspección OCA', html)
        self.assertIn('CIE / Boletín eléctrico', html)
        self.assertIn('Libro del Edificio', html)
        self.assertEqual(html.count('pendiente'), 4)

    def test_hito_hecho_se_refleja_en_el_html(self):
        datos = ce.vacio('OBRA X')
        datos['hitos']['libro_edificio'] = {
            'estado': 'hecho', 'fecha': '12/08/2026', 'nota': 'entregado'}
        html = bloque_cierre(datos)
        self.assertIn('hecho', html)
        self.assertIn('12/08/2026', html)
        self.assertIn('entregado', html)

    def test_avisos_se_muestran_como_banner(self):
        html = bloque_cierre(ce.vacio('OBRA X'), avisos=['dato raro en el fichero'])
        self.assertIn('dato raro en el fichero', html)

    def test_sin_avisos_no_hay_banner_de_aviso(self):
        html = bloque_cierre(ce.vacio('OBRA X'), avisos=[])
        self.assertNotIn('banner bad', html)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Confirmar que falla**

Run: `python -m unittest tests.test_panel_cierre_expediente -v`
Expected: `ERROR` — `ImportError: cannot import name 'bloque_cierre'`.

- [ ] **Step 3: Añadir `bloque_cierre` a `panel_obra.py`**

Abre `panel_obra.py`. Busca la función `bloque_prioridades` (línea 414 en
esta versión). Justo **antes** de su definición (`def bloque_prioridades`),
añade esta nueva función completa:

```python
def bloque_cierre(cierre, avisos=None):
    """HTML de la pestana Cierre de expediente.

    `cierre` es la forma que devuelve cierre_expediente.cargar()/vacio():
    {"obra":..., "actualizado":..., "hitos": {id: {"estado","fecha","nota"}}}.
    Dato de obra editado a mano, al margen de la rejilla de revisiones.
    """
    import cierre_expediente as ce
    cierre = cierre or ce.vacio()
    avisos = avisos or []

    avisos_html = ""
    if avisos:
        avisos_html = "".join(
            f"<div class='banner bad'>⚠ {_e(a)}</div>" for a in avisos)

    filas = ""
    for hito_id in ce.HITOS_ORDEN:
        datos_hito = (cierre.get('hitos') or {}).get(hito_id) or {
            'estado': 'pendiente', 'fecha': None, 'nota': ''}
        nombre = ce.HITOS_NOMBRE.get(hito_id, hito_id)
        estado = datos_hito.get('estado') or 'pendiente'
        badge = 'ok' if estado in ('hecho', 'favorable') else (
            'bad' if estado in ('condicionada', 'negativa') else 'warn')
        fecha = datos_hito.get('fecha') or '—'
        nota = datos_hito.get('nota') or '—'
        filas += (
            f"<tr><td>{_e(nombre)}</td>"
            f"<td><span class='badge {badge}'>{_e(estado)}</span></td>"
            f"<td>{_e(fecha)}</td><td>{_e(nota)}</td></tr>"
        )

    actualizado = cierre.get('actualizado') or 'sin actualizar todavía'
    return (
        avisos_html
        + "<div class='card'><h3>Cierre de expediente</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Ensayos, inspección OCA, CIE/Boletín y Libro del Edificio. Dato de "
        "obra editado a mano, no calculado desde las revisiones de campo. "
        f"Última actualización: {_e(actualizado)}.</p>"
        "<table class='data'><thead><tr><th>Hito</th><th>Estado</th>"
        "<th>Fecha</th><th>Nota</th></tr></thead>"
        f"<tbody>{filas}</tbody></table></div>"
    )


```

- [ ] **Step 4: Confirmar que el bloque pasa solo**

Run: `python -m unittest tests.test_panel_cierre_expediente -v`
Expected: `OK`, 4 tests en verde.

- [ ] **Step 5: Conectar la pestaña en `generar_panel`**

Todavía en `panel_obra.py`, dentro de `def generar_panel(...)`:

1. Cambia la firma (línea `def generar_panel(obra, subtitulo, historial, materiales, ficha, documentos,`)
   añadiendo dos parámetros al final de la lista existente:

```python
def generar_panel(obra, subtitulo, historial, materiales, ficha, documentos,
                  output_path, volver_href="../../index.html", prioridades=None,
                  tajos_memoria=None, mem_resumen=None, bat_path=None,
                  cierre=None, cierre_avisos=None):
```

2. Justo después del bloque que calcula `riesgos_html` (busca la línea
   `riesgos_html = bloque_riesgos(`, termina en `riesgos_manual=ficha.get('riesgos', []), sin_cambios=sin_cambios)`),
   añade:

```python
    cierre_html = bloque_cierre(cierre, avisos=cierre_avisos)
```

3. En el bloque `<div class="nav">`, después de la línea
   `<button data-view="v-docs">📎 Documentos</button>`, añade:

```python
  <button data-view="v-cierre">📋 Cierre</button>
```

4. Después de la sección `<section id="v-docs" class="view">...` (busca
   dónde termina esa sección, cierra con `</div></section>`, justo antes de
   `<section id="v-actualizar"`), añade:

```python
<section id="v-cierre" class="view">{cierre_html}</section>
```

- [ ] **Step 6: Añadir una prueba de humo sobre `generar_panel` completo**

Añade este test al final de `tests/test_panel_cierre_expediente.py`, dentro
de una nueva clase en el mismo fichero:

```python
class TestGenerarPanelConCierre(unittest.TestCase):

    def test_generar_panel_incluye_la_pestana_cierre_sin_reventar(self):
        import tempfile
        from panel_obra import generar_panel

        with tempfile.TemporaryDirectory() as tmp:
            salida = os.path.join(tmp, 'panel.html')
            resultado = generar_panel(
                obra='OBRA DE PRUEBAS', subtitulo='Prueba',
                historial=[], materiales={'disponible': False},
                ficha={'_disponible': False}, documentos=[],
                output_path=salida,
                cierre=ce.vacio('OBRA DE PRUEBAS'),
                cierre_avisos=[],
            )
            with open(salida, encoding='utf-8') as f:
                contenido = f.read()
            self.assertIn('data-view="v-cierre"', contenido)
            self.assertIn('id="v-cierre"', contenido)
            self.assertIn('Cierre de expediente', contenido)
```

Run: `python -m unittest tests.test_panel_cierre_expediente -v`
Expected: `OK`, 5 tests en verde. Si `generar_panel` no escribe el fichero en
`output_path` automáticamente, revisa cómo termina la función actual
(busca `with open(output_path` cerca del final) — si en vez de eso
devuelve el HTML, ajusta el test para escribirlo tú mismo con
`open(salida, 'w', encoding='utf-8').write(resultado_html)` en lugar de
leerlo de disco. Verifica el comportamiento real antes de dar el test por
bueno.

- [ ] **Step 7: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_cierre_expediente.py"
git commit -m "Panel: nueva pestana Cierre de expediente"
```

---

### Task 5: `generar_informe_ejecutivo.py` — sección PDF de cierre de expediente

**Files:**
- Modify: `_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py`
- Test: `_SISTEMA/MOTOR/tests/test_informe_ejecutivo_cierre.py`

**Interfaces:**
- Consumes: `cierre_expediente.HITOS_ORDEN`, `HITOS_NOMBRE` (Task 3).
- Produces: `_tabla_cierre_expediente(cierre, avisos, content_w) -> Table`
  (o `Paragraph` si no hay datos); nuevo parámetro `cierre=None,
  avisos_cierre=None` en `generar_pdf_ejecutivo(...)` y `cierre=None` en
  `generar_para_obra(...)`.

**Primero, comprueba dónde viven las pruebas existentes de este módulo:**

Run: `python -c "import os; print(os.path.isdir('_SISTEMA/MOTOR/tests'))"` desde la raíz del repo, y localiza `test_informe_ejecutivo_electrico.py` (está en
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/`, no en
`_SISTEMA/MOTOR/tests/`, aunque el script que prueba vive en
`_SISTEMA/MOTOR/scripts/`). Sigue esa misma convención: crea el test nuevo
en `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_cierre.py`,
no en `_SISTEMA/MOTOR/tests/`.

- [ ] **Step 1: Escribir el test que falla**

Crea `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_cierre.py`:

```python
# -*- coding: utf-8 -*-
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT = os.path.dirname(os.path.dirname(_BASE))  # -> raiz del repo
_SCRIPTS = os.path.join(_ROOT, '_SISTEMA', 'MOTOR', 'scripts')
for ruta in (_BASE, _SCRIPTS):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

import cierre_expediente as ce
from generar_informe_ejecutivo import _tabla_cierre_expediente
from reportlab.platypus import Table, Paragraph


class TestTablaCierreExpediente(unittest.TestCase):

    def test_sin_datos_devuelve_parrafo_informativo(self):
        resultado = _tabla_cierre_expediente(None, [], content_w=170)
        self.assertIsInstance(resultado, Paragraph)

    def test_con_datos_devuelve_una_tabla_de_cuatro_filas_mas_cabecera(self):
        cierre = ce.vacio('OBRA X')
        cierre['hitos']['libro_edificio'] = {
            'estado': 'hecho', 'fecha': '12/08/2026', 'nota': 'entregado'}
        resultado = _tabla_cierre_expediente(cierre, [], content_w=170)
        self.assertIsInstance(resultado, Table)
        self.assertEqual(len(resultado._cellvalues), 5)  # cabecera + 4 hitos

    def test_con_avisos_no_revienta_y_devuelve_flowables(self):
        from reportlab.platypus import KeepTogether
        cierre = ce.vacio('OBRA X')
        resultado = _tabla_cierre_expediente(
            cierre, ["cierre_expediente.json: 'inspeccion_oca' tiene un "
                     "estado no reconocido ('revisar'); revisar a mano."],
            content_w=170)
        self.assertIsInstance(resultado, KeepTogether)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Confirmar que falla**

Run (desde `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/`):
`python -m unittest tests.test_informe_ejecutivo_cierre -v`
Expected: `ERROR` — `ImportError: cannot import name '_tabla_cierre_expediente'`.

- [ ] **Step 3: Importar `cierre_expediente` en el informe ejecutivo**

Abre `_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py`. Busca el bloque:

```python
import motor_informes
import ficha_obra as fichas
import priorizador_trabajos
from registro_obras import OBRAS, resolver_obra
```

Añade una línea:

```python
import motor_informes
import ficha_obra as fichas
import priorizador_trabajos
import cierre_expediente
from registro_obras import OBRAS, resolver_obra
```

- [ ] **Step 4: Añadir `_tabla_cierre_expediente`**

Busca la función `_pie_electrico` (termina justo antes de
`def _construir_bloque_electrico`). Justo después de `_pie_electrico` y
antes de `_construir_bloque_electrico`, añade:

```python
COLOR_ESTADO_HITO = {
    'hecho': COL_OK, 'favorable': COL_OK,
    'condicionada': COL_WARN, 'negativa': COL_WARN,
    'no_aplica': COL_GRIS, 'pendiente': COL_GRIS,
}


def _tabla_cierre_expediente(cierre: dict | None, avisos: list[str] | None,
                              content_w: float):
    cierre = cierre or {}
    hitos = cierre.get('hitos') or {}
    avisos = avisos or []
    if not hitos:
        return Paragraph(
            'Sin datos de cierre de expediente todavía.',
            _style('cierre_vacio', 8, color=COL_MUTED))

    filas = [[
        Paragraph('<b>HITO</b>', _style('cierre_h', 7.5, True, color=colors.white)),
        Paragraph('<b>ESTADO</b>', _style('cierre_h', 7.5, True, color=colors.white)),
        Paragraph('<b>FECHA</b>', _style('cierre_h', 7.5, True, color=colors.white)),
        Paragraph('<b>NOTA</b>', _style('cierre_h', 7.5, True, color=colors.white)),
    ]]
    for hito_id in cierre_expediente.HITOS_ORDEN:
        datos_hito = hitos.get(hito_id) or {'estado': 'pendiente', 'fecha': None, 'nota': ''}
        estado = datos_hito.get('estado') or 'pendiente'
        color_estado = COLOR_ESTADO_HITO.get(estado, COL_GRIS)
        nombre = cierre_expediente.HITOS_NOMBRE.get(hito_id, hito_id)
        filas.append([
            Paragraph(_texto(nombre), _style('cierre_c', 7.5)),
            Paragraph(f'<b>{_texto(estado).upper()}</b>',
                      _style('cierre_c_estado', 7.5, True, color=color_estado)),
            Paragraph(_texto(datos_hito.get('fecha') or '—'), _style('cierre_c', 7.5)),
            Paragraph(_texto(datos_hito.get('nota') or '—'), _style('cierre_c', 7.5)),
        ])
    tabla = Table(
        filas,
        colWidths=[content_w * 0.28, content_w * 0.18, content_w * 0.16, content_w * 0.38])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COL_NAVY),
        ('LINEBELOW', (0, 0), (-1, -1), .4, COL_LINE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    if not avisos:
        return tabla
    bloques = [tabla, Spacer(1, 2 * mm)]
    for aviso in avisos:
        bloques.append(Paragraph(f'⚠ {_texto(aviso)}', _style('cierre_aviso', 7, color=COL_WARN)))
    return KeepTogether(bloques)


```

- [ ] **Step 5: Confirmar que el test pasa**

Run: `python -m unittest tests.test_informe_ejecutivo_cierre -v`
Expected: `OK`, 3 tests en verde.

- [ ] **Step 6: Conectar la sección en `generar_pdf_ejecutivo` y `generar_para_obra`**

En `generar_pdf_ejecutivo(...)`:

1. Añade los parámetros a la firma:

```python
def generar_pdf_ejecutivo(
    nombre_obra: str,
    fecha_rev: str,
    snapshot: list[dict],
    output_pdf: Path,
    historial: list | None = None,
    ficha: dict | None = None,
    prioridades: dict | None = None,
    cierre: dict | None = None,
    avisos_cierre: list[str] | None = None,
) -> Path:
```

2. Justo antes de la línea `doc.build(story)`, añade:

```python
    # 3. Cierre de expediente: una vez, al final, sea cual sea el numero
    #    de portales/bloques de la obra.
    story.append(PageBreak())
    story.append(Paragraph(
        'CIERRE DE EXPEDIENTE', _style('cierre_titulo', 13, True, color=COL_NAVY)))
    story.append(Spacer(1, 3 * mm))
    story.append(_tabla_cierre_expediente(cierre, avisos_cierre, content_w))

    doc.build(story)
```

(la línea `doc.build(story)` que ya existía se sustituye por este bloque
completo — no debe quedar duplicada).

En `generar_para_obra(...)`:

3. Añade el parámetro a la firma:

```python
def generar_para_obra(
    nombre_obra: str,
    historial: list | None = None,
    ficha: dict | None = None,
    prioridades: dict | None = None,
    cierre: dict | None = None,
    avisos_cierre: list[str] | None = None,
) -> Path | None:
```

4. Justo antes de la línea `print(f"[2/2] Generando PDF Ejecutivo A4 en: {output_pdf}...")`, añade:

```python
    if cierre is None:
        ruta_cierre = carpeta_obra / "cierre_expediente.json"
        cierre, avisos_cierre = cierre_expediente.cargar(str(ruta_cierre), obra=nombre_oficial)
    avisos_cierre = avisos_cierre or []
```

(usa la variable `carpeta_obra` que la función ya calcula unas líneas antes
como `OBRAS_DIR / obra['carpeta_obra'] / "INFORME SAGARDE IA"`. Si se pasa
`cierre` pero no `avisos_cierre` —caso de la Task 6, que ya calculó ambos
por separado y solo se le olvida uno—, la línea final igualmente deja
`avisos_cierre` como lista, nunca `None`).

5. En la llamada a `generar_pdf_ejecutivo(...)` unas líneas más abajo, añade
   los dos argumentos nuevos:

```python
    generar_pdf_ejecutivo(
        nombre_oficial,
        fecha_rev,
        snapshot,
        output_pdf,
        historial=historial,
        ficha=ficha,
        prioridades=prioridades,
        cierre=cierre,
        avisos_cierre=avisos_cierre,
    )
```

- [ ] **Step 7: Verificar que el informe se sigue generando para una obra real, sin reventar**

Run (desde la raíz del repo):
```bash
python "_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py" --obra "2026 OBRA PRUEBA"
```
Expected: termina con `[OK] Informe ejecutivo creado con exito: ...pdf`, sin
traceback. Abre el PDF y comprueba a simple vista que la última página
dice "CIERRE DE EXPEDIENTE" con los 4 hitos en pendiente (Obra Prueba no
tiene `cierre_expediente.json` todavía).

- [ ] **Step 8: Ejecutar toda la suite del informe ejecutivo, para descartar regresión**

Run: `python -m unittest tests.test_informe_ejecutivo_electrico tests.test_informe_ejecutivo_caracter tests.test_informe_ejecutivo_cierre -v`
Expected: `OK`, todos en verde.

- [ ] **Step 9: Commit**

```bash
git add "_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_cierre.py"
git commit -m "Informe ejecutivo: seccion final de cierre de expediente"
```

---

### Task 6: `generar_todos.py` — conectar `cierre_expediente.json` y publicarlo

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `cierre_expediente.cargar` (Task 3), el nuevo parámetro
  `cierre=`/`cierre_avisos=` de `panel_obra.generar_panel` (Task 4), el
  nuevo parámetro `cierre=` de `generar_informe_ejecutivo.generar_para_obra`
  (Task 5).

- [ ] **Step 1: Importar el módulo**

Abre `generar_todos.py`. Busca sus imports de módulos propios cerca del
principio del fichero (donde importa `priorizador_trabajos`, `panel_obra`,
etc. — usa `grep -n "^import \|^from " generar_todos.py` si no aparecen
juntos) y añade `import cierre_expediente` junto a ellos.

- [ ] **Step 2: Calcular la ruta y cargar los datos**

Busca el bloque (dentro de `def main(...)`, tras entrar en el `try:` de cada
obra):

```python
        salida_dir = os.path.join(carpeta_abs, 'INFORME SAGARDE IA')
        salida_html = os.path.join(salida_dir, 'panel.html')
        salida_prioridades = os.path.join(salida_dir, 'prioridades_trabajos.json')
        salida_dudas = os.path.join(salida_dir, 'dudas_pendientes.json')
        salida_memoria = os.path.join(salida_dir, 'memoria_obra.json')
```

Añade una línea:

```python
        salida_cierre = os.path.join(salida_dir, 'cierre_expediente.json')
```

Busca la línea `res = panel_obra.generar_panel(` (llamada completa hasta su
`)` de cierre). Justo antes de esa llamada, añade:

```python
            cierre_datos, cierre_avisos = cierre_expediente.cargar(
                salida_cierre, obra=obra['nombre'])
```

- [ ] **Step 3: Pasar los datos a `generar_panel` y a `generar_para_obra`**

En la llamada a `panel_obra.generar_panel(...)`, añade dos argumentos:

```python
            res = panel_obra.generar_panel(
                obra=obra['nombre'], subtitulo=obra['subtitulo'], historial=historial,
                materiales=materiales, ficha=ficha, documentos=documentos,
                prioridades=prioridades, output_path=salida_html, volver_href=volver,
                tajos_memoria=tajos_memoria, mem_resumen=mem_resumen, bat_path=bat_abs,
                cierre=cierre_datos, cierre_avisos=cierre_avisos,
            )
```

En la llamada a `generar_informe_ejecutivo.generar_para_obra(...)`, añade
un argumento:

```python
            generar_informe_ejecutivo.generar_para_obra(
                obra['nombre'],
                historial=historial,
                ficha=ficha_actual,
                prioridades=prioridades,
                cierre=cierre_datos,
                avisos_cierre=cierre_avisos,
            )
```

- [ ] **Step 4: Publicar `cierre_expediente.json` en `.gitignore`**

Abre `.gitignore`. Busca las líneas:

```
# Datos calculados enlazados desde los paneles de obras
!SAGARDE OBRAS ABIERTAS/*/INFORME SAGARDE IA/prioridades_trabajos.json
!SAGARDE OBRAS ABIERTAS/*/INFORME SAGARDE IA/dudas_pendientes.json
```

Añade una línea después de `dudas_pendientes.json`:

```
!SAGARDE OBRAS ABIERTAS/*/INFORME SAGARDE IA/cierre_expediente.json
```

- [ ] **Step 5: Regenerar Obra Prueba y comprobar el fichero**

Run (desde `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/`):
```bash
python regenerar_obra.py prueba
```
Expected: termina sin `[ERROR]`. Comprueba a mano:
```bash
python -c "import json; print(json.load(open('../2026 OBRA PRUEBA/INFORME SAGARDE IA/cierre_expediente.json', encoding='utf-8'))['hitos'].keys())"
```
Expected: `dict_keys(['ensayos_instrumentales', 'inspeccion_oca', 'cie_boletin', 'libro_edificio'])`.

Abre `2026 OBRA PRUEBA/INFORME SAGARDE IA/panel.html` en un navegador (o
`grep -o 'data-view="v-cierre"' panel.html`) y confirma que la pestaña
"Cierre" existe y no rompe el resto del panel.

- [ ] **Step 6: Confirmar con `git status` que solo cambió lo esperado**

Run: `git status`
Expected: modificados `generar_todos.py`, `.gitignore`, y bajo
`2026 OBRA PRUEBA/INFORME SAGARDE IA/` como mucho `panel.html`,
`cierre_expediente.json` y `INFORME_EJECUTIVO_2026_OBRA_PRUEBA.pdf`. Si
aparece cualquier otra obra (Mungia, Gernika, Bolueta) modificada, **para
aquí y avisa** — `regenerar_obra.py prueba` no debería tocar ninguna otra
carpeta; si lo hizo, hay un bug que revisar antes de seguir.

- [ ] **Step 7: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py" .gitignore "SAGARDE OBRAS ABIERTAS/2026 OBRA PRUEBA/INFORME SAGARDE IA"
git commit -m "Conectar cierre_expediente.json al panel y al informe ejecutivo"
```

---

### Task 7: Regresión completa y mapa mental

**Files:**
- Modify: `_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`

- [ ] **Step 1: Ejecutar la suite completa del motor**

Run (desde `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/`):
```bash
python -m unittest discover -s tests -v
```
Expected: `OK`. Compara el número total de tests con el recuento previo a
este plan (348 según la última memoria del proyecto) — debe haber subido en
al menos los tests añadidos en las Tasks 1, 2, 3, 4 y 5 (23 nuevos: 1+3+8+5+2,
más los ya existentes que ahora también cubren `fotovoltaica` de forma
automática). Si baja o se mantiene igual, algún test nuevo no se está
descubriendo — revisar antes de seguir.

- [ ] **Step 2: Regenerar las cuatro obras y comprobar qué se mueve y qué no**

Anota primero los valores actuales de
`_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md` (tabla "Estado de hoy"):
Gernika 76.3, Bolueta 43.5, Mungia 80.1, Obra Prueba 6.4, junto con sus
columnas `X/M///P/?/N`.

Run:
```bash
python regenerar_obra.py mungia
python regenerar_obra.py gernika
python regenerar_obra.py bolueta
python regenerar_obra.py prueba
```

Para cada una, compara el `%` y el desglose `X/M///P/?/N` impreso en
consola contra los valores anotados. Fotovoltaica es un tajo común nuevo sin
marcar en ninguna revisión todavía, así que las CUATRO obras van a ganar
celdas nuevas en `?` (nadie la ha mirado nunca) — eso es el único
movimiento esperado, y es correcto tanto si sale una celda por ubicación
como si `estado_desde_ficha` la reparte de otra forma: no se ha verificado
en este plan cuántas celdas concretas genera un tajo `ambito: "edificio"`
frente a uno `vivienda`, y no hace falta saberlo para esta comprobación.

Lo que sí es una regla dura, sin excepción:

- Ninguna cifra de `X`, `M`, `/` o `P` debe cambiar en ninguna de las
  cuatro obras. Solo puede subir `?` (y el total de celdas, en la misma
  cantidad que suba `?`).
- El `%` puede bajar una fracción mínima (más celdas sin marcar en el
  denominador); no debe subir.

Si `X`, `M`, `/` o `P` se mueven en cualquier obra, **para y repórtalo tal
cual antes de continuar**: no es un resultado esperado de este plan.

- [ ] **Step 3: Reportar antes/después a Bixente**

Escribe en el chat (no hace falta fichero nuevo) los cuatro números de
antes y después del Step 2, y el recuento de tests de antes y después del
Step 1. Norma del proyecto: aplicar en silencio algo que mueve cifras es
repetir el problema desde el otro lado.

- [ ] **Step 4: Actualizar el mapa mental**

Abre `_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`. En la tabla de la
sección **5.2 Scripts**, busca la fila de `memoria_obra.py` (empieza con
`| \`memoria_obra.py\` |`). Justo después de esa fila, añade:

```
| `cierre_expediente.py` | `_SISTEMA.../cierre_expediente.py` | Python | Ensayos/OCA/CIE/Libro del Edificio, aparte de la rejilla | import/CLI | orquestador/panel/informe | `cierre_expediente.json` | mismo fichero | stdlib | Activo desde 15/08/2026 |
```

En la sección **2. Resumen ejecutivo**, en el párrafo que empieza con
"Pendientes concretos al cierre del 13/08/2026", añade un párrafo nuevo
justo antes (no lo edites, es histórico):

```
Añadido el 15/08/2026: tajo común `fotovoltaica` (sin dependencia, igual
que Cuarto técnico) y un cierre de expediente por obra
(`cierre_expediente.json`: ensayos, OCA, CIE/Boletín, Libro del Edificio),
deliberadamente fuera de la rejilla ubicaciones×tajos y de la hoja de
revisión semanal. Ver
`_SISTEMA/docs/superpowers/specs/2026-08-15-tesis-prioridades-instalacion-electrica-design.md`.
```

- [ ] **Step 5: Commit**

```bash
git add "_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md"
git commit -m "Mapa mental: registrar cierre_expediente.py y el tajo Fotovoltaica"
```

**No lanzar `Actualizar_Sagarde.bat` al terminar esta tarea.** Publicar es
decisión de Bixente, no de quien ejecuta el plan.
