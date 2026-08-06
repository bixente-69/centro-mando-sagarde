# Paginación A4 del generador de revisiones — Plan de implementación

> **Para trabajadores agénticos:** SUB-SKILL OBLIGATORIA: usar
> `superpowers:subagent-driven-development` o `superpowers:executing-plans`
> para ejecutar tarea a tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** que cada página del PDF impreso sea una tabla completa,
identificada y sin filas huérfanas, y que el generador avise —con datos, no con
un número inventado— cuando la selección de tajos no cabe en una hoja.

**Arquitectura:** el generador deja de pedirle al navegador que no parta las
tablas (`break-inside:avoid` es una sugerencia) y pasa a repartir las filas él
mismo con alturas medidas en milímetros. `generateHTML` emite una tabla por
(portal × grupo de plantas × **hoja de tajos**), cada una con su `thead`
completo. La verificación no es visual: se imprime el PDF real y se lee con el
propio `rejilla_hoja.py`.

**Stack:** HTML/CSS/JS sin dependencias en `generador_revisiones.html`;
pruebas con `unittest` de la biblioteca estándar; el arnés de PDF usa Node y
Playwright, ambos **opcionales** (la prueba se salta si faltan).

## Restricciones globales

- **Se toca un solo fichero de producción:**
  `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html`.
  `rejilla_hoja.py`, `leer_hoja_marcada.py`, `generar_todos.py`, los adaptadores
  y `obras_revisiones.js` **no se tocan**.
- **Nada de pytest ni dependencias nuevas en la suite.** `unittest` estándar.
  Node y Playwright sólo con `skipUnless`.
- **Invariantes con la lectura posterior** (§4 de la spec), que ninguna tarea
  puede romper:
  1. una tabla por página;
  2. toda página de tabla lleva su fila de identificación
     `OBRA · FECHA · BLOQUE · PORTAL · PLANTAS…`;
  3. ninguna página de tabla por debajo de 50 celdas;
  4. las claves `data-k` no cambian: `portal_id__planta_id__tajo_id__vivienda`;
  5. el nombre de fichero conserva la fecha DDMMAAAA.
- **`rejilla_hoja.tabla_de_tajos()` parsea este mismo HTML** con
  `let CAT = […\n];` y `const BASE_SOURCE_ID = {…\n};`. Ninguna edición puede
  alterar esas dos formas. Se comprueba en la Tarea 1 y otra vez al final.
- **Constantes medidas** (`antes_mungia.pdf`, 06/08/2026), no estimadas:
  fila de tajo **5,01 mm**, rótulo de fase **3,28 mm**, alto útil **284,00 mm**,
  `thead`+observaciones **34,30 mm** hoy y **28,00 mm** tras el recorte.
- **No ejecutar `Actualizar_Sagarde.bat`** en ningún momento.
- Ejecutar la suite con:
  `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`

## Estructura de ficheros

| fichero | responsabilidad |
|---|---|
| `generador_revisiones.html` | añade el bloque de paginación (constantes + 3 funciones puras), reescribe la emisión de tablas en `generateHTML`, el `@media print` y el diálogo de capacidad |
| `tests/test_paginacion_generador.py` | **nuevo.** Prueba la aritmética de paginación ejecutando las funciones puras del generador con Node, y comprueba los invariantes del HTML emitido |
| `verificar_hojas_pdf.py` | **nuevo.** Arnés manual: imprime el PDF A4 de las obras con ficha y lo valida con `rejilla_hoja.leer_pdf` |
| `tests/test_contrato_rejilla.py` | **nuevo.** Prueba barata y siempre activa: `tabla_de_tajos()` sigue leyendo el generador |
| `.gitignore` | añadir `verificar_hojas_pdf.py`… **no hace falta**: `!*.py` ya lo cubre |

---

### Tarea 1: Blindar el contrato con `rejilla_hoja` antes de tocar nada

Es la guarda que impide que cualquier edición posterior rompa en silencio la
lectura. Va primero a propósito.

**Ficheros:**
- Crear: `tests/test_contrato_rejilla.py`

**Interfaces:**
- Consume: `rejilla_hoja.tabla_de_tajos()`
- Produce: nada que usen otras tareas; es una red de seguridad.

- [ ] **Paso 1: escribir la prueba**

```python
# -*- coding: utf-8 -*-
"""El generador es la fuente de la traduccion nombre impreso -> catalogo.

`rejilla_hoja.tabla_de_tajos()` parsea `generador_revisiones.html` buscando
`let CAT = [...];` y `const BASE_SOURCE_ID = {...};`. Cualquier edicion del
generador que altere esas dos formas deja la lectura de hojas sin traduccion,
y el sintoma no aparece hasta que alguien intenta leer una hoja marcada.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rejilla_hoja


class ContratoConElGenerador(unittest.TestCase):

    def test_el_generador_sigue_traduciendo_sus_tajos_al_catalogo(self):
        tabla = rejilla_hoja.tabla_de_tajos()
        self.assertGreater(len(tabla), 40,
                           'la tabla de traduccion se ha quedado vacia o corta')
        self.assertIn('tabicado', tabla)
        self.assertEqual(tabla['tabicado']['id'], 'tabicado')

    def test_ningun_tajo_del_generador_queda_fuera_del_catalogo(self):
        # tabla_de_tajos() lanza HojaIlegible si hay huerfanos; que no lance
        # es la afirmacion.
        rejilla_hoja.tabla_de_tajos()


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Paso 2: ejecutarla y ver que pasa AHORA**

Run: `python -m unittest tests.test_contrato_rejilla -v`
Esperado: PASS (2 pruebas). Si falla, el generador ya está roto y hay que
parar antes de tocar nada.

- [ ] **Paso 3: prueba por mutación**

Cambiar temporalmente en `generador_revisiones.html` la línea 360
`let CAT = [` por `let CAT= [` y volver a ejecutar.
Esperado: FALLA con `HojaIlegible`.
**Restaurar la línea inmediatamente** (CLAUDE.md §4: nunca dejar una mutación
en disco).

- [ ] **Paso 4: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_contrato_rejilla.py"
git commit -m "Blindar el contrato entre el generador y la lectura de hojas

tabla_de_tajos() parsea el HTML del generador. Sin prueba, una edicion del
generador puede dejar la lectura sin traduccion y no enterarse nadie hasta
que falle una hoja real."
```

---

### Tarea 2: Constantes medidas y aritmética de paginación

**Ficheros:**
- Modificar: `generador_revisiones.html:421` (junto a `MAX_TAJOS_A4`)
- Crear: `tests/test_paginacion_generador.py`

**Interfaces:**
- Produce, en el ámbito del script del generador:
  - `MM = {filaTajo:5.01, filaGrupo:3.28, cabeceraTabla:28.0, altoUtil:284.0, colchon:4.0}`
  - `cupoFilasMM() -> number`
  - `alturaFilasMM(tajos: Tajo[]) -> number`
  - `repartirTajosEnHojas(tajos: Tajo[]) -> Tajo[][]`
- Consume: la forma `{id, name, g, p, a, orden}` de cada tajo.

- [ ] **Paso 1: escribir la prueba que falla**

```python
# -*- coding: utf-8 -*-
"""La paginacion se prueba ejecutando el JS real del generador, no una copia.

Copiar la aritmetica a Python la dejaria divergir del navegador en silencio,
que es justo la familia de fallos de este proyecto.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
GENERADOR = os.path.join(RAIZ, 'generador_revisiones.html')

NODE = shutil.which('node')


def ejecutar_en_node(expresion):
    """Evalua una expresion con el script del generador ya cargado."""
    lineas = open(GENERADOR, encoding='utf-8').read().split('\n')
    ini = next(i for i, l in enumerate(lineas) if l.strip() == '<script>' and i > 320)
    fin = next(i for i, l in enumerate(lineas) if l.strip() == '</script>' and i > ini)
    codigo = '\n'.join(lineas[ini + 1:fin])

    shim = """
    const nodo = new Proxy({}, {get:(t,k)=>k==='style'?{}:
      k==='classList'?{add(){},remove(){},contains:()=>false}:
      k==='options'?[]: (k==='value'||k==='innerHTML'||k==='textContent'||k==='className')?'':
      typeof k==='string'?()=>{}:undefined, set:()=>true});
    global.localStorage={getItem:()=>null,setItem(){},removeItem(){}};
    global.document={getElementById:()=>nodo,querySelectorAll:()=>[],
      querySelector:()=>nodo,createElement:()=>nodo,body:nodo};
    global.window=global;
    """
    guion = shim + '\nconsole.log(JSON.stringify(eval(' + json.dumps(
        codigo + '\n;(' + expresion + ')') + ')));'
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False,
                                     encoding='utf-8') as f:
        f.write(guion)
        ruta = f.name
    try:
        salida = subprocess.run([NODE, ruta], capture_output=True, text=True,
                                encoding='utf-8', timeout=60)
        if salida.returncode:
            raise AssertionError(salida.stderr[-1500:])
        return json.loads(salida.stdout.strip().splitlines()[-1])
    finally:
        os.unlink(ruta)


@unittest.skipUnless(NODE, 'node no esta instalado; la aritmetica no se prueba')
class AritmeticaDePaginacion(unittest.TestCase):

    def test_el_cupo_sale_de_las_medidas_reales(self):
        cupo = ejecutar_en_node('cupoFilasMM()')
        # 284 util - 28 de cabecera de tabla - 4 de colchon
        self.assertAlmostEqual(cupo, 252.0, places=2)

    def test_38_tajos_con_18_fases_caben_en_una_hoja(self):
        tajos = [{'id': f't{i}', 'name': f'T{i}', 'g': f'F{i % 18}'}
                 for i in range(38)]
        hojas = ejecutar_en_node(f'repartirTajosEnHojas({json.dumps(tajos)})')
        self.assertEqual(len(hojas), 1)

    def test_55_tajos_con_17_fases_necesitan_dos_hojas_equilibradas(self):
        tajos = [{'id': f't{i}', 'name': f'T{i}', 'g': f'F{i % 17}'}
                 for i in range(55)]
        hojas = ejecutar_en_node(f'repartirTajosEnHojas({json.dumps(tajos)})')
        self.assertEqual(len(hojas), 2)
        tamanos = sorted(len(h) for h in hojas)
        self.assertLessEqual(tamanos[1] - tamanos[0], 1,
                             f'reparto desequilibrado: {tamanos}')

    def test_no_se_pierde_ni_se_duplica_ningun_tajo(self):
        tajos = [{'id': f't{i}', 'name': f'T{i}', 'g': f'F{i % 17}'}
                 for i in range(55)]
        hojas = ejecutar_en_node(f'repartirTajosEnHojas({json.dumps(tajos)})')
        ids = [t['id'] for hoja in hojas for t in hoja]
        self.assertEqual(len(ids), 55)
        self.assertEqual(len(set(ids)), 55)
        self.assertEqual([t['id'] for t in tajos], ids, 'se altero el orden')

    def test_ninguna_hoja_supera_el_cupo(self):
        cupo = ejecutar_en_node('cupoFilasMM()')
        tajos = [{'id': f't{i}', 'name': f'T{i}', 'g': f'F{i % 17}'}
                 for i in range(55)]
        alturas = ejecutar_en_node(
            f'repartirTajosEnHojas({json.dumps(tajos)}).map(h=>alturaFilasMM(h))')
        for alto in alturas:
            self.assertLessEqual(alto, cupo, f'una hoja de {alto}mm sobre {cupo}')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Paso 2: ejecutar y verificar que falla**

Run: `python -m unittest tests.test_paginacion_generador -v`
Esperado: FALLA con `cupoFilasMM is not defined`.

- [ ] **Paso 3: implementar en `generador_revisiones.html`**

Sustituir la línea 421 `const MAX_TAJOS_A4 = 38;` por:

```javascript
/* ── PAGINACIÓN A4 ──────────────────────────────────────────────────────
   Alturas MEDIDAS con pdfplumber sobre el PDF real que produce el navegador
   (antes_mungia.pdf, 06/08/2026), no estimadas desde el CSS: el CSS declara
   la fila de tajo a 4.65mm y en el papel mide 5.01mm, porque bordes y
   relleno suman. Contar tajos e ignorar los rotulos de fase era el error de
   MAX_TAJOS_A4: 38 tajos con 18 fases necesitan 249.42mm y habia 249.70.
   Cabia por 0.28mm, que no es un diseño sino una casualidad. */
const MM = {
  filaTajo: 5.01,
  filaGrupo: 3.28,
  cabeceraTabla: 28.00,   // thead (3 filas) + fila de observaciones, ya recortados
  altoUtil: 284.00,       // A4 297 - 7 de margen arriba - 6 abajo
  colchon: 4.00,          // nada debe rozar el borde
};

function cupoFilasMM(){ return MM.altoUtil - MM.cabeceraTabla - MM.colchon; }

function alturaFilasMM(tajos){
  const fases = new Set((tajos||[]).map(t=>t.g));
  return (tajos||[]).length*MM.filaTajo + fases.size*MM.filaGrupo;
}

/* Cuantas hojas y con que reparto. Dos reglas:
   - equilibrado: 55 tajos en 2 hojas son 28 y 27, no 42 y 13. Se lee mejor
     y cuesta el mismo papel.
   - sin huerfanos: un rotulo de fase nunca se queda al final de una hoja con
     sus tajos en la siguiente. */
function repartirTajosEnHojas(tajos){
  const lista = Array.isArray(tajos) ? tajos : [];
  if(!lista.length) return [lista];
  const cupo = cupoFilasMM();
  let n = 1;
  while(n < lista.length && alturaFilasMM(lista)/n > cupo - MM.filaGrupo) n++;
  for(;; n++){
    const hojas = repartirEn(lista, n);
    if(hojas && hojas.every(h=>alturaFilasMM(h) <= cupo)) return hojas;
    if(n >= lista.length) return lista.map(t=>[t]);
  }
}

function repartirEn(lista, n){
  const porHoja = Math.ceil(lista.length/n);
  const hojas = [];
  for(let i=0; i<lista.length; i+=porHoja) hojas.push(lista.slice(i, i+porHoja));
  // Sin huerfanos: si una hoja empieza con el ultimo tajo de una fase que
  // quedo abierta atras no pasa nada (el rotulo se repite), pero una hoja
  // NUNCA puede terminar con un rotulo sin tajos: aqui no ocurre porque se
  // reparten tajos, no filas. La guarda vive en generateHTML, que emite el
  // rotulo junto al primer tajo de su fase en cada hoja.
  return hojas.length ? hojas : null;
}
```

Y añadir, justo debajo, la compatibilidad para el resto del fichero:

```javascript
const MAX_TAJOS_A4 = 38;   // sólo informativo; el limite real es cupoFilasMM()
```

- [ ] **Paso 4: ejecutar y verificar que pasa**

Run: `python -m unittest tests.test_paginacion_generador -v`
Esperado: PASS (5 pruebas).

- [ ] **Paso 5: verificar que no se rompió el contrato**

Run: `python -m unittest tests.test_contrato_rejilla -v`
Esperado: PASS.

- [ ] **Paso 6: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_paginacion_generador.py"
git commit -m "La capacidad de la hoja se mide en milimetros, no en tajos

MAX_TAJOS_A4=38 contaba tajos e ignoraba las 18 filas de fase, que ocupan
59mm. La hoja cabia por 0.28mm: por eso el navegador escupia restos de tabla
en paginas sueltas."
```

---

### Tarea 3: `generateHTML` emite una tabla por hoja

**Ficheros:**
- Modificar: `generador_revisiones.html:991-1044` (construcción de `blocks`)

**Interfaces:**
- Consume: `repartirTajosEnHojas`, `alturaFilasMM` de la Tarea 2.
- Produce: HTML con N `.planta-block` por grupo de plantas, cada uno con
  `thead` completo y, si N>1, un `<span class="hoja-de">` dentro de `th-ident`.

- [ ] **Paso 1: añadir la prueba de invariantes del HTML**

Añadir a `tests/test_paginacion_generador.py`:

```python
@unittest.skipUnless(NODE, 'node no esta instalado')
class HtmlEmitido(unittest.TestCase):
    """Los invariantes del §4 de la spec, sobre el HTML, sin necesidad de PDF."""

    def _hoja(self, obra):
        return ejecutar_en_node(
            f'(loadInstalledWork({json.dumps(obra)}), S.fecha="2026-08-07",'
            f' generateHTML(S.importData||{{}}))')

    def test_cada_tabla_lleva_su_fila_de_identificacion(self):
        html = self._hoja('obisporueta')
        tablas = html.count('<table class="rev-table">')
        idents = html.count('class="th-ident"')
        self.assertEqual(tablas, idents,
                         'hay tablas sin fila de identificacion')

    def test_orueta_parte_en_dos_hojas_por_tabla(self):
        html = self._hoja('obisporueta')
        self.assertEqual(html.count('<table class="rev-table">'), 16)

    def test_mungia_sigue_con_una_tabla_por_grupo_de_plantas(self):
        html = self._hoja('mungia')
        self.assertEqual(html.count('<table class="rev-table">'), 8)

    def test_no_se_pierde_ni_se_duplica_ninguna_celda(self):
        import re
        for obra, esperadas in [('mungia', 2356), ('gernika', 1216),
                                ('bolueta', 3686), ('obisporueta', 5610),
                                ('prueba', 1178)]:
            with self.subTest(obra=obra):
                html = self._hoja(obra)
                claves = re.findall(r'<td class="td-st[^"]*"[^>]*data-k="([^"]+)"', html)
                self.assertEqual(len(claves), esperadas)
                self.assertEqual(len(set(claves)), esperadas, 'claves repetidas')
```

- [ ] **Paso 2: ejecutar y verificar que falla**

Run: `python -m unittest tests.test_paginacion_generador.HtmlEmitido -v`
Esperado: FALLA — Orueta emite 8 tablas, no 16.

- [ ] **Paso 3: implementar**

En `generateHTML` (línea ~991), envolver la construcción de la tabla en un
bucle por hoja. Sustituir:

```javascript
    const blocks=groupCompleteFloors(portal.plantas).map((plantasGrupo,groupIndex)=>{
```

por:

```javascript
    const hojasDeTajos=repartirTajosEnHojas(tajos);
    const blocks=groupCompleteFloors(portal.plantas).flatMap((plantasGrupo,groupIndex)=>
      hojasDeTajos.map((tajosHoja,hojaIndex)=>{
```

Dentro, sustituir el cálculo de `rows` (línea ~1004) para que use sólo los
tajos de la hoja, agrupados por fase y **con el rótulo de fase repetido en cada
hoja donde aparezca alguno de sus tajos**:

```javascript
    const gruposHoja={};
    tajosHoja.forEach(t=>{ (gruposHoja[t.g]||(gruposHoja[t.g]=[])).push(t); });
    const rows = Object.entries(gruposHoja).map(([gn,gt])=>{
```

Añadir el rótulo de continuación dentro de `th-ident`, sólo cuando hay más de
una hoja:

```javascript
    const rotuloHoja = hojasDeTajos.length>1
      ? `<span class="hoja-de"> · HOJA ${hojaIndex+1} DE ${hojasDeTajos.length}</span>`
      : '';
```

y en la plantilla, cambiar la línea de identificación por:

```javascript
      <tr class="tr-ident"><th class="th-ident" colspan="${ncols}">${escHtml(obraUp)} · ${escHtml(fecha)} · ${escHtml(bloque.nombre)} · ${escHtml(portal.nombre)} · ${plantLabel}${rotuloHoja}</th></tr>
```

Cerrar el `flatMap` con `})).join('');` en lugar de `}).join('');`.

- [ ] **Paso 4: ejecutar y verificar que pasa**

Run: `python -m unittest tests.test_paginacion_generador -v`
Esperado: PASS.

- [ ] **Paso 5: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_paginacion_generador.py"
git commit -m "Una tabla por hoja, con el cabecero de viviendas repetido

Antes se emitia la tabla entera y se le pedia al navegador que no la partiera.
break-inside:avoid es una sugerencia: cuando no cabia, partia por donde caia."
```

---

### Tarea 4: CSS de impresión — portada, una tabla por página, `thead` recortado

**Ficheros:**
- Modificar: `generador_revisiones.html:1223-1249` (bloque `@media print`)

- [ ] **Paso 1: implementar**

Dentro de `@media print`, sustituir estas dos reglas:

```css
  .planta-block{page-break-inside:avoid;break-inside:avoid;border-radius:0}
  .planta-block+.planta-block{break-before:page;page-break-before:always}
```

por:

```css
  /* La cabecera y la leyenda ocupan la pagina 1 a proposito. Antes le robaban
     el sitio a la primera tabla y esa pagina salia con 7 celdas de nada.
     UN solo salto: ponerlo en las dos generaba dos paginas de portada. */
  .doc-header{break-after:auto;page-break-after:auto}
  .legend-strip{break-after:page;page-break-after:always}
  /* Cada tabla ocupa su pagina entera. Ahora cabe por construccion, asi que
     break-inside:avoid deja de ser una esperanza. */
  .planta-block{page-break-inside:avoid;break-inside:avoid;border-radius:0;
                break-after:page;page-break-after:always}
  .planta-block+.planta-block{break-before:auto;page-break-before:auto}
  .planta-block:last-child{break-after:auto;page-break-after:auto}
  .portal-section.portal-break{break-before:auto;page-break-before:auto}
  /* Colchon comprado en el thead. NO se encogen las casillas de marcar:
     siguen a 5.01mm, que es lo que necesita el boli en obra y lo que necesita
     el recorte que luego lee la IA. */
  .th-ident{padding:.6mm 2mm;font-size:8.2pt}
  .th-floor{padding:1.1mm 1mm}
  .th-apt{padding:.7mm .45mm}
  .tr-notes td{height:3.6mm;padding:.4mm 2mm}
```

Y añadir fuera del `@media print`, junto a `.th-ident`:

```css
.hoja-de{font-weight:800;opacity:.75}
```

- [ ] **Paso 2: comprobar a ojo en el navegador**

Abrir `generador_revisiones.html`, cargar OBRA PRUEBA, Vista previa, Ctrl+P.
Esperado: 5 páginas (portada + 4 tablas), ninguna con restos.

- [ ] **Paso 3: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html"
git commit -m "Portada propia y colchon comprado en el thead

La pagina 1 se desperdiciaba siempre: cabecera y leyenda ocupan 32mm y no
dejaban sitio a ninguna tabla completa. Y el thead de 34.3mm dejaba la hoja
en la cuerda floja de los 0.28mm."
```

---

### Tarea 5: El contador y el resumen hablan de hojas

**Ficheros:**
- Modificar: `generador_revisiones.html:803-808` (`updTjCount`)
- Modificar: `generador_revisiones.html:830-834` (`renderSummary`)

- [ ] **Paso 1: implementar `updTjCount`**

```javascript
function updTjCount(){
  const count=document.getElementById('tj-count');
  const hojas=repartirTajosEnHojas(getActiveTajos()).length;
  count.textContent = hojas<=1
    ? `${S.sel.size} tajos · 1 hoja por tabla`
    : `${S.sel.size} tajos · ${hojas} hojas por tabla`;
  count.className='tj-count'+(hojas>1?' over':'');
}
```

- [ ] **Paso 2: implementar en `renderSummary`**

Sustituir:

```javascript
  const overflow=Math.max(0,n-MAX_TAJOS_A4);
  const tables=entries.reduce((sum,{portal})=>sum+groupCompleteFloors(portal.plantas).length,0);
```

por:

```javascript
  const hojasPorTabla=repartirTajosEnHojas(getActiveTajos()).length;
  const tables=entries.reduce((sum,{portal})=>sum+groupCompleteFloors(portal.plantas).length,0)*hojasPorTabla;
```

Buscar con `grep -n "overflow" generador_revisiones.html` **todos** los usos
restantes de `overflow` en `renderSummary` y sustituir el texto de capacidad
por: `${tables} páginas de tabla · ${hojasPorTabla} hoja(s) por cada grupo de
plantas`.

- [ ] **Paso 3: comprobar en el navegador**

Cargar Orueta: el contador debe decir "55 tajos · 2 hojas por tabla" y el
resumen "16 páginas de tabla".

- [ ] **Paso 4: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html"
git commit -m "El contador dice hojas, que es lo que se imprime

'+17 sobre A4' no le decia a nadie cuantas hojas iban a salir."
```

---

### Tarea 6: Diálogo de capacidad con recuentos reales

**Ficheros:**
- Modificar: `generador_revisiones.html:1254-1264` (`confirmA4Capacity`)

**Interfaces:**
- Produce: `recuentoPorTajo() -> {[tajoId]: {x:number, total:number}}`
- Consume: `S.importData`, `getPortalEntries()`, `CAT`.

- [ ] **Paso 1: implementar el recuento**

```javascript
/* Cuantas celdas IMPRESAS de cada tajo estan ya en X.

   No se puede llamar a esto "terminado". Al generador solo le llegan X, M y /:
   generar_todos.py:237 documenta que P (pendiente confirmado), ? (desconocido)
   y N (no aplica) viajan los tres como celda vacia. Medido el 07/08/2026: si
   "terminado" fuese "todas sus celdas en X", Orueta -la unica obra que no
   cabe- tendria CERO tajos terminados, porque le cuentan como pendientes las
   celdas que en realidad son N. Por eso se enseña el recuento y decide
   Bixente, en vez de decidir el generador con un criterio ciego. */
function recuentoPorTajo(){
  const columnas=getPortalEntries().flatMap(({portal})=>
    portal.plantas.flatMap(pl=>pl.vivs.map(v=>({p:portal.id,f:pl.id,v}))));
  const datos=S.importData||{};
  const r={};
  CAT.forEach(t=>{ r[t.id]={x:0,total:0}; });
  columnas.forEach(c=>CAT.forEach(t=>{
    const e=r[t.id];
    e.total++;
    if(datos[`${c.p}__${c.f}__${t.id}__${c.v}`]==='X') e.x++;
  }));
  return r;
}
```

- [ ] **Paso 2: sustituir `confirmA4Capacity`**

```javascript
function confirmA4Capacity(){
  const activos=getActiveTajos();
  const hojas=repartirTajosEnHojas(activos).length;
  if(hojas<=1) return true;
  const cuenta=recuentoPorTajo();
  const alCien=activos.filter(t=>cuenta[t.id]&&cuenta[t.id].total
                                 &&cuenta[t.id].x===cuenta[t.id].total);
  const ranking=activos.slice()
    .sort((a,b)=>(cuenta[b.id].x/cuenta[b.id].total)-(cuenta[a.id].x/cuenta[a.id].total))
    .slice(0,8)
    .map(t=>`   ${t.name}: ${cuenta[t.id].x} de ${cuenta[t.id].total} celdas en X`)
    .join('\n');
  const opcion = alCien.length
    ? `Aceptar: quitar los ${alCien.length} tajos que estan al 100% de lo conocido y volver al paso 3.`
    : 'Aceptar: volver al paso 3 para quitar tajos a mano. Ninguno esta al 100% de lo conocido.';
  const seguir=window.confirm(
    `Con ${activos.length} tajos cada tabla ocupa ${hojas} hojas.\n\n`+
    `Los mas avanzados:\n${ranking}\n\n`+
    `${opcion}\nCancelar: generar igualmente en ${hojas} hojas.`
  );
  if(!seguir) return true;
  if(alCien.length){
    alCien.forEach(t=>{ S.sel.delete(t.id);
      const cb=document.getElementById('cb-'+t.id); if(cb) cb.checked=false; });
    showToast(`Quitados ${alCien.length} tajos al 100%`);
  } else {
    showToast('Ninguno esta al 100%: quitalos a mano');
  }
  goStep(3); renderTajos();
  return false;
}
```

- [ ] **Paso 3: comprobar en el navegador**

Cargar Orueta → Descargar. Debe decir "cada tabla ocupa 2 hojas", listar los 8
más avanzados con su recuento, y avisar de que **ninguno** está al 100%.
Cargar Gernika con los 38 tajos: no debe aparecer el diálogo (cabe en 1 hoja).

- [ ] **Paso 4: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html"
git commit -m "Cuando no caben, enseñar el recuento en vez de decidir a ciegas

El generador no distingue pendiente de no-aplica: solo le llegan X, M y /.
Decidir 'terminado' con ese dato es un criterio ciego, asi que decide Bixente
con el recuento delante."
```

---

### Tarea 7: Arnés de verificación por PDF

**Ficheros:**
- Crear: `verificar_hojas_pdf.py`
- Modificar: `tests/test_paginacion_generador.py` (prueba que lo invoca y se salta si falta Playwright)

- [ ] **Paso 1: crear el arnés**

```python
# -*- coding: utf-8 -*-
"""Imprime el PDF A4 real de cada obra con ficha y lo valida.

No es una comprobacion a ojo: se imprime como imprime Bixente y se lee con el
mismo `rejilla_hoja.py` que lee las hojas marcadas. Lo que se afirma es:
  - toda pagina de tabla tiene UNA tabla con >=50 celdas (por debajo de eso
    `leer_pdf` la descarta en silencio);
  - toda pagina de tabla lleva su identificacion;
  - la union de celdas de todas las paginas es la rejilla completa.

Uso:  python verificar_hojas_pdf.py [obra ...]
"""
import json
import os
import re
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

ESPERADAS = {'gernika': 1216, 'mungia': 2356, 'bolueta': 3686,
             'obisporueta': 5610, 'prueba': 1178}


def generar_html(obra, destino):
    """Ejecuta el script del generador con Node y escribe la hoja."""
    # (mismo shim que tests/test_paginacion_generador.py)
    ...


def imprimir_pdf(html, pdf):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch(channel='msedge')
        pag = nav.new_page()
        pag.goto('file:///' + os.path.abspath(html).replace('\\', '/'),
                 wait_until='load')
        pag.emulate_media(media='print')
        pag.pdf(path=pdf, format='A4', print_background=True,
                prefer_css_page_size=True)
        nav.close()


def validar(pdf, esperadas):
    import pdfplumber
    import rejilla_hoja
    problemas = []
    with pdfplumber.open(pdf) as doc:
        for n, pagina in enumerate(doc.pages, 1):
            tablas = pagina.find_tables()
            celdas = len(tablas[0].cells) if tablas else 0
            if celdas == 0:
                continue
            if celdas < rejilla_hoja.CELDAS_MINIMAS:
                problemas.append(
                    f'pagina {n}: {celdas} celdas, por debajo del minimo '
                    f'{rejilla_hoja.CELDAS_MINIMAS}: leer_pdf la descartaria '
                    f'sin avisar')
                continue
            if len(tablas) > 1:
                problemas.append(
                    f'pagina {n}: {len(tablas)} tablas; leer_pdf solo lee la '
                    f'primera y la segunda desapareceria')
            texto = pagina.extract_text() or ''
            if not re.search(r'\d{2}/\d{2}/\d{4}', texto[:600]):
                problemas.append(f'pagina {n}: sin fila de identificacion')
    paginas = rejilla_hoja.leer_pdf(pdf, rejilla_hoja.tabla_de_tajos())
    total = sum(len(t['celdas']) for _, t in paginas)
    if total != esperadas:
        problemas.append(f'celdas leidas {total}, esperadas {esperadas}')
    return problemas
```

- [ ] **Paso 2: completar `generar_html` reutilizando el shim de la Tarea 2**

Extraerlo a una función compartida en `tests/test_paginacion_generador.py` e
importarla, para no tener dos copias que diverjan.

- [ ] **Paso 3: añadir la prueba que se salta**

```python
def _hay_playwright():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(NODE and _hay_playwright(),
                     'sin node o sin playwright no se imprime el PDF')
class PdfReal(unittest.TestCase):

    def test_la_hoja_de_obra_prueba_sale_limpia(self):
        import verificar_hojas_pdf as V
        with tempfile.TemporaryDirectory() as tmp:
            html = os.path.join(tmp, 'h.html')
            pdf = os.path.join(tmp, 'h.pdf')
            V.generar_html('prueba', html)
            V.imprimir_pdf(html, pdf)
            self.assertEqual(V.validar(pdf, 1178), [])
```

- [ ] **Paso 4: ejecutar el arnés sobre las 5 obras**

Run: `python verificar_hojas_pdf.py`
Esperado: las 4 obras leíbles sin problemas. **Orueta fallará** por
`'Agujero Focos Pasillo' no esta en el catalogo comun` — es el problema de
datos declarado en §6 de la spec, ajeno a la paginación. El arnés debe
distinguirlo y reportarlo como "no verificable", no como fallo de paginación.

- [ ] **Paso 5: prueba por mutación**

Poner `MM.colchon = -40` en el generador y volver a lanzar el arnés.
Esperado: FALLA con páginas por debajo del mínimo.
**Restaurar el valor inmediatamente.**

- [ ] **Paso 6: commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/verificar_hojas_pdf.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_paginacion_generador.py"
git commit -m "Verificar la paginacion imprimiendo el PDF y leyendolo con rejilla_hoja

Comprobar la paginacion a ojo es como comprobar el porcentaje redondeado: no
se entera de que una pagina con 3 celdas se descarta en silencio."
```

---

### Tarea 8: Suite completa y regresión

- [ ] **Paso 1: suite entera**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`
Esperado: las 179 anteriores + las nuevas, todas en verde.

- [ ] **Paso 2: regresión de claves y recuentos**

Comprobar que las 5 obras siguen dando las mismas claves `data-k` y los mismos
estados precargados que antes del cambio: Mungia 2.356/1.887, Gernika
1.216/928, Bolueta 3.686/1.575, Orueta 5.610/2.314, Prueba 1.178/81.

- [ ] **Paso 3: `git status` limpio de mutaciones**

Run: `git status --short`
Esperado: sólo los ficheros del trabajo. Ninguna mutación de prueba olvidada.

---

### Tarea 9: Memoria y skill

**Ficheros:**
- Crear: `~/.claude/projects/…/memory/project_sagarde_paginacion_hoja.md`
- Modificar: `~/.claude/projects/…/memory/MEMORY.md`
- Modificar: `.claude/skills/sagarde-revision/SKILL.md`

- [ ] **Paso 1: memoria del proyecto**

Un fichero con: las constantes medidas, el dato de que la hoja cabía por
0,28 mm, los cinco invariantes con la lectura, y por qué "quitar terminados"
no puede decidirlo el generador.

- [ ] **Paso 2: puntero en `MEMORY.md`**

Una línea, con enlace y gancho.

- [ ] **Paso 3: actualizar la skill de revisión**

`sagarde-revision` describe cómo leer la hoja marcada. Añadir que:
- la página 1 del PDF es la **portada**, no una tabla, y `leer_pdf` la ignora
  por tener menos de 50 celdas;
- una tabla puede venir partida en varias hojas con el rótulo
  `· HOJA n DE N` al final de la identificación, y cada una es una tabla
  completa con su cabecero de viviendas.

- [ ] **Paso 4: commit**

```bash
git add .claude/skills/sagarde-revision/SKILL.md
git commit -m "La skill de revision conoce la portada y las hojas partidas"
```

---

## Autorrevisión

- **Cobertura de la spec:** §3.1 → Tareas 2 y 3. §3.2 → Tareas 2 y 5. §3.3 →
  Tarea 4. §3.4 → Tarea 4. §3.5 → Tarea 6. §4 invariantes → Tareas 1, 3 y 7.
  §5 verificación → Tareas 7 y 8. §6 fuera de alcance → sin tareas, correcto.
  El riesgo abierto del rótulo "HOJA n DE N" → Tarea 3 lo implementa y Tarea 7
  lo verifica contra `leer_pdf`.
- **Sin marcadores de posición:** el único `...` está en la Tarea 7 Paso 1 y la
  Tarea 7 Paso 2 lo resuelve explícitamente (reutilizar el shim de la Tarea 2).
- **Consistencia de nombres:** `cupoFilasMM`, `alturaFilasMM`,
  `repartirTajosEnHojas`, `recuentoPorTajo` se usan con el mismo nombre en
  todas las tareas.
