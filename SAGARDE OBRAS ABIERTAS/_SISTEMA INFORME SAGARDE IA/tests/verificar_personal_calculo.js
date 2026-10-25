'use strict';
/* Verificador de P2 (personal_calculo.js). Exit 0 = todo bien.
   Las cifras esperadas están calculadas a mano (no salen de ningún código). Se repite con zonas horarias extremas. */
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const { spawnSync } = require('child_process');
const RUTA = path.join(process.cwd(), 'personal_calculo.js');

let total = 0, fallos = 0;
function canon(x) {
  if (Array.isArray(x)) return x.map(canon);
  if (x && typeof x === 'object') { const o = {}; Object.keys(x).sort().forEach(k => { o[k] = canon(x[k]); }); return o; }
  return x;
}
function ok(cond, msg) { total++; if (!cond) { fallos++; console.log('FALLO: ' + msg); } }
function eq(a, b, msg) { ok(JSON.stringify(canon(a)) === JSON.stringify(canon(b)), msg + ' | esperado ' + JSON.stringify(b) + ' | obtenido ' + JSON.stringify(a)); }
function cerca(a, b, msg) { ok(typeof a === 'number' && Math.abs(a - b) < 1e-9, msg + ' | esperado ' + b + ' | obtenido ' + a); }

function cargar() {
  try { return require(RUTA); } catch (e) { console.log('FALLO: no carga como módulo CommonJS: ' + e.message); process.exit(1); }
}

const R = [
  { obra: 'A', ambito: 'vivienda', fecha: '2026-12-28', nombre: 'Ana',    horas: 8,  extra: 0 },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-12-29', nombre: 'Ana',    horas: 8,  extra: 0 },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-12-31', nombre: 'Ana',    horas: 10, extra: 2 },
  { obra: 'A', ambito: 'vivienda', fecha: '2027-01-01', nombre: 'Ana',    horas: 6,  extra: 0 },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-12-31', nombre: 'Beto',   horas: 8,  extra: 0 },
  { obra: 'A', ambito: 'vivienda', fecha: '2027-01-04', nombre: 'Beto',   horas: 8,  extra: 0 },
  { obra: 'A', ambito: 'vivienda', fecha: '2027-01-02', nombre: 'Beto',   horas: 5,  extra: 5 },
  { obra: 'B', ambito: 'garaje',   fecha: '2026-12-29', nombre: 'Ana',    horas: 4,  extra: 0 },
  { obra: 'B', ambito: 'garaje',   fecha: '2026-12-29', nombre: 'Carlos', horas: 8,  extra: 0 }
];
const nombres = r => r.trabajadores.map(t => t.nombre);
const claves = m => m.columnas.map(c => c.clave);
const etiq = m => m.columnas.map(c => c.etiqueta);

function pruebas(C) {
  const necesarias = ['semanaISO', 'rangoPeriodo', 'mover', 'filtrar', 'agregar', 'matriz', 'ranking'];
  necesarias.forEach(f => ok(typeof C[f] === 'function', 'falta la función ' + f));
  if (necesarias.some(f => typeof C[f] !== 'function')) return;

  const copiaR = JSON.stringify(R);

  // --- semanaISO
  [['2026-10-22', 43], ['2026-12-31', 53], ['2027-01-01', 53], ['2027-01-03', 53], ['2027-01-04', 1],
   ['2026-01-01', 1], ['2024-12-30', 1], ['2021-01-03', 53]]
    .forEach(([f, s]) => eq(C.semanaISO(f), s, 'semanaISO ' + f));

  // --- rangoPeriodo
  eq(C.rangoPeriodo('semana', '2026-12-31'), { desde: '2026-12-28', hasta: '2027-01-03' }, 'semana de un jueves a caballo de año');
  eq(C.rangoPeriodo('semana', '2027-01-03'), { desde: '2026-12-28', hasta: '2027-01-03' }, 'semana de un domingo');
  eq(C.rangoPeriodo('semana', '2026-12-28'), { desde: '2026-12-28', hasta: '2027-01-03' }, 'semana de un lunes');
  eq(C.rangoPeriodo('mes', '2026-12-31'), { desde: '2026-12-01', hasta: '2026-12-31' }, 'mes diciembre');
  eq(C.rangoPeriodo('mes', '2028-02-10'), { desde: '2028-02-01', hasta: '2028-02-29' }, 'febrero bisiesto');
  eq(C.rangoPeriodo('mes', '2026-02-10'), { desde: '2026-02-01', hasta: '2026-02-28' }, 'febrero normal');
  eq(C.rangoPeriodo('anio', '2026-12-31'), { desde: '2026-01-01', hasta: '2026-12-31' }, 'año');
  eq(C.rangoPeriodo('obra', '2026-12-31'), { desde: null, hasta: null }, 'obra sin límites');

  // --- mover
  eq(C.rangoPeriodo('mes', C.mover('mes', '2026-03-31', -1)), { desde: '2026-02-01', hasta: '2026-02-28' }, 'mover mes -1 desde 31/03');
  eq(C.rangoPeriodo('mes', C.mover('mes', '2026-01-31', 1)), { desde: '2026-02-01', hasta: '2026-02-28' }, 'mover mes +1 desde 31/01');
  eq(C.rangoPeriodo('mes', C.mover('mes', '2026-12-15', 1)), { desde: '2027-01-01', hasta: '2027-01-31' }, 'mover mes a otro año');
  eq(C.rangoPeriodo('semana', C.mover('semana', '2026-12-31', 1)), { desde: '2027-01-04', hasta: '2027-01-10' }, 'mover semana +1');
  eq(C.rangoPeriodo('semana', C.mover('semana', '2026-12-31', -1)), { desde: '2026-12-21', hasta: '2026-12-27' }, 'mover semana -1');
  eq(C.rangoPeriodo('anio', C.mover('anio', '2026-12-31', -1)), { desde: '2025-01-01', hasta: '2025-12-31' }, 'mover año -1');
  eq(C.mover('obra', '2026-05-05', 3), '2026-05-05', 'mover obra no cambia');

  // --- filtrar
  const f1 = C.filtrar(R, { obra: 'A', periodo: 'semana', ref: '2026-12-31' });
  eq(f1.length, 6, 'filtrar obra A semana 53');
  ok(!f1.some(j => j.fecha === '2027-01-04' || j.obra === 'B'), 'filtrar deja pasar filas que no tocan');
  eq(C.filtrar(R, { periodo: 'semana', ref: '2026-12-31' }).length, 8, 'filtrar global semana');
  eq(C.filtrar(R, { obra: 'A', ambito: 'garaje', periodo: 'obra' }).length, 0, 'filtrar obra A garaje');
  eq(C.filtrar(R, { ambito: 'garaje', periodo: 'obra' }).length, 2, 'filtrar garajes');
  eq(C.filtrar(R, { periodo: 'obra' }).length, 9, 'filtrar toda la obra');
  eq(C.filtrar(R, { obra: 'todo', ambito: 'todo', periodo: 'obra' }).length, 9, "'todo' no filtra");
  eq(C.filtrar(R, { obra: 'A', periodo: 'semana', ref: '2026-01-05' }), [], 'filtrar semana sin filas');

  // --- agregar (obra A, semana 53)
  const a1 = C.agregar(f1);
  eq(nombres(a1), ['Ana', 'Beto'], 'orden semana');
  const ana = a1.trabajadores[0], beto = a1.trabajadores[1];
  eq([ana.dias, ana.horas, ana.extra, ana.ordinarias], [4, 32, 2, 30], 'Ana semana 53');
  cerca(ana.pct, 100 * 32 / 45, 'pct Ana');
  eq([beto.dias, beto.horas, beto.extra, beto.ordinarias], [2, 13, 5, 8], 'Beto semana 53');
  cerca(beto.pct, 100 * 13 / 45, 'pct Beto');
  eq(ana.obras, { A: 32 }, 'obras de Ana');
  eq(a1.total, { horas: 45, extra: 7, ordinarias: 38, dias: 5, trabajadores: 2 }, 'total semana 53');
  eq(a1.avisos, { filasSinHoras: 0, filasInvalidas: 0 }, 'avisos limpios');

  // --- agregar (obra A, mes diciembre)
  const a2 = C.agregar(C.filtrar(R, { obra: 'A', periodo: 'mes', ref: '2026-12-15' }));
  eq([a2.trabajadores[0].nombre, a2.trabajadores[0].horas, a2.trabajadores[0].dias], ['Ana', 26, 3], 'Ana diciembre');
  eq([a2.trabajadores[1].nombre, a2.trabajadores[1].horas, a2.trabajadores[1].dias], ['Beto', 8, 1], 'Beto diciembre');
  eq(a2.total, { horas: 34, extra: 2, ordinarias: 32, dias: 3, trabajadores: 2 }, 'total diciembre');
  cerca(a2.trabajadores[0].pct, 100 * 26 / 34, 'pct Ana diciembre');

  // --- ranking global
  const rk = C.ranking(R, { periodo: 'semana', ref: '2026-12-31' });
  eq(nombres(rk), ['Ana', 'Beto', 'Carlos'], 'ranking semana: orden');
  eq(rk.trabajadores.map(t => t.horas), [36, 13, 8], 'ranking semana: horas');
  eq(rk.trabajadores[0].dias, 4, 'Ana: fechas distintas aunque trabaje en dos obras el mismo día');
  eq(rk.trabajadores[0].obras, { A: 32, B: 4 }, 'Ana: horas por obra');
  eq(rk.trabajadores[2].dias, 1, 'Carlos días');
  eq(rk.total, { horas: 57, extra: 7, ordinarias: 50, dias: 5, trabajadores: 3 }, 'ranking semana: total');
  cerca(rk.trabajadores.reduce((s, t) => s + t.pct, 0), 100, 'los pct del ranking suman 100');
  const rko = C.ranking(R, { periodo: 'obra' });
  eq(nombres(rko), ['Ana', 'Beto', 'Carlos'], 'ranking obra: orden');
  eq(rko.trabajadores.map(t => t.horas), [36, 21, 8], 'ranking obra: horas');
  eq(rko.trabajadores[1].dias, 3, 'Beto días en toda la obra');
  eq(rko.total, { horas: 65, extra: 7, ordinarias: 58, dias: 6, trabajadores: 3 }, 'ranking obra: total');

  // --- sin datos / datos que faltan: nunca ceros
  const vacio = C.agregar([]);
  eq(vacio.trabajadores, [], 'agregar([]) trabajadores');
  ok(vacio.total === null, 'agregar([]) debe dar total null, no ceros');
  eq(vacio.avisos, { filasSinHoras: 0, filasInvalidas: 0 }, 'agregar([]) avisos');
  ok(C.agregar(C.filtrar(R, { obra: 'A', periodo: 'semana', ref: '2026-01-05' })).total === null, 'periodo sin jornadas -> total null');
  const base = { obra: 'A', ambito: 'vivienda', fecha: '2026-12-28', nombre: 'Ana' };
  const x1 = C.agregar([Object.assign({}, base, { horas: null, extra: 0 }), Object.assign({}, base, { fecha: '2026-12-29', horas: 8, extra: 0 })]);
  eq(x1.total.horas, 8, 'una fila sin horas no cuenta como 0 ni suma');
  eq(x1.avisos, { filasSinHoras: 1, filasInvalidas: 0 }, 'aviso de fila sin horas');
  const x2 = C.agregar([Object.assign({}, base, { horas: undefined })]);
  ok(x2.total === null && x2.trabajadores.length === 0, 'solo filas sin horas -> total null');
  eq(x2.avisos.filasSinHoras, 1, 'horas undefined cuenta como sin horas');
  eq(C.agregar([Object.assign({}, base, { horas: 'ocho', extra: 0 })]).avisos.filasSinHoras, 1, 'horas en texto cuenta como sin horas');
  [[30, 0], [-1, 0], [8, 9], [8, -1]].forEach(([h, e]) => {
    const r = C.agregar([Object.assign({}, base, { horas: h, extra: e })]);
    ok(r.total === null && r.avisos.filasInvalidas === 1, 'fila inválida horas=' + h + ' extra=' + e + ' debe contarse como inválida');
  });
  eq(C.agregar([Object.assign({}, base, { nombre: '', horas: 8, extra: 0 })]).avisos.filasInvalidas, 1, 'nombre vacío');
  const x8 = C.agregar([Object.assign({}, base, { horas: 0, extra: 0 })]);
  eq(x8.total.horas, 0, 'una fila válida con 0 horas cuenta');
  ok(x8.trabajadores[0].pct === null, 'pct con total 0 debe ser null (no NaN)');
  const x9 = C.agregar([Object.assign({}, base, { horas: 8 })]);
  eq([x9.trabajadores[0].extra, x9.trabajadores[0].ordinarias], [0, 8], 'extra omitido = 0');
  eq(nombres(C.agregar([Object.assign({}, base, { nombre: 'Zuri', horas: 8, extra: 0 }), Object.assign({}, base, { nombre: 'Ander', horas: 8, extra: 0 })])),
     ['Ander', 'Zuri'], 'empate de horas: orden alfabético');

  // --- matriz
  const mw = C.matriz(f1, 'semana', '2026-12-31');
  eq(claves(mw), ['2026-12-28', '2026-12-29', '2026-12-30', '2026-12-31', '2027-01-01', '2027-01-02', '2027-01-03'], 'matriz semana: claves');
  eq(etiq(mw), ['lun 28', 'mar 29', 'mié 30', 'jue 31', 'vie 01', 'sáb 02', 'dom 03'], 'matriz semana: etiquetas');
  eq(mw.filas.map(f => f.nombre), ['Ana', 'Beto'], 'matriz semana: orden de filas');
  eq(mw.filas[0].celdas, { '2026-12-28': 8, '2026-12-29': 8, '2026-12-30': null, '2026-12-31': 10, '2027-01-01': 6, '2027-01-02': null, '2027-01-03': null }, 'matriz semana: Ana');
  eq(mw.filas[1].celdas, { '2026-12-28': null, '2026-12-29': null, '2026-12-30': null, '2026-12-31': 8, '2027-01-01': null, '2027-01-02': 5, '2027-01-03': null }, 'matriz semana: Beto');
  eq([mw.filas[0].total, mw.filas[1].total], [32, 13], 'matriz semana: totales de fila');
  eq(mw.totalesColumna, { '2026-12-28': 8, '2026-12-29': 8, '2026-12-30': null, '2026-12-31': 18, '2027-01-01': 6, '2027-01-02': 5, '2027-01-03': null }, 'matriz semana: totales de columna');

  const fm = C.filtrar(R, { obra: 'A', periodo: 'mes', ref: '2026-12-15' });
  const mm = C.matriz(fm, 'mes', '2026-12-15');
  eq(claves(mm), ['2026-11-30', '2026-12-07', '2026-12-14', '2026-12-21', '2026-12-28'], 'matriz mes: claves (semanas que tocan diciembre)');
  eq(etiq(mm), ['S49', 'S50', 'S51', 'S52', 'S53'], 'matriz mes: etiquetas');
  eq(mm.filas[0].celdas, { '2026-11-30': null, '2026-12-07': null, '2026-12-14': null, '2026-12-21': null, '2026-12-28': 26 }, 'matriz mes: Ana');
  eq(mm.filas[1].celdas['2026-12-28'], 8, 'matriz mes: Beto');

  const ma = C.matriz(C.filtrar(R, { obra: 'A', periodo: 'anio', ref: '2026-12-31' }), 'anio', '2026-12-31');
  eq(claves(ma), ['2026-12'], 'matriz año: solo meses con datos');
  eq(etiq(ma), ['dic'], 'matriz año: etiqueta');
  eq([ma.filas[0].celdas['2026-12'], ma.filas[1].celdas['2026-12']], [26, 8], 'matriz año: celdas');
  const R2 = [
    { obra: 'A', ambito: 'vivienda', fecha: '2026-03-10', nombre: 'Ana', horas: 8, extra: 0 },
    { obra: 'A', ambito: 'vivienda', fecha: '2026-05-12', nombre: 'Ana', horas: 6, extra: 0 }
  ];
  const m2 = C.matriz(R2, 'anio', '2026-06-01');
  eq(claves(m2), ['2026-03', '2026-04', '2026-05'], 'matriz año: incluye meses intermedios sin datos');
  eq(etiq(m2), ['mar', 'abr', 'may'], 'matriz año: etiquetas intermedias');
  eq(m2.filas[0].celdas, { '2026-03': 8, '2026-04': null, '2026-05': 6 }, 'matriz año: mes intermedio es null, no 0');
  const mo = C.matriz(C.filtrar(R, { obra: 'A', periodo: 'obra' }), 'obra', '2026-12-31');
  eq(claves(mo), ['2026-12', '2027-01'], 'matriz obra: claves');
  eq(etiq(mo), ["dic '26", "ene '27"], 'matriz obra: etiquetas');
  eq(mo.filas[0].celdas, { '2026-12': 26, '2027-01': 6 }, 'matriz obra: Ana');
  eq(mo.filas[1].celdas, { '2026-12': 8, '2027-01': 13 }, 'matriz obra: Beto');
  const me = C.matriz([], 'anio', '2026-06-01');
  eq([me.columnas, me.filas], [[], []], 'matriz año vacía');
  const ms = C.matriz([], 'semana', '2026-12-31');
  eq([ms.columnas.length, ms.filas.length], [7, 0], 'matriz semana vacía conserva las 7 columnas');
  eq(C.matriz([Object.assign({}, base, { horas: null })], 'semana', '2026-12-28').filas, [], 'matriz ignora filas sin horas');

  // --- no muta la entrada
  eq(JSON.stringify(R), copiaR, 'las funciones no deben modificar la entrada');

  // --- mismo resultado en un navegador simulado, sin dependencias
  const src = fs.readFileSync(RUTA, 'utf8');
  const ctx = { window: {}, console: console };
  vm.createContext(ctx);
  try { vm.runInContext(src, ctx); } catch (e) { ok(false, 'no se ejecuta en un contexto de navegador simulado: ' + e.message); }
  ok(ctx.window.PersonalCalculo && typeof ctx.window.PersonalCalculo.agregar === 'function', 'no publica window.PersonalCalculo');
  if (ctx.window.PersonalCalculo) eq(ctx.window.PersonalCalculo.agregar(f1).total.horas, 45, 'resultado distinto en contexto navegador');
  ok(!/require\s*\(/.test(src), 'no debe usar require');
  ok(!/\bdocument\s*\./.test(src) && !/\b(localStorage|fetch)\b/.test(src), 'no debe usar DOM, localStorage ni fetch');
  ok(!/\.(getFullYear|getMonth|getDate|getDay|getHours)\s*\(/.test(src), 'usa hora local: usa getUTC*');
}

if (!process.env.VERIF_TZ) {
  pruebas(cargar());
  for (const tz of ['Pacific/Auckland', 'America/Los_Angeles']) {
    const r = spawnSync(process.execPath, [__filename], { env: Object.assign({}, process.env, { VERIF_TZ: tz, TZ: tz }), encoding: 'utf8' });
    if (r.stdout) process.stdout.write(r.stdout);
    total++;
    if (r.status !== 0) { fallos++; console.log('FALLO: con zona horaria ' + tz + ' el resultado cambia'); }
  }
  console.log(total + ' comprobaciones, ' + fallos + ' fallos');
  process.exit(fallos ? 1 : 0);
} else {
  pruebas(cargar());
  console.log('[' + process.env.VERIF_TZ + '] offset local ' + new Date(2026, 0, 1).getTimezoneOffset() + ' min, ' + total + ' comprobaciones, ' + fallos + ' fallos');
  process.exit(fallos ? 1 : 0);
}
