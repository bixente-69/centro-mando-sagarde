# -*- coding: utf-8 -*-
"""Pruebas del adaptador de Barakaldo (modo Gorliz: sin ficha_obra.json).

Barakaldo (104 VPO en 2 portales, garaje de 3 sotanos) se dio de alta el
05/10/2026 solo con el proyecto de ejecucion: no hay hoja del generador ni
estado de obra. El adaptador replica el patron de Gorliz y Olabeaga: no deduce
avance de planos ni fechas de fichero, solo incorpora revisiones EXPLICITAS
guardadas como JSON. Nada de estructura (portales, plantas, plazas) se inventa
aqui: lo que no se declara en el JSON, no existe para este adaptador.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import adaptadores.adaptador_barakaldo as ao


class TestCarpetaSinRevisiones(unittest.TestCase):
    """Sin JSON de revision todavia: historial vacio, nunca un error."""

    def test_historial_vacio_si_no_hay_carpeta_ia(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta_ia = os.path.join(
                temporal, 'OBRA AISLADA', 'INFORME SAGARDE IA')
            self.assertFalse(os.path.exists(carpeta_ia))
            with mock.patch.object(ao, '_cargar_historial_html', return_value=[]):
                self.assertEqual(ao.cargar_historial(carpeta_ia), [])


class TestParseoRegistrosExplicitos(unittest.TestCase):
    """Mismo contrato que adaptador_gorliz: 'registros' es una lista de
    dicts edificio/planta/unidad/tajo/estado, en texto libre."""

    def test_registro_de_garaje_valido(self):
        data = {
            'fecha': '06/10/2026',
            'registros': [
                {
                    'edificio': 'Garaje',
                    'planta': 'Garaje -2',
                    'unidad': 'Zona general',
                    'tajo': 'Tubeado de zonas comunes',
                    'estado': 'M',
                },
            ],
        }
        registros = ao._parsear_datos(data, '06/10/2026', origen='<test>')
        self.assertEqual(registros, [{
            'task': 'Tubeado de zonas comunes',
            'floor': 'Garaje -2',
            'building': 'Garaje',
            'unit': 'Zona general',
            'status': 'M',
        }])

    def test_estado_invalido_lanza_error(self):
        data = {
            'fecha': '06/10/2026',
            'registros': [{
                'edificio': 'Garaje', 'planta': 'Garaje -1',
                'unidad': 'Zona general', 'tajo': 'Cableado de zonas comunes',
                'estado': 'terminado',
            }],
        }
        with self.assertRaises(ValueError):
            ao._parsear_datos(data, '06/10/2026', origen='<test>')

    def test_registro_duplicado_lanza_error(self):
        registro = {
            'edificio': 'Garaje', 'planta': 'Garaje -2',
            'unidad': 'Zona general', 'tajo': 'Tubeado de zonas comunes',
            'estado': 'M',
        }
        data = {'fecha': '06/10/2026', 'registros': [registro, dict(registro)]}
        with self.assertRaises(ValueError):
            ao._parsear_datos(data, '06/10/2026', origen='<test>')

    def test_estado_n_se_descarta_no_bloquea(self):
        data = {
            'fecha': '06/10/2026',
            'registros': [{
                'edificio': 'Garaje', 'planta': 'Planta baja',
                'unidad': 'Trasteros', 'tajo': 'Cuarto tecnico',
                'estado': 'N',
            }],
        }
        self.assertEqual(ao._parsear_datos(data, '06/10/2026', origen='<test>'), [])

    def test_faltan_campos_obligatorios_lanza_error(self):
        data = {
            'fecha': '06/10/2026',
            'registros': [{'edificio': 'Garaje', 'estado': 'M'}],
        }
        with self.assertRaises(ValueError):
            ao._parsear_datos(data, '06/10/2026', origen='<test>')


class TestRutasYConstantes(unittest.TestCase):
    def test_carpeta_obra_apunta_a_la_carpeta_real(self):
        self.assertTrue(os.path.isdir(ao.CARPETA_OBRA),
                         f'no existe {ao.CARPETA_OBRA!r}')
        self.assertTrue(ao.CARPETA_OBRA.endswith('2026 BARAKALDO 104V OBRAS ESPECIALES'))

    def test_prefijo_revision_es_propio_de_barakaldo(self):
        self.assertEqual(ao.PREFIJO_REVISION, 'revision_barakaldo_')


class TestAltaEnElRegistro(unittest.TestCase):
    """Lo declarado en el registro tiene que llegar al adaptador: un alta que
    el motor ignora en silencio es la familia de fallos de este proyecto."""

    def test_registro_resuelve_nombre_y_alias(self):
        import registro_obras
        por_nombre = registro_obras.resolver_obra('2026 BARAKALDO 104V OBRAS ESPECIALES')
        self.assertIsNotNone(por_nombre)
        self.assertEqual(por_nombre['id'], 'barakaldo')
        self.assertIs(registro_obras.resolver_obra('barakaldo'), por_nombre)
        self.assertEqual(por_nombre['adaptador'], 'adaptador_barakaldo')

    def test_carpeta_del_registro_coincide_con_la_del_adaptador(self):
        import registro_obras
        cfg = registro_obras.resolver_obra('barakaldo')
        self.assertEqual(
            os.path.basename(ao.CARPETA_OBRA), cfg['carpeta_obra'])

    def test_obra_registrada_no_pisa_a_otras_ni_a_olabeaga(self):
        import registro_obras
        ids = [o['id'] for o in registro_obras.OBRAS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIsNot(
            registro_obras.resolver_obra('olabeaga'),
            registro_obras.resolver_obra('barakaldo'))


if __name__ == '__main__':
    unittest.main()
