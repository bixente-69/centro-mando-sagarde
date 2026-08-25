# Prioridades: secciones plegables — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganizar la pestaña Prioridades del panel de obra en secciones plegables con un índice arriba, para que un encargado encuentre "qué hacer hoy" sin desplazarse por un scroll interminable — sin tocar ningún dato ni cálculo.

**Architecture:** Todo el cambio vive en una función Python que genera HTML (`bloque_prioridades()` en `panel_obra.py`) y sus ayudantes privados. Se envuelve cada bloque existente en el widget nativo `<details>/<summary>` (ya usado hoy en dos sitios del mismo archivo) y se añade un índice de navegación construido a partir de las mismas variables que ya alimentan cada tabla — nunca un recuento aparte.

**Tech Stack:** Python 3 (stdlib únicamente), HTML/CSS embebidos en `ESTILOS`, un bloque `<script>` sin dependencias. Pruebas con `unittest` de la biblioteca estándar.

## Global Constraints

- Un único archivo de producción cambia: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py`. Ningún otro módulo (`priorizador_trabajos.py`, `motor_informes.py`, etc.) se toca.
- Cero dependencias nuevas: nada de librerías de acordeón ni frameworks CSS/JS. Solo HTML/CSS/JS que ya vive en el propio archivo.
- Cero persistencia entre cargas de página (nada de `localStorage` para el estado abierto/cerrado).
- Ningún dato, cifra, columna ni orden de fila dentro de cada tabla cambia. Solo cambia el envoltorio y la posición de cada bloque dentro de la página.
- Todo número que aparezca en el índice se lee de la misma variable/lista que ya alimenta la tabla de esa sección — nunca un recuento recalculado por separado. Cuando eso obligue a compartir un id de ancla entre dos sitios del código, ese id vive en una única constante de módulo, nunca repetido como cadena literal en dos lugares.
- Pruebas con `unittest` de la biblioteca estándar únicamente. No introducir `pytest` ni ninguna otra dependencia de test.
- Suite del subsistema, desde `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`:
  `python -m unittest discover -s tests`
- No ejecutar `Actualizar_Sagarde.bat` en ningún momento de este plan (hace `git add -A` + push a `main`). Las comprobaciones manuales se hacen regenerando un panel HTML suelto, sin publicar nada.

---

## Contexto de partida para quien ejecute este plan

`bloque_prioridades()` (líneas 657-838 de `panel_obra.py`, antes de empezar)
construye hoy, en este orden: fila de 8 KPI → banner "Estado de la obra" →
tarjeta "Tareas manuales" (`_tabla_tareas_manuales`) → tarjeta o banner
"Preguntas pendientes antes de decidir" (bloque inline `dudas_html`) →
tarjeta "Preguntas sobre el catálogo de tajos" (`_tabla_preguntas_orden`,
puede devolver `''`) → banners de "Avisos" → tarjeta "Qué hacer ahora:
orden lógico de ejecución" (bloque inline, con el filtro LISTO/VERIFICAR) →
tarjeta "Qué se desbloquea al terminar cada cosa" (`_tabla_prevision`,
puede devolver `''`) → cabecera "Inventario completo de la obra" → 6
tarjetas del bucle sobre `_SECCIONES_INVENTARIO` (líneas 137-151 y 781-804),
la última (`TERMINADO`) ya envuelta en un `<details>` propio.

El diseño aprobado está en
`_SISTEMA/docs/superpowers/specs/2026-08-24-prioridades-secciones-plegables-design.md`.
Léelo antes de empezar si algo de lo que sigue no encaja: ahí está el porqué
de cada decisión (agrupación en dos bloques, por qué el índice no declara
sus números por separado, etc.).

Todos los cambios de este plan son en:
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py`
y su prueba:
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py`

---

### Task 1: CSS del plegado + `_envolver_plegable()`

**Files:**
- Modify: `panel_obra.py:69` (final de la constante `ESTILOS`)
- Modify: `panel_obra.py:119` (justo después de `_ubicaciones_html`, antes de `_DUDA_ETIQUETAS`)
- Test: `tests/test_panel_prioridades.py` (nueva clase al final del archivo)

**Interfaces:**
- Produce: `_envolver_plegable(id_ancla, titulo_html, contenido_html, color_borde=None) -> str`, usada por las Tasks 3, 4 y 5.

- [ ] **Step 1: Escribir la prueba que falla**

Añadir al final de `tests/test_panel_prioridades.py`, antes de `if __name__ == '__main__':`:

```python
class TestEnvolverPlegable(unittest.TestCase):

    def test_produce_details_con_id_titulo_y_contenido(self):
        html = panel_obra._envolver_plegable(
            'sec-prueba', 'Título de prueba', '<p>contenido</p>')
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-prueba'>", html)
        self.assertIn('<summary>Título de prueba</summary>', html)
        self.assertIn(
            "<div class='seccion-contenido'><p>contenido</p></div>", html)
        self.assertTrue(html.rstrip().endswith('</details>'))

    def test_aplica_color_de_borde_cuando_se_indica(self):
        html = panel_obra._envolver_plegable(
            'sec-x', 'Título', 'contenido', color_borde='var(--warn)')
        self.assertIn("style='border-left:4px solid var(--warn);'", html)

    def test_sin_color_no_anade_atributo_style(self):
        html = panel_obra._envolver_plegable('sec-x', 'Título', 'contenido')
        self.assertNotIn('style=', html)

    def test_escapa_el_identificador_del_ancla(self):
        html = panel_obra._envolver_plegable('sec "x"', 'Título', 'contenido')
        self.assertIn('id=\'sec &quot;x&quot;\'', html)
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run (desde `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`):
`python -m unittest tests.test_panel_prioridades.TestEnvolverPlegable -v`
Expected: FAIL — `AttributeError: module 'panel_obra' has no attribute '_envolver_plegable'`

- [ ] **Step 3: Implementar `_envolver_plegable` y el CSS**

En `panel_obra.py`, justo después de `_ubicaciones_html` (línea 119, antes de
`_DUDA_ETIQUETAS = {`), insertar:

```python
def _envolver_plegable(id_ancla, titulo_html, contenido_html, color_borde=None):
    """Envuelve una seccion de Prioridades en un <details> plegable.

    Mismo widget nativo que el panel ya usa para 'Mostrar tajos terminados'
    y 'Ver ubicaciones afectadas'. Sin librerias de acordeon.
    """
    estilo = f" style='border-left:4px solid {color_borde};'" if color_borde else ''
    return (
        f"<details class='card seccion-plegable' id='{_e_atributo(id_ancla)}'{estilo}>"
        f"<summary>{titulo_html}</summary>"
        f"<div class='seccion-contenido'>{contenido_html}</div>"
        "</details>"
    )
```

En la constante `ESTILOS` (línea 24), justo antes de la línea final
`@media(max-width:768px){.header{flex-direction:column;}...}` (línea 69),
insertar este bloque de CSS nuevo:

```css
.seccion-plegable{cursor:default;}
.seccion-plegable>summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:14px;font-weight:700;padding:2px 0;}
.seccion-plegable>summary::-webkit-details-marker{display:none;}
.seccion-plegable>summary::after{content:'▸';color:var(--muted);font-size:12px;flex-shrink:0;}
.seccion-plegable[open]>summary::after{content:'▾';}
.seccion-plegable>.seccion-contenido{margin-top:12px;}
.indice-prioridades{margin-bottom:var(--gap);}
.indice-grupo-label{font-size:10.5px;font-weight:700;letter-spacing:.5px;color:var(--muted);text-transform:uppercase;margin:10px 0 6px;}
.indice-grupo{display:flex;flex-direction:column;gap:6px;margin-bottom:6px;}
.indice-item{background:var(--card);border-radius:8px;padding:10px 14px;display:flex;justify-content:space-between;align-items:center;box-shadow:0 1px 3px rgba(0,0,0,.07);text-decoration:none;color:var(--text);font-size:12.5px;font-weight:700;}
.indice-item .indice-flecha{color:var(--muted);font-weight:400;}
@media(max-width:768px){.indice-item{padding:12px 14px;}}
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `python -m unittest tests.test_panel_prioridades.TestEnvolverPlegable -v`
Expected: PASS (4 pruebas)

- [ ] **Step 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py"
git commit -m "prioridades: añade _envolver_plegable() y su CSS, base para las secciones plegables"
```

---

### Task 2: Índice de prioridades y su script de apertura

**Files:**
- Modify: `panel_obra.py` (nuevas funciones, justo después de `_envolver_plegable`)
- Test: `tests/test_panel_prioridades.py`

**Interfaces:**
- Consumes: nada de las tasks anteriores directamente (función independiente).
- Produces: `_indice_prioridades(secciones) -> str`, donde `secciones` es una
  lista de `dict` con claves `id`, `etiqueta`, `grupo` (`'actuar'` o
  `'consulta'`) y opcionalmente `color`. Usada por Task 6.

- [ ] **Step 1: Escribir la prueba que falla**

Añadir a `tests/test_panel_prioridades.py`:

```python
class TestIndicePrioridades(unittest.TestCase):

    def test_agrupa_en_actuar_y_consulta_respetando_el_orden(self):
        html = panel_obra._indice_prioridades([
            {'id': 'sec-a', 'etiqueta': 'Primero', 'grupo': 'actuar'},
            {'id': 'sec-b', 'etiqueta': 'Segundo', 'grupo': 'actuar'},
            {'id': 'sec-c', 'etiqueta': 'Tercero', 'grupo': 'consulta'},
        ])
        self.assertLess(html.index('Para actuar hoy'), html.index('Primero'))
        self.assertLess(html.index('Primero'), html.index('Segundo'))
        self.assertLess(
            html.index('Segundo'), html.index('Consulta y referencia'))
        self.assertLess(
            html.index('Consulta y referencia'), html.index('Tercero'))

    def test_enlace_apunta_al_id_de_la_seccion_y_permite_abrirla(self):
        html = panel_obra._indice_prioridades([{
            'id': 'sec-bloqueados', 'etiqueta': 'Bloqueados', 'grupo': 'actuar',
        }])
        self.assertIn("href='#sec-bloqueados'", html)
        self.assertIn("data-abre='sec-bloqueados'", html)
        self.assertIn('<script>', html)

    def test_lista_vacia_no_pinta_nada(self):
        self.assertEqual(panel_obra._indice_prioridades([]), '')
        self.assertEqual(panel_obra._indice_prioridades(None), '')

    def test_grupo_sin_secciones_no_deja_cabecera_suelta(self):
        html = panel_obra._indice_prioridades(
            [{'id': 'sec-a', 'etiqueta': 'Solo esta', 'grupo': 'actuar'}])
        self.assertNotIn('Consulta y referencia', html)
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `python -m unittest tests.test_panel_prioridades.TestIndicePrioridades -v`
Expected: FAIL — `AttributeError: module 'panel_obra' has no attribute '_indice_prioridades'`

- [ ] **Step 3: Implementar `_indice_prioridades` y su script**

Justo después de `_envolver_plegable`:

```python
_SCRIPT_INDICE_PRIORIDADES = """
<script>
document.querySelectorAll('.indice-item').forEach(function(enlace) {
  enlace.addEventListener('click', function() {
    var destino = document.getElementById(enlace.getAttribute('data-abre'));
    if (destino) { destino.open = true; }
  });
});
</script>
"""


def _indice_prioridades(secciones):
    """secciones: lista de dicts {id, etiqueta, grupo, color opcional}, en
    el orden en que deben salir dentro de su grupo. 'grupo' es 'actuar' o
    'consulta'. Un apartado que no se pasa aqui simplemente no aparece: el
    indice nunca declara algo que la pagina no vaya a pintar."""
    if not secciones:
        return ''

    def _bloque_grupo(etiqueta_grupo, codigo_grupo):
        items = [s for s in secciones if s['grupo'] == codigo_grupo]
        if not items:
            return ''
        enlaces = ''.join(
            f"<a class='indice-item' href='#{_e_atributo(s['id'])}' "
            f"data-abre='{_e_atributo(s['id'])}' "
            f"style='border-left:3px solid {s.get('color') or 'var(--muted)'};'>"
            f"<span>{_e(s['etiqueta'])}</span>"
            "<span class='indice-flecha'>▸</span></a>"
            for s in items
        )
        return (f"<div class='indice-grupo-label'>{_e(etiqueta_grupo)}</div>"
                f"<div class='indice-grupo'>{enlaces}</div>")

    return ("<div class='indice-prioridades'>"
            + _bloque_grupo('Para actuar hoy', 'actuar')
            + _bloque_grupo('Consulta y referencia', 'consulta')
            + "</div>" + _SCRIPT_INDICE_PRIORIDADES)
```

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `python -m unittest tests.test_panel_prioridades.TestIndicePrioridades -v`
Expected: PASS (4 pruebas)

- [ ] **Step 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py"
git commit -m "prioridades: añade _indice_prioridades(), aun no conectado a bloque_prioridades"
```

---

### Task 3: Tareas manuales — extraer `_tareas_pendientes()` y plegar la tarjeta

**Files:**
- Modify: `panel_obra.py:465` (constante `_SCRIPT_MARCAR_TAREA`, sin tocar su contenido, solo referencia)
- Modify: `panel_obra.py:541-654` (`_tabla_tareas_manuales`)
- Test: `tests/test_panel_prioridades.py` (clase `TestTareasManuales` ya existente)

**Interfaces:**
- Consumes: `_envolver_plegable` (Task 1).
- Produces: `_tareas_pendientes(tareas) -> list`, usada también por Task 6
  para el número del índice — así el recuento del índice y el de la propia
  tarjeta nunca pueden divergir, porque es literalmente la misma llamada.
  Constante `_ID_SEC_TAREAS = 'sec-tareas'`, usada también por Task 6.

**Nota de verificación ya hecha:** `_SCRIPT_MARCAR_TAREA` (línea 465) localiza
la tarjeta con `casilla.closest('.card')` y dentro de ella busca
`.tarea-resultado` y `.tareas-pendientes-contador` con `querySelector` — dos
búsquedas que no dependen de la etiqueta HTML (`div` vs `details`) ni de la
profundidad de anidado, solo de la clase `card` en el contenedor y de que
los elementos objetivo sean descendientes suyos. `_envolver_plegable`
conserva la clase `card` en el `<details>` y ambos elementos siguen siendo
descendientes suyos (uno dentro de `<summary>`, el otro dentro de
`.seccion-contenido`). No hace falta tocar `_SCRIPT_MARCAR_TAREA`.

- [ ] **Step 1: Escribir la prueba que falla**

Añadir a la clase `TestTareasManuales` en `tests/test_panel_prioridades.py`:

```python
    def test_tareas_pendientes_es_la_misma_lista_que_pinta_la_tarjeta(self):
        pendientes = panel_obra._tareas_pendientes(self.TAREAS)
        self.assertEqual(len(pendientes), 2)  # dos 'Pendiente' en self.TAREAS
        nombres = [t['Tarea'] for t in pendientes]
        self.assertEqual(nombres, ['Pedir material', 'Revisar cuadro'])

    def test_la_tarjeta_es_un_details_plegable(self):
        html = panel_obra._tabla_tareas_manuales(self.TAREAS, [])
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-tareas'", html)
        self.assertIn('<summary>Tareas manuales', html)
```

- [ ] **Step 2: Ejecutar y comprobar que falla**

Run: `python -m unittest tests.test_panel_prioridades.TestTareasManuales -v`
Expected: FAIL — `AttributeError: module 'panel_obra' has no attribute '_tareas_pendientes'`
(el segundo test también falla, porque la tarjeta hoy es `<div class='card'`)

- [ ] **Step 3: Refactorizar `_tabla_tareas_manuales`**

Sustituir el cuerpo de `_tabla_tareas_manuales` (líneas 541-654) por lo
siguiente. Primero, justo antes de `def _tabla_tareas_manuales(...)`, añadir:

```python
_ID_SEC_TAREAS = 'sec-tareas'


def _tarea_hecha(tarea):
    return str(tarea.get('Estado') or '').strip().casefold() == 'hecho'


def _tarea_pendiente(tarea):
    return str(tarea.get('Estado') or '').strip().casefold() == 'pendiente'


def _tarea_clave_fecha(tarea):
    texto = str(tarea.get('Fecha') or '').strip()
    try:
        return (0, datetime.strptime(texto, '%d/%m/%Y'))
    except ValueError:
        # Una fecha vacía o no normalizada no debe romper el panel. Se
        # conserva al final de las pendientes, ordenada por su texto.
        return (1, texto.casefold())


def _tareas_pendientes(tareas):
    """Las tareas no hechas, ordenadas por fecha. La usan tanto la tarjeta
    de Tareas manuales como el indice, para que el numero de una y otro
    salgan siempre del mismo calculo — nunca de dos formulas parecidas."""
    return sorted(
        (tarea for tarea in (tareas or []) if not _tarea_hecha(tarea)),
        key=_tarea_clave_fecha)
```

Después, dentro de `_tabla_tareas_manuales`, sustituir:

```python
    def esta_hecha(tarea):
        return str(tarea.get('Estado') or '').strip().casefold() == 'hecho'

    def esta_pendiente(tarea):
        return (str(tarea.get('Estado') or '').strip().casefold()
                == 'pendiente')

    def clave_fecha(tarea):
        texto = str(tarea.get('Fecha') or '').strip()
        try:
            return (0, datetime.strptime(texto, '%d/%m/%Y'))
        except ValueError:
            # Una fecha vacía o no normalizada no debe romper el panel. Se
            # conserva al final de las pendientes, ordenada por su texto.
            return (1, texto.casefold())

    pendientes = sorted(
        (tarea for tarea in tareas if not esta_hecha(tarea)), key=clave_fecha)
    hechas = [tarea for tarea in tareas if esta_hecha(tarea)]
```

por:

```python
    pendientes = _tareas_pendientes(tareas)
    hechas = [tarea for tarea in tareas if _tarea_hecha(tarea)]
```

Dentro de la función `fila(...)` anidada, sustituir la única referencia a
`esta_pendiente(tarea)` por `_tarea_pendiente(tarea)`.

Por último, sustituir el bloque final:

```python
    n_pendientes = len(pendientes)
    etiqueta = 'pendiente' if n_pendientes == 1 else 'pendientes'
    tarjeta = (
        "<div class='card' style='border-left:4px solid var(--accent2);'>"
        "<h3>Tareas manuales "
        f"<span class='badge tareas-pendientes-contador' "
        f"data-pendientes='{n_pendientes}'>{n_pendientes} {etiqueta}</span>"
        "</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Acciones declaradas en la hoja <b>Tareas</b> de "
        "<b>FICHA DE OBRA.xlsx</b>. Se muestran aparte: no modifican los "
        "KPI ni el orden calculado de los tajos.</p>"
        f"{bloque_pendientes}{bloque_hechas}"
        "<p class='tarea-resultado' role='status' "
        "style='display:none;font-size:12.5px;margin-top:10px;'></p></div>"
    )
```

por:

```python
    n_pendientes = len(pendientes)
    etiqueta = 'pendiente' if n_pendientes == 1 else 'pendientes'
    titulo = (
        "Tareas manuales "
        f"<span class='badge tareas-pendientes-contador' "
        f"data-pendientes='{n_pendientes}'>{n_pendientes} {etiqueta}</span>"
    )
    contenido = (
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Acciones declaradas en la hoja <b>Tareas</b> de "
        "<b>FICHA DE OBRA.xlsx</b>. Se muestran aparte: no modifican los "
        "KPI ni el orden calculado de los tajos.</p>"
        f"{bloque_pendientes}{bloque_hechas}"
        "<p class='tarea-resultado' role='status' "
        "style='display:none;font-size:12.5px;margin-top:10px;'></p>"
    )
    tarjeta = _envolver_plegable(
        _ID_SEC_TAREAS, titulo, contenido, color_borde='var(--accent2)')
```

(La línea final `return tarjeta + (_SCRIPT_MARCAR_TAREA if hay_casillas else '')` no cambia.)

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `python -m unittest tests.test_panel_prioridades.TestTareasManuales -v`
Expected: PASS (todas — las nuevas y las 12 que ya existían en esta clase;
revisa en concreto `test_la_casilla_se_reactiva_tras_un_cambio_con_exito` y
`test_fila_hecha_tiene_casilla_marcada_para_poder_desmarcar`, que dependen
de `_SCRIPT_MARCAR_TAREA` y de las clases `marcar-tarea-hecha`)

- [ ] **Step 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py"
git commit -m "prioridades: pliega la tarjeta de Tareas manuales y aisla _tareas_pendientes()"
```

---

### Task 4: Preguntas del catálogo, Previsión y Preguntas pendientes — plegar

**Files:**
- Modify: `panel_obra.py:154-179` (`_tabla_preguntas_orden`)
- Modify: `panel_obra.py:182-204` (`_tabla_prevision`)
- Modify: `panel_obra.py` (bloque inline `dudas_html` dentro de `bloque_prioridades`, hoy líneas 726-776)
- Test: `tests/test_panel_prioridades.py`

**Interfaces:**
- Consumes: `_envolver_plegable` (Task 1).
- Produce las constantes `_ID_SEC_PREGUNTAS_CATALOGO = 'sec-preguntas-catalogo'`,
  `_ID_SEC_PREVISION = 'sec-prevision'`, `_ID_SEC_DUDAS = 'sec-dudas'`, usadas
  por Task 6.

- [ ] **Step 1: Escribir las pruebas que fallan**

Añadir a `TestPreguntasDelCatalogo`:

```python
    def test_la_tarjeta_es_un_details_plegable(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            preguntas_orden=[{
                'codigo': 'TAJO_FUERA_DEL_CATALOGO',
                'tarea_id': 'placas_tps_cuadro', 'nombre': 'Placas tapas',
                'parecidos': ['placas_tapas'],
            }]))
        self.assertIn(
            "<details class='card seccion-plegable' "
            "id='sec-preguntas-catalogo'", html)
```

Añadir a `TestPrevision`:

```python
    def test_la_tarjeta_es_un_details_plegable(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            prevision=[{
                'tarea_id': 'pintura_segunda', 'trabajo': 'Pintura',
                'estado_actual': 'Pendiente', 'propiedad': 'externo',
                'desbloquea': 5, 'tajos_afectados': [],
            }]))
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-prevision'", html)
```

Añadir una clase nueva, después de `TestAvisos`:

```python
class TestDudasPendientes(unittest.TestCase):

    def test_con_dudas_es_un_details_con_borde_de_aviso(self):
        html = panel_obra.bloque_prioridades(_prioridades(dudas_pendientes=[{
            'codigo': 'ALCANCE', 'pregunta': '¿Qué alcance tiene?',
            'n_ubicaciones': 0, 'ubicaciones': [],
        }]))
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-dudas' "
            "style='border-left:4px solid var(--warn);'>", html)

    def test_sin_dudas_tambien_es_un_details_plegable_pero_sin_aviso(self):
        html = panel_obra.bloque_prioridades(_prioridades(dudas_pendientes=[]))
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-dudas'>", html)
        self.assertIn('No hay preguntas pendientes en esta actualización', html)
```

- [ ] **Step 2: Ejecutar y comprobar que fallan**

Run: `python -m unittest tests.test_panel_prioridades.TestPreguntasDelCatalogo tests.test_panel_prioridades.TestPrevision tests.test_panel_prioridades.TestDudasPendientes -v`
Expected: FAIL en las 3 pruebas nuevas (el HTML actual usa `<div class='card'`, no `<details>`)

- [ ] **Step 3: Envolver las tres secciones**

En `_tabla_preguntas_orden`, justo antes de `def _tabla_preguntas_orden`,
añadir `_ID_SEC_PREGUNTAS_CATALOGO = 'sec-preguntas-catalogo'`. Sustituir el
`return` final:

```python
    return ("<div class='card' style='border-left:4px solid var(--warn);'>"
            "<h3>Preguntas sobre el catálogo de tajos</h3>"
            "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
            "El catálogo manda sobre el orden y las dependencias, y es "
            "siempre ampliable. Estas son las decisiones que faltan para que "
            "estos tajos ocupen su sitio en la secuencia.</p>"
            "<div class='table-scroll'><table class='data'><thead><tr>"
            "<th>Qué pasa</th><th>Tajo</th></tr></thead><tbody>"
            + filas + "</tbody></table></div></div>")
```

por:

```python
    contenido = (
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "El catálogo manda sobre el orden y las dependencias, y es "
        "siempre ampliable. Estas son las decisiones que faltan para que "
        "estos tajos ocupen su sitio en la secuencia.</p>"
        "<div class='table-scroll'><table class='data'><thead><tr>"
        "<th>Qué pasa</th><th>Tajo</th></tr></thead><tbody>"
        + filas + "</tbody></table></div>")
    return _envolver_plegable(
        _ID_SEC_PREGUNTAS_CATALOGO, 'Preguntas sobre el catálogo de tajos',
        contenido, color_borde='var(--warn)')
```

En `_tabla_prevision`, justo antes de `def _tabla_prevision`, añadir
`_ID_SEC_PREVISION = 'sec-prevision'`. Sustituir el `return` final:

```python
    return ("<div class='card'><h3>Qué se desbloquea al terminar cada cosa</h3>"
            "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
            "Ordenado por lo que más libera. Una obra dura meses: saber qué "
            "abre paso a qué es lo que permite llevar el orden hasta el "
            "final.</p>"
            "<div class='table-scroll'><table class='data'><thead><tr>"
            "<th>Al terminar</th><th>Ahora está</th><th style='text-align:right;'>"
            "Libera</th><th>Deja pasar a</th>"
            "</tr></thead><tbody>" + filas + "</tbody></table></div></div>")
```

por:

```python
    contenido = (
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Ordenado por lo que más libera. Una obra dura meses: saber qué "
        "abre paso a qué es lo que permite llevar el orden hasta el "
        "final.</p>"
        "<div class='table-scroll'><table class='data'><thead><tr>"
        "<th>Al terminar</th><th>Ahora está</th><th style='text-align:right;'>"
        "Libera</th><th>Deja pasar a</th>"
        "</tr></thead><tbody>" + filas + "</tbody></table></div>")
    return _envolver_plegable(
        _ID_SEC_PREVISION, 'Qué se desbloquea al terminar cada cosa', contenido)
```

Añadir `_ID_SEC_DUDAS = 'sec-dudas'` como constante de módulo, junto a
`_ID_SEC_PREGUNTAS_CATALOGO` y `_ID_SEC_PREVISION` (fuera de cualquier
función). Dentro de `bloque_prioridades`, sustituir el bloque:

```python
    if dudas_prio:
        filas_dudas = ''
        for duda in dudas_prio:
            ...(sin cambios en este bucle)...
        dudas_html = ("<div class='card' style='border-left:4px solid var(--warn);'>"
                      "<h3>Preguntas pendientes antes de decidir</h3>"
                      "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
                      "Resolver estas dudas antes de planificar los tajos afectados. "
                      "Pincha en cada fila para ver las plantas y unidades concretas.</p>"
                      "<div class='table-scroll'><table class='data'><thead><tr>"
                      "<th>Tipo</th><th>Qué hay que comprobar</th><th>Uds.</th>"
                      "</tr></thead><tbody>"
                      + filas_dudas + "</tbody></table></div></div>")
    else:
        dudas_html = '<div class="banner">✓ No hay preguntas pendientes en esta actualización.</div>'
```

por:

```python
    if dudas_prio:
        filas_dudas = ''
        for duda in dudas_prio:
            ...(sin cambios en este bucle)...
        contenido_dudas = (
            "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
            "Resolver estas dudas antes de planificar los tajos afectados. "
            "Pincha en cada fila para ver las plantas y unidades concretas.</p>"
            "<div class='table-scroll'><table class='data'><thead><tr>"
            "<th>Tipo</th><th>Qué hay que comprobar</th><th>Uds.</th>"
            "</tr></thead><tbody>"
            + filas_dudas + "</tbody></table></div>")
        dudas_html = _envolver_plegable(
            _ID_SEC_DUDAS, 'Preguntas pendientes antes de decidir',
            contenido_dudas, color_borde='var(--warn)')
    else:
        contenido_dudas = (
            '<p style="color:var(--ok);font-size:13px;">✓ No hay preguntas '
            'pendientes en esta actualización.</p>')
        dudas_html = _envolver_plegable(
            _ID_SEC_DUDAS, 'Preguntas pendientes antes de decidir', contenido_dudas)
```

**Importante:** el bucle que construye `filas_dudas` (todo lo que hay entre
`for duda in dudas_prio:` y el cierre del bucle) no cambia ni una línea —
solo cambia lo que envuelve al resultado.

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `python -m unittest tests.test_panel_prioridades -v`
Expected: PASS en todo el archivo (incluye las clases tocadas y las que no)

- [ ] **Step 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py"
git commit -m "prioridades: pliega Preguntas del catálogo, Previsión y Preguntas pendientes"
```

---

### Task 5: Las 6 secciones del inventario — plegar y desnumerar

**Files:**
- Modify: `panel_obra.py:137-151` (`_SECCIONES_INVENTARIO`)
- Modify: `panel_obra.py:781-804` (bucle de inventario, dentro de `bloque_prioridades`)
- Test: `tests/test_panel_prioridades.py` (`TestSinRevisar`)

**Interfaces:**
- Consumes: `_envolver_plegable` (Task 1).
- Produce: diccionario local `inventario_por_codigo` (dentro de
  `bloque_prioridades`, no exportado), con una entrada por código de
  `_SECCIONES_INVENTARIO` y forma `{'id': str, 'html': str, 'n': int}`.
  Task 6 lo consume para construir el índice y el ensamblado final.

- [ ] **Step 1: Escribir la prueba que falla**

`_SECCIONES_INVENTARIO` pierde sus prefijos numéricos ("1. ", "2. "…), así
que hay que actualizar la única prueba que depende de ellos. En
`TestSinRevisar`, sustituir:

```python
        self.assertIn('5. Sin revisar nunca', html)
```

por:

```python
        self.assertIn('Sin revisar nunca', html)
```

Y añadir una prueba nueva a la misma clase:

```python
    def test_la_seccion_es_un_details_plegable_sin_numero(self):
        html = panel_obra.bloque_prioridades(_prioridades(inventario=[{
            'seccion': 'SIN_REVISAR', 'trabajo': 'Tubeado interior',
            'propiedad': 'propio', 'orden_ejecucion': 130,
            'fase_nombre': 'Instalación interior', 'n_ubicaciones': 5,
            'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
            'subtajos': [],
        }]))
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-inv-sin_revisar'",
            html)
        self.assertNotIn('5. Sin revisar nunca', html)
```

- [ ] **Step 2: Ejecutar y comprobar que fallan**

Run: `python -m unittest tests.test_panel_prioridades.TestSinRevisar -v`
Expected: FAIL — el HTML actual sigue diciendo "5. Sin revisar nunca" y usa
`<div class='card'`, no `<details id='sec-inv-sin_revisar'`.

- [ ] **Step 3: Quitar los números y plegar cada sección del inventario**

Sustituir `_SECCIONES_INVENTARIO` (líneas 137-151) por:

```python
_SECCIONES_INVENTARIO = [
    ('VIABLE', 'Tajos viables',
     'Se pueden ejecutar según los datos disponibles.'),
    ('BLOQUEADO', 'Tajos bloqueados',
     'Son propios, pero falta una dependencia previa.'),
    ('OTROS_GREMIOS', 'Otros gremios e interferencias',
     'Se controlan solo para saber cuándo puede entrar electricidad.'),
    ('DUDAS', 'Sin clasificar o por verificar',
     'No se decide ni se fusiona hasta recibir confirmación.'),
    ('SIN_REVISAR', 'Sin revisar nunca',
     'Nadie los ha mirado todavía. No son trabajo pendiente: son trabajo '
     'por comprobar.'),
    ('TERMINADO', 'Tajos terminados',
     'Histórico conservado; siempre se muestra al final.'),
]
```

Dentro de `bloque_prioridades`, sustituir el bucle completo (líneas 781-804):

```python
    inventario_html = ''
    for codigo, titulo, explicacion in _SECCIONES_INVENTARIO:
        grupos = [g for g in inventario_prio if g.get('seccion') == codigo]
        filas = ''
        for g in grupos:
            subtajos = g.get('subtajos', [])
            sub_txt = ''
            if len(subtajos) > 1:
                sub_txt = f"<div style='font-size:11px;color:var(--muted);'>Incluye: {e(', '.join(subtajos))}</div>"
            filas += (f"<tr><td><b>{e(g.get('trabajo'))}</b>{sub_txt}"
                      f"<div style='font-size:11px;color:var(--muted);'>Orden {e(g.get('orden_ejecucion'))} · {e(g.get('fase_nombre'))}</div></td>"
                      f"<td>{e(g.get('propiedad'))}</td><td><b>{e(g.get('n_ubicaciones'))}</b></td>"
                      f"<td>{_ubicaciones_html(g.get('ubicaciones', []))}</td>"
                      f"<td>{e(g.get('estado_actual'))}</td><td style='font-size:12px;'>{e(g.get('motivo'))}</td></tr>")
        if not filas:
            filas = '<tr><td colspan="6" class="empty">Sin tajos en esta sección.</td></tr>'
        tabla = (f"<div class='card'><h3>{titulo} <span class='badge'>{len(grupos)}</span></h3>"
                 f"<p style='font-size:12px;color:var(--muted);margin-bottom:8px;'>{explicacion}</p>"
                 "<div class='table-scroll'><table class='data'><thead><tr><th>Tajo agrupado</th>"
                 "<th>Responsable</th><th>Ubicaciones</th><th>Dónde</th><th>Estado</th><th>Motivo</th>"
                 f"</tr></thead><tbody>{filas}</tbody></table></div></div>")
        if codigo == 'TERMINADO':
            tabla = f"<details><summary style='cursor:pointer;font-weight:700;margin:14px 0;'>Mostrar {len(grupos)} tajos terminados</summary>{tabla}</details>"
        inventario_html += tabla
```

por:

```python
    inventario_por_codigo = {}
    for codigo, titulo, explicacion in _SECCIONES_INVENTARIO:
        grupos = [g for g in inventario_prio if g.get('seccion') == codigo]
        filas = ''
        for g in grupos:
            subtajos = g.get('subtajos', [])
            sub_txt = ''
            if len(subtajos) > 1:
                sub_txt = f"<div style='font-size:11px;color:var(--muted);'>Incluye: {e(', '.join(subtajos))}</div>"
            filas += (f"<tr><td><b>{e(g.get('trabajo'))}</b>{sub_txt}"
                      f"<div style='font-size:11px;color:var(--muted);'>Orden {e(g.get('orden_ejecucion'))} · {e(g.get('fase_nombre'))}</div></td>"
                      f"<td>{e(g.get('propiedad'))}</td><td><b>{e(g.get('n_ubicaciones'))}</b></td>"
                      f"<td>{_ubicaciones_html(g.get('ubicaciones', []))}</td>"
                      f"<td>{e(g.get('estado_actual'))}</td><td style='font-size:12px;'>{e(g.get('motivo'))}</td></tr>")
        if not filas:
            filas = '<tr><td colspan="6" class="empty">Sin tajos en esta sección.</td></tr>'
        titulo_seccion = f"{titulo} <span class='badge'>{len(grupos)}</span>"
        contenido = (
            f"<p style='font-size:12px;color:var(--muted);margin-bottom:8px;'>{explicacion}</p>"
            "<div class='table-scroll'><table class='data'><thead><tr><th>Tajo agrupado</th>"
            "<th>Responsable</th><th>Ubicaciones</th><th>Dónde</th><th>Estado</th><th>Motivo</th>"
            f"</tr></thead><tbody>{filas}</tbody></table></div>")
        id_ancla = f'sec-inv-{codigo.lower()}'
        inventario_por_codigo[codigo] = {
            'id': id_ancla,
            'html': _envolver_plegable(id_ancla, titulo_seccion, contenido),
            'n': len(grupos),
        }
```

(La rama especial `if codigo == 'TERMINADO':` desaparece: ya no hace falta
un `<details>` anidado dentro de otro — el propio `_envolver_plegable` deja
"Tajos terminados" plegado por defecto igual que las demás secciones.)

El `return f"""..."""` final aún no se toca en esta task — sigue usando
`{inventario_html}`, así que en este punto el módulo no compila si se deja
tal cual (esa variable ya no se construye igual que antes). Por eso, al
final de esta task, añadir temporalmente antes del `return`:

```python
    inventario_html = ''.join(v['html'] for v in inventario_por_codigo.values())
```

Esta línea es solo un puente para dejar la task 5 en un estado que compila
y pasa las pruebas tal y como estaban antes de empezar (mismo contenido,
mismo orden de las 6 secciones, solo que ahora cada una es un `<details>`).
La Task 6 la sustituye por el ensamblado final en dos grupos. La tarjeta
"Qué hacer ahora" se deja sin tocar en esta task — se pliega directamente en
la Task 6, en el mismo paso en que queda conectada, para no dejar código
construido y sin usar (y por tanto sin ninguna prueba que lo cubra) entre
una task y la siguiente.

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `python -m unittest tests.test_panel_prioridades -v`
Expected: PASS en todo el archivo

- [ ] **Step 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py"
git commit -m "prioridades: pliega Qué hacer ahora y las 6 secciones del inventario, sin numerarlas"
```

---

### Task 6: Ensamblado final — pliega "Qué hacer ahora", conecta el índice y arma los dos grupos

**Files:**
- Modify: `panel_obra.py` (constantes de módulo + tramo final de `bloque_prioridades`)
- Test: `tests/test_panel_prioridades.py` (clase nueva `TestIndiceConectado`,
  más revisión de `TestTareasManuales.test_tarjeta_esta_entre_estado_de_obra_y_dudas`)

**Interfaces:**
- Consumes: todo lo de las Tasks 1-5.
- Produce la constante `_ID_SEC_EJECUCION = 'sec-ejecucion'`.
- No produce nada más hacia fuera: es el punto de unión.

- [ ] **Step 1: Escribir las pruebas que fallan**

Añadir al final de `tests/test_panel_prioridades.py`, antes de
`if __name__ == '__main__':`:

```python
class TestIndiceConectado(unittest.TestCase):

    def _html_obra_completa(self):
        return panel_obra.bloque_prioridades(_prioridades(
            resumen={'listos': 2, 'bloqueados': 1, 'sin_revisar': 1},
            items=[
                {'orden': 1, 'situacion': 'LISTO', 'trabajo': 'A',
                 'n_unidades': 1, 'n_celdas': 1, 'n_ubicaciones': 1,
                 'ubicaciones': [], 'estado_actual': 'Pendiente',
                 'motivo': 'x', 'fase_nombre': 'f', 'orden_ejecucion': 1,
                 'ambito_nombre': 'Viviendas'},
            ],
            inventario=[
                {'seccion': 'BLOQUEADO', 'trabajo': 'B', 'propiedad': 'propio',
                 'orden_ejecucion': 2, 'fase_nombre': 'f', 'n_ubicaciones': 3,
                 'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
                 'subtajos': []},
                {'seccion': 'SIN_REVISAR', 'trabajo': 'C', 'propiedad': 'propio',
                 'orden_ejecucion': 3, 'fase_nombre': 'f', 'n_ubicaciones': 4,
                 'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
                 'subtajos': []},
            ],
        ), tareas_manual=[{
            'Tarea': 'Revisar cuadro', 'Origen': 'Parte de obra',
            'Fecha': '22/08/2026', 'Archivo': '', 'Estado': 'Pendiente',
        }], documentos=[])

    def test_el_indice_aparece_una_sola_vez(self):
        html = self._html_obra_completa()
        self.assertEqual(html.count("class='indice-prioridades'"), 1)

    def test_el_indice_va_antes_que_todas_las_secciones_plegables(self):
        html = self._html_obra_completa()
        posicion_indice = html.index("class='indice-prioridades'")
        for id_seccion in ('sec-tareas', 'sec-dudas', 'sec-ejecucion',
                            'sec-inv-bloqueado', 'sec-inv-sin_revisar'):
            self.assertLess(
                posicion_indice, html.index(f"id='{id_seccion}'"),
                f"el indice deberia ir antes que {id_seccion}")

    def test_bloqueados_y_sin_revisar_estan_en_el_grupo_actuar(self):
        html = self._html_obra_completa()
        inicio_actuar = html.index('Para actuar hoy')
        inicio_consulta = html.index('Consulta y referencia')
        pos_bloqueados = html.index("data-abre='sec-inv-bloqueado'")
        pos_sin_revisar = html.index("data-abre='sec-inv-sin_revisar'")
        self.assertTrue(inicio_actuar < pos_bloqueados < inicio_consulta)
        self.assertTrue(inicio_actuar < pos_sin_revisar < inicio_consulta)

    def test_el_numero_del_indice_coincide_con_las_filas_reales_de_la_seccion(self):
        html = self._html_obra_completa()
        # "Tajos bloqueados" tiene 1 grupo en el inventario de esta obra de
        # prueba (seccion BLOQUEADO): el indice debe decir "1", no otra cosa.
        indice_bloqueados = html[
            html.index("data-abre='sec-inv-bloqueado'"):
            html.index("data-abre='sec-inv-bloqueado'") + 200]
        self.assertIn('1', indice_bloqueados)
        # Y la propia seccion debe traer el mismo "1" en su badge.
        seccion_bloqueados = html[
            html.index("id='sec-inv-bloqueado'"):
            html.index("id='sec-inv-bloqueado'") + 400]
        self.assertIn("<span class='badge'>1</span>", seccion_bloqueados)

    def test_una_seccion_vacia_no_aparece_en_el_indice(self):
        # Sin preguntas_orden ni prevision: _tabla_preguntas_orden y
        # _tabla_prevision devuelven '' y no deben dejar entrada en el indice.
        html = self._html_obra_completa()
        self.assertNotIn('sec-preguntas-catalogo', html)
        self.assertNotIn('sec-prevision', html)

    def test_tareas_manuales_vacio_no_deja_entrada_en_el_indice(self):
        html = panel_obra.bloque_prioridades(
            _prioridades(), tareas_manual=[], documentos=[])
        self.assertNotIn('sec-tareas', html)
```

- [ ] **Step 2: Ejecutar y comprobar que fallan**

Run: `python -m unittest tests.test_panel_prioridades.TestIndiceConectado -v`
Expected: FAIL en todas — el índice aún no existe en la salida de
`bloque_prioridades` (la Task 5 dejó un puente que ignora
`_indice_prioridades` y no agrupa nada).

- [ ] **Step 3: Plegar "Qué hacer ahora", conectar el índice y reordenar en dos grupos**

Añadir `_ID_SEC_EJECUCION = 'sec-ejecucion'` junto a las demás constantes
`_ID_SEC_*` declaradas como constantes de módulo (fuera de cualquier
función), por ejemplo justo antes de `def bloque_prioridades` — deja una
única declaración de cada constante, todas juntas.

Dentro de `bloque_prioridades`, justo antes del puente que dejó la Task 5
(`inventario_html = ''.join(...)`), añadir el plegado de "Qué hacer ahora":

```python
    titulo_ejecucion = (
        "Qué hacer ahora: orden lógico de ejecución "
        f"<span class='badge'>{resumen_prio.get('listos', 0)}</span>")
    contenido_ejecucion = f"""<p style="font-size:12.5px;color:var(--muted);margin-bottom:10px;">Primero aparecen los tajos viables de viviendas, después zonas comunes y edificio. Los tajos iguales se agrupan. VERIFICAR nunca se considera ejecutable hasta confirmar la duda. <a href="prioridades_trabajos.json" target="_blank">Ver cálculo y detalle completo</a>.</p>
      <div style="margin-bottom:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <span style="font-size:12px;color:var(--muted);">Filtrar:</span>
        <select id="filtro-sit" style="font-size:12px;padding:4px 8px;border:1px solid #ddd;border-radius:6px;">
          <option value="">LISTO + VERIFICAR</option>
          <option value="LISTO">Solo LISTO</option>
          <option value="VERIFICAR">Solo VERIFICAR</option>
        </select>
        <span id="prio-count" style="font-size:12px;color:var(--muted);"></span>
      </div>
      <div class="table-scroll"><table id="tabla-prio" class="data"><thead><tr><th>#</th><th>Tajo</th><th>Alcance</th><th>Dónde</th><th>En obra</th><th>Motivo / Comprobar</th></tr></thead>
      <tbody>{filas_prio}</tbody></table></div>"""
    ejecucion_html = _envolver_plegable(
        _ID_SEC_EJECUCION, titulo_ejecucion, contenido_ejecucion,
        color_borde='var(--ok)')
```

Ahora sí, sustituir el puente que dejó la Task 5:

```python
    inventario_html = ''.join(v['html'] for v in inventario_por_codigo.values())
```

y el `return f"""..."""` final completo:

```python
    return f"""
    <div class="kpi-row">
      <div class="kpi"><div class="label">Bloques viables</div><div class="value">{resumen_prio.get('listos', 0)}</div><div class="hint">{resumen_prio.get('unidades_listas', 0)} unidades de trabajo</div></div>
      <div class="kpi"><div class="label">Bloqueados</div><div class="value">{resumen_prio.get('bloqueados', 0)}</div><div class="hint">Tajos propios con dependencias</div></div>
      <div class="kpi"><div class="label">Otros gremios</div><div class="value">{resumen_prio.get('otros_gremios', 0)}</div><div class="hint">Control de interferencias</div></div>
      <div class="kpi"><div class="label">Sin revisar nunca</div><div class="value">{resumen_prio.get('sin_revisar', 0)}</div><div class="hint">{resumen_prio.get('unidades_sin_revisar', 0)} celdas que nadie ha mirado</div></div>
      <div class="kpi"><div class="label">Preguntas</div><div class="value">{resumen_prio.get('preguntas_pendientes', 0)}</div><div class="hint">Resolver antes de decidir</div></div>
      <div class="kpi"><div class="label">Terminados</div><div class="value">{resumen_prio.get('terminados', 0)}</div><div class="hint">Conservados del histórico</div></div>
      <div class="kpi"><div class="label">Inventario completo</div><div class="value">{resumen_prio.get('inventario_total', 0)}</div><div class="hint">Tipos de tajo agrupados</div></div>
      <div class="kpi"><div class="label">Revisión utilizada</div><div class="value" style="font-size:18px;">{e(prioridades.get('revision'))}</div><div class="hint">Motor v{e(prioridades.get('version'))} · catálogo v{e(prioridades.get('catalogo_version'))}</div></div>
    </div>
    {estado_obra_html}
    {tareas_manual_html}
    {dudas_html}
    {orden_html}
    {avisos_prio}
    <div class="card"><h3>Qué hacer ahora: orden lógico de ejecución</h3>
      <p style="font-size:12.5px;color:var(--muted);margin-bottom:10px;">Primero aparecen los tajos viables de viviendas, después zonas comunes y edificio. Los tajos iguales se agrupan. VERIFICAR nunca se considera ejecutable hasta confirmar la duda. <a href="prioridades_trabajos.json" target="_blank">Ver cálculo y detalle completo</a>.</p>
      <div style="margin-bottom:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <span style="font-size:12px;color:var(--muted);">Filtrar:</span>
        <select id="filtro-sit" style="font-size:12px;padding:4px 8px;border:1px solid #ddd;border-radius:6px;">
          <option value="">LISTO + VERIFICAR</option>
          <option value="LISTO">Solo LISTO</option>
          <option value="VERIFICAR">Solo VERIFICAR</option>
        </select>
        <span id="prio-count" style="font-size:12px;color:var(--muted);"></span>
      </div>
      <div class="table-scroll"><table id="tabla-prio" class="data"><thead><tr><th>#</th><th>Tajo</th><th>Alcance</th><th>Dónde</th><th>En obra</th><th>Motivo / Comprobar</th></tr></thead>
      <tbody>{filas_prio}</tbody></table></div>
    </div>
    {prevision_html}
    <div style="margin:20px 0 10px;"><h2 style="font-size:18px;">Inventario completo de la obra</h2><p style="font-size:12.5px;color:var(--muted);">Incluye todos los tajos de la base de la obra. Los terminados no desaparecen: se guardan al final.</p></div>
    {inventario_html}"""
```

(Este bloque no lo tocó ninguna task anterior — sigue siendo literalmente el
original. Solo `{inventario_html}` cambió de significado, por el puente que
dejó la Task 5.)

por:

```python
    secciones_indice = []
    if tareas_manual_html:
        secciones_indice.append({
            'id': _ID_SEC_TAREAS,
            'etiqueta': (f"Tareas manuales — "
                        f"{len(_tareas_pendientes(tareas_manual))} pendientes"),
            'grupo': 'actuar', 'color': 'var(--accent2)',
        })
    secciones_indice.append({
        'id': _ID_SEC_DUDAS,
        'etiqueta': f"Preguntas pendientes antes de decidir — {len(dudas_prio)}",
        'grupo': 'actuar',
        'color': 'var(--warn)' if dudas_prio else 'var(--ok)',
    })
    secciones_indice.append({
        'id': _ID_SEC_EJECUCION,
        'etiqueta': f"Qué hacer ahora — {resumen_prio.get('listos', 0)} tajos listos",
        'grupo': 'actuar', 'color': 'var(--ok)',
    })
    secciones_indice.append({
        'id': inventario_por_codigo['BLOQUEADO']['id'],
        'etiqueta': f"Tajos bloqueados — {inventario_por_codigo['BLOQUEADO']['n']}",
        'grupo': 'actuar', 'color': 'var(--warn)',
    })
    secciones_indice.append({
        'id': inventario_por_codigo['SIN_REVISAR']['id'],
        'etiqueta': f"Sin revisar nunca — {inventario_por_codigo['SIN_REVISAR']['n']}",
        'grupo': 'actuar', 'color': 'var(--bad)',
    })
    if orden_html:
        secciones_indice.append({
            'id': _ID_SEC_PREGUNTAS_CATALOGO,
            'etiqueta': (f"Preguntas sobre el catálogo — "
                        f"{len(prioridades.get('preguntas_orden') or [])}"),
            'grupo': 'consulta', 'color': 'var(--warn)',
        })
    if prevision_html:
        secciones_indice.append({
            'id': _ID_SEC_PREVISION,
            'etiqueta': 'Qué se desbloquea al terminar cada cosa',
            'grupo': 'consulta',
        })
    secciones_indice.append({
        'id': inventario_por_codigo['VIABLE']['id'],
        'etiqueta': f"Tajos viables (inventario) — {inventario_por_codigo['VIABLE']['n']}",
        'grupo': 'consulta',
    })
    secciones_indice.append({
        'id': inventario_por_codigo['OTROS_GREMIOS']['id'],
        'etiqueta': (f"Otros gremios e interferencias — "
                    f"{inventario_por_codigo['OTROS_GREMIOS']['n']}"),
        'grupo': 'consulta',
    })
    secciones_indice.append({
        'id': inventario_por_codigo['DUDAS']['id'],
        'etiqueta': f"Sin clasificar o por verificar — {inventario_por_codigo['DUDAS']['n']}",
        'grupo': 'consulta',
    })
    secciones_indice.append({
        'id': inventario_por_codigo['TERMINADO']['id'],
        'etiqueta': f"Tajos terminados — {inventario_por_codigo['TERMINADO']['n']}",
        'grupo': 'consulta',
    })
    indice_html = _indice_prioridades(secciones_indice)

    grupo_actuar_html = (
        tareas_manual_html + dudas_html + ejecucion_html
        + inventario_por_codigo['BLOQUEADO']['html']
        + inventario_por_codigo['SIN_REVISAR']['html']
    )
    grupo_consulta_html = (
        orden_html + prevision_html
        + inventario_por_codigo['VIABLE']['html']
        + inventario_por_codigo['OTROS_GREMIOS']['html']
        + inventario_por_codigo['DUDAS']['html']
        + inventario_por_codigo['TERMINADO']['html']
    )

    return f"""
    <div class="kpi-row">
      <div class="kpi"><div class="label">Bloques viables</div><div class="value">{resumen_prio.get('listos', 0)}</div><div class="hint">{resumen_prio.get('unidades_listas', 0)} unidades de trabajo</div></div>
      <div class="kpi"><div class="label">Bloqueados</div><div class="value">{resumen_prio.get('bloqueados', 0)}</div><div class="hint">Tajos propios con dependencias</div></div>
      <div class="kpi"><div class="label">Otros gremios</div><div class="value">{resumen_prio.get('otros_gremios', 0)}</div><div class="hint">Control de interferencias</div></div>
      <div class="kpi"><div class="label">Sin revisar nunca</div><div class="value">{resumen_prio.get('sin_revisar', 0)}</div><div class="hint">{resumen_prio.get('unidades_sin_revisar', 0)} celdas que nadie ha mirado</div></div>
      <div class="kpi"><div class="label">Preguntas</div><div class="value">{resumen_prio.get('preguntas_pendientes', 0)}</div><div class="hint">Resolver antes de decidir</div></div>
      <div class="kpi"><div class="label">Terminados</div><div class="value">{resumen_prio.get('terminados', 0)}</div><div class="hint">Conservados del histórico</div></div>
      <div class="kpi"><div class="label">Inventario completo</div><div class="value">{resumen_prio.get('inventario_total', 0)}</div><div class="hint">Tipos de tajo agrupados</div></div>
      <div class="kpi"><div class="label">Revisión utilizada</div><div class="value" style="font-size:18px;">{e(prioridades.get('revision'))}</div><div class="hint">Motor v{e(prioridades.get('version'))} · catálogo v{e(prioridades.get('catalogo_version'))}</div></div>
    </div>
    {estado_obra_html}
    {avisos_prio}
    {indice_html}
    {grupo_actuar_html}
    {grupo_consulta_html}"""
```

**Ojo con `filas_prio`:** en el paso anterior (Task 5) `ejecucion_html` ya se
construyó usando `filas_prio` y `resumen_prio.get('listos', 0)`. Aquí no se
vuelve a tocar esa construcción, solo se usa el resultado ya calculado.

- [ ] **Step 4: Ejecutar y comprobar que pasa**

Run: `python -m unittest tests.test_panel_prioridades -v`
Expected: PASS en las 40+ pruebas del archivo, incluida
`test_tarjeta_esta_entre_estado_de_obra_y_dudas` (revísala en concreto: con
el nuevo orden, "Estado de la obra" sigue siendo lo primero que aparece, y
dentro del índice "Tareas manuales" sale antes que "Preguntas pendientes
antes de decidir" porque así están en `secciones_indice`, así que el orden
relativo se mantiene sin tocar esa prueba).

Ejecutar también la suite completa del subsistema para descartar efectos
colaterales en otras pestañas del panel:

Run: `python -m unittest discover -s tests` (desde
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`)
Expected: mismo recuento de pruebas en verde que antes de empezar este plan,
más las nuevas de este plan (4 saltadas de siempre por Orueta cerrada, sin
cambios ahí).

- [ ] **Step 5: Comprobación manual — regenerar un panel real y mirarlo**

Esto NO usa `Actualizar_Sagarde.bat` (evita publicar nada). Desde
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`:

```bash
python regenerar_obra.py "2026 OBRA PRUEBA"
```

Abrir el `panel.html` generado de OBRA PRUEBA en un navegador, ir a la
pestaña Prioridades y comprobar a ojo:
- el índice aparece justo debajo de los 8 KPI, en dos grupos;
- todas las secciones empiezan plegadas;
- pinchar una fila del índice baja hasta la sección **y la abre**;
- dentro de cada sección abierta, el contenido es el mismo de siempre
  (mismas columnas, mismos datos);
- el filtro LISTO/VERIFICAR de "Qué hacer ahora" sigue funcionando al
  abrir esa sección;
- marcar/desmarcar una tarea manual (si OBRA PRUEBA tiene alguna en su
  `FICHA DE OBRA.xlsx`) sigue actualizando el contador sin recargar.

Si algo no cuadra, no se sigue: se vuelve a la task correspondiente.

- [ ] **Step 6: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py"
git commit -m "prioridades: conecta el indice y reordena la pestana en Para actuar hoy / Consulta y referencia"
```

---

## Después de las 6 tasks

No hace falta tocar `generar_todos.py`, `Actualizar_Sagarde.bat` ni ningún
otro panel: `bloque_prioridades()` mantiene su firma, y `generar_panel()` la
sigue llamando exactamente igual. La próxima vez que se ejecute
`Actualizar_Sagarde.bat` con normalidad (fuera de este plan), las 5 obras
con panel publicarán la pestaña Prioridades ya reorganizada.

Actualizar el mapa mental
(`_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`) si esta sesión también lo
hace, mencionando el índice plegable en la fila A15/panel de la tabla de
arquitectura — la norma del proyecto pide reflejarlo en la misma sesión que
cambia el entorno, no dejarlo para luego.
