from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote
import json
import os

from avisos import (
    aviso_caducado,
    dias_desde_timestamp,
    es_aviso_por_antiguedad,
)


# _SISTEMA/MOTOR/sagarde_portal.py -> tres niveles hasta la raiz del entorno.
ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = ROOT / "index.html"
# "_SISTEMA" es la carpeta tecnica de cada apartado (norma del 07/08/2026).
# El portal publica como area de negocio TODO lo que encuentra: sin esta
# entrada, _SISTEMA saldria en la portada como si fuera documentacion.
# Ya no hace falta "_MOTOR_SAGARDE": el motor vive dentro de _SISTEMA.
IGNORE_DIRS = {".git", ".memory", "__pycache__", "_PREVIEWS_WORD",
               "_SISTEMA", "docs", "scratch"}
IGNORE_NAMES = {"index.html"}
APP_HINTS = ("app", "panel", "sagarde", "plantilla", "generador")
DOC_EXTS = {".doc", ".docx", ".pdf", ".xls", ".xlsx", ".xlsm"}

# Mapa mental por mantenimiento: profundidad maxima que se recorre y numero
# maximo de archivos que se listan por carpeta (el resto se resume en un
# badge "+N archivo(s) mas") para que carpetas con cientos de fotos no
# revienten la pagina.
MAPA_MAX_DEPTH = 8
MAPA_MAX_ARCHIVOS = 12
MAPA_EXT_ICON = {
    ".pdf": "\U0001F4D5", ".doc": "\U0001F4DD", ".docx": "\U0001F4DD",
    ".xls": "\U0001F4CA", ".xlsx": "\U0001F4CA", ".xlsm": "\U0001F4CA",
    ".jpg": "\U0001F5BC", ".jpeg": "\U0001F5BC", ".png": "\U0001F5BC",
    ".dwg": "\U0001F4D0", ".bak": "\U0001F5C4", ".txt": "\U0001F4C4",
}
AREA_META = {
    "SAGARDE OBRAS ABIERTAS": ("Obras abiertas", "Seguimiento operativo e informes de avance en tiempo real", "#b42318"),
    "POST-VENTAS": ("Post-ventas", "Incidencias, partes resueltos y matrices por obra", "#0b6bcb"),
    "MANTENIMIENTOS": ("Mantenimientos", "Contratos, revisiones e incidencias de mantenimiento", "#16794b"),
    "APLICACIONES": ("Aplicaciones", "Accesos directos a todas las herramientas del entorno Sagarde", "#0a6b5e"),
    "VARIOS": ("Herramientas", "Catálogos, manuales, plantillas y utilidades técnicas", "#6f42a1"),
    "SAGARDE (OLD)": ("Archivo histórico", "Obras cerradas y documentación anterior", "#5f6875"),
}

# Las dos ultimas areas de la portada tienen una landing generada por este
# mismo modulo. La ruta se declara de forma explicita para que una primera
# ejecucion limpia ya publique el enlace correcto; depender de que el HTML
# existiera antes obligaba a ejecutar el generador dos veces.
AREA_ENTRYPOINTS = {
    "VARIOS": "index.html",
    "SAGARDE (OLD)": "index.html",
}

# `VARIOS/APPS SAGARDE` contiene datos personales y esta excluido de Git. Un
# HTML generado si se publica, de modo que tampoco puede incorporar nombres o
# rutas procedentes de esa carpeta.
HERRAMIENTAS_PRIVADAS = {"APPS SAGARDE"}
HERRAMIENTAS_EXTS = DOC_EXTS | {
    ".html", ".htm", ".dwg", ".jpg", ".jpeg", ".png", ".gif", ".txt",
}
HERRAMIENTAS_RUIDO_EXTS = {".bak", ".dwl", ".dwl2", ".log", ".tmp"}
HERRAMIENTAS_RUIDO_NOMBRES = {"index.html", "videosag.mp4", "plot.log"}
HERRAMIENTAS_DESCRIPCIONES = {
    "BATERIAS DE CONDENSADORES": "Calculo, informes y documentacion de baterias",
    "CATALOGOS": "Catalogos tecnicos y referencias de fabricantes",
    "CENTRALIZACIONES": "Documentacion de centralizaciones y cajas",
    "COTAS VIVIENDAS": "Planos y criterios de montaje en viviendas",
    "DUDAS RBTE": "Consultas y documentacion de apoyo reglamentario",
    "HERRAMIENTAS": "Referencias visuales y utiles de trabajo",
    "LOGOTIPOS CLIENTES": "Recursos graficos de clientes y colaboradores",
    "MANUALES": "Manuales tecnicos y documentacion de equipos",
    "PEGATINAS VIVIENDA": "Plantillas y modelos de identificacion",
    "PLANILLA": "Documentos de planilla y seguimiento interno",
    "RECUENTO MECANISMOS": "Modelos de calculo y recuento de mecanismos",
    "REVISIONES": "Plantillas y archivos auxiliares de revision",
    "TELECOMUNICACIONES": "Esquemas y referencias de telecomunicaciones",
    "TIERRAS": "Mediciones, informes y recursos de puesta a tierra",
    "UNIFILARES": "Planos y bases de esquemas unifilares",
    "VIDEOPORTEROS": "Referencias de equipos de videoportero",
}

# Contratos de solo lectura publicados por los subsistemas ya existentes.
# Si no existen (primera ejecucion, o el subsistema no se ha corrido todavia)
# el portal degrada con gracia: no inventa cifras, simplemente omite la
# seccion o cae al recuento generico de carpetas/archivos.
RESUMEN_OBRAS_JSON = ROOT / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA" / "resumen_obras.json"
RESUMEN_POSTVENTAS_JSON = ROOT / "POST-VENTAS" / "_SISTEMA" / "postventas_resumen.json"

DIAS_OBRA_INACTIVA = 14  # aviso entre 15 y 399 dias sin archivos nuevos
DIAS_POSTVENTA_RECIENTE = 45  # ya definido asi en postventas_index.py, se reutiliza el mismo criterio
DIAS_MANTENIMIENTO_INACTIVO = 90  # aviso entre 91 y 399 dias sin revisiones o documentos nuevos


def url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    return quote(rel, safe="/()[]!$&'()*+,;=:@-._~")


def visible(path: Path) -> bool:
    return not any(part in IGNORE_DIRS or part.startswith("~$") or part.startswith(".") for part in path.relative_to(ROOT).parts)


def es_carpeta_visible(p: Path) -> bool:
    return p.is_dir() and p.name not in IGNORE_DIRS and not p.name.startswith(".")


def es_ruta_privada_herramientas(path: Path) -> bool:
    """Indica si una ruta pertenece al archivo personal no publicable."""
    try:
        partes = path.relative_to(ROOT).parts
    except ValueError:
        return False
    return (
        len(partes) >= 2
        and partes[0] == "VARIOS"
        and partes[1] in HERRAMIENTAS_PRIVADAS
    )


def load_json_safe(path: Path) -> dict | None:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return None


def clase_pct(p: float) -> str:
    return "ok" if p >= 70 else "warn" if p >= 40 else "bad"


def dias_desde(ts: float | None) -> int | None:
    return dias_desde_timestamp(ts)


def scan_area(folder: Path) -> dict:
    dirs, files = [], []
    for path in folder.rglob("*"):
        if not visible(path) or es_ruta_privada_herramientas(path):
            continue
        (dirs if path.is_dir() else files).append(path)
    docs = [p for p in files if p.suffix.lower() in DOC_EXTS]
    latest = max((p.stat().st_mtime for p in files), default=folder.stat().st_mtime)
    title, description, color = AREA_META.get(folder.name, (folder.name.title(), "Carpeta de trabajo", "#475467"))
    entry_rel = AREA_ENTRYPOINTS.get(folder.name, "index.html")
    entry = folder / entry_rel
    tiene_landing = folder.name in AREA_ENTRYPOINTS or entry.exists()
    return {
        "name": folder.name, "title": title, "description": description, "color": color,
        "url": url(entry if tiene_landing else folder) + ("" if tiene_landing else "/"),
        "folders": len(dirs), "files": len(files), "docs": len(docs), "latest": latest,
    }


_MTIME_STAT_BUDGET = 800  # tope de stat() individuales para calcular "ultima actividad"


def _contar_archivos_carpeta(path: Path, _presupuesto: list[int] | None = None) -> tuple[int, float]:
    """Cuenta archivos visibles bajo una carpeta (recursivo) y aproxima su fecha
    de modificacion mas reciente. Usa os.scandir en vez de Path.rglob()+stat()
    por archivo (mucho mas rapido en unidades de red/OneDrive), y limita el
    numero de stat() individuales a _MTIME_STAT_BUDGET: hay contratos de
    mantenimiento con miles de fotos en una sola carpeta, y stat-ear cada una
    solo para la fecha "ultima actividad" no compensa el coste. El recuento de
    archivos siempre es exacto; la fecha puede quedar aproximada solo en esas
    carpetas gigantes."""
    if _presupuesto is None:
        _presupuesto = [_MTIME_STAT_BUDGET]
    n = 0
    ultima = 0.0
    try:
        with os.scandir(path) as it:
            for entry in it:
                if not visible(Path(entry.path)) or entry.name in IGNORE_NAMES:
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        sub_n, sub_ultima = _contar_archivos_carpeta(Path(entry.path), _presupuesto)
                        n += sub_n
                        if sub_ultima > ultima:
                            ultima = sub_ultima
                    elif entry.is_file(follow_symlinks=False):
                        n += 1
                        if _presupuesto[0] > 0:
                            _presupuesto[0] -= 1
                            mtime = entry.stat().st_mtime
                            if mtime > ultima:
                                ultima = mtime
                except OSError:
                    continue
    except OSError:
        pass
    if ultima == 0.0:
        ultima = path.stat().st_mtime
    return n, ultima


def escanear_mantenimientos() -> list[dict]:
    json_path = (ROOT / "MANTENIMIENTOS" / "_SISTEMA"
                 / "mantenimientos_resumen.json")
    if json_path.is_file():
        try:
            with open(json_path, encoding="utf-8") as f:
                res = json.load(f)
            if res and "contratos" in res:
                contratos = []
                for c in res["contratos"]:
                    p = ROOT / "MANTENIMIENTOS" / c["carpeta"]
                    contratos.append({
                        "nombre": c["nombre"],
                        "n_archivos": c["n_archivos"],
                        "ultima_ts": c["ultima_ts"],
                        "url": url(p) + "/index.html",
                        "sub_url": quote(c["carpeta"], safe="/()[]!$&'()*+,;=:@-._~") + "/index.html",
                        "path": p,
                        "dias_inactivo": c.get("dias_inactivo", 0),
                        "estado_actividad": c.get("estado_actividad", "al_dia")
                    })
                return contratos
        except Exception as exc:
            # Antes era 'except Exception: pass'. Un JSON corrupto degradaba
            # al barrido de carpetas sin que nadie se enterase, y el barrido
            # da otros numeros. Si pasa, que se vea.
            print(f"  [AVISO] No se pudo leer {json_path.name} ({exc}). "
                  f"Se recurre al barrido de carpetas, que puede dar un "
                  f"recuento distinto.")

    base = ROOT / "MANTENIMIENTOS"
    contratos = []
    if base.is_dir():
        for p in sorted(base.iterdir()):
            if not p.is_dir():
                continue
            # El barrido NO tenia filtro: con el JSON fuera de sitio publicaba
            # _SISTEMA como un contrato de mantenimiento mas.
            if p.name in IGNORE_DIRS:
                continue
            n_archivos, ultima = _contar_archivos_carpeta(p)
            nombre = p.name.replace("MANTENIMIENTO ", "", 1).strip() or p.name
            contratos.append({"nombre": nombre, "n_archivos": n_archivos, "ultima_ts": ultima, "url": url(p) + "/index.html", "sub_url": quote(p.name, safe="/()[]!$&'()*+,;=:@-._~") + "/index.html", "path": p})
    contratos.sort(key=lambda c: -c["ultima_ts"])
    return contratos


def escanear_planilla() -> dict | None:
    base = ROOT / "VARIOS" / "PLANILLA"
    if not base.is_dir():
        return None
    files = [f for f in base.rglob("*") if f.is_file() and visible(f)]
    if not files:
        return None
    ultima = max(f.stat().st_mtime for f in files)
    return {"n_archivos": len(files), "ultima_ts": ultima}


def contar_obras_abiertas_carpetas() -> int:
    base = ROOT / "SAGARDE OBRAS ABIERTAS"
    if not base.is_dir():
        return 0
    return sum(1 for p in base.iterdir() if p.is_dir() and not p.name.startswith("_"))


def escanear_obras_cerradas() -> list[dict]:
    base = ROOT / "SAGARDE (OLD)" / "OBRAS CERRADAS"
    obras = []
    if not base.is_dir():
        return obras
    for p in base.iterdir():
        if not p.is_dir():
            continue
        files = [f for f in p.rglob("*") if f.is_file() and visible(f)]
        ultima = max((f.stat().st_mtime for f in files), default=p.stat().st_mtime)
        obras.append({"nombre": p.name, "ultima_ts": ultima, "url": url(p) + "/", "sub_url": quote(p.name, safe="/()[]!$&'()*+,;=:@-._~") + "/"})
    obras.sort(key=lambda o: -o["ultima_ts"])
    return obras


def _es_archivo_herramienta(path: Path) -> bool:
    """Filtra copias tecnicas y formatos que no son recursos consultables."""
    nombre = path.name.lower()
    if not path.is_file() or not visible(path) or es_ruta_privada_herramientas(path):
        return False
    if nombre in HERRAMIENTAS_RUIDO_NOMBRES or path.suffix.lower() in HERRAMIENTAS_RUIDO_EXTS:
        return False
    if "backup" in nombre or "copia" in nombre or nombre.startswith("antes_"):
        return False
    return path.suffix.lower() in HERRAMIENTAS_EXTS


def _archivo_herramienta(base: Path, path: Path) -> dict:
    rel = path.relative_to(base)
    ext = path.suffix.lower()
    return {
        "nombre": path.name,
        "ruta": rel.as_posix(),
        "url": quote(rel.as_posix(), safe=_RUTA_SAFE),
        "extension": ext[1:].upper() if ext else "ARCHIVO",
        "es_documento": ext in DOC_EXTS,
        "mtime": path.stat().st_mtime,
    }


def escanear_herramientas() -> dict:
    """Inventaria la biblioteca tecnica publica de VARIOS.

    La zona personal se excluye antes de construir el resultado: el HTML de
    esta portada se publica y no debe actuar como indice lateral de datos que
    Git ignora deliberadamente.
    """
    base = ROOT / "VARIOS"
    resultado = {
        "categorias": [], "generales": [], "n_archivos": 0,
        "n_documentos": 0, "ultima_ts": None,
    }
    if not base.is_dir():
        return resultado

    generales = [
        _archivo_herramienta(base, p)
        for p in sorted(base.iterdir(), key=lambda x: x.name.lower())
        if _es_archivo_herramienta(p)
    ]
    categorias = []
    for carpeta in sorted(base.iterdir(), key=lambda x: x.name.lower()):
        if (
            not carpeta.is_dir()
            or carpeta.name in HERRAMIENTAS_PRIVADAS
            or not es_carpeta_visible(carpeta)
        ):
            continue
        archivos = [
            _archivo_herramienta(base, p)
            for p in sorted(carpeta.rglob("*"), key=lambda x: x.as_posix().lower())
            if _es_archivo_herramienta(p)
        ]
        if not archivos:
            continue
        categorias.append({
            "nombre": carpeta.name,
            "descripcion": HERRAMIENTAS_DESCRIPCIONES.get(
                carpeta.name, f"Recursos tecnicos de {carpeta.name.lower()}"
            ),
            "archivos": archivos,
            "n_archivos": len(archivos),
            "n_documentos": sum(1 for a in archivos if a["es_documento"]),
            "ultima_ts": max(a["mtime"] for a in archivos),
        })

    todos = generales + [a for c in categorias for a in c["archivos"]]
    resultado.update({
        "categorias": categorias,
        "generales": generales,
        "n_archivos": len(todos),
        "n_documentos": sum(1 for a in todos if a["es_documento"]),
        "ultima_ts": max((a["mtime"] for a in todos), default=base.stat().st_mtime),
    })
    return resultado


_SHARED_CSS = (
    ":root{--bg:#eef1f4;--ink:#182230;--muted:#647184;--line:#d0d5dd;--brand:#b42318;"
    "--nav:#0b1f3a;--nav2:#123a63;--accent:#f5a524;--ok:#2e9e5b;--radius:9px}"
    "*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif}a{color:inherit}button,input{font:inherit}"
    ".top{background:linear-gradient(120deg,var(--nav),var(--nav2));color:#fff;border-bottom:4px solid var(--brand)}"
    ".top-inner{max-width:1440px;margin:auto;padding:18px 28px;display:flex;align-items:center;gap:20px}"
    ".logo{width:min(290px,22vw);height:auto;object-fit:contain;border-radius:9px;"
    "box-shadow:0 0 0 3px var(--brand),0 6px 28px rgba(0,0,0,.5)}"
    ".identity{min-width:0}.identity strong{font-size:21px;display:block}.identity span{font-size:12px;color:#c7d3e3}"
    ".top-actions{margin-left:auto;display:flex;gap:8px}"
    ".top-actions a{text-decoration:none;border:1px solid rgba(255,255,255,.35);color:#fff;"
    "padding:9px 12px;border-radius:5px;font-size:13px;font-weight:600}"
    ".shell{max-width:1440px;margin:auto;padding:24px 28px 38px}"
    "h1{font-size:28px;margin:0 0 5px}p.sub{margin:0 0 18px;color:var(--muted)}h2{font-size:17px;margin:0}"
    ".intro{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:18px}"
    ".section-head{display:flex;align-items:center;justify-content:space-between;margin:22px 0 10px;gap:12px;flex-wrap:wrap}"
    ".section-head span{font-size:12px;color:var(--muted)}"
    ".search-wrap{width:min(470px,100%);position:relative}"
    ".search{width:100%;height:42px;padding:0 42px 0 14px;border:1px solid #98a2b3;border-radius:6px;background:#fff;font:inherit}"
    ".search-symbol{position:absolute;right:14px;top:11px;color:#667085}"
    ".pv-list{display:grid;gap:6px;margin-bottom:8px}"
    ".pv-row{display:flex;justify-content:space-between;align-items:center;gap:12px;background:#fff;"
    "border:1px solid var(--line);border-radius:8px;padding:10px 14px;text-decoration:none;color:var(--ink)}"
    ".pv-row:hover{background:#f8fafc}.pv-main strong{display:block;font-size:13px}"
    ".pv-main small{color:var(--muted);font-size:11px}.pv-badge{font-size:11px;color:var(--muted);white-space:nowrap}"
    ".empty{display:none;padding:28px;text-align:center;color:var(--muted);background:#fff;"
    "border:1px solid var(--line);border-radius:var(--radius)}"
    ".footer{font-size:11px;color:var(--muted);text-align:right;margin-top:16px}"
    "@media(max-width:900px){.logo{width:190px}.intro{flex-direction:column;align-items:stretch}.search-wrap{width:100%}}"
    "@media(max-width:600px){.top-inner,.shell{padding-left:14px;padding-right:14px}.logo{width:160px}.top-actions{display:none}}"
)


_LANDING_CSS = (
    ".breadcrumb{display:inline-flex;align-items:center;gap:7px;margin:0 0 14px;color:var(--muted);"
    "font-size:12px;font-weight:650;text-decoration:none}.breadcrumb:hover{color:var(--nav)}"
    ".metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:0 0 24px}"
    ".metric{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:15px 16px;"
    "box-shadow:0 1px 2px rgba(16,24,40,.03)}"
    ".metric strong{display:block;font-size:22px;line-height:1.1;color:var(--nav)}"
    ".metric span{display:block;margin-top:5px;font-size:11.5px;color:var(--muted)}"
    ".toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap}"
    ".filter-select{height:42px;min-width:160px;padding:0 34px 0 12px;border:1px solid #98a2b3;"
    "border-radius:6px;background:#fff;color:var(--ink);font:inherit}"
    ".result-count{font-size:12px;color:var(--muted);margin-left:auto}"
    ".empty-panel{display:none;background:#fff;border:1px dashed #98a2b3;border-radius:var(--radius);"
    "padding:34px 18px;text-align:center;color:var(--muted)}"
    "a:focus-visible,summary:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid rgba(11,107,203,.28);outline-offset:2px}"
    "@media(max-width:900px){.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}"
    "@media(max-width:600px){.metric-grid{gap:8px}.metric{padding:13px}.metric strong{font-size:20px}"
    ".toolbar>*{width:100%}.result-count{margin-left:0}.filter-select{min-width:0}}"
)


_HERRAMIENTAS_CSS = _LANDING_CSS + (
    ".quick-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin-bottom:8px}"
    ".quick-card{position:relative;overflow:hidden;background:#fff;border:1px solid var(--line);border-top:4px solid #6f42a1;"
    "border-radius:var(--radius);padding:17px 18px;text-decoration:none;transition:transform .12s,box-shadow .12s}"
    ".quick-card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(16,24,40,.1)}"
    ".quick-kicker{display:block;color:#6f42a1;font-size:10.5px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}"
    ".quick-card strong{display:block;margin:8px 0 5px;font-size:16px}.quick-card small{display:block;color:var(--muted);line-height:1.4}"
    ".quick-go{position:absolute;right:17px;top:17px;color:#6f42a1;font-weight:800}"
    ".tool-catalog{display:grid;gap:9px}.tool-category{background:#fff;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}"
    ".tool-category[open]{box-shadow:0 4px 14px rgba(16,24,40,.07)}"
    ".tool-category>summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:42px minmax(0,1fr) auto 18px;"
    "align-items:center;gap:12px;padding:14px 16px}.tool-category>summary::-webkit-details-marker{display:none}"
    ".tool-category>summary:hover{background:#faf9fc}.folder-mark{width:38px;height:38px;border-radius:8px;"
    "display:grid;place-items:center;background:#f0eafb;color:#6f42a1;font-size:11px;font-weight:850;letter-spacing:.04em}"
    ".category-main{min-width:0}.category-main strong{display:block;font-size:14px}.category-main small{display:block;"
    "margin-top:3px;color:var(--muted);font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
    ".category-count{text-align:right;color:var(--muted);font-size:11px;white-space:nowrap}.chevron{color:#6f42a1;transition:transform .15s}"
    ".tool-category[open] .chevron{transform:rotate(90deg)}"
    ".asset-list{border-top:1px solid var(--line);background:#fbfcfd;padding:6px 12px 10px}"
    ".asset-row{display:grid;grid-template-columns:43px minmax(0,1fr) auto 18px;align-items:center;gap:10px;"
    "padding:9px 8px;border-bottom:1px solid #eaecf0;text-decoration:none;border-radius:5px}"
    ".asset-row:last-child{border-bottom:0}.asset-row:hover{background:#f1f4f8}"
    ".file-type{display:inline-grid;place-items:center;min-width:38px;height:24px;border-radius:4px;background:#e9f2fc;"
    "color:#0b6bcb;font-size:9px;font-weight:850;letter-spacing:.04em}.asset-main{min-width:0}"
    ".asset-main strong,.asset-main small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
    ".asset-main strong{font-size:12.5px}.asset-main small{font-size:10.5px;color:var(--muted);margin-top:2px}"
    ".asset-date{font-size:10.5px;color:var(--muted);white-space:nowrap}.asset-go{color:#667085}"
    "@media(max-width:600px){.tool-category>summary{grid-template-columns:36px minmax(0,1fr) 16px;padding:12px}"
    ".folder-mark{width:34px;height:34px}.category-count{display:none}.asset-row{grid-template-columns:39px minmax(0,1fr) 16px;padding:9px 4px}"
    ".asset-date{display:none}.quick-grid{grid-template-columns:1fr}}"
)


_ARCHIVO_CSS = _LANDING_CSS + (
    ".archive-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}"
    ".archive-row{display:grid;grid-template-columns:43px minmax(0,1fr) auto 18px;align-items:center;gap:11px;"
    "background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:12px 14px;text-decoration:none;"
    "transition:transform .12s,box-shadow .12s,border-color .12s}"
    ".archive-row:hover{transform:translateY(-1px);box-shadow:0 5px 16px rgba(16,24,40,.08);border-color:#98a2b3}"
    ".archive-mark{width:40px;height:40px;display:grid;place-items:center;border-radius:8px;background:#eef0f3;"
    "color:#5f6875;font-size:10px;font-weight:850;letter-spacing:.05em}.archive-main{min-width:0}"
    ".archive-main strong{display:block;font-size:13px;line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
    ".archive-main small{display:block;margin-top:4px;color:var(--muted);font-size:10.5px}"
    ".archive-date{font-size:10.5px;color:var(--muted);white-space:nowrap}.archive-go{color:#667085}"
    "@media(max-width:900px){.archive-grid{grid-template-columns:1fr}}"
    "@media(max-width:600px){.archive-row{grid-template-columns:39px minmax(0,1fr) 16px;padding:11px}.archive-date{display:none}}"
)


_MAPA_CSS = (
    ".stats-mapa{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 20px}"
    ".stats-mapa .kpi{background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 16px;min-width:130px}"
    ".stats-mapa .kpi strong{display:block;font-size:20px}"
    ".stats-mapa .kpi span{font-size:11px;color:var(--muted)}"
    ".back-link{display:inline-block;margin:0 0 6px;font-size:12px;color:var(--muted);text-decoration:none}"
    ".back-link:hover{color:var(--ink)}"
    ".mapa{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;overflow-x:auto}"
    ".mapa-root{font-size:16px;font-weight:700;display:flex;align-items:center;gap:8px;margin-bottom:8px;color:#16794b}"
    ".ramas{margin:2px 0 2px 11px;padding-left:18px;border-left:2px dashed #c7cdd6}"
    ".nodo{margin:3px 0}"
    ".nodo-carpeta{list-style:none}"
    ".nodo-carpeta>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;"
    "padding:5px 10px;border-radius:6px;background:#f2f6f4;border:1px solid #dce4e0;font-weight:600}"
    ".nodo-carpeta>summary::-webkit-details-marker{display:none}"
    ".nodo-carpeta>summary:hover{background:#e7efe9}"
    ".nodo-carpeta[open]>summary{background:#e2efe8}"
    ".nodo-carpeta>summary .cnt{margin-left:auto;font-size:10px;color:var(--muted);white-space:nowrap;font-weight:400}"
    ".nodo-archivo,.nodo-mas,.nodo-carpeta-vacia,.nodo-carpeta-trunc{display:flex;align-items:center;gap:8px;"
    "padding:4px 10px;font-size:12.5px;color:var(--ink);text-decoration:none;border-radius:5px}"
    ".nodo-mas,.nodo-carpeta-trunc{color:var(--muted);font-style:italic}"
    "a.nodo-archivo,a.nodo-mas,a.nodo-carpeta-trunc{cursor:pointer}"
    "a.nodo-archivo:hover{background:#eef4ff;color:#0b6bcb;text-decoration:underline}"
    "a.nodo-mas:hover,a.nodo-carpeta-trunc:hover{background:#f2f4f7;text-decoration:underline}"
    ".nodo .ico{font-size:14px}"
    ".nodo .nom{overflow-wrap:anywhere}"
)


def _icono_archivo(nombre: str) -> str:
    return MAPA_EXT_ICON.get(Path(nombre).suffix.lower(), "\U0001F4C4")


_RUTA_SAFE = "()[]!$&'*+,;=:@-._~"


def construir_mapa_carpeta(path: Path, depth: int = 0, rel_prefix: str = "") -> dict:
    """Arbol recursivo de una carpeta para el 'mapa mental' de cada mantenimiento.
    Limita profundidad y numero de archivos listados por carpeta: cuenta todo,
    pero solo renderiza una muestra para que carpetas con cientos de fotos
    no revienten la pagina.
    Usa os.scandir en vez de Path.iterdir()+is_dir()/is_file() porque en unidades
    en red/OneDrive cada stat() por separado es lento; scandir trae el tipo de
    entrada en la misma llamada y evita miles de round-trips en carpetas con
    muchos archivos (se han visto carpetas de mantenimiento con miles de fotos).
    rel_prefix acumula la ruta relativa (ya url-encoded) desde la carpeta del
    contrato, para poder enlazar cada archivo/carpeta directamente al original."""
    carpetas: list[os.DirEntry] = []
    archivos: list[os.DirEntry] = []
    try:
        with os.scandir(path) as it:
            for entry in it:
                if not visible(Path(entry.path)) or entry.name in IGNORE_NAMES:
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        carpetas.append(entry)
                    elif entry.is_file(follow_symlinks=False):
                        archivos.append(entry)
                except OSError:
                    continue
    except OSError:
        pass
    carpetas.sort(key=lambda e: e.name.lower())
    archivos.sort(key=lambda e: e.name.lower())
    hijos: list[dict] = []
    if depth < MAPA_MAX_DEPTH:
        hijos.extend(
            construir_mapa_carpeta(Path(e.path), depth + 1, rel_prefix + quote(e.name, safe=_RUTA_SAFE) + "/")
            for e in carpetas
        )
    else:
        hijos.extend(
            {"nombre": e.name, "tipo": "carpeta_truncada", "hijos": [], "n_carpetas": 0, "n_archivos": 0,
             "ruta": rel_prefix + quote(e.name, safe=_RUTA_SAFE) + "/"}
            for e in carpetas
        )
    for e in archivos[:MAPA_MAX_ARCHIVOS]:
        hijos.append({"nombre": e.name, "tipo": "archivo", "hijos": [], "n_carpetas": 0, "n_archivos": 0,
                      "ruta": rel_prefix + quote(e.name, safe=_RUTA_SAFE)})
    restantes = len(archivos) - MAPA_MAX_ARCHIVOS
    if restantes > 0:
        hijos.append({"nombre": f"+{restantes} archivo(s) mas", "tipo": "mas", "hijos": [], "n_carpetas": 0, "n_archivos": 0,
                      "ruta": rel_prefix or "./"})
    return {"nombre": path.name, "tipo": "carpeta", "n_carpetas": len(carpetas), "n_archivos": len(archivos), "hijos": hijos, "ruta": rel_prefix or "./"}


def _render_nodo_mapa(nodo: dict, nivel: int) -> str:
    tipo = nodo["tipo"]
    if tipo == "archivo":
        return (f'<a class="nodo nodo-archivo" href="{escape(nodo["ruta"])}" target="_blank" rel="noopener">'
                f'<span class="ico">{_icono_archivo(nodo["nombre"])}</span><span class="nom">{escape(nodo["nombre"])}</span></a>')
    if tipo == "mas":
        return (f'<a class="nodo nodo-mas" href="{escape(nodo["ruta"])}" target="_blank" rel="noopener">'
                f'<span class="ico">…</span><span class="nom">{escape(nodo["nombre"])}</span></a>')
    if tipo == "carpeta_truncada":
        return (f'<a class="nodo nodo-carpeta-trunc" href="{escape(nodo["ruta"])}" target="_blank" rel="noopener">'
                f'<span class="ico">\U0001F4C1</span><span class="nom">{escape(nodo["nombre"])}</span>'
                f'<span class="cnt">demasiado profundo, abrir carpeta &rarr;</span></a>')
    resumen = []
    if nodo["n_carpetas"]:
        resumen.append(f'{nodo["n_carpetas"]} carpeta(s)')
    if nodo["n_archivos"]:
        resumen.append(f'{nodo["n_archivos"]} archivo(s)')
    resumen_txt = " &middot; ".join(resumen) or "vacia"
    if not nodo["hijos"]:
        return f'<div class="nodo nodo-carpeta-vacia"><span class="ico">\U0001F4C1</span><span class="nom">{escape(nodo["nombre"])}</span><span class="cnt">vacia</span></div>'
    abierto = " open" if nivel <= 1 else ""
    hijos_html = "".join(_render_nodo_mapa(h, nivel + 1) for h in nodo["hijos"])
    return (
        f'<details class="nodo nodo-carpeta"{abierto}>'
        f'<summary><span class="ico">\U0001F4C1</span><span class="nom">{escape(nodo["nombre"])}</span><span class="cnt">{resumen_txt}</span></summary>'
        f'<div class="ramas">{hijos_html}</div>'
        f'</details>'
    )


def _contar_recursivo(nodo: dict) -> tuple[int, int]:
    """Suma archivos y subcarpetas de todo el arbol ya construido, sin volver
    a tocar el disco (evita un segundo recorrido de la carpeta real)."""
    archivos, carpetas = nodo.get("n_archivos", 0), nodo.get("n_carpetas", 0)
    for h in nodo["hijos"]:
        if h["tipo"] == "carpeta":
            sa, sc = _contar_recursivo(h)
            archivos += sa
            carpetas += sc
    return archivos, carpetas


def generar_pagina_mantenimiento(m: dict) -> None:
    """Genera, dentro de la propia carpeta del contrato de mantenimiento, una
    hoja de presentacion corporativa con el mapa mental (arbol interactivo)
    de esa carpeta. Sustituye el listado de directorio "en crudo" que se veia
    antes al entrar en un mantenimiento concreto. Se regenera en cada
    ejecucion del motor (sagarde_portal.py), igual que el resto de paginas."""
    path: Path = m["path"]
    if not path.is_dir():
        return
    arbol = construir_mapa_carpeta(path)
    _, subcarpetas = _contar_recursivo(arbol)
    ramas_html = "".join(_render_nodo_mapa(h, 1) for h in arbol["hijos"]) or '<p style="color:var(--muted)">Carpeta vacia.</p>'
    nav = [
        ("⌂ Portal", "../../index.html"),
        ("Obras abiertas", "../../SAGARDE%20OBRAS%20ABIERTAS/index.html"),
        ("Post-ventas", "../../POST-VENTAS/index.html"),
        ("Mantenimientos", "../index.html"),
        ("Obras cerradas", "../../SAGARDE%20(OLD)/OBRAS%20CERRADAS/index.html"),
    ]
    stats = [
        (m["n_archivos"], "archivos"),
        (subcarpetas, "subcarpetas"),
        (fmt_date(m["ultima_ts"]), "ultima actividad"),
    ]
    stats_html = "".join(f'<div class="kpi"><strong>{escape(str(v))}</strong><span>{escape(k)}</span></div>' for v, k in stats)
    content = (
        f'<a class="back-link" href="../index.html">&larr; Mantenimientos</a>'
        f'<h1>{escape(m["nombre"])}</h1>'
        f'<p class="sub">Mapa de la carpeta de mantenimiento &middot; se regenera automaticamente con cada actualizacion de Sagarde</p>'
        f'<div class="stats-mapa">{stats_html}</div>'
        f'<div class="mapa"><div class="mapa-root"><span class="ico">\U0001F4C1</span>{escape(m["nombre"])}</div>'
        f'<div class="ramas">{ramas_html}</div></div>'
    )
    (path / "index.html").write_text(
        _page_html(m["nombre"], "Mantenimiento · Sagarde", "../../POST-VENTAS/logo_sagarde.jpg", nav, content, _MAPA_CSS),
        encoding="utf-8",
    )


def _page_html(
    title: str,
    subtitle: str,
    logo: str,
    nav: list[tuple[str, str]],
    content: str,
    extra_css: str = "",
    actualizado_ts: float | None = None,
) -> str:
    nav_html = "".join(f'<a href="{u}">{escape(l)}</a>' for l, u in nav)
    gen = (
        fmt_date(actualizado_ts)
        if actualizado_ts is not None
        else datetime.now().strftime("%d/%m/%Y %H:%M")
    )
    return (
        f'<!doctype html><html lang="es"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Sagarde | {escape(title)}</title>'
        f'<style>{_SHARED_CSS}{extra_css}</style></head><body>'
        f'<header class="top"><div class="top-inner">'
        f'<img class="logo" src="{logo}" alt="Sagarde">'
        f'<div class="identity"><strong>{escape(title)}</strong><span>{escape(subtitle)}</span></div>'
        f'<nav class="top-actions">{nav_html}</nav>'
        f'</div></header>'
        f'<main class="shell">{content}</main>'
        f'<p class="footer">Actualizado {gen} · Ejecuta Actualizar_Sagarde.bat para refrescar</p>'
        f'</body></html>'
    )


def _escribir_html_si_cambia(output: Path, contenido: str) -> bool:
    """Escribe una salida solo cuando su contenido real ha cambiado."""
    try:
        if output.is_file() and output.read_text(encoding="utf-8") == contenido:
            return False
    except OSError:
        pass
    output.write_text(contenido, encoding="utf-8")
    return True


def _anio_obra_cerrada(nombre: str) -> str:
    primero = nombre.strip().split(maxsplit=1)[0] if nombre.strip() else ""
    if len(primero) == 4 and primero.isdigit() and 1900 <= int(primero) <= 2100:
        return primero
    return "Sin año"


def _contenido_archivo_historico(
    obras_cerradas: list[dict],
    portal_href: str,
    prefijo_obras: str,
) -> str:
    anios = sorted(
        {_anio_obra_cerrada(o["nombre"]) for o in obras_cerradas} - {"Sin año"},
        reverse=True,
    )
    opciones = "".join(f'<option value="{a}">{a}</option>' for a in anios)
    if any(_anio_obra_cerrada(o["nombre"]) == "Sin año" for o in obras_cerradas):
        opciones += '<option value="Sin año">Sin año en el nombre</option>'

    ultima = max((o["ultima_ts"] for o in obras_cerradas), default=None)
    con_anio = sum(_anio_obra_cerrada(o["nombre"]) != "Sin año" for o in obras_cerradas)
    stats = (
        f'<div class="metric"><strong>{len(obras_cerradas)}</strong><span>obras archivadas</span></div>'
        f'<div class="metric"><strong>{len(anios)}</strong><span>años identificados</span></div>'
        f'<div class="metric"><strong>{con_anio}</strong><span>obras clasificadas por año</span></div>'
        f'<div class="metric"><strong>{fmt_date(ultima) if ultima else "—"}</strong><span>última actividad del archivo</span></div>'
    )
    rows = "".join(
        f'<a class="archive-row" href="{escape(prefijo_obras + o["sub_url"], quote=True)}" '
        f'data-search="{escape(o["nombre"].lower(), quote=True)}" data-year="{_anio_obra_cerrada(o["nombre"])}">'
        f'<span class="archive-mark">OBRA</span><span class="archive-main">'
        f'<strong>{escape(o["nombre"])}</strong><small>{escape(_anio_obra_cerrada(o["nombre"]))} · expediente histórico</small></span>'
        f'<span class="archive-date">{fmt_date(o["ultima_ts"])}</span><span class="archive-go" aria-hidden="true">&#8594;</span></a>'
        for o in obras_cerradas
    )
    script = (
        "const s=document.getElementById('s'),y=document.getElementById('yearFilter'),"
        "rows=[...document.querySelectorAll('.archive-row')],empty=document.getElementById('empty'),"
        "count=document.getElementById('resultCount');"
        "function filtrar(){const q=s.value.trim().toLowerCase(),year=y.value;let n=0;"
        "rows.forEach(r=>{const ok=(!q||(r.dataset.search||'').includes(q))&&(!year||r.dataset.year===year);"
        "r.hidden=!ok;if(ok)n++;});count.textContent=n+(n===1?' obra visible':' obras visibles');"
        "empty.style.display=n?'none':'block';}s.addEventListener('input',filtrar);y.addEventListener('change',filtrar);"
    )
    return (
        f'<a class="breadcrumb" href="{portal_href}">&larr; Centro de mando</a>'
        f'<div class="intro"><div><h1>Archivo histórico</h1>'
        f'<p class="sub">Consulta ordenada de obras cerradas y documentación anterior de Sagarde.</p></div></div>'
        f'<section class="metric-grid">{stats}</section>'
        f'<div class="section-head"><div><h2>Obras cerradas</h2></div>'
        f'<span>Ordenadas por actividad reciente</span></div>'
        f'<div class="toolbar"><label class="search-wrap"><input id="s" class="search" type="search" '
        f'placeholder="Buscar obra, localidad o cliente..." aria-label="Buscar en el archivo histórico">'
        f'<span class="search-symbol">&#9906;</span></label>'
        f'<select id="yearFilter" class="filter-select" aria-label="Filtrar por año">'
        f'<option value="">Todos los años</option>{opciones}</select>'
        f'<span id="resultCount" class="result-count" aria-live="polite">{len(obras_cerradas)} obras visibles</span></div>'
        f'<section class="archive-grid" style="margin-top:12px">{rows}</section>'
        f'<div class="empty-panel" id="empty">No hay obras que coincidan con la búsqueda.</div>'
        f'<script>{script}</script>'
    )


def generar_index_archivo_historico(obras_cerradas: list[dict]) -> None:
    output = ROOT / "SAGARDE (OLD)" / "index.html"
    if not output.parent.is_dir():
        return
    nav = [
        ("⌂ Portal", "../index.html"),
        ("Obras abiertas", "../SAGARDE%20OBRAS%20ABIERTAS/index.html"),
        ("Post-ventas", "../POST-VENTAS/index.html"),
        ("Mantenimientos", "../MANTENIMIENTOS/index.html"),
        ("Archivo histórico", "./"),
    ]
    content = _contenido_archivo_historico(
        obras_cerradas, "../index.html", "OBRAS%20CERRADAS/"
    )
    output.write_text(
        _page_html(
            "Archivo histórico", "Obras cerradas y documentación anterior",
            "../POST-VENTAS/logo_sagarde.jpg", nav, content, _ARCHIVO_CSS,
        ),
        encoding="utf-8",
    )
    print(f"  Archivo historico index: {output}")


def generar_index_obras_cerradas(obras_cerradas: list[dict]) -> None:
    """Conserva la URL historica con la misma experiencia que la nueva area."""
    output = ROOT / "SAGARDE (OLD)" / "OBRAS CERRADAS" / "index.html"
    if not output.parent.is_dir():
        return
    nav = [
        ("⌂ Portal", "../../index.html"),
        ("Obras abiertas", "../../SAGARDE%20OBRAS%20ABIERTAS/index.html"),
        ("Post-ventas", "../../POST-VENTAS/index.html"),
        ("Mantenimientos", "../../MANTENIMIENTOS/index.html"),
        ("Archivo histórico", "../index.html"),
    ]
    content = _contenido_archivo_historico(obras_cerradas, "../../index.html", "")
    output.write_text(
        _page_html(
            "Obras cerradas", "Archivo histórico Sagarde",
            "../../POST-VENTAS/logo_sagarde.jpg", nav, content, _ARCHIVO_CSS,
        ),
        encoding="utf-8",
    )
    print(f"  Obras cerradas index: {output}")


def _etiqueta_app_herramienta(app: dict) -> tuple[str, str]:
    nombre_archivo = Path(app["path"]).name.lower()
    if nombre_archivo == "app_informe_tierras.html":
        return "Informe de tierras", "Mediciones, cálculo y preparación de informes"
    if nombre_archivo == "app_informes.html":
        return "Baterías de condensadores", "Revisiones, perfiles e historial de informes"
    return app["name"].title(), "Aplicación disponible en la biblioteca técnica"


def generar_index_herramientas(catalogo: dict, apps: list[dict]) -> None:
    output = ROOT / "VARIOS" / "index.html"
    if not output.parent.is_dir():
        return
    nav = [
        ("⌂ Portal", "../index.html"),
        ("Obras abiertas", "../SAGARDE%20OBRAS%20ABIERTAS/index.html"),
        ("Post-ventas", "../POST-VENTAS/index.html"),
        ("Mantenimientos", "../MANTENIMIENTOS/index.html"),
        ("Herramientas", "./"),
    ]
    apps_publicas = [
        a for a in apps
        if a.get("area") == "VARIOS"
        and "APPS SAGARDE" not in Path(a.get("path", "")).parts
    ]
    quick_cards = ""
    for app in apps_publicas:
        titulo, descripcion = _etiqueta_app_herramienta(app)
        partes = Path(app["path"]).parts
        rel = Path(*partes[1:]).as_posix() if len(partes) > 1 else partes[0]
        quick_cards += (
            f'<a class="quick-card" href="{quote(rel, safe=_RUTA_SAFE)}" '
            f'data-search="{escape((titulo + " " + app["path"]).lower(), quote=True)}">'
            f'<span class="quick-kicker">Aplicación</span><strong>{escape(titulo)}</strong>'
            f'<small>{escape(descripcion)}</small><span class="quick-go" aria-hidden="true">&#8594;</span></a>'
        )

    categorias = list(catalogo.get("categorias", []))
    if catalogo.get("generales"):
        generales = catalogo["generales"]
        categorias.insert(0, {
            "nombre": "DOCUMENTACIÓN GENERAL",
            "descripcion": "Documentos de referencia disponibles en la raíz de Herramientas",
            "archivos": generales,
            "n_archivos": len(generales),
            "n_documentos": sum(1 for a in generales if a["es_documento"]),
            "ultima_ts": max(a["mtime"] for a in generales),
        })

    bloques = ""
    for categoria in categorias:
        filas = "".join(
            f'<a class="asset-row" href="{escape(a["url"], quote=True)}" target="_blank" rel="noopener" '
            f'data-search="{escape((a["nombre"] + " " + a["ruta"] + " " + a["extension"]).lower(), quote=True)}">'
            f'<span class="file-type">{escape(a["extension"][:5])}</span><span class="asset-main">'
            f'<strong>{escape(a["nombre"])}</strong><small>{escape(a["ruta"])}</small></span>'
            f'<span class="asset-date">{fmt_date(a["mtime"])}</span><span class="asset-go" aria-hidden="true">&#8594;</span></a>'
            for a in categoria["archivos"]
        )
        texto_busqueda = (
            categoria["nombre"] + " " + categoria["descripcion"] + " "
            + " ".join(a["nombre"] for a in categoria["archivos"])
        ).lower()
        bloques += (
            f'<details class="tool-category" data-name="{escape((categoria["nombre"] + " " + categoria["descripcion"]).lower(), quote=True)}" '
            f'data-search="{escape(texto_busqueda, quote=True)}"><summary>'
            f'<span class="folder-mark">SGD</span><span class="category-main">'
            f'<strong>{escape(categoria["nombre"].title())}</strong><small>{escape(categoria["descripcion"])}</small></span>'
            f'<span class="category-count">{categoria["n_archivos"]} archivos · {categoria["n_documentos"]} documentos</span>'
            f'<span class="chevron" aria-hidden="true">&#9656;</span></summary><div class="asset-list">{filas}</div></details>'
        )

    ultima = catalogo.get("ultima_ts")
    stats = (
        f'<div class="metric"><strong>{len(catalogo.get("categorias", []))}</strong><span>categorías técnicas</span></div>'
        f'<div class="metric"><strong>{catalogo.get("n_archivos", 0)}</strong><span>recursos consultables</span></div>'
        f'<div class="metric"><strong>{catalogo.get("n_documentos", 0)}</strong><span>documentos de trabajo</span></div>'
        f'<div class="metric"><strong>{fmt_date(ultima) if ultima else "—"}</strong><span>última actividad pública</span></div>'
    )
    script = (
        "const s=document.getElementById('s'),cats=[...document.querySelectorAll('.tool-category')],"
        "quick=[...document.querySelectorAll('.quick-card')],empty=document.getElementById('empty'),"
        "count=document.getElementById('resultCount');function filtrar(){const q=s.value.trim().toLowerCase();let n=0;"
        "quick.forEach(x=>{const ok=!q||(x.dataset.search||'').includes(q);x.hidden=!ok;if(ok)n++;});"
        "cats.forEach(c=>{const rows=[...c.querySelectorAll('.asset-row')],catOk=!q||(c.dataset.name||'').includes(q);let nr=0;"
        "rows.forEach(r=>{const ok=!q||catOk||(r.dataset.search||'').includes(q);r.hidden=!ok;if(ok)nr++;});"
        "const ok=!q||catOk||nr>0;c.hidden=!ok;if(q&&ok)c.open=true;if(ok)n++;});"
        "count.textContent=n+(n===1?' bloque visible':' bloques visibles');empty.style.display=n?'none':'block';}"
        "s.addEventListener('input',filtrar);"
    )
    quick_section = (
        f'<div class="section-head"><h2>Accesos rápidos</h2><span>{len(apps_publicas)} aplicaciones operativas</span></div>'
        f'<section class="quick-grid">{quick_cards}</section>'
        if quick_cards else ""
    )
    content = (
        f'<a class="breadcrumb" href="../index.html">&larr; Centro de mando</a>'
        f'<div class="intro"><div><h1>Herramientas</h1>'
        f'<p class="sub">Biblioteca técnica, plantillas y utilidades del entorno Sagarde.</p></div></div>'
        f'<section class="metric-grid">{stats}</section>{quick_section}'
        f'<div class="section-head"><h2>Biblioteca técnica</h2><span>Recursos agrupados por especialidad</span></div>'
        f'<div class="toolbar"><label class="search-wrap"><input id="s" class="search" type="search" '
        f'placeholder="Buscar herramienta, documento o categoría..." aria-label="Buscar en Herramientas">'
        f'<span class="search-symbol">&#9906;</span></label>'
        f'<span id="resultCount" class="result-count" aria-live="polite">{len(categorias) + len(apps_publicas)} bloques visibles</span></div>'
        f'<section class="tool-catalog" style="margin-top:12px">{bloques}</section>'
        f'<div class="empty-panel" id="empty">No hay herramientas que coincidan con la búsqueda.</div>'
        f'<script>{script}</script>'
    )
    output.write_text(
        _page_html(
            "Herramientas", "Biblioteca técnica y utilidades Sagarde",
            "../POST-VENTAS/logo_sagarde.jpg", nav, content, _HERRAMIENTAS_CSS,
        ),
        encoding="utf-8",
    )
    print(f"  Herramientas index: {output}")


def generar_index_aplicaciones(apps: list[dict]) -> None:
    output = ROOT / "APLICACIONES" / "index.html"
    output.parent.mkdir(exist_ok=True)
    nav = [
        ("⌂ Portal", "../index.html"),
        ("Obras abiertas", "../SAGARDE%20OBRAS%20ABIERTAS/index.html"),
        ("Post-ventas", "../POST-VENTAS/index.html"),
        ("Mantenimientos", "../MANTENIMIENTOS/index.html"),
        ("Aplicaciones", "./"),
    ]
    by_area: dict[str, list] = {}
    for a in apps:
        by_area.setdefault(a["area"], []).append(a)
    search_js = (
        "const s=document.getElementById('s'),rows=[...document.querySelectorAll('.pv-row')],"
        "empty=document.getElementById('empty');"
        "s.addEventListener('input',()=>{const q=s.value.trim().toLowerCase();let n=0;"
        "rows.forEach(r=>{const ok=!q||(r.dataset.search||'').includes(q);"
        "r.style.display=ok?'':'none';if(ok)n++;});"
        "empty.style.display=n?'none':'block';});"
    )
    sections = ""
    for area_name in sorted(by_area):
        area_apps = sorted(by_area[area_name], key=lambda x: x["name"].lower())
        area_title = AREA_META.get(area_name, (area_name, "", ""))[0]
        rows = "".join(
            f'<a class="pv-row" href="../{a["url"]}" data-search="{escape((a["name"]+" "+a["area"]+" "+a["path"]).lower())}">'
            f'<span class="pv-main"><strong>{escape(a["name"])}</strong>'
            f'<small>{escape(a["path"])}</small></span>'
            f'<span class="pv-badge">{fmt_date(a["mtime"])}</span></a>'
            for a in area_apps
        )
        sections += (
            f'<div class="section-head"><h2>{escape(area_title)}</h2>'
            f'<span>{len(area_apps)} herramienta(s)</span></div>'
            f'<section class="pv-list">{rows}</section>'
        )
    content = (
        f'<div class="intro"><div><h1>Aplicaciones</h1>'
        f'<p class="sub">Todas las herramientas del entorno Sagarde &middot; {len(apps)} accesos detectados</p></div>'
        f'<label class="search-wrap"><input id="s" class="search" type="search" placeholder="Buscar aplicacion...">'
        f'<span class="search-symbol">&#9906;</span></label></div>'
        f'{sections}'
        f'<div class="empty" id="empty" style="display:none;padding:28px;text-align:center;color:var(--muted)">No hay coincidencias.</div>'
        f'<script>{search_js}</script>'
    )
    output.write_text(_page_html("Aplicaciones", "Centro de herramientas Sagarde", "../POST-VENTAS/logo_sagarde.jpg", nav, content), encoding="utf-8")
    print(f"  Aplicaciones index: {output}")


# CSS del portal movil. Copiado literal del ultimo fichero que llego a
# generarse (25/07/2026, commit d71371f) para que la pantalla que Bixente
# conocia siga siendo la misma: esto es una reparacion, no un rediseno.
_MOVIL_CSS = """
:root{--bg:#eef1f4;--ink:#182230;--mut:#647184;--line:#d0d5dd;--brand:#b42318;--nav:#0b1f3a;--nav2:#123a63;--ok:#2e9e5b;--warn:#e07b1a;--bad:#d9483c;--r:9px}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif}
.hd{background:linear-gradient(120deg,var(--nav),var(--nav2));color:#fff;border-bottom:3px solid var(--brand);padding:13px 16px;display:flex;align-items:center;gap:12px}
.logo{height:42px;width:auto;border-radius:6px;box-shadow:0 0 0 2px var(--brand)}
.ht{font-size:17px;font-weight:700}.hs{font-size:11px;color:#c7d3e3;margin-top:2px}
.tab-bar{display:flex;overflow-x:auto;background:var(--nav);border-bottom:3px solid var(--brand);-webkit-overflow-scrolling:touch;scrollbar-width:none}
.tab-bar::-webkit-scrollbar{display:none}
.tp{flex:none;padding:11px 15px;color:rgba(255,255,255,.6);font-size:12px;font-weight:600;border:none;background:none;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-3px;white-space:nowrap;touch-action:manipulation}
.tp.on{color:#fff;border-bottom-color:#f5a524}
.tc{display:none;padding:14px 14px 28px;max-width:860px;margin:0 auto}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}
.kpi{background:#fff;border-radius:var(--r);padding:12px 8px;text-align:center;border:1px solid var(--line)}
.kpi strong{display:block;font-size:22px;font-weight:800}.kpi span{font-size:10px;color:var(--mut);display:block;margin-top:2px;line-height:1.2}
.al{border-radius:var(--r);padding:10px 13px;font-size:12px;font-weight:600;margin-bottom:8px;border:1px solid transparent;line-height:1.4}
.al.bad{background:#fdecea;border-color:#f3b9b2;color:#7a231c}.al.warn{background:#fdf1e0;border-color:#f0cf9a;color:#7a4b0a}.al.ok{background:#e8f6ee;border-color:#b9e3c8;color:#155c34}
.card{background:#fff;border:1px solid var(--line);border-top:3px solid var(--brand);border-radius:var(--r);padding:14px;margin-bottom:10px;color:inherit}
.cn{font-size:14px;font-weight:700;margin-bottom:6px;line-height:1.3}
.pct{font-size:28px;font-weight:800;margin-bottom:4px}.pct.ok{color:var(--ok)}.pct.warn{color:var(--warn)}.pct.bad{color:var(--bad)}
.meta{font-size:11px;color:var(--mut);line-height:1.5}.alert-tag{margin-top:7px;font-size:11px;color:var(--bad);font-weight:700}
.row{display:flex;justify-content:space-between;align-items:center;gap:10px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 13px;margin-bottom:6px;font-size:13px;text-decoration:none;color:inherit}
a.row:active,a.card:active{background:#f2f4f7}
.rn{font-weight:600;line-height:1.3}.muted{font-size:11px;color:var(--mut);white-space:nowrap;flex-shrink:0}
.sh{font-size:14px;font-weight:700;margin:0 0 10px}
.search{width:100%;height:42px;border:1px solid #98a2b3;border-radius:6px;padding:0 12px;font-size:15px;margin-bottom:10px;background:#fff}
.empty{color:var(--mut);font-size:13px;padding:16px 0;text-align:center}
.ft{font-size:10px;color:var(--mut);text-align:center;padding:16px;border-top:1px solid var(--line)}
"""


def generar_portal_movil(ro: dict | None, rp: dict | None,
                          mant: list[dict], obras_cerradas: list[dict]) -> None:
    # Norma _SISTEMA (07/08/2026): el portal movil es una vista generada,
    # no un documento que Bixente abra desde la raiz.
    output = ROOT / "_SISTEMA" / "PORTAL SAGARDE.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    generated = datetime.now().strftime("%d/%m/%Y %H:%M")

    tot_ro = (ro or {}).get("totales", {})
    tot_rp = (rp or {}).get("totales", {})
    avance = tot_ro.get("avance_medio_ponderado")
    n_obras = tot_ro.get("n_obras") if ro else contar_obras_abiertas_carpetas()

    kpis = [
        ("Obras abiertas", n_obras),
        ("Seguimiento IA", tot_ro.get("n_con_panel", 0)),
        ("Avance medio", f"{avance:.0f}%" if avance is not None else "—"),
        ("Bloqueos", tot_ro.get("bloqueos_totales", 0)),
        ("Post-ventas", tot_rp.get("n_contratos", 0)),
        ("Mantenimientos", len(mant)),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><strong>{v}</strong><span>{escape(k)}</span></div>'
        for k, v in kpis
    )

    alertas_raw = []
    if ro:
        tot = tot_ro
        obras = ro.get("obras", [])
        if tot.get("bloqueos_totales"):
            peores = sorted((o for o in obras if o.get("con_panel") and o.get("n_bloqueos")),
                            key=lambda o: -o["n_bloqueos"])[:3]
            nombres = ", ".join(f"{o['nombre']} ({o['n_bloqueos']})" for o in peores)
            alertas_raw.append(("bad", f"{tot['bloqueos_totales']} bloqueo(s) detectado(s) — revisar: {nombres}"))
        sin_cambios = [o["nombre"] for o in obras if o.get("con_panel") and o.get("sin_cambios")]
        if sin_cambios:
            alertas_raw.append(("warn", f"{len(sin_cambios)} obra(s) sin cambios respecto a la ultima revision: {', '.join(sin_cambios)}"))
    alertas_html = "".join(f'<div class="al {t}">{txt}</div>' for t, txt in alertas_raw) \
        if alertas_raw else '<div class="al ok">Sin bloqueos activos en las obras con seguimiento IA.</div>'

    # El fichero vive en _SISTEMA/, un nivel por debajo de la raiz, y todos
    # los href de los resumenes son relativos a la raiz.
    p = "../"

    # --- Obras con seguimiento IA -------------------------------------
    tarjetas = []
    for o in sorted((x for x in (ro or {}).get("obras", []) if x.get("con_panel")),
                    key=lambda x: -(x.get("pct_ponderado") or 0)):
        pct = o.get("pct_ponderado")
        clase = "bad" if pct is None or pct < 40 else ("warn" if pct < 75 else "ok")
        meta = []
        if o.get("ultima_revision"):
            meta.append(f"Rev: {escape(str(o['ultima_revision']))}")
        if o.get("n_rev"):
            meta.append(f"{o['n_rev']} revisiones")
        if o.get("n_docs"):
            meta.append(f"{o['n_docs']} docs")
        aviso = (f'<div class="alert-tag">{o["n_bloqueos"]} bloqueo(s)</div>'
                 if o.get("n_bloqueos") else "")
        cuerpo = (f'<div class="cn">{escape(o["nombre"])}</div>'
                  f'<div class="pct {clase}">{pct:.0f}%</div>'
                  f'<div class="meta">{" &middot; ".join(meta)}</div>{aviso}'
                  if pct is not None else
                  f'<div class="cn">{escape(o["nombre"])}</div>'
                  f'<div class="pct">—</div>'
                  f'<div class="meta">Sin revisiones</div>{aviso}')
        if o.get("href"):
            tarjetas.append(f'<a class="card" style="display:block;'
                            f'text-decoration:none" href="{p}{o["href"]}">'
                            f'{cuerpo}</a>')
        else:
            tarjetas.append(f'<div class="card">{cuerpo}</div>')
    obras_html = ("".join(tarjetas) or
                  '<p class="empty">Ninguna obra con seguimiento IA todavia.</p>')

    # --- Post-ventas ---------------------------------------------------
    filas_pv = []
    for c in (rp or {}).get("contratos", []):
        ts = c.get("ultima_incidencia_ts") or c.get("ultimo_archivo_ts")
        cuando = fmt_date(ts) if ts else "—"
        filas_pv.append(
            f'<a class="row" href="{p}{c["href"]}">'
            f'<span class="rn">{escape(c["nombre"])}</span>'
            f'<span class="muted">{cuando}</span></a>')
    pv_html = (f'<p class="sh">Post-ventas &middot; {tot_rp.get("n_contratos", 0)}'
               f' contratos</p>' + ("".join(filas_pv) or
               '<p class="empty">Sin contratos de post-venta.</p>'))

    # --- Mantenimientos ------------------------------------------------
    filas_mant = "".join(
        f'<a class="row" href="{p}{m["url"]}">'
        f'<span class="rn">{escape(m["nombre"])}</span>'
        f'<span class="muted">{fmt_date(m["ultima_ts"])}</span></a>'
        for m in mant)
    mant_html = (f'<p class="sh">{len(mant)} contrato(s) de mantenimiento</p>'
                 + (filas_mant or '<p class="empty">Sin contratos.</p>'))

    # --- Obras cerradas (con buscador) ---------------------------------
    filas_cerradas = "".join(
        f'<a class="row" data-s="{escape(c["nombre"].lower(), quote=True)}" '
        f'href="{p}{c["url"]}">'
        f'<span class="rn">{escape(c["nombre"])}</span>'
        f'<span class="muted">{fmt_date(c["ultima_ts"])}</span></a>'
        for c in obras_cerradas)
    cerradas_html = (
        '<input id="si" class="search" type="search" '
        'placeholder="Buscar obra cerrada...">'
        f'<p class="sh">{len(obras_cerradas)} obras cerradas</p>'
        + (filas_cerradas or '<p class="empty">Sin obras cerradas.</p>'))

    n_ia = tot_ro.get("n_con_panel", 0)
    html = (
        '<!doctype html><html lang="es"><head>\n'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<title>Portal Sagarde</title>\n'
        f'<style>{_MOVIL_CSS}</style></head><body>\n'
        '<header class="hd">\n'
        f'  <img class="logo" src="{p}POST-VENTAS/logo_sagarde.jpg" '
        'alt="Sagarde" onerror="this.style.display=\'none\'">\n'
        '  <div><div class="ht">Portal Sagarde</div>'
        f'<div class="hs">Centro de mando &middot; {generated}</div></div>\n'
        '</header>\n'
        '<nav class="tab-bar">\n'
        '  <button class="tp" onclick="tab(0)">Inicio</button>\n'
        f'  <button class="tp" onclick="tab(1)">Obras ({n_ia} IA)</button>\n'
        f'  <button class="tp" onclick="tab(2)">Post-ventas '
        f'({tot_rp.get("n_contratos", 0)})</button>\n'
        f'  <button class="tp" onclick="tab(3)">Mantenimientos '
        f'({len(mant)})</button>\n'
        f'  <button class="tp" onclick="tab(4)">Cerradas '
        f'({len(obras_cerradas)})</button>\n'
        '</nav>\n'
        f'<div class="tc" id="tab0"><div class="kpis">{kpi_html}</div>'
        f'{alertas_html}</div>\n'
        f'<div class="tc" id="tab1">{obras_html}</div>\n'
        f'<div class="tc" id="tab2">{pv_html}</div>\n'
        f'<div class="tc" id="tab3">{mant_html}</div>\n'
        f'<div class="tc" id="tab4">{cerradas_html}</div>\n'
        f'<p class="ft">Generado {generated} &middot; '
        'Actualizar_Sagarde.bat para refrescar</p>\n'
        '<script>\n'
        "function tab(n){document.querySelectorAll('.tp').forEach("
        "function(b,i){b.classList.toggle('on',i===n)});"
        "document.querySelectorAll('.tc').forEach(function(c,i){"
        "c.style.display=i===n?'block':'none';});}\n"
        'tab(0);\n'
        "var si=document.getElementById('si');\n"
        "if(si)si.addEventListener('input',function(){"
        "var q=si.value.trim().toLowerCase();"
        "document.querySelectorAll('#tab4 .row').forEach(function(r){"
        "r.style.display=(!q||(r.dataset.s||'').includes(q))?'':'none';});});\n"
        '</script>\n'
        '</body></html>\n'
    )
    output.write_text(html, encoding="utf-8")
    print(f"  Portal movil: {output}")


def _render_sparkline_svg(historico: list[float] | None, width: int = 70, height: int = 22) -> str:
    if not historico or len(historico) < 2:
        return ""
    min_v = min(historico)
    max_v = max(historico)
    rng = (max_v - min_v) if max_v > min_v else 1.0
    
    n = len(historico)
    pts = []
    for i, val in enumerate(historico):
        x = (i / (n - 1)) * (width - 8) + 4
        y = height - 4 - ((val - min_v) / rng) * (height - 8)
        pts.append(f"{x:.1f},{y:.1f}")
    
    polyline_pts = " ".join(pts)
    is_up = historico[-1] >= historico[0]
    color = "#2e9e5b" if is_up else "#e07b1a"
    
    end_x, end_y = pts[-1].split(",")
    return (
        f'<svg width="{width}" height="{height}" style="vertical-align:middle;margin-left:6px">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" points="{polyline_pts}"/>'
        f'<circle cx="{end_x}" cy="{end_y}" r="3" fill="{color}"/>'
        f'</svg>'
    )


def _render_variacion_badge(var_pct: float | None) -> str:
    if var_pct is None:
        return ""
    if var_pct > 0:
        return f'<span style="display:inline-block;padding:2px 7px;border-radius:12px;font-size:11px;font-weight:700;background:#e8f6ee;color:#2e9e5b;margin-left:6px">📈 +{var_pct:.1f}%</span>'
    elif var_pct < 0:
        return f'<span style="display:inline-block;padding:2px 7px;border-radius:12px;font-size:11px;font-weight:700;background:#fff4e5;color:#e07b1a;margin-left:6px">📉 {var_pct:.1f}%</span>'
    else:
        return f'<span style="display:inline-block;padding:2px 7px;border-radius:12px;font-size:11px;font-weight:700;background:#f1f5f9;color:#647184;margin-left:6px">📊 0.0%</span>'


    obras_ia = sorted(
        [o for o in (ro or {}).get("obras", []) if o.get("con_panel")],
        key=lambda o: (-(o.get("n_bloqueos") or 0), o.get("pct_ponderado", 100))
    )
    obras_ia_parts = []
    for o in obras_ia:
        pct_val = o.get("pct_ponderado", 0)
        spark_svg = _render_sparkline_svg(o.get("historico_pct"))
        var_badge = _render_variacion_badge(o.get("variacion_pct"))
        bloqueo = f'<div class="alert-tag">{o["n_bloqueos"]} bloqueo(s)</div>' if o.get("n_bloqueos") else ""
        obras_ia_parts.append(
            f'<div class="card">'
            f'<div class="cn">{escape(o["nombre"])}</div>'
            f'<div style="display:flex;align-items:center;gap:6px">'
            f'<div class="pct {clase_pct(pct_val)}">{pct_val:.0f}%</div>'
            f'{var_badge}{spark_svg}'
            f'</div>'
            f'<div class="meta">Rev: {escape(str(o.get("ultima_revision", "—")))} &middot; {o.get("n_rev", 0)} revisiones &middot; {o.get("n_docs", 0)} docs</div>'
            f'{bloqueo}</div>'
        )
    obras_ia_html = "".join(obras_ia_parts) or "<p class='empty'>Sin datos de obras con seguimiento IA.</p>"

    obras_sin_panel = [o for o in (ro or {}).get("obras", []) if not o.get("con_panel")]
    sin_panel_html = "".join(
        f'<div class="row"><span>{escape(o["nombre"])}</span><span class="muted">Sin panel IA</span></div>'
        for o in obras_sin_panel
    ) if obras_sin_panel else ""
    sin_panel_section = (
        f'<p class="sh" style="margin-top:18px">Sin panel IA ({len(obras_sin_panel)})</p>{sin_panel_html}'
        if sin_panel_html else ""
    )

    contratos_rp = sorted((rp or {}).get("contratos", []), key=lambda c: -c["ultimo_archivo_ts"])
    pv_html = "".join(
        f'<div class="row"><span class="rn">{escape(c["nombre"])}</span>'
        f'<span class="muted">{fmt_date(c["ultimo_archivo_ts"])}</span></div>'
        for c in contratos_rp
    ) or "<p class='empty'>Sin datos de post-ventas.</p>"

    mant_html = "".join(
        f'<a class="row" href="{m["url"]}"><span class="rn">{escape(m["nombre"])}</span>'
        f'<span class="muted">{fmt_date(m["ultima_ts"])}</span></a>'
        for m in mant
    ) or "<p class='empty'>Sin contratos de mantenimiento.</p>"

    cerradas_html = "".join(
        f'<div class="row" data-s="{escape(o["nombre"].lower())}">'
        f'<span>{escape(o["nombre"])}</span>'
        f'<span class="muted">{fmt_date(o["ultima_ts"])}</span></div>'
        for o in obras_cerradas
    )

    html = f'''<!doctype html><html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portal Sagarde</title>
<style>
:root{{--bg:#eef1f4;--ink:#182230;--mut:#647184;--line:#d0d5dd;--brand:#b42318;--nav:#0b1f3a;--nav2:#123a63;--ok:#2e9e5b;--warn:#e07b1a;--bad:#d9483c;--r:9px}}
*{{box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif}}
.hd{{background:linear-gradient(120deg,var(--nav),var(--nav2));color:#fff;border-bottom:3px solid var(--brand);padding:13px 16px;display:flex;align-items:center;gap:12px}}
.logo{{height:42px;width:auto;border-radius:6px;box-shadow:0 0 0 2px var(--brand)}}
.ht{{font-size:17px;font-weight:700}}.hs{{font-size:11px;color:#c7d3e3;margin-top:2px}}
.tab-bar{{display:flex;overflow-x:auto;background:var(--nav);border-bottom:3px solid var(--brand);-webkit-overflow-scrolling:touch;scrollbar-width:none}}
.tab-bar::-webkit-scrollbar{{display:none}}
.tp{{flex:none;padding:11px 15px;color:rgba(255,255,255,.6);font-size:12px;font-weight:600;border:none;background:none;cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-3px;white-space:nowrap;touch-action:manipulation}}
.tp.on{{color:#fff;border-bottom-color:#f5a524}}
.tc{{display:none;padding:14px 14px 28px;max-width:860px;margin:0 auto}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}}
.kpi{{background:#fff;border-radius:var(--r);padding:12px 8px;text-align:center;border:1px solid var(--line)}}
.kpi strong{{display:block;font-size:22px;font-weight:800}}.kpi span{{font-size:10px;color:var(--mut);display:block;margin-top:2px;line-height:1.2}}
.al{{border-radius:var(--r);padding:10px 13px;font-size:12px;font-weight:600;margin-bottom:8px;border:1px solid transparent;line-height:1.4}}
.al.bad{{background:#fdecea;border-color:#f3b9b2;color:#7a231c}}.al.warn{{background:#fdf1e0;border-color:#f0cf9a;color:#7a4b0a}}.al.ok{{background:#e8f6ee;border-color:#b9e3c8;color:#155c34}}
.card{{background:#fff;border:1px solid var(--line);border-top:3px solid var(--brand);border-radius:var(--r);padding:14px;margin-bottom:10px}}
.cn{{font-size:14px;font-weight:700;margin-bottom:6px;line-height:1.3}}
.pct{{font-size:28px;font-weight:800;margin-bottom:4px}}.pct.ok{{color:var(--ok)}}.pct.warn{{color:var(--warn)}}.pct.bad{{color:var(--bad)}}
.meta{{font-size:11px;color:var(--mut);line-height:1.5}}.alert-tag{{margin-top:7px;font-size:11px;color:var(--bad);font-weight:700}}
.row{{display:flex;justify-content:space-between;align-items:center;gap:10px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 13px;margin-bottom:6px;font-size:13px;text-decoration:none;color:inherit}}
a.row:active{{background:#f2f4f7}}
.rn{{font-weight:600;line-height:1.3}}.muted{{font-size:11px;color:var(--mut);white-space:nowrap;flex-shrink:0}}
.sh{{font-size:14px;font-weight:700;margin:0 0 10px}}
.search{{width:100%;height:42px;border:1px solid #98a2b3;border-radius:6px;padding:0 12px;font-size:15px;margin-bottom:10px;background:#fff}}
.empty{{color:var(--mut);font-size:13px;padding:16px 0;text-align:center}}
.ft{{font-size:10px;color:var(--mut);text-align:center;padding:16px;border-top:1px solid var(--line)}}
</style></head><body>
<header class="hd">
  <img class="logo" src="POST-VENTAS/logo_sagarde.jpg" alt="Sagarde" onerror="this.style.display=\'none\'">
  <div><div class="ht">Portal Sagarde</div><div class="hs">Centro de mando &middot; {generated}</div></div>
</header>
<nav class="tab-bar">
  <button class="tp" onclick="tab(0)">Inicio</button>
  <button class="tp" onclick="tab(1)">Obras ({len(obras_ia)} IA)</button>
  <button class="tp" onclick="tab(2)">Post-ventas ({len(contratos_rp)})</button>
  <button class="tp" onclick="tab(3)">Mantenimientos ({len(mant)})</button>
  <button class="tp" onclick="tab(4)">Cerradas ({len(obras_cerradas)})</button>
</nav>
<div class="tc" id="tab0"><div class="kpis">{kpi_html}</div>{alertas_html}</div>
<div class="tc" id="tab1">{obras_ia_html}{sin_panel_section}</div>
<div class="tc" id="tab2"><p class="sh">Post-ventas &middot; {len(contratos_rp)} contratos</p>{pv_html}</div>
<div class="tc" id="tab3"><p class="sh">Mantenimientos &middot; {len(mant)} contratos</p>{mant_html}</div>
<div class="tc" id="tab4">
  <input id="si" class="search" type="search" placeholder="Buscar obra cerrada...">
  <p class="sh">{len(obras_cerradas)} obras cerradas</p>
  {cerradas_html}
</div>
<div class="ft">Actualizado {generated} &middot; Ejecuta Actualizar_Sagarde.bat para refrescar</div>
<script>
function tab(n){{document.querySelectorAll('.tp').forEach(function(b,i){{b.classList.toggle('on',i===n)}});document.querySelectorAll('.tc').forEach(function(c,i){{c.style.display=i===n?'block':'none';}});}}
tab(0);
var si=document.getElementById('si');
if(si)si.addEventListener('input',function(){{var q=si.value.trim().toLowerCase();document.querySelectorAll('#tab4 .row').forEach(function(r){{r.style.display=(!q||(r.dataset.s||'').includes(q))?'':'none';}});}});
</script>
</body></html>'''

    output.write_text(html, encoding="utf-8")
    print(f"  Portal movil: {output}")


def construir_alertas(ro: dict | None = None, rp: dict | None = None, mant: list[dict] | None = None) -> list[tuple[str, str]]:
    """Traduce el resumen de Obras Abiertas, Post-Ventas y Mantenimientos en avisos accionables."""
    alertas = []

    # 1. OBRAS ABIERTAS
    if ro and ro.get("obras"):
        tot = ro.get("totales", {})
        obras = ro["obras"]

        if tot.get("bloqueos_totales"):
            peores = sorted((o for o in obras if o.get("con_panel") and o.get("n_bloqueos")),
                             key=lambda o: -o["n_bloqueos"])[:3]
            nombres = ", ".join(
                f'<a href="{escape(o["href"])}" style="color:inherit;text-decoration:underline"><b>{escape(o["nombre"])}</b> ({o["n_bloqueos"]})</a>'
                if o.get("href") else f"<b>{escape(o['nombre'])}</b> ({o['n_bloqueos']})"
                for o in peores
            )
            alertas.append(("bad", f"{tot['bloqueos_totales']} bloqueo(s) detectado(s) en obras con seguimiento IA — revisar primero: {nombres}"))

        sin_cambios_obras = [o for o in obras if o.get("con_panel") and o.get("sin_cambios")]
        if sin_cambios_obras:
            nombres_sc = ", ".join(
                f'<a href="{escape(o["href"])}" style="color:inherit;text-decoration:underline"><b>{escape(o["nombre"])}</b></a>'
                if o.get("href") else f"<b>{escape(o['nombre'])}</b>"
                for o in sin_cambios_obras
            )
            alertas.append(("warn", f"{len(sin_cambios_obras)} obra(s) sin cambios respecto a su revision anterior — comprobar si la hoja de campo esta al dia: {nombres_sc}"))

        inactivas = [
            o for o in obras
            if o.get("con_panel")
            and es_aviso_por_antiguedad(
                dias_desde(o.get("ultimo_archivo_ts")),
                DIAS_OBRA_INACTIVA,
            )
        ]
        if inactivas:
            nombres_inact = ", ".join(
                f'<a href="{escape(o["href"])}" style="color:inherit;text-decoration:underline"><b>{escape(o["nombre"])}</b> ({dias_desde(o.get("ultimo_archivo_ts"))} dias)</a>'
                if o.get("href") else f"<b>{escape(o['nombre'])}</b> ({dias_desde(o.get('ultimo_archivo_ts'))} dias)"
                for o in inactivas[:3]
            )
            alertas.append(("warn", f"{len(inactivas)} obra(s) con seguimiento IA sin archivos nuevos entre {DIAS_OBRA_INACTIVA + 1} y 399 dias: {nombres_inact}"))

    # 2. MANTENIMIENTOS
    if mant:
        mant_inactivos = [
            m for m in mant
            if es_aviso_por_antiguedad(
                dias_desde(m.get("ultima_ts")),
                DIAS_MANTENIMIENTO_INACTIVO,
            )
        ]
        if mant_inactivos:
            nombres_m = ", ".join(
                f'<a href="MANTENIMIENTOS/{escape(m["sub_url"])}" style="color:inherit;text-decoration:underline"><b>{escape(m["nombre"])}</b> ({dias_desde(m["ultima_ts"])} dias)</a>'
                for m in mant_inactivos[:3]
            )
            alertas.append(("warn", f"{len(mant_inactivos)} contrato(s) de mantenimiento sin revision ni archivos nuevos entre {DIAS_MANTENIMIENTO_INACTIVO + 1} y 399 dias: {nombres_m}"))

    # 3. POST-VENTAS
    if rp and rp.get("contratos"):
        pv_recientes = [c for c in rp["contratos"] if c.get("reciente")]
        if pv_recientes:
            nombres_pv = ", ".join(
                f'<a href="{escape(c["href"])}" style="color:inherit;text-decoration:underline"><b>{escape(c["nombre"])}</b> ({dias_desde(c.get("ultimo_archivo_ts"))}d)</a>'
                if c.get("href") else f"<b>{escape(c['nombre'])}</b>"
                for c in pv_recientes[:4]
            )
            alertas.append(("info", f"{len(pv_recientes)} contrato(s) de post-venta con incidencias activas recientemente: {nombres_pv}"))

    # 4. AUDITORÍA DE DATOS Y PRE-PUBLICACIÓN
    diag_path = ROOT / "_SISTEMA" / "MOTOR" / "auditoria_diagnostico.json"
    if diag_path.is_file():
        try:
            with open(diag_path, encoding="utf-8") as f:
                diag = json.load(f)
            warnings_audit = [
                i for i in diag.get("issues", [])
                if i.get("nivel") == "warning"
                and not aviso_caducado(i.get("dias_antiguedad"))
            ]
            if warnings_audit:
                detalles = ", ".join(f"<b>{escape(w['obra'])}</b> ({escape(w['codigo'])})" for w in warnings_audit[:3])
                alertas.append(("warn", f"⚠️ Salud de Datos: {len(warnings_audit)} aviso(s) de formato en archivos de inspección: {detalles}"))
        except Exception:
            pass

    return alertas


def discover_apps() -> list[dict]:
    # Solo se muestran apps reales, generadores e informes.
    # Se excluyen: índices de navegación (index.html), paneles de obra,
    # áreas operativas (mantenimientos, post-ventas, archivo), años anteriores de registros,
    # y utilidades de otras áreas (tierras, condensadores, manuales).
    EXCLUIR_AREAS = {"MANTENIMIENTOS", "POST-VENTAS", "SAGARDE (OLD)"}
    EXCLUIR_AÑOS = {"2019", "2020", "2021", "2022", "2023", "2024", "2025"}
    apps = []
    candidatos = sorted(set(ROOT.rglob("*.html")) | set(ROOT.rglob("*.htm")))
    for path in candidatos:
        if path == OUTPUT or not visible(path):
            continue
        low = path.name.lower()
        if "backup" in low or "copia" in low or "antes_" in low:
            continue
        if low in {"index.html", "panel.html"}:
            continue
        if not any(h in low for h in APP_HINTS):
            continue
        rel = path.relative_to(ROOT)
        if es_ruta_privada_herramientas(path):
            continue
        if rel.parts[0] == "APLICACIONES":
            continue
        area = rel.parts[0]
        if area in EXCLUIR_AREAS:
            continue
        # De obras abiertas solo se incluye el generador de revisiones
        if area == "SAGARDE OBRAS ABIERTAS" and "generador" not in low:
            continue
        if any(año in rel.parts for año in EXCLUIR_AÑOS):
            continue
        label = " ".join(path.stem.replace("_", " ").split())
        apps.append({"name": label, "area": area, "path": rel.as_posix(), "url": url(path), "mtime": path.stat().st_mtime})
    return sorted(apps, key=lambda x: (-x["mtime"], x["name"].lower()))


def build_tree() -> list[dict]:
    nodes = []
    for area in sorted((p for p in ROOT.iterdir() if es_carpeta_visible(p)), key=lambda p: p.name):
        children = []
        for child in sorted((p for p in area.iterdir() if es_carpeta_visible(p)), key=lambda p: p.name):
            grandchildren = [
                {"name": p.name, "url": url(p) + "/"}
                for p in sorted((x for x in child.iterdir() if es_carpeta_visible(x)), key=lambda p: p.name)
            ]
            children.append({"name": child.name, "url": url(child) + "/", "children": grandchildren})
        nodes.append({"name": area.name, "url": url(area) + "/", "children": children})
    return nodes


def fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")


def area_highlight(a: dict, ro: dict | None, rp: dict | None, mant: list[dict], planilla: dict | None, cerradas: int, n_apps: int = 0) -> str:
    """Linea de metrica real por area, cuando hay datos de un subsistema.
    Si no hay datos frescos, devuelve cadena vacia y el area cae a las 3
    cifras genericas de carpetas/archivos/documentos (siempre calculadas)."""
    name = a["name"]
    if name == "SAGARDE OBRAS ABIERTAS" and ro:
        tot = ro.get("totales", {})
        avance = tot.get("avance_medio_ponderado")
        avance_txt = f"{avance:.0f}% avance medio" if avance is not None else "sin datos de avance"
        cls = clase_pct(avance) if avance is not None else "pending"
        bloqueos = tot.get("bloqueos_totales", 0)
        alerta = f' · <b class="bad">{bloqueos} bloqueo(s)</b>' if bloqueos else ""
        return f'<div class="area-highlight"><span class="pct-chip {cls}">{escape(avance_txt)}</span>{alerta}</div>'
    if name == "POST-VENTAS" and rp:
        tot = rp.get("totales", {})
        return f'<div class="area-highlight"><span class="pct-chip ok">{tot.get("n_contratos", 0)} contratos</span> · {tot.get("n_recientes", 0)} con actividad reciente (&lt;{DIAS_POSTVENTA_RECIENTE} dias)</div>'
    if name == "MANTENIMIENTOS" and mant:
        return f'<div class="area-highlight"><span class="pct-chip ok">{len(mant)} contrato(s) activo(s)</span></div>'
    if name == "APLICACIONES" and n_apps:
        return f'<div class="area-highlight"><span class="pct-chip ok">{n_apps} herramientas accesibles</span></div>'
    if name == "VARIOS" and planilla and planilla.get("ultima_ts"):
        d = dias_desde(planilla["ultima_ts"])
        if d is not None and d > 180:
            anio = datetime.fromtimestamp(planilla["ultima_ts"]).year
            return f'<div class="area-highlight"><span class="pct-chip warn">Planilla sin actualizar desde {anio}</span></div>'
    if name == "SAGARDE (OLD)" and cerradas:
        return f'<div class="area-highlight"><span class="pct-chip">{cerradas} obras cerradas archivadas</span></div>'
    return ""


def build_html(areas: list[dict], apps: list[dict], ro: dict | None, rp: dict | None,
                mant: list[dict], planilla: dict | None, obras_cerradas: list[dict]) -> str:
    area_cards = "".join(f'''<article class="area" style="--accent:{a['color']}" data-search="{escape((a['title']+' '+a['description']+' '+a['name']).lower())}">
      <div class="area-head"><span class="area-mark"></span><span class="area-date">{fmt_date(a['latest'])}</span></div>
      <h3>{escape(a['title'])}</h3><p>{escape(a['description'])}</p>
      {area_highlight(a, ro, rp, mant, planilla, len(obras_cerradas), len(apps))}
      <div class="area-stats"><span>{a['folders']} carpetas</span><span>{a['files']} archivos</span><span>{a['docs']} documentos</span></div>
      <a class="primary" href="{a['url']}">Abrir area <span aria-hidden="true">&#8594;</span></a>
    </article>''' for a in areas)

    app_rows = "".join(f'''<a class="app-row" href="{a['url']}" data-search="{escape((a['name']+' '+a['area']+' '+a['path']).lower())}">
      <span class="app-icon">&#9654;</span><span class="app-main"><strong>{escape(a['name'])}</strong><small>{escape(a['path'])}</small></span>
      <span class="app-area">{escape(AREA_META.get(a['area'], (a['area'], '', ''))[0])}</span><span class="go">&#8594;</span>
    </a>''' for a in apps)

    # --- KPIs de empresa (solo con datos reales de los subsistemas) ---
    tot_ro = (ro or {}).get("totales", {})
    tot_rp = (rp or {}).get("totales", {})
    avance = tot_ro.get("avance_medio_ponderado")
    n_obras = tot_ro.get("n_obras") if ro else contar_obras_abiertas_carpetas()
    kpis = [
        ("Obras abiertas", n_obras, ""),
        ("Con seguimiento IA", tot_ro.get("n_con_panel", 0), ""),
        ("Avance medio", f"{avance:.0f}%" if avance is not None else "—", clase_pct(avance) if avance is not None else ""),
        ("Bloqueos activos", tot_ro.get("bloqueos_totales", 0), "bad" if tot_ro.get("bloqueos_totales") else "ok"),
        ("Post-ventas activos", tot_rp.get("n_contratos", 0), ""),
        ("Mantenimientos", len(mant), ""),
    ]
    kpi_html = "".join(f'<div class="kpi"><strong class="{cls}">{v}</strong><span>{escape(k)}</span></div>' for k, v, cls in kpis)

    # --- Alertas ---
    alertas = construir_alertas(ro, rp, mant)
    if alertas:
        alertas_html = "".join(f'<div class="alerta {tipo}">{txt}</div>' for tipo, txt in alertas)
    else:
        alertas_html = '<div class="alerta ok">Sin bloqueos ni avisos activos en las obras con seguimiento IA.</div>' if ro else \
            '<div class="alerta info">Todavia no se ha generado el resumen de Obras Abiertas — ejecuta el actualizador para verlo aqui.</div>'

    # --- Grid de obras con seguimiento IA, ordenadas por riesgo ---
    obras_ia = [o for o in (ro or {}).get("obras", []) if o.get("con_panel") and o.get("panel_actualizado")]
    obras_ia.sort(key=lambda o: (-(o.get("n_bloqueos") or 0), o.get("pct_ponderado", 100)))
    obra_cards = "".join(f'''<a class="obra" href="{escape(o['href'], quote=True)}" data-search="{escape(o['nombre'].lower())}">
      <h3>{escape(o['nombre'])}</h3>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
        <div class="pct {clase_pct(o.get('pct_ponderado', 0))}">{o.get('pct_ponderado', 0):.0f}%</div>
        <div style="display:flex;align-items:center">{_render_variacion_badge(o.get('variacion_pct'))}{_render_sparkline_svg(o.get('historico_pct'))}</div>
      </div>
      <div class="row"><span>Ultima revision</span><span>{escape(str(o.get('ultima_revision', '—')))}</span></div>
      <div class="row"><span>Revisiones</span><span>{o.get('n_rev', 0)}</span></div>
      <div class="row"><span>Documentos</span><span>{o.get('n_docs', 0)}</span></div>
      {f'<div class="obra-alerta">{o["n_bloqueos"]} bloqueo(s)' + (' · sin cambios' if o.get('sin_cambios') else '') + '</div>' if o.get('n_bloqueos') or o.get('sin_cambios') else ''}
    </a>''' for o in obras_ia)
    obras_section = "" if not obras_ia else f'''
    <div class="section-head"><h2>Obras con seguimiento IA</h2><span>{len(obras_ia)} obra(s) · ordenadas por riesgo · datos del {escape(ro.get('generado','—'))}</span></div>
    <section class="obras-grid">{obra_cards}</section>'''

    # --- Post-ventas recientes ---
    contratos_rp = sorted((rp or {}).get("contratos", []), key=lambda c: -c["ultimo_archivo_ts"])[:6]
    pv_rows = "".join(f'''<a class="pv-row" href="{escape(c['href'], quote=True)}" data-search="{escape(c['nombre'].lower())}">
      <span class="pv-main"><strong>{escape(c['nombre'])}</strong><small>{c['n_archivos']} archivo(s)</small></span>
      <span class="pv-badge {'ok' if c.get('reciente') else ''}">{fmt_date(c['ultimo_archivo_ts'])}</span>
    </a>''' for c in contratos_rp)
    postventas_section = "" if not contratos_rp else f'''
    <div class="section-head"><h2>Post-ventas — actividad reciente</h2><span>{len(contratos_rp)} de {tot_rp.get('n_contratos', 0)} contratos · datos del {escape((rp or {}).get('generado','—'))}</span></div>
    <section class="pv-list">{pv_rows}</section>'''

    # --- Obras cerradas (colapsadas por defecto) ---
    obras_cerradas_rows = "".join(
        f'<a class="pv-row" href="{o["url"]}" data-search="{escape(o["nombre"].lower())}">'
        f'<span class="pv-main"><strong>{escape(o["nombre"])}</strong></span>'
        f'<span class="pv-badge">{fmt_date(o["ultima_ts"])}</span></a>'
        for o in obras_cerradas
    )
    obras_cerradas_section = (
        f'<details class="cerradas-toggle"><summary>'
        f'<span>Obras cerradas</span>'
        f'<span class="toggle-hint" data-count="{len(obras_cerradas)} obras · por actividad reciente"></span>'
        f'</summary><div class="cerradas-inner pv-list">{obras_cerradas_rows}</div></details>'
    ) if obras_cerradas else ""

    generated = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sagarde | Centro de mando</title><style>
:root{{--bg:#eef1f4;--ink:#182230;--muted:#647184;--line:#d0d5dd;--soft:#f2f4f7;--paper:#fff;--brand:#b42318;--nav:#0b1f3a;--nav2:#123a63;--accent:#f5a524;--ok:#2e9e5b;--warn:#e07b1a;--bad:#d9483c;--radius:9px}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;letter-spacing:0}}a{{color:inherit}}button,input{{font:inherit}}
.top{{background:linear-gradient(120deg,var(--nav),var(--nav2));color:#fff;border-bottom:4px solid var(--brand)}}.top-inner{{max-width:1440px;margin:auto;padding:18px 28px;display:flex;align-items:center;gap:20px}}
.logo{{width:min(290px,22vw);height:auto;object-fit:contain;border-radius:9px;box-shadow:0 0 0 3px var(--brand),0 6px 28px rgba(0,0,0,0.5)}}.identity{{min-width:0}}.identity strong{{font-size:21px;display:block}}.identity span{{font-size:12px;color:#c7d3e3}}
.top-actions{{margin-left:auto;display:flex;gap:8px}}.top-actions a{{text-decoration:none;border:1px solid rgba(255,255,255,.35);color:#fff;padding:9px 12px;border-radius:5px;font-size:13px;font-weight:600}}
.shell{{max-width:1440px;margin:auto;padding:24px 28px 38px}}.intro{{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:18px}}h1{{font-size:28px;margin:0 0 5px}}.intro p{{margin:0;color:var(--muted)}}
.search-wrap{{width:min(470px,100%);position:relative}}.search{{width:100%;height:42px;padding:0 42px 0 14px;border:1px solid #98a2b3;border-radius:6px;background:#fff}}.search-symbol{{position:absolute;right:14px;top:11px;color:#667085}}
.alertas{{display:flex;flex-direction:column;gap:8px;margin-bottom:18px}}.alerta{{border-radius:var(--radius);padding:12px 16px;font-size:13px;font-weight:600;border:1px solid transparent}}
.alerta.bad{{background:#fdecea;border-color:#f3b9b2;color:#7a231c}}.alerta.warn{{background:#fdf1e0;border-color:#f0cf9a;color:#7a4b0a}}.alerta.ok{{background:#e8f6ee;border-color:#b9e3c8;color:#155c34}}.alerta.info{{background:#eaf1fb;border-color:#b9d1f0;color:#0b3a6b}}
.kpis{{display:grid;grid-template-columns:repeat(6,1fr);background:#fff;border:1px solid var(--line);border-radius:var(--radius);margin-bottom:24px}}.kpi{{padding:14px 16px;border-right:1px solid var(--line)}}.kpi:last-child{{border:0}}.kpi strong{{display:block;font-size:22px}}.kpi span{{font-size:11.5px;color:var(--muted)}}.kpi strong.ok{{color:var(--ok)}}.kpi strong.warn{{color:var(--warn)}}.kpi strong.bad{{color:var(--bad)}}
.section-head{{display:flex;align-items:center;justify-content:space-between;margin:22px 0 10px;gap:12px;flex-wrap:wrap}}h2{{font-size:17px;margin:0}}.section-head span{{font-size:12px;color:var(--muted)}}
.obras-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;margin-bottom:8px}}.obra{{background:#fff;border:1px solid var(--line);border-top:4px solid var(--accent);border-radius:var(--radius);padding:16px 18px;text-decoration:none;color:var(--ink);display:block;transition:transform .1s}}.obra:hover{{transform:translateY(-2px);box-shadow:0 4px 14px rgba(0,0,0,.12)}}
.obra h3{{font-size:14px;font-weight:700;margin:0 0 8px;line-height:1.3}}.obra .pct{{font-size:26px;font-weight:800;margin-bottom:2px}}.obra .pct.ok{{color:var(--ok)}}.obra .pct.warn{{color:var(--warn)}}.obra .pct.bad{{color:var(--bad)}}
.obra .row{{display:flex;justify-content:space-between;font-size:11.5px;color:var(--muted);margin-top:6px}}.obra-alerta{{margin-top:10px;font-size:11.5px;color:var(--bad);font-weight:700}}
.obra-actions{{display:flex;gap:6px;margin-top:10px;padding-top:8px;border-top:1px solid var(--soft)}}
.btn-action{{display:inline-flex;align-items:center;padding:4px 8px;border-radius:5px;font-size:10.5px;font-weight:700;text-decoration:none}}
.btn-pdf{{background:#fdecea;color:#b42318;border:1px solid #f3b9b2}}
.btn-pdf:hover{{background:#b42318;color:#fff}}
.btn-web{{background:#f2f4f7;color:#182230;border:1px solid #d0d5dd}}
.btn-web:hover{{background:#0b1f3a;color:#fff}}
.pv-list{{display:grid;gap:6px;margin-bottom:8px}}.pv-row{{display:flex;justify-content:space-between;align-items:center;gap:12px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 14px;text-decoration:none;color:var(--ink)}}.pv-row:hover{{background:#f8fafc}}.pv-main strong{{display:block;font-size:13px}}.pv-main small{{color:var(--muted);font-size:11px}}.pv-badge{{font-size:11px;color:var(--muted);white-space:nowrap}}.pv-badge.ok{{color:var(--ok);font-weight:700}}
.areas{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.area{{background:#fff;border:1px solid var(--line);border-top:3px solid var(--accent);border-radius:var(--radius);padding:17px;display:flex;flex-direction:column;min-height:190px}}.area-head{{display:flex;justify-content:space-between}}.area-mark{{width:9px;height:9px;background:var(--accent);border-radius:50%}}.area-date{{font-size:11px;color:var(--muted)}}.area h3{{font-size:17px;margin:13px 0 5px}}.area p{{font-size:13px;line-height:1.4;color:var(--muted);margin:0 0 10px}}
.area-highlight{{margin-bottom:10px;font-size:12px}}.pct-chip{{display:inline-block;background:var(--soft);border-radius:20px;padding:3px 10px;font-weight:700}}.pct-chip.ok{{background:#e8f6ee;color:var(--ok)}}.pct-chip.warn{{background:#fdf1e0;color:var(--warn)}}.pct-chip.bad{{background:#fdecea;color:var(--bad)}}.pct-chip.pending{{color:var(--muted)}}
.area-stats{{display:flex;gap:10px;flex-wrap:wrap;font-size:11px;color:#475467;margin-top:auto}}.primary{{margin-top:13px;padding-top:12px;border-top:1px solid #eaecf0;text-decoration:none;font-size:13px;font-weight:700;display:flex;justify-content:space-between}}
.workspace{{display:grid;gap:14px}}.panel{{background:#fff;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}}.panel-title{{padding:13px 15px;border-bottom:1px solid var(--line);font-size:13px;font-weight:700;background:#f9fafb}}
.app-list{{max-height:480px;overflow:auto}}.app-row{{display:grid;grid-template-columns:30px minmax(0,1fr) 140px 22px;align-items:center;gap:8px;padding:11px 14px;border-bottom:1px solid #eaecf0;text-decoration:none}}.app-row:hover{{background:#f8fafc}}.app-icon{{width:25px;height:25px;background:#e9f2fc;color:#0b6bcb;border-radius:4px;display:grid;place-items:center;font-size:10px}}.app-main{{min-width:0}}.app-main strong,.app-main small{{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.app-main strong{{font-size:13px}}.app-main small{{font-size:10px;color:var(--muted);margin-top:3px}}.app-area{{font-size:11px;color:var(--muted)}}.go{{color:#667085}}
.empty{{display:none;padding:28px;text-align:center;color:var(--muted)}}.footer{{font-size:11px;color:var(--muted);text-align:right;margin-top:16px}}
.cerradas-toggle{{background:#fff;border:1px solid var(--line);border-radius:var(--radius);margin-bottom:8px}}.cerradas-toggle>summary{{cursor:pointer;padding:13px 16px;font-size:13px;font-weight:700;list-style:none;display:flex;justify-content:space-between;align-items:center;color:var(--ink)}}.cerradas-toggle>summary::-webkit-details-marker{{display:none}}.cerradas-toggle>summary .toggle-hint{{font-size:11px;color:var(--muted);font-weight:400}}.cerradas-toggle>summary .toggle-hint::before{{content:"▸ ver todas"}}.cerradas-toggle[open]>summary .toggle-hint::before{{content:"▴ ocultar"}}.cerradas-inner{{padding:0 12px 12px}}
@media(max-width:1000px){{.kpis{{grid-template-columns:repeat(3,1fr)}}.kpi:nth-child(3){{border-right:0}}.kpi:nth-child(-n+3){{border-bottom:1px solid var(--line)}}}}
@media(max-width:900px){{.areas{{grid-template-columns:repeat(2,1fr)}}.workspace{{grid-template-columns:1fr}}.intro{{align-items:stretch;flex-direction:column}}.search-wrap{{width:100%}}.logo{{width:190px}}}}
@media(max-width:600px){{.top-inner,.shell{{padding-left:14px;padding-right:14px}}.logo{{width:160px}}.top-actions{{display:none}}.areas{{grid-template-columns:1fr}}.kpis{{grid-template-columns:repeat(2,1fr)}}.kpi:nth-child(2){{border-right:0}}.kpi:nth-child(-n+2){{border-bottom:1px solid var(--line)}}.app-row{{grid-template-columns:28px minmax(0,1fr) 20px}}.app-area{{display:none}}h1{{font-size:23px}}}}
</style></head><body>
<header class="top"><div class="top-inner"><video id="intro-vid" class="logo" src="VARIOS/VIDEOSAG.mp4" autoplay muted playsinline></video><img id="logo-img" class="logo" src="POST-VENTAS/logo_sagarde.jpg" alt="Sagarde" style="display:none;opacity:0"><div class="identity"><strong>Centro de mando Sagarde</strong><span>Control integral de obras, post-ventas, mantenimientos y herramientas</span></div><nav class="top-actions"><a href="SAGARDE%20OBRAS%20ABIERTAS/index.html">Obras abiertas</a><a href="POST-VENTAS/index.html">Post-ventas</a><a href="MANTENIMIENTOS/index.html">Mantenimientos</a><a href="SAGARDE%20(OLD)/index.html">Archivo histórico</a></nav></div></header>
<main class="shell"><div class="intro"><div><h1>Inicio</h1><p>Todo el entorno de trabajo, con datos reales de los sistemas ya construidos, desde un unico punto.</p></div><label class="search-wrap"><input id="search" class="search" type="search" placeholder="Buscar obra, area, aplicacion o ruta"><span class="search-symbol">&#9906;</span></label></div>
<div class="alertas">{alertas_html}</div>
<section class="kpis">{kpi_html}</section>
{obras_section}
<div class="section-head"><h2>Areas de trabajo</h2><span id="areaCount">{len(areas)} disponibles</span></div><section class="areas" id="areas">{area_cards}</section>
{postventas_section}
{obras_cerradas_section}
<div class="section-head"><h2>Aplicaciones y paneles</h2><span id="appCount">{len(apps)} accesos</span></div><section class="workspace"><div class="panel"><div class="panel-title">Accesos detectados</div><div class="app-list" id="apps">{app_rows}<div class="empty" id="empty">No hay coincidencias.</div></div></div></section>
<div class="footer">Actualizado {generated} · Ejecuta Actualizar_Sagarde.bat para refrescar el centro de mando completo (obras, post-ventas y portal)</div></main>
<script>
const search=document.getElementById('search');
const groups=[{{sel:'.area',count:'areaCount',label:' disponibles'}},{{sel:'.app-row',count:'appCount',label:' accesos'}},{{sel:'.obra',count:null,label:''}},{{sel:'.pv-row',count:null,label:''}}];
const empty=document.getElementById('empty');
function filter(){{const q=search.value.trim().toLowerCase();const ct=document.querySelector('.cerradas-toggle');if(ct)ct.open=q.length>0;let pc=0;groups.forEach(g=>{{const els=[...document.querySelectorAll(g.sel)];let n=0;els.forEach(x=>{{const ok=!q||(x.dataset.search||'').includes(q);x.style.display=ok?'':'none';if(ok)n++}});if(g.count)document.getElementById(g.count).textContent=n+g.label;if(g.sel==='.app-row')pc=n}});empty.style.display=pc?'none':'block'}}
search.addEventListener('input',filter);(function(){{var v=document.getElementById('intro-vid'),i=document.getElementById('logo-img');if(!v)return;function show(){{v.style.transition='opacity .5s';v.style.opacity='0';setTimeout(function(){{v.style.display='none';i.style.display='';setTimeout(function(){{i.style.transition='opacity .5s';i.style.opacity='1';}},20);}},500);}}var fb=setTimeout(show,8000);v.addEventListener('ended',function(){{clearTimeout(fb);show();}});v.addEventListener('error',function(){{v.style.display='none';i.style.display='';i.style.opacity='1';}});}})();</script></body></html>'''


def main() -> None:
    areas = [scan_area(p) for p in ROOT.iterdir() if es_carpeta_visible(p)]
    areas.sort(key=lambda x: list(AREA_META).index(x["name"]) if x["name"] in AREA_META else 99)
    apps = discover_apps()
    ro = load_json_safe(RESUMEN_OBRAS_JSON)
    rp = load_json_safe(RESUMEN_POSTVENTAS_JSON)
    mant = escanear_mantenimientos()
    planilla = escanear_planilla()
    obras_cerradas = escanear_obras_cerradas()
    herramientas = escanear_herramientas()
    # MANTENIMIENTOS/index.html lo escribe su propio generador,
    # MANTENIMIENTOS/_SISTEMA/mantenimientos_index.py, igual que
    # POST-VENTAS. Hasta el 08/08/2026 el portal lo sobreescribia aqui
    # con otra plantilla, y como corre el ultimo, la del apartado no se
    # llego a ver nunca desde que se escribio el 27/07. La suya avisa de
    # los contratos sin revisar; esta no lo hacia. Las paginas POR
    # contrato si las sigue generando el portal, justo debajo.
    for m in mant:
        generar_pagina_mantenimiento(m)
    generar_index_archivo_historico(obras_cerradas)
    generar_index_obras_cerradas(obras_cerradas)
    generar_index_herramientas(herramientas, apps)
    generar_index_aplicaciones(apps)
    generar_portal_movil(ro, rp, mant, obras_cerradas)
    OUTPUT.write_text(build_html(areas, apps, ro, rp, mant, planilla, obras_cerradas), encoding="utf-8")
    print(f"Portal generado: {OUTPUT}")
    print(f"Areas: {len(areas)} | Obras cerradas: {len(obras_cerradas)} | Aplicaciones: {len(apps)} | Archivos: {sum(a['files'] for a in areas)} | Mapas de mantenimiento: {len(mant)}")
    if ro:
        print(f"Obras: {ro['totales']} (resumen del {ro['generado']})")
    else:
        print("Aviso: no se encontro resumen_obras.json — ejecuta generar_todos.py en Obras Abiertas primero.")
    if rp:
        print(f"Post-ventas: {rp['totales']} (resumen del {rp['generado']})")
    else:
        print("Aviso: no se encontro postventas_resumen.json — ejecuta postventas_index.py primero.")


if __name__ == "__main__":
    main()
