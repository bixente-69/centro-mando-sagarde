# El generador de revisiones trabaja desde la base de datos

Diseño aprobado por Bixente el 28/07/2026.

## 1. Para qué

Este trabajo es el **paso 1 del ciclo que Bixente ha declarado el fin del
entorno Sagarde**:

1. La app genera la hoja TYPO **leyendo la base de datos de la obra**
   (`ficha_obra.json`), no la última revisión.
2. Bixente la imprime y sobrescribe a boli en obra.
3. La escanea — PDF, JPG, lo que sea.
4. **La IA lee el escaneo por visión** y lo traduce a datos digitales.
5. Esos datos alimentan la base de esa obra, y el ciclo se repite.

Textual: *"no funcionará nada como quiero sino logramos esto. es el fin a
conseguir."*

Este spec cubre **el paso 1 y las condiciones que la hoja debe cumplir para
que el paso 4 sea posible**. Los pasos 3 a 5 quedan fuera de alcance.

## 2. Estado verificado hoy (28/07/2026, HEAD `b76911c`, 57 pruebas en verde)

**Dos caminos coexisten en `generar_todos.py`:**

| Camino | De dónde saca los estados | Obras |
|---|---|---|
| `registro_revision_desde_ficha` (línea 324) | `ficha['estados']` — la base | mungia |
| `crear_registro_revision` (línea 367) | `prioridades['detalle_items']` — derivado de las revisiones | gernika, bolueta, obisporueta |

**La base de Mungia**, medida directamente sobre `ficha_obra.json`:

```
X = 1801    M = 86    P = 434    ? = 35     total = 2356
```

Al `.js` viajan 1887 estados = 1801 `X` + 86 `M`. Las 469 celdas `P` y `?` se
exportan en blanco (línea 326: `if valor not in {'X','M','/'}: continue`).
La ficha **no está rancia**: registra la revisión 27/07/2026, la misma que el
priorizador.

**Línea base de las otras obras, que no se puede mover:**
Gernika 76.3 · Bolueta 36.1 · Obispo Orueta 80.0 · Mungia 79.8.

**La hoja es legible por visión — verificado, no supuesto.** Leyendo la página 3
del PDF del 27/07 sin mirar el fichero de correcciones, se dedujo
`cuad-mec`, `techos-zzcc` y `aguj-zzcc` de la planta 5 en A2/B2/C3 → todas `M`.
El sidecar transcrito a mano dice exactamente eso, celda por celda.

**El "OCR" no es un módulo de Python.** Buscar `ocr|tesseract|vision` en el
código da cero coincidencias y eso NO significa que el paso no exista: lo
ejecuta la IA leyendo la imagen.

## 3. El problema que resuelve

**P1 — El desplegable no distingue el origen.** Ofrece las cuatro obras por
igual y las presenta todas como "Memoria del portal cargada", aunque tres
salgan de la última revisión y sólo Mungia de la base.

**P2 — Una página de continuación no se identifica.** La hoja se genera así:

```
<div class="planta-block">                                   ← break-inside: avoid
  <div class="block-hdr">ZR1 · ZR1.1 · Plantas PB · 1 · 2</div>   ← FUERA de la tabla
  <table>
    <thead> TAJO │ Planta PB · 3 viv. │ A2 B2 C3 </thead>         ← DENTRO
    <tbody> …filas de tajos… </tbody>
```

`break-inside: avoid` es una sugerencia, no una garantía: cuando el contenido
supera una página, el navegador parte igual. Al partir, **repite sólo el
`<thead>`**. La página de continuación llevaría planta y vivienda, pero **no
bloque ni portal**, que viven fuera de la tabla.

Mungia tiene tres portales con las mismas letras de vivienda: una página que
diga "Planta PB · A2" sin decir el portal es **irresoluble**. Y las páginas 2 y
3 tampoco llevan obra ni fecha, que sólo salen en la primera.

`MAX_TAJOS_A4 = 38` y Mungia tiene exactamente 38 tajos: está en el límite hoy.

**P3 — El fondo de color estorba.** Sombrea las celdas, dificulta tachar sobre
la hoja de campo y no aporta nada que Bixente no sepa ya por otros medios.

## 4. Requisitos

Cada uno es falsable y tiene su verificación en §6.

- **R1** — El desplegable ofrece **exactamente** las obras cuyo registro trae
  `fuente_estructura == "ficha_obra.json"`. Hoy: sólo Mungia.
- **R2** — Si no hay ninguna obra con base, el desplegable **no queda vacío y
  mudo**: dice cuántas obras hay publicadas y que les falta sembrar la ficha.
  *Un recuento de cero es señal de alarma, no de "no aplica".*
- **R3** — Las celdas sin estado (`P` y `?`) se imprimen **limpias, sin marca
  de ningún tipo**, para poder escribir encima sin ambigüedad.
- **R4** — **Toda página A4**, incluidas las de continuación, identifica: obra,
  fecha de revisión, bloque, portal, planta y vivienda. Ninguna página suelta
  puede quedar huérfana.
- **R5** — Fondo blanco unificado en las celdas. La identidad Sagarde se
  conserva en la base de la hoja: logo, cabecera azul, tipografía.
- **R6** — Las marcas impresas se distinguen de las manuscritas **sin depender
  del color del boli**, que varía según el día (negro, azul o pen digital).
- **R7** — Ninguna obra distinta de Mungia cambia sus cifras.

## 5. Diseño

### 5.1 Filtrado del desplegable (R1, R2)

`renderInstalledWorks()` filtra por `fuente_estructura === 'ficha_obra.json'`.

**El filtro va en la app, no en Python.** `generar_informe_ejecutivo.py` lee el
mismo `obras_revisiones.js` (línea 297); filtrar aguas arriba le quitaría tres
obras del suelo sin que nadie lo haya pedido. El `.js` sigue publicando las
cuatro.

`setSourceStatus(null)` gana un tercer caso, distinto de los dos actuales: hay
obras publicadas pero ninguna con base de datos.

### 5.2 Identificación en toda página (R4)

El rótulo de bloque y portal **se mueve dentro del `<thead>`**, como una `<tr>`
con `colspan` completo, porque el `<thead>` es lo único que el navegador repite
al partir una tabla entre páginas. Esa misma fila incorpora obra y fecha de
revisión.

Resultado: cualquier página, suelta y escaneada, dice de qué obra es, de qué
fecha, qué bloque, qué portal, qué planta y qué vivienda.

`.block-hdr` desaparece como div externo. La regla `break-inside: avoid` de
`.planta-block` se conserva sin tocar: sigue siendo útil para que la tabla no se
parta cuando sí cabe entera.

### 5.3 Fondo blanco y marcas legibles (R3, R5, R6)

- Fondo blanco unificado en todas las celdas de estado. Se retira el sombreado
  verde y el resto de fondos por estado.
- Se conservan: logo, cabecera azul corporativa, tipografía, y las bandas de
  sección como separadores estructurales.
- **Las marcas impresas pasan a gris medio neutro: `#6E6E6E`** (≈57 % de negro,
  R=G=B). El discriminador se pone en lo impreso, que es lo único bajo control:
  ningún boli escribe en gris medio uniforme, y la tipografía impresa es regular
  y está centrada, frente al trazo irregular del manuscrito. Así la lectura por
  visión no depende de que Bixente use un boli de un color concreto.

  *Se probó primero `#6B7280` (el gris frío habitual en interfaces) y se cambió
  a neutro al medirlo sobre el PDF impreso: tenía 21 puntos de desviación hacia
  el azul, y el criterio es precisamente que ningún boli pueda imitar el color.
  El valor puede ajustarse si la impresión resulta demasiado tenue, siempre que
  siga siendo gris neutro: ni negro puro ni un tono con matiz.*

### 5.4 Lo que NO cambia

- El canal `estados` sigue transportando sólo `X`, `M` y `/`.
- El camino de vuelta: imprimir → boli → escaneo → lectura por visión → sidecar.
- `lector_hoja_tajos_pdf.py`, que sólo acepta `X`, `M` y `/` (línea 144) e
  ignora cualquier otra cosa impresa en la celda.
- Las obras sin ficha siguen publicándose en el `.js` y siguen alimentando el
  informe ejecutivo.
- La opción "Configuración manual" del desplegable.

## 6. Verificación

**Con `unittest` (biblioteca estándar, sin dependencias nuevas):**

| Requisito | Prueba |
|---|---|
| no regresión | Mungia sigue exportando 1887 estados, sólo `X` y `M`, y su `pct_ponderado` sigue en 79.8 |
| R7 | Gernika 76.3, Bolueta 36.1, Obispo Orueta 80.0 sin moverse |
| R3 | Ninguna clave `P` ni `?` aparece en el `estados` exportado |

Ninguna de las tres piezas del §5 debería mover un solo número: son filtro de
presentación, maquetación de cabecera y estilo. **Si alguna cifra se mueve, hay
un efecto colateral y hay que pararse a entenderlo antes de seguir.**

**A mano, y así se declarará en el plan — la suite no alcanza el JavaScript:**

| Requisito | Comprobación |
|---|---|
| R1 | Abrir la app: el desplegable ofrece Mungia y nada más |
| R2 | Renombrar temporalmente la ficha y comprobar que sale el mensaje, no un desplegable vacío |
| R4 | **Generar una hoja con tajos de sobra que fuerce el corte de página**, imprimirla a PDF y comprobar que la página de continuación se identifica sola |
| R5, R6 | Inspección visual de la hoja generada |

**Probar por mutación:** romper a propósito el filtro de R1 y el traslado de
cabecera de R4, y confirmar que la comprobación correspondiente se entera.

**Antes de dar nada por bueno:** reportar a Bixente el antes/después de las
cuatro obras. Aplicar en silencio una corrección que mueve cifras es repetir el
problema desde el otro lado.

## 7. Riesgos y deuda conocida

- **`Actualizar_Sagarde.bat` hace `git add -A`.** No lanzarlo con trabajo en
  vuelo. Restaurar siempre cualquier fichero mutado para una verificación.
- **`registro_revision_desde_ficha` sólo lee `bloques[0]`.** Las cuatro obras
  tienen hoy un solo bloque, así que no rompe nada; si alguna gana un segundo,
  se perdería en silencio. Se anota, no se corrige aquí.
- **El PDF del 27/07 lleva impreso "FECHA REVISIÓN 26/07/2026"** pero el fichero
  se llama `27072026` y el sistema toma la fecha del nombre. No ha dado guerra
  todavía.
- **Un escaneo no tiene capa de texto**: no entra por `lector_hoja_tajos_pdf.py`.
  Tiene que entrar por el camino de la visión.

## 8. Fuera de alcance

- Sembrar la ficha de Gernika, Bolueta y Obispo Orueta. Queda pendiente
  explícitamente: *"si solo esta mungia, solo saldra mungia y queda pendiente
  el resto para cuando lleguemos a terminar el resto"*.
- Automatizar los pasos 3 a 5 del ciclo (escaneo → visión → base). Hoy la
  salida de la lectura es el sidecar `.correcciones.json`, que en la revisión
  del 27/07 llevaba 213 celdas.
- `generar_informe_ejecutivo.py`, que carga su propio historial (línea 372) y
  no recibe la inversión del flujo.
- La Tarea 4 de la fase A (verificación end-to-end).
- La obra `2026 GORLIZ HOSPITAL`, con `inventario_total: 0` sin explicar.
- Distinguir `P` de `?` en la hoja impresa: descartado por Bixente, todo lo
  vacío va limpio.
- Subir la altura de fila: retirado, el problema real era la identificación.

Relacionado: `docs/superpowers/specs/2026-07-27-ficha-como-centro-design.md`
