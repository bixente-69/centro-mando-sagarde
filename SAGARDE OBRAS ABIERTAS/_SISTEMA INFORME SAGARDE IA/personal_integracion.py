# -*- coding: utf-8 -*-
"""Puente entre el motor de obras y los datos de «Personal en obra» (paso 06).

`personal_obra.py` sabe leer y escribir los datos; este módulo sabe DONDE están
dentro del entorno real (obras abiertas del registro y obras archivadas) y
ofrece lo que necesitan quienes los consumen:

- `filas_para_panel`: filas de una obra para su pestaña Personal. Nunca lanza:
  un fallo de datos devuelve un aviso y el panel sale como siempre.
- `exportar_estado_real`: escribe `personal_estado.js` con TODAS las obras del
  registro (también las archivadas, marcadas `cerrada`). Va siempre con el
  registro entero: regenerar una sola obra no debe encoger el estado de la
  tablet ni el ranking.
- `iniciar_obra`: crea un `personal_obra.json` vacío. La app de la tablet solo
  ofrece las obras que figuran en el estado, y una obra solo figura si ya
  tiene su fichero: sin este alta no hay forma de anotar la primera jornada.
- `auditar`: comprobaciones del paso 0 de `Actualizar_Sagarde.bat`.
- La línea de comandos (`ingerir`, `iniciar-obra`, `exportar-estado`,
  `auditar`), que usa `Ingerir_Personal.bat`.

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
    """Escribe `personal_estado.js` con todas las obras (abiertas y archivadas).
    Devuelve {escrito, motivo, obras:{id: nº de filas}, avisos}. No toca el fichero si el
    contenido no cambia (así no se genera un cambio de git por cada regeneración) ni lo
    crea mientras ninguna obra tenga datos de personal."""
    raiz = _raiz(raiz)
    obras, nombres, cerradas, avisos = universo(raiz)
    destino = raiz / MOTOR / "personal_estado.js"
    res = {"escrito": False, "motivo": "", "obras": {}, "avisos": list(avisos)}
    con_datos = [o for o in obras if _ruta_obra(raiz, obras, o).is_file()]
    if not con_datos and not destino.exists():
        res["motivo"] = "sin datos de personal en ninguna obra: no se crea personal_estado.js"
        return res
    viejo = destino.read_text(encoding="utf-8") if destino.exists() else None
    if viejo is not None:
        igual = po.exportar_estado(raiz, obras, nombres, cerradas, generado=_generado_de(viejo))
        if igual == viejo:
            res["motivo"] = "sin cambios"
            res["obras"] = {o: len(po.aplanar(raiz, obras, o)) for o in con_datos}
            return res
    texto = po.exportar_estado(raiz, obras, nombres, cerradas, generado=ahora, escribir=escribir)
    res["escrito"] = bool(escribir)
    res["obras"] = {o: len(po.aplanar(raiz, obras, o)) for o in con_datos}
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


# ─── Alta de una obra en Personal ─────────────────────────────────────────
def iniciar_obra(obra_id, raiz=None, escribir=False):
    """Crea el `personal_obra.json` vacío de una obra abierta del registro (horario base,
    sin jornadas). Si ya existe no lo toca. Devuelve {creada, ruta, motivo}."""
    raiz = _raiz(raiz)
    obras, _ = obras_registro()
    if obra_id not in obras:
        raise ValueError(f"«{obra_id}» no es una obra abierta del registro: {', '.join(sorted(obras))}")
    ruta = _ruta_obra(raiz, obras, obra_id)
    if ruta.exists():
        return {"creada": False, "ruta": str(ruta), "motivo": "ya existe"}
    if escribir:
        po._saveobra(raiz, obras, obra_id, po.cargar_obra(raiz, obras, obra_id))
    return {"creada": bool(escribir), "ruta": str(ruta), "motivo": "" if escribir else "simulación"}


# ─── Auditoría (paso 0 de Actualizar_Sagarde.bat) ─────────────────────────
def _incidencia(nivel, codigo, mensaje, solucion, archivo=""):
    return {
        "nivel": nivel,
        "area": "Personal",
        "obra": "(personal)",
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
                    "error", "PERSONAL_TRAZA", f"{f.name} línea {n}: no es una traza válida de ingesta.",
                    "Revisar el fichero; la traza solo se añade con personal_obra.py ingerir.", f))
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


def auditar(raiz=None):
    """Comprobaciones de los datos de personal antes de publicar. Lista de incidencias
    (`nivel` «error» frena el .bat, «warning» solo avisa). Sin datos de personal en
    ninguna obra devuelve [] y no mira nada más: la función está dormida."""
    raiz = _raiz(raiz)
    obras, _nombres, _cerradas, avisos = universo(raiz)
    out = [_incidencia("warning", "PERSONAL_OBRA_ARCHIVADA", a, "Revisar la carpeta de obras cerradas.") for a in avisos]
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
                               "Corregir el fichero o restaurarlo; no editar a mano el JSON de personal."))
    out += _datos_privados(ficheros)
    out += _trazas(ficheros)
    if not any(i["nivel"] == "error" and i["codigo"] in ("PERSONAL_ESQUEMA", "PERSONAL_ILEGIBLE") for i in out):
        # Con el esquema roto aplanar() no es fiable: el doble cálculo se haría sobre basura.
        out += _doble_calculo(raiz, obras)
    return out


# ─── Línea de comandos (la usa Ingerir_Personal.bat) ──────────────────────
def _confirmar(pregunta, si=False):
    if si:
        return True
    try:
        return input(pregunta).strip().upper() in ("S", "SI", "SÍ")
    except EOFError:
        return False


def cmd_ingerir(fichero, raiz, hoy, si=False, regenerar=True):
    """Simula, enseña, pide confirmación, escribe, exporta el estado y regenera la obra."""
    obras, _ = obras_registro()
    # Las mismas obras que usa todo lo demás (y que las pruebas pueden sustituir), no las que
    # personal_obra.py leería por su cuenta.
    comunes = ["--raiz", str(raiz), "--hoy", hoy, "--obras", ",".join(f"{o}={c}" for o, c in obras.items())]
    print(f"Fichero: {fichero}\n--- SIMULACIÓN (todavía no se escribe nada) ---")
    codigo = po.main(["ingerir", fichero] + comunes)
    if codigo == 1:
        return 1
    if not _confirmar("\n¿Guardar estos datos? Escribe S y pulsa Intro (cualquier otra cosa cancela): ", si):
        print("Cancelado. No se ha escrito nada.")
        return 3
    print("--- ESCRIBIENDO ---")
    codigo = po.main(["ingerir", fichero, "--escribir"] + comunes)
    r = exportar_estado_real(raiz)
    print("Estado para la tablet:", "actualizado" if r["escrito"] else r["motivo"] or "sin cambios")
    for a in r["avisos"]:
        print("REVISAR", a)
    # Solo si el estado ha cambiado hay algo nuevo que enseñar en el panel: un lote rechazado o
    # repetido no cambia nada y no merece minutos de regeneración.
    if regenerar and r["escrito"]:
        try:
            with open(fichero, encoding="utf-8") as f:
                oid = json.load(f)["obra"]
        except Exception:
            oid = None
        script = Path(raiz).parent / "_SISTEMA" / "MOTOR" / "scripts" / "regenerar_obra.py"
        if oid in obras and script.is_file():
            print(f"--- Regenerando el panel de «{oid}» (puede tardar unos minutos) ---")
            subprocess.run([sys.executable, str(script), oid], cwd=str(script.parent))
        else:
            print("No se regenera ningún panel (obra no reconocida).")
    elif regenerar:
        print("No hay datos nuevos: no se regenera ningún panel.")
    if codigo == 0:
        print("\nHecho. NO se ha publicado nada: para publicar, Actualizar_Sagarde.bat.")
    else:
        print("\nTerminado CON RECHAZOS o avisos: revisa lo que pone arriba. NO se ha publicado nada.")
    return codigo


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except AttributeError:
        pass
    p = argparse.ArgumentParser(description="Personal en obra: integración con el entorno real.")
    s = p.add_subparsers(dest="cmd", required=True)
    for nombre in ("ingerir", "iniciar-obra", "exportar-estado", "auditar"):
        q = s.add_parser(nombre)
        q.add_argument("--raiz", default=str(OBRAS_ABIERTAS_DIR))
        if nombre == "ingerir":
            q.add_argument("fichero")
            q.add_argument("--hoy", default=dt.date.today().isoformat())
            q.add_argument("--si", action="store_true", help="no pedir confirmación")
            q.add_argument("--sin-panel", action="store_true")
        elif nombre == "iniciar-obra":
            q.add_argument("obra")
            q.add_argument("--escribir", action="store_true")
        elif nombre == "exportar-estado":
            q.add_argument("--escribir", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "ingerir":
        return cmd_ingerir(a.fichero, a.raiz, a.hoy, a.si, not a.sin_panel)
    if a.cmd == "iniciar-obra":
        try:
            r = iniciar_obra(a.obra, a.raiz, a.escribir)
        except ValueError as exc:
            print("ERROR:", exc)
            return 1
        print(("Creado" if r["creada"] else f"No se crea ({r['motivo']})") + ":", r["ruta"])
        return 0
    if a.cmd == "exportar-estado":
        r = exportar_estado_real(a.raiz, a.escribir)
        print("Escrito" if r["escrito"] else f"No escrito ({r['motivo'] or 'simulación'})", r["obras"])
        for x in r["avisos"]:
            print("REVISAR", x)
        return 2 if r["avisos"] else 0
    incidencias = auditar(a.raiz)
    for i in incidencias:
        print(f"[{i['nivel'].upper()}] {i['codigo']}: {i['mensaje']}")
    return 2 if any(i["nivel"] == "error" for i in incidencias) else 0


if __name__ == "__main__":
    raise SystemExit(main())
