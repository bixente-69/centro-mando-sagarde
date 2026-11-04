# H · Auditoría del generador de revisiones (`generador_revisiones.html`)

**Fecha:** 04/11/2026 · **Rama:** `claude/blissful-cannon-o3by6q` · **Fichero:** `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html` (2.546 líneas, 1,38 MB: tres copias del logo en base64).
**Por qué este primero:** es la app que imprime la hoja de campo; lo que se marca en ella entra por `data-k`/`data-st` en las fichas. Un fallo aquí contamina los datos de todas las obras.
**Método:** lectura del código real → reproducción en Chromium con datos inventados → prueba que falla → corrección → prueba en verde → mutación → suite completa.

## 1. Fallos encontrados y corregidos

Todos son de la familia del proyecto: *algo declarado que el motor ignora en silencio*. Los cuatro primeros se **reprodujeron antes de tocar nada**.

| # | Fallo | Medido antes | Corrección |
|---|---|---|---|
| H1 | La hoja recupera las marcas guardadas con un `querySelector` armado a mano. Una vivienda con comillas en el nombre lo rompe; el `catch` vacío se lo traga y se pierden **todas** las marcas que venían después. Una marca guardada sin celda se descartaba sin avisar. | 5 marcas guardadas → **1** recuperada | Mapa clave→celdas. Se cuenta lo que no encaja y se avisa 9 s (no sale en el PDF). Almacenamiento corrupto: se dice. Almacenamiento bloqueado: sigue callando (la hoja funciona igual). |
| H2 | `setViv` dejaba renombrar una vivienda con un nombre ya usado en la planta (`addViv` sí lo impedía). Dos columnas con la misma clave `portal__planta__tajo__vivienda`. Nombre en blanco: el dato se conservaba pero la caja se quedaba en blanco. | **37** claves `data-k` repetidas | Se rechaza (sin distinguir mayúsculas), se avisa y la caja vuelve al nombre anterior. |
| H3 | «Recientes» pintaba `onclick="loadConfig('<clave>')"` sin escapar. | `D'ARCY` no se puede reabrir: `SyntaxError: missing ) after argument list` | Clave escapada en `data-key` y un solo escuchador. El nombre ya no se interpreta como HTML. |
| H4 | La fecha por defecto salía de `toISOString()` (UTC). | A las 00:30 locales del 05/11 daba **2026-11-04**; con la pestaña abierta de un día a otro «Nueva revisión» seguía con la fecha vieja | `hoyISO()`: fecha local, calculada cada vez. |
| H5 | `doDownload` liberaba la URL del blob en el mismo instante del clic (`doSave` de la propia hoja no). | **No reproducido** en Chromium | Mismo gesto que `doSave`. Es endurecimiento: Safari/iPad y Firefox pueden anular la descarga. Sin probar en tablet real. |
| H6 | `saveKey()`: código muerto, nunca llamado, sobre un elemento `#api-key` que no existe; mostraba «Clave guardada ✓» sin guardar nada. | — | Eliminada. (La copia de `_SISTEMA/scratch/` la conserva: es un resto.) |
| H7 | **Garaje:** `addZona` e `incGarageCount` nombraban contando las zonas existentes y sumando uno. Al quitar una del medio salían nombres repetidos en la misma planta: en la hoja impresa, dos columnas con el mismo rótulo. (Las claves `data-k` de garaje llevan el `id` de la zona, no el nombre: no hay colisión de datos; el riesgo es humano, poner la marca en la columna equivocada.) | `Trasteros 1,3,3` · `Zona B,C,C` · `Basuras 2,2` | `nombreLibreZona`: primer nombre de la planta no usado, sin distinguir mayúsculas. Sin huecos, la numeración sale igual que antes. Se quita `garageCount()`, que se quedó sin usos. |

## 2. Cómo se verificó (cifras reales)

- **Pruebas nuevas:** `tests/test_generador_revisiones_auditoria.py`, 44 pruebas en Chromium real. Primera tanda (H1–H5): 27 pruebas, **18 en rojo** sobre el código sin corregir (las otras 9 fijan lo que ya funcionaba). Segunda tanda (H7 y guarda de impresión): 11 pruebas, **4 en rojo** antes de corregir. Final: 44 en verde (las 2 últimas fijan la decisión de Bixente sobre las marcas guardadas).
- **Mutación (`CLAUDE.md` §3):** 27 mutantes sobre **copias** (el original no se tocó). De los 20 primeros, **16 murieron a la primera; 4 sobrevivían** y eran huecos de mis pruebas: aviso que se apaga en 1,6 s, aviso falso al reconfirmar el propio nombre, rama «nombre en blanco» sin prueba (la añadí sin ella) y rama de fecha ilegible nunca ejercitada. Se añadieron 4 pruebas: 20/20. De los 7 de garaje, uno (quitar el `!important` de la regla de impresión) **sobrevivía y es equivalente**: una regla de autor ya gana a la del navegador para `[hidden]`; el mutante que de verdad rompe la regla (quitar el `display:block`) sí muere. **27/27 muertos** salvo ese equivalente.
- **Suite completa** (`python -m unittest discover -s tests`):
  - Línea base antes de tocar: 1544 pruebas, 41 errores, 6 saltadas.
  - Tras H1–H6: 1575 pruebas, **los mismos 41 errores, ninguno nuevo**.
  - Con las dependencias que faltaban instaladas en un entorno aislado fuera del repo (`openpyxl`, `pdfplumber`, `python-docx`, `reportlab`, `beautifulsoup4`): 1892 pruebas, 23 fallos. Tras H7: **1903 pruebas, los mismos 23 fallos, ninguno nuevo**. Todos de entorno: 20 de `test_sembrar_ficha_obra` (ruta `D:\Nueva carpeta\…`), 1 de `test_panel_server` (rechazo de unidad de Windows), 1 de `test_adaptar_revision_tinta` (necesita el commit `5c90dec`, ausente en este clon) y 1 de `test_paginacion_generador` (abre Edge). Los dos módulos que leen hojas generadas por este generador (`test_alta_hoja_html_generica`, `test_estructura_con_mapas_explicitos`) no se podían importar en la línea base y ahora **pasan**.
- **Antes/después de cifras de obra (`CLAUDE.md` §3):** no hay. El cambio es solo de cliente (HTML); no se tocó ninguna `ficha_obra.json` ni el motor, y `git status` lo confirma. No se ejecutó `Actualizar_Sagarde.bat`.

## 3. Lo que NO está revisado ni resuelto (no es «perfecta»)

**Revisado en el segundo paso (garaje), sin más defectos:** `generateGarajeHTML`, `renderGarageSheetSection`, `renderGarageZoneTable`, `garageCellHTML`, `normaliseGarajeStructure`, la edición de plantas y zonas. Comprobado con datos reales y en Chromium:
- Los 6 tipos de zona que traen las `ficha_garajes.json` versionadas (`vial`, `rellano`, `escalera`, `trastero`, `cuarto_tecnico`, `cuarto_ligero`; 77 zonas en 4 obras) son exactamente los 6 que la hoja sabe imprimir: hoy no desaparece ninguna zona. Un tipo desconocido sí se descartaría en silencio, pero ninguna ficha lo trae.
- Elegir una pestaña y luego imprimir **sí imprime todas las secciones** (guardado con prueba).
- Un garaje sin ninguna planta saldría como hoja en blanco sin aviso, pero no se alcanza desde la pantalla (`setModo` y `loadConfig` siempre dejan al menos uno). Latente.
- `setZona` permite poner a mano un nombre repetido. No lo he cambiado: no hay colisión de claves (van por `id`) y es una decisión explícita de quien teclea.

**Sin revisar:** la paginación (`repartirTajosEnHojas`, tiene sus propias pruebas), las zonas especiales de vivienda, el CSS de impresión salvo las reglas citadas, y las pantallas del asistente (`renderTajos`, `renderSummary`, `renderSummaryGaraje`). Tampoco la usabilidad en tablet.

**Observado por lectura, sin corregir y sin medir:**
1. `saveConfig()` no tiene `try/catch` y, al salir una obra de las 8 recientes, su clave `sgd_rev_cfg_*` (con el `importData` entero) **no se borra**: el almacenamiento solo crece. Si se llena, no pasa nada visible.
2. ~~`restore()` mezcla lo que trae la hoja con lo guardado en el aparato para la misma obra+fecha.~~ **DECIDIDO por Bixente el 04/11/2026: se queda como está.** Razón de campo, textual: un edificio de 23 plantas (Bolueta) se sube andando, planta a planta, con la tablet en la mano; «es facilísimo que se te resbale y te salgas de la pantalla», y a veces guarda hojas de seguridad por si se apaga o se borra, por eso la última revisión sale a veces con un «(2)» o un «(3)». Esas copias son **a propósito**: no son una anomalía (ni deben dar falsas alarmas el aviso `REVISIONES_DUPLICADAS` del auditor, ver G). Fijado con una prueba (`test_decision_de_bixente_…`) para que nadie lo «arregle». **Matiz comprobado en Chromium:** lo guardado se comparte entre ficheros (`file://` es un único origen), pero las marcas solo vuelven a una hoja nueva si sus identificadores de portal y planta son los mismos, que es lo que pasa con una obra de la base (ficha). En una estructura montada a mano cada generación inventa identificadores nuevos y las marcas viejas **no casan**: antes se descartaban sin decirlo, ahora se avisa (prueba incluida).
3. Un nombre de vivienda con `__` daría una clave de 5 partes. No he comprobado cómo la trata `adaptar_revision_html.py`. Improbable en la práctica.
4. Las celdas `P` y `?` de la ficha salen en blanco en la hoja (solo viajan `X`, `M`, `/`, `N`). Es por diseño (el lector convierte blanco→`P`), pero se pierde la diferencia al imprimir.

**No probado en dispositivo real:** tablet/iPad, y el PDF por Edge (`test_paginacion_generador.PdfReal` no pudo ejecutarse aquí). La regla de impresión nueva sí se comprueba con `emulate_media('print')`.

## 4. Peligros encontrados fuera del generador

- **La suite reescribe `personal_estado.js`**, fichero versionado, cada vez que se ejecuta (cambia `generado` y borra la entrada `prueba`). Con `Actualizar_Sagarde.bat` (`git add -A`) se publicaría. No he identificado qué prueba lo hace. Lo restauré con `git checkout` tras cada ejecución. Además, el `personal_estado.js` versionado **todavía contiene la entrada `prueba`** aunque OBRA PRUEBA se dio de baja (`766a94f`): se limpiará en el próximo ciclo del `.bat`.
- **`.gitignore` línea 2 (`*`) cubre `_SISTEMA/docs/auditorias_nube_*/`** sin excepción propia. Los informes A–G están rastreados «de hecho»; este H hubo que añadirlo con `git add -f`. No he tocado el `.gitignore` (es decisión de Bixente).

## 5. Siguiente en la lista

Informe de tierras (`VARIOS/TIERRAS/app_informe_tierras.html`, 2.758 líneas): calcula valores de instalación y acaba en un informe firmado. Después, el ranking de personal (`personal_sagarde.html`).
