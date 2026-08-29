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

    def test_el_open_se_hornea_en_el_html_antes_de_escribir_el_documento(self):
        """Buena practica: <details open> ya en el HTML analizado la
        primera vez es mas fiable que fijar la propiedad open por JS
        sobre un nodo ya insertado."""
        html = _generar()
        self.assertIn(
            "contenido = contenido.replace(/<details(?![a-zA-Z-])/g, "
            "'<details open');", html)

    def test_las_secciones_clasicas_no_quedan_ocultas_por_el_css_del_panel(self):
        """La causa real de 'Que hacer ahora no esta desplegada, solo se
        ven las cabeceras': ESTILOS oculta #sec-ejecucion (y las demas
        secciones 'clasicas' de Prioridades) por defecto, porque en el
        panel en vivo solo se revelan al pinchar una tarjeta del centro
        de mando (destino.style.display='block'). Aqui no hay ningun
        click que las revele, asi que hacia falta forzar el override —
        confirmado en navegador de verdad: sin esto el <details> entero,
        incluido su propio <summary>, medía 0 de alto."""
        html = _generar()
        self.assertIn(
            "#sec-tareas,#sec-dudas,#sec-ejecucion,#sec-inv-bloqueado,"
            "#sec-inv-sin_revisar,\n#sec-inv-viable,#sec-inv-otros_gremios,"
            "#sec-inv-dudas,#sec-inv-terminado,\n#sec-preguntas-catalogo,"
            "#sec-prevision{display:block!important;}", html)

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

    def test_la_vista_previa_reutiliza_el_mismo_css_del_panel(self):
        """Bixente: la vista previa tiene que verse tal cual como al
        pinchar en cada pestana, no un diseno aparte. ESTILOS (el mismo
        CSS que ya pinta el panel en vivo) debe aparecer tambien dentro
        del documento que arma generarVistaPreviaInforme(), no una hoja
        de estilos nueva e independiente."""
        html = _generar()
        marcador = '--header:#0b1f3a'
        self.assertIn(marcador, panel_obra.ESTILOS)
        self.assertEqual(html.count(marcador), 2,
            'ESTILOS deberia aparecer una vez para la pagina en vivo y '
            'otra vez dentro del documento de la vista previa')
        self.assertNotIn('IBM Plex Sans', html)


class TestPaginacionImpresion(unittest.TestCase):
    """Bixente: al imprimir/guardar en PDF, las cabeceras tienen que salir
    bien, las paginas cuadrar en A4 y nada (tablas, tarjetas) partirse a
    la mitad. Cada regla de aqui responde a uno de esos sintomas
    concretos, no a una idea general de 'que quede bonito'."""

    def test_fuerza_a_imprimir_los_colores_y_fondos(self):
        """Sin esto Chrome imprime todo en blanco y negro por defecto:
        la cabecera naranja/marino desaparece del PDF aunque se vea bien
        en pantalla."""
        html = _generar()
        self.assertIn('print-color-adjust:exact!important', html)

    def test_la_cabecera_es_pequena_y_aparece_una_sola_vez_sin_fijar(self):
        """Bixente: la cabecera repetida y grande dejaba paginas con solo
        un cabecero y un par de lineas, y el hueco reservado arriba podia
        quedarse corto y tapar contenido. Ahora es pequena, aparece una
        sola vez al principio, en flujo normal (nunca position:fixed)."""
        html = _generar()
        self.assertIn('.informe-cabecera{', html)
        self.assertNotIn('position:fixed', html)
        self.assertNotIn('margin-top:34mm', html)
        self.assertEqual(html.count('class="informe-cabecera"'), 1)

    def test_no_fuerza_una_columna_ni_salto_de_pagina_por_seccion(self):
        """Bixente: prefiere un reajuste natural a una pagina casi vacia.
        No se fuerza el apilado en una columna de los paneles anchos
        (bento/kpi ya tienen su propio ajuste responsive) ni se obliga a
        cada seccion elegida a empezar en pagina nueva."""
        html = _generar()
        self.assertNotIn('.kpi-row,.chart-row,.bento-grid', html)
        self.assertNotIn('break-before:page', html)

    def test_las_tablas_repiten_cabecera_y_no_cortan_filas(self):
        html = _generar()
        self.assertIn('table.data thead{display:table-header-group;}', html)
        self.assertIn('table.data tr{break-inside:avoid;}', html)

    def test_solo_se_evita_partir_la_unidad_mas_pequena(self):
        """break-inside:avoid solo en tarjetas/filas sueltas, nunca en un
        bloque grande entero (una seccion de prioridades, un desplegable
        largo): eso es lo que dejaba huecos en blanco cuando el bloque no
        cabia entero en lo que quedaba de pagina."""
        html = _generar()
        self.assertIn('.card,.kpi,.bento-card{break-inside:avoid', html)
        # .bento-command SI aparece en ESTILOS con su propio estilo base
        # (eso es normal); lo que no debe volver es la regla de impresion
        # vieja que lo metia entero en el break-inside:avoid.
        self.assertNotIn('.bento-health,.bento-command{', html)
        self.assertNotIn('break-inside:avoid-page', html)
        self.assertIn(
            'details.seccion-plegable>summary{break-after:avoid;}', html)
        self.assertIn('.informe-titulo{break-after:avoid;}', html)

    def test_el_tamano_de_pagina_es_a4_con_margen_ajustado(self):
        html = _generar()
        self.assertIn('@page{size:A4;margin:12mm;}', html)


if __name__ == '__main__':
    unittest.main()
