# Plan de trabajo por IAs — «Personal en obra» (23/10/2026, v3)

Aplicación de campo para anotar qué trabajadores hay cada día en cada obra, con base de datos acumulada, horario
semanal, horas extra, listados por semana/mes/año/obra y gráfica de impacto en la pestaña **Personal** y en el
**Informe de obra**, más un control de **quién trabaja más para Sagarde y quién tiene más impacto**.

Este plan se reparte en **conversaciones separadas** (M, P0…P7) sin perder el hilo: cada paquete tiene su entrada, su
salida, su verificador y un **prompt de arranque** que se pega tal cual en una conversación nueva. El hilo común es el
contrato de datos que cierra P0.

Proceso aplicado: `D:\Nueva carpeta\OneDrive\PROYECTO IA REPARTO\PROCESO_IAS.md` (cascada de menor a mayor coste,
verificador objetivo antes de delegar, Claude diseña y verifica).

**Historial de cambios**
- **v2 (23/10/2026):** los datos de personal **se publican** (uso personal de un solo usuario, informe de obra desde la
  tablet en cualquier sitio); el cálculo es **una sola implementación en JavaScript** compartida por la app, el panel y el
  informe; se añade el **ranking global de Sagarde**.
- **v3 (23/10/2026):** (a) el trabajador se identifica por su **nombre**, tal como lo escribe Bixente, y punto: sin concepto
  de «alias», sin avisos ni validaciones sobre si es mote o nombre real (él sabe quién es quién); (b) **primero la maqueta**:
  se ve cómo queda antes de tocar el entorno, y la construcción va aislada para no estropear lo que ya funciona.

---

## 0. Regla de oro: no estropear lo que ya funciona, solo mejorarlo

La app actual (panel de obra, pestaña Personal, generador de revisiones) funciona bien. Este plan **solo añade**:

1. **Maqueta antes que nada (paquete M).** Una página suelta con datos inventados que se abre en la tablet o el PC y
   enseña cómo quedarían la app de jornada, la pestaña Personal, el Informe de obra y el ranking. Vive **fuera del
   repositorio** (`D:\Nueva carpeta\OneDrive\PROYECTO PERSONAL EN OBRA\maqueta\`, accesible desde OneDrive en la tablet), así
   que no se publica, y no está conectada a nada. **Bixente la aprueba o la
   corrige antes de que P0 cierre la especificación.**
2. **Construcción aislada:** P1–P3 son ficheros nuevos que no dependen del código existente: se construyen en una **zona de
   trabajo fuera del repositorio** (`D:\Nueva carpeta\OneDrive\PROYECTO PERSONAL EN OBRA\staging\<paquete>\`), con su encargo en
   la carpeta del trabajador y su **verificador fuera** de ella (`staging\_verificadores\`, para que el trabajador no vea las
   cifras esperadas). P4–P5b sí necesitan `panel_obra.py` y el portal: se hacen en una **rama y un worktree propios**
   (`personal-en-obra`, recomendación de Claude). En los dos casos nada llega a `main` ni a GitHub Pages hasta que Bixente dé el
   visto bueno, y Codex no queda bloqueado por el árbol sucio de la sesión paralela (ver 0.1). Límite honesto: ni la zona de
   trabajo ni el worktree contienen los Excel, PDF u hojas de obra; sirven para código y pruebas con datos inventados. La
   comprobación contra las obras reales se hace en P6/P7, con todo ya fusionado **en local y sin publicar**.
3. **Solo ficheros nuevos y huecos mínimos.** `generador_revisiones.html` **no se toca**. En `panel_obra.py` (149 KB) entra
   solo la llamada a un módulo nuevo. Las demás pestañas no cambian.
4. **Una obra sin datos de personal se ve exactamente como hoy** (la tabla de la hoja `Personal` del Excel, o «Sin datos…»).
5. **Prueba de no regresión:** el `panel.html` y el resto de salidas de las obras no implicadas deben ser **idénticos byte a
   byte** antes y después. Si se mueve algo, hay efecto colateral.
6. **Marcha atrás:** la fusión a `main` es una sola operación que se puede deshacer con `git revert`.

---

## 0.1 Prerrequisitos y trampas ya detectadas

1. **El árbol git NO está limpio (comprobado el 23/10/2026).** Hay cambios sin commitear que no son de esta
   conversación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py` (+35/−4 líneas) y
   `tests/test_cutover_generar_todos.py` (+141). Al abrir la sesión de este plan el árbol estaba limpio, así que
   casi seguro es otra sesión trabajando (norma del proyecto: no es basura que limpiar; confirmarlo con Bixente
   antes de tocarlo). Consecuencias:
   - **Codex aborta** si `git status` está sucio. Con el worktree (0.2) no afecta a P1–P5b.
   - **P6 toca `generar_todos.py`**: no empieza hasta que ese trabajo esté commiteado, y al fusionar se resuelven los
     conflictos con sus cambios.
2. **El repositorio de GitHub es público** (`bixente-69/centro-mando-sagarde`, comprobado el 14/09/2026; reverificar con
   `gh repo view` al arrancar P0). Decisión de Bixente (D1): los datos de personal **sí se publican**, con el nombre tal como
   él lo escribe. El esquema **no tiene** DNI, teléfono ni correo (no hacen falta).
3. **No lanzar `Actualizar_Sagarde.bat` mientras haya un paquete en vuelo** (publicaría trabajo a medias, ya ocurrió dos
   veces).
4. **Un solo trabajador sobre el árbol a la vez**, aunque toquen ficheros distintos. Orden secuencial M→P0→P7.
   Al cerrar cada paquete: `git status` revisado y commit que decide Bixente, antes de lanzar el siguiente.
5. Pruebas con `unittest` de la biblioteca estándar en Python (no pytest, no dependencias nuevas) y `node` para el JS.
   Python: `py -3.11`.
6. Todo en D:. Los encargos y logs de `ia_dispatch.py` fuera del repo (`D:\IA_REPARTO\…`).
7. **Los trabajadores IA nunca ven datos reales.** Fixtures con nombres inventados.
8. **«Generado pero nunca publicado»** es una trampa ya vista (`obras_revisiones.js`, `static/chart.min.js`): el
   `.gitignore` es lista blanca (`*`). Cada fichero nuevo de este proyecto tiene que entrar en la lista **y** tener una
   prueba de que de verdad se publica. Ojo: `!*.html` (línea 8) deja pasar **cualquier HTML** del repo, así que un borrador
   o una maqueta HTML se publicaría sin avisar; los `.js` y `.json` sí necesitan entrada propia (por eso `personal_estado.js`
   hay que declararlo, como se hizo con `obras_revisiones.js`).

---

## 1. Qué hay hoy (hechos comprobados, no suposiciones)

| Hecho | Dónde |
|---|---|
| La pestaña Personal solo pinta la hoja `Personal` de `FICHA DE OBRA.xlsx`; en todas las obras revisadas sale «Sin datos en la ficha de obra» | `lectores.py:leer_ficha` → `panel_obra.py:2011` (`tabla_ficha`), vista `v-personal` en `:2422`, checkbox del informe `data-seccion="personal"` en `:2359` |
| El generador de revisiones es un HTML único (1,38 MB), sin servidor; guarda su configuración en `localStorage` (claves `sgd_rev_recents`, una por obra) | `generador_revisiones.html:1660-1700` |
| «La última revisión» llega al generador por `obras_revisiones.js`, que construye `generar_todos.py` desde las fichas | `generador_revisiones.html:358`, `generar_todos.py:984` |
| Garajes y viviendas son modos separados del generador (`setModo`) con ficha propia (`ficha_garajes.json`) | `generador_revisiones.html` paso 1 |
| `.gitignore` es lista blanca: lo no listado no se publica | `.gitignore:2` (`*`) |
| El `panel.html` de cada obra es estático y se publica; Chart.js va en local | `.gitignore` (comentario de `static/chart.min.js`) |
| Colores y tipografía del panel: `--header:#0b1f3a`, `--accent:#f5a524`, `--accent2:#2e7dd7`, fuente del sistema | `panel_obra.py:47-53` |
| Hay Node 24 y Playwright (Python) en este PC → se puede probar la app y el cálculo de forma automática | comprobado 23/10/2026 |

---

## 2. Decisiones

| # | Pregunta | Estado / recomendación |
|---|---|---|
| **D1** | Privacidad: ¿se publican los datos? | **DECIDIDA el 23/10/2026 por Bixente: sí, se publican.** Es una app personal de un solo usuario; necesita el informe de obra en cualquier sitio con la tablet; el fin es llevar el control de quién trabaja más para Sagarde y quién tiene más impacto. El trabajador se identifica por su **nombre**, tal como lo escribe él. |
| **D2** | ¿Dónde vive la app? | Un **HTML único propio** `generador_personal.html` junto al generador de revisiones, mismo estilo. Carga el estado publicado si hay red; **sin red usa la última copia guardada en el aparato**. Sin datos dentro del fichero. |
| **D3** | Horario semanal: ¿por obra o por trabajador? | Plantilla L–D **por obra** (horas por día), con **excepción opcional por trabajador**. **Jornada base: 7,5 h** (dato de Bixente, 23/10/2026). Por defecto se aplica de **lunes a viernes** (supuesto: confirmar) y sábado y domingo quedan sin horario, así que todo lo que se anote esos días cuenta como extra. Editable por obra. «Día extra» = día fuera de horario; «horas extra» = suma sobre los 7,5 h. En un día sin horario la app no guarda 0: obliga a poner las horas (el primer toque fija 7,5 h). |
| **D4** | ¿Qué es «% de impacto»? | Horas-hombre del trabajador ÷ horas-hombre totales, a **dos niveles**: en una obra y en **todo Sagarde**. Gráfica de barras ordenadas. Alternativa: % de días presente. |
| **D5** | ¿Se apuntan subcontratas / otros gremios? | No: solo gente que haya trabajado en Sagarde. El campo `empresa` queda opcional. |
| **D6** | ¿Ranking global de Sagarde (todas las obras)? | **Sí.** Es lo que describes como fin («quiénes trabajan más para Sagarde»). Tarjeta en el portal con filtro semana/mes/año. Si no lo quieres, se quita el paquete P5b. |

D2–D6 se revisan sobre la maqueta (paquete M) y se aplican con la recomendación si no se dice otra cosa; P0 las deja escritas.

Fuera de alcance, a propósito: importar nada de la zona personal de nóminas/vida laboral, inventar trabajadores u horarios,
y tocar ninguna obra que no sea la que se pruebe.

---

## 3. Arquitectura propuesta (borrador; lo cierra y firma P0)

```
TABLET / MÓVIL                                      PC (D:)  — todo sale con Actualizar_Sagarde.bat
generador_personal.html                             personal_catalogo.json   ← nombre, categoría (id estable T0001…)
  · carga personal_estado.js publicado              <obra>/INFORME SAGARDE IA/personal_obra.json
    (o la última copia local si no hay red)             · horario_semanal
  · elige obra + ámbito (viviendas | garajes)           · jornadas[{fecha, ámbito, presentes[{id, horas, extra}]}]
  · carga la ÚLTIMA jornada de ese ámbito           personal_jornadas.jsonl  ← trazabilidad aditiva
  · marca X a quien está hoy                        personal_obra.py         ← ingerir / fusionar / exportar-estado
  · desplegable del catálogo + «Nuevo»              personal_calculo.js      ← UNA sola implementación del cálculo
    (avisa de nombres parecidos)
  · horario del día + días/horas extra              Publicado:
  · guarda en el aparato                              personal_estado.js (para la app)
  · pantalla «Informe de personal»: publicado         panel.html de cada obra (pestaña Personal + Informe de obra)
    + jornadas aún sin ingerir, con personal_calculo  tarjeta «Personal Sagarde» en el portal (ranking global)
  · Exportar jornada (JSON) ───────────────────►    ingerir (idempotente: clave obra+ámbito+fecha)
```

Por qué el cálculo es **una sola implementación en JS** (`personal_calculo.js`): la misma cuenta la necesitan la app
(también con jornadas aún sin publicar, para sacar el informe en la tablet nada más terminar el día), el panel y el
informe. Dos implementaciones (una en Python y otra en JS) acaban divergiendo. Python solo valida, ingiere y calcula unos
**totales de control** sencillos con los que la guarda de P6 compara lo que sale del JS (doble cálculo, como ya hace el
proyecto con las fichas).

Reglas de datos heredadas del proyecto (se escriben en el contrato):
- **Se guarda lo medido, se recalcula lo derivado:** se persisten jornadas; semanas, meses, totales y % se calculan.
- **Un dato que falta no es cero:** hora no anotada ≠ `0`. Un periodo sin jornadas dice «sin jornadas», no «0 h». Un recuento
  0 es señal de alarma, no de «no aplica».
- **Algo declarado que el motor ignora en silencio es la familia de fallos de este proyecto:** cada paquete lleva
  prueba por mutación.
- Garaje y vivienda **separados** (igual que las revisiones): la «última jornada» es por obra **y ámbito**.
- **Esquema cerrado:** un campo fuera del esquema se **rechaza con aviso**, no se ignora en silencio. `nombre` es un campo
  más del esquema y es texto libre.
- **Nombres repetidos o escritos distinto** («Pepe», «pepe», «Pepe el de Bilbao») falsean el ranking. Defensa: desplegable
  primero, aviso de «se parece a…» al crear (sin mayúsculas ni acentos) y comando `fusionar` en el PC que reasigna las
  jornadas del duplicado y lo deja trazado.

---

## 4. Reparto por conversaciones

Orden estricto, un paquete por conversación. `Cascada` = valor de `--cascade` de `ia_dispatch.py`.

| Paquete | Conversación | Quién | Cascada | Ficheros que toca | Verificador (exit 0 = bien) | Depende de |
|---|---|---|---|---|---|---|
| **M** | Maqueta visual | **Claude** | — | solo `PROYECTO PERSONAL EN OBRA/maqueta/` (fuera del repo) | la ve y la aprueba Bixente | — |
| **P0** | Diseño y contrato | **Claude** (mayor) | — | spec, contrato, fixtures, tests y verificadores | referencia = 100 % y esqueleto = falla | M aprobada, D2–D6 |
| **P1** | Núcleo de datos | agy → codex | `agy,codex:low` | `personal_obra.py` (nuevo) | `unittest` de P0 (casos ocultos) | P0 |
| **P2** | Cálculo compartido (JS) | gemini → agy → codex | `gemini,agy,codex:low` | `personal_calculo.js` (nuevo) | script `node` con cifras doradas | P0 |
| **P3** | App móvil/tablet | agy → codex + Claude verifica | `agy,codex:low` | `generador_personal.html` (nuevo) | Playwright 375×812 y 768×1024 + exportación válida para P1 | P0, P1, P2 |
| **P4** | Pestaña Personal del panel | codex + Claude verifica | `codex:low` | `panel_personal.py` (nuevo) + hueco mínimo en `panel_obra.py` | tests del panel + huella de obras ajenas | P1, P2 |
| **P5** | Informe de obra | codex + Claude verifica | `codex:low` | `panel_personal.py`, hueco en `panel_obra.py` | tests del informe + tablet y A4 | P4 |
| **P5b** | Ranking global de Sagarde | codex + Claude verifica | `codex:low` | tarjeta/página nueva en el portal | tests de la página + huella del resto del portal | P2, P5 |
| **P6** | Integración y guardas | **Claude** (+ codex en lo mecánico) | `codex:low` solo mecánico | `generar_todos.py`, `.gitignore`, auditor, skill, mapa mental | suite completa + guardas de publicación y de esquema | P1–P5b y árbol limpio |
| **P7** | Cierre y piloto real | **Claude** | — | solo lectura + informe | suite completa + antes/después | P6 |

Por qué así: M, P0 y P6 son diseño y guardas (Claude). P1/P2 son funciones con especificación y tests (lo que mejor sale en
el banco con `agy`/`codex:low`). P3 es la única pieza visual: la hace el trabajador, pero **Claude la mira en el
navegador** antes de darla por buena. P4/P5 comparten fichero (`panel_obra.py`, 149 KB): por eso la lógica va en un
módulo nuevo y en `panel_obra.py` solo entra el hueco mínimo, y **nunca en paralelo**.

---

## 4b. Estado de ejecución (se actualiza al cerrar cada paquete)

**Prompts por paso (cada paso = una conversación nueva, con todo el contexto dentro):** `D:/Nueva carpeta/OneDrive/PROYECTO PERSONAL EN OBRA/prompts/` — empieza por `00_LEEME_ORDEN_Y_USO.md`; el testigo entre conversaciones es `ESTADO.md` (25/10/2026: pasos 01, 01b (horario propio por trabajador) y 02 (legibilidad de P1 y P3) ejecutados el 24/10/2026; paso 03 (pestaña Personal del panel), paso 04 (sección Personal del Informe de obra), paso 05 (ranking global y su acceso en el portal) y paso 06 (integración y guardas) ejecutados el 25/10/2026 en la rama `personal-en-obra`, ya fusionada en `main` en local (sin `push`); paso 07 ejecutado a medias el 25/10/2026 y sustituido por la **fase 08** (ver `prompts/ESTADO_08.md` y `prompts/00_LEEME_ORDEN_Y_USO.md`)).

| Paquete | Estado | Quién lo hace | Dónde |
|---|---|---|---|
| M Maqueta | Hecha; pendiente del visto bueno de Bixente | Claude | `PROYECTO PERSONAL EN OBRA\maqueta\maqueta_personal.html` |
| Revisión crítica del plan | **Hecha** (gemini, 1 ronda, 37 s) | `gemini` | `staging\revision_plan\informe_revision.md`; contrastada por Claude (ver abajo) |
| P2 (cálculo JS), piloto del reparto | **Hecho y verificado** (gemini, 1 ronda, 106 s, 30 k tokens) | `gemini` | `staging\p2_calculo\personal_calculo.js` (386 líneas); verificador en `staging\_verificadores\verificar_p2.js` |
| Mejoras de la maqueta (8) | **Hechas y verificadas** (gemini, 1 ronda, 174 s, 45 k tokens) | `gemini` | Instaladas en `maqueta\maqueta_personal.html` (la anterior en `maqueta\_anteriores\`); capturas en `maqueta\_capturas\`. Verificador `staging\_verificadores\verificar_maqueta.py` (Playwright, 390 y 1100 px). Claude lo repitió y vio las capturas: encontró un fallo propio (el pie del informe mostraba `0` en una columna sin datos), añadió la prueba, comprobó que fallaba y lo corrigió |
| P0 Especificación y contrato | **Aprobada por Bixente el 23/10/2026** (propuestas A, B, C y D incluidas, v1 completa) | Claude + revisión `gemini` (2 rondas, 183 s) | `docs/superpowers/specs/2026-10-23-personal-en-obra-design.md` (§14 = revisión; §15 = ajustes posteriores a la aprobación; §7b = firma de la API) |
| P1 `personal_obra.py` | **Hecho y verificado (+ horario propio, paso 01b, 24/10/2026)** (origen: `codex:low` a la 1.ª ronda, 240 s; `gemini` y `agy` fallaron 3 rondas por una contradicción mía, ver abajo; 01b: `codex:low` a la 1.ª ronda, 103 s) | `ia_dispatch.py` | `staging\p1_datos\personal_obra.py` (**1.033 líneas desde el paso 02: formato `black`, docstrings y comentarios en castellano; el código es idéntico al denso por árbol sintáctico**); verificador `staging\_verificadores\verificar_p1.py`: **82 pruebas `unittest`, 0 fallos**; mutaciones reescritas contra el fichero final (`staging\_verificadores\mutaciones_p1.py`): **59/59 detectadas** (21 ideas del paso 02 + 38 del 01b). Contrato del horario propio en §17 de la spec. Herramientas del paso 02: `staging\_verificadores\LEEME_legibilidad.md` |
| P3 `generador_personal.html` | **Hecho; revisado (paso 01) y ampliado con horario propio, espera de 4 s y «Empezar de cero» con pregunta (paso 01b, 24/10/2026)**: pasa `verificar_p3.py` (77 escenas + 6 comprobaciones estáticas, ≈ 7 min); mutaciones 92/93 del paso 01 y **64/67 del 01b** (3 equivalentes demostrados). Visto bueno visual de Bixente al boceto y a las capturas (24/10/2026). **Paso 02 (24/10/2026): legible y comentada** (prettier + plantillas largas partidas + 124 comentarios y 9 secciones; árbol JS, CSS y marcado equivalentes a la versión densa; lotes exportados idénticos byte a byte); mutaciones reescritas (`mutaciones_p3.py`): **151/155** (4 equivalentes). | `ia_dispatch.py` (+ Claude) | `staging\p3_app\generador_personal.html` (**1.864 líneas, 71 KB desde el paso 02**; antes 458 líneas, 37,5 KB). 01b: `codex:low` ganó las dos tandas a la 1.ª ronda (A: 297 s, tras 3 rondas fallidas de `gemini`; B: 360 s); lotes idénticos byte a byte a los de antes sin horarios propios (`comparar_lotes_antes_despues.py`). **Lecciones del 01b:** `codex:low` cambió comportamiento para pasar una prueba mía mal escrita, metió cirugía de DOM en `render()` y dijo «guardado» sin comprobarlo: se corrigió leyendo el diff. Detalle en `PROYECTO PERSONAL EN OBRA\prompts\ESTADO.md` |
| P4 `panel_personal.py` + hueco en `panel_obra.py` (pestaña Personal) | **Hecho y verificado (paso 03, 25/10/2026) en la rama `personal-en-obra`** (worktree `D:\Nueva carpeta\worktrees\personal-en-obra`; 4 commits sobre `20012e3`, **nada en `main`, sin `push`**). Hueco: `generar_panel(…, personal=None, personal_obra_id=None)`; sin datos el panel sale **byte a byte igual** que antes (4 casos × 3 formas de llamarlo). Módulo: `codex:low` a la 1.ª ronda (147 s; `agy` falló 3 rondas, 1.530 s); corregido por Claude tras leerlo (plantilla en una pasada, errores del JS en una función, KPI en minúscula como la maqueta). Verificación: `tests/test_panel_personal.py` (36 pruebas) + `verificar_p4.py` (Playwright, cifras contra un cálculo independiente en Python, paseo al azar, 320/390/820 px, 4 zonas horarias) + **41/41 mutaciones detectadas**; suite del motor 1.113/1.114 (la que falla necesita ficheros reales de Mungia). El informe a la carta **no** cambia (es P5) | Claude (hueco, verificador, correcciones) + `codex:low` | Rama `personal-en-obra`; verificadores y logs en `PROYECTO PERSONAL EN OBRA\staging\_verificadores\` y `staging\_logs\`; capturas en `PROYECTO PERSONAL EN OBRA\capturas_p4\` |
| P5 `informe_personal` + hueco en `panel_obra.py` (sección Personal del Informe de obra) | **Hecho y verificado (paso 04, 25/10/2026) en la rama `personal-en-obra`; commit `857c9da`** (permiso de Bixente; sin `push`, nada en `main`). El informe se genera en el NAVEGADOR (`generarVistaPreviaInforme` + `document.write`): la sección es un fragmento autocontenido con scripts (CSS + `personal_calculo.js` + JS) y controles de periodo/ámbito dentro de la vista previa que no se imprimen; matriz trabajador × columnas de `PersonalCalculo.matriz` (> 12 columnas = varias tablas), pie «Total», barras y nota de redondeo. El JS del panel no se toca; hueco de 21 líneas. Sin Personal marcado el documento sale **byte a byte igual** (con o sin datos). La pestaña (P4) sigue idéntica byte a byte tras el refactor (ayudas compartidas). Verificación: `tests/test_panel_personal.py` = 48 pruebas + `verificar_p5.py` (cifras contra cálculo independiente en Python, **PDF A4 leído con PyMuPDF**, 820/390 px) + **34/38 mutaciones** (4 explicados: 2 equivalentes demostrados en Chromium, 1 sin importancia práctica, 1 no cubierto). `agy` a la 2.ª ronda (1.306 s); Claude corrigió una regla de impresión que `agy` incumplió y el verificador no miraba. | Claude (hueco, verificador, correcciones) + `agy` | Rama `personal-en-obra`; verificadores y logs en `PROYECTO PERSONAL EN OBRA\staging\_verificadores\` y `staging\_logs\`; capturas en `PROYECTO PERSONAL EN OBRA\capturas_p5\` |
| P5b `personal_sagarde.html` + acceso en el portal (ranking global de Sagarde) | **Hecho y verificado (paso 05, 25/10/2026) en la rama `personal-en-obra`; commit `a61d9d9`** (permiso de Bixente; sin `push`, nada en `main`). Página autocontenida junto a `generador_revisiones.html`: `personal_calculo.js` (`<script src>` relativo) + `personal_estado.js?v=` (dinámico, sin `fetch`); Semana/Mes/Año/Todo con flechas, KPI, tabla (#, nombre, horas, días, %, chips por obra) y barras de impacto; incluye obras cerradas; «Sin jornadas…» nunca 0; mensajes legibles sin fichero / versión / obras / fechas / obra ilegible. Acceso en el portal = fila nueva «Personal Sagarde · ranking» en «Aplicaciones y paneles» y en `APLICACIONES/index.html` (14 líneas en `sagarde_portal.py` + 4 tests): sin la página el portal sale **idéntico byte a byte**; con ella cambian solo esa fila y los contadores derivados (5→6 accesos). Verificación: `verificar_p5b.py` (Playwright; cifras a mano Ana 36 h / Beto 21 h / Carlos 8 h + cálculo independiente en Python, 5.841 comprobaciones en 26 s, 3 zonas horarias, 320/390/820/1280 px) + **40/40 mutaciones de la página** + 5/5 del hueco del portal. `gemini` a la 1.ª ronda (110 s, 35 k tokens); Claude escribió HTML/CSS/verificador, limpió 3 flecos del código de `gemini` y el hueco del portal. | Claude + `gemini` | Rama `personal-en-obra` (sin commitear); verificadores y logs en `PROYECTO PERSONAL EN OBRA\staging\_verificadores\` y `staging\_logs\`; capturas en `PROYECTO PERSONAL EN OBRA\capturas_p5b\` |
| P6 Integración y guardas | **Hecho y verificado (paso 06, 25/10/2026) en la rama `personal-en-obra`; 4 commits (`d649af8`, `1522f9d`, `48ea367`, `3c1eb90`) y un merge de `main` (`77760a8`)**, permiso de Bixente («solo en la rama»); sin `push`; **fusionada después en `main` (avance rápido, `main` = `3c1eb90`) con el «sí» expreso de Bixente, sin `push`: suites del árbol real 1.273 y 98 OK**. `personal_integracion.py` (estado con TODAS las obras, filas para el panel, alta de obra, auditoría, CLI); cableado en `generar_todos.py` (un fallo de personal nunca tumba un panel) y `regenerar_obra.py` (regenerar una obra no encoge el estado); 6 líneas nuevas del `.gitignore` con prueba de que cada fichero se publica; auditor con nivel «error» (esquema, DNI/teléfono/correo, ficheros, doble cálculo con node) que detiene `Actualizar_Sagarde.bat` con código 3; `Ingerir_Personal.bat`; verificadores de P1/P2/P3 en `tests/`; skill `sagarde-personal`; mapa mental. Verificación: suite de la rama 1.273 pruebas (1 error ya existente en `main` sin datos reales) + 98 del motor; **48/48 mutaciones** de las guardas; las 7 obras reales regeneradas con el código de `main` y con el de la rama: 68/69 ficheros idénticos byte a byte (el otro, solo el sello de hora). Hallazgo: la tablet solo ofrece obras con `personal_obra.json` → `iniciar-obra`. | Claude | Rama `personal-en-obra`; detalle en `PROYECTO PERSONAL EN OBRA\prompts\ESTADO.md` («Paso 06»); herramientas y logs en `D:\bench_ias\_p6\` |
| P7 Piloto real (primera parte) | **Hecha a medias el 25/10/2026 con Bixente, SIN publicar.** Foto «antes» de 83 ficheros; Olabeaga dada de alta y con la jornada de Asensio ingerida y regenerada; cifras comprobadas a mano en la pestaña y el informe; las demás obras idénticas (todos los cambios son de Olabeaga); suites del árbol real 1.273 y 99 OK. **El piloto destapó 5 peticiones suyas y un giro de fondo** («el control horario NO es una app suelta, es una aportación de datos al entorno Sagarde, como el generador de revisiones»): se sustituye `Recibir jornadas`/carpeta propia por «fichero `CONTROL HORARIO` en `REVISIONES` → "actualiza la obra" → `.bat`». Ver `…/specs/2026-10-25-personal-en-obra-repaso-integracion.md`. | Claude | Detalle en `PROYECTO PERSONAL EN OBRA\prompts\ESTADO.md` («Paso 07») y datos reales en `…\piloto_real\` |
| **Fase 08** (integración en el entorno, 6 conversaciones, en orden) | **Pendiente.** Testigo corto: `PROYECTO PERSONAL EN OBRA\prompts\ESTADO_08.md`; prompts `08a`…`08f` (compuestos desde `prompts\_fuentes_08\`). Rama de trabajo `personal-integracion` (se crea en 08a). | Claude (+ IAs con datos inventados) | `PROYECTO PERSONAL EN OBRA\prompts\` |
| 08a Núcleo de datos y lector | Pendiente: P1 (`renombres`, `altas`, `nombres_anteriores`, SHA en la traza, extra derivado) + `lector_control_horario.py` (detectar → simular → aplicar) | Claude + `gemini,agy,codex:low` | — |
| 08b Enganche | Pendiente: `actualizar_obra.py`, `regenerar_obra.py`, `generar_todos.py` (`.bat`), auditor, estado con todas las obras, retirar `Ingerir_Personal.bat`/`ingerir`/`iniciar-obra`; prueba de que `REVISIONES` no se contamina | Claude (sin IAs) | — |
| 08c App: nombres, base, altas | Pendiente: lápiz (renombres), desplegable completo, «Añadir varios»; pregunta de producto: campo Empresa | Claude + `gemini,codex:low` | — |
| 08d App: Enviar al PC, textos, día nuevo | Pendiente: nombre `CONTROL HORARIO <OBRA> <DDMMAAAA>.json`, pantalla «Enviar al PC», textos de electricista + guarda de lenguaje, día nuevo precargado | Claude + `gemini,codex:low` | — |
| 08e Portal, skills, cierre técnico | Pendiente: «Base de trabajadores», skills fundidas, mapa mental, principio en el `CLAUDE.md`, suites, fusión local | Claude | — |
| 08f Piloto 2 y publicación | Pendiente (con Bixente): sus datos reales (`piloto_real\`) por el camino nuevo, `.bat` con su «sí», web (200), tablet, cierre | Claude | — |

**P1, lo que se aprendió (23/10/2026).** `gemini` (3 rondas, 983 s) y `agy` (3 rondas, 1522 s) fallaron la misma prueba (`nombre_parecido`); `codex:low`
pasó a la primera. No era un fallo de los trabajadores: mi encargo y mi verificador decían reglas distintas. Se fijó la regla prudente (§15 de la spec).
Revisión posterior de Claude sobre el código ganador, con cuatro correcciones propias (regla de 3 letras también en `alta_trabajador`, `obra` no textual,
`version: true`, y `comprobar` ahora marca una jornada anulada con presentes) y tres pruebas nuevas; las 21 mutaciones (idempotencia, ámbito, esquema cerrado,
suma diaria, fusionados, orden, traza, avisos…) se detectan. **Deuda anotada:** el código de `codex` es correcto pero está escrito en líneas muy densas con
puntos y coma, sin comentarios, y no se parece al resto del proyecto. **Pasada de legibilidad HECHA en el paso 02 (24/10/2026)**: formato `black` + docstrings y comentarios
insertados desde un `docs.json` escrito por `agy` y corregido por Claude tras leer el fichero entero, con guarda de árbol sintáctico idéntico y las 82 pruebas.

**P2:** se adelantó como piloto porque su contrato es pequeño y estable (filas de jornada con obra, ámbito, fecha, nombre,
horas y extra) y no depende de la forma final del fichero de datos que cierra P0. El verificador se validó antes de lanzar
(contra el esqueleto vacío: 9 fallos y salida 1). Resultado comprobado por Claude: 111 comprobaciones en tres zonas horarias
(Auckland, Los Ángeles y la local), 0 fallos, y **5 de 5 mutaciones detectadas** (ordinarias, límite de fechas, orden de
empate, día de la semana ISO, porcentaje con total 0). Aún no está en el repositorio: entra en P6. Si P0 cambia el contrato,
P2 se ajusta con un encargo nuevo.

**Revisión crítica del plan (gemini), contrastada.** De sus afirmaciones, comprobadas contra el código:
- *Falsas:* que `columnas()` rompe con `Math.max` en año/obra (se envuelve en `new Date` y se ejecutó sin error en las 12
  combinaciones) y que el pie del informe pone «(semana)» fijo (es condicional por periodo). Confirma que hay que contrastar
  siempre lo que dice un revisor IA.
- *Ciertas y aplicadas al plan y a la maqueta:* en un día sin horario, marcar X guardaba **0 h en silencio** (rompe la regla
  «un dato que falta no es cero»); nombres con espacios dobles no se unifican; el pie «100 %» contradice la suma de los
  porcentajes redondeados; faltan «marcar todos», fecha rápida, borrador automático y filtro del desplegable; zonas táctiles
  pequeñas para guantes.
- *Ciertas y pendientes de decidir en P0 (nuevos requisitos):* (a) **corregir o borrar una jornada ya guardada** (la clave
  obra+ámbito+fecha permite sustituirla, falta la pantalla y el «anular»); (b) un trabajador habitual que faltó la última vez
  no aparece en la lista inicial (proponer lista = última jornada + habituales de los últimos 30 días); (c) **Safari borra el
  `localStorage` de una web sin uso en 7 días**: instalar la app en la pantalla de inicio de la tablet y exportar siempre al
  acabar el día; (d) la misma persona anotada en viviendas y garajes el mismo día suma horas: avisar si pasa de 12 h (P1); (e)
  festivos y jornada reducida de verano en el horario semanal (D3).

---

## 5. Ficha de cada paquete

### M — Maqueta visual (Claude) — **hecha el 23/10/2026, pendiente de tu visto bueno**
**Qué es:** `D:\Nueva carpeta\OneDrive\PROYECTO PERSONAL EN OBRA\maqueta\maqueta_personal.html`, una página suelta con **datos inventados** y cuatro vistas:
la app de jornada (marco de móvil), la pestaña Personal (con el aspecto real del panel), el Informe de obra con la sección
Personal y el ranking global de Sagarde. Es interactiva: marcar X, cambiar horas, añadir del desplegable, crear un nombre
nuevo (con el aviso de parecidos), cambiar semana/mes/año/obra y viviendas/garajes.
**No toca nada:** no importa nada del entorno, no genera ficheros y está fuera del repositorio. No puede vivir dentro:
la línea 8 del `.gitignore` (`!*.html`) deja pasar **cualquier HTML** y `Actualizar_Sagarde.bat` lo publicaría sin avisar
(detectado el 23/10/2026 al comprobarlo con `git check-ignore`).
**Para cerrarla:** Bixente la abre (PC o tablet), anota qué cambiaría (columnas, orden, qué se ve primero, textos) y se
corrige antes de P0.

### P0 — Especificación, contrato y verificadores (Claude)
**Objetivo:** con la maqueta aprobada, cerrar D2–D6, escribir la especificación, el contrato de datos y todo lo que permite
delegar sin perder calidad.
**Salida:**
1. `docs/superpowers/specs/2026-10-23-personal-en-obra-design.md` (aprobada por Bixente).
2. Contrato: esquema JSON **cerrado** de catálogo (nombre, categoría, empresa opcional, activo, alta), `personal_obra.json`,
   jornada exportada por la app y `personal_estado.js`; campos obligatorios/opcionales, tratamiento de «dato ausente», formato
   de fecha, semana (lunes–domingo), fórmula del % de impacto a nivel obra y a nivel Sagarde.
3. Fixtures inventados (dos obras, vivienda y garaje, 3 semanas, un cambio de mes y de año, un día extra, un nombre nuevo, dos
   nombres de la misma persona para probar `fusionar`).
4. Tests `unittest` para P1, script `node` con cifras doradas para P2 y script Playwright para P3.
5. Los `encargo_P#.md` de P1–P3 (textos y valores **literales**, ficheros permitidos, «no toques nada más»).
6. Lista exacta de ficheros nuevos para la lista blanca del `.gitignore` (la aplica P6), las zonas `staging\` de P1–P3 y la
   rama/worktree `personal-en-obra` para P4–P5b.
**Validación del verificador:** la solución de referencia da 100 %; el esqueleto vacío falla. Sin esto no se delega.
**Prompt de arranque:**
> Proyecto Sagarde. Paquete P0 del plan `_SISTEMA/docs/superpowers/plans/2026-10-23-personal-en-obra-plan-por-ias.md` (v3).
> Lee solo las secciones 0–4 y la ficha P0. D1 está decidida (se publica, trabajador identificado por su nombre) y la
> maqueta ya está aprobada. Cierra D2–D6 conmigo, escribe la especificación y espera mi aprobación antes de crear tests,
> fixtures o encargos. No escribas código de producción.

### P1 — Núcleo de datos `personal_obra.py` (agy → codex:low)
**Encargo:** módulo solo con biblioteca estándar. Funciones: cargar/guardar catálogo; alta de trabajador con id estable y
aviso de nombre parecido; **`fusionar`** (reasigna jornadas y deja traza); `ingerir_jornada` idempotente (clave
obra+ámbito+fecha, la reingesta sustituye y queda trazada); `ultima_jornada(obra, ámbito)`; `exportar_estado()` que genera
`personal_estado.js`; validación con **esquema cerrado** (campo desconocido, fecha ilegible, horas fuera de 0–24, id
inexistente → **rechazada con aviso, no contada ni puesta a cero**); totales de control por obra para el doble cálculo;
trazabilidad `personal_jornadas.jsonl` aditiva y no bloqueante (un fallo de traza avisa, no revierte).
**Comando** (en `staging\p1_datos`, fuera del repo; el verificador va en `staging\_verificadores\`):
```bash
python "D:\Nueva carpeta\OneDrive\PROYECTO IA REPARTO\ia_dispatch.py" run --cascade agy,codex:low --dir "D:\Nueva carpeta\OneDrive\PROYECTO PERSONAL EN OBRA\staging\p1_datos" --task "<…>\p1_datos\encargo.md" --verify "py -3.11 ..\_verificadores\verificar_p1.py" --rounds 3
```
**Claude comprueba:** el JSON del despachador (`passed`, `winner`, `changed`), que `changed` solo contiene
`personal_obra.py`, y una **mutación** (romper la idempotencia, la separación vivienda/garaje y el rechazo de campos
desconocidos: los tests deben saltar).
**Prompt de arranque:**
> Proyecto Sagarde. Paquete P1 del plan de Personal en obra (v3). Lee solo la ficha P1, el contrato y los tests de P0.
> Trabaja en `staging\p1_datos` (fuera del repo), lanza el despachador con el encargo ya escrito y verifica el resultado con una mutación.

### P2 — Cálculo compartido `personal_calculo.js` (gemini → agy → codex:low)
**Encargo:** funciones puras, sin DOM y sin librerías: horas por trabajador y periodo (semana lunes–domingo, mes, año, obra
completa), ordinarias vs. extra, días presentes, **% de impacto** a nivel obra y a nivel Sagarde (todas las obras),
**ranking** ordenado y estable, agrupación por trabajador (tras `fusionar`). Periodo sin datos → `null`/aviso, nunca `0`.
Los porcentajes de un periodo suman 100 (±0,1). Debe funcionar igual en navegador y en `node`.
**Verificador:** script `node` con cifras doradas calculadas a mano por Claude en P0 (incluye semana a caballo entre dos meses,
cambio de año, nombre fusionado, trabajador sin jornadas y obra vacía).
**Datos:** solo fixtures inventados; apto para `gemini` porque no ve datos reales.
**Prompt de arranque:**
> Proyecto Sagarde. Paquete P2 del plan de Personal en obra (v3). Lee solo la ficha P2, el contrato y las cifras doradas.
> Delega con `gemini,agy,codex:low` y verifica los casos de borde con tus propias cuentas.

### P3 — App `generador_personal.html` (agy → codex:low, Claude verifica)
**Encargo:** HTML único, **sin CDN** ni librerías externas (debe abrir sin cobertura), estilo del generador de revisiones (se
pasa al trabajador un extracto del CSS, **no** el fichero de 1,38 MB) y como la maqueta aprobada. Pensada para móvil **y
tablet**. Flujo: obra → ámbito → última jornada cargada → marcar X → añadir del desplegable → nuevo (con aviso de parecidos)
→ horario semanal → día/horas extra → guardar en el aparato → **Exportar jornada** (JSON del contrato). Pantalla **«Informe
de personal»** que usa `personal_calculo.js` sobre lo publicado más las jornadas del aparato aún sin ingerir. Carga
`personal_estado.js` si hay red y, si no, la última copia guardada. «Deshacer» y confirmación antes de borrar.
**Verificador:** script Playwright (375×812 y 768×1024) que recorre el flujo completo, exporta el JSON y lo pasa por la
validación de P1 con **0 rechazadas**; comprueba que `localStorage` sobrevive a recargar, que sin red usa la copia local y que
el informe de la app coincide con el cálculo de P2 sobre los mismos datos.
**Claude comprueba:** captura en el navegador integrado a móvil y tablet, zonas táctiles ≥ 44 px y una jornada real simulada.
Ver la pantalla antes de dar el visto bueno.
**Prompt de arranque:**
> Proyecto Sagarde. Paquete P3 del plan de Personal en obra (v3). Lee solo la ficha P3, el contrato, la maqueta aprobada y el
> script Playwright de P0. Delega con `agy,codex:low`; después abre el HTML en el navegador integrado a móvil y tablet y
> comprueba el flujo con tus ojos.

### P4 — Pestaña Personal del panel (codex:low, Claude verifica)
**Encargo:** módulo nuevo `panel_personal.py` que devuelve el HTML de la vista e incrusta `personal_calculo.js` y los datos de
la obra. Selector **Semana · Mes · Año · Obra**, tabla por periodo (nombre, días, horas ordinarias/extra, % de impacto) y
gráfica de impacto con el Chart.js local (`static/chart.min.js`), como en la maqueta. En `panel_obra.py` entra únicamente el
hueco que llama al módulo; una obra sin datos nuevos conserva lo de hoy (la tabla de la hoja `Personal` del Excel o «Sin datos…»).
**Verificador:** (a) con fixtures salen las cifras de P2; (b) la obra sin datos produce la misma salida que hoy; (c) el
`panel.html` de las obras no implicadas es **idéntico byte a byte**; (d) el panel generado **no contiene campos fuera del
esquema**.
**Prompt de arranque:**
> Proyecto Sagarde. Paquete P4 del plan de Personal en obra (v3). Lee solo la ficha P4 y la guía de panel (`panel_obra.py:2001-2030, 2296, 2388, 2422`).
> Delega con `codex:low` y verifica la huella de las demás obras antes de dar nada por bueno.

### P5 — Informe de obra con Personal (codex:low, Claude verifica)
**Encargo:** el checkbox `data-seccion="personal"` ya existe en el informe a la carta (`panel_obra.py:2359`): al marcarlo
salen el listado por semana/mes/año/obra con horas y la gráfica de impacto, reutilizando `personal_calculo.js` y las funciones
de P4. Tiene que poder generarse **desde la tablet** sobre el panel publicado.
**Verificador:** tests del informe sobre fixtures + el informe **sin** la sección Personal no cambia.
**Claude comprueba:** el informe en un viewport de tablet (768×1024) y su vista de impresión A4 (letra legible, gráfica que no
se corta). Antes de empezar, mirar cómo genera hoy el informe (en el navegador o no) para no suponer.
Nunca en paralelo con P4.
**Prompt de arranque:**
> Proyecto Sagarde. Paquete P5 del plan de Personal en obra (v3). P4 ya está cerrado y commiteado. Lee solo la ficha P5.
> Reutiliza `panel_personal.py` y `personal_calculo.js`; no dupliques cálculos.

### P5b — Ranking global de Sagarde (codex:low, Claude verifica)
**Encargo:** tarjeta «Personal Sagarde» en el portal que enlaza a una página con el ranking de **todas las obras**: horas
totales, días, % del total de Sagarde y en qué obras ha estado cada trabajador, con filtro semana/mes/año. Mismo cálculo (P2).
**Verificador:** tests de la página con fixtures de dos obras + el resto del portal **idéntico byte a byte**.
**Prompt de arranque:**
> Proyecto Sagarde. Paquete P5b del plan de Personal en obra (v3). P2 y P5 ya están cerrados. Lee solo la ficha P5b y las filas
> del portal en `sagarde_portal.py`. Añade solo la tarjeta y la página; verifica que el resto del portal no se mueve.

### P6 — Integración, guardas y publicación (Claude)
**Alcance:** fusionar la rama `personal-en-obra` **en local y sin publicar**; alimentar el panel desde
`generar_todos.py`/`regenerar_obra.py` (lectura; un fallo de datos de personal **nunca** tumba la generación del panel de una
obra); entradas en la **lista blanca del `.gitignore`** para todos los ficheros nuevos (`personal_catalogo.json`,
`personal_obra.json`, `personal_estado.js`, `personal_calculo.js`, `generador_personal.html` y la traza) **con la prueba de
que de verdad se publican**; auditor del paso 0 del `.bat` que **falla** si un fichero de personal trae campos fuera del
esquema y que compara los totales del JS con los de control de Python (doble cálculo); skill `sagarde-personal` (cómo
ingerir una jornada y fusionar nombres); documentación y **actualización del mapa mental** en la misma sesión. Lo mecánico
(texto) puede ir a `gemini,agy`.
**Prerrequisito:** la otra sesión que modifica `generar_todos.py` ya ha commiteado.
**Verificador:** suite completa `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`
+ mutaciones: quitar una entrada de la lista blanca (el test de publicación debe fallar), colar un campo desconocido en un
fichero de personal (el auditor debe fallar), desviar un total (la comparación JS/Python debe saltar). Restaurar con `cp`,
nunca con `git checkout --`.
**Prompt de arranque:**
> Proyecto Sagarde. Paquete P6 del plan de Personal en obra (v3). Lee la ficha P6, `.gitignore` y el auditor.
> Confirma primero que `generar_todos.py` no tiene cambios ajenos sin commitear. La prioridad son las guardas: lo declarado
> tiene que tener efecto observable, y un recuento 0 es alarma.

### P7 — Cierre y piloto real (Claude)
**Alcance:** con Bixente, una jornada real de una obra (Olabeaga recomendada, tiene viviendas y garajes) de principio a fin:
tablet → exportar → ingerir → publicar → panel e informe de obra desde la tablet → ranking global. **Antes de publicar**,
foto de los SHA de las obras no implicadas y comprobación antes/después (referencia de «Estado de hoy» del mapa mental:
Gernika 94,1 · Mungia 90,3 · Bolueta 73,7 · Barakaldo 0,1 · Prueba 16,3). Solo entonces se fusiona a `main` y se
publica. Memoria del proyecto actualizada y pendientes anotados.
**Prompt de arranque:**
> Proyecto Sagarde. Paquete P7 del plan de Personal en obra (v3). Haz el piloto real con una jornada de Olabeaga:
> exporta desde la app, ingiere, abre el panel y el informe desde la tablet y reporta antes/después de las demás obras.
> No publiques hasta que yo lo diga.

---

## 6. Reglas comunes a todas las conversaciones

- **Arranque corto:** leer solo las secciones que cita el prompt de arranque. No releer el mapa mental entero (43 k tokens); la
  parte útil son las filas A15 (panel), A16 (generador) y la tabla de scripts.
- **Delegar pronto, verificar yo.** Claude lee el JSON del despachador, no el diff entero; muestrea los ficheros de `changed`.
- **Antes de cada `codex exec`:** `git log --oneline -10` y `git status` (otra sesión puede estar trabajando).
- **Mutación obligatoria** en cada paquete de código: romper a propósito, ver que la prueba lo detecta, restaurar con `cp`.
- **Reportar antes/después a Bixente** cuando algo mueva cifras. Sin reportar, no se da por cerrado.
- **Si falla toda la cascada:** Haiku (`Agent`, `model: haiku`); si también falla, Claude mayor. Nunca dos trabajadores a la vez.
- **Cada paquete termina con:** resultado real del verificador, ficheros tocados, y qué **no** se ha comprobado.

## 7. Riesgos principales

| Riesgo | Cómo se corta |
|---|---|
| Estropear lo que ya funciona | Maqueta primero, rama/worktree aislada, solo ficheros nuevos + huecos mínimos, obras ajenas idénticas byte a byte, fusión revertible |
| Alguien con la URL ve nombres, horas y obra | Riesgo aceptado por Bixente (D1). El esquema no tiene DNI, teléfono ni correo y el auditor rechaza campos fuera del esquema |
| Se genera `personal_estado.js` pero nunca se publica (lista blanca) | P6: entrada declarada **y** prueba de que está en lo publicable |
| El cálculo del panel y el de la app divergen | Una sola implementación (`personal_calculo.js`) + comparación con los totales de control de Python |
| Una jornada con un dato ilegible se cuenta como 0 y baja el % sin avisar | Validación de P1: rechazada con aviso; un periodo sin jornadas dice «sin jornadas», no «0 h» |
| Nombres repetidos o escritos distinto que falsean el ranking | Desplegable + aviso de parecidos + `fusionar` con traza |
| Doble ingestión duplica horas | Clave obra+ámbito+fecha y test de idempotencia |
| Se pierde la jornada del aparato (se limpia el navegador) | Botón de exportar al terminar el día; la app avisa de las jornadas pendientes de ingerir |
| Regresión en `panel_obra.py` (149 KB) | Lógica en módulo nuevo, hueco mínimo y comparación byte a byte de las demás obras |
| Sesión paralela pisa `generar_todos.py` | P6 espera a que esté commiteado; un solo trabajador por árbol; la construcción va en worktree |
