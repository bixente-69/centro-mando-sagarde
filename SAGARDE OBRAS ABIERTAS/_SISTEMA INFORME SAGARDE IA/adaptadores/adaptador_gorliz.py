# -*- coding: utf-8 -*-
"""
ADAPTADOR - 2026 GORLIZ HOSPITAL
--------------------------------
Lee revisiones JSON de la obra y devuelve el historial normalizado que
consumen motor_informes.py, priorizador_trabajos.py y panel_obra.py.

La documentacion disponible de Gorliz es de proyecto/licitacion y no contiene
una tabla real de seguimiento. Por ese motivo este adaptador NO deduce avance
desde planos, mediciones o fechas de fichero: solo incorpora revisiones
explicitas guardadas como:

    INFORME SAGARDE IA/revision_gorliz_DDMMAAAA.json

Admite dos formatos de JSON.

1. Registros explicitos (recomendado para la estructura hospitalaria):

    {
      "fecha": "24/07/2026",
      "registros": [
        {
          "edificio": "Hospital de Gorliz",
          "planta": "Planta 1",
          "unidad": "Unidad de hospitalizacion 1",
          "tajo": "Tubeado",
          "estado": "M"
        }
      ]
    }

   Tambien se aceptan los nombres ingleses que usa internamente el motor:
   building, floor, unit, task y status.

2. Mapa de celdas compatible con las revisiones generadas por SAGARDE:

    {
      "fecha": "24/07/2026",
      "estructura": {
        "edificios": {"hospital": "Hospital de Gorliz"},
        "plantas": {"p1": "Planta 1"},
        "unidades": {"uh1": "Unidad de hospitalizacion 1"},
        "tajos": {"tube-viv": "Tubeado"}
      },
      "estados": {
        "hospital__p1__tube-viv__uh1": "M"
      }
    }

Estados validos: "X", "M", "/", "" y "N". Los registros "N" se excluyen
porque el motor actual no representa "no aplica" en sus KPI.
"""

import json
import os
import re
from datetime import datetime


CARPETA_OBRA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "2026 GORLIZ HOSPITAL",
)
CARPETA_IA = os.path.join(CARPETA_OBRA, "INFORME SAGARDE IA")

PREFIJO_REVISION = "revision_gorliz_"
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


def cargar_historial(carpeta_ia=CARPETA_IA):
    """
    Devuelve [(fecha, registros), ...], ordenado de antiguo a nuevo.

    No crea una revision inicial ficticia. Si la carpeta o los JSON no existen,
    devuelve una lista vacia y explica el formato que falta.
    """
    if not os.path.isdir(carpeta_ia):
        print(
            "[adaptador_gorliz] AVISO: no existe '{}'. "
            "La obra aun no tiene seguimiento de avance.".format(carpeta_ia)
        )
        return []

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
            "Hay dos revisiones de Gorliz con la misma fecha; deje una sola por dia"
        )

    if not archivos:
        print(
            "[adaptador_gorliz] AVISO: no hay revisiones. "
            "Se espera revision_gorliz_DDMMAAAA.json en '{}'.".format(carpeta_ia)
        )
        return []

    historial = []
    for _, fecha, nombre in archivos:
        ruta = os.path.join(carpeta_ia, nombre)
        registros = _parsear_json(ruta, fecha)
        if not registros:
            print(
                "  [gorliz] {}: sin registros aplicables en '{}', ignorado.".format(
                    fecha, nombre
                )
            )
            continue
        historial.append((fecha, registros))
        print(
            "  [gorliz] {}: {} registros de '{}'".format(
                fecha, len(registros), nombre
            )
        )
    return historial


def plantilla():
    """Plantilla ilustrativa: los textos entre <...> deben confirmarse en obra."""
    return {
        "fecha": "DD/MM/AAAA",
        "registros": [
            {
                "edificio": "Hospital de Gorliz",
                "planta": "<PLANTA_REAL>",
                "unidad": "<UNIDAD_O_ZONA_REAL>",
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
