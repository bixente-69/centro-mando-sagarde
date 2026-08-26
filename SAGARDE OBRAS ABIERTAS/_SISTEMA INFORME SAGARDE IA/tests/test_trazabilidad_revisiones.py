# -*- coding: utf-8 -*-
"""Trazabilidad comun con datos y rutas exclusivamente sinteticos."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generar_todos as gt
import trazabilidad_revisiones as tr


def _revision(revision_id='pruebas__01/09/2026__tinta__12345678'):
    return {
        'revision_id': revision_id,
        'obra': 'pruebas',
        'fecha': '01/09/2026',
        'origen': 'tinta',
        'fuente': 'REVISION SINTETICA.pdf',
        'metadata': {
            'generado_por': 'test_trazabilidad_revisiones',
            'generado_en': '2026-09-01T12:00:00',
        },
    }


def _aplicacion():
    return {
        'escrito': True,
        'resumen': {
            'total': 6,
            'aceptadas': 5,
            'rechazadas': 1,
            'cambios': 2,
            'sin_cambio': 2,
            'descartadas': 1,
        },
    }


class TestTrazabilidadRevisiones(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)
        self.informe = self.raiz / 'INFORME SAGARDE IA'
        self.informe.mkdir()
        self.log = self.informe / tr.NOMBRE_LOG

    def tearDown(self):
        self.temporal.cleanup()

    def test_append_anade_sin_borrar_la_entrada_anterior(self):
        primera = _revision('revision_sintetica_1')
        segunda = _revision('revision_sintetica_2')

        self.assertTrue(tr.registrar_trazabilidad(
            _aplicacion(), self.log, revision=primera,
            salvaguarda_coincidio=True, celdas_comparadas=6))
        contenido_primero = self.log.read_text(encoding='utf-8')
        self.assertTrue(tr.registrar_trazabilidad(
            _aplicacion(), self.log, revision=segunda,
            salvaguarda_coincidio=True, celdas_comparadas=6))

        contenido_final = self.log.read_text(encoding='utf-8')
        self.assertTrue(contenido_final.startswith(contenido_primero))
        self.assertEqual(len(contenido_final.splitlines()), 2)

    def test_jsonl_es_legible_tras_varias_entradas(self):
        for indice in range(3):
            self.assertTrue(tr.registrar_trazabilidad(
                _aplicacion(), self.log,
                revision=_revision(f'revision_sintetica_{indice}'),
                salvaguarda_coincidio=True,
                celdas_comparadas=10 + indice,
            ))

        entradas = [
            json.loads(linea)
            for linea in self.log.read_text(encoding='utf-8').splitlines()
        ]
        self.assertEqual(
            [entrada['revision_id'] for entrada in entradas],
            [f'revision_sintetica_{indice}' for indice in range(3)])
        self.assertEqual(entradas[0]['obra'], 'pruebas')
        self.assertEqual(entradas[0]['celdas_cambiadas'], 2)
        self.assertEqual(entradas[0]['celdas_conservadas'], 2)
        self.assertEqual(entradas[0]['celdas_descartadas'], 1)
        self.assertTrue(
            entradas[0]['salvaguarda_doble_calculo_coincidio'])

    def test_fallo_del_log_no_impide_guardar_la_ficha_del_cutover(self):
        ficha_nueva = {'id': 'pruebas', 'estados': {}}
        resultado = {
            'coincide': True,
            'claves_comparadas': 6,
            'diferencias': [],
            'ficha_nueva': ficha_nueva,
            'revision': _revision(),
            'validacion': {'resumen': {'cambios': 2}},
            'aplicacion': _aplicacion(),
        }
        orden = []

        def guardar(*_args):
            orden.append('ficha_guardada')

        def fallar_log(*_args, **_kwargs):
            orden.append('log_fallido')
            raise OSError('fallo sintetico de escritura')

        salida = io.StringIO()
        with (
                mock.patch.object(
                    gt, '_correcciones_mas_recientes', return_value={}),
                mock.patch.object(gt, '_mapa_tajos_cortos', return_value={}),
                mock.patch.object(
                    gt, 'calcular_actualizacion_ficha_con_salvaguarda',
                    return_value=resultado),
                mock.patch.object(
                    gt.fichas, 'volcar_apartados', return_value=[]),
                mock.patch.object(gt.fichas, 'guardar', side_effect=guardar),
                mock.patch.object(tr, '_anadir_jsonl', side_effect=fallar_log),
                contextlib.redirect_stdout(salida)):
            ficha_resultado, aplicada = gt.actualizar_ficha_con_salvaguarda(
                {'id': 'pruebas', 'nombre': 'OBRA SINTETICA'},
                self.raiz, {'id': 'pruebas'}, [], '01/09/2026')

        self.assertTrue(aplicada)
        self.assertIs(ficha_resultado, ficha_nueva)
        self.assertEqual(orden, ['ficha_guardada', 'log_fallido'])
        self.assertIn('[AVISO TRAZABILIDAD]', salida.getvalue())
        self.assertIn('La ficha ya guardada se conserva', salida.getvalue())
        self.assertFalse(self.log.exists())

    def test_resultado_no_escrito_no_crea_log(self):
        aplicacion = _aplicacion()
        aplicacion['escrito'] = False
        with contextlib.redirect_stdout(io.StringIO()):
            registrado = tr.registrar_trazabilidad(
                aplicacion, self.log, revision=_revision(),
                salvaguarda_coincidio=True)
        self.assertFalse(registrado)
        self.assertFalse(self.log.exists())


if __name__ == '__main__':
    unittest.main()
