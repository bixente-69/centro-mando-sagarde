"""
generar_parte_incidencia.py — Generador unificado de partes de incidencia Sagarde

Tipos soportados:
    postventa   → INCIDENCIA POST-VENTA
    preventivo  → INCIDENCIA PREVENTIVA
    correctivo  → INCIDENCIA CORRECTIVA

Estructura de cada incidencia (dict):
    {
        "tipo":           str,   # "postventa" | "preventivo" | "correctivo"
        "codigo":         str,   # Nº incidencia Sagarde (ej: AGI20251103483)
        "naturaleza":     str,   # Categoría (ej: Puertas metálicas)
        "direccion":      str,   # Nombre de obra / dirección
        "portal":         str,   # Portal (ej: Portal 02) — vacío si no aplica
        "piso":           str,   # Puerta / piso / zona (ej: Puerta E)
        "ubicacion":      str,   # Jardín / Entrada / Vivienda / Cuadro general...
        "cliente":        str,   # Nombre completo del cliente / contacto
        "telefono":       str,   # Teléfono(s) de contacto
        "fecha_aviso":    str,   # Fecha/período del aviso (ej: Nov-2025)
        "fecha_realizacion": str,  # Fecha de la visita (hoy por defecto)
        "cita_hoy":       str,   # Cita o estado (ej: CITA: 10:15 h)
        "descripcion":    str,   # Descripción de la incidencia
        "observaciones":  str,   # Observaciones de reparación (puede ser "")
    }
"""

import os
import json
import argparse

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, PageBreak, Image,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ─── Identidad visual Sagarde ──────────────────────────────────────────────
PAGE_W, PAGE_H = A4
MARGIN = 15 * mm

COL_DARK  = colors.HexColor('#1A3558')
COL_MID   = colors.HexColor('#2E6DA4')
COL_LIGHT = colors.HexColor('#D9E8F5')
COL_WARN  = colors.HexColor('#C0392B')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH  = os.path.join(SCRIPT_DIR, '..', 'assets', 'logo_sagarde.jpg')

TITULOS = {
    'postventa':  'INCIDENCIA POST-VENTA',
    'preventivo': 'INCIDENCIA PREVENTIVA',
    'correctivo': 'INCIDENCIA CORRECTIVA',
}

# ─── Estilos tipográficos ──────────────────────────────────────────────────
def _ps(name, size, bold=False, align=TA_LEFT, color=colors.black):
    return ParagraphStyle(
        name, fontSize=size, leading=size * 1.35,
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        alignment=align, textColor=color,
    )

LABEL_S  = _ps('label',  9, bold=True)
VALUE_S  = _ps('value', 11)
VALUE_SM = _ps('vsm',   10)
HEADER_S = _ps('hdr',   15, bold=True, align=TA_CENTER, color=colors.white)
DNI_S    = _ps('dni',    7, align=TA_RIGHT, color=colors.grey)


# ─── Helpers de layout ─────────────────────────────────────────────────────
def _row(pairs, col_widths):
    row = []
    for lbl, val in pairs:
        v_style = VALUE_S if len(val) < 55 else VALUE_SM
        row.append([Paragraph(lbl, LABEL_S), Paragraph(val, v_style)])
    tbl = Table([row], colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.5, COL_MID),
        ('INNERGRID',     (0, 0), (-1, -1), 0.3, COL_MID),
        ('BACKGROUND',    (0, 0), (-1, -1), COL_LIGHT),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return tbl


def _big_cell(label, content, width, height=24 * mm):
    data = [
        [Paragraph(label, LABEL_S)],
        [Paragraph(content, _ps('bc', 10, leading=14))],
    ]
    tbl = Table(data, colWidths=[width], rowHeights=[7 * mm, height])
    tbl.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.5, COL_MID),
        ('BACKGROUND',    (0, 0), (0,  0),  COL_DARK),
        ('TEXTCOLOR',     (0, 0), (0,  0),  colors.white),
        ('BACKGROUND',    (0, 1), (0,  1),  colors.white),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    return tbl


# ─── Constructor de un parte ───────────────────────────────────────────────
def _build_parte(inc: dict) -> list:
    W   = PAGE_W - 2 * MARGIN
    GAP = Spacer(1, 2.5 * mm)

    tipo   = inc.get('tipo', 'postventa').lower()
    titulo = TITULOS.get(tipo, 'INCIDENCIA')

    elems = []

    # Cabecera: logo izquierda | título derecha
    logo_img = Image(LOGO_PATH, width=52 * mm, height=13.6 * mm)
    hdr_tbl  = Table(
        [[logo_img, Paragraph(titulo, HEADER_S)]],
        colWidths=[W * 0.32, W * 0.68],
    )
    hdr_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (0, 0), colors.white),
        ('BACKGROUND',    (1, 0), (1, 0), COL_DARK),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (0,  0), 4),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BOX',           (0, 0), (-1, -1), 0.5, COL_MID),
    ]))
    elems += [hdr_tbl, GAP]

    elems += [_row([("CÓDIGO SAGARDE",  inc.get('codigo', '')),
                    ("NATURALEZA",      inc.get('naturaleza', ''))],
                   [W * 0.55, W * 0.45]), GAP]

    elems += [_row([("DIRECCIÓN (OBRA):", inc.get('direccion', '')),
                    ("PORTAL:",           inc.get('portal', ''))],
                   [W * 0.65, W * 0.35]), GAP]

    elems += [_row([("PISO / MANO (PUERTA):", inc.get('piso', '')),
                    ("UBICACIÓN:",            inc.get('ubicacion', ''))],
                   [W * 0.55, W * 0.45]), GAP]

    elems += [_row([("CLIENTE:",             inc.get('cliente', '')),
                    ("TELÉFONO CONTACTO:",   inc.get('telefono', ''))],
                   [W * 0.60, W * 0.40]), GAP]

    elems += [_row([("FECHA AVISO:",          inc.get('fecha_aviso', '')),
                    ("FECHA DE REALIZACIÓN:", inc.get('fecha_realizacion', ''))],
                   [W * 0.50, W * 0.50]), GAP]

    cita_txt = inc.get('cita_hoy', '')
    is_warn  = any(w in cita_txt for w in ('⚠', 'SIN CITA', 'NO PUEDE'))
    cita_ps  = _ps('cita', 11, bold=True, color=COL_WARN if is_warn else COL_DARK)
    cita_tbl = Table(
        [[Paragraph("CITA HOY:", LABEL_S), Paragraph(cita_txt, cita_ps)]],
        colWidths=[W * 0.25, W * 0.75],
    )
    cita_tbl.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.5, COL_MID),
        ('INNERGRID',     (0, 0), (-1, -1), 0.3, COL_MID),
        ('BACKGROUND',    (0, 0), (-1, -1), COL_LIGHT),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elems += [cita_tbl, GAP]

    elems += [_big_cell("DESCRIPCIÓN DE LA INCIDENCIA:",
                        inc.get('descripcion', ' '), W), GAP]
    elems += [_big_cell("OBSERVACIONES DE LA REPARACIÓN:",
                        inc.get('observaciones', ' ') or ' ', W), GAP]

    firma_tbl = Table(
        [[Paragraph("FIRMA DEL CLIENTE:", LABEL_S),
          Paragraph("FIRMA DEL INSTALADOR:", LABEL_S)]],
        colWidths=[W * 0.50, W * 0.50],
        rowHeights=[24 * mm],
    )
    firma_tbl.setStyle(TableStyle([
        ('BOX',          (0, 0), (-1, -1), 0.5, COL_MID),
        ('INNERGRID',    (0, 0), (-1, -1), 0.5, COL_MID),
        ('BACKGROUND',   (0, 0), (-1, -1), colors.white),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 5),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
    ]))
    elems.append(firma_tbl)
    elems.append(Spacer(1, 1 * mm))
    elems.append(Paragraph("D.N.I. / Fecha / Firma", DNI_S))

    return elems


# ─── Función principal exportable ─────────────────────────────────────────
def generar_pdf(incidents: list, output_path: str) -> str:
    """
    Genera un PDF con un parte por página.

    Args:
        incidents:   lista de dicts (ver estructura al inicio del módulo)
        output_path: ruta de salida del PDF

    Returns:
        output_path confirmado
    """
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
    )
    story = []
    for i, inc in enumerate(incidents):
        story.extend(_build_parte(inc))
        if i < len(incidents) - 1:
            story.append(PageBreak())
    doc.build(story)
    return output_path


# ─── CLI ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Genera partes de incidencia Sagarde (post-venta / preventivo / correctivo)'
    )
    parser.add_argument('--data',   required=True, help='JSON con lista de incidencias')
    parser.add_argument('--output', required=True, help='Ruta del PDF de salida')
    args = parser.parse_args()

    with open(args.data, encoding='utf-8') as f:
        data = json.load(f)

    print(f'PDF generado: {generar_pdf(data, args.output)}')
