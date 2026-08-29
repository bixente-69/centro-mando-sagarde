# Diseño — Informe de obra a la carta

Fecha: 29/08/2026. Aprobado por Bixente tras brainstorming y mockup interactivo.

## Motivación

Bixente quería poder mandar el enlace de una obra a alguien (un cliente, un
subcontratista) sin que esa persona pudiera navegar al resto de obras. Tras
explorar el coste de dar acceso restringido (contraseñas, enlaces secretos,
usuarios), se decidió un enfoque distinto: en vez de dar acceso a la base
viva, Bixente genera él mismo un documento cerrado con exactamente lo que
quiere enseñar, y lo envía (por WhatsApp u otro medio) a quien corresponda.
El caso de uso principal es mandar a los oficiales presentes en una obra lo
que el encargado ha visto tras una revisión: avances, tajos bloqueados, qué
hacer, materiales.

## Objetivo

Un botón nuevo, "Informe de obra", junto al ya existente "Informe Ejecutivo
PDF" en el panel de cada obra (`panel_obra.py`). Al pulsarlo se abre un menú
de checkboxes para elegir qué secciones y subsecciones entran en el
documento, con vista previa antes de decidir, y salida en PDF A4 mediante el
propio diálogo de impresión del navegador.

## Alcance v1 — todas las secciones del panel

- Trabajos
- Materiales
- Personal
- Prioridades, con sus 5 subapartados seleccionables por separado: Estado del
  proyecto, Qué hacer ahora, Tajos bloqueados, Tareas manuales, Sin revisar
  nunca
- Riesgos
- Normativa
- Documentos
- Cierre

## Decisiones de arquitectura

### 1. Sin servidor, sin infraestructura nueva

Todo el flujo (selección, vista previa, generación del PDF) ocurre dentro del
navegador, sin depender de `panel_server.py`, sin servicios en la nube y sin
contraseñas nuevas. Funciona exactamente igual si Bixente hace doble clic en
`panel.html` desde su ordenador que si consulta el panel publicado por
internet desde el móvil estando en la obra.

Se descartó explícitamente:

- Un servidor local (`panel_server.py` + lanzador nuevo) que generara el PDF
  al vuelo con ReportLab: habría dado un informe "más vivo" solo en el
  ordenador, pero no resolvía el caso del móvil en la obra, que es el caso de
  uso principal.
- Un servicio en internet (función en la nube) que generara el PDF al
  instante también desde el móvil: exigía infraestructura nueva y una llave
  de acceso que proteger, desproporcionado para esta necesidad. Bixente
  eligió explícitamente la alternativa sencilla.

### 2. "Vivo" significa: tan fresco como la última regeneración del panel

El informe nace embebido dentro de `panel.html`, en el mismo instante en que
`generar_todos.py` ya regenera ese fichero tras aplicar una revisión. No hay
un nivel de frescura distinto para ordenador y para móvil: los dos leen la
misma foto, tomada la última vez que se procesó una revisión y se regeneró
el panel. Si Bixente necesita algo más fresco que eso en el móvil, la
respuesta es la misma de siempre: publicar antes de ir a la obra o nada más
llegar.

### 3. Capa de datos compartida por sección — evita guardas compartidas

Se extraen funciones — una por sección y por subapartado de Prioridades —
que calculan su contenido a partir de `ficha_obra.json` y el historial
validado. Hoy esas mismas cifras se calculan de forma mixta dentro de
`panel_obra.py`: `bloque_riesgos()` y `bloque_cierre()` ya son funciones
propias; `bloque_prioridades()` es una función propia pero mezcla sus 5
subapartados en un único bloque HTML; Trabajos, Materiales, Personal,
Documentos y Normativa se generan inline, sin función propia.

El refactor extrae una función por sección/subsección, de modo que:

- `panel_obra.py` las usa para pintar el HTML del panel, igual que hoy.
- El mismo resultado se serializa a un bloque JSON embebido en `panel.html`
  (p. ej. `<script id="datos-informe" type="application/json">`), que
  alimenta el selector del informe a la carta.

Ninguna cifra (tajos bloqueados, porcentaje de avance, etc.) se calcula por
dos caminos independientes. Es la familia de fallo que ya ha costado caro en
este proyecto (etiquetas de tajo desincronizadas, excepciones del catálogo
tras una guarda obsoleta), y este diseño la evita por construcción.

### 4. Selector, vista previa y salida — mismo patrón que `generador_revisiones.html`

- Menú de checkboxes agrupados por sección, con una casilla de "marcar todo
  el grupo" para Prioridades (igual que `toggleGroup()` en el generador de
  revisiones).
- Botón "Vista previa": monta una página que solo contiene las secciones
  marcadas, con la identidad visual del informe ejecutivo (tipografía IBM
  Plex Sans, colores corporativos, cabecera con nombre de obra y fecha de
  generación).
- Botón "Volver": regresa al menú de selección sin perder lo marcado.
- Botón "Imprimir / Guardar como PDF": dispara `window.print()` (A4) —
  exactamente las mismas condiciones de salida que ya usa el generador de
  revisiones. No se usa ReportLab en este camino.

### 5. Selección recordada por obra

La última selección de checkboxes se guarda en `localStorage`, con clave por
obra, para no tener que volver a marcar todo cada vez que se genera un
informe de la misma obra.

### 6. Identidad visual compartida, no motor de render compartido

El informe ejecutivo sigue generándose con ReportLab (Python); este informe
a la carta se genera con HTML/CSS impreso desde el navegador. Para que se
"parezcan" sin duplicar el motor de PDF, se extrae una referencia mínima de
estilo común (colores, tipografía, tratamiento de cabecera) que se aplica en
ambos sitios. Es una duplicación aceptada de presentación (CSS vs.
ReportLab), no de cálculo — el dato siempre viene de la capa compartida del
punto 3.

## Fuera de alcance (v1)

- Generación instantánea desde el móvil sin haber publicado antes (exigiría
  infraestructura en la nube con autenticación; descartado por Bixente por
  desproporcionado frente al beneficio).
- Unificación completa del motor de render entre el informe ejecutivo
  (ReportLab) y este informe a la carta (CSS/impresión) — sigue siendo,
  como ya se decidió para panel/informe ejecutivo, una tarea aparte.
- Cualquier mecanismo de acceso restringido a la base viva (contraseñas,
  enlaces secretos, usuarios) — descartado como enfoque general al principio
  de este diseño en favor de "Bixente envía lo que decide enseñar".

## Reparto de trabajo

Claude diseña, extrae la capa de datos compartida del punto 3 y define el
contrato exacto de cada función de sección. Codex ejecuta las tareas
mecánicas concretas (extracción de las funciones que faltan, HTML/CSS/JS del
selector y la vista previa, tests) bajo instrucciones explícitas de Claude,
en piezas secuenciales — nunca a la vez sobre los mismos ficheros, para no
repetir el choque de trabajo duplicado que ya ha ocurrido en este proyecto
cuando varios procesos escriben el mismo repo a la vez.

## Riesgos y verificación

- Verificar que las obras no implicadas no cambian sus KPI tras el refactor
  de `panel_obra.py` (Mungia, Gernika, Bolueta, Obispo Orueta cerrada, OBRA
  PRUEBA).
- Probar por mutación: romper a propósito el cálculo de una sección y
  comprobar que el test correspondiente se entera.
- Confirmar que el bloque JSON embebido y el HTML visible del panel muestran
  siempre el mismo desglose `x`/`m`/`/`/vacío para cada sección.
- Comprobar en un navegador real, tanto abriendo `panel.html` con doble clic
  como consultando el panel publicado en GitHub Pages desde un móvil, que el
  botón, el menú, la vista previa y la impresión funcionan igual en los dos
  casos.
