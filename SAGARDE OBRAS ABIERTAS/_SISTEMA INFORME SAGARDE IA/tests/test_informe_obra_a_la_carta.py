# -*- coding: utf-8 -*-
"""El informe de obra a la carta lee del mismo calculo que el panel: estas
pruebas comprueban que lo que se embebe como JSON es exactamente lo que
la pestana correspondiente ya pinta, nunca un calculo aparte."""
import json
import os
import sys
import tempfile
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import panel_obra


def _prioridades(**extra):
    base = {
        'sin_base': False, 'revision': '28/07/2026', 'version': '4.3',
        'catalogo_version': '1.3', 'resumen': {}, 'items': [],
        'inventario': [], 'dudas_pendientes': [], 'preguntas_orden': [],
        'prevision': [], 'avisos': [],
    }
    base.update(extra)
    return base


def _generar(obra='Obra de prueba', **kwargs):
    ficha = kwargs.pop('ficha', {
        '_disponible': True, 'datos': {}, 'personal': [], 'hitos': [],
        'riesgos': [], 'plan': [], 'tareas': [],
    })
    with tempfile.TemporaryDirectory() as carpeta:
        salida = os.path.join(carpeta, 'panel.html')
        panel_obra.generar_panel(
            obra=obra, subtitulo='', historial=kwargs.pop('historial', []),
            materiales=kwargs.pop('materiales', {}), ficha=ficha,
            documentos=kwargs.pop('documentos', []),
            prioridades=kwargs.pop('prioridades', _prioridades()),
            output_path=salida, **kwargs)
        with open(salida, encoding='utf-8') as f:
            return f.read()


def _extraer_secciones(html):
    inicio = html.index('<script id="secciones-informe" type="application/json">')
    inicio = html.index('>', inicio) + 1
    fin = html.index('</script>', inicio)
    return json.loads(html[inicio:fin])


class TestBotonInformeObra(unittest.TestCase):

    def test_el_boton_aparece_junto_al_ejecutivo(self):
        html = _generar()
        self.assertIn('Informe Ejecutivo PDF', html)
        self.assertIn('Informe de obra', html)
        pos_ejecutivo = html.index('Informe Ejecutivo PDF')
        pos_a_la_carta = html.index('Informe de obra')
        self.assertLess(pos_ejecutivo, pos_a_la_carta)


class TestSeccionesEmbebidas(unittest.TestCase):

    def test_el_json_tiene_las_ocho_claves_esperadas(self):
        html = _generar()
        secciones = _extraer_secciones(html)
        self.assertEqual(set(secciones.keys()), {
            'trabajos', 'materiales', 'personal', 'prioridades',
            'riesgos', 'normativa', 'documentos', 'cierre',
        })

    def test_prioridades_tiene_los_cinco_subapartados(self):
        html = _generar(prioridades=_prioridades(
            resumen={'bloqueados': 1, 'sin_revisar': 1},
            inventario=[{
                'seccion': 'BLOQUEADO', 'trabajo': 'B', 'propiedad': 'propio',
                'orden_ejecucion': 1, 'fase_nombre': 'f', 'n_ubicaciones': 1,
                'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
                'subtajos': [],
            }],
        ))
        secciones = _extraer_secciones(html)
        self.assertEqual(set(secciones['prioridades'].keys()), {
            'estado_proyecto', 'que_hacer_ahora', 'tajos_bloqueados',
            'tareas_manuales', 'sin_revisar',
        })
        self.assertIn('Tajos bloqueados', secciones['prioridades']['tajos_bloqueados'])

    def test_el_contenido_embebido_coincide_con_la_pestana_visible(self):
        """La prueba central de esta tarea: el JSON no puede decir una cosa
        mientras la pagina visible dice otra. Se compara contra la seccion
        real v-riesgos, que no pasa por ningun envoltorio nuevo."""
        html = _generar(prioridades=_prioridades(
            resumen={'bloqueados': 2},
        ))
        secciones = _extraer_secciones(html)
        seccion_riesgos_visible = html[
            html.index('<section id="v-riesgos"'):
            html.index('<section id="v-normativa"')]
        self.assertIn(secciones['riesgos'], seccion_riesgos_visible)

    def test_obra_sin_base_no_revienta_y_prioridades_sale_vacio(self):
        html = _generar(prioridades=_prioridades(
            sin_base=True, avisos=['sin base']))
        secciones = _extraer_secciones(html)
        self.assertEqual(secciones['prioridades'], {})


class TestMenuDeSeleccion(unittest.TestCase):

    def test_el_menu_esta_oculto_por_defecto(self):
        html = _generar()
        inicio = html.index('id="panel-informe-obra"')
        self.assertIn('display:none', html[inicio:inicio + 60])

    def test_las_ocho_secciones_simples_tienen_checkbox_con_data_seccion(self):
        html = _generar()
        for seccion in ('trabajos', 'materiales', 'personal', 'riesgos',
                        'normativa', 'documentos', 'cierre'):
            self.assertIn(f'data-seccion="{seccion}"', html)

    def test_los_cinco_subapartados_de_prioridades_tienen_data_sub(self):
        html = _generar()
        for sub in ('estado_proyecto', 'que_hacer_ahora', 'tajos_bloqueados',
                    'tareas_manuales', 'sin_revisar'):
            self.assertIn(f'data-sub="{sub}"', html)


class TestLogicaSelectorJS(unittest.TestCase):

    def test_incluye_las_funciones_clave(self):
        html = _generar()
        for funcion in ('function abrirSelectorInforme',
                        'function toggleGrupoPrioridades',
                        'function marcarTodoInforme',
                        'function generarVistaPreviaInforme',
                        'function guardarSeleccionInforme',
                        'function cargarSeleccionInforme'):
            self.assertIn(funcion, html)

    def test_la_clave_de_localstorage_incluye_el_nombre_de_la_obra(self):
        html = _generar(obra='2026 OBRA PRUEBA')
        self.assertIn("const OBRA_NOMBRE = \"2026 OBRA PRUEBA\"", html)
        self.assertIn("'informe_obra_sel::' + OBRA_NOMBRE", html)

    def test_la_vista_previa_abre_una_pestana_nueva_y_no_reescribe_la_actual(self):
        html = _generar()
        self.assertIn("window.open('', '_blank')", html)
        self.assertIn('ventana.document.write(documento)', html)

    def test_el_documento_generado_fuerza_abrir_los_details_y_ofrece_imprimir(self):
        html = _generar()
        self.assertIn("document.querySelectorAll('details').forEach(d => d.open = true)", html)
        self.assertIn('window.print()', html)

    def test_las_casillas_quedan_inertes_en_el_documento_generado(self):
        """Evita que un clic en la vista previa dispare marcar-tarea-hecha
        contra un servidor que no esta corriendo ahi."""
        html = _generar()
        self.assertIn('input[type=checkbox]{pointer-events:none;}', html)

    def test_avisa_si_el_navegador_bloquea_la_ventana_emergente(self):
        """Bug real detectado al probar en navegador: si window.open()
        devuelve null (ventana emergente bloqueada), el codigo original
        revienta con un TypeError sin decirle nada a Bixente. Debe avisar
        y salir, nunca fallar en silencio."""
        html = _generar()
        self.assertIn('if (!ventana) {', html)
        self.assertIn('El navegador ha bloqueado la ventana emergente', html)


if __name__ == '__main__':
    unittest.main()
