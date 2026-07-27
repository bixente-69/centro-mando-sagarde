# -*- coding: utf-8 -*-
"""
ADAPTADOR - 2025 BILBAO OBISPO ORUETA  (capa 1 - lectura, especifico de obra)
------------------------------------------------------------------------------
Sabe leer el formato concreto de la hoja de revisiones de esta obra, que es
MUY DISTINTO al de Mungia:

  - Un UNICO edificio (no hay ZR1.1/ZR1.2). Direccion confirmada por
    documentacion oficial (OCA / planos de arquitectura): "Obispo Orueta, 2,
    Bilbao". No se ha encontrado ningun indicio de mas de un portal/bloque
    en las hojas de revision ni en los planos revisados, asi que se usa un
    unico valor fijo de 'building'.

  - Cada TABLA del .docx = UNA PLANTA COMPLETA (no un bloque de 2 plantas
    como en Mungia). La fila 0 de cada tabla trae, en una sola celda fusil
    (repetida en las 11 columnas), el nombre de planta + el instalador
    asignado, ej: "PLANTA 6  JOSE MARI", "PLANTA 2 DAYBER", "PLANTA BAJA"
    (sin instalador) o "PLANTA -1" (sin instalador). El numero de espacios
    entre planta e instalador varia (1 o 2), por eso se usa \s+ en el regex.

  - Dentro de cada tabla de planta hay, verificado a mano sobre varios
    ficheros (07/07, 24/09, 15/09...), SIEMPRE el mismo patron de 3
    "subsecciones" verticales, cada una con su propia fila de cabecera
    (etiqueta en mayusculas + codigos de columna/unidad propios):
        APARTAMENTO    -> columnas = nº de apartamento (1..10) o, en plantas
                           especiales, codigos tipo C1/C2/C3/OF (planta baja)
                           o V1/V2/V3/WC1/WC2/H1/H2/H3/GYM (planta -1).
        ZONAS COMUNES  -> columnas = nº de zona comun (1, 2...)
        MONTANTES      -> columnas = nº de montante (1, 2, 3...)
    La deteccion de estas cabeceras de subseccion NO esta hardcodeada a
    esos 3 nombres: se detecta heuristicamente cualquier fila cuya primera
    celda sea texto no vacio Y este integramente en mayusculas (regla que
    se ha verificado que NO da falsos positivos: ninguna tarea real de las
    revisiones inspeccionadas esta en mayusculas completas). Esto hace que
    el adaptador no se rompa si en una revision futura aparece una 4ª
    subseccion nueva (p.ej. "LOCALES" o "GARAJE").

  - Alguna fila de tarea bajo "MONTANTES" aparece con la celda de tarea en
    blanco pero con valores de estado reales en las columnas (un unico
    renglon "suelto" que representa el propio montante). En ese caso se usa
    el nombre de la subseccion ("Montantes") como nombre de tarea.

  - Simbolos de estado: se ha inspeccionado celda a celda la TOTALIDAD de
    los 12 ficheros validos (no solo una muestra). El grueso de las tareas
    solo usa 'X' (terminado), 'M' (>50%) y '' (vacio = no iniciado); no
    aparece ningun '/' en ningun fichero de esta obra (se deja mapeado en
    el codigo por si apareciera en el futuro).

    Se han encontrado, ademas, DOS EXCEPCIONES puntuales, sin ninguna hoja
    de leyenda en la carpeta de la obra que las explique (se ha buscado
    "gemini/leyenda/prompt/instruccion" y no existe nada equivalente al
    "gemini prompt tabla.docx" de Mungia). Se han mapeado por INFERENCIA
    propia, NO por confirmacion documental, y se avisa por consola cada
    vez que se cargan revisiones con estas casillas:

      * Tareas "Pintura Hab" y "Pintura Pasillos": usan una escala propia
        de "manos de pintura" con valores '1' y '2', y tambien 'X'. Se ha
        comprobado en el corpus completo que conviven '1', '2' y 'X' para
        la MISMA tarea en la MISMA revision (p.ej. 24/09/2025: Pintura Hab
        tiene 24x'1', 26x'2' y 1x'X'), lo que sugiere una progresion
        logica 1ª mano -> 2ª mano -> terminado. INFERENCIA aplicada:
        '1' -> '/' (iniciado <50%), '2' -> 'M' (avanzado >50%). Afecta a
        un volumen relevante de celdas (~113 en la ultima revision), por
        lo que dejarlas sin mapear (como "vacio") distorsionaria bastante
        el % de avance a la baja.
      * Tarea "Mecanismos WC": aparecen puntualmente (8 celdas en todo el
        corpus) los valores 'T' y 'C' conviviendo con 'X'. No hay indicio
        claro de cual va antes/despues, asi que INFERENCIA conservadora:
        ambos -> '/' (iniciado <50%), es decir "hay algo hecho pero no se
        da por completo" sin comprometerse a un % concreto.

    Cualquier OTRO simbolo no reconocido (fuera de estos dos casos ya
    documentados) se deja pasar tal cual en 'status' para no perder
    informacion, y se acumula en _SIMBOLOS_DESCONOCIDOS para avisar; el
    motor lo contabilizara como "vacio" al no coincidir con 'X'/'M'/'/'.

  - FECHAS DUPLICADAS: hay 3 fechas con mas de un fichero en la carpeta:
      07/07/2025: "REVISION 07072025.docx" y "REVISION 07072025_094112.docx"
          -> contenido IDENTICO celda a celda (comprobado). No hay conflicto
             real; se aplica igualmente la regla de "mtime mas reciente".
      28/07/2025: "REVISION 28072025_094112.docx" (mtime 28/07 10:40) y
          "REVISION 28072025 limpio.docx" (mtime 29/07 06:13)
          -> el contenido NO es identico: el fichero "_094112" todavia usa
             la lista de tareas ANTIGUA (rozado/tabiqueria: "Perfiles
             pladur", "Tubeado"...), igual que 07/07. El fichero "limpio"
             ya usa la lista de tareas NUEVA (acabados: "Pintura Hab",
             "Focos Hab"...), la misma que se mantiene en TODAS las
             revisiones posteriores (15/09, 24/09). Esto confirma que
             "limpio" es la version valida/definitiva de esa fecha (y
             coincide con la regla de mtime mas reciente).
      08/09/2025: "REVISION 08092025 .docx" (mtime 08/09) y
          "REVISION 08092025 -LAPTOP-63ISJ7TU.docx" (mtime 12/09, nombre
          tipico de copia en conflicto de OneDrive)
          -> el contenido es identico salvo en UNA celda: la cabecera de la
             ultima tabla (planta -1) dice erroneamente "PLANTA 1  AITOR"
             (duplicado de la tabla anterior) en el fichero sin sufijo,
             mientras que en el fichero "-LAPTOP" dice correctamente
             "PLANTA -1". Es una correccion de una errata de copia/pega,
             no una revision distinta. Se usa la version corregida (mtime
             mas reciente), consistente con la regla acordada.
    En los 3 casos se aplica la MISMA regla general y automatica: de entre
    los ficheros con la misma fecha en el nombre, se usa el de fecha de
    ULTIMA MODIFICACION (mtime) mas reciente en el sistema de ficheros.

  - Ficheros NO incluidos en el historial (y por que):
      * "26022025.docx": acta de visita de obra en prosa (0 tablas). Se
        carga sin error pero no aporta registros, así que se descarta
        automaticamente (igual que en Mungia, solo se anaden fechas con
        registros).
      * Revisiones que SOLO existen como PDF y no tienen .docx equivalente
        (26/06 SI tiene .docx, pero "REVISION SEMANA 31.pdf" ~29/07,
        "REVISION DF 30072025.pdf", "REVISION12092025.pdf",
        "REVISION 17092025 JUANMMA.pdf") no se leen: este adaptador, igual
        que el de Mungia, solo sabe parsear .docx con python-docx. Son un
        HUECO de datos pendiente de confirmar si se quiere incorporar en
        el futuro (requeriria OCR o extraccion de tablas desde PDF).
      * No se han encontrado revisiones .docx posteriores a 24/09/2025 en
        esta carpeta, pese a que la obra sigue activa mas alla de esa
        fecha (hay inspeccion OCA de 26/02/2026 y subsanaciones de
        14/04/2026 en la carpeta de la obra). Pendiente de confirmar si
        existen revisiones de campo mas recientes que no se han
        adjuntado/sincronizado en esta carpeta.

  - FORMATO NUEVO (27/07/2026): la revision "OBISPO ORUETA 2A FASE"
    llega como hoja PDF de la app de tajos (1 bloque, 1 portal, PB, viviendas
    A/B). Se lee con `lector_hoja_tajos_pdf.py` y su sidecar
    `<pdf>.correcciones.json`, transcrito y verificado visualmente porque las
    X son trazos graficos sin texto extraible. Esta hoja abre una segunda
    fase con alcance distinto al historial Word anterior: su snapshot tiene
    20 tajos x 2 viviendas y no se mezcla artificialmente con las ubicaciones
    de la primera fase.

Devuelve un "historial": lista de (fecha_dd/mm/aaaa, snapshot) ordenada por
fecha, en el esquema estandar que espera motor_informes.py.
"""
import os
import re
import sys
import unicodedata
import docx

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
import lector_hoja_tajos_pdf as lector_pdf

CARPETA_OBRA = os.path.normpath(os.path.join(
    _BASE_DIR, os.pardir, "2025 BILBAO OBISPO ORUETA"
))
CARPETA_REVISIONES = os.path.join(CARPETA_OBRA, "REVISIONES SAGARDE")

# Edificio unico confirmado (direccion: Obispo Orueta, 2 - Bilbao). No se ha
# detectado mas de un portal/bloque en las tablas de revision inspeccionadas.
BUILDING = "Obispo Orueta 2"

# Formato PDF nuevo: 20 tajos exactos de "OBISPO ORUETA 2A FASE".
TAJO_LABELS_PDF = [
    ('tabicado', 'Tabicado'),
    ('rozas', 'Rozas de timbres'),
    ('pladur-p', 'Perfilado de Pladur'),
    ('pladur-1c', '1as caras Pladur'),
    ('pladur-2c', '2as caras Pladur'),
    ('tube-viv', 'Tubeado vivienda'),
    ('cabl-elec', 'Cableado electrico'),
    ('telecabl', 'Telecableado'),
    ('doblar-caj', 'Doblar cajas'),
    ('embornado', 'Embornado electrico'),
    ('teleembor', 'Telembornado'),
    ('cuad-mec', 'Cuadro mecanizado'),
    ('techos-zzcc', 'Techos ZZCC'),
    ('techos', 'Techos'),
    ('enchapado', 'Enchapado'),
    ('pint-1', 'Pintura 1a mano'),
    ('pint-2', 'Pintura 2a mano'),
    ('mecanizado', 'Mecanizado electrico'),
    ('telemec', 'Telemecanizado'),
    ('plac-tapas', 'Placas y tapas'),
]

# Todos estos nombres resuelven contra CATALOGO_TAJOS.json.
TAJO_NOMBRE_CATALOGO = {
    'tabicado': 'Tabicado',
    'rozas': 'Rozas timbres',
    'pladur-p': 'Perfilado de Pladur',
    'pladur-1c': '1as caras Pladur',
    'pladur-2c': '2as caras Pladur',
    'tube-viv': 'Tubeado',
    'cabl-elec': 'Cableado',
    'telecabl': 'Telecableado',
    'doblar-caj': 'Doblar cajas',
    'embornado': 'Embornado',
    'teleembor': 'Telembornado',
    'cuad-mec': 'Cuadro mecanizado',
    'techos-zzcc': 'Techos zzcc',
    'techos': 'Techos',
    'enchapado': 'Enchapado',
    'pint-1': 'Pintura primera mano',
    'pint-2': 'Pintura segunda mano',
    'mecanizado': 'Mecanizado',
    'telemec': 'telemecanizado',
    'plac-tapas': 'Placas y tapas',
}

PORTAL_NOMBRE_PDF = {'p1': BUILDING}
PLANTA_NOMBRE_PDF = {'pb': 'PB'}

RE_FECHA = re.compile(r'(\d{2})(\d{2})(\d{4})')
RE_HEADER_PLANTA = re.compile(r'^PLANTA\s+(-?\d+|BAJA)\s*(.*)$', re.IGNORECASE)

_SIMBOLOS_DESCONOCIDOS = set()

# Ver docstring del modulo: dos excepciones de codificacion de estado
# detectadas e inferidas (sin leyenda documental que las confirme).
_TAREAS_PINTURA = {'Pintura Hab', 'Pintura Pasillos'}
_MAPEO_PINTURA = {'1': '/', '2': 'M'}
_TAREA_MECANISMOS_WC = 'Mecanismos WC'
_MAPEO_MECANISMOS_WC = {'T': '/', 'C': '/'}


def _fold(s):
    s = (s or '').replace('\n', ' ').replace('?', '').replace('?', '')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def _quitar_prefijo(s):
    return re.sub(r'^(EXT|SGD|COO)\s+', '', (s or '').strip(), flags=re.I)


_TAJO_NORM_PDF = {_fold(label): codigo for codigo, label in TAJO_LABELS_PDF}


def _identificar_tajo_pdf(etiqueta):
    sin_prefijo = _quitar_prefijo(etiqueta)
    codigo = _TAJO_NORM_PDF.get(_fold(sin_prefijo))
    if codigo:
        return codigo
    # La mini-etiqueta de ambito puede quedar pegada al final.
    sin_tag = re.sub(r'(edif|zzcc)$', '', sin_prefijo, flags=re.I)
    return _TAJO_NORM_PDF.get(_fold(sin_tag))


def _portal_id_pdf(texto):
    texto = (texto or '').upper()
    return 'p1' if 'BLOQUE 1' in texto and 'PORTAL 1' in texto else None


def _parsear_pdf(ruta_pdf):
    registros_dict = lector_pdf.parsear_pdf(
        ruta_pdf,
        identificar_portal=_portal_id_pdf,
        identificar_tajo=_identificar_tajo_pdf,
        nombre_log='adaptador_obisporueta',
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
            'fase': '2A FASE',
        })
    if not registros:
        print('  [adaptador_obisporueta] AVISO: PDF sin estados validos: {}'.format(ruta_pdf))
    return registros


def _cargar_historial_pdf():
    archivos = lector_pdf.listar_revisiones_pdf(
        CARPETA_REVISIONES, contiene='OBISPO', nombre_log='adaptador_obisporueta'
    )
    historial = []
    for clave, display, fn in archivos:
        registros = _parsear_pdf(os.path.join(CARPETA_REVISIONES, fn))
        if registros:
            historial.append((clave, display, registros))
    return historial


def _fecha_desde_nombre(fn):
    m = RE_FECHA.search(fn)
    if not m:
        return None, None
    clave_orden = m.group(3) + m.group(2) + m.group(1)
    display = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return clave_orden, display


def _normalizar_estado(tarea, v):
    v = (v or '').strip()
    if v in ('X', 'M', '/', ''):
        return v
    if tarea in _TAREAS_PINTURA and v in _MAPEO_PINTURA:
        return _MAPEO_PINTURA[v]
    if tarea == _TAREA_MECANISMOS_WC and v in _MAPEO_MECANISMOS_WC:
        return _MAPEO_MECANISMOS_WC[v]
    # Simbolo no reconocido y no cubierto por las inferencias documentadas:
    # se deja tal cual para no perder informacion, pero se avisa por
    # consola. El motor lo contara como "vacio" al no ser 'X'/'M'/'/'.
    _SIMBOLOS_DESCONOCIDOS.add((tarea, v))
    return v


def _floor_desde_header(texto_header):
    m = RE_HEADER_PLANTA.match(texto_header.strip())
    if not m:
        return None, ''
    codigo, instalador = m.group(1), m.group(2).strip()
    floor = 'PB' if codigo.upper() == 'BAJA' else codigo
    return floor, instalador


def _es_fila_subseccion(label):
    """Heuristica verificada a mano: las cabeceras de subseccion
    (APARTAMENTO / ZONAS COMUNES / MONTANTES, y cualquier otra que se
    añada en el futuro) estan siempre en mayusculas completas; ninguna
    tarea real observada lo esta."""
    return bool(label) and label == label.upper() and not label[0].isdigit()


def _parsear_tabla_planta(tabla):
    filas = [[c.text.strip() for c in r.cells] for r in tabla.rows]
    if not filas:
        return []
    floor, instalador = _floor_desde_header(filas[0][0])
    if floor is None:
        print(f"  [aviso] cabecera de tabla no reconocida, se omite: {filas[0][0]!r}")
        return []

    registros = []
    seccion_actual = None
    unidades_actuales = []

    for row in filas[1:]:
        label = row[0]
        resto = row[1:]

        if _es_fila_subseccion(label):
            seccion_actual = label.strip()
            unidades_actuales = resto
            continue

        vacio = (not label) and not any(resto)
        if vacio:
            continue

        tarea = label if label else (seccion_actual.title() if seccion_actual else 'Sin tarea')
        for j, val in enumerate(resto):
            unidad = unidades_actuales[j] if j < len(unidades_actuales) else ''
            if not unidad:
                continue
            seccion_prefijo = seccion_actual.title() if seccion_actual else ''
            registros.append({
                'task': tarea,
                'floor': floor,
                'building': BUILDING,
                'unit': f"{seccion_prefijo} {unidad}".strip(),
                'status': _normalizar_estado(tarea, val),
                'instalador': instalador,
            })
    return registros


def _parsear_documento(ruta):
    d = docx.Document(ruta)
    registros = []
    for tabla in d.tables:
        registros.extend(_parsear_tabla_planta(tabla))
    return registros


def cargar_historial():
    if not os.path.isdir(CARPETA_REVISIONES):
        raise FileNotFoundError(f"No se encuentra la carpeta de revisiones: {CARPETA_REVISIONES}")

    # 1) localizar todos los .docx con fecha valida en el nombre
    candidatos = {}  # clave_fecha_orden -> lista de (mtime, display, ruta)
    for fn in os.listdir(CARPETA_REVISIONES):
        if not fn.lower().endswith('.docx'):
            continue
        clave, display = _fecha_desde_nombre(fn)
        if not clave:
            continue
        ruta = os.path.join(CARPETA_REVISIONES, fn)
        mtime = os.path.getmtime(ruta)
        candidatos.setdefault(clave, []).append((mtime, display, ruta, fn))

    # 2) para fechas con mas de un fichero, quedarse con el de mtime mas
    #    reciente (ver cabecera del modulo para el analisis caso a caso)
    elegidos = []
    for clave, opciones in candidatos.items():
        opciones.sort(key=lambda o: o[0])  # por mtime ascendente
        mtime, display, ruta, fn = opciones[-1]
        if len(opciones) > 1:
            descartados = ", ".join(o[3] for o in opciones[:-1])
            print(f"  [fecha duplicada {display}] se usa '{fn}' (mtime mas reciente); "
                  f"descartado(s): {descartados}")
        elegidos.append((clave, display, ruta))

    elegidos.sort(key=lambda x: x[0])

    historial_docx = []
    for clave, display, ruta in elegidos:
        registros = _parsear_documento(ruta)
        if registros:
            historial_docx.append((clave, display, registros))
        else:
            print(f"  [sin tablas de datos] {os.path.basename(ruta)} ({display}) no aporta registros, se omite")

    if _SIMBOLOS_DESCONOCIDOS:
        print(f"  [aviso] simbolos de estado no reconocidos encontrados: {sorted(_SIMBOLOS_DESCONOCIDOS)}")

    historial_pdf = _cargar_historial_pdf()
    if historial_pdf:
        print("  [adaptador_obisporueta] {} revision(es) en formato nuevo (PDF) encontradas.".format(
            len(historial_pdf)
        ))

    # Fusion por fecha; ante coincidencia gana el PDF, formato oficial nuevo.
    combinado = {}
    for clave, display, registros in historial_docx:
        combinado[clave] = (display, registros)
    for clave, display, registros in historial_pdf:
        combinado[clave] = (display, registros)
    return [combinado[clave] for clave in sorted(combinado)]


if __name__ == "__main__":
    import sys

    h = cargar_historial()
    print(f"\nRevisiones cargadas: {len(h)}")
    if h:
        print(f"Primera: {h[0][0]}  ({len(h[0][1])} registros)")
        print(f"Última:  {h[-1][0]}  ({len(h[-1][1])} registros)")

        SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, SISTEMA_DIR)
        import motor_informes

        kpis = motor_informes.kpis_snapshot(h[-1][1])
        print(f"\nKPIs snapshot última revisión ({h[-1][0]}):")
        print(f"  {kpis}")

        bloqueos = motor_informes.detectar_bloqueos(h[-1][1])
        print(f"Bloqueos detectados: {len(bloqueos)}")
    else:
        print("No se ha cargado ninguna revisión con datos.")
