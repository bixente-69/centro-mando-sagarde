# -*- coding: utf-8 -*-
"""Cache persistente de extracciones crudas y deterministas de PDF."""
import atexit
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import tempfile


VERSION_CACHE = 1
CARPETA_CACHE_PDF = Path(__file__).resolve().parent / "_cache_pdf"
VARIABLE_SIN_CACHE = "SAGARDE_SIN_CACHE_PDF"

_leidos_de_cache = 0
_extraidos = 0
_cache_usada = False
_resumen_impreso = False
_avisos_emitidos = set()


def _sha256_fichero(ruta):
    digest = hashlib.sha256()
    with open(ruta, "rb") as fichero:
        for bloque in iter(lambda: fichero.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _version_distribucion(nombre, modulo):
    try:
        return importlib.metadata.version(nombre)
    except importlib.metadata.PackageNotFoundError:
        return str(getattr(modulo, "__version__", "desconocida"))


def huella_codigo_extraccion(extractor):
    """SHA-256 del codigo fuente exacto que produce la extraccion cruda."""
    try:
        fuente = inspect.getsource(extractor).encode("utf-8")
    except (OSError, TypeError):
        codigo = getattr(extractor, "__code__", None)
        if codigo is None:
            raise RuntimeError("no se puede obtener el codigo fuente del extractor PDF")
        fuente = codigo.co_code
    return hashlib.sha256(fuente).hexdigest()


def _metadatos_clave(ruta_pdf, extractor, pdfplumber, pdfminer):
    return {
        "sha256_pdf": _sha256_fichero(ruta_pdf),
        "version_pdfplumber": _version_distribucion("pdfplumber", pdfplumber),
        "version_pdfminer_six": _version_distribucion("pdfminer.six", pdfminer),
        "sha256_codigo_extraccion": huella_codigo_extraccion(extractor),
    }


def _clave_cache(metadatos):
    serializado = json.dumps(
        metadatos, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serializado).hexdigest()


def _datos_validos(datos):
    if not isinstance(datos, dict) or set(datos) != {"paginas"}:
        return False
    paginas = datos["paginas"]
    if not isinstance(paginas, list):
        return False
    for pagina in paginas:
        if not isinstance(pagina, dict):
            return False
        if set(pagina) != {"tabla", "n_anotaciones"}:
            return False
        if not isinstance(pagina["n_anotaciones"], int) or pagina["n_anotaciones"] < 0:
            return False
        tabla = pagina["tabla"]
        if tabla is None:
            continue
        if not isinstance(tabla, list):
            return False
        for fila in tabla:
            if not isinstance(fila, list):
                return False
            if any(celda is not None and not isinstance(celda, str) for celda in fila):
                return False
    return True


def _avisar_una_vez(ruta_cache, mensaje):
    firma = str(ruta_cache)
    if firma in _avisos_emitidos:
        return
    _avisos_emitidos.add(firma)
    print("  AVISO: {} Se vuelve a extraer el PDF.".format(mensaje))


def _leer_cache(ruta_cache, clave, metadatos):
    try:
        with open(ruta_cache, "r", encoding="utf-8") as fichero:
            contenido = json.load(fichero)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _avisar_una_vez(
            ruta_cache,
            "cache PDF corrupta '{}': {}.".format(ruta_cache.name, type(exc).__name__),
        )
        return None

    if not isinstance(contenido, dict) or contenido.get("version_cache") != VERSION_CACHE:
        _avisar_una_vez(
            ruta_cache,
            "version de cache PDF no valida en '{}'.".format(ruta_cache.name),
        )
        return None
    if contenido.get("clave") != clave or contenido.get("metadatos") != metadatos:
        _avisar_una_vez(
            ruta_cache,
            "metadatos de cache PDF no validos en '{}'.".format(ruta_cache.name),
        )
        return None
    datos = contenido.get("datos")
    if not _datos_validos(datos):
        _avisar_una_vez(
            ruta_cache,
            "cache PDF corrupta '{}' (estructura no valida).".format(ruta_cache.name),
        )
        return None
    return datos


def _escribir_cache_atomica(ruta_cache, contenido):
    ruta_cache.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(ruta_cache.parent),
            prefix=".{}-".format(ruta_cache.stem),
            suffix=".tmp",
            delete=False,
        ) as fichero:
            temporal = Path(fichero.name)
            json.dump(
                contenido,
                fichero,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            fichero.flush()
            os.fsync(fichero.fileno())
        os.replace(temporal, ruta_cache)
    finally:
        if temporal is not None and temporal.exists():
            try:
                temporal.unlink()
            except OSError:
                pass


def extraer_con_cache(ruta_pdf, extractor, pdfplumber, pdfminer):
    """Ejecuta ``extractor`` o devuelve su estructura cruda desde JSON."""
    global _cache_usada, _extraidos, _leidos_de_cache
    _cache_usada = True

    if os.environ.get(VARIABLE_SIN_CACHE) == "1":
        _extraidos += 1
        return extractor(ruta_pdf)

    metadatos = _metadatos_clave(ruta_pdf, extractor, pdfplumber, pdfminer)
    clave = _clave_cache(metadatos)
    ruta_cache = Path(CARPETA_CACHE_PDF) / "{}.json".format(clave)

    if ruta_cache.is_file():
        datos = _leer_cache(ruta_cache, clave, metadatos)
        if datos is not None:
            _leidos_de_cache += 1
            return datos

    datos = extractor(ruta_pdf)
    _extraidos += 1
    contenido = {
        "version_cache": VERSION_CACHE,
        "clave": clave,
        "metadatos": metadatos,
        "datos": datos,
    }
    try:
        _escribir_cache_atomica(ruta_cache, contenido)
    except (OSError, TypeError, ValueError) as exc:
        _avisar_una_vez(
            ruta_cache,
            "no se pudo escribir la cache PDF '{}': {}.".format(
                ruta_cache.name, type(exc).__name__
            ),
        )
    return datos


def imprimir_resumen():
    """Imprime una sola linea por proceso si se intento extraer algun PDF."""
    global _resumen_impreso
    if not _cache_usada or _resumen_impreso:
        return
    _resumen_impreso = True
    print("cache PDF: {} leidos de cache, {} extraidos".format(
        _leidos_de_cache, _extraidos
    ))


def _reiniciar_estado_para_pruebas():
    global _cache_usada, _extraidos, _leidos_de_cache, _resumen_impreso
    _cache_usada = False
    _extraidos = 0
    _leidos_de_cache = 0
    _resumen_impreso = False
    _avisos_emitidos.clear()


atexit.register(imprimir_resumen)
