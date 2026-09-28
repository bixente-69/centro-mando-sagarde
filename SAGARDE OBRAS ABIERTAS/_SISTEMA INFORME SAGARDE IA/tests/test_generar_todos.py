# -*- coding: utf-8 -*-
"""Pruebas de los helpers de `generar_todos.py` que alimentan la
actualizacion de la ficha (_correcciones_mas_recientes, _mapa_tajos_cortos).

Nacen de la Tarea 5 (conectar la ficha al orquestador) Ronda 2: el revisor
encontro que, al estrechar los `except Exception` genericos de la Ronda 1
para dejar de tragar errores en silencio, se abrieron dos rutas nuevas donde
esos mismos helpers dejaban de avisar y en su lugar TUMBABAN la generacion
del panel de la obra (la excepcion escapaba hasta el `except Exception`
generico de `main()`). Estas pruebas fijan ese contrato: un fichero de
correcciones o un catalogo/adaptador con problemas tiene que avisar por
consola con el prefijo `[AVISO FICHA]` y devolver `{}`, nunca propagar.
"""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

_SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SISTEMA_DIR)
sys.path.insert(0, os.path.join(_SISTEMA_DIR, 'adaptadores'))

import generar_todos as gt
import generar_informe_ejecutivo as gie

# El propio directorio de pruebas, para que `import fixtures` funcione tanto
# bajo `discover -s tests` (que ya lo anade) como al invocar una clase por
# nombre: `python -m unittest tests.test_generar_todos.TestX`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fixtures


class TestCorreccionesMasRecientes(unittest.TestCase):
    """_correcciones_mas_recientes() localiza y lee el .correcciones.json
    mas reciente de una obra (las marcas escritas a boli sobre la hoja de
    campo). Un fichero ilegible o con forma inesperada no debe tumbar la
    regeneracion de la obra."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.carpeta = self._tmp.name
        os.makedirs(os.path.join(self.carpeta, 'REVISIONES'))

    def tearDown(self):
        self._tmp.cleanup()

    def _escribir(self, nombre, texto):
        ruta = os.path.join(self.carpeta, 'REVISIONES', nombre)
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(texto)
        return ruta

    def test_sin_ficheros_devuelve_vacio_sin_avisar(self):
        salida = io.StringIO()
        with redirect_stdout(salida):
            resultado = gt._correcciones_mas_recientes(self.carpeta)
        self.assertEqual(resultado, {})
        self.assertEqual(salida.getvalue(), '')

    def test_fichero_valido_devuelve_sus_estados(self):
        self._escribir('REVISION 27072026.pdf.correcciones.json',
                        json.dumps({'estados': {'p1__pb__tub__A': 'X'}}))
        resultado = gt._correcciones_mas_recientes(self.carpeta)
        self.assertEqual(resultado, {'p1__pb__tub__A': 'X'})

    def test_elige_el_fichero_mas_reciente_por_fecha_en_el_nombre(self):
        self._escribir('REVISION 25072026.pdf.correcciones.json',
                        json.dumps({'estados': {'viejo': 'X'}}))
        self._escribir('REVISION 27072026.pdf.correcciones.json',
                        json.dumps({'estados': {'nuevo': 'M'}}))
        resultado = gt._correcciones_mas_recientes(self.carpeta)
        self.assertEqual(resultado, {'nuevo': 'M'})

    def test_fecha_malformada_se_ignora_y_avisa(self):
        self._escribir('REVISION SIN FECHA.pdf.correcciones.json',
                        json.dumps({'estados': {'incorrecto': 'X'}}))
        self._escribir('REVISION 27072026.pdf.correcciones.json',
                        json.dumps({'estados': {'correcto': 'M'}}))
        salida = io.StringIO()
        with redirect_stdout(salida):
            resultado = gt._correcciones_mas_recientes(self.carpeta)
        self.assertEqual(resultado, {'correcto': 'M'})
        self.assertIn('[AVISO FICHA]', salida.getvalue())
        self.assertIn('SIN FECHA', salida.getvalue())

    def test_empate_de_fecha_avisa_y_elige_el_mtime_mas_reciente(self):
        antiguo = self._escribir(
            'REVISION A 27072026.pdf.correcciones.json',
            json.dumps({'estados': {'version': 'M'}}),
        )
        nuevo = self._escribir(
            'REVISION B 27072026.pdf.correcciones.json',
            json.dumps({'estados': {'version': 'X'}}),
        )
        os.utime(antiguo, (1000, 1000))
        os.utime(nuevo, (2000, 2000))
        salida = io.StringIO()
        with redirect_stdout(salida):
            resultado = gt._correcciones_mas_recientes(self.carpeta)
        self.assertEqual(resultado, {'version': 'X'})
        self.assertIn('[AVISO FICHA]', salida.getvalue())
        self.assertIn('misma fecha', salida.getvalue())
        self.assertIn(os.path.basename(nuevo), salida.getvalue())

    def test_json_sintacticamente_invalido_avisa_y_no_se_cae(self):
        self._escribir('REVISION 27072026.pdf.correcciones.json',
                        '{ esto no es json valido ///')
        salida = io.StringIO()
        with redirect_stdout(salida):
            resultado = gt._correcciones_mas_recientes(self.carpeta)
        self.assertEqual(resultado, {})
        self.assertIn('[AVISO FICHA]', salida.getvalue())

    def test_raiz_no_es_diccionario_avisa_y_no_se_cae(self):
        """Repro del hallazgo de Ronda 2: JSON sintacticamente valido ([])
        pero sin forma de diccionario. Antes del fix, `.get('estados')`
        lanzaba AttributeError sin capturar y tumbaba el panel."""
        self._escribir('REVISION 27072026.pdf.correcciones.json', '[]')
        salida = io.StringIO()
        with redirect_stdout(salida):
            resultado = gt._correcciones_mas_recientes(self.carpeta)
        self.assertEqual(resultado, {})
        self.assertIn('[AVISO FICHA]', salida.getvalue())

    def test_estados_con_forma_incorrecta_avisa_y_no_se_cae(self):
        self._escribir('REVISION 27072026.pdf.correcciones.json',
                        json.dumps({'estados': ['no', 'es', 'un', 'dict']}))
        salida = io.StringIO()
        with redirect_stdout(salida):
            resultado = gt._correcciones_mas_recientes(self.carpeta)
        self.assertEqual(resultado, {})
        self.assertIn('[AVISO FICHA]', salida.getvalue())


class TestMapaTajosCortos(unittest.TestCase):
    """_mapa_tajos_cortos() cruza el codigo corto del adaptador con el id
    largo del catalogo. Con el mapa vacio, TODAS las correcciones manuales
    de la obra dejan de aplicarse en esa pasada, asi que un fallo aqui tiene
    que avisar -- y nunca tumbar la generacion del panel."""

    def setUp(self):
        self._base_dir_original = gt.BASE_DIR
        self._sys_path_original = list(sys.path)
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        gt.BASE_DIR = self._base_dir_original
        sys.path[:] = self._sys_path_original
        self._tmp.cleanup()
        for nombre in list(sys.modules):
            if nombre.startswith('adaptador_pruebamapa'):
                del sys.modules[nombre]

    def _escribir_adaptador(self, nombre_fichero, contenido):
        with open(os.path.join(self._tmp.name, nombre_fichero),
                  'w', encoding='utf-8') as f:
            f.write(contenido)
        sys.path.insert(0, self._tmp.name)

    def _escribir_catalogo(self, contenido_json):
        os.makedirs(os.path.join(self._tmp.name, 'reglas'), exist_ok=True)
        with open(os.path.join(self._tmp.name, 'reglas', 'CATALOGO_TAJOS.json'),
                  'w', encoding='utf-8') as f:
            json.dump(contenido_json, f)
        gt.BASE_DIR = self._tmp.name

    def test_adaptador_inexistente_avisa_y_no_se_cae(self):
        salida = io.StringIO()
        with redirect_stdout(salida):
            resultado = gt._mapa_tajos_cortos('esto_no_existe_de_verdad_9999')
        self.assertEqual(resultado, {})
        self.assertIn('[AVISO FICHA]', salida.getvalue())

    def test_adaptador_que_lanza_excepcion_no_import_error_avisa_y_no_se_cae(self):
        """Repro del hallazgo de Ronda 2: el cuerpo del modulo lanza
        ValueError (no ImportError) al importarse. Antes del fix, solo se
        capturaba ImportError y esto escapaba hasta tumbar el panel."""
        self._escribir_adaptador(
            'adaptador_pruebamapabomba.py',
            "raise ValueError('boom: error interno del adaptador')\n")
        salida = io.StringIO()
        with redirect_stdout(salida):
            resultado = gt._mapa_tajos_cortos('pruebamapabomba')
        self.assertEqual(resultado, {})
        self.assertIn('[AVISO FICHA]', salida.getvalue())
        self.assertIn('ValueError', salida.getvalue())

    def test_catalogo_ilegible_avisa_y_no_se_cae(self):
        self._escribir_adaptador('adaptador_pruebamapaok.py',
                                  'TAJO_NOMBRE_CATALOGO = {}\n')
        os.makedirs(os.path.join(self._tmp.name, 'reglas'))
        with open(os.path.join(self._tmp.name, 'reglas', 'CATALOGO_TAJOS.json'),
                  'w', encoding='utf-8') as f:
            f.write('{ esto no es json valido ///')
        gt.BASE_DIR = self._tmp.name
        salida = io.StringIO()
        with redirect_stdout(salida):
            resultado = gt._mapa_tajos_cortos('pruebamapaok')
        self.assertEqual(resultado, {})
        self.assertIn('[AVISO FICHA]', salida.getvalue())

    def test_catalogo_con_forma_incorrecta_avisa_y_no_se_cae(self):
        self._escribir_adaptador('adaptador_pruebamapaok2.py',
                                  'TAJO_NOMBRE_CATALOGO = {}\n')
        self._escribir_catalogo([])  # lista en vez de objeto con 'tajos'
        salida = io.StringIO()
        with redirect_stdout(salida):
            resultado = gt._mapa_tajos_cortos('pruebamapaok2')
        self.assertEqual(resultado, {})
        self.assertIn('[AVISO FICHA]', salida.getvalue())

    def test_mapea_codigo_corto_al_id_largo_del_catalogo(self):
        self._escribir_adaptador(
            'adaptador_pruebamapafeliz.py',
            "TAJO_NOMBRE_CATALOGO = {'tub': 'Tubeado electricidad'}\n")
        self._escribir_catalogo({'tajos': [
            {'id': 'tubeado', 'nombre': 'Tubeado electricidad', 'aliases': []},
        ]})
        resultado = gt._mapa_tajos_cortos('pruebamapafeliz')
        self.assertEqual(resultado, {'tub': 'tubeado'})


class TestContratoFuenteEstructura(unittest.TestCase):
    """El filtro del desplegable del generador se apoya en que
    `fuente_estructura` valga 'ficha_obra.json' SOLO cuando la hoja sale de
    la base. Si el camino deducido empezara a marcarlo, la app ofreceria
    obras sin base de datos y no habria forma de notarlo desde fuera."""

    OBRA = {'id': 'pruebas', 'nombre': 'OBRA DE PRUEBAS'}

    def _ficha(self, estados):
        ficha = fixtures.ficha_minima()
        # Sin esto la ficha sale 'rancia' y ensucia la salida con un aviso.
        ficha['revisiones'] = [{'fecha': '27/07/2026'}]
        ficha['estados'] = {
            clave: {'v': valor, 'f': '27/07/2026', 'r': 'rev_27072026'}
            for clave, valor in estados.items()
        }
        return ficha

    def test_la_hoja_desde_la_ficha_se_marca_como_base(self):
        registro = gt.registro_revision_desde_ficha(
            self.OBRA,
            self._ficha({'p1__pb__tubeado__A': 'X'}),
            fixtures.prioridades([]))
        self.assertIsNotNone(registro)
        self.assertEqual(registro['fuente_estructura'], 'ficha_obra.json')

    def test_la_hoja_deducida_no_se_marca_como_base(self):
        registro = gt.crear_registro_revision(
            self.OBRA, fixtures.prioridades([fixtures.item()]))
        self.assertIsNotNone(registro)
        self.assertNotEqual(registro.get('fuente_estructura'),
                            'ficha_obra.json')

    def test_la_planta_zesp_no_viaja_al_registro_ni_infla_viviendas_planta(self):
        """27/09/2026: la planta virtual 'zesp' (zonas especiales de
        portal: cuarto técnico/ligero/cubierta) no son viviendas -- no
        deben aparecer COMO PLANTA en el desplegable "continuar desde" del
        generador ni inflar el recuento que ya usa Bixente para saber
        cuántas viviendas tiene la obra. Las zonas llegan por su propio
        canal, `zonasEspeciales` (ver TestZonasEspecialesLleganAlGenerador,
        28/09/2026)."""
        ficha = self._ficha({'p1__pb__tubeado__A': 'X'})
        ficha['estructura']['bloques'][0]['portales'][0]['plantas'].append({
            'id': gt.fichas.ID_PLANTA_ZONAS_ESPECIALES,
            'nombre': 'Zonas especiales', 'orden': 999,
            'ubicaciones': [
                {'id': 'cub1', 'tipo': 'cubierta', 'nombre': 'Cubierta'},
            ],
        })

        registro = gt.registro_revision_desde_ficha(
            self.OBRA, ficha, fixtures.prioridades([]))

        self.assertIsNotNone(registro)
        self.assertEqual(registro['resumen']['viviendas_planta'], 4)
        ids_planta = {
            planta['id']
            for bloque in registro['bloques']
            for portal in bloque['portales']
            for planta in portal['plantas']
        }
        self.assertFalse(
            any('zesp' in pid for pid in ids_planta),
            f'la planta de zonas especiales no debe viajar al registro: {ids_planta}')

    def test_la_hoja_deducida_tambien_precarga_la_n(self):
        """Mismo contrato que registro_revision_desde_ficha (27/09/2026):
        este camino (obras sin ficha_obra.json, deducidas del historial
        crudo) no debe quedarse atras y perder N tambien."""
        registro = gt.crear_registro_revision(
            self.OBRA, fixtures.prioridades([
                fixtures.item(unidad='A', estado='X'),
                fixtures.item(unidad='B', estado='P'),
                fixtures.item(unidad='C', estado='N'),
            ]))
        self.assertIsNotNone(registro)
        self.assertEqual(sorted(registro['estados'].values()), ['N', 'X'])

    def test_lo_no_medido_no_viaja_pero_n_si(self):
        """P (comprobado pendiente) y ? (nadie lo ha mirado) salen como
        celda en blanco para poder escribir encima a boli -- son el estado
        por defecto que una celda vacia ya recupera sola al aplicar. N (no
        aplica) SI viaja (27/09/2026): no es un default, y si no se
        precarga cada revision nueva pierde la marca y hay que rehacerla."""
        registro = gt.registro_revision_desde_ficha(
            self.OBRA,
            self._ficha({'p1__pb__tubeado__A': 'X',
                         'p1__pb__tubeado__B': 'P',
                         'p1__1__tubeado__A': '?',
                         'p1__1__tubeado__B': 'N'}),
            fixtures.prioridades([]))
        self.assertIsNotNone(registro)
        self.assertEqual(sorted(registro['estados'].values()), ['N', 'X'])


class TestZonasEspecialesLleganAlGenerador(unittest.TestCase):
    """28/09/2026: la base "continuar desde la ultima revision" del generador
    llegaba SIN las zonas especiales (cuartos tecnicos, cuartos ligeros y
    cubierta). El registro descartaba la planta virtual 'zesp' y con ella las
    zonas y todas sus marcas: la hoja siguiente obligaba a dar de alta cada
    zona a mano, con ids nuevos que la ficha no reconoce, y las marcas de la
    revision anterior se perdian (Bolueta: 7 zonas y 31 marcas del 28/09).

    El generador ya sabia importar `zonasEspeciales` por portal
    (`normaliseStructure`) y pintar sus celdas con la clave
    `portal__zesp__tajo__zona`; lo que faltaba era que el registro se las
    diera, con los ids REALES de la ficha para que la hoja rellenada vuelva a
    casar con las mismas zonas.
    """

    OBRA = {'id': 'pruebas', 'nombre': 'OBRA DE PRUEBAS'}
    P1 = 'src_pruebas_p1'
    P2 = 'src_pruebas_p2'

    ZONAS = [
        {'id': 'z_riti_1', 'tipo': 'cuarto_tecnico',
         'nombre': 'Cuarto RITI / Teleco', 'origen': 'revision_sin_confirmar',
         'confirmado': None, 'visto_en': '28/09/2026'},
        {'id': 'z_cub_2', 'tipo': 'cubierta', 'nombre': 'Cubierta',
         'origen': 'revision_sin_confirmar', 'confirmado': None,
         'visto_en': '28/09/2026'},
        {'id': 'z_bas_3', 'tipo': 'cuarto_ligero', 'nombre': 'Basuras',
         'origen': 'revision_sin_confirmar', 'confirmado': None,
         'visto_en': '28/09/2026'},
    ]
    ESTADOS = {
        'p1__pb__tubeado__A': 'X',
        'p1__zesp__garaje_tabicado__z_riti_1': 'X',
        'p1__zesp__garaje_lucido__z_riti_1': 'N',
        'p1__zesp__garaje_tubeado_emp__z_riti_1': 'P',
        'p1__zesp__garaje_cableado_emp__z_riti_1': '?',
        'p1__zesp__fv_paneles_instalacion__z_cub_2': 'M',
        'p1__zesp__garaje_tabicado__z_bas_3': '/',
    }

    def _ficha(self, zonas=None, estados=None):
        ficha = fixtures.ficha_minima()
        ficha['revisiones'] = [{'fecha': '28/09/2026'}]
        if zonas is not None:
            ficha['estructura']['bloques'][0]['portales'][0]['plantas'].append({
                'id': gt.fichas.ID_PLANTA_ZONAS_ESPECIALES,
                'nombre': 'Zonas especiales', 'orden': 999,
                'ubicaciones': [dict(z) for z in zonas],
            })
        ficha['estados'] = {
            clave: {'v': valor, 'f': '28/09/2026', 'r': 'rev_28092026'}
            for clave, valor in (estados or {}).items()
        }
        return ficha

    def _registro(self, ficha):
        salida = io.StringIO()
        with redirect_stdout(salida):
            registro = gt.registro_revision_desde_ficha(
                self.OBRA, ficha, fixtures.prioridades([], revision='28/09/2026'))
        self.assertIsNotNone(registro)
        return registro, salida.getvalue()

    def test_las_zonas_viajan_por_su_propio_canal_con_su_id_real(self):
        registro, _ = self._registro(self._ficha(self.ZONAS, self.ESTADOS))
        portal = registro['bloques'][0]['portales'][0]
        # Solo lo que el generador necesita y sabe leer, en el orden de la
        # ficha, con el id que ya tiene la zona (no uno nuevo).
        self.assertEqual(portal['zonasEspeciales'], [
            {'id': 'z_riti_1', 'tipo': 'cuarto_tecnico',
             'nombre': 'Cuarto RITI / Teleco'},
            {'id': 'z_cub_2', 'tipo': 'cubierta', 'nombre': 'Cubierta'},
            {'id': 'z_bas_3', 'tipo': 'cuarto_ligero', 'nombre': 'Basuras'},
        ])

    def test_las_marcas_de_zona_llegan_con_la_clave_que_pinta_la_hoja(self):
        """Clave = `${portal.id}__zesp__${tajo.id}__${zona.id}`, la misma con
        la que `specialCellHTML` busca la marca. P y ? no viajan, igual que
        en vivienda: la celda vacia ya los recupera sola."""
        registro, _ = self._registro(self._ficha(self.ZONAS, self.ESTADOS))
        de_zona = {k: v for k, v in registro['estados'].items()
                   if '__zesp__' in k}
        self.assertEqual(de_zona, {
            f'{self.P1}__zesp__garaje_tabicado__z_riti_1': 'X',
            f'{self.P1}__zesp__garaje_lucido__z_riti_1': 'N',
            f'{self.P1}__zesp__fv_paneles_instalacion__z_cub_2': 'M',
            f'{self.P1}__zesp__garaje_tabicado__z_bas_3': '/',
        })

    def test_las_viviendas_siguen_como_antes_y_zesp_no_se_cuela_como_planta(self):
        registro, _ = self._registro(self._ficha(self.ZONAS, self.ESTADOS))
        self.assertEqual(
            registro['estados'][f'{self.P1}__{self.P1}_f1__tubeado__A'], 'X')
        self.assertEqual(registro['resumen']['viviendas_planta'], 4)
        portal = registro['bloques'][0]['portales'][0]
        self.assertEqual([p['id'] for p in portal['plantas']],
                         [f'{self.P1}_f1', f'{self.P1}_f2'])

    def test_el_resumen_cuenta_las_zonas_y_las_celdas_precargadas(self):
        registro, _ = self._registro(self._ficha(self.ZONAS, self.ESTADOS))
        # 1 de vivienda + 4 de zona (X, N, M, /); P y ? no cuentan.
        self.assertEqual(registro['resumen']['estados_precargados'], 5)
        self.assertEqual(registro['resumen']['zonas_especiales'], 3)

    def test_una_obra_sin_zonas_no_gana_ninguna_clave_nueva_por_portal(self):
        registro, _ = self._registro(
            self._ficha(None, {'p1__pb__tubeado__A': 'X'}))
        portal = registro['bloques'][0]['portales'][0]
        self.assertNotIn('zonasEspeciales', portal)
        self.assertEqual(registro['resumen']['zonas_especiales'], 0)
        self.assertEqual(registro['resumen']['estados_precargados'], 1)

    def test_una_zona_que_el_generador_no_sabe_pintar_no_viaja_y_avisa(self):
        """El generador descarta en silencio una zona con tipo desconocido o
        sin nombre (`normaliseSpecialZones`). Si el registro se la mandara,
        sus marcas quedarian huerfanas sin que nadie lo notara: se queda
        fuera y se dice."""
        zonas = self.ZONAS + [
            {'id': 'z_raro_4', 'tipo': 'sotano', 'nombre': 'Sotano'},
            {'id': 'z_sinnombre_5', 'tipo': 'cubierta', 'nombre': ''},
        ]
        estados = dict(self.ESTADOS)
        estados['p1__zesp__garaje_tabicado__z_raro_4'] = 'X'
        estados['p1__zesp__fv_paneles_instalacion__z_sinnombre_5'] = 'X'

        registro, salida = self._registro(self._ficha(zonas, estados))

        portal = registro['bloques'][0]['portales'][0]
        self.assertEqual([z['id'] for z in portal['zonasEspeciales']],
                         ['z_riti_1', 'z_cub_2', 'z_bas_3'])
        self.assertFalse(any('z_raro_4' in k or 'z_sinnombre_5' in k
                             for k in registro['estados']))
        self.assertEqual(registro['resumen']['zonas_especiales'], 3)
        self.assertIn('[AVISO FICHA]', salida)
        self.assertIn('z_raro_4', salida)
        self.assertIn('z_sinnombre_5', salida)

    def test_la_funcion_viaja_solo_si_la_ficha_la_conoce(self):
        """`funcion` (riti, calderas...) solo ordena las listas del paso 2 del
        generador; la ficha la guarda unicamente cuando el alta la declaro.
        Si esta, se respeta; si no, no se inventa a partir del nombre."""
        zonas = [dict(self.ZONAS[0], funcion='riti'), dict(self.ZONAS[1])]
        registro, _ = self._registro(self._ficha(zonas, {}))
        por_id = {z['id']: z for z in
                  registro['bloques'][0]['portales'][0]['zonasEspeciales']}
        self.assertEqual(por_id['z_riti_1'].get('funcion'), 'riti')
        self.assertNotIn('funcion', por_id['z_cub_2'])

    def test_dos_portales_con_el_mismo_id_de_zona_no_mezclan_sus_marcas(self):
        ficha = self._ficha(self.ZONAS, self.ESTADOS)
        ficha['estructura']['bloques'][0]['portales'].append({
            'id': 'p2', 'nombre': 'P2', 'referencia': 'P2',
            'plantas': [
                {'id': 'pb', 'nombre': 'PB', 'orden': 0, 'ubicaciones': [
                    {'id': 'C', 'tipo': 'vivienda', 'origen': 'campo'}]},
                {'id': gt.fichas.ID_PLANTA_ZONAS_ESPECIALES,
                 'nombre': 'Zonas especiales', 'orden': 999, 'ubicaciones': [
                     {'id': 'z_riti_1', 'tipo': 'cuarto_tecnico',
                      'nombre': 'RITI del portal 2'}]},
            ],
        })
        ficha['estados']['p2__zesp__garaje_tabicado__z_riti_1'] = {
            'v': 'M', 'f': '28/09/2026', 'r': 'rev_28092026'}

        registro, _ = self._registro(ficha)

        self.assertEqual(
            registro['estados'][f'{self.P1}__zesp__garaje_tabicado__z_riti_1'],
            'X')
        self.assertEqual(
            registro['estados'][f'{self.P2}__zesp__garaje_tabicado__z_riti_1'],
            'M')
        portales = registro['bloques'][0]['portales']
        self.assertEqual(
            [z['nombre'] for z in portales[1]['zonasEspeciales']],
            ['RITI del portal 2'])

    def test_un_portal_que_solo_tiene_zonas_avisa_en_vez_de_perderlas_calladas(self):
        """Un portal sin plantas de viviendas no se ofrece (el generador se
        inventaria 6 plantas por defecto). Eso no puede ser silencioso."""
        ficha = self._ficha(self.ZONAS, self.ESTADOS)
        ficha['estructura']['bloques'][0]['portales'].append({
            'id': 'p9', 'nombre': 'SOLO ZONAS', 'referencia': 'SOLO ZONAS',
            'plantas': [
                {'id': gt.fichas.ID_PLANTA_ZONAS_ESPECIALES,
                 'nombre': 'Zonas especiales', 'orden': 999, 'ubicaciones': [
                     {'id': 'z_x_9', 'tipo': 'cubierta', 'nombre': 'Cubierta'}]},
            ],
        })
        registro, salida = self._registro(ficha)
        self.assertEqual(len(registro['bloques'][0]['portales']), 1)
        self.assertIn('[AVISO FICHA]', salida)
        self.assertIn('SOLO ZONAS', salida)


class TestTodosLosBloquesLleganAlGenerador(unittest.TestCase):
    """La hoja manda: si declara 2 bloques, salen los 2.

    Hasta el 05/08/2026 `registro_revision_desde_ficha` leia
    `bloques_ficha[0]` y descartaba el resto EN SILENCIO. Las 4 obras con
    ficha tienen 1 bloque, asi que nadie lo noto; lo destapo OBRA PRUEBA, que
    nace de una hoja de 2 bloques. Perder un bloque no da error: la obra
    simplemente sale mas pequena de lo que es.
    """

    OBRA = {'id': 'pruebas', 'nombre': 'OBRA DE PRUEBAS'}

    def _ficha_dos_bloques(self):
        ficha = fixtures.ficha_minima()
        ficha['revisiones'] = [{'fecha': '27/07/2026'}]
        segundo = {
            'id': 'b2', 'nombre': 'Bloque 2',
            'portales': [{
                'id': 'p2', 'nombre': 'P2', 'referencia': 'P2',
                'plantas': [
                    {'id': 'pb', 'nombre': 'PB', 'orden': 0, 'ubicaciones': [
                        {'id': 'C', 'tipo': 'vivienda', 'origen': 'campo'},
                    ]},
                ],
            }],
        }
        ficha['estructura']['bloques'].append(segundo)
        ficha['estados'] = {
            'p2__pb__tubeado__C': {'v': 'X', 'f': '27/07/2026',
                                   'r': 'rev_27072026'},
        }
        return ficha

    def _ubicaciones(self, registro):
        return sum(len(planta['vivs'])
                   for bloque in registro['bloques']
                   for portal in bloque['portales']
                   for planta in portal['plantas'])

    def test_no_se_pierde_ninguna_ubicacion_del_segundo_bloque(self):
        registro = gt.registro_revision_desde_ficha(
            self.OBRA, self._ficha_dos_bloques(), fixtures.prioridades([]))
        self.assertIsNotNone(registro)
        # 4 del bloque 1 (PB y 1a, A y B) + 1 del bloque 2 (PB, C)
        self.assertEqual(self._ubicaciones(registro), 5)
        self.assertEqual(registro['resumen']['viviendas_planta'], 5)

    def test_los_dos_bloques_conservan_su_nombre(self):
        registro = gt.registro_revision_desde_ficha(
            self.OBRA, self._ficha_dos_bloques(), fixtures.prioridades([]))
        self.assertEqual([b['nombre'] for b in registro['bloques']],
                         ['Bloque 1', 'Bloque 2'])

    def test_un_estado_del_segundo_bloque_llega_precargado(self):
        """Sin esto la celda saldria en blanco y la hoja de campo pediria
        remarcar a boli algo que la base ya sabia."""
        registro = gt.registro_revision_desde_ficha(
            self.OBRA, self._ficha_dos_bloques(), fixtures.prioridades([]))
        self.assertEqual(sorted(registro['estados'].values()), ['X'])
        self.assertEqual(registro['resumen']['estados_precargados'], 1)

    def test_una_obra_de_un_bloque_no_cambia(self):
        """Guarda contra efecto colateral: las 4 obras reales tienen 1
        bloque y su registro debe salir identico al de antes del arreglo."""
        ficha = fixtures.ficha_minima()
        ficha['revisiones'] = [{'fecha': '27/07/2026'}]
        ficha['estados'] = {'p1__pb__tubeado__A': {'v': 'X', 'f': '27/07/2026',
                                                   'r': 'rev_27072026'}}
        registro = gt.registro_revision_desde_ficha(
            self.OBRA, ficha, fixtures.prioridades([]))
        self.assertEqual(len(registro['bloques']), 1)
        self.assertEqual(registro['bloques'][0]['id'], 'src_pruebas_b1')
        self.assertEqual(
            [p['id'] for p in registro['bloques'][0]['portales']],
            ['src_pruebas_p1'])
        self.assertEqual(self._ubicaciones(registro), 4)


class TestFuenteInformeEjecutivo(unittest.TestCase):
    """El PDF debe usar el historial ya corregido por la ficha de obra."""

    def test_historial_validado_evitas_releer_el_adaptador(self):
        nombre_obra = '2026 MUNGIA ACR NEINOR'
        snapshot_validado = [{
            'task': 'Tubeado',
            'floor': '1',
            'building': 'ZR1.1',
            'unit': 'A2',
            'status': 'M',
        }]
        historial_validado = [('28/07/2026', snapshot_validado)]

        with patch.object(
            gie.ADAPTADORES[nombre_obra],
            'cargar_historial',
            side_effect=AssertionError('no debe releer la hoja original'),
        ), patch.object(gie, 'generar_pdf_ejecutivo') as generar_pdf:
            gie.generar_para_obra(
                nombre_obra,
                historial=historial_validado,
            )

        generar_pdf.assert_called_once()
        self.assertIs(generar_pdf.call_args.args[2], snapshot_validado)
        self.assertIs(
            generar_pdf.call_args.kwargs['historial'],
            historial_validado,
        )

    def test_modo_directo_sustituye_el_pdf_crudo_por_la_base(self):
        nombre_obra = '2026 MUNGIA ACR NEINOR'
        snapshot_crudo = [{
            'task': 'Tabicado', 'floor': '1', 'building': 'ZR1.1',
            'unit': 'A2', 'status': 'X',
        }]
        snapshot_base = [{
            'task': 'Tubeado interior', 'floor': '1', 'building': 'ZR1.1',
            'unit': 'A2', 'status': 'M',
        }]
        ficha = {'revisiones': [{'fecha': '28/07/2026'}]}

        with patch.object(gie.fichas, 'cargar', return_value=ficha), \
             patch.object(gie.fichas, 'snapshot_desde_ficha',
                          return_value=snapshot_base), \
             patch.object(gie.ADAPTADORES[nombre_obra], 'cargar_historial',
                          return_value=[('28/07/2026', snapshot_crudo)]), \
             patch.object(gie.priorizador_trabajos, 'priorizar_ficha',
                          return_value={'detalle_items': []}), \
             patch.object(gie, 'generar_pdf_ejecutivo') as generar_pdf:
            gie.generar_para_obra(nombre_obra)

        self.assertIs(generar_pdf.call_args.args[2], snapshot_base)
        self.assertIs(generar_pdf.call_args.kwargs['ficha'], ficha)
        self.assertIs(generar_pdf.call_args.kwargs['historial'][-1][1],
                      snapshot_base)


class TestObraSinRevisiones(unittest.TestCase):
    """Una obra sin medir no es una obra al 0 %.

    Caso real: 2026 GORLIZ HOSPITAL. Esta dada de alta con su documentacion de
    proyecto pero no tiene ni una revision de campo, y el indice la pintaba
    como '0%' en rojo, al lado de Mungia con 79.8. Eso es sustituir un
    desconocido por cero, que es de las cosas que este proyecto no hace.
    """

    def test_sin_revisiones_no_dice_un_porcentaje(self):
        bloque = gt.bloque_pct(0, n_rev=0)
        self.assertNotIn('%', bloque)
        self.assertIn('Sin revisiones', bloque)

    def test_sin_revisiones_no_se_pinta_como_alarma(self):
        """Rojo significa 'va mal'. Sin datos no se sabe si va mal."""
        self.assertNotIn('bad', gt.bloque_pct(0, n_rev=0))

    def test_con_revisiones_sigue_diciendo_el_porcentaje(self):
        bloque = gt.bloque_pct(79.8, n_rev=25)
        self.assertIn('79.8%', bloque)
        self.assertIn('ok', bloque)

    def test_un_cero_MEDIDO_si_es_un_cero(self):
        """Obra revisada y sin nada hecho: ahi el 0 % es un dato."""
        bloque = gt.bloque_pct(0, n_rev=3)
        self.assertIn('0%', bloque)
        self.assertIn('bad', bloque)


class TestBloquePctVivendaGaraje(unittest.TestCase):
    """27/09/2026: Bixente pidio ver, en la tarjeta de Obras Abiertas, el
    mismo grafico de tendencia que ya tenia el Centro de Mando -- y, al ser
    mas grande esa vista, con vivienda y garaje desdoblados uno encima del
    otro en vez de fundidos en un solo numero."""

    def test_sin_garaje_una_sola_fila_sin_icono(self):
        """Una obra sin garaje no debe verse distinta a como se veia antes
        de que existiera el parametro pct_garaje."""
        bloque = gt.bloque_pct(79.8, n_rev=25)
        self.assertIn('79.8%', bloque)
        self.assertNotIn('🏠', bloque)
        self.assertNotIn('🅿️', bloque)

    def test_con_garaje_dos_filas_con_su_propio_icono_y_porcentaje(self):
        bloque = gt.bloque_pct(89.7, n_rev=6, pct_garaje=52.3)
        self.assertIn('🏠', bloque)
        self.assertIn('89.7%', bloque)
        self.assertIn('🅿️', bloque)
        self.assertIn('52.3%', bloque)
        self.assertLess(bloque.index('🏠'), bloque.index('🅿️'))

    def test_sparkline_solo_aparece_con_dos_puntos_o_mas(self):
        con_un_punto = gt.bloque_pct(
            79.8, n_rev=6, pct_garaje=52.3, historico_pct_garaje=[52.3])
        self.assertNotIn('<svg', con_un_punto)

        con_dos_puntos = gt.bloque_pct(
            79.8, n_rev=6, pct_garaje=52.3,
            historico_pct_garaje=[45.0, 52.3])
        self.assertIn('<svg', con_dos_puntos)

    def test_variacion_positiva_y_negativa_en_cada_fila(self):
        bloque = gt.bloque_pct(
            79.8, n_rev=6, variacion_pct=2.3,
            pct_garaje=52.3, variacion_pct_garaje=-1.1)
        self.assertIn('+2.3%', bloque)
        self.assertIn('-1.1%', bloque)

    def test_sin_revisiones_ni_garaje_tapa_la_tarjeta_entera(self):
        """Norma general de bloque_pct (una obra sin ninguna revision no
        tiene ni siquiera '0 %'): sin dato en NINGUNA de las dos partes,
        el mensaje ocupa toda la tarjeta."""
        bloque = gt.bloque_pct(0, n_rev=0)
        self.assertIn('Sin revisiones', bloque)
        self.assertNotIn('🅿️', bloque)
        self.assertNotIn('🏠', bloque)

    def test_sin_revisiones_de_vivienda_pero_con_garaje_muestra_el_garaje(self):
        """27/09/2026, caso real Olabeaga: garaje con revisiones reales,
        vivienda recien dada de alta (estructura sembrada, 0 revisiones
        todavia). Antes esto colapsaba TODA la tarjeta a 'Sin revisiones'
        y escondia un garaje con dato real -- Bixente lo senalo viendo la
        tarjeta real ('tiene dos revisiones, una de garaje y una de
        viviendas' -- la de garaje no se veia en absoluto)."""
        bloque = gt.bloque_pct(0, n_rev=0, pct_garaje=52.3)
        self.assertIn('Sin revisiones', bloque)
        self.assertIn('🏠', bloque)
        self.assertIn('🅿️', bloque)
        self.assertIn('52.3%', bloque)


class TestRegistroGarajeDesdeFicha(unittest.TestCase):
    """26/09/2026: el desplegable 'Obra ya instalada' del generador solo
    ofrecia revisiones de VIVIENDA aunque tuviera Garajes seleccionado
    (aviso real de Bixente, viendo Gernika en el generador). Causa raiz:
    publicar_registro_revisiones() nunca leia ficha_garajes.json, asi que
    window.SAGARDE_OBRAS_REVISION nunca llevaba nada de garaje pese a que
    el propio JS del generador ya esperaba un campo 'garaje' con
    tiene_garaje/tiene_vivienda (loadInstalledWork ya los leia, pero nadie
    los escribia nunca). Estas pruebas fijan el contrato de
    registro_garaje_desde_ficha(), la funcion que llena ese hueco."""

    OBRA = {'id': 'pruebas', 'nombre': 'OBRA DE PRUEBAS'}

    def _ficha_garaje(self, estados=None):
        return {
            'version': 1,
            'estructura': {
                'garajes': [{
                    'id': 'g1', 'nombre': 'Garaje 1',
                    'plantas': [{
                        'id': 'gp1', 'nombre': 'S-1',
                        'zonas': [
                            {'id': 'z1', 'nombre': 'Vial 1', 'tipo': 'vial'},
                            {'id': 'z2', 'nombre': 'Cuarto técnico',
                             'tipo': 'cuarto_tecnico', 'funcion': 'generales'},
                        ],
                    }],
                }],
            },
            'tajos': {
                'detalle': [
                    {'id': 'garaje_tubeado_vial', 'nombre': 'Tubeado de viales',
                     'propiedad': 'propio', 'ambito': 'zona_comun', 'orden': 100,
                     'fase': 'Instalación interior garaje'},
                    {'id': 'garaje_tabicado', 'nombre': 'Tabicado de garaje',
                     'propiedad': 'externo', 'ambito': 'zona_comun', 'orden': 50,
                     'fase': 'Obra civil garaje'},
                ],
            },
            'estados': {
                clave: {'v': valor, 'f': '25/09/2026', 'r': 'rev_25092026'}
                for clave, valor in (estados or {}).items()
            },
            'revisiones': [{'id': 'rev_25092026', 'fecha': '25/09/2026'}],
            'dudas': [],
        }

    def _prioridades_garaje(self, revision='25/09/2026'):
        return {'revision': revision, 'generado': '25/09/2026 12:00',
                'catalogo_version': '1.3', 'resumen': {}}

    def test_estructura_se_pasa_practicamente_tal_cual(self):
        """A diferencia de vivienda, garaje NO reescribe ids: los de la
        ficha ya son los que necesita el generador (Fase 5)."""
        registro = gt.registro_garaje_desde_ficha(
            self.OBRA, self._ficha_garaje(), self._prioridades_garaje())
        self.assertIsNotNone(registro)
        self.assertEqual(registro['garajes'], [{
            'id': 'g1', 'nombre': 'Garaje 1',
            'plantas': [{
                'id': 'gp1', 'nombre': 'S-1',
                'zonas': [
                    {'id': 'z1', 'nombre': 'Vial 1', 'tipo': 'vial'},
                    {'id': 'z2', 'nombre': 'Cuarto técnico',
                     'tipo': 'cuarto_tecnico', 'funcion': 'generales'},
                ],
            }],
        }])

    def test_catalogo_ordenado_por_orden_con_propiedad_y_ambito_mapeados(self):
        registro = gt.registro_garaje_desde_ficha(
            self.OBRA, self._ficha_garaje(), self._prioridades_garaje())
        self.assertEqual([t['id'] for t in registro['catalog']],
                         ['garaje_tabicado', 'garaje_tubeado_vial'])
        tabicado = registro['catalog'][0]
        self.assertEqual(tabicado['p'], 'e')  # externo
        self.assertEqual(tabicado['a'], 'z')  # zona_comun

    def test_las_claves_de_estados_no_se_reescriben(self):
        clave = 'g1__gp1__garaje_tubeado_vial__z1'
        registro = gt.registro_garaje_desde_ficha(
            self.OBRA, self._ficha_garaje({clave: 'X'}),
            self._prioridades_garaje())
        self.assertEqual(registro['estados'], {clave: 'X'})

    def test_lo_no_medido_no_viaja_pero_n_si(self):
        """Mismo contrato que vivienda (27/09/2026): P/? se quedan fuera,
        N viaja."""
        registro = gt.registro_garaje_desde_ficha(
            self.OBRA,
            self._ficha_garaje({
                'g1__gp1__garaje_tubeado_vial__z1': 'X',
                'g1__gp1__garaje_tubeado_vial__z2': 'P',
                'g1__gp1__garaje_tabicado__z1': '?',
                'g1__gp1__garaje_tabicado__z2': 'N',
            }),
            self._prioridades_garaje())
        self.assertEqual(sorted(registro['estados'].values()), ['N', 'X'])

    def test_sin_garajes_en_la_estructura_devuelve_none(self):
        ficha = self._ficha_garaje()
        ficha['estructura']['garajes'] = []
        self.assertIsNone(gt.registro_garaje_desde_ficha(
            self.OBRA, ficha, self._prioridades_garaje()))

    def test_sin_tajos_devuelve_none(self):
        ficha = self._ficha_garaje()
        ficha['tajos']['detalle'] = []
        self.assertIsNone(gt.registro_garaje_desde_ficha(
            self.OBRA, ficha, self._prioridades_garaje()))

    def test_revision_y_resumen_salen_de_prioridades_no_de_la_ficha(self):
        registro = gt.registro_garaje_desde_ficha(
            self.OBRA,
            self._ficha_garaje({'g1__gp1__garaje_tubeado_vial__z1': 'X'}),
            {'revision': '26/09/2026', 'generado': '26/09/2026 08:00',
             'catalogo_version': '1.4',
             'resumen': {'listos': 3, 'verificar': 1, 'bloqueados': 2}})
        self.assertEqual(registro['revision'], '26/09/2026')
        self.assertEqual(registro['catalogo_version'], '1.4')
        self.assertEqual(registro['resumen']['listos'], 3)
        self.assertEqual(registro['resumen']['verificar'], 1)
        self.assertEqual(registro['resumen']['bloqueados'], 2)
        self.assertEqual(registro['resumen']['zonas'], 2)
        self.assertEqual(registro['resumen']['estados_precargados'], 1)


if __name__ == '__main__':
    unittest.main()
