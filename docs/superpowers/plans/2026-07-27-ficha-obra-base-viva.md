# Ficha de obra como base viva — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que `ficha_obra.json` se actualice sola en cada regeneración y contenga todos los datos de la obra, dejando de ser una foto que hay que resembrar a mano.

**Architecture:** Un módulo `ficha_obra.py` (capa 0) expone `cargar/actualizar/guardar`. `generar_todos.py` lo llama por obra justo después de calcular las prioridades: la ficha absorbe los estados nuevos, da de alta lo que no conocía marcándolo *sin confirmar*, recupera las correcciones manuales que la revisión no supo leer, y rellena los apartados de identidad, materiales, documentos y contactos desde los lectores que ya existen. Las obras sin ficha siguen comportándose exactamente como hasta ahora.

**Tech Stack:** Python 3.11.9 (Windows), stdlib únicamente. `openpyxl` ya se usa vía `lectores.py`. Pruebas con `unittest` de la stdlib — **no instalar pytest**, el entorno no lo tiene y el usuario ejecuta todo desde ficheros `.bat`.

## Global Constraints

- Raíz del proyecto: `D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE`
- Sistema: `SAGARDE OBRAS ABIERTAS\_SISTEMA INFORME SAGARDE IA\` (referido como `_SISTEMA` en este plan)
- **Una obra sin `ficha_obra.json` debe comportarse EXACTAMENTE como hoy.** Cualquier tarea que rompa esto está mal.
- **Criterio de regresión permanente:** Mungia debe mantener `pct_ponderado = 80.1`. Si cambia, parar e investigar.
- Alfabeto de estados guardados: `X` terminado · `M` más del 50% · `/` iniciado · `P` pendiente confirmado · `?` desconocido · `N` no aplica.
- **No se persisten categorías derivadas** (`BLOQUEADO`, `DUDAS`, `VIABLE`, `OTROS_GREMIOS`): las calcula el priorizador desde las dependencias. Se guarda lo medido, se recalcula lo derivado.
- Norma de obra: **lo que se apunta en la última revisión es lo que vale.** Una marca explícita (`X`/`M`/`/`) y una casilla vacía en hoja validada (`P`) mandan sobre el histórico. Solo `?` (el lector no supo leer) no puede bajar una `X`.
- Los ficheros `.py` no están versionados en git (el `.gitignore` es lista blanca y solo admite `.html` y JSON concretos). Los commits de código solo moverán ficheros ya rastreados; el código Python vive en disco. Hacer copia `.bak` con fecha antes de modificar cualquier `.py` existente, siguiendo la convención del proyecto.
- Codificación: todo script de diagnóstico empieza con `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`.

---

## Estructura de ficheros

| Fichero | Responsabilidad | Estado |
|---|---|---|
| `_SISTEMA/ficha_obra.py` | Cargar, actualizar y guardar la ficha. Única autoridad sobre su esquema. | **Ya escrito, sin probar ni conectar** |
| `_SISTEMA/tests/test_ficha_obra.py` | Banco de pruebas del módulo con datos sintéticos. | Crear |
| `_SISTEMA/tests/fixtures.py` | Constructores de ficha y prioridades de juguete. | Crear |
| `_SISTEMA/generar_todos.py` | Orquestador. Llama a `ficha_obra.actualizar()` por obra. | Modificar |
| `_SISTEMA/sembrar_ficha_obra.py` | Siembra inicial de una obra desde sus datos existentes. | Ya escrito |
| `_SISTEMA/lectores.py` | Lee xlsx de materiales, ficha de obra y lista documentos. | Solo lectura, no tocar |

**Interfaces que ya existen y se consumen (no reimplementar):**

```python
lectores.leer_ficha(ruta_xlsx)
# -> {'datos': {clave: valor}, 'personal': [dict], 'hitos': [dict],
#     'riesgos': [dict], 'plan': [dict], '_disponible': bool}

lectores.leer_materiales(ruta_xlsx)
# -> {'disponible': bool, 'meses': [str], 'ultimo_mes': str|None,
#     'ultima_fecha': str|None, 'dias_desde': int|None,
#     'items': [{'categoria','material','tipo','uni','total'}], 'aviso': str|None}

lectores.listar_documentos(carpeta_obra, base_href_desde)
# -> [{'nombre','categoria','subcarpeta','href','kb'}]
```

---

## Task 1: Banco de pruebas y fixtures

**Files:**
- Create: `_SISTEMA/tests/fixtures.py`
- Create: `_SISTEMA/tests/test_ficha_obra.py`

**Interfaces:**
- Consumes: `ficha_obra.asegurar_apartados`, `ficha_obra.APARTADOS`
- Produces: `fixtures.ficha_minima()` y `fixtures.prioridades(items)`, que usan todas las tareas siguientes.

- [ ] **Step 1: Escribir las fixtures**

Crear `_SISTEMA/tests/fixtures.py`:

```python
# -*- coding: utf-8 -*-
"""Datos de juguete para las pruebas de ficha_obra.

Una obra minima pero realista: 1 bloque, 1 portal ('P1'), 2 plantas
('PB' y '1'), 2 viviendas por planta ('A' y 'B'), y 2 tajos.
"""


def ficha_minima():
    return {
        'version': 1,
        'id': 'pruebas',
        'modo': 'hibrida',
        'identidad': {'nombre': 'OBRA DE PRUEBAS', 'carpeta': 'OBRA DE PRUEBAS',
                      'tipo_obra': 'viviendas', '_meta': {}},
        'estructura': {
            'bloques': [{
                'id': 'b1', 'nombre': 'Bloque 1',
                'portales': [{
                    'id': 'p1', 'nombre': 'P1', 'referencia': 'P1',
                    'plantas': [
                        {'id': 'pb', 'nombre': 'PB', 'orden': 0, 'ubicaciones': [
                            {'id': 'A', 'tipo': 'vivienda', 'origen': 'campo'},
                            {'id': 'B', 'tipo': 'vivienda', 'origen': 'campo'},
                        ]},
                        {'id': '1', 'nombre': '1', 'orden': 1, 'ubicaciones': [
                            {'id': 'A', 'tipo': 'vivienda', 'origen': 'campo'},
                            {'id': 'B', 'tipo': 'vivienda', 'origen': 'campo'},
                        ]},
                    ],
                }],
            }],
            'alias_historico': {},
            '_meta': {},
        },
        'tajos': {
            'aplicables': ['tubeado', 'cableado'],
            'detalle': [
                {'id': 'tubeado', 'nombre': 'Tubeado', 'ambito': 'vivienda',
                 'propiedad': 'propio', 'fase': 'Interior', 'orden': 10},
                {'id': 'cableado', 'nombre': 'Cableado', 'ambito': 'vivienda',
                 'propiedad': 'propio', 'fase': 'Interior', 'orden': 20},
            ],
            '_meta': {},
        },
        'estados': {},
        'revisiones': [], 'dudas': [],
        'materiales': {}, 'documentos': {}, 'contactos': [],
    }


def item(edificio='P1', planta='PB', unidad='A', tarea='tubeado',
         estado='X', trabajo='Tubeado', ambito='vivienda', orden=10):
    return {
        'tarea_id': tarea, 'trabajo': trabajo, 'ambito': ambito,
        'propiedad': 'propio', 'fase_nombre': 'Interior',
        'orden_ejecucion': orden, 'edificio': edificio, 'planta': planta,
        'unidad': unidad, 'estado_actual': estado, 'ultima_fecha': '27/07/2026',
    }


def prioridades(items, revision='27/07/2026'):
    return {'revision': revision, 'generado': '27/07/2026 18:00',
            'detalle_items': list(items), 'resumen': {}}
```

- [ ] **Step 2: Escribir la primera prueba (apartados)**

Crear `_SISTEMA/tests/test_ficha_obra.py`:

```python
# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ficha_obra
import fixtures


class TestApartados(unittest.TestCase):

    def test_crea_los_apartados_que_faltan(self):
        ficha = {'id': 'pruebas'}
        creados = ficha_obra.asegurar_apartados(ficha)
        for nombre in ficha_obra.APARTADOS:
            self.assertIn(nombre, ficha)
        self.assertIn('materiales', creados)

    def test_no_pisa_los_apartados_que_ya_existen(self):
        ficha = fixtures.ficha_minima()
        ficha['materiales'] = {'algo': 1}
        creados = ficha_obra.asegurar_apartados(ficha)
        self.assertEqual(creados, [])
        self.assertEqual(ficha['materiales'], {'algo': 1})


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Ejecutar y verificar que pasa**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -v
```

Esperado: 2 pruebas OK. Si `asegurar_apartados` falla, corregir `ficha_obra.py` hasta que pasen.

- [ ] **Step 4: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "Banco de pruebas de ficha_obra con datos sinteticos"
```

---

## Task 2: Estados — la revisión manda, pero solo sobre lo que menciona

**Files:**
- Modify: `_SISTEMA/tests/test_ficha_obra.py`
- Modify: `_SISTEMA/ficha_obra.py` (solo si las pruebas fallan)

**Interfaces:**
- Consumes: `fixtures.ficha_minima`, `fixtures.item`, `fixtures.prioridades`
- Produces: garantía de que `ficha_obra.actualizar(ficha, prioridades)` devuelve `(ficha, cambios)` con `cambios['estados_cambiados']` como lista de tuplas `(clave, anterior, nuevo)` y `cambios['estados_nuevos']` como entero.

- [ ] **Step 1: Escribir las pruebas**

Añadir a `test_ficha_obra.py`:

```python
class TestEstados(unittest.TestCase):

    def test_una_celda_medida_se_guarda_con_su_fecha(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='X')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        celda = ficha['estados']['p1__pb__tubeado__A']
        self.assertEqual(celda['v'], 'X')
        self.assertEqual(celda['f'], '27/07/2026')
        self.assertEqual(celda['r'], 'rev_27072026')

    def test_pendiente_se_guarda_como_P_no_como_ausencia(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='Pendiente')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'P')

    def test_las_celdas_sin_dato_nacen_como_desconocido(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        # 1 portal x 2 plantas x 2 viviendas x 2 tajos = 8 celdas
        self.assertEqual(len(ficha['estados']), 8)
        self.assertEqual(ficha['estados']['p1__1__cableado__B']['v'], '?')

    def test_la_ultima_revision_manda_aunque_baje_de_X(self):
        """Norma de obra: si el revisor escribe M sobre algo que figuraba
        terminado, es que ha ido y ha visto que faltaba algo."""
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='X')]))
        ficha, cambios = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='M')],
                                        revision='30/07/2026'))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')
        self.assertIn(('p1__pb__tubeado__A', 'X', 'M'), cambios['estados_cambiados'])

    def test_no_toca_las_celdas_que_la_revision_no_menciona(self):
        """Si la hoja no cubre una celda, su dato anterior se conserva.
        Una revision parcial no puede borrar lo que no ha mirado."""
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(ficha, fixtures.prioridades([
            fixtures.item(unidad='A', estado='X'),
            fixtures.item(unidad='B', estado='X'),
        ]))
        ficha, _ = ficha_obra.actualizar(ficha, fixtures.prioridades(
            [fixtures.item(unidad='A', estado='M')], revision='30/07/2026'))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__B']['v'], 'X')
```

- [ ] **Step 2: Ejecutar**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_ficha_obra.TestEstados -v
```

Esperado: las 5 pasan. Si `test_las_celdas_sin_dato_nacen_como_desconocido` falla por el recuento, comprobar que `_completar_matriz` se llama después de procesar el detalle y que recorre todas las ubicaciones.

- [ ] **Step 3: Corregir `ficha_obra.py` si algo falla**

No hay implementación nueva que escribir salvo que las pruebas revelen un fallo. Si lo hay, corregirlo sin cambiar la firma de `actualizar()`.

- [ ] **Step 4: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "Pruebas de estados: la ultima revision manda sobre lo que menciona"
```

---

## Task 3: Alta sin confirmar de ubicaciones y tajos nuevos

**Files:**
- Modify: `_SISTEMA/tests/test_ficha_obra.py`
- Modify: `_SISTEMA/ficha_obra.py` (solo si fallan)

**Interfaces:**
- Consumes: `ficha_obra.actualizar`
- Produces: `cambios['ubicaciones_nuevas']` y `cambios['tajos_nuevos']` como listas de texto legible; toda alta automática lleva `origen='revision_sin_confirmar'`.

- [ ] **Step 1: Escribir las pruebas**

```python
class TestAltasSinConfirmar(unittest.TestCase):

    def test_una_vivienda_nueva_entra_marcada_sin_confirmar_y_avisa(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(unidad='C', estado='X')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        pb = ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0]
        nueva = next(u for u in pb['ubicaciones'] if u['id'] == 'C')
        self.assertEqual(nueva['origen'], 'revision_sin_confirmar')
        self.assertIsNone(nueva['confirmado'])
        self.assertTrue(any('unidad C' in a for a in cambios['ubicaciones_nuevas']))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__C']['v'], 'X')

    def test_una_planta_nueva_tambien_entra_sin_confirmar(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(planta='2', unidad='A')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        plantas = ficha['estructura']['bloques'][0]['portales'][0]['plantas']
        nueva = next(p for p in plantas if p['nombre'] == '2')
        self.assertEqual(nueva['origen'], 'revision_sin_confirmar')
        self.assertTrue(any('planta entera' in a for a in cambios['ubicaciones_nuevas']))

    def test_un_portal_desconocido_NO_se_inventa(self):
        """Un portal entero que no existe casi siempre es un error de lectura,
        no una obra que ha crecido. Se ignora y no se ensucia la estructura."""
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(edificio='P9', unidad='A')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        portales = ficha['estructura']['bloques'][0]['portales']
        self.assertEqual([p['id'] for p in portales], ['p1'])

    def test_un_tajo_nuevo_entra_sin_confirmar_y_avisa(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(
            tarea='mecanizado', trabajo='Mecanizado', orden=30)])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        self.assertIn('mecanizado', cambios['tajos_nuevos'])
        nuevo = next(t for t in ficha['tajos']['detalle'] if t['id'] == 'mecanizado')
        self.assertEqual(nuevo['origen'], 'revision_sin_confirmar')
        self.assertIn('mecanizado', ficha['tajos']['aplicables'])

    def test_las_plantas_quedan_ordenadas_con_PB_primero(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(planta='2', unidad='A')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        nombres = [p['nombre'] for p in
                   ficha['estructura']['bloques'][0]['portales'][0]['plantas']]
        self.assertEqual(nombres, ['PB', '1', '2'])
```

- [ ] **Step 2: Ejecutar**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_ficha_obra.TestAltasSinConfirmar -v
```

Esperado: las 5 pasan.

- [ ] **Step 3: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "Pruebas de altas: lo nuevo entra marcado sin confirmar y avisa"
```

---

## Task 4: Recuperar las correcciones manuales que la revisión no supo leer

**Files:**
- Modify: `_SISTEMA/tests/test_ficha_obra.py`

**Interfaces:**
- Consumes: `ficha_obra.actualizar(ficha, prioridades, correcciones, mapa_tajos_cortos)`
- Produces: `cambios['correcciones_reclamadas']` como lista de tuplas `(clave, anterior, nuevo)`.

Contexto: las correcciones son marcas escritas a boli sobre la hoja. Se perdían cuando la clave no casaba — porque el extractor de PDF parte `PORTAL` en `PORT AL`, porque la ubicación no existía, o porque usan códigos cortos de tajo (`cuad-mec`) frente a los largos de la ficha (`cuadro_mecanizado`).

- [ ] **Step 1: Escribir las pruebas**

```python
class TestCorrecciones(unittest.TestCase):

    def test_traduce_el_codigo_corto_de_tajo_al_largo(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='Pendiente')])
        ficha, cambios = ficha_obra.actualizar(
            ficha, prio,
            correcciones={'p1__pb__tub__A': 'X'},
            mapa_tajos_cortos={'tub': 'tubeado'})
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['origen'],
                         'correccion manual')

    def test_recompone_una_unidad_partida_por_el_extractor(self):
        """'PORT AL' es 'PORTAL' con un espacio metido por pdfplumber."""
        ficha = fixtures.ficha_minima()
        ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0][
            'ubicaciones'].append(
                {'id': 'PORTAL', 'tipo': 'zona_comun', 'origen': 'campo'})
        prio = fixtures.prioridades([fixtures.item(estado='X')])
        ficha, _ = ficha_obra.actualizar(
            ficha, prio, correcciones={'p1__pb__tubeado__PORT AL': 'M'})
        self.assertEqual(ficha['estados']['p1__pb__tubeado__PORTAL']['v'], 'M')

    def test_llega_a_una_vivienda_que_la_revision_no_conoce(self):
        """El caso de la vivienda E de Mungia: existe en la ficha, la
        revision no la lee, pero Bixente si la relleno a boli."""
        ficha = fixtures.ficha_minima()
        ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0][
            'ubicaciones'].append({'id': 'E', 'tipo': 'vivienda',
                                   'origen': 'confirmado_usuario'})
        prio = fixtures.prioridades([fixtures.item(unidad='A', estado='X')])
        ficha, cambios = ficha_obra.actualizar(
            ficha, prio, correcciones={'p1__pb__cableado__E': 'X'})
        self.assertEqual(ficha['estados']['p1__pb__cableado__E']['v'], 'X')
        self.assertEqual(len(cambios['correcciones_reclamadas']), 1)

    def test_una_correccion_que_coincide_no_se_cuenta_como_cambio(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='X')])
        ficha, cambios = ficha_obra.actualizar(
            ficha, prio, correcciones={'p1__pb__tubeado__A': 'X'})
        self.assertEqual(cambios['correcciones_reclamadas'], [])
```

- [ ] **Step 2: Ejecutar**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_ficha_obra.TestCorrecciones -v
```

Esperado: las 4 pasan. Si `test_recompone_una_unidad_partida` falla, revisar que `_reclamar_correcciones` aplica `unidad.replace(' ', '')` ANTES de componer la clave destino.

- [ ] **Step 3: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "Pruebas de correcciones manuales huerfanas"
```

---

## Task 5: Conectar la actualización a `generar_todos.py`

**Files:**
- Modify: `_SISTEMA/generar_todos.py` (función `main`, dentro del bucle por obra, después de calcular `prioridades`)
- Create: `_SISTEMA/generar_todos.py.ANTES_ACTUALIZACION_FICHA_20260727.bak`

**Interfaces:**
- Consumes: `ficha_obra.cargar`, `ficha_obra.actualizar`, `ficha_obra.guardar`, `ficha_obra.resumen_cambios`
- Produces: efecto lateral — `ficha_obra.json` queda al día tras cada regeneración; avisos por consola con prefijo `[FICHA]`.

Esta tarea cierra el defecto principal: hoy `prioridades_trabajos.json` se regenera solo pero la ficha no, así que el generador puede servir estados de ayer.

- [ ] **Step 1: Copia de seguridad**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && cp generar_todos.py generar_todos.py.ANTES_ACTUALIZACION_FICHA_20260727.bak
```

- [ ] **Step 2: Guardar el porcentaje actual de Mungia como referencia**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -c "import json,sys; sys.stdout.reconfigure(encoding='utf-8',errors='replace'); d=json.load(open('resumen_obras.json',encoding='utf-8')); print([(o['nombre'],o.get('pct_ponderado')) for o in d['obras'] if o.get('con_panel')])"
```

Anotar el resultado. Mungia debe salir en `80.1`.

- [ ] **Step 3: Añadir el import**

En `generar_todos.py`, junto a los demás imports de módulos propios (buscar la línea `import memoria_obra as mem  # noqa: E402`), añadir debajo:

```python
import ficha_obra as fichas    # noqa: E402
```

- [ ] **Step 4: Añadir el helper que localiza las correcciones más recientes**

Añadir antes de `def cargar_ficha_obra(obra):` en `generar_todos.py`:

```python
def _correcciones_mas_recientes(carpeta_abs):
    """Devuelve los estados del fichero *.correcciones.json mas reciente de la
    obra, o {}. Son marcas escritas a boli sobre la hoja de campo: el dato mas
    directo que hay, y el que mas veces se ha perdido por no casar la clave."""
    import glob
    patron = os.path.join(carpeta_abs, 'REVISIONES', '*.correcciones.json')
    ficheros = glob.glob(patron) or glob.glob(
        os.path.join(carpeta_abs, 'REVISIONES SAGARDE', '*.correcciones.json'))
    if not ficheros:
        return {}

    def fecha(ruta):
        m = re.search(r'(\d{2})(\d{2})(\d{4})', os.path.basename(ruta))
        return (m.group(3), m.group(2), m.group(1)) if m else ('0000', '00', '00')

    try:
        with open(max(ficheros, key=fecha), encoding='utf-8') as f:
            return json.load(f).get('estados') or {}
    except Exception:
        return {}
```

- [ ] **Step 5: Llamar a la actualización dentro del bucle por obra**

En `main()`, localizar la línea que lee `documentos = lectores.listar_documentos(carpeta_abs, salida_dir)` (alrededor de la 769). Justo **después** del bloque donde se calcula `prioridades`, insertar:

```python
        # La ficha absorbe lo que trae esta regeneracion. Si la obra no tiene
        # ficha no pasa nada: sigue funcionando como siempre.
        ficha_actual = fichas.cargar(carpeta_abs)
        if ficha_actual:
            ficha_actual, cambios_ficha = fichas.actualizar(
                ficha_actual, prioridades,
                correcciones=_correcciones_mas_recientes(carpeta_abs),
                mapa_tajos_cortos=_mapa_tajos_cortos(obra['id']),
            )
            fichas.guardar(carpeta_abs, ficha_actual)
            for linea in fichas.resumen_cambios(cambios_ficha):
                print(f"  [FICHA] {linea}")
```

- [ ] **Step 6: Añadir `_mapa_tajos_cortos` a `generar_todos.py`**

Añadir junto al helper anterior:

```python
def _mapa_tajos_cortos(obra_id):
    """Codigo corto del adaptador ('cuad-mec') -> id del catalogo
    ('cuadro_mecanizado'). Las correcciones manuales usan el corto y la ficha
    el largo; sin esta traduccion no se pueden cruzar."""
    try:
        modulo = __import__(f'adaptador_{obra_id}')
    except Exception:
        return {}
    ruta_cat = os.path.join(BASE_DIR, 'reglas', 'CATALOGO_TAJOS.json')
    try:
        with open(ruta_cat, encoding='utf-8') as f:
            catalogo = json.load(f)
    except Exception:
        return {}

    def norm(valor):
        texto = unicodedata.normalize('NFKD', str(valor or ''))
        texto = ''.join(c for c in texto if not unicodedata.combining(c))
        return re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()

    alias = {}
    for tajo in catalogo.get('tajos', []):
        alias[norm(tajo['nombre'])] = tajo['id']
        for otro in tajo.get('aliases', []):
            alias[norm(otro)] = tajo['id']
    corto = getattr(modulo, 'TAJO_NOMBRE_CATALOGO', None) or \
        getattr(modulo, 'TAJO_NOMBRE', {})
    return {c: alias[norm(n)] for c, n in corto.items() if norm(n) in alias}
```

- [ ] **Step 7: Regenerar Mungia y comprobar la regresión**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/_MOTOR_SAGARDE/scripts" && python regenerar_obra.py mungia
```

Esperado: aparecen líneas `[FICHA] ...` y los KPIs mantienen `'pct_ponderado': 80.1`. **Si el porcentaje cambia, parar y averiguar por qué antes de seguir.**

- [ ] **Step 8: Comprobar que la ficha se ha actualizado sola**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python -c "import json,sys; sys.stdout.reconfigure(encoding='utf-8',errors='replace'); f=json.load(open('SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/ficha_obra.json',encoding='utf-8')); print('actualizado:',f['actualizado']); print('revisiones registradas:',[r['id'] for r in f['revisiones']]); from collections import Counter; print(dict(Counter(v['v'] for v in f['estados'].values())))"
```

Esperado: `actualizado` con la hora de ahora, la revisión `rev_27072026` registrada, y el reparto de estados sin celdas perdidas.

- [ ] **Step 9: Comprobar que una obra SIN ficha no cambia**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/_MOTOR_SAGARDE/scripts" && python regenerar_obra.py bolueta
```

Esperado: ninguna línea `[FICHA]`, y `'pct_ponderado': 36.1` intacto.

- [ ] **Step 10: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "La ficha se actualiza sola en cada regeneracion"
```

---

## Task 6: Aviso de ficha rancia

**Files:**
- Modify: `_SISTEMA/ficha_obra.py`
- Modify: `_SISTEMA/tests/test_ficha_obra.py`

**Interfaces:**
- Produces: `ficha_obra.esta_rancia(ficha, prioridades) -> str|None`, que devuelve el motivo si la ficha ha quedado por detrás de los datos, o `None` si está al día.

Red de seguridad: si alguien regenera saltándose la actualización, o edita la ficha a mano y se equivoca, hay que enterarse.

- [ ] **Step 1: Escribir la prueba**

```python
class TestRancia(unittest.TestCase):

    def test_detecta_que_la_ficha_va_por_detras(self):
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item()], revision='20/07/2026'))
        motivo = ficha_obra.esta_rancia(
            ficha, fixtures.prioridades([fixtures.item()], revision='27/07/2026'))
        self.assertIsNotNone(motivo)
        self.assertIn('27/07/2026', motivo)

    def test_no_avisa_cuando_esta_al_dia(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item()], revision='27/07/2026')
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        self.assertIsNone(ficha_obra.esta_rancia(ficha, prio))
```

- [ ] **Step 2: Ejecutar y ver que falla**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_ficha_obra.TestRancia -v
```

Esperado: FAIL con `AttributeError: module 'ficha_obra' has no attribute 'esta_rancia'`.

- [ ] **Step 3: Implementar**

Añadir a `ficha_obra.py`:

```python
def esta_rancia(ficha, prioridades):
    """Devuelve el motivo si la ficha ha quedado por detras de los datos, o
    None si esta al dia.

    La ficha alimenta la hoja de campo. Si se queda atras, se genera una hoja
    con estados de hace dias sin que nadie se entere: por eso conviene que
    grite en vez de fallar en silencio."""
    revision = prioridades.get('revision')
    if not revision:
        return None
    registradas = {r.get('fecha') for r in ficha.get('revisiones') or []}
    if revision not in registradas:
        return (f'la ficha no ha registrado la revision {revision}; '
                f'ultima registrada: {max(registradas, key=_orden_fecha) if registradas else "ninguna"}')
    return None
```

- [ ] **Step 4: Ejecutar y ver que pasa**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -v
```

Esperado: todas OK.

- [ ] **Step 5: Avisar desde `generar_todos.py`**

En `registro_revision_desde_ficha`, al principio de la función, añadir:

```python
    motivo = fichas.esta_rancia(ficha, prioridades)
    if motivo:
        print(f"  [AVISO FICHA] {obra['nombre']}: {motivo}. "
              f"La hoja de campo puede salir con estados atrasados.")
```

- [ ] **Step 6: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "Aviso cuando la ficha se queda por detras de los datos"
```

---

## Task 7: Rellenar identidad, materiales, documentos y contactos

**Files:**
- Modify: `_SISTEMA/ficha_obra.py`
- Modify: `_SISTEMA/generar_todos.py`
- Modify: `_SISTEMA/tests/test_ficha_obra.py`

**Interfaces:**
- Consumes: la salida de `lectores.leer_ficha`, `lectores.leer_materiales` y `lectores.listar_documentos` (firmas al principio de este plan)
- Produces: `ficha_obra.volcar_apartados(ficha, ficha_xlsx=None, materiales=None, documentos=None) -> list[str]` con los nombres de los apartados que han cambiado.

Esto es el "absolutamente todo bien estructurado". Hoy esos tres apartados están vacíos y `identidad` solo tiene nombre, carpeta y tipo.

- [ ] **Step 1: Escribir las pruebas**

```python
class TestApartadosRellenos(unittest.TestCase):

    def test_identidad_toma_los_datos_del_xlsx_sin_pisar_lo_que_ya_hay(self):
        ficha = fixtures.ficha_minima()
        ficha['identidad']['tipo_obra'] = 'viviendas'
        cambiados = ficha_obra.volcar_apartados(ficha, ficha_xlsx={
            '_disponible': True,
            'datos': {'Cliente': 'NEINOR', 'Constructora': 'ACR'},
            'personal': [{'Nombre': 'Bixente', 'Rol': 'Jefe de obra'}],
            'hitos': [], 'riesgos': [], 'plan': [],
        })
        self.assertEqual(ficha['identidad']['cliente'], 'NEINOR')
        self.assertEqual(ficha['identidad']['constructora'], 'ACR')
        self.assertEqual(ficha['identidad']['tipo_obra'], 'viviendas')
        self.assertEqual(len(ficha['contactos']), 1)
        self.assertIn('identidad', cambiados)

    def test_materiales_guarda_resumen_y_no_la_lista_entera(self):
        ficha = fixtures.ficha_minima()
        ficha_obra.volcar_apartados(ficha, materiales={
            'disponible': True, 'meses': ['Junio26', 'Julio26'],
            'ultimo_mes': 'Julio26', 'ultima_fecha': '20/07/2026',
            'dias_desde': 7, 'aviso': None,
            'items': [{'categoria': 'Cable', 'material': 'RZ1 3G1.5',
                       'tipo': 'm', 'uni': 'm', 'total': 500}],
        })
        self.assertEqual(ficha['materiales']['ultimo_mes'], 'Julio26')
        self.assertEqual(ficha['materiales']['n_items'], 1)
        self.assertEqual(ficha['materiales']['dias_desde'], 7)

    def test_documentos_guarda_el_recuento_por_categoria(self):
        ficha = fixtures.ficha_minima()
        ficha_obra.volcar_apartados(ficha, documentos=[
            {'nombre': 'a.pdf', 'categoria': 'Planos', 'subcarpeta': '.',
             'href': 'a.pdf', 'kb': 100},
            {'nombre': 'b.pdf', 'categoria': 'Planos', 'subcarpeta': '.',
             'href': 'b.pdf', 'kb': 50},
            {'nombre': 'c.xlsx', 'categoria': 'Otros', 'subcarpeta': 'x',
             'href': 'x/c.xlsx', 'kb': 10},
        ])
        self.assertEqual(ficha['documentos']['total'], 3)
        self.assertEqual(ficha['documentos']['por_categoria']['Planos'], 2)

    def test_sin_datos_no_marca_nada_como_cambiado(self):
        ficha = fixtures.ficha_minima()
        self.assertEqual(ficha_obra.volcar_apartados(ficha), [])
```

- [ ] **Step 2: Ejecutar y ver que falla**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_ficha_obra.TestApartadosRellenos -v
```

Esperado: FAIL con `AttributeError: module 'ficha_obra' has no attribute 'volcar_apartados'`.

- [ ] **Step 3: Implementar**

Añadir a `ficha_obra.py`:

```python
# Etiqueta tal y como aparece en la hoja 'Datos' del xlsx -> campo de la ficha
CAMPOS_IDENTIDAD = {
    'cliente': 'cliente', 'promotora': 'promotora',
    'constructora': 'constructora', 'direccion': 'direccion',
    'codigo': 'codigo', 'codigo de obra': 'codigo',
    'fecha inicio': 'fecha_inicio', 'fecha fin': 'fecha_fin',
    'fecha fin prevista': 'fecha_fin', 'jefe de obra': 'jefe_obra',
    'responsable': 'jefe_obra',
}


def volcar_apartados(ficha, ficha_xlsx=None, materiales=None, documentos=None):
    """Rellena identidad, contactos, materiales y documentos desde los lectores.

    Solo escribe lo que viene con dato: nunca pisa un valor existente con vacio,
    porque la ficha es acumulativa y un xlsx incompleto no debe borrar lo que ya
    se sabia. Devuelve la lista de apartados que han cambiado."""
    asegurar_apartados(ficha)
    cambiados = []

    if ficha_xlsx and ficha_xlsx.get('_disponible'):
        identidad = ficha['identidad']
        toco = False
        for etiqueta, valor in (ficha_xlsx.get('datos') or {}).items():
            campo = CAMPOS_IDENTIDAD.get(_fold(etiqueta))
            if campo and valor not in (None, ''):
                if identidad.get(campo) != valor:
                    identidad[campo] = valor
                    toco = True
        if toco:
            identidad.setdefault('_meta', {})['actualizado'] = _ahora()
            cambiados.append('identidad')
        personal = ficha_xlsx.get('personal') or []
        if personal and personal != ficha.get('contactos'):
            ficha['contactos'] = personal
            cambiados.append('contactos')

    if materiales and materiales.get('disponible'):
        resumen = {
            'ultimo_mes': materiales.get('ultimo_mes'),
            'ultima_fecha': materiales.get('ultima_fecha'),
            'dias_desde': materiales.get('dias_desde'),
            'meses': materiales.get('meses') or [],
            'n_items': len(materiales.get('items') or []),
            'aviso': materiales.get('aviso'),
            '_meta': {'actualizado': _ahora()},
        }
        if {k: v for k, v in resumen.items() if k != '_meta'} != \
           {k: v for k, v in (ficha.get('materiales') or {}).items() if k != '_meta'}:
            ficha['materiales'] = resumen
            cambiados.append('materiales')

    if documentos:
        por_categoria = {}
        for doc in documentos:
            categoria = doc.get('categoria') or 'Otros'
            por_categoria[categoria] = por_categoria.get(categoria, 0) + 1
        resumen = {'total': len(documentos), 'por_categoria': por_categoria,
                   '_meta': {'actualizado': _ahora()}}
        anterior = ficha.get('documentos') or {}
        if (anterior.get('total'), anterior.get('por_categoria')) != \
           (resumen['total'], resumen['por_categoria']):
            ficha['documentos'] = resumen
            cambiados.append('documentos')

    return cambiados
```

- [ ] **Step 4: Ejecutar y ver que pasa**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -v
```

Esperado: todas OK.

- [ ] **Step 5: Conectar a `generar_todos.py`**

En `main()`, dentro del bloque `if ficha_actual:` añadido en la Task 5, justo **antes** de `fichas.guardar(...)`, insertar:

```python
            tocados = fichas.volcar_apartados(
                ficha_actual, ficha_xlsx=ficha, materiales=materiales,
                documentos=documentos)
            if tocados:
                print(f"  [FICHA] apartados actualizados: {', '.join(tocados)}")
```

Nota: `ficha`, `materiales` y `documentos` son las variables que `main()` ya tiene en ese punto (líneas ~767-769). Cuidado de no confundir la variable local `ficha` (el xlsx leído por `lectores.leer_ficha`) con `ficha_actual` (la ficha de obra JSON).

- [ ] **Step 6: Regenerar Mungia y comprobar**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/_MOTOR_SAGARDE/scripts" && python regenerar_obra.py mungia
```

Esperado: `'pct_ponderado': 80.1` intacto y una línea `[FICHA] apartados actualizados: ...`.

- [ ] **Step 7: Verificar que ya no quedan apartados vacíos**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python -c "import json,sys; sys.stdout.reconfigure(encoding='utf-8',errors='replace'); f=json.load(open('SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/ficha_obra.json',encoding='utf-8')); [print('%-14s %s'%(k, 'VACIO' if not [x for x in (f[k] if isinstance(f[k],(dict,list)) else []) if not str(x).startswith('_')] else 'con datos')) for k in ['identidad','estructura','tajos','estados','revisiones','dudas','materiales','documentos','contactos']]"
```

Esperado: ninguno en `VACIO`, salvo los que la obra realmente no tenga (si Mungia no tiene `FICHA DE OBRA.xlsx`, `identidad` y `contactos` seguirán cortos: eso es correcto y se anota como pendiente de rellenar a mano).

- [ ] **Step 8: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "La ficha recoge identidad, materiales, documentos y contactos"
```

---

## Comprobación final del plan

- [ ] **Todas las pruebas pasan**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -v
```

- [ ] **Regeneración completa sin sorpresas**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py" --no-pdf
```

Esperado: Mungia `80.1`, Gernika `76.3`, Bolueta `36.1`, Obispo Orueta `80.0`. Avisos `[FICHA]` solo para Mungia.

- [ ] **Prueba del ciclo completo**: meter una revisión nueva de Mungia, regenerar, y comprobar que la ficha registra la revisión y que el generador ofrece los estados nuevos sin resembrar nada a mano.

---

## Fuera del alcance de este plan

Cada uno tendrá su propio plan cuando este esté cerrado:

- **P3 — Gernika y Bolueta**: sembrar sus fichas, con la ronda de confirmación de estructura que hizo falta en Mungia.
- **P4 — Gorliz**: alta de obra nueva sin ninguna revisión previa, más el lector de carpeta que propone la estructura desde presupuestos y proyectos.
- **P5 — Panel e informes desde la ficha**: hoy solo la consume el generador de hojas; el panel sigue leyendo de `prioridades_trabajos.json`.
- **P6 — Limpiar duplicados**: un solo catálogo de tajos (hoy hay tres), un solo registro de obras (hoy `OBRAS` en `generar_todos.py` y `ADAPTADORES` en `generar_informe_ejecutivo.py`), un solo formato de clave de celda (hoy conviven el corto y el largo).
- **Garajes de Mungia y Gernika**: la Task 3 ya deja el mecanismo listo (entran como alta sin confirmar), pero conviene declararlos en las confirmaciones de estructura cuando llegue el momento.
