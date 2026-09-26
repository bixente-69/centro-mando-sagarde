# Integración del garaje en el total de la obra — plan de trabajo

Decidido en conversación con Bixente el 25/09/2026, contra el caso real
de Gernika 32V (ya con datos reales de garaje: 81 X, 65 N, 9 pendientes
de las 161 celdas de las 11 zonas).

## La decisión (textual)

> "si hay garaje, aunque hagamos una revisión independiente, forma parte
> del total de la obra"
>
> "a la hora de presentar y tratar puede ser un aparte, una hoja más,
> pero siempre dentro y todo de la misma obra y jugando todo a la vez"

Traducido a reglas concretas:

1. El **camino de revisión** (hoja separada, `alta_garaje_desde_hoja.py`,
   `adaptar_revision_garaje.py`, `ficha_garajes.json`) **no cambia**. Ya
   funciona y está verificado (Fases 1-7).
2. Lo que falta es la **integración en la vista/cálculo agregado**: el
   garaje tiene que aparecer, como sección propia (como un bloque más),
   en **todos** los sitios donde hoy solo aparece vivienda: el % total
   de la obra (Portal Sagarde), Trabajos, Prioridades, Riesgos, Informe
   Ejecutivo PDF e Informe de obra a la carta.
3. El garaje mantiene su propia gráfica/sección — no se funden las
   filas de vivienda y garaje en una sola tabla. Pero para el número
   único de "% de la obra" (cabecera del panel, Portal Sagarde), SÍ se
   combinan.

## Cómo se combina el %: media ponderada por celdas

Confirmado con Bixente con datos reales de Gernika: **no** promedio
simple de los dos porcentajes (eso trataría el garaje como si fuera la
mitad de la obra). Se combinan **todas** las celdas de vivienda y
garaje en una sola cuenta.

**Hallazgo clave, ya no hay que escribir el cálculo de cero**:
`motor_informes.kpis_snapshot(snapshot)` (el motor ya usado por
vivienda) es agnóstico de esquema — solo necesita una lista plana de
dicts `{task, floor, building, unit, status}`. Basta con:

1. Construir un `snapshot_garaje` con esa misma forma desde
   `ficha_garajes.json` (garaje→building, planta→floor, zona→unit,
   tajo→task, estado→status vía `ESTADO_BASE_A_MOTOR` de
   `priorizador_trabajos.py`, que ya existe y ya excluye N por diseño).
2. `kpis_obra_total = motor.kpis_snapshot(snapshot_vivienda + snapshot_garaje)`.

Con los datos reales de hoy: vivienda 90.2%, garaje 52.3% (81/155),
combinado ponderado ≈ **86-87%** (recalcular con el snapshot real, el
81/155 no es exactamente lo mismo que el pct_estricto de motor_informes
si building/floor/unit no casan 1:1 — verificar).

## Dónde vive cada pieza a tocar

- **`generar_todos.py`**: ya carga `ficha_garajes` si existe (Fase 3a).
  Aquí se construye `snapshot_garaje` y se calcula `kpis_obra_total`,
  una sola vez por obra, para no tener el cálculo duplicado en dos
  sitios con riesgo de que diverjan.
- **`panel_obra.generar_panel()`** (línea ~1554-1610): hoy calcula
  `kpis = motor.kpis_snapshot(snapshot)` solo con el snapshot de
  vivienda y pinta las 4 tarjetas de cabecera (Avance estricto, Avance
  estimado, Revisiones, Tajos bloqueados) en la pestaña Panel. Recibe ya
  `prioridades_garaje` como parámetro — falta que reciba también
  `kpis_obra_total` (o el propio `snapshot_garaje`) y lo use en la
  cabecera.
- **`resumen_obras.json`** (escrito por `generar_todos.py`, línea
  ~1320, consumido por el Portal Sagarde / `index.html` — la pestaña de
  "todas las obras"): hoy escribe `pct_ponderado` solo de vivienda. Aquí
  es donde hay que usar `kpis_obra_total` en vez del de solo-vivienda.
- **Trabajos / Prioridades** (pestañas de panel_obra.py): hoy 100%
  vivienda. El garaje YA tiene su tabla propia en la pestaña "🅿️
  Garaje" — decidir si esa misma tabla se **repite/enlaza** también
  dentro de Trabajos y Prioridades (sección aparte dentro de la misma
  vista) o si basta con que la pestaña Garaje ya exista y lo que falta
  es solo que el AVANCE cuente en el total (más barato, más alineado
  con "puede ser un aparte, una hoja más"). **Confirmar con Bixente
  antes de tocar código aquí** — es la pieza con más ambigüedad real
  todavía.
- **Riesgos**: `priorizar_ficha_garaje` YA calcula bloqueos por
  dependencia (`categoria: BLOQUEADO`, `dependencias_bloqueantes`) con
  la misma lógica que vivienda. Probablemente baste con que la pestaña
  Riesgos también lea `prioridades_garaje` y añada su propia sección,
  reusando el motor ya existente — no hace falta lógica de riesgo
  nueva.
- **Informe Ejecutivo PDF** (`generar_informe_ejecutivo.py`) e
  **Informe de obra a la carta** (`SECCIONES_INFORME` en
  `panel_obra.py`, ver memoria `project_sagarde_informe_obra_a_la_carta`):
  ninguno de los dos toca garaje hoy. Añadir una sección de garaje,
  tratada como un bloque más (palabras de Bixente), en ambos.

## Estado (25/09/2026)

- ✅ **% total combinado** (panel + Portal Sagarde), commit `1077c39`.
  Verificado contra Gernika real: 85.9%/87.1%.
- ✅ **Riesgos**, commit `8e95763`. Sección propia de garaje reutilizando
  `bloque_riesgos` tal cual. Hecho por **agy** (edición exacta) tras dos
  intentos fallidos de Codex (sin cuota) — Claude corrigió 2 fallos
  reales de su propio encargo detectados por la suite, no de agy.
- ✅ **Informe Ejecutivo PDF**, commit `a12b69b`. Resumen general
  combinado + página GARAJE completa (mismo detalle que un bloque de
  vivienda). Codex vía `-p free` se quedó inestable ("alta demanda") y
  solo dejó una firma sin usar — lo hizo Claude directamente. Verificado
  generando el PDF real de Gernika y leyéndolo: encontró y corrigió un
  bug real (`snapshot_garaje` llevaba el id del tajo en `'task'` en vez
  del nombre, la página de garaje salía vacía) que no habría salido a
  la luz sin generar el PDF de verdad, solo con la suite.
- ✅ **Prioridades**, commit `924ae25`, **corregido en commit `6fd46a7`**.
  "Calca el formato de vivienda" (Bixente, textual): misma
  `bloque_prioridades_partes()`, llamada una segunda vez con
  `sufijo='-garaje'`. Hecho por Claude directamente (no delegado):
  requería sostener ~15 ids interdependientes a la vez y verificar en
  navegador real. De paso corrigió un enlace fijo a JSON equivocado,
  encontrado solo al probar en un servidor local real (el snapshot
  estático del navegador integrado no ejecuta bien la interactividad de
  esta plantilla — hace falta origen http de verdad).

  **Malentendido real en la primera versión (25/09/2026), señalado por
  Bixente al ver el panel de Gernika**: el bento de garaje se metió
  pegado DENTRO de la pestaña "Prioridades" de vivienda, dejando la
  pestaña "🅿️ Garaje" con su formato viejo (KPI-row + tabla). Bixente,
  textual: "pestaña prioridades se suponia prioridades de vivienda,
  simbolo en la pestaña de vivienda. pestaña de garaje se suponia igual
  que prioridades de vivienda pero con los datos de garaje. no se
  parecen en nada". Corregido: son dos pestañas separadas, cada una con
  su propio centro de mando; "🎯 Prioridades 🏠" queda solo de vivienda,
  "🅿️ Garaje" recibe el mismo `bloque_prioridades_partes(sufijo='-garaje')`
  que antes estaba mal conectado. El namespacing de ids (la parte
  difícil) no cambió, solo a qué pestaña se conecta su resultado.

  **De la misma tanda de avisos**: "Panel: no hay nada de garaje" — el
  gráfico "Avance por planta y edificio" ahora funde vivienda y garaje
  con icono de origen (🏠/🅿️), vía `_combinar_matriz_planta_edificio`
  (misma lógica que Trabajos). "Evolución del avance" (serie temporal)
  se deja tal cual: `generar_panel()` no recibe un historial propio de
  garaje, solo un snapshot puntual — no hay con qué construir esa serie
  todavía. Verificado con 665 tests y en navegador real.
- ✅ **Trabajos**, commit `ce4dda0`. "Trabajos es una cosa, debería de
  ir todo junto" (Bixente, textual) — a diferencia de Riesgos/
  Prioridades, aquí NO hay sección aparte: las filas de vivienda y
  garaje se funden en las mismas tablas ("Desviaciones de avance",
  "Detalle por planta/edificio") y en la misma gráfica ("Avance por
  tarea"), cada una con su icono de origen (🏠/🅿️). Hecho por **agy**:
  el diseño completo (el diff exacto de 5 puntos en panel_obra.py + los
  valores esperados de los tests, calculados aparte contra
  `motor_informes` real antes de escribir el encargo) lo hizo Claude —
  agy solo aplicó el texto tal cual se le dio, verificado después
  idéntico byte a byte al pedido. Confirmado en navegador real contra
  Gernika: la fila de Garaje 1 (52.3%) aparece al final de la tabla de
  detalle, y la gráfica mezcla tareas de ambos con su icono.
- ✅ **Informe de obra a la carta**, commit `8ea3afc` (26/09/2026).
  Confirmado por Bixente, textual: "por supuesto que debe inclir
  garaje, es una pieza mas de las obras y muchas veces una obra en si
  solo". Nuevo grupo "🅿️ Garaje" en el selector con los mismos 5
  subapartados que vivienda; JS generalizado (ya no fijado a
  `'prioridades'`) + `PREFIJO_SECCION` para distinguir "Qué hacer
  ahora" de vivienda y de garaje si se marcan los dos a la vez.
  **Hallazgo real de la verificación**: el CSS `display:block!important`
  de la vista previa enumeraba una lista fija de 11 ids de vivienda
  (misma familia de fallo que `e7d9f74`, coleada aquí) — corregido a
  selector por clase. Verificado generando la vista previa real
  (interceptando `window.open`, servida por un servidor local) contra
  Gernika: ambas secciones aparecen distintas y con su contenido
  completo visible, no solo el título.

## Orden de trabajo propuesto

1. `snapshot_garaje` + `kpis_obra_total` en `generar_todos.py`,
   enchufado a `resumen_obras.json` y a la cabecera del Panel — es lo
   que más se nota (el % que Bixente vio primero que faltaba) y reusa
   una función ya verificada, riesgo bajo.
2. Verificar contra Gernika real (86-87% esperado) antes de seguir.
3. Riesgos — reusar `prioridades_garaje` ya calculado, riesgo bajo.
4. Informes (PDF + a la carta) — sección nueva, no toca cálculo.
5. Prioridades — hecho (ver Estado arriba).
6. Trabajos — hecho (ver Estado arriba).
7. Informe de obra a la carta (piezas de Prioridades) — hecho (ver
   Estado arriba).

**Con esto, las 7 piezas de esta integración quedan cerradas.**

Cada pieza se verifica contra Gernika real antes de pasar a la
siguiente (igual que las 7 fases anteriores) — "la forma de perfeccionar
y ajustar la app es con el uso real" (Bixente, textual).
