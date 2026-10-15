# -*- coding: utf-8 -*-
"""Las zonas especiales (cuartos tecnicos, ligeros, cubierta) que la hoja
declara y la base no tiene SE DAN DE ALTA desde la hoja.

Caso real del 15/10/2026 (Olabeaga): Bixente creo en el generador
«CUADRO SEVICIOS GENERALES» y recreo «Cuarto RITI / Teleco» con otro id. El
lector saltaba a proposito toda planta ``zesp`` (``ampliar_estructura_desde_
hoja`` y ``estructura_nueva_en_hoja``), asi que sus 36 claves quedaban «sin
resolver», la estructura de la hoja no entraba en la base y la zona antigua no
podia retirarse (la baja exige que TODA clave de la hoja se resuelva). Es la
familia de fallo del proyecto: algo que la hoja declara y el motor ignora en
silencio.

La hoja SI declara lo que hace falta: ``data-zone-category`` (tipo) y el
nombre impreso (``<strong>`` de la tarjeta o cabecera de columna de la tabla).
"""
import copy
import os
import sys
import tempfile
import unittest


MOTOR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MOTOR)

import adaptar_revision_html as adaptador
import ficha_obra
import fixtures
import lector_hoja_tajos_html as lector

OBRAS = os.path.dirname(MOTOR)
HOJA_REAL_OLABEAGA = os.path.join(
    OBRAS, '2026 OLABEAGA BILBAO', 'REVISIONES',
    'REVISION 2026 OLABEAGA BILBAO 14102026.html')

PORTAL = 'src_pruebas_p1'


def _catalogo():
    return {
        'version': 'test',
        'tajos': [{'id': 'tubeado'}, {'id': 'cableado'},
                  {'id': 'montante_electrica'}],
        'obras': {},
    }


def _residencial():
    """Una celda por vivienda de la ficha minima: la hoja imprime las 4."""
    return ''.join(
        '<td class="td-st" data-k="{}__{}__tubeado__{}" data-st=""></td>'.format(
            PORTAL, planta, unidad)
        for planta in ('src_pruebas_p1_f1', 'src_pruebas_p1_f2')
        for unidad in ('A', 'B'))


def _celda(zona_id, tajo, estado='', portal=PORTAL):
    return ('<span class="td-st pend tecnico-state" '
            'data-k="{}__zesp__{}__{}" data-st="{}"></span>'.format(
                portal, tajo, zona_id, estado))


def _tarjeta(tipo, nombre, zona_id, tajos=('tubeado', 'cableado'),
             estado='', categoria=True):
    atributo = ' data-zone-category="{}"'.format(tipo) if categoria else ''
    checks = ''.join(
        '<div class="tecnico-check">{}<span>{}</span></div>'.format(
            _celda(zona_id, tajo, estado), tajo)
        for tajo in tajos)
    return ('<div class="tecnico-card"{}><div class="tecnico-card-head">'
            '<strong>{}</strong><span>Bloque 1 · PORTAL 1</span></div>'
            '{}</div>'.format(atributo, nombre, checks))


def _bloque_tabla(tipo, zonas, tajos=('tubeado', 'cableado')):
    """Maqueta de tabla (la que usan los cuartos ligeros): una columna por
    zona, el nombre en ``th.th-floor``."""
    cabeceras = ''.join(
        '<th class="th-floor">{}</th>'.format(nombre) for _id, nombre in zonas)
    filas = ''.join(
        '<tr class="tr-tajo"><td class="td-name">{}</td>{}</tr>'.format(
            tajo,
            ''.join('<td class="special-zone-state-cell">{}</td>'.format(
                _celda(zona_id, tajo)) for zona_id, _n in zonas))
        for tajo in tajos)
    return (
        '<div class="planta-block special-zone-table-block" '
        'data-zone-category="{}"><div class="tbl-wrap"><table class="rev-table">'
        '<thead><tr class="tr-ident"><th class="th-ident" colspan="3">'
        'OBRA · Bloque 1 · PORTAL 1 · {}</th></tr>'
        '<tr><th class="th-floor th-floor-tajo">TAJO</th>{}</tr></thead>'
        '<tbody>{}</tbody></table></div></div>'.format(
            tipo, tipo, cabeceras, filas))


def _hoja(*bloques_zona):
    return (
        '<html><body><table class="rev-table"><tbody><tr>{}</tr></tbody></table>'
        '<section class="garage-section special-zone-section">'
        '<section class="hoja-section"><div class="garage-section-title">'
        'Zonas</div><div class="tecnico-grid">{}</div></section></section>'
        '</body></html>'.format(_residencial(), ''.join(bloques_zona)))


def _ficha_con_zona_antigua(estado='?'):
    ficha = fixtures.ficha_minima()
    portal = ficha['estructura']['bloques'][0]['portales'][0]
    portal['plantas'].append({
        'id': 'zesp', 'nombre': 'Zonas especiales', 'orden': 999,
        'ubicaciones': [{'id': 'z_old', 'tipo': 'cuarto_tecnico',
                         'nombre': 'Cuarto RITI / Teleco',
                         'origen': 'campo'}],
    })
    for tajo in ('tubeado', 'cableado'):
        ficha['estados']['p1__zesp__{}__z_old'.format(tajo)] = {
            'v': estado, 'f': None, 'r': None}
    return ficha


class _ConHoja(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.catalogo = _catalogo()

    def _escribir(self, contenido, nombre='REVISION PRUEBAS 15102026.html'):
        ruta = os.path.join(self.temporal.name, nombre)
        with open(ruta, 'w', encoding='utf-8') as fichero:
            fichero.write(contenido)
        return ruta


class TestExtraerZonasEspeciales(_ConHoja):
    def test_tarjeta_declara_tipo_nombre_y_tajos_en_orden(self):
        ruta = self._escribir(_hoja(
            _tarjeta('cuarto_tecnico', 'CUADRO SERVICIOS GENERALES', 'z_a',
                     tajos=('cableado', 'tubeado'))))

        zonas = lector.extraer_zonas_especiales(ruta)

        self.assertEqual(zonas, [{
            'portal_html': PORTAL, 'zona_id': 'z_a',
            'tipo': 'cuarto_tecnico', 'nombre': 'CUADRO SERVICIOS GENERALES',
            'tajos_html': ['cableado', 'tubeado'], 'problema': None,
        }])

    def test_tabla_con_varias_zonas_empareja_nombre_e_id_por_columna(self):
        ruta = self._escribir(_hoja(_bloque_tabla(
            'cuarto_ligero', [('z_b1', 'Bicicletas'), ('z_b2', 'Trastero')])))

        zonas = lector.extraer_zonas_especiales(ruta)

        self.assertEqual(
            [(z['zona_id'], z['tipo'], z['nombre'], z['problema'])
             for z in zonas],
            [('z_b1', 'cuarto_ligero', 'Bicicletas', None),
             ('z_b2', 'cuarto_ligero', 'Trastero', None)])
        self.assertEqual(zonas[0]['tajos_html'], ['tubeado', 'cableado'])

    def test_nombre_con_acentos_y_espacios_se_normaliza_sin_inventar(self):
        ruta = self._escribir(_hoja(_tarjeta(
            'cuarto_tecnico', '  Centralización   de contadores (P1) ',
            'z_c')))

        self.assertEqual(lector.extraer_zonas_especiales(ruta)[0]['nombre'],
                         'Centralización de contadores (P1)')

    def test_tarjeta_sin_categoria_no_se_adivina(self):
        ruta = self._escribir(_hoja(
            '<div class="tecnico-card"><div class="tecnico-card-head">'
            '<strong>Sin tipo</strong></div>' + _celda('z_d', 'tubeado')
            + '</div>'))

        # Sin ``data-zone-category`` no hay contenedor de zona declarada.
        self.assertEqual(lector.extraer_zonas_especiales(ruta), [])

    def test_tarjeta_sin_nombre_declara_el_problema(self):
        ruta = self._escribir(_hoja(
            '<div class="tecnico-card" data-zone-category="cubierta">'
            '<div class="tecnico-card-head"><span>sin strong</span></div>'
            + _celda('z_e', 'tubeado') + '</div>'))

        zona, = lector.extraer_zonas_especiales(ruta)

        self.assertIsNone(zona['nombre'])
        self.assertIn('nombre', zona['problema'])

    def test_tabla_con_distinto_numero_de_nombres_que_de_ids_declara_problema(self):
        bloque = _bloque_tabla('cuarto_ligero', [('z_f1', 'Uno'), ('z_f2', 'Dos')])
        bloque = bloque.replace('<th class="th-floor">Dos</th>', '')
        ruta = self._escribir(_hoja(bloque))

        zonas = lector.extraer_zonas_especiales(ruta)

        self.assertEqual({z['zona_id'] for z in zonas}, {'z_f1', 'z_f2'})
        for zona in zonas:
            self.assertIsNone(zona['nombre'])
            self.assertIn('nombre', zona['problema'])

    def test_celda_zesp_fuera_de_cualquier_zona_declarada_se_ignora(self):
        # Sigue siendo una clave sin resolver y asi la avisa el adaptador.
        ruta = self._escribir(_hoja(_celda('z_g', 'tubeado')))

        self.assertEqual(lector.extraer_zonas_especiales(ruta), [])

    @unittest.skipUnless(os.path.isfile(HOJA_REAL_OLABEAGA),
                         'hoja real de Olabeaga 14/10/2026 no disponible')
    def test_hoja_real_olabeaga_14_10_trae_14_zonas_completas(self):
        zonas = lector.extraer_zonas_especiales(HOJA_REAL_OLABEAGA)

        self.assertEqual(len(zonas), 14)
        self.assertTrue(all(z['tipo'] and z['nombre'] and not z['problema']
                            for z in zonas), zonas)
        nombres = {z['nombre'] for z in zonas}
        self.assertIn('CUADRO SEVICIOS GENERALES', nombres)
        self.assertIn('Cuarto RITI / Teleco', nombres)
        self.assertEqual({z['tipo'] for z in zonas},
                         {'cuarto_tecnico', 'cuarto_ligero', 'cubierta'})


class TestEstructuraNuevaConZonasEspeciales(_ConHoja):
    def test_zona_declarada_y_desconocida_se_propone_con_tipo_nombre_y_tajos(self):
        ficha = fixtures.ficha_minima()    # ni siquiera tiene planta zesp
        ruta = self._escribir(_hoja(
            _tarjeta('cuarto_tecnico', 'CUADRO SERVICIOS GENERALES', 'z_new',
                     tajos=('tubeado', 'cableado', 'tajo-nuevo-html'))))

        nuevas = adaptador.estructura_nueva_en_hoja(
            ruta, 'pruebas', ficha, self.catalogo)

        self.assertEqual(nuevas, [{
            'edificio': 'P1', 'planta': 'Zonas especiales',
            'planta_id': 'zesp', 'portal_id': 'p1', 'unidad': 'z_new',
            'tipo_ubicacion': 'cuarto_tecnico',
            'nombre_ubicacion': 'CUADRO SERVICIOS GENERALES',
            'tajos': ['tubeado', 'cableado'],
            'tajos_sin_traducir': ['tajo-nuevo-html'],
            'problema': None,
        }])

    def test_zona_ya_en_la_base_no_se_repite(self):
        ficha = _ficha_con_zona_antigua()
        ruta = self._escribir(_hoja(
            _tarjeta('cuarto_tecnico', 'Cuarto RITI / Teleco', 'z_old')))

        self.assertEqual(adaptador.estructura_nueva_en_hoja(
            ruta, 'pruebas', ficha, self.catalogo), [])

    def test_zona_incompleta_se_propone_con_su_problema_para_que_se_vea(self):
        ficha = fixtures.ficha_minima()
        ruta = self._escribir(_hoja(
            '<div class="tecnico-card" data-zone-category="cubierta">'
            '<div class="tecnico-card-head"><span>x</span></div>'
            + _celda('z_h', 'tubeado') + '</div>'))

        nuevas = adaptador.estructura_nueva_en_hoja(
            ruta, 'pruebas', ficha, self.catalogo)

        self.assertEqual(len(nuevas), 1)
        self.assertIsNone(nuevas[0]['nombre_ubicacion'])
        self.assertIn('nombre', nuevas[0]['problema'])

    def test_zona_de_un_portal_desconocido_no_se_inventa(self):
        ficha = fixtures.ficha_minima()
        ruta = self._escribir(_hoja(
            _tarjeta('cuarto_tecnico', 'Zona', 'z_i')
            .replace(PORTAL, 'src_pruebas_p9')))

        self.assertEqual(adaptador.estructura_nueva_en_hoja(
            ruta, 'pruebas', ficha, self.catalogo), [])


class TestAmpliarConZonasEspeciales(_ConHoja):
    def _nuevas(self, ficha, *bloques):
        ruta = self._escribir(_hoja(*bloques))
        return ruta, adaptador.estructura_nueva_en_hoja(
            ruta, 'pruebas', ficha, self.catalogo)

    def test_alta_crea_planta_zesp_zona_y_solo_las_celdas_que_imprime_la_hoja(self):
        ficha = fixtures.ficha_minima()
        _ruta, nuevas = self._nuevas(ficha, _tarjeta(
            'cuarto_tecnico', 'CUADRO SERVICIOS GENERALES', 'z_new',
            tajos=('tubeado',)))

        ampliada, informe = ficha_obra.ampliar_estructura_desde_hoja(
            ficha, nuevas, '15/10/2026', 'rev_html_15102026')

        portal = ampliada['estructura']['bloques'][0]['portales'][0]
        planta = next(p for p in portal['plantas'] if p['id'] == 'zesp')
        self.assertEqual(planta['nombre'], 'Zonas especiales')
        self.assertEqual(planta['ubicaciones'], [{
            'id': 'z_new', 'tipo': 'cuarto_tecnico',
            'nombre': 'CUADRO SERVICIOS GENERALES',
            'origen': 'hoja digital', 'confirmado': '15/10/2026',
            'visto_en': 'rev_html_15102026',
        }])
        self.assertEqual(
            {c: v for c, v in ampliada['estados'].items() if 'zesp' in c},
            {'p1__zesp__tubeado__z_new': {'v': '?', 'f': None, 'r': None}})
        self.assertEqual(informe['celdas_creadas'],
                         ['p1__zesp__tubeado__z_new'])
        self.assertEqual(informe['no_incorporadas'], [])
        # No toca las viviendas ni inventa tajos para la zona.
        self.assertEqual(
            {c for c in ampliada['estados'] if 'zesp' not in c}, set())
        # Trabaja sobre una copia: la ficha de entrada queda intacta.
        self.assertEqual(fixtures.ficha_minima(), ficha)

    def test_zona_nueva_en_planta_zesp_existente_conserva_la_antigua(self):
        ficha = _ficha_con_zona_antigua()
        _ruta, nuevas = self._nuevas(
            ficha, _tarjeta('cuarto_tecnico', 'Cuarto nuevo', 'z_new'))

        ampliada, _ = ficha_obra.ampliar_estructura_desde_hoja(
            ficha, nuevas, '15/10/2026', 'rev')

        planta = next(p for p in ampliada['estructura']['bloques'][0][
            'portales'][0]['plantas'] if p['id'] == 'zesp')
        self.assertEqual([u['id'] for u in planta['ubicaciones']],
                         ['z_old', 'z_new'])
        self.assertEqual(
            sum(1 for p in ampliada['estructura']['bloques'][0]['portales'][
                0]['plantas'] if p['id'] == 'zesp'), 1)

    def test_zona_nueva_se_agrupa_por_tipo_sin_reordenar_las_existentes(self):
        """El orden de las zonas es el de la hoja (tecnicos, ligeros,
        cubierta); un alta no debe barajarlas por id."""
        ficha = fixtures.ficha_minima()
        portal = ficha['estructura']['bloques'][0]['portales'][0]
        portal['plantas'].append({
            'id': 'zesp', 'nombre': 'Zonas especiales', 'orden': 999,
            'ubicaciones': [
                {'id': 'z_9', 'tipo': 'cuarto_tecnico', 'nombre': 'T9'},
                {'id': 'z_1', 'tipo': 'cuarto_tecnico', 'nombre': 'T1'},
                {'id': 'z_5', 'tipo': 'cuarto_ligero', 'nombre': 'L5'},
                {'id': 'z_3', 'tipo': 'cubierta', 'nombre': 'C3'},
            ],
        })
        _ruta, nuevas = self._nuevas(
            ficha,
            _tarjeta('cuarto_tecnico', 'T2', 'z_2'),
            _tarjeta('cubierta', 'C0', 'z_0'),
            _tarjeta('cuarto_ligero', 'L8', 'z_8'))

        ampliada, _ = ficha_obra.ampliar_estructura_desde_hoja(
            ficha, nuevas, '15/10/2026', 'rev')

        planta = next(p for p in ampliada['estructura']['bloques'][0][
            'portales'][0]['plantas'] if p['id'] == 'zesp')
        self.assertEqual([u['id'] for u in planta['ubicaciones']],
                         ['z_9', 'z_1', 'z_2', 'z_5', 'z_8', 'z_3', 'z_0'])

    def test_aplicar_dos_veces_no_duplica(self):
        ficha = fixtures.ficha_minima()
        ruta, nuevas = self._nuevas(
            ficha, _tarjeta('cubierta', 'Cubierta', 'z_cub'))
        una, _ = ficha_obra.ampliar_estructura_desde_hoja(
            ficha, nuevas, '15/10/2026', 'rev')

        self.assertEqual(adaptador.estructura_nueva_en_hoja(
            ruta, 'pruebas', una, self.catalogo), [])
        dos, informe = ficha_obra.ampliar_estructura_desde_hoja(
            una, nuevas, '15/10/2026', 'rev')

        self.assertEqual(dos, una)
        self.assertEqual(informe['anadidas'], [])

    def test_zona_sin_tipo_valido_o_sin_nombre_no_entra_y_se_informa(self):
        ficha = fixtures.ficha_minima()
        items = [
            {'edificio': 'P1', 'planta': 'Zonas especiales',
             'planta_id': 'zesp', 'portal_id': 'p1', 'unidad': 'z_x',
             'tipo_ubicacion': 'sotano_raro', 'nombre_ubicacion': 'X',
             'tajos': ['tubeado'], 'tajos_sin_traducir': [], 'problema': None},
            {'edificio': 'P1', 'planta': 'Zonas especiales',
             'planta_id': 'zesp', 'portal_id': 'p1', 'unidad': 'z_y',
             'tipo_ubicacion': 'cubierta', 'nombre_ubicacion': None,
             'tajos': ['tubeado'], 'tajos_sin_traducir': [],
             'problema': 'la hoja no imprime el nombre de la zona'},
        ]

        ampliada, informe = ficha_obra.ampliar_estructura_desde_hoja(
            ficha, items, '15/10/2026', 'rev')

        self.assertEqual(ampliada, ficha)
        self.assertEqual(informe['anadidas'], [])
        self.assertEqual([i['unidad'] for i in informe['no_incorporadas']],
                         ['z_x', 'z_y'])
        self.assertTrue(all(i['motivo'] for i in informe['no_incorporadas']))

    def test_zona_excluida_a_proposito_no_resucita(self):
        ficha = _ficha_con_zona_antigua()
        ficha['estructura']['exclusiones'] = [{
            'portal': 'P1', 'planta': 'Zonas especiales', 'unidad': 'z_back',
            'motivo': 'no figura en la hoja del 01/10/2026',
            'fecha': '01/10/2026', 'revision': 'rev_x'}]
        _ruta, nuevas = self._nuevas(
            ficha, _tarjeta('cuarto_tecnico', 'Vuelve', 'z_back'))

        ampliada, informe = ficha_obra.ampliar_estructura_desde_hoja(
            ficha, nuevas, '15/10/2026', 'rev')

        self.assertEqual(ampliada, ficha)
        self.assertEqual(len(informe['excluidas']), 1)


class TestZonaRecreadaConOtroId(_ConHoja):
    """Flujo de ``leer_hoja_marcada --digital``: alta de la zona nueva y baja
    de la antigua por el camino de retirada ya existente."""

    def _flujo(self, ficha, ruta):
        nuevas = adaptador.estructura_nueva_en_hoja(
            ruta, 'pruebas', ficha, self.catalogo)
        ficha, _informe_alta = ficha_obra.ampliar_estructura_desde_hoja(
            ficha, nuevas, '15/10/2026', 'rev_html_15102026')
        ausentes = adaptador.estructura_ausente_en_hoja(
            ruta, 'pruebas', ficha, self.catalogo, fecha='15/10/2026')
        return ficha, ausentes

    def test_sin_el_alta_la_baja_era_imposible(self):
        """Documenta el sintoma original: claves sin resolver => no_fiable."""
        ficha = _ficha_con_zona_antigua()
        ruta = self._escribir(_hoja(
            _tarjeta('cuarto_tecnico', 'Cuarto RITI / Teleco', 'z_new')))

        ausentes = adaptador.estructura_ausente_en_hoja(
            ruta, 'pruebas', ficha, self.catalogo, fecha='15/10/2026')

        self.assertIn('sin resolver', ausentes['no_fiable'])

    def test_alta_de_la_nueva_y_baja_de_la_antigua_con_exclusion(self):
        ficha = _ficha_con_zona_antigua(estado='P')
        ruta = self._escribir(_hoja(
            _tarjeta('cuarto_tecnico', 'Cuarto RITI / Teleco', 'z_new')))

        ficha_ampliada, ausentes = self._flujo(ficha, ruta)

        self.assertIsNone(ausentes['no_fiable'])
        self.assertEqual([u['unidad'] for u in ausentes['unidades']],
                         ['z_old'])
        self.assertEqual(ausentes['tajos'], [])
        retirada, informe = ficha_obra.retirar_estructura_ausente_en_hoja(
            ficha_ampliada, ausentes, '15/10/2026', 'rev_html_15102026')

        self.assertTrue(informe['retirado'])
        self.assertEqual(informe['con_avance'], [])
        planta = next(p for p in retirada['estructura']['bloques'][0][
            'portales'][0]['plantas'] if p['id'] == 'zesp')
        self.assertEqual([u['id'] for u in planta['ubicaciones']], ['z_new'])
        self.assertEqual(
            sorted(c for c in retirada['estados'] if '__z_old' in c), [])
        self.assertEqual(
            sorted(c for c in retirada['estados'] if '__z_new' in c),
            ['p1__zesp__cableado__z_new', 'p1__zesp__tubeado__z_new'])
        self.assertEqual(retirada['estructura']['exclusiones'], [{
            'portal': 'P1', 'planta': 'Zonas especiales', 'unidad': 'z_old',
            'motivo': 'no figura en la hoja del 15/10/2026',
            'fecha': '15/10/2026', 'revision': 'rev_html_15102026'}])

    def test_todas_las_claves_de_la_hoja_resuelven_tras_el_alta(self):
        ficha = _ficha_con_zona_antigua(estado='P')
        ruta = self._escribir(_hoja(
            _tarjeta('cuarto_tecnico', 'CUADRO SERVICIOS', 'z_n1'),
            _tarjeta('cubierta', 'Cubierta', 'z_n2')))
        ficha_ampliada, _ = self._flujo(ficha, ruta)

        revision = adaptador.construir_revision_normalizada_html(
            ruta, 'pruebas', ficha_ampliada, self.catalogo)

        self.assertEqual(revision['metadata']['avisos'], [])
        zesp = [c for c in revision['celdas'] if '__zesp__' in c['clave']]
        self.assertEqual(len(zesp), 4)

    def test_zona_antigua_con_avance_no_se_retira_aunque_la_nueva_entra(self):
        ficha = _ficha_con_zona_antigua(estado='X')
        ruta = self._escribir(_hoja(
            _tarjeta('cuarto_tecnico', 'Cuarto RITI / Teleco', 'z_new')))

        ficha_ampliada, ausentes = self._flujo(ficha, ruta)
        retirada, informe = ficha_obra.retirar_estructura_ausente_en_hoja(
            ficha_ampliada, ausentes, '15/10/2026', 'rev')

        self.assertEqual(sorted(informe['con_avance']),
                         ['p1__zesp__cableado__z_old',
                          'p1__zesp__tubeado__z_old'])
        self.assertFalse(informe['retirado'])
        self.assertEqual(retirada, ficha_ampliada)    # nada se retira
        planta = next(p for p in retirada['estructura']['bloques'][0][
            'portales'][0]['plantas'] if p['id'] == 'zesp')
        self.assertEqual(sorted(u['id'] for u in planta['ubicaciones']),
                         ['z_new', 'z_old'])


if __name__ == '__main__':
    unittest.main()
