# Prioridades desde la base de obra — diseño

**Fecha:** 11/08/2026
**Estado:** aprobado en brainstorming, pendiente de plan de implementación
**Alcance:** pestaña Prioridades del panel de obra, `priorizador_trabajos.py`,
`reglas/CATALOGO_TAJOS.json` y su propagación al generador de revisiones.

---

## 1. Qué se quiere y por qué

Una obra dura semanas, meses o años. El valor de este apartado es responder,
después de cada revisión y su actualización, a una sola pregunta:

> **¿Qué tajos se pueden ejecutar ahora, cuáles están bloqueados y por qué, y
> qué se desbloquea al terminar cada cosa?**

Prever el siguiente tajo es lo que permite llevar el orden de la obra hasta la
finalización. El enfoque es **eléctrico**: los tajos de albañilería, pladur,
fontanería o calefacción se modelan únicamente porque nos condicionan la
entrada, no para gestionarlos. No puede haber tubeado sin tabique, ni tabique
sin suelo.

Hoy la pestaña no puede responder a eso porque lee de la fuente equivocada.

---

## 2. Principio de arquitectura

> **La base de cada obra es el estado. El catálogo es la regla.**

La base (`ficha_obra.json`) dice qué existe y cómo está. El catálogo
(`reglas/CATALOGO_TAJOS.json`) dice en qué orden va cada tajo y qué exige qué.
Ninguno de los dos manda sobre todo.

Corolario permanente del entorno Sagarde: **toda información queda guardada en
una base de datos.** Nada vive solo en la cabeza de un script ni en un cálculo
intermedio.

---

## 3. Estado actual: hallazgos medidos (11/08/2026)

Todos verificados sobre los ficheros reales, no deducidos.

### 3.1 La base ya es sólida y el motor no la usa

| | Bolueta | Mungia | Gernika | Orueta | PRUEBA |
|---|---|---|---|---|---|
| Ubicaciones | 97 | 62 | 32 | 102 | 31 |
| Tajos | 38 | 38 | 38 | 40 | 38 |
| Celdas | 3686 | 2356 | 1216 | 4080 | 1178 |

Rejilla completa y sin huecos en las cinco: `celdas == ubicaciones × tajos`.
Cada celda guarda `{v: estado, f: fecha, r: revisión}`.

`generar_todos.py:916` sustituye **solo `historial[-1]`** por el snapshot de la
base. El priorizador recorre todo el historial, así que las revisiones
anteriores siguen entrando crudas del adaptador.

### 3.2 Consecuencia: Bolueta prioriza 4 viviendas que no existen

`estructura.exclusiones` de la base declara `PB/A`, `PB/B`, `PB/C` y `PB/D`
como *"la hoja la imprime pero la estructura confirmada no la incluye"*,
confirmado el 28/07/2026. Orueta declara 15 exclusiones más. **El priorizador
no lee ese apartado.**

- Las 152 celdas de PB del priorizador tienen `ultima_fecha` = 26/07/2026 (la
  revisión cruda). Ninguna del 28/07.
- **25 de las 26 preguntas pendientes** son sobre PB/A–D.
- **25 de las 44 filas** de "Qué hacer ahora" (57 %) y **100 de las 104
  unidades `VERIFICAR`** son de viviendas inexistentes.

La pregunta 26 (`NO_QUITAR_X`, embornado de planta 9) también es falsa: dice
que *"figuraba terminado y la siguiente revisión lo corrige"*, y la base tiene
esas celdas en `P` desde el 26/07, sin ninguna `X` previa.

**Las 26 preguntas de Bolueta son 26 falsos positivos.**

### 3.3 Y calla sobre lo que sí existe

`snapshot_desde_ficha` excluye `?` y `N` (`ficha_obra.py:241`), correcto para el
porcentaje. Pero el priorizador consume ese mismo snapshot, donde un `?` no es
"fuera del denominador": es **no existir**.

Bolueta tiene 190 `?` en exactamente 5 ubicaciones reales: `PB/Local 1`,
`PB/Local 2`, `1/Txoko`, `1/Gim.`, `1/Multiusos`. Ninguna aparece en Prioridades.

`97 − 5 + 4 = 96`, que es lo que ve el priorizador. La cuenta cuadra al detalle.

### 3.4 El recuento está inflado un 43 %

La agrupación cuenta una unidad por celda de la rejilla, así que un tajo de
edificio se multiplica por vivienda: `Cuarto técnico — 92 unidades` cuando hay
**uno**; `Montante eléctrica — 56`. Son 370 de las 851 unidades del panel.

### 3.5 El orden está declarado y el motor lo ignora

Orueta tiene 18 de sus 40 tajos con `orden: 9999` en la base. **14 de ellos sí
tienen orden real en el catálogo**: `ventilacion` 145, `cableado_extractor` 146,
`techos_wc` 240, `lucido_paredes` 255, `mecanismos_wc` 271, `mecanismos_pasillo`
272, `agujeros_focos_wc` 282, `cajas_techo_pasillo` 284, `pintura_pasillos` 290,
`pintura_wc` 290, `pintura_segunda` 290, `placas_tapas` 300, `focos_wc` 341,
`focos_pasillos` 342.

Los otros 4 son deriva de nombre entre base y catálogo:

| Base | Catálogo |
|---|---|
| `agujero_focos_pasillo` | `agujeros_focos_pasillo` |
| `focos_hab` | `focos_habitaciones` |
| `pintura_hab` | `pintura_habitaciones` |
| `placas_tps_cuadro` | *(no existe)* |

Además `pintura_segunda` y `placas_tapas` entraron duplicados con
`origen: revision_sin_confirmar` pese a estar ya definidos.

### 3.6 La cadena de otros gremios está sin modelar

**19 de los 39 tajos comunes no declaran ninguna dependencia**, y 12 de esos 19
son de otros gremios:

```
tubeado → tabicado                    ✓ declarado
tabicado → suelo                      ✗ Tabicado no tiene dependencias
primeras caras pladur → perfilado     ✗
segundas caras → primeras caras       ✗
pintura primera → techos / 2ª cara    ✗
pintura segunda → pintura primera     ✗
```

Sin esta cadena no hay previsión posible: el motor puede decir "el tubeado está
bloqueado por el tabicado" pero no "y el tabicado por el suelo, así que esto se
mueve cuando entre el solador".

### 3.7 Otros defectos medidos

- **Las 29 dependencias exigen `X` completo.** La escala `/ = 0,25` y
  `M = 0,60` existe en el motor y ninguna regla la usa.
- **La caducidad de 30 días es un interruptor global** calculado con
  `datetime.now()` en el momento de generar: el mismo dato produce paneles
  distintos según el día. Bolueta y Mungia están a 13 días, Orueta a 14 y
  Gernika a 16: en dos semanas las cuatro caen a la vez.
- **`orden` duplicado:** `montante_sscc` y `montante_general` comparten 50, y
  `montante_general` es el agregado histórico explícitamente no confirmado.
- **`_scope()` busca `"zona comun"`** y el catálogo escribe `"zonas comunes"`:
  esa mitad de la condición no se cumple nunca.
- **Truncado silencioso** a 200 bloques en `_agrupar_prioridades`.
- **Cero pruebas del motor de dependencias.** Las 9 de `test_catalogo_tajos.py`
  son de semántica del catálogo y de alias.

---

## 4. Decisiones tomadas

| # | Decisión |
|---|---|
| D1 | **El catálogo manda** sobre orden y dependencias. Un tajo nuevo en una base dispara una pregunta para actualizar el catálogo. |
| D2 | **`?` tiene sección propia "Sin revisar nunca"**, con KPI y ubicaciones. No se prioriza como ejecutable. `N` queda fuera del todo. |
| D3 | **Se cuenta según el ámbito del tajo:** vivienda → una por vivienda; zona común → una por planta; edificio → una para toda la obra. |
| D4 | **Se usan mínimos parciales** (`/`, `M`) solo donde Bixente los confirme uno a uno, y la fila bloqueada indica cuánto falta. |
| D5 | **La antigüedad es aviso graduado**, no interruptor. Nada se apaga solo. |
| D6 | **Obra sin base: no se calcula.** Mensaje explícito y cómo sembrarla. Recuento vacío, nunca cero. |
| D7 | **El catálogo es SIEMPRE AMPLIABLE**, con la ampliación como operación normal y prevista. |
| D8 | **Si el orden de un tajo no está claro, se pregunta.** Nunca `9999` silencioso ni orden inventado. |
| D9 | **Ante cualquier duda, preguntar.** No se deduce semántica de obra. |

---

## 5. Arquitectura

### 5.1 Flujo actual (dos caminos, gana el malo)

```
adaptador → historial crudo ──┬──→ ficha (base) ──→ KPIs, panel, informe
                              └──→ priorizador ────→ Prioridades      ✗
```

### 5.2 Flujo objetivo (uno solo)

```
adaptador → historial crudo → ficha (base) ─┬─→ KPIs, panel, informe
                                            └─→ priorizador → Prioridades
                    catálogo ──(orden + deps)──↗
```

### 5.3 El ciclo completo, con el generador dentro

```
CATALOGO_TAJOS.json ──┐
                      ├→ generar_todos.py → obras_revisiones.js
ficha_obra.json ──────┘                            ↓
        ↑                              generador_revisiones.html
        │                                          ↓
        │                                     hoja A4 PDF
        │                                          ↓ boli en obra
        └──── leer_hoja_marcada.py ←──────── escaneo
                      ↓
              priorizador → Prioridades
```

**El generador consume la salida del priorizador**, no el catálogo directamente:
`crear_registro_revision(obra, prioridades)` construye la lista de tajos de la
hoja desde `detalle_items`. Dos consecuencias:

1. Este cambio **propaga a la hoja impresa** y hay que verificarlo.
2. Hoy un tajo del catálogo que nunca haya aparecido en una revisión **no se
   imprime**, así que nunca se puede medir. Leyendo de la base —que tiene la
   rejilla completa de `tajos.aplicables`— pasará a imprimirse. El bucle
   catálogo → hoja → campo → base → prioridades se cierra solo.

La actualización automática no necesita trabajo extra: `generar_todos.py` ya
llama al priorizador en cada regeneración. Solo cambia de dónde lee.

---

## 6. Componentes

### 6.1 Se retira

**`_construir_estado()`** (≈110 líneas). Reconstruye el estado a partir de N
revisiones crudas; la base ya **es** ese estado, resuelto celda a celda, con
fecha y revisión de origen, con la norma de la última revisión aplicada y con
las exclusiones respetadas.

Con ella se van cuatro mecanismos que hoy producen exclusivamente falsos
positivos: detección de conflicto sobre `X`, `omitido_ultima`,
`ESTADOS_DUPLICADOS` y el cierre por fecha `forzar_historial_terminado_hasta`.

### 6.2 Se añade

**`estado_desde_ficha(ficha, catalogo)`** — recorre
`estructura.bloques → portales → plantas → ubicaciones`, salta las de
`estructura.exclusiones`, y para cada `(ubicación, tajo)` lee
`estados[clave] = {v, f, r}`. Produce el mismo diccionario que consumía el resto
del motor.

**`sembrar_reglas(ficha, catalogo)`** — en cada regeneración vuelca `orden`,
`deps`, `propiedad`, `ambito` y `fase` del catálogo sobre `tajos.detalle` de la
base. Lo que el catálogo no conoce **no se inventa**: sale como pregunta.

**`prevision_desbloqueos(detalle)`** — ver sección 9.

**`verificar_rejilla(ficha)`** — comprueba que la base es una rejilla densa
(`celdas == ubicaciones × tajos`) y devuelve el aviso con las cifras si no
cuadra. Ver §10.

### 6.3 Se conserva intacto

Resolución por catálogo y alias, cascada de clasificación, agrupado e
inventario. Es la parte que funciona y la única con pruebas.

### 6.4 Correcciones menores incluidas

Los defectos de §3.7 que no dependen de ninguna decisión pendiente se corrigen
en este mismo trabajo, cada uno con su prueba:

- **`orden` duplicado 50** entre `montante_sscc` y `montante_general`. Además
  hay que decidir qué se hace con `montante_general`, que es el agregado
  histórico explícitamente no confirmado: o recibe orden propio o se retira del
  catálogo común. **Se pregunta antes de tocarlo.**
- **La guarda muerta de `_scope()`**: busca `"zona comun"` y el catálogo escribe
  `"zonas comunes"`. Se corrige la comparación o se elimina la condición, con
  una prueba que fije el comportamiento esperado.
- **El truncado silencioso a 200 bloques** pasa a avisar en pantalla cuando
  recorta, con el número de filas ocultas.
- **La caducidad** deja de usar `datetime.now()` dentro del cálculo: la fecha de
  referencia se pasa como parámetro para que el resultado sea reproducible.

---

## 7. Las reglas de prioridad, escritas

Un tajo se clasifica en una y sólo una categoría. **El orden de evaluación
manda**:

| # | Si… | Categoría |
|---|---|---|
| 1 | el estado es `N` | **no entra** |
| 2 | el estado es `?` | **Sin revisar nunca** |
| 3 | el estado es `X` | **Terminado** (se conserva siempre, al final) |
| 4 | la propiedad no es `propio` | **Otros gremios** |
| 5 | el tajo no está en el catálogo | **Duda** + pregunta |
| 6 | alguna dependencia no llega a su mínimo | **Bloqueado** |
| 7 | en cualquier otro caso | **Viable** |

Dentro de Viables el orden es:

**`orden` del catálogo → ámbito (vivienda → zona común → edificio) → planta y
unidad naturales.**

No se calcula por número de bloqueos ni por porcentaje: es la secuencia real de
obra escrita en el catálogo, del 10 (Tabicado) al 330 (Iluminación de rellanos).

La antigüedad de la revisión **no cambia ninguna categoría**: sale como aviso
con fecha y días.

---

## 8. El catálogo como base de tajos ampliable

### 8.1 Qué es

`reglas/CATALOGO_TAJOS.json` v1.3. Hoy: 39 tajos comunes + 18 propios de Orueta.
Cada tajo declara `id`, `nombre`, `aliases`, `propiedad`, `ambito`, `orden`,
`fase`, `deps`, `estado_m`, `estado_x`, `impacto`.

Estado de salud verificado: 0 dependencias colgando, 0 colisiones de alias, 0
dependencias hacia el futuro, 0 tajos sin alias.

### 8.2 SIEMPRE AMPLIABLE

Ampliar el catálogo es una operación **normal y prevista**, no un parche. Un
tajo nuevo en cualquier obra se define una vez ahí y sirve para las 21.

El bucle de ampliación:

1. Aparece un tajo en una hoja que el catálogo no reconoce.
2. `actualizar_desde_snapshot` lo registra en la base con
   `origen: revision_sin_confirmar`.
3. Prioridades lo muestra como **pregunta**, con nombre, ubicaciones e ids
   parecidos del catálogo, para decidir si es alias o tajo nuevo.
4. Bixente confirma: se añade al catálogo con su orden, propiedad, ámbito y
   dependencias.
5. La siguiente regeneración lo siembra en la base y lo imprime en la hoja.

### 8.3 Invariantes que se prueban

- Ningún tajo del catálogo sin `orden`, `propiedad` y `ambito`.
- Ningún `orden` duplicado.
- Ninguna dependencia apuntando a un id inexistente.
- Ningún alias resolviendo a dos tajos distintos.
- Ningún tajo de la base con `orden: 9999` sin una pregunta abierta que lo
  acompañe.

### 8.4 Completar la cadena de otros gremios

Los 19 tajos sin dependencias se revisan uno a uno con Bixente. **No se
inventa ninguna:** la que no se pueda confirmar se queda sin declarar y sale
como pregunta.

Los gremios ajenos se modelan **solo hasta donde nos condicionan la entrada**.

### 8.5 Tabiquería: qué cierra el paso a qué (confirmado 11/08/2026)

Un tabique es un tabique sea de ladrillo o de pladur, pero **no cierran las
mismas cosas**. Norma de obra confirmada por Bixente:

> En obra moderna el ladrillo se usa solo para las separaciones entre
> viviendas distintas y con las zonas comunes; el pladur para los interiores
> de cada vivienda.

De ahí la regla de dependencia:

| Lo que se va a ejecutar | Lo bloquea |
|---|---|
| Tajo de **zona común** | `tabicado` (ladrillo) |
| Tajo de **interior de vivienda** | `primera_cara_pladur` (primera placa de yeso) |

Esto obliga a revisar dependencias ya declaradas. Dos casos concretos
detectados, **ambos a confirmar uno a uno antes de tocar nada**:

- `tubeado` (vivienda, orden 130) depende hoy de `tabicado`. Por la regla
  debería depender de `primera_cara_pladur`.
- `tubeado_zzcc` (zona común, orden 60) no declara ninguna dependencia. Por la
  regla debería depender de `tabicado`.

**No se aplica en bloque.** Cada reasignación se pregunta y se confirma por
separado, y la que no se confirme se queda como está con su pregunta abierta.

### 8.6 Los estados son porcentaje del propio tajo, nunca trabajo distinto

Norma confirmada por Bixente (11/08/2026):

| | Significa |
|---|---|
| `/` | tajo empezado |
| `M` | tajo con un mínimo del 50 % |
| `X` | tajo zanjado |

Los tres miden **el mismo trabajo, a distinto porcentaje de su propio alcance**.
Nunca se usan para codificar trabajos diferentes.

> **Si `M` sería un tajo y `X` otro, no son estados: son dos tajos.**

Ahora que el entorno está digitalizado se pueden especificar los tajos con más
detalle, así que la respuesta a "este estado significa otra cosa" es **añadir un
tajo nuevo al catálogo**, no reinterpretar el estado. Es la razón operativa de
que el catálogo sea SIEMPRE AMPLIABLE.

Consecuencias directas:

- No se mezclan datos de trabajos distintos bajo un mismo tajo.
- Un estado nunca se traduce entre tajos: cuando un tajo se divide, cada uno
  arranca con su propia escala y solo se traduce lo que tenga equivalencia
  histórica confirmada.
- Los valores numéricos (`/ = 0,25`, `M = 0,60`, `X = 1,0`) son los mismos para
  todos los tajos, y las descripciones físicas de un estado solo explican mejor
  el trabajo hecho: no crean otro porcentaje.

Esto ya está recogido en `reglas/CRITERIOS_PRIORIZACION_TRABAJOS.md` bajo
"Especialización de tajos"; aquí queda elevado a norma que las pruebas
comprueban.

---

## 9. Previsión del siguiente tajo

Sección nueva de la pestaña, en dos sentidos:

**Hacia atrás — qué me falta.** Para cada tajo bloqueado, qué dependencia falta
y con qué estado va (`Tubeado interior: M — falta X`), y en qué ubicaciones.

**Hacia delante — qué libero.** Para cada tajo pendiente, cuántas unidades
propias se desbloquean al terminarlo, ordenado por ese número.

Ahí es donde una obra de meses gana: saber que acabar el suelo de tres plantas
libera 40 viviendas de tubeado.

---

## 10. Errores y casos límite

- **Obra sin base** → no se calcula. *"Esta obra no tiene base de datos
  todavía"* y cómo sembrarla.
- **Base incompleta** → debe cumplirse `celdas == ubicaciones × tajos`. Si no
  cuadra, se avisa con las cifras en vez de calcular sobre datos parciales.
- **Tajo en la base que el catálogo no conoce** → pregunta con ids parecidos.
  Nunca se le inventa un orden.
- **Dependencia que apunta a un tajo que esa obra no tiene** → hoy vale 0 y
  bloquea para siempre en silencio; pasa a ser aviso explícito.
- **Orueta** es el caso delicado. Antes de retirar el cierre por fecha del
  24/09/2025 hay que confirmar que ya está materializado en la base (2314 `X`,
  1758 `N`, 8 `P`), y que las excepciones de los apartamentos 1 y 2 de PB se
  siguen inyectando.

---

## 11. Pruebas y verificación

Pruebas nuevas con `unittest` de la biblioteca estándar —sin dependencias
nuevas—, **probadas por mutación**: romper el código a propósito y comprobar
que la prueba se entera.

Cubren lo que hoy no cubre nadie: la cascada de clasificación completa, las
exclusiones, `?` y `N`, el conteo por ámbito, los mínimos parciales, la
caducidad como aviso, los invariantes del catálogo y la paginación de la hoja
generada.

### Verificación antes/después, con cifras

| | Antes | Después esperado |
|---|---|---|
| Preguntas de Bolueta | 26 | 0 (las 26 son falsas) |
| Unidades `VERIFICAR` Bolueta | 104 | 0 |
| Ubicaciones vistas Bolueta | 96 (4 fantasma) | 97 |
| Ubicaciones `?` visibles Bolueta | 0 | 5 |
| Tajos de Orueta en `9999` | 18 | 4, y con nombre y pregunta |
| Unidades no-vivienda infladas | 370 de 851 | contadas por ámbito |
| Mungia 80.1 · Gernika 76.3 · Bolueta 43.5 · Orueta 99.7 | | **sin moverse** |

El último renglón es la prueba de que no hay efecto colateral: Prioridades no
toca los KPIs. Además hay que comprobar que la hoja A4 generada mantiene sus
invariantes de paginación.

Todo cambio se reporta a Bixente con el antes/después. Aplicar en silencio una
corrección que mueve cifras es repetir el problema desde el otro lado.

---

## 12. Mapa mental de datos

Existe: `_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`, 619 líneas, publicado en
`main` el 10/08/2026 (`51fe4b0`).

**Está desfasado.** Dice *"tres `ficha_obra.json` (Gernika, Mungia y Bolueta)…
Obispo opera sin ficha"*; hoy hay cinco bases y Orueta tiene la suya.

Actualizarlo entra en este trabajo: debe reflejar dónde vive cada dato que usa
la interfaz —una base por obra, el catálogo general, los sidecars, las memorias
y las salidas del generador— y el ciclo de la sección 5.3.

---

## 13. Fuera de alcance

- La pestaña **Riesgos** (analizada, sin decisión tomada).
- Los KPIs, el panel de avance y el informe ejecutivo.
- Migrar `estructura.exclusiones` o `excepciones` del catálogo a otro sitio.
- Refactorizar el adaptador o el lector de hojas.

---

## 14. Riesgos abiertos

1. **Orueta y el cierre por fecha.** Si no está materializado en la base,
   retirar el mecanismo movería el 99.7. Verificar antes de tocar.
2. **El generador depende del priorizador.** Cambiar la salida cambia la hoja
   impresa. Las pruebas de paginación deben pasar sin retoques.
3. **`Actualizar_Sagarde.bat` hace `git add -A`.** No lanzarlo con trabajo en
   vuelo, y restaurar cualquier fichero mutado para una verificación.
4. **Reasignación de dependencias por tabiquería** (sección 8.5). La regla está
   confirmada, pero cada tajo afectado se revisa por separado: cambiar
   `tubeado → tabicado` por `tubeado → primera_cara_pladur` mueve la
   clasificación de muchas celdas a la vez. Reportar antes/después por obra.
