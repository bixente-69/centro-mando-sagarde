'use strict';
/* Viviendas por tajo y periodo natural. Mismo calculo que viviendas_tajos.py
   (una prueba exige que den lo mismo). Fechas siempre en texto ISO AAAA-MM-DD:
   se comparan como texto, sin zonas horarias. */

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
  'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

function aUTC(iso) {
  const p = iso.split('-').map(Number);
  return new Date(Date.UTC(p[0], p[1] - 1, p[2]));
}
function aISO(d) {
  return d.getUTCFullYear() + '-' + String(d.getUTCMonth() + 1).padStart(2, '0') +
    '-' + String(d.getUTCDate()).padStart(2, '0');
}
function sumarDias(d, n) { const r = new Date(d.getTime()); r.setUTCDate(r.getUTCDate() + n); return r; }
function mayus(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

function periodoNatural(tipo, hoyISO) {
  const hoy = aUTC(hoyISO);
  if (tipo === 'todo') return { desde: null, hasta: null, etiqueta: 'Desde el principio' };
  if (tipo === 'semana') {
    const lunes = sumarDias(hoy, -((hoy.getUTCDay() + 6) % 7));
    return { desde: aISO(lunes), hasta: hoyISO, etiqueta: 'Esta semana' };
  }
  if (tipo === 'semana_pasada') {
    const lunes = sumarDias(hoy, -((hoy.getUTCDay() + 6) % 7) - 7);
    return { desde: aISO(lunes), hasta: aISO(sumarDias(lunes, 6)), etiqueta: 'Semana pasada' };
  }
  if (tipo === 'anio') {
    return { desde: hoy.getUTCFullYear() + '-01-01', hasta: hoyISO, etiqueta: 'Este año (' + hoy.getUTCFullYear() + ')' };
  }
  if (tipo === 'anio_anterior') {
    const a = hoy.getUTCFullYear() - 1;
    return { desde: a + '-01-01', hasta: a + '-12-31', etiqueta: 'Año ' + a };
  }
  if (tipo === 'mes') {
    const primero = new Date(Date.UTC(hoy.getUTCFullYear(), hoy.getUTCMonth(), 1));
    return { desde: aISO(primero), hasta: hoyISO, etiqueta: mayus(MESES[hoy.getUTCMonth()]) + ' (en curso)' };
  }
  if (tipo === 'mes_anterior') {
    const ultimo = sumarDias(new Date(Date.UTC(hoy.getUTCFullYear(), hoy.getUTCMonth(), 1)), -1);
    const primero = new Date(Date.UTC(ultimo.getUTCFullYear(), ultimo.getUTCMonth(), 1));
    return { desde: aISO(primero), hasta: aISO(ultimo),
      etiqueta: mayus(MESES[ultimo.getUTCMonth()]) + ' ' + ultimo.getUTCFullYear() };
  }
  if (tipo.indexOf('mes:') === 0) {
    const p = tipo.slice(4).split('-').map(Number);
    const primero = new Date(Date.UTC(p[0], p[1] - 1, 1));
    const siguiente = new Date(Date.UTC(p[0], p[1], 1));
    let fin = aISO(sumarDias(siguiente, -1));
    if (hoyISO < fin) fin = hoyISO;
    return { desde: aISO(primero), hasta: fin, etiqueta: mayus(MESES[p[1] - 1]) + ' ' + p[0] };
  }
  throw new Error('periodo desconocido: ' + tipo);
}

function contar(datos, tajoId, desde, hasta) {
  const r = { total: 0, X: 0, M: 0, '/': 0, P: 0, '?': 0, hechas: 0, dudosas: 0, acumuladas: 0, sin_fecha: 0 };
  const sinPeriodo = desde === null && hasta === null;
  (datos.celdas[tajoId] || []).forEach(function (c) {
    const v = c[0], f = c[1], fiable = c[2];
    if (v === 'N' || v === '-') return;
    r.total++;
    r[(v === 'X' || v === 'M' || v === '/' || v === 'P') ? v : '?']++;
    if (v !== 'X') return;
    if (sinPeriodo) { r.hechas++; r.acumuladas++; if (f === null) r.sin_fecha++; return; }
    if (f === null) { r.sin_fecha++; return; }
    if (hasta === null || f <= hasta) r.acumuladas++;
    if ((desde === null || f >= desde) && (hasta === null || f <= hasta)) {
      if (fiable) r.hechas++; else r.dudosas++;
    }
  });
  return r;
}

const API = { periodoNatural, contar, MESES };
if (typeof module !== 'undefined' && module.exports) { module.exports = API; }
if (typeof window !== 'undefined') { window.ViviendasCalculo = API; }
