# -*- coding: utf-8 -*-
"""El catalogo de tajos es una base de datos: SIEMPRE AMPLIABLE, nunca
ambigua.

Estas pruebas son el trinquete que lo mantiene sano al crecer. Ampliar el
catalogo es una operacion normal y prevista: un tajo nuevo en cualquier obra
se define una vez aqui y sirve para las 21. Lo que no puede pasar es que
crezca de forma que el motor no pueda resolver.
"""
import json
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CATALOGO = os.path.join(_BASE, 'reglas', 'CATALOGO_TAJOS.json')
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from priorizador_trabajos import Catalogo, ESTADO_VALOR


def _todos_los_tajos(catalogo):
    """Los comunes mas los propios de cada obra."""
    tajos = list(catalogo.get('tajos') or [])
    for cfg in (catalogo.get('obras') or {}).values():
        tajos.extend(cfg.get('tajos') or [])
    return tajos


class TestInvariantesCatalogo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(_CATALOGO, encoding='utf-8') as f:
            cls.catalogo = json.load(f)
        cls.comunes = cls.catalogo['tajos']
        cls.todos = _todos_los_tajos(cls.catalogo)

    def test_todo_tajo_declara_orden_propiedad_y_ambito(self):
        """Sin estos tres campos un tajo no se puede ni ordenar ni clasificar."""
        for tajo in self.todos:
            with self.subTest(tajo=tajo['id']):
                self.assertIsInstance(tajo.get('orden'), int)
                self.assertIn(tajo.get('propiedad'),
                              {'propio', 'externo', 'coordinacion'})
                self.assertIn(tajo.get('ambito'),
                              {'vivienda', 'zona_comun', 'edificio', 'dinamico'})

    def test_ningun_orden_duplicado_entre_tajos_comunes(self):
        vistos = {}
        for tajo in self.comunes:
            vistos.setdefault(tajo['orden'], []).append(tajo['id'])
        duplicados = {o: ids for o, ids in vistos.items() if len(ids) > 1}
        self.assertEqual(
            duplicados, {},
            'dos tajos con el mismo orden compiten y el desempate acaba '
            'siendo alfabetico: %r' % duplicados)

    def test_ninguna_dependencia_apunta_a_un_tajo_inexistente(self):
        ids = {t['id'] for t in self.todos}
        for tajo in self.todos:
            for dep in tajo.get('deps') or []:
                with self.subTest(tajo=tajo['id'], dep=dep['id']):
                    self.assertIn(dep['id'], ids)

    def test_ninguna_dependencia_apunta_hacia_delante(self):
        """Una dependencia posterior en la secuencia no se cumple nunca."""
        orden = {t['id']: t['orden'] for t in self.todos}
        for tajo in self.todos:
            for dep in tajo.get('deps') or []:
                if dep['id'] not in orden:
                    continue
                with self.subTest(tajo=tajo['id'], dep=dep['id']):
                    self.assertLess(orden[dep['id']], tajo['orden'])

    def test_ningun_alias_resuelve_a_dos_tajos_distintos(self):
        self.assertEqual(Catalogo().errores, [])

    def test_el_minimo_de_una_dependencia_es_un_estado_valido(self):
        """Un minimo que no corresponda a '/', 'M' o 'X' es inalcanzable."""
        validos = set(ESTADO_VALOR.values())
        for tajo in self.todos:
            for dep in tajo.get('deps') or []:
                with self.subTest(tajo=tajo['id'], dep=dep['id']):
                    self.assertIn(float(dep.get('minimo', 1.0)), validos)


if __name__ == '__main__':
    unittest.main()
