# -*- coding: utf-8 -*-
"""Vista de personal asignado para el panel de obra de Sagarde.

Este módulo proporciona la vista interactiva de la pestaña «Personal» en el panel
de obra, permitiendo filtrar jornadas por periodo y ámbito, consultar KPIs globales,
la tabla de horas por trabajador y barras de impacto relativo.
"""

import datetime
import html
import json
import os
import re

_CSS_PANEL_PERSONAL = """\
#pers-raiz {
  font-family: inherit;
  color: var(--text, #1c2733);
  line-height: 1.5;
}
#pers-raiz * {
  box-sizing: border-box;
}
#pers-raiz .pers-ctl {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
}
#pers-raiz .pers-seg {
  display: inline-flex;
  align-items: center;
  background: var(--bg, #f4f6f9);
  border: 1px solid var(--line, #e2e8f0);
  border-radius: 8px;
  padding: 2px;
  gap: 2px;
  max-width: 100%;
  min-width: 0;
}
#pers-raiz .pers-seg button {
  border: none;
  background: transparent;
  color: var(--text, #1c2733);
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease, color 0.15s ease;
}
#pers-raiz .pers-seg button:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.05);
}
#pers-raiz .pers-seg button.on {
  background: var(--header, #0b1f3a);
  color: #fff;
}
#pers-raiz .pers-seg button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
#pers-raiz button[data-pers-m] {
  width: 44px;
  font-size: 18px;
  font-weight: 700;
  padding: 0;
}
#pers-raiz #pers-etiqueta {
  font-size: 13px;
  font-weight: 700;
  color: var(--text, #1c2733);
  padding: 0 10px;
  text-align: center;
  white-space: nowrap;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
#pers-raiz .pers-kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
#pers-raiz .pers-kpi {
  background: var(--bg, #f4f6f9);
  border: 1px solid var(--line, #e2e8f0);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
#pers-raiz .pers-kpi b {
  font-size: 22px;
  font-weight: 700;
  color: var(--header, #0b1f3a);
  line-height: 1.2;
}
#pers-raiz .pers-kpi span {
  font-size: 12px;
  color: var(--muted, #647184);
}
#pers-raiz .pers-aviso {
  background: #fff4e5;
  border: 1px solid var(--warn, #e07b1a);
  color: #7a4c00;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 14px;
  font-size: 13px;
  line-height: 1.4;
}
#pers-raiz .pers-vacio {
  color: var(--muted, #647184);
  font-size: 13.5px;
  padding: 16px 4px;
}
#pers-raiz .pers-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin-bottom: 20px;
}
#pers-raiz .pers-tabla {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
#pers-raiz .pers-tabla th {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 2px solid var(--line, #e3e7ee);
  color: var(--muted, #647184);
  font-weight: 700;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
#pers-raiz .pers-tabla td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--line, #eef1f5);
}
#pers-raiz .pers-tabla td:first-child {
  overflow-wrap: anywhere;
  word-break: break-word;
}
#pers-raiz .pers-tabla tr:hover td {
  background: rgba(0, 0, 0, 0.02);
}
#pers-raiz .pers-tabla .n {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
#pers-raiz .pers-tabla tfoot tr td {
  border-top: 2px solid var(--line, #e3e7ee);
  border-bottom: none;
  font-weight: 700;
  padding-top: 10px;
}
#pers-raiz .pers-ih {
  font-size: 14px;
  font-weight: 700;
  color: var(--header, #0b1f3a);
  margin: 22px 0 12px 0;
}
#pers-raiz .pers-impacto {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 13px;
}
#pers-raiz .pers-nom {
  width: 130px;
  max-width: 130px;
  flex: 0 0 130px;
  font-weight: 600;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.2;
}
#pers-raiz .pers-bar {
  flex: 1;
  height: 14px;
  background: var(--bg, #eef1f5);
  border-radius: 7px;
  overflow: hidden;
  position: relative;
  min-width: 60px;
}
#pers-raiz .pers-bar i {
  display: block;
  height: 100%;
  border-radius: 7px;
  background: var(--accent2, #2e7dd7);
  transition: width 0.25s ease;
}
#pers-raiz .pers-bar.top i {
  background: var(--accent, #f5a524);
}
#pers-raiz .pers-impacto b {
  width: 55px;
  max-width: 55px;
  flex: 0 0 55px;
  text-align: right;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
#pers-raiz .pers-nota {
  font-size: 11.5px;
  color: var(--muted, #647184);
  margin-top: 14px;
  line-height: 1.4;
}
@media (max-width: 480px) {
  #pers-raiz .pers-tabla {
    font-size: 11px;
  }
  #pers-raiz .pers-tabla th,
  #pers-raiz .pers-tabla td {
    padding: 4px 2px;
  }
  #pers-raiz .pers-tabla th {
    white-space: normal;
    line-height: 1.15;
  }
  #pers-raiz .pers-tabla td:first-child {
    max-width: 90px;
  }
  #pers-raiz .pers-nom {
    width: 90px;
    max-width: 90px;
    flex: 0 0 90px;
    font-size: 12px;
  }
  #pers-raiz .pers-impacto b {
    width: 45px;
    max-width: 45px;
    flex: 0 0 45px;
    font-size: 12px;
  }
  #pers-raiz .pers-kpis {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  #pers-raiz .pers-kpi {
    padding: 8px 10px;
  }
  #pers-raiz .pers-kpi b {
    font-size: 18px;
  }
  #pers-raiz .pers-seg button {
    padding: 6px 10px;
    font-size: 12px;
  }
}
"""

_JS_VISTA_PERSONAL = """\
(function () {
  'use strict';

  var raiz = document.getElementById('pers-raiz');
  if (!raiz) return;

  var datosEl = document.getElementById('pers-datos');
  if (!datosEl) return;

  var filas = [];
  try {
    filas = JSON.parse(datosEl.textContent);
  } catch (errJson) {
    mostrarError(errJson);
    return;
  }

  // Estado inicial: periodo 'mes', ámbito 'todo', referencia = fecha más reciente
  var periodo = 'mes';
  var ambito = 'todo';
  var ref = '';

  for (var i = 0; i < filas.length; i++) {
    var f = filas[i];
    if (f && typeof f.fecha === 'string') {
      if (!ref || f.fecha > ref) {
        ref = f.fecha;
      }
    }
  }

  var MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
  ];

  function formatearNum(x) {
    // Un dato ausente se distingue de cero en toda la presentación.
    if (x === null || x === undefined || typeof x !== 'number' || isNaN(x)) {
      return '–';
    }
    return String(Math.round(x * 10) / 10).replace('.', ',');
  }

  function escaparHtml(str) {
    // Los nombres se insertan como marcado generado y por eso requieren escape explícito.
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function mostrarError(error) {
    // Un fallo al calcular o pintar tiene que verse en la pestaña: nunca una vista vacía en silencio.
    var contenedor = document.getElementById('pers-contenido');
    if (contenedor) {
      contenedor.innerHTML = '<p class="pers-aviso">⚠ No se pudo calcular el personal: ' +
        escaparHtml(error && error.message ? error.message : String(error)) + '</p>';
    }
  }

  function obtenerTextoEtiqueta(p, r) {
    // El motor fija los límites; aquí únicamente se da formato legible a esos datos.
    if (p === 'obra') {
      return 'Toda la obra';
    }
    if (p === 'anio') {
      return r ? r.slice(0, 4) : '';
    }
    if (p === 'mes') {
      if (!r || r.length < 7) return '';
      var anio = r.slice(0, 4);
      var mesNum = parseInt(r.slice(5, 7), 10);
      var nombreMes = (mesNum >= 1 && mesNum <= 12) ? MESES[mesNum - 1] : '';
      return nombreMes + ' ' + anio;
    }
    if (p === 'semana') {
      if (!window.PersonalCalculo) return '';
      var numSemana = window.PersonalCalculo.semanaISO(r);
      var rango = window.PersonalCalculo.rangoPeriodo('semana', r);
      if (!rango || !rango.desde || !rango.hasta) return '';
      var diaD = rango.desde.slice(8, 10);
      var mesD = rango.desde.slice(5, 7);
      var diaH = rango.hasta.slice(8, 10);
      var mesH = rango.hasta.slice(5, 7);
      return 'Semana ' + numSemana + ' · ' + diaD + '/' + mesD + ' – ' + diaH + '/' + mesH;
    }
    return '';
  }

  function actualizarControles() {
    // Se mutan los controles existentes para conservar tanto el foco como el teclado.
    var btnsP = raiz.querySelectorAll('[data-pers-p]');
    for (var i = 0; i < btnsP.length; i++) {
      var bp = btnsP[i];
      var activoP = bp.getAttribute('data-pers-p') === periodo;
      if (activoP) {
        bp.classList.add('on');
        bp.setAttribute('aria-pressed', 'true');
      } else {
        bp.classList.remove('on');
        bp.setAttribute('aria-pressed', 'false');
      }
    }

    var btnsA = raiz.querySelectorAll('[data-pers-a]');
    for (var j = 0; j < btnsA.length; j++) {
      var ba = btnsA[j];
      var activoA = ba.getAttribute('data-pers-a') === ambito;
      if (activoA) {
        ba.classList.add('on');
        ba.setAttribute('aria-pressed', 'true');
      } else {
        ba.classList.remove('on');
        ba.setAttribute('aria-pressed', 'false');
      }
    }

    var btnsM = raiz.querySelectorAll('[data-pers-m]');
    for (var k = 0; k < btnsM.length; k++) {
      btnsM[k].disabled = (periodo === 'obra');
    }

    var etq = document.getElementById('pers-etiqueta');
    if (etq) {
      etq.textContent = obtenerTextoEtiqueta(periodo, ref);
    }
  }

  function pintarContenido() {
    // La vista consume los resultados del motor sin reproducir sus cálculos.
    var contenedor = document.getElementById('pers-contenido');
    if (!contenedor) return;

    if (!window.PersonalCalculo) {
      contenedor.innerHTML =
        '<p class="pers-aviso">⚠ No se pudo calcular el personal: ' +
        'motor PersonalCalculo no disponible.</p>';
      return;
    }

    var filtradas = window.PersonalCalculo.filtrar(filas, {
      ambito: ambito,
      periodo: periodo,
      ref: ref
    });

    var res = window.PersonalCalculo.agregar(filtradas);
    var trabajadores = res.trabajadores || [];
    var total = res.total;
    var avisos = res.avisos || {};

    var sinH = avisos.filasSinHoras || 0;
    var inv = avisos.filasInvalidas || 0;

    var avisoHtml = '';
    if (sinH > 0 || inv > 0) {
      var partes = [];
      if (sinH > 0) {
        partes.push(sinH === 1 ? '1 sin horas' : (sinH + ' sin horas'));
      }
      if (inv > 0) {
        partes.push(inv + ' con datos no válidos');
      }
      avisoHtml = '<p class="pers-aviso">⚠ Filas que no se han contado: ' +
        partes.join(', ') + '.</p>';
    }

    if (total === null) {
      // La ausencia de jornadas válidas no equivale a un total numérico de cero.
      contenedor.innerHTML = avisoHtml +
        '<p class="empty pers-vacio">Sin jornadas anotadas en este periodo ' +
        '(no es lo mismo que 0 horas).</p>';
      return;
    }

    var html = '';

    // 1. Cuatro KPI
    html += '<div class="pers-kpis">' +
      '<div class="pers-kpi"><b>' + total.trabajadores + '</b><span>trabajadores</span></div>' +
      '<div class="pers-kpi"><b>' + formatearNum(total.horas) + ' h</b><span>horas totales</span></div>' +
      '<div class="pers-kpi"><b>' + formatearNum(total.extra) + ' h</b><span>de ellas extra</span></div>' +
      '<div class="pers-kpi"><b>' + total.dias + '</b><span>días con gente</span></div>' +
      '</div>';

    // 2. Aviso de filas no contadas
    if (avisoHtml) {
      html += avisoHtml;
    }

    // 3. Tabla por trabajador y totales
    html += '<div class="pers-scroll"><table class="pers-tabla">' +
      '<thead><tr>' +
      '<th>Nombre</th>' +
      '<th class="n">Días</th>' +
      '<th class="n">H. ordinarias</th>' +
      '<th class="n">H. extra</th>' +
      '<th class="n">Total h</th>' +
      '<th class="n">% impacto</th>' +
      '</tr></thead><tbody>';

    for (var tIdx = 0; tIdx < trabajadores.length; tIdx++) {
      var t = trabajadores[tIdx];
      var pctStr = (t.pct !== null) ? (formatearNum(t.pct) + ' %') : '–';
      html += '<tr>' +
        '<td><b>' + escaparHtml(t.nombre) + '</b></td>' +
        '<td class="n">' + t.dias + '</td>' +
        '<td class="n">' + formatearNum(t.ordinarias) + '</td>' +
        '<td class="n">' + formatearNum(t.extra) + '</td>' +
        '<td class="n">' + formatearNum(t.horas) + '</td>' +
        '<td class="n">' + pctStr + '</td>' +
        '</tr>';
    }

    var pctTotalStr = (total.horas > 0) ? '100 %' : '–';
    html += '</tbody><tfoot><tr>' +
      '<td>Total</td>' +
      '<td></td>' +
      '<td class="n">' + formatearNum(total.ordinarias) + '</td>' +
      '<td class="n">' + formatearNum(total.extra) + '</td>' +
      '<td class="n">' + formatearNum(total.horas) + '</td>' +
      '<td class="n">' + pctTotalStr + '</td>' +
      '</tr></tfoot></table></div>';

    // 4 y 5. Barras de impacto y nota explicativa (solo si total.horas > 0)
    if (total.horas > 0 && trabajadores.length > 0) {
      html += '<h4 class="pers-ih">Impacto en la obra · % de horas-hombre</h4>';
      var pctMax = trabajadores[0].pct || 1;
      // El primer elemento ya es el máximo porque agregar entrega el orden contractual.
      for (var bIdx = 0; bIdx < trabajadores.length; bIdx++) {
        var tb = trabajadores[bIdx];
        var valPct = tb.pct || 0;
        var ancho = (100 * valPct / pctMax).toFixed(1) + '%';
        var claseBar = (bIdx === 0) ? 'pers-bar top' : 'pers-bar';
        html += '<div class="pers-impacto">' +
          '<span class="pers-nom">' + escaparHtml(tb.nombre) + '</span>' +
          '<div class="' + claseBar + '"><i style="width:' + ancho + '"></i></div>' +
          '<b>' + formatearNum(tb.pct) + ' %</b>' +
          '</div>';
      }
      html += '<p class="pers-nota">% = horas del trabajador ÷ horas totales en el periodo ' +
        'y el filtro elegidos. La barra naranja es la de mayor impacto. Los porcentajes se ' +
        'redondean a 1 decimal; por eso pueden sumar 99,9 o 100,1.</p>';
    }

    contenedor.innerHTML = html;
  }

  function repintar() {
    // Primero los controles y luego el contenido; un fallo de cálculo se muestra, no se traga.
    try {
      actualizarControles();
      pintarContenido();
    } catch (error) {
      mostrarError(error);
    }
  }

  raiz.addEventListener('click', function (evento) {
    // La delegación evita reconstruir botones y mantiene estable el elemento enfocado.
    var btn = evento.target.closest('button');
    if (!btn || !raiz.contains(btn)) return;

    if (btn.hasAttribute('data-pers-p')) {
      periodo = btn.getAttribute('data-pers-p');
    } else if (btn.hasAttribute('data-pers-a')) {
      ambito = btn.getAttribute('data-pers-a');
    } else if (btn.hasAttribute('data-pers-m')) {
      // Con el periodo «obra» no hay a dónde moverse (los botones ya van deshabilitados).
      if (periodo === 'obra' || !window.PersonalCalculo) return;
      var paso = parseInt(btn.getAttribute('data-pers-m'), 10);
      if (isNaN(paso)) return;
      try {
        ref = window.PersonalCalculo.mover(periodo, ref, paso);
      } catch (error) {
        mostrarError(error);
        return;
      }
    } else {
      return;
    }
    repintar();
  });

  repintar();
})();
"""

_PLANTILLA_HTML = """\
<div id="pers-raiz" class="pers" data-obra="__OBRA_ID__">
  <style>
__CSS__
  </style>
  <div class="pers-ctl">
    <div class="pers-seg">
      <button type="button" data-pers-p="semana" aria-pressed="false">Semana</button>
      <button type="button" data-pers-p="mes" class="on" aria-pressed="true">Mes</button>
      <button type="button" data-pers-p="anio" aria-pressed="false">Año</button>
      <button type="button" data-pers-p="obra" aria-pressed="false">Obra</button>
    </div>
    <div class="pers-seg">
      <button type="button" data-pers-m="-1" aria-label="Periodo anterior">‹</button>
      <span id="pers-etiqueta" aria-live="polite"></span>
      <button type="button" data-pers-m="1" aria-label="Periodo siguiente">›</button>
    </div>
    <div class="pers-seg">
      <button type="button" data-pers-a="todo" class="on" aria-pressed="true">Todo</button>
      <button type="button" data-pers-a="vivienda" aria-pressed="false">Viviendas</button>
      <button type="button" data-pers-a="garaje" aria-pressed="false">Garajes</button>
    </div>
  </div>
  <div id="pers-contenido">
    <p class="pers-aviso">Cargando personal…</p>
  </div>
  <script>
__SCRIPT_CALCULO__
  </script>
  <script id="pers-datos" type="application/json">__DATOS_JSON__</script>
  <script>
__SCRIPT_VISTA__
  </script>
</div>"""


def _leer_personal_calculo_js() -> str:
    """Carga personal_calculo.js de la misma carpeta y lo envuelve en una IIFE."""
    # Resolver desde __file__ mantiene el módulo independiente del directorio de ejecución.
    directorio = os.path.dirname(os.path.abspath(__file__))
    ruta_fichero = os.path.join(directorio, "personal_calculo.js")
    with open(ruta_fichero, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Salvaguarda de inyección o ruptura de script HTML
    if re.search(r"</script", contenido, flags=re.IGNORECASE) or "<!--" in contenido:
        raise ValueError(
            "personal_calculo.js contiene secuencias no permitidas ('</script' o '<!--')."
        )

    # Envuelve en funcion autoejecutada para aislar variables del ámbito global
    contenido_limpio = contenido.rstrip("\r\n")
    return f"(function () {{\n{contenido_limpio}\n}})();"


def _validar_entradas(obra_id: str, filas_planas: list) -> None:
    """Valida los tipos y restricciones de las entradas antes de construir la vista."""
    # Fallar antes de generar HTML evita producir fragmentos parciales o ambiguos.
    if not isinstance(obra_id, str) or not obra_id.strip():
        raise ValueError("El identificador de obra ('obra_id') debe ser un texto no vacío.")

    if not isinstance(filas_planas, list):
        raise ValueError("El parámetro 'filas_planas' debe ser una lista de diccionarios.")

    claves_requeridas = {"fecha", "ambito", "nombre", "horas"}
    claves_permitidas = {"fecha", "ambito", "nombre", "horas", "extra"}

    for idx, fila in enumerate(filas_planas, start=1):
        # La numeración humana comienza en uno para localizar la fila en el origen.
        if not isinstance(fila, dict):
            raise ValueError(f"Fila {idx}: debe ser un diccionario, no {type(fila).__name__}.")

        claves = set(fila.keys())
        # Se rechazan claves desconocidas para detectar pronto errores de integración.
        desconocidas = claves - claves_permitidas
        if desconocidas:
            raise ValueError(
                f"Fila {idx}: contiene claves no permitidas: {sorted(desconocidas)}."
            )

        faltantes = claves_requeridas - claves
        if faltantes:
            raise ValueError(
                f"Fila {idx}: faltan claves requeridas: {sorted(faltantes)}."
            )

        fecha = fila["fecha"]
        if not isinstance(fecha, str) or len(fecha) != 10:
            raise ValueError(
                f"Fila {idx}: la fecha debe tener formato YYYY-MM-DD (recibido {fecha!r})."
            )
        try:
            # fromisoformat verifica días reales, incluidos bisiestos y límites mensuales.
            d = datetime.date.fromisoformat(fecha)
            if d.isoformat() != fecha:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError(
                f"Fila {idx}: la fecha '{fecha}' no es una fecha real válida en formato YYYY-MM-DD."
            )

        ambito = fila["ambito"]
        if ambito not in ("vivienda", "garaje"):
            raise ValueError(
                f"Fila {idx}: ámbito '{ambito}' no válido (debe ser 'vivienda' o 'garaje')."
            )

        nombre = fila["nombre"]
        if not isinstance(nombre, str):
            raise ValueError(
                f"Fila {idx}: el nombre debe ser texto (recibido {type(nombre).__name__})."
            )

        horas = fila["horas"]
        if isinstance(horas, bool) or (
            horas is not None
            and not (
                isinstance(horas, (int, float))
                and horas == horas
                and abs(horas) != float("inf")
            )
        ):
            raise ValueError(
                f"Fila {idx}: las horas deben ser None o un número finito, sin booleanos "
                f"(recibido {horas!r})."
            )

        if "extra" in fila:
            extra = fila["extra"]
            if isinstance(extra, bool) or (
                extra is not None
                and not (
                    isinstance(extra, (int, float))
                    and extra == extra
                    and abs(extra) != float("inf")
                )
            ):
                raise ValueError(
                    f"Fila {idx}: las horas extra deben ser None o un número finito, sin booleanos "
                    f"(recibido {extra!r})."
                )


def vista_personal(obra_id: str, filas_planas: list) -> str:
    """Genera el fragmento HTML autocontenido para la pestaña de personal de una obra."""
    _validar_entradas(obra_id, filas_planas)

    # Si la lista viene vacía se muestra mensaje neutro sin inyectar scripts ni estilos
    if not filas_planas:
        return '<p class="empty pers-vacio">Sin jornadas de personal anotadas en esta obra.</p>'

    # Una copia evita modificar diccionarios que siguen perteneciendo al llamador.
    # Añadir al final preserva exactamente el orden original de sus claves.
    filas_con_obra = []
    for f in filas_planas:
        fila_dict = dict(f)
        fila_dict["obra"] = obra_id
        filas_con_obra.append(fila_dict)

    json_compacto = json.dumps(
        filas_con_obra,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )

    # El escape impide cerrar el bloque script sin alterar los datos tras JSON.parse.
    json_escapado = (
        json_compacto
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

    valores = {
        "OBRA_ID": html.escape(obra_id, quote=True),
        "CSS": _CSS_PANEL_PERSONAL,
        "SCRIPT_CALCULO": _leer_personal_calculo_js(),
        "DATOS_JSON": json_escapado,
        "SCRIPT_VISTA": _JS_VISTA_PERSONAL,
    }
    # Una sola pasada sobre la plantilla: con varios .replace seguidos, un nombre de trabajador
    # (texto libre) que fuera «__SCRIPT_VISTA__» se volvería a sustituir y rompería los datos.
    return re.sub(r"__(OBRA_ID|CSS|SCRIPT_CALCULO|DATOS_JSON|SCRIPT_VISTA)__",
                  lambda coincidencia: valores[coincidencia.group(1)], _PLANTILLA_HTML)
