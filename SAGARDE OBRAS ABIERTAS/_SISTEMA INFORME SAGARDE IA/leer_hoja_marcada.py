# -*- coding: utf-8 -*-
"""LEER UNA HOJA MARCADA EN OBRA Y METERLA EN LA BASE  (paso 4 del ciclo)
=========================================================================

Cierra el paso que faltaba: la hoja sale de la base, se marca en obra, y lo
marcado vuelve a la base. Los pasos 1, 2, 3 y 5 ya funcionaban.

LA IDEA QUE LO HACE ABORDABLE
-----------------------------
Como la hoja la genera el sistema, ya sabemos que habia impreso en cada
celda. Solo hay que leer LA DIFERENCIA. No son 1.178 celdas: son las ~80 con
tinta encima. Y da gratis la barrera contra inventar datos: **sin tinta no
hay cambio**.

EL REPARTO, QUE ES LO IMPORTANTE
--------------------------------
El error caro de una lectura por vision no es confundir una `X` con una `M`:
es poner la marca en la FILA equivocada, porque produce un dato plausible en
el sitio equivocado y nadie se entera.

    lo hace el codigo                      lo hace la IA
    -----------------------------------    ---------------------------
    de que obra es la hoja                 que letra hay en el recorte
    que celda es cada posicion
    que habia impreso antes
    que ha cambiado
    que fecha lleva

Por eso son DOS PASOS y no uno:

    --preparar   localiza la tinta, le pone su clave por geometria y recorta
                 cada celda candidata a PNG. Escribe `<hoja>.candidatas.json`.
    --aplicar    toma la clasificacion, la contrasta con lo que habia, escribe
                 el sidecar `<hoja>.correcciones.json` y actualiza la ficha.

En medio, alguien (la IA, mirando los recortes) rellena el valor de cada
candidata. El codigo nunca decide que letra es.

QUE NO SE HACE EN SILENCIO
--------------------------
- Una celda con muy poca tinta no se descarta sola: sale como DUDOSA y la
  clasificacion tiene que resolverla, aunque sea marcandola `descartada`.
  El 05/08/2026 una `X` de "Tubeado vivienda" dejo 1 punto en la fila de
  abajo; contarlo habria inventado un tajo iniciado que nadie marco.
- Un valor que no baje de lo que ya habia se aplica igual: la norma de obra
  dice que una marca explicita vale a la primera, tambien si es un retroceso.
- La fecha no se deduce de la hoja: la manda quien ejecuta, porque la de la
  cabecera es la de GENERACION, no la de la revision.
- Se reporta el antes/despues de cada celda tocada.

USO
---
    python leer_hoja_marcada.py <hoja.pdf> <id_obra> --preparar
    python leer_hoja_marcada.py <hoja.pdf> <id_obra> --aplicar clasif.json \\
                                --fecha DD/MM/AAAA [--escribir]
"""
import argparse
import io
import json
import os
import sys
from collections import Counter, defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
OBRAS_DIR = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)

import ficha_obra as fichas          # noqa: E402
import rejilla_hoja as rejilla       # noqa: E402
from registro_obras import OBRAS     # noqa: E402

# Por debajo de esto la tinta de una celda no se da por marca: casi siempre es
# el rabo del trazo de la fila de al lado. No se descarta sola, se marca como
# dudosa para que alguien la mire.
PUNTOS_DUDOSA = 4

VALIDOS = {'X', 'M', '/', 'P'}
DESCARTADA = 'descartada'


class LecturaImposible(Exception):
    pass


# --------------------------------------------------------------- la tinta

def puntos_de(anot):
    """Puntos de un trazo, sea cual sea la forma en que llegue.

    Segun la version de PyMuPDF, `vertices` es una lista de trazos (cada uno
    lista de puntos) o una lista plana, y cada punto es fitz.Point o tupla.
    """
    import fitz

    crudos = []
    for trazo in (anot.vertices or []):
        if isinstance(trazo, (tuple, list)) and trazo and \
                isinstance(trazo[0], (tuple, list, fitz.Point)):
            crudos.extend(trazo)
        else:
            crudos.append(trazo)
    return [(p.x, p.y) if isinstance(p, fitz.Point) else (p[0], p[1])
            for p in crudos]


def tipo_de_trazo(anot):
    """'corrector' o 'marca'. Es la diferencia entre borrar y escribir.

    Medido el 05/08/2026 en las hojas reales de Bolueta y Mungia:

        negro  [0,0,0]  ancho 1.5-3      -> lo escrito a boli
        blanco [1,1,1]  ancho 17-28.5    -> corrector, tapa lo impreso

    El corrector NO es un error ni ruido: es la tecnica correcta de Bixente
    para decir "esta marca impresa ya no vale", y tiene sentido justamente
    porque quien lee es la vista. En Mungia aparece el patron completo: una
    pasada de corrector y encima un trazo negro con el estado nuevo.

    Tratarlos igual invierte el significado: una celda tapada se leeria como
    una celda marcada.
    """
    stroke = (anot.colors or {}).get('stroke') or []
    if len(stroke) >= 3 and min(stroke[:3]) >= 0.85:
        return 'corrector'
    return 'marca'


def repartir(puntos, celdas):
    """clave de celda -> nº de puntos que caen dentro. Y los que caen fuera.

    Un trazo es grueso y cruza varias celdas, asi que la anotacion dice DONDE
    mirar, no que celda es. Se decide por donde cae cada punto.
    """
    reparto = Counter()
    fuera = 0
    for px, py in puntos:
        for c in celdas:
            x0, t0, x1, t1 = c['bbox']
            if x0 <= px <= x1 and t0 <= py <= t1:
                reparto[(c['planta'], c['viv'], c['tajo'])] += 1
                break
        else:
            fuera += 1
    return reparto, fuera


# ------------------------------------------------------- claves de la ficha

def indice_de_ficha(ficha):
    """(portal_id, planta_nombre, etiqueta_vivienda) -> (planta_id, ubi_id).

    Dos motivos para no resolver por nombre exacto:

    - La hoja imprime la vivienda por su ALIAS, no por su id. En Mungia la
      ubicacion 'A' se imprime 'A2' (vivienda A de 2 habitaciones). Buscar
      por id no encuentra ninguna y la revision entera se pierde.
    - El portal no se resuelve aqui sino en `resolver_portal`, porque el
      formato viejo de hoja llama "bloque" a lo que la ficha llama portal.
    """
    alias = (ficha.get('estructura') or {}).get('alias_historico') or {}
    indice = {}
    for bloque in (ficha.get('estructura') or {}).get('bloques') or []:
        for portal in bloque.get('portales') or []:
            for planta in portal.get('plantas') or []:
                for ubi in planta.get('ubicaciones') or []:
                    destino = (planta['id'], ubi['id'])
                    etiqueta = alias.get(
                        f"{portal['id']}__{planta['id']}__{ubi['id']}")
                    for nombre in {ubi['id'], etiqueta} - {None}:
                        indice[(portal['id'], planta.get('nombre'),
                                str(nombre))] = destino
    return indice


def resolver_portal(ficha, etiquetas, aviso=''):
    """Que portal de la ficha es el que identifica esta tabla.

    La identificacion de la hoja no tiene un formato estable:

        OBRA PRUEBA · 05/08/2026 · BLOQUE 1 · PORTAL 1 · PLANTAS ...   (hoy)
        ZR1 · ZR1.2 · PLANTA PB                                        (Mungia)
        BOLUETA · PORTAL UNICO · PLANTAS PB · 1                        (Bolueta)

    En la de Bolueta, "BOLUETA" es lo que la ficha guarda como PORTAL y
    "PORTAL UNICO" es solo una etiqueta. Tomar la posicion como buena pondria
    las marcas en otro portal, que es el error caro de este proyecto.

    Por eso no se adivina: se busca que par (bloque, portal) de la ficha casa
    con las etiquetas. Si no hay exactamente uno, se para.
    """
    pares = []
    for bloque in (ficha.get('estructura') or {}).get('bloques') or []:
        for portal in bloque.get('portales') or []:
            pares.append((rejilla.fold(bloque.get('nombre')),
                          rejilla.fold(portal.get('nombre')),
                          portal['id'], bloque.get('nombre'),
                          portal.get('nombre')))
    vistas = {rejilla.fold(e) for e in etiquetas}

    # 1) casan bloque Y portal: es lo que hace falta cuando dos bloques
    #    repiten nombre de portal ("PORTAL 1" en BLOQUE 1 y en BLOQUE 2).
    exactos = [p for p in pares if p[0] in vistas and p[1] in vistas]
    if len(exactos) == 1:
        return exactos[0][2]
    # 2) casa solo el portal, y es unico en toda la obra.
    solo = [p for p in pares if p[1] in vistas]
    if len(solo) == 1:
        return solo[0][2]

    conocidos = ', '.join(f'{b} / {p}' for _fb, _fp, _id, b, p in pares)
    raise LecturaImposible(
        f'{aviso}la identificacion {etiquetas} no casa con un portal unico de '
        f'la ficha. La ficha tiene: {conocidos}. Antes que elegir uno se para: '
        f'una marca en el portal equivocado es un dato plausible en el sitio '
        f'equivocado.')


# ----------------------------------------------------------------- preparar

def preparar(ruta, obra, ficha, carpeta_recortes=None, zoom=6):
    import fitz

    doc = fitz.open(ruta)
    paginas = dict(rejilla.leer_pdf(ruta))
    indice = indice_de_ficha(ficha)

    if carpeta_recortes:
        os.makedirs(carpeta_recortes, exist_ok=True)

    candidatas, sin_tinta, fuera_total = [], 0, 0
    for npag, pagina in enumerate(doc, 1):
        anots = list(pagina.annots() or [])
        if not anots:
            continue
        tabla = paginas.get(npag)
        if tabla is None:
            raise LecturaImposible(
                f'pagina {npag}: hay {len(anots)} trazo(s) de tinta pero la '
                f'pagina no tiene rejilla legible. Antes que perder la marca, '
                f'se para.')
        celdas = {(c['planta'], c['viv'], c['tajo']): c for c in tabla['celdas']}
        portal_id = resolver_portal(ficha, tabla['etiquetas'],
                                    aviso=f'pagina {npag}: ')

        # Se acumula POR CELDA antes de decidir nada: una misma celda puede
        # llevar corrector y encima un trazo negro, que es como se anota un
        # cambio sobre una marca impresa.
        por_celda = defaultdict(lambda: {'marca': 0, 'corrector': 0})
        for anot in anots:
            puntos = puntos_de(anot)
            if not puntos:
                sin_tinta += 1
                continue
            tipo = tipo_de_trazo(anot)
            reparto, fuera = repartir(puntos, list(celdas.values()))
            fuera_total += fuera
            for destino, n_pts in reparto.items():
                por_celda[destino][tipo] += n_pts

        for (planta, viv, tajo), cuenta in por_celda.items():
            celda = celdas[(planta, viv, tajo)]
            clave_ficha = indice.get((portal_id, planta, viv))
            if clave_ficha is None:
                raise LecturaImposible(
                    f'pagina {npag}: la hoja marca planta {planta} / '
                    f'vivienda {viv} del portal {portal_id}, y la ficha '
                    f'no tiene esa ubicacion (ni por id ni por alias).')
            plid, uid = clave_ficha
            clave = f'{portal_id}__{plid}__{tajo}__{uid}'
            recorte = None
            if carpeta_recortes:
                x0, t0, x1, t1 = celda['bbox']
                pix = pagina.get_pixmap(
                    matrix=fitz.Matrix(zoom, zoom),
                    clip=fitz.Rect(x0 - 1, t0 - 1, x1 + 1, t1 + 1))
                recorte = f'{clave}.png'
                pix.save(os.path.join(carpeta_recortes, recorte))
            # Manda el trazo negro: si hay corrector Y marca, es que se tapo
            # lo viejo y se escribio lo nuevo encima.
            if cuenta['marca'] >= PUNTOS_DUDOSA:
                tipo = 'marca'
            elif cuenta['corrector'] >= PUNTOS_DUDOSA:
                tipo = 'corrector'
            else:
                tipo = 'dudosa'
            candidatas.append({
                'clave': clave,
                'pagina': npag,
                'bloque': tabla['bloque'], 'portal': tabla['portal'],
                'planta': planta, 'vivienda': viv,
                'tajo': tajo, 'tajo_nombre': celda['tajo_nombre'],
                'puntos': cuenta['marca'] + cuenta['corrector'],
                'puntos_marca': cuenta['marca'],
                'puntos_corrector': cuenta['corrector'],
                'tipo': tipo,
                'dudosa': tipo == 'dudosa',
                'antes': ((ficha.get('estados') or {})
                          .get(clave, {}) or {}).get('v'),
                'recorte': recorte,
                'valor': None,
            })

    # Todas las celdas que la hoja imprime, tengan tinta o no. Hacen falta
    # para el paso siguiente: si la hoja se ha llevado a obra, una casilla en
    # blanco NO es "sin mirar", es "ese tajo no ha empezado". Textual de
    # Bixente: "el no tener ninguna marca no significa que no se haya
    # revisado, es que ni siquiera existe". Una obra dura meses y muchos
    # tajos son casi del final.
    celdas_hoja = []
    sin_mapear = set()
    for npag, tabla in paginas.items():
        pid = resolver_portal(ficha, tabla['etiquetas'],
                              aviso=f'pagina {npag}: ')
        for c in tabla['celdas']:
            clave_ficha = indice.get((pid, c['planta'], c['viv']))
            if clave_ficha is None:
                # No se salta en silencio: una columna que la hoja imprime y
                # la ficha no reconoce es una ubicacion que se queda sin
                # medir, y el recuento saldria bien igualmente.
                sin_mapear.add((pid, c['planta'], c['viv']))
                continue
            plid, uid = clave_ficha
            celdas_hoja.append(f'{pid}__{plid}__{c["tajo"]}__{uid}')

    candidatas.sort(key=lambda c: (c['pagina'], c['clave']))
    return {
        'version': 1,
        'hoja': os.path.basename(ruta),
        'obra': obra['id'],
        'fecha_cabecera': next(iter(paginas.values()))['fecha'] if paginas else None,
        'puntos_fuera_de_la_rejilla': fuera_total,
        'trazos_sin_puntos': sin_tinta,
        'celdas_hoja': sorted(set(celdas_hoja)),
        'columnas_sin_mapear': sorted(f'{a} / planta {b} / {c}'
                                      for a, b, c in sin_mapear),
        'candidatas': candidatas,
    }


# ------------------------------------------------------------------ aplicar

def marcar_no_empezados(estados, celdas_hoja, marcadas, fecha, rev_id):
    """Las casillas en blanco de una hoja que SI se llevo a obra.

    Bixente, textual: *"el no tener ninguna marca no significa que no se haya
    revisado, es que ni siquiera existe [ese tajo todavia]"*. Una obra dura
    meses: empiezan unos tajos y otros se hacen encima de los ya hechos, casi
    al final. Por eso una casilla vacia de una hoja usada es un dato -- el
    tajo no ha empezado -- y tiene que contar en el denominador. Su estado es
    `P`, pendiente confirmado, que pesa 0.

    Solo asciende `?` -> `P`. **Nunca baja una X, una M ni una /**: esa es la
    otra mitad de la norma de obra, que la ausencia de marca no puede bajar
    un estado conocido. Sin esa guarda, una hoja donde Bixente solo anota los
    avances borraria todo lo anterior.
    """
    cambios = []
    for clave in celdas_hoja:
        if clave in marcadas or clave not in estados:
            continue
        antes = (estados[clave] or {}).get('v')
        if antes != '?':
            continue
        estados[clave] = {'v': 'P', 'f': fecha, 'r': rev_id,
                          'origen': 'hoja revisada sin marca'}
        cambios.append((clave, antes, 'P'))
    return cambios


def aplicar(ficha, candidatas, clasificacion, fecha, rev_id):
    """Devuelve (estados_nuevos, cambios, dudas). No toca la ficha."""
    por_clave = {c['clave']: c for c in candidatas}
    faltan = [k for k in por_clave if k not in clasificacion]
    if faltan:
        raise LecturaImposible(
            f'{len(faltan)} candidata(s) sin clasificar. Ninguna se descarta '
            f'sola: hay que darles valor o marcarlas "{DESCARTADA}". '
            f'Primeras: {", ".join(faltan[:5])}')
    sobran = [k for k in clasificacion if k not in por_clave]
    if sobran:
        raise LecturaImposible(
            f'{len(sobran)} celda(s) clasificadas que no tienen tinta en la '
            f'hoja. Sin tinta no hay cambio: {", ".join(sobran[:5])}')

    estados = dict(ficha.get('estados') or {})
    cambios, dudas = [], []
    for clave, valor in clasificacion.items():
        candidata = por_clave[clave]
        if valor == DESCARTADA:
            dudas.append({**candidata, 'motivo': 'descartada al clasificar'})
            continue
        if valor not in VALIDOS:
            raise LecturaImposible(
                f'{clave}: valor {valor!r} desconocido. Validos: '
                f'{sorted(VALIDOS)} o "{DESCARTADA}".')
        if clave not in estados:
            raise LecturaImposible(
                f'{clave}: la ficha no tiene esa celda.')
        antes = (estados[clave] or {}).get('v')
        if antes == valor:
            continue
        estados[clave] = {'v': valor, 'f': fecha, 'r': rev_id,
                          'origen': 'hoja marcada'}
        cambios.append((clave, antes, valor))
    return estados, cambios, dudas


# -------------------------------------------------------------------- salida

def _obra_de(obra_id):
    obra = next((o for o in OBRAS if o['id'] == obra_id), None)
    if obra is None:
        raise SystemExit(
            f'La obra {obra_id!r} no esta en registro_obras.py. '
            f'Conocidas: {", ".join(o["id"] for o in OBRAS)}')
    return obra


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                                  errors='replace')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('hoja')
    p.add_argument('obra_id')
    p.add_argument('--preparar', action='store_true')
    p.add_argument('--aplicar', metavar='CLASIFICACION.json')
    p.add_argument('--fecha', help='DD/MM/AAAA de la revision')
    p.add_argument('--sin-marca', choices=['pendiente', 'desconocido'],
                   default='pendiente',
                   help='que hacer con las casillas en blanco de la hoja. '
                        '"pendiente" (por defecto): la hoja se llevo a obra, '
                        'asi que en blanco significa que ese tajo no ha '
                        'empezado y cuenta en el porcentaje. "desconocido": '
                        'la hoja no cubrio esa parte y se dejan como estaban.')
    p.add_argument('--reemplazar', action='store_true',
                   help='sustituir un sidecar que ya exista para esa hoja')
    p.add_argument('--escribir', action='store_true')
    args = p.parse_args()

    obra = _obra_de(args.obra_id)
    carpeta = os.path.join(OBRAS_DIR, obra['carpeta_obra'])
    ficha = fichas.cargar(carpeta)
    if not ficha:
        raise SystemExit(
            f'{obra["nombre"]} no tiene ficha_obra.json. El lector exige base '
            f'previa: sin ella no se sabe que habia impreso en cada celda.')

    base = os.path.splitext(args.hoja)[0]
    ruta_candidatas = base + '.candidatas.json'

    if args.preparar:
        recortes = base + '.recortes'
        datos = preparar(args.hoja, obra, ficha, carpeta_recortes=recortes)
        with open(ruta_candidatas, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        cand = datos['candidatas']
        dudosas = [c for c in cand if c['dudosa']]
        por_tipo = Counter(c['tipo'] for c in cand)
        print(f'HOJA: {datos["hoja"]}   obra: {obra["nombre"]}')
        print(f'  celdas con tinta: {len(cand)}   '
              f'marcas: {por_tipo.get("marca", 0)}   '
              f'corrector: {por_tipo.get("corrector", 0)}   '
              f'dudosas (<{PUNTOS_DUDOSA} puntos): {len(dudosas)}')
        print(f'  puntos fuera de la rejilla: '
              f'{datos["puntos_fuera_de_la_rejilla"]}')
        por_portal = defaultdict(int)
        for c in cand:
            por_portal[f'{c["bloque"]} / {c["portal"]}'] += 1
        for k, n in sorted(por_portal.items()):
            print(f'    {k}: {n}')
        for col in datos.get('columnas_sin_mapear') or []:
            print(f'  [SIN MAPEAR] la hoja imprime {col} y la ficha no la '
                  f'reconoce: esa ubicacion se queda sin medir')
        for c in dudosas:
            print(f'  [DUDOSA] {c["clave"]} ({c["puntos"]} punto/s) '
                  f'-> {c["recorte"]}')
        print(f'  candidatas: {ruta_candidatas}')
        print(f'  recortes:   {recortes}')
        return

    if not args.aplicar:
        raise SystemExit('Elige --preparar o --aplicar.')
    if not args.fecha:
        raise SystemExit(
            'Falta --fecha. La fecha de la revision no se deduce de la hoja: '
            'la de la cabecera es la de generacion.')

    with open(ruta_candidatas, encoding='utf-8') as f:
        datos = json.load(f)
    with open(args.aplicar, encoding='utf-8') as f:
        clasificacion = json.load(f)
    clasificacion = clasificacion.get('celdas', clasificacion)

    rev_id = 'rev_' + args.fecha.replace('/', '')
    estados, cambios, dudas = aplicar(
        ficha, datos['candidatas'], clasificacion, args.fecha, rev_id)

    en_blanco = []
    if args.sin_marca == 'pendiente':
        # Una candidata DESCARTADA no lleva marca: su tinta era el rabo del
        # trazo de al lado. Asi que es una casilla en blanco como cualquier
        # otra y le toca el mismo trato, no quedarse en '?'.
        con_marca = {c['clave'] for c in datos['candidatas']
                     if clasificacion.get(c['clave']) != DESCARTADA}
        en_blanco = marcar_no_empezados(
            estados, datos.get('celdas_hoja') or [], con_marca,
            args.fecha, rev_id)
        cambios = cambios + en_blanco

    conteo = Counter(nuevo for _k, _a, nuevo in cambios)
    print(f'HOJA: {datos["hoja"]}   obra: {obra["nombre"]}   '
          f'fecha: {args.fecha}')
    print(f'  candidatas: {len(datos["candidatas"])}   '
          f'cambios: {len(cambios)}   descartadas: {len(dudas)}')
    print(f'  de ellos, casillas en blanco -> tajo no empezado: {len(en_blanco)}')
    print(f'  por valor: {dict(conteo)}')
    de_a = Counter((a, n) for _k, a, n in cambios)
    for (antes, nuevo), n in sorted(de_a.items(), key=lambda x: -x[1]):
        print(f'    {antes!r} -> {nuevo!r}: {n}')
    if not args.escribir:
        print('\n[SIMULACION] no se ha escrito nada.')
        return

    # Mismo nombre que usa el resto del sistema: "<hoja.pdf>.correcciones.json".
    # generar_todos elige el sidecar mas reciente por la FECHA del nombre, asi
    # que dos ficheros de la misma revision compiten y gana uno cualquiera.
    sidecar = args.hoja + '.correcciones.json'
    if os.path.isfile(sidecar) and not args.reemplazar:
        anterior = (json.load(open(sidecar, encoding='utf-8')).get('estados')
                    or {})
        raise SystemExit(
            f'\nYa existe {os.path.basename(sidecar)} con {len(anterior)} '
            f'celdas, probablemente transcritas a mano. No se pisa sin '
            f'decirlo: es la unica copia de ese trabajo. Compara primero y '
            f'usa --reemplazar si de verdad quieres sustituirlo.')
    with open(sidecar, 'w', encoding='utf-8') as f:
        json.dump({
            'version': 1, 'hoja': datos['hoja'], 'obra': obra['id'],
            'fecha': args.fecha, 'revision': rev_id,
            'origen': 'lectura de hoja marcada (paso 4)',
            'estados': {k: n for k, _a, n in cambios},
            'descartadas': [{'clave': d['clave'], 'puntos': d['puntos'],
                             'motivo': d['motivo']} for d in dudas],
        }, f, ensure_ascii=False, indent=2)

    ficha['estados'] = estados
    revisiones = [r for r in (ficha.get('revisiones') or [])
                  if r.get('id') != rev_id]
    # Lo que MIDIO la revision, no lo que cambio en esta pasada: si se vuelve
    # a aplicar la misma hoja no hay cambios y quedaria registrada como una
    # revision que no midio nada.
    medidas = sum(1 for k in (datos.get('celdas_hoja') or [])
                  if (estados.get(k) or {}).get('v') in VALIDOS)
    revisiones.append({'id': rev_id, 'fecha': args.fecha,
                       'origen': 'hoja marcada leida por la IA',
                       'celdas_medidas': medidas,
                       'celdas_cambiadas': len(cambios)})
    ficha['revisiones'] = revisiones
    fichas.guardar(carpeta, ficha)
    print(f'\n  sidecar: {sidecar}')
    print(f'  ficha actualizada: {fichas.ruta_ficha(carpeta)}')


if __name__ == '__main__':
    main()
