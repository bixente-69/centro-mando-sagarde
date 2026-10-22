# -*- coding: utf-8 -*-
"""Reglas comunes de vigencia de los avisos del Centro de Mando."""
from datetime import datetime

# Un aviso con 400 días de antigüedad ya no es accionable y deja de mostrarse.
DIAS_CADUCIDAD_AVISO = 400


# Contratos de mantenimiento a los que NO se avisa de inactividad. Nombre tal
# como lo muestra el portal (sin el prefijo "MANTENIMIENTO ") -> motivo corto,
# que el indice de mantenimientos escribe en la tarjeta: el aviso queda apagado
# a proposito y a la vista, no oculto. Lo leen el portal, la auditoria y ese
# indice. Quitar la entrada para volver a avisar. Una prueba comprueba que cada
# nombre casa con una carpeta real: uno mal escrito no apagaria nada.
#   OBRAMAT: Bixente, 22/10/2026 -- han rescindido el contrato de mantenimiento,
#   ya no habra mas partes. Mantener hasta que Bixente diga lo contrario.
CONTRATOS_SIN_AVISO_INACTIVIDAD = {
    "OBRAMAT": "contrato rescindido",
}


def _clave_contrato(nombre):
    return " ".join(str(nombre or "").split()).upper()


def motivo_sin_aviso(nombre):
    """Motivo por el que el contrato no avisa de inactividad, o None."""
    clave = _clave_contrato(nombre)
    for declarado, motivo in CONTRATOS_SIN_AVISO_INACTIVIDAD.items():
        if _clave_contrato(declarado) == clave:
            return motivo
    return None


def contrato_sin_aviso(nombre):
    """True si el contrato esta declarado sin aviso de inactividad."""
    return motivo_sin_aviso(nombre) is not None


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
