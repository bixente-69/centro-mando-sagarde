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
        'materiales_rel': os.path.join(
            'REVISIONES', 'hoja de entrega de materiales OBRA PRUEBA.xlsx'),
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
