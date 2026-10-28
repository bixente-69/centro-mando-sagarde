# -*- coding: utf-8 -*-
"""Verificación mediante Playwright de la pestaña «Base de trabajadores» de personal_sagarde.html (paso 08e).

Comprueba que la pestaña de solo lectura refleja exactamente los datos esperados de datos_base_trabajadores.py
en múltiples zonas horarias, resoluciones móviles/escritorio y escenarios de avisos/errores.
"""
import io
import json
import os
import shutil
import sys
import tempfile
import uuid
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DIR_TESTS = os.path.dirname(os.path.abspath(__file__))
if DIR_TESTS not in sys.path:
    sys.path.insert(0, DIR_TESTS)
import datos_base_trabajadores as D

comprobaciones = 0
fallos = []


def comprobar(cond, contexto, esperado, obtenido=None):
    """Verifica una condición general y registra un fallo detallado si no se cumple."""
    global comprobaciones
    comprobaciones += 1
    if not cond:
        if obtenido is not None:
            detalle = f'se esperaba {esperado} y salió {obtenido}'
        else:
            detalle = str(esperado)
        fallos.append(f'[{contexto}] {detalle}')
        print(f'FALLO: [{contexto}] {detalle}')
        return False
    return True


def comprobar_igual(obtenido, esperado, contexto):
    """Compara si obtenido es igual a esperado y registra el fallo si difieren."""
    global comprobaciones
    comprobaciones += 1
    if obtenido != esperado:
        detalle = f'se esperaba {esperado!r} y salió {obtenido!r}'
        fallos.append(f'[{contexto}] {detalle}')
        print(f'FALLO: [{contexto}] {detalle}')
        return False
    return True


def registrar_excepcion(contexto, exc):
    """Registra una excepción imprevista como fallo sin detener la ejecución."""
    global comprobaciones
    comprobaciones += 1
    detalle = f'excepción {type(exc).__name__}: {exc}'
    fallos.append(f'[{contexto}] {detalle}')
    print(f'FALLO: [{contexto}] {detalle}')


def obtener_carpeta_motor():
    """Determina la carpeta donde residen personal_sagarde.html y personal_calculo.js."""
    if len(sys.argv) > 1:
        ruta = os.path.abspath(sys.argv[1])
    else:
        ruta = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if os.path.exists(os.path.join(ruta, 'personal_sagarde.html')):
        return ruta
    sub = os.path.join(ruta, 'motor')
    if os.path.exists(os.path.join(sub, 'personal_sagarde.html')):
        return sub
    return ruta


def url_de_fichero(ruta_html):
    """Convierte una ruta de archivo local en una URL file:/// válida para el navegador."""
    return 'file:///' + ruta_html.replace(os.sep, '/').replace(' ', '%20')


def montar_carpeta_temporal(motor, estado=None, con_calculo=True, carpetas=None):
    """Crea una carpeta temporal nueva con los ficheros indicados y devuelve su ruta."""
    base_tmp = os.environ.get('P3_TMP') or tempfile.gettempdir()
    d = os.path.join(base_tmp, 'base_trab_' + uuid.uuid4().hex[:8])
    os.makedirs(d)
    if carpetas is not None:
        carpetas.append(d)

    shutil.copy(os.path.join(motor, 'personal_sagarde.html'), os.path.join(d, 'personal_sagarde.html'))
    if con_calculo:
        shutil.copy(os.path.join(motor, 'personal_calculo.js'), os.path.join(d, 'personal_calculo.js'))

    if estado is not None:
        ruta_estado = os.path.join(d, 'personal_estado.js')
        with open(ruta_estado, 'w', encoding='utf-8') as fh:
            if isinstance(estado, str):
                fh.write(estado)
            else:
                fh.write('window.SAGARDE_PERSONAL = ' + json.dumps(estado, ensure_ascii=False) + ';\n')

    return d


def obtener_nombres_tabla(pg, selector='table.base tbody tr'):
    """Devuelve los nombres de las filas extrayendo el primer nodo de texto de td.b-nom."""
    return pg.eval_on_selector_all(
        selector,
        """trs => trs.map(tr => {
            const td = tr.querySelector('td.b-nom');
            return td && td.firstChild ? td.firstChild.textContent.trim() : '';
        })"""
    )


def esperar_carga_base(pg, timeout_ms=7000):
    """Espera a que #contenido-base ya no contenga el texto «Cargando»."""
    pg.wait_for_function(
        "() => !document.querySelector('#contenido-base') || "
        "!document.querySelector('#contenido-base').textContent.includes('Cargando')",
        timeout=timeout_ms
    )


def ejecutar_escenario_principal(browser, motor, tz, carpetas):
    """Ejecuta las comprobaciones del bloque A en una zona horaria concreta."""
    ctx = browser.new_context(
        viewport={'width': 1000, 'height': 900},
        timezone_id=tz,
        locale='es-ES'
    )
    carpeta = None
    try:
        carpeta = montar_carpeta_temporal(
            motor,
            estado=D.ESTADO_PRINCIPAL,
            con_calculo=True,
            carpetas=carpetas
        )
        url_html = url_de_fichero(os.path.join(carpeta, 'personal_sagarde.html'))
        pg = ctx.new_page()

        errores_consola = []
        pg.on('pageerror', lambda e: errores_consola.append(f'pageerror: {e}'))
        pg.on(
            'console',
            lambda msg: errores_consola.append(f'console {msg.type}: {msg.text}')
            if msg.type == 'error' else None
        )

        pg.goto(url_html)
        pg.wait_for_function(
            "() => !document.querySelector('#contenido') || "
            "!document.querySelector('#contenido').textContent.includes('Cargando')",
            timeout=7000
        )

        # 1. Pestañas al abrir
        vr_hidden = pg.eval_on_selector('#vista-ranking', 'el => el.hidden')
        vb_hidden = pg.eval_on_selector('#vista-base', 'el => el.hidden')
        comprobar(vr_hidden is False, f'{tz} A.1 ranking visible', 'hidden=False', f'hidden={vr_hidden}')
        comprobar(vb_hidden is True, f'{tz} A.1 base oculta', 'hidden=True', f'hidden={vb_hidden}')

        btn_rk_on = pg.eval_on_selector('#pestanas [data-v="ranking"]', 'el => el.classList.contains("on")')
        btn_rk_aria = pg.eval_on_selector('#pestanas [data-v="ranking"]', 'el => el.getAttribute("aria-pressed")')
        btn_bs_on = pg.eval_on_selector('#pestanas [data-v="base"]', 'el => el.classList.contains("on")')
        btn_bs_aria = pg.eval_on_selector('#pestanas [data-v="base"]', 'el => el.getAttribute("aria-pressed")')
        comprobar(btn_rk_on is True, f'{tz} A.1 boton ranking on', "clase 'on'", "sin 'on'")
        comprobar_igual(btn_rk_aria, 'true', f'{tz} A.1 boton ranking aria-pressed')
        comprobar(btn_bs_on is False, f'{tz} A.1 boton base sin on', "sin clase 'on'", "con 'on'")
        comprobar_igual(btn_bs_aria, 'false', f'{tz} A.1 boton base aria-pressed')

        # 2. Pulsar base
        pg.click('#pestanas [data-v="base"]')
        vr_hidden_2 = pg.eval_on_selector('#vista-ranking', 'el => el.hidden')
        vb_hidden_2 = pg.eval_on_selector('#vista-base', 'el => el.hidden')
        comprobar(vr_hidden_2 is True, f'{tz} A.2 ranking oculto', 'hidden=True', f'hidden={vr_hidden_2}')
        comprobar(vb_hidden_2 is False, f'{tz} A.2 base visible', 'hidden=False', f'hidden={vb_hidden_2}')

        btn_rk_on_2 = pg.eval_on_selector('#pestanas [data-v="ranking"]', 'el => el.classList.contains("on")')
        btn_rk_aria_2 = pg.eval_on_selector('#pestanas [data-v="ranking"]', 'el => el.getAttribute("aria-pressed")')
        btn_bs_on_2 = pg.eval_on_selector('#pestanas [data-v="base"]', 'el => el.classList.contains("on")')
        btn_bs_aria_2 = pg.eval_on_selector('#pestanas [data-v="base"]', 'el => el.getAttribute("aria-pressed")')
        comprobar(btn_rk_on_2 is False, f'{tz} A.2 boton ranking sin on', "sin clase 'on'", "con 'on'")
        comprobar_igual(btn_rk_aria_2, 'false', f'{tz} A.2 boton ranking aria-pressed')
        comprobar(btn_bs_on_2 is True, f'{tz} A.2 boton base on', "clase 'on'", "sin 'on'")
        comprobar_igual(btn_bs_aria_2, 'true', f'{tz} A.2 boton base aria-pressed')

        hash_2 = pg.evaluate('location.hash')
        comprobar_igual(hash_2, '#base', f'{tz} A.2 location.hash')
        esperar_carga_base(pg)

        # 3. Tabla
        cabecera = pg.eval_on_selector_all(
            'table.base thead th',
            'ths => ths.map(th => th.textContent.trim())'
        )
        comprobar_igual(cabecera, D.CABECERA, f'{tz} A.3 cabecera')

        filas_dom = pg.evaluate("""() => {
            const trs = document.querySelectorAll('table.base tbody tr');
            return Array.from(trs).map(tr => {
                const tdNom = tr.querySelector('td.b-nom');
                let nombre = '';
                if (tdNom && tdNom.firstChild) {
                    nombre = tdNom.firstChild.textContent.trim();
                }
                const empEl = tr.querySelector('td.b-emp .nom-emp') || (tdNom ? tdNom.querySelector('.nom-emp') : null);
                const empresa = empEl ? empEl.textContent.trim() : '';
                const etiquetas = tdNom
                    ? Array.from(tdNom.querySelectorAll('.chip')).map(c => c.textContent.trim())
                    : [];

                const tdObras = tr.querySelector('td.b-obras');
                const chips = tdObras
                    ? Array.from(tdObras.querySelectorAll('.chip')).map(c => c.innerText.trim())
                    : [];
                const sinjEl = tdObras ? tdObras.querySelector('.sinj') : null;
                const sinjTexto = sinjEl ? sinjEl.textContent.trim() : null;

                const tdD = tr.querySelector('td.b-d');
                const dias = tdD ? tdD.innerText.trim() : '';

                const tdH = tr.querySelector('td.b-h');
                const horas = tdH ? tdH.innerText.trim() : '';

                const tdHist = tr.querySelector('td.b-hist');
                const historia = tdHist ? tdHist.innerText.trim() : '';

                const tdUlt = tr.querySelector('td.b-ult');
                const ultima = tdUlt
                    ? tdUlt.innerText.split('\\n').map(l => l.trim()).filter(Boolean)
                    : [];

                return {
                    nombre,
                    empresa,
                    etiquetas,
                    chips,
                    tiene_sinj: sinjEl !== null,
                    sinj_texto: sinjTexto,
                    dias,
                    horas,
                    historia,
                    ultima
                };
            });
        }""")

        nombres_filas = [r['nombre'] for r in filas_dom]
        comprobar_igual(nombres_filas, D.NOMBRES, f'{tz} A.3 nombres de filas')

        for r in filas_dom:
            nom = r['nombre']
            esp = D.FILAS.get(nom)
            if not esp:
                comprobar(
                    False,
                    f'{tz} A.3 fila {nom}',
                    f'datos esperados para {nom}',
                    'fila no encontrada en D.FILAS'
                )
                continue

            comprobar_igual(r['empresa'], esp['empresa'], f'{tz} A.3 {nom} empresa')
            comprobar_igual(r['etiquetas'], esp['etiquetas'], f'{tz} A.3 {nom} etiquetas')
            comprobar_igual(r['chips'], esp['chips'], f'{tz} A.3 {nom} chips')

            if esp['sin_jornadas']:
                cond_sinj = (
                    r['tiene_sinj']
                    and r['sinj_texto'] == 'Sin jornadas todavía'
                    and len(r['chips']) == 0
                )
                comprobar(
                    cond_sinj,
                    f'{tz} A.3 {nom} sin_jornadas',
                    ".sinj con 'Sin jornadas todavía' y sin chips",
                    f"tiene_sinj={r['tiene_sinj']}, texto={r['sinj_texto']!r}, chips={r['chips']}"
                )
            else:
                comprobar(
                    not r['tiene_sinj'],
                    f'{tz} A.3 {nom} sin_jornadas falso',
                    'sin elemento .sinj',
                    f"tiene_sinj={r['tiene_sinj']}"
                )

            comprobar_igual(r['dias'], esp['dias'], f'{tz} A.3 {nom} dias')
            comprobar_igual(r['horas'], esp['horas'], f'{tz} A.3 {nom} horas')
            comprobar_igual(r['historia'], esp['historia'], f'{tz} A.3 {nom} historia')
            comprobar_igual(r['ultima'], esp['ultima'], f'{tz} A.3 {nom} ultima')

        # 4. Cifras generales
        kpis_dom = pg.eval_on_selector_all(
            '#contenido-base .kpi',
            """els => els.map(e => [
                (e.querySelector('b') ? e.querySelector('b').textContent.trim() : ''),
                (e.querySelector('span') ? e.querySelector('span').textContent.trim() : '')
            ])"""
        )
        kpis_tuplas = [tuple(k) for k in kpis_dom]
        comprobar_igual(kpis_tuplas, D.KPIS, f'{tz} A.4 kpis')

        cuenta_base = pg.eval_on_selector('#base-lista .cuenta', 'el => el.textContent.trim()')
        comprobar_igual(cuenta_base, '6 personas', f'{tz} A.4 cuenta')

        # 5. Escapado
        num_i = pg.eval_on_selector_all('table.base i', 'els => els.length')
        num_b = pg.eval_on_selector_all('table.base b', 'els => els.length')
        comprobar_igual(num_i, 0, f'{tz} A.5 table.base sin elementos <i>')
        comprobar_igual(num_b, 0, f'{tz} A.5 table.base sin elementos <b>')

        body_text = pg.inner_text('body')
        comprobar(
            'Zoe & <i>Co</i>' in body_text,
            f'{tz} A.5 escapado Zoe',
            'texto visible contiene Zoe & <i>Co</i>',
            'no encontrado en body'
        )
        comprobar(
            '«<b>vieja</b>»' in body_text,
            f'{tz} A.5 escapado vieja',
            'texto visible contiene «<b>vieja</b>»',
            'no encontrado en body'
        )

        # 6. Orden
        for clave, nombres_esp in D.ORDENES.items():
            pg.click(f'#controles-base [data-o="{clave}"]')
            nombres_act = obtener_nombres_tabla(pg)
            comprobar_igual(nombres_act, nombres_esp, f'{tz} A.6 orden {clave} nombres')

            for otro in ('nombre', 'horas', 'ultima'):
                btn_on = pg.eval_on_selector(
                    f'#controles-base [data-o="{otro}"]',
                    'el => el.classList.contains("on")'
                )
                btn_aria = pg.eval_on_selector(
                    f'#controles-base [data-o="{otro}"]',
                    'el => el.getAttribute("aria-pressed")'
                )
                if otro == clave:
                    comprobar(btn_on is True, f'{tz} A.6 orden {clave} boton {otro} on', "clase 'on'", "sin 'on'")
                    comprobar_igual(btn_aria, 'true', f'{tz} A.6 orden {clave} boton {otro} aria-pressed')
                else:
                    comprobar(
                        btn_on is False,
                        f'{tz} A.6 orden {clave} boton {otro} sin on',
                        "sin clase 'on'",
                        "con 'on'"
                    )
                    comprobar_igual(btn_aria, 'false', f'{tz} A.6 orden {clave} boton {otro} aria-pressed')

        pg.click('#controles-base [data-o="nombre"]')
        nombres_final_orden = obtener_nombres_tabla(pg)
        comprobar_igual(nombres_final_orden, D.ORDENES['nombre'], f'{tz} A.6 orden final nombre')

        # 7. Buscador
        for txt, nombres_esp, cuenta_esp in D.BUSQUEDAS:
            pg.fill('#buscar', txt)
            nombres_act = obtener_nombres_tabla(pg)
            comprobar_igual(nombres_act, nombres_esp, f'{tz} A.7 buscar {txt!r} nombres')
            cuenta_act = pg.eval_on_selector('#base-lista .cuenta', 'el => el.textContent.trim()')
            comprobar_igual(cuenta_act, cuenta_esp, f'{tz} A.7 buscar {txt!r} cuenta')

        txt_sin, cuenta_sin, vacio_sin = D.BUSQUEDA_SIN_RESULTADOS
        pg.fill('#buscar', txt_sin)
        num_tablas = pg.eval_on_selector_all('table.base', 'els => els.length')
        comprobar_igual(num_tablas, 0, f'{tz} A.7 sin resultados existencia table.base')
        cuenta_sin_act = pg.eval_on_selector('#base-lista .cuenta', 'el => el.textContent.trim()')
        comprobar_igual(cuenta_sin_act, cuenta_sin, f'{tz} A.7 sin resultados cuenta')
        vacio_act = pg.eval_on_selector('#base-lista .empty', 'el => el.textContent.trim()')
        comprobar_igual(vacio_act, vacio_sin, f'{tz} A.7 sin resultados vacio')

        pg.fill('#buscar', '')
        nombres_vuelven = obtener_nombres_tabla(pg)
        comprobar_igual(nombres_vuelven, D.NOMBRES, f'{tz} A.7 buscador vaciado nombres')
        cuenta_vuelven = pg.eval_on_selector('#base-lista .cuenta', 'el => el.textContent.trim()')
        comprobar_igual(cuenta_vuelven, '6 personas', f'{tz} A.7 buscador vaciado cuenta')

        # 8. Buscar y ordenar a la vez
        txt_bo, ord_bo, nombres_bo = D.BUSQUEDA_Y_ORDEN
        pg.fill('#buscar', txt_bo)
        pg.click(f'#controles-base [data-o="{ord_bo}"]')
        nombres_bo_act = obtener_nombres_tabla(pg)
        comprobar_igual(nombres_bo_act, nombres_bo, f'{tz} A.8 buscar y ordenar nombres')

        pg.fill('#buscar', '')
        pg.click('#controles-base [data-o="nombre"]')

        # 9. Volver al ranking
        pg.click('#pestanas [data-v="ranking"]')
        vr_hidden_9 = pg.eval_on_selector('#vista-ranking', 'el => el.hidden')
        vb_hidden_9 = pg.eval_on_selector('#vista-base', 'el => el.hidden')
        comprobar(vr_hidden_9 is False, f'{tz} A.9 volver ranking visible', 'hidden=False', f'hidden={vr_hidden_9}')
        comprobar(vb_hidden_9 is True, f'{tz} A.9 volver base oculta', 'hidden=True', f'hidden={vb_hidden_9}')

        btn_rk_on_9 = pg.eval_on_selector('#pestanas [data-v="ranking"]', 'el => el.classList.contains("on")')
        btn_rk_aria_9 = pg.eval_on_selector('#pestanas [data-v="ranking"]', 'el => el.getAttribute("aria-pressed")')
        btn_bs_on_9 = pg.eval_on_selector('#pestanas [data-v="base"]', 'el => el.classList.contains("on")')
        btn_bs_aria_9 = pg.eval_on_selector('#pestanas [data-v="base"]', 'el => el.getAttribute("aria-pressed")')
        comprobar(btn_rk_on_9 is True, f'{tz} A.9 volver boton ranking on', "clase 'on'", "sin 'on'")
        comprobar_igual(btn_rk_aria_9, 'true', f'{tz} A.9 volver boton ranking aria-pressed')
        comprobar(btn_bs_on_9 is False, f'{tz} A.9 volver boton base sin on', "sin clase 'on'", "con 'on'")
        comprobar_igual(btn_bs_aria_9, 'false', f'{tz} A.9 volver boton base aria-pressed')

        hash_9 = pg.evaluate('location.hash')
        comprobar_igual(hash_9, '', f'{tz} A.9 volver ranking hash vacio')

        # 10. Ranking sigue funcionando
        filas_rk = pg.eval_on_selector_all('#contenido table.data tbody tr', 'els => els.length')
        comprobar(filas_rk >= 1, f'{tz} A.10 ranking filas presentes', 'al menos 1 fila', f'{filas_rk} filas')
        ctl_hidden = pg.eval_on_selector('#controles', 'el => el.hidden')
        comprobar(ctl_hidden is False, f'{tz} A.10 controles ranking visibles', 'hidden=False', f'hidden={ctl_hidden}')

        # 11. Enlace directo
        pg2 = ctx.new_page()
        pg2.on('pageerror', lambda e: errores_consola.append(f'pageerror pg2: {e}'))
        pg2.on(
            'console',
            lambda msg: errores_consola.append(f'console pg2 {msg.type}: {msg.text}')
            if msg.type == 'error' else None
        )
        pg2.goto(url_html + '#base')
        esperar_carga_base(pg2)

        vb2_hidden = pg2.eval_on_selector('#vista-base', 'el => el.hidden')
        vr2_hidden = pg2.eval_on_selector('#vista-ranking', 'el => el.hidden')
        comprobar(vb2_hidden is False, f'{tz} A.11 enlace directo base visible', 'hidden=False', f'hidden={vb2_hidden}')
        comprobar(vr2_hidden is True, f'{tz} A.11 enlace directo ranking oculto', 'hidden=True', f'hidden={vr2_hidden}')

        btn_bs2_on = pg2.eval_on_selector('#pestanas [data-v="base"]', 'el => el.classList.contains("on")')
        btn_bs2_aria = pg2.eval_on_selector('#pestanas [data-v="base"]', 'el => el.getAttribute("aria-pressed")')
        btn_rk2_on = pg2.eval_on_selector('#pestanas [data-v="ranking"]', 'el => el.classList.contains("on")')
        btn_rk2_aria = pg2.eval_on_selector('#pestanas [data-v="ranking"]', 'el => el.getAttribute("aria-pressed")')
        comprobar(btn_bs2_on is True, f'{tz} A.11 enlace directo boton base on', "clase 'on'", "sin 'on'")
        comprobar_igual(btn_bs2_aria, 'true', f'{tz} A.11 enlace directo boton base aria-pressed')
        comprobar(btn_rk2_on is False, f'{tz} A.11 enlace directo boton ranking sin on', "sin clase 'on'", "con 'on'")
        comprobar_igual(btn_rk2_aria, 'false', f'{tz} A.11 enlace directo boton ranking aria-pressed')

        pg2.close()
        pg.close()

        comprobar(
            len(errores_consola) == 0,
            f'{tz} consola limpia',
            'cero errores de consola o pageerror',
            f'{errores_consola}'
        )
    finally:
        ctx.close()


def ejecutar_escenario_movil(browser, motor, carpetas):
    """Ejecuta las comprobaciones de vistas de escritorio y móvil del bloque B."""
    ctx = browser.new_context(
        viewport={'width': 1000, 'height': 900},
        timezone_id='Europe/Madrid',
        locale='es-ES'
    )
    carpeta = None
    try:
        carpeta = montar_carpeta_temporal(
            motor,
            estado=D.ESTADO_PRINCIPAL,
            con_calculo=True,
            carpetas=carpetas
        )
        url_html = url_de_fichero(os.path.join(carpeta, 'personal_sagarde.html'))
        pg = ctx.new_page()

        pg.goto(url_html)
        pg.click('#pestanas [data-v="base"]')
        esperar_carga_base(pg)

        # 1000 px de ancho
        disp_tbl = pg.evaluate("getComputedStyle(document.querySelector('table.base')).display")
        comprobar_igual(disp_tbl, 'table', 'B 1000px table.base display')
        disp_th = pg.evaluate("getComputedStyle(document.querySelector('table.base thead')).display")
        comprobar(disp_th != 'none', 'B 1000px thead display no es none', 'display != none', f'display={disp_th}')

        # 390 px de ancho (alto 844)
        pg.set_viewport_size({'width': 390, 'height': 844})
        disp_th_390 = pg.evaluate("getComputedStyle(document.querySelector('table.base thead')).display")
        comprobar_igual(disp_th_390, 'none', 'B 390px thead display: none')

        disp_tr_390 = pg.evaluate("getComputedStyle(document.querySelector('table.base tbody tr')).display")
        comprobar_igual(disp_tr_390, 'grid', 'B 390px primer tr display: grid')

        ana_datos = pg.evaluate("""() => {
            const trs = document.querySelectorAll('table.base tbody tr');
            for (const tr of trs) {
                const tdNom = tr.querySelector('td.b-nom');
                if (tdNom && tdNom.firstChild && tdNom.firstChild.textContent.trim() === 'Ana') {
                    return {
                        horas: tr.querySelector('td.b-h') ? tr.querySelector('td.b-h').innerText.trim() : '',
                        dias: tr.querySelector('td.b-d') ? tr.querySelector('td.b-d').innerText.trim() : ''
                    };
                }
            }
            return { horas: '', dias: '' };
        }""")
        comprobar_igual(ana_datos['horas'], D.MOVIL_ANA['horas'], 'B 390px Ana td.b-h inner_text')
        comprobar_igual(ana_datos['dias'], D.MOVIL_ANA['dias'], 'B 390px Ana td.b-d inner_text')

        dani_datos = pg.evaluate("""() => {
            const trs = document.querySelectorAll('table.base tbody tr');
            let trDani = null;
            for (const tr of trs) {
                const tdNom = tr.querySelector('td.b-nom');
                if (tdNom && tdNom.firstChild && tdNom.firstChild.textContent.trim() === 'Dani') {
                    trDani = tr;
                    break;
                }
            }
            if (!trDani && trs.length >= 4) {
                trDani = trs[3];
            }
            if (!trDani) return { dias_disp: null, ult_disp: null };
            const tdD = trDani.querySelector('td.b-d');
            const tdUlt = trDani.querySelector('td.b-ult');
            return {
                dias_disp: tdD ? getComputedStyle(tdD).display : null,
                ult_disp: tdUlt ? getComputedStyle(tdUlt).display : null
            };
        }""")
        comprobar_igual(dani_datos['dias_disp'], 'none', 'B 390px Dani td.b-d display: none')
        comprobar_igual(dani_datos['ult_disp'], 'none', 'B 390px Dani td.b-ult display: none')

        sw_390 = pg.evaluate('document.documentElement.scrollWidth')
        comprobar(sw_390 <= 390, 'B 390px scrollWidth <= ventana', 'scrollWidth <= 390', f'scrollWidth={sw_390}')

        # 320 px de ancho
        pg.set_viewport_size({'width': 320, 'height': 844})
        sw_320 = pg.evaluate('document.documentElement.scrollWidth')
        comprobar(sw_320 <= 320, 'B 320px scrollWidth <= 320', 'scrollWidth <= 320', f'scrollWidth={sw_320}')

        pg.close()
    finally:
        ctx.close()


def ejecutar_escenarios_mensajes(browser, motor, carpetas):
    """Ejecuta los escenarios de avisos y errores de configuración del bloque C."""
    ctx = browser.new_context(
        viewport={'width': 1000, 'height': 900},
        timezone_id='Europe/Madrid',
        locale='es-ES'
    )
    try:
        for esc in D.ESCENARIOS:
            esc_id = esc['id']
            try:
                carpeta = montar_carpeta_temporal(
                    motor,
                    estado=esc.get('estado'),
                    con_calculo=esc.get('con_calculo', True),
                    carpetas=carpetas
                )
                url_html = url_de_fichero(os.path.join(carpeta, 'personal_sagarde.html'))
                pg = ctx.new_page()
                try:
                    pg.goto(url_html)
                    esperar_carga_base(pg)

                    # Ranking
                    if esc.get('ranking') is not None:
                        rk = esc['ranking']
                        empty_esp = rk.get('empty', [])
                        aviso_esp = rk.get('aviso', [])

                        empty_act = pg.eval_on_selector_all(
                            '#contenido .empty',
                            'els => els.map(e => e.textContent.trim())'
                        )
                        aviso_act = pg.eval_on_selector_all(
                            '#contenido .aviso',
                            'els => els.map(e => e.textContent.trim())'
                        )
                        comprobar_igual(empty_act, empty_esp, f'C [{esc_id}] ranking empty')
                        comprobar_igual(aviso_act, aviso_esp, f'C [{esc_id}] ranking aviso')

                    # Base
                    if esc.get('base') is not None:
                        bs = esc['base']
                        empty_esp = bs.get('empty', [])
                        aviso_esp = bs.get('aviso', [])

                        empty_act = pg.eval_on_selector_all(
                            '#contenido-base .empty',
                            'els => els.map(e => e.textContent.trim())'
                        )
                        aviso_act = pg.eval_on_selector_all(
                            '#contenido-base .aviso',
                            'els => els.map(e => e.textContent.trim())'
                        )
                        comprobar_igual(empty_act, empty_esp, f'C [{esc_id}] base empty')
                        comprobar_igual(aviso_act, aviso_esp, f'C [{esc_id}] base aviso')

                        if 'filas' in bs:
                            filas_esp = bs['filas']
                            filas_act = pg.eval_on_selector_all(
                                '#contenido-base table.base tbody tr',
                                """trs => trs.map(tr => {
                                    const td = tr.querySelector('td.b-nom');
                                    return td && td.firstChild ? td.firstChild.textContent.trim() : '';
                                })"""
                            )
                            comprobar_igual(filas_act, filas_esp, f'C [{esc_id}] base filas')

                        if 'kpis' in bs:
                            kpis_esp = bs['kpis']
                            kpis_act = pg.eval_on_selector_all(
                                '#contenido-base .kpi',
                                """els => els.map(e => [
                                    (e.querySelector('b') ? e.querySelector('b').textContent.trim() : ''),
                                    (e.querySelector('span') ? e.querySelector('span').textContent.trim() : '')
                                ])"""
                            )
                            kpis_act_tuplas = [tuple(k) for k in kpis_act]
                            comprobar_igual(kpis_act_tuplas, kpis_esp, f'C [{esc_id}] base kpis')

                        if bs.get('sin_etiqueta_aviso'):
                            num_etq = pg.eval_on_selector_all('.etq-aviso', 'els => els.length')
                            comprobar_igual(num_etq, 0, f'C [{esc_id}] sin_etiqueta_aviso')

                        if 'etiquetas' in bs:
                            etq_dict_esp = bs['etiquetas']
                            etq_dict_act = pg.evaluate("""() => {
                                const res = {};
                                const trs = document.querySelectorAll('#contenido-base table.base tbody tr');
                                for (const tr of trs) {
                                    const td = tr.querySelector('td.b-nom');
                                    const nom = td && td.firstChild ? td.firstChild.textContent.trim() : '';
                                    const chips = td
                                        ? Array.from(td.querySelectorAll('.chip')).map(c => c.textContent.trim())
                                        : [];
                                    res[nom] = chips;
                                }
                                return res;
                            }""")
                            for nom in bs.get('filas', []):
                                esp_chips = etq_dict_esp.get(nom, [])
                                act_chips = etq_dict_act.get(nom, [])
                                comprobar_igual(act_chips, esp_chips, f'C [{esc_id}] etiquetas {nom}')
                finally:
                    pg.close()
            except Exception as e:
                registrar_excepcion(f'C [{esc_id}]', e)
    finally:
        ctx.close()


def main():
    """Función principal: orquesta la verificación completa y gestiona la salida."""
    motor = obtener_carpeta_motor()
    carpetas_temporales = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                # Bloque A: Escenario principal en las tres zonas horarias
                for tz in D.ZONAS_HORARIAS:
                    try:
                        ejecutar_escenario_principal(browser, motor, tz, carpetas_temporales)
                    except Exception as e:
                        registrar_excepcion(f'{tz} escenario principal', e)

                # Bloque B: Móvil y escritorio (Europe/Madrid)
                try:
                    ejecutar_escenario_movil(browser, motor, carpetas_temporales)
                except Exception as e:
                    registrar_excepcion('Bloque B movil/escritorio', e)

                # Bloque C: Escenarios con avisos y mensajes
                try:
                    ejecutar_escenarios_mensajes(browser, motor, carpetas_temporales)
                except Exception as e:
                    registrar_excepcion('Bloque C escenarios avisos', e)
            finally:
                browser.close()
    finally:
        for carpeta in carpetas_temporales:
            shutil.rmtree(carpeta, ignore_errors=True)

    if fallos:
        print(f'FALLOS: {len(fallos)}')
        sys.exit(1)
    else:
        print(f'OK: base de trabajadores ({comprobaciones} comprobaciones)')
        sys.exit(0)


if __name__ == '__main__':
    main()
