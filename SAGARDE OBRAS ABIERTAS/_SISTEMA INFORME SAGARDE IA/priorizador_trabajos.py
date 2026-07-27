# -*- coding: utf-8 -*-
"""Motor Sagarde v4: catálogo explícito, memoria histórica e inventario completo."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime


VERSION = "4.2"
# Unificado con SCORE de motor_informes.py (25/07/2026): mismo valor de "M"
# en los dos sitios. Si cambia aquí, cambiar también SCORE en motor_informes.py.
ESTADO_VALOR = {"": 0.0, "/": 0.25, "M": 0.60, "X": 1.0}
AMBITO_ORDEN = {"vivienda": 0, "zona_comun": 1, "edificio": 2}
AMBITO_NOMBRE = {
    "vivienda": "Viviendas",
    "zona_comun": "Zonas comunes",
    "edificio": "Edificio general",
}
SECCION_ORDEN = {
    "VIABLE": 0,
    "BLOQUEADO": 1,
    "OTROS_GREMIOS": 2,
    "DUDAS": 3,
    "TERMINADO": 4,
}
SECCION_NOMBRE = {
    "VIABLE": "Tajos viables",
    "BLOQUEADO": "Tajos bloqueados",
    "OTROS_GREMIOS": "Otros gremios e interferencias",
    "DUDAS": "Dudas pendientes",
    "TERMINADO": "Tajos terminados",
}
DISPLAY_NAMES = {"pintura": "Pintura", "techos": "Techos"}


def _normalizar(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto.casefold()).strip()


def _estado(valor):
    estado = str(valor or "").strip().upper()
    return estado if estado in ESTADO_VALOR else ""


def _fecha(valor):
    try:
        return datetime.strptime(str(valor), "%d/%m/%Y")
    except (TypeError, ValueError):
        return datetime.min


def _orden_natural(valor):
    partes = re.split(r"(\d+)", str(valor or ""))
    return tuple(int(p) if p.isdigit() else p.casefold() for p in partes)


def _scope(meta, original, unidad):
    ambito = meta.get("ambito", "vivienda")
    texto = _normalizar(f"{original} {unidad}")
    if "zona comun" in texto or "zzcc" in texto:
        return "zona_comun"
    if ambito == "dinamico":
        if any(x in texto for x in ("pasillo", "rellano", "escalera")):
            return "zona_comun"
        return "vivienda"
    return ambito if ambito in AMBITO_ORDEN else "vivienda"


class Catalogo:
    def __init__(self, obra=""):
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reglas", "CATALOGO_TAJOS.json")
        with open(ruta, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.version = self.data.get("version", "—")
        self.obra = obra
        self.config_obra = self.data.get("obras", {}).get(obra, {})
        self.errores = []

        self.tajos = {x["id"]: dict(x) for x in self.data.get("tajos", [])}
        comunes = list(self.data.get("tajos", []))
        especificos = list(self.config_obra.get("tajos", []))
        for tajo in especificos:
            self.tajos[tajo["id"]] = dict(tajo)

        self.aliases = {}
        for tajo in comunes:
            self._registrar_aliases(tajo, especifico=False)
        for tajo in especificos:
            self._registrar_aliases(tajo, especifico=True)

    def _registrar_aliases(self, tajo, especifico=False):
        for alias in tajo.get("aliases", []):
            clave = _normalizar(alias)
            anterior = self.aliases.get(clave)
            if anterior and anterior != tajo["id"] and not especifico:
                self.errores.append(f"Alias duplicado en catálogo: {alias}.")
                continue
            self.aliases[clave] = tajo["id"]

    def resolver(self, nombre):
        original = str(nombre or "").strip()
        task_id = self.aliases.get(_normalizar(original))
        if task_id:
            return task_id, self.tajos[task_id], False
        desconocido = "sin_clasificar:" + (_normalizar(original) or "sin_nombre")
        meta = {
            "id": desconocido,
            "nombre": original or "Tajo sin nombre",
            "aliases": [original] if original else [],
            "propiedad": "desconocido",
            "ambito": "vivienda",
            "orden": 9999,
            "fase": "Sin clasificar",
            "deps": [],
            "estado_m": "Sin definir",
            "estado_x": "Sin definir",
            "impacto": "Debe definirse antes de priorizar.",
        }
        return desconocido, meta, True

    def meta(self, task_id, fallback=None):
        return self.tajos.get(task_id, fallback or {})


def _pregunta(registro, codigo, texto, task_id=None, loc=None):
    clave = (codigo, task_id or "", texto)
    item = registro.setdefault(clave, {
        "codigo": codigo,
        "tarea_id": task_id,
        "pregunta": texto,
        "ubicaciones": set(),
    })
    if loc:
        item["ubicaciones"].add(loc)


def _construir_estado(historial, catalogo, preguntas):
    revisiones = sorted(historial or [], key=lambda x: _fecha(x[0]))
    if not revisiones:
        return {}, set(), None

    estados = {}
    ultima_fecha = revisiones[-1][0]
    vistos_ultima = set()

    # Algunas obras abren una fase nueva despues de tener una fase anterior
    # confirmada como entregada. Para el priorizador (solo para el), las
    # revisiones hasta esa fecha se consideran cerradas en X. El historial
    # original sigue intacto para KPIs y graficos.
    cierre_historico = catalogo.config_obra.get("forzar_historial_terminado_hasta")
    fecha_cierre = None
    if cierre_historico:
        try:
            fecha_cierre = _fecha(cierre_historico)
        except Exception:
            _pregunta(
                preguntas, "ERROR_CONFIG_OBRA",
                "Fecha forzar_historial_terminado_hasta no valida: {}.".format(cierre_historico),
            )

    for indice, (fecha, snapshot) in enumerate(revisiones):
        por_revision = {}
        fecha_revision = _fecha(fecha)
        for reg in snapshot:
            original = str(reg.get("task", "")).strip()
            task_id, meta, desconocido = catalogo.resolver(original)
            edificio = str(reg.get("building", "")).strip() or "—"
            planta = str(reg.get("floor", "")).strip() or "—"
            unidad = str(reg.get("unit", "")).strip() or "—"
            loc = (edificio, planta, unidad)
            key = (loc, task_id)
            nuevo = _estado(reg.get("status", ""))
            if fecha_cierre is not None and fecha_revision <= fecha_cierre:
                nuevo = "X"
            actual_rev = por_revision.get(key)
            if actual_rev is None:
                por_revision[key] = {
                    "estado": nuevo, "originales": {original}, "meta": meta,
                    "desconocido": desconocido, "loc": loc, "task_id": task_id,
                }
            else:
                actual_rev["originales"].add(original)
                if actual_rev["estado"] != nuevo:
                    _pregunta(
                        preguntas, "ESTADOS_DUPLICADOS",
                        f"El tajo {meta.get('nombre', original)} aparece dos veces con estados distintos en la revisión {fecha}. Confirmar el estado correcto.",
                        task_id, loc,
                    )
                    if ESTADO_VALOR[nuevo] < ESTADO_VALOR[actual_rev["estado"]]:
                        actual_rev["estado"] = nuevo

        for key, nuevo in por_revision.items():
            anterior = estados.get(key)
            if anterior is None:
                estados[key] = {
                    **nuevo, "primera_fecha": fecha, "ultima_fecha": fecha,
                    "conflicto": False, "forzado_entregado": False,
                }
            else:
                anterior["originales"].update(nuevo["originales"])
                anterior["ultima_fecha"] = fecha
                anterior["meta"] = nuevo["meta"]
                anterior["desconocido"] = nuevo["desconocido"]
                if anterior["estado"] == "X" and nuevo["estado"] != "X":
                    # NORMA DE OBRA: lo que se apunta en la ultima revision es
                    # lo que vale. Si el revisor escribe una marca explicita
                    # (M o /) sobre algo que figuraba terminado, es que ha ido
                    # y ha visto que faltaba algo. Se acepta a la primera: no
                    # es un retroceso, es una correccion.
                    if nuevo["estado"]:
                        anterior["estado"] = nuevo["estado"]
                        anterior["conflicto"] = False
                        anterior.pop("estado_conflictivo", None)
                        anterior.pop("conflicto_n", None)
                    elif anterior.get("conflicto"):
                        # Celda VACIA (sin marca). No es lo mismo que una marca:
                        # hoy no se puede distinguir "he ido y no esta hecho" de
                        # "el lector no supo leer la marca a boli" (488 celdas
                        # asi en la ultima hoja de Mungia). Se mantiene la
                        # cautela de 2 revisiones hasta que la ficha de obra
                        # separe 'P' (pendiente confirmado) de '?' (desconocido).
                        n = anterior.get("conflicto_n", 1) + 1
                        anterior["conflicto_n"] = n
                        anterior["estado_conflictivo"] = nuevo["estado"]
                        if n >= 2:
                            anterior["estado"] = nuevo["estado"]
                            anterior["conflicto"] = False
                            anterior.pop("estado_conflictivo", None)
                            anterior.pop("conflicto_n", None)
                    else:
                        # Primera vez que aparece vacia tras una X: pendiente de confirmar
                        anterior["conflicto"] = True
                        anterior["estado_conflictivo"] = nuevo["estado"]
                        anterior["conflicto_n"] = 1
                else:
                    anterior["estado"] = nuevo["estado"]
                    if nuevo["estado"] == "X":
                        anterior["conflicto"] = False
                        anterior.pop("estado_conflictivo", None)
                        anterior.pop("conflicto_n", None)

        if indice == len(revisiones) - 1:
            vistos_ultima = set(por_revision)

    for key, item in estados.items():
        item["omitido_ultima"] = key not in vistos_ultima

    return estados, vistos_ultima, ultima_fecha


def _aplicar_excepciones_obra(estados, catalogo, preguntas):
    config = catalogo.config_obra

    # Dos mecanismos INDEPENDIENTES que antes compartian una sola guarda:
    #
    # 1) forzar_historial_terminado (booleano): da por terminado TODO el
    #    historial de la obra. Las obras migradas al cierre por fecha
    #    (forzar_historial_terminado_hasta) lo tienen en false porque ese
    #    cierre ya se aplica revision a revision en _construir_estado; aqui
    #    NO deben pasar o se marcaria como X tambien la fase en curso.
    #
    # 2) excepciones: tajos que se inyectan aunque no aparezcan en ninguna
    #    hoja de revision. No dependen del punto 1: una obra puede declarar
    #    excepciones sin dar por terminado su historial. Compartir la guarda
    #    dejaba este bloque inalcanzable en cuanto la obra migraba al _hasta.
    if config.get("forzar_historial_terminado"):
        for item in estados.values():
            item["estado"] = "X"
            item["conflicto"] = False
            item["omitido_ultima"] = False
            item["forzado_entregado"] = True

    excepciones = config.get("excepciones", [])
    if not excepciones:
        return

    edificios_pb = [x["loc"][0] for x in estados.values() if x["loc"][1] == "PB"]
    edificio = edificios_pb[0] if edificios_pb else "Obispo Orueta 2"
    for excepcion in excepciones:
        if excepcion.get("tipo") != "pendiente_especial":
            continue
        planta = excepcion["planta"]
        for unidad in excepcion.get("unidades", []):
            loc = (edificio, planta, unidad)
            for task_id, especial in ((excepcion["bloqueo"], False), (excepcion["tajo"], True)):
                meta = catalogo.meta(task_id)
                estados[(loc, task_id)] = {
                    "estado": "", "originales": {meta.get("nombre", task_id)},
                    "meta": meta, "desconocido": False, "loc": loc,
                    "task_id": task_id, "primera_fecha": "Excepción confirmada",
                    "ultima_fecha": "Excepción confirmada", "conflicto": False,
                    "omitido_ultima": False, "forzado_entregado": False,
                    "especial_verificar": especial,
                }
        _pregunta(
            preguntas, "ALCANCE_POSTAPERTURA",
            "Cuando termine el tabique separador de cocinas, revisar los apartamentos 1 y 2 de PB antes de decidir si quedan tubeado, cableado, mecanismos u otros trabajos.",
            excepcion["tajo"], (edificio, planta, "Apartamentos 1 y 2"),
        )


def _buscar_dep(por_loc, dep_id):
    item = por_loc.get(dep_id)
    return item["estado"] if item else None


def _clasificar_detalle(estados, catalogo, ultima_fecha, preguntas):
    por_loc = defaultdict(dict)
    for item in estados.values():
        por_loc[item["loc"]][item["task_id"]] = item

    edad_dias = None
    try:
        edad_dias = (datetime.now().date() - _fecha(ultima_fecha).date()).days
    except Exception:
        pass
    caducada = edad_dias is None or edad_dias > 30
    ignorar_caducidad = bool(catalogo.config_obra.get("forzar_historial_terminado"))

    detalle = []
    for item in estados.values():
        meta = item["meta"]
        task_id = item["task_id"]
        loc = item["loc"]
        estado = item["estado"]
        propiedad = meta.get("propiedad", "desconocido")
        ambito = _scope(meta, " ".join(item["originales"]), loc[2])
        bloqueos = []
        cumplidas = []

        if item.get("conflicto"):
            categoria = "DUDAS"
            motivo = "Existe una corrección posterior a una X; se conserva X hasta verificar."
            _pregunta(
                preguntas, "NO_QUITAR_X",
                f"'{meta.get('nombre', task_id)}' figuraba como terminado pero la siguiente revisión lo corrige a {item.get('estado_conflictivo') or 'pendiente'}. Ir a comprobar en obra si realmente está terminado.",
                task_id, loc,
            )
        elif estado == "X":
            categoria = "TERMINADO"
            motivo = "Terminado según la última confirmación válida."
        elif propiedad in ("externo", "coordinacion"):
            categoria = "OTROS_GREMIOS"
            motivo = meta.get("impacto", "Condición de otro gremio.")
        elif propiedad == "desconocido" or item.get("desconocido"):
            categoria = "DUDAS"
            motivo = "Nombre no reconocido; no se prioriza hasta definirlo."
            _pregunta(
                preguntas, "TAJO_NUEVO",
                f"Definir el nuevo tajo '{next(iter(item['originales']), task_id)}': significado, propiedad, posición, estados y dependencias.",
                task_id, loc,
            )
        elif item.get("especial_verificar"):
            categoria = "DUDAS"
            motivo = meta.get("impacto", "Alcance pendiente de revisión.")
        elif item.get("omitido_ultima"):
            categoria = "DUDAS"
            motivo = "El tajo desapareció sin una X previa; confirmar su estado."
            _pregunta(
                preguntas, "OMITIDO_SIN_X",
                f"{meta.get('nombre', task_id)} dejó de aparecer con último estado {estado or 'pendiente'}. Confirmar si terminó o sigue pendiente.",
                task_id, loc,
            )
        elif caducada and not ignorar_caducidad:
            categoria = "DUDAS"
            motivo = f"La revisión tiene {edad_dias} días; actualizar antes de ejecutar."
        else:
            for dep in meta.get("deps", []):
                dep_id = dep["id"]
                dep_estado = _buscar_dep(por_loc[loc], dep_id)
                dep_meta = catalogo.meta(dep_id, {"nombre": dep_id})
                nombre_dep = dep_meta.get("nombre", dep_id)
                # None = nunca visto en ninguna revisión = no iniciado = 0%
                dep_valor = ESTADO_VALOR.get(dep_estado, 0.0)
                if dep_valor < float(dep.get("minimo", 1.0)):
                    bloqueos.append(nombre_dep)
                else:
                    cumplidas.append(nombre_dep)
            if bloqueos:
                categoria = "BLOQUEADO"
                motivo = "Dependencias pendientes: " + ", ".join(bloqueos) + "."
            else:
                categoria = "VIABLE"
                motivo = meta.get("impacto", "Viable según el orden lógico y las dependencias.")

        detalle.append({
            "tarea_id": task_id,
            "trabajo": meta.get("nombre", task_id),
            "trabajos_originales": sorted(item["originales"]),
            "propiedad": propiedad,
            "ambito": ambito,
            "ambito_nombre": AMBITO_NOMBRE[ambito],
            "orden_ejecucion": int(meta.get("orden", 9999)),
            "fase_nombre": meta.get("fase", "Sin clasificar"),
            "display_group": meta.get("display_group", task_id),
            "edificio": loc[0], "planta": loc[1], "unidad": loc[2],
            "estado": estado,
            "estado_actual": "Pendiente" if estado == "" else estado,
            "categoria": categoria,
            "motivo": motivo,
            "dependencias_cumplidas": cumplidas,
            "dependencias_bloqueantes": bloqueos,
            "dependencias_sin_dato": [],
            "omitido_ultima": bool(item.get("omitido_ultima")),
            "forzado_entregado": bool(item.get("forzado_entregado")),
            "ultima_fecha": item.get("ultima_fecha"),
        })

    detalle.sort(key=lambda x: (
        x["orden_ejecucion"], AMBITO_ORDEN[x["ambito"]],
        _orden_natural(x["edificio"]), _orden_natural(x["planta"]),
        _orden_natural(x["unidad"]), x["trabajo"].casefold(),
    ))
    return detalle, edad_dias, caducada


def _estado_resumen(conteo):
    orden = {"M": 0, "/": 1, "Pendiente": 2, "X": 3}
    return " · ".join(
        f"{estado}: {cantidad}"
        for estado, cantidad in sorted(conteo.items(), key=lambda x: (orden.get(x[0], 9), x[0]))
    )


def _agrupar_prioridades(detalle, limite=200):
    grupos = {}
    for item in detalle:
        if item["propiedad"] != "propio" or item["categoria"] not in ("VIABLE", "DUDAS"):
            continue
        key = (item["categoria"], item["tarea_id"], item["ambito"])
        g = grupos.setdefault(key, {
            "tarea_id": item["tarea_id"], "trabajo": item["trabajo"],
            "situacion": "LISTO" if item["categoria"] == "VIABLE" else "VERIFICAR",
            "categoria": item["categoria"], "ambito": item["ambito"],
            "ambito_nombre": item["ambito_nombre"],
            "prioridad": {"vivienda": "P1", "zona_comun": "P2", "edificio": "P3"}[item["ambito"]],
            "orden_ejecucion": item["orden_ejecucion"],
            "fase_nombre": item["fase_nombre"], "ubicaciones": [],
            "estado_conteo": Counter(), "motivos": set(), "n_unidades": 0,
        })
        g["ubicaciones"].append({
            "edificio": item["edificio"], "planta": item["planta"],
            "unidades": [item["unidad"]], "n_unidades": 1,
            "estado_actual": item["estado_actual"],
        })
        g["estado_conteo"][item["estado_actual"]] += 1
        g["motivos"].add(item["motivo"])
        g["n_unidades"] += 1

    salida = []
    for g in grupos.values():
        g["ubicaciones"].sort(key=lambda x: (
            _orden_natural(x["edificio"]), _orden_natural(x["planta"]), _orden_natural(x["unidades"][0])
        ))
        g["n_ubicaciones"] = len(g["ubicaciones"])
        g["estado_actual"] = _estado_resumen(g.pop("estado_conteo"))
        g["motivo"] = " ".join(sorted(g.pop("motivos")))
        g["impacto_gremios"] = g["motivo"]
        salida.append(g)
    salida.sort(key=lambda x: (
        0 if x["situacion"] == "LISTO" else 1,
        x["orden_ejecucion"], AMBITO_ORDEN[x["ambito"]], x["trabajo"].casefold(),
    ))
    salida = salida[:limite]
    for i, item in enumerate(salida, 1):
        item["orden"] = i
    return salida


def _agrupar_inventario(detalle):
    grupos = {}
    for item in detalle:
        agrupar_externo = item["propiedad"] in ("externo", "coordinacion")
        group_id = item["display_group"] if agrupar_externo else item["tarea_id"]
        key = (group_id, item["propiedad"])
        nombre = DISPLAY_NAMES.get(group_id, item["trabajo"])
        g = grupos.setdefault(key, {
            "grupo_id": group_id, "trabajo": nombre,
            "propiedad": item["propiedad"], "orden_ejecucion": item["orden_ejecucion"],
            "fase_nombre": item["fase_nombre"], "categorias": Counter(),
            "estados": Counter(), "ubicaciones": [], "subtajos": set(),
            "motivos": set(),
        })
        g["orden_ejecucion"] = min(g["orden_ejecucion"], item["orden_ejecucion"])
        g["categorias"][item["categoria"]] += 1
        g["estados"][item["estado_actual"]] += 1
        g["subtajos"].add(item["trabajo"])
        g["motivos"].add(item["motivo"])
        g["ubicaciones"].append({
            "edificio": item["edificio"], "planta": item["planta"], "unidad": item["unidad"],
            "estado": item["estado_actual"], "categoria": item["categoria"],
        })

    salida = []
    for g in grupos.values():
        cats = g["categorias"]
        if g["propiedad"] == "desconocido":
            seccion = "DUDAS"
        elif g["propiedad"] in ("externo", "coordinacion"):
            seccion = "TERMINADO" if sum(v for k, v in cats.items() if k != "TERMINADO") == 0 else "OTROS_GREMIOS"
        elif cats.get("VIABLE"):
            seccion = "VIABLE"
        elif cats.get("BLOQUEADO"):
            seccion = "BLOQUEADO"
        elif cats.get("DUDAS"):
            seccion = "DUDAS"
        else:
            seccion = "TERMINADO"
        g["seccion"] = seccion
        g["seccion_nombre"] = SECCION_NOMBRE[seccion]
        g["n_ubicaciones"] = len(g["ubicaciones"])
        g["estado_actual"] = _estado_resumen(g.pop("estados"))
        g["resumen_categorias"] = dict(g.pop("categorias"))
        g["subtajos"] = sorted(g["subtajos"])
        g["motivo"] = " ".join(sorted(g.pop("motivos")))
        g["ubicaciones"].sort(key=lambda x: (
            _orden_natural(x["edificio"]), _orden_natural(x["planta"]), _orden_natural(x["unidad"])
        ))
        salida.append(g)
    salida.sort(key=lambda x: (
        SECCION_ORDEN[x["seccion"]], x["orden_ejecucion"], x["trabajo"].casefold()
    ))
    for i, item in enumerate(salida, 1):
        item["orden_inventario"] = i
    return salida


def _serializar_preguntas(preguntas):
    salida = []
    for item in preguntas.values():
        ubicaciones = sorted(item["ubicaciones"], key=lambda x: (
            _orden_natural(x[0]), _orden_natural(x[1]), _orden_natural(x[2])
        ))
        salida.append({
            "codigo": item["codigo"], "tarea_id": item["tarea_id"],
            "pregunta": item["pregunta"],
            "n_ubicaciones": len(ubicaciones),
            "ubicaciones": [
                {"edificio": x[0], "planta": x[1], "unidad": x[2]} for x in ubicaciones[:20]
            ],
        })
    salida.sort(key=lambda x: (x["codigo"], x["pregunta"]))
    return salida


def priorizar_historial(historial, obra="", limite=200):
    preguntas = {}
    catalogo = Catalogo(obra)
    for error in catalogo.errores:
        _pregunta(preguntas, "ERROR_CATALOGO", error)

    estados, _vistos_ultima, ultima_fecha = _construir_estado(historial, catalogo, preguntas)
    if not estados:
        return {
            "version": VERSION, "catalogo_version": catalogo.version,
            "obra": obra, "revision": ultima_fecha,
            "estado_obra": catalogo.config_obra.get("estado_obra"),
            "historial_confirmado_terminado": bool(catalogo.config_obra.get("forzar_historial_terminado")),
            "resumen": {"listos": 0, "verificar": 0, "bloqueados": 0, "inventario_total": 0},
            "items": [], "detalle_items": [], "inventario": [],
            "dudas_pendientes": [], "avisos": ["No hay datos de revisión."],
        }

    _aplicar_excepciones_obra(estados, catalogo, preguntas)
    detalle, edad_dias, caducada = _clasificar_detalle(estados, catalogo, ultima_fecha, preguntas)
    items = _agrupar_prioridades(detalle, limite=limite)
    inventario = _agrupar_inventario(detalle)
    dudas = _serializar_preguntas(preguntas)

    listos = [x for x in items if x["situacion"] == "LISTO"]
    verificar = [x for x in items if x["situacion"] == "VERIFICAR"]
    secciones = Counter(x["seccion"] for x in inventario)
    resumen = {
        "listos": len(listos), "verificar": len(verificar),
        "unidades_listas": sum(x["n_unidades"] for x in listos),
        "unidades_verificar": sum(x["n_unidades"] for x in verificar),
        "bloqueados": secciones.get("BLOQUEADO", 0),
        "otros_gremios": secciones.get("OTROS_GREMIOS", 0),
        "dudas": secciones.get("DUDAS", 0),
        "terminados": secciones.get("TERMINADO", 0),
        "inventario_total": len(inventario),
        "detalle_total": len(detalle),
        "preguntas_pendientes": len(dudas),
        "viviendas": sum(1 for x in listos if x["ambito"] == "vivienda"),
        "zonas_comunes": sum(1 for x in listos if x["ambito"] == "zona_comun"),
        "edificio": sum(1 for x in listos if x["ambito"] == "edificio"),
    }
    avisos = [
        "El inventario incluye todos los tajos encontrados en el historial; los terminados aparecen al final.",
        "Los nombres nuevos no se fusionan: quedan SIN CLASIFICAR hasta confirmación.",
        "Una X histórica se conserva aunque el tajo desaparezca; nunca se rebaja sin verificación.",
        "El orden sigue la secuencia lógica definida en CATALOGO_TAJOS.json.",
    ]
    if catalogo.config_obra.get("estado_obra"):
        avisos.insert(0, catalogo.config_obra["estado_obra"] + ".")
    if catalogo.config_obra.get("forzar_historial_terminado_hasta"):
        avisos.insert(1, "Primera fase confirmada hasta {} a efectos de priorizacion.".format(
            catalogo.config_obra["forzar_historial_terminado_hasta"]
        ))
    if caducada and not catalogo.config_obra.get("forzar_historial_terminado"):
        avisos.append(f"La revisión tiene {edad_dias} días; los tajos pendientes requieren verificación.")

    return {
        "version": VERSION, "catalogo_version": catalogo.version,
        "obra": obra, "revision": ultima_fecha,
        "edad_revision_dias": edad_dias, "revision_caducada": caducada,
        "estado_obra": catalogo.config_obra.get("estado_obra"),
        "historial_confirmado_terminado": bool(catalogo.config_obra.get("forzar_historial_terminado")),
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "resumen": resumen, "items": items,
        "detalle_items": detalle, "inventario": inventario,
        "dudas_pendientes": dudas, "avisos": avisos,
    }


def escribir_json(resultado, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)



