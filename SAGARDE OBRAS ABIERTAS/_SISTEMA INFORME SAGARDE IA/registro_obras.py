# -*- coding: utf-8 -*-
"""Registro único de las obras abiertas que procesa Sagarde IA.

El panel, el generador de hojas y el informe ejecutivo importan esta misma
lista. Dar de alta una obra aquí basta para que los tres caminos la conozcan.
"""
import os


OBRAS = [
    {
        'id': 'gernika',
        'nombre': '2025 GERNIKA 32V',
        'aliases': ['GERNIKA'],
        'subtitulo': 'Electricidad y telecomunicaciones · 1 bloque, 2 portales, 32 viviendas',
        'adaptador': 'adaptador_gernika',
        'carpeta_obra': '2025 GERNIKA 32V',
        'bloque_revision': 'Bloque 1',
        'materiales_rel': os.path.join(
            'REVISIONES', 'hoja de entrega de materiales GERNIKA.xlsx'),
    },
    {
        'id': 'mungia',
        'nombre': '2026 MUNGIA ACR NEINOR',
        'aliases': ['MUNGIA'],
        'subtitulo': 'Electricidad y telecomunicaciones · Edificios ZR1.1 / ZR1.2',
        'adaptador': 'adaptador_mungia',
        'carpeta_obra': '2026 MUNGIA ACR NEINOR',
        'bloque_revision': 'ZR1',
        'materiales_rel': os.path.join(
            'REVISIONES', 'hoja de entrega de materiales MUNGIA.xlsx'),
    },
    {
        'id': 'bolueta',
        'nombre': '2026 BOLUETA ACR',
        'aliases': ['BOLUETA'],
        'subtitulo': 'Electricidad y telecomunicaciones · Portal único, B+23',
        'adaptador': 'adaptador_bolueta',
        'carpeta_obra': '2026 BOLUETA ACR',
        'bloque_revision': 'Bolueta',
        'alias_portales_revision': {'BOLUETA': 'Portal único'},
        # Las hojas nuevas incluyen cuartos técnicos, cuartos ligeros y
        # cubierta bajo una planta virtual que no se deduce de B+23.
        'mapa_plantas_revision_html': {'zesp': 'zesp'},
        'materiales_rel': os.path.join(
            'REVISIONES', 'hoja de entrega de materiales BOLUETA.xlsx'),
    },
    {
        'id': 'gorliz',
        'nombre': '2026 GORLIZ HOSPITAL',
        'aliases': ['GORLIZ'],
        'subtitulo': 'Electricidad y telecomunicaciones · Hospital de Gorliz',
        'adaptador': 'adaptador_gorliz',
        'carpeta_obra': '2026 GORLIZ HOSPITAL',
        'bloque_revision': 'Hospital de Gorliz',
        # El adaptador admite historial vacío hasta que llegue la primera
        # revisión oficial de la obra.
        'materiales_rel': os.path.join(
            'REVISIONES', 'hoja de entrega de materiales GORLIZ.xlsx'),
    },
    {
        # Obra ficticia. Sirve para verificar la lectura de hojas marcadas en
        # obra sin tocar datos reales: como se controlan sus dos revisiones,
        # la respuesta correcta se conoce de antemano. Nacio de su propia
        # hoja de alta (REVISION OBRA PRUEBA 05082026.pdf), en blanco, que es
        # la que fija su distribucion: 2 bloques, 3 portales, 31 ubicaciones.
        'id': 'prueba',
        'nombre': '2026 OBRA PRUEBA',
        'aliases': ['OBRA PRUEBA'],
        'subtitulo': 'Obra de pruebas · No es una obra real · 2 bloques, 3 portales, 31 ubicaciones',
        'adaptador': 'adaptador_prueba',
        'carpeta_obra': '2026 OBRA PRUEBA',
        'bloque_revision': 'BLOQUE 1',
        # La hoja HTML enumera los portales en el orden de la estructura:
        # B1/P1, B1/P2 y B2/P1. Los dos ultimos no se pueden deducir solo
        # por el nombre "PORTAL" porque el orden natural alternativo los
        # intercambia. El adaptador exige este mapa explicito antes de
        # aceptar sus celdas; nunca debe adivinar una ubicacion plausible.
        'mapa_portales_revision_html': {
            'src_prueba_p1': 'p1',
            'src_prueba_p2': 'p2',
            'src_prueba_p3': 'p3',
        },
        'materiales_rel': os.path.join(
            'REVISIONES', 'hoja de entrega de materiales OBRA PRUEBA.xlsx'),
    },
    {
        # Alta nativa el 27/09/2026 desde su primera hoja de distribución HTML.
        # Promoción de 30 viviendas con garajes y trasteros (proyecto "makia").
        'id': 'olabeaga',
        'nombre': '2026 OLABEAGA BILBAO',
        'aliases': ['OLABEAGA'],
        'subtitulo': ('Electricidad y telecomunicaciones · 1 bloque, 3 portales, '
                       '30 viviendas, locales comerciales y garajes'),
        'adaptador': 'adaptador_olabeaga',
        'carpeta_obra': '2026 OLABEAGA BILBAO',
        'bloque_revision': 'Bloque 1',
        'mapa_portales_revision_html': {
            'p_muk0ktg3_2': 'p1',
            'p_muk0mekn_11': 'p2',
            'p_muk0mey7_18': 'p3',
        },
        'mapa_plantas_revision_html': {
            'f_muk0ktg3_3': 'pb',
            'f_muk0ktg3_4': '1',
            'f_muk0ktg3_5': '2',
            'f_muk0ktg3_6': '3',
            'f_muk0ktg3_7': '4',
            'f_muk0mekn_12': 'pb',
            'f_muk0mekn_13': '1',
            'f_muk0mekn_14': '2',
            'f_muk0mekn_15': '3',
            'f_muk0mekn_16': '4',
            'f_muk0tpsy_32': 'duplx_atico',
            'f_muk0mey7_19': 'pb',
            'f_muk0mey7_20': '1',
            'f_muk0mey7_21': '2',
            'f_muk0mey7_22': '3',
            'f_muk0mey7_23': '4',
            'zesp': 'zesp',
        },
        'materiales_rel': os.path.join(
            'REVISIONES', 'hoja de entrega de materiales OLABEAGA.xlsx'),
    },
    {
        # Alta el 05/10/2026 en modo Gorliz (sin ficha_obra.json): solo existe el
        # proyecto de ejecucion (REBT, ICT, fotovoltaica), no hay hoja de
        # distribucion ni estado de obra. Bloque 1 de la UE-12 Rontegui.
        # La estructura propuesta esta en INFORME_TECNICO_OBRA_BARAKALDO.md;
        # los mapas de ids de la hoja HTML se declaran el dia que llegue la hoja.
        'id': 'barakaldo',
        'nombre': '2026 BARAKALDO 104V OBRAS ESPECIALES',
        'aliases': ['BARAKALDO', 'BARAKALDO 104V'],
        'subtitulo': ('Electricidad y telecomunicaciones · 1 bloque, 2 portales, '
                       '104 viviendas VPO y garaje de 3 sotanos'),
        'adaptador': 'adaptador_barakaldo',
        'carpeta_obra': '2026 BARAKALDO 104V OBRAS ESPECIALES',
        'bloque_revision': 'Bloque 1',
        'materiales_rel': os.path.join(
            'REVISIONES', 'hoja de entrega de materiales BARAKALDO.xlsx'),
    },
]


def _clave_nombre(nombre):
    return str(nombre or '').strip().casefold()


def mapa_por_nombre():
    """Devuelve nombre oficial/alias -> configuración de la obra."""
    resultado = {}
    for obra in OBRAS:
        for nombre in [obra['nombre'], *obra.get('aliases', [])]:
            clave = _clave_nombre(nombre)
            if clave in resultado:
                raise ValueError(
                    f"Nombre o alias de obra duplicado en el registro: {nombre}")
            resultado[clave] = obra
    return resultado


_POR_NOMBRE = mapa_por_nombre()


def resolver_obra(nombre):
    """Resuelve un nombre oficial o alias, sin distinguir mayúsculas."""
    return _POR_NOMBRE.get(_clave_nombre(nombre))
