# -*- coding: utf-8 -*-
"""Pruebas de los criterios operativos confirmados del catálogo de tajos."""
import json
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CATALOGO = os.path.join(_BASE, 'reglas', 'CATALOGO_TAJOS.json')
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from priorizador_trabajos import Catalogo, priorizar_historial


class TestCatalogoTajosConfirmado(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(_CATALOGO, encoding='utf-8') as f:
            cls.catalogo = json.load(f)
        cls.tajos = {t['id']: t for t in cls.catalogo['tajos']}
        tajos_obispo = cls.catalogo['obras']['2025 BILBAO OBISPO ORUETA']['tajos']
        cls.tajos_obispo = {t['id']: t for t in tajos_obispo}

    def test_m_es_siempre_mas_del_50_por_ciento_del_tajo(self):
        self.assertEqual(
            self.catalogo['estados']['M'],
            'Más del 50 % del alcance del tajo',
        )

    def test_tajos_especializados_miden_su_propio_alcance(self):
        for tajo_id in (
            'pintura_primera',
            'pintura_segunda',
            'agujeros_iluminacion_zzcc',
            'iluminacion_rellanos',
        ):
            with self.subTest(tajo=tajo_id):
                self.assertIn('Más del 50 %', self.tajos[tajo_id]['estado_m'])

    def test_iluminacion_rellanos_solo_mide_colocacion_de_equipos(self):
        tajo = self.tajos['iluminacion_rellanos']
        self.assertIn('equipos', tajo['estado_m'].lower())
        self.assertIn('equipos', tajo['estado_x'].lower())
        self.assertNotIn('agujeros', tajo['estado_m'].lower())

    def test_techos_generales_son_solo_de_viviendas(self):
        self.assertEqual(self.tajos['techos']['ambito'], 'vivienda')

    def test_mecanizado_no_incluye_placas_ni_tapas(self):
        self.assertIn('sin placas', self.tajos['mecanizado']['estado_x'].lower())

    def test_pasillos_de_obispo_son_zonas_comunes(self):
        for tajo_id in (
            'pintura_pasillos',
            'agujeros_focos_pasillo',
            'cajas_techo_pasillo',
            'mecanismos_pasillo',
            'focos_pasillos',
        ):
            with self.subTest(tajo=tajo_id):
                self.assertEqual(
                    self.tajos_obispo[tajo_id]['ambito'],
                    'zona_comun',
                )

    def test_el_nombre_principal_de_cada_tajo_resuelve_sin_dudas(self):
        catalogo = Catalogo()
        for tajo in self.catalogo['tajos']:
            with self.subTest(tajo=tajo['id']):
                tajo_id, _meta, desconocido = catalogo.resolver(tajo['nombre'])
                self.assertEqual(tajo_id, tajo['id'])
                self.assertFalse(desconocido)

    def test_nombres_principales_especificos_de_obispo_resuelven(self):
        catalogo = Catalogo('2025 BILBAO OBISPO ORUETA')
        for tajo in self.tajos_obispo.values():
            with self.subTest(tajo=tajo['id']):
                tajo_id, _meta, desconocido = catalogo.resolver(tajo['nombre'])
                self.assertEqual(tajo_id, tajo['id'])
                self.assertFalse(desconocido)

    def test_cambio_de_alias_a_nombre_no_genera_desaparicion(self):
        base = {
            'floor': '1',
            'building': 'PORTAL 1',
            'unit': 'A',
            'status': '/',
        }
        historial = [
            ('27/07/2026', [dict(base, task='Apliques')]),
            ('28/07/2026', [dict(base, task='Apliques y enchufes de terraza')]),
        ]
        resultado = priorizar_historial(historial)
        codigos = {d['codigo'] for d in resultado['dudas_pendientes']}
        self.assertNotIn('TAJO_NUEVO', codigos)
        self.assertNotIn('OMITIDO_SIN_X', codigos)


if __name__ == '__main__':
    unittest.main()
