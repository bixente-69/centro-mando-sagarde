'use strict';
/* Verificador de la «Base de trabajadores» de P2 (personal_calculo.js, paso 08e). Exit 0 = todo bien.
   Las cifras esperadas están calculadas a mano (no salen de ningún código). Se repite en tres zonas horarias. */
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

// Quita las marcas de tilde (se construye con códigos para no dejar caracteres combinantes sueltos en el fichero)
const MARCAS_TILDE = new RegExp('[' + String.fromCharCode(0x300) + '-' + String.fromCharCode(0x36f) + ']', 'g');

function cargar() {
  try { return require(RUTA); } catch (e) { console.log('FALLO: no carga como módulo CommonJS: ' + e.message); process.exit(1); }
}

// Jornadas inventadas. Cada comentario dice qué debe pasar.
const FILAS = [
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-19', nombre: 'Ana',   horas: 7.5, extra: 0 },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-20', nombre: 'Ana',   horas: 7.5, extra: 1 },
  { obra: 'B', ambito: 'garaje',   fecha: '2026-10-20', nombre: 'Ana',   horas: 2,   extra: 0 },   // mismo día en otra obra: sigue siendo 1 día
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-19', nombre: 'Beto',  horas: 8,   extra: 0 },
  { obra: 'B', ambito: 'vivienda', fecha: '2026-10-22', nombre: 'Beto',  horas: 4,   extra: 0 },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-21', nombre: 'Carla', horas: 6,   extra: 0 },   // no está en la base: sale igual
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-21', nombre: 'Ana',   horas: null },            // sin horas: no se cuenta, se avisa
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-21', nombre: 'Dani',  horas: 30,  extra: 0 },   // más de 24 h: no válida, se avisa
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-18', nombre: 'Gala',  horas: 6,   extra: 0 },   // empata en horas con Carla
  { obra: 'B', ambito: 'vivienda', fecha: '2026-10-23', nombre: 'ANGEL', horas: 4,   extra: 0 }    // sin tilde ni mayúsculas: es «Ángel»
];
const CATALOGO = [
  { id: 'T0001', nombre: 'Ana', empresa: 'Manueles', activo: true, nombres_anteriores: ['Anita', 'Ana M'] },
  { id: 'T0002', nombre: 'Beto', empresa: '', activo: true, fusionados: ['Beto B'] },
  { id: 'T0003', nombre: 'Dani', empresa: 'Dani @AUT', activo: true },          // sin jornadas válidas
  { id: 'T0004', nombre: 'Eli', empresa: '', activo: false },                    // dada de baja, sin jornadas
  { id: 'T0005', nombre: 'Fede', empresa: '', activo: true, nombres_anteriores: 'Fedor' },   // historial ilegible: se avisa
  { id: 'T0006', nombre: 'Gala', empresa: '', activo: true },
  { id: 'T0007', nombre: 'Ángel', empresa: 'Sin empresa', activo: true },
  { id: 'T0008', nombre: 'ana', empresa: '', activo: true },                      // repetida (misma clave que Ana): se avisa
  { id: 'T0009', empresa: '', activo: true }                                      // sin nombre: se avisa
];

// Resultado esperado a mano.
//   Ana: 7,5 + 7,5 + 2 = 17 h (extra 1); días 19 y 20 = 2; obra A 15 h en 2 días (última 20), obra B 2 h en 1 día (última 20).
//   Beto: 8 + 4 = 12 h; días 19 y 22 = 2; A 8 h/1 día (19), B 4 h/1 día (22); última 22 en B.
//   Carla (sin ficha): 6 h; 1 día; A. Gala: 6 h; 1 día (18). Ángel: 4 h; 1 día (23) en B. Dani, Eli y Fede: sin jornadas.
//   Horas totales 17 + 12 + 6 + 6 + 4 = 45; extra 1; 8 personas, 5 con jornadas y 3 sin.
const ESPERADO = {
  Ana: { horas: 17, extra: 1, dias: 2, ultima: '2026-10-20', ultimaObras: ['A', 'B'], empresa: 'Manueles',
    obras: [{ obra: 'A', dias: 2, horas: 15, ultima: '2026-10-20' }, { obra: 'B', dias: 1, horas: 2, ultima: '2026-10-20' }],
    anteriores: ['Anita', 'Ana M'], fusionados: [], sinFicha: false, conJornadas: true, activo: true },
  Beto: { horas: 12, extra: 0, dias: 2, ultima: '2026-10-22', ultimaObras: ['B'], empresa: '',
    obras: [{ obra: 'A', dias: 1, horas: 8, ultima: '2026-10-19' }, { obra: 'B', dias: 1, horas: 4, ultima: '2026-10-22' }],
    anteriores: [], fusionados: ['Beto B'], sinFicha: false, conJornadas: true, activo: true },
  Carla: { horas: 6, extra: 0, dias: 1, ultima: '2026-10-21', ultimaObras: ['A'], empresa: '',
    obras: [{ obra: 'A', dias: 1, horas: 6, ultima: '2026-10-21' }],
    anteriores: [], fusionados: [], sinFicha: true, conJornadas: true, activo: true },
  Dani: { horas: 0, extra: 0, dias: 0, ultima: null, ultimaObras: [], empresa: 'Dani @AUT', obras: [],
    anteriores: [], fusionados: [], sinFicha: false, conJornadas: false, activo: true },
  Eli: { horas: 0, extra: 0, dias: 0, ultima: null, ultimaObras: [], empresa: '', obras: [],
    anteriores: [], fusionados: [], sinFicha: false, conJornadas: false, activo: false },
  Fede: { horas: 0, extra: 0, dias: 0, ultima: null, ultimaObras: [], empresa: '', obras: [],
    anteriores: [], fusionados: [], sinFicha: false, conJornadas: false, activo: true },
  Gala: { horas: 6, extra: 0, dias: 1, ultima: '2026-10-18', ultimaObras: ['A'], empresa: '',
    obras: [{ obra: 'A', dias: 1, horas: 6, ultima: '2026-10-18' }],
    anteriores: [], fusionados: [], sinFicha: false, conJornadas: true, activo: true },
  'Ángel': { horas: 4, extra: 0, dias: 1, ultima: '2026-10-23', ultimaObras: ['B'], empresa: '',
    obras: [{ obra: 'B', dias: 1, horas: 4, ultima: '2026-10-23' }],
    anteriores: [], fusionados: [], sinFicha: false, conJornadas: true, activo: true }
};

function pruebas(C) {
  const necesarias = ['agregar', 'baseTrabajadores', 'ordenarBase'];
  necesarias.forEach(f => ok(typeof C[f] === 'function', 'falta la función ' + f));
  if (necesarias.some(f => typeof C[f] !== 'function')) return;

  const copiaFilas = JSON.stringify(FILAS);
  const copiaCatalogo = JSON.stringify(CATALOGO);
  const b = C.baseTrabajadores(FILAS, CATALOGO);
  const nombres = b.personas.map(p => p.nombre);

  // --- una línea por persona de la base, alfabético, y quien tiene jornadas sin estar en la base también sale
  eq(nombres, ['Ana', 'Ángel', 'Beto', 'Carla', 'Dani', 'Eli', 'Fede', 'Gala'], 'personas, por orden alfabético');
  b.personas.forEach(p => {
    const e = ESPERADO[p.nombre];
    if (!e) { ok(false, 'persona que no se esperaba: ' + p.nombre); return; }
    const visto = {
      horas: p.horas, extra: p.extra, dias: p.dias, ultima: p.ultima, ultimaObras: p.ultimaObras, empresa: p.empresa, obras: p.obras,
      anteriores: p.anteriores, fusionados: p.fusionados, sinFicha: p.sinFicha, conJornadas: p.conJornadas, activo: p.activo
    };
    eq(visto, e, 'línea de ' + p.nombre);
    ok(!Object.keys(p).some(k => k.charAt(0) === '_'), 'la línea de ' + p.nombre + ' no deja campos de trabajo internos');
  });
  eq(b.total, { personas: 8, conJornadas: 5, sinJornadas: 3, horas: 45, extra: 1 }, 'totales');
  eq(b.avisos, { filasSinHoras: 1, filasInvalidas: 1, fichasInvalidas: 1, fichasRepetidas: ['ana'],
    historialIlegible: ['Fede'], sinFicha: ['Carla'] }, 'avisos: nada se omite en silencio');
  eq(JSON.stringify(FILAS), copiaFilas, 'no cambia las filas que recibe');
  eq(JSON.stringify(CATALOGO), copiaCatalogo, 'no cambia el catálogo que recibe');

  // --- coherencia con la suma por persona del ranking (mismas reglas, mismas cifras)
  const g = C.agregar(FILAS);
  g.trabajadores.forEach(t => {
    const clave = t.nombre.normalize('NFD').replace(MARCAS_TILDE, '').toLowerCase();
    const p = b.personas.find(x => x.nombre.normalize('NFD').replace(MARCAS_TILDE, '').toLowerCase() === clave);
    ok(!!p, 'el ranking tiene a ' + t.nombre + ' y la base no');
    if (!p) return;
    eq([p.horas, p.extra, p.dias], [t.horas, t.extra, t.dias], 'horas, extra y días de ' + t.nombre + ' = los del ranking');
    const obrasBase = {};
    p.obras.forEach(o => { obrasBase[o.obra] = o.horas; });
    eq(obrasBase, t.obras, 'horas por obra de ' + t.nombre + ' = las del ranking');
  });
  eq([b.total.horas, b.total.extra], [g.total.horas, g.total.extra], 'las horas totales son las del ranking');

  // --- orden
  eq(C.ordenarBase(b.personas, 'nombre').map(p => p.nombre), ['Ana', 'Ángel', 'Beto', 'Carla', 'Dani', 'Eli', 'Fede', 'Gala'], 'orden por nombre');
  eq(C.ordenarBase(b.personas, 'horas').map(p => p.nombre), ['Ana', 'Beto', 'Carla', 'Gala', 'Ángel', 'Dani', 'Eli', 'Fede'],
    'orden por horas: más primero, con las mismas horas el nombre, y sin jornadas al final');
  eq(C.ordenarBase(b.personas, 'ultima').map(p => p.nombre), ['Ángel', 'Beto', 'Carla', 'Ana', 'Gala', 'Dani', 'Eli', 'Fede'],
    'orden por última jornada: la más reciente primero y sin jornadas al final');
  eq(C.ordenarBase(b.personas, 'algo raro').map(p => p.nombre), ['Ana', 'Ángel', 'Beto', 'Carla', 'Dani', 'Eli', 'Fede', 'Gala'], 'un criterio desconocido ordena por nombre');
  const antes = b.personas.map(p => p.nombre).join();
  C.ordenarBase(b.personas, 'horas');
  eq(b.personas.map(p => p.nombre).join(), antes, 'ordenarBase no cambia la lista que recibe');
  eq(C.ordenarBase(null, 'horas'), [], 'ordenarBase sin lista da una lista vacía');

  // --- bordes
  const vacio = C.baseTrabajadores(undefined, undefined);
  eq(vacio.personas, [], 'sin datos no hay personas');
  eq(vacio.total, { personas: 0, conJornadas: 0, sinJornadas: 0, horas: 0, extra: 0 }, 'sin datos los totales son 0 personas (no se inventa nada)');
  const soloFicha = C.baseTrabajadores([], [{ nombre: 'Ona' }]);
  eq([soloFicha.personas.length, soloFicha.personas[0].conJornadas, soloFicha.personas[0].ultima, soloFicha.personas[0].horas], [1, false, null, 0],
    'una persona de la base sin jornadas sale, sin última jornada');
  const fechaMala = C.baseTrabajadores([{ obra: 'A', nombre: 'X', fecha: '2026-02-30', horas: 1 }], []).personas[0];
  eq([fechaMala.horas, fechaMala.dias, fechaMala.ultima, fechaMala.ultimaObras], [1, 1, null, []],
    'una fecha que no existe cuenta las horas pero no es nunca «la última jornada» (ni de ninguna obra)');
  const fechaBuena = C.baseTrabajadores([{ obra: 'A', nombre: 'X', fecha: '2026-02-30', horas: 1 }, { obra: 'A', nombre: 'X', fecha: '2026-10-01', horas: 1 }], []).personas[0];
  eq(fechaBuena.ultima, '2026-10-01', 'la última jornada es la última fecha válida');
  const medio = C.baseTrabajadores([], [{ nombre: 'Gus', nombres_anteriores: ['Gus1', 5, ''] }, { nombre: 'Hana', nombres_anteriores: [] },
    { nombre: 'Ivo', fusionados: ['X', null] }]);
  eq(medio.personas.map(p => [p.nombre, p.anteriores, p.fusionados]), [['Gus', ['Gus1'], []], ['Hana', [], []], ['Ivo', [], ['X']]],
    'un historial a medias enseña lo que se puede leer');
  eq(medio.avisos.historialIlegible, ['Gus', 'Ivo'], 'y avisa de quién lo tiene a medias (un historial vacío es normal y no avisa)');
  const sinObra = C.baseTrabajadores([{ nombre: 'Y', fecha: '2026-10-01', horas: 2 }], []).personas[0];
  eq([sinObra.horas, sinObra.obras], [2, []], 'una fila sin obra suma horas pero no inventa una obra');
  const otraFicha = C.baseTrabajadores([{ obra: 'A', nombre: 'Zoe', fecha: '2026-10-01', horas: 2, empresa: 'Acme' }], []).personas[0];
  eq([otraFicha.sinFicha, otraFicha.empresa], [true, 'Acme'], 'sin ficha en la base, la empresa se toma de sus jornadas');
}

function enNavegadorSimulado() {
  const src = fs.readFileSync(RUTA, 'utf8');
  const ctx = { window: {}, console };
  vm.createContext(ctx);
  try { vm.runInContext(src, ctx); } catch (e) { ok(false, 'no se ejecuta en un contexto de navegador simulado: ' + e.message); }
  const W = ctx.window.PersonalCalculo;
  ok(W && typeof W.baseTrabajadores === 'function' && typeof W.ordenarBase === 'function', 'no publica window.PersonalCalculo.baseTrabajadores y ordenarBase');
  if (W && W.baseTrabajadores) {
    eq(JSON.parse(JSON.stringify(W.baseTrabajadores(FILAS, CATALOGO))), JSON.parse(JSON.stringify(cargar().baseTrabajadores(FILAS, CATALOGO))),
      'resultado distinto en contexto navegador');
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
