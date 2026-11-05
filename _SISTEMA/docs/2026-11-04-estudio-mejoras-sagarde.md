# Estudio de mejoras de Sagarde

**Fecha:** 04/11/2026 · **Estado:** COMPLETO (fases 0–6). Solo lectura sobre producción: no se ha tocado código ni datos de obra, no se ha ejecutado ningún `.bat`.

## 0. Resumen de una página

**Recomendación: empezar por el «Parte de cambios» (P1).** Es un parte por obra que dice *qué ha avanzado desde la revisión anterior* (por portal, planta y tajo), enchufado al «Informe de obra a la carta» que ya existe, **más un cambio pequeño y urgente de fondo: guardar las transiciones celda a celda («de X a M») que hoy el motor calcula y tira.**

**Por qué esa y no otra (hechos medidos):**
1. `ficha_obra.py:611` calcula en memoria `estados_cambiados = (clave, antes, después)` en cada revisión y **lo descarta**: `revisiones_aplicadas.jsonl` solo guarda el *número* (`celdas_cambiadas`). La ficha conserva únicamente el último estado y su fecha. **Cada revisión que pase sin guardarlo pierde para siempre el historial fino** que `CLAUDE.md` §1 promete («analizar históricos de revisiones», «estadísticas») y del que dependen una futura previsión y los rendimientos por tajo.
2. Hoy **no existe ningún «qué ha cambiado»** en panel ni informe (`grep` de ritmo/tendencia/fecha de fin: 0 lógica). Los datos para el 80 % del parte **ya están** en la ficha (`f` = fecha del último cambio de cada celda): sin entradas nuevas, sin app nueva, encaja con §7c.
3. Las ideas «bonitas» del encargo **no tienen datos hoy**: horas por tajo (el control horario lleva ámbito vivienda/garaje, no tajo; 140 persona-día, 1.154 h, desde el 12/10), comparar con las 128 obras cerradas (en git solo hay 3 paneles y un `cierre.json`) y pedidos anticipados (no existe cantidad *necesaria* ni *instalada*; las hojas `.xlsx` ni están en git).
4. Previsión de fin de obra: backtest propio, errores de −28 a +41 días **a umbrales del 70–85 %**; Mungia lleva 4 meses entre el 80 % y el 90 %. Una fecha de fin al 100 % con «intervalo de confianza» sería adorno. Se descarta hasta tener transiciones guardadas y la serie arreglada.

**Las tres propuestas:** **P1** Parte de cambios + guardar transiciones (1–2 sesiones, recomendada). **P2** Estadística de postventa sobre las 2.786 incidencias que ya hay (2 sesiones; datos reales, pero su uso en la semana a semana es menor). **P3** Materiales «necesario frente a entregado» (condicionada a que Bixente aporte cantidades; no la empezaría).

**Crítica al sistema:** fuerte en capturar estado, débil en convertirlo en acción; tres promesas de §1 sin implementar; tres decisiones ya tomadas por Bixente (G1 media del inicio, G3 plazos, G4 aviso de pendientes en `REVISIONES`) **siguen sin implementar** y compiten con esto por los mismos créditos: G4 en particular ataca el eslabón manual donde más se pierde y es más barata que cualquier propuesta nueva.

**Límites de este estudio:** no abrí las páginas de la competencia, solo los extractos del buscador (marcado en §5); las horas ahorradas son **hipótesis (H)**, no medidas; el histórico de 128 obras y las hojas de materiales viven fuera de git (no verificable).

---

## 1. Plan de trabajo

| Fase | Entregable | Tope | Estado |
|---|---|---|---|
| 0 Orientación | lecturas obligatorias de `CLAUDE.md` §5 | ~10 lecturas | hecha |
| 1 Inventario con cifras | scripts de solo lectura sobre fichas, jornadas, series, postventa | 6 scripts | hecha |
| 2 Dónde se pierde trabajo | fricciones con evidencia | grep + informes A–H | hecha |
| 3 Investigación web | ≥15 fuentes en ~25–30 búsquedas | 30 búsquedas | hecha (21 búsquedas, 33 URLs) |
| 4 Ideas | ≥10 puntuadas con criterios | 1 tabla | hecha (14 ideas) |
| 5 Propuestas | ≥2 completas, 1 recomendada | — | hecha (3) |
| 6 Entrega | este documento + resumen + 1 pregunta | — | hecha |

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

## 5. Fase 3 — Investigación web

**Cómo se hizo y límite:** 21 búsquedas; **solo leí los extractos que devuelve el buscador, no abrí las páginas completas** (no usé el agente de lectura). Por eso cada afirmación es «según el extracto». Lo de fabricantes es publicidad salvo que diga lo contrario. Cobertura: lo que **no** encontré (Cocoplan: funciones; Obralia: nada fiable; precios fiables de casi todo) está dicho en cada fila.

| # | Producto / fuente | Qué hace bien (según el extracto) | Qué copiar | Qué NO copiar (usuario único, portal estático, sin servidor) | URL |
|---|---|---|---|---|---|
| 1 | **Touchplan** (Last Planner) | PPC por semana, por gremio y por motivo de incumplimiento; informe de restricciones abiertas/resueltas; lookahead de 6 semanas | El **motivo de variación** junto al porcentaje; PPC por tajo/gremio | Multiusuario en tiempo real, edición colaborativa | https://touchplan.io/reporting/ |
| 2 | **Last Planner / PPC** (literatura) | PPC = actividades completadas / planificadas; Mortenson cita media del sector 54,4 % frente a ~70 % en su obra (fabricante/contratista, no estudio independiente); causas de incumplimiento | Medir el cumplimiento *de lo comprometido*, no solo el avance | Exigir a Bixente un plan semanal nuevo (rompe §7c) | https://www.mortenson.com/newsroom/improving-productivity-in-the-field · https://iglc.net/PAPERS/Details/1916 |
| 3 | **Cocoplan** (Valencia, basado en LPS) | Existe y se vende como software LPS; **no hallé** sus funciones concretas | Nada verificado | Todo lo no verificado | https://elreferente.es/startup/cocoplan |
| 4 | **Fieldwire** (Hilti) | Informes **programables** (p. ej. «todas las tareas abiertas eléctricas al subcontratista cada lunes»); tareas ligadas a plano; offline con sincronización | La idea de **informe recurrente con filtro por gremio**; exportar PDF/hoja | Envío automático por correo (no hay servidor); cuentas por usuario. Informes y estados personalizados son de pago | https://fieldwire.com/support/using-fieldwire · https://thedigitalprojectmanager.com/tools/fieldwire-review/ |
| 5 | **Raken** | Registra horas **y cantidades por código de coste** en el parte diario; compara con presupuesto y calcula eficiencia y tiempo proyectado. Producción solo en plan caro; el % se corta en 100 % | **Registrar horas por código de coste (= tajo)** es justo lo que le falta al control horario de Sagarde; presupuesto de horas por tajo | Exigir esto en la tablet **hoy**: más toques en obra con guantes y 23 plantas; solo cuando haya 6+ semanas de horas por ámbito | https://help.rakenapp.com/en/articles/14436994-how-to-track-production-hours-with-cost-codes-in-raken · https://help.rakenapp.com/en/articles/14492631-production-insights-in-raken |
| 6 | **busybusy** | Horas por proyecto y código de coste; avisa **horas sin asignar** día a día; compara horas estimadas/reales. Una reseña de 2024 dice que si el trabajador se salta el campo, queda sin atribuir | La alarma de **«horas sin asignar»** (en Sagarde: jornadas sin tajo) | GPS/geovalla, cuentas | https://busybusy.com/features/budgets-projects-cost-codes/ · https://timeero.com/reviews/busybusy-review |
| 7 | **Jibble / ClockShark** | Control horario con geovalla, offline, exportar XLS/CSV; ClockShark elige tarea al fichar | Exportar a hoja | Geovalla/biometría (el alcance de Bixente es «boceto», G §2) | https://www.jibble.io/construction-time-tracking · https://www.fool.com/the-ascent/small-business/time-clock/clockshark-review/ |
| 8 | **simPRO** | Pedidos de compra ligados a trabajo; consumos por trabajo; aprobación de pedidos; informe semanal de discrepancias de precio con proveedor | Ligar **material ↔ trabajo** y el informe de discrepancias (en Sagarde: líneas sin albarán) | Catálogos de proveedor, stock, facturación; integraciones por nivel de plan | https://helpguide.simprogroup.com/Content/Service-and-Enterprise/Create-a-Purchase-Order.htm · https://www.casestudies.com/company/simpro-software/case-study/middlebury-electric-customer-case-study |
| 9 | **Fergus / ServiceM8 / Tradify / Jobber** | Pensados para fontaneros/electricistas de servicio (presupuesto→factura); Fergus sigue material+horas+margen por trabajo | Nada de peso: son de **servicio y facturación**, no de obra por tajo | Facturación, agenda de cuadrillas | https://fergus.com/servicem8-vs-fergus/ · https://dev.to/tobydowns/best-job-management-software-for-nz-tradies-in-2026-tradify-vs-fergus-vs-servicem8-59el |
| 10 | **Procore** (informe de propietario / semanal) | El informe semanal estándar lleva: calendario, trabajo hecho, **trabajo próximo**, RFI/consultas; plantilla propia de cada contratista | **Estructura del parte semanal**: hecho / próximo / bloqueos | Todo el ecosistema | https://v2.support.procore.com/en-gb/process-guides/analytics-2.0-reports/owner-report · https://support.procore.com/tc/brinkmann/Procore_Process_Database/Weekly_Report |
| 11 | **Buildertrend** | «AI Client Updates»: resumen automático de la actividad de la obra hacia el cliente (en la hoja de ruta, estado «en curso» según la fuente) | La idea: resumen **generado desde la actividad**, no escrito a mano | Portal de cliente con cuenta | https://buildertrend-publicroadmap.launchnotes.io/board/keep-clients-informed-with-client-updates |
| 12 | **Dashpivot (Sitemate)** | Seguimiento de progreso sobre PDF/plano en tablet, offline | Confirma el modelo de Sagarde (hoja de campo → progreso); nada nuevo | Panel multiusuario | https://sitemate.com/?p=7631 |
| 13 | **Dalux Field** | Listas de comprobación **offline**: hay que *preparar* (descargar) antes de perder cobertura | Validan la decisión de Sagarde de que la descarga del HTML no dependa de la red | — | https://support.dalux.com/hc/articles/28263982197276 |
| 14 | **PlanRadar** | Informes de defectos filtrables por contratista y tipo; paneles de estadística de defectos | Filtrar incidencias **por tipo y por responsable** | No encontré evidencia de tendencia en el tiempo por contratista en PlanRadar, Autodesk Build o PlanGrid | https://planradar.com/snag-app/ |
| 15 | **Garantía en promotoras** (Punchlist Manager de Verisk, MASYC, Pivotal CRM) | Venden análisis de **causa raíz y tendencias por categoría/oficio** de las reclamaciones de postventa (publicidad del fabricante) | Campos mínimos: **vivienda, fecha, categoría del defecto, quién lo hizo**, si el mismo oficio lo repara | Su CRM completo | https://www.verisk.com/en-ca/products/punchlist-manager/ · https://masyc.squarespace.com/products/warranty · https://aihomebuilding.pages.dev/articles/warranty-callbacks-predictive-data.html |
| 16 | **Presto (RIB Spain)** | Estándar español de presupuesto, mediciones, certificaciones y **control de producción** | La idea de **mediciones por partida** como base de «cantidad necesaria» | Es presupuesto de oficina, no seguimiento de campo | https://www.softwaredoit.es/rib-spain/rib-spain.html · https://www.emagister.com/presto-certificacion-obra-cursos-3827455.htm |
| 17 | **Obralia** | **No encontré nada fiable** sobre la plataforma | — | — | (búsqueda sin resultado útil) |
| 18 | **OpenProject** (código abierto) | Paquetes de trabajo, Gantt con dependencias, tiempos y costes; BIM en edición de pago | Nada: es un gestor de proyectos con servidor y base de datos | Todo (necesita servidor) | https://thedigitalprojectmanager.com/es/tools/resena-de-openproject/ |
| 19 | **ERPNext / Odoo** (código abierto) | Consumo de material por tarea **no viene de serie**: hay módulos de pago o a medida | Confirma que «material por tarea» es un problema difícil incluso en ERP | Servidor, base de datos, modelo de stock | https://discuss.frappe.io/t/project-workflow-for-company-using-both-services-material-with-tracking-time-material-consumption/42747 · https://apps.odoo.com/apps/modules/19.0/job_order_material_consumption |
| 20 | **Pedidos justo a tiempo (Procore)** | El momento del pedido se calcula hacia atrás desde la fecha de necesidad del *lookahead* de 2–6 semanas, con plazo del proveedor | Modelo lógico: *necesito el tajo X en la planta Y en la fecha F → pedir en F − plazo* | Necesita fechas de necesidad, que Sagarde no tiene (Cocoplan es de la constructora y no está en git) | https://www.procore.com/en-au/library/just-in-time-delivery-construction |
| 21 | **NECA, unidades de trabajo** | Horas estándar por tarea eléctrica; normales/difíciles; ajustes por altura; la comparación «horas ganadas = cantidad × unidad frente a horas gastadas» es mi inferencia, no de la fuente | Idea de **horas ganadas** por tajo | El manual es de pago y de EE. UU.; no sirve para REBT/ICT sin calibrar | https://www.ecmweb.com/construction/estimating/article/20903843/understanding-labor · https://www.necaconvention.org/wp-content/uploads/2023/10/NECA-2023_Improving-and-Tracking-Labor-Productivity-with-Material-Management-_Matt-McDaniel-Dave-Gralike.pdf |

### Metodología de previsión (por qué no prometo fecha de fin)

- La previsión de duración por valor ganado es **más débil al principio** y se supone para proyectos grandes y largos; para pequeños puede no dar información fiable (extractos de revisión académica). Con la curva en S no lineal, de siete métodos comparados solo el filtro de Kalman fue robusto (Kim y Kim, 2014, según el extracto). Con muestras pequeñas se propone *bootstrap* de observaciones históricas (artículo de 2025, según el extracto). **No encontré** una fuente que cuantifique bandas de confianza con n pequeño: lo digo tal cual. Fuentes: https://pure.psu.edu/en/publications/sensitivity-of-earned-value-schedule-forecasting-to-s-curve-patte/ · https://iris.polito.it/handle/11583/2987791 · https://hrcak.srce.hr/file/199595.
- Mi propio backtest (§3.6) coincide: indicio, no prueba.

---

## 6. Fase 4 — Ideas puntuadas

Escala 0–3 (3 = mejor; en «esfuerzo» y «riesgo», 3 = menos esfuerzo/riesgo). **Ahorro** = hipótesis (H) con su cálculo. «Datos hoy» cita la cifra de §3.

| # | Idea | Ahorro/semana (H) | Datos hoy (cifra) | Esfuerzo (sesiones) | Riesgo | Encaje §7c y portal estático | Verificación | Total /15 | Decisión |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Parte de cambios por obra** + guardar transiciones | 2 — 5 obras × ~10 min = ~50 min (H: si manda 1 parte/semana a cada una) | 3 — `f` y `r` en 100 % de las celdas; 0 % de transiciones | 3 — 1–2 | 3 — aditiva, no mueve cifras | 3 — sale del mismo `.bat`, sin app | 3 — fixtures + mutación + antes/después | **14** | **P1, recomendada** |
| 2 | Avisos de pendientes en `REVISIONES` + estado de subida (**G3+G4 ya decididos**) | 2 — evita olvidos; H: 1 incidente/mes de ~30 min | 3 — auditor existe | 3 — 1 | 3 | 3 | 3 | **15** | **Hacer antes o con P1** (ya aprobado; no es propuesta nueva) |
| 3 | Estadística de postventa (tiempos, reincidencias, por tipo) | 1 — es insight, no ahorro semanal | 3 — **2.786** filas, 2.502 con fecha de recepción | 2 — 2 | 2 — privacidad, texto libre, 71 % en 2022 | 2 — pasa por el `.bat` de postventa; hay que confirmar camino | 2 | **12** | **P2** |
| 4 | Materiales «necesario frente a entregado» + pedidos | 3 si se acierta (H: 30–60 min/semana de cuentas de cabeza) | 0 — **no hay cantidad necesaria ni instalada**; `.xlsx` fuera de git | 1 — 3+ y depende de datos de Bixente | 1 — riesgo de ratios inventados | 2 | 2 | **9** | **P3 condicionada** |
| 5 | Previsión de fin de obra con intervalo | 1 | 1 — 2 obras con serie larga; errores −28/+41 d | 1 | 1 — riesgo de **publicidad** | 3 | 1 — no validable con n=2 | **7** | **Descartada** hasta tener transiciones y serie corregida (revisar con ≥4 obras con serie) |
| 6 | Horas por tajo / rendimiento | 2 | 0 — el control horario no tiene tajo; 3 semanas | 1 — toca la tablet | 1 — más toques en obra | 2 | 2 | **8** | **Aplazada**: cuando haya ≥6 semanas; primero «horas por punto de avance» por obra |
| 7 | Comparar con las 128 obras cerradas | 1 | 0 — en git: 6 ficheros | 0 | 2 | 2 | 0 | **5** | **Descartada**: sin datos; preguntar a Bixente si existen fuera del repo |
| 8 | PPC / plan semanal comprometido (Last Planner) | 2 | 1 — Cocoplan de Mungia fuera de git | 1 | 1 — pide un paso manual nuevo a Bixente | 1 — rompe «solo un fichero» | 1 | **6** | **Descartada** (puede volver si Bixente quiere un compromiso semanal) |
| 9 | Alerta de datos viejos por tipo (entrega de material de Mungia: mayo; control horario) | 2 | 3 — medido | 3 | 3 | 3 | 3 | **14** | **Meter en P1/G4** como ampliación pequeña |
| 10 | Corregir la serie histórica (denominadores 1295→1461; Mungia 88→43,5) | 1 | 3 | 2 | 2 | 3 | 3 | **12** | **Prerrequisito** de cualquier gráfica de tendencia; es «F3» del informe D |
| 11 | «Cola de obra»: qué queda en obras >85 % (Mungia 186 `P`) y desde cuándo | 2 | 3 | 2 | 3 | 3 | 3 | **13** | **Incluida en P1** como sección del parte; ojo: solapa con «Qué hacer ahora» del priorizador (comprobar) |
| 12 | Panel comparativo entre obras (ritmo, % por semana) | 1 | 2 — 5 obras, series dispares | 2 | 2 | 3 | 2 | **10** | Aplazada (misma razón que 5) |
| 13 | Informe de cierre automático con lecciones (horas, incidencias) | 1 | 1 | 1 | 2 | 2 | 1 | **7** | Descartada: cierre de expediente ya existe |
| 14 | Sustituir por herramienta comercial / ERP | 0 | – | 0 | 0 | 0 | 0 | **0** | **Descartada**: todas exigen servidor/cuentas, rompen §7c y el portal estático (OpenProject, ERPNext, Odoo); las comerciales son de servicio o de oficina |

**Si solo hay una buena, lo digo:** la idea 2 (avisos G3+G4) es la más barata y ya está aprobada; la idea 1 es la mejor *nueva*. No relleno más.

---

## 7. Fase 5 — Propuestas

### P1 · «Parte de cambios» + guardar las transiciones (RECOMENDADA)

**1. Problema con evidencia.** (a) El motor calcula `estados_cambiados = (clave, antes, después)` en `ficha_obra.py:611` y la traza `revisiones_aplicadas.jsonl` guarda solo el recuento (`celdas_cambiadas`; en Bolueta: 132 líneas, 120 son «historial consolidado», 12 `html_digital`, suma de cambios 1.766). La ficha guarda `{v, f, r}` y se sobrescribe. (b) Panel e informe enseñan el estado actual, un sparkline y `variacion_pct`; **ninguno dice qué se hizo desde la última vez** (F3, F4). (c) Lo que sí se puede reconstruir hoy: celdas cuya fecha `f` es posterior a la revisión anterior = lo que ha cambiado, sin el «de». Pero ojo: **fechas de carga masiva** (p. ej. 28/07: 1.410 celdas en Mungia, 1.314 en Bolueta; Gernika 80 % con fecha de historial base) no son avance de campo y hay que excluirlas.

**2. Qué vería Bixente** (boceto; en el panel de la obra y como bloque preseleccionado en «Informe de obra»):

```
OLABEAGA · cambios entre la revisión del 30/10 y la del 02/11
  Terminado (X):  +17 celdas · Más del 50 % (M): +3 · Iniciado (/): +9
  Bajan:           2 celdas (X→P) ← revisar: «lo que se apunta en la última vale»
  Por tajo:        Tubos en vivienda  +12  · Cajas y mecanismos  +8 · ...
  Por planta:      P3 +14 · P4 +7 · ...
  Sin tocar en 3 revisiones: Cuarto técnico (todas P)
  Quedan: 1.186 P  ·  desglose: X 209 · M 25 · / 41 · P 1186 · N 58
```

Nota: el «Bajan» solo es exacto con las transiciones guardadas (primera revisión tras implantarlo); antes aparece como «no se puede saber: no se guardó el estado anterior» — **nunca un 0**.

**3. Flujo conforme a §7c.** Entra: nada nuevo (misma hoja en `REVISIONES`, mismo «actualiza la obra»). Se extiende: al aplicar, la traza JSONL guarda además `transiciones: [[clave, de, a], ...]` (campo aditivo, mismo fichero, **sin tipo de fichero nuevo, sin `.gitignore`**). Se regenera: panel (sección nueva) y «Informe de obra» (bloque nuevo). Se ve: portal. Cómo lo haría el generador de revisiones: mismo patrón «fichero → traza → panel».

**4. Alcance mínimo (1–2 sesiones).** Sesión 1: guardar transiciones (+ prueba) y función pura `cambios_entre(ficha, fecha_desde)` sobre `f`; excluir fechas de carga masiva. Sesión 2: sección en panel + bloque en informe a la carta. **No hará:** previsión de fechas, horas, materiales, ni tocará la tablet.

**5. Verificación.** `unittest`: (i) fixture con 3 revisiones y cambios conocidos → el parte da exactamente esos; (ii) revisión sin cambios → muestra «0 cambios» explícito, no oculta el bloque; (iii) carga masiva no cuenta como avance. **Mutación:** invertir el comparador de fechas, no excluir la carga masiva, perder el campo `transiciones` en `_entrada` de `trazabilidad_revisiones.py`: cada una debe romper una prueba. **Antes/después:** desglose `X/M//P/?/N` y SHA-256 de `ficha_obra.json` de **todas** las obras idénticos (`actualizar_obra.py` ya lo hace); solo cambia la traza JSONL y el panel. Regla de la familia de fallos: una prueba que compruebe que lo declarado (`transiciones`) aparece en el panel.

**6. Riesgos / calidad del dato / decisiones.** Series cortas: Barakaldo 1 revisión (parte vacío con aviso). La baja `X→P` depende de que se guarde el estado anterior. Garajes usan `ficha_garajes.py:263`, también hay que cubrirlos (si no, repetimos «arreglar un camino y dejar roto su hermano», CLAUDE.md §6). **Decisiones de Bixente (una cada vez):** ¿el parte compara contra «la revisión anterior» o contra «hace 7 días»? (recomiendo la revisión anterior).

**7. Copiado / descartado.** Copio: estructura hecho-próximo-bloqueos de Procore, informe recurrente filtrable de Fieldwire, resumen generado desde la actividad de Buildertrend, motivo de variación de Touchplan. Descarto: envío automático por correo, cuentas, tiempo real.

**8. Coste.** 2 sesiones de nube (la 1ª puede hacerse sin él; la 2ª necesita su decisión sobre el formato). Valor: ~50 min/semana (H) + el historial fino que deja de perderse.

### P2 · Estadística de postventa con los datos que ya hay

**1. Problema.** 63 vistas previas de contratos, 45 con tablas, **2.786 incidencias** con recepción (2.502 legibles), resolución (2.340) y texto libre; **tiempo de resolución: mediana 7 días, p90 50 días** (1.976 pares). Hoy no hay consulta posible ni retorno a obra (F6). **Calidad:** columna OK con >6 variantes (`OK`, `SI`, `S`, `0K`…), años absurdos (`219`, `3018`), 2022 = 71 % de las filas (casi seguro pocas obras: no es tendencia).
**2. Qué vería.** En el índice de postventa: tabla por contrato (nº de incidencias, mediana y p90 de resolución, abiertas y su antigüedad) y, aparte, «reincidencias por palabras clave» (toma, diferencial, telefonillo, luz…) marcadas **como hipótesis de clasificación**.
**3. Flujo §7c.** Sin entrada nueva: el `.bat` ya regenera postventa (`Actualizar_Sagarde.bat`, paso 2); la estadística es un derivado más. **Por confirmar:** la fuente real son los Word en el PC (las vistas previas son derivadas); el cálculo debe leer la misma fuente que ya lee el pipeline, no las vistas previas.
**4. Alcance.** Tiempos, abiertas/antigüedad, normalización de OK y fechas con **lista de filas rechazadas** (nunca a cero). **No hará:** clasificar por IA ni asignar causa; no publicará nombres ni teléfonos.
**5. Verificación.** Fixture con filas conocidas (fechas inválidas, OK mal escrito); mutación del parser de fechas; conteo total = filas leídas + rechazadas (invariante); obras abiertas sin cambio.
**6. Riesgos.** **Privacidad:** esos ficheros públicos ya contienen datos de clientes (informe E, §5.1). La salida debe ir agregada. Decisión de Bixente: ¿vale el ahorro de nada semanal a cambio de poder responder «¿cuánto tardamos?»? Mi opinión: es útil para negociar con promotoras, pero **no ahorra trabajo**.
**7. Copiado.** Campos mínimos de garantía (vivienda, fecha, categoría, responsable) de Punchlist Manager/MASYC; filtro por tipo de PlanRadar. Descartado: CRM.
**8. Coste.** 2 sesiones; casi todo sin él.

### P3 · Materiales: necesario frente a entregado (no empezar aún)

**Problema.** Solo existe «entregado», y el panel avisa de que no equivale a instalado. Mungia sin entradas desde el 08/05/2026. **Bloqueo real:** sin cantidades necesarias por tajo o ubicación, cualquier «pedido anticipado» sería un ratio inventado (§10). **Lo que sí vale ya (pequeño):** aviso de «sin entregas desde hace N días» por obra (idea 9) y filas incompletas.
**Requiere de Bixente:** una fuente de cantidades necesarias (mediciones del proyecto o lista por vivienda tipo), una obra piloto y confirmar qué es «instalado». Mi recomendación: **no abrir P3** hasta tener eso; si lo tiene, es la de más valor potencial (idea 4) con riesgo de dato alto.
**Verificación futura.** Totales entregado ≥ necesario no se corrige a cero; mutación de unidad; desglose de obras no implicadas.
**Coste.** 3+ sesiones, dependientes de datos.

---

## 8. Fuentes

Todas consultadas el 04/11/2026 **solo mediante extractos del buscador** (no se abrieron las páginas); precios de todas: sin verificar.

1. https://touchplan.io/reporting/
2. https://www.mortenson.com/newsroom/improving-productivity-in-the-field
3. https://iglc.net/PAPERS/Details/1916
4. https://elreferente.es/startup/cocoplan
5. https://fieldwire.com/support/using-fieldwire
6. https://thedigitalprojectmanager.com/tools/fieldwire-review/
7. https://help.rakenapp.com/en/articles/14436994-how-to-track-production-hours-with-cost-codes-in-raken
8. https://help.rakenapp.com/en/articles/14492631-production-insights-in-raken
9. https://busybusy.com/features/budgets-projects-cost-codes/
10. https://timeero.com/reviews/busybusy-review
11. https://www.jibble.io/construction-time-tracking
12. https://www.fool.com/the-ascent/small-business/time-clock/clockshark-review/
13. https://helpguide.simprogroup.com/Content/Service-and-Enterprise/Create-a-Purchase-Order.htm
14. https://www.casestudies.com/company/simpro-software/case-study/middlebury-electric-customer-case-study
15. https://fergus.com/servicem8-vs-fergus/
16. https://v2.support.procore.com/en-gb/process-guides/analytics-2.0-reports/owner-report
17. https://buildertrend-publicroadmap.launchnotes.io/board/keep-clients-informed-with-client-updates
18. https://sitemate.com/?p=7631
19. https://support.dalux.com/hc/articles/28263982197276
20. https://planradar.com/snag-app/
21. https://www.verisk.com/en-ca/products/punchlist-manager/
22. https://masyc.squarespace.com/products/warranty
23. https://aihomebuilding.pages.dev/articles/warranty-callbacks-predictive-data.html
24. https://www.softwaredoit.es/rib-spain/rib-spain.html
25. https://thedigitalprojectmanager.com/es/tools/resena-de-openproject/
26. https://discuss.frappe.io/t/project-workflow-for-company-using-both-services-material-with-tracking-time-material-consumption/42747
27. https://apps.odoo.com/apps/modules/19.0/job_order_material_consumption
28. https://www.procore.com/en-au/library/just-in-time-delivery-construction
29. https://www.ecmweb.com/construction/estimating/article/20903843/understanding-labor
30. https://pure.psu.edu/en/publications/sensitivity-of-earned-value-schedule-forecasting-to-s-curve-patte/
31. https://iris.polito.it/handle/11583/2987791
32. https://hrcak.srce.hr/file/199595
33. https://www.necaconvention.org/wp-content/uploads/2023/10/NECA-2023_Improving-and-Tracking-Labor-Productivity-with-Material-Management-_Matt-McDaniel-Dave-Gralike.pdf

**Medidas propias** (scripts de solo lectura, 04/11/2026): recuentos de §3 sobre `ficha_obra.json`, `ficha_garajes.json`, `personal_obra.json`, `revisiones_aplicadas.jsonl`, `panel.html` publicado y `POST-VENTAS/_SISTEMA/_PREVIEWS_WORD/*.html`. No se ejecutó la suite ni ningún `.bat`.

