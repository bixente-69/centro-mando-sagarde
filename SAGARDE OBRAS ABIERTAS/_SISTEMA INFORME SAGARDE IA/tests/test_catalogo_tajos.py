# -*- coding: utf-8 -*-
"""Pruebas de los criterios operativos confirmados del catálogo de tajos."""
import json
import os
import sys
import unittest
from datetime import date

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CATALOGO = os.path.join(_BASE, 'reglas', 'CATALOGO_TAJOS.json')
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import fixtures
from priorizador_trabajos import Catalogo, priorizar_ficha


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

    def test_un_alias_resuelve_igual_que_el_nombre_principal(self):
        """Antes esto se probaba sobre el historial crudo: una revision decia
        'Apliques' y la siguiente 'Apliques y enchufes de terraza', y el motor
        inventaba a la vez TAJO_NUEVO y OMITIDO_SIN_X.

        Leyendo de la base ese caso no existe —la base guarda un id por tajo—
        pero el invariante sigue vigente por otra via: un tajo cuya CLAVE no
        esta en el catalogo pero cuyo NOMBRE es un alias tiene que resolver
        limpio y recibir su orden. Es lo que arregla los 18 tajos de Orueta.
        """
        ficha = fixtures.ficha_minima()
        ficha['tajos']['detalle'] = [
            {'id': 'apliques_viejo', 'nombre': 'Apliques', 'orden': 9999},
        ]
        ficha['tajos']['aplicables'] = ['apliques_viejo']
        ficha['revisiones'] = [{'id': 'r', 'fecha': '28/07/2026'}]
        ficha['estados'] = {
            'p1__pb__apliques_viejo__A': {'v': '/', 'f': '28/07/2026',
                                          'r': 'r'},
        }
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        codigos = {d['codigo'] for d in resultado['dudas_pendientes']}
        codigos |= {p['codigo'] for p in resultado['preguntas_orden']}
        self.assertNotIn('TAJO_NUEVO', codigos)
        self.assertNotIn('TAJO_FUERA_DEL_CATALOGO', codigos)
        self.assertNotIn('ORDEN_SIN_CONFIRMAR', codigos)
        self.assertEqual(ficha['tajos']['detalle'][0]['orden'], 310)

    def test_fotovoltaica_y_cuarto_tecnico_sueltos_ya_no_existen(self):
        """27/09/2026, Bixente: se desglosan en zonas con sub-tajos (ver
        los dos tests siguientes) y el tajo suelto desaparece del
        catálogo. Los datos ya guardados con estos ids en fichas antiguas
        no se migran (decisión explícita: 'no hagas migraciones')."""
        self.assertNotIn('fotovoltaica', self.tajos)
        self.assertNotIn('cuarto_tecnico', self.tajos)

    def test_la_cadena_de_fotovoltaica_encadena_sus_seis_pasos(self):
        cadena = [
            'fv_paneles_instalacion', 'fv_paneles_cableado',
            'fv_paneles_tierra', 'fv_strings_cableado',
            'fv_equipos_protecciones', 'fv_puesta_marcha',
        ]
        for tajo_id in cadena:
            with self.subTest(tajo=tajo_id):
                self.assertIn(tajo_id, self.tajos)
                tajo = self.tajos[tajo_id]
                self.assertEqual(tajo['propiedad'], 'propio')
                self.assertEqual(tajo['ambito'], 'edificio')
        self.assertEqual(self.tajos[cadena[0]]['deps'], [])
        for previo, siguiente in zip(cadena, cadena[1:]):
            deps = [d['id'] for d in self.tajos[siguiente]['deps']]
            self.assertEqual(
                deps, [previo],
                f'{siguiente} debería depender solo de {previo}')

    def test_soportes_de_antena_y_pararrayos_son_independientes(self):
        """Bixente, 27/09/2026: soportes distintos para antena y
        pararrayos (no comparten un único tajo de soporte)."""
        self.assertIn('cub_soporte_antena', self.tajos)
        self.assertIn('cub_soporte_pararrayos', self.tajos)
        self.assertEqual(self.tajos['cub_soporte_antena']['deps'], [])
        self.assertEqual(self.tajos['cub_soporte_pararrayos']['deps'], [])

        deps_instalacion_antena = [
            d['id'] for d in self.tajos['cub_antena_instalacion']['deps']]
        self.assertEqual(deps_instalacion_antena, ['cub_soporte_antena'])
        deps_instalacion_pararrayos = [
            d['id']
            for d in self.tajos['cub_pararrayos_instalacion']['deps']]
        self.assertEqual(
            deps_instalacion_pararrayos, ['cub_soporte_pararrayos'])

    def test_pararrayos_no_lleva_tajo_de_tierra_propio(self):
        """Bixente, 27/09/2026, textual: 'tierra de pararrayos ya es el
        cableado del mismo, por eso lo he omitido' -- el propio conductor
        de bajada hace de tierra. La antena sí lleva un tajo de tierra
        aparte, distinto de su cableado."""
        self.assertNotIn('cub_pararrayos_tierra', self.tajos)
        self.assertIn('cub_antena_tierra', self.tajos)
        deps_tierra_antena = [
            d['id'] for d in self.tajos['cub_antena_tierra']['deps']]
        self.assertEqual(deps_tierra_antena, ['cub_antena_cableado'])


if __name__ == '__main__':
    unittest.main()
