# Fase 9 — trazabilidad unificada de revisiones

Fecha de ejecución: 26/08/2026.

## Resultado

Se añadió un log común, mínimo y aditivo por obra:

`{carpeta_obra}/INFORME SAGARDE IA/revisiones_aplicadas.jsonl`

Los cuatro orígenes que ya cruzaban el motor común (`tinta`,
`pdf_digital`, `html_digital` e `historial_consolidado`) registran ahora la
misma forma de entrada cuando, y solo cuando, la ficha real ya se ha guardado
después de superar la salvaguarda de doble cálculo. No se modificaron el
formato de los sidecars ni `ficha['revisiones']`. Tampoco se tocaron
`validar_revision.py`, `aplicar_revision.py` ni `_SISTEMA/MOTOR/`.

## Trazabilidad que existía antes de esta fase

### Base compartida en memoria y por celda

La revisión normalizada ya exigía en memoria `revision_id`, obra, fecha,
origen, fuente y metadata; dentro de metadata exigía `generado_por` y
`generado_en` (`validar_revision.py:37-40,91-109,142-156`). El validador ya
calculaba el resumen común `cambios`, `sin_cambio`, `descartadas` y
`rechazadas` (`validar_revision.py:247-258`). Esos datos no constituían aún un
registro persistente común.

El motor común solo persistía en cada celda realmente cambiada `v`, `f`
(fecha) y `r` (`revision_id`) (`aplicar_revision.py:35-42`). Por tanto, una
revisión sin cambios no dejaba rastro en `estados`, y las celdas no guardaban
el origen, la fuente ni quién construyó la revisión.

### Tinta por el CLI

El adaptador producía en memoria `origen='tinta'` y
`generado_por='adaptar_revision_tinta.construir_revision_normalizada_tinta'`
(`adaptar_revision_tinta.py:24-28,178-198`). Al escribir de verdad, el CLI
dejaba dos rastros adicionales:

- Sidecar `.correcciones.json`: `version`, hoja, obra, fecha,
  `revision` (el `revision_id` normalizado), un texto de origen, `estados`
  como mapa de las celdas cambiadas a su valor nuevo y `descartadas`
  (`leer_hoja_marcada.py:923-931`). No guardaba `generado_por`, la fuente
  normalizada ni los conteos de celdas conservadas.
- `ficha_nueva['revisiones']`: id, fecha, texto de origen,
  `celdas_medidas` y `celdas_cambiadas`
  (`leer_hoja_marcada.py:933-946`). Tampoco guardaba `generado_por`, fuente,
  conservadas o descartadas.

La escritura real de la ficha estaba en `leer_hoja_marcada.py:947`, después
de la salvaguarda de `leer_hoja_marcada.py:905-907`.

### PDF digital y HTML digital por el CLI

Los dos formatos entraban por la misma rama del CLI, aunque los adaptadores
sí los distinguían correctamente en memoria:

- PDF: `origen='pdf_digital'` y
  `generado_por='adaptar_revision_pdf_digital.construir_revision_normalizada_pdf_digital'`
  (`adaptar_revision_pdf_digital.py:16-20,59-74`).
- HTML: `origen='html_digital'` y
  `generado_por='adaptar_revision_html.construir_revision_normalizada_html'`
  (`adaptar_revision_html.py:27-28,348-364`).

La persistencia previa era parcialmente común y perdía esa distinción
explícita:

- Sidecar `.correcciones.json`: version, hoja, obra, fecha,
  `revision`, el texto genérico de origen digital y el mapa `estados` de las
  celdas cambiadas (`leer_hoja_marcada.py:784-792`).
- `ficha_nueva['revisiones']`: id, fecha, texto genérico de origen,
  `celdas_medidas` y `celdas_cambiadas`
  (`leer_hoja_marcada.py:794-801`).

Ni el sidecar ni la entrada de ficha persistían `generado_por`, fuente,
conservadas o descartadas. La escritura real de la ficha estaba en
`leer_hoja_marcada.py:802`, después de la salvaguarda de
`leer_hoja_marcada.py:772-774`.

### Historial consolidado por `generar_todos.py`

Este camino ya construía en memoria un `revision_id` determinista, obra,
fecha, `origen='historial_consolidado'`, una fuente descriptiva del adaptador
y `generado_por='generar_todos.construir_revision_normalizada_desde_snapshot'`
(`generar_todos.py:947-965`). La salvaguarda conservaba también en memoria la
revisión, validación, aplicación, número de claves comparadas y si coincidían
los dos cálculos (`generar_todos.py:998-1027`).

Tras el cutover de Fase 8 no añadía ninguna entrada nueva a
`ficha_nueva['revisiones']` ni creaba un sidecar. Al guardar
(`generar_todos.py:1060-1064`), el único rastro persistente propio de la
aplicación era `f`/`r` en las celdas que efectivamente cambiaban, por la lógica
común de `aplicar_revision.py:35-42`; el número de cambios solo se imprimía en
consola (`generar_todos.py:1072-1078`). En una revisión idempotente sin cambios
no quedaba ningún rastro persistente nuevo.

## Formato elegido

Se eligió JSONL UTF-8, con un objeto JSON compacto por línea y apertura en
modo append (`trazabilidad_revisiones.py:54-60`). Es adecuado para este log
porque:

1. añadir una aplicación no reescribe ni borra las anteriores;
2. cada evento se puede leer y validar de forma independiente;
3. es sencillo de revisar con herramientas de texto y de versionar;
4. un fallo en una entrada nueva no obliga a reconstruir un documento JSON
   monolítico ya existente.

Cada entrada, definida en `trazabilidad_revisiones.py:22-51`, contiene:

- `version`, `revision_id`, `obra`, `fecha`, `origen` y `fuente`;
- `generado_por` y `generado_en` de la revisión normalizada;
- `celdas_cambiadas`, `celdas_conservadas`, `celdas_descartadas` y, como
  dato adicional, `celdas_rechazadas`;
- `aplicado_en`, timestamp ISO con zona horaria de la aplicación real;
- `salvaguarda_doble_calculo_coincidio` y
  `celdas_comparadas_salvaguarda`.

Un log de revisiones **aplicadas** solo puede registrar
`salvaguarda_doble_calculo_coincidio=true`: si no coincide, el flujo no guarda
la ficha y no crea entrada. El campo se conserva explícitamente para que esa
condición no tenga que inferirse en una auditoría posterior.

La función pública es
`registrar_trazabilidad(resultado_aplicacion, ruta_log, *, revision,
salvaguarda_coincidio, celdas_comparadas=None)`
(`trazabilidad_revisiones.py:63-83`). Rechaza resultados que no tengan
`escrito=True`, captura cualquier excepción, avisa con
`[AVISO TRAZABILIDAD]` y devuelve `False`. No crea directorios implícitos y no
propaga el fallo: la ficha ya guardada se conserva.

## Puntos exactos de conexión

### CLI `leer_hoja_marcada.py`

- Digital (PDF o HTML preferido): el dry-run termina antes en
  `leer_hoja_marcada.py:768-770`; la salvaguarda termina en 772-774; se
  conservan sidecar y `ficha['revisiones']` en 784-801; se guarda la ficha en
  802 y solo después se registra el JSONL en 803-809.
- Tinta: el dry-run termina antes en `leer_hoja_marcada.py:902-903`; la
  salvaguarda termina en 905-907; se conservan sidecar y
  `ficha['revisiones']` en 923-946; se guarda la ficha en 947 y solo después
  se registra el JSONL en 948-954.

Así, ninguna simulación escribe el log y un fallo del log ocurre después de
la persistencia validada, sin posibilidad de bloquearla o revertirla.

### Cutover de `generar_todos.py`

Una discrepancia devuelve la ficha anterior y `False` antes de cualquier
registro (`generar_todos.py:1042-1058`). Cuando hay paridad, se vuelcan los
apartados, se guarda la ficha en `generar_todos.py:1060-1064` y se registra el
JSONL inmediatamente después, en `generar_todos.py:1065-1071`. La llamada usa
la `revision` y la `aplicacion` ya calculadas por la salvaguarda, sin repetir
el cálculo.

## Tests nuevos

`tests/test_trazabilidad_revisiones.py` usa únicamente
`TemporaryDirectory`, datos mínimos y mocks:

- append sin borrar la entrada anterior: líneas 59-73;
- lectura JSONL después de tres entradas y comprobación de campos: 75-96;
- fallo sintético `OSError` después del guardado de ficha, con continuidad
  del cutover y aviso visible: 98-140;
- una aplicación no escrita no crea log: 142-150.

Ejecución dirigida:

```text
python -m unittest discover -s tests -p 'test_trazabilidad_revisiones.py' -v
Ran 4 tests in 0.136s
OK
```

También se ejecutaron de forma dirigida los dos módulos de cutover: 7 tests,
0 fallos. Tras estas pruebas se comprobó que no existía ningún
`revisiones_aplicadas.jsonl` bajo una obra real.

## Suite completa

Se ejecutó **una sola vez** la suite completa solicitada:

```text
python -m unittest discover -s tests
Ran 551 tests in 61.229s
OK (skipped=4)
```

Resultado: 0 fallos y 4 omitidos. Se mantiene exactamente la línea base de la
Fase 8 (547 tests) más los 4 tests nuevos. Los dos `ResourceWarning` ya
existentes de `test_paginacion_generador.py` no afectaron al resultado.

## `.gitignore`

Sí hacía falta tocarlo para publicar el nuevo log. La lista blanca parte de
`*` (`.gitignore:1-5`) y antes no tenía una excepción para `.jsonl`, por lo
que el registro común habría quedado solo en el disco local, justo el mismo
problema que ya se había resuelto para `.clasificacion.json` y
`.correcciones.json`.

Se añadió una única excepción, deliberadamente estrecha:

`!SAGARDE OBRAS ABIERTAS/*/INFORME SAGARDE IA/revisiones_aplicadas.jsonl`

en `.gitignore:48-50`. No se amplió la publicación a otros JSONL ni a otros
directorios.
