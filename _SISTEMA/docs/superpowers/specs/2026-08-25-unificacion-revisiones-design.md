# Unificación del sistema de actualización de revisiones de obra — auditoría y arquitectura objetivo

Fecha: 25/08/2026. Autor: Claude (auditoría inicial, sin tocar código).
Encargo de Bixente: eliminar la dispersión entre los métodos de actualizar
una obra desde una hoja de revisión (papel escaneado, PDF digital, HTML) y
dejar un único sistema conceptual, sin romper lo que ya funciona.

Este documento es el resultado de la **Fase -1 / primera tarea**: analizar
el entorno existente y proponer plan y arquitectura, sin programar nada
todavía. No avanzar a la Fase 0 de Codex sin que Bixente haya revisado esto.

**Fin al que sirve todo esto (releer antes de cada fase, para no perder
el rumbo):** un único sistema conceptual de actualización de revisiones
que acepte los tres orígenes (papel escaneado, PDF digital, HTML
digital), los normalice a una estructura común, los valide con reglas
compartidas, actualice `ficha_obra.json` desde un único motor, deje
trazabilidad unificada, **sin romper los caminos actuales hasta que la
paridad esté demostrada**, con tests, documentado, y cerrado con una
auditoría final independiente de Claude. Prioridad, en este orden:
integridad de los datos > compatibilidad > simplicidad arquitectónica >
facilidad de uso > funcionalidades nuevas.

**Modo de ejecución (25/08/2026, autorizado por Bixente):** continuar
fase por fase de la tabla de la sección F de forma autónoma hasta el
final, sin pararse a pedir revisión entre fases salvo bloqueo genuino
(ambigüedad real no resoluble investigando, riesgo de pérdida de datos,
o decisión que solo Bixente puede tomar). Ante cualquier alternativa
técnica, elegir siempre la más recomendada. Excepción ya vigente y que
esto NO cambia: `_SISTEMA/MOTOR/` no se toca sin volver a preguntar
explícitamente (decisión de Bixente del 25/08/2026, ver
`project_sagarde_motor_claude_md_secundario` en memoria).

---

## A. Estado actual

**Hallazgo principal: los "Método 2 (PDF digital)" y "Método 3 (HTML)" del
encargo original no son dos sistemas — son el mismo artefacto.**

`generador_revisiones.html`
(`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html`)
es una única app: un asistente (`sc-wizard`) que configura la obra y genera
la hoja vacía, y la hoja generada en sí, que trae cada celda como
`<td data-k="..." data-st="">` con un `click` que cicla
`''→'/'→'M'→'X'` (líneas 1173, 1179-1188) y autoguardado en `localStorage`.
Esa misma hoja abierta en el navegador tiene los botones:

- `printRevision()` (línea 1205) → `window.print()` → el PDF ("Método 2").
- `doSave()` (línea 1191) → descarga el HTML con los `data-st` ya rellenos,
  mismo nombre base ("Método 3").

Es el mismo evento de edición, exportado en dos formatos.

### Los tres orígenes reales, y cómo entra cada uno hoy

| Origen | Qué es | Herramienta de lectura | Destino | Nivel de verificación |
|---|---|---|---|---|
| Papel + boli + escaneo | Marca a boli sobre el PDF impreso (o pen digital), escaneo, lectura por visión IA | `leer_hoja_marcada.py --preparar/--aplicar` (geometría de `rejilla_hoja.py` + clasificación visual, dos fases) | `ficha_obra.json` directo | Alto: 5 hojas de 3 obras, incluida verdad conocida a mano |
| Digital, exportación PDF | `generador_revisiones.html`, botón "Imprimir" | `leer_hoja_marcada.py --digital` (lee el texto ya impreso vía `pdfplumber` + geometría) | `ficha_obra.json` directo | Bajo: un solo uso real (Bolueta 24/08/2026), con 4 bugs reales encontrados en ese único uso |
| Digital, exportación HTML | Mismo generador, botón "Guardar revisión" | `lector_hoja_tajos_html.py` (regex sobre `data-k`/`data-st`, sin geometría) | Vía adaptador (hoy solo `adaptador_gernika.py`) → `generar_todos.py` → `ficha_obra.json` indirectamente | Activo desde 25/07/2026, pero solo para Gernika |

La skill publicada `.claude/skills/sagarde-revision/SKILL.md` cubre los dos
primeros caminos y los documenta bien. **No menciona el tercero.**

### Las dos vías independientes que escriben en `ficha_obra.json`

Confirmado a nivel de código, con el mecanismo exacto:

1. **Vía skill** — `leer_hoja_marcada.py` (Flujo A o `--digital`) escribe en
   `ficha_obra.json` directamente, sin pasar por ningún adaptador.
2. **Vía adaptadores** — `generar_todos.py`, en su bucle por obra, hace
   `historial = adaptador.cargar_historial()` (línea ~850) y si existe
   ficha, `fichas.actualizar_desde_snapshot(ficha_actual, snapshot_crudo, ...)`
   (línea ~902) también escribe en `ficha_obra.json`, tomando el snapshot
   del historial crudo del adaptador.

Para Gernika, `adaptador.cargar_historial()` fusiona JSON legado **y el
HTML exportado por el mismo generador**
(`adaptador_gernika.py:220-265`), con esta regla textual en el propio
código: *"Si una misma fecha existe en ambos formatos, gana el HTML por
ser la exportación más completa/reciente"*.

**Consecuencia verificada:** para Gernika, una hoja rellenada en el
generador puede entrar en `ficha_obra.json` por DOS caminos independientes
y no coordinados: si alguien ejecuta `leer_hoja_marcada.py --digital`
sobre el PDF gemelo, y en algún momento se ejecuta `generar_todos.py` (que
ocurre en cada publicación), el HTML gemelo también se procesa
automáticamente vía `adaptador_gernika → lector_hoja_tajos_html →
actualizar_desde_snapshot`. Cada camino resuelve claves y nombres de tajo
con vocabularios distintos. Es el patrón de "guarda compartida" que el
`CLAUDE.md` raíz marca como la familia de fallos de este proyecto — no
detectado aún como incidente, pero con la maquinaria puesta para que
ocurra.

`regenerar_obra.py` no es una tercera vía: es un envoltorio de la Vía 2
limitado a una sola obra.

---

## B. Mapa de arquitectura actual

```
                         generador_revisiones.html
                    (wizard + hoja interactiva, clic en celda)
                                    │
                    ┌───────────────┴───────────────┐
                    │ printRevision()                │ doSave()
                    ▼                                ▼
              hoja A4 → PDF                    hoja → HTML
           (texto ya impreso,                (data-k/data-st
            sin anotaciones)                   embebidos)
                    │                                │
       ╔════════════╪═══════════════╗                │
       ║  boli en obra (opcional)   ║                │
       ║  → escaneo con tinta       ║                │
       ╚════════════╪═══════════════╝                │
                    │                                │
        ┌───────────┴────────────┐                   │
        ▼                        ▼                   ▼
  leer_hoja_marcada.py    leer_hoja_marcada.py   lector_hoja_tajos_html.py
   --preparar/--aplicar        --digital          (solo adaptador_gernika)
   (tinta, rejilla_hoja)   (texto impreso,               │
        │                   rejilla_hoja)                ▼
        │                        │                adaptador.cargar_historial()
        └───────────┬────────────┘                       │
                     ▼                                    ▼
              ficha_obra.json  ◄──── actualizar_desde_snapshot ── generar_todos.py
              (escritura DIRECTA         (VÍA 2, snapshot del historial crudo)
               desde la skill,
               VÍA 1)
                     │
                     ▼
     motor_informes / priorizador / panel / informe ejecutivo / portal
```

Dos motores de escritura de estado, dos vocabularios de resolución de
claves, un único fichero de destino.

---

## C. Problemas detectados

1. **Duplicidad real, no solo nominal**, para las obras híbridas (Mungia,
   Gernika, Bolueta): dos escritores independientes de `ficha_obra.json`.
2. **El camino más fiable está infrautilizado.** `lector_hoja_tajos_html.py`
   lee `data-k`/`data-st` por regex — exacto, sin geometría, sin los bugs
   de tolerancia/columnas ya sufridos. Hoy solo alimenta la Vía 2, y solo
   para Gernika.
3. **Nomenclatura confusa.** "PDF digital" y "HTML" no son dos orígenes:
   son dos formatos de exportación del mismo evento de edición. Cualquier
   documento nuevo debe decirlo explícitamente.
4. **Adaptadores con estado desconocido.** El mapa mental
   (`_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`, fila A07) dice
   "7 adaptadores; 5 activos; 2 sin uso" sin nombrarlos.
5. **Validación repartida.** Reglas como "blanco no baja una X", "un
   retroceso se acepta a la primera", "sin tinta no hay cambio" están
   reimplementadas por separado en varios módulos.
6. **Trazabilidad fragmentada.** Flujo A/B dejan `.clasificacion.json`/
   `.correcciones.json`; la Vía 2 no deja sidecar equivalente por revisión.
7. **Sin dry-run uniforme.** `generar_todos.py` no tiene modo simulación
   para la escritura en ficha.
8. **Capa de documentación secundaria desactualizada**
   (`_SISTEMA/MOTOR/CLAUDE.md` y sus tres agentes): rutas muertas
   (`_MOTOR_SAGARDE\`), no menciona `--digital` ni HTML. Bixente decidió
   el 25/08/2026 dejarla tal cual por ahora — **no tocar sin volver a
   preguntar**.
9. **Flujo B tiene una sola verificación real** (un uso, cuatro bugs
   encontrados en ese único uso).

---

## D. Arquitectura objetivo

```
CAPA 1 — ENTRADA (ya existente, se mantiene)
  · Escaneo/foto con tinta            → PDF con anotaciones o imagen
  · Exportación digital del generador → PDF (texto impreso) + HTML (data-k/st)

CAPA 2 — ADAPTADORES (reutilizar, no reescribir)
  · rejilla_hoja.py           → común, ya sirve para tinta y texto impreso
  · lector_hoja_tajos_html.py → YA es el lector ideal para exportación
                                  digital; pasa a ser la vía PREFERENTE
                                  para Flujo B cuando el .html gemelo exista
  · Camino visión IA          → único camino para tinta real

CAPA 3 — REVISIÓN NORMALIZADA (nueva, pequeña)
  {obra, portal, planta, vivienda, tajo, estado_anterior, estado_nuevo,
   fecha, origen (tinta|pdf_digital|html_digital), revision_id}
  Reutiliza el vocabulario existente: clave portal__planta__tajo__vivienda,
  alfabeto X/M//P/?/N de ficha_obra.py.

CAPA 4 — VALIDACIÓN (nueva, une lo disperso)
  Módulo único con las reglas ya escritas pero repartidas: catálogo de
  tajos, blanco-no-baja-un-estado-conocido, retroceso aceptado a la
  primera, sin-tinta-no-hay-cambio, alfabeto válido.

CAPA 5 — ACTUALIZACIÓN (nueva: apply_revision())
  Único punto que escribe en ficha_obra.json. Sustituye a los dos
  escritores actuales, que pasan a ser productores de REVISION_NORMALIZADA.

CAPA 6 — TRAZABILIDAD (extiende el sidecar existente)
  Log por revisión aplicada (obra, fecha, origen, celdas antes/después),
  común a los tres orígenes.
```

**Decisión de diseño derivada de lo verificado en código:** cuando una
revisión digital traiga su `.html` gemelo, la Capa 2 debe preferir
`lector_hoja_tajos_html.py` sobre la relectura de texto del PDF. La
lectura de texto del PDF (`--digital` actual) queda como *fallback* solo
para cuando no exista el HTML gemelo. Esto reduce la superficie de la
maquinaria de geometría — la que ya ha dado los bugs más caros del
proyecto — al único caso donde de verdad hace falta: la tinta real.

---

## E. Plan de migración (sin romper nada)

1. No tocar los escritores actuales todavía. Construir Capas 3-4-5 en
   paralelo, sin que nada las llame en producción.
2. Pruebas de paridad antes que cutover: para cada camino existente, el
   nuevo `apply_revision()` debe reproducir EXACTAMENTE el resultado que
   produce hoy sobre las revisiones ya conocidas (5 hojas de Flujo A con
   verdad conocida, la de Bolueta de Flujo B, el historial de Gernika).
3. Cutover por camino, uno cada vez, de menor a mayor riesgo: HTML
   (Gernika) → PDF-digital (con preferencia al HTML gemelo si existe) →
   tinta → `generar_todos.py` deja de llamar a `actualizar_desde_snapshot`.
4. Cada cutover se verifica contra las obras NO implicadas (deben quedar
   exactamente igual).
5. Retirada del código viejo solo al final, con los tres caminos
   funcionando sobre el motor común sin discrepancias.
6. La capa secundaria `_SISTEMA/MOTOR/` no se toca en ninguna fase sin
   volver a preguntar a Bixente explícitamente.

---

## F. Plan de trabajo Claude → Codex

| Fase | Objetivo | Riesgo |
|---|---|---|
| 0 | Inventario técnico verificado: confirmar/corregir este documento contra el código actual, identificar los 2 adaptadores "sin uso", listar TODOS los llamadores de las funciones clave | Ninguno (solo lectura) |
| 1 | Diseño del modelo REVISION_NORMALIZADA y del validador común — con aprobación de Bixente | Ninguno (diseño) |
| 2 | Validador común + tests, sin conectar a nada todavía | Bajo |
| 3 | `apply_revision()` + tests de paridad contra los 3 caminos actuales | Bajo |
| 4 | Adaptador HTML→normalizada + cutover Gernika + verificación de no-regresión | Medio |
| 5 | Adaptador PDF-digital→normalizada (preferencia a HTML gemelo) + cutover Flujo B | Medio |
| 6 | Adaptador tinta→normalizada + cutover Flujo A | Alto |
| 7 | `generar_todos.py` usa el motor común en vez de `actualizar_desde_snapshot` | Alto |
| 8 | Trazabilidad unificada (log de revisiones) | Bajo |
| 9 | Dry-run uniforme en los tres caminos | Bajo |
| 10 | Actualizar skill `sagarde-revision`; decidir con Bixente qué hacer con `_SISTEMA/MOTOR/` | — |
| 11 | Documentación final + actualizar el mapa mental | Bajo |
| 12 | Auditoría final (Claude, independiente) | — |

No se avanza de fase sin revisión de la anterior.

---

## G. Prompt de Codex — Fase 0 (solo inventario, cero escritura de datos)

Ver fichero hermano
`2026-08-25-unificacion-revisiones-fase0-prompt.txt` (texto plano, listo
para `codex exec`) y el comando de lanzamiento en PowerShell documentado
junto a él / en la respuesta de Claude del 25/08/2026.

Entregable esperado de la Fase 0:
`_SISTEMA/docs/2026-08-25-auditoria-revisiones-fase0-codex.md`

---

## Bitácora de fases ejecutadas (registro corto; el detalle vive en el
informe de cada fase, no se duplica aquí)

| Fase | Estado | Entregable | Auditado por Claude |
|---|---|---|---|
| 0 — Inventario | ✅ Hecho 25/08 | `_SISTEMA/docs/2026-08-25-auditoria-revisiones-fase0-codex.md` | Sí — ver corrección Bolueta/Gernika abajo |
| 1 — Diseño REVISION_NORMALIZADA + validador | ✅ Hecho 25/08 (Claude) | Sección "Fase 1" de este documento | — |
| 2 — Validador común + tests | ✅ Hecho 25/08 | `validar_revision.py` + `tests/test_validar_revision.py` + `_SISTEMA/docs/2026-08-25-fase2-codex-informe.md` | Sí — código leído entero, `git status` confirma solo 3 ficheros nuevos, 490/490 tests (4 omitidos) verificado |
| 3 — `apply_revision()` + paridad | ✅ Hecho 25/08, con hallazgo crítico | `aplicar_revision.py` + `tests/test_aplicar_revision.py` + `_SISTEMA/docs/2026-08-25-fase3-codex-informe.md` | Sí — hallazgo verificado y corregido, ver Fase 3b |
| 3b — corrección de mayúsculas en la clave | ✅ Hecho 25/08 | Corrección en `validar_revision.py`, sección añadida a `fase3-codex-informe.md` | Sí — diff leído, `_partes_clave`/`_ubicacion_existe` verificados, 508 tests sin expectedFailure |
| 4 — Adaptador HTML→normalizada, generalizado a toda obra | ✅ Hecho 25/08, con hallazgo mayor | `adaptar_revision_html.py` + `tests/` + `_SISTEMA/docs/2026-08-25-fase4-codex-informe.md` | Sí — código leído, diseño de doble-mapa-con-desambiguación verificado |
| 5 — Adaptador PDF-digital→normalizada | ✅ Hecho 26/08 (reanudada tras corte de cuota) | `adaptar_revision_pdf_digital.py` + `tests/` + `_SISTEMA/docs/2026-08-25-fase5-codex-informe.md` | Sí |
| 6 — Adaptador tinta→normalizada | ✅ Hecho 26/08, con 2 hallazgos reales | `adaptar_revision_tinta.py` + `tests/` + `_SISTEMA/docs/2026-08-25-fase6-codex-informe.md` | Sí — ver Fase 6b |
| 6b — corrección: `P` explícita y semántica de `descartada` | ✅ Hecho 26/08 | Corrección en `validar_revision.py`/`adaptar_revision_tinta.py`, sección añadida a `fase6-codex-informe.md` | Sí — `ALFABETO_HOJA` verificado por origen, Mungia real da 12/12 |
| 7 — Cutover del CLI `leer_hoja_marcada.py` al motor común | ✅ Hecho 26/08 (dos intentos, el primero cortado por disco lleno) | `leer_hoja_marcada.py` modificado + `tests/test_cutover_leer_hoja_marcada.py` + `_SISTEMA/docs/2026-08-25-fase7-codex-informe.md` | Sí — código de la salvaguarda leído línea a línea, confirma `ficha_actualizada` del motor nuevo, gateada por paridad con el camino antiguo |
| 8 — Cutover de `generar_todos.py` | ✅ Hecho 26/08 | `generar_todos.py`/`validar_revision.py` modificados + `tests/test_cutover_generar_todos.py` + `_SISTEMA/docs/2026-08-25-fase8-codex-informe.md` | Sí — código de la salvaguarda y el bloqueo de doble escritura leídos y confirmados línea a línea |
| 9 — Trazabilidad unificada | ✅ Hecho 26/08 | `trazabilidad_revisiones.py` + `tests/` + `.gitignore` + `_SISTEMA/docs/2026-08-25-fase9-codex-informe.md` | Sí |
| 10 — Dry-run uniforme | ✅ Ya conseguido de forma emergente (verificado, sin fase de Codex nueva) | — | Sí |
| 11 — Actualizar skill `sagarde-revision` | ✅ Hecho 26/08 (Claude, sin Codex) | `.claude/skills/sagarde-revision/SKILL.md` actualizado | — |
| 12 — Documentación final + mapa mental | ✅ Hecho 26/08 | Mapa mental actualizado (A26-A31), `SAGARDE_MOTOR_REVISIONES_GUIA_RAPIDA.md`, `_SISTEMA/docs/2026-08-25-fase12-codex-informe.md` | Sí — `git diff` del mapa mental leído, bloques `<!-- AUTO -->` regenerados con su script canónico, no a mano |
| 13 — Auditoría final independiente | ✅ Hecho 26/08 (Claude) | `_SISTEMA/docs/2026-08-26-auditoria-final-unificacion-revisiones-claude.md` | — (es la propia auditoría) |

## PROYECTO CERRADO — 26/08/2026

Los 12 criterios de éxito del encargo original, contrastados uno a uno en
la auditoría final: 11 cumplidos, 1 no aplica (multi-dispositivo — no se
tocó la interfaz del navegador en ningún momento de este proyecto).
Pendientes explícitos, ninguno bloqueante: retirar la salvaguarda de
doble cálculo cuando haya histórico real suficiente, decidir la guarda
`antes=None`, y `_SISTEMA/MOTOR/` sigue esperando decisión de Bixente.
Detalle completo en la auditoría final.

### Fase 9 — trazabilidad común, aditiva, que nunca bloquea una escritura ya validada

Log JSONL por obra (`INFORME SAGARDE IA/revisiones_aplicadas.jsonl`),
solo se escribe DESPUÉS de que la ficha real ya se guardó tras superar la
salvaguarda — nunca en simulación, nunca en una revisión bloqueada. Un
fallo al escribir el log se captura, avisa por consola y no revierte ni
bloquea la persistencia ya hecha (probado con un `OSError` sintético).
`.gitignore` tocado de forma mínima y coherente con el patrón ya
existente (lista blanca, una excepción estrecha para este fichero
concreto, igual que ya existe para `ficha_obra.json`).

### Fase 10 — dry-run uniforme, sin trabajo nuevo

Revisado sin lanzar una fase de Codex: `apply_revision(dry_run=True)` ya
es el valor por defecto en los tres caminos desde la Fase 3; el CLI de
`leer_hoja_marcada.py` sigue simulando por defecto sin `--escribir`
(Fase 7); y el cutover de `generar_todos.py` (Fase 8) calcula siempre
ambos caminos en memoria antes de decidir si guarda, por obra — un
dry-run automático incorporado, no manual. No hacía falta construir nada
más para cumplir este punto del plan original.

### Fase 8 — segundo y último cutover grande, con aislamiento por obra verificado

Bixente autorizó continuar con ~6,4 GB libres en C: tras liberar algo de
espacio ("tengo que arriesgarme para poder borrar la caché de Codex").
Con `--ephemeral` el consumo de disco fue mínimo (6,6 GB al terminar,
prácticamente el mismo).

Investigación previa (obligatoria) confirmó tres cosas importantes: (1)
`snapshot_crudo` es una fotografía completa de la última fecha, no una
lista de cambios; (2) `actualizar_desde_snapshot()` y `actualizar()`
siguen siendo literalmente la misma lógica, no dos implementaciones; (3)
el HTML de Gernika sigue sin conflicto real con el CLI de la Fase 7
(idempotente, sin duplicar aritméticamente) — **decisión explícita de no
tocarlo en esta fase**, con la evidencia documentada.

Como el dato que recibe este camino ya mezcla varias fuentes históricas
por obra, se añadió un cuarto origen honesto (`historial_consolidado`) en
vez de forzarlo a `tinta`/`pdf_digital`/`html_digital` — decisión
correcta, verificada por Claude en el código.

**Aislamiento por obra, verificado leyendo el código línea a línea:**
`bloquear_guardado_ficha = not ficha_cutover_aplicada`
(`generar_todos.py:1163`) impide tanto el guardado del motor común como
el guardado posterior que haría el priorizador
(`generar_todos.py:1186-1187`) — una obra que diverge no se actualiza,
pero el resto del pipeline de esa obra y las demás obras siguen
normalmente. No hay `SystemExit` global.

**Verificado empíricamente contra las 4 obras reales que hoy tienen
ficha e historial** (Gernika, Mungia, Bolueta, Obra Prueba): **0
discrepancias en las 4**, SHA-256 de las fichas reales confirmados
idénticos antes y después. Gorliz (sin ficha aún) queda fuera del
cutover, comportamiento anterior sin cambios. Suite completa: 547 tests,
0 fallos — y los 4 fallos "ambientales" de la Fase 7 pasan limpio esta
vez, confirmando que eran del entorno, no del código.

### Fase 7 — primer cutover real, con salvaguarda de doble cálculo probada

Verificado por Claude leyendo el código (no solo el informe): en
`--aplicar`/`--digital` con `--escribir`, el CLI calcula el resultado por
el camino antiguo (`aplicar()`/`aplicar_digital()`) Y por el motor común
(`validar()`+`apply_revision()`) de forma independiente, compara el valor
`v` de cada clave, y solo si son idénticos guarda
`aplicacion['ficha_actualizada']` (la del motor nuevo) — nunca la del
camino antiguo. Ante cualquier discrepancia aborta con `SystemExit(2)`
sin tocar disco. Probado con una divergencia forzada artificialmente:
aborta, 0 llamadas a `fichas.guardar`, ningún sidecar creado.

**Verificado contra los tres casos reales ya usados en fases anteriores,
en modo simulado sin tocar ficha real** (SHA-256 de las fichas y sidecars
reales confirmados idénticos antes y después): Bolueta 26/07 tinta (3.838
celdas), Mungia 27/07 tinta (2.356 celdas, incluidos los 12 cambios reales),
Bolueta 24/08 digital con HTML gemelo preferido (3.686 celdas, 443
cambios) — **0 discrepancias en los tres**.

**Pendiente, no urgente:** la única ejecución completa de la suite (540+5
tests) no salió "verde" por una causa puramente ambiental (TEMP
redirigido dentro del repo por falta de espacio en C:), no por una
regresión — los dos módulos afectados se re-ejecutaron aislados con su
entorno normal y pasaron íntegros (24/24 y 7/7). Repetir la suite
completa de una sentada, con margen normal de disco, cuando sea posible.

**Bloqueo actual: disco de la máquina de Bixente.** C: ha bajado de 238
GB completamente llenos a ~105 MB libres tras dos intentos de esta fase,
incluso usando `--ephemeral` y prohibiendo copiar árboles de directorios.
No arrancar la Fase 8 (cutover de `generar_todos.py`, mayor alcance: toca
las 5 obras reales en cada publicación) sin más margen.

Con la Fase 6b, los tres adaptadores (tinta, pdf_digital, html_digital)
están construidos, verificados por Claude y validados contra datos reales
con paridad exacta demostrada. A partir de aquí empieza la parte de
mayor riesgo: conectar el motor nuevo a los caminos que Bixente usa de
verdad.

### Fase 6b — dos huecos reales del modelo, confirmados con Mungia 27/07 real

1. **`P` explícita no cabía en el alfabeto de hoja.** El `.clasificacion.json`
   real permite marcar una celda directamente como `P` (el corrector,
   visto y confirmado pendiente), y `aplicar()` la trata como marca
   explícita (`M -> P` a la primera). `ALFABETO_HOJA` solo admitía
   `X/M//blanco/N` — un hueco de mi propio diseño de Fase 1, no un fallo
   de implementación. Confirmado con datos reales: de las 12 correcciones
   reales de Mungia 27/07, el motor común solo proponía 9 — las 3
   perdidas eran exactamente `M -> P` en `casquillos_bombillas`.
2. **Una candidata `descartada` sí participa hoy en el barrido
   `--sin-marca pendiente`.** El código antiguo descarta la marca
   clasificada pero deja la celda disponible para que
   `marcar_no_empezados()` la suba de `?` a `P` si estaba en blanco. El
   adaptador nuevo la excluía del barrido por completo — más
   conservador, pero no es lo que hace hoy el sistema.

**Corrección, en los dos casos: igualar al comportamiento actual**, no
decidir cuál "debería" ser mejor — es la política ya establecida en este
proyecto (paridad antes que cambio de comportamiento). `P` se admite como
marca explícita solo para origen `tinta` (nunca para `pdf_digital`/
`html_digital`, que no pueden imprimirla); `descartada` deja de excluirse
del barrido de blancos.

### Fase 5 — resultado destacado: PDF y HTML llegan al mismo resultado exacto sobre datos reales

Comparación empírica final sobre la revisión real de Bolueta 24/08/2026,
misma ficha "antes" que la Fase 4 (commit `a616f91`, leída con `git
show`, sin checkout): el camino PDF-digital (corregido, geometría) y el
camino HTML-digital (atributos `data-k`/`data-st`) proponen exactamente
**443 actualizaciones cada uno, las mismas 443 en clave y valor, 0
exclusivas de un camino, 0 valores distintos para la misma clave**. El
HTML trae más celdas en bruto (3.686 frente a 1.963) solo porque incluye
los blancos, que se validan como `conservar` en ambos caminos por igual
— no es una discrepancia.

Con esto, la recomendación de preferir el HTML (sección D) queda
respaldada dos veces con datos reales: una vez porque recuperó sin fallos
las 411 celdas que el PDF sí perdió antes de corregir sus bugs (Fase 4),
y ahora porque, ya con el PDF corregido, ambos caminos coinciden al
100%. El PDF sigue siendo un *fallback* válido, no un camino inferior en
este caso — pero es más frágil por depender de geometría.

**Pendiente sin resolver, de riesgo bajo, para antes de la Fase 7:** con
una clave sin registro previo en `estados` (`antes=None`), el código
antiguo aborta (`LecturaImposible`); el motor nuevo la acepta y crea la
celda. Bajo riesgo real porque toda ficha se siembra con `?` en todas las
combinaciones válidas, pero es una guarda que el motor nuevo no replica
todavía.

### Fase 5 — pausada por límite de cuenta de Codex, no por un fallo del proyecto

`codex exec` devolvió "hit your usage limit... try again at Aug 26th,
2026 2:21 AM" tras escribir el módulo y los tests pero antes del informe
final. Verificado por Claude de forma independiente: los 7 tests nuevos
pasan, y la suite completa (524 tests) no tiene regresiones.

**Hallazgo real encontrado por los tests nuevos, de riesgo bajo pero sin
resolver:** con una ficha sin ningún registro previo para una clave
(`antes=None`), el código antiguo (`aplicar_digital`) aborta con
`LecturaImposible`; el motor nuevo la acepta y crea la celda. Codex no lo
ocultó — lo dejó como test explícito, no como `expectedFailure`. Claude
verificó por qué probablemente no afecta a datos reales:
`ficha_obra.py:689-696` siembra con `'?'` **todas** las combinaciones
válidas de portal/planta/tajo/vivienda al construir la ficha, así que
`antes=None` no debería darse nunca en una obra real ya sembrada — el
caso solo aparece con una ficha de prueba deliberadamente vacía. Pendiente
antes de la Fase 7 (cutover): decidir si el validador debe replicar la
guarda antigua explícitamente (más seguro, coherente con "no crear una
celda plausible en el sitio equivocado") o si basta con la garantía de
siembra ya existente.

**Cuando se reanude:** relanzar Fase 5 con instrucción de completar solo
lo que falta (comparación empírica PDF-vs-HTML de Bolueta + informe
final) sin repetir el módulo ni los tests ya hechos y verificados.

### Fase 4 — resultado destacado: la tesis central queda demostrada con datos reales

Investigación previa (obligatoria, con cita fichero:línea) confirmó que
`data-k` no pasa por `BASE_SOURCE_ID` al imprimirse — los tres ids cortos
que Gernika trataba como "excepciones" son exactamente los que
`BASE_SOURCE_ID` traduce, una tabla fija y ya existente, no una
heurística nueva. Para portal/planta encontró que hay DOS numeradores
históricos (`crear_registro_revision`, orden natural, vs
`registro_revision_desde_ficha`, orden de estructura) que pueden diverger;
la solución fue no elegir a ciegas — calcular ambos y solo resolver
automáticamente cuando coinciden, dejando el resto en avisos. Es la
decisión correcta y queda como limitación conocida para la Fase 7
(cutover de `generar_todos.py`): un HTML antiguo de una obra donde los
dos órdenes ya divergieron necesitará un mapa explícito.

**Verificación empírica contra Bolueta 24/08/2026 (solo lectura, sin
escribir nada, ficha "antes" leída con `git show` sin checkout):** el
camino HTML propone 443 cambios frente a la ficha previa. Las 411 celdas
que de verdad se aplicaron aquel día por el camino PDF (con sus 4 bugs
ya corregidos) están las 411 dentro de esas 443, **con 0 ausencias y 0
valores discrepantes**. Las 32 de más se explican con precisión por
historial de git: son estados que llegaron por otra vía entre dos
commits anteriores, no cambios de esa sesión — no es un fallo del
adaptador, es que el HTML expone el estado final completo, no solo el
delta de una sesión.

Esto confirma con datos reales, no solo con argumento arquitectónico, la
recomendación de la sección D: preferir el HTML gemelo sobre la
relectura de texto por geometría del PDF cuando ambos existan.

### Fase 3b — corrección: la vivienda NO va en minúsculas

Codex encontró en la Fase 3, con pruebas de paridad reales (no
teóricas), que `validar_revision._partes_clave()` exige la clave entera
en minúsculas, pero la ficha real guarda el segmento de vivienda con su
case original (`ficha_obra.py:497,693`: `clave =
f"{portal_id}__{planta_id}__{tajo}__{ubi_id}"`, sin `.lower()` sobre
`ubi_id`). Confirmado por Claude leyendo el código: portal/planta/tajo sí
son convencionalmente minúsculas ya en el catálogo y en los ids de
portal/planta; la vivienda no. Con la regla tal cual estaba: una clave
con vivienda en mayúscula se rechazaba entera, o si se forzaba a
minúsculas, creaba una clave paralela nueva dejando huérfana la
histórica — el patrón de "guarda compartida" que motiva este proyecto.

**Corrección (Fase 3b, alcance mínimo):** portal, planta y tajo siguen
exigiéndose en minúsculas; la vivienda conserva su forma tal cual la
declara la estructura de la ficha (case-sensitive, sin normalizar en el
validador). La resolución de existencia usa el id exacto tal como está
en `ficha['estructura']`, no una versión forzada a minúsculas.

---

## Resultado de la Fase 0 (ejecutada 25/08/2026, auditada por Claude)

Codex ejecutó la Fase 0 de forma autónoma (`codex exec`, sandbox
`workspace-write`, sin tocar nada salvo su entregable) y produjo
`_SISTEMA/docs/2026-08-25-auditoria-revisiones-fase0-codex.md`, con cita de
fichero:línea en cada afirmación. Confirma la arquitectura de este
documento sin desviaciones estructurales. Claude ha verificado por su
cuenta el hallazgo más relevante (punto 2 de abajo) antes de darlo por
bueno.

**Precisiones menores confirmadas:**
- `--preparar` (Flujo A) por sí solo no escribe la ficha; solo
  `--aplicar ... --escribir` lo hace.
- La skill `sagarde-revision` sí menciona el `.html` gemelo como señal
  para distinguir Flujo A de Flujo B, pero no documenta cómo se ingiere
  ese HTML (`lector_hoja_tajos_html`) — matiz sobre "no lo menciona".
- Adaptadores sin enganchar en `registro_obras.OBRAS`, confirmando la fila
  A07 del mapa mental: `adaptador_egurrola` y `adaptador_zorrozaure`.

**Dos hallazgos que cambian el peso de las fases 3-4 del plan:**

1. **Las dos vías no comparten ni siquiera la función de escritura celda a
   celda.** `ficha_obra.actualizar()` (la función que decide si un estado
   nuevo puede pisar uno guardado) solo la llama internamente
   `actualizar_desde_snapshot()` — la Vía 2. `leer_hoja_marcada.py` **no
   la llama en ningún punto** (verificado por Claude con grep,
   0 resultados): tiene su propia lógica de escritura de celda,
   independiente. No son dos entradas a una misma regla: son dos
   implementaciones de la misma regla que hoy no pueden divergir sin que
   nadie se entere. Esto refuerza — con evidencia adicional a la ya
   citada en la sección C — la prioridad de la Capa 5
   (`apply_revision()`): no es solo redirigir llamadas, es sustituir dos
   implementaciones independientes de la misma decisión por una sola.
2. **El camino HTML de Gernika (`parsear_html()`/`listar_revisiones_html()`)
   tiene cero tests directos**, pese a estar vivo en producción desde el
   25/07/2026. Antes de convertirlo en la vía preferente para Flujo B
   (como propone la sección D), la Fase 4 del plan debe empezar por
   escribirle cobertura de test — no heredar una ruta sin red de
   seguridad justo cuando se le va a dar más peso.

**Salud de la suite:** 445 tests ejecutados, 441 pasan, 0 fallos, 0
errores, 4 omitidos (los ya conocidos de Obispo Orueta archivada). Base
sana para construir encima con pruebas de paridad.

### Corrección de Bixente (25/08/2026): el evento real fue Bolueta, no Gernika

La revisión digital que sí se ha usado en producción (24/08/2026, la de
los 4 bugs) fue de **Bolueta**, no de Gernika. Verificado con grep:
`adaptador_bolueta.py` **no importa** `lector_hoja_tajos_html` ni tiene
ninguna referencia a `.html` — a diferencia de `adaptador_gernika.py`, que
sí lo hace. Esto cambia el diagnóstico, y lo empeora en un sentido
concreto:

**El `.html` gemelo que se generó junto al PDF de Bolueta ese día nunca
lo leyó nadie.** Solo se consumió el PDF, vía `leer_hoja_marcada.py
--digital` — exactamente el camino que tuvo que releer texto por
geometría y que produjo los 4 bugs documentados (tolerancia vertical,
unidades con espacio, sidecars contados como Documentos y, el más grave,
el agrupamiento de columnas que perdió el 40% de los cambios). El HTML
con `data-k`/`data-st` ya limpio, exacto y sin ambigüedad geométrica
estaba en el mismo directorio y no se tocó, porque **hoy solo
`adaptador_gernika.py` sabe leer ese formato — para cualquier otra obra,
incluida Bolueta, el HTML exportado es un fichero huérfano.**

Esto no debilita la recomendación de la sección D (preferir el HTML
cuando exista un gemelo); la refuerza con un incidente real: si el motor
hubiera podido leer el HTML de Bolueta ese día, el bug más caro de los
cuatro — el que perdió 166 de 411 cambios y que solo se detectó porque
Bixente comparó la hoja contra el panel a ojo — probablemente no habría
existido, porque es un bug específico de la extracción por geometría de
texto en PDF, no del formato HTML. La Fase 4 del plan (adaptador
HTML→normalizada) debe generalizarse desde el principio a **todas** las
obras, no solo a Gernika — hoy es la única que puede leerlo, pero es un
accidente de qué adaptador se escribió primero, no una limitación real
del formato.

---

## Fase 1 — Diseño: REVISION_NORMALIZADA y validador común

Diseño de Claude, pendiente de aprobación de Bixente. Nada de esto se
implementa todavía — es la Fase 1 de la tabla de la sección F. Construido
sobre lo confirmado en la Fase 0, reutilizando exactamente lo que ya
existe: la clave `portal__planta__tajo__vivienda`, el alfabeto de
`MAPA_ESTADO` (`ficha_obra.py:59-71`), `CATALOGO_TAJOS.json` y las reglas
ya escritas (blanco no baja, sin tinta no hay cambio, retroceso aceptado).

### `REVISION_NORMALIZADA` — una revisión completa

```python
{
  "revision_id": str,      # determinista: obra + fecha + origen + hash de fuente
  "obra": str,              # id de obra, tal cual registro_obras.py
  "fecha": str,              # DD/MM/AAAA — la de cabecera/generación, NUNCA inferida
  "origen": str,             # "tinta" | "pdf_digital" | "html_digital"
  "fuente": str,             # ruta del PDF/HTML/imagen origen
  "celdas": [REVISION_CELDA, ...],
  "metadata": {
    "generado_por": str,     # qué adaptador/skill la produjo
    "generado_en": str,      # timestamp ISO
    "avisos": [str, ...],    # no bloqueantes: "clave sin resolver", "hoja sin fecha"
  },
}
```

### `REVISION_CELDA` — un cambio propuesto

```python
{
  "clave": "portal__planta__tajo__vivienda",
  "estado_leido": "X" | "M" | "/" | "" | "N",   # alfabeto de la HOJA, no el de la ficha
  "confianza": "cierta" | "dudosa",               # solo se usa con origen="tinta"
}
```

**Decisión de diseño importante:** `estado_leido` usa el alfabeto de la
*hoja* (`X`/`M`/`/`/vacío/`N`), no el de la *ficha*
(`X`/`M`/`/`/`P`/`?`/`N`). Traducir un vacío a `P`, a `?`, o dejarlo tal
cual, depende del origen y del contexto — es una decisión de la Capa de
Validación, no del adaptador de lectura. Hoy cada camino decide esto por
su cuenta (`marcar_no_empezados` en tinta, "no tocar" en `--digital`); la
Fase 1 lo centraliza sin cambiar el comportamiento actual de ninguno de
los dos.

### Validador común (módulo nuevo, p.ej. `validar_revision.py`)

```
validar(revision: REVISION_NORMALIZADA, ficha_actual: dict, catalogo: dict) -> ValidationResult
```

Reutiliza, sin duplicar:
- `CATALOGO_TAJOS.json` para existencia de tajo, incluidos los propios de
  obra (`reglas/CATALOGO_TAJOS.json:852+`).
- La estructura de `ficha_actual` para existencia de portal/planta/vivienda.
- `MAPA_ESTADO` (`ficha_obra.py:59-71`) para el alfabeto válido.

Reglas que centraliza (todas ya escritas en el código hoy, repartidas —
ver Fase 0 sección 4):

1. La obra de la revisión coincide con la ficha que se le pasa.
2. La clave tiene el formato de 4 partes.
3. Portal, planta y vivienda existen en la estructura de la ficha.
4. El tajo existe en el catálogo para esa obra.
5. `estado_leido` es válido en el alfabeto de hoja.
6. Traducción `estado_leido` → estado a guardar, según origen:
   - vacío + origen `tinta` (hoja marcada como "usada") → `P`, si no había
     estado ya.
   - vacío + origen `pdf_digital`/`html_digital` → no se toca la celda
     (igual que hoy en `--digital`).
   - `N` → la celda se descarta, no se guarda.
7. Blanco nunca baja un estado conocido — solo un `P` explícito baja.
8. Un retroceso explícito (p.ej. `X`→`M`) se acepta a la primera.
9. Sin tinta no hay cambio: para origen `tinta`, una celda sin trazo
   asignado no debe llegar aquí — se filtra antes, en el adaptador.
10. La fecha no se infiere nunca: si falta, es error bloqueante.

Salida: celdas aceptadas, celdas rechazadas (con motivo), avisos no
bloqueantes, y un resumen antes/después por celda — para que el dry-run
imprima exactamente lo que hoy imprime `leer_hoja_marcada.py` sin
`--escribir`.

### `apply_revision()` — boceto para la Fase 3 (no se implementa aún)

```
apply_revision(revision: REVISION_NORMALIZADA, dry_run=True) -> AplicacionResult
```

- Llama al validador.
- Si `dry_run`, devuelve el resultado sin tocar disco (como hoy).
- Si no, aplica las celdas aceptadas sobre `ficha_obra.json` — única
  función de escritura, sustituye a `ficha_obra.actualizar()` y a la
  lógica propia de `leer_hoja_marcada.py` — guarda con
  `fichas.guardar()` y escribe el log de trazabilidad (Capa 6, Fase 8).

### Decisiones de diseño resueltas por paridad (no cambian nada de hoy)

Tres puntos que podían quedar ambiguos, resueltos con el mismo criterio
que gobierna toda la migración: no cambiar comportamiento todavía, solo
centralizar.

1. **¿Quién decide que una hoja de tinta está "usada" (para que un blanco
   ascienda a `P`)?** Hoy esa decisión ya la toma el lector, antes de
   llegar a ninguna validación (si hay anotaciones/trazos, la hoja
   "cuenta"). Se mantiene así: el adaptador que produce la
   `REVISION_NORMALIZADA` marca `metadata.avisos`/un flag
   `hoja_usada: bool`, y el validador solo aplica la regla 6 (vacío→`P`)
   cuando ese flag es cierto. El validador no decide esto por su cuenta.
2. **¿Debe el validador resolver las celdas "dudosas" de tinta?** No — eso
   ya lo resuelve el humano hoy, en la fase intermedia entre `--preparar`
   y `--aplicar` (mirando los recortes y escribiendo
   `.clasificacion.json`, incluso para marcar `descartada`). Cuando una
   `REVISION_NORMALIZADA` llega al validador, las dudosas ya están
   resueltas o descartadas — no es responsabilidad de esta capa.
3. **`revision_id` es determinista**, no aleatorio:
   `{obra}__{fecha}__{origen}__{hash8 de la fuente}`. Esto es lo que
   cierra el riesgo central de este proyecto: si la Vía skill y la Vía
   adaptadores procesan alguna vez la *misma* hoja (el caso Gernika +
   HTML que motivó esta auditoría), `apply_revision()` puede detectar que
   ese `revision_id` ya se aplicó y negarse a duplicar el cambio, en vez
   de que cada camino lo aplique por su lado sin saber del otro.

Si alguno de estos tres criterios no es el que quieres, dímelo antes de
que pase a generar el prompt de la Fase 2 para Codex (validador + tests,
sin tocar nada en producción todavía).
