# -*- coding: utf-8 -*-
"""Cierre de expediente: ensayos, OCA, CIE/Boletin y Libro del Edificio.

Datos de obra a mano, al margen de la rejilla ubicaciones x tajos. No lo
toca ningun adaptador, no lo siembra sembrar_reglas, no lo lee el generador
de hojas ni el priorizador. Panel e informe ejecutivo lo leen para mostrar
el cierre administrativo de la obra, no su avance fisico.
"""
from datetime import datetime
import argparse
import json
import os

HITOS_ORDEN = (
    "ensayos_instrumentales",
    "inspeccion_oca",
    "cie_boletin",
    "libro_edificio",
)

HITOS_NOMBRE = {
    "ensayos_instrumentales": "Ensayos instrumentales",
    "inspeccion_oca": "Inspección OCA",
    "cie_boletin": "CIE / Boletín eléctrico",
    "libro_edificio": "Libro del Edificio",
}

ESTADOS_POR_HITO = {
    "ensayos_instrumentales": ("pendiente", "hecho", "no_aplica"),
    "inspeccion_oca": ("pendiente", "favorable", "condicionada", "negativa", "no_aplica"),
    "cie_boletin": ("pendiente", "hecho", "no_aplica"),
    "libro_edificio": ("pendiente", "hecho", "no_aplica"),
}


def _hito_vacio():
    return {"estado": "pendiente", "fecha": None, "nota": ""}


def vacio(obra=""):
    return {
        "obra": obra,
        "actualizado": None,
        "hitos": {h: _hito_vacio() for h in HITOS_ORDEN},
    }


def cargar(ruta_json, obra=""):
    """Lee cierre_expediente.json. Nunca lanza: fichero ausente o corrupto
    se trata como "sin datos todavia", con un aviso legible en el segundo
    valor devuelto. No se inventa ni se corrige un estado desconocido: se
    conserva tal cual y se avisa, para no ocultar un dato raro."""
    avisos = []
    base = vacio(obra)
    if not os.path.isfile(ruta_json):
        return base, avisos

    try:
        with open(ruta_json, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError) as e:
        avisos.append(
            f"cierre_expediente.json no se pudo leer ({e}); se trata como sin datos.")
        return base, avisos

    if not isinstance(datos, dict):
        avisos.append(
            "cierre_expediente.json no tiene la forma esperada (no es un "
            "objeto); se trata como sin datos.")
        return base, avisos

    base["obra"] = datos.get("obra") or obra
    base["actualizado"] = datos.get("actualizado")
    hitos_guardados = datos.get("hitos")
    if not isinstance(hitos_guardados, dict):
        avisos.append(
            "cierre_expediente.json: 'hitos' no es un objeto; se trata como sin datos.")
        return base, avisos

    for clave, valor in hitos_guardados.items():
        if clave not in ESTADOS_POR_HITO:
            avisos.append(f"cierre_expediente.json: hito desconocido '{clave}', se ignora.")
            continue
        if not isinstance(valor, dict):
            avisos.append(
                f"cierre_expediente.json: el hito '{clave}' no tiene la forma "
                f"esperada, se ignora.")
            continue
        estado = valor.get("estado", "pendiente")
        if estado not in ESTADOS_POR_HITO[clave]:
            avisos.append(
                f"cierre_expediente.json: '{clave}' tiene un estado no "
                f"reconocido ('{estado}'); revisar a mano.")
        base["hitos"][clave] = {
            "estado": estado,
            "fecha": valor.get("fecha"),
            "nota": valor.get("nota", ""),
        }
    return base, avisos


def guardar(ruta_json, datos):
    directorio = os.path.dirname(ruta_json)
    if directorio:
        os.makedirs(directorio, exist_ok=True)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def actualizar_hito(ruta_json, obra, hito, estado, fecha=None, nota=""):
    """Cambia un hito y guarda. Lanza ValueError si el hito o el estado no
    son validos: es una accion explicita de quien lo llama, no una lectura
    pasiva, asi que aqui si conviene fallar alto en vez de avisar y seguir."""
    if hito not in ESTADOS_POR_HITO:
        raise ValueError(
            f"hito desconocido: {hito!r}. Validos: {', '.join(HITOS_ORDEN)}")
    if estado not in ESTADOS_POR_HITO[hito]:
        raise ValueError(
            f"estado {estado!r} no valido para {hito!r}. "
            f"Validos: {', '.join(ESTADOS_POR_HITO[hito])}")
    datos, _avisos = cargar(ruta_json, obra=obra)
    datos["obra"] = obra or datos.get("obra", "")
    datos["hitos"][hito] = {"estado": estado, "fecha": fecha, "nota": nota}
    datos["actualizado"] = datetime.now().strftime("%d/%m/%Y")
    guardar(ruta_json, datos)
    return datos


def main():
    from registro_obras import resolver_obra

    parser = argparse.ArgumentParser(
        description="Actualiza un hito de cierre de expediente de una obra.")
    parser.add_argument("obra", help="nombre oficial o alias de la obra (registro_obras.py)")
    parser.add_argument("--hito", required=True, choices=HITOS_ORDEN)
    parser.add_argument("--estado", required=True)
    parser.add_argument("--fecha", default=None, help="DD/MM/AAAA")
    parser.add_argument("--nota", default="")
    args = parser.parse_args()

    obra = resolver_obra(args.obra)
    if obra is None:
        print(f"[ERROR] No hay obra registrada con el nombre '{args.obra}'.")
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    obras_abiertas_dir = os.path.dirname(base_dir)
    carpeta_abs = os.path.join(obras_abiertas_dir, obra["carpeta_obra"])
    ruta_json = os.path.join(carpeta_abs, "INFORME SAGARDE IA", "cierre_expediente.json")

    try:
        datos = actualizar_hito(
            ruta_json, obra["nombre"], args.hito, args.estado,
            fecha=args.fecha, nota=args.nota)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return

    print(f"[OK] {HITOS_NOMBRE[args.hito]} -> {args.estado} ({obra['nombre']})")
    print(json.dumps(datos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
