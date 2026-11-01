# -*- coding: utf-8 -*-
"""Ayudante de las pruebas de «Generar personal» (MA5): abre personal_sagarde.html en Chromium de verdad, con datos INVENTADOS.

Lo usan test_generar_personal_ma5.py y test_lenguaje_electricista.py (para que la guarda de lenguaje recorra los mismos estados).
P3_APP apunta a otra copia de la página (para las mutaciones: se rompe una COPIA, nunca el original)."""
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

import datos_base_trabajadores as D

SISTEMA = Path(__file__).resolve().parent.parent
APP_DIR = Path(os.environ.get("P3_APP") or SISTEMA)
TMP_BASE = Path(os.environ.get("P3_TMP") or tempfile.gettempdir())

ALFA, BETA, GAMMA = "Alfa Instalaciones", "Beta Montajes", "Gamma Electrica"
HORARIO_8H = {"lun": 8, "mar": 8, "mie": 8, "jue": 8, "vie": 8, "sab": 0, "dom": 0}
ANCHOS = [360, 375, 390, 414, 768, 820]
CLAVE_BORRADOR = "sagarde_personal_generar_v1"


def estado(jornada_base=7.5, fichas=None):
    """Una base inventada: Rafa (Alfa, con oficio y horario propio), Pepe (sin empresa), Luis (Beta), Ander (de baja), Zoilo (Sagarde)."""
    if fichas is None:
        fichas = [
            D.ficha(1, "Rafa", ALFA, categoria="Oficial 1ª", horario_preferido=dict(HORARIO_8H)),
            D.ficha(2, "Pepe", ""),
            D.ficha(3, "Luis", BETA),
            D.ficha(4, "Ander", GAMMA, activo=False),
            D.ficha(5, "Zoilo", "Sagarde"),
        ]
    e = D.estado(fichas, {"olabeaga": D.obra("OBRA UNO", [
        D.fila("2026-10-22", "vivienda", "Rafa", 7.5, empresa=ALFA),
        D.fila("2026-10-22", "vivienda", "Luis", 7.5, empresa=BETA),
    ])})
    if jornada_base is None:
        e.pop("jornada_base_h")
    else:
        e["jornada_base_h"] = jornada_base
    return e


def escribir_estado(carpeta, e):
    (Path(carpeta) / "personal_estado.js").write_text(
        "window.SAGARDE_PERSONAL = " + json.dumps(e, ensure_ascii=False) + ";\n", encoding="utf-8")


def hay_chromium():
    import importlib.util
    if os.environ.get("SAGARDE_SIN_NAVEGADOR") == "1":
        return False, "saltada a propósito (SAGARDE_SIN_NAVEGADOR=1)"
    if importlib.util.find_spec("playwright") is None:
        return False, "falta Playwright"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, "Playwright no puede abrir Chromium (%s)" % type(exc).__name__


def con_pagina(fn, e=None, ancho=390, init=None, con_estado=True, con_calculo=True, ir_a_generar=True, esperar=True):
    """Abre la página con ese estado y llama a fn(page, carpeta). Devuelve los errores de JavaScript que dio la página.
    init: código JavaScript que se ejecuta antes que la página (por ejemplo, para dejar algo guardado o bloquear el almacenamiento)."""
    from playwright.sync_api import sync_playwright
    carpeta = TMP_BASE / ("ma5_" + uuid.uuid4().hex[:8])
    carpeta.mkdir(parents=True)
    try:
        shutil.copy2(APP_DIR / "personal_sagarde.html", carpeta / "personal_sagarde.html")
        if con_calculo:
            shutil.copy2(APP_DIR / "personal_calculo.js", carpeta / "personal_calculo.js")
        if con_estado:
            escribir_estado(carpeta, e if e is not None else estado())
        errores = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": ancho, "height": 900})
                page.on("pageerror", lambda x: errores.append(str(x)))
                if init:
                    page.add_init_script(init)
                page.goto((carpeta / "personal_sagarde.html").resolve().as_uri())
                if con_estado and con_calculo and esperar:
                    page.wait_for_selector("table.data tbody tr")
                    if ir_a_generar:
                        page.click('#pestanas [data-v="generar"]')
                        page.wait_for_selector("#gen-empresa")
                fn(page, carpeta)
            finally:
                browser.close()
        return errores
    finally:
        shutil.rmtree(str(carpeta), ignore_errors=True)


def recargar(page, carpeta, e=None):
    """Cambia el estado publicado (si se da) y recarga la página, como cuando el PC publica y se vuelve a abrir."""
    if e is not None:
        escribir_estado(carpeta, e)
    page.reload()
    page.wait_for_selector("#gen-empresa", state="attached")
    page.click('#pestanas [data-v="generar"]')   # la dirección ya lleva #generar, pero así vale con cualquiera
    page.wait_for_selector("#gen-empresa")


def texto(page, sel):
    el = page.query_selector(sel)
    return " ".join(el.inner_text().split()) if el else ""


def anadir(page, nombre, empresa, oficio=None, horario=None):
    page.select_option("#gen-empresa", empresa)
    if horario is not None:
        page.select_option("#gen-horario-tipo", horario)
    page.fill("#gen-nombre", nombre)
    if oficio is not None:
        page.select_option("#gen-categoria", oficio)
    page.click("#btn-gen-anadir")


def filas(page):
    return page.eval_on_selector_all(
        "#tabla-generar tbody tr", "els => els.map(e => [e.dataset.genPreparado, e.innerText.replace(/\\s+/g,' ').trim()])")


def descargar(page):
    """Pulsa «Guardar cambios de la base» y devuelve (nombre del fichero, contenido ya leído)."""
    with page.expect_download() as d:
        page.click("#btn-gen-descargar")
    return d.value.suggested_filename, json.loads(Path(d.value.path()).read_text(encoding="utf-8"))


# Mide, en la página tal como está: desborde horizontal de la página, objetos táctiles de menos de 44 px y tablas convertidas en
# tarjetas que aún tengan desplazamiento lateral propio.
JS_MEDIDAS = """() => {
  const vw = window.innerWidth;
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !e.closest('[hidden]'); };
  const out = { doc: [document.documentElement.scrollWidth, vw], fuera: [], chicos: [], scrolls: [], recortes: [] };
  document.querySelectorAll('body *').forEach(e => {
    if (!vis(e)) return; const r = e.getBoundingClientRect();
    if (r.right > vw + 1 && !e.closest('.base-scroll,.emp-scroll')) out.fuera.push(e.tagName + (e.id ? '#' + e.id : '') + ':' + Math.round(r.right));
  });
  document.querySelectorAll('button, a[href], select, input:not([type=hidden]), summary').forEach(e => {
    if (!vis(e)) return;
    const r = (e.type === 'checkbox' && e.closest('label') ? e.closest('label') : e).getBoundingClientRect();
    if (r.height < 43.5 || r.width < 43.5) out.chicos.push(e.tagName + (e.id ? '#' + e.id : '') + ':' + (e.textContent || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 20) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  document.querySelectorAll('.base-scroll,.emp-scroll').forEach(e => {
    if (vis(e) && e.querySelector('table.tarjetas') && e.scrollWidth > e.clientWidth + 1) out.scrolls.push(e.querySelector('table').id || e.className);
  });
  document.querySelectorAll('.seg').forEach(e => { if (vis(e) && e.scrollWidth > e.clientWidth + 1) out.recortes.push(e.getAttribute('aria-label') + ':' + e.scrollWidth + '>' + e.clientWidth); });
  out.fuera = out.fuera.slice(0, 5);
  return out; }"""
