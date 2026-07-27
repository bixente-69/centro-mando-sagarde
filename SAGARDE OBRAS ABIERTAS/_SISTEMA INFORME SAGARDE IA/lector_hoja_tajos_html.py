# -*- coding: utf-8 -*-
"""
LECTOR GENÉRICO DE HOJA DE TAJOS EN HTML (capa 0 — común a todas las obras)
----------------------------------------------------------------------------
Lee el export HTML de la "app de generación de tajos" (la misma herramienta
web que consume `obras_revisiones.js`, generado por
`crear_registro_revision()` en generar_todos.py). Cuando un usuario rellena
esa hoja interactiva en el navegador y hace "Guardar como" / exportar,
obtiene un .html con el estado de cada celda embebido en atributos:

    <td data-k="src_{obra}_p{n}__src_{obra}_p{n}_f{m}__{tarea_id}__{unidad}"
        data-st="X"|"M"|"/"|""|"N">

Este módulo NO sabe nada de una obra concreta: cada adaptador debe pasarle
sus propios diccionarios de traducción (portal_id->nombre, planta_id->nombre,
tarea_id->nombre) — exactamente el mismo patrón de "motor genérico + config
delgada por obra" que ya usa `lector_hoja_tajos_pdf.py` para las hojas PDF.

IMPORTANTE — de dónde salen los ids de portal/planta:
  Los ids "src_{obra}_p{n}" / "_f{m}" son los que asigna
  `crear_registro_revision()` (generar_todos.py) al publicar
  `obras_revisiones.js`: p{n} enumera los edificios en orden natural
  (`sorted(..., key=_clave_natural)`) y f{m} enumera las plantas de cada
  portal en orden natural con PB primero (`sorted(..., key=_clave_planta)`).
  Mientras el conjunto de edificios/plantas de la obra no cambie, este orden
  es estable, así que cada adaptador puede fijar ese mapeo como una tabla
  fija (ver receta en CLAUDE.md) sin tener que releer `obras_revisiones.js`
  en cada ejecución.

Filtrado de ficheros "vacíos"/plantilla: la misma app también genera
ficheros HTML plantilla (sin datos reales, todo data-st="") u otros ficheros
HTML no relacionados en la misma carpeta de REVISIONES. `listar_revisiones_html`
exige un nombre con fecha DDMMAAAA y un mínimo de registros reales
decodificados para no confundir una plantilla en blanco con una revisión.
"""
import os
import re


def extraer_pares(ruta_html):
    """Devuelve [(data_k, data_st), ...] tal cual aparecen en el HTML."""
    with open(ruta_html, encoding='utf-8') as f:
        html = f.read()
    return re.findall(r'data-k="([^"]*)"\s+data-st="([^"]*)"', html)


def parsear_html(ruta_html, portal_nombre, planta_nombre, tarea_id_a_nombre, nombre_log=''):
    """
    Decodifica un HTML de hoja de tajos en una lista de registros
    {'task','floor','building','unit','status'}.

    portal_nombre:      dict {portal_id (ej. 'src_gernika_p1'): nombre real}
    planta_nombre:      dict {planta_id (ej. 'src_gernika_p1_f1'): nombre real}
    tarea_id_a_nombre:  dict {tarea_id (id de catálogo o código corto): nombre
                         de tarea ya usado por el adaptador de la obra —
                         importante mantener el MISMO texto que usa el resto
                         del historial de esa obra, para no romper continuidad
                         en priorizador_trabajos.py (ver protocolo en CLAUDE.md).
    """
    registros = []
    sin_resolver = set()
    for data_k, data_st in extraer_pares(ruta_html):
        partes = data_k.split('__')
        if len(partes) != 4:
            continue
        portal_id, planta_id, tarea_id, unidad = partes
        if data_st == 'N':
            continue
        building = portal_nombre.get(portal_id)
        floor = planta_nombre.get(planta_id)
        task = tarea_id_a_nombre.get(tarea_id)
        if not (building and floor and task):
            sin_resolver.add((portal_id, planta_id, tarea_id))
            continue
        status = data_st if data_st in ('X', 'M', '/') else ''
        registros.append({
            'task':     task,
            'floor':    floor,
            'building': building,
            'unit':     unidad,
            'status':   status,
        })
    if sin_resolver and nombre_log:
        print("  [{}] AVISO: {} clave(s) sin resolver en '{}' (portal/planta/tarea "
              "desconocidos para este adaptador): {}".format(
                  nombre_log, len(sin_resolver), os.path.basename(ruta_html),
                  sorted(sin_resolver)[:10]))
    return registros


def _fecha_desde_nombre(fn):
    """Extrae DDMMAAAA del nombre de fichero y devuelve (clave_orden, display)."""
    m = re.search(r'(\d{2})(\d{2})(\d{4})', fn)
    if not m:
        return None, None
    dd, mm, aaaa = m.group(1), m.group(2), m.group(3)
    try:
        d, mo, y = int(dd), int(mm), int(aaaa)
    except ValueError:
        return None, None
    if not (1 <= d <= 31 and 1 <= mo <= 12 and 2000 <= y <= 2100):
        return None, None
    return aaaa + mm + dd, "{}/{}/{}".format(dd, mm, aaaa)


def listar_revisiones_html(carpeta, portal_nombre, planta_nombre, tarea_id_a_nombre,
                            contiene=None, minimo_registros=20, nombre_log=''):
    """
    Escanea `carpeta` en busca de ficheros .html con fecha DDMMAAAA en el
    nombre, los decodifica y devuelve [(fecha_display, [registros]), ...]
    ordenado por fecha. Ignora ficheros con menos de `minimo_registros`
    registros reales decodificados (plantillas en blanco u otros HTML sin
    relación con esta hoja de tajos).
    """
    if not os.path.isdir(carpeta):
        return []

    candidatos = []
    for fn in os.listdir(carpeta):
        if not fn.lower().endswith('.html'):
            continue
        if contiene and contiene.upper() not in fn.upper():
            continue
        clave, display = _fecha_desde_nombre(fn)
        if clave:
            candidatos.append((clave, display, fn))
    candidatos.sort(key=lambda x: x[0])

    historial = []
    for _, display, fn in candidatos:
        ruta = os.path.join(carpeta, fn)
        registros = parsear_html(ruta, portal_nombre, planta_nombre, tarea_id_a_nombre,
                                  nombre_log=nombre_log)
        if len(registros) >= minimo_registros:
            if nombre_log:
                print("  [{}] {}: {} registros de '{}'".format(
                    nombre_log, display, len(registros), fn))
            historial.append((display, registros))
        elif nombre_log and registros:
            print("  [{}] '{}' descartado ({} registros, por debajo del minimo {}) "
                  "— probablemente una plantilla en blanco.".format(
                      nombre_log, fn, len(registros), minimo_registros))
    return historial
