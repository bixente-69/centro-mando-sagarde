# -*- coding: utf-8 -*-
"""Prioridades leyendo de la base de obra en vez del historial crudo.

La base ya es el estado resuelto: trae la norma de la ultima revision
aplicada, la fecha y la revision de origen de cada celda, y las ubicaciones
descartadas fuera del arbol de estructura. Reconstruirlo desde el historial
crudo es lo que metia 4 viviendas inexistentes en Bolueta y 15 en Orueta.
"""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import fixtures
from priorizador_trabajos import (Catalogo, _agrupar_inventario,
                                  _agrupar_prioridades, _clasificar_detalle,
                                  estado_desde_ficha, verificar_rejilla)


def _item(ambito, planta, unidad, tarea='cuarto_tecnico', edificio='P1',
          categoria='VIABLE'):
    """Una celda de detalle con la forma que produce _clasificar_detalle."""
    return {
        'tarea_id': tarea, 'trabajo': tarea.replace('_', ' ').capitalize(),
        'trabajos_originales': [], 'propiedad': 'propio', 'ambito': ambito,
        'ambito_nombre': 'x', 'orden_ejecucion': 235, 'fase_nombre': 'F',
        'display_group': tarea, 'edificio': edificio, 'planta': planta,
        'unidad': unidad, 'estado': '', 'estado_actual': 'Pendiente',
        'categoria': categoria, 'motivo': 'Viable.',
        'dependencias_cumplidas': [], 'dependencias_bloqueantes': [],
        'dependencias_sin_dato': [], 'omitido_ultima': False,
        'forzado_entregado': False, 'ultima_fecha': '28/07/2026',
    }


def _ficha_con_estados(pares, tajos_extra=()):
    """pares: {(planta_id, tajo_id, ubicacion_id): estado}

    No se toca fixtures.ficha_minima(): test_ficha_obra comprueba que produce
    exactamente 8 celdas. Los tajos que hagan falta de mas se anaden aqui.
    """
    ficha = fixtures.ficha_minima()
    ficha['revisiones'] = [{'id': 'rev_28072026', 'fecha': '28/07/2026'}]
    for tajo in tajos_extra:
        ficha['tajos']['detalle'].insert(0, dict(tajo))
        ficha['tajos']['aplicables'].insert(0, tajo['id'])
    for (planta, tajo, ubi), valor in pares.items():
        clave = 'p1__%s__%s__%s' % (planta, tajo, ubi)
        ficha['estados'][clave] = {'v': valor, 'f': '28/07/2026',
                                   'r': 'rev_28072026'}
    return ficha


TABICADO = {'id': 'tabicado', 'nombre': 'Tabicado', 'ambito': 'vivienda',
            'propiedad': 'externo', 'fase': 'Inicio de obra', 'orden': 5}


class TestEstadoDesdeFicha(unittest.TestCase):

    def test_traduce_los_estados_medidos(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'X',
            ('pb', 'tubeado', 'B'): 'M',
            ('1', 'tubeado', 'A'): '/',
            ('1', 'tubeado', 'B'): 'P',
        })
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(estados[(('P1', 'PB', 'A'), 'tubeado')]['estado'], 'X')
        self.assertEqual(estados[(('P1', 'PB', 'B'), 'tubeado')]['estado'], 'M')
        self.assertEqual(estados[(('P1', '1', 'A'), 'tubeado')]['estado'], '/')
        self.assertEqual(estados[(('P1', '1', 'B'), 'tubeado')]['estado'], '')

    def test_conserva_el_estado_crudo_de_la_base(self):
        """'P', '?' y 'N' valen todos '' para el motor, pero significan cosas
        distintas y la clasificacion los tiene que poder separar."""
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): '?',
            ('pb', 'tubeado', 'B'): 'N',
            ('1', 'tubeado', 'A'): 'P',
        })
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(
            estados[(('P1', 'PB', 'A'), 'tubeado')]['estado_base'], '?')
        self.assertEqual(
            estados[(('P1', 'PB', 'B'), 'tubeado')]['estado_base'], 'N')
        self.assertEqual(
            estados[(('P1', '1', 'A'), 'tubeado')]['estado_base'], 'P')
        for loc in (('P1', 'PB', 'A'), ('P1', 'PB', 'B'), ('P1', '1', 'A')):
            self.assertEqual(estados[(loc, 'tubeado')]['estado'], '')

    def test_una_ubicacion_fuera_del_arbol_no_aparece(self):
        """Las excluidas no estan en estructura.bloques: recorrer el arbol es,
        por si solo, respetar estructura.exclusiones. Es el caso de las 4
        viviendas fantasma de PB en Bolueta y las 15 de Orueta."""
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        ficha['estados']['p1__pb__tubeado__FANTASMA'] = {
            'v': 'X', 'f': '28/07/2026', 'r': 'rev_28072026'}
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        unidades = {loc[2] for loc, _tid in estados}
        self.assertNotIn('FANTASMA', unidades)

    def test_conserva_la_fecha_y_la_revision_de_cada_celda(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        celda = estados[(('P1', 'PB', 'A'), 'tubeado')]
        self.assertEqual(celda['ultima_fecha'], '28/07/2026')

    def test_la_fecha_es_la_de_la_ultima_revision_registrada(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        ficha['revisiones'] = [
            {'id': 'rev_26072026', 'fecha': '26/07/2026'},
            {'id': 'rev_28072026', 'fecha': '28/07/2026'},
        ]
        _estados, fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(fecha, '28/07/2026')

    def test_la_fecha_no_depende_del_orden_de_la_lista(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        ficha['revisiones'] = [
            {'id': 'rev_28072026', 'fecha': '28/07/2026'},
            {'id': 'rev_26072026', 'fecha': '26/07/2026'},
        ]
        _estados, fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(fecha, '28/07/2026')

    def test_una_base_sin_celdas_no_revienta(self):
        ficha = fixtures.ficha_minima()
        estados, fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(estados, {})
        self.assertIsNone(fecha)

    def test_el_id_de_la_base_manda_si_el_catalogo_lo_conoce(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        celda = estados[(('P1', 'PB', 'A'), 'tubeado')]
        self.assertFalse(celda['desconocido'])
        self.assertEqual(celda['meta']['id'], 'tubeado')


class TestDesconocidoYNoAplica(unittest.TestCase):
    """'P', '?' y 'N' valen todos '' para el motor y significan cosas
    distintas. Confundirlos es la causa de casi todo lo que ha fallado aqui."""

    def _clasificar(self, pares, tajos_extra=()):
        ficha = _ficha_con_estados(pares, tajos_extra=tajos_extra)
        catalogo = Catalogo()
        estados, fecha = estado_desde_ficha(ficha, catalogo)
        detalle, _edad, _cad = _clasificar_detalle(estados, catalogo, fecha, {})
        return detalle

    def test_no_aplica_no_entra_en_el_calculo(self):
        detalle = self._clasificar({('pb', 'tubeado', 'A'): 'N'})
        self.assertEqual(detalle, [])

    def test_nunca_revisado_tiene_categoria_propia(self):
        detalle = self._clasificar({('pb', 'tubeado', 'A'): '?'})
        self.assertEqual(len(detalle), 1)
        self.assertEqual(detalle[0]['categoria'], 'SIN_REVISAR')

    def test_nunca_revisado_no_se_confunde_con_pendiente(self):
        detalle = self._clasificar({
            ('pb', 'tubeado', 'A'): '?',
            ('pb', 'tubeado', 'B'): 'P',
        })
        por_unidad = {d['unidad']: d['categoria'] for d in detalle}
        self.assertEqual(por_unidad['A'], 'SIN_REVISAR')
        self.assertNotEqual(por_unidad['B'], 'SIN_REVISAR')

    def test_nunca_revisado_gana_a_la_propiedad_del_tajo(self):
        """Un tajo de otro gremio que nadie ha mirado es 'sin revisar', no
        'otros gremios': la accion sigue siendo ir a mirarlo."""
        detalle = self._clasificar({('pb', 'tabicado', 'A'): '?'},
                                   tajos_extra=[TABICADO])
        self.assertEqual(detalle[0]['categoria'], 'SIN_REVISAR')

    def test_un_grupo_entero_sin_mirar_va_a_su_seccion(self):
        detalle = self._clasificar({
            ('pb', 'tabicado', 'A'): '?',
            ('pb', 'tabicado', 'B'): '?',
        }, tajos_extra=[TABICADO])
        inventario = _agrupar_inventario(detalle)
        self.assertEqual(inventario[0]['seccion'], 'SIN_REVISAR')
        self.assertEqual(inventario[0]['seccion_nombre'], 'Sin revisar nunca')

    def test_un_grupo_mezclado_no_se_va_a_sin_revisar(self):
        detalle = self._clasificar({
            ('pb', 'tabicado', 'A'): '?',
            ('pb', 'tabicado', 'B'): 'X',
        }, tajos_extra=[TABICADO])
        inventario = _agrupar_inventario(detalle)
        self.assertNotEqual(inventario[0]['seccion'], 'SIN_REVISAR')


class TestConteoPorAmbito(unittest.TestCase):
    """Hay UN cuarto tecnico en Bolueta, no 92. La hoja repite cada tajo en
    todas las ubicaciones, tambien los que son unicos del edificio."""

    def _grupos(self, ambito, tarea):
        detalle = [_item(ambito, p, u, tarea)
                   for p in ('PB', '1', '2') for u in ('A', 'B')]
        return _agrupar_prioridades(detalle)

    def test_un_tajo_de_edificio_cuenta_una_sola_unidad(self):
        grupos = self._grupos('edificio', 'cuarto_tecnico')
        self.assertEqual(len(grupos), 1)
        self.assertEqual(grupos[0]['n_unidades'], 1)
        self.assertEqual(grupos[0]['n_celdas'], 6)

    def test_un_tajo_de_zona_comun_cuenta_una_por_planta(self):
        grupos = self._grupos('zona_comun', 'tubeado_zzcc')
        self.assertEqual(grupos[0]['n_unidades'], 3)
        self.assertEqual(grupos[0]['n_celdas'], 6)

    def test_un_tajo_de_vivienda_cuenta_una_por_vivienda(self):
        grupos = self._grupos('vivienda', 'tubeado')
        self.assertEqual(grupos[0]['n_unidades'], 6)
        self.assertEqual(grupos[0]['n_celdas'], 6)

    def test_dos_portales_no_colapsan_en_uno(self):
        detalle = [_item('zona_comun', 'PB', 'A', 'tubeado_zzcc', edificio=e)
                   for e in ('PORTAL 1', 'PORTAL 2')]
        grupos = _agrupar_prioridades(detalle)
        self.assertEqual(grupos[0]['n_unidades'], 2)

    def test_el_recorte_se_puede_pedir_aparte(self):
        detalle = [_item('vivienda', 'PB', 'A', 'tajo_%d' % i)
                   for i in range(260)]
        grupos, recortados = _agrupar_prioridades(detalle, limite=200,
                                                  con_recorte=True)
        self.assertEqual(len(grupos), 200)
        self.assertEqual(recortados, 60)


class TestRejillaCompleta(unittest.TestCase):
    """La base tiene que ser una rejilla densa: ubicaciones x tajos. Si falta
    una celda, calcular sobre datos parciales es peor que avisar."""

    def _ficha_completa(self):
        pares = {(p, t, u): 'P'
                 for p in ('pb', '1') for u in ('A', 'B')
                 for t in ('tubeado', 'cableado')}
        return _ficha_con_estados(pares)

    def test_una_rejilla_completa_no_avisa(self):
        self.assertEqual(verificar_rejilla(self._ficha_completa()), [])

    def test_una_celda_que_falta_se_reporta_con_cifras(self):
        ficha = self._ficha_completa()
        del ficha['estados']['p1__pb__tubeado__A']
        avisos = verificar_rejilla(ficha)
        self.assertEqual(len(avisos), 1)
        self.assertIn('7', avisos[0])    # celdas encontradas
        self.assertIn('8', avisos[0])    # celdas esperadas

    def test_una_base_recien_creada_no_avisa(self):
        """Sin celdas no hay nada que comparar; el aviso lo da sin_base."""
        self.assertEqual(verificar_rejilla(fixtures.ficha_minima()), [])


if __name__ == '__main__':
    unittest.main()
