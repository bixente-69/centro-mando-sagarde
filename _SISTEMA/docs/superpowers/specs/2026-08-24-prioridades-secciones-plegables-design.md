# Prioridades: secciones plegables para el encargado

**Fecha:** 24/08/2026
**Estado:** Diseño aprobado por Bixente, pendiente de plan de implementación.

## Contexto

La pestaña Prioridades (`bloque_prioridades()` en `panel_obra.py`) es hoy una
página de scroll interminable: KPI, estado de la obra, tareas manuales,
preguntas pendientes, preguntas del catálogo, avisos, la tabla "Qué hacer
ahora", la previsión de desbloqueos y, al final, las 6 secciones del
inventario completo (viables, bloqueados, otros gremios, sin clasificar, sin
revisar, terminados).

Bixente usa este panel como encargado de obra, no como programador: necesita
encontrar rápido "qué mando hacer hoy" y "qué está bloqueado", sin desplazarse
por cientos de filas de inventario para llegar a ello. El contenido y los
cálculos ya son correctos (ver
[[project-sagarde-prioridades-desde-la-base]]); lo que falla es la
presentación.

Validado con maquetas en el companion visual: formato de índice, agrupación
en dos bloques y comportamiento de plegado — ver capturas y decisiones más
abajo.

## Objetivo

Reorganizar visualmente la pestaña Prioridades para que:

1. Al entrar, se vea un resumen (los 8 KPI, sin cambios) y un índice de
   apartados con el número real de cada uno.
2. El resto de apartados empiece plegado; un clic los abre con el contenido
   íntegro, exactamente igual que hoy.
3. El índice separe "lo que hay que actuar hoy" de "lo que es consulta o
   referencia", para que el encargado no tenga que leer los 11 apartados para
   encontrar el que le importa.

## Fuera de alcance

- No se toca `priorizador_trabajos.py` ni ningún cálculo. Cero cambios de
  datos, cifras o clasificación.
- No se añade ninguna dependencia nueva (ni JS de terceros, ni CSS framework).
- No se persiste el estado abierto/cerrado entre visitas: cada carga de
  página empieza igual (plegado + índice), sin `localStorage`.
- No se toca ninguna otra pestaña del panel (Trabajos, Materiales, Riesgos…).
- No se decide aquí si el `<script>` de tareas manuales cambia — sigue
  exactamente igual, solo cambia el envoltorio visual que lo rodea.

## Diseño

### 1. Qué se queda siempre visible (no se pliega)

- La fila de 8 KPI, sin cambios.
- El banner "Estado de la obra" (cuando existe): es una línea, no aporta
  nada plegarlo y hoy ya funciona como aviso a primera vista.
- Los banners de "Avisos" (cuando existen): son avisos activos, no deben
  esconderse detrás de un clic.

### 2. El índice

Formato validado (opción B de la maqueta): una lista vertical de tarjetas,
una por apartado, con el número dicho en contexto ("21 tajos listos", "3
tajos esperando algo previo") en vez de una cifra sola — más legible desde el
móvil en obra que un número aislado.

El índice se divide en dos grupos con una etiqueta encima de cada uno:

**Para actuar hoy** (en este orden):
1. Tareas manuales
2. Preguntas pendientes antes de decidir
3. Qué hacer ahora: orden lógico de ejecución
4. Tajos bloqueados
5. Sin revisar nunca

**Consulta y referencia** (en este orden):
6. Preguntas sobre el catálogo de tajos
7. Qué se desbloquea al terminar cada cosa
8. Tajos viables (vista de inventario completo)
9. Otros gremios e interferencias
10. Sin clasificar o por verificar
11. Tajos terminados

Un apartado que hoy no se pinta por estar vacío (p. ej. "Preguntas sobre el
catálogo de tajos" sin ninguna pregunta) tampoco aparece en el índice — la
ausencia se hereda, no se declara aparte.

Color de cada entrada (mismo criterio que las maquetas y que la fila de KPI
ya usa hoy, reutilizando las variables CSS existentes `--ok`/`--warn`/
`--bad`/`--muted`, sin inventar una paleta nueva): verde cuando el apartado
está "tranquilo" (Qué hacer ahora, Preguntas en 0, Terminados), naranja para
Bloqueados, rojo para Sin revisar nunca, gris neutro para Otros gremios y el
resto de consulta.

Los apartados que hoy están dentro del bloque "Inventario completo de la
obra" (los 6 de `_SECCIONES_INVENTARIO`) dejan de estar agrupados bajo un
único encabezado: cada uno pasa a ser un apartado plegable de primer nivel,
repartido entre los dos grupos según si es información para actuar (2 y 5) o
de consulta (1, 3, 4 y 6). El criterio de qué cae en cada categoría no
cambia — sigue siendo el que ya está descrito y probado en
`priorizador_trabajos.py`.

### 3. Mecánica de plegado

Cada apartado pasa de:

```html
<div class="card"><h3>Título</h3>...contenido...</div>
```

a:

```html
<details class="card seccion-plegable" id="sec-<código>">
  <summary>Título <span class="badge">N</span></summary>
  <div class="seccion-contenido">...contenido idéntico al de hoy...</div>
</details>
```

Es el mismo widget nativo `<details>/<summary>` que el panel ya usa para
"Mostrar N tajos terminados" y "Ver ubicaciones afectadas" — no se introduce
ninguna librería ni framework de acordeón.

- Varios apartados pueden estar abiertos a la vez (no es un acordeón
  exclusivo): abrir uno no cierra los demás.
- Un clic en una fila del índice baja hasta el apartado **y lo abre** en el
  mismo gesto. Se implementa con un único bloque `<script>` compartido (no
  uno por fila) que escucha los clics del índice y hace
  `elemento.open = true` antes de que el navegador haga scroll al ancla. Si
  el JS no llegara a cargar, el enlace `href="#sec-..."` sigue funcionando
  como ancla normal — solo que el usuario tendría que pinchar una vez más
  para abrirlo. Nunca se rompe del todo.
- Sin persistencia: cada carga de página vuelve a "todo plegado + índice".

### 4. Principio de integridad: el número del índice no se declara aparte

Esto es lo más importante del diseño para este proyecto en concreto. La
cifra que aparece en el índice (p. ej. "3" en "Tajos bloqueados") se lee del
mismo recuento que ya usa la tabla de esa sección (`len(grupos)`,
`len(filas_dudas)`, etc.) en el mismo paso de generación — nunca un número
escrito o calculado por separado. Es exactamente la clase de fallo que este
proyecto ya ha sufrido con etiquetas y contadores desincronizados (ver
`CLAUDE.md` §2): un índice que dijera "3" mientras la tabla de debajo tiene 4
filas sería peor que no tener índice.

### 5. Qué no cambia

- ningún dato, cifra, columna, orden de filas dentro de cada tabla, ni texto
  de motivo/duda;
- el filtro LISTO/VERIFICAR de "Qué hacer ahora" sigue funcionando igual;
- las reglas de cuándo una sección se omite por estar vacía;
- el JSON `prioridades_trabajos.json` y todo lo que lo consume fuera del
  panel.

## Alcance del cambio en código

Todo el cambio vive en `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE
IA/panel_obra.py`:

- `bloque_prioridades()` — reordena el ensamblado final en los dos grupos y
  añade el índice.
- `_tabla_tareas_manuales`, `_tabla_preguntas_orden`, `_tabla_prevision` —
  cambian su envoltorio externo de `<div class="card">` a
  `<details class="card">`.
- El bloque de `dudas_html` y la tarjeta literal "Qué hacer ahora" (hoy
  inline en el f-string final) — mismo cambio de envoltorio.
- El bucle sobre `_SECCIONES_INVENTARIO` — en vez de concatenar las 6
  tarjetas en su orden fijo dentro de un único bloque "Inventario completo",
  construye un diccionario `html_por_codigo` y el ensamblado final coloca
  cada una en su grupo (actuar hoy / consulta) según el reparto de la
  sección 2.
- `ESTILOS` (CSS embebido) — añade el estilo del índice (dos columnas de
  etiqueta + lista), el marcador `▸`/`▾` de `<summary>`, y algo más de
  padding táctil para pulgar en móvil.

Ningún otro fichero cambia. `generar_panel()` sigue llamando a
`bloque_prioridades()` con la misma firma.

## Pruebas

`test_panel_prioridades.py` ya cubre casi todo el contenido con `assertIn` /
`assertNotIn` y comprobaciones de orden con `html.index(...)`; como el texto
no desaparece (solo cambia de envoltorio y de posición dentro de la página),
la mayoría deberían seguir en verde sin tocarlas. Los puntos a revisar
expresamente al implementar:

- `test_tarjeta_esta_entre_estado_de_obra_y_dudas` — comprueba
  `Estado de la obra < Tareas manuales < Preguntas pendientes...`; con el
  nuevo orden (Estado de la obra sigue primero, Tareas manuales y Preguntas
  pendientes son los dos primeros del grupo "Para actuar hoy") debería seguir
  cumpliéndose, pero hay que ejecutarla y confirmarlo, no darlo por hecho.
- Pruebas nuevas a añadir (con el espíritu de "probar por mutación" del
  proyecto):
  - el número que muestra cada entrada del índice coincide con el número de
    filas reales de datos de su sección (romper el cálculo a propósito y
    comprobar que la prueba lo nota);
  - una sección que no se pinta por estar vacía tampoco aparece en el
    índice;
  - los apartados 2 (Bloqueados) y 5 (Sin revisar) del inventario siguen
    apareciendo con su contenido íntegro aunque ya no estén dentro de un
    bloque "Inventario completo" único.

## Riesgos y mitigaciones

- **Riesgo:** reordenar visualmente los 6 bloques de inventario en dos
  grupos podría romper alguna prueba que asuma que van todos seguidos.
  **Mitigación:** ejecutar la suite completa tras el cambio, no solo los
  casos que ya existen para `bloque_prioridades`.
- **Riesgo:** el índice queda desincronizado si en el futuro alguien añade un
  apartado nuevo sin darlo de alta en el índice. **Mitigación:** el índice se
  genera recorriendo la misma lista de secciones que se renderizan, no una
  lista aparte — un apartado nuevo que no se registre en esa lista
  simplemente no se pinta tampoco, así que no hay forma de que exista un
  apartado sin su entrada en el índice.
