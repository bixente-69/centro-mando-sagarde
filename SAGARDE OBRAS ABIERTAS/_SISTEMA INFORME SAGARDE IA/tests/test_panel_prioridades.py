# -*- coding: utf-8 -*-
"""El panel tiene que ensenar lo que el motor calcula.

Un dato que se calcula y no se pinta es lo mismo que no calcularlo. Estas
pruebas son la red de eso: cada cosa nueva del motor tiene que llegar a la
pantalla.
"""
import os
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
        self.assertEqual(panel_obra._tabla_tareas_manuales([], []), '')

        html = panel_obra.bloque_prioridades(
            _prioridades(), tareas_manual=[], documentos=[])
        self.assertNotIn('Tareas manuales', html)

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

        self.assertLess(html.index('Estado de la obra'),
                        html.index('Tareas manuales'))
        self.assertLess(html.index('Tareas manuales'),
                        html.index('Preguntas pendientes antes de decidir'))

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

    def test_escapa_el_contenido_de_la_ficha(self):
        html = panel_obra._tabla_tareas_manuales([{
            'Tarea': '<script>alert(1)</script>',
            'Estado': 'Pendiente',
        }], [])

        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)


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
        self.assertIn('5. Sin revisar nunca', html)
        self.assertIn('Tubeado interior', html)


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
        self.assertIn('92 celdas en la hoja', html)


if __name__ == '__main__':
    unittest.main()
