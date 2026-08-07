#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mantenimientos_index.py — Generador de índice y resumen de Mantenimientos Sagarde

Escanea las carpetas de contratos en MANTENIMIENTOS/ y produce:
  1. mantenimientos_resumen.json (metadatos y estadísticas para el portal raíz)
  2. MANTENIMIENTOS/index.html (centro de mando interactivo de mantenimientos)

Uso:
  python MANTENIMIENTOS/mantenimientos_index.py
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
import json
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
MOTOR_DIR = ROOT.parent / "_MOTOR_SAGARDE"
if str(MOTOR_DIR) not in sys.path:
    sys.path.insert(0, str(MOTOR_DIR))

from avisos import dias_desde_timestamp, es_aviso_por_antiguedad

INDEX_PATH = ROOT / "index.html"
RESUMEN_JSON = ROOT / "mantenimientos_resumen.json"

IGNORE_DIRS = {".memory", "__pycache__", "_SISTEMA"}
IGNORE_FILES = {"desktop.ini", "thumbs.db", "index.html"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic", ".webp"}
DOC_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".dwg"}

DIAS_ALERTA_MANTENIMIENTO = 90  # alerta desde 91 hasta 399 días


def fmt_dt(ts: float | None) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")


def days_text(ts: float | None) -> str:
    if not ts:
        return "sin fecha"
    d = (datetime.now().date() - datetime.fromtimestamp(ts).date()).days
    if d <= 0:
        return "hoy"
    if d == 1:
        return "ayer"
    return f"hace {d} días"


def days_count(ts: float | None) -> int:
    dias = dias_desde_timestamp(ts)
    return 9999 if dias is None else dias


def clean_name(folder_name: str) -> str:
    name = " ".join(folder_name.split())
    if name.upper().startswith("MANTENIMIENTO "):
        name = name[14:].strip()
    return name or folder_name


def iter_files(folder: Path) -> list[Path]:
    files: list[Path] = []
    for path in folder.rglob("*"):
        if path.is_dir():
            continue
        if any(part in IGNORE_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.name.startswith("~$") or path.name.lower() in IGNORE_FILES:
            continue
        files.append(path)
    return files


def scan_mantenimientos() -> list[dict]:
    contratos: list[dict] = []
    for folder in ROOT.iterdir():
        if not folder.is_dir() or folder.name in IGNORE_DIRS:
            continue
        if folder.name.startswith("_"):
            continue

        files = iter_files(folder)
        docs = [p for p in files if p.suffix.lower() in DOC_EXTS]
        imgs = [p for p in files if p.suffix.lower() in IMAGE_EXTS]

        # Calcular timestamp de modificación más reciente ignorando index.html
        ultima_ts = max((p.stat().st_mtime for p in files), default=0.0)
        if ultima_ts == 0.0:
            try:
                ultima_ts = folder.stat().st_mtime
            except OSError:
                ultima_ts = 0.0

        dias_inactivo = days_count(ultima_ts)
        
        if dias_inactivo <= DIAS_ALERTA_MANTENIMIENTO:
            estado_actividad = "al_dia"
            estado_label = "Al día"
            clase_estado = "ok"
        elif dias_inactivo <= 365:
            estado_actividad = "revision_pendiente"
            estado_label = f"Revisión pendiente ({dias_inactivo}d)"
            clase_estado = "warn"
        else:
            estado_actividad = "inactivo"
            estado_label = f"Inactivo ({dias_inactivo}d)"
            clase_estado = "bad"

        nombre_limpio = clean_name(folder.name)
        folder_rel = folder.name
        index_rel = f"{quote(folder.name, safe='/()[]!$&()*+,;=:@-._~')}/index.html"

        contratos.append({
            "nombre": nombre_limpio,
            "carpeta": folder.name,
            "path": str(folder),
            "n_archivos": len(files),
            "n_documentos": len(docs),
            "n_imagenes": len(imgs),
            "ultima_ts": ultima_ts,
            "ultima_str": fmt_dt(ultima_ts),
            "hace_texto": days_text(ultima_ts),
            "dias_inactivo": dias_inactivo,
            "aviso_activo": es_aviso_por_antiguedad(
                dias_inactivo, DIAS_ALERTA_MANTENIMIENTO),
            "estado_actividad": estado_actividad,
            "estado_label": estado_label,
            "clase_estado": clase_estado,
            "url_index": index_rel,
            "href": f"MANTENIMIENTOS/{index_rel}",
        })

    contratos.sort(key=lambda c: -c["ultima_ts"])

    if not contratos:
        raise SystemExit(
            f"[ERROR] Ningun contrato de mantenimiento bajo {ROOT}. "
            f"Si el script se ha movido, ROOT esta mal calculado. "
            f"No se reescribe index.html con un indice vacio.")

    return contratos


def escribir_resumen_json(contratos: list[dict]):
    inactivos = [c for c in contratos if c["aviso_activo"]]

    resumen = {
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "generado_ts": datetime.now().timestamp(),
        "totales": {
            "n_contratos": len(contratos),
            "n_al_dia": sum(1 for c in contratos if c["estado_actividad"] == "al_dia"),
            "n_pendientes": sum(1 for c in contratos if c["estado_actividad"] == "revision_pendiente"),
            "n_inactivos": sum(1 for c in contratos if c["estado_actividad"] == "inactivo"),
            "n_alertas_desactualizadas": len(inactivos),
            "archivos_totales": sum(c["n_archivos"] for c in contratos),
        },
        "contratos": contratos,
    }

    with open(RESUMEN_JSON, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    print(f"[OK] Mantenimientos JSON generado: {RESUMEN_JSON} ({len(contratos)} contratos)")


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sagarde | Mantenimientos</title>
<style>
:root{{--bg:#eef1f4;--card:#fff;--ink:#182230;--muted:#647184;--line:#d0d5dd;--brand:#b42318;--nav:#0b1f3a;--nav2:#123a63;--accent:#f5a524;--ok:#2e9e5b;--warn:#e07b1a;--bad:#d9483c;--radius:9px;}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;background:var(--bg);color:var(--ink);}}
a{{color:inherit;}}
.top{{background:linear-gradient(120deg,var(--nav),var(--nav2));color:#fff;border-bottom:4px solid var(--brand);}}
.top-inner{{max-width:1440px;margin:auto;padding:18px 28px;display:flex;align-items:center;gap:20px;}}
.logo{{width:min(290px,22vw);height:auto;object-fit:contain;border-radius:9px;box-shadow:0 0 0 3px var(--brand),0 6px 28px rgba(0,0,0,.5);}}
.identity{{min-width:0;}}.identity strong{{font-size:21px;display:block;}}.identity span{{font-size:12px;color:#c7d3e3;}}
.top-actions{{margin-left:auto;display:flex;gap:8px;}}
.top-actions a{{text-decoration:none;border:1px solid rgba(255,255,255,.35);color:#fff;padding:9px 12px;border-radius:5px;font-size:13px;font-weight:600;}}
.wrap{{max-width:1440px;margin:0 auto;padding:24px 28px 38px;}}
.intro{{display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap;margin-bottom:18px;}}
.sub{{font-size:13px;color:var(--muted);margin:0;}}
.search-wrap{{width:min(360px,100%);position:relative;}}
.search{{width:100%;height:42px;padding:0 42px 0 14px;border:1px solid #98a2b3;border-radius:6px;background:#fff;font:inherit;}}
.search-symbol{{position:absolute;right:14px;top:11px;color:#667085;}}
.empty{{display:none;background:#fff;border-radius:var(--radius);padding:30px;text-align:center;color:var(--muted);}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;}}
.card{{background:var(--card);border-radius:var(--radius);padding:20px 22px;box-shadow:0 1px 3px rgba(0,0,0,.08);text-decoration:none;color:var(--ink);display:block;transition:transform .1s;border-top:4px solid var(--accent);}}
.card:hover{{transform:translateY(-2px);box-shadow:0 4px 14px rgba(0,0,0,.12);}}
.card.ok{{border-top-color:var(--ok);}}.card.warn{{border-top-color:var(--warn);}}.card.bad{{border-top-color:var(--bad);}}
.card h2{{font-size:15.5px;font-weight:700;margin-bottom:10px;}}
.card .badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;text-transform:uppercase;margin-bottom:10px;}}
.card .badge.ok{{background:#e8f6ee;color:var(--ok);}}.card .badge.warn{{background:#fff4e5;color:var(--warn);}}.card .badge.bad{{background:#fdecea;color:var(--bad);}}
.card .row{{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-top:8px;}}
.footer{{text-align:right;font-size:11px;color:var(--muted);margin-top:20px;}}
@media(max-width:900px){{.logo{{width:190px;}}}}
@media(max-width:600px){{.top-inner,.wrap{{padding-left:14px;padding-right:14px;}}.logo{{width:160px;}}.top-actions{{display:none;}}}}
</style></head><body>
<header class="top"><div class="top-inner">
  <img class="logo" src="../POST-VENTAS/logo_sagarde.jpg" alt="Sagarde">
  <div class="identity"><strong>Contratos de Mantenimiento</strong><span>Gestión e inspección periódica de instalaciones eléctricas</span></div>
  <nav class="top-actions">
    <a href="../index.html">&#8962; Portal</a>
    <a href="../SAGARDE%20OBRAS%20ABIERTAS/index.html">Obras abiertas</a>
    <a href="../POST-VENTAS/index.html">Post-ventas</a>
    <a href="./">Mantenimientos</a>
  </nav>
</div></header>
<div class="wrap">
  <div class="intro">
    <p class="sub">{n_contratos} contrato(s) de mantenimiento &middot; {n_alertas} aviso(s) entre 91 y 399 días sin revisión &middot; actualizado {generado}</p>
    <label class="search-wrap"><input id="s" class="search" type="search" placeholder="Buscar contrato..."><span class="search-symbol">&#9906;</span></label>
  </div>
  <div class="grid" id="grid">{tarjetas}</div>
  <div class="empty" id="empty">No hay coincidencias.</div>
  <p class="footer">Actualizado {generado} &middot; Ejecuta Actualizar_Sagarde.bat para refrescar</p>
</div>
<script>
const s=document.getElementById('s'),cards=[...document.querySelectorAll('#grid .card')],empty=document.getElementById('empty');
s.addEventListener('input',()=>{{const q=s.value.trim().toLowerCase();let n=0;
cards.forEach(c=>{{const ok=!q||(c.dataset.search||'').includes(q);c.style.display=ok?'':'none';if(ok)n++;}});
empty.style.display=n?'none':'block';}});
</script>
</body></html>"""

CARD_TEMPLATE = """<a class="card {clase}" href="{url_index}" data-search="{busca}">
<h2>{nombre}</h2>
<div><span class="badge {clase}">{estado_label}</span></div>
<div class="row"><span>Último archivo</span><span>{hace}</span></div>
<div class="row"><span>Última modificación</span><span>{ultima_str}</span></div>
<div class="row"><span>Archivos totales</span><span>{n_archivos}</span></div>
<div class="row"><span>Documentos / Fotos</span><span>{n_docs} doc / {n_imgs} img</span></div>
</a>"""


def generar_html_index(contratos: list[dict]):
    tarjetas_html = ""
    for c in contratos:
        t = CARD_TEMPLATE.format(
            clase=c["clase_estado"],
            url_index=c["url_index"],
            busca=escape(c["nombre"].lower(), quote=True),
            nombre=escape(c["nombre"]),
            estado_label=escape(c["estado_label"]),
            hace=escape(c["hace_texto"]),
            ultima_str=escape(c["ultima_str"]),
            n_archivos=c["n_archivos"],
            n_docs=c["n_documentos"],
            n_imgs=c["n_imagenes"],
        )
        tarjetas_html += t

    n_alertas = sum(1 for c in contratos if c["aviso_activo"])
    html_out = INDEX_TEMPLATE.format(
        n_contratos=len(contratos),
        n_alertas=n_alertas,
        generado=datetime.now().strftime("%d/%m/%Y %H:%M"),
        tarjetas=tarjetas_html,
    )

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"[OK] Mantenimientos index.html generado: {INDEX_PATH}")


def main():
    print("[1/2] Escaneando contratos de Mantenimiento...")
    contratos = scan_mantenimientos()
    print(f"      {len(contratos)} contrato(s) encontrados.")
    escribir_resumen_json(contratos)
    print("[2/2] Generando portal MANTENIMIENTOS/index.html...")
    generar_html_index(contratos)


if __name__ == "__main__":
    main()
