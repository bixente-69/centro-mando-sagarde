# -*- coding: utf-8 -*-
"""
REGENERAR OBRA — regeneración acotada por obra + agregación final
--------------------------------------------------------------------------
Motivo: `generar_todos.py` procesa TODAS las obras registradas en su lista
OBRAS en una sola ejecución. Con 5+ obras esto puede superar fácilmente los
límites de tiempo de un entorno con ejecución acotada (ej. una sesión de
agente con timeout de comandos). Este script permite regenerar UNA obra a
la vez (rápido, siempre dentro de cualquier límite razonable) y agregar el
resultado global (index.html, resumen_obras.json, registro de revisiones)
en un paso final separado, sin tener que reprocesar todas las obras cada vez.

Uso:
    # 1) Regenerar cada obra que cambió, una llamada por obra:
    python3 regenerar_obra.py mungia
    python3 regenerar_obra.py bolueta
    ...

    # 2) Cuando ya se regeneraron todas las obras que tocaba, agregar:
    python3 regenerar_obra.py --finalizar

    # (equivalente a: regenerar 1 obra y finalizar en la misma llamada,
    #  solo seguro si es una unica obra y hay margen de tiempo)
    python3 regenerar_obra.py mungia --finalizar

Cada invocación de una obra concreta guarda su resultado en una cache local
(`_cache_resultados_regen.json`, junto a resumen_obras.json) para que el
paso de agregación final no dependa de qué obras se procesaron en la MISMA
llamada — puede combinar resultados de llamadas anteriores.

Si una obra registrada en OBRAS no tiene entrada en la cache (nunca se ha
regenerado con este script), --finalizar la deja como estaba antes (usa el
comportamiento normal de generar_todos.py: si ya existe un panel.html previo
en disco, se muestra como "no actualizado en esta ejecución"; si no, como
pendiente de alta). Nunca inventa datos.
"""
import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBRAS_ABIERTAS_DIR = os.path.join(BASE_DIR, os.pardir, "SAGARDE OBRAS ABIERTAS")
MOTOR_IA_DIR = os.path.join(OBRAS_ABIERTAS_DIR, "_SISTEMA INFORME SAGARDE IA")
MOTOR_IA_DIR = os.path.normpath(MOTOR_IA_DIR)
CACHE_PATH = os.path.join(MOTOR_IA_DIR, "_cache_resultados_regen.json")

sys.path.insert(0, MOTOR_IA_DIR)
sys.path.insert(0, os.path.join(MOTOR_IA_DIR, "adaptadores"))
import generar_todos as gt  # noqa: E402


def _cargar_cache():
    if not os.path.isfile(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _guardar_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def regenerar_una_obra(obra_id, hacer_pdf=False):
    """Regenera memoria/prioridades/panel/informe de UNA obra y guarda su
    'resultado' (el mismo dict que generar_todos.main() acumularía para el
    index/resumen) en la cache local, indexado por obra_id."""
    obras_originales = gt.OBRAS
    obra_cfg = next((o for o in obras_originales if o["id"] == obra_id), None)
    if not obra_cfg:
        disponibles = ", ".join(o["id"] for o in obras_originales)
        raise SystemExit(
            "Obra '{}' no está en OBRAS de generar_todos.py. Disponibles: {}".format(
                obra_id, disponibles
            )
        )

    gt.OBRAS = [obra_cfg]
    capturado = {}
    gt.generar_index = lambda resultados: capturado.setdefault("resultados", resultados)
    gt.escribir_resumen_json = lambda resultados: None
    gt.publicar_registro_revisiones = lambda: None
    try:
        gt.main(hacer_pdf=hacer_pdf)
    finally:
        gt.OBRAS = obras_originales
        gt.generar_index = _generar_index_original
        gt.escribir_resumen_json = _escribir_resumen_json_original
        gt.publicar_registro_revisiones = _publicar_registro_revisiones_original

    resultados = capturado.get("resultados", [])
    if not resultados:
        print("[AVISO] '{}' no produjo resultado (revisar errores arriba).".format(obra_id))
        return None

    cache = _cargar_cache()
    cache[obra_id] = resultados[0]
    _guardar_cache(cache)
    print("Cache actualizada para '{}' -> {}".format(obra_id, CACHE_PATH))
    return resultados[0]


def finalizar():
    """Agrega los resultados cacheados de todas las obras y regenera
    index.html, resumen_obras.json y el registro de revisiones (una sola
    vez, barato: no reprocesa historial/priorización de ninguna obra)."""
    cache = _cargar_cache()
    resultados = []
    for obra in gt.OBRAS:
        r = cache.get(obra["id"])
        if r:
            resultados.append(r)
    print("Obras con resultado cacheado: {} de {} registradas.".format(
        len(resultados), len(gt.OBRAS)))
    for r in resultados:
        print(" -", r["nombre"], "pct_ponderado=", r.get("pct_ponderado"))

    _generar_index_original(resultados)
    _escribir_resumen_json_original(resultados)
    _publicar_registro_revisiones_original()
    print("OK: index.html, resumen_obras.json y registro de revisiones actualizados.")


# Referencias a las funciones REALES (antes de cualquier monkeypatch), para
# poder restaurarlas tras cada regenerar_una_obra() y para finalizar().
_generar_index_original = gt.generar_index
_escribir_resumen_json_original = gt.escribir_resumen_json
_publicar_registro_revisiones_original = gt.publicar_registro_revisiones


if __name__ == "__main__":
    argv = sys.argv[1:]
    solo_finalizar = "--finalizar" in argv
    obra_ids = [a for a in argv if not a.startswith("--")]

    if not obra_ids and not solo_finalizar:
        print(__doc__)
        raise SystemExit(1)

    for obra_id in obra_ids:
        regenerar_una_obra(obra_id)

    if solo_finalizar:
        finalizar()
