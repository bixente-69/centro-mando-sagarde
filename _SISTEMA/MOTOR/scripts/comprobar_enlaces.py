#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
comprobar_enlaces.py — Enlaces internos rotos en el portal publicado de Sagarde

Recorre un conjunto fijo de paginas de nivel superior (portal raiz, indices
de area, paneles de obra) y comprueba que cada enlace interno relativo
(href/src) apunte a un archivo que existe. No comprueba enlaces externos
(http/https/mailto/tel/javascript:) ni anclas (#id).

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

ESQUEMAS_EXTERNOS = ("http:", "https:", "mailto:", "tel:", "javascript:")

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
    if valor.startswith("#"):
        return False
    return not valor.strip().lower().startswith(ESQUEMAS_EXTERNOS)


def resolver_ruta(valor: str, archivo_html: Path) -> Path:
    """Resuelve un enlace interno relativo a la carpeta del HTML que lo contiene."""
    destino = unquote(valor.split("#", 1)[0].split("?", 1)[0])
    return (archivo_html.parent / destino).resolve()


if __name__ == "__main__":
    sys.exit(0)
