'use strict';
/* Verificador de la suma por empresa de P2 (personal_calculo.js, paso 08c2b). Exit 0 = todo bien.
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
function cerca(a, b, msg) { ok(typeof a === 'number' && Math.abs(a - b) < 1e-9, msg + ' | esperado ' + b + ' | obtenido ' + a); }

function cargar() {
  try { return require(RUTA); } catch (e) { console.log('FALLO: no carga como módulo CommonJS: ' + e.message); process.exit(1); }
}

// Jornadas inventadas. Cada comentario dice qué debe pasar.
const R = [
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-19', nombre: 'Carla', horas: 8,   extra: 0, empresa: 'CATERSYSTEM' },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-20', nombre: 'Carla', horas: 8,   extra: 0, empresa: 'Catersystem' },   // otra grafía: misma empresa
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-19', nombre: 'Ana',   horas: 7.5, extra: 0, empresa: 'Manueles' },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-20', nombre: 'Ana',   horas: 7.5, extra: 0, empresa: 'Manueles' },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-19', nombre: 'Beto',  horas: 7.5, extra: 0, empresa: 'Manueles' },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-19', nombre: 'Dani',  horas: 6,   extra: 0, empresa: 'Dani @AUT' },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-20', nombre: 'Eli',   horas: 4,   extra: 0, empresa: 'Eli@aut' },
  { obra: 'A', ambito: 'vivienda', fecha: '2026-10-19', nombre: 'Fran',  horas: 7.5, extra: 0, empresa: '' },
  { obra: 'B', ambito: 'garaje',   fecha: '2026-10-19', nombre: 'Fran',  horas: 2,   extra: 0 }                             // sin la clave: sin empresa
];
// Resultado esperado a mano: horas 22,5 + 16 + 6 + 4 + 9,5 = 58; 6 personas; días de persona 3 + 2 + 1 + 1 + 1 = 8.
const ESPERADO = [
  { nombre: 'Manueles',    sinEmpresa: false, autonomo: false, personas: 2, dias: 3, horas: 22.5, pct: 100 * 22.5 / 58 },
  { nombre: 'CATERSYSTEM', sinEmpresa: false, autonomo: false, personas: 1, dias: 2, horas: 16,   pct: 100 * 16 / 58 },
  { nombre: 'Dani @AUT',   sinEmpresa: false, autonomo: true,  personas: 1, dias: 1, horas: 6,    pct: 100 * 6 / 58 },
  { nombre: 'Eli@aut',     sinEmpresa: false, autonomo: true,  personas: 1, dias: 1, horas: 4,    pct: 100 * 4 / 58 },
  { nombre: 'Sin empresa', sinEmpresa: true,  autonomo: false, personas: 1, dias: 1, horas: 9.5,  pct: 100 * 9.5 / 58 }
];

function resumir(l) { return { nombre: l.nombre, sinEmpresa: l.sinEmpresa, autonomo: l.autonomo, personas: l.personas, dias: l.dias, horas: l.horas }; }

function pruebas(C) {
  const necesarias = ['agregar', 'ranking', 'agregarPorEmpresa', 'esAutonomo', 'textoAvisoEmpresas', 'htmlPorEmpresa'];
  necesarias.forEach(f => ok(typeof C[f] === 'function', 'falta la función ' + f));
  if (necesarias.some(f => typeof C[f] !== 'function')) return;

  const copiaR = JSON.stringify(R);
  const r = C.agregarPorEmpresa(R);

  // --- el desglose del ejemplo, a mano
  eq(r.empresas.map(resumir), ESPERADO.map(resumir), 'líneas por empresa (orden: más horas primero, «Sin empresa» al final)');
  r.empresas.forEach((l, i) => cerca(l.pct, ESPERADO[i].pct, '% de ' + ESPERADO[i].nombre));
  eq(r.total, { personas: 6, dias: 8, horas: 58 }, 'total general (sin contar dos veces los autónomos)');
  const pctSuma = r.empresas.reduce((s, l) => s + l.pct, 0);
  cerca(pctSuma, 100, 'los % de las líneas suman 100 (no 100 + los autónomos)');
  cerca(r.empresas.reduce((s, l) => s + l.horas, 0), r.total.horas, 'las horas de las líneas suman el total');
  ok(r.autonomos && r.autonomos.etiqueta === 'Total autónomos (@AUT)', 'la línea de autónomos se llama «Total autónomos (@AUT)»');
  eq(r.autonomos && { personas: r.autonomos.personas, dias: r.autonomos.dias, horas: r.autonomos.horas },
    { personas: 2, dias: 2, horas: 10 }, 'total de autónomos = Dani + Eli');
  cerca(r.autonomos && r.autonomos.pct, 100 * 10 / 58, '% del total de autónomos');
  eq(r.avisos, { variasEmpresas: [] }, 'sin avisos cuando cada persona tiene una sola empresa');
  eq(JSON.stringify(R), copiaR, 'agregarPorEmpresa no cambia las filas que recibe');

  // --- coherencia con la suma por persona de siempre
  const g = C.agregar(R);
  cerca(r.total.horas, g.total.horas, 'las mismas horas totales que agregar');
  eq(r.total.personas, g.total.trabajadores, 'las mismas personas que agregar');
  eq(r.total.dias, g.trabajadores.reduce((s, t) => s + t.dias, 0), 'los días de persona suman los de cada trabajador');

  // --- agregar enseña la empresa de cada persona solo si la tiene (la forma antigua no cambia)
  const por = {}; g.trabajadores.forEach(t => { por[t.nombre] = t; });
  eq(por.Ana.empresa, 'Manueles', 'Ana lleva su empresa');
  eq(por.Carla.empresa, 'CATERSYSTEM', 'Carla lleva la grafía de su primera fila');
  ok(!('empresa' in por.Fran), 'quien no tiene empresa no lleva la clave (forma antigua intacta)');
  ok(C.ranking(R, { periodo: 'obra', ref: '2026-10-20' }).trabajadores.some(t => t.nombre === 'Dani' && t.empresa === 'Dani @AUT'), 'ranking también enseña la empresa');

  // --- obra sin ninguna empresa: una sola línea «Sin empresa» con el 100 %
  const sinNada = C.agregarPorEmpresa([
    { fecha: '2026-10-19', ambito: 'vivienda', nombre: 'Ana', horas: 7.5, extra: 0 },
    { fecha: '2026-10-19', ambito: 'vivienda', nombre: 'Beto', horas: 7.5, extra: 0 }
  ]);
  eq(sinNada.empresas.map(resumir), [{ nombre: 'Sin empresa', sinEmpresa: true, autonomo: false, personas: 2, dias: 2, horas: 15 }], 'sin empresas: solo «Sin empresa»');
  cerca(sinNada.empresas[0].pct, 100, 'sin empresas: 100 %');
  eq(sinNada.autonomos, null, 'sin autónomos no hay línea de autónomos');

  // --- sin datos no es lo mismo que cero
  eq(C.agregarPorEmpresa([]), { empresas: [], autonomos: null, total: null, avisos: { variasEmpresas: [] } }, 'sin filas');
  eq(C.agregarPorEmpresa(null).total, null, 'lo que no es lista: sin total');
  const malas = [{ fecha: '2026-10-19', nombre: 'Ana', horas: null, empresa: 'X' }, { fecha: '2026-10-19', nombre: 'Ana', horas: 30, empresa: 'X' },
    { fecha: '2026-10-19', nombre: '', horas: 5, empresa: 'X' }, null];
  eq(C.agregarPorEmpresa(malas).total, null, 'filas no válidas: no hay total (no es 0)');
  eq(C.agregarPorEmpresa(R.concat(malas)).empresas.map(resumir), ESPERADO.map(resumir), 'las filas no válidas se ignoran igual que en agregar');

  // --- grafías, «Sin empresa» escrito a mano y nombres raros de empresa
  const grafias = C.agregarPorEmpresa([
    { fecha: '2026-10-19', nombre: 'Ana', horas: 8, empresa: 'Cafeteria  Ñandú' },
    { fecha: '2026-10-19', nombre: 'Beto', horas: 8, empresa: ' cafetería ñandú ' },
    { fecha: '2026-10-19', nombre: 'Carla', horas: 8, empresa: 'SIN EMPRESA' },
    { fecha: '2026-10-19', nombre: 'Dani', horas: 8 }
  ]);
  eq(grafias.empresas.map(l => [l.nombre, l.personas]), [['Cafeteria Ñandú', 2], ['Sin empresa', 2]], 'sin tildes ni mayúsculas ni espacios de más; «Sin empresa» escrito también es sin empresa');
  const raros = C.agregarPorEmpresa([
    { fecha: '2026-10-19', nombre: 'Ana', horas: 1, empresa: '__proto__' },
    { fecha: '2026-10-19', nombre: 'Beto', horas: 2, empresa: 'constructor' },
    { fecha: '2026-10-19', nombre: 'Carla', horas: 3, empresa: 'toString' }
  ]);
  eq(raros.empresas.map(l => [l.nombre, l.horas]), [['toString', 3], ['constructor', 2], ['__proto__', 1]], 'nombres de empresa que parecen propiedades de objeto');
  eq(raros.total.horas, 6, 'y el total sigue bien');

  // --- empate de horas: por nombre; cero horas: sin % (no NaN)
  const empate = C.agregarPorEmpresa([
    { fecha: '2026-10-19', nombre: 'Ana', horas: 5, empresa: 'Beta' }, { fecha: '2026-10-19', nombre: 'Beto', horas: 5, empresa: 'alfa' }]);
  eq(empate.empresas.map(l => l.nombre), ['alfa', 'Beta'], 'con las mismas horas, por orden alfabético');
  const ceros = C.agregarPorEmpresa([{ fecha: '2026-10-19', nombre: 'Ana', horas: 0, empresa: 'X' }]);
  eq(ceros.empresas[0].pct, null, 'con 0 horas en total el % no existe (no es NaN)');

  // --- una persona con dos empresas: se avisa y las horas no se cuentan de menos ni de más
  const dos = C.agregarPorEmpresa([
    { fecha: '2026-10-19', nombre: 'Ana', horas: 7.5, empresa: 'Manueles' },
    { fecha: '2026-10-20', nombre: 'Ana', horas: 7.5, empresa: 'CATERSYSTEM' },
    { fecha: '2026-10-20', nombre: 'Beto', horas: 7.5, empresa: 'CATERSYSTEM' }]);
  eq(dos.avisos.variasEmpresas, ['Ana'], 'se avisa de quien sale con dos empresas');
  eq(dos.total, { personas: 2, dias: 3, horas: 22.5 }, 'el total cuenta a la persona una sola vez');
  cerca(dos.empresas.reduce((s, l) => s + l.horas, 0), 22.5, 'las horas siguen sumando el total');
  ok(C.textoAvisoEmpresas(dos).indexOf('Ana') >= 0, 'el texto del aviso dice quién');
  eq(C.textoAvisoEmpresas(r), '', 'sin aviso, texto vacío');
  ok(/dos|más de una/.test(C.textoAvisoEmpresas(dos)), 'el texto del aviso está en llano');
  const trabDos = C.agregar([{ fecha: '2026-10-19', nombre: 'Ana', horas: 7.5, empresa: 'Manueles' }, { fecha: '2026-10-20', nombre: 'Ana', horas: 7.5, empresa: 'CATERSYSTEM' }]).trabajadores[0];
  eq(trabDos.empresa, 'CATERSYSTEM', 'si una persona tiene dos, se enseña la de su fila más reciente');

  // --- una persona con dos empresas @AUT cuenta una sola vez (persona y día) en el total de autónomos
  const dosAut = C.agregarPorEmpresa([
    { fecha: '2026-10-19', nombre: 'Ana', horas: 4, empresa: 'Ana @AUT' },
    { fecha: '2026-10-19', nombre: 'Ana', horas: 6, empresa: 'Zeta@aut' },
    { fecha: '2026-10-20', nombre: 'Ana', horas: 2, empresa: 'Ana @AUT' }]);
  eq(dosAut.autonomos && { personas: dosAut.autonomos.personas, dias: dosAut.autonomos.dias, horas: dosAut.autonomos.horas },
    { personas: 1, dias: 2, horas: 12 }, 'una persona en dos empresas @AUT cuenta una vez en el total de autónomos');
  eq(dosAut.total, { personas: 1, dias: 2, horas: 12 }, 'y en el total general también');
  eq(dosAut.empresas.map(l => [l.nombre, l.personas, l.dias, l.horas]), [['Ana @AUT', 1, 2, 6], ['Zeta@aut', 1, 1, 6]],
    'cada línea @AUT cuenta lo suyo (empate de horas: por orden alfabético)');

  // --- quién es autónomo (la misma regla que P1: acaba en @AUT, sin mirar mayúsculas ni espacios)
  ['Javi @AUT', 'Javi@aut', 'JAVI @ AUT ', 'Javi @AuT', '@AUT'].forEach(t => ok(C.esAutonomo(t) === true, 'es autónomo: ' + JSON.stringify(t)));
  ['AUT', 'Autónomos SL', '@AUT SL', 'Javi AUT', 'Javi @AUTO', '', null, undefined, 5, 'Sin empresa'].forEach(t => ok(C.esAutonomo(t) === false, 'NO es autónomo: ' + JSON.stringify(t)));

  // --- el bloque HTML «Por empresa» (el mismo en los cuatro sitios): celdas esperadas escritas a mano
  const filasDe = html => (html.match(/<tr[^>]*>.*?<\/tr>/g) || []).map(tr => (tr.match(/<t[dh][^>]*>.*?<\/t[dh]>/g) || []).map(td => td.replace(/<[^>]*>/g, '')));
  const bloque = C.htmlPorEmpresa(r, { bloque: 'b', titulo: 't', scroll: 's', tabla: 'tb', nota: 'n', aviso: 'a' });
  eq(filasDe(bloque), [
    ['Empresa', 'Personas', 'Días', 'Horas', '% impacto'],
    ['Manueles', '2', '3', '22,5', '38,8 %'],
    ['CATERSYSTEM', '1', '2', '16', '27,6 %'],
    ['Dani @AUT', '1', '1', '6', '10,3 %'],
    ['Eli@aut', '1', '1', '4', '6,9 %'],
    ['Sin empresa', '1', '1', '9,5', '16,4 %'],
    ['Total', '6', '8', '58', '100 %'],
    ['Total autónomos (@AUT)', '2', '2', '10', '17,2 %']
  ], 'tabla «Por empresa» (cifras a mano)');
  ok(/<h4 class="t">Por empresa<\/h4>/.test(bloque) && /<table class="tb">/.test(bloque) && /<div class="s">/.test(bloque) && /<p class="n">/.test(bloque), 'el bloque lleva las clases que le da cada sitio');
  ok(/<tbody>(?:(?!<\/tbody>).)*Sin empresa(?:(?!<\/tbody>).)*<\/tbody>/.test(bloque) && bloque.indexOf('Sin empresa</td>') > bloque.indexOf('Eli@aut</td>'), '«Sin empresa» va al final de la tabla');
  ok(bloque.indexOf('Total autónomos') > bloque.indexOf('<tfoot>') && bloque.indexOf('Total autónomos') > bloque.indexOf('>Total<'), 'el total de autónomos va debajo del total, no entre las líneas');
  ok(/data-por-empresa/.test(bloque), 'el bloque se puede localizar (data-por-empresa)');
  ok(bloque.indexOf('no se suman otra vez') > 0 && bloque.indexOf('todavía no se les ha puesto empresa') > 0, 'la nota explica el total de autónomos y «Sin empresa»');
  ok(C.htmlPorEmpresa(sinNada, {}).indexOf('Total autónomos') < 0 && C.htmlPorEmpresa(sinNada, {}).indexOf('no se suman otra vez') < 0, 'sin autónomos no hay línea ni nota de autónomos');
  eq(filasDe(C.htmlPorEmpresa(sinNada, {})).slice(1), [['Sin empresa', '2', '2', '15', '100 %'], ['Total', '2', '2', '15', '100 %']], 'obra sin empresas: solo «Sin empresa» y el total');
  eq(C.htmlPorEmpresa(C.agregarPorEmpresa([]), {}), '', 'sin datos no hay bloque');
  eq(C.htmlPorEmpresa(null, {}), '', 'sin resultado no hay bloque');
  ok(C.htmlPorEmpresa(r).indexOf('undefined') < 0 && C.htmlPorEmpresa(r, null).indexOf('undefined') < 0, 'sin clases no se escribe «undefined»');
  const peligro = C.htmlPorEmpresa(C.agregarPorEmpresa([{ fecha: '2026-10-19', nombre: 'Ana', horas: 8, empresa: '<b>x</b> & "y"' }]), {});
  ok(peligro.indexOf('<b>x</b>') < 0 && peligro.indexOf('&lt;b&gt;x&lt;/b&gt; &amp; &quot;y&quot;') > 0, 'el nombre de una empresa se escapa');
  ok(C.htmlPorEmpresa(dos, {}).indexOf('Hay una persona con más de una empresa (Ana)') > 0, 'el aviso de dos empresas sale en el bloque');
  ok(C.htmlPorEmpresa(r, {}).indexOf('Hay ') < 0, 'sin avisos el bloque no lleva aviso');

  // --- mismo resultado en un navegador simulado, sin dependencias
  const src = fs.readFileSync(RUTA, 'utf8');
  const ctx = { window: {}, console: console };
  vm.createContext(ctx);
  try { vm.runInContext(src, ctx); } catch (e) { ok(false, 'no se ejecuta en un contexto de navegador simulado: ' + e.message); }
  ok(ctx.window.PersonalCalculo && typeof ctx.window.PersonalCalculo.agregarPorEmpresa === 'function', 'no publica window.PersonalCalculo.agregarPorEmpresa');
  if (ctx.window.PersonalCalculo && ctx.window.PersonalCalculo.agregarPorEmpresa) {
    eq(JSON.parse(JSON.stringify(ctx.window.PersonalCalculo.agregarPorEmpresa(R))), JSON.parse(JSON.stringify(r)), 'resultado distinto en contexto navegador');
  }
  ok(!/\bnormalize\s*\(\s*['"]NFKD/.test(src), 'la comparación sin tildes usa NFD como la tablet');
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
