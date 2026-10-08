---
name: sagarde-actualizar-obra
description: Actualizar UNA obra concreta de Sagarde cuando Bixente entrega o ha dejado hojas de revisión nuevas (vivienda y/o garaje) y pide "actualiza la obra X". Aplica solo esa obra: ficha, panel, prioridades, informe ejecutivo PDF y su tarjeta en el índice. NO recorre el resto de obras. Usar siempre que la petición nombre una obra concreta; el recorrido de todas las obras solo si Bixente pide expresamente "todas las obras".
---

# Actualizar UNA obra (alcance cerrado)

Regla de Bixente (04/10/2026, textual en espíritu): **si pide actualizar una
obra, se toca solo esa obra y lo que de ella depende. Regenerar las demás
cuando no se ha revisado nada nuevo es un gasto absurdo de recursos y no
puede costar una hora de espera.** Solo "revisa/actualiza todas las obras"
autoriza el recorrido completo.

## Qué NO se hace (sin que lo pida)

- `generar_todos.py` (entero), ni siquiera con `--no-pdf`: ese flag no
  evita nada y regenera TODAS las obras, sus PDF y sus `revisiones_aplicadas.jsonl`.
- `Actualizar_Sagarde.bat` (hace `git add -A` y publica en `main`).
- `regenerar_obra.py --finalizar` sin pedir publicar: es el paso de
  agregación global (ver mapa). Barato, pero toca ficheros compartidos.
- Seguir la skill `sagarde-informe-ejecutivo` al pie de la letra: su
  sección 1 ("no hay atajo para una sola obra") quedó desmentida el
  04/10/2026 — `regenerar_obra.py <id>` ya arma bien garaje y zonas
  especiales y deja el PDF completo.
- `adaptar_revision_garaje.py` «para probar»: **no tiene modo simulación y
  escribe** (sobrescribe `ficha_garajes.json`; aunque el contenido salga igual,
  cambia la marca de hora).

## Mapa de impacto de una obra (medido el 04/10/2026 con Olabeaga)

**Por obra — carpeta `<obra>/INFORME SAGARDE IA/` y `<obra>/REVISIONES/`:**
`ficha_obra.json` (vivienda) · `ficha_garajes.json` (garaje) ·
`revisiones_aplicadas.jsonl` · sidecar `.correcciones.json` en
`REVISIONES/_SISTEMA/` · `memoria_obra.json` · `prioridades_trabajos.json`,
`_garaje.json`, `_zesp.json` · `dudas_pendientes.json` · `panel.html` ·
`INFORME_EJECUTIVO_<obra>.pdf`. Todo esto lo produce `regenerar_obra.py <id>`
solo. Medido: no se movió ningún fichero de otra obra.

**Globales (solo cambia la entrada/tarjeta de la obra tocada):**
`SAGARDE OBRAS ABIERTAS/index.html` (tarjeta de la obra + hora «actualizado»,
y el orden de tarjetas por último archivo) ·
`_SISTEMA INFORME SAGARDE IA/obras_revisiones.js` (registro que precarga la
app del generador: sin esto la próxima hoja en blanco sale sin los estados
nuevos) · `resumen_obras.json` (tarjeta del Portal; ignorado por git).
Los escribe `regenerar_obra.py --finalizar` leyendo `_cache_resultados_regen.json`
(ignorado por git; guarda el resultado de cada obra). Medido en el diff de
git: en `index.html` y `obras_revisiones.js` solo cambió Olabeaga.
**Por lectura de código, no medido**: `--finalizar` solo ejecuta
`generar_index`, `escribir_resumen_json` y `publicar_registro_revisiones`.

**Fuera del alcance** (no se actualizan nunca en esta tarea): paneles, PDF y
fichas de las demás obras; `informe_movil.pdf` (solo lo hace el generador
completo con PDF); el Centro de Mando de GitHub Pages (solo se publica con el
`.bat`, que lanza Bixente).

## Procedimiento

Siempre con `py -3.11` (el `python` por defecto de este PC no trae `reportlab`
y el PDF falla). Rutas: motor en `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`,
regenerador en `_SISTEMA/MOTOR/scripts/regenerar_obra.py` (raíz del repo).

1. **Estado del árbol.** `git status --short` y `git log --oneline -5`. Si hay
   cambios ajenos a esta obra, no son basura: es otra sesión; parar y avisar.
2. **Qué hojas hay nuevas.** Listar `<obra>/REVISIONES/`. Una hoja está
   aplicada si su fecha ya figura en `ficha_obra.json['revisiones']`
   (vivienda) o en `ficha_garajes.json['revisiones']` (garaje; id
   `rev_DDMMAAAA`). **`actualizado` NO sirve para esto: es la hora a la que se
   escribió el fichero, no la fecha de la hoja** (el 08/10/2026 una
   comprobación sobre `actualizado` hizo parar a un worker sin motivo). Una
   hoja con el mismo tamaño/contenido que otra ya aplicada (OneDrive la
   re-sincroniza con otra hora) no es nueva: `cmp` antes de aplicar. Sin hoja
   nueva → no hay nada que hacer: decirlo y parar.
3. **Vivienda (HTML del generador).** Simular y luego escribir:
   ```bash
   py -3.11 leer_hoja_marcada.py "<hoja.html>" <id_obra> --digital --fecha DD/MM/AAAA
   py -3.11 leer_hoja_marcada.py "<hoja.html>" <id_obra> --digital --fecha DD/MM/AAAA --escribir
   ```
   Con HTML sin PDF gemelo la salvaguarda geométrica se omite (lo dice); queda
   el motor común. Aviso `[ABORTADO]` → parar, no forzar. Hoja a boli → skill
   `sagarde-revision` (flujo A).

   > **REGLA DE ORO (Bixente, 04/10/2026, no negociable): leer BIEN la última hoja entregada e incorporar TODO lo que trae a la base de la obra, estructura incluida.** A veces una hoja nueva trae cambios de estructura (viviendas, plantas, portales generados después de la hoja anterior). Lo que la hoja trae manda; lo que la base no recoge se pierde y no se puede volver atrás. Por eso, en la **simulación** hay que leer entera la salida y comprobar:
   > - **`ESTRUCTURA NUEVA EN LA HOJA`**: lista las viviendas nuevas que se incorporan a la base (solo se añade, nunca se quita). Contrastarlas con lo que Bixente haya dicho de la obra; si algo no cuadra, preguntar antes de escribir.
   > - **`[MARCA SIN APLICAR]`**: una marca de la hoja que la base no sabe colocar. Con `--escribir` el lector **aborta**. NO se usa `--permitir-marcas-sin-aplicar` para saltarse el aborto: se resuelve la causa (estructura, tajo) y se vuelve a simular. Cero marcas sin aplicar es la única salida aceptable.
   > - **«casillas en blanco -> tajo no empezado (P)»**: un blanco en una hoja entregada NO es «sin revisar»: significa que ese tajo no ha empezado o que esa ubicación aún no existe. Pasa a `P`; nunca baja una `X`, `M` o `/`. Con `--sin-marca desconocido` se dejan como estaban, solo si la hoja no cubre toda la obra.
   > - **`ESTRUCTURA QUE YA NO ESTA EN LA HOJA`**: la última hoja manda también para **quitar**. Lo que la hoja ya no trae (una vivienda que desaparece, un tajo que no imprime para una unidad) se retira de la base y deja una exclusión para que ninguna regeneración lo resucite; la copia anterior queda en git y en un `ficha_obra.json.antes_hoja_*.bak`. Se retira todo o nada: si lo retirado guarda avance (`X`/`M`/`/`) el lector aborta y es una decisión de obra que se confirma con Bixente. Contrastar la lista con lo que él diga de la obra. **Las marcas de la hoja se leen con la estructura de antes de retirar** (las hojas numeran las plantas por posición; borrar una planta correría la numeración y pasaría marcas a la planta de al lado): por eso una planta que queda vacía se conserva marcada como retirada. Señal de alarma: si tras escribir, una segunda simulación de la misma hoja no da 0 cambios, algo está mal alineado; no seguir.
   > - Después de escribir, comprobar con una comparación completa (todas las ubicaciones y tajos que imprime la hoja frente a la base) que **no queda nada de la hoja sin reflejar**, y que el registro del generador (`obras_revisiones.js`) saca la estructura nueva para la próxima hoja.
4. **Garaje (HTML).** Solo si la fecha no está aplicada ya (no hay simulación):
   `py -3.11 adaptar_revision_garaje.py "<hoja_garaje.html>" <id_obra> --fecha DD/MM/AAAA`
   Comprobar después que `ficha_garajes.json['revisiones'][-1]['fecha']` es la
   de la hoja (no `actualizado`).
5. **Regenerar solo esa obra** (panel, prioridades, PDF ejecutivo):
   ```bash
   py -3.11 _SISTEMA/MOTOR/scripts/regenerar_obra.py <id_obra>
   ```
6. **Agregados globales** (tarjeta del índice + registro del generador):
   `py -3.11 _SISTEMA/MOTOR/scripts/regenerar_obra.py --finalizar`
   Es lo único que sale del perímetro de la obra; hacerlo y decirlo.
   **Inmediatamente después, SIEMPRE (parche hasta que `--finalizar` se
   arregle de raíz; pasó el 05/10 y el 08/10/2026):**
   `py -3.11 _SISTEMA/MOTOR/scripts/restaurar_tarjetas_index.py "<obra 1 tocada>" "<obra 2 tocada>"`
   (nombre oficial de la carpeta de cada obra actualizada). Deja la tarjeta
   nueva solo de esas obras y devuelve las demás a `HEAD`. Es idempotente. Si ya
   se arregló `--finalizar` (mirar «Trampas ya vistas»), no hace falta.
7. **Verificar** (un `exit 0` no certifica nada):
   - PDF con PyMuPDF: páginas = 1 resumen + 1 por portal (si ≥2) + 1 garaje
     (si hay `ficha_garajes.json` con zonas) + 1 zonas especiales (si hay
     celdas `zesp`). Olabeaga: 6. Menos páginas = algo se omitió en silencio.
   - `git status --short`: solo ficheros de esta obra + los 2-3 globales del
     mapa. Cualquier otra obra en la lista → investigar, no restaurar a ciegas.
   - Suite: `py -3.11 -m unittest discover -s tests` desde la carpeta del motor.
8. **Reportar antes/después** del desglose `x / m / / / vacío / N` y de los %
   (estricto y ponderado) de la obra, y de qué ficheros cambiaron. No commitear
   ni publicar salvo que Bixente lo pida.

## Cuando Bixente pide un informe de una obra («genérame el informe técnico/ejecutivo de X»)

Objetivo suyo (04/10/2026): tras actualizar la obra, el informe que pida sale
**ya actualizado**, sin que tenga que acordarse de regenerar nada.

1. Comprobar frescura: la fecha de datos del PDF
   (`<obra>/INFORME SAGARDE IA/INFORME_EJECUTIVO_*.pdf`, cabecera «Datos: DD/MM/AAAA»)
   debe ser igual a la última revisión real de la obra (`ficha_obra.json['revisiones'][-1]`
   o la fecha de `ficha_garajes.json`, la más reciente). Si es anterior, o hay una hoja
   sin aplicar en `REVISIONES/`, aplicar y regenerar con los pasos 2-5 de arriba
   (solo esa obra) ANTES de entregar.
2. «Informe técnico/ejecutivo» = el PDF `INFORME_EJECUTIVO_*.pdf` (el que se genera
   con los datos). El `INFORME_TECNICO_OBRA_<obra>.md` es un documento fijo de
   proyecto (memoria REBT, planos): no depende de revisiones y se rehace a mano.
3. `informe_movil.pdf` no se regenera en este flujo (queda desfasado); no entregarlo
   como actualizado. El «informe a la carta» sale del panel ya regenerado.
4. Al entregar, decir la fecha de datos del PDF.

## Trampas ya vistas

- **`--finalizar` puede degradar las tarjetas de OTRAS obras (05/10/2026).** Reconstruye
  `index.html` y `resumen_obras.json` desde `_cache_resultados_regen.json`, que solo se
  refresca para la obra regenerada: las demás entradas pueden estar desfasadas. Con Olabeaga
  dejó Mungia en 83.8 % / 28 revisiones / última 04/09 (real: 85.5 % / 29 / 10/09) y OBRA
  PRUEBA en 5.9 % (real 14.2 %). La afirmación de arriba «solo cambió Olabeaga» se midió el
  04/10 con la caché al día; **no es una garantía**. Tras `--finalizar`, comparar el diff de
  `index.html` tarjeta a tarjeta: solo debe cambiar la obra tocada (y lo que sea real en
  disco: obras nuevas, hora de «último archivo»). Si otra tarjeta retrocede, restaurar esa
  tarjeta desde `git show HEAD:` y avisar; `resumen_obras.json` (ignorado por git) queda
  igualmente desfasado hasta la próxima actualización completa.

- **Repetido el 08/10/2026 (Olabeaga+Bolueta+Barakaldo): `--finalizar` volvió a degradar
  Mungia (85,5→83,8 %), OBRA PRUEBA (14,2→5,9 %) y Gernika (93,3→92,9 %, una revisión
  menos).** Es un FALLO DE PROGRAMACIÓN (la caché solo se refresca para la obra que se
  regenera), no un asunto de datos. Mientras no se arregle de raíz (tarea pendiente
  abierta el 08/10/2026), el paso 6 incluye `restaurar_tarjetas_index.py`. Cuando se
  arregle, borrar este aviso y ese paso. `resumen_obras.json` (ignorado por git) queda
  desfasado para las obras no tocadas hasta la próxima actualización completa; solo lo
  usa el Portal móvil, y el `.bat` lo rehace.
- **El «AVISO CUTOVER FICHA ... difieren en N clave(s)» es ruido conocido, no un fallo.**
  Sale siempre en las obras con ficha nativa y sin adaptador histórico (Olabeaga: 1.225
  claves; Barakaldo: 3.286): el camino antiguo rellena celdas fantasma con todos los
  tajos en todas las unidades; la salvaguarda bloquea esa escritura y la ficha no se
  toca (comprobado por SHA). No perder tiempo investigándolo; sí si N cambia mucho.
- **Avisos de «recorte visible» / «excede la altura» del PDF ejecutivo** (Olabeaga,
  Barakaldo, Bolueta): el PDF se genera igualmente y las tablas declaran lo omitido
  con «+N más». Verificar páginas y la cabecera «Datos: DD/MM/AAAA», no alarmarse.
- **Tras un alta nativa, regenerar la obra ENSEGUIDA** (`regenerar_obra.py <id>`): la
  prueba `test_priorizador_garaje::test_todas_las_obras_registradas_conservan_sus_bytes`
  compara `prioridades_trabajos.json` de cada obra registrada con lo recalculado, y
  falla para una obra recién dada de alta hasta que se regenera. No es un bug.
- **Repartir con workers (Codex/agy) — lo aprendido el 08/10/2026:** (1) las comprobaciones
  que se les piden deben ser comprobables: un criterio equivocado (p. ej. `actualizado`)
  los hace parar a media tarea; (2) un worker puede dar «OK» con 0 errores y haber dejado
  celdas fantasma o desactivada una guarda: la verificación independiente (celdas de la
  ficha frente a las que imprime la hoja, simulaciones con y sin el cambio) es de Claude;
  (3) Codex puede quedarse sin cuota a mitad: leer `git status`/`git diff` de lo que dejó,
  ejecutar las pruebas uno mismo (`py -3.11 -m unittest discover -s tests` desde el
  motor; los módulos sueltos solo funcionan con `discover -s tests -p "..."`, no con
  `tests.modulo`) y rematar.
- **Obra «sin medir» que pasa a medida**: mientras TODA la obra está en `?`,
  `generar_todos.py` presenta `?` como pendiente en el PDF; con la primera
  hoja real esa vista se apagaba y desaparecía la página de Zonas Especiales
  (corregido el 04/10/2026, `snapshot_zonas_especiales_para_informe`). Si tras
  una primera revisión falta una página del PDF, buscar aquí.
- El % de una obra ignora las celdas `?` (no medidas): 30 celdas medidas
  pueden mover el % de golpe. Es esperable, no un error.
- Las cifras de referencia de `CLAUDE.md` (Mungia 79.8, Gernika 76.3, Bolueta
  41.7, Orueta 80.0) están desfasadas; la comprobación válida es que los
  `ficha_obra.json` de las demás obras no cambian (mismo SHA-256 antes y después).
- Hacer la actualización de una obra no es motivo para ejecutar `git checkout --`
  ni `git restore` sobre otros ficheros: preservar y preguntar.
- **Olabeaga 04/10/2026: la hoja traía la vivienda C en las 4 plantas del portal 3 y la base solo A y B.** 5 marcas (tabicado, suelo radiante, recrecido) y 148 casillas se perdieron sin aviso, y 1.411 celdas quedaron en `?` («sin revisar nunca») en vez de `P`, de modo que las rozas de timbres no se ofrecían ni con el tabique hecho. Ya está corregido en el lector (`ESTRUCTURA NUEVA EN LA HOJA`, aborto por `[MARCA SIN APLICAR]`, blanco → `P`); no relajar esas guardas.
