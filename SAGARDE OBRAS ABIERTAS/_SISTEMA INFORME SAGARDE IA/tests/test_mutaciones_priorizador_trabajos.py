# -*- coding: utf-8 -*-
"""Pruebas que matan mutaciones supervivientes de `priorizador_trabajos.py`.

Origen: auditoria por mutacion del 04/11/2026
(`_SISTEMA/docs/auditorias_nube_2026-11-04/B_mutaciones.md`). Hay una familia
que es la de este proyecto (`CLAUDE.md` §2, "algo declarado que el motor
ignora en silencio"): una dependencia declarada SIN `minimo` pasaba a no
bloquear nada y ninguna prueba se enteraba. Cada prueba dice que mutacion mata
(PTxx).

`_clasificar_detalle` se prueba con un catalogo de juguete (solo necesita
`meta()`), asi que no depende del catalogo real ni de ninguna obra.
"""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import motor_informes
import priorizador_trabajos as ps

LOC = ('P1', 'PB', 'A')
HOY = date(2026, 11, 4)


class CatalogoDeJuguete:
    def __init__(self, tajos):
        self.tajos = tajos

    def meta(self, task_id, fallback=None):
        return self.tajos.get(task_id, fallback or {})


def _meta(task_id, orden=10, deps=None, propiedad='propio'):
    meta = {'id': task_id, 'nombre': task_id.capitalize(),
            'propiedad': propiedad, 'ambito': 'vivienda',
            'fase': 'Interior', 'deps': deps or []}
    if orden is not None:
        meta['orden'] = orden
    return meta


def _celda(meta, estado_base, desconocido=False):
    estado = {'X': 'X', 'M': 'M', '/': '/', 'P': ''}.get(estado_base, '')
    return {'estado': estado, 'estado_base': estado_base,
            'originales': {meta['nombre']}, 'meta': meta,
            'desconocido': desconocido, 'loc': LOC, 'task_id': meta['id'],
            'primera_fecha': '01/11/2026', 'ultima_fecha': '01/11/2026',
            'conflicto': False, 'omitido_ultima': False,
            'forzado_entregado': False}


def _clasificar(*celdas, catalogo=None):
    estados = {(c['loc'], c['task_id']): c for c in celdas}
    catalogo = catalogo or CatalogoDeJuguete({c['task_id']: c['meta']
                                              for c in celdas})
    detalle, _edad, _caducada = ps._clasificar_detalle(
        estados, catalogo, '01/11/2026', {}, hoy=HOY)
    return {d['tarea_id']: d for d in detalle}


class TestPesosDeEstado(unittest.TestCase):

    def test_los_pesos_son_los_acordados(self):
        # Mata PT01. Con M=0.60 desde el 25/07/2026; cambiar uno mueve cada
        # porcentaje y cada dependencia de cada obra.
        self.assertEqual(ps.ESTADO_VALOR,
                         {'': 0.0, '/': 0.25, 'M': 0.60, 'X': 1.0})

    def test_priorizador_y_motor_de_informes_pesan_igual(self):
        # Ambos ficheros dicen en un comentario "si cambia aqui, cambiar
        # tambien alli". Esta es la prueba que lo hace cumplir.
        self.assertEqual(ps.ESTADO_VALOR, motor_informes.SCORE)

    def test_el_estado_se_normaliza_antes_de_pesarlo(self):
        # Mata PT05: ' m ' y 'x' son M y X; lo desconocido es vacio.
        self.assertEqual(ps._estado(' m '), 'M')
        self.assertEqual(ps._estado('x'), 'X')
        self.assertEqual(ps._estado('/'), '/')
        self.assertEqual(ps._estado('?'), '')
        self.assertEqual(ps._estado(None), '')


class TestDependencias(unittest.TestCase):

    def test_una_dependencia_sin_minimo_exige_terminado(self):
        # Mata PT16. Declarada sin `minimo`, vale 1.0 (X): con M no basta.
        # Si el valor por defecto fuera 0 la dependencia no bloquearia nunca,
        # en silencio.
        trab = _meta('trab', orden=20, deps=[{'id': 'dep'}])
        dep = _meta('dep')
        r = _clasificar(_celda(trab, 'P'), _celda(dep, 'M'))
        self.assertEqual(r['trab']['categoria'], 'BLOQUEADO')
        self.assertEqual(r['trab']['dependencias_bloqueantes'], ['Dep'])
        r = _clasificar(_celda(trab, 'P'), _celda(dep, 'X'))
        self.assertEqual(r['trab']['categoria'], 'VIABLE')

    def test_con_minimo_de_M_basta_una_M_pero_no_una_barra(self):
        # Mata PT02: M pesa 0.60 y el minimo 0.6 se cumple con M.
        trab = _meta('trab', orden=20, deps=[{'id': 'dep', 'minimo': 0.6}])
        dep = _meta('dep')
        r = _clasificar(_celda(trab, 'P'), _celda(dep, 'M'))
        self.assertEqual(r['trab']['categoria'], 'VIABLE')
        self.assertTrue(r['trab']['dependencias_detalle'][0]['cumplida'])
        r = _clasificar(_celda(trab, 'P'), _celda(dep, '/'))
        self.assertEqual(r['trab']['categoria'], 'BLOQUEADO')
        self.assertFalse(r['trab']['dependencias_detalle'][0]['cumplida'])


class TestTajoDesconocido(unittest.TestCase):

    def test_un_tajo_marcado_como_desconocido_va_a_dudas(self):
        # Mata PT23. La marca `desconocido` de la celda basta aunque el meta
        # del catalogo diga 'propio'; con `and` el tajo sin resolver seguiria
        # al calculo de dependencias y saldria VIABLE.
        meta = _meta('raro')
        r = _clasificar(_celda(meta, 'P', desconocido=True))
        self.assertEqual(r['raro']['categoria'], 'DUDAS')

    def test_un_tajo_de_propiedad_desconocida_va_a_dudas(self):
        meta = _meta('raro', propiedad='desconocido')
        r = _clasificar(_celda(meta, 'P', desconocido=False))
        self.assertEqual(r['raro']['categoria'], 'DUDAS')


class TestOrdenPorDefecto(unittest.TestCase):

    def test_un_tajo_sin_orden_se_ordena_el_ultimo(self):
        # Mata PT20: sin `orden` declarado vale 9999, no 0.
        sin = _meta('sin', orden=None)
        con = _meta('con', orden=5)
        estados = {(LOC, 'sin'): _celda(sin, 'P'), (LOC, 'con'): _celda(con, 'P')}
        detalle, _, _ = ps._clasificar_detalle(
            estados, CatalogoDeJuguete({'sin': sin, 'con': con}),
            '01/11/2026', {}, hoy=HOY)
        self.assertEqual([d['tarea_id'] for d in detalle], ['con', 'sin'])
        self.assertEqual([d['orden_ejecucion'] for d in detalle], [5, 9999])


if __name__ == '__main__':
    unittest.main()
