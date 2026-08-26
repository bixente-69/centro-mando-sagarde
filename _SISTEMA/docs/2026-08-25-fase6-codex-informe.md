# Informe de implementación — Fase 6 de unificación de revisiones

Fecha de cierre: 26/08/2026.

## Alcance completado

Se ha implementado el tercer adaptador como código nuevo y aislado. Los únicos
ficheros creados en esta fase son:

- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/adaptar_revision_tinta.py`;
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_adaptar_revision_tinta.py`;
- `_SISTEMA/docs/2026-08-25-fase6-codex-informe.md` (este informe).

No se ha modificado ningún fichero anterior, no se ha conectado el adaptador a
`leer_hoja_marcada.py`, `generar_todos.py` ni a otro adaptador, y no se ha
tocado `_SISTEMA/MOTOR/`. El adaptador solo lee; no contiene ninguna operación
de persistencia.

## Contrato respetado: el adaptador empieza después de la visión

`construir_revision_normalizada_tinta(ruta_pdf, ruta_clasificacion, obra_id,
ficha_actual, fecha, sin_marca='pendiente')` no intenta reconocer el PDF ni
llama a `preparar()`. Exige los mismos dos artefactos que ya consume la segunda
fase del flujo A:

1. `<hoja>.candidatas.json`, producido por la geometría de
   `rejilla_hoja.py` a través de `preparar()`;
2. `<hoja>.clasificacion.json`, ya rellenado por una persona o por visión con
   una letra por clave.

El sidecar de candidatas se busca primero en `REVISIONES/_SISTEMA/`, que es la
ubicación vigente, y como compatibilidad de lectura también junto al PDF, que
era la ubicación anterior. La búsqueda no crea directorios.

La clasificación se lee con el mismo contrato que el CLI: admite el objeto
`{"celdas": {...}}` o directamente el mapa. Después se llama directamente a
`leer_hoja_marcada.aplicar()`. Por tanto, siguen perteneciendo a una única
implementación histórica estas guardas:

- ninguna candidata puede quedar sin clasificar;
- ninguna clasificación puede introducir una clave sin tinta;
- solo se admiten `X`, `M`, `/`, `P` y `descartada`;
- la clave tiene que existir ya en `ficha_actual['estados']`;
- una marca explícita manda aunque sea un retroceso.

Para `sin_marca='pendiente'` se llama también directamente a
`leer_hoja_marcada.marcar_no_empezados()` sobre la copia devuelta por
`aplicar()`. Para `desconocido` no se hace ese barrido. El adaptador no muta la
ficha recibida.

Una precisión encontrada al leer el código completo: aunque cada candidata
guarda un campo `antes`, `aplicar()` no lo consulta para decidir. Consulta el
estado actual de la ficha pasada como argumento. El adaptador conserva
exactamente ese comportamiento, sin inventar una comparación distinta.

## Traducción a la revisión normalizada

- `origen` es `tinta` y la fecha es obligatoria. Si falta, se produce
  `ValueError`; nunca se infiere del nombre ni de la cabecera del PDF.
- Toda clasificación real no descartada se conserva como `REVISION_CELDA`,
  incluso si al compararla con la ficha resulta ser el mismo estado. Esto
  conserva la medición, igual que los adaptadores HTML y PDF conservan sus
  lecturas aunque la acción posterior sea `conservar`.
- Los únicos blancos añadidos por `sin_marca='pendiente'` son los que la
  función histórica identifica como cambios `? -> P`. No se vuelve a
  implementar esa decisión.
- Una clave clasificada como `descartada` no genera `REVISION_CELDA`.
- `metadata.hoja_usada` solo es `true` si la clasificación contiene al menos
  una marca real no vacía y distinta de `descartada`.
- Los avisos de columnas sin mapear del sidecar se propagan a
  `metadata.avisos`.

### Confianza

Los dos `.clasificacion.json` reales inspeccionados usan exclusivamente el
formato publicado `clave -> string`; no tienen campo de confianza ni una forma
de marcar explícitamente una celda como dudosa. El concepto sí existe en el
paso anterior: cada candidata tiene `dudosa: bool`. Esa señal significa «debe
resolverla la clasificación», no «la respuesta final conserva duda».

En Bolueta había 3 candidatas previas dudosas y en Mungia 29; las 32 terminaron
como `descartada`. No se encontró una marca real clasificada con un campo de
confianza explícito. Por ello, toda celda no descartada sale con
`confianza='cierta'`, incluida una candidata inicialmente dudosa que el humano
o la visión ya resolvió. No se ha inventado una extensión del formato.

## Decisión de `revision_id`

Se eligió el formato habitual
`{obra}__{fecha}__tinta__{hash8}`, pero el SHA-256 no cubre solo el PDF. Incluye,
con separación de dominio:

- bytes del PDF;
- bytes de `.candidatas.json`;
- bytes de `.clasificacion.json`;
- valor de `sin_marca`.

La clasificación es una entrada humana independiente: dos letras distintas
sobre el mismo PDF no pueden compartir id. Las candidatas también importan,
porque fijan las claves geométricas y el alcance de `celdas_hoja`; y el modo
`sin_marca` puede cambiar el resultado sin cambiar ningún fichero. El test
específico comprueba repetibilidad y que modificar la clasificación o el modo
cambia el identificador.

## Pruebas de paridad

Se añadieron 14 tests, reconstruyendo las ramas de tinta de
`TestNadaSeDescartaSolo`, `TestSinTintaNoHayCambio` y `TestNormaDeObra`.
Cada comparación ejecuta primero el código antiguo y después el adaptador,
`validar()` y `apply_revision(dry_run=False)` exclusivamente sobre fichas y
ficheros temporales sintéticos.

Coinciden exactamente:

- candidata sin clasificar: ambos abortan;
- clave clasificada sin candidata: ambos abortan con «sin tinta no hay
  cambio»;
- valor desconocido: ambos abortan;
- clave estructural ausente de `estados`: ambos abortan;
- descarte explícito, sin barrido de blancos: no cambia la ficha;
- retroceso explícito `X -> M`: se acepta a la primera;
- volver a marcar `X` sobre `X`: se conserva;
- `sin_marca='pendiente'`: un blanco aplicable hace `? -> P`;
- `sin_marca='desconocido'`: el mismo blanco no se toca;
- la ficha recibida no se muta.

Resultado focalizado:

```text
Ran 14 tests in 0.578s
OK
```

### Discrepancias reales, mantenidas visibles

#### 1. Una `P` explícita sobre un estado conocido no cabe en el modelo común

El flujo A histórico admite `P` como clasificación del corrector y
`aplicar()` la trata como marca explícita: puede hacer `M -> P` a la primera.
Sin embargo, `REVISION_CELDA.estado_leido` y `validar_revision.ALFABETO_HOJA`
solo admiten `X`, `M`, `/`, blanco y `N`; `P` es deliberadamente un estado de
ficha. La única traducción formal disponible es `P -> ''`, pero la regla 7 del
validador impide que un blanco baje un estado conocido.

El adaptador traduce `P` a blanco para producir una revisión formalmente
válida y añade un aviso preciso cuando la decisión final va a divergir. Un
test demuestra la diferencia sin `expectedFailure` ni falsa igualdad:

```text
antiguo: M -> P
nuevo:   M -> M (conservar)
```

No es posible corregirla modificando solo este adaptador: antes del cutover
habrá que ampliar el contrato común para representar una `P` explícita, o
proporcionar otra señal inequívoca al validador.

#### 2. `descartada` y el barrido `--sin-marca pendiente`

`aplicar()` descarta la candidata, pero el CLI actual la vuelve a incluir
después entre las casillas sin marca: si estaba en `?`,
`marcar_no_empezados()` la convierte a `P`. Esto contradice literalmente la
restricción de esta fase de que una `descartada` no genere
`REVISION_CELDA`.

El adaptador cumple la restricción: omite esa clave incluso si el barrido
histórico devolvió `? -> P`, y deja un aviso con el número y las primeras
claves omitidas. Otro test conserva visible esta diferencia. No afectó a los
dos casos reales verificados porque sus descartadas no producían transiciones
`? -> P` contra las fichas históricas usadas.

### `antes=None`

La divergencia de Fase 5 no reaparece aquí. El motivo es estructural:
el adaptador llama primero a `aplicar()`, que aborta si la clave no existe en
`estados`, antes de poder construir la revisión normalizada. Un test específico
ejecuta y confirma ambas llamadas abortadas. La guarda antigua queda por tanto
preservada en este adaptador.

## Verificación empírica, estrictamente en lectura

### Ficheros localizados

Bolueta:

- `SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/REVISIONES/REVISION BOLUETA 26072026.pdf`;
- `SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/REVISIONES/_SISTEMA/REVISION BOLUETA 26072026.candidatas.json`;
- `SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/REVISIONES/_SISTEMA/REVISION BOLUETA 26072026.clasificacion.json`;
- `SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/REVISIONES/_SISTEMA/REVISION BOLUETA 26072026.pdf.correcciones.json`.

Mungia:

- `SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/REVISIONES/REVISION MUNGIA 27072026.pdf`;
- `SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/REVISIONES/_SISTEMA/REVISION MUNGIA 27072026.candidatas.json`;
- `SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/REVISIONES/_SISTEMA/REVISION MUNGIA 27072026.clasificacion.json`;
- `SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/REVISIONES/_SISTEMA/REVISION MUNGIA 27072026.pdf.correcciones.json`.

No existe una versión de `ficha_obra.json` anterior a cada PDF: la ficha de
Bolueta se añadió por primera vez el 28/07 en `9a70a5f`, y la de Mungia el
27/07 a las 18:05 en `5c90dec`, después de la hora del PDF. Se usaron esas
primeras fichas disponibles, leídas directamente con `git show` y
deserializadas en memoria. Son las bases contra las que se hizo después la
verificación del lector: Bolueta ya contenía las 7 transcripciones y Mungia
aún contenía los estados anteriores a las 12 correcciones encontradas.

No se hizo checkout, no se llamó a `apply_revision(dry_run=False)` sobre estos
datos y no se escribió ningún fichero de obra. Se construyó la revisión y se
llamó solo a `validar()`; como contraste independiente en memoria también se
ejecutó `leer_hoja_marcada.aplicar()`.

### Bolueta 26/07/2026

```text
candidatas con tinta:       12
marcas reales clasificadas:  7  (3 X, 4 P)
descartadas:                  5
candidatas previas dudosas:   3  (las 3 descartadas)
celdas normalizadas:          7
validar(): aceptadas=7, rechazadas=0, aplicable=True
validar(): actualizar=0, conservar=7
revision_id: bolueta__26/07/2026__tinta__83749431
```

Se reproduce exactamente el recuento conocido: 7 celdas reales y 5 rabos
descartados. El sidecar manual usa aún el id corto `pint-1` y blanco para el
corrector, mientras la preparación posterior usa el id canónico
`pintura_primera` y `P`; son las mismas 7 mediciones semánticas. Contra la
primera ficha histórica todas ya estaban incorporadas, por eso tanto
`aplicar()` como el motor común dan 0 cambios, que coincide con el «cero
cambios» documentado en la skill.

### Mungia 27/07/2026

```text
candidatas con tinta:        225
marcas reales clasificadas:  192  (146 X, 43 M, 3 P)
descartadas:                  33
candidatas previas dudosas:   29  (las 29 descartadas)
celdas normalizadas:         192
validar(): aceptadas=192, rechazadas=0, aplicable=True
aplicar() antiguo:            12 cambios
validar() común:               9 cambios
coincidentes exactos:          9
revision_id: mungia__27/07/2026__tinta__20f1ebfb
```

La versión manual del sidecar anterior a la corrección se recuperó con
`git show 4b00534^:<ruta>`: contenía 213 estados. Tras resolver ids cortos y
aliases hay 179 coincidencias sintácticas con las candidatas; la verificación
humana documentada excluyó dos de esas coincidencias porque estaban colocadas
en la vivienda equivocada, dejando las **177 coincidencias reales** conocidas.
También normalizó las tres claves con `PORT AL` partido.

`aplicar()` encuentra exactamente las 12 correcciones publicadas en el
sidecar actual: mismas 12 claves y valores, sin extras ni ausencias. El motor
común conserva 9. Las tres que faltan son, una por una:

- `p1__pb__casquillos_bombillas__A`: `M -> P`;
- `p1__pb__casquillos_bombillas__B`: `M -> P`;
- `p1__pb__casquillos_bombillas__C`: `M -> P`.

Es la discrepancia de `P` explícita descrita arriba, confirmada ahora con datos
reales. No se forzó la igualdad ni se ocultó el resultado.

## Suite completa

Comando ejecutado desde
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`, con escritura de
bytecode desactivada:

```text
python -m unittest discover -s tests
Ran 538 tests in 36.644s
OK (skipped=4)
```

Son exactamente los 524 tests de la línea base de Fase 5 más los 14 nuevos:
534 pasan, 4 se omiten, 0 fallos y 0 errores. Reaparecieron los dos
`ResourceWarning` históricos de `test_paginacion_generador.py` por ficheros
sin cerrar, sin afectar al resultado.

La suite existente imprimió sus mensajes habituales de generación del informe
ejecutivo de Mungia. La comprobación posterior mostró 0 ficheros rastreados
modificados y el PDF real conservó su fecha de modificación anterior a la
ejecución; no quedó ninguna escritura material de obra.

## Estado para el cutover

El adaptador está implementado, aislado y cubierto, pero la paridad total del
flujo A no está demostrada: el caso real de Mungia deja 3 de 12 correcciones
fuera por la imposibilidad del modelo común de expresar una `P` explícita.
Con la prioridad del proyecto —integridad antes que compatibilidad y
simplicidad— no debe conectarse el flujo A al motor común hasta resolver esa
representación y decidir expresamente la semántica conjunta de
`descartada` con `--sin-marca pendiente`.

## Fase 6b - correccion de P explicita y descartada

Se han corregido los dos huecos anteriores aplicando el criterio fijado para
esta fase: paridad con `leer_hoja_marcada.aplicar()` y
`marcar_no_empezados()`, sin introducir una política nueva.

### Cambios exactos

- `validar_revision.py`: el antiguo `ALFABETO_HOJA` único se ha separado en
  `ALFABETO_HOJA_DIGITAL`, exactamente `{'X', 'M', '/', '', 'N'}`, y
  `ALFABETO_HOJA_TINTA`, que añade `P`. `ALFABETOS_HOJA` selecciona el
  conjunto por `origen` y la regla 5 usa el conjunto seleccionado. Una `P`
  de `tinta` llega por tanto a la rama de marca explícita de la regla 8, usa
  `MAPA_ESTADO['p']` y actualiza o conserva con los mismos motivos que
  `X`/`M`/`/`. En `pdf_digital` y `html_digital`, `P` sigue rechazada por la
  regla 5.
- `adaptar_revision_tinta.py`: se ha eliminado la traducción artificial
  `P -> ''` y el aviso que explicaba aquella divergencia. La `P` clasificada
  se emite ahora literalmente. También se ha eliminado la excepción que
  descartaba los cambios `? -> P` devueltos por el barrido cuando la clave
  estaba clasificada como `descartada`, junto con su aviso de omisión. La
  `descartada` continúa sin emitir una `REVISION_CELDA` directa; solo puede
  aparecer como el blanco derivado por `marcar_no_empezados()`.
- `tests/test_validar_revision.py`: los tests de regla 5 comprueban los tres
  alfabetos por origen, incluida la invalidez de `P` para ambos orígenes
  digitales. La prueba nueva de regla 8 comprueba tanto `M -> P` con acción
  `actualizar` y motivo de marca explícita como `P -> P` con acción
  `conservar`.
- `tests/test_adaptar_revision_tinta.py`: las dos pruebas que antes mantenían
  visibles las discrepancias ahora exigen igualdad completa entre el camino
  antiguo y el común. Se añadió además la regresión empírica de Mungia
  descrita abajo.
- `adaptar_revision_html.py`: al retirar la constante singular, sus tests
  revelaron una dependencia directa en una única línea. Esa consulta usa
  ahora `ALFABETOS_HOJA[ORIGEN]`. No cambia el comportamiento HTML: su
  alfabeto continúa siendo exactamente el digital y no admite `P`. No fue
  necesario modificar `adaptar_revision_pdf_digital.py`.

### Paridad de las dos discrepancias

Las dos pruebas sintéticas comparativas demuestran ahora paridad real:

```text
P explícita:       antiguo M -> P; común M -> P
descartada+barrido: antiguo ? -> P; común ? -> P
```

En el segundo caso la revisión común contiene una celda en blanco producida
por el barrido, no una celda directa producida por la clasificación
`descartada`. No apareció otra discrepancia real durante estas correcciones.

Resultados focalizados finales:

```text
test_validar_revision.py:             Ran 48 tests - OK
test_adaptar_revision_tinta.py:       Ran 15 tests - OK
test_adaptar_revision_pdf_digital.py: Ran  7 tests - OK
test_adaptar_revision_html.py:        Ran  9 tests - OK
```

### Regresión empírica: Mungia 27/07/2026

El nuevo
`test_mungia_27_07_propone_las_12_correcciones_completas` usa en lectura los
mismos PDF, `.candidatas.json`, `.clasificacion.json` y
`.pdf.correcciones.json` detallados en la Fase 6. La ficha «antes» se obtiene
en memoria con:

```text
git show 5c90dec:SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/ficha_obra.json
```

No hace checkout, no llama a `apply_revision()` sobre datos reales y no
escribe ningún fichero. Ejecuta `aplicar()` y `marcar_no_empezados()` sobre
copias en memoria, construye la revisión común y llama únicamente a
`validar()`. El resultado final es:

```text
correcciones publicadas: 12
camino antiguo:          12
motor común:             12
coincidencias exactas:   12
rechazadas:               0
aplicable:             true
```

Las tres `P` explícitas de `casquillos_bombillas` que antes faltaban están
incluidas y coinciden con el sidecar publicado, junto con las otras nueve.

### Suite completa y aislamiento

Comando ejecutado desde
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`, con escritura de
bytecode desactivada:

```text
python -m unittest discover -s tests
Ran 540 tests in 55.870s
OK (skipped=4)
```

La línea base de 538 tests queda superada por las dos regresiones nuevas: 536
pasan, 4 se omiten, 0 fallos y 0 errores. Reaparecieron únicamente los dos
`ResourceWarning` históricos de `test_paginacion_generador.py`.

La suite imprimió los mensajes habituales de generación del informe
ejecutivo de Mungia, pero el PDF real mantuvo la fecha de modificación
`25/08/2026 19:40:24`, anterior a la ejecución, y Git no mostró cambios en
datos de obra. El motor común y los adaptadores continúan aislados; esta Fase
6b no conecta nada a producción.
