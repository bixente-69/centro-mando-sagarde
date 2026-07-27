# -*- coding: utf-8 -*-
"""
ADAPTADOR - 2026 BOLUETA ACR  (capa 1 - lectura, especifico de obra)
--------------------------------------------------------------------------
Formato de esta obra (verificado con python-docx sobre el fichero mas
antiguo y el mas reciente, e inspeccion cruzada de los 7 ficheros de la
carpeta REVISIONES): edificio UNICO (1 portal, segun "Proyecto teleco
Bolueta 92.pdf": "Nº Portales: 1", "Nº Plantas: B+23"), sin division en
ZR1.1/ZR1.2 como en Mungia. Cada hoja de revision Word contiene 6 tablas
de 68 filas x 18 columnas. Cada tabla agrupa 2 "bloques" de 2 plantas en
paralelo (izquierda = planta N, derecha = planta N+1); cada bloque
empieza con una fila de cabecera (unidades A/B/C/D) seguida de ~31 filas
de tareas. Las 6 tablas del documento cubren, en conjunto, las plantas
PB, 1, 2 ... 23 (24 niveles), lo que coincide exactamente con "B+23" del
proyecto ICT. Comprobado con un barrido completo de los 7 ficheros x 6
tablas (42 tablas): la cabecera de unidades es SIEMPRE ('A','B','C','D')
en ambos bloques (izquierdo y derecho) -- no cambia de una planta a otra
como si ocurre en Mungia -- y las columnas separadoras (6,7,8,15,16,17)
estan siempre vacias (no hay una 5ª unidad oculta ni edificios extra).

Valores de estado encontrados en las celdas de datos: EXACTAMENTE 'X',
'M', '/' y '' (vacio) -- iguales al esquema estandar que espera
motor_informes.py, por lo que NO hace falta remapeo de simbolos. Esto se
confirmo contando de forma exhaustiva todos los valores no vacios de las
columnas de datos (2,3,4,5,11,12,13,14) en el fichero mas antiguo y en el
mas reciente: unicos valores presentes fueron X/M//''. No existe en la
carpeta de Bolueta ningun documento de "leyenda" (no hay equivalente al
"gemini prompt tabla.docx" de Mungia); el documento homonimo de Mungia SI
describe ese mismo diccionario X="100%", M=">50%", /="<50%", vacio="no
iniciado" como convencion usada por el encargado en varias obras, lo cual
es coherente con lo observado aqui pero se trata de una inferencia
razonada a partir de los datos + un documento de OTRA obra, no de una
leyenda propia de Bolueta.

INCIDENCIAS DE FECHA DETECTADAS EN LA CARPETA (no se resuelven de forma
oculta; se registran aqui y se avisan por consola al cargar el historial):

  1) "REVISION BOLUETA 00002026.docx": el nombre no contiene una fecha
     DD/MM/AAAA valida (dia=00, mes=00). Se descarta por validacion de
     rango (dia 1-31, mes 1-12) -- NO se inventa una fecha para este
     fichero. Verificado ademas que su tabla es BYTE A BYTE IDENTICA a la
     de "REVISION BOLUETA 10042026.docx" (408/408 filas de datos iguales,
     comparacion exhaustiva), y que sus metadatos internos
     (docx.core_properties.created) marcan 2026-04-10 -- coincide con la
     fecha que debio llevar el nombre. Al excluir "00002026" no se pierde
     ningun dato: la revision del 10/04/2026 queda igualmente
     representada por el otro fichero (el que si tiene nombre valido).

  2) Contradiccion fecha-de-nombre vs fecha-de-cabecera-interna: el
     parrafo de cabecera de pagina dentro de cada .docx (formato
     "BOLUETA  DD/MM/AAAA   SEMANA : NN") NO siempre coincide con la
     fecha codificada en el nombre de fichero:
       - "10042026.docx" -> cabecera interna dice "21/04/2026", pero su
         contenido de tabla es identico al de "00002026" (fechado 10/04
         por metadatos). Es decir, este fichero es, en la practica, una
         copia de la revision del 10/04 a la que se le cambio la fecha de
         cabecera sin rellenar datos nuevos.
       - "11052026.docx" -> cabecera interna dice "12/05/2026" (+1 dia).
       - "26052026.docx" -> cabecera interna dice "27/05/2026" (+1 dia).
       - "01062026.docx" -> cabecera interna dice "14/07/2026" (!), y la
         fecha de modificacion del fichero en disco TAMBIEN es 14/07/2026,
         lo que sugiere fuertemente que la fecha REAL de esta revision (la
         mas reciente de toda la obra) es 14/07/2026 y no 01/06/2026 como
         indica su nombre.
     Este adaptador usa DELIBERADAMENTE la fecha del NOMBRE DE FICHERO
     (mismo criterio que adaptador_mungia.py), para no introducir un
     criterio de fechado distinto al del resto del sistema y para evitar
     colisiones de fecha (usar la cabecera interna de "10042026.docx"
     duplicaria la fecha 21/04/2026, que ya tiene su propia revision real
     y distinta en "21042026.docx", con mas avance). Esto es una decision
     explicita, no un descuido: si se prefiere usar la fecha de cabecera,
     hay que decidirlo con el encargado y renombrar los ficheros en
     origen. Se recomienda, en particular, revisar y renombrar
     "REVISION BOLUETA 01062026.docx" a su fecha real aparente
     (14/07/2026), porque con el nombre actual el panel puede mostrar una
     "ultima revision" que parece desactualizada ~6 semanas cuando no lo
     esta.

FORMATO NUEVO (25/07/2026): además del Word de arriba, esta obra empezó a
recibir también la "hoja de revisión de tajos" en PDF que genera la app de
generación de tajos, igual que Mungia (mismo layout: 1 tabla por página con
banner "BOLUETA · PORTAL ÚNICO · PLANTAS X · Y"). Se lee con el motor
genérico `lector_hoja_tajos_pdf.py` — ver `_portal_id_pdf`/
`_identificar_tajo_pdf`/`TAJO_LABELS_PDF`/`TAJO_NOMBRE_CATALOGO` más abajo.

IMPORTANTE — catálogo de tajos verificado contra el historial YA EXISTENTE
de esta obra (25/07/2026), no copiado a ciegas del de Mungia, aunque la
plantilla de la app es la misma: se comprobó, con `catalogo.resolver()` de
priorizador_trabajos.py, que cada nombre de tajo usado aquí resuelve a un
id de CATALOGO_TAJOS.json real (nunca "sin_clasificar"), y se usó el
nombre EXACTO que ya aparece en el historial Word de Bolueta cuando existía
uno equivalente (para no romper la continuidad de memoria_obra.py). Casos
notables:
  - El Word antiguo trackeaba pintura como una sola tarea "Pintado"; la
    hoja PDF nueva la separa en "Pintura primera mano" / "Pintura segunda
    mano" / "Pintura zzcc". Esto NO genera dudas falsas: CATALOGO_TAJOS.json
    ya declara "Pintado" como alias de "pintura_primera", así que el
    priorizador (que resuelve por id de catálogo, no por texto literal) ve
    continuidad real. "Pintura segunda mano"/"Pintura zzcc" son tajos
    nuevos que Bolueta no trackeaba antes (progreso empieza desde cero, no
    es un error).
  - "Escaleras agujeros ilum" (ya en el historial) es el mismo tajo que el
    PDF imprime como "Agujeros de iluminación en ZZCC" — mismo id de
    catálogo, se usa el nombre antiguo para mantener continuidad.
  - Casquillos y bombillas, Placas y tapas, Cuarto técnico, Fachada
    terminada e Ilum. rellanos/ZZCC son tajos que el Word antiguo nunca
    cubría — aparecen como nuevos con este PDF, no como "desaparecidos".

Si el formato de esta obra cambia, este es el UNICO fichero que hay que
tocar. El motor_informes.py no se toca nunca.
"""
import os
import sys
import re
import unicodedata
import docx

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
import lector_hoja_tajos_pdf as lector_pdf

CARPETA_OBRA = os.path.normpath(os.path.join(_BASE_DIR, os.pardir, "2026 BOLUETA ACR"))
CARPETA_REVISIONES = os.path.join(CARPETA_OBRA, "REVISIONES")

# Unico edificio/portal de esta obra (no hay division tipo ZR1.1/ZR1.2 como
# en Mungia: el "Proyecto teleco Bolueta 92.pdf" indica explicitamente
# "Nº Portales: 1"). Se usa una etiqueta fija de edificio para que el motor
# (que agrupa por 'building') tenga una clave estable.
BUILDING = "BOLUETA"

# --- Formato nuevo (PDF "hoja de revision de tajos") -----------------------
# alias corto -> nombre de tajo tal y como aparece impreso en la hoja (sin el
# prefijo SGD/EXT/COO ni la mini-etiqueta 'edif'/'zzcc' pegada al final).
TAJO_LABELS_PDF = [
    ('tabicado',    'Tabicado'),
    ('rozas',       'Rozas de timbres'),
    ('mont-elec',   'Montante eléctrica'),
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
    ('cabl-elec',   'Cableado eléctrico'),
    ('telecabl',    'Telecableado'),
    ('portero',     'Portero / videoportero'),
    ('termostatos', 'Termostatos'),
    ('doblar-caj',  'Doblar cajas'),
    ('embornado',   'Embornado eléctrico'),
    ('teleembor',   'Telembornado'),
    ('deriv-ind',   'Derivación individual'),
    ('cuad-mec',    'Cuadro mecanizado'),
    ('ct-tec',      'Cuarto técnico'),
    ('techos',      'Techos'),
    ('enchapado',   'Enchapado'),
    ('techos-zzcc', 'Techos ZZCC'),
    ('pint-1',      'Pintura — primera mano'),
    ('pint-zzcc',   'Pintura ZZCC'),
    ('pint-2',      'Pintura — 2ª mano'),
    ('mecanizado',  'Mecanizado eléctrico'),
    ('telemec',     'Telemecanizado'),
    ('apliques',    'Apliques y enchufes de terraza'),
    ('casquillos',  'Casquillos y bombillas'),
    # Estos 2 tienen wording propio de Bolueta, distinto al de Mungia:
    ('aguj-zzcc',   'Agujeros de iluminación en ZZCC'),
    ('ilum-rell',   'Ilum. rellanos / ZZCC'),
    ('plac-tapas',  'Placas y tapas'),
    ('fachada',     'Fachada terminada'),
]

# alias corto -> nombre EXACTO usado para 'task' (verificado con
# catalogo.resolver(): ninguno cae en "sin_clasificar"). Se usa el nombre ya
# presente en el historial Word de Bolueta cuando existía uno equivalente,
# para no romper la continuidad de memoria_obra.py; si no existía, se usa el
# mismo nombre ya validado en adaptador_mungia.py para ese mismo id.
TAJO_NOMBRE_CATALOGO = {
    'tabicado': 'Tabicado', 'rozas': 'Rozas timbres', 'mont-elec': 'Montante eléctrica',
    'mont-telco': 'Montante teleco', 'mont-sscc': 'Montante sscc', 'tube-zzcc': 'Tubeado zzcc',
    'cabl-zzcc': 'Cableado zzcc', 'suelo-rad': 'Suelo radiante', 'suelo-rec': 'Suelo recrecido',
    'pladur-p': 'Perfilado de Pladur', 'pladur-1c': '1as caras Pladur', 'pladur-2c': '2as caras Pladur',
    'cuad-pres': 'Cuadros presentados', 'tube-viv': 'Tubeado', 'cabl-elec': 'Cableado',
    'telecabl': 'Telecableado', 'portero': 'Portero', 'termostatos': 'Termostatos',
    'doblar-caj': 'Doblar cajas', 'embornado': 'Embornado', 'teleembor': 'Telembornado',
    'deriv-ind': 'Derivación individual', 'cuad-mec': 'Cuadro mecanizado', 'ct-tec': 'Cuarto técnico',
    'techos': 'Techos', 'enchapado': 'Enchapado', 'techos-zzcc': 'Techos zzcc',
    'pint-1': 'Pintura primera mano', 'pint-zzcc': 'Pintura zzcc', 'pint-2': 'Pintura segunda mano',
    'mecanizado': 'Mecanizado', 'telemec': 'telemecanizado', 'apliques': 'Apliques',
    'casquillos': 'Casquillos Bombilla', 'aguj-zzcc': 'Escaleras agujeros ilum',
    'ilum-rell': 'ILuminacion Rellanos', 'plac-tapas': 'Placas y tapas', 'fachada': 'Fachada terminada',
}

PORTAL_NOMBRE_PDF = {'p1': BUILDING}
PLANTA_NOMBRE_PDF = {'pb': 'PB'}
PLANTA_NOMBRE_PDF.update({str(i): str(i) for i in range(1, 24)})


def _fold(s):
    s = (s or '').replace('\n', ' ').replace('ª', '').replace('º', '')
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
    sin_tag = re.sub(r'(edif|zzcc)$', '', sin_prefijo, flags=re.I)
    return _TAJO_NORM_PDF.get(_fold(sin_tag))


def _portal_id_pdf(texto):
    """Unico portal de esta obra: cualquier banner con 'BOLUETA' es 'p1'."""
    return 'p1' if 'BOLUETA' in (texto or '').upper() else None


def _parsear_pdf(ruta_pdf):
    registros_dict = lector_pdf.parsear_pdf(
        ruta_pdf,
        identificar_portal=_portal_id_pdf,
        identificar_tajo=_identificar_tajo_pdf,
        nombre_log='adaptador_bolueta',
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
        print("  [adaptador_bolueta] AVISO: PDF sin estados validos: {}".format(ruta_pdf))
    return registros


def _cargar_historial_pdf():
    archivos = lector_pdf.listar_revisiones_pdf(
        CARPETA_REVISIONES, contiene='BOLUETA', nombre_log='adaptador_bolueta'
    )
    historial = []
    for clave, display, fn in archivos:
        registros = _parsear_pdf(os.path.join(CARPETA_REVISIONES, fn))
        if registros:
            historial.append((clave, display, registros))
    return historial


def _fecha_desde_nombre(fn):
    """Extrae DDMMAAAA del nombre de fichero y valida que sea una fecha
    real (dia 1-31, mes 1-12, año 2000-2100). Devuelve (None, None) si no
    hay 8 digitos o si no es una fecha valida -- p.ej. "00002026" (dia=00,
    mes=00) se descarta aqui, sin inventar una fecha alternativa."""
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
    clave_orden = aaaa + mm + dd
    display = f"{dd}/{mm}/{aaaa}"
    return clave_orden, display


def _parsear_tabla(ruta):
    """Recorre las 6 tablas del documento. Dentro de cada tabla, detecta
    bloques delimitados por una fila de cabecera (unidades A/B/C/D en las
    columnas 2-5 izquierda y 11-14 derecha, con columnas 0 y 1 vacias) y
    lee las filas de tareas siguientes hasta la proxima cabecera o el fin
    de la tabla. La cabecera se relee dinamicamente en cada bloque (no se
    asume fija) por si alguna planta futura tuviera unidades distintas."""
    d = docx.Document(ruta)
    registros = []
    for tabla in d.tables:
        rows = [[c.text.strip() for c in r.cells] for r in tabla.rows]
        n = len(rows)
        i = 0
        while i < n:
            row = rows[i]
            es_cabecera = len(row) >= 15 and row[0] == '' and row[1] == '' and row[2] != ''
            if not es_cabecera:
                i += 1
                continue
            header = row
            j = i + 1
            while j < n:
                r = rows[j]
                if len(r) < 15:
                    j += 1
                    continue
                # Fin de bloque: aparece la siguiente fila de cabecera.
                if r[0] == '' and r[1] == '' and r[2] != '':
                    break
                task_l, floor_l = r[0].strip(), r[1].strip()
                task_r, floor_r = r[9].strip(), r[10].strip()
                if task_l and floor_l:
                    for col in (2, 3, 4, 5):
                        unidad = header[col] if col < len(header) else ''
                        if unidad:
                            registros.append({
                                'task': task_l, 'floor': floor_l,
                                'building': BUILDING, 'unit': unidad,
                                'status': r[col] if col < len(r) else '',
                            })
                if task_r and floor_r:
                    for col in (11, 12, 13, 14):
                        unidad = header[col] if col < len(header) else ''
                        if unidad:
                            registros.append({
                                'task': task_r, 'floor': floor_r,
                                'building': BUILDING, 'unit': unidad,
                                'status': r[col] if col < len(r) else '',
                            })
                j += 1
            i = j
    return registros


def cargar_historial():
    if not os.path.isdir(CARPETA_REVISIONES):
        raise FileNotFoundError(f"No se encuentra la carpeta de revisiones: {CARPETA_REVISIONES}")

    archivos = []
    excluidos = []
    for fn in os.listdir(CARPETA_REVISIONES):
        if fn.upper().startswith('REVISION BOLUETA') and fn.lower().endswith('.docx'):
            clave, display = _fecha_desde_nombre(fn)
            if clave:
                archivos.append((clave, display, fn))
            else:
                excluidos.append(fn)
    archivos.sort(key=lambda x: x[0])

    if excluidos:
        print(f"[adaptador_bolueta] AVISO: {len(excluidos)} fichero(s) excluido(s) del historial "
              f"por no tener una fecha DD/MM/AAAA valida en el nombre (no se inventa fecha): {excluidos}")

    historial_docx = []
    for clave, display, fn in archivos:
        ruta = os.path.join(CARPETA_REVISIONES, fn)
        registros = _parsear_tabla(ruta)
        if registros:
            historial_docx.append((clave, display, registros))

    historial_pdf = _cargar_historial_pdf()
    if historial_pdf:
        print("  [adaptador_bolueta] {} revision(es) en formato nuevo (PDF) encontradas.".format(len(historial_pdf)))

    # Fusion por fecha (clave_orden = AAAAMMDD). Si una misma fecha existe en
    # ambos formatos, gana el PDF (formato nuevo, mas completo).
    combinado = {}
    for clave, display, registros in historial_docx:
        combinado[clave] = (display, registros)
    for clave, display, registros in historial_pdf:
        combinado[clave] = (display, registros)

    historial = [combinado[clave] for clave in sorted(combinado)]
    return historial


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import motor_informes as motor

    h = cargar_historial()
    print(f"Revisiones cargadas: {len(h)}")
    print(f"Primera: {h[0][0]}  ({len(h[0][1])} registros)")
    print(f"Última:  {h[-1][0]}  ({len(h[-1][1])} registros)")

    kpis = motor.kpis_snapshot(h[-1][1])
    print(f"KPIs de la última revisión ({h[-1][0]}): {kpis}")
