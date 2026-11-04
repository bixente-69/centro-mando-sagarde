# Estudio de mejoras de Sagarde — borrador por fases

**Fecha:** 04/11/2026 · **Estado:** EN CURSO (se completa fase a fase; cada fase se guarda con commit). Solo lectura sobre producción: no se ha tocado código ni datos de obra, no se ha ejecutado ningún `.bat`.

## 1. Plan de trabajo

| Fase | Entregable | Tope | Estado |
|---|---|---|---|
| 0 Orientación | lecturas obligatorias de `CLAUDE.md` §5 | ~10 lecturas | hecha |
| 1 Inventario con cifras | scripts de solo lectura sobre fichas, jornadas, series, postventa | 6 scripts | hecha |
| 2 Dónde se pierde trabajo | fricciones con evidencia | grep + informes A–H | hecha |
| 3 Investigación web | ≥15 fuentes en ~25–30 búsquedas | 30 búsquedas | pendiente |
| 4 Ideas | ≥10 puntuadas con criterios | 1 tabla | pendiente |
| 5 Propuestas | ≥2 completas, 1 recomendada | — | pendiente |
| 6 Entrega | este documento + resumen + 1 pregunta | — | pendiente |

---

## 3. Fase 1 — Inventario de datos con cifras

Mediciones hechas el 04/11/2026 sobre el checkout (rama `claude/blissful-cannon-o3by6q`). **Hecho** = medido por script; **inferido** = deducido; **no verificable** = no está en git.

### 3.1 Obras abiertas con seguimiento (5 con ficha; Gorliz sin base)

| Obra | Revisiones en ficha | Fechas distintas | Serie del KPI (puntos) | Primer punto → último | Control horario (días con jornada) | Horas registradas |
|---|---|---|---|---|---|---|
| Gernika | 10 (+3 garaje) | 6 | 8 | 22/07/2026 → 05/10/2026 | no tiene | – |
| Mungia | 7 | 5 | 30 | 16/01/2026 → 15/10/2026 | 4 (solo garaje) | 72 h |
| Bolueta | 24 (+2 garaje) | ~12 | 22 | 10/04/2026 → 27/10/2026 | 12 (vivienda) | 568,5 h |
| Olabeaga | 12 (+5 garaje) | 8 | 8 | 04/10/2026 → 02/11/2026 | 17 | 393,5 h (345,5 vivienda + 48 garaje) |
| Barakaldo | 2 (+1 garaje) | 1 | 1 | 08/10/2026 | 5 (solo garaje) | 120 h |
| Gorliz | – | – | – | sin revisión ni base | – | – |

(Gernika: `ficha_obra.json` + `revisiones_aplicadas.jsonl` (154 líneas); Bolueta 24 revisiones en ficha, de las que varias son «historial existente» reconstruido.)

**Lecturas críticas de la tabla:**

1. **Series cortas.** Solo Mungia (30 puntos) y Bolueta (22) tienen serie con cuerpo; Olabeaga 8 puntos en un mes; Barakaldo **1**. Cualquier estadística «de obra» con n<10 es ilustrativa, no inferencial.
2. **La serie no es homogénea.** El campo `total` (denominador) cambia dentro de la misma obra: Gernika 1088 → 1216 → 1208; Olabeaga 1295 → 1265 → 1256 → **1461** (02/11); Bolueta 2880 → 2964. Mungia tiene un **salto de 88,0 % a 43,5 % el 25/07/2026** y de 43,5 a 74,9 el 27/07: ruptura de método en la serie, no avance real. Es la «fuga F3» ya señalada en el informe D (denominadores mezclados). Cualquier previsión basada en esta serie hereda ese ruido si no se corrige antes.
3. **`P` y `?`**: en las 5 fichas hay `?` = 0 y toda la incertidumbre está en `P` (Barakaldo: 4130 `P` de 4140; Olabeaga 1186 de 1519). Es coherente con la norma de Bixente (blanco → `P`) pero significa que **el sistema no distingue «no empezado» de «no mirado»**: dato a tener en cuenta en cualquier previsión.

### 3.2 Control horario (Personal en obra)

- **140 filas persona-día** en 4 obras (Barakaldo 15, Bolueta 66, Mungia 9, Olabeaga 50), **1.154 h** en total, entre el **12/10/2026 y el 06/11/2026**. Gernika: nada.
- Cada fila lleva `id`, `horas`, `extra` por persona y día, y el **ámbito** de la jornada (`vivienda` / `garaje`). **No lleva tajo.**
- Hay jornadas con fecha **futura** respecto al 04/11 (hasta 06/11; el lector las marca `fecha_futura`): dato de prueba o previsión, no medición.
- **Consecuencia:** «horas por tajo» y «horas por vivienda» **no se pueden calcular hoy**; solo «horas por obra y ámbito». Lo que existe son ~3 semanas de datos. Cruzarlo con avance daría rendimiento por obra, con 1–3 semanas de horas frente a 4–9 meses de avance (Mungia, 72 h frente a 9 meses de obra: cobertura <5 %, estimada).
- (No se copian nombres ni ids de trabajadores en este documento.)

### 3.3 Materiales

- Lo implementado es **solo «entregado»**. `entregas_materiales.py` (1.021 líneas) y la sección del panel dicen literalmente: *«Cantidades entregadas… no equivalen necesariamente a material instalado»*. No existe «necesario», ni «instalado», ni «a pedir», ni consumo por tajo. `grep` de `consumo|por_pedir|ratio|necesari…material` en el motor: **0 coincidencias con lógica** (solo textos de aviso).
- Las hojas `.xlsx` **no están en git** (el `.gitignore` es lista blanca), así que no puedo contarlas. Lo único medible es lo que el panel publicado imprime: Olabeaga, mes de noviembre: 2 entregas, 13 líneas; Barakaldo, noviembre: 5 entregas, 22 líneas; Olabeaga con 2 líneas sin suministrador/albarán.
- **Mungia: la última entrada de material es del 08/05/2026**, mientras la obra sigue con revisiones hasta el 15/10. O la entrega acabó en mayo, o la hoja está sin actualizar: **no se puede saber desde aquí**; el panel no avisa de ninguna de las dos.
- No hay **mediciones por tajo** en el repo (`grep medici[oó]n` solo toca adaptadores y planes del Buscador). Sin cantidades «necesarias» por tajo, una previsión de pedidos tendría que partir de **ratios inventados**, lo que `CLAUDE.md` §10 prohíbe. Hay que obtenerlas de Bixente (presupuesto o histórico de entregas) o derivarlas de entregas ya hechas de obras terminadas.

### 3.4 Archivo histórico («128 obras cerradas»)

- `SAGARDE (OLD)/OBRAS CERRADAS` en git: **6 ficheros** (3 `panel.html` + 2 `.py` de adaptador + índice). **No hay histórico de rejillas ni de horas** de las 128 obras en este repositorio. Puede existir en OneDrive (**no verificable**), pero el repo público no lo contiene.
- **Consecuencia directa:** «compararse con las obras cerradas» (semilla (a) del encargo) **no es posible hoy con lo versionado**. Solo hay 3 paneles y el cierre de Orueta (`cierre.json`: 99,7 %, 102 ubicaciones, 4080 celdas). Habría que traer los datos o construirlos.

### 3.5 Postventa — el conjunto de datos histórico más grande y mejor del repo

- `POST-VENTAS/_SISTEMA/_PREVIEWS_WORD/*.html`: 96 ficheros versionados; tras quitar copias `BACKUP` y `_vN`: **63 ficheros, 45 con tablas de incidencias, 2.786 filas** con columnas cliente · nº · mano · código de vivienda · incidencia (texto libre) · recibí · operario · solución (texto libre) · OK · fecha.
- Fecha de recepción legible en **2.502** filas; fecha de resolución legible en **2.340**; **1.976** con las dos. Años de recepción: 2018 (75), 2019 (150), 2020 (186), 2021 (95), **2022 (1.783)**, 2023 (24), 2024 (40), 2025 (114), 2026 (32), más 3 fechas con año erróneo (`219`, `3018`).
- **Tiempo de resolución medido: mediana 7 días, percentil 90 = 50 días** (1.976 pares).
- **Calidad:** la columna OK mezcla `OK` (1.473), `SI` (652), `S` (146), `0K` (56), vacío (206), `NO` (24)… y otras 100+ variantes: hace falta normalizar. 2022 pesa el 71 % de las filas: casi seguro una o pocas obras grandes, **no una tendencia** (inferido). Textos libres: clasificar por tipo exige reglas o lectura asistida; hoy no hay campo de tipo/causa.
- **No tocado:** nombres de clientes y teléfonos están en esos ficheros públicos (informe E, §5.1); no se reproducen aquí.

### 3.6 Previsión: ¿se puede predecir el fin de obra con los datos de hoy? (backtest propio)

Ajuste lineal de los 6 últimos puntos de `pct_ponderado`, predicción de la fecha en que se cruza un umbral y comparación con la fecha real, cortando la serie en el pasado (script de solo lectura, 6 cortes sobre 2 obras):

| Obra | Corte | Ritmo ajustado (pt/día) | Umbral | Fecha predicha | Fecha real | Error (días) |
|---|---|---|---|---|---|---|
| Mungia | 08/05 | 0,61 | 85 % | 19/05 | 29/06 | +41 |
| Mungia | 25/05 | 0,34 | 85 % | 08/06 | 29/06 | +21 |
| Bolueta | 26/05 | 0,28 | 70 % | 05/11 | 08/10 | −28 |
| Bolueta | 24/08 | 0,30 | 70 % | 25/10 | 08/10 | −17 |
| Bolueta | 28/09 | 0,42 | 70 % | 08/10 | 08/10 | 0 |

- **Lectura honesta:** errores de −28 a +41 días a umbrales de 70–85 %. Sirve para «¿llegamos al 85 % antes de X?» con margen de ±5 semanas; **no sirve para «fecha de fin al 100 %»**. Mungia lleva **~4 meses entre el 80 % (25/05) y el 90 % (15/10)** y no ha llegado al 100 %: la cola de obra depende de otros gremios, no del ritmo de Sagarde. Una extrapolación lineal de esa cola sería engañosa.
- n = 2 obras, 5 cortes útiles: **no hay validación estadística**. Es un indicio, no una prueba. Un intervalo «de confianza» honesto con estos datos sería tan ancho que una fecha única sería publicidad.

### 3.7 Resumen de lo que hoy NO se puede contestar

| Pregunta | Por qué no |
|---|---|
| «¿Cuántas horas cuesta un tajo / una vivienda?» | el control horario no lleva tajo; 3 semanas de datos |
| «¿Cómo va esta obra frente a las 128 cerradas?» | el histórico no está en el repo |
| «¿Qué material falta por pedir?» | no existe cantidad necesaria ni instalada |
| «¿Cuándo termina Mungia?» | la cola depende de terceros; sin datos de causa de bloqueo medibles |
| «¿Material de Mungia sin actualizar desde mayo?» | el panel no avisa de entregas viejas |
| «¿Qué tipo de incidencia se repite por tajo?» | existe texto libre, no hay tipo ni causa |

---

## 4. Fase 2 — Dónde se pierde trabajo de gestión (con evidencia)

Las horas de Bixente por paso **no están medidas en ningún sitio del repo**; donde doy una cifra es una **hipótesis marcada (H)** que él puede corregir con un dato.

| # | Fricción | Evidencia | Qué se pierde |
|---|---|---|---|
| F1 | **El eslabón manual «fichero en `REVISIONES` → alguien dice “actualiza la obra”» no avisa si se olvida.** El auditor solo avisa de `REVISIONES_DUPLICADAS`; no de hojas ni controles horarios pendientes | `G_decisiones_bixente.md` §4 (punto 3); informe F §3.2 | trabajo que existe en la tablet y no llega al portal sin que nadie lo vea |
| F2 | **Subida semanal sin estado visible.** Hoy el portal solo lleva un sello gris «datos del…»; no hay aviso por antigüedad ni de push fallido (decidido 8/14 días, **sin implementar**) | G §3–4; F resumen 4 | confianza en lo que se ve en tablet/móvil |
| F3 | **No existe ningún «qué ha cambiado desde la última vez».** El panel enseña estado actual, sparkline y `variacion_pct`; el único «prevision» del código (`priorizador_trabajos.prevision_desbloqueos`) significa «qué se desbloquea al terminar X», **no una fecha ni un ritmo** | `panel_obra.py:677-701`; `priorizador_trabajos.py:823`; `grep` de ritmo/tendencia/fecha de fin: 0 lógica | cada informe a la constructora se compone a mano |
| F4 | **«Informe de obra a la carta» es 100 % manual:** se eligen las secciones con casillas cada vez, y su caso de uso declarado es mandar a oficiales «lo que ha visto el encargado tras una revisión» | `2026-08-29-informe-obra-a-la-carta-diseno.md` | **H:** 5 obras × 1 informe/semana × ~10 min = ~50 min/semana, si los manda |
| F5 | **Materiales: solo «entregado», a mano, sin vigilancia.** Mungia: última entrada 08/05/2026 con obra viva hasta el 15/10 sin aviso; Olabeaga: 2 líneas sin suministrador/albarán | panel publicado (3.3); `entregas_materiales.py` | el control de pedidos se hace de cabeza o fuera del sistema |
| F6 | **Postventa: 2.786 incidencias en tablas Word, texto libre, sin tipo ni causa.** El flujo de la skill es «detectar archivos → leer PDFs → cruzar con Word → añadir filas → ordenar» | 3.5; skill `postventas-sagarde` | el histórico más rico no se puede consultar ni devolver a obra |
| F7 | **Serie histórica con denominadores mezclados** (Olabeaga 1295→1461; Mungia 88 %→43,5 %): cualquier tendencia calculada sobre ella arrastra el salto | informe D, F3; 3.1 | cualquier estadística o previsión nueva nacería rota si no se arregla esto antes |
| F8 | **«Avance medio» del inicio contaminado** (decisión 1 de G, pendiente) | G §1 | números del primer vistazo que no son los reales |
| F9 | **Copias `(2)/(3)` en `REVISIONES`**: a propósito, no es fricción de Bixente; coste menor: el motor elige por fecha de modificación y el auditor lo reporta como `info` | G §8 | nada que arreglar (no tocar) |

**Crítica a lo que ya existe:** el sistema es **fuerte en capturar y mostrar estado** y **débil en convertirlo en acción**. Las tres funciones que `CLAUDE.md` §1 promete («estimar consumos y anticipar pedidos», «analizar históricos de revisiones», «estadísticas») **no tienen ninguna implementación**: lo único «de análisis» es la prioridad por dependencias. Además, **tres decisiones ya tomadas por Bixente (G1, G3, G4) siguen sin implementar**: cualquier propuesta nueva compite con ellas por los mismos créditos.

**Descartado como fricción:** subir la tablet a la nube (no existe y §7c lo prohíbe); cobertura de la tablet (el informe C ya la cubre: PWA red-primero).

---

*Las secciones 2 (resumen), 5 (investigación web), 6 (ideas), 7 (propuestas) y 8 (fuentes) se añaden en las fases siguientes.*
