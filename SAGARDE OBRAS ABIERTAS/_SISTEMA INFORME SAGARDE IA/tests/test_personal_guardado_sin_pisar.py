# -*- coding: utf-8 -*-
"""Paso MA2: la lógica que decide qué avisos tiene cada día antes de guardar (planificarGuardado y aplicarDecision de
generador_personal.html). Es lógica pura: se saca del HTML tal cual está y se ejecuta con node contra unos 70 casos
escritos a mano (días con gente ya anotada, fin de semana, días futuros, personas con 0 horas, mezclas, repetidos, orden,
firma del aviso y decisiones). P3_APP apunta a otra copia de la app (para las mutaciones: se rompe una COPIA)."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

TESTS = Path(__file__).resolve().parent
APP_DIR = Path(os.environ.get("P3_APP") or TESTS.parent)

VERIFICADOR = r'''// Verificador OCULTO de planificar.js (MA2). Uso: node verif_plan.js <ruta a planificar.js>
// Una línea por cada caso que falla. Exit 0 = todo bien. Casos escritos a mano desde encargo.md (sin generarlos con código).
const fs = require('fs'), vm = require('vm');
const ruta = process.argv[2];
const texto = fs.readFileSync(ruta, 'utf8');
const ctx = {};
vm.createContext(ctx);
try {
  vm.runInContext(texto + '\n;this.__f={planificarGuardado,aplicarDecision};', ctx, { timeout: 5000 });
} catch (e) {
  console.log('FALLO no se puede cargar el fichero: ' + e.message);
  process.exit(1);
}
const { planificarGuardado, aplicarDecision } = ctx.__f;
const clonar = (x) => JSON.parse(JSON.stringify(x));
const igual = (x, y) => JSON.stringify(x) === JSON.stringify(y);
let fallos = 0, total = 0;
function caso(nombre, f) {
  total++;
  try {
    const r = f();
    if (r !== true && r !== undefined) { fallos++; console.log('FALLO ' + nombre + ' -> ' + r); }
  } catch (e) {
    fallos++;
    console.log('FALLO ' + nombre + ' -> excepción: ' + e.message);
  }
}
// día de entrada con valores por defecto: laborable, con horario, sin nadie
const dia = (fecha, extra) => Object.assign({ fecha, horarioObra: 7.5, existente: null, nuevas: [{ nombre: 'Ana', horas: 7.5 }] }, extra || {});
const exi = (origen, ...personas) => ({ origen, personas: personas.map(([nombre, horas]) => ({ nombre, horas })) });
const plan = (dias, hoy) => planificarGuardado({ hoy: hoy || '2026-10-23', dias });
const campos = ['fecha', 'accion', 'origen', 'anteriores', 'finde', 'futuro', 'sinHoras', 'avisos'];
const vista = (d) => { const o = {}; campos.forEach((c) => { o[c] = d[c]; }); return o; };
function esperaDia(nombre, entradaDia, esperado, hoy) {
  caso(nombre, () => {
    const p = plan([entradaDia], hoy);
    if (!p || !Array.isArray(p.dias) || p.dias.length !== 1) return 'el plan no tiene exactamente 1 día: ' + JSON.stringify(p);
    const v = vista(p.dias[0]);
    const e = Object.assign({ fecha: entradaDia.fecha, accion: 'nuevo', origen: null, anteriores: [], finde: false, futuro: false, sinHoras: [], avisos: [] }, esperado);
    if (!igual(v, e)) return 'esperado ' + JSON.stringify(e) + ' obtenido ' + JSON.stringify(v);
  });
}

// ---- A. acción (nuevo / igual / sustituye) ----
esperaDia('A01 día vacío (existente null) = nuevo', dia('2026-10-22'), {});
esperaDia('A02 existente sin personas = nuevo, origen null', dia('2026-10-22', { existente: exi('en_el_pc') }), {});
esperaDia('A03 mismas personas y horas = igual, sin aviso',
  dia('2026-10-22', { existente: exi('sin_enviar', ['Asensio', 7.5], ['Wilson', 8]), nuevas: [{ nombre: 'Asensio', horas: 7.5 }, { nombre: 'Wilson', horas: 8 }] }),
  { accion: 'igual', origen: 'sin_enviar', anteriores: ['Asensio', 'Wilson'] });
esperaDia('A04 igual aunque cambie el orden y la escritura (mayúsculas, tildes, espacios)',
  dia('2026-10-22', { existente: exi('en_el_pc', ['Wílson', 8], ['  asensio ', 7.5]), nuevas: [{ nombre: 'ASENSIO', horas: 7.5 }, { nombre: 'Wilson', horas: 8 }] }),
  { accion: 'igual', origen: 'en_el_pc', anteriores: ['Wílson', '  asensio '] });
esperaDia('A05 espacios repetidos en medio del nombre no cuentan',
  dia('2026-10-22', { existente: exi('en_el_pc', ['Juan  Carlos', 7.5]), nuevas: [{ nombre: 'Juan Carlos', horas: 7.5 }] }),
  { accion: 'igual', origen: 'en_el_pc', anteriores: ['Juan  Carlos'] });
esperaDia('A06 mismas personas pero una hora distinta = sustituye + ocupado',
  dia('2026-10-22', { existente: exi('en_el_pc', ['Asensio', 7.5], ['Wilson', 8]), nuevas: [{ nombre: 'Asensio', horas: 7.5 }, { nombre: 'Wilson', horas: 9 }] }),
  { accion: 'sustituye', origen: 'en_el_pc', anteriores: ['Asensio', 'Wilson'], avisos: ['ocupado'] });
esperaDia('A07 la nueva lista añade a alguien = sustituye',
  dia('2026-10-22', { existente: exi('sin_enviar', ['Asensio', 7.5]), nuevas: [{ nombre: 'Asensio', horas: 7.5 }, { nombre: 'Wilson', horas: 7.5 }] }),
  { accion: 'sustituye', origen: 'sin_enviar', anteriores: ['Asensio'], avisos: ['ocupado'] });
esperaDia('A08 la nueva lista quita a alguien = sustituye',
  dia('2026-10-22', { existente: exi('sin_enviar', ['Asensio', 7.5], ['Wilson', 7.5]), nuevas: [{ nombre: 'Asensio', horas: 7.5 }] }),
  { accion: 'sustituye', origen: 'sin_enviar', anteriores: ['Asensio', 'Wilson'], avisos: ['ocupado'] });
esperaDia('A09 la nueva lista es otra persona = sustituye',
  dia('2026-10-22', { existente: exi('en_el_pc', ['Asensio', 7.5], ['Wilson', 7.5]), nuevas: [{ nombre: 'Pedro', horas: 7.5 }] }),
  { accion: 'sustituye', origen: 'en_el_pc', anteriores: ['Asensio', 'Wilson'], avisos: ['ocupado'] });
esperaDia('A10 la nueva lista vacía con gente ya anotada = sustituye (y no hay cero_horas)',
  dia('2026-10-22', { existente: exi('en_el_pc', ['Asensio', 7.5]), nuevas: [] }),
  { accion: 'sustituye', origen: 'en_el_pc', anteriores: ['Asensio'], avisos: ['ocupado'] });
esperaDia('A11 una persona repetida en uno y no en el otro = sustituye (se cuentan las repeticiones)',
  dia('2026-10-22', { existente: exi('en_el_pc', ['Ana', 7.5], ['Ana', 7.5]), nuevas: [{ nombre: 'Ana', horas: 7.5 }] }),
  { accion: 'sustituye', origen: 'en_el_pc', anteriores: ['Ana', 'Ana'], avisos: ['ocupado'] });
esperaDia('A12 horas 7,501 y 7,5 se igualan al redondear a 2 decimales',
  dia('2026-10-22', { existente: exi('en_el_pc', ['Ana', 7.501]), nuevas: [{ nombre: 'Ana', horas: 7.5 }] }),
  { accion: 'igual', origen: 'en_el_pc', anteriores: ['Ana'] });
esperaDia('A13 horas 7,51 y 7,5 son distintas',
  dia('2026-10-22', { existente: exi('en_el_pc', ['Ana', 7.51]), nuevas: [{ nombre: 'Ana', horas: 7.5 }] }),
  { accion: 'sustituye', origen: 'en_el_pc', anteriores: ['Ana'], avisos: ['ocupado'] });
esperaDia('A14 el origen sin_enviar se conserva',
  dia('2026-10-22', { existente: exi('sin_enviar', ['Ana', 6]), nuevas: [{ nombre: 'Ana', horas: 7.5 }] }),
  { accion: 'sustituye', origen: 'sin_enviar', anteriores: ['Ana'], avisos: ['ocupado'] });

// ---- B. fin de semana (2026-10-24 sábado, 25 domingo, 23 viernes, 26 lunes) ----
esperaDia('B01 sábado sin horario en la obra = finde', dia('2026-10-24', { horarioObra: 0 }), { finde: true, futuro: true, avisos: ['finde', 'futuro'] });
esperaDia('B02 domingo sin horario = finde', dia('2026-10-25', { horarioObra: 0 }), { finde: true, futuro: true, avisos: ['finde', 'futuro'] });
esperaDia('B03 sábado con horario en la obra (4 h) = sin aviso de finde', dia('2026-10-24', { horarioObra: 4 }), { futuro: true, avisos: ['futuro'] });
esperaDia('B04 viernes con horario 0 no es fin de semana', dia('2026-10-23', { horarioObra: 0 }), {});
esperaDia('B05 lunes sin horario no es fin de semana', dia('2026-10-26', { horarioObra: 0 }), { futuro: true, avisos: ['futuro'] });
esperaDia('B06 sábado pasado sin horario (17/10)', dia('2026-10-17', { horarioObra: 0 }), { finde: true, avisos: ['finde'] });
esperaDia('B07 domingo del cambio de hora (29/03/2026)', dia('2026-03-29', { horarioObra: 0 }), { finde: true, avisos: ['finde'] });
esperaDia('B08 domingo del cambio de hora de octubre (25/10/2026), hoy el 30', dia('2026-10-25', { horarioObra: 0 }), { finde: true, avisos: ['finde'] }, '2026-10-30');
esperaDia('B09 sábado a final de mes (31/10/2026)', dia('2026-10-31', { horarioObra: 0 }), { finde: true, futuro: true, avisos: ['finde', 'futuro'] });
esperaDia('B10 sábado a principios de año (02/01/2027)', dia('2027-01-02', { horarioObra: 0 }), { finde: true, avisos: ['finde'] }, '2027-01-05');
esperaDia('B11 jueves bisiesto (29/02/2024) no es finde', dia('2024-02-29', { horarioObra: 0 }), {}, '2024-03-01');
esperaDia('B12 horarioObra con decimales (0,5) en sábado = hay horario', dia('2026-10-17', { horarioObra: 0.5 }), {});

// ---- C. día futuro (hoy = 2026-10-23) ----
esperaDia('C01 hoy no es futuro', dia('2026-10-23'), {});
esperaDia('C02 mañana es futuro (laborable: 2026-10-26 no, pero 2026-10-27 sí)', dia('2026-10-27'), { futuro: true, avisos: ['futuro'] });
esperaDia('C03 ayer no es futuro', dia('2026-10-22'), {});
esperaDia('C04 cambio de año: hoy 31/12, fecha 01/01 = futuro', dia('2027-01-01'), { futuro: true, avisos: ['futuro'] }, '2026-12-31');
esperaDia('C05 cambio de mes: hoy 30/09, fecha 01/10 = futuro', dia('2026-10-01'), { futuro: true, avisos: ['futuro'] }, '2026-09-30');
esperaDia('C06 día 10 contra día 9 (no comparar como números sueltos)', dia('2026-10-10', { horarioObra: 7.5 }), { futuro: true, avisos: ['futuro'] }, '2026-10-09');
esperaDia('C07 mismo día de otro año ya pasado', dia('2025-10-23'), {});

// ---- D. horas a cero ----
esperaDia('D01 una persona con 0 h', dia('2026-10-22', { nuevas: [{ nombre: 'Ana', horas: 7.5 }, { nombre: 'Bea', horas: 0 }] }), { sinHoras: ['Bea'], avisos: ['cero_horas'] });
esperaDia('D02 horas null cuentan como sin horas', dia('2026-10-22', { nuevas: [{ nombre: 'Ana', horas: null }] }), { sinHoras: ['Ana'], avisos: ['cero_horas'] });
esperaDia('D03 horas NaN cuentan', dia('2026-10-22', { nuevas: [{ nombre: 'Ana', horas: NaN }] }), { sinHoras: ['Ana'], avisos: ['cero_horas'] });
esperaDia('D04 horas negativas cuentan', dia('2026-10-22', { nuevas: [{ nombre: 'Ana', horas: -1 }] }), { sinHoras: ['Ana'], avisos: ['cero_horas'] });
esperaDia('D05 horas como texto cuentan', dia('2026-10-22', { nuevas: [{ nombre: 'Ana', horas: '7.5' }] }), { sinHoras: ['Ana'], avisos: ['cero_horas'] });
esperaDia('D06 sinHoras sigue el orden de las nuevas', dia('2026-10-22', { nuevas: [{ nombre: 'Zoe', horas: 0 }, { nombre: 'Ana', horas: 8 }, { nombre: 'Mar', horas: 0 }] }), { sinHoras: ['Zoe', 'Mar'], avisos: ['cero_horas'] });
esperaDia('D07 horas pequeñas pero positivas (0,5) no cuentan', dia('2026-10-22', { nuevas: [{ nombre: 'Ana', horas: 0.5 }] }), {});
esperaDia('D08 nuevas vacía sin nadie anotado: ni aviso ni sinHoras', dia('2026-10-22', { nuevas: [] }), {});
esperaDia('D09 Infinity cuenta como sin horas', dia('2026-10-22', { nuevas: [{ nombre: 'Ana', horas: Infinity }] }), { sinHoras: ['Ana'], avisos: ['cero_horas'] });

// ---- E. combinaciones y orden de los avisos ----
esperaDia('E01 los cuatro avisos a la vez, en su orden',
  dia('2026-10-24', { horarioObra: 0, existente: exi('sin_enviar', ['Pedro', 7.5]), nuevas: [{ nombre: 'Ana', horas: 0 }] }),
  { accion: 'sustituye', origen: 'sin_enviar', anteriores: ['Pedro'], finde: true, futuro: true, sinHoras: ['Ana'], avisos: ['ocupado', 'finde', 'futuro', 'cero_horas'] });
esperaDia('E02 sábado pasado con gente y 0 h: ocupado, finde, cero_horas',
  dia('2026-10-17', { horarioObra: 0, existente: exi('en_el_pc', ['Pedro', 5]), nuevas: [{ nombre: 'Ana', horas: 0 }] }),
  { accion: 'sustituye', origen: 'en_el_pc', anteriores: ['Pedro'], finde: true, sinHoras: ['Ana'], avisos: ['ocupado', 'finde', 'cero_horas'] });
esperaDia('E03 igual + futuro: solo futuro, la acción sigue siendo igual',
  dia('2026-10-27', { existente: exi('sin_enviar', ['Ana', 7.5]) }),
  { accion: 'igual', origen: 'sin_enviar', anteriores: ['Ana'], futuro: true, avisos: ['futuro'] });

// ---- E2. día ya anotado (el que se está corrigiendo): sin aviso de fin de semana ni de día futuro ----
esperaDia('E21 yaAnotado: un sábado sin horario no avisa de finde ni de futuro', dia('2026-10-24', { horarioObra: 0, yaAnotado: true }), {});
esperaDia('E22 yaAnotado: un día futuro laborable no avisa', dia('2026-10-27', { yaAnotado: true }), {});
esperaDia('E23 yaAnotado sigue avisando de 0 horas', dia('2026-10-24', { horarioObra: 0, yaAnotado: true, nuevas: [{ nombre: 'Ana', horas: 0 }] }), { sinHoras: ['Ana'], avisos: ['cero_horas'] });
esperaDia('E24 yaAnotado sigue avisando si pisa a otra gente', dia('2026-10-27', { yaAnotado: true, existente: exi('en_el_pc', ['Pedro', 7.5]) }), { accion: 'sustituye', origen: 'en_el_pc', anteriores: ['Pedro'], avisos: ['ocupado'] });
esperaDia('E25 yaAnotado false o ausente = como siempre', dia('2026-10-27', { yaAnotado: false }), { futuro: true, avisos: ['futuro'] });

// ---- F. varios días, orden, repetidos, hayAvisos ----
caso('F01 sale ordenado por fecha', () => {
  const p = plan([dia('2026-10-22'), dia('2026-10-20'), dia('2026-10-21')]);
  const f = p.dias.map((d) => d.fecha);
  if (!igual(f, ['2026-10-20', '2026-10-21', '2026-10-22'])) return JSON.stringify(f);
});
caso('F02 fecha repetida: se queda la primera', () => {
  const p = plan([dia('2026-10-22', { nuevas: [{ nombre: 'Ana', horas: 7.5 }] }), dia('2026-10-22', { nuevas: [{ nombre: 'Bea', horas: 0 }] })]);
  if (p.dias.length !== 1) return 'sale ' + p.dias.length + ' días';
  if (!igual(p.dias[0].sinHoras, []) || p.hayAvisos) return 'se ha usado la segunda repetida: ' + JSON.stringify(p.dias[0]);
});
caso('F03 sin días: plan vacío', () => {
  const p = plan([]);
  if (!igual(p.dias, []) || p.hayAvisos !== false || typeof p.firma !== 'string') return JSON.stringify(p);
});
caso('F04 hayAvisos false con todos los días limpios', () => {
  const p = plan([dia('2026-10-20'), dia('2026-10-21'), dia('2026-10-22', { existente: exi('en_el_pc', ['Ana', 7.5]) })]);
  if (p.hayAvisos !== false) return 'hayAvisos true: ' + JSON.stringify(p.dias.map((d) => d.avisos));
});
caso('F05 hayAvisos true con un solo día con aviso entre cuatro', () => {
  const p = plan([dia('2026-10-19'), dia('2026-10-20'), dia('2026-10-21', { existente: exi('en_el_pc', ['Otra', 7.5]) }), dia('2026-10-22')]);
  if (p.hayAvisos !== true) return 'hayAvisos false';
  const con = p.dias.filter((d) => d.avisos.length).map((d) => d.fecha);
  if (!igual(con, ['2026-10-21'])) return 'avisos en ' + JSON.stringify(con);
});
caso('F06 cada día se evalúa con sus propios datos (horarioObra y existente por día)', () => {
  const p = plan([
    dia('2026-10-23'),
    dia('2026-10-24', { horarioObra: 0 }),
    dia('2026-10-25', { horarioObra: 5 }),
    dia('2026-10-22', { existente: exi('sin_enviar', ['X', 1]) }),
  ]);
  const r = p.dias.map((d) => d.fecha + ':' + d.accion + ':' + d.avisos.join('+'));
  const e = ['2026-10-22:sustituye:ocupado', '2026-10-23:nuevo:', '2026-10-24:nuevo:finde+futuro', '2026-10-25:nuevo:futuro'];
  if (!igual(r, e)) return 'esperado ' + JSON.stringify(e) + ' obtenido ' + JSON.stringify(r);
});

// ---- G. firma y pureza ----
const baseG = () => [dia('2026-10-21'), dia('2026-10-22', { existente: exi('en_el_pc', ['Ana', 7.5]) })];
caso('G01 la firma es texto y es la misma para la misma entrada', () => {
  const a = plan(baseG()), b = plan(baseG());
  if (typeof a.firma !== 'string' || !a.firma) return 'firma vacía o no es texto';
  if (a.firma !== b.firma) return 'dos entradas iguales dan firmas distintas';
});
caso('G02 la firma no depende del orden de entrada de los días', () => {
  const x = baseG();
  if (plan(x).firma !== plan([x[1], x[0]]).firma) return 'cambia al invertir el orden de los días';
});
const cambia = (nombre, mutar) => caso(nombre, () => {
  const x = baseG();
  mutar(x);
  if (plan(baseG()).firma === plan(x).firma) return 'la firma no cambia';
});
cambia('G03 cambia una hora', (x) => { x[1].nuevas[0].horas = 8; });
cambia('G04 cambia un nombre', (x) => { x[0].nuevas[0].nombre = 'Beatriz'; });
cambia('G05 cambia una persona que ya había', (x) => { x[1].existente.personas[0].nombre = 'Otra'; });
cambia('G06 se añade un día', (x) => { x.push(dia('2026-10-20')); });
cambia('G07 cambia una fecha', (x) => { x[0].fecha = '2026-10-19'; });
cambia('G08 se añade una persona nueva', (x) => { x[0].nuevas.push({ nombre: 'Bea', horas: 7.5 }); });
cambia('G09 desaparece quien ya estaba', (x) => { x[1].existente = null; });
caso('G10 el plan se calcula sin modificar la entrada', () => {
  const entrada = { hoy: '2026-10-23', dias: [dia('2026-10-24', { horarioObra: 0, existente: exi('sin_enviar', ['Z', 3]) }), dia('2026-10-20')] };
  const antes = clonar(entrada);
  planificarGuardado(entrada);
  if (!igual(entrada, antes)) return 'la entrada ha cambiado';
});

// ---- H. aplicarDecision ----
const planH = () => plan([
  dia('2026-10-19'),
  dia('2026-10-20', { existente: exi('en_el_pc', ['Otra', 7.5]) }),
  dia('2026-10-21', { existente: exi('sin_enviar', ['Ana', 7.5]) }),
  dia('2026-10-22', { existente: exi('sin_enviar', ['Pepe', 7.5]) }),
]);
caso('H01 seguir: guarda todos y marca las sustituidas', () => {
  const r = aplicarDecision(planH(), 'seguir');
  const e = { guardar: ['2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22'], sustituidas: ['2026-10-20', '2026-10-22'], saltadas: [], cancelado: false };
  if (!igual(r, e)) return JSON.stringify(r);
});
caso('H02 saltar: no guarda las que sustituyen, sí las nuevas y las iguales', () => {
  const r = aplicarDecision(planH(), 'saltar');
  const e = { guardar: ['2026-10-19', '2026-10-21'], sustituidas: [], saltadas: ['2026-10-20', '2026-10-22'], cancelado: false };
  if (!igual(r, e)) return JSON.stringify(r);
});
caso('H03 cancelar: no guarda nada', () => {
  const r = aplicarDecision(planH(), 'cancelar');
  const e = { guardar: [], sustituidas: [], saltadas: [], cancelado: true };
  if (!igual(r, e)) return JSON.stringify(r);
});
caso('H04 un modo desconocido cancela', () => {
  for (const m of ['', 'SEGUIR', 'guardar', undefined, null, 1]) {
    const r = aplicarDecision(planH(), m);
    if (!igual(r, { guardar: [], sustituidas: [], saltadas: [], cancelado: true })) return 'modo ' + String(m) + ' -> ' + JSON.stringify(r);
  }
});
caso('H05 saltar sin días ocupados = seguir, sin saltadas', () => {
  const p = plan([dia('2026-10-20'), dia('2026-10-21')]);
  const r = aplicarDecision(p, 'saltar');
  if (!igual(r, { guardar: ['2026-10-20', '2026-10-21'], sustituidas: [], saltadas: [], cancelado: false })) return JSON.stringify(r);
});
caso('H06 el orden sale como el plan (por fecha)', () => {
  const p = plan([dia('2026-10-22'), dia('2026-10-19'), dia('2026-10-20')]);
  const r = aplicarDecision(p, 'seguir');
  if (!igual(r.guardar, ['2026-10-19', '2026-10-20', '2026-10-22'])) return JSON.stringify(r.guardar);
});
caso('H07 no modifica el plan', () => {
  const p = planH(), antes = clonar(p);
  aplicarDecision(p, 'seguir'); aplicarDecision(p, 'saltar'); aplicarDecision(p, 'cancelar');
  if (!igual(p, antes)) return 'el plan ha cambiado';
});
caso('H08 plan sin días', () => {
  const r = aplicarDecision(plan([]), 'seguir');
  if (!igual(r, { guardar: [], sustituidas: [], saltadas: [], cancelado: false })) return JSON.stringify(r);
});
caso('H09 las listas devueltas no comparten referencia con el plan', () => {
  const p = planH();
  const r = aplicarDecision(p, 'seguir');
  r.guardar.push('x');
  if (p.dias.length !== 4 || aplicarDecision(p, 'seguir').guardar.length !== 4) return 'modificar el resultado cambió el plan';
});

console.log((fallos ? 'FALLAN ' + fallos : 'OK') + ' de ' + total + ' casos');
process.exit(fallos ? 1 : 0);'''


def funciones_del_html(texto):
    """El texto de las dos funciones, desde `function planificarGuardado` hasta justo antes de `presentesDelDia`."""
    ini = texto.index("function planificarGuardado(entrada) {")
    fin = texto.index("function presentesDelDia(")
    return texto[ini:fin]


class TestPlanificarGuardado(unittest.TestCase):
    def setUp(self):
        self.texto = (APP_DIR / "generador_personal.html").read_text(encoding="utf-8")
        self.funciones = funciones_del_html(self.texto)

    def test_los_casos_de_la_funcion_pura(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("falta node: NO se ha revisado la lógica de los avisos de antes de guardar")
        base = Path(os.environ.get("P3_TMP") or tempfile.gettempdir()) / ("plan_guardado_" + uuid.uuid4().hex[:8])
        base.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(base), True)
        (base / "planificar.js").write_text(self.funciones, encoding="utf-8")
        (base / "verificador.js").write_text(VERIFICADOR, encoding="utf-8")
        p = subprocess.run([node, str(base / "verificador.js"), str(base / "planificar.js")], capture_output=True, timeout=120)
        salida = p.stdout.decode("utf-8", "replace")
        self.assertEqual(0, p.returncode, salida + p.stderr.decode("utf-8", "replace"))
        m = re.search(r"OK de (\d+) casos", salida)
        self.assertTrue(m and int(m.group(1)) >= 60, "se han revisado muy pocos casos: " + salida)

    def test_la_funcion_no_toca_la_pantalla_ni_el_reloj(self):
        for prohibido in ("document", "localStorage", "Date.now", "Math.random", "new Date()", "toast("):
            self.assertNotIn(prohibido, self.funciones, "la lógica de los avisos debe ser pura: lleva «%s»" % prohibido)

    def test_save_usa_el_plan_antes_de_escribir(self):
        """El plan se calcula y se resuelve ANTES de tocar `pending` en save (si no, el aviso llegaría tarde)."""
        cuerpo = self.texto[self.texto.index("function save(decision) {"):]
        cuerpo = cuerpo[: cuerpo.index("\n      // Enviar al PC")]
        self.assertLess(cuerpo.index("planificarGuardado("), cuerpo.index("pending.push("), "el aviso tiene que salir antes de guardar")
        self.assertLess(cuerpo.index("aplicarDecision("), cuerpo.index("pending.push("), "la decisión se aplica antes de guardar")


if __name__ == "__main__":
    unittest.main()
