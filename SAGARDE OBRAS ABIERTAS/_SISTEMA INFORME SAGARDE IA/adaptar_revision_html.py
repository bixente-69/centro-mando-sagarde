# -*- coding: utf-8 -*-
"""Adapta una exportacion HTML a ``REVISION_NORMALIZADA``.

El lector de atributos sigue siendo :mod:`lector_hoja_tajos_html`. Este
modulo solo resuelve los ids publicados por el generador contra la ficha y el
catalogo. No escribe fichas ni conecta el camino HTML con produccion.

Hay dos productores historicos de ids ``src_*`` en ``generar_todos.py``:

* ``crear_registro_revision`` numera portales y plantas en orden natural;
* ``registro_revision_desde_ficha`` los numera en el orden de la estructura.

Se calculan ambos mapas y solo se acepta automaticamente una posicion cuando
los dos coinciden. Si una ficha hace que difieran, el llamador puede aportar
mapas explicitos; sin ellos la clave queda en ``metadata.avisos``. Es una
guarda deliberada contra asignar una marca valida a otra vivienda plausible.
"""
import html
import os
from datetime import datetime

import lector_hoja_tajos_html
import validar_revision
from generar_todos import _clave_natural, _clave_planta, _slug


ORIGEN = 'html_digital'
GENERADO_POR = 'adaptar_revision_html.construir_revision_normalizada_html'

# Traduccion oficial del catalogo corto CAT al id fuente. Es la misma relacion
# declarada por BASE_SOURCE_ID en generador_revisiones.html. No se comparan
# nombres ni se aplican heuristicas: las redacciones no son una clave estable.
TAREA_ID_GENERADOR_A_CATALOGO = {
    'rozas': 'rozas_timbres',
    'mont-elec': 'montante_electrica',
    'mont-telco': 'montante_teleco',
    'mont-sscc': 'montante_sscc',
    'tube-zzcc': 'tubeado_zzcc',
    'cabl-zzcc': 'cableado_zzcc',
    'suelo-rad': 'suelo_radiante',
    'suelo-rec': 'suelo_recrecido',
    'pladur-p': 'perfilado_pladur',
    'pladur-1c': 'primera_cara_pladur',
    'cuad-pres': 'cuadros_presentados',
    'tube-viv': 'tubeado',
    'cabl-elec': 'cableado',
    'telecabl': 'telecableado',
    'pladur-2c': 'segunda_cara_pladur',
    'doblar-caj': 'doblar_cajas',
    'teleembor': 'telembornado',
    'deriv-ind': 'derivacion_individual',
    'cuad-mec': 'cuadro_mecanizado',
    'ct-tec': 'cuarto_tecnico',
    'pint-1': 'pintura_primera',
    'telemec': 'telemecanizado',
    'aguj-zzcc': 'agujeros_iluminacion_zzcc',
    'pint-2': 'pintura_segunda',
    'plac-tapas': 'placas_tapas',
    'fachada': 'fachada_terminada',
    'casquillos': 'casquillos_bombillas',
    'ilum-rell': 'iluminacion_rellanos',
}

# Excepciones historicas minimas documentadas en adaptador_gernika.py:86-90.
# Se incorporaron como codigos cortos al HTML porque esos tajos aun no estaban
# en el vocabulario de Gernika. Sus destinos son ids reales del catalogo.
TAREA_ID_EXCEPCIONES_HISTORICAS = {
    'techos-zzcc': 'techos_zzcc',
    'pint-zzcc': 'pintura_zzcc',
}


def _estructura(ficha_actual):
    if not isinstance(ficha_actual, dict):
        return {}, []
    estructura = ficha_actual.get('estructura') or {}
    return estructura, estructura.get('bloques') or []


def _portales_en_estructura(ficha_actual):
    _, bloques = _estructura(ficha_actual)
    return [
        portal
        for bloque in bloques
        if isinstance(bloque, dict)
        for portal in (bloque.get('portales') or [])
        if isinstance(portal, dict)
    ]


def _ubicaciones(planta):
    return [
        ubicacion for ubicacion in (planta.get('ubicaciones') or [])
        if isinstance(ubicacion, dict) and str(ubicacion.get('id') or '')
    ]


def _plantas_con_ubicaciones(portal):
    return [
        planta for planta in (portal.get('plantas') or [])
        if isinstance(planta, dict) and _ubicaciones(planta)
    ]


def _referencia_portal(portal):
    return (portal.get('referencia') or portal.get('nombre')
            or portal.get('id') or '')


def _referencia_planta(planta):
    return planta.get('nombre') or planta.get('id') or ''


def _id_real(valor):
    """Devuelve ids de portal/planta con el contrato minusculo del validador."""
    return str(valor or '').lower()


def _mapas_orden_natural(obra_id, ficha_actual):
    """Reproduce la numeracion de ``crear_registro_revision``."""
    slug = _slug(obra_id)
    portales = [
        portal for portal in _portales_en_estructura(ficha_actual)
        if _plantas_con_ubicaciones(portal)
    ]
    portales.sort(key=lambda portal: _clave_natural(_referencia_portal(portal)))

    mapa_portales = {}
    mapa_plantas = {}
    for indice_portal, portal in enumerate(portales, 1):
        portal_html = f'src_{slug}_p{indice_portal}'
        mapa_portales[portal_html] = _id_real(portal.get('id'))
        plantas = sorted(
            _plantas_con_ubicaciones(portal),
            key=lambda planta: _clave_planta(_referencia_planta(planta)),
        )
        for indice_planta, planta in enumerate(plantas, 1):
            mapa_plantas[f'{portal_html}_f{indice_planta}'] = _id_real(
                planta.get('id'))
    return mapa_portales, mapa_plantas


def _mapas_orden_estructura(obra_id, ficha_actual):
    """Reproduce la numeracion de ``registro_revision_desde_ficha``."""
    slug = _slug(obra_id)
    mapa_portales = {}
    mapa_plantas = {}
    indice_portal = 0
    for portal in _portales_en_estructura(ficha_actual):
        indice_portal += 1
        portal_html = f'src_{slug}_p{indice_portal}'
        hay_plantas = False
        for indice_planta, planta in enumerate(portal.get('plantas') or [], 1):
            if not isinstance(planta, dict) or not _ubicaciones(planta):
                continue
            hay_plantas = True
            mapa_plantas[f'{portal_html}_f{indice_planta}'] = _id_real(
                planta.get('id'))
        if hay_plantas:
            mapa_portales[portal_html] = _id_real(portal.get('id'))
    return mapa_portales, mapa_plantas


def _combinar_mapas_seguros(mapa_natural, mapa_estructura):
    """Separa traducciones inequívocas y posiciones con destinos distintos."""
    seguros = {}
    ambiguos = {}
    for clave in set(mapa_natural) | set(mapa_estructura):
        destinos = {
            mapa[clave] for mapa in (mapa_natural, mapa_estructura)
            if clave in mapa and mapa[clave]
        }
        if len(destinos) == 1:
            seguros[clave] = destinos.pop()
        elif destinos:
            ambiguos[clave] = sorted(destinos)
    return seguros, ambiguos


def derivar_mapas_ubicacion(obra_id, ficha_actual):
    """Deriva mapas ``src_*`` seguros y sus posibles ambiguedades.

    Devuelve ``(portales, plantas, ambiguos_portal, ambiguos_planta)``. Las
    funciones de orden se importan de ``generar_todos.py``; no hay una tercera
    implementacion local del criterio de orden.
    """
    natural_portales, natural_plantas = _mapas_orden_natural(
        obra_id, ficha_actual)
    orden_portales, orden_plantas = _mapas_orden_estructura(
        obra_id, ficha_actual)
    portales, ambiguos_portal = _combinar_mapas_seguros(
        natural_portales, orden_portales)
    plantas, ambiguos_planta = _combinar_mapas_seguros(
        natural_plantas, orden_plantas)
    return portales, plantas, ambiguos_portal, ambiguos_planta


def derivar_mapa_tareas(obra_id, catalogo, tarea_id_a_real=None):
    """Deriva ids HTML -> ids reales mediante relaciones exactas conocidas."""
    ids_validos = validar_revision._ids_tajos(catalogo, obra_id)
    mapa = {tajo_id: tajo_id for tajo_id in ids_validos}
    traducciones = dict(TAREA_ID_GENERADOR_A_CATALOGO)
    traducciones.update(TAREA_ID_EXCEPCIONES_HISTORICAS)
    for tarea_html, tarea_real in traducciones.items():
        if tarea_real in ids_validos:
            mapa[tarea_html] = tarea_real
    for tarea_html, tarea_real in (tarea_id_a_real or {}).items():
        if tarea_real in ids_validos:
            mapa[str(tarea_html)] = tarea_real
    return mapa


def _indice_plantas(ficha_actual):
    indice = {}
    for portal in _portales_en_estructura(ficha_actual):
        portal_id = _id_real(portal.get('id'))
        for planta in portal.get('plantas') or []:
            if isinstance(planta, dict):
                indice[(portal_id, _id_real(planta.get('id')))] = planta
    return indice


def _resolver_unidad(ficha_actual, portal_id, planta_id, unidad_html):
    """Resuelve el alias impreso por la hoja al id canonico de vivienda."""
    estructura, _ = _estructura(ficha_actual)
    planta = _indice_plantas(ficha_actual).get((portal_id, planta_id))
    if planta is None:
        return None, 'la planta no pertenece al portal traducido'

    aliases = estructura.get('alias_historico') or {}
    coincidencias = []
    for ubicacion in _ubicaciones(planta):
        ubicacion_id = str(ubicacion.get('id'))
        clave_alias = f'{portal_id}__{planta_id}__{ubicacion_id}'
        unidad_exportada = str(aliases.get(clave_alias, ubicacion_id))
        if unidad_html in {ubicacion_id, unidad_exportada}:
            coincidencias.append(ubicacion_id)
    coincidencias = list(dict.fromkeys(coincidencias))
    if len(coincidencias) == 1:
        return coincidencias[0], None
    if len(coincidencias) > 1:
        return None, 'el alias de vivienda coincide con varias ubicaciones'
    return None, 'vivienda desconocida en la planta traducida'


def _fecha_html(ruta_html):
    # Se reutiliza exactamente el extractor empleado por
    # listar_revisiones_html; no se mantiene una segunda regex DDMMAAAA.
    _, fecha = lector_hoja_tajos_html._fecha_desde_nombre(
        os.path.basename(ruta_html))
    if fecha is None:
        raise ValueError(
            'el nombre del HTML no contiene una fecha DDMMAAAA valida')
    return fecha


def _aviso_clave(data_k, motivo):
    return f'clave HTML sin resolver {data_k!r}: {motivo}'


def construir_revision_normalizada_html(
        ruta_html, obra_id, ficha_actual, catalogo,
        portal_id_a_real=None, planta_id_a_real=None,
        tarea_id_a_real=None, fecha=None):
    """Construye una ``REVISION_NORMALIZADA`` desde un HTML exportado.

    Los tres mapas opcionales son traducciones explicitas ``id HTML -> id
    real``. Solo son necesarios si una obra historica no permite una
    derivacion inequivoca. ``fecha`` permite que el CLI conserve su argumento
    ``--fecha`` como autoridad; si se omite, se mantiene el comportamiento de
    historiales y se extrae del nombre. Las claves no resueltas se omiten como
    celdas y se conservan en ``metadata.avisos``; nunca bloquean las demas.
    """
    ruta_html = os.path.abspath(os.fspath(ruta_html))
    if fecha is None:
        fecha = _fecha_html(ruta_html)
    elif not isinstance(fecha, str) or not fecha:
        raise ValueError('la fecha explicita del HTML debe ser un texto no vacio')
    (mapa_portales, mapa_plantas,
     ambiguos_portal, ambiguos_planta) = derivar_mapas_ubicacion(
         obra_id, ficha_actual)
    mapa_portales.update({
        str(clave): _id_real(valor)
        for clave, valor in (portal_id_a_real or {}).items()
    })
    mapa_plantas.update({
        str(clave): _id_real(valor)
        for clave, valor in (planta_id_a_real or {}).items()
    })
    mapa_tareas = derivar_mapa_tareas(
        obra_id, catalogo, tarea_id_a_real=tarea_id_a_real)

    celdas = []
    avisos = []
    for data_k_crudo, data_st_crudo in lector_hoja_tajos_html.extraer_pares(
            ruta_html):
        data_k = html.unescape(data_k_crudo)
        estado = html.unescape(data_st_crudo)
        partes = data_k.split('__')
        if len(partes) != 4 or not all(partes):
            avisos.append(_aviso_clave(
                data_k, 'se esperaban cuatro segmentos no vacios'))
            continue
        if estado not in validar_revision.ALFABETOS_HOJA[ORIGEN]:
            avisos.append(_aviso_clave(
                data_k, f'estado HTML desconocido {estado!r}'))
            continue

        portal_html, planta_html, tarea_html, unidad_html = partes
        portal_id = mapa_portales.get(portal_html)
        if portal_id is None:
            if portal_html in ambiguos_portal:
                motivo = ('portal ambiguo entre '
                          f'{ambiguos_portal[portal_html]!r}; requiere mapa explicito')
            else:
                motivo = f'portal desconocido {portal_html!r}'
            avisos.append(_aviso_clave(data_k, motivo))
            continue

        planta_id = mapa_plantas.get(planta_html)
        if planta_id is None:
            if planta_html in ambiguos_planta:
                motivo = ('planta ambigua entre '
                          f'{ambiguos_planta[planta_html]!r}; requiere mapa explicito')
            else:
                motivo = f'planta desconocida {planta_html!r}'
            avisos.append(_aviso_clave(data_k, motivo))
            continue

        tarea_id = mapa_tareas.get(tarea_html)
        if tarea_id is None:
            avisos.append(_aviso_clave(
                data_k, f'tajo desconocido {tarea_html!r}'))
            continue

        unidad_id, error_unidad = _resolver_unidad(
            ficha_actual, portal_id, planta_id, unidad_html)
        if error_unidad:
            avisos.append(_aviso_clave(data_k, error_unidad))
            continue

        celdas.append(validar_revision.crear_revision_celda(
            f'{portal_id}__{planta_id}__{tarea_id}__{unidad_id}',
            estado,
            confianza='cierta',
        ))

    revision_id = validar_revision.generar_revision_id(
        obra_id, fecha, ORIGEN, ruta_html)
    metadata = {
        'generado_por': GENERADO_POR,
        'generado_en': datetime.now().astimezone().isoformat(timespec='seconds'),
        'avisos': avisos,
        'hoja_usada': True,
    }
    return validar_revision.crear_revision_normalizada(
        revision_id=revision_id,
        obra=obra_id,
        fecha=fecha,
        origen=ORIGEN,
        fuente=ruta_html,
        celdas=celdas,
        metadata=metadata,
    )
