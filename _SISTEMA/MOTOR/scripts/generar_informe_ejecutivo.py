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
from reportlab.lib.utils import ImageReader
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
FUENTE_ITALIC = 'IBMPlexSans-Italic'
FUENTE_BOLD_ITALIC = 'IBMPlexSans-BoldItalic'
CATALOGO_PATH = MOTOR_IA_DIR / "reglas" / "CATALOGO_TAJOS.json"


def _registrar_fuentes() -> None:
    '''Registra IBM Plex Sans para el informe.

    Las cuatro variantes, no dos: el informe usa <i> en los mensajes de "no
    hay nada que enseñar" (tajos todos terminados, sin frentes, sin
    dependencias) y en un enfasis del pie. Mapear la cursiva a la redonda las
    habria borrado sin que saltara nada.

    Falla a gritos si falta la tipografia. Volver a Helvetica en silencio
    produciria un informe con el aspecto de siempre y nadie se enteraria: es
    exactamente el fallo que este trabajo viene a quitar.
    '''
    if FUENTE in pdfmetrics.getRegisteredFontNames():
        return
    ficheros = {
        FUENTE: FONTS_DIR / 'IBMPlexSans-Regular.ttf',
        FUENTE_BOLD: FONTS_DIR / 'IBMPlexSans-Bold.ttf',
        FUENTE_ITALIC: FONTS_DIR / 'IBMPlexSans-Italic.ttf',
        FUENTE_BOLD_ITALIC: FONTS_DIR / 'IBMPlexSans-BoldItalic.ttf',
    }
    faltan = [str(ruta) for ruta in ficheros.values() if not ruta.is_file()]
    if faltan:
        raise RuntimeError(
            'Falta la tipografia del informe ejecutivo: ' + ', '.join(faltan) +
            '. Se descarga segun la Tarea 1 de _SISTEMA/docs/superpowers/'
            'plans/2026-08-13-informe-ejecutivo-caracter.md')
    for nombre, ruta in ficheros.items():
        pdfmetrics.registerFont(TTFont(nombre, str(ruta)))
    # Sin esta linea los <b> y los <i> del informe dejan de tener efecto SIN
    # dar error: el PDF sale plano y no se queja nadie.
    pdfmetrics.registerFontFamily(
        FUENTE, normal=FUENTE, bold=FUENTE_BOLD,
        italic=FUENTE_ITALIC, boldItalic=FUENTE_BOLD_ITALIC)

if str(MOTOR_IA_DIR) not in sys.path:
    sys.path.append(str(MOTOR_IA_DIR))

import motor_informes
import ficha_obra as fichas
import priorizador_trabajos
import cierre_expediente
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
    # Algunas fichas anaden las coordenadas tras la direccion; en la cabecera
    # solo estorban y hacian que el texto se cortara con puntos suspensivos.
    texto = re.split(r'[.;]?\s*Coordenadas\b', texto, maxsplit=1,
                     flags=re.IGNORECASE)[0].strip().rstrip('.;,')
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


def _nombres_ubicacion_por_id(ficha: dict | None) -> dict:
    """id de ubicacion (estructura de ficha_obra.json) -> nombre real.

    Cubre cualquier planta, no solo zesp: los ids que genera el alta de obra
    son unicos en toda la ficha, asi que no hace falta filtrar por planta
    para resolverlos sin ambiguedad.
    """
    salida = {}
    for bloque in (ficha or {}).get('estructura', {}).get('bloques') or []:
        for portal in bloque.get('portales') or []:
            for planta in portal.get('plantas') or []:
                for ubi in planta.get('ubicaciones') or []:
                    salida[ubi['id']] = ubi.get('nombre') or ubi['id']
    return salida


def _zonas_con_nombre(
    prioridades: dict | None,
    ficha: dict | None,
    resolver_nombre: bool,
    referencias: set[str] | None = None,
) -> list[dict]:
    """Agrupa 'detalle_items' propios por zona/ubicacion con nombre real.

    Usa 'detalle_items' (no el snapshot ya filtrado) porque necesita el
    TOTAL de celdas aplicables de cada zona, incluidas las no medidas
    todavia -- si no, una zona recien dada de alta y sin ninguna celda
    medida no aparaceria con 0%, sencillamente no aparaceria.

    En Garaje, 'unidad' ya es el nombre legible (viene de
    priorizador_trabajos via ficha_garajes, ver generar_todos.py). En Zonas
    Especiales 'unidad' es el id interno de la ubicacion (ver
    ficha_obra.snapshot_desde_ficha) y hay que resolverlo contra la
    estructura de `ficha` -- de ahi el flag `resolver_nombre`.
    """
    nombres_por_id = _nombres_ubicacion_por_id(ficha) if resolver_nombre else {}
    grupos: dict[str, dict] = {}
    for fila in (prioridades or {}).get('detalle_items') or []:
        if fila.get('propiedad') != 'propio':
            continue
        if not _fila_en_alcance(fila, referencias):
            continue
        clave = fila.get('unidad')
        if not clave:
            continue
        nombre = nombres_por_id.get(clave, clave) if resolver_nombre else clave
        grupo = grupos.setdefault(clave, {'nombre': nombre, 'recs': []})
        grupo['recs'].append({'status': fila.get('estado') or ''})

    salida = []
    for grupo in grupos.values():
        recs = grupo['recs']
        salida.append({
            'nombre': grupo['nombre'],
            'pct': motor_informes._pct_ponderado(recs),
            'x': sum(1 for r in recs if r['status'] == 'X'),
            'total': len(recs),
        })
    salida.sort(key=lambda z: (z['pct'], _fold(z['nombre'])))
    return salida


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
COL_GRIS   = colors.HexColor('#98A2B3')


def _style(name: str, size: float, bold: bool = False, align: int = TA_LEFT, color: colors.Color = colors.black, leading: float | None = None) -> ParagraphStyle:
    lead = leading if leading is not None else size * 1.25
    return ParagraphStyle(
        name, fontSize=size, leading=lead,
        fontName=FUENTE_BOLD if bold else FUENTE,
        alignment=align, textColor=color
    )


def _logo_flowable(ancho_mm: float) -> Image:
    '''El logo a un ancho dado, con su proporcion real.

    La altura se calcula, no se escribe: estaba a 48x14 mm en una cabecera y a
    52x15 en la otra, sobre un nativo de 2732x751, asi que salia aplastado y
    ademas distinto en cada pagina. Leyendo el tamaño real, el arreglo
    sobrevive a que algun dia se cambie el logo.

    Si falta el fichero se lanza un error. Antes caia a la palabra "SAGARDE"
    escrita en texto y el informe salia sin logo sin que nadie se enterase.
    '''
    if not LOGO_PATH.is_file():
        raise RuntimeError(
            'Falta el logo del informe ejecutivo: ' + str(LOGO_PATH))
    ancho_px, alto_px = ImageReader(str(LOGO_PATH)).getSize()
    ancho = ancho_mm * mm
    return Image(str(LOGO_PATH), width=ancho, height=ancho * alto_px / ancho_px)


def _make_mini_bar(pct: float, w_mm: float = 34) -> Table:
    fill_w = max(1, min(w_mm, (pct / 100.0) * w_mm))
    rem_w = max(0, w_mm - fill_w)
    col = _color_estado(pct)
    t = Table([['', '']], colWidths=[fill_w * mm, rem_w * mm], rowHeights=[3.5 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), col),
        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#E2E8F0')),
        ('BOX', (0,0), (-1,-1), 0.4, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    return t


# Escala de avance en CUATRO tramos: del azul corporativo a un verde oscuro,
# pasando por dos tonos intermedios apagados. Sobria a proposito (nada de
# semaforo ni de arcoiris en un informe): el verde queda reservado para lo
# terminado y se reconoce de un vistazo que fases o porcentajes van mas
# avanzados. Ningun tono lleva rojo; el rojo sigue siendo solo para la tabla de
# condicionantes.
COL_TRAMO_1 = colors.HexColor('#123A63')   # menos de 50 %: azul corporativo
COL_TRAMO_2 = colors.HexColor('#164F5C')   # 50 a 79 %
COL_TRAMO_3 = colors.HexColor('#1B6554')   # 80 a 99 %
COL_TRAMO_4 = colors.HexColor('#1F7A4D')   # 100 %: verde oscuro
TRAMOS_AVANCE = (
    (50.0, COL_TRAMO_1, 'menos de 50 %'),
    (80.0, COL_TRAMO_2, '50 a 79 %'),
    (99.95, COL_TRAMO_3, '80 a 99 %'),
    (None, COL_TRAMO_4, '100 %'),
)


def _color_estado(pct: float):
    '''Color del porcentaje: escala de cuatro tramos (ver TRAMOS_AVANCE).

    El color describe el estado; no lo juzga. Un tajo al 0 % que es del final
    de obra no va mal, es que aun no toca, y pintarlo de rojo afirmaba algo
    falso sobre la obra: por eso la escala va de azul a verde y sin rojo.

    Esta funcion es la UNICA regla de color por porcentaje del informe. Habia
    una copia a mano dentro de _make_mini_bar, y cambiar solo una de las dos
    dejaba media pagina con el criterio viejo. El 100 % se decide con el
    mismo redondeo a un decimal con que se imprime (99.95 o mas se ve 100.0 %).
    '''
    try:
        valor = float(pct)
    except (TypeError, ValueError):
        return COL_TRAMO_1
    for limite, color, _etiqueta in TRAMOS_AVANCE:
        if limite is None or valor < limite:
            return color
    return COL_TRAMO_4


def _leyenda_tramos(ancho: float, escala: float = 1.0) -> Drawing:
    '''Leyenda de la escala de color, en una linea bajo el titulo de fases.'''
    tam = _fuente_escalada(8.4, escala, 8)
    alto = max(4.2 * mm, 4.4 * mm * escala)
    dibujo = Drawing(ancho, alto)
    base = (alto - tam * .72) / 2
    x = 0.0
    rotulo = 'Color según avance:'
    dibujo.add(String(x, base, rotulo, fontName=FUENTE, fontSize=tam,
                      fillColor=COL_MUTED))
    x += pdfmetrics.stringWidth(rotulo, FUENTE, tam) + 2.2 * mm
    lado = 3 * mm
    for _limite, color, etiqueta in TRAMOS_AVANCE:
        dibujo.add(Rect(x, (alto - lado) / 2, lado, lado, fillColor=color,
                        strokeColor=None))
        x += lado + 1.2 * mm
        dibujo.add(String(x, base, etiqueta, fontName=FUENTE, fontSize=tam,
                          fillColor=COL_MUTED))
        x += pdfmetrics.stringWidth(etiqueta, FUENTE, tam) + 3.2 * mm
    return dibujo


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
        dibujo.add(String(x0 - 3 * mm, y - 1.5, f'{valor}%', fontName=FUENTE,
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
        dibujo.add(String(x, 2.3 * mm, str(datos[i]['fecha'])[:5], fontName=FUENTE,
                          fontSize=6.5, textAnchor='middle', fillColor=COL_MUTED))
    if datos:
        x, y = puntos[-1]
        etiqueta = '{:.1f}%'.format(datos[-1]['pct'])
        dibujo.add(String(min(x, x0 + plot_w - 2 * mm), min(y + 4, y0 + plot_h + 4),
                          etiqueta, fontName=FUENTE_BOLD, fontSize=8,
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
                          fontName=FUENTE, fontSize=6.5, fillColor=COL_MUTED))
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
        dibujo.add(String(x0 - 3 * mm, y - 1, str(fase['fase']), fontName=FUENTE,
                          fontSize=6.8, textAnchor='end', fillColor=COL_NAVY))
        dibujo.add(Rect(x0, y - 3, barra_w, 6, fillColor=colors.HexColor('#E8EDF3'),
                        strokeColor=None))
        dibujo.add(Rect(x0, y - 3, barra_w * pct / 100, 6, fillColor=COL_ACCENT,
                        strokeColor=None))
        etiqueta = '{:.0f}%  {}/{}'.format(pct, fase['x'], fase['total'])
        dibujo.add(String(x0 + barra_w + 3 * mm, y - 1, etiqueta,
                          fontName=FUENTE_BOLD, fontSize=6.8,
                          fillColor=_color_estado(pct)))
        y -= 9
    return dibujo


def _cabecera_electrica(
    nombre_obra: str,
    sub_titulo: str,
    fecha_rev: str,
    ficha: dict | None,
    content_w: float,
) -> Table:
    logo = _logo_flowable(48)
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
         _color_estado(kpis['pct_ponderado']), True),
        ('{:.1f}%'.format(kpis['pct_estricto']), 'Terminado estricto (X)',
         _color_estado(kpis['pct_estricto']), True),
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


def _texto_resumen_ejecutivo(kpis: dict, serie: list[dict],
                             frentes: list[dict], bloqueadores: list[dict],
                             solo_viviendas: bool = False) -> str:
    """Frase de situacion de la hoja: es la esencia narrativa del informe.

    Con garaje sumado en los indicadores, la serie historica sigue siendo solo
    de vivienda (no hay forma honesta de fusionar las dos series), asi que la
    frase lo dice en lugar de atribuir a toda la obra el avance de las viviendas.
    """
    if len(serie) >= 2:
        delta = serie[-1]['pct'] - serie[-2]['pct']
        if solo_viviendas:
            evolucion = ('las viviendas avanzan {:+.1f} puntos frente a la '
                         'revisión anterior').format(delta)
        else:
            evolucion = ('avance de {:+.1f} puntos frente a la revisión '
                         'anterior').format(delta)
    else:
        evolucion = 'sin comparación histórica suficiente'
    externos = [b for b in bloqueadores
                if b['propiedad'] in ('externo', 'coordinacion')]
    return (
        '<b>Situación eléctrica:</b> Sagarde alcanza un <b>{:.1f}%</b> de avance '
        'estimado y un <b>{:.1f}%</b> terminado; {}. '
        '<b>Producción:</b> {} tajos propios tienen frente disponible. '
        '<b>Condicionantes:</b> {} dependencias externas activas afectan a la '
        'producción Sagarde.'
    ).format(kpis['pct_ponderado'], kpis['pct_estricto'], evolucion,
             len(frentes), len(externos))


def _resumen_ejecutivo_pagina(datos: dict, content_w: float, escala: float,
                              solo_viviendas: bool = False) -> Table:
    """Resumen ejecutivo de la hoja densa: misma frase, letra >= 8,5 pt y
    a lo ancho del contenido (la hoja se ajusta a la pagina con `escala`)."""
    texto = _texto_resumen_ejecutivo(
        datos['kpis'], datos['serie'], datos['frentes'], datos['bloqueadores'],
        solo_viviendas=solo_viviendas)
    tabla = Table(
        [[Paragraph(texto, _estilo_maqueta(
            'resumen_ejecutivo_pagina', 8.9, escala, minimo=8.5,
            color=COL_NAVY, factor_leading=1.22))]],
        colWidths=[content_w])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COL_CARD),
        ('BOX', (0, 0), (-1, -1), .7, colors.HexColor('#B8C7DA')),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return tabla


def _resumen_ejecutivo_electrico(
    snapshot: list[dict],
    serie: list[dict],
    frentes: list[dict],
    bloqueadores: list[dict],
) -> Table:
    kpis = motor_informes.kpis_snapshot(snapshot)
    texto = _texto_resumen_ejecutivo(kpis, serie, frentes, bloqueadores)
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
                _color_estado(tajo['pct']).hexval(), tajo['pct']),
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


def _tabla_detalle_zona(zonas: list[dict], content_w: float) -> Table | Paragraph:
    """Detalle por zona/ubicacion con nombre propio (Garaje, Zonas Especiales).

    Sin truncar (a diferencia de `_tabla_tajos_atencion`, que solo muestra
    las primeras 8): el volumen aqui es pequeno -- unas pocas decenas de
    zonas como mucho -- y omitir una escondería justo la que alguien
    buscaba."""
    if not zonas:
        return Paragraph('<i>Sin zonas con nombre propio en este ambito.</i>',
                         _style('sin_zonas', 7.5, color=COL_MUTED))
    filas = [[
        Paragraph('<b>Zona</b>', _style('zh_nombre', 7, True, color=colors.white)),
        Paragraph('<b>Avance</b>', _style('zh_avance', 7, True, align=TA_CENTER, color=colors.white)),
        Paragraph('<b>Hecho</b>', _style('zh_hecho', 7, True, align=TA_CENTER, color=colors.white)),
        Paragraph('<b>Pendiente</b>', _style('zh_pendiente', 7, True, align=TA_CENTER, color=colors.white)),
    ]]
    for zona in zonas:
        pct = zona['pct']
        filas.append([
            Paragraph('<b>{}</b>'.format(_texto(zona['nombre'])), _style('zd_nombre', 7)),
            Paragraph('<font color={}><b>{:.0f}%</b></font>'.format(
                _color_estado(pct).hexval(), pct),
                _style('zd_avance', 7, align=TA_CENTER)),
            Paragraph('{}/{}'.format(zona['x'], zona['total']),
                      _style('zd_hecho', 7, align=TA_CENTER)),
            Paragraph(str(zona['total'] - zona['x']), _style('zd_pendiente', 7, align=TA_CENTER)),
        ])
    tabla = Table(filas, colWidths=[content_w - 3 * 25 * mm, 25 * mm, 25 * mm, 25 * mm])
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


COLOR_ESTADO_HITO = {
    'hecho': COL_OK, 'favorable': COL_OK,
    'condicionada': COL_WARN, 'negativa': COL_WARN,
    'no_aplica': COL_GRIS, 'pendiente': COL_GRIS,
}


def _tabla_cierre_expediente(cierre: dict | None, avisos: list[str] | None,
                              content_w: float):
    _registrar_fuentes()
    cierre = cierre or {}
    hitos = cierre.get('hitos') or {}
    avisos = avisos or []
    if not hitos:
        return Paragraph(
            'Sin datos de cierre de expediente todavía.',
            _style('cierre_vacio', 8, color=COL_MUTED))

    filas = [[
        Paragraph('<b>HITO</b>', _style('cierre_h', 7.5, True, color=colors.white)),
        Paragraph('<b>ESTADO</b>', _style('cierre_h', 7.5, True, color=colors.white)),
        Paragraph('<b>FECHA</b>', _style('cierre_h', 7.5, True, color=colors.white)),
        Paragraph('<b>NOTA</b>', _style('cierre_h', 7.5, True, color=colors.white)),
    ]]
    for hito_id in cierre_expediente.HITOS_ORDEN:
        datos_hito = hitos.get(hito_id) or {'estado': 'pendiente', 'fecha': None, 'nota': ''}
        estado = datos_hito.get('estado') or 'pendiente'
        color_estado = COLOR_ESTADO_HITO.get(estado, COL_GRIS)
        nombre = cierre_expediente.HITOS_NOMBRE.get(hito_id, hito_id)
        filas.append([
            Paragraph(_texto(nombre), _style('cierre_c', 7.5)),
            Paragraph(f'<b>{_texto(estado).upper()}</b>',
                      _style('cierre_c_estado', 7.5, True, color=color_estado)),
            Paragraph(_texto(datos_hito.get('fecha') or '—'), _style('cierre_c', 7.5)),
            Paragraph(_texto(datos_hito.get('nota') or '—'), _style('cierre_c', 7.5)),
        ])
    tabla = Table(
        filas,
        colWidths=[content_w * 0.28, content_w * 0.18, content_w * 0.16, content_w * 0.38])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COL_NAVY),
        ('LINEBELOW', (0, 0), (-1, -1), .4, COL_LINE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    if not avisos:
        return tabla
    bloques = [tabla, Spacer(1, 2 * mm)]
    for aviso in avisos:
        bloques.append(Paragraph(f'⚠ {_texto(aviso)}', _style('cierre_aviso', 7, color=COL_WARN)))
    return KeepTogether(bloques)


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

    # Detalle por zona: solo Garaje y Zonas Especiales tienen un numero
    # pequeno de ubicaciones con nombre propio (unas pocas decenas como
    # mucho). En vivienda hay demasiadas unidades por portal para que quepa
    # una fila por cada una -- ahi se sigue viendo solo el agregado por
    # fase/tajo de mas arriba.
    if sub_titulo in ('GARAJE', 'ZONAS ESPECIALES'):
        zonas = _zonas_con_nombre(
            prioridades, ficha, resolver_nombre=(sub_titulo == 'ZONAS ESPECIALES'),
            referencias=referencias,
        )
        story.append(Paragraph('<b>DETALLE POR ZONA</b>',
                               _style('sec_zonas', 8.5, True, color=COL_NAVY)))
        story.append(Paragraph(
            'Avance ponderado y celdas de cada zona con nombre propio de esta obra.',
            _style('nota_zonas', 6.6, color=COL_MUTED)))
        story.append(Spacer(1, .6 * mm))
        story.append(_tabla_detalle_zona(zonas, content_w))
        story.append(Spacer(1, 2 * mm))

    story.append(KeepTogether([
        _tabla_operativa(frentes, bloqueadores, content_w),
        Spacer(1, 2 * mm),
        _pie_electrico(fecha_rev, content_w),
    ]))


# ─── Generación de cada bloque de 1 página A4 ─────────────────────────────
def _construir_bloque_ejecutivo(story: list, nombre_obra: str, sub_titulo: str, fecha_rev: str, snapshot: list[dict], content_w: float) -> None:
    kpis = motor_informes.kpis_snapshot(snapshot)
    bloqueos = motor_informes.detectar_bloqueos(snapshot)

    # 1. Cabecera Corporativa
    logo_cell = _logo_flowable(52)
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


# ---------------------------------------------------------------------------
# Maquetacion compacta, medible y ajustada pagina a pagina
# ---------------------------------------------------------------------------

def _fuente_escalada(base: float, escala: float, minimo: float,
                     maximo: float | None = None) -> float:
    valor = max(minimo, base * escala)
    if maximo is not None:
        valor = min(maximo, valor)
    return round(valor, 2)


def _estilo_maqueta(nombre: str, base: float, escala: float,
                    minimo: float = 8.5, bold: bool = False,
                    align: int = TA_LEFT, color=colors.black,
                    factor_leading: float = 1.16) -> ParagraphStyle:
    size = _fuente_escalada(base, escala, minimo)
    return _style(
        nombre, size, bold=bold, align=align, color=color,
        leading=size * factor_leading)


def _seccion(texto: str, escala: float, color=COL_NAVY) -> Paragraph:
    return Paragraph(
        '<b>{}</b>'.format(_texto(texto.upper())),
        _estilo_maqueta('seccion_' + _fold(texto).replace(' ', '_'),
                        10.5, escala, minimo=10, bold=True, color=color))


def _nota(texto: str, escala: float) -> Paragraph:
    return Paragraph(
        _texto(texto),
        _estilo_maqueta('nota_' + str(abs(hash(texto))), 8.4, escala,
                        minimo=8, color=COL_MUTED, factor_leading=1.18))


def _cabecera_electrica(
    nombre_obra: str,
    sub_titulo: str,
    fecha_rev: str,
    ficha: dict | None,
    content_w: float,
    escala: float = 1.0,
) -> Table:
    """Cabecera corporativa unica para todas las hojas del informe."""
    logo = _logo_flowable(43)
    titulo = [
        Paragraph(
            '<b>INFORME EJECUTIVO EL\u00c9CTRICO</b>',
            _estilo_maqueta('titulo_electrico_ajustado', 14.2, escala,
                            minimo=12.5, bold=True, color=COL_NAVY)),
        Paragraph(
            '<b>OBRA:</b> {} &nbsp;|&nbsp; <b>\u00c1MBITO:</b> {}'.format(
                _texto(nombre_obra), _texto(sub_titulo or 'RESUMEN GENERAL')),
            _estilo_maqueta('subtitulo_electrico_ajustado', 9.1, escala,
                            minimo=8.5, color=COL_MUTED)),
        Paragraph(
            '<b>Datos:</b> {} &nbsp;|&nbsp; Alcance: tajos propios de Sagarde'.format(
                _texto(fecha_rev)),
            _estilo_maqueta('fuente_electrica_ajustada', 8.7, escala,
                            minimo=8.5, color=COL_MUTED)),
    ]
    identidad = (ficha or {}).get('identidad') or {}
    cliente = _valor_ejecutivo(identidad.get('cliente'), 70)
    direccion = _valor_ejecutivo(identidad.get('direccion'), 85)
    if cliente or direccion:
        titulo.append(Paragraph(
            _texto(' \u00b7 '.join(x for x in (cliente, direccion) if x)),
            _estilo_maqueta('identidad_electrica_ajustada', 8.5, escala,
                            minimo=8.5, color=COL_MUTED)))
    tabla = Table([[logo, titulo]], colWidths=[47 * mm, content_w - 47 * mm])
    tabla.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5 * mm),
        ('LINEBELOW', (0, 0), (-1, -1), .8, COL_LINE),
    ]))
    return tabla


def _conteo_cierre(cierre: dict | None) -> tuple[int, int]:
    hitos = (cierre or {}).get('hitos') or {}
    if not hitos:
        return 0, 0
    hechos = sum(
        1 for hito_id in cierre_expediente.HITOS_ORDEN
        if (hitos.get(hito_id) or {}).get('estado') in ('hecho', 'favorable'))
    return hechos, len(cierre_expediente.HITOS_ORDEN)


def _tabla_kpis_electricos(
    snapshot: list[dict],
    frentes: list[dict],
    bloqueadores: list[dict],
    content_w: float,
    cierre: dict | None = None,
    incluir_cierre: bool = False,
    escala: float = 1.0,
) -> Table:
    kpis = motor_informes.kpis_snapshot(snapshot)
    objetivos_bloqueados = set()
    for bloqueo in bloqueadores:
        objetivos_bloqueados.update(bloqueo['tajos_sagarde'])
    tarjetas = [
        ('{:.1f}%'.format(kpis['pct_ponderado']), 'Avance estimado',
         _color_estado(kpis['pct_ponderado'])),
        ('{:.1f}%'.format(kpis['pct_estricto']), 'Terminado estricto',
         _color_estado(kpis['pct_estricto'])),
        ('{}/{}'.format(kpis['x'], kpis['total']), 'Celdas terminadas', COL_NAVY),
        (str(len(frentes)), 'Tajos listos', COL_ACCENT),
        (str(len(objetivos_bloqueados)), 'Tajos condicionados',
         COL_WARN if objetivos_bloqueados else COL_ACCENT),
    ]
    hechos, total_hitos = _conteo_cierre(cierre)
    if incluir_cierre and total_hitos:
        tarjetas.append(('{}/{}'.format(hechos, total_hitos),
                         'Cierre de expediente', COL_NAVY))

    # La razon X/total es el unico valor que crece con el volumen de obra.
    # Se le reserva mas anchura que a los contadores de una o dos cifras;
    # el reparto sigue sumando exactamente el ancho disponible.
    pesos_base = [1.0, 1.0, 1.30, .82, .93, .95]
    pesos = pesos_base[:len(tarjetas)]
    unidad = content_w / sum(pesos)
    anchos = [unidad * peso for peso in pesos]
    celdas = []
    for indice, ((valor, etiqueta, color), ancho_celda) in enumerate(
            zip(tarjetas, anchos)):
        size_valor = _fuente_escalada(22, escala, 20, 24)
        ancho_util = ancho_celda - 4.5
        ancho_a_1pt = pdfmetrics.stringWidth(valor, FUENTE_BOLD, 1)
        if ancho_a_1pt:
            size_valor = max(16, min(size_valor, ancho_util / ancho_a_1pt))
        estilo_valor = _style(
            'kpi_valor_{}'.format(indice), size_valor, True,
            align=TA_CENTER, leading=size_valor * 1.02)
        # ReportLab considera la barra una oportunidad de salto. Aunque la
        # cifra quepa, sin esta guarda puede partir 1309/1547 en dos lineas.
        estilo_valor.splitLongWords = 0
        celdas.append([
            Paragraph(
                '<nobr><font color={}><b>{}</b></font></nobr>'.format(
                    color.hexval(), _texto(valor)),
                estilo_valor),
            Spacer(1, max(.4 * mm, .8 * mm * escala)),
            Paragraph(
                _texto(etiqueta),
                _estilo_maqueta('kpi_etiqueta_{}'.format(indice), 8.8,
                                escala, minimo=8.5, align=TA_CENTER,
                                color=COL_MUTED, factor_leading=1.08)),
        ])
    tabla = Table([celdas], colWidths=anchos)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COL_LIGHT),
        ('BOX', (0, 0), (-1, -1), .7, COL_LINE),
        ('INNERGRID', (0, 0), (-1, -1), .35, COL_LINE),
        ('TOPPADDING', (0, 0), (-1, -1), max(2.5, 3.4 * escala)),
        ('BOTTOMPADDING', (0, 0), (-1, -1), max(2.5, 3.4 * escala)),
        ('LEFTPADDING', (0, 0), (-1, -1), 1.2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1.2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return tabla


def _grafico_tendencia(
    serie: list[dict],
    ancho: float,
    escala: float = 1.0,
    total_actual: float | None = None,
) -> Drawing:
    """Evolucion vectorial con etiquetas seleccionadas por espacio real."""
    datos = serie[-12:]
    alto = max(45 * mm, 55 * mm * escala)
    dibujo = Drawing(ancho, alto)
    x0, y0 = 16 * mm, 12 * mm
    plot_w, plot_h = ancho - 21 * mm, alto - 20 * mm
    fuente_eje = _fuente_escalada(8.8, escala, 8.5)

    cajas_ocupadas = []

    def caja_texto(x, y, texto, ancla='middle'):
        ancho_texto = pdfmetrics.stringWidth(texto, FUENTE_BOLD, fuente_eje)
        if ancla == 'start':
            izquierda = x
        elif ancla == 'end':
            izquierda = x - ancho_texto
        else:
            izquierda = x - ancho_texto / 2
        return (izquierda, y - fuente_eje * .25,
                izquierda + ancho_texto, y + fuente_eje * .9)

    def solapa(caja):
        return any(
            max(caja[0], otra[0]) < min(caja[2], otra[2])
            and max(caja[1], otra[1]) < min(caja[3], otra[3])
            for otra in cajas_ocupadas)

    for valor in (0, 25, 50, 75, 100):
        y = y0 + plot_h * valor / 100
        dibujo.add(Line(x0, y, x0 + plot_w, y, strokeColor=COL_LINE,
                        strokeWidth=.45))
        texto_eje = '{}%'.format(valor)
        dibujo.add(String(
            x0 - 2 * mm, y - 1.5, texto_eje, fontName=FUENTE,
            fontSize=fuente_eje, textAnchor='end', fillColor=COL_MUTED))
        ancho_eje = pdfmetrics.stringWidth(texto_eje, FUENTE, fuente_eje)
        cajas_ocupadas.append((
            x0 - 2 * mm - ancho_eje, y - 1.5 - fuente_eje * .25,
            x0 - 2 * mm, y - 1.5 + fuente_eje * .9))

    if not datos:
        dibujo.add(String(
            ancho / 2, alto / 2, 'Sin historial comparable',
            fontName=FUENTE_ITALIC, fontSize=fuente_eje,
            textAnchor='middle', fillColor=COL_MUTED))
        return dibujo

    if len(datos) == 1:
        puntos = [(x0 + plot_w / 2,
                   y0 + plot_h * datos[0]['pct'] / 100)]
    else:
        puntos = [
            (x0 + i * plot_w / (len(datos) - 1),
             y0 + plot_h * dato['pct'] / 100)
            for i, dato in enumerate(datos)
        ]
    if len(puntos) >= 2:
        dibujo.add(PolyLine(puntos, strokeColor=COL_ACCENT,
                            strokeWidth=2, fillColor=None))
    for x, y in puntos:
        dibujo.add(Circle(x, y, 2.2, fillColor=colors.white,
                          strokeColor=COL_ACCENT, strokeWidth=1.2))

    obligatorios = {
        0, len(datos) - 1,
        min(range(len(datos)), key=lambda i: datos[i]['pct']),
        max(range(len(datos)), key=lambda i: datos[i]['pct']),
    }
    indices_valor = set(obligatorios)
    for indice, (x, _y) in enumerate(puntos):
        if indice in indices_valor:
            continue
        if all(abs(x - puntos[otro][0]) >= 11 * mm
               for otro in indices_valor):
            indices_valor.add(indice)

    cajas_valores = {}
    for orden, indice in enumerate(sorted(indices_valor)):
        x, y = puntos[indice]
        dato = datos[indice]
        texto_valor = '{:.1f}%'.format(dato['pct'])
        if indice == 0:
            x_etiqueta, ancla = x + 2.5 * mm, 'start'
        elif indice == len(datos) - 1:
            x_etiqueta, ancla = x - 2.5 * mm, 'end'
        else:
            x_etiqueta, ancla = x, 'middle'
        preferidos = ((6, -12, 15, -22, 25, -31)
                      if orden % 2 == 0 else
                      (-12, 6, -22, 15, -31, 25))
        y_etiqueta = None
        caja = None
        for desplazamiento in preferidos:
            candidato_y = min(
                y0 + plot_h + 8,
                max(y0 + fuente_eje * .35, y + desplazamiento))
            candidato = caja_texto(
                x_etiqueta, candidato_y, texto_valor, ancla)
            if not solapa(candidato):
                y_etiqueta, caja = candidato_y, candidato
                break
        if y_etiqueta is None:
            y_etiqueta = min(y0 + plot_h + 8, y + 6)
            caja = caja_texto(x_etiqueta, y_etiqueta, texto_valor, ancla)
        dibujo.add(String(
            x_etiqueta, y_etiqueta, texto_valor,
            fontName=FUENTE_BOLD, fontSize=fuente_eje,
            textAnchor=ancla, fillColor=COL_ACCENT))
        cajas_ocupadas.append(caja)
        cajas_valores[indice] = caja

    indices_fecha = [0]
    if len(puntos) > 1:
        for indice in range(1, len(puntos) - 1):
            x = puntos[indice][0]
            if (x - puntos[indices_fecha[-1]][0] >= 14 * mm
                    and puntos[-1][0] - x >= 14 * mm):
                indices_fecha.append(indice)
        indices_fecha.append(len(puntos) - 1)
    for indice in indices_fecha:
        x = puntos[indice][0]
        dato = datos[indice]
        dibujo.add(String(
            x, 3.2 * mm, str(dato['fecha'])[:5], fontName=FUENTE,
            fontSize=fuente_eje, textAnchor='middle', fillColor=COL_MUTED))

    if total_actual is not None:
        x = puntos[-1][0]
        y = y0 + plot_h * max(0, min(100, total_actual)) / 100
        dibujo.add(Circle(x, y, 3.4, fillColor=COL_NAVY,
                          strokeColor=colors.white, strokeWidth=1.1))
        ancla = 'end' if x > ancho * .72 else 'start'
        dx = -3 * mm if ancla == 'end' else 3 * mm
        texto_total = 'Total obra {:.1f}%'.format(total_actual)
        x_total = x + dx
        y_total = None
        caja_total = None
        for desplazamiento in (-14, 8, -24, 18, -33, 27):
            candidato_y = min(
                y0 + plot_h + 10,
                max(y0 + fuente_eje * .35, y + desplazamiento))
            candidato = caja_texto(
                x_total, candidato_y, texto_total, ancla)
            if not solapa(candidato):
                y_total, caja_total = candidato_y, candidato
                break
        if y_total is None:
            y_total = max(y0 + fuente_eje * .35, y - 14)
        dibujo.add(String(
            x_total, y_total, texto_total,
            fontName=FUENTE_BOLD, fontSize=fuente_eje,
            textAnchor=ancla, fillColor=COL_NAVY))
    return dibujo


def _grafico_distribucion(snapshot: list[dict], ancho: float,
                          escala: float = 1.0) -> Drawing:
    alto = max(42 * mm, 52 * mm * escala)
    dibujo = Drawing(ancho, alto)
    total = max(1, len(snapshot))
    segmentos = [
        ('Terminado X', sum(r.get('status') == 'X' for r in snapshot), COL_ACCENT),
        ('En marcha M', sum(r.get('status') == 'M' for r in snapshot),
         colors.HexColor('#5B8DB8')),
        ('Iniciado /', sum(r.get('status') == '/' for r in snapshot),
         colors.HexColor('#8FB3D9')),
        ('Pendiente', sum(r.get('status') == '' for r in snapshot), COL_LINE),
    ]
    x0, y0, barra_w, barra_h = 2 * mm, alto * .55, ancho - 4 * mm, 8 * mm
    cursor = x0
    for _etiqueta, n, color in segmentos:
        w = barra_w * n / total
        if w > 0:
            dibujo.add(Rect(cursor, y0, w, barra_h, fillColor=color,
                            strokeColor=colors.white, strokeWidth=.4))
            cursor += w
    font_size = _fuente_escalada(8.7, escala, 8.5)
    mitad = ancho / 2
    for indice, (etiqueta, n, color) in enumerate(segmentos):
        col = indice % 2
        fila = indice // 2
        x = 2 * mm + col * mitad
        y = 8 * mm + (1 - fila) * 8 * mm
        dibujo.add(Rect(x, y, 3.2 * mm, 3.2 * mm,
                        fillColor=color, strokeColor=color))
        dibujo.add(String(
            x + 4.3 * mm, y + .2 * mm, '{}: {}'.format(etiqueta, n),
            fontName=FUENTE, fontSize=font_size, fillColor=COL_MUTED))
    return dibujo


def _dibujo_barra_linea(nombre: str, pct: float, x: int, total: int,
                        ancho: float, escala: float,
                        ancho_nombre: float) -> Drawing:
    """Fase en una sola linea: rotulo, barra y valor. Cuesta ~5,6 mm por fase
    en vez de los ~8,5 mm de la variante con el rotulo encima de la barra, y
    ese espacio se dedica a mostrar mas filas de las tablas de la hoja."""
    alto = max(5.2 * mm, 5.6 * mm * escala)
    dibujo = Drawing(ancho, alto)
    font_size = _fuente_escalada(8.7, escala, 8.5)
    valor = '{:.1f}%  {}/{}'.format(pct, x, total)
    ancho_valor = pdfmetrics.stringWidth(valor, FUENTE_BOLD, font_size)
    etiqueta = str(nombre)
    # La variante en linea solo se elige cuando el nombre cabe entero
    # (ver _tabla_fases_doble); este recorte es una red de seguridad.
    if pdfmetrics.stringWidth(etiqueta, FUENTE, font_size) > ancho_nombre:
        recortada = etiqueta
        while (recortada
               and pdfmetrics.stringWidth(
                   recortada.rstrip() + '…', FUENTE, font_size)
               > ancho_nombre):
            recortada = recortada[:-1]
        etiqueta = recortada.rstrip() + '…'
    base = (alto - font_size * .72) / 2
    dibujo.add(String(0, base, etiqueta, fontName=FUENTE,
                      fontSize=font_size, fillColor=COL_NAVY))
    x0 = ancho_nombre + 1.5 * mm
    ancho_barra = max(8 * mm, ancho - ancho_valor - 1.5 * mm - x0)
    grosor = 2.8 * mm
    y = (alto - grosor) / 2
    dibujo.add(Rect(x0, y, ancho_barra, grosor,
                    fillColor=colors.HexColor('#E8EDF3'), strokeColor=None))
    color = _color_estado(pct)
    dibujo.add(Rect(x0, y, ancho_barra * max(0, min(100, pct)) / 100, grosor,
                    fillColor=color, strokeColor=None))
    dibujo.add(String(ancho, base, valor, fontName=FUENTE_BOLD,
                      fontSize=font_size, textAnchor='end',
                      fillColor=color))
    return dibujo


def _dibujo_barra_resumen(nombre: str, pct: float, x: int, total: int,
                          ancho: float, escala: float,
                          mostrar_nombre: bool = True) -> Drawing:
    alto = max(8 * mm, 8.5 * mm * escala)
    dibujo = Drawing(ancho, alto)
    font_size = _fuente_escalada(8.7, escala, 8.5)
    etiqueta = str(nombre)
    valor = '{:.1f}%  {}/{}'.format(pct, x, total)
    ancho_valor = pdfmetrics.stringWidth(valor, FUENTE_BOLD, font_size)
    ancho_nombre = max(10 * mm, ancho - ancho_valor - 3 * mm)
    # Antes de recortar un nombre con puntos suspensivos se reduce su letra
    # hasta el minimo de 8,5 pt: un nombre cortado no se distingue de otro.
    tam_nombre = font_size
    while (tam_nombre > 8.5
           and pdfmetrics.stringWidth(etiqueta, FUENTE_BOLD, tam_nombre)
           > ancho_nombre):
        tam_nombre = max(8.5, tam_nombre - .25)
    if pdfmetrics.stringWidth(etiqueta, FUENTE_BOLD, tam_nombre) > ancho_nombre:
        recortada = etiqueta
        while (recortada
               and pdfmetrics.stringWidth(
                   recortada.rstrip() + '\u2026', FUENTE_BOLD, tam_nombre)
               > ancho_nombre):
            recortada = recortada[:-1]
        etiqueta = recortada.rstrip() + '\u2026'
    if mostrar_nombre:
        dibujo.add(String(0, alto - font_size, etiqueta, fontName=FUENTE_BOLD,
                          fontSize=tam_nombre, fillColor=COL_NAVY))
    color = _color_estado(pct)
    dibujo.add(String(ancho, alto - font_size, valor, fontName=FUENTE_BOLD,
                      fontSize=font_size, textAnchor='end',
                      fillColor=color))
    y = 1.2 * mm
    dibujo.add(Rect(0, y, ancho, 2.4 * mm, fillColor=colors.HexColor('#E8EDF3'),
                    strokeColor=None))
    dibujo.add(Rect(0, y, ancho * max(0, min(100, pct)) / 100, 2.4 * mm,
                    fillColor=color, strokeColor=None))
    return dibujo


def _tabla_fases_doble(fases: list[dict], content_w: float,
                        escala: float = 1.0) -> Table | Paragraph:
    if not fases:
        return Paragraph(
            '<i>Sin fases propias medidas en este \u00e1mbito.</i>',
            _estilo_maqueta('sin_fases', 8.7, escala, minimo=8.5,
                            color=COL_MUTED))
    mitad = (content_w - 4 * mm) / 2
    ancho_celda = mitad - 3 * mm
    font_size = _fuente_escalada(8.7, escala, 8.5)
    # Linea unica (rotulo, barra y valor) solo si NINGUN nombre se corta y la
    # barra conserva al menos 17 mm; si no, la variante con el rotulo encima.
    # Un nombre cortado es peor que una barra mas alta.
    ancho_nombre = max(
        pdfmetrics.stringWidth(str(f['fase']), FUENTE, font_size)
        for f in fases) + .8 * mm
    ancho_valor_max = max(
        pdfmetrics.stringWidth('{:.1f}%  {}/{}'.format(
            f['pct'], f['x'], f['total']), FUENTE_BOLD, font_size)
        for f in fases)
    barra_disponible = ancho_celda - ancho_nombre - ancho_valor_max - 3 * mm
    if barra_disponible >= 17 * mm:
        celdas = [
            _dibujo_barra_linea(
                fase['fase'], fase['pct'], fase['x'], fase['total'],
                ancho_celda, escala, ancho_nombre)
            for fase in fases
        ]
    else:
        celdas = [
            _dibujo_barra_resumen(
                fase['fase'], fase['pct'], fase['x'], fase['total'],
                ancho_celda, escala)
            for fase in fases
        ]
    filas = []
    for indice in range(0, len(celdas), 2):
        filas.append([celdas[indice],
                      celdas[indice + 1] if indice + 1 < len(celdas) else ''])
    alto_dibujo = celdas[0].height
    # Una sola fase no debe reservar media pagina vacia; con muchas fases
    # manda la altura natural de cada dibujo.
    alto_total_minimo = 12 * mm * escala
    alto_fila = max(alto_dibujo + .8 * mm,
                    alto_total_minimo / max(1, len(filas)))
    tabla = Table(filas, colWidths=[mitad, mitad],
                  rowHeights=[alto_fila] * len(filas))
    tabla.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, -1), 2 * mm),
        ('LEFTPADDING', (1, 0), (1, -1), 2 * mm),
        ('RIGHTPADDING', (1, 0), (1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return tabla


def _tabla_tajos_atencion(tajos: list[dict], content_w: float,
                           escala: float = 1.0,
                           max_filas: int = 10) -> Table | Paragraph:
    pendientes = [t for t in tajos if t['pct'] < 99.9]
    pendientes.sort(key=lambda t: (t['orden'], t['pct'], _fold(t['nombre'])))
    if not pendientes:
        return Paragraph(
            '<i>Todos los tajos propios medidos est\u00e1n terminados.</i>',
            _estilo_maqueta('tajos_completos_ajustado', 8.7, escala,
                            minimo=8.5, color=COL_ACCENT))
    th = lambda n: _estilo_maqueta(n, 8.6, escala, minimo=8.5,
                                   bold=True, color=colors.white,
                                   align=TA_CENTER)
    filas = [[
        Paragraph('<b>Tajo Sagarde / fase</b>', th('th_tajo_ajustado')),
        Paragraph('<b>Avance</b>', th('th_avance_ajustado')),
        Paragraph('<b>Hecho</b>', th('th_hecho_ajustado')),
        Paragraph('<b>Pend.</b>', th('th_pend_ajustado')),
    ]]
    for indice, tajo in enumerate(pendientes[:max_filas]):
        estilo = _estilo_maqueta('td_tajo_{}'.format(indice), 8.6, escala,
                                 minimo=8.5, factor_leading=1.08)
        centro = _estilo_maqueta('td_centro_{}'.format(indice), 8.6, escala,
                                 minimo=8.5, align=TA_CENTER,
                                 factor_leading=1.08)
        filas.append([
            Paragraph('<b>{}</b><br/><font color=#475467>{}</font>'.format(
                _texto(tajo['nombre']), _texto(tajo['fase'])), estilo),
            Paragraph('<font color={}><b>{:.0f}%</b></font>'.format(
                _color_estado(tajo['pct']).hexval(), tajo['pct']), centro),
            Paragraph('{}/{}'.format(tajo['x'], tajo['total']), centro),
            Paragraph(str(tajo['pendiente']), centro),
        ])
    restantes = len(pendientes) - max_filas
    if restantes > 0:
        filas.append([
            Paragraph(
                '<b>+{} m\u00e1s</b> \u00b7 contin\u00faan en el mismo orden de ejecuci\u00f3n'.format(
                    restantes),
                _estilo_maqueta('tajos_mas', 8.6, escala, minimo=8.5,
                                bold=True, color=COL_MUTED)), '', '', '',
        ])
    tabla = Table(
        filas,
        colWidths=[content_w * .58, content_w * .15,
                   content_w * .14, content_w * .13])
    estilos = [
        ('BACKGROUND', (0, 0), (-1, 0), COL_NAVY),
        ('GRID', (0, 0), (-1, -1), .3, COL_LINE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COL_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), max(1.4, 1.8 * escala)),
        ('BOTTOMPADDING', (0, 0), (-1, -1), max(1.4, 1.8 * escala)),
        ('LEFTPADDING', (0, 0), (-1, -1), 2.2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2.2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    if restantes > 0:
        estilos.append(('SPAN', (0, -1), (-1, -1)))
    tabla.setStyle(TableStyle(estilos))
    return tabla


def _tabla_lista_compacta(items: list[dict], ancho: float, escala: float,
                           tipo: str, max_filas: int = 4):
    es_bloqueo = tipo == 'bloqueo'
    if not items:
        texto = ('No hay dependencias activas que frenen producci\u00f3n Sagarde.'
                 if es_bloqueo else
                 'No hay frentes propios clasificados como listos.')
        return Paragraph(
            '<i>{}</i>'.format(_texto(texto)),
            _estilo_maqueta('lista_vacia_' + tipo, 8.6, escala,
                            minimo=8.5, color=COL_MUTED))
    cabecera = 'Condicionante' if es_bloqueo else 'Pr\u00f3ximo tajo Sagarde'
    auxiliar = 'Afecta' if es_bloqueo else 'Uds.'
    estilo_h = _estilo_maqueta('lista_h_' + tipo, 8.6, escala,
                               minimo=8.5, bold=True, color=colors.white)
    filas = [[
        Paragraph('<b>{}</b>'.format(cabecera), estilo_h),
        Paragraph('<b>{}</b>'.format(auxiliar),
                  _estilo_maqueta('lista_hc_' + tipo, 8.6, escala,
                                  minimo=8.5, bold=True, color=colors.white,
                                  align=TA_CENTER)),
    ]]
    for indice, item in enumerate(items[:max_filas]):
        if es_bloqueo:
            objetivos = ', '.join(sorted(str(x) for x in item['tajos_sagarde']))
            if len(objetivos) > 42:
                objetivos = objetivos[:41].rstrip() + '\u2026'
            principal = item['trabajo']
            secundario = objetivos
            numero = item['afecta_celdas']
        else:
            principal = item['trabajo']
            secundario = item['fase']
            numero = item['unidades']
        filas.append([
            Paragraph(
                '<b>{}</b><br/><font color=#475467>{}</font>'.format(
                    _texto(principal), _texto(secundario)),
                _estilo_maqueta('lista_d_{}_{}'.format(tipo, indice),
                                8.5, escala, minimo=8.5,
                                factor_leading=1.08)),
            Paragraph(
                str(numero),
                _estilo_maqueta('lista_n_{}_{}'.format(tipo, indice),
                                8.7, escala, minimo=8.5, bold=True,
                                align=TA_CENTER,
                                color=COL_WARN if es_bloqueo else COL_NAVY)),
        ])
    restantes = len(items) - max_filas
    if restantes > 0:
        filas.append([
            Paragraph(
                '<b>+{} m\u00e1s</b>'.format(restantes),
                _estilo_maqueta('lista_mas_' + tipo, 8.6, escala,
                                minimo=8.5, bold=True, color=COL_MUTED)), '',
        ])
    tabla = Table(filas, colWidths=[ancho - 17 * mm, 17 * mm])
    estilos = [
        ('BACKGROUND', (0, 0), (-1, 0), COL_WARN if es_bloqueo else COL_ACCENT),
        ('GRID', (0, 0), (-1, -1), .3, COL_LINE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#FFF8F6') if es_bloqueo else COL_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), max(1.3, 1.7 * escala)),
        ('BOTTOMPADDING', (0, 0), (-1, -1), max(1.3, 1.7 * escala)),
        ('LEFTPADDING', (0, 0), (-1, -1), 2.2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2.2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    if restantes > 0:
        estilos.append(('SPAN', (0, -1), (-1, -1)))
    tabla.setStyle(TableStyle(estilos))
    return tabla


def _tabla_frentes(frentes: list[dict], ancho: float,
                    escala: float = 1.0, max_filas: int = 4):
    return _tabla_lista_compacta(frentes, ancho, escala, 'frente', max_filas)


def _tabla_bloqueadores(bloqueadores: list[dict], ancho: float,
                         escala: float = 1.0, max_filas: int = 4):
    return _tabla_lista_compacta(
        bloqueadores, ancho, escala, 'bloqueo', max_filas)


def _tabla_detalle_zona(zonas: list[dict], content_w: float,
                         escala: float = 1.0,
                         max_zonas: int = 12) -> Table | Paragraph:
    if not zonas:
        return Paragraph(
            '<i>Sin zonas con nombre propio en este \u00e1mbito.</i>',
            _estilo_maqueta('sin_zonas_ajustado', 8.6, escala,
                            minimo=8.5, color=COL_MUTED))
    visibles = zonas[:max_zonas]
    restantes = len(zonas) - len(visibles)
    mitad = (content_w - 2 * mm) / 2
    celdas = []
    for indice, zona in enumerate(visibles):
        texto = '<b>{}</b><br/><font color={}><b>{:.0f}%</b></font> \u00b7 {}/{}'.format(
            _texto(zona['nombre']), _color_estado(zona['pct']).hexval(),
            zona['pct'], zona['x'], zona['total'])
        celda = Table([[Paragraph(
            texto,
            _estilo_maqueta('zona_{}'.format(indice), 8.6, escala,
                            minimo=8.5, color=COL_NAVY,
                            factor_leading=1.12))]], colWidths=[mitad - 2 * mm])
        celda.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COL_LIGHT),
            ('BOX', (0, 0), (-1, -1), .35, COL_LINE),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        celdas.append(celda)
    if restantes > 0:
        celdas.append(Paragraph(
            '<b>+{} m\u00e1s</b>'.format(restantes),
            _estilo_maqueta('zonas_mas', 8.6, escala, minimo=8.5,
                            bold=True, color=COL_MUTED)))
    filas = []
    for indice in range(0, len(celdas), 2):
        filas.append([celdas[indice],
                      celdas[indice + 1] if indice + 1 < len(celdas) else ''])
    tabla = Table(filas, colWidths=[mitad, mitad])
    tabla.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, -1), 1 * mm),
        ('LEFTPADDING', (1, 0), (1, -1), 1 * mm),
        ('RIGHTPADDING', (1, 0), (1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), .7 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), .7 * mm),
    ]))
    return tabla


def _chips_cierre(cierre: dict, avisos: list[str] | None,
                  ancho: float, escala: float) -> list:
    hitos = cierre.get('hitos') or {}
    celdas = []
    for indice, hito_id in enumerate(cierre_expediente.HITOS_ORDEN):
        datos = hitos.get(hito_id) or {'estado': 'pendiente'}
        estado = datos.get('estado') or 'pendiente'
        nombre = cierre_expediente.HITOS_NOMBRE.get(hito_id, hito_id)
        fondo = (colors.HexColor('#FFF1F0')
                 if estado in ('condicionada', 'negativa') else COL_CARD)
        color = COL_WARN if estado in ('condicionada', 'negativa') else COL_NAVY
        chip = Table([[Paragraph(
            '<b>{}</b><br/><font color={}>{}</font>'.format(
                _texto(nombre), color.hexval(), _texto(estado.upper())),
            _estilo_maqueta('chip_cierre_{}'.format(indice), 8.3, escala,
                            minimo=8, color=COL_NAVY,
                            factor_leading=1.1))]], colWidths=[ancho / 2 - 2 * mm])
        chip.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), fondo),
            ('BOX', (0, 0), (-1, -1), .45, COL_LINE),
            ('TOPPADDING', (0, 0), (-1, -1), 2.2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2),
        ]))
        celdas.append(chip)
    filas = [[celdas[0], celdas[1]], [celdas[2], celdas[3]]]
    tabla = Table(filas, colWidths=[ancho / 2, ancho / 2])
    tabla.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    salida = [tabla]
    for indice, aviso in enumerate(avisos or []):
        salida.append(Paragraph(
            '\u26a0 {}'.format(_texto(aviso)),
            _estilo_maqueta('aviso_cierre_chip_{}'.format(indice), 8.1,
                            escala, minimo=8, color=COL_WARN)))
    return salida


def _tabla_avance_componentes(componentes: list[dict], ancho: float,
                               escala: float,
                               max_filas: int = 10):
    if not componentes:
        return [Paragraph(
            '<i>Sin subdivisiones adicionales.</i>',
            _estilo_maqueta('sin_componentes', 8.6, escala,
                            minimo=8.5, color=COL_MUTED))]
    visibles = componentes[:max_filas]
    dibujos = []
    for componente in visibles:
        kpis = motor_informes.kpis_snapshot(componente['snapshot'])
        dibujos.append(_dibujo_barra_resumen(
            componente['nombre'], kpis['pct_ponderado'], kpis['x'],
            kpis['total'], ancho, escala))
    restantes = len(componentes) - len(visibles)
    if restantes > 0:
        dibujos.append(Paragraph(
            '<b>+{} m\u00e1s</b>'.format(restantes),
            _estilo_maqueta('componentes_mas', 8.6, escala,
                            minimo=8.5, bold=True, color=COL_MUTED)))
    return dibujos


def _pie_electrico(fecha_rev: str, content_w: float,
                   escala: float = 1.0) -> Table:
    generado = datetime.now().strftime('%d/%m/%Y %H:%M')
    texto = ('Fuente: base viva de la obra + cat\u00e1logo de tajos y dependencias \u00b7 '
             'Datos {} \u00b7 Generado {}').format(_texto(fecha_rev), generado)
    tabla = Table([[
        Paragraph(
            texto,
            _estilo_maqueta('pie_fuente_ajustado', 8.1, escala,
                            minimo=8, color=COL_MUTED)),
        Paragraph(
            '<b>Montajes El\u00e9ctricos Sagarde, S.L.</b>',
            _estilo_maqueta('pie_marca_ajustado', 8.2, escala,
                            minimo=8, bold=True, align=TA_RIGHT,
                            color=COL_NAVY)),
    ]], colWidths=[128 * mm, content_w - 128 * mm])
    tabla.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), .5, COL_LINE),
        ('TOPPADDING', (0, 0), (-1, -1), 2.4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    return tabla


def _datos_pagina_electrica(
    snapshot_propio: list[dict],
    historial: list | None,
    prioridades: dict | None,
    metadatos_por_id: dict,
    metadatos_por_nombre: dict,
    referencias: set[str] | None = None,
) -> dict:
    """Calcula solo con helpers vigentes; la maqueta consume este resultado."""
    return {
        'kpis': motor_informes.kpis_snapshot(snapshot_propio),
        'serie': _serie_avance_sagarde(
            historial, metadatos_por_nombre, referencias),
        'fases': _resumen_fases_sagarde(snapshot_propio, metadatos_por_nombre),
        'tajos': _resumen_tajos_sagarde(snapshot_propio, metadatos_por_nombre),
        'frentes': _frentes_sagarde(
            prioridades, metadatos_por_id, referencias),
        'bloqueadores': _bloqueadores_sagarde(
            prioridades, metadatos_por_id, referencias),
    }


def _panel_superior(
    datos: dict,
    snapshot_propio: list[dict],
    content_w: float,
    escala: float,
    componentes: list[dict] | None,
    titulo_componentes: str,
    cierre: dict | None,
    avisos_cierre: list[str] | None,
    hay_garaje: bool,
    zonas: list[dict] | None,
) -> Table:
    ancho_izq = content_w * .59
    ancho_der = content_w - ancho_izq - 4 * mm
    serie = [dict(punto) for punto in datos['serie']]
    total_actual = None
    if serie and not hay_garaje:
        # Sin garaje, la ultima etiqueta representa el mismo snapshot actual
        # que el KPI. No se altera el historial de entrada, solo su rotulo.
        serie[-1]['pct'] = datos['kpis']['pct_ponderado']
    elif hay_garaje:
        total_actual = datos['kpis']['pct_ponderado']

    izquierda = []
    if len(serie) >= 4:
        izquierda.extend([
            _seccion('Evoluci\u00f3n (viviendas)' if hay_garaje else
                     'Evoluci\u00f3n del avance', escala),
            _nota('Cada punto muestra el avance ponderado de la revisi\u00f3n; '
                  'el marcador final distingue el total de obra cuando '
                  'existe garaje.', escala),
            _grafico_tendencia(
                serie, ancho_izq - 2 * mm, escala, total_actual=total_actual),
        ])
    else:
        izquierda.extend([
            _seccion('Estado actual del alcance Sagarde', escala),
            _nota('Sin cuatro revisiones comparables; composici\u00f3n del '
                  '\u00faltimo estado medido.', escala),
            _grafico_distribucion(snapshot_propio, ancho_izq - 2 * mm, escala),
        ])

    derecha = []
    if zonas is not None:
        derecha.extend([
            _seccion('Detalle por zona', escala),
            _tabla_detalle_zona(zonas, ancho_der, escala),
        ])
    else:
        derecha.append(_seccion(titulo_componentes, escala))
        derecha.extend(_tabla_avance_componentes(
            componentes or [], ancho_der, escala))
        if cierre is not None and (cierre.get('hitos') or {}):
            derecha.extend([
                Spacer(1, max(.8 * mm, 1.2 * mm * escala)),
                _seccion('Cierre de expediente', escala),
                *_chips_cierre(cierre, avisos_cierre, ancho_der, escala),
            ])

    tabla = Table([[izquierda, derecha]],
                  colWidths=[ancho_izq, ancho_der])
    tabla.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 2 * mm),
        ('LEFTPADDING', (1, 0), (1, 0), 2 * mm),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return tabla


def _panel_inferior(datos: dict, content_w: float, escala: float,
                    limites: dict | None = None) -> Table:
    limites = limites or {'tajos': 10, 'frentes': 4, 'bloqueadores': 4}
    ancho_izq = content_w * .61
    ancho_der = content_w - ancho_izq - 4 * mm
    izquierda = [
        _seccion('Tajos que requieren atenci\u00f3n', escala),
        _nota('Hasta {} filas, en el orden de ejecuci\u00f3n de la base.'.format(
            limites['tajos']), escala),
        _tabla_tajos_atencion(
            datos['tajos'], ancho_izq, escala=escala,
            max_filas=limites['tajos']),
    ]
    derecha = [
        _seccion('Condicionantes', escala,
                 color=COL_WARN if datos['bloqueadores'] else COL_NAVY),
        _tabla_bloqueadores(
            datos['bloqueadores'], ancho_der, escala=escala,
            max_filas=limites['bloqueadores']),
        Spacer(1, max(.8 * mm, 1.2 * mm * escala)),
        _seccion('Pr\u00f3ximos frentes', escala),
        _tabla_frentes(
            datos['frentes'], ancho_der, escala=escala,
            max_filas=limites['frentes']),
    ]
    tabla = Table([[izquierda, derecha]],
                  colWidths=[ancho_izq, ancho_der])
    tabla.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 2 * mm),
        ('LEFTPADDING', (1, 0), (1, 0), 2 * mm),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return tabla


def _crear_pagina_electrica(
    escala: float,
    nombre_obra: str,
    sub_titulo: str,
    fecha_rev: str,
    snapshot_propio: list[dict],
    historial: list | None,
    ficha: dict | None,
    prioridades: dict | None,
    metadatos_por_id: dict,
    metadatos_por_nombre: dict,
    content_w: float,
    referencias: set[str] | None = None,
    cierre: dict | None = None,
    avisos_cierre: list[str] | None = None,
    componentes: list[dict] | None = None,
    titulo_componentes: str = 'Avance por bloque',
    hay_garaje: bool = False,
    zonas: list[dict] | None = None,
    limites: dict | None = None,
) -> list:
    datos = _datos_pagina_electrica(
        snapshot_propio, historial, prioridades, metadatos_por_id,
        metadatos_por_nombre, referencias)
    hueco = lambda base: Spacer(1, max(.7 * mm, base * mm * escala))
    pagina = [
        _cabecera_electrica(
            nombre_obra, sub_titulo, fecha_rev, ficha, content_w, escala),
        hueco(1.2),
        _tabla_kpis_electricos(
            snapshot_propio, datos['frentes'], datos['bloqueadores'],
            content_w, cierre=cierre, incluir_cierre=cierre is not None,
            escala=escala),
        hueco(1.2),
        _resumen_ejecutivo_pagina(
            datos, content_w, escala, solo_viviendas=hay_garaje),
        hueco(1.2),
        _panel_superior(
            datos, snapshot_propio, content_w, escala, componentes,
            titulo_componentes, cierre, avisos_cierre, hay_garaje, zonas),
        hueco(1.2),
        _seccion('Fases de producci\u00f3n', escala),
        _nota('Porcentaje ponderado y celdas terminadas sobre el total '
              'medido de cada fase.', escala),
        _leyenda_tramos(content_w, escala),
        _tabla_fases_doble(datos['fases'], content_w, escala),
        hueco(1.2),
        _panel_inferior(datos, content_w, escala, limites=limites),
        hueco(1.1),
        _pie_electrico(fecha_rev, content_w, escala),
    ]
    return pagina


def _medir_flowables(flowables: list, ancho: float) -> float:
    alto = 0.0
    for flowable in flowables:
        _w, h = flowable.wrap(ancho, 1000 * mm)
        alto += h
    return alto


def _ajustar_pagina(fabrica, ancho: float, alto: float,
                    etiqueta: str, planes: list[dict] | None = None,
                    ocupacion_max: float = 1.0) -> dict:
    """Ajusta sin abortar: recorta con trazabilidad y usa 0.85 al final."""
    candidatos = [round(.90 + paso * .05, 2) for paso in range(13)]
    planes_efectivos = planes or [None]
    limite_alto = alto * ocupacion_max

    def construir(escala, limites):
        return fabrica(escala) if limites is None else fabrica(escala, limites)

    def resultado(flowables, escala, alto_natural, limites, indice_plan,
                  forzado=False):
        return {
            'flowables': flowables,
            'escala': escala,
            'alto': alto_natural,
            'ocupacion': alto_natural / alto if alto else 0,
            'limites': dict(limites) if limites is not None else None,
            'recortado': indice_plan > 0,
            'forzado': forzado,
        }

    for indice_plan, limites in enumerate(planes_efectivos):
        for escala in reversed(candidatos):
            flowables = construir(escala, limites)
            alto_natural = _medir_flowables(flowables, ancho)
            if alto_natural > limite_alto + .01:
                continue

            limites_finales = dict(limites) if limites is not None else None
            # La columna izquierda suele mandar la altura. Mientras no crezca
            # la pagina se aprovecha ese hueco con mas filas a la derecha.
            if limites_finales is not None:
                for clave in ('bloqueadores', 'frentes'):
                    while limites_finales[clave] < 12:
                        ampliados = dict(limites_finales)
                        ampliados[clave] += 1
                        prueba = construir(escala, ampliados)
                        alto_prueba = _medir_flowables(prueba, ancho)
                        if alto_prueba > limite_alto + .01:
                            break
                        limites_finales = ampliados
                        flowables, alto_natural = prueba, alto_prueba

            if indice_plan > 0:
                print(
                    '[AVISO INFORME EJECUTIVO] Recorte visible para {!r}: '
                    'tajos={}, condicionantes={}, frentes={}; las tablas '
                    'declaran lo omitido con "+N m\u00e1s".'.format(
                        etiqueta, limites_finales['tajos'],
                        limites_finales['bloqueadores'],
                        limites_finales['frentes']))
            return resultado(
                flowables, escala, alto_natural, limites_finales, indice_plan)

    limites_finales = planes_efectivos[-1]
    flowables = construir(.85, limites_finales)
    alto_minimo = _medir_flowables(flowables, ancho)
    if alto_minimo <= limite_alto + .01:
        if limites_finales is not None:
            print(
                '[AVISO INFORME EJECUTIVO] Recorte visible y escala 0.85 '
                'para {!r}: tajos={}, condicionantes={}, frentes={}; las '
                'tablas declaran lo omitido con "+N m\u00e1s".'.format(
                    etiqueta, limites_finales['tajos'],
                    limites_finales['bloqueadores'],
                    limites_finales['frentes']))
        return resultado(
            flowables, .85, alto_minimo, limites_finales,
            len(planes_efectivos) - 1)

    print(
        '[AVISO INFORME EJECUTIVO] {!r} excede la altura incluso con el '
        'recorte maximo y escala 0.85: {:.1f} mm necesarios y {:.1f} mm '
        'disponibles. Se genera igualmente; no se conserva un PDF antiguo '
        'en silencio.'.format(
            etiqueta, alto_minimo / mm, alto / mm))
    return resultado(
        flowables, .85, alto_minimo, limites_finales,
        len(planes_efectivos) - 1, forzado=True)


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
    alto_util: float | None = None,
    cierre: dict | None = None,
    avisos_cierre: list[str] | None = None,
    componentes: list[dict] | None = None,
    titulo_componentes: str = 'Avance por bloque',
    hay_garaje: bool = False,
    zonas: list[dict] | None = None,
) -> dict:
    propios = _filtrar_snapshot_sagarde(
        snapshot, metadatos_por_nombre, referencias)
    alto_disponible = (alto_util if alto_util is not None
                       else PAGE_H - 2 * MARGIN_Y - 4 * mm)
    planes_recorte = [
        {'tajos': 10, 'bloqueadores': 4, 'frentes': 4},
        {'tajos': 8, 'bloqueadores': 4, 'frentes': 4},
        {'tajos': 6, 'bloqueadores': 4, 'frentes': 4},
        {'tajos': 6, 'bloqueadores': 3, 'frentes': 3},
        {'tajos': 6, 'bloqueadores': 2, 'frentes': 2},
    ]
    ajuste = _ajustar_pagina(
        lambda escala, limites: _crear_pagina_electrica(
            escala, nombre_obra, sub_titulo, fecha_rev, propios, historial,
            ficha, prioridades, metadatos_por_id, metadatos_por_nombre,
            content_w, referencias=referencias, cierre=cierre,
            avisos_cierre=avisos_cierre, componentes=componentes,
            titulo_componentes=titulo_componentes, hay_garaje=hay_garaje,
            zonas=zonas, limites=limites),
        content_w, alto_disponible,
        '{} \u00b7 {}'.format(nombre_obra, sub_titulo),
        planes=planes_recorte, ocupacion_max=.96)
    story.extend(ajuste['flowables'])
    return ajuste


def _componentes_por_campo(snapshot: list[dict], campo: str) -> list[dict]:
    grupos = motor_informes._agrupar(snapshot, campo) if snapshot else {}
    return [
        {'nombre': str(nombre), 'snapshot': registros}
        for nombre, registros in sorted(
            grupos.items(), key=lambda item: _fold(item[0]))
    ]


def _clave_registro(registro: dict) -> tuple:
    return tuple(registro.get(campo) for campo in
                 ('task', 'building', 'floor', 'unit', 'status'))


def _sin_subsnapshot(snapshot: list[dict], subsnapshot: list[dict] | None) -> list[dict]:
    claves = {_clave_registro(r) for r in (subsnapshot or [])}
    return [r for r in snapshot if _clave_registro(r) not in claves]


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


def _portales_del_informe(meta: dict | None,
                          snapshot: list[dict]) -> list[tuple[str, str, str]]:
    """Devuelve referencia, rotulo corto unico y nombre real de cada portal."""
    entradas = []
    for bloque in (meta or {}).get('bloques') or []:
        bloque_nombre = str(bloque.get('nombre') or '').strip()
        for portal in bloque.get('portales') or []:
            portal_nombre = str(portal.get('nombre') or '').strip()
            referencia = (portal.get('referencia_portal')
                          or portal.get('referencia') or portal_nombre)
            entradas.append((referencia, portal_nombre, bloque_nombre))

    if not entradas:
        return [
            (nombre, str(nombre), str(nombre))
            for nombre in sorted(
                {r.get('building') for r in snapshot if r.get('building')},
                key=_fold)
        ]

    repeticiones = defaultdict(int)
    for _referencia, portal_nombre, _bloque_nombre in entradas:
        repeticiones[_fold(portal_nombre)] += 1

    salida = []
    for referencia, portal_nombre, bloque_nombre in entradas:
        es_unico = _fold(portal_nombre) in ('portal unico', '')
        if es_unico:
            rotulo = bloque_nombre or portal_nombre or str(referencia)
        elif repeticiones[_fold(portal_nombre)] > 1 and bloque_nombre:
            rotulo = '{} \u00b7 {}'.format(bloque_nombre, portal_nombre)
        else:
            rotulo = portal_nombre
        salida.append((referencia, rotulo, portal_nombre or str(referencia)))
    return salida


# ─── Generación del PDF ───────────────────────────────────────────────────
def generar_pdf_ejecutivo(
    nombre_obra: str,
    fecha_rev: str,
    snapshot: list[dict],
    output_pdf: Path,
    historial: list | None = None,
    ficha: dict | None = None,
    prioridades: dict | None = None,
    snapshot_garaje: list[dict] | None = None,
    prioridades_garaje: dict | None = None,
    snapshot_zonas_especiales: list[dict] | None = None,
    prioridades_zonas_especiales: dict | None = None,
    cierre: dict | None = None,
    avisos_cierre: list[str] | None = None,
) -> Path:
    _registrar_fuentes()
    doc = SimpleDocTemplate(
        str(output_pdf),
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_Y,
        bottomMargin=MARGIN_Y,
        allowSplitting=0,
    )

    story = []
    content_w = PAGE_W - 2 * MARGIN_X
    metadatos_por_id, metadatos_por_nombre = _indice_metadatos_tajos(ficha)

    meta_obras = _cargar_meta_obras()
    meta = meta_obras.get(nombre_obra)

    portal_items = _portales_del_informe(meta, snapshot)

    # 1. Página General de la Obra. Si la obra tiene garaje, el resumen
    #    general cuenta vivienda+garaje juntos (decision de Bixente
    #    25/09/2026: "si hay garaje... forma parte del total de la obra") --
    #    misma bolsa de celdas que ya usa panel_obra.py para el % de
    #    cabecera. El historial y las prioridades de esa llamada siguen
    #    siendo solo de vivienda: no hay una forma honesta de fusionar el
    #    historico de revisiones de vivienda con el de garaje (series
    #    independientes), y los frentes/bloqueadores de garaje ya tienen su
    #    propia pagina completa mas abajo.
    snapshot_general = snapshot + (snapshot_garaje or [])
    snapshot_viviendas = _sin_subsnapshot(
        snapshot, snapshot_zonas_especiales)
    componentes_generales = []
    for ref, lbl, p_nom in portal_items:
        snap_componente = [
            r for r in snapshot_viviendas
            if r.get('building') == ref or r.get('building') == p_nom
        ]
        propios_componente = _filtrar_snapshot_sagarde(
            snap_componente, metadatos_por_nombre)
        if propios_componente:
            componentes_generales.append({
                'nombre': lbl,
                'snapshot': propios_componente,
            })
    if snapshot_garaje:
        propios_garaje = _filtrar_snapshot_sagarde(
            snapshot_garaje, metadatos_por_nombre)
        if propios_garaje:
            componentes_generales.append({
                'nombre': 'GARAJE', 'snapshot': propios_garaje})
    if snapshot_zonas_especiales:
        propios_zesp = _filtrar_snapshot_sagarde(
            snapshot_zonas_especiales, metadatos_por_nombre)
        if propios_zesp:
            componentes_generales.append({
                'nombre': 'ZONAS ESPECIALES', 'snapshot': propios_zesp})
    sub_tit_gen = f"RESUMEN GENERAL ({len(portal_items)} PORTALES/BLOQUES)" if len(portal_items) >= 2 else "RESUMEN GENERAL"
    _construir_bloque_electrico(
        story, nombre_obra, sub_tit_gen, fecha_rev, snapshot_general, historial,
        ficha, prioridades, metadatos_por_id, metadatos_por_nombre, content_w,
        alto_util=doc.height - 12,
        cierre=cierre,
        avisos_cierre=avisos_cierre,
        componentes=componentes_generales,
        titulo_componentes='Avance por bloque',
        hay_garaje=bool(snapshot_garaje),
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
                    alto_util=doc.height - 12,
                    componentes=_componentes_por_campo(
                        _filtrar_snapshot_sagarde(
                            snap_portal, metadatos_por_nombre), 'floor'),
                    titulo_componentes='Avance por planta',
                )

    # 2b. Página de Garaje, tratada como un bloque más (decision de
    #     Bixente: "quiero el informe igual que para los bloques"). Reusa
    #     el mismo indice de metadatos que vivienda: ya viene del catalogo
    #     completo (incluye los 42 tajos garaje_* desde la Fase 1 de la
    #     ampliacion), asi que los nombres de tajo de garaje resuelven
    #     correctamente sin construir un indice aparte -- verificado antes
    #     de escribir esto, no asumido. Una sola pagina combinada por
    #     ahora (no una por cada garaje fisico): la obra de referencia
    #     (Gernika) solo tiene uno.
    if prioridades_garaje is not None and snapshot_garaje:
        story.append(PageBreak())
        _construir_bloque_electrico(
            story, nombre_obra, "GARAJE", fecha_rev, snapshot_garaje,
            [(fecha_rev, snapshot_garaje)], ficha, prioridades_garaje,
            metadatos_por_id, metadatos_por_nombre, content_w,
            alto_util=doc.height - 12,
            zonas=_zonas_con_nombre(
                prioridades_garaje, ficha, resolver_nombre=False),
        )

    # 2c. Pagina de Zonas especiales (cuarto tecnico/ligero/cubierta de
    #     vivienda), tratada igual que Garaje: un bloque mas, misma funcion
    #     de construccion, mismo indice de metadatos (los tajos garaje_*
    #     reutilizados y los fv_*/cub_* ya estan en el catalogo comun).
    #     snapshot_general de arriba NO se toca: 'snapshot' (vivienda) ya
    #     incluye estas celdas mezcladas desde el modelo de datos (planta
    #     virtual 'zesp'), sumarlas aqui tambien las contaria dos veces.
    if prioridades_zonas_especiales is not None and snapshot_zonas_especiales:
        story.append(PageBreak())
        _construir_bloque_electrico(
            story, nombre_obra, "ZONAS ESPECIALES", fecha_rev,
            snapshot_zonas_especiales,
            [(fecha_rev, snapshot_zonas_especiales)], ficha,
            prioridades_zonas_especiales,
            metadatos_por_id, metadatos_por_nombre, content_w,
            alto_util=doc.height - 12,
            zonas=_zonas_con_nombre(
                prioridades_zonas_especiales, ficha, resolver_nombre=True),
        )

    doc.build(story)
    return output_pdf


def _fecha_ordenable(fecha_ddmmaaaa):
    """Convierte 'DD/MM/AAAA' en algo comparable de verdad.

    Comparar estas fechas como texto plano es un bug real: '09/09/2026' <
    '31/08/2026' alfabeticamente (el '0' inicial gana), aunque sea la mas
    reciente. ``None`` si el texto no es una fecha valida.
    """
    try:
        return datetime.strptime(fecha_ddmmaaaa, '%d/%m/%Y')
    except (TypeError, ValueError):
        return None


def _fecha_base_snapshot(fecha_historial_adaptador, fecha_ficha):
    """Fecha que describe de verdad el snapshot actual de la ficha.

    ``fichas.snapshot_desde_ficha(ficha)`` siempre construye el estado
    ACTUAL de la ficha vaya o no el adaptador. Pero el adaptador puede no
    conocer la revision mas reciente -- p.ej. escrita por
    leer_hoja_marcada.py via HTML o tinta, sin PDF/DOCX que el adaptador
    lea -- y en ese caso su ultima fecha queda desfasada respecto a la
    ficha real. Preferir siempre la mas reciente de las dos, comparando
    fechas de verdad (no texto): la etiqueta debe describir lo que el
    snapshot realmente es.
    """
    ordenable_ficha = _fecha_ordenable(fecha_ficha)
    ordenable_adaptador = _fecha_ordenable(fecha_historial_adaptador)
    if ordenable_ficha and (
            ordenable_adaptador is None or ordenable_ficha > ordenable_adaptador):
        return fecha_ficha
    return fecha_historial_adaptador or fecha_ficha


# ─── Entry Point ──────────────────────────────────────────────────────────
def generar_para_obra(
    nombre_obra: str,
    historial: list | None = None,
    ficha: dict | None = None,
    prioridades: dict | None = None,
    snapshot_garaje: list[dict] | None = None,
    prioridades_garaje: dict | None = None,
    snapshot_zonas_especiales: list[dict] | None = None,
    prioridades_zonas_especiales: dict | None = None,
    cierre: dict | None = None,
    avisos_cierre: list[str] | None = None,
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
                revisiones = ficha.get('revisiones') or []
                fecha_ficha = revisiones[-1].get('fecha') if revisiones else ''
                if historial:
                    fecha_base = _fecha_base_snapshot(
                        historial[-1][0], fecha_ficha)
                    historial[-1] = (fecha_base, snapshot_base)
                else:
                    fecha_base = fecha_ficha
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

    if cierre is None:
        ruta_cierre = carpeta_obra / "cierre_expediente.json"
        cierre, avisos_cierre = cierre_expediente.cargar(str(ruta_cierre), obra=nombre_oficial)
    avisos_cierre = avisos_cierre or []

    print(f"[2/2] Generando PDF Ejecutivo A4 en: {output_pdf}...")
    generar_pdf_ejecutivo(
        nombre_oficial,
        fecha_rev,
        snapshot,
        output_pdf,
        historial=historial,
        ficha=ficha,
        prioridades=prioridades,
        snapshot_garaje=snapshot_garaje,
        prioridades_garaje=prioridades_garaje,
        snapshot_zonas_especiales=snapshot_zonas_especiales,
        prioridades_zonas_especiales=prioridades_zonas_especiales,
        cierre=cierre,
        avisos_cierre=avisos_cierre,
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
