# Fase 3a — Cálculo de garaje en `priorizador_trabajos.py` y `generar_todos.py` (fichero de trabajo)

Diseño de Claude para que Codex lo implemente y pruebe. Divide la Fase 3
original del plan (`2026-09-24-ampliacion-garajes-plan.md`) en dos mitades
más seguras de verificar por separado:

- **Fase 3a (este documento):** que el sistema SEPA calcular prioridades y
  KPIs de garaje y los escriba en disco. Ningún HTML cambia todavía.
- **Fase 3b (aparte, después):** que `panel_obra.py` los muestre en el
  panel real. Es la parte que toca el fichero que genera el HTML de
  **todas** las obras existentes — se hace con más cuidado y con su propia
  verificación (diff byte a byte del HTML de obras sin garaje).

Motivo del split: leyendo `priorizador_trabajos.py` y `generar_todos.py`
completos aparecieron varios hallazgos reales que cambian el reparto — no
es tan simple como "llamar dos veces a lo mismo". Todos verificados contra
el código real, no supuestos.

## Hallazgo 1 — `motor_informes.py` no sabe nada de bloques/portales

Es puramente `task/floor/building/unit/status`, sin ninguna suposición de
estructura. La "lectura combinada de varios bloques" de vivienda no es una
agregación especial: es que `ficha_obra.snapshot_desde_ficha` YA produce
una sola lista plana cubriendo toda la ficha. Lo mismo aplica a
`ficha_garajes.snapshot_desde_ficha`, que ya recorre TODOS los garajes de
la obra (§3.3 del diseño ya sale gratis, no hace falta código nuevo para
"combinar" nada).

**Consecuencia:** para reusar `motor_informes.kpis_snapshot` y compañía
sobre el snapshot de garaje, solo hace falta traducir los nombres de campo
de `ficha_garajes.snapshot_desde_ficha` (`garaje`/`zona`/`garaje_id`/
`planta_id`/`zona_id`) a los que espera `motor_informes.py`
(`building`/`unit`). Una función de una línea por fila, sin tocar
`motor_informes.py`.

## Hallazgo 2 — nunca mezclar los `estados` de vivienda y garaje en la misma llamada

`_agrupar_prioridades` calcula `"prioridad": {"vivienda":"P1","zona_comun":"P2","edificio":"P3"}[item["ambito"]]`
y clasifica por `ambito`. Los 42 tajos de garaje usan `ambito: zona_comun`
(decisión ya tomada en la Fase 1) — si se calculan en la MISMA llamada que
los `zona_comun` de vivienda (escaleras, rellanos...), sus recuentos se
mezclarían sin ninguna forma de separarlos después. **Por eso `priorizar_ficha`
se llama DOS VECES, una por ficha, nunca una vez con los estados
combinados.** Cada llamada produce su propio `resumen`/`items`/`inventario`
autocontenidos — es justo lo que pide §3.3 del diseño ("dos lecturas").

## Hallazgo 3 — `estado_desde_ficha` y `verificar_rejilla` están cableados a bloques/portales

Los dos recorren literalmente `estructura["bloques"]` → `["portales"]` →
`["plantas"]` → `["ubicaciones"]`. Llamarlos con una ficha de garaje
(`estructura["garajes"]`, sin bloques) no da error: simplemente no
encuentra nada, y `priorizar_ficha` trataría un garaje con datos reales
como "sin base" (`sin_base()`). Hacen falta versiones paralelas, no se
pueden reusar tal cual. `_etiquetas_de_portal` y `_ultima_revision_ficha`
en cambio SÍ son reusables: la primera no hace falta para garaje (no hay
portales que desambiguar, el nombre del garaje ya es la etiqueta), la
segunda es genérica (`ficha.get("revisiones")`, funciona igual para
cualquier ficha).

## Hallazgo 4 — `verificar_rejilla` asume "cada ubicación lleva todos los tajos", que en garaje es falso a propósito

`esperadas = ubicaciones * len(tajos)` — en vivienda es cierto (toda
vivienda lleva todos los tajos de vivienda). En garaje es FALSO por diseño
(§5.9: un vial no lleva "lucido", un cuarto técnico sí — perfiles por tipo
de zona, todavía sin modelar en Python, ver "Qué NO hace v1" de la Fase 2).
Aplicar esta comprobación a garaje generaría un aviso de "rejilla
incompleta" permanente y falso. **Se omite para garaje en v1**, documentado,
no se intenta adaptar sin tener el mecanismo de perfiles.

## Hallazgo 5 — el más importante: `_clave_unidad` cuenta mal las unidades de garaje

```python
def _clave_unidad(item):
    ambito = item["ambito"]
    if ambito == "edificio":
        return (item["edificio"],)
    if ambito == "zona_comun":
        return (item["edificio"], item["planta"])   # <- colapsa por planta
    return (item["edificio"], item["planta"], item["unidad"])
```

Para vivienda, colapsar `zona_comun` a `(edificio, planta)` es correcto:
una escalera es UNA por planta, contar 40 celdas del mismo tajo como "40
unidades" infló Bolueta a 92 cuartos técnicos donde había uno (comentario
ya existente en el código, 851 unidades con 370 infladas).

Para garaje, **todos** los tajos son `zona_comun`, pero una planta de
garaje puede tener MUCHAS zonas distintas del mismo tipo (10 viales, 4
trasteros...) — cada una es una unidad real de trabajo, no la misma
repetida. Colapsar por `(garaje, planta)` haría que 10 viales pendientes de
tubeado contaran como **"1 unidad lista"**, escondiendo 9. Es el hallazgo
de más impacto de los cinco: silencioso, y exactamente la familia de fallo
que este proyecto existe para evitar (CLAUDE.md §2).

**Arreglo, mínimo y sin tocar el comportamiento de vivienda:** añadir un
parámetro opcional con el valor por defecto igual al actual, para que
ningún llamador existente cambie de comportamiento:

```python
def _clave_unidad(item, colapsar_zona_comun=True):
    ambito = item["ambito"]
    if ambito == "edificio":
        return (item["edificio"],)
    if ambito == "zona_comun" and colapsar_zona_comun:
        return (item["edificio"], item["planta"])
    return (item["edificio"], item["planta"], item["unidad"])
```

Y threadear `colapsar_zona_comun` (por defecto `True`) a través de
`_agrupar_prioridades(..., colapsar_zona_comun=True)` y
`prevision_desbloqueos(..., colapsar_zona_comun=True)`, que son las dos
únicas funciones que llaman a `_clave_unidad`. `priorizar_ficha` (vivienda)
sigue llamando a las dos exactamente igual que hoy — cero cambio de
comportamiento. La nueva `priorizar_ficha_garaje` las llama con
`colapsar_zona_comun=False`.

**Esta es la única excepción real a "no tocar la lógica de vivienda ya
existente" de todo el plan** — y es deliberada: un parámetro opcional con
el valor por defecto igual al actual no cambia ni una coma del
comportamiento de ningún llamador existente (vivienda, todas las obras).
Codex tiene que demostrarlo con un test explícito: llamar a
`_agrupar_prioridades`/`prevision_desbloqueos` SIN el nuevo parámetro sobre
datos de vivienda reales y comprobar que el resultado es idéntico al de
antes del cambio.

## Qué implementar

### En `priorizador_trabajos.py` (añadir, no modificar nada existente salvo el Hallazgo 5)

1. `_clave_unidad(item, colapsar_zona_comun=True)` — modificar como arriba.
2. `_agrupar_prioridades(detalle, limite=200, con_recorte=False, colapsar_zona_comun=True)`
   — añadir el parámetro, pasarlo a `_clave_unidad`.
3. `prevision_desbloqueos(detalle, colapsar_zona_comun=True)` — igual.
4. `_etiquetas_de_garaje(estructura)` — nueva, mucho más simple que
   `_etiquetas_de_portal`: `{garaje["id"]: garaje.get("nombre") or garaje["id"]
   for garaje in estructura.get("garajes") or []}`.
5. `estado_desde_ficha_garaje(ficha_garaje, catalogo)` — nueva, mismo
   patrón que `estado_desde_ficha` pero recorriendo
   `estructura["garajes"][]["plantas"][]["zonas"][]` (sin nivel de
   bloque/portal) y usando la clave de 4 partes
   `f"{garaje_id}__{planta_id}__{tajo_id}__{zona_id}"` (la misma que ya usa
   `ficha_garajes.py`). Devuelve `(estados, ultima_fecha)` con la misma
   forma exacta que `estado_desde_ficha` — así `_clasificar_detalle` no
   necesita saber que viene de garaje.
6. `priorizar_ficha_garaje(ficha_garaje, obra="", limite=200, hoy=None)` —
   nueva, calco de `priorizar_ficha` con estos cambios:
   - llama a `estado_desde_ficha_garaje` en vez de `estado_desde_ficha`;
   - **no llama a `verificar_rejilla`** (Hallazgo 4) — `avisos_rejilla = []`;
   - llama a `_agrupar_prioridades(..., colapsar_zona_comun=False)` y
     `prevision_desbloqueos(..., colapsar_zona_comun=False)`;
   - reusa tal cual `sembrar_reglas`, `_aplicar_excepciones_obra`,
     `_clasificar_detalle`, `_agrupar_inventario`, `_serializar_preguntas`
     (ninguno de estos hace suposiciones de estructura vivienda-específicas
     — confirmado leyendo cada uno);
   - el resto del cuerpo (resumen, avisos, dict de salida) igual que
     `priorizar_ficha`, mismos nombres de campo — así el consumidor (Fase
     3b) no tiene que distinguir "es de vivienda" o "es de garaje", solo
     que existe o no.

**`priorizar_ficha` (vivienda) no se toca ni una línea salvo lo del punto 1-3.**

### En `generar_todos.py` (añadir dentro de `main()`, después de la lectura de `ficha_actual`)

```python
ficha_garaje_actual = ficha_garajes.cargar(carpeta_abs)  # None si la obra no tiene garaje
if ficha_garaje_actual:
    prioridades_garaje = priorizador_trabajos.priorizar_ficha_garaje(
        ficha_garaje_actual, obra=obra['nombre'])
    salida_prioridades_garaje = os.path.join(
        salida_dir, 'prioridades_trabajos_garaje.json')
    priorizador_trabajos.escribir_json(
        prioridades_garaje, salida_prioridades_garaje)
else:
    prioridades_garaje = None
```

Fichero de salida nuevo (`prioridades_trabajos_garaje.json`, junto al ya
existente `prioridades_trabajos.json`), no se sobrescribe el de vivienda.
**Necesita entrada en `.gitignore`** (mismo patrón que la línea 48 ya
existente para `prioridades_trabajos.json`) — si no, se genera y nunca se
publica, sin dar ningún error (norma ya conocida del proyecto).

`panel_obra.generar_panel(...)` recibe `prioridades_garaje=prioridades_garaje`
como parámetro nuevo — **pero en Fase 3a no se usa todavía dentro de
`generar_panel`** (Fase 3b). Pasarlo ya desde ahora evita tener que volver
a tocar `generar_todos.py` cuando llegue la Fase 3b.

## Salvaguarda de esta fase

No hay "camino antiguo vs camino nuevo" que comparar aquí (a diferencia de
`actualizar_ficha_con_salvaguarda`, que es del cutover de revisiones, algo
distinto) — la salvaguarda real es que **ninguna obra existente tiene
`ficha_garajes.json` todavía**, así que para las 100% de las obras reales de
hoy, `ficha_garaje_actual` es `None` y todo el código nuevo no se ejecuta.
La comprobación exigida a Codex: generar TODAS las obras reales antes y
después del cambio y comprobar que `prioridades_trabajos.json` de cada una
es **byte a byte idéntico** (no solo "el test pasa") — es la prueba de que
tocar `_clave_unidad`/`_agrupar_prioridades`/`prevision_desbloqueos` no
movió ni una coma de vivienda.

## Tests que debe escribir Codex

1. `_clave_unidad` con `colapsar_zona_comun=True` (por defecto) da
   exactamente el mismo resultado que antes del cambio, para varios
   `ambito` — congelar con datos conocidos (p.ej. el caso Bolueta ya
   documentado en el docstring).
2. `_clave_unidad` con `colapsar_zona_comun=False`: dos items `zona_comun`
   con distinta `unidad` en la misma `(edificio, planta)` cuentan como 2
   unidades, no 1.
3. `estado_desde_ficha_garaje` sobre una ficha mínima (1 garaje, 1 planta,
   2 zonas, 2 tajos) produce el `estados` esperado, con la clave de 4
   partes correcta, y excluye correctamente celdas sin dato.
4. `priorizar_ficha_garaje` sobre una ficha de garaje sin ningún estado
   devuelve `sin_base()` (mismo comportamiento que vivienda sin ficha).
5. `priorizar_ficha_garaje` sobre una ficha con datos reales: un tajo
   `VIABLE` con su dependencia cumplida, uno `BLOQUEADO` con su dependencia
   pendiente — igual que ya prueba el test de `priorizar_ficha` de
   vivienda, pero con estructura de garaje.
6. `priorizar_ficha_garaje` con 3 zonas tipo vial pendientes del mismo tajo:
   `resumen['unidades_listas']` cuenta 3, no 1 (el caso exacto del
   Hallazgo 5).
7. **Prueba de no regresión, la más importante:** ejecutar
   `generar_todos.main(hacer_pdf=False)` (o el equivalente que ya use la
   suite) antes y después de este cambio sobre datos de obra reales, y
   comparar `prioridades_trabajos.json` de cada obra real byte a byte —
   tiene que ser idéntico. Si la suite ya tiene un test parecido para el
   cutover de fichas, seguir el mismo patrón.
8. `priorizar_ficha` (vivienda) sigue devolviendo exactamente lo mismo que
   antes del cambio para al menos una obra real de prueba — no solo "pasa",
   comparar el dict completo.

## Qué NO hace la Fase 3a (documentar en el propio código)

- No muestra nada en `panel_obra.py` — eso es la Fase 3b.
- No aplica la salvaguarda de doble cálculo estilo
  `actualizar_ficha_con_salvaguarda` (no aplica aquí: no hay dos caminos
  calculando el mismo dato, hay un camino nuevo que antes no existía).
- No implementa `verificar_rejilla` para garaje (Hallazgo 4) — pendiente
  de un mecanismo de perfiles por tipo de zona.
- No decide todavía si `prioridades_trabajos_garaje.json` se publica en el
  portal (`.gitignore`) más allá de dejarlo generable — confirmar con
  Bixente si hace falta publicarlo ya en esta fase o esperar a la Fase 3b,
  cuando el panel realmente lo use.
