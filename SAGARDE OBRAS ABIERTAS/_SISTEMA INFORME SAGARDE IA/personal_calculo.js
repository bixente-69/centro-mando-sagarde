'use strict';

// Helper: parsear fecha 'YYYY-MM-DD' a Date en UTC
function aFechaUTC(str) {
  if (typeof str !== 'string') return null;
  const partes = str.split('-').map(Number);
  if (partes.length !== 3 || partes.some(isNaN)) return null;
  return new Date(Date.UTC(partes[0], partes[1] - 1, partes[2]));
}

// Helper: formatear Date UTC a 'YYYY-MM-DD'
function aTextoISO(d) {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const dia = String(d.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${dia}`;
}

// Helper: sumar/restar días en UTC
function sumarDias(d, n) {
  const res = new Date(d.getTime());
  res.setUTCDate(res.getUTCDate() + n);
  return res;
}

// Nombres de días y meses en español
const DIAS_SEMANA_3 = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];
const MESES_3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

// Texto sin espacios de más; vacío si no es texto
function limpiarTexto(x) {
  return typeof x === 'string' ? x.split(/\s+/).filter(Boolean).join(' ') : '';
}

// Quita las marcas de tilde de un texto (mismo método que la tablet: separar con NFD y soltar las marcas)
const MARCAS_TILDE = new RegExp('[' + String.fromCharCode(0x300) + '-' + String.fromCharCode(0x36f) + ']', 'g');

// Clave para comparar empresas: sin tildes, sin mayúsculas y sin espacios de más
function claveEmpresa(x) {
  return limpiarTexto(x).normalize('NFD').replace(MARCAS_TILDE, '').toLowerCase();
}

// Empresa escrita en una fila; vacía si no tiene (o si lo escrito es «Sin empresa»)
function empresaDeFila(f) {
  const texto = limpiarTexto(f && f.empresa);
  return claveEmpresa(texto) === claveEmpresa('Sin empresa') ? '' : texto;
}

// Un autónomo es quien tiene una empresa que acaba en «@AUT» (mayúsculas y espacios indiferentes): la misma
// regla que `es_autonomo` de personal_obra.py
function esAutonomo(empresa) {
  return /@\s*aut$/i.test(limpiarTexto(empresa));
}

// De dos empresas de la misma persona gana la de la fila más reciente; con la misma fecha, la de clave menor
function esMasReciente(actual, fecha, empresa) {
  if (!empresa) return false;
  if (!actual) return true;
  if (fecha !== actual.fecha) return fecha > actual.fecha;
  return claveEmpresa(empresa) < claveEmpresa(actual.empresa);
}

// Clasifica si una fila es válida o qué tipo de error tiene
function clasificarFila(f) {
  if (!f) return 'sinHoras';
  const sinHoras = f.horas === undefined || f.horas === null || typeof f.horas !== 'number' || !Number.isFinite(f.horas);
  if (sinHoras) return 'sinHoras';

  if (f.horas < 0 || f.horas > 24) return 'invalida';
  if (typeof f.nombre !== 'string' || f.nombre.length === 0) return 'invalida';

  if (f.extra !== undefined && f.extra !== null) {
    if (typeof f.extra !== 'number' || !Number.isFinite(f.extra) || f.extra < 0 || f.extra > f.horas) {
      return 'invalida';
    }
  }

  return 'valida';
}

// 1. semanaISO(fecha)
function semanaISO(fecha) {
  const d = aFechaUTC(fecha);
  const diaSemana = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - diaSemana);
  const inicioAnio = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d - inicioAnio) / 86400000) + 1) / 7);
}

// 2. rangoPeriodo(periodo, ref)
function rangoPeriodo(periodo, ref) {
  if (periodo === 'obra') {
    return { desde: null, hasta: null };
  }
  const d = aFechaUTC(ref);
  if (!d) return { desde: null, hasta: null };

  if (periodo === 'semana') {
    const diaSem = d.getUTCDay() || 7;
    const lunes = sumarDias(d, 1 - diaSem);
    const domingo = sumarDias(lunes, 6);
    return { desde: aTextoISO(lunes), hasta: aTextoISO(domingo) };
  }

  if (periodo === 'mes') {
    const y = d.getUTCFullYear();
    const m = d.getUTCMonth();
    const primerDia = new Date(Date.UTC(y, m, 1));
    const ultimoDia = new Date(Date.UTC(y, m + 1, 0));
    return { desde: aTextoISO(primerDia), hasta: aTextoISO(ultimoDia) };
  }

  if (periodo === 'anio') {
    const y = d.getUTCFullYear();
    return { desde: `${y}-01-01`, hasta: `${y}-12-31` };
  }

  return { desde: null, hasta: null };
}

// 3. mover(periodo, ref, k)
function mover(periodo, ref, k) {
  if (periodo === 'obra' || k === 0) return ref;
  const d = aFechaUTC(ref);
  if (!d) return ref;

  if (periodo === 'semana') {
    return aTextoISO(sumarDias(d, 7 * k));
  }

  if (periodo === 'mes') {
    const y = d.getUTCFullYear();
    const m = d.getUTCMonth();
    const dia = d.getUTCDate();
    const mesDestino = m + k;
    const ultimoDiaMes = new Date(Date.UTC(y, mesDestino + 1, 0)).getUTCDate();
    const diaFinal = Math.min(dia, ultimoDiaMes);
    return aTextoISO(new Date(Date.UTC(y, mesDestino, diaFinal)));
  }

  if (periodo === 'anio') {
    const y = d.getUTCFullYear() + k;
    const m = d.getUTCMonth();
    const dia = d.getUTCDate();
    const ultimoDiaMes = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
    const diaFinal = Math.min(dia, ultimoDiaMes);
    return aTextoISO(new Date(Date.UTC(y, m, diaFinal)));
  }

  return ref;
}

// 4. filtrar(jornadas, { obra, ambito, periodo, ref })
function filtrar(jornadas, opts) {
  if (!Array.isArray(jornadas)) return [];
  const { obra, ambito, periodo, ref } = opts || {};

  let desde = null;
  let hasta = null;
  if (periodo && periodo !== 'obra') {
    const r = rangoPeriodo(periodo, ref);
    desde = r.desde;
    hasta = r.hasta;
  }

  return jornadas.filter(f => {
    if (!f) return false;
    if (obra && obra !== 'todo' && f.obra !== obra) return false;
    if (ambito && ambito !== 'todo' && f.ambito !== ambito) return false;
    if (desde !== null && hasta !== null) {
      if (!f.fecha || f.fecha < desde || f.fecha > hasta) return false;
    }
    return true;
  });
}

// 5. agregar(filas)
function agregar(filas) {
  let filasSinHoras = 0;
  let filasInvalidas = 0;

  if (!Array.isArray(filas)) {
    return { trabajadores: [], total: null, avisos: { filasSinHoras: 0, filasInvalidas: 0 } };
  }

  const mapaTrabajadores = new Map();
  const grafiasEmpresa = new Map();
  const totalDiasGlobal = new Set();
  let totalHoras = 0;
  let totalExtra = 0;
  let hayFilasValidas = false;

  for (const f of filas) {
    const estado = clasificarFila(f);
    if (estado === 'sinHoras') {
      filasSinHoras++;
      continue;
    }
    if (estado === 'invalida') {
      filasInvalidas++;
      continue;
    }

    hayFilasValidas = true;
    const extraVal = (f.extra !== undefined && f.extra !== null) ? f.extra : 0;
    const horasVal = f.horas;

    totalHoras += horasVal;
    totalExtra += extraVal;
    if (f.fecha) totalDiasGlobal.add(f.fecha);

    let t = mapaTrabajadores.get(f.nombre);
    if (!t) {
      t = {
        nombre: f.nombre,
        diasSet: new Set(),
        horas: 0,
        extra: 0,
        obras: {},
        empresa: null
      };
      mapaTrabajadores.set(f.nombre, t);
    }

    // Una empresa se escribe siempre como la primera vez que salió (así la tabla por empresa y el nombre coinciden)
    const empresaFila = empresaDeFila(f);
    if (empresaFila && !grafiasEmpresa.has(claveEmpresa(empresaFila))) {
      grafiasEmpresa.set(claveEmpresa(empresaFila), empresaFila);
    }
    if (esMasReciente(t.empresa, f.fecha || '', empresaFila)) {
      t.empresa = { fecha: f.fecha || '', empresa: empresaFila };
    }

    if (f.fecha) t.diasSet.add(f.fecha);
    t.horas += horasVal;
    t.extra += extraVal;
    if (f.obra) {
      t.obras[f.obra] = (t.obras[f.obra] || 0) + horasVal;
    }
  }

  const avisos = { filasSinHoras, filasInvalidas };

  if (!hayFilasValidas) {
    return { trabajadores: [], total: null, avisos };
  }

  const listaTrabajadores = Array.from(mapaTrabajadores.values()).map(t => {
    const persona = {
      nombre: t.nombre,
      dias: t.diasSet.size,
      horas: t.horas,
      extra: t.extra,
      ordinarias: t.horas - t.extra,
      pct: totalHoras > 0 ? (100 * t.horas / totalHoras) : null,
      obras: t.obras
    };
    // La empresa solo sale si se conoce: «sin empresa» es no tener la clave
    if (t.empresa) persona.empresa = grafiasEmpresa.get(claveEmpresa(t.empresa.empresa));
    return persona;
  });

  listaTrabajadores.sort((a, b) => {
    if (b.horas !== a.horas) return b.horas - a.horas;
    return a.nombre.localeCompare(b.nombre, 'es');
  });

  const total = {
    horas: totalHoras,
    extra: totalExtra,
    ordinarias: totalHoras - totalExtra,
    dias: totalDiasGlobal.size,
    trabajadores: listaTrabajadores.length
  };

  return { trabajadores: listaTrabajadores, total, avisos };
}

// 6. matriz(filas, periodo, ref)
function matriz(filas, periodo, ref) {
  const filasValidas = Array.isArray(filas)
    ? filas.filter(f => clasificarFila(f) === 'valida')
    : [];

  const columnas = [];

  if (periodo === 'semana') {
    const d = aFechaUTC(ref);
    const diaSem = d ? (d.getUTCDay() || 7) : 1;
    const lunes = d ? sumarDias(d, 1 - diaSem) : new Date(Date.UTC(2000, 0, 3));
    for (let i = 0; i < 7; i++) {
      const diaActual = sumarDias(lunes, i);
      const clave = aTextoISO(diaActual);
      const numDia = String(diaActual.getUTCDate()).padStart(2, '0');
      const etiqueta = `${DIAS_SEMANA_3[i]} ${numDia}`;
      columnas.push({ clave, etiqueta });
    }
  } else if (periodo === 'mes') {
    const d = aFechaUTC(ref);
    if (d) {
      const y = d.getUTCFullYear();
      const m = d.getUTCMonth();
      const primerDia = new Date(Date.UTC(y, m, 1));
      const ultimoDia = new Date(Date.UTC(y, m + 1, 0));

      const diaSem1 = primerDia.getUTCDay() || 7;
      let lunesActual = sumarDias(primerDia, 1 - diaSem1);

      while (lunesActual <= ultimoDia) {
        const clave = aTextoISO(lunesActual);
        const sIso = semanaISO(clave);
        const etiqueta = `S${sIso}`;
        columnas.push({ clave, etiqueta });
        lunesActual = sumarDias(lunesActual, 7);
      }
    }
  } else if (periodo === 'anio' || periodo === 'obra') {
    if (filasValidas.length > 0) {
      let minFecha = filasValidas[0].fecha;
      let maxFecha = filasValidas[0].fecha;
      for (const f of filasValidas) {
        if (f.fecha < minFecha) minFecha = f.fecha;
        if (f.fecha > maxFecha) maxFecha = f.fecha;
      }

      const dMin = aFechaUTC(minFecha);
      const dMax = aFechaUTC(maxFecha);

      let yCur = dMin.getUTCFullYear();
      let mCur = dMin.getUTCMonth();
      const yEnd = dMax.getUTCFullYear();
      const mEnd = dMax.getUTCMonth();

      while (yCur < yEnd || (yCur === yEnd && mCur <= mEnd)) {
        const clave = `${yCur}-${String(mCur + 1).padStart(2, '0')}`;
        let etiqueta = MESES_3[mCur];
        if (periodo === 'obra') {
          etiqueta += ` '${String(yCur).slice(-2)}`;
        }
        columnas.push({ clave, etiqueta });

        mCur++;
        if (mCur > 11) {
          mCur = 0;
          yCur++;
        }
      }
    }
  }

  // Obtener trabajadores en el mismo orden que 'agregar'
  const aggResult = agregar(filasValidas);
  const trabajadoresInfo = aggResult.trabajadores;

  // Mapa helper para obtener clave de columna de una fila
  function obtenerClaveColumna(fechaStr) {
    if (periodo === 'semana') return fechaStr;
    if (periodo === 'mes') {
      const d = aFechaUTC(fechaStr);
      const diaSem = d.getUTCDay() || 7;
      return aTextoISO(sumarDias(d, 1 - diaSem));
    }
    return fechaStr.slice(0, 7);
  }

  const resultFilas = [];
  const totalesColumna = {};
  const recuentoColumna = {};

  for (const col of columnas) {
    totalesColumna[col.clave] = null;
    recuentoColumna[col.clave] = 0;
  }

  for (const t of trabajadoresInfo) {
    const filasTrabajador = filasValidas.filter(f => f.nombre === t.nombre);
    const horasPorCol = {};
    const conteoPorCol = {};

    for (const f of filasTrabajador) {
      const colKey = obtenerClaveColumna(f.fecha);
      horasPorCol[colKey] = (horasPorCol[colKey] || 0) + f.horas;
      conteoPorCol[colKey] = (conteoPorCol[colKey] || 0) + 1;

      if (recuentoColumna[colKey] !== undefined) {
        totalesColumna[colKey] = (totalesColumna[colKey] || 0) + f.horas;
        recuentoColumna[colKey]++;
      }
    }

    const celdas = {};
    for (const col of columnas) {
      if (conteoPorCol[col.clave] > 0) {
        celdas[col.clave] = horasPorCol[col.clave];
      } else {
        celdas[col.clave] = null;
      }
    }

    resultFilas.push({
      nombre: t.nombre,
      celdas,
      total: t.horas
    });
  }

  return {
    columnas,
    filas: resultFilas,
    totalesColumna
  };
}

// 7. ranking(jornadas, { periodo, ref })
function ranking(jornadas, opts) {
  const p = opts && opts.periodo;
  const r = opts && opts.ref;
  const filasFiltradas = filtrar(jornadas, { periodo: p, ref: r });
  return agregar(filasFiltradas);
}

// 8. agregarPorEmpresa(filas): la suma por empresa. Por empresa: personas, días de persona (un día de una persona
// cuenta 1 aunque trabaje en dos obras o en vivienda y garaje), horas y % de impacto. Más horas primero y
// «Sin empresa» siempre al final. Cada autónomo («X @AUT») es una línea más y `autonomos` es la suma de todos
// ellos: sirve para enseñarla aparte y NO entra en `total` ni en los % (no se cuenta dos veces).
const ETIQUETA_SIN_EMPRESA = 'Sin empresa';
const ETIQUETA_AUTONOMOS = 'Total autónomos (@AUT)';

function agregarPorEmpresa(filas) {
  const resultado = { empresas: [], autonomos: null, total: null, avisos: { variasEmpresas: [] } };
  if (!Array.isArray(filas)) return resultado;

  const grupos = new Map();
  const empresasDeCadaUno = new Map();
  const personasTodas = new Set();
  const diasTodos = new Set();
  let totalHoras = 0;

  for (const f of filas) {
    if (clasificarFila(f) !== 'valida') continue;
    const texto = empresaDeFila(f);
    const claveGrupo = claveEmpresa(texto);
    const sinEmpresa = claveGrupo === '';

    let g = grupos.get(claveGrupo);
    if (!g) {
      g = {
        nombre: sinEmpresa ? ETIQUETA_SIN_EMPRESA : texto,
        clave: claveGrupo,
        sinEmpresa,
        autonomo: !sinEmpresa && esAutonomo(texto),
        personas: new Set(),
        dias: new Set(),
        horas: 0
      };
      grupos.set(claveGrupo, g);
    }

    const diaDePersona = f.nombre + '\n' + f.fecha;
    g.personas.add(f.nombre);
    if (f.fecha) g.dias.add(diaDePersona);
    g.horas += f.horas;

    personasTodas.add(f.nombre);
    if (f.fecha) diasTodos.add(diaDePersona);
    totalHoras += f.horas;

    if (!empresasDeCadaUno.has(f.nombre)) empresasDeCadaUno.set(f.nombre, new Set());
    empresasDeCadaUno.get(f.nombre).add(claveGrupo);
  }

  if (grupos.size === 0) return resultado;

  const lineas = Array.from(grupos.values());
  lineas.sort((a, b) => {
    if (a.sinEmpresa !== b.sinEmpresa) return a.sinEmpresa ? 1 : -1;
    if (b.horas !== a.horas) return b.horas - a.horas;
    return a.nombre.localeCompare(b.nombre, 'es');
  });
  const porcentaje = horas => (totalHoras > 0 ? (100 * horas / totalHoras) : null);

  resultado.empresas = lineas.map(g => ({
    nombre: g.nombre,
    clave: g.clave,
    sinEmpresa: g.sinEmpresa,
    autonomo: g.autonomo,
    personas: g.personas.size,
    dias: g.dias.size,
    horas: g.horas,
    pct: porcentaje(g.horas)
  }));

  // El total de autónomos se junta aparte: una persona o un día que salgan en dos líneas @AUT cuentan una vez
  const autonomos = lineas.filter(g => g.autonomo);
  if (autonomos.length > 0) {
    const personasAut = new Set();
    const diasAut = new Set();
    let horasAut = 0;
    for (const g of autonomos) {
      g.personas.forEach(p => personasAut.add(p));
      g.dias.forEach(d => diasAut.add(d));
      horasAut += g.horas;
    }
    resultado.autonomos = {
      etiqueta: ETIQUETA_AUTONOMOS,
      personas: personasAut.size,
      dias: diasAut.size,
      horas: horasAut,
      pct: porcentaje(horasAut)
    };
  }

  resultado.total = { personas: personasTodas.size, dias: diasTodos.size, horas: totalHoras };
  const dobles = [];
  empresasDeCadaUno.forEach((claves, nombre) => { if (claves.size > 1) dobles.push(nombre); });
  resultado.avisos.variasEmpresas = dobles.sort((a, b) => a.localeCompare(b, 'es'));
  return resultado;
}

// 9. textoAvisoEmpresas(resultado): la frase que se enseña si alguien sale con más de una empresa (vacía si no)
function textoAvisoEmpresas(resultado) {
  const quienes = resultado && resultado.avisos && resultado.avisos.variasEmpresas;
  if (!Array.isArray(quienes) || quienes.length === 0) return '';
  const cuantos = quienes.length === 1 ? 'una persona' : quienes.length + ' personas';
  return 'Hay ' + cuantos + ' con más de una empresa (' + quienes.join(', ') + '): sus horas se cuentan en cada una.';
}

// 10. htmlPorEmpresa(resultado, clases): el bloque «Por empresa» que enseñan los cuatro sitios (pestaña, informe,
// ranking y tablet), escrito UNA sola vez para que todos digan lo mismo. `clases` da la clase de cada pieza en cada
// sitio: { bloque, titulo, aviso, scroll, tabla, nota, pct } (`pct` = título de la columna del %).
// Vacío si no hay datos.
const MARCAS_HTML = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

function escaparTexto(x) {
  return String(x === null || x === undefined ? '' : x).replace(/[&<>"']/g, c => MARCAS_HTML[c]);
}

// Un decimal y con coma; un dato que falta se escribe «–», nunca 0
function numeroCorto(x) {
  return (typeof x === 'number' && Number.isFinite(x)) ? String(Math.round(x * 10) / 10).replace('.', ',') : '–';
}

function htmlPorEmpresa(res, clases) {
  if (!res || !res.total || !Array.isArray(res.empresas) || res.empresas.length === 0) return '';
  const c = clases || {};
  const clase = k => (c[k] ? ' class="' + escaparTexto(c[k]) + '"' : '');
  const porciento = x => (typeof x === 'number' && Number.isFinite(x) ? numeroCorto(x) + ' %' : '–');
  const fila = (nombre, personas, dias, horas, pct, claseFila) =>
    '<tr' + (claseFila ? ' class="' + claseFila + '"' : '') + '><td>' + escaparTexto(nombre) + '</td>' +
    '<td class="n">' + personas + '</td><td class="n">' + dias + '</td>' +
    '<td class="n">' + numeroCorto(horas) + '</td><td class="n">' + porciento(pct) + '</td></tr>';

  const aviso = textoAvisoEmpresas(res);
  let html = '<div' + clase('bloque') + ' data-por-empresa>';
  html += '<h4' + clase('titulo') + '>Por empresa</h4>';
  if (aviso) html += '<p' + clase('aviso') + '>⚠ ' + escaparTexto(aviso) + '</p>';
  html += '<div' + clase('scroll') + '><table' + clase('tabla') + '><thead><tr><th>Empresa</th>' +
    '<th class="n">Personas</th><th class="n">Días</th><th class="n">Horas</th>' +
    '<th class="n">' + escaparTexto(c.pct || '% impacto') + '</th></tr></thead><tbody>';
  res.empresas.forEach(l => {
    html += fila(l.nombre, l.personas, l.dias, l.horas, l.pct, l.sinEmpresa ? 'emp-sin' : '');
  });
  html += '</tbody><tfoot>' + fila('Total', res.total.personas, res.total.dias, res.total.horas,
    res.total.horas > 0 ? 100 : null, '');
  if (res.autonomos) {
    html += fila(res.autonomos.etiqueta, res.autonomos.personas, res.autonomos.dias, res.autonomos.horas,
      res.autonomos.pct, 'emp-total-aut');
  }
  html += '</tfoot></table></div>';

  let nota = 'Días = días trabajados por cada persona, sumados: si dos personas trabajan el mismo día, son 2 días.';
  if (res.empresas.some(l => l.sinEmpresa)) nota += ' «Sin empresa» = todavía no se les ha puesto empresa.';
  if (res.autonomos) {
    nota += ' «' + res.autonomos.etiqueta + '» es la suma de los autónomos de arriba: ' +
      'ya están contados, no se suman otra vez.';
  }
  html += '<p' + clase('nota') + '>' + escaparTexto(nota) + '</p></div>';
  return html;
}

const API = {
  semanaISO,
  rangoPeriodo,
  mover,
  filtrar,
  agregar,
  matriz,
  ranking,
  agregarPorEmpresa,
  esAutonomo,
  textoAvisoEmpresas,
  htmlPorEmpresa
};

if (typeof module !== 'undefined' && module.exports) { module.exports = API; }
if (typeof window !== 'undefined') { window.PersonalCalculo = API; }
