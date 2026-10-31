# Personal en obra — dos personas con el mismo nombre (MA4a · F5)

Diseño del 30/10/2026 (Claude, Sonnet 5.5). **Sin código.** Sale de la auditoría del 30/10 (hallazgo F5) y de medidas
propias sobre copias con **nombres inventados** (Rafa, Pepe, Luis; empresas «Alfa Instalaciones», «Beta Montajes»…).
Arnés y resultados en `D:/bench_ias/_MA4a/` (`medir_pc.py`, `medir_tablet.py`, `calculo.js`, `resultados_pc.json`,
`resultados_tablet.json`); capturas a 390 px en `PROYECTO PERSONAL EN OBRA/mejoras_auditoria_30oct/capturas_ma/MA4a/`.

**Estado de la decisión: PROVISIONAL hasta la prueba de campo.** Bixente (30/10): «todo lo que me propongas me va a parecer
bien, te puedes ahorrar las preguntas, cuando hagamos un trabajo de campo probaremos la realidad». No se le ha preguntado nada:
la opción sale de lo medido (§2–§4). Lo que habrá que mirar en el campo está en §10.

## 1. Resumen (en llano)

- **Hoy la persona ES su nombre**, en todo el sistema (≈ 190 sitios que comparan el nombre limpio). Dos personas con el mismo
  nombre se funden **sin avisar**: sus horas se suman en una sola y, peor, **al segundo «Rafa» se le cambia la empresa al primero
  y todas sus horas viejas pasan a contarse en la empresa nueva**.
- **Recomiendo la opción B reforzada: el nombre sigue siendo único**, y cuando se escribe uno que ya existe con otra empresa,
  la tablet y «Generar personal» **preguntan** («¿es el mismo o es otra persona?») y, si es otra, **piden un apellido o una
  inicial** («Rafa B.»). Más tres arreglos en el PC para que **nada cambie de empresa en silencio** (opción C, que va dentro).
- **No cambia ningún fichero ni ningún dato guardado**: ni el contrato de la tablet, ni el de «Generar personal», ni el catálogo, ni
  lo ya publicado. No hay migración. La base real de hoy tiene **15 personas y 15 nombres distintos** (contado con Python sobre `personal_catalogo.json`, igual en `main` y en la rama a 30/10; el árbol real puede haber cambiado desde entonces): no hay nada que separar.
- No recomiendo la A (nombre + empresa = persona) porque obliga a reescribir ≈ 190 sitios, rompe el contrato y, además, la
  empresa de una persona **cambia** de verdad (el lápiz ✎ y `poner_empresa` lo permiten): con la A, quien cambia de empresa pasaría a
  ser otra persona.

## 2. Qué pasa hoy (MEDIDO, no supuesto)

PC = `personal_obra.py` + `lector_control_horario.py` + `personal_calculo.js`, ejecutados de verdad sobre copias (`medir_pc.py`).
Tablet = Chromium real, 390 px, fecha fija 23/10/2026 (`medir_tablet.py`). «Rafa (Alfa)» = Rafa de Alfa Instalaciones.

| # | Camino y caso | Resultado medido |
|---|---|---|
| P1 | Fichero con una jornada con «Rafa» dos veces el mismo día + empresas Alfa y Beta | Jornada **rechazada** («Una persona sale dos veces el mismo día»). El fichero queda **listo** con «1 jornada que no vale / No trae nada nuevo»: las horas se pierden y lo demás se aplicaría. Es el comportamiento que fija la prueba `test_lector_control_horario.py:260`; **no se toca** |
| P10 | Lo mismo sin `empresas` | Fichero **rechazado**: «Ninguna jornada de este fichero vale». Visible |
| P2 | «Rafa» 8 h en OBRA UNO y otro «Rafa» (Beta) 8 h en OBRA DOS el mismo día | Se toma como **una** persona: aviso falso «Rafa suma más de 12 horas» (frena el fichero) y a la vez **cambia la empresa** de Alfa a Beta (resumen: «1 empresa puesta») |
| P3 | Otro «Rafa» (Beta) llega otro día | **Un solo Rafa en el catálogo**. Su empresa pasa de Alfa a Beta **sin avisar** (fichero *listo*) y **todos sus días anteriores** cambian de empresa: «Por empresa» pasa de *Alfa 8 h* a *Beta 16 h* |
| P4 | «Generar personal»: añadir «Rafa» a Beta existiendo «Rafa (Alfa)» | El fichero trae `empresas:[Rafa→Beta]`, el PC lo da por **listo** («1 empresa puesta»): **mueve al Rafa de Alfa** sin avisar. La pestaña dice «se ha añadido a la empresa» |
| P5 | Fichero con «Rafa» en `altas` (nombre nuevo) y Rafa ya existe | `accion: sin_cambios`, **sin ningún aviso** |
| P6 | Renombrar «Pepe» a «Rafa» (existe) | **Bien**: queda «a revisar» con «ya es otra persona… si son la misma persona hay que juntarlas» y la orden `fusionar` |
| P7 | Catálogo con **dos** «Rafa» vigentes (a mano) | `comprobar`: «nombres no fusionados duplicados». `_buscar_nombre('Rafa')` → siempre el **último** (T0002). Una jornada de «Rafa» va a T0002. `poner_empresa('Rafa')` toca T0002. El catálogo publicado trae los dos. `aplanar` da 2 filas «Rafa». **Ranking: UN «Rafa» con 24 h y 2 días** (juntó 3 filas); «Por empresa» dice «una persona con más de una empresa»; `totales_control`: 1 trabajador, 16 h; la base de trabajadores avisa `fichasRepetidas` |
| P8 | Alta por orden con nombre repetido; `separar-empresas` con «Rafa (Alfa)» y «Rafa (Beta)» | `nombre_duplicado` (bien). Separar: **para** las dos con «otra persona de la lista quedaría también como «Rafa». ¿Son la misma persona?» (bien) |
| P9 | Juego completo (30 personas, 6 empresas, 4 obras, 3 pares repetidos) cargado tal cual | `comprobar` lo marca; se publican 30 fichas, 3 nombres repetidos |
| P11 | «Rafa» estaba de baja y un fichero lo trae en `altas` | Se **reactiva** en silencio y el resumen dice «1 persona nueva» (era una existente) |
| P12 | Dos tablets crean «Pepe» con empresas distintas (la segunda llega después) | El segundo fichero queda **listo** («1 empresa puesta»): el Pepe de Alfa pasa a Beta. **Es la forma real de que entre un homónimo** |
| P13 | La misma tablet repite las mismas `altas` | Listo, sin aviso (esto es normal: la tablet las olvida cuando el PC republica la lista) |
| T1 | Tablet: «Nombre nuevo» «Rafa» + empresa Beta, existiendo «Rafa (Alfa)» | **No crea a nadie**: apunta al Rafa de Alfa y enseña unos **5 s** «ya tiene la empresa «Alfa Instalaciones»: para cambiarla usa el lápiz ✎». No se apunta nada para el PC. Quien quería otro Rafa **no puede tenerlo** |
| T2 | Lápiz: «Pepe» → «Rafa» (existe) | Pregunta bien («¿Son la misma persona? Se juntarán al pasarlo al PC, con vista previa»), pero **no dice la empresa de cada uno**; «No» solo cancela |
| T3 | «Añadir varios nombres»: «Rafa, Beta Montajes» | «Ya estaba 1: Rafa. Ya tiene otra empresa… Para cambiarla usa el lápiz» (no crea nada) |
| T4 | La base trae **dos** «Rafa» (Alfa y Beta) | La lista enseña **uno**; el desplegable enseña **uno** («Rafa · Alfa Instalaciones (ya está)»): **el de Beta no se puede elegir** (captura `ma4a_T4_…png`). Un día con los dos anotados se ve como un solo Rafa con 7,5 h |
| T5 | Doble obra: «Rafa» en OBRA UNO el 22/10, se añade en OBRA DOS | «⚠️ En otra obra hoy (OBRA UNO: 7,5 h)». Funciona **para la misma persona**; con dos Rafa avisaría por el equivocado (por lectura de código: `empresaDe` va por nombre; no medido) |
| T5b | Lo mismo con 17 h en OBRA DOS (7,5 + 17 = 24,5) | **Bloquea**: «Rafa pasaría de 24 h ese día». Con dos personas distintas sería un bloqueo falso |
| T6 | Fichero que sale tras T1 | No lleva nada del segundo Rafa (ni `altas` ni `empresas`): sus horas se anotan al Rafa de Alfa |
| T7 | Informe de la tablet con dos «Rafa» anotados el mismo día | **«Rafa · Alfa Instalaciones: 1 día, 15 h»** y «Por empresa»: Alfa 15 h (las 7,5 h del de Beta se cuentan en Alfa) |

**Dos ideas de lo medido.**
1. Lo que ya está bien **no se toca**: el PC ya impide crear dos nombres iguales (`alta_trabajador`, renombres, `comprobar`,
   `separar-empresas`). El daño entra por **dos puertas que no miran la empresa**: el campo `empresas` (P3, P4, P12) y las `altas`
   de un nombre que ya existe (P5, P11), más la tablet, que **funde en silencio** (T1, T3).
2. El cálculo, la pestaña, el informe y el ranking **no tienen fallos propios**: con nombres únicos suman bien. Se rompen solo si
   alguien les mete dos personas con el mismo nombre (P7, T4, T7). Por eso la solución más barata es **que no entren**.

## 3. Por qué el nombre es la identidad (y qué costaría cambiarlo)

Conteo de comparaciones por nombre limpio (`grep`, 30/10): tablet `key(` **93**, pestaña/ranking `claveNombre(` **25**, cálculo
`.nombre` **36**, PC `clave_nombre` **35**. Lo que sale publicado (`personal_estado.js`) lleva el **nombre**, no el id, en cada fila
de jornada y en los horarios especiales (`excepciones_horario` por nombre). El contrato de la jornada
(`PK = {nombre, horas, extra}`, esquema cerrado) tampoco lleva id.

## 4. Las tres opciones

Leyenda de coste: 0 = nada · baja · media · alta.

| Sitio | A. Nombre + empresa = persona | B. Nombre único (con pregunta y ayuda) | C. Solo avisar mejor |
|---|---|---|---|
| Contrato del fichero de la tablet | **Cambia**: cada presente lleva empresa o id (`PK` cerrado) | 0 | 0 |
| Contrato de «Generar personal» | **Cambia** (`altas`/`empresas`/`bajas` por persona, no por nombre) | 0 | 0 |
| P1 (`personal_obra.py`) | **Alta**: resolver (nombre, empresa) → id en 35 sitios; qué hace `comprobar`; los viejos ficheros (solo nombre) serían ambiguos con dos vigentes | **Baja**: 2–3 avisos nuevos; `empresa_cambiada` frena | Igual que B en el PC |
| Lector | Media: leer ficheros viejos y nuevos | **Baja**: 2 códigos más en «a revisar» | Igual |
| Cálculo, pestaña, Informe, ranking | **Alta**: clave única nueva en 36 sitios + los 3 informes | 0 | 0 |
| Catálogo publicado / `personal_estado.js` | **Cambia** (nombre único para mostrar, o id en cada fila) | 0 | 0 |
| Tablet (93 sitios) | **Alta**: lista, desplegable, 24 h, doble obra, borrador, lápiz, renombres, horarios especiales | **Media**: una pregunta, un campo, 4 textos, un aviso | **Baja**: cambiar 3 textos |
| «Generar personal» | Alta | **Media**: la misma pregunta con 3 botones y el mensaje final verdadero | Baja |
| Ficheros ya guardados (REVISIONES) | Hay que **migrarlos** (con vista previa) o mantener dos formatos para siempre | **Ninguno** | Ninguno |
| Riesgo para el dato real | **Alto**: toca la identidad de personas con horas ya contadas | **Muy bajo**: no toca ningún dato; el peor fallo es una pregunta de más | Bajo, pero **no resuelve el fondo** (T1: quien quiere otro Rafa no puede tenerlo) |
| Quien cambia de empresa | Pasa a ser **otra persona** (rompe `poner_empresa` y el lápiz) | Sigue siendo la misma (con aviso) | Igual que B |
| Qué le cuesta a Bixente | Casi nada al teclear | **Un toque y un apellido/inicial** solo cuando hay un homónimo | Nada, pero no puede crearlo |

## 5. Recomendación: B reforzada (con C dentro)

**Razones**, por orden de peso:
1. **Lo medido pide «que no entren», no «que convivan».** Todo lo que se publica y se suma va por nombre; con dos «Rafa» vigentes el
   ranking junta 24 h en uno (P7) y la tablet esconde uno (T4). Arreglarlo con A es reescribir ≈ 190 sitios para un caso que **hoy no
   existe** en la base real (15 nombres, 15 distintos).
2. **No se toca ningún dato ni contrato** (todo lo guardado sigue válido byte a byte), algo que Bixente pide siempre («no estropear lo
   que ya funciona»).
3. **La empresa es un dato que cambia** (subcontratas que se llevan gente de una obra a otra). Si la empresa fuera parte de la
   identidad, cada cambio crearía una persona nueva con las horas partidas.
4. **Ya lo hace él**: en su base hay varios nombres acabados en «(M)» (todos con la misma empresa, que empieza por M): distingue con una marca en el
   nombre cuando hace falta. B le pide lo mismo, solo cuando hace falta, y la tablet se lo recuerda.
5. **Es reversible**: si en el campo resulta que hay muchos homónimos, A sigue siendo posible después, sobre una base limpia y con
   la pregunta ya hecha.

**Lo que B no resuelve** (honesto):
- Dos personas **de la misma empresa y con el mismo nombre** que el capataz no distingue al teclear (dos «Pepe» de Alfa): la tablet
  no puede saberlo; solo puede enseñar a quién se ha apuntado y cómo crear otro (§6.2, caso «mismo»).
- Dos tablets que crean el mismo nombre **sin empresa**: el PC lo toma como una persona (con aviso informativo, §6.1).
- **Separar a dos personas que ya se juntaron por error** no tiene herramienta (hoy tampoco; `fusionar` solo junta). Se previene
  con la pregunta; si pasa, es una orden de Claude con vista previa, fuera de este diseño.

## 6. Contrato exacto (opción B)

### 6.0 Lo que NO cambia
Esquemas del fichero de la tablet (`LK`, `JK`, `PK`), del fichero de «Generar personal», del catálogo (`TK`), de la obra (`OK`,
`GJK`, `GPK`), de `personal_estado.js` y de la traza. **Un fichero viejo da el mismo resultado** salvo por los avisos nuevos de §6.1.
No hay campos nuevos, **no hay migración**, `.gitignore` no cambia (no hay ficheros nuevos de producto).

### 6.1 PC (MA4b) — `personal_obra.py`, `lector_control_horario.py`, `personal_integracion.py`

Tres códigos de aviso nuevos (`{codigo, detalle, texto}`; **el texto es lo único que ve Bixente**; sin las palabras de la guarda de
lenguaje, p. ej. «alta»):

| Código | Cuándo sale | `detalle` | Texto (provisional) | ¿Frena el fichero («a revisar»)? |
|---|---|---|---|---|
| `empresa_cambiada` | En el paso de `empresas`, cuando `_aplicar_empresa` da `accion == "cambiada"` (**había** otra empresa y es **distinta**, comparada sin tildes ni mayúsculas). No sale en `puesta` (no tenía) ni `quitada` ni `sin_cambios` | `"<nombre> \| <antes> \| <después>"` | «Rafa» pasa de la empresa «Alfa Instalaciones» a «Beta Montajes»: todas sus horas ya apuntadas se contarán en «Beta Montajes». Si es otra persona con el mismo nombre, hay que ponerle un apellido o una inicial en la tablet. | **Sí** (entra en `AVISOS_A_REVISAR`) |
| `alta_ya_existia` | En el paso de `altas`, cuando el nombre **ya existe y está activo** (hoy: `sin_cambios` mudo, P5/P13) | `"<nombre>"` | «Rafa» ya estaba en la base: este fichero lo daba por nuevo y se ha tomado como la misma persona. | **No** (solo informa; se repite sin daño al reenviar las mismas altas, P13) |
| `alta_de_baja` | En el paso de `altas`, cuando el nombre existe **de baja** y el fichero lo da por nuevo (hoy: se reactiva y dice «persona nueva», P11) | `"<nombre>"` | «Rafa» estaba de baja y este fichero lo da por nuevo: vuelve a la lista. Si es otra persona con el mismo nombre, hay que ponerle un apellido o una inicial. | **Sí** |

Reglas del PC:
1. Un nombre que llega por un **nombre anterior** sigue emitiendo `nombre_anterior_usado` y **no** `alta_ya_existia` (no se duplican avisos).
2. Con `--aceptar` el fichero se aplica igual que hoy (el cambio de empresa se hace): el aviso **frena para mirarlo**, no lo prohíbe
   (decisión de Bixente del 25/10: ningún dudoso se aplica ni se descarta en silencio).
3. `_resumen_texto` del lector debe decir «empresa cambiada» (no «empresa puesta») cuando es `cambiada` (hoy P2/P3/P12 la llaman «puesta»).
4. `personal_integracion` ya imprime los cambios de empresa (`texto_empresa`) y los avisos (menos `alta_nueva`): solo hay que comprobar
   que **imprime los tres códigos nuevos** y que sigue imprimiendo la lista de `comprobar` (nombres duplicados) en el panel/`.bat`.
5. **No cambian**: `comprobar`, `alta_trabajador`, `_aplicar_renombre`, `fusionar`, `separar_empresas`, la jornada rechazada
   que deja el fichero «listo» (prueba existente), `exportar_estado`, `aplanar`, el cálculo y el ranking.

### 6.2 Tablet (MA4c) — `generador_personal.html`

**Función pura nueva** (dentro del HTML, sin pantalla ni reloj; se prueba sacada tal cual, como `planificarGuardado`):

`clasificarNombreEscrito({ nombre, empresa, base, enLista })` → `{ tipo, existente? }` con `base = [{ nombre, empresa, activo }]`:

| Caso | `tipo` | Qué hace la tablet |
|---|---|---|
| El nombre (`key`, sin tildes ni mayúsculas) no está y no se parece a nadie | `nuevo` | Crea como hoy (`news`, `altas`, empresa) |
| No está pero **se parece** (`similar`) | `parecido` | El aviso de hoy («Se parece a… ¿Es la misma persona?») |
| Está, activo, y la empresa escrita es **vacía**, o **igual** (clave) a la suya, o **él no tiene ninguna** (no hay conflicto que detectar: completar el dato es lo normal; punto a mirar en el campo, §10) | `mismo` | Apunta al que ya está (**como hoy**; si él no tenía empresa y se escribió una, se la pone, como hoy). Cambia el **aviso**: dice a quién se ha apuntado y cómo crear otro (texto A) |
| Está, activo, **la empresa escrita y la suya son distintas y las dos no vacías** | `otra_persona_posible` | **Pregunta** (texto B). No crea ni cambia nada hasta que responde |
| Está **de baja** (`activo === false`) | `de_baja` | **Pregunta** (texto C) |

Pregunta B/C → «Sí, es el mismo»: apunta al existente, **no cambia su empresa** (para eso está el lápiz ✎) y lo dice. «No, es otra
persona»: campo de texto con el nombre escrito más un espacio, con ejemplos («Rafa B.», «Rafa Pérez»); **Crear** valida: no vacío, **distinto
de todos los que ya existen** (`key`) y publicable (`motivoNombre`); si ya existe, error y se queda; si vale, entra por el camino normal de «Nombre
nuevo» con la empresa escrita. «Cancelar» no deja rastro. **No se usan paréntesis** en los ejemplos: `separar-empresas` lee un «(x)» al
final como una empresa (medido, P8) y propondría separarlo.

Otros puntos de la tablet:
1. **Lápiz** ✎ (`guardarRenombre`): la pregunta existente dice la empresa de cada uno («Ya hay un «Rafa» (Alfa Instalaciones). ¿Son la
   misma persona? …»), y «No» enseña la ayuda de apellido/inicial (texto D) en vez de cancelar sin más.
2. **Añadir varios nombres** (`añadirVarios`): una línea cuyo nombre ya existe con **otra** empresa (`otras` de hoy) pasa a una
   categoría nueva `homonimos` (texto E): no entra, **se queda en el cuadro** para corregirla. Si no la corrige no pasa nada: la línea sigue en el cuadro, **no entra y no se guarda nada**. «Ya estaba» con la misma empresa o sin
   empresa sigue como hoy.
3. **Desplegable, lista, doble obra y 24 h: no cambian** (con nombres únicos ya funcionan, T5). El desplegable ya enseña «Nombre ·
   Empresa».
4. **Aviso defensivo** (nuevo): si el estado publicado trae **dos personas con el mismo nombre** (lo que hoy esconde a una, T4), la
   tablet lo dice arriba con un recuadro visible (texto F) en vez de callar. Es la familia «algo declarado que el motor ignora en
   silencio».
5. El fichero para el PC **no cambia de forma**: una persona creada con apellido sale en `altas` y `empresas` como cualquier nombre nuevo.

### 6.3 «Generar personal» (MA4c; cuidado con MA5, ver §9) — `personal_sagarde.html`, `intentarAnadirTrabajadores`

La misma función de decisión (`yaEnBase` ya existe). Para un nombre que **existe** (activo, con otra empresa, o de baja) la pestaña
**pregunta** (texto G) con tres botones: **«Sí, es el mismo: pasa a <empresa>»** (como hoy, pero diciéndolo: el mensaje final cambia a
texto H y la fila preparada pone «pasa de <antes> a <después>»; el fichero lleva `empresas`, no `altas`), **«No, es otra persona»**
(el mismo campo de apellido/inicial; el fichero lleva `altas` y `empresas` del nombre nuevo y **no toca** al existente) y **«Cancelar»**.
Con la misma empresa que ya tiene: no hace falta añadirlo (texto I). Para un nombre que no existe: como hoy («se ha añadido a la
empresa» solo se dice cuando de verdad es nuevo). El aviso de «nombre parecido» sigue igual.

### 6.4 Textos en llano (literales provisionales; la guarda de lenguaje los vigila en la tablet; los de la pestaña, a mano hasta MA5)

- **A** (nombre que ya está, sin conflicto de empresa): ««Rafa» (Alfa Instalaciones) ya estaba en la base: lo he apuntado en la lista. Si es otra persona, créala con un apellido o una inicial («Rafa B.»).» (sin empresa: se omite el paréntesis).
- **B** (pregunta, tablet): «Ya hay un «Rafa» (Alfa Instalaciones). ¿Es el mismo?» · botones «Sí, es el mismo» / «No, es otra persona». Tras «Sí»: «Se ha apuntado a «Rafa» (Alfa Instalaciones). Su empresa no se cambia: para cambiarla usa el lápiz ✎.»
- **B2** (otra persona): «Ponle algo que lo distinga del otro «Rafa»: un apellido o una inicial. Por ejemplo «Rafa B.» o «Rafa Pérez».» · errores: «Tiene que ser distinto de «Rafa»: añade un apellido o una inicial.» / «Ya hay un «Rafa B.». Elige otro.»
- **C** (de baja): ««Rafa» estaba de baja. ¿Es el mismo, que vuelve?» · mismos botones.
- **D** (lápiz, «No»): «Si son dos personas distintas, ponle un apellido o una inicial: «Rafa B.».»
- **E** (varios): «Ya hay un «Rafa» (Alfa Instalaciones): «Rafa» no entra. Si es otra persona, escríbela con un apellido o una inicial («Rafa B., Beta Montajes»); si es la misma, quita la línea.»
- **F** (dos iguales publicados): «En la lista del PC hay dos personas llamadas «Rafa» (Alfa Instalaciones y Beta Montajes) y la tablet solo puede enseñar a una. Cámbiale el nombre a una de ellas desde el PC.»
- **G** (Generar): «Ya hay un «Rafa» en la base (Alfa Instalaciones). ¿Es el mismo, que pasa a «Beta Montajes»?»
- **H** (Generar, mensaje final): ««Rafa» pasa de «Alfa Instalaciones» a «Beta Montajes» (queda preparado; todavía no se ha enviado).»
- **I** (Generar, ya está): ««Rafa» ya está en «Alfa Instalaciones»: no hace falta añadirlo.»
- Los tres textos del PC están en §6.1.

## 7. Casos de prueba (nombres inventados)

**PC (MA4b)** — `tests/test_personal_mismo_nombre.py` (`unittest`) y verificador oculto:
1. `empresas: [Rafa→Beta]` con «Rafa (Alfa)» existente → `empresa_cambiada`, fichero **a revisar**; sin `--aceptar` no se aplica nada (disco igual).
2. Lo mismo con `--aceptar` → se aplica y la empresa cambia (comportamiento de hoy cuando él lo acepta).
3. `empresas: [Rafa→Alfa]` y Rafa sin empresa → `puesta`, **listo**, sin aviso.
4. `empresas: [Rafa→«»]` (quitar) → listo, sin aviso.
5. `empresas: [Rafa→«alfa instalaciones»]` (mismas letras, otras mayúsculas) → `sin_cambios`, sin aviso (`_grafia_empresa`).
6. Fichero de «Generar personal» (`obra: sagarde`) con `empresas` que cambia la empresa → igual que 1.
7. `altas: ["Rafa"]` con «Rafa» activo → `alta_ya_existia`, **listo**, `altas_pedidas.accion == sin_cambios`.
8. `altas: ["  rafa "]` → lo mismo (clave sin espacios ni mayúsculas).
9. `altas: ["Rafa"]` con «Rafa» **de baja** → `alta_de_baja`, **a revisar**; con aceptar, se reactiva.
10. `altas: ["Rafa Viejo"]` que es nombre anterior de «Rafa» → `nombre_anterior_usado` y **no** `alta_ya_existia`.
10b. `empresas: [{"Rafa Viejo" → Beta}]` con «Rafa Viejo» nombre anterior de «Rafa (Alfa)» → `nombre_anterior_usado` **y** `empresa_cambiada`, a revisar (la resolución por nombre anterior no se salta el aviso).
11. Dos tablets: «Pepe» (Alfa) aplicado; segundo fichero «Pepe» (Beta) en `altas` + `empresas` → `alta_ya_existia` + `empresa_cambiada`, a revisar, disco igual.
12. La misma tablet reenvía las mismas `altas` y la misma empresa → `alta_ya_existia` informativo, **listo**.
12b. Dos tablets crean «Pepe» **sin empresa** (o con la misma): el segundo fichero → `alta_ya_existia` informativo, **listo**, una sola persona. Es el límite declarado en §5: queda **documentado por la prueba**, no resuelto.
13. El mismo fichero dos veces (mismo SHA) → `ya_aplicado`, sin segundo aviso.
14. `renombres: [Pepe→Rafa]` (existe) → sigue «a revisar» con la orden `fusionar` (regresión de P6).
15. Catálogo con dos «Rafa» vigentes → `comprobar` sigue marcando «nombres no fusionados duplicados» y `personal_integracion` lo imprime (regresión de P7).
16. Jornada con «Rafa» dos veces → `presente_duplicado`, y la prueba existente de «1 jornada que no vale / listo» sigue igual (regresión).
17. Sin ninguno de los casos anteriores, el resultado de los ficheros de las pruebas existentes es **idéntico** (mismos estados, mismos textos); foto SHA256 de las 7 obras y de `piloto_real/` sin cambios (`D:/bench_ias/_p6/foto.py`).
18. Los tres textos nuevos pasan `tests/test_lenguaje_electricista.py` (sin «alta», sin códigos con guion bajo).
19. `_resumen_texto` dice «empresa cambiada» cuando es `cambiada` y «empresa puesta» cuando es `puesta`.

**Función pura de la tablet (MA4c)** — ≥ 40 casos ocultos escritos por Claude (tabla de §6.2, con tildes, mayúsculas, espacios dobles, empresa vacía, `@AUT`, de baja, parecido, mismo nombre en `enLista`).

**Tablet (MA4c)**, Playwright, fecha 23/10/2026, 390 y 820 px:
20. «Nombre nuevo» «Rafa» + Beta con «Rafa (Alfa)» → sale la pregunta B; **no se ha creado nada** (ni `news`, ni `altas`, ni `empresas`).
21. «Sí, es el mismo» → el existente queda marcado; `empresas` **sigue vacío**; el aviso lo dice.
22. «No, es otra persona» + «Rafa B.» + Crear → `altas: ["Rafa B."]`, `empresas: [{Rafa B., Beta}]`, **«Rafa» intacto**, y `Rafa B.` marcado en la lista.
23. Campo vacío, solo «Rafa», o «rafa» → error «Tiene que ser distinto…»; «Rafa B.» ya creado → «Ya hay un «Rafa B.»».
24. «RAFÁ» / «rafa » con tilde o espacio → la misma pregunta (la clave no distingue).
25. «Rafa» con empresa Alfa (la misma) o sin empresa → **sin pregunta**, aviso A.
25b. Un nombre **parecido** («Rafaa» frente a «Rafa»), no igual → el aviso de hoy «Se parece a…» sigue saliendo y no sale la pregunta B (regresión).
26. «Rafa» sin empresa en la base y se escribe Beta → se le pone Beta, **no sale ninguna pregunta** (se comprueba que no hay `#pregunta-homonimo` ni equivalente) y `empresas` lleva `Rafa→Beta`.
27. «Rafa» de baja → pregunta C; con «No, es otra persona» + «Rafa B.» se crea «Rafa B.» y el de baja **sigue de baja**.
28. «Añadir varios»: «Rafa, Beta» → línea que se queda en el cuadro con el texto E, **sin tocar nada**; «Rafa B., Beta» → entra.
29. Lápiz «Pepe»→«Rafa»: la pregunta dice las dos empresas; «No» enseña D; «Pepe»→«Rafa B.» → renombra.
30. Desplegable y lista con «Rafa» y «Rafa B.»: **se ven los dos**, cada uno con su empresa y se pueden elegir.
31. Doble obra: «Rafa» en OBRA UNO y «Rafa B.» en OBRA DOS el mismo día → **sin** aviso falso; 7,5 + 17 h entre los dos → **no** bloquea (T5b).
32. Estado publicado con dos «Rafa» → aparece el recuadro F (hoy se esconde uno).
33. El fichero que sale: sin homónimos es **idéntico** al de antes (equivalencia byte a byte de las 16 escenas de MA1/MA2/MA3).
34. Guarda de lenguaje y recorte a 390 px: ningún texto nuevo desborda.

**«Generar personal» (MA4c)**:
35. Añadir «Rafa» a Beta con «Rafa (Alfa)» → pregunta G con tres botones; no se prepara nada hasta responder.
36. «Sí, es el mismo» → fila «pasa de Alfa a Beta»; fichero con `empresas:[Rafa→Beta]` y **sin** `altas`; mensaje H (ya no dice «se ha añadido»).
37. «No, es otra persona» + «Rafa B.» → fichero con `altas:["Rafa B."]`, `empresas:[{Rafa B., Beta}]`, Rafa intacto.
38. «Cancelar» → ni fila ni mensaje de éxito. Misma empresa → texto I. De baja → pregunta. Línea repetida en «varios» → igual por línea.
39. El fichero generado pasa por `lector_control_horario.analizar` real: en el caso 36 sale **a revisar** con `empresa_cambiada` (PC y pestaña de acuerdo).

## 8. Mutaciones que deben saltar (≥ 30 en total; las del PC y las de pantalla las rompe Claude sobre copias con `cp`)

PC: (1) no emitir `empresa_cambiada`; (2) emitirlo pero sin frenar; (3) emitirlo también en `puesta`; (4) comparar la empresa sensible a
mayúsculas/tildes; (5) `alta_ya_existia` también en `anterior` (duplica avisos); (6) `alta_ya_existia` que frena; (7) olvidar `alta_de_baja`;
(8) `alta_de_baja` que no frena; (9) el aviso con `detalle` mal cortado («|»); (10) un texto con la palabra «alta»; (11) `_resumen_texto` sigue
diciendo «puesta»; (12) el auditor no imprime los códigos nuevos; (13) cambiar `comprobar` para que no marque duplicados.
Tablet: (14) la pregunta solo salta si el nombre coincide letra por letra (`===`); (15) salta también cuando la empresa escrita es vacía; (16) salta cuando él no tiene empresa;
(17) «Sí, es el mismo» cambia la empresa; (18) «No, es otra persona» crea con el mismo nombre; (19) el campo acepta «Rafa» a secas; (20) acepta un nombre que
ya existe con otras mayúsculas; (21) «De baja» no pregunta; (22) «Cancelar» deja `news`/`altas`; (23) el desplegable vuelve a un `Map` por nombre (esconde uno);
(24) falta el recuadro de dos iguales publicados; (25) «Añadir varios» crea la línea con empresa distinta; (26) el aviso A no dice la empresa; (27) el lápiz no dice la empresa;
(28) el 24 h junta a «Rafa» y «Rafa B.»; (29) sin homónimos el HTML cambia (equivalencia rota). Generar: (30) «Es el mismo» envía `altas`; (31) «Es otra persona» no envía `altas`;
(32) el mensaje final sigue diciendo «se ha añadido» cuando movió; (33) «Cancelar» prepara algo. Todo superviviente se explica (equivalente demostrado) o se arregla la prueba.

## 9. Reparto de MA4b y MA4c (con este diseño en la mano)

**No hay cambio de datos ni de contrato.** El PC es pequeño (≈ 40 líneas + sus pruebas); la tablet y «Generar» son lo gordo.
Recomiendo **no fundir** (se verifican con verificadores distintos y cada uno merece su commit), pero **MA4b es corto**: media conversación.
Si se quiere ahorrar una conversación, MA4b puede fundirse al principio de MA4c **a condición de commitear el PC aparte**.

- **MA4b (PC)** toca: `personal_obra.py`, `lector_control_horario.py`, `personal_integracion.py` (solo comprobar que imprime), pruebas
  `tests/test_personal_mismo_nombre.py` y la lista de textos de `tests/test_lenguaje_electricista.py`. **No** toca `personal_calculo.js`
  ni `exportar_estado` (el prompt viejo de MA4b los listaba porque la opción A los pedía).
  *Verificadores ocultos de Claude* (`D:/bench_ias/_MA4b/_verif/`): `verif_pc_mismo_nombre.py` (casos 1–19 de §7 como caja negra sobre copias;
  validado: contra el esqueleto falla con una línea legible por caso, contra mi referencia pasa) y `mutar_pc.py` (mutaciones 1–13). Delegable
  (`codex:low`, datos inventados): los cambios de P1 y del lector con ese verificador. La foto SHA256 se hace yo.
- **MA4c (tablet + «Generar»)** toca: `generador_personal.html` (función pura, pregunta, campo, `añadirVarios`, lápiz, recuadro F),
  `personal_sagarde.html` (`intentarAnadirTrabajadores` y su mensaje final), `tests/verificar_generador_personal.py` (escenas, modo
  `P3_SOLO_MA4C=1`), `tests/test_personal_mismo_nombre_pantallas.py` (función pura) y `tests/test_orden_empresas_y_generar_personal.py` si
  la pestaña ya tiene arnés ahí. *Verificadores ocultos de Claude* (`D:/bench_ias/_MA4c/`): la función pura con ≥ 40 casos
  (`gemini,codex:low` la escriben; Claude valida el verificador) y las escenas 20–39 (`codex:xhigh` las escribe, mutantes 14–33 ocultos).
  Capturas a 390 y 820 px en `capturas_ma/MA4c/` (**sin** esperar su «sí»: él ya dijo que se prueba en el campo; se enseñan y se anota).
- **MA5 (colisión):** MA4c cambia `intentarAnadirTrabajadores` y su mensaje final; MA5 (F8–F12, F14, F15) retoca la misma pestaña. Que MA5
  parta del resultado de MA4c y **no rehaga** la pregunta de §6.3.
- **Hallazgos colaterales (fuera de F5, no se tocan aquí):** (a) una jornada anotada a una persona **de baja** se cuenta sin avisar (por lectura de código: `actuales.get` no mira `activo`; no medido); (b) un
  fichero con alguna jornada rechazada y otra cosa dentro queda «listo» (decisión de la prueba `test_lector_control_horario.py:260`);
  (c) la empresa es de la **persona**, no del día: un cambio de empresa aceptado reescribe la empresa de todos sus días viejos (P3; es el modelo de 08c2a, y el aviso `empresa_cambiada` lo dice). Si el campo pide historial por fechas, es otro diseño.

## 10. Lo no verificado y qué mirar en el campo

- **Nada de esto se ha probado con trabajadores reales ni en la tablet Android.** Las medidas son de un PC con Chromium/Node y datos
  inventados; la base real (15 personas) **no tiene** homónimos hoy.
- Textos y pregunta: **provisionales**. Cosas que él dirá en el campo: ¿le molesta la pregunta?, ¿prefiere que **siempre** pregunte
  al teclear un nombre que ya existe (en vez de solo cuando la empresa es distinta)?, ¿tiene dos personas de la **misma empresa** con el
  mismo nombre (el caso que B no puede detectar)?, ¿le vale «Rafa B.» o prefiere otra forma?
- El formato del `detalle` de `empresa_cambiada` (`" | "`) es una propuesta: MA4b puede cambiarlo si lo prueba contra nombres con `|`.
- `personal_integracion.py` (auditor) no se ha leído entero; solo se ha comprobado que imprime avisos, cambios de empresa y `comprobar`.

## 11. Revisión externa

`gemini` (solo texto, el diseño sin nombres reales, 49 s) listó 15 puntos; **Claude los contrastó uno a uno**. Aceptados y ya incorporados: el límite de las horas históricas al aceptar (§9 c), dos tablets sin empresa (caso 12b), nombres parecidos en la tablet (25b), «ausencia de pregunta» en el caso 26, el caso de baja con apellido (27), qué pasa si no se corrige una línea de «Añadir varios» (§6.2), el nombre anterior con empresa distinta (10b) y la fuente de «15 nombres distintos» (§1). **Rechazados con motivo:** «no hay solución para dos de la misma empresa» (ya es el primer límite de §5); «contradicción» de §6.2 (es la tabla, deliberada: sin conflicto no se pregunta); «el caso 26 no prueba la ausencia de pregunta» (lo decía: «sin pregunta»; ahora más explícito); «fusionar «Rafa B.» con «Rafa» por error» (el lápiz ya pregunta y el PC enseña vista previa, T2/P6); «textos sin verificar en el campo» (§10 ya lo dice); «sin alternativa si `comprobar` falla» (la mutación 13 existe justo para que la prueba salte si deja de marcar duplicados).

## 12. Implementación de MA4b (30/10/2026) — lo que se hizo y en qué se desvía del diseño

Hecho tal cual §6.1 (`personal_obra.py`: tres avisos y sus tres frases; `lector_control_horario.py`: `AVISOS_A_REVISAR` y `_resumen_texto`;
`personal_integracion.py` **no se tocó**: ya imprime los avisos, las líneas de empresa y los motivos que frenan, y lo comprueba la prueba).
Desviaciones y precisiones: (1) `alta_de_baja` sale **también** cuando la baja se pide por un **nombre anterior** (el detalle es el nombre vigente);
el diseño solo hablaba del nombre actual. (2) El `detalle` de `empresa_cambiada` es `"<nombre> | <antes> | <después>"` y se corta con `split(" | ", 2)`:
un nombre o una empresa con « | » dentro saldría mal cortado (no hay ninguno hoy; el texto genérico se usa si no salen tres trozos). (3) Tres pruebas
viejas fijaban el comportamiento que el diseño cambia a propósito y se han actualizado: `test_personal_obra_08a` (`test_altas_existentes_no_cambian_nada` y
`test_alta_con_un_nombre_actual_de_uno_y_anterior_de_otro_va_al_actual`: antes `avisos_lote == []`, ahora `alta_ya_existia`; y la lista `EJEMPLOS` de frases con los tres
códigos nuevos) y `test_personal_empresas_08c2a` (`test_cambiada_y_quitada…`: el resumen pasa de «2 empresas puestas, 1 empresa quitada» a
«1 empresa puesta, 1 empresa cambiada, 1 empresa quitada»). (4) Pruebas nuevas: `tests/test_personal_mismo_nombre.py` (30). No se tocó `personal_calculo.js`, `exportar_estado`, `comprobar` ni nada de las pantallas.

