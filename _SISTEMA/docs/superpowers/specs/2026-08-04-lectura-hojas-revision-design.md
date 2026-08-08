# Leer la hoja marcada en obra y meterla en la base

Diseño acordado con Bixente el 04/08/2026. Cierra el **paso 4** del ciclo que
él llama el fin del entorno Sagarde: la hoja sale de la base, se marca en obra,
se escanea, **la IA la traduce**, y eso vuelve a la base.

Los pasos 1, 2, 3 y 5 ya funcionan. Este documento sólo cubre el 4.

---

## 1. Qué pide Bixente, con sus palabras

> *"El generador me genera una revisión con las notas en las cuadrículas tal
> cual estaba en la última revisión. Yo cojo esa hoja generada, que es la
> última que hemos hecho, con todos los datos ya apuntados sobre ella y a pie
> de campo compruebo los avances marcando los nuevos, o incluso si ha habido un
> retroceso. Yo vendré a la IA, esta u otra de las que uso normalmente, y le
> diré: pásame los datos al entorno SAGARDE, y tiene que añadir los cambios a
> la base de datos de la obra que le corresponda con fecha nueva, la del día
> que se ejecute la revisión."*

Tres cosas que se derivan de ahí y gobiernan el diseño:

1. **La hoja de partida la genera el sistema.** No es un papel cualquiera:
   sabemos exactamente qué imprimimos en cada celda.
2. **Lo único nuevo es lo que él escribe encima.** Todo lo demás ya está en la
   base.
3. **Un retroceso vale igual que un avance.** Si tacha una `X` y escribe `M`,
   es una marca explícita, y la norma de obra ya dice que se acepta a la
   primera.

## 2. La idea central

> **Como la hoja se genera desde la base, ya sabemos qué había impreso en cada
> celda. Lo único que hay que leer es la diferencia.**

Esto no es un detalle de implementación, es lo que hace el problema abordable:

- No hay que leer 2.300 celdas. Hay que encontrar las ~200 con tinta encima.
- **Sin tinta no hay cambio.** Una celda sin trazo conserva lo que tenía. Es la
  misma regla que se implementó el 04/08/2026 para las casillas en blanco.
- Cada cambio queda **justificado por un recorte** que Bixente puede mirar.

## 3. Reparto de trabajo: geometría vs. visión

El error caro en este proyecto es el silencioso. En una lectura por visión, el
error caro es **atribuir una marca a la fila o columna equivocada**: produce un
dato plausible, en el sitio equivocado, y nadie se entera.

Por eso el trabajo se parte así:

| Lo resuelve el código (no falla) | Lo resuelve la IA (falible) |
|---|---|
| De qué obra es la hoja | Qué letra hay en este recorte |
| Qué celda es cada posición | |
| Qué había impreso antes | |
| Qué ha cambiado | |
| Qué fecha lleva la revisión | |

**La clave `portal__planta__tajo__vivienda` sale siempre de la geometría, nunca
de la vista.** La IA recibe un recorte de un centímetro con su clave ya
resuelta y sólo dice: `X`, `M`, `/`, `tachado` o `no lo veo claro`.

## 4. Cómo se localiza la tinta

Dos caminos según cómo haya marcado ese día. Ambos desembocan en lo mismo: un
conjunto de celdas con tinta y su recorte.

### 4.1 Pen digital

Las marcas viven **dentro del PDF como anotaciones, con coordenadas**.
Verificado el 04/08/2026:

| PDF | anotaciones |
|---|---|
| `REVISION MUNGIA 27072026.pdf` (usada) | **56** |
| `REVISION MUNGIA 28072026.pdf` (sin usar) | **0** |

**Aviso medido:** las 56 anotaciones no son 56 celdas. Sus cajas son gruesas —
una llega a medir 420 px de ancho— y un solo trazo cruza varias celdas. La
anotación sirve para saber **dónde mirar**, no para decidir qué celda es.

Para tinta exacta: renderizar la página **con** y **sin** anotaciones y restar.

### 4.2 Escaneo de papel

Aquí está la ventaja de generar nosotros la hoja: **se reimprime la hoja limpia
y se resta del escaneo**. Lo que sobra es el boli. Requiere alinear las dos
imágenes antes de restar.

El **corrector blanco** entra solo por este camino: aparece como una zona que
*perdió* tinta impresa respecto a la hoja limpia. Es una señal legítima, no un
error — significa "esta marca ya no vale".

### 4.3 La rejilla

`pdfplumber.find_tables()` da las celdas con sus coordenadas: **414 celdas en
una sola página** de Mungia. La rejilla es dato exacto, no hay que deducirla.

## 5. La fecha

Textual de Bixente: *"la del día de la revisión, te la doy yo o te la escribo
encima de la antigua, para que sepas cuál es"*.

Orden de resolución, y **nunca se inventa**:

1. Si la dice al pedirlo, esa.
2. Si hay tinta sobre el campo de fecha de la cabecera, se lee de ahí.
3. Si no, **se pregunta**.

## 6. El flujo completo

Bixente dice *"pásame los datos al entorno SAGARDE"* con el fichero.

| | quién | qué |
|---|---|---|
| 1 | código | Identifica la obra por la cabecera y carga su `ficha_obra.json` |
| 2 | código | Reconstruye qué se imprimió, desde la base |
| 3 | código | Localiza la tinta (§4.1 o §4.2) |
| 4 | código | Cruza tinta con rejilla → celdas candidatas **con su clave** |
| 5 | código | Recorta esas celdas y las numera |
| 6 | **IA** | Clasifica cada recorte |
| 7 | código | Contrasta con lo impreso, escribe la revisión y separa las dudas |
| 8 | código | Regenera la obra y reporta el antes/después |

## 7. Barreras contra inventar datos

- **Sin tinta, no hay cambio.**
- **Lo dudoso no entra**: va a la lista con su recorte.
- **La fecha no se inventa** (§5).
- **La obra no se adivina**: si la cabecera no se lee, se pregunta.
- **Se reporta el antes/después** de los recuentos `x` / `m` / `/` / vacío.

## 8. Dónde vive

**Una skill dentro del repositorio**, no en la carpeta personal de una IA.
Bixente usa Claude, Codex y Gemini indistintamente y dijo *"esta u otra de las
que uso normalmente"*.

**Hallazgo del 04/08/2026:** el `CLAUDE.md` del proyecto ya menciona una skill
local `sagarde-revision` que **no existe** en `.claude/skills/` — allí sólo está
`generate-cardiva-report`. Otro caso de algo declarado que nadie lee. Esta skill
tapa ese hueco.

## 9. Cómo se verifica

### 9.1 La obra de prueba (idea de Bixente, es la buena)

Se da de alta una obra ficticia, **`OBRA PRUEBA`**, en el entorno:

1. Se declara su estructura — la obra ficticia sirve para fijar la
   distribución sin tocar datos reales.
2. Se genera con el generador una **primera revisión** que resuelve esa
   distribución.
3. Se fabrica una **segunda revisión con cambios conocidos**.
4. Se pasa el lector y se comprueba que encuentra **exactamente** esos cambios:
   ni uno más, ni uno menos.

**Por qué es mejor que probar contra una obra real:** controlamos las dos
revisiones, así que la respuesta correcta se conoce de antemano y al dedillo.
Y no se toca ninguna obra de verdad.

### 9.2 Contraste con tinta real

La obra de prueba valida la lógica, pero su tinta será sintética. Para la tinta
de verdad está `REVISION MUNGIA 27072026.pdf`: **56 trazos reales de pen y un
sidecar de 213 celdas transcrito a mano**, o sea verdad conocida. El lector
tiene que reproducir esas 213.

Las dos pruebas son complementarias: una da control, la otra realismo.

## 10. Lo que NO hace

- **Fotos de móvil**: no, al principio. Perspectiva, sombras y arrugas son otro
  problema. Se añade después si hace falta.
- **Texto libre de "Obs:"**: se extrae y se devuelve tal cual, sin convertirlo
  en datos.
- **Dependencias nuevas**: ninguna. `pdfplumber`, `PyMuPDF`, `PIL` y `numpy` ya
  están instalados — comprobado el 04/08/2026.

## 11. Riesgos conocidos

| Riesgo | Cómo se ataja |
|---|---|
| Un trazo cruza dos celdas y se cuenta dos veces | Se decide por solape mayoritario y, si está repartido, es duda |
| El escaneo viene torcido o a otra escala | Alinear contra la hoja limpia antes de restar |
| Bixente marca fuera de la rejilla | Queda como observación, no como estado |
| La IA clasifica mal una letra | El recorte queda guardado: el error es auditable, no silencioso |
| Una obra sin ficha | No aplica: el flujo exige base previa |

---

Relacionado: `docs/superpowers/plans/2026-07-28-trabajo-restante-y-reparto.md`
(bloque A), y el protocolo de PDF de `_MOTOR_SAGARDE/CLAUDE.md`.
