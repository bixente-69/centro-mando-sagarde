# El ciclo cerrado: la IA ya lee la hoja marcada

Escrito el 05/08/2026. Sustituye como referencia de estado a
`2026-08-04-estado-y-siguiente-paso.md`, que queda como histórico.

El diseño está en
`docs/superpowers/specs/2026-08-04-lectura-hojas-revision-design.md` y se ha
seguido tal cual, salvo donde la realidad obligó a cambiarlo (§4).

---

## Los 5 pasos del ciclo

| paso | estado |
|---|---|
| 1 · La app genera la hoja **desde la base** | ✅ |
| 2 · Bixente marca en obra | ✅ |
| 3 · Escanea, o marca con pen digital | ✅ |
| 4 · **La IA traduce lo marcado** | ✅ **05/08/2026** |
| 5 · Eso alimenta la base | ✅ |

## 1. Qué se ha construido

| fichero | qué hace |
|---|---|
| `rejilla_hoja.py` | resuelve por geometría qué celda es cada posición. Común |
| `alta_obra_desde_hoja.py` | da de alta una obra desde su hoja **en blanco** |
| `leer_hoja_marcada.py` | lee la tinta de una hoja **marcada** y actualiza la ficha |

Sin dependencias nuevas. 168 pruebas en verde (eran 145).

El lector va en **dos fases**, `--preparar` y `--aplicar`, con la
clasificación por medio. No es un detalle de implementación: es la frontera
entre lo que resuelve el código (qué celda es) y lo que resuelve la vista (qué
letra hay). Juntarlas en un solo paso borraría esa frontera.

## 2. La verificación que propuso Bixente, y su resultado

1. Alta de `OBRA PRUEBA` desde su hoja en blanco → 2 bloques, 3 portales,
   **31 ubicaciones**, 38 tajos, 1.178 celdas, todas `?`.
2. Segunda hoja, marcada con pen digital → **82 celdas con tinta**.
3. El lector encuentra **exactamente** esas 82: 81 marcas (70 `X`, 6 `M`,
   5 `/`) y 1 descartada a mano.
4. Ida y vuelta: sidecar → ficha → hoja regenerada trae esas **81
   precargadas**. Ni una más, ni una menos.
5. Las 4 obras reales no se mueven: 0 campos distintos en `resumen_obras.json`
   salvo la marca de tiempo `generado`.

## 3. Un fallo latente que destapó la obra de prueba

`generar_todos.py` leía `bloques_ficha[0]` y **descartaba el resto en
silencio**. Con la hoja de 2 bloques de OBRA PRUEBA se habrían perdido 10
ubicaciones —incluidos LOCALES y la única planta 3ª— sin un solo error.

Las 4 obras con ficha tienen 1 bloque, por eso llevaba ahí sin verse. Ahora se
recorren todos los bloques; el contador de portales es global, así que para
una obra de un bloque produce exactamente los mismos ids que antes. Norma de
Bixente, textual: *"tiene que regirse siempre por el diseño de la hoja
generada, si tiene un bloque uno, si tiene 15 pues 15"*.

## 4. Dónde la realidad corrigió a la spec

- **La spec daba por hecho que un escaneo no tiene capa de texto.** Cierto,
  pero el caso frecuente hoy es el PDF *digital* marcado con pen: la tinta
  viene como anotaciones `Ink` con vértices, y ahí el reparto de puntos entre
  celdas resuelve el problema sin restar imágenes.
- **Un trazo NO es una celda, y es peor de lo que decía la spec.** El de OBRA
  PRUEBA medía 300×253 px con 724 puntos y cruzaba 51 celdas. La anotación
  dice dónde mirar; deciden los puntos.
- **La memoria decía que las hojas HTML no se podían parsear.** Era cierto
  para el formato anterior al 25/07/2026; el actual trae 1216 `data-k`
  estáticos. Verificar antes de descartar un camino.

## 4bis. Qué es el 100 %, cerrado con Bixente el mismo día

> *"Yo entiendo por 100 % acabada cuando todos los tajos que se han definido
> para ella se encuentran acabados. La pega no es que no esté revisada, sí lo
> está, lo que pasa es que ese tajo no ha comenzado. El no tener ninguna marca
> no significa que no se haya revisado, es que ni siquiera existe."*

Una obra dura meses: empiezan unos tajos y otros se hacen encima de los ya
hechos, muchos casi al final. Así que **una casilla vacía de una hoja que sí
se llevó a obra es un dato**, no una laguna: ese tajo no ha empezado.

El motor ya calculaba bien (`X`=1, `M`=0.6, `/`=0.25, vacío=0, y `N` fuera del
denominador). Lo que estaba mal era el dato guardado: el lector dejaba esas
celdas en `?`, que queda fuera. Ahora las escribe como `P` — pendiente
confirmado, peso 0, dentro del denominador. **Se arregló donde nace, no en el
cálculo.** OBRA PRUEBA pasa de 92.4 (sobre lo medido) a **6.4 sobre las 1.178
celdas**, que es la lectura correcta de una obra recién empezada.

Guarda que se mantiene: un blanco solo asciende `?`→`P`; **nunca baja una
`X`, `M` o `/`**. Sin ella, una hoja donde Bixente solo anota los avances
borraría todo lo anterior.

Eso destapó otro fallo de la misma familia: `MAPA_ESTADO` aceptaba `''` y
`'pendiente'` pero **no la letra `'P'`**, la canónica del alfabeto que
documenta el `CLAUDE.md`. Un sidecar escrito con el alfabeto de la casa se
guardaba como `?`: avisaba por consola, pero se guardaba mal.

Y un fallo mío: el alta guardaba los tajos en el orden en que los imprime la
hoja (agrupado por fase), no en el de ejecución del catálogo. Corregido.

## 5. Lo siguiente

- **Contrastar con tinta real de una obra de verdad**:
  `REVISION MUNGIA 27072026.pdf` tiene 56 trazos de pen y un sidecar de 213
  celdas transcrito a mano. Es verdad conocida contra la que medirse.
- **Fotos de móvil y escaneos de papel**: siguen fuera. Perspectiva, sombras y
  arrugas son otro problema.
- **El porcentaje de una obra recién medida engaña.** OBRA PRUEBA sale a 92.4
  %, pero eso es *sobre lo medido*: 1.097 celdas siguen en `?` y quedan fuera
  del denominador. Decidir cómo se presenta.

## 6. Deuda que sigue abierta

- 17 de 21 obras sin adaptador ni ficha. Ahora hay un camino de alta que no
  exige historial previo: `alta_obra_desde_hoja.py`. Gorliz es la candidata.
- El commit `7d91628` (rama `claude/cool-bardeen-fc67fd`) haría el commit del
  `.bat` selectivo. Sin fusionar; decisión pendiente.
- `main` no tiene upstream, así que `git log origin/main..HEAD` sale vacío
  tanto si está publicado como si no. Comparar contra `FETCH_HEAD`.
