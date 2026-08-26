# Informe de implementación — Fase 2 de unificación de revisiones

Fecha: 25/08/2026.

## Alcance completado

Se ha implementado únicamente la Fase 2 aprobada, como código nuevo y sin
conectarlo a ningún camino de producción.

Ficheros creados:

- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/validar_revision.py`
  contiene el modelo ligero de `REVISION_NORMALIZADA` y `REVISION_CELDA`, sus
  constructores y validadores de forma, la generación determinista de
  `revision_id`, la carga del catálogo real y el validador común de las diez
  reglas.
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_validar_revision.py`
  contiene 45 tests unitarios nuevos, con datos sintéticos y sin dependencias
  nuevas.
- `_SISTEMA/docs/2026-08-25-fase2-codex-informe.md` es este informe.

No se ha modificado ningún fichero existente, no se ha tocado nada bajo
`_SISTEMA/MOTOR/`, no se ha escrito ningún dato de obra y no se ha conectado el
módulo nuevo a lectores, adaptadores ni generadores.

## Implementación

El módulo nuevo ofrece:

- `crear_revision_celda()` y `validar_forma_revision_celda()` para dicts con
  `clave`, `estado_leido` y `confianza`.
- `crear_revision_normalizada()` y `validar_forma_revision_normalizada()` para
  dicts con los campos aprobados y `metadata`, incluido `hoja_usada`.
- `generar_revision_id()`, que calcula SHA-256 sobre los bytes del contenido de
  la fuente y usa sus ocho primeros caracteres hexadecimales en el formato
  `{obra}__{fecha}__{origen}__{hash8}`. La ruta y la fecha de modificación del
  fichero no intervienen.
- `cargar_catalogo_tajos()`, cuya ruta por defecto es el
  `reglas/CATALOGO_TAJOS.json` real situado junto al módulo.
- `validar(revision, ficha_actual, catalogo)`, que no muta ninguna entrada y
  devuelve errores bloqueantes, celdas aceptadas, celdas rechazadas, avisos,
  resumen y el indicador global `aplicable`.

Cada celda aceptada lleva `antes`, `despues` y una acción explícita:
`actualizar`, `conservar` o `descartar`. Una futura Fase 3 podrá escribir solo
las de acción `actualizar`, siempre que `aplicable` sea verdadero. Un blanco
digital y una `N` son entradas válidas, por lo que se conservan entre las
aceptadas, pero sus acciones dejan explícito que no se escriben.

Las diez reglas se aplican en el orden diseñado: coincidencia de obra, forma de
clave, existencia de ubicación, tajo de catálogo común o propio de obra,
alfabeto de hoja, traducción por origen, protección frente a blancos,
retroceso explícito, precondición de tinta y fecha explícita.

## Decisiones técnicas menores

- Se usaron dicts simples y funciones, sin dataclasses ni jerarquías de clases,
  para mantener el estilo del proyecto y dejar el resultado serializable.
- `MAPA_ESTADO` se importa desde `ficha_obra.py`. El alfabeto de hoja aprobado
  se comprueba contra ese mapa y la traducción de `X`, `M`, `/` y blanco usa el
  propio `MAPA_ESTADO`; no se copió el mapa de estados de ficha.
- Los tajos válidos son la unión de `catalogo["tajos"]` y
  `catalogo["obras"][obra]["tajos"]`. Un test carga el catálogo 1.3 real y
  valida el tajo propio `ventilacion` de Obispo Orueta.
- La clave exige exactamente cuatro partes no vacías y minúsculas. La búsqueda
  de portal, planta y vivienda recorre la estructura declarada de la ficha.
- Un blanco de tinta con `hoja_usada=true` convierte `None` o `?` en `P`; un
  estado conocido se conserva. Esto mantiene la paridad comprobada de
  `? -> P` y de blanco sobre `X` sin descenso.
- `hoja_usada` es un booleano obligatorio de `metadata`. Como la asignación de
  trazos por celda se realiza antes de normalizar, el validador trata
  “sin tinta no hay cambio” como la precondición aprobada: una revisión de
  origen `tinta` con `hoja_usada=false` no puede proponer un estado no vacío.
  Sus blancos se aceptan como `conservar`.
- Una `confianza="dudosa"` mantiene la forma admitida por el diseño y produce
  un aviso no bloqueante. La resolución o el descarte humano sigue siendo
  responsabilidad previa del adaptador.
- Si una sola celda queda rechazada, el resultado conserva el detalle de las
  demás celdas para el dry-run, pero `aplicable=false` impide una aplicación
  parcial accidental.
- La fecha se valida estrictamente como `DD/MM/AAAA`; un timestamp de
  `metadata.generado_en` nunca la sustituye ni permite inferirla.

## Cobertura de tests

Los 45 tests nuevos incluyen casos independientes de paso y fallo o de
aplicación/no aplicación para cada una de las diez reglas, los constructores y
validadores de forma, la estructura consumible del resultado, el carácter no
mutante de `validar()`, propagación de avisos y los tres orígenes.

La determinación del identificador se comprobó con:

- el mismo fichero procesado dos veces;
- el mismo contenido guardado en dos rutas distintas;
- dos contenidos distintos.

Los dos cruces exigidos contra el comportamiento existente comparan
directamente el nuevo resultado con `leer_hoja_marcada.marcar_no_empezados()`:

- blanco sobre `X`: ambos conservan `X` y no producen cambio;
- blanco sobre `?`: ambos producen `? -> P`.

Resultado de la suite específica, después de restaurar las mutaciones:

```text
Ran 45 tests in 0.086s
OK
```

## Pruebas por mutación

Se hicieron dos mutaciones temporales sobre el módulo nuevo y se restauró el
código correcto inmediatamente después de cada ejecución:

1. Se añadió deliberadamente `P` al alfabeto de hoja. El test
   `test_regla_5_falla_con_estado_fuera_del_alfabeto_de_hoja` dejó de encontrar
   el rechazo esperado para `P` y terminó con error (`exit_code=1`).
2. Se alteró la guarda del blanco para permitir que una `X` entrara en la rama
   de traducción a `P`. El test
   `test_regla_7_pasa_blanco_conservando_cualquier_estado_conocido` falló con
   la diferencia `('X', 'P') != ('X', 'X')` (`exit_code=1`).

Por tanto, ambos tests reaccionan ante una rotura real de su regla y no son
falsos verdes. La suite específica volvió a quedar 45/45 tras restaurar el
código.

## Suite completa y regresiones

Comando ejecutado desde
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`:

```text
python -m unittest discover -s tests
```

Resultado:

```text
Ran 490 tests in 50.401s
OK (skipped=4)
```

El conteo es exactamente la línea base de la Fase 0 (445 tests: 441 pasan y 4
omitidos) más los 45 tests nuevos: 486 pasan y 4 se omiten, con 0 fallos y 0
errores. Durante la ejecución aparecieron dos `ResourceWarning` de tests
existentes de paginación, sin afectar el resultado.

## Ambigüedades

No quedó ninguna ambigüedad semántica abierta que obligara a detener la fase.
La única frontera que requería hacer explícita una decisión técnica menor era
la regla 9: el modelo aprobado no contiene geometría ni un campo de trazo por
celda y declara que ese filtrado pertenece al adaptador. Se resolvió sin ampliar
el modelo, usando `metadata.hoja_usada` para bloquear cualquier marca no vacía
de una hoja de tinta declarada no usada y manteniendo la asignación de tinta por
celda como precondición del productor de la revisión normalizada.
