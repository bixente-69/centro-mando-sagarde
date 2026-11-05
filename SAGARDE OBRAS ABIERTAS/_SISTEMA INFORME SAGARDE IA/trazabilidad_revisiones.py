# -*- coding: utf-8 -*-
"""Registro comun, aditivo y no bloqueante de revisiones aplicadas.

El log complementa los sidecars y ``ficha_obra.json``. Nunca los sustituye y
un fallo al registrar la traza no invalida una ficha que el llamador ya haya
guardado.
"""
import json
import os
from datetime import datetime


NOMBRE_LOG = 'revisiones_aplicadas.jsonl'


def ruta_log_obra(carpeta_obra):
    """Ruta convencional del log dentro de una carpeta de obra."""
    return os.path.join(
        os.fspath(carpeta_obra), 'INFORME SAGARDE IA', NOMBRE_LOG)


def _transiciones(resultado_aplicacion, resumen):
    """Celdas que cambian de estado, como ``[clave, antes, despues]``.

    ``None`` significa "no se sabe" (no hay detalle, o el detalle no cuadra
    con el resumen): nunca una lista vacia, que diria "no cambio nada".
    """
    aceptadas = resultado_aplicacion.get('aceptadas')
    if not isinstance(aceptadas, list):
        return None
    cambios = [[c['clave'], c.get('antes'), c.get('despues')]
               for c in aceptadas if c.get('accion') == 'actualizar']
    if len(cambios) != resumen.get('cambios', 0):
        return None
    return cambios


def _entrada(revision, resultado_aplicacion, salvaguarda_coincidio,
             celdas_comparadas):
    if not isinstance(revision, dict):
        raise TypeError('revision debe ser un dict')
    if not isinstance(resultado_aplicacion, dict):
        raise TypeError('resultado_aplicacion debe ser un dict')
    if not resultado_aplicacion.get('escrito'):
        raise ValueError('el resultado no corresponde a una aplicacion escrita')
    if salvaguarda_coincidio is not None and not isinstance(
            salvaguarda_coincidio, bool):
        raise TypeError(
            'salvaguarda_coincidio debe ser bool, o None si no hubo '
            'comprobacion cruzada que hacer (p.ej. --digital sin PDF real)')

    resumen = resultado_aplicacion.get('resumen') or {}
    metadata = revision.get('metadata') or {}
    return {
        'version': 1,
        'revision_id': revision['revision_id'],
        'obra': revision['obra'],
        'fecha': revision['fecha'],
        'origen': revision['origen'],
        'fuente': revision['fuente'],
        'generado_por': metadata.get('generado_por'),
        'generado_en': metadata.get('generado_en'),
        'celdas_cambiadas': resumen.get('cambios', 0),
        'transiciones': _transiciones(resultado_aplicacion, resumen),
        'celdas_conservadas': resumen.get('sin_cambio', 0),
        'celdas_descartadas': resumen.get('descartadas', 0),
        'celdas_rechazadas': resumen.get('rechazadas', 0),
        'aplicado_en': datetime.now().astimezone().isoformat(timespec='seconds'),
        'salvaguarda_doble_calculo_coincidio': salvaguarda_coincidio,
        'celdas_comparadas_salvaguarda': celdas_comparadas,
    }


def _anadir_jsonl(ruta_log, entrada):
    linea = json.dumps(
        entrada, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    # La carpeta INFORME SAGARDE IA ya existe cuando se guarda la ficha. No se
    # crea aqui: una ruta equivocada debe avisar, no fabricar otro arbol.
    with open(ruta_log, 'a', encoding='utf-8', newline='\n') as fichero:
        fichero.write(linea + '\n')


def registrar_trazabilidad(resultado_aplicacion, ruta_log, *, revision,
                            salvaguarda_coincidio,
                            celdas_comparadas=None):
    """Anade una entrada JSONL y devuelve si pudo hacerlo.

    La funcion es deliberadamente no bloqueante: captura cualquier fallo de
    preparacion o escritura, lo muestra en consola y devuelve ``False``. Los
    llamadores la invocan despues de guardar la ficha real, de modo que esta
    traza complementaria nunca bloquea ni revierte el dato validado.
    """
    try:
        entrada = _entrada(
            revision, resultado_aplicacion, salvaguarda_coincidio,
            celdas_comparadas)
        _anadir_jsonl(ruta_log, entrada)
    except Exception as exc:
        print(
            f'[AVISO TRAZABILIDAD] no se pudo registrar {ruta_log} '
            f'({type(exc).__name__}: {exc}). La ficha ya guardada se conserva.')
        return False
    return True
