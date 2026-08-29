# -*- coding: utf-8 -*-
"""El panel tiene que ensenar lo que el motor calcula.

Un dato que se calcula y no se pinta es lo mismo que no calcularlo. Estas
pruebas son la red de eso: cada cosa nueva del motor tiene que llegar a la
pantalla.
"""
import os
import re
import sys
import tempfile
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import panel_obra


def _prioridades(**extra):
    """Salida minima del motor, con la forma que produce priorizar_ficha."""
    base = {
        'sin_base': False, 'revision': '28/07/2026', 'version': '4.3',
        'catalogo_version': '1.3', 'resumen': {}, 'items': [],
        'inventario': [], 'dudas_pendientes': [], 'preguntas_orden': [],
        'prevision': [], 'avisos': [],
    }
    base.update(extra)
    return base


class TestObraSinBase(unittest.TestCase):

    def test_lo_dice_en_pantalla_y_no_inventa_cifras(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            sin_base=True,
            avisos=['Esta obra no tiene base de datos todavía.']))
        self.assertIn('no tiene base de datos', html)
        self.assertNotIn('Bloques viables', html)
        self.assertNotIn('Inventario completo', html)

    def test_una_salida_vacia_no_revienta(self):
        self.assertIsInstance(panel_obra.bloque_prioridades({}), str)
        self.assertIsInstance(panel_obra.bloque_prioridades(None), str)


class TestTareasManuales(unittest.TestCase):

    TAREAS = [
        {'Tarea': 'Revisar cuadro', 'Origen': 'Parte de obra',
         'Fecha': '22/08/2026', 'Archivo': 'parte-22-08.pdf',
         'Estado': 'Pendiente'},
        {'Tarea': 'Cerrar incidencia', 'Origen': 'Correo',
         'Fecha': '19/08/2026', 'Archivo': 'correo-19-08.msg',
         'Estado': 'hEcHo'},
        {'Tarea': 'Pedir material', 'Origen': 'Encargado',
         'Fecha': '20/08/2026', 'Archivo': 'pedido-20-08.pdf',
         'Estado': 'Pendiente'},
    ]

    def test_pendientes_ordenadas_por_fecha_y_archivo_enlazado(self):
        html = panel_obra._tabla_tareas_manuales(self.TAREAS, [{
            'nombre': 'PEDIDO-20-08.PDF',
            'href': '../DOCUMENTOS/pedido-20-08.pdf',
        }])

        self.assertLess(html.index('Pedir material'),
                        html.index('Revisar cuadro'))
        self.assertLess(html.index('Revisar cuadro'),
                        html.index('Cerrar incidencia'))
        self.assertIn(
            '<a href="../DOCUMENTOS/pedido-20-08.pdf">pedido-20-08.pdf</a>',
            html)

    def test_hecha_va_en_bloque_separado_gris_y_tachado_al_final(self):
        html = panel_obra._tabla_tareas_manuales(self.TAREAS, [])

        inicio_hechas = html.index('tareas-hechas')
        self.assertLess(html.index('Revisar cuadro'), inicio_hechas)
        self.assertLess(inicio_hechas, html.index('Cerrar incidencia'))
        self.assertIn('color:var(--muted)', html[inicio_hechas:])
        self.assertIn('text-decoration:line-through', html[inicio_hechas:])

    def test_lista_vacia_no_anade_tarjeta(self):
        tabla = panel_obra._tabla_tareas_manuales([], [])
        self.assertEqual(tabla, '')
        self.assertNotIn('<script>', tabla)

        html = panel_obra.bloque_prioridades(
            _prioridades(), tareas_manual=[], documentos=[])
        # La tarjeta del centro de mando sigue apareciendo (igual que el
        # resto de tarjetas, muestra 0 en vez de desaparecer), pero su
        # enlace tiene que apuntar a una seccion real: sin lista de tareas
        # no se deja un enlace muerto a un id que no existe.
        self.assertIn("id='sec-tareas'", html)
        self.assertIn(
            'No hay tareas manuales declaradas en la ficha.', html)
        self.assertNotIn('marcar-tarea-hecha', html)

    def test_archivo_sin_coincidencia_se_muestra_sin_enlace(self):
        html = panel_obra._tabla_tareas_manuales([{
            'Tarea': 'Comprobar acta', 'Origen': 'Correo',
            'Fecha': '23/08/2026', 'Archivo': 'acta-inexistente.pdf',
            'Estado': 'Pendiente',
        }], [{'nombre': 'otro.pdf', 'href': '../otro.pdf'}])

        self.assertIn('acta-inexistente.pdf', html)
        self.assertNotIn('<a ', html)

    def test_tarjeta_esta_entre_estado_de_obra_y_dudas(self):
        html = panel_obra.bloque_prioridades(
            _prioridades(
                estado_obra='En ejecución',
                dudas_pendientes=[{
                    'codigo': 'ALCANCE', 'pregunta': '¿Qué alcance tiene?',
                    'n_ubicaciones': 0, 'ubicaciones': [],
                }]),
            tareas_manual=self.TAREAS, documentos=[])

        # 'Tareas manuales' ya no es un ancla univoca: el centro de mando
        # tambien la nombra, antes de 'Estado de la obra'. Se comprueba el
        # orden real de las secciones por su id, no por texto ambiguo.
        self.assertLess(html.index('Estado de la obra'),
                        html.index("id='sec-tareas'"))
        self.assertLess(html.index("id='sec-tareas'"),
                        html.index("id='sec-dudas'"))

    def test_generar_panel_pasa_tareas_y_documentos(self):
        ficha = {
            '_disponible': True, 'datos': {}, 'personal': [], 'hitos': [],
            'riesgos': [], 'plan': [], 'tareas': self.TAREAS,
        }
        documentos = [{
            'nombre': 'pedido-20-08.pdf',
            'href': '../DOCUMENTOS/pedido-20-08.pdf',
            'categoria': 'PDF', 'subcarpeta': 'DOCUMENTOS', 'kb': 10,
        }]
        with tempfile.TemporaryDirectory() as carpeta:
            salida = os.path.join(carpeta, 'panel.html')
            panel_obra.generar_panel(
                obra='Obra de prueba', subtitulo='', historial=[],
                materiales={}, ficha=ficha, documentos=documentos,
                prioridades=_prioridades(), output_path=salida)
            with open(salida, encoding='utf-8') as f:
                html = f.read()

        self.assertIn('Tareas manuales', html)
        self.assertIn(
            '<a href="../DOCUMENTOS/pedido-20-08.pdf">pedido-20-08.pdf</a>',
            html)
        self.assertIn("data-obra='Obra de prueba'", html)

    def test_escapa_el_contenido_de_la_ficha(self):
        html = panel_obra._tabla_tareas_manuales([{
            'Tarea': '<script>alert(1)</script>',
            'Estado': 'Pendiente',
        }], [])

        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_casilla_pendiente_lleva_los_datos_exactos_escapados(self):
        html = panel_obra._tabla_tareas_manuales([{
            'Tarea': 'Revisar "A&B" <cuadro>',
            'Origen': "Correo de O'Reilly",
            'Fecha': '24/08/2026',
            'Archivo': 'nota "final" & plano.txt',
            'Estado': 'Pendiente',
        }], [], obra='2026 OBRA "PRUEBA" & <NORTE>')

        self.assertIn("class='marcar-tarea-hecha'", html)
        self.assertIn(
            "data-obra='2026 OBRA &quot;PRUEBA&quot; &amp; &lt;NORTE&gt;'",
            html)
        self.assertIn(
            "data-tarea='Revisar &quot;A&amp;B&quot; &lt;cuadro&gt;'",
            html)
        self.assertIn("data-origen='Correo de O&#x27;Reilly'", html)
        self.assertIn("data-fecha='24/08/2026'", html)
        self.assertIn(
            "data-archivo='nota &quot;final&quot; &amp; plano.txt'", html)

    def test_script_local_aparece_si_hay_alguna_pendiente(self):
        html = panel_obra._tabla_tareas_manuales(
            [self.TAREAS[0]], [], obra='2026 OBRA PRUEBA')

        self.assertIn('<script>', html)
        self.assertIn("fetch('/api/marcar_hecho'", html)
        self.assertIn('AbortController', html)
        self.assertIn('Marcada como hecha. Recuerda ejecutar '
                      'Actualizar_Sagarde.bat para publicar este cambio.', html)
        self.assertIn('No se ha guardado ningún cambio.', html)
        self.assertIn('No se encontró esa tarea en el Excel', html)

    def test_la_casilla_se_reactiva_tras_un_cambio_con_exito(self):
        """Bug real detectado en revisión manual: la casilla se deshabilita
        al iniciar la petición y solo se reactivaba en las ramas de fallo
        (restaurar()); si la petición tenía éxito quedaba deshabilitada para
        siempre y un segundo clic no volvía a disparar el evento 'change'."""
        html = panel_obra._tabla_tareas_manuales(
            [self.TAREAS[0]], [], obra='2026 OBRA PRUEBA')

        self.assertEqual(html.count('casilla.disabled = false;'), 2)

    def test_fila_hecha_tiene_casilla_marcada_para_poder_desmarcar(self):
        html = panel_obra._tabla_tareas_manuales(
            [self.TAREAS[1]], [], obra='2026 OBRA PRUEBA')

        self.assertIn("class='marcar-tarea-hecha' checked", html)
        self.assertIn('data-tarea=', html)
        self.assertIn('<script>', html)
        self.assertIn(
            'Marcada de nuevo como pendiente. Recuerda ejecutar '
            'Actualizar_Sagarde.bat para publicar este cambio.', html)

    def test_fila_sin_estado_reconocido_no_tiene_casilla(self):
        html = panel_obra._tabla_tareas_manuales([{
            'Tarea': 'Tarea con estado raro',
            'Origen': 'Origen', 'Fecha': '24/08/2026', 'Archivo': '',
            'Estado': 'En duda',
        }], [], obra='2026 OBRA PRUEBA')

        self.assertNotIn("class='marcar-tarea-hecha'", html)
        self.assertNotIn('<script>', html)

    def test_tareas_pendientes_es_la_misma_lista_que_pinta_la_tarjeta(self):
        pendientes = panel_obra._tareas_pendientes(self.TAREAS)
        self.assertEqual(len(pendientes), 2)  # dos 'Pendiente' en self.TAREAS
        nombres = [t['Tarea'] for t in pendientes]
        self.assertEqual(nombres, ['Pedir material', 'Revisar cuadro'])

    def test_la_tarjeta_es_un_details_plegable(self):
        html = panel_obra._tabla_tareas_manuales(self.TAREAS, [])
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-tareas'", html)
        self.assertIn('<summary>Tareas manuales', html)


class TestSinRevisar(unittest.TestCase):

    def test_aparece_con_su_kpi(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            resumen={'sin_revisar': 3, 'unidades_sin_revisar': 190}))
        self.assertIn('Sin revisar nunca', html)
        self.assertIn('190', html)

    def test_tiene_seccion_propia_en_el_inventario(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            inventario=[{
                'seccion': 'SIN_REVISAR', 'trabajo': 'Tubeado interior',
                'propiedad': 'propio', 'orden_ejecucion': 130,
                'fase_nombre': 'Instalación interior', 'n_ubicaciones': 5,
                'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
                'subtajos': [],
            }]))
        self.assertIn('Sin revisar nunca', html)
        self.assertIn('Tubeado interior', html)

    def test_la_seccion_es_un_details_plegable_sin_numero(self):
        html = panel_obra.bloque_prioridades(_prioridades(inventario=[{
            'seccion': 'SIN_REVISAR', 'trabajo': 'Tubeado interior',
            'propiedad': 'propio', 'orden_ejecucion': 130,
            'fase_nombre': 'Instalación interior', 'n_ubicaciones': 5,
            'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
            'subtajos': [],
        }]))
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-inv-sin_revisar'",
            html)
        self.assertNotIn('5. Sin revisar nunca', html)


class TestPreguntasDelCatalogo(unittest.TestCase):

    def test_un_tajo_fuera_del_catalogo_sale_con_sus_candidatos(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            preguntas_orden=[{
                'codigo': 'TAJO_FUERA_DEL_CATALOGO',
                'tarea_id': 'placas_tps_cuadro', 'nombre': 'Placas tapas',
                'parecidos': ['placas_tapas'],
            }]))
        self.assertIn('No está en el catálogo', html)
        self.assertIn('placas_tps_cuadro', html)
        self.assertIn('placas_tapas', html)

    def test_la_tarjeta_es_un_details_plegable(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            preguntas_orden=[{
                'codigo': 'TAJO_FUERA_DEL_CATALOGO',
                'tarea_id': 'placas_tps_cuadro', 'nombre': 'Placas tapas',
                'parecidos': ['placas_tapas'],
            }]))
        self.assertIn(
            "<details class='card seccion-plegable' "
            "id='sec-preguntas-catalogo'", html)

    def test_un_duplicado_en_la_base_sale_nombrado(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            preguntas_orden=[{
                'codigo': 'TAJO_DUPLICADO_EN_LA_BASE',
                'tarea_id': 'placas_tapas', 'nombre': 'Placas y tapas',
                'parecidos': ['placas_tapas', 'placas_tps_cuadro'],
            }]))
        self.assertIn('Dos filas para el mismo tajo', html)

    def test_una_dependencia_ausente_sale_nombrada(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            preguntas_orden=[{
                'codigo': 'DEPENDENCIA_AUSENTE_EN_LA_OBRA',
                'tarea_id': 'cuadro_mecanizado', 'nombre': 'Cuadro mecanizado',
                'parecidos': ['cuadros_presentados'],
            }]))
        self.assertIn('Depende de un tajo que la obra no tiene', html)
        self.assertIn('cuadros_presentados', html)

    def test_sin_preguntas_no_se_pinta_la_tabla(self):
        html = panel_obra.bloque_prioridades(_prioridades())
        self.assertNotIn('Preguntas sobre el catálogo de tajos', html)


class TestPrevision(unittest.TestCase):

    def test_se_pinta_con_lo_que_libera(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            prevision=[{
                'tarea_id': 'pintura_segunda',
                'trabajo': 'Pintura — segunda mano',
                'estado_actual': 'Pendiente', 'propiedad': 'externo',
                'desbloquea': 184,
                'tajos_afectados': ['Casquillos y bombillas'],
            }]))
        self.assertIn('Qué se desbloquea al terminar cada cosa', html)
        self.assertIn('184', html)
        self.assertIn('Otro gremio', html)

    def test_distingue_lo_nuestro_de_lo_de_otros(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            prevision=[{
                'tarea_id': 'cuadro_mecanizado', 'trabajo': 'Cuadro mecanizado',
                'estado_actual': 'Pendiente', 'propiedad': 'propio',
                'desbloquea': 138, 'tajos_afectados': ['Placas y tapas'],
            }]))
        self.assertIn('Nuestro', html)

    def test_sin_prevision_no_se_pinta_la_tabla(self):
        html = panel_obra.bloque_prioridades(_prioridades())
        self.assertNotIn('Qué se desbloquea', html)

    def test_la_tarjeta_es_un_details_plegable(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            prevision=[{
                'tarea_id': 'pintura_segunda', 'trabajo': 'Pintura',
                'estado_actual': 'Pendiente', 'propiedad': 'externo',
                'desbloquea': 5, 'tajos_afectados': [],
            }]))
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-prevision'", html)


class TestAvisos(unittest.TestCase):

    def test_un_aviso_de_fusion_de_ubicaciones_sale_marcado(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            avisos=['5 ubicaciones de la base se fusionan al priorizar '
                    'porque producen la misma clave.']))
        self.assertIn('se fusionan al priorizar', html)
        self.assertIn('banner bad', html)

    def test_los_avisos_de_siempre_no_ensucian_la_pantalla(self):
        html = panel_obra.bloque_prioridades(_prioridades(
            avisos=['El inventario incluye todos los tajos de la base.',
                    'El orden sigue la secuencia lógica definida.']))
        self.assertNotIn('El inventario incluye', html)


class TestDudasPendientes(unittest.TestCase):

    def test_con_dudas_es_un_details_con_borde_de_aviso(self):
        html = panel_obra.bloque_prioridades(_prioridades(dudas_pendientes=[{
            'codigo': 'ALCANCE', 'pregunta': '¿Qué alcance tiene?',
            'n_ubicaciones': 0, 'ubicaciones': [],
        }]))
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-dudas' "
            "style='border-left:4px solid var(--warn);'>", html)

    def test_sin_dudas_tambien_es_un_details_plegable_pero_sin_aviso(self):
        html = panel_obra.bloque_prioridades(_prioridades(dudas_pendientes=[]))
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-dudas'>", html)
        self.assertIn('No hay preguntas pendientes en esta actualización', html)


class TestConteoPorAmbito(unittest.TestCase):

    def test_un_tajo_de_edificio_ensena_unidades_y_celdas(self):
        """Una unidad real, 92 celdas en la hoja: las dos cifras importan y
        significan cosas distintas."""
        html = panel_obra.bloque_prioridades(_prioridades(items=[{
            'orden': 1, 'situacion': 'LISTO', 'trabajo': 'Cuarto técnico',
            'n_unidades': 1, 'n_celdas': 92, 'n_ubicaciones': 92,
            'ubicaciones': [], 'estado_actual': 'Pendiente',
            'motivo': 'Viable.', 'fase_nombre': 'Cierre técnico',
            'orden_ejecucion': 235, 'ambito_nombre': 'Edificio general',
        }]))
        self.assertIn('Cuarto técnico', html)
        self.assertIn('1 ud.', html)
        self.assertIn('Celdas en hoja: 92', html)

    def test_el_badge_de_que_hacer_ahora_cuenta_listo_y_verificar(self):
        """El badge de la tarjeta 'Qué hacer ahora' tiene que coincidir con
        las filas reales de su propia tabla, que muestra LISTO y VERIFICAR
        (el filtro por defecto es 'LISTO + VERIFICAR'). Si el badge solo
        contara 'listos' del resumen, divergiría en cuanto hubiera algún
        VERIFICAR — bug real detectado en revisión, invisible hasta hoy
        porque verificar siempre había sido 0 en obras reales."""
        html = panel_obra.bloque_prioridades(_prioridades(
            resumen={'listos': 1},
            items=[
                {'orden': 1, 'situacion': 'LISTO', 'trabajo': 'A',
                 'n_unidades': 1, 'n_celdas': 1, 'n_ubicaciones': 1,
                 'ubicaciones': [], 'estado_actual': 'Pendiente',
                 'motivo': 'x', 'fase_nombre': 'f', 'orden_ejecucion': 1,
                 'ambito_nombre': 'Viviendas'},
                {'orden': 2, 'situacion': 'VERIFICAR', 'trabajo': 'B',
                 'n_unidades': 1, 'n_celdas': 1, 'n_ubicaciones': 1,
                 'ubicaciones': [], 'estado_actual': 'Pendiente',
                 'motivo': 'x', 'fase_nombre': 'f', 'orden_ejecucion': 2,
                 'ambito_nombre': 'Viviendas'},
            ]))

        timeline = html[html.index('id="timeline-prio"'):]
        n_tarjetas = timeline.count('<article class="timeline-item"')
        self.assertEqual(n_tarjetas, 2)

        # La tarjeta heroe del centro de mando tiene que contar LISTO y
        # VERIFICAR contando los tajos reales, no fiarse a ciegas de
        # resumen_prio (aqui deliberadamente incompleto: solo declara
        # 'listos', no 'verificar').
        hero = html[html.index("bento-hero"):html.index("bento-hero") + 900]
        self.assertIn("<strong>1</strong><span>tajos listos</span>", hero)
        self.assertIn(
            "<span>Listos</span><strong>1</strong>", hero)
        self.assertIn(
            "<span>Verificar</span><strong>1</strong>", hero)


class TestTimelineEjecucion(unittest.TestCase):
    """El timeline de tarjetas de 'Qué hacer ahora' calcula sus propias
    cifras sobre las ubicaciones reales, sin parsear el estado agregado."""

    def test_medidos_solo_cuenta_x_y_m_el_resto_es_pendiente(self):
        """Un '/' (iniciado) o el texto 'Pendiente' no deben colarse como
        medidos: solo X y M cuentan. Si alguien reintroduce un parseo del
        string agregado en vez de contar ubicaciones, esta prueba lo pilla."""
        html = panel_obra.bloque_prioridades(_prioridades(items=[{
            'orden': 1, 'situacion': 'LISTO', 'trabajo': 'Tajo mixto',
            'n_unidades': 1, 'n_celdas': 5, 'n_ubicaciones': 5,
            'motivo': 'x', 'fase_nombre': 'f', 'orden_ejecucion': 1,
            'ambito_nombre': 'Viviendas',
            'ubicaciones': [
                {'edificio': 'OBRA', 'planta': '1', 'unidades': ['A'], 'estado_actual': 'X'},
                {'edificio': 'OBRA', 'planta': '1', 'unidades': ['B'], 'estado_actual': 'M'},
                {'edificio': 'OBRA', 'planta': '1', 'unidades': ['C'], 'estado_actual': '/'},
                {'edificio': 'OBRA', 'planta': '1', 'unidades': ['D'], 'estado_actual': 'Pendiente'},
                {'edificio': 'OBRA', 'planta': '1', 'unidades': ['E'], 'estado_actual': '?'},
            ],
        }]))
        self.assertIn('<strong>2</strong><span>Medidos</span>', html)
        self.assertIn('<strong>3</strong><span>Pendientes</span>', html)
        self.assertIn('<strong>5</strong><span>Total</span>', html)
        self.assertIn('40% · 2 medidos · 3 pendientes', html)

    def test_mas_de_seis_plantas_no_pierde_ninguna_solo_las_pliega(self):
        """Con muchas plantas, la tarjeta no lista todo de golpe, pero
        ninguna ubicación desaparece: las que no caben en la vista directa
        quedan dentro de un <details> anidado, no descartadas en silencio."""
        ubicaciones = [
            {'edificio': 'OBRA', 'planta': str(planta), 'unidades': ['A'],
             'estado_actual': 'M'}
            for planta in range(1, 9)
        ]
        html = panel_obra.bloque_prioridades(_prioridades(items=[{
            'orden': 1, 'situacion': 'LISTO', 'trabajo': 'Tajo grande',
            'n_unidades': 1, 'n_celdas': 8, 'n_ubicaciones': 8,
            'motivo': 'x', 'fase_nombre': 'f', 'orden_ejecucion': 1,
            'ambito_nombre': 'Edificio general',
            'ubicaciones': ubicaciones,
        }]))
        self.assertIn('+2 ubicaciones más en 2 plantas', html)
        for planta in range(1, 9):
            self.assertIn(f'planta {planta}<', html)


class TestEnvolverPlegable(unittest.TestCase):

    def test_produce_details_con_id_titulo_y_contenido(self):
        html = panel_obra._envolver_plegable(
            'sec-prueba', 'Título de prueba', '<p>contenido</p>')
        self.assertIn(
            "<details class='card seccion-plegable' id='sec-prueba'>", html)
        self.assertIn('<summary>Título de prueba</summary>', html)
        self.assertIn(
            "<div class='seccion-contenido'><p>contenido</p></div>", html)
        self.assertTrue(html.rstrip().endswith('</details>'))

    def test_aplica_color_de_borde_cuando_se_indica(self):
        html = panel_obra._envolver_plegable(
            'sec-x', 'Título', 'contenido', color_borde='var(--warn)')
        self.assertIn("style='border-left:4px solid var(--warn);'", html)

    def test_sin_color_no_anade_atributo_style(self):
        html = panel_obra._envolver_plegable('sec-x', 'Título', 'contenido')
        self.assertNotIn('style=', html)

    def test_escapa_el_identificador_del_ancla(self):
        html = panel_obra._envolver_plegable('sec "x"', 'Título', 'contenido')
        self.assertIn('id=\'sec &quot;x&quot;\'', html)


class TestIndicePrioridades(unittest.TestCase):

    def test_agrupa_en_actuar_y_consulta_respetando_el_orden(self):
        html = panel_obra._indice_prioridades([
            {'id': 'sec-a', 'etiqueta': 'Primero', 'grupo': 'actuar'},
            {'id': 'sec-b', 'etiqueta': 'Segundo', 'grupo': 'actuar'},
            {'id': 'sec-c', 'etiqueta': 'Tercero', 'grupo': 'consulta'},
        ])
        self.assertLess(html.index('Para actuar hoy'), html.index('Primero'))
        self.assertLess(html.index('Primero'), html.index('Segundo'))
        self.assertLess(
            html.index('Segundo'), html.index('Consulta y referencia'))
        self.assertLess(
            html.index('Consulta y referencia'), html.index('Tercero'))

    def test_enlace_apunta_al_id_de_la_seccion_y_permite_abrirla(self):
        html = panel_obra._indice_prioridades([{
            'id': 'sec-bloqueados', 'etiqueta': 'Bloqueados', 'grupo': 'actuar',
        }])
        self.assertIn("href='#sec-bloqueados'", html)
        self.assertIn("data-abre='sec-bloqueados'", html)
        self.assertIn('<script>', html)

    def test_lista_vacia_no_pinta_nada(self):
        self.assertEqual(panel_obra._indice_prioridades([]), '')
        self.assertEqual(panel_obra._indice_prioridades(None), '')

    def test_grupo_sin_secciones_no_deja_cabecera_suelta(self):
        html = panel_obra._indice_prioridades(
            [{'id': 'sec-a', 'etiqueta': 'Solo esta', 'grupo': 'actuar'}])
        self.assertNotIn('Consulta y referencia', html)

    def test_cada_grupo_es_un_desplegable_exclusivo(self):
        """Los dos botones comparten name='indice-nav-grupo': abrir uno
        pliega el otro solo, sin JavaScript (soporte nativo del navegador)."""
        html = panel_obra._indice_prioridades([
            {'id': 'sec-a', 'etiqueta': 'Uno', 'grupo': 'actuar'},
            {'id': 'sec-b', 'etiqueta': 'Dos', 'grupo': 'consulta'},
        ])
        self.assertEqual(
            html.count("<details class='indice-nav-grupo' "
                       "name='indice-nav-grupo'>"), 2)


def _contar_data_abre(html, id_seccion):
    """Cuenta enlaces data-abre a un id, sin importar la comilla usada:
    las tarjetas bento usan comillas dobles y los chips comillas simples."""
    return len(re.findall(
        r"""data-abre=["']""" + re.escape(id_seccion) + r"""["']""", html))


class TestCentroDeMandoConectado(unittest.TestCase):
    """El centro de mando (bento) sustituyo a la fila de KPIs + el indice
    desplegable. Estas pruebas protegen la misma familia de fallo de
    siempre: un dato o un enlace que el motor calcula pero que la pagina no
    conecta con la seccion real a la que dice apuntar."""

    def _html_obra_completa(self):
        return panel_obra.bloque_prioridades(_prioridades(
            resumen={'listos': 2, 'bloqueados': 1, 'sin_revisar': 1},
            items=[
                {'orden': 1, 'situacion': 'LISTO', 'trabajo': 'A',
                 'n_unidades': 1, 'n_celdas': 1, 'n_ubicaciones': 1,
                 'ubicaciones': [], 'estado_actual': 'Pendiente',
                 'motivo': 'x', 'fase_nombre': 'f', 'orden_ejecucion': 1,
                 'ambito_nombre': 'Viviendas'},
            ],
            inventario=[
                {'seccion': 'BLOQUEADO', 'trabajo': 'B', 'propiedad': 'propio',
                 'orden_ejecucion': 2, 'fase_nombre': 'f', 'n_ubicaciones': 3,
                 'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
                 'subtajos': []},
                {'seccion': 'SIN_REVISAR', 'trabajo': 'C', 'propiedad': 'propio',
                 'orden_ejecucion': 3, 'fase_nombre': 'f', 'n_ubicaciones': 4,
                 'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
                 'subtajos': []},
            ],
        ), tareas_manual=[{
            'Tarea': 'Revisar cuadro', 'Origen': 'Parte de obra',
            'Fecha': '22/08/2026', 'Archivo': '', 'Estado': 'Pendiente',
        }], documentos=[])

    def test_el_centro_de_mando_aparece_una_sola_vez(self):
        html = self._html_obra_completa()
        self.assertEqual(html.count('class="bento-command"'), 1)

    def test_las_secciones_clasicas_estan_ocultas_por_defecto(self):
        """Bixente: 'si ya tengo arriba enlace, no necesito debajo' — un
        enlace bento + la seccion real duplicando la misma cabecera visible
        alargaba la pagina. Se comprueba que la regla CSS que las oculta
        por defecto sigue cubriendo las once secciones reales, para que
        nadie la borre sin darse cuenta y resucite la duplicidad."""
        estilo = panel_obra.ESTILOS
        for id_seccion in (
            'sec-tareas', 'sec-dudas', 'sec-ejecucion', 'sec-inv-bloqueado',
            'sec-inv-sin_revisar', 'sec-inv-viable', 'sec-inv-otros_gremios',
            'sec-inv-dudas', 'sec-inv-terminado', 'sec-preguntas-catalogo',
            'sec-prevision',
        ):
            self.assertIn(
                f'#{id_seccion}', estilo,
                f'{id_seccion} no esta en la regla que oculta por defecto')

    def test_el_centro_de_mando_va_antes_que_todas_las_secciones_plegables(self):
        html = self._html_obra_completa()
        posicion_bento = html.index('class="bento-command"')
        for id_seccion in ('sec-tareas', 'sec-dudas', 'sec-ejecucion',
                            'sec-inv-bloqueado', 'sec-inv-sin_revisar'):
            self.assertLess(
                posicion_bento, html.index(f"id='{id_seccion}'"),
                f"el centro de mando deberia ir antes que {id_seccion}")

    def test_bloqueados_y_sin_revisar_son_tarjetas_no_chips(self):
        """Tienen su propia tabla completa (no solo un contador), asi que
        van en la rejilla de tarjetas grandes, no en la fila de chips de
        solo consulta."""
        html = self._html_obra_completa()
        inicio_grid = html.index('class="bento-grid"')
        inicio_referencia = html.index('class="bento-reference"')
        pos_bloqueados = html.index("sec-inv-bloqueado", inicio_grid)
        pos_sin_revisar = html.index("sec-inv-sin_revisar", inicio_grid)
        self.assertTrue(inicio_grid < pos_bloqueados < inicio_referencia)
        self.assertTrue(inicio_grid < pos_sin_revisar < inicio_referencia)

    def test_el_numero_de_la_tarjeta_coincide_con_las_filas_reales_de_la_seccion(self):
        html = self._html_obra_completa()
        # "Tajos bloqueados" tiene 1 grupo en el inventario de esta obra de
        # prueba (seccion BLOQUEADO): la tarjeta debe decir "1", no otra cosa.
        tarjeta_bloqueados = html[
            html.index("sec-inv-bloqueado"):
            html.index("sec-inv-bloqueado") + 300]
        self.assertIn('<div class="bento-number">1</div>', tarjeta_bloqueados)
        # Y la seccion real debe traer exactamente 1 fila de tajo (mas la
        # cabecera de la tabla, que no cuenta).
        seccion_bloqueados = html[
            html.index("id='sec-inv-bloqueado'"):
            html.index("id='sec-inv-sin_revisar'")]
        self.assertEqual(seccion_bloqueados.count('<tr><td><b>'), 1)

    def test_una_seccion_vacia_no_aparece_como_tarjeta_ni_chip(self):
        # Sin preguntas_orden ni prevision: _tabla_preguntas_orden y
        # _tabla_prevision devuelven '' y no deben dejar tarjeta ni chip
        # (la regla CSS que las oculta por id sigue mencionandolas, eso es
        # aparte y ya lo cubre otra prueba).
        html = self._html_obra_completa()
        self.assertNotIn("id='sec-preguntas-catalogo'", html)
        self.assertNotIn("data-abre='sec-preguntas-catalogo'", html)
        self.assertNotIn("id='sec-prevision'", html)
        self.assertNotIn("data-abre='sec-prevision'", html)

    def test_las_seis_secciones_del_inventario_salen_conectadas_una_sola_vez(self):
        """Guarda contra la familia de fallo de este proyecto: un codigo que
        el bucle de mas arriba construye en `inventario_por_codigo` pero que
        el montaje final (hardcodeado por nombre) no coloca en ninguna
        tarjeta ni chip se quedaria construido y nunca mostrado, en
        silencio. Esta prueba pasa hoy porque los seis codigos actuales
        estan bien conectados; su valor es fallar el dia que se añada un
        septimo codigo a _SECCIONES_INVENTARIO sin conectarlo."""
        html = self._html_obra_completa()
        for codigo, _, _ in panel_obra._SECCIONES_INVENTARIO:
            self.assertEqual(
                _contar_data_abre(html, f'sec-inv-{codigo.lower()}'), 1,
                f'{codigo} no tiene exactamente un enlace conectado')

    def test_pinchar_un_enlace_revela_abre_y_hace_scroll(self):
        """El script no solo abre la seccion destino: primero la revela
        (estaba oculta por CSS) y hace scroll manual, porque el salto de
        ancla nativo del navegador no funciona sobre un elemento oculto."""
        html = self._html_obra_completa()
        self.assertIn("destino.style.display = 'block'", html)
        self.assertIn('destino.open = true', html)
        self.assertIn('destino.scrollIntoView(', html)

    def test_cerrar_una_seccion_la_vuelve_a_ocultar(self):
        """Para que la pagina en reposo siga siendo 'solo bento': si el
        usuario explora una seccion y la cierra, no debe quedar un resto
        visible suelto."""
        html = self._html_obra_completa()
        self.assertIn("if (!el.open) { el.style.display = 'none'; }", html)


if __name__ == '__main__':
    unittest.main()


class TestBloquePrioridadesPartes(unittest.TestCase):
    """bloque_prioridades_partes() es la fuente unica: bloque_prioridades()
    y el informe de obra a la carta tienen que leer de aqui, nunca
    recalcular por su cuenta."""

    def test_devuelve_un_dict_con_las_claves_esperadas(self):
        partes = panel_obra.bloque_prioridades_partes(_prioridades())
        claves_esperadas = {
            'bento_command', 'estado_obra_html', 'avisos_prio',
            'script_indice', 'tareas_manual_html', 'dudas_html',
            'ejecucion_html', 'bloqueado_html', 'sin_revisar_html',
            'orden_html', 'prevision_html', 'viable_html',
            'otros_gremios_html', 'dudas_inventario_html', 'terminado_html',
        }
        self.assertEqual(set(partes.keys()), claves_esperadas)

    def test_sin_base_devuelve_string_no_dict(self):
        partes = panel_obra.bloque_prioridades_partes(
            _prioridades(sin_base=True, avisos=['sin base']))
        self.assertIsInstance(partes, str)
        self.assertIn('sin base', partes)

    def test_concatenar_las_partes_da_el_mismo_html_que_bloque_prioridades(self):
        """La prueba mas importante de esta tarea: bloque_prioridades()
        tiene que seguir devolviendo exactamente lo mismo que antes de
        dividir la funcion. Si un dia alguien cambia el orden en uno de
        los dos sitios sin cambiar el otro, esta prueba lo detecta."""
        prioridades = _prioridades(
            resumen={'listos': 1, 'bloqueados': 1, 'sin_revisar': 1},
            items=[{
                'orden': 1, 'situacion': 'LISTO', 'trabajo': 'A',
                'n_unidades': 1, 'n_celdas': 1, 'n_ubicaciones': 1,
                'ubicaciones': [], 'estado_actual': 'Pendiente',
                'motivo': 'x', 'fase_nombre': 'f', 'orden_ejecucion': 1,
                'ambito_nombre': 'Viviendas',
            }],
            inventario=[{
                'seccion': 'BLOQUEADO', 'trabajo': 'B', 'propiedad': 'propio',
                'orden_ejecucion': 2, 'fase_nombre': 'f', 'n_ubicaciones': 3,
                'ubicaciones': [], 'estado_actual': '—', 'motivo': 'x',
                'subtajos': [],
            }],
        )
        tareas_manual = [{
            'Tarea': 'Revisar cuadro', 'Origen': 'Parte de obra',
            'Fecha': '22/08/2026', 'Archivo': '', 'Estado': 'Pendiente',
        }]

        html_directo = panel_obra.bloque_prioridades(
            prioridades, tareas_manual=tareas_manual, documentos=[])
        partes = panel_obra.bloque_prioridades_partes(
            prioridades, tareas_manual=tareas_manual, documentos=[])
        html_reconstruido = (
            partes['bento_command'] + partes['estado_obra_html']
            + partes['avisos_prio'] + partes['script_indice']
            + partes['tareas_manual_html'] + partes['dudas_html']
            + partes['ejecucion_html'] + partes['bloqueado_html']
            + partes['sin_revisar_html'] + partes['orden_html']
            + partes['prevision_html'] + partes['viable_html']
            + partes['otros_gremios_html'] + partes['dudas_inventario_html']
            + partes['terminado_html']
        )
        self.assertEqual(html_directo, html_reconstruido)
