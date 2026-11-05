# -*- coding: utf-8 -*-
"""Que ha cambiado entre la revision anterior y la ultima (P1, sesion 1).

Lee el log ``revisiones_aplicadas.jsonl`` (campo ``transiciones``, que guarda
``trazabilidad_revisiones``). Es de solo lectura y no toca la ficha.

Reglas del proyecto que cumple:
  * Una entrada antigua sin ``transiciones`` es DESCONOCIDO (``conocido``
    False), nunca "0 cambios".
  * Una lista vacia guardada SI es "0 cambios" conocido.
  * ``historial_consolidado`` no es una revision de campo: no cuenta.
  * Una misma revision reaplicada (sin cambios la segunda vez) no borra las
    transiciones de la primera: se agrupa por ``revision_id``.
"""
import json
import os
from datetime import datetime

ORIGEN_NO_CAMPO = 'historial_consolidado'
# Peso de cada estado medido. '?' y 'N' quedan fuera: ni suben ni bajan.
_PESO = {'P': 0, '/': 1, 'M': 2, 'X': 3}


def _fecha(texto):
    try:
        return datetime.strptime(texto, '%d/%m/%Y')
    except (TypeError, ValueError):
        return datetime.min


def _leer_log(ruta):
    ruta = os.fspath(ruta)
    if not os.path.isfile(ruta):
        return []
    entradas = []
    with open(ruta, encoding='utf-8') as fichero:
        for linea in fichero:
            if linea.strip():
                entradas.append(json.loads(linea))
    return entradas


def ultima_revision(ruta_log, fechas_previas=None):
    """Ultima revision de campo del log, con sus transiciones unidas.

    Devuelve ``None`` si no hay ninguna. Si ninguna entrada de esa revision
    trae ``transiciones``, ``conocido`` es False y ``transiciones`` None.

    ``fecha_anterior`` es la fecha de la revision de campo inmediatamente
    anterior (del log y de ``fechas_previas``, p. ej. las de
    ``ficha['revisiones']``, que cubren las anteriores al log). ``None`` si no
    hay ninguna: nunca se inventa.
    """
    grupos = {}
    for e in _leer_log(ruta_log):
        if e.get('origen') == ORIGEN_NO_CAMPO:
            continue
        g = grupos.setdefault(e['revision_id'], {
            'revision_id': e['revision_id'], 'fecha': e.get('fecha'),
            'origen': e.get('origen'), 'conocido': False,
            'transiciones': None, 'celdas_cambiadas_sin_detalle': 0})
        if isinstance(e.get('transiciones'), list):
            g['conocido'] = True
            g['transiciones'] = (g['transiciones'] or []) + e['transiciones']
        g['celdas_cambiadas_sin_detalle'] = max(
            g['celdas_cambiadas_sin_detalle'], e.get('celdas_cambiadas', 0))
    if not grupos:
        return None
    ultima = max(grupos.values(), key=lambda g: _fecha(g['fecha']))
    candidatas = [g['fecha'] for g in grupos.values()] + list(fechas_previas or [])
    anteriores = [f for f in candidatas
                  if _fecha(f) != datetime.min
                  and _fecha(f) < _fecha(ultima['fecha'])]
    ultima['fecha_anterior'] = (
        max(anteriores, key=_fecha) if anteriores else None)
    return ultima


def resumir_transiciones(transiciones):
    """Cuenta subidas, bajadas y reparto por tajo y planta."""
    if transiciones is None:
        return {'conocido': False}
    a_estado, por_tajo, por_planta, bajan = {}, {}, {}, []
    for clave, antes, despues in transiciones:
        partes = clave.split('__', 3)
        portal, planta, tajo = partes[0], partes[1], partes[2]
        a_estado[despues] = a_estado.get(despues, 0) + 1
        por_tajo[tajo] = por_tajo.get(tajo, 0) + 1
        por_planta[(portal, planta)] = por_planta.get((portal, planta), 0) + 1
        if (antes in _PESO and despues in _PESO
                and _PESO[despues] < _PESO[antes]):
            bajan.append([clave, antes, despues])
    return {'conocido': True, 'total': len(transiciones),
            'a_estado': a_estado, 'por_tajo': por_tajo,
            'por_planta': por_planta, 'bajan': bajan}


def _nombres_plantas(ficha):
    nombres = {}
    for bloque in (ficha.get('estructura') or {}).get('bloques') or []:
        for portal in bloque.get('portales') or []:
            for planta in portal.get('plantas') or []:
                nombres[(portal.get('id'), planta.get('id'))] = (
                    f"{portal.get('nombre') or portal.get('id')} · "
                    f"{planta.get('nombre') or planta.get('id')}")
    return nombres


def preparar_para_panel(ruta_log, ficha, tajos_catalogo):
    """Todo lo que la pestaña «Cambios» necesita, o ``None`` si no hay log.

    ``ficha`` aporta las fechas de revisiones anteriores al log y los nombres
    de portal y planta; ``tajos_catalogo`` es la lista ``tajos`` del catalogo.
    """
    fechas_ficha = [r.get('fecha') for r in (ficha.get('revisiones') or [])
                    if r.get('fecha')]
    ultima = ultima_revision(ruta_log, fechas_previas=fechas_ficha)
    if ultima is None:
        return None
    return {
        'revision': ultima,
        'resumen': resumir_transiciones(ultima['transiciones']),
        'nombres_tajo': {t['id']: t.get('nombre', t['id'])
                         for t in tajos_catalogo or []},
        'nombres_planta': _nombres_plantas(ficha),
    }
