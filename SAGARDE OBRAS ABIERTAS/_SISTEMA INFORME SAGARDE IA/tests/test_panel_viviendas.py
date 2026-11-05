# -*- coding: utf-8 -*-
"""Pestaña «Viviendas» y casilla del informe de obra. Datos inventados.

La parte de pantalla se prueba en Chromium real (Playwright de Node) y se salta
si no esta disponible. El resto es estatico.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import panel_obra
import viviendas_tajos as vt
from test_viviendas_tajos import CATALOGO, _ficha

NODE = shutil.which('node')

PRIORIDADES = {
    'sin_base': False, 'revision': '30/10/2026', 'version': '4.3',
    'catalogo_version': '1.3', 'resumen': {}, 'items': [], 'inventario': [],
    'dudas_pendientes': [], 'preguntas_orden': [], 'prevision': [],
    'avisos': [],
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


def _datos():
    return vt.datos_para_panel(_ficha(), CATALOGO)


def _vista(html, id_vista):
    vistas = list(re.finditer(
        r'<section id="(v-[^"]+)" class="view(?: active)?">', html))
    for i, m in enumerate(vistas):
        if m.group(1) == id_vista:
            fin = vistas[i + 1].start() if i + 1 < len(vistas) else len(html)
            return html[m.start():fin]
    raise AssertionError('No existe la vista ' + id_vista)


class TestEstatico(unittest.TestCase):

    def test_pestana_justo_despues_de_trabajos(self):
        html = _generar(viviendas=_datos())
        a = html.index('data-view="v-trabajos"')
        b = html.index('data-view="v-viviendas"')
        c = html.index('data-view="v-materiales"')
        self.assertTrue(a < b < c)

    def test_los_datos_incrustados_son_los_del_calculo(self):
        html = _generar(viviendas=_datos())
        m = re.search(r'<script id="viviendas-datos" type="application/json">'
                      r'(.*?)</script>', html, re.S)
        self.assertEqual(json.loads(m.group(1)), _datos())

    def test_incluye_el_calculo_de_la_pagina(self):
        v = _vista(_generar(viviendas=_datos()), 'v-viviendas')
        self.assertIn('periodoNatural', v)

    def test_sin_datos_dice_sin_datos_y_no_rompe(self):
        v = _vista(_generar(), 'v-viviendas')
        self.assertIn('Sin datos de viviendas', v)

    def test_casilla_en_el_informe_y_gancho_en_la_vista_previa(self):
        html = _generar(viviendas=_datos())
        self.assertIn('data-seccion="viviendas"', html)
        self.assertIn('viviendasHTMLInforme', html)
        self.assertIn("viviendas: '", html)

    def test_el_selector_ofrece_año_y_año_anterior(self):
        v = _vista(_generar(viviendas=_datos()), 'v-viviendas')
        self.assertIn("value='anio'", v)
        self.assertIn("value='anio_anterior'", v)

    def test_el_informe_lleva_sus_propios_controles_de_periodo_y_tajos(self):
        html = _generar(viviendas=_datos())
        panel = html[html.index('id="panel-informe-obra"'):
                     html.index('<div class="nav">')]
        self.assertIn('id=\'viv-periodo-inf\'', panel)
        self.assertIn("data-tajo='cableado'", panel)
        self.assertIn("data-tajo='embornado'", panel)

    def test_cableado_en_generar_todos(self):
        ruta = os.path.join(_BASE, 'generar_todos.py')
        with open(ruta, encoding='utf-8') as f:
            fuente = f.read()
        llamada = fuente[fuente.index('panel_obra.generar_panel('):]
        llamada = llamada[:llamada.index('\n            )')]
        self.assertIn('viviendas=viviendas', llamada)


GUION = r"""
const { chromium } = require('playwright');
(async () => {
  const [html, hoy] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.addInitScript(h => { window.__HOY_VIVIENDAS = h; }, hoy);
  const errores = [];
  p.on('pageerror', e => errores.push(String(e)));
  await p.goto('file://' + html);
  await p.click('button[data-view="v-viviendas"]');
  const leer = async () => p.evaluate(() => {
    const o = {};
    document.querySelectorAll('#viv-tabla tbody tr').forEach(tr => {
      o[tr.dataset.tajo] = {
        total: tr.querySelector('.viv-total').textContent.trim(),
        X: tr.querySelector('.viv-x').textContent.trim(),
        M: tr.querySelector('.viv-m').textContent.trim(),
        hechas: tr.querySelector('.viv-hechas').textContent.trim(),
        acum: tr.querySelector('.viv-acum').textContent.trim(),
        dudosas: tr.querySelector('.viv-dudosas').textContent.trim(),
      };
    });
    return { filas: o, cab: document.getElementById('viv-cabecera').textContent,
             informe: window.viviendasHTMLInforme() };
  });
  const res = {};
  res.inicial = await leer();
  res.inicial.periodo = await p.inputValue('#viv-periodo');
  for (const per of ['mes', 'mes_anterior', 'todo', 'semana']) {
    await p.selectOption('#viv-periodo', per);
    res[per] = await leer();
  }
  await p.selectOption('#viv-periodo', 'rango');
  await p.fill('#viv-desde', '2026-10-01');
  await p.fill('#viv-hasta', '2026-10-15');
  await p.dispatchEvent('#viv-hasta', 'change');
  res.rango = await leer();
  await p.fill('#viv-desde', '');
  await p.fill('#viv-hasta', '');
  await p.dispatchEvent('#viv-hasta', 'change');
  res.rango_vacio = await leer();
  await p.fill('#viv-desde', '2026-10-20');
  await p.fill('#viv-hasta', '2026-10-01');
  await p.dispatchEvent('#viv-hasta', 'change');
  res.rango_al_reves = await leer();
  await p.fill('#viv-desde', '2026-10-01');
  await p.fill('#viv-hasta', '2026-10-15');
  await p.dispatchEvent('#viv-hasta', 'change');
  // Año
  await p.selectOption('#viv-periodo', 'anio');
  res.anio = await leer();
  await p.selectOption('#viv-periodo', 'anio_anterior');
  res.anio_anterior = await leer();
  // Elegir tajos: quitar embornado en la pestaña
  await p.selectOption('#viv-periodo', 'mes_anterior');
  await p.evaluate(() => {
    const cb = document.querySelector('#viv-tajos input[data-tajo="embornado"]');
    cb.checked = false; cb.dispatchEvent(new Event('change', { bubbles: true }));
  });
  res.sin_embornado = await leer();
  // Sincronizacion: el informe cambia el periodo y la pestaña lo refleja
  await p.evaluate(() => {
    const s = document.getElementById('viv-periodo-inf');
    s.value = 'todo'; s.dispatchEvent(new Event('change', { bubbles: true }));
  });
  res.tab_tras_informe = await p.inputValue('#viv-periodo');
  // ... y quitar cableado desde el informe lo quita tambien en la pestaña
  await p.evaluate(() => {
    const cb = document.querySelector('#viv-tajos-inf input[data-tajo="cableado"]');
    cb.checked = false; cb.dispatchEvent(new Event('change', { bubbles: true }));
  });
  res.nada = await leer();
  res.cb_pestana = await p.evaluate(() => ({
    cableado: document.querySelector('#viv-tajos input[data-tajo="cableado"]').checked,
    embornado: document.querySelector('#viv-tajos input[data-tajo="embornado"]').checked }));
  await p.click('#viv-tajos .viv-todos');
  res.todos_antes = await leer();
  // Boton «Ninguno» y «Todos»
  await p.click('#viv-tajos .viv-ninguno');
  res.ninguno = await leer();
  await p.click('#viv-tajos .viv-todos');
  res.todos = await leer();
  // volver a marcar todo
  await p.evaluate(() => {
    document.querySelectorAll('#viv-tajos input[data-tajo]').forEach(c => {
      c.checked = true; c.dispatchEvent(new Event('change', { bubbles: true }));
    });
  });
  // «hoy» == dia de la ultima revision de campo
  await p.evaluate(() => { window.__HOY_VIVIENDAS = '2026-10-30'; });
  await p.selectOption('#viv-periodo', 'semana');
  res.mismo_dia = await leer();
  // Vista previa del informe de obra con SOLO la casilla Viviendas y octubre elegido
  await p.evaluate(() => { window.__HOY_VIVIENDAS = '2026-11-05'; });
  await p.selectOption('#viv-periodo', 'mes_anterior');
  await p.evaluate(() => {
    document.querySelectorAll('#panel-informe-obra input[type=checkbox]').forEach(c => { c.checked = false; });
    document.querySelector('input[data-seccion="viviendas"]').checked = true;
  });
  const [popup] = await Promise.all([
    p.waitForEvent('popup'),
    p.evaluate(() => generarVistaPreviaInforme()),
  ]);
  await popup.waitForLoadState();
  res.popup = await popup.content();
  res.errores = errores;
  console.log(JSON.stringify(res));
  await b.close();
})();
"""


@unittest.skipUnless(NODE, 'node no disponible')
class TestEnNavegador(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.html = os.path.join(cls.tmp.name, 'panel.html')
        ficha = {'_disponible': True, 'datos': {}, 'personal': [], 'hitos': [],
                 'riesgos': [], 'plan': [], 'tareas': []}
        panel_obra.generar_panel(
            obra='2026 OBRA INVENTADA', subtitulo='', historial=[],
            materiales={}, ficha=ficha, documentos=[],
            prioridades=PRIORIDADES, output_path=cls.html, viviendas=_datos())
        guion = os.path.join(cls.tmp.name, 'viv.js')
        with open(guion, 'w', encoding='utf-8') as f:
            f.write(GUION)
        r = subprocess.run([NODE, guion, cls.html, '2026-11-05'],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            # Solo se salta si NO HAY navegador. Si el guion falla por otra
            # causa, la prueba falla: un salto mudo daba por bueno un panel roto.
            if ('Cannot find module' in r.stderr
                    or "Executable doesn't exist" in r.stderr):
                raise unittest.SkipTest('Chromium/Playwright no disponible')
            raise AssertionError('el guion del navegador fallo:\n' + r.stderr[-800:])
        cls.res = json.loads(r.stdout)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_sin_errores_de_javascript(self):
        self.assertEqual(self.res['errores'], [])

    def test_noviembre_en_curso_son_cinco_dias_y_no_hay_terminadas(self):
        f = self.res['mes']['filas']['cableado']
        self.assertEqual((f['hechas'], f['acum']), ('0', '2'))
        self.assertIn('01/11/2026', self.res['mes']['cab'])
        self.assertIn('05/11/2026', self.res['mes']['cab'])

    def test_octubre_cuenta_la_de_campo(self):
        f = self.res['mes_anterior']['filas']['cableado']
        self.assertEqual((f['hechas'], f['acum'], f['dudosas']), ('1', '2', '0'))
        self.assertIn('31/10/2026', self.res['mes_anterior']['cab'])

    def test_desde_el_principio_y_estado_de_ahora(self):
        f = self.res['todo']['filas']['cableado']
        self.assertEqual((f['total'], f['X'], f['M']), ('3', '2', '1'))
        self.assertEqual(f['hechas'], '2')

    def test_los_tajos_sin_celdas_no_salen(self):
        self.assertEqual(sorted(self.res['todo']['filas']),
                         ['cableado', 'embornado'])

    def test_rango_a_mano_inclusivo(self):
        f = self.res['rango']['filas']['cableado']
        self.assertEqual(f['hechas'], '1')          # A el 10/10
        self.assertIn('15/10/2026', self.res['rango']['cab'])

    def test_rango_vacio_es_desde_el_principio_no_fechas_vacias(self):
        self.assertIn('desde el principio', self.res['rango_vacio']['cab'])
        self.assertNotIn('del —', self.res['rango_vacio']['cab'])

    def test_rango_al_reves_avisa_y_no_calcula(self):
        self.assertIn('posterior', self.res['rango_al_reves']['cab'])
        self.assertEqual(self.res['rango_al_reves']['filas'], {})

    def test_el_informe_saca_lo_que_se_esta_viendo(self):
        inf = self.res['rango']['informe']
        self.assertIn('Cableado eléctrico', inf)
        self.assertIn('01/10/2026', inf)
        self.assertIn('15/10/2026', inf)

    def test_año_en_curso_y_año_anterior(self):
        self.assertIn('01/01/2026', self.res['anio']['cab'])
        self.assertIn('05/11/2026', self.res['anio']['cab'])
        f = self.res['anio']['filas']['cableado']
        self.assertEqual(f['hechas'], '1')           # A el 10/10; B es historial
        self.assertEqual(self.res['anio']['filas']['cableado']['dudosas'], '1')
        self.assertIn('31/12/2025', self.res['anio_anterior']['cab'])
        self.assertEqual(
            self.res['anio_anterior']['filas']['cableado']['hechas'], '0')

    def test_elegir_tajos_en_la_pestana_quita_la_fila(self):
        self.assertEqual(sorted(self.res['sin_embornado']['filas']),
                         ['cableado'])

    def test_la_casilla_de_la_pestana_refleja_lo_que_se_cambia_en_el_informe(self):
        self.assertEqual(self.res['cb_pestana'],
                         {'cableado': False, 'embornado': False})

    def test_botones_ninguno_y_todos(self):
        # «Todos» devuelve lo que se habia quitado; «Ninguno» desde ahi vacia.
        self.assertEqual(sorted(self.res['todos_antes']['filas']),
                         ['cableado', 'embornado'])
        self.assertEqual(self.res['ninguno']['filas'], {})
        self.assertEqual(sorted(self.res['todos']['filas']),
                         ['cableado', 'embornado'])

    def test_periodo_elegido_en_el_informe_se_refleja_en_la_pestana(self):
        self.assertEqual(self.res['tab_tras_informe'], 'todo')

    def test_quitar_todos_los_tajos_avisa_y_no_enseña_tabla_vacia_muda(self):
        self.assertEqual(self.res['nada']['filas'], {})
        self.assertIn('al menos un tajo', self.res['nada']['cab'])

    def test_por_defecto_se_abre_en_este_mes(self):
        self.assertEqual(self.res['inicial']['periodo'], 'mes')
        self.assertIn('Noviembre', self.res['inicial']['cab'])

    def test_si_la_revision_es_de_hoy_lo_dice(self):
        self.assertIn('(hoy)', self.res['mismo_dia']['cab'])

    def test_la_vista_previa_del_informe_lleva_lo_elegido_en_la_pestana(self):
        pop = self.res['popup']
        self.assertIn('Viviendas', pop)
        self.assertIn('Octubre 2026', pop)
        self.assertIn('Cableado eléctrico', pop)
        self.assertIn('31/10/2026', pop)

    def test_la_cabecera_dice_la_antiguedad_de_la_ultima_revision(self):
        c = self.res['mes']['cab']
        self.assertIn('30/10/2026', c)
        self.assertIn('hace 6 días', c)


if __name__ == '__main__':
    unittest.main()
