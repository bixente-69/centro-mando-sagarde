# -*- coding: utf-8 -*-
"""Prioridades leyendo de la base de obra en vez del historial crudo.

La base ya es el estado resuelto: trae la norma de la ultima revision
aplicada, la fecha y la revision de origen de cada celda, y las ubicaciones
descartadas fuera del arbol de estructura. Reconstruirlo desde el historial
crudo es lo que metia 4 viviendas inexistentes en Bolueta y 15 en Orueta.
"""
import os
import sys
import unittest
from datetime import date

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import fixtures
from priorizador_trabajos import (Catalogo, _agrupar_inventario,
                                  _agrupar_prioridades, _clasificar_detalle,
                                  _scope, estado_desde_ficha, priorizar_ficha,
                                  sembrar_reglas, sin_base, verificar_rejilla)


def _item(ambito, planta, unidad, tarea='cuarto_tecnico', edificio='P1',
          categoria='VIABLE'):
    """Una celda de detalle con la forma que produce _clasificar_detalle."""
    return {
        'tarea_id': tarea, 'trabajo': tarea.replace('_', ' ').capitalize(),
        'trabajos_originales': [], 'propiedad': 'propio', 'ambito': ambito,
        'ambito_nombre': 'x', 'orden_ejecucion': 235, 'fase_nombre': 'F',
        'display_group': tarea, 'edificio': edificio, 'planta': planta,
        'unidad': unidad, 'estado': '', 'estado_actual': 'Pendiente',
        'categoria': categoria, 'motivo': 'Viable.',
        'dependencias_cumplidas': [], 'dependencias_bloqueantes': [],
        'dependencias_sin_dato': [], 'omitido_ultima': False,
        'forzado_entregado': False, 'ultima_fecha': '28/07/2026',
    }


def _ficha_con_estados(pares, tajos_extra=()):
    """pares: {(planta_id, tajo_id, ubicacion_id): estado}

    No se toca fixtures.ficha_minima(): test_ficha_obra comprueba que produce
    exactamente 8 celdas. Los tajos que hagan falta de mas se anaden aqui.
    """
    ficha = fixtures.ficha_minima()
    ficha['revisiones'] = [{'id': 'rev_28072026', 'fecha': '28/07/2026'}]
    for tajo in tajos_extra:
        ficha['tajos']['detalle'].insert(0, dict(tajo))
        ficha['tajos']['aplicables'].insert(0, tajo['id'])
    for (planta, tajo, ubi), valor in pares.items():
        clave = 'p1__%s__%s__%s' % (planta, tajo, ubi)
        ficha['estados'][clave] = {'v': valor, 'f': '28/07/2026',
                                   'r': 'rev_28072026'}
    return ficha


TABICADO = {'id': 'tabicado', 'nombre': 'Tabicado', 'ambito': 'vivienda',
            'propiedad': 'externo', 'fase': 'Inicio de obra', 'orden': 5}


class TestEstadoDesdeFicha(unittest.TestCase):

    def test_traduce_los_estados_medidos(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'X',
            ('pb', 'tubeado', 'B'): 'M',
            ('1', 'tubeado', 'A'): '/',
            ('1', 'tubeado', 'B'): 'P',
        })
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(estados[(('P1', 'PB', 'A'), 'tubeado')]['estado'], 'X')
        self.assertEqual(estados[(('P1', 'PB', 'B'), 'tubeado')]['estado'], 'M')
        self.assertEqual(estados[(('P1', '1', 'A'), 'tubeado')]['estado'], '/')
        self.assertEqual(estados[(('P1', '1', 'B'), 'tubeado')]['estado'], '')

    def test_conserva_el_estado_crudo_de_la_base(self):
        """'P', '?' y 'N' valen todos '' para el motor, pero significan cosas
        distintas y la clasificacion los tiene que poder separar."""
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): '?',
            ('pb', 'tubeado', 'B'): 'N',
            ('1', 'tubeado', 'A'): 'P',
        })
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(
            estados[(('P1', 'PB', 'A'), 'tubeado')]['estado_base'], '?')
        self.assertEqual(
            estados[(('P1', 'PB', 'B'), 'tubeado')]['estado_base'], 'N')
        self.assertEqual(
            estados[(('P1', '1', 'A'), 'tubeado')]['estado_base'], 'P')
        for loc in (('P1', 'PB', 'A'), ('P1', 'PB', 'B'), ('P1', '1', 'A')):
            self.assertEqual(estados[(loc, 'tubeado')]['estado'], '')

    def test_una_ubicacion_fuera_del_arbol_no_aparece(self):
        """Las excluidas no estan en estructura.bloques: recorrer el arbol es,
        por si solo, respetar estructura.exclusiones. Es el caso de las 4
        viviendas fantasma de PB en Bolueta y las 15 de Orueta."""
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        ficha['estados']['p1__pb__tubeado__FANTASMA'] = {
            'v': 'X', 'f': '28/07/2026', 'r': 'rev_28072026'}
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        unidades = {loc[2] for loc, _tid in estados}
        self.assertNotIn('FANTASMA', unidades)

    def test_conserva_la_fecha_y_la_revision_de_cada_celda(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        celda = estados[(('P1', 'PB', 'A'), 'tubeado')]
        self.assertEqual(celda['ultima_fecha'], '28/07/2026')

    def test_la_fecha_es_la_de_la_ultima_revision_registrada(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        ficha['revisiones'] = [
            {'id': 'rev_26072026', 'fecha': '26/07/2026'},
            {'id': 'rev_28072026', 'fecha': '28/07/2026'},
        ]
        _estados, fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(fecha, '28/07/2026')

    def test_la_fecha_no_depende_del_orden_de_la_lista(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        ficha['revisiones'] = [
            {'id': 'rev_28072026', 'fecha': '28/07/2026'},
            {'id': 'rev_26072026', 'fecha': '26/07/2026'},
        ]
        _estados, fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(fecha, '28/07/2026')

    def test_una_base_sin_celdas_no_revienta(self):
        ficha = fixtures.ficha_minima()
        estados, fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(estados, {})
        self.assertIsNone(fecha)

    def test_el_id_de_la_base_manda_si_el_catalogo_lo_conoce(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        celda = estados[(('P1', 'PB', 'A'), 'tubeado')]
        self.assertFalse(celda['desconocido'])
        self.assertEqual(celda['meta']['id'], 'tubeado')


class TestDesconocidoYNoAplica(unittest.TestCase):
    """'P', '?' y 'N' valen todos '' para el motor y significan cosas
    distintas. Confundirlos es la causa de casi todo lo que ha fallado aqui."""

    def _clasificar(self, pares, tajos_extra=()):
        ficha = _ficha_con_estados(pares, tajos_extra=tajos_extra)
        catalogo = Catalogo()
        estados, fecha = estado_desde_ficha(ficha, catalogo)
        detalle, _edad, _cad = _clasificar_detalle(estados, catalogo, fecha, {})
        return detalle

    def test_no_aplica_no_entra_en_el_calculo(self):
        detalle = self._clasificar({('pb', 'tubeado', 'A'): 'N'})
        self.assertEqual(detalle, [])

    def test_nunca_revisado_tiene_categoria_propia(self):
        detalle = self._clasificar({('pb', 'tubeado', 'A'): '?'})
        self.assertEqual(len(detalle), 1)
        self.assertEqual(detalle[0]['categoria'], 'SIN_REVISAR')

    def test_nunca_revisado_no_se_confunde_con_pendiente(self):
        detalle = self._clasificar({
            ('pb', 'tubeado', 'A'): '?',
            ('pb', 'tubeado', 'B'): 'P',
        })
        por_unidad = {d['unidad']: d['categoria'] for d in detalle}
        self.assertEqual(por_unidad['A'], 'SIN_REVISAR')
        self.assertNotEqual(por_unidad['B'], 'SIN_REVISAR')

    def test_nunca_revisado_gana_a_la_propiedad_del_tajo(self):
        """Un tajo de otro gremio que nadie ha mirado es 'sin revisar', no
        'otros gremios': la accion sigue siendo ir a mirarlo."""
        detalle = self._clasificar({('pb', 'tabicado', 'A'): '?'},
                                   tajos_extra=[TABICADO])
        self.assertEqual(detalle[0]['categoria'], 'SIN_REVISAR')

    def test_un_grupo_entero_sin_mirar_va_a_su_seccion(self):
        detalle = self._clasificar({
            ('pb', 'tabicado', 'A'): '?',
            ('pb', 'tabicado', 'B'): '?',
        }, tajos_extra=[TABICADO])
        inventario = _agrupar_inventario(detalle)
        self.assertEqual(inventario[0]['seccion'], 'SIN_REVISAR')
        self.assertEqual(inventario[0]['seccion_nombre'], 'Sin revisar nunca')

    def test_un_grupo_mezclado_no_se_va_a_sin_revisar(self):
        detalle = self._clasificar({
            ('pb', 'tabicado', 'A'): '?',
            ('pb', 'tabicado', 'B'): 'X',
        }, tajos_extra=[TABICADO])
        inventario = _agrupar_inventario(detalle)
        self.assertNotEqual(inventario[0]['seccion'], 'SIN_REVISAR')


class TestConteoPorAmbito(unittest.TestCase):
    """Hay UN cuarto tecnico en Bolueta, no 92. La hoja repite cada tajo en
    todas las ubicaciones, tambien los que son unicos del edificio."""

    def _grupos(self, ambito, tarea):
        detalle = [_item(ambito, p, u, tarea)
                   for p in ('PB', '1', '2') for u in ('A', 'B')]
        return _agrupar_prioridades(detalle)

    def test_un_tajo_de_edificio_cuenta_una_sola_unidad(self):
        grupos = self._grupos('edificio', 'cuarto_tecnico')
        self.assertEqual(len(grupos), 1)
        self.assertEqual(grupos[0]['n_unidades'], 1)
        self.assertEqual(grupos[0]['n_celdas'], 6)

    def test_un_tajo_de_zona_comun_cuenta_una_por_planta(self):
        grupos = self._grupos('zona_comun', 'tubeado_zzcc')
        self.assertEqual(grupos[0]['n_unidades'], 3)
        self.assertEqual(grupos[0]['n_celdas'], 6)

    def test_un_tajo_de_vivienda_cuenta_una_por_vivienda(self):
        grupos = self._grupos('vivienda', 'tubeado')
        self.assertEqual(grupos[0]['n_unidades'], 6)
        self.assertEqual(grupos[0]['n_celdas'], 6)

    def test_dos_portales_no_colapsan_en_uno(self):
        detalle = [_item('zona_comun', 'PB', 'A', 'tubeado_zzcc', edificio=e)
                   for e in ('PORTAL 1', 'PORTAL 2')]
        grupos = _agrupar_prioridades(detalle)
        self.assertEqual(grupos[0]['n_unidades'], 2)

    def test_el_recorte_se_puede_pedir_aparte(self):
        detalle = [_item('vivienda', 'PB', 'A', 'tajo_%d' % i)
                   for i in range(260)]
        grupos, recortados = _agrupar_prioridades(detalle, limite=200,
                                                  con_recorte=True)
        self.assertEqual(len(grupos), 200)
        self.assertEqual(recortados, 60)


class TestSembrarReglas(unittest.TestCase):
    """El catalogo manda sobre orden y dependencias; la base guarda el estado.
    Lo que el catalogo no conoce NO recibe orden inventado: sale como
    pregunta, porque el catalogo es SIEMPRE AMPLIABLE."""

    def _ficha(self, detalle):
        ficha = fixtures.ficha_minima()
        ficha['tajos']['detalle'] = detalle
        return ficha

    def test_el_catalogo_manda_sobre_el_orden(self):
        ficha = self._ficha([
            {'id': 'tubeado', 'nombre': 'Tubeado interior', 'orden': 9999}])
        sembrar_reglas(ficha, Catalogo())
        self.assertEqual(ficha['tajos']['detalle'][0]['orden'], 130)

    def test_siembra_propiedad_ambito_fase_y_deps(self):
        ficha = self._ficha([
            {'id': 'cableado', 'nombre': 'Cableado eléctrico', 'orden': 9999}])
        sembrar_reglas(ficha, Catalogo())
        tajo = ficha['tajos']['detalle'][0]
        self.assertEqual(tajo['propiedad'], 'propio')
        self.assertEqual(tajo['ambito'], 'vivienda')
        self.assertEqual(tajo['fase'], 'Instalación interior')
        self.assertEqual([d['id'] for d in tajo['deps']], ['tubeado'])

    def test_un_tajo_que_el_catalogo_no_conoce_sale_como_pregunta(self):
        ficha = self._ficha([
            {'id': 'placas_tps_cuadro', 'nombre': 'Placas tapas cuadro',
             'orden': 9999}])
        preguntas = sembrar_reglas(ficha, Catalogo())
        self.assertIn('TAJO_FUERA_DEL_CATALOGO',
                      {p['codigo'] for p in preguntas})

    def test_nunca_se_inventa_un_orden(self):
        ficha = self._ficha([
            {'id': 'inventado_xyz', 'nombre': 'Inventado', 'orden': 9999}])
        sembrar_reglas(ficha, Catalogo())
        self.assertEqual(ficha['tajos']['detalle'][0]['orden'], 9999)

    def test_la_pregunta_sugiere_ids_parecidos(self):
        """focos_hab en la base, focos_habitaciones en el catalogo: la deriva
        de nombre que dejo 18 tajos de Orueta en 9999."""
        ficha = self._ficha([
            {'id': 'focos_hab', 'nombre': 'Zzz sin alias', 'orden': 9999}])
        preguntas = sembrar_reglas(
            ficha, Catalogo('2025 BILBAO OBISPO ORUETA'))
        self.assertIn('focos_habitaciones', preguntas[0]['parecidos'])

    def test_resuelve_por_nombre_cuando_el_id_no_esta(self):
        ficha = self._ficha([
            {'id': 'id_raro', 'nombre': 'Tubeado interior', 'orden': 9999}])
        preguntas = sembrar_reglas(ficha, Catalogo())
        self.assertEqual(ficha['tajos']['detalle'][0]['orden'], 130)
        self.assertNotIn('TAJO_FUERA_DEL_CATALOGO',
                         {p['codigo'] for p in preguntas})

    def test_dos_filas_que_caen_en_el_mismo_tajo_se_avisan(self):
        """En Orueta, placas_tps_cuadro resuelve por alias a placas_tapas, que
        ya existe en la base. No se fusionan solas: se pregunta."""
        ficha = self._ficha([
            {'id': 'placas_tapas', 'nombre': 'Placas y tapas', 'orden': 9999},
            {'id': 'placas_tps_cuadro', 'nombre': 'Placas y tapas',
             'orden': 9999},
        ])
        preguntas = sembrar_reglas(ficha, Catalogo())
        dup = [p for p in preguntas
               if p['codigo'] == 'TAJO_DUPLICADO_EN_LA_BASE']
        self.assertEqual(len(dup), 1)
        self.assertEqual(dup[0]['parecidos'],
                         ['placas_tapas', 'placas_tps_cuadro'])

    def test_una_dependencia_que_existe_con_otro_id_no_se_avisa(self):
        """Orueta guarda 'pintura_hab' y el catalogo dice
        'pintura_habitaciones'. Comparar los ids en crudo daba 3 falsas
        alarmas de 4."""
        ficha = self._ficha([
            {'id': 'tabicado_viejo', 'nombre': 'Tabicado', 'orden': 9999},
            {'id': 'tubeado', 'nombre': 'Tubeado interior', 'orden': 9999},
        ])
        preguntas = sembrar_reglas(ficha, Catalogo())
        por_tubeado = [p for p in preguntas
                       if p['codigo'] == 'DEPENDENCIA_AUSENTE_EN_LA_OBRA'
                       and p['tarea_id'] == 'tubeado']
        self.assertEqual(por_tubeado, [])

    def test_sin_duplicados_no_hay_aviso(self):
        ficha = self._ficha([
            {'id': 'tubeado', 'nombre': 'Tubeado interior', 'orden': 9999},
            {'id': 'cableado', 'nombre': 'Cableado eléctrico', 'orden': 9999},
        ])
        preguntas = sembrar_reglas(ficha, Catalogo())
        self.assertNotIn('TAJO_DUPLICADO_EN_LA_BASE',
                         {p['codigo'] for p in preguntas})

    def test_una_dependencia_que_la_obra_no_tiene_se_avisa(self):
        """Hoy vale 0 y bloquea para siempre en silencio."""
        ficha = self._ficha([
            {'id': 'cableado', 'nombre': 'Cableado eléctrico', 'orden': 9999}])
        preguntas = sembrar_reglas(ficha, Catalogo())
        avisos = [p for p in preguntas
                  if p['codigo'] == 'DEPENDENCIA_AUSENTE_EN_LA_OBRA']
        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0]['tarea_id'], 'cableado')
        self.assertIn('tubeado', avisos[0]['parecidos'])

    def test_si_la_dependencia_esta_en_la_obra_no_se_avisa(self):
        """cableado depende de tubeado y tubeado SI esta: no hay aviso por
        cableado. Que lo haya por tubeado (depende de tabicado, que no esta)
        es justo lo que se quiere: cada tajo responde de sus propias deps."""
        ficha = self._ficha([
            {'id': 'tubeado', 'nombre': 'Tubeado interior', 'orden': 9999},
            {'id': 'cableado', 'nombre': 'Cableado eléctrico', 'orden': 9999},
        ])
        preguntas = sembrar_reglas(ficha, Catalogo())
        por_cableado = [p for p in preguntas
                        if p['codigo'] == 'DEPENDENCIA_AUSENTE_EN_LA_OBRA'
                        and p['tarea_id'] == 'cableado']
        self.assertEqual(por_cableado, [])
        por_tubeado = [p for p in preguntas
                       if p['codigo'] == 'DEPENDENCIA_AUSENTE_EN_LA_OBRA'
                       and p['tarea_id'] == 'tubeado']
        self.assertEqual(por_tubeado[0]['parecidos'], ['tabicado'])


class TestAntiguedadEsAviso(unittest.TestCase):
    """A los 30 dias el motor volcaba TODA la obra a DUDAS de golpe, y con la
    fecha de generacion dentro del calculo el mismo dato daba paneles
    distintos segun cuando se lanzara."""

    def _clasificar(self, fecha_revision, hoy):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'P'})
        ficha['revisiones'] = [{'id': 'r', 'fecha': fecha_revision}]
        catalogo = Catalogo()
        estados, fecha = estado_desde_ficha(ficha, catalogo)
        return _clasificar_detalle(estados, catalogo, fecha, {}, hoy=hoy)

    def test_una_revision_vieja_ya_no_tumba_la_clasificacion(self):
        detalle, edad, caducada = self._clasificar('01/01/2026',
                                                   date(2026, 8, 11))
        self.assertEqual(edad, 222)
        self.assertTrue(caducada)
        self.assertNotEqual(detalle[0]['categoria'], 'DUDAS')

    def test_el_resultado_no_depende_del_dia_en_que_se_genera(self):
        d1, _e, _c = self._clasificar('01/07/2026', date(2026, 7, 20))
        d2, _e, _c = self._clasificar('01/07/2026', date(2026, 12, 31))
        self.assertEqual([x['categoria'] for x in d1],
                         [x['categoria'] for x in d2])

    def test_la_edad_se_calcula_contra_la_fecha_que_se_pasa(self):
        _d, edad, caducada = self._clasificar('01/08/2026', date(2026, 8, 11))
        self.assertEqual(edad, 10)
        self.assertFalse(caducada)


class TestPuntoDeEntrada(unittest.TestCase):

    def test_una_obra_sin_base_no_calcula_nada(self):
        resultado = sin_base('2026 GORLIZ HOSPITAL')
        self.assertIs(resultado['sin_base'], True)
        self.assertEqual(resultado['resumen']['inventario_total'], 0)
        self.assertIn('no tiene base de datos', resultado['avisos'][0])

    def test_priorizar_ficha_devuelve_la_forma_de_siempre(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        for clave in ('version', 'catalogo_version', 'revision', 'resumen',
                      'items', 'detalle_items', 'inventario',
                      'dudas_pendientes', 'preguntas_orden', 'avisos',
                      'historial_confirmado_terminado'):
            self.assertIn(clave, resultado)

    def test_cableado_es_viable_con_el_tubeado_terminado(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'X',
            ('pb', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        cableado = [d for d in resultado['detalle_items']
                    if d['tarea_id'] == 'cableado']
        self.assertEqual(cableado[0]['categoria'], 'VIABLE')

    def test_cableado_esta_bloqueado_sin_tubeado(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'P',
            ('pb', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        cableado = [d for d in resultado['detalle_items']
                    if d['tarea_id'] == 'cableado']
        self.assertEqual(cableado[0]['categoria'], 'BLOQUEADO')
        self.assertIn('Tubeado interior',
                      cableado[0]['dependencias_bloqueantes'])

    def test_una_base_vacia_cae_en_sin_base(self):
        resultado = priorizar_ficha(fixtures.ficha_minima())
        self.assertIs(resultado['sin_base'], True)

    def test_las_preguntas_de_orden_cuentan_en_el_resumen(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'P'})
        ficha['tajos']['detalle'].append(
            {'id': 'inventado_xyz', 'nombre': 'Inventado', 'orden': 9999})
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        self.assertGreater(resultado['resumen']['preguntas_pendientes'], 0)


class TestDependenciaNoDefinida(unittest.TestCase):
    """NORMA DE OBRA (12/08/2026): un tajo que no se definio en su momento no
    puede bloquear. Si hay marca en un tajo de escalafon superior, los
    anteriores estan hechos por fuerza."""

    def test_una_dependencia_que_la_obra_no_tiene_no_bloquea(self):
        """cableado depende de tubeado; si la obra no declara tubeado, el
        cableado no se queda bloqueado para siempre."""
        ficha = _ficha_con_estados({('pb', 'cableado', 'A'): 'P'})
        ficha['tajos']['detalle'] = [
            t for t in ficha['tajos']['detalle'] if t['id'] != 'tubeado']
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        cableado = [d for d in resultado['detalle_items']
                    if d['tarea_id'] == 'cableado'][0]
        self.assertEqual(cableado['categoria'], 'VIABLE')
        self.assertEqual(cableado['dependencias_bloqueantes'], [])

    def test_pero_sigue_saliendo_como_pregunta(self):
        """No bloquear no es callar: hay que poder definirlo."""
        ficha = _ficha_con_estados({('pb', 'cableado', 'A'): 'P'})
        ficha['tajos']['detalle'] = [
            t for t in ficha['tajos']['detalle'] if t['id'] != 'tubeado']
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        self.assertIn('DEPENDENCIA_AUSENTE_EN_LA_OBRA',
                      {p['codigo'] for p in resultado['preguntas_orden']})

    def test_una_dependencia_que_si_existe_sigue_bloqueando(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'P',
            ('pb', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        cableado = [d for d in resultado['detalle_items']
                    if d['tarea_id'] == 'cableado'][0]
        self.assertEqual(cableado['categoria'], 'BLOQUEADO')


class TestPrevision(unittest.TestCase):
    """Saber que acabar el suelo de tres plantas libera 40 viviendas de
    tubeado es lo que permite llevar el orden de una obra de meses."""

    def test_dice_cuantas_unidades_libera_cada_tajo(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'P', ('pb', 'cableado', 'A'): 'P',
            ('pb', 'tubeado', 'B'): 'P', ('pb', 'cableado', 'B'): 'P',
            ('1', 'tubeado', 'A'): 'X', ('1', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        por_tajo = {p['tarea_id']: p for p in resultado['prevision']}
        self.assertEqual(por_tajo['tubeado']['desbloquea'], 2)
        self.assertIn('Cableado eléctrico',
                      por_tajo['tubeado']['tajos_afectados'])

    def test_ordena_por_lo_que_mas_libera(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'P', ('pb', 'cableado', 'A'): 'P',
            ('pb', 'tubeado', 'B'): 'P', ('pb', 'cableado', 'B'): 'P',
            ('1', 'tubeado', 'A'): 'P', ('1', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        valores = [p['desbloquea'] for p in resultado['prevision']]
        self.assertEqual(valores, sorted(valores, reverse=True))

    def test_la_fila_bloqueada_dice_cuanto_falta(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'M', ('pb', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        cableado = [d for d in resultado['detalle_items']
                    if d['tarea_id'] == 'cableado'][0]
        dep = [x for x in cableado['dependencias_detalle']
               if x['id'] == 'tubeado'][0]
        self.assertEqual(dep['estado'], 'M')
        self.assertEqual(dep['minimo'], 1.0)
        self.assertFalse(dep['cumplida'])

    def test_una_dependencia_cumplida_no_aparece_en_la_prevision(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'X', ('pb', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        self.assertNotIn('tubeado',
                         {p['tarea_id'] for p in resultado['prevision']})

    def test_una_obra_sin_base_no_tiene_prevision(self):
        self.assertEqual(sin_base('X')['prevision'], [])


class TestCorreccionesMenores(unittest.TestCase):

    def test_zonas_comunes_en_plural_se_reconoce(self):
        """La guarda buscaba 'zona comun' y todo el catalogo escribe 'zonas
        comunes': esa mitad de la condicion no se cumplia nunca."""
        self.assertEqual(
            _scope({'ambito': 'vivienda'}, 'Tubeado de zonas comunes', 'A'),
            'zona_comun')

    def test_una_unidad_llamada_zonas_comunes_se_reconoce(self):
        """Orueta tiene unidades 'Zonas Comunes 1' y 'Zonas Comunes 2'."""
        self.assertEqual(
            _scope({'ambito': 'vivienda'}, 'Tubeado interior',
                   'Zonas Comunes 1'),
            'zona_comun')

    def test_zzcc_sigue_funcionando(self):
        self.assertEqual(
            _scope({'ambito': 'vivienda'}, 'Iluminación de rellanos / ZZCC',
                   'A'),
            'zona_comun')

    def test_una_vivienda_normal_no_se_convierte_en_zona_comun(self):
        self.assertEqual(
            _scope({'ambito': 'vivienda'}, 'Tubeado interior', 'A'),
            'vivienda')

    def test_el_recorte_avisa_en_la_salida(self):
        """El limite recortaba en silencio. Con tabicado terminado el tubeado
        es viable, asi que hay al menos un bloque que recortar."""
        ficha = _ficha_con_estados({
            ('pb', 'tabicado', 'A'): 'X',
            ('pb', 'tubeado', 'A'): 'P',
        }, tajos_extra=[TABICADO])
        completo = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        self.assertTrue(completo['items'])
        self.assertEqual([a for a in completo['avisos'] if 'recortado' in a],
                         [])

        ficha = _ficha_con_estados({
            ('pb', 'tabicado', 'A'): 'X',
            ('pb', 'tubeado', 'A'): 'P',
        }, tajos_extra=[TABICADO])
        recortado = priorizar_ficha(ficha, limite=0, hoy=date(2026, 8, 11))
        self.assertEqual(recortado['items'], [])
        self.assertEqual(
            len([a for a in recortado['avisos'] if 'recortado' in a]), 1)


class TestRejillaCompleta(unittest.TestCase):
    """La base tiene que ser una rejilla densa: ubicaciones x tajos. Si falta
    una celda, calcular sobre datos parciales es peor que avisar."""

    def _ficha_completa(self):
        pares = {(p, t, u): 'P'
                 for p in ('pb', '1') for u in ('A', 'B')
                 for t in ('tubeado', 'cableado')}
        return _ficha_con_estados(pares)

    def test_una_rejilla_completa_no_avisa(self):
        self.assertEqual(verificar_rejilla(self._ficha_completa()), [])

    def test_una_celda_que_falta_se_reporta_con_cifras(self):
        ficha = self._ficha_completa()
        del ficha['estados']['p1__pb__tubeado__A']
        avisos = verificar_rejilla(ficha)
        self.assertEqual(len(avisos), 1)
        self.assertIn('7', avisos[0])    # celdas encontradas
        self.assertIn('8', avisos[0])    # celdas esperadas

    def test_una_base_recien_creada_no_avisa(self):
        """Sin celdas no hay nada que comparar; el aviso lo da sin_base."""
        self.assertEqual(verificar_rejilla(fixtures.ficha_minima()), [])

    def test_dos_plantas_con_el_mismo_nombre_se_avisan(self):
        """La base las guarda separadas —la clave lleva el id— pero al
        priorizar se fusionan y una pisa a la otra."""
        ficha = self._ficha_completa()
        plantas = ficha['estructura']['bloques'][0]['portales'][0]['plantas']
        plantas[1]['nombre'] = plantas[0]['nombre']   # '1' pasa a llamarse 'PB'
        avisos = verificar_rejilla(ficha)
        self.assertEqual(len(avisos), 1)
        self.assertIn('se fusionan al priorizar', avisos[0])
        self.assertIn('4 ubicaciones declaradas', avisos[0])
        self.assertIn('2 distinguibles', avisos[0])

    def test_plantas_con_nombres_distintos_no_avisan(self):
        self.assertEqual(verificar_rejilla(self._ficha_completa()), [])


def _con_dos_bloques(ficha):
    """Anade un BLOQUE 2 con un portal que tambien se llama 'P1'."""
    import copy
    b1 = ficha['estructura']['bloques'][0]
    b2 = copy.deepcopy(b1)
    b2['id'], b2['nombre'] = 'b2', 'B2'
    b1['nombre'] = 'B1'
    b2['portales'][0]['id'] = 'p2'
    ficha['estructura']['bloques'].append(b2)
    for clave, valor in list(ficha['estados'].items()):
        ficha['estados']['p2' + clave[2:]] = dict(valor)
    return ficha


class TestBloqueEnLaUbicacion(unittest.TestCase):
    """NORMA DE OBRA (12/08/2026): dos portales pueden llamarse igual si estan
    en bloques distintos. Son el portal 1 de cada bloque y van a ritmos
    diferentes. En OBRA PRUEBA se perdian 5 de sus 31 ubicaciones."""

    def _ficha_dos_bloques(self):
        """Rejilla completa: 2 plantas x 2 viviendas x 2 tajos por bloque."""
        pares = {(p, t, u): 'P'
                 for p in ('pb', '1') for u in ('A', 'B')
                 for t in ('tubeado', 'cableado')}
        return _con_dos_bloques(_ficha_con_estados(pares))

    def test_dos_portales_homonimos_no_se_fusionan(self):
        estados, _f = estado_desde_ficha(self._ficha_dos_bloques(), Catalogo())
        edificios = {loc[0] for loc, _t in estados}
        self.assertEqual(edificios, {'B1 P1', 'B2 P1'})

    def test_no_se_pierde_ninguna_ubicacion(self):
        ficha = self._ficha_dos_bloques()
        self.assertEqual(verificar_rejilla(ficha), [])
        estados, _f = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(len({loc for loc, _t in estados}), 8)

    def test_una_obra_de_un_solo_bloque_no_cambia_de_etiqueta(self):
        """Las cuatro obras reales tienen un bloque: no se pueden mover."""
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        estados, _f = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual({loc[0] for loc, _t in estados}, {'P1'})


if __name__ == '__main__':
    unittest.main()
