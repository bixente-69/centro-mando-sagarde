# Mapeo CARDIVA 01–09

## Correspondencia con la plantilla

| Punto | Contenido | Tablas Word |
|---|---|---|
| 01 | Batería de condensadores | 3–5 |
| 02 | Protección contra el rayo y puesta a tierra | 6–7 |
| 03 | Cuadros eléctricos, medidas, analizador y SAI | 8–13 |
| 04 | Baja tensión por zonas y automatismos | 14–16 |
| 05/06 | Instalaciones de alumbrado | 17–19 |
| 07 | Deficiencias y acciones | 20–21 |
| 08 | Materiales y evidencias | 22–23 |
| 09 | Resultado, cierre, técnicos y sello | 24–25 |

## Derivación de 07

- Crear una `D-xx` por cada incidencia técnica independiente.
- Vincular cualquier resultado `DEF` con una `D-xx`.
- No crear una deficiencia a partir de una recomendación si el equipo se declara conforme.
- Si una nota manuscrita clara contradice una marca `OK` y contiene una negación técnica explícita —por ejemplo, `no funciona`, `no actúa` o `no dispara`—, la nota prevalece: registrar `DEF` y crear su `D-xx`.
- Si la nota contradictoria es ilegible o ambigua, detener el proceso y preguntar siempre al usuario. No conservar `OK`, registrar `DEF`, asignar `N/R` ni generar el informe hasta recibir la aclaración.
- Una confirmación posterior del usuario resuelve la contradicción y se considera evidencia suficiente para registrar el estado confirmado.
- Una lectura numérica claramente incoherente con las demás lecturas del mismo equipo debe conservarse tal como está escrita y generar una `D-xx` de verificación; no corregirla por intuición. La acción será repetir la medida y diagnosticar únicamente si se confirma.
- Asignar criticidad:
  - `A`: riesgo eléctrico, protección que no actúa, cortocircuito o indisponibilidad crítica.
  - `M`: fallo múltiple o impacto operativo relevante.
  - `B`: fallo unitario sin riesgo inmediato.

## Derivación de 08

- Crear materiales solo cuando la reparación requiera sustitución.
- Mantener cantidades y modelos exactamente como aparecen en la fuente.
- En sumas manuscritas corregidas, distinguir entre un sumando sustituido y el total. Contrastar cada sumando con las marcas del plano o croquis; por ejemplo, `6 + 13 + 2` son 21 unidades, no 13.
- Si el plano no permite resolver de forma fiable una cantidad tachada o sobrescrita, detener el proceso y preguntar siempre al usuario; no calcular ni registrar un total supuesto.
- Escribir `confirmar modelo` si la referencia no se ha verificado.
- Crear una referencia `F-xx` por cada `D-xx`.
- Crear una página fotográfica por cada referencia, aunque la fotografía se vaya a pegar manualmente.

## Derivación de 09

- Sin deficiencias: `CONFORME` y `CERRADO`.
- Con deficiencias: `CONDICIONADO` y `CERRADO CON N DEFICIENCIAS ABIERTAS`.
- Resumir primero los sistemas conformes y después las actuaciones pendientes.
- Priorizar en la próxima actuación las deficiencias `A`, después `M` y finalmente `B`.
- Citar los partes o códigos externos relacionados.

## Datos ausentes

- `N/R`: no registrado en la fuente.
- `N/A`: no aplicable.
- `PENDIENTE`: actuación o material todavía no ejecutado.
- No inferir horas, contactos, lecturas, modelos ni estados ausentes.
- `N/R` no debe utilizarse para ocultar una lectura dudosa: si existe una marca o anotación pero no se entiende con certeza, preguntar siempre antes de continuar.
