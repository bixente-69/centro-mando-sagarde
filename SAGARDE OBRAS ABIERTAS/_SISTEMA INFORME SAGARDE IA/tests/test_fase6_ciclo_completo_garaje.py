# -*- coding: utf-8 -*-
"""Fase 6: ciclo completo de garaje contra una obra de prueba, de punta a
punta -- alta desde hoja, revision desde hoja, y priorizador -- usando los
adaptadores reales (Fase 5), no fichas construidas a mano.

Ninguno de los tests existentes encadenaba las tres piezas: los de la
Fase 5 (tests/test_adaptadores_garaje.py) prueban los adaptadores contra
fixtures simbolicos; los de la Fase 3a (tests/test_priorizador_garaje.py)
prueban el priorizador contra fichas construidas directamente con
ficha_garajes.guardar, sin pasar nunca por un adaptador. Este fichero
cierra ese hueco: reproduce en miniatura la validacion manual hecha en
navegador real contra OBRA PRUEBA el 25/09/2026 (Fase 6 del plan de
ampliacion a garajes), para que quede protegida por la suite y no solo
por una verificacion puntual.

Usa el CATALOGO_TAJOS.json real (via validar_revision.cargar_catalogo_tajos)
en las tres piezas, a proposito: priorizador_trabajos.Catalogo carga
siempre el fichero real de disco (ruta fija en su constructor, sin forma
de inyectar uno sintetico) -- confirmado leyendo su codigo y comprobado
por mutacion (cambiar los deps de un catalogo de prueba en memoria no
alteraba el resultado del priorizador). Un catalogo sintetico aqui solo
para el alta/revision habria probado una combinacion que nunca ocurre en
produccion. Mismo patron que ya usa test_priorizador_garaje.py en toda
su suite (Catalogo() sin argumentos, nunca mockeado).
"""
import json
import os
import sys
import tempfile
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import adaptar_revision_garaje
import alta_garaje_desde_hoja
import priorizador_trabajos
import validar_revision


CATALOGO_REAL = validar_revision.cargar_catalogo_tajos()

# Tajo propio real cuya dependencia (tambien real) usamos a proposito:
# es el mismo par que se bloqueo en la verificacion manual en navegador
# el 25/09/2026 contra OBRA PRUEBA.
TAJO_DEPENDIENTE = 'garaje_centralizacion_modulos'
TAJO_DEPENDENCIA = 'garaje_pintura_1_recinto'


def _deps_reales(tajo_id):
    for tajo in CATALOGO_REAL['tajos']:
        if tajo['id'] == tajo_id:
            return tajo.get('deps') or []
    raise AssertionError(f'{tajo_id!r} no esta en el catalogo real')


ESTRUCTURA = {
    'obra': 'OBRA PRUEBA FASE 6',
    'garajes': [
        {
            'id': 'g1', 'nombre': 'Garaje 1',
            'plantas': [{
                'id': 'p1', 'nombre': 'S-1',
                'zonas': [
                    {'id': 'z_rellano', 'nombre': 'Rellano', 'tipo': 'rellano'},
                    {
                        'id': 'z_centralizacion',
                        'nombre': 'Centralización de contadores',
                        'tipo': 'cuarto_tecnico', 'funcion': 'centralizacion',
                    },
                ],
            }],
        },
    ],
    'tajos_seleccionados': [
        'garaje_tabicado', TAJO_DEPENDENCIA, TAJO_DEPENDIENTE,
    ],
}

_ESCAPE_ANGULO = chr(92) + 'u003c'  # <, construido sin ambiguedad


def _html_alta(datos):
    bloque = json.dumps(datos, ensure_ascii=False).replace('<', _ESCAPE_ANGULO)
    return (
        '<!DOCTYPE html><html><head>'
        '<script type="application/json" id="garaje-estructura">'
        + bloque + '</script></head><body></body></html>'
    )


def _html_revision(pares):
    celdas = ''.join(
        f'<span class="td-st" data-k="{clave}" data-st="{estado}"></span>'
        for clave, estado in pares
    )
    return '<!DOCTYPE html><html><body>' + celdas + '</body></html>'


class TestCatalogoRealTienelaDependenciaAsumida(unittest.TestCase):
    """Si el catalogo real cambia este par, el resto de la clase de abajo
    deja de probar lo que dice probar -- que falle aqui primero y claro,
    no en una aserción confusa mas abajo."""

    def test_garaje_centralizacion_modulos_depende_de_pintura_1_recinto(self):
        deps = _deps_reales(TAJO_DEPENDIENTE)
        ids_dep = {d['id'] for d in deps}
        self.assertIn(
            TAJO_DEPENDENCIA, ids_dep,
            f'{TAJO_DEPENDIENTE!r} ya no depende de {TAJO_DEPENDENCIA!r} '
            'en el catalogo real -- actualiza este test para usar el par '
            'correcto antes de confiar en el resto de esta clase.',
        )


class TestCicloCompletoGarajeObraPrueba(unittest.TestCase):
    """Reproduce la validacion manual de la Fase 6: alta -> revision (con
    N y una dependencia sin resolver EN OTRA zona) -> priorizador."""

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta_obra = os.path.join(self.temporal.name, 'obra')
        os.makedirs(self.carpeta_obra)

    def _escribir(self, nombre, contenido):
        ruta = os.path.join(self.temporal.name, nombre)
        with open(ruta, 'w', encoding='utf-8') as fichero:
            fichero.write(contenido)
        return ruta

    def test_alta_revision_y_priorizador_encadenados(self):
        # 1) Alta desde una hoja de verdad (misma forma que emite
        #    generateGarajeHTML tras la Fase 4).
        hoja_alta = self._escribir('HOJA ALTA.html', _html_alta(ESTRUCTURA))
        ficha, _ = alta_garaje_desde_hoja.alta_garaje_desde_hoja(
            hoja_alta, 'prueba',
            carpeta_obra_abs=self.carpeta_obra, catalogo=CATALOGO_REAL,
        )
        self.assertEqual(3, len(ficha['tajos']['detalle']))

        # 2) Revision desde una hoja de verdad. La dependencia SI existe
        #    en la obra (Rellano), pero nunca en Centralizacion -- el
        #    hallazgo de la Fase 1: una dependencia que existe en otro
        #    sitio de la obra pero no en ESTA ubicacion bloquea para
        #    siempre, no se trata como "no aplica". Incluye ademas un N,
        #    que debe excluirse del todo.
        hoja_revision = self._escribir(
            'REVISION GARAJE 25092026.html',
            _html_revision([
                (f'g1__p1__{TAJO_DEPENDENCIA}__z_rellano', 'X'),
                (f'g1__p1__{TAJO_DEPENDIENTE}__z_centralizacion', 'M'),
                ('g1__p1__garaje_tabicado__z_centralizacion', 'N'),
            ]),
        )
        ficha, cambios, avisos, _ = (
            adaptar_revision_garaje.adaptar_revision_garaje(
                hoja_revision, 'prueba',
                carpeta_obra_abs=self.carpeta_obra, catalogo=CATALOGO_REAL,
            )
        )
        self.assertEqual([], avisos)
        self.assertEqual(2, cambios['estados_nuevos'])
        self.assertNotIn(
            f'g1__p1__garaje_tabicado__z_centralizacion', ficha['estados'],
        )

        # 3) El priorizador real (mismo Catalogo() que produccion, sin
        #    mocks) debe ver la dependencia sin resolver en ESA zona
        #    concreta y bloquear -- no dar el tajo por viable solo
        #    porque su dependencia existe en algun sitio de la obra.
        resultado = priorizador_trabajos.priorizar_ficha_garaje(
            ficha, obra='OBRA PRUEBA FASE 6',
        )
        por_tarea_unidad = {
            (item['tarea_id'], item['unidad']): item
            for item in resultado['detalle_items']
        }
        bloqueado = por_tarea_unidad[
            (TAJO_DEPENDIENTE, 'Centralización de contadores')
        ]
        self.assertEqual('BLOQUEADO', bloqueado['categoria'])
        self.assertTrue(
            bloqueado['dependencias_bloqueantes'],
            'se esperaba al menos una dependencia bloqueante listada',
        )
        self.assertEqual(1, resultado['resumen']['bloqueados'])

        # El estado N nunca debe aparecer como un tajo del priorizador
        # (ni bloqueado, ni listo, ni de ningun tipo): esta excluido, no
        # es que "no aplica" cuente como otra categoria.
        self.assertNotIn(
            ('garaje_tabicado', 'Centralización de contadores'),
            por_tarea_unidad,
        )


if __name__ == '__main__':
    unittest.main()
