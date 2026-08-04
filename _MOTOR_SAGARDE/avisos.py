# -*- coding: utf-8 -*-
"""Reglas comunes de vigencia de los avisos del Centro de Mando."""
from datetime import datetime

# Un aviso con 400 días de antigüedad ya no es accionable y deja de mostrarse.
DIAS_CADUCIDAD_AVISO = 400


def dias_desde_timestamp(timestamp, ahora=None):
    """Edad en días naturales, igual en portal, auditoría y mantenimientos."""
    if not timestamp:
        return None
    ahora = ahora or datetime.now()
    return (ahora.date() - datetime.fromtimestamp(timestamp).date()).days


def aviso_caducado(dias):
    """Devuelve True desde el día 400 inclusive."""
    return dias is not None and dias >= DIAS_CADUCIDAD_AVISO


def es_aviso_por_antiguedad(dias, desde_dias):
    """Visible sólo después del umbral inicial y antes de cumplir 400 días."""
    return (
        dias is not None
        and dias > desde_dias
        and not aviso_caducado(dias)
    )
