# -*- coding: utf-8 -*-
"""Cierra una obra y la manda al archivo, dejando el entorno limpio.

Cerrar una obra a mano —mover la carpeta y ya— parece funcionar: el motor la
salta con un aviso (`generar_todos.py`) y el portal la recoge sola como
cerrada. Pero deja la obra en `registro_obras.py` avisando en cada
publicacion, y su adaptador huerfano en `adaptadores/`, que es como llevan
Egurrola y Zorrozaure desde que se cerraron.

Uso:
    python cerrar_obra.py <id_obra>              # informa, no toca nada
    python cerrar_obra.py <id_obra> --ejecutar   # lo hace

Diseno: _SISTEMA/docs/superpowers/specs/2026-08-13-cierre-de-obra-design.md
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
OBRAS_ABIERTAS = "SAGARDE OBRAS ABIERTAS"
OBRAS_CERRADAS = os.path.join("SAGARDE (OLD)", "OBRAS CERRADAS")
SALIDA_OBRA = "INFORME SAGARDE IA"
MOTOR = "_SISTEMA INFORME SAGARDE IA"


class CierreAbortado(Exception):
    """El cierre no puede seguir. Nada se ha movido."""


def _carpeta_obra(raiz: Path, obra: dict) -> Path:
    return Path(raiz) / OBRAS_ABIERTAS / obra["carpeta_obra"]


def _pct_publicado(raiz: Path, nombre: str):
    """pct_ponderado que publica el motor, si existe el resumen."""
    resumen = Path(raiz) / OBRAS_ABIERTAS / MOTOR / "resumen_obras.json"
    if not resumen.exists():
        return None
    try:
        datos = json.loads(resumen.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    obras = datos if isinstance(datos, list) else datos.get("obras", [])
    for o in obras:
        if isinstance(o, dict) and o.get("nombre") == nombre:
            return o.get("pct_ponderado")
    return None


def estado_de_cierre(raiz: Path, obra: dict) -> dict:
    """Como esta la obra ahora mismo, leido de su ficha.

    Sin ficha no se inventa nada: `celdas` sale None y el desglose vacio.
    """
    raiz = Path(raiz)
    ficha_ruta = _carpeta_obra(raiz, obra) / SALIDA_OBRA / "ficha_obra.json"
    desglose: Counter = Counter()
    ubicaciones: set = set()
    celdas = tajos = ultima = None
    hay_ficha = ficha_ruta.exists()
    if hay_ficha:
        ficha = json.loads(ficha_ruta.read_text(encoding="utf-8"))
        estados = ficha.get("estados") or {}
        celdas = len(estados)
        tajos = len(ficha.get("tajos", {}).get("aplicables", []))
        for clave, celda in estados.items():
            valor = celda.get("v") if isinstance(celda, dict) else celda
            if valor:
                desglose[valor] += 1
            partes = clave.split("__")
            if len(partes) == 4:
                ubicaciones.add((partes[0], partes[1], partes[3]))
        revisiones = ficha.get("revisiones") or []
        if revisiones:
            ultima = revisiones[-1].get("fecha")
    return {
        "obra": obra["nombre"],
        "id": obra["id"],
        "carpeta": obra["carpeta_obra"],
        "ubicaciones": len(ubicaciones) if hay_ficha else None,
        "tajos": tajos,
        "celdas": celdas,
        "desglose": dict(desglose),
        "ultima_revision": ultima,
        "pct": _pct_publicado(raiz, obra["nombre"]),
    }


# ─── El registro unico ────────────────────────────────────────────────────
def ids_declarados(fuente: str) -> list:
    """Los id de OBRAS, ejecutando el registro en un espacio aparte."""
    espacio: dict = {}
    exec(compile(fuente, "registro_obras.py", "exec"), espacio)
    return [o["id"] for o in espacio["OBRAS"]]


def registro_sin_obra(fuente: str, id_obra: str) -> str:
    """Devuelve el registro sin esa obra. No escribe nada.

    Se localiza el bloque con `ast`, no con expresiones regulares: el nodo del
    diccionario ya sabe en que linea empieza y acaba, comentarios de dentro
    incluidos. Despues se comprueba que lo que queda sigue siendo Python y que
    solo ha desaparecido la obra pedida; si no, no se devuelve nada.
    """
    arbol = ast.parse(fuente)
    lista = None
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign):
            for destino in nodo.targets:
                if getattr(destino, "id", None) == "OBRAS":
                    lista = nodo.value
    if not isinstance(lista, ast.List):
        raise CierreAbortado(
            "registro_obras.py no declara una lista OBRAS; no se toca.")

    objetivo = None
    for elemento in lista.elts:
        if not isinstance(elemento, ast.Dict):
            continue
        for clave, valor in zip(elemento.keys, elemento.values):
            if (getattr(clave, "value", None) == "id"
                    and getattr(valor, "value", None) == id_obra):
                objetivo = elemento
    if objetivo is None:
        raise CierreAbortado(
            f"El registro no declara ninguna obra con id '{id_obra}'.")

    lineas = fuente.splitlines(keepends=True)
    nuevo = "".join(lineas[:objetivo.lineno - 1] + lineas[objetivo.end_lineno:])

    antes = ids_declarados(fuente)
    esperado = [i for i in antes if i != id_obra]
    despues = ids_declarados(nuevo)
    if despues != esperado:
        raise CierreAbortado(
            "Retirar la obra del registro habria cambiado algo mas: "
            f"esperaba {esperado} y queda {despues}. No se escribe nada.")
    return nuevo


# ─── Mover ────────────────────────────────────────────────────────────────
def archivar_adaptador(raiz: Path, obra: dict):
    """Mueve el adaptador —y su prueba— dentro de la obra, a su `_SISTEMA`.

    Asi no queda un huerfano en `adaptadores/` —como Egurrola y Zorrozaure—
    pero el codigo que sabe leer sus hojas viaja con la obra por si algun dia
    hay que releerlas. Devuelve el destino del adaptador, o None si no tenia.

    La prueba del adaptador se lleva con el: se quedo atras al cerrar Orueta,
    importando un modulo que ya no existia, y tumbo la suite entera.
    """
    raiz = Path(raiz)
    nombre = obra.get("adaptador")
    if not nombre:
        return None
    origen = raiz / OBRAS_ABIERTAS / MOTOR / "adaptadores" / f"{nombre}.py"
    if not origen.exists():
        return None
    destino_dir = _carpeta_obra(raiz, obra) / "_SISTEMA"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / origen.name
    shutil.move(str(origen), str(destino))

    prueba = raiz / OBRAS_ABIERTAS / MOTOR / "tests" / f"test_{nombre}.py"
    if prueba.exists():
        shutil.move(str(prueba), str(destino_dir / prueba.name))
    return destino


def mover_a_cerradas(raiz: Path, obra: dict) -> Path:
    """Mueve la carpeta entera al archivo historico."""
    raiz = Path(raiz)
    origen = _carpeta_obra(raiz, obra)
    if not origen.is_dir():
        raise CierreAbortado(f"La carpeta de la obra no existe: {origen}")
    destino = raiz / OBRAS_CERRADAS / obra["carpeta_obra"]
    if destino.exists():
        raise CierreAbortado(
            f"Ya hay una obra archivada con ese nombre: {destino}. "
            "No se sobrescribe.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(origen), str(destino))
    return destino


# ─── Como termino la obra ─────────────────────────────────────────────────
def escribir_cierre(destino: Path, estado: dict, commit) -> Path:
    """Deja dentro de la obra archivada como termino.

    Es lo que hace que cerrar no sea perder: dentro de dos anos la carpeta
    dice como acabo sin tener que bucear en el historial de git.
    """
    carpeta = Path(destino) / "_SISTEMA"
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "cierre.json"
    ruta.write_text(json.dumps({
        "obra": estado["obra"],
        "id": estado["id"],
        "fecha_cierre": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "commit_al_cerrar": commit,
        "estado_final": {
            "pct_ponderado": estado["pct"],
            "ubicaciones": estado["ubicaciones"],
            "tajos": estado["tajos"],
            "celdas": estado["celdas"],
            "desglose": estado["desglose"],
            "ultima_revision": estado["ultima_revision"],
        },
        "alfabeto": {
            "X": "terminado", "M": "mas del 50%", "/": "iniciado",
            "P": "pendiente confirmado", "?": "sin mirar", "N": "no aplica",
        },
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


# ─── Guardas y orquestacion ───────────────────────────────────────────────
def _registro_ruta(raiz: Path) -> Path:
    return Path(raiz) / OBRAS_ABIERTAS / MOTOR / "registro_obras.py"


def _obra_del_registro(raiz: Path, id_obra: str) -> dict:
    fuente = _registro_ruta(raiz).read_text(encoding="utf-8")
    espacio: dict = {}
    exec(compile(fuente, "registro_obras.py", "exec"), espacio)
    for obra in espacio["OBRAS"]:
        if obra["id"] == id_obra:
            return obra
    raise CierreAbortado(
        f"El registro no declara ninguna obra con id '{id_obra}'. "
        f"Hay estas: {', '.join(o['id'] for o in espacio['OBRAS'])}")


def cambios_pendientes(raiz: Path, rutas: list) -> list:
    """Cuales de esas rutas tienen cambios sin commitear.

    Solo se mira lo que el cierre va a tocar: exigir el arbol entero limpio
    bloquearia el primer uso, porque este mismo script estara sin publicar la
    primera vez que se use.
    """
    try:
        salida = subprocess.run(
            ["git", "status", "--porcelain", "--"] + list(rutas),
            cwd=str(raiz), capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []          # sin git no se bloquea el cierre
    return [l[3:].strip().strip('"')
            for l in salida.stdout.splitlines() if l.strip()]


def _commit_actual(raiz: Path):
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=str(raiz), capture_output=True, text=True,
                           timeout=60)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def cerrar(raiz: Path, id_obra: str, ejecutar: bool = False) -> dict:
    """Cierra la obra. Sin `ejecutar`, solo mide y devuelve el informe."""
    raiz = Path(raiz)
    obra = _obra_del_registro(raiz, id_obra)
    carpeta = _carpeta_obra(raiz, obra)
    if not carpeta.is_dir():
        raise CierreAbortado(
            f"La obra esta en el registro pero su carpeta no existe: {carpeta}")
    destino_previsto = raiz / OBRAS_CERRADAS / obra["carpeta_obra"]
    if destino_previsto.exists():
        raise CierreAbortado(
            f"Ya hay una obra archivada con ese nombre: {destino_previsto}.")

    estado = estado_de_cierre(raiz, obra)
    resultado = {"estado": estado, "movida": False, "destino": None,
                 "adaptador": None, "cierre": None}
    if not ejecutar:
        return resultado

    implicadas = [
        f"{OBRAS_ABIERTAS}/{obra['carpeta_obra']}",
        f"{OBRAS_ABIERTAS}/{MOTOR}/registro_obras.py",
        f"{OBRAS_ABIERTAS}/{MOTOR}/adaptadores/{obra.get('adaptador', '')}.py",
    ]
    sucias = cambios_pendientes(raiz, implicadas)
    if sucias:
        raise CierreAbortado(
            "Hay cambios sin commitear en lo que el cierre va a mover:\n  "
            + "\n  ".join(sucias)
            + "\nCommitealos o descartalos antes de cerrar la obra.")

    commit = _commit_actual(raiz)
    adaptador = archivar_adaptador(raiz, obra)

    registro = _registro_ruta(raiz)
    nuevo = registro_sin_obra(registro.read_text(encoding="utf-8"), id_obra)
    registro.write_text(nuevo, encoding="utf-8")

    destino = mover_a_cerradas(raiz, obra)
    resultado["destino"] = destino
    # El adaptador se archivo dentro de la obra, asi que se ha movido con
    # ella: informar de su ruta anterior seria mandar a un sitio que ya no
    # existe.
    if adaptador is not None:
        resultado["adaptador"] = destino / "_SISTEMA" / adaptador.name
    resultado["movida"] = True
    resultado["cierre"] = escribir_cierre(destino, estado, commit)
    return resultado


def _informe(estado: dict) -> str:
    orden = ("X", "M", "/", "P", "?", "N")
    # Separador ASCII a proposito: esto se lee en la consola de Windows desde
    # un .bat, y un `·` sale como `?` o revienta segun la pagina de codigos.
    desglose = "  ".join(
        f"{e}={estado['desglose'][e]}"
        for e in orden if estado["desglose"].get(e))

    def val(clave):
        return estado[clave] if estado[clave] is not None else "(sin dato)"

    return "\n".join([
        f"  Obra            : {estado['obra']}  (id {estado['id']})",
        f"  Carpeta         : {estado['carpeta']}",
        f"  Avance publicado: {val('pct')}",
        f"  Ultima revision : {val('ultima_revision')}",
        f"  Ubicaciones     : {val('ubicaciones')}",
        f"  Tajos           : {val('tajos')}",
        f"  Celdas          : {val('celdas')}",
        f"  Desglose        : {desglose or '(sin dato)'}",
    ])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Cierra una obra y la manda a SAGARDE (OLD)/OBRAS CERRADAS.")
    parser.add_argument("id_obra", help="id de la obra en registro_obras.py")
    parser.add_argument("--ejecutar", action="store_true",
                        help="Hace el cierre. Sin esto solo informa.")
    args = parser.parse_args(argv)

    try:
        resultado = cerrar(RAIZ, args.id_obra, ejecutar=args.ejecutar)
    except CierreAbortado as err:
        print(f"[ABORTADO] {err}")
        return 1

    estado = resultado["estado"]
    print("\nAsi esta la obra ahora mismo:\n")
    print(_informe(estado))

    if not resultado["movida"]:
        print("\n  No se ha movido nada. Para cerrarla de verdad:")
        print(f"    python cerrar_obra.py {args.id_obra} --ejecutar\n")
        return 0

    print("\n  Cerrada:")
    print(f"    Carpeta archivada en : {resultado['destino']}")
    print(f"    Adaptador archivado  : {resultado['adaptador'] or 'no tenia'}")
    print(f"    Ficha de cierre      : {resultado['cierre']}")
    print("\n  Para deshacer el movimiento de la carpeta:")
    print(f'    move "{resultado["destino"]}" '
          f'"{RAIZ / OBRAS_ABIERTAS / estado["carpeta"]}"')
    print("    (y `git checkout -- registro_obras.py` para devolverla al registro)")
    print("\n  Ahora: lanza Actualizar_Sagarde.bat y comprueba que la obra ya no")
    print("  sale en resumen_obras.json, que aparece en el indice de cerradas,")
    print("  y que las dos suites siguen verdes.")
    print("  El seguimiento posterior de esta obra, si lo hay, va por postventa.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
