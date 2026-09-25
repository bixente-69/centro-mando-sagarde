# -*- coding: utf-8 -*-
'''Contrato del informe ejecutivo eléctrico basado en la base de obra.'''
import os
import sys
import tempfile
import unittest
from datetime import date


SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(SISTEMA_DIR))
sys.path.insert(0, SISTEMA_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'scripts'))

import generar_informe_ejecutivo as gie
import ficha_garajes
from priorizador_trabajos import priorizar_ficha_garaje


class TestFechaBaseSnapshot(unittest.TestCase):
    """La etiqueta de fecha del snapshot no puede quedarse desfasada.

    Bug real encontrado el 09/09/2026: la ficha de Bolueta ya tenia una
    revision del 09/09 (escrita via HTML, sin PDF que el adaptador viera),
    pero el informe ejecutivo seguia imprimiendo 'Datos: 31/08/2026' -- la
    ultima fecha que conocia el adaptador -- aunque el snapshot usado SI
    era el estado actual y completo de la ficha.
    """

    def test_prefiere_la_fecha_mas_reciente_aunque_el_adaptador_no_la_conozca(self):
        self.assertEqual(
            gie._fecha_base_snapshot('31/08/2026', '09/09/2026'),
            '09/09/2026')

    def test_conserva_la_fecha_del_adaptador_si_es_la_mas_reciente(self):
        self.assertEqual(
            gie._fecha_base_snapshot('31/08/2026', '24/08/2026'),
            '31/08/2026')

    def test_comparacion_no_es_alfabetica(self):
        # '09/09/2026' < '31/08/2026' como texto plano (el '0' inicial
        # gana); la comparacion real de fechas tiene que dar lo contrario.
        self.assertGreater(
            gie._fecha_ordenable('09/09/2026'),
            gie._fecha_ordenable('31/08/2026'))

    def test_sin_fecha_de_ficha_usa_la_del_adaptador(self):
        self.assertEqual(
            gie._fecha_base_snapshot('31/08/2026', ''), '31/08/2026')

    def test_fecha_de_adaptador_invalida_usa_la_de_la_ficha(self):
        self.assertEqual(
            gie._fecha_base_snapshot('', '09/09/2026'), '09/09/2026')


class TestAlcanceSagarde(unittest.TestCase):

    def setUp(self):
        self.meta = {
            'tubeado interior': {'id': 'tubeado', 'propiedad': 'propio'},
            'tabicado': {'id': 'tabicado', 'propiedad': 'externo'},
            'suelo radiante': {'id': 'suelo_radiante', 'propiedad': 'coordinacion'},
        }

    def test_el_kpi_excluye_tajos_no_sagarde(self):
        snapshot = [
            {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
             'unit': 'A', 'status': 'M'},
            {'task': 'Tabicado', 'building': 'P1', 'floor': '1',
             'unit': 'A', 'status': 'X'},
            {'task': 'Suelo radiante', 'building': 'P1', 'floor': '1',
             'unit': 'A', 'status': 'X'},
        ]
        propios = gie._filtrar_snapshot_sagarde(snapshot, self.meta)
        self.assertEqual([r['task'] for r in propios], ['Tubeado interior'])

    def test_el_filtro_por_portal_se_aplica_al_alcance_propio(self):
        snapshot = [
            {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
             'unit': 'A', 'status': 'X'},
            {'task': 'Tubeado interior', 'building': 'P2', 'floor': '1',
             'unit': 'A', 'status': 'M'},
        ]
        propios = gie._filtrar_snapshot_sagarde(snapshot, self.meta, {'P2'})
        self.assertEqual(len(propios), 1)
        self.assertEqual(propios[0]['building'], 'P2')

    def test_la_serie_historica_tambien_es_sagarde_only(self):
        historial = [
            ('01/08/2026', [
                {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
                 'unit': 'A', 'status': ''},
                {'task': 'Tabicado', 'building': 'P1', 'floor': '1',
                 'unit': 'A', 'status': 'X'},
            ]),
            ('08/08/2026', [
                {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
                 'unit': 'A', 'status': 'X'},
                {'task': 'Tabicado', 'building': 'P1', 'floor': '1',
                 'unit': 'A', 'status': 'X'},
            ]),
        ]
        serie = gie._serie_avance_sagarde(historial, self.meta)
        self.assertEqual([p['pct'] for p in serie], [0.0, 100.0])
        self.assertEqual([p['total'] for p in serie], [1, 1])


class TestCondicionantesSagarde(unittest.TestCase):

    def test_resume_solo_dependencias_incumplidas_de_tajos_propios(self):
        prioridades = {'detalle_items': [{
            'tarea_id': 'mecanizado',
            'trabajo': 'Mecanizado eléctrico',
            'propiedad': 'propio',
            'categoria': 'BLOQUEADO',
            'edificio': 'P1',
            'planta': '2',
            'dependencias_detalle': [
                {'id': 'pintura_primera', 'nombre': 'Pintura primera',
                 'estado': 'Pendiente', 'cumplida': False},
                {'id': 'doblar_cajas', 'nombre': 'Doblar cajas',
                 'estado': 'X', 'cumplida': True},
            ],
        }]}
        metadatos = {
            'pintura_primera': {'propiedad': 'externo'},
            'doblar_cajas': {'propiedad': 'propio'},
        }
        bloqueos = gie._bloqueadores_sagarde(prioridades, metadatos)
        self.assertEqual(len(bloqueos), 1)
        self.assertEqual(bloqueos[0]['trabajo'], 'Pintura primera')
        self.assertEqual(bloqueos[0]['propiedad'], 'externo')
        self.assertEqual(bloqueos[0]['afecta_celdas'], 1)
        self.assertEqual(bloqueos[0]['tajos_sagarde'], {'Mecanizado eléctrico'})


class TestMetadatosResuelvenTajosDeGaraje(unittest.TestCase):
    """Integracion garaje-obra, pieza 4 (25/09/2026): _indice_metadatos_tajos
    parte del catalogo COMPLETO (incluye los 42 tajos garaje_* desde la
    Fase 1 de la ampliacion), asi que el mismo indice ya calculado para
    vivienda resuelve tambien nombres de tajo de garaje -- sin construir
    un indice aparte. No es una suposicion: es justo lo que se comprobo
    a mano antes de escribir el codigo, y lo que el bug real de hoy
    (snapshot_garaje llevaba el ID en 'task' en vez del NOMBRE, y la
    pagina de garaje del PDF salia vacia) demuestra que hace falta
    verificar con un test, no solo de un vistazo."""

    def test_nombre_de_tajo_de_garaje_resuelve_con_ficha_de_vivienda(self):
        # Ficha de VIVIENDA tal cual, sin ningun tajo de garaje en su
        # propio 'tajos.detalle' -- la resolucion tiene que venir del
        # catalogo compartido, no de un aporte especifico de esta ficha.
        ficha_vivienda = {'tajos': {'detalle': [
            {'id': 'tabicado', 'nombre': 'Tabicado'},
        ]}}
        por_id, por_nombre = gie._indice_metadatos_tajos(ficha_vivienda)
        meta = por_nombre.get(gie._fold('Tubeado de viales'))
        self.assertIsNotNone(meta)
        self.assertEqual(meta['id'], 'garaje_tubeado_vial')
        self.assertEqual(meta['propiedad'], 'propio')

    def test_filtro_sagarde_con_task_como_nombre_incluye_garaje(self):
        ficha_vivienda = {'tajos': {'detalle': []}}
        _, por_nombre = gie._indice_metadatos_tajos(ficha_vivienda)
        snapshot = [
            {'task': 'Tubeado de viales', 'building': 'Garaje 1',
             'floor': 'S-1', 'unit': 'Vial A', 'status': 'X'},
        ]
        propios = gie._filtrar_snapshot_sagarde(snapshot, por_nombre)
        self.assertEqual(len(propios), 1)

    def test_filtro_sagarde_con_task_como_id_NO_resuelve(self):
        # El bug real encontrado hoy: si 'task' lleva el id
        # (garaje_tubeado_vial) en vez del nombre (Tubeado de viales),
        # _filtrar_snapshot_sagarde no encuentra metadatos y la celda se
        # descarta en silencio -- asi es como la pagina de garaje del
        # PDF salio vacia la primera vez. Este test deja el sintoma
        # documentado para que no vuelva a colarse sin que algo falle.
        ficha_vivienda = {'tajos': {'detalle': []}}
        _, por_nombre = gie._indice_metadatos_tajos(ficha_vivienda)
        snapshot = [
            {'task': 'garaje_tubeado_vial', 'building': 'Garaje 1',
             'floor': 'S-1', 'unit': 'Vial A', 'status': 'X'},
        ]
        propios = gie._filtrar_snapshot_sagarde(snapshot, por_nombre)
        self.assertEqual(propios, [])


class TestPdfEjecutivoConGaraje(unittest.TestCase):
    """Genera un PDF real (no solo inspecciona el story) porque es la
    unica forma de comprobar que reportlab no revienta con los
    argumentos nuevos y que el contenido de verdad aparece -- igual
    que se verifico a mano contra Gernika antes de comprobarlo aqui."""

    def _ficha_garaje(self):
        return {
            'version': 1, 'id': 'garaje_test_informe',
            'estructura': {'garajes': [{
                'id': 'g1', 'nombre': 'Garaje 1',
                'plantas': [{'id': 's1', 'nombre': 'S-1', 'zonas': [
                    {'id': 'z1', 'nombre': 'Vial A', 'tipo': 'vial'},
                ]}],
            }]},
            'tajos': {'detalle': [
                {'id': 'garaje_tubeado_vial', 'nombre': 'Tubeado de viales'},
            ]},
            'estados': {
                'g1__s1__garaje_tubeado_vial__z1': {
                    'v': 'X', 'f': '24/09/2026', 'r': 'rev_24092026'},
            },
            'revisiones': [{'id': 'rev_24092026', 'fecha': '24/09/2026'}],
            'dudas': [],
        }

    def _snapshot_y_prioridades_garaje(self):
        prioridades_garaje = priorizar_ficha_garaje(
            self._ficha_garaje(), obra='OBRA TEST INFORME',
            hoy=date(2026, 9, 25))
        snapshot_garaje = [
            {'task': item['trabajo'], 'floor': item['planta'],
             'building': item['edificio'], 'unit': item['unidad'],
             'status': item['estado']}
            for item in prioridades_garaje.get('detalle_items') or []
        ]
        return snapshot_garaje, prioridades_garaje

    def _generar_pdf(self, snapshot_garaje=None, prioridades_garaje=None):
        snapshot = [
            {'task': 'Tabicado', 'building': 'PORTAL 1', 'floor': 'PB',
             'unit': 'A', 'status': 'X'},
        ]
        with tempfile.TemporaryDirectory() as carpeta:
            salida = os.path.join(carpeta, 'informe.pdf')
            gie.generar_pdf_ejecutivo(
                'OBRA TEST INFORME', '25/09/2026', snapshot, salida,
                historial=[('25/09/2026', snapshot)],
                ficha={'tajos': {'detalle': []}},
                prioridades={'detalle_items': []},
                snapshot_garaje=snapshot_garaje,
                prioridades_garaje=prioridades_garaje,
                cierre=None, avisos_cierre=[],
            )
            import pdfplumber
            with pdfplumber.open(salida) as pdf:
                return [p.extract_text() or '' for p in pdf.pages]

    def test_sin_garaje_no_genera_pagina_de_garaje(self):
        paginas = self._generar_pdf()
        self.assertTrue(all('ÁMBITO: GARAJE' not in p for p in paginas))

    def test_con_garaje_genera_pagina_de_garaje_con_contenido_real(self):
        snapshot_garaje, prioridades_garaje = self._snapshot_y_prioridades_garaje()
        paginas_sin = self._generar_pdf()
        paginas_con = self._generar_pdf(snapshot_garaje, prioridades_garaje)

        # Una pagina mas que sin garaje (la nueva pagina GARAJE).
        self.assertEqual(len(paginas_con), len(paginas_sin) + 1)

        pagina_garaje = next(
            p for p in paginas_con if 'ÁMBITO: GARAJE' in p)
        # El unico tajo del fixture esta 100% terminado, asi que no sale
        # en "requieren atencion" (correcto: esa tabla solo lista lo
        # incompleto) -- pero su FASE si aparece en el desglose por fase,
        # que es contenido real de garaje de todas formas.
        self.assertIn('Instalación interior garaje', pagina_garaje)
        self.assertIn('Todos los tajos propios medidos están terminados',
                       pagina_garaje)

        # El resumen general (pagina 1) tiene que reflejar tambien el
        # garaje: con un tajo mas terminado que sin garaje.
        self.assertIn('100.0%', paginas_con[0])


if __name__ == '__main__':
    unittest.main()
