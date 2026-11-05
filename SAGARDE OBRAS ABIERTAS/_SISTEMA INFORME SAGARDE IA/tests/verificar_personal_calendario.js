'use strict';
/* Verificador de «calendarioMes» (personal_calculo.js): qué obras tienen registro cada día del mes. Exit 0 = todo bien.
   Las cifras esperadas están calculadas a mano (no salen de ningún código). Se repite en tres zonas horarias.
   Datos INVENTADOS. */
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
function cargar() {
  try { return require(RUTA); } catch (e) { console.log('FALLO: no carga como módulo CommonJS: ' + e.message); process.exit(1); }
}

// Jornadas inventadas. Cada comentario dice qué debe pasar.
const FILAS = [
  { obra: 'a', ambito: 'vivienda', fecha: '2026-11-02', nombre: 'Ana',  horas: 7.5, extra: 0, empresa: 'Sagarde' },
  { obra: 'a', ambito: 'vivienda', fecha: '2026-11-02', nombre: 'Luis', horas: 8,   extra: 0, empresa: 'Manueles' },
  { obra: 'a', ambito: 'vivienda', fecha: '2026-11-03', nombre: 'Ana',  horas: 7.5, extra: 0, empresa: 'Sagarde' },
  { obra: 'a', ambito: 'vivienda', fecha: '2026-11-03', nombre: 'Beba', horas: null },                       // sin horas: el total del día sale «sin dato», no 0
  { obra: 'b', ambito: 'vivienda', fecha: '2026-11-02', nombre: 'Pepe', horas: 7.5, extra: 0 },
  { obra: 'b', ambito: 'garaje',   fecha: '2026-11-02', nombre: 'PEPE', horas: 2,   extra: 0 },              // misma persona (otra grafía) en la otra zona: 1 persona, 2 líneas
  { obra: 'b', ambito: 'vivienda', fecha: '2026-11-04', nombre: 'Pepe', horas: 7.5, extra: 0 },
  { obra: 'c', ambito: 'vivienda', fecha: '2026-11-04', nombre: 'Rosa', horas: 8,   extra: 0 },              // la obra c empieza el 04/11
  { obra: 'z', ambito: 'vivienda', fecha: '2026-11-02', nombre: 'Zeta', horas: 8,   extra: 0 },              // obra que ya no está abierta: sale, pero no se le exige
  { obra: 'a', ambito: 'vivienda', fecha: '2026-11-07', nombre: 'Ana',  horas: 4,   extra: 0 },              // sábado con registro
  { obra: 'a', ambito: 'vivienda', fecha: '2026-13-45', nombre: 'Xx',   horas: 8 },                           // fecha imposible: no cuenta, se avisa
  { fecha: '2026-11-03', nombre: 'Yy', horas: 8 }                                                           // sin obra: no cuenta, se avisa
];
const ABIERTAS = ['a', 'b', 'c'];
const HOY = '2026-11-09'; // lunes

function mes(C, filas, anio, m, abiertas, hoy) {
  return C.calendarioMes(filas, { anio, mes: m, obrasAbiertas: abiertas, hoy });
}
function dia(r, f) { return r.dias.filter(d => d.fecha === f)[0]; }
function idsObras(d) { return d.obras.map(o => o.obra); }

function pruebas(C) {
  ok(typeof C.calendarioMes === 'function', 'falta la función calendarioMes');
  if (typeof C.calendarioMes !== 'function') return;

  const copiaEntrada = JSON.stringify(FILAS);
  const r = mes(C, FILAS, 2026, 11, ABIERTAS, HOY);
  ok(JSON.stringify(FILAS) === copiaEntrada, 'modifica las jornadas que recibe');

  // --- La rejilla: noviembre de 2026 empieza en domingo y acaba en lunes -> 6 semanas completas (26/10 al 06/12) ---
  eq(r.dias.length, 42, 'noviembre 2026 son 6 semanas = 42 días');
  eq(r.dias[0].fecha, '2026-10-26', 'la rejilla empieza el lunes 26/10');
  eq(r.dias[41].fecha, '2026-12-06', 'la rejilla acaba el domingo 06/12');
  eq(r.dias.filter(d => d.enMes).length, 30, 'noviembre tiene 30 días del mes');
  eq(r.dias.map(d => d.semanaDia).join(''), '0123456'.repeat(6), 'los días van de lunes (0) a domingo (6)');
  eq(dia(r, '2026-10-26').enMes, false, '26/10 es de relleno');
  eq(dia(r, '2026-11-01').enMes, true, '01/11 es del mes');
  eq(dia(r, '2026-11-02').laborable, true, 'el lunes es laborable');
  eq(dia(r, '2026-11-07').laborable, false, 'el sábado no es laborable');
  eq(dia(r, '2026-11-09').hoy, true, 'el 09/11 es hoy');
  eq(dia(r, '2026-11-09').futuro, false, 'hoy no es futuro');
  eq(dia(r, '2026-11-08').hoy, false, 'el 08/11 no es hoy');
  eq(dia(r, '2026-11-10').futuro, true, 'el 10/11 es futuro');
  eq(dia(r, '2026-11-08').futuro, false, 'el 08/11 no es futuro');

  // --- Avisos y primera fecha de cada obra ---
  eq(r.avisos.filasInvalidas, 2, 'dos jornadas no válidas (fecha imposible y sin obra)');
  eq(r.primeraFecha, { a: '2026-11-02', b: '2026-11-02', c: '2026-11-04', z: '2026-11-02' }, 'primer día con registro de cada obra');

  // --- Lunes 02/11: a (2 personas), b (1 persona en 2 líneas) y z; se le exigen a y b (c aún no había empezado) ---
  let d = dia(r, '2026-11-02');
  eq(idsObras(d), ['a', 'b', 'z'], '02/11: obras con registro (abiertas primero, en su orden, y luego las demás)');
  eq(d.esperadas, ['a', 'b'], '02/11: obras que debían tener registro');
  eq(d.faltan, [], '02/11: no falta ninguna');
  eq(d.estado, 'completo', '02/11: completo');
  let o = d.obras[0];
  eq([o.nPersonas, o.horas, o.ambitos], [2, 15.5, ['vivienda']], '02/11 obra a: 2 personas, 15,5 h, viviendas');
  eq(o.personas, [
    { nombre: 'Ana', empresa: 'Sagarde', ambito: 'vivienda', horas: 7.5, extra: 0 },
    { nombre: 'Luis', empresa: 'Manueles', ambito: 'vivienda', horas: 8, extra: 0 }
  ], '02/11 obra a: quién estuvo, por nombre');
  o = d.obras[1];
  eq([o.nPersonas, o.horas, o.ambitos], [1, 9.5, ['vivienda', 'garaje']], '02/11 obra b: 1 persona (2 líneas), 9,5 h, viviendas y garajes');
  eq(o.personas.map(p => p.ambito), ['vivienda', 'garaje'], '02/11 obra b: viviendas antes que garajes');

  // --- Martes 03/11: solo a; falta b; Beba sin horas -> el total del día-obra no se inventa ---
  d = dia(r, '2026-11-03');
  eq(idsObras(d), ['a'], '03/11: solo a');
  eq(d.faltan, ['b'], '03/11: falta b');
  eq(d.estado, 'parcial', '03/11: parcial');
  eq([d.obras[0].nPersonas, d.obras[0].horas], [2, null], '03/11 obra a: 2 personas y horas sin dato (no 0)');

  // --- Miércoles 04/11: b y c; falta a ---
  d = dia(r, '2026-11-04');
  eq(idsObras(d), ['b', 'c'], '04/11: b y c');
  eq(d.esperadas, ['a', 'b', 'c'], '04/11: se exigen las tres');
  eq(d.faltan, ['a'], '04/11: falta a');
  eq(d.estado, 'parcial', '04/11: parcial');

  // --- Jueves 05 y viernes 06: laborables pasados sin nada -> ninguno ---
  for (const f of ['2026-11-05', '2026-11-06']) {
    d = dia(r, f);
    eq([idsObras(d), d.esperadas, d.faltan, d.estado], [[], ['a', 'b', 'c'], ['a', 'b', 'c'], 'ninguno'], f + ': laborable pasado sin registro de ninguna obra');
  }

  // --- Fin de semana: con registro cuenta como completo y no se exige nada; sin registro, vacío ---
  d = dia(r, '2026-11-07');
  eq([idsObras(d), d.esperadas, d.faltan, d.estado, d.obras[0].horas], [['a'], [], [], 'completo', 4], '07/11 sábado con registro');
  d = dia(r, '2026-11-08');
  eq([idsObras(d), d.esperadas, d.faltan, d.estado], [[], [], [], 'vacio'], '08/11 domingo sin registro: vacío');
  d = dia(r, '2026-11-01');
  eq(d.estado, 'vacio', '01/11 domingo: vacío');

  // --- Antes de que empezara ninguna obra no se exige nada; hoy y el futuro tampoco ---
  eq([dia(r, '2026-10-30').esperadas, dia(r, '2026-10-30').estado], [[], 'vacio'], '30/10 (antes de la primera jornada): no se exige nada');
  eq([dia(r, '2026-11-09').esperadas, dia(r, '2026-11-09').estado], [[], 'vacio'], 'hoy: aún no es un hueco');
  eq([dia(r, '2026-11-12').esperadas, dia(r, '2026-11-12').estado], [[], 'vacio'], 'futuro: no se exige nada');

  // --- Otros meses: diciembre 2026 = 5 semanas; febrero 2027 = 4 semanas exactas ---
  let r2 = mes(C, FILAS, 2026, 12, ABIERTAS, HOY);
  eq([r2.dias.length, r2.dias[0].fecha, r2.dias[34].fecha], [35, '2026-11-30', '2027-01-03'], 'diciembre 2026: 35 días, del 30/11 al 03/01');
  eq(dia(r2, '2026-12-01').enMes, true, 'diciembre: el día 1 es del mes');
  r2 = mes(C, FILAS, 2027, 2, ABIERTAS, HOY);
  eq([r2.dias.length, r2.dias[0].fecha, r2.dias[27].fecha], [28, '2027-02-01', '2027-02-28'], 'febrero 2027: 4 semanas exactas');
  // 2028 es bisiesto: 29 de febrero
  r2 = mes(C, [], 2028, 2, [], HOY);
  eq(r2.dias.filter(x => x.enMes).length, 29, 'febrero 2028 tiene 29 días');

  // --- Sin jornadas, sin obras o con parámetros raros: nada se rompe ni se inventa ---
  r2 = mes(C, [], 2026, 11, ABIERTAS, HOY);
  eq([r2.dias.length, r2.dias.every(x => x.estado === 'vacio' && x.obras.length === 0 && x.esperadas.length === 0)], [42, true], 'sin jornadas: todo vacío, sin exigir nada');
  r2 = C.calendarioMes(null, { anio: 2026, mes: 11, obrasAbiertas: null, hoy: HOY });
  eq(r2.dias.length, 42, 'filas null: la rejilla sale igual');
  eq(C.calendarioMes(FILAS, { anio: 2026, mes: 13, obrasAbiertas: ABIERTAS, hoy: HOY }).dias, [], 'mes 13: sin rejilla');
  eq(C.calendarioMes(FILAS, { anio: 'x', mes: 11, obrasAbiertas: ABIERTAS, hoy: HOY }).dias, [], 'año no numérico: sin rejilla');
  // Sin «hoy» válido no se exige nada (no se puede saber qué días ya pasaron)
  r2 = C.calendarioMes(FILAS, { anio: 2026, mes: 11, obrasAbiertas: ABIERTAS });
  eq(dia(r2, '2026-11-05').estado, 'vacio', 'sin «hoy»: no se exige nada');

  // --- Una obra abierta que nunca tuvo jornadas (como Gorliz) no se exige nunca ---
  r2 = mes(C, FILAS, 2026, 11, ['a', 'b', 'c', 'g'], HOY);
  eq(dia(r2, '2026-11-05').esperadas, ['a', 'b', 'c'], 'una obra sin ninguna jornada no se exige');

  // --- Un registro de otra obra el mismo día no tapa el hueco de la que falta ---
  eq(dia(r, '2026-11-03').faltan, ['b'], 'que a tenga registro no oculta que b falta');
}

function enNavegadorSimulado() {
  // La página carga personal_calculo.js con <script>, no con require: el resultado tiene que ser el mismo.
  const fs = require('fs'), vm = require('vm');
  const src = fs.readFileSync(RUTA, 'utf8');
  const W = { window: {} };
  W.window = W;
  vm.createContext(W);
  vm.runInContext(src, W);
  ok(W.window.PersonalCalculo && typeof W.window.PersonalCalculo.calendarioMes === 'function', 'en el navegador falta calendarioMes');
  if (W.window.PersonalCalculo && typeof W.window.PersonalCalculo.calendarioMes === 'function') {
    const a = JSON.parse(JSON.stringify(W.window.PersonalCalculo.calendarioMes(FILAS, { anio: 2026, mes: 11, obrasAbiertas: ABIERTAS, hoy: HOY })));
    const b = JSON.parse(JSON.stringify(cargar().calendarioMes(FILAS, { anio: 2026, mes: 11, obrasAbiertas: ABIERTAS, hoy: HOY })));
    eq(a, b, 'resultado distinto en contexto navegador');
  }
  ok(!/\.(getFullYear|getMonth|getDate|getDay|getHours)\s*\(/.test(src), 'usa hora local: usa getUTC*');
}

if (!process.env.VERIF_TZ) {
  pruebas(cargar());
  enNavegadorSimulado();
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
