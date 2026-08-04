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

    def test_lo_no_medido_no_viaja_a_la_hoja(self):
        """P (comprobado pendiente), ? (nadie lo ha mirado) y N (no aplica)
        salen como celda en blanco para poder escribir encima a boli."""
        registro = gt.registro_revision_desde_ficha(
            self.OBRA,
            self._ficha({'p1__pb__tubeado__A': 'X',
                         'p1__pb__tubeado__B': 'P',
                         'p1__1__tubeado__A': '?',
                         'p1__1__tubeado__B': 'N'}),
            fixtures.prioridades([]))
        self.assertIsNotNone(registro)
        self.assertEqual(sorted(registro['estados'].values()), ['X'])


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


if __name__ == '__main__':
    unittest.main()
