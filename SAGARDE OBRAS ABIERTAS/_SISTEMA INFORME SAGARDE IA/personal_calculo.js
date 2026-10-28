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
    const resultadoFila = clasificarFila(f);
    if (resultadoFila === 'sinHoras') {
      filasSinHoras++;
      continue;
    }
    if (resultadoFila === 'invalida') {
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
// sitio: { bloque, titulo, aviso, scroll, tabla, nota, pct, ordenPor, ordenDir }.
// Vacío si no hay datos.
const MARCAS_HTML = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

function escaparTexto(x) {
  return String(x === null || x === undefined ? '' : x).replace(/[&<>"']/g, c => MARCAS_HTML[c]);
}

// Un decimal y con coma; un dato que falta se escribe «–», nunca 0
function numeroCorto(x) {
  return (typeof x === 'number' && Number.isFinite(x)) ? String(Math.round(x * 10) / 10).replace('.', ',') : '–';
}

function ordenarEmpresas(empresas, por, dir) {
  const copia = Array.isArray(empresas) ? empresas.slice() : [];
  const campo = por || 'horas';
  const dirPorDefecto = (campo === 'nombre' || campo === 'empresa' || campo === 'tipo') ? 'asc' : 'desc';
  const dirEfectiva = (dir === 'asc' || dir === 'desc') ? dir : dirPorDefecto;
  const s = dirEfectiva === 'asc' ? 1 : -1;
  const alfabetico = (a, b) => a.nombre.localeCompare(b.nombre, 'es');

  return copia.sort((a, b) => {
    if (a.sinEmpresa !== b.sinEmpresa) return a.sinEmpresa ? 1 : -1;
    if (campo === 'nombre' || campo === 'empresa') {
      return s * alfabetico(a, b);
    }
    if (campo === 'tipo') {
      const ta = a.tipo || (a.autonomo ? 'Autónomo (@AUT)' : 'Empresa');
      const tb = b.tipo || (b.autonomo ? 'Autónomo (@AUT)' : 'Empresa');
      return s * ta.localeCompare(tb, 'es') || (b.horas - a.horas) || alfabetico(a, b);
    }
    if (campo === 'enBase') {
      return s * ((a.enBase || 0) - (b.enBase || 0)) || (b.horas - a.horas) || alfabetico(a, b);
    }
    if (campo === 'personas') {
      return s * ((a.personas || 0) - (b.personas || 0)) || (b.horas - a.horas) || alfabetico(a, b);
    }
    if (campo === 'dias') {
      return s * ((a.dias || 0) - (b.dias || 0)) || (b.horas - a.horas) || alfabetico(a, b);
    }
    if (campo === 'obras') {
      const oa = Array.isArray(a.obras) ? a.obras.length : 0;
      const ob = Array.isArray(b.obras) ? b.obras.length : 0;
      return s * (oa - ob) || s * (a.horas - b.horas) || alfabetico(a, b);
    }
    if (campo === 'ultima') {
      const ua = a.ultima || null;
      const ub = b.ultima || null;
      if ((ua === null) !== (ub === null)) return ua === null ? 1 : -1;
      if (ua !== ub) return s * (ua < ub ? -1 : 1);
      return alfabetico(a, b);
    }
    // 'horas' o 'pct'
    return s * ((a.horas || 0) - (b.horas || 0)) || alfabetico(a, b);
  });
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

  const colActiva = c.ordenPor || '';
  const dirActiva = c.ordenDir || '';
  const attrTh = (col, esNum) => {
    let s = '';
    if (esNum) s += ' class="n"';
    if (c.ordenable) {
      s += ' data-col-emp="' + col + '"';
      if (colActiva === col && (dirActiva === 'asc' || dirActiva === 'desc')) {
        s += ' data-dir="' + dirActiva + '"';
      }
    }
    return s;
  };

  const listaEmpresas = (c.ordenable && colActiva)
    ? ordenarEmpresas(res.empresas, colActiva, dirActiva)
    : res.empresas;

  const aviso = textoAvisoEmpresas(res);
  let html = '<div' + clase('bloque') + ' data-por-empresa>';
  html += '<h4' + clase('titulo') + '>Por empresa</h4>';
  if (aviso) html += '<p' + clase('aviso') + '>⚠ ' + escaparTexto(aviso) + '</p>';
  html += '<div' + clase('scroll') + '><table' + clase('tabla') + '><thead><tr>' +
    '<th' + attrTh('nombre', false) + '>Empresa</th>' +
    '<th' + attrTh('personas', true) + '>Personas</th>' +
    '<th' + attrTh('dias', true) + '>Días</th>' +
    '<th' + attrTh('horas', true) + '>Horas</th>' +
    '<th' + attrTh('pct', true) + '>' + escaparTexto(c.pct || '% impacto') + '</th></tr></thead><tbody>';
  listaEmpresas.forEach(l => {
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

// Una fecha válida de jornada: 'AAAA-MM-DD' (solo estas cuentan como «última jornada»)
function esFechaISO(fecha) {
  if (typeof fecha !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(fecha)) return false;
  return aTextoISO(aFechaUTC(fecha)) === fecha;
}

// 11. baseTrabajadores(filas, catalogo): una línea por persona de la base, tenga o no jornadas. Horas, días, obras y última
// jornada salen de las MISMAS filas y con las mismas reglas que el ranking (una fila sin horas o inválida no se cuenta y se
// avisa); de la ficha de la base salen la empresa y el historial de nombres (renombres y fusiones). Nada se pierde en
// silencio: alguien con jornadas que no está en la base sale igual (con `sinFicha`), y lo raro de la base se cuenta en `avisos`.
function claveNombre(x) {
  return claveEmpresa(x);
}

function textosDeLista(valor) {
  if (valor === undefined || valor === null) return { lista: [], legible: true };
  if (!Array.isArray(valor)) return { lista: [], legible: false };
  const lista = valor.filter(x => typeof x === 'string' && limpiarTexto(x)).map(limpiarTexto);
  return { lista, legible: lista.length === valor.length };
}

function baseTrabajadores(filas, catalogo) {
  const avisos = {
    filasSinHoras: 0,
    filasInvalidas: 0,
    fichasInvalidas: 0,
    fichasRepetidas: [],
    historialIlegible: [],
    sinFicha: []
  };
  const porClave = new Map();

  const nuevaLinea = (nombre, ficha) => ({
    nombre,
    empresa: ficha ? empresaDeFila(ficha) : '',
    categoria: ficha && typeof ficha.categoria === 'string' ? limpiarTexto(ficha.categoria) : '',
    horarioPreferido: (ficha && ficha.horario_preferido && typeof ficha.horario_preferido === 'object')
      ? ficha.horario_preferido
      : null,
    activo: !(ficha && ficha.activo === false),
    anteriores: [],
    fusionados: [],
    sinFicha: !ficha,
    horas: 0,
    extra: 0,
    dias: 0,
    obras: [],
    ultima: null,
    ultimaObras: [],
    conJornadas: false,
    _dias: new Set(),
    _obras: new Map()
  });

  (Array.isArray(catalogo) ? catalogo : []).forEach(ficha => {
    const nombre = ficha && typeof ficha.nombre === 'string' ? limpiarTexto(ficha.nombre) : '';
    if (!nombre) {
      avisos.fichasInvalidas++;
      return;
    }
    const clave = claveNombre(nombre);
    if (porClave.has(clave)) {
      avisos.fichasRepetidas.push(nombre);
      return;
    }
    const linea = nuevaLinea(nombre, ficha);
    const anteriores = textosDeLista(ficha.nombres_anteriores);
    const fusionados = textosDeLista(ficha.fusionados);
    linea.anteriores = anteriores.lista;
    linea.fusionados = fusionados.lista;
    if (!anteriores.legible || !fusionados.legible) avisos.historialIlegible.push(nombre);
    porClave.set(clave, linea);
  });

  (Array.isArray(filas) ? filas : []).forEach(f => {
    const resultadoFila = clasificarFila(f);
    if (resultadoFila === 'sinHoras') { avisos.filasSinHoras++; return; }
    if (resultadoFila === 'invalida') { avisos.filasInvalidas++; return; }

    const clave = claveNombre(f.nombre);
    let linea = porClave.get(clave);
    if (!linea) {
      linea = nuevaLinea(limpiarTexto(f.nombre), null);
      porClave.set(clave, linea);
      avisos.sinFicha.push(linea.nombre);
    }
    const extra = (f.extra !== undefined && f.extra !== null) ? f.extra : 0;
    linea.conJornadas = true;
    linea.horas += f.horas;
    linea.extra += extra;
    if (!linea.empresa && linea.sinFicha) linea.empresa = empresaDeFila(f);
    if (f.fecha) linea._dias.add(f.fecha);

    if (f.obra) {
      let o = linea._obras.get(f.obra);
      if (!o) {
        o = { obra: f.obra, dias: new Set(), horas: 0, ultima: null };
        linea._obras.set(f.obra, o);
      }
      o.horas += f.horas;
      if (f.fecha) o.dias.add(f.fecha);
      if (esFechaISO(f.fecha) && (o.ultima === null || f.fecha > o.ultima)) o.ultima = f.fecha;
    }
    if (esFechaISO(f.fecha) && (linea.ultima === null || f.fecha > linea.ultima)) linea.ultima = f.fecha;
  });

  let sumaHoras = 0;
  let sumaExtra = 0;
  let cuentaConJornadas = 0;
  let cuentaSinJornadas = 0;

  const personas = Array.from(porClave.values()).map(linea => {
    linea.dias = linea._dias.size;
    linea.obras = Array.from(linea._obras.values())
      .map(o => ({ obra: o.obra, dias: o.dias.size, horas: o.horas, ultima: o.ultima }))
      .sort((a, b) => (b.horas - a.horas) || (a.obra < b.obra ? -1 : a.obra > b.obra ? 1 : 0));
    linea.ultimaObras = linea.obras.filter(o => linea.ultima !== null && o.ultima === linea.ultima).map(o => o.obra).sort();
    delete linea._dias;
    delete linea._obras;
    sumaHoras += linea.horas;
    sumaExtra += linea.extra;
    if (linea.conJornadas) cuentaConJornadas++;
    else cuentaSinJornadas++;
    return linea;
  });
  personas.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));

  const total = {
    personas: personas.length,
    conJornadas: cuentaConJornadas,
    sinJornadas: cuentaSinJornadas,
    horas: sumaHoras,
    extra: sumaExtra
  };
  return { personas, total, avisos };
}

// 12. ordenarBase(personas, por, dir): copia ordenada por cualquier columna de la base.
// 'nombre', 'empresa', 'obras', 'dias', 'horas', 'ultima', 'historia'.
// Sin `dir`, mantiene el orden por defecto ('nombre'/'empresa'/'historia' asc; 'horas'/'dias'/'obras'/'ultima' desc).
// Quien no tiene jornadas (o no tiene empresa / historia en esa columna) va siempre al final.
function ordenarBase(personas, por, dir) {
  const alfabetico = (a, b) => a.nombre.localeCompare(b.nombre, 'es');
  const copia = Array.isArray(personas) ? personas.slice() : [];
  const campo = por || 'nombre';
  const dirPorDefecto = (campo === 'horas' || campo === 'dias' || campo === 'obras' || campo === 'ultima') ? 'desc' : 'asc';
  const dirEfectiva = (dir === 'asc' || dir === 'desc') ? dir : dirPorDefecto;
  const s = dirEfectiva === 'asc' ? 1 : -1;

  if (campo === 'horas') {
    return copia.sort((a, b) => {
      if (a.conJornadas !== b.conJornadas) return a.conJornadas ? -1 : 1;
      return s * (a.horas - b.horas) || alfabetico(a, b);
    });
  }
  if (campo === 'dias') {
    return copia.sort((a, b) => {
      if (a.conJornadas !== b.conJornadas) return a.conJornadas ? -1 : 1;
      return s * (a.dias - b.dias) || s * (a.horas - b.horas) || alfabetico(a, b);
    });
  }
  if (campo === 'obras') {
    return copia.sort((a, b) => {
      if (a.conJornadas !== b.conJornadas) return a.conJornadas ? -1 : 1;
      const oa = Array.isArray(a.obras) ? a.obras.length : 0;
      const ob = Array.isArray(b.obras) ? b.obras.length : 0;
      return s * (oa - ob) || s * (a.horas - b.horas) || alfabetico(a, b);
    });
  }
  if (campo === 'ultima') {
    return copia.sort((a, b) => {
      if ((a.ultima === null) !== (b.ultima === null)) return a.ultima === null ? 1 : -1;
      if (a.ultima !== b.ultima) return s * (a.ultima < b.ultima ? -1 : 1);
      return alfabetico(a, b);
    });
  }
  if (campo === 'empresa') {
    return copia.sort((a, b) => {
      const ea = limpiarTexto(a.empresa);
      const eb = limpiarTexto(b.empresa);
      if (Boolean(ea) !== Boolean(eb)) return ea ? -1 : 1;
      return s * ea.localeCompare(eb, 'es') || alfabetico(a, b);
    });
  }
  if (campo === 'historia') {
    return copia.sort((a, b) => {
      const ha = ((a.anteriores && a.anteriores.length) || 0) + ((a.fusionados && a.fusionados.length) || 0);
      const hb = ((b.anteriores && b.anteriores.length) || 0) + ((b.fusionados && b.fusionados.length) || 0);
      if ((ha > 0) !== (hb > 0)) return ha > 0 ? -1 : 1;
      const ta = [].concat(a.anteriores || [], a.fusionados || []).join(' ');
      const tb = [].concat(b.anteriores || [], b.fusionados || []).join(' ');
      return s * ta.localeCompare(tb, 'es') || alfabetico(a, b);
    });
  }
  return copia.sort((a, b) => s * alfabetico(a, b));
}

// 13. ordenarRanking(trabajadores, por, dir): copia ordenada de las filas de trabajadores del ranking.
function ordenarRanking(trabajadores, por, dir) {
  const alfabetico = (a, b) => a.nombre.localeCompare(b.nombre, 'es');
  const copia = Array.isArray(trabajadores) ? trabajadores.slice() : [];
  const campo = por || 'horas';
  const dirPorDefecto = (campo === 'nombre' || campo === 'empresa') ? 'asc' : 'desc';
  const dirEfectiva = (dir === 'asc' || dir === 'desc') ? dir : dirPorDefecto;
  const s = dirEfectiva === 'asc' ? 1 : -1;

  if (campo === 'nombre') {
    return copia.sort((a, b) => s * alfabetico(a, b));
  }
  if (campo === 'empresa') {
    return copia.sort((a, b) => {
      const ea = limpiarTexto(a.empresa);
      const eb = limpiarTexto(b.empresa);
      if (Boolean(ea) !== Boolean(eb)) return ea ? -1 : 1;
      return s * ea.localeCompare(eb, 'es') || (b.horas - a.horas) || alfabetico(a, b);
    });
  }
  if (campo === 'dias') {
    return copia.sort((a, b) => s * (a.dias - b.dias) || s * (a.horas - b.horas) || alfabetico(a, b));
  }
  if (campo === 'obras') {
    return copia.sort((a, b) => {
      const oa = a.obras ? Object.keys(a.obras).length : 0;
      const ob = b.obras ? Object.keys(b.obras).length : 0;
      return s * (oa - ob) || s * (a.horas - b.horas) || alfabetico(a, b);
    });
  }
  // 'pos', 'horas' o 'pct'
  return copia.sort((a, b) => s * (a.horas - b.horas) || alfabetico(a, b));
}

// 14. resumenEmpresas(filas, catalogo): vista completa de empresas cruzando la base de trabajadores y las jornadas
// filtradas. Incluye empresas que están en la base aunque aún no tengan jornadas en el periodo, desglose de obras y
// plantilla de cada empresa.
function resumenEmpresas(filas, catalogo) {
  const base = baseTrabajadores(filas, catalogo);
  const porEmp = agregarPorEmpresa(filas);
  const totalHoras = porEmp.total ? porEmp.total.horas : 0;

  const grupos = new Map();
  const asegurarGrupo = textoEmpresa => {
    const limpio = empresaDeFila({ empresa: textoEmpresa });
    const clave = claveEmpresa(limpio);
    const sinEmpresa = clave === '';
    let g = grupos.get(clave);
    if (!g) {
      const autonomo = !sinEmpresa && esAutonomo(limpio);
      g = {
        nombre: sinEmpresa ? ETIQUETA_SIN_EMPRESA : limpio,
        clave,
        sinEmpresa,
        autonomo,
        tipo: sinEmpresa ? ETIQUETA_SIN_EMPRESA : (autonomo ? 'Autónomo (@AUT)' : 'Empresa'),
        enBase: 0,
        activosEnBase: 0,
        personasSet: new Set(),
        diasSet: new Set(),
        horas: 0,
        extra: 0,
        obrasMap: new Map(),
        ultima: null,
        trabajadoresMap: new Map()
      };
      grupos.set(clave, g);
    }
    return g;
  };

  // 1) Personas de la base
  base.personas.forEach(p => {
    if (!p.sinFicha) {
      const g = asegurarGrupo(p.empresa);
      g.enBase++;
      if (p.activo) g.activosEnBase++;
      g.trabajadoresMap.set(claveNombre(p.nombre), {
        nombre: p.nombre,
        empresa: g.sinEmpresa ? '' : g.nombre,
        categoria: p.categoria || '',
        horarioPreferido: p.horarioPreferido || null,
        activo: p.activo,
        enBase: true,
        conJornadas: p.conJornadas,
        dias: p.dias,
        horas: p.horas,
        extra: p.extra,
        obras: p.obras,
        ultima: p.ultima,
        ultimaObras: p.ultimaObras,
        anteriores: p.anteriores,
        fusionados: p.fusionados
      });
    }
  });

  // 2) Jornadas del periodo
  (Array.isArray(filas) ? filas : []).forEach(f => {
    if (clasificarFila(f) !== 'valida') return;
    const g = asegurarGrupo(empresaDeFila(f));
    const extraVal = (f.extra !== undefined && f.extra !== null) ? f.extra : 0;
    const diaDePersona = f.nombre + '\n' + f.fecha;
    g.personasSet.add(f.nombre);
    if (f.fecha) g.diasSet.add(diaDePersona);
    g.horas += f.horas;
    g.extra += extraVal;
    if (esFechaISO(f.fecha) && (g.ultima === null || f.fecha > g.ultima)) {
      g.ultima = f.fecha;
    }
    if (f.obra) {
      let o = g.obrasMap.get(f.obra);
      if (!o) {
        o = { obra: f.obra, diasSet: new Set(), personasSet: new Set(), horas: 0, ultima: null };
        g.obrasMap.set(f.obra, o);
      }
      o.horas += f.horas;
      o.personasSet.add(f.nombre);
      if (f.fecha) o.diasSet.add(diaDePersona);
      if (esFechaISO(f.fecha) && (o.ultima === null || f.fecha > o.ultima)) o.ultima = f.fecha;
    }
    const cNom = claveNombre(f.nombre);
    if (!g.trabajadoresMap.has(cNom)) {
      const pBase = base.personas.find(x => claveNombre(x.nombre) === cNom);
      if (pBase) {
        g.trabajadoresMap.set(cNom, {
          nombre: pBase.nombre,
          empresa: g.sinEmpresa ? '' : g.nombre,
          categoria: pBase.categoria || '',
          horarioPreferido: pBase.horarioPreferido || null,
          activo: pBase.activo,
          enBase: !pBase.sinFicha,
          conJornadas: pBase.conJornadas,
          dias: pBase.dias,
          horas: pBase.horas,
          extra: pBase.extra,
          obras: pBase.obras,
          ultima: pBase.ultima,
          ultimaObras: pBase.ultimaObras,
          anteriores: pBase.anteriores,
          fusionados: pBase.fusionados
        });
      }
    }
  });

  let empresasRegulares = 0;
  let autonomosTotal = 0;
  let enBaseConEmpresa = 0;
  let enBaseSinEmpresa = 0;

  const empresas = Array.from(grupos.values()).map(g => {
    if (g.sinEmpresa) {
      enBaseSinEmpresa += g.enBase;
    } else {
      enBaseConEmpresa += g.enBase;
      if (g.autonomo) autonomosTotal++;
      else empresasRegulares++;
    }
    const obras = Array.from(g.obrasMap.values())
      .map(o => ({
        obra: o.obra,
        dias: o.diasSet.size,
        personas: o.personasSet.size,
        horas: o.horas,
        ultima: o.ultima
      }))
      .sort((a, b) => (b.horas - a.horas) || (a.obra < b.obra ? -1 : a.obra > b.obra ? 1 : 0));
    const ultimaObras = obras.filter(o => g.ultima !== null && o.ultima === g.ultima).map(o => o.obra).sort();
    const trabajadores = ordenarBase(Array.from(g.trabajadoresMap.values()), 'horas', 'desc');
    return {
      nombre: g.nombre,
      clave: g.clave,
      sinEmpresa: g.sinEmpresa,
      autonomo: g.autonomo,
      tipo: g.tipo,
      enBase: g.enBase,
      activosEnBase: g.activosEnBase,
      personas: g.personasSet.size,
      dias: g.diasSet.size,
      horas: g.horas,
      extra: g.extra,
      pct: totalHoras > 0 ? (100 * g.horas / totalHoras) : null,
      obras,
      ultima: g.ultima,
      ultimaObras,
      trabajadores
    };
  });

  const ordenadas = ordenarEmpresas(empresas, 'horas', 'desc');
  return {
    empresas: ordenadas,
    autonomos: porEmp.autonomos,
    avisos: porEmp.avisos,
    totales: {
      empresas: empresasRegulares,
      autonomos: autonomosTotal,
      enBaseConEmpresa,
      enBaseSinEmpresa,
      enBaseTotal: enBaseConEmpresa + enBaseSinEmpresa,
      personasConJornadas: porEmp.total ? porEmp.total.personas : 0,
      dias: porEmp.total ? porEmp.total.dias : 0,
      horas: totalHoras
    }
  };
}

// 15. empresasConocidas(filas, catalogo): lista ordenada de nombres de empresa conocidos (sin «Sin empresa»).
function empresasConocidas(filas, catalogo) {
  const mapa = new Map();
  const anadir = raw => {
    const limpio = empresaDeFila({ empresa: raw });
    if (!limpio) return;
    const k = claveEmpresa(limpio);
    if (!mapa.has(k)) mapa.set(k, limpio);
  };
  anadir('Sagarde');
  (Array.isArray(catalogo) ? catalogo : []).forEach(c => anadir(c && c.empresa));
  (Array.isArray(filas) ? filas : []).forEach(f => anadir(f && f.empresa));
  return Array.from(mapa.values()).sort((a, b) => a.localeCompare(b, 'es'));
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
  htmlPorEmpresa,
  claveNombre,
   claveEmpresa,
  baseTrabajadores,
  ordenarBase,
  ordenarRanking,
  ordenarEmpresas,
  resumenEmpresas,
  empresasConocidas
};

if (typeof module !== 'undefined' && module.exports) { module.exports = API; }
if (typeof window !== 'undefined') { window.PersonalCalculo = API; }
