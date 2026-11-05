# -*- coding: utf-8 -*-
"""Viviendas por tajo electrico y periodo natural (peticion de Bixente 05/11/2026).

«¿Cuantas viviendas tenemos cableadas?»: por tajo, cuantas viviendas estan X, M,
/, P, ? ahora y cuantas se terminaron en un periodo NATURAL (semana de lunes a
domingo, mes de dia 1 a fin de mes; el periodo en curso llega solo hasta hoy).

Este modulo es la REFERENCIA en Python y prepara los datos que el panel incrusta
en la pagina; el calculo que ve Bixente lo hace ``viviendas_calculo.js`` en el
navegador (asi «hoy» es el dia real) y una prueba exige que den lo mismo.

Reglas del proyecto:
  * M y / solo existen «ahora»: la ficha guarda el ultimo estado, no su historia.
  * Una fecha de carga de historial no es una fecha de obra: esas viviendas no
    cuentan como hechas en el periodo y se enseñan aparte («dudosas»).
  * Una celda inexistente o N no entra en el total; nunca se convierte en cero.
"""
from datetime import date, datetime, timedelta

# Tajos electricos de vivienda (lista confirmada por Bixente el 05/11/2026).
# Quedan fuera los de telecomunicaciones, portero y termostatos.
TAJOS_ELECTRICOS = [
    'rozas_timbres', 'tubeado', 'doblar_cajas', 'cableado', 'embornado',
    'cuadro_mecanizado', 'derivacion_individual', 'cuadros_presentados',
    'placas_tapas', 'apliques', 'casquillos_bombillas',
]

_MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
          'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def _iso(texto):
    try:
        return datetime.strptime(texto, '%d/%m/%Y').date().isoformat()
    except (TypeError, ValueError):
        return None


def _viviendas(ficha):
    salida = []
    for bloque in (ficha.get('estructura') or {}).get('bloques') or []:
        for portal in bloque.get('portales') or []:
            for planta in portal.get('plantas') or []:
                for ub in planta.get('ubicaciones') or []:
                    if ub.get('tipo') == 'vivienda':
                        salida.append((portal.get('id'), planta.get('id'),
                                       ub.get('id')))
    return salida


def datos_para_panel(ficha, catalogo_tajos, tajos_ids=None):
    """Datos en bruto que el panel incrusta: por tajo y vivienda ``[v, f, fiable]``.

    ``fiable`` es 1 si la fecha viene de una revision de campo (hoja), 0 si es
    de una carga de historial o no se sabe de donde sale.
    """
    tajos_ids = tajos_ids or TAJOS_ELECTRICOS
    nombres = {t['id']: t.get('nombre', t['id']) for t in catalogo_tajos or []}
    revisiones = ficha.get('revisiones') or []
    de_campo = {r['id'] for r in revisiones
                if str(r.get('origen') or '').startswith('hoja')}
    fechas_campo = [_iso(r.get('fecha')) for r in revisiones
                    if r['id'] in de_campo]
    fechas_campo = [f for f in fechas_campo if f]
    viviendas = _viviendas(ficha)
    estados = ficha.get('estados') or {}
    celdas, tajos = {}, []
    for tid in tajos_ids:
        filas = []
        for portal, planta, ub in viviendas:
            c = estados.get(f'{portal}__{planta}__{tid}__{ub}')
            if c is None:
                filas.append(['-', None, 0])
            else:
                filas.append([c.get('v'), _iso(c.get('f')),
                              1 if c.get('r') in de_campo else 0])
        if any(f[0] != '-' for f in filas):
            celdas[tid] = filas
            tajos.append({'id': tid, 'nombre': nombres.get(tid, tid)})
    return {'tajos': tajos, 'n_viviendas': len(viviendas), 'celdas': celdas,
            'ultima_revision': max(fechas_campo) if fechas_campo else None}


def contar(datos, tajo_id, desde, hasta):
    """Conteo de un tajo. ``desde``/``hasta`` en ISO o None (sin limite)."""
    r = {'total': 0, 'X': 0, 'M': 0, '/': 0, 'P': 0, '?': 0,
         'hechas': 0, 'dudosas': 0, 'acumuladas': 0, 'sin_fecha': 0}
    sin_periodo = desde is None and hasta is None
    for v, f, fiable in datos['celdas'].get(tajo_id, []):
        if v in ('N', '-'):
            continue
        r['total'] += 1
        r[v if v in ('X', 'M', '/', 'P') else '?'] += 1
        if v != 'X':
            continue
        if sin_periodo:
            r['hechas'] += 1
            r['acumuladas'] += 1
            if f is None:
                r['sin_fecha'] += 1
            continue
        if f is None:
            r['sin_fecha'] += 1
            continue
        if hasta is None or f <= hasta:
            r['acumuladas'] += 1
        if (desde is None or f >= desde) and (hasta is None or f <= hasta):
            r['hechas' if fiable else 'dudosas'] += 1
    return r


def periodo_natural(tipo, hoy):
    """(desde, hasta, etiqueta) en ISO. El periodo en curso termina hoy."""
    if tipo == 'todo':
        return None, None, 'Desde el principio'
    if tipo == 'semana':
        lunes = hoy - timedelta(days=hoy.weekday())
        return lunes.isoformat(), hoy.isoformat(), 'Esta semana'
    if tipo == 'semana_pasada':
        lunes = hoy - timedelta(days=hoy.weekday() + 7)
        return (lunes.isoformat(), (lunes + timedelta(days=6)).isoformat(),
                'Semana pasada')
    if tipo == 'anio':
        return (date(hoy.year, 1, 1).isoformat(), hoy.isoformat(),
                f'Este año ({hoy.year})')
    if tipo == 'anio_anterior':
        a = hoy.year - 1
        return (date(a, 1, 1).isoformat(), date(a, 12, 31).isoformat(),
                f'Año {a}')
    if tipo == 'mes':
        return (hoy.replace(day=1).isoformat(), hoy.isoformat(),
                f'{_MESES[hoy.month - 1].capitalize()} (en curso)')
    if tipo == 'mes_anterior':
        ultimo = hoy.replace(day=1) - timedelta(days=1)
        return (ultimo.replace(day=1).isoformat(), ultimo.isoformat(),
                f'{_MESES[ultimo.month - 1].capitalize()} {ultimo.year}')
    if tipo.startswith('mes:'):
        anio, mes = (int(x) for x in tipo[4:].split('-'))
        primero = date(anio, mes, 1)
        siguiente = (date(anio + 1, 1, 1) if mes == 12
                     else date(anio, mes + 1, 1))
        fin = min(siguiente - timedelta(days=1), hoy)
        return (primero.isoformat(), fin.isoformat(),
                f'{_MESES[mes - 1].capitalize()} {anio}')
    raise ValueError(f'periodo desconocido: {tipo!r}')
