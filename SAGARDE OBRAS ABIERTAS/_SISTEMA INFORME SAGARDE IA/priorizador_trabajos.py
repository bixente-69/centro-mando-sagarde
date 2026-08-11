# -*- coding: utf-8 -*-
"""Motor Sagarde v4: catálogo explícito, memoria histórica e inventario completo."""

from __future__ import annotations

import difflib
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime


VERSION = "4.3"
# Unificado con SCORE de motor_informes.py (25/07/2026): mismo valor de "M"
# en los dos sitios. Si cambia aquí, cambiar también SCORE en motor_informes.py.
ESTADO_VALOR = {"": 0.0, "/": 0.25, "M": 0.60, "X": 1.0}
# Estado guardado en la base -> estado que entiende el motor.
# '?' (nadie lo ha mirado) y 'N' (no aplica) NO tienen equivalente: valen ''
# igual que 'P', pero significan cosas distintas. Se conservan en
# 'estado_base' y los separa _clasificar_detalle. Confundirlos es la causa de
# casi todo lo que ha fallado aqui.
ESTADO_BASE_A_MOTOR = {"X": "X", "M": "M", "/": "/", "P": ""}
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
    "SIN_REVISAR": 4,
    "TERMINADO": 5,
}
SECCION_NOMBRE = {
    "VIABLE": "Tajos viables",
    "BLOQUEADO": "Tajos bloqueados",
    "OTROS_GREMIOS": "Otros gremios e interferencias",
    "DUDAS": "Dudas pendientes",
    "SIN_REVISAR": "Sin revisar nunca",
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
        # El nombre principal forma parte del diccionario igual que sus
        # alias. Las hojas nuevas suelen imprimir ``nombre`` mientras que
        # las antiguas usan un alias abreviado; ambos deben resolver al mismo
        # id para que el motor no invente a la vez TAJO_NUEVO y OMITIDO_SIN_X.
        nombres = [tajo.get("nombre")] + list(tajo.get("aliases", []))
        for alias in nombres:
            if not alias:
                continue
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


def _ultima_revision_ficha(ficha):
    """La fecha mas reciente registrada en la base, o None si no hay ninguna."""
    fechas = [r.get("fecha") for r in (ficha.get("revisiones") or [])
              if r.get("fecha")]
    if not fechas:
        return None
    return max(fechas, key=_fecha)


def estado_desde_ficha(ficha, catalogo):
    """Construye el estado por celda leyendo la base de la obra.

    Sustituye a _construir_estado. La base YA es el estado resuelto: trae la
    norma de la ultima revision aplicada, la fecha y la revision de origen de
    cada celda, y las ubicaciones descartadas fuera del arbol de estructura.

    Recorrer el arbol es, por si solo, respetar estructura.exclusiones: por eso
    aqui no hay ninguna comprobacion de exclusiones. Reconstruir esto desde el
    historial crudo metia 4 viviendas inexistentes en Bolueta y 15 en Orueta.
    """
    estructura = ficha.get("estructura") or {}
    alias = estructura.get("alias_historico") or {}
    tajos = (ficha.get("tajos") or {}).get("detalle") or []
    guardados = ficha.get("estados") or {}

    estados = {}
    for bloque in estructura.get("bloques") or []:
        for portal in bloque.get("portales") or []:
            edificio = (portal.get("referencia") or portal.get("nombre")
                        or portal["id"])
            for planta in portal.get("plantas") or []:
                planta_nom = planta.get("nombre") or planta["id"]
                for ubi in planta.get("ubicaciones") or []:
                    clave_alias = "%s__%s__%s" % (portal["id"], planta["id"],
                                                  ubi["id"])
                    unidad = alias.get(clave_alias, ubi["id"])
                    loc = (edificio, planta_nom, unidad)
                    for tajo in tajos:
                        clave = "%s__%s__%s__%s" % (
                            portal["id"], planta["id"], tajo["id"], ubi["id"])
                        dato = guardados.get(clave)
                        if not dato:
                            continue
                        nombre = tajo.get("nombre") or tajo["id"]
                        # El id de la base manda si el catalogo lo conoce; si
                        # no, se resuelve por nombre para pillar los alias.
                        meta = catalogo.meta(tajo["id"])
                        if meta:
                            task_id, desconocido = tajo["id"], False
                        else:
                            task_id, meta, desconocido = catalogo.resolver(nombre)
                        valor = str(dato.get("v") or "")
                        # La CLAVE es el id de la base, no el del catalogo.
                        # Dos filas distintas de la base pueden resolver al
                        # mismo tajo del catalogo (en Orueta, placas_tps_cuadro
                        # cae en placas_tapas por alias). Indexar por el id del
                        # catalogo hacia que una pisara a la otra y se perdian
                        # 98 celdas en silencio. sembrar_reglas lo saca como
                        # pregunta; aqui no se pierde ninguna fila.
                        estados[(loc, tajo["id"])] = {
                            "estado": ESTADO_BASE_A_MOTOR.get(valor, ""),
                            "estado_base": valor,
                            "originales": {nombre},
                            "meta": meta,
                            "desconocido": desconocido,
                            "loc": loc,
                            "task_id": task_id,
                            "primera_fecha": dato.get("f"),
                            "ultima_fecha": dato.get("f"),
                            "conflicto": False,
                            "omitido_ultima": False,
                            "forzado_entregado": False,
                        }
    return estados, _ultima_revision_ficha(ficha)


CAMPOS_SEMBRADOS = ("orden", "propiedad", "ambito", "fase", "deps")


def sembrar_reglas(ficha, catalogo):
    """Vuelca orden, propiedad, ambito, fase y deps del catalogo sobre la base.

    DECISION: el catalogo manda. La base guarda el ESTADO; el catalogo guarda
    la REGLA. Un tajo que el catalogo no conoce NO recibe orden inventado:
    sale como pregunta para ampliar el catalogo, que es SIEMPRE AMPLIABLE.

    En Orueta habia 18 tajos con orden 9999 y 14 de ellos tenian orden real en
    el catalogo: el orden estaba declarado y el motor lo ignoraba. Los otros 4
    son deriva de nombre (focos_hab / focos_habitaciones), y para esos la
    pregunta trae los ids parecidos para poder resolverla de un vistazo.

    Devuelve la lista de preguntas. Modifica ficha['tajos']['detalle'] en sitio.
    """
    preguntas = []
    detalle = (ficha.get("tajos") or {}).get("detalle") or []
    ids_catalogo = list(catalogo.tajos)

    for tajo in detalle:
        meta = catalogo.meta(tajo["id"])
        if not meta:
            nombre = tajo.get("nombre") or tajo["id"]
            _resuelto, meta_alias, desconocido = catalogo.resolver(nombre)
            if desconocido:
                preguntas.append({
                    "codigo": "TAJO_FUERA_DEL_CATALOGO",
                    "tarea_id": tajo["id"],
                    "nombre": nombre,
                    "parecidos": difflib.get_close_matches(
                        tajo["id"], ids_catalogo, n=3, cutoff=0.5),
                })
                continue
            meta = meta_alias
        for campo in CAMPOS_SEMBRADOS:
            if campo in meta:
                tajo[campo] = meta[campo]
        if (tajo.get("orden") or 9999) >= 9999:
            preguntas.append({
                "codigo": "ORDEN_SIN_CONFIRMAR",
                "tarea_id": tajo["id"],
                "nombre": tajo.get("nombre") or tajo["id"],
                "parecidos": [],
            })

    # Dos filas de la base que resuelven al mismo tajo del catalogo son un
    # duplicado que hay que resolver: en Orueta, placas_tps_cuadro cae en
    # placas_tapas por alias. No se fusionan solas ni se descarta ninguna.
    por_catalogo = {}
    for tajo in detalle:
        meta = catalogo.meta(tajo["id"])
        if meta:
            resuelto = tajo["id"]
        else:
            resuelto, _m, desconocido = catalogo.resolver(
                tajo.get("nombre") or tajo["id"])
            if desconocido:
                continue
        por_catalogo.setdefault(resuelto, []).append(tajo["id"])
    for resuelto, ids in sorted(por_catalogo.items()):
        if len(ids) > 1:
            preguntas.append({
                "codigo": "TAJO_DUPLICADO_EN_LA_BASE",
                "tarea_id": resuelto,
                "nombre": catalogo.meta(resuelto).get("nombre", resuelto),
                "parecidos": sorted(ids),
            })

    # Una dependencia que apunta a un tajo que esta obra no tiene vale 0 y
    # bloquea para siempre en silencio: "Dependencias pendientes: Tabicado"
    # sin que Tabicado exista en la obra. Se avisa en vez de callar.
    presentes = {t["id"] for t in detalle}
    for tajo in detalle:
        ausentes = sorted(d["id"] for d in (tajo.get("deps") or [])
                          if d["id"] not in presentes)
        if ausentes:
            preguntas.append({
                "codigo": "DEPENDENCIA_AUSENTE_EN_LA_OBRA",
                "tarea_id": tajo["id"],
                "nombre": tajo.get("nombre") or tajo["id"],
                "parecidos": ausentes,
            })
    return preguntas


def verificar_rejilla(ficha):
    """La base debe ser una rejilla densa: ubicaciones x tajos, y cada
    ubicacion tiene que ser distinguible de las demas.

    Dos comprobaciones, las dos contra perdidas silenciosas:

    1. Faltan celdas. Calcular sobre datos parciales es peor que avisar.
    2. Dos ubicaciones distintas producen el mismo (edificio, planta, unidad).
       Pasa cuando dos plantas comparten el NOMBRE aunque tengan ids
       distintos: OBRA PRUEBA tiene dos plantas llamadas '1a' y por eso el
       motor veia 26 de sus 31 ubicaciones. La base las guarda separadas —la
       clave lleva el id— pero al priorizar se fusionan y una pisa a la otra.
    """
    avisos = []
    estructura = ficha.get("estructura") or {}
    tajos = (ficha.get("tajos") or {}).get("detalle") or []
    alias = estructura.get("alias_historico") or {}

    ubicaciones = 0
    locs = {}
    for bloque in estructura.get("bloques") or []:
        for portal in bloque.get("portales") or []:
            edificio = (portal.get("referencia") or portal.get("nombre")
                        or portal["id"])
            for planta in portal.get("plantas") or []:
                planta_nom = planta.get("nombre") or planta["id"]
                for ubi in planta.get("ubicaciones") or []:
                    ubicaciones += 1
                    clave_alias = "%s__%s__%s" % (portal["id"], planta["id"],
                                                  ubi["id"])
                    unidad = alias.get(clave_alias, ubi["id"])
                    locs.setdefault((edificio, planta_nom, unidad), []).append(
                        "%s/%s" % (planta["id"], ubi["id"]))

    esperadas = ubicaciones * len(tajos)
    encontradas = len(ficha.get("estados") or {})
    if esperadas and encontradas and encontradas != esperadas:
        avisos.append(
            "La base no es una rejilla completa: %d celdas encontradas frente "
            "a %d esperadas (%d ubicaciones x %d tajos). Los tajos que falten "
            "no se pueden priorizar."
            % (encontradas, esperadas, ubicaciones, len(tajos)))

    chocan = {k: v for k, v in locs.items() if len(v) > 1}
    if chocan:
        detalle = "; ".join(
            "%s planta %s unidad %s <- %s" % (k[0], k[1], k[2], ", ".join(v))
            for k, v in sorted(chocan.items())[:5])
        avisos.append(
            "%d ubicaciones de la base se fusionan al priorizar porque "
            "producen la misma clave (%d ubicaciones declaradas, %d "
            "distinguibles). Suele ser que dos plantas comparten nombre. "
            "Afectadas: %s."
            % (ubicaciones - len(locs), ubicaciones, len(locs), detalle))
    return avisos


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


def _clasificar_detalle(estados, catalogo, ultima_fecha, preguntas, hoy=None):
    por_loc = defaultdict(dict)
    for item in estados.values():
        por_loc[item["loc"]][item["task_id"]] = item

    # DECISION (11/08/2026): la antiguedad es un AVISO, no un interruptor.
    # Volcar toda la obra a DUDAS a los 30 dias apagaba cuatro obras el mismo
    # dia, y calcular la edad con datetime.now() dentro del cálculo hacia que
    # el mismo dato produjera paneles distintos segun cuando se regenerara.
    # `hoy` se inyecta para que el resultado sea reproducible.
    edad_dias = None
    referencia = hoy or datetime.now().date()
    try:
        edad_dias = (referencia - _fecha(ultima_fecha).date()).days
    except Exception:
        pass
    caducada = edad_dias is None or edad_dias > 30

    detalle = []
    for item in estados.values():
        meta = item["meta"]
        task_id = item["task_id"]
        loc = item["loc"]
        estado = item["estado"]
        propiedad = meta.get("propiedad", "desconocido")
        ambito = _scope(meta, " ".join(item["originales"]), loc[2])
        estado_base = item.get("estado_base", "")
        bloqueos = []
        cumplidas = []
        deps_detalle = []

        # 'N' no aplica a esta ubicacion: no es trabajo pendiente ni
        # terminado, simplemente no existe ahi. No entra en el calculo.
        if estado_base == "N":
            continue

        if estado_base == "?":
            # Nadie lo ha mirado nunca. No es 'pendiente': afirmar que lo esta
            # seria inventarse el dato. Va antes que la propiedad del tajo
            # porque un tajo de otro gremio sin mirar tambien hay que ir a
            # verlo. En Bolueta esto son 5 ubicaciones reales que hasta ahora
            # no aparecian en ninguna parte.
            categoria = "SIN_REVISAR"
            motivo = ("Nadie lo ha mirado nunca. Hay que ir a comprobarlo "
                      "antes de poder decidir.")
        elif item.get("conflicto"):
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
        else:
            for dep in meta.get("deps", []):
                dep_id = dep["id"]
                dep_estado = _buscar_dep(por_loc[loc], dep_id)
                dep_meta = catalogo.meta(dep_id, {"nombre": dep_id})
                nombre_dep = dep_meta.get("nombre", dep_id)
                # None = nunca visto en ninguna revisión = no iniciado = 0%
                dep_valor = ESTADO_VALOR.get(dep_estado, 0.0)
                minimo = float(dep.get("minimo", 1.0))
                # Se guarda el detalle para poder decir CUANTO falta, no solo
                # que falta: "Tubeado interior: M - falta X".
                deps_detalle.append({
                    "id": dep_id, "nombre": nombre_dep,
                    "estado": dep_estado if dep_estado else "Pendiente",
                    "minimo": minimo, "cumplida": dep_valor >= minimo,
                })
                if dep_valor < minimo:
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
            "dependencias_detalle": deps_detalle,
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


def _clave_unidad(item):
    """Que cuenta como 'una unidad' segun el ambito del tajo.

    La hoja repite cada tajo en TODAS las ubicaciones, tambien los que son
    unicos del edificio. Contar celdas daba '92 cuartos tecnicos' en Bolueta
    donde hay uno, y 370 de sus 851 unidades estaban infladas asi.
    """
    ambito = item["ambito"]
    if ambito == "edificio":
        return (item["edificio"],)
    if ambito == "zona_comun":
        return (item["edificio"], item["planta"])
    return (item["edificio"], item["planta"], item["unidad"])


def _agrupar_prioridades(detalle, limite=200, con_recorte=False):
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
            "estado_conteo": Counter(), "motivos": set(),
            "unidades_reales": set(), "n_celdas": 0,
        })
        g["ubicaciones"].append({
            "edificio": item["edificio"], "planta": item["planta"],
            "unidades": [item["unidad"]], "n_unidades": 1,
            "estado_actual": item["estado_actual"],
        })
        g["estado_conteo"][item["estado_actual"]] += 1
        g["motivos"].add(item["motivo"])
        g["unidades_reales"].add(_clave_unidad(item))
        g["n_celdas"] += 1

    salida = []
    for g in grupos.values():
        g["ubicaciones"].sort(key=lambda x: (
            _orden_natural(x["edificio"]), _orden_natural(x["planta"]), _orden_natural(x["unidades"][0])
        ))
        g["n_ubicaciones"] = len(g["ubicaciones"])
        g["n_unidades"] = len(g.pop("unidades_reales"))
        g["estado_actual"] = _estado_resumen(g.pop("estado_conteo"))
        g["motivo"] = " ".join(sorted(g.pop("motivos")))
        g["impacto_gremios"] = g["motivo"]
        salida.append(g)
    salida.sort(key=lambda x: (
        0 if x["situacion"] == "LISTO" else 1,
        x["orden_ejecucion"], AMBITO_ORDEN[x["ambito"]], x["trabajo"].casefold(),
    ))
    recortados = max(0, len(salida) - limite)
    salida = salida[:limite]
    for i, item in enumerate(salida, 1):
        item["orden"] = i
    if con_recorte:
        return salida, recortados
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
        if cats.get("SIN_REVISAR") == sum(cats.values()):
            # Todas las celdas del grupo estan sin mirar. El grupo entero es
            # 'sin revisar', sea de quien sea el tajo: igual que en la cascada,
            # no haberlo mirado gana sobre la propiedad.
            seccion = "SIN_REVISAR"
        elif g["propiedad"] == "desconocido":
            seccion = "DUDAS"
        elif g["propiedad"] in ("externo", "coordinacion"):
            seccion = "TERMINADO" if sum(v for k, v in cats.items() if k != "TERMINADO") == 0 else "OTROS_GREMIOS"
        elif cats.get("VIABLE"):
            seccion = "VIABLE"
        elif cats.get("BLOQUEADO"):
            seccion = "BLOQUEADO"
        elif cats.get("DUDAS"):
            seccion = "DUDAS"
        elif cats.get("SIN_REVISAR"):
            seccion = "SIN_REVISAR"
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


def prevision_desbloqueos(detalle):
    """Que se libera al terminar cada tajo.

    Es el valor de este apartado en una obra de meses: no solo saber que el
    tubeado de la 12 espera al tabique, sino que acabar el suelo de tres
    plantas libera 40 viviendas de tubeado. Se ordena por lo que mas libera.

    Cuenta unidades reales (segun el ambito del tajo bloqueado), no celdas.
    """
    muestra = {}
    for item in detalle:
        muestra.setdefault(item["tarea_id"], item)

    libera = defaultdict(lambda: {"unidades": set(), "tajos": set()})
    for item in detalle:
        if item["categoria"] != "BLOQUEADO":
            continue
        for dep in item.get("dependencias_detalle") or []:
            if dep.get("cumplida"):
                continue
            registro = libera[dep["id"]]
            registro["unidades"].add((_clave_unidad(item), item["tarea_id"]))
            registro["tajos"].add(item["trabajo"])

    salida = []
    for dep_id, registro in libera.items():
        ref = muestra.get(dep_id)
        salida.append({
            "tarea_id": dep_id,
            "trabajo": ref["trabajo"] if ref else dep_id,
            "estado_actual": ref["estado_actual"] if ref else "—",
            "propiedad": ref["propiedad"] if ref else "desconocido",
            "desbloquea": len(registro["unidades"]),
            "tajos_afectados": sorted(registro["tajos"]),
        })
    salida.sort(key=lambda x: (-x["desbloquea"], x["trabajo"].casefold()))
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


def sin_base(obra=""):
    """DECISION: una obra sin base de datos no calcula prioridades.

    Un recuento vacio es senal de alarma, no de 'no aplica'. Asi se ve de un
    vistazo que obras faltan por dar de alta, en vez de publicar un 0 % que
    parece un dato.
    """
    catalogo = Catalogo(obra)
    return {
        "version": VERSION, "catalogo_version": catalogo.version,
        "obra": obra, "revision": None, "sin_base": True,
        "estado_obra": catalogo.config_obra.get("estado_obra"),
        "historial_confirmado_terminado": bool(
            catalogo.config_obra.get("forzar_historial_terminado")),
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "resumen": {"listos": 0, "verificar": 0, "bloqueados": 0,
                    "sin_revisar": 0, "inventario_total": 0,
                    "preguntas_pendientes": 0},
        "items": [], "detalle_items": [], "inventario": [],
        "dudas_pendientes": [], "preguntas_orden": [], "prevision": [],
        "avisos": ["Esta obra no tiene base de datos todavía. Sembrarla con "
                   "sembrar_ficha_obra.py habilita las prioridades."],
    }


def priorizar_ficha(ficha, obra="", limite=200, hoy=None):
    """Prioriza leyendo la base de la obra. Sustituye a priorizar_historial.

    La base es el estado; el catalogo es la regla. `sembrar_reglas` vuelca la
    regla sobre la base antes de clasificar, para que el orden y las
    dependencias salgan siempre del catalogo.
    """
    preguntas = {}
    catalogo = Catalogo(obra)
    for error in catalogo.errores:
        _pregunta(preguntas, "ERROR_CATALOGO", error)

    preguntas_orden = sembrar_reglas(ficha, catalogo)
    avisos_rejilla = verificar_rejilla(ficha)
    estados, ultima_fecha = estado_desde_ficha(ficha, catalogo)
    if not estados:
        return sin_base(obra)

    _aplicar_excepciones_obra(estados, catalogo, preguntas)
    detalle, edad_dias, caducada = _clasificar_detalle(
        estados, catalogo, ultima_fecha, preguntas, hoy=hoy)
    items, recortados = _agrupar_prioridades(detalle, limite=limite,
                                             con_recorte=True)
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
        "sin_revisar": secciones.get("SIN_REVISAR", 0),
        "unidades_sin_revisar": sum(
            1 for x in detalle if x["categoria"] == "SIN_REVISAR"),
        "terminados": secciones.get("TERMINADO", 0),
        "inventario_total": len(inventario),
        "detalle_total": len(detalle),
        "preguntas_pendientes": len(dudas) + len(preguntas_orden),
        "viviendas": sum(1 for x in listos if x["ambito"] == "vivienda"),
        "zonas_comunes": sum(1 for x in listos if x["ambito"] == "zona_comun"),
        "edificio": sum(1 for x in listos if x["ambito"] == "edificio"),
    }
    avisos = list(avisos_rejilla) + [
        "El inventario incluye todos los tajos de la base; los terminados "
        "aparecen al final.",
        "Los nombres nuevos no se fusionan: quedan SIN CLASIFICAR hasta "
        "confirmación.",
        "El orden sigue la secuencia lógica definida en CATALOGO_TAJOS.json.",
    ]
    if catalogo.config_obra.get("estado_obra"):
        avisos.insert(0, catalogo.config_obra["estado_obra"] + ".")
    if caducada:
        avisos.append(
            "La revisión es del %s (%s días). Los tajos conservan su "
            "clasificación; confirmar en obra antes de ejecutar."
            % (ultima_fecha, edad_dias))
    if recortados:
        avisos.append(
            "La lista se ha recortado a %d bloques; hay %d más sin mostrar."
            % (limite, recortados))

    return {
        "version": VERSION, "catalogo_version": catalogo.version,
        "obra": obra, "revision": ultima_fecha, "sin_base": False,
        "edad_revision_dias": edad_dias, "revision_caducada": caducada,
        "estado_obra": catalogo.config_obra.get("estado_obra"),
        "historial_confirmado_terminado": bool(
            catalogo.config_obra.get("forzar_historial_terminado")),
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "resumen": resumen, "items": items,
        "detalle_items": detalle, "inventario": inventario,
        "dudas_pendientes": dudas, "preguntas_orden": preguntas_orden,
        "prevision": prevision_desbloqueos(detalle),
        "avisos": avisos,
    }


def escribir_json(resultado, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)



