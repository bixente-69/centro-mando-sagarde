# -*- coding: utf-8 -*-
"""Pruebas de la pestaña «Calendario» del ranking de Sagarde (personal_sagarde.html): qué obras tienen registro cada día.
Datos INVENTADOS. unittest de la biblioteca estándar.

Qué cubre:
  · El cálculo (personal_calculo.js, `calendarioMes`): el verificador de node con cifras hechas a mano, en tres zonas horarias.
  · La página: usa el cálculo compartido (no decide por su cuenta qué obras debían tener registro) y es de solo lectura.
  · El navegador: `verificar_calendario_obras.py` (cada casilla contra un cálculo independiente en Python, el detalle de cada
    día, el desplegable de obras, los meses, el móvil, la inyección de HTML, los avisos y las palabras de programador).
  · Que los ficheros nuevos de tests/ se publican (lista blanca del .gitignore) y que el cálculo y la página siguen publicándose.

`SAGARDE_SIN_NAVEGADOR=1` salta a propósito la parte de Playwright."""
import os
import re
import shutil
import subprocess
import sys
import unittest

TESTS = os.path.dirname(os.path.abspath(__file__))
MOTOR = os.environ.get('PERSONAL_MOTOR') or os.path.dirname(TESTS)
RAIZ = os.path.abspath(os.path.join(MOTOR, '..', '..'))
NODE = shutil.which('node')


def leer(ruta):
    with open(ruta, encoding='utf-8') as fh:
        return fh.read()


@unittest.skipUnless(NODE, 'falta node en el PATH: NO se ha probado el cálculo del calendario (personal_calculo.js)')
class TestCalculoDelCalendario(unittest.TestCase):
    def test_verificador_de_node_en_tres_zonas_horarias(self):
        p = subprocess.run([NODE, os.path.join(TESTS, 'verificar_personal_calendario.js')], cwd=MOTOR, capture_output=True, timeout=300)
        salida = (p.stdout + p.stderr).decode('utf-8', 'replace')
        self.assertEqual(0, p.returncode, '\n'.join(salida.splitlines()[-25:]))
        self.assertNotIn('FALLO', salida)
        self.assertEqual(3, len(re.findall(r'comprobaciones, 0 fallos', salida)), 'tres pasadas (local y dos zonas extremas):\n' + salida[-600:])

    def test_el_cuadro_no_se_cae_con_datos_rotos(self):
        script = ("const C=require('./personal_calculo.js');"
                  "const raros=[undefined,null,5,'x',{},[null],[{}],[5],[[]],[{obra:5,fecha:{},nombre:[]}]];let n=0;"
                  "for(const f of raros){for(const o of raros){C.calendarioMes(f,{anio:2026,mes:11,obrasAbiertas:o,hoy:'2026-11-09'});n++;}}"
                  "C.calendarioMes(1,2);C.calendarioMes();console.log('sin caidas:'+n)")
        p = subprocess.run([NODE, '-e', script], cwd=MOTOR, capture_output=True, timeout=60)
        salida = (p.stdout + p.stderr).decode('utf-8', 'replace')
        self.assertEqual(0, p.returncode, salida[-800:])
        self.assertIn('sin caidas:100', salida)


class TestLaPaginaSoloDibuja(unittest.TestCase):
    def setUp(self):
        self.html = leer(os.path.join(MOTOR, 'personal_sagarde.html'))
        i = self.html.index('/* ================= PESTAÑA: CALENDARIO')
        j = self.html.index('/* ================= NAVEGACIÓN ENTRE PESTAÑAS')
        self.codigo = self.html[i:j]

    def test_usa_el_calculo_compartido(self):
        self.assertIn('PersonalCalculo.calendarioMes(', self.codigo)

    def test_no_decide_por_su_cuenta_que_obras_debian_tener_registro(self):
        # Esa regla (laborables pasados, desde la primera jornada de cada obra) vive UNA sola vez, en el cálculo: la página
        # solo lee lo que éste le da (`obras`, `faltan`, `estado`, `laborable`…), no vuelve a calcular `esperadas`.
        for palabra in ('esperadas', 'primeraFecha', 'obrasEsperadas'):
            self.assertTrue(palabra not in self.codigo, 'la página no debe repetir la regla «%s» del cálculo' % palabra)

    def test_es_de_solo_lectura(self):
        for palabra in ('localStorage', 'sessionStorage', 'fetch(', 'XMLHttpRequest', 'createObjectURL', 'Blob(', 'download'):
            self.assertTrue(palabra not in self.codigo, 'el calendario solo enseña: no guarda ni descarga nada (%s)' % palabra)

    def test_la_pestana_y_su_hueco_existen(self):
        self.assertIn('data-v="calendario"', self.html)
        self.assertIn('id="vista-calendario"', self.html)
        self.assertIn('id="contenido-calendario"', self.html)


@unittest.skipIf(os.environ.get('SAGARDE_SIN_NAVEGADOR') == '1', 'SAGARDE_SIN_NAVEGADOR=1: NO se ha probado el calendario en el navegador')
class TestElNavegador(unittest.TestCase):
    def test_el_script_de_navegador_del_calendario_pasa(self):
        try:
            import playwright  # noqa: F401
        except ImportError:
            self.skipTest('falta Playwright: NO se ha probado el calendario en el navegador')
        script = os.path.join(TESTS, 'verificar_calendario_obras.py')
        self.assertTrue(os.path.isfile(script), 'falta tests/verificar_calendario_obras.py')
        p = subprocess.run([sys.executable, script, MOTOR], cwd=MOTOR, capture_output=True, timeout=900,
                           env=dict(os.environ, PYTHONUTF8='1'))
        salida = (p.stdout + p.stderr).decode('utf-8', 'replace')
        self.assertEqual(0, p.returncode, '\n'.join(salida.splitlines()[-25:]))
        self.assertRegex(salida.strip().splitlines()[-1], r'^\d+ comprobaciones, 0 fallos$', salida[-300:])


class TestSePublica(unittest.TestCase):
    """La lista blanca del .gitignore deja pasar lo nuevo: un fichero que se genera pero nunca se publica es la familia de
    fallos de este proyecto."""

    def publica(self, ruta):
        # `git check-ignore --no-index`: código 1 = NO está ignorado (se publicaría); 0 = ignorado
        p = subprocess.run(['git', 'check-ignore', '--no-index', '-q', ruta], cwd=RAIZ, capture_output=True)
        return p.returncode == 1

    @unittest.skipUnless(shutil.which('git'), 'falta git')
    def test_el_verificador_de_node_se_versiona(self):
        r = 'SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/verificar_personal_calendario.js'
        self.assertTrue(self.publica(r), 'falta su línea «!%s» en el .gitignore: se generaría pero nunca se publicaría' % r)

    @unittest.skipUnless(shutil.which('git'), 'falta git')
    def test_la_pagina_y_el_calculo_se_publican(self):
        base = 'SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/'
        for f in ('personal_sagarde.html', 'personal_calculo.js', 'tests/verificar_calendario_obras.py', 'tests/test_calendario_obras.py'):
            self.assertTrue(self.publica(base + f), '%s no se publicaría' % f)


if __name__ == '__main__':
    unittest.main()
