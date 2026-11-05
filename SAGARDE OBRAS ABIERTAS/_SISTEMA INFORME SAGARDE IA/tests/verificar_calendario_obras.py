# -*- coding: utf-8 -*-
"""Verificación con Playwright de la pestaña «Calendario» de personal_sagarde.html. Datos INVENTADOS.

Qué comprueba: que cada casilla del mes dice lo mismo que un cálculo INDEPENDIENTE hecho aquí en Python (no el de la página),
que al pinchar un día salen las obras y las personas correctas, el desplegable de obras, los días sin registro y las obras
que faltan, la navegación entre meses, el móvil (sin desplazamiento lateral), que un nombre con etiquetas HTML no se ejecuta,
los avisos (jornadas no válidas, sin jornadas) y que ningún texto lleva palabras de programador.

Uso: python verificar_calendario_obras.py [carpeta con personal_sagarde.html y personal_calculo.js]
Salida 0 = todo bien. La fecha «hoy» de la página se fija al 09/11/2026 (lunes)."""
import datetime
import io
import json
import os
import shutil
import sys
import tempfile
import uuid
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS)

comprobaciones = 0
fallos = []


def comprobar(cond, contexto, detalle=''):
    global comprobaciones
    comprobaciones += 1
    if not cond:
        fallos.append('[%s] %s' % (contexto, detalle))
        print('FALLO: [%s] %s' % (contexto, detalle))
    return cond


def igual(obtenido, esperado, contexto):
    return comprobar(obtenido == esperado, contexto, 'se esperaba %r y salió %r' % (esperado, obtenido))


# ----------------------------------------------------------------------------------------------------------------------
# Datos inventados (los mismos de tests/verificar_personal_calendario.js, más un nombre con etiquetas HTML)
# ----------------------------------------------------------------------------------------------------------------------
HOY = '2026-11-09'
NOMBRES = {'a': '2026 ALFA UNO', 'b': '2026 BETA DOS 32V', 'c': '2025 GAMMA TRES', 'z': '2024 ZETA CERRADA', 'g': '2026 GORLIZ'}
CERRADAS = {'z'}
ABIERTAS = ['a', 'b', 'c', 'g']
XSS = '<img src=x onerror="window.__xss=1">'


def j(obra, fecha, nombre, horas, ambito='vivienda', extra=0, empresa=None):
    d = {'fecha': fecha, 'ambito': ambito, 'nombre': nombre, 'horas': horas, 'extra': extra}
    if empresa:
        d['empresa'] = empresa
    return obra, d


JORNADAS = [
    j('a', '2026-11-02', 'Ana', 7.5, empresa='Sagarde'),
    j('a', '2026-11-02', 'Luis', 8, empresa='Manueles'),
    j('a', '2026-11-02', XSS, 6, empresa='<b>Falsa</b>'),
    j('a', '2026-11-03', 'Ana', 7.5, empresa='Sagarde'),
    j('a', '2026-11-03', 'Beba', None, extra=None),
    j('b', '2026-11-02', 'Pepe', 7.5),
    j('b', '2026-11-02', 'PEPE', 2, ambito='garaje'),
    j('b', '2026-11-04', 'Pepe', 7.5),
    j('c', '2026-11-04', 'Rosa', 8),
    j('z', '2026-11-02', 'Zeta', 8),
    j('a', '2026-11-07', 'Ana', 4, empresa='Sagarde'),
]
MALAS = [  # no cuentan: fecha imposible y sin nombre
    ('a', {'fecha': '2026-13-45', 'ambito': 'vivienda', 'nombre': 'Xx', 'horas': 8, 'extra': 0}),
    ('a', {'fecha': '2026-11-03', 'ambito': 'vivienda', 'nombre': '', 'horas': 8, 'extra': 0}),
]


def estado_js(jornadas):
    obras = {}
    for id_, nombre in NOMBRES.items():
        obras[id_] = {'nombre': nombre, 'cerrada': id_ in CERRADAS, 'horario_semanal': {}, 'excepciones_horario': {},
                      'ultima': None, 'jornadas': [d for o, d in jornadas if o == id_]}
    est = {'version': 1, 'generado': '2026-11-09T08:00:00+01:00', 'jornada_base_h': 7.5, 'catalogo': [], 'obras': obras}
    return 'window.SAGARDE_PERSONAL = ' + json.dumps(est, ensure_ascii=False) + ';\n'


# ----------------------------------------------------------------------------------------------------------------------
# El cálculo esperado, hecho aparte (otra implementación, a propósito)
# ----------------------------------------------------------------------------------------------------------------------
def esperado_mes(jornadas, anio, mes):
    validas = [(o, d) for o, d in jornadas if d['fecha'][5:7] != '13' and d['nombre'].strip()]
    primera = {}
    por = {}
    for o, d in validas:
        primera[o] = min(primera.get(o, '9999'), d['fecha'])
        por.setdefault((d['fecha'], o), []).append(d)
    p = datetime.date(anio, mes, 1)
    u = (datetime.date(anio + (mes == 12), mes % 12 + 1, 1) - datetime.timedelta(days=1))
    ini = p - datetime.timedelta(days=p.weekday())
    fin = u + datetime.timedelta(days=6 - u.weekday())
    res = {}
    dia = ini
    while dia <= fin:
        f = dia.isoformat()
        con = [o for o in ABIERTAS if (f, o) in por] + sorted(o for (ff, o) in por if ff == f and o not in ABIERTAS)
        exigible = dia.weekday() < 5 and f < HOY
        esp = [o for o in ABIERTAS if exigible and o in primera and primera[o] <= f]
        falt = [o for o in esp if o not in con]
        est = ('parcial' if falt else 'completo') if con else ('ninguno' if esp else 'vacio')
        res[f] = {'estado': est, 'con': con, 'faltan': falt, 'total': len(con) + len(falt)}
        dia += datetime.timedelta(days=1)
    return res


def corto(id_):
    return NOMBRES[id_].split(' ', 1)[1].split(' ')[0]


# ----------------------------------------------------------------------------------------------------------------------
# Navegador
# ----------------------------------------------------------------------------------------------------------------------
FIJA = """(() => { const R = Date; const F = new R('%sT12:00:00').getTime();
 class D extends R { constructor(...a){ if(a.length===0) super(F); else super(...a);} static now(){return F;} }
 window.Date = D; })();""" % HOY


def carpeta_motor():
    if len(sys.argv) > 1:
        return os.path.abspath(sys.argv[1])
    return os.path.dirname(TESTS)


def montar(motor, jornadas, temporales):
    base = os.environ.get('P3_TMP') or tempfile.gettempdir()
    d = os.path.join(base, 'cal_obras_' + uuid.uuid4().hex[:8])
    os.makedirs(d)
    temporales.append(d)
    for f in ('personal_sagarde.html', 'personal_calculo.js'):
        shutil.copy(os.path.join(motor, f), os.path.join(d, f))
    with open(os.path.join(d, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
        fh.write(estado_js(jornadas))
    return d


def url(d, hash_=''):
    return 'file:///' + os.path.join(d, 'personal_sagarde.html').replace(os.sep, '/').replace(' ', '%20') + hash_


def abrir(browser, d, hash_='#calendario', ancho=1100, errores=None):
    pg = browser.new_page(viewport={'width': ancho, 'height': 900})
    pg.add_init_script(FIJA)
    if errores is not None:
        pg.on('pageerror', lambda e: errores.append('pageerror: ' + str(e)))
        pg.on('console', lambda m: errores.append('console: ' + m.text) if m.type == 'error' else None)
    pg.goto(url(d, hash_))
    pg.wait_for_selector('#contenido-calendario .cal-dia, #contenido-calendario .aviso')
    return pg


def casillas(pg):
    return pg.eval_on_selector_all('.cal-dia', """els => els.map(e => ({f: e.dataset.f, cls: e.className,
      cnt: (e.querySelector('.cal-cnt') || {}).textContent || '',
      chips: Array.from(e.querySelectorAll('.cal-chip')).map(c => c.textContent), aria: e.getAttribute('aria-label')}))""")


def texto_calendario(pg):
    return pg.inner_text('#contenido-calendario')


TEXTOS = []  # todo lo que lee Bixente en la pestaña, para pasarle la guarda de lenguaje


def anotar(pg):
    TEXTOS.append(texto_calendario(pg))


def tabla(pg):
    return pg.eval_on_selector_all('#cal-detalle tbody tr', 'trs => trs.map(t => Array.from(t.querySelectorAll("td")).map(c => c.innerText.replace(/\\s+/g, " ").trim()))')


def verificar_mes(pg, jornadas, anio, mes, contexto):
    esp = esperado_mes(jornadas, anio, mes)
    cas = casillas(pg)
    igual(len(cas), len(esp), contexto + ': número de casillas')
    for c in cas:
        e = esp.get(c['f'])
        if e is None:
            comprobar(False, contexto, 'casilla %s que no debería existir' % c['f'])
            continue
        clases = c['cls'].split()
        comprobar(e['estado'] in clases, '%s %s' % (contexto, c['f']), 'estado %s y clases %s' % (e['estado'], clases))
        cnt = ('%d/%d' % (len(e['con']), e['total'])) if e['total'] else ''
        igual(c['cnt'], cnt, '%s %s: recuento' % (contexto, c['f']))
        igual(c['chips'], [corto(o) for o in e['con']], '%s %s: obras en la casilla' % (contexto, c['f']))
        comprobar(('finde' in clases) == (datetime.date.fromisoformat(c['f']).weekday() >= 5), '%s %s' % (contexto, c['f']), 'marca de fin de semana')
        comprobar(('hoy' in clases) == (c['f'] == HOY), '%s %s' % (contexto, c['f']), 'marca de hoy')


def main():
    motor = carpeta_motor()
    temporales = []
    errores = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            todas = JORNADAS + MALAS
            d = montar(motor, todas, temporales)

            # --- 1. Abre en el Ranking; el calendario se abre con su pestaña y con #calendario ---
            pg = browser.new_page(viewport={'width': 1100, 'height': 900})
            pg.add_init_script(FIJA)
            pg.on('pageerror', lambda e: errores.append('pageerror: ' + str(e)))
            pg.goto(url(d, ''))
            pg.wait_for_function('!document.getElementById("contenido").innerText.includes("Cargando personal")')
            comprobar(pg.is_visible('#vista-ranking') and not pg.is_visible('#vista-calendario'), 'arranque', 'sin # debe verse el ranking y no el calendario')
            comprobar(pg.locator('#pestanas [data-v="calendario"]').count() == 1, 'pestañas', 'falta la pestaña Calendario')
            pg.click('#pestanas [data-v="calendario"]')
            comprobar(pg.is_visible('#vista-calendario') and not pg.is_visible('#vista-ranking'), 'pestaña', 'al pulsar Calendario debe verse solo el calendario')
            pg.click('#pestanas [data-v="base"]')
            comprobar(pg.is_visible('#vista-base') and not pg.is_visible('#vista-calendario'), 'pestaña', 'otra pestaña oculta el calendario')
            pg.close()

            pg = abrir(browser, d, errores=errores)
            comprobar(pg.is_visible('#vista-calendario') and not pg.is_visible('#vista-ranking'), 'enlace #calendario', 'debe abrirse en el calendario')
            igual(pg.inner_text('#contenido-calendario .etq'), 'noviembre 2026', 'mes de arranque (el de «hoy»)')

            # --- 2. Cada casilla de noviembre dice lo que dice el cálculo independiente ---
            verificar_mes(pg, todas, 2026, 11, 'nov 2026')
            igual(pg.inner_text('.cal-dia[data-f="2026-11-02"] .cal-cnt'), '3/3', '02/11 recuento')
            igual(pg.get_attribute('.cal-dia[data-f="2026-11-02"]', 'aria-label'), 'lunes 2 de noviembre: 3 de 3 obras con registro', '02/11 texto para lectores de pantalla')
            igual(pg.get_attribute('.cal-dia[data-f="2026-11-03"]', 'aria-label'), 'martes 3 de noviembre: 1 de 2 obras con registro', '03/11 (falta una) texto para lectores de pantalla')
            igual(pg.get_attribute('.cal-dia[data-f="2026-11-04"]', 'aria-label'), 'miércoles 4 de noviembre: 2 de 3 obras con registro', '04/11 (falta una) texto para lectores de pantalla')
            igual(pg.get_attribute('.cal-dia[data-f="2026-11-05"]', 'aria-label'), 'jueves 5 de noviembre: sin registro de ninguna de las 3 obras', '05/11 texto para lectores de pantalla')
            igual(pg.get_attribute('.cal-dia[data-f="2026-11-08"]', 'aria-label'), 'domingo 8 de noviembre: sin registro', '08/11 texto para lectores de pantalla')
            igual(pg.get_attribute('.cal-dia[data-f="2026-11-09"]', 'aria-current'), 'date', 'hoy lleva aria-current')
            comprobar(pg.locator('.cal-dia[aria-pressed="true"]').count() == 0, 'sin día elegido', 'al abrir no debe haber ninguno elegido')
            comprobar('Pincha un día' in pg.inner_text('#cal-detalle'), 'sin día elegido', 'debe invitar a pinchar un día')
            # El aviso de jornadas no válidas se ve y dice cuántas
            comprobar('2 jornadas no tienen obra, nombre o fecha válidos' in texto_calendario(pg), 'aviso de jornadas no válidas', texto_calendario(pg)[:200])
            anotar(pg)

            # --- 3. Día con varias obras: desplegable, y cada obra enseña a su gente ---
            pg.click('.cal-dia[data-f="2026-11-02"]')
            comprobar(pg.get_attribute('.cal-dia[data-f="2026-11-02"]', 'aria-pressed') == 'true', 'día elegido', 'el día pinchado queda marcado')
            igual(pg.inner_text('#cal-detalle h3'), 'lunes 2 de noviembre de 2026', '02/11 título del día')
            igual(pg.eval_on_selector_all('#cal-obra option', 'o => o.map(x => x.value)'), ['a', 'b', 'z'], '02/11 obras del desplegable (abiertas primero)')
            comprobar('3 obras con registro' in pg.inner_text('#cal-detalle'), '02/11 resumen', pg.inner_text('#cal-detalle')[:160])
            igual(pg.input_value('#cal-obra'), 'a', '02/11 obra elegida por defecto')
            filas = tabla(pg)
            # Orden por nombre: los símbolos («<») van antes que las letras
            igual([f[0].split(' ')[0] for f in filas], ['<img', 'Ana', 'Luis'], '02/11 obra a: personas por orden alfabético')
            igual(filas[1], ['Ana Sagarde', 'Viviendas', '7,5'], '02/11 obra a: nombre, empresa debajo, zona y horas')
            igual(filas[2], ['Luis Manueles', 'Viviendas', '8'], '02/11 obra a: segunda persona')
            igual(pg.locator('#cal-detalle .cuenta').nth(1).inner_text(), '3 personas · 21,5 h', '02/11 obra a: personas y horas')
            # Un nombre con etiquetas HTML se ve como texto y no se ejecuta
            comprobar(pg.evaluate('window.__xss') is None, 'inyección', 'el nombre con etiquetas HTML se ejecutó')
            comprobar(pg.locator('#cal-detalle img').count() == 0, 'inyección', 'el nombre con etiquetas HTML creó una imagen')
            comprobar(XSS in pg.inner_text('#cal-detalle'), 'inyección', 'el nombre con etiquetas debe verse tal cual, como texto')
            comprobar('<b>Falsa</b>' in pg.inner_text('#cal-detalle'), 'inyección', 'la empresa con etiquetas debe verse como texto')
            anotar(pg)
            pg.select_option('#cal-obra', 'b')
            igual(pg.input_value('#cal-obra'), 'b', '02/11 al cambiar de obra se queda en ella')
            filas = tabla(pg)
            igual([[c for c in f] for f in filas], [['Pepe', 'Viviendas', '7,5'], ['PEPE', 'Garajes', '2']], '02/11 obra b: una persona, dos zonas, viviendas antes que garajes')
            igual(pg.locator('#cal-detalle .cuenta').nth(1).inner_text(), '1 persona · 9,5 h', '02/11 obra b: personas distintas y horas')
            anotar(pg)
            pg.select_option('#cal-obra', 'z')
            igual(tabla(pg), [['Zeta', 'Viviendas', '8']], '02/11 obra cerrada: sale con su gente')
            comprobar('Sin registro este día' not in pg.inner_text('#cal-detalle'), '02/11 sin faltas', 'no debe avisar de obras que faltan')

            # --- 4. Día con una sola obra (sin desplegable), con horas sin dato y con una obra que falta ---
            pg.click('.cal-dia[data-f="2026-11-03"]')
            igual(pg.locator('#cal-obra').count(), 0, '03/11 con una sola obra no hay desplegable')
            igual(pg.inner_text('#cal-detalle h4'), '2026 ALFA UNO', '03/11 nombre de la obra')
            igual(pg.locator('#cal-detalle .cuenta').nth(0).inner_text(), '1 de 2 obras con registro', '03/11 resumen')
            igual(tabla(pg), [['Ana Sagarde', 'Viviendas', '7,5'], ['Beba', 'Viviendas', '–']], '03/11 personas; horas sin dato como «–», nunca 0')
            igual(pg.locator('#cal-detalle .cuenta').nth(1).inner_text(), '2 personas · hay jornadas sin horas', '03/11 el total no se inventa')
            igual(pg.inner_text('#cal-detalle .aviso'), 'Sin registro este día: 2026 BETA DOS 32V.', '03/11 obra que falta')
            anotar(pg)

            # --- 5. Día laborable pasado sin nada: dice qué obras debían tener registro ---
            pg.click('.cal-dia[data-f="2026-11-05"]')
            igual(pg.inner_text('#cal-detalle .empty'), 'Ninguna obra tiene registro este día.', '05/11 sin registro')
            igual(pg.inner_text('#cal-detalle .aviso'), 'Sin registro este día: 2026 ALFA UNO, 2026 BETA DOS 32V, 2025 GAMMA TRES.', '05/11 las tres obras que faltan (Gorliz nunca tuvo jornadas: no se exige)')
            anotar(pg)
            # Fin de semana sin registro: no se acusa a nadie
            pg.click('.cal-dia[data-f="2026-11-08"]')
            igual(pg.inner_text('#cal-detalle .empty'), 'Ninguna obra tiene registro este día.', '08/11 sin registro')
            igual(pg.locator('#cal-detalle .aviso').count(), 0, '08/11 domingo: no se exige nada')
            # Sábado con registro: cuenta
            pg.click('.cal-dia[data-f="2026-11-07"]')
            igual(tabla(pg), [['Ana Sagarde', 'Viviendas', '4']], '07/11 sábado con registro')

            # --- 6. Meses: anterior, siguiente, cambio de año y «Hoy» ---
            # El 30/11 es un día de relleno que sale en la rejilla de noviembre Y en la de diciembre: al cambiar de mes la
            # elección se quita aunque ese día siga a la vista
            pg.click('.cal-dia[data-f="2026-11-30"]')
            pg.click('[data-cm="1"]')
            igual(pg.inner_text('#contenido-calendario .etq'), 'diciembre 2026', 'mes siguiente')
            igual(pg.locator('.cal-dia[data-f="2026-11-30"]').count(), 1, 'el 30/11 también sale en la rejilla de diciembre')
            igual(pg.locator('.cal-dia[aria-pressed="true"]').count(), 0, 'al cambiar de mes se quita el día elegido, aunque también salga en el mes nuevo')
            comprobar('Pincha un día' in pg.inner_text('#cal-detalle'), 'al cambiar de mes el detalle vuelve a invitar a pinchar un día', pg.inner_text('#cal-detalle')[:120])
            pg.click('[data-cm="-1"]')
            igual(pg.inner_text('#contenido-calendario .etq'), 'noviembre 2026', 'vuelta a noviembre')
            pg.click('[data-cm="-1"]')
            igual(pg.inner_text('#contenido-calendario .etq'), 'octubre 2026', 'mes anterior')
            igual(pg.locator('.cal-dia[aria-pressed="true"]').count(), 0, 'al cambiar de mes se quita el día elegido')
            verificar_mes(pg, todas, 2026, 10, 'oct 2026')
            igual(pg.locator('.cal-dia').count(), 35, 'octubre 2026: 5 semanas')
            pg.click('[data-cm="1"]')
            pg.click('[data-cm="1"]')
            igual(pg.inner_text('#contenido-calendario .etq'), 'diciembre 2026', 'dos meses adelante')
            verificar_mes(pg, todas, 2026, 12, 'dic 2026')
            pg.click('[data-cm="1"]')
            igual(pg.inner_text('#contenido-calendario .etq'), 'enero 2027', 'cambio de año hacia delante')
            for _ in range(13):
                pg.click('[data-cm="-1"]')
            igual(pg.inner_text('#contenido-calendario .etq'), 'diciembre 2025', 'cambio de año hacia atrás')
            comprobar(all('vacio' in c['cls'].split() for c in casillas(pg)), 'diciembre 2025', 'sin jornadas todas deben salir vacías')
            pg.click('[data-cm="hoy"]')
            igual(pg.inner_text('#contenido-calendario .etq'), 'noviembre 2026', '«Hoy» vuelve al mes de hoy')
            igual(pg.get_attribute('.cal-dia[data-f="2026-11-09"]', 'aria-pressed'), 'true', '«Hoy» elige el día de hoy')
            igual(pg.inner_text('#cal-detalle h3'), 'lunes 9 de noviembre de 2026', '«Hoy» enseña el día de hoy')
            anotar(pg)
            # El teclado: las casillas son botones y el foco se queda donde estaba
            pg.focus('.cal-dia[data-f="2026-11-03"]')
            pg.keyboard.press('Enter')
            igual(pg.evaluate('document.activeElement && document.activeElement.dataset.f'), '2026-11-03', 'con el teclado el foco se queda en la casilla')
            igual(pg.inner_text('#cal-detalle h3'), 'martes 3 de noviembre de 2026', 'con el teclado se elige el día')
            pg.close()

            # --- 7. Móvil: sin desplazamiento lateral, sin nombres de obra dentro de la casilla, detalle en tarjetas ---
            pg = abrir(browser, d, ancho=390, errores=errores)
            pg.click('.cal-dia[data-f="2026-11-02"]')
            ancho_doc = pg.evaluate('document.documentElement.scrollWidth')
            comprobar(ancho_doc <= 391, 'móvil', 'hay desplazamiento lateral: el documento mide %s px en una pantalla de 390' % ancho_doc)
            comprobar(pg.evaluate('getComputedStyle(document.querySelector(".cal-chip")).display') == 'none', 'móvil', 'los nombres de obra no deben verse dentro de la casilla')
            comprobar(pg.evaluate('document.querySelector(".cal-dia").getBoundingClientRect().height') >= 44, 'móvil', 'la casilla es más baja que un dedo (44 px)')
            comprobar(pg.is_visible('#cal-obra'), 'móvil', 'el desplegable debe verse')
            igual(pg.eval_on_selector_all('#cal-detalle tbody td[data-etq]', 'tds => tds.slice(0, 3).map(t => t.dataset.etq)'), ['Nombre', 'Zona', 'Horas'], 'móvil: cada dato lleva su etiqueta')
            anotar(pg)
            pg.close()

            # --- 8. Sin ninguna jornada: lo dice y no inventa nada ---
            d2 = montar(motor, [], temporales)
            pg = abrir(browser, d2, errores=errores)
            comprobar('Todavía no hay jornadas guardadas' in texto_calendario(pg), 'sin jornadas', texto_calendario(pg)[:160])
            comprobar(all(c['cls'].split()[1] == 'vacio' and c['cnt'] == '' for c in casillas(pg)), 'sin jornadas', 'todas las casillas deben salir vacías y sin recuento')
            anotar(pg)
            pg.close()

            # --- 9. Una sola jornada no válida: el aviso va en singular ---
            d3 = montar(motor, JORNADAS + MALAS[:1], temporales)
            pg = abrir(browser, d3, errores=errores)
            comprobar('Una jornada no tiene obra, nombre o fecha válidos: no sale en el calendario' in texto_calendario(pg), 'aviso en singular', texto_calendario(pg)[:200])
            pg.close()

            # --- 10. Estado roto: la página lo dice, no se queda en blanco ---
            d4 = montar(motor, JORNADAS, temporales)
            with open(os.path.join(d4, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
                fh.write('window.SAGARDE_PERSONAL = {"version": 1, "obras": 5};\n')
            pg = browser.new_page()
            pg.add_init_script(FIJA)
            pg.goto(url(d4, '#calendario'))
            pg.wait_for_selector('#contenido-calendario .aviso')
            comprobar('personal_estado.js' in texto_calendario(pg), 'datos rotos', 'debe avisar con la causa; salió: ' + texto_calendario(pg)[:200])
            pg.close()
            browser.close()
    finally:
        for t in temporales:
            shutil.rmtree(t, ignore_errors=True)

    comprobar(not errores, 'errores de la página', '; '.join(errores)[:300])

    # --- Ningún texto que lea Bixente lleva palabras de programador ---
    try:
        from test_lenguaje_electricista import palabras_prohibidas
        for t in TEXTOS:
            malas = palabras_prohibidas(t)
            comprobar(not malas, 'lenguaje', 'palabras de programador %s en «%s»' % (malas, ' '.join(t.split())[:120]))
        comprobar(len(TEXTOS) >= 7, 'lenguaje', 'se han revisado pocos textos (%d)' % len(TEXTOS))
    except ImportError as e:
        comprobar(False, 'lenguaje', 'no se pudo cargar la guarda de lenguaje: %s' % e)

    print('%d comprobaciones, %d fallos' % (comprobaciones, len(fallos)))
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
