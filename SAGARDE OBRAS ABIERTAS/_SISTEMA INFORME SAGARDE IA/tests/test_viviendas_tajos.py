# -*- coding: utf-8 -*-
"""Viviendas por tajo electrico y periodo natural (peticion de Bixente 05/11/2026).

Cuenta, por tajo, cuantas viviendas estan X, M, /, P, ? y cuantas se
terminaron en un periodo NATURAL (semana lunes-domingo, mes 1-fin; el periodo
en curso llega solo hasta hoy). Datos inventados.

Reglas: M y / solo existen "ahora" (la ficha no guarda su historia); una
fecha de carga de historial no es una fecha de obra: esas viviendas no cuentan
como hechas en el periodo y se enseñan aparte (nunca se tiran ni se ponen a
cero); un desconocido no es cero.
"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import viviendas_tajos as vt

NODE = shutil.which('node')


def _ficha():
    """3 viviendas + 1 local; revisiones: una de historial y una de campo."""
    return {
        'revisiones': [
            {'id': 'rev_28072026', 'fecha': '28/07/2026', 'origen': ''},
            {'id': 'o__10/10/2026__html_digital__aa', 'fecha': '10/10/2026',
             'origen': 'hoja generada rellenada digitalmente, leida por la IA'},
            {'id': 'o__30/10/2026__html_digital__bb', 'fecha': '30/10/2026',
             'origen': 'hoja generada rellenada digitalmente, leida por la IA'},
        ],
        'estructura': {'bloques': [{'portales': [{'id': 'p1', 'plantas': [
            {'id': 'pb', 'ubicaciones': [
                {'id': 'L1', 'tipo': 'local'},
                {'id': 'A', 'tipo': 'vivienda'}]},
            {'id': '1', 'ubicaciones': [
                {'id': 'B', 'tipo': 'vivienda'},
                {'id': 'C', 'tipo': 'vivienda'}]},
        ]}]}]},
        'estados': {
            # cableado: A X (campo 10/10), B X (historial 28/07), C M
            'p1__pb__cableado__A': {'v': 'X', 'f': '10/10/2026',
                                    'r': 'o__10/10/2026__html_digital__aa'},
            'p1__1__cableado__B': {'v': 'X', 'f': '28/07/2026',
                                   'r': 'rev_28072026'},
            'p1__1__cableado__C': {'v': 'M', 'f': '30/10/2026',
                                   'r': 'o__30/10/2026__html_digital__bb'},
            # el local no es vivienda: nunca cuenta
            'p1__pb__cableado__L1': {'v': 'X', 'f': '10/10/2026',
                                     'r': 'o__10/10/2026__html_digital__aa'},
            # embornado: A X (30/10), B N, C sin celda
            'p1__pb__embornado__A': {'v': 'X', 'f': '30/10/2026',
                                     'r': 'o__30/10/2026__html_digital__bb'},
            'p1__1__embornado__B': {'v': 'N', 'f': '30/10/2026',
                                    'r': 'o__30/10/2026__html_digital__bb'},
        },
    }


CATALOGO = [{'id': 'cableado', 'nombre': 'Cableado eléctrico'},
            {'id': 'embornado', 'nombre': 'Embornado eléctrico'},
            {'id': 'telecableado', 'nombre': 'Telecableado'}]


class TestDatos(unittest.TestCase):

    def setUp(self):
        self.d = vt.datos_para_panel(_ficha(), CATALOGO)

    def test_solo_cuenta_viviendas_no_locales(self):
        self.assertEqual(self.d['n_viviendas'], 3)

    def test_solo_tajos_electricos_de_la_lista_y_con_celdas(self):
        ids = [t['id'] for t in self.d['tajos']]
        self.assertEqual(ids, ['cableado', 'embornado'])   # no telecableado

    def test_fecha_fiable_solo_si_viene_de_una_revision_de_campo(self):
        c = self.d['celdas']['cableado']          # A, B, C
        self.assertEqual(c[0], ['X', '2026-10-10', 1])
        self.assertEqual(c[1], ['X', '2026-07-28', 0])   # historial
        self.assertEqual(c[2], ['M', '2026-10-30', 1])

    def test_celda_inexistente_se_marca_aparte_no_se_pone_cero(self):
        self.assertEqual(self.d['celdas']['embornado'][2][0], '-')

    def test_ultima_revision_de_campo(self):
        self.assertEqual(self.d['ultima_revision'], '2026-10-30')

    def test_la_lista_declarada_existe_en_el_catalogo_real(self):
        ruta = os.path.join(_BASE, 'reglas', 'CATALOGO_TAJOS.json')
        with open(ruta, encoding='utf-8') as f:
            tajos = {t['id']: t for t in json.load(f)['tajos']}
        for tid in vt.TAJOS_ELECTRICOS:
            self.assertIn(tid, tajos, tid)
            self.assertEqual(tajos[tid]['ambito'], 'vivienda', tid)
            self.assertEqual(tajos[tid]['propiedad'], 'propio', tid)
        for fuera in ('telecableado', 'telembornado', 'telemecanizado',
                      'portero', 'termostatos'):
            self.assertNotIn(fuera, vt.TAJOS_ELECTRICOS)


class TestContar(unittest.TestCase):

    def setUp(self):
        self.d = vt.datos_para_panel(_ficha(), CATALOGO)

    def test_desde_el_principio(self):
        r = vt.contar(self.d, 'cableado', None, None)
        self.assertEqual((r['total'], r['X'], r['M'], r['/'], r['P']),
                         (3, 2, 1, 0, 0))
        self.assertEqual(r['hechas'], 2)          # todas las X
        self.assertEqual(r['dudosas'], 0)

    def test_periodo_octubre_cuenta_la_de_campo_y_aparta_la_de_historial(self):
        r = vt.contar(self.d, 'cableado', '2026-10-01', '2026-10-31')
        self.assertEqual(r['hechas'], 1)          # A, 10/10
        self.assertEqual(r['acumuladas'], 2)      # A y B (28/07) a fin de oct
        self.assertEqual(r['dudosas'], 0)         # B no cae dentro de octubre

    def test_periodo_con_fecha_de_historial_dentro_va_a_dudosas(self):
        r = vt.contar(self.d, 'cableado', '2026-07-01', '2026-07-31')
        self.assertEqual(r['hechas'], 0)
        self.assertEqual(r['dudosas'], 1)         # B: X con fecha de historial

    def test_periodo_sin_nada_es_cero_conocido(self):
        r = vt.contar(self.d, 'cableado', '2026-11-01', '2026-11-05')
        self.assertEqual((r['hechas'], r['dudosas']), (0, 0))
        self.assertEqual(r['acumuladas'], 2)

    def test_n_y_sin_celda_no_entran_en_el_total(self):
        r = vt.contar(self.d, 'embornado', None, None)
        self.assertEqual(r['total'], 1)           # solo A
        self.assertEqual(r['X'], 1)

    def test_los_limites_del_periodo_son_inclusivos(self):
        r = vt.contar(self.d, 'cableado', '2026-10-10', '2026-10-10')
        self.assertEqual(r['hechas'], 1)

    def test_m_y_barra_solo_son_de_ahora_no_dependen_del_periodo(self):
        a = vt.contar(self.d, 'cableado', '2026-07-01', '2026-07-31')
        b = vt.contar(self.d, 'cableado', None, None)
        self.assertEqual((a['M'], a['/']), (b['M'], b['/']))


class TestPeriodoNatural(unittest.TestCase):
    HOY = date(2026, 11, 5)          # jueves

    def p(self, tipo, hoy=None):
        return vt.periodo_natural(tipo, hoy or self.HOY)

    def test_esta_semana_es_lunes_a_hoy(self):
        self.assertEqual(self.p('semana')[:2], ('2026-11-02', '2026-11-05'))

    def test_semana_pasada_es_lunes_a_domingo(self):
        self.assertEqual(self.p('semana_pasada')[:2],
                         ('2026-10-26', '2026-11-01'))

    def test_el_lunes_esta_semana_tiene_un_solo_dia(self):
        self.assertEqual(self.p('semana', date(2026, 11, 2))[:2],
                         ('2026-11-02', '2026-11-02'))

    def test_este_mes_son_cinco_dias_el_5_de_noviembre(self):
        self.assertEqual(self.p('mes')[:2], ('2026-11-01', '2026-11-05'))

    def test_mes_anterior_es_el_mes_natural_completo(self):
        self.assertEqual(self.p('mes_anterior')[:2],
                         ('2026-10-01', '2026-10-31'))

    def test_mes_anterior_en_enero_es_diciembre_del_año_anterior(self):
        self.assertEqual(self.p('mes_anterior', date(2027, 1, 15))[:2],
                         ('2026-12-01', '2026-12-31'))

    def test_mes_concreto_pasado_y_en_curso(self):
        self.assertEqual(self.p('mes:2026-10')[:2], ('2026-10-01', '2026-10-31'))
        self.assertEqual(self.p('mes:2026-11')[:2], ('2026-11-01', '2026-11-05'))
        self.assertEqual(self.p('mes:2026-02')[:2], ('2026-02-01', '2026-02-28'))

    def test_este_año_va_del_1_de_enero_a_hoy(self):
        self.assertEqual(self.p('anio')[:2], ('2026-01-01', '2026-11-05'))

    def test_año_anterior_es_el_año_natural_completo(self):
        self.assertEqual(self.p('anio_anterior')[:2],
                         ('2025-01-01', '2025-12-31'))

    def test_el_1_de_enero_el_año_en_curso_tiene_un_solo_dia(self):
        self.assertEqual(self.p('anio', date(2027, 1, 1))[:2],
                         ('2027-01-01', '2027-01-01'))

    def test_todo_no_tiene_limites(self):
        self.assertEqual(self.p('todo')[:2], (None, None))

    def test_tipo_desconocido_falla_no_adivina(self):
        with self.assertRaises(ValueError):
            self.p('quincena')


@unittest.skipUnless(NODE, 'node no disponible')
class TestParidadConJavaScript(unittest.TestCase):
    """El mismo calculo escrito en Python y en la pagina debe dar lo mismo."""

    def _node(self, caso):
        ruta = os.path.join(_BASE, 'viviendas_calculo.js')
        guion = (
            "const J=require(%s);const c=JSON.parse(require('fs')"
            ".readFileSync(0,'utf8'));"
            "const out={periodos:c.periodos.map(([t,h])=>"
            "{const p=J.periodoNatural(t,h);return [p.desde,p.hasta];}),"
            "conteos:c.conteos.map(([d,t,a,b])=>J.contar(d,t,a,b))};"
            "console.log(JSON.stringify(out));" % json.dumps(ruta))
        r = subprocess.run([NODE, '-e', guion], input=json.dumps(caso),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_periodos_y_conteos_coinciden_en_un_barrido(self):
        rnd = random.Random(7)
        tipos = ['todo', 'semana', 'semana_pasada', 'mes', 'mes_anterior',
                 'mes:2026-02', 'mes:2026-10', 'mes:2027-01', 'anio',
                 'anio_anterior']
        periodos = []
        for i in range(0, 900, 7):
            hoy = date(2026, 1, 1) + timedelta(days=i)
            periodos += [[t, hoy.isoformat()] for t in tipos]
        datos = {'tajos': [{'id': 'cableado', 'nombre': 'x'}],
                 'n_viviendas': 40, 'ultima_revision': '2026-10-30',
                 'celdas': {'cableado': []}}
        for _ in range(40):
            v = rnd.choice(['X', 'X', 'M', '/', 'P', '?', 'N', '-'])
            f = (date(2026, 1, 1) + timedelta(days=rnd.randrange(400))
                 ).isoformat() if rnd.random() > 0.1 else None
            datos['celdas']['cableado'].append([v, f, rnd.choice([0, 1])])
        conteos = []
        for _ in range(300):
            a, b = sorted(rnd.sample(range(400), 2))
            ini = (date(2026, 1, 1) + timedelta(days=a)).isoformat()
            fin = (date(2026, 1, 1) + timedelta(days=b)).isoformat()
            conteos.append([datos, 'cableado', rnd.choice([None, ini]),
                            rnd.choice([None, fin])])
        caso = {'periodos': periodos, 'conteos': conteos}
        js = self._node(caso)
        for (t, h), (d, a) in zip(periodos, js['periodos']):
            esperado = vt.periodo_natural(t, date.fromisoformat(h))[:2]
            self.assertEqual((d, a), esperado, (t, h))
        for (dd, t, a, b), got in zip(conteos, js['conteos']):
            esperado = vt.contar(dd, t, a, b)
            for k, v in esperado.items():
                self.assertEqual(got[k], v, (k, a, b))



class TestPublicacion(unittest.TestCase):
    """«Generado pero nunca publicado» ya ha pasado: se comprueba."""

    def test_viviendas_calculo_js_no_esta_ignorado_por_git(self):
        ruta = os.path.join(_BASE, 'viviendas_calculo.js')
        try:
            # --no-index: sin el, un fichero ya versionado nunca cuenta como
            # ignorado y la prueba no fallaria aunque se quitase la linea.
            r = subprocess.run(['git', 'check-ignore', '-q', '--no-index', ruta],
                               cwd=_BASE, capture_output=True)
        except FileNotFoundError:
            self.skipTest('git no esta disponible')
        if r.returncode == 128:
            self.skipTest('esto no es una copia de trabajo de git')
        self.assertEqual(1, r.returncode,
                         'viviendas_calculo.js esta en .gitignore: falta su linea')


if __name__ == '__main__':
    unittest.main()
