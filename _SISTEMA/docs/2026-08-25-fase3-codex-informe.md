# Informe de implementación — Fase 3 de unificación de revisiones

Fecha: 25/08/2026.

## Alcance completado

Se ha implementado únicamente la Fase 3, todavía aislada de los lectores,
adaptadores y generadores existentes. Se han creado estos tres ficheros:

- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/aplicar_revision.py`.
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_aplicar_revision.py`.
- `_SISTEMA/docs/2026-08-25-fase3-codex-informe.md` (este informe).

No se ha modificado ningún fichero anterior, no se ha conectado el motor nuevo
a producción, no se ha tocado `_SISTEMA/MOTOR/` y no se llama a
`ficha_obra.guardar()` ni a ninguna otra operación de escritura. Todos los
datos empleados por las pruebas nuevas son sintéticos y parten de
`fixtures.ficha_minima()` o de diccionarios construidos en memoria; ninguna
prueba nueva abre o escribe un `ficha_obra.json` real.

## Implementación

`apply_revision(revision, ficha_actual, catalogo, dry_run=True)`:

1. Llama primero, con los argumentos recibidos, a
   `validar_revision.validar(revision, ficha_actual, catalogo)`.
2. Añade al resultado `escrito=False` y lo devuelve sin ficha resultante cuando
   `dry_run=True` o cuando `aplicable=False`.
3. Solo con `dry_run=False` y `aplicable=True` crea una copia profunda de
   `ficha_actual` y aplica exclusivamente las aceptadas cuya acción es
   `actualizar`.
4. Cada estado actualizado usa la forma exacta del camino principal de
   `ficha_obra.py`: `{'v': despues, 'f': revision['fecha'],
   'r': revision['revision_id']}`. No se inventan campos adicionales.
5. Devuelve la copia en `ficha_actualizada` y marca `escrito=True`. En esta
   fase, `escrito` significa que se construyó la salida actualizada en memoria;
   nunca que se haya persistido a disco.

Las acciones `conservar` y `descartar` no escriben la celda. Como se trabaja
sobre una copia profunda, conservan también sin cambios los metadatos `f` y
`r` que ya tuviera el registro.

## Pruebas de paridad

Se añadieron 15 pruebas. Las comparaciones semánticas ejecutan también la
función histórica correspondiente y comparan el valor final de la celda con el
producido por `apply_revision(dry_run=False)`.

### Casos que coinciden

| Caso histórico reconstruido | Camino histórico comparado | Resultado antiguo | Resultado nuevo | Paridad |
|---|---|---:|---:|---|
| Retroceso explícito `X -> M` a la primera (`TestNormaDeObra`, `test_leer_hoja_marcada.py:92`) | `leer_hoja_marcada.aplicar()` | `M` | `M` | Sí |
| Blanco de hoja de tinta usada sobre `X` | `leer_hoja_marcada.marcar_no_empezados()` | conserva `X` | conserva `X` | Sí |
| Blanco de hoja de tinta usada sobre `?` | `leer_hoja_marcada.marcar_no_empezados()` | `P` | `P` | Sí |
| Marca clasificada sin tinta (`TestSinTintaNoHayCambio`, línea 64) | `leer_hoja_marcada.aplicar()` | aborta y deja `?` | regla 9, `aplicable=False`, deja `?` | Sí, misma decisión de no cambiar |
| Marca digital explícita `P -> X` (`TestAplicarDigital`, línea 275) | `leer_hoja_marcada.aplicar_digital()` | `X` | `X` | Sí |
| Celda digital en blanco (`TestAplicarDigital`, línea 284) | el camino antiguo no la incluye en `impresos` | conserva `?` | acción `conservar`, queda `?` | Sí |
| Blanco sobre `X` (`test_ficha_obra.py:72-90`) | `ficha_obra.actualizar()` | conserva `X` | conserva `X` | Sí |
| Blanco digital sobre un registro `?` (`test_ficha_obra.py:111-124`) | `ficha_obra.actualizar()` | conserva `?` | conserva `?` | Sí |
| Blanco de tinta sin registro previo (`test_ficha_obra.py:126-131`) | `ficha_obra.actualizar()` | crea `P` | crea `P` | Sí |

Al confirmar las líneas exactas se encontró una precisión respecto al texto del
encargo: `test_ficha_obra.py` no contiene un caso literal `? -> P`. Su test de
las líneas 111-124 exige que un blanco sobre un registro `?` siga siendo `?`, y
las líneas 126-131 exigen `P` cuando no existe ningún registro previo. El
`? -> P` literal está demostrado en el camino de tinta por
`marcar_no_empezados()`. Las pruebas nuevas cubren las tres situaciones y
distinguen el origen para no mezclar un blanco digital con uno de tinta.

### Hallazgo crítico: las claves actuales y el contrato normalizado no son compatibles

**No hay paridad end-to-end exacta con la ficha usada por los tests actuales.**
Los tests históricos y `fixtures.ficha_minima()` conservan los identificadores
de vivienda en mayúscula y escriben claves como
`p1__pb__tubeado__A`. En cambio, `validar_revision.py` exige que toda la clave
sea minúscula y consulta `ficha_actual['estados']` por coincidencia exacta.

La discrepancia se reproduce de dos formas, ambas protegidas como
`@unittest.expectedFailure` para mantener visible la igualdad que debería
cumplirse sin convertirla en un falso verde:

1. Si la `REVISION_NORMALIZADA` conserva la clave histórica
   `p1__pb__tubeado__A`, el camino antiguo aplica `X -> M`, pero el nuevo la
   rechaza por la regla 2 (`aplicable=False`, `escrito=False`) porque contiene
   una mayúscula.
2. Si el productor cumple el contrato y emite `p1__pb__tubeado__a`, la revisión
   sí es aplicable, pero el validador ve `antes=None`. El aplicador deja intacta
   la clave histórica `...__A: X` y añade otra clave `...__a: M`. El camino
   antiguo deja una sola clave `...__A: M`.

Por tanto, los casos semánticos de la tabla coinciden cuando se representan en
la forma minúscula que admite el validador, pero esa representación no puede
actualizar por sí sola los estados de la ficha histórica. No se ha corregido ni
ocultado: resolverlo requeriría decidir una normalización canónica o una
resolución de claves compartida, y modificar el validador, los productores o la
estructura de ficha queda fuera de esta fase. **Claude debe revisar esta
discrepancia antes de cualquier cutover de la Fase 4.**

## Pruebas propias del aplicador

- El `dry_run` por defecto devuelve `escrito=False`, no devuelve
  `ficha_actualizada` y deja intacta la entrada.
- Una revisión no aplicable tampoco devuelve una ficha ni muta la entrada,
  aunque se invoque con `dry_run=False`.
- Una aplicación real devuelve una copia profunda: tanto el dict raíz como la
  estructura anidada son objetos distintos, y la ficha recibida permanece
  idéntica.
- El caso mixto end-to-end contiene, en la misma revisión, `actualizar`,
  `conservar` y `descartar`: solo cambia la primera celda; las otras dos,
  incluidos sus metadatos anteriores, quedan intactas.

Resultado focalizado después de restaurar la mutación:

```text
Ran 15 tests in 0.033s
OK (expected failures=2)
```

Los dos fallos esperados son exclusivamente las dos manifestaciones del
hallazgo crítico de claves; no son fallos del resto de la implementación.

## Prueba por mutación

Se rompió temporalmente la regla de no mutación sustituyendo:

```python
ficha_actualizada = copy.deepcopy(ficha_actual)
```

por:

```python
ficha_actualizada = ficha_actual
```

Se ejecutó únicamente
`test_aplicacion_no_muta_ficha_actual_y_devuelve_copia_profunda`. El test falló
con `exit_code=1`: la ficha recibida había cambiado de `?` a `X`. La mutación se
restauró inmediatamente, se confirmó en el fuente que vuelve a usarse
`copy.deepcopy`, y las 15 pruebas focalizadas regresaron al resultado anterior.

## Suite completa y regresiones

Antes de crear los ficheros de Fase 3 se confirmó la línea base:

```text
Ran 490 tests in 50.964s
OK (skipped=4)
```

Tras añadir las 15 pruebas:

```text
Ran 505 tests in 43.110s
OK (skipped=4, expected failures=2)
```

La línea base permanece intacta: sus 486 tests pasan y sus 4 omisiones se
mantienen. De las pruebas nuevas, 13 pasan y 2 quedan como fallos esperados por
la discrepancia crítica documentada; hay 0 fallos inesperados y 0 errores. Se
repitieron los dos `ResourceWarning` ya existentes de paginación, sin afectar al
resultado.

## Decisiones técnicas propias

- Se eligió una función y dicts simples, siguiendo el estilo de
  `validar_revision.py` y manteniendo el resultado serializable.
- `ficha_actualizada` solo existe cuando se aplica realmente la revisión. Así
  un consumidor no puede confundir el resultado de un dry-run con una ficha
  autorizada para persistir.
- Se usa copia profunda, no una copia superficial de `estados`, para garantizar
  que ninguna referencia anidada de la ficha recibida pueda modificarse desde
  la salida.
- Se conserva íntegro el resultado del validador y se usa su acción calculada;
  el aplicador no vuelve a decidir reglas ni traduce estados por su cuenta.
- `ficha_obra.actualizar()` no conserva un campo de origen. Para reconstruir
  sus tests se tomó como digital el blanco sobre `?` descrito allí como hoja de
  la app no usada, y como tinta usada el blanco sin registro previo que debe
  crear `P`, de acuerdo con la distinción aprobada en la Fase 1.
- No se registran revisiones, no se añade trazabilidad y no se actualizan campos
  globales de la ficha: esas responsabilidades pertenecen a fases posteriores.
- Los fallos de paridad de claves se dejaron como `expectedFailure` con la
  igualdad correcta como aserción. Esto permite ejecutar toda la suite y, a la
  vez, evita convertir la discrepancia en una expectativa de comportamiento
  aceptable.

## Fase 3b - correccion de mayusculas

Se ha corregido el contrato de la clave en `validar_revision.py` sin cambiar
su forma de cuatro segmentos. `_partes_clave()` sigue exigiendo cuatro partes
no vacías y minúsculas en portal, planta y tajo, pero ya no impone ningún
case al cuarto segmento: el identificador de vivienda se conserva literalmente.

La comprobación de estructura también conserva ahora ese identificador:
`_ubicacion_existe()` compara la vivienda exactamente con el `id` declarado en
`ficha_actual['estructura']`, sin convertirlo a minúsculas ni resolver aliases.
Por tanto, una estructura que declara `A` admite `p1__pb__tubeado__A` y rechaza
`p1__pb__tubeado__a`. `_estado_anterior()` ya consultaba
`ficha_actual['estados']` con la clave literal de la revisión y se ha mantenido
sin cambios. `aplicar_revision.py` tampoco necesitó cambios: no normaliza la
clave y escribe exactamente la clave aceptada por el validador.

Los dos `@unittest.expectedFailure` de Fase 3 se han retirado y ambos casos
pasan de verdad con el contrato corregido:

1. La clave histórica `p1__pb__tubeado__A` es aplicable y actualiza esa misma
   entrada, con paridad respecto al lector anterior y sin crear `...__a`.
2. La variante `p1__pb__tubeado__a` contra una estructura que declara `A` se
   rechaza por la regla 3; no muta la ficha ni crea una clave paralela.

Además se añadió una prueba end-to-end explícita que llama primero a
`validar()` y después a `apply_revision()` sobre datos sintéticos. Confirma que
la validación recupera el estado anterior de `...__A`, que la aplicación
actualiza solo esa clave y que `...__a` no aparece en el resultado.

Resultados focalizados:

```text
Ran 47 tests in 0.049s
OK

Ran 16 tests in 0.010s
OK
```

Resultado de la suite completa de `tests`:

```text
Ran 508 tests in 31.129s
OK (skipped=4)
```

Quedan 0 fallos, 0 errores y 0 fallos esperados. Se mantienen exclusivamente
las 4 omisiones ya conocidas y se repiten los dos `ResourceWarning` históricos
de paginación, sin regresiones. No se encontró otra discrepancia real de
comportamiento durante esta corrección.
