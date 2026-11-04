# F — Centro de mando y dispositivos (PC · tablet · móvil)

**Auditoría de solo lectura y diseño en papel · 04/11/2026**
Base analizada: `main` @ `3415610` («Actualizacion 2026-11-03_2204»). No se ha modificado código ni datos, no se ha ejecutado ningún `.bat` ni nada que publique.

**Norte (Bixente):** el entorno funciona «como un ente vivo»: un cuerpo central (la base común de datos de obra), muchas extremidades (apps) que beben de ahí y la alimentan, y el **centro de mando** como forma de controlarlo. Debe funcionar en PC, tablet y móvil. «Es lo más básico.»

---

## 0. Leyenda, límites y resumen

**Certeza de cada afirmación**

| Marca | Significa |
|---|---|
| **CONFIRMADO** `fichero:línea` | Leído en código/datos versionados, o medido sobre ellos |
| **INFERIDO** | Deducido del código; no se ha visto funcionar |
| **NO VERIFICABLE** | No se puede comprobar desde aquí (motivo al lado) |

**Límites de esta auditoría (importan para fiarse de ella)**

- No hay navegador real ni dispositivo: **todo lo que dice «se ve», «se toca» o «funciona en Edge Android» es INFERIDO del código**, salvo lo cubierto por pruebas Playwright existentes, que corren en Chromium de escritorio (no en Edge Android).
- **El sitio publicado no es accesible desde esta sesión** (el proxy devuelve 403 a `bixente-69.github.io`). Lo que sé del despliegue sale de la API de Actions de GitHub (lectura) y del contenido versionado, no de ver las URL.
- **Lo no versionado no lo veo.** El `.gitignore` es lista blanca (`.gitignore:2`, `*`). No he podido abrir: `resumen_obras.json`, `postventas_resumen.json`, `auditoria_diagnostico.json`, `Actualizar_Obras.bat`, `FICHA DE OBRA.xlsx`, las hojas `.xlsx` de materiales, `_cache_resultados_regen.json` ni las 17 carpetas de obra sin seguimiento. `git check-ignore` confirma que los cuatro primeros están ignorados.
- El clon es superficial (66 commits). La cadencia de publicación sale de la API de Actions (180 despliegues), no del `git log`.
- No se copia ningún dato personal de trabajadores. Donde se habla de ficheros de personal se citan **solo nombres de campo y recuentos**.

### Resumen

1. **El portal móvil NO está obsoleto** (el mapa mental se equivoca): se genera en cada pasada (`sagarde_portal.py:1676`), está commiteado el 03/11 22:04 y lo cubre `tests/test_portal_movil.py`. Lo que sí está es **huérfano** (ningún enlace de la navegación lleva a él) e **incoherente** con el de escritorio (2 tipos de alerta frente a 6; ordena por avance, no por riesgo).
2. **El centro de mando hoy VE poco y CONTROLA nada.** Ve: avance, última revisión, bloqueos y 6 avisos. No ve: frescura por tipo de dato, ni ficheros pendientes en `REVISIONES`, ni si el `.bat` falló o si la última subida llegó. Controla: solo el botón «Hecho», y solo en `localhost`.
3. **Los avisos de «controles horarios sin aplicar» llegan al portal con etiqueta falsa y un paso de retraso** (INFERIDO por el orden del `.bat`): salen como «avisos de formato en archivos de inspección» (`sagarde_portal.py:1426`) y se calculan *antes* de aplicarlos.
4. **Nada en la página detecta «nadie ha ejecutado el .bat».** Solo hay un sello pasivo. Y el `.bat` imprime «Portal actualizado» tras el `push` sin esperar a Pages (`Actualizar_Sagarde.bat:118`). Pages sí expone el estado de cada despliegue (180 ejecuciones; las 12 últimas, correctas).
5. **«Avance medio 42 %» está contaminado**: media simple de 7 tarjetas que incluye **OBRA PRUEBA** (16 %) y **GORLIZ** (0 % por no tener base: desconocido convertido en cero). Sin esas dos, 55 %. Comprobado con aritmética sobre el `index.html` publicado (§1.2, H-04).
6. **Muchos enlaces de lo publicado apuntan a ficheros que no se publican** (PDF, DOCX, JPG, DWG y carpetas de OneDrive): fuera del PC dan 404. `comprobar_enlaces.py` no lo ve porque comprueba el **disco**, no lo **publicado**. Medido contra `git ls-files`: p. ej. 123 de 211 enlaces internos de Post-ventas y 131 de 153 en el panel de Bolueta (H-17).
7. **Los 7 `panel.html` publicados llevan una ruta de Windows (`D:\Nueva carpeta\OneDrive\…`) y un enlace a `Actualizar_Obras.bat`**, que el `.gitignore` deja sin publicar: la pestaña «Actualizar» es inútil en tablet/móvil.
8. **Tablet de Personal: la mejor pieza del entorno para campo** (PWA, red-primero con 4 s, 13 escenas Playwright, objetivos de 44–48 px). Sus huecos: no pide almacenamiento persistente y no protege contra dos pestañas.
9. **El generador de revisiones no abre sin cobertura una vez cerrado** (sin service worker; `obras_revisiones.js?v=Date.now()` rompe la caché HTTP): justo el caso de un garaje sin red. INFERIDO.
10. **Hay datos de trabajadores en el repo público** (`personal_catalogo.json` lleva `nombre`, `empresa`, `categoria` de 22 personas). Es decisión documentada de Bixente (`.gitignore:70-80`), pero conviene reconsiderarla: el panel de salud propuesto **no puede** llevar nombres.
11. **Recomendación:** un fichero de estado único (`estado_ente.js`) que regenere el `.bat`, una vista `SALUD.html` que lo pinte con **edad calculada en el navegador** y cada alarma con su **orden copiable**. 10 pasos pequeños, cada uno con su prueba (§4.6).

---

## 1. ¿Qué es hoy el centro de mando?

### 1.1 Qué se genera y por quién

| Pieza | Fichero publicado | Lo escribe | Evidencia |
|---|---|---|---|
| Portal de escritorio («Centro de mando») | `index.html` | `build_html()` | `sagarde_portal.py:1519`, escritura `:1677` |
| Portal móvil (5 pestañas) | `_SISTEMA/PORTAL SAGARDE.html` | `generar_portal_movil()` | `:1018-1175`, llamada `:1676` |
| Índice de obras abiertas | `SAGARDE OBRAS ABIERTAS/index.html` | `generar_index()` de `generar_todos.py` | `generar_todos.py:1227` |
| Panel de obra (×7) | `<obra>/INFORME SAGARDE IA/panel.html` | `panel_obra.generar_panel()` | `panel_obra.py:1810` |
| Índices de área | `APLICACIONES/`, `VARIOS/`, `SAGARDE (OLD)/index.html` | `generar_index_*` | `sagarde_portal.py:790-980` |
| Post-ventas / Mantenimientos | `POST-VENTAS/index.html`, `MANTENIMIENTOS/index.html` | sus propios `*_index.py` | `Actualizar_Sagarde.bat:40-47` |
| Registro del generador | `obras_revisiones.js` | `publicar_registro_revisiones()` | cabecera del fichero (`generado` por obra) |
| Estado de personal | `personal_estado.js` | `exportar_personal_estado()` | `generar_todos.py:1778` |

Los datos de entrada del portal (`resumen_obras.json`, `postventas_resumen.json`, `auditoria_diagnostico.json`) **no se publican** (ignorados por `*`). Todo lo que la página muestra va **incrustado en el HTML en el momento de generarlo**. Consecuencia de diseño: la página no puede releer nada ni calcular una edad por sí sola.

### 1.2 Qué puede VER del cuerpo

| Lo que querría ver | ¿Lo ve hoy? | Dónde / límite | Certeza |
|---|---|---|---|
| Avance por obra | Sí (% ponderado + sparkline + variación) | `sagarde_portal.py:1560-1570`. **Solo el %**, no el desglose `X/M/slash/P/?/N` que `CLAUDE.md §3` exige para no fiarse del redondeo | CONFIRMADO |
| Última revisión por obra | Sí, **una fecha** | `:1566` (`ultima_revision`) | CONFIRMADO |
| Frescura **del portal** | Sí, pasiva | «Actualizado dd/mm hh:mm» `:1644`; «datos del …» `:1572, :1582`. Dice cuándo se generó, no si es reciente | CONFIRMADO |
| Frescura **por tipo de dato** (revisión / personal / materiales / notas / informe PDF / postventa) | **No** | Solo existe en cada panel por dentro. En portada no hay ni un sello por tipo | CONFIRMADO |
| Última aportación por obra | Parcial | `ultima_actividad_obra()` toma el `mtime` de **cualquier** fichero de la obra salvo `INFORME SAGARDE IA` (`generar_todos.py:1182-1202`). Una foto o una sincronización de OneDrive apagan el aviso de inactividad | CONFIRMADO |
| Ficheros pendientes de aplicar | **Solo personal**, y mal | `personal_integracion._controles_sin_aplicar` (`:542`) los detecta; el portal los muestra como «avisos de formato» (`:1426`), máximo 3 | CONFIRMADO |
| Hojas de revisión pendientes de aplicar | **No** en el portal | Existe `actualizar_obra.detectar_hojas` (`:245`) pero es una orden de consola, no una señal publicada | CONFIRMADO |
| Alarmas | 6 tipos | `construir_alertas` `:1333-1430`: bloqueos, sin cambios, obra inactiva >14 d, mantenimiento >90 d, post-venta con pendientes, avisos de auditoría | CONFIRMADO |
| «Declarado e ignorado» (un recuento de 0) | **No en la página** | Sí en consola: `generar_todos._controles_horarios_de_obra` imprime siempre una línea «un recuento de 0 es una alarma» (`:1759-1773`). No se publica | CONFIRMADO |
| ¿Falló un paso del `.bat`? | Solo en el PC | `OBRAS_FALLO` (`.bat:35`) y mensaje final (`:130`); la página publicada no lo sabe | CONFIRMADO |
| ¿Llegó el `push` / se desplegó Pages? | **No** | El `.bat` da por bueno el `push` sin esperar el build (`:113-118`) | CONFIRMADO |

**Hallazgos concretos de esta tabla**

- **H-02 · Etiqueta falsa y retraso de una pasada (INFERIDO).** El auditor corre en el paso `[0/6]` (`.bat:14`) y escribe `auditoria_diagnostico.json`. `generar_todos` aplica los controles horarios en `[1/6]` (`generar_todos.py:2093`). El portal (paso `[3/6]`) lee el JSON del paso 0 (`sagarde_portal.py:1414`). Resultado probable: en la pasada en que se aplican, el portal publicado sigue diciendo que están «sin aplicar». Además `aviso_caducado(None)` es `False` (`avisos.py`), así que estos avisos no caducan por antigüedad. No lo he ejecutado: confirmar con una pasada de prueba.
- **H-04 · KPI «Avance medio 42 %».** `escribir_resumen_json` promedia `r['pct_ponderado'] or r['pct']` de todas las obras con datos (`generar_todos.py:1334`). Sobre el `index.html` publicado:
  `(0 + 15 + 77 + 16 + 90 + 94 + 0) / 7 = 41,7 → 42 %` (coincide con el KPI publicado). Contiene OBRA PRUEBA (16 %, es un banco de pruebas) y GORLIZ (0 %: «registrado pero sin revisión ni base», `SAGARDE_MAPA_MENTAL_ENTORNO.md:96`), o sea **desconocido sustituido por cero** (`CLAUDE.md §7`). Sin ambas: `(0 + 15 + 77 + 90 + 94) / 5 = 55,2`. Y es media simple, sin ponderar por tamaño (Barakaldo tiene 4140 celdas; Prueba, 1178). El KPI no sirve para decidir nada.
- **H-08 · «Inactividad» ≠ «sin revisión».** El aviso de obra inactiva usa `mtime` de OneDrive. Cualquier fichero tocado en la carpeta de la obra lo reinicia, aunque no haya ninguna revisión nueva.
- **H-16 · «Obras abiertas = 24»** cuenta carpetas (`contar_obras_abiertas_carpetas`), no obras vivas: 7 tienen seguimiento. Las otras 17 no puedo verlas (NO VERIFICABLE). Mezclar ambas cifras en un KPI invita a malinterpretar.
- **H-05 · Dos consumidores, dos comportamientos.** Una obra que no se regenera (`panel_actualizado = False`) **desaparece** de la portada de escritorio (filtro `:1558`) pero **sigue** en el móvil con cifras viejas y sin marca (filtro `:1065`). El `.bat` termina con «Ya se ha publicado igual» (`.bat:130-137`). Es la misma familia que el resto del proyecto: algo declarado que se ignora en silencio.

**Lo que está bien resuelto (para no estropearlo)**

- `avisos.py` unifica la caducidad (400 días) y los contratos sin aviso, con motivo visible.
- `comprobar_enlaces.py` y el auditor ya intentan que los fallos se vean (aunque `comprobar_enlaces.py` mira el disco, no lo publicado: H-17); `tests/test_portal_movil.py` nació de un fallo real (la función no escribía nada durante 2 semanas).
- Convención «un 0 es una alarma» ya aplicada en la consola de personal.

### 1.3 Qué puede CONTROLAR de verdad

**Desde el sitio publicado: nada.** Es estático. Las únicas escrituras de toda la interfaz:

| Mecanismo | Qué escribe | Dónde funciona | Evidencia |
|---|---|---|---|
| Botón «Hecho/Deshacer» del panel | Marca tarea en `FICHA DE OBRA.xlsx` | **Solo** con `Abrir_Panel_Local.bat` → `http://127.0.0.1:8765` | `panel_server.py:15-18, :64`; `panel_obra.py:1077`. En Pages falla **con aviso claro** (`:1131-1141`) y revierte la casilla: bien resuelto |
| Generador de revisiones | Descarga un `.html` rellenado | PC/tablet/móvil (Blob + `a[download]`) | `generador_revisiones.html:1812-1815, :2501-2505` |
| Tablet de Personal | Descarga/comparte `CONTROL HORARIO … .json` | PC/tablet/móvil | `generador_personal.html:3821-3825, :3848-3866` |
| «📋 Copiar ruta completa» del panel | Copia al portapapeles una ruta `D:\…` | Solo útil en el PC de Bixente | `panel_obra.py:2305` |

Todo lo demás se ordena **fuera de la página**: «actualiza la obra» (skill), `actualizar_obra.py`, `Actualizar_Sagarde.bat`, «renombrar/fusionar» (skill de personal). Es decisión de diseño explícita (`CLAUDE.md §7c`, regla 3: «el portal es estático… los cambios se piden por el camino del entorno»). **No la discuto: la propuesta la respeta.**

Matiz que importa: **el mismo HTML se sirve en dos contextos con poderes distintos.** En el PC se abre por `file://` (enlaces a `.bat`, `.docx` locales, `panel_server`); en Pages no. Ninguna página detecta en qué contexto está y ajusta sus controles (la tablet de Personal sí: `test_11_desde_file_funciona_sin_worker_ni_aviso`).

### 1.4 Qué le falta para ser el sitio único desde el que se gobierna

Opinión crítica: **con un sitio estático y la regla 7c, «gobernar» no puede ser «ejecutar»; tiene que ser «ver con honradez y formular la orden exacta».** El cuerpo vive en OneDrive/PC; Pages solo conoce lo que el `.bat` le cuenta en cada pasada. Un centro de mando honesto dice *«esto es lo que sé, de hace X, y esto es lo que no sé»*. Hoy no dice lo segundo.

| # | Falta | Por qué importa |
|---|---|---|
| G1 | Edad **viva** de cada dato (calculada en el navegador, no pintada al generar) | Sin ella, un portal olvidado parece sano |
| G2 | Frescura **por tipo y por obra** (revisión, personal, materiales, notas, informe PDF) | Hoy solo hay una fecha de revisión por obra |
| G3 | **Pendientes** visibles: hojas y controles en `REVISIONES` no aplicados, con su obra | Es el eslabón manual donde más se pierde |
| G4 | **Salud de la tubería**: resultado de cada paso del `.bat` y si la última subida se desplegó | Hoy solo se entera quien mira la consola |
| G5 | Alarmas de **declarado e ignorado** en la página (recuento 0 / obra sin base / obra del registro sin tarjeta) | Es la familia de fallo de este proyecto |
| G6 | **Orden copiable** junto a cada alarma | Cierra el bucle sin backend |
| G7 | **Un solo cálculo de alertas** para escritorio y móvil | Hoy divergen (6 frente a 2) |
| G8 | **Conciencia de contexto** (`file://` / Pages / `localhost`) | Evita controles muertos y rutas `D:\` en tablet |
| G9 | Coherencia de KPI (excluir pruebas, no convertir desconocido en 0, mostrar desglose) | H-04 |

---

## 2. Matriz PC / tablet / móvil

Convención: ✔ abre y es usable · ◐ abre pero con limitación · ✘ no funciona · ? no se puede saber. Todas las celdas de tablet/móvil son **INFERIDAS del código** salvo las marcadas CONFIRMADO.

### 2.1 Matriz por pieza

| Pieza | PC | Tablet | Móvil | Responsive y táctil | Sin cobertura | Dependencias que rompen en tablet/móvil |
|---|---|---|---|---|---|---|
| **Portal** `index.html` | ✔ | ✔ | ✔ | Viewport `:1601`; 3 saltos (1000/900/600 px) `:1631-1633`. En ≤600 px **se oculta la barra superior de áreas** (`.top-actions{display:none}`, `:1633`) pero las tarjetas de área siguen | ✘ (sin SW ni almacenamiento) | Pie: «Ejecuta Actualizar_Sagarde.bat» (`:1644`), no ejecutable fuera del PC. Vídeo de portada autoplay de **1,03 MB** (`VARIOS/VIDEOSAG.mp4`, `:1635`) en cada visita |
| **Portal móvil** `_SISTEMA/PORTAL SAGARDE.html` | ✔ | ✔ | ✔ | Viewport; barra de pestañas con scroll horizontal; `.tp` ≈ 37 px de alto (11 px de relleno + 12 px de texto, `:996`) | ✘ | **Huérfano**: no lo enlaza ninguna página de navegación (ver §2.2) |
| **Índice de obras abiertas** | ✔ | ✔ | ✔ | Viewport + 2 saltos | ✘ | Pie con `.bat` |
| **Panel de obra** (×7, 0,15–1,3 MB) | ✔ | ✔ | ◐ | Viewport `panel_obra.py:2376`; saltos 768/760/640 px; tablas con `.table-scroll{overflow-x:auto}` `:79`. Barra de pestañas con `flex-wrap` (`:62`): 10–13 botones de ≈ 34 px (9 px de relleno + 13 px de texto, `:63`) ocupan **varias filas** en móvil | ✘ | Pestaña «Actualizar»: ruta `D:\…` y enlace a `Actualizar_Obras.bat` que da 404 (H-06). «Hecho» solo con `localhost` |
| **Prioridades** (pestaña `v-prioridades` del panel) | ✔ | ✔ | ◐ | Hereda el panel; índice flotante con salto a 768 px `:196`. Los JSON enlazados pesan hasta **5,1 MB** (`prioridades_trabajos.json` de Barakaldo) | ✘ | Ninguna propia |
| **Generador de revisiones** | ✔ | ✔ | ◐ | Viewport; solo 5 `@media` (el asistente oculta la barra lateral a 600 px, `:199`); 23 coincidencias de eventos táctiles/puntero; 1,38 MB + 527 KB de `obras_revisiones.js` | **✘** tras cerrar: sin SW; `obras_revisiones.js?v=Date.now()` (`:358`) nunca acierta en caché | Ninguna de Windows. Salida por descarga (`:1812-1815`) o imprimir (`:1825`) |
| **Tablet de Personal** `generador_personal.html` | ✔ | ✔ (diseñada para esto) | ✔ | Viewport con `viewport-fit=cover,interactive-widget=resizes-content`; objetivos **44–48 px** declarados (`min-height` en CSS líneas 30, 55, 133, 144, 196, 222, 283, 325) | **✔** PWA + SW red-primero (4 s) + `localStorage`; 13 escenas Playwright | Ninguna (el `.bat` solo se nombra en un texto de ayuda `:3763`). La **primera** visita exige red |
| **Ranking de Personal** `personal_sagarde.html` | ✔ | ✔ | ◐ | 1 solo `@media`; 9 coincidencias de alturas ≥ 44 px | ✘ | Texto de ayuda con «.bat» (`:2165`) |
| **Informe de obra a la carta** (dentro del panel) | ✔ | ◐ | ◐ | Selección guardada en `localStorage` por obra (`panel_obra.py:2576-2582`); salida con `window.print()` (`:2814`) | ✘ | Depende del diálogo de impresión del navegador |
| **Tierras** `app_informe_tierras.html` | ✔ | ✔ | ◐ | Viewport; 2 `@media`; 19 coincidencias táctiles/puntero | ◐ (estado en `localStorage`, 17 usos; la tipografía de Google es opcional) | Fuentes de `fonts.googleapis.com` |
| **Baterías** `app_informes.html` | ✔ | ✔ | ◐ | Viewport; 3 `@media` | ◐ (4 usos de `localStorage`) | Ídem; 10 puntos de descarga |
| **Buscador Eléctrico** | ✔ | ✔ | ✔ | Viewport; 310 líneas, simple | **✘ por diseño**: cada consulta es un `POST` al Worker (`:101, :262`) | Servicio externo en `workers.dev`; la clave la teclea el usuario y se guarda en `localStorage`. El nombre del Worker incluye «spike» (¿prototipo?) |
| **Post-ventas** `POST-VENTAS/index.html` | ✔ | ✔ | ◐ | Viewport; 2 `@media` | ✘ | **123 de 211 enlaces internos apuntan a ficheros no versionados** (45 PDF, 29 DOCX, 13 JPG, 31 carpetas): 404 fuera del PC (H-17). Las 82 vistas HTML de los Word sí están publicadas |
| **Mantenimientos** | ✔ | ✔ | ✔ | Viewport; página ligera (6 KB) | ✘ | Pie con `.bat`. Sus 10 enlaces internos sí están publicados |

**Qué sirve hoy en el móvil:** la portada (`index.html`, responsive), los paneles (usables pero con pestañas apiladas), la tablet de Personal (la única verdaderamente pensada para móvil/campo) y el Buscador. El portal móvil dedicado existe, pero casi nadie llega a él.

### 2.2 Veredicto sobre el «portal móvil obsoleto»

**Falso a fecha de hoy.** Evidencia:

- `generar_portal_movil` escribe de verdad (`sagarde_portal.py:1174`) y `main()` la llama (`:1676`).
- El fichero está commiteado el 03/11/2026 22:04 y su sello coincide («Centro de mando · 03/11/2026 22:04»). Lleva 6 KPI (24 / 7 / 42 % / 112 / 31 / 4), una alerta de bloqueos y 7 tarjetas.
- `tests/test_portal_movil.py` existe y explica por qué (la función estuvo del 25/07 al 08/08 sin escribir nada).
- Lo que el mapa llama «código inalcanzable» **sigue ahí, pero es otra cosa**: las líneas **1216-1330 son código muerto dentro de `_render_variacion_badge`** (AST: la función va de la 1205 a la 1330, con 16 sentencias; todas las ramas devuelven antes). Es una versión anterior y más rica del portal móvil (sparkline, variación, «Sin panel IA») que ya no se ejecuta. Referencia nombres no definidos (`ro`, `mant`…). Inofensivo, pero engaña a quien lo lea.

**Lo que sí está mal:**

1. **Huérfano.** El único enlace entrante es el botón «volver» de la tablet de Personal, y solo si el `referrer` contiene `PORTAL SAGARDE` o `_SISTEMA` (`generador_personal.html:1874-1875`). `discover_apps()` lo excluye porque `_SISTEMA` está en `IGNORE_DIRS` (`sagarde_portal.py:25-26`). Ni `index.html` ni `APLICACIONES/` lo enlazan. Hay que conocer la URL.
2. **Incoherente con el de escritorio** (`CLAUDE.md §3`: «comprobar que todos los consumidores muestran el mismo desglose»):
   - alertas: móvil `:1044-1057` = 2 tipos; escritorio `construir_alertas` = 6;
   - orden: móvil por avance descendente (`:1065`), escritorio por riesgo (`:1559`);
   - sin sparkline ni variación en el móvil; sin desglose en ninguno.
3. **Enlaces relativos con `../`** (`:1061`): correctos mientras el fichero siga en `_SISTEMA/`.

### 2.3 Edge para Android: qué puede fallar (todo INFERIDO salvo lo marcado)

| Tema | Riesgo | Fundamento |
|---|---|---|
| Descargas de revisiones/controles | Re-descargar el mismo fichero lo renombra «… (1).html». **CONFIRMADO que ocurre**: hay revisiones con ` (1)` en `REVISIONES/` (p. ej. `REVISION 2025 GERNIKA 32V 25092026 (1).html`). Para controles horarios el SHA-256 evita aplicar dos veces el mismo contenido (`lector_control_horario.py:8-11`) | `a[download]` + Blob |
| Compartir el fichero desde la tablet | `navigator.share({files})` requiere HTTPS y gesto del usuario; la app ya lo comprueba con `canShare` y cae a descarga (`generador_personal.html:3848-3866`) | Bien resuelto |
| Instalar como app | Edge Android permite «Añadir a pantalla de inicio»; el manifest tiene iconos 192/512 y `start_url` relativa. SW con alcance estrecho `./generador_personal.html` (`:1002`) | Prueba 12 y 13 de Playwright (escritorio) |
| Persistencia de las jornadas sin enviar | La única copia vive en `localStorage`. **No se llama a `navigator.storage.persist()`** (0 coincidencias en el fichero). Si el usuario borra datos del sitio o el navegador libera espacio, se pierden | H-10 |
| Dos pestañas / dos instancias | **No hay evento `storage`, `BroadcastChannel` ni `navigator.locks`** (0 coincidencias en ambos generadores): lectura-modificación-escritura sin bloqueo → gana la última | H-10 |
| `window.print()` → PDF (informe a la carta) | Edge Android ofrece «Guardar como PDF», pero paneles de 1 MB con `@media print` pueden tardar o paginar mal. **NO VERIFICABLE** sin dispositivo | `panel_obra.py:2814` |
| Portapapeles | `navigator.clipboard.writeText` exige contexto seguro: vale en Pages (HTTPS), falla desde `file://`; el panel ya muestra «Error» si falla (`:2305`) | Bien resuelto |
| CSS moderno | El panel usa `color-mix()` (`panel_obra.py:208`): requiere Chromium ≥ 111. Edge se actualiza solo; riesgo bajo | — |
| Objetivos táctiles | Pestañas del panel ≈ 34 px y del portal móvil ≈ 37 px, por debajo de los 44–48 px habituales. La tablet de Personal sí cumple | CSS citado arriba |
| Primera visita de la tablet | Sin red no hay SW instalado → no abre. Documentado en `.gitignore:82-85` | — |
| Generador de revisiones sin red | Ver §2.1: una vez cerrado, no vuelve a abrir | H-11 |
| Autoplay del vídeo de portada | `muted playsinline` está permitido; consume ≈ 1 MB de datos por visita | `sagarde_portal.py:1635` |

---

## 3. Circulación entre dispositivos

### 3.1 El camino exacto (hoja de campo → portal)

```
 CAMPO (tablet / móvil)                         PC (OneDrive)                          NUBE
 ─────────────────────                          ─────────────                          ────
 A. Personal
  generador_personal.html ──"Enviar"──▶ CONTROL HORARIO <OBRA> <DDMMAAAA>.json
  (localStorage = única copia)             en Descargas (o share)
                                                │  ① paso MANUAL (OneDrive / cable / mensaje)
 B. Revisión de tajos                           ▼
  generador_revisiones.html ──descarga──▶ REVISION … .html ──▶ <obra>/REVISIONES/
                                                │
                                                │  ② «actualiza la obra <X>»  (skill, solo esa obra)
                                                │     actualizar_obra.py  [simula → --escribir]
                                                │     → ficha_obra.json, personal_obra.json,
                                                │       personal_jornadas.jsonl, revisiones_aplicadas.jsonl
                                                ▼
                                       ③ Actualizar_Sagarde.bat  (git add -A en main)
                                          [0] auditor → auditoria_diagnostico.json
                                          [1] generar_todos → paneles, prioridades, obras_revisiones.js,
                                                              resumen_obras.json, personal_estado.js
                                          [2] post-ventas / mantenimientos
                                          [3] sagarde_portal → index.html + PORTAL SAGARDE.html
                                          [4] comprobar_enlaces   [5] mapa mental
                                          [6] git add -A · commit · push origin main ──────────▶ ④ GitHub Pages
                                                                                                  (build ≈ 30–95 s)
 ◀──────────────────────────── ⑤ la tablet lee personal_estado.js (SW: red primero, 4 s, si no copia) ◀───┘
   concilia: lo publicado desaparece de «sin enviar»      (cierra el bucle de Personal)
 ◀──────────────────────────── ⑥ el generador lee obras_revisiones.js (estados precargados en la hoja siguiente)
```

Hechos medidos del despliegue (API de Actions, lectura): 180 ejecuciones de «pages build and deployment»; la última, `head_sha 3415610`, creada 03/11 21:04:55Z y terminada 21:05:34Z, **correcta**; las 12 últimas, todas correctas. Hubo un hueco de ≈ 67 h (29/10 12:38Z → 01/11 07:30Z): **es normal** y condiciona los umbrales de §4.

### 3.2 Puntos de rotura y qué avisa hoy cada uno

| # | Rotura | Qué pasa | Quién avisa hoy | Certeza |
|---|---|---|---|---|
| 1 | El fichero no sale de la tablet | El PC no se entera | La **tablet** sí lo dice si se abre («Tienes cambios sin enviar», `:3745`; «las jornadas siguen apuntadas aquí hasta que el PC las recibe y se publica», `:3764`). El PC/portal: **nada** | CONFIRMADO |
| 2 | Llega, pero mal nombrado, duplicado o dudoso | Se clasifica LISTO / A_REVISAR / RECHAZADO; el duplicado idéntico no se reaplica (SHA-256) | Consola del `.bat` y aviso en portal (con la etiqueta equivocada, H-02). Una revisión HTML sin fecha en el nombre se ignora, con aviso `NOMBRE_FECHA_INVALIDA` del auditor | CONFIRMADO |
| 3 | Nadie dice «actualiza la obra» / nadie lanza el `.bat` | La página envejece | **Nadie.** Solo el sello pasivo | CONFIRMADO |
| 4 | El `.bat` falla en un paso | Se publica igual con datos viejos de esa obra | Consola y recuadro final; la página no lleva marca (H-05) | CONFIRMADO |
| 5 | **`git push` falla (HTTP 408, «RPC failed»…)** | Los cambios quedan solo en local; Pages sigue en la versión anterior | `[ERROR] No se pudo subir…` + `pause` + `exit /b 1` (`.bat:113-117`), **solo en el PC**. La página no sabe que va atrasada. La causa del 408 es **NO VERIFICABLE** (no hay trazas en el repo). Contexto medido: pack de 40 MiB; cada pasada toca ≈ 150 ficheros (`3415610`: 148 ficheros; `b2d4562`: 160 ficheros y 29 833 inserciones); hay JSON de hasta 5,1 MB | CONFIRMADO (cifras) / NO VERIFICABLE (causa) |
| 6 | El `push` entra pero Pages no despliega | La web no cambia | El `.bat` ya imprimió «Portal actualizado en…» (`:118`). **Falso OK.** Visible en GitHub → Actions | CONFIRMADO |
| 7 | Caché | Tras publicar, hasta ≈ 10 min con la versión anterior (Pages cachea ~600 s: **conocimiento externo, NO VERIFICABLE desde aquí**). El SW de Personal pide con `cache:'no-cache'` y solo controla su página y 3 ficheros (`personal_sw.js`; prueba 13). El resto de páginas no tienen SW | Nadie | INFERIDO |
| 8 | Dos pestañas o dos aparatos | Misma obra, ámbito y fecha desde dos orígenes: en una misma pestaña ganan los últimos datos; con dos aparatos, dos ficheros con contenido distinto el mismo día. El comportamiento del lector ante contenido distinto mismo día **no lo he podido comprobar** | Parcial (A_REVISAR) | NO VERIFICABLE |
| 9 | Repo público | Se publica el catálogo de 22 trabajadores con `nombre`, `empresa`, `categoria` (`personal_catalogo.json`; `personal_estado.js` repite el catálogo) y jornadas con `id` + horas. No hay DNI, teléfono ni correo (comprobado: 0 coincidencias de correo). Búsqueda de claves/tokens habituales en todo lo versionado: **0 coincidencias**. El Buscador no lleva secretos (URL pública del Worker + clave tecleada) | `auditor` (`_datos_privados`) | CONFIRMADO |
| 10 | Un tipo de fichero nuevo no está en la lista blanca | Se genera y nunca se publica | `tests/test_publicacion_personal.py` (solo para personal) | CONFIRMADO |
| 11 | Ruta local en lo publicado | Los 7 paneles incluyen `D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE\…` (`generar_todos.py:2086`, `panel_obra.py:2284-2303`). Revela la estructura local y es inútil fuera del PC | Nadie | CONFIRMADO |
| 12 | El enlace apunta a un fichero que no se publica (PDF, DOCX, JPG, DWG, carpeta de OneDrive) | En el PC abre; en tablet/móvil, 404 | **Nadie.** `comprobar_enlaces.py` comprueba `ruta.exists()` en disco (`comprobar_enlaces.py`, función `enlaces_rotos_de_pagina`), no lo publicado (H-17, §3.3) | CONFIRMADO método · INFERIDO 404 |

**Lo mejor del circuito actual:** el bucle de **Personal está cerrado** (la tablet concilia lo publicado con lo pendiente). Las **revisiones no**: el generador recibe el estado nuevo vía `obras_revisiones.js`, pero no hay acuse por hoja.

### 3.3 Enlaces que existen en la página pero no en lo publicado (medido)

**Método.** `comprobar_enlaces.py` resuelve cada `href/src` relativo contra el **sistema de ficheros del PC** y solo avisa si el destino no existe allí. Pages, en cambio, sirve **solo lo que está en `main`** (y la lista blanca de `.gitignore` deja fuera casi todo lo que no es `.html`/`.py`). Para ver la diferencia he resuelto los mismos enlaces contra `git ls-files` (destino versionado, o carpeta con algo versionado dentro). Es una **cota inferior**: una carpeta cuenta como publicada aunque no tenga `index.html`, y Pages no lista carpetas (404), así que la cifra real de enlaces muertos fuera del PC es igual o mayor.

| Página | Enlaces internos publicados | **No publicados** | Qué son (principales) |
|---|---|---|---|
| `index.html` (portada) | 34 | **138** | 137 carpetas, en su mayoría las obras cerradas (128 según el mapa; solo 3 tienen algo versionado) |
| `_SISTEMA/PORTAL SAGARDE.html` (móvil) | 15 | **159** | 158 carpetas (sobre todo las pestañas Cerradas y Post-ventas) |
| `POST-VENTAS/index.html` | 88 | **123** | 45 PDF · 31 carpetas · 29 DOCX · 13 JPG |
| `VARIOS/index.html` | 55 | **104** | 38 PDF · 24 JPG · 15 DOCX · 8 DWG |
| `SAGARDE OBRAS ABIERTAS/index.html` | 13 | 0 | — |
| `MANTENIMIENTOS/index.html` | 10 | 0 | — |
| `APLICACIONES/index.html` | 12 | 0 | — |
| Panel Gernika | 19 | **197** | 136 PDF · 16 PNG · 12 TXT · 5 DWG |
| Panel Barakaldo | 7 | **207** | 140 JPG · 48 PDF · 10 DWG · 2 XLSX |
| Panel Bolueta | 22 | **131** | 68 JPG · 23 PDF · 12 DOCX · 9 JPEG |
| Panel Mungia | 9 | **135** | 70 PDF · 27 DOCX · 21 JPEG · 5 DWG |
| Panel Olabeaga | 20 | **43** | 25 PDF · 4 JPG · 3 DWG · 2 TXT |
| Panel Gorliz | 2 | **46** | 26 DWG · 10 PDF |
| Panel Obra Prueba | 8 | 5 | 2 PDF · 1 XLSX · 1 `.bat` · 1 carpeta |

**Lectura crítica**

- **No es necesariamente un error de publicación:** que los planos, las fotos y los DOCX de obra no estén en un repo público es una decisión razonable (derechos, peso, datos de cliente; ver comentarios de `.gitignore`). El fallo es que **la interfaz los ofrece como enlaces navegables** y desde tablet/móvil llevan a un 404, sin decir «solo en el PC».
- Ya pasó una vez: el `.gitignore` recoge que «el 96 % de Herramientas daba 404 en la tablet» (23/09/2026) y se corrigió **para esa carpeta**, no para el resto de páginas.
- Se agrava por una incoherencia del verificador: en el PC `comprobar_enlaces.py` dice «Todos los enlaces del portal publicado resuelven» (`comprobar_enlaces.py`, mensaje final) con todos estos enlaces rotos fuera del PC. Es un **falso OK**, de la misma familia que el resto del proyecto.
- Consecuencia para el panel de salud: sus propios enlaces deben apuntar **solo a lo publicado**, y debe añadirse la regla R9 (§4.6) que cuenta los enlaces a no publicados.
- Pregunta abierta para Bixente: ¿se prefiere que, fuera del PC, esos enlaces se muestren como texto gris con «solo en el PC», o que se publiquen algunos (p. ej. los PDF ejecutivos, que ya se publican)?

---

## 4. Propuesta: panel de salud del ente

### 4.1 Restricciones que se respetan

- Sitio estático en repo público: **sin backend, sin claves, sin cuentas**.
- Se construye **solo con lo que ya genera el pipeline** + **un fichero de estado que regenere el `.bat`**.
- Regla 7c: la app aporta datos; el portal solo muestra; los cambios se piden por el camino del entorno.
- `CLAUDE.md §7`: **desconocido ≠ cero**; **`P` ≠ `?`**; un 0 es alarma, no «no aplica».
- Datos públicos: **solo ids de obra, fechas y recuentos. Nunca nombres, ni horas por persona.**

### 4.2 Inventario de señales que ya existen

| Señal | Fuente existente | ¿Versionada? | Nota |
|---|---|---|---|
| Última revisión, nº de revisiones, bloqueos, sin cambios | `resumen_obras.json` (`generar_todos.py:1309`) | **No** (ignorado) | Hay que dejarlo pasar o duplicar los campos en el estado |
| Cuándo se aplicó cada revisión y si la salvaguarda comparó celdas | `revisiones_aplicadas.jsonl` (`trazabilidad_revisiones.py:22-60`) | Sí | `None` en la salvaguarda = «sin comprobación cruzada que hacer» **por diseño** (`:30-33`) |
| Última jornada y nº de ficheros de personal aplicados | `personal_jornadas.jsonl` (campos: `fecha`, `ts`, `fichero`, `sha256`, `n_presentes`, `avisos`, `rechazadas`) | Sí | Sin nombres |
| Controles pendientes / a revisar / rechazados | `personal_integracion._controles_sin_aplicar` (`:542`) | — (función) | Hoy solo vía auditoría |
| Hojas de revisión sin aplicar | `actualizar_obra.detectar_hojas` (`:245`) | — (función) | Hoy solo consola |
| Avisos del auditor | `auditoria_diagnostico.json` | **No** | `audit_obras`, `audit_materiales`, `audit_personal`, `audit_mantenimientos` |
| Enlaces rotos | `comprobar_enlaces.py` (código de salida 0/1/2) | — | Solo consola |
| Última entrega de materiales | Hoja `ENTREGAS` del `.xlsx` (`materiales_xlsx.py`) | **No** | Solo el PC puede leerla; INFERIDO que hay lectura reutilizable (no la he inspeccionado) |
| Despliegue de Pages | API pública de Actions de GitHub | Externa | Sin clave; CORS y límite de 60 peticiones/h por IP: **conocimiento externo, NO VERIFICABLE aquí** |

### 4.3 Tres opciones comparadas

| | **A · `estado_ente.js` + `SALUD.html` con edad viva** | **B · Todo pre-renderizado en Python** (ampliar el portal móvil) | **C · A + comprobación del despliegue vía API de GitHub** |
|---|---|---|---|
| Idea | El `.bat` escribe un único fichero de estado; la página lo lee con `<script src>` (como `personal_estado.js`) y **calcula edades con el reloj del navegador**. Lleva además una instantánea pre-renderizada para `<noscript>` | Python escribe el HTML final con todo ya calculado. Cero JS de cálculo | A, más un `fetch` opcional a Actions: ¿hay un despliegue posterior al sello de la página? |
| Detecta «nadie ha ejecutado el .bat» | **Sí** (la edad crece sola) | **No** (la fecha pintada no cambia) | Sí |
| Detecta «el push no llegó» | Indirecto (edad sin renovar) | No | **Sí**, directo |
| Detecta «Pages no desplegó» | No | No | **Sí** |
| Funciona sin red en tablet | Sí si la página ya está cargada; sin SW no reabre | Ídem | El `fetch` falla y degrada a A |
| Funciona desde `file://` (PC) | **Sí** (el patrón de `personal_estado.js` ya lo prueba) | Sí | Sí, sin el extra |
| Coste | Medio: 1 script nuevo, 1 página, 1 línea de `.gitignore`, 1 paso en el `.bat` | Bajo | Medio-alto |
| Riesgo principal | Que el estado sea un fichero más que nadie verifica → **hay que probar que cada regla se evalúa** | Repetir el fallo actual (dos renderizadores que divergen) | Dependencia externa; límite de peticiones; no debe bloquear el render |
| Respeta «sin backend/claves» | Sí | Sí | Sí (solo lectura pública) |

**Descartada:** un Worker o función en la nube que reciba órdenes o guarde estado. Viola «sin backend, sin claves», abre una superficie de ataque y contradice la regla 7c.

**Recomendación: A, con la instantánea pre-renderizada de B como degradación sin JS, y C como último paso opcional.** Es la única que detecta lo que hoy falla en silencio (G1, G4) sin añadir infraestructura.

### 4.4 Qué se ve en 10 segundos (boceto)

Los valores del boceto son **ilustrativos**, salvo las fechas de «última revisión», que son las del portal publicado el 03/11/2026 22:04. Los umbrales son **propuesta a confirmar con Bixente** (§4.7).

**Móvil (≈ 360 px de ancho, una columna)**

```
┌──────────────────────────────────────┐
│ SAGARDE · SALUD DEL ENTE             │
│ ⚠ ATENCIÓN                           │
│ Publicado hace 14 h · 03/11 22:04    │
├──────────────────────────────────────┤
│ QUÉ HACER AHORA            (2)       │
│ ┌──────────────────────────────────┐ │
│ │ ⚠ OLABEAGA                       │ │
│ │ 1 control horario sin aplicar    │ │
│ │ [📋 Copiar orden]                │ │
│ │ «actualiza la obra olabeaga»     │ │
│ └──────────────────────────────────┘ │
│ ┌──────────────────────────────────┐ │
│ │ ✖ GORLIZ                         │ │
│ │ SIN BASE: no hay % que mostrar   │ │
│ │ [📋 Copiar orden]                │ │
│ └──────────────────────────────────┘ │
├──────────────────────────────────────┤
│ OBRAS                                │
│ Olabeaga   ✔ rev 02/11  ⚠ pers 6 d   │
│ Barakaldo  ✔ rev 02/11  ✔ pers 1 d   │
│ Bolueta    ✔ rev 27/10  ⚠ pers 9 d   │
│ Mungia     ⚠ rev 15/10  ✔ pers 3 d   │
│ Gernika    ⚠ rev 05/10  ? pers sin datos │
│ Gorliz     ✖ sin base                │
│ Prueba     (banco de pruebas)        │
│ [ver matriz completa ▾]              │
├──────────────────────────────────────┤
│ TUBERÍA                              │
│ ✔ auditor  ✔ obras  ✔ portal         │
│ ✔ enlaces  ✔ mapa   ? subida         │
│ Despliegue Pages: ✔ 21:05 (03/11)    │
├──────────────────────────────────────┤
│ DECLARADO E IGNORADO         (0)     │
│ ✔ ninguna regla en alarma            │
│ (7 reglas evaluadas)                 │
└──────────────────────────────────────┘
```

**Tablet / PC (≥ 900 px, dos columnas)**: izquierda, «Qué hacer ahora» + «Declarado e ignorado»; derecha, la **matriz de frescura**:

```
                 Revisión  Personal  Materiales  Pendientes  PDF ejec.
 Olabeaga          2 d        6 d        4 d         1          2 d
 Barakaldo         2 d        1 d        –           0          5 d
 Bolueta           8 d        9 d       12 d         0          9 d
 Mungia           20 d        3 d        –           0         20 d
 Gernika          30 d         ?          ?          0         30 d
 Gorliz           SIN BASE    –          –           –          –
 ✔ al día · ⚠ revisar · ✖ vencido · ? desconocido · – no aplica
```

Reglas de diseño:

- **Estado en palabras y símbolo, no solo en color** (✔ ⚠ ✖ ? –). El semáforo global es una palabra: «AL DÍA», «ATENCIÓN», «ROJO».
- **`?` (desconocido) y `0` se pintan distinto.** Es la regla de la casa.
- Cada obra enseña la **fecha**, no solo un adjetivo. El % solo aparece con su **desglose** `X/M/slash/P/?/N` en el detalle; en la portada, nunca como «media».
- Cada alarma lleva **una orden copiable** (de una tabla fija, nunca generada con datos de personas).
- El texto fijo «edad» se recalcula en el navegador cada minuto.
- En `file://` aparece además el enlace a `.bat` local; en Pages y en tablet **no** (G8).

### 4.5 Contrato del fichero de estado (descripción, sin código)

Un único `estado_ente.js` (`window.SAGARDE_ESTADO = …`), escrito por un script nuevo al final de la tubería:

| Bloque | Contenido | Fuente |
|---|---|---|
| Cabecera | versión, `generado`, `generado_ts`, commit local (si se conoce) | reloj del PC |
| `tuberia[]` | un elemento por paso del `.bat`: nombre, código de salida, `ok/aviso/error` | códigos del `.bat` pasados como argumento |
| `obras[]` | id, nombre, `estado` (`CON_BASE`/`SIN_BASE`/`PRUEBA`), última revisión (fecha + `aplicado_en`), última jornada (fecha), última entrega de materiales (fecha), fecha del PDF ejecutivo, nº de bloqueos, desglose `X/M/slash/P/?/N` | resumen + trazas + hojas locales |
| `pendientes[]` | tipo (`CONTROL_LISTO`, `CONTROL_A_REVISAR`, `CONTROL_RECHAZADO`, `HOJA_SIN_APLICAR`), obra, recuento, **clave de la orden copiable** | `personal_integracion`, `actualizar_obra.detectar_hojas` |
| `reglas[]` | id de regla, descripción, valor medido (o `null` = desconocido), `en_alarma` | §4.6, paso 3 |
| `ordenes{}` | tabla fija «clave → texto de la orden» | constante del script |

Reglas de contrato: cualquier valor que no se pueda leer es `null` (**nunca 0**); el script **no inventa** nada; no entra ningún nombre ni hora por persona.

### 4.6 Plan en pasos pequeños, cada uno con su prueba

Todas las pruebas con `unittest` de la biblioteca estándar (`CLAUDE.md §6`). Las de navegador reutilizan Playwright, que ya usa `tests/test_personal_sin_cobertura.py` (no es una dependencia nueva). Cada paso termina con **prueba por mutación**: romper a propósito y comprobar que la prueba lo nota.

| Paso | Qué se hace | Prueba que lo demuestra | Mutación que debe romperla |
|---|---|---|---|
| **P0** | Bixente confirma umbrales (§4.7) y ubicación (`_SISTEMA/SALUD.html` o raíz) | — (decisión) | — |
| **P1** | Función **pura** `calcular_estado(entradas) → dict`, sin disco | Casos tabulados: obra al día, vencida, sin base, fuente ausente | Cambiar un umbral → falla el caso de borde |
| **P2** | Lectores finos de las fuentes existentes; fuente ausente o ilegible → `null` | Fixture con cada fuente ausente: el estado dice `null`, **nunca 0** | Sustituir `null` por `0` → falla |
| **P3** | Tabla declarativa de **reglas de «declarado e ignorado»** (R1…R10) | (a) un caso positivo y uno negativo por regla; (b) **meta-prueba**: toda regla declarada aparece evaluada en la salida (el panel no puede ignorar sus propias reglas) | Quitar una regla de la evaluación → falla la meta-prueba |
| **P4** | Escritura de `estado_ente.js` + línea en `.gitignore` | Como `test_publicacion_personal.py`: `git check-ignore` deja pasar el fichero y `git add -A --dry-run` lo incluye | Quitar la línea del `.gitignore` → falla |
| **P5** | Paso nuevo en `Actualizar_Sagarde.bat` **después del paso 5 y antes de `git add -A`**, pasando los códigos de salida de los pasos (hoy el `.bat` **no los guarda**: solo los usa en `if`; habrá que capturarlos en variables, con cuidado con `%errorlevel%` dentro de bloques) | Prueba que lee el `.bat`: la llamada existe, está antes del `add`, y recibe un código por paso | Borrar la llamada → falla |
| **P6** | `SALUD.html` generado, solo lectura del estado | Estático: viewport, **una fila por cada obra del registro**, sin `D:\`, sin `localhost`, sin `.bat` fuera de bloque `file://`, **ningún enlace interno a algo no versionado** (contra `git ls-files`, no contra el disco). Playwright a 360×800: `scrollWidth ≤ innerWidth` y ningún objetivo táctil < 44 px | Añadir una obra al registro sin tarjeta → falla (obra declarada e ignorada) |
| **P7** | Edad viva en el navegador | Playwright con reloj simulado: a +36 h → ATENCIÓN; a +96 h → ROJO; sin JS → se ve la instantánea | Fijar la edad al generar → falla |
| **P8** | Botón «Copiar orden» | Cada alarma con orden tiene texto no vacío de la tabla fija; con `clipboard` bloqueado cae a selección manual y avisa | Orden vacía → falla |
| **P9** | Franja de una línea («Salud: ATENCIÓN →») en `index.html` y en el portal móvil; añadir `SALUD.html` a `PAGINAS_FIJAS` | `comprobar_enlaces.py` sin enlaces rotos; ambos portales comparten **la misma función** de alertas (cierra G7) | Reintroducir el cálculo duplicado → falla |
| **P10** (opcional) | Comprobar el despliegue con la API pública de Actions | Respuesta simulada: despliegue posterior al sello → ✔; ausente → ⚠; sin red/límite → `?` y **no bloquea** el render | Hacer el `fetch` bloqueante → falla |
| **P11** | Corregir el mapa mental (A18, «portal móvil obsoleto», números de línea) en la misma sesión que construya el panel | `actualizar_mapa_mental.py --comprobar` sin rutas muertas | — |

**Reglas de «declarado e ignorado» propuestas (P3)**

| ID | Se declara… | Debe producir… | Alarma si | Fuente ya disponible |
|---|---|---|---|---|
| R1 | Hojas de revisión con fecha en el nombre | La fecha figura en la ficha de la obra | Hay hojas cuya fecha no figura (`HOJA_SIN_APLICAR`) | `actualizar_obra.detectar_hojas` |
| R2 | Sidecar `.correcciones.json` con N marcas | N marcas con efecto en la ficha | Declara ≥ 1 y el efecto es 0 | `claves_correcciones.py` (INFERIDO que sirve) |
| R3 | Control horario en `REVISIONES` | Su SHA-256 en `personal_jornadas.jsonl` o rechazo explícito | Fichero sin SHA ni rechazo | `lector_control_horario.analizar` |
| R4 | Obra en el registro | Tarjeta en índice, portal móvil y estado | Obra del registro sin tarjeta | `registro_obras.OBRAS` |
| R5 | Obra con panel | ≥ 1 revisión aplicada | `n_rev = 0` → estado `SIN_BASE`, **no** 0 % | `resumen_obras.json` |
| R6 | Salvaguarda de doble cálculo | `celdas_comparadas > 0` en el camino `historial_consolidado` | = 0 en ese camino (los `html_digital` quedan exentos por diseño) | `revisiones_aplicadas.jsonl` |
| R7 | «Actualiza la obra» con controles `LISTO` > 0 | Jornadas nuevas en `personal_jornadas.jsonl` | Controles `LISTO` y 0 jornadas añadidas | `personal_integracion` |
| R8 | `n_con_panel` obras con panel | `n_con_datos_frescos` igual | `n_con_datos_frescos < n_con_panel` (H-05) | `resumen_obras.json` |
| R9 | Enlaces del portal | Todos apuntan a algo **publicado** (versionado o permitido por la lista blanca) | Hay enlaces a ficheros no publicados (H-17); hoy `comprobar_enlaces.py` solo mira el disco | recuento nuevo contra `git ls-files` + código de salida actual |
| R10 | Pasos del `.bat` | Todos con código 0 | Cualquier paso ≠ 0 | argumentos del paso P5 |

**Medición real de R6 (para que no sea teórica):** de 625 eventos en las 6 trazas, **28 no llevan datos de salvaguarda**. Los 28 son del camino `html_digital`, donde la propia traza documenta que no hay comprobación cruzada (`trazabilidad_revisiones.py:30-33`). En el camino `historial_consolidado`, **0 casos**. Es decir: la regla R6 arranca limpia, y se descarta como falso positivo lo que parecía una alarma.

### 4.7 Decisiones que necesito de Bixente

1. **Umbrales de edad.** Propuesta: publicación ATENCIÓN > 72 h y ROJO > 7 días (hay huecos normales de 67 h); revisión de obra y mantenimiento, **los mismos que ya existen** (14 d, 30 d, 90 d, caducidad 400 d) para no inventar otros. Personal: sin umbral hasta que defina cuántos días sin control horario son un problema.
2. **Ubicación:** `_SISTEMA/SALUD.html` (coherente con `PORTAL SAGARDE.html`) o raíz. La norma `_SISTEMA` considera «informático» el HTML generado; la URL para el móvil sería más corta en la raíz.
3. **¿Se excluye OBRA PRUEBA del KPI de avance y se retira el KPI de media simple?** (H-04).
4. **¿Se acepta que `personal_catalogo.json` con nombres siga en el repo público?** Es una decisión suya vigente; la dejo anotada por riesgo de protección de datos.

---

## 5. Hallazgos ordenados

| ID | Gravedad | Hallazgo | Certeza |
|---|---|---|---|
| H-01 | Alta | Portal móvil vigente pero **huérfano** e **incoherente** con el de escritorio; el mapa mental lo da por obsoleto | CONFIRMADO |
| H-02 | Alta | Avisos de controles sin aplicar: etiqueta falsa (`:1426`) y un paso de retraso | CONFIRMADO etiqueta · INFERIDO retraso |
| H-03 | Alta | Nada detecta «nadie ejecutó el `.bat`»; el `.bat` declara éxito sin esperar a Pages | CONFIRMADO |
| H-04 | Media-alta | «Avance medio 42 %» incluye OBRA PRUEBA y un 0 por desconocido (Gorliz) | CONFIRMADO (aritmética) |
| H-05 | Media | Obra no regenerada: desaparece en escritorio, permanece sin marca en móvil | CONFIRMADO |
| H-06 | Media | Ruta `D:\…` y enlace a `Actualizar_Obras.bat` (404 por lista blanca) en los 7 paneles | CONFIRMADO ruta · INFERIDO 404 |
| H-07 | Media | `resumen_obras.json`, `postventas_resumen.json` y `auditoria_diagnostico.json` no se publican: la página no puede releerlos | CONFIRMADO |
| H-08 | Media | «Inactividad» usa `mtime` de OneDrive de cualquier fichero | CONFIRMADO |
| H-09 | Info | Botón «Hecho»: solo funciona con servidor local, y falla con aviso claro y casilla revertida. Sin acción | CONFIRMADO |
| H-10 | Media | Tablet: sin `storage.persist()` y sin protección entre pestañas | CONFIRMADO ausencia · INFERIDO efecto |
| H-11 | Media | Generador de revisiones: no reabre sin cobertura | INFERIDO |
| H-12 | Baja-media | Objetivos táctiles ≈ 34–37 px en panel y portal móvil | INFERIDO |
| H-13 | Media | Datos de 22 trabajadores (nombre, empresa, categoría) en repo público | CONFIRMADO |
| H-14 | Baja | Mapa mental desfasado (ver §7) | CONFIRMADO |
| H-15 | Baja | 125 líneas de código muerto en `_render_variacion_badge` | CONFIRMADO (AST) |
| H-16 | Baja | KPI «Obras abiertas 24» cuenta carpetas, no obras vivas | CONFIRMADO |
| H-17 | **Alta** | `comprobar_enlaces.py` valida contra el **disco**; lo publicado solo tiene lo versionado. Cientos de enlaces de portadas y paneles dan 404 fuera del PC (tabla en §3.3) | CONFIRMADO medición · INFERIDO 404 (Pages inaccesible) |

## 6. Dudosos descartados (y por qué)

| Sospecha | Veredicto | Motivo |
|---|---|---|
| «El portal móvil está roto» | Descartada | Se genera, está commiteado y probado (§2.2) |
| «Hay 28 trazas sin salvaguarda» | Descartada | Todas son `html_digital`; la ausencia está documentada por diseño |
| «El `.gitignore` bloquea el portal móvil» | Descartada | `!*.html` (`.gitignore:8`) lo deja pasar |
| «El SW de Personal sirve versiones viejas» | Descartada | Red primero con `no-cache`, 4 s de espera, copia solo si falla; 13 escenas Playwright |
| «El panel depende de `localhost`» | Descartada | Solo el botón «Hecho», con aviso claro si falla |
| «El Buscador lleva una clave en el repo» | Descartada | URL pública del Worker; la clave la teclea el usuario. 0 coincidencias de secretos |
| «`document.write` del generador se bloquea» | Descartada (baja) | El bloqueo de Chrome afecta a scripts de otro origen en 2G; aquí es el mismo origen. Conocimiento externo |
| «El HTTP 408 se puede explicar desde el repo» | No concluyo | No hay trazas; solo cifras de tamaño |

## 7. Correcciones que necesita el mapa mental (no las aplico: esta tarea es de solo lectura)

- **A18 y «Estado»**: «APARENTEMENTE OBSOLETO» / «portal móvil estancado» / «código roto» → **vigente, huérfano e incoherente** (líneas 125, 161, 185, 226, 324, 377, 515, 578, 794, 808, 845).
- Referencias de línea desfasadas: `build_html` está en `sagarde_portal.py:1519` (el mapa dice `:936-1085`); `generar_portal_movil` en `:1018-1175` (dice `:569-759`); «acaba en línea 605» ya no es cierto.
- Falta anotar que `_render_variacion_badge` contiene código muerto.
- Falta anotar que `resumen_obras.json`, `postventas_resumen.json` y `auditoria_diagnostico.json` **no se publican**.

## 8. Lo que queda NO VERIFICABLE

- Comportamiento real en Edge para Android, impresión a PDF y reapertura offline (sin dispositivo).
- Cabeceras reales de Pages (caché ≈ 600 s) y respuesta de `Actualizar_Obras.bat` en la web (proxy 403).
- Causa del HTTP 408 en `git push`.
- Contenido de `resumen_obras.json`, `auditoria_diagnostico.json`, hojas `.xlsx` y `FICHA DE OBRA.xlsx`.
- Qué hace el lector de controles horarios cuando dos orígenes traen contenido distinto para la misma obra, ámbito y fecha.
- Si `materiales_xlsx.py` expone una lectura reutilizable de la última entrega.
- La existencia y estado de las 17 carpetas de obra sin seguimiento.
