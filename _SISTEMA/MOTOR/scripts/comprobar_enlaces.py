#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
comprobar_enlaces.py — Enlaces internos rotos en el portal publicado de Sagarde

Recorre un conjunto fijo de paginas de nivel superior (portal raiz, indices
de area, paneles de obra) y comprueba que cada enlace interno relativo
(href/src) apunte a un archivo o carpeta que existe dentro del sitio. No
comprueba enlaces externos (http/https/mailto/tel/javascript:/data:) ni
anclas (#id).

Uso:
  python _SISTEMA/MOTOR/scripts/comprobar_enlaces.py
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
import sys

# _SISTEMA/MOTOR/scripts/comprobar_enlaces.py -> cuatro niveles hasta la raiz.
ROOT = Path(__file__).resolve().parent.parent.parent.parent

OBRA_MOTOR_DIR = ROOT / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
if str(OBRA_MOTOR_DIR) not in sys.path:
    sys.path.insert(0, str(OBRA_MOTOR_DIR))

from registro_obras import OBRAS

ESQUEMAS_EXTERNOS = ("http:", "https:", "mailto:", "tel:", "javascript:", "data:")

PAGINAS_FIJAS = [
    "index.html",
    "SAGARDE OBRAS ABIERTAS/index.html",
    "POST-VENTAS/index.html",
    "MANTENIMIENTOS/index.html",
    "APLICACIONES/index.html",
    "SAGARDE (OLD)/index.html",
]


class _ExtractorEnlaces(HTMLParser):
    """Recoge (valor, linea) de cada href/src de las etiquetas del HTML."""

    def __init__(self):
        super().__init__()
        self.enlaces: list[tuple[str, int]] = []

    def handle_starttag(self, tag, attrs):
        for nombre, valor in attrs:
            if nombre in ("href", "src") and valor:
                self.enlaces.append((valor, self.getpos()[0]))


def extraer_enlaces(html_texto: str) -> list[tuple[str, int]]:
    """Devuelve [(valor_bruto, linea), ...] de cada href/src del HTML."""
    parser = _ExtractorEnlaces()
    parser.feed(html_texto)
    return parser.enlaces


def es_enlace_interno(valor: str) -> bool:
    """True si el enlace es una ruta relativa que hay que comprobar en disco."""
    if valor.startswith("#") or valor.startswith("//"):
        return False
    return not valor.strip().lower().startswith(ESQUEMAS_EXTERNOS)


def resolver_ruta(valor: str, archivo_html: Path) -> Path:
    """Resuelve un enlace interno relativo a la carpeta del HTML que lo contiene."""
    destino = unquote(valor.split("#", 1)[0].split("?", 1)[0])
    return (archivo_html.parent / destino).resolve()


def enlaces_rotos_de_pagina(archivo_html: Path, raiz: Path) -> list[dict]:
    """[{'destino': str, 'linea': int}, ...] de los enlaces internos rotos."""
    texto = archivo_html.read_text(encoding="utf-8")
    raiz = raiz.resolve()
    rotos = []
    for valor, linea in extraer_enlaces(texto):
        if not es_enlace_interno(valor):
            continue
        ruta = resolver_ruta(valor, archivo_html)
        dentro_de_raiz = ruta == raiz or raiz in ruta.parents
        if not ruta.exists() or not dentro_de_raiz:
            rotos.append({"destino": valor, "linea": linea})
    return rotos


def paginas_a_comprobar(raiz: Path) -> list[Path]:
    """Paginas fijas de nivel superior + panel.html de cada obra registrada."""
    paginas = [raiz / rel for rel in PAGINAS_FIJAS]
    for obra in OBRAS:
        paginas.append(
            raiz / "SAGARDE OBRAS ABIERTAS" / obra["carpeta_obra"]
            / "INFORME SAGARDE IA" / "panel.html"
        )
    return paginas


def comprobar_enlaces(raiz: Path | None = None) -> dict:
    """{'ausentes': [Path,...], 'rotos': {Path: [dict,...]}}"""
    raiz = raiz if raiz is not None else ROOT
    ausentes = []
    rotos = {}
    for pagina in paginas_a_comprobar(raiz):
        if not pagina.is_file():
            ausentes.append(pagina)
            continue
        encontrados = enlaces_rotos_de_pagina(pagina, raiz)
        if encontrados:
            rotos[pagina] = encontrados
    return {"ausentes": ausentes, "rotos": rotos}


def main() -> int:
    resultado = comprobar_enlaces(ROOT)
    ausentes = resultado["ausentes"]
    rotos = resultado["rotos"]

    if rotos:
        total = sum(len(v) for v in rotos.values())
        print(f"  [AVISO] {total} enlace(s) roto(s) en el portal publicado:")
        for pagina, items in rotos.items():
            for item in items:
                print(f"    - {pagina.name} -> {item['destino']} (linea {item['linea']})")

    if ausentes:
        print("  [ERROR] Faltan paginas que deberian existir tras publicar el portal:")
        for pagina in ausentes:
            print(f"    - {pagina}")
        return 2

    if rotos:
        return 1

    print("  Todos los enlaces del portal publicado resuelven.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
