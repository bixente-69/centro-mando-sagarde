# -*- coding: utf-8 -*-
"""Regresiones de la vista separada de zonas especiales de vivienda."""

import copy
import json
import os
import re
import sys
import tempfile
import types
import unittest
from datetime import date, datetime
from unittest import mock


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

import ficha_obra
import generar_todos
import generar_informe_ejecutivo
import panel_obra
import priorizador_trabajos
import fixtures


def _ficha_con_zonas_especiales():
    """Ficha controlada: 2 celdas normales y 4 de zonas especiales.

    Normal: X, P. Zonas especiales: X, P, P, P. El priorizador real da
    para el subconjunto especial 2 bloques listos y 1 desbloqueo previsto.
    """
    ficha = fixtures.ficha_minima()
    portal = ficha['estructura']['bloques'][0]['portales'][0]
    portal['plantas'].append({
        'id': ficha_obra.ID_PLANTA_ZONAS_ESPECIALES,
        'nombre': ficha_obra.NOMBRE_PLANTA_ZONAS_ESPECIALES,
        'orden': ficha_obra.ORDEN_PLANTA_ZONAS_ESPECIALES,
        'ubicaciones': [
            {'id': 'ct1', 'tipo': 'cuarto_tecnico', 'nombre': 'RITI'},
            {'id': 'cub1', 'tipo': 'cubierta', 'nombre': 'Cubierta'},
        ],
    })
    for planta_id, unidad, tajo_id, valor in (
        ('pb', 'A', 'tubeado', 'X'),
        ('pb', 'A', 'cableado', 'P'),
        ('zesp', 'ct1', 'tubeado', 'X'),
        ('zesp', 'ct1', 'cableado', 'P'),
        ('zesp', 'cub1', 'tubeado', 'P'),
        ('zesp', 'cub1', 'cableado', 'P'),
    ):
        clave = 'p1__%s__%s__%s' % (planta_id, tajo_id, unidad)
        ficha['estados'][clave] = {
            'v': valor, 'f': '27/09/2026', 'r': 'rev_27092026',
        }
    ficha['revisiones'] = [{
        'id': 'rev_27092026', 'fecha': '27/09/2026',
    }]
    return ficha


def _prioridades_y_snapshots():
    ficha = _ficha_con_zonas_especiales()
    prioridades = priorizador_trabajos.priorizar_ficha(
        ficha, obra='OBRA ZESP PRUEBA', hoy=date(2026, 9, 27))
    prioridades_zesp = generar_todos.extraer_prioridades_zonas_especiales(
        prioridades)
    snapshot = ficha_obra.snapshot_desde_ficha(ficha)
    snapshot_zesp = generar_todos.snapshot_zonas_especiales(ficha)
    return prioridades, prioridades_zesp, snapshot, snapshot_zesp


class _DatetimeFijo(datetime):
    @classmethod
    def now(cls, tz=None):
        instante = datetime(2026, 9, 27, 12, 0)
        return instante if tz is None else instante.replace(tzinfo=tz)


def _generar(prioridades_zesp=None, snapshot_zesp=None):
    prioridades, _calculadas, snapshot, _snapshot_calculado = (
        _prioridades_y_snapshots())
    ficha_xlsx = {
        '_disponible': True, 'datos': {}, 'personal': [], 'hitos': [],
        'riesgos': [], 'plan': [], 'tareas': [],
    }
    with tempfile.TemporaryDirectory() as carpeta:
        salida = os.path.join(carpeta, 'panel.html')
        with mock.patch.object(panel_obra, 'datetime', _DatetimeFijo):
            resultado = panel_obra.generar_panel(
                obra='OBRA ZESP PRUEBA', subtitulo='Prueba de panel',
                historial=[('27/09/2026', snapshot)], materiales={},
                ficha=ficha_xlsx, documentos=[], prioridades=prioridades,
                prioridades_zonas_especiales=prioridades_zesp,
                snapshot_zonas_especiales=snapshot_zesp,
                output_path=salida,
            )
        with open(salida, encoding='utf-8') as fichero:
            return fichero.read(), resultado


def _vistas(html):
    patron = re.compile(r'<section id="(v-[^"]+)" class="view(?: active)?">')
    coincidencias = list(patron.finditer(html))
    resultado = {}
    for indice, coincidencia in enumerate(coincidencias):
        fin = (coincidencias[indice + 1].start()
               if indice + 1 < len(coincidencias)
               else html.index('<div class="footer">', coincidencia.end()))
        resultado[coincidencia.group(1)] = html[coincidencia.end():fin]
    return resultado


class TestFiltradoZonasEspeciales(unittest.TestCase):

    def test_recalcula_todos_los_derivados_sin_mutar_las_prioridades(self):
        ficha = _ficha_con_zonas_especiales()
        prioridades = priorizador_trabajos.priorizar_ficha(
            ficha, obra='OBRA ZESP PRUEBA', hoy=date(2026, 9, 27))
        originales = copy.deepcopy(prioridades)

        zesp = generar_todos.extraer_prioridades_zonas_especiales(prioridades)

        self.assertEqual(prioridades, originales)
        self.assertEqual(len(zesp['detalle_items']), 4)
        self.assertEqual(
            {item['planta'] for item in zesp['detalle_items']},
            {ficha_obra.NOMBRE_PLANTA_ZONAS_ESPECIALES})
        # Valores calculados a mano sobre X,P,P,P y contrastados con el
        # priorizador real antes de fijarlos en esta prueba.
        self.assertEqual(zesp['resumen'], {
            'listos': 2,
            'verificar': 0,
            'unidades_listas': 2,
            'unidades_verificar': 0,
            'bloqueados': 0,
            'otros_gremios': 0,
            'dudas': 0,
            'sin_revisar': 0,
            'unidades_sin_revisar': 0,
            'terminados': 0,
            'inventario_total': 2,
            'detalle_total': 4,
            'preguntas_pendientes': 1,
            'viviendas': 2,
            'zonas_comunes': 0,
            'edificio': 0,
        })
        self.assertEqual(len(zesp['items']), 2)
        self.assertEqual(len(zesp['inventario']), 2)
        self.assertEqual(len(zesp['prevision']), 1)
        self.assertEqual(len(zesp['preguntas_orden']), 1)

    def test_snapshot_filtra_floor_literal_confirmado_por_ficha_obra(self):
        ficha = _ficha_con_zonas_especiales()

        snapshot = generar_todos.snapshot_zonas_especiales(ficha)

        self.assertEqual(len(snapshot), 4)
        self.assertEqual(
            {fila['floor'] for fila in snapshot},
            {ficha_obra.NOMBRE_PLANTA_ZONAS_ESPECIALES})
        self.assertEqual(
            {fila['planta_id'] for fila in snapshot},
            {ficha_obra.ID_PLANTA_ZONAS_ESPECIALES})
        self.assertEqual(
            {estado: sum(1 for fila in snapshot if fila['status'] == estado)
             for estado in ('X', 'M', '/', '')},
            {'X': 1, 'M': 0, '/': 0, '': 3})

    def test_sin_zonas_no_inventa_una_seccion_vacia(self):
        ficha = fixtures.ficha_minima()
        ficha['estados']['p1__pb__tubeado__A'] = {
            'v': 'X', 'f': '27/09/2026', 'r': 'rev_27092026',
        }
        ficha['revisiones'] = [{
            'id': 'rev_27092026', 'fecha': '27/09/2026',
        }]
        prioridades = priorizador_trabajos.priorizar_ficha(
            ficha, obra='OBRA SIN ZESP', hoy=date(2026, 9, 27))

        self.assertIsNone(
            generar_todos.extraer_prioridades_zonas_especiales(prioridades))
        self.assertEqual(generar_todos.snapshot_zonas_especiales(ficha), [])


class TestIntegracionGenerarTodosZonasEspeciales(unittest.TestCase):

    def test_main_escribe_el_json_filtrado_y_lo_entrega_al_panel(self):
        obra = {
            'id': 'zesp_test',
            'nombre': 'OBRA ZESP TEST',
            'subtitulo': 'Prueba',
            'adaptador': 'adaptador_zesp_test',
            'carpeta_obra': 'OBRA ZESP TEST',
            'materiales_rel': 'materiales.xlsx',
        }
        adaptador = types.ModuleType('adaptador_zesp_test')
        adaptador.cargar_historial = lambda: []

        with tempfile.TemporaryDirectory() as temporal:
            carpeta = os.path.join(temporal, obra['carpeta_obra'])
            os.makedirs(carpeta)
            ficha_obra.guardar(carpeta, _ficha_con_zonas_especiales())
            panel = mock.Mock(return_value={
                'kpis': {}, 'bloqueos': [], 'n_docs': 0,
                'sin_cambios': False,
            })

            parches = [
                mock.patch.object(generar_todos, 'OBRAS', [obra]),
                mock.patch.object(
                    generar_todos, 'OBRAS_ABIERTAS_DIR', temporal),
                mock.patch.dict(sys.modules, {
                    'adaptador_zesp_test': adaptador,
                }),
                mock.patch.object(
                    generar_todos.lectores, 'leer_materiales',
                    return_value={}),
                mock.patch.object(
                    generar_todos.lectores, 'leer_ficha', return_value={}),
                mock.patch.object(
                    generar_todos.lectores, 'listar_documentos',
                    return_value=[]),
                mock.patch.object(
                    generar_todos.mem, 'calcular_memoria', return_value={}),
                mock.patch.object(
                    generar_todos.mem, 'guardar_memoria', return_value={
                        'total_tajos': 0, 'activos': 0, 'terminados': 0,
                    }),
                mock.patch.object(
                    generar_todos.panel_obra, 'generar_panel', panel),
                mock.patch.object(
                    generar_todos.cierre_expediente, 'cargar',
                    return_value=({}, [])),
                mock.patch.object(
                    generar_todos.cierre_expediente, 'guardar'),
                mock.patch.object(
                    generar_informe_ejecutivo, 'generar_para_obra'),
                mock.patch.object(generar_todos, 'generar_index'),
                mock.patch.object(generar_todos, 'escribir_resumen_json'),
                mock.patch.object(
                    generar_todos, 'publicar_registro_revisiones'),
            ]
            for parche in parches:
                parche.start()
            self.addCleanup(
                lambda: [parche.stop() for parche in parches])

            generar_todos.main(hacer_pdf=False)

            ruta_zesp = os.path.join(
                carpeta, 'INFORME SAGARDE IA',
                'prioridades_trabajos_zesp.json')
            with open(ruta_zesp, encoding='utf-8') as fichero:
                zesp = json.load(fichero)
            with open(os.path.join(
                    carpeta, 'INFORME SAGARDE IA',
                    'prioridades_trabajos.json'), encoding='utf-8') as fichero:
                principales = json.load(fichero)

            self.assertEqual(zesp['resumen']['detalle_total'], 4)
            self.assertEqual(principales['resumen']['detalle_total'], 6)
            self.assertEqual(
                panel.call_args.kwargs['prioridades_zonas_especiales'],
                zesp)
            self.assertEqual(
                len(panel.call_args.kwargs['snapshot_zonas_especiales']), 4)


class TestPanelZonasEspeciales(unittest.TestCase):

    def test_crea_una_pestana_independiente_con_ids_y_json_propios(self):
        _prioridades, zesp, _snapshot, snapshot_zesp = (
            _prioridades_y_snapshots())
        html, _resultado = _generar(zesp, snapshot_zesp)
        vistas = _vistas(html)

        self.assertIn(
            '<button data-view="v-zesp">🔧 Zonas especiales</button>', html)
        self.assertIn('v-zesp', vistas)
        self.assertIn('Centro de mando · Prioridades', vistas['v-zesp'])
        self.assertIn('Tubeado interior', vistas['v-zesp'])
        self.assertIn('Cableado eléctrico', vistas['v-zesp'])
        self.assertIn('href="prioridades_trabajos_zesp.json"',
                      vistas['v-zesp'])
        self.assertIn('id="timeline-prio-zesp"', vistas['v-zesp'])
        self.assertNotIn('id="timeline-prio"', vistas['v-zesp'])
        self.assertNotIn('🔧', vistas['v-prioridades'])

    def test_sin_datos_no_aparece_en_ningun_sitio(self):
        html, _resultado = _generar(None, None)

        self.assertNotIn('data-view="v-zesp"', html)
        self.assertNotIn('id="v-zesp"', html)
        self.assertNotIn('prioridades_trabajos_zesp.json', html)

    def test_el_kpi_principal_no_suma_dos_veces_el_snapshot_filtrado(self):
        _prioridades, zesp, _snapshot, snapshot_zesp = (
            _prioridades_y_snapshots())

        html, resultado = _generar(zesp, snapshot_zesp)

        # Snapshot principal: X,P,X,P,P,P -> 2/6 = 33,3 %. El filtrado
        # especial (X,P,P,P -> 25 %) es solo una vista; no se vuelve a sumar.
        self.assertEqual(resultado['kpis']['total'], 6)
        self.assertEqual(resultado['kpis']['x'], 2)
        self.assertEqual(resultado['kpis']['pct_estricto'], 33.3)
        panel = _vistas(html)['v-panel']
        self.assertIn('<div class="value">33.3%</div>', panel)
        self.assertNotIn('incluye zonas especiales', panel)


class TestPanelTrabajosZonasEspeciales(unittest.TestCase):

    def test_funde_filas_sin_duplicar_zesp_como_vivienda(self):
        _prioridades, zesp, _snapshot, snapshot_zesp = (
            _prioridades_y_snapshots())

        html, _resultado = _generar(zesp, snapshot_zesp)
        trabajos = _vistas(html)['v-trabajos']

        self.assertIn(
            '<tr><td>🏠</td><td>P1</td><td>PB</td><td>50.0%</td>'
            '<td>50.0%</td><td>2</td></tr>', trabajos)
        self.assertIn(
            '<tr><td>🔧</td><td>P1</td><td>Zonas especiales</td>'
            '<td>25.0%</td><td>25.0%</td><td>4</td></tr>', trabajos)
        self.assertNotIn(
            '<tr><td>🏠</td><td>P1</td><td>Zonas especiales</td>',
            trabajos)
        self.assertIn('"🏠 Cableado"', html)
        self.assertIn('"🔧 Cableado"', html)
        self.assertIn('"🔧 Tubeado"', html)


class TestPanelGraficaZonasEspeciales(unittest.TestCase):

    def test_la_planta_virtual_se_muestra_como_serie_separada(self):
        _prioridades, zesp, _snapshot, snapshot_zesp = (
            _prioridades_y_snapshots())

        html, _resultado = _generar(zesp, snapshot_zesp)

        # Decisión de presentación: la planta virtual sí encaja en esta
        # gráfica, pero como origen 🔧 separado, no dentro de la serie 🏠.
        sin_espacios = html.replace(' ', '')
        self.assertIn('"labels":["PB","Zonasespeciales"]', sin_espacios)
        self.assertIn('"🏠P1":[50.0,null]', sin_espacios)
        self.assertIn('"🔧P1":[null,25.0]', sin_espacios)


if __name__ == '__main__':
    unittest.main()
