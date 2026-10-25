# -*- coding: utf-8 -*-
"""Pestaña «Personal» del panel de obra (paso P4 de «Personal en obra»).

Sin navegador: comprueba el hueco de `panel_obra.generar_panel` (una obra sin datos de personal
sale como siempre; si la vista nueva falla, el panel sigue y lo dice), el contrato de
`panel_personal.vista_personal` (validación, datos incrustados, escapes, sin red, determinismo) y la
forma del módulo. Las cifras que ve la persona las calcula `personal_calculo.js` en el navegador:
eso lo comprueba `verificar_p4.py` con Playwright (fuera de `tests/`, necesita un navegador).
"""

import ast
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tokenize
import types
import unittest
from datetime import datetime
from unittest import mock


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import panel_obra

RUTA_MODULO = os.path.join(_BASE, 'panel_personal.py')
RUTA_CALCULO = os.path.join(_BASE, 'personal_calculo.js')


def _fila(fecha, ambito, nombre, horas, extra=0):
    return {'fecha': fecha, 'ambito': ambito, 'nombre': nombre, 'horas': horas, 'extra': extra}


# Datos inventados: octubre de una obra con vivienda y garaje, más tres días de septiembre.
FILAS_OLA = [
    _fila('2026-09-01', 'vivienda', 'Josu', 7.5), _fila('2026-09-02', 'vivienda', 'Josu', 7.5),
    _fila('2026-09-03', 'vivienda', 'Josu', 7.5),
    _fila('2026-10-05', 'vivienda', 'Rafa', 7.5), _fila('2026-10-06', 'vivienda', 'Rafa', 7.5),
    _fila('2026-10-10', 'vivienda', 'Mikel', 5, 5),
    _fila('2026-10-12', 'vivienda', 'Rafa', 7.5), _fila('2026-10-12', 'vivienda', 'Mikel', 7.5),
    _fila('2026-10-15', 'garaje', 'Andoni', 7.5), _fila('2026-10-15', 'garaje', 'Txomin', 7.5),
    _fila('2026-10-16', 'garaje', 'Andoni', 7.5),
    _fila('2026-10-21', 'vivienda', 'Mikel', 7.5), _fila('2026-10-21', 'vivienda', 'Txomin', 7.5),
    _fila('2026-10-22', 'vivienda', 'Mikel', 7.5), _fila('2026-10-22', 'vivienda', 'Txomin', 7.5),
]

PRIORIDADES = {
    'sin_base': False, 'revision': '24/10/2026', 'version': '4.3', 'catalogo_version': '1.3',
    'resumen': {}, 'items': [], 'inventario': [], 'dudas_pendientes': [], 'preguntas_orden': [],
    'prevision': [], 'avisos': [],
}
PERSONAL_FICHA = [{'Nombre': 'Ana Prueba', 'Categoría': 'Oficial', 'Horas': '40'}]
TABLA_FICHA = (
    '<table class="data"><thead><tr><th>Nombre</th><th>Categoría</th><th>Horas</th></tr></thead>'
    '<tbody><tr><td>Ana Prueba</td><td>Oficial</td><td>40</td></tr></tbody></table>')
SIN_PARAMETRO = object()


class _DatetimeFijo(datetime):
    @classmethod
    def now(cls, tz=None):
        instante = datetime(2026, 10, 25, 12, 0)
        return instante if tz is None else instante.replace(tzinfo=tz)


def _generar(personal=SIN_PARAMETRO, personal_obra_id=None, ficha_personal=None):
    """Genera un panel con datos inventados y devuelve su HTML."""
    ficha = {
        '_disponible': True, 'datos': {}, 'personal': list(ficha_personal or []), 'hitos': [],
        'riesgos': [], 'plan': [], 'tareas': [],
    }
    extra = {}
    if personal is not SIN_PARAMETRO:
        extra['personal'] = personal
    if personal_obra_id is not None:
        extra['personal_obra_id'] = personal_obra_id
    with tempfile.TemporaryDirectory() as carpeta:
        salida = os.path.join(carpeta, 'panel.html')
        with mock.patch.object(panel_obra, 'datetime', _DatetimeFijo):
            panel_obra.generar_panel(
                obra='2026 OBRA INVENTADA', subtitulo='', historial=[], materiales={}, ficha=ficha,
                documentos=[], prioridades=PRIORIDADES, output_path=salida, **extra)
        with open(salida, encoding='utf-8') as f:
            return f.read()


def _vista(html, id_vista):
    """Recorta una vista de primer nivel (`<section id="v-…" class="view…">`)."""
    vistas = list(re.finditer(r'<section id="(v-[^"]+)" class="view(?: active)?">', html))
    for indice, coincidencia in enumerate(vistas):
        if coincidencia.group(1) == id_vista:
            fin = vistas[indice + 1].start() if indice + 1 < len(vistas) else len(html)
            return html[coincidencia.start():fin]
    raise AssertionError('No existe la vista ' + id_vista)


def _secciones_informe(html):
    """Las secciones del informe a la carta, tal como las incrusta el panel."""
    m = re.search(r'<script id="secciones-informe" type="application/json">(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


def _modulo():
    """Importa `panel_personal`; si aún no existe, la prueba falla con un motivo legible."""
    try:
        return importlib.import_module('panel_personal')
    except ImportError as error:
        raise AssertionError('no se puede importar panel_personal: %r' % (error,))


class TestHuecoEnElPanel(unittest.TestCase):
    """`generar_panel(personal=…)`: sin datos, lo de siempre; con datos, la vista nueva."""

    def test_sin_datos_la_pestana_es_la_tabla_de_la_ficha(self):
        esperado = ('<section id="v-personal" class="view"><div class="card"><h3>Personal asignado</h3>'
                    + TABLA_FICHA + '</div></section>')
        for personal in (SIN_PARAMETRO, None, []):
            with self.subTest(personal=personal if personal is not SIN_PARAMETRO else 'sin parámetro'):
                html = _generar(personal, ficha_personal=PERSONAL_FICHA)
                self.assertEqual(esperado, _vista(html, 'v-personal').strip())

    def test_sin_datos_ni_ficha_dice_sin_datos(self):
        html = _generar(None)
        self.assertIn('<p class="empty">Sin datos en la ficha de obra.</p>', _vista(html, 'v-personal'))

    def test_las_tres_formas_de_no_dar_datos_producen_el_mismo_panel(self):
        sin_parametro = _generar(SIN_PARAMETRO, ficha_personal=PERSONAL_FICHA)
        self.assertEqual(sin_parametro, _generar(None, ficha_personal=PERSONAL_FICHA))
        self.assertEqual(sin_parametro, _generar([], ficha_personal=PERSONAL_FICHA))

    def test_con_datos_la_pestana_lleva_la_vista_nueva(self):
        _modulo()
        vista = _vista(_generar(FILAS_OLA, personal_obra_id='olabeaga', ficha_personal=PERSONAL_FICHA),
                       'v-personal')
        self.assertIn('id="pers-raiz"', vista)
        self.assertIn('data-obra="olabeaga"', vista)
        self.assertIn('<h3>Personal asignado</h3>', vista)
        self.assertNotIn(TABLA_FICHA, vista)

    def test_sin_id_de_obra_usa_el_nombre_de_la_obra(self):
        _modulo()
        vista = _vista(_generar(FILAS_OLA), 'v-personal')
        self.assertIn('data-obra="2026 OBRA INVENTADA"', vista)

    def test_el_informe_a_la_carta_sigue_con_la_tabla_de_la_ficha(self):
        esperado = "<div class='card'><h3>Personal asignado</h3>" + TABLA_FICHA + '</div>'
        self.assertEqual(esperado, _secciones_informe(
            _generar(None, ficha_personal=PERSONAL_FICHA))['personal'])
        _modulo()
        self.assertEqual(esperado, _secciones_informe(
            _generar(FILAS_OLA, ficha_personal=PERSONAL_FICHA))['personal'])

    def test_el_resto_del_panel_no_cambia_con_datos(self):
        _modulo()
        sin = _generar(None, ficha_personal=PERSONAL_FICHA)
        con = _generar(FILAS_OLA, personal_obra_id='olabeaga', ficha_personal=PERSONAL_FICHA)
        self.assertEqual(
            sin.replace(_vista(sin, 'v-personal'), ''), con.replace(_vista(con, 'v-personal'), ''))

    def test_si_la_vista_falla_el_panel_sale_con_aviso_y_con_la_tabla_de_la_ficha(self):
        falso = types.ModuleType('panel_personal')

        def vista_personal(obra_id, filas):
            raise RuntimeError('fallo <inventado>')

        falso.vista_personal = vista_personal
        with mock.patch.dict(sys.modules, {'panel_personal': falso}):
            html = _generar(FILAS_OLA, ficha_personal=PERSONAL_FICHA)
        vista = _vista(html, 'v-personal')
        self.assertIn('class="banner bad"', vista)
        self.assertIn('RuntimeError: fallo &lt;inventado&gt;', vista)
        self.assertIn(TABLA_FICHA, vista)
        sin = _generar(None, ficha_personal=PERSONAL_FICHA)
        self.assertEqual(sin.replace(_vista(sin, 'v-personal'), ''),
                         html.replace(vista, ''), 'el aviso no debe tocar el resto del panel')

    def test_si_el_modulo_no_se_puede_importar_el_panel_sale_con_aviso(self):
        with mock.patch.dict(sys.modules, {'panel_personal': None}):
            vista = _vista(_generar(FILAS_OLA, ficha_personal=PERSONAL_FICHA), 'v-personal')
        self.assertIn('class="banner bad"', vista)
        self.assertRegex(vista, 'ImportError|ModuleNotFoundError')
        self.assertIn(TABLA_FICHA, vista)


class TestVistaPersonal(unittest.TestCase):
    """Contrato de `panel_personal.vista_personal`."""

    @classmethod
    def setUpClass(cls):
        cls.m = _modulo()

    def vista(self, filas=None, obra_id='olabeaga'):
        return self.m.vista_personal(obra_id, FILAS_OLA if filas is None else filas)

    def datos_incrustados(self, html):
        m = re.search(r'<script id="pers-datos" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(m, 'falta el bloque <script id="pers-datos" type="application/json">')
        return json.loads(m.group(1))

    def test_devuelve_un_fragmento_con_la_estructura_pedida(self):
        html = self.vista()
        self.assertIsInstance(html, str)
        self.assertTrue(html.lstrip().startswith('<div id="pers-raiz" class="pers" data-obra="olabeaga">'))
        for esperado in ('data-pers-p="semana"', 'data-pers-p="mes"', 'data-pers-p="anio"', 'data-pers-p="obra"',
                         'data-pers-m="-1"', 'data-pers-m="1"', 'data-pers-a="todo"',
                         'data-pers-a="vivienda"', 'data-pers-a="garaje"', 'id="pers-etiqueta"',
                         'id="pers-contenido"'):
            self.assertIn(esperado, html)
        self.assertNotIn('<html', html.lower())
        self.assertNotIn('<body', html.lower())

    def test_las_filas_incrustadas_son_las_recibidas_mas_la_obra(self):
        incrustadas = self.datos_incrustados(self.vista())
        self.assertEqual([dict(f, obra='olabeaga') for f in FILAS_OLA], incrustadas)

    def test_una_fila_sin_extra_se_incrusta_sin_inventar_un_extra(self):
        fila = {'fecha': '2026-10-01', 'ambito': 'vivienda', 'nombre': 'Ana', 'horas': 7.5}
        self.assertEqual([dict(fila, obra='o')], self.datos_incrustados(self.m.vista_personal('o', [fila])))

    def test_horas_ausentes_se_incrustan_como_null_no_como_cero(self):
        fila = _fila('2026-10-01', 'vivienda', 'Ana', None, None)
        incrustada = self.datos_incrustados(self.m.vista_personal('o', [fila]))[0]
        self.assertIsNone(incrustada['horas'])
        self.assertIsNone(incrustada['extra'])

    def test_incrusta_personal_calculo_js_tal_cual(self):
        with open(RUTA_CALCULO, encoding='utf-8') as f:
            calculo = f.read()
        self.assertIn(calculo, self.vista(), 'personal_calculo.js debe ir entero y sin tocar (una sola implementación)')

    def test_el_calculo_va_envuelto_en_una_funcion_para_no_crear_globales(self):
        with open(RUTA_CALCULO, encoding='utf-8') as f:
            calculo = f.read()
        patron = r'\(function\s*\(\)\s*\{\s*' + re.escape(calculo.strip()) + r'\s*\}\)\(\);?\s*</script>'
        self.assertIsNotNone(re.search(patron, self.vista()),
                             'personal_calculo.js debe ir dentro de (function () { … })();')

    def test_un_nombre_con_script_no_rompe_la_pagina(self):
        malo = '</script><img src=x onerror=alert(1)>&  '
        html = self.vista([_fila('2026-10-01', 'vivienda', malo, 7.5)])
        self.assertEqual(3, len(re.findall(r'</script', html, re.I)),
                         'solo deben cerrarse los 3 scripts del módulo (cálculo, datos y vista)')
        self.assertNotIn('<img', html)
        self.assertNotIn(' ', html)
        self.assertNotIn(' ', html)
        self.assertEqual(malo, self.datos_incrustados(html)[0]['nombre'])

    def test_un_nombre_con_comentario_html_no_rompe_la_pagina(self):
        html = self.vista([_fila('2026-10-01', 'vivienda', '<!-- x', 7.5)])
        with open(RUTA_CALCULO, encoding='utf-8') as f:
            self.assertNotIn('<!--', html.replace(f.read(), ''))

    def test_el_id_de_obra_se_escapa_en_el_atributo(self):
        html = self.m.vista_personal('a"b<c>&', FILAS_OLA)
        self.assertIn('data-obra="a&quot;b&lt;c&gt;&amp;"', html)
        self.assertEqual('a"b<c>&', self.datos_incrustados(html)[0]['obra'])

    def test_lista_vacia_solo_dice_que_no_hay_jornadas(self):
        html = self.m.vista_personal('olabeaga', [])
        self.assertEqual(
            '<p class="empty pers-vacio">Sin jornadas de personal anotadas en esta obra.</p>', html.strip())

    def test_datos_invalidos_se_rechazan_con_un_mensaje_legible(self):
        buenas = _fila('2026-10-01', 'vivienda', 'Ana', 7.5)
        casos = {
            'clave fuera del esquema': dict(buenas, dni='1'),
            'falta la fecha': {k: v for k, v in buenas.items() if k != 'fecha'},
            'falta el nombre': {k: v for k, v in buenas.items() if k != 'nombre'},
            'fecha con otro formato': dict(buenas, fecha='01/10/2026'),
            'fecha imposible': dict(buenas, fecha='2026-02-30'),
            'fecha que no es texto': dict(buenas, fecha=20261001),
            'ámbito desconocido': dict(buenas, ambito='local'),
            'nombre que no es texto': dict(buenas, nombre=None),
            'horas en texto': dict(buenas, horas='7,5'),
            'horas booleanas': dict(buenas, horas=True),
            'horas NaN': dict(buenas, horas=float('nan')),
            'horas infinitas': dict(buenas, horas=float('inf')),
            'extra en texto': dict(buenas, extra='1'),
            'la fila no es un dict': ['2026-10-01'],
        }
        for nombre, mala in casos.items():
            with self.subTest(nombre):
                with self.assertRaises(ValueError) as contexto:
                    self.m.vista_personal('olabeaga', [buenas, mala])
                self.assertIn('2', str(contexto.exception), 'el mensaje debe decir la fila (la 2)')

    def test_entradas_que_no_son_una_lista_de_filas_se_rechazan(self):
        for malo in (None, 'texto', {'fecha': '2026-10-01'}, 5):
            with self.subTest(malo=malo):
                with self.assertRaises(ValueError):
                    self.m.vista_personal('olabeaga', malo)

    def test_obra_id_vacio_o_que_no_es_texto_se_rechaza(self):
        for malo in ('', None, 3):
            with self.subTest(malo=malo):
                with self.assertRaises(ValueError):
                    self.m.vista_personal(malo, FILAS_OLA)

    def test_los_valores_raros_de_horas_no_se_rechazan_en_python(self):
        """Negativas o de 30 h: las cuenta como no válidas `PersonalCalculo` y la vista lo avisa."""
        html = self.vista([_fila('2026-10-01', 'vivienda', 'Ana', -3), _fila('2026-10-01', 'vivienda', 'Ana', 30, 0)])
        self.assertEqual(2, len(self.datos_incrustados(html)))

    def test_no_modifica_las_filas_recibidas(self):
        filas = [dict(f) for f in FILAS_OLA]
        self.vista(filas)
        self.assertEqual(FILAS_OLA, filas)

    def test_es_determinista(self):
        self.assertEqual(self.vista(), self.vista())

    def test_sin_red_ni_ficheros_externos(self):
        html = self.vista()
        self.assertIsNone(re.search(r'\b(?:src|href)\s*=', html, re.I), 'no debe cargar ni enlazar nada')
        for prohibido in ('http://', 'https://', '@import', 'url(', 'fetch(', 'XMLHttpRequest', 'WebSocket',
                          'localStorage', 'sendBeacon', 'eval(', 'new Function'):
            self.assertNotIn(prohibido, html)

    def test_el_trabajador_se_llama_nombre_no_alias_ni_mote(self):
        html = self.vista().lower()
        self.assertIsNone(re.search(r'\b(?:alias|mote)\b', html))

    def test_no_usa_current_script_ni_crea_globales_evidentes(self):
        html = self.vista()
        self.assertNotIn('currentScript', html)
        self.assertNotIn('document.write', html)


class TestFormaDelModulo(unittest.TestCase):
    """El código debe poder leerse: la pasada de legibilidad del paso 02 no se repite a mano."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(RUTA_MODULO):
            raise AssertionError('falta panel_personal.py')
        with open(RUTA_MODULO, encoding='utf-8') as f:
            cls.texto = f.read()

    def test_lineas_de_como_mucho_120_columnas(self):
        largas = [i + 1 for i, linea in enumerate(self.texto.splitlines()) if len(linea) > 120]
        self.assertEqual([], largas, 'líneas demasiado largas: %s' % largas[:10])

    def test_ninguna_sentencia_python_separada_con_punto_y_coma(self):
        with open(RUTA_MODULO, 'rb') as f:
            separadores = [t.start[0] for t in tokenize.tokenize(f.readline)
                           if t.type == tokenize.OP and t.string == ';']
        self.assertEqual([], separadores, 'varias sentencias en una línea: %s' % separadores[:10])

    def test_sin_texto_roto_por_la_codificacion(self):
        for roto in ('Ã', 'â€', 'Â', '�'):
            self.assertNotIn(roto, self.texto)

    def test_tiene_comentarios_y_docstrings(self):
        with open(RUTA_MODULO, 'rb') as f:
            comentarios = [t for t in tokenize.tokenize(f.readline) if t.type == tokenize.COMMENT]
        self.assertGreaterEqual(len(comentarios), 12, 'faltan comentarios que expliquen el porqué')
        modulo = ast.parse(self.texto)
        sin_docstring = [f.name for f in ast.walk(modulo)
                         if isinstance(f, ast.FunctionDef) and not ast.get_docstring(f)]
        self.assertEqual([], sin_docstring, 'funciones sin docstring')

    def test_solo_biblioteca_estandar(self):
        permitidos = {'json', 'os', 're', 'html', 'datetime', 'string', 'math', 'functools', 'typing'}
        importados = set()
        for nodo in ast.walk(ast.parse(self.texto)):
            if isinstance(nodo, ast.Import):
                importados.update(a.name.split('.')[0] for a in nodo.names)
            elif isinstance(nodo, ast.ImportFrom):
                importados.add((nodo.module or '').split('.')[0])
        self.assertEqual(set(), importados - permitidos)

    def test_una_unica_funcion_publica(self):
        publicas = [n.name for n in ast.parse(self.texto).body
                    if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]
        self.assertEqual(['vista_personal'], publicas)


class TestPublicacion(unittest.TestCase):
    """«Generado pero nunca publicado» ya ha pasado con obras_revisiones.js: se comprueba."""

    def test_personal_calculo_js_no_esta_ignorado_por_git(self):
        try:
            resultado = subprocess.run(['git', 'check-ignore', '-q', RUTA_CALCULO], cwd=_BASE,
                                       capture_output=True)
        except FileNotFoundError:
            self.skipTest('git no está disponible')
        if resultado.returncode == 128:
            self.skipTest('esto no es una copia de trabajo de git')
        self.assertEqual(1, resultado.returncode,
                         'personal_calculo.js está en .gitignore: la lista blanca necesita su línea')


if __name__ == '__main__':
    unittest.main()
