# -*- coding: utf-8 -*-
"""Mide una salida de prioridades para poder comparar antes/despues.

No es una prueba: es la regla con la que se demuestra que un cambio hace lo
que dice. En este proyecto el porcentaje redondeado es un criterio ciego, asi
que lo que se compara es el desglose: cuantas preguntas, cuantas unidades, en
cuantas ubicaciones y cuantas celdas.

Se usa desde test_linea_base_prioridades.py y a mano antes y despues de cada
cambio del motor.
"""
import json


def medir_prioridades(datos):
    """Resume una salida de prioridades_trabajos.json en cifras comparables."""
    datos = datos or {}
    items = datos.get('items') or []
    detalle = datos.get('detalle_items') or []
    # El edificio forma parte de la clave: Gernika tiene DOS portales con las
    # mismas plantas y las mismas letras de vivienda. Sin el, sus 32
    # ubicaciones se colapsaban en 16 y el antes/despues mentia.
    ubicaciones = {(d.get('edificio'), d.get('planta'), d.get('unidad'))
                   for d in detalle}
    return {
        'preguntas': (datos.get('resumen') or {}).get('preguntas_pendientes', 0),
        'unidades_verificar': sum(
            i.get('n_unidades', 0) for i in items
            if i.get('situacion') == 'VERIFICAR'),
        'unidades_listas': sum(
            i.get('n_unidades', 0) for i in items
            if i.get('situacion') == 'LISTO'),
        'unidades_no_vivienda': sum(
            i.get('n_unidades', 0) for i in items
            if i.get('ambito') != 'vivienda'),
        'ubicaciones': len(ubicaciones),
        'celdas': len(detalle),
    }


def medir_fichero(ruta):
    with open(ruta, encoding='utf-8') as f:
        return medir_prioridades(json.load(f))


def tajos_sin_orden(ruta_ficha):
    """Tajos de la base con el centinela 9999 (sin posicion confirmada).

    Un tajo sin orden no tiene respuesta a 'cual va primero': se ordena
    alfabeticamente al final. En Orueta habia 18 el 11/08/2026.
    """
    with open(ruta_ficha, encoding='utf-8') as f:
        ficha = json.load(f)
    detalle = (ficha.get('tajos') or {}).get('detalle') or []
    return sorted(t['id'] for t in detalle if (t.get('orden') or 9999) >= 9999)


def celdas_por_categoria(datos):
    """Cuantas celdas hay en cada categoria de la cascada de clasificacion."""
    conteo = {}
    for item in (datos or {}).get('detalle_items') or []:
        categoria = item.get('categoria', '?')
        conteo[categoria] = conteo.get(categoria, 0) + 1
    return conteo
