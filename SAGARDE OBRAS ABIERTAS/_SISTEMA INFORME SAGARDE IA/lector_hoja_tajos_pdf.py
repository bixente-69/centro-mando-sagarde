# -*- coding: utf-8 -*-
"""
LECTOR HOJA DE REVISION DE TAJOS (PDF) — capa 0, comun a TODAS las obras
--------------------------------------------------------------------------
Motor generico para leer la "hoja de revision de tajos" en PDF que genera
la app de generacion de tajos (misma plantilla para cualquier obra desde
25/07/2026, primero adoptada en 2026 MUNGIA ACR NEINOR). Cada obra tiene su
propio adaptador (capa 1, en adaptadores/adaptador_{id}.py) que le pasa a
este motor SOLO lo que cambia de una obra a otra:

  - identificar_portal(texto_banner): como reconocer el portal/edificio a
    partir del texto de cabecera de cada tabla/pagina. Cada obra nombra sus
    portales de forma distinta ('ZR1.1', 'PORTAL 1', 'BLOQUE A', ...).
  - identificar_tajo(etiqueta_fila): como reconocer el tajo a partir de la
    etiqueta impresa en la primera columna de cada fila. Cada obra tiene su
    propio catalogo/alias de tajos.

Lo que SI es igual en todas las obras (porque lo genera la misma app):
  - la cabecera de bloque 'PLANTAS X · Y · Z' o 'PLANTA X'
  - la fila de vivienda debajo de la fila de grupos de planta
  - las celdas en verde con texto real 'X'/'M' rellenadas por la app
  - las celdas en blanco para marcar a mano en campo (marca de boli, sin
    texto extraible por pdfplumber)
  - el mecanismo de correcciones manuales via '<pdf>.correcciones.json'
    (lecturas verificadas a mano de marcas manuscritas; si no existe,
    esas celdas quedan pendientes — nunca se inventa un valor)

Ver protocolo completo ("cuando un PDF es una revision oficial valida") y
la receta para dar de alta una obra nueva en `_SISTEMA/MOTOR/CLAUDE.md`.

Requiere 'pdfplumber' (pip install pdfplumber --break-system-packages). Si
no esta instalado, se avisa y se devuelve vacio (no rompe otros formatos).
"""
import os
import re
import json

from claves_correcciones import normalizar_unidad, partir_clave

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


def cargar_correcciones(ruta_pdf):
    """Lee '<ruta_pdf>.correcciones.json' si existe. Devuelve dict
    {'portal__planta__tajo__viv': 'X'|'M'|'/'}. Si no existe, {}."""
    ruta_json = ruta_pdf + '.correcciones.json'
    if not os.path.isfile(ruta_json):
        return {}
    with open(ruta_json, encoding='utf-8') as f:
        data = json.load(f)
    return data.get('estados', data)


def _indice_correcciones(correcciones):
    """Indexa por clave normalizada y separa las claves mal formadas."""
    indice, malformadas = {}, []
    for clave, valor in correcciones.items():
        partes = partir_clave(clave)
        if partes is None:
            malformadas.append(clave)
            continue
        indice[partes] = (clave, valor)
    return indice, malformadas


def _resolver_celdas(portal_id, registros, dudas, indice, usadas):
    """Aplica correcciones a valores impresos y celdas manuscritas."""
    celdas, sin_corregir = {}, 0
    for (planta, codigo, viv), valor in registros.items():
        clave = (portal_id, planta, codigo, viv)
        normalizada = (portal_id, planta, codigo, normalizar_unidad(viv))
        if normalizada in indice:
            usadas.add(normalizada)
            celdas[clave] = indice[normalizada][1]
        else:
            celdas[clave] = valor
    for (planta, codigo, viv) in dudas:
        clave = (portal_id, planta, codigo, viv)
        normalizada = (portal_id, planta, codigo, normalizar_unidad(viv))
        if normalizada in indice:
            usadas.add(normalizada)
            celdas[clave] = indice[normalizada][1]
        else:
            celdas[clave] = ''
            sin_corregir += 1
    return celdas, sin_corregir


def _planta_id(texto):
    texto = (texto or '').replace('\n', ' ')
    if re.search(r'\bPORT', texto, re.I):
        return 'pb'
    m = re.search(r'PLANTA\s+(\w+)', texto, re.I)
    if not m:
        return None
    tok = m.group(1).upper()
    if tok == 'PB':
        return 'pb'
    m2 = re.match(r'(\d+)', tok)
    return m2.group(1) if m2 else None


def _plantas_desde_banner(texto):
    """Extrae la lista ordenada de plantas del titulo de bloque, p.ej.
    'ZR1 · ZR1.2 · PLANTAS PB · 1 · 2 · 3' -> ['pb','1','2','3']
    'ZR1 · ZR1.1 · PLANTA 6' -> ['6']
    Se usa la cabecera LIMPIA (una sola celda de texto) en vez de la fila de
    grupos, que en columnas estrechas (p.ej. 'PORTAL' de 1 vivienda) puede
    llegar partida entre celdas por el ajuste de linea de pdfplumber.
    """
    texto = (texto or '').replace('ª', '').replace('º', '')
    m = re.search(r'PLANTAS?\s+(.+)$', texto, re.I)
    if not m:
        return []
    partes = [p.strip().upper() for p in m.group(1).split('·')]
    plantas = []
    for p in partes:
        if not p:
            continue
        plantas.append('pb' if p == 'PB' else (re.match(r'(\d+)', p).group(1) if re.match(r'(\d+)', p) else None))
    return plantas


def _parsear_tabla_pagina(tabla, identificar_portal, identificar_tajo):
    """Devuelve (portal_id, {(planta,tajo,viv): 'X'|'M'|'/'}, dudas)."""
    idx_header = next((i for i, row in enumerate(tabla)
                        if row and row[0] and re.search(r'PLANTAS?\b', row[0], re.I)), None)
    if idx_header is None:
        return None, {}, []
    portal_id = identificar_portal(tabla[idx_header][0])
    plantas_bloque = _plantas_desde_banner(tabla[idx_header][0])
    fila_grupos = tabla[idx_header + 1]
    fila_viv = tabla[idx_header + 2]
    ncols = len(fila_viv)

    # Limites de cada grupo de planta = columnas donde la fila de grupos NO
    # es None (arranque de tramo). El contenido de esa celda no es fiable en
    # columnas estrechas, asi que solo se usa para saber DONDE empieza cada
    # tramo; el nombre de la planta se asigna en orden desde 'plantas_bloque'.
    arranques = [c for c in range(1, ncols) if c < len(fila_grupos) and fila_grupos[c]]
    planta_por_col = {}
    if len(arranques) == len(plantas_bloque):
        for idx_grupo, c_inicio in enumerate(arranques):
            c_fin = arranques[idx_grupo + 1] if idx_grupo + 1 < len(arranques) else ncols
            for c in range(c_inicio, c_fin):
                planta_por_col[c] = plantas_bloque[idx_grupo]
    else:
        # fallback: metodo antiguo (texto de la propia celda), por si algun
        # dia cambia el layout y el recuento de arranques no cuadra.
        grupo_actual = None
        for c in range(1, ncols):
            val = (fila_grupos[c] or '') if c < len(fila_grupos) else ''
            if val and ('PLANTA' in val.replace('\n', ' ').upper() or 'PORT' in val.replace('\n', ' ').upper()):
                grupo_actual = _planta_id(val)
            planta_por_col[c] = grupo_actual

    viv_por_col = {}
    for c in range(1, ncols):
        v = re.sub(r'\s+', '', (fila_viv[c] or '').replace('\n', ' ')) if c < len(fila_viv) else ''
        viv_por_col[c] = v or None

    registros, dudas = {}, []
    for row in tabla[idx_header + 3:]:
        etiqueta = row[0]
        if not etiqueta:
            continue
        if etiqueta.strip().upper().startswith('OBS'):
            break
        codigo = identificar_tajo(etiqueta)
        if not codigo:
            continue  # fila de seccion (INICIO DE OBRA, PLADUR, ...)
        for c in range(1, len(row)):
            planta, viv = planta_por_col.get(c), viv_por_col.get(c)
            if not planta or not viv:
                continue
            clave = (planta, codigo, viv)
            valor = (row[c] or '').strip()
            if valor in ('X', 'M', '/'):
                registros[clave] = valor
            else:
                dudas.append(clave)
    return portal_id, registros, dudas


def parsear_pdf(ruta_pdf, identificar_portal, identificar_tajo, nombre_log=''):
    """
    Lee toda la hoja de revision de tajos en PDF (todas las paginas/tablas).

    identificar_portal(texto_banner_pagina) -> id_portal interno | None
    identificar_tajo(etiqueta_fila) -> codigo_tajo interno | None

    Devuelve dict {(portal_id, planta_id, tajo_id, viv): 'X'|'M'|'/'|''},
    ya con las correcciones manuales aplicadas. Las celdas sin texto y sin
    correccion se ponen a '' (pendiente) — nunca se inventa un valor.
    """
    if pdfplumber is None:
        print("  [lector_hoja_tajos_pdf] AVISO: falta 'pdfplumber' (pip install pdfplumber); "
              "no se puede leer '{}'.".format(os.path.basename(ruta_pdf)))
        return {}

    correcciones = cargar_correcciones(ruta_pdf)
    indice, malformadas = _indice_correcciones(correcciones)
    usadas = set()
    registros_dict = {}
    dudas_sin_corregir = 0
    with pdfplumber.open(ruta_pdf) as pdf:
        for page in pdf.pages:
            tabla = page.extract_table()
            if not tabla:
                continue
            portal_id, registros, dudas = _parsear_tabla_pagina(tabla, identificar_portal, identificar_tajo)
            if portal_id is None:
                continue
            celdas, sin_corregir = _resolver_celdas(
                portal_id, registros, dudas, indice, usadas)
            registros_dict.update(celdas)
            dudas_sin_corregir += sin_corregir

    _avisar(
        ruta_pdf,
        nombre_log,
        dudas_sin_corregir,
        indice,
        usadas,
        malformadas,
    )

    return registros_dict


def _avisar(ruta_pdf, nombre_log, dudas_sin_corregir, indice, usadas,
            malformadas):
    """Hace visibles celdas pendientes, claves huérfanas y claves inválidas."""
    etiqueta = '[{}] '.format(nombre_log) if nombre_log else ''
    fichero = os.path.basename(ruta_pdf)

    if dudas_sin_corregir:
        print("  {}AVISO: {} celda(s) manuscrita(s) SIN corrección "
              "transcrita en '{}' -> se tratan como pendiente.".format(
                  etiqueta, dudas_sin_corregir, fichero))

    huerfanas = sorted(indice[k] for k in indice if k not in usadas)
    if huerfanas:
        print("  {}AVISO: {} corrección(es) de '{}' no casan con ninguna "
              "celda de la hoja; se reintentan sobre la ficha:".format(
                  etiqueta, len(huerfanas), fichero))
        for clave, valor in huerfanas[:10]:
            print("      {} = {}".format(clave, valor))
        if len(huerfanas) > 10:
            print("      ... y {} más.".format(len(huerfanas) - 10))

    if malformadas:
        print("  {}AVISO: {} clave(s) de '{}' no tienen los 4 tramos "
              "'portal__planta__tajo__unidad': {}".format(
                  etiqueta,
                  len(malformadas),
                  fichero,
                  ', '.join(sorted(malformadas)[:10]),
              ))


def _fecha_desde_nombre(fn):
    m = re.search(r'(\d{2})(\d{2})(\d{4})', fn)
    if not m:
        return None, None
    dd, mm, aaaa = m.groups()
    try:
        d, mo, y = int(dd), int(mm), int(aaaa)
    except ValueError:
        return None, None
    if not (1 <= d <= 31 and 1 <= mo <= 12 and 2000 <= y <= 2100):
        return None, None
    return aaaa + mm + dd, "{}/{}/{}".format(dd, mm, aaaa)


def aporta_datos_de_campo(ruta_pdf, n_anotaciones, hay_sidecar):
    """True si el PDF trae algo que no supieramos ya.

    Una hoja recien generada por la app NO es una revision: lleva impreso el
    estado que ya esta en la base y nada mas. Como la app imprime en blanco lo
    que no sabe, leerla de vuelta convierte los '?' en 'P' y hace bajar el
    porcentaje sin que nadie haya pisado la obra. Paso con
    REVISION MUNGIA 28072026.pdf: 35 celdas de la vivienda E y Mungia de 79.8
    a 78.6.

    Aporta si tiene marcas de pen digital (anotaciones) o si alguien ha
    transcrito lo escrito a boli en el sidecar. Un escaneo de papel no lleva
    anotaciones, asi que para el vale el sidecar.
    """
    return bool(n_anotaciones) or bool(hay_sidecar)


def _mide_aportacion(ruta_pdf):
    """(n_anotaciones, hay_sidecar) de un PDF concreto."""
    hay_sidecar = os.path.isfile(ruta_pdf + '.correcciones.json')
    n_anotaciones = 0
    try:
        import pdfplumber
        with pdfplumber.open(ruta_pdf) as pdf:
            n_anotaciones = sum(len(p.annots or []) for p in pdf.pages)
    except Exception as exc:
        # Si no se puede mirar, se deja pasar y que lo juzgue el parser: es
        # peor descartar una revision buena que colar una hoja sin usar.
        print(f"  AVISO: no se pudo comprobar si '{os.path.basename(ruta_pdf)}' "
              f"lleva marcas ({type(exc).__name__}). Se acepta.")
        return 1, hay_sidecar
    return n_anotaciones, hay_sidecar


def listar_revisiones_pdf(carpeta, contiene=None, prefijo='REVISION', nombre_log=''):
    """
    Busca ficheros '<prefijo> ... <contiene> ... DDMMAAAA.pdf' dentro de
    'carpeta'. Devuelve [(clave_orden_AAAAMMDD, fecha_display_DD/MM/AAAA,
    nombre_fichero), ...] ordenado por fecha.

    'contiene': palabra que debe aparecer en el nombre (ej. 'MUNGIA') para
    distinguir la revision de esta obra de otros ficheros REVISION *.pdf
    que pudiera haber en la misma carpeta. None para no filtrar.
    """
    if not os.path.isdir(carpeta):
        return []
    archivos = []
    for fn in os.listdir(carpeta):
        nombre_up = fn.upper()
        if not nombre_up.startswith(prefijo.upper()):
            continue
        if contiene and contiene.upper() not in nombre_up:
            continue
        if not fn.lower().endswith('.pdf'):
            continue
        clave, display = _fecha_desde_nombre(fn)
        if clave:
            etiqueta = '[{}] '.format(nombre_log) if nombre_log else ''
            n_anot, sidecar = _mide_aportacion(os.path.join(carpeta, fn))
            if not aporta_datos_de_campo(fn, n_anot, sidecar):
                # Se avisa pero NO se descarta: excluirla haria retroceder a
                # una hoja anterior, y una hoja mas vieja tiene mas celdas en
                # blanco todavia. El dano de las celdas en blanco se ataja
                # donde nace, en ficha_obra: una casilla sin marca no baja un
                # estado ya conocido.
                print("{}AVISO: '{}' no lleva marcas ni correcciones "
                      "transcritas. Parece una hoja impresa y no usada: no "
                      "aporta nada que no este ya en la base.".format(
                          etiqueta, fn))
            archivos.append((clave, display, fn))
        else:
            etiqueta = '[{}] '.format(nombre_log) if nombre_log else ''
            print("{}AVISO: '{}' sin fecha DDMMAAAA valida, ignorado.".format(etiqueta, fn))
    archivos.sort(key=lambda x: x[0])
    return archivos
