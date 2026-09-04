# Sagarde — Motor de gestión de obras eléctricas

## Contexto

Proyecto de seguimiento de obras de instalación eléctrica y telecomunicaciones.
El usuario es el gestor/técnico que supervisa el avance de cada obra.

## Skills disponibles (invocar con `/nombre`)

| Skill | Cuándo usarlo |
|-------|--------------|
| `/sagarde-actualizar` | Actualizar una obra, el generador o el portal con alcance controlado |
| `/sagarde-revision` | Crear nueva hoja de revisión para una obra |
| `/sagarde-nueva-obra` | Configurar el entorno digital de una nueva obra |

## Arquitectura rápida (3 capas)

```
Origen de la revisión (3 formatos posibles, conviven):
  A) revision_{id}_DDMMAAAA.json     (formato antiguo: export "estados" simple)
  B) REVISION {OBRA} DDMMAAAA.pdf    (desde 25/07/2026: hoja de revisión de
     tajos en PDF, rellenada a mano en obra — ver protocolo PDF abajo)
  C) REVISION {OBRA} DDMMAAAA...html (desde 25/07/2026: export directo de la
     hoja interactiva de la app de tajos, con data-k/data-st ya rellenos —
     ver protocolo HTML abajo)
       ↓
lector_hoja_tajos_pdf.py / lector_hoja_tajos_html.py  →  motores GENÉRICOS de
     lectura (capa 0, comunes a TODAS las obras). Cada adaptador solo le pasa
     sus propios resolutores/diccionarios de portal/planta/tajo — ver recetas
     más abajo.
       ↓
adaptador_{id}.py  →  historial normalizado [(fecha, [registros]), ...]
       ↓
ficha_obra.json + correcciones (cuando existen) → historial validado
       ↓
generar_todos.py  →  memoria + prioridades + KPI + panel + informe ejecutivo
                     desde el MISMO historial validado
       ↓
sagarde_portal.py  →  index.html (Centro de Mando local)
       ↓
Actualizar_Sagarde.bat  →  git push → GitHub Pages
```

### Protocolo: cuándo un PDF es una revisión oficial válida

A partir del 25/07/2026 las revisiones pueden llegar en PDF (antes de fotos de
Wasap, si se adopta, haría falta OCR/visión — no construido todavía). Para que
un PDF funcione en todo el entorno (adaptador → motor → priorizador → panel →
informe → auditor), tiene que cumplir:

1. **Nombre**: empieza por `REVISION` y lleva una fecha `DDMMAAAA` reconocible
   (ej. `REVISION MUNGIA 25072026.pdf`). Sin esto ni el adaptador ni
   `auditor_sagarde.py` lo detectan.
2. **Ubicación**: carpeta `REVISIONES` de la obra — mismo sitio que las Word.
3. **Estructura de tabla**: hoja de revisión de tajos con cabecera de planta
   reconocible (`PLANTA`/`PLANTAS` + lista) y columnas de vivienda por portal
   — el mismo esquema que genera la app de tajos. La extracción de la tabla
   en sí (banner, columnas, celdas) la hace el motor genérico
   `lector_hoja_tajos_pdf.py` — ya sirve para cualquier obra con esta misma
   plantilla, sin tocarlo. Solo hace falta el adaptador propio de la obra
   (ver receta abajo).
4. **Marcas manuscritas (X/M a mano)**: el parser NO las lee solo con texto.
   Hacen falta lecturas verificadas a mano en un sidecar
   `<nombre_pdf>.correcciones.json` (clave `portal__planta__tajo__vivienda`).
   Sin sidecar, esas celdas cuentan como pendientes — nunca se inventa un dato.
5. **Fecha única**: una fecha por PDF, sin duplicar otra revisión ya cargada.
6. **Consistencia de ubicaciones**: si cambia el nombre/estructura de
   portales-plantas-viviendas entre revisiones (ej. ZR1.2 PB pasó de 3
   viviendas A/B/C a una sola fila "PORTAL" el 25/07/2026), hay que
   confirmarlo con Bixente y añadir una normalización histórica en el
   adaptador (ver `_normalizar_zr12_pb` en `adaptador_mungia.py` como
   ejemplo) — si no, el priorizador genera "dudas" falsas de tajos que
   "desaparecen".
7. **Dar de alta la obra en el registro único**:
   `_SISTEMA INFORME SAGARDE IA/registro_obras.py`. `generar_todos.py` y
   `generar_informe_ejecutivo.py` lo importan y comparten; no hay un segundo
   diccionario que mantener.
8. Ejecutar `generar_todos.py` para regenerar memoria/prioridades/panel/informe.

### Flujo obligatorio: PDF corregido a boli hasta memoria y generador

Cuando el usuario entregue una hoja corregida a mano, no basta con archivarla:

1. Conservar el original y validar visualmente trazos negros, corrector blanco y fecha.
2. Transcribir las marcas verificadas en `<pdf>.correcciones.json`; un blanco expl?cito tambi?n es un dato.
3. Crear un PDF oficial limpio y comparar todas sus celdas contra `campo + sidecar`.
4. Incorporarlo con `python _MOTOR_SAGARDE/scripts/regenerar_obra.py <obra_id>` para no reprocesar otras obras.
5. Comparar ficha y PDF mediante IDs normalizados con `Catalogo.resolver()`: los aliases textuales pueden diferir sin que el tajo sea distinto.
6. Confirmar en ficha `rev_DDMMAAAA`, celdas y cambios; en memoria/prioridades/panel, la fecha nueva. Blanco revisado pasa a `P`; fuera de alcance permanece `?`.
7. Comprobar aparte `obras_revisiones.js`: actualizar memoria no actualiza el generador. Usar `generar_todos.py --solo-revisiones` para el registro local o `Actualizar_Sagarde.bat` solo con autorizaci?n de publicaci?n.
8. Reportar recuentos `X`, `M`, `/`, blanco y KPIs antes/despu?s; no cerrar con fechas o recuentos discordantes.

La detecci?n vectorial solo localiza candidatos. La clasificaci?n final de una marca manuscrita o blanca requiere inspecci?n visual.

### Receta: dar de alta una obra nueva (TODOS los formatos desde el alta)

**Regla (04/09/2026): cuando se da de alta una obra nueva, su adaptador debe
aceptar desde el primer día todos los sistemas de recepción de datos y
revisiones que el entorno soporta — JSON simple, PDF y HTML — no solo el que
se vaya a usar primero.** No se onboardea una obra con un solo formato
"de momento": el usuario cambia de formato de campo a oficina, o entre obras,
sin avisar, y un adaptador que solo entiende uno de los tres deja revisiones
reales sin recoger hasta que alguien se dé cuenta. El coste ya no es una
excusa: el soporte HTML genérico (ver receta arriba) es un bloque de 4 líneas
copiado tal cual, sin trabajo específico de la obra.

El motor de lectura de PDF (`lector_hoja_tajos_pdf.py`, en
`_SISTEMA INFORME SAGARDE IA\`) ya es genérico — NO se toca por obra. Lo único
que hay que escribir por obra es un adaptador delgado que le pase 2 funciones
propias. Usar `adaptadores/adaptador_mungia.py` como plantilla y copiar este
patrón (funciones `_portal_id_pdf` y `_parsear_pdf`/`_cargar_historial_pdf`):

1. **Catálogo de tajos de la obra**: dict `TAJO_LABELS_PDF` (alias corto →
   nombre tal cual aparece impreso en la hoja) + `TAJO_NOMBRE_CATALOGO`
   (alias corto → nombre EXACTO del alias en `CATALOGO_TAJOS.json`, para que
   el priorizador clasifique el tajo). Puede haber tajos comunes con otras
   obras (electricidad/teleco básica se repite), pero hay que confirmar caso
   a caso — no asumir que el catálogo de Mungia vale sin mirar la hoja real.
2. **`identificar_portal(texto_banner)`**: función que reconoce el
   portal/edificio a partir de la cabecera de cada tabla. En Mungia busca
   `ZR(\d)\.(\d)`; otra obra imprimirá su propio identificador de portal
   (`PORTAL 1`, `BLOQUE A`, ...) y necesita su propio regex/mapeo.
3. **`identificar_tajo(etiqueta_fila)`**: resuelve la etiqueta impresa de
   cada fila al alias corto interno (normalizando acentos/mayúsculas y
   prefijos `SGD/EXT/COO`, igual que `_identificar_tajo_pdf` de Mungia).
4. Llamar a `lector_hoja_tajos_pdf.listar_revisiones_pdf(carpeta, contiene=<PALABRA_OBRA>)`
   para encontrar los ficheros, y `lector_hoja_tajos_pdf.parsear_pdf(ruta, identificar_portal, identificar_tajo)`
   para extraer cada uno — devuelve `{(portal_id, planta_id, tajo_id, viv): estado}`.
   El adaptador solo traduce esos ids a `building`/`floor`/`task`/`unit` con
   sus propios mapas de nombres.
5. **Antes de dar el parser por bueno**: validar contra una transcripción
   manual de al menos una hoja real completa (así se hizo con Mungia: 2318
   celdas comprobadas una a una). No asumir que el layout es idéntico sin
   verificarlo — columnas corridas, cabeceras partidas o el patrón "PORTAL"
   de una sola vivienda pueden variar página a página.
6. Revisar si hace falta alguna normalización histórica como
   `_normalizar_zr12_pb` (punto 6 del protocolo arriba) al fusionar con
   revisiones antiguas de esa obra.
7. Dar de alta la obra en el registro único (punto 7 del protocolo arriba).
8. **Añadir también soporte HTML genérico**, aunque la obra no vaya a recibir
   HTML de inmediato: copiar el bloque `_cargar_historial_html()` y su fusión
   en `cargar_historial()` (precedencia HTML > PDF > Word) tal cual de
   `adaptador_mungia.py`/`adaptador_bolueta.py`/`adaptador_gorliz.py`, solo
   cambiando `obra_id` y `contiene=<PALABRA_OBRA>` — ver "Receta (recomendada
   desde 04/09/2026): HTML genérico" arriba. Es inofensivo aunque la carpeta
   `REVISIONES` no exista todavía: la función devuelve `[]` sin romper nada.

### Protocolo: cuándo un HTML de hoja de tajos es una revisión oficial válida

Añadido 25/07/2026 (caso real: Gernika). La app de generación de tajos (la
misma que alimenta `obras_revisiones.js`) permite exportar/guardar la hoja ya
rellena como `.html`, con el estado de cada celda embebido en atributos
`data-k`/`data-st` (no en JS runtime — se puede leer con texto/regex sin
ejecutar nada). Antes de aceptar uno de estos ficheros como revisión oficial:

1. **Nombre**: debe llevar una fecha `DDMMAAAA` reconocible en el nombre
   (cualquier prefijo vale, ej. `REVISION {OBRA} DDMMAAAA (1).html`). Sin
   fecha, `lector_hoja_tajos_html.listar_revisiones_html` lo ignora.
2. **Ubicación**: carpeta `REVISIONES` de la obra.
3. **No confundir con plantillas en blanco**: la misma app también deja en
   esa carpeta ficheros `.html` plantilla (todo `data-st=""`, ids de sesión
   tipo `p_xxxxx_1__f_xxxxx_2__tabicado__A`, NO el esquema
   `src_{obra}_pN__..._fM`) o ficheros con placeholders JS sin renderizar
   (`data-k="${k}"`). El lector exige un mínimo de registros reales
   decodificados (`minimo_registros`, por defecto 20) para descartarlos.
4. **ids de portal/planta largos**: usan el esquema `src_{obra}_p{n}` /
   `_f{m}` que asigna `crear_registro_revision()` (generar_todos.py) al
   publicar `obras_revisiones.js` — NO son los ids cortos del adaptador
   (`p1`/`pb`). Cada adaptador fija su propia tabla `PORTAL_NOMBRE_HTML`/
   `PLANTA_NOMBRE_HTML` reproduciendo ese orden (portales/plantas en orden
   natural, PB primero) — ver `adaptador_gernika.py` como ejemplo. Si la obra
   gana o pierde un edificio/planta, hay que revisar y regenerar esta tabla.
5. **tarea_id mixto**: la mayoría de tarea_id en el HTML son ids de
   `CATALOGO_TAJOS.json` (formato `snake_case`), pero unos pocos tajos usan
   códigos cortos "legacy" (`suelo-rad`, `techos-zzcc`, `pint-zzcc`
   confirmados hasta ahora) que NO están en el catálogo. Cada adaptador debe
   mantener su propio `TAREA_ID_A_NOMBRE_HTML` (id → nombre principal o alias
   EXACTO del catálogo) para no romper continuidad en el priorizador. Desde
   el motor 4.3, `Catalogo.resolver()` registra tanto `"nombre"` como los
   alias confirmados; validar igualmente cada id antes de aceptarlo.
6. **Comparar ubicaciones contra el historial anterior** (mismo criterio que
   el punto 6 del protocolo PDF) antes de aceptarlo como oficial.
7. Dar de alta la obra en el registro único si es la primera vez (punto 7).

**Nota (04/09/2026)**: los puntos 4 y 5 de arriba (tablas propias
`PORTAL_NOMBRE_HTML`/`PLANTA_NOMBRE_HTML`/`TAREA_ID_A_NOMBRE_HTML` por obra)
describen el método ANTIGUO, usado por `adaptador_gernika.py` vía
`lector_hoja_tajos_html.py`. Se mantiene tal cual porque ya está verificado y
en producción, pero **ya no es el método recomendado para obras nuevas ni
para tocar un adaptador por otro motivo** — ver la receta genérica siguiente,
que evita escribir esas tablas.

### Receta (recomendada desde 04/09/2026): HTML genérico para cualquier obra

El HTML exportado por la propia app de tajos es, de los tres formatos, el más
sencillo de traducir (lo genera el propio entorno, sin marcas manuscritas que
interpretar) y es previsiblemente el más usado a partir de ahora. Por eso
existe un lector genérico, `adaptar_revision_html.cargar_historial_html_generico()`
(`_SISTEMA INFORME SAGARDE IA\adaptar_revision_html.py`), que **no necesita
ninguna tabla propia por obra**: deriva portal/planta directamente de la
`estructura` que ya tiene `ficha_obra.json` (cruzando dos órdenes
independientes — natural y de estructura — y solo acepta el mapeo cuando es
inequívoco), resuelve alias de vivienda con el `alias_historico` de la propia
ficha, y resuelve tarea_id contra `CATALOGO_TAJOS.json`. Si una posición no
se puede traducir sin ambigüedad, esa clave queda fuera del historial (avisada
por consola) en vez de adivinarla.

Añadir soporte HTML a un adaptador (nuevo o existente) es un bloque de 4
líneas más una fusión, sin nada específico de la obra. Copiar tal cual de
`adaptador_mungia.py`, `adaptador_bolueta.py` o `adaptador_gorliz.py`:

```python
def _cargar_historial_html():
    try:
        ficha_actual = _fichas.cargar(CARPETA_OBRA)
    except Exception as e:
        print("AVISO: no se pudo cargar ficha_obra.json ({}); se ignoran los HTML.".format(e))
        return []
    try:
        catalogo = _vr.cargar_catalogo_tajos()
    except Exception as e:
        print("AVISO: no se pudo cargar CATALOGO_TAJOS.json ({}); se ignoran los HTML.".format(e))
        return []
    return adaptar_revision_html.cargar_historial_html_generico(
        '<obra_id>', CARPETA_REVISIONES, ficha_actual, catalogo,
        contiene='<PALABRA_OBRA>', nombre_log='adaptador_<obra_id>',
    )
```

Y fusionar su resultado dentro de `cargar_historial()` con el resto de
formatos que tenga la obra, dando prioridad **HTML > PDF > Word** en caso de
coincidir la misma fecha (el HTML es el más fiable de los tres al no llevar
transcripción manual).

Requisitos para que un adaptador pueda llamarlo: `import adaptar_revision_html`,
`import ficha_obra as _fichas`, `import validar_revision as _vr` (con
`sys.path` apuntando a `_SISTEMA INFORME SAGARDE IA\`), y una constante
`CARPETA_REVISIONES` (`os.path.join(CARPETA_OBRA, "REVISIONES")`). Si la obra
todavía no tiene `ficha_obra.json` o no tiene carpeta `REVISIONES`, la función
devuelve `[]` sin romper nada — es seguro añadirlo aunque la obra no reciba
HTML todavía (caso Gorliz, 04/09/2026).

Validado en producción (04/09/2026) en Mungia (2356 celdas, salvaguarda de
doble cálculo coincidente) y Bolueta (3686 celdas, coincidente). `adaptador_gernika.py`
se deja con el método antiguo por no incurrir en riesgo de regresión sin
necesidad, no porque el método antiguo siga siendo el recomendado.

## Rutas clave

| Qué | Ruta |
|-----|------|
| Raíz proyecto | `D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE\` |
| Obras abiertas | `SAGARDE OBRAS ABIERTAS\` |
| Sistema IA | `SAGARDE OBRAS ABIERTAS\_SISTEMA INFORME SAGARDE IA\` |
| Adaptadores | `_SISTEMA INFORME SAGARDE IA\adaptadores\` |
| Motor lectura PDF (genérico) | `_SISTEMA INFORME SAGARDE IA\lector_hoja_tajos_pdf.py` |
| Motor lectura HTML tajos (genérico) | `_SISTEMA INFORME SAGARDE IA\lector_hoja_tajos_html.py` |
| Motor | `_MOTOR_SAGARDE\` (este directorio) |
| Memoria vigente | `_SISTEMA\docs\2026-07-28-memoria-diccionario-tajos-alertas-informes.md` |
| Centro de Mando URL | https://bixente-69.github.io/centro-mando-sagarde/ |

## Reglas de trabajo

1. **Cuidado al parsear HTML de revisión**: la mayoría de exports antiguos de la app generan las celdas `data-k`/`data-st` en runtime JS (no están en el HTML fuente) — para esos, usar el JSON companion. Pero desde 25/07/2026 la app también puede guardar el HTML YA renderizado con los valores embebidos de verdad (confirmado con Gernika) — en ese caso sí se puede leer con `lector_hoja_tajos_html.py` (regex sobre texto, sin ejecutar JS). Antes de asumir uno u otro, comprobar con `grep -o 'data-k="[^"]*"'`: si aparecen placeholders tipo `${k}` o `${esc(k)}`, es el caso viejo (usar JSON); si aparecen claves reales (`src_...` o `pN__...`), es el caso nuevo (usar el lector HTML).
2. **TAJO_NOMBRE debe ser exacto** — usar el nombre principal o un alias
   confirmado del catálogo. No se usa similitud. Desde el motor 4.3 ambos
   resuelven al mismo id. Ver `.claude/agents/sagarde-revision.md`.
3. **Después de crear/modificar una revisión (JSON o PDF)**, siempre correr `generar_todos.py --no-pdf` + `sagarde_portal.py` para refrescar datos locales. Ver "Protocolo: cuándo un PDF es una revisión oficial válida" arriba antes de dar por buena una revisión en PDF.
4. **Para publicar en GitHub Pages**, el usuario ejecuta `Actualizar_Sagarde.bat` — no hacer push directamente.
5. **panel.html en INFORME SAGARDE IA** se sobreescribe con cada ejecución de `generar_todos.py`. Es normal.
6. **Dar de alta una obra nueva (adaptador) en el registro único**: editar `_SISTEMA INFORME SAGARDE IA/registro_obras.py`; panel e informe ejecutivo lo comparten — ver protocolo arriba, punto 7.
7. **SCORE (motor_informes.py) y ESTADO_VALOR (priorizador_trabajos.py) deben tener siempre los mismos valores** para cada estado (unificados el 25/07/2026, ambos M=0.60). Si se cambia uno, cambiar el otro.
8. **Caducidad de avisos por antigüedad**: los avisos siguen visibles hasta 399 días y desaparecen al cumplir 400. No se elimina la obra o contrato; solo deja de figurar como aviso accionable. La regla compartida vive en `_MOTOR_SAGARDE/avisos.py`.
9. **Alta de obra nueva = todos los formatos desde el primer día** (JSON, PDF y HTML), no solo el que se vaya a usar primero — ver "Receta: dar de alta una obra nueva" arriba, punto 8.
10. **HTML nuevo en un adaptador existente**: usar siempre `adaptar_revision_html.cargar_historial_html_generico()` (ver receta arriba), no copiar el patrón de tablas por obra de `adaptador_gernika.py` salvo que ya se esté tocando ese adaptador por otro motivo.

## Estructura estándar de obra (ejemplo Gernika)

```
2025 GERNIKA 32V\
  INFORME SAGARDE IA\
    panel.html
    revision_gernika_22072026.json   ← estados de cada tajo
    dudas_pendientes.json
    prioridades_trabajos.json
  REVISIONES\
    REVISON GERNIKA 32VIV TYPO.html  ← plantilla vacía del generador
    REVISION GERNIKA 22072026.html   ← hoja pre-rellenada interactiva
```

## Formato clave JSON de revisión

```json
{
  "fecha": "22/07/2026",
  "estados": {
    "p1__pb__mecanizado__A": "X",
    "p1__pb__pint-2__A": "",
    "p2__3__embornado__D": "M"
  }
}
```
Estados: `X`=terminado, `M`=en marcha >50%, `/`=iniciado <50%, `""`=pendiente. Los `N` se excluyen del JSON.

## Contexto de negocio (para generar ideas/propuestas)

Lo usa y mantiene una sola persona (Bixente, gestor/técnico), sin otros usuarios internos ni externos por ahora.

El volumen de obras abiertas, contratos de post-venta y mantenimientos es variable según la carga de trabajo en cada momento — no hay un número fijo de referencia. El avance de cada obra se actualiza manualmente desde campo u oficina, sin automatización de captura de datos.

Al proponer ideas para este proyecto, priorizar dos tipos:
1. Mejoras técnicas del sistema (motor, scripts, portal, panel, generación de datos).
2. Mejoras del proceso de obra en el día a día (seguimiento de avance, incidencias, mantenimientos), no solo del código.

No proponer ideas de negocio, crecimiento comercial o nuevos servicios — fuera de alcance.

No hay prioridad entre obras/post-ventas/mantenimientos: tratar como un sistema conjunto.

Carencias conocidas a explorar: alertas o avisos automáticos (obras paradas, incidencias sin resolver, plazos próximos) e informes/reportes generados automáticamente. Fuera de eso, no hay problemas identificados todavía — abierto a propuestas nuevas sin partir de una lista cerrada de quejas.
