# Fase 5 — Adaptador de lectura de garaje (fichero de trabajo)

Diseño de Claude. La Fase 4 ya está cerrada y verificada (commits
`645d9b8` y `1216d49`, este último añade la estructura embebida en la
hoja que la sección 5.1 de más abajo usa).

## Hallazgo, releyendo `adaptar_revision_html.py` (vivienda) completo

Su mayor complejidad (`_mapas_orden_natural` vs `_mapas_orden_estructura`,
comparar dos numeraciones y aceptar solo si coinciden) existe por una
razón **histórica que garaje no hereda**: los `portal.id`/`planta.id` que
vivienda escribe en `data-k` a veces son ids sintéticos `src_obra_pN`
generados por `generar_todos.py` (dos productores distintos con distinto
criterio de orden), no siempre los ids reales de `ficha_obra.json`. Para
garaje, el asistente (Fase 4) escribe siempre `garaje.id`/`planta.id`/
`zona.id` — los mismos ids `uid()` con los que se construyó la estructura,
sin ninguna capa de numeración sintética intermedia. **No hace falta
resolver ninguna ambigüedad de numeración: el id del HTML y el id que
debe existir en `ficha_garajes.json` son literalmente el mismo.**

Consecuencia real: el adaptador de garaje es bastante más simple que el
de vivienda — hereda `extraer_pares()` de `lector_hoja_tajos_html.py` tal
cual (genérico, ya confirmado: un regex sobre `data-k`/`data-st`, sin
ninguna suposición de estructura), pero no necesita nada parecido a
`derivar_mapas_ubicacion`.

## El problema real a resolver: alta vs. revisión

`ficha_garajes.actualizar_desde_snapshot` (Fase 2) **exige que garaje/
planta/zona ya existan** en la estructura — a propósito, es la decisión
de simplicidad de esa fase (nada de auto-alta de zonas nuevas). Esto deja
una pregunta sin cerrar: ¿cómo entra la estructura la primera vez?

**Respuesta:** no se deriva de una hoja rellena (a diferencia de
`alta_obra_desde_hoja.py`, que sí lee geometría de un PDF en blanco —
mecanismo ya descartado para garaje en el diseño original, por estructura
no uniforme). El asistente de la Fase 4, en el paso "Generar", YA
construye la estructura completa en `S.garajes` antes de generar la hoja
— es la misma fuente de la que sale la hoja. **La primera alta consiste
en escribir esa misma estructura directamente en `ficha_garajes.json`,
sin pasar por ninguna hoja.**

Dos piezas, no una:

### 5.1 — Alta: de la estructura embebida en la hoja a `ficha_garajes.json`

**Revisado tras cerrar la Fase 4 (25/09/2026):** en vez de un botón nuevo
de "Descargar estructura (JSON)" (lo que se planteó primero, y habría
sido una vía de entrada nueva que Bixente tendría que aprender),
`generateGarajeHTML()` ya embebe la estructura completa en la propia hoja:

```html
<script type="application/json" id="garaje-estructura">
  {"obra": "...", "garajes": [...], "tajos_seleccionados": [...]}
</script>
```

Con la MISMA forma que espera `estructura.garajes` de
`ficha_garajes.json`, sin transformar nada. Esto significa que **la
primera alta usa exactamente el mismo fichero HTML** que Bixente ya sabe
generar y guardar con el botón "⬇ Descargar HTML" que ya existe — cero UI
nueva, cero fichero nuevo que aprender a manejar.

- `alta_garaje_desde_hoja.py` (nuevo, pequeño): recibe la ruta de esa hoja
  (en blanco o ya con marcas, da igual — la estructura embebida es la
  misma) + `id_obra`. Extrae el bloque `<script id="garaje-estructura">`
  con un regex simple (no hace falta un parser HTML completo — el propio
  generador solo emite un `<script>` con ese id) y `json.loads`. Valida
  que la obra no tenga ya `ficha_garajes.json` (si lo tiene, para y avisa
  — no se sobrescribe una estructura confirmada sin que alguien lo pida
  explícitamente, mismo espíritu que `_esta_excluida`/estructura
  confirmada de vivienda). Construye la ficha inicial con
  `ficha_garajes.asegurar_apartados` + `estructura.garajes = datos['garajes']`,
  y la guarda con `ficha_garajes.guardar`.
- Tajos: `ficha['tajos']['detalle']` se rellena desde `CATALOGO_TAJOS.json`
  filtrando por los ids `garaje_*` que el JSON embebido marque como
  seleccionados (`tajos_seleccionados`), igual patrón que ya usa
  `sembrar_reglas` para completar metadatos desde el catálogo.
- Verificado el escapado antes de delegar esto (`<` en vez de solo
  `</script>`, para que ningún nombre con "<" pueda romper el HTML):
  viaje de ida y vuelta real en Python (construir, extraer con regex,
  `json.loads`) — coincide exactamente con el original.

### 5.2 — Revisión: `adaptar_revision_garaje.py`, calco simplificado de `adaptar_revision_html.py`

Con `ficha_garajes.json` ya existente (por la 5.1), leer una hoja de
garaje rellena:

1. `lector_hoja_tajos_html.extraer_pares(ruta_html)` — sin cambios, reusar
   tal cual.
2. Para cada `(data_k, data_st)`: `partes = data_k.split('__')` → debe dar
   4 partes (`garaje_id, planta_id, tajo_id, zona_id`) — mismo formato de
   clave que ya define `ficha_garajes.py`.
3. **Sin mapas de traducción de ids** (a diferencia de vivienda): validar
   directamente contra la estructura de `ficha_garajes.json` — si el trío
   `(garaje_id, planta_id, zona_id)` no existe, es un aviso, no un error
   fatal (mismo criterio que `ficha_garajes.actualizar` ya implementa vía
   `zonas_desconocidas` — este adaptador puede incluso delegar
   directamente esa comprobación en lugar de duplicarla).
4. `tarea_id`: validar contra
   `{t for t in _ids_tajos(catalogo, obra) if t.startswith('garaje_')}`
   (mismo `validar_revision._ids_tajos`, filtrado — ver nota de abajo) —
   no hace falta `TAREA_ID_GENERADOR_A_CATALOGO`: los ids ya son
   canónicos desde la Fase 4.
5. Estados: reusar la constante `validar_revision.ALFABETO_HOJA_DIGITAL`
   para validar qué símbolos son aceptables — **ya incluye `N`**
   (comprobado leyendo el código: se construye filtrando
   `('X','M','/','','N')` contra `MAPA_ESTADO`, y `MAPA_ESTADO` ya tiene
   `'n':'N'` desde la Fase 0). No hace falta tocar nada ahí. Solo se
   reusa la constante, no el resto de la maquinaria de
   `validar_revision.py` (ver el punto siguiente).
6. Construir directamente el snapshot que espera
   `ficha_garajes.actualizar_desde_snapshot` (§ de la Fase 2), no un
   `REVISION_NORMALIZADA` de `validar_revision.py` — ese contrato existe
   para el camino de vivienda con su salvaguarda de doble cálculo
   (`aplicar_revision.py`), que garaje no tiene ni necesita todavía (no
   hay "camino antiguo" con el que comparar). Mantiene el adaptador de
   garaje más simple y más corto.

## Nota sobre `_ids_tajos` (validar_revision.py)

Devuelve TODOS los ids del catálogo mezclados (vivienda + garaje, más los
propios de obra). Para garaje, filtrar por prefijo `garaje_` al construir
el conjunto válido — evita que una revisión de garaje resuelva por
accidente contra un id de vivienda homónimo (no debería pasar nunca dado
el prefijo, pero filtrar explícito es más seguro que confiar en que nunca
colisionen).

## Qué NO hace la Fase 5

- No implementa ninguna salvaguarda de doble cálculo (no hay camino
  antiguo con el que comparar, a diferencia de vivienda).
- No lee hojas en papel/PDF escaneado de garaje — solo el HTML digital
  que produce el propio asistente (mismo alcance que decidió §6 del
  diseño original: "html digital" es la vía, nunca tinta para garaje v1).
- No decide todavía cómo se invoca desde `generar_todos.py`/la skill
  `sagarde-revision` — eso es integración de la Fase 6 (validación en
  `OBRA PRUEBA`), no de esta.
