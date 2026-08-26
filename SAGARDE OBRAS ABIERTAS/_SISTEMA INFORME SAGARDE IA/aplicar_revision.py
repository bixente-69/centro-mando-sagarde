# -*- coding: utf-8 -*-
"""Aplicacion pura, en memoria, de una revision normalizada.

Este modulo no persiste fichas ni mantiene trazabilidad. La unica mutacion que
realiza es sobre una copia profunda de ``ficha_actual``, y solo cuando la
revision completa es aplicable y se solicita ``dry_run=False``.
"""
import copy

import validar_revision


def apply_revision(revision, ficha_actual, catalogo, dry_run=True):
    """Valida y, si procede, devuelve una ficha actualizada en memoria.

    El resultado conserva todos los campos producidos por
    :func:`validar_revision.validar` y agrega ``escrito``. Cuando ``escrito``
    es verdadero, ``ficha_actualizada`` contiene una copia profunda de la
    ficha con las acciones ``actualizar`` aplicadas. El nombre ``escrito`` se
    refiere exclusivamente a esa copia en memoria; esta funcion nunca escribe
    en disco.
    """
    resultado = validar_revision.validar(revision, ficha_actual, catalogo)
    resultado['escrito'] = False

    if dry_run or not resultado['aplicable']:
        return resultado

    ficha_actualizada = copy.deepcopy(ficha_actual)
    estados = ficha_actualizada.get('estados')
    if estados is None:
        estados = {}
        ficha_actualizada['estados'] = estados

    for celda in resultado['aceptadas']:
        if celda['accion'] != 'actualizar':
            continue
        estados[celda['clave']] = {
            'v': celda['despues'],
            'f': revision['fecha'],
            'r': revision['revision_id'],
        }

    resultado['escrito'] = True
    resultado['ficha_actualizada'] = ficha_actualizada
    return resultado
