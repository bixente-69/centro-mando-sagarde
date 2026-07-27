# -*- coding: utf-8 -*-
"""
MEMORIA DE OBRA (capa 1.5 - acumulacion entre revisiones)
----------------------------------------------------------
Las hojas de revision omiten tajos que el equipo ya da por terminados.
Esta capa mantiene un registro persistente JSON de TODOS los tajos vistos
a lo largo del historial de una obra. Cuando un tajo desaparece de la
ultima revision, se marca como terminado (100%) en la memoria.

Fichero generado en: INFORME SAGARDE IA/memoria_obra.json
"""
import json
import os
from datetime import datetime

VERSION = 1


def calcular_memoria(historial):
    """
    Construye el diccionario de memoria a partir del historial completo.

    Logica:
    - Acumula todos los tajos vistos en todas las revisiones.
    - Un tajo 'terminado' es aquel que aparecio en al menos una revision
      pero ya NO aparece en la ultima.
    - 'terminado_desde' es la primera revision en que deja de verse.

    Returns: dict {nombre_tajo: {primera_revision, ultima_revision_activa,
                                  terminado, terminado_desde,
                                  n_registros_ultima_activa}}
    """
    if not historial:
        return {}

    memoria = {}
    ultima_idx_tajo = {}  # nombre -> (indice_en_historial, fecha, n_registros)

    for idx, (fecha, registros) in enumerate(historial):
        agrupados = {}
        for r in registros:
            t = (r.get('task') or '').strip()
            if t:
                agrupados.setdefault(t, []).append(r)
        for nombre, recs in agrupados.items():
            if nombre not in memoria:
                memoria[nombre] = {'primera_revision': fecha}
            ultima_idx_tajo[nombre] = (idx, fecha, len(recs))

    if not memoria:
        return {}

    tajos_ultima = {(r.get('task') or '').strip() for r in historial[-1][1]
                    if (r.get('task') or '').strip()}

    for nombre in memoria:
        idx, ultima_fecha, n_recs = ultima_idx_tajo[nombre]
        memoria[nombre]['ultima_revision_activa'] = ultima_fecha
        memoria[nombre]['n_registros_ultima_activa'] = n_recs
        if nombre in tajos_ultima:
            memoria[nombre]['terminado'] = False
            memoria[nombre]['terminado_desde'] = None
        else:
            memoria[nombre]['terminado'] = True
            memoria[nombre]['terminado_desde'] = _primera_ausencia(
                historial, nombre, idx
            )

    return memoria


def _primera_ausencia(historial, tajo, ultima_presente_idx):
    """Primera fecha (tras ultima_presente_idx) en que el tajo no aparece."""
    for fecha, registros in historial[ultima_presente_idx + 1:]:
        presentes = {(r.get('task') or '').strip() for r in registros}
        if tajo not in presentes:
            return fecha
    return historial[-1][0]


def cargar_memoria(path):
    """Carga un JSON de memoria; devuelve {} si no existe o esta corrupto."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return data.get('tajos', {})
    except Exception:
        return {}


def guardar_memoria(path, obra, historial, tajos):
    """Serializa la memoria al JSON de la obra."""
    n_term = sum(1 for v in tajos.values() if v.get('terminado'))
    data = {
        'version': VERSION,
        'obra': obra,
        'generado': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'ultima_revision': historial[-1][0] if historial else '—',
        'n_revisiones': len(historial),
        'resumen': {
            'total_tajos': len(tajos),
            'activos': len(tajos) - n_term,
            'terminados': n_term,
        },
        'tajos': tajos,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data['resumen']
