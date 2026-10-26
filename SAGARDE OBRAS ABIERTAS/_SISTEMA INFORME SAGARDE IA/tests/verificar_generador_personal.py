# -*- coding: utf-8 -*-
"""Escenas de navegador de la app de la tablet (generador_personal.html). Playwright (Python). Exit 0 = todo bien.
Lo lanza tests/test_generador_personal.py (≈ 7 min); también se puede ejecutar a mano:
    py -3.11 tests/verificar_generador_personal.py        (P3_RAPIDO=1 para en el primer fallo)
Monta una carpeta de pruebas con la app, personal_calculo.js y un personal_estado.js inventado, fija la
fecha en el 23/10/2026 y recorre el flujo completo. El lote que exporta la app se valida con personal_obra.py
(P1). Viene del verificador de staging (paso 06): solo cambia de dónde salen la app, P1 y la carpeta de pruebas.
P3_SOLO_08C=1 = modo rápido del paso 08c: solo las escenas T80 en adelante (lápiz, desplegable completo, varios nombres).
P3_SOLO_08C2A=1 = modo rápido del paso 08c2a: solo las escenas T120 en adelante (el campo Empresa: crear, lápiz, varios nombres, lista, «Enviar al PC»).
P3_SOLO_08C2B=1 = modo rápido del paso 08c2b: solo las escenas T140 en adelante (la suma por empresa y la empresa junto al nombre en el Informe).
P3_SOLO_08D=1 = modo rápido del paso 08d: solo las escenas T90 en adelante (día nuevo con la gente anterior marcada, «Enviar al PC», nombre del fichero).
P3_APP = carpeta que tiene generador_personal.html, personal_calculo.js y personal_obra.py (por defecto, el motor)."""
import copy
import functools
import http.server
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
TRABAJO = os.environ.get('P3_APP') or os.path.dirname(BASE)
# Carpeta de pruebas ÚNICA por ejecución, en la carpeta temporal del sistema (variable P3_TMP para cambiarla).
SANDBOX = os.path.join(os.environ.get('P3_TMP', tempfile.gettempdir()), 'run_' + __import__('uuid').uuid4().hex[:8])
__import__('atexit').register(lambda: shutil.rmtree(SANDBOX, ignore_errors=True))
APP = os.path.join(TRABAJO, 'generador_personal.html')
CALC = os.path.join(TRABAJO, 'personal_calculo.js')
# P3_P1RUTA permite probar P3 contra otra copia de personal_obra.py (p. ej. mientras P1 aún se está escribiendo)
P1RUTA = os.environ.get('P3_P1RUTA') or os.path.join(TRABAJO, 'personal_obra.py')
H = {'lun': 7.5, 'mar': 7.5, 'mie': 7.5, 'jue': 7.5, 'vie': 7.5, 'sab': 0, 'dom': 0}
fallos = []


def ok(cond, msg):
    if not cond:
        fallos.append(msg)
        print('FALLO:', msg)
        if os.environ.get('P3_RAPIDO'):
            sys.stdout.flush()
            sys.exit(1)


def fila(fecha, ambito, nombre, horas, extra=0):
    return {'fecha': fecha, 'ambito': ambito, 'nombre': nombre, 'horas': horas, 'extra': extra}


def trab(i, n):
    return {'id': 'T%04d' % i, 'nombre': n, 'categoria': '', 'empresa': '', 'activo': True}


FILAS_OLA = [
    fila('2026-09-01', 'vivienda', 'Josu', 7.5), fila('2026-09-02', 'vivienda', 'Josu', 7.5), fila('2026-09-03', 'vivienda', 'Josu', 7.5),
    fila('2026-10-05', 'vivienda', 'Rafa', 7.5), fila('2026-10-06', 'vivienda', 'Rafa', 7.5),
    fila('2026-10-10', 'vivienda', 'Mikel', 5, 5),
    fila('2026-10-12', 'vivienda', 'Rafa', 7.5), fila('2026-10-12', 'vivienda', 'Mikel', 7.5),
    fila('2026-10-15', 'garaje', 'Andoni', 7.5), fila('2026-10-15', 'garaje', 'Txomin', 7.5),
    fila('2026-10-16', 'garaje', 'Andoni', 7.5),
    fila('2026-10-21', 'vivienda', 'Mikel', 7.5), fila('2026-10-21', 'vivienda', 'Txomin', 7.5),
    fila('2026-10-22', 'vivienda', 'Mikel', 7.5), fila('2026-10-22', 'vivienda', 'Txomin', 7.5),
]


def estado(filas_ola, generado, horario=None, ultima_viv=None):
    horario = horario or H
    return {
        'version': 1, 'generado': generado, 'jornada_base_h': 7.5,
        'catalogo': [trab(1, 'Mikel'), trab(2, 'Txomin'), trab(3, 'Rafa'), trab(4, 'Andoni'), trab(5, 'Josu'), trab(6, 'Pepe')],
        'obras': {
            'olabeaga': {
                'nombre': '2026 OLABEAGA BILBAO', 'cerrada': False, 'horario_semanal': horario, 'excepciones_horario': {},
                'ultima': {'vivienda': ultima_viv or {'fecha': '2026-10-22', 'presentes': [
                    {'nombre': 'Mikel', 'horas': 7.5, 'extra': 0}, {'nombre': 'Txomin', 'horas': 7.5, 'extra': 0}]},
                    'garaje': {'fecha': '2026-10-16', 'presentes': [{'nombre': 'Andoni', 'horas': 7.5, 'extra': 0}]}},
                'jornadas': filas_ola},
            'mungia': {
                'nombre': '2026 MUNGIA ACR NEINOR', 'cerrada': False, 'horario_semanal': H, 'excepciones_horario': {},
                'ultima': {'vivienda': {'fecha': '2026-10-21', 'presentes': [{'nombre': 'Pepe', 'horas': 7.5, 'extra': 0}]}, 'garaje': None},
                'jornadas': [fila('2026-10-21', 'vivienda', 'Pepe', 7.5)]},
            'vieja': {
                'nombre': '2024 OBRA CERRADA', 'cerrada': True, 'horario_semanal': H, 'excepciones_horario': {},
                'ultima': {'vivienda': None, 'garaje': None}, 'jornadas': [fila('2024-05-02', 'vivienda', 'Josu', 7.5)]},
        }}


def escribir_estado(datos):
    with open(os.path.join(SANDBOX, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
        fh.write('window.SAGARDE_PERSONAL = ' + json.dumps(datos, ensure_ascii=False) + ';\n')


def quitar_estado():
    ruta = os.path.join(SANDBOX, 'personal_estado.js')
    if os.path.exists(ruta):
        os.remove(ruta)


# Paso 08d (D5): un día nuevo sale con la gente de la jornada anterior marcada. Las pruebas de antes del 08d parten de la lista sin marcar:
# este JS desmarca por dentro (sin pulsar nada ni guardar borrador) lo que salió prerrellenado. Las escenas nuevas (T90+) no lo usan.
JS_SIN_PREVIA = "if (typeof a !== 'undefined' && a.prefill) { a.list.forEach(x => { x.on = false; }); a.prefill = null; render(); }"
MAIN = {'sin_previa': False}
FECHA_FIJA = """(() => { const fijo = new Date('2026-10-23T10:00:00+02:00').valueOf(); const Real = Date;
  class Falsa extends Real { constructor(...a) { if (a.length === 0) { super(fijo); } else { super(...a); } } static now() { return fijo; } }
  window.Date = Falsa; })();"""


def norm(t):
    return re.sub(r'\s+', ' ', t or '').strip()


# ---------------------------------------------------------------- comprobaciones estáticas
if not os.path.isfile(APP):
    print('FALLO: no existe generador_personal.html')
    sys.exit(1)
html = open(APP, encoding='utf-8').read()
ok(os.path.getsize(APP) < 300 * 1024, 'generador_personal.html debe pesar menos de 300 KB (pesa %d)' % os.path.getsize(APP))
ok(not re.search(r'(src|href)=["\']https?://', html), 'la app debe ser autocontenida: sin CDN ni enlaces externos')
ok('personal_calculo.js' in html and 'personal_estado.js' in html, 'debe cargar personal_calculo.js y personal_estado.js con <script src>')
ok('<html lang="es"' in html and 'name="viewport"' in html, 'faltan lang="es" o la meta viewport')
for n in ('Mikel', 'Txomin', 'Rafa', 'Andoni', 'Josu', 'Pepe', 'Zuri', 'El Gallego'):
    ok(n not in html, 'la app no debe llevar datos incrustados (aparece «%s»)' % n)
ok(not re.search(r'alias|mote\b', html, re.I), 'no debe aparecer «alias» ni «mote»: el trabajador es «nombre»')
# añadidas en el paso 01: codex:low llegó a dejar mojibake (Ã³, Â·, âœ“) y a parchear funciones por capas sin que nada lo viera
ok(not any(m in html for m in ('Ã', 'Â', 'â€', 'âœ', '�')), 'el fichero tiene mojibake (UTF-8 leído como cp1252, p. ej. «Ã³», «Â·», «âœ“»): se escribe siempre en UTF-8 limpio')
ok(not re.search(r'\w+Original\b|stopImmediatePropagation', html), 'no se parchean funciones por capas ni se anulan manejadores con stopImmediatePropagation: edita la función original y borra el código muerto')
ok(not re.search(r'(?m)^\s*(?:save|prepararFichero|render|init|appView|jornadasView|infoView|loadList|restore|reconcile)\s*=\s*(?:function|\()', html), 'no se reasignan funciones ya declaradas (save=function…): edita la función original')
ok(len(re.findall(r'\bfunction (?:save|prepararFichero|render|init|appView|jornadasView|infoView|loadList)\b', html)) == 8, 'cada función principal debe estar declarada una sola vez')
# añadida en el paso 01b: las preguntas van dentro de la página, nunca con ventanas del navegador (en el iPad bloquean o no se ven)
ok(not re.search(r'(?<![\w.])(?:confirm|alert|prompt)\s*\(', html), 'no se usan confirm(), alert() ni prompt(): las preguntas van dentro de la página')
ok(len(re.findall(r'\bfunction (?:guardarPropio|horarioDe)\b', html)) == 2, 'guardarPropio(nombre, objeto) y horarioDe(nombre, fecha) deben estar declaradas una sola vez')
# añadidas en el paso 08d: Chromium pone «.json» al descargar aunque el nombre no lo lleve y Safari del iPad no tiene por qué: se exige en el código;
# y del camino viejo de «Exportar» no debe quedar nada
ok("enlace.download = fichero.nombre + '.json'" in html, 'el fichero se descarga con «.json» escrito en su nombre')
ok(not re.search(r'lote_personal_|data-exportar|function exportar\b', html), 'no debe quedar nada del camino viejo de «Exportar» (nombre lote_personal_…, data-exportar, function exportar)')

if os.path.isdir(SANDBOX):
    shutil.rmtree(SANDBOX, ignore_errors=True)
os.makedirs(SANDBOX, exist_ok=True)
shutil.copy(APP, os.path.join(SANDBOX, 'generador_personal.html'))
shutil.copy(CALC, os.path.join(SANDBOX, 'personal_calculo.js'))
ESTADO1 = estado(FILAS_OLA, '2026-10-23T08:00:00+02:00')
escribir_estado(ESTADO1)
URL = 'file:///' + SANDBOX.replace(os.sep, '/').replace(' ', '%20') + '/generador_personal.html'

spec = importlib.util.spec_from_file_location('personal_obra_p1', P1RUTA)
P1 = None
if os.path.isfile(P1RUTA):
    try:
        P1 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(P1)
    except Exception as e:  # noqa: BLE001
        P1 = None
        ok(False, 'no se puede cargar personal_obra.py de P1: %r' % (e,))
else:
    ok(False, 'falta personal_obra.py de P1 en %s' % P1RUTA)


def valida_con_p1(lote):
    if P1 is None:
        return
    raiz = SANDBOX  # simulación (escribir=False): no crea nada. Una subcarpeta propia dejaba restos que Windows no deja borrar (ACL heredada)
    r = P1.ingerir_lote(copy.deepcopy(lote), raiz, {'olabeaga': '2026 OLABEAGA BILBAO'}, '2026-10-23', escribir=False,
                        ahora='2026-10-23T22:00:00+02:00')
    ok(r['ok'] and not r['lote_rechazado'], 'el lote exportado debe pasar la validación de P1 sin rechazos: %s' % json.dumps(r, ensure_ascii=False)[:600])


with sync_playwright() as p:
    b = p.chromium.launch()

    def contexto(ancho=390, alto=844):
        c = b.new_context(viewport={'width': ancho, 'height': alto}, timezone_id='Europe/Madrid', locale='es-ES', accept_downloads=True)
        c.add_init_script(FECHA_FIJA)
        return c

    ctx = contexto()
    pg = ctx.new_page()
    pg.set_default_timeout(4000)
    errs = []
    peticiones = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.on('request', lambda r: peticiones.append(r.url))

    def clic(sel, msg=None):
        if pg.query_selector(sel) is None:
            ok(False, msg or 'no existe el elemento %s' % sel)
            return False
        pg.click(sel, timeout=4000)
        if MAIN['sin_previa'] and ('data-amb' in sel or 'data-dia' in sel):
            pg.evaluate(JS_SIN_PREVIA)
        return True

    def espera_obra():
        try:
            pg.wait_for_selector('#obra', timeout=3000)
            return True
        except Exception:  # noqa: BLE001
            ok(False, 'no aparece el selector #obra tras cargar la app')
            return False

    def valor(sel):
        el = pg.query_selector(sel)
        return el.input_value() if el else ''

    def llenar(sel, v):
        if pg.query_selector(sel) is None:
            ok(False, 'no existe el campo %s' % sel)
            return False
        pg.fill(sel, v)
        pg.dispatch_event(sel, 'change')
        return True

    def txt(sel):
        el = pg.query_selector(sel)
        return norm(el.inner_text()) if el else ''

    def filas_lista():
        return pg.eval_on_selector_all('#v-app .row', 'e=>e.map(r=>r.dataset.nombre)')

    def marcados():
        return pg.eval_on_selector_all('#v-app .row', 'e=>e.filter(r=>r.querySelector(".x.on")).map(r=>r.dataset.nombre)')

    def pendientes():
        el = pg.query_selector('#pendientes')
        return el.get_attribute('data-n') if el else None

    def poner_fecha(v):
        if pg.query_selector('#fecha') is None:
            ok(False, 'no existe #fecha')
            return
        pg.evaluate("v=>{const e=document.getElementById('fecha');e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}))}", v)
        if MAIN['sin_previa']:
            pg.evaluate(JS_SIN_PREVIA)

    def exportar():
        # Paso 08d: se prepara desde la pestaña «Enviar al PC» (botón de la obra que se ve en «Anotar») y se vuelve a «Anotar».
        try:
            obra_id = pg.evaluate("document.querySelector('#obra') ? document.querySelector('#obra').value : ''")
            pg.click('nav button[data-v="enviar"]', timeout=3000)
            with pg.expect_download(timeout=5000) as d:
                pg.click('button[data-preparar="%s"]' % obra_id, timeout=3000)
            ruta = os.path.join(SANDBOX, 'descarga.json')
            d.value.save_as(ruta)
            pg.click('nav button[data-v="app"]', timeout=3000)
            return json.load(open(ruta, encoding='utf-8'))
        except Exception as e:  # noqa: BLE001
            ok(False, 'preparar el fichero no descarga un JSON válido desde «Enviar al PC» (button[data-preparar]): %s' % str(e)[:160])
            return {}

    def filas_informe():
        return pg.eval_on_selector_all('#v-informe table.data tbody tr', 'e=>e.map(r=>r.innerText.split(String.fromCharCode(10)).join(" ").split(String.fromCharCode(9)).join(" ").trim())')

    def fila_de(filas, nombre):
        return next((f for f in filas if f.split(' ')[0] == nombre.split(' ')[0] and f.startswith(nombre)), '')

    try:
        # --- T0: carga del estado
        pg.goto(URL)
        espera_obra()
        ok(pg.eval_on_selector_all('#obra option', 'e=>e.map(o=>o.value)') == ['olabeaga', 'mungia'], 'el selector #obra debe listar las obras no cerradas con su id como value')
        ok('al día' in txt('#estado-origen').lower(), '#estado-origen debe decir «Lista de trabajadores y obras al día» cuando carga personal_estado.js (08d: antes «publicado»): %r' % txt('#estado-origen'))
        ok(any('personal_estado.js?v=' in u for u in peticiones), 'personal_estado.js debe pedirse con ?v=<marca de tiempo> para saltarse la caché')
        ok(pg.is_visible('#sin-estado') is False if pg.query_selector('#sin-estado') else True, '#sin-estado no debe verse si hay estado')
        ok(pg.query_selector('#aviso-instalar') is not None and 'pantalla de inicio' in txt('#aviso-instalar'), 'falta #aviso-instalar con el texto «pantalla de inicio»')
        ok(valor('#fecha') == '2026-10-23', '#fecha debe empezar en hoy (23/10/2026): %r' % valor('#fecha'))

    except Exception as e:  # noqa: BLE001
        ok(False, 'T0 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T1 (reescrita en 08d, D5): lista inicial = última jornada + habituales, con MARCADA la gente de la última jornada anterior
        ok(filas_lista() == ['Mikel', 'Txomin', 'Rafa'], 'lista inicial de viviendas: última jornada + habituales (≥ 3 días en 30): %s' % filas_lista())
        ok(marcados() == ['Mikel', 'Txomin'], 'el viernes 23/10 sale marcada la gente del jueves 22/10 (Mikel y Txomin), no Rafa: %s' % marcados())
        ok(txt('#rotulo-marcados') == 'Marcados según la jornada del jueves 22/10: quita a quien no haya venido.', 'rótulo de la lista prerrellenada: %r' % txt('#rotulo-marcados'))
        clic('button[data-amb="garaje"]')
        ok(filas_lista() == ['Andoni'] and marcados() == ['Andoni'], 'lista inicial de garajes: la última jornada de garajes (viernes 16/10) marcada: %s %s' % (filas_lista(), marcados()))
        ok(txt('#rotulo-marcados') == 'Marcados según la jornada del viernes 16/10: quita a quien no haya venido.', 'rótulo de garajes: %r' % txt('#rotulo-marcados'))
        ok('on' in (pg.get_attribute('button[data-amb="garaje"]', 'class') or ''), 'el ámbito activo debe llevar la clase on')
        clic('button[data-amb="vivienda"]')
        ok(filas_lista() == ['Mikel', 'Txomin', 'Rafa'], 'al volver a viviendas vuelve su lista: %s' % filas_lista())
        # T2 en adelante (anteriores a 08d) parten de la lista sin marcar: se desmarca por dentro, sin pulsar nada ni guardar borrador
        MAIN['sin_previa'] = True
        pg.evaluate(JS_SIN_PREVIA)

    except Exception as e:  # noqa: BLE001
        ok(False, 'T1 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T2: marcar X fija las horas del horario del día (viernes = 7,5)
        clic('#v-app .row[data-nombre="Mikel"] .x')
        clic('#v-app .row[data-nombre="Rafa"] .x')
        ok(marcados() == ['Mikel', 'Rafa'], 'marcar X: %s' % marcados())
        ok(txt('#v-app .row[data-nombre="Mikel"] .step output') == '7,5 h', 'X fija las horas del horario del día: %r' % txt('#v-app .row[data-nombre="Mikel"] .step output'))
        ok('2 presentes' in txt('.sum') and '15 h' in txt('.sum'), 'el resumen debe decir «2 presentes · 15 h»: %r' % txt('.sum'))
        clic('#v-app .row[data-nombre="Rafa"] .step button[data-d="0.5"]')
        ok(txt('#v-app .row[data-nombre="Rafa"] .step output') == '8 h', 'el botón + suma 0,5 h')
        ok('0,5' in txt('#v-app .row[data-nombre="Rafa"]'), 'la fila debe mostrar +0,5 h extra')
        clic('#v-app .row[data-nombre="Rafa"] .step button[data-d="-0.5"]')
        ok(txt('#v-app .row[data-nombre="Rafa"] .step output') == '7,5 h', 'el botón − resta 0,5 h')
        clic('button[data-todos="0"]')
        ok(marcados() == [], 'Desmarcar todos')
        clic('button[data-todos="1"]')
        ok(marcados() == filas_lista(), 'Marcar todos')
        clic('button[data-todos="0"]')
        clic('#v-app .row[data-nombre="Mikel"] .x')
        clic('#v-app .row[data-nombre="Rafa"] .x')

    except Exception as e:  # noqa: BLE001
        ok(False, 'T2 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T3: añadir de la base con buscador; nombre nuevo; nombre repetido
        llenar('#filtro', 'an')
        ok(pg.eval_on_selector_all('#addsel option', 'e=>e.map(o=>o.textContent.trim())') == ['Andoni'], 'el filtro «an» debe dejar solo Andoni')
        clic('button[data-add]')
        ok('Andoni' in marcados(), 'añadir de la base debe poner a Andoni en la lista y marcado: %s' % marcados())
        llenar('#nuevo', '  Zuriñe  ')
        clic('button[data-nuevo]')
        ok('Zuriñe' in marcados(), 'un nombre nuevo se añade limpio (sin espacios de más) y marcado: %s' % filas_lista())
        llenar('#nuevo', 'mikel ')
        clic('button[data-nuevo]')
        if pg.query_selector('#nuevo-aviso [data-usar]'):
            clic('#nuevo-aviso [data-usar]')
        ok(sum(1 for n in filas_lista() if n.lower().startswith('mikel')) == 1, 'un nombre ya existente no se duplica: %s' % filas_lista())
        ok('Mikel' in marcados(), 'Mikel debe seguir marcado')

    except Exception as e:  # noqa: BLE001
        ok(False, 'T3 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T4: guardar jornada
        clic('button[data-guardar]')
        ok('guardada' in txt('#toast').lower(), 'guardar debe avisar con un toast «Jornada guardada…»: %r' % txt('#toast'))
        ok(pendientes() == '1', '#pendientes[data-n] debe valer 1 tras guardar: %r' % pendientes())
        pend = pg.evaluate("JSON.parse(localStorage.getItem('sgd_personal_pendientes') || 'null')")
        ok(isinstance(pend, list) and len(pend) == 1 and pend[0].get('obra') == 'olabeaga', 'sgd_personal_pendientes debe guardar la jornada con su obra: %s' % pend)

    except Exception as e:  # noqa: BLE001
        ok(False, 'T4 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T5: exportar el lote y validarlo con P1
        lote = exportar()
        ok(lote.get('tipo') == 'lote_personal' and lote.get('version') == 1 and lote.get('obra') == 'olabeaga', 'cabecera del lote: %s' % {k: lote.get(k) for k in ('tipo', 'version', 'obra')})
        ok(set(lote) <= {'tipo', 'version', 'obra', 'horario_semanal', 'excepciones_horario', 'jornadas', 'dispositivo'}, 'claves del lote fuera del contrato: %s' % sorted(lote))
        ok('horario_semanal' not in lote, 'sin cambiar el horario, el lote no debe llevar horario_semanal')
        ok(set(lote) == {'tipo', 'version', 'obra', 'jornadas'}, 'una obra sin ningún horario propio exporta exactamente el lote de siempre (sin excepciones_horario): %s' % sorted(lote))
        js = lote.get('jornadas', [])
        ok(len(js) == 1 and js[0].get('ambito') == 'vivienda' and js[0].get('fecha') == '2026-10-23' and js[0].get('anulada') is False, 'la jornada exportada: %s' % js)
        if js:
            ok(set(js[0]) <= {'ambito', 'fecha', 'presentes', 'anulada', 'notas', 'registrado'}, 'claves de la jornada fuera del contrato: %s' % sorted(js[0]))
            pres = {x['nombre']: x for x in js[0]['presentes']}
            ok(set(pres) == {'Mikel', 'Rafa', 'Andoni', 'Zuriñe'}, 'presentes exportados: %s' % sorted(pres))
            ok(all(x['horas'] == 7.5 and x.get('extra', 0) == 0 and set(x) <= {'nombre', 'horas', 'extra'} for x in pres.values()), 'horas y extra de los presentes: %s' % pres)
            ok(isinstance(js[0].get('registrado'), str) and len(js[0]['registrado']) >= 19, 'registrado debe ser una fecha y hora ISO')
        valida_con_p1(lote)

    except Exception as e:  # noqa: BLE001
        ok(False, 'T5 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T6: informe de personal (publicado + pendiente), cifras hechas a mano
        clic('button[data-v="informe"]')
        fi = filas_informe()
        ok([f.split(' ')[0] for f in fi] == ['Mikel', 'Rafa', 'Andoni', 'Txomin', 'Zuriñe'], 'orden del informe (octubre, todo): %s' % fi)
        ok('35' in fila_de(fi, 'Mikel').split(' ') and '29,8' in fila_de(fi, 'Mikel'), 'Mikel: 35 h y 29,8 %%: %r' % fila_de(fi, 'Mikel'))
        ok('30' in fila_de(fi, 'Rafa').split(' ') and '25,5' in fila_de(fi, 'Rafa'), 'Rafa: 30 h y 25,5 %%: %r' % fila_de(fi, 'Rafa'))
        ok('redondean' in txt('#v-informe'), 'falta la nota «los porcentajes se redondean…»')
        clic('#v-informe button[data-a="garaje"]')
        fg = filas_informe()
        ok([f.split(' ')[0] for f in fg] == ['Andoni', 'Txomin'] and '66,7' in fila_de(fg, 'Andoni') and '33,3' in fila_de(fg, 'Txomin'), 'informe solo garajes: %s' % fg)
        clic('#v-informe button[data-a="todo"]')
        clic('#v-informe button[data-p="anio"]')
        clic('#v-informe button[data-m="-1"]')
        ok('sin jornadas' in txt('#v-informe').lower(), 'un periodo sin datos debe decir «Sin jornadas», nunca 0 h')
        clic('#v-informe button[data-m="1"]')
        clic('#v-informe button[data-p="mes"]')

    except Exception as e:  # noqa: BLE001
        ok(False, 'T6 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T7: pantalla Jornadas: corregir y anular (propuesta A)
        clic('button[data-v="jornadas"]')
        items = pg.eval_on_selector_all('#v-jornadas .jor-item', 'e=>e.map(i=>[i.dataset.obra,i.dataset.ambito,i.dataset.fecha,i.classList.contains("pendiente")])')
        claves = {(a, f) for o, a, f, pe in items}
        esperado = {('vivienda', '2026-10-23'), ('vivienda', '2026-10-22'), ('vivienda', '2026-10-21'), ('garaje', '2026-10-16'),
                    ('garaje', '2026-10-15'), ('vivienda', '2026-10-12'), ('vivienda', '2026-10-10')}
        ok(claves == esperado, 'jornadas listadas (pendientes + publicadas de los últimos 14 días): %s' % sorted(claves))
        ok([pe for o, a, f, pe in items if (a, f) == ('vivienda', '2026-10-23')] == [True], 'la jornada sin ingerir debe llevar la clase pendiente')
        clic('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-22"] button[data-abrir]')
        ok(valor('#fecha') == '2026-10-22' and marcados() == ['Mikel', 'Txomin'], 'abrir una jornada la carga en el formulario: %s %s' % (valor('#fecha'), marcados()))
        clic('#v-app .row[data-nombre="Txomin"] .x')
        clic('button[data-guardar]')
        ok(pendientes() == '2', 'corregir y guardar una jornada publicada crea un pendiente: %r' % pendientes())
        clic('button[data-v="jornadas"]')
        clic('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-21"] button[data-anular]')
        ok(pg.query_selector('#confirmar') is not None and pg.is_visible('#confirmar'), 'anular debe pedir confirmación dentro de la página (#confirmar)')
        clic('#confirmar button[data-confirmar="si"]')
        ok(pendientes() == '3', 'anular confirmado crea un pendiente: %r' % pendientes())
        lote2 = exportar()
        por_clave = {(j['ambito'], j['fecha']): j for j in lote2.get('jornadas', [])}
        ok(set(por_clave) == {('vivienda', '2026-10-23'), ('vivienda', '2026-10-22'), ('vivienda', '2026-10-21')}, 'el lote exporta los 3 pendientes: %s' % sorted(por_clave))
        anul = por_clave.get(('vivienda', '2026-10-21'), {})
        ok(anul.get('anulada') is True and anul.get('presentes') == [], 'la jornada anulada se exporta con anulada=true y sin presentes: %s' % anul)
        ok([x['nombre'] for x in por_clave.get(('vivienda', '2026-10-22'), {}).get('presentes', [])] == ['Mikel'], 'la jornada corregida solo lleva a Mikel')
        valida_con_p1(lote2)
        clic('button[data-v="informe"]')
        fi2 = filas_informe()
        ok([f.split(' ')[0] for f in fi2] == ['Rafa', 'Mikel', 'Andoni', 'Txomin', 'Zuriñe'], 'el informe debe aplicar correcciones y anulaciones pendientes: %s' % fi2)
        ok('30' in fila_de(fi2, 'Rafa').split(' ') and '31,6' in fila_de(fi2, 'Rafa'), 'Rafa: 30 h y 31,6 %%: %r' % fila_de(fi2, 'Rafa'))
        ok('27,5' in fila_de(fi2, 'Mikel').split(' '), 'Mikel: 27,5 h: %r' % fila_de(fi2, 'Mikel'))
        ok('7,5' in fila_de(fi2, 'Txomin').split(' '), 'Txomin: 7,5 h: %r' % fila_de(fi2, 'Txomin'))

    except Exception as e:  # noqa: BLE001
        ok(False, 'T7 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T8: horario semanal editable y aviso
        clic('button[data-v="app"]')
        clic('details#horario summary')
        llenar('input[data-hor="5"]', '7')
        ok(pg.query_selector('#aviso-horario') is not None and 'no modifica' in txt('#aviso-horario').lower(), 'al cambiar el horario debe verse #aviso-horario con «no modifica las jornadas ya guardadas»')
        lote3 = exportar()
        ok(lote3.get('horario_semanal') == dict(H, vie=7), 'el lote debe llevar el horario cambiado: %s' % lote3.get('horario_semanal'))
        valida_con_p1(lote3)

    except Exception as e:  # noqa: BLE001
        ok(False, 'T8 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T9: lo ya ingerido deja de ser pendiente al publicarse el estado nuevo
        f2 = [f for f in FILAS_OLA if f['fecha'] != '2026-10-21' and f['fecha'] != '2026-10-22']
        f2 += [fila('2026-10-22', 'vivienda', 'Mikel', 7.5)]
        f2 += [fila('2026-10-23', 'vivienda', n, 7.5) for n in ('Mikel', 'Rafa', 'Andoni', 'Zuriñe')]
        ESTADO2 = estado(f2, '2026-10-23T23:00:00+02:00', horario=dict(H, vie=7),
                         ultima_viv={'fecha': '2026-10-23', 'presentes': [{'nombre': n, 'horas': 7.5, 'extra': 0} for n in ('Mikel', 'Rafa', 'Andoni', 'Zuriñe')]})
        escribir_estado(ESTADO2)
        pg.reload()
        espera_obra()
        ok(pendientes() == '0', 'las jornadas ya publicadas deben dejar de ser pendientes (reconciliación): %r' % pendientes())
        clic('button[data-v="informe"]')
        fi3 = filas_informe()
        ok([f.split(' ')[0] for f in fi3] == ['Rafa', 'Mikel', 'Andoni', 'Txomin', 'Zuriñe'] and '31,6' in fila_de(fi3, 'Rafa'), 'el informe publicado coincide con el que salía con los pendientes: %s' % fi3)

    except Exception as e:  # noqa: BLE001
        ok(False, 'T9 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T10: día sin horario (sábado): las horas son obligatorias
        clic('button[data-v="app"]')
        poner_fecha('2026-10-24')
        clic('#v-app .row[data-nombre="Mikel"] .x') if 'Mikel' not in marcados() else None
        ok('Mikel' in marcados(), 'Mikel debe poder marcarse el sábado')
        ok(txt('#v-app .row[data-nombre="Mikel"] .step output.falta') == '¿horas?', 'sin horario, la fila debe mostrar «¿horas?» (output.falta): %r' % txt('#v-app .row[data-nombre="Mikel"] .step'))
        ok('faltan horas' in txt('.sum').lower(), 'el resumen debe decir «faltan horas»: %r' % txt('.sum'))
        antes = pendientes()
        clic('button[data-guardar]')
        ok('faltan' in txt('#toast').lower() and pendientes() == antes, 'sin horas no se guarda: toast «Faltan las horas de: …»: %r' % txt('#toast'))
        clic('#v-app .row[data-nombre="Mikel"] .step button >> nth=0')
        ok(txt('#v-app .row[data-nombre="Mikel"] .step output') == '7,5 h', 'el primer toque fija 7,5 h: %r' % txt('#v-app .row[data-nombre="Mikel"] .step output'))
        clic('button[data-guardar]')
        ok(pendientes() == str(int(antes) + 1), 'con horas puestas, guardar sí guarda el sábado: %r' % pendientes())
        sab = [j for j in exportar().get('jornadas', []) if j['fecha'] == '2026-10-24']
        ok(sab and sab[0]['presentes'][0]['horas'] == 7.5 and sab[0]['presentes'][0].get('extra') == 7.5, 'el sábado todo cuenta como extra: %s' % sab)

    except Exception as e:  # noqa: BLE001
        ok(False, 'T10 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T11: borrador automático
        poner_fecha('2026-10-23')
        antes_on = marcados()
        clic('#v-app .row[data-nombre="Rafa"] .x')
        despues = marcados()
        ok(pg.evaluate("localStorage.getItem('sgd_personal_borrador')") is not None, 'falta el borrador en localStorage (sgd_personal_borrador)')
        pg.reload()
        espera_obra()
        ok(marcados() == despues and valor('#fecha') == '2026-10-23', 'al recargar se restaura el borrador: %s (esperado %s)' % (marcados(), despues))
        ok('borrador' in txt('#v-app').lower(), 'debe verse un texto de borrador guardado automáticamente')

    except Exception as e:  # noqa: BLE001
        ok(False, 'T11 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T12: aviso de instalación y cerrarlo
        if clic('button[data-cerrar-aviso]'):
            pg.reload()
            espera_obra()
            ok(pg.query_selector('#aviso-instalar') is None or not pg.is_visible('#aviso-instalar'), 'el aviso cerrado no debe volver a salir')

    except Exception as e:  # noqa: BLE001
        ok(False, 'T12 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T13: tamaños táctiles y desbordamiento
        clic('#v-app .row[data-nombre="Rafa"] .x') if 'Rafa' not in marcados() else None
        t = pg.evaluate("""() => { const q = s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; };
           return {x: q('#v-app .row .x'), step: q('#v-app .row .step button'), btn: q('button[data-guardar]'), amb: q('button[data-amb]')}; }""")
        ok(t['x'] and t['x'][0] >= 56 and t['x'][1] >= 56, 'el cuadro X debe medir al menos 56×56 px: %s' % t['x'])
        ok(t['step'] and t['step'][0] >= 48 and t['step'][1] >= 48, 'los botones + y − deben medir al menos 48×48 px: %s' % t['step'])
        ok(t['btn'] and t['btn'][1] >= 52, 'Guardar debe medir al menos 52 px de alto: %s' % t['btn'])
        ok(t['amb'] and t['amb'][1] >= 48, 'el selector de ámbito debe medir al menos 48 px de alto: %s' % t['amb'])
        for v in ('app', 'jornadas', 'informe'):
            clic('button[data-v="%s"]' % v)
            ok(pg.evaluate('document.documentElement.scrollWidth') <= 391, 'desbordamiento horizontal en móvil en la vista %s: %s' % (v, pg.evaluate('document.documentElement.scrollWidth')))
        pg.set_viewport_size({'width': 820, 'height': 1180})
        for v in ('app', 'jornadas', 'informe'):
            clic('button[data-v="%s"]' % v)
            ok(pg.evaluate('document.documentElement.scrollWidth') <= 821, 'desbordamiento horizontal en tablet en la vista %s' % v)
            ok(pg.is_visible('#v-%s' % v), 'la vista %s debe verse en tablet' % v)
        pg.set_viewport_size({'width': 390, 'height': 844})

    except Exception as e:  # noqa: BLE001
        ok(False, 'T13 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T14: sin red usa la copia local
        ok(pg.evaluate("localStorage.getItem('sgd_personal_estado')") is not None, 'la app debe guardar la copia del estado en sgd_personal_estado')
        quitar_estado()
        pg.reload()
        espera_obra()
        ok(pg.eval_on_selector_all('#obra option', 'e=>e.map(o=>o.value)') == ['olabeaga', 'mungia'], 'sin personal_estado.js la app debe usar la copia local')
        ok('guardada' in txt('#estado-origen').lower(), '#estado-origen debe decir «lista guardada» al usar la copia local (08d: antes «copia»): %r' % txt('#estado-origen'))

    except Exception as e:  # noqa: BLE001
        ok(False, 'T14 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T15: sin estado ni copia
        ctx2 = contexto()
        pg2 = ctx2.new_page()
        pg2.set_default_timeout(4000)
        errs2 = []
        pg2.on('pageerror', lambda e: errs2.append(str(e)))
        pg2.goto(URL)
        pg2.wait_for_timeout(500)
        ok(pg2.query_selector('#sin-estado') is not None and pg2.is_visible('#sin-estado'), 'sin estado ni copia debe verse #sin-estado')
        ok(not errs2, 'errores de JavaScript sin estado: %s' % errs2)
        ctx2.close()

    except Exception as e:  # noqa: BLE001
        ok(False, 'T15 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    # ======================================================================================================================
    # Bloque añadido en el paso 01 (revisión + mutaciones). Cada escena usa su propio contexto y su propia carpeta, con su
    # propio personal_estado.js, para no tocar los datos de T0–T15. Los números salen de datos inventados hechos a mano.
    # ======================================================================================================================
    import uuid

    class Escena:
        """Una página nueva (contexto propio) con la app, personal_calculo.js y un personal_estado.js dado."""

        def __init__(self, datos, init=None, ancho=390, alto=844, hoy='2026-10-23T10:00:00+02:00', con_estado=True):
            self.dir = os.path.join(SANDBOX, 'esc_' + uuid.uuid4().hex[:6])
            os.makedirs(self.dir)
            shutil.copy(APP, os.path.join(self.dir, 'generador_personal.html'))
            shutil.copy(CALC, os.path.join(self.dir, 'personal_calculo.js'))
            if con_estado:
                with open(os.path.join(self.dir, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
                    fh.write('window.SAGARDE_PERSONAL = ' + json.dumps(datos, ensure_ascii=False) + ';\n')
            self.url = 'file:///' + self.dir.replace(os.sep, '/').replace(' ', '%20') + '/generador_personal.html'
            self.ctx = b.new_context(viewport={'width': ancho, 'height': alto}, timezone_id='Europe/Madrid', locale='es-ES', accept_downloads=True)
            self.ctx.add_init_script(FECHA_FIJA.replace('2026-10-23T10:00:00+02:00', hoy))
            if init:
                self.ctx.add_init_script(init)
            self.pg = self.ctx.new_page()
            self.pg.set_default_timeout(4000)
            self.errs = []
            self.previa = False
            self.pg.on('pageerror', lambda e: self.errs.append(str(e)))

        def sin_previa(self):
            if not self.previa:
                self.pg.evaluate(JS_SIN_PREVIA)

        def ir(self, esperar_obra=True, previa=False):
            self.pg.goto(self.url)
            if esperar_obra:
                try:
                    self.pg.wait_for_selector('#obra', timeout=3000)
                except Exception:  # noqa: BLE001
                    pass
            # Paso 08d (D5): las escenas de antes del 08d parten de la lista sin marcar (solo si salió prerrellenada, para no tocar un
            # borrador restaurado). Lo nuevo se prueba en T90+ con previa=True.
            self.previa = previa
            self.sin_previa()
            return self

        def cerrar(self):
            self.ctx.close()

        def txt(self, sel):
            el = self.pg.query_selector(sel)
            return norm(el.inner_text()) if el else ''

        def valor(self, sel):
            el = self.pg.query_selector(sel)
            return el.input_value() if el else ''

        def clic(self, sel):
            if self.pg.query_selector(sel) is None:
                ok(False, 'no existe el elemento %s' % sel)
                return False
            self.pg.click(sel, timeout=4000)
            if 'data-amb' in sel or 'data-dia' in sel:
                self.sin_previa()
            return True

        def filas(self):
            return self.pg.eval_on_selector_all('#v-app .row', 'e=>e.map(r=>r.dataset.nombre)')

        def marcados(self):
            return self.pg.eval_on_selector_all('#v-app .row', 'e=>e.filter(r=>r.querySelector(".x.on")).map(r=>r.dataset.nombre)')

        def pendientes(self):
            el = self.pg.query_selector('#pendientes')
            return el.get_attribute('data-n') if el else None

        def fecha(self, v):
            self.pg.evaluate("v=>{const e=document.getElementById('fecha');e.value=v;e.dispatchEvent(new Event('change',{bubbles:true}))}", v)
            self.sin_previa()

        def obra(self, v):
            self.pg.select_option('#obra', v)
            self.sin_previa()

        def horas(self, nombre):
            return self.txt('#v-app .row[data-nombre="%s"] .step output' % nombre)

        def pulsar(self, nombre, veces, d='0.5'):
            """Pulsa + o − varias veces (la vista se repinta en cada pulsación, así que se vuelve a buscar el botón)."""
            self.pg.evaluate("""([n,d,k])=>{for(let i=0;i<k;i++){const b=document.querySelector('#v-app .row[data-nombre="'+n+'"] .step button[data-d="'+d+'"]');if(b)b.click();}}""", [nombre, d, veces])

        def toast(self):
            return self.txt('#toast').lower()

        def anotar(self, nombre):
            """Marca a alguien: si ya está en la lista, con su X; si no, lo añade de la base."""
            if self.pg.query_selector('#v-app .row[data-nombre="%s"]' % nombre):
                if nombre not in self.marcados():
                    self.clic('#v-app .row[data-nombre="%s"] .x' % nombre)
            else:
                self.pg.select_option('#addsel', nombre)
                self.clic('button[data-add]')

        def exportar(self, esperar=True, obra=None):
            """Paso 08d: prepara el fichero de la obra que se ve en «Anotar» (o la indicada) desde «Enviar al PC» y vuelve a «Anotar».
            Devuelve su contenido, o None si esa obra no tiene nada por enviar (entonces no hay botón). Guarda el nombre en self.descarga."""
            try:
                obra_id = obra or self.pg.evaluate("document.querySelector('#obra') ? document.querySelector('#obra').value : ''")
                self.pg.click('nav button[data-v="enviar"]', timeout=3000)
                boton = 'button[data-preparar="%s"]' % obra_id
                if self.pg.query_selector(boton) is None:
                    self.pg.click('nav button[data-v="app"]', timeout=3000)
                    return None
                with self.pg.expect_download(timeout=5000 if esperar else 1500) as d:
                    self.pg.click(boton, timeout=3000)
                ruta = os.path.join(self.dir, 'descarga.json')
                d.value.save_as(ruta)
                self.descarga = d.value.suggested_filename
                self.pg.click('nav button[data-v="app"]', timeout=3000)
                return json.load(open(ruta, encoding='utf-8'))
            except Exception:  # noqa: BLE001
                return None

        def listo(self):
            """Texto del recuadro «Listo» de «Enviar al PC» (está en la página aunque esa pestaña no se vea)."""
            el = self.pg.query_selector('#listo')
            return norm(el.text_content()) if el else ''

        def enviar_txt(self, sel):
            el = self.pg.query_selector(sel)
            return norm(el.text_content()) if el else ''

        def informe(self):
            return self.pg.eval_on_selector_all('#v-informe table.data tbody tr', 'e=>e.map(r=>r.innerText.split(String.fromCharCode(10)).join(" ").split(String.fromCharCode(9)).join(" ").trim())')

    def con_escena(nombre, datos, fn, **kw):
        """Ejecuta una escena; cualquier excepción se convierte en un fallo legible y no tumba las demás."""
        if os.environ.get('P3_SOLO_08C2B') == '1':     # modo del paso 08c2b: solo las escenas T140 en adelante (la suma por empresa en el Informe)
            m = re.match(r'T(\d+)', nombre)
            if not (m and int(m.group(1)) >= 140):
                return
        if os.environ.get('P3_SOLO_08C2A') == '1':     # modo del paso 08c2a: solo las escenas T120 en adelante (el campo Empresa)
            m = re.match(r'T(\d+)', nombre)
            if not (m and int(m.group(1)) >= 120):
                return
        if os.environ.get('P3_SOLO_08D') == '1':     # modo del paso 08d: solo las escenas T90 en adelante
            m = re.match(r'T(\d+)', nombre)
            if not (m and int(m.group(1)) >= 90):
                return
        if os.environ.get('P3_SOLO_08C') == '1':     # modo del paso 08c: solo las escenas T80 en adelante (las comprobaciones estáticas corren siempre)
            m = re.match(r'T(\d+)', nombre)
            if not (m and int(m.group(1)) >= 80):
                return
        if os.environ.get('P3_SOLO_NUEVAS') == '1':     # modo de las mutaciones del paso 01b: solo lo nuevo (T52 en adelante) y las dos escenas viejas que tocan lo nuevo
            m = re.match(r'T(\d+)', nombre)
            if m and int(m.group(1)) < 52 and not nombre.startswith(('T23b', 'T27')):
                return
        e = None
        try:
            e = Escena(datos, **kw)
            fn(e)
        except Exception as ex:  # noqa: BLE001
            ok(False, '%s se interrumpió: %s' % (nombre, (str(ex).strip().splitlines() or [repr(ex)])[0][:220]))
        finally:
            if e is not None:
                ok(not e.errs, '%s: errores de JavaScript: %s' % (nombre, e.errs))
                e.cerrar()

    def estado_con(obras, catalogo, generado='2026-10-23T08:00:00+02:00'):
        return {'version': 1, 'generado': generado, 'jornada_base_h': 7.5, 'catalogo': [trab(i + 1, n) for i, n in enumerate(catalogo)], 'obras': obras}

    def obra_est(nombre, filas, ultima=None, cerrada=False, horario=None, excep=None):
        return {'nombre': nombre, 'cerrada': cerrada, 'horario_semanal': horario or H, 'excepciones_horario': excep or {},
                'ultima': ultima or {'vivienda': None, 'garaje': None}, 'jornadas': filas}

    def pres(*nombres):
        return [{'nombre': n, 'horas': 7.5, 'extra': 0} for n in nombres]

    # --- T16: lista por defecto = última jornada + habituales (≥ 3 fechas en los 30 días anteriores, límite inclusivo, mismo ámbito y obra)
    def t16(e):
        e.ir(previa=True)
        ok(e.filas() == ['Fran', 'Ana', 'Beto', 'Dani'], 'T16 lista de viviendas = última jornada (en su orden) + habituales por nombre, sin repetir: %s' % e.filas())
        ok(e.marcados() == ['Fran', 'Ana'], 'T16 (08d) de esa lista salen marcados solo los de la última jornada anterior (22/10: Fran y Ana); los habituales, sin marcar: %s' % e.marcados())
        e.clic('button[data-amb="garaje"]')
        ok(e.filas() == ['Hugo'] and e.marcados() == ['Hugo'], 'T16 lista de garajes: solo cuentan las fechas del propio ámbito (Eva: 2 de garaje + 2 de vivienda no es habitual): %s %s' % (e.filas(), e.marcados()))
    d16 = [fila(f, 'vivienda', 'Ana', 7.5) for f in ('2026-10-05', '2026-10-06')]  # 2 días: no es habitual
    d16 += [fila(f, 'vivienda', 'Beto', 7.5) for f in ('2026-09-23', '2026-10-01', '2026-10-02')]  # 09-23 = justo 30 días antes (incluido)
    d16 += [fila(f, 'vivienda', 'Carlos', 7.5) for f in ('2026-09-22', '2026-10-01', '2026-10-02')]  # 09-22 = 31 días antes (fuera): solo 2
    d16 += [fila(f, 'vivienda', 'Dani', 7.5) for f in ('2026-10-14', '2026-10-15', '2026-10-16')]
    d16 += [fila(f, 'vivienda', 'Eva', 7.5) for f in ('2026-10-19', '2026-10-20')] + [fila(f, 'garaje', 'Eva', 7.5) for f in ('2026-10-19', '2026-10-20')]
    d16 += [fila('2026-10-22', 'vivienda', 'Fran', 7.5), fila('2026-10-22', 'vivienda', 'Ana', 7.5), fila('2026-10-22', 'garaje', 'Hugo', 7.5)]  # 08d: la última jornada por filas = la de «ultima»
    d16 += [fila(f, 'vivienda', 'Fran', 7.5) for f in ('2026-10-12', '2026-10-13', '2026-10-14')]  # habitual y además en «última»
    d16 += [fila(f, 'garaje', 'Hugo', 7.5) for f in ('2026-10-12', '2026-10-13', '2026-10-14')]
    s16 = estado_con({
        'olabeaga': obra_est('2026 OLABEAGA BILBAO', d16, ultima={'vivienda': {'fecha': '2026-10-22', 'presentes': pres('Fran', 'Ana')}, 'garaje': None}),
        'mungia': obra_est('2026 MUNGIA', [fila(f, 'vivienda', 'Gus', 7.5) for f in ('2026-10-12', '2026-10-13', '2026-10-14')])},
        ['Ana', 'Beto', 'Carlos', 'Dani', 'Eva', 'Fran', 'Gus', 'Hugo'])
    con_escena('T16', s16, t16)

    # --- T17: los nombres escritos a mano se resuelven contra el catálogo por clave («mikel» = «Mikel»), también sin ingerir
    def t17(e):
        e.ir()
        e.clic('button[data-v="informe"]')
        fi = e.informe()
        ok([f.split(' ')[0] for f in fi] == ['Mikel', 'Txomin'], 'T17 informe: «mikel»/«MIKEL» y «TXOMIN» deben contarse como Mikel y Txomin: %s' % fi)
        ok(fila_de(fi, 'Mikel').split(' ')[1] == '2', 'T17 Mikel debe tener 2 días (uno publicado en minúsculas y uno pendiente): %r' % fila_de(fi, 'Mikel'))
    pend17 = [{'obra': 'olabeaga', 'ambito': 'vivienda', 'fecha': '2026-10-22', 'presentes': [{'nombre': 'mikel', 'horas': 7.5, 'extra': 0}, {'nombre': 'TXOMIN', 'horas': 7.5, 'extra': 0}],
               'anulada': False, 'notas': '', 'registrado': '2026-10-22T18:00:00.000Z'}]
    s17 = estado_con({'olabeaga': obra_est('2026 OLABEAGA BILBAO', [fila('2026-10-20', 'vivienda', 'mikel', 7.5)])}, ['Mikel', 'Txomin'])
    con_escena('T17', s17, t17, init="if(!localStorage.getItem('_s')){localStorage.setItem('_s','1');localStorage.setItem('sgd_personal_pendientes',%s)}" % json.dumps(json.dumps(pend17)))

    # --- T18: nombre nuevo parecido a uno existente → aviso con «Sí» y «No, crear»
    def t18(e):
        e.ir()
        e.pg.fill('#nuevo', 'Mikell')
        e.clic('button[data-nuevo]')
        av = e.txt('#nuevo-aviso')
        ok('Se parece a «Mikel»' in av, 'T18 «Mikell» debe avisar «Se parece a «Mikel»»: %r' % av)
        ok(e.pg.query_selector('#nuevo-aviso [data-usar="Mikel"]') is not None and e.pg.query_selector('#nuevo-aviso [data-crear="Mikell"]') is not None, 'T18 faltan los botones data-usar="Mikel" y data-crear="Mikell"')
        e.clic('#nuevo-aviso [data-crear="Mikell"]')
        ok('Mikell' in e.marcados() and e.txt('#nuevo-aviso') == '', 'T18 «No, crear» añade Mikell marcado y quita el aviso: %s' % e.marcados())
        e.pg.fill('#nuevo', 'Rafael')
        e.clic('button[data-nuevo]')
        ok('Se parece a «Rafa»' in e.txt('#nuevo-aviso'), 'T18 «Rafael» contiene a «Rafa»: debe avisar: %r' % e.txt('#nuevo-aviso'))
        e.clic('#nuevo-aviso [data-usar="Rafa"]')
        ok('Rafa' in e.marcados() and 'Rafael' not in e.filas(), 'T18 «Sí» usa el nombre existente y no crea el nuevo: %s' % e.filas())
        e.pg.fill('#nuevo', 'Al')
        e.clic('button[data-nuevo]')
        ok(e.txt('#nuevo-aviso') == '' and 'Al' in e.marcados(), 'T18 los nombres de menos de 3 letras no avisan (dan ruido): %r' % e.txt('#nuevo-aviso'))
    con_escena('T18', ESTADO1, t18)

    # --- T19: anular pide confirmación; «No» no anula y cierra; la confirmación aparece a la vista
    def t19(e):
        e.ir()
        e.clic('button[data-v="jornadas"]')
        e.pg.eval_on_selector('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-12"]', 'e=>e.scrollIntoView({block:"center"})')
        e.clic('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-12"] button[data-anular]')
        ok(e.pg.is_visible('#confirmar'), 'T19 anular debe mostrar #confirmar')
        pos = e.pg.evaluate("(()=>{const r=document.querySelector('#confirmar').getBoundingClientRect();return [r.top,r.bottom,innerHeight]})()")
        ok(pos[0] >= 0 and pos[1] <= pos[2], 'T19 la confirmación debe verse en pantalla justo al pulsar Anular (no al final de una lista larga): top=%d bottom=%d alto=%d' % tuple(pos))
        e.clic('#confirmar button[data-confirmar="no"]')
        ok(e.pendientes() == '0' and not e.pg.is_visible('#confirmar'), 'T19 «No» no anula nada y cierra la confirmación: pendientes=%r' % e.pendientes())
        e.clic('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-12"] button[data-anular]')
        e.clic('#confirmar button[data-confirmar="si"]')
        ok(e.pendientes() == '1', 'T19 «Sí» anula: pendientes=%r' % e.pendientes())
        item = e.txt('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-12"]').lower()
        ok('anulada' in item, 'T19 una jornada anulada pendiente debe decir «anulada» en la lista: %r' % item)
    con_escena('T19', ESTADO1, t19)

    # --- T20: ventana de Jornadas: de hoy−14 a hoy, ambos incluidos; ni más viejas ni futuras
    def t20(e):
        e.ir()
        e.clic('button[data-v="jornadas"]')
        cl = e.pg.eval_on_selector_all('#v-jornadas .jor-item', 'e=>e.map(i=>i.dataset.fecha)')
        ok(sorted(cl) == ['2026-10-09', '2026-10-10', '2026-10-23'], 'T20 jornadas listadas (14 días hacia atrás desde hoy, sin futuras): %s' % cl)
    f20 = [fila(f, 'vivienda', 'Mikel', 7.5) for f in ('2026-10-08', '2026-10-09', '2026-10-10', '2026-10-23', '2026-10-24')]
    con_escena('T20', estado_con({'olabeaga': obra_est('2026 OLABEAGA', f20)}, ['Mikel']), t20)

    # --- T21: obra inicial = primera NO cerrada; sin ninguna obra abierta no hay error y se explica
    def t21(e):
        e.ir()
        ok(e.pg.eval_on_selector_all('#obra option', 'e=>e.map(o=>o.value)') == ['olabeaga'] and e.valor('#obra') == 'olabeaga', 'T21 con la primera obra cerrada, la inicial es la primera abierta: %s' % e.valor('#obra'))
        ok(e.pg.eval_on_selector_all('#obra-j option', 'e=>e.map(o=>o.value)') == ['olabeaga'], 'T21 Jornadas tampoco debe listar obras cerradas')
    con_escena('T21', estado_con({'vieja': obra_est('2024 CERRADA', [], cerrada=True), 'olabeaga': obra_est('2026 OLABEAGA', [])}, ['Mikel']), t21)

    def t21b(e):
        e.ir(esperar_obra=False)
        e.pg.wait_for_timeout(500)
        ok(e.pg.query_selector('#sin-obras') is not None and 'obras abiertas' in e.txt('#sin-obras').lower(), 'T21b sin obras abiertas debe verse #sin-obras «No hay obras abiertas…»: %r' % e.txt('#v-app')[:120])
        for v in ('jornadas', 'informe'):
            e.clic('button[data-v="%s"]' % v)
        e.clic('button[data-v="app"]')
    con_escena('T21b', estado_con({'vieja': obra_est('2024 CERRADA', [], cerrada=True)}, ['Mikel']), t21b)
    con_escena('T21c', estado_con({}, []), t21b)

    # --- T22: las horas se limitan a 0–24 con los botones + y −
    def t22(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.pulsar('Mikel', 40, '0.5')
        ok(e.horas('Mikel') == '24 h', 'T22 tras muchos «+» las horas deben quedarse en 24 h: %r' % e.horas('Mikel'))
        e.pulsar('Mikel', 60, '-0.5')
        ok(e.horas('Mikel') == '0 h', 'T22 tras muchos «−» las horas deben quedarse en 0 h (nunca negativas): %r' % e.horas('Mikel'))
    con_escena('T22', ESTADO1, t22)

    # --- T23: sin localStorage (Safari en privado / cuota llena) la app sigue funcionando y NO dice que ha guardado
    def t23(e):
        e.ir()
        ok(e.pg.eval_on_selector_all('#obra option', 'e=>e.map(o=>o.value)') == ['olabeaga', 'mungia'], 'T23 sin localStorage la app debe cargar igualmente el estado publicado')
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        ok(e.marcados() == ['Mikel'], 'T23 se puede marcar sin localStorage')
        e.clic('button[data-guardar]')
        ok('no se pudo' in e.toast() and 'guardada en este aparato' not in e.toast(), 'T23 si no se puede escribir en el aparato, guardar debe avisarlo en vez de decir «guardada ✓»: %r' % e.toast())
    sin_ls = "(()=>{const f=()=>{throw new DOMException('cuota','QuotaExceededError')};Storage.prototype.setItem=f;Storage.prototype.getItem=f;Storage.prototype.removeItem=f})()"
    con_escena('T23', ESTADO1, t23, init=sin_ls)

    # --- T24: todo lo que viene de los datos se escapa (nombres y obras con comillas, < y &). Ojo: el informe lleva <b> e <i> legítimos
    #     (porcentaje y barra), así que solo se cuentan los elementos que habría creado el texto inyectado.
    raro = 'O\'Brien "el Rubio" <b>x</b> & Co'

    def t24(e):
        e.ir()
        e.fecha('2026-10-22')
        ok(raro in e.filas(), 'T24 el nombre raro debe salir tal cual en la lista: %s' % e.filas())
        ok(e.pg.evaluate("document.querySelectorAll('#v-app .nm *').length") == 0, 'T24 no debe interpretarse HTML dentro de los nombres de la lista')
        ok(e.pg.eval_on_selector_all('#obra option', 'e=>e.map(o=>o.textContent)')[0] == '2026 <i>OLA</i> & "X"', 'T24 el nombre de la obra se escapa en #obra')
        ok(e.pg.evaluate("document.querySelectorAll('#obra option *').length") == 0, 'T24 no debe haber elementos dentro de las opciones de #obra')
        e.clic('button[data-v="jornadas"]')
        ok(e.pg.eval_on_selector_all('#v-jornadas option', 'e=>e.map(o=>o.textContent)')[0] == '2026 <i>OLA</i> & "X"' and e.pg.evaluate("document.querySelectorAll('#v-jornadas option *').length") == 0, 'T24 el nombre de la obra se escapa en Jornadas')
        e.clic('button[data-v="informe"]')
        fi = e.informe()
        ok(any(f.startswith(raro) for f in fi), 'T24 el nombre raro sale entero en la tabla del informe: %s' % fi)
        ok(e.pg.evaluate("document.querySelectorAll('#v-informe td:first-child *, #v-informe .impacto span *').length") == 0, 'T24 no debe interpretarse HTML dentro de los nombres del informe')
        ok(e.pg.evaluate("[...document.querySelectorAll('#v-informe b')].filter(b=>b.textContent.trim()==='x').length") == 0, 'T24 no debe haber un <b>x</b> nacido del nombre')
        ok(e.pg.evaluate("document.querySelectorAll('#v-informe .ib i').length") == len(fi), 'T24 una barra de impacto por trabajador (las barras llevan su <i> legítimo)')
    s24 = estado_con({'olabeaga': obra_est('2026 <i>OLA</i> & "X"', [fila('2026-10-22', 'vivienda', raro, 7.5), fila('2026-10-22', 'vivienda', 'Mikel', 7.5)],
                                           ultima={'vivienda': {'fecha': '2026-10-22', 'presentes': pres(raro, 'Mikel')}, 'garaje': None})}, ['Mikel', raro])
    con_escena('T24', s24, t24)

    # --- T25: el horario cambiado deja de recordarse cuando el estado publicado ya lo trae
    def t25(e):
        e.ir()
        e.clic('details#horario summary')
        e.pg.fill('input[data-hor="5"]', '6')
        e.pg.dispatch_event('input[data-hor="5"]', 'change')
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        e.sin_previa()      # 08d: al recargar, el día nuevo vuelve a salir con la gente anterior marcada; T25 no trata de eso
        ok(e.pg.evaluate("localStorage.getItem('sgd_personal_horarios')") in ('{}', None), 'T25 el horario guardado en el aparato debe olvidarse cuando coincide con el publicado: %r' % e.pg.evaluate("localStorage.getItem('sgd_personal_horarios')"))
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        lote = e.exportar()
        ok(lote is not None and 'horario_semanal' not in lote, 'T25 un horario ya publicado no debe exportarse otra vez: %s' % (lote or {}).get('horario_semanal'))
    con_escena('T25', estado_con({'olabeaga': obra_est('2026 OLABEAGA', [fila('2026-10-22', 'vivienda', 'Mikel', 7.5)], horario=dict(H, vie=6),
                                                      ultima={'vivienda': {'fecha': '2026-10-22', 'presentes': pres('Mikel')}, 'garaje': None})}, ['Mikel']), t25)

    # --- T26: «hoy» es la fecha LOCAL (a las 00:30 del sábado en Madrid todavía es viernes en UTC)
    def t26(e):
        e.ir()
        ok(e.valor('#fecha') == '2026-10-24', 'T26 a las 00:30 locales del 24/10 la fecha de hoy debe ser 2026-10-24 (no la UTC): %r' % e.valor('#fecha'))
        ok('on' in (e.pg.get_attribute('button[data-dia="0"]', 'class') or ''), 'T26 el botón «Hoy» debe estar activo')
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        ok(e.txt('#v-app .row[data-nombre="Mikel"] .step output') == '¿horas?', 'T26 el 24/10 es sábado: sin horario')
    con_escena('T26', ESTADO1, t26, hoy='2026-10-24T00:30:00+02:00')

    # --- T27: «Empezar de cero» borra el borrador y recarga, pero NO las jornadas pendientes
    def t27(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        e.clic('#v-app .row[data-nombre="Rafa"] .x')
        ok(e.pg.evaluate("localStorage.getItem('sgd_personal_borrador')") is not None, 'T27 debe haber borrador antes de empezar de cero')
        e.clic('button[data-reset]')
        e.clic('button[data-reset-si]')     # paso 01b: «Empezar de cero» pregunta antes de borrar
        e.pg.wait_for_selector('#obra')
        e.pg.wait_for_timeout(300)
        ok(e.pg.evaluate("localStorage.getItem('sgd_personal_borrador')") is None or 'Rafa' not in e.marcados(), 'T27 «Empezar de cero» debe olvidar el borrador')
        ok('Rafa' not in e.marcados(), 'T27 tras empezar de cero no queda marcado lo del borrador: %s' % e.marcados())
        ok(e.pendientes() == '1', 'T27 empezar de cero no borra las jornadas pendientes: %r' % e.pendientes())
    con_escena('T27', ESTADO1, t27)

    # --- T28/T29: guardar sin nadie, guardar dos veces el mismo día, mismo día en dos ámbitos
    def t28(e):
        e.ir()
        e.clic('button[data-guardar]')
        ok('ninguna persona' in e.toast() and e.pendientes() == '0', 'T28 guardar sin presentes avisa y no guarda: %r %r' % (e.toast(), e.pendientes()))
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        e.clic('#v-app .row[data-nombre="Rafa"] .x')
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '1', 'T29 guardar dos veces el mismo día sustituye, no duplica: %r' % e.pendientes())
        e.clic('button[data-amb="garaje"]')
        e.clic('#v-app .row[data-nombre="Andoni"] .x')
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '2', 'T29 vivienda y garaje del mismo día son jornadas distintas: %r' % e.pendientes())
        lote = e.exportar() or {}
        ok(sorted((j['ambito'], [p['nombre'] for p in j['presentes']]) for j in lote.get('jornadas', [])) == [('garaje', ['Andoni']), ('vivienda', ['Mikel', 'Rafa'])], 'T29 lote con las dos jornadas: %s' % lote.get('jornadas'))
        ok('con 2 jornadas' in e.listo() and e.descarga == 'CONTROL HORARIO 2026 OLABEAGA BILBAO 23102026.json', 'T29 (08d) preparar el fichero deja a la vista el recuadro «Listo» con su nombre y las 2 jornadas, y el fichero se llama así: %r %r' % (e.listo(), e.descarga))
    con_escena('T28', ESTADO1, t28)

    # --- T30/T31: «Marcar todos» + guardar fija el horario del día; bajar de horario no genera extra negativa
    def t30(e):
        e.ir()
        e.clic('button[data-todos="1"]')
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        js = lote.get('jornadas', [])
        ok(js and len(js[0]['presentes']) == 3 and all(p['horas'] == 7.5 and p['extra'] == 0 for p in js[0]['presentes']), 'T30 «Marcar todos» + guardar debe guardar el horario del día (7,5 h) para todos: %s' % js)
        valida_con_p1(lote)
        e.fecha('2026-10-22')
        e.clic('#v-app .row[data-nombre="Mikel"] .step button[data-d="-0.5"]')
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        mk = [p for j in lote.get('jornadas', []) if j['fecha'] == '2026-10-22' for p in j['presentes'] if p['nombre'] == 'Mikel']
        ok(mk and mk[0]['horas'] == 7 and mk[0]['extra'] == 0, 'T31 bajar a 7 h un día de 7,5 h: extra 0 (nunca negativa): %s' % mk)
        valida_con_p1(lote)
    con_escena('T30', ESTADO1, t30)

    # --- T32: el informe navega bien entre periodos (‹ va hacia atrás) y dice qué periodo es
    def t32(e):
        e.ir()
        e.clic('button[data-v="informe"]')
        ok('octubre' in e.txt('#periodo').lower() and '2026' in e.txt('#periodo'), 'T32 el informe debe decir qué periodo muestra (octubre 2026): %r' % e.txt('#periodo'))
        e.clic('#v-informe button[data-m="-1"]')
        fi = e.informe()
        ok('septiembre' in e.txt('#periodo').lower() and [f.split(' ')[0] for f in fi] == ['Josu'] and '22,5' in fila_de(fi, 'Josu') and '100' in fila_de(fi, 'Josu'), 'T32 ‹ lleva a septiembre: Josu 22,5 h al 100 %%: %s %r' % (fi, e.txt('#periodo')))
        e.clic('#v-informe button[data-m="1"]')
        ok('octubre' in e.txt('#periodo').lower(), 'T32 › vuelve a octubre')
        e.clic('#v-informe button[data-p="anio"]')
        ok('2026' in e.txt('#periodo') and 'octubre' not in e.txt('#periodo').lower(), 'T32 periodo año: %r' % e.txt('#periodo'))
        e.clic('#v-informe button[data-p="obra"]')
        ok('obra' in e.txt('#periodo').lower(), 'T32 periodo obra completa: %r' % e.txt('#periodo'))
        e.clic('#v-informe button[data-p="semana"]')
        per = e.txt('#periodo').lower()
        ok('19' in per and '25' in per and 'oct' in per and '2026' in per, 'T32 la semana del 23/10/2026 va del lunes 19 al domingo 25 de octubre: %r' % per)
        e.clic('#v-informe button[data-m="-1"]')
        per = e.txt('#periodo').lower()
        ok('12' in per and '18' in per and '19' not in per, 'T32 semana anterior: del 12 al 18 de octubre: %r' % per)
    con_escena('T32', ESTADO1, t32)

    # --- T33: se exportan solo los pendientes de la obra elegida; los de otra obra siguen ahí
    def t33(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        e.obra('mungia')
        e.clic('#v-app .row[data-nombre="Pepe"] .x')
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '2', 'T33 dos pendientes (uno por obra): %r' % e.pendientes())
        lm = e.exportar() or {}
        ok(lm.get('obra') == 'mungia' and [p['nombre'] for j in lm.get('jornadas', []) for p in j['presentes']] == ['Pepe'], 'T33 el lote de Mungia solo lleva lo de Mungia: %s' % lm)
        e.obra('olabeaga')
        lo = e.exportar() or {}
        ok(lo.get('obra') == 'olabeaga' and [p['nombre'] for j in lo.get('jornadas', []) for p in j['presentes']] == ['Mikel'], 'T33 el lote de Olabeaga solo lleva lo de Olabeaga: %s' % lo)
    con_escena('T33', ESTADO1, t33)

    # --- T34: exportar sin nada que exportar no descarga un lote vacío
    def t34(e):
        e.ir()
        lote = e.exportar(esperar=False)
        ok(lote is None, 'T34 sin pendientes ni horario cambiado no debe descargarse un lote vacío: %s' % lote)
        ok('no hay nada por enviar' in e.enviar_txt('#nada-que-enviar').lower(), 'T34 (08d) la pantalla «Enviar al PC» debe decir «No hay nada por enviar»: %r' % e.enviar_txt('#nada-que-enviar'))
    con_escena('T34', ESTADO1, t34)

    # --- T35: borrador y pendientes corruptos o de otra versión: se ignoran, la app arranca
    def sembrar(clave, valor):
        return "if(!localStorage.getItem('_s')){localStorage.setItem('_s','1');localStorage.setItem('%s',%s)}" % (clave, json.dumps(json.dumps(valor)))

    def t35(e):
        e.ir()
        ok(e.valor('#fecha') == '2026-10-23' and e.marcados() == [], 'T35 un borrador no válido se ignora (fecha %r, marcados %s)' % (e.valor('#fecha'), e.marcados()))
        ok(e.pg.query_selector('#obra') is not None, 'T35 la app debe arrancar con un borrador no válido')
    base_b = {'obra': 'olabeaga', 'ambito': 'vivienda', 'fecha': '2026-10-01', 'lista': [{'nombre': 'Mikel', 'on': True, 'horas': 7.5}]}
    for tag, bor in (('de una obra cerrada', dict(base_b, obra='vieja')), ('de una obra que no existe', dict(base_b, obra='nada')), ('con ámbito inválido', dict(base_b, ambito='otro')),
                     ('con fecha no fecha', dict(base_b, fecha='hoy')), ('con fecha imposible', dict(base_b, fecha='2026-02-30')),
                     ('con la lista llena de nulos', dict(base_b, lista=[None])), ('con filas sin forma', dict(base_b, lista=[{'x': 1}, 7]))):
        con_escena('T35 borrador ' + tag, ESTADO1, t35, init=sembrar('sgd_personal_borrador', bor))

    def t35b(e):
        e.ir()
        ok(e.pg.query_selector('#obra') is not None, 'T35b la app debe arrancar con pendientes corruptos')
        ok(e.pendientes() == '1', 'T35b se quedan solo los pendientes con forma válida (1 de 4): %r' % e.pendientes())
        ok('apartad' in e.toast(), 'T35b los pendientes rotos no se pierden en silencio: debe avisar de que se apartan: %r' % e.toast())
    pend_mal = [None, 5, {'obra': 'olabeaga'}, {'obra': 'olabeaga', 'ambito': 'vivienda', 'fecha': '2026-10-22', 'presentes': [{'nombre': 'Mikel', 'horas': 7.5, 'extra': 0}], 'anulada': False, 'notas': '', 'registrado': '2026-10-22T10:00:00.000Z'}]
    con_escena('T35b', ESTADO1, t35b, init=sembrar('sgd_personal_pendientes', pend_mal))

    # --- T36: 12 h / 24 h por persona y día, sumando TODAS las obras y ámbitos (propuesta D)
    def t36(e):
        e.ir()
        e.fecha('2026-10-21')           # miércoles; Mikel ya tiene 7,5 h publicadas en Olabeaga
        e.obra('mungia')
        e.anotar('Mikel')
        e.pulsar('Mikel', 19, '0.5')    # 7,5 + 9,5 = 17 h; con las 7,5 de Olabeaga serían 24,5
        ok(e.horas('Mikel') == '17 h', 'T36 preparación: 17 h: %r' % e.horas('Mikel'))
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '0' and 'no se guarda' in e.toast() and '24' in e.toast(), 'T36 más de 24 h en el día (con otras obras) no se guarda: %r %r' % (e.toast(), e.pendientes()))
        e.pulsar('Mikel', 10, '-0.5')   # 12 h + 7,5 = 19,5
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '1' and 'aviso' in e.toast() and '19,5' in e.toast(), 'T36 más de 12 h en el día guarda pero avisa con el total (19,5 h): %r %r' % (e.toast(), e.pendientes()))
        e.pulsar('Mikel', 16, '-0.5')   # 4 h + 7,5 = 11,5: ya no avisa, y no cuenta dos veces su propia jornada
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '1' and 'aviso' not in e.toast() and 'guardada' in e.toast(), 'T36 al sustituir la jornada no se suma a sí misma (11,5 h): %r %r' % (e.toast(), e.pendientes()))
    con_escena('T36', ESTADO1, t36)

    def t36b(e):
        e.ir()
        e.fecha('2026-10-21')           # Olabeaga, viviendas, ya publicada con Mikel 7,5 h y Txomin 7,5 h
        e.pulsar('Mikel', 8, '0.5')     # 11,5 h: si se sumara con su propia fila publicada (7,5) saldría 19
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '1' and 'aviso' not in e.toast(), 'T36b corregir una jornada publicada no suma las horas viejas de esa misma jornada: %r %r' % (e.toast(), e.pendientes()))
    con_escena('T36b', ESTADO1, t36b)

    # --- T37: horario y horas con decimales de más no pueden romper el lote (P1 rechaza más de 2 decimales)
    def t37(e):
        e.ir()
        e.clic('details#horario summary')
        e.pg.fill('input[data-hor="5"]', '7.333')
        e.pg.dispatch_event('input[data-hor="5"]', 'change')
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.pulsar('Mikel', 5, '0.5')
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        hs = lote.get('horario_semanal', {})
        ok(hs.get('vie') == 7.33, 'T37 el horario se redondea a 2 decimales (7,333 → 7,33): %s' % hs)
        valida_con_p1(lote)
        mk = [p for j in lote.get('jornadas', []) for p in j['presentes'] if p['nombre'] == 'Mikel']
        ok(mk and round(mk[0]['horas'], 2) == mk[0]['horas'] and round(mk[0]['extra'], 2) == mk[0]['extra'], 'T37 horas y extra con 2 decimales como mucho: %s' % mk)
    con_escena('T37', ESTADO1, t37)

    def t37b(e):
        e.ir()
        e.clic('details#horario summary')
        e.pg.fill('input[data-hor="5"]', '7.3')
        e.pg.dispatch_event('input[data-hor="5"]', 'change')
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.pulsar('Mikel', 5, '0.5')     # 7,3 + 2,5 = 9,8 → extra 2,5 exacto
        e.clic('button[data-guardar]')
        mk = [p for j in (e.exportar() or {}).get('jornadas', []) for p in j['presentes'] if p['nombre'] == 'Mikel']
        ok(mk and mk[0]['horas'] == 9.8 and mk[0]['extra'] == 2.5, 'T37b sin ruido de coma flotante: 9,8 h con 2,5 extra: %s' % mk)
    con_escena('T37b', ESTADO1, t37b)

    # --- T38: una fecha vacía o rota no entra en la app
    def t38(e):
        e.ir()
        e.pg.evaluate("()=>{const e=document.getElementById('fecha');e.value='';e.dispatchEvent(new Event('change',{bubbles:true}))}")
        ok(e.valor('#fecha') == '2026-10-23', 'T38 si se vacía la fecha se mantiene la anterior (no se anota «sin fecha»): %r' % e.valor('#fecha'))
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        ok([j['fecha'] for j in lote.get('jornadas', [])] == ['2026-10-23'], 'T38 la jornada guardada lleva una fecha válida: %s' % lote.get('jornadas'))
    con_escena('T38', ESTADO1, t38)

    # --- T39: al abrir una jornada existente la lista es la de siempre (última + habituales + presentes), no todo el catálogo
    def t39(e):
        e.ir()
        e.fecha('2026-10-22')
        ok(sorted(e.filas()) == ['Mikel', 'Rafa', 'Txomin'] and sorted(e.marcados()) == ['Mikel', 'Txomin'], 'T39 al abrir el 22/10: presentes marcados + la lista habitual (sin Andoni, Josu ni Pepe): filas %s marcados %s' % (e.filas(), e.marcados()))
    con_escena('T39', ESTADO1, t39)

    # --- T40: legibilidad y pulsaciones: casilla vacía sin «X», toast que no tapa, estado sin ISO, resumen sin «0 h» inventado
    def t40(e):
        e.ir()
        col = e.pg.evaluate("(()=>{const x=document.querySelector('#v-app .row:not(.off) .x:not(.on)')||document.querySelector('#v-app .x:not(.on)');return getComputedStyle(x).color})()")
        ok(col in ('rgba(0, 0, 0, 0)', 'transparent'), 'T40 una casilla sin marcar no debe mostrar la «X» (si no, parece marcada): color %s' % col)
        ok(not re.search(r'T\d\d:\d\d', e.txt('#estado-origen')), 'T40 #estado-origen no debe enseñar la fecha en formato máquina: %r' % e.txt('#estado-origen'))
        ok(e.pg.evaluate("getComputedStyle(document.querySelector('#toast')).pointerEvents") == 'none', 'T40 el aviso (#toast) no debe interceptar pulsaciones cuando está invisible')
        e.fecha('2026-10-24')
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        s = e.txt('.sum')
        ok('faltan horas' in s.lower() and '0 h' not in s and '1 presente ' in s + ' ', 'T40 con horas sin poner el resumen no debe decir «0 h» y debe hablar en singular: %r' % s)
        ok(e.pg.query_selector('#v-app .row[data-nombre="Mikel"] .step output.falta') is not None, 'T40 sigue la marca ¿horas?')
    con_escena('T40', ESTADO1, t40)

    # --- T41: con un nombre muy largo la tabla del informe sigue mostrando sus columnas en el móvil
    def t41(e):
        e.ir()
        e.clic('button[data-v="informe"]')
        m = e.pg.evaluate("(()=>{const w=document.querySelector('#v-informe .wrapx');return [w.scrollWidth,w.clientWidth]})()")
        ok(m[0] <= m[1] + 1, 'T41 la tabla del informe no debe necesitar desplazamiento lateral con un nombre largo a 390 px: ancho %d en %d' % tuple(m))
    nlargo = 'José Antonio Fernández de la Torre y Arrieta'
    con_escena('T41', estado_con({'olabeaga': obra_est('2026 OLABEAGA', [fila('2026-10-22', 'vivienda', nlargo, 7.5), fila('2026-10-22', 'vivienda', 'Mikel', 7.5)])}, ['Mikel', nlargo]), t41)

    # --- T42: tras cambiar el horario de hoy las cifras de la pantalla se actualizan al momento y el aviso sigue visible
    def t42(e):
        e.ir()
        e.clic('button[data-todos="1"]')
        e.clic('details#horario summary')
        e.pg.fill('input[data-hor="5"]', '8')
        e.pg.dispatch_event('input[data-hor="5"]', 'change')
        e.pg.wait_for_timeout(100)
        ok(e.horas('Mikel') == '8 h', 'T42 al cambiar el horario del viernes a 8 h, quien tiene «el horario del día» debe verse con 8 h al instante: %r' % e.horas('Mikel'))
        ok(e.pg.is_visible('#aviso-horario') and 'no modifica' in e.txt('#aviso-horario').lower(), 'T42 el aviso del horario sigue visible y el desplegable abierto tras repintar')
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        mk = [p for j in lote.get('jornadas', []) for p in j['presentes'] if p['nombre'] == 'Mikel']
        ok(mk and mk[0]['horas'] == 8 and mk[0]['extra'] == 0 and lote.get('horario_semanal', {}).get('vie') == 8, 'T42 se guarda con el horario nuevo (8 h, sin extra) y el lote lleva el horario: %s %s' % (mk, lote.get('horario_semanal')))
    con_escena('T42', ESTADO1, t42)

    # --- T43: sin red y con la copia local usa la copia; y la lista y las jornadas del aparato se conservan entre aperturas
    def t43(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        os.remove(os.path.join(e.dir, 'personal_estado.js'))
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        ok('guardada' in e.txt('#estado-origen').lower() and e.pendientes() == '1', 'T43 sin red usa la lista guardada y conserva la jornada sin enviar: %r %r' % (e.txt('#estado-origen'), e.pendientes()))
    con_escena('T43', ESTADO1, t43)

    # ======================================================================================================================
    # Bloque 2 del paso 01: pruebas añadidas para matar mutantes que sobrevivieron o que nacieron con el código consolidado.
    # ======================================================================================================================

    # --- T44: reabrir una jornada anulada no cuenta la jornada anulada para los habituales (solo días ANTERIORES a la fecha)
    def t44(e):
        e.ir()
        e.clic('button[data-v="jornadas"]')
        e.clic('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-14"] button[data-anular]')
        e.clic('#confirmar button[data-confirmar="si"]')
        e.clic('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-14"] button[data-abrir]')
        ok(e.valor('#fecha') == '2026-10-14', 'T44 abrir la jornada del 14/10: %r' % e.valor('#fecha'))
        ok(e.filas() == ['Mikel'] and e.marcados() == [], 'T44 la lista del 14/10 es la última jornada (Mikel); Zeta solo tenía 2 días antes (el 12 y el 13) y el propio 14 no cuenta: %s' % e.filas())
    f44 = [fila(f, 'vivienda', 'Zeta', 7.5) for f in ('2026-10-12', '2026-10-13', '2026-10-14')]
    con_escena('T44', estado_con({'olabeaga': obra_est('2026 OLABEAGA', f44, ultima={'vivienda': {'fecha': '2026-10-22', 'presentes': pres('Mikel')}, 'garaje': None})}, ['Mikel', 'Zeta']), t44)

    # --- T45: límites exactos del aviso (> 12 h) y del rechazo (> 24 h) por persona y día
    def t45(e):
        e.ir()
        e.fecha('2026-10-21')           # Mikel ya tiene 7,5 h publicadas en Olabeaga ese día
        e.obra('mungia')
        e.anotar('Mikel')
        e.pulsar('Mikel', 6, '-0.5')    # 4,5 h: total exacto 12 h → sin aviso
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '1' and 'aviso' not in e.toast() and 'guardada' in e.toast(), 'T45 12 h exactas no avisan: %r %r' % (e.toast(), e.pendientes()))
        e.pulsar('Mikel', 1, '0.5')     # 5 h: total 12,5 h → aviso
        e.clic('button[data-guardar]')
        ok('aviso' in e.toast() and '12,5' in e.toast(), 'T45 12,5 h avisan con el total: %r' % e.toast())
        e.pulsar('Mikel', 23, '0.5')    # 16,5 h: total exacto 24 h → se guarda (con aviso)
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '1' and 'aviso' in e.toast() and 'no se guarda' not in e.toast(), 'T45 24 h exactas se guardan con aviso: %r %r' % (e.toast(), e.pendientes()))
        e.pulsar('Mikel', 1, '0.5')     # 17 h: total 24,5 h → no se guarda
        e.clic('button[data-guardar]')
        ok('no se guarda' in e.toast(), 'T45 24,5 h no se guardan: %r' % e.toast())
    con_escena('T45', ESTADO1, t45)

    # --- T46: una anulación pendiente en otra obra libera las horas de ese día (la pendiente manda sobre la publicada)
    def t46(e):
        e.ir()
        e.clic('button[data-v="jornadas"]')
        e.clic('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-21"] button[data-anular]')
        e.clic('#confirmar button[data-confirmar="si"]')
        e.clic('button[data-v="app"]')
        e.fecha('2026-10-21')
        e.obra('mungia')
        e.anotar('Mikel')
        e.pulsar('Mikel', 30, '0.5')    # 22,5 h; las 7,5 h de Olabeaga están anuladas (pendiente), así que el total del día es 22,5
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '2' and 'no se guarda' not in e.toast(), 'T46 con la jornada de Olabeaga anulada, 22,5 h en Mungia caben en el día: %r %r' % (e.toast(), e.pendientes()))
    con_escena('T46', ESTADO1, t46)

    # --- T47: Jornadas: título con día de la semana, una sola confirmación, la anulada pierde «Anular»
    def t47(e):
        e.ir()
        e.clic('button[data-v="jornadas"]')
        it = '#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-12"]'
        ok(e.txt(it + ' h3') == 'lun 12/10 · vivienda', 'T47 título de la jornada: %r' % e.txt(it + ' h3'))
        e.clic(it + ' button[data-anular]')
        ok(e.pg.evaluate("document.querySelectorAll('#confirmar').length") == 1, 'T47 debe haber una sola confirmación abierta')
        ok(e.pg.evaluate("document.querySelector('#confirmar').closest('.jor-item').dataset.fecha") == '2026-10-12', 'T47 la confirmación está dentro de la jornada pulsada')
        e.clic('#confirmar button[data-confirmar="si"]')
        ok(e.pg.evaluate("document.querySelectorAll('%s button[data-anular]').length" % it) == 0 and e.pg.evaluate("document.querySelectorAll('%s button[data-abrir]').length" % it) == 1, 'T47 una jornada anulada solo lleva «Abrir»')
    con_escena('T47', ESTADO1, t47)

    def t47b(e):
        e.ir()
        e.clic('button[data-v="jornadas"]')
        e.clic('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-12"] button[data-anular]')
        ok(e.pg.evaluate("document.querySelectorAll('#confirmar').length") == 1 and e.pg.evaluate("document.querySelector('#confirmar').closest('.jor-item').dataset.ambito") == 'vivienda', 'T47b vivienda y garaje del mismo día: la confirmación solo sale en la pulsada')
        ok(e.pg.evaluate("document.querySelectorAll('#v-jornadas .jor-item[data-ambito=\"garaje\"] button[data-anular]').length") == 1, 'T47b el garaje del mismo día conserva su botón Anular')
    f47 = [fila('2026-10-12', 'vivienda', 'Mikel', 7.5), fila('2026-10-12', 'garaje', 'Andoni', 7.5)]
    con_escena('T47b', estado_con({'olabeaga': obra_est('2026 OLABEAGA', f47)}, ['Mikel', 'Andoni']), t47b)

    # --- T48: singular en Jornadas y en el resumen; fecha del estado legible; el resumen se repinta al cambiar el horario
    def t48(e):
        e.ir()
        ok(e.txt('#estado-origen') == 'Lista de trabajadores y obras al día: 23/10/2026 08:00', 'T48 #estado-origen: %r' % e.txt('#estado-origen'))
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        ok(e.txt('.sum') == '1 presente · 7,5 h', 'T48 resumen con una persona: %r' % e.txt('.sum'))
        e.clic('button[data-v="jornadas"]')
        ok('1 presente ·' in e.txt('#v-jornadas .jor-item[data-fecha="2026-10-10"]') and '1 presentes' not in e.txt('#v-jornadas'), 'T48 Jornadas: «1 presente», no «1 presentes»: %r' % e.txt('#v-jornadas .jor-item[data-fecha="2026-10-10"]'))
    con_escena('T48', ESTADO1, t48)

    def t48b(e):
        e.ir()
        e.clic('button[data-todos="1"]')        # nadie tiene las horas fijadas: todos siguen «el horario del día»
        e.clic('details#horario summary')
        e.pg.fill('input[data-hor="5"]', '8')
        e.pg.dispatch_event('input[data-hor="5"]', 'change')
        ok(e.txt('.sum') == '3 presentes · 24 h', 'T48b el resumen se repinta al cambiar el horario (3 × 8 h): %r' % e.txt('.sum'))
    con_escena('T48b', ESTADO1, t48b)

    # --- T49: los pendientes que se apartan por estar dañados se guardan aparte (no se pierden)
    def t49(e):
        e.ir()
        rotos = e.pg.evaluate("JSON.parse(localStorage.getItem('sgd_personal_rotos') || 'null')")
        ok(isinstance(rotos, list) and len(rotos) == 3, 'T49 los 3 pendientes dañados deben guardarse en sgd_personal_rotos: %s' % rotos)
        ok(e.pendientes() == '1', 'T49 queda 1 pendiente válido: %r' % e.pendientes())
    con_escena('T49', ESTADO1, t49, init=sembrar('sgd_personal_pendientes', pend_mal))

    # --- T50: anular una jornada que ya estaba pendiente la sustituye (si no, el lote llevaría dos con la misma clave y el PC rechazaría las dos)
    def t50(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        e.clic('button[data-v="jornadas"]')
        e.clic('#v-jornadas .jor-item[data-ambito="vivienda"][data-fecha="2026-10-23"] button[data-anular]')
        e.clic('#confirmar button[data-confirmar="si"]')
        n = e.pg.evaluate("JSON.parse(localStorage.getItem('sgd_personal_pendientes')).length")
        ok(n == 1, 'T50 anular una jornada pendiente la sustituye, no se acumula: %s pendientes guardados' % n)
        lote = e.exportar() or {}
        ok(len(lote.get('jornadas', [])) == 1 and lote['jornadas'][0]['anulada'] is True and lote['jornadas'][0]['presentes'] == [], 'T50 el lote lleva una sola jornada anulada: %s' % lote.get('jornadas'))
        valida_con_p1(lote)
    con_escena('T50', ESTADO1, t50)

    # --- T51: «inaki» es «Iñaki» (la clave de nombre quita tildes y la eñe de combinación: mismas reglas que el PC)
    def t51(e):
        e.ir()
        e.pg.fill('#nuevo', ' INAKI ')
        e.clic('button[data-nuevo]')
        ok(e.filas().count('Iñaki') == 1 and 'Iñaki' in e.marcados() and not any(n.lower() == 'inaki' for n in e.filas()), 'T51 «INAKI» debe usar al «Iñaki» del catálogo, sin duplicarlo ni preguntar: %s %r' % (e.filas(), e.txt('#nuevo-aviso')))
    con_escena('T51', estado_con({'olabeaga': obra_est('2026 OLABEAGA', [])}, ['Iñaki', 'Mikel']), t51)

    # --- T18b: «Mikal» no contiene a «Mikel» pero dista 1 (una letra cambiada): también avisa (la regla de contención no basta)
    def t18b(e):
        e.ir()
        e.pg.fill('#nuevo', 'Mikal')
        e.clic('button[data-nuevo]')
        ok('Se parece a «Mikel»' in e.txt('#nuevo-aviso'), 'T18b «Mikal» dista 1 de «Mikel» sin contenerlo: debe avisar: %r' % e.txt('#nuevo-aviso'))
    con_escena('T18b', ESTADO1, t18b)

    # --- T25b: un horario cambiado en el aparato se olvida cuando el estado publicado ya trae ese mismo horario
    def t25b(e):
        e.ir()
        e.clic('details#horario summary')
        e.pg.fill('input[data-hor="5"]', '6')
        e.pg.dispatch_event('input[data-hor="5"]', 'change')
        guardado = e.pg.evaluate("localStorage.getItem('sgd_personal_horarios')")
        ok(guardado and '"olabeaga"' in guardado, 'T25b preparación: el horario cambiado se recuerda en el aparato: %r' % guardado)
        nuevo_estado = estado_con({'olabeaga': obra_est('2026 OLABEAGA', [], horario=dict(H, vie=6))}, ['Mikel'])
        with open(os.path.join(e.dir, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
            fh.write('window.SAGARDE_PERSONAL = ' + json.dumps(nuevo_estado, ensure_ascii=False) + ';\n')
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        despues = e.pg.evaluate("localStorage.getItem('sgd_personal_horarios')")
        ok(despues in ('{}', None), 'T25b cuando el estado publicado trae el horario nuevo, el del aparato se olvida: %r' % despues)
        ok(e.pg.input_value('input[data-hor="5"]') == '6', 'T25b y el campo del viernes sigue mostrando 6')
    con_escena('T25b', estado_con({'olabeaga': obra_est('2026 OLABEAGA', [])}, ['Mikel']), t25b)

    # --- T41b: lo mismo que T41 en un móvil estrecho (320 px)
    def t41b(e):
        e.ir()
        e.clic('button[data-v="informe"]')
        m = e.pg.evaluate("(()=>{const w=document.querySelector('#v-informe .wrapx');return [w.scrollWidth,w.clientWidth,document.documentElement.scrollWidth]})()")
        ok(m[0] <= m[1] + 1 and m[2] <= 321, 'T41b a 320 px la tabla del informe no debe desbordar: tabla %d en %d, página %d' % tuple(m))
    con_escena('T41b', estado_con({'olabeaga': obra_est('2026 OLABEAGA', [fila('2026-10-22', 'vivienda', nlargo, 7.5), fila('2026-10-22', 'vivienda', 'Mikel', 7.5)])}, ['Mikel', nlargo]), t41b, ancho=320, alto=640)

    # ======================================================================================================================
    # Bloque 3 (paso 01b): horario propio por trabajador, el cambio de horario del día arrastra a quien lo sigue, espera máxima de
    # 4 s al estado publicado y «Empezar de cero» con pregunta. Grupo A = lógica (se prueba con estados publicados y con la función
    # global guardarPropio(nombre, objeto)); grupo B = pantalla del horario propio y la pregunta de «Empezar de cero».
    # Con P3_GRUPO=A se omite el grupo B (primera tanda de trabajo: todavía no hay pantalla).
    # ======================================================================================================================
    import hashlib
    GRUPO_B = os.environ.get('P3_GRUPO', '') != 'A'
    CINCO = ['Mikel', 'Txomin', 'Rafa', 'Aitor', 'Gorka']
    PROPIOS = {'Aitor': {'vie': 9}, 'Gorka': {'vie': 9}}
    H_9 = {'Mikel': '7,5 h', 'Txomin': '7,5 h', 'Rafa': '7,5 h', 'Aitor': '9 h', 'Gorka': '9 h'}

    def est5(excep=None, horario=None):
        return estado_con({'olabeaga': obra_est('2026 OLABEAGA', [], horario=horario, excep=excep,
                                                ultima={'vivienda': {'fecha': '2026-10-22', 'presentes': pres(*CINCO)}, 'garaje': None}),
                           'mungia': obra_est('2026 MUNGIA', [], ultima={'vivienda': {'fecha': '2026-10-21', 'presentes': pres('Pepe')}, 'garaje': None})},
                          CINCO + ['Pepe'])

    def marcar_los_cinco(e):
        for n in CINCO:
            e.clic('#v-app .row[data-nombre="%s"] .x' % n)

    def horas5(e):
        return {n: e.horas(n) for n in CINCO}

    def chip(e, n, propio=False):
        return e.txt('#v-app .row[data-nombre="%s"] .chip%s' % (n, '.propio' if propio else ':not(.propio)'))

    def propio_ls(e):
        return e.pg.evaluate("localStorage.getItem('sgd_personal_excepciones')")

    def guardar_propio(e, nombre, obj):
        return e.pg.evaluate("([n,o])=>guardarPropio(n,o)", [nombre, obj])

    def cambia_horario(e, indice, valor):
        e.pg.evaluate("document.getElementById('horario').open=true")
        e.pg.fill('input[data-hor="%d"]' % indice, str(valor))
        e.pg.dispatch_event('input[data-hor="%d"]' % indice, 'change')

    def tokens(filas, nombre):
        return fila_de(filas, nombre).split(' ')

    def hash_dir(d):
        out = {}
        for r, _, fs in os.walk(d):
            for f in fs:
                with open(os.path.join(r, f), 'rb') as fh:
                    out[os.path.relpath(os.path.join(r, f), d)] = hashlib.sha256(fh.read()).hexdigest()
        return out

    # --- T52: el ejemplo de Bixente con el horario propio ya publicado: viernes de 7,5 h y dos autónomos a 9 h
    def t52(e):
        e.ir()
        marcar_los_cinco(e)
        ok(horas5(e) == H_9, 'T52 viernes con los 5 marcados: los de horario propio salen a 9 h, los demás a 7,5 h: %s' % horas5(e))
        ok(e.txt('.sum') == '5 presentes · 40,5 h', 'T52 el resumen no habla de «extra» (los 9 h son normales): %r' % e.txt('.sum'))
        ok(all(chip(e, n) == '' for n in CINCO), 'T52 nadie lleva chip de horas extra: %s' % [chip(e, n) for n in CINCO])
        ok(chip(e, 'Aitor', True) == 'horario especial 9 h' and chip(e, 'Gorka', True) == 'horario especial 9 h', 'T52 quien tiene horario especial lleva el chip «horario especial 9 h»: %r %r' % (chip(e, 'Aitor', True), chip(e, 'Gorka', True)))
        ok(chip(e, 'Mikel', True) == '' and chip(e, 'Rafa', True) == '' and chip(e, 'Txomin', True) == '', 'T52 los demás no llevan el chip de horario propio')
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        ps = {p['nombre']: (p['horas'], p.get('extra', 0)) for j in lote.get('jornadas', []) for p in j['presentes']}
        ok(ps == {'Mikel': (7.5, 0), 'Txomin': (7.5, 0), 'Rafa': (7.5, 0), 'Aitor': (9, 0), 'Gorka': (9, 0)}, 'T52 lote: horas y extra por persona (los 9 h de un autónomo son normales): %s' % ps)
        ok('excepciones_horario' not in lote, 'T52 un horario propio que ya está publicado no se exporta otra vez: %s' % lote.get('excepciones_horario'))
        valida_con_p1(lote)
        e.clic('button[data-v="informe"]')
        fi = e.informe()
        ok(tokens(fi, 'Aitor') == ['Aitor', '1', '9', '0', '9', '22,2', '%'], 'T52 informe de Aitor (9 ordinarias, 0 extra, 22,2 %%): %r' % fila_de(fi, 'Aitor'))
        ok(tokens(fi, 'Mikel') == ['Mikel', '1', '7,5', '0', '7,5', '18,5', '%'], 'T52 informe de Mikel (7,5 h, 18,5 %%): %r' % fila_de(fi, 'Mikel'))
    con_escena('T52', est5(PROPIOS), t52)

    # --- T53: se fija el horario propio en la app, se recuerda, se exporta, el PC lo acepta, y al publicarse se olvida
    def t53(e):
        e.ir()
        ok(e.pg.evaluate("typeof guardarPropio") == 'function' and e.pg.evaluate("typeof horarioDe") == 'function', 'T53 deben existir las funciones globales guardarPropio(nombre, objeto) y horarioDe(nombre, fecha)')
        marcar_los_cinco(e)
        ok(e.txt('.sum') == '5 presentes · 37,5 h', 'T53 sin horarios propios: 5 × 7,5 h: %r' % e.txt('.sum'))
        guardar_propio(e, 'Aitor', {'vie': 9})
        guardar_propio(e, 'Gorka', {'vie': 9})
        ok(horas5(e) == H_9 and e.txt('.sum') == '5 presentes · 40,5 h', 'T53 al fijar el horario propio, quien seguía el horario del día pasa a 9 h: %s %r' % (horas5(e), e.txt('.sum')))
        ok(propio_ls(e) and json.loads(propio_ls(e)) == {'olabeaga': {'Aitor': {'vie': 9}, 'Gorka': {'vie': 9}}}, 'T53 el horario propio se recuerda en el aparato (sgd_personal_excepciones): %r' % propio_ls(e))
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        ok(horas5(e) == H_9, 'T53 tras recargar la app sigue recordando el horario propio: %s' % horas5(e))
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        ok(lote.get('excepciones_horario') == {'Aitor': {'vie': 9}, 'Gorka': {'vie': 9}}, 'T53 el lote lleva excepciones_horario por nombre, solo los que cambiaron: %s' % lote.get('excepciones_horario'))
        ok(set(lote) == {'tipo', 'version', 'obra', 'excepciones_horario', 'jornadas'}, 'T53 claves del lote: %s' % sorted(lote))
        valida_con_p1(lote)
        if P1 is None:
            return
        raiz = os.path.join(SANDBOX, 'p1_' + uuid.uuid4().hex[:6])
        os.makedirs(raiz)
        obras = {'olabeaga': '2026 OLABEAGA BILBAO'}
        r = P1.ingerir_lote(copy.deepcopy(lote), raiz, obras, '2026-10-23', escribir=True, ahora='2026-10-23T22:00:00+02:00')
        ok(r['ok'] and r['escrito'] and [x['accion'] for x in r['excepciones']] == ['fijada', 'fijada'], 'T53 el PC debe ingerir el lote de la app: %s' % json.dumps(r, ensure_ascii=False)[:400])
        antes = hash_dir(raiz)
        P1.ingerir_lote(copy.deepcopy(lote), raiz, obras, '2026-10-23', escribir=True, ahora='2026-10-23T22:30:00+02:00')
        ok(hash_dir(raiz) == antes, 'T53 reingerir el lote de la app no cambia ni un byte')
        texto = P1.exportar_estado(raiz, obras, nombres_obra={'olabeaga': '2026 OLABEAGA'}, generado='2026-10-23T23:00:00+02:00')
        datos = json.loads(texto[texto.index('{'):texto.rindex('}') + 1])
        ok(datos['obras']['olabeaga']['excepciones_horario'] == {'Aitor': {'vie': 9}, 'Gorka': {'vie': 9}}, 'T53 el estado regenerado trae el horario propio por nombre: %s' % datos['obras']['olabeaga']['excepciones_horario'])
        with open(os.path.join(e.dir, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
            fh.write(texto)
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        ok(propio_ls(e) in (None, '{}'), 'T53 cuando el estado publicado ya trae el horario propio, la app lo olvida: %r' % propio_ls(e))
        ok(e.exportar(esperar=False) is None and 'no hay nada por enviar' in e.enviar_txt('#nada-que-enviar').lower(), 'T53 (08d) recargada con el estado nuevo ya no queda nada por enviar: %r' % e.enviar_txt('#nada-que-enviar'))
        ok(e.horas('Aitor') == '9 h', 'T53 y Aitor sigue saliendo a 9 h (ahora por el estado publicado): %r' % e.horas('Aitor'))
    con_escena('T53', est5(), t53)

    # --- T54: Aitor a 10 h un viernes = 1 h extra (sobre SU horario de 9 h); el sábado sin horario de obra ni propio, «¿horas?» para todos
    def t54(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Aitor"] .x')
        e.pulsar('Aitor', 2, '0.5')
        ok(e.horas('Aitor') == '10 h' and chip(e, 'Aitor') == '+1 h extra', 'T54 10 h con horario propio de 9 h: 1 h extra: %r %r' % (e.horas('Aitor'), chip(e, 'Aitor')))
        ok(e.txt('.sum') == '1 presente · 10 h · 1 h extra', 'T54 resumen: %r' % e.txt('.sum'))
        e.clic('button[data-guardar]')
        a = [p for j in (e.exportar() or {}).get('jornadas', []) for p in j['presentes'] if p['nombre'] == 'Aitor']
        ok(a and a[0]['horas'] == 10 and a[0]['extra'] == 1, 'T54 lote: Aitor 10 h con 1 h extra: %s' % a)
        e.fecha('2026-10-24')
        e.clic('button[data-todos="1"]')
        faltan = e.pg.eval_on_selector_all('#v-app .row .step output.falta', 'e=>e.length')
        ok(faltan == 5 and 'faltan horas' in e.txt('.sum').lower(), 'T54 el sábado, sin horario de obra ni propio, «¿horas?» para los 5 (también Aitor): %s %r' % (faltan, e.txt('.sum')))
        e.clic('button[data-guardar]')
        ok('faltan' in e.toast() and 'aitor' in e.toast(), 'T54 sin horas no se guarda y el aviso nombra a Aitor: %r' % e.toast())
    con_escena('T54', est5(PROPIOS), t54)

    # --- T55: cambiar el horario de la obra del día anotado arrastra a quien lo seguía; a los de horario propio no se les toca
    def t55(e):
        e.ir()
        marcar_los_cinco(e)
        cambia_horario(e, 5, 8)
        ok(horas5(e) == {'Mikel': '8 h', 'Txomin': '8 h', 'Rafa': '8 h', 'Aitor': '9 h', 'Gorka': '9 h'}, 'T55 viernes de 7,5 a 8 h: los 3 sin horario propio pasan a 8 h y los 2 de 9 h siguen en 9 h: %s' % horas5(e))
        ok(e.txt('.sum') == '5 presentes · 42 h' and all(chip(e, n) == '' for n in CINCO), 'T55 resumen y sin extra: %r' % e.txt('.sum'))
        cambia_horario(e, 1, 6)
        ok(horas5(e) == {'Mikel': '8 h', 'Txomin': '8 h', 'Rafa': '8 h', 'Aitor': '9 h', 'Gorka': '9 h'}, 'T55 cambiar el horario del lunes estando en viernes no mueve a nadie: %s' % horas5(e))
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        ok(lote.get('horario_semanal') == dict(H, vie=8, lun=6), 'T55 el lote lleva el horario de la obra cambiado: %s' % lote.get('horario_semanal'))
        ps = {p['nombre']: (p['horas'], p.get('extra', 0)) for j in lote.get('jornadas', []) for p in j['presentes']}
        ok(ps == {'Mikel': (8, 0), 'Txomin': (8, 0), 'Rafa': (8, 0), 'Aitor': (9, 0), 'Gorka': (9, 0)}, 'T55 lote: %s' % ps)
        valida_con_p1(lote)
    con_escena('T55', est5(PROPIOS), t55)

    def t55b(e):
        e.ir()
        marcar_los_cinco(e)
        e.pulsar('Rafa', 2, '0.5')
        ok(e.horas('Rafa') == '8,5 h', 'T55b preparación: Rafa a 8,5 h puestas a mano: %r' % e.horas('Rafa'))
        cambia_horario(e, 5, 8)
        ok(horas5(e) == {'Mikel': '8 h', 'Txomin': '8 h', 'Rafa': '8,5 h', 'Aitor': '9 h', 'Gorka': '8 h'},
           'T55b las horas puestas a mano no se tocan, y quien solo tiene horario propio de OTRO día (Gorka: el lunes) sigue el horario de la obra: %s' % horas5(e))
        ok(chip(e, 'Rafa') == '+0,5 h extra', 'T55b Rafa lleva su media hora extra sobre las 8 h: %r' % chip(e, 'Rafa'))
        e.fecha('2026-10-19')
        e.clic('#v-app .row[data-nombre="Gorka"] .x')
        e.clic('#v-app .row[data-nombre="Aitor"] .x')
        ok(e.horas('Gorka') == '8 h' and chip(e, 'Gorka', True) == 'horario especial 8 h', 'T55b el lunes Gorka tiene horario propio de 8 h: %r %r' % (e.horas('Gorka'), chip(e, 'Gorka', True)))
        ok(e.horas('Aitor') == '7,5 h' and chip(e, 'Aitor', True) == '', 'T55b el lunes Aitor (propio solo el viernes) sigue el horario de la obra y no lleva chip: %r %r' % (e.horas('Aitor'), chip(e, 'Aitor', True)))
    con_escena('T55b', est5({'Aitor': {'vie': 9}, 'Gorka': {'lun': 8}}), t55b)

    # --- T56: al fijar o quitar un horario propio estando marcado, lo que seguía al horario anterior se mueve; lo puesto a mano no
    def t56(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Aitor"] .x')
        e.clic('#v-app .row[data-nombre="Gorka"] .x')
        e.pulsar('Gorka', 2, '0.5')
        guardar_propio(e, 'Aitor', {'vie': 9})
        guardar_propio(e, 'Gorka', {'vie': 9})
        ok(e.horas('Aitor') == '9 h', 'T56 Aitor seguía el horario de la obra (7,5 h): al fijar su horario propio pasa a 9 h: %r' % e.horas('Aitor'))
        ok(e.horas('Gorka') == '8,5 h' and chip(e, 'Gorka') == '', 'T56 las horas puestas a mano (8,5 h) no se tocan y no hay extra: %r %r' % (e.horas('Gorka'), chip(e, 'Gorka')))
        guardar_propio(e, 'Aitor', {})
        ok(e.horas('Aitor') == '7,5 h' and chip(e, 'Aitor', True) == '', 'T56 al quitar el horario propio vuelve al de la obra: %r' % e.horas('Aitor'))
        guardar_propio(e, 'Aitor', {'vie': 6})
        ok(e.horas('Aitor') == '6 h' and chip(e, 'Aitor') == '', 'T56 un horario propio MENOR (6 h) también se sigue y no genera extra: %r' % e.horas('Aitor'))
        e.pulsar('Aitor', 3, '0.5')
        ok(e.horas('Aitor') == '7,5 h' and chip(e, 'Aitor') == '+1,5 h extra', 'T56 el extra se cuenta contra SU horario (6 h): %r %r' % (e.horas('Aitor'), chip(e, 'Aitor')))
    con_escena('T56', est5(), t56)

    # --- T57: quitar un horario propio ya publicado: se recuerda la baja, se exporta {"Aitor": {}} (aunque no haya jornadas) y se olvida al publicarse
    def t57(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Aitor"] .x')
        ok(e.horas('Aitor') == '9 h', 'T57 preparación: Aitor sale a 9 h con su horario propio publicado: %r' % e.horas('Aitor'))
        guardar_propio(e, 'Aitor', {})
        ok(e.horas('Aitor') == '7,5 h' and chip(e, 'Aitor', True) == '', 'T57 sin horario propio vuelve a 7,5 h: %r' % e.horas('Aitor'))
        ok(propio_ls(e) and json.loads(propio_ls(e)) == {'olabeaga': {'Aitor': {}}}, 'T57 la baja se recuerda como {} (distinta de lo publicado): %r' % propio_ls(e))
        lote = e.exportar() or {}
        ok(lote.get('excepciones_horario') == {'Aitor': {}} and lote.get('jornadas') == [], 'T57 se exporta la baja aunque no haya jornadas: %s' % lote)
        valida_con_p1(lote)
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        ok(e.horas('Aitor') == '7,5 h', 'T57 tras recargar la baja sigue recordada: %r' % e.horas('Aitor'))
        with open(os.path.join(e.dir, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
            fh.write('window.SAGARDE_PERSONAL = ' + json.dumps(est5({'Gorka': {'vie': 9}}), ensure_ascii=False) + ';\n')
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        ok(propio_ls(e) in (None, '{}'), 'T57 cuando el estado publicado ya no trae el horario propio, la baja se olvida: %r' % propio_ls(e))
    con_escena('T57', est5(PROPIOS), t57)

    # --- T58: el horario propio es de una obra (vale en viviendas y garajes, no en otra obra) y se recuerda al cerrar la app
    def t58(e):
        e.ir()
        guardar_propio(e, 'Aitor', {'vie': 9})
        ok(json.loads(propio_ls(e)) == {'olabeaga': {'Aitor': {'vie': 9}}}, 'T58 se guarda dentro de su obra: %r' % propio_ls(e))
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        e.clic('#v-app .row[data-nombre="Aitor"] .x')
        ok(e.horas('Aitor') == '9 h', 'T58 tras cerrar y abrir la app, Aitor sale a 9 h: %r' % e.horas('Aitor'))
        e.clic('button[data-amb="garaje"]')
        e.anotar('Aitor')
        ok(e.horas('Aitor') == '9 h', 'T58 el horario propio vale también en garajes: %r' % e.horas('Aitor'))
        e.obra('mungia')
        e.anotar('Aitor')
        ok(e.horas('Aitor') == '7,5 h' and chip(e, 'Aitor', True) == '', 'T58 en otra obra Aitor no tiene horario propio: %r' % e.horas('Aitor'))
    con_escena('T58', est5(), t58)

    # --- T59: fijar un horario propio con una jornada ya guardada NO reescribe la jornada
    def t59(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Aitor"] .x')
        e.clic('button[data-guardar]')
        guardar_propio(e, 'Aitor', {'vie': 9})
        ok(e.pendientes() == '1', 'T59 sigue habiendo una jornada pendiente: %r' % e.pendientes())
        lote = e.exportar() or {}
        a = [p for j in lote.get('jornadas', []) for p in j['presentes'] if p['nombre'] == 'Aitor']
        ok(a and a[0]['horas'] == 7.5 and a[0]['extra'] == 0, 'T59 la jornada ya guardada conserva sus 7,5 h: %s' % a)
        ok(lote.get('excepciones_horario') == {'Aitor': {'vie': 9}}, 'T59 el horario propio nuevo viaja en el lote: %s' % lote.get('excepciones_horario'))
        e.clic('button[data-v="informe"]')
        ok(tokens(e.informe(), 'Aitor')[4] == '7,5', 'T59 el informe sigue contando la jornada guardada con 7,5 h: %r' % fila_de(e.informe(), 'Aitor'))
    con_escena('T59', est5(), t59)

    # --- T61: lo que entra por guardarPropio se limpia (0–24, 2 decimales como mucho, días válidos); vacío = quitar
    def t61(e):
        e.ir()
        guardar_propio(e, 'Aitor', {'vie': 30, 'lun': -3, 'mar': '', 'mie': None, 'jue': 9.555, 'sab': 'abc', 'xxx': 5})
        mem = json.loads(propio_ls(e) or '{}').get('olabeaga', {}).get('Aitor', {})
        ok(set(mem) == {'lun', 'jue', 'vie'} and mem.get('vie') == 24 and mem.get('lun') == 0 and abs(mem.get('jue', 0) - 9.555) < 0.01 and round(mem.get('jue', 0), 2) == mem.get('jue'),
           'T61 se limpia: 30 → 24, −3 → 0, vacíos y textos fuera, un día inventado fuera, 2 decimales: %s' % mem)
        e.clic('#v-app .row[data-nombre="Aitor"] .x')
        e.clic('button[data-guardar]')
        valida_con_p1(e.exportar() or {})
        guardar_propio(e, 'Aitor', {'vie': '', 'lun': ''})
        ok(propio_ls(e) in (None, '{}'), 'T61 un objeto sin ninguna hora equivale a quitar; si no hay nada publicado, no queda nada que recordar: %r' % propio_ls(e))
    con_escena('T61', est5(), t61)

    # --- T62: lo que haya en sgd_personal_excepciones, por dañado que esté, no tumba la app; las personas con datos no válidos se ignoran enteras
    def t62_mala(e):
        e.ir()
        ok(e.pg.query_selector('#obra') is not None, 'T62 la app debe arrancar con sgd_personal_excepciones dañado')
        e.clic('#v-app .row[data-nombre="Aitor"] .x')
        ok(e.horas('Aitor') == '7,5 h', 'T62 un horario propio no válido se ignora entero (Aitor sigue a 7,5 h): %r' % e.horas('Aitor'))
    for tag, val in (('texto', 'x'), ('lista', []), ('null', None), ('obra que no es objeto', {'olabeaga': 5}), ('persona que no es objeto', {'olabeaga': {'Aitor': 9}}),
                     ('día inventado', {'olabeaga': {'Aitor': {'xxx': 9, 'vie': 9}}}), ('hora en texto', {'olabeaga': {'Aitor': {'vie': '9'}}}),
                     ('hora fuera de rango', {'olabeaga': {'Aitor': {'vie': 99}}}), ('hora nula', {'olabeaga': {'Aitor': {'vie': None}}})):
        con_escena('T62 ' + tag, est5(), t62_mala, init=sembrar('sgd_personal_excepciones', val))

    def t62_mixta(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Aitor"] .x')
        e.clic('#v-app .row[data-nombre="Gorka"] .x')
        ok(e.horas('Aitor') == '9 h' and e.horas('Gorka') == '7,5 h', 'T62 de lo recordado se aprovecha lo válido (Aitor 9 h) y se ignora lo dañado (Gorka 7,5 h): %r %r' % (e.horas('Aitor'), e.horas('Gorka')))
    def t62_publicado(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Aitor"] .x')
        e.clic('#v-app .row[data-nombre="Gorka"] .x')
        ok(e.horas('Aitor') == '9 h' and e.horas('Gorka') == '9 h', 'T62 una persona dañada en la memoria se ignora ENTERA: no puede convertirse en una baja que borre en silencio el horario propio publicado (Aitor y Gorka siguen a 9 h): %r %r' % (e.horas('Aitor'), e.horas('Gorka')))
    con_escena('T62 publicado', est5(PROPIOS), t62_publicado, init=sembrar('sgd_personal_excepciones', {'olabeaga': {'Aitor': {'vie': '9'}, 'Gorka': {'xxx': 1, 'vie': 5}}}))
    con_escena('T62 mixta', est5(), t62_mixta, init=sembrar('sgd_personal_excepciones', {'olabeaga': {'Aitor': {'vie': 9}, 'Gorka': {'vie': '9'}}, 'obra_que_no_existe': {'Aitor': {'vie': 9}}}))

    # --- T63: la app espera como máximo 4 s a personal_estado.js; si no llega usa la copia guardada y lo dice (por HTTP, con el .js lento)
    class _Lento(http.server.SimpleHTTPRequestHandler):
        retraso = 0

        def do_GET(self):
            if 'personal_estado.js' in self.path:
                time.sleep(self.retraso)
            try:
                return super().do_GET()
            except ConnectionError:
                return None     # la página ya se cerró antes de que terminara de enviarse: no es un fallo

        def log_message(self, *a):
            pass

    def abrir_lento(retraso, con_copia):
        """Devuelve (escena, servidor, instante de la petición)."""
        datos = est5()
        e = Escena(datos, init=sembrar('sgd_personal_estado', datos) if con_copia else None)
        srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(type('Manejador', (_Lento,), {'retraso': retraso}), directory=e.dir))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        e.pg.goto('http://127.0.0.1:%d/generador_personal.html' % srv.server_port, wait_until='commit')
        return e, srv, time.time()

    def espera_obra_hasta(e, t0, limite):
        while time.time() - t0 < limite:
            if e.pg.query_selector('#obra') is not None:
                return time.time() - t0
            e.pg.wait_for_timeout(100)
        return None

    def t63(nombre, retraso, con_copia, fn):
        if os.environ.get('P3_SOLO_08C') == '1' or os.environ.get('P3_SOLO_08D') == '1' or os.environ.get('P3_SOLO_08C2A') == '1' \
                or os.environ.get('P3_SOLO_08C2B') == '1':
            return
        e = srv = None
        try:
            e, srv, t0 = abrir_lento(retraso, con_copia)
            fn(e, t0)
        except Exception as ex:  # noqa: BLE001
            ok(False, '%s se interrumpió: %s' % (nombre, (str(ex).strip().splitlines() or [repr(ex)])[0][:220]))
        finally:
            if e is not None:
                ok(not e.errs, '%s: errores de JavaScript: %s' % (nombre, e.errs))
                e.cerrar()
            if srv is not None:
                srv.shutdown()

    def f63a(e, t0):
        t = espera_obra_hasta(e, t0, 12)
        ok(t is not None and 3.5 <= t <= 6.5, 'T63a con el .js tardando 8 s y copia guardada, la app abre a los ~4 s (no antes, no después): abrió a los %s s' % (None if t is None else round(t, 1)))
        ok('guardada' in e.txt('#estado-origen').lower(), 'T63a debe decir que usa la lista guardada: %r' % e.txt('#estado-origen'))
        e.pg.wait_for_timeout(max(0, int((8.5 - (time.time() - t0)) * 1000)))
        ok('guardada' in e.txt('#estado-origen').lower() and e.pg.query_selector('#obra') is not None, 'T63a cuando el .js llega tarde no se cambia lo que se está viendo: %r' % e.txt('#estado-origen'))
    t63('T63a', 8, True, f63a)

    def f63b(e, t0):
        t = espera_obra_hasta(e, t0, 8)
        ok(t is not None and t <= 3.5, 'T63b si el .js llega a los 1,5 s la app abre sin esperar a los 4 s: abrió a los %s s' % (None if t is None else round(t, 1)))
        ok('al día' in e.txt('#estado-origen').lower(), 'T63b debe decir «al día»: %r' % e.txt('#estado-origen'))
    t63('T63b', 1.5, True, f63b)

    def f63c(e, t0):
        e.pg.wait_for_timeout(5000)
        sin = e.pg.query_selector('#sin-estado') is not None and e.pg.is_visible('#sin-estado')
        ok(e.pg.query_selector('#obra') is None and not sin, 'T63c sin copia guardada no hay con qué abrir: la app sigue esperando (no enseña «todavía no hay datos»): sin_datos=%s' % sin)
        t = espera_obra_hasta(e, t0, 12)
        ok(t is not None and 'al día' in e.txt('#estado-origen').lower(), 'T63c cuando por fin llega el .js (a los 7 s) la app abre con él: %r' % e.txt('#estado-origen'))
    t63('T63c', 7, False, f63c)

    # --- Escenas extra (P3_EXTRA=1; se añadieron al revisar el código de la tanda A y matar mutantes)
    if os.environ.get('P3_EXTRA', '1') != '0':      # activas por defecto (P3_EXTRA=0 las omite)
        def t53b(e):
            e.ir()
            e.clic('#v-app .row[data-nombre="Aitor"] .x')
            e.clic('#v-app .row[data-nombre="Gorka"] .x')
            guardar_propio(e, 'Aitor', {'vie': 9})
            guardar_propio(e, 'Gorka', {'vie': 9})
            e.clic('button[data-guardar]')
            ok(e.exportar() is not None and '1 jornada' in e.listo() and '2 horarios especiales' in e.listo(), 'T53b (08d) el recuadro «Listo» cuenta jornadas y horarios especiales: %r' % e.listo())
        con_escena('T53b', est5(), t53b)

        def t54b(e):
            e.ir()
            e.clic('button[data-todos="1"]')
            e.pulsar('Aitor', 1, '0.5')
            e.pulsar('Mikel', 1, '0.5')
            ok(e.horas('Aitor') == '9,5 h' and chip(e, 'Aitor') == '+0,5 h extra' and e.horas('Mikel') == '8 h', 'T54b con «Marcar todos» (horas sin fijar) el primer + parte del horario de CADA persona: %r %r %r' % (e.horas('Aitor'), chip(e, 'Aitor'), e.horas('Mikel')))
        con_escena('T54b', est5(PROPIOS), t54b)

        def t55c(e):
            e.ir()
            marcar_los_cinco(e)
            cambia_horario(e, 1, 6)             # primero el lunes (todos siguen en 7,5): no se mueve nadie
            ok(horas5(e) == {n: '7,5 h' for n in CINCO}, 'T55c cambiar el horario del lunes estando en viernes (con las horas aún sin tocar) no mueve a nadie: %s' % horas5(e))
            cambia_horario(e, 5, 8)
            ok(horas5(e) == {'Mikel': '8 h', 'Txomin': '8 h', 'Rafa': '8 h', 'Aitor': '8 h', 'Gorka': '7,5 h'}, 'T55c quien tiene horario propio de ese día (Gorka: 7,5 h, igual que el horario anterior de la obra) NO se mueve: %s' % horas5(e))
            ok(all(chip(e, n) == '' for n in CINCO), 'T55c sin horas extra: %s' % [chip(e, n) for n in CINCO])
            cambia_horario(e, 5, 0)
            ok(horas5(e) == {'Mikel': '¿horas?', 'Txomin': '¿horas?', 'Rafa': '¿horas?', 'Aitor': '¿horas?', 'Gorka': '7,5 h'} and 'faltan horas' in e.txt('.sum').lower(), 'T55c si el día se queda sin horario, quien lo seguía pasa a «¿horas?» (no a 0 h): %s %r' % (horas5(e), e.txt('.sum')))
        con_escena('T55c', est5({'Gorka': {'vie': 7.5}}), t55c)

        def t66(e):
            e.ir()
            guardar_propio(e, 'Aitor', {'vie': 9, 'lun': 8})
            ok(json.loads(propio_ls(e) or '{}') == {'olabeaga': {'Aitor': {'vie': 9, 'lun': 8}}}, 'T66 un día MÁS que lo publicado es un cambio y se recuerda: %r' % propio_ls(e))
            guardar_propio(e, 'Aitor', {'vie': 9})
            ok(propio_ls(e) in (None, '{}'), 'T66 igual que lo publicado: no queda nada que recordar: %r' % propio_ls(e))
        con_escena('T66', est5({'Aitor': {'vie': 9}}), t66)

        def t66b(e):
            e.ir()
            guardar_propio(e, 'Aitor', {'vie': 9})
            ok(json.loads(propio_ls(e) or '{}') == {'olabeaga': {'Aitor': {'vie': 9}}}, 'T66b un día MENOS que lo publicado es un cambio y se recuerda: %r' % propio_ls(e))
        con_escena('T66b', est5({'Aitor': {'vie': 9, 'lun': 8}}), t66b)

        def t66c(e):
            e.ir()
            ok(json.loads(propio_ls(e) or '{}') == {'olabeaga': {'Aitor': {'vie': 9, 'lun': 8}}}, 'T66c al abrir, lo recordado que sigue siendo distinto de lo publicado se conserva: %r' % propio_ls(e))
        con_escena('T66c', est5({'Aitor': {'vie': 9}}), t66c, init=sembrar('sgd_personal_excepciones', {'olabeaga': {'Aitor': {'vie': 9, 'lun': 8}}}))

        def t66d(e):
            e.ir()
            ok(propio_ls(e) in (None, '{}'), 'T66d al abrir, lo recordado que ya es igual a lo publicado se olvida: %r' % propio_ls(e))
        con_escena('T66d', est5({'Aitor': {'vie': 9, 'lun': 8}}), t66d, init=sembrar('sgd_personal_excepciones', {'olabeaga': {'Aitor': {'lun': 8, 'vie': 9}}}))

        def t69(e):
            e.ir()
            e.fecha('2026-10-24')
            e.clic('#v-app .row[data-nombre="Aitor"] .x')
            e.clic('#v-app .row[data-nombre="Gorka"] .x')
            ok(e.horas('Aitor') == '4 h' and e.horas('Gorka') == '¿horas?' and 'faltan horas' in e.txt('.sum').lower(), 'T69 el sábado, Aitor (horario propio de 4 h) sale a 4 h y Gorka (sin horario) a «¿horas?»: %r %r %r' % (e.horas('Aitor'), e.horas('Gorka'), e.txt('.sum')))
            e.clic('#v-app .row[data-nombre="Gorka"] .x')
            ok(e.txt('.sum') == '1 presente · 4 h', 'T69 con solo Aitor el sábado no faltan horas: %r' % e.txt('.sum'))
            e.clic('button[data-guardar]')
            ok(e.pendientes() == '1', 'T69 se puede guardar el sábado con el horario propio: %r %r' % (e.pendientes(), e.toast()))
            a = [p for j in (e.exportar() or {}).get('jornadas', []) for p in j['presentes']]
            ok(a and a[0]['horas'] == 4 and a[0]['extra'] == 0, 'T69 el sábado de Aitor son 4 h normales: %s' % a)
            guardar_propio(e, 'Aitor', {})
            ok(e.horas('Aitor') == '¿horas?', 'T69 al quitarle el horario propio del sábado vuelve a «¿horas?» (no a 0 h): %r' % e.horas('Aitor'))
        con_escena('T69', est5({'Aitor': {'sab': 4}}), t69)

        def t54c(e):
            e.ir()
            e.clic('button[data-todos="1"]')
            ok(e.txt('.sum') == '5 presentes · 40,5 h', 'T54c «Marcar todos» (horas sin fijar): el resumen suma el horario de CADA persona: %r' % e.txt('.sum'))
            e.clic('button[data-guardar]')
            ps = {p['nombre']: (p['horas'], p.get('extra', 0)) for j in (e.exportar() or {}).get('jornadas', []) for p in j['presentes']}
            ok(ps == {'Mikel': (7.5, 0), 'Txomin': (7.5, 0), 'Rafa': (7.5, 0), 'Aitor': (9, 0), 'Gorka': (9, 0)}, 'T54c guardar con «Marcar todos» fija el horario de cada persona (9 h para los de horario propio): %s' % ps)
        con_escena('T54c', est5(PROPIOS), t54c)

        def t66e(e):
            e.ir()
            guardar_propio(e, 'Aitor', {'vie': 9, 'lun': 7})
            ok(json.loads(propio_ls(e) or '{}') == {'olabeaga': {'Aitor': {'vie': 9, 'lun': 7}}}, 'T66e mismos días pero otra hora en uno de ellos es un cambio y se recuerda: %r' % propio_ls(e))
        con_escena('T66e', est5({'Aitor': {'vie': 9, 'lun': 8}}), t66e)

        def t69b(e):
            e.ir()
            e.fecha('2026-10-24')
            e.clic('button[data-todos="1"]')
            for n in ('Mikel', 'Txomin', 'Rafa', 'Gorka'):
                e.clic('#v-app .row[data-nombre="%s"] .x' % n)
            ok(e.marcados() == ['Aitor'] and e.txt('.sum') == '1 presente · 4 h', 'T69b el sábado con «Marcar todos» y solo Aitor marcado: 4 h (su horario propio), sin «faltan horas»: %r %s' % (e.txt('.sum'), e.marcados()))
            e.clic('button[data-guardar]')
            ok(e.pendientes() == '1' and 'faltan' not in e.toast(), 'T69b se guarda sin pedir horas: %r %r' % (e.pendientes(), e.toast()))
        con_escena('T69b', est5({'Aitor': {'sab': 4}}), t69b)

        def t23b(e):
            e.ir()
            guardar_propio(e, 'Aitor', {'vie': 9})
            ok('no se pudo' in e.toast(), 'T23b si el aparato no deja guardar, guardarPropio lo avisa: %r' % e.toast())
        con_escena('T23b', est5(), t23b, init=sin_ls)

        def f63d(e, t0):
            t = espera_obra_hasta(e, t0, 10)
            ok(t is not None and 'tarda en llegar' in e.txt('#estado-origen').lower() and 'lista guardada en este aparato' in e.txt('#estado-origen').lower(), 'T63d cuando abre por la espera dice que la lista nueva tarda en llegar: %r' % e.txt('#estado-origen'))
        t63('T63d', 6, True, f63d)

    if GRUPO_B:
        # --- T65 (B): el ejemplo de Bixente metiendo el horario propio con la pantalla
        def t65(e):
            e.ir()
            marcar_los_cinco(e)
            ok(all(e.pg.query_selector('#v-app .row[data-nombre="%s"] button[data-hp-abrir]' % n) is not None for n in CINCO), 'T65 cada presente lleva su botón «Horario propio» (button[data-hp-abrir])')
            ok(all('horario especial' in e.txt('#v-app .row[data-nombre="%s"] button[data-hp-abrir]' % n).lower() for n in CINCO), 'T65 el botón dice «Horario especial»')
            for n in ('Aitor', 'Gorka'):
                fila_n = '#v-app .row[data-nombre="%s"]' % n
                e.clic(fila_n + ' button[data-hp-abrir]')
                ok(e.pg.query_selector(fila_n + ' .hp') is not None and e.pg.is_visible(fila_n + ' .hp'), 'T65 el editor se abre dentro de la misma fila de %s' % n)
                ok(e.pg.eval_on_selector_all(fila_n + ' .hp input[data-hp]', 'e=>e.map(i=>i.dataset.hp)') == ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom'], 'T65 siete casillas, de lunes a domingo, en %s' % n)
                e.pg.fill(fila_n + ' input[data-hp="vie"]', '9')
                e.clic(fila_n + ' button[data-hp-guardar]')
                ok(e.pg.query_selector(fila_n + ' .hp') is None, 'T65 el editor se cierra al guardar')
            ok(horas5(e) == H_9 and e.txt('.sum') == '5 presentes · 40,5 h', 'T65 con la pantalla: Aitor y Gorka a 9 h, resumen 40,5 h: %s %r' % (horas5(e), e.txt('.sum')))
            ok(chip(e, 'Aitor', True) == 'horario especial 9 h', 'T65 chip de horario especial tras guardar: %r' % chip(e, 'Aitor', True))
            e.clic('button[data-guardar]')
            lote = e.exportar() or {}
            ok(lote.get('excepciones_horario') == {'Aitor': {'vie': 9}, 'Gorka': {'vie': 9}}, 'T65 el lote lleva el horario propio: %s' % lote.get('excepciones_horario'))
            valida_con_p1(lote)
        con_escena('T65', est5(), t65)

        # --- T66 (B): contenido y comportamiento del editor
        def t66(e):
            e.ir()
            marcar_los_cinco(e)
            ok(e.pg.query_selector('#v-app .row[data-nombre="Mikel"] .hp') is None, 'T66 el editor empieza cerrado')
            a = '#v-app .row[data-nombre="Aitor"]'
            g = '#v-app .row[data-nombre="Gorka"]'
            e.clic(a + ' button[data-hp-abrir]')
            ok(e.pg.input_value(a + ' input[data-hp="vie"]') == '9' and all(e.pg.input_value(a + ' input[data-hp="%s"]' % d) == '' for d in ('lun', 'mar', 'mie', 'jue', 'sab', 'dom')), 'T66 el editor sale rellenado con el horario propio actual (vie 9) y el resto vacío')
            ok(e.pg.get_attribute(a + ' input[data-hp="lun"]', 'placeholder') == '7,5' and e.pg.get_attribute(a + ' input[data-hp="sab"]', 'placeholder') == '0', 'T66 las casillas vacías enseñan el horario de la obra de ese día (7,5 / 0) como pista: %r %r' % (e.pg.get_attribute(a + ' input[data-hp="lun"]', 'placeholder'), e.pg.get_attribute(a + ' input[data-hp="sab"]', 'placeholder')))
            tx = e.txt(a + ' .hp').lower()
            ok('aitor' in tx and 'sigue el horario de la obra' in tx and 'guardar horario especial' in tx and 'quitar' in tx, 'T66 el editor dice de quién es, qué significa vacío y lleva «Guardar horario especial» y «Quitar»: %r' % tx)
            e.clic(g + ' button[data-hp-abrir]')
            ok(e.pg.query_selector(a + ' .hp') is None and e.pg.query_selector(g + ' .hp') is not None, 'T66 solo hay un editor abierto a la vez')
            e.clic(g + ' button[data-hp-abrir]')
            ok(e.pg.query_selector(g + ' .hp') is None, 'T66 pulsar otra vez «Horario propio» cierra el editor')
            e.clic(a + ' button[data-hp-abrir]')
            e.pg.fill(a + ' input[data-hp="lun"]', '5')
            e.clic(a + ' button[data-hp-abrir]')
            e.clic(a + ' button[data-hp-abrir]')
            ok(e.pg.input_value(a + ' input[data-hp="lun"]') == '' and propio_ls(e) in (None, '{}'), 'T66 lo escrito y no guardado se descarta al cerrar: lunes %r, memoria %r' % (e.pg.input_value(a + ' input[data-hp="lun"]'), propio_ls(e)))
            e.clic(a + ' .x')
            ok(e.pg.query_selector(a + ' .hp') is None and e.pg.query_selector(a + ' button[data-hp-abrir]') is None, 'T66 al desmarcar a alguien se cierra el editor y desaparece su botón')
            e.clic(a + ' .x')
            ok(e.pg.query_selector(a + ' .hp') is None, 'T66 y al volver a marcarlo el editor no reaparece solo')
            e.clic(a + ' .x')
            ok(e.pg.query_selector('#v-app .row.off button[data-hp-abrir]') is None, 'T66 las filas sin marcar no llevan botón de horario propio')
        con_escena('T66', est5(PROPIOS), t66)

        # --- T67 (B): «Quitar» y guardar todo en blanco
        def t67(e):
            e.ir()
            e.clic('#v-app .row[data-nombre="Aitor"] .x')
            e.clic('#v-app .row[data-nombre="Gorka"] .x')
            a = '#v-app .row[data-nombre="Aitor"]'
            g = '#v-app .row[data-nombre="Gorka"]'
            e.clic(a + ' button[data-hp-abrir]')
            e.clic(a + ' button[data-hp-quitar]')
            ok(e.horas('Aitor') == '7,5 h' and chip(e, 'Aitor', True) == '' and e.pg.query_selector(a + ' .hp') is None, 'T67 «Quitar» vuelve al horario de la obra y cierra el editor: %r' % e.horas('Aitor'))
            e.clic(g + ' button[data-hp-abrir]')
            e.pg.fill(g + ' input[data-hp="vie"]', '')
            e.clic(g + ' button[data-hp-guardar]')
            ok(e.horas('Gorka') == '7,5 h', 'T67 guardar con todas las casillas vacías equivale a quitar: %r' % e.horas('Gorka'))
            lote = e.exportar() or {}
            ok(lote.get('excepciones_horario') == {'Aitor': {}, 'Gorka': {}}, 'T67 el lote lleva las dos bajas: %s' % lote.get('excepciones_horario'))
            valida_con_p1(lote)
        con_escena('T67', est5(PROPIOS), t67)

        # --- T68 (B): tamaños táctiles, letra y desbordamiento con el editor abierto (móvil 390 y 320, tablet 820)
        def t68(e):
            e.ir()
            e.clic('#v-app .row[data-nombre="Aitor"] .x')
            e.clic('#v-app .row[data-nombre="Aitor"] button[data-hp-abrir]')
            m = e.pg.evaluate("""() => { const q = s => [...document.querySelectorAll(s)].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
               const hp = document.querySelector('#v-app .hp').getBoundingClientRect();
               return {abrir: q('#v-app button[data-hp-abrir]'), guardar: q('#v-app button[data-hp-guardar]'), quitar: q('#v-app button[data-hp-quitar]'), inputs: q('#v-app .hp input'),
                       dentro: [Math.round(hp.left), Math.round(hp.right), innerWidth], ancho: document.documentElement.scrollWidth,
                       letra_input: parseFloat(getComputedStyle(document.querySelector('#v-app .hp input')).fontSize),
                       letra_etiqueta: parseFloat(getComputedStyle(document.querySelector('#v-app .hp label')).fontSize)}; }""")
            ok(all(h >= 48 for w, h in m['abrir'] + m['guardar'] + m['quitar']), 'T68 los botones del horario propio miden al menos 48 px de alto: %s' % (m['abrir'] + m['guardar'] + m['quitar']))
            ok(all(h >= 48 and w >= 40 for w, h in m['inputs']), 'T68 las casillas del editor miden al menos 48 px de alto y 40 de ancho: %s' % m['inputs'])
            ok(m['dentro'][0] >= 0 and m['dentro'][1] <= m['dentro'][2] and m['ancho'] <= m['dentro'][2] + 1, 'T68 el editor cabe en la pantalla sin desplazamiento lateral: %s' % m['dentro'])
            ok(m['letra_input'] >= 16 and m['letra_etiqueta'] >= 12, 'T68 letra legible (casillas ≥ 16 px para que el iPad no haga zoom, etiquetas ≥ 12 px): %s %s' % (m['letra_input'], m['letra_etiqueta']))
        con_escena('T68', est5(PROPIOS), t68)
        con_escena('T68 estrecho', est5(PROPIOS), t68, ancho=320, alto=640)
        con_escena('T68 tablet', est5(PROPIOS), t68, ancho=820, alto=1180)

        # --- T64 (B): «Empezar de cero» pregunta antes de borrar, dentro de la página y sin ventanas del navegador
        def t64(e):
            ventanas = []
            e.pg.on('dialog', lambda d: (ventanas.append(d.message), d.dismiss()))
            e.ir()
            e.clic('#v-app .row[data-nombre="Mikel"] .x')
            e.clic('button[data-guardar]')
            e.clic('#v-app .row[data-nombre="Rafa"] .x')
            e.pg.evaluate("window.__marca = 1")
            e.clic('button[data-reset]')
            ok(e.pg.query_selector('#confirmar-reset') is not None and e.pg.is_visible('#confirmar-reset'), 'T64 «Empezar de cero» debe mostrar la pregunta #confirmar-reset dentro de la página')
            ok('¿Borrar lo que llevas a medias?' in e.txt('#confirmar-reset'), 'T64 texto de la pregunta: %r' % e.txt('#confirmar-reset'))
            pos = e.pg.evaluate("(()=>{const r=document.querySelector('#confirmar-reset').getBoundingClientRect();return [r.top,r.bottom,innerHeight]})()")
            ok(pos[0] >= 0 and pos[1] <= pos[2], 'T64 la pregunta se ve en pantalla justo al pulsar el botón: top=%d bottom=%d alto=%d' % tuple(pos))
            ok(e.pg.evaluate("window.__marca") == 1 and e.marcados() == ['Mikel', 'Rafa'] and e.pg.evaluate("localStorage.getItem('sgd_personal_borrador')") is not None, 'T64 hasta que se responde no se borra, no se desmarca a nadie y no se recarga nada: marcados %s' % e.marcados())
            ok(e.pg.query_selector('#v-app button[data-reset]') is None, 'T64 mientras se pregunta, la pregunta sustituye a la fila de botones «Exportar pendientes / Empezar de cero»')
            h = e.pg.evaluate("(()=>[...document.querySelectorAll('#confirmar-reset button')].map(b=>b.getBoundingClientRect().height))()")
            ok(len(h) == 2 and all(x >= 48 for x in h), 'T64 la pregunta tiene dos botones de al menos 48 px: %s' % h)
            e.clic('button[data-reset-no]')
            ok(e.pg.query_selector('#confirmar-reset') is None and e.pg.query_selector('#v-app button[data-reset]') is not None and e.pg.evaluate("window.__marca") == 1 and e.marcados() == ['Mikel', 'Rafa'] and e.pg.evaluate("localStorage.getItem('sgd_personal_borrador')") is not None, 'T64 «No» cierra la pregunta, vuelven los botones y no cambia nada: marcados %s' % e.marcados())
            e.clic('button[data-reset]')
            e.clic('button[data-reset-si]')
            e.pg.wait_for_selector('#obra')
            e.pg.wait_for_timeout(300)
            ok(e.pg.evaluate("window.__marca") is None and 'Rafa' not in e.marcados(), 'T64 «Sí» recarga y olvida el borrador: marca %r, marcados %s' % (e.pg.evaluate("window.__marca"), e.marcados()))
            ok(e.pendientes() == '1', 'T64 las jornadas pendientes se conservan: %r' % e.pendientes())
            ok(not ventanas, 'T64 no debe abrirse ninguna ventana del navegador (confirm/alert): %s' % ventanas)
        con_escena('T64', ESTADO1, t64)

        # --- T70 (B): si el aparato no deja guardar, el editor del horario propio no dice «guardado»
        def t70(e):
            e.ir()
            e.clic('#v-app .row[data-nombre="Aitor"] .x')
            e.clic('#v-app .row[data-nombre="Aitor"] button[data-hp-abrir]')
            e.pg.fill('#v-app .row[data-nombre="Aitor"] input[data-hp="vie"]', '9')
            e.clic('#v-app .row[data-nombre="Aitor"] button[data-hp-guardar]')
            ok('no se pudo' in e.toast() and 'horario especial guardado' not in e.toast(), 'T70 sin poder escribir en el aparato, «Guardar horario especial» avisa del fallo y no dice «guardado»: %r' % e.toast())
            e.clic('#v-app .row[data-nombre="Aitor"] button[data-hp-abrir]')
            e.clic('#v-app .row[data-nombre="Aitor"] button[data-hp-quitar]')
            ok('horario propio quitado' not in e.toast(), 'T70 lo mismo con «Quitar»: %r' % e.toast())
        con_escena('T70', est5(), t70, init=sin_ls)

        # --- T71 (B): un editor abierto no reaparece solo al desmarcar y volver a marcar a todos; abrir no cambia horas
        def t71(e):
            e.ir()
            marcar_los_cinco(e)
            e.clic('#v-app .row[data-nombre="Aitor"] button[data-hp-abrir]')
            ok(horas5(e) == H_9, 'T71 abrir el editor no cambia ninguna hora: %s' % horas5(e))
            e.clic('button[data-todos="0"]')
            e.clic('button[data-todos="1"]')
            ok(e.pg.query_selector('#v-app .hp') is None, 'T71 con «Desmarcar todos» y «Marcar todos» el editor abierto se cierra y no reaparece')
            e.clic('#v-app .row[data-nombre="Aitor"] button[data-hp-abrir]')
            e.fecha('2026-10-19')
            ok(e.pg.query_selector('#v-app .hp') is None, 'T71 al cambiar de fecha se cierra el editor')
            e.clic('#v-app .row[data-nombre="Aitor"] .x')
            ok(e.pg.query_selector('#v-app .hp') is None, 'T71 y al marcar otra vez a Aitor en la otra fecha el editor no reaparece solo')
        con_escena('T71', est5(PROPIOS), t71)

        # --- T72 (B): el editor escapa el nombre de la persona (comillas, < y &)
        def t72(e):
            e.ir()
            e.clic('#v-app .row .x')
            e.clic('#v-app .row button[data-hp-abrir]')
            ok(e.txt('#v-app .hp b') == 'Horario especial de ' + raro, 'T72 el título del editor lleva el nombre tal cual: %r' % e.txt('#v-app .hp b'))
            ok(e.pg.evaluate("document.querySelectorAll('#v-app .hp b *').length") == 0 and e.pg.evaluate("document.querySelectorAll('#v-app .hp b').length") == 1, 'T72 no se interpreta HTML dentro del nombre del editor')
            e.pg.fill('#v-app .hp input[data-hp="vie"]', '9')
            e.clic('#v-app .hp button[data-hp-guardar]')
            ok(json.loads(propio_ls(e) or '{}') == {'olabeaga': {raro: {'vie': 9}}}, 'T72 el horario propio se guarda con el nombre raro intacto: %r' % propio_ls(e))
            valida_con_p1(e.exportar() or {})
        con_escena('T72', estado_con({'olabeaga': obra_est('2026 OLABEAGA', [], ultima={'vivienda': {'fecha': '2026-10-22', 'presentes': pres(raro)}, 'garaje': None})}, [raro]), t72)

    # ======================================================================================================================
    # Paso 08c: corregir un nombre (lápiz ✎), toda la base en el desplegable y «Añadir varios nombres».
    # Escenas T80–T89. Con P3_SOLO_08C=1 solo corren estas (y las comprobaciones estáticas). Cada una usa datos inventados
    # y, cuando hay fichero, lo comprueba con P1 y lo APLICA de verdad sobre un PC de pruebas (e2e_p1).
    # ======================================================================================================================
    CAT8 = ['Mikel', 'Txomin', 'Rafa', 'Andoni', 'Josu', 'José', 'Iñaki', 'Pepe', 'Zuri']
    FILAS8 = [fila('2026-10-12', 'vivienda', 'Rafa', 7.5),
              fila('2026-10-21', 'vivienda', 'Mikel', 7.5), fila('2026-10-21', 'vivienda', 'Txomin', 7.5),
              fila('2026-10-22', 'vivienda', 'Mikel', 7.5), fila('2026-10-22', 'vivienda', 'Txomin', 7.5),
              fila('2026-10-16', 'garaje', 'Andoni', 7.5)]

    def est8(filas=None, catalogo=None, excep=None, ultima_viv=None):
        """Obra Olabeaga con Mikel y Txomin en la última jornada de viviendas; Zuri está de baja (activo: false)."""
        e8 = estado_con({
            'olabeaga': obra_est('2026 OLABEAGA', FILAS8 if filas is None else filas, excep=excep, ultima={
                'vivienda': ultima_viv or {'fecha': '2026-10-22', 'presentes': pres('Mikel', 'Txomin')},
                'garaje': {'fecha': '2026-10-16', 'presentes': pres('Andoni')}}),
            'mungia': obra_est('2026 MUNGIA', [fila('2026-10-21', 'vivienda', 'Pepe', 7.5)],
                               ultima={'vivienda': {'fecha': '2026-10-21', 'presentes': pres('Pepe')}, 'garaje': None})},
            CAT8 if catalogo is None else catalogo)
        for t in e8['catalogo']:
            if t['nombre'] == 'Zuri':
                t['activo'] = False
        return e8

    def sembrar_varios(claves):
        """Como sembrar(), pero con varias claves de localStorage a la vez (solo en la primera carga)."""
        ordenes = ''.join("localStorage.setItem('%s',%s);" % (k, json.dumps(json.dumps(v))) for k, v in claves.items())
        return "if(!localStorage.getItem('_s')){localStorage.setItem('_s','1');%s}" % ordenes

    def ls(e, clave):
        return e.pg.evaluate("k=>JSON.parse(localStorage.getItem(k)||'null')", 'sgd_personal_' + clave)

    def opciones(e):
        return e.pg.eval_on_selector_all('#addsel option', 'e=>e.map(o=>[o.textContent.trim(),o.disabled])')

    def nombres_opciones(e):
        return [o[0] for o in opciones(e)]

    def lapiz(nombre):
        return '#v-app .row[data-nombre="%s"] button[data-ren]' % nombre

    def renombra(e, de, nuevo, si=True):
        """Abre el lápiz de `de`, escribe el nombre nuevo, pulsa «Guardar» y, si pregunta, «Sí…»."""
        e.clic(lapiz(de))
        e.pg.fill('#ren-campo', nuevo)
        e.clic('button[data-ren-guardar]')
        if si and e.pg.query_selector('button[data-ren-si]'):
            e.clic('button[data-ren-si]')

    def cambios(e):
        return e.txt('#cambios-nombres')

    def lote_de_filas(obra, filas, excep=None):
        grupos = {}
        for f in filas:
            grupos.setdefault((f['ambito'], f['fecha']), []).append({'nombre': f['nombre'], 'horas': f['horas'], 'extra': f.get('extra', 0)})
        lote = {'tipo': 'lote_personal', 'version': 1, 'obra': obra, 'jornadas': [
            {'ambito': am, 'fecha': fe, 'presentes': pr, 'anulada': False, 'notas': '', 'registrado': fe + 'T18:00:00.000Z'}
            for (am, fe), pr in sorted(grupos.items(), key=lambda x: x[0][1])]}
        if excep:
            lote['excepciones_horario'] = excep
        return lote

    def e2e_p1(lote, filas=None, excep=None):
        """Aplica DE VERDAD el fichero de la app sobre un PC de pruebas que ya tiene lo publicado (las filas del estado).
        Devuelve (resultado, catálogo, filas planas de Olabeaga); (None, None, None) si no se pudo cargar P1."""
        if P1 is None:
            return None, None, None
        raiz = os.path.join(SANDBOX, 'pc_' + uuid.uuid4().hex[:6])
        os.makedirs(raiz)
        obras = {'olabeaga': '2026 OLABEAGA BILBAO'}
        r0 = P1.ingerir_lote(lote_de_filas('olabeaga', FILAS8 if filas is None else filas, excep), raiz, obras, '2026-10-23',
                             escribir=True, ahora='2026-10-22T22:00:00+02:00')
        ok(r0['ok'], 'e2e: el PC de pruebas no se pudo preparar: %s' % json.dumps(r0, ensure_ascii=False)[:300])
        r = P1.ingerir_lote(copy.deepcopy(lote), raiz, obras, '2026-10-23', escribir=True, ahora='2026-10-23T22:00:00+02:00')
        return r, P1.cargar_catalogo(raiz), P1.aplanar(raiz, obras, 'olabeaga')

    def codigos_avisos(r):
        return [x['codigo'] for x in r.get('avisos_lote', [])] + [x['codigo'] for j in r.get('jornadas', []) for x in j.get('avisos', [])]

    # --- T80: «Añadir de la base» lista TODA la base activa (D4)
    def t80(e):
        e.ir()
        ok(e.filas() == ['Mikel', 'Txomin'], 'T80 lista de partida: %s' % e.filas())
        todos = [['Andoni', False], ['Iñaki', False], ['José', False], ['Josu', False], ['Mikel (ya está)', True], ['Pepe', False], ['Rafa', False], ['Txomin (ya está)', True]]
        ok(opciones(e) == todos, 'T80 el desplegable debe listar TODA la base activa por orden alfabético, con «(ya está)» (y sin poder elegirse) en quien ya sale en pantalla, y sin Zuri (de baja): %s' % opciones(e))
        ok(e.valor('#addsel') == 'Andoni', 'T80 queda seleccionada la primera persona que se puede añadir: %r' % e.valor('#addsel'))
        for q, esperado in (('jose', ['José']), ('JOSÉ', ['José']), ('inaki', ['Iñaki']), ('IÑAKI', ['Iñaki']), ('jos', ['José', 'Josu']),
                            ('mik', ['Mikel (ya está)']), ('zzz', []), ('zuri', [])):
            e.pg.fill('#filtro', q)
            ok(nombres_opciones(e) == esperado, 'T80 el buscador (sin distinguir tildes ni mayúsculas) con «%s» debe dejar %s: %s' % (q, esperado, nombres_opciones(e)))
        e.pg.fill('#filtro', 'mik')
        ok(e.valor('#addsel') == '', 'T80 si solo quedan personas que ya están, no queda nada seleccionado: %r' % e.valor('#addsel'))
        e.clic('button[data-add]')
        ok(e.filas() == ['Mikel', 'Txomin'] and e.marcados() == [], 'T80 «Añadir» sin nadie que se pueda añadir no hace nada: %s %s' % (e.filas(), e.marcados()))
        e.pg.fill('#filtro', '')
        e.pg.evaluate("document.getElementById('addsel').value='Txomin'")
        ok(e.valor('#addsel') == 'Txomin', 'T80 preparación: se ha podido forzar la opción desactivada: %r' % e.valor('#addsel'))
        e.clic('button[data-add]')
        ok(e.filas() == ['Mikel', 'Txomin'] and e.marcados() == [], 'T80 quien ya está en pantalla no se añade otra vez ni se marca desde el desplegable, aunque se fuerce el valor: %s %s' % (e.filas(), e.marcados()))
        e.pg.select_option('#addsel', 'Andoni')
        e.clic('button[data-add]')
        ok(e.filas() == ['Mikel', 'Txomin', 'Andoni'] and e.marcados() == ['Andoni'], 'T80 añadir de la base pone a la persona en la lista y marcada: %s %s' % (e.filas(), e.marcados()))
        ok(['Andoni (ya está)', True] in opciones(e) and len(opciones(e)) == 8, 'T80 tras añadir, esa persona pasa a «(ya está)» y la base sigue completa (8): %s' % opciones(e))
        e.clic('button[data-amb="garaje"]')
        d = dict(opciones(e))
        ok(e.filas() == ['Andoni'] and d.get('Andoni (ya está)') is True and d.get('Mikel') is False and d.get('Txomin') is False and len(d) == 8, 'T80 el desplegable sigue a la lista de pantalla (garajes): %s' % opciones(e))
        e.clic('button[data-amb="vivienda"]')
        e.obra('mungia')
        d = dict(opciones(e))
        ok(e.filas() == ['Pepe'] and d.get('Pepe (ya está)') is True and d.get('Andoni') is False and len(d) == 8, 'T80 y a la de la otra obra: %s %s' % (e.filas(), opciones(e)))
        e.pg.fill('#nuevo', 'Begoña')
        e.clic('button[data-nuevo]')
        ok(['Begoña (ya está)', True] in opciones(e), 'T80 un nombre recién creado también sale en el desplegable (y como «ya está» mientras esté en pantalla): %s' % nombres_opciones(e))
    con_escena('T80', est8(), t80)

    # --- T81: «Añadir varios nombres»: un nombre por línea, resumen, y viajan en el fichero como altas (D4)
    def t81(e):
        e.ir()
        ok(e.pg.query_selector('#varios') is None and e.pg.query_selector('#cambios-nombres') is None, 'T81 el cuadro de varios nombres empieza cerrado y sin contador de cambios')
        ok('Añadir varios nombres' in e.txt('button[data-varios]'), 'T81 falta el botón «Añadir varios nombres» (button[data-varios]): %r' % e.txt('button[data-varios]'))
        e.clic('button[data-varios]')
        ok(e.pg.query_selector('#varios textarea#varios-texto') is not None and e.pg.query_selector('button[data-varios-ok]') is not None and e.pg.query_selector('button[data-varios-cerrar]') is not None, 'T81 el cuadro lleva textarea#varios-texto y los botones data-varios-ok y data-varios-cerrar')
        ok('Añadir a la base' in e.txt('button[data-varios-ok]') and 'Cerrar' in e.txt('button[data-varios-cerrar]'), 'T81 textos de los botones: %r %r' % (e.txt('button[data-varios-ok]'), e.txt('button[data-varios-cerrar]')))
        ok('un nombre en cada línea' in e.txt('#varios').lower(), 'T81 explica que va un nombre en cada línea: %r' % e.txt('#varios'))
        largo = 'N' * 61
        lineas = ['Ane', '', '  Iker  ', 'ane', 'Mikel', 'rafa', 'Jon   Ander', 'Iker', 'x@y.es', '12345678Z', '600123456', '<b>x</b>', largo, 'Mikell', 'Al', '   ']
        e.pg.fill('#varios-texto', '\n'.join(lineas))
        e.clic('button[data-varios-ok]')
        ok(e.txt('[data-res="entran"]') == 'Entran 4: Ane, Iker, Jon Ander, Al.', 'T81 resumen de los que entran (limpios, sin repetidos ni líneas vacías): %r' % e.txt('[data-res="entran"]'))
        ok(e.txt('[data-res="estaban"]') == 'Ya estaban 2: Mikel, Rafa.', 'T81 resumen de los que ya estaban (con la grafía de la base): %r' % e.txt('[data-res="estaban"]'))
        ok(e.txt('[data-res="novalen"]') == 'No valen 5: «x@y.es» (parece un correo); «12345678Z» (parece un DNI); «600123456» (parece un teléfono); «<b>x</b>» (lleva los signos < o >); «%s» (tiene más de 60 letras).' % largo, 'T81 resumen de los que no valen, cada uno con su motivo: %r' % e.txt('[data-res="novalen"]'))
        ok(e.txt('[data-res="parecidos"]') == 'Se parece a alguien que ya está 1: «Mikell» (se parece a «Mikel»). Si es otra persona, créala con «Nombre nuevo».', 'T81 resumen de los parecidos: %r' % e.txt('[data-res="parecidos"]'))
        ok(e.pg.evaluate("document.querySelectorAll('#varios-resumen [data-res] *').length") == 0, 'T81 los nombres del resumen salen como texto, sin crear elementos (se escapan)')
        ok(e.valor('#varios-texto') == '\n'.join(['x@y.es', '12345678Z', '600123456', '<b>x</b>', largo, 'Mikell']), 'T81 en el cuadro solo quedan las líneas que NO entraron y hay que corregir (no valen y parecidos): %r' % e.valor('#varios-texto'))
        ok(ls(e, 'altas') == ['Ane', 'Iker', 'Jon Ander', 'Al'], 'T81 los que entran se apuntan en sgd_personal_altas: %s' % ls(e, 'altas'))
        ok(all(n in (ls(e, 'nuevos') or []) for n in ('Ane', 'Iker', 'Jon Ander', 'Al')), 'T81 y se guardan como nombres nuevos del aparato: %s' % ls(e, 'nuevos'))
        nombres = [n for n in nombres_opciones(e)]
        ok(all(n in nombres for n in ('Al', 'Ane', 'Iker', 'Jon Ander')) and not any(n.startswith(('x@', 'Mikell', '<')) for n in nombres), 'T81 los que entran quedan disponibles en el desplegable, y solo ellos: %s' % nombres)
        ok(e.filas() == ['Mikel', 'Txomin'], 'T81 entrar en la base no mete a nadie en la lista de pantalla: %s' % e.filas())
        ok(cambios(e) == '4 nombres nuevos sin enviar al PC', 'T81 contador de cambios por pasar al PC: %r' % cambios(e))
        e.pg.fill('#varios-texto', 'ane\nBegoña\n')
        e.clic('button[data-varios-ok]')
        ok(e.txt('[data-res="estaban"]') == 'Ya estaba 1: Ane.' and e.txt('[data-res="entran"]') == 'Entra 1: Begoña.' and e.valor('#varios-texto') == '', 'T81 singular y vaciado del cuadro: %r %r %r' % (e.txt('[data-res="estaban"]'), e.txt('[data-res="entran"]'), e.valor('#varios-texto')))
        e.pg.fill('#varios-texto', '  \n\n   ')
        e.clic('button[data-varios-ok]')
        ok(e.txt('[data-res="nada"]') == 'No hay ningún nombre que añadir.' and ls(e, 'altas') == ['Ane', 'Iker', 'Jon Ander', 'Al', 'Begoña'], 'T81 un cuadro vacío lo dice y no apunta nada: %r %s' % (e.txt('[data-res="nada"]'), ls(e, 'altas')))
        e.clic('button[data-varios-cerrar]')
        ok(e.pg.query_selector('#varios') is None and ls(e, 'altas') is not None and cambios(e) == '5 nombres nuevos sin enviar al PC', 'T81 «Cerrar» esconde el cuadro y no pierde nada: %r' % cambios(e))
        lote = e.exportar() or {}
        ok(set(lote) == {'tipo', 'version', 'obra', 'altas', 'jornadas'} and lote.get('altas') == ['Ane', 'Iker', 'Jon Ander', 'Al', 'Begoña'] and lote.get('jornadas') == [], 'T81 con solo nombres nuevos el fichero lleva altas y ninguna jornada: %s' % {k: lote.get(k) for k in lote})
        valida_con_p1(lote)
        r, cat8, filas8 = e2e_p1(lote)
        ok(r is not None and r['ok'] and sorted(x['nombre'] for x in r['altas']) == ['Al', 'Ane', 'Begoña', 'Iker', 'Jon Ander'], 'T81 el PC da de alta a los 5 sin jornada: %s' % (json.dumps(r, ensure_ascii=False)[:400] if r else r))
        ok(r is not None and not any(f['nombre'] in ('Al', 'Ane', 'Iker', 'Begoña', 'Jon Ander') for f in filas8), 'T81 y no les inventa ninguna jornada')
        ok('con 5 nombres nuevos' in e.listo(), 'T81 (08d) el recuadro «Listo» cuenta los nombres nuevos: %r' % e.listo())
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        ok(ls(e, 'altas') == ['Ane', 'Iker', 'Jon Ander', 'Al', 'Begoña'] and 'Ane' in nombres_opciones(e), 'T81 al recargar siguen apuntados y disponibles: %s' % ls(e, 'altas'))
    con_escena('T81', est8(), t81)

    def t81b(e):
        e.ir()
        ok(ls(e, 'altas') == ['Ane'], 'T81b al abrir, el nombre que el PC ya publicó (Josu) se olvida de lo que falta por enviar y el otro se conserva: %s' % ls(e, 'altas'))
        ok(cambios(e) == '1 nombre nuevo sin enviar al PC', 'T81b contador en singular: %r' % cambios(e))
    con_escena('T81b', est8(), t81b, init=sembrar_varios({'sgd_personal_altas': ['Ane', 'Josu'], 'sgd_personal_nuevos': ['Ane', 'Josu']}))

    def t81c(e):
        e.ir()
        e.clic('button[data-varios]')
        e.pg.fill('#varios-texto', chr(10).join(['Zé &lt;i&gt;', 'Tom &amp; Jerry']))
        e.clic('button[data-varios-ok]')
        ok(e.txt('[data-res="entran"]') == 'Entran 2: Zé &lt;i&gt;, Tom &amp; Jerry.', 'T81c el resumen enseña los nombres tal como se escribieron (un nombre con &lt; o &amp; no se interpreta): %r' % e.txt('[data-res="entran"]'))
        ok(e.pg.evaluate("document.querySelectorAll('#varios-resumen [data-res] *').length") == 0, 'T81c y sin crear elementos')
    con_escena('T81c', est8(), t81c)

    # --- T82: el lápiz ✎ corrige un nombre en TODO lo que hay en el aparato y lo apunta para el PC (D3)
    def t82(e):
        e.ir()
        ok(e.pg.eval_on_selector_all('#v-app .row', 'e=>e.length>0&&e.every(r=>r.querySelector("button[data-ren]"))'), 'T82 cada persona de la lista lleva su lápiz (button[data-ren])')
        ok('✎' in e.txt(lapiz('Mikel')) and 'Mikel' in (e.pg.get_attribute(lapiz('Mikel'), 'aria-label') or ''), 'T82 el lápiz se ve como ✎ y su aria-label dice de quién es: %r %r' % (e.txt(lapiz('Mikel')), e.pg.get_attribute(lapiz('Mikel'), 'aria-label')))
        e.anotar('Mikel')
        e.anotar('Rafa')
        ok(e.filas() == ['Mikel', 'Txomin', 'Rafa'] and e.marcados() == ['Mikel', 'Rafa'], 'T82 preparación: %s %s' % (e.filas(), e.marcados()))
        e.clic(lapiz('Rafa'))
        ok(e.valor('#ren-campo') == 'Rafa' and e.pg.evaluate("document.activeElement.id") == 'ren-campo', 'T82 el lápiz abre un campo con el nombre actual y el cursor dentro: %r' % e.valor('#ren-campo'))
        ok(e.txt('button[data-ren-guardar]') == 'Guardar' and 'Cancelar' in e.txt('button[data-ren-cancelar]') and e.pg.evaluate("document.querySelectorAll('#ren-campo').length") == 1, 'T82 el campo lleva «Guardar» (guarda nombre y empresa) y «Cancelar»: %r %r' % (e.txt('button[data-ren-guardar]'), e.txt('button[data-ren-cancelar]')))
        e.clic('button[data-ren-cancelar]')
        ok(e.pg.query_selector('#ren-campo') is None and e.filas() == ['Mikel', 'Txomin', 'Rafa'] and not ls(e, 'renombres') and e.pg.query_selector('#cambios-nombres') is None, 'T82 «Cancelar» cierra el campo sin cambiar nada: %s %s' % (e.filas(), ls(e, 'renombres')))
        e.clic(lapiz('Rafa'))
        e.pg.fill('#ren-campo', 'Rafa')
        e.clic('button[data-ren-guardar]')
        ok(e.pg.query_selector('#ren-campo') is None and not ls(e, 'renombres'), 'T82 guardar el mismo nombre cierra el campo y no apunta nada: %s' % ls(e, 'renombres'))
        e.clic(lapiz('Rafa'))
        e.pg.fill('#ren-campo', '  Rafael  ')
        e.clic('button[data-ren-guardar]')
        ok(e.filas() == ['Mikel', 'Txomin', 'Rafael'] and e.marcados() == ['Mikel', 'Rafael'] and e.horas('Rafael') == '7,5 h', 'T82 el nombre cambia en la lista (limpio, en el mismo sitio y conservando marca y horas): %s %s %s' % (e.filas(), e.marcados(), e.horas('Rafael')))
        ok(e.txt('#toast') == 'Nombre corregido: «Rafa» ahora es «Rafael». Queda apuntado para el PC.', 'T82 aviso: %r' % e.txt('#toast'))
        ok(ls(e, 'renombres') == [{'de': 'Rafa', 'a': 'Rafael'}], 'T82 se apunta el renombre {de, a} con el nombre limpio de espacios: %s' % ls(e, 'renombres'))
        ok(cambios(e) == '1 nombre corregido sin enviar al PC', 'T82 contador: %r' % cambios(e))
        ok(['Rafael (ya está)', True] in opciones(e) and 'Rafa' not in nombres_opciones(e), 'T82 el desplegable ya trae el nombre nuevo: %s' % nombres_opciones(e))
        ok(ls(e, 'borrador')['lista'][2]['nombre'] == 'Rafael', 'T82 el borrador guardado lleva el nombre nuevo: %s' % ls(e, 'borrador'))
        e.clic('button[data-guardar]')
        ok([p['nombre'] for p in ls(e, 'pendientes')[0]['presentes']] == ['Mikel', 'Rafael'], 'T82 la jornada guardada lleva el nombre nuevo: %s' % ls(e, 'pendientes'))
        e.clic('button[data-v="informe"]')
        fi = e.informe()
        ok('Rafael' in [f.split(' ')[0] for f in fi] and 'Rafa' not in [f.split(' ')[0] for f in fi] and tokens(fi, 'Rafael')[1] == '2', 'T82 el informe cuenta las jornadas ya publicadas de Rafa bajo el nombre nuevo (1 publicada + la de hoy = 2 días): %s' % fi)
        e.clic('button[data-v="app"]')
        lote = e.exportar() or {}
        ok(set(lote) == {'tipo', 'version', 'obra', 'renombres', 'jornadas'} and lote.get('renombres') == [{'de': 'Rafa', 'a': 'Rafael'}], 'T82 el fichero lleva el renombre dentro: %s' % {k: lote.get(k) for k in lote})
        ok([p['nombre'] for p in lote.get('jornadas', [{}])[0].get('presentes', [])] == ['Mikel', 'Rafael'], 'T82 y la jornada con el nombre nuevo: %s' % lote.get('jornadas'))
        valida_con_p1(lote)
        r, cat8, filas8 = e2e_p1(lote)
        ok(r is not None and r['ok'] and r['renombres'][0]['accion'] == 'renombrado' and 'alta_nueva' not in codigos_avisos(r), 'T82 el PC lo aplica como un cambio de nombre y NO da de alta a nadie nuevo: %s' % (json.dumps(r, ensure_ascii=False)[:500] if r else r))
        if r is not None:
            p = [t for t in cat8['trabajadores'] if t['nombre'] == 'Rafael']
            ok(len(p) == 1 and p[0].get('nombres_anteriores') == ['Rafa'], 'T82 la misma persona conserva su nombre anterior: %s' % p)
            ok(sorted((f['fecha'], f['nombre']) for f in filas8 if f['nombre'] in ('Rafael', 'Rafa')) == [('2026-10-12', 'Rafael'), ('2026-10-23', 'Rafael')], 'T82 sus jornadas, las de antes y la nueva, quedan bajo el nombre nuevo: %s' % [f for f in filas8 if 'af' in f['nombre']])
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        ok('Rafael' in e.filas() and 'Rafa' not in e.filas() and ls(e, 'renombres') == [{'de': 'Rafa', 'a': 'Rafael'}], 'T82 al recargar (el PC aún no ha publicado nada) el nombre nuevo sigue en pantalla y apuntado: %s %s' % (e.filas(), ls(e, 'renombres')))
        e.clic('button[data-v="informe"]')
        ok('Rafael' in [f.split(' ')[0] for f in e.informe()] and 'Rafa' not in [f.split(' ')[0] for f in e.informe()], 'T82 y el informe lo sigue viendo con el nombre nuevo: %s' % e.informe())
    con_escena('T82', est8(), t82)

    # --- T82b: el campo se niega a guardar lo que el PC rechazaría; no se pierde lo escrito
    def t82b(e):
        e.ir()
        casos = (('', 'Escribe el nombre.'), ('   ', 'Escribe el nombre.'), ('rafa@x.com', 'Ese nombre no vale: parece un correo.'),
                 ('12345678Z', 'Ese nombre no vale: parece un DNI.'), ('X1234567L', 'Ese nombre no vale: parece un NIE.'), ('600123456', 'Ese nombre no vale: parece un teléfono.'),
                 ('Rafa <b>', 'Ese nombre no vale: lleva los signos < o >.'), ('N' * 61, 'Ese nombre no vale: tiene más de 60 letras.'),
                 ('Ra\u0007fa', 'Ese nombre no vale: lleva caracteres raros.'))
        e.anotar('Rafa')
        e.clic(lapiz('Rafa'))
        for valor, mensaje in casos:
            e.pg.evaluate("v=>{const i=document.getElementById('ren-campo');i.value=v;i.dispatchEvent(new Event('input',{bubbles:true}))}", valor)
            e.clic('button[data-ren-guardar]')
            ok(e.txt('#ren-error') == mensaje and e.valor('#ren-campo') == valor and e.filas() == ['Mikel', 'Txomin', 'Rafa'] and not ls(e, 'renombres'), 'T82b «%s» debe dar «%s», dejar el campo como estaba y no cambiar nada: %r %r' % (valor[:20], mensaje, e.txt('#ren-error'), e.valor('#ren-campo')))
        e.pg.fill('#ren-campo', 'Rafael')
        e.pg.keyboard.press('Enter')
        ok(e.pg.query_selector('#ren-campo') is None and e.pg.query_selector('#ren-error') is None and 'Rafael' in e.filas(), 'T82b con un nombre bueno se guarda (también con Intro) y desaparece el error: %s' % e.filas())
        e.pg.fill('#nuevo', 'x@y.es')
        e.clic('button[data-nuevo]')
        ok('Ese nombre no vale: parece un correo.' in e.txt('#nuevo-aviso') and 'x@y.es' not in e.filas(), 'T82b «Nombre nuevo» aplica las mismas reglas: %r %s' % (e.txt('#nuevo-aviso'), e.filas()))
    con_escena('T82b', est8(), t82b)

    # --- T83: si el nombre nuevo ya es de otra persona, se pregunta y, con «Sí», se apunta para juntarlos en el PC
    def t83(e):
        e.ir()
        e.anotar('Mikel')
        e.clic(lapiz('Txomin'))
        e.pg.fill('#ren-campo', 'mikel')
        e.clic('button[data-ren-guardar]')
        ok(e.txt('#ren-pregunta [data-texto]') == 'Ya hay un «Mikel». ¿Son la misma persona? Se juntarán al pasarlo al PC, con vista previa antes.', 'T83 la pregunta: %r' % e.txt('#ren-pregunta [data-texto]'))
        ok('Sí, son la misma persona' in e.txt('button[data-ren-si]') and e.txt('button[data-ren-no]') == 'No', 'T83 botones de la pregunta: %r %r' % (e.txt('button[data-ren-si]'), e.txt('button[data-ren-no]')))
        ok(e.filas() == ['Mikel', 'Txomin'] and not ls(e, 'renombres'), 'T83 hasta que se contesta no cambia nada: %s %s' % (e.filas(), ls(e, 'renombres')))
        e.clic('button[data-ren-no]')
        ok(e.pg.query_selector('#ren-pregunta') is None and e.valor('#ren-campo') == 'mikel' and e.filas() == ['Mikel', 'Txomin'] and not ls(e, 'renombres'), 'T83 «No» no apunta nada: cierra la pregunta y deja el campo para cambiar el nombre: %s' % ls(e, 'renombres'))
        e.clic('button[data-ren-guardar]')
        e.clic('button[data-ren-si]')
        ok(e.filas() == ['Mikel'] and e.marcados() == ['Mikel'], 'T83 con «Sí» las dos filas pasan a ser una, con el nombre de la base: %s %s' % (e.filas(), e.marcados()))
        ok(ls(e, 'renombres') == [{'de': 'Txomin', 'a': 'Mikel'}], 'T83 se apunta con la grafía que ya tiene la base: %s' % ls(e, 'renombres'))
        ok(e.txt('#toast') == '«Txomin» y «Mikel» pasan a ser la misma persona. Se juntarán al pasarlo al PC.', 'T83 aviso: %r' % e.txt('#toast'))
        e.clic('button[data-v="informe"]')
        fi = e.informe()
        ok('Txomin' not in [f.split(' ')[0] for f in fi] and tokens(fi, 'Mikel')[1] == '2' and tokens(fi, 'Mikel')[2] == '15', 'T83 en el informe, sus días y horas no se duplican (las dos anotaciones del mismo día cuentan una vez): %s' % fi)
        e.clic('button[data-v="app"]')
        lote = e.exportar() or {}
        ok(lote.get('renombres') == [{'de': 'Txomin', 'a': 'Mikel'}] and lote.get('jornadas') == [], 'T83 el fichero lleva el renombre: %s' % {k: lote.get(k) for k in lote})
        valida_con_p1(lote)
        r, cat8, filas8 = e2e_p1(lote)
        ok(r is not None and not r['lote_rechazado'] and r['renombres'][0]['accion'] == 'coincide_con_otro' and 'fusionar' in (r['renombres'][0]['orden'] or '') and 'renombre_coincide_con_otro' in codigos_avisos(r), 'T83 el PC no lo aplica solo: avisa y da la orden de fusionar: %s' % (json.dumps(r, ensure_ascii=False)[:500] if r else r))
    con_escena('T83', est8(), t83)

    def t83b(e):
        e.ir()
        e.anotar('Txomin')
        e.pulsar('Txomin', 1, '0.5')
        renombra(e, 'Txomin', 'MIKEL')
        ok(e.filas() == ['Mikel'] and e.marcados() == ['Mikel'] and e.horas('Mikel') == '8 h', 'T83b si solo estaba marcado el renombrado, la fila que queda conserva su marca y sus horas: %s %s %s' % (e.filas(), e.marcados(), e.horas('Mikel')))
        e.clic('button[data-guardar]')
        renombra(e, 'Mikel', 'Mikel B')
        ok(ls(e, 'renombres') == [{'de': 'Txomin', 'a': 'Mikel'}, {'de': 'Mikel', 'a': 'Mikel B'}], 'T83b corregir luego el nombre de quien ya existía en la base NO se junta con el apunte anterior (son dos personas distintas para el PC hasta que las junte): %s' % ls(e, 'renombres'))
    con_escena('T83b', est8(), t83b)

    def t83c(e):
        e.ir()
        e.clic('button[data-todos="1"]')
        e.pulsar('Txomin', 2, '0.5')
        e.clic('button[data-guardar]')
        renombra(e, 'Txomin', 'Mikel')
        pj = ls(e, 'pendientes')
        ok(e.filas() == ['Mikel'] and [p['nombre'] for p in pj[0]['presentes']] == ['Mikel'] and pj[0]['presentes'][0]['horas'] == 7.5, 'T83c una jornada guardada en la que salían los dos se queda con una sola anotación, la de quien ya tenía ese nombre: %s' % pj)
        ok('salían los dos' in e.txt('#toast'), 'T83c y se avisa de ello: %r' % e.txt('#toast'))
        valida_con_p1(e.exportar() or {})
    con_escena('T83c', est8(), t83c)

    # --- T84: el nombre cambia también en la memoria de horarios propios, que va por nombre
    def t84(e):
        e.ir()
        e.anotar('Aitor')
        e.anotar('Gorka')
        guardar_propio(e, 'Gorka', {'vie': 9})
        ok(json.loads(propio_ls(e) or '{}') == {'olabeaga': {'Gorka': {'vie': 9}}}, 'T84 preparación: solo Gorka tiene un horario propio recordado (el de Aitor es el publicado): %r' % propio_ls(e))
        renombra(e, 'Gorka', 'Gorka B')
        ok(json.loads(propio_ls(e) or '{}') == {'olabeaga': {'Gorka B': {'vie': 9}}} and chip(e, 'Gorka B', True) == 'horario especial 9 h', 'T84 el horario propio recordado sigue a la persona con su nombre nuevo: %r %r' % (propio_ls(e), chip(e, 'Gorka B', True)))
        renombra(e, 'Aitor', 'Aitor Z')
        ok(chip(e, 'Aitor Z', True) == 'horario especial 9 h' and json.loads(propio_ls(e) or '{}') == {'olabeaga': {'Gorka B': {'vie': 9}}}, 'T84 el horario propio PUBLICADO de Aitor también sigue a su nombre nuevo, sin inventar nada que enviar: %r %r' % (chip(e, 'Aitor Z', True), propio_ls(e)))
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        ok(lote.get('excepciones_horario') == {'Gorka B': {'vie': 9}} and lote.get('renombres') == [{'de': 'Gorka', 'a': 'Gorka B'}, {'de': 'Aitor', 'a': 'Aitor Z'}], 'T84 el fichero lleva los dos renombres (en orden) y solo el horario propio nuevo: %s' % {k: lote.get(k) for k in lote})
        valida_con_p1(lote)
        r, cat8, filas8 = e2e_p1(lote, FILAS8 + [fila('2026-10-20', 'vivienda', 'Aitor', 9), fila('2026-10-20', 'vivienda', 'Gorka', 7.5)], {'Aitor': {'vie': 9}})
        ok(r is not None and r['ok'] and [x['accion'] for x in r['renombres']] == ['renombrado', 'renombrado'] and 'alta_nueva' not in codigos_avisos(r), 'T84 el PC aplica los dos cambios de nombre y no da de alta a nadie: %s' % (json.dumps(r, ensure_ascii=False)[:500] if r else r))
    con_escena('T84', est8(catalogo=CAT8 + ['Aitor', 'Gorka'], excep={'Aitor': {'vie': 9}}), t84)

    # --- T85: lo apuntado se olvida cuando el estado publicado ya lo trae; si no, se reaplica al abrir
    def t85a(e):
        e.ir()
        ok('Rafael' in nombres_opciones(e) and 'Rafa' not in nombres_opciones(e) and ls(e, 'renombres') == [{'de': 'Rafa', 'a': 'Rafael'}] and cambios(e) == '1 nombre corregido sin enviar al PC', 'T85a el PC aún no lo ha hecho: al abrir se ve el nombre nuevo y sigue apuntado: %s %s' % (nombres_opciones(e), ls(e, 'renombres')))
        e.clic('button[data-v="informe"]')
        ok('Rafael' in [f.split(' ')[0] for f in e.informe()] and 'Rafa' not in [f.split(' ')[0] for f in e.informe()], 'T85a y el informe ya lo ve con el nombre nuevo: %s' % e.informe())
    con_escena('T85a', est8(), t85a, init=sembrar('sgd_personal_renombres', [{'de': 'Rafa', 'a': 'Rafael'}]))

    def t85b(e):
        e.ir()
        ok(not ls(e, 'renombres') and e.pg.query_selector('#cambios-nombres') is None, 'T85b el estado publicado ya trae «Rafael» y no «Rafa»: el renombre apuntado se olvida: %s' % ls(e, 'renombres'))
    filas85 = [dict(f, nombre='Rafael') if f['nombre'] == 'Rafa' else f for f in FILAS8]
    con_escena('T85b', est8(filas=filas85, catalogo=['Rafael' if n == 'Rafa' else n for n in CAT8]), t85b, init=sembrar('sgd_personal_renombres', [{'de': 'Rafa', 'a': 'Rafael'}]))

    def t85i(e):
        e.ir()
        ok(not ls(e, 'renombres') and e.pg.query_selector('#cambios-nombres') is None, 'T85i el PC ya hizo el cambio (trae «Rafael» y ya no «Rafa»): se olvida aunque una jornada guardada siga llevando el nombre nuevo: %s' % ls(e, 'renombres'))
    pj85i = [{'obra': 'olabeaga', 'ambito': 'vivienda', 'fecha': '2026-10-23', 'presentes': [{'nombre': 'Rafael', 'horas': 8, 'extra': 0.5}], 'anulada': False, 'notas': '', 'registrado': '2026-10-23T08:00:00.000Z'}]
    con_escena('T85i', est8(filas=filas85, catalogo=['Rafael' if n == 'Rafa' else n for n in CAT8]), t85i,
               init=sembrar_varios({'sgd_personal_renombres': [{'de': 'Rafa', 'a': 'Rafael'}], 'sgd_personal_pendientes': pj85i}))

    def t85c(e):
        e.ir()
        ok(ls(e, 'renombres') == [{'de': 'Txomin', 'a': 'Mikel'}] and e.filas() == ['Mikel'], 'T85c si el estado publicado trae a las dos personas (aún sin juntar), se conserva lo apuntado y se ve ya como una: %s %s' % (ls(e, 'renombres'), e.filas()))
    con_escena('T85c', est8(), t85c, init=sembrar('sgd_personal_renombres', [{'de': 'Txomin', 'a': 'Mikel'}]))

    def t85d(e):
        e.ir()
        ok(not ls(e, 'renombres'), 'T85d un renombre de un nombre que el PC no conoce y que ninguna jornada ni alta lleva no tiene nada que enviar y se olvida: %s' % ls(e, 'renombres'))
    con_escena('T85d', est8(), t85d, init=sembrar('sgd_personal_renombres', [{'de': 'Fantasma', 'a': 'Fantasma 2'}]))

    def t85e(e):
        e.ir()
        ok(ls(e, 'renombres') == [{'de': 'Fantasma', 'a': 'Fantasma 2'}], 'T85e pero si una jornada guardada lleva el nombre nuevo, se conserva (puede que el PC ya tenga al antiguo por un envío anterior): %s' % ls(e, 'renombres'))
    pj85 = [{'obra': 'olabeaga', 'ambito': 'vivienda', 'fecha': '2026-10-22', 'presentes': [{'nombre': 'Fantasma 2', 'horas': 7.5, 'extra': 0}], 'anulada': False, 'notas': '', 'registrado': '2026-10-22T18:00:00.000Z'}]
    con_escena('T85e', est8(), t85e, init=sembrar_varios({'sgd_personal_renombres': [{'de': 'Fantasma', 'a': 'Fantasma 2'}], 'sgd_personal_pendientes': pj85}))

    def t85f(e):
        e.ir()
        renombra(e, 'Mikel', 'Miguel')
        renombra(e, 'Miguel', 'Mikelo')
        ok(ls(e, 'renombres') == [{'de': 'Mikel', 'a': 'Mikelo'}], 'T85f dos cambios seguidos sobre la misma persona se apuntan como uno: de lo que conoce el PC al último nombre: %s' % ls(e, 'renombres'))
        renombra(e, 'Txomin', 'Txomín')
        ok(ls(e, 'renombres') == [{'de': 'Mikel', 'a': 'Mikelo'}, {'de': 'Txomin', 'a': 'Txomín'}] and cambios(e) == '2 nombres corregidos sin enviar al PC', 'T85f y dos personas distintas, dos apuntes en orden: %s %r' % (ls(e, 'renombres'), cambios(e)))
        renombra(e, 'Mikelo', 'Mikel')
        ok(ls(e, 'renombres') == [{'de': 'Txomin', 'a': 'Txomín'}] and e.filas() == ['Mikel', 'Txomín'], 'T85f si se vuelve al nombre de antes de todo, ya no hay nada que apuntar de esa persona: %s %s' % (ls(e, 'renombres'), e.filas()))
        renombra(e, 'Mikel', 'mikel')
        ok(ls(e, 'renombres') == [{'de': 'Txomin', 'a': 'Txomín'}, {'de': 'Mikel', 'a': 'mikel'}], 'T85f cambiar solo mayúsculas o tildes también es un cambio que hay que apuntar: %s' % ls(e, 'renombres'))
    con_escena('T85f', est8(), t85f)

    def t85g(e):
        e.ir()
        e.pg.fill('#nuevo', 'Begoña')
        e.clic('button[data-nuevo]')
        renombra(e, 'Begoña', 'Begoña B')
        ok(not ls(e, 'renombres') and 'Begoña B' in (ls(e, 'nuevos') or []) and 'Begoña' not in (ls(e, 'nuevos') or []) and e.pg.query_selector('#cambios-nombres') is None, 'T85g un nombre nuevo que no ha salido del aparato se corrige sin apuntar nada para el PC: %s %s' % (ls(e, 'renombres'), ls(e, 'nuevos')))
        e.clic('button[data-guardar]')
        renombra(e, 'Begoña B', 'Begoña C')
        ok(ls(e, 'renombres') == [{'de': 'Begoña B', 'a': 'Begoña C'}] and [p['nombre'] for p in ls(e, 'pendientes')[0]['presentes']] == ['Begoña C'], 'T85g pero si una jornada guardada lo lleva (puede haberse enviado ya), sí se apunta: %s %s' % (ls(e, 'renombres'), ls(e, 'pendientes')))
    con_escena('T85g', est8(), t85g)

    def t83d(e):
        e.ir()
        e.clic('button[data-todos="1"]')
        e.pulsar('Mikel', 2, '0.5')
        e.clic('button[data-guardar]')
        renombra(e, 'Mikel', 'Txomin')
        pj = ls(e, 'pendientes')
        ok(e.filas() == ['Txomin'] and [(p['nombre'], p['horas']) for p in pj[0]['presentes']] == [('Txomin', 7.5)], 'T83d si salían los dos, queda la anotación de quien ya tenía ese nombre aunque vaya después en la lista: %s %s' % (e.filas(), pj))
        ok(ls(e, 'renombres') == [{'de': 'Mikel', 'a': 'Txomin'}], 'T83d se apunta la unión: %s' % ls(e, 'renombres'))
    con_escena('T83d', est8(), t83d)

    def t82c(e):
        e.ir()
        e.clic(lapiz('Mikel'))
        e.pg.fill('#ren-campo', 'Mik')
        e.clic('#v-app .row[data-nombre="Txomin"] .x')
        ok(e.valor('#ren-campo') == 'Mik' and 'Txomin' in e.marcados(), 'T82c marcar a otra persona no cierra el campo ni pierde lo escrito: %r %s' % (e.valor('#ren-campo'), e.marcados()))
        e.clic('button[data-amb="garaje"]')
        ok(e.pg.query_selector('#ren-campo') is None and e.filas() == ['Andoni'], 'T82c cambiar de viviendas a garajes cierra el campo (la lista es otra): %s' % e.filas())
        e.clic(lapiz('Andoni'))
        e.fecha('2026-10-19')
        ok(e.pg.query_selector('#ren-campo') is None, 'T82c cambiar de fecha cierra el campo')
        e.clic(lapiz('Andoni'))
        e.obra('mungia')
        ok(e.pg.query_selector('#ren-campo') is None, 'T82c cambiar de obra cierra el campo')
    con_escena('T82c', est8(), t82c)

    def t85h(e):
        e.ir()
        e.clic('button[data-varios]')
        e.pg.fill('#varios-texto', chr(10).join(['Ane', 'Iker']))
        e.clic('button[data-varios-ok]')
        e.pg.select_option('#addsel', 'Ane')
        e.clic('button[data-add]')
        renombra(e, 'Ane', 'Anita')
        ok(ls(e, 'altas') == ['Anita', 'Iker'] and ls(e, 'renombres') == [{'de': 'Ane', 'a': 'Anita'}], 'T85h un nombre nuevo (sin jornada) que ya pudo salir en un envío se corrige apuntando el cambio y con el nombre nuevo en la lista de nuevos: %s %s' % (ls(e, 'altas'), ls(e, 'renombres')))
        renombra(e, 'Anita', 'Iker')
        ok(ls(e, 'altas') == ['Iker'] and (ls(e, 'nuevos') or []).count('Iker') == 1 and cambios(e) == '1 nombre corregido · 1 nombre nuevo sin enviar al PC', 'T85h si el nombre corregido ya era de otro nombre nuevo, no quedan repetidos: %s %s %r' % (ls(e, 'altas'), ls(e, 'nuevos'), cambios(e)))
        lote = e.exportar() or {}
        ok(lote.get('altas') == ['Iker'] and lote.get('renombres') == [{'de': 'Ane', 'a': 'Iker'}], 'T85h el fichero lleva las dos cosas: %s' % {k: lote.get(k) for k in lote})
        valida_con_p1(lote)
    con_escena('T85h', est8(), t85h)

    # --- T86: el fichero y el aviso de enviar con los cambios nuevos
    def t86(e):
        e.ir()
        ok(e.exportar(esperar=False) is None and 'no hay nada por enviar' in e.enviar_txt('#nada-que-enviar').lower(), 'T86 (08d) sin nada que enviar no hay botón ni se descarga nada: %r' % e.enviar_txt('#nada-que-enviar'))
        renombra(e, 'Mikel', 'Mikelo')
        lote = e.exportar() or {}
        ok(set(lote) == {'tipo', 'version', 'obra', 'renombres', 'jornadas'} and lote['jornadas'] == [] and lote['renombres'] == [{'de': 'Mikel', 'a': 'Mikelo'}], 'T86 solo con un nombre corregido el fichero se envía igualmente, sin jornadas: %s' % lote)
        ok('con 1 nombre corregido' in e.listo() and 'jornada' not in e.listo(), 'T86 (08d) el recuadro «Listo» cuenta lo enviado (sin hablar de jornadas si no hay): %r' % e.listo())
        valida_con_p1(lote)
    con_escena('T86', est8(), t86)

    # --- T87: si el aparato no deja guardar, no se dice que está hecho
    def t87(e):
        e.ir()
        renombra(e, 'Mikel', 'Mikelo')
        ok('no se pudo' in e.toast() and 'nombre corregido' not in e.toast(), 'T87 sin poder escribir en el aparato, corregir un nombre lo avisa en vez de decir que está hecho: %r' % e.toast())
        e.clic('button[data-varios]')
        e.pg.fill('#varios-texto', 'Ane')
        e.clic('button[data-varios-ok]')
        ok('no se pudo' in e.toast(), 'T87 y lo mismo con varios nombres: %r' % e.toast())
    con_escena('T87', est8(), t87, init=sin_ls)

    # --- T88: medidas táctiles, letra y desbordamiento (móvil 390 y 320, tablet 820)
    def t88(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        m = e.pg.evaluate("""() => { const q = s => [...document.querySelectorAll(s)].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
           return {lapiz: q('#v-app button[data-ren]'), ancho: document.documentElement.scrollWidth, ventana: innerWidth, filas: q('#v-app .row')}; }""")
        ok(all(w >= 40 and h >= 44 for w, h in m['lapiz']) and len(m['lapiz']) == 2, 'T88 los lápices miden al menos 40 de ancho y 44 de alto: %s' % m['lapiz'])
        ok(m['ancho'] <= m['ventana'] + 1, 'T88 con los lápices no hay desplazamiento lateral: %s > %s' % (m['ancho'], m['ventana']))
        e.clic(lapiz('Mikel'))
        e.pg.fill('#ren-campo', 'x@y.es')
        e.clic('button[data-ren-guardar]')
        m = e.pg.evaluate("""() => { const q = s => [...document.querySelectorAll(s)].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
           const f = document.querySelector('#v-app .row.ren').getBoundingClientRect();
           return {campo: q('#ren-campo'), botones: q('#v-app .row.ren .btn'), letra: parseFloat(getComputedStyle(document.querySelector('#ren-campo')).fontSize),
                   dentro: [Math.round(f.left), Math.round(f.right), innerWidth], ancho: document.documentElement.scrollWidth, error: q('#ren-error')}; }""")
        ok(all(h >= 46 for w, h in m['campo']) and all(h >= 48 for w, h in m['botones']) and len(m['botones']) == 2 and m['letra'] >= 16, 'T88 el campo del nombre mide ≥ 46 px de alto con letra ≥ 16 px y sus dos botones ≥ 48: %s %s %s' % (m['campo'], m['botones'], m['letra']))
        ok(m['dentro'][0] >= 0 and m['dentro'][1] <= m['dentro'][2] and m['ancho'] <= m['dentro'][2] + 1 and len(m['error']) == 1, 'T88 el campo con su error cabe en pantalla: %s' % m['dentro'])
        e.clic('button[data-ren-cancelar]')
        e.clic('button[data-varios]')
        m = e.pg.evaluate("""() => { const q = s => [...document.querySelectorAll(s)].map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
           const v = document.querySelector('#varios').getBoundingClientRect();
           return {area: q('#varios-texto'), botones: q('#varios .btn'), letra: parseFloat(getComputedStyle(document.querySelector('#varios-texto')).fontSize), boton: q('button[data-varios]'),
                   dentro: [Math.round(v.left), Math.round(v.right), innerWidth], ancho: document.documentElement.scrollWidth}; }""")
        ok(m['area'][0][1] >= 100 and m['letra'] >= 16 and all(h >= 48 for w, h in m['botones']) and len(m['botones']) == 2, 'T88 el cuadro de varios nombres es cómodo: alto ≥ 100, letra ≥ 16, botones ≥ 48: %s %s %s' % (m['area'], m['letra'], m['botones']))
        ok(m['dentro'][0] >= 0 and m['dentro'][1] <= m['dentro'][2] and m['ancho'] <= m['dentro'][2] + 1, 'T88 el cuadro de varios nombres cabe en pantalla: %s' % m['dentro'])
    con_escena('T88', est8(), t88)
    con_escena('T88 estrecho', est8(), t88, ancho=320, alto=640)
    con_escena('T88 tablet', est8(), t88, ancho=820, alto=1180)

    # --- T89: todo lo que viene de los datos se escapa también en lo nuevo
    def t89(e):
        e.ir()
        ok(e.pg.evaluate("[...document.querySelectorAll('#v-app .row')].some(r=>r.dataset.nombre.includes('<b>'))"), 'T89 preparación: el nombre raro está en la lista')
        ok(e.pg.evaluate("document.querySelectorAll('#v-app .nm *').length") == 0 and e.pg.evaluate("[...document.querySelectorAll('#v-app .nm')].map(n=>n.textContent)")[0] == raro, 'T89 el nombre raro sale en la lista como texto y sin crear elementos')
        e.pg.click('#v-app .row button[data-ren]')
        ok(e.valor('#ren-campo') == raro and e.pg.evaluate("document.querySelectorAll('#v-app .row.ren b, #v-app .row.ren i').length") == 0, 'T89 el campo lleva el nombre raro tal cual y no se crea ningún elemento a partir de él: %r' % e.valor('#ren-campo'))
        e.clic('button[data-ren-cancelar]')
        e.clic(lapiz('Mikel'))
        e.pg.fill('#ren-campo', raro2)
        e.clic('button[data-ren-guardar]')
        ok(e.txt('#ren-pregunta [data-texto]') == 'Ya hay un «%s». ¿Son la misma persona? Se juntarán al pasarlo al PC, con vista previa antes.' % raro2 and e.pg.evaluate("document.querySelectorAll('#ren-pregunta [data-texto] *').length") == 0, 'T89 la pregunta enseña el nombre con comillas y & como texto: %r' % e.txt('#ren-pregunta [data-texto]'))
        e.clic('button[data-ren-si]')
        ok(raro2 in e.txt('#toast') and e.pg.evaluate("document.querySelectorAll('#toast *').length") == 0 and 'Mikel' not in e.filas() and raro2 in e.filas(), 'T89 al juntarlos el aviso lleva los nombres como texto: %r %s' % (e.txt('#toast'), e.filas()))
        ok(ls(e, 'renombres') == [{'de': 'Mikel', 'a': raro2}], 'T89 y se apunta con las comillas intactas: %s' % ls(e, 'renombres'))
        e.pg.click('#v-app .row button[data-ren]')
        e.pg.fill('#ren-campo', 'x')
        e.clic('button[data-ren-guardar]')
        ok('x' in e.filas() and raro not in e.filas() and ls(e, 'renombres')[1] == {'de': raro, 'a': 'x'}, 'T89 corregir el nombre raro funciona y se apunta tal cual: %s %s' % (e.filas(), ls(e, 'renombres')))
        ok(raro in e.txt('#toast') and e.pg.evaluate("document.querySelectorAll('#toast *').length") == 0 and e.pg.evaluate("document.querySelectorAll('#v-app .nm *').length") == 0, 'T89 el aviso lleva el nombre raro como texto: %r' % e.txt('#toast'))
    raro2 = "O'Brien \"el Rubio\" &amp; Co &lt;i&gt;"
    con_escena('T89', estado_con({'olabeaga': obra_est('2026 OLABEAGA', [], ultima={'vivienda': {'fecha': '2026-10-22', 'presentes': pres(raro, raro2, 'Mikel')}, 'garaje': None})}, [raro, raro2, 'Mikel']), t89)


    # ======================================================================================================================
    # Bloque del paso 08d: día nuevo con la gente anterior marcada (D5), pantalla «Enviar al PC», nombre del fichero (D7).
    # Fecha fija: viernes 23/10/2026. Datos inventados. Escenas T90 en adelante (P3_SOLO_08D=1 corre solo estas).
    # ======================================================================================================================
    OB = '2026 OLABEAGA'

    def viv(fecha, *nombres, horas=7.5, extra=0):
        return [fila(fecha, 'vivienda', n, horas, extra) for n in nombres]

    def gar(fecha, *nombres):
        return [fila(fecha, 'garaje', n, 7.5) for n in nombres]

    def est9(filas, catalogo, ultima_viv=None, ultima_gar=None, extra_obras=None, excep=None):
        obras = {'olabeaga': obra_est(OB, filas, ultima={'vivienda': ultima_viv, 'garaje': ultima_gar}, excep=excep)}
        obras.update(extra_obras or {})
        return estado_con(obras, catalogo)

    def u(fecha, *nombres):
        return {'fecha': fecha, 'presentes': pres(*nombres)}

    def rotulo(e):
        return e.txt('#rotulo-marcados')

    def pend9(fecha, nombres, ambito='vivienda', anulada=False, obra='olabeaga', horas=7.5):
        return {'obra': obra, 'ambito': ambito, 'fecha': fecha, 'anulada': anulada,
                'presentes': [] if anulada else [{'nombre': n, 'horas': horas, 'extra': 0} for n in nombres],
                'notas': '', 'registrado': fecha + 'T18:00:00.000Z'}

    # --- T90: el lunes mira el viernes (la última jornada anterior que existe, no el «ayer» de calendario)
    def t90(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Ana', 'Beto'] and rotulo(e) == 'Marcados según la jornada del viernes 16/10: quita a quien no haya venido.',
           'T90 el viernes 23/10 (ayer, 22/10, no hubo obra) sale marcada la gente del viernes 16/10: %s %r' % (e.marcados(), rotulo(e)))
        e.fecha('2026-10-19')
        ok(e.filas() == ['Ana', 'Beto'] and e.marcados() == ['Ana', 'Beto'] and 'viernes 16/10' in rotulo(e),
           'T90 el lunes 19/10 mira el viernes 16/10 (no el domingo ni el jueves 15/10, que es de Carlos): %s %s %r' % (e.filas(), e.marcados(), rotulo(e)))
        e.fecha('2026-10-14')
        ok(e.marcados() == [] and e.pg.query_selector('#rotulo-marcados') is None,
           'T90 el miércoles 14/10 no tiene nada ANTERIOR (lo del 15 y el 16 es posterior): no se marca a nadie y no hay rótulo: %s %r' % (e.marcados(), rotulo(e)))
    con_escena('T90', est9(viv('2026-10-15', 'Carlos') + viv('2026-10-16', 'Ana', 'Beto'), ['Ana', 'Beto', 'Carlos'], u('2026-10-16', 'Ana', 'Beto')), t90)

    # --- T90b: «la última jornada anterior» deja fuera la de la propia fecha (se prueba la función directamente: la pantalla ni la llama
    # cuando la fecha ya tiene jornada)
    def t90b(e):
        e.ir(previa=True)
        e.fecha('2026-10-16')           # el 16/10 ya tiene jornada (Ana y Beto): lo anterior es el 15/10 (Carlos)
        r = e.pg.evaluate("jornadaAnterior()")
        ok(r == {'fecha': '2026-10-15', 'nombres': ['Carlos']}, 'T90b la última jornada anterior al 16/10 es la del 15/10 (Carlos), no la del propio 16/10: %s' % r)
    con_escena('T90b', est9(viv('2026-10-15', 'Carlos') + viv('2026-10-16', 'Ana', 'Beto'), ['Ana', 'Beto', 'Carlos'], u('2026-10-16', 'Ana', 'Beto')), t90b,
               init=sembrar('sgd_personal_pendientes', [pend9('2026-10-16', ['Ana'])]))

    # --- T91: viviendas y garajes por separado (y cada obra con lo suyo)
    def t91(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Ana'] and 'miércoles 21/10' in rotulo(e), 'T91 viviendas mira SU última jornada (miércoles 21/10: Ana): %s %r' % (e.marcados(), rotulo(e)))
        e.clic('button[data-amb="garaje"]')
        ok(e.marcados() == ['Hugo'] and 'jueves 22/10' in rotulo(e) and 'Ana' not in e.filas(), 'T91 garajes mira SU última jornada (jueves 22/10: Hugo) y no mezcla las de viviendas: %s %s %r' % (e.filas(), e.marcados(), rotulo(e)))
        e.clic('button[data-amb="vivienda"]')
        ok(e.marcados() == ['Ana'] and 'Hugo' not in e.filas(), 'T91 al volver a viviendas vuelve la suya: %s %s' % (e.filas(), e.marcados()))
        e.obra('mungia')
        ok(e.marcados() == ['Pepe'] and 'martes 20/10' in rotulo(e), 'T91 otra obra mira la suya (Mungia, martes 20/10: Pepe): %s %r' % (e.marcados(), rotulo(e)))
    mun9 = {'mungia': obra_est('2026 MUNGIA', viv('2026-10-20', 'Pepe'), ultima={'vivienda': u('2026-10-20', 'Pepe'), 'garaje': None})}
    con_escena('T91', est9(viv('2026-10-21', 'Ana') + gar('2026-10-22', 'Hugo'), ['Ana', 'Hugo', 'Pepe'], u('2026-10-21', 'Ana'), u('2026-10-22', 'Hugo'), mun9), t91)

    # --- T91b: una jornada de GARAJES sin enviar no entra en la lista de viviendas (ni al revés)
    def t91b(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Ana'] and 'miércoles 21/10' in rotulo(e), 'T91b viviendas sigue mirando la suya (miércoles 21/10: Ana) aunque haya garajes sin enviar el jueves: %s %r' % (e.marcados(), rotulo(e)))
        e.clic('button[data-amb="garaje"]')
        ok(e.marcados() == ['Hugo'] and 'jueves 22/10' in rotulo(e), 'T91b garajes mira la de garajes sin enviar (jueves 22/10: Hugo): %s %r' % (e.marcados(), rotulo(e)))
    con_escena('T91b', est9(viv('2026-10-21', 'Ana'), ['Ana', 'Hugo'], u('2026-10-21', 'Ana')), t91b,
               init=sembrar('sgd_personal_pendientes', [pend9('2026-10-22', ['Hugo'], ambito='garaje')]))

    # --- T92: cuentan las jornadas todavía sin enviar al PC (y mandan sobre las del PC)
    def t92(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Beto'] and 'jueves 22/10' in rotulo(e) and e.filas() == ['Ana', 'Beto'],
           'T92 una jornada sin enviar (jueves 22/10: Beto) cuenta como anterior: %s %s %r' % (e.filas(), e.marcados(), rotulo(e)))
    con_escena('T92', est9(viv('2026-10-21', 'Ana'), ['Ana', 'Beto'], u('2026-10-21', 'Ana')), t92,
               init=sembrar('sgd_personal_pendientes', [pend9('2026-10-22', ['beto'])]))   # «beto» en minúscula: sale como «Beto»

    def t92b(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Beto'] and 'jueves 22/10' in rotulo(e),
           'T92b la jornada corregida sin enviar (Beto) manda sobre la que ya tiene el PC de ese mismo día (Ana): %s %r' % (e.marcados(), rotulo(e)))
    con_escena('T92b', est9(viv('2026-10-22', 'Ana'), ['Ana', 'Beto'], u('2026-10-22', 'Ana')), t92b,
               init=sembrar('sgd_personal_pendientes', [pend9('2026-10-22', ['Beto'])]))

    # --- T93: una jornada ANULADA no cuenta (la anulada sin enviar quita la del PC)
    def t93(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Ana'] and 'miércoles 21/10' in rotulo(e), 'T93 la jornada del jueves 22/10 está anulada: se mira la del miércoles 21/10 (Ana): %s %r' % (e.marcados(), rotulo(e)))
        e.clic('nav button[data-v="enviar"]')
        li = e.pg.eval_on_selector_all('.envio[data-obra="olabeaga"] li', 'e=>e.map(l=>l.textContent.trim())')
        ok(li == ['Viviendas · jue 22/10 — jornada anulada (se quita del PC)'], 'T93 en «Enviar al PC» una jornada anulada se cuenta como anulada (no como gente): %s' % li)
    con_escena('T93', est9(viv('2026-10-21', 'Ana') + viv('2026-10-22', 'Beto'), ['Ana', 'Beto'], u('2026-10-22', 'Beto')), t93,
               init=sembrar('sgd_personal_pendientes', [pend9('2026-10-22', [], anulada=True)]))

    def t93b(e):
        e.ir(previa=True)
        ok(e.marcados() == [] and e.pg.query_selector('#rotulo-marcados') is None, 'T93b si la única jornada anterior está anulada es como si no hubiera: sin marcar y sin rótulo: %s %r' % (e.marcados(), rotulo(e)))
    con_escena('T93b', est9(viv('2026-10-22', 'Beto'), ['Beto'], u('2026-10-22', 'Beto')), t93b,
               init=sembrar('sgd_personal_pendientes', [pend9('2026-10-22', [], anulada=True)]))

    # --- T94: se marcan con las horas normales de la fecha nueva (su horario especial si lo tienen), sin extra ni notas
    def t94(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Ana', 'Beto'] and e.horas('Ana') == '7,5 h' and e.horas('Beto') == '9 h',
           'T94 el viernes: Ana a 7,5 h (aunque el jueves hizo 9 h) y Beto a su horario especial de 9 h: %s %r %r' % (e.marcados(), e.horas('Ana'), e.horas('Beto')))
        ok(chip(e, 'Beto', True) == 'horario especial 9 h' and chip(e, 'Ana') == '' and chip(e, 'Beto') == '',
           'T94 sin horas extra heredadas (ni el +1,5 h de Ana): %r %r %r' % (chip(e, 'Ana'), chip(e, 'Beto'), chip(e, 'Beto', True)))
        ok(e.txt('.sum') == '2 presentes · 16,5 h', 'T94 el resumen: %r' % e.txt('.sum'))
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        js = {p['nombre']: p for j in lote.get('jornadas', []) for p in j['presentes']}
        ok(js.get('Ana') == {'nombre': 'Ana', 'horas': 7.5, 'extra': 0} and js.get('Beto') == {'nombre': 'Beto', 'horas': 9, 'extra': 0},
           'T94 la jornada guardada lleva las horas normales de hoy y extra 0: %s' % js)
        ok(all(j['notas'] == '' for j in lote.get('jornadas', [])), 'T94 sin notas heredadas: %s' % lote.get('jornadas'))
        valida_con_p1(lote)
    con_escena('T94', est9([fila('2026-10-22', 'vivienda', 'Ana', 9, 1.5), fila('2026-10-22', 'vivienda', 'Beto', 9)], ['Ana', 'Beto'],
                           {'fecha': '2026-10-22', 'presentes': [{'nombre': 'Ana', 'horas': 9, 'extra': 1.5}, {'nombre': 'Beto', 'horas': 9, 'extra': 0}]},
                           excep={'Beto': {'vie': 9}}), t94)

    def t94b(e):
        e.ir(previa=True)
        e.fecha('2026-10-24')
        ok(e.marcados() == ['Ana'] and e.horas('Ana') == '¿horas?', 'T94b un sábado sin horario sale marcada pero pide las horas, como al marcar a mano: %s %r' % (e.marcados(), e.horas('Ana')))
        e.clic('button[data-guardar]')
        ok('faltan las horas' in e.toast() and e.pendientes() == '0', 'T94b y no se guarda sin ellas: %r %r' % (e.toast(), e.pendientes()))
    con_escena('T94b', est9(viv('2026-10-23', 'Ana'), ['Ana'], u('2026-10-23', 'Ana')), t94b, hoy='2026-10-24T10:00:00+02:00')

    # --- T95: nada se guarda hasta «Guardar jornada»
    def t95(e):
        e.ir(previa=True)
        e.fecha('2026-10-19')
        e.fecha('2026-10-23')
        ok(e.marcados() == ['Ana', 'Beto'] and e.pendientes() == '0' and ls(e, 'pendientes') in (None, []), 'T95 abrir y cambiar de fecha no guarda ninguna jornada: %s %r %s' % (e.marcados(), e.pendientes(), ls(e, 'pendientes')))
        e.clic('button[data-guardar]')
        ok(e.pendientes() == '1' and [x['nombre'] for x in ls(e, 'pendientes')[0]['presentes']] == ['Ana', 'Beto'], 'T95 «Guardar jornada» sí la guarda, con los marcados: %s' % ls(e, 'pendientes'))
        ok(e.pg.query_selector('#rotulo-marcados') is None, 'T95 una vez guardada la jornada el rótulo ya no se ve: %r' % rotulo(e))
    con_escena('T95', est9(viv('2026-10-16', 'Ana', 'Beto'), ['Ana', 'Beto'], u('2026-10-16', 'Ana', 'Beto')), t95)

    # --- T96: si la fecha YA tiene jornada (del PC o sin enviar) se ve lo guardado, como hoy
    def t96(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Ana'] and e.filas() == ['Ana', 'Beto'] and e.pg.query_selector('#rotulo-marcados') is None,
           'T96 con jornada del PC en esa fecha se ve lo guardado (solo Ana), sin rótulo: %s %s %r' % (e.filas(), e.marcados(), rotulo(e)))
        e.fecha('2026-10-24')
        e.fecha('2026-10-23')
        ok(e.marcados() == ['Ana'] and e.pg.query_selector('#rotulo-marcados') is None, 'T96 al volver a esa fecha sigue viéndose lo guardado: %s' % e.marcados())
    con_escena('T96', est9(viv('2026-10-22', 'Ana', 'Beto') + viv('2026-10-23', 'Ana'), ['Ana', 'Beto'], u('2026-10-22', 'Ana', 'Beto')), t96)

    def t96b(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Beto'] and e.pg.query_selector('#rotulo-marcados') is None, 'T96b con jornada SIN ENVIAR en esa fecha se ve lo guardado (Beto), sin rótulo: %s %r' % (e.marcados(), rotulo(e)))
    con_escena('T96b', est9(viv('2026-10-22', 'Ana', 'Beto'), ['Ana', 'Beto'], u('2026-10-22', 'Ana', 'Beto')), t96b,
               init=sembrar('sgd_personal_pendientes', [pend9('2026-10-23', ['Beto'])]))

    # --- T97: un borrador a medias manda (no se pisa); y conserva el rótulo al recargar
    def t97(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Beto'] and e.pg.query_selector('#rotulo-marcados') is None, 'T97 el borrador a medias (solo Beto) manda sobre la jornada anterior (Ana y Beto): %s %r' % (e.marcados(), rotulo(e)))
    bor97 = {'obra': 'olabeaga', 'ambito': 'vivienda', 'fecha': '2026-10-23', 'lista': [{'nombre': 'Ana', 'on': False, 'horas': None}, {'nombre': 'Beto', 'on': True, 'horas': None}]}
    con_escena('T97', est9(viv('2026-10-22', 'Ana', 'Beto'), ['Ana', 'Beto'], u('2026-10-22', 'Ana', 'Beto')), t97, init=sembrar('sgd_personal_borrador', bor97))

    def t97b(e):
        e.ir(previa=True)
        e.clic('#v-app .row[data-nombre="Ana"] .x')
        ok(e.marcados() == ['Beto'], 'T97b preparación: se quita a Ana: %s' % e.marcados())
        e.pg.reload()
        e.pg.wait_for_selector('#obra')
        ok(e.marcados() == ['Beto'] and 'jueves 22/10' in rotulo(e), 'T97b al recargar manda el borrador (sin Ana) y el rótulo sigue avisando de dónde salió la lista: %s %r' % (e.marcados(), rotulo(e)))
    con_escena('T97b', est9(viv('2026-10-22', 'Ana', 'Beto'), ['Ana', 'Beto'], u('2026-10-22', 'Ana', 'Beto')), t97b)

    def t97c(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Beto'] and e.pg.query_selector('#rotulo-marcados') is None, 'T97c un borrador con la marca de un día que NO es anterior no enseña rótulo: %s %r' % (e.marcados(), rotulo(e)))
    con_escena('T97c', est9(viv('2026-10-22', 'Ana', 'Beto'), ['Ana', 'Beto'], u('2026-10-22', 'Ana', 'Beto')), t97c,
               init=sembrar('sgd_personal_borrador', dict(bor97, prefill='2026-10-24')))

    # --- T98: sin jornada anterior, como hoy (habituales sin marcar, sin rótulo)
    def t98(e):
        e.ir(previa=True)
        e.fecha('2026-10-01')
        ok(e.marcados() == [] and e.filas() == ['Ana'] and e.pg.query_selector('#rotulo-marcados') is None, 'T98 antes de la primera jornada no se marca a nadie y no hay rótulo: %s %s %r' % (e.filas(), e.marcados(), rotulo(e)))
    con_escena('T98', est9(viv('2026-10-14', 'Ana'), ['Ana'], u('2026-10-14', 'Ana')), t98)

    # --- T99: «Desmarcar todos» y «Marcar todos» siguen funcionando con la lista prerrellenada
    def t99(e):
        e.ir(previa=True)
        e.clic('button[data-todos="0"]')
        ok(e.marcados() == [], 'T99 Desmarcar todos con la lista prerrellenada: %s' % e.marcados())
        e.clic('button[data-todos="1"]')
        ok(e.marcados() == e.filas() == ['Ana', 'Beto'], 'T99 Marcar todos: %s %s' % (e.marcados(), e.filas()))
    con_escena('T99', est9(viv('2026-10-21', 'Carlos') + viv('2026-10-22', 'Ana', 'Beto'), ['Ana', 'Beto', 'Carlos'], u('2026-10-22', 'Ana', 'Beto')), t99)

    # --- T100: al cambiar fecha, ámbito u obra se recalcula
    def t100(e):
        e.ir(previa=True)
        ok(e.marcados() == ['Ana'] and 'miércoles 21/10' in rotulo(e), 'T100 punto de partida (viernes 23/10 mira el miércoles 21/10): %s %r' % (e.marcados(), rotulo(e)))
        e.clic('button[data-dia="-2"]')                      # anteayer = 21/10, que ya tiene jornada: se ve lo guardado y desaparece el rótulo
        ok(e.marcados() == ['Ana'] and e.pg.query_selector('#rotulo-marcados') is None, 'T100 con «Anteayer» (21/10, con jornada) se ve lo guardado y se recalcula el rótulo: %s %r' % (e.marcados(), rotulo(e)))
        e.fecha('2026-10-20')                                # martes sin jornada: mira el lunes 19/10
        ok(e.marcados() == ['Beto'] and 'lunes 19/10' in rotulo(e), 'T100 al cambiar de fecha (20/10) mira el 19/10: %s %r' % (e.marcados(), rotulo(e)))
        e.fecha('2026-10-18')                                # domingo sin jornada: mira el viernes 16/10
        ok(e.marcados() == ['Carlos'] and 'viernes 16/10' in rotulo(e), 'T100 con el domingo 18/10 mira el viernes 16/10: %s %r' % (e.marcados(), rotulo(e)))
        e.obra('mungia')
        ok(e.marcados() == ['Pepe'] and 'lunes 12/10' in rotulo(e), 'T100 al cambiar de obra mira la de esa obra: %s %r' % (e.marcados(), rotulo(e)))
        e.obra('olabeaga')
        e.clic('button[data-amb="garaje"]')
        ok(e.marcados() == [] and e.pg.query_selector('#rotulo-marcados') is None, 'T100 al cambiar de ámbito a uno sin jornadas anteriores no se marca a nadie: %s' % e.marcados())
    mun100 = {'mungia': obra_est('2026 MUNGIA', viv('2026-10-12', 'Pepe'), ultima={'vivienda': u('2026-10-12', 'Pepe'), 'garaje': None})}
    con_escena('T100', est9(viv('2026-10-16', 'Carlos') + viv('2026-10-19', 'Beto') + viv('2026-10-21', 'Ana'), ['Ana', 'Beto', 'Carlos', 'Pepe'],
                            u('2026-10-21', 'Ana'), None, mun100), t100)

    # --- T101: nombres escritos distinto en el PC («mikel») salen una sola vez y con el nombre de la base
    def t101(e):
        e.ir(previa=True)
        ok(e.filas() == ['Mikel'] and e.marcados() == ['Mikel'], 'T101 «mikel» del PC sale como «Mikel», una vez y marcado: %s %s' % (e.filas(), e.marcados()))
    con_escena('T101', est9([fila('2026-10-22', 'vivienda', 'mikel', 7.5)], ['Mikel'], None), t101)   # sin «ultima»: el nombre sale SOLO de las filas del PC

    # --- T104: la pantalla «Enviar al PC» sin nada que enviar
    def t104(e):
        e.ir()
        ok(e.pg.eval_on_selector_all('nav button', 'e=>e.map(b=>b.textContent.trim())') == ['Anotar', 'Jornadas', 'Informe', 'Enviar al PC'],
           'T104 las cuatro pestañas: Anotar, Jornadas, Informe y Enviar al PC: %s' % e.pg.eval_on_selector_all('nav button', 'e=>e.map(b=>b.textContent.trim())'))
        e.clic('nav button[data-v="enviar"]')
        ok(e.pg.is_visible('#enviar') and e.pg.query_selector('#v-app') is not None and not e.pg.is_visible('#v-app'), 'T104 la pestaña abre una pantalla de verdad')
        ok(e.txt('#enviar h2') == 'Enviar las jornadas al PC', 'T104 título: %r' % e.txt('#enviar h2'))
        ok(e.txt('#para-que').startswith('Para qué sirve:') and 'No se envía solo' in e.txt('#para-que') and 'el PC no se entera' in e.txt('#para-que'), 'T104 «Para qué sirve»: %r' % e.txt('#para-que'))
        ok(e.txt('#nada-que-enviar') == 'No hay nada por enviar: todas las jornadas ya están en el PC.' and e.pg.query_selector('button[data-preparar]') is None, 'T104 sin nada que enviar lo dice y no hay botón: %r' % e.txt('#nada-que-enviar'))
        pasos = e.pg.eval_on_selector_all('#pasos li', 'e=>e.map(l=>l.textContent.trim())')
        ok(len(pasos) == 3 and 'CONTROL HORARIO' in pasos[0] and 'descargas' in pasos[0] and 'REVISIONES' in pasos[1] and 'como haces con las revisiones' in pasos[1] and 'actualiza la obra' in pasos[2] and '.bat' in pasos[2],
           'T104 los 3 pasos (fichero «CONTROL HORARIO», REVISIONES como las revisiones, «actualiza la obra» o el .bat): %s' % pasos)
        ok('siguen apuntadas aquí hasta que el PC las recibe' in e.txt('#sigue-apuntado'), 'T104 dice que las jornadas siguen apuntadas: %r' % e.txt('#sigue-apuntado'))
    con_escena('T104', ESTADO1, t104)

    # --- T105: con 2 jornadas: lista con obra, ámbito, día y gente; el fichero; el recuadro «Listo» que se queda
    def t105(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('#v-app .row[data-nombre="Txomin"] .x')
        e.clic('button[data-guardar]')
        e.clic('button[data-amb="garaje"]')
        e.clic('#v-app .row[data-nombre="Andoni"] .x')
        e.clic('button[data-guardar]')
        e.clic('button[data-amb="vivienda"]')
        e.fecha('2026-10-20')
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        e.clic('nav button[data-v="enviar"]')
        ok(e.txt('#resumen-envio') == 'Tienes 3 jornadas sin enviar:', 'T105 resumen: %r' % e.txt('#resumen-envio'))
        li = e.pg.eval_on_selector_all('.envio[data-obra="olabeaga"] li', 'e=>e.map(l=>l.textContent.trim())')
        ok(li == ['Viviendas · mar 20/10 — Mikel (7,5 h)', 'Garajes · vie 23/10 — Andoni (7,5 h)', 'Viviendas · vie 23/10 — Mikel, Txomin (15 h)'],
           'T105 cada jornada con ámbito, día y gente (por fecha): %s' % li)
        ok(e.txt('.envio[data-obra="olabeaga"] h3') == '2026 OLABEAGA BILBAO' and e.txt('.envio[data-obra="olabeaga"] .nota') == 'Se llamará «CONTROL HORARIO 2026 OLABEAGA BILBAO 23102026»',
           'T105 obra y nombre del fichero: %r %r' % (e.txt('.envio[data-obra="olabeaga"] h3'), e.txt('.envio[data-obra="olabeaga"] .nota')))
        ok(e.txt('button[data-preparar="olabeaga"]') == 'Preparar el fichero para el PC' and e.pg.query_selector('#listo') is None, 'T105 botón y todavía sin recuadro «Listo»')
        with e.pg.expect_download(timeout=5000) as d:
            e.pg.click('button[data-preparar="olabeaga"]')
        ok(d.value.suggested_filename == 'CONTROL HORARIO 2026 OLABEAGA BILBAO 23102026.json', 'T105 nombre del fichero descargado: %r' % d.value.suggested_filename)
        ruta = os.path.join(e.dir, 'f105.json')
        d.value.save_as(ruta)
        lote = json.load(open(ruta, encoding='utf-8'))
        ok(lote['tipo'] == 'lote_personal' and len(lote['jornadas']) == 3, 'T105 el fichero lleva las 3 jornadas: %s' % lote)
        valida_con_p1(lote)
        esperado = 'Listo. Se ha guardado el fichero «CONTROL HORARIO 2026 OLABEAGA BILBAO 23102026» con 3 jornadas. Ahora mándalo al PC.'
        ok(e.txt('#listo') == esperado, 'T105 recuadro «Listo»: %r' % e.txt('#listo'))
        e.pg.wait_for_timeout(6500)
        ok(e.pg.is_visible('#listo') and e.txt('#listo') == esperado, 'T105 el recuadro se queda (no es un aviso que desaparece a los pocos segundos): visible=%s' % e.pg.is_visible('#listo'))
        e.clic('nav button[data-v="app"]')
        e.clic('nav button[data-v="enviar"]')
        ok(e.txt('#listo') == esperado and e.pendientes() == '3', 'T105 sigue ahí al cambiar de pestaña y las jornadas siguen apuntadas (3): %r %r' % (e.txt('#listo'), e.pendientes()))
    con_escena('T105', ESTADO1, t105)

    # --- T106: singular y plural bien
    def t106(e):
        e.ir()
        ok(e.txt('#pendientes') == 'Sin enviar al PC: 0 jornadas', 'T106 cero: %r' % e.txt('#pendientes'))
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        ok(e.txt('#pendientes') == 'Sin enviar al PC: 1 jornada', 'T106 una: %r' % e.txt('#pendientes'))
        e.clic('nav button[data-v="enviar"]')
        ok(e.txt('#resumen-envio') == 'Tienes 1 jornada sin enviar:', 'T106 una en la pantalla: %r' % e.txt('#resumen-envio'))
        e.clic('nav button[data-v="app"]')
        e.fecha('2026-10-22')
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        e.fecha('2026-10-21')
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        ok(e.txt('#pendientes') == 'Sin enviar al PC: 3 jornadas', 'T106 tres: %r' % e.txt('#pendientes'))
    con_escena('T106', ESTADO1, t106)

    # --- T107: dos obras con cosas sin enviar: un bloque, un botón y un fichero por obra; cada fichero solo lleva lo suyo
    def t107(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Mikel"] .x')
        e.clic('button[data-guardar]')
        e.obra('mungia')
        e.clic('#v-app .row[data-nombre="Pepe"] .x')
        e.clic('button[data-guardar]')
        e.clic('nav button[data-v="enviar"]')
        ids = e.pg.eval_on_selector_all('#enviar .envio[data-obra]', 'e=>e.map(b=>b.dataset.obra)')
        ok(ids == ['mungia', 'olabeaga'], 'T107 un bloque por obra, la que se está viendo primero: %s' % ids)
        lm = e.exportar(obra='mungia') or {}
        nm = e.descarga
        ok(nm == 'CONTROL HORARIO 2026 MUNGIA ACR NEINOR 23102026.json' and lm.get('obra') == 'mungia' and [p['nombre'] for j in lm.get('jornadas', []) for p in j['presentes']] == ['Pepe'],
           'T107 el fichero de Mungia lleva solo lo de Mungia: %r %s' % (nm, lm))
        ok(e.pendientes() == '2' and 'CONTROL HORARIO 2026 MUNGIA ACR NEINOR 23102026' in e.listo(), 'T107 las dos siguen sin enviar y el recuadro nombra el de Mungia: %r %r' % (e.pendientes(), e.listo()))
        lo = e.exportar(obra='olabeaga') or {}
        ok(lo.get('obra') == 'olabeaga' and [p['nombre'] for j in lo.get('jornadas', []) for p in j['presentes']] == ['Mikel'] and 'OLABEAGA BILBAO 23102026' in e.listo() and 'MUNGIA' not in e.listo(),
           'T107 el de Olabeaga lleva solo lo suyo y el recuadro pasa a nombrar el suyo: %s %r' % (lo, e.listo()))
    con_escena('T107', ESTADO1, t107)

    # --- T108: nombre del fichero: limpio como el del generador de revisiones, y con la fecha en que se prepara (reloj de la tablet)
    def t108(e):
        e.ir()
        e.clic('nav button[data-v="enviar"]')
        lote = e.exportar(obra='rara') or {}
        ok(e.descarga == 'CONTROL HORARIO N OBRA X 1 A B UNICA NANDU 24102026.json', 'T108 nombre limpio (mayúsculas, sin tildes, signos y barras → espacio) y fecha DEL DÍA QUE SE PREPARA en hora de la tablet (00:30 del 24/10, que en UTC aún es el 23): %r' % e.descarga)
        ok(not re.search(r'[\\/:*?"<>|]', e.descarga), 'T108 sin caracteres que Windows no admita: %r' % e.descarga)
        ok('CONTROL HORARIO N OBRA X 1 A B UNICA NANDU 24102026' in e.listo(), 'T108 el recuadro muestra el nombre exacto (sin .json): %r' % e.listo())
        ok(e.pg.eval_on_selector_all('#enviar .envio[data-obra="rara"] h3', 'e=>e.map(h=>h.textContent)') == ['Ñ Obra/ "X": 1 <a>|b? Única ñandú'] and e.pg.evaluate("document.querySelectorAll('#enviar h3 *').length") == 0,
           'T108 el nombre de la obra sale como texto, sin crear elementos')
    rara = obra_est('Ñ Obra/ "X": 1 <a>|b? Única ñandú', [], ultima={'vivienda': u('2026-10-23', 'Pepe'), 'garaje': None})
    con_escena('T108', estado_con({'olabeaga': obra_est(OB, []), 'rara': rara}, ['Pepe']), t108, hoy='2026-10-24T00:30:00+02:00',
               init=sembrar('sgd_personal_pendientes', [pend9('2026-10-23', ['Pepe'], obra='rara')]))

    # --- T109: la limpieza del nombre es LA MISMA que la del generador de revisiones (se prueba con su código, no con una copia)
    def t109(e):
        e.ir()
        fuente = open(os.path.join(TRABAJO, 'generador_revisiones.html'), encoding='utf-8').read()
        m = re.search(r'function safeRevisionWorkName\(value\)\{.*?\n\}', fuente, re.S)
        ok(m is not None, 'T109 no se encuentra safeRevisionWorkName en generador_revisiones.html')
        if m is None:
            return
        casos = ['2026 OLABEAGA BILBAO', 'Ñandú / Órgano "X"', 'a:b*c?d<e>f|g\\h', '   muchos    espacios  ', 'ÀÉÎÕÜ ç', '2026-MUNGIA_ACR (NEINOR)', 'tab\tray']
        for c in casos:
            ref = e.pg.evaluate("([src,v])=>new Function('v', src+';return safeRevisionWorkName(v)')(v)", [m.group(0), c])
            mia = e.pg.evaluate("v=>nombreSeguro(v)", c)
            ok(ref == mia, 'T109 «%s»: el generador de revisiones da %r y la tablet %r' % (c, ref, mia))
        ok(e.pg.evaluate("nombreSeguro('')") == 'OBRA' and e.pg.evaluate("nombreSeguro('€€€')") == 'OBRA', 'T109 si no queda nada, «OBRA» (como el generador para un nombre vacío)')
    con_escena('T109', ESTADO1, t109)

    # --- T110: horarios especiales, cambio de horario y nombres también salen en la lista y en el recuadro, en llano
    def t110(e):
        e.ir()
        e.clic('nav button[data-v="enviar"]')
        lis = e.pg.eval_on_selector_all('#enviar .envio li', 'e=>e.map(l=>l.textContent.trim())')
        ok(lis == ['Viviendas · vie 23/10 — Mikel (7,5 h)', 'Cambio del horario semanal de la obra', '1 horario especial: Mikel', '1 nombre corregido: «Rafa» → «Rafael»', '2 nombres nuevos: Ane, Iker'],
           'T110 la lista dice todo lo que se enviará: %s' % lis)
        e.exportar()
        ok(e.listo().endswith('con 1 jornada, el cambio del horario de la obra, 1 horario especial, 1 nombre corregido y 2 nombres nuevos. Ahora mándalo al PC.'),
           'T110 el recuadro lo cuenta en llano: %r' % e.listo())
    pend110 = [pend9('2026-10-23', ['Mikel'])]
    init110 = (sembrar_varios({'sgd_personal_pendientes': pend110, 'sgd_personal_horarios': {'olabeaga': [0, 8, 8, 8, 8, 8, 0]},
                               'sgd_personal_excepciones': {'olabeaga': {'Mikel': {'vie': 9}}}, 'sgd_personal_renombres': [{'de': 'Rafa', 'a': 'Rafael'}],
                               'sgd_personal_altas': ['Ane', 'Iker'], 'sgd_personal_nuevos': ['Ane', 'Iker']}))
    con_escena('T110', ESTADO1, t110, init=init110)

    # --- T110b: solo un horario especial (sin jornadas ni cambio de horario) también se ofrece para enviar
    def t110b(e):
        e.ir()
        e.clic('nav button[data-v="enviar"]')
        lis = e.pg.eval_on_selector_all('#enviar .envio[data-obra="olabeaga"] li', 'e=>e.map(l=>l.textContent.trim())')
        ok(lis == ['1 horario especial: Mikel'] and e.pg.query_selector('button[data-preparar="olabeaga"]') is not None,
           'T110b solo con un horario especial hay bloque, lista y botón: %s' % lis)
        lote = e.exportar() or {}
        ok(lote.get('excepciones_horario') == {'Mikel': {'vie': 9}} and lote.get('jornadas') == [] and e.listo().endswith('con 1 horario especial. Ahora mándalo al PC.'),
           'T110b el fichero lleva el horario especial y el recuadro lo cuenta: %s %r' % (lote, e.listo()))
    con_escena('T110b', ESTADO1, t110b, init=sembrar('sgd_personal_excepciones', {'olabeaga': {'Mikel': {'vie': 9}}}))

    # --- T111: solo nombres (sin jornadas) también tienen su bloque y su botón; y nada de eso se ve si no hay nada
    def t111(e):
        e.ir()
        e.clic('nav button[data-v="enviar"]')
        ok(e.txt('#resumen-envio') == 'Tienes cambios sin enviar:' and e.pg.query_selector('#envio-nombres') is not None and e.pg.query_selector('button[data-preparar="olabeaga"]') is not None,
           'T111 solo con nombres nuevos hay bloque de nombres y botón para la obra que se ve: %r' % e.txt('#resumen-envio'))
        lote = e.exportar() or {}
        ok(lote.get('altas') == ['Ane'] and lote.get('jornadas') == [] and 'con 1 nombre nuevo.' in e.listo(), 'T111 el fichero lleva el nombre nuevo y ninguna jornada: %s %r' % (lote, e.listo()))
    con_escena('T111', ESTADO1, t111, init=sembrar_varios({'sgd_personal_altas': ['Ane'], 'sgd_personal_nuevos': ['Ane']}))

    # --- T112: textos de la pantalla de anotar: «Enviar al PC» lleva a la pantalla, «Borrar lo que llevo a medias» pregunta antes
    def t112(e):
        e.ir()
        ok(e.txt('#v-app button[data-v="enviar"]') == 'Enviar al PC' and e.txt('#v-app button[data-reset]') == 'Borrar lo que llevo a medias',
           'T112 botones de abajo: %r %r' % (e.txt('#v-app button[data-v="enviar"]'), e.txt('#v-app button[data-reset]')))
        e.clic('#v-app button[data-v="enviar"]')
        ok(e.pg.is_visible('#enviar'), 'T112 «Enviar al PC» (abajo) abre la pantalla de enviar')
        e.clic('nav button[data-v="app"]')
        ok(e.txt('.bar small') == 'Funciona sin cobertura: sí', 'T112 cabecera: %r' % e.txt('.bar small'))
        e.clic('button[data-reset]')
        ok(e.txt('#confirmar-reset').startswith('¿Borrar lo que llevas a medias?'), 'T112 pregunta antes de borrar: %r' % e.txt('#confirmar-reset'))
    con_escena('T112', ESTADO1, t112)

    # --- T113: nada de lo que se escribe a mano se interpreta como HTML en la pantalla de enviar
    def t113(e):
        e.ir()
        e.clic('nav button[data-v="enviar"]')
        ok(e.pg.evaluate("document.querySelectorAll('#enviar li *, #enviar h3 *, #enviar .nota *').length") == 0 and raro in e.txt('#enviar .envio li'),
           'T113 el nombre raro sale como texto en la lista de lo que se envía: %r' % e.txt('#enviar .envio li'))
        e.exportar()
        ok(raro in e.listo() or 'con 1 jornada' in e.listo(), 'T113 el recuadro sale: %r' % e.listo())
    con_escena('T113', estado_con({'olabeaga': obra_est(OB, [], ultima={'vivienda': u('2026-10-22', raro), 'garaje': None})}, [raro]), t113,
               init=sembrar('sgd_personal_pendientes', [pend9('2026-10-23', [raro])]))

    # --- T114: en un iPad estrecho (320 px) y en una tableta (820 px) la pantalla cabe y los botones se pueden pulsar
    def t114(e):
        e.ir()
        e.clic('nav button[data-v="enviar"]')
        ok(e.pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), 'T114 la pantalla de enviar no se sale de ancho (%s px)' % e.pg.viewport_size['width'])
        caja = e.pg.eval_on_selector('button[data-preparar]', 'b=>{const r=b.getBoundingClientRect();return [r.width,r.height]}')
        ok(caja[1] >= 48 and caja[0] >= 150, 'T114 el botón es grande para el dedo: %s' % caja)
    for ancho in (320, 820):
        con_escena('T114', ESTADO1, t114, ancho=ancho, alto=900, init=sembrar('sgd_personal_pendientes', [pend9('2026-10-22', ['Mikel'])]))

    # ======================================================================================================================
    # Bloque del paso 08c2a: el campo Empresa (crear, lápiz, varios nombres, lista, «Enviar al PC»). Escenas T120 en adelante
    # (P3_SOLO_08C2A=1 corre solo estas). Fecha fija: viernes 23/10/2026. Datos inventados.
    # ======================================================================================================================
    def pe(i, n, emp=''):
        return {'id': 'T%04d' % i, 'nombre': n, 'categoria': '', 'empresa': emp, 'activo': True}

    PERS = [('Ana', 'Manueles'), ('Beto', 'Manueles'), ('Carlos', 'CATERSYSTEM'), ('Dani', ''), ('Eli', 'Eli @AUT')]

    def est10(personas=None, filas=None, ultima=None):
        personas = PERS if personas is None else personas
        nombres = [n for n, _ in personas]
        ult = u('2026-10-22', *nombres) if ultima is None else ultima
        fil = viv('2026-10-22', *nombres) if filas is None else filas
        return {'version': 1, 'generado': '2026-10-23T08:00:00+02:00', 'jornada_base_h': 7.5,
                'catalogo': [pe(i + 1, n, em) for i, (n, em) in enumerate(personas)],
                'obras': {'olabeaga': obra_est(OB, fil, ultima={'vivienda': ult, 'garaje': None})}}

    def emp_fila(e, nombre):
        return e.txt('#v-app .row[data-nombre="%s"] .emp' % nombre)

    def opciones_emp(e, sel):
        return e.pg.eval_on_selector_all(sel + ' option', 'e=>e.map(o=>[o.value,o.textContent.trim()])')

    def crear(e, nombre, empresa=None, otra=None):
        """Escribe el nombre, elige la empresa (de la lista o «Otra empresa…» con su texto) y pulsa «Crear»."""
        e.pg.fill('#nuevo', nombre)
        if empresa is not None:
            e.pg.select_option('#nuevo-empresa', empresa)
        if otra is not None:
            e.pg.fill('#nuevo-empresa-otra', otra)
        e.clic('button[data-nuevo]')

    def e2e_emp(lote, previas=None, personas=None):
        """Aplica DE VERDAD el fichero sobre un PC de pruebas que ya tiene a las personas del estado (con las empresas que se
        indiquen en `previas`). Devuelve (resultado, {nombre: empresa} de las personas vigentes, catálogo completo)."""
        if P1 is None:
            return None, None, None
        raiz = os.path.join(SANDBOX, 'pc_' + uuid.uuid4().hex[:6])
        os.makedirs(raiz)
        obras = {'olabeaga': '2026 OLABEAGA BILBAO'}
        nombres = [n for n, _ in (PERS if personas is None else personas)]
        r0 = P1.ingerir_lote(lote_de_filas('olabeaga', viv('2026-10-22', *nombres)), raiz, obras, '2026-10-23', escribir=True,
                             ahora='2026-10-22T22:00:00+02:00')
        ok(r0['ok'], 'e2e: el PC de pruebas no se pudo preparar: %s' % json.dumps(r0, ensure_ascii=False)[:300])
        if previas:
            r1 = P1.ingerir_lote({'tipo': 'lote_personal', 'version': 1, 'obra': 'olabeaga', 'jornadas': [],
                                  'empresas': [{'nombre': n, 'empresa': em} for n, em in previas.items()]},
                                 raiz, obras, '2026-10-23', escribir=True, ahora='2026-10-22T23:00:00+02:00')
            ok(r1['ok'], 'e2e: no se pudieron poner las empresas de partida: %s' % r1)
        r = P1.ingerir_lote(copy.deepcopy(lote), raiz, obras, '2026-10-23', escribir=True, ahora='2026-10-23T22:00:00+02:00')
        cat = P1.cargar_catalogo(raiz)
        return r, {t['nombre']: t.get('empresa') for t in cat['trabajadores'] if t.get('fusionado_en') is None}, cat

    # --- T120: la empresa sale en pequeño al lado del nombre; quien no tiene, nada; el nombre sigue siendo solo el nombre
    def t120(e):
        e.ir()
        ok(e.filas() == ['Ana', 'Beto', 'Carlos', 'Dani', 'Eli'], 'T120 lista: %s' % e.filas())
        ok(emp_fila(e, 'Ana') == 'Manueles' and emp_fila(e, 'Carlos') == 'CATERSYSTEM' and emp_fila(e, 'Eli') == 'Eli @AUT',
           'T120 la empresa sale al lado del nombre: %r %r %r' % (emp_fila(e, 'Ana'), emp_fila(e, 'Carlos'), emp_fila(e, 'Eli')))
        ok(e.pg.query_selector('#v-app .row[data-nombre="Dani"] .emp') is None and e.pg.query_selector('#v-app .row[data-nombre="Dani"] .nw.con-emp') is None,
           'T120 quien no tiene empresa no lleva nada')
        caja = e.pg.evaluate('''()=>{const f=document.querySelector('#v-app .row[data-nombre="Carlos"]');const n=f.querySelector('.nm').getBoundingClientRect();
          const m=f.querySelector('.emp').getBoundingClientRect();const l=f.querySelector('.lap').getBoundingClientRect();
          return {debajo: m.top >= n.bottom - 1, alto: Math.round(m.height), ancho: Math.round(m.width), lapizALaDerecha: l.left >= m.right - 1,
                  con: !!f.querySelector('.nw.con-emp')}}''')
        ok(caja['con'] and caja['debajo'] and caja['alto'] <= 20 and caja['lapizALaDerecha'],
           'T120 la empresa va debajo del nombre, en UNA línea (no partida letra a letra) y con el lápiz a la derecha: %s' % caja)
        ok(e.txt('#v-app .row[data-nombre="Ana"] .nm') == 'Ana', 'T120 el nombre es solo el nombre: %r' % e.txt('#v-app .row[data-nombre="Ana"] .nm'))
        px = e.pg.eval_on_selector('#v-app .row[data-nombre="Ana"] .emp', 'x=>[parseFloat(getComputedStyle(x).fontSize), getComputedStyle(x).color]')
        px_nombre = e.pg.eval_on_selector('#v-app .row[data-nombre="Ana"] .nm', 'x=>parseFloat(getComputedStyle(x).fontSize)')
        ok(px[0] < px_nombre and px[0] >= 11.5, 'T120 la empresa es más pequeña que el nombre pero se lee: %s frente a %s' % (px, px_nombre))
        ok(emp_fila(e, 'Ana') == 'Manueles' and e.pg.evaluate("document.querySelector('#addsel').innerText").count('Manueles') == 0,
           'T120 el desplegable de la base no repite la empresa')
    con_escena('T120', est10(), t120)

    # --- T121: el desplegable de «Nombre nuevo»: Sin empresa, las usadas (una vez cada una, ordenadas), Sagarde y «Otra empresa…»
    def t121(e):
        e.ir()
        ok(opciones_emp(e, '#nuevo-empresa') == [['', 'Sin empresa'], ['CATERSYSTEM', 'CATERSYSTEM'], ['Eli @AUT', 'Eli @AUT'], ['Manueles', 'Manueles'],
                                                 ['Sagarde', 'Sagarde'], ['__otra__', 'Otra empresa…']],
           'T121 opciones: %s' % opciones_emp(e, '#nuevo-empresa'))
        ok(e.valor('#nuevo-empresa') == '', 'T121 por defecto «Sin empresa» (no se da por hecho que sea de Sagarde)')
        ok(not e.pg.is_visible('#nuevo-empresa-otra'), 'T121 el campo de «otra empresa» no se ve hasta elegirlo')
        e.pg.select_option('#nuevo-empresa', '__otra__')
        ok(e.pg.is_visible('#nuevo-empresa-otra') and e.pg.evaluate("document.activeElement.id") == 'nuevo-empresa-otra',
           'T121 «Otra empresa…» enseña el campo y lo deja listo para escribir')
        e.pg.fill('#nuevo', 'Fran')
        e.pg.select_option('#nuevo-empresa', 'Manueles')
        ok(not e.pg.is_visible('#nuevo-empresa-otra') and e.valor('#nuevo') == 'Fran', 'T121 al volver a una empresa de la lista se esconde y no se pierde lo escrito')
        ok(e.pg.evaluate("document.querySelector('#nuevo-empresa').previousElementSibling.textContent") == 'Empresa del nombre nuevo', 'T121 el desplegable lleva su rótulo')
    con_escena('T121', est10(), t121)

    # --- T122: crear a alguien con una empresa de la lista: sale marcado con la empresa, se apunta y viaja en el fichero
    def t122(e):
        e.ir()
        crear(e, 'Fran', 'Manueles')
        ok('Fran' in e.filas() and 'Fran' in e.marcados() and emp_fila(e, 'Fran') == 'Manueles', 'T122 Fran sale marcado con su empresa: %s %r' % (e.marcados(), emp_fila(e, 'Fran')))
        ok(ls(e, 'empresas') == [{'nombre': 'Fran', 'empresa': 'Manueles'}] and ls(e, 'nuevos') == ['Fran'], 'T122 se apunta en el aparato: %s %s' % (ls(e, 'empresas'), ls(e, 'nuevos')))
        ok(cambios(e) == '1 empresa puesta sin enviar al PC', 'T122 lo dice en la pantalla de anotar: %r' % cambios(e))
        ok(e.valor('#nuevo-empresa') == '' and e.valor('#nuevo') == '', 'T122 el formulario queda limpio')
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        ok(lote.get('altas') == ['Fran'] and lote.get('empresas') == [{'nombre': 'Fran', 'empresa': 'Manueles'}] and 'renombres' not in lote,
           'T122 el fichero lleva a Fran como nombre nuevo (para que la empresa tenga a quién ponerse) y su empresa: %s' % json.dumps(lote, ensure_ascii=False)[:400])
        valida_con_p1(lote)
        r, por_nombre, cat = e2e_emp(lote)
        ok(r is None or (r['ok'] and por_nombre.get('Fran') == 'Manueles' and [x['accion'] for x in r['empresas']] == ['puesta']),
           'T122 el PC crea a Fran con su empresa: %s' % por_nombre)
        ok(e.listo().endswith('con 1 jornada y 1 empresa puesta. Ahora mándalo al PC.'), 'T122 el recuadro lo cuenta en llano: %r' % e.listo())
    con_escena('T122', est10(), t122)

    # --- T123: «Otra empresa…»: la escribe; si ya existe con otra grafía se usa la que ya está; vacía o con un teléfono no vale
    def t123(e):
        e.ir()
        crear(e, 'Gaia', '__otra__', 'Obras Nuevas SL')
        ok(emp_fila(e, 'Gaia') == 'Obras Nuevas SL' and ls(e, 'empresas') == [{'nombre': 'Gaia', 'empresa': 'Obras Nuevas SL'}], 'T123 empresa nueva: %r %s' % (emp_fila(e, 'Gaia'), ls(e, 'empresas')))
        ok(['Obras Nuevas SL', 'Obras Nuevas SL'] in opciones_emp(e, '#nuevo-empresa'), 'T123 la empresa nueva ya sale en la lista para la siguiente persona: %s' % opciones_emp(e, '#nuevo-empresa'))
        crear(e, 'Hugo', '__otra__', '  catersystem ')
        ok(emp_fila(e, 'Hugo') == 'CATERSYSTEM', 'T123 «catersystem» es la misma empresa que «CATERSYSTEM»: se usa la que ya consta (%r)' % emp_fila(e, 'Hugo'))
        crear(e, 'Iker', '__otra__', 'obras nuevas sl')
        ok(emp_fila(e, 'Iker') == 'Obras Nuevas SL', 'T123 también con una empresa que acaba de escribirse aquí (%r)' % emp_fila(e, 'Iker'))
        antes = e.filas()
        crear(e, 'Jon', '__otra__', '')
        ok(e.txt('#nuevo-aviso') == 'Escribe la empresa.' and e.filas() == antes and 'Jon' not in ls(e, 'nuevos'), 'T123 «Otra empresa…» sin escribir nada no crea a nadie: %r' % e.txt('#nuevo-aviso'))
        crear(e, 'Jon', '__otra__', '612 345 678')
        ok(e.txt('#nuevo-aviso') == 'Esa empresa no vale: parece un teléfono.' and e.filas() == antes, 'T123 una empresa con un teléfono no vale: %r' % e.txt('#nuevo-aviso'))
        crear(e, 'Jon', '__otra__', 'x@y.es')
        ok(e.txt('#nuevo-aviso') == 'Esa empresa no vale: parece un correo.' and e.filas() == antes, 'T123 ni con un correo: %r' % e.txt('#nuevo-aviso'))
        crear(e, 'Jon', '__otra__', 'a<b')
        ok(e.txt('#nuevo-aviso') == 'Esa empresa no vale: lleva los signos < o >.' and e.filas() == antes, 'T123 ni con < o >: %r' % e.txt('#nuevo-aviso'))
        e.pg.fill('#nuevo', 'Jon')
        e.pg.select_option('#nuevo-empresa', '__otra__')
        e.pg.evaluate("v=>{document.getElementById('nuevo-empresa-otra').value=v}", 'x' * 61)   # fill() respeta el maxlength: se fuerza el valor
        e.clic('button[data-nuevo]')
        ok(e.txt('#nuevo-aviso') == 'Esa empresa no vale: tiene más de 60 letras.' and e.filas() == antes, 'T123 ni de más de 60 letras: %r' % e.txt('#nuevo-aviso'))
        crear(e, 'Eli @AUT', 'Sagarde')
        crear(e, 'Nuria', '__otra__', 'Nuria @AUT')
        ok(emp_fila(e, 'Nuria') == 'Nuria @AUT', 'T123 un autónomo se crea con su «@AUT»: %r' % emp_fila(e, 'Nuria'))
    con_escena('T123', est10(), t123)

    # --- T124: «Crear» con el nombre de alguien que ya está: no lo duplica; la empresa solo se le pone si no tenía, y nunca se cambia sin avisar
    def t124(e):
        e.ir()
        crear(e, 'ana', 'Manueles')
        ok(e.marcados() == ['Ana'] and ls(e, 'empresas') in (None, []) and 'ya tiene' not in e.toast(), 'T124 misma empresa: lo marca y no apunta nada: %s %s' % (e.marcados(), ls(e, 'empresas')))
        crear(e, 'ANA', 'CATERSYSTEM')
        ok(e.txt('#toast') == '«Ana» ya tiene la empresa «Manueles»: para cambiarla usa el lápiz ✎.' and emp_fila(e, 'Ana') == 'Manueles' and ls(e, 'empresas') in (None, []),
           'T124 otra empresa: avisa y NO la cambia: %r %r %s' % (e.txt('#toast'), emp_fila(e, 'Ana'), ls(e, 'empresas')))
        crear(e, 'dani', 'Sagarde')
        ok(emp_fila(e, 'Dani') == 'Sagarde' and ls(e, 'empresas') == [{'nombre': 'Dani', 'empresa': 'Sagarde'}] and 'Dani' in e.marcados(),
           'T124 quien no tenía empresa la recibe: %r %s' % (emp_fila(e, 'Dani'), ls(e, 'empresas')))
        ok(ls(e, 'nuevos') in (None, []), 'T124 y no se crea un nombre nuevo: %s' % ls(e, 'nuevos'))
    con_escena('T124', est10(), t124)

    # --- T125: el aviso «Se parece a…» no pierde la empresa elegida
    def t125(e):
        e.ir()
        crear(e, 'Anaa', 'Sagarde')
        ok('Se parece a «Ana»' in e.txt('#nuevo-aviso'), 'T125 avisa del parecido: %r' % e.txt('#nuevo-aviso'))
        e.clic('#nuevo-aviso [data-crear="Anaa"]')
        ok(emp_fila(e, 'Anaa') == 'Sagarde' and ls(e, 'empresas') == [{'nombre': 'Anaa', 'empresa': 'Sagarde'}], 'T125 «No, crear» conserva la empresa: %r %s' % (emp_fila(e, 'Anaa'), ls(e, 'empresas')))
        crear(e, 'Betoo', 'CATERSYSTEM')
        e.clic('#nuevo-aviso [data-usar="Beto"]')
        ok(e.txt('#toast') == '«Beto» ya tiene la empresa «Manueles»: para cambiarla usa el lápiz ✎.' and 'Betoo' not in e.filas() and emp_fila(e, 'Beto') == 'Manueles',
           'T125 «Sí» (es Beto) no cambia la empresa de Beto y lo dice: %r' % e.txt('#toast'))
        crear(e, 'Danii', 'Sagarde')
        e.clic('#nuevo-aviso [data-usar="Dani"]')
        ok(emp_fila(e, 'Dani') == 'Sagarde', 'T125 «Sí» (es Dani, que no tenía) le pone la empresa: %r' % emp_fila(e, 'Dani'))
    con_escena('T125', est10(), t125)

    # --- T126: el lápiz muestra la empresa de ahora; cambiarla solo cambia la empresa; volver a la de siempre no deja nada apuntado
    def t126(e):
        e.ir()
        e.clic(lapiz('Ana'))
        ok(e.valor('#ren-empresa') == 'Manueles' and e.valor('#ren-campo') == 'Ana', 'T126 el lápiz abre con la empresa de ahora: %r %r' % (e.valor('#ren-empresa'), e.valor('#ren-campo')))
        ok(opciones_emp(e, '#ren-empresa')[0] == ['', 'Sin empresa'] and opciones_emp(e, '#ren-empresa')[-1] == ['__otra__', 'Otra empresa…'], 'T126 opciones del lápiz: %s' % opciones_emp(e, '#ren-empresa'))
        ok(e.txt('button[data-ren-guardar]') == 'Guardar', 'T126 el botón dice «Guardar» (guarda nombre y empresa)')
        e.clic('button[data-ren-cancelar]')
        e.clic(lapiz('Dani'))
        ok(e.valor('#ren-empresa') == '', 'T126 quien no tiene empresa sale en «Sin empresa»')
        e.clic('button[data-ren-guardar]')
        ok(e.pg.query_selector('#ren-campo') is None and e.txt('#toast') == '', 'T126 guardar sin cambiar nada cierra sin avisar de nada: %r' % e.txt('#toast'))
        ok(ls(e, 'empresas') in (None, []) and ls(e, 'renombres') in (None, []), 'T126 y no apunta nada: %s %s' % (ls(e, 'empresas'), ls(e, 'renombres')))
        e.clic(lapiz('Ana'))
        e.pg.select_option('#ren-empresa', 'CATERSYSTEM')
        ok(e.valor('#ren-campo') == 'Ana', 'T126 cambiar el desplegable no toca lo escrito en el nombre')
        e.clic('button[data-ren-guardar]')
        ok(e.txt('#toast') == 'Empresa de «Ana»: ahora «CATERSYSTEM». Queda apuntado para el PC.' and emp_fila(e, 'Ana') == 'CATERSYSTEM' and e.filas()[0] == 'Ana',
           'T126 solo cambia la empresa: %r %r' % (e.txt('#toast'), emp_fila(e, 'Ana')))
        ok(ls(e, 'empresas') == [{'nombre': 'Ana', 'empresa': 'CATERSYSTEM'}] and ls(e, 'renombres') in (None, []) and cambios(e) == '1 empresa puesta sin enviar al PC',
           'T126 queda apuntada: %s %r' % (ls(e, 'empresas'), cambios(e)))
        e.clic(lapiz('Ana'))
        e.pg.select_option('#ren-empresa', '')
        e.clic('button[data-ren-guardar]')
        ok(e.txt('#toast') == '«Ana» se queda sin empresa. Queda apuntado para el PC.' and e.pg.query_selector('#v-app .row[data-nombre="Ana"] .emp') is None
           and ls(e, 'empresas') == [{'nombre': 'Ana', 'empresa': ''}] and cambios(e) == '1 empresa quitada sin enviar al PC',
           'T126 «Sin empresa» la quita (y el PC debe enterarse): %r %s %r' % (e.txt('#toast'), ls(e, 'empresas'), cambios(e)))
        e.clic(lapiz('Ana'))
        e.pg.select_option('#ren-empresa', 'Manueles')
        e.clic('button[data-ren-guardar]')
        ok(emp_fila(e, 'Ana') == 'Manueles' and ls(e, 'empresas') == [], 'T126 volver a la empresa de siempre no deja nada apuntado: %s' % ls(e, 'empresas'))
        ok(cambios(e) == '', 'T126 y no se cuenta nada: %r' % cambios(e))
    con_escena('T126', est10(), t126)

    # --- T127: nombre y empresa a la vez: viajan los dos, el PC no crea a nadie y no hace falta «nombre nuevo»
    def t127(e):
        e.ir()
        e.clic(lapiz('Ana'))
        e.pg.fill('#ren-campo', 'Ana María')
        e.pg.select_option('#ren-empresa', 'Sagarde')
        e.clic('button[data-ren-guardar]')
        ok(e.txt('#toast') == 'Nombre corregido: «Ana» ahora es «Ana María», empresa «Sagarde». Queda apuntado para el PC.' and 'Ana María' in e.filas() and emp_fila(e, 'Ana María') == 'Sagarde',
           'T127 aviso y fila: %r %s %r' % (e.txt('#toast'), e.filas(), emp_fila(e, 'Ana María')))
        ok(ls(e, 'renombres') == [{'de': 'Ana', 'a': 'Ana María'}] and ls(e, 'empresas') == [{'nombre': 'Ana María', 'empresa': 'Sagarde'}], 'T127 se apuntan las dos cosas: %s %s' % (ls(e, 'renombres'), ls(e, 'empresas')))
        ok(cambios(e) == '1 nombre corregido · 1 empresa puesta sin enviar al PC', 'T127 contadores: %r' % cambios(e))
        e.clic('#v-app .row[data-nombre="Ana María"] .x')
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        ok(lote.get('renombres') == [{'de': 'Ana', 'a': 'Ana María'}] and lote.get('empresas') == [{'nombre': 'Ana María', 'empresa': 'Sagarde'}] and 'altas' not in lote,
           'T127 el fichero lleva el cambio de nombre y la empresa, sin altas: %s' % json.dumps(lote, ensure_ascii=False)[:400])
        valida_con_p1(lote)
        r, por_nombre, cat = e2e_emp(lote)
        ok(r is None or (r['ok'] and por_nombre.get('Ana María') == 'Sagarde' and 'Ana' not in por_nombre and len(por_nombre) == 5),
           'T127 el PC renombra a la misma persona y le pone la empresa: %s' % por_nombre)
    con_escena('T127', est10(), t127)

    # --- T128: corregir solo el nombre arrastra la empresa (la publicada y la que está por enviar)
    def t128(e):
        e.ir()
        renombra(e, 'Beto', 'Beto Zubi')
        ok(emp_fila(e, 'Beto Zubi') == 'Manueles' and ls(e, 'empresas') in (None, []), 'T128 la empresa publicada se va con el nombre sin apuntar nada: %r %s' % (emp_fila(e, 'Beto Zubi'), ls(e, 'empresas')))
        ok(e.txt('#toast') == 'Nombre corregido: «Beto» ahora es «Beto Zubi». Queda apuntado para el PC.', 'T128 el aviso de antes, sin empresa: %r' % e.txt('#toast'))
        e.clic(lapiz('Carlos'))
        e.pg.select_option('#ren-empresa', 'Sagarde')
        e.clic('button[data-ren-guardar]')
        renombra(e, 'Carlos', 'Carlos Ruiz')
        ok(ls(e, 'empresas') == [{'nombre': 'Carlos Ruiz', 'empresa': 'Sagarde'}] and emp_fila(e, 'Carlos Ruiz') == 'Sagarde', 'T128 la empresa apuntada se va con el nombre: %s %r' % (ls(e, 'empresas'), emp_fila(e, 'Carlos Ruiz')))
        ok(ls(e, 'renombres') == [{'de': 'Beto', 'a': 'Beto Zubi'}, {'de': 'Carlos', 'a': 'Carlos Ruiz'}], 'T128 renombres: %s' % ls(e, 'renombres'))
    con_escena('T128', est10(), t128)

    # --- T129: «Otra empresa…» en el lápiz: se escribe, se comprueba y no se pierde lo que había escrito en el nombre
    def t129(e):
        e.ir()
        e.clic(lapiz('Dani'))
        e.pg.fill('#ren-campo', 'Dani Z')
        e.pg.select_option('#ren-empresa', '__otra__')
        ok(e.pg.is_visible('#ren-empresa-otra') and e.pg.evaluate("document.activeElement.id") == 'ren-empresa-otra' and e.valor('#ren-campo') == 'Dani Z',
           'T129 «Otra empresa…» enseña el campo y no pierde el nombre')
        e.clic('button[data-ren-guardar]')
        ok(e.txt('#ren-error') == 'Escribe la empresa.' and e.valor('#ren-campo') == 'Dani Z' and e.valor('#ren-empresa') == '__otra__', 'T129 sin escribir la empresa: %r' % e.txt('#ren-error'))
        e.pg.fill('#ren-empresa-otra', '612 345 678')
        e.clic('button[data-ren-guardar]')
        ok(e.txt('#ren-error') == 'Esa empresa no vale: parece un teléfono.' and e.valor('#ren-empresa-otra') == '612 345 678', 'T129 con un teléfono: %r' % e.txt('#ren-error'))
        e.pg.fill('#ren-empresa-otra', 'Obras Nuevas SL')
        e.pg.press('#ren-empresa-otra', 'Enter')
        ok(e.pg.query_selector('#ren-campo') is None and 'Dani Z' in e.filas() and emp_fila(e, 'Dani Z') == 'Obras Nuevas SL', 'T129 con Intro también guarda: %s %r' % (e.filas(), emp_fila(e, 'Dani Z')))
        ok(ls(e, 'empresas') == [{'nombre': 'Dani Z', 'empresa': 'Obras Nuevas SL'}] and ls(e, 'renombres') == [{'de': 'Dani', 'a': 'Dani Z'}], 'T129 apuntado: %s %s' % (ls(e, 'empresas'), ls(e, 'renombres')))
        e.clic(lapiz('Eli'))
        e.pg.fill('#ren-campo', 'x@y.es')
        e.pg.select_option('#ren-empresa', '__otra__')
        e.pg.fill('#ren-empresa-otra', '')
        e.clic('button[data-ren-guardar]')
        ok(e.txt('#ren-error') == 'Ese nombre no vale: parece un correo.', 'T129 si falla el nombre se dice primero: %r' % e.txt('#ren-error'))
    con_escena('T129', est10(), t129)

    # --- T130: «Añadir varios nombres» con «Nombre, Empresa» (lo que va tras la ÚLTIMA coma)
    TEXTO130 = 'Fran, Manueles\nGaia, Obras Nuevas SL\nHugo\nIker,\n, Ona\nAna, CATERSYSTEM\nDani, Sagarde\nBeto, manueles\nLuz, 612345678\nAnaa, Sagarde'

    def t130(e):
        e.ir()
        e.clic('button[data-varios]')
        e.pg.fill('#varios-texto', TEXTO130)
        e.clic('button[data-varios-ok]')
        res = {k: e.txt('[data-res="%s"]' % k) for k in ('entran', 'estaban', 'puestas', 'otras', 'novalen', 'parecidos')}
        ok(res['entran'] == 'Entran 4: Fran, Gaia, Hugo, Iker. 2 con empresa.', 'T130 entran: %r' % res['entran'])
        ok(res['estaban'] == 'Ya estaban 3: Ana, Dani, Beto.', 'T130 ya estaban: %r' % res['estaban'])
        ok(res['puestas'] == 'Se le pone la empresa a 1: Dani (Sagarde).', 'T130 a quien no tenía se le pone: %r' % res['puestas'])
        ok(res['otras'] == 'Ya tiene otra empresa: «Ana» (Manueles, no CATERSYSTEM). Para cambiarla usa el lápiz ✎.', 'T130 a quien ya tiene otra NO se le cambia: %r' % res['otras'])
        ok(res['novalen'] == 'No valen 2: «, Ona» (falta el nombre); «Luz» (la empresa no vale: parece un teléfono).', 'T130 no valen: %r' % res['novalen'])
        ok(res['parecidos'].startswith('Se parece a alguien que ya está 1: «Anaa» (se parece a «Ana»).'), 'T130 parecidos: %r' % res['parecidos'])
        ok(e.valor('#varios-texto') == ', Ona\nLuz, 612345678\nAnaa, Sagarde', 'T130 en el cuadro quedan las líneas por corregir, enteras (con su empresa): %r' % e.valor('#varios-texto'))
        ok(ls(e, 'altas') == ['Fran', 'Gaia', 'Hugo', 'Iker'] and ls(e, 'nuevos') == ['Fran', 'Gaia', 'Hugo', 'Iker'], 'T130 altas y nuevos: %s %s' % (ls(e, 'altas'), ls(e, 'nuevos')))
        ok(ls(e, 'empresas') == [{'nombre': 'Fran', 'empresa': 'Manueles'}, {'nombre': 'Gaia', 'empresa': 'Obras Nuevas SL'}, {'nombre': 'Dani', 'empresa': 'Sagarde'}],
           'T130 empresas apuntadas: %s' % ls(e, 'empresas'))
        ok(cambios(e) == '4 nombres nuevos · 3 empresas puestas sin enviar al PC', 'T130 contadores: %r' % cambios(e))
        lote = e.exportar() or {}
        ok(lote.get('altas') == ['Fran', 'Gaia', 'Hugo', 'Iker'] and len(lote.get('empresas', [])) == 3 and lote.get('jornadas') == [], 'T130 el fichero: %s' % json.dumps(lote, ensure_ascii=False)[:400])
        valida_con_p1(lote)
        r, por_nombre, cat = e2e_emp(lote)
        ok(r is None or (r['ok'] and por_nombre.get('Fran') == 'Manueles' and por_nombre.get('Gaia') == 'Obras Nuevas SL' and por_nombre.get('Dani') == 'Sagarde' and por_nombre.get('Hugo') == ''),
           'T130 el PC los crea con su empresa: %s' % por_nombre)
    con_escena('T130', est10(), t130)

    # --- T131: una coma dentro del nombre vale (la empresa es lo que va tras la última); sin coma, sin empresa
    def t131(e):
        e.ir()
        e.clic('button[data-varios]')
        e.pg.fill('#varios-texto', 'García, Pedro, Manueles\nSolo Nombre\nMarta ,Sagarde')
        e.clic('button[data-varios-ok]')
        ok(ls(e, 'altas') == ['García, Pedro', 'Solo Nombre', 'Marta'] and ls(e, 'empresas') == [{'nombre': 'García, Pedro', 'empresa': 'Manueles'}, {'nombre': 'Marta', 'empresa': 'Sagarde'}],
           'T131 coma dentro del nombre: %s %s' % (ls(e, 'altas'), ls(e, 'empresas')))
        ok(e.txt('[data-res="entran"]') == 'Entran 3: García, Pedro, Solo Nombre, Marta. 2 con empresa.', 'T131 resumen: %r' % e.txt('[data-res="entran"]'))
    con_escena('T131', est10(), t131)

    # --- T132: «Enviar al PC» cuenta las empresas en el bloque de nombres y en el recuadro «Listo»
    def t132(e):
        e.ir()
        e.clic('nav button[data-v="enviar"]')
        lis = e.pg.eval_on_selector_all('#envio-nombres li', 'e=>e.map(l=>l.textContent.trim())')
        ok(lis == ['2 empresas puestas y 1 empresa quitada: «Ana» → «CATERSYSTEM», «Dani» → «Sagarde», «Beto» sin empresa'], 'T132 bloque de nombres: %s' % lis)
        e.exportar()
        ok(e.listo().endswith('con 1 jornada, 2 empresas puestas y 1 empresa quitada. Ahora mándalo al PC.'), 'T132 recuadro: %r' % e.listo())
    emp132 = [{'nombre': 'Ana', 'empresa': 'CATERSYSTEM'}, {'nombre': 'Dani', 'empresa': 'Sagarde'}, {'nombre': 'Beto', 'empresa': ''}]
    con_escena('T132', est10(), t132, init=sembrar_varios({'sgd_personal_empresas': emp132, 'sgd_personal_pendientes': [pend9('2026-10-22', ['Ana'])]}))

    # --- T132b: solo empresas (sin jornadas): también hay bloque y botón, y el fichero lleva las empresas y ninguna jornada
    def t132b(e):
        e.ir()
        e.clic('nav button[data-v="enviar"]')
        ok(e.txt('#resumen-envio') == 'Tienes cambios sin enviar:' and e.pg.query_selector('button[data-preparar="olabeaga"]') is not None, 'T132b solo con empresas hay bloque y botón: %r' % e.txt('#resumen-envio'))
        lote = e.exportar() or {}
        ok(lote.get('empresas') == [{'nombre': 'Ana', 'empresa': 'CATERSYSTEM'}] and lote.get('jornadas') == [] and 'altas' not in lote and e.listo().endswith('con 1 empresa puesta. Ahora mándalo al PC.'),
           'T132b fichero y recuadro: %s %r' % (lote, e.listo()))
        valida_con_p1(lote)
        r, por_nombre, cat = e2e_emp(lote)
        ok(r is None or (r['ok'] and por_nombre.get('Ana') == 'CATERSYSTEM' and por_nombre.get('Beto') == '' and len(por_nombre) == 5), 'T132b el PC le pone la empresa a Ana: %s' % por_nombre)
    con_escena('T132b', est10(), t132b, init=sembrar('sgd_personal_empresas', [{'nombre': 'Ana', 'empresa': 'CATERSYSTEM'}]))

    # --- T133: las empresas apuntadas se olvidan cuando el estado publicado ya las trae (sin tildes ni mayúsculas); las demás se quedan
    def t133(e):
        e.ir()
        ok(ls(e, 'empresas') == [{'nombre': 'Dani', 'empresa': 'Sagarde'}], 'T133 queda solo lo que el PC aún no trae: %s' % ls(e, 'empresas'))
        ok(emp_fila(e, 'Ana') == 'Manueles' and emp_fila(e, 'Dani') == 'Sagarde' and e.pg.query_selector('#v-app .row[data-nombre="Beto"] .emp') is None, 'T133 la lista: %r %r' % (emp_fila(e, 'Ana'), emp_fila(e, 'Dani')))
    pub133 = [('Ana', 'Manueles'), ('Beto', ''), ('Carlos', 'CATERSYSTEM'), ('Dani', ''), ('Eli', 'Eli @AUT')]
    ls133 = [{'nombre': 'Ana', 'empresa': 'MANUELES'}, {'nombre': 'Beto', 'empresa': ''}, {'nombre': 'Dani', 'empresa': 'Sagarde'}]
    con_escena('T133', est10(pub133), t133, init=sembrar('sgd_personal_empresas', ls133))

    # --- T133b: una misma empresa con dos grafías (una apuntada a mano) sale una sola vez en los desplegables
    def t133b(e):
        e.ir()
        ok(opciones_emp(e, '#nuevo-empresa').count(['Manueles', 'Manueles']) == 1 and ['MANUELES', 'MANUELES'] not in opciones_emp(e, '#nuevo-empresa'),
           'T133b la empresa sale una sola vez, con la grafía que ya constaba: %s' % opciones_emp(e, '#nuevo-empresa'))
    con_escena('T133b', est10(), t133b, init=sembrar('sgd_personal_empresas', [{'nombre': 'Dani', 'empresa': 'MANUELES'}]))

    # --- T134: sin usar nada de lo nuevo el fichero es el de siempre (ni «empresas» ni «altas»)
    def t134(e):
        e.ir()
        e.clic('#v-app .row[data-nombre="Ana"] .x')
        e.clic('#v-app .row[data-nombre="Carlos"] .x')
        e.clic('button[data-guardar]')
        lote = e.exportar() or {}
        ok(sorted(lote) == ['jornadas', 'obra', 'tipo', 'version'] and [p['nombre'] for p in lote['jornadas'][0]['presentes']] == ['Ana', 'Carlos'],
           'T134 el fichero solo lleva lo de siempre: %s' % sorted(lote))
        ok('1 jornada.' in e.listo() and 'empresa' not in e.listo(), 'T134 y el recuadro no habla de empresas: %r' % e.listo())
        ok(cambios(e) == '', 'T134 ni hay contadores de nombres: %r' % cambios(e))
    con_escena('T134', est10(), t134)

    # --- T135: al juntar a dos personas manda la empresa de la que ya existía con ese nombre
    def t135(e):
        e.ir()
        e.clic(lapiz('Dani'))
        e.pg.select_option('#ren-empresa', 'Sagarde')
        e.clic('button[data-ren-guardar]')
        renombra(e, 'Dani', 'Ana')
        ok(e.filas().count('Ana') == 1 and 'Dani' not in e.filas() and emp_fila(e, 'Ana') == 'Manueles', 'T135 la que ya era Ana conserva su empresa: %s %r' % (e.filas(), emp_fila(e, 'Ana')))
        ok(ls(e, 'empresas') in (None, []), 'T135 y la empresa que estaba por enviar para Dani desaparece: %s' % ls(e, 'empresas'))
        ok('pasan a ser la misma persona' in e.txt('#toast') and 'empresa' not in e.txt('#toast'), 'T135 aviso de unión sin hablar de empresa: %r' % e.txt('#toast'))
    con_escena('T135', est10(), t135)

    # --- T136: lo que se escribe a mano en la empresa nunca se interpreta como HTML
    RARA = '<b>x</b> & "y" \'z\''
    def t136(e):
        e.ir()
        ok(emp_fila(e, 'Ana') == RARA and e.pg.evaluate("document.querySelectorAll('#v-app .emp *').length") == 0, 'T136 la empresa sale como texto en la lista: %r' % emp_fila(e, 'Ana'))
        e.clic(lapiz('Ana'))
        ok(e.pg.evaluate("document.querySelectorAll('#ren-empresa *:not(option)').length") == 0 and e.valor('#ren-empresa') == RARA, 'T136 y en el desplegable del lápiz: %r' % e.valor('#ren-empresa'))
        e.clic('button[data-ren-cancelar]')
        ok(e.pg.evaluate("document.querySelectorAll('#nuevo-empresa *:not(option)').length") == 0, 'T136 y en el de nombre nuevo')
    con_escena('T136', est10([('Ana', RARA), ('Beto', '')]), t136)

    # --- T137: lo que haya en sgd_personal_empresas, por dañado que esté, no tumba la app y solo se queda lo que vale
    def t137(e):
        e.ir()
        ok(e.filas() == ['Ana', 'Beto', 'Carlos', 'Dani', 'Eli'] and ls(e, 'empresas') == [{'nombre': 'Dani', 'empresa': 'Sagarde'}], 'T137 solo queda lo válido: %s' % ls(e, 'empresas'))
    mala137 = [{'nombre': 'Dani', 'empresa': 'Sagarde'}, {'nombre': 5, 'empresa': 'X'}, {'nombre': 'Ana'}, {'nombre': '', 'empresa': 'X'}, 'cadena', None, {'nombre': 'Beto', 'empresa': 7}]
    con_escena('T137', est10(), t137, init=sembrar('sgd_personal_empresas', mala137))

    def t137b(e):
        e.ir()
        ok(e.filas() == ['Ana', 'Beto', 'Carlos', 'Dani', 'Eli'] and ls(e, 'empresas') == [], 'T137 un valor que no es una lista no tumba la app y queda vacío: %s' % ls(e, 'empresas'))
    con_escena('T137 no lista', est10(), t137b, init=sembrar('sgd_personal_empresas', {'a': 1}))

    # --- T138: alguien creado aquí con empresa y corregido antes de enviarlo: va como nombre nuevo con su empresa y SIN cambio de nombre
    def t138(e):
        e.ir()
        crear(e, 'Fran', 'Manueles')
        renombra(e, 'Fran', 'Franco')
        ok(ls(e, 'renombres') in (None, []) and ls(e, 'empresas') == [{'nombre': 'Franco', 'empresa': 'Manueles'}] and ls(e, 'nuevos') == ['Franco'],
           'T138 un nombre que el PC nunca vio no se apunta como cambio: %s %s %s' % (ls(e, 'renombres'), ls(e, 'empresas'), ls(e, 'nuevos')))
        lote = e.exportar() or {}
        ok(lote.get('altas') == ['Franco'] and lote.get('empresas') == [{'nombre': 'Franco', 'empresa': 'Manueles'}] and 'renombres' not in lote, 'T138 fichero: %s' % json.dumps(lote, ensure_ascii=False)[:300])
        r, por_nombre, cat = e2e_emp(lote)
        ok(r is None or (r['ok'] and por_nombre.get('Franco') == 'Manueles' and 'Fran' not in por_nombre), 'T138 el PC: %s' % por_nombre)
    con_escena('T138', est10(), t138)

    # --- T139: la pantalla cabe y se puede pulsar en un móvil estrecho (320 px) y en una tableta (820 px)
    def t139(e):
        e.ir()
        e.clic(lapiz('Ana'))
        e.pg.select_option('#ren-empresa', '__otra__')
        cajas = e.pg.evaluate("""()=>{const q=s=>{const x=document.querySelector(s);if(!x)return null;const r=x.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]};
          return {sel:q('#ren-empresa'),otra:q('#ren-empresa-otra'),nuevo:q('#nuevo-empresa'),crear:q('button[data-nuevo]'),nuevoCampo:q('#nuevo'),guardar:q('button[data-ren-guardar]'),
                  ancho:document.documentElement.scrollWidth<=window.innerWidth+1}}""")
        ok(cajas['ancho'] and cajas['sel'][1] >= 44 and cajas['otra'][1] >= 44 and cajas['nuevo'][1] >= 44 and cajas['crear'][1] >= 48 and cajas['crear'][0] >= cajas['nuevoCampo'][0] - 2 and cajas['guardar'][1] >= 48,
           'T139 todo cabe y se puede pulsar con el dedo a %s px: %s' % (e.pg.viewport_size['width'], cajas))
        e.clic('button[data-ren-cancelar]')
        ok(e.pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), 'T139 la lista con empresas no se sale de ancho')
    for ancho in (320, 820):
        con_escena('T139', est10([('Ana', 'Construcciones y Reformas Muñoz de Bilbao S.L.'), ('Beto', 'CATERSYSTEM'), ('Carlos', '')]), t139, ancho=ancho, alto=900)

    # Fin del bloque del paso 08c2a

    # ======================================================================================================================
    # Bloque del paso 08c2b: la suma por empresa en el Informe de la tablet (y la empresa junto al nombre). Escenas T140 en
    # adelante (P3_SOLO_08C2B=1 corre solo estas). Fecha fija: viernes 23/10/2026. Datos inventados; cifras hechas a mano.
    # ======================================================================================================================
    CAB_EMP = ['Empresa', 'Personas', 'Días', 'Horas', '% de impacto']

    def tabla_emp(e):
        return e.pg.eval_on_selector_all('#v-informe table.emp-tabla tr', "f=>f.map(r=>[...r.children].map(c=>c.textContent.trim()))")

    def informe_toda_la_obra(e):
        e.clic('button[data-v="informe"]')
        e.clic('#v-informe button[data-p="obra"]')

    # Ana 3 días, Beto 1, Carlos 2, Dani 2, Eli 2 (7,5 h cada día): 75 h y 10 días de persona en total.
    FILAS140 = viv('2026-10-19', 'Ana', 'Beto', 'Carlos', 'Eli') + viv('2026-10-20', 'Ana', 'Carlos', 'Dani', 'Eli') + viv('2026-10-21', 'Ana', 'Dani')
    # El PC publica la empresa de cada persona también dentro de sus jornadas (quien no tiene, sin clave): la escena lo imita.
    for fila_140 in FILAS140:
        empresa_140 = dict(PERS).get(fila_140['nombre'])
        if empresa_140:
            fila_140['empresa'] = empresa_140
    EST140 = est10(filas=FILAS140, ultima=u('2026-10-21', 'Ana', 'Dani'))

    # --- T140: la tabla «Por empresa» con las cifras a mano; «Sin empresa» al final aunque empate en horas; el total de autónomos debajo
    def t140(e):
        e.ir()
        informe_toda_la_obra(e)
        ok(tabla_emp(e) == [CAB_EMP,
                            ['Manueles', '2', '4', '30', '40 %'], ['CATERSYSTEM', '1', '2', '15', '20 %'], ['Eli @AUT', '1', '2', '15', '20 %'],
                            ['Sin empresa', '1', '2', '15', '20 %'], ['Total', '5', '10', '75', '100 %'],
                            ['Total autónomos (@AUT)', '1', '2', '15', '20 %']],
           'T140 tabla por empresa: %s' % tabla_emp(e))
        ok(e.txt('#v-informe .emp-bloque h4') == 'Por empresa', 'T140 el bloque lleva su título «Por empresa»: %r' % e.txt('#v-informe .emp-bloque h4'))
        ok('no se suman otra vez' in e.txt('#v-informe .emp-bloque .nota'), 'T140 la nota explica que el total de autónomos ya está contado')
        ok(e.pg.evaluate("document.querySelectorAll('#v-informe table.emp-tabla tfoot tr').length") == 2, 'T140 el total y el total de autónomos van en el pie')
        ok(e.pg.evaluate("document.querySelectorAll('#v-informe table.emp-tabla tbody tr.emp-total-aut').length") == 0,
           'T140 el total de autónomos NO está entre las líneas que se suman')
    con_escena('T140', EST140, t140)

    # --- T141: la empresa en pequeño junto al nombre en la tabla de personas; quien no tiene, nada; la tabla de personas sigue igual
    def t141(e):
        e.ir()
        informe_toda_la_obra(e)
        quien = e.pg.eval_on_selector_all('#v-informe table.data tbody tr', "f=>f.map(r=>[r.children[0].childNodes[0].textContent.trim(), (r.querySelector('.nom-emp')||{}).textContent||null])")
        ok(quien == [['Ana', 'Manueles'], ['Carlos', 'CATERSYSTEM'], ['Dani', None], ['Eli', 'Eli @AUT'], ['Beto', 'Manueles']], 'T141 empresa junto al nombre: %s' % quien)
        ok(len(e.informe()) == 5, 'T141 sigue habiendo una fila por persona: %s' % e.informe())
    con_escena('T141', EST140, t141)

    # --- T142: una obra sin empresas puestas solo enseña «Sin empresa» (y no inventa autónomos)
    def t142(e):
        e.ir()
        informe_toda_la_obra(e)
        ok(tabla_emp(e) == [CAB_EMP, ['Sin empresa', '2', '2', '15', '100 %'], ['Total', '2', '2', '15', '100 %']], 'T142 sin empresas: %s' % tabla_emp(e))
        ok(e.pg.evaluate("document.querySelectorAll('#v-informe .nom-emp').length") == 0 and 'Total autónomos' not in e.txt('#v-informe'),
           'T142 sin empresas no sale nada junto a los nombres ni línea de autónomos')
    con_escena('T142', est10(personas=[('Ana', ''), ('Beto', '')], filas=viv('2026-10-22', 'Ana', 'Beto')), t142)

    # --- T143: lo que se apunta en la tablet (aún sin enviar) manda: Ana pasa de Manueles a Sagarde y el informe lo enseña
    def t143(e):
        e.ir()
        e.clic(lapiz('Ana'))
        e.pg.select_option('#ren-empresa', 'Sagarde')
        e.clic('button[data-ren-guardar]')
        informe_toda_la_obra(e)
        ok(tabla_emp(e) == [CAB_EMP,
                            ['Sagarde', '1', '3', '22,5', '30 %'], ['CATERSYSTEM', '1', '2', '15', '20 %'], ['Eli @AUT', '1', '2', '15', '20 %'],
                            ['Manueles', '1', '1', '7,5', '10 %'], ['Sin empresa', '1', '2', '15', '20 %'], ['Total', '5', '10', '75', '100 %'],
                            ['Total autónomos (@AUT)', '1', '2', '15', '20 %']],
           'T143 empresa apuntada en la tablet: %s' % tabla_emp(e))
    con_escena('T143', EST140, t143)

    # --- T144: una jornada guardada y aún sin enviar cuenta en la empresa de cada persona
    def t144(e):
        e.ir()
        informe_toda_la_obra(e)
        ok(tabla_emp(e) == [CAB_EMP,
                            ['Manueles', '2', '4', '30', '33,3 %'], ['Eli @AUT', '1', '3', '22,5', '25 %'], ['CATERSYSTEM', '1', '2', '15', '16,7 %'],
                            ['Sin empresa', '1', '3', '22,5', '25 %'], ['Total', '5', '12', '90', '100 %'],
                            ['Total autónomos (@AUT)', '1', '3', '22,5', '25 %']],
           'T144 con una jornada sin enviar: %s' % tabla_emp(e))
    con_escena('T144', EST140, t144, init=sembrar('sgd_personal_pendientes', [pend9('2026-10-23', ['Dani', 'Eli'])]))

    # --- T145: el nombre de una empresa nunca se interpreta como HTML
    def t145(e):
        e.ir()
        informe_toda_la_obra(e)
        ok(e.pg.evaluate("document.querySelectorAll('#v-informe table.emp-tabla td b, #v-informe .nom-emp b').length") == 0, 'T145 no debe nacer un <b> del nombre de la empresa')
        ok(tabla_emp(e)[1][0] == '<b>x</b> & Co' and e.txt('#v-informe .nom-emp') == '<b>x</b> & Co', 'T145 se ve tal cual: %s %r' % (tabla_emp(e), e.txt('#v-informe .nom-emp')))
    con_escena('T145', est10(personas=[('Ana', '<b>x</b> & Co')], filas=viv('2026-10-22', 'Ana')), t145)

    # --- T146: el informe cabe a 320, 390 y 820 px aunque haya empresas muy largas
    def t146(e):
        e.ir()
        informe_toda_la_obra(e)
        ok(e.pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), 'T146 el informe no se sale de ancho a %s px' % e.pg.viewport_size['width'])
        sobra = e.pg.evaluate("[...document.querySelectorAll('#v-informe .emp-bloque *')].filter(x=>x.getBoundingClientRect().right > window.innerWidth + 1).length")
        ok(sobra == 0, 'T146 nada del bloque «Por empresa» queda fuera de la pantalla a %s px (%s elementos)' % (e.pg.viewport_size['width'], sobra))
    for ancho in (320, 390, 820):
        con_escena('T146', est10([('Ana', 'Construcciones y Reformas Muñoz de Bilbao S.L.'), ('Beto', 'CATERSYSTEM'), ('Carlos', 'Eli @AUT'), ('Dani', '')]), t146, ancho=ancho, alto=900)

    # --- T147: Todo / Viviendas / Garajes también cambia la suma por empresa (y el periodo, el mes)
    def t147(e):
        e.ir()
        e.clic('button[data-v="informe"]')
        e.clic('#v-informe button[data-p="obra"]')
        e.clic('#v-informe button[data-a="garaje"]')
        ok(tabla_emp(e) == [CAB_EMP, ['CATERSYSTEM', '1', '1', '8', '100 %'], ['Total', '1', '1', '8', '100 %']], 'T147 solo garajes: %s' % tabla_emp(e))
        e.clic('#v-informe button[data-a="vivienda"]')
        ok(tabla_emp(e) == [CAB_EMP, ['Manueles', '1', '1', '7,5', '50 %'], ['Sin empresa', '1', '1', '7,5', '50 %'], ['Total', '2', '2', '15', '100 %']],
           'T147 solo viviendas: %s' % tabla_emp(e))
        e.clic('#v-informe button[data-a="todo"]')
        e.clic('#v-informe button[data-p="mes"]')
        ok(tabla_emp(e) == [CAB_EMP, ['CATERSYSTEM', '1', '1', '8', '51,6 %'], ['Sin empresa', '1', '1', '7,5', '48,4 %'], ['Total', '2', '2', '15,5', '100 %']],
           'T147 solo octubre (la jornada de septiembre de Manueles no cuenta): %s' % tabla_emp(e))
    filas_147 = [dict(fila('2026-09-30', 'vivienda', 'Ana', 7.5), empresa='Manueles'), dict(fila('2026-10-22', 'vivienda', 'Dani', 7.5)),
                 dict(fila('2026-10-22', 'garaje', 'Carlos', 8), empresa='CATERSYSTEM')]
    con_escena('T147', est10(filas=filas_147, ultima=u('2026-10-22', 'Dani')), t147)

    # Fin del bloque del paso 08c2b

    # Fin del bloque del paso 08d

    # Fin del bloque del paso 08c
    ok(not errs, 'errores de JavaScript: %s' % errs)
    b.close()

shutil.rmtree(SANDBOX, ignore_errors=True)
if fallos:
    print('\n%d fallos' % len(fallos))
    sys.exit(1)
print('OK: todas las comprobaciones')
