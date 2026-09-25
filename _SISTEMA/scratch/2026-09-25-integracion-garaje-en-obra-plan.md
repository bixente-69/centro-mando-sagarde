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

## Orden de trabajo propuesto

1. `snapshot_garaje` + `kpis_obra_total` en `generar_todos.py`,
   enchufado a `resumen_obras.json` y a la cabecera del Panel — es lo
   que más se nota (el % que Bixente vio primero que faltaba) y reusa
   una función ya verificada, riesgo bajo.
2. Verificar contra Gernika real (86-87% esperado) antes de seguir.
3. Riesgos — reusar `prioridades_garaje` ya calculado, riesgo bajo.
4. Informes (PDF + a la carta) — sección nueva, no toca cálculo.
5. Trabajos / Prioridades — la pieza ambigua, hablarla con Bixente
   antes de tocarla.

Cada pieza se verifica contra Gernika real antes de pasar a la
siguiente (igual que las 7 fases anteriores) — "la forma de perfeccionar
y ajustar la app es con el uso real" (Bixente, textual).
