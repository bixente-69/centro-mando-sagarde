# -*- coding: utf-8 -*-
import copy
import os
import tempfile
import unittest

import ficha_garajes


def ficha_minima():
    return {
        'estructura': {
            'garajes': [
                {
                    'id': 'garaje_b1',
                    'nombre': 'Garaje Bloque 1',
                    'plantas': [
                        {
                            'id': 's1',
                            'nombre': 'S-1',
                            'zonas': [
                                {
                                    'id': 'zona_a',
                                    'tipo': 'vial',
                                    'nombre': 'Zona A',
                                    'origen': 'asistente',
                                    'confirmado': True,
                                },
                                {
                                    'id': 'cuarto_1',
                                    'tipo': 'cuarto_tecnico',
                                    'nombre': 'Cuarto técnico 1',
                                    'origen': 'asistente',
                                    'confirmado': True,
                                },
                            ],
                        }
                    ],
                }
            ],
            '_meta': {},
        },
        'tajos': {
            'detalle': [
                {'id': 'bandeja', 'nombre': 'Bandeja'},
                {'id': 'lucido', 'nombre': 'Lucido'},
            ],
            '_meta': {},
        },
        'estados': {},
        'revisiones': [],
        'dudas': [],
    }


def fila(zona_id, estado, tarea='Bandeja', fecha=None):
    dato = {
        'task': tarea,
        'floor': 'S-1',
        'garaje': 'Garaje Bloque 1',
        'zona': 'Zona A' if zona_id == 'zona_a' else 'Cuarto técnico 1',
        'status': estado,
        'garaje_id': 'garaje_b1',
        'planta_id': 's1',
        'zona_id': zona_id,
    }
    if fecha is not None:
        dato['ultima_fecha'] = fecha
    return dato


class TestFichaGarajes(unittest.TestCase):
    def test_asegurar_apartados_crea_cinco_y_es_idempotente(self):
        ficha = {}

        creados = ficha_garajes.asegurar_apartados(ficha)

        self.assertEqual(list(ficha_garajes.APARTADOS), creados)
        self.assertEqual({}, ficha['estructura']['_meta'])
        self.assertEqual({}, ficha['tajos']['_meta'])
        self.assertEqual([], ficha['revisiones'])
        self.assertEqual([], ficha['dudas'])
        self.assertEqual([], ficha_garajes.asegurar_apartados(ficha))
        self.assertEqual(set(ficha_garajes.APARTADOS), set(ficha))

    def test_guardar_y_cargar_hacen_roundtrip_en_directorio_temporal(self):
        ficha = ficha_minima()
        ficha['dudas'].append('acentos: canalización')

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = ficha_garajes.guardar(carpeta, ficha)

            self.assertEqual(
                os.path.join(
                    carpeta, 'INFORME SAGARDE IA', 'ficha_garajes.json'),
                ruta,
            )
            self.assertEqual(ficha, ficha_garajes.cargar(carpeta))

    def test_aplicar_snapshot_guarda_dos_zonas_con_clave_de_cuatro_partes(self):
        ficha = ficha_minima()
        snapshot = [fila('zona_a', 'X'), fila('cuarto_1', 'M')]

        actualizada, cambios = ficha_garajes.actualizar_desde_snapshot(
            ficha, snapshot, '24/09/2026')

        self.assertIs(ficha, actualizada)
        self.assertEqual(
            'X',
            ficha['estados']['garaje_b1__s1__bandeja__zona_a']['v'],
        )
        self.assertEqual(
            'M',
            ficha['estados']['garaje_b1__s1__bandeja__cuarto_1']['v'],
        )
        self.assertEqual(2, cambios['estados_nuevos'])

    def test_snapshot_desde_ficha_excluye_estado_n(self):
        ficha = ficha_minima()

        ficha_garajes.actualizar_desde_snapshot(
            ficha,
            [fila('zona_a', 'N'), fila('cuarto_1', 'X')],
            '24/09/2026',
        )

        snapshot = ficha_garajes.snapshot_desde_ficha(ficha)

        self.assertEqual(
            'N', ficha['estados']['garaje_b1__s1__bandeja__zona_a']['v']
        )
        self.assertEqual(1, len(snapshot))
        self.assertEqual('cuarto_1', snapshot[0]['zona_id'])
        self.assertEqual('X', snapshot[0]['status'])
        self.assertNotIn('zona_a', {registro['zona_id'] for registro in snapshot})

    def test_vacio_no_baja_x_y_p_explicito_si_la_baja(self):
        ficha = ficha_minima()
        clave = 'garaje_b1__s1__bandeja__zona_a'
        ficha['estados'][clave] = {
            'v': 'X', 'f': '20/09/2026', 'r': 'rev_20092026'
        }

        ficha_garajes.actualizar_desde_snapshot(
            ficha, [fila('zona_a', '')], '24/09/2026')

        self.assertEqual('X', ficha['estados'][clave]['v'])
        self.assertEqual('24/09/2026', ficha['estados'][clave]['f'])

        ficha_garajes.actualizar_desde_snapshot(
            ficha, [fila('zona_a', 'P')], '25/09/2026')

        self.assertEqual(
            {'v': 'P', 'f': '25/09/2026', 'r': 'rev_25092026'},
            ficha['estados'][clave],
        )

    def test_zona_desconocida_se_descarta_y_se_declara_en_cambios(self):
        ficha = ficha_minima()
        estructura_original = copy.deepcopy(ficha['estructura'])
        desconocida = fila('zona_inexistente', 'X')
        desconocida['zona'] = 'Zona inexistente'

        _, cambios = ficha_garajes.actualizar_desde_snapshot(
            ficha, [desconocida], '24/09/2026')

        self.assertTrue(cambios['zonas_desconocidas'])
        self.assertIn(
            'garaje_b1__s1__zona_inexistente',
            cambios['zonas_desconocidas'],
        )
        self.assertEqual(estructura_original, ficha['estructura'])
        self.assertEqual({}, ficha['estados'])

    def test_misma_revision_no_se_registra_dos_veces(self):
        ficha = ficha_minima()

        ficha_garajes.actualizar_desde_snapshot(
            ficha, [fila('zona_a', 'X')], '24/09/2026')
        ficha_garajes.actualizar_desde_snapshot(
            ficha, [fila('zona_a', 'M')], '24/09/2026')

        self.assertEqual(1, len(ficha['revisiones']))
        self.assertEqual('rev_24092026', ficha['revisiones'][0]['id'])

    def test_esta_rancia_distingue_revision_pendiente_y_registrada(self):
        ficha = ficha_minima()
        datos = {'revision': '24/09/2026'}

        motivo = ficha_garajes.esta_rancia(ficha, datos)

        self.assertIn('24/09/2026', motivo)
        ficha['revisiones'].append(
            {'id': 'rev_24092026', 'fecha': '24/09/2026'}
        )
        self.assertIsNone(ficha_garajes.esta_rancia(ficha, datos))

    def test_tajo_nuevo_se_declara_y_mapa_corto_se_aplica(self):
        ficha = ficha_minima()
        ficha['tajos']['detalle'] = []

        _, cambios = ficha_garajes.actualizar_desde_snapshot(
            ficha,
            [fila('zona_a', 'X', tarea='band')],
            '24/09/2026',
            mapa_tajos_cortos={'band': 'bandeja'},
        )

        self.assertEqual(['bandeja'], cambios['tajos_nuevos'])
        self.assertEqual('bandeja', ficha['tajos']['detalle'][0]['id'])
        self.assertEqual(
            'revision_sin_confirmar', ficha['tajos']['detalle'][0]['origen']
        )
        self.assertIn(
            'garaje_b1__s1__bandeja__zona_a', ficha['estados']
        )

    def test_estado_no_reconocido_no_baja_y_queda_visible_en_cambios(self):
        ficha = ficha_minima()
        clave = 'garaje_b1__s1__bandeja__zona_a'
        ficha['estados'][clave] = {
            'v': 'X', 'f': '20/09/2026', 'r': 'rev_20092026'
        }

        _, cambios = ficha_garajes.actualizar_desde_snapshot(
            ficha, [fila('zona_a', 'terminado quizá')], '24/09/2026')

        self.assertEqual('X', ficha['estados'][clave]['v'])
        self.assertEqual('24/09/2026', ficha['estados'][clave]['f'])
        self.assertEqual(['terminado quizá'], cambios['estados_no_reconocidos'])

    def test_no_autocompleta_combinaciones_no_reportadas_y_las_resume(self):
        ficha = ficha_minima()

        _, cambios = ficha_garajes.actualizar_desde_snapshot(
            ficha, [fila('zona_a', 'X')], '24/09/2026')
        lineas = ficha_garajes.resumen_cambios(cambios)

        self.assertEqual(
            {'garaje_b1__s1__bandeja__zona_a'}, set(ficha['estados'])
        )
        self.assertIn('celdas nuevas: 1', lineas)


if __name__ == '__main__':
    unittest.main()
