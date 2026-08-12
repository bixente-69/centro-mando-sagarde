# -*- coding: utf-8 -*-
"""Mantiene al dia el mapa mental del entorno en cada Actualizar_Sagarde.bat.

El mapa (`_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`) es lectura obligatoria
al empezar sesion. Cuando envejece manda a ciegas a quien lo lee: el 08/08/2026
el motor bajo a `_SISTEMA/MOTOR/` y el documento siguio diciendo
`_MOTOR_SAGARDE/` 23 veces hasta el 12/08.

Este script hace las dos unicas cosas que una maquina puede hacer con honradez
sobre un documento escrito a mano:

1. **Regenera lo derivable.** Entre marcas `<!-- AUTO:nombre -->` reescribe la
   fecha y la tabla de estado de las obras, leidas de las fichas.
2. **Audita lo que no puede reescribir.** Comprueba cada ruta que el documento
   declara y publica en el propio mapa las que ya no existen. La prosa no se
   toca: se senala.

Lo que NO hace, a proposito: reescribir prosa, recuentos narrados ni juicios de
certeza. Un generador que rehiciera el texto entero borraria el criterio de
quien lo escribio.

Limitacion declarada: solo se auditan las rutas que llevan carpeta (`a/b.py`).
Un nombre suelto (`panel.html`, `AAAA-MM-DD-descripcion.md`) es ambiguo entre
fichero y convencion de nombre, y marcarlo daria falsos positivos.

Uso:
    python _SISTEMA/MOTOR/scripts/actualizar_mapa_mental.py [--comprobar]

Devuelve 1 si el mapa declara alguna ruta muerta, para que el BAT lo avise.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
MAPA = RAIZ / "_SISTEMA" / "docs" / "SAGARDE_MAPA_MENTAL_ENTORNO.md"

#: Bloques generados. El mapa tiene que traer las dos marcas de cada uno.
BLOQUES = ("estado", "rutas_muertas")

#: El propio mapa declara esta abreviatura en su cabecera. Si el documento la
#: usa, el auditor tiene que entenderla igual que la entiende un lector.
ABREVIATURAS = {
    "_SISTEMA...": "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA",
}

# Caracteres que delatan una plantilla, un comodin de nombre o una expresion
# que no es una ruta: `<obra>/...`, `${k}`, `{plans,specs}`, `X M / P ? N`.
_NO_ES_RUTA = ("<", ">", "?", "{", "}", "$", "…", '"')

# Solo codigo en linea: nunca cruza un salto. Sin acotarlo, un bloque ``` sin
# cerrar emparejaria comillas de secciones distintas y devolveria parrafos
# enteros como si fueran rutas.
#: Sello de hora de los bloques generados. Se ignora al decidir si el
#: documento cambio de verdad; ver `actualizar_mapa`.
_SELLO = re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}")

_ENTRE_COMILLAS = re.compile(r"`([^`\n]+)`")
_VALLA = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
_BLOQUE_AUTO = re.compile(r"<!-- AUTO:\w+ -->.*?<!-- /AUTO:\w+ -->", re.DOTALL)
_REFERENCIA_DE_LINEA = re.compile(r":\d+(?:\s*[-,]\s*\d+)*$")


class BloqueAusente(Exception):
    """El mapa no trae la marca del bloque que se iba a escribir.

    Es un error y no un aviso: un nombre de bloque mal escrito dejaria el
    documento sin actualizar sin que nadie se enterase, que es exactamente la
    familia de fallos de este proyecto.
    """


# ─── Rutas declaradas en el documento ─────────────────────────────────────
def _limpiar(token: str) -> str | None:
    """Normaliza un token entre comillas, o None si no es una ruta."""
    # Solo se recorta por la derecha: `.claude/launch.json` no es
    # `claude/launch.json`, y perder el punto inventaba una carpeta que no
    # existe y daba por muerta una que si.
    t = token.strip().rstrip(".,;:")
    if not t or any(c in t for c in _NO_ES_RUTA):
        return None
    # `X M / vacio`: una barra rodeada de espacios nunca separa carpetas.
    if " / " in t or " \\ " in t:
        return None
    t = _REFERENCIA_DE_LINEA.sub("", t).strip()
    for abreviatura, completa in ABREVIATURAS.items():
        if t.startswith(abreviatura):
            t = completa + t[len(abreviatura):]
    if "..." in t:
        return None          # plantilla: `SAGARDE .../REVISION/.../*.md`
    t = t.replace("\\", "/")
    if t.startswith("/"):
        return None          # `/sagarde-revision` es un comando, no una ruta
    t = t.strip("/")
    if "/" not in t:
        return None          # nombre suelto: ambiguo, ver limitacion arriba
    return t


_TIENE_EXTENSION = re.compile(r"\.[A-Za-z0-9]{1,6}$")


def _es_auditable(ruta: str, raiz: Path) -> bool:
    """Si podemos afirmar que el token pretendia ser un fichero o carpeta.

    Dos senales bastan y ninguna otra es fiable: que el ultimo tramo lleve
    extension, o que el primero sea algo que existe en la raiz. Sin este
    filtro, `task/floor/building/unit/status` (el esquema comun) y
    `all/recent/vencido/pdf/word/images` (los filtros de postventa) se
    denunciaban como carpetas perdidas.
    """
    tramos = ruta.split("/")
    if _TIENE_EXTENSION.search(tramos[-1]):
        return True
    return os.path.exists(os.path.join(str(raiz), tramos[0]))


def extraer_rutas(texto: str, raiz: Path = RAIZ) -> list[str]:
    """Rutas que el documento declara a mano, en orden y sin repetir.

    Quedan fuera dos cosas. Los diagramas y arboles entre ``` , que son
    dibujos y no declaraciones. Y los bloques `<!-- AUTO:... -->`, que los
    escribe este mismo script: auditarlos haria que el documento se
    denunciase a si mismo, porque el bloque nombra la ruta del generador.
    """
    prosa = _BLOQUE_AUTO.sub("", _VALLA.sub("", texto))
    vistas: dict[str, None] = {}
    for token in _ENTRE_COMILLAS.findall(prosa):
        ruta = _limpiar(token)
        if ruta and _es_auditable(ruta, Path(raiz)):
            vistas.setdefault(ruta, None)
    return list(vistas)


_PODAR = {".git", "__pycache__", "node_modules", ".recortes"}
_INDICES: dict[str, tuple[str, ...]] = {}


def _indice(raiz: Path) -> tuple[str, ...]:
    """Todas las rutas relativas del arbol, para resolver citas parciales."""
    clave = str(raiz)
    if clave not in _INDICES:
        rutas = []
        for base, dirs, ficheros in os.walk(clave):
            dirs[:] = [d for d in dirs
                       if d not in _PODAR and not d.endswith(".recortes")]
            relativa = os.path.relpath(base, clave).replace(os.sep, "/")
            prefijo = "" if relativa == "." else relativa + "/"
            for nombre in list(dirs) + ficheros:
                rutas.append(prefijo + nombre)
        _INDICES[clave] = tuple(rutas)
    return _INDICES[clave]


def _existe(raiz: Path, ruta: str) -> bool:
    """Si la ruta declarada lleva a algo real.

    Se acepta tambien la cita parcial: el mapa nombra
    `reglas/CATALOGO_TAJOS.json` sin la carpeta que lo contiene, y quien lo
    lee encuentra el fichero igual. Lo que no aparece por ninguna parte del
    arbol es lo que se denuncia.
    """
    comodin = any(c in ruta for c in "*[")
    destino = os.path.join(str(raiz), ruta.replace("/", os.sep))
    if comodin:
        if glob.glob(destino):
            return True
    elif os.path.exists(destino):
        return True

    cola = "*/" + ruta
    for candidata in _indice(Path(raiz)):
        if comodin:
            if fnmatch(candidata, ruta) or fnmatch(candidata, cola):
                return True
        elif candidata.endswith("/" + ruta):
            return True
    return False


def rutas_muertas(texto: str, raiz: Path) -> list[str]:
    """Rutas declaradas que no existen en ninguna parte del arbol."""
    raiz = Path(raiz)
    return [r for r in extraer_rutas(texto, raiz) if not _existe(raiz, r)]


# ─── Bloques generados ────────────────────────────────────────────────────
def reemplazar_bloque(texto: str, nombre: str, contenido: str) -> str:
    """Sustituye lo que hay entre las marcas del bloque. La prosa no se toca."""
    abre, cierra = f"<!-- AUTO:{nombre} -->", f"<!-- /AUTO:{nombre} -->"
    i, j = texto.find(abre), texto.find(cierra)
    if i == -1 or j == -1 or j < i:
        raise BloqueAusente(
            f"El mapa no trae las marcas <!-- AUTO:{nombre} --> ... "
            f"<!-- /AUTO:{nombre} -->; no hay donde escribir."
        )
    return texto[:i + len(abre)] + "\n" + contenido.strip("\n") + "\n" + texto[j:]


# ─── Estado real de las obras ─────────────────────────────────────────────
def _kpis(raiz: Path) -> dict[str, str]:
    """pct_ponderado por obra, tal como lo publica el motor."""
    resumen = (raiz / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
               / "resumen_obras.json")
    if not resumen.exists():
        return {}
    try:
        datos = json.loads(resumen.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    obras = datos if isinstance(datos, list) else datos.get("obras", [])
    return {
        o["nombre"]: str(o.get("pct_ponderado", "—"))
        for o in obras if isinstance(o, dict) and o.get("nombre")
    }


def estado_obras(raiz: Path) -> list[dict]:
    """Una fila por obra con ficha: ubicaciones, tajos, celdas y desglose."""
    raiz = Path(raiz)
    kpis = _kpis(raiz)
    filas = []
    patron = os.path.join(
        str(raiz), "SAGARDE OBRAS ABIERTAS", "*", "INFORME SAGARDE IA",
        "ficha_obra.json")
    for ruta in sorted(glob.glob(patron)):
        try:
            ficha = json.loads(Path(ruta).read_text(encoding="utf-8"))
        except (OSError, ValueError) as err:
            print(f"  [AVISO] No se pudo leer {ruta}: {err}")
            continue
        estados = ficha.get("estados") or {}
        desglose: Counter = Counter()
        ubicaciones = set()
        for clave, celda in estados.items():
            valor = celda.get("v") if isinstance(celda, dict) else celda
            if valor:
                desglose[valor] += 1
            partes = clave.split("__")
            if len(partes) == 4:
                ubicaciones.add((partes[0], partes[1], partes[3]))
        nombre = Path(ruta).parent.parent.name
        filas.append({
            "obra": nombre,
            "ubicaciones": len(ubicaciones),
            "tajos": len(ficha.get("tajos", {}).get("aplicables", [])),
            "celdas": len(estados),
            "desglose": dict(desglose),
            "pct": kpis.get(nombre, "—"),
            "actualizado": ficha.get("actualizado", "—"),
        })
    return filas


def recuentos(raiz: Path) -> dict:
    """Las cifras del entorno que el mapa narraba a mano y se desfasaban.

    `registradas` sale del registro único; si no se puede leer se devuelve
    None y se imprime una raya. No se sustituye un desconocido por cero.
    """
    raiz = Path(raiz)
    base = raiz / "SAGARDE OBRAS ABIERTAS"
    carpetas = [
        d for d in (os.listdir(base) if base.is_dir() else [])
        if (base / d).is_dir() and not d.startswith("_")
    ]
    salida = os.path.join(str(base), "*", "INFORME SAGARDE IA")
    ficheros = _indice(raiz)
    return {
        "carpetas": len(carpetas),
        "paneles": len(glob.glob(os.path.join(salida, "panel.html"))),
        "fichas": len(glob.glob(os.path.join(salida, "ficha_obra.json"))),
        "registradas": _obras_registradas(base),
        "py": sum(1 for p in ficheros if p.endswith(".py")),
        "bat": sum(1 for p in ficheros if p.endswith(".bat")),
    }


def _obras_registradas(base: Path) -> int | None:
    """Cuenta `registro_obras.OBRAS` sin importar el módulo.

    Se lee el fichero en vez de importarlo: importar el motor de obras desde
    el motor de la raíz arrastraría sus dependencias, y un fallo ahí tumbaría
    el paso del mapa en mitad de una publicación.
    """
    fuente = base / "_SISTEMA INFORME SAGARDE IA" / "registro_obras.py"
    try:
        texto = fuente.read_text(encoding="utf-8")
    except OSError:
        return None
    cuenta = len(re.findall(r"^\s*['\"]adaptador['\"]\s*:", texto, re.MULTILINE))
    return cuenta or None


_ORDEN_ESTADOS = ("X", "M", "/", "P", "?", "N")


def _cifra(valor) -> str:
    return "—" if valor is None else f"**{valor}**"


def render_estado(filas: list[dict], cuentas: dict, momento: str) -> str:
    """Tabla del bloque AUTO:estado. Desglose completo, no solo el porcentaje."""
    lineas = [
        f"*Lo reescribe `_SISTEMA/MOTOR/scripts/actualizar_mapa_mental.py` en "
        f"cada `Actualizar_Sagarde.bat`. La fecha es la de la última vez que "
        f"alguna cifra cambió: {momento}. No editar a mano.*",
        "",
        f"{_cifra(cuentas.get('carpetas'))} carpetas de obra abiertas · "
        f"{_cifra(cuentas.get('registradas'))} en el registro único · "
        f"{_cifra(cuentas.get('paneles'))} con panel · "
        f"{_cifra(cuentas.get('fichas'))} con ficha. "
        f"En todo el árbol, {_cifra(cuentas.get('py'))} `.py` y "
        f"{_cifra(cuentas.get('bat'))} `.bat`.",
        "",
        "| Obra | Ubic. | Tajos | Celdas | " + " | ".join(_ORDEN_ESTADOS) + " | % |",
        "|---|---|---|---|" + "---|" * len(_ORDEN_ESTADOS) + "---|",
    ]
    for f in filas:
        cuentas = " | ".join(
            str(f["desglose"].get(e, "")) or "–" for e in _ORDEN_ESTADOS)
        lineas.append(
            f"| {f['obra']} | {f['ubicaciones']} | {f['tajos']} | "
            f"{f['celdas']} | {cuentas} | {f['pct']} |")
    if not filas:
        lineas.append("| *ninguna obra con ficha* | | | | " +
                      "| " * len(_ORDEN_ESTADOS) + "|")
    lineas += [
        "",
        "`X` terminado · `M` mas del 50 % · `/` iniciado · `P` pendiente "
        "confirmado · `?` sin mirar · `N` no aplica.",
    ]
    return "\n".join(lineas)


def render_rutas_muertas(muertas: list[str], momento: str) -> str:
    """Lo que el script detecta pero no puede arreglar solo."""
    if not muertas:
        return (f"*Se comprueban en cada `Actualizar_Sagarde.bat`. Ninguna "
                f"ruta declarada en este documento apunta a un sitio que no "
                f"exista (última variación: {momento}).*")
    lineas = [
        f"> ⚠️ **{len(muertas)} rutas declaradas en este documento no existen "
        f"en disco** (detectado el {momento}). Hasta que se corrijan, este "
        f"mapa manda a ciegas a quien lo lea:",
        "",
    ]
    lineas += [f"> - `{r}`" for r in muertas]
    return "\n".join(lineas)


# ─── Orquestacion ─────────────────────────────────────────────────────────
def actualizar_mapa(ruta_mapa: Path = MAPA, raiz: Path = RAIZ,
                    escribir: bool = True) -> dict:
    ruta_mapa, raiz = Path(ruta_mapa), Path(raiz)
    texto = ruta_mapa.read_text(encoding="utf-8")
    momento = datetime.now().strftime("%d/%m/%Y %H:%M")

    muertas = rutas_muertas(texto, raiz)
    nuevo = reemplazar_bloque(
        texto, "estado",
        render_estado(estado_obras(raiz), recuentos(raiz), momento))
    nuevo = reemplazar_bloque(nuevo, "rutas_muertas",
                              render_rutas_muertas(muertas, momento))

    # El sello de hora no cuenta como cambio: si contara, cada pasada
    # reescribiria el fichero, `git add -A` veria diferencias y el BAT haria
    # un commit vacio en cada publicacion.
    cambiado = _SELLO.sub("", nuevo) != _SELLO.sub("", texto)
    if cambiado and escribir:
        ruta_mapa.write_text(nuevo, encoding="utf-8")
    return {"muertas": muertas, "cambiado": cambiado}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comprobar", action="store_true",
                        help="Solo informa; no escribe el mapa.")
    args = parser.parse_args(argv)

    try:
        resultado = actualizar_mapa(escribir=not args.comprobar)
    except BloqueAusente as err:
        print(f"  [ERROR] {err}")
        return 2
    except OSError as err:
        print(f"  [ERROR] No se pudo leer o escribir el mapa mental: {err}")
        return 2

    if resultado["cambiado"]:
        print("  Mapa mental actualizado con el estado de hoy.")
    else:
        print("  Mapa mental ya estaba al dia.")

    muertas = resultado["muertas"]
    if muertas:
        print(f"  [AVISO] El mapa declara {len(muertas)} rutas que no existen:")
        for ruta in muertas:
            print(f"    - {ruta}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
