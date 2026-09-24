# -*- coding: utf-8 -*-
"""Ficha de garajes (capa de persistencia separada de la vivienda).

Mantiene ``{obra}/INFORME SAGARDE IA/ficha_garajes.json`` con una estructura
plana ``garaje -> planta -> zona`` y estados por tajo. Los estados medidos
comparten el alfabeto de :mod:`ficha_obra`; las categorías derivadas no se
persisten aquí.

Qué NO hace v1
--------------
- No auto-completa celdas ``?`` para combinaciones zona x tajo no reportadas:
  todavía no existe un perfil por tipo de zona validado en Python.
- No da de alta zonas nuevas desde una revisión: deben existir previamente en
  la estructura y cualquier trío desconocido se declara en los cambios.
- No gestiona identidad, materiales, documentos ni contactos de la obra;
  esos apartados siguen perteneciendo exclusivamente a ``ficha_obra.py``.
- No integra con ``generar_todos.py``, ``panel_obra.py``,
  ``motor_informes.py`` ni ``priorizador_trabajos.py``; corresponde a la
  Fase 3 y esos módulos no se modifican aquí.
"""
import json
import os

from ficha_obra import (
    MAPA_ESTADO,
    ESTADO_A_SNAPSHOT,
    _fold,
    _ahora,
    _normalizar_estado,
)


VERSION = 1
NOMBRE_FICHERO = 'ficha_garajes.json'
APARTADOS = ('estructura', 'tajos', 'estados', 'revisiones', 'dudas')
VACIO_POR_APARTADO = {
    'estructura': dict,
    'tajos': dict,
    'estados': dict,
    'revisiones': list,
    'dudas': list,
}


def ruta_ficha(carpeta_obra_abs):
    """Devuelve la ruta de la ficha de garajes de una obra."""
    return os.path.join(
        carpeta_obra_abs, 'INFORME SAGARDE IA', NOMBRE_FICHERO
    )


def cargar(carpeta_obra_abs):
    """Devuelve la ficha de garajes, o ``None`` si aún no existe."""
    ruta = ruta_ficha(carpeta_obra_abs)
    if not os.path.isfile(ruta):
        return None
    with open(ruta, encoding='utf-8') as fichero:
        return json.load(fichero)


def guardar(carpeta_obra_abs, ficha):
    """Guarda la ficha de garajes como JSON UTF-8 y devuelve su ruta."""
    ruta = ruta_ficha(carpeta_obra_abs)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as fichero:
        json.dump(ficha, fichero, ensure_ascii=False, indent=2)
    return ruta


def asegurar_apartados(ficha):
    """Crea los apartados ausentes y devuelve sus nombres."""
    creados = []
    for nombre in APARTADOS:
        if nombre not in ficha:
            ficha[nombre] = VACIO_POR_APARTADO[nombre]()
            creados.append(nombre)
    for nombre in ('estructura', 'tajos'):
        if isinstance(ficha.get(nombre), dict):
            ficha[nombre].setdefault('_meta', {})
    return creados


def snapshot_desde_ficha(ficha):
    """Traduce la ficha de garajes al snapshot plano de sus celdas medidas."""
    nombres_tajo = {
        tajo['id']: (tajo.get('nombre') or tajo['id'])
        for tajo in (ficha.get('tajos') or {}).get('detalle') or []
    }
    estados = ficha.get('estados') or {}
    filas = []

    for garaje in (ficha.get('estructura') or {}).get('garajes') or []:
        garaje_id = garaje['id']
        nombre_garaje = garaje.get('nombre') or garaje_id
        for planta in garaje.get('plantas') or []:
            planta_id = planta['id']
            nombre_planta = planta.get('nombre') or planta_id
            for zona in planta.get('zonas') or []:
                zona_id = zona['id']
                nombre_zona = zona.get('nombre') or zona_id
                for tajo_id, nombre_tajo in nombres_tajo.items():
                    clave = (
                        f'{garaje_id}__{planta_id}__{tajo_id}__{zona_id}'
                    )
                    dato = estados.get(clave)
                    if not dato:
                        continue
                    estado = ESTADO_A_SNAPSHOT.get(dato.get('v'))
                    if estado is None:
                        continue
                    filas.append({
                        'task': nombre_tajo,
                        'floor': nombre_planta,
                        'garaje': nombre_garaje,
                        'zona': nombre_zona,
                        'status': estado,
                        'garaje_id': garaje_id,
                        'planta_id': planta_id,
                        'zona_id': zona_id,
                    })
    return filas


def _mapa_normalizado(mapa_tajos_cortos):
    """Indexa aliases de tajo sin hacer depender su uso de mayúsculas."""
    return {
        _fold(alias): tajo_id
        for alias, tajo_id in (mapa_tajos_cortos or {}).items()
    }


def _id_tajo(valor, mapa_normalizado):
    """Aplica, si existe, el alias corto declarado para un tajo."""
    return mapa_normalizado.get(_fold(valor), valor)


def actualizar_desde_snapshot(
        ficha, snapshot, revision, mapa_tajos_cortos=None):
    """Convierte un snapshot de garaje y lo aplica mediante :func:`actualizar`."""
    detalle_tajos = (ficha.get('tajos') or {}).get('detalle') or []
    id_por_nombre = {}
    for tajo in detalle_tajos:
        id_por_nombre[_fold(tajo.get('nombre') or '')] = tajo['id']
        id_por_nombre[_fold(tajo['id'])] = tajo['id']

    items = []
    for registro in snapshot or []:
        nombre = str(registro.get('task') or '').strip()
        if not nombre:
            continue
        tarea_id = id_por_nombre.get(_fold(nombre), nombre)
        items.append({
            'tarea_id': tarea_id,
            'trabajo': nombre,
            'garaje_id': registro.get('garaje_id'),
            'planta_id': registro.get('planta_id'),
            'zona_id': registro.get('zona_id'),
            'estado_actual': registro.get('status', ''),
            'ultima_fecha': registro.get('ultima_fecha') or revision,
        })

    datos = {'revision': revision, 'detalle_items': items}
    return actualizar(
        ficha, datos, mapa_tajos_cortos=mapa_tajos_cortos
    )


def _indice_zonas(ficha):
    """Devuelve los tríos canónicos declarados en la estructura."""
    zonas = set()
    for garaje in (ficha.get('estructura') or {}).get('garajes') or []:
        for planta in garaje.get('plantas') or []:
            for zona in planta.get('zonas') or []:
                zonas.add((garaje.get('id'), planta.get('id'), zona.get('id')))
    return zonas


def _referencia_zona(trio):
    """Forma estable y legible para declarar una zona desconocida."""
    return '__'.join(str(parte or '') for parte in trio)


def actualizar(ficha, datos, mapa_tajos_cortos=None):
    """Aplica los ``detalle_items`` de una revisión a la ficha, in situ.

    Cada elemento usa ``tarea_id``, ``trabajo``, ``garaje_id``,
    ``planta_id``, ``zona_id``, ``estado_actual`` y, opcionalmente,
    ``ultima_fecha``. Devuelve ``(ficha, cambios)``.
    """
    cambios = {
        'apartados_creados': asegurar_apartados(ficha),
        'tajos_nuevos': [],
        'estados_nuevos': 0,
        'estados_cambiados': [],
        'zonas_desconocidas': [],
        'estados_no_reconocidos': [],
        'revision_registrada': None,
    }
    detalle = datos.get('detalle_items') or []
    if not detalle:
        return ficha, cambios

    revision = datos.get('revision') or ''
    rev_id = 'rev_' + str(revision).replace('/', '')
    mapa = _mapa_normalizado(mapa_tajos_cortos)

    tajos = ficha.setdefault('tajos', {})
    detalle_tajos = tajos.setdefault('detalle', [])
    conocidos = {tajo['id'] for tajo in detalle_tajos}
    items_con_id = []
    for item in detalle:
        valor_tajo = item.get('tarea_id') or item.get('trabajo')
        tarea_id = _id_tajo(valor_tajo, mapa)
        items_con_id.append((item, tarea_id))
        if tarea_id and tarea_id not in conocidos:
            conocidos.add(tarea_id)
            detalle_tajos.append({
                'id': tarea_id,
                'nombre': item.get('trabajo') or tarea_id,
                'origen': 'revision_sin_confirmar',
                'visto_en': revision,
            })
            cambios['tajos_nuevos'].append(tarea_id)
    if cambios['tajos_nuevos']:
        tajos['aplicables'] = [tajo['id'] for tajo in detalle_tajos]
        tajos.setdefault('_meta', {})['actualizado'] = revision

    estados = ficha.setdefault('estados', {})
    zonas_conocidas = _indice_zonas(ficha)
    for item, tarea_id in items_con_id:
        if not tarea_id:
            continue
        trio = (
            item.get('garaje_id'),
            item.get('planta_id'),
            item.get('zona_id'),
        )
        if trio not in zonas_conocidas:
            referencia = _referencia_zona(trio)
            if referencia not in cambios['zonas_desconocidas']:
                cambios['zonas_desconocidas'].append(referencia)
            continue

        garaje_id, planta_id, zona_id = trio
        clave = f'{garaje_id}__{planta_id}__{tarea_id}__{zona_id}'
        estado_norm = _normalizar_estado(item.get('estado_actual', ''))
        reconocido = estado_norm in MAPA_ESTADO
        if not reconocido and estado_norm:
            if estado_norm not in cambios['estados_no_reconocidos']:
                cambios['estados_no_reconocidos'].append(estado_norm)

        fecha = item.get('ultima_fecha') or revision
        anterior = estados.get(clave)
        if anterior is not None and (not estado_norm or not reconocido):
            anterior['f'] = fecha
            continue

        nuevo = MAPA_ESTADO.get(estado_norm, '?')
        if anterior is None:
            estados[clave] = {'v': nuevo, 'f': fecha, 'r': rev_id}
            cambios['estados_nuevos'] += 1
        elif anterior.get('v') != nuevo:
            cambios['estados_cambiados'].append(
                (clave, anterior.get('v'), nuevo)
            )
            estados[clave] = {'v': nuevo, 'f': fecha, 'r': rev_id}
        else:
            anterior['f'] = fecha
            anterior['r'] = rev_id

    revisiones = ficha.setdefault('revisiones', [])
    if revision and not any(
            registrada.get('id') == rev_id for registrada in revisiones):
        revisiones.append({
            'id': rev_id,
            'fecha': revision,
            'procesada': _ahora(),
            'celdas': len(detalle),
            'cambios': len(cambios['estados_cambiados']),
        })
        cambios['revision_registrada'] = rev_id

    ficha['actualizado'] = _ahora()
    ficha.setdefault('version', VERSION)
    return ficha, cambios


def esta_rancia(ficha, datos):
    """Devuelve un motivo si falta la revisión declarada, o ``None``."""
    revision = datos.get('revision')
    if not revision:
        return None
    revisiones = ficha.get('revisiones') or []
    registradas = {registrada.get('fecha') for registrada in revisiones}
    if revision not in registradas:
        ultima = revisiones[-1].get('fecha') if revisiones else 'ninguna'
        return (
            f'la ficha de garajes no ha registrado la revision {revision}; '
            f'ultima registrada: {ultima}'
        )
    return None


def resumen_cambios(cambios):
    """Devuelve líneas legibles para que ningún cambio o descarte sea mudo."""
    lineas = []
    if cambios.get('apartados_creados'):
        lineas.append(
            'apartados creados: '
            + ', '.join(cambios['apartados_creados'])
        )
    if cambios.get('tajos_nuevos'):
        lineas.append(
            'TAJOS NUEVOS sin confirmar: '
            + ', '.join(cambios['tajos_nuevos'])
        )
    for zona in cambios.get('zonas_desconocidas') or []:
        lineas.append(f'ZONA DESCONOCIDA descartada: {zona}')
    if cambios.get('estados_cambiados'):
        lineas.append(
            'celdas que cambian de estado: %d'
            % len(cambios['estados_cambiados'])
        )
    if cambios.get('estados_nuevos'):
        lineas.append('celdas nuevas: %d' % cambios['estados_nuevos'])
    if cambios.get('estados_no_reconocidos'):
        lineas.append(
            'ESTADOS NO RECONOCIDOS (no bajan estados guardados): '
            + ', '.join(cambios['estados_no_reconocidos'])
        )
    return lineas
