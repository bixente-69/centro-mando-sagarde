# -*- coding: utf-8 -*-
"""Adapta la fase clasificada del flujo de tinta a REVISION_NORMALIZADA.

Este modulo no intenta reconocer tinta ni reconstruir la geometria del PDF.
Parte de los dos sidecars que ya produce el flujo A: ``.candidatas.json``,
con las claves resueltas por :mod:`rejilla_hoja`, y
``.clasificacion.json``, con la letra decidida por una persona o una IA de
vision. Tampoco escribe ningun fichero.

La decision historica se delega en :func:`leer_hoja_marcada.aplicar` y, para
``sin_marca='pendiente'``, en
:func:`leer_hoja_marcada.marcar_no_empezados`. El adaptador solo convierte
esa lectura comprobada al contrato normalizado.
"""
import hashlib
import json
import os
from datetime import datetime

import leer_hoja_marcada
import validar_revision


ORIGEN = 'tinta'
GENERADO_POR = (
    'adaptar_revision_tinta.'
    'construir_revision_normalizada_tinta'
)
SIN_MARCA_VALIDOS = frozenset({'pendiente', 'desconocido'})


def _ruta_candidatas_de_pdf(ruta_pdf):
    """Localiza el sidecar de ``--preparar`` sin crear directorios.

    Desde la norma ``_SISTEMA`` el lector lo guarda debajo de esa carpeta.
    Se conserva como segundo candidato la ubicacion historica junto al PDF,
    exclusivamente para poder leer artefactos anteriores a esa norma.
    """
    carpeta, nombre = os.path.split(ruta_pdf)
    base = os.path.splitext(nombre)[0]
    candidatas = [
        os.path.join(carpeta, '_SISTEMA', base + '.candidatas.json'),
        os.path.join(carpeta, base + '.candidatas.json'),
    ]
    for ruta in candidatas:
        if os.path.isfile(ruta):
            return ruta
    raise FileNotFoundError(
        'no se encontro el sidecar de candidatas preparado para el PDF; '
        'se buscaron: ' + ', '.join(candidatas))


def _cargar_json(ruta, nombre):
    with open(ruta, encoding='utf-8') as fichero:
        datos = json.load(fichero)
    if not isinstance(datos, dict):
        raise ValueError(f'{nombre} debe contener un objeto JSON')
    return datos


def _actualizar_hash_desde_fichero(digest, etiqueta, ruta):
    digest.update(b'\x00fichero\x00')
    digest.update(etiqueta.encode('ascii'))
    digest.update(b'\x00')
    with open(ruta, 'rb') as fichero:
        for bloque in iter(lambda: fichero.read(1024 * 1024), b''):
            digest.update(bloque)


def _generar_revision_id(obra_id, fecha, ruta_pdf, ruta_candidatas,
                         ruta_clasificacion, sin_marca):
    """Identifica todos los insumos capaces de alterar la revision.

    La clasificacion es una entrada humana independiente del PDF. El sidecar
    de candidatas fija tanto las claves geometricas como el alcance de las
    casillas sin marca, y ``sin_marca`` decide si ese alcance se aplica. Por
    eso los tres ficheros y el modo forman parte del hash.
    """
    digest = hashlib.sha256()
    digest.update(b'adaptar_revision_tinta:v1')
    for etiqueta, ruta in (
            ('pdf', ruta_pdf),
            ('candidatas', ruta_candidatas),
            ('clasificacion', ruta_clasificacion)):
        _actualizar_hash_desde_fichero(digest, etiqueta, ruta)
    digest.update(b'\x00sin_marca\x00')
    digest.update(sin_marca.encode('ascii'))
    return f'{obra_id}__{fecha}__{ORIGEN}__{digest.hexdigest()[:8]}'


def construir_revision_normalizada_tinta(
        ruta_pdf, ruta_clasificacion, obra_id, ficha_actual, fecha,
        sin_marca='pendiente'):
    """Construye una revision desde una clasificacion ya terminada.

    No llama a ``preparar`` ni abre el PDF para interpretar sus marcas. El
    ``.candidatas.json`` asociado debe existir, exactamente como en el
    ``--aplicar`` historico. Una clasificacion incompleta, sobrante, invalida
    o dirigida a una celda inexistente produce la misma ``LecturaImposible``
    que :func:`leer_hoja_marcada.aplicar`.
    """
    if not isinstance(fecha, str) or not fecha:
        raise ValueError(
            'la fecha de la revision es obligatoria; no se deduce del PDF')
    if sin_marca not in SIN_MARCA_VALIDOS:
        raise ValueError(
            f'sin_marca debe ser uno de {sorted(SIN_MARCA_VALIDOS)!r}')

    ruta_pdf = os.path.abspath(os.fspath(ruta_pdf))
    ruta_clasificacion = os.path.abspath(os.fspath(ruta_clasificacion))
    ruta_candidatas = _ruta_candidatas_de_pdf(ruta_pdf)

    datos = _cargar_json(ruta_candidatas, 'el sidecar de candidatas')
    datos_clasificacion = _cargar_json(
        ruta_clasificacion, 'la clasificacion')
    clasificacion = datos_clasificacion.get(
        'celdas', datos_clasificacion)
    if not isinstance(clasificacion, dict):
        raise ValueError(
            "la clasificacion debe ser un objeto clave -> valor o contener "
            "un objeto 'celdas'")

    candidatas = datos.get('candidatas') or []
    celdas_hoja = datos.get('celdas_hoja') or []
    revision_id = _generar_revision_id(
        obra_id, fecha, ruta_pdf, ruta_candidatas, ruta_clasificacion,
        sin_marca)

    # Esta llamada es la frontera deliberada del flujo A: comprueba que nada
    # con tinta falte, que no aparezcan claves sin tinta, que el valor sea
    # valido y que cada clave exista en la ficha. No se duplican esas reglas.
    estados, _cambios_explicitos, dudas = leer_hoja_marcada.aplicar(
        ficha_actual, candidatas, clasificacion, fecha, revision_id)

    con_marca = {
        clave for clave, valor in clasificacion.items()
        if valor != leer_hoja_marcada.DESCARTADA
    }
    hoja_usada = any(
        valor not in (leer_hoja_marcada.DESCARTADA, '', None)
        for valor in clasificacion.values()
    )

    cambios_sin_marca = []
    if sin_marca == 'pendiente':
        # La funcion muta solo ``estados``, que ya es la copia devuelta por
        # aplicar(); nunca toca ficha_actual.
        cambios_sin_marca = leer_hoja_marcada.marcar_no_empezados(
            estados, celdas_hoja, con_marca, fecha, revision_id)

    avisos = [
        f'columna sin mapear en candidatas: {columna}'
        for columna in (datos.get('columnas_sin_mapear') or [])
    ]

    celdas = []
    claves_emitidas = set()
    for clave, valor in clasificacion.items():
        if valor == leer_hoja_marcada.DESCARTADA:
            continue
        celdas.append(validar_revision.crear_revision_celda(
            clave, valor, confianza='cierta'))
        claves_emitidas.add(clave)

    if hoja_usada and sin_marca == 'pendiente':
        for clave, _antes, _despues in cambios_sin_marca:
            if clave in claves_emitidas:
                continue
            celdas.append(validar_revision.crear_revision_celda(
                clave, '', confianza='cierta'))
            claves_emitidas.add(clave)
    elif cambios_sin_marca:
        avisos.append(
            f'hoja sin marca real: el camino CLI antiguo habria propuesto '
            f'{len(cambios_sin_marca)} blanco(s) como P; el adaptador no los '
            'emite porque metadata.hoja_usada=false')

    metadata = {
        'generado_por': GENERADO_POR,
        'generado_en': datetime.now().astimezone().isoformat(
            timespec='seconds'),
        'avisos': avisos,
        'hoja_usada': hoja_usada,
        'clasificacion': ruta_clasificacion,
        'candidatas': ruta_candidatas,
        'sin_marca': sin_marca,
        'candidatas_totales': len(candidatas),
        'clasificadas_descartadas': len(dudas),
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
