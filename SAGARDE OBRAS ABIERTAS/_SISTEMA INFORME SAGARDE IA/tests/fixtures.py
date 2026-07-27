# -*- coding: utf-8 -*-
"""Datos de juguete para las pruebas de ficha_obra.

Una obra minima pero realista: 1 bloque, 1 portal ('P1'), 2 plantas
('PB' y '1'), 2 viviendas por planta ('A' y 'B'), y 2 tajos.
"""


def ficha_minima():
    return {
        'version': 1,
        'id': 'pruebas',
        'modo': 'hibrida',
        'identidad': {'nombre': 'OBRA DE PRUEBAS', 'carpeta': 'OBRA DE PRUEBAS',
                      'tipo_obra': 'viviendas', '_meta': {}},
        'estructura': {
            'bloques': [{
                'id': 'b1', 'nombre': 'Bloque 1',
                'portales': [{
                    'id': 'p1', 'nombre': 'P1', 'referencia': 'P1',
                    'plantas': [
                        {'id': 'pb', 'nombre': 'PB', 'orden': 0, 'ubicaciones': [
                            {'id': 'A', 'tipo': 'vivienda', 'origen': 'campo'},
                            {'id': 'B', 'tipo': 'vivienda', 'origen': 'campo'},
                        ]},
                        {'id': '1', 'nombre': '1', 'orden': 1, 'ubicaciones': [
                            {'id': 'A', 'tipo': 'vivienda', 'origen': 'campo'},
                            {'id': 'B', 'tipo': 'vivienda', 'origen': 'campo'},
                        ]},
                    ],
                }],
            }],
            'alias_historico': {},
            '_meta': {},
        },
        'tajos': {
            'aplicables': ['tubeado', 'cableado'],
            'detalle': [
                {'id': 'tubeado', 'nombre': 'Tubeado', 'ambito': 'vivienda',
                 'propiedad': 'propio', 'fase': 'Interior', 'orden': 10},
                {'id': 'cableado', 'nombre': 'Cableado', 'ambito': 'vivienda',
                 'propiedad': 'propio', 'fase': 'Interior', 'orden': 20},
            ],
            '_meta': {},
        },
        'estados': {},
        'revisiones': [], 'dudas': [],
        'materiales': {}, 'documentos': {}, 'contactos': [],
    }


def item(edificio='P1', planta='PB', unidad='A', tarea='tubeado',
         estado='X', trabajo='Tubeado', ambito='vivienda', orden=10):
    return {
        'tarea_id': tarea, 'trabajo': trabajo, 'ambito': ambito,
        'propiedad': 'propio', 'fase_nombre': 'Interior',
        'orden_ejecucion': orden, 'edificio': edificio, 'planta': planta,
        'unidad': unidad, 'estado_actual': estado, 'ultima_fecha': '27/07/2026',
    }


def prioridades(items, revision='27/07/2026'):
    return {'revision': revision, 'generado': '27/07/2026 18:00',
            'detalle_items': list(items), 'resumen': {}}
