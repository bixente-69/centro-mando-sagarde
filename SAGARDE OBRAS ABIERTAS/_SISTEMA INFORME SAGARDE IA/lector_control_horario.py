# -*- coding: utf-8 -*-
"""Lector de los CONTROL HORARIO que genera la tablet (paso 08a de «Personal en obra»).

Hace con los `CONTROL HORARIO <OBRA> <DDMMAAAA>.json` de `<obra>/REVISIONES/` lo mismo que `detectar_hojas`
hace con las hojas de revisión: detectar -> vista previa (sin escribir) -> aplicar. No tiene línea de comandos
ni `.bat` propios: lo llaman «actualiza la obra» y `generar_todos.py` (paso 08b).

- `listar`: los ficheros candidatos de una carpeta, con su SHA256 y la fecha del nombre.
- `analizar`: clasifica cada fichero sin escribir nada: ya aplicado, listo, a revisar o rechazado.
- `aplicar`: aplica los listos (y los «a revisar» solo si se acepta). Es idempotente: cada fichero aplicado
  deja su SHA256 en la traza de la obra (`personal_jornadas.jsonl`) y no se vuelve a aplicar.

El nombre del fichero es solo para las personas: la obra y las jornadas se leen de DENTRO. Lo que lee Bixente
va en lenguaje llano (`texto`); los códigos (`codigo`) son para las pruebas y el auditor.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import personal_obra as po  # noqa: E402

# Estados de un fichero tras `analizar`.
YA_APLICADO, LISTO, A_REVISAR, RECHAZADO = "ya_aplicado", "listo", "a_revisar", "rechazado"

# Avisos de personal_obra que obligan a MIRAR el fichero antes de aplicarlo: nunca se aplican ni se descartan
# en silencio. El resto de avisos (alta_nueva, nombre_anterior_usado, renombre_sin_origen) solo se cuentan.
AVISOS_A_REVISAR = (
    "nombre_parecido",
    "suma_diaria_alta",
    "fecha_futura",
    "reemplazo",
    "renombre_coincide_con_otro",
)

AMBITOS = {"vivienda": "viviendas", "garaje": "garajes"}

# Lo que hace una línea de `empresas` cuando de verdad cambia algo (el resto es «sin_cambios» o «sin_persona»).
CAMBIOS_DE_EMPRESA = ("puesta", "cambiada", "quitada")

# Frases de lo que decide este módulo (las de personal_obra salen de `po.texto_aviso`).
TEXTOS = {
    "ya_aplicado": "Este control horario ya está aplicado: no se hace nada.",
    "copia_de": "Es una copia de «{d}», que ya se aplica: no se hace nada.",
    "ilegible": "No se puede leer este fichero: no es un control horario válido.",
    "obra_distinta": "Este control horario es de «{d}», no de esta obra: no se aplica para no mezclar obras.",
    "dato_privado": "Hay un nombre que parece un DNI, un teléfono o un correo ({d}): no se aplica; "
    "corrígelo en la tablet.",
    "todo_rechazado": "Ninguna jornada de este fichero vale: no se aplica nada.",
    "anulacion": "Anula una jornada que ya tenía gente apuntada ({d}).",
    "sin_efecto": "No trae nada nuevo: solo se anota que ya se ha recibido.",
    "error_interno": "Ha fallado al procesarlo ({d}): no se aplica.",
    "cambio_en_disco": "El fichero ha cambiado mientras se aplicaba: no se aplica; vuelve a lanzarlo.",
    "no_anotado": "Se ha aplicado, pero no se ha podido anotar en el registro: se volverá a ofrecer (no duplica nada).",
    "datos_ilegibles": "No se pueden leer los datos de personal de esta obra ({d}): "
    "no se aplica nada hasta arreglarlo.",
}

_FECHA_NOMBRE = re.compile(r"(\d{2})(\d{2})(\d{4})(?:\s*\((\d+)\))?\s*\.json$", re.I)


def texto(codigo, detalle=None):
    """Frase en lenguaje llano para un código, de este módulo o de personal_obra.
    Los códigos de este módulo que llevan «{d}» usan el detalle como complemento.
    """
    plantilla = TEXTOS.get(codigo)
    if plantilla is None:
        return po.texto_aviso(codigo, detalle)
    return plantilla.format(d=detalle or "")


def _fecha_es(iso):
    """Fecha ISO (AAAA-MM-DD) como dd/mm/aaaa; si no es una fecha, el texto tal cual."""
    try:
        return dt.date.fromisoformat(iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(iso)


def _donde(ambito, fecha):
    """Dónde ocurre un aviso: «viviendas del 22/10». Vacío si no se sabe."""
    if ambito not in AMBITOS or not isinstance(fecha, str):
        return ""
    return AMBITOS[ambito] + " del " + _fecha_es(fecha)[:5]


def _motivo(codigo, detalle=None, donde=""):
    """Un motivo o aviso: código, detalle y la frase en llano (con el lugar entre paréntesis)."""
    frase = texto(codigo, detalle)
    if donde:
        frase += " (" + donde + ")"
    return {"codigo": codigo, "detalle": detalle, "texto": frase}


# ─── Listar ───────────────────────────────────────────────────────────────────────────────────────
def _sha256(datos):
    return hashlib.sha256(datos).hexdigest()


def _fecha_del_nombre(nombre):
    """(fecha ISO o None, número de copia) que lleva el nombre: `... 25102026 (1).json` -> ('2026-10-25', 1)."""
    m = _FECHA_NOMBRE.search(nombre)
    if not m:
        return None, 0
    dia, mes, anio = int(m.group(1)), int(m.group(2)), int(m.group(3))
    copia = int(m.group(4) or 0)
    try:
        return dt.date(anio, mes, dia).isoformat(), copia
    except ValueError:
        return None, copia


def _clave_orden(f):
    """Orden de aplicación: fecha del nombre (sin fecha, primero), número de copia y nombre."""
    return (f.get("fecha_nombre") or "", f.get("copia", 0), f.get("nombre", "").casefold())


def es_control_horario(nombre):
    """True si el nombre es el de un control horario de la tablet: `CONTROL HORARIO <algo>.json` (mayúsculas
    indiferentes). Es la regla única: la usan `listar` y la lista de documentos de la obra."""
    minuscula = nombre.casefold()
    return minuscula.startswith("control horario") and minuscula.endswith(".json")


def listar(carpeta_revisiones):
    """Ficheros `CONTROL HORARIO*.json` de una carpeta (mayúsculas indiferentes, cualquier sufijo).
    Devuelve, en orden de aplicación, dicts con nombre, ruta, sha256 (None si no se pudo leer), fecha_nombre,
    copia, bytes y error.
    """
    carpeta = Path(carpeta_revisiones)
    if not carpeta.is_dir():
        return []
    out = []
    for p in carpeta.iterdir():
        nombre = p.name
        if not es_control_horario(nombre) or not p.is_file():
            continue
        fecha, copia = _fecha_del_nombre(nombre)
        ficha = {
            "nombre": nombre,
            "ruta": str(p),
            "sha256": None,
            "fecha_nombre": fecha,
            "copia": copia,
            "bytes": None,
            "error": None,
        }
        try:
            datos = p.read_bytes()
        except OSError as exc:
            ficha["error"] = type(exc).__name__ + ": " + str(exc)
        else:
            ficha["sha256"] = _sha256(datos)
            ficha["bytes"] = len(datos)
        out.append(ficha)
    return sorted(out, key=_clave_orden)


# ─── Guardas propias del lector ───────────────────────────────────────────────────────────────────
def _parece_privado(nombre):
    """True si un nombre lleva etiquetas o parece un DNI, un teléfono o un correo."""
    if not isinstance(nombre, str):
        return False
    limpio = po.limpiar_nombre(nombre)
    if "<" in limpio or ">" in limpio:
        return True
    return any(patron.search(limpio) for _tipo, patron in po.PATRONES_PRIVADOS)


def _sitios_con_datos_privados(lote):
    """Dónde lleva el lote nombres con datos privados (sin repetir el valor). Lista de textos de lugar."""
    sitios = []
    for j in lote.get("jornadas") if isinstance(lote.get("jornadas"), list) else []:
        if not isinstance(j, dict):
            continue
        presentes = j.get("presentes") if isinstance(j.get("presentes"), list) else []
        if any(isinstance(p, dict) and _parece_privado(p.get("nombre")) for p in presentes):
            sitios.append("jornada de " + (_donde(j.get("ambito"), j.get("fecha")) or "una fecha ilegible"))
    excepciones = lote.get("excepciones_horario")
    if isinstance(excepciones, dict) and any(_parece_privado(n) for n in excepciones):
        sitios.append("horarios especiales")
    renombres = lote.get("renombres") if isinstance(lote.get("renombres"), list) else []
    if any(isinstance(r, dict) and (_parece_privado(r.get("de")) or _parece_privado(r.get("a"))) for r in renombres):
        sitios.append("cambios de nombre")
    altas = lote.get("altas") if isinstance(lote.get("altas"), list) else []
    if any(_parece_privado(n) for n in altas):
        sitios.append("nombres nuevos")
    empresas = lote.get("empresas") if isinstance(lote.get("empresas"), list) else []
    if any(isinstance(e, dict) and (_parece_privado(e.get("nombre")) or _parece_privado(e.get("empresa")))
           for e in empresas):
        sitios.append("empresas")
    return sitios


def _totales(estado, raiz, obras, obra_id):
    """Horas, días y trabajadores de la obra en un estado en memoria (None si aún no hay jornadas)."""
    t = po.totales_control(raiz, obras, obra_id, estado=estado)
    if t is None:
        return None
    return {"horas": t["horas"], "dias": t["dias"], "trabajadores": t["trabajadores"]}


# ─── Analizar un fichero ──────────────────────────────────────────────────────────────────────────
def _ficha_vacia(f):
    """Ficha de un fichero antes de clasificarlo: lo que se sabe de él y los huecos por rellenar."""
    return {
        "nombre": f.get("nombre"),
        "ruta": f.get("ruta"),
        "sha256": f.get("sha256"),
        "fecha_nombre": f.get("fecha_nombre"),
        "estado": None,
        "motivos": [],
        "avisos": [],
        "jornadas": [],
        "renombres": [],
        "personas_nuevas": [],
        "empresas": [],
        "horarios_propios": [],
        "rechazadas": 0,
        "sin_efecto": False,
        "resumen": "",
    }


def _cerrar(ficha, estado, *motivos):
    """Fija el estado final del fichero y sus motivos."""
    ficha["estado"] = estado
    ficha["motivos"] = list(motivos)
    return ficha


def _nombre_de(cat_mp, ident):
    """Nombre vigente de una persona (siguiendo las fusiones)."""
    return cat_mp[po._resolve(ident, cat_mp)]["nombre"]


def _resumen_jornada(entrada, previas, nuevo, obra_id):
    """Una jornada del resultado de personal_obra: quién, cuántas horas y cómo era antes."""
    _obra, ambito, fecha = entrada["clave"]
    avisos = [_motivo(a["codigo"], a["detalle"], _donde(ambito, fecha)) for a in entrada["avisos"]]
    if entrada["estado"] != "aceptada":
        rechazos = [_motivo(c) for c in entrada["rechazos"]]
        return {"ambito": ambito, "fecha": fecha, "estado": "rechazada", "rechazos": rechazos, "avisos": avisos}
    mp = {t["id"]: t for t in nuevo["cat"]["trabajadores"]}
    despues = next(j for j in nuevo["ods"][obra_id]["jornadas"] if j["ambito"] == ambito and j["fecha"] == fecha)
    previa = previas.get((ambito, fecha))
    antes = None
    if previa is not None and not previa.get("anulada"):
        antes = {"personas": len(previa["presentes"]), "horas": sum(p["horas"] for p in previa["presentes"])}
    return {
        "ambito": ambito,
        "fecha": fecha,
        "estado": "aceptada",
        "accion": entrada["accion"],
        "personas": sorted(_nombre_de(mp, p["id"]) for p in despues["presentes"]),
        "horas": sum(p["horas"] for p in despues["presentes"]),
        "antes": antes,
        "avisos": avisos,
    }


def _plural(n, uno, varios):
    return "%d %s" % (n, uno if n == 1 else varios)


def _resumen_texto(ficha):
    """Una línea en llano de lo que trae el fichero."""
    partes = []
    aceptadas = [j for j in ficha["jornadas"] if j["estado"] == "aceptada"]
    if aceptadas:
        ambitos = sorted({AMBITOS.get(j["ambito"], j["ambito"]) for j in aceptadas})
        partes.append(_plural(len(aceptadas), "jornada", "jornadas") + " de " + " y ".join(ambitos))
    cambiados = [r for r in ficha["renombres"] if r["accion"] == "renombrado"]
    if cambiados:
        partes.append(_plural(len(cambiados), "cambio de nombre", "cambios de nombre"))
    if ficha["personas_nuevas"]:
        partes.append(_plural(len(ficha["personas_nuevas"]), "persona nueva", "personas nuevas"))
    puestas = [e for e in ficha["empresas"] if e["accion"] in ("puesta", "cambiada")]
    if puestas:
        partes.append(_plural(len(puestas), "empresa puesta", "empresas puestas"))
    quitadas = [e for e in ficha["empresas"] if e["accion"] == "quitada"]
    if quitadas:
        partes.append(_plural(len(quitadas), "empresa quitada", "empresas quitadas"))
    if ficha["horarios_propios"]:
        partes.append(_plural(len(ficha["horarios_propios"]), "horario especial", "horarios especiales"))
    if ficha["rechazadas"]:
        partes.append(_plural(ficha["rechazadas"], "jornada que no vale", "jornadas que no valen"))
    return ", ".join(partes) if partes else "no trae nada nuevo"


def _simular(obra_id, lote, ficha, estado, hoy, raiz, obras, ahora):
    """Aplica el lote a una COPIA del estado y clasifica el resultado. Devuelve (ficha, estado nuevo o None)."""
    previas = {(j["ambito"], j["fecha"]): j for j in estado["ods"][obra_id]["jornadas"]}
    prueba = copy.deepcopy(estado)
    r = po.ingerir_lote(
        copy.deepcopy(lote),
        raiz,
        obras,
        hoy,
        ahora=ahora,
        sha256=ficha["sha256"],
        fichero=ficha["nombre"],
        estado=prueba,
    )
    if r["lote_rechazado"]:
        return _cerrar(ficha, RECHAZADO, *[_motivo(c) for c in r["lote_rechazado"]]), None
    ficha["jornadas"] = [_resumen_jornada(e, previas, prueba, obra_id) for e in r["jornadas"]]
    ficha["rechazadas"] = sum(1 for j in ficha["jornadas"] if j["estado"] == "rechazada")
    ficha["renombres"] = list(r["renombres"])
    ficha["personas_nuevas"] = [dict(a) for a in r["altas"]]
    ficha["empresas"] = [dict(e) for e in r["empresas"] if e["accion"] in CAMBIOS_DE_EMPRESA]
    ficha["horarios_propios"] = [x for x in r["excepciones"] if x["accion"] != "sin_cambios"]
    ficha["avisos"] = [_motivo(a["codigo"], a["detalle"]) for a in r["avisos_lote"]]
    for j in ficha["jornadas"]:
        ficha["avisos"] += j["avisos"]
    aplica = [j for j in ficha["jornadas"] if j["estado"] == "aceptada"]
    # Aparte de las jornadas, el fichero puede traer cambios de nombre, nombres nuevos u horarios.
    hay_otra_cosa = bool(lote.get("renombres") or lote.get("altas") or lote.get("excepciones_horario"))
    hay_otra_cosa = hay_otra_cosa or bool(lote.get("empresas"))
    hay_otra_cosa = hay_otra_cosa or "horario_semanal" in lote
    if ficha["rechazadas"] and not aplica and not hay_otra_cosa:
        return _cerrar(ficha, RECHAZADO, _motivo("todo_rechazado")), None
    ficha["resumen"] = _resumen_texto(ficha)
    revisar = [a for a in ficha["avisos"] if a["codigo"] in AVISOS_A_REVISAR]
    for j in aplica:
        previa = previas.get((j["ambito"], j["fecha"]))
        if j["accion"] == "anulacion" and previa is not None and previa["presentes"] and not previa.get("anulada"):
            revisar.append(_motivo("anulacion", _donde(j["ambito"], j["fecha"])))
    if revisar:
        return _cerrar(ficha, A_REVISAR, *revisar), prueba
    # Si la copia queda igual que el original, el fichero no cambia nada: solo se anotará que se ha recibido.
    ficha["sin_efecto"] = prueba == estado
    return _cerrar(ficha, LISTO, *([_motivo("sin_efecto")] if ficha["sin_efecto"] else [])), prueba


def _analizar_uno(obra_id, f, hoy, raiz, obras, estado, recibidos, vistos, ahora):
    """Clasifica UN fichero. Devuelve (ficha, estado nuevo si se aplicaría o None).
    Un fallo de lectura o de proceso se cuenta como fichero rechazado: no tumba a los demás.
    """
    ficha = _ficha_vacia(f)
    ruta = f.get("ruta")
    try:
        datos = Path(ruta).read_bytes()
    except (OSError, TypeError) as exc:
        return _cerrar(ficha, RECHAZADO, _motivo("ilegible", type(exc).__name__ + ": " + str(exc))), None
    ficha["sha256"] = _sha256(datos)
    if ficha["sha256"] in recibidos:
        return _cerrar(ficha, YA_APLICADO, _motivo("ya_aplicado")), None
    if ficha["sha256"] in vistos:
        return _cerrar(ficha, YA_APLICADO, _motivo("copia_de", vistos[ficha["sha256"]])), None
    try:
        lote = json.loads(datos.decode("utf-8-sig"))
    except ValueError as exc:
        return _cerrar(ficha, RECHAZADO, _motivo("ilegible", type(exc).__name__)), None
    if not isinstance(lote, dict) or lote.get("tipo") != "lote_personal":
        return _cerrar(ficha, RECHAZADO, _motivo("tipo_desconocido")), None
    de_otra_obra = lote.get("obra")
    if isinstance(de_otra_obra, str) and de_otra_obra in obras and de_otra_obra != obra_id:
        return _cerrar(ficha, RECHAZADO, _motivo("obra_distinta", obras[de_otra_obra])), None
    sitios = _sitios_con_datos_privados(lote)
    if sitios:
        return _cerrar(ficha, RECHAZADO, _motivo("dato_privado", ", ".join(sitios))), None
    try:
        return _simular(obra_id, lote, ficha, estado, hoy, raiz, obras, ahora)
    except Exception as exc:  # frontera de aislamiento: un fichero que falla se cuenta y se dice, no tumba la obra
        return _cerrar(ficha, RECHAZADO, _motivo("error_interno", type(exc).__name__ + ": " + str(exc))), None


def analizar(obra_id, ficheros, hoy, raiz, obras, aceptar=False, ahora=None):
    """Vista previa de los ficheros de una obra: no escribe NADA.
    Los aplica en cadena sobre una copia en memoria (los «a revisar» solo si `aceptar`), como lo hará `aplicar`.
    """
    if obra_id not in obras:
        raise ValueError("obra desconocida: %s" % obra_id)
    try:
        estado = po.cargar_estado(raiz, obras)
        recibidos = set(po.shas_recibidos(raiz, obras, obra_id))
    except (OSError, ValueError) as exc:
        # Sin poder leer los datos, o sin saber qué se aplicó ya, aplicar podría pisar o duplicar: no se toca
        # nada y se dice.
        motivo = _motivo("datos_ilegibles", type(exc).__name__ + ": " + str(exc))
        fichas = [_cerrar(_ficha_vacia(f), RECHAZADO, motivo) for f in sorted(ficheros, key=_clave_orden)]
        return _informe(obra_id, hoy, aceptar, fichas, None, None)
    antes = _totales(estado, raiz, obras, obra_id)
    vistos = {}
    fichas = []
    for f in sorted(ficheros, key=_clave_orden):
        ficha, nuevo = _analizar_uno(obra_id, f, hoy, raiz, obras, estado, recibidos, vistos, ahora)
        if nuevo is not None and (ficha["estado"] == LISTO or aceptar):
            estado = nuevo
            vistos[ficha["sha256"]] = ficha["nombre"]
            ficha["aceptado"] = ficha["estado"] == A_REVISAR
        fichas.append(ficha)
    return _informe(obra_id, hoy, aceptar, fichas, antes, _totales(estado, raiz, obras, obra_id))


def _informe(obra_id, hoy, aceptar, fichas, antes, despues):
    """Resultado de `analizar`: los ficheros en orden de aplicación, el recuento por estado y las horas."""
    cuenta = {e: sum(1 for x in fichas if x["estado"] == e) for e in (YA_APLICADO, LISTO, A_REVISAR, RECHAZADO)}
    return {
        "obra": obra_id,
        "hoy": hoy,
        "aceptar": bool(aceptar),
        "ficheros": fichas,
        "cuenta": cuenta,
        "pendientes": cuenta[LISTO] + cuenta[A_REVISAR],
        "frena": bool(cuenta[A_REVISAR] or cuenta[RECHAZADO]),
        "antes": antes,
        "despues": despues,
    }


def _totales_en_disco(raiz, obras, obra_id):
    """Horas, días y trabajadores que hay ahora en el disco (None si no hay jornadas o no se pueden leer)."""
    try:
        return _totales(po.cargar_estado(raiz, obras), raiz, obras, obra_id)
    except (OSError, ValueError):
        return None


# ─── Aplicar ──────────────────────────────────────────────────────────────────────────────────────
def _aplicar_uno(obra_id, ficha, hoy, raiz, obras, ahora):
    """Escribe UN fichero con personal_obra y comprueba que su SHA256 ha quedado anotado. Devuelve la ficha."""
    datos = Path(ficha["ruta"]).read_bytes()
    if _sha256(datos) != ficha["sha256"]:
        ficha["motivos"].append(_motivo("cambio_en_disco"))
        ficha["estado"] = RECHAZADO
        return ficha
    lote = json.loads(datos.decode("utf-8-sig"))
    r = po.ingerir_lote(
        lote, raiz, obras, hoy, escribir=True, ahora=ahora, sha256=ficha["sha256"], fichero=ficha["nombre"]
    )
    ficha["escrito"] = bool(r["escrito"])
    ficha["aplicado"] = True
    anotado = ficha["sha256"] in po.shas_recibidos(raiz, obras, obra_id)
    if not anotado:
        ficha["motivos"].append(_motivo("no_anotado"))
    return ficha


def aplicar(obra_id, ficheros, hoy, raiz, obras, aceptar=False, ahora=None):
    """Aplica los ficheros listos de una obra (y los «a revisar» solo con `aceptar`). Idempotente.
    Devuelve lo aplicado, lo que no se ha tocado y por qué, las horas antes/después y los fallos.
    """
    analisis = analizar(obra_id, ficheros, hoy, raiz, obras, aceptar=aceptar, ahora=ahora)
    aplicados, no_aplicados, ya_aplicados, errores = [], [], [], []
    for ficha in analisis["ficheros"]:
        if ficha["estado"] == YA_APLICADO:
            ya_aplicados.append(ficha)
        elif ficha["estado"] == LISTO or (ficha["estado"] == A_REVISAR and aceptar):
            try:
                ficha = _aplicar_uno(obra_id, ficha, hoy, raiz, obras, ahora)
            except Exception as exc:  # frontera de aislamiento: lo que falla se cuenta y se dice
                ficha["estado"] = RECHAZADO
                ficha["motivos"].append(_motivo("error_interno", type(exc).__name__ + ": " + str(exc)))
            (aplicados if ficha["estado"] != RECHAZADO else errores).append(ficha)
        else:
            no_aplicados.append(ficha)
    despues = _totales_en_disco(raiz, obras, obra_id)
    avisos = [dict(a, fichero=f["nombre"]) for f in aplicados + no_aplicados for a in f["avisos"]]
    return {
        "obra": obra_id,
        "ficheros": analisis["ficheros"],
        "aplicados": aplicados,
        "no_aplicados": no_aplicados,
        "ya_aplicados": ya_aplicados,
        "errores": errores,
        "antes": analisis["antes"],
        "despues": despues,
        "avisos": avisos,
        "personas_nuevas": [a for f in aplicados for a in f["personas_nuevas"]],
        "frena": bool(no_aplicados or errores),
    }
