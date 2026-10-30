# -*- coding: utf-8 -*-
"""La tablet «Personal en obra» con histórico de meses, y los patrones de DNI/teléfono sin «lookbehind» (MA1).

Dos fallos de la auditoría del 30/10/2026, y lo que impide que vuelvan:

F1 · El rendimiento. Cada repintado de «Anotar» volvía a leer TODO el histórico una vez por persona de la
lista (y cada lectura reordenaba el catálogo por fila): con 6 meses de 4 obras (≈ 7.000 filas) un toque en
«+/−» tardaba ~27 s en un PC. Ahora el histórico se lee una vez por repintado (`conMemoria`) y esa memoria se
tira al terminar, así que no hay caché vieja posible. Aquí se comprueba, con datos INVENTADOS y la fecha fija
del 23/10/2026:
  · escenas: lo que pinta la tablet con memoria es igual, carácter a carácter, que sin ella, tras cambiar de
    obra, fecha o ámbito, guardar, anular, corregir un nombre, unir dos personas o cargar una lista nueva;
  · verdad: respuestas conocidas a mano (nombre tal como consta, aviso de doble obra, avisos al guardar), que
    no dependen de comparar dos caminos del mismo código;
  · estructura: el número de filas del histórico que se leen no depende de cuántas personas hay en la lista;
  · tiempo: 6 meses de histórico se repintan en menos de 1,5 s (la meta era 0,3 s; el código viejo, 27 s).

F6 · Safari anterior a 16.4 no entiende «lookbehind» y, si una expresión no compila, el script entero no
carga. personal_sagarde.html lo usaba en tres expresiones; ahora no, y se comprueba que dicen lo mismo que las
de antes con ~50.000 cadenas.

Hace falta node. Sin node las pruebas de la tablet se SALTAN y lo dicen: nadie comprobaría nada. Para probar una
copia (p. ej. con un fallo puesto a propósito) apunta SAGARDE_MOTOR_PERSONAL a la carpeta que tenga
generador_personal.html, personal_sagarde.html y personal_calculo.js."""
import json
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
_MOTOR = Path(os.environ.get("SAGARDE_MOTOR_PERSONAL") or _TESTS.parent)  # _SISTEMA INFORME SAGARDE IA
_NODE = shutil.which("node")
_FICHEROS = ("generador_personal.html", "personal_sagarde.html", "personal_calculo.js")

# El verificador de node va dentro de esta prueba (y no en un .js suelto) para no tocar la lista blanca de
# .gitignore: un .js nuevo dentro de tests/ se generaría y nunca se publicaría. Se lanza por la entrada
# estándar: node - <carpeta del motor> <modo>.
_JS = r'''
// Arnés de la tablet «Personal en obra» (MA1): ejecuta el script de generador_personal.html en un vm con un
// DOM falso que RECUERDA lo que se pinta, con datos INVENTADOS y fecha fija. Solo lee los ficheros del motor.
//   cargar(motor, almacenInicial) -> { ctx, A }   (A = funciones y variables del script de la tablet)
//   datos(opciones) -> estado inventado {catalogo, obras}
process.env.TZ = 'Europe/Madrid';
const fs = require('fs'), vm = require('vm'), path = require('path'), crypto = require('crypto');

const FIJO = new Date('2026-10-23T09:00:00+02:00').getTime();
class FechaFija extends Date {
  constructor(...x) {
    if (x.length === 0) super(FIJO);
    else super(...x);
  }
  static now() {
    return FIJO;
  }
}

function cargar(motor, almacenInicial) {
  const html = fs.readFileSync(path.join(motor, 'generador_personal.html'), 'utf8');
  const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
  const principal = scripts.find((s) => s.includes("'use strict'"));
  if (!principal) throw new Error('no se encuentra el script principal de la tablet');
  const store = Object.assign({}, almacenInicial || {});
  const ls = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; },
  };
  const elementos = new Map();
  const nuevoElemento = () => ({
    classList: { add() {}, remove() {}, toggle() {} }, style: {}, dataset: {}, value: '',
    querySelector: () => null, querySelectorAll: () => [], appendChild() {}, addEventListener() {}, focus() {},
    set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h || ''; },
    set textContent(v) { this._t = v; }, get textContent() { return this._t || ''; },
    set hidden(v) { this._hid = v; }, get hidden() { return !!this._hid; },
  });
  const elemento = (sel) => {
    if (!elementos.has(sel)) elementos.set(sel, nuevoElemento());
    return elementos.get(sel);
  };
  const ctx = {
    console, localStorage: ls, Date: FechaFija, Math, JSON, Set, Map, Promise, performance, Intl,
    setTimeout: () => 0, clearTimeout: () => 0,
    document: {
      addEventListener() {}, querySelector: (sel) => elemento(sel), querySelectorAll: () => [],
      createElement: () => nuevoElemento(), head: nuevoElemento(), body: nuevoElemento(), referrer: '',
    },
    matchMedia: () => ({ matches: true }), location: { href: '' },
    URL: { createObjectURL: () => '', revokeObjectURL() {} }, Blob: function () {},
  };
  ctx.window = ctx;
  ctx.addEventListener = () => {};
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(motor, 'personal_calculo.js'), 'utf8'), ctx);
  const opcional = (n) => `${n}: (typeof ${n} === 'function' ? ${n} : null)`;
  const codigo =
    'var __toasts=[];' + principal.replace('function toast(s) {', 'function toast(s) { __toasts.push(s);') +
    '\n;this.__A={save,addName,horarioDe,ultimoHorarioDe,jk,cat,canon,rowsHTML,loadList,render,appView,infoView,' +
    'jornadasView,enviarView,pub,filasDeTodasLasObras,buscarCoincidenciasOtrasObras,opcionesHTML,rotuloDobleObraHTML,' +
    'renombrar,armarFichero,toastLog:()=>__toasts,get a(){return a},get state(){return state},setState(s){state=s},' +
    'set pending(v){pending=v},get pending(){return pending},set news(v){news=v},get news(){return news},' +
    'set publicados(v){publicados=v},' + [opcional('rowsHTMLSinMemoria'), opcional('renderSinMemoria'), opcional('conMemoria')].join(',') + '};';
  vm.runInContext(codigo, ctx, { timeout: 60000 });
  return { ctx, A: ctx.__A, elemento, store };
}

// ---- datos inventados --------------------------------------------------------------------------------
const NOMBRES = ['Aitor Zubi', 'Bruno', 'Carlos', 'Dario', 'Edorta', 'Fermin', 'Gaizka', 'Hector', 'Iker', 'Jon',
  'Koldo', 'Lander', 'Mikel', 'Nerea', 'Oier', 'Pablo', 'Quim', 'Raul', 'Sergio', 'Txomin', 'Unai', 'Victor',
  'Xabier', 'Yago', 'Zigor', 'Álvaro', 'Íñigo Prueba', 'Ángel', 'Beñat', 'Ibon', 'Javi Uno', 'Javi Dos'];
const EMPRESAS = ['', 'Sagarde', 'Instalaciones Norte', 'Montajes Ruiz'];
const OBRAS = ['obra-alfa', 'obra-beta', 'obra-gama', 'obra-delta'];

function azar(semilla) {
  let s = semilla >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}
const dos = (n) => String(n).padStart(2, '0');
function diasLaborables(desde, hasta) {
  const fechas = [];
  for (let t = Date.UTC(...desde); t <= Date.UTC(...hasta); t += 864e5) {
    const d = new Date(t);
    if (d.getUTCDay() >= 1 && d.getUTCDay() <= 5) fechas.push(d.getUTCFullYear() + '-' + dos(d.getUTCMonth() + 1) + '-' + dos(d.getUTCDate()));
  }
  return fechas;
}

// opciones: {fechas:[...], obras:n, personas:n por jornada, catalogo:n, semilla}
function datos(op) {
  const { fechas, obras = 4, personas = 6, catalogo = 24, semilla = 7, ambitos = ['vivienda', 'garaje'] } = op;
  const rnd = azar(semilla);
  const nombres = [];
  for (let i = 0; i < catalogo; i++) nombres.push(i < NOMBRES.length ? NOMBRES[i] : 'Operario ' + (i + 1));
  const cat = nombres.map((n, i) => ({ id: 'T' + String(i + 1).padStart(4, '0'), nombre: n, categoria: '', empresa: EMPRESAS[i % 4], activo: true }));
  const estado = { version: 1, generado: '2026-10-22T20:00:00+02:00', jornada_base_h: 7.5, catalogo: cat, obras: {} };
  OBRAS.forEach((id, oi) => {
    estado.obras[id] = {
      nombre: 'Obra ' + id.split('-')[1].toUpperCase(), cerrada: false,
      horario_semanal: { lun: 7.5, mar: 7.5, mie: 7.5, jue: 7.5, vie: 7.5, sab: 0, dom: 0 },
      excepciones_horario: oi === 0 ? { Bruno: { lun: 8, mar: 8, mie: 8, jue: 8, vie: 6 } } : {},
      ultima: { vivienda: null, garaje: null }, jornadas: [],
    };
    if (oi >= obras) return;
    const o = estado.obras[id];
    fechas.forEach((f) => {
      ambitos.forEach((amb, ai) => {
        const n = ai === 0 ? personas : Math.max(1, Math.floor(personas / 3));
        const elegidos = new Set();
        while (elegidos.size < n) elegidos.add(Math.floor(rnd() * catalogo));
        [...elegidos].sort((x, y) => x - y).forEach((i) => {
          const horas = [7.5, 7.5, 7.5, 8, 6, 9][Math.floor(rnd() * 6)];
          o.jornadas.push({ ambito: amb, fecha: f, nombre: nombres[i], horas, extra: Math.max(0, horas - 7.5) });
        });
      });
    });
  });
  // La misma persona en dos obras el mismo día (aviso de doble obra), con la fecha de las escenas
  const f = fechas[fechas.length - 1];
  [['obra-alfa', 'Aitor Zubi'], ['obra-beta', 'Aitor Zubi']].forEach(([id, n]) => {
    const o = estado.obras[id];
    o.jornadas = o.jornadas.filter((x) => !(x.fecha === f && x.ambito === 'vivienda' && x.nombre === n));
    o.jornadas.push({ ambito: 'vivienda', fecha: f, nombre: n, horas: 4, extra: 0 });
  });
  return estado;
}

const sha = (t) => crypto.createHash('sha256').update(t).digest('hex').slice(0, 16);

// ======================= verificador (se ejecuta con: node - <carpeta del motor> <modo>) =======================
// Modos: escenas · verdad · estructura · tiempo · patrones.  Cada uno imprime {fallos:[...], datos:{...}} en una línea.
const fs2 = require('fs'), path2 = require('path');
const motor = process.argv[2], modo = process.argv[3];
const ms = (f, n) => { const t = process.hrtime.bigint(); for (let i = 0; i < n; i++) f(); return Number(process.hrtime.bigint() - t) / 1e6 / n; };
const mejor = (f, n) => { let m = Infinity; for (let i = 0; i < n; i++) m = Math.min(m, ms(f, 1)); return m; };
const MES = (desde) => diasLaborables(desde, [2026, 9, 22]);

function nuevaTablet(estado, almacen) {
  const t = cargar(motor, almacen || {});
  t.A.setState(JSON.parse(JSON.stringify(estado)));
  return t;
}

// ---- 1. escenas: lo pintado con memoria de repintado es idéntico a lo pintado sin ella ----------------------
function modoEscenas() {
  const fallos = [];
  const fechas = diasLaborables([2026, 9, 7], [2026, 9, 22]);
  const estado = datos({ fechas, obras: 4, personas: 6, catalogo: 24, semilla: 11 });
  const ultimo = fechas[fechas.length - 1];
  const almacen = {
    sgd_personal_nuevos: JSON.stringify(['Íñigo Prueba', 'Recien Llegado']),
    sgd_personal_ultimas_horas: JSON.stringify({ dario: 9, 'recien llegado': 6 }),
  };
  const { A, elemento } = nuevaTablet(estado, almacen);
  const a = A.a;
  if (!A.rowsHTMLSinMemoria || !A.renderSinMemoria) return { fallos: ['faltan rowsHTMLSinMemoria / renderSinMemoria: no hay con qué comparar'], datos: {} };
  A.publicados = new Set(estado.catalogo.map((x) => x.nombre.toLowerCase()));
  const vistas = () => Object.fromEntries(['app', 'jornadas', 'informe', 'enviar'].map((v) => [v, elemento('#v-' + v).innerHTML]));
  const escenas = [];
  function rec(nombre) {
    const con = A.rowsHTML();
    A.render();
    const vistasCon = vistas();
    const sin = A.rowsHTMLSinMemoria();
    A.renderSinMemoria();
    const vistasSin = vistas();
    if (con !== sin) fallos.push(`«${nombre}»: la lista de personas pintada con memoria no es igual que sin ella`);
    for (const v of Object.keys(vistasCon)) if (vistasCon[v] !== vistasSin[v]) fallos.push(`«${nombre}»: la vista «${v}» pintada con memoria no es igual que sin ella`);
    escenas.push({ nombre, filas: con.length, aviso: /aviso-doble-obra/.test(vistasCon.app), chips: (con.match(/warn-obra/g) || []).length });
  }
  const ir = (obra, amb, fecha, varias) => { Object.assign(a, { obra, amb, fecha, fechas: varias || [fecha], ren: null, hp: null }); A.loadList(); };
  const marcar = (n) => a.list.slice(0, n).forEach((p) => { p.on = true; });
  ir('obra-alfa', 'vivienda', ultimo); rec('base');
  ir('obra-alfa', 'vivienda', fechas[fechas.length - 2]); rec('otra fecha');
  ir('obra-alfa', 'garaje', ultimo); rec('garajes');
  ir('obra-beta', 'vivienda', ultimo); rec('otra obra (doble obra con alfa)');
  ir('obra-beta', 'vivienda', ultimo, fechas.slice(-3)); rec('varios días marcados');
  ir('obra-alfa', 'vivienda', ultimo); A.addName('Dario'); A.addName('Recien Llegado'); A.addName('Nadie Nuevo'); rec('añadir desde la base y uno nuevo');
  A.pending = [
    { obra: 'obra-alfa', ambito: 'vivienda', fecha: ultimo, anulada: false, notas: '', registrado: 'x',
      presentes: [{ nombre: 'INIGO prueba', horas: 8, extra: 0.5 }, { nombre: 'bruno', horas: 7.5, extra: 0 }, { nombre: 'Aitor Zubi', horas: 6, extra: 0 }] },
    { obra: 'obra-beta', ambito: 'vivienda', fecha: ultimo, anulada: true, presentes: [], notas: '', registrado: 'x' },
  ];
  ir('obra-alfa', 'vivienda', ultimo); rec('con jornadas sin enviar');
  ir('obra-gama', 'vivienda', ultimo); marcar(5); A.save(); rec('tras guardar');
  ir('obra-gama', 'vivienda', ultimo, fechas.slice(-2)); marcar(4); A.save(); rec('tras guardar dos días');
  A.pending = A.pending.filter((j) => A.jk(j) !== 'obra-alfa|vivienda|' + ultimo).concat([
    { obra: 'obra-alfa', ambito: 'vivienda', fecha: ultimo, anulada: true, presentes: [], notas: '', registrado: 'x' }]);
  ir('obra-alfa', 'vivienda', ultimo); rec('tras anular');
  ir('obra-beta', 'vivienda', ultimo);
  A.renombrar('Aitor Zubi', 'Aitor Zubieta', undefined); rec('tras renombrar');
  A.renombrar('Bruno', 'Carlos', undefined); rec('tras renombrar uniendo a dos personas');
  Object.assign(a, { v: 'informe', p: 'semana', scope: 'vivienda' }); rec('informe por semana');
  Object.assign(a, { p: 'anio', scope: 'garaje' }); rec('informe por año');
  Object.assign(a, { p: 'obra', scope: 'todo', v: 'jornadas' }); rec('informe por obra');
  const otro = datos({ fechas: fechas.slice(0, 8), obras: 3, personas: 5, catalogo: 20, semilla: 99 });
  otro.catalogo.reverse();
  A.setState(otro); A.news = ['Otro Nuevo'];
  ir('obra-beta', 'garaje', fechas[5]); rec('con una lista de obras y trabajadores nueva');
  // Un recuento de 0 es una alarma: si el aviso de doble obra nunca sale, las escenas no ejercitan nada
  if (escenas.length < 16) fallos.push('hay menos de 16 escenas: ' + escenas.length);
  if (escenas.filter((e) => e.aviso).length < 3) fallos.push('el aviso de doble obra sale en menos de 3 escenas: no se está ejercitando');
  if (escenas.filter((e) => e.chips > 0).length < 3) fallos.push('el chip «En otra obra hoy» sale en menos de 3 escenas: no se está ejercitando');
  if (escenas.some((e) => e.filas < 200)) fallos.push('alguna escena pinta una lista casi vacía');
  return { fallos, datos: { escenas: escenas.length } };
}

// ---- 2. verdad: respuestas conocidas a mano (no dependen de comparar dos caminos del mismo código) ---------------
function mini(jor, catalogo) {
  const est = { version: 1, generado: '2026-10-22T20:00:00+02:00', jornada_base_h: 7.5, catalogo: catalogo || [
    { id: 'T0001', nombre: 'Aitor Zubi', categoria: '', empresa: '', activo: true }, { id: 'T0002', nombre: 'Bruno', categoria: '', empresa: '', activo: true }], obras: {} };
  OBRAS.forEach((id) => {
    est.obras[id] = { nombre: id, cerrada: false, horario_semanal: { lun: 7.5, mar: 7.5, mie: 7.5, jue: 7.5, vie: 7.5, sab: 0, dom: 0 },
      excepciones_horario: {}, ultima: { vivienda: null, garaje: null },
      jornadas: (jor[id] || []).map(([f, amb, n, h]) => ({ ambito: amb, fecha: f, nombre: n, horas: h, extra: 0 })) };
  });
  return est;
}
function modoVerdad() {
  const fallos = [];
  const igual = (que, real, esperado) => { if (JSON.stringify(real) !== JSON.stringify(esperado)) fallos.push(`${que}: sale ${JSON.stringify(real)} y debería salir ${JSON.stringify(esperado)}`); };
  const D = '2026-10-20';
  // nombres: tal como constan, sin tildes ni mayúsculas; los nuevos también; un cambio se ve en el acto
  let t = nuevaTablet(mini({}), { sgd_personal_nuevos: JSON.stringify(['Íñigo Prueba']) });
  igual('nombre con otras mayúsculas', t.A.canon('bruno'), 'Bruno');
  igual('nombre sin tilde de la lista de nuevos', t.A.canon('INIGO prueba'), 'Íñigo Prueba');
  igual('nombre que no consta', t.A.canon('  Nadie   Nuevo '), 'Nadie Nuevo');
  t.A.news = ['Íñigo Prueba', 'Zeta Nuevo'];
  igual('nombre nuevo añadido después', t.A.canon('zeta nuevo'), 'Zeta Nuevo');
  t.A.setState(mini({}, [{ id: 'T1', nombre: 'Carla', categoria: '', empresa: '', activo: true }]));
  igual('lista de trabajadores cambiada después', t.A.canon('BRUNO'), 'BRUNO');
  igual('lista de trabajadores cambiada después (2)', t.A.canon('carla'), 'Carla');
  // doble obra: lo guardado en otra obra, lo pendiente que lo sustituye y lo anulado que lo quita
  const jor = { 'obra-beta': [[D, 'vivienda', 'AITOR ZUBI', 6]] };
  t = nuevaTablet(mini(jor));
  const busca = (obraActual, fecha) => t.A.buscarCoincidenciasOtrasObras('Aitor Zubi', fecha || D, obraActual).map((c) => c.obra + ':' + c.ambito + ':' + c.horas);
  igual('mismo día en otra obra', busca('obra-alfa'), ['obra-beta:vivienda:6']);
  igual('la propia obra no cuenta', busca('obra-beta'), []);
  igual('otro día no cuenta', busca('obra-alfa', '2026-10-21'), []);
  t.A.pending = [{ obra: 'obra-beta', ambito: 'vivienda', fecha: D, anulada: false, notas: '', registrado: 'x', presentes: [{ nombre: 'Aitor Zubi', horas: 3, extra: 0 }] }];
  igual('lo sin enviar sustituye a lo publicado', busca('obra-alfa'), ['obra-beta:vivienda:3']);
  t.A.pending = [{ obra: 'obra-beta', ambito: 'vivienda', fecha: D, anulada: true, notas: '', registrado: 'x', presentes: [] }];
  igual('lo anulado sin enviar quita lo publicado', busca('obra-alfa'), []);
  // las horas 0 (alguien apuntado sin trabajar) no cuentan como estar en otra obra
  const cero = nuevaTablet(mini({ 'obra-beta': [[D, 'vivienda', 'Aitor Zubi', 0]] }));
  igual('0 horas en otra obra no cuenta', cero.A.buscarCoincidenciasOtrasObras('Aitor Zubi', D, 'obra-alfa').length, 0);
  // con empresa (con mayúsculas y espacios) sigue saliendo el aviso: la empresa de la misma persona es la misma
  const conEmpresa = nuevaTablet(mini({ 'obra-beta': [[D, 'vivienda', 'Aitor Zubi', 6]] }, [
    { id: 'T0001', nombre: 'Aitor Zubi', categoria: '', empresa: 'Instalaciones Norte', activo: true }]));
  igual('con empresa también avisa de la doble obra', conEmpresa.A.buscarCoincidenciasOtrasObras('Aitor Zubi', D, 'obra-alfa').map((c) => c.obra), ['obra-beta']);
  // la lista de nombres (cat) y lo que se añade a la lista de hoy llevan el nombre tal como consta
  const nom = nuevaTablet(mini({}), { sgd_personal_nuevos: JSON.stringify(['Íñigo Prueba']) });
  igual('lista de nombres tal como constan, por orden', nom.A.cat(), ['Aitor Zubi', 'Bruno', 'Íñigo Prueba']);
  Object.assign(nom.A.a, { obra: 'obra-alfa', amb: 'vivienda', fecha: D, fechas: [D] }); nom.A.loadList();
  nom.A.addName('inigo PRUEBA');
  igual('añadir a alguien lo pone con su nombre de siempre', nom.A.a.list.filter((p) => p.on).map((p) => p.nombre), ['Íñigo Prueba']);
  // lo publicado con el nombre escrito de otra manera sale con el nombre de la lista
  igual('jornada publicada con otro formato de nombre', nuevaTablet(mini({ 'obra-beta': [[D, 'vivienda', 'AITOR  zubi', 6]] })).A.pub('obra-beta').map((x) => x.nombre), ['Aitor Zubi']);
  // jornadaOk admite una anulada con gente dentro (viene de un guardado de otra versión): cuenta como vacía
  t.A.pending = [{ obra: 'obra-beta', ambito: 'vivienda', fecha: D, anulada: true, notas: '', registrado: 'x', presentes: [{ nombre: 'Aitor Zubi', horas: 3, extra: 0 }] }];
  igual('una anulada cuenta como vacía aunque traiga gente', busca('obra-alfa'), []);
  t.A.pending = [{ obra: 'obra-gama', ambito: 'garaje', fecha: D, anulada: false, notas: '', registrado: 'x', presentes: [{ nombre: 'aitor zubi', horas: 5, extra: 0 }] }];
  igual('lo sin enviar de otra obra y otro ámbito también cuenta', busca('obra-alfa').sort(), ['obra-beta:vivienda:6', 'obra-gama:garaje:5']);
  igual('claves de las jornadas de todas las obras', [...t.A.filasDeTodasLasObras().keys()].sort(), ['obra-beta|vivienda|' + D, 'obra-gama|garaje|' + D]);
  // guardar: el aviso de más de 12 h y el rechazo de más de 24 h cuentan lo guardado en las otras obras
  const guardar = (horas, estado) => {
    const u = nuevaTablet(estado || mini({ 'obra-alfa': [[D, 'vivienda', 'Aitor Zubi', 4]] }));
    Object.assign(u.A.a, { obra: 'obra-gama', amb: 'vivienda', fecha: D, fechas: [D] });
    u.A.loadList();
    u.A.a.list = [{ nombre: 'Aitor Zubi', on: true, horas }];
    u.A.save();
    return { toast: u.A.toastLog().slice(-1)[0] || '', pendientes: u.A.pending.length };
  };
  let g = guardar(9);
  if (!/Aitor Zubi suma 13 h ese día/.test(g.toast) || g.pendientes !== 1) fallos.push('guardar 9 h con 4 h en otra obra debería avisar «suma 13 h» y guardar: ' + JSON.stringify(g));
  g = guardar(21);
  if (!/pasaría de 24 h/.test(g.toast) || g.pendientes !== 0) fallos.push('guardar 21 h con 4 h en otra obra debería rechazarse por pasar de 24 h: ' + JSON.stringify(g));
  // la copia de las filas es de quien la pide: borrarle claves no estropea lo que ve el resto del repintado
  t = nuevaTablet(mini({ 'obra-alfa': [[D, 'vivienda', 'Bruno', 7.5]], 'obra-beta': [[D, 'vivienda', 'Aitor Zubi', 6]] }));
  if (t.A.conMemoria) {
    const r = t.A.conMemoria(() => { const m = t.A.filasDeTodasLasObras(); const n = m.size; m.clear(); return [n, t.A.filasDeTodasLasObras().size]; });
    igual('quitar jornadas a la copia no toca la memoria del repintado', r, [2, 2]);
    // un fallo a mitad de un repintado no deja memoria vieja para el siguiente
    try { t.A.conMemoria(() => { t.A.canon('bruno'); t.A.filasDeTodasLasObras(); throw new Error('fallo de prueba'); }); } catch (e) { /* esperado */ }
    t.A.news = ['Recien Llegado'];
    t.A.pending = [{ obra: 'obra-gama', ambito: 'garaje', fecha: D, anulada: false, notas: '', registrado: 'x', presentes: [{ nombre: 'Bruno', horas: 5, extra: 0 }] }];
    igual('tras un fallo en un repintado, los nombres salen al día', t.A.canon('recien llegado'), 'Recien Llegado');
    igual('tras un fallo en un repintado, las filas salen al día', [...t.A.filasDeTodasLasObras().keys()].length, 3);
    // un render que revienta de verdad (falta personal_calculo.js) tampoco deja memoria
    const copia = t.ctx.PersonalCalculo; t.ctx.PersonalCalculo = undefined;
    Object.assign(t.A.a, { obra: 'obra-alfa', amb: 'vivienda', fecha: D, fechas: [D] }); t.A.loadList();
    let lanzo = false; try { t.A.render(); } catch (e) { lanzo = true; }
    t.ctx.PersonalCalculo = copia;
    t.A.news = ['Recien Llegado', 'Otro Mas'];
    igual('tras un render que falla, los nombres salen al día', t.A.canon('otro mas'), 'Otro Mas');
    if (!lanzo) fallos.push('el render sin personal_calculo.js debía fallar para probar esto, y no falló');
  } else fallos.push('falta conMemoria');
  return { fallos, datos: {} };
}

// ---- 3. estructura: el histórico se lee UNA vez por repintado, vengan 5 personas o 40 -------------------------
function modoEstructura() {
  const fallos = [];
  const estado = datos({ fechas: MES([2026, 8, 21]), obras: 3, personas: 8, catalogo: 60, semilla: 5 });
  const total = Object.values(estado.obras).reduce((s, o) => s + o.jornadas.length, 0);
  const { A, ctx } = nuevaTablet(estado);
  const a = A.a;
  Object.assign(a, { obra: 'obra-alfa', amb: 'vivienda', fecha: '2026-10-20', fechas: ['2026-10-20'] });
  A.loadList();
  const original = ctx.pub;
  let leidas = 0;
  ctx.pub = function (...x) { const r = original.apply(this, x); leidas += r.length; return r; };
  const nombres = A.cat();
  const medir = (n, f) => { a.list = nombres.slice(0, n).map((nombre) => ({ nombre, on: true, horas: null })); leidas = 0; f(); return leidas; };
  const r5 = medir(5, () => A.rowsHTML()), r40 = medir(40, () => A.rowsHTML());
  const p5 = medir(5, () => A.render()), p40 = medir(40, () => A.render());
  if (!r5) fallos.push('la prueba no ve ninguna lectura del histórico en rowsHTML (el contador no engancha)');
  if (r5 !== r40) fallos.push(`rowsHTML lee el histórico ${r5} veces con 5 personas y ${r40} con 40: debe ser lo mismo`);
  if (p5 !== p40) fallos.push(`render lee el histórico ${p5} veces con 5 personas y ${p40} con 40: debe ser lo mismo`);
  if (r40 > total) fallos.push(`rowsHTML lee ${r40} filas del histórico y solo hay ${total}: más de una vez`);
  if (p40 > 6 * total) fallos.push(`render lee ${p40} filas del histórico, más de 6 veces las ${total} que hay`);
  return { fallos, datos: { filas: total, rowsHTML_5: r5, rowsHTML_40: r40, render_5: p5, render_40: p40 } };
}

// ---- 4. tiempo: 6 meses de histórico en 4 obras (unas 7.000 filas) -------------------------------------------
function modoTiempo() {
  const fallos = [];
  const estado = datos({ fechas: MES([2026, 3, 20]), obras: 4, personas: 10, catalogo: 60, semilla: 5 });
  const total = Object.values(estado.obras).reduce((s, o) => s + o.jornadas.length, 0);
  const { A } = nuevaTablet(estado);
  const a = A.a;
  Object.assign(a, { obra: 'obra-alfa', amb: 'vivienda', fecha: '2026-10-20', fechas: ['2026-10-20'] });
  A.loadList();
  A.cat().slice(0, 18).forEach((x) => { if (!a.list.some((y) => y.nombre === x)) a.list.push({ nombre: x, on: true, horas: null }); });
  const lista = mejor(() => A.rowsHTML(), 3), completo = mejor(() => A.render(), 3);
  if (total < 6000) fallos.push('la prueba debía tener unas 7.000 filas y tiene ' + total);
  // La meta era 0,3 s; se da margen para un PC lento (el código sin memoria tardaba 27 s con esto)
  if (completo > 1500) fallos.push(`repintar todo con ${total} filas tarda ${completo.toFixed(0)} ms (máximo 1500)`);
  if (lista > 1500) fallos.push(`repintar la lista con ${total} filas tarda ${lista.toFixed(0)} ms (máximo 1500)`);
  return { fallos, datos: { filas: total, personas: a.list.length, lista_ms: +lista.toFixed(1), repintado_ms: +completo.toFixed(1) } };
}

// ---- 5. patrones de DNI / NIE / teléfono de personal_sagarde.html: iguales que los de antes (con lookbehind) --------
function modoPatrones() {
  const fallos = [];
  const VIEJOS = {
    PATRON_DNI: /(?<![A-Za-z0-9])\d{8}[- ]?[A-Za-z](?![A-Za-z0-9])/,
    PATRON_NIE: /(?<![A-Za-z0-9])[XYZxyz][- ]?\d{7}[- ]?[A-Za-z](?![A-Za-z0-9])/,
    PATRON_TEL: /(?<![\d.])(?:\+?34[\s.-]?)?[6789](?:[\s.-]?\d){8}(?!\d)/,
  };
  const html = fs2.readFileSync(path2.join(motor, 'personal_sagarde.html'), 'utf8');
  const NUEVOS = {};
  for (const n of Object.keys(VIEJOS)) {
    const m = html.match(new RegExp('var ' + n + ' = /(.+)/;'));
    if (!m) return { fallos: ['no encuentro ' + n + ' en personal_sagarde.html'], datos: {} };
    NUEVOS[n] = new RegExp(m[1]);
  }
  const nucleos = ['12345678Z', '12345678-Z', '12345678 Z', '12345678z', '1234567Z', '123456789Z', '12345678', 'Z12345678', '12345678ZZ',
    'X1234567L', 'x1234567l', 'Y-1234567-Z', 'Z 1234567 A', 'X123456L', 'X12345678L', 'XX1234567L', 'A1234567B',
    '600123456', '+34 600 123 456', '+34600123456', '34600123456', '34 600123456', '600.123.456', '600-123-456', '600 12 34 56',
    '6001234567', '60012345', '700123456', '800123456', '900123456', '123456789', '+34-700-123-456', '0034600123456',
    '(600) 123456', '1.600123456', '.600123456', '600123456.', '6 0 0 1 2 3 4 5 6', 'Aitor Zubi', 'Obra 12345', 'Oier (M)', 'Juan Carlos', '', ' '];
  const antes = ['', ' ', 'a', 'A', '1', '9', '.', '-', ',', '_', '+', 'Nombre ', 'ñ', 'é', '@', '\t', String.fromCharCode(160)];
  const despues = ['', ' ', 'a', 'A', '1', '9', '.', '-', ',', '_', '+', ' Perez', 'ñ', 'é', '@', '\t', String.fromCharCode(160)];
  const corpus = [];
  for (const n of nucleos) for (const p of antes) for (const s of despues) corpus.push(p + n + s);
  let semilla = 20261030;
  const rnd = () => { semilla = (Math.imul(semilla, 1664525) + 1013904223) >>> 0; return semilla / 4294967296; };
  const alfabeto = '0123456789 -.+AXYZaxyzbñé@_,()';
  for (let i = 0; i < 40000; i++) {
    let t = '';
    const largo = Math.floor(rnd() * 22);
    for (let j = 0; j < largo; j++) t += alfabeto[Math.floor(rnd() * alfabeto.length)];
    corpus.push(t);
  }
  const aciertos = {};
  for (const n of Object.keys(VIEJOS)) {
    aciertos[n] = 0;
    let distintos = 0;
    for (const t of corpus) {
      const v = VIEJOS[n].test(t), nu = NUEVOS[n].test(t);
      if (v) aciertos[n]++;
      if (v !== nu && ++distintos <= 3) fallos.push(`${n} y el de antes no coinciden con ${JSON.stringify(t)} (antes ${v}, ahora ${nu})`);
    }
    if (aciertos[n] < 100) fallos.push(`el corpus casi no ejercita ${n} (${aciertos[n]} coincidencias)`);
  }
  return { fallos, datos: { cadenas: corpus.length, coincidencias: aciertos } };
}

const MODOS = { escenas: modoEscenas, verdad: modoVerdad, estructura: modoEstructura, tiempo: modoTiempo, patrones: modoPatrones };
if (!MODOS[modo]) { console.log(JSON.stringify({ fallos: ['modo desconocido: ' + modo], datos: {} })); process.exit(2); }
try { console.log(JSON.stringify(MODOS[modo]())); } catch (e) { console.log(JSON.stringify({ fallos: ['la prueba ha reventado: ' + (e && e.stack ? e.stack.split('\n').slice(0, 4).join(' | ') : e)], datos: {} })); }
'''


def _correr(modo, tiempo_maximo=300):
    """Lanza el verificador de node en un modo y devuelve (fallos, datos)."""
    entorno = dict(os.environ, TZ="Europe/Madrid")
    p = subprocess.run([_NODE, "-", str(_MOTOR), modo], input=_JS.encode("utf-8"), capture_output=True,
                       timeout=tiempo_maximo, env=entorno)
    salida = p.stdout.decode("utf-8", "replace").strip().splitlines()
    error = p.stderr.decode("utf-8", "replace").strip()
    if not salida:
        return ["node no ha dado ninguna respuesta (código %s): %s" % (p.returncode, error[-600:])], {}
    try:
        respuesta = json.loads(salida[-1])
    except ValueError:
        return ["respuesta ilegible de node: %s" % salida[-1][:300]], {}
    return list(respuesta.get("fallos", [])), respuesta.get("datos", {})


@unittest.skipUnless(_NODE, "falta node en el PATH: NO se ha probado la tablet con histórico")
class TestTabletConHistorico(unittest.TestCase):
    def _sin_fallos(self, modo):
        fallos, datos = _correr(modo)
        self.assertEqual([], fallos, "\n" + "\n".join(fallos))
        return datos

    def test_lo_pintado_con_memoria_es_igual_que_sin_ella(self):
        datos = self._sin_fallos("escenas")
        self.assertGreaterEqual(datos.get("escenas", 0), 16)

    def test_respuestas_conocidas_a_mano(self):
        self._sin_fallos("verdad")

    def test_el_historico_se_lee_una_vez_por_repintado(self):
        datos = self._sin_fallos("estructura")
        self.assertGreater(datos.get("rowsHTML_5", 0), 0)  # un 0 sería que la prueba no ve nada

    def test_seis_meses_de_historico_se_repintan_rapido(self):
        datos = self._sin_fallos("tiempo")
        self.assertGreater(datos.get("filas", 0), 6000)


@unittest.skipUnless(_NODE, "falta node en el PATH: NO se han comparado los patrones")
class TestPatronesSinLookbehind(unittest.TestCase):
    def test_los_tres_patrones_dicen_lo_mismo_que_los_de_antes(self):
        fallos, datos = _correr("patrones")
        self.assertEqual([], fallos, "\n" + "\n".join(fallos))
        self.assertGreater(datos.get("cadenas", 0), 50000)

    def test_ningun_fichero_de_personal_usa_lookbehind(self):
        # Se busca la sintaxis tal cual (también en comentarios): un solo fallo de compilación en Safari < 16.4
        # deja el script entero sin cargar.
        for nombre in _FICHEROS:
            texto = (_MOTOR / nombre).read_text(encoding="utf-8")
            hallazgos = [(i + 1, l.strip()[:90]) for i, l in enumerate(texto.splitlines()) if re.search(r"\(\?<[=!]", l)]
            self.assertEqual([], hallazgos, "%s usa lookbehind (?<= o (?<!: %s" % (nombre, hallazgos))


if __name__ == "__main__":
    unittest.main()
