# Memoria · generador de revisiones, trabajo de campo y entorno de pruebas en la nube

**Fecha:** 04/11/2026 · **Qué es:** memoria vigente de la sesión que auditó `generador_revisiones.html` (14 fallos corregidos, fusionado en `main` con la PR 14). Léela **antes de volver a preguntar a Bixente** o de tocar el generador. Todo lo de aquí está medido o confirmado por él; lo que es suposición va marcado como tal.

Documentos hermanos: informe de la auditoría (`_SISTEMA/docs/auditorias_nube_2026-11-04/H_generador_revisiones.md`) y decisiones de Bixente (`_SISTEMA/docs/auditorias_nube_2026-11-04/G_decisiones_bixente.md`, decisiones 8 y 9).

---

## 1. Hechos de campo confirmados por Bixente (no se discuten)

- Una obra grande (Bolueta, **23 plantas**) se sube **andando, planta a planta, vivienda por vivienda, escalera y rellanos, con la tablet en la mano**. Textual: *«es facilísimo que se te resbale y te salgas de la pantalla»*.
- Guarda **hojas de seguridad por si se apaga o se borra**. Por eso en `REVISIONES` aparecen copias `(1)`, `(2)`, `(3)`: **son a propósito, no una anomalía**. El auditor las ve como `REVISIONES_DUPLICADAS` de nivel `info` y el motor se queda con la de modificación más reciente.
- Las marcas guardadas en el aparato **tienen que seguir volviendo al reabrir la hoja**. *«Tiene que ser así. Comprobado con trabajo de campo.»* No «arreglar» esa recuperación.
- Bixente es electricista, no programador: **una pregunta cada vez, en llano**, con recomendación.
- Quiere acabar subiendo el portal **una vez por semana, los viernes desde la oficina**.

## 2. Cómo guarda el generador (invariantes que no se rompen)

**Las marcas de cada hoja** se guardan en el aparato al pulsar cada celda (`autoSave`) y se recuperan al abrir (`restore`):

| Clave en `localStorage` | Contenido | Tamaño medido |
|---|---|---|
| `sgd_rev_<obra>_<fecha>` y `…_garaje` | marcas de esa hoja (`{clave de celda: estado}`); `<obra>_<fecha>` va con `encodeURIComponent` | una hoja de Bolueta con las 3.740 celdas marcadas: **223.690 caracteres** |
| `sgd_rev_cfg_<obra>` y `…_garaje` | configuración de «Recientes», con todas las celdas de la obra | Bolueta 197.738 · Mungia 135.923 · Gernika 76.682 |
| `sgd_rev_recents` | lista de las 8 últimas | pequeña |

- Cuota del aparato en Chromium: **unos 5,2 millones de caracteres** por origen. `file://` es **un único origen compartido** por todos los ficheros locales (comprobado), así que el generador, las hojas y la vista previa comparten cuota. Caben unas **23 hojas grandes de Bolueta**.
- **Claves de celda:** vivienda `portal.id__planta.id__tajo.id__vivienda` (lleva el *nombre* de la vivienda); garaje `garaje.id__planta.id__tajo.id__zona.id`; zonas especiales `portal.id__zesp__tajo.id__zona.id`. El registro (`obras_revisiones.js`) solo exporta los estados `X`, `M`, `/`, `N`: `P` y `?` salen en blanco por diseño (el lector convierte blanco→`P`).
- **Las marcas solo vuelven a una hoja nueva si portal y planta tienen los mismos identificadores** (obra de la base). En una estructura montada a mano cada generación inventa `uid()` nuevos y las marcas viejas no casan: ahora se **avisa** en vez de descartarlas en silencio.
- **Política de limpieza (decisión 9, opción B):** si el aparato se llena, `escribirHaciendoSitio` borra **solo** copias `sgd_rev_<obra>_<fecha>[_garaje]` de **más de 30 días** (31 o más), la más vieja primero y solo las necesarias, y avisa. **Nunca** toca la clave que se está escribiendo, `sgd_rev_cfg_*`, `sgd_rev_recents` ni nada de otra aplicación. Es una función **autónoma**: se incrusta en cada hoja con `toString()`, así que no puede usar variables de fuera.
- **«Guardar revisión» descarga el HTML completo** y **no depende del almacenamiento**: es la salvaguarda real. Si no se está guardando en el aparato, la hoja avisa y manda a pulsarlo.
- **Fecha:** siempre local (`hoyISO()`), nunca `toISOString()` (UTC daba el día anterior pasada la medianoche).
- Paso 3 del asistente: las **hojas por tabla se calculan con la matriz de viviendas**, no con todos los tajos. El resumen del paso 4 cuenta solo los tajos de zonas especiales que de verdad se imprimen.

## 3. Hallazgos corregidos (resumen; detalle y medidas en el informe H)

| # | Qué fallaba | Dónde está la prueba |
|---|---|---|
| H1 | Recuperar marcas con `querySelector` a mano: una vivienda con comillas cortaba todo (5 guardadas → 1 recuperada) | `TestH1RecuperarMarcas` |
| H2 | Renombrar una vivienda a un nombre ya usado → claves repetidas | `TestH2ViviendasRepetidas` |
| H3 | `D'ARCY` no se podía reabrir desde «Recientes» | `TestH3Recientes` |
| H4 | Fecha en UTC | `TestH4FechaLocal` |
| H5/H6 | Descarga endurecida (no reproducido); `saveKey()` muerto | `TestH5Descarga` |
| H7/H7b | Nombres de zona repetidos (garaje y zonas especiales) | `TestH7NombresDeZonaDeGaraje`, `TestH7bNombresDeZonaEspecial` |
| H8/H9 | Autoguardado mudo con el aparato lleno; política B | `TestH8RedDeSeguridad`, `TestH9HacerSitio` |
| H10–H12 | Contador del paso 3 («2 hojas» donde salía 1), resumen de zonas especiales, nombres sin escapar | `TestH10…`, `TestH11…`, `TestH12…` |
| H13 | La única prueba de papel usaba la obra `prueba` (de baja) y exigía Edge | `test_paginacion_generador.py` |

Todas en `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_generador_revisiones_auditoria.py` (87 pruebas en Chromium real) y `test_paginacion_generador.py`. **65 mutaciones** sobre copias del código, todas detectadas (una equivalente descartada).

## 4. Cómo ejecutar las pruebas con navegador en la nube (hecho el 04/11/2026)

Playwright de **Python** no viene instalado; Node sí, y Chromium está en `/opt/pw-browsers` (`PLAYWRIGHT_BROWSERS_PATH` ya fijado). No hay Edge. Se instala **fuera del repo** (no entra en ningún manifiesto):

```bash
python3 -m venv /tmp/venv && /tmp/venv/bin/pip install -q playwright==1.63.0 \
  openpyxl pdfplumber python-docx reportlab beautifulsoup4
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA"
/tmp/venv/bin/python -m unittest discover -s tests            # ~5 min, 1950 pruebas
/tmp/venv/bin/python -m unittest discover -s tests -p "test_generador_revisiones_auditoria.py"
```

- Sin Playwright o sin Chromium las pruebas de navegador **se saltan** (no fallan): Bixente lo lanza todo con `.bat`.
- `P3_GENERADOR` apunta las pruebas del generador a una **copia** para mutar sin tocar el original; `P3_TMP` cambia la carpeta temporal.
- **Mutar siempre una copia**, nunca el original: copiar el fichero, sustituir una cadena exacta (comprobando que aparece una vez), ejecutar con `-f`, restaurar. El arnés que usé **no está versionado**; el método es ese.
- **Resultado de referencia (04/11/2026, con dependencias):** 1950 pruebas, **22 fallos, todos de entorno**: 20 de `test_sembrar_ficha_obra` (ruta `D:\Nueva carpeta\…`), 1 de `test_panel_server` (rechazo de unidad de Windows) y 1 de `test_adaptar_revision_tinta` (necesita el commit `5c90dec`, ausente en un clon superficial). `MOTOR/tests` (117 pruebas) no se ha ejecutado.
- **Dos pruebas intermitentes que ya fallaban antes de esta sesión** (sobre el commit `766a94f`): `test_generar_personal_ma5` (2 de 5) y `test_personal_enviar_con_ma7` (2 de 3). Un rojo suelto de ellas no es una regresión.
- **La suite reescribe `personal_estado.js`** (fichero versionado). Tras ejecutarla: `git checkout -- "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/personal_estado.js"`. Con `Actualizar_Sagarde.bat` (`git add -A`) se publicaría.
- Barrido de papel (Chromium en lugar de Edge): `python verificar_hojas_pdf.py`. **Da hoy 7 problemas que ya existían**: recuentos esperados desfasados (Gernika 1216 frente a 1184 leídas; Bolueta 3686 frente a 3589) y las páginas de zonas especiales, que el verificador no modela.

## 5. Flujo de publicación (comprobado)

- `Actualizar_Sagarde.bat` hace `add -A`, `commit` y `push origin main`, y **no hace `pull`**. Si `main` avanzó en GitHub (por ejemplo, tras fusionar una PR), hay que traer los cambios al PC **antes** de lanzarlo; si no, el push falla (no se pierde nada).
- GitHub Pages sirve los **ficheros fuente**: `generador_revisiones.html` llega a la tablet **en cuanto se fusiona en `main`**, sin esperar al `.bat`.
- En el GitHub Desktop de Bixente, `main` no tiene rama de seguimiento: sale **«Publish branch»** en vez de *Pull*. **No pulsarlo.** Para traer lo nuevo: *Repository → Pull*, o si sale en gris, *Branch → Merge into current branch… → origin/main*.

## 6. Medida: borrar revisiones antiguas (04/11/2026)

Bixente borró a propósito 4 revisiones HTML (2 de Gernika del 22 y 23/07; las **dos copias** del 04/09 de Mungia). Medido en una copia aislada, ejecutando el paso 1 del `.bat` antes y después: **el desglose `X/M//P/N` de las cuatro obras no se mueve**, prioridades y dudas tampoco; cambia el inventario de documentos (Gernika 14→12, Mungia 5→3) y **«Revisiones» de Mungia pasa de 4 a 3** (esa fecha desaparece de la lista). Aceptado por Bixente. Las copias siguen en el historial de Git.

## 7. Abierto, decisión de Bixente (no tocar sin preguntarle)

1. `ESPERADAS` de `verificar_hojas_pdf.py` desfasadas, y el verificador no entiende las páginas de zonas especiales.
2. La fila de identificación de las tablas de **zona especial y de garaje no lleva fecha** (la de la matriz sí). Tocarla puede romper `leer_pdf`; no probado en campo.
3. `.gitignore` línea 2 (`*`) cubre `_SISTEMA/docs/auditorias_nube_*/`: los informes nuevos de esa carpeta se añaden con `git add -f`.
4. Qué prueba reescribe `personal_estado.js`, y las dos pruebas intermitentes.
5. **No probado en dispositivo real:** tablet/iPad y PDF por Edge.
