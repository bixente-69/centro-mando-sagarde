# -*- coding: utf-8 -*-
"""Datos de personal en obra: ingesta de los lotes de jornadas que exporta la tablet, catálogo de
trabajadores y estado para la app.
Funciones principales: ingerir_lote, alta_trabajador, fusionar, aplanar, totales_control,
exportar_estado, comprobar y la línea de comandos (main).
"""

from __future__ import annotations
import argparse, copy, datetime as dt, json, math, os, sys, tempfile, time, unicodedata
from collections import Counter
from pathlib import Path

# Días canónicos de la semana y jornada base por defecto de 7.5 h de lunes a viernes.
DIAS = ("lun", "mar", "mie", "jue", "vie", "sab", "dom")
HOR = {"lun": 7.5, "mar": 7.5, "mie": 7.5, "jue": 7.5, "vie": 7.5, "sab": 0, "dom": 0}
# Claves permitidas (esquemas cerrados). LK = lote, JK = jornada del lote, PK = presente del lote:
# un campo extra los rechaza. CK, TK, OK, GJK y GPK (catálogo, trabajador, obra, jornada guardada y
# presente guardado) los usa `comprobar` para señalar campos fuera del esquema.
LK = {"tipo", "version", "obra", "horario_semanal", "excepciones_horario", "jornadas", "dispositivo"}
JK = {"ambito", "fecha", "presentes", "anulada", "notas", "registrado"}
PK = {"nombre", "horas", "extra"}
CK = {"version", "trabajadores"}
TK = {"id", "nombre", "categoria", "empresa", "activo", "alta", "fusionado_en"}
OK = {"version", "obra", "jornada_base_h", "horario_semanal", "excepciones_horario", "jornadas"}
GJK = {"fecha", "ambito", "anulada", "notas", "presentes", "registrado", "origen"}
GPK = {"id", "horas", "extra"}


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


def clave_nombre(x):
    """Genera la clave canónica sin tildes y en minúsculas.
    Permite comparar nombres ignorando grafías alternativas.
    """
    return "".join(
        c for c in unicodedata.normalize("NFD", limpiar_nombre(x)) if not unicodedata.combining(c)
    ).lower()


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


def ingerir_lote(lote, raiz, obras, hoy, escribir=False, ahora=None):
    """Ingiere un lote de la tablet: lo valida entero y después procesa jornadas, horario semanal y
    horarios propios. Con escribir=True guarda catálogo y obra y añade la traza. Devuelve ok,
    escrito, lote_rechazado, avisos_lote, jornadas, altas y excepciones.
    """
    lr = validar_lote(lote, obras)
    res = {
        "ok": not lr,
        "escrito": False,
        "lote_rechazado": lr,
        "avisos_lote": [],
        "jornadas": [],
        "altas": [],
        "excepciones": [],
    }
    # Rechazo de lote completo: si la cabecera o esquema general fallan no se procesa ninguna
    # jornada.
    if lr:
        return res
    oid = lote["obra"]
    # Paso 1: Normaliza previamente cada jornada y cuenta repeticiones de clave en el propio lote.
    norms = []
    counts = Counter()
    for x in lote["jornadas"]:
        n, e = _norm(x)
        norms.append((n, e))
        if n and n["ambito"] in ("vivienda", "garaje") and _date(n["fecha"]):
            counts[(n["ambito"], n["fecha"])] += 1
    # Paso 2: Carga copias de trabajo del catálogo y de las obras para operar en memoria de forma
    # aislada.
    cat = copy.deepcopy(cargar_catalogo(raiz))
    ods = {o: copy.deepcopy(cargar_obra(raiz, obras, o)) for o in obras}
    od = ods[oid]
    cc = oc = False
    traces = []
    ts = ahora or _now()
    today = dt.date.fromisoformat(hoy)
    # Paso 3: Procesa las jornadas en orden; cada una ve las altas y cambios de las anteriores.
    for n, e in norms:
        a = n["ambito"] if n else None
        f = n["fecha"] if n else None
        key = [oid, a, f]
        # Rechaza si la misma clave de jornada (ámbito y fecha) viene repetida dentro del propio
        # lote.
        if n and counts[(a, f)] > 1:
            e.append("jornada_repetida_en_lote")
        e = list(dict.fromkeys(e))
        # Rechazo de jornada individual: descarta la fila errónea sin detener el procesamiento del
        # resto del lote.
        if e:
            res["ok"] = False
            res["jornadas"].append(
                {"clave": key, "estado": "rechazada", "accion": None, "rechazos": e, "avisos": []}
            )
            continue
        tc = copy.deepcopy(cat)
        mp = {t["id"]: t for t in tc["trabajadores"]}
        names = {}
        # Mapea nombres a ids vigentes resolviendo fusiones para que las horas computen al destino.
        for t in tc["trabajadores"]:
            names[clave_nombre(t["nombre"])] = _resolve(t["id"], mp)
        av = []
        alts = []
        prs = []
        for p in n["presentes"]:
            # Resuelve el trabajador por clave; si es desconocido crea alta nueva y busca nombres
            # parecidos.
            i = names.get(p["clave"])
            if i is None:
                i = _newid(tc["trabajadores"])
                # Un solo aviso por alta; las claves muy cortas no son fiables.
                parecido = next(
                    (q for q in tc["trabajadores"] if _similar(p["clave"], clave_nombre(q["nombre"]))), None
                )
                if parecido:
                    av.append(
                        {"codigo": "nombre_parecido", "detalle": p["nombre"] + " ~ " + parecido["nombre"]}
                    )
                q = {
                    "id": i,
                    "nombre": p["nombre"],
                    "categoria": "",
                    "empresa": "",
                    "activo": True,
                    "alta": hoy,
                    "fusionado_en": None,
                }
                tc["trabajadores"].append(q)
                mp[i] = q
                names[p["clave"]] = i
                alts.append({"id": i, "nombre": p["nombre"]})
                av.append({"codigo": "alta_nueva", "detalle": p["nombre"]})
            prs.append({"id": i, "horas": p["horas"], "extra": p["extra"]})
        old = next((j for j in od["jornadas"] if j.get("fecha") == f and j.get("ambito") == a), None)
        # Inicializa el cómputo de horas del día con los presentes de la jornada evaluada.
        totals = {p["id"]: p["horas"] for p in prs}
        # Calcula las horas diarias acumuladas por persona entre todas las obras, ignorando la
        # jornada previa.
        for xd in ods.values():
            for j in xd.get("jornadas", []):
                if j.get("fecha") != f or j.get("anulada") or (xd is od and j is old):
                    continue
                for p in j.get("presentes", []):
                    # Resuelve el id vigente antes de acumular horas para contabilizar duplicados
                    # fusionados.
                    rid = _resolve(p["id"], mp)
                    totals[rid] = totals.get(rid, 0) + p["horas"]
        # Rechaza la jornada si alguien supera 24 h en el día entre todas las obras por ser
        # imposible.
        if any(v > 24 for v in totals.values()):
            res["ok"] = False
            res["jornadas"].append(
                {
                    "clave": key,
                    "estado": "rechazada",
                    "accion": None,
                    "rechazos": ["suma_diaria_invalida"],
                    "avisos": [],
                }
            )
            continue
        # Emite aviso informativo si la suma diaria acumulada supera 12 h sin llegar a 24 h.
        if any(v > 12 for v in totals.values()):
            av.append({"codigo": "suma_diaria_alta", "detalle": None})
        # Avisa si la fecha anotada es posterior al día de hoy para advertir sobre posibles erratas.
        if dt.date.fromisoformat(f) > today:
            av.append({"codigo": "fecha_futura", "detalle": f})
        new = {
            "fecha": f,
            "ambito": a,
            "anulada": n["anulada"],
            "notas": n["notas"],
            "presentes": sorted(prs, key=lambda p: p["id"]),
            "registrado": n["registrado"] if n["registrado"] is not None else ts,
            "origen": "movil",
        }
        # Comprueba idempotencia: si el contenido es idéntico a lo guardado no reescribe ni deja
        # traza.
        if old and _content(old) == _content(new):
            act = "sin_cambios"
        elif n["anulada"]:
            act = "anulacion"
        elif old:
            act = "reemplazo"
            av.append({"codigo": "reemplazo", "detalle": None})
        else:
            act = "alta"
        # Aplica los cambios en memoria y registra la traza solo si la jornada aporta novedades
        # efectivas.
        if act != "sin_cambios":
            cat = tc
            res["altas"] += alts
            cc |= bool(alts)
            oc = True
            if old:
                od["jornadas"][od["jornadas"].index(old)] = new
            else:
                od["jornadas"].append(new)
            traces.append(
                {
                    "ts": ts,
                    "obra": oid,
                    "ambito": a,
                    "fecha": f,
                    "accion": act,
                    "n_presentes": len(prs),
                    "avisos": [x["codigo"] for x in av],
                    "dispositivo": lote.get("dispositivo"),
                }
            )
        res["jornadas"].append(
            {"clave": key, "estado": "aceptada", "accion": act, "rechazos": [], "avisos": av}
        )
    # Paso 4: Actualiza el horario semanal de la obra si viene en el lote y es distinto al actual.
    if "horario_semanal" in lote and lote["horario_semanal"] != od["horario_semanal"]:
        od["horario_semanal"] = {k: _num(lote["horario_semanal"][k]) for k in DIAS}
        oc = True
        traces.append(
            {
                "ts": ts,
                "obra": oid,
                "ambito": None,
                "fecha": None,
                "accion": "horario",
                "n_presentes": 0,
                "avisos": [],
                "dispositivo": lote.get("dispositivo"),
            }
        )
    # Aplica el horario propio una vez resueltas las altas de las jornadas.
    mp = {t["id"]: t for t in cat["trabajadores"]}
    names = {clave_nombre(t["nombre"]): _resolve(t["id"], mp) for t in cat["trabajadores"]}
    horarios = od.setdefault("excepciones_horario", {})
    # Paso 5: Procesa horarios propios, aplicándose incluso si alguna jornada del lote fue
    # rechazada.
    for nombre_original, horario_original in lote.get("excepciones_horario", {}).items():
        nombre = limpiar_nombre(nombre_original)
        clave = clave_nombre(nombre)
        i = names.get(clave)
        # Da de alta al trabajador si se le asigna un horario propio y aún no figuraba en el
        # catálogo.
        if i is None and horario_original:
            i = _newid(cat["trabajadores"])
            parecido = next(
                (q for q in cat["trabajadores"] if _similar(clave, clave_nombre(q["nombre"]))), None
            )
            if parecido:
                res["avisos_lote"].append(
                    {"codigo": "nombre_parecido", "detalle": nombre + " ~ " + parecido["nombre"]}
                )
            q = {
                "id": i,
                "nombre": nombre,
                "categoria": "",
                "empresa": "",
                "activo": True,
                "alta": hoy,
                "fusionado_en": None,
            }
            cat["trabajadores"].append(q)
            mp[i] = q
            names[clave] = i
            res["altas"].append({"id": i, "nombre": nombre})
            res["avisos_lote"].append({"codigo": "alta_nueva", "detalle": nombre})
            cc = True
        if i is None:
            res["excepciones"].append({"nombre": nombre, "id": None, "accion": "sin_cambios"})
            continue
        # Sustituye por completo el horario propio del trabajador con los días especificados en el
        # lote.
        nuevo = (
            {dia: _num(horario_original[dia]) for dia in DIAS if dia in horario_original}
            if horario_original
            else None
        )
        propio = horarios.get(i)
        # Purga posibles claves antiguas residuales pertenecientes a identificadores fusionados en
        # este.
        viejas = [x for x in horarios if x != i and x in mp and _resolve(x, mp) == i]
        if not viejas and ((nuevo is None and propio is None) or nuevo == propio):
            accion = "sin_cambios"
        else:
            for x in viejas:
                del horarios[x]
            if nuevo is None:
                horarios.pop(i, None)
                accion = "quitada"
                accion_traza = "horario_propio_quitado"
            else:
                horarios[i] = nuevo
                accion = "fijada"
                accion_traza = "horario_propio"
            oc = True
            traces.append(
                {
                    "ts": ts,
                    "obra": oid,
                    "ambito": None,
                    "fecha": None,
                    "accion": accion_traza,
                    "n_presentes": 0,
                    "avisos": [],
                    "dispositivo": lote.get("dispositivo"),
                    "id": i,
                }
            )
        res["excepciones"].append({"nombre": nombre, "id": i, "accion": accion})
    # Paso 6: Persiste atómicamente catálogo y obra solo si se activó la opción y hubo
    # modificaciones.
    if escribir and (cc or oc):
        if cc:
            guardar_catalogo(raiz, cat)
        if oc:
            _saveobra(raiz, obras, oid, od)
        res["escrito"] = True
        try:
            # Añade la traza a `personal_jornadas.jsonl`. Si falla, lo ya guardado se mantiene y
            # solo se avisa (`traza_no_escrita`).
            p = _rop(raiz, obras, oid, "personal_jornadas.jsonl")
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "ab") as z:
                for tr in traces:
                    z.write((json.dumps(tr, ensure_ascii=False) + "\n").encode())
        except Exception as x:
            res["avisos_lote"].append({"codigo": "traza_no_escrita", "detalle": str(x)})
    return res


def _maps(c):
    """Crea índices de trabajadores y resoluciones de fusión.
    Devuelve el diccionario de catálogo y el de destinos.
    """
    mp = {t["id"]: t for t in c["trabajadores"]}
    return mp, {i: _resolve(i, mp) for i in mp}


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
    for p in Path(raiz).glob("*/INFORME SAGARDE IA/personal_obra.json"):
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


def aplanar(raiz, obras, obra):
    """Convierte jornadas activas en filas planas de cálculo.
    Ordena el resultado por fecha, ámbito y trabajador.
    """
    mp, rs = _maps(cargar_catalogo(raiz))
    out = []
    # Filtra jornadas anuladas y proyecta cada presente en una fila plana con su nombre resuelto.
    for j in cargar_obra(raiz, obras, obra)["jornadas"]:
        if j["anulada"]:
            continue
        for p in j["presentes"]:
            out.append(
                {
                    "fecha": j["fecha"],
                    "ambito": j["ambito"],
                    "nombre": mp[rs[p["id"]]]["nombre"],
                    "horas": p["horas"],
                    "extra": p.get("extra", 0),
                }
            )
    return sorted(out, key=lambda x: (x["fecha"], x["ambito"], x["nombre"]))


def totales_control(raiz, obras, obra=None):
    """Calcula totales independientes de horas, días y extra.
    Devuelve None si no hay filas para no falsear datos.
    """
    fs = (
        aplanar(raiz, obras, obra)
        if obra is not None
        else [x for o in obras for x in aplanar(raiz, obras, o)]
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


def exportar_estado(raiz, obras, nombres_obra=None, cerradas=(), generado=None, escribir=False):
    """Genera personal_estado.js con el estado para la app.
    Exporta catálogo activo, últimas jornadas y filas.
    """
    c = cargar_catalogo(raiz)
    mp, rs = _maps(c)
    # Solo se exportan las identidades vigentes: los trabajadores fusionados en otro no aparecen.
    cats = [
        {k: t[k] for k in ("id", "nombre", "categoria", "empresa", "activo")}
        for t in sorted(c["trabajadores"], key=lambda x: x["id"])
        if t.get("fusionado_en") is None
    ]
    obs = {}
    for o in obras:
        if not _rop(raiz, obras, o).exists():
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


def _cli_obras(x):
    """Devuelve {id_obra: carpeta_obra}: lo indicado en --obras (formato id=carpeta,id=carpeta) o,
    si no se indica,
    el registro de obras (registro_obras.OBRAS).
    """
    if x:
        return dict(v.split("=", 1) for v in x.split(","))
    import registro_obras

    return {o["id"]: o["carpeta_obra"] for o in registro_obras.OBRAS}


def main(argv=None):
    """Punto de entrada de la línea de comandos (ingerir, fusionar, exportar-estado, comprobar).
    Devuelve 0 si va bien, 2 si hay rechazos o incoherencias y 1 si el uso o el fichero son
    erróneos.
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
            for v in r["avisos_lote"]:
                print("REVISAR", v["codigo"], v["detalle"])
            return 0 if r["ok"] else 2
        if a.cmd == "fusionar":
            r = fusionar(a.raiz, a.origen, a.destino, a.escribir)
            print("Fusión correcta" if r["ok"] else "ERROR: " + r["error"])
            return 0 if r["ok"] else 2
        if a.cmd == "exportar-estado":
            exportar_estado(a.raiz, ob, escribir=a.escribir)
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
