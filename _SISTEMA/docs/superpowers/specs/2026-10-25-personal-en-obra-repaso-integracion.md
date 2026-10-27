# Personal en obra — repaso de integración en el entorno Sagarde

**Fecha:** 25/10/2026 · **Estado:** PROPUESTA para el visto bueno de Bixente · **Autor:** Claude (Sonnet 5.5)
**Manda sobre:** `2026-10-25-personal-en-obra-piloto-v1-1-design.md` (que queda **sustituido en D1, D2 y §2**; el resto sigue vigente).
**Guardado también en la memoria del proyecto:** `feedback_sagarde_control_horario_es_integracion_no_app_suelta.md`.

## 0. El principio (Bixente, 25/10/2026, «lo máximo principal, no pierdas nunca esta idea»)

> «Olvídate de Recibir jornadas ni de cosas de esas: tiene que ser como hacemos con el generador de revisiones. Yo genero un control horario en tablet, lo paso a la carpeta REVISIONES y cuando le digo que actualice la obra actualiza toda la obra: las revisiones, los controles horarios y todo lo demás, y cuando haga el .bat actualiza informes y todo. La app de generar control horario **no es una app suelta, es una integración en el entorno de Sagarde**. Desde el portal de Sagarde se controlan todos los datos. La app de control horario es solo **una aportación de datos a las obras** del entorno Sagarde.»

Traducido a reglas de diseño (cualquier cosa de Personal se mide contra ellas):

1. **La app solo APORTA datos**: produce un fichero y nada más. No guarda datos maestros, no tiene su propio circuito.
2. **El fichero entra como entra una revisión**: se deja a mano en `<obra>/REVISIONES/`; entrar en la obra es parte de «**actualiza la obra**» y del **`.bat`**. Ningún `.bat` ni comando propio de «recibir/ingerir».
3. **Los datos viven en el entorno** (la obra, sus ficheros derivados, el portal) y **se ven y se controlan desde el portal**.
4. **Nada paralelo**: sin carpetas, `.bat`, altas manuales ni registros que el entorno no tenga ya para las revisiones.

## 1. El modelo a copiar: cómo entra hoy una revisión (leído en el código el 25/10/2026)

| Paso | Cómo es hoy con las revisiones |
|---|---|
| 1 | El **generador de revisiones** (`generador_revisiones.html`, en `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/`, enlazado desde el portal) se carga con `obras_revisiones.js` (el registro de **todas** las obras, publicado por el motor). |
| 2 | Genera `REVISION <OBRA EN MAYÚSCULAS SIN TILDES> <DDMMAAAA>.html` y lo descarga. No explica nada más (solo «Descargado: nombre»). |
| 3 | Bixente lo deja a mano en `<obra>/REVISIONES/`. |
| 4 | «**Actualiza la obra X**» → `actualizar_obra.py`: detecta las hojas nuevas (por fecha y SHA256), **simula**, aplica, **regenera solo esa obra** (ficha, panel, prioridades, PDF), y escribe un **informe de verificación** (antes/después, las demás obras idénticas por SHA…). Las guardas paran con código 3 si algo exige mirarlo. |
| 5 | `Actualizar_Sagarde.bat` → auditor → `generar_todos.py` (todas las obras) → portal → publica. |
| 6 | El portal (estático) lo muestra todo; para cambiar datos se pide «actualiza la obra» (o una operación del motor): **el portal no escribe datos**. |

Dos detalles que importan: el **alta de una obra** se hace una sola vez en `registro_obras.py` y desde ahí todos los caminos la conocen (no hay un alta por herramienta); y **el original se conserva** en `REVISIONES/`.

## 2. Lo construido, pieza por pieza, contra el principio

| Pieza (hoy) | Veredicto | Qué hacer |
|---|---|---|
| `generador_personal.html` (app de la tablet), en la misma carpeta que el generador de revisiones y enlazada desde el portal | **Cumple en lo básico** | Se queda donde está. Cambia: nombre del fichero que descarga, textos, y lo que ya se había pedido (desplegable completo, «Añadir varios», día nuevo con la gente anterior, nombre editable). |
| Nombre del fichero: `lote_personal_<obra>.json` | **No cumple** | → `CONTROL HORARIO <OBRA EN MAYÚSCULAS SIN TILDES> <DDMMAAAA>.json`, **con la misma función de limpieza de nombre que usa el generador de revisiones** (`safeRevisionWorkName`). Fecha = día de la exportación (decidido). |
| `personal_estado.js` (lo que lee la app): solo ofrece las obras que ya tienen `personal_obra.json` | **No cumple** | Debe ofrecer **todas las obras abiertas del registro**, como `obras_revisiones.js`, y publicarse en el mismo paso (`regenerar_obra --finalizar` / `generar_todos`). |
| «Dar de alta la obra en Personal» (`iniciar-obra`, paso manual que el piloto tuvo que hacer) | **No cumple** (circuito paralelo) | **Se elimina.** El primer `CONTROL HORARIO` de una obra crea su `personal_obra.json` solo; la obra ya está dada de alta en el registro. |
| `Ingerir_Personal.bat` + `personal_integracion.py ingerir` (su propia simulación, su S, su regeneración parcial, su exportación del estado) | **No cumple** | **Se retiran como camino.** Su lógica (detectar, simular, aplicar) pasa a **un lector del motor**, como `lector_hoja_tajos_html.py`, llamado desde `actualizar_obra.py` y desde `generar_todos.py`. |
| Buscar el fichero en Descargas / carpeta `LOTES RECIBIDOS` / apartado `PERSONAL EN OBRA/` (diseño v1.1 del mismo día) | **No cumple** | **Anulado** antes de construirlo (no existe nada en disco). La entrada es solo `REVISIONES`. |
| `personal_obra.py` (P1: datos, `ingerir_lote`, `fusionar`…), `personal_obra.json` y `personal_jornadas.jsonl` por obra | **Cumple** | Núcleo que se queda. `personal_obra.json` + traza = el equivalente de `ficha_obra.json` + `revisiones_aplicadas.jsonl`. |
| `personal_catalogo.json` (la base), en `_SISTEMA INFORME SAGARDE IA/` | **Cumple** | Se queda **donde está**: es el registro global de las apps, igual que `obras_revisiones.js`. |
| Pestaña Personal del panel, sección del Informe de obra, ranking del portal | **Cumple** | Se quedan. El ranking gana una pestaña **«Base de trabajadores»** (§4). |
| Auditor del `.bat` (esquema, datos privados, doble cálculo) | **Cumple** | Se queda y **añade**: «hay un `CONTROL HORARIO` en `REVISIONES` sin aplicar» (nada se omite en silencio). |
| Skill `sagarde-personal` aparte | **No cumple** | Se **funde** en `sagarde-actualizar-obra` (un control horario es otra clase de «hoja»). La de personal queda solo para operaciones sobre la base (fusionar, renombrar). |
| Ficheros `CONTROL HORARIO … .json` en `REVISIONES` | **Cumple, comprobado en parte** | No se publican (lista blanca); la norma `_SISTEMA` solo cuenta como técnico el código. **Pendiente de probar:** que los lectores de revisiones ignoran del todo un `.json` ahí (foto SHA256 de las 7 obras). |

## 3. El flujo nuevo, de punta a punta

1. **Tablet:** abre «Personal en obra», elige la obra, rellena y pulsa «Enviar al PC» → se descarga `CONTROL HORARIO 2026 OLABEAGA BILBAO 25102026.json`.
2. **PC:** Bixente lo deja en `2026 OLABEAGA BILBAO/REVISIONES/`, igual que las hojas.
3. **«Actualiza la obra Olabeaga»** (`actualizar_obra.py`): además de las hojas de revisión, detecta los `CONTROL HORARIO` **sin aplicar** (por SHA256 anotado en la traza de la obra), los **simula** (jornadas, personas nuevas, avisos), los aplica, regenera la obra (panel con su pestaña Personal, informe de obra, PDF) y **verifica**: las demás obras idénticas por SHA y un antes/después de las horas. Todo en el mismo informe de verificación de siempre.
4. **`Actualizar_Sagarde.bat`:** `generar_todos.py` aplica, antes de construir cada obra, los controles horarios **limpios** que aún no estén (la misma función, idempotente); los **dudosos no se aplican** y salen avisados (consola + auditor). Regenera informes, estado de la tablet, ranking y portal, y publica.
5. **Portal:** ranking, base de trabajadores y la pestaña Personal de cada obra. La tablet recibe el estado nuevo al publicarse.

**Guardas (copiadas de la filosofía de las revisiones):**

| Situación | Qué pasa |
|---|---|
| Fichero ilegible, esquema roto, o su `obra` interna **no coincide con la carpeta** donde está | **No se aplica**, error visible (no mezclar obras). |
| `alta_nueva` (primera vez que sale un nombre) | Se aplica y se cuenta en el informe. |
| `nombre_parecido`, `suma_diaria_alta` (> 12 h), `fecha_futura`, una jornada que **sustituye** a otra distinta | **Para a mirar** (código 3 en «actualiza la obra»; en el `.bat` queda sin aplicar y avisado). Se libera tras mirarlo con una opción tipo `--aceptar-controles`. |
| Jornada > 24 h por persona y día, horas inválidas, etc. | Esa jornada se rechaza (las demás entran); se cuenta en el informe. |
| Un fichero ya aplicado vuelve a aparecer (OneDrive, copia) | No se hace nada (SHA256). |
| «Última revisión manda» | Un control horario posterior de la misma obra/ámbito/fecha **sustituye** al anterior, como en las revisiones. |

## 4. «Desde el portal se controlan todos los datos»

El portal es **estático** (no escribe datos; el único servidor local escribe una sola cosa, marcar tareas en el Excel). Controlar desde el portal significa, como con las revisiones, **verlo todo ahí y pedir los cambios por el camino del entorno**. Propuesta:

- **Ver:** pestaña Personal por obra (ya está) + ranking (ya está) + **«Base de trabajadores»** nueva: todas las personas con su nombre, obras donde han estado, días, horas, última jornada, y su historia de nombres (renombres y fusiones).
- **Cambiar:** nombre de una persona, fusionar dos, añadir un grupo: desde la tablet como aportación (el lápiz y «Añadir varios» viajan **dentro del `CONTROL HORARIO`** y se aplican con «actualiza la obra») y, para correcciones puntuales, pidiéndoselo a Claude por la skill (`renombrar`, `fusionar`), con vista previa y antes/después.
- **Una sola fuente:** la base es `personal_catalogo.json` (registro global) y cada obra guarda lo suyo. La tablet **lee** de ahí al publicarse; nunca es la fuente.

## 5. Qué cambia de las decisiones ya tomadas el 25/10/2026

| Decisión | Estado |
|---|---|
| D1 Carpeta propia `PERSONAL EN OBRA/` | **ANULADA por el principio** (el generador de revisiones tampoco tiene carpeta propia: sus datos están en la carpeta del motor de Obras abiertas). La base se queda en `_SISTEMA INFORME SAGARDE IA/`. *Bixente lo confirma.* |
| D2 «Doble clic y que lo busque» | **ANULADA.** Sustituida por «actualiza la obra» y el `.bat`. |
| D3 Renombrar a toda la persona (lápiz) | **Vigente**; el renombre viaja en el `CONTROL HORARIO` y se aplica al actualizar. |
| D4 Base completa en desplegable + «Añadir varios» | **Vigente**; las altas viajan en el `CONTROL HORARIO`. |
| D5 Día nuevo con la gente anterior | **Vigente.** |
| D6 Lenguaje de electricista | **Vigente** y se amplía: también los textos de «actualiza la obra» sobre personal. |
| D7 `CONTROL HORARIO <obra> <fecha>.json` en `REVISIONES` | **Vigente y reforzada** (misma limpieza de nombre que las revisiones). |

## 6. Plan de trabajo (paso 08) — nada se toca hasta que él diga

| Fase | Qué | Quién |
|---|---|---|
| 08a | **Núcleo y lector:** P1 gana `renombres`, `altas`, `nombres_anteriores`, SHA256 en la traza y la creación automática de `personal_obra.json`; módulo `lector_control_horario` (detectar → simular → aplicar, **sin CLI propia**). Datos inventados; mutaciones. | `agy`/`codex:low` con verificador mío; yo leo el código |
| 08b | **Enganche:** `actualizar_obra.py` (detecta/simula/aplica/verifica), `generar_todos.py` y `regenerar_obra.py`, auditor; el estado ofrece **todas** las obras; se **retiran** `Ingerir_Personal.bat`, `ingerir` e `iniciar-obra`. Prueba de que un `.json` en `REVISIONES` no mueve ninguna otra obra (foto SHA256 de las 7). | Claude (guardas: no se delega) |
| 08c | **App:** nombre del fichero, pantalla «Enviar al PC» y textos, lápiz, desplegable, «Añadir varios», día nuevo precargado. Capturas a Bixente **antes** de aplicar. | `codex:low`; yo leo el código |
| 08d | **Portal y documentación:** «Base de trabajadores», skills, mapa mental y **el principio escrito en el `CLAUDE.md` del proyecto**. | Claude |
| 08e | **Segundo piloto de Olabeaga:** su jornada ya hecha se deja como `CONTROL HORARIO 2026 OLABEAGA BILBAO 25102026.json` en `REVISIONES`, «actualiza la obra», y debe dar **lo mismo** que ya tenemos (Asensio, 7,5 h, 100 %). Después, `.bat` con su «sí», web (200) y tablet. | Claude + Bixente |

**Estado real hoy:** nada de esto está publicado (`origin/main` = `20012e3`); lo ya construido vive en `main` local. Es el momento más barato para cambiarlo.

## 7. Riesgos que veo

- **Aplicar datos dentro de `generar_todos`/el `.bat`** aumenta lo que un `.bat` puede tocar. Mitigación: función idempotente, solo ficheros limpios, los dudosos nunca; auditor que lo cuenta; y la prueba de «las demás obras idénticas».
- **Fichero en la carpeta equivocada** (otra obra): lo para la guarda de obra interna ≠ carpeta.
- **Dos tablets con nombres viejos**: `nombres_anteriores` evita personas fantasma.
- **Rellenar el día con la gente anterior** (D5): riesgo aceptado por Bixente (rapidez), mitigado con el rótulo.
- **Safari/iPad sin probar**: la prueba de tablet sigue pendiente del final.

## 8. Decisiones que necesito de Bixente

1. **¿Anulamos la carpeta `PERSONAL EN OBRA`?** Recomendado: **sí** (la base se queda en la carpeta técnica de Obras abiertas, donde ya viven los datos del generador de revisiones).
2. **¿El `.bat` también aplica los controles horarios limpios** o solo «actualiza la obra»? Recomendado: **los dos**, para que nada que él deje en `REVISIONES` quede fuera de lo publicado sin que se note.
3. **¿Qué hacer con un aviso dudoso** (nombre parecido, > 12 h, fecha futura)? Recomendado: **parar y mirarlo juntos**; nunca aplicarlo ni descartarlo en silencio.
