# -*- coding: utf-8 -*-
"""
GENERAR TODOS — orquestador Informe Sagarde IA
------------------------------------------------
1. Por cada obra dada de alta: llama a su adaptador (lee su hoja de
   revisiones), lee materiales + ficha + documentos de su carpeta, y genera
   el panel HTML de 8 secciones dentro de la carpeta de la obra.
2. Genera el index.html raiz con una tarjeta por obra abierta.
3. (Opcional) genera un PDF del panel para consulta en movil.

Ejecutar:  python generar_todos.py
o doble clic en Actualizar_Sagarde.bat
"""
import os
import sys
import html
import json
import re
import unicodedata
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OBRAS_ABIERTAS_DIR = os.path.dirname(BASE_DIR)
ROOT_DIR = os.path.dirname(OBRAS_ABIERTAS_DIR)
RESUMEN_JSON = os.path.join(BASE_DIR, 'resumen_obras.json')
REVISIONES_JS = os.path.join(BASE_DIR, 'obras_revisiones.js')
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "adaptadores"))
sys.path.insert(0, os.path.join(ROOT_DIR, "_MOTOR_SAGARDE", "scripts"))

import panel_obra  # noqa: E402
import lectores    # noqa: E402
import priorizador_trabajos  # noqa: E402
import memoria_obra as mem  # noqa: E402
import motor_informes       # noqa: E402

OBRAS = [
    {
        'id': 'gernika',
        'nombre': '2025 GERNIKA 32V',
        'subtitulo': 'Electricidad y telecomunicaciones · 1 bloque, 2 portales, 32 viviendas',
        'adaptador': 'adaptador_gernika',
        'carpeta_obra': '2025 GERNIKA 32V',
        'bloque_revision': 'Bloque 1',
        'materiales_rel': os.path.join('REVISIONES', 'hoja de entrega de materiales GERNIKA.xlsx'),
    },
    {
        'id': 'mungia',
        'nombre': '2026 MUNGIA ACR NEINOR',
        'subtitulo': 'Electricidad y telecomunicaciones · Edificios ZR1.1 / ZR1.2',
        'adaptador': 'adaptador_mungia',
        'carpeta_obra': '2026 MUNGIA ACR NEINOR',
        'bloque_revision': 'ZR1',
        'materiales_rel': os.path.join('REVISIONES', 'hoja de entrega de materiales MUNGIA.xlsx'),
    },
    {
        'id': 'bolueta',
        'nombre': '2026 BOLUETA ACR',
        'subtitulo': 'Electricidad y telecomunicaciones · Portal único, B+23',
        'adaptador': 'adaptador_bolueta',
        'carpeta_obra': '2026 BOLUETA ACR',
        'bloque_revision': 'Bolueta',
        'alias_portales_revision': {'BOLUETA': 'Portal único'},
        'materiales_rel': os.path.join('REVISIONES', 'hoja de entrega de materiales BOLUETA.xlsx'),
    },
    {
        'id': 'obisporueta',
        'nombre': '2025 BILBAO OBISPO ORUETA',
        'subtitulo': 'Electricidad y telecomunicaciones · Obispo Orueta, 2 - Bilbao',
        'adaptador': 'adaptador_obisporueta',
        'carpeta_obra': '2025 BILBAO OBISPO ORUETA',
        'bloque_revision': 'Obispo Orueta 2',
        'alias_portales_revision': {'Obispo Orueta 2': 'Portal único'},
        'materiales_rel': os.path.join('REVISIONES SAGARDE', 'hoja de entrega de materiales OBISPO ORUETA.xlsx'),
    },
    {
        'id': 'gorliz',
        'nombre': '2026 GORLIZ HOSPITAL',
        'subtitulo': 'Electricidad y telecomunicaciones · Hospital de Gorliz',
        'adaptador': 'adaptador_gorliz',
        'carpeta_obra': '2026 GORLIZ HOSPITAL',
        'bloque_revision': 'Hospital de Gorliz',
        # Aun sin revisiones (INFORME SAGARDE IA/revision_gorliz_DDMMAAAA.json no existe todavia).
        # El adaptador ya soporta esto: devuelve historial vacio sin romper el pipeline.
        # Ruta de materiales anticipada; aun no existe el fichero en la obra.
        'materiales_rel': os.path.join('REVISIONES', 'hoja de entrega de materiales GORLIZ.xlsx'),
    },
    # Añadir aquí la siguiente obra cuando tenga su adaptador.
    # --- OBRAS CERRADAS (desactivadas — carpetas en SAGARDE (OLD)\OBRAS CERRADAS\) ---
    # {
    #     'id': 'zorrozaure',
    #     'nombre': '2024 BILBAO 88V ZORROZAURE',
    #     'subtitulo': 'Electricidad y telecomunicaciones · Bloques A1 / A2 (snapshot único, sin serie temporal)',
    #     'adaptador': 'adaptador_zorrozaure',
    #     'carpeta_obra': '2024 BILBAO 88V ZORROZAURE',
    #     'materiales_rel': os.path.join('hoja de entrega de materiales ZORROZAURE.xlsx'),
    # },
    # {
    #     'id': 'egurrola',
    #     'nombre': '2025 GETXO 12V EGURROLA',
    #     'subtitulo': 'Electricidad y telecomunicaciones · 12 viviendas, C/ Artibai',
    #     'adaptador': 'adaptador_egurrola',
    #     'carpeta_obra': '2025 GETXO 12V EGURROLA',
    #     'materiales_rel': os.path.join('hoja de entrega de materiales EGURROLA.xlsx'),
    # },
]


def _slug(valor):
    texto = unicodedata.normalize('NFKD', str(valor or ''))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r'[^a-zA-Z0-9]+', '_', texto).strip('_').lower()
    return texto or 'sin_nombre'


def _clave_natural(valor):
    partes = re.split(r'(\d+)', str(valor or '').strip().casefold())
    return tuple((0, int(p)) if p.isdigit() else (1, p) for p in partes if p != '')


def _clave_planta(valor):
    texto = str(valor or '').strip()
    normal = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode().casefold()
    if normal in {'b', 'pb', 'bajo', 'baja', 'planta baja'}:
        return (1, 0, ())
    if re.fullmatch(r'-?\d+(?:[.,]\d+)?', normal):
        numero = float(normal.replace(',', '.'))
        return (0 if numero < 0 else 2, numero, ())
    return (3, 0, _clave_natural(texto))


def cargar_ficha_obra(obra):
    """Devuelve ficha_obra.json de la obra, o None si aun no tiene.

    La ficha es la FUENTE de la estructura (bloques/portales/plantas/
    ubicaciones). Sin ella hay que deducirla de las celdas que alguien
    relleno alguna vez, que es como se hacia hasta ahora: una ubicacion no
    marcada simplemente no existia.
    """
    ruta = os.path.join(
        OBRAS_ABIERTAS_DIR, obra['carpeta_obra'],
        'INFORME SAGARDE IA', 'ficha_obra.json',
    )
    if not os.path.isfile(ruta):
        return None
    try:
        with open(ruta, encoding='utf-8') as f:
            return json.load(f)
    except Exception as exc:
        print(f"  [AVISO FICHA] {obra['nombre']}: no se pudo leer la ficha ({exc})."
              f" Se deduce la estructura de las revisiones, como antes.")
        return None


def registro_revision_desde_ficha(obra, ficha, prioridades):
    """Igual que crear_registro_revision pero leyendo la estructura de la ficha.

    Produce EXACTAMENTE el mismo formato (mismos ids src_*, mismas claves de
    celda) para no romper las hojas ya exportadas ni el generador. Lo unico
    que cambia es de donde sale la verdad:
      - las ubicaciones son las declaradas, no las que aparecieron en una hoja
      - los estados salen de la ficha, que ya incorpora las correcciones
        manuales que antes se perdian

    Solo se exportan X/M//. 'P' (pendiente confirmado) y '?' (desconocido)
    viajan como celda vacia, igual que hoy: la hoja de campo los imprime en
    blanco para rellenar. Distinguirlos en la hoja es un paso posterior.
    """
    alias = (ficha.get('estructura') or {}).get('alias_historico') or {}
    bloques_ficha = (ficha.get('estructura') or {}).get('bloques') or []
    if not bloques_ficha:
        return None

    slug = _slug(obra['id'])
    portales, mapa = [], {}
    for i_portal, portal in enumerate(bloques_ficha[0].get('portales') or [], 1):
        portal_id = f'src_{slug}_p{i_portal}'
        plantas = []
        for i_planta, planta in enumerate(portal.get('plantas') or [], 1):
            planta_id = f'{portal_id}_f{i_planta}'
            vivs = []
            for ubi in planta.get('ubicaciones') or []:
                # Se muestra el nombre historico ('A2' = vivienda A de 2
                # habitaciones en Mungia) para que la hoja de campo siga
                # siendo reconocible; el id canonico es la letra.
                clave_alias = f"{portal['id']}__{planta['id']}__{ubi['id']}"
                vivs.append(alias.get(clave_alias, ubi['id']))
                mapa[(portal['id'], planta['id'], ubi['id'])] = (
                    portal_id, planta_id, alias.get(clave_alias, ubi['id']))
            if not vivs:
                continue
            plantas.append({'id': planta_id, 'nombre': planta.get('nombre'),
                            'vivs': vivs})
        if plantas:
            portales.append({
                'id': portal_id,
                'nombre': portal.get('nombre'),
                'referencia_portal': portal.get('referencia') or portal.get('nombre'),
                'plantas': plantas,
            })
    if not portales:
        return None

    catalogo = []
    for tajo in (ficha.get('tajos') or {}).get('detalle') or []:
        try:
            orden = float(tajo.get('orden') or 9999)
        except (TypeError, ValueError):
            orden = 9999
        catalogo.append({
            'id': tajo['id'],
            'name': tajo.get('nombre') or tajo['id'],
            'g': tajo.get('fase') or 'Otros',
            'p': {'propio': 'p', 'externo': 'e', 'coordinacion': 'c'}.get(
                str(tajo.get('propiedad') or '').casefold(), 'c'),
            'a': {'vivienda': 'v', 'zona_comun': 'z', 'edificio': 'd'}.get(
                str(tajo.get('ambito') or '').casefold(), 'v'),
            'orden': int(orden) if float(orden).is_integer() else orden,
        })
    catalogo.sort(key=lambda t: (t['orden'], _clave_natural(t['name'])))
    if not catalogo:
        return None

    estados = {}
    for clave, dato in (ficha.get('estados') or {}).items():
        valor = (dato or {}).get('v')
        if valor not in {'X', 'M', '/'}:
            continue
        try:
            portal_f, planta_f, tajo_f, ubi_f = clave.split('__')
        except ValueError:
            continue
        ids = mapa.get((portal_f, planta_f, ubi_f))
        if ids:
            portal_id, planta_id, viv = ids
            estados[f'{portal_id}__{planta_id}__{tajo_f}__{viv}'] = valor

    resumen = prioridades.get('resumen') or {}
    return {
        'id': obra['id'],
        'nombre': obra['nombre'],
        'revision': prioridades.get('revision') or '',
        'generado': prioridades.get('generado') or '',
        'catalogo_version': prioridades.get('catalogo_version'),
        'fuente_estructura': 'ficha_obra.json',
        'resumen': {
            'tajos': len(catalogo),
            'estados_precargados': len(estados),
            'viviendas_planta': sum(
                len(planta['vivs']) for portal in portales for planta in portal['plantas']
            ),
            'listos': resumen.get('listos', 0),
            'verificar': resumen.get('verificar', 0),
            'bloqueados': resumen.get('bloqueados', 0),
        },
        'bloques': [{
            'id': f'src_{slug}_b1',
            'nombre': bloques_ficha[0].get('nombre') or obra.get('bloque_revision') or obra['nombre'],
            'portales': portales,
        }],
        'catalog': catalogo,
        'estados': estados,
    }


def crear_registro_revision(obra, prioridades):
    """Convierte el estado consolidado del portal en datos para hojas A4."""
    detalle = prioridades.get('detalle_items') or []
    if not detalle:
        return None
    catalogo_por_id = {}
    ubicaciones = {}
    for item in detalle:
        tarea_id = str(item.get('tarea_id') or '').strip()
        edificio = str(item.get('edificio') or '').strip()
        planta = str(item.get('planta') or '').strip()
        unidad = str(item.get('unidad') or '').strip()
        if tarea_id and tarea_id not in catalogo_por_id:
            propiedad = str(item.get('propiedad') or '').strip().casefold()
            ambito = str(item.get('ambito') or '').strip().casefold()
            try:
                orden = float(item.get('orden_ejecucion') or 9999)
            except (TypeError, ValueError):
                orden = 9999
            catalogo_por_id[tarea_id] = {
                'id': tarea_id,
                'name': str(item.get('trabajo') or tarea_id).strip(),
                'g': str(item.get('fase_nombre') or 'Otros').strip(),
                'p': {'propio': 'p', 'externo': 'e', 'coordinacion': 'c'}.get(propiedad, 'c'),
                'a': {'vivienda': 'v', 'zona_comun': 'z', 'edificio': 'd'}.get(ambito, 'v'),
                'orden': orden,
            }
        if edificio and planta and unidad and unidad not in {'—', '-'}:
            ubicaciones.setdefault(edificio, {}).setdefault(planta, set()).add(unidad)

    edificios = sorted(ubicaciones, key=_clave_natural)
    if not edificios or not catalogo_por_id:
        return None
    alias_portales = obra.get('alias_portales_revision') or {}
    bloque_id = f"src_{_slug(obra['id'])}_b1"
    portales = []
    ids_ubicacion = {}
    for indice_portal, edificio in enumerate(edificios, 1):
        portal_id = f"src_{_slug(obra['id'])}_p{indice_portal}"
        plantas = []
        orden_plantas = sorted(ubicaciones[edificio], key=_clave_planta)
        for indice_planta, planta in enumerate(orden_plantas, 1):
            planta_id = f"{portal_id}_f{indice_planta}"
            viviendas = sorted(ubicaciones[edificio][planta], key=_clave_natural)
            plantas.append({'id': planta_id, 'nombre': planta, 'vivs': viviendas})
            ids_ubicacion[(edificio, planta)] = (portal_id, planta_id)
        portales.append({
            'id': portal_id,
            'nombre': alias_portales.get(edificio, edificio),
            'referencia_portal': edificio,
            'plantas': plantas,
        })

    estados = {}
    for item in detalle:
        tarea_id = str(item.get('tarea_id') or '').strip()
        edificio = str(item.get('edificio') or '').strip()
        planta = str(item.get('planta') or '').strip()
        unidad = str(item.get('unidad') or '').strip()
        estado = str(item.get('estado_actual', item.get('estado', '')) or '').strip().upper()
        ids = ids_ubicacion.get((edificio, planta))
        if ids and tarea_id and unidad and estado in {'X', 'M', '/'}:
            portal_id, planta_id = ids
            estados[f'{portal_id}__{planta_id}__{tarea_id}__{unidad}'] = estado

    catalogo = sorted(catalogo_por_id.values(), key=lambda t: (t['orden'], _clave_natural(t['name'])))
    for tajo in catalogo:
        if float(tajo['orden']).is_integer():
            tajo['orden'] = int(tajo['orden'])
    resumen = prioridades.get('resumen') or {}
    return {
        'id': obra['id'],
        'nombre': obra['nombre'],
        'revision': prioridades.get('revision') or '',
        'generado': prioridades.get('generado') or '',
        'catalogo_version': prioridades.get('catalogo_version'),
        'resumen': {
            'tajos': len(catalogo),
            'estados_precargados': len(estados),
            'viviendas_planta': sum(
                len(planta['vivs']) for portal in portales for planta in portal['plantas']
            ),
            'listos': resumen.get('listos', 0),
            'verificar': resumen.get('verificar', 0),
            'bloqueados': resumen.get('bloqueados', 0),
        },
        'bloques': [{
            'id': bloque_id,
            'nombre': obra.get('bloque_revision') or obra['nombre'],
            'portales': portales,
        }],
        'catalog': catalogo,
        'estados': estados,
    }


def publicar_registro_revisiones():
    """Publica un JS común, legible también al abrir la app con file://."""
    registros = []
    errores = []
    for obra in OBRAS:
        ruta = os.path.join(
            OBRAS_ABIERTAS_DIR, obra['carpeta_obra'],
            'INFORME SAGARDE IA', 'prioridades_trabajos.json',
        )
        if not os.path.isfile(ruta):
            errores.append(f"{obra['nombre']}: sin prioridades_trabajos.json")
            continue
        try:
            with open(ruta, encoding='utf-8') as f:
                prioridades = json.load(f)
            # Si la obra tiene ficha, manda la ficha. Si no, se deduce la
            # estructura de las revisiones como se ha hecho siempre.
            ficha = cargar_ficha_obra(obra)
            registro = None
            if ficha:
                registro = registro_revision_desde_ficha(obra, ficha, prioridades)
                if registro:
                    print(f"  [FICHA] {obra['nombre']}: estructura leida de "
                          f"ficha_obra.json ({registro['resumen']['viviendas_planta']} "
                          f"ubicaciones).")
                else:
                    print(f"  [AVISO FICHA] {obra['nombre']}: la ficha no tiene "
                          f"estructura utilizable. Se deduce de las revisiones.")
            if registro is None:
                registro = crear_registro_revision(obra, prioridades)
            if registro:
                registros.append(registro)
            else:
                errores.append(f"{obra['nombre']}: sin detalle de viviendas")
        except Exception as exc:
            errores.append(f"{obra['nombre']}: {exc}")

    meta = {
        'version': 1,
        'generado': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'obras': len(registros),
        'errores': errores,
    }
    contenido = (
        'window.SAGARDE_OBRAS_REVISION = '
        + json.dumps(registros, ensure_ascii=False, separators=(',', ':'))
        + ';\nwindow.SAGARDE_OBRAS_REVISION_META = '
        + json.dumps(meta, ensure_ascii=False, separators=(',', ':'))
        + ';\n'
    )
    with open(REVISIONES_JS, 'w', encoding='utf-8', newline='\n') as f:
        f.write(contenido)
    print(f"Registro de hojas de revisión: {REVISIONES_JS} ({len(registros)} obras)")
    for error in errores:
        print(f"  [AVISO REVISIONES] {error}")
    return meta

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sagarde | Obras abiertas</title>
<style>
:root{--bg:#eef1f4;--card:#fff;--ink:#182230;--muted:#647184;--line:#d0d5dd;--brand:#b42318;--nav:#0b1f3a;--nav2:#123a63;--accent:#f5a524;--ok:#2e9e5b;--warn:#e07b1a;--bad:#d9483c;--radius:9px;}
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;background:var(--bg);color:var(--ink);}
a{color:inherit;}
.top{background:linear-gradient(120deg,var(--nav),var(--nav2));color:#fff;border-bottom:4px solid var(--brand);}
.top-inner{max-width:1440px;margin:auto;padding:18px 28px;display:flex;align-items:center;gap:20px;}
.logo{width:min(290px,22vw);height:auto;object-fit:contain;border-radius:9px;box-shadow:0 0 0 3px var(--brand),0 6px 28px rgba(0,0,0,.5);}
.identity{min-width:0;}.identity strong{font-size:21px;display:block;}.identity span{font-size:12px;color:#c7d3e3;}
.top-actions{margin-left:auto;display:flex;gap:8px;}
.top-actions a{text-decoration:none;border:1px solid rgba(255,255,255,.35);color:#fff;padding:9px 12px;border-radius:5px;font-size:13px;font-weight:600;}
.wrap{max-width:1440px;margin:0 auto;padding:24px 28px 38px;}
.intro{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap;margin-bottom:18px;}
.sub{font-size:13px;color:var(--muted);margin:0;}
.search-wrap{width:min(360px,100%);position:relative;}
.search{width:100%;height:42px;padding:0 42px 0 14px;border:1px solid #98a2b3;border-radius:6px;background:#fff;font:inherit;}
.search-symbol{position:absolute;right:14px;top:11px;color:#667085;}
.empty{display:none;background:#fff;border-radius:var(--radius);padding:30px;text-align:center;color:var(--muted);}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;}
.obra{background:var(--card);border-radius:var(--radius);padding:20px 22px;box-shadow:0 1px 3px rgba(0,0,0,.08);text-decoration:none;color:var(--ink);display:block;transition:transform .1s;border-top:4px solid var(--accent);}
.obra:hover{transform:translateY(-2px);box-shadow:0 4px 14px rgba(0,0,0,.12);}
.obra.disabled{border-top-color:#c5ccd6;cursor:default;}
.obra.disabled:hover{transform:none;box-shadow:0 1px 3px rgba(0,0,0,.08);}
.obra h2{font-size:15.5px;font-weight:700;margin-bottom:10px;}
.obra .estado{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:700;margin-bottom:8px;}
.obra .pct{font-size:30px;font-weight:800;margin-bottom:2px;}
.obra .pct.ok{color:var(--ok);}.obra .pct.warn{color:var(--warn);}.obra .pct.bad{color:var(--bad);}.obra .pct.pending{color:var(--muted);}
.obra .row{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-top:10px;}
.obra .alerta{margin-top:10px;font-size:12px;color:var(--bad);font-weight:600;}
.footer{text-align:right;font-size:11px;color:var(--muted);margin-top:16px;}
@media(max-width:900px){.logo{width:190px;}}
@media(max-width:600px){.top-inner,.wrap{padding-left:14px;padding-right:14px;}.logo{width:160px;}.top-actions{display:none;}}
</style></head><body>
<header class="top"><div class="top-inner">
  <img class="logo" src="../POST-VENTAS/logo_sagarde.jpg" alt="Sagarde">
  <div class="identity"><strong>Obras abiertas</strong><span>Seguimiento operativo e informes de avance en tiempo real</span></div>
  <nav class="top-actions">
    <a href="../index.html">&#8962; Portal</a>
    <a href="./">Obras abiertas</a>
    <a href="../POST-VENTAS/index.html">Post-ventas</a>
    <a href="../MANTENIMIENTOS/index.html">Mantenimientos</a>
    <a href="../SAGARDE%20(OLD)/OBRAS%20CERRADAS/index.html">Obras cerradas</a>
  </nav>
</div></header>
<div class="wrap">
  <div class="intro">
    <p class="sub">__N_OBRAS__ obra(s) en carpeta · __N_PANELES__ con panel IA · actualizado __GENERADO__</p>
    <label class="search-wrap"><input id="s" class="search" type="search" placeholder="Buscar obra..."><span class="search-symbol">&#9906;</span></label>
  </div>
  <div class="grid" id="grid">__TARJETAS__</div>
  <div class="empty" id="empty">No hay coincidencias.</div>
  <p class="footer">Actualizado __GENERADO__ · Ejecuta Actualizar_Sagarde.bat para refrescar</p>
</div>
<script>
const s=document.getElementById('s'),cards=[...document.querySelectorAll('#grid .obra')],empty=document.getElementById('empty');
s.addEventListener('input',()=>{const q=s.value.trim().toLowerCase();let n=0;
cards.forEach(c=>{const ok=!q||(c.dataset.search||'').includes(q);c.style.display=ok?'':'none';if(ok)n++;});
empty.style.display=n?'none':'block';});
</script>
</body></html>"""

TARJETA = """<a class="obra" href="__HREF__" data-search="__BUSCA__"><h2>__NOMBRE__</h2>
<div class="pct __CLASE__">__PCT__%</div>
<div class="row"><span>Último archivo</span><span>__ULTIMO_ARCHIVO__</span></div>
<div class="row"><span>Última revisión</span><span>__ULTIMA__</span></div>
<div class="row"><span>Revisiones</span><span>__NREV__</span></div>
<div class="row"><span>Documentos</span><span>__NDOCS__</span></div>__ALERTA__</a>"""

TARJETA_PENDIENTE = """<div class="obra disabled" data-search="__BUSCA__"><h2>__NOMBRE__</h2>
<div class="estado">Pendiente de alta</div>
<div class="pct pending">—</div>
<div class="row"><span>Último archivo</span><span>__ULTIMO_ARCHIVO__</span></div>
<div class="row"><span>Panel IA</span><span>No generado</span></div>
<div class="row"><span>Documentos</span><span>__NDOCS__</span></div>
<div class="alerta">Añadir adaptador para activar seguimiento</div></div>"""


def clase_pct(p):
    return 'ok' if p >= 70 else 'warn' if p >= 40 else 'bad'


def fecha_corta(timestamp):
    if not timestamp:
        return '—'
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')


def ultima_actividad_obra(carpeta_abs):
    """
    Fecha del archivo mas reciente dentro de una obra.
    Se excluye INFORME SAGARDE IA para que regenerar paneles no cambie el orden.
    """
    try:
        ultima = os.path.getmtime(carpeta_abs)
    except OSError:
        ultima = 0

    for root, dirs, files in os.walk(carpeta_abs):
        dirs[:] = [d for d in dirs if d != 'INFORME SAGARDE IA']
        for fn in files:
            if fn.startswith('~$') or fn.lower() in ('plot.log', 'thumbs.db', 'desktop.ini'):
                continue
            ruta_abs = os.path.join(root, fn)
            try:
                ultima = max(ultima, os.path.getmtime(ruta_abs))
            except OSError:
                continue
    return ultima


def carpetas_obra():
    """Devuelve las carpetas de obra reales, ordenadas por ultima actividad."""
    if not os.path.isdir(OBRAS_ABIERTAS_DIR):
        return []
    obras = []
    for nombre in os.listdir(OBRAS_ABIERTAS_DIR):
        ruta = os.path.join(OBRAS_ABIERTAS_DIR, nombre)
        if not os.path.isdir(ruta):
            continue
        if nombre.startswith('_'):
            continue
        obras.append({
            'nombre': nombre,
            'ultima_ts': ultima_actividad_obra(ruta),
        })
    return sorted(obras, key=lambda o: (-o['ultima_ts'], o['nombre'].casefold()))


def n_documentos_obra(carpeta_abs):
    return len(lectores.listar_documentos(carpeta_abs, OBRAS_ABIERTAS_DIR))


def generar_index(resultados):
    resultados_por_carpeta = {r['carpeta_obra']: r for r in resultados}
    carpetas = carpetas_obra()
    tarjetas = ""
    n_paneles = 0

    for carpeta in carpetas:
        nombre_carpeta = carpeta['nombre']
        ultimo_archivo = fecha_corta(carpeta['ultima_ts'])
        carpeta_abs = os.path.join(OBRAS_ABIERTAS_DIR, nombre_carpeta)
        panel_path = os.path.join(carpeta_abs, 'INFORME SAGARDE IA', 'panel.html')
        r = resultados_por_carpeta.get(nombre_carpeta)

        if r:
            n_paneles += 1
            avisos = []
            if r['sin_cambios']:
                avisos.append("Sin cambios en la última revisión")
            if r['n_bloqueos']:
                avisos.append(f"{r['n_bloqueos']} bloqueo(s)")
            alerta = f'<div class="alerta">⚠ {" · ".join(avisos)}</div>' if avisos else ''
            t = TARJETA
            valores = [
                ('__HREF__', html.escape(r['href'], quote=True)),
                ('__BUSCA__', html.escape(r['nombre'].lower(), quote=True)),
                ('__NOMBRE__', html.escape(r['nombre'])),
                ('__PCT__', str(r['pct'])),
                ('__CLASE__', clase_pct(r['pct'])),
                ('__ULTIMO_ARCHIVO__', html.escape(ultimo_archivo)),
                ('__ULTIMA__', html.escape(str(r['ultima']))),
                ('__NREV__', str(r['n_rev'])),
                ('__NDOCS__', str(r['n_docs'])),
                ('__ALERTA__', alerta),
            ]
            for k, v in valores:
                t = t.replace(k, v)
            tarjetas += t
            continue

        if os.path.isfile(panel_path):
            n_paneles += 1
            href = os.path.relpath(panel_path, OBRAS_ABIERTAS_DIR).replace('\\', '/')
            t = TARJETA_PENDIENTE.replace('class="obra disabled"', 'class="obra"')
            t = t.replace('<div class="estado">Pendiente de alta</div>', '<div class="estado">Panel generado</div>')
            t = t.replace('<div class="row"><span>Panel IA</span><span>No generado</span></div>',
                          '<div class="row"><span>Panel IA</span><span>Disponible</span></div>')
            t = t.replace('Añadir adaptador para activar seguimiento', 'Panel existente sin regenerar en esta ejecución')
            t = t.replace('<div class="obra"', f'<a class="obra" href="{html.escape(href, quote=True)}"', 1)
            t = t[:-6] + '</a>' if t.endswith('</div>') else t
            t = t.replace('__NOMBRE__', html.escape(nombre_carpeta))
            t = t.replace('__BUSCA__', html.escape(nombre_carpeta.lower(), quote=True))
            t = t.replace('__ULTIMO_ARCHIVO__', html.escape(ultimo_archivo))
            t = t.replace('__NDOCS__', str(n_documentos_obra(carpeta_abs)))
            tarjetas += t
            continue

        t = TARJETA_PENDIENTE
        t = t.replace('__NOMBRE__', html.escape(nombre_carpeta))
        t = t.replace('__BUSCA__', html.escape(nombre_carpeta.lower(), quote=True))
        t = t.replace('__ULTIMO_ARCHIVO__', html.escape(ultimo_archivo))
        t = t.replace('__NDOCS__', str(n_documentos_obra(carpeta_abs)))
        tarjetas += t

    if not carpetas:
        tarjetas = '<div class="empty">Todavía no hay ninguna obra en esta carpeta.</div>'

    index = INDEX_TEMPLATE.replace('__N_OBRAS__', str(len(carpetas)))
    index = index.replace('__N_PANELES__', str(n_paneles))
    index = index.replace('__GENERADO__', datetime.now().strftime('%d/%m/%Y %H:%M'))
    index = index.replace('__TARJETAS__', tarjetas)
    index_path = os.path.join(OBRAS_ABIERTAS_DIR, 'index.html')
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index)
    print(f"\nIndex: {index_path}")


def escribir_resumen_json(resultados):
    """
    Publica un resumen en JSON, pensado para que lo lea el portal raiz
    (COPIA SEGURIDAD SAGARDE/sagarde_portal.py) sin tener que importar
    este sistema como modulo Python ni volver a parsear el .docx/.xlsx
    de cada obra. Es un contrato de solo lectura: si este fichero no
    existe o esta desactualizado, el portal raiz debe degradar con
    gracia (mostrar solo recuento de carpetas), nunca inventar cifras.
    """
    resultados_por_carpeta = {r['carpeta_obra']: r for r in resultados}
    carpetas = carpetas_obra()

    obras_json = []
    con_pct = []
    bloqueos_totales = 0
    sin_cambios_total = 0

    for carpeta in carpetas:
        nombre_carpeta = carpeta['nombre']
        carpeta_abs = os.path.join(OBRAS_ABIERTAS_DIR, nombre_carpeta)
        panel_path = os.path.join(carpeta_abs, 'INFORME SAGARDE IA', 'panel.html')
        r = resultados_por_carpeta.get(nombre_carpeta)

        if r:
            con_pct.append(r['pct_ponderado'] or r['pct'])
            bloqueos_totales += r['n_bloqueos']
            if r['sin_cambios']:
                sin_cambios_total += 1
            obras_json.append({
                'nombre': r['nombre'],
                'carpeta': nombre_carpeta,
                'con_panel': True,
                'panel_actualizado': True,
                'pct_estricto': r['pct'],
                'pct_ponderado': r['pct_ponderado'],
                'n_rev': r['n_rev'],
                'n_docs': r['n_docs'],
                'n_bloqueos': r['n_bloqueos'],
                'sin_cambios': r['sin_cambios'],
                'ultima_revision': r['ultima'],
                'ultimo_archivo_ts': carpeta['ultima_ts'],
                'href': 'SAGARDE OBRAS ABIERTAS/' + r['href'],
                'pdf_href': ('SAGARDE OBRAS ABIERTAS/' + r['pdf_ejecutivo_href']) if r.get('pdf_ejecutivo_href') else None,
                'historico_pct': r.get('historico_pct', []),
                'variacion_pct': r.get('variacion_pct', 0.0),
            })
            continue

        tiene_panel_previo = os.path.isfile(panel_path)
        obras_json.append({
            'nombre': nombre_carpeta,
            'carpeta': nombre_carpeta,
            'con_panel': tiene_panel_previo,
            'panel_actualizado': False,
            'n_docs': n_documentos_obra(carpeta_abs),
            'ultimo_archivo_ts': carpeta['ultima_ts'],
            'href': ('SAGARDE OBRAS ABIERTAS/' + os.path.relpath(panel_path, OBRAS_ABIERTAS_DIR).replace('\\', '/')) if tiene_panel_previo else None,
        })

    resumen = {
        'generado': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'generado_ts': datetime.now().timestamp(),
        'totales': {
            'n_obras': len(carpetas),
            'n_con_panel': sum(1 for o in obras_json if o['con_panel']),
            'n_con_datos_frescos': len(con_pct),
            'avance_medio_ponderado': round(sum(con_pct) / len(con_pct), 1) if con_pct else None,
            'bloqueos_totales': bloqueos_totales,
            'obras_sin_cambios': sin_cambios_total,
        },
        'obras': obras_json,
    }
    with open(RESUMEN_JSON, 'w', encoding='utf-8') as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    print(f"Resumen JSON: {RESUMEN_JSON}")


def intentar_pdf(html_path, pdf_path):
    """Genera PDF del panel si hay motor disponible. No es crítico: si falla, se avisa."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto('file://' + html_path)
            pg.wait_for_timeout(1500)
            pg.pdf(path=pdf_path, format='A4', print_background=True)
            b.close()
        return True, 'playwright'
    except Exception as e:
        return False, str(e)


def main(hacer_pdf=True):
    resultados = []
    for obra in OBRAS:
        print(f"--- {obra['nombre']} ---")
        carpeta_abs = os.path.join(OBRAS_ABIERTAS_DIR, obra['carpeta_obra'])
        if not os.path.isdir(carpeta_abs):
            print("  Saltada: la carpeta de obra no existe en esta ubicación")
            continue

        try:
            adaptador = __import__(obra['adaptador'])
            historial = adaptador.cargar_historial()
        except Exception as e:
            print(f"  [ERROR] No se pudo leer la obra: {e}")
            print(f"  Causa probable: archivo abierto en Word, en sincronizacion o formato inesperado.")
            print(f"  El resto de obras se procesa igualmente.")
            continue

        salida_dir = os.path.join(carpeta_abs, 'INFORME SAGARDE IA')
        salida_html = os.path.join(salida_dir, 'panel.html')
        salida_prioridades = os.path.join(salida_dir, 'prioridades_trabajos.json')
        salida_dudas = os.path.join(salida_dir, 'dudas_pendientes.json')
        salida_memoria = os.path.join(salida_dir, 'memoria_obra.json')

        try:
            # Memoria de obra: acumula tajos de todas las revisiones
            tajos_memoria = mem.calcular_memoria(historial)
            mem_resumen = mem.guardar_memoria(salida_memoria, obra['nombre'], historial, tajos_memoria)
            print(f"  Memoria: {mem_resumen['total_tajos']} tajos "
                  f"({mem_resumen['activos']} activos, {mem_resumen['terminados']} terminados)")

            prioridades = priorizador_trabajos.priorizar_historial(
                historial, obra=obra['nombre']
            )
            priorizador_trabajos.escribir_json(prioridades, salida_prioridades)
            priorizador_trabajos.escribir_json({
                'version': prioridades.get('version'),
                'catalogo_version': prioridades.get('catalogo_version'),
                'obra': prioridades.get('obra'),
                'revision': prioridades.get('revision'),
                'generado': prioridades.get('generado'),
                'dudas_pendientes': prioridades.get('dudas_pendientes', []),
            }, salida_dudas)

            materiales = lectores.leer_materiales(os.path.join(carpeta_abs, obra['materiales_rel']))
            ficha = lectores.leer_ficha(os.path.join(carpeta_abs, 'FICHA DE OBRA.xlsx'))
            documentos = lectores.listar_documentos(carpeta_abs, salida_dir)

            bat_abs = os.path.abspath(os.path.join(BASE_DIR, 'Actualizar_Obras.bat'))
            volver = os.path.relpath(os.path.join(OBRAS_ABIERTAS_DIR, 'index.html'), salida_dir).replace('\\', '/')
            res = panel_obra.generar_panel(
                obra=obra['nombre'], subtitulo=obra['subtitulo'], historial=historial,
                materiales=materiales, ficha=ficha, documentos=documentos,
                prioridades=prioridades, output_path=salida_html, volver_href=volver,
                tajos_memoria=tajos_memoria, mem_resumen=mem_resumen, bat_path=bat_abs,
            )
        except Exception as e:
            print(f"  [ERROR] Fallo al generar el panel: {e}")
            print(f"  El panel anterior (si existe) no se sobreescribe. Continua con la siguiente obra.")
            continue

        print(f"  KPIs: {res['kpis']}")
        print(f"  Bloqueos: {len(res['bloqueos'])} · Docs: {res['n_docs']} · Sin cambios: {res['sin_cambios']}")
        print(f"  Prioridades: {prioridades['resumen']['listos']} listas · "
              f"{prioridades['resumen']['verificar']} a verificar · "
              f"{prioridades['resumen']['bloqueados']} bloqueadas")

        try:
            import generar_informe_ejecutivo
            generar_informe_ejecutivo.generar_para_obra(obra['nombre'])
        except Exception as e_exec:
            print(f"  [AVISO INFORME EJECUTIVO] {e_exec}")

        pdf_rel = None
        if hacer_pdf:
            pdf_path = os.path.join(salida_dir, 'informe_movil.pdf')
            ok, info = intentar_pdf(salida_html, pdf_path)
            if ok:
                pdf_rel = os.path.relpath(pdf_path, OBRAS_ABIERTAS_DIR).replace('\\', '/')
                print(f"  PDF móvil: OK ({info})")
            else:
                print(f"  PDF móvil: no generado ({info[:80]})")

        historico_pct = [round(motor_informes._pct_ponderado(s), 1) for _, s in historial[-6:]] if historial else []
        variacion_pct = round(historico_pct[-1] - historico_pct[-2], 1) if len(historico_pct) >= 2 else 0.0

        pdf_ejecutivo_nom = f"INFORME_EJECUTIVO_{re.sub(r'[^A-Z0-9]', '_', obra['nombre'].upper())}.pdf"
        pdf_ejecutivo_abs = os.path.join(salida_dir, pdf_ejecutivo_nom)
        pdf_ejecutivo_rel = os.path.relpath(pdf_ejecutivo_abs, OBRAS_ABIERTAS_DIR).replace('\\', '/') if os.path.isfile(pdf_ejecutivo_abs) else None

        resultados.append({
            'carpeta_obra': obra['carpeta_obra'],
            'nombre': obra['nombre'],
            'href': os.path.relpath(salida_html, OBRAS_ABIERTAS_DIR).replace('\\', '/'),
            'pct': res['kpis'].get('pct_estricto', 0) if res['kpis'] else 0,
            'pct_ponderado': res['kpis'].get('pct_ponderado', 0) if res['kpis'] else 0,
            'ultima': historial[-1][0] if historial else '—',
            'n_rev': len(historial), 'n_docs': res['n_docs'],
            'sin_cambios': res['sin_cambios'], 'n_bloqueos': len(res['bloqueos']),
            'n_prioridades': prioridades['resumen']['listos'],
            'n_prioridades_verificar': prioridades['resumen']['verificar'],
            'historico_pct': historico_pct,
            'variacion_pct': variacion_pct,
            'pdf_ejecutivo_href': pdf_ejecutivo_rel,
        })

    generar_index(resultados)
    escribir_resumen_json(resultados)
    publicar_registro_revisiones()


if __name__ == "__main__":
    if '--solo-revisiones' in sys.argv:
        publicar_registro_revisiones()
    else:
        main(hacer_pdf='--no-pdf' not in sys.argv)
