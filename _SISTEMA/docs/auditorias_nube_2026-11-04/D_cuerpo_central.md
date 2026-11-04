# D · ¿Existe el cuerpo central y bebe todo de él? — auditoría de solo lectura

**Fecha:** 04/11/2026 · **Commit auditado:** `3415610` (= `origin/main`, «Actualizacion 2026-11-03_2204») · **Rama del informe:** `nube/integracion-cuerpo-central`
**Alcance:** repositorio clonado en la nube (solo lo versionado). **Modo:** solo lectura. No se modificó código ni datos, no se ejecutó ningún `.bat` ni nada que haga push a `main`. Lo único escrito es este informe.

**Norte de Bixente:** un cuerpo central (la base común de obra) con extremidades que beben y la alimentan, los `.bat` como circulación y el centro de mando como control. PC, tablet y móvil.

**Etiquetas:** `CONFIRMADO` = visto en código o reproducido (con `fichero:línea` o cálculo). `INFERIDO` = deducido de lo visto, sin prueba directa. `NO VERIFICABLE` = no está versionado o no se puede ejecutar aquí; no se concluye que no exista.

---

## 0. Veredicto en cinco líneas

1. **El cuerpo central existe, pero solo para el dominio «obra de vivienda/garaje» y «personal».** `ficha_obra.json` / `ficha_garajes.json` mandan de verdad: panel, prioridades, KPI, portal, generador de revisiones e informe ejecutivo parten de ellas. `CONFIRMADO`.
2. **Dentro de ese cuerpo hay cuatro goteras de cifras.** Dos definiciones de «avance» bajo la misma etiqueta (panel/portal frente al PDF ejecutivo: hasta 3,6 puntos de diferencia en obras reales, 4,1 en OBRA PRUEBA), una memoria que fuerza al 100 % tajos que la ficha da por pendientes, una evolución histórica que mezcla denominadores, y un aviso de divergencia que solo sale por consola. Todas `CONFIRMADO`.
3. **Postventa, mantenimiento, CARDIVA y las apps de `VARIOS` son órganos sueltos:** índice propio, ficha propia (Word/PDF/localStorage), ninguna clave común con el registro de obras. Las apps de `VARIOS` guardan su estado en el `localStorage` de cada navegador, así que PC, tablet y móvil divergen. `CONFIRMADO` por código y `grep`; el contenido real de las carpetas es `NO VERIFICABLE`.
4. **La circulación (`.bat`) solo está versionada en un 40 %.** De cinco `.bat`, dos están en git (`Actualizar_Sagarde.bat`, `Abrir_Panel_Local.bat` este último forzado contra el `.gitignore`); `Actualizar_Obras.bat`, `Servidor_Local.bat` y `Actualizar_Postventas.bat` no. No se puede auditar lo que no se ve: `NO VERIFICABLE`.
5. **El control que debería vigilar la publicación mira el universo equivocado:** `comprobar_enlaces.py` comprueba contra el disco local, no contra la lista blanca de git. Por eso un enlace de panel a un fichero que nunca se publica (`prioridades_trabajos_zesp.json`, en 3 paneles) pasa limpio y da 404 en tablet y móvil. `CONFIRMADO`.

---

## 1. Inventario de la base: dato × escritor × lectores

Leyenda de la columna «M/D»: **M** = verdad medida (se guarda), **D** = derivada (se recalcula), **M+D** = mezcla.
Rutas abreviadas: `MOT` = `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`, `SCR` = `_SISTEMA/MOTOR/scripts`.

| Dato | Escritor(es) | Lectores | M/D | ¿Escritor único? |
|---|---|---|---|---|
| **`ficha_obra.json`** (por obra; 6 de 7 registradas, falta Gorliz) | `MOT/ficha_obra.py:115` (`guardar`), llamado desde `MOT/generar_todos.py:1663` y `:2036` (en **cada** `Actualizar_Sagarde.bat`), `MOT/leer_hoja_marcada.py:1042` y `:1188` (hojas de campo); alta directa en `MOT/alta_obra_desde_hoja.py:1008-1009`; `MOT/cerrar_obra.py:259,279` la mueve al cerrar | `MOT/generar_todos.py:399,1870`; `priorizador_trabajos.priorizar_ficha`; `MOT/panel_obra.py` (vía snapshot); `SCR/generar_informe_ejecutivo.py:3039`; adaptadores (`MOT/adaptadores/adaptador_bolueta.py:402`…); `MOT/adaptar_revision_html.py:657`; `SCR/actualizar_obra.py:709,849,1209`; `SCR/actualizar_mapa_mental.py:234,281`; `obras_revisiones.js` | M (`estados`, `estructura`, `tajos`) + D (4 apartados, ver abajo) | **No.** 3 caminos reales (`generar_todos`, `leer_hoja_marcada`, `alta_obra_desde_hoja`). Mitigado por la salvaguarda de doble cálculo (`generar_todos.py:1572-1611`) y la traza JSONL. `CONFIRMADO` |
| ↳ apartados `contactos`, `materiales`, `documentos` dentro de la ficha | `MOT/ficha_obra.py:239-268` (`volcar_apartados`) | **Nadie** fuera de su propio escritor (dos `grep` distintos). `identidad` sí se lee: `SCR/generar_informe_ejecutivo.py:690,1415` | D persistida (incluye `dias_desde`, que caduca) | Copia muerta en la base. Va contra «se guarda lo medido, se recalcula lo derivado». `CONFIRMADO`; una lectura dinámica por clave variable no se puede excluir |
| **`ficha_garajes.json`** | `MOT/ficha_garajes.py:61-66` (`guardar`), llamado desde `MOT/alta_garaje_desde_hoja.py:116` y `MOT/adaptar_revision_garaje.py:147` | `MOT/generar_todos.py:1871` (`ficha_garajes.cargar`), informe ejecutivo `:3041`, `registro_garaje_desde_ficha` | M | Sí, un módulo; dos entradas |
| **`revisiones_aplicadas.jsonl`** | `MOT/trazabilidad_revisiones.py:66` (`registrar_trazabilidad`), llamado desde `generar_todos.py:1664`, `leer_hoja_marcada.py:1043,1189` | **Ningún lector fuera de tests** (grep del nombre y de las funciones) | M (evidencia, no entra en cálculo) | Sí. Es traza pura; nadie la contrasta. `CONFIRMADO` |
| **`personal_obra.json` / `personal_jornadas.jsonl`** (por obra) y **`personal_catalogo.json`** (global, cruza obras) | Un solo módulo: `MOT/personal_obra.py` (`ingerir_lote:624`, `alta_trabajador:236`, `fusionar:1425`, `renombrar:1200`, `poner_empresa:1243`, escritura atómica `:107`). Entrada por la tablet → `CONTROL HORARIO` en `REVISIONES` → `personal_integracion.aplicar_controles_limpios:357` (lo lanza `generar_todos.py:2093`) | `personal_integracion.filas_para_panel:165`, `panel_personal.py`, `exportar_estado_real:189` → `personal_estado.js` (tablet `generador_personal.html`, ranking `personal_sagarde.html`), auditor `audit_personal` (`SCR/auditor_sagarde.py:198`) | M | Sí, **un escritor**. Salvedad: `personal_obra.py` conserva un subcomando CLI `ingerir` (`:1893`) que se salta las guardas de `lector_control_horario`; `CLAUDE.md §7c` prohíbe «recibir/ingerir». `CONFIRMADO` que existe, `INFERIDO` que sea un riesgo real |
| **Entregas de material (`ENTREGAS`, xlsx)** | `MOT/entregas_materiales.py:940` (`refrescar_hojas`, rehace hojas de mes), `SCR/materiales_xlsx.py:191,280,328` (`reparar`/`migrar`), y a mano (Excel/openpyxl, `CLAUDE.md §7b`) | `MOT/lectores.py:80` (`leer_materiales`) ← `generar_todos.py` ~1844-1853 → panel | M (`ENTREGAS`) + D (hojas de mes, `ACUMULADO`) | **No**: humano + 2 scripts. **El xlsx no está versionado** (`*` lo ignora). Contenido y exactitud: `NO VERIFICABLE` |
| **Notas / tareas pendientes** (`FICHA DE OBRA.xlsx`, hoja `Tareas`) | `MOT/nota_pendiente.py` (añadir fila, marcar/desmarcar), `MOT/panel_server.py:12,64` (botón «Hecho»), y a mano | `MOT/lectores.py:29` (`leer_ficha`), `hilos_notas.py`, panel | M | **No**: 3 escritores sobre el mismo xlsx. No versionado. `NO VERIFICABLE` el contenido. `panel_server` solo escucha en `127.0.0.1` (`:15,119`): el botón no funciona en tablet/móvil, avisa del fallo (no es silencioso) |
| **`cierre_expediente.json`** | `MOT/cierre_expediente.py:102-107`; lo crea vacío `generar_todos.py:2090-2092` si falta; el resto, a mano | panel, informe ejecutivo (`generar_informe_ejecutivo.py:95`). Su docstring dice que priorizador y generador **no** lo leen | M | Sí (CLI + creación). Fuera de la rejilla por diseño |
| **`prioridades_trabajos.json`**, `_garaje`, `_zesp`, `dudas_pendientes.json` | `MOT/priorizador_trabajos.py:1073` (`escribir_json`), llamado desde `generar_todos.py:1876,2039,2062,2078` | Panel y PDF reciben el dict **en memoria**; `generar_todos.publicar_registro_revisiones:900` lo relee **del disco** → `obras_revisiones.js` (generador); el panel enlaza los JSON | D | Sí. Dos rutas de lectura (memoria / disco) para la misma salida: si falla la regeneración de una obra, el generador consume el JSON viejo |
| **`memoria_obra.json`** | `MOT/memoria_obra.py:98-112`, llamado desde `generar_todos.py:2021-2022` | Solo en memoria (`tajos_memoria` → `panel_obra.py:1863`). `cargar_memoria` (`memoria_obra.py:81`) **no se llama en ningún sitio** | D, aunque el docstring dice «registro persistente» | Sí. «Persistente» es falso: se recalcula del historial cada vez. No versionado. Ver F2 |
| **Catálogo de tajos** `reglas/CATALOGO_TAJOS.json` (v1.3, 93 tajos: 71 propio, 20 externo, 2 coordinación) | A mano. **Está versionado** (entró en `78c0b3a`, forzado) aunque la documentación diga lo contrario | **≥ 9 cargadores independientes**: `validar_revision.py:17,44`, `priorizador_trabajos.py:91`, `alta_obra_desde_hoja.py:64`, `rejilla_hoja.py:46`, `sembrar_ficha_obra.py:77,97,309`, `generar_todos.py:379`, `ficha_obra.py:427`, `generar_informe_ejecutivo.py:51`, y 6 adaptadores | M (regla) | Sí, humano. Un solo fichero, nueve rutas de lectura (hoy no divergen: leen el mismo fichero) |
| **Registro de obras** `registro_obras.py` | A mano | Ver §2.3 | M | Sí |
| **Postventa** | `POST-VENTAS/_SISTEMA/postventas_sync.py` (escribe el Word matriz) y `postventas_index.py` (índice HTML + `postventas_resumen.json`, `:26`) | `_SISTEMA/MOTOR/sagarde_portal.py:103` (resumen), portal | M en Word/PDF (no versionados) | Órgano suelto: sin clave común con obras. `NO VERIFICABLE` contenido |
| **Mantenimiento** | `MANTENIMIENTOS/_SISTEMA/mantenimientos_index.py:33` (índice + resumen); CARDIVA por su propia skill | `sagarde_portal.py:217`, `auditor_sagarde.py:237`, `avisos.py` | M en carpetas/DOCX (no versionados) | Órgano suelto |
| **Avisos** (reglas de vigencia, contratos «sin aviso») | A mano en `_SISTEMA/MOTOR/avisos.py` | `sagarde_portal.py:10`, `auditor_sagarde.py:44`, `mantenimientos_index.py:30` | M (regla) | Sí. Es la única regla compartida por los tres consumidores y bien hecha |
| **`resumen_obras.json`** | `MOT/generar_todos.py:1309-1383`; **segunda implementación** de totales e índice en `SCR/regenerar_obra.py:248-275` | `sagarde_portal.py:102,1028`, `actualizar_mapa_mental.py:213`, `cerrar_obra.py:58` | D (y no versionado) | **No**: dos implementaciones del mismo agregado. Ver F5 |

**Lectura del cuadro.** El cuerpo tiene un escritor claro solo para personal y garajes. La ficha de vivienda tiene tres caminos de escritura y se defiende con doble cálculo; el resto de «datos» que Bixente teclea (entregas, tareas, controles) viven en ficheros fuera de git, y dos de ellos tienen varios escritores.

---

## 2. Fugas

### 2.1 Verificación del desglose X / M / / / vacío en cada consumidor

Reproducido a mano desde cada `ficha_obra.json` + `ficha_garajes.json` (peso `X=1, M=0,60, /=0,25`, `N` excluida, `?` = 0 celdas en las 6 obras) y comparado con lo publicado en cada `panel.html` (cabecera, gráfica) y con el texto de cada `INFORME_EJECUTIVO_*.pdf` (`pdftotext`).

| Obra | Ficha viv. (X/M//P) | Viv.+garaje: avance / estricto | **Panel (cabecera)** | Último punto de la gráfica del panel (solo vivienda) | **PDF ejecutivo** | Solo tajos *propios* (reproducido) |
|---|---|---|---|---|---|---|
| Gernika | 1131/13/5/59 | 94,12 / 93,34 | 94,1 / 93,3 ✔ | 94,4 | **96,1 / 95,1**, 827/870 | 96,1 / 95,1, 827/870 ✔ |
| Bolueta | 2617/345/67/627 | 76,72 / 70,69 | 76,7 / 70,7 ✔ | 77,7 | **73,6 / 68,5**, 1683/2458 | 73,6 / 68,5, 1683/2458 ✔ |
| Mungia | 2083/66/21/186 | 90,32 / 88,41 (sin garaje) | 90,3 / 88,4 ✔ | 90,3 | **88,8 / 86,2**, 1336/1550 | 88,8 / 86,2, 1336/1550 ✔ |
| Olabeaga | 209/25/41/1186 | 15,03 / 13,26 | 15,0 / 13,3 ✔ | 16,0 | **11,4 / 9,8**, 115/1174 | 11,4 / 9,8, 115/1174 ✔ |
| Barakaldo | 0/0/10/4130 | 0,14 / 0,04 | 0,1 / 0,0 ✔ | 0,1 | 0,1 / 0,0, 0/3009 | 0,1 / 0,0, 0/3009 ✔ |
| OBRA PRUEBA | 161/36/5/976 | 16,29 / 14,20 | 16,3 / 14,2 ✔ | 15,6 | **12,2 / 9,6**, 75/780 | 12,2 / 9,6, 75/780 ✔ |

**Conclusión del cuadro** (`CONFIRMADO`, cálculo reproducible):

- **Panel, portal, índice, mapa mental y `resumen_obras.json` coinciden con la ficha** al decimal. En eso el cuerpo funciona: `generar_panel` devuelve el KPI combinado vivienda+garaje (`panel_obra.py:1852,2849`) y de ahí sale el portal.
- **El PDF ejecutivo mide otra cosa con el mismo nombre.** Filtra a «tajos propios de Sagarde» (`SCR/generar_informe_ejecutivo.py:175-190`, cabecera `:687`) y esa cifra sale bajo la etiqueta «Avance estimado», igual que en el panel. Mi reproducción con `propiedad == 'propio'` da exactamente las cifras del PDF en las 6 obras. La diferencia llega a **−3,6 pp (Olabeaga)**, **−4,1 pp (OBRA PRUEBA)**, **−3,1 pp (Bolueta)** y **+2,0 pp (Gernika, sube)**. No es ruido de redondeo: es un universo distinto (el panel cuenta también los tajos `externo` y `coordinacion` del catálogo, p. ej. Tabicado).
- **Dentro del propio panel hay dos números**: la cabecera es vivienda+garaje y el último punto de la gráfica es solo vivienda (Gernika 94,1 frente a 94,4; Olabeaga 15,0 frente a 16,0; Prueba 16,3 frente a 15,6). `panel_obra.py:2075` además pasa solo vivienda (`kpis`) a la pestaña de prioridades.

El PDF dice «Alcance: tajos propios» en letra pequeña, y puede ser exactamente lo que Bixente quiere. Lo que no es defendible es que el mismo rótulo, «Avance estimado», designe dos medidas.

### 2.2 Hallazgos

**F1 · Dos «avances» bajo una etiqueta (panel/portal frente a PDF).** `CONFIRMADO`, ver 2.1. Dato que falta y que debe decidir Bixente: ¿el avance oficial de la obra es «todos los tajos» o «los tajos de Sagarde»? Hoy el portal publica uno y el PDF que se comparte con terceros, el otro.

**F2 · La memoria de tajos marca como «terminado al 100 %» tajos que la ficha da por pendientes.** `CONFIRMADO` con números.
- Mecanismo: `memoria_obra.calcular_memoria` (`memoria_obra.py:19`) compara **nombres de tajo literales** entre todas las hojas del historial. Las hojas viejas traen el vocabulario antiguo («Pintura zzcc», «Apliques», «ILuminación Rellanos») y el último snapshot, que ahora sale de la ficha (`generar_todos.py:1966`), trae los nombres canónicos. Todo nombre antiguo «desaparece» de la última hoja → `terminado=True` → `ranking_tareas_con_memoria` lo añade **al 100 %** (`motor_informes.py:220-235`) y `panel_obra.py:1863` lo pinta en la gráfica «Avance por tajo». Es la regla «ausente = terminado» de cuando las hojas omitían lo acabado; con la ficha explícita ya no vale (§7 de `CLAUDE.md`: ausencia ≠ terminado).
- Alcance medido en los paneles publicados (`DATA.por_tarea`): **23 sombras en Gernika, 21 en Bolueta, 27 en Mungia**, 0 en Olabeaga, Barakaldo y Prueba (sus hojas nacieron con vocabulario canónico). El propio panel lo reconoce: «61 tajos en total — 38 activos · 23 terminados (100 % forzado en el gráfico)» frente a 38 tajos en la ficha de Gernika.
- Contradicciones dentro de la misma gráfica (sombra forzada al 100 % frente al avance real del tajo equivalente en la ficha, resuelto por alias del catálogo):

  | Obra | Tajo (nombre antiguo) | Gráfica | Ficha (mismo tajo) |
  |---|---|---|---|
  | Bolueta | Apliques | 100,0 | **0,0** |
  | Bolueta | Pintura segunda mano | 100,0 | **21,1** |
  | Bolueta | Pintura zzcc | 100,0 | **48,2** |
  | Gernika | Pintura zzcc | 100,0 | **0,0** |
  | Gernika | Casquillos Bombilla | 100,0 | **25,2** |
  | Mungia | ILuminación Rellanos | 100,0 | **8,1** |
  | Mungia | Apliques / Aplique + Enchufe | 100,0 | **50,7** |

  Solo 2 de las 71 sombras (`Cuarto tecnico`) no tienen equivalente vivo (tajo retirado por decisión, `ficha_obra.py:74`).
- No toca los KPI (`kpis_snapshot` no usa la memoria) pero sí la gráfica y el ranking de tajos, que es lo primero que mira Bixente para saber qué falta.

**F3 · La evolución histórica mezcla definiciones y denominadores.** `CONFIRMADO` el síntoma, `INFERIDO` la causa exacta.
- Solo se sustituye el **último** punto del historial por el snapshot de la ficha (`generar_todos.py:1966`); los anteriores siguen siendo la hoja cruda de cada día. Denominadores publicados (`DATA.serie[].total`): Mungia 1147 → 2318 → 2309 → 2356 → 2294 → 2356; Olabeaga 1295 → 1265 → 1256 → **1461**; Bolueta 3525 → **3656**; Gernika 1088 → 1216 → 1208.
- `variacion_pct` y `historico_pct` del índice (`generar_todos.py:2155-2156`) restan el último punto (ficha acumulada) al anterior (hoja del día): parte del «+1,5 pp» de Olabeaga es cambio de cobertura, no avance. `NO VERIFICABLE` cuánto, porque el historial crudo sale de los adaptadores (HTML/PDF de `REVISIONES`, no todos versionados).

**F4 · La divergencia entre el camino antiguo y el motor común se queda en la consola.** `CONFIRMADO`.
`actualizar_ficha_con_salvaguarda` imprime `[AVISO CUTOVER FICHA]` y devuelve la ficha **sin actualizar** (`generar_todos.py:1629-1650`); `main` solo añade a `fallidas` las obras que lanzan excepción (`:1817`, `:2112`; el código de salida se decide en `:2217`), así que el código de salida es 0, el `.bat` no se entera y publica un panel construido sobre la ficha vieja, sin banner (no hay ninguna referencia a «cutover» en `panel_obra.py`). La etiqueta de fecha sí describe la última revisión de la ficha, por lo que el panel parece al día. Es exactamente «algo que el motor ignora en silencio», con la salvedad de que la consola lo dice.

**F5 · Los agregados del portal cuentan obras que no deberían y ceros que no son datos.** `CONFIRMADO` en código, valor numérico `NO VERIFICABLE` (`resumen_obras.json` no está versionado).
- `avance_medio_ponderado` (`generar_todos.py:1333,1375`) es la media simple de **todas** las obras registradas con panel: incluye **OBRA PRUEBA** (ficticia: `registro_obras.py:62-68`, subtítulo «No es una obra real») y **Gorliz sin base**, cuyo `res['kpis']` vacío entra como `0` (`or r['pct']`). «No sustituir valores desconocidos por cero» (`CLAUDE.md §7`). `bloqueos_totales` también suma los 10 bloqueos de Prueba (`n_bloqueos` del panel).
- `SCR/regenerar_obra.py:248-275` reimplementa los totales y la fusión de tarjetas (`pct_ponderado is not None … else pct_estricto`, frente a `or`): dos agregados que pueden divergir según se use `generar_todos` o `regenerar_obra --finalizar`.

**F6 · Alarma encendida de forma permanente y verificador ciego.** `CONFIRMADO`.
`verificar_rejilla` (`priorizador_trabajos.py:455`) compara celdas con `ubicaciones × tajos`. Desde que existen zonas especiales y tajos por tipo de zona, las fichas son esparcidas a propósito: Bolueta 3837 de 7738 (106×73), Olabeaga 1519 de 3528, Barakaldo 4140 de 8160. El banner rojo «La base no es una rejilla completa… Los tajos que falten no se pueden priorizar» sale **fijo en 3 de 6 paneles publicados** y nunca en Gernika, Mungia ni Prueba. Una alarma que siempre suena no avisa de nada, y el comprobador no detectaría un hueco real. El mapa mental sigue diciendo «rejilla densa».

**F7 · El PDF ejecutivo viejo se publica y se enlaza si la generación falla.** `CONFIRMADO` en código.
`generar_para_obra` va dentro de un `try/except` que solo imprime `[AVISO INFORME EJECUTIVO]` (`generar_todos.py:2126-2143`), y el enlace del portal se arma con solo `os.path.isfile` (`:2178`). El PDF anterior sigue en disco, `git add -f` lo sube (`Actualizar_Sagarde.bat:103`) y el portal lo ofrece con la fecha de hoy. Hoy están al día (ficha, panel y PDF del mismo commit; el PDF de Mungia lleva fecha de creación 03/11 20:59 UTC), así que es riesgo latente, no hallazgo vivo.

**F8 · Pesos duplicados con la sincronía solo en un comentario.** `CONFIRMADO` que hoy coinciden.
`SCORE` (`MOT/motor_informes.py:37`) y `ESTADO_VALOR` (`MOT/priorizador_trabajos.py:18`) llevan `X=1, M=0,60, /=0,25`. La regla «si cambias uno, cambia el otro» está en tres comentarios y en `_SISTEMA/MOTOR/CLAUDE.md`; no hay ninguna prueba que las compare (el `grep` solo encuentra `test_catalogo_invariantes.py:82`, que mira los valores, no la igualdad). El PDF reutiliza `motor_informes` (bien).

**F9 · `ficha_obra.json` tiene un escritor disimulado dentro del `.bat`.** `CONFIRMADO` por código, `INFERIDO` el riesgo.
`generar_todos.py:1937-1944` y `:2036` escriben la ficha en cada publicación, reaplicando la última hoja que **conoce el adaptador**. El propio código admite que puede ir por detrás de la ficha («`fecha_ultima` … puede quedar desfasada si la ficha ya tiene una revisión más reciente», `:1953-1962`). La salvaguarda de doble cálculo lo protege hoy; si falla, vale F4. Un `.bat` de publicación que modifica la verdad medida merece decisión explícita de Bixente.

### 2.3 Listas de obras: cuántas hay y pueden divergir

| # | Fuente | Qué contiene | ¿Diverge hoy? |
|---|---|---|---|
| 1 | `MOT/registro_obras.py:9-` | **7 obras** (`gernika, mungia, bolueta, gorliz, prueba, olabeaga, barakaldo`) | Fuente oficial |
| 2 | Derivadas del registro (bien) | `generar_informe_ejecutivo._cargar_adaptadores:99`, `comprobar_enlaces.paginas_a_comprobar`, `publicar_registro_revisiones`, `personal_integracion.obras_registro:107`, `validar_revision._configuracion_obra` | No |
| 3 | **Carpetas en disco** | `generar_todos.carpetas_obra:1205` y `sagarde_portal.contar_obras_abiertas_carpetas:273` cuentan todas las carpetas no `_`. El mapa mental AUTO dice 24 carpetas / 7 registradas | **Sí, a propósito:** las carpetas sin registrar salen como «Pendiente de alta» (`generar_todos.py:1068`). La cuenta (24 − 7 = 17) sale del mapa mental: `INFERIDO`; `NO VERIFICABLE` en este clon, que solo trae las carpetas versionadas |
| 4 | **`MOT/verificar_hojas_pdf.py:37-38`** `ESPERADAS = {'gernika','mungia','bolueta','obisporueta','prueba'}` | 5 ids escritos a mano con nº de celdas | **Sí:** Bolueta 3686 frente a 3837 de la ficha; faltan Olabeaga y Barakaldo; `obisporueta` está cerrada |
| 5 | `MOT/alta_obra_desde_hoja.py:166,175,177-182,697` | Literales de Olabeaga: mapa de portales duplicado del registro (`registro_obras.py:98-102`) y `catalogo['obras']['olabeaga']` | **Sí:** esa clave **no existe** en el catálogo (sus claves son `2025 GERNIKA 32V` y `2025 BILBAO OBISPO ORUETA`), el bucle es un no-op en silencio |
| 6 | `CATALOGO_TAJOS.json → obras` | 2 entradas indexadas por **nombre completo** (Gernika: 1 tajo; Orueta, ya cerrada: 18) | Convive con ids cortos; `validar_revision._configuracion_obra:204` traduce |
| 7 | Adaptadores: 9 ficheros, cada uno con su `CARPETA_OBRA` literal | 7 registrados + `adaptador_egurrola` + `adaptador_zorrozaure` | Huérfanos documentados en el mapa mental |
| 8 | `_SISTEMA/MOTOR/sagarde_portal.py:33` `APPS_OBRAS_ABIERTAS` | 2 apps a mano (ranking y tablet de personal) | No; hay prueba que exige que existan |

**Veredicto:** una lista oficial y cinco copias que se mantienen a mano. Dos ya divergen (filas 4 y 5); ninguna tiene prueba que la compare con el registro.

### 2.4 Extremidades: ¿beben y alimentan?

| Extremidad | Bebe de | Alimenta a | Evidencia |
|---|---|---|---|
| Panel de obra | ficha (snapshot) + xlsx directos | — | Salvo F2/F3 |
| Generador de revisiones (tablet) | `obras_revisiones.js` (ficha + prioridades) | Un HTML exportado a mano a `REVISIONES` | `generador_revisiones.html` carga `obras_revisiones.js`; coherente con `§7c` |
| Personal en obra (tablet) | `personal_estado.js`, `personal_calculo.js`, service worker | Un `CONTROL HORARIO` a mano | `generador_personal.html`; cumple las 4 reglas de `§7c` |
| Ranking de personal | `personal_estado.js` | — | |
| **Apps de `VARIOS`** (baterías, tierras, buscador eléctrico) | **Nada del cuerpo**; solo `localStorage` (4, 17 y 3 usos) | **Nada** | `grep` en los tres HTML: ninguna referencia a `ficha_obra`, `resumen_obras`, `personal_estado`, `obras_revisiones` |
| Postventa / Mantenimiento / CARDIVA | Carpetas, Word, PDF | Índices propios | Sin clave común con el registro |

Las apps de `VARIOS` son extremidades amputadas: lo que Bixente teclea en la tablet no existe en el PC y viceversa, y borrar los datos del navegador lo borra todo. `CONFIRMADO` por `grep`; el uso real y el valor de esos datos, `NO VERIFICABLE`.

### 2.5 Documentación desfasada (hecho contrastado con código)

| Documento dice | Código/dato dice | Etiqueta |
|---|---|---|
| Mapa mental y encargo: «`CATALOGO_TAJOS.json` no está en git (decisión 11/08)» | Está versionado, entró en `78c0b3a`; el `.gitignore` sigue sin excepción para él (frágil: una copia nueva se ignoraría) | `CONFIRMADO` (`git ls-files`) |
| Mapa: «39 tajos comunes (+18 de Orueta)» | Catálogo v1.3: 93 tajos | `CONFIRMADO` |
| Mapa: «portal móvil estancado, código inalcanzable» | `sagarde_portal.py:1676` llama a `generar_portal_movil` en cada ejecución; `_SISTEMA/PORTAL SAGARDE.html` cambió en el último commit | `CONFIRMADO` |
| `CLAUDE.md §3`: «Mungia 79.8, Gernika 76.3, Bolueta 41.7, Obispo Orueta 80.0» como guardas contra efectos colaterales | Hoy 90,3 / 94,1 / 76,7 (Orueta cerrada). 76,3 es el valor de Gernika del 25/07. Ninguna prueba comprueba estas cifras | `CONFIRMADO` |
| `_SISTEMA/MOTOR/CLAUDE.md` (se carga en cada sesión): `python _MOTOR_SAGARDE/scripts/regenerar_obra.py`, «Motor: `_MOTOR_SAGARDE\`» (3 menciones), skills `/sagarde-actualizar`, `/sagarde-nueva-obra` | El motor vive en `_SISTEMA/MOTOR`; las skills reales son `sagarde-actualizar-obra`, `-cerrar-obra`, `-informe-ejecutivo`, `-nota-pendiente`, `-personal`, `-revision`, `generate-cardiva-report`; no existe `sagarde-nueva-obra` | `CONFIRMADO` |
| Mapa: «cuatro BAT» | 5 `.bat` documentados, 2 en git | `CONFIRMADO` |

`actualizar_mapa_mental.py` solo vigila el propio mapa; nadie vigila los `CLAUDE.md`.

---

## 3. Los `.bat` como circulación

### 3.1 `Actualizar_Sagarde.bat` (versionado, `CONFIRMADO` línea a línea)

| Paso | Líneas | Lee | Escribe | Si falla |
|---|---|---|---|---|
| 0 Auditoría | 15-28 | Obras, mantenimientos, hojas de materiales, personal | `_SISTEMA/MOTOR/auditoria_diagnostico.json` (no publicado) | **Para** solo con código 3 = errores de **personal**. Materiales y obras son `warning`: aunque el auditor compruebe el xlsx dañado de Olabeaga (`auditor_sagarde.py:171-195`), **no frena** |
| 1 Obras | 31-37 | Adaptadores, fichas, xlsx | Por obra: `panel.html`, prioridades, dudas, memoria, ficha, PDF ejecutivo; globales: `index.html`, `resumen_obras.json`, `obras_revisiones.js`, `personal_estado.js` | Aviso y **sigue y publica** (`OBRAS_FALLO`). Excepción de una obra → entra en `fallidas`; divergencia de cutover o fallo del PDF → **ni siquiera eso** (F4, F7) |
| 2 Postventa y mantenimiento | 39-48 | Carpetas | Índices + `*_resumen.json` | Aviso y sigue |
| 3 Portal | 50-57 | `resumen_obras.json`, `postventas_resumen.json`, `mantenimientos_resumen.json`, `auditoria_diagnostico.json` | `index.html`, índices de área, `_SISTEMA/PORTAL SAGARDE.html` | **Para**, no publica |
| 4 Enlaces | 60-68 | HTML generados | — | Aviso («Se publica igual»); mira el **disco local**, no lo publicable (§4) |
| 5 Mapa mental | 71-79 | Fichas, resumen | Tablas AUTO del mapa | Aviso y sigue |
| 6 git | 82-128 | Todo | `git add -A`, `git add -f` de los PDF, commit, `push origin main` | Para si falla commit o push. Sin `pull` previo, sin suite de pruebas, sin comprobar que no haya ficheros mutados (riesgo ya documentado en `CLAUDE.md §4`) |

Observaciones:
- De los 7 pasos, **solo 3 pueden detener la publicación** (paso 0 por personal, paso 3, paso 6). El resto avisa y sigue.
- Los pasos que producen cifras (1) no pueden pararla. Todo el modelo de control descansa en leer el recuadro de la consola.
- `comprobar_enlaces.py` solo conoce 6 páginas fijas y el `panel.html` de las 7 obras registradas; no mira los HTML de `VARIOS` ni los de obras cerradas.
- `SCR/actualizar_obra.py:42` usa `py -3.11` fijo; el `.bat` usa `python` o `py` sin versión. Dos intérpretes posibles según quién lance. `INFERIDO` que sea un riesgo; ninguna evidencia de que haya fallado.

### 3.2 Los otros cuatro `.bat`

| `.bat` | Estado en git | Qué se sabe |
|---|---|---|
| `Abrir_Panel_Local.bat` | Versionado (forzado; el `.gitignore` lo ignoraría) | 3 líneas: `cd` + `python panel_server.py` + `pause`. `CONFIRMADO` |
| `Actualizar_Obras.bat` | **No versionado** | Solo se sabe por el mapa mental («instala y regenera», «instala sin versiones») y por el panel, que arma su ruta (`generar_todos.py:2087`). **NO VERIFICABLE** |
| `_SISTEMA/Servidor_Local.bat` | **No versionado** | Mapa mental: «HTTP LAN 8080», hace `cd %~dp0..`. **NO VERIFICABLE** |
| `POST-VENTAS/_SISTEMA/Actualizar_Postventas.bat` | **No versionado** | Mapa mental: «regenerar/abrir postventa». Se desconoce si ejecuta `postventas_sync.py` (el único escritor del Word matriz). **NO VERIFICABLE** |

Tres de las cinco arterias no se ven desde el repositorio. El `.gitignore` es lista blanca (`*`), no admite `*.bat`, y la excepción de `Actualizar_Sagarde.bat` es nominal. Es el mecanismo exacto del §4 de `CLAUDE.md` («un tipo de fichero nuevo exige tocar `.gitignore` y el `.bat` a la vez»), aplicado a los propios `.bat`.

---

## 4. Lo generado frente a lo publicado (`.gitignore` como lista blanca)

Prueba hecha con `git check-ignore --no-index` sobre rutas que el pipeline escribe de verdad y `git ls-files` para ver si están en el repositorio.

### 4.1 Generado y **no** publicado

| Fichero | Quién lo genera | Quién lo necesita | Efecto |
|---|---|---|---|
| **`prioridades_trabajos_zesp.json`** | `generar_todos.py:1826,2062` | **Enlace del panel** «Ver cálculo y detalle completo» (`panel_obra.py:1349,2150`), presente en el `panel.html` publicado de **Bolueta, Olabeaga y Barakaldo** | **404 en GitHub Pages**; los otros dos JSON de prioridades sí están en la lista (comentario del `.gitignore`: «enlazados desde los paneles»). `CONFIRMADO` por la lista blanca y por `ls` del directorio publicado |
| Documentos de obra (DOCX, PDF, XLSX, TXT, JPG, COCOPLAN…) | Los pone Bixente | Pestaña «Documentos» de cada panel (`lectores.listar_documentos:216-264`): decenas de `href="../…"` | Casi todos dan 404 en tablet y móvil. Es decisión documentada para PDF/recortes, pero el panel los lista como abribles |
| `informe_movil.pdf` | `generar_todos.py:2147` (solo sin `--no-pdf`; el `.bat` usa `--no-pdf`) | — | El `.bat` nunca lo genera; no se publica por `*.pdf`. Consistente, pero no existe en la nube |
| `memoria_obra.json` | `generar_todos.py:2022` | Nadie (F2) | No publicado ni leído |
| `resumen_obras.json`, `auditoria_diagnostico.json`, `*_resumen.json` | pasos 0-2 | Portal, mapa mental (en la misma pasada) | Un clon limpio no puede regenerar el portal sin ejecutar antes los pasos 1-2; `sagarde_portal.py:1683,1687` solo avisa |
| Hojas de materiales (`*.xlsx`), `FICHA DE OBRA.xlsx`, `CONTROL HORARIO *.json` | Bixente / tablet | Panel y personal | Datos de entrada fuera de git. Una copia por OneDrive; sin historial |
| `Actualizar_Obras.bat`, `Servidor_Local.bat`, `Actualizar_Postventas.bat` | A mano | Bixente | Ver §3.2 |

### 4.2 Publicado y que nadie genera ya (candidatos)

| Fichero | Evidencia | Etiqueta |
|---|---|---|
| `2025 GERNIKA 32V/INFORME SAGARDE IA/revision_gernika_22072026.html` | Ningún `.py` lo cita; último cambio 15/10/2026 | `INFERIDO` (resto del flujo antiguo) |
| `…/OBRAS CERRADAS/…/panel.html` (Orueta) y su `INFORME SAGARDE IA` | Obra cerrada; solo `cerrar_obra.py` lo movió | `INFERIDO`, legítimo (archivo) |
| `2026 GORLIZ HOSPITAL/INFORME SAGARDE IA/{panel.html, prioridades_trabajos.json, dudas_pendientes.json, cierre_expediente.json}` | Sí se regeneran cada pasada, pero son marcadores «sin base» | `CONFIRMADO` que se generan; publicar un panel «—» es consciente |

### 4.3 Qué NO es fuga (descartado)

- **`personal_estado.js`, `personal_calculo.js`, `personal_sw.js`, iconos, `obras_revisiones.js`, `chart.min.js`**: están en la lista blanca y los comprueban `tests/test_publicacion_personal.py` y compañía. Es el patrón correcto.
- **`confirmaciones_*.json`, sidecars `.correcciones.json`/`.clasificacion.json`**: cubiertos por el `.gitignore`.

---

## 5. Veredicto: cuerpo único u órganos sueltos

| Dominio | Estado | Por qué |
|---|---|---|
| Obra: estructura, estados, prioridades, KPI, panel, portal, generador | **Cuerpo único** (con las goteras F1-F4) | Todo parte de `ficha_obra.json` / `ficha_garajes.json` |
| Personal en obra | **Cuerpo único, módulo propio bien integrado** | Un escritor, entrada por fichero, `personal_estado.js` para tablet y ranking |
| Informe ejecutivo | **Misma fuente, otra definición** | F1 |
| Materiales, tareas/notas | **Parcial**: bebe de xlsx no versionados, sin copia útil en la base | `ficha.materiales/documentos/contactos` son copias muertas (§1) |
| Cierre de expediente | **Almacén propio dentro del cuerpo** | JSON manual por obra, leído por panel e informe |
| Postventa, Mantenimiento, CARDIVA | **Órganos sueltos** | Sin clave común, índice y datos propios |
| Apps de `VARIOS` | **Extremidades desconectadas** | Solo `localStorage` por navegador |

Resumen contable (`INFERIDO`, criterio mío): de 7 dominios, **2** son cuerpo único sin reservas, **3** son parciales o con otra definición, **2** (más las apps) son órganos sueltos. En obra, el cuerpo existe y es sólido; fuera de obra, el «ente vivo» todavía son varios organismos.

### 5.1 Top 10 de fugas con riesgo de cifras discordantes

Ordenadas por riesgo de que Bixente vea **dos números distintos para lo mismo** sin darse cuenta.

| # | Fuga | Esfuerzo | Prueba que la detectaría |
|---|---|---|---|
| 1 | **F1** Dos «avances» bajo la misma etiqueta (panel/portal/mapa frente a PDF). Dif. hasta 3,6 pp en obras reales | **M** (hay que decidir con Bixente el alcance oficial; luego rotular los dos o unificar) | Prueba de contrato que, para cada obra con ficha, recalcule el desglose con ambos alcances y compruebe que cada consumidor muestra el suyo **con rótulo distinto**. Mutación: cambiar el filtro `propio` en `generar_informe_ejecutivo.py:175` y exigir que falle |
| 2 | **F2** Memoria: «ausente = terminado al 100 %». 21-27 sombras por obra; Bolueta «Apliques» 100 frente a 0,0 | **S** (resolver nombres por id de catálogo antes de acumular, o no forzar 100 % si hay ficha) | Para cada obra con ficha: `{tajos 🏠 de DATA.por_tarea} ⊆ {tajos de la ficha}` y ningún tajo con dos valores. Mutación: reinsertar un nombre antiguo en el historial |
| 3 | **F3** Serie histórica: último punto de ficha acumulada, anteriores de hoja; denominadores 1256 → 1461; `variacion_pct` arrastra el salto | **M** | Invariante: el último punto de `serie` iguala el KPI de cabecera **del mismo ámbito**, y los saltos de `total` entre puntos consecutivos se rotulan o se rechazan |
| 4 | **F4** Cutover divergente solo por consola: panel sobre ficha vieja, exit 0, `.bat` publica | **S** (añadir la obra a `fallidas` o banner en el panel) | Simular una divergencia (mutar un estado en el camino antiguo) y comprobar `main()` ≠ lista vacía y banner visible. Hoy `tests/test_cutover_generar_todos.py` lo prueba por separado; falta el extremo a extremo |
| 5 | **F5** Medias del portal con OBRA PRUEBA y Gorliz = 0; dos implementaciones del agregado | **S** | Totales excluyen `prueba` y obras sin datos; igualdad `generar_todos` frente a `regenerar_obra._recalcular_totales_resumen` con la misma entrada |
| 6 | **F8** `SCORE` y `ESTADO_VALOR` duplicados, sincronía solo en comentarios | **S** | `assert motor_informes.SCORE == priorizador_trabajos.ESTADO_VALOR`. Mutación: cambiar un peso |
| 7 | **F7** PDF ejecutivo viejo se publica si falla la generación | **S** | Probar que un fallo de `generar_para_obra` quita el enlace o marca el PDF como desfasado (comparar fecha del PDF con la de la ficha) |
| 8 | **F6** Banner «rejilla incompleta» fijo en 3 de 6 paneles; verificador ciego | **M** (esperado por tipo de ubicación) | Fixture con una celda borrada **debe** avisar; fixture esparcida legítima **no** |
| 9 | Listas de obras paralelas (`ESPERADAS`, literales de Olabeaga, `catalogo.obras['olabeaga']` inexistente, adaptadores huérfanos) | **S** | Prueba estática que recorra el código buscando ids/nombres de obra y los compare con el registro; `verificar_hojas_pdf.ESPERADAS` ⊆ registro y con cifras tomadas de la ficha |
| 10 | **F9 + escritores múltiples de la ficha** (`generar_todos` reescribe la verdad medida en cada publicación; 3 caminos de escritura) | **M** (decisión de diseño: ¿quién puede escribir la base?) | Prueba que ejecute `generar_todos` sobre una copia con la ficha más nueva que el adaptador y afirme que la ficha no retrocede; mutar `ficha_obra._ordenar_revisiones` |

### 5.2 Otros hallazgos no numéricos (de §3 y §4), por orden de utilidad

1. `comprobar_enlaces.py` valida el disco, no lo publicable → `prioridades_trabajos_zesp.json` (3 paneles) y la pestaña «Documentos» dan 404 sin aviso. **S–M.** Prueba: repositorio temporal con el `.gitignore` real; un enlace a un fichero ignorado debe salir roto.
2. Tres de cinco `.bat` fuera de git; `Actualizar_Postventas.bat` quizá dispara el único escritor de postventa. **S** (versionar con `git add -f` o excepción nominal) + decisión de Bixente.
3. `CLAUDE.md` de `_SISTEMA/MOTOR` con rutas y skills que no existen; guardas de `§3` con cifras de julio. **S.** Prueba: extender `actualizar_mapa_mental.py` a todos los `.md` de instrucciones.
4. Apps de `VARIOS` sin conexión y con estado por navegador. **L** si se quiere integrarlas; **S** si basta con documentarlo.
5. `ficha.contactos/materiales/documentos` son copias muertas que caducan (`dias_desde`). **S** (quitar o dejar de persistir).
6. Subcomando `ingerir` en `personal_obra.py:1893` frente a `CLAUDE.md §7c`. **S.**

---

## 6. NO VERIFICABLE y límites

- **Contenido de datos de obra no versionados:** `FICHA DE OBRA.xlsx`, hojas de materiales (`ENTREGAS`), `CONTROL HORARIO *.json`, DOCX/PDF de revisión, Word de postventa, carpetas de mantenimiento. Se auditó el código que los lee y escribe, no su contenido.
- **Los tres `.bat` no versionados** (§3.2).
- **Cifras de `resumen_obras.json`:** no está en git. Verificado por código y por el mapa AUTO (que sí lo lee); el valor del «avance medio» del portal es `NO VERIFICABLE`.
- **Historial crudo de los adaptadores:** depende de ficheros de `REVISIONES` que no están todos en el repositorio; por eso F3 queda en `INFERIDO` en lo que atribuye a la mezcla.
- **Ejecución de la suite:** no la ejecuté (el encargo era de solo lectura y los tests escriben en carpetas temporales y a veces en disco). Las afirmaciones sobre «ninguna prueba cubre X» salen de `grep` sobre `tests/`; una prueba con otro nombre o por reflexión no se descarta.
- **Datos personales:** no se copió ni un nombre de trabajador. `personal_estado.js` y `personal_obra.json` se publican por decisión de Bixente (comentarios del `.gitignore`); no se auditó su contenido.
- **Plataforma:** análisis hecho en Linux; los `.bat` son de Windows y no se ejecutaron.

### Dudosos descartados

- **«`CATALOGO_TAJOS.json` fuera de git»:** descartado, está versionado (`git ls-files`).
- **«Las prioridades del panel se leen de disco»:** descartado; panel y PDF reciben el dict en memoria. Solo el generador de revisiones lo relee de disco (`generar_todos.py:900`).
- **«El garaje se cuenta dos veces»:** descartado; el KPI combinado suma celdas de ambas fichas una sola vez, verificado al decimal (§2.1).
- **«Panel y portal difieren»:** descartado; coinciden al decimal con la ficha. La discrepancia es con el PDF y dentro del propio panel (cabecera frente a gráfica).
- **«El portal móvil está estancado»:** descartado (§2.5).
- **«`?` y `N` rompen el cálculo»:** descartado en la práctica; hay 0 celdas `?` en las 6 fichas y `N` se excluye bien (`ficha_obra.py:278`).
- **«`panel_server` expone escritura en red»:** descartado; escucha solo en `127.0.0.1` (`panel_server.py:15,119`).

---

## 7. Cómo reproducir los dos cálculos clave

Solo lectura; no escribe nada en el repositorio.

```bash
# Desglose por obra desde la ficha y comparación con lo publicado en el panel (§2.1)
python3 - <<'EOF'
import json, re, os
R = "SAGARDE OBRAS ABIERTAS"
for o in ["2025 GERNIKA 32V", "2026 BOLUETA ACR", "2026 MUNGIA ACR NEINOR",
          "2026 OLABEAGA BILBAO", "2026 BARAKALDO 104V OBRAS ESPECIALES", "2026 OBRA PRUEBA"]:
    b = f"{R}/{o}/INFORME SAGARDE IA/"
    f = json.load(open(b + "ficha_obra.json", encoding="utf-8"))
    c = {k: 0 for k in "XM/PN?"}
    for v in f["estados"].values():
        c[v["v"]] += 1
    t = c["X"] + c["M"] + c["/"] + c["P"]
    print(o, c, "pond=%.2f" % ((c["X"] + .6*c["M"] + .25*c["/"]) / t * 100))
    h = open(b + "panel.html", encoding="utf-8").read()
    print("   panel:", re.findall(r'class="kpi"><div class="label">([^<]*)</div><div class="value">([^<]*)', h)[:2])
EOF

# PDF ejecutivo: cifras de cabecera
pdftotext -layout "SAGARDE OBRAS ABIERTAS/2025 GERNIKA 32V/INFORME SAGARDE IA/INFORME_EJECUTIVO_2025_GERNIKA_32V.pdf" - | sed -n 7,10p

# ¿Qué se ignora de lo que enlaza un panel? (§4.1)
git check-ignore -v --no-index "SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/INFORME SAGARDE IA/prioridades_trabajos_zesp.json"
```
