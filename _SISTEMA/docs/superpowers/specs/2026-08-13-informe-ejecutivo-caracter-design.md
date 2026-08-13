# Carácter visual del informe ejecutivo

**Fecha:** 13/08/2026
**Estado:** diseño aprobado por Bixente, pendiente de plan de ejecución
**Fichero afectado:** `_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py` (982 líneas)

---

## 1. El problema, dicho por Bixente

El informe ejecutivo **«parece hecho por un script»**. No es un problema de
jerarquía, ni de contenido, ni de maquetación rota: es que le falta carácter.

Se descartaron expresamente otras tres lecturas del encargo: rehacer la
jerarquía, cambiar qué información aparece, y arreglar solo defectos sueltos.

## 2. Diagnóstico

Auditoría del fichero y del PDF generado de `2026 MUNGIA ACR NEINOR`
(4 páginas: una general y una por portal).

**El informe no está mal.** Tiene estructura real —cabecera con logo, resumen
ejecutivo, cinco KPI, evolución, avance por fase, tajos que requieren atención,
frentes y condicionantes, pie— y es denso y ordenado. Lo que falla es el
acabado:

| Hallazgo | Evidencia |
|---|---|
| Toda la tipografía es Helvetica, la de fábrica de ReportLab | `_style()` línea 297; siete apariciones en total |
| Ninguna fuente registrada en todo el árbol | `grep registerFont\|TTFont\|pdfmetrics` → sin resultados |
| El logo va deformado, y distinto en cada página | Nativo 2732×751 (ratio **3.638**); colocado a 48×14 mm (3.429) en la línea 423 y a 52×15 mm (3.467) en la 760 |
| El logo no tiene fondo blanco | Esquinas `(232,245,253)` y `(194,230,246)`: azul pálido. Parece un recuadro pegado |
| El color juzga en vez de describir | Verde ≥70, ámbar ≥40, rojo <40: pinta de rojo fases que solo es que aún no tocan |

## 3. Alcance

**Dentro:** tipografía, color y logo del informe ejecutivo.

**Fuera, y a propósito:** el flujo del dato, `_filtrar_snapshot_sagarde`, la
jerarquía tipográfica, el contenido, el número de páginas, y el resto de
generadores del entorno. Durante un tiempo el informe y el `panel.html` no irán
a juego. Unificarlos es otra tarea, no esta.

**No se toca ni una cifra.** El informe seguirá diciendo 80.7 % y 1159/1528
para Mungia, con el mismo alcance de tajos propios de Sagarde.

## 4. Decisiones

### 4.1 Tipografía — IBM Plex Sans

Elegida por Bixente sobre Source Sans 3 e Inter, comparándolas con un trozo
real del informe **a los tamaños del PDF** (16 pt título, 10 pt rótulos,
7 pt tabla), que es donde se juega un documento denso.

Licencia **SIL OFL**: gratuita, incrustable y redistribuible, condición
necesaria porque el PDF puede acabar en manos del promotor.

Pesos necesarios: **Regular y Bold**. El informe no usa cursivas.

Ficheros a incorporar en `_SISTEMA/MOTOR/assets/fonts/`:

- `IBMPlexSans-Regular.ttf`
- `IBMPlexSans-Bold.ttf`
- `OFL.txt` — la SIL OFL exige que la licencia acompañe a la fuente

### 4.2 Color — describe, no juzga

Regla nueva:

| Color | Significa |
|---|---|
| Verde `#2E9E5B` | terminado al 100 % |
| Azul `#123A63` | en marcha; el número ya dice cuánto |
| Gris `#98A2B3` | todavía no ha empezado (0 %) |
| Rojo `#B42318` | **solo** en la tabla de condicionantes, donde sí hay un problema |

El motivo no es estético. Con la regla actual, la página 1 de Mungia enseña
tres líneas en rojo —«Remates finales 0 %», «Remates exteriores 0 %»,
«Entrega 22 %»— en una obra que va al 80 %. Esas fases no van mal: son del
final de la obra y todavía no tocan. El color estaba afirmando algo falso.

### 4.3 Logo

Calcular la altura desde el ancho con el ratio nativo 3.638, en los dos sitios
(líneas 423 y 760), para que quede idéntico en todas las páginas. Limpiar el
fondo azul pálido.

## 5. Detalle técnico

### 5.1 Dónde vive Helvetica — siete sitios, cuatro funciones

| Línea | Función | Uso |
|---|---|---|
| 297 | `_style()` | fábrica de **todos** los párrafos |
| 336, 354 | `_grafico_tendencia` | rótulos de eje y fechas |
| 360 | `_grafico_tendencia` | etiqueta del último punto (bold) |
| 388 | `_grafico_distribucion` | leyenda |
| 402 | `_grafico_fases` | nombre de la fase |
| 410 | `_grafico_fases` | etiqueta de porcentaje (bold) |

`_style()` cubre todo el texto de párrafo. Los gráficos llevan la fuente
escrita a mano en cada `String()` y **no pasan por `_style()`**: si solo se
cambia la fábrica, los tres gráficos se quedan en Helvetica y el informe sale
con dos tipografías.

### 5.2 La regla de color está duplicada

Este es el punto donde es fácil dejar el trabajo a medias:

| Sitio | Qué colorea |
|---|---|
| `_color_pct()` líneas 317-322 | usada en 4 puntos: 411 (etiquetas del gráfico de fases), 463 y 465 (los KPI grandes), 555 (columna «Avance» de tajos que requieren atención) |
| `_make_mini_bar()` línea 305 | **copia propia del mismo umbral**, en un ternario en línea. Usada en 483 (barras de los KPI) y en 786, 792 (bloque ejecutivo) |

**Cambiar solo `_color_pct` deja las barras de los KPI con el semáforo viejo.**
Las dos tienen que moverse juntas, y lo suyo es que compartan una única
función.

### 5.3 Consecuencia que hay que aceptar o vetar

`_color_pct` colorea también **los dos números grandes de la cabecera**
(líneas 463 y 465). Con la regla nueva, el `78.7 %` de Mungia pasa de **verde
a azul marino**, porque no está al 100 %.

Es coherente con el principio aprobado —el color describe— y visualmente queda
serio. Pero es un cambio que Bixente no vio en la comparativa, donde el número
grande aparecía en verde.

**Valor por defecto: se aplica la regla a todo, incluidos los KPI de cabecera.**
Es lo coherente con el principio aprobado, y así el informe tiene una sola regla
de color en vez de dos. Si Bixente prefiere que el titular siga en verde cuando
va bien, es una línea: dejar los KPI de cabecera con su propia función de color
y aplicar la regla descriptiva solo a los desgloses por fase y por tajo.

### 5.4 Los ficheros tienen que estar en git

El `.gitignore` es lista blanca. La línea 14 publica
`!POST-VENTAS/logo_sagarde.jpg`, pero **no hay ninguna línea que publique
`_SISTEMA/MOTOR/assets/logo_sagarde.jpg`**, que es el que usa este informe.
Hoy ese fichero tiene copia única, como `CATALOGO_TAJOS.json`.

Un `.ttf` nuevo correría la misma suerte. Por tanto, el plan incluye dar de
alta en `.gitignore`:

- `_SISTEMA/MOTOR/assets/logo_sagarde.*`
- `_SISTEMA/MOTOR/assets/fonts/*.ttf` y `OFL.txt`

Sin esto, una restauración desde git deja el informe sin logo y sin fuente.

### 5.5 Dos fallos silenciosos a evitar

Son de la familia de fallos de este proyecto: algo declarado que el motor
ignora sin avisar.

**El logo ya falla en silencio hoy.** Líneas 423-425:

```python
logo = (Image(str(LOGO_PATH), width=48*mm, height=14*mm)
        if LOGO_PATH.is_file()
        else Paragraph('<b>SAGARDE</b>', _style('logo', 16, True, color=COL_BRAND)))
```

Si el fichero desaparece, el informe sale con la palabra «SAGARDE» en texto y
nadie se entera. **La fuente no debe repetir este patrón: si falta el `.ttf`,
el generador tiene que fallar con un error legible**, no volver a Helvetica.

**Las negritas pueden dejar de funcionar sin dar error.** El informe usa
etiquetas `<b>` dentro de los `Paragraph` por todas partes. En ReportLab, si se
registra la fuente pero no se declara la familia con `registerFontFamily`, el
`<b>` deja de tener efecto: el PDF se genera igual, plano, sin una sola queja.

## 6. Pruebas

En `unittest`, sin dependencias nuevas, junto a
`test_informe_ejecutivo_electrico.py`. Las cuatro se validan **por mutación**:
se rompe el código a propósito y la prueba tiene que enterarse.

1. **La negrita sigue siendo negrita.** Mutación: quitar `registerFontFamily`.
2. **La fuente incrustada es la pedida.** Se abre el PDF generado y se
   comprueba que dentro está IBM Plex Sans y no Helvetica.
   Mutación: dejar la fuente sin registrar.
3. **No se ha movido ni una cifra.** Se generan el informe antes y después y
   se comparan los números extraídos del PDF. Mutación: alterar un porcentaje.
4. **Falta la fuente → error ruidoso.** Se apunta a un `.ttf` inexistente y se
   comprueba que el generador falla con un mensaje legible, en vez de producir
   un PDF en Helvetica.

## 7. Criterio de terminado

- Las cuatro pruebas en verde, y las suites de motor y de obras sin regresión.
- El informe de Mungia regenerado conserva **80.7 % / 1159 de 1528** y sus
  cuatro páginas.
- Las otras obras del registro no se mueven: Gernika 76.3, Bolueta 43.5,
  OBRA PRUEBA 6.4.
- Comparación visual antes/después de las cuatro páginas, reportada a Bixente.
- El mapa mental actualizado si el inventario de ficheros cambia.
