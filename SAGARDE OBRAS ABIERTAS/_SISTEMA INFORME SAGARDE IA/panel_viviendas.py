# -*- coding: utf-8 -*-
"""Pestaña «Viviendas» del panel: cuantas viviendas tienen cada tajo electrico.

El HTML lleva los datos en bruto (``viviendas_tajos.datos_para_panel``) y el
calculo de ``viviendas_calculo.js``: asi «hoy» es el dia real en que se abre la
pagina, y el informe de obra saca exactamente lo que se esta viendo.

Los controles (periodo y tajos que salen) existen DOS veces, en la pestaña y
en el selector del informe de obra, y comparten un unico estado: cambiar uno
cambia el otro, asi que el informe lleva siempre lo que se ve en la pestaña.
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
  const cab = document.getElementById('viv-cabecera');
  const cuerpo = document.querySelector('#viv-tabla tbody');
  const notas = document.getElementById('viv-notas');
  const raices = Array.prototype.slice.call(document.querySelectorAll('.viv-controles'));
  const pad = n => String(n).padStart(2, '0');
  // UNICO estado: la pestaña y el informe de obra lo comparten.
  const estado = { periodo: 'mes', desde: '', hasta: '',
    tajos: new Set(datos.tajos.map(t => t.id)) };

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

  // Meses con datos (los de las fechas de las viviendas), del mas reciente al mas antiguo.
  const meses = {};
  Object.keys(datos.celdas).forEach(t => datos.celdas[t].forEach(c => { if (c[1]) meses[c[1].slice(0, 7)] = 1; }));
  const listaMeses = Object.keys(meses).sort().reverse();
  raices.forEach(r => {
    const sel = r.querySelector('.viv-sel');
    listaMeses.forEach(m => {
      const o = document.createElement('option');
      o.value = 'mes:' + m;
      o.textContent = C.periodoNatural('mes:' + m, hoyISO()).etiqueta;
      sel.insertBefore(o, sel.querySelector('option[value="todo"]'));
    });
  });

  function periodo() {
    if (estado.periodo === 'rango') {
      return { desde: estado.desde || null, hasta: estado.hasta || null, etiqueta: 'Entre fechas' };
    }
    return C.periodoNatural(estado.periodo, hoyISO());
  }

  function construir() {
    const tajos = datos.tajos.filter(t => estado.tajos.has(t.id));
    if (!tajos.length) return { cab: 'Elige al menos un tajo.', filas: '', notas: '' };
    const p = periodo();
    const hoy = hoyISO();
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
    tajos.forEach(t => {
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

  function pintarControles() {
    raices.forEach(r => {
      r.querySelector('.viv-sel').value = estado.periodo;
      r.querySelector('.viv-desde').value = estado.desde;
      r.querySelector('.viv-hasta').value = estado.hasta;
      r.querySelector('.viv-rango').style.display = estado.periodo === 'rango' ? 'inline' : 'none';
      r.querySelectorAll('input[data-tajo]').forEach(cb => { cb.checked = estado.tajos.has(cb.dataset.tajo); });
    });
  }
  function pintar() {
    pintarControles();
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
      (r.filas ? '<table class="data">' + CABECERA + '<tbody>' + r.filas + '</tbody></table>' : '') +
      '<p style="font-size:12.5px;color:var(--muted)">' + esc(r.notas) + '</p></div>';
  };

  raices.forEach(r => {
    r.querySelector('.viv-sel').addEventListener('change', e => { estado.periodo = e.target.value; pintar(); });
    r.querySelector('.viv-desde').addEventListener('change', e => { estado.desde = e.target.value; pintar(); });
    r.querySelector('.viv-hasta').addEventListener('change', e => { estado.hasta = e.target.value; pintar(); });
    r.querySelectorAll('input[data-tajo]').forEach(cb => cb.addEventListener('change', e => {
      if (e.target.checked) estado.tajos.add(e.target.dataset.tajo); else estado.tajos.delete(e.target.dataset.tajo);
      pintar();
    }));
    r.querySelector('.viv-todos').addEventListener('click', () => {
      datos.tajos.forEach(t => estado.tajos.add(t.id)); pintar(); });
    r.querySelector('.viv-ninguno').addEventListener('click', () => { estado.tajos.clear(); pintar(); });
  });
  pintar();
})();
"""

_OPCIONES = (
    ('semana', 'Esta semana'), ('semana_pasada', 'Semana pasada'),
    ('mes', 'Este mes'), ('mes_anterior', 'Mes anterior'),
    ('anio', 'Este año'), ('anio_anterior', 'Año anterior'),
    ('todo', 'Desde el principio'), ('rango', 'Entre fechas…'))


def controles_html(datos, sufijo=''):
    """Periodo + tajos que salen. ``sufijo`` distingue la copia del informe."""
    if not datos or not datos.get('tajos'):
        return ''
    opciones = ''.join(f"<option value='{v}'>{html_lib.escape(t)}</option>"
                       for v, t in _OPCIONES)
    tajos = ''.join(
        f"<label style='margin-right:12px;white-space:nowrap'>"
        f"<input type='checkbox' data-tajo='{html_lib.escape(t['id'], quote=True)}' checked> "
        f"{html_lib.escape(t['nombre'])}</label>" for t in datos['tajos'])
    return (
        f"<div class='viv-controles' style='margin:8px 0'>"
        f"<div style='display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:8px'>"
        f"<label><b>Periodo</b> <select id='viv-periodo{sufijo}' class='viv-sel'>{opciones}</select></label>"
        f"<span class='viv-rango' id='viv-rango{sufijo}' style='display:none'>"
        f"<input type='date' id='viv-desde{sufijo}' class='viv-desde'> a "
        f"<input type='date' id='viv-hasta{sufijo}' class='viv-hasta'></span></div>"
        f"<div id='viv-tajos{sufijo}' class='viv-tajos' style='font-size:13px'><b>Tajos</b> "
        f"<button type='button' class='viv-todos'>Todos</button> "
        f"<button type='button' class='viv-ninguno'>Ninguno</button><br>{tajos}</div></div>")


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
        + controles_html(datos, '') +
        f"<div class='table-scroll'><table class='data' id='viv-tabla'><thead><tr>{cabecera}"
        "</tr></thead><tbody></tbody></table></div>"
        "<p id='viv-notas' style='font-size:12.5px;color:var(--muted);margin-top:10px'></p>"
        "</div>"
        f'<script id="viviendas-datos" type="application/json">{datos_json}</script>'
        f"<script>\n(function () {{\n{_leer_calculo_js()}\n}})();\n{_UI}</script>")
