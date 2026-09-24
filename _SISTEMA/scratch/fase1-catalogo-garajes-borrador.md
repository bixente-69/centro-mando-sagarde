# Fase 1 — Borrador de catálogo de tajos de garaje (fichero de trabajo)

No es el JSON final. Es el borrador que Claude diseña para que agy lo
transcriba a `reglas/CATALOGO_TAJOS.json` (ver
`2026-09-24-ampliacion-garajes-plan.md`, Fase 1). Fuente: §4 y §5 de
`2026-09-24-ampliacion-garajes-design.md`.

## Decisiones de diseño tomadas al escribir esta tabla (no estaban ya escritas tal cual)

Estas tres son la parte de más criterio de toda la Fase 1. Si Bixente
discrepa de alguna, se corrige aquí y se retranscribe — el JSON real
todavía no existe.

1. **`ambito` = `zona_comun` para todos los tajos de garaje.** El diseño
   (§3.2) deja el garaje sin nivel de vivienda; `AMBITO_ORDEN` en
   `priorizador_trabajos.py` (línea 25) es un diccionario sin `.get()` que
   solo conoce `vivienda`/`zona_comun`/`edificio` — un valor `ambito`
   nuevo como `"garaje"` reventaría con `KeyError` en el primer intento de
   ordenar. `zona_comun` es lo que ya existe y ninguna zona de garaje es
   una unidad privada tipo vivienda.
2. **Cableado es un tajo compartido por zona/ruta, NO uno por tipo de
   equipo.** El texto de §5.5 ("Cableado → Colocación → Embornado...
   Tajos independientes por tipo de equipo") se puede leer como que las
   tres fases son por tipo de equipo. Pero eso choca con una decisión
   posterior y explícita de Bixente sobre viales, ya registrada en
   memoria: *"ponemos un solo cableado por zona que abarque los tres
   tipos (menos tajos)"*. Se resuelve a favor de esa instrucción, más
   tardía y más explícita: cableado es UNO por ruta (empotrada/vista/vial),
   compartido; solo Colocación y Embornado son por tipo de equipo — es lo
   que de verdad varía físicamente (terminar un downlight no es terminar
   un detector). **Pendiente de confirmar con Bixente.**
3. **Colocación de equipos depende solo de Pintura 1ª de su rama, nunca
   del cableado directamente.** Aplica la misma simplificación que el
   diseño ya adoptó explícitamente para Lucido (§4.1, "decisión de
   simplicidad": Lucido depende solo de Tabicado, nunca del tubeado de
   Sagarde) y que el propio catálogo real de vivienda ya usa (`pintura_primera`
   depende solo de `techos`+`enchapado`, nunca de `cableado`). Evita que
   Colocación necesite una variante por cada ruta (empotrada/vista/vial) del
   cableado, que habría triplicado el número de tajos de equipo sin más
   beneficio real. Se pierde algo de precisión (si el cableado se retrasa,
   el motor no avisará) a cambio de un catálogo bastante más pequeño —
   mismo criterio de "simplicidad ante todo" ya aplicado dos veces en este
   diseño.

## Hallazgo técnico nuevo, verificado leyendo `priorizador_trabajos.py` (24/09/2026)

`_clasificar_detalle` construye `tajos_de_la_obra` (línea 484) como el
conjunto de `task_id` que existen **en toda la obra**, no por ubicación. El
bucle de deps (línea 560-572) solo salta una dependencia (`continue`, no
bloquea) si ese `id` **no existe en ningún sitio de la obra entera**. Si el
`id` existe en la obra pero no en la ubicación concreta que se está
evaluando, `_buscar_dep` devuelve `None` (línea 472-474) y bloquea para
siempre — no hay excepción para "esta zona en concreto no tiene ese tajo".

**Consecuencia para el catálogo de garaje:** como un garaje reúne zonas muy
distintas en la misma obra (viales, trasteros, cuartos técnicos...), un tajo
de un tipo de zona nunca puede depender de un tajo que solo existe en OTRO
tipo de zona, aunque ambos existan "en la obra" — porque en la ubicación
concreta que depende, esa celda sencillamente no está. Ya era la razón por
la que las rutas empotrada/vista no podían cruzar sus cadenas (§4.1); esta
tabla generaliza la misma regla a viales vs. recintos y a cada tipo de
equipo. Cada cadena de `deps` de esta tabla se mantiene dentro de su propio
tipo de zona a propósito. Añadir esto a §4.1 del diseño cuando se confirme
la tabla.

## Convenciones de la tabla

- Todos: `ambito: zona_comun`. `estado_m` es literalmente `"Más del 50 %"`
  en todos salvo que se indique otra cosa (mismo valor que usa casi todo el
  catálogo real de vivienda).
- `propiedad`: **propio** (Sagarde) salvo que se indique externo/coordinacion.
- IDs con prefijo `garaje_` en todos los casos, para que nunca puedan
  coincidir por accidente con un id de vivienda ya existente.

## Tabla completa (42 tajos)

### A. Obra civil (500-519)

| id | nombre | orden | propiedad | deps | estado_x | impacto |
|---|---|---|---|---|---|---|
| garaje_tabicado | Tabicado de garaje | 500 | externo | [] | Tabicado terminado | Sin separaciones no se inicia nada del resto en esa zona. |
| garaje_lucido | Lucido de garaje | 505 | externo | garaje_tabicado≥1 | Paredes lucidas | Depende solo de tabicado, nunca del tubeado de Sagarde (decisión de simplicidad, §4.1). |
| garaje_falso_techo | Falso techo de garaje | 510 | externo | garaje_tabicado≥1 | Falso techo terminado | Si aplica en esa zona (trasteros/cuartos técnicos/rellano); rama independiente de lucido. |
| garaje_raseado_viales | Raseado/yeso de viales | 515 | externo | [] | Raseado o yeso terminado | Acabado del forjado visto en viales; no hay tabicado ni lucido que lo condicione. |

### B. Tubeado y cableado — tres rutas independientes (520-549)

| id | nombre | orden | deps | estado_x | impacto |
|---|---|---|---|---|---|
| garaje_tubeado_emp | Tubeado empotrado de garaje | 520 | garaje_tabicado≥1 | Tubeado terminado | Ruta empotrada: va antes que el lucido en obra real, pero no depende de él (§4.1). |
| garaje_cableado_emp | Cableado empotrado de garaje | 525 | garaje_tubeado_emp≥1 | Cableado terminado | — |
| garaje_tubeado_visto | Tubeado visto de garaje | 530 | garaje_lucido≥1 | Tubeado terminado | Ruta vista: aquí sí depende del lucido — el tubo de superficie se monta sobre la pared ya acabada. |
| garaje_cableado_visto | Cableado visto de garaje | 535 | garaje_tubeado_visto≥1 | Cableado terminado | — |
| garaje_tubeado_vial | Tubeado de viales | 540 | [] | Tubeado terminado | Raíz propia de los viales; no espera a raseado (superficies distintas). |
| garaje_cableado_vial | Cableado de viales | 545 | garaje_tubeado_vial≥1 | Cableado terminado | — |

### C. Pintura — dos ramas (550-559)

`display_group: garaje_pintura` en las 4 filas de pintura (1ª y 2ª), igual
patrón que `pintura`/`techos` en el catálogo real.

| id | nombre | orden | deps | estado_x |
|---|---|---|---|---|
| garaje_pintura_1_recinto | Pintura de garaje (recintos) — 1ª mano | 550 | garaje_lucido≥1 | Primera mano terminada |
| garaje_pintura_1_vial | Pintura de garaje (viales) — 1ª mano | 555 | garaje_raseado_viales≥1 | Primera mano terminada |

(pintura 2ª va en el bloque F, después de colocación, para que el orden
numérico siga aproximadamente la secuencia real de obra igual que hace
vivienda con `pintura_segunda` en 290 tras `mecanizado` en 270)

### D. Colocación de equipos (560-579)

Cada uno depende solo de la pintura 1ª de su propia rama (recinto o vial) —
ver decisión 3 arriba. `enchufe` es propio de cuartos técnicos, sin variante
de vial.

| id | nombre | orden | deps | estado_x |
|---|---|---|---|---|
| garaje_alum_fijo_coloc_recinto | Colocación alumbrado fijo (recintos) | 560 | garaje_pintura_1_recinto≥1 | Pantallas colocadas |
| garaje_alum_fijo_coloc_vial | Colocación alumbrado fijo (viales) | 561 | garaje_pintura_1_vial≥1 | Pantallas colocadas |
| garaje_alum_temp_coloc_recinto | Colocación alumbrado temporizado (recintos) | 562 | garaje_pintura_1_recinto≥1 | Detectores/pantallas colocados |
| garaje_alum_temp_coloc_vial | Colocación alumbrado temporizado (viales) | 563 | garaje_pintura_1_vial≥1 | Detectores/pantallas colocados |
| garaje_emergencia_coloc_recinto | Colocación luminarias de emergencia (recintos) | 564 | garaje_pintura_1_recinto≥1 | Luminarias colocadas |
| garaje_emergencia_coloc_vial | Colocación luminarias de emergencia (viales) | 565 | garaje_pintura_1_vial≥1 | Luminarias colocadas |
| garaje_enchufe_coloc | Colocación de enchufe de cuarto técnico | 566 | garaje_pintura_1_recinto≥1 | Enchufe colocado |

### E. Cuadros — genérico, se repite por zona vía la ficha (580-609)

Un cuadro concreto no es un id distinto: es este mismo grupo de tajos
aplicado a la zona (cuarto técnico) donde vive ese cuadro — el nivel de
`zona` en `ficha_garajes.json` ya distingue "Cuadro RITI" de "Cuadro
Centralización" sin que el catálogo necesite un id por cuadro (mismo
patrón que `cuadro_mecanizado` en vivienda, un solo id repetido por
vivienda).

| id | nombre | orden | deps | estado_x | impacto |
|---|---|---|---|---|---|
| garaje_cuadro_tubeado_cableado | Tubeado y cableado hasta cuadro secundario | 580 | garaje_tabicado≥1 | Alimentación tendida | Desde el Cuadro General de Garaje. Todo cuadro lo lleva, sea o no nuestro por dentro (§5.6). |
| garaje_cuadro_colocacion | Colocación y mecanizado de cuadro propio | 585 | garaje_cuadro_tubeado_cableado≥1, garaje_pintura_1_recinto≥1 | Cuadro colocado y mecanizado | Solo si el cuadro es nuestro por dentro (RITI, Cuadro Eléctrico General...). |
| garaje_cuadro_embornado | Embornado de cuadro propio | 590 | garaje_cuadro_colocacion≥1, garaje_pintura_2_recinto≥1 | Embornado terminado | — |
| garaje_cuadro_rotulacion | Rotulación de cuadro propio | 595 | garaje_cuadro_embornado≥1 | Cuadro rotulado | Solo si el cuadro es nuestro por dentro. |
| garaje_cuadro_equipo_tubeado_cableado | Tubeado y cableado del cuadro al equipo que controla | 600 | garaje_cuadro_colocacion≥1 | Alimentación al equipo tendida | Solo cuando el cuadro es nuestro por dentro (bomba, ventilador...); no aplica a Ventilación/Bombas/Aerotermia/CO2/PCI/Ascensor con cuadro ajeno. |

### F. Pintura 2ª y embornado de equipos (610-649)

| id | nombre | orden | deps | estado_x |
|---|---|---|---|---|
| garaje_pintura_2_recinto | Pintura de garaje (recintos) — 2ª mano | 610 | garaje_pintura_1_recinto≥1 | Segunda mano terminada |
| garaje_pintura_2_vial | Pintura de garaje (viales) — 2ª mano | 615 | garaje_pintura_1_vial≥1 | Segunda mano terminada |
| garaje_alum_fijo_embornado_recinto | Embornado alumbrado fijo (recintos) | 620 | garaje_alum_fijo_coloc_recinto≥1, garaje_pintura_2_recinto≥1 | Embornado terminado |
| garaje_alum_fijo_embornado_vial | Embornado alumbrado fijo (viales) | 621 | garaje_alum_fijo_coloc_vial≥1, garaje_pintura_2_vial≥1 | Embornado terminado |
| garaje_alum_temp_embornado_recinto | Embornado alumbrado temporizado (recintos) | 622 | garaje_alum_temp_coloc_recinto≥1, garaje_pintura_2_recinto≥1 | Embornado terminado |
| garaje_alum_temp_embornado_vial | Embornado alumbrado temporizado (viales) | 623 | garaje_alum_temp_coloc_vial≥1, garaje_pintura_2_vial≥1 | Embornado terminado |
| garaje_emergencia_embornado_recinto | Embornado luminarias de emergencia (recintos) | 624 | garaje_emergencia_coloc_recinto≥1, garaje_pintura_2_recinto≥1 | Embornado terminado |
| garaje_emergencia_embornado_vial | Embornado luminarias de emergencia (viales) | 625 | garaje_emergencia_coloc_vial≥1, garaje_pintura_2_vial≥1 | Embornado terminado |
| garaje_enchufe_embornado | Embornado de enchufe de cuarto técnico | 626 | garaje_enchufe_coloc≥1, garaje_pintura_2_recinto≥1 | Embornado terminado |

### G. Cuartos técnicos específicos — tierras y centralización (650-669)

| id | nombre | orden | deps | estado_x | impacto |
|---|---|---|---|---|---|
| garaje_tierras_general | Tierras — llegada y embornado en Centralización | 650 | garaje_tabicado≥1 | Tierras embornadas en Centralización | Una sola vez por garaje; vive en la zona de Centralización. |
| garaje_tierras_derivacion | Derivación de tierra de cuarto técnico | 655 | garaje_tabicado≥1 | Derivación embornada | Una por cada cuarto técnico (achique, ventilación, aerotermia, sala de calderas...), distinta de la general. |
| garaje_centralizacion_modulos | Colocación de módulos de contadores | 660 | garaje_pintura_1_recinto≥1 | Módulos colocados | — |
| garaje_centralizacion_derivaciones | Derivaciones individuales — centralización y embornado | 665 | garaje_centralizacion_modulos≥1, garaje_pintura_2_recinto≥1 | Derivaciones centralizadas y embornadas | — |
| garaje_centralizacion_lga | Acometida LGA desde CGP de calle | 669 | garaje_tabicado≥1 | Tubeado, cableado y embornado terminados | Tratada como un único tajo autocontenido en Centralización a propósito — no depende del tajo de vial aunque discurra por ahí, para no cruzar zonas (mismo motivo que §5.3). |

### H. Puerta de acceso y otros (670-689)

| id | nombre | orden | propiedad | deps | estado_x | impacto |
|---|---|---|---|---|---|---|
| garaje_puerta_alimentacion | Alimentación de cuadro de puerta de acceso | 670 | propio | garaje_tubeado_vial≥1 | Alimentación terminada | Vive en la zona Rampa (ruta de vial). Siempre nuestra. |
| garaje_puerta_mecanizado | Mecanizado de puerta de acceso | 675 | coordinacion | garaje_puerta_alimentacion≥1 | Semáforo/llaves/detectores instalados | Puede ser del instalador de la puerta; en catálogo pero no marcado por defecto. |
| garaje_irve_preinstalacion | Preinstalación vehículo eléctrico (IRVE) | 680 | propio | garaje_tubeado_vial≥1 | Bandeja/canaleta reservada hasta última plaza | Un único tajo básico; cargadores concretos fuera de v1. |
| garaje_telco_transito | Telecomunicaciones de tránsito | 685 | propio | garaje_tubeado_vial≥1 | Tubo/bandeja de tránsito terminado | Solo cuando el garaje es paso entre edificios o entrada desde calle. |

## Recuento

**42 tajos nuevos**, por bloque: A (civil) 4 + B (tubeado/cableado) 6 +
C (pintura 1ª) 2 + D (colocación) 7 + E (cuadros) 5 + F (pintura 2ª +
embornado) 9 + G (cuartos técnicos) 5 + H (puerta/otros) 4 = 42.

## Pendiente antes de que agy transcriba

Ninguno bloqueante, pero si Bixente quiere corregir algo de las 3 decisiones
de arriba, es el momento — después de transcribir a JSON el coste de
cambiarlo ya no es solo de este fichero.
