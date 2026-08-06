# -*- coding: utf-8 -*-
"""LA REJILLA DE UNA HOJA DE REVISION GENERADA (capa comun)
============================================================

Resuelve, por GEOMETRIA, que celda es cada posicion de la hoja que imprime
`generador_revisiones.html`. Lo usan el alta de una obra
(`alta_obra_desde_hoja.py`) y el lector de hojas marcadas
(`leer_hoja_marcada.py`). Vive aparte porque los dos necesitan exactamente lo
mismo y tenerlo duplicado acaba en un camino arreglado y su hermano roto.

POR QUE GEOMETRIA Y NO TEXTO
----------------------------
El error caro al leer una hoja no es confundir una `X` con una `M`: es
atribuir una marca a la fila o columna equivocada, porque produce un dato
plausible en el sitio equivocado y nadie se entera. Por eso la clave
(portal, planta, vivienda, tajo) sale siempre de la rejilla.

Y ademas el texto, aqui, miente:

- La cabecera de una columna estrecha viene partida en varias lineas
  ("PLANT\\nPB .\\n1\\nVIV.") y su texto desborda sobre la celda vecina, que
  acaba leyendose "APLANTA 1a". Por eso el nombre de planta se busca por su
  FORMA (PB, 1a, 2a...), no limpiando un prefijo.
- La cabecera de grupo "REMATES EXTERIORES" contiene "EXT", que es tambien el
  distintivo de propiedad de un tajo. Distinguirlas por texto colaba un tajo
  fantasma llamado "REMATES ERIORES". Se distinguen por anchura: una cabecera
  de grupo ocupa toda la fila (una celda) y una fila de tajo tiene la del
  nombre mas una por vivienda.

Las dos trampas son reales: las dos aparecieron el 05/08/2026 leyendo la
primera hoja de OBRA PRUEBA.

QUE SE COMPRUEBA
----------------
Cada cabecera de planta declara cuantas viviendas tiene ("PLANTA 1a . 4
VIV."). Si la rejilla no trae exactamente esas columnas, se para. Es una
comprobacion cruzada gratis: la hoja se contradice a si misma antes de que
nosotros nos equivoquemos.
"""
import json
import os
import re
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
CATALOGO = os.path.join(AQUI, 'reglas', 'CATALOGO_TAJOS.json')
GENERADOR = os.path.join(AQUI, 'generador_revisiones.html')

FORMA_PLANTA = re.compile(r'(PB|BAJO|BAJA|ATICO|ÁTICO|S\d*|\d+ª|\d+)', re.I)
DISTINTIVOS = re.compile(r'(SGD|EXT|COO|edif|zzcc)')
FECHA = re.compile(r'\d{2}/\d{2}/\d{4}')
CELDAS_MINIMAS = 50          # por debajo de esto la "tabla" es un adorno


class HojaIlegible(Exception):
    """La hoja no se puede leer sin adivinar. Nunca se sigue adivinando."""


def limpio(valor):
    return re.sub(r'\s+', ' ', str(valor or '')).strip()


def fold(valor):
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()


# ----------------------------------------------------------- tajos impresos

def tabla_de_tajos(ruta_generador=GENERADOR, ruta_catalogo=CATALOGO):
    """nombre impreso (fold) -> entrada del catalogo comun.

    La cadena la declara el propio generador: nombre impreso -> id del
    generador -> BASE_SOURCE_ID -> id del catalogo. La hoja imprime nombres
    cortos ("Montante teleco") y el catalogo guarda los largos ("Montante de
    telecomunicaciones"): comparar cadenas pierde tajos en silencio.
    """
    with open(ruta_generador, encoding='utf-8') as f:
        html = f.read()
    bloque = re.search(r'let CAT = \[(.*?)\n\];', html, re.S)
    tabla = re.search(r'const BASE_SOURCE_ID = \{(.*?)\n\};', html, re.S)
    if not bloque or not tabla:
        raise HojaIlegible(
            'No se encuentran CAT o BASE_SOURCE_ID en '
            f'{os.path.basename(ruta_generador)}. Sin esa tabla los nombres '
            'cortos de la hoja no se pueden traducir al catalogo comun.')

    traduce = dict(re.findall(r"'?([\w-]+)'?\s*:\s*'([\w-]+)'", tabla.group(1)))
    with open(ruta_catalogo, encoding='utf-8') as f:
        por_id = {t['id']: t for t in json.load(f)['tajos']}

    indice, huerfanos = {}, []
    for m in re.finditer(
            r"\{id:'([^']+)',\s*name:'([^']+)',\s*g:'([^']+)',\s*p:'(\w)',a:'(\w)'\}",
            bloque.group(1)):
        destino = por_id.get(traduce.get(m.group(1), m.group(1)))
        if destino is None:
            huerfanos.append(m.group(2))
        else:
            indice[fold(m.group(2))] = destino
    if huerfanos:
        raise HojaIlegible(
            'Tajos del generador que no existen en el catalogo comun: '
            + ', '.join(huerfanos))

    # Y tambien por el nombre LARGO del catalogo y sus alias: las hojas
    # anteriores imprimian "Montante de telecomunicaciones" donde la de hoy
    # pone "Montante teleco". Sin esto una hoja de julio no se puede releer.
    # Los nombres del generador mandan si hubiera choque, porque son los que
    # imprime la hoja actual.
    for tajo in por_id.values():
        for nombre in [tajo.get('nombre'), *(tajo.get('aliases') or [])]:
            clave = fold(nombre)
            if clave and clave not in indice:
                indice[clave] = tajo
    return indice


# ------------------------------------------------------- lectura de una tabla

def leer_tabla(filas, texto, indice_tajos, aviso=''):
    """Resuelve una tabla de la hoja. Nucleo puro, sin PDF, para poder probarlo.

    `filas`  : [(bbox_fila, [bbox_celda, ...]), ...] de arriba a abajo.
    `texto`  : callable(bbox) -> str, el texto que hay en ese recorte.

    Devuelve None si la tabla no es una tabla de revision (portada, pie...).
    """
    # La fila de identificacion se busca por ESTRUCTURA, no por su contenido:
    # ocupa toda la anchura (una celda) y va seguida de la fila de plantas
    # (varias celdas) y la de viviendas. Anclarla en la fecha dejaba fuera el
    # formato anterior de hoja, que no la lleva: la de Bolueta del 26/07/2026
    # pone solo "BOLUETA · PORTAL UNICO · PLANTAS PB · 1".
    idx = ident = None
    for i, (_bbox, celdas) in enumerate(filas[:-2]):
        if len(celdas) != 1:
            continue
        candidato = texto(celdas[0])
        if not candidato or '·' not in candidato:
            continue
        if len(filas[i + 1][1]) < 2:
            continue
        idx, ident = i, candidato
        break
    if idx is None:
        return None

    partes = [p.strip() for p in ident.split('·')]
    # La cola "PLANTAS PB · 1 · 2" no identifica nada: la reparte la geometria.
    cabeza = []
    for p in partes:
        if re.match(r'^PLANTAS?\b', p, re.I):
            break
        cabeza.append(p)
    if len(cabeza) < 2:
        raise HojaIlegible(f'{aviso}identificacion incompleta: {ident!r}')

    fechas = [p for p in cabeza if FECHA.fullmatch(p)]
    # OJO: esta fecha es la de GENERACION de la hoja, no la de la revision.
    # La de Bolueta pone 25/07/2026 y el fichero es del 26. Se devuelve como
    # dato informativo; quien aplica la revision manda su fecha.
    fecha = fechas[0] if fechas else None
    etiquetas = [p for p in cabeza if p not in fechas]
    obra = etiquetas[0] if len(etiquetas) > 2 else None
    bloque, portal = etiquetas[-2], etiquetas[-1]

    # --- plantas: cada cabecera ocupa un rango x -------------------------
    plantas = []
    for bbox in filas[idx + 1][1]:
        t = texto(bbox)
        if t.upper().startswith('TAJO'):
            continue                     # abarca tambien la fila de viviendas
        forma = FORMA_PLANTA.search(t)
        declara = re.search(r'(\d+)\s*VIV', t, re.I)
        plantas.append({
            'nombre': forma.group(1) if forma else t,
            'declara': int(declara.group(1)) if declara else None,
            'x0': bbox[0], 'x1': bbox[2], 'vivs': [],
        })

    # --- viviendas: cada columna cae dentro del rango x de su planta ------
    columnas = []
    for bbox in filas[idx + 2][1]:
        t = texto(bbox)
        if not t or t.upper().startswith('TAJO'):
            continue
        centro = (bbox[0] + bbox[2]) / 2
        destino = next((p for p in plantas
                        if p['x0'] - 0.5 <= centro <= p['x1'] + 0.5), None)
        if destino is None:
            raise HojaIlegible(
                f'{aviso}la columna {t!r} no cae dentro de ninguna planta. '
                'Colocarla a ojo produciria un dato plausible en el sitio '
                'equivocado.')
        destino['vivs'].append(t)
        columnas.append({'planta': destino['nombre'], 'viv': t,
                         'x0': bbox[0], 'x1': bbox[2]})

    for p in plantas:
        if p['declara'] is not None and p['declara'] != len(p['vivs']):
            raise HojaIlegible(
                f'{aviso}la planta {p["nombre"]} declara {p["declara"]} '
                f'viviendas y la rejilla tiene {len(p["vivs"])}.')

    # --- tajos: una fila de grupo ocupa toda la anchura -------------------
    x_rejilla = filas[idx + 1][1][0][2]
    tajos, celdas = [], []
    for bbox, cs in filas[idx + 3:]:
        if len(cs) < 2:
            continue                     # cabecera de grupo, u "Obs:"
        crudo = texto((0, bbox[1], x_rejilla, bbox[3]))
        if not crudo or crudo.startswith('Obs'):
            continue
        nombre = DISTINTIVOS.sub('', crudo).strip()
        destino = indice_tajos.get(fold(nombre))
        if destino is None:
            raise HojaIlegible(
                f'{aviso}el tajo {nombre!r} no esta en el catalogo comun. '
                'Inventarle un id lo dejaria fuera de los calculos sin avisar.')
        tajos.append({'id': destino['id'], 'nombre': destino['nombre'],
                      'meta': destino, 'top': bbox[1], 'bottom': bbox[3]})
        for col in columnas:
            celdas.append({
                'bbox': (col['x0'], bbox[1], col['x1'], bbox[3]),
                'bloque': bloque, 'portal': portal,
                'planta': col['planta'], 'viv': col['viv'],
                'tajo': destino['id'], 'tajo_nombre': destino['nombre'],
            })

    return {
        'obra': obra, 'fecha': fecha, 'bloque': bloque, 'portal': portal,
        # Todas las etiquetas de la identificacion, sin interpretar. Quien
        # resuelve contra la ficha las necesita: el formato viejo llama
        # "bloque" a lo que la ficha llama portal (la hoja de Bolueta pone
        # "BOLUETA · PORTAL UNICO" y la ficha guarda bloque ZR1 / portal
        # BOLUETA). Adivinar la posicion pone las marcas en otro portal.
        'etiquetas': etiquetas,
        'plantas': [{'nombre': p['nombre'], 'vivs': p['vivs']} for p in plantas],
        'columnas': columnas, 'tajos': tajos, 'celdas': celdas,
        'x_rejilla': x_rejilla,
    }


# ------------------------------------------------------------ envoltura PDF

def _texto_de(page):
    def texto(bbox):
        x0, top, x1, bottom = bbox
        chars = [c for c in page.chars
                 if c['x0'] >= x0 - 0.5 and c['x1'] <= x1 + 0.5
                 and c['top'] >= top - 0.5 and c['bottom'] <= bottom + 0.5
                 # fuera del plano basico revientan la consola de Windows
                 and ord(c.get('text', 'x')) < 0x10000]
        chars.sort(key=lambda c: (round(c['top'], 1), c['x0']))
        return limpio(''.join(c['text'] for c in chars))
    return texto


def leer_pdf(ruta, indice_tajos=None):
    """[(n_pagina, tabla)] de las paginas que son tabla de revision."""
    import pdfplumber                      # solo hace falta en este camino

    indice_tajos = indice_tajos or tabla_de_tajos()
    paginas = []
    with pdfplumber.open(ruta) as pdf:
        for npag, page in enumerate(pdf.pages, 1):
            tablas = page.find_tables()
            if not tablas or len(tablas[0].cells) < CELDAS_MINIMAS:
                continue
            filas = [(f.bbox, [c for c in f.cells if c])
                     for f in tablas[0].rows if [c for c in f.cells if c]]
            tabla = leer_tabla(filas, _texto_de(page), indice_tajos,
                               aviso=f'pagina {npag}: ')
            if tabla:
                paginas.append((npag, tabla))
    if not paginas:
        raise HojaIlegible(
            f'{os.path.basename(ruta)} no tiene ninguna tabla de revision '
            'legible.')
    return paginas
