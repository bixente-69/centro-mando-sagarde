# -*- coding: utf-8 -*-
"""Contrato compartido para las claves de correcciones manuales.

La clave tiene cuatro tramos: ``portal__planta__tajo__unidad``. El extractor
PDF puede partir nombres estrechos como ``PORTAL`` y devolver ``PORT AL``;
todas las capas deben normalizarlo igual para no perder la marca manuscrita.
"""
import re

TRAMOS = 4
SEPARADOR = '__'


def normalizar_unidad(unidad):
    """Quita espacios introducidos por el extractor dentro de la unidad."""
    return re.sub(r'\s+', '', str(unidad or ''))


def partir_clave(clave):
    """Devuelve los cuatro tramos normalizados o ``None`` si está mal formada."""
    tramos = str(clave or '').split(SEPARADOR)
    if len(tramos) != TRAMOS:
        return None
    portal, planta, tajo, unidad = tramos
    return portal, planta, tajo, normalizar_unidad(unidad)
