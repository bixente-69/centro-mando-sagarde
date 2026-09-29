# -*- coding: utf-8 -*-
"""Lectura segura del hilo conductor escrito en las notas de tareas."""
from datetime import datetime
import ntpath
import os
import re


_URL_RE = re.compile(
    r"\b(?:https?://|www\.)[^\s<>\"']+",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(
    r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
    re.IGNORECASE,
)
_TELEFONO_RE = re.compile(
    r"(?<!\w)(?!\d{4}-\d{2}-\d{2}\b)\+?\s*(?:\d[ .-]*){8,}\d(?!\w)",
)
_ENTRADA_RE = re.compile(
    r"^\s*-\s*\[\s*(?P<lado>[^\]]+)\s*\]\s*(?P<resto>.*?)\s*$",
)
_MENSAJE_RE = re.compile(
    r"^(?P<fecha>\d{4}-\d{2}-\d{2})"
    r"(?:\s+(?P<hora>\d{2}:\d{2}))?\s*\|\s*"
    r"(?P<de_a>[^|]+?)\s*\|\s*(?P<texto>.+?)\s*$",
)
_LADOS = {
    'egurrola': 'Egurrola',
    'externo': 'Externo',
    'sagarde': 'Sagarde',
    'citado': 'Citado',
    'hueco': 'Hueco',
}


def sanear_texto(s) -> str:
    """Oculta datos de contacto que nunca deben llegar al panel público."""
    texto = str('' if s is None else s)
    texto = _URL_RE.sub('[dato oculto]', texto)
    texto = _EMAIL_RE.sub('[dato oculto]', texto)
    return _TELEFONO_RE.sub('[dato oculto]', texto)


def _fecha_hora_validas(fecha, hora):
    formato = '%Y-%m-%d %H:%M' if hora else '%Y-%m-%d'
    valor = f'{fecha} {hora}' if hora else fecha
    try:
        datetime.strptime(valor, formato)
    except ValueError:
        return False
    return True


def parse_hilo_conductor(texto) -> dict | None:
    """Extrae el primer bloque HILO CONDUCTOR de una nota de texto.

    Las líneas no vacías que no cumplen el contrato se omiten y producen un
    aviso individual. La presencia del bloque se conserva aunque no contenga
    ninguna entrada válida.
    """
    lineas = str('' if texto is None else texto).splitlines()
    inicio = None
    for indice, linea in enumerate(lineas):
        if linea.strip().casefold() == 'hilo conductor':
            inicio = indice + 1
            break
    if inicio is None:
        return None

    mensajes = []
    avisos = []
    for indice in range(inicio, len(lineas)):
        linea = lineas[indice]
        if linea.strip().casefold() == 'fin hilo':
            break
        if not linea.strip():
            continue

        entrada = _ENTRADA_RE.fullmatch(linea)
        if entrada is None:
            avisos.append(
                f'Línea {indice + 1} descartada: formato no válido.')
            continue

        lado = _LADOS.get(entrada.group('lado').strip().casefold())
        resto = entrada.group('resto').strip()
        if lado is None:
            avisos.append(
                f'Línea {indice + 1} descartada: lado no reconocido.')
            continue

        if lado == 'Hueco':
            if not resto or '|' in resto:
                avisos.append(
                    f'Línea {indice + 1} descartada: formato Hueco no válido.')
                continue
            mensajes.append({
                'lado': lado,
                'fecha': '',
                'hora': '',
                'de_a': '',
                'texto': sanear_texto(resto),
            })
            continue

        mensaje = _MENSAJE_RE.fullmatch(resto)
        if mensaje is None:
            avisos.append(
                f'Línea {indice + 1} descartada: formato no válido.')
            continue
        fecha = mensaje.group('fecha')
        hora = mensaje.group('hora') or ''
        if not _fecha_hora_validas(fecha, hora):
            avisos.append(
                f'Línea {indice + 1} descartada: fecha u hora no válida.')
            continue

        mensajes.append({
            'lado': lado,
            'fecha': fecha,
            'hora': hora,
            'de_a': sanear_texto(mensaje.group('de_a').strip()),
            'texto': sanear_texto(mensaje.group('texto').strip()),
        })

    return {'mensajes': mensajes, 'avisos': avisos}


def _motivo_nombre_inseguro(archivo):
    if '..' in archivo:
        return "contiene '..'"
    if '/' in archivo or '\\' in archivo:
        return 'contiene separadores de ruta'
    if os.path.isabs(archivo) or ntpath.isabs(archivo):
        return 'es una ruta absoluta'
    if ntpath.splitdrive(archivo)[0]:
        return 'incluye una unidad de Windows'
    if os.path.basename(archivo) != archivo or ntpath.basename(archivo) != archivo:
        return 'no es un nombre base'
    return ''


def leer_hilos_de_tareas(carpeta_obra, tareas) -> tuple[dict, list]:
    """Lee únicamente notas ``.txt`` seguras situadas dentro de la obra."""
    hilos = {}
    avisos = []
    carpeta_real = os.path.realpath(os.fspath(carpeta_obra))

    for tarea in tareas or []:
        archivo = str(tarea.get('Archivo') or '').strip()
        if not archivo or not archivo.casefold().endswith('.txt'):
            continue

        motivo = _motivo_nombre_inseguro(archivo)
        if motivo:
            avisos.append(
                f"Hilo '{archivo}' rechazado: {motivo}; no se leyó ningún fichero.")
            continue

        ruta = os.path.join(carpeta_real, archivo)
        ruta_real = os.path.realpath(ruta)
        try:
            dentro_de_obra = os.path.commonpath(
                [carpeta_real, ruta_real]) == carpeta_real
        except ValueError:
            dentro_de_obra = False
        if not dentro_de_obra:
            avisos.append(
                f"Hilo '{archivo}' rechazado: resuelve fuera de la carpeta de obra.")
            continue

        if not os.path.exists(ruta_real):
            avisos.append(
                f"Hilo '{archivo}': el fichero no existe en la carpeta de obra.")
            continue
        try:
            with open(ruta_real, encoding='utf-8', errors='replace') as fichero:
                texto = fichero.read()
        except OSError as exc:
            avisos.append(
                f"Hilo '{archivo}': no se pudo leer ({type(exc).__name__}: {exc}).")
            continue

        hilo = parse_hilo_conductor(texto)
        if hilo is None:
            continue
        hilos[archivo] = hilo
        for aviso in hilo['avisos']:
            avisos.append(f"Hilo '{archivo}': {aviso}")
        if not hilo['mensajes']:
            avisos.append(
                f"Hilo '{archivo}': el bloque está presente pero sin entradas válidas.")

    return hilos, avisos
