# -*- coding: utf-8 -*-
"""Crea ``ficha_garajes.json`` desde la estructura embebida en una hoja.

Uso::

    python alta_garaje_desde_hoja.py <hoja.html> <id_obra>

La estructura ya fue confirmada en el asistente que genero la hoja. Este
script no la deduce del HTML: recupera literalmente el JSON del bloque
``garaje-estructura`` y completa los tajos seleccionados desde el catalogo.
"""
import argparse
import copy
import json
import os
import re

import ficha_garajes
import registro_obras
import validar_revision


AQUI = os.path.dirname(os.path.abspath(__file__))
OBRAS_DIR = os.path.dirname(AQUI)

PATRON_ESTRUCTURA = re.compile(
    r'<script\s+type=["\']application/json["\']\s+'
    r'id=["\']garaje-estructura["\']\s*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _configuracion_obra(obra_id):
    return next(
        (obra for obra in registro_obras.OBRAS if obra.get('id') == obra_id),
        None,
    )


def resolver_carpeta_obra(obra_id):
    """Resuelve el id corto del registro a la carpeta absoluta de la obra."""
    configuracion = _configuracion_obra(obra_id)
    if configuracion is None:
        raise ValueError(f'id de obra desconocido: {obra_id!r}')
    return os.path.join(OBRAS_DIR, configuracion['carpeta_obra'])


def extraer_estructura(ruta_html):
    """Devuelve el JSON de ``garaje-estructura`` incluido por el generador."""
    with open(ruta_html, encoding='utf-8') as fichero:
        contenido = fichero.read()
    coincidencia = PATRON_ESTRUCTURA.search(contenido)
    if coincidencia is None:
        raise ValueError(
            'la hoja no contiene el bloque JSON garaje-estructura'
        )
    return json.loads(coincidencia.group(1))


def _detalle_tajos(catalogo, obra, seleccionados):
    """Copia del catalogo los tajos de garaje seleccionados en la hoja."""
    por_id = {
        tajo['id']: tajo
        for tajo in catalogo.get('tajos') or []
        if isinstance(tajo, dict) and isinstance(tajo.get('id'), str)
    }
    configuracion = (catalogo.get('obras') or {}).get(obra) or {}
    for tajo in configuracion.get('tajos') or []:
        if isinstance(tajo, dict) and isinstance(tajo.get('id'), str):
            por_id[tajo['id']] = tajo

    elegidos = set(seleccionados or [])
    return [
        copy.deepcopy(tajo)
        for tajo_id, tajo in por_id.items()
        if tajo_id.startswith('garaje_') and tajo_id in elegidos
    ]


def construir_ficha(datos, obra_catalogo, catalogo):
    """Construye la ficha inicial con la forma definida por ``ficha_garajes``."""
    ficha = {}
    ficha_garajes.asegurar_apartados(ficha)
    ficha['estructura']['garajes'] = datos['garajes']
    ficha['tajos']['detalle'] = _detalle_tajos(
        catalogo,
        obra_catalogo,
        datos.get('tajos_seleccionados') or [],
    )
    return ficha


def alta_garaje_desde_hoja(
        ruta_html, obra_id, carpeta_obra_abs=None, catalogo=None):
    """Crea y guarda la ficha de garajes; nunca pisa una ficha existente."""
    configuracion = _configuracion_obra(obra_id)
    if carpeta_obra_abs is None:
        carpeta_obra_abs = resolver_carpeta_obra(obra_id)
    else:
        carpeta_obra_abs = os.path.abspath(os.fspath(carpeta_obra_abs))

    destino = ficha_garajes.ruta_ficha(carpeta_obra_abs)
    if os.path.isfile(destino):
        raise FileExistsError(
            f'ya existe {destino}; no se sobrescribe una estructura de '
            'garaje ya confirmada'
        )

    datos = extraer_estructura(os.path.abspath(os.fspath(ruta_html)))
    if catalogo is None:
        catalogo = validar_revision.cargar_catalogo_tajos()
    obra_catalogo = (
        configuracion.get('nombre') if configuracion else obra_id
    )
    ficha = construir_ficha(datos, obra_catalogo, catalogo)
    return ficha, ficha_garajes.guardar(carpeta_obra_abs, ficha)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hoja_html')
    parser.add_argument('obra_id')
    args = parser.parse_args(argv)

    try:
        ficha, destino = alta_garaje_desde_hoja(
            args.hoja_html, args.obra_id
        )
    except (FileExistsError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f'[ABORTADO] {exc}') from exc

    print(
        f'ESCRITA: {destino} '
        f'({len(ficha["estructura"]["garajes"])} garaje(s), '
        f'{len(ficha["tajos"]["detalle"])} tajo(s))'
    )


if __name__ == '__main__':
    main()
