# -*- coding: utf-8 -*-
"""
generar_informe_ejecutivo.py — Informe Ejecutivo Eléctrico Sagarde

Genera un PDF vectorial con una página A4 de resumen general y, cuando la obra
tiene varios portales o bloques, una página A4 adicional por cada uno, con la
identidad corporativa de Montajes Eléctricos Sagarde, S.L.

Uso:
    python _SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py --obra "2026 BOLUETA ACR"
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import importlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image, KeepTogether, PageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String, Line, PolyLine, Circle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# _SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py -> cuatro niveles.
ROOT = Path(__file__).resolve().parent.parent.parent.parent
OBRAS_DIR = ROOT / "SAGARDE OBRAS ABIERTAS"
MOTOR_IA_DIR = OBRAS_DIR / "_SISTEMA INFORME SAGARDE IA"
ASSETS_DIR = ROOT / "_SISTEMA" / "MOTOR" / "assets"
LOGO_PATH = ASSETS_DIR / "logo_sagarde.jpg"
FONTS_DIR = ASSETS_DIR / "fonts"
FUENTE = 'IBMPlexSans'
FUENTE_BOLD = 'IBMPlexSans-Bold'
CATALOGO_PATH = MOTOR_IA_DIR / "reglas" / "CATALOGO_TAJOS.json"


def _registrar_fuentes() -> None:
    '''Registra IBM Plex Sans para el informe.

    Falla a gritos si falta la tipografia. Volver a Helvetica en silencio
    produciria un informe con el aspecto de siempre y nadie se enteraria: es
    exactamente el fallo que este trabajo viene a quitar.
    '''
    if FUENTE in pdfmetrics.getRegisteredFontNames():
        return
    ficheros = {
        FUENTE: FONTS_DIR / 'IBMPlexSans-Regular.ttf',
        FUENTE_BOLD: FONTS_DIR / 'IBMPlexSans-Bold.ttf',
    }
    faltan = [str(ruta) for ruta in ficheros.values() if not ruta.is_file()]
    if faltan:
        raise RuntimeError(
            'Falta la tipografia del informe ejecutivo: ' + ', '.join(faltan) +
            '. Se descarga segun la Tarea 1 de _SISTEMA/docs/superpowers/'
            'plans/2026-08-13-informe-ejecutivo-caracter.md')
    for nombre, ruta in ficheros.items():
        pdfmetrics.registerFont(TTFont(nombre, str(ruta)))
    # Sin esta linea los <b> del informe dejan de tener efecto SIN dar error.
    pdfmetrics.registerFontFamily(
        FUENTE, normal=FUENTE, bold=FUENTE_BOLD,
        italic=FUENTE, boldItalic=FUENTE_BOLD)

if str(MOTOR_IA_DIR) not in sys.path:
    sys.path.append(str(MOTOR_IA_DIR))

import motor_informes
import ficha_obra as fichas
import priorizador_trabajos
from registro_obras import OBRAS, resolver_obra


def _cargar_adaptadores():
    """Deriva nombre/alias -> módulo desde el registro único de obras."""
    resultado = {}
    for obra in OBRAS:
        modulo = importlib.import_module(
            f"adaptadores.{obra['adaptador']}")
        for nombre in [obra['nombre'], *obra.get('aliases', [])]:
            resultado[nombre] = modulo
    return resultado


# Compatibilidad con las llamadas y pruebas existentes. El mapa ya no se
# mantiene a mano: nace siempre de registro_obras.OBRAS.
ADAPTADORES = _cargar_adaptadores()


def _fold(valor: object) -> str:
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', texto.casefold()).strip()


def _texto(valor: object) -> str:
    return escape(str(valor or '').strip())


def _valor_ejecutivo(valor: object, limite: int = 105) -> str:
    texto = str(valor or '').strip()
    if not texto or texto.startswith('['):
        return ''
    texto = texto.split(' [', 1)[0].strip()
    return texto if len(texto) <= limite else texto[:limite - 1].rstrip() + '…'


def _cargar_catalogo_tajos() -> list[dict]:
    try:
        datos = json.loads(CATALOGO_PATH.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    return datos.get('tajos') or []


def _indice_metadatos_tajos(ficha: dict | None) -> tuple[dict, dict]:
    '''Devuelve índices por id y nombre/alias.

    La ficha de la obra manda sobre el catálogo general: es la base viva que
    confirma qué tajos aplican y quién los ejecuta en esa obra concreta.
    '''
    por_id: dict[str, dict] = {}
    por_nombre: dict[str, dict] = {}

    for tajo in _cargar_catalogo_tajos():
        meta = dict(tajo)
        por_id[meta['id']] = meta
        for nombre in [meta.get('nombre'), *(meta.get('aliases') or [])]:
            if nombre:
                por_nombre[_fold(nombre)] = meta

    for tajo in ((ficha or {}).get('tajos') or {}).get('detalle') or []:
        anterior = por_id.get(tajo.get('id'), {})
        meta = {**anterior, **tajo}
        if not meta.get('id'):
            continue
        por_id[meta['id']] = meta
        nombres = [meta.get('nombre'), *(anterior.get('aliases') or [])]
        for nombre in nombres:
            if nombre:
                por_nombre[_fold(nombre)] = meta

    return por_id, por_nombre


def _filtrar_snapshot_sagarde(
    snapshot: list[dict],
    metadatos_por_nombre: dict,
    referencias: set[str] | None = None,
) -> list[dict]:
    '''Filtra exclusivamente producción cuya propiedad es Sagarde.'''
    refs = {_fold(x) for x in (referencias or set()) if x}
    salida = []
    for registro in snapshot or []:
        if refs and _fold(registro.get('building')) not in refs:
            continue
        meta = metadatos_por_nombre.get(_fold(registro.get('task')))
        if meta and meta.get('propiedad') == 'propio':
            salida.append(registro)
    return salida


def _resumen_tajos_sagarde(snapshot: list[dict], metadatos_por_nombre: dict) -> list[dict]:
    por_tarea = motor_informes._agrupar(snapshot, 'task')
    salida = []
    for nombre, registros in por_tarea.items():
        meta = metadatos_por_nombre.get(_fold(nombre), {})
        x = sum(1 for r in registros if r.get('status') == 'X')
        marcha = sum(1 for r in registros if r.get('status') in ('M', '/'))
        total = len(registros)
        salida.append({
            'id': meta.get('id') or _fold(nombre),
            'nombre': nombre,
            'fase': meta.get('fase') or 'Sin clasificar',
            'orden': meta.get('orden', 9999),
            'pct': motor_informes._pct_ponderado(registros),
            'x': x,
            'marcha': marcha,
            'pendiente': total - x - marcha,
            'total': total,
        })
    return sorted(salida, key=lambda t: (t['orden'], _fold(t['nombre'])))


def _resumen_fases_sagarde(snapshot: list[dict], metadatos_por_nombre: dict) -> list[dict]:
    grupos: dict[str, list] = defaultdict(list)
    ordenes: dict[str, int] = {}
    for registro in snapshot:
        meta = metadatos_por_nombre.get(_fold(registro.get('task')), {})
        fase = meta.get('fase') or 'Sin clasificar'
        grupos[fase].append(registro)
        ordenes[fase] = min(ordenes.get(fase, 9999), meta.get('orden', 9999))
    salida = []
    for fase, registros in grupos.items():
        salida.append({
            'fase': fase,
            'orden': ordenes[fase],
            'pct': motor_informes._pct_ponderado(registros),
            'x': sum(1 for r in registros if r.get('status') == 'X'),
            'total': len(registros),
        })
    return sorted(salida, key=lambda x: (x['orden'], _fold(x['fase'])))


def _serie_avance_sagarde(
    historial: list | None,
    metadatos_por_nombre: dict,
    referencias: set[str] | None = None,
) -> list[dict]:
    salida = []
    for fecha, snapshot in historial or []:
        propios = _filtrar_snapshot_sagarde(snapshot, metadatos_por_nombre, referencias)
        if not propios:
            continue
        salida.append({
            'fecha': fecha,
            'pct': round(motor_informes._pct_ponderado(propios), 1),
            'estricto': round(motor_informes._pct_estricto(propios), 1),
            'total': len(propios),
        })
    return salida


def _fila_en_alcance(fila: dict, referencias: set[str] | None) -> bool:
    if not referencias:
        return True
    refs = {_fold(x) for x in referencias if x}
    return _fold(fila.get('edificio')) in refs


def _frentes_sagarde(
    prioridades: dict | None,
    metadatos_por_id: dict,
    referencias: set[str] | None = None,
) -> list[dict]:
    grupos: dict[str, dict] = {}
    for fila in (prioridades or {}).get('detalle_items') or []:
        if fila.get('propiedad') != 'propio' or fila.get('categoria') != 'VIABLE':
            continue
        if not _fila_en_alcance(fila, referencias):
            continue
        tajo_id = fila.get('tarea_id') or _fold(fila.get('trabajo'))
        meta = metadatos_por_id.get(tajo_id, {})
        grupo = grupos.setdefault(tajo_id, {
            'trabajo': fila.get('trabajo') or meta.get('nombre') or tajo_id,
            'fase': fila.get('fase_nombre') or meta.get('fase') or 'Sin clasificar',
            'orden': fila.get('orden_ejecucion', meta.get('orden', 9999)),
            'unidades': 0,
            'ubicaciones': set(),
        })
        grupo['unidades'] += 1
        grupo['ubicaciones'].add((fila.get('edificio'), fila.get('planta')))
    return sorted(grupos.values(), key=lambda x: (x['orden'], -x['unidades'], _fold(x['trabajo'])))


def _bloqueadores_sagarde(
    prioridades: dict | None,
    metadatos_por_id: dict,
    referencias: set[str] | None = None,
) -> list[dict]:
    '''Resume dependencias realmente incumplidas de tajos propios.'''
    grupos: dict[tuple, dict] = {}
    for fila in (prioridades or {}).get('detalle_items') or []:
        if fila.get('propiedad') != 'propio' or fila.get('categoria') != 'BLOQUEADO':
            continue
        if not _fila_en_alcance(fila, referencias):
            continue
        for dep in fila.get('dependencias_detalle') or []:
            if dep.get('cumplida'):
                continue
            dep_id = dep.get('id') or _fold(dep.get('nombre'))
            meta = metadatos_por_id.get(dep_id, {})
            propiedad = meta.get('propiedad') or 'desconocido'
            clave = (dep_id, propiedad)
            grupo = grupos.setdefault(clave, {
                'id': dep_id,
                'trabajo': dep.get('nombre') or meta.get('nombre') or dep_id,
                'propiedad': propiedad,
                'estado': dep.get('estado') or 'Pendiente',
                'afecta_celdas': 0,
                'tajos_sagarde': set(),
                'ubicaciones': set(),
            })
            grupo['afecta_celdas'] += 1
            grupo['tajos_sagarde'].add(fila.get('trabajo') or fila.get('tarea_id'))
            grupo['ubicaciones'].add((fila.get('edificio'), fila.get('planta')))

    prioridad_propiedad = {'externo': 0, 'coordinacion': 0, 'propio': 1, 'desconocido': 2}
    return sorted(
        grupos.values(),
        key=lambda x: (
            prioridad_propiedad.get(x['propiedad'], 2),
            -x['afecta_celdas'],
            _fold(x['trabajo']),
        ),
    )

# ─── Identidad Visual Sagarde ──────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN_X = 12 * mm
MARGIN_Y = 10 * mm

COL_NAVY   = colors.HexColor('#0B1F3A')
COL_BRAND  = colors.HexColor('#B42318')
COL_ACCENT = colors.HexColor('#123A63')
COL_LIGHT  = colors.HexColor('#F8FAFC')
COL_CARD   = colors.HexColor('#EEF4FF')
COL_LINE   = colors.HexColor('#D0D5DD')
COL_WARN   = colors.HexColor('#D9483C')
COL_OK     = colors.HexColor('#2E9E5B')
COL_MUTED  = colors.HexColor('#475467')


def _style(name: str, size: float, bold: bool = False, align: int = TA_LEFT, color: colors.Color = colors.black, leading: float | None = None) -> ParagraphStyle:
    lead = leading if leading is not None else size * 1.25
    return ParagraphStyle(
        name, fontSize=size, leading=lead,
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        alignment=align, textColor=color
    )


def _make_mini_bar(pct: float, w_mm: float = 34) -> Table:
    fill_w = max(1, min(w_mm, (pct / 100.0) * w_mm))
    rem_w = max(0, w_mm - fill_w)
    col = colors.HexColor('#2E9E5B') if pct >= 70 else colors.HexColor('#E07B1A') if pct >= 40 else colors.HexColor('#D9483C')
    t = Table([['', '']], colWidths=[fill_w * mm, rem_w * mm], rowHeights=[3.5 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), col),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#E2E8F0')),
        ('BOX', (0,0), (-1,-1), 0.4, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    return t


def _color_pct(pct: float):
    if pct >= 70:
        return COL_OK
    if pct >= 40:
        return colors.HexColor('#E07B1A')
    return COL_WARN


def _grafico_tendencia(serie: list[dict], ancho: float) -> Drawing:
    '''Gráfico vectorial de avance ponderado Sagarde, últimas 12 revisiones.'''
    datos = serie[-12:]
    alto = 34 * mm
    dibujo = Drawing(ancho, alto)
    x0, y0 = 27 * mm, 7 * mm
    plot_w, plot_h = ancho - 35 * mm, alto - 13 * mm

    for valor in (0, 25, 50, 75, 100):
        y = y0 + plot_h * valor / 100
        dibujo.add(Line(x0, y, x0 + plot_w, y, strokeColor=COL_LINE, strokeWidth=.45))
        dibujo.add(String(x0 - 3 * mm, y - 1.5, f'{valor}%', fontName='Helvetica',
                          fontSize=6.5, textAnchor='end', fillColor=COL_MUTED))

    if len(datos) == 1:
        puntos = [(x0 + plot_w / 2, y0 + plot_h * datos[0]['pct'] / 100)]
    else:
        puntos = [
            (x0 + i * plot_w / (len(datos) - 1), y0 + plot_h * dato['pct'] / 100)
            for i, dato in enumerate(datos)
        ]
    if len(puntos) >= 2:
        dibujo.add(PolyLine(puntos, strokeColor=COL_ACCENT, strokeWidth=2, fillColor=None))
    for x, y in puntos:
        dibujo.add(Circle(x, y, 2.1, fillColor=colors.white, strokeColor=COL_ACCENT, strokeWidth=1.2))

    indices = sorted({0, len(datos) // 2, len(datos) - 1})
    for i in indices:
        x, _ = puntos[i]
        dibujo.add(String(x, 2.3 * mm, str(datos[i]['fecha'])[:5], fontName='Helvetica',
                          fontSize=6.5, textAnchor='middle', fillColor=COL_MUTED))
    if datos:
        x, y = puntos[-1]
        etiqueta = '{:.1f}%'.format(datos[-1]['pct'])
        dibujo.add(String(min(x, x0 + plot_w - 2 * mm), min(y + 4, y0 + plot_h + 4),
                          etiqueta, fontName='Helvetica-Bold', fontSize=8,
                          textAnchor='end', fillColor=COL_ACCENT))
    return dibujo


def _grafico_distribucion(snapshot: list[dict], ancho: float) -> Drawing:
    '''Alternativa honesta cuando no hay suficientes revisiones para tendencia.'''
    alto = 25 * mm
    dibujo = Drawing(ancho, alto)
    total = max(1, len(snapshot))
    segmentos = [
        ('Terminado X', sum(r.get('status') == 'X' for r in snapshot), COL_ACCENT),
        ('En marcha M', sum(r.get('status') == 'M' for r in snapshot), colors.HexColor('#5B8DB8')),
        ('Iniciado /', sum(r.get('status') == '/' for r in snapshot), colors.HexColor('#E07B1A')),
        ('Pendiente', sum(r.get('status') == '' for r in snapshot), colors.HexColor('#D0D5DD')),
    ]
    x0, y0, barra_w, barra_h = 2 * mm, 13 * mm, ancho - 4 * mm, 7 * mm
    cursor = x0
    for etiqueta, n, color in segmentos:
        w = barra_w * n / total
        if w > 0:
            dibujo.add(Rect(cursor, y0, w, barra_h, fillColor=color, strokeColor=colors.white,
                            strokeWidth=.4))
            cursor += w
    leyenda_x = x0
    for etiqueta, n, color in segmentos:
        dibujo.add(Rect(leyenda_x, 3 * mm, 3 * mm, 3 * mm, fillColor=color, strokeColor=color))
        dibujo.add(String(leyenda_x + 4 * mm, 3.2 * mm, f'{etiqueta}: {n}',
                          fontName='Helvetica', fontSize=6.5, fillColor=COL_MUTED))
        leyenda_x += 43 * mm
    return dibujo


def _grafico_fases(fases: list[dict], ancho: float) -> Drawing:
    alto = max(22 * mm, 8 + len(fases) * 9)
    dibujo = Drawing(ancho, alto)
    etiqueta_w = 47 * mm
    x0 = etiqueta_w
    barra_w = ancho - etiqueta_w - 22 * mm
    y = alto - 8
    for fase in fases:
        pct = fase['pct']
        dibujo.add(String(x0 - 3 * mm, y - 1, str(fase['fase']), fontName='Helvetica',
                          fontSize=6.8, textAnchor='end', fillColor=COL_NAVY))
        dibujo.add(Rect(x0, y - 3, barra_w, 6, fillColor=colors.HexColor('#E8EDF3'),
                        strokeColor=None))
        dibujo.add(Rect(x0, y - 3, barra_w * pct / 100, 6, fillColor=COL_ACCENT,
                        strokeColor=None))
        etiqueta = '{:.0f}%  {}/{}'.format(pct, fase['x'], fase['total'])
        dibujo.add(String(x0 + barra_w + 3 * mm, y - 1, etiqueta,
                          fontName='Helvetica-Bold', fontSize=6.8,
                          fillColor=_color_pct(pct)))
        y -= 9
    return dibujo


def _cabecera_electrica(
    nombre_obra: str,
    sub_titulo: str,
    fecha_rev: str,
    ficha: dict | None,
    content_w: float,
) -> Table:
    logo = (Image(str(LOGO_PATH), width=48 * mm, height=14 * mm)
            if LOGO_PATH.is_file()
            else Paragraph('<b>SAGARDE</b>', _style('logo', 16, True, color=COL_BRAND)))
    titulo = [
        Paragraph('<b>INFORME EJECUTIVO ELÉCTRICO</b>',
                  _style('titulo_electrico', 14.5, True, color=COL_NAVY)),
        Paragraph('<b>OBRA:</b> {} &nbsp;|&nbsp; <b>ÁMBITO:</b> {}'.format(
            _texto(nombre_obra), _texto(sub_titulo or 'RESUMEN GENERAL')),
            _style('subtitulo_electrico', 8.6, color=COL_MUTED)),
        Paragraph('<b>Datos:</b> {} &nbsp;|&nbsp; Alcance: tajos propios de Sagarde'.format(
            _texto(fecha_rev)), _style('fuente_electrica', 7.4, color=COL_MUTED)),
    ]
    identidad = (ficha or {}).get('identidad') or {}
    cliente = _valor_ejecutivo(identidad.get('cliente'), 70)
    direccion = _valor_ejecutivo(identidad.get('direccion'), 85)
    if cliente or direccion:
        detalle = ' · '.join(x for x in [cliente, direccion] if x)
        titulo.append(Paragraph(_texto(detalle), _style('identidad_electrica', 6.8, color=COL_MUTED)))
    tabla = Table([[logo, titulo]], colWidths=[52 * mm, content_w - 52 * mm])
    tabla.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (0, 0), (-1, -1), .8, COL_LINE),
    ]))
    return tabla


def _tabla_kpis_electricos(
    snapshot: list[dict],
    frentes: list[dict],
    bloqueadores: list[dict],
    content_w: float,
) -> Table:
    kpis = motor_informes.kpis_snapshot(snapshot)
    objetivos_bloqueados = set()
    for bloqueo in bloqueadores:
        objetivos_bloqueados.update(bloqueo['tajos_sagarde'])
    tarjetas = [
        ('{:.1f}%'.format(kpis['pct_ponderado']), 'Avance eléctrico estimado',
         _color_pct(kpis['pct_ponderado']), True),
        ('{:.1f}%'.format(kpis['pct_estricto']), 'Terminado estricto (X)',
         _color_pct(kpis['pct_estricto']), True),
        (str(len(frentes)), 'Tajos Sagarde listos', COL_ACCENT, False),
        (str(len(objetivos_bloqueados)), 'Tajos condicionados',
         COL_WARN if objetivos_bloqueados else COL_OK, False),
        ('{} / {}'.format(kpis['x'], kpis['total']), 'Celdas terminadas', COL_NAVY, False),
    ]
    w = (content_w - 8 * mm) / len(tarjetas)
    celdas = []
    for valor, etiqueta, color, con_barra in tarjetas:
        contenido = [
            Paragraph('<font color={}><b>{}</b></font>'.format(color.hexval(), valor),
                      _style('kpi_valor_electrico', 14, True, align=TA_CENTER)),
        ]
        if con_barra:
            try:
                pct = float(valor.rstrip('%'))
            except ValueError:
                pct = 0
            contenido.extend([_make_mini_bar(pct, w_mm=25), Spacer(1, .7 * mm)])
        else:
            contenido.append(Spacer(1, 3.8 * mm))
        contenido.append(Paragraph(etiqueta, _style('kpi_etiqueta_electrico', 6.6,
                                                    align=TA_CENTER, color=COL_MUTED)))
        celdas.append(contenido)
    tabla = Table([celdas], colWidths=[w] * len(celdas))
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COL_LIGHT),
        ('BOX', (0, 0), (-1, -1), .7, COL_LINE),
        ('INNERGRID', (0, 0), (-1, -1), .35, COL_LINE),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return tabla


def _resumen_ejecutivo_electrico(
    snapshot: list[dict],
    serie: list[dict],
    frentes: list[dict],
    bloqueadores: list[dict],
) -> Table:
    kpis = motor_informes.kpis_snapshot(snapshot)
    if len(serie) >= 2:
        delta = serie[-1]['pct'] - serie[-2]['pct']
        evolucion = 'avance de {:+.1f} puntos frente a la revisión anterior'.format(delta)
    else:
        evolucion = 'sin comparación histórica suficiente'
    externos = [b for b in bloqueadores if b['propiedad'] in ('externo', 'coordinacion')]
    texto = (
        '<b>Situación eléctrica:</b> Sagarde alcanza un <b>{:.1f}%</b> de avance '
        'estimado y un <b>{:.1f}%</b> terminado; {}. '
        '<b>Producción:</b> {} tajos propios tienen frente disponible. '
        '<b>Condicionantes:</b> {} dependencias externas activas afectan a la '
        'producción Sagarde.'
    ).format(kpis['pct_ponderado'], kpis['pct_estricto'], evolucion,
             len(frentes), len(externos))
    tabla = Table([[Paragraph(texto, _style('resumen_ejecutivo', 8.2, leading=10.4,
                                             color=COL_NAVY))]],
                  colWidths=[PAGE_W - 2 * MARGIN_X])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COL_CARD),
        ('BOX', (0, 0), (-1, -1), .7, colors.HexColor('#B8C7DA')),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return tabla


def _tabla_tajos_atencion(tajos: list[dict], content_w: float) -> Table | Paragraph:
    pendientes = [t for t in tajos if t['pct'] < 99.9]
    pendientes.sort(key=lambda t: (t['orden'], t['pct'], _fold(t['nombre'])))
    if not pendientes:
        return Paragraph('<i>Todos los tajos propios medidos están terminados.</i>',
                         _style('tajos_completos', 7.5, color=COL_OK))
    filas = [[
        Paragraph('<b>Tajo Sagarde</b>', _style('th_tajo', 7, True, color=colors.white)),
        Paragraph('<b>Fase</b>', _style('th_fase', 7, True, color=colors.white)),
        Paragraph('<b>Avance</b>', _style('th_avance', 7, True, align=TA_CENTER, color=colors.white)),
        Paragraph('<b>Hecho</b>', _style('th_hecho', 7, True, align=TA_CENTER, color=colors.white)),
        Paragraph('<b>Pendiente</b>', _style('th_pendiente', 7, True, align=TA_CENTER, color=colors.white)),
    ]]
    for tajo in pendientes[:8]:
        filas.append([
            Paragraph('<b>{}</b>'.format(_texto(tajo['nombre'])), _style('td_tajo', 7)),
            Paragraph(_texto(tajo['fase']), _style('td_fase', 6.6, color=COL_MUTED)),
            Paragraph('<font color={}><b>{:.0f}%</b></font>'.format(
                _color_pct(tajo['pct']).hexval(), tajo['pct']),
                _style('td_avance', 7, align=TA_CENTER)),
            Paragraph('{}/{}'.format(tajo['x'], tajo['total']),
                      _style('td_hecho', 7, align=TA_CENTER)),
            Paragraph(str(tajo['pendiente']), _style('td_pendiente', 7, align=TA_CENTER)),
        ])
    tabla = Table(filas, colWidths=[57 * mm, 45 * mm, 25 * mm, 25 * mm, 27 * mm])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COL_NAVY),
        ('GRID', (0, 0), (-1, -1), .3, COL_LINE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COL_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.1),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return tabla


def _tabla_frentes(frentes: list[dict], ancho: float) -> Table | Paragraph:
    if not frentes:
        return Paragraph('<i>No hay frentes propios clasificados como listos.</i>',
                         _style('sin_frentes', 7, color=COL_MUTED))
    filas = [[
        Paragraph('<b>Próximo tajo Sagarde</b>', _style('fh1', 6.8, True, color=colors.white)),
        Paragraph('<b>Uds.</b>', _style('fh2', 6.8, True, align=TA_CENTER, color=colors.white)),
    ]]
    for frente in frentes[:5]:
        filas.append([
            Paragraph('<b>{}</b><br/><font color=#475467>{}</font>'.format(
                _texto(frente['trabajo']), _texto(frente['fase'])), _style('fd1', 6.7, leading=8.3)),
            Paragraph(str(frente['unidades']), _style('fd2', 7, True, align=TA_CENTER)),
        ])
    tabla = Table(filas, colWidths=[ancho - 16 * mm, 16 * mm])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COL_ACCENT),
        ('GRID', (0, 0), (-1, -1), .3, COL_LINE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COL_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return tabla


def _tabla_bloqueadores(bloqueadores: list[dict], ancho: float) -> Table | Paragraph:
    if not bloqueadores:
        return Paragraph('<i>No hay dependencias activas que frenen producción Sagarde.</i>',
                         _style('sin_bloqueos', 7, color=COL_OK))
    filas = [[
        Paragraph('<b>Condicionante</b>', _style('bh1', 6.8, True, color=colors.white)),
        Paragraph('<b>Afecta</b>', _style('bh2', 6.8, True, align=TA_CENTER, color=colors.white)),
    ]]
    for bloqueo in bloqueadores[:5]:
        tipo = ('OTRO GREMIO' if bloqueo['propiedad'] in ('externo', 'coordinacion')
                else 'CADENA SAGARDE' if bloqueo['propiedad'] == 'propio'
                else 'SIN CLASIFICAR')
        objetivos = ', '.join(sorted(str(x) for x in bloqueo['tajos_sagarde']))
        if len(objetivos) > 54:
            objetivos = objetivos[:53].rstrip() + '…'
        filas.append([
            Paragraph('<b>{}</b> · {}<br/><font color=#475467>{}</font>'.format(
                _texto(bloqueo['trabajo']), tipo, _texto(objetivos)),
                _style('bd1', 6.5, leading=8.1)),
            Paragraph(str(bloqueo['afecta_celdas']),
                      _style('bd2', 7, True, align=TA_CENTER, color=COL_WARN)),
        ])
    tabla = Table(filas, colWidths=[ancho - 17 * mm, 17 * mm])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COL_WARN),
        ('GRID', (0, 0), (-1, -1), .3, COL_LINE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFF8F6')]),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return tabla


def _tabla_operativa(frentes: list[dict], bloqueadores: list[dict], content_w: float) -> Table:
    mitad = (content_w - 4 * mm) / 2
    izquierda = [
        Paragraph('<b>PRÓXIMOS FRENTES DE PRODUCCIÓN</b>',
                  _style('sec_frentes', 8, True, color=COL_NAVY)),
        Spacer(1, 1 * mm),
        _tabla_frentes(frentes, mitad),
    ]
    derecha = [
        Paragraph('<b>CONDICIONANTES DE PRODUCCIÓN SAGARDE</b>',
                  _style('sec_bloqueos', 8, True, color=COL_WARN if bloqueadores else COL_NAVY)),
        Spacer(1, 1 * mm),
        _tabla_bloqueadores(bloqueadores, mitad),
    ]
    tabla = Table([[izquierda, derecha]], colWidths=[mitad, mitad])
    tabla.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 2 * mm),
        ('LEFTPADDING', (1, 0), (1, 0), 2 * mm),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
    ]))
    return tabla


def _pie_electrico(fecha_rev: str, content_w: float) -> Table:
    generado = datetime.now().strftime('%d/%m/%Y %H:%M')
    texto = ('Fuente: base viva de la obra + catálogo de tajos y dependencias · '
             'Datos {} · Generado {}').format(_texto(fecha_rev), generado)
    tabla = Table([[
        Paragraph(texto, _style('pie_fuente', 6.5, color=COL_MUTED)),
        Paragraph('<b>Montajes Eléctricos Sagarde, S.L.</b>',
                  _style('pie_marca', 7, True, align=TA_RIGHT, color=COL_NAVY)),
    ]], colWidths=[128 * mm, content_w - 128 * mm])
    tabla.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), .5, COL_LINE),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    return tabla


def _construir_bloque_electrico(
    story: list,
    nombre_obra: str,
    sub_titulo: str,
    fecha_rev: str,
    snapshot: list[dict],
    historial: list | None,
    ficha: dict | None,
    prioridades: dict | None,
    metadatos_por_id: dict,
    metadatos_por_nombre: dict,
    content_w: float,
    referencias: set[str] | None = None,
) -> None:
    propios = _filtrar_snapshot_sagarde(snapshot, metadatos_por_nombre, referencias)
    story.append(_cabecera_electrica(nombre_obra, sub_titulo, fecha_rev, ficha, content_w))
    story.append(Spacer(1, 2 * mm))

    if not propios:
        story.append(Paragraph(
            '<b>Sin datos eléctricos Sagarde para este ámbito.</b> La base no contiene '
            'registros medidos con <i>propiedad = propio</i>.',
            _style('sin_datos_propios', 9, color=COL_WARN, leading=12)))
        story.append(Spacer(1, 4 * mm))
        story.append(_pie_electrico(fecha_rev, content_w))
        return

    serie = _serie_avance_sagarde(historial, metadatos_por_nombre, referencias)
    fases = _resumen_fases_sagarde(propios, metadatos_por_nombre)
    tajos = _resumen_tajos_sagarde(propios, metadatos_por_nombre)
    frentes = _frentes_sagarde(prioridades, metadatos_por_id, referencias)
    bloqueadores = _bloqueadores_sagarde(prioridades, metadatos_por_id, referencias)

    story.append(Paragraph('<b>RESUMEN EJECUTIVO</b>',
                           _style('sec_resumen', 8.5, True, color=COL_NAVY)))
    story.append(Spacer(1, .8 * mm))
    story.append(_resumen_ejecutivo_electrico(propios, serie, frentes, bloqueadores))
    story.append(Spacer(1, 2 * mm))
    story.append(_tabla_kpis_electricos(propios, frentes, bloqueadores, content_w))
    story.append(Spacer(1, 2.2 * mm))

    if len(serie) >= 4:
        story.append(Paragraph('<b>EVOLUCIÓN DEL AVANCE ELÉCTRICO SAGARDE</b>',
                               _style('sec_tendencia', 8.5, True, color=COL_NAVY)))
        story.append(Paragraph(
            'Avance ponderado real de las últimas revisiones disponibles; cada punto '
            'usa únicamente tajos propios identificados en la base.',
            _style('nota_tendencia', 6.6, color=COL_MUTED)))
        story.append(_grafico_tendencia(serie, content_w))
    else:
        story.append(Paragraph('<b>ESTADO ACTUAL DEL ALCANCE SAGARDE</b>',
                               _style('sec_distribucion', 8.5, True, color=COL_NAVY)))
        story.append(Paragraph(
            'No hay suficientes revisiones comparables para una tendencia fiable; se '
            'muestra la composición del último estado medido.',
            _style('nota_distribucion', 6.6, color=COL_MUTED)))
        story.append(_grafico_distribucion(propios, content_w))
    story.append(Spacer(1, 1.5 * mm))

    story.append(Paragraph('<b>AVANCE POR FASE DE PRODUCCIÓN SAGARDE</b>',
                           _style('sec_fases', 8.5, True, color=COL_NAVY)))
    story.append(Paragraph(
        'Porcentaje ponderado y celdas terminadas sobre el total medido de cada fase.',
        _style('nota_fases', 6.6, color=COL_MUTED)))
    story.append(_grafico_fases(fases, content_w))
    story.append(Spacer(1, 1.5 * mm))

    story.append(Paragraph('<b>TAJOS SAGARDE QUE REQUIEREN ATENCIÓN</b>',
                           _style('sec_atencion', 8.5, True, color=COL_NAVY)))
    story.append(Paragraph(
        'Primeros tajos incompletos según el orden de ejecución definido en la base.',
        _style('nota_atencion', 6.6, color=COL_MUTED)))
    story.append(Spacer(1, .6 * mm))
    story.append(_tabla_tajos_atencion(tajos, content_w))
    story.append(Spacer(1, 2 * mm))
    story.append(_tabla_operativa(frentes, bloqueadores, content_w))
    story.append(Spacer(1, 2 * mm))
    story.append(_pie_electrico(fecha_rev, content_w))


# ─── Generación de cada bloque de 1 página A4 ─────────────────────────────
def _construir_bloque_ejecutivo(story: list, nombre_obra: str, sub_titulo: str, fecha_rev: str, snapshot: list[dict], content_w: float) -> None:
    kpis = motor_informes.kpis_snapshot(snapshot)
    bloqueos = motor_informes.detectar_bloqueos(snapshot)

    # 1. Cabecera Corporativa
    logo_cell = Image(str(LOGO_PATH), width=52 * mm, height=15 * mm) if LOGO_PATH.is_file() else Paragraph("<b>SAGARDE</b>", _style("l", 16, True, color=COL_BRAND))
    sub_txt = f" &nbsp;|&nbsp; <b>{sub_titulo}</b>" if sub_titulo else ""
    title_cell = [
        Paragraph(f"<b>INFORME EJECUTIVO DE AVANCE DE OBRA</b>", _style("t1", 14, True, color=COL_NAVY)),
        Paragraph(f"<b>OBRA:</b> {nombre_obra}{sub_txt} &nbsp;|&nbsp; <b>Fecha Revisión:</b> {fecha_rev}", _style("t2", 9.5, False, color=COL_MUTED)),
    ]
    hdr_tbl = Table([[logo_cell, title_cell]], colWidths=[56 * mm, content_w - 56 * mm])
    hdr_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 3 * mm))

    # 2. Bloque de KPIs Principales
    w_kpi = (content_w - 9 * mm) / 4
    pct_pond = kpis['pct_ponderado']
    pct_estr = kpis['pct_estricto']

    col_pond = COL_OK if pct_pond >= 70 else COL_BRAND if pct_pond < 40 else colors.HexColor('#E07B1A')
    col_estr = COL_OK if pct_estr >= 70 else COL_BRAND if pct_estr < 40 else colors.HexColor('#E07B1A')

    kpi_cells = [
        [
            Paragraph(f"<font color='{col_pond.hexval()}'><b>{pct_pond:.1f}%</b></font>", _style("kv", 16, True, align=TA_CENTER)),
            _make_mini_bar(pct_pond, w_mm=34),
            Spacer(1, 1 * mm),
            Paragraph("% Avance Ponderado", _style("kl", 7.5, False, align=TA_CENTER, color=COL_MUTED)),
        ],
        [
            Paragraph(f"<font color='{col_estr.hexval()}'><b>{pct_estr:.1f}%</b></font>", _style("kv", 16, True, align=TA_CENTER)),
            _make_mini_bar(pct_estr, w_mm=34),
            Spacer(1, 1 * mm),
            Paragraph("% Avance Estricto (X)", _style("kl", 7.5, False, align=TA_CENTER, color=COL_MUTED)),
        ],
        [
            Paragraph(f"<font color='{(COL_WARN if bloqueos else COL_OK).hexval()}'><b>{len(bloqueos)}</b></font>", _style("kv", 18, True, align=TA_CENTER)),
            Spacer(1, 3.5 * mm),
            Paragraph("Bloqueos Activos", _style("kl", 7.5, False, align=TA_CENTER, color=COL_MUTED)),
        ],
        [
            Paragraph(f"<font color='{COL_NAVY.hexval()}'><b>{kpis['x']} / {kpis['total']}</b></font>", _style("kv", 16, True, align=TA_CENTER)),
            Spacer(1, 3.5 * mm),
            Paragraph("Tajos Completados (X)", _style("kl", 7.5, False, align=TA_CENTER, color=COL_MUTED)),
        ],
    ]
    
    kpi_tbl = Table([kpi_cells], colWidths=[w_kpi]*4)
    kpi_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COL_LIGHT),
        ('BOX', (0,0), (-1,-1), 0.8, COL_LINE),
        ('INNERGRID', (0,0), (-1,-1), 0.5, COL_LINE),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 3 * mm))

    # 3. Estado de Avance de Partidas
    tit_desglose = f"DESGLOSE DE TAJOS ELÉCTRICOS Y TELECO — {sub_titulo.upper()}" if sub_titulo else "DESGLOSE COMPLETO DE TAJOS ELÉCTRICOS Y TELECO (TODOS LOS TAJOS DE CAMPO)"
    story.append(Paragraph(f"<b>{tit_desglose}</b>", _style("sec", 9, True, color=COL_NAVY)))
    story.append(Spacer(1, 1 * mm))

    por_tarea = motor_informes._agrupar(snapshot, 'task')
    tareas_summary = []
    for tarea, recs in por_tarea.items():
        if any(g in tarea.lower() for g in ['pladur', 'tabic', 'enchap', 'pint', 'recrecido', 'techos']):
            continue
        pct = motor_informes._pct_ponderado(recs)
        x_cnt = sum(1 for r in recs if r['status'] == 'X')
        m_cnt = sum(1 for r in recs if r['status'] in ('M', '/'))
        tot = len(recs)
        tareas_summary.append({
            'tarea': tarea,
            'pct': pct,
            'x': x_cnt,
            'marcha': m_cnt,
            'pendiente': tot - x_cnt - m_cnt,
            'total': tot
        })

    tareas_summary.sort(key=lambda t: (-t['pct'], -t['x'], t['tarea']))

    mitad = (len(tareas_summary) + 1) // 2
    col1 = tareas_summary[:mitad]
    col2 = tareas_summary[mitad:]

    def _crear_subtabla_tareas(lista_t):
        rows = [
            [
                Paragraph("<b>Tajo Eléctrico / Teleco</b>", _style("th", 7.5, True, color=colors.white)),
                Paragraph("<b>%</b>", _style("thc", 7.5, True, align=TA_CENTER, color=colors.white)),
                Paragraph("<b>Hecho (X)</b>", _style("thc", 7.5, True, align=TA_CENTER, color=colors.white)),
                Paragraph("<b>Falta</b>", _style("thc", 7.5, True, align=TA_CENTER, color=colors.white)),
            ]
        ]
        for t in lista_t:
            pct = t['pct']
            bar_col = "#2E9E5B" if pct >= 70 else "#E07B1A" if pct >= 40 else "#D9483C"
            if pct >= 99.9:
                st_txt = "<font color='#2E9E5B'><b>100%</b></font>"
            elif t['x'] > 0 or t['marcha'] > 0:
                st_txt = f"<font color='{bar_col}'><b>{pct:.0f}%</b></font>"
            else:
                st_txt = "<font color='#94A3B8'>0%</font>"

            rows.append([
                Paragraph(f"<b>{t['tarea']}</b>", _style("td", 7.5)),
                Paragraph(st_txt, _style("tdc", 7.5, align=TA_CENTER)),
                Paragraph(f"<b>{t['x']}</b> ud", _style("tdc", 7.5, align=TA_CENTER)),
                Paragraph(f"{t['pendiente']} ud", _style("tdc", 7.5, align=TA_CENTER)),
            ])
        sub_tbl = Table(rows, colWidths=[42 * mm, 14 * mm, 18 * mm, 16 * mm])
        sub_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), COL_NAVY),
            ('GRID', (0,0), (-1,-1), 0.3, COL_LINE),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COL_LIGHT]),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        return sub_tbl

    sub1 = _crear_subtabla_tareas(col1)
    sub2 = _crear_subtabla_tareas(col2)
    tbl_tareas_doble = Table([[sub1, sub2]], colWidths=[90 * mm, 90 * mm])
    tbl_tareas_doble.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(tbl_tareas_doble)
    story.append(Spacer(1, 3 * mm))

    # 4. Sección de Bloqueos Críticos
    story.append(Paragraph("<b>INTERFERENCIAS Y TAJOS FRENADOS POR OTROS GREMIOS</b>", _style("sec", 9.5, True, color=COL_WARN if bloqueos else COL_NAVY)))
    story.append(Spacer(1, 1 * mm))
    
    if bloqueos:
        rows_blq = [
            [
                Paragraph("<b>Planta / Ubicación</b>", _style("bh", 8, True, color=colors.white)),
                Paragraph("<b>Motivo / Gremio Frenante</b>", _style("bh", 8, True, color=colors.white)),
                Paragraph("<b>Diagnóstico de Avance</b>", _style("bh", 8, True, color=colors.white)),
            ]
        ]
        for b in bloqueos[:4]:
            ub = f"{b.get('edificio','')}" + (f" - Planta {b.get('planta')}" if b.get('planta') else "")
            rows_blq.append([
                Paragraph(f"<b>{ub}</b>", _style("bd", 7.5)),
                Paragraph(b.get('motivo', 'Retraso significativo respecto a la media de obra'), _style("bd", 7.5)),
                Paragraph(f"Avance actual: <b>{b.get('avance', 0):.0f}%</b> (Media edif: {b.get('referencia', 0):.0f}%)", _style("bd", 7.5)),
            ])
        tbl_blq = Table(rows_blq, colWidths=[38 * mm, 98 * mm, 50 * mm])
        tbl_blq.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), COL_WARN),
            ('GRID', (0,0), (-1,-1), 0.4, COL_LINE),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#FDFEFE')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(tbl_blq)
    else:
        story.append(Paragraph("<i>No se han detectado bloqueos ni interferencias críticas de gremios en este portal/obra.</i>", _style("nb", 8, False, color=COL_OK)))

    story.append(Spacer(1, 3 * mm))
    gen_time = datetime.now().strftime("%d/%m/%Y %H:%M")
    footer_text = f"Informe emitido automáticamente por el Motor Sagarde &middot; Datos del {fecha_rev} &middot; Generado {gen_time}"
    footer_tbl = Table([
        [Paragraph(footer_text, _style("foot", 7.5, color=COL_MUTED)), Paragraph("<b>Montajes Eléctricos Sagarde, S.L.</b>", _style("footr", 8, True, align=TA_RIGHT, color=COL_NAVY))]
    ], colWidths=[120 * mm, content_w - 120 * mm])
    footer_tbl.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 0.5, COL_LINE),
        ('TOPPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(footer_tbl)


def _cargar_meta_obras() -> dict:
    js_path = MOTOR_IA_DIR / "obras_revisiones.js"
    if not js_path.is_file():
        return {}
    try:
        data = js_path.read_text(encoding="utf-8")
        m = re.search(r'SAGARDE_OBRAS_REVISION\s*=\s*(.*);', data)
        if not m:
            return {}
        obras = json.loads(m.group(1))
        return {o["nombre"]: o for o in obras}
    except Exception:
        return {}


# ─── Generación del PDF ───────────────────────────────────────────────────
def generar_pdf_ejecutivo(
    nombre_obra: str,
    fecha_rev: str,
    snapshot: list[dict],
    output_pdf: Path,
    historial: list | None = None,
    ficha: dict | None = None,
    prioridades: dict | None = None,
) -> Path:
    _registrar_fuentes()
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_Y,
        bottomMargin=MARGIN_Y,
    )

    story = []
    content_w = PAGE_W - 2 * MARGIN_X
    metadatos_por_id, metadatos_por_nombre = _indice_metadatos_tajos(ficha)

    meta_obras = _cargar_meta_obras()
    meta = meta_obras.get(nombre_obra)

    portal_items = []
    if meta and meta.get("bloques"):
        for b in meta["bloques"]:
            b_nom = b.get("nombre", "")
            for p in b.get("portales", []):
                p_nom = p.get("nombre", "")
                p_ref = p.get("referencia_portal", p_nom)
                if p_nom.lower() == "portal único" or p_nom.lower() == "portal unico":
                    lbl = f"BLOQUE: {b_nom}" if b_nom else "PORTAL ÚNICO"
                elif b_nom and b_nom.lower() not in p_nom.lower() and p_nom.lower() not in b_nom.lower():
                    lbl = f"BLOQUE: {b_nom} — PORTAL: {p_nom}"
                else:
                    lbl = f"PORTAL: {p_nom}"
                portal_items.append((p_ref, lbl, p_nom))
    
    if not portal_items:
        raw_buildings = sorted(set(r.get('building') for r in snapshot if r.get('building')))
        for b in raw_buildings:
            portal_items.append((b, f"SUBDIVISIÓN: {b}", b))

    # 1. Página General de la Obra
    sub_tit_gen = f"RESUMEN GENERAL ({len(portal_items)} PORTALES/BLOQUES)" if len(portal_items) >= 2 else "RESUMEN GENERAL"
    _construir_bloque_electrico(
        story, nombre_obra, sub_tit_gen, fecha_rev, snapshot, historial,
        ficha, prioridades, metadatos_por_id, metadatos_por_nombre, content_w,
    )

    # 2. Páginas Desglosadas por Bloque / Portal (si hay 2 o más subdivisiones)
    if len(portal_items) >= 2:
        for ref, lbl, p_nom in portal_items:
            snap_portal = [r for r in snapshot if r.get('building') == ref or r.get('building') == p_nom]
            if snap_portal:
                story.append(PageBreak())
                _construir_bloque_electrico(
                    story, nombre_obra, lbl, fecha_rev, snap_portal, historial,
                    ficha, prioridades, metadatos_por_id, metadatos_por_nombre,
                    content_w, referencias={ref, p_nom},
                )

    doc.build(story)
    return output_pdf


# ─── Entry Point ──────────────────────────────────────────────────────────
def generar_para_obra(
    nombre_obra: str,
    historial: list | None = None,
    ficha: dict | None = None,
    prioridades: dict | None = None,
) -> Path | None:
    obra = resolver_obra(nombre_obra)
    if obra is None:
        print(f"[ERROR] No hay obra registrada con el nombre '{nombre_obra}'.")
        return None
    nombre_oficial = obra['nombre']
    carpeta_obra = OBRAS_DIR / obra['carpeta_obra']

    # El modo directo también respeta la base viva. Conserva el historial
    # para la gráfica y sustituye el último snapshot por la ficha consolidada.
    if ficha is None and historial is None:
        ficha = fichas.cargar(str(carpeta_obra))

    if historial is None:
        adaptador = ADAPTADORES[nombre_oficial]
        print(f"[1/2] Cargando historial de revisiones para '{nombre_oficial}'...")
        historial = adaptador.cargar_historial()
        if ficha:
            snapshot_base = fichas.snapshot_desde_ficha(ficha)
            if snapshot_base:
                if historial:
                    fecha_base = historial[-1][0]
                    historial[-1] = (fecha_base, snapshot_base)
                else:
                    revisiones = ficha.get('revisiones') or []
                    fecha_base = revisiones[-1].get('fecha') if revisiones else ''
                    historial = [(fecha_base, snapshot_base)] if fecha_base else []
    else:
        print(f"[1/2] Usando el historial validado por la ficha para '{nombre_oficial}'...")

    if ficha and prioridades is None:
        prioridades = priorizador_trabajos.priorizar_ficha(
            ficha, obra=nombre_oficial)

    if not historial:
        print(f"[ERROR] No se encontraron revisiones para '{nombre_oficial}'.")
        return None

    fecha_rev, snapshot = historial[-1]
    print(f"      Ultima revision: {fecha_rev} ({len(snapshot)} registros)")

    # Ruta de salida PDF
    carpeta_obra = OBRAS_DIR / obra['carpeta_obra'] / "INFORME SAGARDE IA"
    carpeta_obra.mkdir(parents=True, exist_ok=True)
    output_pdf = carpeta_obra / (
        f"INFORME_EJECUTIVO_{nombre_oficial.replace(' ', '_')}.pdf")

    print(f"[2/2] Generando PDF Ejecutivo A4 en: {output_pdf}...")
    generar_pdf_ejecutivo(
        nombre_oficial,
        fecha_rev,
        snapshot,
        output_pdf,
        historial=historial,
        ficha=ficha,
        prioridades=prioridades,
    )
    print(f"[OK] Informe ejecutivo creado con exito: {output_pdf}")
    return output_pdf


def main():
    parser = argparse.ArgumentParser(description="Generador de Informe Ejecutivo en PDF para Sagarde")
    parser.add_argument("--obra", type=str, default="2026 BOLUETA ACR", help="Nombre de la obra (ej. '2026 BOLUETA ACR')")
    args = parser.parse_args()
    generar_para_obra(args.obra)


if __name__ == "__main__":
    main()
