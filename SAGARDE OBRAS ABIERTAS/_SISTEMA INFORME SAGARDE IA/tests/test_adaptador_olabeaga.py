# -*- coding: utf-8 -*-
"""Pruebas del adaptador de Olabeaga (modo Gorliz: sin ficha_obra.json).

Olabeaga (30 viviendas + garajes y trasteros) esta en fase de garajes. No
existe todavia una ampliacion del generador de revisiones para garajes
(plazas sin numerar en el plano, sin rejilla que dar de alta), asi que este
adaptador replica el patron ya probado en produccion con Gorliz: no deduce
avance de planos ni fechas de fichero, solo incorpora revisiones EXPLICITAS
guardadas como JSON. Nada de estructura (bloques/portales/plazas) se inventa
aqui: lo que no se declara en el JSON, no existe para este adaptador.
"""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import adaptadores.adaptador_olabeaga as ao


class TestCarpetaSinRevisiones(unittest.TestCase):
    """Sin JSON de revision todavia: historial vacio, nunca un error."""

    def test_historial_vacio_si_no_hay_carpeta_ia(self):
        # La obra real aun no tiene 'INFORME SAGARDE IA' con revisiones.
        self.assertEqual(ao.cargar_historial(), [])


class TestParseoRegistrosExplicitos(unittest.TestCase):
    """Mismo contrato que adaptador_gorliz: 'registros' es una lista de
    dicts edificio/planta/unidad/tajo/estado, en texto libre."""

    def test_registro_de_garaje_valido(self):
        data = {
            'fecha': '24/09/2026',
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
        registros = ao._parsear_datos(data, '24/09/2026', origen='<test>')
        self.assertEqual(registros, [{
            'task': 'Tubeado de zonas comunes',
            'floor': 'Garaje -2',
            'building': 'Garaje',
            'unit': 'Zona general',
            'status': 'M',
        }])

    def test_estado_invalido_lanza_error(self):
        data = {
            'fecha': '24/09/2026',
            'registros': [{
                'edificio': 'Garaje', 'planta': 'Garaje -1',
                'unidad': 'Zona general', 'tajo': 'Cableado de zonas comunes',
                'estado': 'terminado',
            }],
        }
        with self.assertRaises(ValueError):
            ao._parsear_datos(data, '24/09/2026', origen='<test>')

    def test_registro_duplicado_lanza_error(self):
        registro = {
            'edificio': 'Garaje', 'planta': 'Garaje -2',
            'unidad': 'Zona general', 'tajo': 'Tubeado de zonas comunes',
            'estado': 'M',
        }
        data = {'fecha': '24/09/2026', 'registros': [registro, dict(registro)]}
        with self.assertRaises(ValueError):
            ao._parsear_datos(data, '24/09/2026', origen='<test>')

    def test_estado_n_se_descarta_no_bloquea(self):
        data = {
            'fecha': '24/09/2026',
            'registros': [{
                'edificio': 'Garaje', 'planta': 'Planta baja',
                'unidad': 'Trasteros', 'tajo': 'Cuarto tecnico',
                'estado': 'N',
            }],
        }
        self.assertEqual(ao._parsear_datos(data, '24/09/2026', origen='<test>'), [])

    def test_faltan_campos_obligatorios_lanza_error(self):
        data = {
            'fecha': '24/09/2026',
            'registros': [{'edificio': 'Garaje', 'estado': 'M'}],
        }
        with self.assertRaises(ValueError):
            ao._parsear_datos(data, '24/09/2026', origen='<test>')


class TestRutasYConstantes(unittest.TestCase):
    def test_carpeta_obra_apunta_a_la_carpeta_real(self):
        self.assertTrue(os.path.isdir(ao.CARPETA_OBRA),
                         f'no existe {ao.CARPETA_OBRA!r}')
        self.assertTrue(ao.CARPETA_OBRA.endswith('2026 OLABEAGA BILBAO'))

    def test_prefijo_revision_es_propio_de_olabeaga(self):
        self.assertEqual(ao.PREFIJO_REVISION, 'revision_olabeaga_')


if __name__ == '__main__':
    unittest.main()
