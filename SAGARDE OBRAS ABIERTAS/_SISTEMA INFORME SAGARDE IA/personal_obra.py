# -*- coding: utf-8 -*-
"""Datos de personal en obra: ingesta de los lotes de jornadas que exporta la tablet, catálogo de
trabajadores y estado para la app.
Funciones principales: ingerir_lote, alta_trabajador, fusionar, aplanar, totales_control,
exportar_estado, comprobar y la línea de comandos (main).
Empresa: cada persona tiene una (`poner_empresa`, la clave `empresas` del fichero y `separar_empresas`).
"""

from __future__ import annotations
import argparse, copy, datetime as dt, json, math, os, re, sys, tempfile, time, unicodedata
from collections import Counter
from pathlib import Path

# Días canónicos de la semana y jornada base por defecto de 7.5 h de lunes a viernes.
DIAS = ("lun", "mar", "mie", "jue", "vie", "sab", "dom")
HOR = {"lun": 7.5, "mar": 7.5, "mie": 7.5, "jue": 7.5, "vie": 7.5, "sab": 0, "dom": 0}
# Claves permitidas (esquemas cerrados). LK = lote, JK = jornada del lote, PK = presente del lote:
# un campo extra los rechaza. CK, TK, OK, GJK y GPK (catálogo, trabajador, obra, jornada guardada y
# presente guardado) los usa `comprobar` para señalar campos fuera del esquema.
LK = {
    "tipo", "version", "obra", "horario_semanal", "excepciones_horario", "jornadas",
    "dispositivo", "renombres", "altas", "bajas", "empresas", "categorias", "horarios_preferidos",
}
JK = {"ambito", "fecha", "presentes", "anulada", "notas", "registrado"}
PK = {"nombre", "horas", "extra"}
CK = {"version", "trabajadores"}
TK = {
    "id", "nombre", "categoria", "empresa", "activo", "alta",
    "fusionado_en", "nombres_anteriores", "horario_preferido",
}
OK = {"version", "obra", "jornada_base_h", "horario_semanal", "excepciones_horario", "jornadas"}
GJK = {"fecha", "ambito", "anulada", "notas", "presentes", "registrado", "origen"}
GPK = {"id", "horas", "extra"}

PATRONES_PRIVADOS = (
    ("DNI", re.compile(r"(?<![A-Za-z0-9])\d{8}[- ]?[A-Za-z](?![A-Za-z0-9])")),
    ("NIE", re.compile(r"(?<![A-Za-z0-9])[XYZxyz][- ]?\d{7}[- ]?[A-Za-z](?![A-Za-z0-9])")),
    ("telefono", re.compile(r"(?<![\d.])(?:\+?34[\s.-]?)?[6789](?:[\s.-]?\d){8}(?!\d)")),
    ("correo", re.compile(r"[^\s@\"']+@[^\s@\"']+\.[^\s@\"']+")),
)


def limpiar_nombre(x):
    """Colapsa espacios internos y recorta extremos de una cadena.
    Devuelve el texto limpio o cadena vacía si no es texto.
    """
    return " ".join(x.split()) if isinstance(x, str) else ""


def nombre_valido(x):
    """Comprueba que el nombre limpio tenga de 1 a 60 caracteres.
    Verifica que carezca de caracteres de control.
    """
    x = limpiar_nombre(x)
    return bool(x) and len(x) <= 60 and not any(unicodedata.category(c) == "Cc" for c in x)


def nombre_publicable(x):
    """Comprueba que un nombre sea válido y no lleve etiquetas ni parezca un DNI, teléfono o correo."""
    nombre = limpiar_nombre(x)
    return nombre_valido(x) and "<" not in nombre and ">" not in nombre and not any(
        patron.search(nombre) for _, patron in PATRONES_PRIVADOS
    )


def clave_nombre(x):
    """Genera la clave canónica sin tildes y en minúsculas.
    Permite comparar nombres ignorando grafías alternativas.
    """
    return "".join(
        c for c in unicodedata.normalize("NFD", limpiar_nombre(x)) if not unicodedata.combining(c)
    ).lower()


def es_autonomo(empresa):
    """True si la empresa termina en «@AUT» (mayúsculas indiferentes, con o sin espacio): un autónomo."""
    return re.search(r"@\s*aut$", limpiar_nombre(empresa), re.IGNORECASE) is not None


def empresa_valida(x):
    """Una empresa vale si es texto vacío (sin empresa) o un nombre publicable (nunca DNI, teléfono ni correo)."""
    return isinstance(x, str) and (limpiar_nombre(x) == "" or nombre_publicable(x))


def _sis(r, n):
    return Path(r) / "_SISTEMA INFORME SAGARDE IA" / n


def _rop(r, ob, o, n="personal_obra.json"):
    return Path(r) / ob[o] / "INFORME SAGARDE IA" / n


def _read(p):
    """Lee y decodifica un fichero en formato JSON con UTF-8.
    Devuelve la estructura de datos Python resultante.
    """
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _bytes(x):
    return (json.dumps(x, ensure_ascii=False, indent=1) + "\n").encode()


def _atomic(p, b):
    """Escribe en disco de forma atómica con temporal y fsync.
    Reintenta ante bloqueos de sincronización en OneDrive.
    """
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Crea el temporal en la misma carpeta para que el reemplazo atómico se realice en el mismo
    # volumen.
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(b)
            f.flush()
            # Fuerza la escritura física en disco antes del reemplazo para evitar ficheros corruptos
            # o truncados.
            os.fsync(f.fileno())
        # OneDrive suele bloquear ficheros durante la sincronización; reintenta hasta 5 veces con
        # espera.
        for i in range(5):
            try:
                os.replace(tmp, p)
                tmp = None
                return
            except PermissionError:
                if i == 4:
                    raise
                time.sleep(0.2 * (i + 1))
    finally:
        # Garantiza la limpieza del fichero temporal si la sustitución atómica no culmina con éxito.
        if tmp:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass


def cargar_catalogo(raiz):
    """Carga el catálogo central de trabajadores desde disco.
    Si no existe devuelve una estructura vacía en versión 1.
    """
    p = _sis(raiz, "personal_catalogo.json")
    return _read(p) if p.exists() else {"version": 1, "trabajadores": []}


def guardar_catalogo(raiz, catalogo):
    """Guarda el catálogo de trabajadores de forma atómica.
    Escribe en formato JSON UTF-8 con sangría uniforme.
    """
    _atomic(_sis(raiz, "personal_catalogo.json"), _bytes(catalogo))


def cargar_obra(raiz, obras, obra):
    """Carga los datos de personal y jornadas de una obra.
    Si no existe inicializa con horario semanal base L-V.
    """
    p = _rop(raiz, obras, obra)
    return (
        _read(p)
        if p.exists()
        else {
            "version": 1,
            "obra": obra,
            "jornada_base_h": 7.5,
            "horario_semanal": dict(HOR),
            "excepciones_horario": {},
            "jornadas": [],
        }
    )


def _saveobra(r, ob, o, d):
    """Guarda la obra con ordenación determinista de datos.
    Persiste atómicamente el fichero personal_obra.json.
    """
    # Guarda los horarios propios con un orden estable.
    ex = d.get("excepciones_horario", {})
    if isinstance(ex, dict):
        # Un valor dañado (que no es un diccionario) se deja tal cual: lo señala `comprobar`,
        # no se rompe al guardar otra cosa.
        d["excepciones_horario"] = {
            i: ({dia: ex[i][dia] for dia in DIAS if dia in ex[i]} if isinstance(ex[i], dict) else ex[i])
            for i in sorted(ex)
        }
    d["jornadas"].sort(key=lambda j: (j["fecha"], j["ambito"]))
    for j in d["jornadas"]:
        j["presentes"].sort(key=lambda p: p["id"])
    _atomic(_rop(r, ob, o), _bytes(d))


def _dist(a, b):
    """Calcula la distancia de Levenshtein entre dos cadenas.
    Devuelve el número mínimo de operaciones de edición.
    """
    z = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        n = [i]
        for j, y in enumerate(b, 1):
            n.append(min(n[-1] + 1, z[j] + 1, z[j - 1] + (x != y)))
        z = n
    return z[-1]


def _similar(a, b):
    """Parecidas: ambas de >= 3 letras y a distancia <= 1 o una dentro de la otra."""
    return len(a) >= 3 and len(b) >= 3 and (_dist(a, b) <= 1 or a in b or b in a)


def _newid(ts):
    """Genera el siguiente id correlativo de trabajador.
    Busca el número mayor con prefijo T y suma uno.
    """
    ns = [
        int(t["id"][1:])
        for t in ts
        if isinstance(t.get("id"), str) and t["id"].startswith("T") and t["id"][1:].isdigit()
    ]
    return "T" + str(max(ns, default=0) + 1).zfill(4)


def alta_trabajador(raiz, nombre, categoria="", empresa="", hoy=None, escribir=False):
    """Registra un nuevo trabajador en el catálogo central.
    Comprueba duplicados y avisa si hay nombres parecidos.
    """
    n = limpiar_nombre(nombre)
    if not n:
        return {"ok": False, "id": None, "error": "nombre_vacio", "parecidos": [], "escrito": False}
    if not nombre_valido(nombre):
        return {"ok": False, "id": None, "error": "nombre_invalido", "parecidos": [], "escrito": False}
    c = cargar_catalogo(raiz)
    k = clave_nombre(n)
    # Detecta nombres parecidos para alertar de posibles erratas sin bloquear altas legítimas
    # similares.
    ps = [
        t["nombre"]
        for t in c["trabajadores"]
        if clave_nombre(t["nombre"]) != k and _similar(k, clave_nombre(t["nombre"]))
    ]
    # Comprueba duplicados exactos por clave de nombre entre los trabajadores no fusionados.
    old = next(
        (t for t in c["trabajadores"] if t.get("fusionado_en") is None and clave_nombre(t["nombre"]) == k),
        None,
    )
    if old:
        return {"ok": False, "id": old["id"], "error": "nombre_duplicado", "parecidos": ps, "escrito": False}
    i = _newid(c["trabajadores"])
    c["trabajadores"].append(
        {
            "id": i,
            "nombre": n,
            "categoria": categoria,
            "empresa": empresa,
            "activo": True,
            "alta": hoy or dt.date.today().isoformat(),
            "fusionado_en": None,
        }
    )
    if escribir:
        guardar_catalogo(raiz, c)
    return {"ok": True, "id": i, "error": None, "parecidos": ps, "escrito": bool(escribir)}


def _num(x):
    """Devuelve la hora redondeada a 2 decimales, o None si no es un número finito (un bool
    tampoco), si tiene más de 2 decimales reales (tolerancia 1e-9 para el ruido de coma flotante)
    o si queda fuera de 0-24.
    """
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        return None
    # Redondea a 2 decimales y tolera ruido de coma flotante (menor de 1e-9) rechazando decimales
    # espurios.
    y = round(x, 2)
    return y if abs(x - y) < 1e-9 and 0 <= y <= 24 else None


def _date(x):
    """Valida formato de fecha ISO estricto YYYY-MM-DD.
    Devuelve True si corresponde a una fecha real.
    """
    try:
        return isinstance(x, str) and len(x) == 10 and dt.date.fromisoformat(x).isoformat() == x
    except ValueError:
        return False


def _hv(x):
    """Comprueba que el horario tenga los 7 días de la semana.
    Verifica que todas las horas sean números válidos.
    """
    return isinstance(x, dict) and set(x) == set(DIAS) and all(_num(v) is not None for v in x.values())


def _excepciones_validas(x):
    """Valida nombres, días y horas de horarios propios.
    Comprueba que no existan trabajadores duplicados.
    """
    # Valida nombres, duplicados, días y horas del horario propio.
    if not isinstance(x, dict):
        return False
    claves = []
    for nombre, horario in x.items():
        if not nombre_valido(nombre):
            return False
        claves.append(clave_nombre(nombre))
        if not isinstance(horario, dict):
            return False
        if any(dia not in DIAS for dia in horario):
            return False
        if any(_num(horas) is None for horas in horario.values()):
            return False
    return len(claves) == len(set(claves))


def validar_lote(lote, obras):
    """Valida la estructura global y esquema cerrado del lote.
    Devuelve la lista de códigos de error de lote hallados.
    """
    if not isinstance(lote, dict):
        return ["lote_invalido"]
    e = []
    if not isinstance(lote.get("jornadas"), list):
        e.append("lote_invalido")
    if lote.get("tipo") != "lote_personal":
        e.append("tipo_desconocido")
    if lote.get("version") != 1 or isinstance(lote.get("version"), bool):
        e.append("version_desconocida")
    if not isinstance(lote.get("obra"), str) or lote["obra"] not in obras:
        e.append("obra_invalida")
    if set(lote) - LK:
        e.append("campo_desconocido")
    if "horario_semanal" in lote and not _hv(lote["horario_semanal"]):
        e.append("horario_invalido")
    if "excepciones_horario" in lote and not _excepciones_validas(lote["excepciones_horario"]):
        e.append("excepcion_invalida")
    renombres = lote.get("renombres")
    if "renombres" in lote and (
        not isinstance(renombres, list)
        or any(
            not isinstance(x, dict)
            or set(x) != {"de", "a"}
            or not nombre_publicable(x.get("de"))
            or not nombre_publicable(x.get("a"))
            for x in renombres
        )
    ):
        e.append("renombre_invalido")
    altas = lote.get("altas")
    if "altas" in lote and (
        not isinstance(altas, list) or any(not nombre_publicable(x) for x in altas)
    ):
        e.append("alta_invalida")
    bajas = lote.get("bajas")
    if "bajas" in lote and (
        not isinstance(bajas, list) or any(not nombre_publicable(x) for x in bajas)
    ):
        e.append("baja_invalida")
    empresas = lote.get("empresas")
    if "empresas" in lote and (
        not isinstance(empresas, list)
        or any(
            not isinstance(x, dict)
            or set(x) != {"nombre", "empresa"}
            or not nombre_publicable(x.get("nombre"))
            or not empresa_valida(x.get("empresa"))
            for x in empresas
        )
    ):
        e.append("empresa_invalida")
    categorias = lote.get("categorias")
    if "categorias" in lote and (
        not isinstance(categorias, list)
        or any(
            not isinstance(x, dict)
            or set(x) != {"nombre", "categoria"}
            or not nombre_publicable(x.get("nombre"))
            or not empresa_valida(x.get("categoria"))
            for x in categorias
        )
    ):
        e.append("categoria_invalida")
    if "horarios_preferidos" in lote and not _excepciones_validas(lote["horarios_preferidos"]):
        e.append("horario_preferido_invalido")
    return e


def _resolve(i, mp):
    """Resuelve la cadena de fusiones hasta el id vigente final.
    Controla ciclos para evitar bucles infinitos.
    """
    # Recorre la cadena de fusiones hasta el id vigente final, detectando ciclos para evitar bucles.
    seen = set()
    while i in mp and mp[i].get("fusionado_en") is not None and i not in seen:
        seen.add(i)
        i = mp[i]["fusionado_en"]
    return i


def _indices_nombres(catalogo):
    """Crea los índices de nombres actuales y anteriores, cada uno hacia el id vigente (siguiendo fusiones)."""
    mp = {t["id"]: t for t in catalogo["trabajadores"]}
    actuales = {}
    anteriores = {}
    for trabajador in catalogo["trabajadores"]:
        vigente = _resolve(trabajador["id"], mp)
        actuales[clave_nombre(trabajador["nombre"])] = vigente
        for nombre in trabajador.get("nombres_anteriores", []):
            anteriores[clave_nombre(nombre)] = vigente
    return mp, actuales, anteriores


def _buscar_nombre(nombre, catalogo):
    """Resuelve un nombre: primero entre los actuales y después entre los anteriores."""
    mp, actuales, anteriores = _indices_nombres(catalogo)
    clave = clave_nombre(nombre)
    if clave in actuales:
        return actuales[clave], "actual", mp
    if clave in anteriores:
        return anteriores[clave], "anterior", mp
    return None, None, mp


def _persona_nueva(catalogo, nombre, hoy):
    """Añade al catálogo una persona nueva con los mismos campos que las altas de siempre."""
    identificador = _newid(catalogo["trabajadores"])
    persona = {
        "id": identificador,
        "nombre": nombre,
        "categoria": "",
        "empresa": "",
        "activo": True,
        "alta": hoy,
        "fusionado_en": None,
    }
    catalogo["trabajadores"].append(persona)
    return persona


def _aplicar_renombre(catalogo, de, a, identificador=None, rechazar_fusionada=False):
    """Aplica la regla común de renombre (la usan el lote y `renombrar`) y devuelve su resultado."""
    de = limpiar_nombre(de)
    a = limpiar_nombre(a)
    mp, actuales, anteriores = _indices_nombres(catalogo)
    origen_anterior = False
    if identificador is not None:
        if identificador not in mp:
            return {"error": "persona_inexistente", "id": None}
        if rechazar_fusionada and mp[identificador].get("fusionado_en") is not None:
            return {"error": "persona_fusionada", "id": identificador}
        origen = _resolve(identificador, mp)
    else:
        clave_de = clave_nombre(de)
        if clave_de in actuales:
            origen = actuales[clave_de]
        elif clave_de in anteriores:
            origen = anteriores[clave_de]
            origen_anterior = True
        else:
            return {"error": "persona_inexistente", "id": None}
    persona = mp[origen]
    otro = actuales.get(clave_nombre(a))
    if otro is not None and otro != origen:
        return {"error": "coincide_con_otro", "id": origen, "id_otro": otro}
    anterior_actual = persona["nombre"]
    if anterior_actual == a:
        return {
            "error": None, "accion": "sin_cambios", "id": origen, "id_otro": None,
            "de_actual": anterior_actual, "uso_anterior": False,
        }
    historial = list(persona.get("nombres_anteriores", []))
    clave_nueva = clave_nombre(a)
    historial = [x for x in historial if clave_nombre(x) != clave_nueva]
    if clave_nombre(anterior_actual) != clave_nueva:
        historial.append(anterior_actual)
    unicos = []
    vistas = set()
    for nombre in historial:
        clave = clave_nombre(nombre)
        if clave not in vistas:
            unicos.append(nombre)
            vistas.add(clave)
    persona["nombre"] = a
    persona["nombres_anteriores"] = unicos
    return {
        "error": None, "accion": "renombrado", "id": origen, "id_otro": None,
        "de_actual": anterior_actual, "uso_anterior": origen_anterior,
    }


def _grafia_empresa(catalogo, empresa):
    """La grafía con la que ya consta una empresa en la base (se compara sin tildes ni mayúsculas);
    si es nueva, la que se ha escrito."""
    escrita = limpiar_nombre(empresa)
    clave = clave_nombre(escrita)
    for t in catalogo["trabajadores"]:
        actual = limpiar_nombre(t.get("empresa"))
        if t.get("fusionado_en") is None and actual and clave_nombre(actual) == clave:
            return actual
    return escrita


def _aplicar_empresa(catalogo, persona, empresa):
    """Regla común de empresa (la usan el fichero y `poner_empresa`): una persona, una empresa.
    Vacía = quitarla. Devuelve la acción (puesta, cambiada, quitada o sin_cambios) y la empresa de antes y de después.
    """
    antes = limpiar_nombre(persona.get("empresa"))
    despues = _grafia_empresa(catalogo, empresa) if limpiar_nombre(empresa) else ""
    if clave_nombre(despues) == clave_nombre(antes):
        return {"accion": "sin_cambios", "antes": antes, "despues": antes}
    persona["empresa"] = despues
    accion = "quitada" if not despues else ("puesta" if not antes else "cambiada")
    return {"accion": accion, "antes": antes, "despues": despues}


def _traza_base(ts, obra, accion, dispositivo=None):
    """Construye una línea de traza con las claves comunes (sin ámbito, fecha ni presentes)."""
    return {
        "ts": ts,
        "obra": obra,
        "ambito": None,
        "fecha": None,
        "accion": accion,
        "n_presentes": 0,
        "avisos": [],
        "dispositivo": dispositivo,
    }


def _norm(x):
    """Normaliza y valida una jornada individual y presentes.
    Devuelve los datos limpios y la lista de rechazos.
    """
    if not isinstance(x, dict):
        return None, ["campo_desconocido"]
    e = []
    if set(x) - JK:
        e.append("campo_desconocido")
    a, f = x.get("ambito"), x.get("fecha")
    if a not in ("vivienda", "garaje"):
        e.append("ambito_invalido")
    if not _date(f):
        e.append("fecha_invalida")
    ps = x.get("presentes")
    an = x.get("anulada", False)
    if not isinstance(ps, list):
        ps = []
        e.append("sin_presentes")
    out = []
    ks = []
    for p in ps:
        if not isinstance(p, dict):
            e.append("campo_desconocido")
            continue
        if set(p) - PK:
            e.append("campo_desconocido")
        n = limpiar_nombre(p.get("nombre"))
        k = clave_nombre(n)
        ks.append(k)
        if not n:
            e.append("nombre_vacio")
        elif not nombre_valido(p.get("nombre")):
            e.append("nombre_invalido")
        h = _num(p.get("horas"))
        ex = _num(p.get("extra", 0))
        if h is None:
            e.append("horas_invalidas")
        if ex is None or (h is not None and ex > h):
            e.append("extra_invalido")
        out.append({"nombre": n, "clave": k, "horas": h, "extra": ex})
    # Rechaza si una misma persona aparece repetida en la lista de presentes de la jornada.
    if any(v > 1 for v in Counter(ks).values()):
        e.append("presente_duplicado")
    # Una jornada anulada debe tener presentes vacíos; si no está anulada, no puede guardarse vacía.
    if an is True and ps:
        e.append("anulada_con_presentes")
    if not ps and an is not True:
        e.append("sin_presentes")
    if not isinstance(an, bool):
        e.append("campo_desconocido")
    return {
        "ambito": a,
        "fecha": f,
        "anulada": an,
        "notas": x.get("notas", ""),
        "presentes": out,
        "registrado": x.get("registrado"),
    }, list(dict.fromkeys(e))


def _content(j):
    """Extrae el contenido comparable normalizado de una jornada.
    Ordena los presentes por id para verificar idempotencia.
    """
    return {
        k: (sorted(j[k], key=lambda p: p["id"]) if k == "presentes" else j[k])
        for k in ("fecha", "ambito", "anulada", "notas", "presentes")
    }


def _now():
    return dt.datetime.now().astimezone().isoformat()


def ingerir_lote(
    lote, raiz, obras, hoy, escribir=False, ahora=None, sha256=None, fichero=None, estado=None
):
    """Ingiere un lote: lo valida entero y aplica renombres, altas, jornadas, horario semanal y horarios propios.
    Con escribir=True guarda y anota la traza; con `estado` trabaja en memoria sin tocar el disco.
    Devuelve ok, escrito, lote_rechazado, avisos_lote, jornadas, altas, excepciones, renombres y más.
    """
    if estado is not None and escribir:
        raise ValueError("no se puede escribir al usar estado")
    if sha256 is not None and (
        not isinstance(sha256, str) or re.fullmatch(r"[0-9A-Fa-f]{64}", sha256) is None
    ):
        raise ValueError("sha256 invalido")
    errores_lote = validar_lote(lote, obras)
    res = {
        "ok": not errores_lote, "escrito": False, "lote_rechazado": errores_lote,
        "avisos_lote": [], "jornadas": [], "altas": [], "excepciones": [],
        "renombres": [], "altas_pedidas": [], "obra_creada": False, "recibido": False,
        "empresas": [], "categorias": [], "horarios_preferidos": [], "bajas": [],
    }
    # Rechazo de lote completo: si la cabecera o el esquema general fallan no se procesa nada.
    if errores_lote:
        return res
    oid = lote["obra"]
    no_existia = estado is None and not _rop(raiz, obras, oid).exists()
    # Copias de trabajo del catálogo y de las obras (del disco, o del `estado` en memoria): se opera en ellas
    # de forma aislada y solo al final se persisten o se devuelven al `estado`.
    if estado is None:
        cat = copy.deepcopy(cargar_catalogo(raiz))
        ods = {o: copy.deepcopy(cargar_obra(raiz, obras, o)) for o in obras}
    else:
        cat = copy.deepcopy(estado["cat"])
        ods = copy.deepcopy(estado["ods"])
    od = ods[oid]
    cambio_cat = False
    cambio_obra = False
    trazas = []
    ts = ahora or _now()
    # El primer fichero recibido de una obra crea su `personal_obra.json`: ya no hay alta manual de la obra.
    if sha256 is not None and no_existia:
        res["obra_creada"] = True
        cambio_obra = True
        trazas.append(_traza_base(ts, oid, "obra_creada", lote.get("dispositivo")))

    # Paso 1: renombres, en orden (cada uno ve el efecto de los anteriores). El nombre cambia por id: las
    # jornadas y horarios propios siguen colgando de la misma persona.
    for item in lote.get("renombres", []):
        de = limpiar_nombre(item["de"])
        nuevo = limpiar_nombre(item["a"])
        r = _aplicar_renombre(cat, de, nuevo)
        if r.get("error") == "persona_inexistente":
            accion = "sin_origen"
            res["avisos_lote"].append({"codigo": "renombre_sin_origen", "detalle": de})
        elif r.get("error") == "coincide_con_otro":
            accion = "coincide_con_otro"
            detalle = f"{de} -> {nuevo} ({r['id']}, {r['id_otro']})"
            res["avisos_lote"].append({"codigo": "renombre_coincide_con_otro", "detalle": detalle})
        else:
            accion = r["accion"]
            if accion == "renombrado":
                cambio_cat = True
                tr = _traza_base(ts, oid, "renombre", lote.get("dispositivo"))
                tr.update({"id": r["id"], "de": r["de_actual"], "a": nuevo})
                trazas.append(tr)
                if r["uso_anterior"]:
                    detalle = f"{de} -> {r['de_actual']}"
                    res["avisos_lote"].append({"codigo": "nombre_anterior_usado", "detalle": detalle})
        orden = None
        if accion == "coincide_con_otro":
            orden = f"personal_obra.py fusionar {r['id']} {r['id_otro']}"
        res["renombres"].append({
            "de": de, "a": nuevo, "accion": accion, "id": r.get("id"),
            "id_otro": r.get("id_otro"), "orden": orden,
        })

    # Paso 2: altas sin jornada. Un nombre que ya existe (actual o anterior) no abre una persona nueva.
    for original in lote.get("altas", []):
        nombre = limpiar_nombre(original)
        identificador, modo, mp = _buscar_nombre(nombre, cat)
        if identificador is None:
            parecido = next((
                p for p in cat["trabajadores"]
                if _similar(clave_nombre(nombre), clave_nombre(p["nombre"]))
            ), None)
            if parecido:
                res["avisos_lote"].append({
                    "codigo": "nombre_parecido", "detalle": nombre + " ~ " + parecido["nombre"],
                })
            persona = _persona_nueva(cat, nombre, hoy)
            identificador = persona["id"]
            accion = "alta"
            cambio_cat = True
            res["altas"].append({"id": identificador, "nombre": nombre})
            res["avisos_lote"].append({"codigo": "alta_nueva", "detalle": nombre})
            tr = _traza_base(ts, oid, "alta_persona", lote.get("dispositivo"))
            tr.update({"id": identificador, "nombre": nombre})
            trazas.append(tr)
        else:
            accion = "sin_cambios"
            if modo == "anterior":
                res["avisos_lote"].append({
                    "codigo": "nombre_anterior_usado",
                    "detalle": f"{nombre} -> {mp[identificador]['nombre']}",
                })
            if mp[identificador].get("activo") is False:
                mp[identificador]["activo"] = True
                accion = "alta"
                cambio_cat = True
                res["altas"].append({"id": identificador, "nombre": mp[identificador]["nombre"]})
                tr = _traza_base(ts, oid, "alta_persona", lote.get("dispositivo"))
                tr.update({"id": identificador, "nombre": mp[identificador]["nombre"]})
                trazas.append(tr)
        res["altas_pedidas"].append({"nombre": nombre, "id": identificador, "accion": accion})

    # Paso 2b: empresas, una por persona. Van después de los renombres y las altas (quien se acaba de crear o de
    # renombrar ya puede llevar empresa) y antes de las jornadas. Quien no existe no se crea: se avisa.
    for item in lote.get("empresas", []):
        nombre = limpiar_nombre(item["nombre"])
        empresa = limpiar_nombre(item["empresa"])
        identificador, modo, mp = _buscar_nombre(nombre, cat)
        if identificador is None:
            res["avisos_lote"].append({"codigo": "empresa_sin_persona", "detalle": nombre})
            res["empresas"].append({
                "nombre": nombre, "id": None, "accion": "sin_persona", "antes": "", "despues": empresa,
            })
            continue
        persona = mp[identificador]
        if modo == "anterior":
            detalle = f"{nombre} -> {persona['nombre']}"
            res["avisos_lote"].append({"codigo": "nombre_anterior_usado", "detalle": detalle})
        cambio = _aplicar_empresa(cat, persona, empresa)
        if cambio["accion"] != "sin_cambios":
            cambio_cat = True
            tr = _traza_base(ts, oid, "empresa", lote.get("dispositivo"))
            tr.update({
                "id": identificador, "nombre": persona["nombre"], "de": cambio["antes"], "a": cambio["despues"],
            })
            trazas.append(tr)
        res["empresas"].append({
            "nombre": persona["nombre"], "id": identificador, "accion": cambio["accion"],
            "antes": cambio["antes"], "despues": cambio["despues"],
        })

    # Paso 2c: categorías/oficios por persona.
    for item in lote.get("categorias", []):
        nombre = limpiar_nombre(item["nombre"])
        categoria = limpiar_nombre(item["categoria"])
        identificador, modo, mp = _buscar_nombre(nombre, cat)
        if identificador is None:
            res["avisos_lote"].append({"codigo": "categoria_sin_persona", "detalle": nombre})
            res["categorias"].append({
                "nombre": nombre, "id": None, "accion": "sin_persona", "antes": "", "despues": categoria,
            })
            continue
        persona = mp[identificador]
        if modo == "anterior":
            detalle = f"{nombre} -> {persona['nombre']}"
            res["avisos_lote"].append({"codigo": "nombre_anterior_usado", "detalle": detalle})
        antes = limpiar_nombre(persona.get("categoria"))
        if clave_nombre(categoria) == clave_nombre(antes):
            accion = "sin_cambios"
            despues = antes
        else:
            persona["categoria"] = categoria
            despues = categoria
            accion = "quitada" if not categoria else ("puesta" if not antes else "cambiada")
            cambio_cat = True
            tr = _traza_base(ts, oid, "categoria", lote.get("dispositivo"))
            tr.update({"id": identificador, "nombre": persona["nombre"], "de": antes, "a": despues})
            trazas.append(tr)
        res["categorias"].append({
            "nombre": persona["nombre"], "id": identificador, "accion": accion,
            "antes": antes, "despues": despues,
        })

    # Paso 2d: horarios preferidos de la persona en la base (valen para todas las obras salvo horario propio en una obra).
    for original, horario in lote.get("horarios_preferidos", {}).items():
        nombre = limpiar_nombre(original)
        identificador, modo, mp = _buscar_nombre(nombre, cat)
        if identificador is None and horario:
            parecido = next((
                p for p in cat["trabajadores"]
                if _similar(clave_nombre(nombre), clave_nombre(p["nombre"]))
            ), None)
            if parecido:
                res["avisos_lote"].append({
                    "codigo": "nombre_parecido", "detalle": nombre + " ~ " + parecido["nombre"],
                })
            persona = _persona_nueva(cat, nombre, hoy)
            identificador = persona["id"]
            mp[identificador] = persona
            res["altas"].append({"id": identificador, "nombre": nombre})
            res["avisos_lote"].append({"codigo": "alta_nueva", "detalle": nombre})
            cambio_cat = True
        elif identificador is not None and modo == "anterior":
            res["avisos_lote"].append({
                "codigo": "nombre_anterior_usado",
                "detalle": f"{nombre} -> {mp[identificador]['nombre']}",
            })
        if identificador is None:
            res["horarios_preferidos"].append({"nombre": nombre, "id": None, "accion": "sin_cambios"})
            continue
        persona = mp[identificador]
        nuevo = {d: _num(horario[d]) for d in DIAS if d in horario} if horario else None
        actual = persona.get("horario_preferido") or None
        if nuevo == actual:
            accion = "sin_cambios"
        else:
            if nuevo is None:
                persona.pop("horario_preferido", None)
                accion = "quitada"
                accion_traza = "horario_preferido_quitado"
            else:
                persona["horario_preferido"] = nuevo
                accion = "fijada"
                accion_traza = "horario_preferido"
            cambio_cat = True
            tr = _traza_base(ts, oid, accion_traza, lote.get("dispositivo"))
            tr.update({"id": identificador, "nombre": persona["nombre"]})
            trazas.append(tr)
        res["horarios_preferidos"].append({"nombre": persona["nombre"], "id": identificador, "accion": accion})

    # Paso 2e: bajas de trabajadores en la base (se marcan inactivos sin borrar su id para conservar el historial).
    for original in lote.get("bajas", []):
        nombre = limpiar_nombre(original)
        identificador, modo, mp = _buscar_nombre(nombre, cat)
        if identificador is None:
            res["avisos_lote"].append({"codigo": "baja_sin_persona", "detalle": nombre})
            res["bajas"].append({"nombre": nombre, "id": None, "accion": "sin_persona"})
            continue
        persona = mp[identificador]
        if modo == "anterior":
            res["avisos_lote"].append({
                "codigo": "nombre_anterior_usado",
                "detalle": f"{nombre} -> {persona['nombre']}",
            })
        if persona.get("activo") is False:
            accion = "sin_cambios"
        else:
            persona["activo"] = False
            accion = "baja"
            cambio_cat = True
            tr = _traza_base(ts, oid, "baja_persona", lote.get("dispositivo"))
            tr.update({"id": identificador, "nombre": persona["nombre"]})
            trazas.append(tr)
        res["bajas"].append({"nombre": persona["nombre"], "id": identificador, "accion": accion})

    # Paso 3: normaliza cada jornada y cuenta repeticiones de clave dentro del propio lote.
    normas = []
    repetidas = Counter()
    for entrada in lote["jornadas"]:
        normal, errores = _norm(entrada)
        normas.append((normal, errores))
        if normal and normal["ambito"] in ("vivienda", "garaje") and _date(normal["fecha"]):
            repetidas[(normal["ambito"], normal["fecha"])] += 1
    hoy_fecha = dt.date.fromisoformat(hoy)
    # Procesa las jornadas en orden; cada una ve las altas y cambios de las anteriores.
    for normal, errores_originales in normas:
        errores = list(errores_originales)
        ambito = normal["ambito"] if normal else None
        fecha = normal["fecha"] if normal else None
        clave = [oid, ambito, fecha]
        # Rechaza si el mismo ámbito y fecha vienen repetidos dentro del propio lote.
        if normal and repetidas[(ambito, fecha)] > 1:
            errores.append("jornada_repetida_en_lote")
        errores = list(dict.fromkeys(errores))
        # Rechazo de jornada individual: descarta la fila errónea sin detener el resto del lote.
        if errores:
            res["ok"] = False
            res["jornadas"].append({
                "clave": clave, "estado": "rechazada", "accion": None,
                "rechazos": errores, "avisos": [],
            })
            continue
        temporal = copy.deepcopy(cat)
        mp, actuales, anteriores = _indices_nombres(temporal)
        avisos = []
        altas = []
        presentes = []
        for p in normal["presentes"]:
            # Resuelve por nombre actual y, si no, por nombre anterior; solo si no existe se crea una persona
            # nueva (y se busca si se parece a otra).
            identificador = actuales.get(p["clave"])
            antiguo = identificador is None and p["clave"] in anteriores
            if antiguo:
                identificador = anteriores[p["clave"]]
            if identificador is None:
                parecido = next((
                    q for q in temporal["trabajadores"]
                    if _similar(p["clave"], clave_nombre(q["nombre"]))
                ), None)
                if parecido:
                    avisos.append({
                        "codigo": "nombre_parecido",
                        "detalle": p["nombre"] + " ~ " + parecido["nombre"],
                    })
                persona = _persona_nueva(temporal, p["nombre"], hoy)
                identificador = persona["id"]
                mp[identificador] = persona
                actuales[p["clave"]] = identificador
                altas.append({"id": identificador, "nombre": p["nombre"]})
                avisos.append({"codigo": "alta_nueva", "detalle": p["nombre"]})
            elif antiguo:
                avisos.append({
                    "codigo": "nombre_anterior_usado",
                    "detalle": f"{p['nombre']} -> {mp[identificador]['nombre']}",
                })
            presentes.append({"id": identificador, "horas": p["horas"], "extra": p["extra"]})
        # Dos nombres que resuelven a la misma persona (p. ej. el nuevo y el antiguo): jornada rechazada.
        if len(presentes) != len({p["id"] for p in presentes}):
            res["ok"] = False
            res["jornadas"].append({
                "clave": clave, "estado": "rechazada", "accion": None,
                "rechazos": ["presente_duplicado"], "avisos": [],
            })
            continue
        previa = next((
            j for j in od["jornadas"]
            if j.get("fecha") == fecha and j.get("ambito") == ambito
        ), None)
        # Horas del día por persona entre todas las obras, sin contar la jornada que esta sustituye.
        totales = {p["id"]: p["horas"] for p in presentes}
        for otra in ods.values():
            for j in otra.get("jornadas", []):
                if j.get("fecha") != fecha or j.get("anulada") or (otra is od and j is previa):
                    continue
                for p in j.get("presentes", []):
                    vigente = _resolve(p["id"], mp)
                    totales[vigente] = totales.get(vigente, 0) + p["horas"]
        # Rechaza la jornada si alguien supera 24 h en el día entre todas las obras: es imposible.
        if any(h > 24 for h in totales.values()):
            res["ok"] = False
            res["jornadas"].append({
                "clave": clave, "estado": "rechazada", "accion": None,
                "rechazos": ["suma_diaria_invalida"], "avisos": [],
            })
            continue
        # Aviso si alguien suma más de 12 h el mismo día (con sus nombres) o si la fecha aún no ha llegado.
        altos = sorted(mp[i]["nombre"] for i, horas in totales.items() if horas > 12)
        if altos:
            avisos.append({"codigo": "suma_diaria_alta", "detalle": ", ".join(altos)})
        if dt.date.fromisoformat(fecha) > hoy_fecha:
            avisos.append({"codigo": "fecha_futura", "detalle": fecha})
        nueva = {
            "fecha": fecha, "ambito": ambito, "anulada": normal["anulada"],
            "notas": normal["notas"], "presentes": sorted(presentes, key=lambda p: p["id"]),
            "registrado": normal["registrado"] if normal["registrado"] is not None else ts,
            "origen": "movil",
        }
        # Idempotencia: si el contenido es idéntico a lo guardado no se reescribe ni deja traza.
        if previa and _content(previa) == _content(nueva):
            accion = "sin_cambios"
        elif normal["anulada"]:
            accion = "anulacion"
        elif previa:
            accion = "reemplazo"
            avisos.append({"codigo": "reemplazo", "detalle": None})
        else:
            accion = "alta"
        # Aplica los cambios en memoria y anota la traza solo si la jornada aporta novedades efectivas.
        if accion != "sin_cambios":
            cat = temporal
            res["altas"] += altas
            cambio_cat |= bool(altas)
            cambio_obra = True
            if previa:
                od["jornadas"][od["jornadas"].index(previa)] = nueva
            else:
                od["jornadas"].append(nueva)
            trazas.append({
                "ts": ts, "obra": oid, "ambito": ambito, "fecha": fecha,
                "accion": accion, "n_presentes": len(presentes),
                "avisos": [x["codigo"] for x in avisos],
                "dispositivo": lote.get("dispositivo"),
            })
        res["jornadas"].append({
            "clave": clave, "estado": "aceptada", "accion": accion,
            "rechazos": [], "avisos": avisos,
        })

    # Paso 4: actualiza el horario semanal de la obra si viene en el lote y es distinto del actual.
    if "horario_semanal" in lote and lote["horario_semanal"] != od["horario_semanal"]:
        od["horario_semanal"] = {dia: _num(lote["horario_semanal"][dia]) for dia in DIAS}
        cambio_obra = True
        trazas.append(_traza_base(ts, oid, "horario", lote.get("dispositivo")))

    # Paso 5: horarios propios, una vez resueltas las altas de las jornadas. Se aplican incluso si alguna
    # jornada del lote se rechazó. Un nombre anterior vale; uno desconocido con horario da de alta a la persona.
    mp, actuales, anteriores = _indices_nombres(cat)
    horarios = od.setdefault("excepciones_horario", {})
    for original, horario in lote.get("excepciones_horario", {}).items():
        nombre = limpiar_nombre(original)
        clave_nombre_limpia = clave_nombre(nombre)
        identificador = actuales.get(clave_nombre_limpia)
        if identificador is None and clave_nombre_limpia in anteriores:
            identificador = anteriores[clave_nombre_limpia]
            res["avisos_lote"].append({
                "codigo": "nombre_anterior_usado",
                "detalle": f"{nombre} -> {mp[identificador]['nombre']}",
            })
        if identificador is None and horario:
            parecido = next((
                p for p in cat["trabajadores"]
                if _similar(clave_nombre_limpia, clave_nombre(p["nombre"]))
            ), None)
            if parecido:
                res["avisos_lote"].append({
                    "codigo": "nombre_parecido", "detalle": nombre + " ~ " + parecido["nombre"],
                })
            persona = _persona_nueva(cat, nombre, hoy)
            identificador = persona["id"]
            mp[identificador] = persona
            actuales[clave_nombre_limpia] = identificador
            res["altas"].append({"id": identificador, "nombre": nombre})
            res["avisos_lote"].append({"codigo": "alta_nueva", "detalle": nombre})
            cambio_cat = True
        if identificador is None:
            res["excepciones"].append({"nombre": nombre, "id": None, "accion": "sin_cambios"})
            continue
        # Sustituye por completo el horario propio de la persona por los días indicados en el lote y purga
        # claves antiguas de ids que se fusionaron en ella.
        nuevo = {d: _num(horario[d]) for d in DIAS if d in horario} if horario else None
        viejas = [
            i for i in horarios
            if i != identificador and i in mp and _resolve(i, mp) == identificador
        ]
        if not viejas and ((nuevo is None and horarios.get(identificador) is None)
                           or nuevo == horarios.get(identificador)):
            accion = "sin_cambios"
        else:
            for vieja in viejas:
                del horarios[vieja]
            if nuevo is None:
                horarios.pop(identificador, None)
                accion = "quitada"
                accion_traza = "horario_propio_quitado"
            else:
                horarios[identificador] = nuevo
                accion = "fijada"
                accion_traza = "horario_propio"
            cambio_obra = True
            tr = _traza_base(ts, oid, accion_traza, lote.get("dispositivo"))
            tr["id"] = identificador
            trazas.append(tr)
        res["excepciones"].append({"nombre": nombre, "id": identificador, "accion": accion})

    # Recepción del fichero: si el SHA256 aún no consta en la traza de la obra, una última línea `recibido`
    # lo anota (aunque no cambie ningún dato) y es lo que evita aplicar dos veces el mismo fichero.
    sha_nuevo = sha256 is not None
    if estado is None and sha_nuevo:
        sha_nuevo = sha256 not in shas_recibidos(raiz, obras, oid)
    if sha_nuevo:
        codigos = []
        avisos = res["avisos_lote"] + [a for j in res["jornadas"] for a in j["avisos"]]
        for aviso in avisos:
            if aviso["codigo"] not in codigos:
                codigos.append(aviso["codigo"])
        tr = _traza_base(ts, oid, "recibido", lote.get("dispositivo"))
        tr["avisos"] = codigos
        tr["rechazadas"] = sum(j["estado"] == "rechazada" for j in res["jornadas"])
        trazas.append(tr)
        res["recibido"] = True
    if sha256 is not None:
        for tr in trazas:
            tr["sha256"] = sha256
            if isinstance(fichero, str):
                tr["fichero"] = fichero
    # En memoria: el estado recibe el resultado y no se toca el disco.
    if estado is not None:
        estado["cat"] = cat
        estado["ods"] = ods
        return res
    # Paso 6: persiste atómicamente catálogo y obra solo si se pidió y hubo algo que guardar.
    if escribir and (cambio_cat or cambio_obra or trazas):
        if cambio_cat:
            guardar_catalogo(raiz, cat)
        if cambio_obra:
            _saveobra(raiz, obras, oid, od)
        res["escrito"] = True
        try:
            # Añade la traza a `personal_jornadas.jsonl`. Si falla, lo ya guardado se mantiene y solo se avisa
            # (`traza_no_escrita`).
            ruta = _rop(raiz, obras, oid, "personal_jornadas.jsonl")
            ruta.parent.mkdir(parents=True, exist_ok=True)
            with open(ruta, "ab") as salida:
                for tr in trazas:
                    salida.write((json.dumps(tr, ensure_ascii=False) + "\n").encode())
        except Exception as error:
            res["avisos_lote"].append({"codigo": "traza_no_escrita", "detalle": str(error)})
    return res


def _maps(c):
    """Crea índices de trabajadores y resoluciones de fusión.
    Devuelve el diccionario de catálogo y el de destinos.
    """
    mp = {t["id"]: t for t in c["trabajadores"]}
    return mp, {i: _resolve(i, mp) for i in mp}


def cargar_estado(raiz, obras):
    """Carga copias profundas del catálogo y de todas las obras: un estado en memoria para simular."""
    return {
        "cat": copy.deepcopy(cargar_catalogo(raiz)),
        "ods": {o: copy.deepcopy(cargar_obra(raiz, obras, o)) for o in obras},
    }


def shas_recibidos(raiz, obras, obra):
    """Huellas SHA256 de los ficheros ya recibidos que constan en la traza de una obra.
    Sin traza devuelve un conjunto vacío; si no se puede leer, la excepción sube.
    """
    ruta = _rop(raiz, obras, obra, "personal_jornadas.jsonl")
    if not ruta.exists():
        return set()
    resultado = set()
    with open(ruta, encoding="utf-8") as entrada:
        for linea in entrada:
            try:
                dato = json.loads(linea)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(dato, dict) and isinstance(dato.get("sha256"), str):
                resultado.add(dato["sha256"])
    return resultado


def alta_obra(raiz, obras, obra, escribir=False):
    """Crea el `personal_obra.json` base de una obra del registro si todavía no existe (solo con escribir)."""
    if obra not in obras:
        raise ValueError("obra inexistente")
    ruta = _rop(raiz, obras, obra)
    falta = not ruta.exists()
    creada = falta and escribir
    if creada:
        _saveobra(raiz, obras, obra, cargar_obra(raiz, obras, obra))
    if creada:
        motivo = "creada"
    elif falta:
        motivo = "vista_previa"
    else:
        motivo = "ya_existia"
    return {"creada": creada, "ruta": str(ruta), "motivo": motivo}


def _obras_de_persona(raiz, obras, identificador, catalogo):
    """Obras en las que consta una persona (en jornadas u horarios propios), siguiendo fusiones."""
    mp = {t["id"]: t for t in catalogo["trabajadores"]}
    destino = _resolve(identificador, mp)
    resultado = []
    for obra in obras:
        datos = cargar_obra(raiz, obras, obra)
        ids = [p.get("id") for j in datos.get("jornadas", []) for p in j.get("presentes", [])]
        ids += list(datos.get("excepciones_horario", {}))
        if any(i in mp and _resolve(i, mp) == destino for i in ids):
            resultado.append(obra)
    return sorted(resultado)


def renombrar(raiz, obras, quien, nuevo, escribir=False, ahora=None):
    """Cambia el nombre de una persona (por id o por nombre): vista previa o, con escribir, de verdad."""
    base = {
        "ok": False, "error": None, "id": None, "id_otro": None, "orden": None,
        "de": quien, "a": limpiar_nombre(nuevo), "accion": None, "avisos": [],
        "escrito": False, "trazas_en": [],
    }
    if not nombre_publicable(nuevo):
        base["error"] = "nombre_invalido"
        return base
    catalogo = copy.deepcopy(cargar_catalogo(raiz))
    mp = {t["id"]: t for t in catalogo["trabajadores"]}
    es_id = isinstance(quien, str) and re.fullmatch(r"T\d{4,}", quien) is not None
    if es_id:
        cambio = _aplicar_renombre(catalogo, mp.get(quien, {}).get("nombre", ""),
                                   limpiar_nombre(nuevo), quien, True)
    else:
        cambio = _aplicar_renombre(catalogo, limpiar_nombre(quien), limpiar_nombre(nuevo))
    if cambio.get("error"):
        base.update({"error": cambio["error"], "id": cambio.get("id"),
                     "id_otro": cambio.get("id_otro")})
        if cambio["error"] == "coincide_con_otro":
            base["orden"] = f"personal_obra.py fusionar {cambio['id']} {cambio['id_otro']}"
        return base
    base.update({"ok": True, "id": cambio["id"], "accion": cambio["accion"],
                 "de": cambio["de_actual"]})
    if cambio["uso_anterior"]:
        detalle = f"{limpiar_nombre(quien)} -> {cambio['de_actual']}"
        base["avisos"].append({"codigo": "nombre_anterior_usado", "detalle": detalle})
    base["trazas_en"] = _obras_de_persona(raiz, obras, cambio["id"], catalogo)
    if escribir and cambio["accion"] == "renombrado":
        guardar_catalogo(raiz, catalogo)
        for obra in base["trazas_en"]:
            traza = _traza_base(ahora or _now(), obra, "renombre")
            traza.update({"id": cambio["id"], "de": cambio["de_actual"], "a": limpiar_nombre(nuevo)})
            ruta = _rop(raiz, obras, obra, "personal_jornadas.jsonl")
            ruta.parent.mkdir(parents=True, exist_ok=True)
            with open(ruta, "ab") as salida:
                salida.write((json.dumps(traza, ensure_ascii=False) + "\n").encode())
        base["escrito"] = True
    return base


def poner_empresa(raiz, obras, quien, empresa, escribir=False, ahora=None):
    """Pone (o quita, con la empresa vacía) la empresa de una persona, por id o por nombre.
    Vista previa o, con escribir, de verdad: guarda la base y deja una línea de registro en cada obra de la persona.
    """
    base = {
        "ok": False, "error": None, "id": None, "nombre": quien, "accion": None, "antes": "",
        "despues": limpiar_nombre(empresa), "avisos": [], "escrito": False, "trazas_en": [],
    }
    if not empresa_valida(empresa):
        base["error"] = "empresa_invalida"
        return base
    catalogo = copy.deepcopy(cargar_catalogo(raiz))
    mp = {t["id"]: t for t in catalogo["trabajadores"]}
    if isinstance(quien, str) and re.fullmatch(r"T\d{4,}", quien) is not None:
        identificador = _resolve(quien, mp) if quien in mp else None
        modo = "actual"
    else:
        identificador, modo, mp = _buscar_nombre(limpiar_nombre(quien), catalogo)
    if identificador is None:
        base["error"] = "persona_inexistente"
        return base
    persona = mp[identificador]
    cambio = _aplicar_empresa(catalogo, persona, empresa)
    base.update({
        "ok": True, "id": identificador, "nombre": persona["nombre"], "accion": cambio["accion"],
        "antes": cambio["antes"], "despues": cambio["despues"],
    })
    if modo == "anterior":
        base["avisos"].append({
            "codigo": "nombre_anterior_usado", "detalle": f"{limpiar_nombre(quien)} -> {persona['nombre']}",
        })
    base["trazas_en"] = _obras_de_persona(raiz, obras, identificador, catalogo)
    if escribir and cambio["accion"] != "sin_cambios":
        guardar_catalogo(raiz, catalogo)
        for obra in base["trazas_en"]:
            traza = _traza_base(ahora or _now(), obra, "empresa")
            traza.update({
                "id": identificador, "nombre": persona["nombre"], "de": cambio["antes"], "a": cambio["despues"],
            })
            ruta = _rop(raiz, obras, obra, "personal_jornadas.jsonl")
            ruta.parent.mkdir(parents=True, exist_ok=True)
            with open(ruta, "ab") as salida:
                salida.write((json.dumps(traza, ensure_ascii=False) + "\n").encode())
        base["escrito"] = True
    return base


# La empresa que va escrita dentro del nombre: «Alejo (Manueles)» o «Javi @ CATERSYSTEM».
_EMPRESA_EN_PARENTESIS = re.compile(r"^(?P<nombre>.*?)\s*\(\s*(?P<empresa>[^()]*?)\s*\)$")
_EMPRESA_CON_ARROBA = re.compile(r"^(?P<nombre>.*?)\s*@\s*(?P<empresa>.*)$")


def _partir_empresa(nombre):
    """Separa «Alejo (Manueles)» en ("Alejo", "Manueles") y «Javi @ CATERSYSTEM» en ("Javi", "CATERSYSTEM").
    Devuelve None si el nombre no lleva ninguna empresa dentro.
    """
    texto = limpiar_nombre(nombre)
    for patron in (_EMPRESA_EN_PARENTESIS, _EMPRESA_CON_ARROBA):
        encontrado = patron.match(texto)
        if encontrado:
            return limpiar_nombre(encontrado.group("nombre")), limpiar_nombre(encontrado.group("empresa"))
    return None


def _motivo_que_para(persona, limpio, empresa, repetidos):
    """Por qué un nombre con empresa dentro NO se puede separar solo: (código, detalle) o None si se puede."""
    if not limpio:
        return "nombre_vacio", None
    if not any(c.isalpha() for c in empresa):
        return "sin_letras", empresa
    if es_autonomo(empresa) or clave_nombre(empresa) == "aut":
        return "sufijo_aut", empresa
    if not nombre_publicable(limpio) or not empresa_valida(empresa):
        return "no_vale", None
    if repetidos[clave_nombre(limpio)] > 1:
        return "mismo_nombre", limpio
    propia = limpiar_nombre(persona.get("empresa"))
    if propia and clave_nombre(propia) != clave_nombre(empresa):
        return "ya_tiene_empresa", propia
    return None


def texto_separar(codigo, nombre, detalle=None):
    """Frase en lenguaje llano de por qué un nombre con empresa dentro se deja sin tocar."""
    if codigo == "nombre_vacio":
        return f"«{nombre}»: quitando la empresa no quedaría ningún nombre."
    if codigo == "sin_letras":
        return f"«{nombre}»: lo que acompaña al nombre no parece una empresa. No se toca."
    if codigo == "sufijo_aut":
        return (f"«{nombre}»: acaba en «@AUT», que marca a un autónomo. ¿Es una persona con la empresa "
                f"«{detalle}»? Dímelo con este caso delante.")
    if codigo == "no_vale":
        return f"«{nombre}»: la parte del nombre o la de la empresa no vale (vacía, muy larga o con signos raros)."
    if codigo == "mismo_nombre":
        return f"«{nombre}»: otra persona de la lista quedaría también como «{detalle}». ¿Son la misma persona?"
    if codigo == "ya_tiene_empresa":
        return f"«{nombre}» ya tiene la empresa «{detalle}»: una persona solo puede tener una."
    if codigo == "coincide_con_otro":
        return (f"«{nombre}»: ya hay otro «{detalle}» en la base. "
                "Si son la misma persona hay que juntarlas antes.")
    return f"«{nombre}»: no se puede separar la empresa."


def separar_empresas(raiz, obras, aplicar=False, ahora=None):
    """Separa la empresa escrita dentro del nombre («Alejo (Manueles)» -> «Alejo», empresa «Manueles»).
    Sin `aplicar` es una vista previa; con `aplicar` renombra a la persona y le pone la empresa, sin tocar jornadas.
    Lo dudoso sale en `paran` y no se aplica nunca. Devuelve propuestas, paran, aplicadas, errores y escrito.
    """
    trabajo = copy.deepcopy(cargar_catalogo(raiz))
    candidatas = []
    sin_empresa = 0
    for persona in trabajo["trabajadores"]:
        if persona.get("fusionado_en") is not None:
            continue
        partes = _partir_empresa(persona.get("nombre"))
        if partes is None:
            sin_empresa += 1
        else:
            candidatas.append((persona, partes[0], partes[1]))
    repetidos = Counter(clave_nombre(limpio) for _, limpio, _ in candidatas)
    res = {
        "propuestas": [], "paran": [], "sin_empresa_en_el_nombre": sin_empresa,
        "aplicadas": [], "errores": [], "escrito": False,
    }

    def parar(persona, codigo, detalle=None, extra=None):
        """Anota una persona que NO se separa (con su frase en llano) en `paran`."""
        item = {"id": persona["id"], "de": persona["nombre"], "motivo": codigo, "detalle": detalle}
        item["texto"] = texto_separar(codigo, persona["nombre"], detalle)
        item.update(extra or {})
        res["paran"].append(item)

    # Cada propuesta se prueba sobre la copia, en orden, igual que se aplicará: lo que se enseña es lo que pasa.
    for persona, limpio, empresa in candidatas:
        motivo = _motivo_que_para(persona, limpio, empresa, repetidos)
        if motivo:
            parar(persona, *motivo)
            continue
        original = persona["nombre"]
        cambio = _aplicar_renombre(trabajo, original, limpio, persona["id"])
        if cambio.get("error") == "coincide_con_otro":
            otro = {t["id"]: t for t in trabajo["trabajadores"]}[cambio["id_otro"]]
            orden = f"personal_obra.py fusionar {persona['id']} {otro['id']}"
            parar(persona, "coincide_con_otro", otro["nombre"], {"orden": orden})
            continue
        puesta = _aplicar_empresa(trabajo, persona, empresa)
        res["propuestas"].append({
            "id": persona["id"], "de": original, "nombre": persona["nombre"], "empresa": persona.get("empresa", ""),
            "accion": puesta["accion"],
        })
    if not aplicar:
        return res
    for propuesta in res["propuestas"]:
        cambio_nombre = renombrar(raiz, obras, propuesta["id"], propuesta["nombre"], escribir=True, ahora=ahora)
        if not cambio_nombre["ok"]:
            res["errores"].append({"id": propuesta["id"], "error": cambio_nombre["error"]})
            break
        cambio_empresa = poner_empresa(raiz, obras, propuesta["id"], propuesta["empresa"], escribir=True, ahora=ahora)
        if not cambio_empresa["ok"]:
            res["errores"].append({"id": propuesta["id"], "error": cambio_empresa["error"]})
            break
        res["aplicadas"].append(propuesta["id"])
        res["escrito"] = True
    return res


def ultima_jornada(raiz, obras, obra, ambito):
    """Obtiene la última jornada no anulada por obra y ámbito.
    Devuelve la fecha y presentes con nombres canónicos.
    """
    js = [j for j in cargar_obra(raiz, obras, obra)["jornadas"] if j["ambito"] == ambito and not j["anulada"]]
    if not js:
        return None
    j = max(js, key=lambda x: x["fecha"])
    mp, rs = _maps(cargar_catalogo(raiz))
    ps = [
        {"nombre": mp[rs[p["id"]]]["nombre"], "horas": p["horas"], "extra": p.get("extra", 0)}
        for p in sorted(j["presentes"], key=lambda x: x["id"])
    ]
    return {"fecha": j["fecha"], "presentes": ps}


def fusionar(raiz, origen, destino, escribir=False, ahora=None):
    """Fusiona un trabajador origen en uno de destino.
    Comprueba que no coincidan en jornadas ni horarios.
    """
    c = cargar_catalogo(raiz)
    mp = {t["id"]: t for t in c["trabajadores"]}
    if origen not in mp or destino not in mp:
        return {"ok": False, "error": "id_inexistente", "escrito": False}
    if origen == destino:
        return {"ok": False, "error": "mismo_id", "escrito": False}
    # Evita cadenas transitivas o ciclos impidiendo fusionar trabajadores ya fusionados.
    if mp[origen].get("fusionado_en") is not None:
        return {"ok": False, "error": "origen_ya_fusionado", "escrito": False}
    if mp[destino].get("fusionado_en") is not None:
        return {"ok": False, "error": "destino_fusionado", "escrito": False}
    # Comprueba en todas las obras que origen y destino no coincidan en la misma jornada ni horario.
    # Las archivadas (cerrar_obra.py las deja en «SAGARDE (OLD)/OBRAS CERRADAS», al lado de la raíz)
    # cuentan igual: sus jornadas siguen en el ranking y una persona no puede sumar dos veces un día.
    rutas = list(Path(raiz).glob("*/INFORME SAGARDE IA/personal_obra.json"))
    rutas += sorted(
        (Path(raiz).parent / "SAGARDE (OLD)" / "OBRAS CERRADAS").glob("*/INFORME SAGARDE IA/personal_obra.json")
    )
    for p in rutas:
        try:
            d = _read(p)
        except Exception:
            continue
        for j in d.get("jornadas", []):
            ids = [
                destino if x.get("id") == origen else _resolve(x.get("id"), mp)
                for x in j.get("presentes", [])
            ]
            if len(ids) != len(set(ids)):
                return {"ok": False, "error": "conflicto_en_jornada", "escrito": False}
        # Compara el horario efectivo de ambos antes de fusionar.
        ex = d.get("excepciones_horario", {})
        if isinstance(ex, dict):

            def efectivo(i):
                """Obtiene el horario propio efectivo de un id.
                Resuelve restos de fusiones si no tiene directo.
                """
                if i in ex:
                    return ex[i]
                # Si el id vigente no tiene horario propio directo busca restos de ids fusionados en
                # él.
                restos = [x for x in ex if x in mp and _resolve(x, mp) == i]
                return ex[min(restos)] if restos else None

            eo, ed = efectivo(origen), efectivo(destino)
            if eo is not None and ed is not None and eo != ed:
                return {"ok": False, "error": "conflicto_en_horario_propio", "escrito": False}
    # Apunta el origen al destino para que las consultas y cálculos resuelvan su identidad canónica.
    mp[origen]["fusionado_en"] = destino
    if escribir:
        guardar_catalogo(raiz, c)
    return {"ok": True, "error": None, "escrito": bool(escribir)}


def aplanar(raiz, obras, obra, estado=None):
    """Convierte jornadas activas en filas planas de cálculo (con la empresa de la persona, si la tiene).
    Ordena el resultado por fecha, ámbito y trabajador.
    """
    catalogo = estado["cat"] if estado is not None else cargar_catalogo(raiz)
    datos_obra = estado["ods"][obra] if estado is not None else cargar_obra(raiz, obras, obra)
    mp, rs = _maps(catalogo)
    out = []
    # Filtra jornadas anuladas y proyecta cada presente en una fila plana con su nombre resuelto.
    for j in datos_obra["jornadas"]:
        if j["anulada"]:
            continue
        for p in j["presentes"]:
            persona = mp[rs[p["id"]]]
            fila = {
                "fecha": j["fecha"],
                "ambito": j["ambito"],
                "nombre": persona["nombre"],
                "horas": p["horas"],
                "extra": p.get("extra", 0),
            }
            # La empresa va en la fila solo si la persona la tiene: «sin empresa» es no tener la clave, y así
            # lo que se publica de quien no usa empresas no cambia ni un byte.
            empresa = limpiar_nombre(persona.get("empresa"))
            if empresa:
                fila["empresa"] = empresa
            out.append(fila)
    return sorted(out, key=lambda x: (x["fecha"], x["ambito"], x["nombre"]))


def totales_control(raiz, obras, obra=None, estado=None):
    """Calcula totales independientes de horas, días y extra.
    Devuelve None si no hay filas para no falsear datos.
    """
    fs = (
        aplanar(raiz, obras, obra, estado)
        if obra is not None
        else [x for o in obras for x in aplanar(raiz, obras, o, estado)]
    )
    # Si no hay jornadas devuelve None (nunca ceros) para distinguir ausencia de datos de ceros
    # reales.
    if not fs:
        return None
    h = e = 0
    ds = set()
    ns = set()
    por = {}
    pds = {}
    for x in fs:
        n = x["nombre"]
        h += x["horas"]
        e += x["extra"]
        ds.add(x["fecha"])
        ns.add(n)
        if n not in por:
            por[n] = {"horas": 0, "extra": 0, "dias": 0}
            pds[n] = set()
        por[n]["horas"] += x["horas"]
        por[n]["extra"] += x["extra"]
        pds[n].add(x["fecha"])
        por[n]["dias"] = len(pds[n])
    return {"horas": h, "extra": e, "dias": len(ds), "trabajadores": len(ns), "por_trabajador": por}


def exportar_estado(
    raiz, obras, nombres_obra=None, cerradas=(), generado=None, escribir=False, incluir_vacias=False
):
    """Genera personal_estado.js con el estado para la app: catálogo activo, últimas jornadas y filas.
    Con `incluir_vacias` también salen las obras que aún no tienen `personal_obra.json` (sin jornadas).
    """
    c = cargar_catalogo(raiz)
    mp, rs = _maps(c)
    ordenados = sorted(c["trabajadores"], key=lambda x: x["id"])
    # Quién se juntó con quién: los nombres de las fichas fusionadas, agrupados por la persona que sigue vigente.
    juntados = {}
    for t in ordenados:
        if t.get("fusionado_en") is not None:
            juntados.setdefault(rs[t["id"]], []).append(t["nombre"])
    # Solo se exportan las identidades vigentes: los trabajadores fusionados en otro no aparecen como personas.
    cats = []
    for t in ordenados:
        if t.get("fusionado_en") is not None:
            continue
        ficha = {k: t[k] for k in ("id", "nombre", "categoria", "empresa", "activo")}
        # El historial de nombres (renombres y fusiones) solo sale si lo hay: quien nunca cambió de nombre se publica
        # igual que antes, y la tablet (que lee este mismo fichero) ignora las claves que no conoce.
        if t.get("nombres_anteriores"):
            ficha["nombres_anteriores"] = list(t["nombres_anteriores"])
        if juntados.get(t["id"]):
            ficha["fusionados"] = juntados[t["id"]]
        if t.get("horario_preferido"):
            ficha["horario_preferido"] = {d: t["horario_preferido"][d] for d in DIAS if d in t["horario_preferido"]}
        cats.append(ficha)
    obs = {}
    for o in obras:
        # Por defecto solo salen las obras con datos; la tablet necesita ofrecerlas todas (`incluir_vacias`).
        if not incluir_vacias and not _rop(raiz, obras, o).exists():
            continue
        d = cargar_obra(raiz, obras, o)
        ex = {}
        # Conserva el id menor, salvo que aparezca el horario del destino.
        # Traduce identificadores a nombres canónicos preservando el horario propio asignado al
        # destino.
        for i in sorted(d["excepciones_horario"]):
            destino = rs.get(i, i)
            if destino not in mp:
                continue
            nombre = mp[destino]["nombre"]
            if nombre not in ex or i == destino:
                ex[nombre] = d["excepciones_horario"][i]
        obs[o] = {
            "nombre": (nombres_obra or {}).get(o, o),
            "cerrada": o in cerradas,
            "horario_semanal": d["horario_semanal"],
            "excepciones_horario": ex,
            "ultima": {
                "vivienda": ultima_jornada(raiz, obras, o, "vivienda"),
                "garaje": ultima_jornada(raiz, obras, o, "garaje"),
            },
            "jornadas": aplanar(raiz, obras, o),
        }
    data = {
        "version": 1,
        "generado": generado or _now(),
        "jornada_base_h": 7.5,
        "catalogo": cats,
        "obras": obs,
    }
    s = "window.SAGARDE_PERSONAL = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n"
    if escribir:
        _atomic(_sis(raiz, "personal_estado.js"), s.encode())
    return s


def comprobar(raiz, obras):
    """Audita la integridad de catálogo y obras de Sagarde.
    Devuelve lista de incoherencias o vacía si es válido.
    """
    out = []
    pc = _sis(raiz, "personal_catalogo.json")
    try:
        c = cargar_catalogo(raiz)
    except Exception as e:
        return [f"{pc}: JSON ilegible ({e})"]
    if set(c) - CK:
        out.append(f"{pc}: claves fuera del esquema")
    ts = c.get("trabajadores", [])
    ids = {t.get("id") for t in ts if isinstance(t, dict)}
    mp = {t.get("id"): t for t in ts if isinstance(t, dict)}
    ks = Counter()
    for t in ts:
        if not isinstance(t, dict) or set(t) - TK:
            out.append(f"{pc}: trabajador con claves fuera del esquema")
            continue
        # Verifica que no haya nombres repetidos entre los trabajadores no fusionados y que los
        # enlaces de fusión sean válidos.
        if t.get("fusionado_en") is None:
            ks[clave_nombre(t.get("nombre"))] += 1
        elif t["fusionado_en"] not in ids or mp[t["fusionado_en"]].get("fusionado_en") is not None:
            out.append(f"{pc}: fusionado_en inválido")
        if "nombres_anteriores" in t:
            anteriores = t["nombres_anteriores"]
            validos = isinstance(anteriores, list) and all(
                isinstance(nombre, str) and nombre_publicable(nombre) for nombre in anteriores
            )
            claves_anteriores = [clave_nombre(nombre) for nombre in anteriores] if validos else []
            if (
                not validos
                or len(claves_anteriores) != len(set(claves_anteriores))
                or clave_nombre(t.get("nombre")) in claves_anteriores
            ):
                out.append(f"{pc}: nombres_anteriores invalidos")
        if t.get("empresa") is not None and not empresa_valida(t["empresa"]):
            out.append(f"{pc}: empresa invalida")
        if "horario_preferido" in t and t["horario_preferido"] is not None:
            hp = t["horario_preferido"]
            if (
                not isinstance(hp, dict)
                or any(dia not in DIAS for dia in hp)
                or any(_num(h) is None for h in hp.values())
            ):
                out.append(f"{pc}: horario_preferido invalido")
    if any(v > 1 for v in ks.values()):
        out.append(f"{pc}: nombres no fusionados duplicados")
    for o in obras:
        p = _rop(raiz, obras, o)
        if not p.exists():
            continue
        try:
            d = _read(p)
        except Exception as e:
            out.append(f"{p}: JSON ilegible ({e})")
            continue
        if set(d) - OK:
            out.append(f"{p}: claves fuera del esquema de obra")
        if d.get("obra") != o:
            out.append(f"{p}: obra distinta de {o}")
        # Comprueba que los horarios propios sean seguros y referencien el catálogo.
        ex = d.get("excepciones_horario")
        if not isinstance(ex, dict):
            out.append(f"{p}: excepciones_horario no es un diccionario")
        else:
            for i, horario in ex.items():
                if i not in ids:
                    out.append(f"{p}: id inexistente {i}")
                if not isinstance(horario, dict):
                    out.append(f"{p}: horario propio invalido {i}")
                    continue
                if any(dia not in DIAS for dia in horario) or any(
                    _num(horas) is None for horas in horario.values()
                ):
                    out.append(f"{p}: horario propio invalido {i}")
        seen = set()
        for j in d.get("jornadas", []):
            if not isinstance(j, dict) or set(j) - GJK:
                out.append(f"{p}: jornada con claves fuera del esquema")
                continue
            # Comprueba que la clave única (ámbito y fecha) no se repita en las jornadas de la obra.
            k = (j.get("ambito"), j.get("fecha"))
            if k in seen:
                out.append(f"{p}: jornada repetida {k}")
            seen.add(k)
            if j.get("anulada") is True and j.get("presentes"):
                out.append(f"{p}: jornada anulada con presentes {k}")
            for x in j.get("presentes", []):
                if not isinstance(x, dict) or set(x) - GPK:
                    out.append(f"{p}: presente con claves fuera del esquema")
                    continue
                if x.get("id") not in ids:
                    out.append(f"{p}: id inexistente {x.get('id')}")
                h, e = _num(x.get("horas")), _num(x.get("extra", 0))
                if h is None or e is None or (h is not None and e > h):
                    out.append(f"{p}: horas o extra fuera de rango")
    return out


def texto_aviso(codigo, detalle=None):
    """Frase en lenguaje llano para un código de aviso o de rechazo (nunca se enseña el código)."""
    fijos = {
        "lote_invalido": "El fichero no tiene el formato esperado.",
        "tipo_desconocido": "Este fichero no es un control horario.",
        "version_desconocida": "Este control horario es de una versión que este PC no conoce.",
        "obra_invalida": "La obra que figura en el fichero no existe en Sagarde.",
        "campo_desconocido": "El fichero trae algo que no se esperaba.",
        "horario_invalido": "El horario de la obra viene mal escrito.",
        "excepcion_invalida": "Un horario especial viene mal escrito.",
        "renombre_invalido": "Un cambio de nombre viene mal escrito.",
        "alta_invalida": "Un nombre de la lista de nuevos viene mal escrito.",
        "baja_invalida": "Un nombre de la lista de personas a quitar viene mal escrito.",
        "empresa_invalida": "Una empresa viene mal escrita.",
        "categoria_invalida": "El oficio o categoría viene mal escrito.",
        "horario_preferido_invalido": "Un horario preferido viene mal escrito.",
        "ambito_invalido": "Una jornada no dice si es de viviendas o de garajes.",
        "fecha_invalida": "Una jornada tiene una fecha que no existe.",
        "sin_presentes": "Una jornada no tiene a nadie apuntado.",
        "nombre_vacio": "Hay un trabajador sin nombre.",
        "nombre_invalido": "Hay un nombre que no vale (vacío, demasiado largo o con signos raros).",
        "horas_invalidas": "Hay unas horas que no valen (deben estar entre 0 y 24).",
        "extra_invalido": "Hay unas horas extra que no valen.",
        "presente_duplicado": "Una persona sale dos veces el mismo día.",
        "anulada_con_presentes": "Una jornada anulada no puede llevar gente.",
        "jornada_repetida_en_lote": "El mismo día y el mismo ámbito aparece dos veces en el fichero.",
        "suma_diaria_invalida": "Alguien suma más de 24 horas ese día entre todas las obras.",
        "persona_inexistente": "No hay nadie en la base con ese nombre ni con ese número.",
        "persona_fusionada": "Esa persona ya está juntada con otra: cambia el nombre de la otra.",
        "coincide_con_otro": "Ese nombre ya es de otra persona. Si son la misma persona hay que juntarlas.",
        "reemplazo": "Ya había una jornada de ese día en esa obra: la nueva la sustituye.",
        "traza_no_escrita": "Guardado bien, pero no se pudo anotar en el registro.",
    }
    if codigo in fijos:
        return fijos[codigo]
    if codigo == "alta_nueva":
        if isinstance(detalle, str) and detalle:
            return f"Nombre nuevo: «{detalle}» no estaba en la base; se añade."
        return "Hay un nombre nuevo que no estaba en la base; se añade."
    if codigo == "nombre_parecido":
        if isinstance(detalle, str) and " ~ " in detalle:
            primero, segundo = detalle.split(" ~ ", 1)
            return f"Se parecen: «{primero}» y «{segundo}». ¿Es la misma persona?"
        return "Hay dos nombres que se parecen. ¿Es la misma persona?"
    if codigo == "suma_diaria_alta":
        if not isinstance(detalle, str) or not detalle:
            return "Alguien suma más de 12 horas ese día entre todas las obras."
        verbo = "suman" if "," in detalle else "suma"
        return f"{detalle} {verbo} más de 12 horas ese día entre todas las obras."
    if codigo == "fecha_futura":
        if isinstance(detalle, str) and _date(detalle):
            fecha = dt.date.fromisoformat(detalle)
            return f"La jornada es de una fecha que aún no ha llegado ({fecha:%d/%m}): ¿es una errata?"
        return "La jornada es de una fecha que aún no ha llegado: ¿es una errata?"
    if codigo == "renombre_coincide_con_otro":
        if isinstance(detalle, str) and " -> " in detalle:
            primero, resto = detalle.split(" -> ", 1)
            segundo = resto.split(" (", 1)[0]
            return (f"No se ha cambiado «{primero}»: «{segundo}» ya es otra persona de la base. "
                    "Si son la misma persona hay que juntarlas.")
        return "No se ha cambiado el nombre: ya es de otra persona de la base."
    if codigo == "renombre_sin_origen":
        if isinstance(detalle, str) and detalle:
            return f"«{detalle}» no estaba en la base: no hay nada que cambiar de nombre."
        return "Un nombre que se quería cambiar no estaba en la base: no hay nada que cambiar."
    if codigo == "empresa_sin_persona":
        if isinstance(detalle, str) and detalle:
            return f"«{detalle}» no estaba en la base: no se le puede poner empresa."
        return "Una empresa era para alguien que no estaba en la base: no se ha puesto."
    if codigo == "categoria_sin_persona":
        if isinstance(detalle, str) and detalle:
            return f"«{detalle}» no estaba en la base: no se le puede poner oficio."
        return "Un oficio era para alguien que no estaba en la base: no se ha puesto."
    if codigo == "baja_sin_persona":
        if isinstance(detalle, str) and detalle:
            return f"«{detalle}» no estaba en la base: no hay nadie a quien quitar."
        return "Un nombre que se quería quitar no estaba en la base."
    if codigo == "nombre_anterior_usado":
        if isinstance(detalle, str) and " -> " in detalle:
            anterior, actual = detalle.split(" -> ", 1)
            return (f"«{anterior}» es un nombre antiguo de «{actual}»: "
                    "se ha tomado como la misma persona.")
        return "Se ha reconocido un nombre antiguo como la misma persona."
    return f"Aviso: {codigo}."


def texto_empresa(accion, nombre, antes="", despues=""):
    """Frase en llano de un cambio de empresa: puesta, cambiada o quitada."""
    if accion == "puesta":
        return f"Pone la empresa «{despues}» a «{nombre}»."
    if accion == "cambiada":
        return f"Cambia la empresa de «{nombre}»: de «{antes}» a «{despues}»."
    if accion == "quitada":
        return f"Quita la empresa a «{nombre}» (era «{antes}»)."
    return f"«{nombre}» ya tiene esa empresa: no hay nada que cambiar."


def _cli_obras(x):
    """Devuelve {id_obra: carpeta_obra}: lo indicado en --obras (formato id=carpeta,id=carpeta) o,
    si no se indica,
    el registro de obras (registro_obras.OBRAS).
    """
    if x:
        return dict(v.split("=", 1) for v in x.split(","))
    import registro_obras

    return {o["id"]: o["carpeta_obra"] for o in registro_obras.OBRAS}


def _cli_separar_empresas(raiz, obras, aplicar):
    """Imprime en llano la vista previa (o el resultado) de `separar_empresas`. Devuelve 0 si no hay nada dudoso."""
    r = separar_empresas(raiz, obras, aplicar=aplicar)
    if not aplicar:
        print("Vista previa: todavía no se guarda nada.")
    if not r["propuestas"] and not r["paran"]:
        print("No hay nombres con la empresa dentro: no hay nada que separar.")
    if r["propuestas"]:
        print("Se separaría así:" if not aplicar else "Se ha separado así:")
        for x in r["propuestas"]:
            print(f"  · «{x['de']}» pasa a «{x['nombre']}», empresa «{x['empresa']}»")
    if r["paran"]:
        print("Hay que mirarlos a mano (no se tocan):")
        for x in r["paran"]:
            print("  · " + x["texto"])
            if x.get("orden"):
                print("    Para juntarlas: " + x["orden"])
    for x in r["errores"]:
        print(f"  ✗ No se pudo con {x['id']}: " + texto_aviso(x["error"]))
    n = r["sin_empresa_en_el_nombre"]
    print(("1 persona no lleva" if n == 1 else f"{n} personas no llevan") + " empresa en el nombre: no se toca.")
    if r["propuestas"] and not aplicar:
        print("Para hacerlo de verdad, vuelve a lanzarlo con --aplicar (cuando lo hayas visto).")
    return 0 if not r["paran"] and not r["errores"] else 2


def main(argv=None):
    """Punto de entrada de la línea de comandos (ingerir, fusionar, renombrar, separar-empresas, exportar-estado,
    comprobar). Devuelve 0 si va bien, 2 si hay rechazos o incoherencias y 1 si el uso es erróneo.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)

    def comunes(q):
        """Añade los argumentos comunes a un subcomando CLI.
        Define --raiz, --obras, --hoy y la opción --escribir.
        """
        q.add_argument("--raiz", default=str(Path(__file__).resolve().parent.parent))
        q.add_argument("--obras")
        q.add_argument("--hoy", default=dt.date.today().isoformat())
        q.add_argument("--escribir", action="store_true")

    q = s.add_parser("ingerir")
    q.add_argument("fichero")
    comunes(q)
    q = s.add_parser("fusionar")
    q.add_argument("origen")
    q.add_argument("destino")
    comunes(q)
    q = s.add_parser("renombrar")
    q.add_argument("quien")
    q.add_argument("nuevo")
    comunes(q)
    q = s.add_parser("separar-empresas")
    q.add_argument("--raiz", default=str(Path(__file__).resolve().parent.parent))
    q.add_argument("--obras")
    q.add_argument("--aplicar", action="store_true")
    q = s.add_parser("exportar-estado")
    comunes(q)
    q = s.add_parser("comprobar")
    comunes(q)
    try:
        a = p.parse_args(argv)
        ob = _cli_obras(a.obras)
        if a.cmd == "ingerir":
            try:
                l = _read(a.fichero)
            except Exception as e:
                print("ERROR:", e)
                return 1
            r = ingerir_lote(l, a.raiz, ob, a.hoy, a.escribir)
            for j in r["jornadas"]:
                print(j["estado"].upper(), j["clave"], j["accion"] or j["rechazos"])
                for v in j["avisos"]:
                    print("REVISAR", v["codigo"], v["detalle"])
            for codigo in r["lote_rechazado"]:
                print("RECHAZADO lote", codigo)
            for x in r["excepciones"]:
                print("HORARIO PROPIO", x["nombre"], x["accion"])
            for x in r["empresas"]:
                print("EMPRESA", x["nombre"], x["accion"])
            for v in r["avisos_lote"]:
                print("REVISAR", v["codigo"], v["detalle"])
            return 0 if r["ok"] else 2
        if a.cmd == "fusionar":
            r = fusionar(a.raiz, a.origen, a.destino, a.escribir)
            print("Fusión correcta" if r["ok"] else "ERROR: " + r["error"])
            return 0 if r["ok"] else 2
        if a.cmd == "renombrar":
            r = renombrar(a.raiz, ob, a.quien, a.nuevo, a.escribir)
            if not a.escribir:
                print("Vista previa: todavía no se guarda nada.")
            if r["error"]:
                print(texto_aviso(r["error"]))
                if r["error"] == "coincide_con_otro":
                    print("Para juntarlas: " + r["orden"])
            elif r["accion"] == "sin_cambios":
                print(f"«{r['de']}» ya se llama así: no hay nada que cambiar.")
            else:
                print(f"«{r['de']}» pasa a llamarse «{r['a']}».")
            for aviso in r["avisos"]:
                print(texto_aviso(aviso["codigo"], aviso["detalle"]))
            return 0 if r["ok"] else 2
        if a.cmd == "separar-empresas":
            return _cli_separar_empresas(a.raiz, ob, a.aplicar)
        if a.cmd == "exportar-estado":
            if a.obras:
                exportar_estado(a.raiz, ob, escribir=a.escribir)
            else:
                # Sin --obras es el entorno real: nombres de obra del registro y obras archivadas
                # marcadas `cerrada`. Sin esto el estado saldría con ids por nombre y todo abierto.
                import personal_integracion

                personal_integracion.exportar_estado_real(a.raiz, escribir=a.escribir)
            print("Estado exportado")
            return 0
        z = comprobar(a.raiz, ob)
        for x in z:
            print("REVISAR", x)
        return 0 if not z else 2
    except (ValueError, KeyError) as e:
        print("ERROR de uso:", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
