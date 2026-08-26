# Informe de implementación — Fase 4 de unificación de revisiones

Fecha: 25/08/2026.

## Hallazgos obligatorios previos a la implementación

### 1. Procedencia exacta de los cuatro segmentos de `data-k`

La celda se construye literalmente como
``${portal.id}__${planta.id}__${t.id}__${viv}`` y ese mismo valor se imprime en
`data-k`; el estado precargado solo se consulta después mediante esa clave
(`generador_revisiones.html:1074-1080`). Por tanto, al imprimir no existe una
llamada a `BASE_SOURCE_ID` ni otra traducción oculta.

El tercer segmento depende del origen de la configuración:

- En modo manual, `CAT` es el catálogo base cuyos ids son cortos, por ejemplo
  `mont-elec` (`generador_revisiones.html:360-399`), y al volver a modo manual
  se restaura directamente `BASE_CAT` (`generador_revisiones.html:609-612`).
- Al cargar una obra publicada se ejecuta `CAT=catalogForSource(source)`
  (`generador_revisiones.html:625-629`). Esa función conserva sin modificar los
  ids de `source.catalog`; solo usa `BASE_SOURCE_ID` para saber qué tareas base
  faltan y añade las ausentes todavía con el id corto de `BASE_CAT`
  (`generador_revisiones.html:401-418`).

Conclusión: un HTML importado desde `obras_revisiones.js` puede mezclar ids
largos del catálogo fuente con ids cortos de tareas base ausentes; un HTML
configurado desde cero usa los ids cortos. `BASE_SOURCE_ID` no transforma el
id en el momento de generar `data-k`.

### 2. Relación entre Gernika, `BASE_SOURCE_ID` y el catálogo real

`TAREA_ID_A_NOMBRE_HTML` de Gernika usa mayoritariamente los ids largos reales,
por ejemplo `montante_electrica`, `tubeado` y `pintura_primera`, pero conserva
tres ids cortos observados en su HTML: `suelo-rad`, `pint-zzcc` y
`techos-zzcc` (`adaptadores/adaptador_gernika.py:113-152`). Los dos últimos
están documentados como altas del 25/07/2026 que antes no existían en el
vocabulario de la obra (`adaptadores/adaptador_gernika.py:86-90`).

No son ids reales de `CATALOGO_TAJOS.json`: allí figuran
`suelo_radiante`, `techos_zzcc` y `pintura_zzcc`
(`reglas/CATALOGO_TAJOS.json:174`, `:522`, `:784`). La relación es exacta y
derivable sin comparar textos: el propio `BASE_SOURCE_ID` declara
`suelo-rad -> suelo_radiante`, `techos-zzcc -> techos_zzcc` y
`pint-zzcc -> pintura_zzcc` (`generador_revisiones.html:404`, `:408`, `:410`).
Los ids que ya coinciden con el catálogo se resuelven por identidad.

Conclusión: no hace falta un diccionario por obra ni una heurística por
nombres. Hace falta una traducción global exacta del catálogo corto del
generador y conservar explícitamente las dos excepciones históricas señaladas
por Gernika.

### 3. Numeración de portal/planta y orden usado por el navegador

`_clave_natural` separa las partes numéricas y las compara como enteros
(`generar_todos.py:48-50`). `_clave_planta` ordena primero plantas numéricas
negativas, después PB/B/bajo, luego plantas numéricas no negativas y al final
otros textos con `_clave_natural` (`generar_todos.py:53-61`).

En `crear_registro_revision` el algoritmo exacto es:

1. edificios únicos ordenados con `_clave_natural`;
2. enumeración desde 1 como `src_{slug}_p{n}`;
3. dentro de cada edificio, plantas ordenadas con `_clave_planta`;
4. enumeración desde 1 como `{portal_id}_f{m}`;
5. viviendas ordenadas con `_clave_natural`
   (`generar_todos.py:400-415`).

El navegador no repite ese orden ni renumera. `normaliseStructure` recorre los
bloques, portales y plantas en el orden recibido y conserva cada `id`
(`generador_revisiones.html:498-522`); al cargar una obra asigna esa estructura
a `S.bloques` (`generador_revisiones.html:625-629`) y `data-k` usa esos ids
literales (`generador_revisiones.html:1074-1080`). Para una fuente producida
por `crear_registro_revision`, el resultado es por ello idéntico: el navegador
preserva los ids ya numerados por Python.

Hay dos límites reales a esa automatización universal:

- una configuración manual crea ids temporales con `uid()` y no ids `src_*`
  (`generador_revisiones.html:481-493`);
- el publicador actual `registro_revision_desde_ficha` numera portales y
  plantas según el orden almacenado en `ficha_actual['estructura']`, sin los
  dos `sorted` anteriores (`generar_todos.py:270-278`).

Por tanto, con solo un HTML antiguo y la ficha actual no siempre se puede saber
cuál de los dos productores de `src_*` se usó. Elegir uno a ciegas podría
asignar una marca válida a otra planta o portal también válido.

## Decisión de alcance

Se implementó una automatización conservadora:

- Para portal y planta se derivan dos mapas: el de orden natural de
  `crear_registro_revision`, reutilizando por importación `_clave_natural`,
  `_clave_planta` y `_slug`, y el de orden estructural de
  `registro_revision_desde_ficha`. Una posición se resuelve automáticamente
  cuando ambos caminos producen el mismo destino o solo uno puede producirla.
  Si producen destinos distintos, no se elige ninguno: la clave queda en
  avisos y el llamador puede aportar `portal_id_a_real` y
  `planta_id_a_real` explícitos.
- Para tareas se acepta por identidad cualquier id real válido del catálogo y
  se aplica la relación exacta global de `BASE_SOURCE_ID`. No se comparan
  nombres, aliases ni similitud textual. `techos-zzcc` y `pint-zzcc` viven en
  una tabla de excepciones histórica separada y comentada.
- Las viviendas impresas se resuelven contra la planta real y contra
  `estructura.alias_historico`, para recuperar el id canónico sin perder el
  case de la vivienda.

Así se generaliza automáticamente el caso normal y se mantiene manual y
explícito el caso que el código existente no permite desambiguar.

## Implementación

Se creó
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/adaptar_revision_html.py`.

La función principal
`construir_revision_normalizada_html(ruta_html, obra_id, ficha_actual,
catalogo, ...)` (`adaptar_revision_html.py:261-359`):

- llama a `lector_hoja_tajos_html.extraer_pares()` para leer los atributos, sin
  reimplementar la regex (`adaptar_revision_html.py:290-291`);
- deriva las ubicaciones de forma segura en `derivar_mapas_ubicacion()`
  (`adaptar_revision_html.py:180-196`);
- deriva tareas por ids exactos en `derivar_mapa_tareas()`
  (`adaptar_revision_html.py:198-211`);
- conserva `X`, `M`, `/`, blanco y `N` como alfabeto de hoja y crea una
  `REVISION_CELDA` cierta por cada par válido traducido;
- omite solo las claves no traducibles o mal formadas y conserva cada caso en
  `metadata.avisos`, sin bloquear las demás;
- extrae la fecha llamando al mismo `_fecha_desde_nombre()` que usa
  `listar_revisiones_html`, sin duplicar el patrón DDMMAAAA
  (`adaptar_revision_html.py:246-255`);
- reutiliza `validar_revision.generar_revision_id()` sobre el contenido del
  HTML (`adaptar_revision_html.py:343-344`);
- fija `origen='html_digital'` y `metadata.hoja_usada=true`
  (`adaptar_revision_html.py:343-357`).

El módulo permanece aislado: no se conectó a `generar_todos.py`, a los
adaptadores existentes ni a `leer_hoja_marcada.py`; no persiste datos.

## Pruebas

Se creó
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_adaptar_revision_html.py`
con 9 tests sintéticos. Cubren traducción de ids largos y cortos, conservación
del case de vivienda, aliases históricos, claves sin resolver como avisos sin
abortar, `N`, fecha DDMMAAAA, ausencia de fecha, `revision_id` determinista y
el rechazo seguro de un orden ambiguo con resolución mediante mapa explícito
(`test_adaptar_revision_html.py:59-199`).

Resultado focalizado:

```text
Ran 9 tests in 0.418s
OK
```

También pasó la compilación de ambos ficheros con `py_compile`.

Resultado de la suite completa desde
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`:

```text
python -m unittest discover -s tests
Ran 517 tests in 30.021s
OK (skipped=4)
```

Son los 508 tests de la línea base de Fase 3b más los 9 nuevos: 513 pasan,
4 se omiten, 0 fallos y 0 errores. Se repitieron los dos `ResourceWarning`
históricos de `test_paginacion_generador.py` por ficheros no cerrados.

Como comprobación adicional de generalización, siempre en lectura y sobre las
fichas actuales, el adaptador tradujo Gernika (1.216 celdas) y Mungia (2.356
celdas) con 0 avisos y 0 rechazos en ambos casos. No se aplicó ninguna revisión.

## Verificación empírica de Bolueta 24/08/2026

Se encontraron los dos gemelos reales:

- `SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/REVISIONES/REVISION 2026 BOLUETA ACR 24082026.pdf`;
- `SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/REVISIONES/REVISION 2026 BOLUETA ACR 24082026.html`.

El último commit anterior a la hora del HTML que contiene una ficha de Bolueta
sin la revisión del 24/08 es `a616f91`, creado el 24/08/2026 a las 08:42. El
HTML tiene hora 11:41 y la revisión aparece por primera vez en la ficha del
commit `c400209`, de las 15:58. La ficha previa se leyó directamente con
`git show a616f91:<ruta>` y se mantuvo solo en memoria; no se hizo checkout ni
se escribió ningún fichero de obra.

Resultado sobre esa ficha previa:

```text
revision_id: bolueta__24/08/2026__html_digital__4e987c08
pares/celdas traducidas: 3686
avisos de traducción: 0
validar(): aplicable=True, aceptadas=3686, rechazadas=0
validar(): cambios=443, sin_cambio=3243, descartadas=0
apply_revision(dry_run=True): escrito=False, aplicable=True, cambios=443
```

No se ejecutó `dry_run=False` ni se construyó o persistió una ficha real.

### Comparación con las 411 celdas documentadas

El camino HTML propone 443 diferencias frente a la ficha de las 08:42, 32 más
que las 411 documentadas. La discrepancia se pudo aislar sin inferencias de
geometría usando las versiones históricas de los sidecars y de la ficha:

- el sidecar de `c400209` contiene las 245 celdas de la primera pasada;
- el sidecar reemplazado en `8ef317b` contiene las 166 recuperadas tras
  corregir el agrupamiento de columnas;
- ambos conjuntos son disjuntos y suman 411;
- las 411 claves están entre las 443 propuestas por el HTML y sus valores
  coinciden: 411 coincidencias, 0 claves documentadas ausentes y 0 valores
  discrepantes;
- quedan 32 claves adicionales del HTML: 16 de `doblar_cajas`, 12 de
  `pintura_zzcc` y 4 de `perfilado_pladur`. Son 16 `P->X`, 14 `P->M` y
  2 `P->/`.

La historia de la ficha explica esas 32: entre `a616f91` y `c400209` cambian
277 estados, exactamente las 245 del primer sidecar más esas 32; entre
`c400209` y `8ef317b` cambian exactamente las otras 166. La exportación HTML
solo conserva el estado final de cada `data-st`, no distingue qué valores
venían precargados al abrir la app de cuáles se pulsaron durante esa revisión.
La explicación compatible con toda la evidencia es que esas 32 ya llegaron
precargadas desde el otro productor de estado y no formaban parte del recuento
manual de 411 avances de esa sesión. Esto no es un fallo de traducción: el
adaptador recupera íntegramente las 411 conocidas y además expone la divergencia
de 32 que existía entre las fuentes de verdad previas.

## Alcance de escritura

Solo se crearon los tres ficheros autorizados de esta fase:

- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/adaptar_revision_html.py`;
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_adaptar_revision_html.py`;
- `_SISTEMA/docs/2026-08-25-fase4-codex-informe.md`.

No se modificó ningún fichero existente, nada bajo `_SISTEMA/MOTOR/` ni
ninguna ficha o carpeta de una obra real.
