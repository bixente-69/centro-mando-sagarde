# -*- coding: utf-8 -*-
"""
MOTOR DE INFORME SAGARDE IA  (capa 2 - codigo, sin IA, coste cero)
--------------------------------------------------------------------
Genera un informe HTML interactivo (KPIs + graficos + tablas) a partir de
registros YA NORMALIZADOS a un esquema comun. No sabe nada de como esta
construida la hoja de revisiones de cada obra en concreto -- de eso se
encarga el "adaptador" de cada obra (ver carpeta adaptadores/).

Esquema de registro estandar (un dict por cada tarea x planta x edificio x
vivienda/mano, en una fecha de revision concreta):

    {
        "task":     "Tabicado",        # nombre de la tarea/partida
        "floor":    "PB",              # planta
        "building": "ZR1.1",           # edificio / bloque / portal
        "unit":     "A2",              # vivienda, local o mano
        "status":   "X",               # 'X' terminado, 'M' >50%, '/' <50%, '' no iniciado
    }

Un "historial" es una lista de tuplas (fecha_str, lista_de_registros), una
por cada revision encontrada, ordenada cronologicamente. El "snapshot" es
la lista de registros de la revision mas reciente.

Este fichero NO se debe tocar por obra. Si una obra necesita otra logica de
lectura, se escribe un adaptador nuevo; el motor es siempre el mismo.
"""
import json
import os
from collections import defaultdict
from datetime import datetime

# Peso de "M" unificado a 0.60 (25/07/2026) para coincidir con ESTADO_VALOR
# de priorizador_trabajos.py. Antes eran 0.75 aquí y 0.60 allí: dos criterios
# distintos para el mismo estado. Si cambia este valor, cambiar también
# ESTADO_VALOR en priorizador_trabajos.py para mantenerlos iguales.
SCORE = {'X': 1.0, 'M': 0.60, '/': 0.25, '': 0.0}
ESTADO_LABEL = {'X': 'Terminado (100%)', 'M': 'Avanzado (>50%)', '/': 'Iniciado (<50%)', '': 'No iniciado'}


# ---------------------------------------------------------------------------
# Calculo de metricas
# ---------------------------------------------------------------------------

def _pct_ponderado(records):
    """% de avance dando peso parcial a M y '/'. Es una ESTIMACION, no un hecho."""
    if not records:
        return 0.0
    return sum(SCORE.get(r['status'], 0) for r in records) / len(records) * 100


def _pct_estricto(records):
    """% estricto: solo cuenta como avance lo marcado como X (terminado)."""
    if not records:
        return 0.0
    return sum(1 for r in records if r['status'] == 'X') / len(records) * 100


def _agrupar(records, *keys):
    grupos = defaultdict(list)
    for r in records:
        k = tuple(r[key] for key in keys)
        grupos[k if len(keys) > 1 else k[0]].append(r)
    return grupos


def _floor_key(f):
    if f == 'PB':
        return (0, 0)
    try:
        return (1, int(f))
    except ValueError:
        return (2, str(f))


def kpis_snapshot(snapshot):
    total = len(snapshot)
    x = sum(1 for r in snapshot if r['status'] == 'X')
    m = sum(1 for r in snapshot if r['status'] == 'M')
    s = sum(1 for r in snapshot if r['status'] == '/')
    v = total - x - m - s
    return {
        'total': total, 'x': x, 'm': m, 'slash': s, 'vacio': v,
        'pct_estricto': round(_pct_estricto(snapshot), 1),
        'pct_ponderado': round(_pct_ponderado(snapshot), 1),
    }


def cobertura_encogida(historial, umbral=0.5):
    """Devuelve el motivo si la ultima revision cubre bastantes menos
    ubicaciones que la anterior, o None si no hay nada que avisar.

    TODO el calculo de una obra se hace sobre `historial[-1]`: el sistema
    interpreta la ultima hoja como el estado completo de la obra. Eso vale
    mientras cada revision cubra la obra entera; si una cubre solo un trozo,
    la obra ENCOGE a ese trozo y el porcentaje publicado pasa a calcularse
    sobre una fraccion.

    Caso real (Obispo Orueta, 27/07/2026): una hoja de "2a fase" con 40
    celdas de dos viviendas nuevas de PB dejo fuera 107 ubicaciones y el
    panel publico un 80.0% sobre esas 40, frente al 62.1% sobre 1288 de la
    revision anterior. No salto ningun aviso.

    Esto NO corrige el porcentaje: lo corrige la ficha de obra, que acumula
    en vez de sustituir (ver `generar_todos.registro_revision_desde_ficha`).
    Sirve para que las obras que aun no tienen ficha no fallen en silencio.

    Se cuentan UBICACIONES (edificio, planta, vivienda), no celdas: una hoja
    con menos tajos no es una revision parcial, pero una hoja donde
    desaparecen viviendas enteras si lo es.
    """
    if len(historial) < 2:
        return None

    def _ubicaciones(registros):
        return {(r.get('building'), r.get('floor'), r.get('unit'))
                for r in registros}

    fecha_previa, previos = historial[-2]
    fecha_ultima, ultimos = historial[-1]
    antes = _ubicaciones(previos)
    ahora = _ubicaciones(ultimos)
    if not antes or len(ahora) >= len(antes) * umbral:
        return None

    huerfanas = len(antes - ahora)
    return (f'la revision {fecha_ultima} cubre {len(ahora)} ubicaciones '
            f'frente a {len(antes)} de {fecha_previa}: {huerfanas} se quedan '
            f'sin datos nuevos y el porcentaje se calcula solo sobre lo que '
            f'cubre esta hoja')


def detectar_bloqueos(snapshot):
    """
    Heuristica generica (no usa umbrales fijos por obra, compara cada grupo
    contra la media de su propio edificio/planta, para que se adapte sola
    al nivel de avance general de la obra):

      1) Plantas de un edificio muy por debajo de la media de ESE edificio.
      2) Viviendas/manos practicamente sin iniciar mientras el resto de su
         misma planta+edificio ya tiene avance relevante.
    """
    bloqueos = []

    por_edificio = _agrupar(snapshot, 'building')
    por_planta_ed = _agrupar(snapshot, 'floor', 'building')
    for edificio, recs_ed in por_edificio.items():
        media_ed = _pct_ponderado(recs_ed)
        for (floor, building), recs in por_planta_ed.items():
            if building != edificio:
                continue
            p = _pct_ponderado(recs)
            if p < 60 and (media_ed - p) > 15:
                bloqueos.append({
                    'tipo': 'Planta rezagada',
                    'edificio': building, 'planta': floor, 'unidad': '-',
                    'avance': round(p, 1), 'referencia': round(media_ed, 1),
                    'motivo': f"Planta {floor} de {building} al {p:.0f}% frente a una media de edificio del {media_ed:.0f}%.",
                })

    por_unidad = _agrupar(snapshot, 'floor', 'building', 'unit')
    grupos_planta_ed = defaultdict(list)
    for (floor, building, unit), recs in por_unidad.items():
        grupos_planta_ed[(floor, building)].append((unit, recs))

    for (floor, building), unidades in grupos_planta_ed.items():
        if len(unidades) < 2:
            continue
        pcts = [(u, _pct_ponderado(r)) for u, r in unidades]
        media = sum(p for _, p in pcts) / len(pcts)
        for unit, p in pcts:
            if p < 15 and (media - p) > 30:
                bloqueos.append({
                    'tipo': 'Vivienda/mano sin iniciar',
                    'edificio': building, 'planta': floor, 'unidad': unit,
                    'avance': round(p, 1), 'referencia': round(media, 1),
                    'motivo': f"{unit} (planta {floor}, {building}) al {p:.0f}% mientras la media de su planta es {media:.0f}%.",
                })

    return sorted(bloqueos, key=lambda b: b['avance'])


def sin_cambios_entre_ultimas(historial):
    """True si las dos ultimas revisiones son identicas celda a celda."""
    if len(historial) < 2:
        return False
    (_, r1), (_, r2) = historial[-2], historial[-1]
    key = lambda r: (r['task'], r['floor'], r['building'], r['unit'])
    return {key(r): r['status'] for r in r1} == {key(r): r['status'] for r in r2}


def serie_tiempo(historial):
    out = []
    for fecha, recs in historial:
        out.append({
            'fecha': fecha,
            'pct_estricto': round(_pct_estricto(recs), 1),
            'pct_ponderado': round(_pct_ponderado(recs), 1),
            'total': len(recs),
        })
    return out


def matriz_planta_edificio(snapshot):
    plantas = sorted({r['floor'] for r in snapshot}, key=_floor_key)
    edificios = sorted({r['building'] for r in snapshot})
    por_pe = _agrupar(snapshot, 'floor', 'building')
    series = {}
    for ed in edificios:
        series[ed] = [round(_pct_ponderado(por_pe.get((pl, ed), [])), 1) for pl in plantas]
    return {'labels': plantas, 'series': series}


def ranking_tareas(snapshot):
    por_tarea = _agrupar(snapshot, 'task')
    filas = [(t, round(_pct_ponderado(r), 1), len(r)) for t, r in por_tarea.items()]
    return sorted(filas, key=lambda x: x[1])


def ranking_tareas_con_memoria(snapshot, tajos_memoria=None):
    """
    Como ranking_tareas pero anade los tajos 'terminados' de la memoria
    (ausentes del snapshot actual) al 100%, ya que desaparecieron de la
    hoja de revision porque el equipo los dio por completados.
    """
    por_tarea = _agrupar(snapshot, 'task')
    filas = [(t, round(_pct_ponderado(r), 1), len(r)) for t, r in por_tarea.items()]

    if tajos_memoria:
        activos = {t for t, _, _ in filas}
        for nombre, info in tajos_memoria.items():
            if info.get('terminado') and nombre not in activos:
                n = info.get('n_registros_ultima_activa', 0)
                filas.append((nombre, 100.0, n))

    return sorted(filas, key=lambda x: x[1])


def tabla_detalle(snapshot):
    por_pe = _agrupar(snapshot, 'floor', 'building')
    filas = []
    for (pl, ed), recs in por_pe.items():
        filas.append({
            'planta': pl, 'edificio': ed,
            'pct_estricto': round(_pct_estricto(recs), 1),
            'pct_ponderado': round(_pct_ponderado(recs), 1),
            'n': len(recs),
        })
    filas.sort(key=lambda f: (f['edificio'], _floor_key(f['planta'])))
    return filas



