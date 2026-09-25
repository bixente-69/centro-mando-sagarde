# -*- coding: utf-8 -*-
import copy
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import adaptar_revision_garaje
import alta_garaje_desde_hoja
import ficha_garajes


CATALOGO = {
    'tajos': [
        {
            'id': 'garaje_tabicado',
            'nombre': 'Tabicado de garaje',
            'propiedad': 'externo',
            'ambito': 'zona_comun',
            'fase': 'Obra civil garaje',
            'orden': 500,
            'deps': [],
        },
        {
            'id': 'garaje_lucido',
            'nombre': 'Lucido de garaje',
            'propiedad': 'externo',
            'ambito': 'zona_comun',
            'fase': 'Obra civil garaje',
            'orden': 505,
            'deps': [{'id': 'garaje_tabicado', 'minimo': 1}],
        },
        {'id': 'tubeado', 'nombre': 'Tubeado de vivienda'},
    ],
    'obras': {},
}


def estructura(zonas=None):
    zonas = zonas or [
        {'id': 'zona_1', 'nombre': 'Vial <principal>', 'tipo': 'vial'},
        {'id': 'zona_2', 'nombre': 'Trasteros', 'tipo': 'trasteros'},
    ]
    return [
        {
            'id': 'garaje_1',
            'nombre': 'Garaje 1',
            'plantas': [
                {
                    'id': 'planta_s1',
                    'nombre': 'S-1',
                    'zonas': zonas,
                }
            ],
        }
    ]


def ficha_inicial(zonas=None):
    ficha = {}
    ficha_garajes.asegurar_apartados(ficha)
    ficha['estructura']['garajes'] = estructura(zonas)
    ficha['tajos']['detalle'] = [copy.deepcopy(CATALOGO['tajos'][0])]
    return ficha


def html_estructura(datos):
    bloque = json.dumps(datos, ensure_ascii=False).replace('<', r'\u003c')
    return (
        '<!DOCTYPE html><html><head>'
        '<script type="application/json" id="garaje-estructura">'
        + bloque
        + '</script></head><body></body></html>'
    )


def html_revision(pares):
    celdas = ''.join(
        f'<span class="td-st" data-k="{clave}" data-st="{estado}"></span>'
        for clave, estado in pares
    )
    return '<!DOCTYPE html><html><body>' + celdas + '</body></html>'


class TestAdaptadoresGaraje(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta_obra = os.path.join(self.temporal.name, 'obra')
        os.makedirs(self.carpeta_obra)

    def _escribir(self, nombre, contenido):
        ruta = os.path.join(self.temporal.name, nombre)
        with open(ruta, 'w', encoding='utf-8') as fichero:
            fichero.write(contenido)
        return ruta

    def test_alta_desde_estructura_embebida_con_formato_del_generador(self):
        datos = {
            'obra': '2026 OBRA PRUEBA',
            'garajes': estructura(),
            'tajos_seleccionados': ['garaje_lucido'],
        }
        hoja = self._escribir('HOJA GARAJE.html', html_estructura(datos))

        ficha, ruta = alta_garaje_desde_hoja.alta_garaje_desde_hoja(
            hoja,
            'prueba',
            carpeta_obra_abs=self.carpeta_obra,
            catalogo=CATALOGO,
        )

        self.assertEqual(datos['garajes'], ficha['estructura']['garajes'])
        self.assertEqual(
            [CATALOGO['tajos'][1]], ficha['tajos']['detalle']
        )
        self.assertEqual(
            os.path.join(
                self.carpeta_obra,
                'INFORME SAGARDE IA',
                'ficha_garajes.json',
            ),
            ruta,
        )
        self.assertEqual(ficha, ficha_garajes.cargar(self.carpeta_obra))
        self.assertEqual(
            'Vial <principal>',
            ficha['estructura']['garajes'][0]['plantas'][0]['zonas'][0]['nombre'],
        )

    def test_alta_no_sobrescribe_una_ficha_existente(self):
        existente = ficha_inicial()
        ruta_ficha = ficha_garajes.guardar(self.carpeta_obra, existente)
        with open(ruta_ficha, 'rb') as fichero:
            antes = fichero.read()
        hoja = self._escribir(
            'HOJA GARAJE.html',
            html_estructura({
                'obra': '2026 OBRA PRUEBA',
                'garajes': estructura([
                    {'id': 'otra', 'nombre': 'Otra', 'tipo': 'vial'}
                ]),
                'tajos_seleccionados': ['garaje_lucido'],
            }),
        )

        with self.assertRaisesRegex(FileExistsError, 'no se sobrescribe'):
            alta_garaje_desde_hoja.alta_garaje_desde_hoja(
                hoja,
                'prueba',
                carpeta_obra_abs=self.carpeta_obra,
                catalogo=CATALOGO,
            )

        with open(ruta_ficha, 'rb') as fichero:
            self.assertEqual(antes, fichero.read())

    def test_revision_aplica_estados_y_excluye_n_del_todo(self):
        zonas = [
            {'id': 'zona_x', 'nombre': 'Zona X', 'tipo': 'vial'},
            {'id': 'zona_m', 'nombre': 'Zona M', 'tipo': 'vial'},
            {'id': 'zona_barra', 'nombre': 'Zona /', 'tipo': 'vial'},
            {'id': 'zona_vacia', 'nombre': 'Zona vacía', 'tipo': 'vial'},
            {'id': 'zona_n', 'nombre': 'Zona N', 'tipo': 'vial'},
        ]
        ficha_garajes.guardar(self.carpeta_obra, ficha_inicial(zonas))
        hoja = self._escribir('REVISION GARAJE 25092026.html', html_revision([
            ('garaje_1__planta_s1__garaje_tabicado__zona_x', 'X'),
            ('garaje_1__planta_s1__garaje_tabicado__zona_m', 'M'),
            ('garaje_1__planta_s1__garaje_tabicado__zona_barra', '/'),
            ('garaje_1__planta_s1__garaje_tabicado__zona_vacia', ''),
            ('garaje_1__planta_s1__garaje_tabicado__zona_n', 'N'),
        ]))

        ficha, cambios, avisos, _ = (
            adaptar_revision_garaje.adaptar_revision_garaje(
                hoja,
                'prueba',
                carpeta_obra_abs=self.carpeta_obra,
                catalogo=CATALOGO,
            )
        )

        prefijo = 'garaje_1__planta_s1__garaje_tabicado__'
        self.assertEqual('X', ficha['estados'][prefijo + 'zona_x']['v'])
        self.assertEqual('M', ficha['estados'][prefijo + 'zona_m']['v'])
        self.assertEqual('/', ficha['estados'][prefijo + 'zona_barra']['v'])
        self.assertEqual('P', ficha['estados'][prefijo + 'zona_vacia']['v'])
        self.assertNotIn(prefijo + 'zona_n', ficha['estados'])
        self.assertEqual(4, cambios['estados_nuevos'])
        self.assertEqual([], avisos)

    def test_revision_descarta_zona_y_tajo_inexistentes_con_aviso(self):
        ficha_garajes.guardar(self.carpeta_obra, ficha_inicial())
        hoja = self._escribir('REVISION GARAJE 25092026.html', html_revision([
            ('garaje_1__planta_s1__garaje_tabicado__zona_inexistente', 'X'),
            ('garaje_1__planta_s1__garaje_inventado__zona_1', 'M'),
        ]))
        salida = io.StringIO()

        with redirect_stdout(salida):
            ficha, cambios, avisos, _ = (
                adaptar_revision_garaje.adaptar_revision_garaje(
                    hoja,
                    'prueba',
                    carpeta_obra_abs=self.carpeta_obra,
                    catalogo=CATALOGO,
                )
            )

        self.assertEqual({}, ficha['estados'])
        self.assertEqual([], cambios['tajos_nuevos'])
        self.assertEqual(
            ['garaje_1__planta_s1__zona_inexistente'],
            cambios['zonas_desconocidas'],
        )
        self.assertTrue(any('tajo desconocido' in aviso for aviso in avisos))
        self.assertIn('ZONA DESCONOCIDA descartada', salida.getvalue())
        self.assertIn('tajo desconocido', salida.getvalue())

    def test_estado_no_reconocido_no_baja_un_estado_guardado(self):
        ficha = ficha_inicial()
        clave = 'garaje_1__planta_s1__garaje_tabicado__zona_1'
        ficha['estados'][clave] = {
            'v': 'X', 'f': '24/09/2026', 'r': 'rev_24092026'
        }
        ficha_garajes.guardar(self.carpeta_obra, ficha)
        hoja = self._escribir('REVISION GARAJE 25092026.html', html_revision([
            (clave, 'terminado quizá'),
        ]))

        guardada, cambios, avisos, _ = (
            adaptar_revision_garaje.adaptar_revision_garaje(
                hoja,
                'prueba',
                carpeta_obra_abs=self.carpeta_obra,
                catalogo=CATALOGO,
            )
        )

        self.assertEqual(
            {'v': 'X', 'f': '24/09/2026', 'r': 'rev_24092026'},
            guardada['estados'][clave],
        )
        self.assertEqual([], cambios['estados_cambiados'])
        self.assertTrue(
            any('estado HTML desconocido' in aviso for aviso in avisos)
        )


if __name__ == '__main__':
    unittest.main()
