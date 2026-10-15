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

## PROCEDIMIENTO RÁPIDO (desde el 09/10/2026) — usar SIEMPRE este primero

Bixente tardaba ~40 min por actualización (queja textual del 09/10: «30 cambios como
mucho en una tabla ya generada»). Todo lo determinista está en UN comando, ~25-60 s
de reloj. **No hace falta Codex ni agy para actualizar datos** (cada ronda con un worker
costaba 3-4 min de arranque y verificación); basta esto, desde la raíz del repo:

```bash
py -3.11 _SISTEMA/MOTOR/scripts/actualizar_obra.py <id_obra>             # SIMULA: no escribe
py -3.11 _SISTEMA/MOTOR/scripts/actualizar_obra.py <id_obra> --escribir  # aplica
```

1. **Simular** y leer el resumen (hojas detectadas, cambios, transiciones). Códigos de
   salida: `0` todo bien · `2` error o verificación fallida · `3` **requiere revisión
   humana** (estructura nueva, estructura que la hoja ya no trae, `[MARCA SIN APLICAR]`,
   claves sin resolver, hoja anormal: >400 cambios medidos o >15 % de las celdas con
   marca; las casillas en blanco→`P` NO cuentan): leer la sección entera, contrastar con
   lo que diga Bixente y, si procede, repetir con `--aceptar-estructura` (estructura) o
   `--aceptar-hoja-grande N` (hoja anormal; `N` = el nº de «cambios medidos» que dice la
   propia guarda, tras leer la lista de transiciones antes→después; con otra cifra la
   guarda sigue). Las marcas sin aplicar NUNCA se saltan. Si dice que no hay
   hojas nuevas: es verdad (compara fechas de `revisiones`, no `actualizado`, y
   descarta copias idénticas que OneDrive re-sincroniza); no hay nada que hacer.
2. **Aplicar** con `--escribir`. Hace: vivienda → re-simulación que debe dar 0 cambios →
   garaje (una vez) → `regenerar_obra.py <id>` (con un reintento si la captura sale
   vacía) → `--finalizar` (que ya solo toca la tarjeta de esa obra) → informe.
3. **Leer el INFORME DE VERIFICACIÓN** (se guarda en `_SISTEMA/MOTOR/logs/`): debe acabar
   en `G) OK`. Mirar: A) antes/después x/m/slash/P/N y %; B) SHA de las demás obras
   `IDENTICO`; C) PDF con las páginas esperadas y «Datos» = última revisión; D) ninguna
   tarjeta ajena cambiada; **E) AVISO informativo: celdas que BAJAN de avance o pasan a
   `N`** (ya aplicadas: la última revisión manda); F) tiempos. **E NO es una pregunta:**
   Bixente (15/10/2026, harto de repetirlo): «la última revisión manda… está bien el aviso
   para tener en cuenta que se ha visto el cambio, pero no hace falta preguntar: se
   cambia y punto». Se las cuento en el informe como dato, sin pedir confirmación, sin
   «pendiente de tu OK» ni «a confirmar».
4. Reportar a Bixente el antes/después (A) y, como aviso, la lista E. **No commitear ni
   publicar** salvo que lo pida (publicar = su `Actualizar_Sagarde.bat`). La suite
   completa NO hace falta si no se ha tocado código (tarda ~2 min y regenera PDFs de
   Mungia).

Lo que sigue es el procedimiento manual: úsalo solo como referencia o si el comando falla.

## Procedimiento manual (referencia / plan B)

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
   Desde el 09/10/2026 `--finalizar` **solo cambia la tarjeta y la entrada de
   `resumen_obras.json` de las obras regeneradas desde el último finalizar**
   (las marca `regenerar_obra.py <id>` en `_pendientes_finalizar` de la caché) y
   conserva literalmente las de las demás. Imprime `Tarjetas actualizadas: ...` y
   `Tarjetas conservadas: ...`: comprobar que «actualizadas» son exactamente las
   obras que se acaban de regenerar. Sin ninguna pendiente dice «Nada pendiente:
   se conservan todas las tarjetas». Ya no hace falta ningún parche.
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

- **RESUELTO el 09/10/2026: `--finalizar` ya no degrada las tarjetas de OTRAS obras.**
  Pasó el 05/10, el 08/10 y el 09/10: reconstruía `index.html` y `resumen_obras.json`
  desde `_cache_resultados_regen.json`, cuya entrada de cada obra solo se refrescaba al
  regenerar ESA obra (Mungia salió con 83,8 % en vez de 85,5 %, OBRA PRUEBA con 5,9 % en
  vez de 14,2 %, Gernika con una revisión menos). Ahora `regenerar_obra.py` apunta las
  obras regeneradas en `_pendientes_finalizar` y `finalizar()` fusiona: tarjeta nueva solo
  para esas, el resto literal (también en `resumen_obras.json`, que antes quedaba
  desfasado). 6 pruebas en `tests/test_regenerar_obra_finalizar.py` y prueba real el
  09/10 (regenerar Bolueta + finalizar: «actualizadas: Bolueta», las demás idénticas).
  Si alguna vez una tarjeta ajena vuelve a retroceder, es un fallo nuevo: parar y
  avisar, no restaurar a ciegas. Se retiró el parche `restaurar_tarjetas_index.py`.
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
  (2b) A veces la captura de `regenerar_obra.py` le llega VACÍA a Codex (09/10/2026): el
  script sí terminó (PDF y panel escritos) pero no puede certificar KPIs, así que se
  para con razón; repetir `regenerar_obra.py <id>` uno mismo (es idempotente) y seguir
  con `--finalizar`; (2c) en la lista de ficheros «esperados» del encargo a Codex hay que
  incluir el `.correcciones.json` de `REVISIONES/_SISTEMA/` que genera la propia
  actualización, o se para (pasó el 09/10/2026);
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
- **Olabeaga 15/10/2026: «(DPX)» en la etiqueta de una unidad = vivienda dúplex, NO unidad nueva.** Bixente (textual): «las unidades dpx se han renombrado para saber cuáles son las viviendas que son dúplex, tienen escaleras en su interior a una planta superior con más habitaciones que el resto». La hoja del 14/10 traía `A (DPX)` (P1, 4ª) y `B (DPX)`, `C (DPX)` (P3, 4ª) con los mismos estados que A/B/C de la hoja anterior. Leídas como unidad nueva habrían creado 111 celdas fantasma (103 pasadas a `P`) y dejado las originales huérfanas. Solución: declarar el renombre en `estructura.alias_historico` de la ficha (`"p1__4__A": "A (DPX)"`, `"p3__4__B": "B (DPX)"`, `"p3__4__C": "C (DPX)"`); el lector y el generador ya lo entienden. Señal para detectarlo: la simulación pide «ESTRUCTURA NUEVA» con una unidad cuya etiqueta es `<id> (algo)` y la base ya tiene `<id>` en esa planta; comparar los estados de la hoja anterior.
- **RESUELTO el 15/10/2026: las zonas especiales nuevas o recreadas se dan de alta desde la hoja.** Antes `ampliar_estructura_desde_hoja` saltaba `planta_id == zesp` y `estructura_nueva_en_hoja` las excluía: la hoja traía «36 clave(s) sin resolver», la estructura no entraba y la zona antigua no se podía retirar (la baja exige que TODA clave se resuelva). Ahora `lector_hoja_tajos_html.extraer_zonas_especiales` lee lo que la hoja DECLARA (tipo = `data-zone-category`; nombre = `<strong>` de la `.tecnico-card` o cabecera `th.th-floor` de la tabla de los cuartos ligeros; solo biblioteca estándar), `estructura_nueva_en_hoja` las propone y `ampliar_estructura_desde_hoja` las da de alta (`origen: "hoja digital"`, `confirmado`, `visto_en`, celdas `?` solo de los tajos que la hoja imprime; la zona nueva se coloca tras la última del mismo tipo sin barajar las demás). Una zona recreada con otro id sigue el camino de retirada de siempre (exclusión; si la antigua guarda X/M// no se retira nada y `--escribir` aborta: decisión de Bixente). Lo que la hoja declara pero la base no acepta (sin nombre, tipo no admitido, nombre/tipo contradictorios) sale como `[NO INCORPORADA] ... motivo` dentro de la sección «ESTRUCTURA NUEVA»; las celdas `zesp` sueltas, fuera de una zona declarada, siguen siendo claves sin resolver. Comprobado con la hoja real de Olabeaga del 14/10: reproduce el alta manual del plan B (mismas 2 zonas con igual tipo/nombre y las mismas 36 celdas; solo difiere `visto_en`) y retira la RITI antigua. 22 pruebas en `tests/test_zonas_especiales_desde_hoja.py`. Ya no hay que añadirlas a mano.
- **RESUELTO el 15/10/2026: la guarda `hoja_anormal` de `actualizar_obra.py` ya no bloquea sin salida.** Contaba las casillas en blanco→`P` como «cambios» y las medía contra las celdas con marca (peras con manzanas): en una obra joven casi todo son blancos que pasan a `P`, y 97 cambios sobre 153 marcas (Olabeaga, 14/10) bloqueaban una hoja correcta sin salida posible. Ahora cuenta solo los «cambios medidos» (cambios − blancos→P) frente al tope de 400 y al 15 % de las celdas con marca. Si aun así salta, la propia guarda lista las transiciones antes→después y dice la salida: `--aceptar-hoja-grande N` con `N` = esos cambios medidos (con otra cifra la guarda sigue; repetible; no salta ninguna otra guarda). En una obra joven eso seguirá pasando con hojas legítimas (Olabeaga 14/10: 61 cambios medidos de 153 marcas = 39,9 %, tras restar 36 `?→P`; se habría liberado con `--aceptar-hoja-grande 61`): es lo esperado, no un fallo; el criterio no intenta distinguir progreso real de hoja rara, solo obliga a mirar la lista antes de escribir. El informe de verificación deja escrita la lista de transiciones aceptadas. El plan B manual queda solo como último recurso.
