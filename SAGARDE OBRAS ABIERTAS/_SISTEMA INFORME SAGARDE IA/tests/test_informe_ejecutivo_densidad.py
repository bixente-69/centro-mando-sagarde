# -*- coding: utf-8 -*-
"""Contrato de maquetacion de una pagina por ambito del informe ejecutivo."""
import inspect
import io
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(SISTEMA_DIR))
sys.path.insert(0, SISTEMA_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'scripts'))

from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, String
from reportlab.platypus import Paragraph, Spacer, Table

import cierre_expediente as ce
import generar_informe_ejecutivo as gie
import motor_informes


TOKEN_NUMERICO = re.compile(r'\d+(?:\.\d+)?%|\d+/\d+')


def _texto_de_flowable(valor):
    """Texto visible de Paragraph/Table/Drawing sin escribir un PDF."""
    if isinstance(valor, Paragraph):
        return valor.getPlainText()
    if isinstance(valor, Table):
        return ' '.join(
            _texto_de_flowable(celda)
            for fila in valor._cellvalues
            for celda in fila
        )
    if isinstance(valor, Drawing):
        return ' '.join(
            str(elemento.text)
            for elemento in valor.contents
            if isinstance(elemento, String)
        )
    if isinstance(valor, (list, tuple)):
        return ' '.join(_texto_de_flowable(x) for x in valor)
    return str(valor or '')


def _ficha_fixture():
    tajos = []
    for indice in range(1, 13):
        tajos.append({
            'id': f'propio_{indice:02d}',
            'nombre': f'Tajo propio {indice:02d}',
            'propiedad': 'propio',
            'fase': f'Fase {((indice - 1) % 6) + 1}',
            'orden': indice,
        })
    for indice in range(1, 7):
        tajos.append({
            'id': f'externo_{indice:02d}',
            'nombre': f'Condicionante externo {indice:02d}',
            'propiedad': 'externo',
            'fase': 'Condicionantes',
            'orden': 100 + indice,
        })
    for indice in range(1, 5):
        tajos.append({
            'id': f'garaje_{indice:02d}',
            'nombre': f'Tajo garaje {indice:02d}',
            'propiedad': 'propio',
            'fase': 'Garaje',
            'orden': 200 + indice,
        })
    return {
        'identidad': {
            'cliente': 'Cliente de prueba',
            'direccion': 'Calle de la Maquetacion 1, Bilbao',
        },
        'estructura': {'bloques': [{
            'id': 'b1', 'nombre': 'Bloque 1', 'portales': [
                {'id': 'p1', 'nombre': 'P1', 'referencia': 'P1',
                 'plantas': [
                     {'id': 'pb', 'nombre': 'PB', 'orden': 0,
                      'ubicaciones': [{'id': 'A', 'tipo': 'vivienda'}]},
                     {'id': 'zesp', 'nombre': 'Zonas especiales', 'orden': 99,
                      'ubicaciones': [{
                          'id': 'ze1', 'nombre': 'RITI principal',
                          'tipo': 'cuarto_tecnico',
                      }]},
                 ]},
                {'id': 'p2', 'nombre': 'P2', 'referencia': 'P2',
                 'plantas': [{
                     'id': 'pb', 'nombre': 'PB', 'orden': 0,
                     'ubicaciones': [{'id': 'B', 'tipo': 'vivienda'}],
                 }]},
            ],
        }]},
        'tajos': {'detalle': tajos},
    }


def _snapshot_vivienda():
    filas = []
    for indice in range(1, 13):
        nombre = f'Tajo propio {indice:02d}'
        estado_p1 = ('X', 'M', '')[(indice - 1) % 3]
        estado_p2 = '/' if indice % 2 == 0 else ''
        filas.extend([
            {'task': nombre, 'building': 'P1', 'floor': 'PB',
             'unit': 'A', 'status': estado_p1},
            {'task': nombre, 'building': 'P2', 'floor': 'PB',
             'unit': 'B', 'status': estado_p2},
        ])
    filas.extend([
        {'task': 'Tajo propio 01', 'building': 'P1',
         'floor': 'Zonas especiales', 'unit': 'ze1', 'status': 'X'},
        {'task': 'Tajo propio 02', 'building': 'P1',
         'floor': 'Zonas especiales', 'unit': 'ze1', 'status': 'M'},
    ])
    return filas


def _snapshot_zonas(snapshot):
    return [r for r in snapshot if r['floor'] == 'Zonas especiales']


def _snapshot_garaje():
    estados = ('X', 'M', '/', '')
    return [
        {'task': f'Tajo garaje {i:02d}', 'building': 'Garaje 1',
         'floor': 'S-1', 'unit': f'Zona {i}', 'status': estado}
        for i, estado in enumerate(estados, 1)
    ]


def _historial(snapshot):
    base = [r for r in snapshot]
    fechas_estados = (
        ('01/09/2026', ''),
        ('08/09/2026', '/'),
        ('15/09/2026', 'M'),
    )
    historial = []
    for fecha, estado in fechas_estados:
        historial.append((fecha, [{**r, 'status': estado} for r in base]))
    historial.append(('22/09/2026', base))
    return historial


def _prioridades_principales(snapshot):
    detalle = []
    for indice in range(1, 8):
        detalle.append({
            'tarea_id': f'propio_{indice:02d}',
            'trabajo': f'Tajo propio {indice:02d}',
            'propiedad': 'propio', 'categoria': 'VIABLE',
            'edificio': 'P1', 'planta': 'PB', 'unidad': 'A',
            'estado': '', 'fase_nombre': f'Fase {((indice - 1) % 6) + 1}',
            'orden_ejecucion': indice,
        })
    for indice in range(1, 7):
        tajo = indice + 6
        detalle.append({
            'tarea_id': f'propio_{tajo:02d}',
            'trabajo': f'Tajo propio {tajo:02d}',
            'propiedad': 'propio', 'categoria': 'BLOQUEADO',
            'edificio': 'P2', 'planta': 'PB', 'unidad': 'B',
            'estado': '', 'fase_nombre': f'Fase {((tajo - 1) % 6) + 1}',
            'orden_ejecucion': tajo,
            'dependencias_detalle': [{
                'id': f'externo_{indice:02d}',
                'nombre': f'Condicionante externo {indice:02d}',
                'estado': 'Pendiente', 'cumplida': False,
            }],
        })
    # Las dos celdas de zonas especiales existen tambien en la prioridad
    # principal, igual que en la ficha real de vivienda.
    for fila in _snapshot_zonas(snapshot):
        detalle.append({
            'tarea_id': 'propio_01' if fila['task'].endswith('01') else 'propio_02',
            'trabajo': fila['task'], 'propiedad': 'propio',
            'categoria': 'TERMINADO' if fila['status'] == 'X' else 'VIABLE',
            'edificio': fila['building'], 'planta': fila['floor'],
            'unidad': fila['unit'], 'estado': fila['status'],
            'fase_nombre': 'Fase 1', 'orden_ejecucion': 1,
        })
    return {'detalle_items': detalle}


def _prioridades_de_snapshot(snapshot, prefijo):
    return {'detalle_items': [
        {
            'tarea_id': (f'garaje_{indice:02d}' if prefijo == 'garaje'
                         else f'propio_{indice:02d}'),
            'trabajo': fila['task'], 'propiedad': 'propio',
            'categoria': 'TERMINADO' if fila['status'] == 'X' else 'VIABLE',
            'edificio': fila['building'], 'planta': fila['floor'],
            'unidad': fila['unit'], 'estado': fila['status'],
            'fase_nombre': 'Garaje' if prefijo == 'garaje' else 'Fase 1',
            'orden_ejecucion': indice,
        }
        for indice, fila in enumerate(snapshot, 1)
    ]}


def _cierre_fixture():
    cierre = ce.vacio('OBRA DENSIDAD')
    cierre['actualizado'] = '22/09/2026'
    cierre['hitos']['ensayos_instrumentales'].update(
        estado='hecho', fecha='20/09/2026', nota='Acta firmada')
    cierre['hitos']['inspeccion_oca'].update(
        estado='favorable', fecha='21/09/2026', nota='Sin defectos')
    return cierre


def _fixture_completo():
    snapshot = _snapshot_vivienda()
    zesp = _snapshot_zonas(snapshot)
    garaje = _snapshot_garaje()
    return {
        'ficha': _ficha_fixture(),
        'snapshot': snapshot,
        'zesp': zesp,
        'garaje': garaje,
        'historial': _historial(snapshot),
        'prioridades': _prioridades_principales(snapshot),
        'prioridades_zesp': _prioridades_de_snapshot(zesp, 'zesp'),
        'prioridades_garaje': _prioridades_de_snapshot(garaje, 'garaje'),
        'cierre': _cierre_fixture(),
    }


def _fixture_estres():
    """Volumen comparable al de una obra grande, sin depender de datos reales."""
    tajos = [
        {
            'id': f'propio_{indice:02d}',
            'nombre': f'Tajo propio de estres {indice:02d}',
            'propiedad': 'propio',
            'fase': f'Fase de produccion {((indice - 1) % 20) + 1:02d}',
            'orden': indice,
        }
        for indice in range(1, 31)
    ]
    tajos.extend({
        'id': f'externo_{indice:02d}',
        'nombre': f'Condicionante externo de estres {indice:02d}',
        'propiedad': 'externo',
        'fase': 'Condicionantes',
        'orden': 100 + indice,
    } for indice in range(1, 13))

    portales = [
        ('ref_a1', 'Portal 1', 'Bloque Norte'),
        ('ref_a2', 'Portal 2', 'Bloque Norte'),
        ('ref_b1', 'Portal 1', 'Bloque Sur'),
    ]
    bloques = []
    for bloque_nombre in ('Bloque Norte', 'Bloque Sur'):
        portales_bloque = []
        for referencia, portal_nombre, bloque in portales:
            if bloque != bloque_nombre:
                continue
            ubicaciones = [
                {'id': f'{referencia}_v{i:02d}', 'nombre': f'Vivienda {i:02d}',
                 'tipo': 'vivienda'}
                for i in range(1, 16)
            ]
            plantas = [{
                'id': f'{referencia}_pb', 'nombre': 'PB', 'orden': 0,
                'ubicaciones': ubicaciones,
            }]
            if referencia == 'ref_a1':
                plantas.append({
                    'id': 'zesp', 'nombre': 'Zonas especiales', 'orden': 99,
                    'ubicaciones': [
                        {'id': f'ze{i:02d}',
                         'nombre': f'Zona especial tecnica {i:02d}',
                         'tipo': 'cuarto_tecnico'}
                        for i in range(1, 15)
                    ],
                })
            portales_bloque.append({
                'id': referencia,
                'nombre': portal_nombre,
                'referencia': referencia,
                'plantas': plantas,
            })
        bloques.append({
            'id': bloque_nombre.lower().replace(' ', '_'),
            'nombre': bloque_nombre,
            'portales': portales_bloque,
        })

    ficha = {
        'identidad': {
            'cliente': 'Cliente de prueba de volumen alto',
            'direccion': 'Avenida de la Maquetacion 100, Bilbao',
        },
        'estructura': {'bloques': bloques},
        'tajos': {'detalle': tajos},
    }

    snapshot_vivienda = []
    primera_por_tajo = set()
    for referencia, _portal_nombre, _bloque in portales:
        for unidad in range(1, 16):
            for indice in range(1, 31):
                tajo = f'Tajo propio de estres {indice:02d}'
                estado = 'X'
                if tajo not in primera_por_tajo:
                    estado = ''
                    primera_por_tajo.add(tajo)
                snapshot_vivienda.append({
                    'task': tajo,
                    'building': referencia,
                    'floor': 'PB',
                    'unit': f'{referencia}_v{unidad:02d}',
                    'status': estado,
                })

    zesp = [
        {
            'task': f'Tajo propio de estres {((i - 1) % 30) + 1:02d}',
            'building': 'ref_a1', 'floor': 'Zonas especiales',
            'unit': f'ze{i:02d}', 'status': 'X' if i % 4 else 'M',
        }
        for i in range(1, 15)
    ]
    snapshot = snapshot_vivienda + zesp
    garaje = [
        {
            'task': f'Tajo propio de estres {((i - 1) % 30) + 1:02d}',
            'building': 'Garaje principal', 'floor': 'S-1',
            'unit': f'Zona de garaje {i:02d}',
            'status': ('X', 'M', '/', '')[(i - 1) % 4],
        }
        for i in range(1, 21)
    ]

    historial = []
    fechas = (
        '01/06/2026', '08/06/2026', '15/06/2026', '22/06/2026',
        '29/06/2026', '06/07/2026', '13/07/2026', '20/07/2026',
        '27/07/2026', '03/08/2026', '10/08/2026', '17/08/2026',
    )
    for paso, fecha in enumerate(fechas, 1):
        terminadas = 110 + paso * 96
        en_marcha = 18 + paso
        revision = []
        for indice, fila in enumerate(snapshot_vivienda):
            if indice < terminadas:
                estado = 'X'
            elif indice < terminadas + en_marcha:
                estado = 'M'
            elif indice < terminadas + en_marcha + 11:
                estado = '/'
            else:
                estado = ''
            revision.append({**fila, 'status': estado})
        historial.append((fecha, revision))

    detalle = []
    for indice in range(1, 13):
        detalle.append({
            'tarea_id': f'propio_{indice:02d}',
            'trabajo': f'Tajo propio de estres {indice:02d}',
            'propiedad': 'propio', 'categoria': 'VIABLE',
            'edificio': portales[(indice - 1) % 3][0], 'planta': 'PB',
            'unidad': f'v{indice:02d}', 'estado': '',
            'fase_nombre': f'Fase de produccion {indice:02d}',
            'orden_ejecucion': indice,
        })
    for indice in range(1, 13):
        tajo = indice + 12
        detalle.append({
            'tarea_id': f'propio_{tajo:02d}',
            'trabajo': f'Tajo propio de estres {tajo:02d}',
            'propiedad': 'propio', 'categoria': 'BLOQUEADO',
            'edificio': portales[(indice - 1) % 3][0], 'planta': 'PB',
            'unidad': f'v{indice:02d}', 'estado': '',
            'fase_nombre': f'Fase de produccion {tajo:02d}',
            'orden_ejecucion': tajo,
            'dependencias_detalle': [{
                'id': f'externo_{indice:02d}',
                'nombre': f'Condicionante externo de estres {indice:02d}',
                'estado': 'Pendiente', 'cumplida': False,
            }],
        })

    def prioridades_zonas(filas, nombres_reales):
        return {'detalle_items': [
            {
                'tarea_id': f'propio_{((i - 1) % 30) + 1:02d}',
                'trabajo': fila['task'], 'propiedad': 'propio',
                'categoria': 'TERMINADO' if fila['status'] == 'X' else 'VIABLE',
                'edificio': fila['building'], 'planta': fila['floor'],
                'unidad': (f'ze{i:02d}' if nombres_reales else fila['unit']),
                'estado': fila['status'], 'fase_nombre': 'Zonas',
                'orden_ejecucion': i,
            }
            for i, fila in enumerate(filas, 1)
        ]}

    meta = {
        'OBRA ESTRES': {
            'nombre': 'OBRA ESTRES',
            'bloques': [
                {
                    'nombre': bloque['nombre'],
                    'portales': [
                        {
                            'nombre': portal['nombre'],
                            'referencia_portal': portal['referencia'],
                        }
                        for portal in bloque['portales']
                    ],
                }
                for bloque in bloques
            ],
        },
    }
    return {
        'ficha': ficha, 'snapshot': snapshot, 'zesp': zesp,
        'garaje': garaje, 'historial': historial,
        'prioridades': {'detalle_items': detalle},
        'prioridades_zesp': prioridades_zonas(zesp, True),
        'prioridades_garaje': prioridades_zonas(garaje, False),
        'meta': meta,
    }


class TestAjusteDePagina(unittest.TestCase):

    def test_elige_el_mayor_factor_que_cabe_en_pasos_de_cinco_cientesimas(self):
        ajuste = gie._ajustar_pagina(
            lambda escala: [Spacer(1, 100 * escala)],
            ancho=100, alto=126, etiqueta='fixture')
        self.assertEqual(ajuste['escala'], 1.25)
        self.assertLessEqual(ajuste['alto'], 126)

    def test_si_ni_el_minimo_cabe_no_aborta_y_avisa_visiblemente(self):
        salida = io.StringIO()
        with redirect_stdout(salida):
            ajuste = gie._ajustar_pagina(
                lambda escala: [Spacer(1, 200 * escala)],
                ancho=100, alto=126, etiqueta='fixture imposible')
        self.assertEqual(ajuste['escala'], .85)
        self.assertTrue(ajuste['forzado'])
        self.assertIn('AVISO INFORME EJECUTIVO', salida.getvalue())
        self.assertIn('fixture imposible', salida.getvalue())

    def test_el_bloque_no_vuelve_a_encerrar_el_final_en_keep_together(self):
        fuente = inspect.getsource(gie._construir_bloque_electrico)
        self.assertNotIn('KeepTogether', fuente)
        self.assertIn('_ajustar_pagina', fuente)


class TestMinimosTipograficosPorCategoria(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        gie._registrar_fuentes()

    def test_notas_secciones_y_cuerpo_respetan_minimos_a_escala_090(self):
        self.assertGreaterEqual(gie._nota('Nota', .90).style.fontSize, 8.0)
        self.assertGreaterEqual(gie._seccion('Seccion', .90).style.fontSize, 10.0)

        tabla = gie._tabla_tajos_atencion([
            {'nombre': 'Tajo', 'fase': 'Fase', 'pct': 25.0, 'x': 0,
             'total': 1, 'pendiente': 0, 'orden': 1},
        ], 112 * mm, escala=.90)
        parrafos = [
            celda
            for fila in tabla._cellvalues
            for celda in fila
            if isinstance(celda, Paragraph)
        ]
        self.assertTrue(parrafos)
        self.assertGreaterEqual(
            min(p.style.fontSize for p in parrafos), 8.5)

    def test_el_cuerpo_no_baja_de_8_5_a_escala_085(self):
        tabla = gie._tabla_tajos_atencion([
            {'nombre': 'Tajo', 'fase': 'Fase', 'pct': 25.0, 'x': 0,
             'total': 1, 'pendiente': 1, 'orden': 1},
        ], 112 * mm, escala=.85)
        cuerpo = [
            celda.style.fontSize
            for fila in tabla._cellvalues
            for celda in fila
            if isinstance(celda, Paragraph)
        ]
        self.assertTrue(cuerpo)
        self.assertGreaterEqual(min(cuerpo), 8.5)
        self.assertGreaterEqual(gie._nota('Nota', .85).style.fontSize, 8.0)

    def test_etiquetas_del_grafico_no_bajan_de_8_5(self):
        dibujo = gie._grafico_tendencia([
            {'fecha': '01/09/2026', 'pct': 25.0},
            {'fecha': '08/09/2026', 'pct': 50.0},
        ], 100 * mm, escala=.90)
        tamanos = [e.fontSize for e in dibujo.contents if isinstance(e, String)]
        self.assertTrue(tamanos)
        self.assertGreaterEqual(min(tamanos), 8.5)

    def test_grafico_de_doce_puntos_adelgaza_valores_y_fechas(self):
        serie = [
            {'fecha': f'{1 + i * 2:02d}/09/2026', 'pct': pct}
            for i, pct in enumerate(
                (80.1, 75.0, 72.4, 84.3, 80.2, 97.5,
                 83.1, 90.4, 88.2, 93.6, 91.5, 96.0))
        ]
        dibujo = gie._grafico_tendencia(
            serie, 112 * mm, escala=.90, total_actual=95.4)
        cadenas = [e for e in dibujo.contents if isinstance(e, String)]
        valores = [e for e in cadenas if re.fullmatch(r'\d+\.\d%', str(e.text))]
        fechas = [e for e in cadenas if re.fullmatch(r'\d\d/\d\d', str(e.text))]
        textos_valor = {str(e.text) for e in valores}
        for obligatorio in ('80.1%', '72.4%', '97.5%', '96.0%'):
            self.assertIn(obligatorio, textos_valor)
        self.assertLess(len(valores), len(serie))
        self.assertEqual(str(fechas[0].text), '01/09')
        self.assertEqual(str(fechas[-1].text), '23/09')
        for anterior, siguiente in zip(fechas, fechas[1:]):
            self.assertGreaterEqual(siguiente.x - anterior.x, 14 * mm - .01)

    def test_cifras_kpi_permanecen_entre_20_y_24(self):
        tabla = gie._tabla_kpis_electricos(
            [{'status': 'X'}], [], [], 186 * mm, escala=.90)
        tamanos = []
        for celda in tabla._cellvalues[0]:
            for flowable in celda:
                if isinstance(flowable, Paragraph) and '%' in flowable.getPlainText():
                    tamanos.append(flowable.style.fontSize)
        self.assertTrue(tamanos)
        self.assertGreaterEqual(min(tamanos), 20.0)
        self.assertLessEqual(max(tamanos), 24.0)

    def test_barra_de_avance_usa_un_decimal(self):
        dibujo = gie._dibujo_barra_resumen(
            'Portal 1', 95.5, 191, 200, 70 * mm, escala=1.0)
        textos = [str(e.text) for e in dibujo.contents if isinstance(e, String)]
        self.assertIn('95.5%  191/200', textos)
        self.assertNotIn('96%  191/200', textos)


class TestContenidoNumericoYRecortes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        gie._registrar_fuentes()
        cls.fx = _fixture_completo()
        cls.por_id, cls.por_nombre = gie._indice_metadatos_tajos(cls.fx['ficha'])
        cls.propios = gie._filtrar_snapshot_sagarde(
            cls.fx['snapshot'] + cls.fx['garaje'], cls.por_nombre)
        cls.datos = gie._datos_pagina_electrica(
            cls.propios, cls.fx['historial'], cls.fx['prioridades'],
            cls.por_id, cls.por_nombre)

    def test_kpis_y_orden_de_tajos_son_los_del_motor_sin_recalculo_visual(self):
        self.assertEqual(
            self.datos['kpis'], motor_informes.kpis_snapshot(self.propios))
        esperados = gie._resumen_tajos_sagarde(self.propios, self.por_nombre)
        self.assertEqual(self.datos['tajos'], esperados)

    def test_kpis_conservan_porcentajes_razon_y_anaden_cierre_sin_pagina(self):
        tabla = gie._tabla_kpis_electricos(
            self.propios, self.datos['frentes'], self.datos['bloqueadores'],
            186 * mm, cierre=self.fx['cierre'], incluir_cierre=True,
            escala=1.0)
        texto = _texto_de_flowable(tabla)
        kpis = motor_informes.kpis_snapshot(self.propios)
        for token in (
                f"{kpis['pct_ponderado']:.1f}%",
                f"{kpis['pct_estricto']:.1f}%",
                f"{kpis['x']}/{kpis['total']}", '2/4'):
            self.assertIn(token, texto)

    def test_tajos_limitados_a_diez_declaran_cuantos_quedan(self):
        tabla = gie._tabla_tajos_atencion(
            self.datos['tajos'], 112 * mm, escala=1.0, max_filas=10)
        texto = _texto_de_flowable(tabla)
        pendientes = [t for t in self.datos['tajos'] if t['pct'] < 99.9]
        self.assertIn('+{}'.format(len(pendientes) - 10), texto)
        self.assertIn('ma', gie._fold(texto))
        for nombre in [f'Tajo propio {i:02d}' for i in range(1, 11)]:
            self.assertIn(nombre, texto)
        self.assertNotIn('Tajo propio 11', texto)

    def test_tokens_de_tablas_y_fases_son_los_calculados_por_los_helpers_vigentes(self):
        piezas = [
            gie._tabla_kpis_electricos(
                self.propios, self.datos['frentes'], self.datos['bloqueadores'],
                186 * mm, cierre=self.fx['cierre'], incluir_cierre=True,
                escala=1.0),
            gie._tabla_tajos_atencion(
                self.datos['tajos'], 112 * mm, escala=1.0, max_filas=10),
            gie._tabla_fases_doble(
                self.datos['fases'], 186 * mm, escala=1.0),
        ]
        encontrados = set(TOKEN_NUMERICO.findall(_texto_de_flowable(piezas)))
        kpis = motor_informes.kpis_snapshot(self.propios)
        esperados = {
            f"{kpis['pct_ponderado']:.1f}%",
            f"{kpis['pct_estricto']:.1f}%",
            f"{kpis['x']}/{kpis['total']}",
            '2/4',
        }
        for fase in self.datos['fases']:
            esperados.add(f"{fase['pct']:.1f}%")
            esperados.add(f"{fase['x']}/{fase['total']}")
        for tajo in [t for t in self.datos['tajos'] if t['pct'] < 99.9][:10]:
            esperados.add(f"{tajo['pct']:.0f}%")
            esperados.add(f"{tajo['x']}/{tajo['total']}")
        self.assertTrue(esperados <= encontrados,
                        'faltan tokens: ' + repr(sorted(esperados - encontrados)))


class TestPdfDensoDeFixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            import pdfplumber  # noqa: F401
        except ImportError:
            raise unittest.SkipTest('pdfplumber no esta instalado')
        cls.fx = _fixture_completo()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pdf = Path(cls.tmp.name) / 'informe_denso.pdf'
        gie.generar_pdf_ejecutivo(
            'OBRA DENSIDAD', '22/09/2026', cls.fx['snapshot'], cls.pdf,
            historial=cls.fx['historial'], ficha=cls.fx['ficha'],
            prioridades=cls.fx['prioridades'],
            snapshot_garaje=cls.fx['garaje'],
            prioridades_garaje=cls.fx['prioridades_garaje'],
            snapshot_zonas_especiales=cls.fx['zesp'],
            prioridades_zonas_especiales=cls.fx['prioridades_zesp'],
            cierre=cls.fx['cierre'], avisos_cierre=[])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _abrir(self):
        import pdfplumber
        return pdfplumber.open(str(self.pdf))

    def test_cada_hoja_lleva_el_resumen_ejecutivo_con_la_situacion(self):
        """El parrafo de situacion es la esencia narrativa del informe: se
        quito en la primera iteracion del rediseno y no puede volver a faltar."""
        with self._abrir() as pdf:
            textos = [gie._fold(p.extract_text() or '') for p in pdf.pages]
        for indice, texto in enumerate(textos, 1):
            # _fold devuelve minusculas y sin puntuacion.
            self.assertIn('situacion electrica sagarde alcanza un', texto,
                          'hoja {}'.format(indice))
            self.assertIn('de avance estimado y un', texto,
                          'hoja {}'.format(indice))
            self.assertIn('produccion', texto, 'hoja {}'.format(indice))

    def test_una_pagina_por_ambito_y_ninguna_pagina_independiente_de_cierre(self):
        with self._abrir() as pdf:
            textos = [p.extract_text() or '' for p in pdf.pages]
        self.assertEqual(len(textos), 5, textos)
        for texto in textos:
            normalizado = gie._fold(texto).upper()
            self.assertIn('INFORME EJECUTIVO', normalizado)
            self.assertIn('OBRA OBRA DENSIDAD', normalizado)
            self.assertIn('MONTAJES', normalizado)
            self.assertIn('SAGARDE', normalizado)
            self.assertIn('S L', normalizado)
            self.assertIn('Fuente:', texto)
        self.assertFalse(any(
            texto.lstrip().startswith('CIERRE DE EXPEDIENTE')
            for texto in textos))
        self.assertIn('Ensayos', textos[0])
        self.assertIn('instrumentales', textos[0])
        self.assertIn('Libro del Edificio', textos[0])

    def test_evolucion_distingue_viviendas_del_total_de_obra(self):
        serie = gie._serie_avance_sagarde(
            self.fx['historial'],
            gie._indice_metadatos_tajos(self.fx['ficha'])[1])
        total = gie._filtrar_snapshot_sagarde(
            self.fx['snapshot'] + self.fx['garaje'],
            gie._indice_metadatos_tajos(self.fx['ficha'])[1])
        pct_total = motor_informes.kpis_snapshot(total)['pct_ponderado']
        with self._abrir() as pdf:
            texto = pdf.pages[0].extract_text() or ''
        self.assertIn('VIVIENDAS', gie._fold(texto).upper())
        self.assertIn('Total obra', texto)
        for punto in serie:
            self.assertIn(f"{punto['pct']:.1f}%", texto)
        self.assertIn(f'{pct_total:.1f}%', texto)

    def test_avance_por_bloque_incluye_portales_garaje_y_zonas_especiales(self):
        with self._abrir() as pdf:
            texto = pdf.pages[0].extract_text() or ''
        self.assertIn('AVANCE POR BLOQUE', gie._fold(texto).upper())
        for rotulo in ('P1', 'P2', 'GARAJE', 'ZONAS ESPECIALES'):
            self.assertIn(rotulo, gie._fold(texto).upper())

    def test_todas_las_paginas_ocupan_al_menos_el_75_por_ciento_sin_el_pie(self):
        with self._abrir() as pdf:
            for numero, pagina in enumerate(pdf.pages, 1):
                palabras = pagina.extract_words()
                pies = [p['top'] for p in palabras if p['text'] == 'Fuente:']
                self.assertTrue(pies, f'pagina {numero} sin linea de fuente')
                limite_pie = min(pies)
                cuerpo = [c for c in pagina.chars if c['top'] < limite_pie - 1]
                self.assertTrue(cuerpo, f'pagina {numero} sin contenido')
                ocupado = ((max(c['bottom'] for c in cuerpo)
                            - min(c['top'] for c in cuerpo))
                           / (pagina.height - 2 * gie.MARGIN_Y))
                self.assertGreaterEqual(
                    ocupado, .75,
                    f'pagina {numero}: ocupacion {ocupado:.1%}')

    def test_fuentes_reales_respetan_minimos_y_kpis_grandes(self):
        with self._abrir() as pdf:
            for numero, pagina in enumerate(pdf.pages, 1):
                minimo = min(float(c['size']) for c in pagina.chars)
                self.assertGreaterEqual(
                    minimo + .01, 8.0,
                    f'pagina {numero}: fuente minima {minimo:.2f} pt')

            pagina = pdf.pages[0]
            palabras = pagina.extract_words(extra_attrs=['size'])
            total = gie._filtrar_snapshot_sagarde(
                self.fx['snapshot'] + self.fx['garaje'],
                gie._indice_metadatos_tajos(self.fx['ficha'])[1])
            kpis = motor_informes.kpis_snapshot(total)
            valores = (
                f"{kpis['pct_ponderado']:.1f}%",
                f"{kpis['pct_estricto']:.1f}%",
                f"{kpis['x']}/{kpis['total']}", '2/4')
            for valor in valores:
                tamanos = [float(p['size']) for p in palabras
                           if p['text'] == valor]
                self.assertTrue(tamanos, f'no se encontro KPI {valor}')
                self.assertGreaterEqual(max(tamanos), 20.0, valor)
                self.assertLessEqual(max(tamanos), 24.01, valor)


class TestPdfDeEstres(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            import pdfplumber  # noqa: F401
        except ImportError:
            raise unittest.SkipTest('pdfplumber no esta instalado')
        cls.fx = _fixture_estres()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pdf = Path(cls.tmp.name) / 'informe_estres.pdf'
        salida = io.StringIO()
        with mock.patch.object(
                gie, '_cargar_meta_obras', return_value=cls.fx['meta']):
            with redirect_stdout(salida):
                gie.generar_pdf_ejecutivo(
                    'OBRA ESTRES', '17/08/2026', cls.fx['snapshot'], cls.pdf,
                    historial=cls.fx['historial'], ficha=cls.fx['ficha'],
                    prioridades=cls.fx['prioridades'],
                    snapshot_garaje=cls.fx['garaje'],
                    prioridades_garaje=cls.fx['prioridades_garaje'],
                    snapshot_zonas_especiales=cls.fx['zesp'],
                    prioridades_zonas_especiales=cls.fx['prioridades_zesp'])
        cls.log = salida.getvalue()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _abrir(self):
        import pdfplumber
        return pdfplumber.open(str(self.pdf))

    def test_genera_todas_las_paginas_y_el_recorte_es_visible(self):
        with self._abrir() as pdf:
            textos = [p.extract_text() or '' for p in pdf.pages]
        self.assertEqual(len(textos), 6, textos)
        self.assertNotIn('[ERROR INFORME EJECUTIVO]', self.log)
        self.assertIn('[AVISO INFORME EJECUTIVO]', self.log)
        self.assertTrue(any(re.search(r'\+\d+\s+m', t.casefold())
                            for t in textos), textos)

    def test_paginas_entre_75_y_96_por_ciento_de_ocupacion(self):
        with self._abrir() as pdf:
            for numero, pagina in enumerate(pdf.pages, 1):
                palabras = pagina.extract_words()
                pies = [p['top'] for p in palabras if p['text'] == 'Fuente:']
                self.assertTrue(pies, f'pagina {numero} sin linea de fuente')
                limite_pie = min(pies)
                cuerpo = [c for c in pagina.chars if c['top'] < limite_pie - 1]
                ocupado = ((max(c['bottom'] for c in cuerpo)
                            - min(c['top'] for c in cuerpo))
                           / (pagina.height - 2 * gie.MARGIN_Y))
                self.assertGreaterEqual(
                    ocupado, .75, f'pagina {numero}: {ocupado:.1%}')
                self.assertLessEqual(
                    ocupado, .965, f'pagina {numero}: {ocupado:.1%}')

    def test_fuente_minima_y_kpi_de_celdas_en_una_sola_linea(self):
        por_nombre = gie._indice_metadatos_tajos(self.fx['ficha'])[1]
        total = gie._filtrar_snapshot_sagarde(
            self.fx['snapshot'] + self.fx['garaje'], por_nombre)
        kpis = motor_informes.kpis_snapshot(total)
        token = f"{kpis['x']}/{kpis['total']}"
        self.assertGreaterEqual(kpis['total'], 1000)
        with self._abrir() as pdf:
            for numero, pagina in enumerate(pdf.pages, 1):
                minimo = min(float(c['size']) for c in pagina.chars)
                self.assertGreaterEqual(
                    minimo + .01, 8.0,
                    f'pagina {numero}: fuente minima {minimo:.2f} pt')
            palabras = pdf.pages[0].extract_words(extra_attrs=['size'])
        coincidencias = [p for p in palabras if p['text'] == token]
        self.assertTrue(coincidencias, f'KPI partido o ausente: {token}')
        self.assertGreaterEqual(max(float(p['size']) for p in coincidencias), 16)

    def test_etiquetas_del_grafico_no_se_intersectan_en_el_pdf(self):
        with self._abrir() as pdf:
            palabras = pdf.pages[0].extract_words(extra_attrs=['size'])
        titulos = [p for p in palabras
                   if gie._fold(p['text']).startswith('evolucion')]
        self.assertTrue(titulos)
        titulos_fase = [p for p in palabras
                        if gie._fold(p['text']).startswith('fases')]
        self.assertTrue(titulos_fase)
        arriba = min(p['top'] for p in titulos)
        limite_inferior = min(p['top'] for p in titulos_fase)
        fechas = [p for p in palabras
                  if re.fullmatch(r'\d\d/\d\d', p['text'])
                  and arriba <= p['top'] < limite_inferior]
        self.assertGreaterEqual(len(fechas), 2, fechas)
        abajo = max(p['bottom'] for p in fechas)
        etiquetas = [
            p for p in palabras
            if arriba <= p['top'] <= abajo
            and (re.fullmatch(r'\d+(?:\.\d+)?%', p['text'])
                 or re.fullmatch(r'\d\d/\d\d', p['text']))
        ]
        self.assertGreaterEqual(len(etiquetas), 8, etiquetas)

        def intersectan(a, b):
            return (max(a['x0'], b['x0']) < min(a['x1'], b['x1']) - .2
                    and max(a['top'], b['top'])
                    < min(a['bottom'], b['bottom']) - .2)

        solapes = [
            (a['text'], b['text'])
            for indice, a in enumerate(etiquetas)
            for b in etiquetas[indice + 1:]
            if intersectan(a, b)
        ]
        self.assertEqual(solapes, [])

        fechas = sorted(fechas, key=lambda p: (p['x0'] + p['x1']) / 2)
        centros = [(p['x0'] + p['x1']) / 2 for p in fechas]
        for anterior, siguiente in zip(centros, centros[1:]):
            self.assertGreaterEqual(siguiente - anterior, 14 * mm - 1)

    def test_valores_obligatorios_del_grafico_siguen_presentes(self):
        serie = gie._serie_avance_sagarde(
            self.fx['historial'],
            gie._indice_metadatos_tajos(self.fx['ficha'])[1])[-12:]
        obligatorios = {
            serie[0]['pct'], serie[-1]['pct'],
            min(p['pct'] for p in serie), max(p['pct'] for p in serie),
        }
        with self._abrir() as pdf:
            texto = pdf.pages[0].extract_text() or ''
        for valor in obligatorios:
            self.assertIn(f'{valor:.1f}%', texto)
        visibles = sum(f'{p["pct"]:.1f}%' in texto for p in serie)
        self.assertLess(visibles, len(serie))

    def test_portales_tienen_etiquetas_cortas_y_unicas(self):
        esperados = (
            'Bloque Norte Portal 1',
            'Portal 2',
            'Bloque Sur Portal 1',
        )
        with self._abrir() as pdf:
            textos = [gie._fold(p.extract_text() or '') for p in pdf.pages]
        for pagina, esperado in zip(textos[1:4], esperados):
            self.assertIn(gie._fold(esperado), pagina)
        self.assertEqual(len({gie._fold(e) for e in esperados}), 3)

    def test_avance_por_bloque_conserva_un_decimal(self):
        por_nombre = gie._indice_metadatos_tajos(self.fx['ficha'])[1]
        componentes = []
        for referencia in ('ref_a1', 'ref_a2', 'ref_b1'):
            snap = [r for r in self.fx['snapshot']
                    if r['building'] == referencia
                    and r['floor'] != 'Zonas especiales']
            snap = gie._filtrar_snapshot_sagarde(snap, por_nombre)
            componentes.append(
                motor_informes.kpis_snapshot(snap)['pct_ponderado'])
        with self._abrir() as pdf:
            texto = pdf.pages[0].extract_text() or ''
        for valor in componentes:
            self.assertIn(f'{valor:.1f}%', texto)


class TestTextoDelResumenEjecutivo(unittest.TestCase):
    KPIS = {'pct_ponderado': 95.4, 'pct_estricto': 94.5}
    SERIE = [{'pct': 92.8}, {'pct': 95.4}]

    def test_dice_la_situacion_y_el_avance_frente_a_la_revision_anterior(self):
        texto = gie._texto_resumen_ejecutivo(
            self.KPIS, self.SERIE, [1, 2, 3], [])
        for esperado in ('Situación eléctrica', '95.4%', '94.5%',
                         'avance de +2.6 puntos frente a la revisión anterior',
                         '3 tajos propios'):
            self.assertIn(esperado, texto)

    def test_con_garaje_no_atribuye_a_toda_la_obra_el_avance_de_las_viviendas(self):
        texto = gie._texto_resumen_ejecutivo(
            self.KPIS, self.SERIE, [], [], solo_viviendas=True)
        self.assertIn('las viviendas avanzan +2.6 puntos', texto)
        self.assertNotIn('avance de +2.6', texto)

    def test_sin_serie_suficiente_lo_dice_en_lugar_de_inventar_un_avance(self):
        texto = gie._texto_resumen_ejecutivo(
            self.KPIS, self.SERIE[:1], [], [])
        self.assertIn('sin comparación histórica suficiente', texto)
        self.assertNotIn('puntos frente', texto)


class TestRotulosDeFasesNoSeCortan(unittest.TestCase):
    """Un nombre cortado con puntos suspensivos no se distingue de otro:
    la fase o el bloque se lee entero a cualquier escala, aunque haya que
    pasar de la linea unica a la variante con el rotulo encima o reducir la
    letra hasta su minimo."""

    @classmethod
    def setUpClass(cls):
        # La tipografia solo se registra al generar un PDF; estas pruebas
        # miden anchos de texto sin generarlo.
        gie._registrar_fuentes()

    FASES = [
        {'fase': 'Recuperación tras Pladur', 'pct': 100.0, 'x': 62, 'total': 62},
        {'fase': 'Cubierta — Antena/pararrayos', 'pct': 7.1, 'x': 0, 'total': 7},
        {'fase': 'Instalación interior garaje', 'pct': 0.0, 'x': 0, 'total': 8},
        {'fase': 'Inicio de obra', 'pct': 100.0, 'x': 92, 'total': 92},
    ]

    def test_el_nombre_de_cada_fase_esta_entero_a_cualquier_escala(self):
        for escala in (.9, 1.0, 1.25, 1.5):
            texto = _texto_de_flowable(
                gie._tabla_fases_doble(self.FASES, 190 * mm, escala))
            for fase in self.FASES:
                self.assertIn(fase['fase'], texto, 'escala {}'.format(escala))
            self.assertNotIn('…', texto, 'escala {}'.format(escala))

    def test_la_barra_de_bloque_reduce_la_letra_antes_de_cortar_el_nombre(self):
        dibujo = gie._dibujo_barra_resumen(
            'ZONAS ESPECIALES', 4.4, 1, 88, 60 * mm, 1.5)
        nombre = next(
            s for s in dibujo.contents
            if isinstance(s, String) and 'ZONAS' in s.text)
        self.assertEqual(nombre.text, 'ZONAS ESPECIALES')
        self.assertGreaterEqual(nombre.fontSize, 8.5)
        self.assertLess(nombre.fontSize, gie._fuente_escalada(8.7, 1.5, 8.5))

    def test_la_direccion_de_cabecera_no_arrastra_las_coordenadas(self):
        crudo = ('Parcela RE A4, Bolueta, 48004 Bilbao (Bizkaia). '
                 'Coordenadas geográficas: 43° 14\' 46" N, 2° 54\' 13" O')
        self.assertEqual(gie._valor_ejecutivo(crudo, 85),
                         'Parcela RE A4, Bolueta, 48004 Bilbao (Bizkaia)')
        # Una direccion normal no se toca.
        self.assertEqual(gie._valor_ejecutivo('Kortezubi Bidea, Nº 1', 85),
                         'Kortezubi Bidea, Nº 1')

    def test_la_linea_unica_solo_se_usa_si_la_barra_conserva_17_mm(self):
        # Nombres muy largos: no queda barra util en la mitad de la hoja, asi
        # que debe caer a la variante con el rotulo encima (dibujo mas alto).
        largas = [{'fase': 'Instalación interior de servicios generales del edificio',
                   'pct': 50.0, 'x': 5, 'total': 10}]
        tabla = gie._tabla_fases_doble(largas, 190 * mm, 1.0)
        alto_celda = tabla._cellvalues[0][0].height
        self.assertGreaterEqual(alto_celda, 8 * mm)


if __name__ == '__main__':
    unittest.main()
