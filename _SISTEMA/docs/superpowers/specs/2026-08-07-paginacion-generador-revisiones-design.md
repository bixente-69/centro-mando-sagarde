# Paginación A4 del generador de hojas de revisión

**Fecha:** 07/08/2026
**Fichero afectado:** `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html`
**Estado:** aprobado por Bixente el 07/08/2026 tras ver la maqueta impresa a PDF.

---

## 1. El problema, medido

Al imprimir la hoja a PDF las tablas se parten entre páginas por donde cae, lo
que estorba en obra y, sobre todo, estorba a la lectura posterior: quien lee la
hoja marcada es la IA, página a página.

Hoy `sheetCSS()` declara la intención correcta —una tabla por página— pero no
la garantiza:

| regla actual (líneas 1223-1249) | qué hace |
|---|---|
| `@page{size:A4 portrait;margin:7mm 7mm 6mm}` | deja **284 mm** útiles |
| `.portal-section.portal-break{break-before:page}` | cada portal empieza en página nueva |
| `.planta-block{break-inside:avoid}` | pide que la tabla no se parta |
| `.planta-block+.planta-block{break-before:page}` | una tabla por página |

`break-inside:avoid` es una sugerencia. Cuando la tabla no cabe, el navegador
la parte donde quiere.

### Constantes medidas sobre PDF real

No estimadas: medidas con `pdfplumber` sobre el PDF que produce Edge desde la
hoja de Mungia (`antes_mungia.pdf`, 06/08/2026).

| elemento | alto real |
|---|---|
| fila de tajo | **5,01 mm** |
| rótulo de fase (`tr-grp`) | **3,28 mm** |
| `thead` (3 filas) + fila de observaciones | **34,30 mm** |
| alto útil de página | **284,00 mm** |

De ahí sale el dato que gobierna todo el diseño:

```
38 tajos × 5,01 + 18 grupos × 3,28 = 249,42 mm de filas
284,00 − 34,30                     = 249,70 mm disponibles
                                     ─────────────────────
                                     cabe por 0,28 mm
```

**La hoja de hoy cabe por un cuarto de milímetro.** No es un diseño, es una
coincidencia. Por eso escupe restos.

Orueta ni siquiera coincide: 55 tajos × 5,01 + 17 grupos × 3,28 = **331,31 mm**
de filas frente a 249,70 disponibles. Necesita dos hojas por tabla, siempre.

### Consecuencias observadas

| | páginas | páginas basura | tablas partidas a ciegas |
|---|---|---|---|
| Mungia hoy | 12 | 4 (p1, p5, p7, p9) | sí |
| Orueta hoy | 17 | 1 | las 8 |

La página 1 se desperdicia **siempre**: cabecera y leyenda ocupan ~32 mm, así
que ninguna tabla completa cabe detrás. Hoy sale con 7 celdas de nada.

### Por qué esto es un riesgo de datos, no sólo estético

`rejilla_hoja.leer_pdf` lee **página a página**, toma sólo `tablas[0]` de cada
página y **descarta en silencio** toda página con menos de `CELDAS_MINIMAS`
(50) celdas. Un resto de tabla en una página no da error: desaparece.

Hoy no se ha perdido nada por suerte —los restos medidos contenían sólo
cabeceras y la fila de observaciones—, pero la protección es el azar.

---

## 2. Alcance

### Se toca

- `generador_revisiones.html` (paginación, CSS de impresión, diálogo de
  capacidad).
- Pruebas nuevas en `tests/`.

### No se toca

`rejilla_hoja.py`, `leer_hoja_marcada.py`, `generar_todos.py`, los adaptadores
y `obras_revisiones.js`. **Cero cambios.**

---

## 3. Diseño

### 3.1 Reparto calculado en lugar de confianza

`generateHTML` deja de emitir una tabla por (portal × grupo de plantas) y pasa
a emitir una tabla por (portal × grupo de plantas × **hoja**).

Una función nueva reparte las filas del cuerpo en hojas que caben por
construcción, con dos reglas:

1. **Sin huérfanos.** Un rótulo de fase nunca se queda al final de una hoja con
   sus tajos en la siguiente: si no cabe al menos un tajo detrás, el rótulo se
   arrastra a la hoja siguiente.
2. **Reparto equilibrado.** Cuando hacen falta N hojas, los tajos se reparten a
   partes iguales entre ellas, no llenando la primera a tope. Con 55 tajos en 2
   hojas salen 28 y 27, no 42 y 13. *(Decisión de Bixente, 07/08/2026.)*

Cada hoja lleva su `thead` completo: fila de identificación, fila de plantas y
**cabecero de viviendas repetido**. Es lo que Bixente pidió: partir por tajos,
repitiendo las viviendas.

### 3.2 La medida deja de ser un número inventado

`MAX_TAJOS_A4 = 38` cuenta tajos e ignora las 18 filas de fase, que se comen
59 mm. Se sustituye por una suma de alturas con las constantes medidas.

El contador del paso 3 deja de decir *"55 tajos · +17 sobre A4"* y pasa a decir
cuántas hojas salen por tabla.

### 3.3 Colchón comprado en el `thead`

Con 0 mm de margen el corte sigue en la cuerda floja. Se recorta el relleno de
las filas de cabecera y de la fila de observaciones **sólo en `@media print`**:

```
.th-ident{padding:.6mm 2mm;font-size:8.2pt}
.th-floor{padding:1.1mm 1mm}
.th-apt{padding:.7mm .45mm}
.tr-notes td{height:3.6mm;padding:.4mm 2mm}
```

Eso baja el `thead` de 34,30 a ~28 mm y deja **4 mm de colchón real**.

**Las casillas de marcar no se tocan**: siguen a 5,01 mm. Es el tamaño que
necesita Bixente para el boli y el que necesita la lectura por visión para que
el recorte de cada celda sea legible. Encogerlas sería cambiar el problema de
sitio.

### 3.4 Portada

La cabecera y la leyenda dejan de robarle la página a una tabla: ocupan la
página 1 a propósito. Deja de haber una primera página rota con 7 celdas.

Un único salto detrás de la leyenda, no uno por cada elemento (en la maqueta,
poner el salto en los dos generaba dos páginas de portada).

### 3.5 Diálogo de capacidad

Al pulsar Descargar o Vista previa, si la selección no entra en una hoja:

- dice cuántas hojas saldrían y por qué;
- lista los tajos con **"X de N celdas impresas"**, ordenados de más hecho a
  menos y plegados por fase;
- un botón quita los que están al 100% de lo conocido —es decir, aquellos cuyas
  celdas impresas están **todas** en `X`— **y dice cuántos ha quitado**: en
  Orueta dirá "ninguno", no fingirá;
- se pueden desmarcar a mano los que aún no tocan;
- queda siempre **"generar igualmente en N hojas"**.

**Por qué el recuento y no un "quitar terminados" automático.** Al generador
sólo le llegan `X`, `M` y `/`: `generar_todos.py:237` documenta que `P`
(pendiente confirmado), `?` (desconocido) y `N` (no aplica) viajan los tres
como celda vacía. El generador no puede distinguir "falta por hacer" de "aquí
no aplica". Decidir "terminado" con ese dato sería un criterio ciego. Medido:
si se definiera "terminado" como *todas sus celdas en X*, Orueta —la única obra
que no cabe— tendría **cero** tajos terminados, porque le cuentan como
pendientes las celdas que en realidad son `N`.

Que Bixente omita tajos es seguro y ya está verificado: `marcar_no_empezados`
recorre `celdas_hoja`, que se construye con las celdas **impresas en la
rejilla** (`leer_hoja_marcada.py:318`), no con las de la ficha. Un tajo que no
se imprime nunca entra ahí. Y lleva segunda guarda: sólo asciende `?` → `P`,
nunca baja una `X`.

---

## 4. Contrato con la lectura posterior

Invariantes que el generador debe seguir cumpliendo. Son el contrato con
`rejilla_hoja.py` y `leer_hoja_marcada.py`, que no se tocan:

1. **Una tabla por página.** Innegociable: `leer_pdf` toma sólo `tablas[0]` de
   cada página; dos tablas en una página harían desaparecer la segunda en
   silencio. Que la tabla de 2 viviendas de Mungia ocupe un A4 entero no es
   desperdicio, es la protección.
2. **Toda página de tabla lleva su fila de identificación**, con el mismo
   formato que hoy: `OBRA · FECHA · BLOQUE · PORTAL · PLANTAS…`.
3. **Ninguna página de tabla por debajo de 50 celdas**, o `leer_pdf` la
   descarta sin avisar.
4. **Las claves `data-k` no cambian**:
   `portal_id__planta_id__tajo_id__vivienda`.
5. **El nombre de fichero conserva la fecha DDMMAAAA**, que es lo que
   `_fecha_desde_nombre` necesita para ordenar las revisiones.

### Riesgo abierto: el rótulo "HOJA n DE N"

`leer_tabla` parsea la identificación partiendo por `·`. La maqueta añadió
`· HOJA 1 DE 2` dentro de `th-ident` y **no se ha podido verificar**: la única
obra con tablas partidas es Orueta, y Orueta falla la lectura por otro motivo
(ver §6).

**Decisión:** se intenta primero dentro de `th-ident` y se prueba que
`leer_tabla` sigue parseando igual. Si no, el rótulo se saca fuera de la tabla.
No se da por bueno sin la prueba.

---

## 5. Verificación

1. Arnés en `tests/` que genera el PDF A4 real de las 5 obras con ficha
   (Playwright con `channel='msedge'`; Edge en `--print-to-pdf` resultó
   errático cuando hay una sesión de Edge abierta).
2. Sobre cada PDF:
   - toda página de tabla tiene **una** tabla con ≥50 celdas;
   - toda página de tabla lleva identificación válida;
   - **la unión de celdas de todas las páginas es igual a la rejilla completa**:
     ni una perdida, ni una repetida con distinta identificación.
3. `rejilla_hoja.leer_pdf` lee el PDF y devuelve el total esperado
   (Mungia 2.356, Gernika 1.216, Bolueta 3.686, Prueba 1.178).
4. **Prueba por mutación:** romper la paginación a propósito y comprobar que el
   arnés se entera. Sin esto la prueba no vale.
5. Regresión: las 5 obras siguen dando las mismas claves `data-k` y los mismos
   recuentos de estados precargados que hoy (Mungia 2.356 celdas / 1.887
   estados; Gernika 1.216 / 928; Bolueta 3.686 / 1.575; Orueta 5.610 / 2.314;
   Prueba 1.178 / 81).
6. Restaurar cualquier fichero mutado antes de dar nada por bueno.

### Resultado de la maqueta (07/08/2026)

Ya medido, sin tocar el generador:

| | páginas | basura | páginas sin identificar | lector |
|---|---|---|---|---|
| Mungia después | **9** | 1 (portada) | ninguna | 2.356/2.356 |
| Orueta después | 17 | 1 (portada) | ninguna | falla (§6) |

---

## 6. Fuera de alcance, anotado

**Orueta no se puede leer hoy, y no es por la paginación.** `rejilla_hoja`
la rechaza: *"el tajo 'Agujero Focos Pasillo' no está en el catálogo común"*.
Es un problema de datos de esa obra. No se toca aquí.

**`groupCompleteFloors(plantas, maxViviendas=10)` no es un tope.** Mete la
planta entera antes de comprobar el límite, así que una planta de 15 viviendas
da una tabla de 15 columnas (pasa en Orueta). Se deja: partir una planta entre
dos tablas se lee peor que una tabla ancha. El cálculo de anchos debe seguir
soportando 15 columnas.

**`saveKey()` (línea 1292) es código muerto.** La pantalla `sc-import` ya no
existe en el DOM, pero quedaron la función, su CSS y el rótulo del bloque. La
función lee la clave, no la guarda y muestra *"Clave guardada ✓"*. Hoy es
inalcanzable. Es la familia de fallos de este proyecto esperando a que alguien
vuelva a enganchar la pantalla: conviene borrarla, pero no en este trabajo.

**Publicar `N` y `P` en `obras_revisiones.js`** permitiría que "terminado"
significase terminado de verdad. Obliga a tocar `generar_todos.py` y a
revalidar las 5 obras. Queda para otro trabajo.
