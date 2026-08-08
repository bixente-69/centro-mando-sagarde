# -*- coding: utf-8 -*-
"""
generar_informe_ejecutivo.py — Generador de Informes Ejecutivos A4 de Obra

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

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image, KeepTogether, PageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# _SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py -> cuatro niveles.
ROOT = Path(__file__).resolve().parent.parent.parent.parent
OBRAS_DIR = ROOT / "SAGARDE OBRAS ABIERTAS"
MOTOR_IA_DIR = OBRAS_DIR / "_SISTEMA INFORME SAGARDE IA"
ASSETS_DIR = ROOT / "_SISTEMA" / "MOTOR" / "assets"
LOGO_PATH = ASSETS_DIR / "logo_sagarde.jpg"

if str(MOTOR_IA_DIR) not in sys.path:
    sys.path.append(str(MOTOR_IA_DIR))

import motor_informes
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
def generar_pdf_ejecutivo(nombre_obra: str, fecha_rev: str, snapshot: list[dict], output_pdf: Path, historial: list | None = None) -> Path:
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
    _construir_bloque_ejecutivo(story, nombre_obra, sub_tit_gen, fecha_rev, snapshot, content_w)

    # 2. Páginas Desglosadas por Bloque / Portal (si hay 2 o más subdivisiones)
    if len(portal_items) >= 2:
        for ref, lbl, p_nom in portal_items:
            snap_portal = [r for r in snapshot if r.get('building') == ref or r.get('building') == p_nom]
            if snap_portal:
                story.append(PageBreak())
                _construir_bloque_ejecutivo(story, nombre_obra, lbl, fecha_rev, snap_portal, content_w)

    doc.build(story)
    return output_pdf


# ─── Entry Point ──────────────────────────────────────────────────────────
def generar_para_obra(
    nombre_obra: str,
    historial: list | None = None,
) -> Path | None:
    obra = resolver_obra(nombre_obra)
    if obra is None:
        print(f"[ERROR] No hay obra registrada con el nombre '{nombre_obra}'.")
        return None
    nombre_oficial = obra['nombre']

    if historial is None:
        adaptador = ADAPTADORES[nombre_oficial]
        print(f"[1/2] Cargando historial de revisiones para '{nombre_oficial}'...")
        historial = adaptador.cargar_historial()
    else:
        print(f"[1/2] Usando el historial validado por la ficha para '{nombre_oficial}'...")

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
