# -*- coding: utf-8 -*-
"""
VALIDAR REVISIÓN PDF — dry-run antes de aceptar un PDF como revisión oficial
--------------------------------------------------------------------------
Lee un PDF candidato (en cualquier ruta, no hace falta que ya esté en
REVISIONES) usando el motor genérico `lector_hoja_tajos_pdf.py` + los
resolutores propios del adaptador de la obra, y compara el resultado contra
la última revisión ya cargada en el historial de esa obra. Sirve para
detectar, ANTES de aceptar el fichero como oficial:

  1. Cuántas celdas manuscritas quedan sin corregir (candidatas a
     '<pdf>.correcciones.json').
  2. Ubicaciones (edificio/planta/vivienda) que aparecen en la última
     revisión conocida y NO aparecen en el PDF nuevo — posible indicio de
     que cambió la estructura de la hoja (como ZR1.2 PB: A/B/C -> PORTAL
     el 25/07/2026) en vez de que el trabajo realmente "desapareciera".
  3. Ubicaciones nuevas que no existían antes (edificios/plantas que se
     añaden por primera vez).

CONTRATO con cada adaptador (ver receta en CLAUDE.md): para que este
validador funcione con la obra X, `adaptadores/adaptador_x.py` debe exponer:
  - `_portal_id_pdf(texto_banner)`      -> id de portal interno | None
  - `_identificar_tajo_pdf(etiqueta)`   -> alias corto de tajo | None
  - `PORTAL_NOMBRE_PDF` / `PLANTA_NOMBRE_PDF` (dicts id -> nombre mostrado)
Estos son exactamente los nombres que ya usa adaptador_mungia.py.

Uso:
    python3 validar_revision_pdf.py <obra_id> <ruta_al_pdf_candidato>

No escribe nada. Es solo lectura/diagnóstico.
"""
import os
import sys
import importlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOTOR_IA_DIR = os.path.normpath(os.path.join(BASE_DIR, os.pardir, "SAGARDE OBRAS ABIERTAS", "_SISTEMA INFORME SAGARDE IA"))
sys.path.insert(0, MOTOR_IA_DIR)
sys.path.insert(0, os.path.join(MOTOR_IA_DIR, "adaptadores"))
import lector_hoja_tajos_pdf as lector_pdf  # noqa: E402
import generar_todos as gt  # noqa: E402


def _ubicaciones(registros):
    """Set de (building, floor, unit) — sin task, para ver el 'mapa' de
    ubicaciones que cubre una revision, independientemente del tajo."""
    return {(r['building'], r['floor'], r['unit']) for r in registros}


def validar(obra_id, ruta_pdf):
    obra_cfg = next((o for o in gt.OBRAS if o['id'] == obra_id), None)
    if not obra_cfg:
        disponibles = ", ".join(o['id'] for o in gt.OBRAS)
        print("[ERROR] Obra '{}' no está registrada en OBRAS de generar_todos.py.".format(obra_id))
        print("Disponibles: {}".format(disponibles))
        print("Si es una obra nueva en PDF, primero hay que construir su adaptador")
        print("siguiendo la receta de _MOTOR_SAGARDE/CLAUDE.md.")
        return

    adaptador = importlib.import_module(obra_cfg['adaptador'])
    for nombre_attr in ('_portal_id_pdf', '_identificar_tajo_pdf', 'PORTAL_NOMBRE_PDF', 'PLANTA_NOMBRE_PDF'):
        if not hasattr(adaptador, nombre_attr):
            print("[ERROR] {} no tiene '{}'. Este validador solo funciona con adaptadores".format(
                obra_cfg['adaptador'], nombre_attr))
            print("que sigan el contrato de PDF descrito en CLAUDE.md (igual que adaptador_mungia.py).")
            return

    if not os.path.isfile(ruta_pdf):
        print("[ERROR] No existe el fichero: {}".format(ruta_pdf))
        return

    print("=== Leyendo candidato: {} ===".format(os.path.basename(ruta_pdf)))
    registros_dict = lector_pdf.parsear_pdf(
        ruta_pdf,
        identificar_portal=adaptador._portal_id_pdf,
        identificar_tajo=adaptador._identificar_tajo_pdf,
        nombre_log='validar_revision_pdf',
    )
    if not registros_dict:
        print("[AVISO] El PDF no produjo ningún registro reconocible. Revisar que la")
        print("plantilla/tabla coincide con lo que espera el adaptador de esta obra.")
        return

    total = len(registros_dict)
    pendientes_manuscritos = sum(1 for v in registros_dict.values() if v == '')
    print("Total celdas leídas: {}".format(total))
    print("Celdas manuscritas sin corrección (quedarán pendiente): {}".format(pendientes_manuscritos))
    if pendientes_manuscritos:
        print("  -> si alguna de estas SÍ tiene marca a mano, crea '<pdf>.correcciones.json'")
        print("     con las claves 'portal__planta__tajo__vivienda' verificadas visualmente.")

    # Construir registros "de verdad" (con nombres) para comparar ubicaciones
    registros = []
    for (portal_id, planta_id, tajo_id, viv), valor in registros_dict.items():
        building = adaptador.PORTAL_NOMBRE_PDF.get(portal_id)
        floor = adaptador.PLANTA_NOMBRE_PDF.get(planta_id)
        if building and floor:
            registros.append({'building': building, 'floor': floor, 'unit': viv})

    ubicaciones_nuevas = _ubicaciones(registros)

    print()
    print("=== Comparando contra la última revisión ya cargada ===")
    try:
        historial = adaptador.cargar_historial()
    except Exception as e:
        print("[AVISO] No se pudo cargar el historial existente para comparar: {}".format(e))
        historial = []

    if not historial:
        print("Esta obra no tiene revisiones previas cargadas — no hay drift que comparar")
        print("(es la primera revisión, o el historial existente está vacío).")
        return

    fecha_anterior, registros_anteriores = historial[-1]
    ubicaciones_anteriores = _ubicaciones(registros_anteriores)

    desaparecen = sorted(ubicaciones_anteriores - ubicaciones_nuevas)
    aparecen = sorted(ubicaciones_nuevas - ubicaciones_anteriores)

    print("Última revisión cargada: {} ({} ubicaciones únicas)".format(
        fecha_anterior, len(ubicaciones_anteriores)))
    print("Candidato nuevo: {} ubicaciones únicas".format(len(ubicaciones_nuevas)))

    if desaparecen:
        print()
        print("⚠ {} ubicación(es) que SÍ estaban en la revisión anterior y ya NO aparecen".format(len(desaparecen)))
        print("  en el candidato (puede ser trabajo terminado y omitido, o un cambio de")
        print("  estructura de la hoja que hay que confirmar — como pasó con ZR1.2 PB el 25/07/2026):")
        for building, floor, unit in desaparecen[:30]:
            print("   - {} / planta {} / {}".format(building, floor, unit))
        if len(desaparecen) > 30:
            print("   ... y {} más".format(len(desaparecen) - 30))
    else:
        print("Sin ubicaciones desaparecidas respecto a la revisión anterior.")

    if aparecen:
        print()
        print("+ {} ubicación(es) nueva(s) que no estaban antes:".format(len(aparecen)))
        for building, floor, unit in aparecen[:30]:
            print("   - {} / planta {} / {}".format(building, floor, unit))
        if len(aparecen) > 30:
            print("   ... y {} más".format(len(aparecen) - 30))

    print()
    if desaparecen or aparecen:
        print("=> Antes de aceptar este PDF como revisión oficial, confirmar con obra si")
        print("   este cambio de ubicaciones es real (fusión/renombrado de unidades, etc.)")
        print("   o si es un fallo de la hoja. Ver punto 6 del protocolo en CLAUDE.md.")
    else:
        print("=> Sin cambios de estructura detectados. Solo falta confirmar las celdas")
        print("   manuscritas sin corregir (si las hay) antes de aceptarlo como oficial.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(1)
    validar(sys.argv[1], sys.argv[2])
