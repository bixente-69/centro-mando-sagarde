# Ampliación de revisiones a garajes — Plan de trabajo y reparto

**Fecha:** 24/09/2026
**Depende de:** `2026-09-24-ampliacion-garajes-design.md` (misma carpeta) —
diseño cerrado y validado contra prototipo interactivo (§9 de ese documento).
Este plan no reabre ninguna decisión de diseño, solo la secuencia para
llevarla a producción.
**Pedido explícito de Bixente (24/09/2026):** *"comienza poco a poco con tu
spec tu plan de trabajo el reparto de tareas etc. si acabáramos hoy no sé si
llegarán los tokens, probaríamos con Mungia o Gernika que paso mañana a
revisar estado de obras. Si no, el lunes o martes cualquiera de ellas."*
Consecuencia directa para este plan: **está pensado para pausarse entre
fases sin dejar nada roto**, no para completarse de una sentada.

---

## 0. Cómo leer este plan

- Cada fase es **commiteable de forma independiente** y dejar el árbol
  limpio al terminarla es parte de la fase, no un extra — así una sesión
  puede parar en cualquier punto sin arriesgar que `Actualizar_Sagarde.bat`
  publique algo a medias (regla del CLAUDE.md del proyecto, §4).
- **Nunca dos trabajadores a la vez sobre el mismo árbol.** Antes de lanzar
  cualquier tarea de Codex o agy, `git status` y `git log --oneline -10` —
  no solo al empezar la sesión, también por si Bixente ha trabajado el
  mismo repo desde otro sitio entretanto.
- El reparto seguido es el ya fijado para el proyecto: **agy** para
  ficheros de solo-edición con valores ya decididos (sin ejecutar nada);
  **Codex** para lo que necesita ejecutarse para hacerse o comprobarse;
  **Claude** para diseño de detalle, dirección de cada encargo y
  verificación independiente — nunca dar por bueno el informe de un
  trabajador sin comprobarlo aparte.
- Todas las fases heredan las reglas fijas del CLAUDE.md del proyecto:
  pruebas primero, no tocar nada fuera del alcance de la fase, commits
  pequeños que expliquen el porqué, `grep -n` de todos los usos antes de
  dar por bueno un cambio a algo compartido, y comprobar siempre que las
  obras no implicadas no se mueven (Mungia, Gernika — la que no sea la
  obra de prueba elegida —, Bolueta, Obispo Orueta).

## Resumen de reparto por fase

| Fase | Qué es | Quién | Estado |
|---|---|---|---|
| 1 | Catálogo de tajos garaje en `CATALOGO_TAJOS.json` | Claude diseña la tabla exacta → **agy** transcribe → Codex escribe/ejecuta los tests → Claude verifica | ✅ **CERRADA** (`b694b97`) |
| 2 | `ficha_garajes.json` + módulo Python equivalente a `ficha_obra.py` | Claude diseña la forma → **Codex** implementa y prueba → Claude verifica | ✅ **CERRADA** (`3e5da0a`) |
| 3a | Cálculo: `priorizar_ficha_garaje` en `priorizador_trabajos.py` + llamada en `generar_todos.py` | Claude diseñó 5 hallazgos y las funciones exactas → **Codex** implementa con diff byte a byte → Claude verifica | ✅ **CERRADA** (`daf4c2a`) |
| 3b | Mostrarlo: sección de garaje en `panel_obra.py` | Claude diseña dónde insertarla → **Codex** implementa con diff byte a byte del HTML → Claude verifica en navegador real | ✅ **CERRADA** (`f623e24`) |
| 4 | Wizard de 4 pantallas + hoja por tipo de zona en `generador_revisiones.html` | **Codex** implementa a partir del prototipo de referencia → Claude verifica en navegador real | ✅ **CERRADA** (`645d9b8`) |
| 5 | Adaptador de lectura de revisiones de garaje | **Codex** implementa y prueba → Claude verifica | ✅ **CERRADA** (`9298c2f`) |
| 6 | Validación completa contra `OBRA PRUEBA` (con mutación) | **Claude** dirige, **Codex** ejecuta los escenarios | pendiente |
| 7 | Alta y primera revisión real: Mungia o Gernika | **Claude + Bixente** (necesita su hoja/planos reales, ningún worker puede inventarlos) | pendiente |

---

## Fase 1 — CERRADA (24/09/2026, commit `b694b97`)

Ejecutada tal como estaba planeada, reparto incluido: Claude diseñó la tabla
completa (`_SISTEMA/scratch/fase1-catalogo-garajes-borrador.md`, 42 tajos),
agy la transcribió al JSON sin errores de transcripción, Codex escribió y
ejecutó `tests/test_catalogo_garajes.py` más la suite entera.

**El paso de verificación de Claude no fue un trámite — encontró dos fallos
reales antes de commitear:**
1. Detectado por la propia suite (test ya existente,
   `test_catalogo_invariantes.py`): `garaje_cuadro_embornado` dependía de
   `garaje_pintura_2_recinto` con un `orden` numérico posterior — ninguna
   dependencia puede apuntar hacia delante. Era un fallo de mi propio
   diseño de la tabla, no de la transcripción de agy.
2. Detectado releyendo el catálogo línea a línea (ningún test lo cubría):
   las 4 entradas de pintura tenían `propiedad: "propio"` en vez de
   `"externo"` — hueco en mis propias instrucciones a agy, no un error suyo.

Los dos corregidos y reverificados de forma independiente (script de
Python aparte, no solo la suite) antes de commitear. Queda como precedente
concreto de por qué el plan exige verificación independiente en cada fase,
no solo confiar en que "los tests pasan": el primer fallo SÍ lo habría
detectado cualquiera que corriera la suite, pero el segundo no lo detecta
ningún test automático — solo revisar el diff de verdad.

### Detalle original de la Fase 1 (para referencia — ya ejecutado)

**Objetivo:** las entradas nuevas de `CATALOGO_TAJOS.json` que traducen §4 y
§5 del diseño a `id`/`nombre`/`aliases`/`propiedad`/`ambito`/`orden`/`fase`/
`deps`/`estado_m`/`estado_x`/`impacto` reales.

**Qué toca:** solo `reglas/CATALOGO_TAJOS.json`, más un test nuevo que lo
valide.
**Qué NO toca:** ningún otro fichero — en particular, nada de
`priorizador_trabajos.py` todavía (eso vendría solo si hiciera falta
ajustar `_buscar_dep` o `AMBITO_ORDEN`, y hoy no se prevé).

**Decisiones técnicas que Claude tiene que cerrar antes de encargar nada**
(no están explícitas en el diseño y agy no debe inventarlas):

1. **Valor de `ambito` para tajos de garaje.** El diseño (§3.2 del
   documento de diseño) deja el garaje como `garaje → planta → zona → tajo`,
   sin nivel de vivienda. `AMBITO_ORDEN` en `priorizador_trabajos.py` hoy
   solo conoce `vivienda`/`zona_comun`/`edificio` (dict sin `.get()`, revienta
   con `KeyError` si aparece un valor nuevo no contemplado — ver hallazgo ya
   registrado en la fase de brainstorming). Propuesta de Claude: reusar
   `zona_comun` para todas las zonas de garaje — ninguna es una unidad
   privada tipo vivienda, y es el valor que ya existe, sin tocar el dict.
   Confirmar con Bixente antes de commitear la Fase 1 si hay dudas, pero no
   bloquear todo el plan por esto.
2. **Dos cadenas `deps` completas y paralelas** (ruta empotrada y ruta
   vista) por cada tipo de tajo del patrón de §4.1/§5.5, sin cruzarlas —
   motivo ya documentado en el diseño (una celda `N` no libera a quien
   dependa de ella).
3. **`orden`** dentro de cada cadena, reflejando qué gremio va antes en cada
   ruta (§4.1) — es la única forma en que ese orden queda representado, ya
   que no se traduce en dependencia bloqueante (decisión de simplicidad ya
   tomada).

**Reparto:**
1. Claude escribe la tabla completa (todas las filas, con `id`/`orden`/
   `deps` exactos) como un fichero de trabajo aparte, no directamente en el
   JSON.
2. **agy** transcribe esa tabla ya cerrada a `CATALOGO_TAJOS.json` — tarea de
   solo-edición con valores ya decididos, encaja en lo que agy hace bien.
   Prompt con el aviso estándar ("no puedes ejecutar nada, solo editar"), un
   único fichero nombrado, y la tabla completa pegada.
3. **Codex** escribe y ejecuta un test nuevo (`tests/test_catalogo_garajes.py`
   o extensión de uno ya existente) que compruebe: el JSON carga, ningún
   `deps[].id` apunta a un tajo inexistente, no hay `id` duplicado entre
   vivienda y garaje, y el recuento de tajos nuevos coincide con lo previsto
   en el diseño.
4. Claude revisa el diff línea a línea (no solo el resultado del test) y
   corre la suite completa:
   ```bash
   cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
   ```
   Los 604 tests que pasaban hoy (más los nuevos) tienen que seguir
   pasando — ninguno menos.

**Checkpoint de cierre:** commit propio, mensaje explicando qué tajos se
añadieron y por qué (no solo "añadir tajos garaje").

---

## Fase 2 — `ficha_garajes.json` y su módulo Python — ✅ CERRADA

**Objetivo:** estructura de datos real (garaje→planta→zona→tajo) y las
funciones equivalentes a las de `ficha_obra.py` (`snapshot_desde_ficha`,
`actualizar_desde_snapshot`, `MAPA_ESTADO`...) para leerla y escribirla.

**Por qué es menos riesgo de lo que parece:** el estado `N` **ya existe**
hoy en el alfabeto persistido del proyecto (CLAUDE.md §7) y ya se aplicó al
ciclo de marcado real en esta misma sesión (ver §6.3 del diseño) — no hace
falta enseñarle `N` a `ficha_obra.py` desde cero, solo confirmar que el
`MAPA_ESTADO` que se reutilice para garaje lo trata igual que para vivienda.

**Qué toca:** fichero nuevo (`ficha_garajes.py` o extensión de
`ficha_obra.py` si Claude decide que compensa compartir código — a decidir
al diseñar el detalle, no antes) + `ficha_garajes.json` de `OBRA PRUEBA`
como primer caso real de prueba.
**Qué NO toca:** `ficha_obra.json` de ninguna obra existente, ni los
módulos de lectura/paneles (eso es la Fase 3).

**Reparto:**
1. Claude diseña la forma exacta del módulo (qué funciones, qué firma, qué
   reutiliza literalmente de `ficha_obra.py` y qué es distinto por ser más
   plano — sin nivel de bloque/portal).
2. **Codex** implementa y escribe tests unitarios (crear ficha vacía, poblar
   estructura, aplicar snapshot de revisión, leer estados incluyendo `N`,
   recalcular porcentaje excluyendo las `N` del denominador).
3. Claude revisa el diff y ejecuta la suite completa otra vez.

**Checkpoint de cierre:** commit propio. `ficha_garajes.json` de `OBRA
PRUEBA` puede quedar vacío o con un caso mínimo — el poblado real es la
Fase 6.

**✅ CERRADA (24/09/2026, commit `3e5da0a`).** `ficha_garajes.py` con
`ruta_ficha`/`cargar`/`guardar`/`asegurar_apartados`/`snapshot_desde_ficha`/
`actualizar`/`actualizar_desde_snapshot`/`esta_rancia`/`resumen_cambios`,
11 tests propios. Verificación de Claude fue más allá de correr la suite:
trazado a mano de la máquina de estados encontró que el diseño (no Codex)
introduce una diferencia deliberada frente a `ficha_obra.py` — un estado no
reconocido (no solo uno vacío) nunca baja un estado ya guardado, más
protector que vivienda para una vía de entrada sin historial probado
todavía. Suite completa: 622 tests, 0 fallos.

---

## Fase 3 — Segunda ficha por obra (la parte de más riesgo real) — ✅ CERRADA (3a + 3b)

**Dividida en dos al diseñar el detalle (24/09/2026)**, tras leer completos
`priorizador_trabajos.py`, `generar_todos.py`, `motor_informes.py` y
`panel_obra.py`: no era tan simple como "llamar dos veces a lo mismo".
Aparecieron 6 hallazgos reales en total (5 en el cálculo, uno de ellos un
fallo de conteo real que habría afectado a garaje de forma silenciosa; 1
más en el render, sobre `panel_obra.py`) que hacían irresponsable diseñar
el cálculo y el renderizado como una sola pieza. Detalle completo del
cálculo en `_SISTEMA/scratch/fase3a-calculo-garaje-diseno.md` y del
render en `_SISTEMA/scratch/fase3b-panel-garaje-diseno.md`.

**Objetivo general (de las dos sub-fases juntas):** que el sistema sepa
calcular Y mostrar prioridades y KPIs de garaje junto a los de vivienda,
sin mover ni una cifra de las obras que no tienen garaje (§3.3 del diseño:
dos lecturas, no una por garaje físico).

**Por qué es la fase de más riesgo:** toca módulos que ya generan **todas**
las obras existentes, no solo garajes. Un error aquí no falla
"silenciosamente en garajes" — puede mover el porcentaje de obras que no
tienen nada que ver con esta ampliación, que es exactamente la familia de
fallo que el CLAUDE.md del proyecto pide vigilar por encima de todo.

### Fase 3a — Cálculo (sin tocar ningún HTML)

**Objetivo:** que `priorizador_trabajos.py` sepa calcular prioridades de
una ficha de garaje (`priorizar_ficha_garaje`, nueva, en paralelo a
`priorizar_ficha`) y que `generar_todos.py` la llame y escriba
`prioridades_trabajos_garaje.json` cuando la obra tenga
`ficha_garajes.json`. Nada se muestra todavía.

**Qué toca:** `priorizador_trabajos.py` (funciones nuevas, más un
parámetro opcional con su valor por defecto igual al actual en
`_clave_unidad`/`_agrupar_prioridades`/`prevision_desbloqueos` — ver
Hallazgo 5 del diseño, la única excepción real a "no tocar vivienda" de
todo el plan, y está acotada y verificable) y `generar_todos.py` (llamada
nueva dentro de `main()`, más el parámetro nuevo `prioridades_garaje` que
`panel_obra.generar_panel` recibirá pero todavía no usa).
**Qué NO toca:** ni una línea de `panel_obra.py` ni de `motor_informes.py`
(este último no hace falta tocarlo — es agnóstico de estructura, ver
Hallazgo 1). `priorizar_ficha` (vivienda) no cambia de comportamiento para
ningún llamador existente.

**Reparto:**
1. Claude diseñó las funciones exactas, sus firmas y qué reutiliza tal
   cual (`_SISTEMA/scratch/fase3a-calculo-garaje-diseno.md`).
2. **Codex** implementa y escribe/ejecuta los tests, incluyendo la prueba
   de no regresión más importante de toda la fase: generar
   `prioridades_trabajos.json` de las obras reales antes y después del
   cambio y compararlos **byte a byte** — no solo "el test pasa".
3. Claude verifica de forma independiente: lee el diff línea a línea,
   corre la suite completa, y comprueba a mano al menos 2 obras reales
   antes/después.

**Checkpoint de cierre:** commit propio. Reportar a Bixente el antes/después
de las obras reales existentes antes de seguir — regla explícita del
CLAUDE.md del proyecto (§3), no un extra opcional.

**✅ CERRADA (24/09/2026, commit `daf4c2a`).** Las 6 obras reales
registradas (Gernika, Mungia, Bolueta, Gorliz, OBRA PRUEBA, Olabeaga)
conservan `prioridades_trabajos.json` byte a byte idéntico, verificado por
un test que recarga su `ficha_obra.json` real y recalcula, no una
comparación hardcodeada. `panel_obra.py` recibió su único toque permitido
(`prioridades_garaje=None` en la firma de `generar_panel`, sin usar
todavía) — Codex había resuelto la misma necesidad con detección por
`inspect.signature`, correcta pero más compleja de lo necesario; Claude la
sustituyó por el parámetro simple ya previsto en este mismo plan. Suite
completa: 632 tests, 0 fallos.

### Fase 3b — Mostrarlo en `panel_obra.py`

**Objetivo:** que el panel de una obra con `ficha_garajes.json` muestre una
sección de garaje (KPIs + tabla de prioridades) junto a la de vivienda,
usando `prioridades_garaje` que la Fase 3a ya deja calculado y pasado como
parámetro.

**Por qué se separó de la 3a:** `panel_obra.py` (2183 líneas) genera el
HTML de **todas** las obras hoy mismo, con muchas funciones entrelazadas
(`bloque_prioridades_partes`, tarjetas de KPI, tablas) que habría que
llamar una segunda vez con los datos de garaje. Es la pieza con más
superficie de fallo visual de toda la ampliación.

**Mitigación obligatoria — más estricta que "correr los tests":**
generar el panel de **todas** las obras reales antes y después del cambio
y comparar el HTML resultante **byte a byte** para cualquier obra sin
`ficha_garajes.json` (es decir, todas las de hoy) — tiene que ser
idéntico, no solo "visualmente parecido". Es una versión más mecánica y
más verificable de la salvaguarda de doble cálculo, adaptada a que aquí no
hay dos caminos de cálculo que comparar, sino una función de render que no
debe cambiar su salida cuando no hay nada nuevo que mostrar.

**Hallazgo 6 (al diseñar el detalle):** `bloque_prioridades_partes` NO se
puede llamar una segunda vez con los datos de garaje — usa `id` de HTML
fijos por constantes de módulo (`_ID_SEC_DUDAS` y similares), pensados
para una sola instancia por página. Llamarla dos veces duplicaría esos
`id`, HTML inválido y acordeones/filtros rotos. La sección de garaje es
una pestaña nueva (`v-garaje`, mismo patrón que las demás pestañas de la
página) con una tabla simple propia, no una reutilización de esa función.
Detalle completo en `_SISTEMA/scratch/fase3b-panel-garaje-diseno.md`.

**Reparto:** igual patrón que el resto — Claude diseñó exactamente dónde
se inserta la sección nueva, Codex implementa con la comprobación byte a
byte activa, Claude verifica en navegador real además de revisar el diff — no
basta con mirar el HTML como texto (ver
[[feedback_sagarde_dirigir_codex_y_verificar_de_verdad]], la lección de
CSS/print ya aprendida una vez en este proyecto).

**Checkpoint de cierre:** commit propio. No empezar sin que la Fase 3a
esté cerrada y verificada.

**✅ CERRADA (24/09/2026, commit `f623e24` — el subject dice "Fase 3a" por
un error de tecleo al escribirlo, el contenido es 100% Fase 3b, ver el
cuerpo del propio commit).** Pestaña "🅿️ Garaje" añadida al panel con KPIs
simples y tabla de prioridades, condicionada por completo a que
`prioridades_garaje` no sea `None` — para las 6 obras reales de hoy el
HTML no cambia ni un carácter (verificado por SHA-256 de Codex y por un
test que compara el contenido completo de cada vista `v-*`). Verificado
además visualmente en el navegador con datos sintéticos: la pestaña
cambia de vista, las tarjetas KPI y la tabla muestran los números
correctos, y las ubicaciones se despliegan bien al pulsarlas. Suite
completa: 634 tests, 0 fallos.

**Con esto, la Fase 3 completa (3a + 3b) queda cerrada.**

---

## Fase 4 — Wizard de 4 pantallas en `generador_revisiones.html`

**Objetivo:** llevar el flujo ya probado en el prototipo (§3.5 y §6.4 del
diseño) al generador real: Obra → Estructura → Tajos → Generar, con la hoja
repartida por tipo de zona (tablas anchas para zonas de conteo uniforme,
tarjetas individuales para cuartos técnicos).

**Diseño detallado ya escrito**, tras leer el fichero real completo (1459
líneas): `_SISTEMA/scratch/fase4-wizard-garaje-diseno.md`. Decisión clave
de arquitectura: los pasos 2-4 del asistente no se duplican en HTML —
sus funciones de render ya existentes se ramifican por `S.modo` y
rellenan los mismos contenedores; solo el paso 1 necesita HTML nuevo (el
selector de modo). Incluye ya generado mecánicamente (no retecleado a
mano) el `CAT_GARAJE` de 42 entradas desde el `CATALOGO_TAJOS.json` real.
De paso, leer el fichero completo destapó y corrigió un cabo suelto de la
Fase 0: `generateHTML()` tenía una segunda correspondencia de símbolos
(para prerellenar celdas desde una obra con base de datos) que aún usaba
el punto pequeño en vez de `N` — commit `944a6fd`.

**Qué toca:** `generador_revisiones.html`. El prototipo
(`_SISTEMA/scratch/garaje-wizard-demo.html`, Artifact
`https://claude.ai/artifact/TKc74kuhSoykLidgbgJnbD`) es referencia de
comportamiento ya validada con Bixente, no código a copiar literal — está
desconectado del backend real y usa datos de ejemplo.
**Qué NO toca:** el flujo de vivienda existente, que tiene que seguir
funcionando exactamente igual (mismo generador, dos flujos dentro,
`S.modo==='vivienda'` por defecto preserva el 100% del comportamiento
actual).

**Reparto:**
1. Claude traduce el comportamiento validado del prototipo a instrucciones
   concretas para el fichero real (qué funciones existentes de
   `generador_revisiones.html` se reutilizan — `CYCLE`/`SYM`/`CLS`,
   `wireCeldas`-equivalente — y qué es nuevo).
2. **Codex** implementa — requiere ejecutar y probar en navegador, no es
   tarea de solo-edición.
3. Claude prueba en navegador real (Chrome o Edge, no solo el pane de
   Claude) el camino completo: generar hoja de garaje en blanco, marcar
   casillas incluyendo `N`, guardar, y que el flujo de vivienda existente
   siga intacto.

**Checkpoint de cierre:** commit propio. Este es el primer punto en que
Bixente puede empezar a usar algo con sus manos en un navegador normal,
antes incluso de que exista el adaptador de lectura.

**✅ CERRADA (24-25/09/2026, commit `645d9b8`).** El asistente completo de
garaje (selector de modo, estructura por lista de comprobación/conteo,
catálogo de 42 tajos, hoja repartida por tipo de zona con pestañas y
tarjetas) está en el fichero real. `sheetRuntime()` comparte de verdad el
ciclo `CYCLE/SYM/CLS` entre los dos modos — no hay una segunda copia.
Verificación independiente encontró un fallo real (`GARAGE_PROFILE_TAJOS.cuarto_ligero`
solo llevaba alumbrado fijo, faltaban temporizado/emergencia/enchufe
completos pese a que §5.7 del diseño pide expresamente los tres),
corregido y reverificado mecánicamente contra los 42 tajos del catálogo.
Probado de verdad en el navegador (Claude, tras crear una copia de
prueba sin el logo — el fichero real pesa 1,3&nbsp;MB por el logo en
base64 y excede el límite de carga del navegador integrado): estructura,
tajos, generación de hoja, pestañas, ciclo de marcado hasta `N` con
símbolo grande y visible, y la fila resaltada del tajo específico de
cada cuarto técnico. Suite completa: 634 tests, 0 fallos.

---

## Fase 5 — Adaptador de lectura de revisiones de garaje

**Objetivo:** traducir una hoja de garaje rellena (HTML guardado, o PDF
escaneado con marca a boli, según cómo Bixente la traiga de campo) a
`REVISION_NORMALIZADA` y de ahí a `ficha_garajes.json`, análogo a
`adaptar_revision_html.py` / `adaptar_revision_pdf_digital.py` /
`leer_hoja_marcada.py`.

**Qué toca:** adaptador nuevo (o extensión de los existentes, a decidir al
diseñar el detalle según cuánto se pueda reutilizar de la lectura por
geometría ya existente para viviendas).
**Qué NO toca:** los adaptadores de vivienda existentes, que no deben
cambiar de comportamiento.

**Reparto:** igual patrón que las fases 2-3 — Claude diseña el punto de
entrada exacto, **Codex** implementa y prueba con una hoja de garaje real
generada en la Fase 4, Claude verifica.

**Checkpoint de cierre:** commit propio.

**✅ CERRADA (25/09/2026, commit `9298c2f`).** Dos piezas: `alta_garaje_desde_hoja.py`
extrae el `<script id="garaje-estructura">` que la Fase 4 embebe en la
hoja (misma hoja que Bixente ya sabe generar y guardar, cero UI nueva)
y crea `ficha_garajes.json` — nunca pisa una ficha existente.
`adaptar_revision_garaje.py` aplica una hoja de garaje ya rellena vía
`ficha_garajes.actualizar_desde_snapshot`, sin ninguna de las dos capas
de numeración sintética que arrastra `adaptar_revision_html.py`: los
ids que escribe el asistente de garaje ya son los canónicos. Codex se
quedó sin cuota (185.753 tokens) justo al terminar de escribir los
tests — el código y los tests que dejó estaban completos y correctos,
sin necesidad del fallback gratuito ni de que Claude reescribiera nada.

Verificación independiente de Claude (no solo el informe de Codex, ni
solo "la suite pasa"): los tres ficheros leídos línea a línea contra el
diseño; el contrato con `ficha_garajes.actualizar_desde_snapshot` y
`resumen_cambios` releído y confirmado exacto, incluida la delegación
correcta de zonas desconocidas (el adaptador no duplica esa lógica); el
regex de extracción del JSON embebido contrastado contra la línea real
de `generador_revisiones.html` (no solo la prueba sintética de
escapado ya hecha al cerrar la Fase 4); `data-k`/`data-st` de
`extraer_pares` contrastado contra el HTML real que emite el generador
para vivienda y para garaje; `registro_obras.OBRAS` y el formato real
de `CATALOGO_TAJOS.json.obras` confirmados contra disco, no de memoria.
Suite completa: **639 tests, 0 fallos** (634 previos + 5 nuevos).

Hallazgo real, fuera de alcance de esta fase y no corregido aquí: el
camino principal de `generar_todos.py`
(`construir_revision_normalizada_desde_snapshot`) llama a
`validar_revision._ids_tajos` con el id corto de la obra (`obra['id']`,
p. ej. `'mungia'`), pero `CATALOGO_TAJOS.json.obras` está indexado por
el nombre completo de la obra — nunca coinciden, así que los tajos
propios de obra declarados ahí son invisibles para ese camino. Hoy es
inofensivo (solo Obispo Orueta, ya archivada, tiene tajos propios en el
catálogo), pero afectaría en cuanto una obra activa —de vivienda o de
garaje— declare tajos propios. Pendiente de revisar aparte.

---

## Fase 6 — Validación completa contra `OBRA PRUEBA`

**Objetivo:** demostrar el ciclo completo (alta de garaje → generar hoja →
rellenar → leer → ficha actualizada → panel muestra las dos lecturas) sobre
`OBRA PRUEBA`, la obra ficticia que ya existe exactamente para esto (§2,
principio 5 del diseño), antes de tocar Mungia o Gernika.

**Cómo, siguiendo la norma del proyecto de "probar por mutación":** no basta
con que el camino feliz funcione. Romper algo a propósito (una celda sin
`deps` resuelta, un tajo marcado `N` que debería excluirse del porcentaje y
comprobar que de verdad se excluye, una obra sin `ficha_garajes.json` que
debe comportarse exactamente como hoy) y confirmar que la prueba se entera.

**Reparto:** Claude dirige el guion de validación y hace la verificación
final; **Codex** ejecuta los escenarios concretos (generar, rellenar
programáticamente para simular varias combinaciones, leer, comprobar
salida) porque requieren ejecución real repetida.

**Checkpoint de cierre:** informe a Bixente con capturas o datos concretos
del ciclo completo en `OBRA PRUEBA`, antes de pasar a obra real — es el
punto de decisión de Bixente para dar luz verde a la Fase 7.

---

## Fase 7 — Obra real: Mungia o Gernika

**Objetivo:** alta del garaje real de la obra elegida (estructura real de
plantas/zonas, según planos/hoja que traiga Bixente) y primera revisión de
verdad.

**Por qué ningún worker puede adelantar esto solo:** la estructura depende
de datos reales de obra (planos, recuento real de plazas/trasteros/cuartos
técnicos) que solo Bixente tiene. Esta fase empieza con Bixente, no con una
tarea que se le pueda encargar a Codex o agy de antemano.

**Reparto:** Claude prepara de antemano (antes de que Bixente visite la
obra) el wizard ya operativo y probado por la Fase 6, para que dar de alta
la estructura real sea cuestión de minutos delante de Bixente o con lo que
él traiga; Claude ejecuta el alta con los datos que Bixente aporte y
verifica el resultado con él en el momento.

**Checkpoint de cierre:** ninguno técnico — el cierre es que Bixente vea su
garaje real reflejado y dé el visto bueno, o corrija lo que no cuadre.

---

## Qué es razonable esperar completar hoy

Bixente ya avisó de que los tokens pueden no alcanzar para todo en una sola
sesión. Orden de prioridad si hay que parar a media fase:

1. Fase 1 (catálogo) es la base de todo lo demás — sin ella nada del resto
   tiene sentido. Prioridad máxima.
2. Fase 2 (ficha) es barata gracias a que `N` ya existe en el motor —
   segunda prioridad.
3. Fases 3-5 son las que de verdad necesitan varias rondas de Codex con
   verificación intermedia — es razonable que queden para el lunes o
   martes, tal como el propio Bixente planteó como alternativa.
4. Fase 6 y 7 no deberían intentarse el mismo día que las fases 3-5: la
   regla del proyecto de nunca dar una tarea por terminada sin pruebas
   reales pesa más que la prisa por enseñarle algo a Bixente en la obra.

Parar limpio al final de cualquier fase (commit hecho, suite en verde,
`git status` limpio) dejando las siguientes documentadas aquí es preferible
a avanzar varias fases a la vez sin verificación intermedia.
