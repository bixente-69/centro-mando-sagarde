# Fase A — Inversión del flujo: la ficha alimenta al motor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que los KPIs, el priorizador, el panel de obra y el informe ejecutivo de Mungia se calculen a partir de `ficha_obra.json` en vez de calcularse antes que ella.

**Architecture:** Todo el sistema consume el mismo formato de registro — `{'task','floor','building','unit','status'}` — que viaja en el `historial` que devuelve cada adaptador. La inversión no exige reescribir el motor ni el priorizador ni el panel: basta con **sustituir el último snapshot del historial por uno derivado de la ficha**, justo después de actualizarla y antes de que nadie calcule nada. Un módulo aporta la traducción; `generar_todos.py` la conecta en una línea.

**Tech Stack:** Python 3.11.9 en Windows, biblioteca estándar únicamente. Pruebas con `unittest`. **No introducir pytest ni ninguna dependencia**: Bixente ejecuta todo con ficheros `.bat`.

## Global Constraints

- Raíz: `D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE`. `_SISTEMA` = `SAGARDE OBRAS ABIERTAS\_SISTEMA INFORME SAGARDE IA\`
- **Una obra SIN `ficha_obra.json` debe comportarse EXACTAMENTE como hoy.** De 5 obras registradas solo Mungia tiene ficha. Gernika, Bolueta y Obispo Orueta son la prueba de que no se rompe nada.
- **El porcentaje redondeado es un criterio ciego**: 3 celdas sobre 2309 no lo mueven. Verificar siempre el desglose `x / m / slash / vacio`.
- Línea base a 27/07/2026, antes de esta fase:

| Obra | x | m | / | vacío | total | pct |
|---|---|---|---|---|---|---|
| Mungia | 1798 | 84 | 0 | 427 | 2309 | 80.1 |
| Gernika | 928 | 0 | 0 | 288 | 1216 | 76.3 |
| Bolueta | 1265 | 76 | 20 | 2287 | 3648 | 36.1 |
| Obispo Orueta | 2392 | 0 | 0 | 8 | 2400 | 80.0 |

- Alfabeto guardado en la ficha: `X` terminado · `M` más del 50% · `/` iniciado · `P` pendiente confirmado · `?` desconocido · `N` no aplica.
- **Se guarda lo medido, se recalcula lo derivado.** No persistir `BLOQUEADO`, `DUDAS`, `VIABLE` ni `OTROS_GREMIOS`.
- Norma de obra: *"lo que se apunta en la última revisión es lo que vale"*.
- Los `.py` están versionados en git desde `3e318f3`. **No hacer copias `.bak`.**
- `Actualizar_Sagarde.bat` hace `git add -A`: **no dejar el árbol con cambios a medias**, y restaurar siempre cualquier fichero mutado para una verificación. Han ocurrido dos incidentes en un día.
- `regenerar_obra.py <obra>` sustituye `publicar_registro_revisiones` por una función vacía: para el camino de publicación usar `--finalizar`.
- Codificación: todo script de diagnóstico empieza con `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`.

---

## Estructura de ficheros

| Fichero | Responsabilidad | Estado |
|---|---|---|
| `_SISTEMA/ficha_obra.py` | Fuente de verdad. Se le añade la traducción ficha → snapshot y una variante de actualización que consume el snapshot crudo. | Modificar |
| `_SISTEMA/generar_todos.py` | Orquestador. Reordena: actualizar ficha primero, derivar el snapshot después. | Modificar |
| `_SISTEMA/tests/test_ficha_obra.py` | Pruebas del módulo. | Modificar |
| `_SISTEMA/motor_informes.py` | Calcula KPIs desde un snapshot. **No se toca**: ya consume el formato correcto. | Intacto |
| `_SISTEMA/priorizador_trabajos.py` | Clasifica desde un historial. **No se toca.** | Intacto |
| `_SISTEMA/panel_obra.py` | Genera el HTML. **No se toca.** | Intacto |

**Por qué tres ficheros no se tocan:** todos consumen `{'task','floor','building','unit','status'}`. Si el snapshot que reciben sale de la ficha, ya están leyendo de la ficha. Esa es toda la inversión.

**Interfaz existente que se consume (no reimplementar):**

```python
motor_informes.kpis_snapshot(snapshot)
# -> {'total','x','m','slash','vacio','pct_estricto','pct_ponderado'}
# snapshot: [{'task','floor','building','unit','status'}, ...]

priorizador_trabajos.priorizar_historial(historial, obra='')
# historial: [(fecha_dd/mm/aaaa, snapshot), ...] ordenado por fecha

adaptador.cargar_historial()   # todos los adaptadores exponen esto
# -> historial en el mismo formato
```

---

## Task 1: Traducir la ficha a snapshot

**Files:**
- Modify: `_SISTEMA/ficha_obra.py`
- Modify: `_SISTEMA/tests/test_ficha_obra.py`

**Interfaces:**
- Consumes: `fixtures.ficha_minima()`, `fixtures.item()`, `fixtures.prioridades()`, `ficha_obra.actualizar()`
- Produces: `ficha_obra.snapshot_desde_ficha(ficha) -> list[dict]`, donde cada dict tiene exactamente las claves `task`, `floor`, `building`, `unit`, `status`.

Es la pieza central de la fase. Traduce el árbol de la ficha al formato plano que consume todo el sistema.

**Reglas de traducción — cada una tiene un porqué:**

| Estado en la ficha | En el snapshot | Motivo |
|---|---|---|
| `X` `M` `/` | igual | Son los estados que el motor entiende |
| `P` | `''` | Pendiente confirmado: cuenta como no iniciado y **entra en el denominador** |
| `?` | **se excluye** | Desconocido. Meterlo como `''` sería afirmar que está pendiente, que es justo lo que no consta |
| `N` | **se excluye** | No aplica a esa ubicación: no debe ensuciar el porcentaje |

Los nombres se devuelven como los espera el catálogo: `building` es la
referencia del portal, `floor` el nombre de la planta, `unit` el alias
histórico si existe (`A2`) y si no el id canónico (`A`), y `task` el nombre del
tajo, no su id.

- [ ] **Step 1: Escribir las pruebas**

Añadir al final de `_SISTEMA/tests/test_ficha_obra.py`:

```python
class TestSnapshotDesdeFicha(unittest.TestCase):

    def _ficha_con_estados(self, valores):
        """valores: {clave_celda: estado}. Devuelve una ficha con esos
        estados y el resto de la matriz en '?'."""
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='X')]))
        for clave, valor in valores.items():
            ficha['estados'][clave] = {'v': valor, 'f': '27/07/2026',
                                       'r': 'rev_27072026'}
        return ficha

    def test_devuelve_las_claves_que_espera_el_motor(self):
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': 'X'})
        fila = next(r for r in ficha_obra.snapshot_desde_ficha(ficha)
                    if r['unit'] == 'A' and r['task'] == 'Tubeado'
                    and r['floor'] == 'PB')
        self.assertEqual(set(fila), {'task', 'floor', 'building', 'unit', 'status'})
        self.assertEqual(fila['building'], 'P1')
        self.assertEqual(fila['status'], 'X')

    def test_pendiente_confirmado_viaja_como_vacio(self):
        """P entra en el denominador: se comprobo y no esta hecho."""
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': 'P'})
        fila = next(r for r in ficha_obra.snapshot_desde_ficha(ficha)
                    if r['unit'] == 'A' and r['task'] == 'Tubeado'
                    and r['floor'] == 'PB')
        self.assertEqual(fila['status'], '')

    def test_desconocido_se_excluye_del_snapshot(self):
        """? no puede contar como pendiente: seria afirmar lo que no consta."""
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': '?'})
        filas = [r for r in ficha_obra.snapshot_desde_ficha(ficha)
                 if r['unit'] == 'A' and r['task'] == 'Tubeado'
                 and r['floor'] == 'PB']
        self.assertEqual(filas, [])

    def test_no_aplica_se_excluye_del_snapshot(self):
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': 'N'})
        filas = [r for r in ficha_obra.snapshot_desde_ficha(ficha)
                 if r['unit'] == 'A' and r['task'] == 'Tubeado'
                 and r['floor'] == 'PB']
        self.assertEqual(filas, [])

    def test_usa_el_nombre_historico_de_la_unidad_si_existe(self):
        """En Mungia el id canonico es 'A' pero la hoja dice 'A2'."""
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': 'X'})
        ficha['estructura']['alias_historico'] = {'p1__pb__A': 'A2'}
        unidades = {r['unit'] for r in ficha_obra.snapshot_desde_ficha(ficha)
                    if r['floor'] == 'PB'}
        self.assertIn('A2', unidades)
        self.assertNotIn('A', unidades)

    def test_devuelve_el_nombre_del_tajo_no_su_id(self):
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': 'X'})
        tareas = {r['task'] for r in ficha_obra.snapshot_desde_ficha(ficha)}
        self.assertIn('Tubeado', tareas)
        self.assertNotIn('tubeado', tareas)

    def test_una_ficha_sin_estados_devuelve_lista_vacia(self):
        ficha = fixtures.ficha_minima()
        self.assertEqual(ficha_obra.snapshot_desde_ficha(ficha), [])
```

- [ ] **Step 2: Ejecutar y ver que falla**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_ficha_obra.TestSnapshotDesdeFicha -v
```

Esperado: FAIL con `AttributeError: module 'ficha_obra' has no attribute 'snapshot_desde_ficha'`.

- [ ] **Step 3: Implementar**

Añadir a `ficha_obra.py`, después de `volcar_apartados`:

```python
# Estado guardado -> estado que entiende el motor. Los que no aparecen aqui
# se EXCLUYEN del snapshot a proposito:
#   '?' desconocido -> meterlo como '' seria afirmar que esta pendiente
#   'N' no aplica   -> no debe entrar en el denominador del porcentaje
ESTADO_A_SNAPSHOT = {'X': 'X', 'M': 'M', '/': '/', 'P': ''}


def snapshot_desde_ficha(ficha):
    """Traduce la ficha al formato plano que consume todo el sistema:
    [{'task','floor','building','unit','status'}, ...]

    Es la pieza que invierte el flujo. Hasta ahora los KPIs, el priorizador,
    el panel y los informes se calculaban desde lo que leia el adaptador, y la
    ficha era un subproducto que se escribia despues: corregir la ficha no
    corregia los numeros publicados. Pasando por aqui, lo que se publica sale
    de la ficha.
    """
    alias = (ficha.get('estructura') or {}).get('alias_historico') or {}
    nombres_tajo = {t['id']: (t.get('nombre') or t['id'])
                    for t in (ficha.get('tajos') or {}).get('detalle') or []}
    estados = ficha.get('estados') or {}

    filas = []
    for bloque in (ficha.get('estructura') or {}).get('bloques') or []:
        for portal in bloque.get('portales') or []:
            edificio = portal.get('referencia') or portal.get('nombre') or portal['id']
            for planta in portal.get('plantas') or []:
                for ubi in planta.get('ubicaciones') or []:
                    clave_alias = f"{portal['id']}__{planta['id']}__{ubi['id']}"
                    unidad = alias.get(clave_alias, ubi['id'])
                    for tajo_id, nombre in nombres_tajo.items():
                        clave = (f"{portal['id']}__{planta['id']}"
                                 f"__{tajo_id}__{ubi['id']}")
                        dato = estados.get(clave)
                        if not dato:
                            continue
                        estado = ESTADO_A_SNAPSHOT.get(dato.get('v'))
                        if estado is None:
                            continue      # '?' o 'N': fuera del calculo
                        filas.append({
                            'task': nombre,
                            'floor': planta.get('nombre') or planta['id'],
                            'building': edificio,
                            'unit': unidad,
                            'status': estado,
                        })
    return filas
```

- [ ] **Step 4: Ejecutar y ver que pasa**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -v
```

Esperado: las 44 anteriores más las 7 nuevas, todas OK.

- [ ] **Step 5: Medir la ficha real de Mungia**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python -c "
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, 'SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA')
import ficha_obra, motor_informes
f = json.load(open('SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/ficha_obra.json', encoding='utf-8'))
snap = ficha_obra.snapshot_desde_ficha(f)
print('KPIs desde la ficha:', motor_informes.kpis_snapshot(snap))
"
```

Anotar el resultado en el informe. **No lo compares aún con la línea base**: la Task 2 es la que lo conecta. Aquí solo se documenta qué dice la ficha.

- [ ] **Step 6: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "La ficha se puede traducir al formato que consume el motor"
```

---

## Task 2: Actualizar la ficha desde el snapshot crudo

**Files:**
- Modify: `_SISTEMA/ficha_obra.py`
- Modify: `_SISTEMA/tests/test_ficha_obra.py`

**Interfaces:**
- Consumes: `ficha_obra.actualizar(ficha, prioridades, correcciones=None, mapa_tajos_cortos=None) -> (ficha, cambios)`
- Produces: `ficha_obra.actualizar_desde_snapshot(ficha, snapshot, revision, correcciones=None, mapa_tajos_cortos=None) -> (ficha, cambios)`, con el mismo dict `cambios` que devuelve `actualizar`.

**Por qué hace falta.** Hoy la ficha se actualiza desde `prioridades_trabajos.json`, que ya es el resultado de haber pasado por el priorizador. Si además el priorizador va a leer de la ficha, se forma un ciclo. Esta función rompe el ciclo: la ficha se alimenta del **snapshot crudo** que devuelve el adaptador, antes de que nadie calcule nada.

La diferencia con `actualizar` es solo la forma de la entrada. El snapshot trae `{'task','floor','building','unit','status'}` con el **nombre** del tajo; `actualizar` espera items con `tarea_id`, `edificio`, `planta`, `unidad`, `estado_actual`. Hay que traducir y delegar, no duplicar la lógica.

- [ ] **Step 1: Escribir las pruebas**

```python
class TestActualizarDesdeSnapshot(unittest.TestCase):

    def test_un_snapshot_crudo_actualiza_los_estados(self):
        ficha = fixtures.ficha_minima()
        snapshot = [{'task': 'Tubeado', 'floor': 'PB', 'building': 'P1',
                     'unit': 'A', 'status': 'X'}]
        ficha, cambios = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['f'], '27/07/2026')

    def test_la_casilla_vacia_del_snapshot_se_guarda_como_pendiente(self):
        ficha = fixtures.ficha_minima()
        snapshot = [{'task': 'Tubeado', 'floor': 'PB', 'building': 'P1',
                     'unit': 'A', 'status': ''}]
        ficha, _ = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'P')

    def test_reclama_las_correcciones_manuales(self):
        ficha = fixtures.ficha_minima()
        snapshot = [{'task': 'Tubeado', 'floor': 'PB', 'building': 'P1',
                     'unit': 'A', 'status': ''}]
        ficha, cambios = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026',
            correcciones={'p1__pb__tubeado__A': 'X'})
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')
        self.assertEqual(len(cambios['correcciones_reclamadas']), 1)

    def test_una_ubicacion_desconocida_entra_sin_confirmar_y_avisa(self):
        ficha = fixtures.ficha_minima()
        snapshot = [{'task': 'Tubeado', 'floor': 'PB', 'building': 'P1',
                     'unit': 'C', 'status': 'X'}]
        ficha, cambios = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026')
        self.assertTrue(any('unidad C' in a for a in cambios['ubicaciones_nuevas']))

    def test_registra_la_revision(self):
        ficha = fixtures.ficha_minima()
        snapshot = [{'task': 'Tubeado', 'floor': 'PB', 'building': 'P1',
                     'unit': 'A', 'status': 'X'}]
        ficha, cambios = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026')
        self.assertEqual(cambios['revision_registrada'], 'rev_27072026')
```

- [ ] **Step 2: Ejecutar y ver que falla**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_ficha_obra.TestActualizarDesdeSnapshot -v
```

Esperado: FAIL con `AttributeError: ... has no attribute 'actualizar_desde_snapshot'`.

- [ ] **Step 3: Implementar**

Añadir a `ficha_obra.py`, justo antes de `def actualizar(`:

```python
def actualizar_desde_snapshot(ficha, snapshot, revision, correcciones=None,
                              mapa_tajos_cortos=None):
    """Igual que `actualizar`, pero comiendo el snapshot CRUDO del adaptador.

    Rompe el ciclo: hasta ahora la ficha se alimentaba de
    prioridades_trabajos.json, que ya venia del priorizador. Para que el
    priorizador pueda leer de la ficha, la ficha tiene que alimentarse de algo
    anterior — el snapshot tal cual sale de la hoja de revision.
    """
    id_por_nombre = {}
    for tajo in (ficha.get('tajos') or {}).get('detalle') or []:
        id_por_nombre[_fold(tajo.get('nombre') or '')] = tajo['id']

    items = []
    for reg in snapshot or []:
        nombre = str(reg.get('task') or '').strip()
        if not nombre:
            continue
        # Un tajo que la ficha no conoce entra por su nombre: `actualizar`
        # lo dara de alta marcado sin confirmar y avisara.
        tarea_id = id_por_nombre.get(_fold(nombre), nombre)
        items.append({
            'tarea_id': tarea_id,
            'trabajo': nombre,
            'ambito': 'vivienda',
            'propiedad': 'propio',
            'fase_nombre': 'Sin clasificar',
            'orden_ejecucion': 9999,
            'edificio': reg.get('building'),
            'planta': reg.get('floor'),
            'unidad': reg.get('unit'),
            'estado_actual': reg.get('status', ''),
            'ultima_fecha': revision,
        })

    prioridades = {'revision': revision, 'detalle_items': items}
    return actualizar(ficha, prioridades, correcciones=correcciones,
                      mapa_tajos_cortos=mapa_tajos_cortos)
```

**Limitación conocida y deliberada.** El snapshot crudo no trae ámbito ni fase
del tajo: esos datos viven en el catálogo, no en la hoja. Por eso los items se
construyen con `ambito='vivienda'` y `fase_nombre='Sin clasificar'`. Solo
afecta a **tajos que la ficha no conozca todavía**, que entrarán marcados
`revision_sin_confirmar` y avisando, para que Bixente los corrija. Los tajos ya
conocidos conservan su ámbito y su fase, porque `actualizar` no los reescribe.
En Mungia los 38 tajos son conocidos, así que este camino no se ejercita. No
inventar aquí un ámbito "adivinado" a partir del nombre: sería exactamente el
tipo de dato inventado que este proyecto prohíbe.

- [ ] **Step 4: Ejecutar y ver que pasa**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -v
```

Esperado: 56 pruebas OK (44 + 7 de la Task 1 + 5 de esta).

- [ ] **Step 5: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "La ficha se puede alimentar del snapshot crudo del adaptador"
```

---

## Task 3: Invertir el flujo en el orquestador

**Files:**
- Modify: `_SISTEMA/generar_todos.py` (función `main`, alrededor de las líneas 846-880)

**Interfaces:**
- Consumes: `ficha_obra.actualizar_desde_snapshot`, `ficha_obra.snapshot_desde_ficha`, `ficha_obra.cargar`, `ficha_obra.guardar`, `ficha_obra.resumen_cambios`, `_correcciones_mas_recientes`, `_mapa_tajos_cortos`
- Produces: efecto lateral — para una obra con ficha, el `historial` que reciben la memoria, el priorizador, los KPIs, el panel y el informe lleva como último snapshot el derivado de la ficha.

Es la tarea que cambia el comportamiento del sistema. Todo lo anterior era preparación.

**El orden importa y es el núcleo de la fase:**

```
1. historial = adaptador.cargar_historial()        ← crudo, de la hoja
2. si hay ficha:
     ficha = actualizar_desde_snapshot(ficha, historial[-1][1], fecha, correcciones)
     guardar(ficha)
     historial[-1] = (fecha, snapshot_desde_ficha(ficha))   ← LA INVERSION
3. memoria, priorizador, KPIs, panel, informe        ← ya leen de la ficha
```

- [ ] **Step 1: Anotar la línea base antes de tocar nada**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/_MOTOR_SAGARDE/scripts" && python regenerar_obra.py mungia 2>&1 | grep KPIs
```

Esperado hoy: `{'total': 2309, 'x': 1798, 'm': 84, 'slash': 0, 'vacio': 427, 'pct_estricto': 77.9, 'pct_ponderado': 80.1}`. Anotarlo literal en el informe.

- [ ] **Step 2: Localizar el punto de inserción**

En `generar_todos.py`, la función `main()` contiene:

```python
            adaptador = __import__(obra['adaptador'])
            historial = adaptador.cargar_historial()
```

y más abajo, dentro del `try` siguiente, el bloque que empieza con
`tajos_memoria = mem.calcular_memoria(historial)`.

Entre esos dos puntos hay que insertar la inversión. **Importante:** el bloque
actual que llama a `fichas.cargar` / `fichas.actualizar` / `fichas.guardar`
está DESPUÉS del priorizador; hay que **retirarlo de ahí** y sustituirlo por el
bloque nuevo, o la ficha se actualizaría dos veces por pasada.

- [ ] **Step 3: Implementar la inversión**

Sustituir el bloque de actualización de ficha existente por este, colocado
inmediatamente ANTES de `tajos_memoria = mem.calcular_memoria(historial)`:

```python
            # ── INVERSION DEL FLUJO ──────────────────────────────────────
            # La ficha se alimenta del snapshot crudo y, a partir de aqui,
            # TODO lo demas (memoria, priorizador, KPIs, panel, informe) lee
            # el snapshot derivado de la ficha. Antes de esto, la ficha era un
            # subproducto que se escribia despues de calcular, asi que
            # corregirla no corregia los numeros publicados.
            # Una obra sin ficha no entra aqui y sigue igual que siempre.
            ficha_actual = fichas.cargar(carpeta_abs)
            if ficha_actual and historial:
                fecha_ultima, snapshot_crudo = historial[-1]
                ficha_actual, cambios_ficha = fichas.actualizar_desde_snapshot(
                    ficha_actual, snapshot_crudo, fecha_ultima,
                    correcciones=_correcciones_mas_recientes(carpeta_abs),
                    mapa_tajos_cortos=_mapa_tajos_cortos(obra['id']),
                )
                tocados = fichas.volcar_apartados(
                    ficha_actual, ficha_xlsx=ficha, materiales=materiales,
                    documentos=documentos)
                fichas.guardar(carpeta_abs, ficha_actual)
                for linea in fichas.resumen_cambios(cambios_ficha):
                    print(f"  [FICHA] {linea}")
                if tocados:
                    print(f"  [FICHA] apartados actualizados: {', '.join(tocados)}")

                snapshot_ficha = fichas.snapshot_desde_ficha(ficha_actual)
                if snapshot_ficha:
                    historial[-1] = (fecha_ultima, snapshot_ficha)
                    print(f"  [FICHA] el sistema lee de la ficha: "
                          f"{len(snapshot_ficha)} registros")
                else:
                    print(f"  [AVISO FICHA] {obra['nombre']}: la ficha no "
                          f"produce ningun registro. Se sigue con los datos "
                          f"del adaptador.")
```

**Cuidado con la colisión de nombres:** en `main()` la variable `ficha` es el
Excel leído por `lectores.leer_ficha(...)`, y `ficha_actual` es la ficha de
obra JSON. Si `ficha`, `materiales` o `documentos` todavía no están leídos en
ese punto del código, hay que adelantar sus lecturas, igual que se hizo en la
tarea anterior del plan previo.

- [ ] **Step 4: Regenerar Mungia y comparar el desglose**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/_MOTOR_SAGARDE/scripts" && python regenerar_obra.py mungia 2>&1 | grep -E "FICHA|KPIs|Prioridades"
```

**Esto es el criterio de aceptación de la fase.** Se espera que `x` y `m`
**suban** respecto a la línea base (1798 / 84), porque las correcciones
manuales que la ficha ya tenía llegan por fin al cálculo.

**Obligatorio: justificar celda a celda cada diferencia.** No basta con que el
porcentaje cuadre. Si `total` cambia, explicar por qué (las celdas `?` y `N` se
excluyen a propósito). Si algún número baja, **parar e investigar**: sería
señal de que la traducción pierde datos.

- [ ] **Step 5: Comprobar que las obras sin ficha no se mueven**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/_MOTOR_SAGARDE/scripts" && python regenerar_obra.py gernika 2>&1 | grep -E "FICHA|KPIs"
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/_MOTOR_SAGARDE/scripts" && python regenerar_obra.py bolueta 2>&1 | grep -E "FICHA|KPIs"
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/_MOTOR_SAGARDE/scripts" && python regenerar_obra.py obisporueta 2>&1 | grep -E "FICHA|KPIs"
```

Esperado, **exacto**: Gernika `x=928, m=0, slash=0, vacio=288, pct 76.3`;
Bolueta `x=1265, m=76, slash=20, vacio=2287, pct 36.1`; Obispo Orueta
`x=2392, m=0, slash=0, vacio=8, pct 80.0`. Ninguna debe imprimir líneas
`[FICHA]`. **Cualquier desviación es un fallo de la tarea.**

- [ ] **Step 6: Comprobar que las pruebas siguen verdes**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Esperado: 56 OK.

- [ ] **Step 7: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "Invertir el flujo: el sistema lee de la ficha"
```

---

## Task 4: Verificar que el panel y el informe reflejan la ficha

**Files:**
- Ninguno que modificar. Es una tarea de verificación end-to-end.

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: la evidencia de que la fase A cumple su objetivo.

Las tareas anteriores cambian de dónde salen los datos. Esta comprueba que el
cambio se ve donde tiene que verse: en lo que Bixente mira y en lo que entrega
al cliente.

- [ ] **Step 1: Regeneración completa**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE/_MOTOR_SAGARDE/scripts" && python regenerar_obra.py --finalizar
```

Se usa `--finalizar` a propósito: `regenerar_obra.py <obra>` sustituye
`publicar_registro_revisiones` por una función vacía y no ejercita el camino de
publicación.

- [ ] **Step 2: Comprobar que las 3 correcciones del PORTAL llegan al panel**

Son las que motivaron toda la fase: `p2__pb__suelo_radiante__PORTAL`,
`p2__pb__suelo_recrecido__PORTAL` y `p2__pb__agujeros_iluminacion_zzcc__PORTAL`.

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python -c "
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
O = 'SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/'
f = json.load(open(O + 'ficha_obra.json', encoding='utf-8'))
p = json.load(open(O + 'prioridades_trabajos.json', encoding='utf-8'))
pares = [('suelo_radiante', 'X'), ('suelo_recrecido', 'X'),
         ('agujeros_iluminacion_zzcc', 'M')]
for tajo, esperado in pares:
    en_ficha = f['estados'].get('p2__pb__%s__PORTAL' % tajo, {}).get('v')
    en_prio = [i['estado_actual'] for i in p['detalle_items']
               if i['tarea_id'] == tajo and i['edificio'] == 'ZR1.2'
               and str(i['planta']).upper() == 'PB']
    print('%-28s ficha=%-3s prioridades=%s  esperado=%s' %
          (tajo, en_ficha, en_prio, esperado))
"
```

Esperado: los tres coinciden entre ficha y prioridades. **Antes de esta fase
coincidían solo en la ficha.** Si `prioridades` sigue discrepando, la inversión
no ha llegado hasta el priorizador y la tarea no está hecha.

- [ ] **Step 3: Comprobar que la vivienda E aparece en el panel**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python -c "
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = json.load(open('SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/prioridades_trabajos.json', encoding='utf-8'))
e = [i for i in p['detalle_items']
     if i['edificio'] == 'ZR2.1' and str(i['planta']) == '2' and i['unidad'] == 'E']
print('celdas de la vivienda E de ZR2.1 planta 2 en el panel:', len(e))
for i in e[:5]:
    print('   ', i['tarea_id'], '->', i['estado_actual'])
"
```

Esperado: más de 0. Esa vivienda existe en la obra, estaba rellenada a boli en
la hoja del 27/07/2026, y hasta ahora era invisible para el panel.

- [ ] **Step 4: Comprobar el Centro de Mando**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && python -c "
import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(open('SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/resumen_obras.json', encoding='utf-8'))
for o in d['obras']:
    if o.get('con_panel'):
        print('%-32s %s' % (o['nombre'][:32], o.get('pct_ponderado')))
"
```

Anotar los cuatro porcentajes. Gernika, Bolueta y Obispo Orueta deben ser
`76.3`, `36.1` y `80.0`. Mungia es el que legítimamente cambia.

- [ ] **Step 5: Escribir el antes/después en el informe**

Tabla con las cuatro obras, columnas `x / m / slash / vacio / total / pct`,
antes y después, y una línea explicando cada diferencia de Mungia. Sin esa
tabla la tarea no está terminada: **aplicar en silencio una corrección que
mueve cifras es el mismo problema desde el otro lado**.

- [ ] **Step 6: Commit**

```bash
cd "D:/Nueva carpeta/OneDrive/COPIA SEGURIDAD SAGARDE" && git add -A && git commit -m "Verificacion end-to-end de la inversion del flujo"
```

---

## Comprobación final de la fase

- [ ] Las 56 pruebas pasan.
- [ ] Mungia: `x` y `m` han subido respecto a 1798/84, y cada diferencia está justificada celda a celda.
- [ ] Gernika, Bolueta y Obispo Orueta: desglose **idéntico** a la línea base.
- [ ] Las 3 correcciones del PORTAL coinciden entre ficha y prioridades.
- [ ] La vivienda E de ZR2.1 planta 2 aparece en el panel.
- [ ] `git status` limpio.

## Fuera del alcance de esta fase

Cada una tendrá su plan cuando esta cierre:

- **Fase B — Entrada manual puntual:** corregir una celda sin montar una revisión.
- **Fase C — Árbol de materiales:** entregado / instalado / pendiente / necesario como bases anidadas dentro del apartado.
- **Fase D — Escritura desde el generador:** que marcar en la app escriba en la ficha sin pasar por un PDF impreso.
- **Fase E — Resto de obras:** Gernika, Bolueta, Gorliz y las 16 dormidas.
- **Fase F — Limpiar duplicados:** un catálogo, un registro de obras, un formato de clave.
