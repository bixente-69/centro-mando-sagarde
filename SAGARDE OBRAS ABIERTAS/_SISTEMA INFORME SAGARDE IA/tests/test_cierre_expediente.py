# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import cierre_expediente as ce


class TestCierreExpedienteVacioYCarga(unittest.TestCase):

    def test_vacio_tiene_los_cuatro_hitos_en_pendiente(self):
        datos = ce.vacio('OBRA X')
        self.assertEqual(set(datos['hitos']), set(ce.HITOS_ORDEN))
        for hito in ce.HITOS_ORDEN:
            self.assertEqual(datos['hitos'][hito]['estado'], 'pendiente')

    def test_cargar_fichero_ausente_no_lanza_y_devuelve_vacio(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'no_existe', 'cierre_expediente.json')
            datos, avisos = ce.cargar(ruta, obra='OBRA X')
            self.assertEqual(avisos, [])
            self.assertEqual(datos['hitos']['ensayos_instrumentales']['estado'],
                              'pendiente')

    def test_cargar_json_corrupto_no_lanza_y_avisa(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'cierre_expediente.json')
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write('{ esto no es json valido')
            datos, avisos = ce.cargar(ruta, obra='OBRA X')
            self.assertTrue(avisos)
            self.assertEqual(datos['hitos']['inspeccion_oca']['estado'],
                              'pendiente')

    def test_cargar_estado_no_reconocido_avisa_pero_conserva_el_dato(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'cierre_expediente.json')
            with open(ruta, 'w', encoding='utf-8') as f:
                json.dump({
                    'obra': 'OBRA X', 'actualizado': '15/08/2026',
                    'hitos': {'inspeccion_oca': {
                        'estado': 'valor_raro', 'fecha': '01/01/2026', 'nota': ''}},
                }, f)
            datos, avisos = ce.cargar(ruta, obra='OBRA X')
            self.assertTrue(any('valor_raro' in a for a in avisos))
            self.assertEqual(
                datos['hitos']['inspeccion_oca']['estado'], 'valor_raro')

    def test_guardar_y_recargar_conserva_los_datos(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'sub', 'cierre_expediente.json')
            datos = ce.vacio('OBRA X')
            datos['hitos']['cie_boletin'] = {
                'estado': 'hecho', 'fecha': '10/08/2026', 'nota': 'ok'}
            ce.guardar(ruta, datos)
            recargado, avisos = ce.cargar(ruta, obra='OBRA X')
            self.assertEqual(avisos, [])
            self.assertEqual(recargado['hitos']['cie_boletin']['estado'], 'hecho')
            self.assertEqual(recargado['hitos']['cie_boletin']['fecha'], '10/08/2026')


class TestActualizarHito(unittest.TestCase):

    def test_actualizar_hito_valido_escribe_y_devuelve_los_datos(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'cierre_expediente.json')
            datos = ce.actualizar_hito(
                ruta, 'OBRA X', 'libro_edificio', 'hecho',
                fecha='12/08/2026', nota='entregado en mano')
            self.assertEqual(datos['hitos']['libro_edificio']['estado'], 'hecho')
            self.assertTrue(os.path.isfile(ruta))

    def test_actualizar_hito_desconocido_lanza_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'cierre_expediente.json')
            with self.assertRaises(ValueError):
                ce.actualizar_hito(ruta, 'OBRA X', 'hito_que_no_existe', 'hecho')

    def test_actualizar_estado_no_valido_para_ese_hito_lanza_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, 'cierre_expediente.json')
            with self.assertRaises(ValueError):
                ce.actualizar_hito(ruta, 'OBRA X', 'cie_boletin', 'favorable')


if __name__ == '__main__':
    unittest.main()
