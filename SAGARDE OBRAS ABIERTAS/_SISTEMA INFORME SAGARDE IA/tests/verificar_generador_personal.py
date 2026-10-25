# -*- coding: utf-8 -*-
"""Escenas de navegador de la app de la tablet (generador_personal.html). Playwright (Python). Exit 0 = todo bien.
Lo lanza tests/test_generador_personal.py (≈ 7 min); también se puede ejecutar a mano:
    py -3.11 tests/verificar_generador_personal.py        (P3_RAPIDO=1 para en el primer fallo)
Monta una carpeta de pruebas con la app, personal_calculo.js y un personal_estado.js inventado, fija la
fecha en el 23/10/2026 y recorre el flujo completo. El lote que exporta la app se valida con personal_obra.py
(P1). Viene del verificador de staging (paso 06): solo cambia de dónde salen la app, P1 y la carpeta de pruebas.
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
ok(not re.search(r'(?m)^\s*(?:save|exportar|render|init|appView|jornadasView|infoView|loadList|restore|reconcile)\s*=\s*(?:function|\()', html), 'no se reasignan funciones ya declaradas (save=function…): edita la función original')
ok(len(re.findall(r'\bfunction (?:save|exportar|render|init|appView|jornadasView|infoView|loadList)\b', html)) == 8, 'cada función principal debe estar declarada una sola vez')
# añadida en el paso 01b: las preguntas van dentro de la página, nunca con ventanas del navegador (en el iPad bloquean o no se ven)
ok(not re.search(r'(?<![\w.])(?:confirm|alert|prompt)\s*\(', html), 'no se usan confirm(), alert() ni prompt(): las preguntas van dentro de la página')
ok(len(re.findall(r'\bfunction (?:guardarPropio|horarioDe)\b', html)) == 2, 'guardarPropio(nombre, objeto) y horarioDe(nombre, fecha) deben estar declaradas una sola vez')

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

    def exportar():
        try:
            with pg.expect_download(timeout=5000) as d:
                pg.click('button[data-exportar]', timeout=3000)
            ruta = os.path.join(SANDBOX, 'descarga.json')
            d.value.save_as(ruta)
            return json.load(open(ruta, encoding='utf-8'))
        except Exception as e:  # noqa: BLE001
            ok(False, 'exportar no descarga un JSON válido con button[data-exportar]: %s' % str(e)[:160])
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
        ok('publicado' in txt('#estado-origen').lower(), '#estado-origen debe decir «publicado» cuando carga personal_estado.js: %r' % txt('#estado-origen'))
        ok(any('personal_estado.js?v=' in u for u in peticiones), 'personal_estado.js debe pedirse con ?v=<marca de tiempo> para saltarse la caché')
        ok(pg.is_visible('#sin-estado') is False if pg.query_selector('#sin-estado') else True, '#sin-estado no debe verse si hay estado')
        ok(pg.query_selector('#aviso-instalar') is not None and 'pantalla de inicio' in txt('#aviso-instalar'), 'falta #aviso-instalar con el texto «pantalla de inicio»')
        ok(valor('#fecha') == '2026-10-23', '#fecha debe empezar en hoy (23/10/2026): %r' % valor('#fecha'))

    except Exception as e:  # noqa: BLE001
        ok(False, 'T0 se interrumpio: %s' % (str(e).strip().splitlines() or [repr(e)])[0][:220])
    try:
        # --- T1: lista inicial = última jornada + habituales, todos sin marcar (propuesta B)
        ok(filas_lista() == ['Mikel', 'Txomin', 'Rafa'], 'lista inicial de viviendas: última jornada + habituales (≥ 3 días en 30): %s' % filas_lista())
        ok(marcados() == [], 'la lista inicial debe empezar sin nadie marcado: %s' % marcados())
        clic('button[data-amb="garaje"]')
        ok(filas_lista() == ['Andoni'], 'lista inicial de garajes: %s' % filas_lista())
        ok('on' in (pg.get_attribute('button[data-amb="garaje"]', 'class') or ''), 'el ámbito activo debe llevar la clase on')
        clic('button[data-amb="vivienda"]')
        ok(filas_lista() == ['Mikel', 'Txomin', 'Rafa'], 'al volver a viviendas vuelve su lista: %s' % filas_lista())

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
        ok('copia' in txt('#estado-origen').lower(), '#estado-origen debe decir «copia» al usar la copia local: %r' % txt('#estado-origen'))

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
            self.pg.on('pageerror', lambda e: self.errs.append(str(e)))

        def ir(self, esperar_obra=True):
            self.pg.goto(self.url)
            if esperar_obra:
                try:
                    self.pg.wait_for_selector('#obra', timeout=3000)
                except Exception:  # noqa: BLE001
                    pass
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

        def obra(self, v):
            self.pg.select_option('#obra', v)

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

        def exportar(self, esperar=True):
            try:
                with self.pg.expect_download(timeout=5000 if esperar else 1500) as d:
                    self.pg.click('button[data-exportar]', timeout=3000)
                ruta = os.path.join(self.dir, 'descarga.json')
                d.value.save_as(ruta)
                return json.load(open(ruta, encoding='utf-8'))
            except Exception:  # noqa: BLE001
                return None

        def informe(self):
            return self.pg.eval_on_selector_all('#v-informe table.data tbody tr', 'e=>e.map(r=>r.innerText.split(String.fromCharCode(10)).join(" ").split(String.fromCharCode(9)).join(" ").trim())')

    def con_escena(nombre, datos, fn, **kw):
        """Ejecuta una escena; cualquier excepción se convierte en un fallo legible y no tumba las demás."""
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
        e.ir()
        ok(e.filas() == ['Fran', 'Ana', 'Beto', 'Dani'], 'T16 lista de viviendas = última jornada (en su orden) + habituales por nombre, sin repetir: %s' % e.filas())
        ok(e.marcados() == [], 'T16 la lista inicial va sin marcar')
        e.clic('button[data-amb="garaje"]')
        ok(e.filas() == ['Hugo'], 'T16 lista de garajes: solo cuentan las fechas del propio ámbito (Eva: 2 de garaje + 2 de vivienda no es habitual): %s' % e.filas())
    d16 = [fila(f, 'vivienda', 'Ana', 7.5) for f in ('2026-10-05', '2026-10-06')]  # 2 días: no es habitual
    d16 += [fila(f, 'vivienda', 'Beto', 7.5) for f in ('2026-09-23', '2026-10-01', '2026-10-02')]  # 09-23 = justo 30 días antes (incluido)
    d16 += [fila(f, 'vivienda', 'Carlos', 7.5) for f in ('2026-09-22', '2026-10-01', '2026-10-02')]  # 09-22 = 31 días antes (fuera): solo 2
    d16 += [fila(f, 'vivienda', 'Dani', 7.5) for f in ('2026-10-14', '2026-10-15', '2026-10-16')]
    d16 += [fila(f, 'vivienda', 'Eva', 7.5) for f in ('2026-10-21', '2026-10-22')] + [fila(f, 'garaje', 'Eva', 7.5) for f in ('2026-10-19', '2026-10-20')]
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
        ok('exportad' in e.toast(), 'T29 exportar debe confirmar con un aviso «Exportadas N jornadas…»: %r' % e.toast())
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
        ok('no hay' in e.toast(), 'T34 debe avisar «No hay jornadas pendientes en esta obra»: %r' % e.toast())
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
        ok('copia' in e.txt('#estado-origen').lower() and e.pendientes() == '1', 'T43 sin red usa la copia local y conserva el pendiente: %r %r' % (e.txt('#estado-origen'), e.pendientes()))
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
        ok(e.txt('#estado-origen') == 'Estado publicado · 23/10/2026 08:00', 'T48 #estado-origen: %r' % e.txt('#estado-origen'))
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
        ok(chip(e, 'Aitor', True) == 'horario propio 9 h' and chip(e, 'Gorka', True) == 'horario propio 9 h', 'T52 quien tiene horario propio lleva el chip «horario propio 9 h»: %r %r' % (chip(e, 'Aitor', True), chip(e, 'Gorka', True)))
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
        ok(e.exportar(esperar=False) is None and 'no hay' in e.toast(), 'T53 recargada con el estado nuevo ya no queda nada que exportar: %r' % e.toast())
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
        ok(e.horas('Gorka') == '8 h' and chip(e, 'Gorka', True) == 'horario propio 8 h', 'T55b el lunes Gorka tiene horario propio de 8 h: %r %r' % (e.horas('Gorka'), chip(e, 'Gorka', True)))
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
        ok('copia' in e.txt('#estado-origen').lower(), 'T63a debe decir que usa la copia guardada: %r' % e.txt('#estado-origen'))
        e.pg.wait_for_timeout(max(0, int((8.5 - (time.time() - t0)) * 1000)))
        ok('copia' in e.txt('#estado-origen').lower() and e.pg.query_selector('#obra') is not None, 'T63a cuando el .js llega tarde no se cambia lo que se está viendo: %r' % e.txt('#estado-origen'))
    t63('T63a', 8, True, f63a)

    def f63b(e, t0):
        t = espera_obra_hasta(e, t0, 8)
        ok(t is not None and t <= 3.5, 'T63b si el .js llega a los 1,5 s la app abre sin esperar a los 4 s: abrió a los %s s' % (None if t is None else round(t, 1)))
        ok('publicado' in e.txt('#estado-origen').lower(), 'T63b debe decir «publicado»: %r' % e.txt('#estado-origen'))
    t63('T63b', 1.5, True, f63b)

    def f63c(e, t0):
        e.pg.wait_for_timeout(5000)
        sin = e.pg.query_selector('#sin-estado') is not None and e.pg.is_visible('#sin-estado')
        ok(e.pg.query_selector('#obra') is None and not sin, 'T63c sin copia guardada no hay con qué abrir: la app sigue esperando (no enseña «todavía no hay datos»): sin_datos=%s' % sin)
        t = espera_obra_hasta(e, t0, 12)
        ok(t is not None and 'publicado' in e.txt('#estado-origen').lower(), 'T63c cuando por fin llega el .js (a los 7 s) la app abre con él: %r' % e.txt('#estado-origen'))
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
            ok(e.exportar() is not None and '2 horario(s) propio(s)' in e.toast() and '1 jornada(s)' in e.toast(), 'T53b el aviso de exportar cuenta jornadas y horarios propios: %r' % e.toast())
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
            ok(t is not None and 'tarda en llegar' in e.txt('#estado-origen').lower() and 'copia guardada en este aparato' in e.txt('#estado-origen').lower(), 'T63d cuando abre por la espera dice que el estado publicado tarda en llegar: %r' % e.txt('#estado-origen'))
        t63('T63d', 6, True, f63d)

    if GRUPO_B:
        # --- T65 (B): el ejemplo de Bixente metiendo el horario propio con la pantalla
        def t65(e):
            e.ir()
            marcar_los_cinco(e)
            ok(all(e.pg.query_selector('#v-app .row[data-nombre="%s"] button[data-hp-abrir]' % n) is not None for n in CINCO), 'T65 cada presente lleva su botón «Horario propio» (button[data-hp-abrir])')
            ok(all('horario propio' in e.txt('#v-app .row[data-nombre="%s"] button[data-hp-abrir]' % n).lower() for n in CINCO), 'T65 el botón dice «Horario propio»')
            for n in ('Aitor', 'Gorka'):
                fila_n = '#v-app .row[data-nombre="%s"]' % n
                e.clic(fila_n + ' button[data-hp-abrir]')
                ok(e.pg.query_selector(fila_n + ' .hp') is not None and e.pg.is_visible(fila_n + ' .hp'), 'T65 el editor se abre dentro de la misma fila de %s' % n)
                ok(e.pg.eval_on_selector_all(fila_n + ' .hp input[data-hp]', 'e=>e.map(i=>i.dataset.hp)') == ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom'], 'T65 siete casillas, de lunes a domingo, en %s' % n)
                e.pg.fill(fila_n + ' input[data-hp="vie"]', '9')
                e.clic(fila_n + ' button[data-hp-guardar]')
                ok(e.pg.query_selector(fila_n + ' .hp') is None, 'T65 el editor se cierra al guardar')
            ok(horas5(e) == H_9 and e.txt('.sum') == '5 presentes · 40,5 h', 'T65 con la pantalla: Aitor y Gorka a 9 h, resumen 40,5 h: %s %r' % (horas5(e), e.txt('.sum')))
            ok(chip(e, 'Aitor', True) == 'horario propio 9 h', 'T65 chip de horario propio tras guardar: %r' % chip(e, 'Aitor', True))
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
            ok('aitor' in tx and 'sigue el horario de la obra' in tx and 'guardar horario propio' in tx and 'quitar' in tx, 'T66 el editor dice de quién es, qué significa vacío y lleva «Guardar horario propio» y «Quitar»: %r' % tx)
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
            ok('no se pudo' in e.toast() and 'horario propio guardado' not in e.toast(), 'T70 sin poder escribir en el aparato, «Guardar horario propio» avisa del fallo y no dice «guardado»: %r' % e.toast())
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
            ok(e.txt('#v-app .hp b') == 'Horario propio de ' + raro, 'T72 el título del editor lleva el nombre tal cual: %r' % e.txt('#v-app .hp b'))
            ok(e.pg.evaluate("document.querySelectorAll('#v-app .hp b *').length") == 0 and e.pg.evaluate("document.querySelectorAll('#v-app .hp b').length") == 1, 'T72 no se interpreta HTML dentro del nombre del editor')
            e.pg.fill('#v-app .hp input[data-hp="vie"]', '9')
            e.clic('#v-app .hp button[data-hp-guardar]')
            ok(json.loads(propio_ls(e) or '{}') == {'olabeaga': {raro: {'vie': 9}}}, 'T72 el horario propio se guarda con el nombre raro intacto: %r' % propio_ls(e))
            valida_con_p1(e.exportar() or {})
        con_escena('T72', estado_con({'olabeaga': obra_est('2026 OLABEAGA', [], ultima={'vivienda': {'fecha': '2026-10-22', 'presentes': pres(raro)}, 'garaje': None})}, [raro]), t72)

    ok(not errs, 'errores de JavaScript: %s' % errs)
    b.close()

shutil.rmtree(SANDBOX, ignore_errors=True)
if fallos:
    print('\n%d fallos' % len(fallos))
    sys.exit(1)
print('OK: todas las comprobaciones')
