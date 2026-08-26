# Informe de implementación — Fase 7 de unificación de revisiones

Fecha de cierre: 26/08/2026.

## Alcance y reanudación

Esta fase conecta por primera vez el CLI real `leer_hoja_marcada.py` con el
motor común de revisiones. El intento anterior ya había dejado una
implementación completa y un fichero de pruebas nuevo. En esta reanudación se
leyeron íntegros el contrato, el diseño, los informes de Fases 2–6b, el CLI, el
validador, el aplicador, los tres adaptadores y la skill de revisión. Después de
contrastarlos no fue necesario reescribir la implementación: se conservó el
trabajo ya correcto y se verificó empírica y automáticamente.

Los únicos entregables propios de Fase 7 son:

- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/leer_hoja_marcada.py`;
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_cutover_leer_hoja_marcada.py`;
- `_SISTEMA/docs/2026-08-25-fase7-codex-informe.md` (este informe).

No se tocó `_SISTEMA/MOTOR/`, ningún adaptador, `generar_todos.py`, una ficha
real ni otro fichero de obra. Tampoco se copió ningún árbol de directorios. Los
tests nuevos solo crean un PDF sintético de unos bytes, dos JSON mínimos y, en
los casos digitales, un HTML mínimo dentro de `TemporaryDirectory`.

## Cutover de la escritura: antes y después

### Antes

En tinta, `main()` llamaba directamente a `aplicar()` y, cuando correspondía,
a `marcar_no_empezados()`. En digital llamaba a `estados_impresos()` y
`aplicar_digital()`. Después asignaba esos estados a la ficha y persistía con
`fichas.guardar()`.

### Después

Los flags y argumentos públicos anteriores se mantienen. Se añade únicamente
el escape opcional `--forzar-pdf` para el flujo digital.

Para `--aplicar`:

1. `adaptar_revision_tinta.construir_revision_normalizada_tinta()` construye
   la `REVISION_NORMALIZADA` con la clasificación y las candidatas existentes;
2. `validar_revision.validar()` la valida explícitamente;
3. `aplicar_revision.apply_revision(..., dry_run=not args.escribir)` calcula la
   ficha resultante en memoria;
4. con `--escribir`, solo la `ficha_actualizada` del motor común llega a
   `fichas.guardar()`.

Para `--digital` se sigue el mismo patrón, eligiendo antes el adaptador HTML o
PDF. `apply_revision()` continúa siendo puro respecto al disco: su campo
`escrito=True` significa que construyó una copia de ficha en memoria. La única
persistencia de ficha sigue siendo la llamada final y explícita a
`fichas.guardar()`.

Los sidecars y el historial usan ahora el `revision_id` determinista de la
revisión normalizada. Al sustituir una entrada se retiran tanto ese id como el
antiguo `rev_DDMMYYYY`, para no dejar duplicada la misma revisión durante la
migración.

`_ruta_sistema()` acepta ahora `crear=False`. En `--aplicar` y `--digital` no
se crea una carpeta ni se abre un sidecar para escritura antes de superar la
salvaguarda. `--preparar` conserva su comportamiento anterior y sí crea sus
artefactos.

## Preferencia por el HTML gemelo

En `--digital`, el CLI forma la ruta gemela sustituyendo la extensión del PDF
por `.html`, en el mismo directorio y con el mismo nombre base.

- Si existe, usa
  `adaptar_revision_html.construir_revision_normalizada_html()` e imprime
  `usando el HTML gemelo: <ruta>`.
- Si no existe, usa
  `adaptar_revision_pdf_digital.construir_revision_normalizada_pdf_digital()`
  e imprime `sin HTML gemelo, usando lectura del PDF`.
- Con `--forzar-pdf`, un HTML existente se ignora de forma explícita y se
  imprime `HTML gemelo ignorado por --forzar-pdf; usando lectura del PDF`.

La fecha pasada por `--fecha` sigue siendo la autoridad también al leer HTML;
no se infiere del nombre ni de la cabecera.

## Salvaguarda de doble cálculo

La salvaguarda está activa obligatoriamente en `--aplicar --escribir` y
`--digital --escribir`. No se aplica a `--preparar` ni a simulaciones sin
`--escribir`.

Antes de cualquier escritura:

1. el camino antiguo calcula en memoria los estados mediante
   `aplicar()` más `marcar_no_empezados()` en tinta, o mediante
   `estados_impresos()` más `aplicar_digital()` en digital;
2. el camino nuevo construye, valida y aplica la revisión normalizada sobre
   una copia en memoria;
3. se compara la unión de todas las claves de `estados` y el valor funcional
   `v` de cada clave;
4. una clave ausente en cualquiera de los lados también es discrepancia.

Se compara `v`, no los metadatos `f`, `r` u `origen`: el id histórico y el
`revision_id` normalizado son deliberadamente distintos, mientras que la red
de seguridad debe exigir igualdad de la decisión funcional de estado.

Si hay diferencias, se imprime cada clave con
`antiguo=<valor>; nuevo=<valor>`, se informa que no se escribió nada y se
termina con `SystemExit(2)`. La comprobación ocurre antes de crear/escribir el
sidecar y antes de llamar a `fichas.guardar()`. Si hay igualdad, se informa el
número total de celdas comparadas y solo entonces se autoriza la persistencia
del resultado nuevo.

El test más importante,
`test_discrepancia_aborta_sin_sidecar_ni_ficha`, altera artificialmente el
resultado común de `X` a `M`. Resultado observado:

```text
[ABORTADO]
antiguo='X'; nuevo='M'
SystemExit: 2
fichas.guardar: 0 llamadas
sidecar: no creado
```

## Verificación empírica final de los tres casos reales

### Método de aislamiento

Se ejecutó `leer_hoja_marcada.main()` con los argumentos reales y con
`--escribir`, pero sin entregar al CLI ninguna ficha viva:

- las fichas históricas se obtuvieron con `git show` y se deserializaron en
  memoria;
- `fichas.cargar()` devolvió una copia profunda de esa ficha histórica;
- `fichas.guardar()` fue sustituido por una captura en memoria;
- la ruta de escritura del sidecar se redirigió a un `TemporaryDirectory`
  mínimo situado en D:, con un único JSON por caso, eliminado al terminar;
- los PDF, HTML, candidatas y clasificaciones reales se leyeron directamente
  de su ubicación, sin copiarlos;
- no se hizo checkout ni se copió una carpeta real.

Aunque el CLI se invocó con `--escribir` para atravesar la salvaguarda completa,
`apply_revision(dry_run=False)` solo operó sobre la copia histórica en memoria,
y el guardado real estuvo simulado.

Como comprobación adicional, antes y después se calcularon SHA-256 de las dos
fichas vivas implicadas y de los tres sidecars reales. Los cinco hashes
permanecieron idénticos.

### Resultados exactos

| Caso | Base histórica | Resultado de la salvaguarda | Resumen del CLI |
|---|---|---|---|
| Bolueta 26/07/2026, tinta | `9a70a5f` | Coincidencia exacta en **3.838** celdas; 0 discrepancias | 12 candidatas, 0 cambios, 5 descartadas |
| Mungia 27/07/2026, tinta | `5c90dec` | Coincidencia exacta en **2.356** celdas; 0 discrepancias | 225 candidatas, 12 cambios, 33 descartadas |
| Bolueta 24/08/2026, digital | `a616f91` | Coincidencia exacta en **3.686** celdas; 0 discrepancias | HTML gemelo preferido; 1.963 marcas explícitas, 443 cambios |

En los tres casos se alcanzó exactamente una llamada simulada a
`fichas.guardar()`, siempre después del mensaje `[SALVAGUARDA]`. En Bolueta
digital aparecieron los 19 avisos `FontBBox` ya documentados en Fase 5 durante
la lectura PDF del camino antiguo. La extracción terminó correctamente y la
comparación fue exacta.

## Pruebas nuevas y contrato histórico

`test_cutover_leer_hoja_marcada.py` contiene 5 tests end-to-end con datos
sintéticos mínimos:

- tinta con paridad exacta: guarda solo el resultado común;
- digital con HTML gemelo: usa HTML y no el adaptador PDF;
- digital sin HTML gemelo: usa el fallback PDF;
- `--forzar-pdf`: ignora el HTML existente;
- divergencia artificial: aborta sin ficha ni sidecar.

Resultados focalizados:

```text
test_leer_hoja_marcada.py:         Ran 28 tests - OK
test_cutover_leer_hoja_marcada.py: Ran  5 tests - OK
```

Las 28 aserciones históricas se ejecutaron sin modificación.

## Suite completa

La suite completa se ejecutó una sola vez, con bytecode desactivado:

```text
python -B -m unittest discover -s tests
Ran 545 tests in 50.980s
FAILED (failures=1, errors=3, skipped=4)
```

El total es el esperado: 540 tests de Fase 6b más los 5 nuevos. La ejecución
produjo 537 éxitos, 4 omisiones históricas y 4 resultados fallidos. Los cuatro
fallos fueron causados por la decisión de desviar `TEMP/TMP` desde el casi
lleno C: a `.fase7_unittest_temp` dentro del árbol técnico del repositorio:

- tres tests de `test_cerrar_obra` vieron sus propios fixtures sintéticos como
  cambios sin commitear del repositorio padre;
- el control de `test_auditor_sagarde` quedó filtrado porque la ruta absoluta
  de su fixture contenía el segmento técnico
  `_SISTEMA INFORME SAGARDE IA`.

No se repitió la suite completa, respetando la orden de ejecutarla una sola
vez. Se ejecutaron únicamente los dos módulos afectados con el directorio
temporal normal de Windows; no contienen `copytree` y sus fixtures ocupan pocos
KB:

```text
test_cerrar_obra.py:     Ran 24 tests - OK
test_auditor_sagarde.py: Ran  7 tests - OK
```

Por tanto, todos los tests que no dependían de esa ubicación temporal pasaron
en la ejecución completa, y los módulos afectados pasaron al eliminar la causa
ambiental. No hay evidencia de regresión funcional, aunque el registro literal
de la única invocación completa no es verde y debe conservarse así, sin
presentarlo como un `OK` que no ocurrió. Se mantuvieron los 2
`ResourceWarning` históricos de paginación.

La carpeta temporal de suite quedó vacía y fue eliminada. `git diff --check`
terminó con código 0. No hubo aviso de falta de espacio; al cierre quedaban
aproximadamente 159 MiB libres en C:.

## Puntos para revisión especial de Claude

1. Revisar expresamente que la igualdad de salvaguarda sobre el valor `v` es
   la interpretación correcta del contrato. Comparar el registro completo
   haría divergir siempre los caminos por los metadatos e ids distintos del
   propio cutover.
2. Confirmar el resultado combinado de suite: la única ejecución completa no
   fue verde por una ubicación temporal incompatible, mientras los dos módulos
   afectados pasan íntegros con su entorno normal. Si se exige un único
   transcript completo en verde, habrá que repetirlo en otra sesión con más
   margen en C: o con un temporal en D: que esté fuera del repositorio y fuera
   de cualquier carpeta técnica; no se hizo aquí por la orden de una sola
   ejecución.
3. Mantener activa la salvaguarda. En digital, el camino antiguo se calcula
   siempre desde el PDF aunque el nuevo prefiera HTML: esa independencia es la
   que da valor a la comparación.
4. Recordar que `apply_revision(..., dry_run=False)` no persiste por sí mismo;
   devuelve la copia que el CLI guarda una sola vez tras la paridad.

## Conclusión

El cutover está implementado y los tres casos reales demuestran 0
discrepancias entre el camino antiguo y el motor común. La preferencia por HTML
gemelo funciona y el fallback PDF queda disponible, incluido el escape
`--forzar-pdf`. La prueba de divergencia confirma que la red de seguridad
detiene el proceso antes de cualquier escritura.

No se escribió ningún dato real ni se copió ningún árbol de directorios.
