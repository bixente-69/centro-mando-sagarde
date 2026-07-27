# -*- coding: utf-8 -*-
"""
FICHA DE OBRA (capa 0 - fuente de verdad por obra)
====================================================
Mantiene `{obra}/INFORME SAGARDE IA/ficha_obra.json` al dia en cada
regeneracion, en vez de tener que resembrarla a mano.

Por que existe
--------------
Hasta ahora la estructura de la obra (bloques/portales/plantas/ubicaciones)
no era un dato: se deducia de las celdas que alguien habia rellenado alguna
vez. Una ubicacion no marcada sencillamente no existia, con dos consecuencias:
una obra sin revisiones no podia generar su primera hoja, y una vivienda que
nadie hubiera marcado nunca desaparecia del sistema aunque estuviera
construida.

La ficha invierte eso: la estructura se declara y las revisiones solo
rellenan estados.

Que hace `actualizar()`
-----------------------
En cada pasada compara la ficha con los datos frescos de la revision y:
  - actualiza el estado de las celdas que la revision menciona
  - NO toca las que no menciona (evita borrar datos que la revision no cubre)
  - reclama correcciones manuales sobre ubicaciones que la ficha conoce y la
    revision no (asi no se pierde lo escrito a boli sobre una vivienda que el
    lector todavia no sabe leer)
  - da de alta ubicaciones y tajos nuevos marcandolos SIN CONFIRMAR y avisando,
    para que nada entre en silencio
  - registra la revision procesada
  - crea los apartados que falten si el esquema crece

Alfabeto de estados guardados
-----------------------------
  X  terminado          M  mas del 50%        /  iniciado
  P  pendiente CONFIRMADO: se comprobo en campo y no esta hecho
  ?  desconocido: nadie lo ha mirado nunca
  N  no aplica a esa ubicacion

`P` y `?` son distintos a proposito: "he ido y no esta" no es lo mismo que
"no se sabe". Esa diferencia es la que permite respetar la norma de obra
(la ultima revision es la que vale) sin tragarse errores de lectura.

NO se guardan BLOQUEADO / DUDAS / VIABLE / OTROS_GREMIOS: son categorias que
calcula el priorizador desde las dependencias. Regla de la casa: se guarda lo
MEDIDO, se recalcula lo DERIVADO.
"""
import json
import os
import re
import unicodedata
from datetime import datetime

VERSION = 1
NOMBRE_FICHERO = 'ficha_obra.json'

# Estado tal y como llega del priorizador -> estado guardado en la ficha
# Las claves están normalizadas (minúsculas). La cadena vacía sigue siendo 'P':
# una casilla vacía en hoja validada es un dato que confirma "no está hecho".
MAPA_ESTADO = {
    'x': 'X', 'm': 'M', '/': '/',
    'pendiente': 'P', '': 'P', 'n': 'N',
}

APARTADOS = ('identidad', 'estructura', 'tajos', 'estados', 'revisiones',
             'dudas', 'materiales', 'documentos', 'contactos')

VACIO_POR_APARTADO = {
    'identidad': dict, 'estructura': dict, 'tajos': dict, 'estados': dict,
    'revisiones': list, 'dudas': list, 'materiales': dict,
    'documentos': dict, 'contactos': list,
}


# ---------------------------------------------------------------- utilidades

def ruta_ficha(carpeta_obra_abs):
    return os.path.join(carpeta_obra_abs, 'INFORME SAGARDE IA', NOMBRE_FICHERO)


def cargar(carpeta_obra_abs):
    """Devuelve la ficha, o None si la obra aun no tiene."""
    ruta = ruta_ficha(carpeta_obra_abs)
    if not os.path.isfile(ruta):
        return None
    with open(ruta, encoding='utf-8') as f:
        return json.load(f)


def guardar(carpeta_obra_abs, ficha):
    ruta = ruta_ficha(carpeta_obra_abs)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(ficha, f, ensure_ascii=False, indent=2)
    return ruta


def _clave_planta(nombre):
    texto = str(nombre or '').strip().upper()
    if texto in {'PB', 'B', 'BAJA', 'BAJO', 'PLANTA BAJA'}:
        return (0, 0.0)
    try:
        return (1, float(texto.replace(',', '.')))
    except ValueError:
        return (2, 0.0)


def _planta_id(nombre):
    return 'pb' if _clave_planta(nombre)[0] == 0 else str(nombre)


def _fold(valor):
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()


def _ahora():
    return datetime.now().strftime('%d/%m/%Y %H:%M')


def _normalizar_estado(valor):
    """Normaliza un estado para búsqueda en MAPA_ESTADO.
    Convierte a minúsculas y elimina espacios en blanco."""
    return str(valor or '').strip().lower()


# ------------------------------------------------------------- normalizacion

def asegurar_apartados(ficha):
    """Crea los apartados que falten. Permite que el esquema crezca sin que
    haya que regenerar las fichas ya existentes."""
    creados = []
    for nombre in APARTADOS:
        if nombre not in ficha:
            ficha[nombre] = VACIO_POR_APARTADO[nombre]()
            creados.append(nombre)
    for nombre in ('identidad', 'estructura', 'tajos'):
        if isinstance(ficha.get(nombre), dict):
            ficha[nombre].setdefault('_meta', {})
    return creados


# ------------------------------------------------------ volcado de apartados

# Etiqueta tal y como aparece en la hoja 'Datos' del xlsx (normalizada con
# _fold) -> campo de ficha['identidad']. Se listan varias variantes por
# campo porque las FICHA DE OBRA.xlsx reales de Mungia/Bolueta/Gernika/
# Obispo Orueta no comparten una redaccion unica de cabecera.
CAMPOS_IDENTIDAD = {
    'cliente': 'cliente',
    'cliente titular de la instalacion': 'cliente',
    'promotora': 'promotora', 'promotor': 'promotora',
    'constructora': 'constructora',
    'constructora contratista general': 'constructora',
    'direccion': 'direccion',
    'codigo': 'codigo', 'codigo de obra': 'codigo',
    'fecha inicio': 'fecha_inicio', 'fecha de inicio': 'fecha_inicio',
    'fecha de inicio de obra': 'fecha_inicio',
    'fecha fin': 'fecha_fin', 'fecha fin prevista': 'fecha_fin',
    'fecha prevista de fin': 'fecha_fin',
    'fecha prevista de fin de obra': 'fecha_fin',
    'jefe de obra': 'jefe_obra', 'responsable': 'jefe_obra',
    'responsable de obra': 'jefe_obra', 'responsable de obra sagarde': 'jefe_obra',
}


def volcar_apartados(ficha, ficha_xlsx=None, materiales=None, documentos=None):
    """Rellena identidad, contactos, materiales y documentos desde los lectores.

    Solo escribe lo que viene con dato: nunca pisa un valor existente con
    vacio, porque la ficha es acumulativa y un xlsx incompleto no debe
    borrar lo que ya se sabia. Devuelve la lista de apartados que han
    cambiado."""
    asegurar_apartados(ficha)
    cambiados = []

    if ficha_xlsx and ficha_xlsx.get('_disponible'):
        identidad = ficha['identidad']
        toco = False
        for etiqueta, valor in (ficha_xlsx.get('datos') or {}).items():
            campo = CAMPOS_IDENTIDAD.get(_fold(etiqueta))
            # La guarda del valor vacio es el principio de esta funcion: la
            # ficha es acumulativa y un xlsx a medio rellenar no debe borrar
            # lo que ya se sabia de la obra.
            if campo and valor not in (None, ''):
                if identidad.get(campo) != valor:
                    identidad[campo] = valor
                    toco = True
        if toco:
            identidad.setdefault('_meta', {})['actualizado'] = _ahora()
            cambiados.append('identidad')
        personal = ficha_xlsx.get('personal') or []
        if personal and personal != ficha.get('contactos'):
            ficha['contactos'] = personal
            cambiados.append('contactos')

    if materiales and materiales.get('disponible') and materiales.get('items'):
        resumen = {
            'ultimo_mes': materiales.get('ultimo_mes'),
            'ultima_fecha': materiales.get('ultima_fecha'),
            'dias_desde': materiales.get('dias_desde'),
            'meses': materiales.get('meses') or [],
            'n_items': len(materiales.get('items') or []),
            'aviso': materiales.get('aviso'),
            '_meta': {'actualizado': _ahora()},
        }
        if {k: v for k, v in resumen.items() if k != '_meta'} != \
           {k: v for k, v in (ficha.get('materiales') or {}).items() if k != '_meta'}:
            ficha['materiales'] = resumen
            cambiados.append('materiales')

    if documentos:
        por_categoria = {}
        for doc in documentos:
            categoria = doc.get('categoria') or 'Otros'
            por_categoria[categoria] = por_categoria.get(categoria, 0) + 1
        resumen = {'total': len(documentos), 'por_categoria': por_categoria,
                   '_meta': {'actualizado': _ahora()}}
        anterior = ficha.get('documentos') or {}
        if (anterior.get('total'), anterior.get('por_categoria')) != \
           (resumen['total'], resumen['por_categoria']):
            ficha['documentos'] = resumen
            cambiados.append('documentos')

    return cambiados


def _indice_ubicaciones(ficha):
    """(portal_id, planta_id, ubicacion_id) -> dict de la ubicacion, mas los
    indices por nombre para poder cruzar con lo que dice la revision, que
    habla de (edificio, planta, unidad) con los nombres impresos."""
    por_id, por_nombre = {}, {}
    alias = (ficha.get('estructura') or {}).get('alias_historico') or {}
    inverso = {}
    for clave, historico in alias.items():
        inverso.setdefault(historico, clave)
    for bloque in (ficha.get('estructura') or {}).get('bloques') or []:
        for portal in bloque.get('portales') or []:
            for planta in portal.get('plantas') or []:
                for ubi in planta.get('ubicaciones') or []:
                    trio = (portal['id'], planta['id'], ubi['id'])
                    por_id[trio] = ubi
                    ref = portal.get('referencia') or portal.get('nombre')
                    por_nombre[(_fold(ref), _fold(planta.get('nombre')),
                                _fold(ubi['id']))] = trio
                    clave_alias = f"{portal['id']}__{planta['id']}__{ubi['id']}"
                    historico = alias.get(clave_alias)
                    if historico:
                        por_nombre[(_fold(ref), _fold(planta.get('nombre')),
                                    _fold(historico))] = trio
    return por_id, por_nombre


def _localizar(por_nombre, edificio, planta, unidad):
    return por_nombre.get((_fold(edificio), _fold(planta), _fold(unidad)))


# ------------------------------------------------------------- actualizacion

def actualizar(ficha, prioridades, correcciones=None, mapa_tajos_cortos=None):
    """Vuelca en la ficha lo que trae una regeneracion.

    ficha         : dict ya cargado (se modifica in situ y se devuelve)
    prioridades   : contenido de prioridades_trabajos.json
    correcciones  : {clave_corta: estado} del fichero de correcciones mas
                    reciente, para reclamar lo escrito a boli sobre
                    ubicaciones que la revision todavia no sabe leer
    mapa_tajos_cortos : {'cuad-mec': 'cuadro_mecanizado', ...}

    Devuelve (ficha, cambios) donde `cambios` es un dict con el detalle de lo
    que ha pasado, para poder avisar por consola.
    """
    cambios = {
        'apartados_creados': asegurar_apartados(ficha),
        'estados_cambiados': [], 'estados_nuevos': 0,
        'ubicaciones_nuevas': [], 'tajos_nuevos': [],
        'correcciones_reclamadas': [], 'revision_registrada': None,
        'estados_no_reconocidos': [],
    }
    detalle = prioridades.get('detalle_items') or []
    if not detalle:
        return ficha, cambios

    revision = prioridades.get('revision') or ''
    rev_id = 'rev_' + str(revision).replace('/', '')
    estados = ficha.setdefault('estados', {})
    por_id, por_nombre = _indice_ubicaciones(ficha)

    # --- tajos nuevos -----------------------------------------------------
    tajos = ficha.setdefault('tajos', {})
    detalle_tajos = tajos.setdefault('detalle', [])
    conocidos = {t['id'] for t in detalle_tajos}
    for item in detalle:
        tid = item.get('tarea_id')
        if tid and tid not in conocidos:
            conocidos.add(tid)
            detalle_tajos.append({
                'id': tid, 'nombre': item.get('trabajo') or tid,
                'ambito': item.get('ambito'), 'propiedad': item.get('propiedad'),
                'fase': item.get('fase_nombre'),
                'orden': item.get('orden_ejecucion'),
                'origen': 'revision_sin_confirmar', 'visto_en': revision,
            })
            cambios['tajos_nuevos'].append(tid)
    if cambios['tajos_nuevos']:
        detalle_tajos.sort(key=lambda t: (t.get('orden') or 9999, t['id']))
        tajos['aplicables'] = [t['id'] for t in detalle_tajos]
        tajos.setdefault('_meta', {})['actualizado'] = revision

    # --- estados de las celdas que la revision SI menciona -----------------
    for item in detalle:
        trio = _localizar(por_nombre, item.get('edificio'),
                          item.get('planta'), item.get('unidad'))
        if trio is None:
            trio = _alta_ubicacion(ficha, item, revision, cambios,
                                   por_id, por_nombre)
            if trio is None:
                continue
        portal_id, planta_id, ubi_id = trio
        clave = f"{portal_id}__{planta_id}__{item['tarea_id']}__{ubi_id}"
        # Normalizar el estado: minúsculas, sin espacios
        estado_raw = item.get('estado_actual', '')
        estado_norm = _normalizar_estado(estado_raw)
        nuevo = MAPA_ESTADO.get(estado_norm, '?')
        # Registrar estados no reconocidos (que no sean vacíos)
        if nuevo == '?' and estado_norm:
            if estado_norm not in cambios['estados_no_reconocidos']:
                cambios['estados_no_reconocidos'].append(estado_norm)
        anterior = estados.get(clave)
        if anterior is None:
            estados[clave] = {'v': nuevo, 'f': item.get('ultima_fecha') or revision,
                              'r': rev_id}
            cambios['estados_nuevos'] += 1
        elif anterior.get('v') != nuevo:
            cambios['estados_cambiados'].append((clave, anterior.get('v'), nuevo))
            estados[clave] = {'v': nuevo, 'f': item.get('ultima_fecha') or revision,
                              'r': rev_id}
        else:
            anterior['f'] = item.get('ultima_fecha') or revision
            anterior['r'] = rev_id

    # --- celdas nuevas por tajos o ubicaciones dados de alta ahora ---------
    _completar_matriz(ficha, estados, cambios)

    # --- correcciones sobre ubicaciones que la revision no cubre -----------
    if correcciones:
        _reclamar_correcciones(estados, correcciones, mapa_tajos_cortos or {},
                               ficha, revision, rev_id, cambios)

    # --- registro de la revision ------------------------------------------
    revisiones = ficha.setdefault('revisiones', [])
    if revision and not any(r.get('id') == rev_id for r in revisiones):
        revisiones.append({
            'id': rev_id, 'fecha': revision,
            'procesada': _ahora(),
            'celdas': len(detalle),
            'cambios': len(cambios['estados_cambiados']),
        })
        revisiones.sort(key=lambda r: _orden_fecha(r.get('fecha')))
        cambios['revision_registrada'] = rev_id

    ficha['actualizado'] = _ahora()
    ficha.setdefault('version', VERSION)
    return ficha, cambios


def _orden_fecha(fecha):
    partes = str(fecha or '').split('/')
    return tuple(reversed(partes)) if len(partes) == 3 else ('0000',)


def _alta_ubicacion(ficha, item, revision, cambios, por_id, por_nombre):
    """Da de alta una ubicacion que la revision trae y la ficha no conoce.

    Entra marcada SIN CONFIRMAR y se avisa: asi no se pierde el dato, pero
    tampoco se ensucia la estructura en silencio (que es lo que produjo en su
    dia la 'vivienda fantasma' de Mungia)."""
    edificio = str(item.get('edificio') or '').strip()
    planta_nom = str(item.get('planta') or '').strip()
    unidad = str(item.get('unidad') or '').strip()
    if not (edificio and planta_nom and unidad) or unidad in {'—', '-'}:
        return None

    bloques = (ficha.get('estructura') or {}).get('bloques') or []
    if not bloques:
        return None
    portal = None
    for bloque in bloques:
        for candidato in bloque.get('portales') or []:
            ref = candidato.get('referencia') or candidato.get('nombre')
            if _fold(ref) == _fold(edificio):
                portal = candidato
                break
        if portal:
            break
    if portal is None:
        return None          # portal entero desconocido: no se inventa

    planta = next((p for p in portal.get('plantas') or []
                   if _fold(p.get('nombre')) == _fold(planta_nom)), None)
    if planta is None:
        planta = {'id': _planta_id(planta_nom), 'nombre': planta_nom,
                  'orden': _clave_planta(planta_nom)[1], 'ubicaciones': [],
                  'origen': 'revision_sin_confirmar'}
        portal.setdefault('plantas', []).append(planta)
        portal['plantas'].sort(key=lambda p: _clave_planta(p.get('nombre')))
        cambios['ubicaciones_nuevas'].append(f'{edificio} planta {planta_nom} (planta entera)')

    ambito = str(item.get('ambito') or 'vivienda').casefold()
    nueva = {'id': unidad, 'tipo': 'zona_comun' if ambito == 'zona_comun' else
             ('edificio' if ambito == 'edificio' else 'vivienda'),
             'habitaciones': None, 'origen': 'revision_sin_confirmar',
             'confirmado': None, 'visto_en': revision}
    planta.setdefault('ubicaciones', []).append(nueva)
    planta['ubicaciones'].sort(key=lambda u: str(u['id']))
    cambios['ubicaciones_nuevas'].append(f'{edificio} planta {planta_nom} unidad {unidad}')

    trio = (portal['id'], planta['id'], unidad)
    por_id[trio] = nueva
    ref = portal.get('referencia') or portal.get('nombre')
    por_nombre[(_fold(ref), _fold(planta_nom), _fold(unidad))] = trio
    ficha['estructura'].setdefault('_meta', {})['actualizado'] = revision
    return trio


def _completar_matriz(ficha, estados, cambios):
    """Toda ubicacion debe tener una celda por cada tajo aplicable. Las que
    aun no tienen dato nacen como '?' (desconocido), nunca como pendiente:
    que nadie las haya mirado no significa que no esten hechas."""
    tajos = [t['id'] for t in (ficha.get('tajos') or {}).get('detalle') or []]
    if not tajos:
        return
    for bloque in (ficha.get('estructura') or {}).get('bloques') or []:
        for portal in bloque.get('portales') or []:
            for planta in portal.get('plantas') or []:
                for ubi in planta.get('ubicaciones') or []:
                    for tajo in tajos:
                        clave = f"{portal['id']}__{planta['id']}__{tajo}__{ubi['id']}"
                        if clave not in estados:
                            estados[clave] = {'v': '?', 'f': None, 'r': None}
                            cambios['estados_nuevos'] += 1


def _reclamar_correcciones(estados, correcciones, mapa_cortos, ficha,
                           revision, rev_id, cambios):
    """Aplica las correcciones manuales que la revision no llego a recoger.

    Son marcas escritas a boli sobre la hoja de campo: el dato mas directo que
    existe. Se perdian cuando la clave no casaba, por ejemplo porque el
    extractor de PDF parte 'PORTAL' en 'PORT AL', o porque la ubicacion no
    existia en la estructura deducida."""
    for clave, valor in correcciones.items():
        try:
            portal_id, planta_id, tajo_corto, unidad = clave.split('__')
        except ValueError:
            continue
        tajo = mapa_cortos.get(tajo_corto, tajo_corto)
        unidad = unidad.replace(' ', '')
        destino = f'{portal_id}__{planta_id}__{tajo}__{unidad}'
        if destino not in estados:
            destino = _con_alias(ficha, portal_id, planta_id, tajo, unidad, estados)
        if destino is None:
            continue
        # Normalizar el valor de la corrección igual que el bucle principal
        valor_norm = _normalizar_estado(valor)
        nuevo = MAPA_ESTADO.get(valor_norm)
        if nuevo is None:  # Estado no reconocido
            if valor_norm and valor_norm not in cambios['estados_no_reconocidos']:
                cambios['estados_no_reconocidos'].append(valor_norm)
            continue  # No aplicar corrección con estado desconocido, pero sí registrar
        # Si llegamos aquí, el valor fue reconocido correctamente
        if estados[destino].get('v') != nuevo:
            cambios['correcciones_reclamadas'].append(
                (destino, estados[destino].get('v'), nuevo))
            estados[destino] = {'v': nuevo, 'f': revision, 'r': rev_id,
                                'origen': 'correccion manual'}


def _con_alias(ficha, portal_id, planta_id, tajo, unidad, estados):
    """La correccion puede venir con el nombre historico de la unidad ('A2')
    mientras la ficha usa el canonico ('A')."""
    alias = (ficha.get('estructura') or {}).get('alias_historico') or {}
    for clave_alias, historico in alias.items():
        if historico.replace(' ', '') != unidad:
            continue
        try:
            p, pl, u = clave_alias.split('__')
        except ValueError:
            continue
        if p == portal_id and pl == planta_id:
            candidato = f'{p}__{pl}__{tajo}__{u}'
            if candidato in estados:
                return candidato
    return None


def esta_rancia(ficha, prioridades):
    """Devuelve el motivo si la ficha ha quedado por detras de los datos, o
    None si esta al dia.

    La ficha alimenta la hoja de campo. Si se queda atras, se genera una hoja
    con estados de hace dias sin que nadie se entere: por eso conviene que
    grite en vez de fallar en silencio."""
    revision = prioridades.get('revision')
    if not revision:
        return None
    registradas = {r.get('fecha') for r in ficha.get('revisiones') or []}
    if revision not in registradas:
        return (f'la ficha no ha registrado la revision {revision}; '
                f'ultima registrada: {max(registradas, key=_orden_fecha) if registradas else "ninguna"}')
    return None


def resumen_cambios(cambios):
    """Lineas legibles para avisar por consola. Vacio si no hubo nada."""
    lineas = []
    if cambios['apartados_creados']:
        lineas.append('apartados creados: ' + ', '.join(cambios['apartados_creados']))
    if cambios['tajos_nuevos']:
        lineas.append('TAJOS NUEVOS sin confirmar: ' + ', '.join(cambios['tajos_nuevos']))
    for ubi in cambios['ubicaciones_nuevas']:
        lineas.append(f'UBICACION NUEVA sin confirmar: {ubi}')
    if cambios['estados_cambiados']:
        lineas.append('celdas que cambian de estado: %d' % len(cambios['estados_cambiados']))
    if cambios['estados_nuevos']:
        lineas.append('celdas nuevas: %d' % cambios['estados_nuevos'])
    if cambios['correcciones_reclamadas']:
        lineas.append('correcciones manuales recuperadas: %d'
                      % len(cambios['correcciones_reclamadas']))
    if cambios.get('estados_no_reconocidos'):
        lineas.append('ESTADOS NO RECONOCIDOS (guardados como ?): ' +
                      ', '.join(cambios['estados_no_reconocidos']))
    return lineas
