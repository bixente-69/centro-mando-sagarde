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
import html
import re
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# BASE_DIR es _SISTEMA/MOTOR: hacen falta DOS pardir para la raiz, no uno.
# Con uno solo se caeria en _SISTEMA y las obras no aparecerian.
OBRAS_ABIERTAS_DIR = os.path.join(BASE_DIR, os.pardir, os.pardir,
                                  "SAGARDE OBRAS ABIERTAS")
MOTOR_IA_DIR = os.path.join(OBRAS_ABIERTAS_DIR, "_SISTEMA INFORME SAGARDE IA")
MOTOR_IA_DIR = os.path.normpath(MOTOR_IA_DIR)
CACHE_PATH = os.path.join(MOTOR_IA_DIR, "_cache_resultados_regen.json")
INDEX_PATH = os.path.join(OBRAS_ABIERTAS_DIR, "index.html")

sys.path.insert(0, MOTOR_IA_DIR)
sys.path.insert(0, os.path.join(MOTOR_IA_DIR, "adaptadores"))
import generar_todos as gt  # noqa: E402


RESUMEN_PATH = gt.RESUMEN_JSON
PENDIENTES_FINALIZAR = "_pendientes_finalizar"
MARCA_GRID = '<div class="grid" id="grid">'
INICIO_TARJETA = re.compile(
    r'(?=<a class="obra" |<div class="obra disabled")'
)
FILA_ULTIMO_ARCHIVO = re.compile(
    r'<div class="row"><span>[^<]*ltimo archivo</span><span>[^<]*</span></div>'
)


def _cargar_cache():
    if not os.path.isfile(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "No se pudo leer la cache de regeneracion '{}': {}".format(
                CACHE_PATH, exc
            )
        ) from exc
    if not isinstance(cache, dict):
        raise RuntimeError(
            "La cache de regeneracion '{}' debe contener un objeto JSON.".format(
                CACHE_PATH
            )
        )
    pendientes = cache.get(PENDIENTES_FINALIZAR, [])
    if not isinstance(pendientes, list) or not all(
        isinstance(obra_id, str) for obra_id in pendientes
    ):
        raise RuntimeError(
            "La clave '{}' de la cache debe ser una lista de ids.".format(
                PENDIENTES_FINALIZAR
            )
        )
    return cache


def _escribir_bytes_atomico(ruta, contenido):
    """Escribe bytes en la misma carpeta y publica con ``os.replace``."""
    carpeta = os.path.dirname(os.path.abspath(ruta))
    fd, temporal = tempfile.mkstemp(
        prefix=os.path.basename(ruta) + ".", suffix=".tmp", dir=carpeta
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(contenido)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporal, ruta)
    except BaseException:
        if os.path.exists(temporal):
            os.remove(temporal)
        raise


def _escribir_texto_atomico(ruta, contenido):
    _escribir_bytes_atomico(ruta, contenido.encode("utf-8"))


def _guardar_cache(cache):
    texto = json.dumps(cache, ensure_ascii=False, indent=2)
    _escribir_texto_atomico(CACHE_PATH, texto)


def _trocear_tarjetas(html_indice):
    """Separa cabecera, tarjetas y pie sin normalizar el texto recibido."""
    try:
        inicio_grid = html_indice.index(MARCA_GRID) + len(MARCA_GRID)
        inicio_footer = html_indice.index('<p class="footer"', inicio_grid)
        fin_grid = html_indice.rindex("</div>", inicio_grid, inicio_footer)
    except ValueError as exc:
        raise ValueError(
            "El formato del indice cambio: no se pudo delimitar la rejilla de tarjetas."
        ) from exc

    contenido = html_indice[inicio_grid:fin_grid]
    comienzos = [m.start() for m in INICIO_TARJETA.finditer(contenido)]
    if not comienzos:
        if contenido.strip():
            raise ValueError(
                "El formato del indice cambio: la rejilla no contiene tarjetas reconocibles."
            )
        tarjetas = []
    else:
        if contenido[:comienzos[0]].strip():
            raise ValueError(
                "El formato del indice cambio: hay contenido desconocido antes de la primera tarjeta."
            )
        tarjetas = [
            contenido[inicio:fin]
            for inicio, fin in zip(comienzos, comienzos[1:] + [len(contenido)])
        ]
    return html_indice[:inicio_grid], tarjetas, html_indice[fin_grid:]


def _nombre_tarjeta(tarjeta):
    encontrado = re.search(r"<h2>(.*?)</h2>", tarjeta, flags=re.DOTALL)
    if not encontrado:
        raise ValueError(
            "El formato del indice cambio: se encontro una tarjeta sin <h2>."
        )
    return html.unescape(encontrado.group(1))


def _tarjetas_por_nombre(tarjetas, origen):
    por_nombre = {}
    for tarjeta in tarjetas:
        nombre = _nombre_tarjeta(tarjeta)
        if nombre in por_nombre:
            raise ValueError(
                "El indice {} contiene dos tarjetas para '{}'.".format(origen, nombre)
            )
        por_nombre[nombre] = tarjeta
    return por_nombre


def _fin_de_linea(texto):
    return "\r\n" if "\r\n" in texto else "\n"


def _adaptar_fin_de_linea(texto, fin_de_linea):
    texto_lf = texto.replace("\r\n", "\n").replace("\r", "\n")
    return texto_lf if fin_de_linea == "\n" else texto_lf.replace("\n", "\r\n")


def fusionar_tarjetas(previo_html, nuevo_html, obras_a_actualizar):
    """Fusiona tarjetas siguiendo el orden y la envoltura del indice nuevo.

    Las obras indicadas y las que no existian antes usan la tarjeta nueva. El
    resto conserva literalmente su tarjeta previa salvo la fila ``Ultimo
    archivo``, que procede del escaneo nuevo del generador.
    """
    cabecera_nueva, tarjetas_nuevas, pie_nuevo = _trocear_tarjetas(nuevo_html)
    _, tarjetas_previas, _ = _trocear_tarjetas(previo_html)
    previas_por_nombre = _tarjetas_por_nombre(tarjetas_previas, "previo")
    _tarjetas_por_nombre(tarjetas_nuevas, "nuevo")
    eol = _fin_de_linea(nuevo_html)

    salida = []
    for tarjeta_nueva in tarjetas_nuevas:
        nombre = _nombre_tarjeta(tarjeta_nueva)
        tarjeta_previa = previas_por_nombre.get(nombre)
        if nombre in obras_a_actualizar or tarjeta_previa is None:
            salida.append(tarjeta_nueva)
            continue

        tarjeta_previa = _adaptar_fin_de_linea(tarjeta_previa, eol)
        fila_nueva = FILA_ULTIMO_ARCHIVO.search(tarjeta_nueva)
        fila_previa = FILA_ULTIMO_ARCHIVO.search(tarjeta_previa)
        if bool(fila_nueva) != bool(fila_previa):
            raise ValueError(
                "No se pudo conservar la tarjeta '{}': la fila 'Ultimo archivo' "
                "no coincide entre el indice previo y el nuevo.".format(nombre)
            )
        if fila_nueva and fila_previa:
            tarjeta_previa = FILA_ULTIMO_ARCHIVO.sub(
                lambda _m: fila_nueva.group(0), tarjeta_previa, count=1
            )
        salida.append(tarjeta_previa)

    return cabecera_nueva + "".join(salida) + pie_nuevo


def _indexar_resumen_por_carpeta(entradas, origen):
    if not isinstance(entradas, list):
        raise ValueError("El resumen {} no contiene una lista 'obras'.".format(origen))
    por_carpeta = {}
    for entrada in entradas:
        if not isinstance(entrada, dict) or not isinstance(entrada.get("carpeta"), str):
            raise ValueError(
                "El resumen {} contiene una entrada de obra sin 'carpeta'.".format(
                    origen
                )
            )
        carpeta = entrada["carpeta"]
        if carpeta in por_carpeta:
            raise ValueError(
                "El resumen {} contiene dos entradas para '{}'.".format(
                    origen, carpeta
                )
            )
        por_carpeta[carpeta] = entrada
    return por_carpeta


def _recalcular_totales_resumen(resumen):
    obras = resumen["obras"]
    porcentajes = []
    for obra in obras:
        if obra.get("pct_ponderado") is not None:
            porcentajes.append(obra["pct_ponderado"])
        elif obra.get("pct_estricto") is not None:
            porcentajes.append(obra["pct_estricto"])

    totales_nuevos = resumen.get("totales")
    if not isinstance(totales_nuevos, dict):
        raise ValueError("El resumen nuevo no contiene un objeto 'totales'.")
    totales = dict(totales_nuevos)
    totales.update(
        {
            "n_obras": len(obras),
            "n_con_panel": sum(bool(obra.get("con_panel")) for obra in obras),
            "n_con_datos_frescos": len(porcentajes),
            "avance_medio_ponderado": (
                round(sum(porcentajes) / len(porcentajes), 1)
                if porcentajes
                else None
            ),
            "bloqueos_totales": sum(
                obra["n_bloqueos"] for obra in obras if "n_bloqueos" in obra
            ),
            "obras_sin_cambios": sum(
                bool(obra["sin_cambios"])
                for obra in obras
                if "sin_cambios" in obra
            ),
        }
    )
    resumen["totales"] = totales


def fusionar_resumen_obras(previo, nuevo, carpetas_a_actualizar):
    """Conserva las entradas previas no pendientes en el orden del resumen nuevo."""
    if not isinstance(previo, dict) or not isinstance(nuevo, dict):
        raise ValueError("Los resumenes previo y nuevo deben ser objetos JSON.")
    previas = _indexar_resumen_por_carpeta(previo.get("obras"), "previo")
    nuevas = _indexar_resumen_por_carpeta(nuevo.get("obras"), "nuevo")

    fusionadas = []
    for carpeta, entrada_nueva in nuevas.items():
        entrada_previa = previas.get(carpeta)
        if carpeta in carpetas_a_actualizar or entrada_previa is None:
            fusionadas.append(entrada_nueva)
        else:
            fusionadas.append(entrada_previa)

    salida = dict(nuevo)
    salida["obras"] = fusionadas
    _recalcular_totales_resumen(salida)
    return salida


def _leer_bytes_si_existe(ruta):
    if not os.path.isfile(ruta):
        return None
    with open(ruta, "rb") as f:
        return f.read()


def _restaurar_archivo(ruta, contenido_previo):
    if contenido_previo is None:
        if os.path.exists(ruta):
            os.remove(ruta)
        return
    _escribir_bytes_atomico(ruta, contenido_previo)


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
    pendientes = cache.setdefault(PENDIENTES_FINALIZAR, [])
    if obra_id not in pendientes:
        pendientes.append(obra_id)
    _guardar_cache(cache)
    print("Cache actualizada para '{}' -> {}".format(obra_id, CACHE_PATH))
    print("Pendiente de finalizar: '{}'".format(obra_id))
    return resultados[0]


def finalizar():
    """Agrega los resultados cacheados de todas las obras y regenera
    index.html, resumen_obras.json y el registro de revisiones (una sola
    vez, barato: no reprocesa historial/priorización de ninguna obra)."""
    cache = _cargar_cache()
    pendientes = list(cache.get(PENDIENTES_FINALIZAR, []))
    pendientes_set = set(pendientes)
    obras_por_id = {obra["id"]: obra for obra in gt.OBRAS}
    for obra_id in pendientes:
        if obra_id not in obras_por_id:
            print(
                "[AVISO] La cache marca '{}' como pendiente, pero ya no esta en el "
                "registro de obras; no se actualizara ninguna tarjeta con ese id.".format(
                    obra_id
                )
            )

    resultados = []
    ids_actualizables = set()
    for obra in gt.OBRAS:
        r = cache.get(obra["id"])
        if r:
            resultados.append(r)
            if obra["id"] in pendientes_set:
                ids_actualizables.add(obra["id"])
        elif obra["id"] in pendientes_set:
            print(
                "[AVISO] '{}' esta pendiente de finalizar, pero no tiene resultado "
                "en la cache: se conservan su tarjeta y su entrada previas.".format(
                    obra["nombre"]
                )
            )

    nombres_a_actualizar = {
        obras_por_id[obra_id]["nombre"] for obra_id in ids_actualizables
    }
    carpetas_a_actualizar = {
        obras_por_id[obra_id]["carpeta_obra"] for obra_id in ids_actualizables
    }

    print("Obras con resultado cacheado: {} de {} registradas.".format(
        len(resultados), len(gt.OBRAS)))
    for r in resultados:
        print(" -", r["nombre"], "pct_ponderado=", r.get("pct_ponderado"))
    if not pendientes:
        print("Nada pendiente: se conservan todas las tarjetas.")

    index_previo_bytes = _leer_bytes_si_existe(INDEX_PATH)
    resumen_previo_bytes = _leer_bytes_si_existe(RESUMEN_PATH)

    try:
        _generar_index_original(resultados)
        _escribir_resumen_json_original(resultados)

        with open(INDEX_PATH, encoding="utf-8", newline="") as f:
            index_nuevo = f.read()
        if index_previo_bytes is None:
            index_fusionado = index_nuevo
        else:
            index_previo = index_previo_bytes.decode("utf-8")
            index_fusionado = fusionar_tarjetas(
                index_previo, index_nuevo, nombres_a_actualizar
            )

        with open(RESUMEN_PATH, encoding="utf-8") as f:
            resumen_nuevo = json.load(f)
        if resumen_previo_bytes is None:
            resumen_fusionado = resumen_nuevo
            _recalcular_totales_resumen(resumen_fusionado)
        else:
            resumen_previo = json.loads(resumen_previo_bytes.decode("utf-8"))
            resumen_fusionado = fusionar_resumen_obras(
                resumen_previo, resumen_nuevo, carpetas_a_actualizar
            )

        _, tarjetas_finales, _ = _trocear_tarjetas(index_fusionado)
        nombres_finales = [_nombre_tarjeta(tarjeta) for tarjeta in tarjetas_finales]
        if index_previo_bytes is None:
            nombres_previos = set()
        else:
            _, tarjetas_previas, _ = _trocear_tarjetas(index_previo)
            nombres_previos = {
                _nombre_tarjeta(tarjeta) for tarjeta in tarjetas_previas
            }
        actualizadas = [
            nombre
            for nombre in nombres_finales
            if nombre in nombres_a_actualizar or nombre not in nombres_previos
        ]
        conservadas = [
            nombre
            for nombre in nombres_finales
            if nombre not in nombres_a_actualizar and nombre in nombres_previos
        ]

        _escribir_texto_atomico(INDEX_PATH, index_fusionado)
        _escribir_texto_atomico(
            RESUMEN_PATH,
            json.dumps(resumen_fusionado, ensure_ascii=False, indent=2),
        )

        _publicar_registro_revisiones_original()
        cache[PENDIENTES_FINALIZAR] = []
        _guardar_cache(cache)
    except Exception as exc:
        errores_restauracion = []
        for ruta, contenido in (
            (INDEX_PATH, index_previo_bytes),
            (RESUMEN_PATH, resumen_previo_bytes),
        ):
            try:
                _restaurar_archivo(ruta, contenido)
            except Exception as exc_restauracion:
                errores_restauracion.append(
                    "{}: {}".format(ruta, exc_restauracion)
                )
        if errores_restauracion:
            raise RuntimeError(
                "Fallo al finalizar ({}); ademas no se pudo restaurar: {}".format(
                    exc, "; ".join(errores_restauracion)
                )
            ) from exc
        raise RuntimeError(
            "Fallo al finalizar; index.html y resumen_obras.json fueron "
            "restaurados: {}".format(exc)
        ) from exc

    print(
        "Tarjetas actualizadas:",
        ", ".join(actualizadas) if actualizadas else "(ninguna)",
    )
    print(
        "Tarjetas conservadas:",
        ", ".join(conservadas) if conservadas else "(ninguna)",
    )
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
