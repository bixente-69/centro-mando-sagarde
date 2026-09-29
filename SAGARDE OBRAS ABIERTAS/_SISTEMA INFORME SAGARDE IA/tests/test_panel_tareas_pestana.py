# -*- coding: utf-8 -*-
"""Regresiones de la pestaña propia de tareas manuales del panel."""

import os
import re
import sys
import tempfile
import unittest


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import panel_obra


def _prioridades():
    return {
        'sin_base': False, 'revision': '29/09/2026', 'version': '4.3',
        'catalogo_version': '1.3', 'resumen': {}, 'items': [],
        'inventario': [], 'dudas_pendientes': [], 'preguntas_orden': [],
        'prevision': [], 'avisos': [],
    }


def _generar(tareas=None, hilos=None):
    ficha = {
        '_disponible': True, 'datos': {}, 'personal': [], 'hitos': [],
        'riesgos': [], 'plan': [], 'tareas': list(tareas or []),
    }
    with tempfile.TemporaryDirectory() as carpeta:
        salida = os.path.join(carpeta, 'panel.html')
        panel_obra.generar_panel(
            obra='2026 OBRA PRUEBA', subtitulo='', historial=[],
            materiales={}, ficha=ficha, documentos=[],
            prioridades=_prioridades(), output_path=salida, hilos=hilos)
        with open(salida, encoding='utf-8') as f:
            return f.read()


def _vista(html, id_vista):
    """Recorta una vista de primer nivel sin confundir sus <section> hijas."""
    vistas = list(re.finditer(
        r'<section id="(v-[^"]+)" class="view(?: active)?">', html))
    for indice, coincidencia in enumerate(vistas):
        if coincidencia.group(1) == id_vista:
            fin = vistas[indice + 1].start() if indice + 1 < len(vistas) else len(html)
            return html[coincidencia.start():fin]
    raise AssertionError('No existe la vista ' + id_vista)


class TestPestanaTareas(unittest.TestCase):

    PENDIENTE = {
        'Tarea': 'Resolver consulta', 'Origen': 'Correo',
        'Fecha': '29/09/2026', 'Archivo': 'consulta.txt',
        'Estado': 'Pendiente',
    }
    HECHA = {
        'Tarea': 'Cerrar incidencia', 'Origen': 'Parte de obra',
        'Fecha': '28/09/2026', 'Archivo': 'parte.pdf',
        'Estado': 'Hecho',
    }
    HILO = {
        'mensajes': [{
            'lado': 'Sagarde', 'fecha': '2026-09-29', 'hora': '09:20',
            'de_a': 'Vicente → Amets', 'texto': 'Mensaje del hilo',
        }],
        'avisos': [],
    }

    def test_boton_tareas_existe_justo_despues_de_prioridades(self):
        html = _generar([self.PENDIENTE])
        nav = html[html.index('<div class="nav">'):html.index('</div>', html.index('<div class="nav">'))]
        posicion_prioridades = nav.index('data-view="v-prioridades"')
        posicion_tareas = nav.index('data-view="v-tareas"')
        self.assertLess(posicion_prioridades, posicion_tareas)
        self.assertNotIn('data-view=', nav[
            posicion_prioridades + len('data-view="v-prioridades"'):
            posicion_tareas])
        self.assertIn('☑ Tareas', nav)

    def test_vista_tareas_contiene_tarjeta_e_hilo_conductor(self):
        html = _generar(
            [self.PENDIENTE], hilos={'consulta.txt': self.HILO})
        tareas = _vista(html, 'v-tareas')
        self.assertIn("id='sec-tareas'", tareas)
        self.assertIn('<summary>Tareas manuales', tareas)
        self.assertIn('Ver el hilo conductor', tareas)
        self.assertIn('Mensaje del hilo', tareas)

    def test_prioridades_no_contiene_la_tabla_de_tareas(self):
        html = _generar([self.PENDIENTE])
        prioridades = _vista(html, 'v-prioridades')
        self.assertNotIn("id='sec-tareas'", prioridades)
        self.assertNotIn('<summary>Tareas manuales', prioridades)
        self.assertNotIn('marcar-tarea-hecha', prioridades)
        # La tarjeta-resumen del centro de mando se conserva y ahora abre
        # la pestaña propia, no una sección interior de Prioridades.
        self.assertIn('<h3>Tareas manuales</h3>', prioridades)
        self.assertIn('data-activa-view="v-tareas"', prioridades)

    def test_obra_sin_tareas_muestra_estado_vacio_y_no_contador_cero(self):
        html = _generar([])
        tareas = _vista(html, 'v-tareas')
        nav = html[html.index('<div class="nav">'):html.index('</div>', html.index('<div class="nav">'))]
        self.assertIn('Esta obra no tiene tareas manuales.', tareas)
        self.assertIn('data-view="v-tareas"', nav)
        self.assertNotIn('nav-contador', nav)

    def test_contador_de_pestana_coincide_con_pendientes(self):
        segunda = dict(self.PENDIENTE, Tarea='Pedir material')
        html = _generar([self.PENDIENTE, segunda, self.HECHA])
        nav = html[html.index('<div class="nav">'):html.index('</div>', html.index('<div class="nav">'))]
        self.assertIn(
            'class="nav-contador" data-pendientes="2">2</span>', nav)
        self.assertIn("data-pendientes='2'>2 pendientes", _vista(html, 'v-tareas'))

    def test_tarea_hecha_dice_deshacer_y_conserva_todos_los_datos(self):
        html = panel_obra._tabla_tareas_manuales(
            [self.HECHA], [], obra='2026 OBRA PRUEBA')
        self.assertIn("class='marcar-tarea-hecha' checked", html)
        self.assertIn('>Deshacer</span>', html)
        for atributo, valor in (
            ('obra', '2026 OBRA PRUEBA'),
            ('tarea', 'Cerrar incidencia'),
            ('origen', 'Parte de obra'),
            ('fecha', '28/09/2026'),
            ('archivo', 'parte.pdf'),
        ):
            self.assertIn(f"data-{atributo}='{valor}'", html)

    def test_script_mueve_filas_y_actualiza_ambos_contadores_y_vacios(self):
        html = panel_obra._tabla_tareas_manuales(
            [self.PENDIENTE, self.HECHA], [], obra='2026 OBRA PRUEBA')
        for selector in (
            '.tareas-pendientes', '.tareas-hechas',
            '.tareas-sin-pendientes', '.tareas-pendientes-contador',
            '.nav-contador', '.tarea-accion-texto',
        ):
            self.assertIn(selector, html)
        self.assertIn('asegurarBloquePendientes', html)
        self.assertIn('asegurarBloqueHechas', html)
        self.assertIn('appendChild(fila)', html)
        self.assertIn('actualizarContadoresTareas', html)
        self.assertIn("bloqueHechas.remove()", html)

    def test_tarjeta_bento_activa_tareas_mediante_el_boton_nav(self):
        html = _generar([self.PENDIENTE])
        self.assertIn('data-activa-view="v-tareas"', html)
        self.assertIn("document.querySelectorAll('[data-activa-view]')", html)
        self.assertIn('botonVista.click()', html)


if __name__ == '__main__':
    unittest.main()
