# -*- coding: utf-8 -*-
"""Prevalida y aplica las ultimas revisiones SAGARDE de viviendas y garaje."""
from __future__ import annotations

import argparse
import ast
import copy
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime


def _find_workspace():
    for parent in Path(__file__).resolve().parents:
        if (parent / 'SAGARDE OBRAS ABIERTAS').is_dir():
            return parent
    raise RuntimeError('no se encuentra la raiz que contiene SAGARDE OBRAS ABIERTAS')


WORKSPACE = _find_workspace()
OPEN_WORKS = WORKSPACE / 'SAGARDE OBRAS ABIERTAS'
SYSTEM = OPEN_WORKS / '_SISTEMA INFORME SAGARDE IA'


def _load_system():
    for path in (SYSTEM, SYSTEM / 'adaptadores'):
        value = os.fspath(path)
        if value not in sys.path:
            sys.path.insert(0, value)

    global adaptar_revision_garaje, adaptar_revision_html
    global alta_garaje_desde_hoja, aplicar_revision, ficha_garajes
    global ficha_obra, lector_hoja_tajos_html, registro_obras
    global validar_revision
    import adaptar_revision_garaje
    import adaptar_revision_html
    import alta_garaje_desde_hoja
    import aplicar_revision
    import ficha_garajes
    import ficha_obra
    import lector_hoja_tajos_html
    import registro_obras
    import validar_revision


def _fold(value):
    return str(value or '').strip().casefold()


def _resolve_work(query):
    wanted = _fold(query)
    matches = []
    for work in registro_obras.OBRAS:
        names = [work.get('id'), work.get('nombre')]
        names.extend(work.get('aliases') or [])
        if wanted in {_fold(name) for name in names}:
            matches.append(work)
    if len(matches) != 1:
        known = ', '.join(work['id'] for work in registro_obras.OBRAS)
        raise ValueError(
            f'obra {query!r} no resuelta de forma unica; ids conocidos: {known}')
    return matches[0]


def _revision_folders(work_dir):
    folders = [
        work_dir / name for name in ('REVISIONES', 'REVISIONES SAGARDE')
        if (work_dir / name).is_dir()
    ]
    return folders


def _dated_htmls(folders, garage):
    found = []
    for folder in folders:
        for path in folder.iterdir():
            if not path.is_file() or path.suffix.casefold() != '.html':
                continue
            is_garage = 'garaje' in path.stem.casefold()
            if is_garage != garage:
                continue
            _key, display = lector_hoja_tajos_html._fecha_desde_nombre(path.name)
            if display is None:
                continue
            date = datetime.strptime(display, '%d/%m/%Y')
            found.append((date, path.stat().st_mtime_ns, path.name.casefold(),
                          path, display))
    return sorted(found)


def _latest_html(folders, garage):
    found = _dated_htmls(folders, garage)
    return found[-1] if found else None


def _warning_states(path, warnings):
    raw = dict(lector_hoja_tajos_html.extraer_pares(os.fspath(path)))
    states = Counter()
    for warning in warnings:
        match = re.search(r"clave HTML sin resolver ('.*?'): ", warning)
        if match is None:
            states['<sin_clave>'] += 1
            continue
        try:
            key = ast.literal_eval(match.group(1))
        except (ValueError, SyntaxError):
            states['<sin_clave>'] += 1
            continue
        states[raw.get(key, '<sin_estado>')] += 1
    return states


def _housing_plan(work, work_dir, candidate, catalog):
    if candidate is None:
        return {'kind': 'viviendas', 'source': None, 'blockers': [],
                'summary': 'sin hoja HTML de viviendas'}
    _date, _mtime, _name, path, display = candidate
    current = ficha_obra.cargar(os.fspath(work_dir))
    if current is None:
        return {'kind': 'viviendas', 'source': path, 'date': display,
                'blockers': ['falta ficha_obra.json'],
                'summary': 'sin base de viviendas'}

    revision = adaptar_revision_html.construir_revision_normalizada_html(
        os.fspath(path), work['id'], current, catalog,
        portal_id_a_real=work.get('mapa_portales_revision_html'),
        planta_id_a_real=work.get('mapa_plantas_revision_html'),
        tarea_id_a_real=work.get('mapa_tajos_revision_html'),
        fecha=display,
    )
    result = aplicar_revision.apply_revision(
        revision, current, catalog, dry_run=False)
    warnings = revision['metadata']['avisos']
    warning_states = _warning_states(path, warnings)
    blockers = list(result.get('errores') or [])
    blockers.extend(
        f"{item.get('clave')}: {item.get('motivo')}"
        for item in result.get('rechazadas') or [])
    non_n_warnings = sum(
        count for state, count in warning_states.items() if state != 'N')
    if non_n_warnings:
        blockers.append(
            f'{non_n_warnings} celda(s) no resuelta(s) con dato distinto de N')
    has_marks = any(
        cell['estado_leido'] in {'X', 'M', '/'}
        for cell in revision['celdas'])
    already = any(
        item.get('id') == revision['revision_id']
        or item.get('fecha') == display
        for item in current.get('revisiones') or [])
    if already:
        # La hoja ya forma parte de la ficha: sus avisos historicos se
        # muestran en el resumen, pero no pueden bloquear una pasada --all
        # que no va a volver a escribirla.
        blockers = []
    return {
        'kind': 'viviendas', 'source': path, 'date': display,
        'revision': revision, 'result': result, 'blockers': blockers,
        'warnings': warning_states, 'already': already,
        'skip': not has_marks,
        'summary': (
            f"{len(revision['celdas'])} celdas, "
            f"{result['resumen']['cambios']} cambios, "
            f"avisos={dict(warning_states)}, "
            f"marcas_explicitas={'si' if has_marks else 'no'}"),
    }


def _garage_plan(work, work_dir, candidate, catalog):
    if candidate is None:
        return {'kind': 'garaje', 'source': None, 'blockers': [],
                'summary': 'sin hoja HTML de garaje'}
    _date, _mtime, _name, path, display = candidate
    current = ficha_garajes.cargar(os.fspath(work_dir))
    needs_initial = current is None
    blockers = []
    if needs_initial:
        try:
            data = alta_garaje_desde_hoja.extraer_estructura(os.fspath(path))
            current = alta_garaje_desde_hoja.construir_ficha(
                data, work['nombre'], catalog)
        except (OSError, ValueError, KeyError) as exc:
            blockers.append(f'no se puede dar de alta el garaje: {exc}')
            return {'kind': 'garaje', 'source': path, 'date': display,
                    'blockers': blockers, 'summary': blockers[0]}

    snapshot, warnings = adaptar_revision_garaje.construir_snapshot(
        os.fspath(path), work['nombre'], catalog)
    _simulated, changes = ficha_garajes.actualizar_desde_snapshot(
        copy.deepcopy(current), snapshot, display)
    unknown_zones = changes.get('zonas_desconocidas') or []
    if warnings:
        blockers.append(f'{len(warnings)} clave(s) de garaje no resuelta(s)')
    if unknown_zones:
        blockers.append(f'{len(unknown_zones)} zona(s) de garaje descartada(s)')
    revision_id = 'rev_' + display.replace('/', '')
    has_marks = any(
        item.get('status') in {'X', 'M', '/'} for item in snapshot)
    already = any(
        item.get('id') == revision_id
        or item.get('fecha') == display
        for item in current.get('revisiones') or [])
    if already:
        blockers = []
    changed = len(changes.get('estados_cambiados') or [])
    new = changes.get('estados_nuevos') or 0
    return {
        'kind': 'garaje', 'source': path, 'date': display,
        'blockers': blockers, 'warnings': warnings,
        'unknown_zones': unknown_zones, 'already': already,
        'skip': not has_marks,
        'needs_initial': needs_initial, 'snapshot': snapshot,
        'summary': (
            f'{len(snapshot)} celdas, {changed} cambios, {new} nuevas, '
            f'{len(warnings)} avisos, {len(unknown_zones)} zonas descartadas, '
            f"marcas_explicitas={'si' if has_marks else 'no'}"),
    }


def _backup(path):
    if not path.is_file():
        return None
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    target = path.with_name(f'{path.name}.antes_actualizar_{stamp}.bak')
    shutil.copy2(path, target)
    return target


def _run(command, cwd=SYSTEM):
    subprocess.run(
        [os.fspath(item) for item in command], cwd=os.fspath(cwd), check=True)


def _apply_work(work, work_dir, plans):
    applied = 0
    for plan in plans:
        source = plan.get('source')
        if source is None or plan.get('already') or plan.get('skip'):
            continue
        if plan['kind'] == 'viviendas':
            _backup(work_dir / 'INFORME SAGARDE IA' / 'ficha_obra.json')
            _run([
                sys.executable, SYSTEM / 'leer_hoja_marcada.py', source,
                work['id'], '--digital', '--fecha', plan['date'], '--escribir',
            ])
        else:
            garage_file = work_dir / 'INFORME SAGARDE IA' / 'ficha_garajes.json'
            if plan.get('needs_initial'):
                _run([
                    sys.executable, SYSTEM / 'alta_garaje_desde_hoja.py',
                    source, work['id'],
                ])
            else:
                _backup(garage_file)
            _run([
                sys.executable, SYSTEM / 'adaptar_revision_garaje.py',
                source, work['id'], '--fecha', plan['date'],
            ])
        applied += 1
    return applied


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('obras', nargs='*', help='ids, nombres o alias de obra')
    parser.add_argument('--all', action='store_true',
                        help='revisa todas las obras de registro_obras.py')
    parser.add_argument('--apply', action='store_true',
                        help='escribe las fichas y regenera los informes')
    parser.add_argument('--skip-regenerate', action='store_true',
                        help='con --apply, no ejecuta generar_todos.py')
    args = parser.parse_args(argv)

    if args.all and args.obras:
        parser.error('usa nombres concretos o --all, no ambos a la vez')
    if not args.all and not args.obras:
        parser.error('indica al menos una obra o usa --all')

    _load_system()
    catalog = validar_revision.cargar_catalogo_tajos()
    queries = (
        [work['id'] for work in registro_obras.OBRAS]
        if args.all else args.obras)
    all_plans = []
    seen = set()
    for query in queries:
        work = _resolve_work(query)
        if work['id'] in seen:
            continue
        seen.add(work['id'])
        work_dir = OPEN_WORKS / work['carpeta_obra']
        revisions = _revision_folders(work_dir)
        plans = [
            _housing_plan(work, work_dir, _latest_html(revisions, False), catalog),
            _garage_plan(work, work_dir, _latest_html(revisions, True), catalog),
        ]
        all_plans.append((work, work_dir, plans))
        print(f'\n{work["nombre"]}')
        for plan in plans:
            source = plan.get('source')
            label = source.name if source else '-'
            if source is None:
                status = 'SIN HOJA HTML'
            elif plan.get('already'):
                status = 'YA APLICADA'
            elif plan.get('skip'):
                status = 'SIN MARCAS'
            else:
                status = 'PENDIENTE'
            if plan.get('blockers'):
                status = 'BLOQUEADA'
            print(f'  {plan["kind"]}: {label} [{status}]')
            print(f'    {plan["summary"]}')
            for blocker in plan.get('blockers') or []:
                print(f'    BLOQUEO: {blocker}')

    blockers = [
        blocker
        for _work, _dir, plans in all_plans
        for plan in plans for blocker in plan.get('blockers') or []
    ]
    if blockers:
        print('\n[ABORTADO] Hay bloqueos. No se ha escrito ninguna ficha.')
        return 2
    if not args.apply:
        print('\n[SIMULACION] Todo validado; usa --apply para escribir y regenerar.')
        return 0

    applied = sum(
        _apply_work(work, work_dir, plans)
        for work, work_dir, plans in all_plans)
    if applied and not args.skip_regenerate:
        _run([sys.executable, SYSTEM / 'generar_todos.py'])
    print(f'\n[OK] Actualizacion terminada: {applied} revision(es) aplicada(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
