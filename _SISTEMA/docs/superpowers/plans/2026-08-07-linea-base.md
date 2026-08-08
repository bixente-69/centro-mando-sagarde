# Línea base — 2026-08-07, antes de reordenar el entorno `_SISTEMA`

Tarea 0 del plan `2026-08-07-jerarquia-sistema-entorno`. Esta tarea no mueve
ni un fichero: sólo mide y congela el estado actual, para que cada tarea de
traslado (1 a 13) pueda comparar su antes/después contra estos números.

**Regla de comparación:** el recuento por letra (`X`/`M`/`/`/`P`/`?`/`N`), no
el porcentaje redondeado. El porcentaje ya coincide en este documento
(sirve para localizar la obra), pero no vale como prueba de que nada se ha
movido.

---

## Paso 1 — Árbol limpio y commit de referencia

```
git status --short   →  (sin salida)
git log --oneline -1 →  985737a Plan de implementacion de la jerarquia _SISTEMA
```

`985737a` es descendiente de `d9ad986` (comprobado con
`git merge-base --is-ancestor d9ad986 HEAD`, resultado positivo), que es el
commit mínimo exigido por el brief. Árbol de trabajo limpio confirmado.

Historial inmediato (`git log --oneline -8`):

```
985737a Plan de implementacion de la jerarquia _SISTEMA
d9ad986 Especificar la jerarquia _SISTEMA para separar lo informatico de lo visible
cebce47 Actualizacion 2026-08-07_0810
4e5c1dc Desactivar Jekyll: el generador daba 404 en el Centro de Mando
465ae65 Actualizacion 2026-08-07_0750
f754876 Las skills se publican de verdad, no solo sobre el papel
bf0d144 La hoja se pagina calculando, no esperando que quepa
590a38e Actualizacion 2026-08-06_1132
```

---

## Paso 2 — Suite de referencia

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

Resultado exacto:

```
Ran 191 tests in 29.387s

OK
```

**191 tests, en verde.** Coincide con el número de referencia anotado hoy
antes de empezar (`Ran 191 tests ... OK`).

Dos `ResourceWarning` (ficheros no cerrados en
`tests/test_paginacion_generador.py`, líneas 54 y 63: `obras_revisiones.js`
y `generador_revisiones.html` abiertos sin `with`) — son avisos, no fallos,
y no cambian el resultado (`OK`). Se anotan aquí para no ocultarlos, no
porque sean parte de esta tarea.

**Efecto colateral observado (no atribuible a esta tarea, pero digno de
constar):** al terminar el descubrimiento de tests, la ejecución imprime
además:

```
[1/2] Usando el historial validado por la ficha para '2026 MUNGIA ACR NEINOR'...
      Ultima revision: 28/07/2026 (1 registros)
[2/2] Generando PDF Ejecutivo A4 en: ...\2026 MUNGIA ACR NEINOR\INFORME SAGARDE IA\INFORME_EJECUTIVO_2026_MUNGIA_ACR_NEINOR.pdf...
[OK] Informe ejecutivo creado con exito: ...
```

Es decir: descubrir/ejecutar la suite regenera de verdad el PDF ejecutivo de
Mungia en su carpeta real (mensajes propios de `generar_todos.py` /
`panel_obra.py`). Comprobado con `git status --short` inmediatamente después:
**sin salida** — ese PDF no está rastreado por git (lo cubre el `.gitignore`
de lista blanca), así que el efecto no ensucia el repositorio. Se deja
constancia porque es justo el tipo de efecto lateral silencioso que este
proyecto vigila; no se ha investigado más a fondo por quedar fuera del
alcance de la Tarea 0 (que es medir, no corregir).

---

## Paso 3 — Desglose real por letra en `ficha_obra.json`

### La forma asumida por el brief no es la forma real

El script propuesto en el brief asume `d["ubicaciones"]`, cada una con un
sub-diccionario `"tajos"`. **Esa clave no existe.** Las claves reales de
nivel superior en los 5 ficheros son idénticas:

```
version, id, modo, fecha_entrada_digital, actualizado, identidad,
estructura, tajos, estados, revisiones, dudas, materiales, documentos,
contactos
```

- `estructura.bloques[].portales[].plantas[].ubicaciones[]` describe **dónde**
  existen viviendas/locales (id, tipo, habitaciones, origen, confirmado) —
  es la geometría, no los estados.
- `tajos.aplicables` es la lista plana de tajos que aplican a esa obra;
  `tajos.detalle` da su metadato (nombre, ámbito, propiedad, fase, orden).
- **`estados` es el diccionario plano que realmente guarda la letra.**
  Clave = `"{portal}__{planta}__{tajo}__{ubicacion}"` (p. ej.
  `"p1__pb__tabicado__A"`). Valor = `{"v": "<letra>", "f": <fecha o null>,
  "r": <id_revision o null>, ["origen": "<texto>"]}`.

El recuento real se hizo recorriendo `estados.values()` y contando el campo
`"v"` de cada entrada (tratando `None`/`""` como `"vacio"`). Verificado en
los 5 ficheros: **0 entradas con `v` ausente, `None` o vacío, 0 entradas que
no fueran diccionario** — es decir, bajo este modelo de datos cada celda
declarada (aplicable o no) siempre lleva una letra explícita; no existe hoy
un estado "vacío" real. Por eso la columna `vacío` sale a 0 en las cinco
obras: es un recuento verificado, no una casilla sin rellenar.

Tampoco aparecieron letras fuera del alfabeto conocido
(`X`, `M`, `/`, `P`, `?`, `N`).

### Recuento por letra, las 5 obras con `ficha_obra.json`

| Obra | celdas (`len(estados)`) | X | M | / | P | ? | N | vacío |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025 BILBAO OBISPO ORUETA | 4080 | 2314 | 0 | 0 | 8 | 0 | 1758 | 0 |
| 2025 GERNIKA 32V | 1216 | 928 | 0 | 0 | 288 | 0 | 0 | 0 |
| 2026 BOLUETA ACR | 3686 | 1453 | 103 | 19 | 1921 | 190 | 0 | 0 |
| 2026 MUNGIA ACR NEINOR | 2356 | 1810 | 82 | 0 | 429 | 35 | 0 | 0 |
| 2026 OBRA PRUEBA | 1178 | 70 | 6 | 5 | 1097 | 0 | 0 | 0 |

Nota: en Mungia el total de celdas de `estados` hoy es 2356, no 2309 (cifra
citada en `CLAUDE.md` como ejemplo del 27/07/2026). No es una discrepancia
de este recuento: han pasado revisiones desde esa fecha (última revisión de
Mungia según la suite: 28/07/2026) y el número de celdas de `estados` crece
con lo que se va marcando. Este documento congela el número de **hoy**
(07/08/2026); las tareas siguientes comparan contra esta tabla, no contra la
cifra de la memoria antigua.

### Verificación cruzada contra `pct_ponderado`

`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/resumen_obras.json`
(generado 07/08/2026 08:10) da, campo `pct_ponderado`, exactamente los
valores esperados:

**Orueta 99.7 · Mungia 80.1 · Gernika 76.3 · Bolueta 43.5 · OBRA PRUEBA 6.4**

Coincide dígito a dígito con lo indicado en el encargo. Sirve para confirmar
que el fichero leído es el correcto — **no** sustituye al recuento por letra
de la tabla anterior, que es el dato que hay que comparar tarea a tarea.

(De paso, contraste rápido no pedido pero observado: en Orueta,
`X / (total - N)` = 2314/2322 = 99.65 % ≈ 99.7 %, y en Gernika, sin `N` ni
`M`, `X/total` = 928/1216 = 76.3 % exacto. En Mungia la fórmula simple
`(X + 0.5·M)/total` da 78.6 %, no 80.1 %: el priorizador pondera con algo
más que ese cálculo ingenuo. No se ha perseguido la fórmula exacta —
`CLAUDE.md` ya avisa de que el porcentaje es un criterio ciego; el dato que
cuenta es el desglose de la tabla.)

---

## Paso 4 — Enlaces internos (`href` de `.html` que resuelven en disco)

Script del brief ejecutado tal cual (excluye rutas con `.git`,
`SAGARDE (OLD)` y `_PREVIEWS_WORD`; sólo `href="..."` sin `#`, `?` ni `:`,
es decir, enlaces relativos internos, no anclas ni `http:`/`mailto:`).

```
enlaces internos que resuelven: 4719
enlaces rotos YA existentes: 1
    .\SAGARDE OBRAS ABIERTAS\2026 GORLIZ HOSPITAL\INFORME SAGARDE IA\panel.html -> INFORME_EJECUTIVO_2026_GORLIZ_HOSPITAL.pdf
```

El único roto es coherente con lo ya sabido: Gorliz no tiene revisiones
todavía (`pct_ponderado = 0` en `resumen_obras.json`), así que su PDF
ejecutivo nunca se ha generado y el enlace del panel apunta a un fichero
que no existe. Preexistente, no causado por esta tarea.

Comprobación de que el filtro de exclusión no es un no-op silencioso: la
carpeta `SAGARDE (OLD)` existe de verdad en la raíz del repositorio (se
confirmó con un listado directo), así que si el traslado tocara algo bajo
esa carpeta, el script la seguiría ignorando a propósito y no por omisión.

**Números de referencia para las tareas siguientes:**
- Enlaces que resuelven: **4719** (no debería bajar sin explicación).
- Enlaces rotos: **1** (no debería subir; motivo: PDF de Gorliz no generado).

---

## Cómo usar esta línea base

Cada tarea de traslado (1–13) debe, antes de darse por buena:

1. Repetir el paso 2 (suite) y comprobar `Ran 191 tests` (o más, nunca
   menos) `... OK`.
2. Repetir el paso 3 para las obras que pudieran verse afectadas y comparar
   la tabla letra a letra contra la de este documento — no sólo el
   `pct_ponderado`.
3. Repetir el paso 4 y comprobar que "enlaces rotos" no ha subido de 1, y
   que "enlaces que resuelven" no ha bajado de 4719 sin una explicación de
   por qué (por ejemplo, un `.html` movido intencionadamente cuya cuenta se
   desplaza a otro lado).
4. Confirmar explícitamente que las obras **no implicadas** en el traslado
   de esa tarea conservan exactamente su fila de la tabla del paso 3.

Si cualquiera de estos cuatro puntos no cuadra, la tarea no cierra en verde:
se para y se reporta a Bixente el antes/después, tal como exige
`CLAUDE.md`.
