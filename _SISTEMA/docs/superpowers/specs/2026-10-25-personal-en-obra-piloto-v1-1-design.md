# Personal en obra — cambios que pidió Bixente en el piloto (v1.1)

**Fecha:** 25/10/2026 · **Estado:** BORRADOR para el visto bueno de Bixente · **Autor:** Claude (Sonnet 5.5)
> **⚠ PARCIALMENTE SUSTITUIDO el mismo día (25/10/2026)** por `2026-10-25-personal-en-obra-repaso-integracion.md`, a raíz del principio de Bixente («el control horario no es una app suelta, es una aportación de datos al entorno Sagarde»). **Anulados: D1 (carpeta `PERSONAL EN OBRA`), D2 (`Recibir jornadas`/Descargas/`LOTES RECIBIDOS`) y todo el §2.** Siguen vigentes D3, D4, D5, D6 y D7. Léase primero el repaso.

**Parte de:** `2026-10-23-personal-en-obra-design.md` (especificación vigente; §17 = horario propio). Este documento NO la sustituye: la amplía.

## 0. De dónde sale

En el piloto real de Olabeaga (25/10/2026, paso 07), tras anotar y exportar su primera jornada, Bixente pidió cuatro cosas. Sus palabras:

1. «falta poder editar el nombre una vez guardado»
2. «falta poder ver la base en desplegable para elegir a los trabajadores»
3. «tiene que haber también una carpeta dentro de Sagarde para la aplicación donde guarde los datos que necesite como app, aparte de que en cada obra guarde su información» (y antes: el fichero exportado «no tendría que haber ido a una carpeta [de Descargas] sino dentro de Sagarde»)
4. «a la hora de generar un día nuevo debería de mirar qué gente hubo el día anterior y ponerlos. Así es mucho más rápido poder quitar o añadir alguno que tener que buscarlos por la base»

5. «cuando pone en la pestaña Exportar a qué se refiere, explica a un electricista, no como si fuera programador» (dicho mientras se diseñaba lo anterior; aclaró después que lo que quería era saber **qué hace esa pestaña, qué exporta y para qué**)
6. «el fichero que sale de esa exportación lo tengo que meter en qué carpeta del ordenador… yo creo que tenía que ser en la de REVISIONES, pues al final no deja de ser una revisión. El nombre del archivo debería ser CONTROL HORARIO + OBRA + FECHA al estilo 20102026, día 20 mes 10 año 2026» (con el diseño ya escrito; **sustituye a `LOTES RECIBIDOS`**)

Nada de esto es un fallo del piloto: los datos, las cifras y las demás obras están bien. Son huecos de producto.

## 1. Decisiones de Bixente (cerradas el 25/10/2026, contestadas en llano)

| # | Pregunta | Respuesta |
|---|---|---|
| D1 | ¿Dónde va la carpeta de la app? | **Carpeta propia en la raíz de Sagarde: `PERSONAL EN OBRA/`**, junto a MANTENIMIENTOS y POST-VENTAS. Cada obra sigue guardando lo suyo en su carpeta. |
| D2 | ¿Cómo pasa el fichero de la tablet al PC? | **Doble clic en `Ingerir_Personal.bat` y que él busque** los ficheros nuevos (primero en `REVISIONES` de cada obra, donde Bixente los deja a mano como las revisiones; y además en Descargas), enseñe qué trae cada uno, pida S y **guarde una copia en la carpeta `REVISIONES` de su obra** (D7, que sustituye al `LOTES RECIBIDOS` que se había elegido antes). |
| D3 | Al corregir un nombre, ¿a qué jornadas afecta? | **A toda la persona** (base y todas sus jornadas, de todas las obras). Si el nombre nuevo ya existe, se avisa de que es una fusión y se hace en el PC con simulación. |
| D4 | ¿Qué ve el desplegable de la base? | **Toda la base**, y un botón **«Añadir varios nombres»** para cargar el equipo de golpe sin apuntar una jornada. |
| D5 | Día nuevo | **Sale ya con la gente de la jornada anterior marcada**; se quita o añade a quien toque. |
| D7 | ¿En qué carpeta del PC va el fichero que sale de la tablet y cómo se llama? | **En la carpeta `REVISIONES` de su obra** («al final no deja de ser una revisión»). Nombre: **`CONTROL HORARIO <nombre de la obra> <DDMMAAAA>.json`**, con la fecha **del día que exporta** (una sola fecha; cada jornada lleva su día dentro). Ejemplo: `CONTROL HORARIO 2026 OLABEAGA BILBAO 25102026.json`. Es el mismo estilo que sus hojas (`REVISION 2026 OLABEAGA BILBAO 21102026.html`). |
| D6 | Lenguaje | **Todo lo que lee Bixente, en lenguaje de electricista**: sin «exportar», «lote», «ingerir», «pendiente», «alta_nueva»… (su frase, ver §0.5). Textos propuestos en §5b: **él los aprueba antes de aplicarlos**. |

## 2. Cambio A — Carpeta `PERSONAL EN OBRA/`

### 2.1 Estructura final

```
COPIA SEGURIDAD SAGARDE/
├─ SAGARDE OBRAS ABIERTAS/<obra>/INFORME SAGARDE IA/   personal_obra.json, personal_jornadas.jsonl   (SIN CAMBIOS)
├─ SAGARDE OBRAS ABIERTAS/<obra>/REVISIONES/           CONTROL HORARIO <OBRA> <DDMMAAAA>.json   (lo que manda la tablet; NO se publica)
├─ SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/ el código (.py) SIGUE AQUÍ: un solo hogar para el código
└─ PERSONAL EN OBRA/                                   ← NUEVA (un apartado más, como MANTENIMIENTOS)
   ├─ index.html                 (lo genera el portal; accesos a la app y al ranking)
   ├─ generador_personal.html    (la app de la tablet: a la vista, es lo que se abre)
   ├─ personal_sagarde.html      (el ranking)
   ├─ Ingerir_Personal.bat       (el botón que pulsa Bixente; excepción a la norma, igual que Actualizar_Sagarde.bat)
   └─ _SISTEMA/                  personal_catalogo.json (la base), personal_estado.js (lo que lee la tablet)
```

Cumple la norma `_SISTEMA` del `CLAUDE.md` (lo informático dentro de una `_SISTEMA`; fuera, lo que abre una persona). Las dos páginas HTML y el `.bat` se quedan a la vista por ser lo que Bixente abre/pulsa; el `.bat` va a `EXCEPCIONES` de `test_jerarquia_sistema.py` con su porqué escrito.

### 2.2 Qué se mueve y qué no

| Fichero | Hoy | Después |
|---|---|---|
| `personal_catalogo.json` | `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/` | `PERSONAL EN OBRA/_SISTEMA/` |
| `personal_estado.js` | ídem | `PERSONAL EN OBRA/_SISTEMA/` |
| `generador_personal.html`, `personal_sagarde.html` | motor | `PERSONAL EN OBRA/` |
| `Ingerir_Personal.bat` | motor | `PERSONAL EN OBRA/` |
| `personal_calculo.js` | motor | **se queda en el motor** (fuente única, con su prueba; los paneles lo incrustan desde ahí). La app y el ranking lo cargan por ruta relativa. *Decisión técnica a cerrar en el plan:* se descarta tener una copia (copias = la familia de fallos del proyecto); la prueba de publicación debe demostrar que esa ruta responde en el árbol publicado. |
| `personal_obra.py`, `personal_integracion.py`, `panel_personal.py`, `generar_todos.py` | motor | **se quedan**; solo cambian las constantes de ruta de los datos. |
| `personal_obra.json`, `personal_jornadas.jsonl` de cada obra | carpeta de la obra | **sin cambios** |

### 2.3 Publicación

- Se publican: `generador_personal.html`, `personal_sagarde.html`, `index.html`, `_SISTEMA/personal_estado.js`, `_SISTEMA/personal_catalogo.json` (líneas nuevas del `.gitignore`, **con prueba de que de verdad salen**: la trampa «generado pero nunca publicado»).
- **Los `CONTROL HORARIO … .json` de `REVISIONES/` NO se publican** (llevan nombres y horas; su contenido ya está en `personal_jornadas.jsonl`). La lista blanca no los cubre y una prueba lo demuestra: `git add -A --dry-run` no los lista.
- **¿Choca un `.json` en `REVISIONES/`?** Comprobado el 25/10/2026: la norma `_SISTEMA` (`test_jerarquia_sistema._es_tecnico`) solo cuenta como técnico el código (`.py .bat .cmd .ps1`) y sus respaldos, no los `.json`; y es un **documento recibido de obra**, como las hojas de revisión (precedente: los `.bak` de AutoCAD, 08/08/2026). Los adaptadores leen en `REVISIONES/` los `REVISION … .html`/`.pdf`; **no se ha comprobado aún que ignoren por completo un `.json` nuevo**: el plan lo prueba metiendo uno en una obra de prueba y comparando la foto SHA256 de las 7 obras (tiene que dar igual).
- Ojo: la carpeta de aguas arriba `_SISTEMA` con guion bajo: GitHub Pages las descarta sin `.nojekyll`; ya existe en la raíz. Se comprueba con una petición real a la web publicada.

### 2.4 Migración de lo que ya existe

Hoy hay 1 persona (T0001 Asensio), 1 jornada y un `personal_estado.js`. Se migran con un script que **copia, verifica byte a byte, y solo entonces** deja el original sin usar (el borrado de los viejos lo hace Bixente; no se tocan datos de obra). Nada de esto está publicado todavía, así que no hay URLs que romper: este es el momento barato de moverlo.

### 2.5 `Ingerir_Personal.bat` por doble clic

1. Localiza la carpeta de Descargas **real** de Windows (hoy `D:\Descargas`; se lee del sistema, no se escribe a fuego).
2. Busca ficheros `CONTROL HORARIO*.json` (y los antiguos `lote_personal_*.json`, como los dos de hoy) en **dos sitios**: la carpeta `REVISIONES` de cada obra abierta (**el camino normal: Bixente los deja ahí a mano, como las hojas de revisión, porque la tablet y el PC son aparatos distintos y el fichero es el único puente**) y, por si acaso, Descargas (con cualquier sufijo, p. ej. « (1)»). Un fichero está **ya recibido** si su SHA256 consta en el registro de esa obra (`personal_jornadas.jsonl`), esté donde esté: así el doble export de hoy cuenta una sola vez y uno ya recibido no se vuelve a ofrecer. *(Anotar el SHA256 en la traza es un cambio pequeño de P1 y del auditor: va al plan.)* El nombre del fichero es solo para personas: la obra y las jornadas se leen **de dentro**.
3. Para cada fichero nuevo enseña: obra, ámbito, fecha, nombres y horas, y los avisos (`alta_nueva`, `nombre_parecido`, `suma_diaria_alta`, `fecha_futura`, `renombre…`).
4. Pide **S**. Solo con S escribe y regenera **solo** la obra del lote.
5. **Guarda una copia en `<obra>/REVISIONES/`** con el nombre `CONTROL HORARIO <nombre de la obra> <DDMMAAAA>.json` (solo si algo se ha escrito; si ya existe uno con ese nombre y distinto contenido, añade « (2)»; si el fichero ya estaba en `REVISIONES`, no se copia). Un fichero rechazado no se copia y se vuelve a ofrecer con su motivo. **No borra** el original de Descargas (es de Bixente).
6. Sigue funcionando arrastrando un fichero encima, como ahora. Si no encuentra Descargas, pide arrastrar.

## 3. Cambio B — Editar el nombre de una persona (D3)

### 3.1 En la app

- Cada persona de la pantalla «Anotar» lleva un **lápiz ✎**. Al tocarlo, la fila se convierte en un campo con el nombre actual, **[Guardar nombre]** y **[Cancelar]**. Mismas reglas que «Nombre nuevo» (1–60 caracteres, sin etiquetas, sin repetirse).
- Al guardar, la app cambia el nombre **en todo lo que tiene en el aparato**: la lista, el borrador, las jornadas pendientes, su copia de la base y la memoria de horarios propios (que va por nombre). Y apunta la petición en una lista de **renombres pendientes** que viaja en el lote.
- Si el nombre nuevo **ya es de otra persona** de la base: pregunta «Ya hay un «Mikel». ¿Son la misma persona? Se fusionará al pasarlo al PC, con simulación antes.» Con *Sí* se apunta igual; con *No* no se hace nada.
- Se olvida el renombre pendiente cuando el estado publicado ya trae el nombre nuevo (mismo patrón que las jornadas y los horarios propios: «se olvida al publicarse»).

### 3.2 Contrato del lote (esquema cerrado; amplía `LK` y `TK`)

```json
{ "tipo": "lote_personal", "version": 1, "obra": "olabeaga",
  "renombres": [ { "de": "Asensio", "a": "Asensio García" } ],
  "altas": [], "jornadas": [ … ], "excepciones_horario": { … } }
```

**Orden de aplicación en el PC: `renombres` → `altas` → `jornadas` → `excepciones_horario`.** Los renombres van primero a propósito: las jornadas del mismo lote ya traen el nombre nuevo (la app las reescribe) y deben caer en la persona existente, no crear otra.

Reglas de `renombres` (cada elemento `{de, a}`, esquema cerrado):

| Caso | Resultado |
|---|---|
| `de` es el nombre actual de una persona activa y `a` es libre | se cambia el nombre en `personal_catalogo.json` **por id**; todas sus jornadas, horarios propios y fusiones siguen colgando del id. La persona guarda el nombre viejo en `nombres_anteriores`. Traza `renombre` en el `.jsonl`. |
| `a` es el mismo nombre (o solo cambian mayúsculas/acentos) | `sin_cambios` / se aplica la grafía nueva (decidir en el plan; ver 7). |
| `a` ya es el nombre de **otra** persona activa | **no se aplica**; aviso `renombre_coincide_con_otro` con los dos ids y el comando exacto `fusionar <origen> <destino>`. Las jornadas del lote ya caen en la persona existente, así que no se pierde nada: solo queda pendiente juntar las dos fichas. |
| `de` no existe (persona solo en pendientes, nunca ingerida) | aviso `renombre_sin_origen`, **no es error**: las jornadas ya traen el nombre nuevo. |
| `de` o `a` inválidos (vacío, > 60, etiquetas, algo que parezca DNI/teléfono/correo) | se rechaza el **lote entero**: `renombre_invalido` (igual que `excepcion_invalida`). |

**`nombres_anteriores`** (clave nueva y opcional de `TK`; los catálogos sin ella siguen siendo válidos): resuelve el caso de **dos aparatos** (tablet y PC): un lote antiguo que todavía diga «Asensio» se asigna a la misma persona con aviso `nombre_anterior_usado`, en vez de abrir una persona fantasma («algo declarado que el motor ignora en silencio», la regla de este proyecto). Orden de resolución de un nombre: nombre actual → nombres anteriores → alta nueva.

## 4. Cambio C — Base en desplegable y «Añadir varios nombres» (D4)

- El desplegable de «Añadir de la base» lista **toda la base** (personas activas, sin las fusionadas), por orden alfabético y con el buscador filtrándola sin distinguir tildes. A quien **ya está en pantalla** lo muestra marcado «(ya está)» y no se puede añadir dos veces.
- **«Añadir varios nombres»**: un cuadro de texto, un nombre por línea. Se ignoran líneas vacías y repetidas; cada nombre pasa las mismas reglas que «Nombre nuevo»; el resumen dice cuántos entran, cuáles ya estaban y cuáles no son válidos (con el motivo). Los válidos entran en la base **sin jornada** y quedan disponibles en el desplegable.
- Contrato: `altas: ["Mikel", "Rafa", …]` en el lote. El PC crea la persona (`alta_nueva`; `nombre_parecido` si se parece a otra) o `sin_cambios` si ya existe. Un lote que solo trae `altas` es válido. Nombre inválido → `alta_invalida` y se rechaza el lote entero.
- Las altas pendientes se olvidan igual que lo demás cuando el estado publicado ya las trae.

## 5. Cambio D — Día nuevo con la gente de la jornada anterior (D5)

**Regla:** al abrir «Anotar» para una obra + ámbito + fecha **sin jornada guardada**, la lista sale con **marcada** a la gente de la **última jornada anterior a esa fecha** de esa misma obra y ese mismo ámbito.

- «Anterior» = la última jornada **existente** antes de la fecha elegida, **no el día de calendario de ayer** (el lunes mira el viernes; un festivo o un día sin obra no deja la lista vacía). Viviendas y garajes por separado.
- Cuentan las jornadas ya ingeridas **y** las pendientes de pasar al PC; **no** las anuladas.
- Se marcan con las **horas normales de la fecha nueva** (el horario de ese día; su horario propio si lo tienen) y **sin horas extra ni notas** (eso es de ese día, no se hereda). *Supuesto a confirmar con Bixente.*
- Rótulo visible sobre la lista: «Marcados según la jornada del jueves 22/10: quita a quien no haya venido.»
- **Nada se guarda hasta pulsar «Guardar jornada».** Si la fecha ya tiene jornada, se ve lo guardado, como hoy. Si hay un borrador a medias, manda el borrador (no se pisa). Si no hay ninguna jornada anterior, sale como hoy (habituales sin marcar). «Desmarcar todos» sigue funcionando. Al cambiar fecha/ámbito/obra se recalcula.
- **Riesgo asumido por Bixente al elegirlo (rapidez):** guardar sin mirar apunta como presente a quien no vino, y esos datos se publican en el ranking. Se mitiga con el rótulo, con que no se guarde nada solo y con que corregir una jornada ya existe; no con una confirmación extra.

## 5b. Cambio E — Textos para un electricista (D6)

**Qué hay hoy (leído en la app el 25/10/2026):** la pestaña de arriba se llama «Exportar» y al pulsarla **no abre ninguna pantalla**: descarga un fichero y dice solo «Exportadas 1 jornada(s) de 2026 OLABEAGA BILBAO». No dice qué es ese fichero, dónde ha quedado ni qué hay que hacer después. Los demás textos usan las mismas palabras de programador («pendiente(s) de pasar al PC», «Exportar pendientes», «horario(s) propio(s)», «lote», «alta_nueva»…).

**Idea:** la pestaña pasa a ser una **pantalla de verdad** que cuenta lo que pasa, con los pasos, y el aviso de después ya no desaparece solo.

Pantalla propuesta (pestaña «**Enviar al PC**»):

```
Enviar las jornadas al PC

Para qué sirve: la tablet apunta quién ha trabajado cada día, pero las cuentas
(horas, extras y % de cada uno), el panel de la obra, el informe y el ranking se
hacen en el PC. Aquí preparas lo que has apuntado para llevárselo al PC.
No se envía solo: si no lo llevas, el PC no se entera.

Tienes 2 jornadas sin enviar:
  · Olabeaga · Viviendas · vie 23/10 — Asensio (7,5 h)
  · Olabeaga · Garajes   · vie 23/10 — Mikel, Rafa (15 h)

[ Preparar el fichero para el PC ]

Cómo sigue:
  1. Se guarda un fichero llamado «CONTROL HORARIO 2026 OLABEAGA BILBAO 25102026»
     en la carpeta de descargas de este aparato.
  2. Pásalo al PC como haces con las revisiones y déjalo en la carpeta
     REVISIONES de la obra.
  3. En el PC, doble clic en «Recibir jornadas» y contesta S.
Las jornadas siguen apuntadas aquí hasta que el PC las recibe y lo publicas:
no hace falta volver a anotarlas.
```

Después de pulsar, un recuadro que **se queda** (no un aviso de 3 segundos): «Listo. Se ha guardado el fichero «CONTROL HORARIO 2026 OLABEAGA BILBAO 25102026» con 2 jornadas. Ahora mándalo al PC.»

**Nombre del fichero (D7):** lo pone la app: `CONTROL HORARIO ` + nombre de la obra tal como figura en el registro + ` ` + `DDMMAAAA` del día de la exportación (reloj de la tablet) + `.json`. Se limpian los caracteres que Windows no admite en un nombre (`\ / : * ? " < > |`). Si el navegador ya tiene uno igual le añade « (1)»: el PC lo acepta igual.

| Hoy | Propuesta |
|---|---|
| pestaña «Exportar» | **«Enviar al PC»** |
| «0 jornada(s) pendiente(s) de pasar al PC» | «Sin enviar al PC: 0 jornadas» · «Sin enviar al PC: 1 jornada» · «…: 3 jornadas» (singular/plural bien) |
| botón «Exportar pendientes» | «Enviar al PC» (lleva a la pantalla de arriba) |
| aviso «No hay jornadas pendientes en esta obra» | «No hay nada por enviar: todas las jornadas de esta obra ya están en el PC.» |
| aviso «Exportadas 1 jornada(s) de … y 2 horario(s) propio(s)» | recuadro «Listo…» de arriba, con jornadas y horarios especiales contados en llano |
| «horario(s) propio(s)» / «horario propio 9 h» | «horario especial» / «horario especial 9 h» |
| botón «Empezar de cero» | «Borrar lo que llevo a medias» (ya pregunta antes de borrar) |
| cabecera «Estado publicado · 25/10/2026 15:59» | «Lista de trabajadores y obras al día: 25/10/2026 15:59» |
| «sin red: OK» | «Funciona sin cobertura: sí» |
| `Ingerir_Personal.bat` | **«Recibir_Jornadas.bat»** (propuesta de nombre: Bixente decide) |
| avisos en la consola del PC: `alta_nueva Asensio` · `nombre_parecido A ~ B` · `suma_diaria_alta` · `fecha_futura` · `reemplazo` · `traza_no_escrita` · `renombre_coincide_con_otro` | «**Nombre nuevo:** «Asensio» no estaba en la base; se añade.» · «**Se parecen:** «Mikell» y «Mikel». ¿Es la misma persona?» · ««Rafa» suma más de 12 h ese día entre todas las obras.» · «La jornada es de una fecha que aún no ha llegado (30/10): ¿es una errata?» · «Ya había una jornada de ese día en esa obra: la nueva la sustituye.» · «Guardado bien, pero no se pudo anotar en el registro.» · ««Asensio» ya está en la base como «Mikel»: si es la misma persona hay que juntarlas.» |

**Regla para todo texto nuevo o cambiado** (queda en la skill `sagarde-personal` y como comprobación): sin las palabras *exportar, importar, lote, ingerir, fichero JSON, pendiente(s), alta, base de datos, estado, simulación* en lo que lee Bixente (la **simulación** se llama «Vista previa: todavía no se guarda nada»). Frases cortas; qué ha pasado, dónde ha quedado y qué hacer después. Los códigos internos (`alta_nueva`…) siguen existiendo para las pruebas y el auditor, pero **no se le enseñan**.

**Cómo se comprueba:** una prueba recorre todos los textos visibles de la app y de la consola del `.bat` y falla si aparece una palabra de la lista (mutación: reponer «Exportar» y que salte). **Bixente ve las capturas de la pantalla nueva antes de aplicar nada**, como en el 01b.

## 6. Qué NO cambia

La fórmula de horas y extras, el cálculo del % de impacto (`personal_calculo.js`), el formato de `personal_obra.json` de cada obra, la pestaña Personal, el Informe de obra y el ranking (solo cambia **de dónde se cargan**). Las demás obras no se tocan: el criterio de «hecho» sigue siendo foto SHA256 antes/después.

## 7. Dudas pequeñas que dejo anotadas (las decido en el plan o se las pregunto)

1. Cambio de solo mayúsculas/tildes en un renombre («asensio» → «Asensio»): ¿se aplica la grafía nueva? Propuesta: **sí**, es una corrección.
2. Cuando el renombre coincide con otra persona: ¿el `.bat` ofrece fusionar con una S, o solo avisa con el comando? Propuesta: **ofrecer con S** tras otra simulación.
3. Pantalla «Jornadas»: ¿también lápiz allí? Propuesta: **no en esta versión**; solo «Anotar».

## 8. Cómo se comprobará (esbozo; el detalle va en el plan)

- **P1** (datos): pruebas nuevas con datos **inventados** para `renombres`, `altas`, `nombres_anteriores`, orden de aplicación, rechazos y `comprobar`; mutaciones sobre cada regla; las 82 pruebas actuales no se tocan.
- **Migración y carpeta:** prueba de que cada fichero que debe publicarse sale (`git check-ignore --no-index -v` + `git add -A --dry-run` sobre un repo de prueba) y de que los `CONTROL HORARIO … .json` de `REVISIONES/` no; `test_jerarquia_sistema`; mapa mental; skill `sagarde-personal`; auditor.
- **`Ingerir_Personal.bat`:** doble export idéntico = un solo ofrecimiento; fichero en Descargas y fichero dejado en `REVISIONES` (los dos caminos); un fichero ya recibido no se ofrece de nuevo; Descargas ausente; fichero rechazado no se copia; arrastrar sigue valiendo; nombre `CONTROL HORARIO … DDMMAAAA.json` bien formado (incluida una obra con caracteres raros y la colisión « (2)»); probado **sin elevar** (como lo lanza Bixente).
- **`REVISIONES/` no se contamina:** un `CONTROL HORARIO … .json` en la carpeta de una obra de prueba no cambia el resultado de ninguna obra (foto SHA256 antes/después) y `test_jerarquia_sistema` sigue verde.
- **App (P3):** escenarios de Playwright para lápiz (con y sin coincidencia), desplegable completo, «Añadir varios», prerrelleno (lunes→viernes, anuladas, pendientes, borrador, fecha con jornada, sin jornada anterior); lotes exportados validados con P1.
- **Antes de publicar:** repetir foto SHA256 de todas las obras, las suites completas, y **la jornada de Asensio sigue dando 7,5 h y 100 %** tras la migración.
- Después de publicar: peticiones reales a la web (200) y prueba en la tablet con la red apagada (Safari no probado todavía).

## 9. Orden de trabajo y reparto (propuesta)

| Paso | Qué | Quién |
|---|---|---|
| 08a | Carpeta + migración + portal + `.gitignore` y sus pruebas | Claude (guardas y rutas: no se delega) |
| 08b | P1: `renombres`, `altas`, `nombres_anteriores` | `agy`/`codex:low` con verificador nuevo y datos inventados |
| 08c | P3: lápiz, desplegable completo, «Añadir varios», prerrelleno, **pantalla «Enviar al PC» y textos en lenguaje de electricista** (capturas a Bixente antes de aplicar) | `codex:low` (leer SIEMPRE el código) |
| 08d | `Ingerir_Personal.bat` → «Recibir jornadas» / `personal_integracion.py` (Descargas, archivo, duplicados, avisos en llano) | Claude |
| 08e | Repetir el piloto de Olabeaga con lo nuevo, publicar con el sí de Bixente, web y tablet | Claude + Bixente |

Los datos reales de Olabeaga solo los ve Claude; los trabajadores IA reciben datos inventados.
