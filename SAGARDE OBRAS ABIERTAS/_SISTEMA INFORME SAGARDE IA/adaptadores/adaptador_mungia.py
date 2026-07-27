# -*- coding: utf-8 -*-
"""
ADAPTADOR - 2026 MUNGIA ACR NEINOR  (capa 1 - lectura, especifico de obra)
--------------------------------------------------------------------------
Sabe leer DOS formatos de hoja de revision para esta obra, ambos dentro de
la misma carpeta REVISIONES:

1) FORMATO ANTIGUO (REVISION ZR1 MUNGIA DDMMAAAA.docx): tabla unica dividida
   en bloques de 2 plantas en paralelo (izquierda/derecha), 2 edificios
   (ZR1.1 / ZR1.2) por bloque. Solo cubre ZR1.1 y ZR1.2 (no sabe leer ZR2.1).

2) FORMATO NUEVO (REVISION MUNGIA DDMMAAAA.pdf): la "hoja de revision de
   tajos" que genera la app de generacion de tajos, con tabla real (bordes)
   por pagina, un bloque de portal/plantas por tabla, y celdas en verde
   prerrellenas por la app (texto real "X"/"M") o en blanco para rellenar a
   mano en campo (marca de boli, sin texto real: pdfplumber la ve vacia).
   Cubre los 3 portales (p1=ZR1.1, p2=ZR1.2, p3=ZR2.1) y cualquier obra
   futura con esta misma plantilla (no es codigo especifico de una sola
   hoja, lee la tabla dinamicamente).

   Las celdas que son marca de boli (sin texto extraible) NO se adivinan:
   si existe un fichero hermano "<NOMBRE_PDF>.correcciones.json" con el
   mismo esquema {"p1__pb__mecanizado__A2": "X", ...}, se usa para rellenar
   esas celdas concretas (verificadas a mano, una vez, por Bixente/Claude
   mirando el PDF). Si no existe, esas celdas quedan en blanco (pendiente)
   igual que si no se hubiera marcado nada.

El historial final fusiona ambos formatos ordenados por fecha, para no
perder continuidad con las revisiones .docx ya existentes.

Requiere 'pdfplumber' (pip install pdfplumber --break-system-packages). Si
no esta instalado, las revisiones en PDF se ignoran con un aviso (no rompe
la lectura de las .docx).

Si el formato de esta obra cambia (nueva fase, tareas sustituidas, columnas
distintas), este es el UNICO fichero que hay que tocar. El motor_informes.py
no se toca nunca.

Devuelve un "historial": lista de (fecha_dd/mm/aaaa, snapshot) ordenada por
fecha, en el esquema estandar que espera motor_informes.py.
"""
import os
import sys
import re
import unicodedata
import docx

# lector_hoja_tajos_pdf.py vive en la carpeta padre (motor comun a todas las
# obras). Se asegura aqui el sys.path por si este adaptador se ejecuta suelto
# (python3 adaptador_mungia.py) en vez de vía generar_todos.py.
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
import lector_hoja_tajos_pdf as lector_pdf

CARPETA_OBRA = os.path.join(_BASE_DIR, os.pardir, "2026 MUNGIA ACR NEINOR")
CARPETA_OBRA = os.path.normpath(CARPETA_OBRA)
CARPETA_REVISIONES = os.path.join(CARPETA_OBRA, "REVISIONES")

LEFT_VALCOLS = {'ZR1.1': [2, 3, 4], 'ZR1.2': [6, 7, 8]}
RIGHT_VALCOLS = {'ZR1.1': [11, 12, 13], 'ZR1.2': [15, 16, 17]}

# --- Formato nuevo (PDF "hoja de revision de tajos") -----------------------
# alias corto -> nombre de tajo tal y como aparece impreso en la hoja (sin el
# prefijo SGD/EXT/COO ni la mini-etiqueta 'edif'/'zzcc' pegada al final).
TAJO_LABELS_PDF = [
    ('tabicado',    'Tabicado'),
    ('rozas',       'Rozas de timbres'),
    ('mont-elec',   'Montante electrica'),
    ('mont-telco',  'Montante de telecomunicaciones'),
    ('mont-sscc',   'Montante de servicios comunes'),
    ('tube-zzcc',   'Tubeado de zonas comunes'),
    ('cabl-zzcc',   'Cableado de zonas comunes'),
    ('suelo-rad',   'Suelo radiante'),
    ('suelo-rec',   'Suelo recrecido'),
    ('pladur-p',    'Perfilado de Pladur'),
    ('pladur-1c',   'Primeras caras de Pladur'),
    ('pladur-2c',   'Segundas caras de Pladur'),
    ('cuad-pres',   'Cuadros presentados'),
    ('tube-viv',    'Tubeado interior'),
    ('cabl-elec',   'Cableado electrico'),
    ('telecabl',    'Telecableado'),
    ('portero',     'Portero / videoportero'),
    ('termostatos', 'Termostatos'),
    ('doblar-caj',  'Doblar cajas'),
    ('embornado',   'Embornado electrico'),
    ('teleembor',   'Telembornado'),
    ('deriv-ind',   'Derivacion individual'),
    ('cuad-mec',    'Cuadro mecanizado'),
    ('ct-tec',      'Cuarto tecnico'),
    ('techos',      'Techos'),
    ('enchapado',   'Enchapado'),
    ('techos-zzcc', 'Techos ZZCC'),
    ('pint-1',      'Pintura primera mano'),
    ('pint-zzcc',   'Pintura ZZCC'),
    ('pint-2',      'Pintura 2 mano'),
    ('mecanizado',  'Mecanizado electrico'),
    ('telemec',     'Telemecanizado'),
    ('apliques',    'Apliques y enchufes de terraza'),
    ('casquillos',  'Casquillos y bombillas'),
    ('ilum-rell',   'Iluminacion de rellanos / ZZCC'),
    ('aguj-zzcc',   'Agujeros ilum ZZCC'),
    ('plac-tapas',  'Placas y tapas'),
    ('fachada',     'Fachada terminada'),

    # --- Redacciones largas que imprime el generador desde el 25/07/2026 -----
    # El generador de hojas paso a usar los nombres completos del catalogo y
    # estos 3 tajos dejaron de reconocerse: sus filas se leian como "tajo
    # omitido" y con ellas se descartaban en silencio las correcciones
    # manuales escritas sobre esas filas (41 en la revision del 27/07/2026).
    # Se conservan tambien las redacciones cortas por compatibilidad con las
    # hojas antiguas.
    ('aguj-zzcc',   'Agujeros de iluminacion en ZZCC'),
    ('techos-zzcc', 'Techos de zonas comunes'),
    ('pint-zzcc',   'Pintura de zonas comunes'),
    ('pint-2',      'Pintura segunda mano'),
]

# Mismo diccionario que adaptador_gernika.TAJO_NOMBRE: alias EXACTO del
# CATALOGO_TAJOS.json para que el priorizador clasifique cada tajo.
TAJO_NOMBRE_CATALOGO = {
    'tabicado': 'Tabicado', 'rozas': 'Rozas timbres', 'mont-elec': 'Montante electrica',
    'mont-telco': 'Montante teleco', 'mont-sscc': 'Montante sscc', 'tube-zzcc': 'Tubeado zzcc',
    'cabl-zzcc': 'Cableado zzcc', 'suelo-rad': 'Suelo radiante', 'suelo-rec': 'Suelo recrecido',
    'pladur-p': 'Perfilado de Pladur', 'pladur-1c': '1as caras Pladur', 'cuad-pres': 'Cuadros presentados',
    'tube-viv': 'Tubeado', 'cabl-elec': 'Cableado', 'telecabl': 'Telecableado', 'portero': 'Portero',
    'termostatos': 'Termostatos', 'pladur-2c': '2as caras Pladur', 'doblar-caj': 'Doblar cajas',
    'embornado': 'Embornado', 'teleembor': 'Telembornado', 'deriv-ind': 'Derivacion individual',
    'cuad-mec': 'Cuadro mecanizado', 'ct-tec': 'Cuarto tecnico', 'techos': 'Techos', 'enchapado': 'Enchapado',
    'techos-zzcc': 'Techos zzcc', 'pint-1': 'Pintura primera mano', 'pint-zzcc': 'Pintura zzcc',
    'pint-2': 'Pintura segunda mano', 'mecanizado': 'Mecanizado', 'telemec': 'Telemecanizado',
    'aguj-zzcc': 'Escaleras agujeros ilum', 'plac-tapas': 'Placas y tapas', 'fachada': 'Fachada terminada',
    'apliques': 'Apliques', 'casquillos': 'Casquillos Bombilla', 'ilum-rell': 'ILuminacion Rellanos',
}

PORTAL_NOMBRE_PDF = {'p1': 'ZR1.1', 'p2': 'ZR1.2', 'p3': 'ZR2.1'}
PLANTA_NOMBRE_PDF = {'pb': 'PB', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6'}


def _fold(s):
    s = (s or '').replace('\n', ' ').replace('ª', '').replace('º', '')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def _quitar_prefijo(s):
    return re.sub(r'^(EXT|SGD|COO)\s+', '', (s or '').strip(), flags=re.I)


_TAJO_NORM_PDF = {_fold(_quitar_prefijo(label)): codigo for codigo, label in TAJO_LABELS_PDF}


def _identificar_tajo_pdf(etiqueta):
    sin_prefijo = _quitar_prefijo(etiqueta)
    codigo = _TAJO_NORM_PDF.get(_fold(sin_prefijo))
    if codigo:
        return codigo
    # la mini-etiqueta 'edif'/'zzcc' puede venir pegada sin espacio al final
    sin_tag = re.sub(r'(edif|zzcc)$', '', sin_prefijo, flags=re.I)
    codigo = _TAJO_NORM_PDF.get(_fold(sin_tag))
    if codigo:
        return codigo
    # Ultimo recurso: el prefijo SGD/EXT/COO puede llegar partido por el
    # extractor y dejar suelta una letra ('D Iluminacion de rellanos / ZZCC').
    # Solo se intenta cuando los dos intentos anteriores han fallado, asi que
    # no puede romper ninguna equivalencia que ya funcionara.
    suelto = re.sub(r'^[A-Z]{1,3}\s+', '', sin_tag.strip())
    if suelto != sin_tag.strip():
        return _TAJO_NORM_PDF.get(_fold(suelto))
    return None


def _portal_id_pdf(texto):
    """Especifico de Mungia: sus portales se imprimen como 'ZR1.1'/'ZR1.2'/
    'ZR2.1' en la cabecera de cada tabla. Otra obra necesitara su propia
    version de esta funcion (ver receta en _MOTOR_SAGARDE/CLAUDE.md)."""
    m = re.search(r'ZR(\d)\.(\d)', texto or '')
    if not m:
        return None
    return {'1.1': 'p1', '1.2': 'p2', '2.1': 'p3'}.get(f'{m.group(1)}.{m.group(2)}')


def _parsear_pdf(ruta_pdf):
    """Delega la extraccion de tabla en el motor comun (lector_hoja_tajos_pdf)
    y aqui solo se traducen los ids internos (portal/planta/tajo) a los
    nombres de esta obra para el esquema estandar building/floor/task/unit."""
    registros_dict = lector_pdf.parsear_pdf(
        ruta_pdf,
        identificar_portal=_portal_id_pdf,
        identificar_tajo=_identificar_tajo_pdf,
        nombre_log='adaptador_mungia',
    )

    registros = []
    for (portal_id, planta_id, tajo_id, viv), valor in registros_dict.items():
        building = PORTAL_NOMBRE_PDF.get(portal_id)
        floor = PLANTA_NOMBRE_PDF.get(planta_id)
        task = TAJO_NOMBRE_CATALOGO.get(tajo_id)
        if not (building and floor and task):
            continue
        registros.append({
            'task': task, 'floor': floor, 'building': building,
            'unit': viv, 'status': valor if valor in ('X', 'M', '/') else '',
        })
    if not registros:
        print("  [adaptador_mungia] AVISO: PDF sin estados validos: {}".format(ruta_pdf))
    return registros


def _cargar_historial_pdf():
    archivos = lector_pdf.listar_revisiones_pdf(
        CARPETA_REVISIONES, contiene='MUNGIA', nombre_log='adaptador_mungia'
    )
    historial = []
    for clave, display, fn in archivos:
        registros = _parsear_pdf(os.path.join(CARPETA_REVISIONES, fn))
        if registros:
            historial.append((clave, display, registros))
    return historial


def _fecha_desde_nombre(fn):
    m = re.search(r'(\d{2})(\d{2})(\d{4})', fn)
    if not m:
        return None, None
    clave_orden = m.group(3) + m.group(2) + m.group(1)
    display = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return clave_orden, display


def _parsear_tabla(fn):
    d = docx.Document(fn)
    rows = [[c.text.strip() for c in r.cells] for r in d.tables[0].rows]
    n = len(rows)
    i = 0
    registros = []
    while i < n:
        row = rows[i]
        if len(row) > 2 and row[2] == 'ZR1.1':
            header_viv = rows[i + 1]
            j = i + 2
            while j < n and not (len(rows[j]) > 2 and rows[j][2] == 'ZR1.1'):
                r = rows[j]
                if len(r) < 18:
                    j += 1
                    continue
                task_l, floor_l = r[0].strip(), r[1].strip()
                task_r, floor_r = r[9].strip(), r[10].strip()
                if task_l and floor_l:
                    for edif, cols in LEFT_VALCOLS.items():
                        for col in cols:
                            viv = header_viv[col] if col < len(header_viv) else ''
                            if viv:
                                registros.append({
                                    'task': task_l, 'floor': floor_l,
                                    'building': edif, 'unit': viv, 'status': r[col],
                                })
                if task_r and floor_r:
                    for edif, cols in RIGHT_VALCOLS.items():
                        for col in cols:
                            viv = header_viv[col] if col < len(header_viv) else ''
                            if viv:
                                registros.append({
                                    'task': task_r, 'floor': floor_r,
                                    'building': edif, 'unit': viv, 'status': r[col],
                                })
                j += 1
            i = j
        else:
            i += 1
    return registros


# Orden de "fuerza" de un estado, de menos a mas avanzado.
_ORDEN_ESTADO_PB = {'': 0, '/': 1, 'M': 2, 'X': 3}


def _normalizar_zr12_pb(registros):
    """
    Normalizacion historica de ZR1.2 (confirmado con obra, 25/07/2026):

    - Planta PB se trackeaba antes como 3 locales separados (A, B, C) en
      las revisiones Word; la hoja PDF nueva los lleva juntos como una
      sola fila "PORTAL" (mismo espacio fisico, cambia solo la forma de
      registrarlo). Se funden aqui bajo "PORTAL" para que el priorizador
      vea continuidad en vez de "tajos que desaparecen sin terminar".
      Si habia estados distintos entre A/B/C para el mismo tajo, se usa
      el menos avanzado (no se infla progreso por la fusion).
    - Planta 1, vivienda "C": confirmado con obra que nunca tuvo datos
      reales (siempre a 0 / pendiente). Se descarta de raiz para no
      arrastrar una unidad fantasma que nunca existio.
    """
    resultado = []
    fusion_portal = {}
    for r in registros:
        if r['building'] == 'ZR1.2' and r['floor'] == '1' and r['unit'] == 'C':
            continue
        if r['building'] == 'ZR1.2' and r['floor'] == 'PB' and r['unit'] in ('A', 'B', 'C'):
            clave = r['task']
            actual = fusion_portal.get(clave)
            if actual is None or (_ORDEN_ESTADO_PB.get(r['status'], 0)
                                   < _ORDEN_ESTADO_PB.get(actual['status'], 0)):
                fusion_portal[clave] = {**r, 'unit': 'PORTAL'}
            continue
        resultado.append(r)
    resultado.extend(fusion_portal.values())
    return resultado


def cargar_historial():
    if not os.path.isdir(CARPETA_REVISIONES):
        raise FileNotFoundError(f"No se encuentra la carpeta de revisiones: {CARPETA_REVISIONES}")

    archivos = []
    for fn in os.listdir(CARPETA_REVISIONES):
        if fn.upper().startswith('REVISION ZR1') and fn.lower().endswith('.docx'):
            clave, display = _fecha_desde_nombre(fn)
            if clave:
                archivos.append((clave, display, fn))
    archivos.sort(key=lambda x: x[0])

    historial_docx = []
    for clave, display, fn in archivos:
        ruta = os.path.join(CARPETA_REVISIONES, fn)
        registros = _parsear_tabla(ruta)
        if registros:
            historial_docx.append((clave, display, registros))

    historial_pdf = _cargar_historial_pdf()
    if historial_pdf:
        print("  [adaptador_mungia] {} revision(es) en formato nuevo (PDF) encontradas.".format(len(historial_pdf)))

    # Fusion por fecha (clave_orden = AAAAMMDD). Si una misma fecha existe en
    # ambos formatos, gana el PDF (formato nuevo, mas completo: incluye ZR2.1).
    combinado = {}
    for clave, display, registros in historial_docx:
        combinado[clave] = (display, registros)
    for clave, display, registros in historial_pdf:
        combinado[clave] = (display, registros)

    historial = [
        (combinado[clave][0], _normalizar_zr12_pb(combinado[clave][1]))
        for clave in sorted(combinado)
    ]
    return historial


if __name__ == "__main__":
    h = cargar_historial()
    print(f"Revisiones cargadas: {len(h)}")
    print(f"Primera: {h[0][0]}  ({len(h[0][1])} registros)")
    print(f"Última:  {h[-1][0]}  ({len(h[-1][1])} registros)")
