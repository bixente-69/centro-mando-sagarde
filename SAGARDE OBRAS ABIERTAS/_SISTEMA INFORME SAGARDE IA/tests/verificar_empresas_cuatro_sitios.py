# -*- coding: utf-8 -*-
"""Paso 08c2b: el MISMO desglose por empresa en los cuatro sitios (pestaña Personal, Informe de obra, ranking de Sagarde e
Informe de la tablet), comparado con un cálculo INDEPENDIENTE en Python (sin personal_calculo.js). Navegador (Playwright).

Uso:  py -3.11 tests/verificar_empresas_cuatro_sitios.py [carpeta del motor]     (por defecto, el de este repositorio)
Lo lanza tests/test_empresas_suma_08c2b.py (se salta sin navegador). Datos INVENTADOS. Exit 0 = los cuatro sitios dicen lo mismo
que el cálculo a mano, en tres zonas horarias. Cada fallo sale como una línea «FALLO:»."""
import io
import json
import os
import shutil
import sys
import tempfile
import unicodedata
import uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

MOTOR = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(os.environ.get('P3_TMP') or tempfile.gettempdir(), 'cuatro_' + uuid.uuid4().hex[:6])
os.makedirs(TMP)
sys.path.insert(0, MOTOR)
import panel_personal  # noqa: E402

fallos = []


def ok(cond, msg):
    if not cond:
        fallos.append(msg)
        print('FALLO:', msg)


# ---------------------------------------------------------------- datos inventados (dos obras, una persona en las dos)
def f(obra, fecha, ambito, nombre, horas, empresa=None):
    fila = {'fecha': fecha, 'ambito': ambito, 'nombre': nombre, 'horas': horas, 'extra': 0}
    if empresa:
        fila['empresa'] = empresa
    return fila


OBRAS = {
    'alfa': ('2026 ALFA', [
        f('alfa', '2026-10-19', 'vivienda', 'Ana', 7.5, 'Manueles'), f('alfa', '2026-10-20', 'vivienda', 'Ana', 7.5, 'Manueles'),
        f('alfa', '2026-10-19', 'vivienda', 'Beto', 7.5, 'Manueles'),
        f('alfa', '2026-10-19', 'vivienda', 'Carla', 8, 'CATERSYSTEM'), f('alfa', '2026-10-20', 'garaje', 'Carla', 8, 'CATERSYSTEM'),
        f('alfa', '2026-10-19', 'vivienda', 'Dani', 6, 'Dani @AUT'),
        f('alfa', '2026-10-20', 'vivienda', 'Eli', 4, 'Eli@aut'),
        f('alfa', '2026-10-19', 'vivienda', 'Fran', 7.5),
        f('alfa', '2026-09-30', 'vivienda', 'Ana', 7.5, 'Manueles'),          # septiembre: solo cuenta en «Obra» y en «Año»
    ]),
    'beta': ('2026 BETA', [
        f('beta', '2026-10-19', 'garaje', 'Fran', 2),                       # Fran, el mismo día en la otra obra: un día de persona
        f('beta', '2026-10-21', 'vivienda', 'Dani', 5, 'Dani @AUT'),
        f('beta', '2026-10-21', 'vivienda', 'Gus', 7.5, '<b>Raro</b> & Co'),
        f('beta', '2026-09-15', 'vivienda', 'Hugo', 7.5, 'Zeta'),
    ]),
}


def esperado(filas):
    """Cálculo independiente: por empresa (sin tildes ni mayúsculas), personas, días de persona, horas, %."""
    def clave(e):
        t = ''.join(c for c in unicodedata.normalize('NFD', ' '.join((e or '').split())) if not unicodedata.combining(c)).lower()
        return '' if t in ('', 'sin empresa') else t
    grupos = {}
    for r in filas:
        k = clave(r.get('empresa'))
        g = grupos.setdefault(k, {'nombre': ' '.join((r.get('empresa') or '').split()) if k else 'Sin empresa', 'p': set(), 'd': set(), 'h': 0.0})
        g['p'].add(r['nombre'])
        g['d'].add((r['nombre'], r['fecha']))
        g['h'] += r['horas']
    total_h = sum(g['h'] for g in grupos.values())
    todas = {r['nombre'] for r in filas}
    dias = {(r['nombre'], r['fecha']) for r in filas}
    lineas = sorted(grupos.items(), key=lambda kv: (kv[0] == '', -kv[1]['h'], kv[1]['nombre'].lower()))

    def num(x):
        s = str(round(x + 1e-9, 1))
        return (s[:-2] if s.endswith('.0') else s).replace('.', ',')
    out = [[g['nombre'], str(len(g['p'])), str(len(g['d'])), num(g['h']), num(100 * g['h'] / total_h) + ' %'] for _, g in lineas]
    out.append(['Total', str(len(todas)), str(len(dias)), num(total_h), '100 %'])
    aut = [g for k, g in lineas if k and g['nombre'].lower().replace(' ', '').endswith('@aut')]
    if aut:
        pa = set().union(*[g['p'] for g in aut])
        da = set().union(*[g['d'] for g in aut])
        ha = sum(g['h'] for g in aut)
        out.append(['Total autónomos (@AUT)', str(len(pa)), str(len(da)), num(ha), num(100 * ha / total_h) + ' %'])
    return out


JS_CELDAS = "f=>f.map(r=>[...r.children].map(c=>c.textContent.trim()))"


def tabla_de(pg, selector):
    return pg.eval_on_selector_all(selector + ' [data-por-empresa] tr', JS_CELDAS)


def octubre(filas):
    return [r for r in filas if r['fecha'].startswith('2026-10')]


def scroll_x(pg, raiz):
    return pg.evaluate("s=>{const d=document.querySelector(s+' [data-por-empresa] > div');return d?getComputedStyle(d).overflowX:null}", raiz)


# Una palabra sola (CATERSYSTEM) no puede partirse en dos líneas: era el fallo de «CATERSYS / TEM» a 390 px.
JS_PARTIDAS = r"""s=>[...document.querySelectorAll(s)].filter(e=>e.textContent.trim()&&!/\s/.test(e.textContent.trim())).filter(e=>{
  const r=document.createRange();r.selectNodeContents(e);return r.getClientRects().length>1}).map(e=>e.textContent.trim())"""


def sin_cabecera(t):
    return t[1:] if t and t[0][0] == 'Empresa' else t


def montar_pagina(cuerpo):
    ruta = os.path.join(TMP, 'pagina_' + uuid.uuid4().hex[:6] + '.html')
    with open(ruta, 'w', encoding='utf-8') as fh:
        fh.write('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                 '<style>body{font-family:sans-serif;margin:12px}</style></head><body>' + cuerpo + '</body></html>')
    return 'file:///' + ruta.replace(os.sep, '/').replace(' ', '%20')


def main():
    rankings, tablets = [], []
    todas = [dict(r, obra=o) for o, (_, filas) in OBRAS.items() for r in filas]
    with sync_playwright() as p:
        b = p.chromium.launch()
        for tz in ('Europe/Madrid', 'Pacific/Auckland', 'America/Los_Angeles'):
            ctx = b.new_context(viewport={'width': 820, 'height': 1000}, timezone_id=tz, locale='es-ES')
            errs = []

            # 1) PESTAÑA y 2) INFORME de la obra alfa (octubre, todas las jornadas de esa obra)
            for nombre, fn, raiz in (('pestaña', panel_personal.vista_personal, '#pers-raiz'), ('informe', panel_personal.informe_personal, '#pinf-raiz')):
                filas = OBRAS['alfa'][1]
                pg = ctx.new_page()
                pg.on('pageerror', lambda e: errs.append(str(e)))
                pg.goto(montar_pagina(fn('alfa', filas)))
                pre = 'p' if nombre == 'pestaña' else 'pinf'
                clave_js = 'pers' if nombre == 'pestaña' else 'pinf'
                ok(sin_cabecera(tabla_de(pg, raiz)) == esperado(octubre(filas)),
                   '[%s] %s (mes de octubre): %s' % (tz, nombre, tabla_de(pg, raiz)))
                pg.click('%s [data-%s-p="obra"]' % (raiz, clave_js))
                ok(sin_cabecera(tabla_de(pg, raiz)) == esperado(filas), '[%s] %s: tabla por empresa distinta del cálculo a mano: %s' % (tz, nombre, tabla_de(pg, raiz)))
                # la empresa junto al nombre, en la tabla de personas
                quien = pg.evaluate("""s=>[...document.querySelectorAll(s+' table')].filter(t=>!t.closest('[data-por-empresa]'))
                    .flatMap(t=>[...t.querySelectorAll('tbody tr')]).map(r=>[r.children[0].querySelector('b').textContent.trim(),
                    (r.querySelector('[class$="-emp"]')||{}).textContent||null])""", raiz)
                dicc = dict((k, v) for k, v in quien)
                ok(dicc.get('Ana') == 'Manueles' and dicc.get('Carla') == 'CATERSYSTEM' and dicc.get('Fran') is None and dicc.get('Dani') == 'Dani @AUT',
                   '[%s] %s: empresa junto al nombre: %s' % (tz, nombre, dicc))
                # cambiar de ámbito recalcula el bloque con el mismo cálculo
                pg.click('%s [data-%s-a="garaje"]' % (raiz, 'pers' if nombre == 'pestaña' else 'pinf'))
                solo_garaje = [r for r in filas if r['ambito'] == 'garaje']
                ok(sin_cabecera(tabla_de(pg, raiz)) == esperado(solo_garaje), '[%s] %s (solo garajes): %s' % (tz, nombre, tabla_de(pg, raiz)))
                ok(scroll_x(pg, raiz) in ('auto', 'scroll'), '[%s] %s: la tabla por empresa no tiene scroll horizontal (%r)' % (tz, nombre, scroll_x(pg, raiz)))
                pg.close()

            # 3) RANKING de Sagarde: suma de TODAS las obras (copia de la página + estado inventado)
            d = os.path.join(TMP, 'ranking_' + uuid.uuid4().hex[:6])
            os.makedirs(d)
            rankings.append(d)
            for nom in ('personal_sagarde.html', 'personal_calculo.js'):
                shutil.copy(os.path.join(MOTOR, nom), os.path.join(d, nom))
            estado = {'version': 1, 'generado': '2026-10-23T08:00:00+02:00', 'jornada_base_h': 7.5, 'catalogo': [],
                      'obras': {o: {'nombre': n, 'cerrada': False, 'horario_semanal': {}, 'excepciones_horario': {}, 'ultima': {},
                                    'jornadas': [{k: v for k, v in r.items() if k != 'obra'} for r in filas]} for o, (n, filas) in OBRAS.items()}}
            with open(os.path.join(d, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
                fh.write('window.SAGARDE_PERSONAL = ' + json.dumps(estado, ensure_ascii=False) + ';\n')
            pg = ctx.new_page()
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.goto('file:///' + os.path.join(d, 'personal_sagarde.html').replace(os.sep, '/').replace(' ', '%20'))
            pg.wait_for_selector('#contenido [data-por-empresa]')
            ok(sin_cabecera(tabla_de(pg, '#contenido')) == esperado(octubre(todas)),
               '[%s] ranking (mes de octubre, todas las obras): %s' % (tz, tabla_de(pg, '#contenido')))
            pg.click('#controles [data-p="obra"]')
            ok(sin_cabecera(tabla_de(pg, '#contenido')) == esperado(todas), '[%s] ranking: suma de todas las obras: %s' % (tz, tabla_de(pg, '#contenido')))
            ok(scroll_x(pg, '#contenido') in ('auto', 'scroll'), '[%s] ranking: la tabla por empresa no tiene scroll horizontal (%r)' % (tz, scroll_x(pg, '#contenido')))
            cab = pg.eval_on_selector('#contenido [data-por-empresa] thead', "h=>h.textContent")
            ok('% de Sagarde' in cab, '[%s] ranking: la columna del %% se llama «%% de Sagarde»: %r' % (tz, cab))
            ok(pg.evaluate("document.querySelectorAll('#contenido .nom-emp').length") >= 4, '[%s] ranking: la empresa va junto al nombre' % tz)
            pg.close()
            # 4) INFORME DE LA TABLET (obra alfa): el catálogo trae la empresa de cada persona
            d = os.path.join(TMP, 'tablet_' + uuid.uuid4().hex[:6])
            os.makedirs(d)
            tablets.append(d)
            for nom in ('generador_personal.html', 'personal_calculo.js'):
                shutil.copy(os.path.join(MOTOR, nom), os.path.join(d, nom))
            filas_alfa = OBRAS['alfa'][1]
            personas = []
            for r in filas_alfa:
                if r['nombre'] not in [x['nombre'] for x in personas]:
                    personas.append({'id': 'T%04d' % (len(personas) + 1), 'nombre': r['nombre'], 'categoria': '', 'empresa': r.get('empresa', ''), 'activo': True})
            horario = {'lun': 7.5, 'mar': 7.5, 'mie': 7.5, 'jue': 7.5, 'vie': 7.5, 'sab': 0, 'dom': 0}
            estado_t = {'version': 1, 'generado': '2026-10-23T08:00:00+02:00', 'jornada_base_h': 7.5, 'catalogo': personas,
                        'obras': {'alfa': {'nombre': '2026 ALFA', 'cerrada': False, 'horario_semanal': horario, 'excepciones_horario': {},
                                           'ultima': {'vivienda': None, 'garaje': None},
                                           'jornadas': [{k: v for k, v in r.items() if k != 'empresa'} for r in filas_alfa]}}}
            with open(os.path.join(d, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
                fh.write('window.SAGARDE_PERSONAL = ' + json.dumps(estado_t, ensure_ascii=False) + ';' + chr(10))
            pg = ctx.new_page()
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.goto('file:///' + os.path.join(d, 'generador_personal.html').replace(os.sep, '/').replace(' ', '%20'))
            pg.wait_for_selector('#obra')
            pg.click('button[data-v="informe"]')
            pg.click('#v-informe button[data-p="mes"]')
            ok(sin_cabecera(tabla_de(pg, '#v-informe')) == esperado(octubre(filas_alfa)),
               '[%s] tablet (mes de octubre): %s' % (tz, tabla_de(pg, '#v-informe')))
            pg.click('#v-informe button[data-p="obra"]')
            ok(sin_cabecera(tabla_de(pg, '#v-informe')) == esperado(filas_alfa), '[%s] tablet: tabla por empresa distinta del cálculo a mano: %s' % (tz, tabla_de(pg, '#v-informe')))
            pg.close()
            ok(not errs, '[%s] errores de JavaScript: %s' % (tz, errs))
            ctx.close()
        # 320 y 390 px: las palabras sueltas de empresa (CATERSYSTEM, Manueles) no se parten por la mitad en ningún sitio
        for ancho in (390, 320):
            ctx = b.new_context(viewport={'width': ancho, 'height': 900}, timezone_id='Europe/Madrid', locale='es-ES')
            for nombre, fn, raiz, sel in (('pestaña', panel_personal.vista_personal, '#pers-raiz', '#pers-raiz .pers-emp, #pers-raiz [data-por-empresa] td:first-child'),
                                          ('informe', panel_personal.informe_personal, '#pinf-raiz', '#pinf-raiz .pinf-emp, #pinf-raiz [data-por-empresa] td:first-child')):
                pg = ctx.new_page()
                pg.goto(montar_pagina(fn('alfa', OBRAS['alfa'][1])))
                pg.click('%s [data-%s-p="obra"]' % (raiz, 'pers' if nombre == 'pestaña' else 'pinf'))
                partidas = pg.evaluate(JS_PARTIDAS, sel)
                ok(not partidas, '[%d px] ' % ancho + '%s: palabras de empresa partidas por la mitad: %s' % (nombre, partidas))
                pg.close()
            pg = ctx.new_page()
            pg.goto('file:///' + os.path.join(rankings[0], 'personal_sagarde.html').replace(os.sep, '/').replace(' ', '%20'))
            pg.wait_for_selector('#contenido [data-por-empresa]')
            pg.click('#controles [data-p="obra"]')
            partidas = pg.evaluate(JS_PARTIDAS, '#contenido .nom-emp, #contenido [data-por-empresa] td:first-child')
            ok(not partidas, '[%d px] ' % ancho + 'ranking: palabras de empresa partidas por la mitad: %s' % partidas)
            pg.close()
            pg = ctx.new_page()
            pg.goto('file:///' + os.path.join(tablets[0], 'generador_personal.html').replace(os.sep, '/').replace(' ', '%20'))
            pg.wait_for_selector('#obra')
            pg.click('button[data-v="informe"]')
            pg.click('#v-informe button[data-p="obra"]')
            partidas = pg.evaluate(JS_PARTIDAS, '#v-informe .nom-emp, #v-informe [data-por-empresa] td:first-child')
            ok(not partidas, '[%d px] ' % ancho + 'tablet: palabras de empresa partidas por la mitad: %s' % partidas)
            pg.close()
            ctx.close()
        b.close()
    shutil.rmtree(TMP, ignore_errors=True)
    print('%d fallos' % len(fallos) if fallos else 'OK: pestaña, informe, ranking y tablet dicen lo mismo que el cálculo a mano (3 zonas horarias)')
    sys.exit(1 if fallos else 0)


main()
