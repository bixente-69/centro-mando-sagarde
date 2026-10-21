# -*- coding: utf-8 -*-
"""Actualiza una sola obra SAGARDE mediante un flujo verificable.

Por defecto solo simula. ``--escribir`` aplica las hojas pendientes, vuelve a
simular las de vivienda, regenera exclusivamente la obra y verifica que no se
hayan movido las demás.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
RAIZ = SCRIPT_DIR.parents[2]
OBRAS_DIR = RAIZ / "SAGARDE OBRAS ABIERTAS"
MOTOR_IA_DIR = OBRAS_DIR / "_SISTEMA INFORME SAGARDE IA"
INDEX_PATH = OBRAS_DIR / "index.html"
LOGS_DIR = RAIZ / "_SISTEMA" / "MOTOR" / "logs"
PYTHON = ["py", "-3.11"]
FICHA_AUSENTE = "<FICHA_AUSENTE>"
UMBRAL_CAMBIOS_MEDIDOS = 400
UMBRAL_PROPORCION_MARCAS = 0.15
MENSAJE_PUBLICACION = (
    "Suite completa no necesaria: no se ha tocado codigo. "
    "Publicar = Actualizar_Sagarde.bat (lo lanza Bixente)"
)
ROJO = "\033[31m"
RESET = "\033[0m"

if str(MOTOR_IA_DIR) not in sys.path:
    sys.path.insert(0, str(MOTOR_IA_DIR))

from lector_hoja_tajos_html import _fecha_desde_nombre  # noqa: E402
from registro_obras import OBRAS  # noqa: E402


class ErrorActualizacion(RuntimeError):
    """Error operativo o comprobación que no pudo completarse."""


class RequiereRevisionHumana(RuntimeError):
    """Una simulación activó una guarda que no admite escritura."""

    def __init__(self, analisis: "AnalisisSimulacion"):
        super().__init__("la simulación requiere revisión humana")
        self.analisis = analisis


@dataclass(frozen=True)
class Hoja:
    ruta: Path
    fecha: str
    orden: str
    tipo: str
    sha256: str


@dataclass
class DeteccionHojas:
    vivienda: list[Hoja] = field(default_factory=list)
    garaje: list[Hoja] = field(default_factory=list)
    ya_aplicadas: list[Hoja] = field(default_factory=list)
    copias_identicas: list[tuple[Hoja, Hoja]] = field(default_factory=list)
    hojas_de_alta: list[Hoja] = field(default_factory=list)


@dataclass(frozen=True)
class Guarda:
    codigo: str
    motivo: str
    seccion: str


@dataclass
class AnalisisSimulacion:
    salida: str
    marcas: int | None
    cambios: int | None
    blancos_a_p: int | None
    transiciones: list[tuple[str, str, int]]
    guardas: list[Guarda]
    estructuras_aceptadas: list[str] = field(default_factory=list)
    cambios_medidos: int | None = None
    hoja_grande_aceptada: int | None = None
    returncode: int = 0


@dataclass(frozen=True)
class CambioEstado:
    clave: str
    de: str | None
    a: str
    fecha_anterior: str | None


@dataclass
class Retrocesos:
    bajadas: list[CambioEstado] = field(default_factory=list)
    retiradas: list[CambioEstado] = field(default_factory=list)
    a_n: list[CambioEstado] = field(default_factory=list)


@dataclass
class ComparacionTarjetas:
    cambiadas_ajenas: list[str]
    objetivo_cambio: bool
    faltantes: list[str] = field(default_factory=list)


@dataclass
class ComparacionSha:
    cambiadas: list[str]
    faltantes: list[str]


@dataclass(frozen=True)
class ResumenFicha:
    estados: dict[str, int]
    pct_estricto: float
    pct_ponderado: float
    revisiones_vivienda: int
    revisiones_garaje: int


@dataclass
class VerificacionPdf:
    ruta: Path | None
    paginas: int | None
    paginas_esperadas: int | None
    fecha_esperada: str | None
    fechas_por_pagina: list[str | None]
    errores: list[str]
    avisos: list[str]


def _configurar_stdout_utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _leer_json(ruta: Path, *, obligatorio: bool = True):
    if not ruta.is_file():
        if obligatorio:
            raise ErrorActualizacion(f"No existe el fichero obligatorio: {ruta}")
        return None
    try:
        with ruta.open(encoding="utf-8") as f:
            dato = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ErrorActualizacion(f"No se pudo leer {ruta}: {exc}") from exc
    if not isinstance(dato, dict):
        raise ErrorActualizacion(f"{ruta} no contiene un objeto JSON.")
    return dato


def _ruta_ficha(carpeta_obra: Path, nombre: str) -> Path:
    return carpeta_obra / "INFORME SAGARDE IA" / nombre


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    try:
        with ruta.open("rb") as f:
            for bloque in iter(lambda: f.read(1024 * 1024), b""):
                h.update(bloque)
    except OSError as exc:
        raise ErrorActualizacion(f"No se pudo calcular SHA-256 de {ruta}: {exc}") from exc
    return h.hexdigest()


def _fechas_aplicadas(ficha) -> set[str]:
    if not ficha:
        return set()
    revisiones = ficha.get("revisiones") or []
    if not isinstance(revisiones, list):
        raise ErrorActualizacion("La clave 'revisiones' de la ficha no es una lista.")
    fechas = set()
    for revision in revisiones:
        if not isinstance(revision, dict):
            raise ErrorActualizacion("Una revisión de la ficha no es un objeto.")
        fecha = revision.get("fecha")
        if isinstance(fecha, str) and fecha:
            fechas.add(fecha)
    return fechas


def _nombres_de_alta(ficha) -> set[str]:
    """Nombres HTML declarados explícitamente como origen de la ficha.

    Una hoja de alta no es una revisión pendiente. Solo se reconoce cuando la
    ficha conserva el nombre literal; no se deduce por antigüedad.
    """
    if not ficha:
        return set()
    textos = []
    for ruta in (
        ("estructura", "_meta", "origen"),
        ("identidad", "_meta", "origen"),
    ):
        valor = ficha
        for clave in ruta:
            valor = valor.get(clave) if isinstance(valor, dict) else None
        if isinstance(valor, str):
            textos.append(valor)
    nombres = set()
    for texto in textos:
        for encontrado in re.findall(
            r"((?:REVISION|REVISON)[^/\\\r\n;]*?\.html)", texto, flags=re.I
        ):
            nombre = encontrado.strip(" '" + '"')
            if nombre:
                nombres.add(nombre.casefold())
    return nombres


# «_garaje.html», o «_garaje (1).html» cuando el navegador renombra una descarga repetida.
_ES_HOJA_GARAJE = re.compile(r"_garaje(?:\s*\(\d+\))?\.html$", flags=re.I)


def detectar_hojas(
    carpeta_revisiones,
    ficha_obra,
    ficha_garajes,
    *,
    forzar_fecha: str | None = None,
    incluir_vivienda: bool = True,
    incluir_garaje: bool = True,
) -> DeteccionHojas:
    """Detecta HTML pendientes por fecha y SHA, separados por tipo."""
    carpeta = Path(carpeta_revisiones)
    resultado = DeteccionHojas()
    if not carpeta.is_dir():
        return resultado

    fechas = {
        "vivienda": _fechas_aplicadas(ficha_obra),
        "garaje": _fechas_aplicadas(ficha_garajes),
    }
    altas = _nombres_de_alta(ficha_obra)
    hojas = []
    for ruta in carpeta.iterdir():
        if not ruta.is_file() or ruta.suffix.casefold() != ".html":
            continue
        orden, fecha = _fecha_desde_nombre(ruta.name)
        if not orden or not fecha:
            continue
        tipo = "garaje" if _ES_HOJA_GARAJE.search(ruta.name) else "vivienda"
        if tipo == "vivienda" and not incluir_vivienda:
            continue
        if tipo == "garaje" and not incluir_garaje:
            continue
        hojas.append(Hoja(ruta, fecha, orden, tipo, _sha256(ruta)))
    hojas.sort(key=lambda h: (h.orden, h.ruta.name.casefold()))

    referencias: dict[str, dict[str, Hoja]] = {"vivienda": {}, "garaje": {}}
    candidatas: list[Hoja] = []
    for hoja in hojas:
        es_alta = hoja.tipo == "vivienda" and hoja.ruta.name.casefold() in altas
        if es_alta:
            resultado.hojas_de_alta.append(hoja)
            referencias[hoja.tipo].setdefault(hoja.sha256, hoja)
            continue
        coincide_forzada = forzar_fecha is not None and hoja.fecha == forzar_fecha
        if hoja.fecha in fechas[hoja.tipo] and not coincide_forzada:
            resultado.ya_aplicadas.append(hoja)
            referencias[hoja.tipo].setdefault(hoja.sha256, hoja)
            continue
        if forzar_fecha is not None and not coincide_forzada:
            continue
        candidatas.append(hoja)

    vistas_forzadas: dict[str, Hoja] = {}
    for hoja in candidatas:
        referencia = referencias[hoja.tipo].get(hoja.sha256)
        if referencia is not None and forzar_fecha is None:
            resultado.copias_identicas.append((hoja, referencia))
            continue
        if forzar_fecha is not None and hoja.sha256 in vistas_forzadas:
            resultado.copias_identicas.append((hoja, vistas_forzadas[hoja.sha256]))
            continue
        vistas_forzadas[hoja.sha256] = hoja
        getattr(resultado, hoja.tipo).append(hoja)
    return resultado


def _sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    ).casefold()


def _extraer_seccion(salida: str, marcador: str) -> str:
    lineas = salida.splitlines()
    inicio = next((i for i, linea in enumerate(lineas) if marcador in linea), None)
    if inicio is None:
        return ""
    fin = inicio + 1
    while fin < len(lineas):
        linea = lineas[fin]
        if linea.strip() and not linea.startswith((" ", "\t")):
            break
        fin += 1
    return "\n".join(lineas[inicio:fin]).rstrip()


def _transiciones(salida: str) -> list[tuple[str, str, int]]:
    patron = re.compile(r"^\s+(.+?)\s+->\s+(.+?):\s+(\d+)\s*$", re.MULTILINE)
    transiciones = []
    for antes_txt, despues_txt, numero in patron.findall(salida):
        try:
            antes = ast.literal_eval(antes_txt)
            despues = ast.literal_eval(despues_txt)
        except (SyntaxError, ValueError):
            continue
        if isinstance(antes, str) and isinstance(despues, str):
            transiciones.append((antes, despues, int(numero)))
    return transiciones


def analizar_salida_simulacion(
    salida: str,
    *,
    aceptar_estructura: bool = False,
    aceptar_hoja_grande: Iterable[int] = (),
) -> AnalisisSimulacion:
    """Parsea el contrato visible del CLI y aplica todas sus guardas."""
    resumen = re.search(
        r"celdas impresas con marca:\s*(\d+)\s+cambios:\s*(\d+)", salida
    )
    blancos = re.search(
        r"casillas en blanco\s*->\s*tajo no empezado\s*\(P\):\s*(\d+)",
        salida,
        flags=re.I,
    )
    tiene_hoja = re.search(r"^HOJA:\s*", salida, flags=re.MULTILINE) is not None
    tiene_por_valor = re.search(r"^\s*por valor:\s*", salida, flags=re.MULTILINE) is not None
    marcas = int(resumen.group(1)) if resumen else None
    cambios = int(resumen.group(2)) if resumen else None
    blancos_a_p = int(blancos.group(1)) if blancos else None
    guardas: list[Guarda] = []
    aceptadas = []

    cambios_medidos = (
        max(cambios - blancos_a_p, 0)
        if cambios is not None and blancos_a_p is not None
        else None
    )
    hoja_grande_aceptada = None

    estructuras = (
        (
            "estructura_nueva",
            "ESTRUCTURA NUEVA EN LA HOJA",
            "La hoja incorpora estructura nueva.",
        ),
        (
            "estructura_retirada",
            "ESTRUCTURA QUE YA NO ESTA EN LA HOJA",
            "La hoja retira estructura existente.",
        ),
    )
    for codigo, marcador, motivo in estructuras:
        if marcador in salida:
            if aceptar_estructura:
                aceptadas.append(codigo)
            else:
                guardas.append(Guarda(codigo, motivo, _extraer_seccion(salida, marcador)))

    if "[MARCA SIN APLICAR]" in salida:
        guardas.append(
            Guarda(
                "marca_sin_aplicar",
                "Hay una marca de la hoja que el motor no sabe aplicar.",
                _extraer_seccion(salida, "[MARCA SIN APLICAR]"),
            )
        )
    if "[ABORTADO]" in salida:
        guardas.append(
            Guarda(
                "abortado",
                "El CLI de revisión abortó la operación.",
                _extraer_seccion(salida, "[ABORTADO]"),
            )
        )
    for linea in salida.splitlines():
        normalizada = _sin_acentos(linea)
        if "[aviso]" in normalizada and "sin resolver" in normalizada:
            guardas.append(
                Guarda(
                    "sin_resolver",
                    "El CLI declara claves sin resolver.",
                    linea.rstrip(),
                )
            )
            break

    if not (resumen and blancos and tiene_hoja and tiene_por_valor):
        guardas.append(
            Guarda(
                "formato_cambiado",
                "La salida no contiene el resumen esperado del CLI; el formato pudo cambiar.",
                salida.rstrip(),
            )
        )
    elif cambios_medidos is not None and marcas is not None:
        proporcion = (
            cambios_medidos / marcas
            if marcas > 0
            else (float("inf") if cambios_medidos > 0 else 0.0)
        )
        if (
            cambios_medidos > UMBRAL_CAMBIOS_MEDIDOS
            or proporcion > UMBRAL_PROPORCION_MARCAS
        ):
            if cambios_medidos in set(aceptar_hoja_grande):
                hoja_grande_aceptada = cambios_medidos
            else:
                porcentaje = (
                    "infinito"
                    if proporcion == float("inf")
                    else f"{proporcion * 100:.1f}%"
                )
                motivo = (
                    f"Hoja anormal: {cambios_medidos} cambios medidos ({porcentaje} "
                    f"de {marcas} celdas impresas con marca; las {blancos_a_p} casillas "
                    f"en blanco -> P no cuentan). Si la hoja es legítima, revisa las "
                    f"transiciones listadas y repite con --aceptar-hoja-grande {cambios_medidos}."
                )
                seccion_lineas = [resumen.group(0)]
                for antes, despues, numero in _transiciones(salida):
                    seccion_lineas.append(f"    {antes!r} -> {despues!r}: {numero}")
                seccion = "\n".join(seccion_lineas)
                guardas.append(Guarda("hoja_anormal", motivo, seccion))

    return AnalisisSimulacion(
        salida=salida,
        marcas=marcas,
        cambios=cambios,
        blancos_a_p=blancos_a_p,
        transiciones=_transiciones(salida),
        guardas=guardas,
        estructuras_aceptadas=aceptadas,
        cambios_medidos=cambios_medidos,
        hoja_grande_aceptada=hoja_grande_aceptada,
    )


def _lineas_hoja_grande(hoja: Hoja, analisis: AnalisisSimulacion) -> list[str]:
    if analisis.hoja_grande_aceptada is None:
        return []
    n = analisis.hoja_grande_aceptada
    lineas = [
        f"Hoja grande aceptada mediante --aceptar-hoja-grande {n}: {hoja.ruta.name}: "
        f"{n} cambios medidos sobre {analisis.marcas} marcas ({analisis.blancos_a_p} casillas en blanco -> P aparte). "
        "Transiciones antes -> después:"
    ]
    for antes, despues, numero in analisis.transiciones:
        lineas.append(f"  {antes!r} -> {despues!r}: {numero}")
    return lineas


def _salida_proceso(proceso: subprocess.CompletedProcess) -> str:
    partes = [proceso.stdout or "", proceso.stderr or ""]
    return "\n".join(p.rstrip("\r\n") for p in partes if p).strip() + (
        "\n" if any(partes) else ""
    )


def _ejecutar(comando: list[str], *, cwd: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            comando,
            cwd=os.fspath(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise ErrorActualizacion(f"No se pudo ejecutar {' '.join(comando)}: {exc}") from exc


def simular_vivienda(
    hoja,
    obra_id: str,
    fecha: str,
    *,
    aceptar_estructura: bool = False,
    aceptar_hoja_grande: Iterable[int] = (),
) -> AnalisisSimulacion:
    ruta = Path(hoja)
    if not ruta.is_file():
        raise ErrorActualizacion(f"No existe la hoja de vivienda: {ruta}")
    comando = PYTHON + [
        os.fspath(MOTOR_IA_DIR / "leer_hoja_marcada.py"),
        os.fspath(ruta),
        obra_id,
        "--digital",
        "--fecha",
        fecha,
    ]
    proceso = _ejecutar(comando, cwd=MOTOR_IA_DIR)
    analisis = analizar_salida_simulacion(
        _salida_proceso(proceso),
        aceptar_estructura=aceptar_estructura,
        aceptar_hoja_grande=aceptar_hoja_grande,
    )
    analisis.returncode = proceso.returncode
    if proceso.returncode != 0 and not analisis.guardas:
        raise ErrorActualizacion(
            f"La simulación de {ruta.name} terminó con código {proceso.returncode}:\n"
            f"{analisis.salida}"
        )
    return analisis


def _aplicar_vivienda(
    hoja: Hoja,
    obra_id: str,
    *,
    aceptar_estructura: bool,
    reemplazar: bool,
    aceptar_hoja_grande: Iterable[int] = (),
) -> tuple[AnalisisSimulacion, str]:
    comando = PYTHON + [
        os.fspath(MOTOR_IA_DIR / "leer_hoja_marcada.py"),
        os.fspath(hoja.ruta),
        obra_id,
        "--digital",
        "--fecha",
        hoja.fecha,
        "--escribir",
    ]
    if reemplazar:
        comando.append("--reemplazar")
    proceso = _ejecutar(comando, cwd=MOTOR_IA_DIR)
    salida = _salida_proceso(proceso)
    analisis = analizar_salida_simulacion(
        salida,
        aceptar_estructura=aceptar_estructura,
        aceptar_hoja_grande=aceptar_hoja_grande,
    )
    analisis.returncode = proceso.returncode
    if analisis.guardas:
        raise RequiereRevisionHumana(analisis)
    if proceso.returncode != 0:
        raise ErrorActualizacion(
            f"La escritura de {hoja.ruta.name} terminó con código "
            f"{proceso.returncode}:\n{salida}"
        )
    return analisis, salida


def _resumen_compacto(hoja: Hoja, analisis: AnalisisSimulacion) -> str:
    transiciones = ", ".join(
        f"{antes or 'blanco'}->{despues}:{numero}"
        for antes, despues, numero in analisis.transiciones
    ) or "ninguna"
    return (
        f"SIMULACION VIVIENDA {hoja.ruta.name}: marcas={analisis.marcas}; "
        f"cambios={analisis.cambios}; blancos->P={analisis.blancos_a_p}; "
        f"transiciones={transiciones}"
    )


ORDEN_ESTADOS = {"N": 0, "?": 1, "P": 2, "/": 3, "M": 4, "X": 5}
ESTADOS_AVANCE = {"X", "M", "/"}


def calcular_retrocesos(antes, despues) -> Retrocesos:
    estados_antes = (antes or {}).get("estados") or {}
    estados_despues = (despues or {}).get("estados") or {}
    resultado = Retrocesos()
    for clave in sorted(estados_antes):
        dato_antes = estados_antes[clave] or {}
        valor_antes = dato_antes.get("v")
        fecha = dato_antes.get("f")
        if clave not in estados_despues:
            resultado.retiradas.append(
                CambioEstado(clave, valor_antes, "<RETIRADA>", fecha)
            )
            continue
        valor_despues = (estados_despues[clave] or {}).get("v")
        if valor_despues == "N" and valor_antes != "N":
            resultado.a_n.append(CambioEstado(clave, valor_antes, "N", fecha))
        if (
            valor_antes in ESTADOS_AVANCE
            and valor_despues in ORDEN_ESTADOS
            and ORDEN_ESTADOS[valor_despues] < ORDEN_ESTADOS[valor_antes]
        ):
            resultado.bajadas.append(
                CambioEstado(clave, valor_antes, valor_despues, fecha)
            )
    return resultado


INICIO_TARJETA = re.compile(r'(?=<a class="obra" |<div class="obra disabled")')
FILA_IGNORADA = re.compile(
    r'<div class="row">\s*<span>\s*(?:Actualizado|[UÚ]ltimo archivo)\s*</span>'
    r'\s*<span>.*?</span>\s*</div>',
    flags=re.I | re.DOTALL,
)


def _tarjetas_por_nombre(html_indice: str) -> dict[str, str]:
    marca_grid = '<div class="grid" id="grid">'
    if marca_grid in html_indice and '<p class="footer"' in html_indice:
        inicio = html_indice.index(marca_grid) + len(marca_grid)
        inicio_footer = html_indice.index('<p class="footer"', inicio)
        try:
            fin = html_indice.rindex("</div>", inicio, inicio_footer)
        except ValueError as exc:
            raise ErrorActualizacion(
                "El formato del índice cambió: no se pudo cerrar la rejilla."
            ) from exc
        contenido = html_indice[inicio:fin]
    else:
        contenido = html_indice
    comienzos = [m.start() for m in INICIO_TARJETA.finditer(contenido)]
    if not comienzos:
        raise ErrorActualizacion(
            "El formato del índice cambió: no se encontraron tarjetas de obra."
        )
    trozos = [
        contenido[inicio:fin]
        for inicio, fin in zip(comienzos, comienzos[1:] + [len(contenido)])
    ]
    resultado = {}
    for trozo in trozos:
        nombre_m = re.search(r"<h2>(.*?)</h2>", trozo, flags=re.DOTALL)
        if not nombre_m:
            raise ErrorActualizacion(
                "El formato del índice cambió: una tarjeta no contiene <h2>."
            )
        nombre = re.sub(r"<[^>]+>", "", nombre_m.group(1)).strip()
        if nombre in resultado:
            raise ErrorActualizacion(f"El índice contiene dos tarjetas para {nombre!r}.")
        resultado[nombre] = trozo
    return resultado


def _normalizar_tarjeta(tarjeta: str) -> str:
    tarjeta = FILA_IGNORADA.sub("", tarjeta)
    tarjeta = re.sub(
        r"Actualizado(?:\s+el)?\s*:?\s*[^<\r\n]*",
        "Actualizado <IGNORADO>",
        tarjeta,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", tarjeta).strip()


def comparar_tarjetas_indice(
    antes: str, despues: str, nombre_objetivo: str
) -> ComparacionTarjetas:
    tarjetas_antes = _tarjetas_por_nombre(antes)
    tarjetas_despues = _tarjetas_por_nombre(despues)
    nombres_antes = set(tarjetas_antes)
    nombres_despues = set(tarjetas_despues)
    faltantes = sorted(nombres_antes ^ nombres_despues)
    cambiadas = []
    objetivo_cambio = False
    for nombre in sorted(nombres_antes & nombres_despues):
        cambio = _normalizar_tarjeta(tarjetas_antes[nombre]) != _normalizar_tarjeta(
            tarjetas_despues[nombre]
        )
        if nombre == nombre_objetivo:
            objetivo_cambio = cambio
        elif cambio:
            cambiadas.append(nombre)
    return ComparacionTarjetas(cambiadas, objetivo_cambio, faltantes)


def sha_fichas_otras_obras(obras, obra_id: str, obras_dir) -> dict[str, str]:
    raiz = Path(obras_dir)
    resultado = {}
    for obra in obras:
        otro_id = obra.get("id")
        if otro_id == obra_id:
            continue
        if not isinstance(otro_id, str) or not isinstance(obra.get("carpeta_obra"), str):
            raise ErrorActualizacion("El registro contiene una obra sin id o carpeta_obra.")
        ruta = raiz / obra["carpeta_obra"] / "INFORME SAGARDE IA" / "ficha_obra.json"
        resultado[otro_id] = _sha256(ruta) if ruta.is_file() else FICHA_AUSENTE
    return resultado


def comparar_sha_otras(antes: dict[str, str], despues: dict[str, str]) -> ComparacionSha:
    claves_antes = set(antes)
    claves_despues = set(despues)
    faltantes = sorted(claves_antes ^ claves_despues)
    cambiadas = sorted(
        clave
        for clave in claves_antes & claves_despues
        if antes[clave] != despues[clave]
    )
    return ComparacionSha(cambiadas, faltantes)


def resumir_fichas(ficha_obra, ficha_garajes=None) -> ResumenFicha:
    conteo = Counter({estado: 0 for estado in ("X", "M", "/", "P", "?", "N")})
    for ficha in (ficha_obra, ficha_garajes):
        if not ficha:
            continue
        for clave, dato in ((ficha.get("estados") or {}).items()):
            valor = dato.get("v") if isinstance(dato, dict) else None
            if valor not in conteo:
                raise ErrorActualizacion(
                    f"Estado desconocido {valor!r} en la celda {clave!r}."
                )
            conteo[valor] += 1
    medidos = conteo["X"] + conteo["M"] + conteo["/"] + conteo["P"]
    estricto = round(conteo["X"] / medidos * 100, 1) if medidos else 0.0
    ponderado = (
        round(
            (conteo["X"] + 0.60 * conteo["M"] + 0.25 * conteo["/"])
            / medidos
            * 100,
            1,
        )
        if medidos
        else 0.0
    )
    return ResumenFicha(
        estados=dict(conteo),
        pct_estricto=estricto,
        pct_ponderado=ponderado,
        revisiones_vivienda=len((ficha_obra or {}).get("revisiones") or []),
        revisiones_garaje=len((ficha_garajes or {}).get("revisiones") or []),
    )


def _ultima_fecha(ficha_obra, ficha_garajes) -> str:
    fechas = []
    for ficha in (ficha_obra, ficha_garajes):
        for revision in (ficha or {}).get("revisiones") or []:
            fecha = revision.get("fecha") if isinstance(revision, dict) else None
            if not fecha:
                continue
            try:
                clave = datetime.strptime(fecha, "%d/%m/%Y")
            except ValueError as exc:
                raise ErrorActualizacion(f"Fecha de revisión inválida: {fecha!r}") from exc
            fechas.append((clave, fecha))
    if not fechas:
        raise ErrorActualizacion("La obra no tiene una fecha de revisión para verificar el PDF.")
    return max(fechas)[1]


def _numero_portales(ficha) -> int:
    return sum(
        len(bloque.get("portales") or [])
        for bloque in ((ficha.get("estructura") or {}).get("bloques") or [])
        if isinstance(bloque, dict)
    )


def _garaje_tiene_zonas(ficha_garajes) -> bool:
    for garaje in ((ficha_garajes or {}).get("estructura") or {}).get("garajes") or []:
        for planta in garaje.get("plantas") or []:
            if planta.get("zonas"):
                return True
    return False


def _tiene_zesp(ficha) -> bool:
    return any("zesp" in clave.split("__") for clave in (ficha.get("estados") or {}))


def verificar_pdf(carpeta_obra: Path, ficha_obra, ficha_garajes) -> VerificacionPdf:
    informe_dir = carpeta_obra / "INFORME SAGARDE IA"
    pdfs = sorted(informe_dir.glob("INFORME_EJECUTIVO_*.pdf"))
    errores = []
    avisos = []
    if len(pdfs) != 1:
        errores.append(
            f"Se esperaba exactamente un PDF ejecutivo y se encontraron {len(pdfs)}."
        )
        return VerificacionPdf(None, None, None, None, [], errores, avisos)
    fecha = _ultima_fecha(ficha_obra, ficha_garajes)
    portales = _numero_portales(ficha_obra)
    esperadas = 1 + (portales if portales >= 2 else 0)
    if _garaje_tiene_zonas(ficha_garajes):
        esperadas += 1
    if _tiene_zesp(ficha_obra):
        esperadas += 1
    try:
        import fitz

        documento = fitz.open(os.fspath(pdfs[0]))
        try:
            paginas = len(documento)
            fechas = []
            patron = re.compile(r"Datos\s*:\s*(\d{2}/\d{2}/\d{4})", re.I)
            for numero, pagina in enumerate(documento, start=1):
                encontrado = patron.search(pagina.get_text("text"))
                fecha_pagina = encontrado.group(1) if encontrado else None
                fechas.append(fecha_pagina)
                if fecha_pagina != fecha:
                    errores.append(
                        f"PDF página {numero}: Datos={fecha_pagina!r}, esperado {fecha!r}."
                    )
        finally:
            documento.close()
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        errores.append(f"No se pudo verificar el PDF con PyMuPDF: {exc}")
        return VerificacionPdf(pdfs[0], None, esperadas, fecha, [], errores, avisos)
    if paginas != esperadas:
        avisos.append(f"Páginas PDF: {paginas}; esperadas por estructura: {esperadas}.")
    return VerificacionPdf(pdfs[0], paginas, esperadas, fecha, fechas, errores, avisos)


def _copiar_fichas_temporales(carpeta_obra: Path, destino: Path) -> list[Path]:
    try:
        comun = os.path.commonpath([os.fspath(RAIZ), os.fspath(destino.resolve())])
    except ValueError:
        comun = ""
    if os.path.normcase(comun) == os.path.normcase(os.fspath(RAIZ)):
        raise ErrorActualizacion(
            f"La copia temporal debe quedar fuera del repositorio: {destino}"
        )
    copiadas = []
    for nombre in ("ficha_obra.json", "ficha_garajes.json"):
        origen = _ruta_ficha(carpeta_obra, nombre)
        if origen.is_file():
            destino_ficha = destino / nombre
            shutil.copy2(origen, destino_ficha)
            copiadas.append(destino_ficha)
    if not copiadas:
        raise ErrorActualizacion("No existe ninguna ficha que respaldar antes de escribir.")
    return copiadas


def _aplicar_garaje(hoja: Hoja, obra_id: str) -> str:
    if not hoja.ruta.is_file():
        raise ErrorActualizacion(f"No existe la hoja de garaje: {hoja.ruta}")
    comando = PYTHON + [
        os.fspath(MOTOR_IA_DIR / "adaptar_revision_garaje.py"),
        os.fspath(hoja.ruta),
        obra_id,
        "--fecha",
        hoja.fecha,
    ]
    proceso = _ejecutar(comando, cwd=MOTOR_IA_DIR)
    salida = _salida_proceso(proceso)
    if proceso.returncode != 0:
        raise ErrorActualizacion(
            f"El adaptador de garaje terminó con código {proceso.returncode}:\n{salida}"
        )
    return salida


def _ejecutar_regeneracion(obra_id: str) -> tuple[str, int]:
    comando = PYTHON + [os.fspath(SCRIPT_DIR / "regenerar_obra.py"), obra_id]
    salidas = []
    for intento in (1, 2):
        proceso = _ejecutar(comando, cwd=RAIZ)
        salida = _salida_proceso(proceso)
        salidas.append(salida)
        valida = bool(salida.strip()) and re.search(r"^\s*KPIs:", salida, re.MULTILINE)
        if proceso.returncode == 0 and valida:
            return salida, intento
        if intento == 1 and not valida:
            print("[AVISO] La captura de regenerar_obra llegó vacía o sin KPIs; se repite una vez.")
            continue
        if proceso.returncode != 0:
            raise ErrorActualizacion(
                f"regenerar_obra.py terminó con código {proceso.returncode}:\n{salida}"
            )
        raise ErrorActualizacion(
            "regenerar_obra.py no imprimió la línea 'KPIs:' tras dos intentos.\n"
            + "\n--- intento ---\n".join(salidas)
        )
    raise AssertionError("bucle de regeneración inalcanzable")


def _ejecutar_finalizar(obra: dict) -> str:
    comando = PYTHON + [os.fspath(SCRIPT_DIR / "regenerar_obra.py"), "--finalizar"]
    proceso = _ejecutar(comando, cwd=RAIZ)
    salida = _salida_proceso(proceso)
    if proceso.returncode != 0:
        raise ErrorActualizacion(
            f"regenerar_obra.py --finalizar terminó con código {proceso.returncode}:\n{salida}"
        )
    if not salida.strip():
        raise ErrorActualizacion("regenerar_obra.py --finalizar no produjo salida verificable.")
    linea = next(
        (l for l in salida.splitlines() if l.startswith("Tarjetas actualizadas:")), None
    )
    if linea is None or obra["nombre"] not in linea:
        raise ErrorActualizacion(
            "--finalizar no confirmó que la tarjeta actualizada fuera la obra objetivo:\n"
            + salida
        )
    return salida


def _formatear_resumen(etiqueta: str, resumen: ResumenFicha) -> str:
    e = resumen.estados
    return (
        f"{etiqueta}: X={e['X']} M={e['M']} /={e['/']} P={e['P']} "
        f"?={e['?']} N={e['N']} | estricto={resumen.pct_estricto:.1f}% "
        f"ponderado={resumen.pct_ponderado:.1f}% | revisiones="
        f"{resumen.revisiones_vivienda} vivienda + "
        f"{resumen.revisiones_garaje} garaje"
    )


def _prefijar_retrocesos(retro: Retrocesos, prefijo: str) -> Retrocesos:
    def prefijar(items):
        return [
            CambioEstado(f"{prefijo}:{i.clave}", i.de, i.a, i.fecha_anterior)
            for i in items
        ]

    return Retrocesos(
        bajadas=prefijar(retro.bajadas),
        retiradas=prefijar(retro.retiradas),
        a_n=prefijar(retro.a_n),
    )


def _unir_retrocesos(*retros: Retrocesos) -> Retrocesos:
    return Retrocesos(
        bajadas=[i for r in retros for i in r.bajadas],
        retiradas=[i for r in retros for i in r.retiradas],
        a_n=[i for r in retros for i in r.a_n],
    )


def _lineas_retrocesos(retro: Retrocesos) -> list[str]:
    # Informativo, no una pregunta: la ultima revision manda (norma de Bixente,
    # reiterada el 15/10/2026) y estas marcas ya estan aplicadas.
    lineas = [
        "E) AVISO informativo: la hoja baja o quita avance (ya aplicado; "
        "la ultima revision manda)"
    ]
    if not (retro.bajadas or retro.retiradas or retro.a_n):
        lineas.append("  Ninguno.")
        return lineas
    lineas.append("  Bajadas de avance:")
    if retro.bajadas:
        for cambio in retro.bajadas:
            lineas.append(
                f"    {cambio.clave}: {cambio.de} -> {cambio.a}; "
                f"fecha anterior={cambio.fecha_anterior}"
            )
    else:
        lineas.append("    Ninguna.")
    lineas.append("  Celdas retiradas:")
    if retro.retiradas:
        for cambio in retro.retiradas:
            lineas.append(
                f"    {cambio.clave}: {cambio.de} -> {cambio.a}; "
                f"fecha anterior={cambio.fecha_anterior}"
            )
    else:
        lineas.append("    Ninguna.")
    lineas.append("  Celdas que pasan a N:")
    if retro.a_n:
        for cambio in retro.a_n:
            lineas.append(
                f"    {cambio.clave}: {cambio.de} -> N; "
                f"fecha anterior={cambio.fecha_anterior}"
            )
    else:
        lineas.append("    Ninguna.")
    return lineas


def _guardar_informe(obra_id: str, lineas: Iterable[str], instante: datetime) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ruta = LOGS_DIR / f"actualizacion_{obra_id}_{instante:%Y%m%d_%H%M}.txt"
    texto = "\n".join(lineas).rstrip() + "\n"
    try:
        ruta.write_text(texto, encoding="utf-8")
    except OSError as exc:
        raise ErrorActualizacion(f"No se pudo guardar el informe {ruta}: {exc}") from exc
    return ruta


def _mostrar_guardas(analisis: AnalisisSimulacion) -> None:
    print("REVISION HUMANA OBLIGATORIA")
    for guarda in analisis.guardas:
        print(f"- {guarda.motivo}")
        if guarda.seccion:
            print(guarda.seccion)


def _obra_por_id(obra_id: str) -> dict:
    obra = next((o for o in OBRAS if o.get("id") == obra_id), None)
    if obra is None:
        disponibles = ", ".join(o["id"] for o in OBRAS)
        raise ErrorActualizacion(
            f"La obra {obra_id!r} no está registrada. Disponibles: {disponibles}"
        )
    return obra


def _validar_fecha(texto: str | None) -> str | None:
    if texto is None:
        return None
    try:
        fecha = datetime.strptime(texto, "%d/%m/%Y")
    except ValueError as exc:
        raise ErrorActualizacion(
            f"--forzar-fecha exige una fecha real DD/MM/AAAA: {texto!r}"
        ) from exc
    return fecha.strftime("%d/%m/%Y")


def _imprimir_ignoradas(deteccion: DeteccionHojas) -> None:
    for hoja in deteccion.hojas_de_alta:
        print(f"IGNORADA hoja de alta ya consumida: {hoja.ruta.name}")
    for copia, referencia in deteccion.copias_identicas:
        print(
            f"IGNORADA copia idéntica por SHA-256: {copia.ruta.name} "
            f"= {referencia.ruta.name} ({copia.sha256})"
        )


def _detectar_actual(obra: dict, forzar_fecha, incluir_vivienda, incluir_garaje):
    carpeta_obra = OBRAS_DIR / obra["carpeta_obra"]
    ficha_obra = _leer_json(
        _ruta_ficha(carpeta_obra, "ficha_obra.json"), obligatorio=False
    )
    ficha_garajes = _leer_json(
        _ruta_ficha(carpeta_obra, "ficha_garajes.json"), obligatorio=False
    )
    deteccion = detectar_hojas(
        carpeta_obra / "REVISIONES",
        ficha_obra,
        ficha_garajes,
        forzar_fecha=forzar_fecha,
        incluir_vivienda=incluir_vivienda,
        incluir_garaje=incluir_garaje,
    )
    return carpeta_obra, ficha_obra, ficha_garajes, deteccion


def _simular(
    obra: dict,
    deteccion: DeteccionHojas,
    *,
    aceptar_estructura: bool,
    aceptar_hoja_grande: Iterable[int] = (),
) -> int:
    if deteccion.vivienda:
        primera = deteccion.vivienda[0]
        analisis = simular_vivienda(
            primera.ruta,
            obra["id"],
            primera.fecha,
            aceptar_estructura=aceptar_estructura,
            aceptar_hoja_grande=aceptar_hoja_grande,
        )
        print(_resumen_compacto(primera, analisis))
        for linea in _lineas_hoja_grande(primera, analisis):
            print(linea)
        if len(deteccion.vivienda) > 1:
            print(
                f"AVISO: quedan {len(deteccion.vivienda) - 1} hoja(s) de vivienda "
                "posteriores; la simulación solo muestra la primera porque la siguiente "
                "depende de que esta se escriba."
            )
        if analisis.guardas:
            _mostrar_guardas(analisis)
            return 3
    if deteccion.garaje:
        primera = deteccion.garaje[0]
        if not primera.ruta.is_file():
            raise ErrorActualizacion(f"No existe la hoja de garaje: {primera.ruta}")
        print(
            f"SIMULACION GARAJE {primera.ruta.name}: existe; fecha "
            f"{primera.fecha} no aplicada. El adaptador no se ejecuta porque escribe."
        )
        if len(deteccion.garaje) > 1:
            print(
                f"AVISO: quedan {len(deteccion.garaje) - 1} hoja(s) de garaje "
                "posteriores; se procesarán una por una al escribir."
            )
    print("[SIMULACION] no se ha escrito nada.")
    return 0


def _informe_fallo(
    obra: dict,
    inicio: float,
    instante: datetime,
    motivo: str,
    fases: dict[str, float],
    lineas_previas: list[str],
) -> Path:
    lineas = list(lineas_previas)
    lineas.extend(
        [
            "",
            "F) TIEMPOS",
            *[f"  {nombre}: {segundos:.2f} s" for nombre, segundos in fases.items()],
            f"  total: {time.perf_counter() - inicio:.2f} s",
            "",
            f"G) REVISAR: {motivo}",
            MENSAJE_PUBLICACION,
        ]
    )
    ruta = _guardar_informe(obra["id"], lineas, instante)
    print("\n".join(lineas[:-1]))
    print(f"Informe guardado: {ruta}")
    print(MENSAJE_PUBLICACION)
    return ruta


def _escribir(obra: dict, args, deteccion_inicial: DeteccionHojas) -> int:
    inicio = time.perf_counter()
    instante = datetime.now()
    fases: dict[str, float] = {}
    lineas: list[str] = [
        f"INFORME DE VERIFICACION — {obra['nombre']} ({obra['id']})",
        f"Generado: {instante:%d/%m/%Y %H:%M:%S}",
    ]
    carpeta_obra = OBRAS_DIR / obra["carpeta_obra"]
    ficha_obra_antes = _leer_json(_ruta_ficha(carpeta_obra, "ficha_obra.json"))
    ficha_garaje_antes = _leer_json(
        _ruta_ficha(carpeta_obra, "ficha_garajes.json"), obligatorio=False
    )
    resumen_antes = resumir_fichas(ficha_obra_antes, ficha_garaje_antes)

    t = time.perf_counter()
    sha_antes = sha_fichas_otras_obras(OBRAS, obra["id"], OBRAS_DIR)
    if not INDEX_PATH.is_file():
        raise ErrorActualizacion(f"No existe el índice global: {INDEX_PATH}")
    index_antes = INDEX_PATH.read_text(encoding="utf-8")
    fases["captura previa"] = time.perf_counter() - t

    lineas.extend(["", "A) ESTADO ANTES/DESPUES", _formatear_resumen("ANTES", resumen_antes)])
    t = time.perf_counter()
    aplicadas_vivienda = []
    aplicadas_garaje = []
    aceptadas = []
    with tempfile.TemporaryDirectory(prefix=f"sagarde_actualizar_{obra['id']}_") as tmp:
        copias = _copiar_fichas_temporales(carpeta_obra, Path(tmp))
        copias_por_nombre = {copia.name: copia for copia in copias}
        ficha_obra_antes = _leer_json(copias_por_nombre["ficha_obra.json"])
        ficha_garaje_antes = (
            _leer_json(copias_por_nombre["ficha_garajes.json"])
            if "ficha_garajes.json" in copias_por_nombre
            else None
        )
        lineas.append(
            "Backups temporales fuera del repositorio: "
            + ", ".join(p.name for p in copias)
        )
        fases["backup"] = time.perf_counter() - t

        try:
            t = time.perf_counter()
            hashes_aplicados = set()
            for hoja in deteccion_inicial.vivienda:
                ficha_actual = _leer_json(_ruta_ficha(carpeta_obra, "ficha_obra.json"))
                if (
                    args.forzar_fecha is None
                    and hoja.fecha in _fechas_aplicadas(ficha_actual)
                ):
                    lineas.append(
                        f"Vivienda omitida tras aplicar una anterior: {hoja.ruta.name}; "
                        f"la fecha {hoja.fecha} ya figura en revisiones."
                    )
                    continue
                if hoja.sha256 in hashes_aplicados:
                    lineas.append(
                        f"Vivienda omitida por SHA idéntico a la anterior: {hoja.ruta.name}."
                    )
                    continue
                analisis = simular_vivienda(
                    hoja.ruta,
                    obra["id"],
                    hoja.fecha,
                    aceptar_estructura=args.aceptar_estructura,
                    aceptar_hoja_grande=args.aceptar_hoja_grande,
                )
                print(_resumen_compacto(hoja, analisis))
                if analisis.guardas:
                    raise RequiereRevisionHumana(analisis)
                aceptadas.extend(analisis.estructuras_aceptadas)
                analisis_aplicada, _salida_cli = _aplicar_vivienda(
                    hoja,
                    obra["id"],
                    aceptar_estructura=args.aceptar_estructura,
                    reemplazar=args.forzar_fecha is not None,
                    aceptar_hoja_grande=args.aceptar_hoja_grande,
                )
                lineas.extend(_lineas_hoja_grande(hoja, analisis_aplicada))
                comprobacion = simular_vivienda(
                    hoja.ruta,
                    obra["id"],
                    hoja.fecha,
                    aceptar_estructura=True,
                )
                if comprobacion.guardas:
                    raise RequiereRevisionHumana(comprobacion)
                if comprobacion.cambios != 0:
                    raise ErrorActualizacion(
                        f"La simulación posterior de {hoja.ruta.name} da "
                        f"cambios={comprobacion.cambios}, no 0."
                    )
                aplicadas_vivienda.append(hoja)
                hashes_aplicados.add(hoja.sha256)
                lineas.append(
                    f"Vivienda aplicada y re-simulada con cambios=0: {hoja.ruta.name}."
                )
            fases["vivienda"] = time.perf_counter() - t

            t = time.perf_counter()
            for hoja in deteccion_inicial.garaje:
                ficha_actual = _leer_json(
                    _ruta_ficha(carpeta_obra, "ficha_garajes.json"), obligatorio=False
                )
                if (
                    args.forzar_fecha is None
                    and hoja.fecha in _fechas_aplicadas(ficha_actual)
                ):
                    lineas.append(
                        f"Garaje omitido tras aplicar uno anterior: {hoja.ruta.name}; "
                        f"la fecha {hoja.fecha} ya figura en revisiones."
                    )
                    continue
                _aplicar_garaje(hoja, obra["id"])
                ficha_actual = _leer_json(
                    _ruta_ficha(carpeta_obra, "ficha_garajes.json")
                )
                revisiones = ficha_actual.get("revisiones") or []
                ultima = revisiones[-1].get("fecha") if revisiones else None
                if ultima != hoja.fecha:
                    raise ErrorActualizacion(
                        f"El garaje no dejó {hoja.fecha} como última revisión; "
                        f"quedó {ultima!r}."
                    )
                aplicadas_garaje.append(hoja)
                lineas.append(f"Garaje aplicado una vez y fecha comprobada: {hoja.ruta.name}.")
            fases["garaje"] = time.perf_counter() - t

            if not aplicadas_vivienda and not aplicadas_garaje:
                raise ErrorActualizacion(
                    "La detección encontró pendientes, pero ninguna hoja llegó a aplicarse."
                )

            t = time.perf_counter()
            _salida_regen, intentos = _ejecutar_regeneracion(obra["id"])
            lineas.append(f"Regeneración acotada confirmada por KPIs ({intentos} intento(s)).")
            _ejecutar_finalizar(obra)
            lineas.append("--finalizar confirmó exactamente la tarjeta de la obra objetivo.")
            fases["regeneración y finalizar"] = time.perf_counter() - t
        except RequiereRevisionHumana as exc:
            _mostrar_guardas(exc.analisis)
            motivo = "; ".join(g.motivo for g in exc.analisis.guardas)
            lineas.append("REVISION HUMANA: " + motivo)
            for guarda in exc.analisis.guardas:
                if guarda.seccion:
                    lineas.append(guarda.seccion)
            _informe_fallo(obra, inicio, instante, motivo, fases, lineas)
            return 3
        except Exception as exc:
            motivo = str(exc)
            _informe_fallo(obra, inicio, instante, motivo, fases, lineas)
            return 2

    t = time.perf_counter()
    motivos_revisar = []
    ficha_obra_despues = _leer_json(_ruta_ficha(carpeta_obra, "ficha_obra.json"))
    ficha_garaje_despues = _leer_json(
        _ruta_ficha(carpeta_obra, "ficha_garajes.json"), obligatorio=False
    )
    resumen_despues = resumir_fichas(ficha_obra_despues, ficha_garaje_despues)
    lineas.append(_formatear_resumen("DESPUES", resumen_despues))

    sha_despues = sha_fichas_otras_obras(OBRAS, obra["id"], OBRAS_DIR)
    comparacion_sha = comparar_sha_otras(sha_antes, sha_despues)
    lineas.extend(["", "B) SHA-256 DE LAS DEMAS OBRAS"])
    for obra_id in sorted(sha_antes):
        estado = "IDENTICO" if sha_antes[obra_id] == sha_despues.get(obra_id) else "CAMBIO"
        lineas.append(
            f"  {obra_id}: {sha_antes[obra_id]} -> {sha_despues.get(obra_id)} [{estado}]"
        )
    if comparacion_sha.cambiadas or comparacion_sha.faltantes:
        afectadas = comparacion_sha.cambiadas + comparacion_sha.faltantes
        motivo = "ERROR (efecto colateral) en ficha(s): " + ", ".join(afectadas)
        motivos_revisar.append(motivo)
        print(f"{ROJO}{motivo}{RESET}")

    pdf = verificar_pdf(carpeta_obra, ficha_obra_despues, ficha_garaje_despues)
    lineas.extend(["", "C) PDF EJECUTIVO"])
    lineas.append(f"  ruta: {pdf.ruta}")
    lineas.append(f"  páginas: {pdf.paginas}; esperadas: {pdf.paginas_esperadas}")
    lineas.append(f"  fecha esperada en cada página: {pdf.fecha_esperada}")
    lineas.append(f"  fechas leídas: {pdf.fechas_por_pagina}")
    for error in pdf.errores:
        lineas.append("  ERROR: " + error)
        motivos_revisar.append(error)
    for aviso in pdf.avisos:
        lineas.append("  AVISO: " + aviso)
        motivos_revisar.append(aviso)

    index_despues = INDEX_PATH.read_text(encoding="utf-8")
    tarjetas = comparar_tarjetas_indice(index_antes, index_despues, obra["nombre"])
    lineas.extend(["", "D) TARJETAS DEL INDICE"])
    lineas.append(f"  tarjeta objetivo cambió: {'SI' if tarjetas.objetivo_cambio else 'NO'}")
    lineas.append(
        "  tarjetas ajenas cambiadas: "
        + (", ".join(tarjetas.cambiadas_ajenas) or "ninguna")
    )
    if tarjetas.cambiadas_ajenas or tarjetas.faltantes:
        afectadas = tarjetas.cambiadas_ajenas + tarjetas.faltantes
        motivo = "ERROR: cambiaron tarjetas ajenas: " + ", ".join(afectadas)
        motivos_revisar.append(motivo)
        print(f"{ROJO}{motivo}{RESET}")

    retro_v = _prefijar_retrocesos(
        calcular_retrocesos(ficha_obra_antes, ficha_obra_despues), "vivienda"
    )
    retro_g = _prefijar_retrocesos(
        calcular_retrocesos(ficha_garaje_antes or {}, ficha_garaje_despues or {}),
        "garaje",
    )
    retro = _unir_retrocesos(retro_v, retro_g)
    # Las bajadas, retiradas y pasos a N se listan arriba como aviso; NO entran
    # en motivos_revisar: una marca explicita de la ultima hoja vale a la
    # primera y no deja el informe en REVISAR ni la salida en 2.
    lineas.extend([""] + _lineas_retrocesos(retro))
    if aceptadas:
        lineas.append(
            "Estructura aceptada mediante --aceptar-estructura: "
            + ", ".join(sorted(set(aceptadas)))
        )
    fases["verificación"] = time.perf_counter() - t
    lineas.extend(["", "F) TIEMPOS"])
    for nombre, segundos in fases.items():
        lineas.append(f"  {nombre}: {segundos:.2f} s")
    lineas.append(f"  total: {time.perf_counter() - inicio:.2f} s")
    lineas.extend(["", "G) " + ("OK" if not motivos_revisar else "REVISAR")])
    if motivos_revisar:
        for motivo in motivos_revisar:
            lineas.append("  - " + motivo)
    lineas.append(MENSAJE_PUBLICACION)
    try:
        ruta_informe = _guardar_informe(obra["id"], lineas, instante)
    except Exception as exc:
        print(f"ERROR: {exc}")
        print(MENSAJE_PUBLICACION)
        return 2
    print("\n".join(lineas[:-1]))
    print(f"Informe guardado: {ruta_informe}")
    print(MENSAJE_PUBLICACION)
    return 0 if not motivos_revisar else 2


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id_obra")
    parser.add_argument("--escribir", action="store_true")
    parser.add_argument("--aceptar-estructura", action="store_true")
    parser.add_argument(
        "--aceptar-hoja-grande",
        type=int,
        action="append",
        default=[],
        metavar="N",
        help=(
            "Acepta una hoja marcada como anormal SOLO si su número de "
            "cambios medidos coincide con N, tras revisar la lista de "
            "transiciones antes -> después (se puede repetir)."
        ),
    )
    parser.add_argument("--forzar-fecha", metavar="DD/MM/AAAA")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--solo-vivienda", action="store_true")
    grupo.add_argument("--solo-garaje", action="store_true")
    return parser


def main(argv=None) -> int:
    _configurar_stdout_utf8()
    args = construir_parser().parse_args(argv)
    try:
        args.forzar_fecha = _validar_fecha(args.forzar_fecha)
        obra = _obra_por_id(args.id_obra)
        incluir_vivienda = not args.solo_garaje
        incluir_garaje = not args.solo_vivienda
        carpeta_obra, _ficha, _ficha_g, deteccion = _detectar_actual(
            obra, args.forzar_fecha, incluir_vivienda, incluir_garaje
        )
        if not carpeta_obra.is_dir():
            raise ErrorActualizacion(f"No existe la carpeta de obra: {carpeta_obra}")
        _imprimir_ignoradas(deteccion)
        if not deteccion.vivienda and not deteccion.garaje:
            if args.forzar_fecha:
                raise ErrorActualizacion(
                    f"No hay ninguna hoja seleccionable con fecha {args.forzar_fecha}."
                )
            print(f"{obra['nombre']}: NO hay hojas nuevas.")
            print(MENSAJE_PUBLICACION)
            return 0
        if not args.escribir:
            codigo = _simular(
                obra,
                deteccion,
                aceptar_estructura=args.aceptar_estructura,
                aceptar_hoja_grande=args.aceptar_hoja_grande,
            )
            print(MENSAJE_PUBLICACION)
            return codigo
        return _escribir(obra, args, deteccion)
    except RequiereRevisionHumana as exc:
        _mostrar_guardas(exc.analisis)
        print(MENSAJE_PUBLICACION)
        return 3
    except Exception as exc:
        print(f"ERROR: {exc}")
        print(MENSAJE_PUBLICACION)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
