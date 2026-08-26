# Informe final — Fase 5 de unificación de revisiones

Fecha de cierre: 26/08/2026.

## Alcance de esta reanudación

La Fase 5 se retomó únicamente para completar lo que quedó pendiente al
agotarse la cuota anterior: la verificación empírica cruzada PDF digital vs.
HTML sobre Bolueta y este informe final.

No se modificaron ni se reescribieron:

- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/adaptar_revision_pdf_digital.py`;
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_adaptar_revision_pdf_digital.py`.

Tampoco se conectó el adaptador a producción, se tocó `_SISTEMA/MOTOR/`, se
ejecutó una aplicación real ni se escribió una ficha o un fichero de obra. La
comparación se hizo enteramente en memoria. El único fichero creado en esta
reanudación es este informe.

## Estado del módulo, sus pruebas y la suite completa

Antes de hacer la comparación empírica se ejecutó, desde
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`, con escritura de bytecode
desactivada:

```text
python -m unittest discover -s tests
```

Resultado:

```text
Ran 524 tests in 44.248s
OK (skipped=4)
```

Por tanto, se mantiene exactamente el estado que había verificado Claude:
524 tests ejecutados, 520 superados, 0 fallos, 0 errores y 4 omitidos. También
reaparecieron los dos `ResourceWarning` históricos de
`test_paginacion_generador.py` por ficheros abiertos sin cerrar; no alteraron
el resultado.

El módulo y su test conservaron durante toda esta reanudación estos SHA-256:

```text
adaptar_revision_pdf_digital.py
3CECFB91A1131DD7985B70CDC4EE0C6C7DC1374523D92906E36305E899D4947E

test_adaptar_revision_pdf_digital.py
EAA0BB492F20BE7C62B8CC12221339291FC1C3D2C7BDE8268DD7CFA863B808AB
```

## Resumen de las pruebas de paridad contra `TestAplicarDigital`

Los 7 tests de `test_adaptar_revision_pdf_digital.py` siguen pasando dentro de
la suite completa. Los casos que reconstruyen directamente
`TestAplicarDigital` comparan la decisión final de `aplicar_digital()` con la
del adaptador nuevo seguido de `validar()` y `apply_revision()` en memoria:

- una marca explícita `P -> X` produce la misma actualización;
- una celda que el PDF no imprime se conserva sin cambios en ambos caminos;
- volver a marcar `X` sobre `X` no produce cambio en ninguno;
- el cuarto caso, clave estructural sin registro previo en `estados`, mantiene
  visible una divergencia real y no se presenta como falsa paridad.

Las otras pruebas comprueban el contrato normalizado (`X`, `M`, `/`, blanco y
`N`, origen, fecha, `revision_id` y confianza), el criterio de
`metadata.hoja_usada` y que la fecha explícita sea obligatoria y no se infiera
del nombre del PDF.

## Hallazgo `antes=None`: sigue presente sin cambios

La divergencia documentada al crear las pruebas sigue presente exactamente en
el código actual:

- `leer_hoja_marcada.aplicar_digital()` exige que la clave ya exista en
  `ficha['estados']` y, si falta, aborta con `LecturaImposible`;
- el validador nuevo obtiene `antes=None`, acepta la marca explícita como
  acción `actualizar`, y `apply_revision(dry_run=False)` crearía esa entrada en
  la copia de la ficha.

El test
`test_discrepancia_documentada_si_falta_el_registro_de_estado` comprueba las
dos ramas de forma explícita y pasó en la suite. No se ha cambiado ninguna de
ellas en esta reanudación.

El riesgo práctico sigue siendo bajo para una ficha real correctamente
sembrada, porque el constructor de fichas crea todas las combinaciones válidas
con estado inicial `?`; aun así, la discrepancia contractual es real y queda
pendiente de decisión antes del cutover: replicar la guarda antigua evita que
una clave plausible pero ausente se cree por accidente.

## Verificación empírica cruzada de Bolueta

### Método y salvaguardas

Se usaron exclusivamente estos dos gemelos reales, en lectura:

- `SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/REVISIONES/REVISION 2026 BOLUETA ACR 24082026.pdf`;
- `SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/REVISIONES/REVISION 2026 BOLUETA ACR 24082026.html`.

La ficha común «antes» fue
`SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/INFORME SAGARDE IA/ficha_obra.json`
del commit `a616f91`, leída mediante `git show` y deserializada solo en memoria.
Es la ficha de `bolueta` actualizada a las 08:40 del 24/08/2026, con 3.686
entradas en `estados`, y es la misma base histórica usada en la Fase 4.

Se construyeron las dos `REVISION_NORMALIZADA` y se llamó directamente a
`validar_revision.validar()` contra esa ficha y el catálogo real. No se llamó
a `apply_revision()`, no se usó `dry_run=False`, no se hizo checkout y no se
persistió ninguna salida intermedia.

### Resultado individual de cada camino

| Medida | PDF digital | HTML digital |
|---|---:|---:|
| `revision_id` | `bolueta__24/08/2026__pdf_digital__91bd2489` | `bolueta__24/08/2026__html_digital__4e987c08` |
| Celdas normalizadas | 1.963 | 3.686 |
| Avisos del adaptador/validador | 0 | 0 |
| Claves duplicadas | 0 | 0 |
| Aceptadas | 1.963 | 3.686 |
| Rechazadas | 0 | 0 |
| Acción `actualizar` | 443 | 443 |
| Acción `conservar` | 1.520 | 3.243 |
| Acción `descartar` | 0 | 0 |
| `aplicable` | `True` | `True` |

El distinto número bruto de celdas no es una discrepancia de lectura. El PDF
solo permite recuperar glifos explícitos y produjo 1.786 `X`, 126 `M` y 51
`/`: 1.963 celdas. El HTML contiene exactamente esas mismas 1.963 claves y
valores explícitos, más 1.723 celdas con `data-st=''`. Los blancos digitales
se validan como `conservar`, de acuerdo con la regla común.

La lectura explícita completa también coincide antes de calcular el delta:
1.963 coincidencias de clave y valor, 0 claves exclusivas de un camino y 0
valores distintos.

### Comparación exacta de las propuestas `actualizar`

| Comparación | Celdas |
|---|---:|
| Propuestas por PDF digital | 443 |
| Propuestas por HTML digital | 443 |
| Misma clave y mismo valor | **443** |
| Solo en PDF digital | **0** |
| Solo en HTML digital | **0** |
| Misma clave pero valor distinto | **0** |

**No apareció el hallazgo grave:** no existe ninguna clave para la que ambos
caminos propongan valores diferentes. Los dos conjuntos de actualizaciones son
idénticos.

Como comprobación adicional, el desglose antes/después es el mismo en ambos:

| Transición | Celdas |
|---|---:|
| `P -> X` | 280 |
| `P -> M` | 52 |
| `P -> /` | 51 |
| `M -> X` | 32 |
| `/ -> X` | 16 |
| `? -> X` | 9 |
| `/ -> M` | 3 |
| **Total** | **443** |

La Fase 4 ya estableció que, de esas 443 propuestas HTML, las 411 celdas
documentadas como aplicadas aquel día estaban incluidas y coincidían en valor;
las 32 adicionales se explicaban por estados que habían llegado por otra vía
entre commits. La comparación actual añade la evidencia que faltaba: el camino
PDF digital corregido recupera las mismas 443, incluidas esas 32, sin ninguna
divergencia respecto al HTML.

## Discrepancias y observaciones adicionales

No se encontró ninguna discrepancia adicional de claves, valores, traducción,
aplicabilidad o duplicados entre los caminos PDF y HTML sobre este caso real.

Durante la comparación, la biblioteca de lectura emitió 19 avisos
`Could not get FontBBox from font descriptor because None cannot be parsed as
4 floats`; la lectura complementaria que comprobó el conjunto completo de
marcas explícitas repitió los mismos 19. Son avisos del descriptor tipográfico
del PDF, no rechazos del adaptador: ambas extracciones terminaron, las 1.963
marcas explícitas coincidieron una por una con el HTML y la validación tuvo 0
errores y 0 rechazos. Se documentan para no ocultar ruido diagnóstico de la
ejecución.

La única diferencia funcional conocida de la Fase 5 sigue siendo la ya
descrita para `antes=None`; no apareció otra durante la verificación empírica.

## Conclusión

El adaptador PDF digital y sus pruebas permanecen intactos y la suite completa
mantiene 524 tests sin fallos. Sobre los datos reales de Bolueta y contra la
misma ficha histórica, PDF y HTML producen un conjunto exactamente idéntico de
443 actualizaciones, con cero valores incompatibles para una misma clave.

Esto confirma la corrección del adaptador PDF digital como fallback y, a la
vez, mantiene la recomendación arquitectónica de preferir el HTML gemelo: el
HTML representa directamente las 3.686 celdas, mientras el PDF necesita la
lectura geométrica para recuperar las 1.963 marcas explícitas, aunque en este
caso corregido ambas vías hayan llegado al mismo resultado.
