# -*- coding: utf-8 -*-
"""Aplica una hoja HTML digital de garaje a ``ficha_garajes.json``.

Uso::

    python adaptar_revision_garaje.py <hoja.html> <id_obra>
    python adaptar_revision_garaje.py <hoja.html> <id_obra> --fecha DD/MM/AAAA

Los ids de garaje, planta y zona escritos por el asistente ya son los ids
canonicos de la ficha. Por eso este adaptador no genera numeraciones
sinteticas ni mantiene mapas de traduccion.
"""
import argparse
import html
import os

import ficha_garajes
import lector_hoja_tajos_html
import registro_obras
import validar_revision


AQUI = os.path.dirname(os.path.abspath(__file__))
OBRAS_DIR = os.path.dirname(AQUI)


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


def _fecha_html(ruta_html):
    _, fecha = lector_hoja_tajos_html._fecha_desde_nombre(
        os.path.basename(ruta_html)
    )
    if fecha is None:
        raise ValueError(
            'el nombre del HTML no contiene una fecha DDMMAAAA valida'
        )
    return fecha


def _aviso_clave(data_k, motivo):
    return f'clave HTML descartada {data_k!r}: {motivo}'


def construir_snapshot(ruta_html, obra_catalogo, catalogo):
    """Lee claves canonicas de garaje y devuelve ``(snapshot, avisos)``."""
    ids_tajos = {
        tajo_id
        for tajo_id in validar_revision._ids_tajos(
            catalogo, obra_catalogo
        )
        if tajo_id.startswith('garaje_')
    }
    snapshot = []
    avisos = []

    for data_k_crudo, data_st_crudo in lector_hoja_tajos_html.extraer_pares(
            ruta_html):
        data_k = html.unescape(data_k_crudo)
        estado = html.unescape(data_st_crudo)
        partes = data_k.split('__')
        if len(partes) != 4 or not all(partes):
            avisos.append(_aviso_clave(
                data_k, 'se esperaban cuatro segmentos no vacios'
            ))
            continue
        if estado not in validar_revision.ALFABETO_HOJA_DIGITAL:
            avisos.append(_aviso_clave(
                data_k, f'estado HTML desconocido {estado!r}'
            ))
            continue

        garaje_id, planta_id, tarea_id, zona_id = partes
        if tarea_id not in ids_tajos:
            avisos.append(_aviso_clave(
                data_k, f'tajo desconocido {tarea_id!r}'
            ))
            continue
        if estado == 'N':
            continue

        snapshot.append({
            'task': tarea_id,
            'status': estado,
            'garaje_id': garaje_id,
            'planta_id': planta_id,
            'zona_id': zona_id,
        })
    return snapshot, avisos


def adaptar_revision_garaje(
        ruta_html, obra_id, fecha=None, carpeta_obra_abs=None,
        catalogo=None):
    """Lee, aplica y guarda una revision HTML de garaje."""
    ruta_html = os.path.abspath(os.fspath(ruta_html))
    configuracion = _configuracion_obra(obra_id)
    if carpeta_obra_abs is None:
        carpeta_obra_abs = resolver_carpeta_obra(obra_id)
    else:
        carpeta_obra_abs = os.path.abspath(os.fspath(carpeta_obra_abs))

    ficha = ficha_garajes.cargar(carpeta_obra_abs)
    if ficha is None:
        raise FileNotFoundError(
            f'no existe {ficha_garajes.ruta_ficha(carpeta_obra_abs)}; '
            'primero hay que dar de alta la estructura de garaje'
        )
    if fecha is None:
        fecha = _fecha_html(ruta_html)
    elif not isinstance(fecha, str) or not fecha:
        raise ValueError('la fecha explicita debe ser un texto no vacio')
    if catalogo is None:
        catalogo = validar_revision.cargar_catalogo_tajos()
    obra_catalogo = (
        configuracion.get('nombre') if configuracion else obra_id
    )

    snapshot, avisos = construir_snapshot(
        ruta_html, obra_catalogo, catalogo
    )
    ficha, cambios = ficha_garajes.actualizar_desde_snapshot(
        ficha, snapshot, fecha
    )
    destino = ficha_garajes.guardar(carpeta_obra_abs, ficha)

    for aviso in avisos:
        print(f'[AVISO GARAJE] {aviso}')
    for linea in ficha_garajes.resumen_cambios(cambios):
        print(f'[AVISO GARAJE] {linea}')
    return ficha, cambios, avisos, destino


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hoja_html')
    parser.add_argument('obra_id')
    parser.add_argument('--fecha')
    args = parser.parse_args(argv)

    try:
        ficha, cambios, avisos, destino = adaptar_revision_garaje(
            args.hoja_html,
            args.obra_id,
            fecha=args.fecha,
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise SystemExit(f'[ABORTADO] {exc}') from exc

    print(
        f'GUARDADA: {destino} '
        f'({len(ficha.get("estados") or {})} estado(s), '
        f'{len(avisos)} aviso(s), '
        f'{len(cambios.get("zonas_desconocidas") or [])} zona(s) descartada(s))'
    )


if __name__ == '__main__':
    main()
