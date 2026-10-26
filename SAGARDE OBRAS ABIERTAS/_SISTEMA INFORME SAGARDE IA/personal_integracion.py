# -*- coding: utf-8 -*-
"""Puente entre el motor de obras y los datos de «Personal en obra» (pasos 06 y 08b).

`personal_obra.py` sabe leer y escribir los datos; `lector_control_horario.py` sabe qué hacer con los
`CONTROL HORARIO` de la tablet; este módulo sabe DONDE está cada cosa dentro del entorno real (obras abiertas
del registro y obras archivadas) y ofrece lo que necesitan quienes lo consumen:

- `filas_para_panel`: filas de una obra para su pestaña Personal. Nunca lanza:
  un fallo de datos devuelve un aviso y el panel sale como siempre.
- `controles_horarios` y `lineas_controles`: los `CONTROL HORARIO` de la carpeta `REVISIONES` de una obra, en
  vista previa o aplicados, y su texto en lenguaje llano. Los usan «actualiza la obra» y el auditor.
- `aplicar_controles_limpios`: lo que hace `generar_todos.py` (y con él el `.bat`) antes de construir el panel
  de cada obra: aplica los controles limpios y AVISA de los dudosos, que no se aplican. Nunca lanza.
- `exportar_estado_real`: escribe `personal_estado.js` con TODAS las obras abiertas del registro (tengan o no
  jornadas: la tablet tiene que poder ofrecerlas) y las archivadas con datos (marcadas `cerrada`). Va siempre
  con el registro entero: regenerar una sola obra no debe encoger el estado de la tablet ni el ranking.
- `auditar`: comprobaciones del paso 0 de `Actualizar_Sagarde.bat`.
- La línea de comandos (`exportar-estado`, `auditar`).

No hay ningún comando para «ingerir» ni para dar de alta una obra: un `CONTROL HORARIO` entra como entra una
revisión (se deja en `REVISIONES` y se dice «actualiza la obra», o lo aplica el `.bat`), y la primera vez crea
sola los datos de la obra.

Regla de la casa: algo declarado que el motor ignora en silencio es el fallo
típico de este proyecto. Por eso cada función que lee datos de personal dice
lo que hizo (o por qué no lo hizo) y `auditar` mira que lo declarado exista.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent  # _SISTEMA INFORME SAGARDE IA
OBRAS_ABIERTAS_DIR = BASE_DIR.parent  # SAGARDE OBRAS ABIERTAS
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import lector_control_horario as lector  # noqa: E402
import personal_obra as po  # noqa: E402

SALIDA_OBRA = "INFORME SAGARDE IA"
MOTOR = "_SISTEMA INFORME SAGARDE IA"
# Las obras cerradas viven al lado de «SAGARDE OBRAS ABIERTAS» (cerrar_obra.py).
CERRADAS_REL = ("SAGARDE (OLD)", "OBRAS CERRADAS")

# Ficheros de código y de aplicación que el sistema declara. Si hay datos de
# personal y falta alguno, la pestaña, el ranking o la tablet se quedan sin
# motor sin avisar.
FICHEROS_DECLARADOS = (
    "personal_calculo.js",
    "personal_obra.py",
    "panel_personal.py",
    "personal_integracion.py",
    "generador_personal.html",
    "personal_sagarde.html",
    "lector_control_horario.py",
)

# Claves de una línea de la traza `personal_jornadas.jsonl` (ver ingerir_lote). `sha256` y `fichero` identifican el
# control horario recibido; `de`, `a` y `nombre` los cambios de nombre y las altas; `rechazadas` cuenta las jornadas
# que no valían en la línea `recibido`.
CLAVES_TRAZA = {
    "ts", "obra", "ambito", "fecha", "accion", "n_presentes", "avisos", "dispositivo", "id",
    "sha256", "fichero", "de", "a", "nombre", "rechazadas",
}
_SHA256 = re.compile(r"[0-9a-fA-F]{64}")

# Datos que jamás deben llegar a estos ficheros (decisión de Bixente: el
# esquema no lleva DNI, teléfono ni correo). Se buscan en el texto crudo para
# que cuenten también las notas y el nombre del dispositivo, que son libres.
# La lista es UNA sola, la de personal_obra, que la usa también para rechazar nombres.
PATRONES_PRIVADOS = po.PATRONES_PRIVADOS

# Se ejecuta con node sobre `personal_calculo.js`: la misma implementación que
# usan la pestaña, el informe, la tablet y el ranking. Entrada por stdin
# ({clave: filas}), salida por stdout.
_JS_DOBLE_CALCULO = """
const fs = require('fs');
const api = require(process.env.PERSONAL_CALCULO);
const entrada = JSON.parse(fs.readFileSync(0, 'utf8'));
const salida = {};
for (const [clave, filas] of Object.entries(entrada)) {
  const r = api.agregar(filas);
  const trabajadores = {};
  for (const t of r.trabajadores) trabajadores[t.nombre] = { dias: t.dias, horas: t.horas, extra: t.extra };
  salida[clave] = { total: r.total, avisos: r.avisos, trabajadores };
}
process.stdout.write(JSON.stringify(salida));
"""
TOLERANCIA = 1e-6


# ─── Dónde está cada obra ─────────────────────────────────────────────────
def _raiz(raiz):
    return Path(raiz) if raiz else OBRAS_ABIERTAS_DIR


def obras_registro():
    """({id: carpeta_obra}, {id: nombre}) de las obras abiertas del registro."""
    import registro_obras

    return (
        {o["id"]: o["carpeta_obra"] for o in registro_obras.OBRAS},
        {o["id"]: o["nombre"] for o in registro_obras.OBRAS},
    )


def obras_cerradas(raiz=None):
    """({id: carpeta relativa a raiz}, avisos) de las obras archivadas que conservan
    su `personal_obra.json`. El id sale del propio fichero (campo `obra`): al cerrar
    una obra desaparece del registro y la carpeta ya no lo dice."""
    raiz = _raiz(raiz)
    base = raiz.parent.joinpath(*CERRADAS_REL)
    cerradas, avisos = {}, []
    if not base.is_dir():
        return cerradas, avisos
    for carpeta in sorted(base.iterdir()):
        fichero = carpeta / SALIDA_OBRA / "personal_obra.json"
        if not fichero.is_file():
            continue
        try:
            with open(fichero, encoding="utf-8") as f:
                oid = json.load(f)["obra"]
        except Exception as exc:
            avisos.append(f"{fichero}: no se pudo leer el id de la obra ({type(exc).__name__}: {exc})")
            continue
        if not isinstance(oid, str) or not oid or oid in cerradas:
            avisos.append(f"{fichero}: id de obra vacío, no textual o repetido entre las archivadas")
            continue
        cerradas[oid] = os.path.join(os.pardir, *CERRADAS_REL, carpeta.name)
    return cerradas, avisos


def universo(raiz=None):
    """Todas las obras que cuentan para el estado: abiertas del registro + archivadas.
    Devuelve (obras {id: carpeta relativa a raiz}, nombres {id: nombre}, ids_cerradas, avisos)."""
    raiz = _raiz(raiz)
    obras, nombres = obras_registro()
    archivadas, avisos = obras_cerradas(raiz)
    ids_cerradas = set()
    for oid, carpeta in archivadas.items():
        if oid in obras:
            avisos.append(f"la obra «{oid}» figura abierta en el registro y archivada: se cuenta como abierta")
            continue
        obras[oid] = carpeta
        nombres[oid] = os.path.basename(carpeta)
        ids_cerradas.add(oid)
    return obras, nombres, ids_cerradas, avisos


def _ruta_obra(raiz, obras, oid, nombre="personal_obra.json"):
    return Path(raiz) / obras[oid] / SALIDA_OBRA / nombre


# ─── Lo que consume el panel ──────────────────────────────────────────────
def filas_para_panel(obra, raiz=None):
    """Filas planas de personal de una obra del registro, para `generar_panel(personal=…)`.
    Devuelve (filas, aviso). Sin `personal_obra.json` -> ([], None): la obra se ve como
    siempre. Si el fichero existe y no se puede leer -> ([], texto del fallo): el panel
    sale igual y quien llama imprime el aviso. No lanza nunca."""
    raiz = _raiz(raiz)
    try:
        if not (raiz / obra["carpeta_obra"] / SALIDA_OBRA / "personal_obra.json").is_file():
            return [], None
        return po.aplanar(raiz, {obra["id"]: obra["carpeta_obra"]}, obra["id"]), None
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"


# ─── Estado para la tablet y el ranking ───────────────────────────────────
def _generado_de(texto):
    """Campo `generado` de un personal_estado.js, o None si no se puede leer."""
    m = re.match(r"window\.SAGARDE_PERSONAL = (.*);\n?\Z", texto or "", re.S)
    try:
        return json.loads(m.group(1)).get("generado") if m else None
    except ValueError:
        return None


def exportar_estado_real(raiz=None, escribir=True, ahora=None):
    """Escribe `personal_estado.js` con todas las obras abiertas del registro (con o sin jornadas) y las
    archivadas. Devuelve {escrito, motivo, obras:{id: nº de filas}, avisos}. No toca el fichero si el
    contenido no cambia (así no se genera un cambio de git por cada regeneración)."""
    raiz = _raiz(raiz)
    obras, nombres, cerradas, avisos = universo(raiz)
    destino = raiz / MOTOR / "personal_estado.js"
    res = {"escrito": False, "motivo": "", "obras": {}, "avisos": list(avisos)}
    if not obras:
        res["motivo"] = "no hay ninguna obra en el registro: no se escribe personal_estado.js"
        return res
    viejo = destino.read_text(encoding="utf-8") if destino.exists() else None
    if viejo is not None:
        igual = po.exportar_estado(raiz, obras, nombres, cerradas, generado=_generado_de(viejo), incluir_vacias=True)
        if igual == viejo:
            res["motivo"] = "sin cambios"
            res["obras"] = {o: len(po.aplanar(raiz, obras, o)) for o in obras}
            return res
    texto = po.exportar_estado(raiz, obras, nombres, cerradas, generado=ahora, escribir=escribir, incluir_vacias=True)
    res["escrito"] = bool(escribir)
    res["obras"] = {o: len(po.aplanar(raiz, obras, o)) for o in obras}
    if escribir:
        # Lo declarado tiene que verse: se vuelve a leer lo escrito y se cuentan las filas.
        leido = destino.read_text(encoding="utf-8")
        m = re.match(r"window\.SAGARDE_PERSONAL = (.*);\n?\Z", leido, re.S)
        publicado = json.loads(m.group(1))["obras"] if m else {}
        for oid, n in res["obras"].items():
            if len(publicado.get(oid, {}).get("jornadas", [])) != n:
                res["avisos"].append(f"personal_estado.js no refleja las {n} filas de «{oid}»")
        if leido != texto:
            res["avisos"].append("personal_estado.js escrito no coincide con lo generado")
    return res


# ─── Controles horarios (los CONTROL HORARIO de la carpeta REVISIONES) ────────────────────────────
def carpeta_revisiones(obra_id, raiz=None):
    """Carpeta REVISIONES de una obra abierta del registro: ahí se dejan los CONTROL HORARIO."""
    obras, _ = obras_registro()
    if obra_id not in obras:
        raise ValueError(f"«{obra_id}» no es una obra abierta del registro: {', '.join(sorted(obras))}")
    return _raiz(raiz) / obras[obra_id] / "REVISIONES"


def controles_horarios(obra_id, raiz=None, hoy=None, escribir=False, aceptar=False, ahora=None):
    """Vista previa (o, con `escribir`, aplicación) de los CONTROL HORARIO de la carpeta REVISIONES de una obra.
    Devuelve {obra, carpeta, n_ficheros, aplicado, ficheros, cuenta, avisos_a_revisar, frena, antes, despues}.
    Un fichero que falla no lanza: sale como rechazado. Solo lanza ValueError si la obra no es del registro."""
    raiz = _raiz(raiz)
    obras, _ = obras_registro()
    carpeta = carpeta_revisiones(obra_id, raiz)
    hoy = hoy or dt.date.today().isoformat()
    ficheros = lector.listar(carpeta)
    funcion = lector.aplicar if escribir else lector.analizar
    r = funcion(obra_id, ficheros, hoy, str(raiz), obras, aceptar=aceptar, ahora=ahora)
    fichas = r["ficheros"]
    cuenta = {e: sum(1 for f in fichas if f["estado"] == e and not f.get("aplicado")) for e in (
        lector.YA_APLICADO, lector.LISTO, lector.A_REVISAR, lector.RECHAZADO)}
    cuenta["aplicado"] = sum(1 for f in fichas if f.get("aplicado"))
    return {
        "obra": obra_id,
        "carpeta": str(carpeta),
        "n_ficheros": len(ficheros),
        "aplicado": bool(escribir),
        "ficheros": fichas,
        "cuenta": cuenta,
        # La cifra que dice la guarda de «actualiza la obra»: cuántos avisos obligan a mirar (sin aceptar nada).
        "avisos_a_revisar": sum(len(f["motivos"]) for f in fichas if f["estado"] == lector.A_REVISAR),
        "frena": r["frena"],
        "antes": r["antes"],
        "despues": r["despues"],
    }


def _plural(n, uno, varios):
    return "%d %s" % (n, uno if n == 1 else varios)


def _horas(x):
    """Horas con coma decimal: 7.5 -> «7,5»; 8.0 -> «8»."""
    return ("%g" % x).replace(".", ",")


def _resumen_totales(t):
    """«7,5 h en 1 día con 1 persona», o «sin jornadas» si la obra aún no tiene ninguna."""
    if not t:
        return "sin jornadas"
    dias = _plural(t["dias"], "día", "días")
    personas = _plural(t["trabajadores"], "persona", "personas")
    return "%s h en %s con %s" % (_horas(t["horas"]), dias, personas)


_ETIQUETAS_PREVIA = {
    lector.YA_APLICADO: "ya estaba aplicado",
    lector.LISTO: "se aplicaría",
    lector.A_REVISAR: "HAY QUE MIRARLO, no se aplica",
    lector.RECHAZADO: "NO VALE, no se aplica",
}
MAX_AVISOS_POR_FICHERO = 8


def _lineas_ficha(f):
    """Las líneas de un fichero en lenguaje llano: qué es, qué trae y qué hay que mirar."""
    if f.get("aplicado"):
        etiqueta = "APLICADO" + (" (con tu visto bueno)" if f["estado"] == lector.A_REVISAR else "")
    else:
        etiqueta = _ETIQUETAS_PREVIA[f["estado"]]
    linea = f"  · «{f['nombre']}» — {etiqueta}"
    if f["estado"] in (lector.LISTO, lector.A_REVISAR):
        linea += ": " + ("no trae nada nuevo (solo se anota que ya se ha recibido)" if f.get("sin_efecto") else f["resumen"])
    else:
        # «ya estaba aplicado: Este control horario ya está aplicado» se repetiría a sí mismo: solo se añade
        # el motivo cuando dice algo más (p. ej. que es una copia de otro fichero).
        motivos = [m["texto"] for m in f["motivos"] if m["codigo"] != "ya_aplicado"]
        linea += (": " + " ".join(motivos)) if motivos else ""
    out = [linea]
    if f["estado"] not in (lector.LISTO, lector.A_REVISAR):
        return out
    if f["personas_nuevas"]:
        out.append("      personas nuevas: " + ", ".join(p["nombre"] for p in f["personas_nuevas"]))
    vistos = set()
    for m in f["motivos"]:
        if m["texto"] not in vistos and m["codigo"] != "sin_efecto":
            vistos.add(m["texto"])
            out.append("      ! " + m["texto"])
    otros = []
    for a in f["avisos"]:
        if a["codigo"] != "alta_nueva" and a["texto"] not in vistos:
            vistos.add(a["texto"])
            otros.append(a["texto"])
    for texto in otros[:MAX_AVISOS_POR_FICHERO]:
        out.append("      · " + texto)
    if len(otros) > MAX_AVISOS_POR_FICHERO:
        out.append("      · … y %d avisos más" % (len(otros) - MAX_AVISOS_POR_FICHERO))
    for j in f["jornadas"]:
        if j["estado"] == "rechazada":
            donde = lector._donde(j["ambito"], j["fecha"]) or "una jornada"
            out.append("      ✗ no vale (%s): %s" % (donde, " ".join(m["texto"] for m in j["rechazos"])))
    return out


def lineas_controles(res):
    """El resultado de `controles_horarios` como líneas de texto en lenguaje llano (para la consola y el informe).
    Si no hay controles nuevos lo dice: no calla."""
    fichas = res["ficheros"]
    if not fichas:
        return ["No hay controles horarios nuevos."]
    if all(f["estado"] == lector.YA_APLICADO for f in fichas):
        return ["No hay controles horarios nuevos (%s)." % _plural(
            len(fichas), "fichero ya estaba aplicado", "ficheros ya estaban aplicados")]
    out = ["Controles horarios en REVISIONES: %s." % _plural(len(fichas), "fichero", "ficheros")]
    for f in fichas:
        out += _lineas_ficha(f)
    if res["antes"] is not None or res["despues"] is not None:
        despues = "después " if res["aplicado"] else "quedarían "
        out.append("  Horas de la obra: antes %s; %s%s." % (
            _resumen_totales(res["antes"]), despues, _resumen_totales(res["despues"])))
    return out


def aplicar_controles_limpios(obra_id, raiz=None, hoy=None, ahora=None):
    """Lo que hace `generar_todos.py` antes de construir el panel de una obra: aplica los CONTROL HORARIO limpios de
    su REVISIONES (idempotente) y AVISA de los dudosos o inválidos, que NO se aplican. No lanza nunca por un fichero.
    Devuelve {lineas, aplicados, avisos, resultado}: las líneas ya van formateadas para la consola."""
    nombre = obras_registro()[1].get(obra_id, obra_id)
    res = controles_horarios(obra_id, raiz, hoy, escribir=True, aceptar=False, ahora=ahora)
    lineas = []
    aplicados = avisos = 0
    for f in res["ficheros"]:
        if f.get("aplicado"):
            aplicados += 1
            lineas.append(f"  [PERSONAL] {nombre}: control horario aplicado «{f['nombre']}» ({f['resumen']})")
        elif f["estado"] == lector.A_REVISAR:
            avisos += 1
            motivos = " ".join(m["texto"] for m in f["motivos"])
            lineas.append(f"  [AVISO PERSONAL] {nombre}: el control horario «{f['nombre']}» NO se aplica, hay que mirarlo: "
                          f"{motivos} Dile «actualiza la obra» para verlo y aceptarlo.")
        elif f["estado"] == lector.RECHAZADO:
            avisos += 1
            motivos = " ".join(m["texto"] for m in f["motivos"])
            lineas.append(f"  [AVISO PERSONAL] {nombre}: el control horario «{f['nombre']}» NO vale y no se aplica: {motivos}")
    if not aplicados and not avisos:
        if not res["n_ficheros"]:
            lineas.append(f"  [PERSONAL] sin controles horarios en {nombre}")
        else:
            lineas.append(f"  [PERSONAL] controles horarios de {nombre}: nada nuevo "
                          f"({_plural(res['n_ficheros'], 'fichero ya aplicado', 'ficheros ya aplicados')})")
    return {"lineas": lineas, "aplicados": aplicados, "avisos": avisos, "resultado": res}


# ─── Auditoría (paso 0 de Actualizar_Sagarde.bat) ─────────────────────────
def _incidencia(nivel, codigo, mensaje, solucion, archivo="", obra="(personal)"):
    return {
        "nivel": nivel,
        "area": "Personal",
        "obra": obra,
        "codigo": codigo,
        "mensaje": mensaje,
        "archivo": str(archivo),
        "solucion": solucion,
    }


def _ficheros_de_personal(raiz, obras):
    """Todos los ficheros de datos de personal que se publican (catálogo, obras, trazas)."""
    out = []
    catalogo = Path(raiz) / MOTOR / "personal_catalogo.json"
    if catalogo.is_file():
        out.append(catalogo)
    for oid in obras:
        for nombre in ("personal_obra.json", "personal_jornadas.jsonl"):
            f = _ruta_obra(raiz, obras, oid, nombre)
            if f.is_file():
                out.append(f)
    return out


def _datos_privados(ficheros):
    """Incidencias por DNI, teléfono o correo en el texto de los ficheros. No repite el
    valor encontrado: solo dice el tipo y la línea."""
    out = []
    for f in ficheros:
        try:
            lineas = f.read_text(encoding="utf-8").splitlines()
        except Exception as exc:
            out.append(_incidencia("error", "PERSONAL_ILEGIBLE", f"{f.name}: no se puede leer ({exc})",
                                   "Abrir el fichero y revisarlo o restaurarlo desde git.", f))
            continue
        for n, linea in enumerate(lineas, 1):
            for tipo, patron in PATRONES_PRIVADOS:
                if patron.search(linea):
                    out.append(_incidencia(
                        "error", "PERSONAL_DATO_PRIVADO",
                        f"{f.name} línea {n}: parece contener un {tipo}. Los datos de personal "
                        f"no llevan DNI, teléfono ni correo y este fichero se publica.",
                        "Quitar ese dato del fichero antes de publicar.", f))
    return out


def _traza_valida(d):
    """Una línea de traza: objeto con claves conocidas, `sha256` en hexadecimal y tipos coherentes."""
    if not isinstance(d, dict) or set(d) - CLAVES_TRAZA:
        return False
    if "sha256" in d and not (isinstance(d["sha256"], str) and _SHA256.fullmatch(d["sha256"])):
        return False
    if any(k in d and not isinstance(d[k], str) for k in ("fichero", "de", "a", "nombre")):
        return False
    rechazadas = d.get("rechazadas", 0)
    return isinstance(rechazadas, int) and not isinstance(rechazadas, bool) and rechazadas >= 0


def _trazas(ficheros):
    """Cada línea de personal_jornadas.jsonl: JSON de un objeto con las claves de la traza."""
    out = []
    for f in ficheros:
        if f.suffix != ".jsonl":
            continue
        for n, linea in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if not linea.strip():
                continue
            try:
                d = json.loads(linea)
            except ValueError:
                d = None
            if not _traza_valida(d):
                out.append(_incidencia(
                    "error", "PERSONAL_TRAZA", f"{f.name} línea {n}: no es una anotación válida del registro de controles horarios.",
                    "Revisar el fichero: el registro solo se escribe al aplicar un control horario; no editarlo a mano.", f))
    return out


def _doble_calculo(raiz, obras):
    """Compara los totales de `personal_calculo.js` (node) con `totales_control` (Python)
    por obra y en conjunto. Devuelve incidencias; sin node avisa, no calla."""
    node = shutil.which("node")
    js = Path(raiz) / MOTOR / "personal_calculo.js"
    if not node:
        return [_incidencia("warning", "PERSONAL_NODE_AUSENTE",
                            "No se pudo comprobar el doble cálculo de personal: no hay node en el PATH.",
                            "Instalar Node.js o abrir una consola donde `node --version` funcione.")]
    entrada, esperado = {}, {}
    for oid in obras:
        if _ruta_obra(raiz, obras, oid).is_file():
            entrada[oid] = po.aplanar(raiz, obras, oid)
            esperado[oid] = po.totales_control(raiz, obras, oid)
    if not entrada:
        return []
    entrada["(todas)"] = [f for oid in list(entrada) for f in entrada[oid]]
    esperado["(todas)"] = po.totales_control(raiz, {o: obras[o] for o in entrada if o != "(todas)"})
    try:
        p = subprocess.run(
            [node, "-e", _JS_DOBLE_CALCULO], input=json.dumps(entrada).encode("utf-8"),
            capture_output=True, timeout=60, env=dict(os.environ, PERSONAL_CALCULO=str(js)))
        calculado = json.loads(p.stdout.decode("utf-8"))
        if p.returncode != 0:
            raise RuntimeError(p.stderr.decode("utf-8", "replace")[:300])
    except Exception as exc:
        return [_incidencia("warning", "PERSONAL_NODE_FALLA",
                            f"No se pudo ejecutar personal_calculo.js con node: {type(exc).__name__}: {exc}",
                            "Ejecutar a mano: node -e \"require('./personal_calculo.js')\" en la carpeta del motor.", js)]
    out = []
    for clave, esp in esperado.items():
        for fallo in _comparar(esp, calculado.get(clave)):
            out.append(_incidencia(
                "error", "PERSONAL_DOBLE_CALCULO",
                f"Los totales de personal no coinciden entre Python y personal_calculo.js ({clave}): {fallo}",
                "No publicar: revisar las jornadas de esa obra (horas fuera de rango, extra mayor que las horas…).", js))
    return out


def _cerca(a, b):
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= TOLERANCIA


def _comparar(esperado, js):
    """Lista de diferencias entre `totales_control` y lo que calcula personal_calculo.js."""
    if js is None:
        return ["personal_calculo.js no devolvió resultado"]
    total = js.get("total")
    if esperado is None or total is None:
        return [] if esperado is None and total is None else [
            f"Python {'sin filas' if esperado is None else 'con filas'}, JS {'sin filas' if total is None else 'con filas'}"
            f" (avisos JS: {js.get('avisos')})"]
    out = []
    for clave in ("horas", "extra"):
        if not _cerca(esperado[clave], total[clave]):
            out.append(f"{clave}: Python {esperado[clave]} · JS {total[clave]}")
    for clave in ("dias", "trabajadores"):
        if esperado[clave] != total[clave]:
            out.append(f"{clave}: Python {esperado[clave]} · JS {total[clave]}")
    if js["avisos"].get("filasSinHoras") or js["avisos"].get("filasInvalidas"):
        out.append(f"filas que el cálculo de pantalla no cuenta: {js['avisos']}")
    for nombre, p in esperado["por_trabajador"].items():
        j = js["trabajadores"].get(nombre)
        if j is None:
            out.append(f"{nombre}: no aparece en el cálculo de pantalla")
        elif not (_cerca(p["horas"], j["horas"]) and _cerca(p["extra"], j["extra"]) and p["dias"] == j["dias"]):
            out.append(f"{nombre}: Python {p} · JS {j}")
    return out


def _controles_sin_aplicar(raiz):
    """Un aviso por cada CONTROL HORARIO de REVISIONES que no está aplicado (listo, dudoso o inválido), para que
    nada quede fuera de lo publicado sin que se note. No lanza: si no puede comprobar una obra, lo dice."""
    out = []
    try:
        abiertas, nombres = obras_registro()
    except Exception as exc:
        return [_incidencia("warning", "PERSONAL_CONTROL_NO_COMPROBADO",
                            f"No se pudo mirar si hay controles horarios sin aplicar: {type(exc).__name__}: {exc}",
                            "Ejecutar: py -3.11 personal_integracion.py auditar")]
    hoy = dt.date.today().isoformat()
    for oid, carpeta in abiertas.items():
        revisiones = Path(raiz) / carpeta / "REVISIONES"
        if not revisiones.is_dir():
            continue
        try:
            ficheros = lector.listar(revisiones)
            if not ficheros:
                continue
            fichas = lector.analizar(oid, ficheros, hoy, str(raiz), abiertas)["ficheros"]
        except Exception as exc:
            out.append(_incidencia("warning", "PERSONAL_CONTROL_NO_COMPROBADO",
                                   f"No se pudo mirar los controles horarios de «{nombres[oid]}»: {type(exc).__name__}: {exc}",
                                   "Decirle «actualiza la obra» para verlo.", revisiones, nombres[oid]))
            continue
        for f in fichas:
            motivos = " ".join(m["texto"] for m in f["motivos"])
            if f["estado"] == lector.LISTO:
                out.append(_incidencia(
                    "warning", "PERSONAL_CONTROL_SIN_APLICAR",
                    f"El control horario «{f['nombre']}» está sin aplicar: lo aplicará el propio .bat al generar los paneles.",
                    "Nada que hacer; o decirle «actualiza la obra» para verlo antes.", f["ruta"], nombres[oid]))
            elif f["estado"] == lector.A_REVISAR:
                out.append(_incidencia(
                    "warning", "PERSONAL_CONTROL_A_REVISAR",
                    f"El control horario «{f['nombre']}» hay que mirarlo y NO se aplica: {motivos}",
                    "Decirle «actualiza la obra» para verlo y aceptarlo.", f["ruta"], nombres[oid]))
            elif f["estado"] == lector.RECHAZADO:
                out.append(_incidencia(
                    "warning", "PERSONAL_CONTROL_RECHAZADO",
                    f"El control horario «{f['nombre']}» NO vale y no se aplica: {motivos}",
                    "Corregirlo en la tablet y volver a enviarlo, o quitar el fichero de REVISIONES.", f["ruta"], nombres[oid]))
    return out


def auditar(raiz=None):
    """Comprobaciones de los datos de personal antes de publicar. Lista de incidencias
    (`nivel` «error» frena el .bat, «warning» solo avisa). Los controles horarios sin aplicar se avisan siempre; el
    resto no mira nada si no hay datos de personal en ninguna obra: la función está dormida."""
    raiz = _raiz(raiz)
    obras, _nombres, _cerradas, avisos = universo(raiz)
    out = [_incidencia("warning", "PERSONAL_OBRA_ARCHIVADA", a, "Revisar la carpeta de obras cerradas.") for a in avisos]
    out += _controles_sin_aplicar(raiz)
    ficheros = _ficheros_de_personal(raiz, obras)
    datos = [f for f in ficheros if f.name == "personal_obra.json"]
    if not datos:
        return out
    for nombre in FICHEROS_DECLARADOS:
        if not (Path(raiz) / MOTOR / nombre).is_file():
            out.append(_incidencia("error", "PERSONAL_FICHERO_FALTA",
                                   f"Falta {nombre}, que la función de personal necesita.",
                                   "Restaurarlo desde git (git restore <fichero>).", Path(raiz) / MOTOR / nombre))
    for problema in po.comprobar(raiz, obras):
        out.append(_incidencia("error", "PERSONAL_ESQUEMA", problema,
                               "Corregir el fichero o restaurarlo; no editar a mano los datos de personal."))
    out += _datos_privados(ficheros)
    out += _trazas(ficheros)
    if not any(i["nivel"] == "error" and i["codigo"] in ("PERSONAL_ESQUEMA", "PERSONAL_ILEGIBLE") for i in out):
        # Con el esquema roto aplanar() no es fiable: el doble cálculo se haría sobre basura.
        out += _doble_calculo(raiz, obras)
    return out


# ─── Línea de comandos ─────────────────────────────────────────────────────
def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except AttributeError:
        pass
    p = argparse.ArgumentParser(description="Personal en obra: integración con el entorno real.")
    s = p.add_subparsers(dest="cmd", required=True)
    for nombre in ("exportar-estado", "auditar"):
        q = s.add_parser(nombre)
        q.add_argument("--raiz", default=str(OBRAS_ABIERTAS_DIR))
        if nombre == "exportar-estado":
            q.add_argument("--escribir", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "exportar-estado":
        r = exportar_estado_real(a.raiz, a.escribir)
        print("Escrito" if r["escrito"] else f"No escrito ({r['motivo'] or 'vista previa'})", r["obras"])
        for x in r["avisos"]:
            print("REVISAR", x)
        return 2 if r["avisos"] else 0
    incidencias = auditar(a.raiz)
    for i in incidencias:
        print(f"[{i['nivel'].upper()}] {i['codigo']}: {i['mensaje']}")
    return 2 if any(i["nivel"] == "error" for i in incidencias) else 0


if __name__ == "__main__":
    raise SystemExit(main())
