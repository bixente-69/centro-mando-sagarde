# -*- coding: utf-8 -*-
"""
SEMBRADOR DE FICHA DE OBRA v2 — con confirmaciones del usuario
----------------------------------------------------------------
Cambios respecto a v1:
  1. El identificador de vivienda es la LETRA. El numero pegado (A2) es el
     numero de habitaciones y pasa a ser un atributo, no parte del id.
  2. La estructura definitiva sale de confirmaciones_{obra}.json (validado por
     el usuario), no de lo que se observo en las hojas.
  3. Las ubicaciones confirmadas que nunca tuvieron datos nacen con estado '?'
     (desconocido) en todos sus tajos: existen, pero nadie las ha comprobado.
  4. El tipo de ubicacion se declara, no se deduce del ambito del tajo.
"""
import glob
import importlib.util
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = r'D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE'
OBRAS_DIR = os.path.join(RAIZ, 'SAGARDE OBRAS ABIERTAS')
SISTEMA = os.path.join(OBRAS_DIR, '_SISTEMA INFORME SAGARDE IA')

MAPA_ESTADO = {'X': 'X', 'M': 'M', '/': '/', 'Pendiente': 'P', '': 'P'}


def clave_planta(nombre):
    t = str(nombre or '').strip().upper()
    if t in {'PB', 'B', 'BAJA', 'BAJO'}:
        return (0, 0)
    try:
        return (1, float(t))
    except ValueError:
        return (2, 0)


def partir_unidad(bruto, separar):
    """'A2' -> ('A', 2) si separar; ('A2', None) si no."""
    if not separar:
        return bruto, None
    m = re.fullmatch(r'([A-Za-z]+)\s*(\d+)', str(bruto).strip())
    if m:
        return m.group(1).upper(), int(m.group(2))
    return str(bruto).strip(), None


def cargar(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _norm_alias(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def _mapa_tajos_cortos(obra_id):
    """Codigo corto del adaptador ('cuad-mec') -> id del catalogo
    ('cuadro_mecanizado'). Las correcciones manuales usan el corto y la ficha
    el largo; sin esta traduccion no se pueden cruzar."""
    ruta = os.path.join(SISTEMA, 'adaptadores', f'adaptador_{obra_id}.py')
    if not os.path.isfile(ruta):
        return {}
    spec = importlib.util.spec_from_file_location(f'_ad_{obra_id}', ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, SISTEMA)
    spec.loader.exec_module(mod)
    catalogo = cargar(os.path.join(SISTEMA, 'reglas', 'CATALOGO_TAJOS.json'))
    alias2id = {}
    for t in catalogo['tajos']:
        alias2id[_norm_alias(t['nombre'])] = t['id']
        for a in t.get('aliases', []):
            alias2id[_norm_alias(a)] = t['id']
    corto2nombre = getattr(mod, 'TAJO_NOMBRE_CATALOGO', None) or \
        getattr(mod, 'TAJO_NOMBRE', {})
    return {c: alias2id[_norm_alias(n)] for c, n in corto2nombre.items()
            if _norm_alias(n) in alias2id}


def resolver_tajo(extra_alias=None):
    """Devuelve una funcion nombre -> (id, es_propio_de_la_obra).

    Lo que no esta en el catalogo comun no se descarta: se le da un id propio.
    Obispo Orueta usa vocabulario suyo (Ventilacion, Techos WC, Cableado
    Extractor...) que son 2227 celdas medidas; ignorarlas por no estar en el
    catalogo seria perder trabajo real.
    """
    catalogo = cargar(os.path.join(SISTEMA, 'reglas', 'CATALOGO_TAJOS.json'))
    alias2id = {}
    for t in catalogo['tajos']:
        alias2id[_norm_alias(t['nombre'])] = t['id']
        for a in t.get('aliases', []):
            alias2id[_norm_alias(a)] = t['id']
    for nombre, tid in (extra_alias or {}).items():
        alias2id[_norm_alias(nombre)] = tid

    def resolver(nombre):
        clave = _norm_alias(nombre)
        if clave in alias2id:
            return alias2id[clave], False
        return re.sub(r'\s+', '_', clave), True

    return resolver


def estados_desde_historial(hist, resolver):
    """Ultimo estado MEDIDO de cada celda, recorriendo las revisiones en orden.

    Esta es la fuente correcta: lo medido. prioridades_trabajos.json es una
    fuente DERIVADA y con una revision parcial arrastra 'terminado' sobre
    celdas que nadie ha mirado.

    Una casilla en blanco NO pisa lo anterior: en blanco significa 'no se
    leyo', no 'se comprobo y no esta'. Confundir esas dos cosas es la
    diferencia entre ? y P, y es lo que mas dano ha hecho en este proyecto.
    """
    ultimo = {}
    for fecha, snap in hist:
        for reg in snap or []:
            estado = str(reg.get('status') or '').strip()
            if not estado:
                continue
            tid, _propio = resolver(reg.get('task'))
            ultimo[(reg.get('floor'), reg.get('unit'), tid)] = (estado, fecha)
    return ultimo


def marcar_no_aplica(estados, hist, resolver, mapa_ids, a_letra):
    """Pone 'N' donde la hoja nunca ha impreso esa fila para esa ubicacion.

    La hoja imprime la fila de un tajo tenga marca o no, asi que 'nunca
    impresa en 13 revisiones' significa que ese tajo NO aplica ahi, no que
    nadie lo haya mirado. En Obispo Orueta un montante lleva un solo tajo y
    unas zonas comunes cinco, frente a los 38 de la obra.

    Importa para la hoja que genera la app: sin esto imprimiria 38 filas por
    montante. No cambia el porcentaje (ni 'N' ni '?' cuentan) pero si lo que
    Bixente se lleva a obra.

    No pisa nada que tenga medida. Devuelve cuantas celdas ha marcado.
    """
    impresos = defaultdict(set)
    for _fecha, snap in hist:
        for reg in snap or []:
            ids = mapa_ids.get((reg.get('building'), reg.get('floor')))
            if not ids:
                continue
            pid, plid = ids
            tid, _propio = resolver(reg.get('task'))
            impresos[(pid, plid, a_letra(reg.get('unit')))].add(tid)

    tocadas = 0
    for clave, celda in estados.items():
        if celda.get('v') not in (None, '?'):
            continue
        try:
            pid, plid, tid, unidad = clave.split('__')
        except ValueError:
            continue
        aplicables = impresos.get((pid, plid, unidad))
        if aplicables is None or tid in aplicables:
            continue
        celda.update({'v': 'N', 'f': None, 'r': None,
                      'origen': 'la hoja no imprime este tajo aqui'})
        tocadas += 1
    return tocadas


def aplicar_terminado_completo(estados, declarado, mapa_ids, fecha):
    """La obra esta acabada salvo las ubicaciones que se excluyan.

    Se usa cuando la obra termino DESPUES de la ultima revision y no hubo hoja
    que lo recogiera: las marcas viejas (M, /) y los huecos (?) ya no
    describen la realidad. Es la norma de obra de Bixente aplicada a la letra
    -lo que dice la ultima confirmacion es lo que vale- solo que la
    confirmacion llega de palabra en vez de en una hoja.

    Respeta 'N': terminar una obra no inventa trabajo donde no lo hay.
    Devuelve cuantas celdas ha tocado.
    """
    if not declarado:
        return 0
    salvo = set()
    for edificio, plantas in (declarado.get('excepto') or {}).items():
        if str(edificio).startswith('_'):
            continue
        for planta, unidades in (plantas or {}).items():
            ids = mapa_ids.get((edificio, planta))
            if not ids:
                print(f'   [AVISO] terminado_completo: no existe '
                      f'{edificio} / planta {planta}. Se ignora la excepcion.')
                continue
            pid, plid = ids
            for unidad in unidades:
                salvo.add((pid, plid, unidad))

    tocadas = 0
    for clave, celda in estados.items():
        if celda.get('v') == 'N':
            continue
        try:
            pid, plid, _tid, unidad = clave.split('__')
        except ValueError:
            continue
        if (pid, plid, unidad) in salvo:
            continue
        if celda.get('v') == 'X':
            continue
        celda.update({'v': 'X', 'f': fecha, 'r': None,
                      'origen': 'confirmado_usuario'})
        tocadas += 1
    return tocadas


def aplicar_terminadas(estados, declaradas, mapa_ids, fecha):
    """Marca X las ubicaciones que el usuario declara acabadas.

    Son dependencias que se trataron aparte y por eso nunca llevaron marca en
    la hoja. Sin esto entrarian como '?' y dirian 'nadie las ha mirado', que
    no es verdad.

    SOLO rellena huecos: no pisa jamas una medida real, porque una
    confirmacion de despacho no puede borrar lo que alguien fue a ver.
    Devuelve cuantas celdas ha tocado.
    """
    tocadas = 0
    for edificio, plantas in (declaradas or {}).items():
        if str(edificio).startswith('_'):
            continue
        for planta, unidades in (plantas or {}).items():
            if str(planta).startswith('_'):
                continue
            ids = mapa_ids.get((edificio, planta))
            if not ids:
                print(f'   [AVISO] terminadas_al_100: no existe '
                      f'{edificio} / planta {planta}. Se ignora.')
                continue
            pid, plid = ids
            prefijo = f'{pid}__{plid}__'
            for unidad in unidades:
                sufijo = f'__{unidad}'
                for clave, celda in estados.items():
                    if not (clave.startswith(prefijo) and clave.endswith(sufijo)):
                        continue
                    if celda.get('v') not in (None, '?'):
                        continue
                    celda.update({'v': 'X', 'f': fecha, 'r': None,
                                  'origen': 'confirmado_usuario'})
                    tocadas += 1
    return tocadas


def _cargar_historial(obra_id):
    """El historial crudo del adaptador de la obra."""
    ruta = os.path.join(SISTEMA, 'adaptadores', f'adaptador_{obra_id}.py')
    spec = importlib.util.spec_from_file_location(f'_adh_{obra_id}', ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, SISTEMA)
    sys.path.insert(0, os.path.join(SISTEMA, 'adaptadores'))
    spec.loader.exec_module(mod)
    return mod.cargar_historial()


def _unidades_vistas(hist):
    """(edificio, planta, unidad) de todo lo que la hoja imprime, con marca o
    sin ella. Las filas sin marca de ninguna revision son las candidatas a
    hueco de plantilla."""
    vistas = []
    ya = set()
    for _fecha, snap in hist:
        for reg in snap or []:
            trio = (reg.get('building'), reg.get('floor'), reg.get('unit'))
            if trio not in ya:
                ya.add(trio)
                vistas.append(trio)
    return vistas


def _detalle_desde_historial(hist, obra_id, resolver):
    """Traduce lo medido al formato de detalle_items que ya consume el
    sembrador. Solo entran celdas CON marca: las que nunca la tuvieron se
    quedan en '?', que es lo que significan."""
    catalogo = cargar(os.path.join(SISTEMA, 'reglas', 'CATALOGO_TAJOS.json'))
    meta = {t['id']: t for t in catalogo['tajos']}
    nombre_original = {}
    edificio_de = {}
    for _fecha, snap in hist:
        for reg in snap or []:
            tid, _propio = resolver(reg.get('task'))
            nombre_original.setdefault(tid, reg.get('task'))
            edificio_de.setdefault((reg.get('floor'), reg.get('unit')),
                                   reg.get('building'))

    detalle = []
    for (floor, unit, tid), (estado, fecha) in \
            estados_desde_historial(hist, resolver).items():
        m = meta.get(tid, {})
        detalle.append({
            'edificio': edificio_de.get((floor, unit)),
            'planta': floor, 'unidad': unit,
            'tarea_id': tid,
            'trabajo': m.get('nombre') or nombre_original.get(tid, tid),
            'ambito': m.get('ambito', 'vivienda'),
            'propiedad': m.get('propiedad', 'propio'),
            'fase_nombre': m.get('fase', 'Sin clasificar'),
            'orden_ejecucion': m.get('orden', 9999),
            'estado_actual': estado,
            'ultima_fecha': fecha,
            # Un tajo que no esta en el catalogo comun no es un error: esta
            # obra tiene vocabulario propio y hay que poder distinguirlo.
            'propio_de_la_obra': tid not in meta,
        })
    return detalle


def sembrar(obra_id, carpeta, modo, tipo_obra):
    conf = cargar(os.path.join(AQUI, f'confirmaciones_{obra_id}.json'))
    separar = conf['regla_identificador']['separar_habitaciones']
    confirmadas = conf['plantas_confirmadas']
    notas = conf.get('notas', {})

    prio = cargar(os.path.join(OBRAS_DIR, carpeta, 'INFORME SAGARDE IA',
                               'prioridades_trabajos.json'))
    revision = prio.get('revision')
    rev_id = 'rev_' + str(revision or '').replace('/', '')

    # De donde salen los estados. Por defecto, prioridades_trabajos.json, que
    # es como nacio el sembrador. Una obra puede pedir 'historial' y entonces
    # se siembra de lo MEDIDO: hace falta cuando la ultima revision es parcial,
    # porque entonces el priorizador arrastra 'Terminado segun la ultima
    # confirmacion valida' sobre celdas que nadie ha mirado (en Obispo Orueta,
    # 1444 de 2404). Regla de la casa: se guarda lo medido, se recalcula lo
    # derivado.
    fuente = conf.get('fuente_estados', 'prioridades')
    hist = []
    if fuente == 'historial':
        hist = _cargar_historial(obra_id)
        detalle = _detalle_desde_historial(hist, obra_id, resolver_tajo())
        print(f'   [FUENTE] historial: {len(hist)} revisiones, '
              f'{len(detalle)} celdas medidas')
    else:
        detalle = prio['detalle_items']

    resumen = cargar(os.path.join(SISTEMA, 'resumen_obras.json'))
    ident = next((o for o in resumen['obras'] if o['carpeta'] == carpeta), {})

    # --- observado: (edif, planta, letra) -> habitaciones ---------------
    # Ojo: se recorre TODO lo que imprime la hoja, tenga marca o no. Las filas
    # sin marca son las candidatas a hueco de plantilla y hay que verlas aqui
    # para que salgan como exclusiones.
    observado = defaultdict(dict)
    habitaciones = {}
    vistos = _unidades_vistas(hist) if fuente == 'historial' else [
        (it['edificio'], it['planta'], it['unidad']) for it in detalle]
    for ed, pl, un in vistos:
        if not (ed and pl and un) or un in {'—', '-'}:
            continue
        letra, hab = partir_unidad(un, separar)
        observado[(ed, pl)][letra] = un          # letra -> id original
        if hab is not None:
            habitaciones[(ed, pl, letra)] = hab

    # --- estructura definitiva = la confirmada -------------------------
    portales, mapa_ids, alias = [], {}, {}
    nuevas, desaparecidas, exclusiones = [], [], []
    for i, ed in enumerate(sorted(confirmadas), 1):
        pid = f'p{i}'
        plantas = []
        zonas = confirmadas[ed].get('_zonas_comunes', {})
        for pl in sorted((p for p in confirmadas[ed] if not p.startswith('_')),
                         key=clave_planta):
            plid = 'pb' if clave_planta(pl)[0] == 0 else str(pl)
            vistas = observado.get((ed, pl), {})
            ubis = []
            for zc in zonas.get(pl, []):
                ubis.append({'id': zc, 'tipo': 'zona_comun', 'habitaciones': None,
                             'origen': 'campo' if zc in vistas else 'confirmado_usuario',
                             'confirmado': revision if zc in vistas else conf['fecha']})
                if zc in vistas:
                    alias[f'{pid}__{plid}__{zc}'] = vistas[zc]
            for letra in confirmadas[ed][pl]:
                visto = letra in vistas
                if not visto:
                    nuevas.append(f'{ed} planta {pl} vivienda {letra}')
                ubis.append({
                    'id': letra,
                    'tipo': 'vivienda',
                    'habitaciones': habitaciones.get((ed, pl, letra)),
                    'origen': 'campo' if visto else 'confirmado_usuario',
                    'confirmado': revision if visto else conf['fecha'],
                })
                if visto:
                    alias[f'{pid}__{plid}__{letra}'] = vistas[letra]
            declaradas = set(confirmadas[ed][pl]) | set(zonas.get(pl, []))
            for letra in vistas:
                if letra not in declaradas:
                    desaparecidas.append(f'{ed} planta {pl} unidad {vistas[letra]}')
                    # Se guarda el descarte, no solo se imprime: el adaptador
                    # volvera a emitir esta unidad en cada regeneracion y la
                    # ficha tiene que poder decir que no existe. Sin esto la
                    # correccion se revertia sola (Bolueta: 101 ubicaciones en
                    # vez de 97).
                    exclusiones.append({
                        'portal': ed, 'planta': pl, 'unidad': vistas[letra],
                        'motivo': 'la hoja la imprime pero la estructura '
                                  'confirmada no la incluye',
                        'confirmado': conf['fecha'],
                    })
            nota = notas.get(f'{ed}/{pl}')
            planta = {'id': plid, 'nombre': pl,
                      'orden': clave_planta(pl)[1] if clave_planta(pl)[0] else 0,
                      'ubicaciones': ubis}
            if nota:
                planta['nota'] = nota
            plantas.append(planta)
            mapa_ids[(ed, pl)] = (pid, plid)
        portales.append({'id': pid, 'nombre': ed, 'referencia': ed,
                         'plantas': plantas})

    # --- tajos ----------------------------------------------------------
    tajos = {}
    for it in detalle:
        t = it['tarea_id']
        if t not in tajos:
            tajos[t] = {'id': t, 'nombre': it['trabajo'], 'ambito': it['ambito'],
                        'propiedad': it['propiedad'], 'fase': it['fase_nombre'],
                        'orden': it['orden_ejecucion']}
            if it.get('propio_de_la_obra'):
                tajos[t]['origen'] = 'propio_de_la_obra'
    orden_tajos = sorted(tajos, key=lambda t: tajos[t]['orden'])
    propios = [t for t in orden_tajos if tajos[t].get('origen') == 'propio_de_la_obra']
    if propios:
        print(f'   [TAJOS] {len(propios)} propios de la obra, fuera del '
              f'catalogo comun: {", ".join(tajos[t]["nombre"] for t in propios)}')

    # --- estados: primero todo '?', luego lo medido --------------------
    estados = {}
    for p in portales:
        for pl in p['plantas']:
            for u in pl['ubicaciones']:
                for t in orden_tajos:
                    estados[f"{p['id']}__{pl['id']}__{t}__{u['id']}"] = {
                        'v': '?', 'f': None, 'r': None}

    medidas, huerfanas = 0, 0
    for it in detalle:
        ids = mapa_ids.get((it['edificio'], it['planta']))
        if not ids:
            huerfanas += 1
            continue
        pid, plid = ids
        letra, _ = partir_unidad(it['unidad'], separar)
        k = f"{pid}__{plid}__{it['tarea_id']}__{letra}"
        if k not in estados:
            huerfanas += 1
            continue
        estados[k] = {'v': MAPA_ESTADO.get(str(it.get('estado_actual', '')).strip(), 'P'),
                      'f': it.get('ultima_fecha') or revision, 'r': rev_id}
        medidas += 1

    # --- que tajos aplican de verdad a cada ubicacion --------------------
    # Antes de dar nada por desconocido: si la hoja nunca ha impreso esa fila
    # ahi, el tajo no aplica.
    no_aplica = 0
    if fuente == 'historial':
        no_aplica = marcar_no_aplica(
            estados, hist, resolver_tajo(), mapa_ids,
            lambda u: partir_unidad(u, separar)[0])
        print(f'   [MATRIZ] {no_aplica} celdas marcadas N: la hoja no imprime '
              f'ese tajo en esa ubicacion')

    # --- ubicaciones que el usuario declara acabadas ---------------------
    # Se aplica DESPUES de lo medido para que no pueda pisarlo.
    confirmadas_x = aplicar_terminadas(
        estados, conf.get('terminadas_al_100'), mapa_ids, conf['fecha'])
    if confirmadas_x:
        print(f'   [CONFIRMADO] {confirmadas_x} celdas a X por declaracion '
              f'del usuario (dependencias tratadas aparte)')

    completo_x = aplicar_terminado_completo(
        estados, conf.get('terminado_completo'), mapa_ids, conf['fecha'])
    if completo_x:
        print(f'   [CONFIRMADO] obra terminada salvo lo excluido: '
              f'{completo_x} celdas a X')

    # --- 5. Reclamar correcciones huerfanas -----------------------------
    # Correcciones que Bixente escribio a mano sobre ubicaciones que la
    # estructura inferida no conocia (p.ej. la vivienda E de ZR2.1 planta 2,
    # o el PORTAL leido como 'PORT AL'). Nunca llegaron a
    # prioridades_trabajos.json. Ahora que la ficha declara esas ubicaciones,
    # el dato se puede recuperar en vez de perderse.
    # NORMA DE OBRA: lo que se apunta en la ultima revision es lo que vale.
    # Las correcciones son marcas escritas a boli sobre la hoja de campo, o
    # sea el dato mas directo que existe. Se aplican las del fichero de
    # correcciones MAS RECIENTE, que es el que describe el estado vigente.
    reclamadas = []
    corto2largo = _mapa_tajos_cortos(obra_id)
    ficheros = glob.glob(os.path.join(OBRAS_DIR, carpeta, 'REVISIONES',
                                      '*.correcciones.json'))

    def _fecha_fichero(ruta):
        m = re.search(r'(\d{2})(\d{2})(\d{4})', os.path.basename(ruta))
        return (m.group(3), m.group(2), m.group(1)) if m else ('0000', '00', '00')

    if ficheros:
        ultimo = max(ficheros, key=_fecha_fichero)
        for k, v in (cargar(ultimo).get('estados') or {}).items():
            try:
                pid, plid, tc, un = k.split('__')
            except ValueError:
                continue
            tid = corto2largo.get(tc, tc)
            # 'PORT AL' -> 'PORTAL': el extractor de PDF parte algunos nombres
            letra, _ = partir_unidad(un.replace(' ', ''), separar)
            destino = f'{pid}__{plid}__{tid}__{letra}'
            actual = estados.get(destino)
            if actual is None or v not in MAPA_ESTADO:
                continue
            if actual['v'] != MAPA_ESTADO[v]:
                reclamadas.append((destino, actual['v'], MAPA_ESTADO[v]))
                estados[destino] = {'v': MAPA_ESTADO[v], 'f': revision,
                                    'r': rev_id, 'origen': 'correccion manual'}

    ficha = {
        'version': 1, 'id': obra_id, 'modo': modo,
        'fecha_entrada_digital': revision, 'actualizado': prio.get('generado'),
        'identidad': {'nombre': ident.get('nombre'), 'carpeta': carpeta,
                      'tipo_obra': tipo_obra,
                      '_meta': {'actualizado': prio.get('generado'), 'origen': 'sembrado'}},
        'estructura': {'bloques': [{'id': 'b1', 'nombre': 'ZR1', 'portales': portales}],
                       'alias_historico': alias,
                       'exclusiones': exclusiones,
                       '_meta': {'actualizado': conf['fecha'],
                                 'origen': 'sembrado + confirmado por usuario'}},
        'tajos': {'plantilla': f'{tipo_obra}_v1', 'aplicables': orden_tajos,
                  'detalle': [tajos[t] for t in orden_tajos],
                  '_meta': {'actualizado': revision, 'origen': 'sembrado'}},
        'estados': estados,
        'revisiones': [{'id': rev_id, 'fecha': revision,
                        'origen': 'historial existente', 'celdas_medidas': medidas}],
        'dudas': prio.get('dudas_pendientes') or [],
        'materiales': {}, 'documentos': {}, 'contactos': [],
    }
    return ficha, nuevas, desaparecidas, medidas, huerfanas, reclamadas


if __name__ == '__main__':
    ficha, nuevas, desap, medidas, huerf, recl = sembrar(
        'mungia', '2026 MUNGIA ACR NEINOR', 'hibrida', 'viviendas')
    salida = os.path.join(AQUI, 'ficha_obra_mungia.json')
    with open(salida, 'w', encoding='utf-8') as f:
        json.dump(ficha, f, ensure_ascii=False, indent=2)

    ports = ficha['estructura']['bloques'][0]['portales']
    est = ficha['estados']
    print('FICHA v2:', salida, '(%.0f KB)' % (os.path.getsize(salida) / 1024))
    print('  portales:%d  plantas:%d  ubicaciones:%d  tajos:%d  celdas:%d'
          % (len(ports), sum(len(p['plantas']) for p in ports),
             sum(len(pl['ubicaciones']) for p in ports for pl in p['plantas']),
             len(ficha['tajos']['aplicables']), len(est)))
    print('  estados:', dict(Counter(v['v'] for v in est.values())))
    print('  celdas medidas desde el historial:', medidas,
          '| descartadas por no existir en la estructura confirmada:', huerf)
    print()
    print('VIVIENDAS QUE EXISTEN PERO NUNCA SE HABIAN REGISTRADO:')
    for n in nuevas:
        print('   +', n)
    print('CORRECCIONES HUERFANAS RECUPERADAS:', len(recl))
    for k,a,b in recl: print('   %-46s %s -> %s'%(k,a,b))
    print('UBICACIONES DESCARTADAS (estaban en los datos, no existen):')
    for d in desap:
        print('   -', d)
    print()
    print('ESTRUCTURA FINAL:')
    for p in ports:
        for pl in p['plantas']:
            ids = ','.join('%s%s' % (u['id'], u['habitaciones'] or '')
                           for u in pl['ubicaciones']) or '(sin viviendas)'
            print('   %-6s planta %-3s -> %s' % (p['nombre'], pl['nombre'], ids))
