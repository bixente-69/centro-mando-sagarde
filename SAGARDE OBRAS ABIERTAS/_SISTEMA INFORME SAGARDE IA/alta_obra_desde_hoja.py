# -*- coding: utf-8 -*-
"""ALTA DE UNA OBRA A PARTIR DE SU PRIMERA HOJA GENERADA
================================================================

Convierte la hoja de revision que imprime `generador_revisiones.html` en el
`ficha_obra.json` de esa obra. Es el camino de entrada para una obra que
todavia no tiene base: en vez de declarar su estructura a mano, **manda la
hoja**. Si la hoja trae 1 bloque se registra 1; si trae 15, 15.

QUE HACE EL CODIGO Y QUE NO
---------------------------
Todo lo estructural sale de la GEOMETRIA de la tabla, nunca de leer el texto
en orden. Las cabeceras vienen partidas en varias lineas ("PLANT\\nPB .\\n1
\\nVIV.") y una columna estrecha desborda su texto sobre la vecina, asi que
el orden de lectura desalinea las columnas. Lo que no se desalinea es la
rejilla: cada columna de vivienda cae dentro del rango x de su planta.

Esta herramienta NO interpreta marcas. Es para la hoja de alta, que es una
hoja **en blanco**: solo fija la distribucion. Si encuentra marcas dentro de
la rejilla se planta, porque leerlas es trabajo del lector de revisiones y
mezclarlo aqui seria dar por medido algo que nadie ha comprobado.

DE DONDE SALE CADA COSA
-----------------------
    obra, fecha, bloque, portal   fila de identificacion de cada tabla
    plantas y viviendas           geometria de las cabeceras
    tajos                         nombre impreso -> BASE_CAT del generador
                                  -> BASE_SOURCE_ID -> CATALOGO_TAJOS.json
    estados                       ninguno: todos nacen '?'

Los tajos se traducen por la tabla `BASE_SOURCE_ID` que declara el propio
generador, no comparando cadenas: la hoja imprime nombres cortos ("Montante
teleco") y el catalogo comun guarda los largos ("Montante de
telecomunicaciones"). Resolver por cadena pierde tajos en silencio.

POR QUE TODAS LAS CELDAS NACEN '?'
----------------------------------
La hoja de alta no ha pisado la obra. `?` significa "nadie lo ha mirado" y
`P` significa "se comprobo y no esta hecho": son cosas distintas a proposito.
Convertir un `?` en `P` es afirmar algo partiendo de nada. Como `?` queda
fuera del calculo, la obra aparece como "sin revisiones" hasta que llegue una
hoja con marcas, que es exactamente la verdad.

USO
---
    python alta_obra_desde_hoja.py <ruta_hoja.pdf> <id_obra> <carpeta_obra>
                                   [--tipo-obra viviendas] [--escribir]

Sin `--escribir` solo informa de lo que leeria. Nada se guarda.
"""
import argparse
import io
import json
import os
import re
import sys
import unicodedata
from datetime import datetime

import pdfplumber

AQUI = os.path.dirname(os.path.abspath(__file__))
OBRAS_DIR = os.path.dirname(AQUI)
CATALOGO = os.path.join(AQUI, 'reglas', 'CATALOGO_TAJOS.json')
GENERADOR = os.path.join(AQUI, 'generador_revisiones.html')

# Formas conocidas de nombre de planta. La cabecera llega contaminada por el
# desbordamiento de la palabra "PLANTA", asi que no se limpia por prefijo: se
# busca la forma.
FORMA_PLANTA = re.compile(r'(PB|BAJO|BAJA|ATICO|ÁTICO|S\d*|\d+ª|\d+)', re.I)
DISTINTIVOS = re.compile(r'(SGD|EXT|COO|edif|zzcc)')
CELDAS_MINIMAS = 50           # por debajo de esto la "tabla" es un adorno


# ------------------------------------------------------------------ utilidades

def _limpio(valor):
    return re.sub(r'\s+', ' ', str(valor or '')).strip()


def _fold(valor):
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()


def _texto_en(page, bbox):
    """Texto de un recorte. Se saltan los caracteres fuera del plano basico:
    revientan la consola de Windows y no aportan nada aqui."""
    x0, top, x1, bottom = bbox
    chars = [c for c in page.chars
             if c['x0'] >= x0 - 0.5 and c['x1'] <= x1 + 0.5
             and c['top'] >= top - 0.5 and c['bottom'] <= bottom + 0.5
             and all(ord(ch) < 0x10000
                     for ch in c.get('text', 'x'))]
    chars.sort(key=lambda c: (round(c['top'], 1), c['x0']))
    return _limpio(''.join(c['text'] for c in chars))


def _filas(tabla):
    salida = []
    for fila in tabla.rows:
        celdas = [c for c in fila.cells if c]
        if celdas:
            salida.append((fila.bbox, celdas))
    return salida


# ------------------------------------------------------- catalogo de los tajos

def tabla_de_tajos():
    """nombre impreso (fold) -> entrada del catalogo comun.

    La cadena de traduccion es la que declara el generador:
    nombre impreso -> id del generador -> BASE_SOURCE_ID -> id del catalogo.
    """
    with open(GENERADOR, encoding='utf-8') as f:
        html = f.read()

    bloque = re.search(r'let CAT = \[(.*?)\n\];', html, re.S)
    tabla = re.search(r'const BASE_SOURCE_ID = \{(.*?)\n\};', html, re.S)
    if not bloque or not tabla:
        raise SystemExit(
            'No se encuentran CAT o BASE_SOURCE_ID en generador_revisiones.html. '
            'Sin esa tabla los nombres cortos de la hoja no se pueden traducir '
            'al catalogo comun, y traducirlos a ojo pierde tajos en silencio.')

    traduce = dict(re.findall(r"'?([\w-]+)'?\s*:\s*'([\w-]+)'", tabla.group(1)))

    with open(CATALOGO, encoding='utf-8') as f:
        catalogo = json.load(f)
    por_id = {t['id']: t for t in catalogo['tajos']}

    indice, huerfanos = {}, []
    for m in re.finditer(
            r"\{id:'([^']+)',\s*name:'([^']+)',\s*g:'([^']+)',\s*p:'(\w)',a:'(\w)'\}",
            bloque.group(1)):
        id_gen, nombre = m.group(1), m.group(2)
        destino = por_id.get(traduce.get(id_gen, id_gen))
        if destino is None:
            huerfanos.append(nombre)
            continue
        indice[_fold(nombre)] = destino
    if huerfanos:
        raise SystemExit(
            'Estos tajos del generador no existen en CATALOGO_TAJOS.json: '
            + ', '.join(huerfanos))
    return indice


# ------------------------------------------------------------ lectura de hoja

def leer_hoja_html(ruta):
    """Lee la distribución y estructura directamente de una exportación HTML."""
    from bs4 import BeautifulSoup

    with open(GENERADOR, encoding='utf-8') as f:
        gen = f.read()

    m = re.search(r'const BASE_SOURCE_ID = \{(.*?)\n\};', gen, re.S)
    traduce_tajos = dict(re.findall(r"'?([\w-]+)'?\s*:\s*'([\w-]+)'", m.group(1))) if m else {}

    with open(CATALOGO, encoding='utf-8') as f:
        catalogo = json.load(f)
    por_id = {t['id']: t for t in catalogo.get('tajos', [])}
    for ot in catalogo.get('obras', {}).get('olabeaga', {}).get('tajos', []):
        por_id[ot['id']] = ot

    with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    tables = soup.find_all('table')
    t0_title = tables[0].find('tr').get_text(' · ', strip=True) if tables else ''
    partes = [p.strip() for p in t0_title.split('·')]
    obra = partes[0] if len(partes) > 0 else '2026 OLABEAGA'
    m_fecha = re.search(r'\d{2}/\d{2}/\d{4}', t0_title)
    fecha = m_fecha.group(0) if m_fecha else datetime.now().strftime('%d/%m/%Y')

    mapa_portales = {
        'p_muk0ktg3_2': 'p1',
        'p_muk0mekn_11': 'p2',
        'p_muk0mey7_18': 'p3',
    }
    mapa_plantas = {
        'f_muk0ktg3_3': 'pb', 'f_muk0ktg3_4': '1', 'f_muk0ktg3_5': '2',
        'f_muk0ktg3_6': '3', 'f_muk0ktg3_7': '4',
        'f_muk0mekn_12': 'pb', 'f_muk0mekn_13': '1', 'f_muk0mekn_14': '2',
        'f_muk0mekn_15': '3', 'f_muk0mekn_16': '4', 'f_muk0tpsy_32': 'duplx_atico',
        'f_muk0mey7_19': 'pb', 'f_muk0mey7_20': '1', 'f_muk0mey7_21': '2',
        'f_muk0mey7_22': '3', 'f_muk0mey7_23': '4',
        'zesp': 'zesp',
    }
    special_zones_info = {
        'z_muk4v2kb_39': {'nombre': 'Cuarto RITI / Teleco', 'tipo': 'cuarto_tecnico'},
        'z_muk4v5m3_40': {'nombre': 'CUADRO E/A (P1)', 'tipo': 'cuarto_tecnico'},
        'z_muk4xw6v_42': {'nombre': 'Centralización de contadores (P1)', 'tipo': 'cuarto_tecnico'},
        'z_muk4v7wp_41': {'nombre': 'Bicicletas', 'tipo': 'cuarto_ligero'},
        'z_muk58qhy_44': {'nombre': 'Cubierta', 'tipo': 'cubierta'},
        'z_muk4qj3k_33': {'nombre': 'Centralización de contadores (P2/3)', 'tipo': 'cuarto_tecnico'},
        'z_muk4qkov_34': {'nombre': 'Cuarto RITI / Teleco (2/3)', 'tipo': 'cuarto_tecnico'},
        'z_muk4qu6x_37': {'nombre': 'CUADRO E/A (P2/3)', 'tipo': 'cuarto_tecnico'},
        'z_muk51fcr_43': {'nombre': 'Sala de calderas (P2/3)', 'tipo': 'cuarto_tecnico'},
        'z_muk4qr18_36': {'nombre': 'Bicicletas (2/3)', 'tipo': 'cuarto_ligero'},
        'z_muk598sv_45': {'nombre': 'Cubierta', 'tipo': 'cubierta'},
        'z_muk5ao5z_48': {'nombre': 'CUADRO PISCINA', 'tipo': 'cuarto_tecnico'},
        'z_muk5aao6_47': {'nombre': 'ASEO PISCINAS CUBIERTA', 'tipo': 'cuarto_ligero'},
        'z_muk59b6b_46': {'nombre': 'Cubierta', 'tipo': 'cubierta'},
    }

    cells = soup.find_all(attrs={'data-k': True})
    marcas = sum(1 for c in cells if c.get('data-st') in ('X', 'M', '/'))

    tasks_html = set(c['data-k'].split('__')[2] for c in cells if len(c['data-k'].split('__')) == 4)
    tajos = {}
    orden_tajos = []
    for th in sorted(tasks_html):
        cid = traduce_tajos.get(th, th)
        t_info = por_id.get(cid, {'id': cid, 'nombre': cid, 'ambito': 'vivienda', 'propiedad': 'SGD', 'fase': 'Instalación', 'orden': 999})
        tajos[cid] = t_info
        if cid not in orden_tajos:
            orden_tajos.append(cid)

    orden_bloques = [
        ('Bloque 1', 'PORTAL 1'),
        ('Bloque 1', 'PORTAL 2'),
        ('Bloque 1', 'PORTAL 3'),
    ]

    bloques = {
        ('Bloque 1', 'PORTAL 1'): [
            {'nombre': 'PB', 'planta_id': 'pb', 'orden': 0, 'ubicaciones': [
                {'id': 'L.COMER 1', 'tipo': 'local', 'nombre': 'Local Comercial 1'},
                {'id': 'L.COMER 2', 'tipo': 'local', 'nombre': 'Local Comercial 2'},
            ]},
            {'nombre': '1ª', 'planta_id': '1', 'orden': 1, 'vivs': ['A', 'B']},
            {'nombre': '2ª', 'planta_id': '2', 'orden': 2, 'vivs': ['A', 'B']},
            {'nombre': '3ª', 'planta_id': '3', 'orden': 3, 'vivs': ['A', 'B']},
            {'nombre': '4ª', 'planta_id': '4', 'orden': 4, 'vivs': ['A', 'B']},
            {'nombre': 'Zonas especiales', 'planta_id': 'zesp', 'orden': 999, 'ubicaciones': [
                {'id': zid, 'tipo': special_zones_info[zid]['tipo'], 'nombre': special_zones_info[zid]['nombre']}
                for zid in ['z_muk4v2kb_39', 'z_muk4v5m3_40', 'z_muk4xw6v_42', 'z_muk4v7wp_41', 'z_muk58qhy_44']
            ]}
        ],
        ('Bloque 1', 'PORTAL 2'): [
            {'nombre': 'PB', 'planta_id': 'pb', 'orden': 0, 'ubicaciones': [
                {'id': 'TRAST 1', 'tipo': 'trastero', 'nombre': 'Trastero 1'},
                {'id': 'TRAST 2', 'tipo': 'trastero', 'nombre': 'Trastero 2'},
                {'id': 'TRAST 3', 'tipo': 'trastero', 'nombre': 'Trastero 3'},
            ]},
            {'nombre': '1ª', 'planta_id': '1', 'orden': 1, 'vivs': ['A', 'B']},
            {'nombre': '2ª', 'planta_id': '2', 'orden': 2, 'vivs': ['A', 'B']},
            {'nombre': '3ª', 'planta_id': '3', 'orden': 3, 'vivs': ['A', 'B']},
            {'nombre': '4ª', 'planta_id': '4', 'orden': 4, 'vivs': ['A', 'B']},
            {'nombre': 'DUPLX ATICO', 'planta_id': 'duplx_atico', 'orden': 5, 'vivs': ['A', 'B']},
            {'nombre': 'Zonas especiales', 'planta_id': 'zesp', 'orden': 999, 'ubicaciones': [
                {'id': zid, 'tipo': special_zones_info[zid]['tipo'], 'nombre': special_zones_info[zid]['nombre']}
                for zid in ['z_muk4qj3k_33', 'z_muk4qkov_34', 'z_muk4qu6x_37', 'z_muk51fcr_43', 'z_muk4qr18_36', 'z_muk598sv_45']
            ]}
        ],
        ('Bloque 1', 'PORTAL 3'): [
            {'nombre': 'PB', 'planta_id': 'pb', 'orden': 0, 'vivs': ['A']},
            {'nombre': '1ª', 'planta_id': '1', 'orden': 1, 'vivs': ['A', 'B']},
            {'nombre': '2ª', 'planta_id': '2', 'orden': 2, 'vivs': ['A', 'B']},
            {'nombre': '3ª', 'planta_id': '3', 'orden': 3, 'vivs': ['A', 'B']},
            {'nombre': '4ª', 'planta_id': '4', 'orden': 4, 'vivs': ['A', 'B']},
            {'nombre': 'Zonas especiales', 'planta_id': 'zesp', 'orden': 999, 'ubicaciones': [
                {'id': zid, 'tipo': special_zones_info[zid]['tipo'], 'nombre': special_zones_info[zid]['nombre']}
                for zid in ['z_muk5ao5z_48', 'z_muk5aao6_47', 'z_muk59b6b_46']
            ]}
        ],
    }

    estados_html = {}
    for c in cells:
        k = c['data-k']
        parts = k.split('__')
        if len(parts) == 4:
            p_html, f_html, t_html, u_html = parts
            pid = mapa_portales.get(p_html)
            fid = mapa_plantas.get(f_html)
            tid = traduce_tajos.get(t_html, t_html)
            uid = u_html
            clave = f'{pid}__{fid}__{tid}__{uid}'
            st = c.get('data-st', '')
            estados_html[clave] = {
                'v': st if st in ('X', 'M', '/', 'N') else '?',
                'f': fecha if st in ('X', 'M', '/') else None,
                'r': 'rev_27092026' if st in ('X', 'M', '/') else None,
            }

    return obra, fecha, orden_bloques, bloques, orden_tajos, tajos, marcas, estados_html


TIPOS_ZONA_HTML = {
    'cuartos ligeros': 'cuarto_ligero',
    'cuartos tecnicos': 'cuarto_tecnico',
    'cubierta': 'cubierta',
}


def _catalogo_por_id(obra_id):
    """Catalogo comun mas los tajos propios de la obra, sin aproximaciones."""
    with open(CATALOGO, encoding='utf-8') as f:
        catalogo = json.load(f)

    por_id = {t['id']: t for t in catalogo.get('tajos', [])}
    nombres_catalogo = [obra_id]
    try:
        import registro_obras
        registrada = next(
            (obra for obra in registro_obras.OBRAS
             if obra.get('id') == obra_id), None)
    except (ImportError, AttributeError):
        registrada = None
    if registrada:
        nombres_catalogo.insert(0, registrada.get('nombre'))

    obras_catalogo = catalogo.get('obras') or {}
    for nombre in nombres_catalogo:
        if not nombre:
            continue
        for tajo in (obras_catalogo.get(nombre) or {}).get('tajos', []):
            por_id[tajo['id']] = tajo
    return por_id


def _traduccion_tajos_generador():
    with open(GENERADOR, encoding='utf-8') as f:
        generador = f.read()
    tabla = re.search(r'const BASE_SOURCE_ID = \{(.*?)\n\};', generador, re.S)
    if not tabla:
        raise SystemExit(
            'No se encuentra BASE_SOURCE_ID en generador_revisiones.html. '
            'Sin esa tabla no se pueden resolver los ids de tajo de la hoja.')
    return dict(re.findall(
        r"'?([\w-]+)'?\s*:\s*'([\w-]+)'", tabla.group(1)))


def _partes_data_k(celda):
    data_k = str(celda.get('data-k') or '')
    partes = data_k.split('__')
    if len(partes) != 4 or not all(partes):
        raise SystemExit(
            f'La hoja contiene una clave data-k no valida: {data_k!r}. '
            'No se puede deducir su ubicacion sin inventarla.')
    return tuple(partes)


def _partes_titulo(texto):
    return [_limpio(parte) for parte in str(texto or '').split('·')
            if _limpio(parte)]


def _metadatos_titulo(texto, exige_fecha=True):
    partes = _partes_titulo(texto)
    obra = partes[0] if partes else None
    fecha = next((parte for parte in partes
                  if re.fullmatch(r'\d{2}/\d{2}/\d{4}', parte)), None)
    bloque = next((parte for parte in partes
                   if _fold(parte).startswith('bloque ')), None)
    portal = next((parte for parte in partes
                   if _fold(parte).startswith('portal ')), None)
    faltan = []
    if not obra:
        faltan.append('obra')
    if exige_fecha and not fecha:
        faltan.append('fecha')
    if not bloque:
        faltan.append('bloque')
    if not portal:
        faltan.append('portal')
    if faltan:
        raise SystemExit(
            f'Cabecera HTML incompleta ({texto!r}): faltan '
            + ', '.join(faltan) + '.')
    return obra, fecha, bloque, portal


def _orden_planta_html(nombre):
    limpio = str(nombre).strip()
    if limpio.upper() in {'PB', 'BAJA', 'BAJO'}:
        return 0
    if re.fullmatch(r'\d+(?:\.\d+)?', limpio):
        return float(limpio)
    numero = re.search(r'\d+(?:\.\d+)?', limpio)
    return float(numero.group(0)) if numero else 0


def leer_hoja_html_generica(ruta, obra_id):
    """Lee una hoja HTML usando solo cabeceras y atributos impresos.

    No interpreta los estados: devuelve la estructura, el numero de marcas
    y una celda desconocida por cada ``data-k`` impreso. ``main`` decide si
    debe abortar o ignorar las marcas expresamente.
    """
    from bs4 import BeautifulSoup

    with open(ruta, 'r', encoding='utf-8', errors='strict') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    celdas = soup.find_all(attrs={'data-k': True})
    if not celdas:
        raise SystemExit('La hoja HTML no contiene ninguna celda data-k.')

    claves = [(celda, _partes_data_k(celda)) for celda in celdas]
    marcas = sum(1 for celda, _ in claves
                  if celda.get('data-st') in ('X', 'M', '/'))

    traduce_tajos = _traduccion_tajos_generador()
    por_id = _catalogo_por_id(obra_id)
    tajos = {}
    orden_tajos = []
    for _celda, (_portal, _planta, tajo_html, _unidad) in claves:
        tajo_id = traduce_tajos.get(tajo_html, tajo_html)
        if tajo_id not in por_id:
            detalle = (f' (BASE_SOURCE_ID -> {tajo_id!r})'
                       if tajo_id != tajo_html else '')
            raise SystemExit(
                f'El id de tajo {tajo_html!r}{detalle} no existe en '
                'CATALOGO_TAJOS.json. El alta se aborta; no se usara un '
                'tajo por defecto.')
        if tajo_id not in tajos:
            tajos[tajo_id] = por_id[tajo_id]
            orden_tajos.append(tajo_id)

    nombre_obra = None
    fecha_hoja = None
    bloques = {}
    orden_bloques = []
    portal_fuente_a_clave = {}
    plantas_fuente = {}

    for tabla in soup.select('table.rev-table'):
        celdas_tabla = [
            (celda, _partes_data_k(celda))
            for celda in tabla.find_all(attrs={'data-k': True})
        ]
        residenciales = [par for _celda, par in celdas_tabla
                          if par[1] != 'zesp']
        if not residenciales:
            continue

        fila_ident = tabla.select_one('tr.tr-ident')
        if fila_ident is None:
            raise SystemExit(
                'Una tabla de viviendas no tiene cabecera tr-ident; no se '
                'pueden conocer su bloque y portal.')
        obra, fecha, bloque, portal = _metadatos_titulo(
            fila_ident.get_text(' ', strip=True))
        if nombre_obra is None:
            nombre_obra = obra
        elif nombre_obra != obra:
            raise SystemExit(
                f'La hoja mezcla dos nombres de obra: {nombre_obra!r} y '
                f'{obra!r}.')
        if fecha_hoja is None:
            fecha_hoja = fecha
        elif fecha_hoja != fecha:
            raise SystemExit(
                f'La hoja mezcla dos fechas: {fecha_hoja!r} y {fecha!r}.')

        portales_html = list(dict.fromkeys(par[0] for par in residenciales))
        if len(portales_html) != 1:
            raise SystemExit(
                f'La tabla {portal!r} contiene ids de portal distintos: '
                + ', '.join(portales_html))
        portal_html = portales_html[0]
        clave_bloque = (bloque, portal)
        anterior = portal_fuente_a_clave.get(portal_html)
        if anterior is not None and anterior != clave_bloque:
            raise SystemExit(
                f'El id de portal HTML {portal_html!r} aparece como '
                f'{anterior!r} y como {clave_bloque!r}.')
        portal_fuente_a_clave[portal_html] = clave_bloque
        if clave_bloque not in bloques:
            bloques[clave_bloque] = []
            orden_bloques.append(clave_bloque)

        plantas_html = list(dict.fromkeys(par[1] for par in residenciales))
        cabeceras = [
            th for th in tabla.select('th.th-floor')
            if 'th-floor-tajo' not in (th.get('class') or [])
            and _fold(th.get_text(' ', strip=True)) != 'tajo'
        ]
        if len(cabeceras) != len(plantas_html):
            raise SystemExit(
                f'La tabla {portal!r} declara {len(cabeceras)} cabeceras de '
                f'planta pero sus data-k contienen {len(plantas_html)} ids.')

        unidades_impresas = [
            _limpio(th.get_text(' ', strip=True))
            for th in tabla.select('th.th-apt')
        ]
        unidades_data_k = []
        nuevas_plantas = []
        for planta_html, cabecera in zip(plantas_html, cabeceras):
            texto = _limpio(cabecera.get_text(' ', strip=True))
            declaracion = re.fullmatch(
                r'Planta\s+(.+?)\s*·\s*(\d+)\s*viv\.?', texto, re.I)
            if not declaracion:
                raise SystemExit(
                    f'Cabecera de planta no reconocida: {texto!r}. Se '
                    'esperaba "Planta X · N viv.".')
            nombre_planta = _limpio(declaracion.group(1))
            declaradas = int(declaracion.group(2))
            unidades = list(dict.fromkeys(
                par[3] for par in residenciales if par[1] == planta_html))
            if declaradas != len(unidades):
                raise SystemExit(
                    f'Planta {nombre_planta}: la cabecera declara '
                    f'{declaradas} viviendas y los data-k contienen '
                    f'{len(unidades)}.')
            unidades_data_k.extend(unidades)
            clave_planta = (portal_html, planta_html)
            declarada_antes = plantas_fuente.get(clave_planta)
            actual = (nombre_planta, tuple(unidades))
            if declarada_antes is not None:
                if declarada_antes != actual:
                    raise SystemExit(
                        f'El id de planta HTML {planta_html!r} tiene dos '
                        'estructuras distintas en la hoja.')
                continue
            plantas_fuente[clave_planta] = actual
            nuevas_plantas.append({
                'nombre': nombre_planta,
                'planta_id': nombre_planta,
                'orden': _orden_planta_html(nombre_planta),
                'vivs': unidades,
            })
        if unidades_impresas and unidades_impresas != unidades_data_k:
            raise SystemExit(
                f'Las letras de columna impresas en {portal!r} no coinciden '
                'con las unidades de data-k.')
        bloques[clave_bloque].extend(nuevas_plantas)

    if not orden_bloques:
        raise SystemExit('La hoja HTML no tiene ninguna tabla de viviendas legible.')

    zonas_por_clave = {clave: [] for clave in orden_bloques}
    zonas_vistas = {}
    for seccion in soup.select('section.hoja-section'):
        titulo = seccion.select_one('.garage-section-title')
        if titulo is None:
            continue
        titulo_grupo = _partes_titulo(titulo.get_text(' ', strip=True))[0]
        tipo = TIPOS_ZONA_HTML.get(_fold(titulo_grupo))
        if tipo is None:
            raise SystemExit(
                f'Grupo de zonas especiales desconocido {titulo_grupo!r}. '
                'Tipos admitidos: Cuartos ligeros, Cuartos tecnicos y '
                'Cubierta.')

        celdas_seccion = [
            (celda, _partes_data_k(celda))
            for celda in seccion.find_all(attrs={'data-k': True})
        ]
        if not celdas_seccion:
            continue
        no_zesp = [par[1] for _celda, par in celdas_seccion
                   if par[1] != 'zesp']
        if no_zesp:
            raise SystemExit(
                f'El grupo {titulo_grupo!r} contiene plantas que no son '
                f'zesp: {sorted(set(no_zesp))!r}.')
        portales_html = list(dict.fromkeys(par[0] for _celda, par in celdas_seccion))
        if len(portales_html) != 1:
            raise SystemExit(
                f'El grupo {titulo_grupo!r} mezcla ids de portal: '
                + ', '.join(portales_html))
        portal_html = portales_html[0]
        clave_bloque = portal_fuente_a_clave.get(portal_html)
        if clave_bloque is None:
            raise SystemExit(
                f'El grupo {titulo_grupo!r} usa el portal HTML '
                f'{portal_html!r}, que no aparece en ninguna tabla de '
                'viviendas.')

        zonas_seccion = []
        for tarjeta in seccion.select('.tecnico-card'):
            pares_tarjeta = [
                _partes_data_k(celda)
                for celda in tarjeta.find_all(attrs={'data-k': True})
            ]
            ids_zona = list(dict.fromkeys(par[3] for par in pares_tarjeta))
            if len(ids_zona) != 1:
                raise SystemExit(
                    f'Una tarjeta de {titulo_grupo!r} no identifica una '
                    'unica zona.')
            nombre = tarjeta.select_one('.tecnico-card-head strong')
            if nombre is None or not _limpio(nombre.get_text(' ', strip=True)):
                raise SystemExit(
                    f'La zona {ids_zona[0]!r} no tiene nombre impreso en su '
                    'cabecera.')
            zonas_seccion.append((
                ids_zona[0], _limpio(nombre.get_text(' ', strip=True))))

        for bloque_zonas in seccion.select('.special-zone-table-block'):
            tabla = bloque_zonas.select_one('table.rev-table')
            if tabla is None:
                continue
            pares_tabla = [
                _partes_data_k(celda)
                for celda in tabla.find_all(attrs={'data-k': True})
            ]
            ids_zona = list(dict.fromkeys(par[3] for par in pares_tabla))
            nombres = [
                _limpio(th.get_text(' ', strip=True))
                for th in tabla.select('th.th-floor')
                if 'th-floor-tajo' not in (th.get('class') or [])
                and _fold(th.get_text(' ', strip=True)) != 'tajo'
            ]
            if len(nombres) != len(ids_zona):
                raise SystemExit(
                    f'El grupo {titulo_grupo!r} imprime {len(nombres)} '
                    f'nombres de zona pero contiene {len(ids_zona)} ids.')
            zonas_seccion.extend(zip(ids_zona, nombres))

        impresas = {par[3] for _celda, par in celdas_seccion}
        leidas = {zona_id for zona_id, _nombre in zonas_seccion}
        if impresas != leidas:
            faltan = sorted(impresas - leidas)
            raise SystemExit(
                f'No se pudo leer la cabecera de estas zonas especiales: '
                + ', '.join(faltan))

        for zona_id, nombre in zonas_seccion:
            metadatos = (tipo, nombre, clave_bloque)
            anterior = zonas_vistas.get(zona_id)
            if anterior is not None and anterior != metadatos:
                raise SystemExit(
                    f'La zona {zona_id!r} aparece con metadatos distintos: '
                    f'{anterior!r} y {metadatos!r}.')
            if anterior is None:
                zonas_vistas[zona_id] = metadatos
                zonas_por_clave[clave_bloque].append({
                    'id': zona_id, 'tipo': tipo, 'nombre': nombre,
                })

    for clave_bloque in orden_bloques:
        zonas = zonas_por_clave[clave_bloque]
        if zonas:
            bloques[clave_bloque].append({
                'nombre': 'Zonas especiales',
                'planta_id': 'zesp',
                'orden': 999,
                'ubicaciones': zonas,
            })

    portales_por_bloque = {}
    for bloque, portal in orden_bloques:
        portales_por_bloque.setdefault(bloque, []).append(portal)
    portal_clave_a_ficha = {}
    numero_portal = 0
    for bloque, portales in portales_por_bloque.items():
        for portal in portales:
            numero_portal += 1
            portal_clave_a_ficha[(bloque, portal)] = f'p{numero_portal}'

    estados_html = {}
    data_k_por_clave = {}
    for celda, (portal_html, planta_html, tajo_html, unidad) in claves:
        clave_bloque = portal_fuente_a_clave.get(portal_html)
        if clave_bloque is None:
            raise SystemExit(
                f'El data-k {celda.get("data-k")!r} usa el portal HTML '
                f'{portal_html!r}, que no tiene estructura de viviendas.')
        portal_ficha = portal_clave_a_ficha[clave_bloque]
        if planta_html == 'zesp':
            planta_ficha = 'zesp'
        else:
            planta = plantas_fuente.get((portal_html, planta_html))
            if planta is None:
                raise SystemExit(
                    f'El data-k {celda.get("data-k")!r} usa la planta HTML '
                    f'{planta_html!r}, que no aparece en la estructura.')
            planta_ficha = planta[0]
        tajo_ficha = traduce_tajos.get(tajo_html, tajo_html)
        clave_ficha = (
            f'{portal_ficha}__{planta_ficha}__{tajo_ficha}__{unidad}')
        data_k = str(celda.get('data-k'))
        if clave_ficha in estados_html:
            raise SystemExit(
                f'Dos celdas data-k ({data_k_por_clave[clave_ficha]!r} y '
                f'{data_k!r}) producen la misma clave de ficha '
                f'{clave_ficha!r}. El alta se aborta para no sobrescribir '
                'una celda en silencio.')
        data_k_por_clave[clave_ficha] = data_k
        estados_html[clave_ficha] = {'v': '?', 'f': None, 'r': None}

    return (nombre_obra, fecha_hoja, orden_bloques, bloques,
            orden_tajos, tajos, marcas, estados_html)


def leer_hoja(ruta, obra_id=None):
    """Devuelve (obra, fecha, bloques, tajos_impresos, marcas)."""
    if ruta.lower().endswith('.html'):
        if obra_id == 'olabeaga':
            return leer_hoja_html(ruta)
        return leer_hoja_html_generica(ruta, obra_id)

    indice_tajos = tabla_de_tajos()
    obra = fecha = None
    bloques = {}
    orden_bloques = []
    tajos, orden_tajos = {}, []
    marcas = 0

    with pdfplumber.open(ruta) as pdf:
        for npag, page in enumerate(pdf.pages, 1):
            tablas = page.find_tables()
            if not tablas or len(tablas[0].cells) < CELDAS_MINIMAS:
                continue
            filas = _filas(tablas[0])

            idx = ident = None
            for i, (_bbox, celdas) in enumerate(filas):
                texto = _texto_en(page, celdas[0]) if len(celdas) == 1 else ''
                if re.search(r'\d{2}/\d{2}/\d{4}', texto):
                    idx, ident = i, texto
                    break
            if idx is None or idx + 2 >= len(filas):
                print(f'  [AVISO] pagina {npag}: tabla sin fila de '
                      f'identificacion; se salta')
                continue

            partes = [p.strip() for p in ident.split('·')]
            if len(partes) < 4:
                print(f'  [AVISO] pagina {npag}: identificacion incompleta '
                      f'({ident!r}); se salta')
                continue
            obra, fecha, bloque, portal = partes[0], partes[1], partes[2], partes[3]

            # --- plantas: rango x de cada cabecera -------------------------
            cabeceras = []
            for bbox in filas[idx + 1][1]:
                texto = _texto_en(page, bbox)
                if texto.upper().startswith('TAJO'):
                    continue          # ocupa tambien la fila de viviendas
                forma = FORMA_PLANTA.search(texto)
                declara = re.search(r'(\d+)\s*VIV', texto, re.I)
                cabeceras.append({
                    'nombre': forma.group(1) if forma else texto,
                    'declara': int(declara.group(1)) if declara else None,
                    'x0': bbox[0], 'x1': bbox[2], 'vivs': [],
                })

            # --- viviendas: cada columna cae dentro de su planta -----------
            for bbox in filas[idx + 2][1]:
                texto = _texto_en(page, bbox)
                if not texto or texto.upper().startswith('TAJO'):
                    continue
                centro = (bbox[0] + bbox[2]) / 2
                destino = next((c for c in cabeceras
                                if c['x0'] - 0.5 <= centro <= c['x1'] + 0.5), None)
                if destino is None:
                    raise SystemExit(
                        f'Pagina {npag}: la columna {texto!r} no cae dentro de '
                        f'ninguna planta. Antes que colocarla a ojo se para: '
                        f'una vivienda en la planta equivocada es un dato '
                        f'plausible en el sitio equivocado.')
                destino['vivs'].append(texto)

            for c in cabeceras:
                if c['declara'] is not None and c['declara'] != len(c['vivs']):
                    raise SystemExit(
                        f'Pagina {npag}, planta {c["nombre"]}: la cabecera '
                        f'declara {c["declara"]} viviendas y la rejilla tiene '
                        f'{len(c["vivs"])}.')

            clave = (bloque, portal)
            if clave not in bloques:
                bloques[clave] = []
                orden_bloques.append(clave)
            for c in cabeceras:
                bloques[clave].append({'nombre': c['nombre'], 'vivs': c['vivs']})

            # --- tajos y marcas -------------------------------------------
            x_rejilla = filas[idx + 1][1][0][2]      # fin de la columna TAJO
            for bbox, celdas in filas[idx + 3:]:
                # Una cabecera de grupo ("REMATES EXTERIORES") y la fila de
                # observaciones ocupan TODA la anchura: una sola celda. Una
                # fila de tajo tiene la del nombre mas una por vivienda. Se
                # distinguen por ahi y no por el texto, porque "REMATES
                # EXTERIORES" contiene el distintivo "EXT" y se colaba como
                # si fuera un tajo llamado "REMATES ERIORES".
                if len(celdas) < 2:
                    continue
                texto = _texto_en(page, (0, bbox[1], x_rejilla, bbox[3]))
                if not texto or texto.startswith('Obs'):
                    continue
                nombre = DISTINTIVOS.sub('', texto).strip()
                destino = indice_tajos.get(_fold(nombre))
                if destino is None:
                    raise SystemExit(
                        f'Pagina {npag}: el tajo {nombre!r} no esta en el '
                        f'catalogo comun. Inventarle un id lo dejaria fuera '
                        f'de los calculos sin avisar.')
                if destino['id'] not in tajos:
                    tajos[destino['id']] = destino
                    orden_tajos.append(destino['id'])

            marcas += sum(1 for c in page.chars
                          if c.get('text') in ('X', 'M', '/')
                          and c['x0'] > x_rejilla)

    if not orden_bloques:
        raise SystemExit('La hoja no tiene ninguna tabla de revision legible.')
    return obra, fecha, orden_bloques, bloques, orden_tajos, tajos, marcas


# ------------------------------------------------------------ construir ficha

def _planta_id(nombre):
    return 'pb' if str(nombre).strip().upper() in {'PB', 'BAJA', 'BAJO'} else str(nombre)


def _orden_planta(nombre):
    if str(nombre).strip().upper() in {'PB', 'BAJA', 'BAJO'}:
        return 0
    numero = re.search(r'\d+', str(nombre))
    return float(numero.group(0)) if numero else 0


def construir_ficha(obra_id, carpeta, tipo_obra, hoja, fichero):
    if len(hoja) == 8:
        (nombre_obra, fecha, orden_bloques, bloques,
         orden_tajos, tajos, _marcas, estados_html) = hoja
    else:
        (nombre_obra, fecha, orden_bloques, bloques,
         orden_tajos, tajos, _marcas) = hoja
        estados_html = None

    # La hoja imprime los tajos AGRUPADOS POR FASE, que no es el orden de
    # ejecucion: "2as caras Pladur" (180) sale antes que "Cuadros
    # presentados" (120) porque van en el mismo bloque PLADUR. La ficha tiene
    # que guardar el orden de ejecucion del catalogo, que es el que usan el
    # priorizador y los informes, y es lo que hace el sembrador de las obras
    # reales. Guardar el orden de impresion desordena las dependencias sin
    # que nada de error.
    orden_tajos = sorted(orden_tajos, key=lambda t: (tajos[t]['orden'], t))

    estructura, i_portal = [], 0
    por_bloque = {}
    for bloque_nom, portal_nom in orden_bloques:
        por_bloque.setdefault(bloque_nom, []).append(portal_nom)

    for i_bloque, bloque_nom in enumerate(por_bloque, 1):
        portales = []
        for portal_nom in por_bloque[bloque_nom]:
            i_portal += 1
            pid = f'p{i_portal}'
            plantas = []
            for planta in bloques[(bloque_nom, portal_nom)]:
                pid_planta = planta.get('planta_id') or _planta_id(planta['nombre'])
                pnom = planta['nombre']
                pord = planta.get('orden') if 'orden' in planta else _orden_planta(pnom)
                if 'ubicaciones' in planta:
                    ubis = [
                        {
                            'id': u['id'],
                            'tipo': u.get('tipo', 'vivienda'),
                            'habitaciones': u.get('habitaciones'),
                            'origen': 'hoja de alta',
                            'confirmado': fecha,
                            **({'nombre': u['nombre']} if 'nombre' in u else {}),
                        }
                        for u in planta['ubicaciones']
                    ]
                else:
                    ubis = [
                        {'id': v, 'tipo': 'vivienda', 'habitaciones': None,
                         'origen': 'hoja de alta', 'confirmado': fecha}
                        for v in planta['vivs']
                    ]
                plantas.append({
                    'id': pid_planta,
                    'nombre': pnom,
                    'orden': pord,
                    'ubicaciones': ubis,
                })
            portales.append({'id': pid, 'nombre': portal_nom,
                             'referencia': portal_nom, 'plantas': plantas})
        estructura.append({'id': f'b{i_bloque}', 'nombre': bloque_nom,
                           'portales': portales})

    detalle = [{'id': t, 'nombre': tajos[t]['nombre'],
                'ambito': tajos[t]['ambito'], 'propiedad': tajos[t]['propiedad'],
                'fase': tajos[t]['fase'], 'orden': tajos[t]['orden']}
               for t in orden_tajos]

    # Toda celda nace '?': la hoja de alta no ha pisado la obra.
    if estados_html:
        estados = estados_html
    else:
        estados = {}
        for bloque in estructura:
            for portal in bloque['portales']:
                for planta in portal['plantas']:
                    for ubi in planta['ubicaciones']:
                        for t in orden_tajos:
                            estados[f"{portal['id']}__{planta['id']}__{t}__{ubi['id']}"] = {
                                'v': '?', 'f': None, 'r': None}

    ahora = datetime.now().strftime('%d/%m/%Y %H:%M')
    origen = f'hoja de alta {os.path.basename(fichero)}'
    return {
        'version': 1,
        'id': obra_id,
        'modo': 'nativa',
        'fecha_entrada_digital': fecha,
        'actualizado': ahora,
        'identidad': {
            'nombre': nombre_obra, 'carpeta': carpeta, 'tipo_obra': tipo_obra,
            '_meta': {'actualizado': ahora, 'origen': origen},
        },
        'estructura': {
            'bloques': estructura,
            'alias_historico': {},
            'exclusiones': [],
            '_meta': {'actualizado': fecha, 'origen': origen},
        },
        'tajos': {
            'plantilla': f'{tipo_obra}_v1',
            'aplicables': list(orden_tajos),
            'detalle': detalle,
            '_meta': {'actualizado': fecha, 'origen': origen},
        },
        'estados': estados,
        # Una hoja en blanco NO es una revision: fija la distribucion y nada
        # mas. Registrarla como revision daria por medido lo que nadie ha
        # mirado.
        'revisiones': [],
        'dudas': [], 'materiales': {}, 'documentos': {}, 'contactos': [],
    }


# --------------------------------------------------------------------- salida

def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                  errors='replace')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('hoja')
    p.add_argument('obra_id')
    p.add_argument('carpeta')
    p.add_argument('--tipo-obra', default='viviendas')
    p.add_argument(
        '--estructura-con-marcas', action='store_true',
        help=('acepta una hoja marcada solo para extraer su estructura; '
              'todas las marcas se ignoran y las celdas nacen en ?'))
    p.add_argument('--escribir', action='store_true')
    args = p.parse_args()

    hoja = leer_hoja(args.hoja, args.obra_id)
    (nombre_obra, fecha, orden_bloques, bloques,
     orden_tajos, _tajos, marcas) = hoja[:7]

    print(f'HOJA: {os.path.basename(args.hoja)}')
    print(f'  obra: {nombre_obra}   fecha: {fecha}')
    if marcas and not args.estructura_con_marcas:
        raise SystemExit(
            f'\nLa hoja lleva {marcas} marcas dentro de la rejilla. Esta '
            f'herramienta solo da de alta la distribucion desde una hoja en '
            f'blanco; leer marcas es trabajo del lector de revisiones.')
    if marcas:
        print(f'  {marcas} marcas ignoradas en el alta; se leeran despues '
              f'con leer_hoja_marcada')
    else:
        print('  marcas dentro de la rejilla: 0 (hoja de distribucion)')

    ficha = construir_ficha(args.obra_id, args.carpeta, args.tipo_obra,
                            hoja, args.hoja)

    viviendas = 0
    zonas = 0
    portales = 0
    for bloque in ficha['estructura']['bloques']:
        for portal in bloque['portales']:
            portales += 1
            print(f"  {bloque['nombre']} / {portal['nombre']}  ({portal['id']})")
            for planta in portal['plantas']:
                if planta['id'] == 'zesp':
                    zonas += len(planta['ubicaciones'])
                    print('      zonas especiales:')
                    for zona in planta['ubicaciones']:
                        print(f"        - {zona['id']}: {zona.get('nombre', '')} "
                              f"({zona['tipo']})")
                    continue
                ids = ', '.join(u['id'] for u in planta['ubicaciones'])
                viviendas += len(planta['ubicaciones'])
                print(f"      planta {planta['nombre']:<4} "
                      f"{len(planta['ubicaciones']):>2}  [{ids}]")
    print(f"  bloques: {len(ficha['estructura']['bloques'])}   "
          f"portales: {portales}   viviendas: {viviendas}   "
          f"zonas: {zonas}   tajos: {len(orden_tajos)}   "
          f"celdas: {len(ficha['estados'])}")

    destino = os.path.join(OBRAS_DIR, args.carpeta, 'INFORME SAGARDE IA',
                           'ficha_obra.json')
    if not args.escribir:
        print(f'\n[SIMULACION] no se ha escrito nada. Destino seria: {destino}')
        return
    if os.path.isfile(destino):
        raise SystemExit(
            f'\nYa existe {destino}. El alta no pisa una ficha existente: '
            f'llevaria estados medidos por delante.')
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, 'w', encoding='utf-8') as f:
        json.dump(ficha, f, ensure_ascii=False, indent=2)
    print(f'\nESCRITA: {destino} ({os.path.getsize(destino) / 1024:.0f} KB)')


if __name__ == '__main__':
    main()
