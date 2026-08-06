---
name: sagarde-revision
description: Pasar una hoja de revisión de tajos marcada en obra a la base de datos de esa obra (paso 4 del ciclo Sagarde), y dar de alta una obra nueva desde su hoja en blanco. Usar cuando Bixente entregue un PDF de revisión marcado a boli o con pen digital y diga "pásame los datos al entorno SAGARDE", "sube esta revisión", "actualiza la obra con esta hoja", o cuando haya que registrar una obra nueva a partir de la hoja que genera el generador.
---

# Leer una hoja de revisión y meterla en la base

Cierra el paso 4 del ciclo: la hoja sale de la base, se marca en obra, se
escanea, **la IA la traduce**, y eso vuelve a la base.

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
| `leer_hoja_marcada.py` | lee la tinta de una hoja **marcada** y actualiza la ficha |

Sin dependencias nuevas: `pdfplumber`, `PyMuPDF`, `PIL`.

## Flujo: hoja marcada → base

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

## Qué mirar en cada recorte

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
- **Una hoja con 0 anotaciones y sin sidecar no es una revisión**: es una hoja
  impresa y no usada. Comprobarlo antes de nada.
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

## Verificado contra verdad conocida

- **Bolueta 26/07/2026**: el lector reproduce exactamente las 7 celdas del
  sidecar transcrito a mano y descarta 5 rabos de trazo. Cero cambios.
- **Mungia 27/07/2026**: 225 celdas con tinta, 177 coinciden con el sidecar.
  Corrigió 2 marcas que estaban en la vivienda equivocada y 3 que el sidecar
  guardaba con la clave `PORT AL` partida.
- **OBRA PRUEBA**: obra ficticia para probar sin tocar datos reales.
