# Buscador Eléctrico — gráficos sacados de los libros — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cuando el Buscador Eléctrico cite una fuente cuya página tenga un diagrama real
extraíble del PDF, mostrar su miniatura junto a la cita, con una casilla para incluirla o no
en el informe impreso — nunca generar ni buscar una imagen sustituta si no la hay.

**Architecture:** El indexador (Python) extrae imágenes reales de cada página con
`pdfplumber` además del texto que ya extrae, filtradas por tamaño mínimo, y las adjunta en
base64 a cada fragmento. El exportador las incluye en los metadatos que ya sube a Workers KV.
El Worker las añade al campo `imagenes` de cada fuente que ya devuelve. La pestaña las
renderiza como miniaturas con casilla, y la casilla decide qué entra en el informe impreso.

**Tech Stack:** Python 3.11 + `pdfplumber` (indexador), JavaScript + Cloudflare Workers/
Durable Objects (backend), HTML/CSS/JS sin frameworks (pestaña). `unittest` para Python,
`node:assert` sin framework para JS — mismo criterio que el resto de estos dos proyectos.

## Global Constraints

- Nunca generar ni buscar en internet una imagen sustituta: si la página citada no tiene
  diagrama real, el campo `imagenes` va vacío y no se muestra nada (spec sección A).
- R2 está descartado como almacén (pide tarjeta de crédito) — todo va a Workers KV, igual
  que el índice de texto (spec sección D.2).
- No tocar el umbral de relevancia de búsqueda (0,35) ni qué fragmentos se citan — esta
  funcionalidad solo añade imagen a fuentes que YA se citan (spec sección G).
- No usar pytest ni frameworks de test nuevos en Python (`unittest` de la biblioteca
  estándar, como el resto de `_INDEXADOR`). En el Worker, seguir el patrón sin dependencias
  de `test/nvidia.test.mjs` (`node:assert/strict`, sin framework).
- Todo el código y los mensajes de commit en español, siguiendo el estilo ya establecido en
  ambos repos.

**Punto de parada obligatorio — no es opcional:** la Tarea 2 termina con una galería real
para que Bixente la revise. **No empezar la Tarea 3 sin que él haya validado o ajustado el
umbral de tamaño mínimo** (spec sección I.1). Si quien ejecuta este plan llega a la Tarea 3
sin ese visto bueno explícito, debe parar y pedirlo antes de continuar.

---

### Task 1: Extraer imágenes reales de una página de PDF

**Files:**
- Modify: `_INDEXADOR/extraer_pdf.py`
- Test: `_INDEXADOR/tests/test_extraer_pdf.py`

**Interfaces:**
- Produces: `extraer_imagenes_pagina(pagina, ancho_min_pt=100, alto_min_pt=60) -> list[str]`
  (imágenes en PNG codificadas en base64, ninguna si no hay ninguna que pase el filtro)
- Produces: `extraer_imagenes_por_pdf(ruta_pdf, ancho_min_pt=100, alto_min_pt=60) -> dict[int, list[str]]`
  (clave = número de página, 1-indexado, igual que `extraer_texto_por_pagina`; solo incluye
  páginas que tengan al menos una imagen que pase el filtro)

Verificado en vivo el 16/09/2026 contra un PDF real de esta biblioteca
(`02_INSTALACIONES ELECTRICAS/19. Instalaciones eléctricas en edificios autor Miguel Ángel
Rodríguez Pozueta.pdf`, página 7): `pagina.within_bbox((x0, top, x1, bottom)).to_image(resolution=150)`
renderiza la región de la imagen real y produce un PNG legible de un diagrama real (~5-6 KB).
También verificado: esa misma página tiene 2 imágenes de 261×200pt, mientras que
`BOE-326_Reglamento_electrotecnico_para_baja_tension_e_ITC.pdf` (en
`03_NORMATIVA Y REGLAMENTOS/`) trae en su página 1 un logo de cabecera de solo 71×30pt — el
umbral por defecto (100×60pt) deja dentro la primera y fuera la segunda, punto de partida
razonable para la muestra de la Tarea 2.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `_INDEXADOR/tests/test_extraer_pdf.py`, junto a las rutas de prueba ya existentes:

```python
import base64

RUTA_PDF_CON_DIAGRAMAS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "02_INSTALACIONES ELECTRICAS",
    "19. Instalaciones eléctricas en edificios autor Miguel Ángel Rodríguez Pozueta.pdf",
)

RUTA_PDF_SOLO_LOGO_PEQUENO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "03_NORMATIVA Y REGLAMENTOS",
    "BOE-326_Reglamento_electrotecnico_para_baja_tension_e_ITC.pdf",
)


class TestExtraerImagenesPagina(unittest.TestCase):
    def test_extrae_imagenes_reales_de_una_pagina_con_diagramas(self):
        import pdfplumber
        with pdfplumber.open(RUTA_PDF_CON_DIAGRAMAS) as pdf:
            pagina = pdf.pages[6]  # pagina 7, confirmado 2 imagenes de 261x200pt
            imagenes = extraer_imagenes_pagina(pagina)
        self.assertEqual(len(imagenes), 2)
        primera = base64.b64decode(imagenes[0])
        self.assertTrue(primera.startswith(b'\x89PNG'), "debe ser un PNG valido")

    def test_descarta_imagenes_por_debajo_del_minimo(self):
        import pdfplumber
        with pdfplumber.open(RUTA_PDF_SOLO_LOGO_PEQUENO) as pdf:
            pagina = pdf.pages[0]  # pagina 1, confirmado logo de 71x30pt, por debajo del minimo
            imagenes = extraer_imagenes_pagina(pagina, ancho_min_pt=100, alto_min_pt=60)
        self.assertEqual(imagenes, [])

    def test_umbral_personalizado_cambia_el_resultado(self):
        import pdfplumber
        with pdfplumber.open(RUTA_PDF_SOLO_LOGO_PEQUENO) as pdf:
            pagina = pdf.pages[0]
            imagenes = extraer_imagenes_pagina(pagina, ancho_min_pt=10, alto_min_pt=10)
        self.assertGreater(len(imagenes), 0, "con umbral bajo, el logo de 71x30pt debe pasar")


class TestExtraerImagenesPorPdf(unittest.TestCase):
    def test_devuelve_diccionario_por_numero_de_pagina(self):
        imagenes_por_pagina = extraer_imagenes_por_pdf(RUTA_PDF_CON_DIAGRAMAS)
        self.assertIn(7, imagenes_por_pagina)
        self.assertEqual(len(imagenes_por_pagina[7]), 2)

    def test_paginas_sin_imagenes_no_aparecen_en_el_diccionario(self):
        imagenes_por_pagina = extraer_imagenes_por_pdf(RUTA_PDF_CON_DIAGRAMAS)
        # pagina 3 no tenia imagenes en el muestreo real del 16/09/2026
        self.assertNotIn(3, imagenes_por_pagina)
```

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

Run: `cd "_INDEXADOR" && python -m unittest tests.test_extraer_pdf -v`
Expected: FAIL — `ImportError` o `AttributeError`, `extraer_imagenes_pagina`/
`extraer_imagenes_por_pdf` no existen todavía.

- [ ] **Step 3: Implementar**

Añadir a `_INDEXADOR/extraer_pdf.py` (junto a los imports ya existentes, añadir `base64` e
`io`):

```python
import base64
import io

ANCHO_MIN_PT_DEFECTO = 100
ALTO_MIN_PT_DEFECTO = 60


def extraer_imagenes_pagina(pagina, ancho_min_pt=ANCHO_MIN_PT_DEFECTO, alto_min_pt=ALTO_MIN_PT_DEFECTO):
    """Extrae las imagenes reales de una pagina de pdfplumber que superen el
    tamano minimo dado (en puntos PDF), como PNG codificado en base64.
    Descarta iconos, logos de cabecera y artefactos de tamano casi nulo que
    algunos PDF generan (confirmado real: un PDF de esta biblioteca trae una
    pagina con 1181 fragmentos de imagen de 0x0 - ver spec 2026-09-16)."""
    imagenes = []
    for img in pagina.images:
        ancho = img['x1'] - img['x0']
        alto = img['bottom'] - img['top']
        if ancho < ancho_min_pt or alto < alto_min_pt:
            continue
        bbox = (img['x0'], img['top'], img['x1'], img['bottom'])
        try:
            recorte = pagina.within_bbox(bbox)
            imagen_render = recorte.to_image(resolution=150)
        except Exception:
            continue  # bbox invalido o imagen no renderizable - se descarta, no se rompe la indexacion
        buffer = io.BytesIO()
        imagen_render.save(buffer, format="PNG")
        imagenes.append(base64.b64encode(buffer.getvalue()).decode('ascii'))
    return imagenes


def extraer_imagenes_por_pdf(ruta_pdf, ancho_min_pt=ANCHO_MIN_PT_DEFECTO, alto_min_pt=ALTO_MIN_PT_DEFECTO):
    """Igual que extraer_imagenes_pagina pero para el PDF completo. Devuelve
    {numero_pagina: [imagenes_base64]}, 1-indexado igual que
    extraer_texto_por_pagina, solo con las paginas que tengan alguna imagen
    que pase el filtro."""
    resultado = {}
    with pdfplumber.open(ruta_pdf) as pdf:
        for indice, pagina in enumerate(pdf.pages):
            imagenes = extraer_imagenes_pagina(pagina, ancho_min_pt, alto_min_pt)
            if imagenes:
                resultado[indice + 1] = imagenes
    return resultado
```

- [ ] **Step 4: Ejecutar los tests y comprobar que pasan**

Run: `cd "_INDEXADOR" && python -m unittest tests.test_extraer_pdf -v`
Expected: PASS, los 5 tests nuevos en verde.

- [ ] **Step 5: Commit**

```bash
git add _INDEXADOR/extraer_pdf.py _INDEXADOR/tests/test_extraer_pdf.py
git commit -m "Añade extracción de imágenes reales de página al extractor de PDFs"
```

---

### Task 2: Generar una muestra real para que Bixente la valide — PUNTO DE PARADA

**Files:**
- Create: `_INDEXADOR/generar_muestra_imagenes.py`

**Interfaces:**
- Consumes: `extraer_imagenes_por_pdf` de la Tarea 1
- Produces: una carpeta `_INDEXADOR/muestra_imagenes/` con PNGs reales + un `index.html` que
  Bixente puede abrir en su navegador

Este script es una herramienta de un solo uso para el punto de parada, no forma parte del
indexador normal — no necesita test automático, su "prueba" es que Bixente lo revise.

- [ ] **Step 1: Escribir el script**

```python
"""Genera una muestra real de imagenes extraidas de varios libros para que
Bixente la valide antes de fijar el umbral definitivo (spec 2026-09-16,
seccion I.1). Uso: python generar_muestra_imagenes.py
"""
import os
import sys

from extraer_pdf import extraer_imagenes_por_pdf

CARPETA_INDEXADOR = os.path.dirname(os.path.abspath(__file__))
CARPETA_BIBLIOTECA = os.path.dirname(CARPETA_INDEXADOR)
CARPETA_SALIDA = os.path.join(CARPETA_INDEXADOR, "muestra_imagenes")

LIBROS_DE_MUESTRA = [
    os.path.join("02_INSTALACIONES ELECTRICAS",
                  "19. Instalaciones eléctricas en edificios autor Miguel Ángel Rodríguez Pozueta.pdf"),
    os.path.join("03_NORMATIVA Y REGLAMENTOS",
                  "BOE-326_Reglamento_electrotecnico_para_baja_tension_e_ITC.pdf"),
    os.path.join("03_NORMATIVA Y REGLAMENTOS", "REBT-2011.pdf"),
    os.path.join("01_FUNDAMENTOS Y TEORIA",
                  "06. Curso práctico sobre electricidad autor Donostialdeko Okupazio Bulegoa.pdf"),
]


def main():
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    filas_html = []
    contador = 0

    for libro_relativo in LIBROS_DE_MUESTRA:
        ruta_absoluta = os.path.join(CARPETA_BIBLIOTECA, libro_relativo)
        if not os.path.exists(ruta_absoluta):
            print(f"[AVISO] no encontrado, se salta: {libro_relativo}")
            continue
        libro = os.path.basename(libro_relativo)
        print(f"Procesando: {libro}")
        imagenes_por_pagina = extraer_imagenes_por_pdf(ruta_absoluta)
        for pagina, imagenes in sorted(imagenes_por_pagina.items()):
            for imagen_b64 in imagenes:
                contador += 1
                nombre_fichero = f"{contador:04d}.png"
                import base64
                with open(os.path.join(CARPETA_SALIDA, nombre_fichero), "wb") as f:
                    f.write(base64.b64decode(imagen_b64))
                filas_html.append(
                    f'<div style="margin-bottom:24px"><p><strong>{libro}</strong> — página {pagina}</p>'
                    f'<img src="{nombre_fichero}" style="max-width:500px;border:1px solid #ccc"></div>'
                )

    ruta_html = os.path.join(CARPETA_SALIDA, "index.html")
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'><title>Muestra de imagenes</title></head><body>")
        f.write(f"<h1>Muestra real de imagenes extraidas ({contador} en total)</h1>")
        f.write("".join(filas_html))
        f.write("</body></html>")

    print(f"\n{contador} imagenes extraidas. Abre {ruta_html} en el navegador para revisarlas.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Ejecutarlo y comprobar que produce resultados reales**

Run: `cd "_INDEXADOR" && python generar_muestra_imagenes.py`
Expected: termina sin error, imprime un número de imágenes mayor que 0, y
`_INDEXADOR/muestra_imagenes/index.html` existe.

- [ ] **Step 3: Commit**

```bash
git add _INDEXADOR/generar_muestra_imagenes.py
git commit -m "Añade script de muestra real de imágenes para validar el umbral con Bixente"
```

**No seguir a la Tarea 3 sin completar esto:**

- [ ] **Step 4: PARAR — enseñar `muestra_imagenes/index.html` a Bixente**

Enseñarle la galería real (puede ser abriendo el fichero, o pasándosela de otra forma) y
preguntarle explícitamente: ¿el umbral por defecto (100×60pt) dejó dentro lo que parecen
diagramas de verdad y fuera lo que no lo es? Si pide un umbral distinto, cambiar
`ANCHO_MIN_PT_DEFECTO`/`ALTO_MIN_PT_DEFECTO` en `extraer_pdf.py` (Tarea 1) y volver a
generar la muestra antes de continuar. No avanzar a la Tarea 3 sin su confirmación explícita.

---

### Task 3: Integrar la extracción de imágenes en el indexador real

**Files:**
- Modify: `_INDEXADOR/indexar_biblioteca.py:81-112` (función `indexar_pdf`)
- Test: `_INDEXADOR/tests/test_indexar_biblioteca.py`

**Interfaces:**
- Consumes: `extraer_imagenes_por_pdf` de la Tarea 1 (con el umbral ya validado en la Tarea 2)
- Produces: cada fragmento del índice ahora incluye `'imagenes': list[str]` (puede ser `[]`)

- [ ] **Step 1: Escribir el test que falla**

Añadir a `_INDEXADOR/tests/test_indexar_biblioteca.py`, dentro de `TestIndexarBiblioteca`:

```python
    def test_indexa_incluye_campo_imagenes(self):
        # 00337-VIA CHISPAS.pdf puede no tener diagramas reales - este test
        # comprueba que el campo existe y es una lista, no que tenga
        # contenido. El contenido real ya lo comprueba test_extraer_pdf.py
        # contra un PDF que sabemos que SI tiene diagramas (Tarea 1).
        indice = ejecutar_indexacion(self.carpeta_temporal, self.carpeta_indexador, self.ruta_indice)
        primero = indice[0]
        self.assertIn('imagenes', primero)
        self.assertIsInstance(primero['imagenes'], list)
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

Run: `cd "_INDEXADOR" && python -m unittest tests.test_indexar_biblioteca -v`
Expected: FAIL — `AssertionError: 'imagenes' not found in {...}`

- [ ] **Step 3: Implementar**

En `_INDEXADOR/indexar_biblioteca.py`, añadir el import junto a los ya existentes (línea 15):

```python
from extraer_pdf import extraer_texto_por_pagina, trocear_texto, extraer_imagenes_por_pdf
```

Modificar `indexar_pdf` (líneas 81-112) para calcular las imágenes por página una vez, y
adjuntar a cada fragmento las de las páginas que cubre:

```python
def indexar_pdf(ruta_relativa, carpeta_biblioteca):
    ruta_absoluta = os.path.join(carpeta_biblioteca, ruta_relativa)
    carpeta = ruta_relativa.split(os.sep)[0]
    libro = os.path.basename(ruta_relativa)

    paginas = extraer_texto_por_pagina(ruta_absoluta)
    fragmentos = trocear_texto(paginas)
    if not fragmentos:
        print(f"  [AVISO] sin texto extraible: {ruta_relativa}")
        return []

    imagenes_por_pagina = extraer_imagenes_por_pdf(ruta_absoluta)

    resultado = []
    for inicio_lote in range(0, len(fragmentos), TAMANO_LOTE_EMBEDDINGS):
        lote = fragmentos[inicio_lote:inicio_lote + TAMANO_LOTE_EMBEDDINGS]
        textos_lote = [f['texto'] for f in lote]
        vectores = generar_embeddings(textos_lote, tipo="passage")
        if len(vectores) != len(textos_lote):
            raise RuntimeError(
                f"La API devolvio {len(vectores)} embeddings para {len(textos_lote)} "
                f"textos enviados al indexar {ruta_relativa} (deberian coincidir)"
            )
        for frag, vector in zip(lote, vectores):
            imagenes_frag = [
                img for pag in frag['paginas'] for img in imagenes_por_pagina.get(pag, [])
            ]
            resultado.append({
                'id': f"{ruta_relativa}::{frag['paginas'][0] if frag['paginas'] else 0}::{len(resultado)}",
                'libro': libro,
                'carpeta': carpeta,
                'ruta_relativa': ruta_relativa,
                'paginas': frag['paginas'],
                'texto': frag['texto'],
                'embedding': vector,
                'imagenes': imagenes_frag,
            })
    return resultado
```

- [ ] **Step 4: Ejecutar el test y comprobar que pasa**

Run: `cd "_INDEXADOR" && python -m unittest tests.test_indexar_biblioteca -v`
Expected: PASS, todos los tests de este fichero en verde (incluidos los ya existentes — este
cambio no debe romper ninguno).

- [ ] **Step 5: Commit**

```bash
git add _INDEXADOR/indexar_biblioteca.py _INDEXADOR/tests/test_indexar_biblioteca.py
git commit -m "El indexador adjunta imágenes reales a cada fragmento, con el umbral validado por Bixente"
```

---

### Task 4: Incluir las imágenes en la exportación a Workers KV

**Files:**
- Modify: `_INDEXADOR/exportar_indice_completo.py:42-59` (función `_escribir_trozo`)
- Test: `_INDEXADOR/tests/test_exportar_indice_completo.py`

**Interfaces:**
- Consumes: fragmentos con `'imagenes': list[str]` (Tarea 3)
- Produces: `metadatos_<i>.json` con un campo `imagenes` por entrada, mismo formato para el
  Worker

- [ ] **Step 1: Escribir el test que falla**

Modificar el `setUp` de `TestTroceadoIndice` en `_INDEXADOR/tests/test_exportar_indice_completo.py`
para que los fragmentos de prueba incluyan `imagenes` (solo en algunos, para comprobar que
también funciona cuando falta el campo):

```python
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.ruta_indice = os.path.join(self.carpeta, "indice_prueba.jsonl")
        with open(self.ruta_indice, "w", encoding="utf-8") as f:
            for i in range(7):
                frag = {
                    "id": f"libro.pdf::{i}::0",
                    "libro": "libro.pdf",
                    "carpeta": "01_FUNDAMENTOS Y TEORIA",
                    "ruta_relativa": "01_FUNDAMENTOS Y TEORIA/libro.pdf",
                    "paginas": [i],
                    "texto": f"fragmento numero {i}",
                    "embedding": [0.1 * (i % 5)] * DIMENSIONES,
                    "imagenes": ["imagenfalsa1base64"] if i == 0 else [],
                }
                f.write(json.dumps(frag, ensure_ascii=False) + "\n")
```

Y añadir un test nuevo a `TestTroceadoIndice`:

```python
    def test_metadatos_incluyen_imagenes(self):
        carpeta_salida = os.path.join(self.carpeta, "export_kv")
        trocear_indice(self.ruta_indice, carpeta_salida, tamano_trozo=3)
        with open(os.path.join(carpeta_salida, "metadatos_0.json"), "r", encoding="utf-8") as f:
            metas0 = json.load(f)
        self.assertEqual(metas0[0]["imagenes"], ["imagenfalsa1base64"])
        self.assertEqual(metas0[1]["imagenes"], [])
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

Run: `cd "_INDEXADOR" && python -m unittest tests.test_exportar_indice_completo -v`
Expected: FAIL — `KeyError: 'imagenes'`

- [ ] **Step 3: Implementar**

En `_INDEXADOR/exportar_indice_completo.py`, modificar `_escribir_trozo` (líneas 52-55):

```python
    metadatos = [
        {
            "id": frag["id"],
            "libro": frag["libro"],
            "paginas": frag["paginas"],
            "texto": frag["texto"],
            "imagenes": frag.get("imagenes", []),
        }
        for frag in fragmentos
    ]
```

- [ ] **Step 4: Ejecutar el test y comprobar que pasa**

Run: `cd "_INDEXADOR" && python -m unittest tests.test_exportar_indice_completo -v`
Expected: PASS, todos los tests en verde.

- [ ] **Step 5: Commit**

```bash
git add _INDEXADOR/exportar_indice_completo.py _INDEXADOR/tests/test_exportar_indice_completo.py
git commit -m "Incluye las imágenes de cada fragmento en la exportación a Workers KV"
```

---

### Task 5: El Worker incluye las imágenes en las fuentes que devuelve

**Files:**
- Modify: `_WORKER/src/buscador_electrico.js` (bloque que construye `fuentesRespuesta`,
  buscar `fuentesRespuesta = relevantes.map(`)
- Test: Create `_WORKER/test/buscador_electrico.test.mjs`

**Interfaces:**
- Consumes: `this.metadatos[i].imagenes` (Tarea 4, puede no existir en entradas antiguas)
- Produces: `construirFuentes(relevantes, metadatos) -> Array<{libro, paginas, puntuacion, texto, imagenes}>`
  (exportada, para poder probarla sin necesitar un Durable Object real)

- [ ] **Step 1: Escribir el test que falla**

Crear `_WORKER/test/buscador_electrico.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { construirFuentes } from "../src/buscador_electrico.js";

function main() {
  const metadatos = [
    { libro: "libro1.pdf", paginas: [1, 2], texto: "texto uno", imagenes: ["imagenfalsa1"] },
    { libro: "libro2.pdf", paginas: [5], texto: "texto dos" }, // sin campo imagenes (indice viejo)
  ];
  const relevantes = [
    { indice: 0, puntuacion: 0.9 },
    { indice: 1, puntuacion: 0.5 },
  ];

  const fuentes = construirFuentes(relevantes, metadatos);
  assert.equal(fuentes.length, 2);
  assert.deepEqual(fuentes[0].imagenes, ["imagenfalsa1"], "debe incluir las imagenes cuando las hay");
  assert.deepEqual(fuentes[1].imagenes, [], "debe dar array vacio cuando el metadato no trae imagenes, nunca undefined");
  assert.equal(fuentes[0].libro, "libro1.pdf");
  assert.equal(fuentes[0].texto, "texto uno");

  console.log("OK construirFuentes: incluye imagenes cuando las hay, array vacio cuando no");
}

main();
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

Run: `cd "_WORKER" && node test/buscador_electrico.test.mjs`
Expected: FAIL — `construirFuentes` no está exportada de `src/buscador_electrico.js` todavía.

- [ ] **Step 3: Implementar**

En `_WORKER/src/buscador_electrico.js`, localizar el bloque (dentro del método `fetch` de la
clase `BuscadorElectrico`) que hoy dice:

```javascript
      fuentesRespuesta = relevantes.map((r) => ({
        libro: this.metadatos[r.indice].libro,
        paginas: this.metadatos[r.indice].paginas,
        puntuacion: r.puntuacion,
        texto: this.metadatos[r.indice].texto,
      }));
```

Sustituirlo por una llamada a una función nueva:

```javascript
      fuentesRespuesta = construirFuentes(relevantes, this.metadatos);
```

Y añadir la función, exportada, a nivel de módulo (fuera de la clase `BuscadorElectrico`,
por ejemplo junto a `respuestaJson`):

```javascript
export function construirFuentes(relevantes, metadatos) {
  return relevantes.map((r) => ({
    libro: metadatos[r.indice].libro,
    paginas: metadatos[r.indice].paginas,
    puntuacion: r.puntuacion,
    texto: metadatos[r.indice].texto,
    imagenes: metadatos[r.indice].imagenes || [],
  }));
}
```

- [ ] **Step 4: Ejecutar el test y comprobar que pasa**

Run: `cd "_WORKER" && node test/buscador_electrico.test.mjs`
Expected: `OK construirFuentes: incluye imagenes cuando las hay, array vacio cuando no`

- [ ] **Step 5: Commit**

```bash
git add _WORKER/src/buscador_electrico.js _WORKER/test/buscador_electrico.test.mjs
git commit -m "El Worker incluye las imágenes reales de cada fuente en la respuesta"
```

---

### Task 6: La pestaña muestra la miniatura con su casilla de informe

**Files:**
- Modify: `VARIOS/BUSCADOR ELECTRICO/app_buscador_electrico.html` (función `añadirMensajeIA`,
  y el bloque CSS)

**Interfaces:**
- Consumes: `datos.fuentes[].imagenes` (array de PNG en base64, del Worker de la Tarea 5)

- [ ] **Step 1: Releer el fichero actual antes de tocarlo**

Este fichero puede haber cambiado desde que se escribió este plan — releer
`añadirMensajeIA(datos)` completa (busca `function añadirMensajeIA`) y el bloque CSS de
`.fuente-cita` antes de pegar código a ciegas. El código de los Steps 2-3 está verificado
contra el contenido real del fichero a 16/09/2026 (líneas 157-179); si ha cambiado desde
entonces, adaptar la forma sin cambiar el comportamiento descrito.

- [ ] **Step 2: Añadir el CSS de la miniatura**

Junto a las reglas ya existentes de `.fuente-cita`/`.fuente-cita-texto`, añadir:

```css
.fuente-imagen{margin-top:8px;display:flex;flex-direction:column;gap:4px;align-items:flex-start}
.fuente-imagen img{max-width:280px;border:1px solid #d0d5dd;border-radius:6px}
.fuente-imagen label{font-size:.8em;color:#555;display:flex;align-items:center;gap:6px}
```

- [ ] **Step 3: Renderizar la miniatura dentro del bucle de fuentes**

El bucle actual (línea 167) es `for (const f of datos.fuentes) {`, sin índice — hace falta
uno para dar un `id` único a cada casilla cuando una respuesta trae varias fuentes con
imagen. Cambiar la línea del bucle para llevar la cuenta:

```diff
-    for (const f of datos.fuentes) {
+    let indiceFuente = 0;
+    for (const f of datos.fuentes) {
       html += '<div class="fuente-cita">';
       html += `<div class="fuente-cita-libro">${escaparHtml(f.libro)} (pág. ${f.paginas.join(", ")})</div>`;
       if (f.texto) {
         html += `<div class="fuente-cita-texto">"${escaparHtml(f.texto)}"</div>`;
       }
+      if (f.imagenes && f.imagenes.length > 0) {
+        f.imagenes.forEach((imagenB64, idxImagen) => {
+          const idCasilla = `incluir-img-${indiceFuente}-${idxImagen}`;
+          html += '<div class="fuente-imagen">';
+          html += `<img src="data:image/png;base64,${imagenB64}" alt="Diagrama de ${escaparHtml(f.libro)}, página ${f.paginas.join(", ")}">`;
+          html += `<label><input type="checkbox" id="${idCasilla}" class="casilla-informe-imagen" data-src="data:image/png;base64,${imagenB64}"> Incluir en el informe</label>`;
+          html += "</div>";
+        });
+      }
       html += "</div>";
+      indiceFuente++;
     }
```

- [ ] **Step 4: Probar en el navegador con datos reales inyectados**

Abrir la pestaña en el navegador (local o el fichero directamente), y en la consola del
navegador, tras hacer una pregunta real o inyectar una respuesta con
`datos.fuentes[0].imagenes = ["<un base64 real de la carpeta muestra_imagenes de la Tarea 2>"]`
antes de llamar a `añadirMensajeIA(datos)`, comprobar visualmente que la miniatura y la
casilla aparecen correctamente junto a la fuente.

- [ ] **Step 5: Commit**

```bash
git add "VARIOS/BUSCADOR ELECTRICO/app_buscador_electrico.html"
git commit -m "La pestaña muestra la miniatura del diagrama junto a cada fuente, con su casilla"
```

---

### Task 7: El informe impreso respeta la casilla de cada imagen

**Files:**
- Modify: `VARIOS/BUSCADOR ELECTRICO/app_buscador_electrico.html` (función `imprimirInforme`,
  y el bloque `@media print`)

**Interfaces:**
- Consumes: el DOM que ya construye la Tarea 6 (`input.casilla-informe-imagen`)

- [ ] **Step 1: Ocultar las miniaturas en impresión por defecto**

En el bloque `@media print` ya existente, junto a la línea que oculta `.fuentes,.fuente-cita`,
añadir `.fuente-imagen` a esa misma regla para que, por defecto, ninguna miniatura se
imprima:

```css
  .fuentes,.fuente-cita,.fuente-imagen{display:none!important}
```

- [ ] **Step 2: Mostrar solo las imágenes marcadas justo antes de imprimir**

Modificar `imprimirInforme()` para, antes de `window.print()`, insertar en el informe (dentro
de `.letterhead-impresion` o al final del hilo, a decidir según cómo quede visualmente mejor
al probarlo) una copia de cada imagen cuya casilla esté marcada, y quitarla después de
imprimir:

```javascript
function imprimirInforme() {
  fechaInforme.textContent = new Date().toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit", year: "numeric" });

  const marcadas = [...document.querySelectorAll(".casilla-informe-imagen:checked")];
  const contenedorImpresion = document.createElement("div");
  contenedorImpresion.id = "imagenes-para-imprimir";
  contenedorImpresion.style.display = "none";
  marcadas.forEach((casilla) => {
    const img = document.createElement("img");
    img.src = casilla.dataset.src;
    img.style.maxWidth = "100%";
    contenedorImpresion.appendChild(img);
  });
  document.querySelector(".contenido").appendChild(contenedorImpresion);

  window.print();

  contenedorImpresion.remove();
}
```

Y añadir la regla de impresión correspondiente para que `#imagenes-para-imprimir` sí se
muestre en papel aunque `.fuente-imagen` esté oculto:

```css
  #imagenes-para-imprimir{display:block!important}
  #imagenes-para-imprimir img{max-width:100%;margin-bottom:12px;break-inside:avoid}
```

- [ ] **Step 3: Probar de verdad en el navegador**

Con al menos una miniatura marcada y otra sin marcar, abrir la vista previa de impresión
(`Ctrl+P` o el equivalente) y comprobar visualmente: la marcada aparece en el informe, la no
marcada no, y no quedan huecos raros.

- [ ] **Step 4: Commit**

```bash
git add "VARIOS/BUSCADOR ELECTRICO/app_buscador_electrico.html"
git commit -m "El informe impreso solo incluye las imágenes que se marquen explícitamente"
```

---

### Task 8: Reindexar la biblioteca completa, desplegar y verificar de punta a punta

**Files:** ninguno nuevo — ejecución real contra los sistemas ya construidos.

**Interfaces:** ninguna nueva — esta tarea verifica que las Tareas 1-7 funcionan juntas
contra datos reales, no añade código.

- [ ] **Step 1: Reindexar la biblioteca completa con imágenes**

Run: `cd "_INDEXADOR" && python indexar_biblioteca.py --forzar`
Expected: termina sin error; el resumen final muestra un número de fragmentos igual o
parecido a los 14.679 ya conocidos (una reindexación completa puede tardar — es una llamada
real a la API de NVIDIA por cada lote, no una operación instantánea).

- [ ] **Step 2: Confirmar que el índice tiene imágenes de verdad**

Run un script rápido de una línea (o Python interactivo) que cuente cuántas entradas de
`indice_biblioteca.jsonl` tienen `imagenes` no vacío, y comprobar que el número es mayor que
0 y razonable (no todas, no ninguna — coherente con la sección C de la spec: los manuales
técnicos tienen diagramas, los normativos casi no).

- [ ] **Step 3: Re-exportar y volver a subir el índice a Workers KV**

Run: `cd "_INDEXADOR" && python exportar_indice_completo.py`, y subir los ficheros
resultantes de `export_kv/` a Workers KV con el mismo procedimiento ya usado en la Fase 2
(`wrangler kv key put`, uno por clave — ver `_WORKER/RESULTADO_MEDICION_ESCALA_COMPLETA.md`
para el procedimiento exacto ya usado antes). Recordar la lección ya conocida: copiar los
ficheros exportados fuera de la carpeta sincronizada por OneDrive antes de subirlos, si
`wrangler kv key put` falla de forma rara.

- [ ] **Step 4: Desplegar el Worker actualizado**

Run: `cd "_WORKER" && node --check src/buscador_electrico.js && npx wrangler deploy`

- [ ] **Step 5: Prueba real de punta a punta con una pregunta que se sepa que cita un diagrama**

Hacer una pregunta real contra el Worker desplegado que se sepa de antemano que va a citar
una página con diagrama real (por ejemplo, algo relacionado con lo que aparece en la página
7 del libro de instalaciones eléctricas en edificios usado en las Tareas 1-2). Comprobar en
la respuesta JSON que `fuentes[].imagenes` trae al menos una imagen real.

- [ ] **Step 6: Prueba real en la pestaña publicada**

Publicar la pestaña actualizada en Sagarde (revisar el diff antes de comitear, nunca
`git add -A` — ver spec sección I.2) y repetir la misma pregunta desde el navegador real:
confirmar que la miniatura se ve, que la casilla funciona, y que el informe impreso respeta
lo marcado (repetir la comprobación visual de la Tarea 7 pero contra el sitio publicado, no
solo en local).

- [ ] **Step 7: Prueba negativa — una pregunta sin diagrama no debe mostrar nada raro**

Repetir con una pregunta que se sepa que solo cita páginas normativas (REBT/BOE, que
raramente tienen diagramas) y confirmar que no aparece ninguna miniatura ni un hueco vacío en
su lugar.

- [ ] **Step 8: Actualizar la memoria del proyecto**

Añadir una entrada a la memoria de Claude
(`project_sagarde_buscador_electrico_fase2_implementacion.md` o una nueva memoria dedicada a
esta fase) con el resultado real: cuántas imágenes se extrajeron en total, tamaño real que
añadió al índice de KV, y cualquier hallazgo real de esta verificación de punta a punta.
