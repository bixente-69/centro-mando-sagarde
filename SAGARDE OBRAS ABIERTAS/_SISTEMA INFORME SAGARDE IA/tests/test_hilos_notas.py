# -*- coding: utf-8 -*-
"""Pruebas del hilo conductor escrito a mano en las notas de tareas."""
import os
from pathlib import Path
import sys
import tempfile
import unittest


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import hilos_notas
import panel_obra


def _prioridades_vacias():
    return {
        'sin_base': False, 'revision': '29/09/2026', 'version': '4.3',
        'catalogo_version': '1.3', 'resumen': {}, 'items': [],
        'inventario': [], 'dudas_pendientes': [], 'preguntas_orden': [],
        'prevision': [], 'avisos': [],
    }


class TestParseHiloConductor(unittest.TestCase):

    def test_bloque_normal_conserva_orden_y_campos(self):
        hilo = hilos_notas.parse_hilo_conductor("""Cabecera libre
HILO CONDUCTOR
- [Egurrola] 2026-09-29 15:13 | Amets → Vicente | Primera pregunta
- [Sagarde] 2026-09-29 10:46 | Vicente → Amets | Segunda respuesta
- [Citado] 2026-09-24 | Amets → Iker | Antecedente citado
- [Hueco] Faltan 3 mensajes anteriores: no están en este buzón
FIN HILO
Pie libre
""")

        self.assertEqual(hilo['avisos'], [])
        self.assertEqual([m['texto'] for m in hilo['mensajes']], [
            'Primera pregunta', 'Segunda respuesta', 'Antecedente citado',
            'Faltan 3 mensajes anteriores: no están en este buzón',
        ])
        self.assertEqual(hilo['mensajes'][0], {
            'lado': 'Egurrola', 'fecha': '2026-09-29', 'hora': '15:13',
            'de_a': 'Amets → Vicente', 'texto': 'Primera pregunta',
        })
        self.assertEqual(hilo['mensajes'][2]['hora'], '')
        self.assertEqual(hilo['mensajes'][3], {
            'lado': 'Hueco', 'fecha': '', 'hora': '', 'de_a': '',
            'texto': 'Faltan 3 mensajes anteriores: no están en este buzón',
        })

    def test_sin_bloque_devuelve_none(self):
        self.assertIsNone(hilos_notas.parse_hilo_conductor(
            'Una nota normal\nsin el marcador reservado\n'))

    def test_bloque_vacio_es_senal_y_no_none(self):
        hilo = hilos_notas.parse_hilo_conductor(
            'Antes\nHILO CONDUCTOR\n\nFIN HILO\nDespués')

        self.assertIsNotNone(hilo)
        self.assertEqual(hilo['mensajes'], [])
        self.assertEqual(hilo['avisos'], [])

    def test_lineas_basura_se_descartan_y_se_cuentan_en_avisos(self):
        hilo = hilos_notas.parse_hilo_conductor("""HILO CONDUCTOR
esto no es una entrada
- [Sagarde] sin fecha | A → B | Tampoco vale

- [Sagarde] 2026-09-29 | Vicente → Amets | Esta sí vale
FIN HILO
""")

        self.assertEqual(len(hilo['mensajes']), 1)
        self.assertEqual(len(hilo['avisos']), 2)
        self.assertTrue(all('descartada' in aviso.lower()
                            for aviso in hilo['avisos']))

    def test_fin_hilo_detiene_el_parser(self):
        hilo = hilos_notas.parse_hilo_conductor("""HILO CONDUCTOR
- [Sagarde] 2026-09-29 | Vicente → Amets | Dentro
 FIN HILO 
- [Egurrola] 2026-09-30 | Amets → Vicente | Fuera
""")

        self.assertEqual([m['texto'] for m in hilo['mensajes']], ['Dentro'])

    def test_marcadores_ignoran_mayusculas_y_espacios_alrededor(self):
        hilo = hilos_notas.parse_hilo_conductor("""  hilo conductor  
- [externo] 2026-09-29 | A → B | Consulta
  fin hilo  
""")

        self.assertEqual(len(hilo['mensajes']), 1)
        self.assertEqual(hilo['mensajes'][0]['lado'], 'Externo')

    def test_lado_desconocido_se_descarta(self):
        hilo = hilos_notas.parse_hilo_conductor("""HILO CONDUCTOR
- [Interno] 2026-09-29 | A → B | No debe entrar
- [Citado] 2026-09-28 | A → C | Sí debe entrar
FIN HILO
""")

        self.assertEqual([m['lado'] for m in hilo['mensajes']], ['Citado'])
        self.assertEqual(len(hilo['avisos']), 1)

    def test_hueco_no_admite_fecha_ni_personas(self):
        hilo = hilos_notas.parse_hilo_conductor("""HILO CONDUCTOR
- [Hueco] 2026-09-20 | A → B | Forma que no corresponde
- [Hueco] Faltan mensajes anteriores
FIN HILO
""")

        self.assertEqual(len(hilo['mensajes']), 1)
        self.assertEqual(hilo['mensajes'][0]['texto'],
                         'Faltan mensajes anteriores')
        self.assertEqual(len(hilo['avisos']), 1)


class TestSanearTexto(unittest.TestCase):

    def test_oculta_correos_telefonos_y_urls(self):
        original = (
            'correo persona@example.com; teléfonos 600 123 456, '
            '600.123.457, 600-123-458 y +34 600 123 459; '
            'web https://ejemplo.com/ruta?q=1 y www.ejemplo.net/ficha')

        saneado = hilos_notas.sanear_texto(original)

        for secreto in (
                'persona@example.com', '600 123 456', '600.123.457',
                '600-123-458', '+34 600 123 459',
                'https://ejemplo.com/ruta?q=1', 'www.ejemplo.net/ficha'):
            self.assertNotIn(secreto, saneado)
        self.assertEqual(saneado.count('[dato oculto]'), 7)

    def test_fecha_hora_y_numeros_cortos_no_se_alteran(self):
        normal = 'Revisión 2026-09-29 15:13 · portal 3 · vivienda 42'
        self.assertEqual(hilos_notas.sanear_texto(normal), normal)

    def test_parser_sanea_de_a_y_texto_antes_de_devolverlos(self):
        hilo = hilos_notas.parse_hilo_conductor("""HILO CONDUCTOR
- [Egurrola] 2026-09-29 | persona@example.com → Vicente | Llama al 600 123 456
FIN HILO
""")

        self.assertEqual(hilo['mensajes'][0]['de_a'],
                         '[dato oculto] → Vicente')
        self.assertEqual(hilo['mensajes'][0]['texto'],
                         'Llama al [dato oculto]')


class TestLeerHilosDeTareas(unittest.TestCase):

    def test_lee_txt_sin_distinguir_mayusculas_y_avisa_de_descartes(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            (carpeta / 'correo.TXT').write_text("""HILO CONDUCTOR
línea basura
- [Sagarde] 2026-09-29 | Vicente → Amets | Respuesta válida
FIN HILO
""", encoding='utf-8')

            hilos, avisos = hilos_notas.leer_hilos_de_tareas(carpeta, [{
                'Archivo': 'correo.TXT',
            }, {'Archivo': 'plano.pdf'}, {'Archivo': ''}])

        self.assertEqual(list(hilos), ['correo.TXT'])
        self.assertEqual(hilos['correo.TXT']['mensajes'][0]['texto'],
                         'Respuesta válida')
        self.assertEqual(len(avisos), 1)
        self.assertIn('correo.TXT', avisos[0])
        self.assertIn('descartada', avisos[0].lower())

    def test_avisa_si_falta_si_es_ilegible_o_si_el_bloque_esta_vacio(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            (carpeta / 'ilegible.txt').mkdir()
            (carpeta / 'vacio.txt').write_text(
                'HILO CONDUCTOR\nFIN HILO\n', encoding='utf-8')

            hilos, avisos = hilos_notas.leer_hilos_de_tareas(carpeta, [
                {'Archivo': 'falta.txt'}, {'Archivo': 'ilegible.txt'},
                {'Archivo': 'vacio.txt'},
            ])

        self.assertEqual(hilos['vacio.txt']['mensajes'], [])
        texto_avisos = '\n'.join(avisos).lower()
        self.assertIn('falta.txt', texto_avisos)
        self.assertIn('no existe', texto_avisos)
        self.assertIn('ilegible.txt', texto_avisos)
        self.assertIn('no se pudo leer', texto_avisos)
        self.assertIn('vacio.txt', texto_avisos)
        self.assertIn('sin entradas válidas', texto_avisos)

    def test_reemplaza_bytes_utf8_invalidos_sin_ocultar_el_bloque(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            (carpeta / 'bytes.txt').write_bytes(
                b'HILO CONDUCTOR\n- [Sagarde] 2026-09-29 | A -> B | '
                b'Mensaje \xff\nFIN HILO\n')

            hilos, avisos = hilos_notas.leer_hilos_de_tareas(
                carpeta, [{'Archivo': 'bytes.txt'}])

        self.assertEqual(avisos, [])
        self.assertIn('\ufffd', hilos['bytes.txt']['mensajes'][0]['texto'])

    def test_rechaza_traversal_rutas_absolutas_y_unidades_windows(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            carpeta = raiz / 'obra'
            carpeta.mkdir()
            secreto = raiz / 'secreto.txt'
            secreto.write_text("""HILO CONDUCTOR
- [Sagarde] 2026-09-29 | A → B | SECRETO-FUERA
FIN HILO
""", encoding='utf-8')
            archivos_peligrosos = [
                '../secreto.txt', '..\\secreto.txt', str(secreto),
                r'C:\datos\secreto.txt', r'C:secreto.txt',
            ]

            hilos, avisos = hilos_notas.leer_hilos_de_tareas(
                carpeta,
                [{'Archivo': archivo} for archivo in archivos_peligrosos])

        self.assertEqual(hilos, {})
        self.assertEqual(len(avisos), len(archivos_peligrosos))
        self.assertNotIn('SECRETO-FUERA', '\n'.join(avisos))
        self.assertTrue(all('rechazado' in aviso.lower() for aviso in avisos))


class TestPrivacidadYExtremoAExtremo(unittest.TestCase):

    @staticmethod
    def _tarea(archivo='correo.txt'):
        return {
            'Tarea': 'Resolver duda de volumen', 'Origen': 'Correo',
            'Fecha': '29/09/2026', 'Archivo': archivo,
            'Estado': 'Pendiente',
        }

    def test_borrar_una_linea_de_la_nota_la_borra_del_html_final(self):
        con_linea = """HILO CONDUCTOR
- [Egurrola] 2026-09-29 15:13 | Amets → Vicente | Mensaje que se conserva
- [Sagarde] 2026-09-29 15:20 | Vicente → Amets | MENSAJE-QUE-SE-BORRA
FIN HILO
"""
        sin_linea = con_linea.replace(
            '- [Sagarde] 2026-09-29 15:20 | Vicente → Amets | '
            'MENSAJE-QUE-SE-BORRA\n', '')
        tarea = self._tarea()

        html_antes = panel_obra._tabla_tareas_manuales(
            [tarea], [], hilos={'correo.txt':
                                hilos_notas.parse_hilo_conductor(con_linea)})
        html_despues = panel_obra._tabla_tareas_manuales(
            [tarea], [], hilos={'correo.txt':
                                hilos_notas.parse_hilo_conductor(sin_linea)})

        self.assertIn('MENSAJE-QUE-SE-BORRA', html_antes)
        self.assertNotIn('MENSAJE-QUE-SE-BORRA', html_despues)
        self.assertIn('Mensaje que se conserva', html_despues)

    def test_html_escapa_script_comillas_y_sanea_datos_aunque_le_pasemos_dict(self):
        hilo_sin_confiar = {
            'mensajes': [{
                'lado': 'Egurrola', 'fecha': '2026-09-29', 'hora': '15:13',
                'de_a': '"persona@example.com" → Vicente',
                'texto': '<script>alert(1)</script> llamar +34 600 123 456',
            }],
            'avisos': [],
        }

        html = panel_obra._tabla_tareas_manuales(
            [self._tarea()], [], hilos={'correo.txt': hilo_sin_confiar})

        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('persona@example.com', html)
        self.assertNotIn('+34 600 123 456', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertIn('&quot;[dato oculto]&quot; → Vicente', html)
        self.assertGreaterEqual(html.count('[dato oculto]'), 2)

    def test_nota_fixture_llega_hasta_generar_panel(self):
        with tempfile.TemporaryDirectory() as temporal:
            carpeta = Path(temporal)
            nota = carpeta / 'correo-origen.txt'
            nota.write_text("""Asunto: consulta
HILO CONDUCTOR
- [Egurrola] 2026-09-29 15:13 | Amets → Vicente | Pregunta inicial
- [Sagarde] 2026-09-29 15:20 | Vicente → Amets | Respuesta final
FIN HILO
""", encoding='utf-8')
            tareas = [self._tarea(nota.name)]
            hilos, avisos = hilos_notas.leer_hilos_de_tareas(carpeta, tareas)
            ficha = {
                '_disponible': True, 'datos': {}, 'personal': [],
                'hitos': [], 'riesgos': [], 'plan': [], 'tareas': tareas,
                'hilos_tareas': hilos,
            }
            salida = carpeta / 'panel.html'

            panel_obra.generar_panel(
                obra='Obra fixture', subtitulo='', historial=[],
                materiales={}, ficha=ficha, documentos=[],
                prioridades=_prioridades_vacias(), output_path=str(salida))
            html = salida.read_text(encoding='utf-8')

        self.assertEqual(avisos, [])
        self.assertIn("<details class='cadena-hilo'>", html)
        self.assertIn('Pregunta inicial', html)
        self.assertIn('Respuesta final', html)
        self.assertLess(html.index('Pregunta inicial'), html.index('Respuesta final'))


if __name__ == '__main__':
    unittest.main()
