# -*- coding: utf-8 -*-
"""Modelo y validacion comun de revisiones normalizadas.

Este modulo es deliberadamente aislado: valida datos y calcula el antes/despues
de cada celda, pero no modifica la ficha ni escribe ningun fichero de obra.
"""
import hashlib
import json
import os
from datetime import datetime

from ficha_obra import MAPA_ESTADO


AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA_CATALOGO_TAJOS = os.path.join(AQUI, 'reglas', 'CATALOGO_TAJOS.json')

ORIGENES_VALIDOS = frozenset({
    'tinta', 'pdf_digital', 'html_digital', 'historial_consolidado'})
CONFIANZAS_VALIDAS = frozenset({'cierta', 'dudosa'})

# Se deriva la traduccion del mapa de ficha existente. Los origenes digitales
# solo pueden leer los simbolos impresos; la clasificacion de tinta tambien
# puede contener una P explicita decidida por el corrector. ``?`` solo existe
# en la ficha.
ALFABETO_HOJA_DIGITAL = frozenset(
    simbolo for simbolo in ('X', 'M', '/', '', 'N')
    if simbolo.lower() in MAPA_ESTADO
)
ALFABETO_HOJA_TINTA = frozenset((*ALFABETO_HOJA_DIGITAL, 'P'))
ALFABETOS_HOJA = {
    'tinta': ALFABETO_HOJA_TINTA,
    'pdf_digital': ALFABETO_HOJA_DIGITAL,
    'html_digital': ALFABETO_HOJA_DIGITAL,
}

CAMPOS_REVISION_CELDA = ('clave', 'estado_leido', 'confianza')
CAMPOS_REVISION_NORMALIZADA = (
    'revision_id', 'obra', 'fecha', 'origen', 'fuente', 'celdas', 'metadata')
CAMPOS_METADATA = ('generado_por', 'generado_en', 'avisos', 'hoja_usada')


def cargar_catalogo_tajos(ruta=None):
    """Carga el catalogo real del sistema, o una ruta explicita para tests."""
    with open(ruta or RUTA_CATALOGO_TAJOS, encoding='utf-8') as fichero:
        return json.load(fichero)


def generar_revision_id(obra, fecha, origen, fuente):
    """Genera ``obra__fecha__origen__hash8`` desde los bytes de la fuente."""
    digest = hashlib.sha256()
    with open(fuente, 'rb') as fichero:
        for bloque in iter(lambda: fichero.read(1024 * 1024), b''):
            digest.update(bloque)
    return f'{obra}__{fecha}__{origen}__{digest.hexdigest()[:8]}'


def validar_forma_revision_celda(celda):
    """Devuelve una lista de errores de forma basica de REVISION_CELDA."""
    if not isinstance(celda, dict):
        return ['la celda debe ser un dict']

    errores = []
    for campo in CAMPOS_REVISION_CELDA:
        if campo not in celda:
            errores.append(f'falta el campo obligatorio {campo!r}')
    if 'clave' in celda and not isinstance(celda['clave'], str):
        errores.append("'clave' debe ser str")
    if 'estado_leido' in celda and not isinstance(celda['estado_leido'], str):
        errores.append("'estado_leido' debe ser str")
    if 'confianza' in celda:
        if not isinstance(celda['confianza'], str):
            errores.append("'confianza' debe ser str")
        elif celda['confianza'] not in CONFIANZAS_VALIDAS:
            errores.append(
                "'confianza' debe ser 'cierta' o 'dudosa'")
    return errores


def crear_revision_celda(clave, estado_leido, confianza='cierta'):
    """Construye una REVISION_CELDA simple y comprueba su forma basica."""
    celda = {
        'clave': clave,
        'estado_leido': estado_leido,
        'confianza': confianza,
    }
    _exigir_forma(celda, validar_forma_revision_celda, 'REVISION_CELDA')
    return celda


def _errores_metadata(metadata):
    if not isinstance(metadata, dict):
        return ["'metadata' debe ser dict"]

    errores = []
    for campo in CAMPOS_METADATA:
        if campo not in metadata:
            errores.append(f"metadata: falta el campo obligatorio {campo!r}")
    for campo in ('generado_por', 'generado_en'):
        if campo in metadata and not isinstance(metadata[campo], str):
            errores.append(f"metadata[{campo!r}] debe ser str")
    if 'avisos' in metadata:
        if not isinstance(metadata['avisos'], list):
            errores.append("metadata['avisos'] debe ser list")
        elif not all(isinstance(aviso, str) for aviso in metadata['avisos']):
            errores.append("todos los elementos de metadata['avisos'] deben ser str")
    if 'hoja_usada' in metadata and not isinstance(metadata['hoja_usada'], bool):
        errores.append("metadata['hoja_usada'] debe ser bool")
    return errores


def _errores_revision_sin_celdas(revision):
    if not isinstance(revision, dict):
        return ['la revision debe ser un dict']

    errores = []
    for campo in CAMPOS_REVISION_NORMALIZADA:
        if campo not in revision:
            errores.append(f'falta el campo obligatorio {campo!r}')
    for campo in ('revision_id', 'obra', 'fecha', 'origen', 'fuente'):
        if campo in revision and not isinstance(revision[campo], str):
            errores.append(f'{campo!r} debe ser str')
    if 'celdas' in revision and not isinstance(revision['celdas'], list):
        errores.append("'celdas' debe ser list")
    if 'metadata' in revision:
        errores.extend(_errores_metadata(revision['metadata']))
    return errores


def validar_forma_revision_normalizada(revision):
    """Devuelve errores de forma basica de REVISION_NORMALIZADA y sus celdas."""
    errores = _errores_revision_sin_celdas(revision)
    if isinstance(revision, dict) and isinstance(revision.get('celdas'), list):
        for indice, celda in enumerate(revision['celdas']):
            errores.extend(
                f'celdas[{indice}]: {error}'
                for error in validar_forma_revision_celda(celda)
            )
    return errores


def crear_revision_normalizada(revision_id, obra, fecha, origen, fuente,
                                celdas, metadata):
    """Construye una REVISION_NORMALIZADA y comprueba su forma basica."""
    revision = {
        'revision_id': revision_id,
        'obra': obra,
        'fecha': fecha,
        'origen': origen,
        'fuente': fuente,
        'celdas': list(celdas) if isinstance(celdas, (list, tuple)) else celdas,
        'metadata': metadata,
    }
    _exigir_forma(
        revision, validar_forma_revision_normalizada, 'REVISION_NORMALIZADA')
    return revision


def _exigir_forma(valor, comprobador, nombre):
    errores = comprobador(valor)
    if errores:
        raise ValueError(f'{nombre} invalida: ' + '; '.join(errores))


def _fecha_valida(fecha):
    if not isinstance(fecha, str) or not fecha:
        return False
    try:
        return datetime.strptime(fecha, '%d/%m/%Y').strftime('%d/%m/%Y') == fecha
    except ValueError:
        return False


def _partes_clave(clave):
    if not isinstance(clave, str):
        return None
    partes = clave.split('__')
    if (len(partes) != 4 or not all(partes)
            or any(parte != parte.lower() for parte in partes[:3])):
        return None
    return tuple(partes)


def _ubicacion_existe(ficha, portal_id, planta_id, vivienda_id):
    estructura = ficha.get('estructura') or {}
    for bloque in estructura.get('bloques') or []:
        for portal in bloque.get('portales') or []:
            if str(portal.get('id', '')).lower() != portal_id:
                continue
            for planta in portal.get('plantas') or []:
                if str(planta.get('id', '')).lower() != planta_id:
                    continue
                viviendas = {
                    str(ubicacion.get('id', ''))
                    for ubicacion in planta.get('ubicaciones') or []
                    if isinstance(ubicacion, dict)
                }
                return vivienda_id in viviendas
            return False
    return False


def _ids_tajos(catalogo, obra):
    ids = {
        tajo.get('id') for tajo in catalogo.get('tajos') or []
        if isinstance(tajo, dict) and isinstance(tajo.get('id'), str)
    }
    configuracion_obra = (catalogo.get('obras') or {}).get(obra) or {}
    ids.update(
        tajo.get('id') for tajo in configuracion_obra.get('tajos') or []
        if isinstance(tajo, dict) and isinstance(tajo.get('id'), str)
    )
    return ids


def _estado_anterior(ficha, clave):
    registro = (ficha.get('estados') or {}).get(clave)
    if isinstance(registro, dict):
        return registro.get('v')
    return None


def _aceptada(indice, celda, antes, despues, accion, motivo):
    return {
        'indice': indice,
        'clave': celda['clave'],
        'estado_leido': celda['estado_leido'],
        'confianza': celda['confianza'],
        'antes': antes,
        'despues': despues,
        'accion': accion,
        'motivo': motivo,
    }


def _rechazada(indice, celda, regla, motivo):
    return {
        'indice': indice,
        'clave': celda.get('clave') if isinstance(celda, dict) else None,
        'estado_leido': (
            celda.get('estado_leido') if isinstance(celda, dict) else None),
        'regla': regla,
        'motivo': motivo,
    }


def _finalizar(resultado):
    acciones = [celda['accion'] for celda in resultado['aceptadas']]
    resultado['resumen'] = {
        'total': len(resultado['aceptadas']) + len(resultado['rechazadas']),
        'aceptadas': len(resultado['aceptadas']),
        'rechazadas': len(resultado['rechazadas']),
        'cambios': acciones.count('actualizar'),
        'sin_cambio': acciones.count('conservar'),
        'descartadas': acciones.count('descartar'),
    }
    resultado['aplicable'] = not resultado['errores'] and not resultado['rechazadas']
    return resultado


def validar(revision, ficha_actual, catalogo):
    """Valida una revision sin modificarla ni tocar ``ficha_actual``.

    El resultado separa errores bloqueantes de revision, celdas aceptadas,
    celdas rechazadas y avisos. Una futura aplicacion solo debe escribir las
    aceptadas cuya ``accion`` sea ``actualizar``, y solo si ``aplicable`` es
    verdadero.
    """
    resultado = {
        'revision_id': (
            revision.get('revision_id') if isinstance(revision, dict) else None),
        'aplicable': False,
        'errores': [],
        'aceptadas': [],
        'rechazadas': [],
        'avisos': [],
        'resumen': {},
    }

    errores_forma = _errores_revision_sin_celdas(revision)
    resultado['errores'].extend(errores_forma)
    if errores_forma:
        celdas = revision.get('celdas', []) if isinstance(revision, dict) else []
        if isinstance(celdas, list):
            motivo = 'revision bloqueada: ' + '; '.join(errores_forma)
            resultado['rechazadas'].extend(
                _rechazada(indice, celda, 0, motivo)
                for indice, celda in enumerate(celdas)
            )
        return _finalizar(resultado)

    resultado['avisos'].extend(revision['metadata']['avisos'])

    if revision['origen'] not in ORIGENES_VALIDOS:
        resultado['errores'].append(
            f"origen {revision['origen']!r} desconocido; validos: "
            + ', '.join(sorted(ORIGENES_VALIDOS)))
    if not _fecha_valida(revision['fecha']):
        resultado['errores'].append(
            "regla 10: fecha obligatoria en formato DD/MM/AAAA; no se infiere")
    if not isinstance(ficha_actual, dict):
        resultado['errores'].append('ficha_actual debe ser un dict')
    elif revision['obra'] != ficha_actual.get('id'):
        resultado['errores'].append(
            f"regla 1: obra de revision {revision['obra']!r} no coincide con "
            f"ficha {ficha_actual.get('id')!r}")
    if (not isinstance(catalogo, dict)
            or not isinstance(catalogo.get('tajos'), list)
            or not isinstance(catalogo.get('obras', {}), dict)):
        resultado['errores'].append(
            "catalogo invalido: se esperan 'tajos' como list y 'obras' como dict")

    if resultado['errores']:
        motivo = 'revision bloqueada: ' + '; '.join(resultado['errores'])
        resultado['rechazadas'].extend(
            _rechazada(indice, celda, 0, motivo)
            for indice, celda in enumerate(revision['celdas'])
        )
        return _finalizar(resultado)

    ids_tajo = _ids_tajos(catalogo, revision['obra'])
    hoja_usada = revision['metadata']['hoja_usada']
    # generar_todos no recibe una hoja sino la fotografia ya normalizada por
    # el adaptador. Puede incorporar una P explicita de un sidecar de tinta,
    # pero sus blancos significan "sin dato nuevo", como en los digitales.
    alfabeto_hoja = (
        ALFABETO_HOJA_TINTA
        if revision['origen'] == 'historial_consolidado'
        else ALFABETOS_HOJA[revision['origen']]
    )

    for indice, celda in enumerate(revision['celdas']):
        errores_celda = validar_forma_revision_celda(celda)
        if errores_celda:
            resultado['rechazadas'].append(_rechazada(
                indice, celda, 0, 'forma de celda invalida: ' + '; '.join(errores_celda)))
            continue

        partes = _partes_clave(celda['clave'])
        if partes is None:
            resultado['rechazadas'].append(_rechazada(
                indice, celda, 2,
                'regla 2: la clave debe tener 4 partes no vacias separadas '
                'por "__"; portal, planta y tajo deben estar en minusculas'))
            continue
        portal, planta, tajo, vivienda = partes

        if not _ubicacion_existe(ficha_actual, portal, planta, vivienda):
            resultado['rechazadas'].append(_rechazada(
                indice, celda, 3,
                f'regla 3: no existe {portal}/{planta}/{vivienda} en la ficha'))
            continue
        if tajo not in ids_tajo:
            resultado['rechazadas'].append(_rechazada(
                indice, celda, 4,
                f"regla 4: el tajo {tajo!r} no existe en el catalogo de "
                f"{revision['obra']!r}"))
            continue

        estado_leido = celda['estado_leido']
        if estado_leido not in alfabeto_hoja:
            resultado['rechazadas'].append(_rechazada(
                indice, celda, 5,
                f'regla 5: estado de hoja {estado_leido!r} no valido; '
                f'validos para {revision["origen"]}: '
                f'{sorted(alfabeto_hoja)!r}'))
            continue

        # Regla 9. El adaptador asigna la tinta a celdas antes de normalizar.
        # En este modelo hoja_usada es la prueba disponible de que hubo tinta:
        # una hoja no usada nunca puede proponer una marca no vacia.
        if (revision['origen'] == 'tinta' and estado_leido != ''
                and not hoja_usada):
            resultado['rechazadas'].append(_rechazada(
                indice, celda, 9,
                'regla 9: una hoja de tinta no usada no puede proponer cambios; '
                'sin tinta no hay cambio'))
            continue

        antes = _estado_anterior(ficha_actual, celda['clave'])
        if celda['confianza'] == 'dudosa':
            resultado['avisos'].append(
                f"{celda['clave']}: confianza dudosa; el adaptador debe haber "
                'resuelto o descartado la lectura antes de aplicar')

        # Regla 6: N es una instruccion valida de descarte, nunca se guarda.
        if estado_leido == 'N':
            resultado['aceptadas'].append(_aceptada(
                indice, celda, antes, antes, 'descartar',
                'regla 6: N se descarta y no se guarda'))
            continue

        if estado_leido == '':
            if revision['origen'] in {
                    'pdf_digital', 'html_digital', 'historial_consolidado'}:
                resultado['aceptadas'].append(_aceptada(
                    indice, celda, antes, antes, 'conservar',
                    'regla 6: un blanco digital no toca la celda'))
                continue
            if not hoja_usada:
                resultado['aceptadas'].append(_aceptada(
                    indice, celda, antes, antes, 'conservar',
                    'reglas 6 y 9: hoja de tinta no usada; no hay cambio'))
                continue
            # Reglas 6 y 7: el blanco de una hoja usada solo confirma lo que
            # aun era desconocido. Nunca rebaja un estado conocido.
            if antes not in (None, '?'):
                resultado['aceptadas'].append(_aceptada(
                    indice, celda, antes, antes, 'conservar',
                    'regla 7: un blanco no baja un estado conocido'))
                continue
            despues = MAPA_ESTADO['']
            resultado['aceptadas'].append(_aceptada(
                indice, celda, antes, despues, 'actualizar',
                'regla 6: blanco de hoja de tinta usada se traduce a P'))
            continue

        # Reglas 6 y 8: una marca explicita usa MAPA_ESTADO y manda aunque
        # suponga retroceder respecto del estado anterior.
        despues = MAPA_ESTADO[estado_leido.lower()]
        accion = 'conservar' if antes == despues else 'actualizar'
        motivo = ('mismo estado; no hay cambio' if accion == 'conservar'
                  else 'regla 8: la marca explicita se acepta a la primera')
        resultado['aceptadas'].append(_aceptada(
            indice, celda, antes, despues, accion, motivo))

    return _finalizar(resultado)
