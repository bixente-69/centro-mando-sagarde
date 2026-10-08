# -*- coding: utf-8 -*-
"""Alta nativa desde una exportacion HTML del generador."""
import os
import subprocess
import sys
import tempfile
import unittest


MOTOR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBRAS = os.path.dirname(MOTOR)
if MOTOR not in sys.path:
    sys.path.insert(0, MOTOR)

import alta_obra_desde_hoja as alta
import adaptar_revision_html
import registro_obras
import validar_revision


OLABEAGA = os.path.join(
    OBRAS, '2026 OLABEAGA BILBAO', 'REVISIONES',
    'REVISION 2026 OLABEAGA 27092026.html')
BARAKALDO = os.path.join(
    OBRAS, '2026 BARAKALDO 104V OBRAS ESPECIALES', 'REVISIONES',
    'REVISION 104V BARAKALDO OBRAS ESPECIALES 08102026.html')


def _tabla_viviendas(obra, fecha, bloque, portal, portal_id, plantas,
                      tajo='tabicado', estado='', celdas_extra=None):
    """Crea una tabla minima con el mismo contrato que imprime el generador."""
    cabeceras = []
    unidades = []
    celdas = []
    nombres_plantas = []
    for planta_id, planta_nombre, letras in plantas:
        nombres_plantas.append(planta_nombre)
        cabeceras.append(
            '<th class="th-floor" colspan="{}">Planta {} · {} viv.</th>'.format(
                len(letras), planta_nombre, len(letras)))
        unidades.extend('<th class="th-apt">{}</th>'.format(letra)
                        for letra in letras)
        celdas.extend(
            '<td class="td-st" data-k="{}__{}__{}__{}" data-st="{}"></td>'.format(
                portal_id, planta_id, tajo, letra, estado)
            for letra in letras)
    filas_extra = ''.join(
        '<tr class="tr-tajo"><td class="td-name">Tajo parcial</td>'
        '<td class="td-st" data-k="{}__{}__{}__{}" data-st="{}"></td></tr>'.format(
            portal_id, planta_id, tajo_extra, unidad, estado_extra)
        for planta_id, tajo_extra, unidad, estado_extra in (celdas_extra or []))
    return '''
    <section class="portal-section">
      <div class="portal-sheet-head">
        <span class="portal-block-name">{bloque}</span>
        <span class="portal-name">{portal}</span>
      </div>
      <table class="rev-table">
        <thead>
          <tr class="tr-ident"><th class="th-ident">{obra} · {fecha} · {bloque} · {portal} · Plantas {plantas}</th></tr>
          <tr><th class="th-floor th-floor-tajo">TAJO</th>{cabeceras}</tr>
          <tr>{unidades}</tr>
        </thead>
        <tbody><tr class="tr-tajo"><td class="td-name">Tabicado</td>{celdas}</tr>{filas_extra}</tbody>
      </table>
    </section>
    '''.format(
        obra=obra, fecha=fecha, bloque=bloque, portal=portal,
        plantas=' · '.join(nombres_plantas), cabeceras=''.join(cabeceras),
        unidades=''.join(unidades), celdas=''.join(celdas),
        filas_extra=filas_extra)


def _tabla_zona(obra, bloque, portal, portal_id, zona_id,
                grupo='Cuartos ligeros', nombre='Bicicletas',
                tajo='garaje_tabicado', estado=''):
    return '''
    <section class="hoja-section">
      <div class="garage-section-title">{grupo} · 1 zona</div>
      <div class="planta-block special-zone-table-block">
        <table class="rev-table">
          <thead>
            <tr class="tr-ident"><th>{obra} · {bloque} · {portal} · {grupo}</th></tr>
            <tr><th class="th-floor th-floor-tajo">TAJO</th><th class="th-floor">{nombre}</th></tr>
          </thead>
          <tbody><tr class="tr-tajo"><td class="td-name">Tabicado</td>
            <td><span class="td-st" data-k="{portal_id}__zesp__{tajo}__{zona_id}" data-st="{estado}"></span></td>
          </tr></tbody>
        </table>
      </div>
    </section>
    '''.format(obra=obra, bloque=bloque, portal=portal, grupo=grupo,
               nombre=nombre, portal_id=portal_id, tajo=tajo,
               zona_id=zona_id, estado=estado)


def _html_sintetico(tajo='tabicado', estado='', tajo_parcial=False):
    obra = 'OBRA SINTETICA'
    fecha = '01/10/2026'
    return '<!doctype html><html><body>{}{}{}</body></html>'.format(
        _tabla_viviendas(
            obra, fecha, 'Bloque 1', 'Portal 1', 'p_src_1', [
                ('f_src_11', '1.1', ['A']),
                ('f_src_12', '1.2', ['A', 'B']),
            ], tajo=tajo, estado=estado,
            celdas_extra=[('f_src_12', 'mont-elec', 'B', '')]
            if tajo_parcial else None),
        _tabla_zona(
            obra, 'Bloque 1', 'Portal 1', 'p_src_1', 'z_src_1',
            estado=estado),
        _tabla_viviendas(
            obra, fecha, 'Bloque 1', 'Portal 2', 'p_src_2', [
                ('f_src_21', '2.1', ['A', 'B', 'C']),
            ], tajo=tajo, estado=estado),
    )


class AltaHojaHtmlGenericaTests(unittest.TestCase):
    def _guardar(self, directorio, contenido, nombre='hoja.html'):
        ruta = os.path.join(directorio, nombre)
        with open(ruta, 'w', encoding='utf-8') as fichero:
            fichero.write(contenido)
        return ruta

    def test_estructura_exacta_de_dos_portales_y_una_zona(self):
        with tempfile.TemporaryDirectory() as temporal:
            ruta = self._guardar(temporal, _html_sintetico())
            hoja = alta.leer_hoja_html_generica(ruta, 'obra_sintetica')

        obra, fecha, orden, bloques, orden_tajos, tajos, marcas, estados = hoja
        self.assertEqual(obra, 'OBRA SINTETICA')
        self.assertEqual(fecha, '01/10/2026')
        self.assertEqual(orden, [
            ('Bloque 1', 'Portal 1'),
            ('Bloque 1', 'Portal 2'),
        ])
        self.assertEqual(bloques, {
            ('Bloque 1', 'Portal 1'): [
                {'nombre': '1.1', 'planta_id': '1.1', 'orden': 1.1,
                 'vivs': ['A']},
                {'nombre': '1.2', 'planta_id': '1.2', 'orden': 1.2,
                 'vivs': ['A', 'B']},
                {'nombre': 'Zonas especiales', 'planta_id': 'zesp',
                 'orden': 999, 'ubicaciones': [
                     {'id': 'z_src_1', 'tipo': 'cuarto_ligero',
                      'nombre': 'Bicicletas'},
                 ]},
            ],
            ('Bloque 1', 'Portal 2'): [
                {'nombre': '2.1', 'planta_id': '2.1', 'orden': 2.1,
                 'vivs': ['A', 'B', 'C']},
            ],
        })
        self.assertEqual(orden_tajos, ['tabicado', 'garaje_tabicado'])
        self.assertEqual(
            {tajo_id: tajos[tajo_id]['nombre'] for tajo_id in orden_tajos},
            {'tabicado': 'Tabicado',
             'garaje_tabicado': 'Tabicado (zona común)'})
        self.assertEqual(marcas, 0)
        self.assertEqual(len(estados), 7)
        self.assertEqual({celda['v'] for celda in estados.values()}, {'?'})

    def test_estados_solo_contienen_las_combinaciones_impresas(self):
        with tempfile.TemporaryDirectory() as temporal:
            ruta = self._guardar(
                temporal, _html_sintetico(tajo_parcial=True))
            hoja = alta.leer_hoja_html_generica(ruta, 'obra_sintetica')
            ficha = alta.construir_ficha(
                'obra_sintetica', 'OBRA SINTETICA', 'viviendas', hoja, ruta)

        claves_impresas = {
            'p1__1.1__tabicado__A',
            'p1__1.2__tabicado__A',
            'p1__1.2__tabicado__B',
            'p1__1.2__montante_electrica__B',
            'p1__zesp__garaje_tabicado__z_src_1',
            'p2__2.1__tabicado__A',
            'p2__2.1__tabicado__B',
            'p2__2.1__tabicado__C',
        }
        self.assertEqual(set(ficha['estados']), claves_impresas)
        self.assertNotIn(
            'p1__1.1__montante_electrica__A', ficha['estados'])
        self.assertNotIn(
            'p1__zesp__tabicado__z_src_1', ficha['estados'])

    def test_dos_data_k_que_traducen_a_la_misma_clave_abortan(self):
        obra = 'OBRA SINTETICA'
        fecha = '01/10/2026'
        html = '<!doctype html><html><body>{}</body></html>'.format(
            _tabla_viviendas(
                obra, fecha, 'Bloque 1', 'Portal 1', 'p_src_1', [
                    ('f_src_11', '1.1', ['A']),
                ], tajo='montante_electrica',
                celdas_extra=[('f_src_11', 'mont-elec', 'A', '')]))
        with tempfile.TemporaryDirectory() as temporal:
            ruta = self._guardar(temporal, html)
            with self.assertRaises(SystemExit) as error:
                alta.leer_hoja_html_generica(ruta, 'obra_sintetica')

        self.assertIn('misma clave de ficha', str(error.exception))
        self.assertIn('p1__1.1__montante_electrica__A', str(error.exception))

    def test_tajo_desconocido_aborta_y_nombra_el_id(self):
        with tempfile.TemporaryDirectory() as temporal:
            ruta = self._guardar(
                temporal, _html_sintetico(tajo='tajo-que-no-existe'))
            with self.assertRaises(SystemExit) as error:
                alta.leer_hoja_html_generica(ruta, 'obra_sintetica')
        self.assertIn('tajo-que-no-existe', str(error.exception))

    def test_cli_aborta_con_marcas_sin_flag_y_las_ignora_con_flag(self):
        with tempfile.TemporaryDirectory() as temporal:
            ruta = self._guardar(temporal, _html_sintetico(estado='/'))
            base = [sys.executable, os.path.join(MOTOR, 'alta_obra_desde_hoja.py'),
                    ruta, 'obra_sintetica', 'OBRA SINTETICA']
            sin_flag = subprocess.run(
                base, cwd=MOTOR, capture_output=True, text=True,
                encoding='utf-8', errors='replace', check=False)
            con_flag = subprocess.run(
                base + ['--estructura-con-marcas'], cwd=MOTOR,
                capture_output=True, text=True, encoding='utf-8',
                errors='replace', check=False)

        self.assertNotEqual(sin_flag.returncode, 0)
        self.assertIn('La hoja lleva 7 marcas', sin_flag.stdout + sin_flag.stderr)
        self.assertEqual(con_flag.returncode, 0, con_flag.stdout + con_flag.stderr)
        self.assertIn(
            '7 marcas ignoradas en el alta; se leeran despues con leer_hoja_marcada',
            con_flag.stdout)

    @unittest.skipUnless(os.path.isfile(OLABEAGA),
                         'No esta la hoja real de alta de Olabeaga')
    def test_regresion_olabeaga_el_despacho_usa_el_lector_antiguo(self):
        directo = alta.leer_hoja_html(OLABEAGA)
        despachado = alta.leer_hoja(OLABEAGA, 'olabeaga')
        self.assertEqual(despachado, directo)

    @unittest.skipUnless(os.path.isfile(BARAKALDO),
                         'No esta la primera hoja real de Barakaldo')
    def test_hoja_real_barakaldo(self):
        hoja = alta.leer_hoja(BARAKALDO, 'barakaldo')
        ficha = alta.construir_ficha(
            'barakaldo', '2026 BARAKALDO 104V OBRAS ESPECIALES',
            'viviendas', hoja, BARAKALDO)

        portales = [
            portal
            for bloque in ficha['estructura']['bloques']
            for portal in bloque['portales']
        ]
        viviendas_por_portal = []
        zonas = []
        for portal in portales:
            viviendas_por_portal.append(sum(
                1 for planta in portal['plantas']
                for ubicacion in planta['ubicaciones']
                if planta['id'] != 'zesp'))
            zonas.extend(
                ubicacion for planta in portal['plantas']
                if planta['id'] == 'zesp'
                for ubicacion in planta['ubicaciones'])

        self.assertEqual(len(portales), 2)
        self.assertEqual(viviendas_por_portal, [78, 28])
        self.assertEqual(len(zonas), 14)
        self.assertEqual(len(ficha['tajos']['aplicables']), 68)
        self.assertEqual(hoja[6], 10)
        self.assertEqual(len(ficha['estados']), 4140)
        self.assertEqual({celda['v'] for celda in ficha['estados'].values()}, {'?'})

        config = next(obra for obra in registro_obras.OBRAS
                      if obra['id'] == 'barakaldo')
        from bs4 import BeautifulSoup
        with open(BARAKALDO, encoding='utf-8', errors='strict') as fichero:
            soup = BeautifulSoup(fichero.read(), 'html.parser')
        traduce_tajos = alta._traduccion_tajos_generador()
        claves_impresas = []
        for celda in soup.find_all(attrs={'data-k': True}):
            portal, planta, tajo, unidad = alta._partes_data_k(celda)
            claves_impresas.append('{}__{}__{}__{}'.format(
                config['mapa_portales_revision_html'][portal],
                config['mapa_plantas_revision_html'][planta],
                traduce_tajos.get(tajo, tajo), unidad))
        self.assertEqual(len(claves_impresas), 4140)
        self.assertEqual(len(set(claves_impresas)), 4140)
        claves_ficha = set(ficha['estados'])
        self.assertEqual(len(set(claves_impresas) - claves_ficha), 0)
        self.assertEqual(len(claves_ficha - set(claves_impresas)), 0)

        revision = adaptar_revision_html.construir_revision_normalizada_html(
            BARAKALDO, 'barakaldo', ficha,
            validar_revision.cargar_catalogo_tajos(),
            portal_id_a_real=config['mapa_portales_revision_html'],
            planta_id_a_real=config['mapa_plantas_revision_html'],
            fecha='08/10/2026', sin_marca='desconocido')
        self.assertEqual(revision['metadata']['avisos'], [])
        self.assertEqual(len(revision['celdas']), 10)
        self.assertEqual(
            {celda['clave'] for celda in revision['celdas']},
            {
                'p1__1.1__montante_electrica__{}'.format(unidad)
                for unidad in ('A', 'B', 'C', 'D')
            } | {
                'p1__1.2__montante_electrica__{}'.format(unidad)
                for unidad in ('A', 'B', 'C', 'D', 'E', 'F')
            })
        self.assertEqual(
            {celda['estado_leido'] for celda in revision['celdas']}, {'/'})


if __name__ == '__main__':
    unittest.main()
