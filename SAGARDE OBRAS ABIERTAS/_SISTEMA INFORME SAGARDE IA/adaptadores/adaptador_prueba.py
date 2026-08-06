# -*- coding: utf-8 -*-
"""
ADAPTADOR - 2026 OBRA PRUEBA
----------------------------
Obra ficticia. Existe para verificar el paso 4 del ciclo (que la IA lea la
hoja marcada en obra) sin tocar datos de una obra real: se controlan las dos
revisiones, asi que la respuesta correcta se conoce de antemano.

ES UNA OBRA NATIVA, Y ESO CAMBIA DE DONDE SALEN LOS DATOS
---------------------------------------------------------
Los adaptadores de las obras reales leen hojas de revision (Word, PDF, JSON)
y la ficha corrige despues lo leido. Aqui no hay nada anterior que leer: la
obra nacio de su propia hoja de alta y `ficha_obra.json` ES la base. Este
adaptador no inventa una segunda copia de los datos: devuelve lo que la ficha
tiene medido, y punto.

Consecuencia buscada: cuando el lector del paso 4 escriba en la ficha lo que
encuentre en la hoja marcada, el panel, los KPI, el priorizador y el informe
lo veran sin tocar nada mas.

MIENTRAS NO HAYA NADA MEDIDO, DEVUELVE HISTORIAL VACIO
------------------------------------------------------
La hoja de alta esta en blanco, asi que todas las celdas valen '?' ("nadie lo
ha mirado"). `snapshot_desde_ficha` deja fuera los '?' a proposito, porque
contarlos como pendientes seria afirmar algo partiendo de nada. Con historial
vacio la obra aparece como "sin revisiones", igual que Gorliz, que es
exactamente la verdad: todavia no se ha medido nada.
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SISTEMA = os.path.dirname(AQUI)
OBRAS_DIR = os.path.dirname(SISTEMA)
CARPETA_OBRA = os.path.join(OBRAS_DIR, "2026 OBRA PRUEBA")

if SISTEMA not in sys.path:
    sys.path.insert(0, SISTEMA)

import ficha_obra as fichas  # noqa: E402


def _orden_fecha(fecha):
    """'05/08/2026' -> ('2026','08','05'), para ordenar sin parsear."""
    partes = str(fecha or "").split("/")
    if len(partes) != 3:
        return ("0000", "00", "00")
    dia, mes, anio = partes
    return (anio, mes, dia)


def cargar_historial(carpeta_obra=CARPETA_OBRA):
    """[(fecha, snapshot)] con lo que la ficha tiene medido.

    Una sola entrada, la de la ultima revision registrada: la ficha guarda el
    estado vigente de cada celda, no una foto por revision. Si no hay
    revisiones registradas, o ninguna celda esta medida, devuelve [].
    """
    ficha = fichas.cargar(carpeta_obra)
    if not ficha:
        return []

    revisiones = ficha.get("revisiones") or []
    if not revisiones:
        return []

    ultima = max(revisiones, key=lambda r: _orden_fecha(r.get("fecha")))
    fecha = ultima.get("fecha")
    if not fecha:
        return []

    snapshot = fichas.snapshot_desde_ficha(ficha)
    if not snapshot:
        return []

    return [(fecha, snapshot)]
