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


def derivar_mapa_tareas(obra_id, catalogo, tarea_id_a_real=None,
                        ficha_actual=None):
    """Deriva ids HTML -> ids reales mediante relaciones exactas conocidas.

    Con `ficha_actual`, tambien son validos los tajos que la propia ficha
    declara aunque el catalogo ya no los tenga (ver
    `validar_revision.ids_tajos_de_la_obra`): la hoja que los ofrecio tiene
    que poder volver a la base."""
    ids_validos = validar_revision.ids_tajos_de_la_obra(
        catalogo, obra_id, ficha_actual)
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


def estructura_nueva_en_hoja(
        ruta_html, obra_id, ficha_actual, catalogo=None,
        tarea_id_a_real=None):
    """Lista ubicaciones residenciales impresas que la ficha aun no conoce.

    Solo se aceptan portales y plantas que los mapas seguros existentes
    resuelven sin ambiguedad. Las zonas especiales quedan fuera: su alta
    requiere un tipo y un nombre que una celda HTML no declara. Cada alta
    incluye exactamente los tajos que la hoja imprime para esa unidad,
    traducidos con el mismo mapa exacto que usa el adaptador de revision.
    """
    ruta_html = os.path.abspath(os.fspath(ruta_html))
    if catalogo is None:
        catalogo = validar_revision.cargar_catalogo_tajos()
    (mapa_portales, mapa_plantas,
     ambiguos_portal, ambiguos_planta) = derivar_mapas_ubicacion(
         obra_id, ficha_actual)
    mapa_tareas = derivar_mapa_tareas(
        obra_id, catalogo, tarea_id_a_real=tarea_id_a_real,
        ficha_actual=ficha_actual)
    plantas = _indice_plantas(ficha_actual)
    portales = {
        _id_real(portal.get('id')): portal
        for portal in _portales_en_estructura(ficha_actual)
    }

    nuevas = {}
    for data_k_crudo, _ in lector_hoja_tajos_html.extraer_pares(ruta_html):
        data_k = html.unescape(data_k_crudo)
        partes = data_k.split('__')
        if len(partes) != 4 or not all(partes):
            continue
        portal_html, planta_html, tarea_html, unidad_html = partes
        if planta_html == 'zesp':
            continue
        if portal_html in ambiguos_portal or planta_html in ambiguos_planta:
            continue
        portal_id = mapa_portales.get(portal_html)
        planta_id = mapa_plantas.get(planta_html)
        if portal_id is None or planta_id is None:
            continue
        portal = portales.get(portal_id)
        planta = plantas.get((portal_id, planta_id))
        if portal is None or planta is None:
            continue

        _, error_unidad = _resolver_unidad(
            ficha_actual, portal_id, planta_id, unidad_html)
        if error_unidad != 'vivienda desconocida en la planta traducida':
            continue

        clave = (portal_id, planta_id, unidad_html)
        nueva = nuevas.setdefault(clave, {
            'edificio': _referencia_portal(portal),
            'planta': _referencia_planta(planta),
            'planta_id': planta_id,
            'portal_id': portal_id,
            'unidad': unidad_html,
            'tajos': [],
            'tajos_sin_traducir': [],
        })
        tarea_id = mapa_tareas.get(tarea_html)
        destino = ('tajos' if tarea_id is not None
                   else 'tajos_sin_traducir')
        valor = tarea_id if tarea_id is not None else tarea_html
        if valor not in nueva[destino]:
            nueva[destino].append(valor)

    return sorted(nuevas.values(), key=lambda item: (
        _clave_natural(item['edificio']),
        _clave_planta(item['planta']),
        _clave_natural(item['unidad']),
        item['portal_id'], item['planta_id'], item['unidad'],
    ))


def estructura_ausente_en_hoja(ruta_html, obra_id, ficha_actual, catalogo,
                               fecha=None):
    """Ubicaciones y tajos que la ficha tiene y la hoja ya NO imprime.

    Norma de Bixente (04/10/2026): la ULTIMA hoja manda, tambien para quitar.
    Una vivienda que desaparece de la hoja no existe (Olabeaga, PB del portal
    3); un tajo que la hoja no imprime para una unidad no aplica a ella
    (alumbrado temporizado en recintos).

    Solo se compara dentro de los portales que la hoja imprime (una hoja que
    no cubre un portal entero no lo borra) y solo si TODA clave de la hoja se
    ha podido resolver: con una clave sin resolver una unidad podria parecer
    ausente por un alias no entendido, y quitarla seria perder datos. En ese
    caso se devuelve ``no_fiable`` con el motivo y no se propone quitar nada.
    No modifica nada.
    """
    revision = construir_revision_normalizada_html(
        ruta_html, obra_id, ficha_actual, catalogo, sin_marca='pendiente',
        fecha=fecha)
    ausentes = {'unidades': [], 'tajos': [], 'no_fiable': None}
    if revision['metadata']['avisos']:
        ausentes['no_fiable'] = (
            f"{len(revision['metadata']['avisos'])} clave(s) de la hoja sin "
            'resolver: no se retira nada de la base')
        return ausentes

    impresas = set()
    unidades_impresas = set()
    portales_cubiertos = set()
    for celda in revision['celdas']:
        portal, planta, _tajo, unidad = celda['clave'].split('__')
        impresas.add(celda['clave'])
        unidades_impresas.add((portal, planta, unidad))
        portales_cubiertos.add(portal)

    estados = ficha_actual.get('estados') or {}
    for portal in _portales_en_estructura(ficha_actual):
        portal_id = _id_real(portal.get('id'))
        if portal_id not in portales_cubiertos:
            continue
        for planta in portal.get('plantas') or []:
            if not isinstance(planta, dict):
                continue
            planta_id = _id_real(planta.get('id'))
            for ubicacion in _ubicaciones(planta):
                unidad = str(ubicacion.get('id'))
                prefijo = f'{portal_id}__{planta_id}__'
                sufijo = f'__{unidad}'
                celdas = {
                    clave: (valor or {}).get('v')
                    for clave, valor in estados.items()
                    if clave.startswith(prefijo) and clave.endswith(sufijo)
                    and len(clave.split('__')) == 4
                }
                if (portal_id, planta_id, unidad) not in unidades_impresas:
                    ausentes['unidades'].append({
                        'portal_id': portal_id, 'planta_id': planta_id,
                        'unidad': unidad,
                        'edificio': _referencia_portal(portal),
                        'planta': _referencia_planta(planta),
                        'tipo': ubicacion.get('tipo'),
                        'nombre': ubicacion.get('nombre'),
                        'celdas': celdas,
                    })
                    continue
                for clave, estado in sorted(celdas.items()):
                    if clave not in impresas:
                        ausentes['tajos'].append({
                            'portal_id': portal_id, 'planta_id': planta_id,
                            'unidad': unidad, 'tajo': clave.split('__')[2],
                            'clave': clave, 'estado': estado})
    return ausentes


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


def _aviso_clave_no_resuelta(data_k, motivo, estado):
    aviso = _aviso_clave(data_k, motivo)
    if estado in ('X', 'M', '/', 'N'):
        return 'MARCA SIN APLICAR: ' + aviso
    return aviso


def construir_revision_normalizada_html(
        ruta_html, obra_id, ficha_actual, catalogo,
        portal_id_a_real=None, planta_id_a_real=None,
        tarea_id_a_real=None, fecha=None, sin_marca='pendiente'):
    """Construye una ``REVISION_NORMALIZADA`` desde un HTML exportado.

    Los tres mapas opcionales son traducciones explicitas ``id HTML -> id
    real``. Solo son necesarios si una obra historica no permite una
    derivacion inequivoca. ``fecha`` permite que el CLI conserve su argumento
    ``--fecha`` como autoridad; si se omite, se mantiene el comportamiento de
    historiales y se extrae del nombre. Las claves no resueltas se omiten como
    celdas y se conservan en ``metadata.avisos``; nunca bloquean las demas.
    ``sin_marca='pendiente'`` conserva los blancos para que una hoja usada los
    traduzca a P; ``sin_marca='desconocido'`` no los emite.
    """
    if sin_marca not in ('pendiente', 'desconocido'):
        raise ValueError("sin_marca debe ser 'pendiente' o 'desconocido'")
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
        obra_id, catalogo, tarea_id_a_real=tarea_id_a_real,
        ficha_actual=ficha_actual)

    celdas = []
    avisos = []
    for data_k_crudo, data_st_crudo in lector_hoja_tajos_html.extraer_pares(
            ruta_html):
        data_k = html.unescape(data_k_crudo)
        estado = html.unescape(data_st_crudo)
        partes = data_k.split('__')
        if len(partes) != 4 or not all(partes):
            avisos.append(_aviso_clave_no_resuelta(
                data_k, 'se esperaban cuatro segmentos no vacios', estado))
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
            avisos.append(_aviso_clave_no_resuelta(data_k, motivo, estado))
            continue

        if planta_html == 'zesp':
            planta_id = ('zesp'
                         if (portal_id, 'zesp') in _indice_plantas(ficha_actual)
                         else None)
        else:
            planta_id = mapa_plantas.get(planta_html)
        if planta_id is None:
            if planta_html in ambiguos_planta:
                motivo = ('planta ambigua entre '
                          f'{ambiguos_planta[planta_html]!r}; requiere mapa explicito')
            else:
                motivo = f'planta desconocida {planta_html!r}'
            avisos.append(_aviso_clave_no_resuelta(data_k, motivo, estado))
            continue

        tarea_id = mapa_tareas.get(tarea_html)
        if tarea_id is None:
            avisos.append(_aviso_clave_no_resuelta(
                data_k, f'tajo desconocido {tarea_html!r}', estado))
            continue

        unidad_id, error_unidad = _resolver_unidad(
            ficha_actual, portal_id, planta_id, unidad_html)
        if error_unidad:
            avisos.append(_aviso_clave_no_resuelta(
                data_k, error_unidad, estado))
            continue

        if estado == '' and sin_marca == 'desconocido':
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
        'hoja_usada': any(
            celda['estado_leido'] in ('X', 'M', '/') for celda in celdas),
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


# --- Lector de historial generico, valido para CUALQUIER obra --------------
#
# A diferencia del patron antiguo (ver adaptador_gernika.py: cada obra
# mantiene su propia PORTAL_NOMBRE_HTML / PLANTA_NOMBRE_HTML /
# TAREA_ID_A_NOMBRE_HTML), esta funcion no necesita ninguna tabla propia de
# la obra: el nombre de portal/planta sale de la ESTRUCTURA de su propia
# ficha_obra.json (misma fuente que ya usa derivar_mapas_ubicacion arriba) y
# el nombre de tarea sale del CATALOGO_TAJOS.json compartido. Como el HTML
# ya trae los estados embebidos por la propia app del generador (sin marcas
# manuscritas que interpretar), es previsible que sea el formato mas usado
# a partir de ahora — por eso conviene que cualquier adaptador pueda sumarlo
# con una sola llamada de 4 argumentos, sin repetir tablas de traduccion por
# obra cada vez que se da de alta o se retoma una obra.


def _mapa_tajo_nombre(catalogo):
    """id de catalogo -> nombre oficial. Misma fuente que ya usan todos los
    adaptadores para poblar su propio TAJO_NOMBRE_CATALOGO a mano; aqui se
    lee directamente para no duplicar esa tabla por obra."""
    return {
        tajo['id']: tajo['nombre']
        for tajo in catalogo.get('tajos') or []
        if isinstance(tajo, dict) and tajo.get('id') and tajo.get('nombre')
    }


def _mapa_ubicacion_nombre(ficha_actual):
    """(portal_id, planta_id) -> (nombre_portal, nombre_planta), leido de la
    estructura de la ficha. Sustituye a PORTAL_NOMBRE_HTML/PLANTA_NOMBRE_HTML
    por obra: mientras la ficha describa bien sus portales/plantas, cualquier
    obra queda cubierta sin mantenimiento adicional."""
    mapa = {}
    for portal in _portales_en_estructura(ficha_actual):
        portal_id = _id_real(portal.get('id'))
        nombre_portal = _referencia_portal(portal) or portal_id
        for planta in portal.get('plantas') or []:
            if not isinstance(planta, dict):
                continue
            planta_id = _id_real(planta.get('id'))
            nombre_planta = _referencia_planta(planta) or planta_id
            mapa[(portal_id, planta_id)] = (nombre_portal, nombre_planta)
    return mapa


def cargar_historial_html_generico(
        obra_id, carpeta_revisiones, ficha_actual, catalogo,
        contiene=None, minimo_celdas=20, nombre_log='',
        portal_id_a_real=None, planta_id_a_real=None, tarea_id_a_real=None,
        ignorar_en_blanco=True):
    """Historial ``[(fecha_display, [registros]), ...]`` desde los HTML de
    ``carpeta_revisiones``, en el mismo esquema ``{'task','floor','building',
    'unit','status'}`` que ya devuelven las rutas PDF/Word de cada
    adaptador. Pensado para que CUALQUIER adaptador lo llame tal cual (solo
    necesita su ficha y el catalogo compartido) y herede soporte HTML sin
    escribir ninguna tabla nueva. Si una ficha concreta no permite traducir
    una posicion sin ambiguedad, esa clave queda fuera del historial (avisada
    por ``construir_revision_normalizada_html``) en vez de adivinarla — el
    llamador puede entonces aportar mapas explicitos a mano solo para ese
    caso (ver parametros opcionales de ``construir_revision_normalizada_html``).
    """
    if not os.path.isdir(carpeta_revisiones):
        return []

    candidatos = []
    for fn in os.listdir(carpeta_revisiones):
        if not fn.lower().endswith('.html'):
            continue
        if contiene and contiene.upper() not in fn.upper():
            continue
        try:
            fecha = _fecha_html(os.path.join(carpeta_revisiones, fn))
        except ValueError:
            continue
        candidatos.append((fecha, fn))
    candidatos.sort(key=lambda par: datetime.strptime(par[0], '%d/%m/%Y'))

    nombre_tajo = _mapa_tajo_nombre(catalogo)
    nombre_ubicacion = _mapa_ubicacion_nombre(ficha_actual)

    historial = []
    for fecha, fn in candidatos:
        ruta = os.path.join(carpeta_revisiones, fn)
        try:
            revision = construir_revision_normalizada_html(
                ruta, obra_id, ficha_actual, catalogo,
                portal_id_a_real=portal_id_a_real,
                planta_id_a_real=planta_id_a_real,
                tarea_id_a_real=tarea_id_a_real,
            )
        except Exception as exc:
            if nombre_log:
                print("  [{}] AVISO: no se pudo leer '{}': {}".format(
                    nombre_log, fn, exc))
            continue

        celdas_historial = [
            celda for celda in revision['celdas']
            if celda['clave'].split('__')[1] != 'zesp'
        ]
        if ignorar_en_blanco and not any(
                c['estado_leido'] in ('X', 'M', '/') for c in celdas_historial):
            if nombre_log:
                print("  [{}] '{}' ignorado como revisión (hoja en blanco sin marcas).".format(
                    nombre_log, fn))
            continue

        registros = []
        for celda in celdas_historial:
            estado = celda['estado_leido']
            portal_id, planta_id, tajo_id, unidad = celda['clave'].split('__')
            if estado == 'N':
                continue
            nombres = nombre_ubicacion.get((portal_id, planta_id))
            task = nombre_tajo.get(tajo_id)
            if not (nombres and task):
                continue
            building, floor = nombres
            registros.append({
                'task': task, 'floor': floor, 'building': building,
                'unit': unidad,
                'status': estado if estado in ('X', 'M', '/') else '',
            })

        if len(registros) >= minimo_celdas:
            if nombre_log:
                avisos_n = len(revision['metadata']['avisos'])
                extra = (' ({} clave(s) sin resolver)'.format(avisos_n)
                         if avisos_n else '')
                print("  [{}] {}: {} registros de '{}'{}".format(
                    nombre_log, fecha, len(registros), fn, extra))
            historial.append((fecha, registros))
        elif nombre_log and registros:
            print("  [{}] '{}' descartado ({} registros, por debajo del "
                  "minimo {}).".format(nombre_log, fn, len(registros), minimo_celdas))

    return historial
