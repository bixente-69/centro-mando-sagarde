---
name: sagarde-revision
description: Pasar una hoja de revisión de tajos (marcada en obra a boli, O rellenada en la app web del generador y exportada sin tinta) a la base de datos de esa obra (paso 4 del ciclo Sagarde), y dar de alta una obra nueva desde su hoja en blanco. Usar cuando Bixente entregue un PDF de revisión marcado a boli, con pen digital, o generado/rellenado desde la propia app del generador, y diga "pásame los datos al entorno SAGARDE", "sube esta revisión", "actualiza la obra con esta hoja", "he añadido/actualizado la revisión de <obra>", o cuando haya que registrar una obra nueva a partir de la hoja que genera el generador.
---

# Leer una hoja de revisión y meterla en la base

Cierra el paso 4 del ciclo: la hoja sale de la base, se marca en obra, se
escanea, **la IA la traduce**, y eso vuelve a la base.

## Antes de nada: ¿a boli o en el generador?

**Preguntarlo si no está claro, ANTES de tocar ninguna herramienta.** Hay dos
caminos completamente distintos y elegir el equivocado cuesta caro en tiempo
(el 24/08/2026, no preguntarlo costó media sesión entera para "algo tan
sencillo como actualizar una revisión"):

| Señal | Camino |
|---|---|
| Bixente dice "la marqué en obra", "hoja a boli/pen digital", o el PDF tiene trazos visibles al abrirlo | **Flujo A: tinta**, más abajo |
| Bixente dice "la rellené en el generador", "la actualicé desde la app", o el PDF viene **acompañado de un `.html` con el mismo nombre y la misma hora de creación** | **Flujo B: digital**, más abajo |

`--preparar` (Flujo A) dice "celdas con tinta: 0" en los dos casos de una
hoja sin usar Y en una hoja rellenada digitalmente — **no asumir "hoja sin
usar" solo por el recuento en 0**: mirar antes si hay un `.html` gemelo (ver
Flujo B) y si el propio PDF trae texto de estado ya impreso (X/M// más allá
de lo que ya había en la base).

## Por dentro: motor común y salvaguarda (desde el 26/08/2026)

Los comandos de abajo no han cambiado, pero por dentro `--aplicar --escribir`
y `--digital --escribir` ya no escriben la ficha directamente: construyen una
`REVISION_NORMALIZADA`, la validan (`validar_revision.py`) y la aplican
(`aplicar_revision.py`) — un único motor común para tinta, PDF digital e
HTML digital. Detalle completo del diseño y de cada fase verificada:
`_SISTEMA/docs/superpowers/specs/2026-08-25-unificacion-revisiones-design.md`.

Dos cosas que sí cambian lo que se ve en pantalla:

- **Antes de escribir, el CLI calcula el resultado dos veces** — por el
  camino antiguo y por el motor nuevo, de forma independiente — y compara
  celda a celda. Si coinciden, guarda y avisa `[SALVAGUARDA] ... coinciden
  exactamente en N celdas`. **Si no coinciden, no escribe nada** y aborta
  con `[ABORTADO]` listando cada clave con `antiguo=...; nuevo=...`. Esto
  no es un error a ignorar ni a reintentar sin más: es la red de seguridad
  del primer cutover real. Si aparece, es un caso para revisar con Claude o
  Codex, no para forzar.
- **En `--digital`, si junto al PDF hay un `.html` gemelo (mismo nombre,
  mismo minuto), el CLI lo prefiere automáticamente** y avisa `usando el
  HTML gemelo: <ruta>` — es más fiable que releer texto por geometría
  (verificado empíricamente: recupera sin fallos cambios que el PDF llegó a
  perder antes de corregir sus bugs). Si por lo que sea hace falta forzar la
  lectura del PDF aunque exista el HTML, usa `--forzar-pdf`.

Cada revisión aplicada de verdad queda además en
`{obra}/INFORME SAGARDE IA/revisiones_aplicadas.jsonl` (una línea por
revisión, con origen, fecha, celdas cambiadas/conservadas/descartadas y si
la salvaguarda coincidió) — es un añadido, no sustituye al sidecar
`.correcciones.json` ni a `ficha['revisiones']`, que siguen igual.

## La regla que gobierna todo esto

**El código pone la clave de la celda; la vista pone la letra.**

El error caro no es confundir una `X` con una `M`: es poner la marca en la
**fila o columna equivocada**, porque produce un dato plausible en el sitio
equivocado y nadie se entera. Por eso `portal__planta__tajo__vivienda` sale
siempre de la geometría de la rejilla, nunca de leer texto en orden.

## Herramientas

Todas en `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/`:

| fichero | para qué |
|---|---|
| `rejilla_hoja.py` | resuelve qué celda es cada posición. Común. **No reescribirla** |
| `alta_obra_desde_hoja.py` | da de alta una obra desde su hoja **en blanco** |
| `leer_hoja_marcada.py` | lee la tinta (`--preparar`/`--aplicar`) **o** el texto ya impreso de una hoja rellenada en el generador (`--digital`, con preferencia automática por el `.html` gemelo) y actualiza la ficha |
| `validar_revision.py` / `aplicar_revision.py` | motor común de validación y escritura, usado por dentro por los tres caminos. No hace falta llamarlos directamente |
| `adaptar_revision_tinta.py` / `adaptar_revision_pdf_digital.py` / `adaptar_revision_html.py` | traducen cada origen al formato común. Tampoco hace falta llamarlos directamente — los usa `leer_hoja_marcada.py` por dentro |

Sin dependencias nuevas: `pdfplumber`, `PyMuPDF`, `PIL`.

## Flujo A: hoja marcada a boli → base

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA"

# 1. Localiza la tinta, le pone su clave por geometría y recorta cada celda
python leer_hoja_marcada.py "<ruta/hoja.pdf>" <id_obra> --preparar

# 2. MIRAR los recortes de <hoja>.recortes/ y escribir <hoja>.clasificacion.json
#    {"celdas": {"p1__pb__tubeado__A": "X", ...}}
#    Valores: X · M · / · P · descartada

# 3. Simular (sin --escribir no toca nada), revisar el antes/después, y aplicar
python leer_hoja_marcada.py "<ruta/hoja.pdf>" <id_obra> \
    --aplicar "<hoja>.clasificacion.json" --fecha DD/MM/AAAA --escribir

# 4. Regenerar y comprobar que las demás obras no se mueven
python generar_todos.py --no-pdf
```

**Son dos fases a propósito.** Juntarlas borraría la frontera entre lo que
resuelve el código y lo que resuelve la vista.

## Flujo B: hoja rellenada en el generador (sin tinta) → base

Bixente marca los estados directamente en la app web del generador y
exporta PDF+HTML a la vez (mismo nombre, mismo minuto). No hay tinta que
buscar: el estado ya está impreso como texto. Un solo paso, sin fase visual:

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA"

# Simular primero (sin --escribir no toca nada)
python leer_hoja_marcada.py "<ruta/hoja.pdf>" <id_obra> --digital --fecha DD/MM/AAAA

# Revisar el antes/después del resumen y aplicar
python leer_hoja_marcada.py "<ruta/hoja.pdf>" <id_obra> --digital --fecha DD/MM/AAAA --escribir

# Regenerar y comprobar que las demás obras no se mueven
python generar_todos.py --no-pdf
```

**Decisión de Bixente (24/08/2026): una celda que sale en blanco en esta
lectura NO se toca.** A diferencia de la hoja de papel (donde Bixente ha
tenido la hoja entera delante y un blanco es "no ha empezado" → `P`), una
exportación digital no garantiza que él haya mirado esa celda. Solo se
aplican las que imprimen marca explícita (`X`/`M`//). No hay
`--sin-marca` en este flujo por eso mismo.

## Qué mirar en cada recorte (solo Flujo A)

| lo que se ve | qué es | valor |
|---|---|---|
| trazo negro fino sobre la celda | lo escrito a boli | `X`, `M` o `/` |
| **mancha blanca ancha** | corrector: tapa una marca impresa que ya no vale | `P` |
| blanco + negro encima | tapó lo viejo y escribió lo nuevo | manda el negro |
| un trozo de trazo que baja de la fila de arriba | rabo, no es marca | `descartada` |

El corrector **no es ruido ni un error**: es la técnica correcta de Bixente, y
tiene sentido justamente porque quien lee es la vista. Se distingue por color
y grosor: negro `[0,0,0]` de 1.5–3 px es boli; blanco `[1,1,1]` de 17–28 px es
corrector.

**El número de puntos del trazo delata el glifo pero NO clasifica**: una `/`
ronda 6-7 puntos, una `X` 10-19, una `M` 25-29. Sirve para contrastar lo que
has leído; usarlo para decidir es adivinar.

## Reglas que no se saltan

- **Sin tinta no hay cambio.** Clasificar una celda sin tinta aborta.
- **Nada se descarta solo.** Una celda con poca tinta sale como DUDOSA y hay
  que resolverla a mano, aunque sea marcándola `descartada`.
- **La fecha no se deduce de la hoja.** La de la cabecera es la de
  *generación*: la de Bolueta pone 25/07 y el fichero es del 26. Va en
  `--fecha`, y si Bixente no la dice, se pregunta.
- **Un retroceso vale igual que un avance.** Tachar una `X` y poner `M` es una
  marca explícita: se acepta a la primera.
- **Las casillas en blanco de una hoja usada pasan a `P`** (ese tajo no ha
  empezado), nunca a `?`. Solo asciende `?`→`P`: un blanco **jamás** baja una
  `X`, `M` o `/`. Con `--sin-marca desconocido` se desactiva, para una hoja
  que no cubra la obra entera.
- **Una hoja con 0 anotaciones y sin sidecar no es SIEMPRE "sin usar"**:
  puede ser eso, o puede ser una hoja del Flujo B (rellenada en el
  generador). Mirar si trae un `.html` gemelo antes de descartarla.
- **Reportar siempre el antes/después** y que las obras no implicadas no se
  mueven.

## Dar de alta una obra nueva

```bash
python alta_obra_desde_hoja.py "<hoja_en_blanco.pdf>" <id_obra> "<CARPETA>" --escribir
```

**Manda la hoja**: si trae 15 bloques, se registran 15. La herramienta se
planta si la hoja lleva marcas — leerlas es trabajo del otro camino. Después
hay que añadir la obra a `registro_obras.py` y darle un adaptador.

## Trampas ya pagadas

- **La palabra "PLANTA" se desborda** de una columna estrecha y contamina la
  vecina (`"APLANTA 1ª"`). El nombre de planta se busca por su forma, y cada
  columna se asigna a la planta cuyo rango x la contiene.
- **"REMATES EXTERIORES" contiene "EXT"**, el distintivo de propiedad: por
  texto se colaba como un tajo llamado "REMATES ERIORES". Las cabeceras de
  grupo se distinguen porque ocupan toda la anchura.
- **Los nombres no casan entre hojas.** Las de julio imprimen el nombre largo
  del catálogo y llaman "bloque" a lo que la ficha guarda como portal; Mungia
  imprime la vivienda por su alias (`A2` donde la ficha guarda `A`). Todo se
  resuelve por catálogo y alias, y si hay ambigüedad **se para**.
- **Un trazo no es una celda.** El de OBRA PRUEBA medía 300×253 px con 724
  puntos y cruzaba 51 celdas. La anotación dice dónde mirar; deciden los
  puntos.
- **El nombre del tajo puede imprimirse por encima del bbox de su fila**
  (Bolueta 24/08/2026: hasta 1pt). Ya corregido — `rejilla_hoja.py` usa
  `TOLERANCIA_VERTICAL_TEXTO = 1.2`, verificado sin diferencias contra las 7
  hojas ya leídas del sistema. Si una hoja NUEVA vuelve a fallar con "el
  tajo '' no está en el catálogo", es el mismo síntoma con un desbordamiento
  aún mayor: medirlo con `page.chars` antes de tocar la constante otra vez.
- **Una unidad con espacio en el nombre se duplicaba al regenerar** (Bolueta:
  "Local 1"/"Local 2", las únicas con espacio de toda la obra → aparecía
  "Local1" fantasma, 76 celdas de más). Ya corregido en `ficha_obra.py`
  (`_fold_unidad`). Si aparece "UBICACION NUEVA sin confirmar" para algo que
  Bixente jura que ya estaba confirmado, sospechar primero de un espacio o
  carácter especial en el nombre antes de aceptar el alta.
- **"Documentos" contaba los sidecars técnicos de `REVISIONES/_SISTEMA/`**
  como si Bixente pudiera abrirlos (JSON de candidatas/correcciones,
  `.recortes/`). Ya corregido en `lectores.listar_documentos` (ignora
  cualquier carpeta `_SISTEMA`, no solo `INFORME SAGARDE IA`). Si el
  recuento de Documentos de una obra parece disparatado, sospechar de esto
  antes de nada.
- **Agrupar columnas solo por la letra de vivienda ('A','B','C','D') las
  fundía entre plantas.** La hoja imprime dos plantas por página con las
  mismas letras repetidas; agrupar sin la planta hacía que la planta de la
  derecha de cada página perdiera sus marcas en silencio (166 de 411
  cambios, 40%, en Bolueta 24/08/2026 — encontrado DESPUÉS de dar la
  revisión por terminada, porque Bixente comparó la hoja contra el panel a
  ojo). Ya corregido: `_agrupar_por_columna()` agrupa por `(planta, viv)`.
  Si algo parecido reaparece, sospechar de cualquier agrupación que use
  solo una etiqueta que se repite entre plantas/portales.
- **Limpiar los restos de un `--preparar` que no se llega a aplicar.** Si se
  arranca por el Flujo A y a mitad de camino se descubre que en realidad es
  Flujo B (0 tinta real), borrar el `.candidatas.json` y el `.recortes/` que
  haya dejado el intento fallido — si no, quedan como ruido en
  `REVISIONES/_SISTEMA/` y cuentan de más en Documentos hasta el próximo
  fix.

## Cómo viene paginada la hoja (desde el 07/08/2026)

- **La página 1 es la portada**: cabecera y leyenda, sin tabla. `leer_pdf` la
  ignora sola porque baja de `CELDAS_MINIMAS`. No es un error ni una hoja
  perdida.
- **De la página 2 en adelante, una tabla completa por página**, cada una con
  su identificación y su cabecero de viviendas. Nunca hay dos tablas en una
  página: `leer_pdf` sólo lee `tablas[0]` y la segunda desaparecería.
- **Una tabla puede venir partida en varias hojas** cuando la obra tiene más
  tajos de los que caben (Orueta, 55). La identificación termina entonces en
  `· HOJA n DE N` y cada hoja repite las mismas columnas de vivienda con otro
  tramo de tajos. Cada una es una tabla completa: se leen igual, por separado.
- **Si aparece una página suelta con menos de 50 celdas que no sea la 1, hay
  un problema**: o es un resto de tabla que se está descartando en silencio, o
  es papel desperdiciado. Comprobarlo con `python verificar_hojas_pdf.py`.
- **Bixente puede haber omitido tajos** de la hoja a propósito (el generador se
  lo ofrece cuando no caben). Un tajo ausente **no es un tajo sin revisar**:
  conserva el estado que tuviera. Está garantizado por código —
  `marcar_no_empezados` sólo recorre las celdas impresas— pero conviene no
  alarmarse al ver menos tajos de los del catálogo.

## Tras cualquier --escribir: comprobar TODOS los consumidores, no solo la ficha

`generar_todos.py --no-pdf` y luego revisar que **ficha, prioridades,
dudas_pendientes, panel.html y el portal (`index.html`/`resumen_obras.json`)
llevan todos la misma fecha de revisión y el mismo desglose x/m/slash/vacío**
— no basta con que la ficha se haya escrito. Esto no es paranoia de más: el
24/08/2026 fue precisamente regenerar y mirar TODAS las obras (no solo
Bolueta) lo que destapó el duplicado de "Local1" y el ruido de Documentos,
ninguno de los dos visible si solo se hubiera mirado la ficha de Bolueta.

Comando rápido para el desglose de una obra:
```bash
python -c "import json; d=json.load(open('<obra>/INFORME SAGARDE IA/ficha_obra.json',encoding='utf-8')); from collections import Counter; print(Counter(v.get('v') for v in d['estados'].values()))"
```

Y comprobar que las obras NO implicadas no se mueven ni un decimal
(`git diff --stat` sobre sus `ficha_obra.json` debería ser solo la línea
`actualizado`, nada de `estados` ni `estructura`).

**Si Bixente señala UN dato concreto que no cuadra con la hoja, no lo
arregles solo a él.** Eso fue exactamente lo que pasó en Bolueta 24/08/2026:
señaló una celda, la causa real era sistemática (columnas agrupadas sin la
planta) y afectaba al 40% de los cambios de la hoja entera. Cuando el
síntoma apunte a un patrón que se repite, verificar el DOCUMENTO COMPLETO
con un método de lectura independiente del que falló — no la misma función,
un camino distinto que no pueda compartir el mismo sesgo (por ejemplo:
asignar cada glifo a la celda más cercana en 2D sobre todas las celdas a la
vez, en lugar de agrupar por columna primero). Si los dos métodos coinciden
al cien por cien, hay confianza real de que no queda nada suelto.

## Verificado contra verdad conocida

- **Bolueta 26/07/2026**: el lector reproduce exactamente las 7 celdas del
  sidecar transcrito a mano y descarta 5 rabos de trazo. Cero cambios.
- **Mungia 27/07/2026**: 225 celdas con tinta, 177 coinciden con el sidecar.
  Corrigió 2 marcas que estaban en la vivienda equivocada y 3 que el sidecar
  guardaba con la clave `PORT AL` partida.
- **OBRA PRUEBA**: obra ficticia para probar sin tocar datos reales.
- **Bolueta 24/08/2026 (Flujo B, primera vez usado)**: 411 celdas avanzaron
  de verdad en total (245 en la primera pasada, 166 más recuperadas del bug
  de columnas fundidas). `pct_ponderado` 41.7→53.6. Gernika, Mungia y
  OBRA PRUEBA comprobadas sin moverse, dos veces. Verificado también con un
  segundo método de lectura independiente sobre el documento completo:
  1963 glifos, 1963 celdas, 0 discrepancias. Detalle completo en la memoria
  `project_sagarde_hoja_generador_digital`.
- **26/08/2026, unificación del motor**: el mismo caso de Bolueta 24/08 se
  releyó por el camino HTML (antes nunca usado — el `.html` gemelo de esa
  revisión estaba huérfano) y coincidió con el PDF corregido en las 443
  celdas, sin ninguna discrepancia. Los tres caminos (tinta, PDF digital,
  HTML digital) y el camino de `generar_todos.py` se verificaron contra
  Bolueta, Mungia, Gernika y OBRA PRUEBA con 0 discrepancias en total.
  Detalle fase por fase en
  `_SISTEMA/docs/superpowers/specs/2026-08-25-unificacion-revisiones-design.md`.
