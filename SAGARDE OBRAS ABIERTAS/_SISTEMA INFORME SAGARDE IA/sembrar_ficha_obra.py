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


def sembrar(obra_id, carpeta, modo, tipo_obra):
    conf = cargar(os.path.join(AQUI, f'confirmaciones_{obra_id}.json'))
    separar = conf['regla_identificador']['separar_habitaciones']
    confirmadas = conf['plantas_confirmadas']
    notas = conf.get('notas', {})

    prio = cargar(os.path.join(OBRAS_DIR, carpeta, 'INFORME SAGARDE IA',
                               'prioridades_trabajos.json'))
    detalle = prio['detalle_items']
    revision = prio.get('revision')
    rev_id = 'rev_' + str(revision or '').replace('/', '')

    resumen = cargar(os.path.join(SISTEMA, 'resumen_obras.json'))
    ident = next((o for o in resumen['obras'] if o['carpeta'] == carpeta), {})

    # --- observado: (edif, planta, letra) -> habitaciones ---------------
    observado = defaultdict(dict)
    habitaciones = {}
    for it in detalle:
        ed, pl, un = it['edificio'], it['planta'], it['unidad']
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
    orden_tajos = sorted(tajos, key=lambda t: tajos[t]['orden'])

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
