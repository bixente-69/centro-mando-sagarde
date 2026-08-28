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
import copy
import hashlib
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
sys.path.insert(0, os.path.join(ROOT_DIR, "_SISTEMA", "MOTOR", "scripts"))

import panel_obra  # noqa: E402
import lectores    # noqa: E402
import priorizador_trabajos  # noqa: E402
import cierre_expediente  # noqa: E402
import memoria_obra as mem  # noqa: E402
import motor_informes       # noqa: E402
import ficha_obra as fichas    # noqa: E402
import aplicar_revision        # noqa: E402
import trazabilidad_revisiones  # noqa: E402
import validar_revision        # noqa: E402
from registro_obras import OBRAS  # noqa: E402


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


def _correcciones_mas_recientes(carpeta_abs):
    """Devuelve los estados del fichero *.correcciones.json mas reciente de la
    obra, o {}. Son marcas escritas a boli sobre la hoja de campo: el dato mas
    directo que hay, y el que mas veces se ha perdido por no casar la clave."""
    import glob
    # Norma _SISTEMA (07/08/2026): los sidecars viven en REVISIONES*/_SISTEMA/.
    # Se siguen aceptando los sueltos en REVISIONES* por si queda alguno de
    # antes: perder un .correcciones.json es perder marcas escritas a boli,
    # el dato mas directo que hay.
    ficheros = []
    for carpeta_rev in ('REVISIONES', 'REVISIONES SAGARDE'):
        ficheros += glob.glob(
            os.path.join(carpeta_abs, carpeta_rev, '*.correcciones.json'))
        ficheros += glob.glob(
            os.path.join(carpeta_abs, carpeta_rev, '_SISTEMA',
                         '*.correcciones.json'))
    if not ficheros:
        return {}

    def fecha(ruta):
        m = re.search(r'(\d{2})(\d{2})(\d{4})', os.path.basename(ruta))
        if not m:
            return None
        texto = ''.join(m.groups())
        try:
            return datetime.strptime(texto, '%d%m%Y').date()
        except ValueError:
            return None

    fechados = [(fecha(ruta), ruta) for ruta in ficheros]
    malformados = sorted(
        os.path.basename(ruta) for fecha_archivo, ruta in fechados
        if fecha_archivo is None
    )
    if malformados:
        print("  [AVISO FICHA] se ignoran correcciones con fecha ausente o "
              "inválida: " + ', '.join(malformados))

    validos = [(fecha_archivo, ruta) for fecha_archivo, ruta in fechados
               if fecha_archivo is not None]
    if not validos:
        return {}

    fecha_reciente = max(fecha_archivo for fecha_archivo, _ in validos)
    candidatos = [ruta for fecha_archivo, ruta in validos
                  if fecha_archivo == fecha_reciente]

    def desempate(ruta):
        try:
            mtime = os.stat(ruta).st_mtime_ns
        except OSError:
            mtime = -1
        return (
            mtime,
            os.path.basename(ruta).casefold(),
            os.path.normcase(os.path.abspath(ruta)),
        )

    ruta_elegida = max(candidatos, key=desempate)
    if len(candidatos) > 1:
        nombres = ', '.join(sorted(os.path.basename(r) for r in candidatos))
        print(
            "  [AVISO FICHA] hay {} ficheros de correcciones con la misma "
            "fecha {}: {}. Se usa '{}' por tener la modificación más "
            "reciente (nombre como desempate).".format(
                len(candidatos),
                fecha_reciente.strftime('%d/%m/%Y'),
                nombres,
                os.path.basename(ruta_elegida),
            )
        )

    nombre = os.path.basename(ruta_elegida)
    try:
        with open(ruta_elegida, encoding='utf-8') as f:
            contenido = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        # Un fichero corrupto no debe tragarse en silencio: es la marca
        # escrita a boli, el dato mas directo que hay. Que grite y siga
        # con la regeneracion (el resto de la obra sigue siendo util).
        print(f"  [AVISO FICHA] {nombre}: no se pudo leer "
              f"({type(exc).__name__}: {exc}). No se aplicaran las "
              f"correcciones manuales de esta obra en esta pasada.")
        return {}

    # JSON sintacticamente valido pero con una forma inesperada (null, una
    # lista, una cadena...) es una corrupcion tan plausible como un JSON
    # roto -- por ejemplo una escritura a medias. Validar antes de usar
    # .get() para que esto tampoco tumbe la generacion del panel.
    if not isinstance(contenido, dict):
        print(f"  [AVISO FICHA] {nombre}: se esperaba un objeto JSON en la "
              f"raiz y llego {type(contenido).__name__}. No se aplicaran "
              f"las correcciones manuales de esta obra en esta pasada.")
        return {}

    estados = contenido.get('estados')
    if estados is None:
        return {}
    if not isinstance(estados, dict):
        print(f"  [AVISO FICHA] {nombre}: la clave 'estados' deberia ser un "
              f"objeto y llego {type(estados).__name__}. No se aplicaran "
              f"las correcciones manuales de esta obra en esta pasada.")
        return {}
    return estados


def _mapa_tajos_cortos(obra_id):
    """Codigo corto del adaptador ('cuad-mec') -> id del catalogo
    ('cuadro_mecanizado'). Las correcciones manuales usan el corto y la ficha
    el largo; sin esta traduccion no se pueden cruzar. Con el mapa vacio,
    _reclamar_correcciones() no casa ninguna clave y TODAS las correcciones
    manuales de la obra dejan de aplicarse en esa pasada: si algo falla aqui
    tiene que avisar, no callarse -- y nunca tumbar la generacion del panel."""
    try:
        modulo = __import__(f'adaptador_{obra_id}')
    except Exception as exc:
        # Import de codigo de terceros (el adaptador de la obra): puede
        # fallar de cualquier forma, no solo ImportError -- el cuerpo del
        # modulo puede lanzar lo que sea. Aqui si es razonable capturar
        # amplio, pero avisando siempre con el tipo de excepcion para saber
        # que paso.
        print(f"  [AVISO FICHA] no se pudo importar adaptador_{obra_id} "
              f"({type(exc).__name__}: {exc}). No se aplicaran las "
              f"correcciones manuales de esta obra en esta pasada.")
        return {}

    # Usar la función compartida de ficha_obra para construir el índice de
    # alias. Esto evita duplicación de lógica: ambos caminos (correcciones
    # manuales y snapshot) usan el mismo mapeo del catálogo.
    ruta_cat = os.path.join(BASE_DIR, 'reglas', 'CATALOGO_TAJOS.json')
    indice_alias = fichas._indice_tajo_por_nombre(ruta_catalogo=ruta_cat, avisar=True)
    if not indice_alias:
        # _indice_tajo_por_nombre ya habrá impreso el aviso si avisar=True
        return {}

    try:
        corto = getattr(modulo, 'TAJO_NOMBRE_CATALOGO', None) or \
            getattr(modulo, 'TAJO_NOMBRE', {})
        return {c: indice_alias[fichas._fold(n)] for c, n in corto.items()
                if fichas._fold(n) in indice_alias}
    except (TypeError, KeyError, AttributeError) as exc:
        # Defensa final: una entrada del adaptador con forma inesperada
        # no debe tumbar el panel tampoco.
        print(f"  [AVISO FICHA] adaptador_{obra_id} tiene datos con forma "
              f"inesperada ({type(exc).__name__}: {exc}). No se aplicaran "
              f"las correcciones manuales de esta obra en esta pasada.")
        return {}


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
    motivo = fichas.esta_rancia(ficha, prioridades)
    if motivo:
        print(f"  [AVISO FICHA] {obra['nombre']}: {motivo}. "
              f"La hoja de campo puede salir con estados atrasados.")

    alias = (ficha.get('estructura') or {}).get('alias_historico') or {}
    bloques_ficha = (ficha.get('estructura') or {}).get('bloques') or []
    if not bloques_ficha:
        return None

    slug = _slug(obra['id'])
    # Se recorren TODOS los bloques. Hasta el 05/08/2026 aqui ponia
    # `bloques_ficha[0]` y el resto se perdia sin dar error: la obra salia mas
    # pequena de lo que es y no habia forma de notarlo. Las 4 obras con ficha
    # tienen 1 bloque, asi que nadie lo vio hasta que OBRA PRUEBA nacio de una
    # hoja de 2 bloques. Manda la hoja: si declara 15 bloques, salen 15.
    # El contador de portales es GLOBAL a proposito: dos portales de bloques
    # distintos chocarian en el mismo `src_{slug}_p1`. Con un solo bloque el
    # numero coincide con el de siempre, asi que las obras reales no se mueven.
    bloques, mapa = [], {}
    i_portal = 0
    for i_bloque, bloque_ficha in enumerate(bloques_ficha, 1):
        portales = []
        for portal in bloque_ficha.get('portales') or []:
            i_portal += 1
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
        if portales:
            bloques.append({
                'id': f'src_{slug}_b{i_bloque}',
                'nombre': (bloque_ficha.get('nombre')
                           or obra.get('bloque_revision') or obra['nombre']),
                'portales': portales,
            })
    if not bloques:
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
                len(planta['vivs'])
                for bloque_reg in bloques
                for portal in bloque_reg['portales']
                for planta in portal['plantas']
            ),
            'listos': resumen.get('listos', 0),
            'verificar': resumen.get('verificar', 0),
            'bloqueados': resumen.get('bloqueados', 0),
        },
        'bloques': bloques,
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
__BLOQUE_PCT__
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


def bloque_pct(pct, n_rev):
    """El numero grande de la tarjeta de la obra.

    Una obra sin ninguna revision no esta al 0 %: no se sabe como esta. Pintar
    un 0 en rojo al lado de las obras medidas es sustituir un desconocido por
    cero, y ademas la lee como si fuera mal. Un 0 % MEDIDO si es un dato y se
    muestra como tal.
    """
    if not n_rev:
        return '<div class="pct pending">Sin revisiones</div>'
    return f'<div class="pct {clase_pct(pct)}">{pct}%</div>'


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
                ('__BLOQUE_PCT__', bloque_pct(r['pct'], r['n_rev'])),
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


ORIGEN_HISTORIAL_CONSOLIDADO = 'historial_consolidado'
_AUSENTE = object()


def _estado_normalizado_para_revision(valor, blanco_como_p=False):
    """Traduce con el mismo alfabeto base de ficha_obra, sin inventar reglas.

    El blanco del snapshot es ausencia de dato nuevo. El blanco de un sidecar
    de correcciones, en cambio, era historicamente una P explicita.
    """
    normalizado = fichas._normalizar_estado(valor)
    if not normalizado and not blanco_como_p:
        return ''
    return fichas.MAPA_ESTADO.get(normalizado)


def _huella_historial(snapshot_crudo, correcciones):
    contenido = json.dumps(
        {'snapshot': snapshot_crudo or [], 'correcciones': correcciones or {}},
        ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str,
    ).encode('utf-8')
    return hashlib.sha256(contenido).hexdigest()[:8]


def construir_revision_normalizada_desde_snapshot(
        obra, ficha_actual, snapshot_crudo, fecha, catalogo,
        correcciones=None, mapa_tajos_cortos=None,
        origen=ORIGEN_HISTORIAL_CONSOLIDADO):
    """Convierte la fotografia final del adaptador en REVISION_NORMALIZADA.

    Reutiliza los indices de ``ficha_obra`` que empleaba el camino antiguo.
    Las ubicaciones o tajos que el motor comun aun no puede representar no se
    fuerzan: quedan en avisos y la comparacion con el resultado antiguo decide
    si la obra puede cruzar el cutover.
    """
    correcciones = correcciones or {}
    mapa_tajos_cortos = mapa_tajos_cortos or {}
    avisos = []
    celdas = []

    id_por_nombre = {
        fichas._fold(tajo.get('nombre') or ''): tajo['id']
        for tajo in (ficha_actual.get('tajos') or {}).get('detalle') or []
    }
    ids_tajo_de_ficha = set(id_por_nombre.values())
    id_por_alias_catalogo = fichas._indice_tajo_por_nombre()
    ids_tajo_validos = validar_revision._ids_tajos(catalogo, obra['id'])
    por_id, por_nombre = fichas._indice_ubicaciones(ficha_actual)

    for indice, registro in enumerate(snapshot_crudo or []):
        nombre_tajo = str(registro.get('task') or '').strip()
        if not nombre_tajo:
            avisos.append(f'snapshot[{indice}]: registro sin tajo; omitido')
            continue
        nombre_fold = fichas._fold(nombre_tajo)
        tajo_id = (id_por_nombre.get(nombre_fold)
                   or id_por_alias_catalogo.get(nombre_fold)
                   or nombre_tajo)
        if (tajo_id not in ids_tajo_validos
                or tajo_id not in ids_tajo_de_ficha):
            avisos.append(
                f'snapshot[{indice}]: tajo {nombre_tajo!r} no representable '
                'por el motor comun; la salvaguarda comprobara la paridad')
            continue

        trio_canonico = (
            registro.get('portal_id'), registro.get('planta_id'),
            registro.get('unidad_id'))
        trio = (trio_canonico if all(trio_canonico)
                and trio_canonico in por_id else None)
        if trio is None:
            trio = fichas._localizar(
                por_nombre, registro.get('building'), registro.get('floor'),
                registro.get('unit'))
        if trio is None:
            avisos.append(
                f"snapshot[{indice}]: ubicacion "
                f"{registro.get('building')!r}/{registro.get('floor')!r}/"
                f"{registro.get('unit')!r} no resuelta; la salvaguarda "
                'comprobara la paridad')
            continue
        portal_id, planta_id, ubicacion_id = trio

        estado_leido = _estado_normalizado_para_revision(
            registro.get('status', ''))
        if estado_leido is None:
            avisos.append(
                f"snapshot[{indice}]: estado {registro.get('status')!r} no "
                'reconocido; la salvaguarda comprobara la paridad')
            continue
        celdas.append(validar_revision.crear_revision_celda(
            f'{portal_id}__{planta_id}__{tajo_id}__{ubicacion_id}',
            estado_leido,
        ))

    estados_actuales = ficha_actual.get('estados') or {}
    for clave_corta, valor in correcciones.items():
        partes = fichas.partir_clave(clave_corta)
        if partes is None:
            avisos.append(f'correccion {clave_corta!r}: clave invalida; omitida')
            continue
        portal_id, planta_id, tajo_corto, unidad = partes
        tajo_id = mapa_tajos_cortos.get(tajo_corto, tajo_corto)
        destino = f'{portal_id}__{planta_id}__{tajo_id}__{unidad}'
        if destino not in estados_actuales:
            destino = fichas._con_alias(
                ficha_actual, portal_id, planta_id, tajo_id, unidad,
                estados_actuales)
        if destino is None:
            avisos.append(
                f'correccion {clave_corta!r}: destino no resuelto; omitida')
            continue
        estado_leido = _estado_normalizado_para_revision(
            valor, blanco_como_p=True)
        if estado_leido is None:
            avisos.append(
                f'correccion {clave_corta!r}: estado {valor!r} no reconocido; '
                'omitida')
            continue
        # El camino historico reclama las correcciones despues del snapshot:
        # para una misma clave la correccion es el valor final, no dos cambios.
        celdas = [celda for celda in celdas if celda['clave'] != destino]
        celdas.append(validar_revision.crear_revision_celda(
            destino, estado_leido))

    fuente = f"{obra.get('adaptador') or 'adaptador'}.cargar_historial()[-1]"
    revision_id = (
        f"{obra['id']}__{fecha}__{origen}__"
        f'{_huella_historial(snapshot_crudo, correcciones)}')
    return validar_revision.crear_revision_normalizada(
        revision_id=revision_id,
        obra=obra['id'],
        fecha=fecha,
        origen=origen,
        fuente=fuente,
        celdas=celdas,
        metadata={
            'generado_por':
                'generar_todos.construir_revision_normalizada_desde_snapshot',
            'generado_en': datetime.now().isoformat(timespec='seconds'),
            'avisos': avisos,
            'hoja_usada': True,
        },
    )


def _valor_estado(estados, clave):
    if clave not in estados:
        return _AUSENTE
    registro = estados[clave]
    return registro.get('v') if isinstance(registro, dict) else None


def _formatear_valor_paridad(valor):
    return '<ausente>' if valor is _AUSENTE else repr(valor)


def _diferencias_estados(estados_antiguos, estados_nuevos):
    diferencias = []
    claves = sorted(set(estados_antiguos) | set(estados_nuevos))
    for clave in claves:
        antiguo = _valor_estado(estados_antiguos, clave)
        nuevo = _valor_estado(estados_nuevos, clave)
        if antiguo is _AUSENTE or nuevo is _AUSENTE or antiguo != nuevo:
            diferencias.append((clave, antiguo, nuevo))
    return claves, diferencias


def calcular_actualizacion_ficha_con_salvaguarda(
        obra, ficha_actual, snapshot_crudo, fecha, correcciones=None,
        mapa_tajos_cortos=None, catalogo=None):
    """Calcula en memoria los caminos antiguo y comun, y compara sus ``v``."""
    correcciones = correcciones or {}
    mapa_tajos_cortos = mapa_tajos_cortos or {}
    catalogo = catalogo or validar_revision.cargar_catalogo_tajos()

    ficha_antigua, cambios_antiguos = fichas.actualizar_desde_snapshot(
        copy.deepcopy(ficha_actual), snapshot_crudo, fecha,
        correcciones=correcciones,
        mapa_tajos_cortos=mapa_tajos_cortos,
    )
    revision = construir_revision_normalizada_desde_snapshot(
        obra, ficha_actual, snapshot_crudo, fecha, catalogo,
        correcciones=correcciones,
        mapa_tajos_cortos=mapa_tajos_cortos,
    )
    validacion = validar_revision.validar(revision, ficha_actual, catalogo)
    aplicacion = aplicar_revision.apply_revision(
        revision, ficha_actual, catalogo, dry_run=False)
    ficha_nueva = aplicacion.get('ficha_actualizada')
    estados_nuevos = ((ficha_nueva or ficha_actual).get('estados') or {})
    claves, diferencias = _diferencias_estados(
        ficha_antigua.get('estados') or {}, estados_nuevos)
    coincide = bool(
        validacion['aplicable'] and aplicacion.get('escrito')
        and ficha_nueva is not None and not diferencias)
    return {
        'coincide': coincide,
        'claves_comparadas': len(claves),
        'diferencias': diferencias,
        'ficha_antigua': ficha_antigua,
        'cambios_antiguos': cambios_antiguos,
        'ficha_nueva': ficha_nueva,
        'revision': revision,
        'validacion': validacion,
        'aplicacion': aplicacion,
    }


def actualizar_ficha_con_salvaguarda(
        obra, carpeta_abs, ficha_actual, snapshot_crudo, fecha,
        ficha_xlsx=None, materiales=None, documentos=None):
    """Hace el cutover de una obra; una divergencia no lanza ni guarda ficha."""
    correcciones = _correcciones_mas_recientes(carpeta_abs)
    mapa_tajos_cortos = _mapa_tajos_cortos(obra['id'])
    resultado = calcular_actualizacion_ficha_con_salvaguarda(
        obra, ficha_actual, snapshot_crudo, fecha,
        correcciones=correcciones,
        mapa_tajos_cortos=mapa_tajos_cortos,
    )

    if not resultado['coincide']:
        diferencias = resultado['diferencias']
        print(f"  [AVISO CUTOVER FICHA] {obra['nombre']}: el camino antiguo "
              f"y el motor comun difieren en {len(diferencias)} clave(s). "
              "La ficha de esta obra no se actualiza; el resto del proceso "
              "y las demas obras continuan.")
        for clave, antiguo, nuevo in diferencias:
            print(f'    {clave}: antiguo={_formatear_valor_paridad(antiguo)}; '
                  f'nuevo={_formatear_valor_paridad(nuevo)}')
        if not resultado['validacion']['aplicable']:
            for error in resultado['validacion']['errores']:
                print(f'    error del motor comun: {error}')
            for celda in resultado['validacion']['rechazadas']:
                print(f"    rechazada {celda.get('clave')!r}: "
                      f"{celda['motivo']}")
        return ficha_actual, False

    ficha_nueva = resultado['ficha_nueva']
    tocados = fichas.volcar_apartados(
        ficha_nueva, ficha_xlsx=ficha_xlsx, materiales=materiales,
        documentos=documentos)
    fichas.guardar(carpeta_abs, ficha_nueva)
    trazabilidad_revisiones.registrar_trazabilidad(
        resultado['aplicacion'],
        trazabilidad_revisiones.ruta_log_obra(carpeta_abs),
        revision=resultado['revision'],
        salvaguarda_coincidio=resultado['coincide'],
        celdas_comparadas=resultado['claves_comparadas'],
    )
    cambios = resultado['validacion']['resumen']['cambios']
    print(f"  [SALVAGUARDA FICHA] {obra['nombre']}: camino antiguo y "
          f"motor comun coinciden exactamente en "
          f"{resultado['claves_comparadas']} celdas; se guarda el resultado "
          "del motor comun.")
    if cambios:
        print(f'  [FICHA] celdas que cambian de estado: {cambios}')
    if tocados:
        print(f"  [FICHA] apartados actualizados: {', '.join(tocados)}")
    return ficha_nueva, True


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
        salida_cierre = os.path.join(salida_dir, 'cierre_expediente.json')

        try:
            # Se leen antes de tocar la ficha porque volcar_apartados() los
            # necesita, y porque el panel los usa igualmente para toda obra
            # (tenga ficha o no).
            materiales = lectores.leer_materiales(os.path.join(carpeta_abs, obra['materiales_rel']))
            ficha = lectores.leer_ficha(os.path.join(carpeta_abs, 'FICHA DE OBRA.xlsx'))
            documentos = lectores.listar_documentos(carpeta_abs, salida_dir)

            # ── INVERSION DEL FLUJO ──────────────────────────────────────
            # La ficha se alimenta del snapshot crudo y, a partir de aqui,
            # TODO lo demas (memoria, priorizador, KPIs, panel, informe) lee
            # el snapshot derivado de la ficha. Antes de esto, la ficha era un
            # subproducto que se escribia despues de calcular, asi que
            # corregirla no corregia los numeros publicados.
            # Una obra sin ficha no entra aqui y sigue igual que siempre.
            # OJO: `ficha` (arriba) es el xlsx recien leido; `ficha_actual` es
            # la ficha de obra JSON, la base de datos. No confundirlos.
            # Guarda de cobertura. Se mide sobre el historial CRUDO, antes de
            # que la ficha lo compense, porque el aviso interesa igual: dice
            # que la ultima hoja no cubre la obra entera. Ver el caso de
            # Obispo Orueta en tests/test_motor_informes.py.
            motivo_cobertura = motor_informes.cobertura_encogida(historial)

            ficha_actual = fichas.cargar(carpeta_abs)
            bloquear_guardado_ficha = False

            if motivo_cobertura:
                if ficha_actual:
                    print(f"  [AVISO COBERTURA] {obra['nombre']}: "
                          f"{motivo_cobertura}. La ficha lo compensa: los "
                          f"numeros salen de la base, no de esta hoja.")
                else:
                    print(f"  [AVISO COBERTURA] {obra['nombre']}: "
                          f"{motivo_cobertura}. ESTA OBRA NO TIENE FICHA: el "
                          f"porcentaje publicado sale solo de esta hoja. "
                          f"Sembrar su ficha_obra.json lo corrige.")

            if ficha_actual and historial:
                fecha_ultima, snapshot_crudo = historial[-1]
                ficha_actual, ficha_cutover_aplicada = (
                    actualizar_ficha_con_salvaguarda(
                        obra, carpeta_abs, ficha_actual, snapshot_crudo,
                        fecha_ultima, ficha_xlsx=ficha,
                        materiales=materiales, documentos=documentos,
                    )
                )
                bloquear_guardado_ficha = not ficha_cutover_aplicada

                snapshot_ficha = fichas.snapshot_desde_ficha(ficha_actual)
                if snapshot_ficha:
                    historial[-1] = (fecha_ultima, snapshot_ficha)
                    print(f"  [FICHA] el sistema lee de la ficha: "
                          f"{len(snapshot_ficha)} registros")
                else:
                    print(f"  [AVISO FICHA] {obra['nombre']}: la ficha no "
                          f"produce ningun registro. Se sigue con los datos "
                          f"del adaptador.")

            # Memoria de obra: acumula tajos de todas las revisiones
            tajos_memoria = mem.calcular_memoria(historial)
            mem_resumen = mem.guardar_memoria(salida_memoria, obra['nombre'], historial, tajos_memoria)
            print(f"  Memoria: {mem_resumen['total_tajos']} tajos "
                  f"({mem_resumen['activos']} activos, {mem_resumen['terminados']} terminados)")

            # La base es el estado. Una obra sin base no calcula: lo dice.
            if ficha_actual:
                prioridades = priorizador_trabajos.priorizar_ficha(
                    ficha_actual, obra=obra['nombre']
                )
                if not bloquear_guardado_ficha:
                    fichas.guardar(carpeta_abs, ficha_actual)
            else:
                prioridades = priorizador_trabajos.sin_base(obra['nombre'])
            priorizador_trabajos.escribir_json(prioridades, salida_prioridades)
            priorizador_trabajos.escribir_json({
                'version': prioridades.get('version'),
                'catalogo_version': prioridades.get('catalogo_version'),
                'obra': prioridades.get('obra'),
                'revision': prioridades.get('revision'),
                'generado': prioridades.get('generado'),
                'dudas_pendientes': prioridades.get('dudas_pendientes', []),
            }, salida_dudas)

            bat_abs = os.path.abspath(os.path.join(BASE_DIR, 'Actualizar_Obras.bat'))
            volver = os.path.relpath(os.path.join(OBRAS_ABIERTAS_DIR, 'index.html'), salida_dir).replace('\\', '/')
            cierre_datos, cierre_avisos = cierre_expediente.cargar(
                salida_cierre, obra=obra['nombre'])
            if not os.path.isfile(salida_cierre):
                cierre_expediente.guardar(salida_cierre, cierre_datos)
            res = panel_obra.generar_panel(
                obra=obra['nombre'], subtitulo=obra['subtitulo'], historial=historial,
                materiales=materiales, ficha=ficha, documentos=documentos,
                prioridades=prioridades, output_path=salida_html, volver_href=volver,
                tajos_memoria=tajos_memoria, mem_resumen=mem_resumen, bat_path=bat_abs,
                cierre=cierre_datos, cierre_avisos=cierre_avisos,
            )
        except Exception as e:
            print(f"  [ERROR] Fallo al generar el panel: {e}")
            print(f"  El panel anterior (si existe) no se sobreescribe. Continua con la siguiente obra.")
            continue

        print(f"  KPIs: {res['kpis']}")
        print(f"  Desviaciones de avance: {len(res['bloqueos'])} · "
              f"Docs: {res['n_docs']} · Sin cambios: {res['sin_cambios']}")
        print(f"  Prioridades: {prioridades['resumen']['listos']} listas · "
              f"{prioridades['resumen']['verificar']} a verificar · "
              f"{prioridades['resumen']['bloqueados']} bloqueadas")

        try:
            import generar_informe_ejecutivo
            # Usa exactamente el mismo historial que panel, memoria, KPI y
            # prioridades. Si existe ficha_obra.json, ``historial`` ya lleva
            # sus correcciones y no debe releerse el PDF crudo.
            generar_informe_ejecutivo.generar_para_obra(
                obra['nombre'],
                historial=historial,
                ficha=ficha_actual,
                prioridades=prioridades,
                cierre=cierre_datos,
                avisos_cierre=cierre_avisos,
            )
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
            # El índice y el portal deben mostrar bloqueos reales de la base,
            # no la antigua heurística estadística de plantas rezagadas.
            'sin_cambios': res['sin_cambios'],
            'n_bloqueos': prioridades['resumen']['bloqueados'],
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
