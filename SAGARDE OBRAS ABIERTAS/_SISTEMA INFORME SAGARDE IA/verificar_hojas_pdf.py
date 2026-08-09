# -*- coding: utf-8 -*-
"""Imprime el PDF A4 real de cada obra con ficha y lo valida.

No es una comprobacion a ojo. Se imprime como imprime Bixente y se lee con el
mismo `rejilla_hoja.py` que lee las hojas marcadas en obra. Lo que se afirma:

  - toda pagina de tabla tiene UNA sola tabla: `leer_pdf` coge solo tablas[0],
    asi que una segunda tabla en la misma pagina desapareceria en silencio;
  - ninguna pagina de tabla baja de CELDAS_MINIMAS: por debajo de eso
    `leer_pdf` la descarta sin avisar, y con ella las marcas que llevara;
  - toda pagina de tabla lleva su fila de identificacion;
  - la union de celdas de todas las paginas es la rejilla completa.

Comprobar la paginacion mirando el PDF es como fiarse del porcentaje
redondeado: no se entera de que una pagina con 3 celdas se ha tirado.

Requiere Node y Playwright, que NO son dependencias de la suite: este arnes se
lanza a mano. Sin ellos, la prueba equivalente de tests/ se salta.

Uso:  python verificar_hojas_pdf.py [obra ...]
"""
import os
import re
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, 'tests'))

import rejilla_hoja
from test_paginacion_generador import NODE, hoja_de

# Rejilla completa de cada obra con ficha: ubicaciones x tajos.
ESPERADAS = {'gernika': 1216, 'mungia': 2356, 'bolueta': 3686,
             'obisporueta': 5610, 'prueba': 1178}


def _tabla_de(obra):
    """Tabla de tajos de esa obra: la comun mas los suyos propios.

    Se lee la ficha por el id corto del generador. Si la obra no tiene ficha
    -o el registro no la conoce- se cae a la tabla comun, que es lo que habia
    antes: nunca queda peor que sin esto.
    """
    import ficha_obra
    from registro_obras import OBRAS
    entrada = next((o for o in OBRAS if o.get('id') == obra), None)
    if entrada and entrada.get('carpeta_obra'):
        carpeta = os.path.join(os.path.dirname(AQUI), entrada['carpeta_obra'])
        try:
            ficha = ficha_obra.cargar(carpeta)
        except Exception:
            ficha = None
        if ficha:
            return rejilla_hoja.tabla_con_tajos_de_obra(ficha)
    return rejilla_hoja.tabla_de_tajos()


def generar_html(obra, destino):
    """Escribe la hoja que produce hoy el generador para esa obra."""
    with open(destino, 'w', encoding='utf-8') as f:
        f.write(hoja_de(obra))
    return destino


def imprimir_pdf(html, pdf):
    """A4 con los margenes que declara el propio @page del generador."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch(channel='msedge')
        pagina = nav.new_page()
        pagina.goto('file:///' + os.path.abspath(html).replace('\\', '/'),
                    wait_until='load')
        pagina.emulate_media(media='print')
        pagina.pdf(path=pdf, format='A4', print_background=True,
                   prefer_css_page_size=True)
        nav.close()
    return pdf


def validar(pdf, esperadas, obra):
    """[] si todo esta bien; si no, la lista de problemas concretos."""
    import pdfplumber
    problemas = []
    paginas_tabla = 0
    with pdfplumber.open(pdf) as doc:
        for n, pagina in enumerate(doc.pages, 1):
            tablas = pagina.find_tables()
            if not tablas:
                # La pagina 1 es la portada: cabecera y leyenda, sin tabla.
                # Cualquier OTRA pagina sin tabla es papel desperdiciado, que
                # es de lo que se quejaba Bixente. No dar error aqui era dejar
                # el defecto sin comprobar.
                if n != 1:
                    problemas.append(
                        'pagina %d: sin tabla. Papel desperdiciado entre '
                        'tablas' % n)
                continue
            celdas = max(len(t.cells) for t in tablas)
            if celdas < rejilla_hoja.CELDAS_MINIMAS:
                # Solo la pagina 1 puede estar por debajo del minimo: es la
                # portada. Cualquier otra es o un resto de tabla que leer_pdf
                # tiraria sin avisar, o papel desperdiciado. Filtrar aqui por
                # si el texto dice "TAJO" era demasiado indulgente: dejaba
                # pasar paginas con solo el rotulo de portal o el pie.
                if n != 1:
                    problemas.append(
                        'pagina %d: %d celdas, por debajo del minimo %d. O es '
                        'un resto de tabla que leer_pdf descartaria sin '
                        'avisar, o es papel desperdiciado'
                        % (n, celdas, rejilla_hoja.CELDAS_MINIMAS))
                continue
            paginas_tabla += 1
            if len(tablas) > 1:
                problemas.append(
                    'pagina %d: %d tablas; leer_pdf solo lee la primera y la '
                    'segunda desapareceria' % (n, len(tablas)))
            texto = pagina.extract_text() or ''
            if not re.search(r'\d{2}/\d{2}/\d{4}', texto[:600]):
                problemas.append('pagina %d: sin fila de identificacion' % n)
    if not paginas_tabla:
        problemas.append('ninguna pagina con tabla de revision')

    try:
        # Con los tajos propios de la obra, como los lee leer_hoja_marcada.
        # Con solo el catalogo comun, Orueta era 'NO VERIFICABLE' porque 16 de
        # sus 40 tajos desglosan por zona y no estan en el comun (08/08/2026).
        leidas = rejilla_hoja.leer_pdf(pdf, _tabla_de(obra))
        total = sum(len(t['celdas']) for _, t in leidas)
        if total != esperadas:
            problemas.append('celdas leidas %d, esperadas %d' % (total, esperadas))
    except rejilla_hoja.HojaIlegible as exc:
        problemas.append('NO VERIFICABLE por datos de la obra: %s' % exc)
    return problemas


def main(obras):
    if not NODE:
        print('[ABORTA] node no esta instalado: no se puede generar la hoja.')
        return 2
    fallos = 0
    with tempfile.TemporaryDirectory() as tmp:
        for obra in obras:
            esperadas = ESPERADAS[obra]
            html = generar_html(obra, os.path.join(tmp, obra + '.html'))
            pdf = imprimir_pdf(html, os.path.join(tmp, obra + '.pdf'))
            import pdfplumber
            with pdfplumber.open(pdf) as doc:
                npaginas = len(doc.pages)
            problemas = validar(pdf, esperadas, obra)
            duros = [p for p in problemas if not p.startswith('NO VERIFICABLE')]
            avisos = [p for p in problemas if p.startswith('NO VERIFICABLE')]
            estado = 'OK' if not duros else 'FALLA'
            print('[%s] %-12s %2d paginas' % (estado, obra, npaginas))
            for p in duros:
                print('        %s' % p)
            for p in avisos:
                print('        [aviso] %s' % p)
            fallos += len(duros)
    print('\n%s' % ('TODO CORRECTO' if not fallos else '%d PROBLEMA(S)' % fallos))
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:] or list(ESPERADAS)))
