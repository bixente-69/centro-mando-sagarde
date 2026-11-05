# -*- coding: utf-8 -*-
"""P1 sesion 2: pestana «Cambios» y seccion del informe de obra.

Datos inventados. Reglas: las dos fechas siempre visibles; un desconocido
nunca se pinta como cero; un fallo de datos no tumba el panel.
"""
import json
import os
import re
import sys
import tempfile
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import cambios_revision as cr
import panel_obra

PRIORIDADES = {
    'sin_base': False, 'revision': '02/11/2026', 'version': '4.3',
    'catalogo_version': '1.3', 'resumen': {}, 'items': [], 'inventario': [],
    'dudas_pendientes': [], 'preguntas_orden': [], 'prevision': [],
    'avisos': [],
}


def _cambios(transiciones, anterior='21/10/2026', fecha='02/11/2026',
             conocido=True, sin_detalle=0):
    return {
        'revision': {'revision_id': 'r3', 'fecha': fecha,
                     'fecha_anterior': anterior, 'conocido': conocido,
                     'transiciones': transiciones if conocido else None,
                     'celdas_cambiadas_sin_detalle': sin_detalle},
        'resumen': cr.resumir_transiciones(
            transiciones if conocido else None),
        'nombres_tajo': {'tubos': 'Tubos en vivienda', 'cajas': 'Cajas'},
        'nombres_planta': {('p1', 'pb'): 'PORTAL 1 · PB',
                           ('p1', 'p1'): 'PORTAL 1 · 1ª'},
    }


def _generar(**extra):
    ficha = {'_disponible': True, 'datos': {}, 'personal': [], 'hitos': [],
             'riesgos': [], 'plan': [], 'tareas': []}
    with tempfile.TemporaryDirectory() as carpeta:
        salida = os.path.join(carpeta, 'panel.html')
        panel_obra.generar_panel(
            obra='2026 OBRA INVENTADA', subtitulo='', historial=[],
            materiales={}, ficha=ficha, documentos=[],
            prioridades=PRIORIDADES, output_path=salida, **extra)
        with open(salida, encoding='utf-8') as f:
            return f.read()


def _vista(html, id_vista):
    vistas = list(re.finditer(
        r'<section id="(v-[^"]+)" class="view(?: active)?">', html))
    for i, m in enumerate(vistas):
        if m.group(1) == id_vista:
            fin = vistas[i + 1].start() if i + 1 < len(vistas) else len(html)
            return html[m.start():fin]
    raise AssertionError('No existe la vista ' + id_vista)


def _secciones(html):
    m = re.search(r'<script id="secciones-informe" type="application/json">'
                  r'(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


T = [['p1__pb__tubos__A', 'P', 'X'], ['p1__pb__tubos__B', '/', 'M'],
     ['p1__p1__cajas__A', 'X', 'P']]


class TestPestanaCambios(unittest.TestCase):

    def test_la_pestana_esta_entre_prioridades_y_tareas(self):
        html = _generar(cambios=_cambios(T))
        a = html.index('data-view="v-prioridades"')
        b = html.index('data-view="v-cambios"')
        c = html.index('data-view="v-tareas"')
        self.assertTrue(a < b < c)

    def test_cabecera_con_las_dos_fechas(self):
        v = _vista(_generar(cambios=_cambios(T)), 'v-cambios')
        self.assertIn('entre el 21/10/2026 y el 02/11/2026', v)

    def test_sin_revision_anterior_lo_dice_y_no_inventa_fecha(self):
        v = _vista(_generar(cambios=_cambios(T, anterior=None)), 'v-cambios')
        self.assertIn('sin revisión anterior', v)
        self.assertIn('02/11/2026', v)

    def test_muestra_totales_bajadas_y_reparto_con_nombres(self):
        v = _vista(_generar(cambios=_cambios(T)), 'v-cambios')
        self.assertIn('Tubos en vivienda', v)
        self.assertIn('PORTAL 1 · PB', v)
        # la bajada X -> P esta en su propia lista
        bajan = v[v.index('Bajan'):]
        self.assertIn('p1__p1__cajas__A', bajan)

    def test_cero_cambios_conocido_se_dice_explicitamente(self):
        v = _vista(_generar(cambios=_cambios([])), 'v-cambios')
        self.assertIn('0 cambios', v)

    def test_desconocido_no_se_pinta_como_cero(self):
        v = _vista(_generar(cambios=_cambios(
            None, conocido=False, sin_detalle=7)), 'v-cambios')
        self.assertIn('no se guardó el estado anterior', v)
        self.assertIn('7', v)
        self.assertNotIn('0 cambios', v)

    def test_sin_datos_de_cambios_el_panel_sigue_saliendo_y_lo_avisa(self):
        v = _vista(_generar(), 'v-cambios')
        self.assertIn('Sin revisiones registradas', v)

    def test_escapa_html_de_los_nombres(self):
        c = _cambios(T)
        c['nombres_tajo']['tubos'] = '<script>alert(1)</script>'
        v = _vista(_generar(cambios=c), 'v-cambios')
        self.assertNotIn('<script>alert(1)</script>', v)
        self.assertIn('&lt;script&gt;', v)

    def test_aviso_de_garajes_no_registrados(self):
        v = _vista(_generar(cambios=_cambios(T)), 'v-cambios')
        self.assertIn('garaje', v.lower())


class TestInformeDeObra(unittest.TestCase):

    def test_casilla_y_seccion_del_informe(self):
        html = _generar(cambios=_cambios(T))
        self.assertIn('data-seccion="cambios"', html)
        sec = _secciones(html)
        self.assertIn('cambios', sec)
        self.assertIn('entre el 21/10/2026 y el 02/11/2026', sec['cambios'])

    def test_el_informe_tiene_nombre_para_la_seccion(self):
        html = _generar(cambios=_cambios(T))
        self.assertIn("cambios: '", html)


class TestPrepararParaPanel(unittest.TestCase):

    def _log(self, entradas):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ruta = os.path.join(tmp.name, 'log.jsonl')
        with open(ruta, 'w', encoding='utf-8') as f:
            for e in entradas:
                f.write(json.dumps(e) + '\n')
        return ruta

    FICHA = {
        'revisiones': [{'id': 'rev_a', 'fecha': '21/10/2026'}],
        'estructura': {'bloques': [{'portales': [{
            'id': 'p1', 'nombre': 'PORTAL 1',
            'plantas': [{'id': 'pb', 'nombre': 'PB'}]}]}]},
    }
    CATALOGO = [{'id': 'tubos', 'nombre': 'Tubos en vivienda'}]

    def test_junta_log_ficha_y_catalogo(self):
        ruta = self._log([{'revision_id': 'r3', 'fecha': '02/11/2026',
                           'origen': 'html_digital',
                           'transiciones': [['p1__pb__tubos__A', 'P', 'X']]}])
        c = cr.preparar_para_panel(ruta, self.FICHA, self.CATALOGO)
        self.assertEqual(c['revision']['fecha_anterior'], '21/10/2026')
        self.assertEqual(c['nombres_tajo']['tubos'], 'Tubos en vivienda')
        self.assertEqual(c['nombres_planta'][('p1', 'pb')], 'PORTAL 1 · PB')
        self.assertEqual(c['resumen']['total'], 1)

    def test_sin_log_devuelve_none(self):
        self.assertIsNone(cr.preparar_para_panel(
            '/no/existe.jsonl', self.FICHA, self.CATALOGO))



class TestCableadoEnGenerarTodos(unittest.TestCase):
    """Lo declarado debe producir efecto: generar_todos pasa `cambios`."""

    def test_el_orquestador_pasa_cambios_a_generar_panel(self):
        import generar_todos
        ruta = os.path.join(_BASE, 'generar_todos.py')
        with open(ruta, encoding='utf-8') as f:
            fuente = f.read()
        llamada = fuente[fuente.index('panel_obra.generar_panel('):]
        llamada = llamada[:llamada.index('\n            )')]
        self.assertIn('cambios=cambios', llamada)
        self.assertTrue(hasattr(generar_todos, '_cambios_para_panel'))

    def test_obra_sin_log_da_none_sin_romper(self):
        import generar_todos
        with tempfile.TemporaryDirectory() as carpeta:
            self.assertIsNone(generar_todos._cambios_para_panel(
                {'nombre': 'X'}, carpeta, {}))

    def test_un_log_corrupto_avisa_y_no_tumba(self):
        import contextlib
        import io
        import generar_todos
        with tempfile.TemporaryDirectory() as carpeta:
            os.makedirs(os.path.join(carpeta, 'INFORME SAGARDE IA'))
            with open(os.path.join(carpeta, 'INFORME SAGARDE IA',
                                   'revisiones_aplicadas.jsonl'), 'w') as f:
                f.write('{esto no es json\n')
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                r = generar_todos._cambios_para_panel(
                    {'nombre': 'X'}, carpeta, {})
        self.assertIsNone(r)
        self.assertIn('[AVISO CAMBIOS]', salida.getvalue())


if __name__ == '__main__':
    unittest.main()
