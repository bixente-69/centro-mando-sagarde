# -*- coding: utf-8 -*-
"""
ADAPTADOR - 2025 GERNIKA 32V  (capa 1 - lectura, especifico de obra)
----------------------------------------------------------------------
Lee las hojas de revision:
  1) JSON (revision_gernika_DDMMAAAA.json en INFORME SAGARDE IA) — export
     "estados" simple, formato original de esta obra.
  2) HTML (REVISION ... DDMMAAAA ....html en la carpeta REVISIONES) — export
     directo de la hoja interactiva de la "app de generación de tajos",
     decodificado con el motor genérico `lector_hoja_tajos_html.py` (mismo
     patrón que el soporte de PDF de Mungia/Bolueta: motor común + config
     delgada aquí). Añadido 25/07/2026 tras verificar con el usuario que
     ambos formatos describen las MISMAS 32 ubicaciones (sin drift) y que
     las diferencias de redacción de tajo son solo de vocabulario, no de
     continuidad real (ver CLAUDE.md, protocolo HTML).

Formato de datos en ambos:
  data-k / clave = "p1__pb__mecanizado__A" (JSON, ids cortos propios) o
                   "src_gernika_p1__src_gernika_p1_f1__tabicado__A" (HTML,
                   ids largos de crear_registro_revision/obras_revisiones.js)
  data-st / valor = "X" | "M" | "/" | "" | "N"

Los registros con estado "N" (no aplica) se descartan del historial porque
el motor no los sabe representar en KPIs.

Nota (JSON): si el usuario modifica estados en el navegador, esos cambios
quedan en localStorage (no en el fichero HTML) salvo que exporte JSON o
guarde el HTML con los data-st ya actualizados — el HTML de REVISIONES SÍ
captura el estado embebido en el momento de guardar.
"""
import os
import re
import sys

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
import lector_hoja_tajos_html as lector_html  # noqa: E402

CARPETA_OBRA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "2025 GERNIKA 32V"
)
CARPETA_IA = os.path.join(CARPETA_OBRA, "INFORME SAGARDE IA")

# Mapa tajoId -> alias exacto del CATALOGO_TAJOS.json
# (el priorizador normaliza acentos/case con _normalizar, pero el texto
#  debe coincidir con uno de los aliases del catalogo para ser clasificado)
TAJO_NOMBRE = {
    'tabicado':    'Tabicado',
    'rozas':       'Rozas timbres',
    'mont-elec':   'Montante electrica',
    'mont-telco':  'Montante teleco',
    'mont-sscc':   'Montante sscc',
    'tube-zzcc':   'Tubeado zzcc',
    'cabl-zzcc':   'Cableado zzcc',
    'suelo-rad':   'Suelo radiante',
    'suelo-rec':   'Suelo recrecido',
    'pladur-p':    'Perfilado de Pladur',
    'pladur-1c':   '1as caras Pladur',
    'cuad-pres':   'Cuadros presentados',
    'tube-viv':    'Tubeado',
    'cabl-elec':   'Cableado',
    'telecabl':    'Telecableado',
    'portero':     'Portero',
    'termostatos': 'Termostatos',
    'pladur-2c':   '2as caras Pladur',
    'doblar-caj':  'Doblar cajas',
    'embornado':   'Embornado',
    'teleembor':   'Telembornado',
    'deriv-ind':   'Derivacion individual',
    'cuad-mec':    'Cuadro mecanizado',
    'ct-tec':      'Cuarto tecnico',
    'techos':      'Techos',
    'enchapado':   'Enchapado',
    'pint-1':      'Pintura primera mano',
    'mecanizado':  'Mecanizado',
    'telemec':     'Telemecanizado',
    'aguj-zzcc':   'Escaleras agujeros ilum',
    'pint-2':      'Pintura segunda mano',
    'plac-tapas':  'Placas y tapas',
    'fachada':     'Fachada terminada',
    'apliques':    'Apliques',
    'casquillos':  'Casquillos Bombilla',
    'ilum-rell':   'ILuminacion Rellanos',
    # Añadidos 25/07/2026 al dar de alta el HTML de la app de generación de
    # tajos (ver CARPETA_REVISIONES/TAREA_ID_A_NOMBRE_HTML más abajo): estos
    # dos códigos cortos no existían antes en el vocabulario de Gernika.
    'techos-zzcc': 'Techos zzcc',
    'pint-zzcc':   'Pintura zzcc',
}

PORTAL_NOMBRE = {'p1': 'PORTAL 1', 'p2': 'PORTAL 2'}
PLANTA_NOMBRE = {'pb': 'PB', '1': '1', '2': '2', '3': '3'}

# --- Soporte HTML (hoja interactiva de la app de generación de tajos) ---
CARPETA_REVISIONES = os.path.join(CARPETA_OBRA, "REVISIONES")

# ids largos que usa crear_registro_revision()/obras_revisiones.js para esta
# obra (2 portales, 4 plantas cada uno, orden natural con PB primero).
PORTAL_NOMBRE_HTML = {'src_gernika_p1': 'PORTAL 1', 'src_gernika_p2': 'PORTAL 2'}
PLANTA_NOMBRE_HTML = {
    'src_gernika_p1_f1': 'PB', 'src_gernika_p1_f2': '1',
    'src_gernika_p1_f3': '2', 'src_gernika_p1_f4': '3',
    'src_gernika_p2_f1': 'PB', 'src_gernika_p2_f2': '1',
    'src_gernika_p2_f3': '2', 'src_gernika_p2_f4': '3',
}

# tarea_id (id de catálogo o código corto) -> nombre de tarea, usando SIEMPRE
# el mismo texto que ya usa TAJO_NOMBRE/el historial de Gernika (verificado
# uno a uno contra priorizador_trabajos.Catalogo el 25/07/2026 para que no
# se generen "dudas pendientes" por redacción distinta de un mismo tajo).
TAREA_ID_A_NOMBRE_HTML = {
    'agujeros_iluminacion_zzcc': 'Escaleras agujeros ilum',
    'apliques': 'Apliques',
    'cableado': 'Cableado',
    'cableado_zzcc': 'Cableado zzcc',
    'casquillos_bombillas': 'Casquillos Bombilla',
    'cuadro_mecanizado': 'Cuadro mecanizado',
    'cuadros_presentados': 'Cuadros presentados',
    'cuarto_tecnico': 'Cuarto tecnico',
    'derivacion_individual': 'Derivacion individual',
    'doblar_cajas': 'Doblar cajas',
    'embornado': 'Embornado',
    'enchapado': 'Enchapado',
    'fachada_terminada': 'Fachada terminada',
    'iluminacion_rellanos': 'ILuminacion Rellanos',
    'mecanizado': 'Mecanizado',
    'montante_electrica': 'Montante electrica',
    'montante_sscc': 'Montante sscc',
    'montante_teleco': 'Montante teleco',
    'perfilado_pladur': 'Perfilado de Pladur',
    'pint-zzcc': 'Pintura zzcc',
    'pintura_primera': 'Pintura primera mano',
    'pintura_segunda': 'Pintura segunda mano',
    'placas_tapas': 'Placas y tapas',
    'portero': 'Portero',
    'primera_cara_pladur': '1as caras Pladur',
    'rozas_timbres': 'Rozas timbres',
    'segunda_cara_pladur': '2as caras Pladur',
    'suelo-rad': 'Suelo radiante',
    'suelo_recrecido': 'Suelo recrecido',
    'tabicado': 'Tabicado',
    'techos': 'Techos',
    'techos-zzcc': 'Techos zzcc',
    'telecableado': 'Telecableado',
    'telembornado': 'Telembornado',
    'telemecanizado': 'Telemecanizado',
    'termostatos': 'Termostatos',
    'tubeado': 'Tubeado',
    'tubeado_zzcc': 'Tubeado zzcc',
}


def _cargar_historial_html():
    return lector_html.listar_revisiones_html(
        CARPETA_REVISIONES,
        portal_nombre=PORTAL_NOMBRE_HTML,
        planta_nombre=PLANTA_NOMBRE_HTML,
        tarea_id_a_nombre=TAREA_ID_A_NOMBRE_HTML,
        nombre_log='adaptador_gernika',
    )


def _fecha_desde_nombre(fn):
    """Extrae DDMMAAAA del nombre y devuelve (clave_orden, display)."""
    m = re.search(r'(\d{2})(\d{2})(\d{4})', fn)
    if not m:
        return None, None
    dd, mm, aaaa = m.group(1), m.group(2), m.group(3)
    try:
        d, mo, y = int(dd), int(mm), int(aaaa)
    except ValueError:
        return None, None
    if not (1 <= d <= 31 and 1 <= mo <= 12 and 2000 <= y <= 2100):
        return None, None
    return aaaa + mm + dd, "{}/{}/{}".format(dd, mm, aaaa)


def _parsear_json(ruta_json):
    """
    Lee el JSON de estados (revision_gernika_DDMMAAAA.json) y devuelve registros.
    El JSON tiene la forma: {"fecha": "DD/MM/AAAA", "estados": {"p1__pb__mecanizado__A": "X", ...}}
    """
    import json
    with open(ruta_json, encoding='utf-8') as f:
        data = json.load(f)
    estados = data.get('estados', {})
    registros = []
    for key, st in estados.items():
        _procesar_celda(key, st, registros)
    if not registros:
        print("  [adaptador_gernika] AVISO: JSON sin estados validos: {}".format(ruta_json))
    return registros


def _procesar_celda(key, st, registros):
    """Parsea 'p1__pb__mecanizado__A' y anade registro si es valido."""
    if st == 'N':
        return
    partes = key.split('__')
    if len(partes) != 4:
        return
    portal_id, planta_id, tajo_id, viv = partes
    building = PORTAL_NOMBRE.get(portal_id)
    floor = PLANTA_NOMBRE.get(planta_id)
    task = TAJO_NOMBRE.get(tajo_id)
    if not (building and floor and task):
        return
    status = st if st in ('X', 'M', '/') else ''
    registros.append({
        'task':     task,
        'floor':    floor,
        'building': building,
        'unit':     viv,
        'status':   status,
    })


def cargar_historial():
    """
    Devuelve historial = [(fecha_display, [registros]), ...] ordenado por fecha.
    Fusiona dos orígenes por fecha (clave DDMMAAAA):
      - revision_gernika_DDMMAAAA.json en INFORME SAGARDE IA (formato original)
      - REVISION ... DDMMAAAA ....html en REVISIONES (hoja interactiva,
        añadido 25/07/2026). Si una misma fecha existe en ambos formatos,
        gana el HTML por ser la exportación más completa/reciente de la app.
    """
    if not os.path.isdir(CARPETA_IA):
        raise FileNotFoundError("No se encuentra la carpeta: {}".format(CARPETA_IA))

    archivos = []
    for fn in os.listdir(CARPETA_IA):
        if fn.lower().startswith('revision_gernika_') and fn.lower().endswith('.json'):
            clave, display = _fecha_desde_nombre(fn)
            if clave:
                archivos.append((clave, display, fn))
            else:
                print("[adaptador_gernika] AVISO: '{}' sin fecha DDMMAAAA valida, ignorado.".format(fn))

    archivos.sort(key=lambda x: x[0])

    combinado = {}
    for clave, display, fn in archivos:
        ruta = os.path.join(CARPETA_IA, fn)
        registros = _parsear_json(ruta)
        if registros:
            combinado[clave] = (display, registros)
            print("  [gernika] {}: {} registros de '{}'".format(display, len(registros), fn))
        else:
            print("  [gernika] {}: sin registros en '{}', ignorado.".format(display, fn))

    for display, registros in _cargar_historial_html():
        m = re.search(r'(\d{2})/(\d{2})/(\d{4})', display)
        clave = m.group(3) + m.group(2) + m.group(1)
        if clave in combinado:
            print("  [gernika] {}: sustituida version JSON por HTML ({} registros).".format(
                display, len(registros)))
        combinado[clave] = (display, registros)

    if not combinado:
        print("[adaptador_gernika] AVISO: No se encontraron revisiones JSON ni HTML validas.")
        return []

    return [combinado[clave] for clave in sorted(combinado)]


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import motor_informes as motor

    h = cargar_historial()
    print("\nRevisiones cargadas: {}".format(len(h)))
    if h:
        print("Unica: {}  ({} registros)".format(h[-1][0], len(h[-1][1])))
        kpis = motor.kpis_snapshot(h[-1][1])
        print("KPIs ({}): {}".format(h[-1][0], kpis))
