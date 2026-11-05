# -*- coding: utf-8 -*-
"""Pestaña «Viviendas» del panel: cuantas viviendas tienen cada tajo electrico.

El HTML lleva los datos en bruto (``viviendas_tajos.datos_para_panel``) y el
calculo de ``viviendas_calculo.js``: asi «hoy» es el dia real en que se abre la
pagina, y el informe de obra saca exactamente lo que se esta viendo.
"""
import html as html_lib
import json
import os
import re


def _leer_calculo_js():
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'viviendas_calculo.js')
    with open(ruta, encoding='utf-8') as f:
        contenido = f.read().rstrip('\r\n')
    if re.search(r'</script', contenido, flags=re.IGNORECASE) or '<!--' in contenido:
        raise ValueError("viviendas_calculo.js contiene secuencias no permitidas "
                         "('</script' o '<!--').")
    return contenido


_UI = r"""
(function () {
  const C = window.ViviendasCalculo;
  const datos = JSON.parse(document.getElementById('viviendas-datos').textContent);
  const sel = document.getElementById('viv-periodo');
  const desdeIn = document.getElementById('viv-desde');
  const hastaIn = document.getElementById('viv-hasta');
  const cab = document.getElementById('viv-cabecera');
  const cuerpo = document.querySelector('#viv-tabla tbody');
  const notas = document.getElementById('viv-notas');
  const pad = n => String(n).padStart(2, '0');

  function hoyISO() {
    if (window.__HOY_VIVIENDAS) return window.__HOY_VIVIENDAS;
    const d = new Date();
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }
  function fmt(iso) { return iso ? iso.slice(8, 10) + '/' + iso.slice(5, 7) + '/' + iso.slice(0, 4) : '—'; }
  function dias(a, b) {
    const x = a.split('-').map(Number), y = b.split('-').map(Number);
    return Math.round((Date.UTC(y[0], y[1] - 1, y[2]) - Date.UTC(x[0], x[1] - 1, x[2])) / 86400000);
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c])); }

  // Meses con datos (los de las fechas de las viviendas terminadas), del mas reciente al mas antiguo.
  const meses = {};
  Object.keys(datos.celdas).forEach(t => datos.celdas[t].forEach(c => { if (c[1]) meses[c[1].slice(0, 7)] = 1; }));
  Object.keys(meses).sort().reverse().forEach(m => {
    const o = document.createElement('option');
    o.value = 'mes:' + m;
    o.textContent = C.periodoNatural('mes:' + m, hoyISO()).etiqueta;
    sel.insertBefore(o, sel.querySelector('option[value="todo"]'));
  });

  function periodo() {
    if (sel.value === 'rango') {
      return { desde: desdeIn.value || null, hasta: hastaIn.value || null, etiqueta: 'Entre fechas' };
    }
    return C.periodoNatural(sel.value, hoyISO());
  }

  function construir() {
    const p = periodo();
    const hoy = hoyISO();
    let aviso = '';
    if (p.desde && p.hasta && p.desde > p.hasta) {
      return { cab: 'La fecha «desde» es posterior a «hasta».', filas: '', notas: '' };
    }
    const rango = (!p.desde && !p.hasta) ? 'desde el principio'
      : 'del ' + fmt(p.desde) + ' al ' + fmt(p.hasta);
    const rev = datos.ultima_revision
      ? 'Datos de la última revisión de campo: ' + fmt(datos.ultima_revision) +
        (function () { const n = dias(datos.ultima_revision, hoy);
          return n <= 0 ? ' (hoy)' : n === 1 ? ' (hace 1 día)' : ' (hace ' + n + ' días)'; })()
      : 'Sin revisión de campo con fecha registrada';
    const cabecera = p.etiqueta + ' — ' + rango + '. ' + rev + '.';
    let filas = '', sinFecha = 0, dudosas = 0;
    datos.tajos.forEach(t => {
      const r = C.contar(datos, t.id, p.desde, p.hasta);
      sinFecha += r.sin_fecha; dudosas += r.dudosas;
      const pend = r.P + (r['?'] ? ' (+' + r['?'] + ' sin mirar)' : '');
      filas += '<tr data-tajo="' + esc(t.id) + '"><td>' + esc(t.nombre) + '</td>' +
        '<td class="viv-total" style="text-align:right">' + r.total + '</td>' +
        '<td class="viv-x" style="text-align:right"><b>' + r.X + '</b></td>' +
        '<td class="viv-m" style="text-align:right">' + r.M + '</td>' +
        '<td class="viv-b" style="text-align:right">' + r['/'] + '</td>' +
        '<td class="viv-p" style="text-align:right">' + pend + '</td>' +
        '<td class="viv-hechas" style="text-align:right"><b>' + r.hechas + '</b></td>' +
        '<td class="viv-acum" style="text-align:right">' + r.acumuladas + '</td>' +
        '<td class="viv-dudosas" style="text-align:right">' + r.dudosas + '</td></tr>';
    });
    let n = 'Solo viviendas (no locales, trasteros ni garajes); las N y las celdas que no existen no cuentan en el total. ' +
      'M, / y pendientes son los de AHORA: la historia de M y / no se guarda. ' +
      '«Terminadas en el periodo» cuenta las que pasaron a X dentro del periodo según su fecha de revisión de campo.';
    if (dudosas) n += ' ' + dudosas + ' con fecha dudosa (carga de historial) dentro del periodo: no cuentan como hechas.';
    if (sinFecha) n += ' ' + sinFecha + ' terminada(s) sin fecha: no entran en ningún periodo.';
    return { cab: cabecera, filas: filas, notas: n };
  }

  function pintar() {
    document.getElementById('viv-rango').style.display = sel.value === 'rango' ? 'inline' : 'none';
    const r = construir();
    cab.textContent = r.cab;
    cuerpo.innerHTML = r.filas;
    notas.textContent = r.notas;
  }

  const CABECERA = '<thead><tr><th>Tajo</th><th>Viviendas</th><th>X terminadas</th><th>M más del 50 %</th>' +
    '<th>/ iniciadas</th><th>Pendientes</th><th>Terminadas en el periodo</th>' +
    '<th>Terminadas a fin del periodo</th><th>Fecha dudosa</th></tr></thead>';

  // El informe de obra saca EXACTAMENTE lo que se esta viendo.
  window.viviendasHTMLInforme = function () {
    const r = construir();
    return '<div class="card"><h3>Viviendas por tajo eléctrico</h3><p>' + esc(r.cab) + '</p>' +
      '<table class="data">' + CABECERA + '<tbody>' + r.filas + '</tbody></table>' +
      '<p style="font-size:12.5px;color:var(--muted)">' + esc(r.notas) + '</p></div>';
  };

  sel.addEventListener('change', pintar);
  desdeIn.addEventListener('change', pintar);
  hastaIn.addEventListener('change', pintar);
  sel.value = 'mes';
  pintar();
})();
"""


def vista_html(datos):
    """Contenido de la pestaña «Viviendas». ``datos`` es None si no hay."""
    if not datos or not datos.get('tajos'):
        return ("<div class='card'><h3>Viviendas por tajo eléctrico</h3>"
                "<p>Sin datos de viviendas: esta obra no tiene viviendas con "
                "tajos eléctricos en su base.</p></div>")
    datos_json = json.dumps(datos, ensure_ascii=False,
                            separators=(',', ':')).replace('</', '<\\/')
    cabecera = ''.join(
        f'<th>{html_lib.escape(t)}</th>' for t in (
            'Tajo', 'Viviendas', 'X terminadas', 'M más del 50 %',
            '/ iniciadas', 'Pendientes', 'Terminadas en el periodo',
            'Terminadas a fin del periodo', 'Fecha dudosa'))
    return (
        "<div class='card'><h3>Viviendas por tajo eléctrico</h3>"
        "<p id='viv-cabecera' style='font-size:13px;color:var(--muted)'></p>"
        "<div style='display:flex;gap:10px;align-items:center;flex-wrap:wrap;"
        "margin:10px 0'><label><b>Periodo</b> "
        "<select id='viv-periodo'>"
        "<option value='semana'>Esta semana</option>"
        "<option value='semana_pasada'>Semana pasada</option>"
        "<option value='mes'>Este mes</option>"
        "<option value='mes_anterior'>Mes anterior</option>"
        "<option value='todo'>Desde el principio</option>"
        "<option value='rango'>Entre fechas…</option></select></label>"
        "<span id='viv-rango' style='display:none'>"
        "<input type='date' id='viv-desde'> a <input type='date' id='viv-hasta'>"
        "</span></div>"
        f"<div class='table-scroll'><table class='data' id='viv-tabla'><thead><tr>{cabecera}"
        "</tr></thead><tbody></tbody></table></div>"
        "<p id='viv-notas' style='font-size:12.5px;color:var(--muted);margin-top:10px'></p>"
        "</div>"
        f'<script id="viviendas-datos" type="application/json">{datos_json}</script>'
        f"<script>\n(function () {{\n{_leer_calculo_js()}\n}})();\n{_UI}</script>")
