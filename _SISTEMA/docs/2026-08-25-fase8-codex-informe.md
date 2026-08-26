# Informe de implementacion - Fase 8 de unificacion de revisiones

Fecha de cierre: 26/08/2026.

## Investigacion previa (documentada antes de implementar)

### 1. Que contiene realmente `snapshot_crudo`

El bucle de publicacion no combina las revisiones celda a celda. El adaptador
devuelve `historial = [(fecha, snapshot), ...]` y `generar_todos.py` selecciona
literalmente el ultimo par con `fecha_ultima, snapshot_crudo = historial[-1]`.
Antes de este cutover, la llamada exacta a
`fichas.actualizar_desde_snapshot()` estaba en
`generar_todos.py:902-906`; `historial` se leia en `generar_todos.py:848-850`.

Cada registro de ese ultimo snapshot aporta una celda completa:
`task` determina el tajo; `building`, `floor` y `unit` determinan la ubicacion;
`status` aporta el estado observado. `actualizar_desde_snapshot()` hace esa
traduccion registro a registro (`ficha_obra.py:401-430`) y entrega el conjunto
a `actualizar()` (`ficha_obra.py:432-434`). Por tanto, `snapshot_crudo` no es
una lista de cambios. Es la fotografia puntual completa que el adaptador pudo
leer para la fecha mas reciente. Tampoco es, por si sola, el acumulado de todas
las fechas: el estado acumulado final aparece al aplicarla sobre la ficha
existente, conservando celdas omitidas y blancos, y reclamando despues las
correcciones manuales (`ficha_obra.py:487-535`).

Los adaptadores pueden fusionar formatos por fecha antes de devolver el
historial, pero eligen una fotografia entera para cada fecha. Gernika sustituye
el JSON por el HTML si ambos comparten fecha
(`adaptadores/adaptador_gernika.py:220-265`); Mungia y Bolueta hacen lo mismo
prefiriendo el PDF nuevo. Nada de eso convierte `snapshot_crudo` en un delta.

### 2. Relacion entre `actualizar_desde_snapshot()` y `actualizar()`

La afirmacion de Fase 0 sigue siendo exacta. No son dos implementaciones:
`actualizar_desde_snapshot()` solo resuelve nombres y construye
`detalle_items`, y su unica salida es la llamada directa a `actualizar()`
(`ficha_obra.py:388-434`). La regla de blanco esta unicamente en
`actualizar()`: si `estado_norm` esta vacio y ya hay registro, conserva el
valor `v` y solo refresca la fecha si faltaba (`ficha_obra.py:487-527`). Asi,
ambos nombres comparten literalmente la misma logica de "blanco no baja un
estado conocido".

### 3. Que aporta hoy el HTML de Gernika y como cruza con el CLI de Fase 7

`adaptador_gernika` llama a `lector_hoja_tajos_html.listar_revisiones_html()`
con tres mapas fijos: portal, planta y tajo
(`adaptadores/adaptador_gernika.py:96-162`). El lector divide cada `data-k` en
portal/planta/tajo/unidad, descarta `N`, resuelve los tres ids y normaliza
`data-st` a `X`, `M`, `/` o blanco antes de emitir
`{task, floor, building, unit, status}`
(`lector_hoja_tajos_html.py:47-88`). El adaptador mezcla despues JSON y HTML
por fecha, haciendo ganar al HTML (`adaptadores/adaptador_gernika.py:220-265`).

Comprobacion estrictamente de lectura sobre los ficheros reales actuales:

- los HTML del 22/07 y 23/07 son plantillas con una unica expresion
  `${st}` y producen cero registros;
- `REVISION 2025 GERNIKA 32V 25072026 (1).html` contiene 1.216 `data-k`
  unicos y todos se resuelven: 928 estados `X` y 288 blancos, sin `M`, `/` ni
  `N`;
- la ficha actual tiene tambien 1.216 claves de estado y una sola revision
  registrada para el 25/07/2026; no existe hoy ningun `.correcciones.json` de
  Gernika.

Si esa misma revision digital se procesa tambien por el CLI de Fase 7, el
estado no se suma: las marcas explicitas coincidentes son idempotentes y los
blancos digitales no cambian nada (`validar_revision.py:378-406`). El sidecar
que crea el CLI contiene solo celdas que cambian y `generar_todos.py` lo
reclama despues del snapshot, de modo que una correccion explicita gana, no se
duplica aritmeticamente (`leer_hoja_marcada.py:771-803` y
`ficha_obra.py:532-535`). Si HTML y PDF discrepasen, esa precedencia podria
mostrar un conflicto funcional, y la salvaguarda de esta fase debe detectarlo.
Lo que si puede duplicarse en el sistema anterior es la trazabilidad de la
misma fecha con ids distintos (`rev_DDMMYYYY` frente al id normalizado): el
CLI retira el id antiguo al guardar, pero una publicacion posterior podia
volver a registrarlo (`leer_hoja_marcada.py:793-801` y
`ficha_obra.py:537-547`).

Decision: no se retira ni se modifica la lectura HTML de Gernika en esta fase.
Es una fotografia completa, exacta e idempotente respecto de los valores, y no
hay evidencia actual de duplicacion conflictiva. La unificacion se hace en el
punto de escritura de `generar_todos.py`, como marca el alcance.

## Origen de la revision normalizada

Se eligio un cuarto origen explicito: `historial_consolidado`. No se etiqueto
como `tinta`, `pdf_digital` ni `html_digital` porque el dato que recibe
`generar_todos.py` ya ha perdido esa procedencia unica: Mungia y Bolueta
fusionan DOCX/PDF y sidecars, Gernika fusiona JSON/HTML, Gorliz usa JSON y la
obra de prueba devuelve el estado de su propia ficha. Forzar uno de los tres
origenes fisicos habria dejado trazabilidad falsa.

Este hallazgo revelo el unico hueco real que obligo a tocar uno de los modulos
ya construidos. `validar_revision.py` admite ahora
`historial_consolidado` (`validar_revision.py:18-19`) con estas dos reglas:

- acepta `P` explicita porque el consolidado puede incorporar un sidecar de
  tinta (`validar_revision.py:323-330`);
- conserva el blanco como los origenes digitales, porque en el snapshot del
  adaptador significa "no hay dato nuevo", no "hoja de tinta usada"
  (`validar_revision.py:392-396`).

El mapa publico `ALFABETOS_HOJA` de los tres origenes existentes no cambio;
sus 48 tests historicos siguen pasando. No se modificaron los tres adaptadores
normalizados, `aplicar_revision.py`, `leer_hoja_marcada.py`, ningun adaptador
de obra ni `_SISTEMA/MOTOR/`.

`construir_revision_normalizada_desde_snapshot()` vive en
`generar_todos.py:851-964`. Reutiliza los indices y normalizadores de
`ficha_obra`, construye claves canonicas, incorpora las correcciones con la
misma precedencia posterior que tenian antes y usa los constructores de
`validar_revision`; no reimplementa las reglas de validacion. Las ubicaciones
o tajos nuevos que el motor comun no puede representar no se inventan: dejan
aviso y la comparacion contra el camino antiguo bloquea la obra si cambian la
verdad de `estados`. El `revision_id` es determinista sobre obra, fecha,
origen y SHA-256 del snapshot mas las correcciones; `fuente` identifica la
salida `adaptador_*.cargar_historial()[-1]`.

## Cutover e aislamiento por obra

La lectura de adaptadores no cambio: el bucle sigue llamando literalmente a
`adaptador.cargar_historial()` (`generar_todos.py:1097-1103`) y sigue tomando
`historial[-1]` (`generar_todos.py:1153-1159`). Solo cambio el mecanismo que
decide y persiste los estados de la ficha.

`calcular_actualizacion_ficha_con_salvaguarda()`
(`generar_todos.py:989-1027`) hace, sin escribir:

1. camino antiguo completo sobre una copia profunda mediante
   `fichas.actualizar_desde_snapshot()`;
2. traduccion a `REVISION_NORMALIZADA`, llamada explicita a
   `validar_revision.validar()` y aplicacion en memoria con
   `apply_revision(..., dry_run=False)`;
3. comparacion de la union de claves y del valor `v`; una clave ausente en
   cualquiera de los lados tambien es discrepancia.

`actualizar_ficha_con_salvaguarda()` (`generar_todos.py:1030-1073`) aplica la
decision por obra:

- con paridad, vuelca los apartados auxiliares y guarda exclusivamente
  `ficha_nueva`, la copia devuelta por el motor comun;
- con divergencia, imprime obra, todas las claves discrepantes y
  `antiguo=<v>; nuevo=<v>`, devuelve la ficha original y no llama a
  `fichas.guardar()`.

El bucle conserva un flag local de bloqueo (`generar_todos.py:1141,1163`) y
tambien impide el guardado posterior que normalmente hace el priorizador
(`generar_todos.py:1182-1187`). Asi una divergencia no se cuela por una segunda
escritura de la misma pasada. No se lanza `SystemExit`: se deriva el snapshot
de la ficha que haya quedado autorizada, y memoria, prioridades, panel e
informe ejecutivo continuan usando `historial` como antes
(`generar_todos.py:1165-1235`). El `except Exception` exterior por obra sigue
siendo el existente; no se creo un aborto global nuevo.

## Tests nuevos

`tests/test_cutover_generar_todos.py` contiene dos tests sinteticos y no copia
ningun arbol ni usa una ficha real:

- paridad exacta: incluye una correccion `P`, exige una sola llamada a
  `fichas.guardar()`, comprueba el valor final y el id
  `historial_consolidado`, y confirma que no se guardo el registro de revision
  del camino antiguo (`test_cutover_generar_todos.py:65-84`);
- divergencia aislada: procesa dos obras en el mismo bucle de test, fuerza
  `X` antiguo frente a `M` nuevo solo en la primera, comprueba que esa conserva
  `?` y no se guarda, y que la segunda si llega a `X` y es la unica guardada
  (`test_cutover_generar_todos.py:86-134`).

Resultado focalizado final:

```text
test_cutover_generar_todos.py: Ran  2 tests - OK
test_validar_revision.py:      Ran 48 tests - OK
test_aplicar_revision.py:      Ran 16 tests - OK
test_generar_todos.py:         Ran 26 tests - OK
test_registro_obras.py:        Ran  4 tests - OK
```

## Verificacion empirica real, solo en memoria

Se importaron los adaptadores reales y se leyeron directamente sus historiales.
Para cada obra se cargo la ficha una vez, se ejecutaron ambos caminos sobre
copias y no se llamo a `guardar`, no se ejecuto `main()` y no se uso ningun
flag de escritura. Se calculo SHA-256 de cada ficha viva antes y despues.

| Obra | Ultima fecha | Entrada al traductor | Claves comparadas | Resultado |
|---|---:|---:|---:|---:|
| Gernika | 25/07/2026 | 1.216 snapshot, 0 correcciones, 1.216 normalizadas | 1.216 | 0 diferencias |
| Mungia | 25/08/2026 | 568 snapshot, 12 correcciones, 573 normalizadas tras precedencia | 2.356 | 0 diferencias |
| Bolueta | 24/08/2026 | 679 snapshot, 166 correcciones, 845 normalizadas | 3.686 | 0 diferencias |
| Obra Prueba | 05/08/2026 | 1.178 snapshot, 0 correcciones | 1.178 | 0 diferencias |

Las cuatro revisiones fueron aplicables, `apply_revision` produjo su copia en
memoria y el traductor emitio cero avisos. Coinciden **4 de 4** obras que hoy
tienen ficha e historial. Gorliz no tiene hoy ni `ficha_obra.json` ni una
revision oficial, por lo que conserva el comportamiento anterior y no entra
en este bloque.

Hashes SHA-256, identicos antes y despues:

```text
Gernika  0ad913bdff859dbda542a85cc905cea062a305b21dc87f9015bbdb77105b7ff3
Mungia   b06e4d7e1886aff7630ebcd11efd877f29734bea2381c330df591ccdbdbbe3c6
Bolueta  5d9290d282cf59da7a524ae6dffb1d924d67617cfe36e834dd02926111d2e2cf
Prueba   031eff3229f98915e2dacde8167ee5a2e758dced8df31bc9ed3a8eefcb31d0fb
```

## Suite completa

Se ejecuto una sola vez, al final y con el directorio temporal normal de
Windows:

```text
python -B -m unittest discover -s tests
Ran 547 tests in 37.248s
OK (skipped=4)
```

Son los 545 tests de la linea base de Fase 7 mas los 2 nuevos: 543 pasan y 4
se omiten por los casos historicos de Obispo Orueta. Los cuatro resultados que
fallaron en Fase 7 por situar TEMP dentro del repositorio pasan esta vez en la
misma ejecucion completa; no hubo fallos ni errores. Se mantienen los dos
`ResourceWarning` historicos de `test_paginacion_generador.py` por dos lecturas
sin `with`, sin efecto en el resultado.

## Puntos para revision especial de Claude

1. Revisar expresamente que `historial_consolidado` es preferible a falsear
   uno de los tres origenes fisicos. La extension del validador es minima y
   mantiene intacto el contrato publico de sus alfabetos existentes.
2. La salvaguarda compara solo `v`, por mandato de esta fase y como Fase 7.
   Los campos `f`/`r` cambian deliberadamente y el resultado nuevo ya no añade
   el registro legado `rev_DDMMYYYY`; la trazabilidad unificada corresponde a
   la fase posterior.
3. Una ubicacion o tajo nuevo que antes habria ampliado estructura queda fuera
   de la revision normalizada y debe causar diferencia de claves/valores. No
   se ha dado en ninguna obra real actual (cero avisos), pero conviene revisar
   esta politica conservadora antes de retirar la salvaguarda.
4. Confirmar el doble bloqueo de escritura: el wrapper no guarda al divergir y
   el flag del bucle impide que el guardado posterior del priorizador toque la
   ficha. El resto de artefactos de la obra y las demas obras si continuan.
5. No se modifico ni retiro el lector HTML de Gernika. Sus 1.216 celdas reales
   actuales se resolvieron todas y coincidieron exactamente.
