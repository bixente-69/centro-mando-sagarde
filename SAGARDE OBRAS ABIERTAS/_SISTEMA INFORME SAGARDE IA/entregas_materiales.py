# -*- coding: utf-8 -*-
"""
entregas_materiales.py - registro de entregas de material de una obra

ESPECIFICACION (piloto Olabeaga, 20/10/2026; aprobada por Bixente: "opcion A").

Problema que resuelve
  El Excel de materiales era una rejilla (catalogo entero x una columna por
  fecha) sin sitio para suministrador ni albaran, y el panel solo leia su
  ultima hoja. Dos formatos para lo mismo, y una rejilla de 117 filas con
  formulas que se rompio al editarla desde codigo.

Diseno
  * UNA hoja ``ENTREGAS`` por obra, con una fila por linea entregada:
        FECHA | SUMINISTRADOR | ALBARAN | CATEGORIA | MATERIAL | TIPO | MARCA |
        UNI | CANTIDAD | NOTAS
    Es lo UNICO que se escribe (a mano o por agy). Todo lo demas se genera.
  * El panel lee ENTREGAS directamente (``leer_materiales_wb``), asi que
    siempre esta al dia. El Excel lleva ademas una hoja por mes y un
    ACUMULADO, generadas de la misma agrupacion (``construir_hojas``): lo que
    ves en pantalla y en el Excel es el mismo calculo.
  * Cada mes lista SOLO lo entregado ese mes (no repite el catalogo): una
    columna por entrega (fecha + suministrador + albaran), MES ANT, TOTAL MES
    y ACUMULADO.
  * Las hojas generadas llevan solo valores, sin formulas: no existe el
    "total sin calcular" que dejo a Olabeaga fuera del portal.

Reglas de datos (CLAUDE.md: no inventar)
  * Una fila invalida (fecha ilegible, cantidad no numerica o ambigua) queda
    FUERA y se avisa con su numero de fila; nunca se convierte en cero.
  * Suministrador o albaran desconocidos son ``None`` ("sin dato"), no "0".
  * Dos filas identicas se cuentan las dos pero se avisan (entrada doble).
"""
from __future__ import annotations

import html as html_lib
import io
import os
import re
import unicodedata
from datetime import date, datetime

try:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.utils.datetime import from_excel
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:  # el resto del motor ya avisa si falta openpyxl
    openpyxl = None

HOJA_ENTREGAS = 'ENTREGAS'
HOJA_ACUMULADO = 'ACUMULADO'
HOJA_LEEME = 'LEEME'
CABECERA = ['FECHA', 'SUMINISTRADOR', 'ALBARÁN', 'CATEGORÍA', 'MATERIAL',
            'TIPO', 'MARCA', 'UNI', 'CANTIDAD', 'NOTAS']
CAMPOS = ['fecha', 'suministrador', 'albaran', 'categoria', 'material',
          'tipo', 'marca', 'uni', 'cantidad', 'notas']
OBLIGATORIOS = ('fecha', 'material', 'cantidad')
MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
_RE_HOJA_MES = re.compile(r'^(%s)\d{2}$' % '|'.join(MESES))
COMANDO_GENERAR = 'py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py generar <obra>'
MAX_AVISOS_EN_PANEL = 5


# --------------------------------------------------------------- utilidades

def _sin_tildes(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def _norm_cabecera(v) -> str:
    return re.sub(r'[^A-Z0-9 ]', ' ', _sin_tildes(str(v or '')).upper()).strip()


def _campo_de_cabecera(v):
    n = _norm_cabecera(v)
    if not n:
        return None
    if n.startswith('FECHA'):
        return 'fecha'
    if 'SUMINIST' in n or 'PROVEED' in n:
        return 'suministrador'
    if 'ALBARAN' in n:
        return 'albaran'
    if n.startswith('CATEGORIA'):
        return 'categoria'
    if n == 'MATERIAL':
        return 'material'
    if n == 'TIPO':
        return 'tipo'
    if n == 'MARCA':
        return 'marca'
    if n in ('UNI', 'UNIDAD', 'UNIDADES', 'UD', 'UDS'):
        return 'uni'
    if n.startswith('CANT'):
        return 'cantidad'
    if n.startswith('NOTA') or n.startswith('OBSERV'):
        return 'notas'
    return None


def _txt(v):
    """Texto limpio o None. Los numeros salen sin '.0' y con coma decimal."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        if float(v).is_integer():
            return str(int(v))
        return str(v).replace('.', ',')
    s = ' '.join(str(v).split())
    return s or None


def _num(v):
    """int/float limpio. Entero si no tiene decimales; sin ruido de coma flotante."""
    v = round(float(v), 6)
    return int(v) if v.is_integer() else v


def _fecha(v):
    """date o None. Acepta fecha de Excel, texto DD/MM/AAAA, AAAA-MM-DD y serie."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool) and 30000 < v < 80000:
        try:
            return from_excel(v).date()
        except (ValueError, OverflowError):
            return None
    if isinstance(v, str):
        s = v.strip()
        m = re.fullmatch(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})', s)
        if m:
            d, mo, a = map(int, m.groups())
        else:
            m = re.fullmatch(r'(\d{4})-(\d{1,2})-(\d{1,2})', s)
            if not m:
                return None
            a, mo, d = map(int, m.groups())
        try:
            return date(a, mo, d)
        except ValueError:
            return None
    return None


def _cantidad(v):
    """(numero, motivo_de_rechazo). Texto numerico simple vale; '1.200' es
    ambiguo (¿1,2 o 1200?) y se rechaza en vez de adivinar."""
    if isinstance(v, bool) or v is None:
        return None, 'esta vacia'
    if isinstance(v, (int, float)):
        return _num(v), None
    s = str(v).strip()
    if re.fullmatch(r'-?\d+[.,]\d{3}', s):
        return None, f"es ambigua ('{s}': ¿decimales o miles?)"
    if re.fullmatch(r'-?\d+([.,]\d+)?', s):
        return _num(s.replace(',', '.')), None
    return None, f"no es un numero ('{s}')"


def _clave_texto(v) -> str:
    return ' '.join(str(v or '').split()).upper()


def _fmt(n) -> str:
    if n is None:
        return ''
    if float(n).is_integer():
        return f"{int(n):,}".replace(',', '.')
    t = f"{n:,.2f}".rstrip('0').rstrip('.')
    return t.replace(',', '§').replace('.', ',').replace('§', '.')


def etiqueta_mes(f: date) -> str:
    return f"{MESES[f.month - 1]}{f.year % 100:02d}"


def _e(v) -> str:
    return html_lib.escape(str(v))


# ------------------------------------------------------------------- lectura

def leer_registro(wb, hoy: date | None = None):
    """Lee la hoja ENTREGAS de un libro de openpyxl.

    Devuelve ``(entregas, avisos)``. Cada entrega es un dict con ``fila`` (la
    del Excel), ``fecha`` (date), ``suministrador``, ``albaran``, ``categoria``,
    ``material``, ``tipo``, ``marca``, ``uni``, ``cantidad`` y ``notas``.
    """
    hoy = hoy or date.today()
    if HOJA_ENTREGAS not in wb.sheetnames:
        return [], [f"No existe la hoja {HOJA_ENTREGAS}."]
    ws = wb[HOJA_ENTREGAS]
    filas = list(ws.iter_rows(values_only=True))
    if not filas:
        return [], [f"La hoja {HOJA_ENTREGAS} esta vacia (falta la cabecera)."]

    columna = {}
    for i, h in enumerate(filas[0]):
        c = _campo_de_cabecera(h)
        if c and c not in columna:
            columna[c] = i
    faltan = [c.upper() for c in OBLIGATORIOS if c not in columna]
    if faltan:
        return [], [f"En {HOJA_ENTREGAS} falta la columna {', '.join(faltan)} en la fila 1."]

    entregas, avisos, vistas = [], [], {}
    for n, valores in enumerate(filas[1:], start=2):
        def v(campo):
            i = columna.get(campo)
            return valores[i] if i is not None and i < len(valores) else None
        if all(x in (None, '') for x in valores):
            continue
        f = _fecha(v('fecha'))
        if f is None:
            avisos.append(f"{HOJA_ENTREGAS} fila {n}: la fecha no es valida ({v('fecha')!r}); la fila no se cuenta.")
            continue
        material = _txt(v('material'))
        if not material:
            avisos.append(f"{HOJA_ENTREGAS} fila {n}: falta el material; la fila no se cuenta.")
            continue
        cant, motivo = _cantidad(v('cantidad'))
        if motivo:
            avisos.append(f"{HOJA_ENTREGAS} fila {n}: la cantidad {motivo}; la fila no se cuenta.")
            continue
        if cant == 0:
            avisos.append(f"{HOJA_ENTREGAS} fila {n}: cantidad 0; se ignora.")
            continue
        if f > hoy:
            avisos.append(f"{HOJA_ENTREGAS} fila {n}: fecha futura ({f:%d/%m/%Y}); se cuenta igualmente.")
        e = {'fila': n, 'fecha': f, 'suministrador': _txt(v('suministrador')),
             'albaran': _txt(v('albaran')), 'categoria': _txt(v('categoria')),
             'material': material, 'tipo': _txt(v('tipo')), 'marca': _txt(v('marca')),
             'uni': _txt(v('uni')), 'cantidad': cant, 'notas': _txt(v('notas'))}
        firma = (f, _clave_texto(e['albaran']), _clave_texto(e['suministrador']),
                 _clave_texto(e['categoria']), _clave_texto(material), _clave_texto(e['tipo']),
                 _clave_texto(e['marca']), _clave_texto(e['uni']), cant)
        if firma in vistas:
            avisos.append(f"{HOJA_ENTREGAS} filas {vistas[firma]} y {n}: linea repetida (misma fecha, albaran, "
                          "material y cantidad); se cuentan las dos, revisa si es una entrada doble.")
        else:
            vistas[firma] = n
        entregas.append(e)
    return entregas, avisos


# ---------------------------------------------------------------- agrupacion

def agrupar(entregas):
    """Agrupa las entregas por mes. Ver la ESPECIFICACION del modulo."""
    ent = sorted(entregas, key=lambda e: (e['fecha'], e.get('fila', 0)))

    def clave(e):
        return (_clave_texto(e['categoria']), _clave_texto(e['material']), _clave_texto(e['tipo']),
                _clave_texto(e['marca']), _clave_texto(e['uni']))

    # Orden de aparicion (cronologico): categorias y, dentro de cada una, materiales.
    visto, orden_cat, nombre = {}, {}, {}
    for e in ent:
        k = clave(e)
        if k not in visto:
            visto[k] = len(visto)
            nombre[k] = {'categoria': e['categoria'], 'material': e['material'], 'tipo': e['tipo'],
                         'marca': e['marca'], 'uni': e['uni']}
        orden_cat.setdefault(k[0], len(orden_cat))

    def orden_fila(k):
        return (orden_cat[k[0]], visto[k])

    meses_claves = sorted({(e['fecha'].year, e['fecha'].month) for e in ent})
    previo = {}          # clave -> cantidad acumulada de meses anteriores
    meses = []
    for (anio, mes) in meses_claves:
        delmes = [e for e in ent if (e['fecha'].year, e['fecha'].month) == (anio, mes)]
        cols = sorted({(e['fecha'], e['suministrador'], e['albaran']) for e in delmes},
                      key=lambda c: (c[0], c[1] or '', c[2] or ''))
        filas = {}
        for e in delmes:
            k = clave(e)
            fila = filas.setdefault(k, [None] * len(cols))
            i = cols.index((e['fecha'], e['suministrador'], e['albaran']))
            fila[i] = (fila[i] or 0) + e['cantidad']
        salida = []
        for k in sorted(filas, key=orden_fila):
            cant = [None if x is None else _num(x) for x in filas[k]]
            total = _num(sum(x for x in cant if x is not None))
            ant = _num(previo.get(k, 0))
            salida.append(dict(nombre[k], cantidades=cant, mes_ant=ant, total_mes=total,
                               acumulado=_num(ant + total)))
        for k, cant in filas.items():
            previo[k] = previo.get(k, 0) + sum(x for x in cant if x is not None)
        meses.append({'etiqueta': etiqueta_mes(date(anio, mes, 1)), 'anio': anio, 'mes': mes,
                      'columnas': [{'fecha': c[0], 'suministrador': c[1], 'albaran': c[2]} for c in cols],
                      'filas': salida})

    etiquetas = [m['etiqueta'] for m in meses]
    acum = []
    for k in sorted(previo, key=orden_fila):
        por_mes = []
        for m in meses:
            f = next((x for x in m['filas'] if _clave_texto(x['categoria']) == k[0]
                      and _clave_texto(x['material']) == k[1] and _clave_texto(x['tipo']) == k[2]
                      and _clave_texto(x['marca']) == k[3] and _clave_texto(x['uni']) == k[4]), None)
            por_mes.append(f['total_mes'] if f else None)
        acum.append(dict(nombre[k], por_mes=por_mes, total=_num(previo[k])))
    return {'meses': meses,
            'acumulado': {'meses': etiquetas, 'filas': acum},
            'ultima_fecha': ent[-1]['fecha'] if ent else None,
            'n_entregas': len(ent)}


def leer_materiales_wb(wb, hoy: date | None = None) -> dict:
    """Mismo diccionario que ``lectores.leer_materiales`` (los consumidores de
    siempre no cambian) mas ``detalle`` y ``formato`` para la vista nueva."""
    hoy = hoy or date.today()
    ent, avisos = leer_registro(wb, hoy)
    g = agrupar(ent)
    res = {'disponible': True, 'meses': g['acumulado']['meses'],
           'ultimo_mes': g['meses'][-1]['etiqueta'] if g['meses'] else None,
           'ultima_fecha': g['ultima_fecha'].strftime('%d/%m/%Y') if g['ultima_fecha'] else None,
           'dias_desde': (hoy - g['ultima_fecha']).days if g['ultima_fecha'] else None,
           'items': [{'categoria': f['categoria'] or '', 'material': f['material'],
                      'tipo': f['tipo'] or '', 'uni': f['uni'] or '', 'total': f['total']}
                     for f in g['acumulado']['filas']],
           'aviso': None, 'formato': 'entregas', 'detalle': g, 'avisos_registro': avisos}
    textos = []
    if avisos:
        textos.append(' · '.join(avisos[:MAX_AVISOS_EN_PANEL])
                      + (f" (+{len(avisos) - MAX_AVISOS_EN_PANEL} mas)" if len(avisos) > MAX_AVISOS_EN_PANEL else ''))
    if res['dias_desde'] is not None and res['dias_desde'] > 30:
        textos.append(f"No hay entregas registradas desde {res['ultima_fecha']} ({res['dias_desde']} dias). "
                      "Los datos de consumo/stock pueden estar desfasados.")
    res['aviso'] = ' '.join(textos) or None
    return res


# ----------------------------------------------------------------------- HTML

def _celda_sin_dato(v):
    return _e(v) if v else '<span style="color:var(--muted)" title="sin dato">—</span>'


def render_html(res: dict) -> str:
    """HTML de la pestana Materiales. Sin JavaScript ni estilos propios: el
    mismo bloque se incrusta en el informe de obra a la carta."""
    g = res.get('detalle') or {}
    meses = g.get('meses') or []
    if not meses:
        return ('<div class="card"><h3>Materiales</h3><p class="empty">Todavia no hay entregas '
                f'registradas en la hoja {HOJA_ENTREGAS}.</p></div>')
    der = 'style="text-align:right;"'
    sub = 'style="text-transform:none;font-weight:600;color:var(--text);font-size:12px;"'
    cat_style = "style='font-weight:700;color:var(--header2);background:#f4f6f9;'"
    out = []
    for m in reversed(meses):
        cols = m['columnas']
        n_cols = 4 + len(cols) + 2
        cab = ''.join(f'<th {der}>{c["fecha"]:%d/%m}</th>' for c in cols)
        sumi = ''.join(f'<th {der} {sub}>{_celda_sin_dato(c["suministrador"])}</th>' for c in cols)
        alb = ''.join(f'<th {der} {sub}>{_celda_sin_dato(c["albaran"])}</th>' for c in cols)
        cuerpo, cat = [], object()
        for f in m['filas']:
            if f['categoria'] != cat:
                cat = f['categoria']
                if cat:
                    cuerpo.append(f'<tr><td colspan="{n_cols}" {cat_style}>{_e(cat)}</td></tr>')
            tipo = ' · '.join(x for x in (f['tipo'], f['marca']) if x)
            celdas = ''.join(f'<td {der}>{_fmt(c)}</td>' for c in f['cantidades'])
            ant = _fmt(f['mes_ant']) if f['mes_ant'] else ''
            cuerpo.append(
                f'<tr><td>{_e(f["material"])}</td><td>{_e(tipo)}</td><td>{_e(f["uni"] or "")}</td>'
                f'<td {der}>{ant}</td>{celdas}<td {der}><b>{_fmt(f["total_mes"])}</b></td>'
                f'<td {der}>{_fmt(f["acumulado"])}</td></tr>')
        n_ent = len(cols)
        out.append(
            f'<div class="card"><h3>{_e(m["etiqueta"])} — material entregado</h3>'
            f'<p style="font-size:12.5px;color:var(--muted);margin-bottom:10px;">'
            f'{len(m["filas"])} material(es) · {n_ent} entrega(s). Cantidades <b>entregadas</b> '
            'según el registro de entregas; no equivalen necesariamente a material instalado.</p>'
            '<div style="overflow-x:auto;"><table class="data"><thead>'
            f'<tr><th>Material</th><th>Tipo</th><th>Uni</th><th {der}>Mes ant.</th>{cab}'
            f'<th {der}>Total mes</th><th {der}>Acumulado</th></tr>'
            f'<tr><th colspan="4" {sub}>Suministrador</th>{sumi}<th></th><th></th></tr>'
            f'<tr><th colspan="4" {sub}>Albarán</th>{alb}<th></th><th></th></tr>'
            f'</thead><tbody>{"".join(cuerpo)}</tbody></table></div></div>')

    ac = g['acumulado']
    cab = ''.join(f'<th {der}>{_e(x)}</th>' for x in ac['meses'])
    cuerpo, cat = [], object()
    for f in ac['filas']:
        if f['categoria'] != cat:
            cat = f['categoria']
            if cat:
                cuerpo.append(f'<tr><td colspan="{4 + len(ac["meses"])}" {cat_style}>{_e(cat)}</td></tr>')
        tipo = ' · '.join(x for x in (f['tipo'], f['marca']) if x)
        celdas = ''.join(f'<td {der}>{_fmt(c)}</td>' for c in f['por_mes'])
        cuerpo.append(f'<tr><td>{_e(f["material"])}</td><td>{_e(tipo)}</td><td>{_e(f["uni"] or "")}</td>'
                      f'{celdas}<td {der}><b>{_fmt(f["total"])}</b></td></tr>')
    ultima = g['ultima_fecha'].strftime('%d/%m/%Y') if g.get('ultima_fecha') else '—'
    out.append(
        '<div class="card"><h3>Acumulado de material entregado</h3>'
        f'<p style="font-size:12.5px;color:var(--muted);margin-bottom:10px;">{g["n_entregas"]} línea(s) '
        f'de entrega · última entrega {ultima}.</p>'
        '<div style="overflow-x:auto;"><table class="data"><thead>'
        f'<tr><th>Material</th><th>Tipo</th><th>Uni</th>{cab}<th {der}>Total</th></tr></thead>'
        f'<tbody>{"".join(cuerpo)}</tbody></table></div></div>')
    return '\n'.join(out)


# ----------------------------------------------------------------- Excel

_AZUL = PatternFill('solid', fgColor='0B1F3A') if openpyxl else None
_GRIS = PatternFill('solid', fgColor='E8EDF4') if openpyxl else None
_NOTA = ("Hoja GENERADA automaticamente desde ENTREGAS: no la edites aqui (se sobrescribe). "
         "Anade las filas en ENTREGAS y ejecuta: " + COMANDO_GENERAR)


def _cabecera_estilo(ws, fila, n):
    for c in range(1, n + 1):
        celda = ws.cell(fila, c)
        celda.fill, celda.font = _AZUL, Font(bold=True, color='FFFFFF')
        celda.alignment = Alignment(horizontal='center' if c > 4 else 'left', vertical='center', wrap_text=True)


def _anchos(ws, anchos):
    for i, a in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = a


def _fila_categoria(ws, fila, texto, n):
    ws.cell(fila, 1, texto)
    for c in range(1, n + 1):
        ws.cell(fila, c).fill = _GRIS
        ws.cell(fila, c).font = Font(bold=True)


def _hoja_mes(wb, m):
    ws = wb.create_sheet(m['etiqueta'])
    cols = m['columnas']
    n = 5 + len(cols) + 2
    ws.append(['MATERIAL', 'TIPO', 'MARCA', 'UNI', 'MES ANT']
              + [datetime(c['fecha'].year, c['fecha'].month, c['fecha'].day) for c in cols]
              + ['TOTAL MES', 'ACUMULADO'])
    ws.append(['Suministrador', None, None, None, None] + [c['suministrador'] for c in cols] + [None, None])
    ws.append(['Albarán', None, None, None, None] + [c['albaran'] for c in cols] + [None, None])
    _cabecera_estilo(ws, 1, n)
    for r in (2, 3):
        for c in range(1, n + 1):
            ws.cell(r, c).font = Font(bold=(c == 1), italic=(c > 1))
            ws.cell(r, c).alignment = Alignment(horizontal='center' if c > 4 else 'left', wrap_text=True)
    for c in range(6, 6 + len(cols)):
        ws.cell(1, c).number_format = 'DD/MM/YYYY'
    cat = object()
    for f in m['filas']:
        if f['categoria'] != cat:
            cat = f['categoria']
            if cat:
                _fila_categoria(ws, ws.max_row + 1, cat, n)
        ws.append([f['material'], f['tipo'], f['marca'], f['uni'], f['mes_ant'] or None]
                  + f['cantidades'] + [f['total_mes'], f['acumulado']])
        ws.cell(ws.max_row, n - 1).font = Font(bold=True)
    ws.cell(ws.max_row + 2, 1, _NOTA).font = Font(italic=True, color='647184')
    _anchos(ws, [34, 22, 14, 8, 9] + [13] * len(cols) + [11, 12])
    ws.freeze_panes = 'E4'
    return ws


def _hoja_acumulado(wb, ac):
    ws = wb.create_sheet(HOJA_ACUMULADO)
    n = 4 + len(ac['meses']) + 1
    ws.append(['MATERIAL', 'TIPO', 'MARCA', 'UNI'] + ac['meses'] + ['TOTAL'])
    _cabecera_estilo(ws, 1, n)
    cat = object()
    for f in ac['filas']:
        if f['categoria'] != cat:
            cat = f['categoria']
            if cat:
                _fila_categoria(ws, ws.max_row + 1, cat, n)
        ws.append([f['material'], f['tipo'], f['marca'], f['uni']] + f['por_mes'] + [f['total']])
        ws.cell(ws.max_row, n).font = Font(bold=True)
    ws.cell(ws.max_row + 2, 1, _NOTA).font = Font(italic=True, color='647184')
    _anchos(ws, [34, 22, 14, 8] + [12] * len(ac['meses']) + [12])
    ws.freeze_panes = 'E2'
    return ws


def _hoja_leeme(wb):
    ws = wb.create_sheet(HOJA_LEEME)
    lineas = [
        ("COMO USAR ESTE LIBRO", True),
        ("Para anadir material entregado: anade UNA FILA por linea al final de la hoja ENTREGAS "
         "(fecha, suministrador, albaran, categoria, material, tipo, marca, uni, cantidad).", False),
        ("Las hojas de cada mes y ACUMULADO se GENERAN a partir de ENTREGAS: no se editan a mano.", False),
        ("Despues de anadir filas ejecuta (desde la raiz del repositorio):", False),
        (COMANDO_GENERAR.replace('<obra>', 'olabeaga'), False),
        ("Si no sabes el suministrador o el albaran, dejalo vacio: no se inventa.", False),
        ("Una fila con fecha ilegible o cantidad no numerica NO se cuenta y se avisa en el panel.", False),
        ("El panel lee ENTREGAS directamente: siempre esta al dia aunque no hayas regenerado el Excel.", False),
    ]
    for i, (t, negrita) in enumerate(lineas, start=1):
        ws.cell(i, 1, t).font = Font(bold=negrita)
    ws.column_dimensions['A'].width = 120
    return ws


def _hoja_entregas(wb, entregas):
    ws = wb.active if wb.sheetnames == ['Sheet'] else wb.create_sheet(HOJA_ENTREGAS, 0)
    ws.title = HOJA_ENTREGAS
    ws.append(CABECERA)
    _cabecera_estilo(ws, 1, len(CABECERA))
    for e in entregas:
        ws.append([datetime(e['fecha'].year, e['fecha'].month, e['fecha'].day), e.get('suministrador'),
                   e.get('albaran'), e.get('categoria'), e['material'], e.get('tipo'), e.get('marca'),
                   e.get('uni'), e['cantidad'], e.get('notas')])
    for fila in ws.iter_rows(min_row=2, max_col=1):
        fila[0].number_format = 'DD/MM/YYYY'
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(CABECERA))}{max(ws.max_row, 2)}"
    _anchos(ws, [12, 22, 14, 22, 30, 24, 14, 8, 11, 30])
    fechas = DataValidation(type='date', operator='greaterThan', formula1='36526', allow_blank=True,
                            showErrorMessage=True, errorTitle='Fecha', error='Escribe una fecha valida (DD/MM/AAAA).')
    cant = DataValidation(type='decimal', operator='notEqual', formula1='0', allow_blank=True,
                          showErrorMessage=True, errorTitle='Cantidad', error='La cantidad debe ser un numero distinto de 0.')
    ws.add_data_validation(fechas)
    ws.add_data_validation(cant)
    fechas.add('A2:A5000')
    cant.add('I2:I5000')
    return ws


def construir_hojas(wb, entregas) -> dict:
    """Borra las hojas generadas (meses y ACUMULADO) y las rehace desde las
    entregas. No toca ENTREGAS ni ninguna hoja ajena. Devuelve la agrupacion."""
    for nombre in list(wb.sheetnames):
        if _RE_HOJA_MES.match(nombre) or nombre == HOJA_ACUMULADO:
            del wb[nombre]
    g = agrupar(entregas)
    for m in g['meses']:
        _hoja_mes(wb, m)
    _hoja_acumulado(wb, g['acumulado'])
    if HOJA_LEEME not in wb.sheetnames:
        _hoja_leeme(wb)
    orden = {nombre: (1, i) for i, nombre in enumerate(m['etiqueta'] for m in g['meses'])}

    def pos(ws):
        if ws.title == HOJA_ENTREGAS:
            return (0, 0)
        if ws.title in orden:
            return (1,) + orden[ws.title][1:]
        if ws.title == HOJA_ACUMULADO:
            return (2, 0)
        if ws.title == HOJA_LEEME:
            return (3, 0)
        return (4, 0)
    wb._sheets.sort(key=pos)
    wb.active = 0
    return g


def _guardar(wb, ruta):
    tmp = ruta + '.generando.tmp'
    wb.save(tmp)
    os.replace(tmp, ruta)


def crear_libro(entregas, ruta):
    """Crea el libro completo (ENTREGAS + meses + ACUMULADO + LEEME)."""
    wb = openpyxl.Workbook()
    _hoja_entregas(wb, entregas)
    construir_hojas(wb, entregas)
    _guardar(wb, ruta)


def _abrir(ruta, data_only=False):
    with open(ruta, 'rb') as f:        # desde memoria: no deja el fichero retenido (Windows)
        return openpyxl.load_workbook(io.BytesIO(f.read()), data_only=data_only)


def regenerar_hojas(ruta, hoy: date | None = None):
    """Rehace las hojas generadas de un libro existente. Devuelve los avisos."""
    wb = _abrir(ruta)
    entregas, avisos = leer_registro(wb, hoy)
    construir_hojas(wb, entregas)
    _guardar(wb, ruta)
    return avisos


def _grid_recortado(ws):
    filas = [list(r) for r in ws.iter_rows(values_only=True)]
    while filas and all(x is None for x in filas[-1]):
        filas.pop()
    ancho = max((max((i for i, x in enumerate(r) if x is not None), default=-1) + 1 for r in filas), default=0)
    return [r[:ancho] + [None] * (ancho - len(r[:ancho])) for r in filas]


def hojas_desactualizadas(wb) -> list[str]:
    """Compara las hojas generadas del libro con las que saldrian hoy de ENTREGAS."""
    entregas, _ = leer_registro(wb)
    esperado = openpyxl.Workbook()
    esperado.remove(esperado.active)
    construir_hojas(esperado, entregas)
    problemas = []
    nombres_esperados = [n for n in esperado.sheetnames if n != HOJA_LEEME]
    for n in nombres_esperados:
        if n not in wb.sheetnames:
            problemas.append(f"falta la hoja {n}")
        elif _grid_recortado(wb[n]) != _grid_recortado(esperado[n]):
            problemas.append(f"la hoja {n} no coincide con ENTREGAS")
    for n in wb.sheetnames:
        if (_RE_HOJA_MES.match(n) or n == HOJA_ACUMULADO) and n not in nombres_esperados:
            problemas.append(f"sobra la hoja {n}")
    return problemas


# --------------------------------------------------------------- migracion

def entregas_desde_rejilla(wb) -> list[dict]:
    """Convierte la rejilla antigua (catalogo x fechas) en filas de entrega.
    Solo cuentan las columnas con fecha: MES ANT y TOTAL son arrastres/derivados
    y no se migran. Suministrador y albaran quedan sin dato (no existian)."""
    entregas = []
    for ws in wb.worksheets:
        filas = list(ws.iter_rows(values_only=True))
        if not filas:
            continue
        fechas = {i: _fecha(h) for i, h in enumerate(filas[0]) if isinstance(h, (datetime, date))}
        if not fechas:
            continue
        cat = None
        for fila in filas[1:]:
            nombre = fila[0] if fila else None
            if not isinstance(nombre, str) or not nombre.strip():
                continue
            cantidades = [(i, fila[i]) for i in fechas
                          if i < len(fila) and isinstance(fila[i], (int, float))
                          and not isinstance(fila[i], bool) and fila[i]]
            tipo = fila[1] if len(fila) > 1 else None
            if not cantidades and tipo in (None, ''):
                cat = nombre.strip()
                continue
            for i, c in cantidades:
                entregas.append({'fila': len(entregas) + 2, 'fecha': fechas[i], 'suministrador': None,
                                 'albaran': None, 'categoria': cat, 'material': ' '.join(nombre.split()),
                                 'tipo': _txt(tipo), 'marca': _txt(fila[2] if len(fila) > 2 else None),
                                 'uni': _txt(fila[3] if len(fila) > 3 else None), 'cantidad': _num(c),
                                 'notas': None})
    entregas.sort(key=lambda e: e['fecha'])      # estable: conserva el orden del catalogo dentro de cada dia
    for n, e in enumerate(entregas, start=2):
        e['fila'] = n
    return entregas
