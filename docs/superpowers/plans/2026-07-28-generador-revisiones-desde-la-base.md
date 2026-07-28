# El generador de revisiones trabaja desde la base — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el generador ofrezca sólo obras con base de datos y produzca una hoja donde cada página A4 se identifique sola, para que la IA pueda leerla al volver de campo.

**Architecture:** Tres cambios independientes sobre dos ficheros. Uno en Python (blindar el contrato del que depende el filtro, con pruebas). Dos en el HTML del generador: filtrar el desplegable, y mover el rótulo de identificación dentro del `<thead>`, que es lo único que el navegador repite al partir una tabla entre páginas. Más un cambio de estilo a fondo blanco.

**Tech Stack:** Python 3.11 con `unittest` de la biblioteca estándar. HTML/CSS/JavaScript sin dependencias, en un único fichero autocontenido.

**Spec:** `docs/superpowers/specs/2026-07-28-generador-revisiones-desde-la-base-design.md`

## Global Constraints

- **No introducir pytest ni ninguna dependencia nueva.** Bixente lo ejecuta todo con ficheros `.bat`. Pruebas con `unittest` de la biblioteca estándar.
- **Suite completa:** `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`. Está en **57 pruebas en verde** antes de empezar.
- **No ejecutar `Actualizar_Sagarde.bat`.** Hace `git add -A` y publica en main. Ha capturado mutaciones de prueba abandonadas dos veces en un día.
- **Para regenerar hay que usar `--finalizar`, siempre.** `regenerar_obra.py` sustituye `publicar_registro_revisiones` por una función vacía (línea 85) y sólo `finalizar()` la restaura (línea 123). **Sin `--finalizar`, `obras_revisiones.js` NO se regenera** y cualquier comprobación en la app estaría mirando el fichero anterior sin avisar de nada. El comando correcto es:

  ```bash
  python "_MOTOR_SAGARDE/scripts/regenerar_obra.py" mungia --finalizar
  ```
- **Restaurar siempre cualquier fichero mutado** para una verificación, antes de commitear.
- **Ninguna de las cuatro tareas debe mover una sola cifra.** Línea base intocable: Mungia 79.8 · Gernika 76.3 · Bolueta 36.1 · Obispo Orueta 80.0. Si alguna se mueve, parar y entender por qué antes de seguir.
- **El fichero `generador_revisiones.html` tiene 1285 líneas y tres líneas de más de 400.000 caracteres** (los logos en base64, líneas 196, 222 y 332). No intentar leerlo entero: usar `offset`/`limit` o `sed -n`.
- **Existen DOS juegos de mapas de símbolo/clase**, y no son el mismo código: líneas 992-993 dentro de `generateHTML()` (los que pintan la hoja al generarla) y líneas 1081-1082 dentro del script embebido en la hoja generada (los que repintan al pulsar una celda). Ninguna tarea de este plan los modifica, pero si alguna vez se tocan, hay que tocar los dos.

---

## Estructura de ficheros

| Fichero | Responsabilidad | Tareas |
|---|---|---|
| `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_generar_todos.py` | Fijar el contrato de `fuente_estructura` del que depende el filtro | 1 |
| `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html` | Filtro del desplegable, cabecera repetida, estilo de impresión | 2, 3, 4 |

No se crean ficheros nuevos. `generar_todos.py` **no se modifica**: la Tarea 1 sólo añade pruebas sobre su comportamiento actual.

---

### Task 1: Blindar el contrato de `fuente_estructura`

El filtro del desplegable (Tarea 2) se apoya en que `fuente_estructura == 'ficha_obra.json'` aparezca **sólo** cuando la hoja sale de la ficha. Hoy es así, pero nada lo garantiza: si `crear_registro_revision` empezara a marcarlo, la app ofrecería obras sin base de datos y **nadie se enteraría**. Esta tarea no cambia comportamiento; fija el contrato antes de construir encima.

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_generar_todos.py` (añadir clase al final, antes de cualquier `if __name__`)

**Interfaces:**
- Consumes: `generar_todos.registro_revision_desde_ficha(obra, ficha, prioridades) -> dict|None`; `generar_todos.crear_registro_revision(obra, prioridades) -> dict|None`; `fixtures.ficha_minima()`, `fixtures.prioridades(items, revision='27/07/2026')`, `fixtures.item(...)`
- Produces: nada que consuman otras tareas. Es una red de seguridad.

- [ ] **Step 1: Comprobar el punto de partida**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`
Expected: `Ran 57 tests ... OK`

Si no son exactamente 57, parar y avisar: el punto de partida no es el que este plan asume.

- [ ] **Step 2: Añadir `import fixtures` si no está**

`tests/test_generar_todos.py` importa hoy `generar_todos as gt` pero puede no importar `fixtures`. Comprobar la cabecera (líneas 15-27) y, si falta, añadir `import fixtures` justo debajo de `import generar_todos as gt`. `fixtures.py` vive en el mismo directorio `tests/`, así que el import simple funciona: `test_ficha_obra.py` ya lo hace igual.

- [ ] **Step 3: Escribir las pruebas que fallan**

Añadir al final de `tests/test_generar_todos.py`:

```python
class TestContratoFuenteEstructura(unittest.TestCase):
    """El filtro del desplegable del generador se apoya en que
    `fuente_estructura` valga 'ficha_obra.json' SOLO cuando la hoja sale de
    la base. Si el camino deducido empezara a marcarlo, la app ofreceria
    obras sin base de datos y no habria forma de notarlo desde fuera."""

    OBRA = {'id': 'pruebas', 'nombre': 'OBRA DE PRUEBAS'}

    def _ficha(self, estados):
        ficha = fixtures.ficha_minima()
        # Sin esto la ficha sale 'rancia' y ensucia la salida con un aviso.
        ficha['revisiones'] = [{'fecha': '27/07/2026'}]
        ficha['estados'] = {
            clave: {'v': valor, 'f': '27/07/2026', 'r': 'rev_27072026'}
            for clave, valor in estados.items()
        }
        return ficha

    def test_la_hoja_desde_la_ficha_se_marca_como_base(self):
        registro = gt.registro_revision_desde_ficha(
            self.OBRA,
            self._ficha({'p1__pb__tubeado__A': 'X'}),
            fixtures.prioridades([]))
        self.assertIsNotNone(registro)
        self.assertEqual(registro['fuente_estructura'], 'ficha_obra.json')

    def test_la_hoja_deducida_no_se_marca_como_base(self):
        registro = gt.crear_registro_revision(
            self.OBRA, fixtures.prioridades([fixtures.item()]))
        self.assertIsNotNone(registro)
        self.assertNotEqual(registro.get('fuente_estructura'),
                            'ficha_obra.json')

    def test_lo_no_medido_no_viaja_a_la_hoja(self):
        """P (comprobado pendiente), ? (nadie lo ha mirado) y N (no aplica)
        salen como celda en blanco para poder escribir encima a boli."""
        registro = gt.registro_revision_desde_ficha(
            self.OBRA,
            self._ficha({'p1__pb__tubeado__A': 'X',
                         'p1__pb__tubeado__B': 'P',
                         'p1__1__tubeado__A': '?',
                         'p1__1__tubeado__B': 'N'}),
            fixtures.prioridades([]))
        self.assertIsNotNone(registro)
        self.assertEqual(sorted(registro['estados'].values()), ['X'])
```

- [ ] **Step 4: Ejecutar y ver qué pasa**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_generar_todos.TestContratoFuenteEstructura -v`

Estas tres pruebas describen el comportamiento **actual**, así que lo esperado es que **pasen a la primera**. Son una red, no un cambio.

Si `test_la_hoja_deducida_no_se_marca_como_base` falla con `assertIsNotNone`, es que `crear_registro_revision` necesita más de un item para producir un registro: ampliar la llamada a
`fixtures.prioridades([fixtures.item(), fixtures.item(unidad='B'), fixtures.item(planta='1')])`
y volver a ejecutar. No relajar el `assertIsNotNone`.

- [ ] **Step 5: Verificar por mutación que las pruebas sirven de algo**

En `generar_todos.py` línea 344, cambiar temporalmente
`'fuente_estructura': 'ficha_obra.json',` por `'fuente_estructura': 'inventado',`

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_generar_todos.TestContratoFuenteEstructura -v`
Expected: `test_la_hoja_desde_la_ficha_se_marca_como_base` FALLA.

Después, en la misma función línea 326, cambiar `if valor not in {'X', 'M', '/'}:` por `if valor not in {'X', 'M', '/', 'P', '?'}:`
Expected: `test_lo_no_medido_no_viaja_a_la_hoja` FALLA.

**Deshacer las dos mutaciones** y confirmar con `git diff` que `generar_todos.py` queda sin cambios. Una mutación olvidada ya se publicó dos veces en este proyecto.

- [ ] **Step 6: Ejecutar la suite completa**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`
Expected: `Ran 60 tests ... OK`

- [ ] **Step 7: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_generar_todos.py"
git commit -m "Fijar el contrato del que depende el filtro del desplegable

El generador va a ofrecer solo obras con fuente_estructura ficha_obra.json.
Nada garantizaba que el camino deducido no marcase tambien ese campo: si
lo hiciera, la app ofreceria obras sin base y no habria forma de notarlo.
Verificado por mutacion: las tres pruebas caen con el codigo roto."
```

---

### Task 2: El desplegable ofrece sólo obras con base de datos

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html:507-573` y `:896-919`

**Interfaces:**
- Consumes: `window.SAGARDE_OBRAS_REVISION` (array de registros de obra, cada uno con `id`, `nombre`, `revision`, `generado`, `bloques`, `catalog`, `estados`, y `fuente_estructura` sólo si sale de la ficha)
- Produces: `worksWithDatabase() -> Array` — usada por `renderInstalledWorks`, `loadInstalledWork`, `setSourceStatus` y `loadConfig`

- [ ] **Step 1: Añadir la función de filtrado**

En `generador_revisiones.html`, justo después de `installedWorks()` (línea 507-509), añadir:

```javascript
function worksWithDatabase(){
  // Solo las obras cuya estructura sale de ficha_obra.json. Las demas dan
  // hoja desde la ultima revision, que es justo lo que no sirve: la hoja
  // tiene que salir de la base para reflejar el estado real de los tajos.
  return installedWorks().filter(o=>o.fuente_estructura==='ficha_obra.json');
}
```

- [ ] **Step 2: Filtrar la lista del desplegable**

En `renderInstalledWorks()` (línea 529), sustituir:

```javascript
  const obras=installedWorks();
```

por:

```javascript
  const obras=worksWithDatabase();
```

La línea 533 que construye `'<option value="">— Configuración manual —</option>'` **no se toca**: la configuración manual sigue siendo la primera opción y sigue permitiendo montar una obra nueva desde cero.

- [ ] **Step 3: Que el caso vacío hable**

Sustituir el bloque `if(!source){...}` de `setSourceStatus` (líneas 514-521) por:

```javascript
  if(!source){
    const total=installedWorks().length;
    const conBase=worksWithDatabase().length;
    host.className='source-status empty';
    if(!total){
      host.textContent='No hay registro de portales disponible todavía. '+
        'Ejecuta la actualización de Sagarde para publicarlo.';
    } else if(!conBase){
      // Un recuento de cero es señal de alarma, no de "no aplica".
      host.textContent=`Hay ${total} obra${total!==1?'s':''} publicada`+
        `${total!==1?'s':''}, pero ninguna con base de datos todavía. `+
        'Para que una obra aparezca aquí hay que sembrar su ficha_obra.json.';
    } else {
      host.textContent='Configuración manual: la estructura y las celdas '+
        'no se leen de ningún portal.';
    }
    return;
  }
```

- [ ] **Step 4: Que no se pueda cargar por id una obra filtrada**

En `loadInstalledWork` (línea 541), sustituir:

```javascript
  const source=installedWorks().find(obra=>obra.id===id);
```

por:

```javascript
  const source=worksWithDatabase().find(obra=>obra.id===id);
```

- [ ] **Step 5: Que una configuración guardada de una obra sin base avise**

`loadConfig` (línea 903) reabre revisiones guardadas en el navegador. Una config guardada antes de este cambio puede apuntar a Gernika, Bolueta u Obispo Orueta. Sustituir la línea 903:

```javascript
  const source=cfg.sourceId?installedWorks().find(o=>o.id===cfg.sourceId):null;
```

por:

```javascript
  const source=cfg.sourceId?worksWithDatabase().find(o=>o.id===cfg.sourceId):null;
  if(cfg.sourceId&&!source){
    // La revision guardada apunta a una obra que ya no sale de la base.
    // Se abre igual, con sus datos de entonces, pero diciendolo.
    showToast('Esa obra ya no tiene base de datos: se abre como estaba guardada');
  }
```

- [ ] **Step 6: Comprobar en la app (la suite no alcanza el JavaScript)**

Abrir `generador_revisiones.html` en el navegador y comprobar, **mirándolo**:

1. El desplegable ofrece "— Configuración manual —" y **2026 MUNGIA ACR NEINOR**, y ninguna obra más.
2. Eligiendo Mungia, el estado dice "Memoria del portal cargada" con 1887 celdas precargadas.
3. Eligiendo "— Configuración manual —", el asistente completo sigue disponible: bloques, portales, plantas, viviendas y tajos editables a mano.

- [ ] **Step 7: Comprobar el caso "ninguna obra con base"**

Renombrar temporalmente la ficha:

```bash
mv "SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/ficha_obra.json" "SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/ficha_obra.json.bak"
```

Regenerar **con `--finalizar`** — sin él, `obras_revisiones.js` no se toca y la comprobación daría un falso negativo:

```bash
python "_MOTOR_SAGARDE/scripts/regenerar_obra.py" mungia --finalizar
```

Recargar la app. El desplegable debe quedarse sin obras y el mensaje debe decir que hay 4 obras publicadas pero ninguna con base de datos. **No puede quedarse vacío y mudo.**

Restaurar inmediatamente y volver a regenerar:

```bash
mv "SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/ficha_obra.json.bak" "SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/ficha_obra.json"
python "_MOTOR_SAGARDE/scripts/regenerar_obra.py" mungia --finalizar
```

Confirmar con `git status --short` que no queda nada movido y que Mungia vuelve a ofrecer sus 1887 celdas precargadas.

- [ ] **Step 8: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html"
git commit -m "El desplegable ofrece solo obras con base de datos

Ofrecia las cuatro por igual y las presentaba todas como memoria del
portal, aunque tres salgan de la ultima revision. Ahora solo aparecen las
que traen fuente_estructura ficha_obra.json: hoy, Mungia. Si no hubiera
ninguna lo dice con el recuento, en vez de quedarse vacio y mudo.

La configuracion manual se mantiene intacta."
```

---

### Task 3: Cada página A4 se identifica sola

Hoy el rótulo "ZR1 · ZR1.1 · Plantas PB · 1 · 2" vive en un `<div>` **fuera** de la tabla. Al partirse la tabla entre páginas, el navegador repite sólo el `<thead>`: la página de continuación conserva planta y vivienda pero **pierde bloque y portal**. Mungia tiene tres portales con las mismas letras de vivienda, así que una página suelta que diga "Planta PB · A2" es irresoluble.

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html:1013-1018` (estructura) y `:1165-1166` + `:1216` (estilo)

**Interfaces:**
- Consumes: dentro de `generateHTML()` están en ámbito `obraUp` (línea 961), `fecha` (línea 960), `ncols` (línea 976), `bloque`, `portal` y `plantLabel` (línea 1011). El bloque a modificar está anidado dentro de ese ámbito, así que las cuatro primeras son accesibles sin cambios.
- Produces: la clase CSS `.th-ident`, usada sólo aquí.

- [ ] **Step 1: Mover la identificación dentro del `<thead>`**

Sustituir las líneas 1013-1018 completas:

```javascript
    return `<div class="planta-block"><div class="block-hdr">
      <span class="block-title">${escHtml(bloque.nombre)} · ${escHtml(portal.nombre)} · ${plantLabel}</span>
    </div><div class="tbl-wrap"><table class="rev-table"><colgroup>${colTpl}</colgroup>
      <thead><tr><th class="th-floor th-floor-tajo" rowspan="2">TAJO</th>${floorHeads}</tr>
      <tr>${aptHeads}</tr></thead>
      <tbody>${rows}${noteRow}</tbody></table></div></div>`;
```

por:

```javascript
    // La identificacion va DENTRO del thead a proposito: es lo unico que el
    // navegador repite cuando una tabla se parte entre paginas. Fuera de la
    // tabla, una hoja de continuacion perderia el portal, y con tres
    // portales de mismas letras de vivienda eso es irresoluble al escanear.
    return `<div class="planta-block"><div class="tbl-wrap"><table class="rev-table"><colgroup>${colTpl}</colgroup>
      <thead>
      <tr class="tr-ident"><th class="th-ident" colspan="${ncols}">${escHtml(obraUp)} · ${escHtml(fecha)} · ${escHtml(bloque.nombre)} · ${escHtml(portal.nombre)} · ${plantLabel}</th></tr>
      <tr><th class="th-floor th-floor-tajo" rowspan="2">TAJO</th>${floorHeads}</tr>
      <tr>${aptHeads}</tr></thead>
      <tbody>${rows}${noteRow}</tbody></table></div></div>`;
```

- [ ] **Step 2: Dar estilo a la fila nueva**

En `sheetCSS()`, sustituir las reglas de `.block-hdr` y `.block-title` (líneas 1165-1166):

```css
.block-hdr{background:#E4EEF8;padding:3px 7px;border-bottom:1px solid rgba(26,53,88,.18)}
.block-title{font-size:9.5pt;font-weight:800;line-height:1.08;letter-spacing:.05em;text-transform:uppercase;color:#102A4C}
```

por:

```css
.th-ident{background:#E4EEF8;padding:3px 7px;text-align:left;font-size:9.5pt;font-weight:800;line-height:1.08;letter-spacing:.05em;text-transform:uppercase;color:#102A4C;border-bottom:1px solid rgba(26,53,88,.18)}
```

- [ ] **Step 3: Ajustar la regla de impresión**

En el bloque `@media print`, sustituir la línea 1216:

```css
  .block-hdr{padding:1.2mm 2mm}.block-title{font-size:8.4pt}
```

por:

```css
  .th-ident{padding:1.2mm 2mm;font-size:8.4pt}
```

- [ ] **Step 4: Comprobar que no queda ninguna referencia huérfana**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && grep -n "block-hdr\|block-title" generador_revisiones.html`
Expected: **ninguna coincidencia.** Si queda alguna, es una regla o un uso que se ha quedado sin pareja.

- [ ] **Step 5: Generar la hoja normal y comprobar que no ha empeorado**

Abrir la app, elegir Mungia, ir al paso 4 y usar "Vista previa". Comprobar que cada tabla muestra arriba una franja azul con obra, fecha, bloque, portal y plantas — la misma información de antes más obra y fecha.

- [ ] **Step 6: LA PRUEBA DE VERDAD — forzar el corte de página**

Este es el requisito por el que existe la tarea, y hay que verlo partido, no suponerlo.

1. En la app, con Mungia cargada, ir al paso 2 y **añadir plantas al primer portal** hasta que la tabla no quepa en un A4 (la app avisa al pasar de 38 tajos, pero aquí lo que se fuerza es el alto: añadir plantas hasta que la vista previa muestre la tabla partida).
2. Vista previa → imprimir a PDF.
3. Abrir el PDF y mirar **la segunda página de esa misma tabla**.

Expected: la página de continuación muestra la franja de identificación completa —obra, fecha, bloque, portal, plantas— y debajo las cabeceras de planta y vivienda. **Ninguna página puede quedar sin decir a qué portal pertenece.**

Si la franja no se repite: el navegador no está tratando la fila como cabecera. Comprobar que la `<tr class="tr-ident">` está dentro del `<thead>` y que ninguna regla CSS le pone `display` distinto de `table-row`.

- [ ] **Step 7: Verificar por mutación que la comprobación anterior sirve de algo**

Una comprobación visual que pasara igual con el código roto no verifica nada. Mover temporalmente la fila de identificación fuera de la cabecera: en el bloque de la Tarea 3 Step 1, sacar la línea `<tr class="tr-ident">…</tr>` del `<thead>` y colocarla como primera fila del `<tbody>`, justo antes de `${rows}`.

Repetir el Step 6 con la misma estructura que forzaba el corte.
Expected: la página de continuación **ya no muestra** la franja de identificación — sólo las cabeceras de planta y vivienda. Ése es exactamente el fallo que la tarea corrige, y confirma que la prueba del Step 6 lo detecta.

**Deshacer la mutación** y confirmar con `git diff` que el fichero queda como lo dejó el Step 1. Volver a ejecutar el Step 6 y ver la franja repetida otra vez.

- [ ] **Step 8: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html"
git commit -m "Cada pagina A4 dice a que obra y portal pertenece

El rotulo de bloque y portal vivia en un div fuera de la tabla, asi que
al partirse entre paginas el navegador repetia solo el thead: la hoja de
continuacion conservaba planta y vivienda pero perdia el portal. Con tres
portales de mismas letras de vivienda, una hoja suelta escaneada era
irresoluble y rompia el paso de lectura del ciclo.

Ahora la identificacion va dentro del thead, con obra y fecha anadidas.
Verificado forzando el corte e imprimiendo a PDF."
```

---

### Task 4: Fondo blanco y marcas impresas en gris

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html:1147-1150` (leyenda) y `:1182-1184` (celdas)

**Interfaces:**
- Consumes: las clases `done`, `half`, `prog`, `pend`, `ext` que generan las líneas 992-993.
- Produces: nada. Es sólo presentación.

- [ ] **Step 1: Celdas a fondo blanco con marca gris**

Sustituir las líneas 1182-1184:

```css
.td-st.done{background:#D5EDD9;color:#1A6030}.td-st.half{background:#E4F4EC;color:#1A6040}
.td-st.prog{background:#FEF7D5;color:#7A5000}.td-st.pend{background:#fff;color:#ccc}
.td-st.ext{background:#F5F0FA;color:#7A50A0}
```

por:

```css
/* Fondo blanco en todas: es mas facil tachar encima a boli y mas limpio de
   leer al escanear. La marca impresa va en gris medio y no en negro porque
   el discriminador tiene que estar en lo impreso, que es lo unico bajo
   control: el boli cambia segun el dia (negro, azul o pen digital) y ningun
   boli escribe en gris uniforme. */
.td-st.done{background:#fff;color:#6B7280}.td-st.half{background:#fff;color:#6B7280}
.td-st.prog{background:#fff;color:#6B7280}.td-st.pend{background:#fff;color:#ccc}
.td-st.ext{background:#fff;color:#6B7280}
```

- [ ] **Step 2: La leyenda tiene que reflejar la hoja**

Sustituir las líneas 1147-1150:

```css
.leg-dot.done{background:#D5EDD9;color:#1A6030;border-color:#1A6030}
.leg-dot.half{background:#E4F4EC;color:#1A6040;border-color:#1A6040}
.leg-dot.prog{background:#FEF7D5;color:#7A5000;border-color:#7A5000}
.leg-dot.pend{background:#fff;color:#aaa;border-color:rgba(26,53,88,.18)}
```

por:

```css
.leg-dot.done{background:#fff;color:#6B7280;border-color:#6B7280}
.leg-dot.half{background:#fff;color:#6B7280;border-color:#6B7280}
.leg-dot.prog{background:#fff;color:#6B7280;border-color:#6B7280}
.leg-dot.pend{background:#fff;color:#aaa;border-color:rgba(26,53,88,.18)}
```

- [ ] **Step 3: Comprobar que la identidad Sagarde sigue intacta**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && grep -c "LOGO_URI" generador_revisiones.html`
Expected: al menos 2 (definición y uso en la cabecera).

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && grep -n "1A3558" generador_revisiones.html | head -3`
Expected: el azul corporativo sigue en la cabecera del documento y en las cabeceras de tabla. **Este cambio no toca el azul ni el logo**: sólo el fondo de las celdas de estado.

- [ ] **Step 4: Mirarlo impreso**

Vista previa → imprimir a PDF → abrirlo. Comprobar:

1. Ninguna celda tiene fondo de color; toda la rejilla es blanca.
2. Las `X` y `M` impresas se leen en gris, no en negro ni en verde.
3. El logo, la cabecera azul y la franja de identificación siguen ahí.
4. La leyenda de arriba muestra los símbolos en gris, coherente con la hoja.

- [ ] **Step 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html"
git commit -m "Fondo blanco y marcas impresas en gris

El sombreado de color no aporta nada que Bixente no sepa ya por otros
medios, y estorba para tachar sobre la hoja de campo. Todo blanco.

Las marcas impresas pasan a gris medio en vez de verde: al volver de
campo hay que distinguir lo impreso de lo escrito a boli, y el color del
boli cambia segun el dia. El discriminador se pone en lo impreso, que es
lo unico bajo control. Ningun boli escribe en gris uniforme.

Logo, azul corporativo y tipografia sin tocar."
```

---

## Verificación final, antes de dar nada por bueno

- [ ] **Suite completa en verde**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`
Expected: `Ran 60 tests ... OK`

- [ ] **Ninguna cifra se ha movido**

Regenerar las cuatro obras **con `--finalizar`** y comparar contra la línea base:

```bash
python "_MOTOR_SAGARDE/scripts/regenerar_obra.py" mungia gernika bolueta obisporueta --finalizar
```

Si el script no acepta varias obras en una llamada, hacerlas de una en una y **terminar siempre con una pasada `--finalizar`**, que es la única que republica `obras_revisiones.js`.

| Obra | `pct_ponderado` esperado |
|---|---|
| Mungia | 79.8 |
| Gernika | 76.3 |
| Bolueta | 36.1 |
| Obispo Orueta | 80.0 |

Ninguna de las cuatro tareas toca el cálculo: son pruebas, filtro de presentación, maquetación y estilo. **Si alguna cifra se mueve, hay un efecto colateral: parar y entenderlo antes de seguir.**

Comprobar además que Mungia sigue exportando 1887 estados precargados y que su `fuente_estructura` sigue siendo `ficha_obra.json`.

- [ ] **El árbol está limpio de mutaciones**

Run: `git status --short`
Expected: sin cambios sin commitear. Cualquier fichero mutado durante una verificación tiene que estar restaurado.

- [ ] **Reportar a Bixente el antes/después de las cuatro obras.** Aplicar en silencio una corrección que mueve cifras es repetir el problema desde el otro lado. Si nada se ha movido, decirlo igualmente: es el resultado esperado y su confirmación es parte de la entrega.

- [ ] **NO ejecutar `Actualizar_Sagarde.bat`.** La publicación la decide Bixente.
