# Trabajo restante del entorno Sagarde y qué se puede desviar a otra IA

Redactado el 28/07/2026, con el generador ya trabajando desde la base
(commiteado hasta `abdf8b0`, **sin push**).

---

## Cómo se decide qué se puede desviar

El criterio no es la dificultad, es **de qué depende el trabajo**:

| | Se puede desviar | Tiene que hacerse aquí |
|---|---|---|
| **Entrada** | un documento (PDF, foto, escaneo) | el repositorio y sus datos |
| **Salida** | un fichero de texto o JSON | ficheros del repo, commits |
| **Verificación** | comparar contra el propio documento | ejecutar el sistema y mirar cifras |

De ahí sale una conclusión clara y muy útil:

> **Lo desviable es el trabajo de LEER documentos. Lo que toca código o datos
> del repositorio, no.**

Y resulta que el trabajo de leer documentos es justamente el más repetitivo y
voluminoso que tienes: 213 celdas transcritas a mano en la última revisión.

---

## 🟢 BLOQUE A — Lectura de escaneos de revisión

**DESVIABLE. Es el que más rinde de todos.**

Es el paso 4 de tu ciclo: coges la hoja rellenada a boli, la escaneas, y hay
que convertirla en datos. Hoy sale un fichero de 213 celdas escritas una a una.

**Por qué se desvía bien:** sólo necesita la imagen. No toca el repositorio, no
ejecuta nada, no depende de git. La salida es un JSON que luego se deja caer en
la carpeta `REVISIONES` de la obra.

**Qué le das a la otra IA:** el escaneo (PDF o fotos) y el encargo del §A.1.

**Qué te devuelve:** un fichero `.correcciones.json` listo para usar.

**Qué hay que hacer aquí después:** dejar el fichero en su sitio, regenerar y
comprobar que las cifras se mueven donde tienen que moverse. Cinco minutos.

### A.1 — Encargo listo para copiar y pegar en otra IA

> Eres un lector de hojas de revisión de obra. Te paso el escaneo de una hoja
> de revisión de tajos de Montajes Eléctricos Sagarde, rellenada a mano.
>
> **Lo impreso en gris** son los estados que ya tenía el sistema. **Lo escrito a
> mano** (boli negro, azul o lápiz digital) son las correcciones nuevas. A veces
> hay corrector blanco tapando una marca impresa: eso significa que ese estado
> ya no vale y el bueno es el manuscrito que hay encima.
>
> **Devuélveme SOLO las celdas manuscritas**, en este formato exacto:
>
> ```json
> {"estados": {"p1__pb__cuad-mec__B2": "M", "p1__5__techos-zzcc__A2": "M"}}
> ```
>
> La clave es `portal__planta__tajo__vivienda`:
>
> - **portal**: `p1` = ZR1.1, `p2` = ZR1.2, `p3` = ZR2.1
> - **planta**: `pb`, `1`, `2`, `3`, `4`, `5`, `6` — tal cual aparece en la cabecera
> - **vivienda**: la etiqueta de la columna tal cual: `A2`, `B2`, `B3`, `C2`, `C3`
> - **tajo**: el identificador de la tabla de abajo, según el texto de la fila
>
> **Estados válidos y sólo estos:** `X` (terminado), `M` (más del 50 %),
> `/` (iniciado).
>
> **Reglas que no se saltan:**
> 1. **No inventes ninguna celda.** Si una marca es ambigua o no distingues a qué
>    fila pertenece, NO la pongas en `estados`: añádela a una lista aparte
>    `"dudas"` describiendo qué ves y dónde.
> 2. Cada página lleva arriba una franja con obra, fecha, bloque, portal y
>    plantas. **Úsala siempre** para saber de qué portal es cada página. Si una
>    página no la tiene, dilo y no adivines el portal.
> 3. Las celdas impresas que no estén tachadas ni corregidas **no se incluyen**.
>    Sólo interesa lo que ha cambiado.
> 4. Si hay texto libre en el campo "Obs:", devuélvelo aparte en
>    `"observaciones"`, indicando la página.
>
> **Tabla de tajos** (identificador → cómo aparece impreso en la fila):
>
> ```
> tabicado      Tabicado                 pladur-2c    Segundas caras de Pladur
> rozas         Rozas de timbres         doblar-caj   Doblar cajas
> mont-elec     Montante eléctrica       embornado    Embornado eléctrico
> mont-telco    Montante de telecomunic. teleembor    Telembornado
> mont-sscc     Montante servicios com.  deriv-ind    Derivación individual
> tube-zzcc     Tubeado de zonas comunes cuad-mec     Cuadro mecanizado
> cabl-zzcc     Cableado de zonas com.   ct-tec       Cuarto técnico
> suelo-rad     Suelo radiante           techos       Techos
> suelo-rec     Suelo recrecido          enchapado    Enchapado
> pladur-p      Perfilado de Pladur      techos-zzcc  Techos de zonas comunes
> pladur-1c     Primeras caras de Pladur pint-1       Pintura — primera mano
> cuad-pres     Cuadros presentados      pint-zzcc    Pintura de zonas comunes
> tube-viv      Tubeado interior         pint-2       Pintura — segunda mano
> cabl-elec     Cableado eléctrico       mecanizado   Mecanizado eléctrico
> telecabl      Telecableado             telemec      Telemecanizado
> portero       Portero / videoportero   aguj-zzcc    Agujeros de iluminación ZZCC
> termostatos   Termostatos              plac-tapas   Placas y tapas
> fachada       Fachada terminada        apliques     Apliques y enchufes terraza
> casquillos    Casquillos y bombillas   ilum-rell    Iluminación de rellanos / ZZCC
> ```

**Aviso importante para ti:** revisa siempre las `dudas` que devuelva. Es
preferible una duda declarada a un dato inventado — el sistema entero depende
de eso.

---

## 🟢 BLOQUE B — Estructura de Gernika, Bolueta y Obispo Orueta

**DESVIABLE la parte de lectura. La siembra se hace aquí.**

Para que esas tres obras aparezcan en el desplegable hay que sembrarles su
`ficha_obra.json`. Eso exige saber su estructura real: portales, plantas y qué
viviendas hay en cada planta. Hoy el sistema la deduce de las hojas, y deducir
es lo que a Mungia le escondió una vivienda entera.

**Se desvía:** leer las hojas de revisión de cada obra y proponer la estructura.
**Se hace aquí:** sembrar la ficha, comprobar contra el histórico y regenerar.

**Se pueden repartir las tres a la vez**, porque son obras distintas y no
comparten nada.

### B.1 — Encargo listo para copiar y pegar

> Te paso las hojas de revisión de una obra. Extrae su **estructura física** y
> devuélvemela en este formato:
>
> ```
> BLOQUE: <nombre>
>   PORTAL <nombre tal como aparece en la cabecera>
>     PLANTA <nombre>: viviendas <lista de etiquetas de columna>
>     PLANTA <nombre>: viviendas <lista>
> ```
>
> **Reglas:**
> 1. Copia las etiquetas **tal cual aparecen impresas**. Si una planta tiene
>    columnas `A2`, `B3`, `C3`, escribe eso, no `A`, `B`, `C`.
> 2. Si una planta tiene **menos viviendas que las demás**, dilo explícitamente
>    y señala en qué página lo has visto: puede ser correcto o puede ser un
>    error de la hoja, y hay que confirmarlo.
> 3. Si el número de viviendas de una misma planta **cambia entre revisiones**,
>    dilo y muestra ambas versiones con sus fechas.
> 4. Marca cualquier fila o columna que no sepas interpretar. **No completes
>    huecos por simetría**: que dos portales se parezcan no significa que sean
>    iguales.
> 5. Indica también cuántos tajos distintos aparecen y cuáles, con el texto
>    exacto de cada fila.

**Qué haré yo con eso:** contrastarlo contra el histórico de revisiones, traerte
las discrepancias para que las confirmes, y sembrar la ficha. La confirmación
final es tuya siempre: el sembrador detecta huecos sospechosos y no se adivinan.

---

## 🔴 BLOQUE C — Obispo Orueta publica 40 celdas en vez de la obra entera

**AQUÍ. Es lo más urgente y no se puede desviar.**

Tu panel publica hoy un 80,0 % calculado sobre **40 celdas**, no sobre las 2404
de la obra. Apareció un `REVISION OBISPO ORUETA 2A FASE 27072026.pdf` con 40
registros y el panel refleja sólo esa hoja. La serie lo enseña claro:

| fecha | total | pct |
|---|---|---|
| 24/09/2025 | 1288 | 62.1 |
| 27/07/2026 | **40** | **80.0** |

**Por qué no se desvía:** hay que reproducirlo sobre los datos reales, decidir
si esa hoja es una revisión parcial legítima —y entonces el sistema debe
fusionarla con el histórico en vez de sustituirlo— o si es un fichero que no
debería estar ahí. Es diagnóstico sobre el repositorio.

**Lo que sí puedes adelantar tú en un minuto:** decirme si esa hoja de "2ª fase"
es una revisión parcial de una zona concreta o si se coló por error. Con eso el
arreglo cambia por completo.

---

## 🔴 BLOQUE D — El PDF ejecutivo publica los números viejos

**AQUÍ.**

`generar_informe_ejecutivo.py` carga su propio historial por su cuenta (línea
372) en vez de recibir el que ya viene corregido. El PDF ejecutivo de Mungia
sigue diciendo 1798/84 mientras el panel dice 1801/86.

**Por qué no se desvía:** es un cambio de código con verificación contra las
cuatro obras.

---

## 🔴 BLOQUE E — Cierres pendientes

**AQUÍ. Poco trabajo cada uno.**

- **Tarea 4 de la fase A**: verificación end-to-end de que las correcciones del
  PORTAL y la vivienda E aparecen en el panel.
- **Gorliz Hospital**: `inventario_total: 0` sin explicación. Puede ser una obra
  dada de alta sin revisiones —normal— o un fallo silencioso. Un recuento de
  cero hay que mirarlo, no suponerlo.
- **Cuatro worktrees residuales** en `.claude/worktrees/`, con sus ramas. Son
  copias del código que ensucian cualquier búsqueda.
- **Deuda menor**: `PORT AL` que no se normaliza a `PORTAL` y degrada tres
  celdas de Mungia en cada pasada; `_orden_fecha` colapsando fechas
  malformadas; empate de fechas resuelto con `max()` sin avisar.

---

## 🟡 BLOQUE F — Cerrar el ciclo del todo

**MIXTO, y es tu objetivo declarado.**

Hoy el paso 4 lo haces pasándome el escaneo. El bloque A lo hace desviable a
otra IA, que ya es un salto grande. El paso siguiente sería que la salida de esa
lectura entre en la base **sin pasar por el sidecar**, que hoy es un parche
sobre el PDF digital.

Eso es diseño nuevo y merece su propia conversación. No lo metas en este plan:
primero conviene que uses unas cuantas revisiones con el bloque A y veamos qué
falla de verdad antes de construir nada.

---

## Orden recomendado

| # | Bloque | Dónde | Por qué en este orden |
|---|---|---|---|
| 1 | **C** — Obispo Orueta | 🔴 aquí | Estás publicando un dato falso. Lo demás puede esperar; esto no |
| 2 | **B** — estructura de las 3 obras | 🟢 desviable | Es tu prioridad declarada y las tres se pueden repartir a la vez |
| 3 | **A** — lectura de escaneos | 🟢 desviable | En cuanto tengas una revisión nueva. Es lo que más trabajo repetitivo te quita |
| 4 | **D** — PDF ejecutivo | 🔴 aquí | Incoherencia entre lo que dice el panel y lo que dice el PDF |
| 5 | **E** — cierres | 🔴 aquí | Rápidos, se pueden ir haciendo entre medias |
| 6 | **F** — cerrar el ciclo | 🟡 mixto | Sólo después de usar A unas cuantas veces |

**Se puede solapar:** mientras yo hago el bloque C aquí, tú puedes tener el
bloque B en marcha en otra IA. No comparten nada.

---

## Dos avisos

**Nada de esto está publicado.** Los seis commits de hoy están en `main` sin
push. El Centro de Mando sigue mostrando lo anterior hasta que lances tu `.bat`.

**Cuando vuelva trabajo de otra IA, tráemelo tal cual.** No lo apliques
directamente al repositorio. Lo que llegue de fuera hay que comprobarlo contra
los datos reales antes de darlo por bueno: es la regla que gobierna este
proyecto y vale también —sobre todo— para lo que produzca otra máquina.
