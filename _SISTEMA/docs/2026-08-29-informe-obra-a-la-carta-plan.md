# Informe de obra a la carta — Plan de ejecución

> **Para quien ejecute esto (Codex):** cada tarea es un commit propio.
> Ejecutar en orden, nunca en paralelo con otra tarea de este plan ni con
> otro trabajo que toque `panel_obra.py` — es la misma familia de choques
> ya sufrida en este repo cuando dos procesos escriben el mismo fichero a
> la vez. Antes de empezar cada tarea, `git status` limpio. Al terminar
> cada tarea: pruebas en verde, commit, y solo entonces se pasa a la
> siguiente tarea (nueva instrucción de Claude).

**Diseño aprobado:** [2026-08-29-informe-obra-a-la-carta-diseno.md](2026-08-29-informe-obra-a-la-carta-diseno.md)

**Objetivo:** un botón "📋 Informe de obra" junto a "📄 Informe Ejecutivo PDF"
en el panel de cada obra, que abre un menú de checkboxes por sección y
subsección, muestra una vista previa con la identidad visual del informe
ejecutivo, y genera el PDF con el diálogo de impresión del navegador (A4) —
sin servidor, sin infraestructura nueva, tan vivo como la última vez que se
regeneró `panel.html`.

**Arquitectura:** `bloque_prioridades()` se divide en piezas nombradas sin
cambiar su salida actual (Tarea 1). `generar_panel()` reutiliza esas piezas
y las demás secciones que ya calcula para montar un diccionario
`secciones_informe`, que se embebe como JSON inerte dentro de `panel.html`
(Tarea 2). Un botón nuevo abre un menú de checkboxes (Tarea 3) cuya lógica
en JavaScript —calcada del patrón de `generador_revisiones.html`— arma con
esas piezas ya existentes una página nueva en una pestaña aparte y dispara
`window.print()` (Tarea 4). Ninguna cifra se recalcula: todo sale de las
mismas cadenas HTML que el panel ya muestra y ya prueba.

**Tech Stack:** Python 3 (sin dependencias nuevas), HTML/CSS/JS vanilla
(sin frameworks, igual que el resto del proyecto), `unittest` de la
biblioteca estándar.

## Global Constraints

- No introducir pytest ni ninguna dependencia nueva — solo `unittest`.
- No modificar archivos no relacionados con esta funcionalidad.
- Ninguna cifra de una sección (tajos bloqueados, avance, etc.) se calcula
  por un camino independiente al que ya usa `panel_obra.py` — siempre se
  reutiliza la cadena HTML ya computada.
- Cada tarea termina con la suite completa en verde antes de commitear:
  `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`
- No tocar `panel_server.py`, no añadir servidores, nube ni contraseñas.
- Todo el código nuevo vive en `panel_obra.py` (Python) y dentro de la
  plantilla HTML que ya genera esa misma función — no se crean ficheros
  `.js`/`.css` sueltos, siguiendo el patrón ya usado en este proyecto
  (todo el panel es un único HTML autocontenido).

---

## Ficheros

- **Modificar:** `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py`
  - `bloque_prioridades()` (línea 1111) se convierte en una función delgada.
  - Nueva función `bloque_prioridades_partes()` con la lógica de cálculo
    (el cuerpo que hoy tiene `bloque_prioridades`).
  - `generar_panel()` (línea 1487): nueva variable `secciones_informe`,
    nuevo bloque `<script id="secciones-informe">` embebido, botón nuevo en
    la cabecera, nueva sección/menú de selección y su JS, todo dentro del
    f-string `html` que ya construye.
  - `ESTILOS` (línea 25): nuevas reglas CSS para el botón, el menú de
    checkboxes y la plantilla de impresión.
- **Modificar:**
  `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py`
  — no se toca ningún test existente (deben seguir en verde tal cual), solo
  se añaden clases de test nuevas al final del fichero.
- **Crear:**
  `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_obra_a_la_carta.py`
  — tests de `generar_panel()` para el botón, el JSON embebido y el
  contenido del menú/JS.

---

### Task 1: Dividir `bloque_prioridades` en piezas nombradas sin cambiar su salida

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py:1111-1484`
- Test: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py`

**Interfaces:**
- Produce: `bloque_prioridades_partes(prioridades, tareas_manual=None, documentos=None, obra='', avance_pct=None) -> dict | str`.
  Devuelve un `str` en el caso `sin_base` (igual que hoy). En el caso normal
  devuelve un `dict` con estas claves, todas `str` de HTML:
  `bento_command`, `estado_obra_html`, `avisos_prio`, `script_indice`,
  `tareas_manual_html`, `dudas_html`, `ejecucion_html`, `bloqueado_html`,
  `sin_revisar_html`, `orden_html`, `prevision_html`, `viable_html`,
  `otros_gremios_html`, `dudas_inventario_html`, `terminado_html`.
- Consume: nada nuevo — exactamente los mismos parámetros que
  `bloque_prioridades` recibe hoy.

Esta tarea es un movimiento mecánico: el cuerpo de `bloque_prioridades`
(líneas 1118 a 1415, todo el cálculo) no cambia ni una línea. Solo cambia
el `return` final (líneas 1416-1484): en vez de concatenar todo en un
único string, se devuelve el dict. `bloque_prioridades` pasa a ser un
envoltorio de 15 líneas que reconstruye el string exacto de siempre.

- [ ] **Step 1: Confirmar que las pruebas actuales están en verde antes de tocar nada**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -p "test_panel_prioridades.py" -v`
Expected: todas las pruebas PASAN (son la red de seguridad de esta tarea).

- [ ] **Step 2: Renombrar la función actual y cambiar su return final**

En `panel_obra.py`, cambiar la línea 1111:

```python
def bloque_prioridades(prioridades, tareas_manual=None, documentos=None,
                       obra='', avance_pct=None):
```

por:

```python
def bloque_prioridades_partes(prioridades, tareas_manual=None,
                              documentos=None, obra='', avance_pct=None):
    """Calcula las piezas de Prioridades por separado, sin concatenarlas.

    Usada por bloque_prioridades() (reconstruye el HTML de siempre) y por
    el informe de obra a la carta (usa solo las piezas marcadas). El
    cálculo vive aquí una sola vez: ninguna cifra se recalcula por un
    camino distinto para el selector.
    """
```

No tocar ninguna línea entre la nueva cabecera y el `return` final (líneas
1119 a 1415 del fichero original: siguen calculando `resumen_prio`,
`tareas_manual_html`, `dudas_html`, `ejecucion_html`,
`inventario_por_codigo`, `orden_html`, `prevision_html`,
`segmentos_salud`, `leyenda_salud`, etc. exactamente igual que hoy).

Sustituir el `return` final (líneas 1416-1484 del fichero original), que
hoy es:

```python
    return f"""
    <section class="bento-command" aria-label="Centro de mando de prioridades">
      ...
    </section>
    {estado_obra_html}
    {avisos_prio}
    {_SCRIPT_INDICE_PRIORIDADES}
    {grupo_actuar_html}
    {grupo_consulta_html}"""
```

por (mantener íntegro el bloque `f"""<section class="bento-command" ...>
... </section>"""` tal cual está hoy — solo cambia lo que hay después):

```python
    bento_command = f"""
    <section class="bento-command" aria-label="Centro de mando de prioridades">
      <div class="bento-health">
        <div class="bento-health-top">
          <div>
            <span class="bento-eyebrow">Centro de mando · Prioridades</span>
            <h2>Estado del proyecto</h2>
            <p class="bento-health-meta">Revisión utilizada: {e(prioridades.get('revision'))} · Motor v{e(prioridades.get('version'))} · catálogo v{e(prioridades.get('catalogo_version'))}</p>
          </div>
          <div class="bento-health-side">
            <div class="bento-attention{atencion_clase}">
              <strong>{e(atencion_titulo)}</strong>
              <span>{e(atencion_detalle)}</span>
            </div>
            <div class="bento-stat"><strong>{e(resumen_prio.get('inventario_total', 0))}</strong><span>tipos de tajo agrupados</span></div>
            <div class="bento-stat"><strong>{avance_html}</strong><span>completado · avance estimado</span></div>
          </div>
        </div>
        <div class="bento-segments" role="img" aria-label="Distribución de la salud del proyecto">{segmentos_salud}</div>
        <div class="bento-legend">{leyenda_salud}</div>
      </div>

      <div class="bento-grid">
        <a class="bento-link bento-card bento-hero indice-nav-link" href="#{_ID_SEC_EJECUCION}" data-abre="{_ID_SEC_EJECUCION}">
          <div class="bento-hero-head">
            <div>
              <div class="bento-card-kicker"><span class="bento-dot"></span>Acción principal</div>
              <h3>Qué hacer ahora</h3>
              <p class="bento-card-copy">Orden lógico de ejecución de tajos</p>
            </div>
            <div class="bento-hero-total"><strong>{e(n_listos_real)}</strong><span>tajos listos</span></div>
          </div>
          <div class="bento-breakdown">
            <div class="bento-breakdown-item" style="--bento-color:var(--ok);"><span>Listos</span><strong>{e(n_listos_real)}</strong></div>
            <div class="bento-breakdown-item" style="--bento-color:var(--warn);"><span>Verificar</span><strong>{e(n_verificar_real)}</strong></div>
          </div>
        </a>

        <a class="bento-link bento-card bento-small indice-nav-link" style="--bento-color:var(--warn);" href="#{inventario_por_codigo['BLOQUEADO']['id']}" data-abre="{inventario_por_codigo['BLOQUEADO']['id']}">
          <div class="bento-card-kicker"><span class="bento-dot"></span>Dependencias</div><h3>Tajos bloqueados</h3>
          <div class="bento-number">{e(n_bloqueados)}</div><div class="bento-number-label">tajos propios con dependencias</div>
        </a>

        <a class="bento-link bento-card bento-small indice-nav-link" style="--bento-color:var(--accent2);" href="#{_ID_SEC_TAREAS}" data-abre="{_ID_SEC_TAREAS}">
          <div class="bento-card-kicker"><span class="bento-dot"></span>Manual</div><h3>Tareas manuales</h3>
          <div class="bento-number">{n_tareas_pendientes}</div><div class="bento-number-label">pendientes declaradas en la ficha</div>
        </a>

        <a class="bento-link bento-card bento-half indice-nav-link" style="--bento-color:var(--bad);" href="#{inventario_por_codigo['SIN_REVISAR']['id']}" data-abre="{inventario_por_codigo['SIN_REVISAR']['id']}">
          <div class="bento-card-kicker"><span class="bento-dot"></span>Revisar</div><h3>Sin revisar nunca</h3>
          <div class="bento-number">{e(resumen_prio.get('sin_revisar', 0))}</div><div class="bento-number-label">tajos que nadie ha mirado todavía · {e(resumen_prio.get('unidades_sin_revisar', 0))} celdas</div>
        </a>

        <a class="bento-link bento-card bento-half indice-nav-link" style="--bento-color:{'var(--warn)' if n_preguntas else 'var(--ok)'};" href="#{_ID_SEC_DUDAS}" data-abre="{_ID_SEC_DUDAS}">
          <div class="bento-card-kicker"><span class="bento-dot"></span>Decisiones</div><h3>Preguntas pendientes</h3>
          <div class="bento-number">{e(n_preguntas)}</div><div class="bento-number-label">resolver antes de decidir</div>
        </a>
      </div>

      <nav class="bento-reference" aria-label="Consulta y referencia">
        <div class="bento-reference-title">Consulta y referencia</div>
        <div class="bento-chips">{chips_consulta_html}</div>
      </nav>
    </section>"""

    return {
        'bento_command': bento_command,
        'estado_obra_html': estado_obra_html,
        'avisos_prio': avisos_prio,
        'script_indice': _SCRIPT_INDICE_PRIORIDADES,
        'tareas_manual_html': tareas_manual_html,
        'dudas_html': dudas_html,
        'ejecucion_html': ejecucion_html,
        'bloqueado_html': inventario_por_codigo['BLOQUEADO']['html'],
        'sin_revisar_html': inventario_por_codigo['SIN_REVISAR']['html'],
        'orden_html': orden_html,
        'prevision_html': prevision_html,
        'viable_html': inventario_por_codigo['VIABLE']['html'],
        'otros_gremios_html': inventario_por_codigo['OTROS_GREMIOS']['html'],
        'dudas_inventario_html': inventario_por_codigo['DUDAS']['html'],
        'terminado_html': inventario_por_codigo['TERMINADO']['html'],
    }
```

- [ ] **Step 3: Añadir la nueva `bloque_prioridades` envoltorio justo debajo**

Inmediatamente después de la función `bloque_prioridades_partes` (que ahora
termina donde antes terminaba `bloque_prioridades`), añadir:

```python
def bloque_prioridades(prioridades, tareas_manual=None, documentos=None,
                       obra='', avance_pct=None):
    """HTML de la pestana Prioridades — envoltorio sobre
    bloque_prioridades_partes() que reconstruye el string de siempre.

    Separado de generar_panel para poder probarlo sin montar una obra entera:
    un dato que se calcula y no se pinta es lo mismo que no calcularlo.
    """
    partes = bloque_prioridades_partes(
        prioridades, tareas_manual=tareas_manual, documentos=documentos,
        obra=obra, avance_pct=avance_pct)
    if isinstance(partes, str):
        return partes
    return (
        partes['bento_command']
        + partes['estado_obra_html']
        + partes['avisos_prio']
        + partes['script_indice']
        + partes['tareas_manual_html']
        + partes['dudas_html']
        + partes['ejecucion_html']
        + partes['bloqueado_html']
        + partes['sin_revisar_html']
        + partes['orden_html']
        + partes['prevision_html']
        + partes['viable_html']
        + partes['otros_gremios_html']
        + partes['dudas_inventario_html']
        + partes['terminado_html']
    )
```

También hay que localizar, dentro del cuerpo movido a
`bloque_prioridades_partes`, la comprobación `sin_base` (era la primera
comprobación de la función original) y dejarla intacta al principio de
`bloque_prioridades_partes` — sigue haciendo `return (...)` de un string
como hoy, antes de llegar a ningún cálculo.

- [ ] **Step 4: Ejecutar la suite existente de Prioridades — no debe cambiar ni una prueba**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -p "test_panel_prioridades.py" -v`
Expected: las mismas pruebas de antes, todas PASS, sin haber tocado el
fichero de test. Si alguna falla, el string reconstruido no es
byte-idéntico al de antes — revisar el orden de concatenación del Step 3
contra el `return` original citado en el Step 2.

- [ ] **Step 5: Ejecutar la suite completa del proyecto**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`
Expected: mismo resultado que antes de esta tarea (mismo número de
pruebas en verde; las 4 omitidas de Obispo Orueta siguen omitidas, nada
más cambia).

- [ ] **Step 6: Añadir pruebas para `bloque_prioridades_partes`**

Añadir al final de `tests/test_panel_prioridades.py`:

```python
class TestBloquePrioridadesPartes(unittest.TestCase):
    """bloque_prioridades_partes() es la fuente unica: bloque_prioridades()
    y el informe de obra a la carta tienen que leer de aqui, nunca
    recalcular por su cuenta."""

    def test_devuelve_un_dict_con_las_claves_esperadas(self):
        partes = panel_obra.bloque_prioridades_partes(_prioridades())
        claves_esperadas = {
            'bento_command', 'estado_obra_html', 'avisos_prio',
            'script_indice', 'tareas_manual_html', 'dudas_html',
            'ejecucion_html', 'bloqueado_html', 'sin_revisar_html',
            'orden_html', 'prevision_html', 'viable_html',
            'otros_gremios_html', 'dudas_inventario_html', 'terminado_html',
        }
        self.assertEqual(set(partes.keys()), claves_esperadas)

    def test_sin_base_devuelve_string_no_dict(self):
        partes = panel_obra.bloque_prioridades_partes(
            _prioridades(sin_base=True, avisos=['sin base']))
        self.assertIsInstance(partes, str)
        self.assertIn('sin base', partes)

    def test_concatenar_las_partes_da_el_mismo_html_que_bloque_prioridades(self):
        """La prueba mas importante de esta tarea: bloque_prioridades()
        tiene que seguir devolviendo exactamente lo mismo que antes de
        dividir la funcion. Si un dia alguien cambia el orden en uno de
        los dos sitios sin cambiar el otro, esta prueba lo detecta."""
        prioridades = _prioridades(
            resumen={'listos': 1, 'bloqueados': 1, 'sin_revisar': 1},
            items=[{
                'orden': 1, 'situacion': 'LISTO', 'trabajo': 'A',
                'n_unidades': 1, 'n_celdas': 1, 'n_ubicaciones': 1,
                'ubicaciones': [], 'estado_actual': 'Pendiente',
                'motivo': 'x', 'fase_nombre': 'f', 'orden_ejecucion': 1,
                'ambito_nombre': 'Viviendas',
            }],
            inventario=[{
                'seccion': 'BLOQUEADO', 'trabajo': 'B', 'propiedad': 'propio',
                'orden_ejecucion': 2, 'fase_nombre': 'f', 'n_ubicaciones': 3,
                'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
                'subtajos': [],
            }],
        )
        tareas_manual = [{
            'Tarea': 'Revisar cuadro', 'Origen': 'Parte de obra',
            'Fecha': '22/08/2026', 'Archivo': '', 'Estado': 'Pendiente',
        }]

        html_directo = panel_obra.bloque_prioridades(
            prioridades, tareas_manual=tareas_manual, documentos=[])
        partes = panel_obra.bloque_prioridades_partes(
            prioridades, tareas_manual=tareas_manual, documentos=[])
        html_reconstruido = (
            partes['bento_command'] + partes['estado_obra_html']
            + partes['avisos_prio'] + partes['script_indice']
            + partes['tareas_manual_html'] + partes['dudas_html']
            + partes['ejecucion_html'] + partes['bloqueado_html']
            + partes['sin_revisar_html'] + partes['orden_html']
            + partes['prevision_html'] + partes['viable_html']
            + partes['otros_gremios_html'] + partes['dudas_inventario_html']
            + partes['terminado_html']
        )
        self.assertEqual(html_directo, html_reconstruido)
```

- [ ] **Step 7: Ejecutar las pruebas nuevas y confirmar que pasan**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -p "test_panel_prioridades.py" -v`
Expected: todo PASS, incluidas las 3 pruebas nuevas de
`TestBloquePrioridadesPartes`.

- [ ] **Step 8: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py"
git commit -m "Divide bloque_prioridades en piezas nombradas sin cambiar su salida

Paso 1 del informe de obra a la carta: bloque_prioridades_partes()
expone las 5 piezas (estado del proyecto, que hacer ahora, tajos
bloqueados, tareas manuales, sin revisar) que necesitara el selector,
sin recalcular nada — bloque_prioridades() sigue devolviendo byte a
byte el mismo HTML de siempre."
```

---

### Task 2: Montar `secciones_informe` en `generar_panel` y embeberlo como JSON

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py:1487-1795` (función `generar_panel`)
- Test: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_obra_a_la_carta.py` (nuevo)

**Interfaces:**
- Consume: `bloque_prioridades_partes()` de la Tarea 1 — se llama UNA vez
  dentro de `generar_panel` (sustituyendo la llamada actual a
  `bloque_prioridades`), y su resultado se usa tanto para pintar la
  pestaña Prioridades como para `secciones_informe['prioridades']`.
- Produce: dict `secciones_informe` con claves
  `trabajos`, `materiales`, `personal`, `prioridades` (a su vez un dict con
  `estado_proyecto`, `que_hacer_ahora`, `tajos_bloqueados`,
  `tareas_manuales`, `sin_revisar`), `riesgos`, `normativa`, `documentos`,
  `cierre` — todos los valores son `str` de HTML, embebido en el HTML de
  salida como `<script id="secciones-informe" type="application/json">`.

- [ ] **Step 1: Cambiar la llamada a `bloque_prioridades` dentro de `generar_panel` por `bloque_prioridades_partes`**

En `panel_obra.py`, dentro de `generar_panel`, sustituir (línea 1601-1605
del fichero original):

```python
    # ---- PRIORIDADES E INVENTARIO COMPLETO DE TAJOS (motor v4) ----
    prioridades_html = bloque_prioridades(
        prioridades, tareas_manual=ficha.get('tareas', []),
        documentos=documentos, obra=obra,
        avance_pct=kpis.get('pct_ponderado'))
```

por:

```python
    # ---- PRIORIDADES E INVENTARIO COMPLETO DE TAJOS (motor v4) ----
    partes_prioridades = bloque_prioridades_partes(
        prioridades, tareas_manual=ficha.get('tareas', []),
        documentos=documentos, obra=obra,
        avance_pct=kpis.get('pct_ponderado'))
    if isinstance(partes_prioridades, str):
        prioridades_html = partes_prioridades
        secciones_prioridades = {}
    else:
        prioridades_html = (
            partes_prioridades['bento_command']
            + partes_prioridades['estado_obra_html']
            + partes_prioridades['avisos_prio']
            + partes_prioridades['script_indice']
            + partes_prioridades['tareas_manual_html']
            + partes_prioridades['dudas_html']
            + partes_prioridades['ejecucion_html']
            + partes_prioridades['bloqueado_html']
            + partes_prioridades['sin_revisar_html']
            + partes_prioridades['orden_html']
            + partes_prioridades['prevision_html']
            + partes_prioridades['viable_html']
            + partes_prioridades['otros_gremios_html']
            + partes_prioridades['dudas_inventario_html']
            + partes_prioridades['terminado_html']
        )
        secciones_prioridades = {
            'estado_proyecto': (
                partes_prioridades['bento_command']
                + partes_prioridades['estado_obra_html']
                + partes_prioridades['avisos_prio']),
            'que_hacer_ahora': partes_prioridades['ejecucion_html'],
            'tajos_bloqueados': partes_prioridades['bloqueado_html'],
            'tareas_manuales': partes_prioridades['tareas_manual_html'],
            'sin_revisar': partes_prioridades['sin_revisar_html'],
        }
```

Esto reemplaza exactamente el valor que antes calculaba
`bloque_prioridades(...)` — `prioridades_html` sigue usándose más abajo
(línea 1722 del fichero original, `<section id="v-prioridades" ...>`)
exactamente igual que hoy.

- [ ] **Step 2: Montar `secciones_informe` justo antes de construir `data_json`**

En `panel_obra.py`, localizar la línea (línea 1667 del fichero original):

```python
    data_json = json.dumps(payload, ensure_ascii=False).replace('</script>', '<\\/script>')
```

Y añadir justo antes:

Nota sobre "Trabajos": la pestaña en vivo incluye un gráfico Chart.js
(`chartTareas`) que se dibuja con JS a partir de `DATA.por_tarea`. Un
informe impreso no reproduce gráficos interactivos, así que la sección
"Trabajos" del selector incluye solo las dos tablas (Desviaciones de
avance, Detalle por planta/edificio) y deja fuera el gráfico — decisión de
alcance explícita, no un olvido.

```python
    # ---- INFORME DE OBRA A LA CARTA ----
    # Cada valor es la MISMA cadena HTML que ya pinta la pestana
    # correspondiente. No se recalcula ninguna cifra por un camino nuevo:
    # es la salvaguarda contra la familia de fallo de este proyecto
    # (un dato declarado que un camino distinto ignora en silencio).
    secciones_informe = {
        'trabajos': (
            "<div class='card'><h3>Desviaciones de avance</h3>"
            "<table class='data'><thead><tr><th>Tipo</th><th>Edificio</th>"
            "<th>Planta</th><th>Unidad</th><th>Avance</th><th>Motivo</th>"
            f"</tr></thead><tbody>{filas_bloq}</tbody></table></div>"
            "<div class='card'><h3>Detalle por planta / edificio</h3>"
            "<table class='data'><thead><tr><th>Edificio</th><th>Planta</th>"
            "<th>% estricto</th><th>% estimado</th><th>Nº registros</th>"
            f"</tr></thead><tbody>{filas_det}</tbody></table></div>"
        ),
        'materiales': materiales_html,
        'personal': f"<div class='card'><h3>Personal asignado</h3>{personal_html}</div>",
        'prioridades': secciones_prioridades,
        'riesgos': riesgos_html,
        'normativa': (
            "<div class='card'><h3>Normativa y criterios técnicos "
            "aplicables</h3><p style='font-size:12.5px;color:var(--muted);"
            "margin-bottom:8px;'>Lista de referencia. No sustituye la "
            "comprobación de la versión vigente ni las instrucciones de la "
            f"Dirección Facultativa.</p><ul class='norm'>{norm_html}</ul></div>"
        ),
        'documentos': f"<div class='card'><h3>Documentos de la obra</h3>{docs_html}</div>",
        'cierre': cierre_html,
    }
    secciones_json = json.dumps(secciones_informe, ensure_ascii=False).replace('</script>', '<\\/script>')
```

- [ ] **Step 3: Embeber el JSON en el HTML de salida**

En `panel_obra.py`, localizar dentro del f-string `html` (línea 1674 del
fichero original):

```python
<script src="../../_SISTEMA INFORME SAGARDE IA/static/chart.min.js"></script>
<style>{ESTILOS}</style></head><body><div class="wrap">
```

y cambiarlo por:

```python
<script src="../../_SISTEMA INFORME SAGARDE IA/static/chart.min.js"></script>
<script id="secciones-informe" type="application/json">{secciones_json}</script>
<style>{ESTILOS}</style></head><body><div class="wrap">
```

- [ ] **Step 4: Añadir el test nuevo**

Crear `tests/test_informe_obra_a_la_carta.py`:

```python
# -*- coding: utf-8 -*-
"""El informe de obra a la carta lee del mismo calculo que el panel: estas
pruebas comprueban que lo que se embebe como JSON es exactamente lo que
la pestana correspondiente ya pinta, nunca un calculo aparte."""
import json
import os
import sys
import tempfile
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import panel_obra


def _prioridades(**extra):
    base = {
        'sin_base': False, 'revision': '28/07/2026', 'version': '4.3',
        'catalogo_version': '1.3', 'resumen': {}, 'items': [],
        'inventario': [], 'dudas_pendientes': [], 'preguntas_orden': [],
        'prevision': [], 'avisos': [],
    }
    base.update(extra)
    return base


def _generar(obra='Obra de prueba', **kwargs):
    ficha = kwargs.pop('ficha', {
        '_disponible': True, 'datos': {}, 'personal': [], 'hitos': [],
        'riesgos': [], 'plan': [], 'tareas': [],
    })
    with tempfile.TemporaryDirectory() as carpeta:
        salida = os.path.join(carpeta, 'panel.html')
        panel_obra.generar_panel(
            obra=obra, subtitulo='', historial=kwargs.pop('historial', []),
            materiales=kwargs.pop('materiales', {}), ficha=ficha,
            documentos=kwargs.pop('documentos', []),
            prioridades=kwargs.pop('prioridades', _prioridades()),
            output_path=salida, **kwargs)
        with open(salida, encoding='utf-8') as f:
            return f.read()


def _extraer_secciones(html):
    inicio = html.index('<script id="secciones-informe" type="application/json">')
    inicio = html.index('>', inicio) + 1
    fin = html.index('</script>', inicio)
    return json.loads(html[inicio:fin])


class TestBotonInformeObra(unittest.TestCase):

    def test_el_boton_aparece_junto_al_ejecutivo(self):
        html = _generar()
        self.assertIn('Informe Ejecutivo PDF', html)
        self.assertIn('Informe de obra', html)
        pos_ejecutivo = html.index('Informe Ejecutivo PDF')
        pos_a_la_carta = html.index('Informe de obra')
        self.assertLess(pos_ejecutivo, pos_a_la_carta)


class TestSeccionesEmbebidas(unittest.TestCase):

    def test_el_json_tiene_las_ocho_claves_esperadas(self):
        html = _generar()
        secciones = _extraer_secciones(html)
        self.assertEqual(set(secciones.keys()), {
            'trabajos', 'materiales', 'personal', 'prioridades',
            'riesgos', 'normativa', 'documentos', 'cierre',
        })

    def test_prioridades_tiene_los_cinco_subapartados(self):
        html = _generar(prioridades=_prioridades(
            resumen={'bloqueados': 1, 'sin_revisar': 1},
            inventario=[{
                'seccion': 'BLOQUEADO', 'trabajo': 'B', 'propiedad': 'propio',
                'orden_ejecucion': 1, 'fase_nombre': 'f', 'n_ubicaciones': 1,
                'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
                'subtajos': [],
            }],
        ))
        secciones = _extraer_secciones(html)
        self.assertEqual(set(secciones['prioridades'].keys()), {
            'estado_proyecto', 'que_hacer_ahora', 'tajos_bloqueados',
            'tareas_manuales', 'sin_revisar',
        })
        self.assertIn('Tajos bloqueados', secciones['prioridades']['tajos_bloqueados'])

    def test_el_contenido_embebido_coincide_con_la_pestana_visible(self):
        """La prueba central de esta tarea: el JSON no puede decir una cosa
        mientras la pagina visible dice otra. Se compara contra la seccion
        real v-riesgos, que no pasa por ningun envoltorio nuevo."""
        html = _generar(prioridades=_prioridades(
            resumen={'bloqueados': 2},
        ))
        secciones = _extraer_secciones(html)
        seccion_riesgos_visible = html[
            html.index('<section id="v-riesgos"'):
            html.index('<section id="v-normativa"')]
        self.assertIn(secciones['riesgos'], seccion_riesgos_visible)

    def test_obra_sin_base_no_revienta_y_prioridades_sale_vacio(self):
        html = _generar(prioridades=_prioridades(
            sin_base=True, avisos=['sin base']))
        secciones = _extraer_secciones(html)
        self.assertEqual(secciones['prioridades'], {})


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 5: Ejecutar el test nuevo**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -p "test_informe_obra_a_la_carta.py" -v`
Expected: todo PASS. Si `test_el_contenido_embebido_coincide_con_la_pestana_visible`
falla, revisar que `secciones_informe['riesgos']` use la misma variable
`riesgos_html` que ya alimenta `<section id="v-riesgos">`, sin transformarla.

- [ ] **Step 6: Ejecutar la suite completa**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`
Expected: mismo número de pruebas en verde que al final de la Tarea 1, más
las nuevas de este fichero.

- [ ] **Step 7: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_obra_a_la_carta.py"
git commit -m "Embebe secciones_informe como JSON inerte en panel.html

Paso 2 del informe de obra a la carta: cada seccion/subapartado
seleccionable se serializa reutilizando la misma cadena HTML que ya
pinta su pestana — sin recalcular nada. Todavia sin boton ni menu de
seleccion visibles; es la base de datos que leera el selector."
```

---

### Task 3: Botón "Informe de obra" y menú de checkboxes (estructura, sin lógica de generación)

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py` (`ESTILOS` línea 25, cabecera y nav dentro de `generar_panel` líneas 1676-1695)
- Test: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_obra_a_la_carta.py`

**Interfaces:**
- Produce: markup con ids `btn-informe-obra` (botón), `panel-informe-obra`
  (contenedor del menú, oculto por defecto), checkboxes con
  `data-seccion="trabajos|materiales|personal|riesgos|normativa|documentos|cierre"`
  para las secciones simples y `data-seccion="prioridades"
  data-sub="estado_proyecto|que_hacer_ahora|tajos_bloqueados|tareas_manuales|sin_revisar"`
  para los 5 subapartados de Prioridades. Estos atributos son el contrato
  que usará la Tarea 4 para leer la selección.

- [ ] **Step 1: Añadir el botón junto al informe ejecutivo**

En `panel_obra.py`, dentro de `generar_panel`, cambiar (línea 1681 del
fichero original):

```python
  <a class="volver" href="{pdf_ejecutivo_nombre}" target="_blank" style="background:var(--bad);border-color:var(--bad);margin-left:6px;">📄 Informe Ejecutivo PDF</a></div>
```

por:

```python
  <a class="volver" href="{pdf_ejecutivo_nombre}" target="_blank" style="background:var(--bad);border-color:var(--bad);margin-left:6px;">📄 Informe Ejecutivo PDF</a>
  <a class="volver" id="btn-informe-obra" href="#panel-informe-obra" style="background:var(--accent);border-color:var(--accent);color:#1c2733;margin-left:6px;" onclick="abrirSelectorInforme();return true;">📋 Informe de obra</a></div>
```

- [ ] **Step 2: Añadir el contenedor del menú, oculto por defecto, tras la cabecera**

En `panel_obra.py`, dentro del f-string `html`, justo después del `</div>`
que cierra `.header` (línea 1682 del fichero original) y antes de
`<div class="nav">` (línea 1684), insertar:

```python
<div id="panel-informe-obra" class="card" style="display:none;">
  <h3>Informe de obra — elige qué secciones incluir</h3>
  <p style="font-size:12.5px;color:var(--muted);margin-bottom:10px;">
    Se genera con los datos de esta misma página (tan actualizado como la
    última vez que se regeneró el panel). Marca lo que quieras enseñar,
    dale a vista previa y desde ahí puedes imprimir o guardar como PDF.
  </p>
  <div id="informe-obra-grupos">
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="trabajos" onchange="toggleGrupoInforme(this)"> <b>✓ Trabajos</b></label>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="materiales" onchange="toggleGrupoInforme(this)"> <b>▣ Materiales</b></label>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="personal" onchange="toggleGrupoInforme(this)"> <b>👷 Personal</b></label>
    <div class="tj-group-hdr">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
        <input type="checkbox" id="cb-prioridades-all" onchange="toggleGrupoPrioridades(this)"> <b>🎯 Prioridades</b>
      </label>
    </div>
    <div class="tj-items" style="padding-left:26px;">
      <label><input type="checkbox" class="cb-prioridades" data-seccion="prioridades" data-sub="estado_proyecto"> Estado del proyecto</label>
      <label><input type="checkbox" class="cb-prioridades" data-seccion="prioridades" data-sub="que_hacer_ahora"> Qué hacer ahora</label>
      <label><input type="checkbox" class="cb-prioridades" data-seccion="prioridades" data-sub="tajos_bloqueados"> Tajos bloqueados</label>
      <label><input type="checkbox" class="cb-prioridades" data-seccion="prioridades" data-sub="tareas_manuales"> Tareas manuales</label>
      <label><input type="checkbox" class="cb-prioridades" data-seccion="prioridades" data-sub="sin_revisar"> Sin revisar nunca</label>
    </div>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="riesgos" onchange="toggleGrupoInforme(this)"> <b>⚠ Riesgos</b></label>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="normativa" onchange="toggleGrupoInforme(this)"> <b>📘 Normativa</b></label>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="documentos" onchange="toggleGrupoInforme(this)"> <b>📎 Documentos</b></label>
    <label class="tj-group-hdr"><input type="checkbox" class="grp-cb" data-seccion="cierre" onchange="toggleGrupoInforme(this)"> <b>📋 Cierre</b></label>
  </div>
  <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end;">
    <button type="button" onclick="marcarTodoInforme()" style="background:#eef0f4;border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:600;cursor:pointer;">Marcar todo</button>
    <button type="button" onclick="generarVistaPreviaInforme()" style="background:var(--accent);border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:700;cursor:pointer;">👁 Vista previa</button>
  </div>
</div>
```

Nota: `toggleGrupoInforme`, `toggleGrupoPrioridades`, `marcarTodoInforme`,
`generarVistaPreviaInforme` y `abrirSelectorInforme` se implementan en la
Tarea 4. En esta tarea basta con que el HTML/CSS exista; los botones no
tienen todavía comportamiento (las funciones no existen aún, así que un
clic en "Vista previa" dará error en consola — se resuelve en la Tarea 4,
que se ejecuta a continuación en el mismo plan, nunca se publica esta
tarea sola).

- [ ] **Step 3: Añadir el CSS del menú a `ESTILOS`**

En `panel_obra.py`, dentro de la constante `ESTILOS` (línea 25), añadir al
final del bloque (antes del cierre `"""`):

```css
.tj-group-hdr{display:flex;align-items:center;gap:8px;padding:8px 4px;border-bottom:1px solid #eef0f4;cursor:pointer;font-size:14px;}
.tj-items{display:flex;flex-direction:column;gap:6px;padding:6px 4px 10px;}
.tj-items label{font-size:13px;color:var(--text);display:flex;align-items:center;gap:7px;cursor:pointer;}
```

- [ ] **Step 4: Añadir el test de estructura**

Añadir a `tests/test_informe_obra_a_la_carta.py`:

```python
class TestMenuDeSeleccion(unittest.TestCase):

    def test_el_menu_esta_oculto_por_defecto(self):
        html = _generar()
        inicio = html.index('id="panel-informe-obra"')
        self.assertIn('display:none', html[inicio:inicio + 60])

    def test_las_ocho_secciones_simples_tienen_checkbox_con_data_seccion(self):
        html = _generar()
        for seccion in ('trabajos', 'materiales', 'personal', 'riesgos',
                        'normativa', 'documentos', 'cierre'):
            self.assertIn(f'data-seccion="{seccion}"', html)

    def test_los_cinco_subapartados_de_prioridades_tienen_data_sub(self):
        html = _generar()
        for sub in ('estado_proyecto', 'que_hacer_ahora', 'tajos_bloqueados',
                    'tareas_manuales', 'sin_revisar'):
            self.assertIn(f'data-sub="{sub}"', html)
```

- [ ] **Step 5: Ejecutar los tests y la suite completa**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`
Expected: todo PASS, incluidas las 3 pruebas nuevas de `TestMenuDeSeleccion`.

- [ ] **Step 6: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_obra_a_la_carta.py"
git commit -m "Anade boton y menu de checkboxes del informe de obra a la carta

Paso 3: estructura visual (boton junto al ejecutivo, menu oculto por
defecto con las 8 secciones y los 5 subapartados de Prioridades).
Todavia sin logica de generacion — eso es la Tarea 4, que se ejecuta a
continuacion; sin ella los botones no hacen nada util."
```

---

### Task 4: Lógica del selector — recordar selección, vista previa e impresión

**Files:**
- Modify: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py` (script final del f-string `html`, tras la línea que hoy termina en `filtrarPrio();`)
- Test: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_obra_a_la_carta.py`

**Interfaces:**
- Consume: `DATA`/`OBRA_NOMBRE` como nuevas constantes JS embebidas junto a
  `const DATA = {data_json};`; el `<script id="secciones-informe">` de la
  Tarea 2; los `data-seccion`/`data-sub` de la Tarea 3.
- Produce: funciones JS `abrirSelectorInforme()`, `toggleGrupoInforme(cb)`,
  `toggleGrupoPrioridades(cb)`, `marcarTodoInforme()`,
  `generarVistaPreviaInforme()`, más el guardado/restauración en
  `localStorage` bajo la clave `'informe_obra_sel::' + OBRA_NOMBRE`.

- [ ] **Step 1: Exponer el nombre de la obra como constante JS**

En `panel_obra.py`, dentro del f-string `html`, cambiar (línea 1742 del
fichero original):

```python
<script>
const DATA = {data_json};
```

por:

```python
<script>
const DATA = {data_json};
const OBRA_NOMBRE = {json.dumps(obra, ensure_ascii=False)};
const SECCIONES_INFORME = JSON.parse(document.getElementById('secciones-informe').textContent);
```

- [ ] **Step 2: Añadir las funciones del selector al final del mismo `<script>`**

En `panel_obra.py`, dentro del f-string `html`, justo antes de
`</script></body></html>` (línea 1784 del fichero original, que hoy es
`filtrarPrio();\n</script></body></html>`), añadir:

```python
function _claveSeleccionInforme(){{ return 'informe_obra_sel::' + OBRA_NOMBRE; }}

function _checksInforme(){{
  return [...document.querySelectorAll(
    '#informe-obra-grupos input[type=checkbox]')];
}}

function _idInforme(cb){{
  return cb.dataset.sub
    ? cb.dataset.seccion + ':' + cb.dataset.sub
    : cb.dataset.seccion;
}}

function guardarSeleccionInforme(){{
  const marcados = _checksInforme()
    .filter(cb => cb.checked && cb.dataset.seccion)
    .map(_idInforme);
  try {{ localStorage.setItem(_claveSeleccionInforme(), JSON.stringify(marcados)); }}
  catch(e) {{}}
}}

function cargarSeleccionInforme(){{
  let marcados = [];
  try {{ marcados = JSON.parse(localStorage.getItem(_claveSeleccionInforme()) || '[]'); }}
  catch(e) {{}}
  const set = new Set(marcados);
  _checksInforme().forEach(cb => {{
    if (cb.dataset.seccion) cb.checked = set.has(_idInforme(cb));
  }});
  document.querySelectorAll('.cb-prioridades').forEach(sub => {{
    // El check del grupo Prioridades refleja si TODOS sus subapartados
    // estan marcados, igual que un checkbox "seleccionar todo" normal.
  }});
  const subsPrio = [...document.querySelectorAll('.cb-prioridades')];
  document.getElementById('cb-prioridades-all').checked =
    subsPrio.length > 0 && subsPrio.every(cb => cb.checked);
}}

function abrirSelectorInforme(){{
  document.getElementById('panel-informe-obra').style.display = 'block';
  cargarSeleccionInforme();
  document.getElementById('panel-informe-obra').scrollIntoView({{behavior:'smooth'}});
}}

function toggleGrupoInforme(cb){{
  guardarSeleccionInforme();
}}

function toggleGrupoPrioridades(masterCb){{
  document.querySelectorAll('.cb-prioridades').forEach(cb => cb.checked = masterCb.checked);
  guardarSeleccionInforme();
}}

function marcarTodoInforme(){{
  _checksInforme().forEach(cb => cb.checked = true);
  guardarSeleccionInforme();
}}

document.querySelectorAll('.cb-prioridades').forEach(cb => {{
  cb.addEventListener('change', () => {{
    const subs = [...document.querySelectorAll('.cb-prioridades')];
    document.getElementById('cb-prioridades-all').checked = subs.every(c => c.checked);
    guardarSeleccionInforme();
  }});
}});

function generarVistaPreviaInforme(){{
  const marcadas = _checksInforme().filter(cb => cb.checked);
  if (!marcadas.length) {{
    alert('Marca al menos una sección antes de generar la vista previa.');
    return;
  }}
  const NOMBRES = {{
    trabajos: '✓ Trabajos', materiales: '▣ Materiales', personal: '👷 Personal',
    riesgos: '⚠ Riesgos', normativa: '📘 Normativa', documentos: '📎 Documentos',
    cierre: '📋 Cierre',
  }};
  const NOMBRES_SUB = {{
    estado_proyecto: 'Estado del proyecto', que_hacer_ahora: 'Qué hacer ahora',
    tajos_bloqueados: 'Tajos bloqueados', tareas_manuales: 'Tareas manuales',
    sin_revisar: 'Sin revisar nunca',
  }};
  let contenido = '';
  marcadas.forEach(cb => {{
    const seccion = cb.dataset.seccion;
    if (seccion === 'prioridades' && cb.dataset.sub) {{
      const html = SECCIONES_INFORME.prioridades[cb.dataset.sub] || '';
      contenido += `<section class="informe-seccion"><h2>${{NOMBRES_SUB[cb.dataset.sub]}}</h2>${{html}}</section>`;
    }} else if (SECCIONES_INFORME[seccion] !== undefined && typeof SECCIONES_INFORME[seccion] === 'string') {{
      contenido += `<section class="informe-seccion"><h2>${{NOMBRES[seccion]}}</h2>${{SECCIONES_INFORME[seccion]}}</section>`;
    }}
  }});
  const fecha = new Date().toLocaleDateString('es-ES');
  const ultimaRevision = (DATA.serie.length
    ? DATA.serie[DATA.serie.length - 1].fecha : '—');
  const documento = `<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<title>Informe de obra — ${{OBRA_NOMBRE}}</title>
<style>
  :root{{--header:#0b1f3a;--header2:#123a63;--accent:#f5a524;--ok:#2e9e5b;--warn:#e07b1a;--bad:#d9483c;--muted:#647184;--card:#fff;}}
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{font-family:'IBM Plex Sans',Arial,sans-serif;color:#1c2733;background:#fff;padding:24px;}}
  .cabecera{{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:3px solid var(--accent);padding-bottom:12px;margin-bottom:20px;}}
  .cabecera .marca{{font-size:10px;letter-spacing:.08em;color:var(--accent);font-weight:700;text-transform:uppercase;}}
  .cabecera h1{{font-size:19px;font-weight:800;color:var(--header);margin-top:3px;}}
  .cabecera .meta{{text-align:right;font-size:11px;color:var(--muted);}}
  .informe-seccion{{margin-bottom:22px;}}
  .informe-seccion h2{{font-size:15px;color:var(--header2);border-left:4px solid var(--accent);padding-left:8px;margin-bottom:10px;}}
  .card{{background:var(--card);border-radius:8px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.08);}}
  table.data{{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px;}}
  table.data th{{text-align:left;padding:5px 8px;border-bottom:2px solid #e3e7ee;color:var(--muted);font-size:10px;text-transform:uppercase;}}
  table.data td{{padding:5px 8px;border-bottom:1px solid #eef1f5;}}
  select, .filtro-oculta-impresion{{display:none !important;}}
  input[type=checkbox]{{pointer-events:none;}}
  .barra-accion{{position:sticky;top:0;background:#fff;padding:10px 0;display:flex;gap:8px;justify-content:flex-end;border-bottom:1px solid #eee;margin-bottom:16px;}}
  .barra-accion button{{border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:700;cursor:pointer;}}
  @media print{{ .barra-accion{{display:none;}} @page{{size:A4;margin:14mm;}} }}
</style></head><body>
<div class="barra-accion">
  <button onclick="window.close()" style="background:#eef0f4;">← Volver</button>
  <button onclick="window.print()" style="background:var(--header);color:#fff;">🖨️ Imprimir / Guardar como PDF</button>
</div>
<div class="cabecera">
  <div><div class="marca">Informe Sagarde IA</div><h1>Informe de obra — ${{OBRA_NOMBRE}}</h1></div>
  <div class="meta">Generado: ${{fecha}}<br>Última revisión: ${{ultimaRevision}}</div>
</div>
${{contenido}}
<script>document.querySelectorAll('details').forEach(d => d.open = true);<\/script>
</body></html>`;
  const ventana = window.open('', '_blank');
  ventana.document.write(documento);
  ventana.document.close();
  guardarSeleccionInforme();
}}
```

- [ ] **Step 3: Añadir tests de contenido del JS generado**

Añadir a `tests/test_informe_obra_a_la_carta.py` (comprobación por texto,
igual que ya hace el proyecto para el JS de `marcar-tarea-hecha`):

```python
class TestLogicaSelectorJS(unittest.TestCase):

    def test_incluye_las_funciones_clave(self):
        html = _generar()
        for funcion in ('function abrirSelectorInforme',
                        'function toggleGrupoPrioridades',
                        'function marcarTodoInforme',
                        'function generarVistaPreviaInforme',
                        'function guardarSeleccionInforme',
                        'function cargarSeleccionInforme'):
            self.assertIn(funcion, html)

    def test_la_clave_de_localstorage_incluye_el_nombre_de_la_obra(self):
        html = _generar(obra='2026 OBRA PRUEBA')
        self.assertIn("const OBRA_NOMBRE = \"2026 OBRA PRUEBA\"", html)
        self.assertIn("'informe_obra_sel::' + OBRA_NOMBRE", html)

    def test_la_vista_previa_abre_una_pestana_nueva_y_no_reescribe_la_actual(self):
        html = _generar()
        self.assertIn("window.open('', '_blank')", html)
        self.assertIn('ventana.document.write(documento)', html)

    def test_el_documento_generado_fuerza_abrir_los_details_y_ofrece_imprimir(self):
        html = _generar()
        self.assertIn("document.querySelectorAll('details').forEach(d => d.open = true)", html)
        self.assertIn('window.print()', html)

    def test_las_casillas_quedan_inertes_en_el_documento_generado(self):
        """Evita que un clic en la vista previa dispare marcar-tarea-hecha
        contra un servidor que no esta corriendo ahi."""
        html = _generar()
        self.assertIn('input[type=checkbox]{pointer-events:none;}', html)
```

- [ ] **Step 4: Ejecutar los tests nuevos y la suite completa**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests`
Expected: todo PASS.

- [ ] **Step 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_obra_a_la_carta.py"
git commit -m "Anade la logica del selector: recordar seleccion, vista previa e imprimir

Paso 4 y ultimo de la parte de codigo: el boton ya genera una pestana
nueva con las secciones marcadas, identidad visual del informe
ejecutivo, details abiertos y checkboxes inertes; imprimir/guardar usa
el propio dialogo del navegador (A4), igual que el generador de
revisiones. La seleccion se recuerda por obra en localStorage."
```

---

### Task 5: Verificación manual en navegador y regresión sobre obras reales

Esta tarea no es código: es la comprobación de que nada se ha movido en
las obras reales, siguiendo la norma del proyecto ("las obras no
implicadas no se mueven"). La ejecuta quien termine la Tarea 4, antes de
avisar a Bixente de que esto está listo para probar de verdad.

- [ ] **Step 1: Regenerar todas las obras abiertas sin publicar**

Run: `cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python generar_todos.py --no-pdf`
Expected: termina sin error, para las 5 obras abiertas (Mungia, Gernika,
Bolueta, Obispo Orueta si sigue activa, OBRA PRUEBA).

- [ ] **Step 2: Comparar KPIs antes/después**

Antes de la Tarea 1, anotar (o recuperar de la memoria del proyecto) el
`pct_ponderado` y el desglose x/m//vacío de cada obra abierta. Tras el
Step 1, volver a leer `resumen_obras.json` y confirmar que **ninguna**
obra cambió de cifra. Si alguna cambió, es un efecto colateral de esta
funcionalidad y hay que encontrar la causa antes de seguir — no se achaca
a "redondeo" sin comparar el desglose real.

- [ ] **Step 3: Abrir un panel real en el navegador y probar el flujo completo**

Abrir con doble clic el `panel.html` de OBRA PRUEBA (o cualquier obra
abierta). Comprobar a mano:

1. El botón "📋 Informe de obra" aparece junto a "📄 Informe Ejecutivo PDF".
2. Al pulsarlo se despliega el menú; marcar 2-3 secciones sueltas y 2 de
   los 5 subapartados de Prioridades.
3. "Vista previa" abre una pestaña nueva con cabecera naranja/marino,
   solo las secciones marcadas, y los `<details>` (Tajos bloqueados, Sin
   revisar nunca, Tareas manuales) ya abiertos sin tener que pinchar.
4. En esa pestaña nueva, el botón "🖨️ Imprimir / Guardar como PDF" abre
   el diálogo de impresión del navegador con vista A4.
5. Cerrar esa pestaña, volver a `panel.html`, recargar la página (F5) y
   comprobar que el menú recuerda la misma selección de antes (persistida
   en `localStorage`).
6. Repetir el mismo panel abierto por su URL publicada de GitHub Pages
   (`https://bixente-69.github.io/centro-mando-sagarde/...`) desde el
   móvil, para confirmar que funciona igual sin ningún servidor local.

- [ ] **Step 4: Reportar a Bixente**

Antes/después de KPIs de las 5 obras (Step 2), resultado de la
verificación manual (Step 3) y número final de pruebas en verde de la
suite completa. Si algo no cuadra, decirlo explícitamente — no cerrar con
cifras discordantes.
