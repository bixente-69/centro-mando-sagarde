# -*- coding: utf-8 -*-
"""
ADAPTADOR - 2026 OLABEAGA BILBAO
---------------------------------
Lee revisiones JSON de la obra y devuelve el historial normalizado que
consumen motor_informes.py, priorizador_trabajos.py y panel_obra.py.

Olabeaga es una promocion de 30 viviendas con garajes y trasteros (proyecto
de ejecucion "makia", mayo 2024). A fecha de alta (24/09/2026) la obra esta
en fase de garajes; las viviendas todavia no han arrancado. La documentacion
disponible (planos de garaje en CAD sin texto extraible, informe de puesta a
tierra) no contiene una tabla real de seguimiento ni una numeracion de
plazas de garaje, y el generador de hojas de revision (generador_revisiones.
html) todavia no tiene su ampliacion para garajes (pendiente, fuera de este
adaptador). Por ese motivo este adaptador sigue el mismo patron que
adaptador_gorliz.py: NO deduce avance desde planos, mediciones o fechas de
fichero, solo incorpora revisiones explicitas guardadas como:

    INFORME SAGARDE IA/revision_olabeaga_DDMMAAAA.json

Cuando exista la ampliacion del generador para garajes y/o arranque la fase
de viviendas con su propia hoja en blanco, esta obra puede darse de alta de
forma nativa con alta_obra_desde_hoja.py (igual que Gernika/Bolueta/Mungia);
este adaptador deja de usarse en ese momento, sin perder las revisiones ya
registradas aqui (quedan en el historial que alimenta la ficha nueva).

Admite dos formatos de JSON.

1. Registros explicitos (recomendado mientras no haya rejilla fija: un
   registro por zona/tajo comprobado, sin necesidad de enumerar plazas):

    {
      "fecha": "24/09/2026",
      "registros": [
        {
          "edificio": "Garaje",
          "planta": "Garaje -2",
          "unidad": "Zona general",
          "tajo": "Tubeado de zonas comunes",
          "estado": "M"
        }
      ]
    }

   Tambien se aceptan los nombres ingleses que usa internamente el motor:
   building, floor, unit, task y status.

2. Mapa de celdas compatible con las revisiones generadas por SAGARDE:

    {
      "fecha": "24/09/2026",
      "estructura": {
        "edificios": {"garaje": "Garaje"},
        "plantas": {"g2": "Garaje -2"},
        "unidades": {"zg": "Zona general"},
        "tajos": {"tub-zzcc": "Tubeado de zonas comunes"}
      },
      "estados": {
        "garaje__g2__tub-zzcc__zg": "M"
      }
    }

Estados validos: "X", "M", "/", "" y "N". Los registros "N" se excluyen
porque el motor actual no representa "no aplica" en sus KPI.
"""

import json
import os
import re
import sys
from datetime import datetime

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)
import adaptar_revision_html  # noqa: E402
import ficha_obra as _fichas  # noqa: E402
import validar_revision as _vr  # noqa: E402

CARPETA_OBRA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "2026 OLABEAGA BILBAO",
)
CARPETA_IA = os.path.join(CARPETA_OBRA, "INFORME SAGARDE IA")
CARPETA_REVISIONES = os.path.join(CARPETA_OBRA, "REVISIONES")

PREFIJO_REVISION = "revision_olabeaga_"
ESTADOS_VALIDOS = {"", "/", "M", "X", "N"}
PATRON_FECHA = re.compile(r"(\d{2})(\d{2})(\d{4})")


def _fecha_desde_nombre(nombre):
    """Devuelve (AAAAMMDD, DD/MM/AAAA) o (None, None)."""
    coincidencia = PATRON_FECHA.search(nombre)
    if not coincidencia:
        return None, None

    dia, mes, anio = coincidencia.groups()
    try:
        fecha = datetime(int(anio), int(mes), int(dia))
    except ValueError:
        return None, None
    return fecha.strftime("%Y%m%d"), fecha.strftime("%d/%m/%Y")


def _fecha_valida(valor):
    if not isinstance(valor, str):
        return None
    try:
        return datetime.strptime(valor.strip(), "%d/%m/%Y").strftime("%d/%m/%Y")
    except ValueError:
        return None


def _texto(registro, *claves):
    for clave in claves:
        valor = registro.get(clave)
        if valor is not None:
            texto = str(valor).strip()
            if texto:
                return texto
    return ""


def _normalizar_estado(valor, contexto):
    if valor is None:
        estado = ""
    else:
        estado = str(valor).strip().upper()
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(
            "{}: estado {!r} no valido; use X, M, /, vacio o N".format(
                contexto, valor
            )
        )
    return estado


def _normalizar_registro(registro, contexto):
    if not isinstance(registro, dict):
        raise ValueError("{}: el registro debe ser un objeto JSON".format(contexto))

    task = _texto(registro, "task", "tajo")
    floor = _texto(registro, "floor", "planta")
    building = _texto(registro, "building", "edificio")
    unit = _texto(registro, "unit", "unidad")
    status = _normalizar_estado(
        registro.get("status", registro.get("estado")), contexto
    )

    faltan = [
        nombre
        for nombre, valor in (
            ("tajo/task", task),
            ("planta/floor", floor),
            ("edificio/building", building),
            ("unidad/unit", unit),
        )
        if not valor
    ]
    if faltan:
        raise ValueError(
            "{}: faltan campos obligatorios: {}".format(contexto, ", ".join(faltan))
        )

    if status == "N":
        return None
    return {
        "task": task,
        "floor": floor,
        "building": building,
        "unit": unit,
        "status": status,
    }


def _mapa(estructura, nombre):
    valor = estructura.get(nombre, {})
    if valor is None:
        return {}
    if not isinstance(valor, dict):
        raise ValueError("estructura.{} debe ser un objeto JSON".format(nombre))
    return {str(clave): str(etiqueta).strip() for clave, etiqueta in valor.items()}


def _registros_desde_celdas(data, origen):
    estados = data.get("estados")
    if not isinstance(estados, dict):
        raise ValueError("{}: 'estados' debe ser un objeto JSON".format(origen))

    estructura = data.get("estructura", {})
    if not isinstance(estructura, dict):
        raise ValueError("{}: 'estructura' debe ser un objeto JSON".format(origen))

    edificios = _mapa(estructura, "edificios")
    plantas = _mapa(estructura, "plantas")
    unidades = _mapa(estructura, "unidades")
    tajos = _mapa(estructura, "tajos")

    registros = []
    for clave, estado in estados.items():
        partes = str(clave).split("__")
        contexto = "{} [{}]".format(origen, clave)
        if len(partes) != 4 or any(not parte.strip() for parte in partes):
            raise ValueError(
                "{}: clave invalida; se espera edificio__planta__tajo__unidad".format(
                    contexto
                )
            )
        edificio_id, planta_id, tajo_id, unidad_id = partes
        registro = _normalizar_registro(
            {
                "building": edificios.get(edificio_id, edificio_id),
                "floor": plantas.get(planta_id, planta_id),
                "task": tajos.get(tajo_id, tajo_id),
                "unit": unidades.get(unidad_id, unidad_id),
                "status": estado,
            },
            contexto,
        )
        if registro is not None:
            registros.append(registro)
    return registros


def _registros_explicitos(data, origen):
    entrada = data.get("registros")
    if not isinstance(entrada, list):
        raise ValueError("{}: 'registros' debe ser una lista JSON".format(origen))

    registros = []
    for indice, registro_crudo in enumerate(entrada, start=1):
        registro = _normalizar_registro(
            registro_crudo, "{} [registro {}]".format(origen, indice)
        )
        if registro is not None:
            registros.append(registro)
    return registros


def _validar_duplicados(registros, origen):
    vistos = set()
    for registro in registros:
        clave = (
            registro["building"],
            registro["floor"],
            registro["unit"],
            registro["task"],
        )
        if clave in vistos:
            raise ValueError(
                "{}: registro duplicado para edificio/planta/unidad/tajo {}".format(
                    origen, " / ".join(clave)
                )
            )
        vistos.add(clave)


def _parsear_datos(data, fecha_archivo, origen="<datos>"):
    """Normaliza un documento JSON ya cargado; se mantiene separada para pruebas."""
    if not isinstance(data, dict):
        raise ValueError("{}: la raiz debe ser un objeto JSON".format(origen))

    fecha_json = _fecha_valida(data.get("fecha"))
    if fecha_json is None:
        raise ValueError(
            "{}: falta 'fecha' valida con formato DD/MM/AAAA".format(origen)
        )
    if fecha_json != fecha_archivo:
        raise ValueError(
            "{}: la fecha interna {} no coincide con la del nombre {}".format(
                origen, fecha_json, fecha_archivo
            )
        )

    tiene_registros = "registros" in data
    tiene_estados = "estados" in data
    if tiene_registros == tiene_estados:
        raise ValueError(
            "{}: incluya exactamente uno de estos campos: 'registros' o 'estados'".format(
                origen
            )
        )

    if tiene_registros:
        registros = _registros_explicitos(data, origen)
    else:
        registros = _registros_desde_celdas(data, origen)
    _validar_duplicados(registros, origen)
    return registros


def _parsear_json(ruta, fecha_archivo):
    try:
        with open(ruta, encoding="utf-8") as fichero:
            data = json.load(fichero)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "{}: JSON invalido en linea {}, columna {}".format(
                ruta, exc.lineno, exc.colno
            )
        ) from exc
    return _parsear_datos(data, fecha_archivo, ruta)


def _cargar_historial_html():
    """Hoja de tajos en HTML exportada por la propia app de generacion de
    tajos, si esta obra llega a recibirla (carpeta REVISIONES). Delega en el
    lector generico (adaptar_revision_html), que traduce portal/planta/tajo
    directamente desde ficha_obra.json y el catalogo compartido — Olabeaga no
    mantiene aqui ninguna tabla propia de ids HTML. Mientras no exista
    REVISIONES ni ficha_obra.json, se ignora sin romper el resto (nunca se
    inventa un historial)."""
    try:
        ficha_actual = _fichas.cargar(CARPETA_OBRA)
    except Exception as e:
        print("  [adaptador_olabeaga] AVISO: no se pudo cargar ficha_obra.json "
              "para traducir HTML ({}); se ignoran los HTML de esta carpeta.".format(e))
        return []
    try:
        catalogo = _vr.cargar_catalogo_tajos()
    except Exception as e:
        print("  [adaptador_olabeaga] AVISO: no se pudo cargar CATALOGO_TAJOS.json "
              "({}); se ignoran los HTML de esta carpeta.".format(e))
        return []

    return adaptar_revision_html.cargar_historial_html_generico(
        'olabeaga', CARPETA_REVISIONES, ficha_actual, catalogo,
        contiene='OLABEAGA', nombre_log='adaptador_olabeaga',
    )


def cargar_historial(carpeta_ia=CARPETA_IA):
    """
    Devuelve [(fecha, registros), ...], ordenado de antiguo a nuevo.

    No crea una revision inicial ficticia. Si la carpeta o los JSON no existen,
    devuelve una lista vacia y explica el formato que falta.
    """
    combinado = {}

    if not os.path.isdir(carpeta_ia):
        print(
            "[adaptador_olabeaga] AVISO: no existe '{}'. "
            "La obra aun no tiene seguimiento de avance.".format(carpeta_ia)
        )
    else:
        archivos = []
        for nombre in os.listdir(carpeta_ia):
            nombre_minusculas = nombre.lower()
            if not (
                nombre_minusculas.startswith(PREFIJO_REVISION)
                and nombre_minusculas.endswith(".json")
            ):
                continue
            clave, fecha = _fecha_desde_nombre(nombre)
            if clave is None:
                raise ValueError(
                    "Nombre de revision sin fecha DDMMAAAA valida: {}".format(nombre)
                )
            archivos.append((clave, fecha, nombre))
        archivos.sort()

        fechas = [clave for clave, _, _ in archivos]
        if len(fechas) != len(set(fechas)):
            raise ValueError(
                "Hay dos revisiones de Olabeaga con la misma fecha; deje una sola por dia"
            )

        if not archivos:
            print(
                "[adaptador_olabeaga] AVISO: no hay revisiones JSON. "
                "Se espera revision_olabeaga_DDMMAAAA.json en '{}'.".format(carpeta_ia)
            )

        for clave, fecha, nombre in archivos:
            ruta = os.path.join(carpeta_ia, nombre)
            registros = _parsear_json(ruta, fecha)
            if not registros:
                print(
                    "  [olabeaga] {}: sin registros aplicables en '{}', ignorado.".format(
                        fecha, nombre
                    )
                )
                continue
            combinado[clave] = (fecha, registros)
            print(
                "  [olabeaga] {}: {} registros de '{}'".format(
                    fecha, len(registros), nombre
                )
            )

    historial_html = []
    for display, registros in _cargar_historial_html():
        m = re.search(r'(\d{2})/(\d{2})/(\d{4})', display)
        clave = m.group(3) + m.group(2) + m.group(1)
        historial_html.append((clave, display, registros))
    if historial_html:
        print("  [adaptador_olabeaga] {} revision(es) en formato HTML encontradas.".format(
            len(historial_html)))
    for clave, display, registros in historial_html:
        combinado[clave] = (display, registros)

    return [combinado[clave] for clave in sorted(combinado)]


def plantilla():
    """Plantilla ilustrativa: los textos entre <...> deben confirmarse en obra."""
    return {
        "fecha": "DD/MM/AAAA",
        "registros": [
            {
                "edificio": "Garaje",
                "planta": "<PLANTA_REAL>",
                "unidad": "<ZONA_REAL>",
                "tajo": "<NOMBRE_EXACTO_DEL_TAJO>",
                "estado": "",
            }
        ],
    }


if __name__ == "__main__":
    import sys

    if "--plantilla" in sys.argv:
        print(json.dumps(plantilla(), ensure_ascii=False, indent=2))
    else:
        historial = cargar_historial()
        print("\nRevisiones cargadas: {}".format(len(historial)))
        if historial:
            print(
                "Ultima: {} ({} registros)".format(
                    historial[-1][0], len(historial[-1][1])
                )
            )
        else:
            print(
                "No se genera avance: faltan revisiones reales de la obra. "
                "Ejecute con --plantilla para ver el formato esperado."
            )
