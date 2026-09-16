# Buscador Eléctrico — gráficos sacados de los libros (Fase 3a) — diseño

Fecha: 16/09/2026. Autor: Claude (diseño, sin programar nada todavía).

Continúa de [2026-09-14-buscador-electrico-design.md](2026-09-14-buscador-electrico-design.md)
(diseño original) y de la implementación completa ya en producción
(`_SISTEMA/docs/superpowers/plans/2026-09-15-buscador-electrico-implementacion-completa.md`).

Encargo de Bixente (16/09/2026): quiere gráficos en las respuestas del
Buscador Eléctrico. Confirmó que quiere **dos cosas distintas**: gráficos
generados por IA, y gráficos sacados de las páginas reales de sus propios
libros. Esta spec cubre **solo la segunda** — ver sección B para por qué.

---

## A. Alcance de esta fase

**Sí, en esta fase:**
- Cuando la IA cite una fuente (de las que ya aparecen en cursiva en pantalla)
  y esa página tenga un diagrama real extraíble del PDF, mostrar una
  miniatura de ese diagrama junto a la cita.
- Casilla propia por miniatura: "incluir en el informe" — cada imagen se
  decide por separado, no es todo o nada.
- El indexador (Fase 1) aprende a extraer también imágenes de cada página,
  no solo texto.

**No, en esta fase (regla explícita de Bixente, 16/09/2026, textual: "si no
hay imagenes de momento nada"):**
- Si la página citada no tiene un diagrama real, no se muestra nada. Nunca
  se genera una imagen ni se busca una sustituta en internet para rellenar
  el hueco.
- Buscar un diagrama en páginas que la IA NO ha citado ya (ver sección G).

---

## B. Por qué esto y no "gráficos" en general

Bixente pidió ambos tipos de gráficos, pero son dos piezas casi
independientes entre sí (comparten muy poco código real) y con perfiles de
riesgo muy distintos:

- **Sacados de los libros** (esta spec): no necesita ningún modelo de IA
  nuevo, no cuesta dinero, y es la opción más alineada con la norma de este
  proyecto de nunca inventar — lo que se muestra es literalmente lo que hay
  en el libro.
- **Generados por IA** (fase aparte, no diseñada todavía): comprobado el
  16/09/2026 que la cuenta de NVIDIA que ya usamos **no tiene ningún modelo
  de generación de imagen** — el único nombre que sonaba a ello
  (`google/diffusiongemma-26b-a4b-it`) resultó ser, al probarlo en vivo, un
  modelo de texto. Haría falta un proveedor nuevo (probablemente de pago) y
  un diseño cuidadoso de aviso de "no verificado" (un diagrama eléctrico
  generado por IA sutilmente incorrecto puede parecer correcto a un
  electricista con prisa). Bixente confirmó (16/09/2026) que esto y la
  búsqueda en internet son casos a valorar por separado más adelante, cada
  uno con su propio diseño.

Por eso se decompone en sub-proyectos independientes, empezando por este.

---

## C. Qué se comprobó de verdad antes de diseñar esto

- **Los manuales técnicos sí tienen diagramas reales incrustados en la
  página** (probado con `pdfplumber` sobre PDFs reales de la biblioteca):
  "19. Instalaciones eléctricas en edificios" trae 2-7 imágenes por página,
  claramente figuras (tamaños como 261×200, 445×91 px), no la hoja entera
  escaneada.
- **Los textos normativos apenas tienen dibujos**: REBT-2011.pdf y
  BOE-326 (el reglamento electrotécnico y sus ITC) tienen 0-1 imágenes en
  sus primeras páginas, casi todo es texto legal — normal, no es un fallo.
- **Hay basura real que filtrar**: "06. Curso práctico sobre electricidad"
  trae una página con 1181 fragmentos de imagen de tamaño 0×0 — un
  artefacto de cómo se generó ese PDF en concreto, no contenido real. Un
  filtro de tamaño mínimo lo descarta.
- **Ningún libro de los 101 es un escaneo puro**: medido sobre el índice
  real ya generado (`_INDEXADOR/indice_biblioteca.jsonl`, 14.679
  fragmentos) — el libro con MENOS texto por página tiene 329 caracteres
  por página, un texto real y sustancial, no una hoja fotografiada sin capa
  de texto. Esto significa que el caso "libro entero sin nada que sacar" no
  existe en la práctica: el único caso real es "esta página en concreto no
  tiene diagrama", que ya cubre la sección A.

---

## D. Arquitectura y flujo

1. **Indexador** (`_INDEXADOR/`, Python, se ejecuta en el PC de Bixente):
   al procesar cada página de un PDF, además del texto (como ya hace),
   extraer también sus imágenes incrustadas reales (`page.images` de
   `pdfplumber`, o el mecanismo equivalente que ya usa el indexador).
   Filtrar por tamaño mínimo razonable para ser un diagrama de verdad
   (descarta iconos, logos de cabecera y artefactos de 0×0 — el umbral
   exacto se ajusta con datos reales durante la implementación, no se fija
   a ciegas aquí). Cada imagen que pase el filtro se asocia al mismo
   fragmento de texto de esa página (un fragmento ya guarda su rango de
   `paginas`).
2. **Almacenamiento**: igual que el texto, en Workers KV (R2 sigue
   descartado — pide tarjeta de crédito, confirmado en la spec original).
   El tamaño real que añade al índice se mide durante la implementación con
   los datos reales de los 101 libros, no se promete un número aquí.
3. **El ayudante privado** (Cloudflare Worker): cuando construye la lista de
   `fuentes` de una respuesta (ya incluye `libro`, `paginas`, `puntuacion`,
   `texto`), añade un campo con la imagen (o imágenes) de esa fuente si el
   indexador encontró alguna. Si no hay, el campo simplemente no aparece o
   viene vacío — la pestaña nunca inventa una miniatura donde no la hay.
4. **La pestaña** (`VARIOS/BUSCADOR ELECTRICO/app_buscador_electrico.html`):
   en la sección "Fragmentos consultados" que ya existe (cursiva, junto a
   cada fuente), si esa fuente trae imagen, se añade su miniatura al lado
   con una casilla "incluir en el informe" (desmarcada por defecto, igual
   de criterio que las fuentes de texto, que hoy tampoco entran en el
   informe por defecto — ver sección F).

---

## E. Qué pasa en cada caso

- **La página citada no tiene diagrama real**: no se muestra nada para esa
  fuente. Coherente con el resto del sistema: nunca se rellena un hueco con
  algo que no está.
- **La página tiene más de un diagrama**: se muestran todas las miniaturas
  que pasen el filtro de tamaño, cada una con su propia casilla.
- **Dos fragmentos citados comparten página y por tanto la misma imagen**:
  puede verse la misma miniatura repetida junto a cada fuente — se acepta
  como comportamiento normal en esta fase (no se deduplica); si en el uso
  real resulta molesto, se revisa más adelante.

---

## F. Informe impreso

Cada miniatura lleva su propia casilla "incluir en el informe" (petición
explícita de Bixente, 16/09/2026: "la opcion o no de incluirla en el
informe"). Igual que las fuentes de texto no aparecen en el informe salvo
que se decida lo contrario, las imágenes no marcadas no se imprimen. La
casilla se resuelve en el propio navegador antes de `window.print()` (mismo
mecanismo de `@media print` que ya oculta `.fuentes`/`.fuente-cita` hoy —
la implementación exacta se decide al construir esto).

---

## G. Fuera de alcance en esta fase

- Generación de imágenes por IA (necesita proveedor nuevo, no configurado;
  necesita diseño propio de aviso "no verificado").
- Búsqueda de imágenes en internet.
- Deduplicar imágenes repetidas entre fragmentos (sección E).
- Cambiar el umbral de relevancia de búsqueda (0,35) o qué fragmentos se
  citan — esta fase solo añade imagen a fuentes que YA se citan, no cambia
  qué se cita.

---

## H. Pruebas antes de dar esto por terminado

- Reindexar una muestra real de libros (al menos los ya usados como
  ejemplo: "Instalaciones eléctricas en edificios", REBT-2011, BOE-326,
  "Curso práctico...") y comprobar a mano que las imágenes extraídas son
  diagramas reales y no basura — no dar el filtro de tamaño por bueno sin
  mirar el resultado real.
- Pregunta real de punta a punta contra el Worker desplegado, con una
  pregunta que se sepa de antemano que cita una página con diagrama real,
  y comprobar en pantalla que la miniatura aparece y se ve bien.
- Comprobar el informe impreso: con la casilla marcada la imagen sale, sin
  marcar no sale, sin huecos raros en el PDF.
- Comprobar que una pregunta que cita solo páginas sin diagrama no muestra
  ninguna miniatura ni un hueco vacío en su lugar.

---

## I. Cómo se ejecuta esto

Este proyecto vive a caballo entre dos repos: el indexador y el Worker
viven fuera de Sagarde (`PROYECTO ELECTRICO/_INDEXADOR` y `_WORKER`, git
local sin remoto), la pestaña vive en el repo público de Sagarde. Parar y
confirmar con Bixente en estos puntos:

1. **Antes de fijar el umbral de tamaño mínimo de imagen**, enseñarle
   ejemplos reales extraídos (qué se queda dentro, qué se descarta) — es un
   criterio de calidad que le toca validar a él, no una decisión puramente
   técnica.
2. **Publicación a Sagarde**: Bixente ya autorizó (16/09/2026) comitear y
   publicar periódicamente mientras está fuera, revisando siempre con
   cuidado qué se sube (nunca `git add -A`) — se mantiene ese criterio
   aquí, no hace falta volver a pedir permiso para cada commit individual
   de esta fase, pero sí seguir revisando el diff antes de cada uno.
3. **Cualquier ambigüedad real** no cubierta ya en este documento.

---

## J. Ya verificado — para no repetir trabajo

- La cuenta de NVIDIA en uso no tiene modelo de generación de imagen
  (`google/diffusiongemma-26b-a4b-it` es texto, no imagen) — comprobado en
  vivo el 16/09/2026, no asumir lo contrario sin volver a comprobarlo si ha
  pasado mucho tiempo.
- `pdfplumber` (`page.images`) sí expone imágenes incrustadas reales en los
  PDFs de esta biblioteca, con coordenadas y tamaño — probado sobre 4 PDFs
  reales, ver sección C.
- Ningún libro de los 101 ya indexados es un escaneo puro sin texto real
  (mínimo real medido: 329 caracteres/página) — no hace falta diseñar un
  caso especial para "libro sin nada que sacar".
- R2 sigue descartado como almacén (pide tarjeta) — el índice de imágenes
  va a Workers KV igual que el de texto.
