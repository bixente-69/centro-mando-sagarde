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

def leer_hoja(ruta):
    """Devuelve (obra, fecha, bloques, tajos_impresos, marcas)."""
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
    (nombre_obra, fecha, orden_bloques, bloques,
     orden_tajos, tajos, _marcas) = hoja

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
                plantas.append({
                    'id': _planta_id(planta['nombre']),
                    'nombre': planta['nombre'],
                    'orden': _orden_planta(planta['nombre']),
                    'ubicaciones': [
                        {'id': v, 'tipo': 'vivienda', 'habitaciones': None,
                         'origen': 'hoja de alta', 'confirmado': fecha}
                        for v in planta['vivs']
                    ],
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
    p.add_argument('--escribir', action='store_true')
    args = p.parse_args()

    hoja = leer_hoja(args.hoja)
    (nombre_obra, fecha, orden_bloques, bloques,
     orden_tajos, _tajos, marcas) = hoja

    print(f'HOJA: {os.path.basename(args.hoja)}')
    print(f'  obra: {nombre_obra}   fecha: {fecha}')
    if marcas:
        raise SystemExit(
            f'\nLa hoja lleva {marcas} marcas dentro de la rejilla. Esta '
            f'herramienta solo da de alta la distribucion desde una hoja en '
            f'blanco; leer marcas es trabajo del lector de revisiones.')
    print('  marcas dentro de la rejilla: 0 (hoja de distribucion)')

    ficha = construir_ficha(args.obra_id, args.carpeta, args.tipo_obra,
                            hoja, args.hoja)

    total = 0
    for bloque in ficha['estructura']['bloques']:
        for portal in bloque['portales']:
            print(f"  {bloque['nombre']} / {portal['nombre']}  ({portal['id']})")
            for planta in portal['plantas']:
                ids = ', '.join(u['id'] for u in planta['ubicaciones'])
                total += len(planta['ubicaciones'])
                print(f"      planta {planta['nombre']:<4} "
                      f"{len(planta['ubicaciones']):>2}  [{ids}]")
    print(f"  bloques: {len(ficha['estructura']['bloques'])}   "
          f"ubicaciones: {total}   tajos: {len(orden_tajos)}   "
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
