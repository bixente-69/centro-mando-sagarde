# -*- coding: utf-8 -*-
"""
PANEL DE OBRA — 9 secciones (capa 3)
-------------------------------------
Genera un panel HTML por obra con navegacion de pestanas:
  Panel · Trabajos · Materiales · Personal · Prioridades · Riesgos · Normativa · Documentos · Actualizar

Consume datos ya normalizados:
  historial   -> de motor_informes (avance/bloqueos)
  materiales  -> de lectores.leer_materiales
  ficha       -> de lectores.leer_ficha
  documentos  -> de lectores.listar_documentos

No sabe leer archivos: eso lo hacen los adaptadores/lectores. Aqui solo se
calcula y se pinta.
"""
import html as html_lib
import json
import os
from datetime import datetime

import motor_informes as motor

ESTILOS = """
:root{
  --bg:#f4f6f9;--card:#fff;--header:#0b1f3a;--header2:#123a63;--text:#1c2733;
  --muted:#647184;--accent:#f5a524;--accent2:#2e7dd7;--ok:#2e9e5b;--warn:#e07b1a;--bad:#d9483c;
  --radius:10px;--gap:16px;
}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.5;}
.wrap{max-width:1320px;margin:0 auto;padding:18px;}
.header{background:linear-gradient(120deg,var(--header),var(--header2));color:#fff;border-radius:var(--radius);padding:20px 26px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;}
.header .brand{font-size:11.5px;letter-spacing:1.5px;text-transform:uppercase;color:var(--accent);font-weight:700;}
.header h1{font-size:21px;font-weight:700;margin-top:2px;}
.header .sub{font-size:12.5px;color:#c7d3e3;margin-top:4px;}
.header .meta{text-align:right;font-size:12px;color:#c7d3e3;}
.header a.volver{color:#fff;text-decoration:none;font-size:12.5px;border:1px solid rgba(255,255,255,.35);padding:5px 11px;border-radius:6px;display:inline-block;margin-top:6px;}
.header a.volver:hover{background:rgba(255,255,255,.12);}
.nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;}
.nav button{border:none;background:#fff;color:var(--text);padding:9px 15px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.07);}
.nav button.active{background:var(--header);color:#fff;}
.view{display:none;}
.view.active{display:block;}
.banner{background:#fff4e5;border:1px solid var(--accent);color:#7a4c00;border-radius:var(--radius);padding:11px 16px;margin-bottom:14px;font-size:13px;}
.banner.bad{background:#fdecea;border-color:var(--bad);color:#7a231c;}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:var(--gap);margin-bottom:var(--gap);}
.kpi{background:var(--card);border-radius:var(--radius);padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.07);}
.kpi .label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;}
.kpi .value{font-size:25px;font-weight:700;margin-top:5px;}
.kpi .hint{font-size:11.5px;color:var(--muted);margin-top:3px;}
.chart-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:var(--gap);margin-bottom:var(--gap);}
.card{background:var(--card);border-radius:var(--radius);padding:18px 22px;box-shadow:0 1px 3px rgba(0,0,0,.07);margin-bottom:var(--gap);}
.card h3{font-size:14px;font-weight:700;margin-bottom:12px;}
.card canvas{max-height:300px;}
.table-scroll{overflow-x:auto;}
table.data{width:100%;border-collapse:collapse;font-size:13px;}
table.data thead th{text-align:left;padding:8px 10px;border-bottom:2px solid #e3e7ee;color:var(--muted);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.4px;}
table.data tbody td{padding:8px 10px;border-bottom:1px solid #eef1f5;}
table.data tbody tr:hover{background:#f8f9fb;}
.badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700;}
.badge.bad{background:#fdecea;color:var(--bad);}.badge.warn{background:#fff4e5;color:var(--warn);}.badge.ok{background:#e8f6ee;color:var(--ok);}
.badge.f1{background:#e8f0fc;color:#1a3a7a;}.badge.f3{background:#f0f0f0;color:#4a5568;}.badge.f4{background:#f5f5f5;color:#718096;}
.empty{color:var(--muted);font-size:13.5px;padding:16px 4px;}
.doc-cat{font-size:12px;font-weight:700;color:var(--header2);text-transform:uppercase;letter-spacing:.5px;margin:14px 0 6px;}
.doc a{color:var(--accent2);text-decoration:none;}.doc a:hover{text-decoration:underline;}
.norm li{margin:6px 0 6px 18px;font-size:13.5px;}
.footer{text-align:center;font-size:11.5px;color:var(--muted);padding:16px 0;}
@media(max-width:768px){.header{flex-direction:column;}.kpi-row{grid-template-columns:repeat(2,1fr);}.chart-row{grid-template-columns:1fr;}}
"""

NORMATIVA_ITEMS = [
    "REBT — Reglamento Electrotécnico para Baja Tensión (RD 842/2002) e ITC-BT aplicables. Verificar versión vigente.",
    "ITC-BT-10 / previsión de cargas; ITC-BT-25 (viviendas); ITC-BT-28 (locales pública concurrencia) según aplique.",
    "Normativa ICT vigente (RD 346/2011 y reglamento posterior) para telecomunicaciones. Verificar versión.",
    "Normas particulares de i-DE / Iberdrola para acometida, CGP y CT cuando sean de aplicación.",
    "Normas UNE aplicables al proyecto (verificar edición vigente).",
    "Normativa autonómica de Euskadi y ordenanzas municipales aplicables.",
    "Proyecto eléctrico y de telecomunicaciones de la obra e instrucciones de la Dirección Facultativa.",
    "Inspección OCA / Industria antes de la puesta en servicio cuando proceda.",
]


def _fmt_num(n):
    try:
        return f"{n:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return str(n)


def _e(valor):
    return html_lib.escape(str(valor if valor not in (None, '') else '—'))


def _e_atributo(valor):
    """Escapa un atributo sin sustituir por un guión los valores vacíos."""
    return html_lib.escape(str('' if valor is None else valor), quote=True)


def _ub_div(ubicacion):
    unidades = ubicacion.get('unidades') or [ubicacion.get('unidad')]
    unidades = [u for u in unidades if u not in (None, '')]
    unidades_txt = ', '.join(str(x) for x in unidades[:10]) or '—'
    if len(unidades) > 10:
        unidades_txt += f" (+{len(unidades) - 10})"
    return (f"<div style='margin-bottom:3px;'><b>{_e(ubicacion.get('edificio'))} · "
            f"planta {_e(ubicacion.get('planta'))}</b>: {_e(unidades_txt)}</div>")


def _ubicaciones_html(ubicaciones, limite=4):
    visibles = ''.join(_ub_div(u) for u in ubicaciones[:limite])
    extra = ''.join(_ub_div(u) for u in ubicaciones[limite:])
    n_extra = max(0, len(ubicaciones) - limite)
    if n_extra:
        return (visibles + f"<div class='ub-extra' style='display:none;'>{extra}</div>"
                + f"<a href='#' class='show-ub' data-n='{n_extra}' "
                  "style='font-size:11.5px;color:var(--accent2);'>"
                + f"+{n_extra} ubicaciones más</a>")
    return visibles or '—'


_DUDA_ETIQUETAS = {
    "NO_QUITAR_X":          "Revisar en obra",
    "TAJO_NUEVO":           "Tajo no reconocido",
    "OMITIDO_SIN_X":        "Desapareció sin terminar",
    "ALCANCE_POSTAPERTURA": "Alcance por confirmar",
    "ESTADOS_DUPLICADOS":   "Estado duplicado en hoja",
}

_ORDEN_ETIQUETAS = {
    "ORDEN_SIN_CONFIRMAR":          "Sin posición en la secuencia",
    "TAJO_FUERA_DEL_CATALOGO":      "No está en el catálogo",
    "TAJO_DUPLICADO_EN_LA_BASE":    "Dos filas para el mismo tajo",
    "DEPENDENCIA_AUSENTE_EN_LA_OBRA": "Depende de un tajo que la obra no tiene",
}

_SECCIONES_INVENTARIO = [
    ('VIABLE', '1. Tajos viables',
     'Se pueden ejecutar según los datos disponibles.'),
    ('BLOQUEADO', '2. Tajos bloqueados',
     'Son propios, pero falta una dependencia previa.'),
    ('OTROS_GREMIOS', '3. Otros gremios e interferencias',
     'Se controlan solo para saber cuándo puede entrar electricidad.'),
    ('DUDAS', '4. Sin clasificar o por verificar',
     'No se decide ni se fusiona hasta recibir confirmación.'),
    ('SIN_REVISAR', '5. Sin revisar nunca',
     'Nadie los ha mirado todavía. No son trabajo pendiente: son trabajo '
     'por comprobar.'),
    ('TERMINADO', '6. Tajos terminados',
     'Histórico conservado; siempre se muestra al final.'),
]


def _tabla_preguntas_orden(preguntas):
    """Lo que el catalogo no sabe resolver solo. Es la puerta por la que el
    catalogo crece: cada fila es una decision que hay que tomar."""
    if not preguntas:
        return ''
    filas = ''
    for p in preguntas:
        etiqueta = _ORDEN_ETIQUETAS.get(p.get('codigo'), p.get('codigo', ''))
        parecidos = p.get('parecidos') or []
        pista = ''
        if parecidos:
            pista = (f"<div style='font-size:11.5px;color:var(--muted);"
                     f"margin-top:3px;'>Candidatos: {_e(', '.join(parecidos))}</div>")
        filas += (f"<tr><td style='white-space:nowrap;'><b>{_e(etiqueta)}</b></td>"
                  f"<td><b>{_e(p.get('nombre'))}</b>"
                  f"<div style='font-size:11px;color:var(--muted);'>"
                  f"{_e(p.get('tarea_id'))}</div>{pista}</td></tr>")
    return ("<div class='card' style='border-left:4px solid var(--warn);'>"
            "<h3>Preguntas sobre el catálogo de tajos</h3>"
            "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
            "El catálogo manda sobre el orden y las dependencias, y es "
            "siempre ampliable. Estas son las decisiones que faltan para que "
            "estos tajos ocupen su sitio en la secuencia.</p>"
            "<div class='table-scroll'><table class='data'><thead><tr>"
            "<th>Qué pasa</th><th>Tajo</th></tr></thead><tbody>"
            + filas + "</tbody></table></div></div>")


def _tabla_prevision(prevision):
    """Que se libera al terminar cada tajo, de mayor a menor."""
    if not prevision:
        return ''
    filas = ''
    for p in prevision[:25]:
        propio = p.get('propiedad') == 'propio'
        badge = ("<span class='badge ok'>Nuestro</span>" if propio
                 else "<span class='badge'>Otro gremio</span>")
        filas += (f"<tr><td><b>{_e(p.get('trabajo'))}</b> {badge}</td>"
                  f"<td style='font-size:12px;'>{_e(p.get('estado_actual'))}</td>"
                  f"<td style='text-align:right;'><b>{_e(p.get('desbloquea'))}</b></td>"
                  f"<td style='font-size:12px;'>"
                  f"{_e(', '.join(p.get('tajos_afectados') or []))}</td></tr>")
    return ("<div class='card'><h3>Qué se desbloquea al terminar cada cosa</h3>"
            "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
            "Ordenado por lo que más libera. Una obra dura meses: saber qué "
            "abre paso a qué es lo que permite llevar el orden hasta el "
            "final.</p>"
            "<div class='table-scroll'><table class='data'><thead><tr>"
            "<th>Al terminar</th><th>Ahora está</th><th style='text-align:right;'>"
            "Libera</th><th>Deja pasar a</th>"
            "</tr></thead><tbody>" + filas + "</tbody></table></div></div>")


def _campo_riesgo(registro, *nombres):
    """Lee una columna manual aunque la plantilla use su nombre corto."""
    por_nombre = {
        str(k).strip().casefold(): v
        for k, v in (registro or {}).items()
    }
    for nombre in nombres:
        valor = por_nombre.get(nombre.casefold())
        if valor not in (None, ''):
            return valor
    return ''


def _tabla_riesgos_manuales(riesgos):
    if not riesgos:
        return ''
    filas = ''
    for riesgo in riesgos:
        valores = [
            _campo_riesgo(riesgo, 'Riesgo'),
            _campo_riesgo(riesgo, 'Tipo'),
            _campo_riesgo(riesgo, 'Probabilidad', 'Prob.'),
            _campo_riesgo(riesgo, 'Impacto'),
            _campo_riesgo(riesgo, 'Acción preventiva', 'Acción'),
            _campo_riesgo(riesgo, 'Fecha límite'),
            _campo_riesgo(riesgo, 'Estado'),
        ]
        filas += '<tr>' + ''.join(f'<td>{_e(v)}</td>' for v in valores) + '</tr>'
    return (
        "<div class='card'><h3>Registro manual</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Riesgos declarados en <b>FICHA DE OBRA.xlsx</b>. Probabilidad, "
        "impacto y fecha solo se muestran cuando alguien los ha registrado; "
        "el sistema no los inventa.</p>"
        "<div class='table-scroll'><table class='data'><thead><tr>"
        "<th>Riesgo</th><th>Tipo</th><th>Probabilidad declarada</th>"
        "<th>Impacto declarado</th><th>Acción</th><th>Fecha límite</th>"
        "<th>Estado</th></tr></thead><tbody>" + filas
        + "</tbody></table></div></div>"
    )


def _tabla_bloqueos_riesgo(prevision):
    if not prevision:
        return (
            "<div class='card'><h3>Bloqueos activos que frenan trabajo Sagarde</h3>"
            "<p class='empty'>La base y el catálogo no producen dependencias "
            "bloqueantes en esta actualización.</p></div>"
        )

    etiquetas = {
        'propio': ('Sagarde', 'ok'),
        'externo': ('Otro gremio', 'warn'),
        'coordinacion': ('Coordinación', 'warn'),
    }
    acciones = {
        'propio': 'Priorizar dentro de Sagarde por su efecto desbloqueante.',
        'externo': 'Coordinar su cierre y confirmarlo en la siguiente revisión.',
        'coordinacion': 'Cerrar la decisión o coordinación antes de liberar el frente.',
    }
    filas = ''
    for item in prevision[:25]:
        propiedad = item.get('propiedad') or 'desconocido'
        etiqueta, clase = etiquetas.get(propiedad, ('Por confirmar', 'bad'))
        afectados = ', '.join(item.get('tajos_afectados') or []) or '—'
        accion = acciones.get(
            propiedad, 'Confirmar responsable y condición de desbloqueo.')
        filas += (
            '<tr>'
            f"<td><b>{_e(item.get('trabajo'))}</b></td>"
            f"<td><span class='badge {clase}'>{_e(etiqueta)}</span></td>"
            f"<td>{_e(item.get('estado_actual'))}</td>"
            f"<td style='text-align:right;'><b>{_e(item.get('desbloquea'))}</b></td>"
            f"<td>{_e(afectados)}</td><td>{_e(accion)}</td>"
            '</tr>'
        )
    return (
        "<div class='card'><h3>Bloqueos activos que frenan trabajo Sagarde</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Ordenados por lo que más liberan. La magnitud cuenta unidades "
        "reales según el ámbito del tajo, no simples celdas.</p>"
        "<div class='table-scroll'><table class='data'><thead><tr>"
        "<th>Condicionante</th><th>Origen</th><th>Estado actual</th>"
        "<th style='text-align:right;'>Libera</th><th>Tajos Sagarde afectados</th>"
        "<th>Acción operativa</th></tr></thead><tbody>" + filas
        + "</tbody></table></div></div>"
    )


def _tabla_controles_riesgo(prioridades, bloqueos, sin_cambios):
    resumen = prioridades.get('resumen') or {}
    revision = prioridades.get('revision') or '—'
    sin_revisar = resumen.get('unidades_sin_revisar', 0)
    preguntas = resumen.get('preguntas_pendientes', 0)
    controles = []

    if prioridades.get('revision_caducada'):
        edad = prioridades.get('edad_revision_dias')
        evidencia = f"Revisión {revision}"
        if edad is not None:
            evidencia += f" · {edad} días"
        controles.append((
            'Revisión desactualizada', evidencia,
            'Actualizar la revisión de campo antes de decidir nuevos frentes.',
            'Verificar'))
    if sin_revisar:
        controles.append((
            'Cobertura pendiente', f'{sin_revisar} unidades sin revisar nunca',
            'Comprobarlas en campo; desconocido no equivale a pendiente.',
            'Verificar'))
    if preguntas:
        controles.append((
            'Decisiones sin resolver', f'{preguntas} decisiones pendientes',
            'Resolver alcance, duplicados o dependencias en la base/catálogo.',
            'Verificar'))
    if sin_cambios:
        controles.append((
            'Dos revisiones idénticas',
            'Las dos últimas revisiones no cambian ninguna celda',
            'Confirmar que la hoja de campo fue realmente actualizada.',
            'Verificar'))
    for bloqueo in bloqueos[:20]:
        controles.append((
            'Desviación de avance', bloqueo.get('motivo') or '—',
            'Verificar en obra la causa de la diferencia respecto a su entorno.',
            'Seguimiento'))

    if not controles:
        return (
            "<div class='card'><h3>Calidad del dato y desviaciones de avance</h3>"
            "<p class='empty'>Sin señales automáticas de control en esta actualización.</p>"
            "</div>"
        )

    filas = ''.join(
        '<tr>'
        f'<td><b>{_e(senal)}</b></td><td>{_e(evidencia)}</td>'
        f'<td>{_e(accion)}</td><td><span class="badge warn">{_e(estado)}</span></td>'
        '</tr>'
        for senal, evidencia, accion, estado in controles
    )
    return (
        "<div class='card'><h3>Calidad del dato y desviaciones de avance</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Estas señales no demuestran por sí solas un bloqueo de producción; "
        "indican qué conviene verificar.</p>"
        "<div class='table-scroll'><table class='data'><thead><tr>"
        "<th>Señal</th><th>Evidencia</th><th>Acción</th><th>Estado</th>"
        "</tr></thead><tbody>" + filas + "</tbody></table></div></div>"
    )


def bloque_riesgos(prioridades, bloqueos=None, riesgos_manual=None,
                    sin_cambios=False):
    """Reconstruye Riesgos con los datos calculados en el ciclo actual.

    Las prioridades ya proceden de ficha_obra.json y del catálogo. Los
    bloqueos de dependencias son hechos materializados, no riesgos
    probabilísticos, y se muestran con la magnitud real que desbloquean.
    """
    prioridades = prioridades or {}
    bloqueos = bloqueos or []
    riesgos_manual = riesgos_manual or []
    manual_html = _tabla_riesgos_manuales(riesgos_manual)

    if prioridades.get('sin_base'):
        avisos = prioridades.get('avisos') or [
            'Esta obra no tiene base de datos todavía.']
        return (
            "<div class='banner bad'><b>Riesgos no evaluables:</b> "
            + _e(avisos[0])
            + " El panel no publica un cero ni afirma que no haya riesgos."
              "</div>" + manual_html
        )

    resumen = prioridades.get('resumen') or {}
    prevision = prioridades.get('prevision') or []
    revision = prioridades.get('revision') or '—'
    bloqueados = resumen.get('bloqueados', 0)
    sin_revisar = resumen.get('unidades_sin_revisar', 0)
    preguntas = resumen.get('preguntas_pendientes', 0)

    cabecera = (
        "<div class='card'><h3>Riesgos de producción Sagarde</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:12px;'>"
        "Se recalculan al actualizar SAGARDE desde la base viva de la obra, "
        "el catálogo de dependencias y la revisión <b>" + _e(revision)
        + "</b>. Un bloqueo activo se presenta como hecho; no se le asigna "
          "una probabilidad ficticia.</p>"
        "<div class='kpi-row' style='margin-bottom:0;'>"
        "<div class='kpi'><div class='label'>Tajos bloqueados</div>"
        f"<div class='value'>{_e(bloqueados)}</div>"
        "<div class='hint'>Familias de trabajo Sagarde</div></div>"
        "<div class='kpi'><div class='label'>Condicionantes activos</div>"
        f"<div class='value'>{_e(len(prevision))}</div>"
        "<div class='hint'>Dependencias que frenan producción</div></div>"
        "<div class='kpi'><div class='label'>Sin revisar</div>"
        f"<div class='value'>{_e(sin_revisar)}</div>"
        "<div class='hint'>Unidades de dato por comprobar</div></div>"
        "<div class='kpi'><div class='label'>Decisiones pendientes</div>"
        f"<div class='value'>{_e(preguntas)}</div>"
        "<div class='hint'>Alcance, catálogo u orden</div></div>"
        "</div></div>"
    )
    return (
        cabecera
        + _tabla_bloqueos_riesgo(prevision)
        + _tabla_controles_riesgo(prioridades, bloqueos, sin_cambios)
        + manual_html
    )


def bloque_cierre(cierre, avisos=None):
    """HTML de la pestana Cierre de expediente.

    `cierre` es la forma que devuelve cierre_expediente.cargar()/vacio():
    {"obra":..., "actualizado":..., "hitos": {id: {"estado","fecha","nota"}}}.
    Dato de obra editado a mano, al margen de la rejilla de revisiones.
    """
    import cierre_expediente as ce
    cierre = cierre or ce.vacio()
    avisos = avisos or []

    avisos_html = ""
    if avisos:
        avisos_html = "".join(
            f"<div class='banner bad'>⚠ {_e(a)}</div>" for a in avisos)

    filas = ""
    for hito_id in ce.HITOS_ORDEN:
        datos_hito = (cierre.get('hitos') or {}).get(hito_id) or {
            'estado': 'pendiente', 'fecha': None, 'nota': ''}
        nombre = ce.HITOS_NOMBRE.get(hito_id, hito_id)
        estado = datos_hito.get('estado') or 'pendiente'
        badge = 'ok' if estado in ('hecho', 'favorable') else (
            'bad' if estado in ('condicionada', 'negativa') else 'warn')
        fecha = datos_hito.get('fecha') or '—'
        nota = datos_hito.get('nota') or '—'
        filas += (
            f"<tr><td>{_e(nombre)}</td>"
            f"<td><span class='badge {badge}'>{_e(estado)}</span></td>"
            f"<td>{_e(fecha)}</td><td>{_e(nota)}</td></tr>"
        )

    actualizado = cierre.get('actualizado') or 'sin actualizar todavía'
    return (
        avisos_html
        + "<div class='card'><h3>Cierre de expediente</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Ensayos, inspección OCA, CIE/Boletín y Libro del Edificio. Dato de "
        "obra editado a mano, no calculado desde las revisiones de campo. "
        f"Última actualización: {_e(actualizado)}.</p>"
        "<table class='data'><thead><tr><th>Hito</th><th>Estado</th>"
        "<th>Fecha</th><th>Nota</th></tr></thead>"
        f"<tbody>{filas}</tbody></table></div>"
    )


_SCRIPT_MARCAR_TAREA = """<script>
document.querySelectorAll('.marcar-tarea-hecha').forEach(casilla => {
  casilla.addEventListener('change', async () => {
    const objetivo = casilla.checked ? 'Hecho' : 'Pendiente';
    casilla.disabled = true;
    const fila = casilla.closest('tr');
    const tarjeta = casilla.closest('.card');
    const mensaje = tarjeta.querySelector('.tarea-resultado');
    const contador = tarjeta.querySelector('.tareas-pendientes-contador');
    const controlador = new AbortController();
    const timeout = setTimeout(() => controlador.abort(), 3000);
    const restaurar = () => {
      casilla.checked = !casilla.checked;
      casilla.disabled = false;
    };
    const avisar = (texto, error) => {
      mensaje.textContent = texto;
      mensaje.style.color = error ? 'var(--bad)' : 'var(--ok)';
      mensaje.style.display = 'block';
    };
    try {
      const respuesta = await fetch('/api/marcar_hecho', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          obra_carpeta: casilla.dataset.obra,
          tarea: casilla.dataset.tarea,
          origen: casilla.dataset.origen,
          fecha: casilla.dataset.fecha,
          archivo: casilla.dataset.archivo,
          objetivo: objetivo
        }),
        signal: controlador.signal
      });
      if (respuesta.ok) {
        const marcandoHecha = objetivo === 'Hecho';
        fila.style.color = marcandoHecha ? 'var(--muted)' : '';
        fila.style.textDecoration = marcandoHecha ? 'line-through' : '';
        const estado = fila.querySelector('.badge');
        estado.textContent = objetivo;
        estado.classList.toggle('f3', marcandoHecha);
        estado.classList.toggle('warn', !marcandoHecha);
        const delta = marcandoHecha ? -1 : 1;
        const restantes = Math.max(
          0, parseInt(contador.dataset.pendientes, 10) + delta);
        contador.dataset.pendientes = restantes;
        contador.textContent = restantes + ' '
          + (restantes === 1 ? 'pendiente' : 'pendientes');
        avisar(marcandoHecha
          ? 'Marcada como hecha. Recuerda ejecutar Actualizar_Sagarde.bat para publicar este cambio.'
          : 'Marcada de nuevo como pendiente. Recuerda ejecutar Actualizar_Sagarde.bat para publicar este cambio.',
          false);
      } else if (respuesta.status === 404) {
        restaurar();
        avisar('No se encontró esa tarea en el Excel; puede que el panel '
          + 'esté desactualizado. Regenera antes de reintentar.', true);
      } else {
        restaurar();
        avisar('No se pudo guardar: esto solo funciona abriendo el panel en '
          + 'local con Abrir_Panel_Local.bat. No se ha guardado ningún cambio.',
          true);
      }
    } catch (error) {
      restaurar();
      avisar('No se pudo guardar: esto solo funciona abriendo el panel en '
        + 'local con Abrir_Panel_Local.bat. No se ha guardado ningún cambio.',
        true);
    } finally {
      clearTimeout(timeout);
    }
  });
});
</script>"""


def _tabla_tareas_manuales(tareas, documentos, obra=''):
    """Pinta las tareas de la ficha y enlaza su documento cuando existe."""
    tareas = tareas or []
    if not tareas:
        return ''

    href_por_nombre = {}
    for documento in documentos or []:
        nombre = str(documento.get('nombre') or '').strip()
        href = documento.get('href')
        if nombre and href not in (None, ''):
            href_por_nombre.setdefault(nombre.casefold(), str(href))

    def esta_hecha(tarea):
        return str(tarea.get('Estado') or '').strip().casefold() == 'hecho'

    def esta_pendiente(tarea):
        return (str(tarea.get('Estado') or '').strip().casefold()
                == 'pendiente')

    def clave_fecha(tarea):
        texto = str(tarea.get('Fecha') or '').strip()
        try:
            return (0, datetime.strptime(texto, '%d/%m/%Y'))
        except ValueError:
            # Una fecha vacía o no normalizada no debe romper el panel. Se
            # conserva al final de las pendientes, ordenada por su texto.
            return (1, texto.casefold())

    pendientes = sorted(
        (tarea for tarea in tareas if not esta_hecha(tarea)), key=clave_fecha)
    hechas = [tarea for tarea in tareas if esta_hecha(tarea)]

    def archivo_html(tarea):
        archivo = str(tarea.get('Archivo') or '').strip()
        if not archivo:
            return _e(None)
        href = href_por_nombre.get(archivo.casefold())
        if href is None:
            return _e(archivo)
        return f'<a href="{_e(href)}">{_e(archivo)}</a>'

    def fila(tarea, hecha=False):
        estado = tarea.get('Estado') or 'Sin estado'
        estilo = (" style='color:var(--muted);text-decoration:line-through;'"
                  if hecha else '')
        clase = 'f3' if hecha else 'warn'
        # Solo se ofrece la casilla cuando el estado actual es exactamente
        # Pendiente o Hecho: un valor ambiguo no dice en qué sentido cambiar,
        # y no se adivina.
        if hecha or esta_pendiente(tarea):
            casilla = (
                "<td><label style='white-space:nowrap;cursor:pointer;'>"
                "<input type='checkbox' class='marcar-tarea-hecha'"
                + (' checked' if hecha else '')
                + f" data-obra='{_e_atributo(obra)}'"
                f" data-tarea='{_e_atributo(tarea.get('Tarea'))}'"
                f" data-origen='{_e_atributo(tarea.get('Origen'))}'"
                f" data-fecha='{_e_atributo(tarea.get('Fecha'))}'"
                f" data-archivo='{_e_atributo(tarea.get('Archivo'))}'> Hecho"
                "</label></td>"
            )
        else:
            casilla = '<td></td>'
        return (
            f"<tr{estilo}><td><span class='badge {clase}'>{_e(estado)}</span></td>"
            f"<td><b>{_e(tarea.get('Tarea'))}</b></td>"
            f"<td>{_e(tarea.get('Origen'))}</td>"
            f"<td style='white-space:nowrap;'>{_e(tarea.get('Fecha'))}</td>"
            f"<td>{archivo_html(tarea)}</td>{casilla}</tr>"
        )

    filas_pendientes = ''.join(fila(tarea) for tarea in pendientes)
    if filas_pendientes:
        bloque_pendientes = (
            "<div class='tareas-pendientes'><div class='table-scroll'>"
            "<table class='data'><thead><tr><th>Estado</th><th>Tarea</th>"
            "<th>Origen</th><th>Fecha</th><th>Archivo</th><th>Acción</th>"
            "</tr></thead>"
            f"<tbody>{filas_pendientes}</tbody></table></div></div>"
        )
    else:
        bloque_pendientes = '<p class="empty">Sin tareas pendientes.</p>'

    bloque_hechas = ''
    if hechas:
        filas_hechas = ''.join(fila(tarea, hecha=True) for tarea in hechas)
        bloque_hechas = (
            "<div class='tareas-hechas' "
            "style='margin-top:16px;color:var(--muted);'>"
            "<h4 style='font-size:12px;margin-bottom:6px;'>Hechas</h4>"
            "<div class='table-scroll'><table class='data'><tbody>"
            f"{filas_hechas}</tbody></table></div></div>"
        )

    n_pendientes = len(pendientes)
    etiqueta = 'pendiente' if n_pendientes == 1 else 'pendientes'
    tarjeta = (
        "<div class='card' style='border-left:4px solid var(--accent2);'>"
        "<h3>Tareas manuales "
        f"<span class='badge tareas-pendientes-contador' "
        f"data-pendientes='{n_pendientes}'>{n_pendientes} {etiqueta}</span>"
        "</h3>"
        "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
        "Acciones declaradas en la hoja <b>Tareas</b> de "
        "<b>FICHA DE OBRA.xlsx</b>. Se muestran aparte: no modifican los "
        "KPI ni el orden calculado de los tajos.</p>"
        f"{bloque_pendientes}{bloque_hechas}"
        "<p class='tarea-resultado' role='status' "
        "style='display:none;font-size:12.5px;margin-top:10px;'></p></div>"
    )
    hay_casillas = bool(hechas) or any(
        esta_pendiente(tarea) for tarea in pendientes)
    return tarjeta + (_SCRIPT_MARCAR_TAREA if hay_casillas else '')


def bloque_prioridades(prioridades, tareas_manual=None, documentos=None,
                       obra=''):
    """HTML de la pestana Prioridades.

    Separado de generar_panel para poder probarlo sin montar una obra entera:
    un dato que se calcula y no se pinta es lo mismo que no calcularlo.
    """
    prioridades = prioridades or {}
    if prioridades.get('sin_base'):
        avisos = prioridades.get('avisos') or [
            'Esta obra no tiene base de datos todavía.']
        return ("<div class='banner bad'>⚠ " + _e(avisos[0]) + "</div>"
                "<p style='font-size:12.5px;color:var(--muted);'>Las "
                "prioridades salen de la base de datos de la obra. Sin ella "
                "no se calcula nada: un recuento vacío sería un dato falso."
                "</p>")

    e = _e
    tareas_manual_html = _tabla_tareas_manuales(
        tareas_manual, documentos, obra=obra)
    resumen_prio = prioridades.get('resumen', {})
    items_prio = prioridades.get('items', [])
    inventario_prio = prioridades.get('inventario', [])
    dudas_prio = prioridades.get('dudas_pendientes', [])

    filas_prio = ""
    for item in items_prio:
        sit_val = item.get('situacion', '')
        clase_estado = 'ok' if sit_val == 'LISTO' else 'warn'
        borde = 'var(--ok)' if sit_val == 'LISTO' else 'var(--warn)'
        todas_ubs = item.get('ubicaciones', [])
        n_ubicaciones = item.get('n_ubicaciones', len(todas_ubs))
        ubicaciones_txt = _ubicaciones_html(todas_ubs)
        motivo_html = e(item.get('motivo') or item.get('impacto_gremios', ''))
        fase_val = e(item.get('fase_nombre', ''))
        celdas = item.get('n_celdas')
        detalle_celdas = ''
        if celdas and celdas != item.get('n_unidades'):
            detalle_celdas = (f"<br><span style='font-size:11px;color:var(--muted);'>"
                              f"{e(celdas)} celdas en la hoja</span>")
        filas_prio += (
            f"<tr data-fase='{fase_val}' data-sit='{e(sit_val)}'>"
            f"<td style='white-space:nowrap;border-left:3px solid {borde};'>"
            f"<b>#{e(item.get('orden'))}</b>"
            f"<div style='margin-top:4px;'><span class='badge {clase_estado}'>{e(sit_val)}</span></div></td>"
            f"<td><b>{e(item.get('trabajo'))}</b>"
            f"<div style='font-size:11px;color:var(--muted);margin-top:3px;'>"
            f"Orden lógico {e(item.get('orden_ejecucion'))} · {e(item.get('fase_nombre'))} · {e(item.get('ambito_nombre'))}</div></td>"
            f"<td style='white-space:nowrap;'><b>{e(item.get('n_unidades'))}</b> ud."
            f"{detalle_celdas}</td>"
            f"<td>{ubicaciones_txt}</td>"
            f"<td style='font-size:12px;'>{e(item.get('estado_actual'))}</td>"
            f"<td style='font-size:12px;'>{motivo_html}</td></tr>"
        )
    if not filas_prio:
        filas_prio = '<tr><td colspan="6" class="empty">No se han identificado bloques ejecutables con las reglas y datos actuales.</td></tr>'

    _bp = ("El inventario incluye", "Los nombres nuevos", "Una X histórica",
           "El orden sigue")
    avisos_prio = ''.join(
        f'<div class="banner{" bad" if any(k in aviso.lower() for k in ("fusionan", "rejilla", "error")) else ""}">⚠ {e(aviso)}</div>'
        for aviso in prioridades.get('avisos', [])
        if not any(aviso.startswith(bp) for bp in _bp)
    )

    estado_obra_html = ''
    if prioridades.get('estado_obra'):
        estado_obra_html = f'<div class="banner">ℹ <b>Estado de la obra:</b> {e(prioridades.get("estado_obra"))}</div>'

    if dudas_prio:
        filas_dudas = ''
        for duda in dudas_prio:
            codigo = duda.get('codigo', '')
            etiqueta = _DUDA_ETIQUETAS.get(codigo, codigo)
            pregunta = duda.get('pregunta', '')
            n_ub = duda.get('n_ubicaciones', 0)
            por_planta = {}
            for ub in duda.get('ubicaciones', []):
                p = ub.get('planta', '?')
                u = ub.get('unidad', '?')
                por_planta.setdefault(p, []).append(u)

            def _sort_key(p):
                texto = str(p).strip()
                if texto.isdigit():
                    return (1, int(texto), '')
                if texto.casefold() in {'pb', 'b', 'bajo', 'baja', 'planta baja'}:
                    return (0, 0, '')
                return (2, 0, texto)
            ub_filas = ''.join(
                f"<tr><td style='padding:2px 8px;'>Planta {e(p)}</td>"
                f"<td style='padding:2px 8px;'>{e(', '.join(por_planta[p]))}</td></tr>"
                for p in sorted(por_planta, key=_sort_key)
            )
            ub_detail = (
                f"<details style='margin-top:6px;'>"
                f"<summary style='cursor:pointer;font-size:12px;color:var(--accent);'>"
                f"Ver {n_ub} ubicaciones afectadas</summary>"
                f"<div style='margin-top:4px;overflow-x:auto;'>"
                f"<table style='border-collapse:collapse;font-size:12px;'>"
                f"<thead><tr><th style='padding:2px 8px;text-align:left;'>Planta</th>"
                f"<th style='padding:2px 8px;text-align:left;'>Unidades</th></tr></thead>"
                f"<tbody>{ub_filas}</tbody></table></div></details>"
            ) if por_planta else ''
            filas_dudas += (
                f"<tr><td style='white-space:nowrap;'><b>{e(etiqueta)}</b></td>"
                f"<td>{e(pregunta)}{ub_detail}</td>"
                f"<td style='text-align:center;'>{n_ub}</td></tr>"
            )
        dudas_html = ("<div class='card' style='border-left:4px solid var(--warn);'>"
                      "<h3>Preguntas pendientes antes de decidir</h3>"
                      "<p style='font-size:12.5px;color:var(--muted);margin-bottom:10px;'>"
                      "Resolver estas dudas antes de planificar los tajos afectados. "
                      "Pincha en cada fila para ver las plantas y unidades concretas.</p>"
                      "<div class='table-scroll'><table class='data'><thead><tr>"
                      "<th>Tipo</th><th>Qué hay que comprobar</th><th>Uds.</th>"
                      "</tr></thead><tbody>"
                      + filas_dudas + "</tbody></table></div></div>")
    else:
        dudas_html = '<div class="banner">✓ No hay preguntas pendientes en esta actualización.</div>'

    orden_html = _tabla_preguntas_orden(prioridades.get('preguntas_orden'))
    prevision_html = _tabla_prevision(prioridades.get('prevision'))

    inventario_html = ''
    for codigo, titulo, explicacion in _SECCIONES_INVENTARIO:
        grupos = [g for g in inventario_prio if g.get('seccion') == codigo]
        filas = ''
        for g in grupos:
            subtajos = g.get('subtajos', [])
            sub_txt = ''
            if len(subtajos) > 1:
                sub_txt = f"<div style='font-size:11px;color:var(--muted);'>Incluye: {e(', '.join(subtajos))}</div>"
            filas += (f"<tr><td><b>{e(g.get('trabajo'))}</b>{sub_txt}"
                      f"<div style='font-size:11px;color:var(--muted);'>Orden {e(g.get('orden_ejecucion'))} · {e(g.get('fase_nombre'))}</div></td>"
                      f"<td>{e(g.get('propiedad'))}</td><td><b>{e(g.get('n_ubicaciones'))}</b></td>"
                      f"<td>{_ubicaciones_html(g.get('ubicaciones', []))}</td>"
                      f"<td>{e(g.get('estado_actual'))}</td><td style='font-size:12px;'>{e(g.get('motivo'))}</td></tr>")
        if not filas:
            filas = '<tr><td colspan="6" class="empty">Sin tajos en esta sección.</td></tr>'
        tabla = (f"<div class='card'><h3>{titulo} <span class='badge'>{len(grupos)}</span></h3>"
                 f"<p style='font-size:12px;color:var(--muted);margin-bottom:8px;'>{explicacion}</p>"
                 "<div class='table-scroll'><table class='data'><thead><tr><th>Tajo agrupado</th>"
                 "<th>Responsable</th><th>Ubicaciones</th><th>Dónde</th><th>Estado</th><th>Motivo</th>"
                 f"</tr></thead><tbody>{filas}</tbody></table></div></div>")
        if codigo == 'TERMINADO':
            tabla = f"<details><summary style='cursor:pointer;font-weight:700;margin:14px 0;'>Mostrar {len(grupos)} tajos terminados</summary>{tabla}</details>"
        inventario_html += tabla

    return f"""
    <div class="kpi-row">
      <div class="kpi"><div class="label">Bloques viables</div><div class="value">{resumen_prio.get('listos', 0)}</div><div class="hint">{resumen_prio.get('unidades_listas', 0)} unidades de trabajo</div></div>
      <div class="kpi"><div class="label">Bloqueados</div><div class="value">{resumen_prio.get('bloqueados', 0)}</div><div class="hint">Tajos propios con dependencias</div></div>
      <div class="kpi"><div class="label">Otros gremios</div><div class="value">{resumen_prio.get('otros_gremios', 0)}</div><div class="hint">Control de interferencias</div></div>
      <div class="kpi"><div class="label">Sin revisar nunca</div><div class="value">{resumen_prio.get('sin_revisar', 0)}</div><div class="hint">{resumen_prio.get('unidades_sin_revisar', 0)} celdas que nadie ha mirado</div></div>
      <div class="kpi"><div class="label">Preguntas</div><div class="value">{resumen_prio.get('preguntas_pendientes', 0)}</div><div class="hint">Resolver antes de decidir</div></div>
      <div class="kpi"><div class="label">Terminados</div><div class="value">{resumen_prio.get('terminados', 0)}</div><div class="hint">Conservados del histórico</div></div>
      <div class="kpi"><div class="label">Inventario completo</div><div class="value">{resumen_prio.get('inventario_total', 0)}</div><div class="hint">Tipos de tajo agrupados</div></div>
      <div class="kpi"><div class="label">Revisión utilizada</div><div class="value" style="font-size:18px;">{e(prioridades.get('revision'))}</div><div class="hint">Motor v{e(prioridades.get('version'))} · catálogo v{e(prioridades.get('catalogo_version'))}</div></div>
    </div>
    {estado_obra_html}
    {tareas_manual_html}
    {dudas_html}
    {orden_html}
    {avisos_prio}
    <div class="card"><h3>Qué hacer ahora: orden lógico de ejecución</h3>
      <p style="font-size:12.5px;color:var(--muted);margin-bottom:10px;">Primero aparecen los tajos viables de viviendas, después zonas comunes y edificio. Los tajos iguales se agrupan. VERIFICAR nunca se considera ejecutable hasta confirmar la duda. <a href="prioridades_trabajos.json" target="_blank">Ver cálculo y detalle completo</a>.</p>
      <div style="margin-bottom:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <span style="font-size:12px;color:var(--muted);">Filtrar:</span>
        <select id="filtro-sit" style="font-size:12px;padding:4px 8px;border:1px solid #ddd;border-radius:6px;">
          <option value="">LISTO + VERIFICAR</option>
          <option value="LISTO">Solo LISTO</option>
          <option value="VERIFICAR">Solo VERIFICAR</option>
        </select>
        <span id="prio-count" style="font-size:12px;color:var(--muted);"></span>
      </div>
      <div class="table-scroll"><table id="tabla-prio" class="data"><thead><tr><th>#</th><th>Tajo</th><th>Alcance</th><th>Dónde</th><th>En obra</th><th>Motivo / Comprobar</th></tr></thead>
      <tbody>{filas_prio}</tbody></table></div>
    </div>
    {prevision_html}
    <div style="margin:20px 0 10px;"><h2 style="font-size:18px;">Inventario completo de la obra</h2><p style="font-size:12.5px;color:var(--muted);">Incluye todos los tajos de la base de la obra. Los terminados no desaparecen: se guardan al final.</p></div>
    {inventario_html}"""


def generar_panel(obra, subtitulo, historial, materiales, ficha, documentos,
                  output_path, volver_href="../../index.html", prioridades=None,
                  tajos_memoria=None, mem_resumen=None, bat_path=None,
                  cierre=None, cierre_avisos=None):
    prioridades = prioridades or {}
    snapshot = historial[-1][1] if historial else []
    historial_panel = list(historial)
    historial_confirmado = bool(prioridades.get('historial_confirmado_terminado'))
    if historial_confirmado and snapshot:
        snapshot = [{**registro, 'status': 'X'} for registro in snapshot]
        historial_panel[-1] = (historial_panel[-1][0], snapshot)

    kpis = motor.kpis_snapshot(snapshot) if snapshot else {}
    bloqueos = [] if historial_confirmado else (motor.detectar_bloqueos(snapshot) if snapshot else [])
    sin_cambios = False if historial_confirmado else motor.sin_cambios_entre_ultimas(historial)
    n_bloqueos_base = (prioridades.get('resumen') or {}).get(
        'bloqueados', len(bloqueos))

    payload = {
        'serie': motor.serie_tiempo(historial_panel) if historial_panel else [],
        'por_planta': motor.matriz_planta_edificio(snapshot) if snapshot else {'labels': [], 'series': {}},
        'por_tarea': motor.ranking_tareas_con_memoria(snapshot, tajos_memoria) if snapshot else [],
    }

    # ---- Banners globales ----
    banners = ""
    if historial_confirmado:
        banners += ('<div class="banner"><b>Estado confirmado:</b> obra entregada y en funcionamiento. '
                    'Solo queda revisar el alcance postapertura de los apartamentos 1 y 2 de planta baja '
                    'cuando termine el tabique separador de cocinas.</div>')
    if sin_cambios:
        banners += ('<div class="banner bad">⚠ Las dos últimas revisiones registradas son idénticas: '
                    'posible hoja de campo sin actualizar.</div>')
    if materiales.get('aviso'):
        banners += f'<div class="banner">⚠ {materiales["aviso"]}</div>'
    if not ficha.get('_disponible'):
        banners += ('<div class="banner">ℹ No se encontró <b>FICHA DE OBRA.xlsx</b> en la carpeta. '
                    'Las secciones Personal, Hitos y Riesgos manuales estarán vacías hasta que la rellenes.</div>')

    # ---- PANEL (resumen) ----
    datos = ficha.get('datos', {})
    def d(k, default='—'):
        v = datos.get(k, '')
        return v if v else default
    resumen_datos = ''.join(
        f'<tr><td style="color:var(--muted);width:42%;">{k}</td><td>{v or "—"}</td></tr>'
        for k, v in datos.items()
    ) or '<tr><td class="empty">Sin ficha de obra.</td></tr>'

    kpi_html = ""
    if kpis:
        kpi_html = f"""
        <div class="kpi"><div class="label">Avance estricto (X)</div><div class="value">{kpis['pct_estricto']}%</div><div class="hint">Solo tareas 100% terminadas</div></div>
        <div class="kpi"><div class="label">Avance estimado</div><div class="value">{kpis['pct_ponderado']}%</div><div class="hint">Incluye parciales (estimación)</div></div>
        <div class="kpi"><div class="label">Revisiones</div><div class="value">{len(historial)}</div><div class="hint">Desde {historial[0][0]}</div></div>
        <div class="kpi"><div class="label">Tajos bloqueados</div><div class="value">{n_bloqueos_base}</div><div class="hint">Sagarde · dependencias de la base</div></div>
        """
    else:
        kpi_html = '<div class="kpi"><div class="label">Avance</div><div class="value">—</div><div class="hint">Sin datos de revisión</div></div>'

    # ---- TRABAJOS: desviaciones + ranking + detalle (charts via JS) ----
    filas_bloq = ""
    if bloqueos:
        for b in bloqueos:
            badge = 'bad' if b['avance'] < 30 else 'warn'
            filas_bloq += (f"<tr><td>{b['tipo']}</td><td>{b['edificio']}</td><td>{b['planta']}</td>"
                           f"<td>{b['unidad']}</td><td><span class='badge {badge}'>{b['avance']}%</span></td>"
                           f"<td>{b['motivo']}</td></tr>")
    else:
        filas_bloq = '<tr><td colspan="6" class="empty">No se detectan desviaciones de avance con la heurística actual.</td></tr>'

    detalle = motor.tabla_detalle(snapshot) if snapshot else []
    filas_det = "".join(
        f"<tr><td>{r['edificio']}</td><td>{r['planta']}</td><td>{r['pct_estricto']}%</td>"
        f"<td>{r['pct_ponderado']}%</td><td>{r['n']}</td></tr>" for r in detalle
    ) or '<tr><td colspan="5" class="empty">Sin datos.</td></tr>'

    # ---- MATERIALES ----
    if materiales.get('disponible') and materiales.get('items'):
        filas_mat = ""
        cat_actual = None
        for it in materiales['items']:
            if it['categoria'] != cat_actual:
                cat_actual = it['categoria']
                if cat_actual:
                    filas_mat += f"<tr><td colspan='4' style='font-weight:700;color:var(--header2);background:#f4f6f9;'>{cat_actual}</td></tr>"
            filas_mat += (f"<tr><td>{it['material']}</td><td>{it['tipo']}</td>"
                          f"<td>{it['uni']}</td><td style='text-align:right;'>{_fmt_num(it['total'])}</td></tr>")
        mat_meta = (f"Última hoja: <b>{materiales['ultimo_mes']}</b>"
                    + (f" · última entrada {materiales['ultima_fecha']}" if materiales.get('ultima_fecha') else ""))
        materiales_html = f"""
        <div class="card"><h3>Consumo acumulado de material — {materiales['ultimo_mes']}</h3>
        <p style="font-size:12.5px;color:var(--muted);margin-bottom:10px;">{mat_meta}. Cantidades <b>suministradas</b> según hoja; no equivalen necesariamente a material instalado.</p>
        <table class="data"><thead><tr><th>Material</th><th>Tipo</th><th>Uni</th><th style="text-align:right;">Total</th></tr></thead>
        <tbody>{filas_mat}</tbody></table></div>"""
    elif materiales.get('disponible'):
        materiales_html = f'<div class="card"><h3>Materiales</h3><p class="empty">Se encontró la hoja de materiales pero no se pudo interpretar automáticamente ({materiales.get("aviso") or "formato no reconocido"}). Ábrela desde la sección Documentos.</p></div>'
    else:
        materiales_html = '<div class="card"><h3>Materiales</h3><p class="empty">No se encontró hoja de materiales en la carpeta de la obra.</p></div>'

    # ---- PERSONAL / PLAN / HITOS / RIESGOS (de ficha) + riesgos auto ----
    def tabla_ficha(registros, cols_orden=None):
        if not registros:
            return '<p class="empty">Sin datos en la ficha de obra.</p>'
        cols = cols_orden or list(registros[0].keys())
        head = "".join(f"<th>{c}</th>" for c in cols)
        body = ""
        for reg in registros:
            body += "<tr>" + "".join(f"<td>{reg.get(c,'')}</td>" for c in cols) + "</tr>"
        return f'<table class="data"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'

    personal_html = tabla_ficha(ficha.get('personal', []))
    hitos_html = tabla_ficha(ficha.get('hitos', []))

    # ---- PRIORIDADES E INVENTARIO COMPLETO DE TAJOS (motor v4) ----
    prioridades_html = bloque_prioridades(
        prioridades, tareas_manual=ficha.get('tareas', []),
        documentos=documentos, obra=obra)

    # Se reconstruye desde la base/priorizador del mismo ciclo. La ficha XLSX
    # solo aporta el registro manual complementario.
    riesgos_html = bloque_riesgos(
        prioridades, bloqueos=bloqueos,
        riesgos_manual=ficha.get('riesgos', []), sin_cambios=sin_cambios)
    cierre_html = bloque_cierre(cierre, avisos=cierre_avisos)

    # ---- DOCUMENTOS ----
    docs_html = ""
    if documentos:
        cat_actual = None
        for doc in documentos:
            if doc['categoria'] != cat_actual:
                cat_actual = doc['categoria']
                docs_html += f'<div class="doc-cat">{cat_actual}</div>'
            sub = f" <span style='color:var(--muted);font-size:11.5px;'>· {doc['subcarpeta']}</span>" if doc['subcarpeta'] else ""
            docs_html += (f'<div class="doc"><a href="{doc["href"]}" target="_blank">{doc["nombre"]}</a>'
                          f'<span style="color:var(--muted);font-size:11.5px;"> ({doc["kb"]} KB)</span>{sub}</div>')
    else:
        docs_html = '<p class="empty">No se encontraron documentos en la carpeta de la obra.</p>'

    norm_html = "".join(f"<li>{n}</li>" for n in NORMATIVA_ITEMS)

    # ---- ACTUALIZAR ----
    mem_r = mem_resumen or {}
    bat_rel = '../../_SISTEMA INFORME SAGARDE IA/Actualizar_Obras.bat'
    bat_abs = bat_path or ''
    bat_js = bat_abs.replace('\\', '\\\\').replace("'", '')  # seguro en atributo onclick JS
    fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
    mem_nota = ''
    if tajos_memoria:
        n_act = mem_r.get('activos', sum(1 for v in tajos_memoria.values() if not v.get('terminado')))
        n_term = mem_r.get('terminados', sum(1 for v in tajos_memoria.values() if v.get('terminado')))
        mem_nota = (f'<div style="margin-top:18px;"><b>Memoria de tajos</b>: '
                    f'{len(tajos_memoria)} tajos en total &mdash; '
                    f'<span style="color:var(--ok);">{n_act} activos</span> · '
                    f'<span style="color:var(--muted);">{n_term} terminados (100% forzado en el gráfico)</span>.</div>'
                    f'<p style="font-size:12px;color:var(--muted);margin-top:6px;">'
                    f'Los tajos terminados son aquellos que desaparecieron de la hoja de revisión. '
                    f'Se conservan en <code>memoria_obra.json</code> y se muestran al 100% en el gráfico de avance.</p>')
    actualizar_html = f"""<div class="card">
  <h3>↻ Actualizar panel</h3>
  <p style="font-size:13px;">Este panel es un fichero HTML estático. Se actualizó el <b>{fecha_gen}</b>.
  Para reflejarlo con los últimos archivos de revisión hay que regenerarlo.</p>
  <div style="margin-top:18px;background:#f0f4ff;border:1px solid #c0cfe8;border-radius:8px;padding:14px 18px;">
    <b style="font-size:13px;">Paso 1 &mdash; Haz doble clic en este archivo:</b><br>
    <code style="font-size:13px;display:block;margin:8px 0;">Actualizar_Obras.bat</code>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;">
      <a href="{bat_rel}" style="background:var(--header2);color:#fff;padding:7px 14px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:600;">⬇ Abrir / descargar .bat</a>
      <button onclick="navigator.clipboard.writeText('{bat_js}').then(()=>this.textContent='✓ Copiado!').catch(()=>this.textContent='Error')" style="background:#e8f0fe;border:1px solid #c0cfe8;padding:7px 14px;border-radius:6px;font-size:13px;cursor:pointer;">📋 Copiar ruta completa</button>
    </div>
    {('<div style="font-size:11.5px;color:var(--muted);margin-top:6px;">Ruta: <code>' + html_lib.escape(bat_abs) + '</code></div>') if bat_abs else ''}
  </div>
  <div style="margin-top:18px;background:#f4f6f9;border-radius:8px;padding:14px 18px;">
    <b style="font-size:13px;">Paso 2 &mdash; Recarga esta página en el navegador (F5)</b><br>
    <span style="font-size:12.5px;color:var(--muted);">El .bat regenera el panel.html y abre el índice automáticamente.</span>
  </div>
  {mem_nota}
</div>"""

    data_json = json.dumps(payload, ensure_ascii=False).replace('</script>', '<\\/script>')

    # ---- HTML ----
    pdf_ejecutivo_nombre = f"INFORME_EJECUTIVO_{obra.replace(' ', '_')}.pdf"
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Panel Sagarde IA · {obra}</title>
<script src="../../_SISTEMA INFORME SAGARDE IA/static/chart.min.js"></script>
<style>{ESTILOS}</style></head><body><div class="wrap">
<div class="header">
  <div><div class="brand">Informe Sagarde IA · Panel de obra</div><h1>{obra}</h1><div class="sub">{subtitulo}</div></div>
  <div class="meta">Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
  Última revisión: {historial[-1][0] if historial else '—'}<br>
  <a class="volver" href="{volver_href}">← Todas las obras</a>
  <a class="volver" href="{pdf_ejecutivo_nombre}" target="_blank" style="background:var(--bad);border-color:var(--bad);margin-left:6px;">📄 Informe Ejecutivo PDF</a></div>
</div>

<div class="nav">
  <button class="active" data-view="v-panel">▦ Panel</button>
  <button data-view="v-trabajos">✓ Trabajos</button>
  <button data-view="v-materiales">▣ Materiales</button>
  <button data-view="v-personal">👷 Personal</button>
  <button data-view="v-prioridades">🎯 Prioridades</button>
  <button data-view="v-riesgos">⚠ Riesgos</button>
  <button data-view="v-normativa">📘 Normativa</button>
  <button data-view="v-docs">📎 Documentos</button>
  <button data-view="v-cierre">📋 Cierre</button>
  <button data-view="v-actualizar" style="margin-left:auto;background:var(--header2);color:#fff;">↻ Actualizar</button>
</div>

{banners}

<section id="v-panel" class="view active">
  <div class="kpi-row">{kpi_html}</div>
  <div class="chart-row">
    <div class="card"><h3>Evolución del avance</h3><canvas id="chartSerie"></canvas></div>
    <div class="card"><h3>Avance por planta y edificio</h3><canvas id="chartPlanta"></canvas></div>
  </div>
  <div class="card"><h3>Ficha de obra</h3><table class="data"><tbody>{resumen_datos}</tbody></table></div>
</section>

<section id="v-trabajos" class="view">
  <div class="card"><h3>Avance por tarea — cuellos de botella</h3><canvas id="chartTareas" style="max-height:520px;"></canvas></div>
  <div class="card"><h3>Desviaciones de avance</h3>
    <table class="data"><thead><tr><th>Tipo</th><th>Edificio</th><th>Planta</th><th>Unidad</th><th>Avance</th><th>Motivo</th></tr></thead>
    <tbody>{filas_bloq}</tbody></table></div>
  <div class="card"><h3>Detalle por planta / edificio</h3>
    <table class="data"><thead><tr><th>Edificio</th><th>Planta</th><th>% estricto</th><th>% estimado</th><th>Nº registros</th></tr></thead>
    <tbody>{filas_det}</tbody></table></div>
</section>

<section id="v-materiales" class="view">{materiales_html}</section>

<section id="v-personal" class="view"><div class="card"><h3>Personal asignado</h3>{personal_html}</div></section>

<section id="v-prioridades" class="view">{prioridades_html}
  <div class="card"><h3>Hitos manuales</h3>{hitos_html}</div></section>

<section id="v-riesgos" class="view">{riesgos_html}</section>

<section id="v-normativa" class="view"><div class="card"><h3>Normativa y criterios técnicos aplicables</h3>
  <p style="font-size:12.5px;color:var(--muted);margin-bottom:8px;">Lista de referencia. No sustituye la comprobación de la versión vigente ni las instrucciones de la Dirección Facultativa.</p>
  <ul class="norm">{norm_html}</ul></div></section>

<section id="v-docs" class="view"><div class="card"><h3>Documentos de la obra</h3>
  <p style="font-size:12.5px;color:var(--muted);margin-bottom:8px;">Todos los archivos de la carpeta. Clic para abrir (los enlaces funcionan en el PC; en el móvil abre los archivos desde la app de OneDrive).</p>
  {docs_html}</div></section>

<section id="v-cierre" class="view">{cierre_html}</section>

<section id="v-actualizar" class="view">{actualizar_html}</section>

<div class="footer">Informe Sagarde IA · Generado automáticamente a partir de los archivos de la carpeta de la obra. Los porcentajes, bloqueos y prioridades son cálculos de apoyo; no sustituyen la verificación en obra.</div>
</div>
<script>
const DATA = {data_json};
document.querySelectorAll('.nav button').forEach(btn=>btn.addEventListener('click',()=>{{
  document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(btn.dataset.view).classList.add('active');
}}));
function pctColor(p){{return p<40?'#d9483c':p<70?'#e07b1a':'#2e9e5b';}}
if(DATA.serie.length) new Chart(document.getElementById('chartSerie'),{{type:'line',
  data:{{labels:DATA.serie.map(d=>d.fecha),datasets:[
    {{label:'% estricto',data:DATA.serie.map(d=>d.pct_estricto),borderColor:'#123a63',backgroundColor:'#123a6320',borderWidth:2,tension:.25,fill:true,pointRadius:2}},
    {{label:'% estimado',data:DATA.serie.map(d=>d.pct_ponderado),borderColor:'#f5a524',borderWidth:2,borderDash:[5,3],tension:.25,pointRadius:2}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'top'}}}},scales:{{y:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}}}}}});
if(Object.keys(DATA.por_planta.series).length){{
  const eds=Object.keys(DATA.por_planta.series),col=['#123a63','#f5a524','#2e7dd7','#8172B3'];
  new Chart(document.getElementById('chartPlanta'),{{type:'bar',
    data:{{labels:DATA.por_planta.labels,datasets:eds.map((e,i)=>({{label:e,data:DATA.por_planta.series[e],backgroundColor:col[i%col.length]}}))}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'top'}}}},scales:{{y:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}}}}}});
}}
if(DATA.por_tarea.length) new Chart(document.getElementById('chartTareas'),{{type:'bar',
  data:{{labels:DATA.por_tarea.map(t=>t[0]),datasets:[{{label:'% avance',data:DATA.por_tarea.map(t=>t[1]),backgroundColor:DATA.por_tarea.map(t=>pctColor(t[1]))}}]}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{beginAtZero:true,max:100,ticks:{{callback:v=>v+'%'}}}}}}}}}});
document.querySelectorAll('.show-ub').forEach(a=>a.addEventListener('click',function(ev){{
  ev.preventDefault();
  const extra=this.previousElementSibling;
  if(extra.style.display==='none'){{extra.style.display='block';this.textContent='▲ Ocultar';}}
  else{{extra.style.display='none';this.textContent='+'+this.dataset.n+' ubicaciones más';}}
}}));
function filtrarPrio(){{
  const fase=document.getElementById('filtro-fase')?.value||'';
  const sit=document.getElementById('filtro-sit')?.value||'';
  const rows=document.querySelectorAll('#tabla-prio tbody tr[data-fase]');
  let n=0;
  rows.forEach(tr=>{{
    const ok=(!fase||tr.dataset.fase===fase)&&(!sit||tr.dataset.sit===sit);
    tr.style.display=ok?'':'none';
    if(ok)n++;
  }});
  const cnt=document.getElementById('prio-count');
  if(cnt)cnt.textContent=n+' bloque(s) visibles';
}}
document.getElementById('filtro-fase')?.addEventListener('change',filtrarPrio);
document.getElementById('filtro-sit')?.addEventListener('change',filtrarPrio);
filtrarPrio();
</script></body></html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return {
        'kpis': kpis, 'bloqueos': bloqueos, 'sin_cambios': sin_cambios,
        'n_docs': len(documentos), 'output_path': output_path,
        'materiales_aviso': materiales.get('aviso'),
        'prioridades': prioridades,
    }












