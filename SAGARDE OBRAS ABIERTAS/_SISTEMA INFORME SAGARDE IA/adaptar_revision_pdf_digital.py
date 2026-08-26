# -*- coding: utf-8 -*-
"""Adapta un PDF digital a ``REVISION_NORMALIZADA``.

La lectura del texto impreso y toda su geometria pertenecen a
:mod:`leer_hoja_marcada`. Este modulo se limita a envolver el resultado de
``estados_impresos``; no interpreta paginas, columnas, filas ni coordenadas y
no escribe ningun fichero de obra.
"""
import os
from datetime import datetime

import leer_hoja_marcada
import validar_revision


ORIGEN = 'pdf_digital'
GENERADO_POR = (
    'adaptar_revision_pdf_digital.'
    'construir_revision_normalizada_pdf_digital'
)


def construir_revision_normalizada_pdf_digital(
        ruta_pdf, obra_id, ficha_actual, fecha):
    """Construye una revision normalizada desde texto impreso en un PDF.

    ``fecha`` es obligatoria y procede siempre del llamador. En particular,
    no se intenta deducir del nombre del PDF ni de la fecha de su cabecera.

    ``estados_impresos`` ya resuelve por geometria las claves de ficha y solo
    devuelve las celdas que contienen una marca explicita. Se conserva cada
    par tal cual como una ``REVISION_CELDA`` de confianza cierta.
    """
    if not isinstance(fecha, str) or not fecha:
        raise ValueError(
            'la fecha de la revision es obligatoria; no se deduce del PDF')

    ruta_pdf = os.path.abspath(os.fspath(ruta_pdf))
    # El argumento ``obra`` de estados_impresos no se usa hoy para resolver
    # geometria, pero se mantiene su contrato de tres argumentos y se le pasa
    # el id explicito sin acoplar este adaptador al registro de produccion.
    impresos = leer_hoja_marcada.estados_impresos(
        ruta_pdf, {'id': obra_id}, ficha_actual)

    celdas = [
        validar_revision.crear_revision_celda(
            clave, estado, confianza='cierta')
        for clave, estado in impresos.items()
    ]
    # Es exactamente el criterio de marca explicita del lector actual: los
    # unicos glifos que estados_impresos considera impresos son X, M y /.
    hoja_usada = any(
        estado in leer_hoja_marcada.VALIDOS_IMPRESOS
        for estado in impresos.values()
    )

    revision_id = validar_revision.generar_revision_id(
        obra_id, fecha, ORIGEN, ruta_pdf)
    metadata = {
        'generado_por': GENERADO_POR,
        'generado_en': datetime.now().astimezone().isoformat(
            timespec='seconds'),
        'avisos': [],
        'hoja_usada': hoja_usada,
    }
    return validar_revision.crear_revision_normalizada(
        revision_id=revision_id,
        obra=obra_id,
        fecha=fecha,
        origen=ORIGEN,
        fuente=ruta_pdf,
        celdas=celdas,
        metadata=metadata,
    )
