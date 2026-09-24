# Fase 3b — Mostrar garaje en `panel_obra.py` (fichero de trabajo)

Diseño de Claude para que Codex lo implemente y pruebe. Sigue a la Fase 3a
(cerrada, commit `daf4c2a`), que ya calcula y pasa `prioridades_garaje` a
`generar_panel` (parámetro ya aceptado, sin usar todavía).

## Cómo está montada la página (leído de `panel_obra.py`, 2183 líneas)

Es una página de una sola carga con **pestañas por JS**, no un SPA de
verdad: una barra `<div class="nav"><button data-view="v-panel">...` con
un botón por pestaña, y una `<section id="v-panel" class="view">...`
paralela por cada una (`v-panel`, `v-trabajos`, `v-materiales`,
`v-personal`, `v-prioridades`, `v-riesgos`, `v-normativa`, `v-docs`,
`v-cierre`, `v-actualizar`). Un listener JS genérico
(`document.querySelectorAll('.nav button')...`) muestra/oculta secciones
por `data-view`/`id` — **no hay que tocar ese JS para añadir una pestaña
más**, el propio listener ya es genérico.

Aparte, hay un mecanismo distinto ("informe de obra a la carta") que
empaqueta el HTML de cada sección en un JSON (`SECCIONES_INFORME`) para un
selector de impresión. **No es la navegación principal** — es un extra.
No hace falta integrar garaje ahí en v1 (documentar como pendiente, no
como olvido).

## Hallazgo 6 — `bloque_prioridades_partes` NO se puede llamar dos veces en la misma página

Usa constantes de módulo fijas para los `id` de sección
(`_ID_SEC_DUDAS`, `_ID_SEC_EJECUCION`, `_ID_SEC_TAREAS`,
`_ID_SEC_PREGUNTAS_CATALOGO`, `_ID_SEC_PREVISION`) y elementos con `id`
únicos pensados para una sola instancia por página (`#filtro-sit`,
`#prio-count`, `#timeline-prio`...). Llamarla una segunda vez con los
datos de garaje produciría `id` de HTML duplicados: HTML inválido, y
`document.getElementById` solo encontraría la primera instancia — los
acordeones/filtros de la sección de garaje simplemente no funcionarían
(o, peor, interferirían con los de vivienda).

**Decisión: la sección de garaje NO reutiliza `bloque_prioridades_partes`.**
Es una sección nueva, deliberadamente más simple, construida con
funciones de bajo nivel que sí son genéricas (`_envolver_plegable` acepta
un `id_ancla` como parámetro, así que se le puede dar un prefijo
`garaje-`; `_tabla_prevision`, `_ubicaciones_html`). Coherente con
"empezar básico" — vivienda tiene filtros y acordeones interactivos
elaborados porque lleva meses de iteración; garaje empieza con una tabla
simple y crece si hace falta.

## Qué se añade (todo condicionado a `prioridades_garaje is not None`)

1. **Un botón de pestaña nuevo**, justo antes de "↻ Actualizar":
   ```html
   <button data-view="v-garaje">🅿️ Garaje</button>
   ```
   Renderizado condicional: si `prioridades_garaje` es `None` (todas las
   obras reales de hoy), este botón **no se genera en absoluto** — no un
   botón deshabilitado, ausente del todo, para que el HTML de esas obras
   no cambie ni un byte.

2. **Una sección nueva**, `<section id="v-garaje" class="view">`, con:
   - Una fila de tarjetas KPI simples construida directamente desde
     `prioridades_garaje['resumen']` (ya calculado por la Fase 3a, sin
     tocar `generar_todos.py` otra vez): "Tajos listos", "Bloqueados",
     "Dudas pendientes", "Terminados". **Sin "% de avance" todavía** — eso
     necesitaría un snapshot de garaje traducido a building/unit (Hallazgo
     1 de la Fase 3a) y no está calculado ni pasado hoy; añadirlo es
     trabajo aparte si Bixente lo pide, no se inventa aquí.
   - Una tabla simple de `prioridades_garaje['items']` (tarea, situación,
     nº de unidades, ubicaciones) — incluye `n_unidades` correctamente
     porque la Fase 3a ya corrigió el Hallazgo 5. Reusar el patrón de
     `_ubicaciones_html(item.get('ubicaciones', []))` para la columna de
     ubicaciones (esa función sí es genérica, no depende de vivienda).
   - Si `prioridades_garaje.get('sin_base')`: mismo aviso simple que ya usa
     `bloque_prioridades_partes` para ese caso (copiar el patrón, no la
     función entera).

3. **Nada más se toca.** Ni el JS existente (el listener de `.nav button`
   ya es genérico), ni ninguna otra sección, ni `SECCIONES_INFORME`.

## Verificación obligatoria — más estricta que "los tests pasan"

Generar el `panel.html` de **las 6 obras reales registradas** (Gernika,
Mungia, Bolueta, Gorliz, OBRA PRUEBA, Olabeaga — ninguna tiene
`ficha_garajes.json` hoy) antes y después del cambio, y comparar
**byte a byte** (no "se parece", el fichero completo idéntico). Ninguna
de las seis debería cambiar ni un carácter, porque para todas
`prioridades_garaje` es `None`. Es la misma disciplina que ya usó la Fase
3a con `test_todas_las_obras_registradas_conservan_sus_bytes`, aplicada
aquí al HTML en vez de al JSON.

Además, un test con una ficha de garaje de prueba (puede ser sintética,
igual que `_ficha_garaje()` en `tests/test_priorizador_garaje.py`) que
compruebe que CUANDO `prioridades_garaje` no es `None`:
- el botón `v-garaje` aparece en el HTML;
- la sección `id="v-garaje"` aparece con el nº de items esperado;
- ninguna otra sección existente (`v-panel`, `v-trabajos`...) cambia de
  contenido respecto a generar el mismo panel sin garaje.

## Qué NO hace la Fase 3b (documentar en el propio código)

- No integra garaje en el selector "informe de obra a la carta"
  (`SECCIONES_INFORME`) — queda para cuando haga falta de verdad.
- No calcula ni muestra "% de avance" de garaje (necesitaría el snapshot
  traducido de motor_informes, Hallazgo 1 de la Fase 3a, no calculado hoy).
- No reutiliza `bloque_prioridades_partes` (Hallazgo 6) — la sección de
  garaje es deliberadamente más simple que la de vivienda.
- No cambia ni una línea de las demás secciones ni del JS ya existente.
