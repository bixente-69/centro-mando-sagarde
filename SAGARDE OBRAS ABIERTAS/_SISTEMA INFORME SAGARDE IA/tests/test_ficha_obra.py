# -*- coding: utf-8 -*-
import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ficha_obra
import fixtures


class TestApartados(unittest.TestCase):

    def test_crea_los_apartados_que_faltan(self):
        ficha = {'id': 'pruebas'}
        creados = ficha_obra.asegurar_apartados(ficha)
        for nombre in ficha_obra.APARTADOS:
            self.assertIn(nombre, ficha)
        self.assertIn('materiales', creados)

    def test_no_pisa_los_apartados_que_ya_existen(self):
        ficha = fixtures.ficha_minima()
        ficha['materiales'] = {'algo': 1}
        creados = ficha_obra.asegurar_apartados(ficha)
        self.assertEqual(creados, [])
        self.assertEqual(ficha['materiales'], {'algo': 1})


class TestEstados(unittest.TestCase):

    def test_una_celda_medida_se_guarda_con_su_fecha(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='X')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        celda = ficha['estados']['p1__pb__tubeado__A']
        self.assertEqual(celda['v'], 'X')
        self.assertEqual(celda['f'], '27/07/2026')
        self.assertEqual(celda['r'], 'rev_27072026')

    def test_pendiente_se_guarda_como_P_no_como_ausencia(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='Pendiente')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        # Verificar que se guardó como P
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'P')
        # Verificar que no aparece en estados no reconocidos (porque es reconocido)
        self.assertNotIn('pendiente', cambios['estados_no_reconocidos'])

    def test_las_celdas_sin_dato_nacen_como_desconocido(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        # 1 portal x 2 plantas x 2 viviendas x 2 tajos = 8 celdas
        self.assertEqual(len(ficha['estados']), 8)
        self.assertEqual(ficha['estados']['p1__1__cableado__B']['v'], '?')

    def test_la_ultima_revision_manda_aunque_baje_de_X(self):
        """Norma de obra: si el revisor escribe M sobre algo que figuraba
        terminado, es que ha ido y ha visto que faltaba algo."""
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='X')]))
        ficha, cambios = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='M')],
                                        revision='30/07/2026'))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')
        self.assertIn(('p1__pb__tubeado__A', 'X', 'M'), cambios['estados_cambiados'])

    def test_una_casilla_en_blanco_NO_baja_un_estado_conocido(self):
        """La otra mitad de la norma: 'solo la ausencia de marca no puede
        bajar una X'.

        Caso real: REVISION MUNGIA 28072026.pdf era una hoja generada por la
        app y nunca usada -0 anotaciones, sin sidecar-. La app imprime en
        blanco lo que no sabe, asi que al releerla 35 celdas de la vivienda E
        pasaron de '?' a 'P' y Mungia bajo de 79.8 a 78.6 sin que nadie
        hubiera pisado la obra. Una casilla vacia es 'no se leyo', no
        'se comprobo y no esta'.
        """
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='X')]))
        ficha, cambios = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='')],
                                        revision='30/07/2026'))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')
        self.assertEqual(cambios['estados_cambiados'], [])

    def test_una_casilla_en_blanco_tampoco_baja_una_M(self):
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='M')]))
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='')],
                                        revision='30/07/2026'))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')

    def test_pero_un_PENDIENTE_explicito_si_baja_una_X(self):
        """Escribir 'Pendiente' es ir y ver que no esta. Eso manda."""
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='X')]))
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='Pendiente')],
                                        revision='30/07/2026'))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'P')

    def test_una_casilla_en_blanco_NO_convierte_un_desconocido_en_pendiente(self):
        """El caso exacto de la vivienda E de Mungia.

        La celda estaba en '?' porque nadie la habia mirado. La app imprime en
        blanco lo que no sabe, y al releer la hoja el blanco la paso a 'P'
        -'se comprobo y no esta'-, que es justo lo contrario de lo que pasaba.
        Dos ausencias de informacion no hacen un dato.
        """
        ficha = fixtures.ficha_minima()
        ficha['estados']['p1__pb__tubeado__A'] = {'v': '?', 'f': None, 'r': None}
        ficha, cambios = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='')]))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], '?')
        self.assertEqual(cambios['estados_cambiados'], [])

    def test_una_casilla_en_blanco_sin_nada_previo_sigue_siendo_P(self):
        """Primera vez que se ve la celda: no hay estado que proteger."""
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='')]))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'P')

    def test_no_toca_las_celdas_que_la_revision_no_menciona(self):
        """Si la hoja no cubre una celda, su dato anterior se conserva.
        Una revision parcial no puede borrar lo que no ha mirado."""
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(ficha, fixtures.prioridades([
            fixtures.item(unidad='A', estado='X'),
            fixtures.item(unidad='B', estado='X'),
        ]))
        ficha, _ = ficha_obra.actualizar(ficha, fixtures.prioridades(
            [fixtures.item(unidad='A', estado='M')], revision='30/07/2026'))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__B']['v'], 'X')

    def test_variantes_de_mayusculas_de_pendiente_se_reconocen(self):
        """'pendiente', 'PENDIENTE', 'Pendiente' deben convertirse todas a 'P'."""
        for estado_variante in ('pendiente', 'PENDIENTE', 'Pendiente', 'PeNdIeNtE'):
            ficha = fixtures.ficha_minima()
            prio = fixtures.prioridades([fixtures.item(estado=estado_variante)])
            ficha, cambios = ficha_obra.actualizar(ficha, prio)
            self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'P',
                           msg=f"Variante '{estado_variante}' no se convirtió a P")
            self.assertEqual(cambios['estados_no_reconocidos'], [],
                           msg=f"Variante '{estado_variante}' apareció como no reconocida")

    def test_estado_desconocido_se_guarda_como_desconocido(self):
        """Un estado que no se reconoce debe guardarse como '?' (desconocido),
        no como 'P', y debe aparecer en estados_no_reconocidos."""
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='ZZZ')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        # Debe guardarse como ?
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], '?')
        # Debe aparecer en estados_no_reconocidos
        self.assertIn('zzz', cambios['estados_no_reconocidos'])
        # Debe aparecer en el resumen de cambios
        resumen = ficha_obra.resumen_cambios(cambios)
        self.assertTrue(any('ESTADOS NO RECONOCIDOS' in linea for linea in resumen),
                       msg="Estado no reconocido no aparece en el resumen de cambios")

    def test_correcciones_manuales_mayuscula_X_se_normalizan(self):
        """Una corrección manual con 'X' en mayúscula debe normalizarse y aplicarse.
        Las correcciones son marcas que el jefe de obra escribe a boli sobre
        la hoja de campo — el dato más directo que existe."""
        ficha = fixtures.ficha_minima()
        # Estado base: 'M' en p1__pb__tubeado__A
        prio = fixtures.prioridades([fixtures.item(unidad='A', estado='M')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        # Segunda revisión: procesa un item diferente (B), y aplica corrección en A
        prio2 = fixtures.prioridades([fixtures.item(unidad='B', estado='X')],
                                    revision='28/07/2026')
        correcciones = {'p1__pb__tubeado__A': 'X'}  # mayúscula
        ficha, cambios = ficha_obra.actualizar(ficha, prio2, correcciones=correcciones)
        # Debe cambiar A a 'X' (normalizado)
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')
        # Debe registrarse en correcciones_reclamadas
        self.assertIn(('p1__pb__tubeado__A', 'M', 'X'), cambios['correcciones_reclamadas'])
        # No debe aparecer en estados_no_reconocidos (porque se reconoció)
        self.assertNotIn('x', cambios['estados_no_reconocidos'])

    def test_correcciones_manuales_mayuscula_M_y_Pendiente(self):
        """Correcciones con variantes de 'M', 'Pendiente' en mayúscula también se normalizan."""
        ficha = fixtures.ficha_minima()
        # Estado base: '?' en ambas celdas (sin datos)
        prio = fixtures.prioridades([])  # Sin items, solo estructura
        # Forzar creación de estados con estado_base
        prio_base = fixtures.prioridades([fixtures.item(unidad='A', estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio_base)

        # Correcciones: una con 'M' mayúscula, otra con 'Pendiente' mayúscula
        prio_rev2 = fixtures.prioridades([fixtures.item(unidad='B', estado='X')],
                                        revision='29/07/2026')
        correcciones = {
            'p1__pb__tubeado__A': 'M',          # mayúscula
            'p1__1__cableado__B': 'Pendiente',  # mayúscula
        }
        ficha, cambios = ficha_obra.actualizar(ficha, prio_rev2, correcciones=correcciones)

        # Ambas correcciones deben aplicarse
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')
        self.assertEqual(ficha['estados']['p1__1__cableado__B']['v'], 'P')

        # Ambas deben estar en correcciones_reclamadas
        self.assertEqual(len(cambios['correcciones_reclamadas']), 2)

        # Ninguna debe aparecer en estados_no_reconocidos
        self.assertEqual(cambios['estados_no_reconocidos'], [])

    def test_correcciones_manuales_no_reconocidas_son_visibles(self):
        """Una corrección con estado no reconocido no se aplica, pero aparece en estados_no_reconocidos."""
        ficha = fixtures.ficha_minima()
        # Estado base
        prio = fixtures.prioridades([fixtures.item(unidad='A', estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)

        # Corrección con estado inventado
        prio_rev2 = fixtures.prioridades([fixtures.item(unidad='B', estado='X')],
                                        revision='29/07/2026')
        correcciones = {'p1__pb__tubeado__A': 'INVENTADO'}
        ficha, cambios = ficha_obra.actualizar(ficha, prio_rev2, correcciones=correcciones)

        # La celda debe mantener su estado anterior (X)
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')

        # NO debe estar en correcciones_reclamadas
        self.assertEqual(len(cambios['correcciones_reclamadas']), 0)

        # DEBE aparecer en estados_no_reconocidos
        self.assertIn('inventado', cambios['estados_no_reconocidos'])

        # DEBE aparecer en el resumen
        resumen = ficha_obra.resumen_cambios(cambios)
        self.assertTrue(any('ESTADOS NO RECONOCIDOS' in linea for linea in resumen))


class TestAltasSinConfirmar(unittest.TestCase):

    def test_una_vivienda_nueva_entra_marcada_sin_confirmar_y_avisa(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(unidad='C', estado='X')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        pb = ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0]
        nueva = next(u for u in pb['ubicaciones'] if u['id'] == 'C')
        self.assertEqual(nueva['origen'], 'revision_sin_confirmar')
        self.assertIsNone(nueva['confirmado'])
        self.assertTrue(any('unidad C' in a for a in cambios['ubicaciones_nuevas']))
        self.assertEqual(ficha['estados']['p1__pb__tubeado__C']['v'], 'X')

    def test_una_planta_nueva_tambien_entra_sin_confirmar(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(planta='2', unidad='A')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        plantas = ficha['estructura']['bloques'][0]['portales'][0]['plantas']
        nueva = next(p for p in plantas if p['nombre'] == '2')
        self.assertEqual(nueva['origen'], 'revision_sin_confirmar')
        self.assertTrue(any('planta entera' in a for a in cambios['ubicaciones_nuevas']))

    def test_un_portal_desconocido_NO_se_inventa(self):
        """Un portal entero que no existe casi siempre es un error de lectura,
        no una obra que ha crecido. Se ignora y no se ensucia la estructura."""
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(edificio='P9', unidad='A')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        portales = ficha['estructura']['bloques'][0]['portales']
        self.assertEqual([p['id'] for p in portales], ['p1'])

    def test_un_tajo_nuevo_entra_sin_confirmar_y_avisa(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(
            tarea='mecanizado', trabajo='Mecanizado', orden=30)])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        self.assertIn('mecanizado', cambios['tajos_nuevos'])
        nuevo = next(t for t in ficha['tajos']['detalle'] if t['id'] == 'mecanizado')
        self.assertEqual(nuevo['origen'], 'revision_sin_confirmar')
        self.assertIn('mecanizado', ficha['tajos']['aplicables'])

    def test_las_plantas_quedan_ordenadas_con_PB_primero(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(planta='2', unidad='A')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        nombres = [p['nombre'] for p in
                   ficha['estructura']['bloques'][0]['portales'][0]['plantas']]
        self.assertEqual(nombres, ['PB', '1', '2'])


class TestExclusionesConfirmadas(unittest.TestCase):
    """Una ubicacion descartada a proposito no puede volver al regenerar.

    El caso real son las 4 viviendas fantasma de la PB de Bolueta: la hoja las
    imprime, el adaptador las emite, y la ficha las readmitia en cada pasada
    aunque la confirmacion de Bixente dijera que PB no tiene viviendas, solo
    dos locales. La ficha declaraba 101 ubicaciones en vez de 97.
    """

    def _ficha_con_exclusion(self):
        ficha = fixtures.ficha_minima()
        ficha['estructura']['exclusiones'] = [{
            'portal': 'P1', 'planta': 'PB', 'unidad': 'C',
            'motivo': 'la hoja la imprime pero no existe',
            'confirmado': '28/07/2026',
        }]
        return ficha

    def test_una_ubicacion_excluida_no_vuelve_a_darse_de_alta(self):
        ficha = self._ficha_con_exclusion()
        prio = fixtures.prioridades([fixtures.item(unidad='C', estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        pb = ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0]
        self.assertEqual([u['id'] for u in pb['ubicaciones']], ['A', 'B'])

    def test_la_celda_de_una_ubicacion_excluida_tampoco_se_guarda(self):
        """Si la ubicacion no existe, su estado no puede contar para el KPI."""
        ficha = self._ficha_con_exclusion()
        prio = fixtures.prioridades([fixtures.item(unidad='C', estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        self.assertNotIn('p1__pb__tubeado__C', ficha['estados'])

    def test_la_exclusion_se_reporta_y_no_es_silenciosa(self):
        """Un descarte que no se cuenta es indistinguible de un fallo."""
        ficha = self._ficha_con_exclusion()
        prio = fixtures.prioridades([fixtures.item(unidad='C', estado='X')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        self.assertTrue(any('unidad C' in a
                            for a in cambios['ubicaciones_excluidas']))

    def test_el_descarte_sale_por_consola(self):
        """resumen_cambios es lo unico que Bixente ve al regenerar."""
        ficha = self._ficha_con_exclusion()
        prio = fixtures.prioridades([fixtures.item(unidad='C', estado='X')])
        _, cambios = ficha_obra.actualizar(ficha, prio)
        lineas = ficha_obra.resumen_cambios(cambios)
        self.assertTrue(any('excluida' in l and 'unidad C' in l for l in lineas),
                        f'no se reporta el descarte: {lineas}')

    def test_una_ubicacion_nueva_DE_VERDAD_sigue_entrando(self):
        """La exclusion es quirurgica: no puede cerrar la puerta a lo demas."""
        ficha = self._ficha_con_exclusion()
        prio = fixtures.prioridades([fixtures.item(unidad='D', estado='X')])
        ficha, cambios = ficha_obra.actualizar(ficha, prio)
        pb = ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0]
        self.assertIn('D', [u['id'] for u in pb['ubicaciones']])
        self.assertTrue(any('unidad D' in a
                            for a in cambios['ubicaciones_nuevas']))

    def test_la_exclusion_distingue_la_planta(self):
        """'C' esta excluida en PB, pero eso no dice nada de la planta 1."""
        ficha = self._ficha_con_exclusion()
        prio = fixtures.prioridades([fixtures.item(planta='1', unidad='C')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        plantas = ficha['estructura']['bloques'][0]['portales'][0]['plantas']
        p1 = next(p for p in plantas if p['nombre'] == '1')
        self.assertIn('C', [u['id'] for u in p1['ubicaciones']])

    def test_una_ubicacion_que_YA_existe_no_la_borra_la_exclusion(self):
        """La exclusion frena altas nuevas; no destruye lo ya confirmado.

        Borrar en silencio seria el mismo fallo por el otro lado.
        """
        ficha = self._ficha_con_exclusion()
        ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0][
            'ubicaciones'].append({'id': 'C', 'tipo': 'vivienda',
                                   'origen': 'confirmado_usuario'})
        prio = fixtures.prioridades([fixtures.item(unidad='C', estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        pb = ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0]
        self.assertIn('C', [u['id'] for u in pb['ubicaciones']])
        self.assertEqual(ficha['estados']['p1__pb__tubeado__C']['v'], 'X')

    def test_manda_tambien_en_el_camino_del_snapshot_crudo(self):
        """El camino de produccion es este, no el de prioridades."""
        ficha = self._ficha_con_exclusion()
        snapshot = [{'building': 'P1', 'floor': 'PB', 'unit': 'C',
                     'task': 'Tubeado', 'status': 'X'}]
        ficha, _ = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026')
        pb = ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0]
        self.assertEqual([u['id'] for u in pb['ubicaciones']], ['A', 'B'])


class TestCorrecciones(unittest.TestCase):

    def test_traduce_el_codigo_corto_de_tajo_al_largo(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='Pendiente')])
        ficha, cambios = ficha_obra.actualizar(
            ficha, prio,
            correcciones={'p1__pb__tub__A': 'X'},
            mapa_tajos_cortos={'tub': 'tubeado'})
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['origen'],
                         'correccion manual')

    def test_recompone_una_unidad_partida_por_el_extractor(self):
        """'PORT AL' es 'PORTAL' con un espacio metido por pdfplumber."""
        ficha = fixtures.ficha_minima()
        ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0][
            'ubicaciones'].append(
                {'id': 'PORTAL', 'tipo': 'zona_comun', 'origen': 'campo'})
        prio = fixtures.prioridades([fixtures.item(estado='X')])
        ficha, _ = ficha_obra.actualizar(
            ficha, prio, correcciones={'p1__pb__tubeado__PORT AL': 'M'})
        self.assertEqual(ficha['estados']['p1__pb__tubeado__PORTAL']['v'], 'M')

    def test_llega_a_una_vivienda_que_la_revision_no_conoce(self):
        """El caso de la vivienda E de Mungia: existe en la ficha, la
        revision no la lee, pero Bixente si la relleno a boli."""
        ficha = fixtures.ficha_minima()
        ficha['estructura']['bloques'][0]['portales'][0]['plantas'][0][
            'ubicaciones'].append({'id': 'E', 'tipo': 'vivienda',
                                   'origen': 'confirmado_usuario'})
        prio = fixtures.prioridades([fixtures.item(unidad='A', estado='X')])
        ficha, cambios = ficha_obra.actualizar(
            ficha, prio, correcciones={'p1__pb__cableado__E': 'X'})
        self.assertEqual(ficha['estados']['p1__pb__cableado__E']['v'], 'X')
        self.assertEqual(len(cambios['correcciones_reclamadas']), 1)

    def test_una_correccion_que_coincide_no_se_cuenta_como_cambio(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item(estado='X')])
        ficha, cambios = ficha_obra.actualizar(
            ficha, prio, correcciones={'p1__pb__tubeado__A': 'X'})
        self.assertEqual(cambios['correcciones_reclamadas'], [])

    def test_con_alias_traduce_nombre_historico_al_canonico(self):
        """Reproduces Mungia: A2 (histórico) → A (canónico).
        La corrección llega con el nombre histórico, pero la ficha
        lo conoce solo por el canónico. _con_alias hace la traducción."""
        ficha = fixtures.ficha_minima()
        # Añadir el alias: A2 es el nombre histórico de A
        ficha['estructura']['alias_historico']['p1__pb__A'] = 'A2'
        # Primer actualizar: procesa A con estado X
        prio = fixtures.prioridades([fixtures.item(unidad='A', estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        # Segundo actualizar: la corrección viene con el nombre histórico A2
        # pero debe encontrar y aplicarse sobre la celda canónica A
        prio2 = fixtures.prioridades([fixtures.item(unidad='B', estado='X')],
                                     revision='28/07/2026')
        ficha, cambios = ficha_obra.actualizar(
            ficha, prio2, correcciones={'p1__pb__tubeado__A2': 'M'})
        # La corrección debe haberse aplicado sobre la ubicación canónica
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'M')
        # Debe estar registrada en correcciones_reclamadas como cambio
        self.assertIn(('p1__pb__tubeado__A', 'X', 'M'),
                      cambios['correcciones_reclamadas'])

    def test_alias_no_resuelve_por_casualidad_en_otra_planta(self):
        """El alias A2 existe en la planta '1', pero la corrección es para
        la planta 'pb'. _con_alias debe respetar el portal y planta: no
        case por coincidencia de nombre."""
        ficha = fixtures.ficha_minima()
        # Alias A2 en otra planta (planta '1')
        ficha['estructura']['alias_historico']['p1__1__A'] = 'A2'
        # Primer actualizar: llena la matriz
        prio = fixtures.prioridades([fixtures.item(unidad='A', estado='X')])
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        # Segundo actualizar: intenta corregir pb con el alias A2
        # No debe encontrarlo porque el alias está en planta '1'
        prio2 = fixtures.prioridades([fixtures.item(unidad='B', estado='X')],
                                     revision='28/07/2026')
        ficha, cambios = ficha_obra.actualizar(
            ficha, prio2, correcciones={'p1__pb__tubeado__A2': 'M'})
        # La corrección no debe aplicarse: A sigue siendo X
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')
        # No debe haber correcciones reclamadas (porque no encontró el alias)
        self.assertEqual(len(cambios['correcciones_reclamadas']), 0)


class TestRancia(unittest.TestCase):

    def test_detecta_que_la_ficha_va_por_detras(self):
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item()], revision='20/07/2026'))
        motivo = ficha_obra.esta_rancia(
            ficha, fixtures.prioridades([fixtures.item()], revision='27/07/2026'))
        self.assertIsNotNone(motivo)
        self.assertIn('27/07/2026', motivo)

    def test_no_avisa_cuando_esta_al_dia(self):
        ficha = fixtures.ficha_minima()
        prio = fixtures.prioridades([fixtures.item()], revision='27/07/2026')
        ficha, _ = ficha_obra.actualizar(ficha, prio)
        self.assertIsNone(ficha_obra.esta_rancia(ficha, prio))


class TestApartadosRellenos(unittest.TestCase):

    def test_identidad_toma_los_datos_del_xlsx_sin_pisar_lo_que_ya_hay(self):
        ficha = fixtures.ficha_minima()
        ficha['identidad']['tipo_obra'] = 'viviendas'
        cambiados = ficha_obra.volcar_apartados(ficha, ficha_xlsx={
            '_disponible': True,
            'datos': {'Cliente': 'NEINOR', 'Constructora': 'ACR'},
            'personal': [{'Nombre': 'Bixente', 'Rol': 'Jefe de obra'}],
            'hitos': [], 'riesgos': [], 'plan': [],
        })
        self.assertEqual(ficha['identidad']['cliente'], 'NEINOR')
        self.assertEqual(ficha['identidad']['constructora'], 'ACR')
        self.assertEqual(ficha['identidad']['tipo_obra'], 'viviendas')
        self.assertEqual(len(ficha['contactos']), 1)
        self.assertIn('identidad', cambiados)

    def test_materiales_guarda_resumen_y_no_la_lista_entera(self):
        ficha = fixtures.ficha_minima()
        ficha_obra.volcar_apartados(ficha, materiales={
            'disponible': True, 'meses': ['Junio26', 'Julio26'],
            'ultimo_mes': 'Julio26', 'ultima_fecha': '20/07/2026',
            'dias_desde': 7, 'aviso': None,
            'items': [{'categoria': 'Cable', 'material': 'RZ1 3G1.5',
                       'tipo': 'm', 'uni': 'm', 'total': 500}],
        })
        self.assertEqual(ficha['materiales']['ultimo_mes'], 'Julio26')
        self.assertEqual(ficha['materiales']['n_items'], 1)
        self.assertEqual(ficha['materiales']['dias_desde'], 7)

    def test_documentos_guarda_el_recuento_por_categoria(self):
        ficha = fixtures.ficha_minima()
        ficha_obra.volcar_apartados(ficha, documentos=[
            {'nombre': 'a.pdf', 'categoria': 'Planos', 'subcarpeta': '.',
             'href': 'a.pdf', 'kb': 100},
            {'nombre': 'b.pdf', 'categoria': 'Planos', 'subcarpeta': '.',
             'href': 'b.pdf', 'kb': 50},
            {'nombre': 'c.xlsx', 'categoria': 'Otros', 'subcarpeta': 'x',
             'href': 'x/c.xlsx', 'kb': 10},
        ])
        self.assertEqual(ficha['documentos']['total'], 3)
        self.assertEqual(ficha['documentos']['por_categoria']['Planos'], 2)

    def test_sin_datos_no_marca_nada_como_cambiado(self):
        ficha = fixtures.ficha_minima()
        self.assertEqual(ficha_obra.volcar_apartados(ficha), [])

    def test_identidad_no_pisa_valor_existente_con_cadena_vacia_ni_con_none(self):
        """Ronda de correccion 1: el revisor comprobo por mutacion que quitar
        `valor not in (None, '')` dejaba las 40 pruebas en verde -- la prueba
        original solo protegia 'tipo_obra', que ni siquiera esta en
        CAMPOS_IDENTIDAD, asi que sobrevivia pasara lo que pasara. Esta
        prueba ataca directamente el campo que SI se toca (cliente/jefe_obra)
        con '' y con None, que es lo que la guarda distingue."""
        ficha = fixtures.ficha_minima()
        ficha['identidad']['cliente'] = 'NEINOR (ya confirmado)'
        ficha['identidad']['jefe_obra'] = 'Bixente'
        cambiados = ficha_obra.volcar_apartados(ficha, ficha_xlsx={
            '_disponible': True,
            'datos': {'Cliente': '', 'Responsable': None},
            'personal': [], 'hitos': [], 'riesgos': [], 'plan': [],
        })
        self.assertEqual(ficha['identidad']['cliente'], 'NEINOR (ya confirmado)')
        self.assertEqual(ficha['identidad']['jefe_obra'], 'Bixente')
        self.assertNotIn('identidad', cambiados)

    def test_contactos_no_se_vacian_si_el_xlsx_no_trae_personal(self):
        """Mismo principio que identidad, aplicado a la lista de contactos:
        un Personal en blanco en el xlsx no debe borrar los contactos que
        ya se conocian."""
        ficha = fixtures.ficha_minima()
        ficha['contactos'] = [{'Nombre': 'Bixente', 'Rol': 'Jefe de obra'}]
        cambiados = ficha_obra.volcar_apartados(ficha, ficha_xlsx={
            '_disponible': True, 'datos': {}, 'personal': [],
            'hitos': [], 'riesgos': [], 'plan': [],
        })
        self.assertEqual(ficha['contactos'],
                         [{'Nombre': 'Bixente', 'Rol': 'Jefe de obra'}])
        self.assertNotIn('contactos', cambiados)

    def test_materiales_no_se_vacian_si_la_lectura_no_trae_items(self):
        """Hallazgo de la ronda de correccion 1: a diferencia de identidad,
        contactos y documentos, la rama de materiales solo comprobaba
        `disponible` (el fichero existe) pero no si la lectura trajo algun
        item. Una lectura degradada (p.ej. no se localiza la columna TOTAL)
        deja 'items': [] con 'disponible': True, y sin esta guarda
        pisaria en silencio un resumen bueno con uno vacio."""
        ficha = fixtures.ficha_minima()
        ficha['materiales'] = {
            'ultimo_mes': 'Junio26', 'ultima_fecha': '15/06/2026',
            'dias_desde': 3, 'meses': ['Mayo26', 'Junio26'],
            'n_items': 50, 'aviso': None,
            '_meta': {'actualizado': '15/06/2026 10:00'},
        }
        cambiados = ficha_obra.volcar_apartados(ficha, materiales={
            'disponible': True, 'meses': ['Mayo26', 'Junio26', 'Julio26'],
            'ultimo_mes': 'Julio26', 'ultima_fecha': None, 'dias_desde': None,
            'aviso': "No se localizó la columna TOTAL en la hoja; se muestra "
                     "solo la referencia al archivo.",
            'items': [],
        })
        self.assertEqual(ficha['materiales']['n_items'], 50)
        self.assertEqual(ficha['materiales']['ultimo_mes'], 'Junio26')
        self.assertNotIn('materiales', cambiados)

    def test_documentos_no_se_vacian_si_la_lista_viene_vacia(self):
        """Mismo principio en documentos: una carpeta que por lo que sea se
        recorre vacia (fallo de lectura, ruta temporalmente inaccesible) no
        debe borrar el recuento que ya se tenia."""
        ficha = fixtures.ficha_minima()
        ficha['documentos'] = {'total': 3, 'por_categoria': {'Planos': 2, 'Otros': 1},
                               '_meta': {'actualizado': '20/07/2026 10:00'}}
        cambiados = ficha_obra.volcar_apartados(ficha, documentos=[])
        self.assertEqual(ficha['documentos']['total'], 3)
        self.assertNotIn('documentos', cambiados)


class TestActualizarDesdeSnapshot(unittest.TestCase):

    def test_un_snapshot_crudo_actualiza_los_estados(self):
        ficha = fixtures.ficha_minima()
        snapshot = [{'task': 'Tubeado', 'floor': 'PB', 'building': 'P1',
                     'unit': 'A', 'status': 'X'}]
        ficha, cambios = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['f'], '27/07/2026')

    def test_la_casilla_vacia_del_snapshot_se_guarda_como_pendiente(self):
        ficha = fixtures.ficha_minima()
        snapshot = [{'task': 'Tubeado', 'floor': 'PB', 'building': 'P1',
                     'unit': 'A', 'status': ''}]
        ficha, _ = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026')
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'P')

    def test_reclama_las_correcciones_manuales(self):
        ficha = fixtures.ficha_minima()
        snapshot = [{'task': 'Tubeado', 'floor': 'PB', 'building': 'P1',
                     'unit': 'A', 'status': ''}]
        ficha, cambios = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026',
            correcciones={'p1__pb__tubeado__A': 'X'})
        self.assertEqual(ficha['estados']['p1__pb__tubeado__A']['v'], 'X')
        self.assertEqual(len(cambios['correcciones_reclamadas']), 1)

    def test_una_ubicacion_desconocida_entra_sin_confirmar_y_avisa(self):
        ficha = fixtures.ficha_minima()
        snapshot = [{'task': 'Tubeado', 'floor': 'PB', 'building': 'P1',
                     'unit': 'C', 'status': 'X'}]
        ficha, cambios = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026')
        self.assertTrue(any('unidad C' in a for a in cambios['ubicaciones_nuevas']))

    def test_registra_la_revision(self):
        ficha = fixtures.ficha_minima()
        snapshot = [{'task': 'Tubeado', 'floor': 'PB', 'building': 'P1',
                     'unit': 'A', 'status': 'X'}]
        ficha, cambios = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026')
        self.assertEqual(cambios['revision_registrada'], 'rev_27072026')

    def test_resuelve_un_alias_del_catalogo(self):
        """Un nombre que sea alias en el catálogo debe resolver al id correcto,
        no crear un tajo nuevo. Mungia emite "Rozas timbres" (alias) pero la
        ficha guarda "Rozas de timbres" (nombre largo). Sin este mapeo se
        duplicarían tajos en silencio."""
        ficha = fixtures.ficha_minima()
        # Añadir el tajo "Rozas de timbres" (nombre largo del catálogo) a la ficha
        ficha['tajos']['detalle'].append({
            'id': 'rozas_timbres', 'nombre': 'Rozas de timbres',
            'ambito': 'vivienda', 'propiedad': 'propio', 'fase': 'Inicio de obra',
            'orden': 20})
        ficha['tajos']['aplicables'].append('rozas_timbres')
        # Snapshot con el alias "Rozas timbres" del catálogo (no el nombre largo)
        snapshot = [{'task': 'Rozas timbres', 'floor': 'PB', 'building': 'P1',
                     'unit': 'A', 'status': 'X'}]
        ficha, cambios = ficha_obra.actualizar_desde_snapshot(
            ficha, snapshot, '27/07/2026')
        # El alias debe haber sido resuelto a su id (rozas_timbres) que ya existe
        # en la ficha: no debe haber tajos nuevos
        self.assertEqual(len(cambios['tajos_nuevos']), 0)
        # Verificar que la celda se escribió bajo el id correcto (no bajo un id nuevo)
        self.assertIn('p1__pb__rozas_timbres__A', ficha['estados'])


class TestSnapshotDesdeFicha(unittest.TestCase):

    def _ficha_con_estados(self, valores):
        """valores: {clave_celda: estado}. Devuelve una ficha con esos
        estados y el resto de la matriz en '?'."""
        ficha = fixtures.ficha_minima()
        ficha, _ = ficha_obra.actualizar(
            ficha, fixtures.prioridades([fixtures.item(estado='X')]))
        for clave, valor in valores.items():
            ficha['estados'][clave] = {'v': valor, 'f': '27/07/2026',
                                       'r': 'rev_27072026'}
        return ficha

    def test_devuelve_las_claves_que_espera_el_motor(self):
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': 'X'})
        fila = next(r for r in ficha_obra.snapshot_desde_ficha(ficha)
                    if r['unit'] == 'A' and r['task'] == 'Tubeado'
                    and r['floor'] == 'PB')
        self.assertEqual(set(fila), {'task', 'floor', 'building', 'unit', 'status'})
        self.assertEqual(fila['building'], 'P1')
        self.assertEqual(fila['status'], 'X')

    def test_pendiente_confirmado_viaja_como_vacio(self):
        """P entra en el denominador: se comprobo y no esta hecho."""
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': 'P'})
        fila = next(r for r in ficha_obra.snapshot_desde_ficha(ficha)
                    if r['unit'] == 'A' and r['task'] == 'Tubeado'
                    and r['floor'] == 'PB')
        self.assertEqual(fila['status'], '')

    def test_desconocido_se_excluye_del_snapshot(self):
        """? no puede contar como pendiente: seria afirmar lo que no consta."""
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': '?'})
        filas = [r for r in ficha_obra.snapshot_desde_ficha(ficha)
                 if r['unit'] == 'A' and r['task'] == 'Tubeado'
                 and r['floor'] == 'PB']
        self.assertEqual(filas, [])

    def test_no_aplica_se_excluye_del_snapshot(self):
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': 'N'})
        filas = [r for r in ficha_obra.snapshot_desde_ficha(ficha)
                 if r['unit'] == 'A' and r['task'] == 'Tubeado'
                 and r['floor'] == 'PB']
        self.assertEqual(filas, [])

    def test_usa_el_nombre_historico_de_la_unidad_si_existe(self):
        """En Mungia el id canonico es 'A' pero la hoja dice 'A2'."""
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': 'X'})
        ficha['estructura']['alias_historico'] = {'p1__pb__A': 'A2'}
        unidades = {r['unit'] for r in ficha_obra.snapshot_desde_ficha(ficha)
                    if r['floor'] == 'PB'}
        self.assertIn('A2', unidades)
        self.assertNotIn('A', unidades)

    def test_devuelve_el_nombre_del_tajo_no_su_id(self):
        ficha = self._ficha_con_estados({'p1__pb__tubeado__A': 'X'})
        tareas = {r['task'] for r in ficha_obra.snapshot_desde_ficha(ficha)}
        self.assertIn('Tubeado', tareas)
        self.assertNotIn('tubeado', tareas)

    def test_una_ficha_sin_estados_devuelve_lista_vacia(self):
        ficha = fixtures.ficha_minima()
        self.assertEqual(ficha_obra.snapshot_desde_ficha(ficha), [])


class TestOrdenRevisiones(unittest.TestCase):

    def test_fechas_malformadas_no_colapsan_y_avisan(self):
        revisiones = [
            {'id': 'rev_z', 'fecha': 'sin fecha Z'},
            {'id': 'rev_a', 'fecha': 'sin fecha A'},
            {'id': 'rev_ok', 'fecha': '27/07/2026'},
        ]
        salida = io.StringIO()
        with redirect_stdout(salida):
            ficha_obra._ordenar_revisiones(revisiones)
        self.assertEqual(
            [r['id'] for r in revisiones],
            ['rev_a', 'rev_z', 'rev_ok'],
        )
        self.assertIn('[AVISO FICHA]', salida.getvalue())
        self.assertIn('sin fecha A', salida.getvalue())
        self.assertNotEqual(
            ficha_obra._orden_fecha('sin fecha A'),
            ficha_obra._orden_fecha('sin fecha Z'),
        )

    def test_fechas_duplicadas_avisan_y_se_ordenan_por_id(self):
        revisiones = [
            {'id': 'rev_b', 'fecha': '27/07/2026'},
            {'id': 'rev_a', 'fecha': '27/07/2026'},
        ]
        salida = io.StringIO()
        with redirect_stdout(salida):
            ficha_obra._ordenar_revisiones(revisiones)
        self.assertEqual([r['id'] for r in revisiones], ['rev_a', 'rev_b'])
        self.assertIn('[AVISO FICHA]', salida.getvalue())
        self.assertIn('duplicada', salida.getvalue())


class TestAlfabetoDeEstados(unittest.TestCase):
    """El alfabeto que documenta el CLAUDE.md tiene que entrar entero.

    Hasta el 05/08/2026 `MAPA_ESTADO` aceptaba '' y 'pendiente' pero NO la
    letra 'P', que es justamente la canonica. Un sidecar escrito con el
    alfabeto de la casa se degradaba a '?' -- avisaba, pero se degradaba, y
    'P' (comprobado, no esta hecho) y '?' (nadie lo ha mirado) son distintos
    a proposito. Lo destapo el lector de hojas marcadas, que escribe 'P'.
    """

    def test_las_letras_del_alfabeto_se_reconocen_todas(self):
        for letra, esperado in [('X', 'X'), ('M', 'M'), ('/', '/'),
                                ('P', 'P'), ('N', 'N')]:
            with self.subTest(letra):
                clave = ficha_obra._normalizar_estado(letra)
                self.assertIn(clave, ficha_obra.MAPA_ESTADO)
                self.assertEqual(ficha_obra.MAPA_ESTADO[clave], esperado)

    def test_la_casilla_vacia_sigue_siendo_pendiente(self):
        """Los sidecars antiguos escriben '' donde el alfabeto escribe 'P'.
        Las dos formas tienen que seguir significando lo mismo."""
        self.assertEqual(
            ficha_obra.MAPA_ESTADO[ficha_obra._normalizar_estado('')],
            ficha_obra.MAPA_ESTADO[ficha_obra._normalizar_estado('P')])


if __name__ == '__main__':
    unittest.main()
