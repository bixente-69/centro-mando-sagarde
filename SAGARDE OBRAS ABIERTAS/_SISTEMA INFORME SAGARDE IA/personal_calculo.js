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
        obras: {}
      };
      mapaTrabajadores.set(f.nombre, t);
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
    return {
      nombre: t.nombre,
      dias: t.diasSet.size,
      horas: t.horas,
      extra: t.extra,
      ordinarias: t.horas - t.extra,
      pct: totalHoras > 0 ? (100 * t.horas / totalHoras) : null,
      obras: t.obras
    };
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

const API = {
  semanaISO,
  rangoPeriodo,
  mover,
  filtrar,
  agregar,
  matriz,
  ranking
};

if (typeof module !== 'undefined' && module.exports) { module.exports = API; }
if (typeof window !== 'undefined') { window.PersonalCalculo = API; }
