# -*- coding: utf-8 -*-
'''Caracter visual del informe ejecutivo: tipografia, color y logo.'''
import os
import sys
import unittest


SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(SISTEMA_DIR))
sys.path.insert(0, SISTEMA_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'scripts'))

FONTS_DIR = os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'assets', 'fonts')
GITIGNORE = os.path.join(ROOT_DIR, '.gitignore')


class TestActivosDelInforme(unittest.TestCase):
    '''Los activos existen y estan publicados.

    El .gitignore es lista blanca: lo que no se da de alta no llega a git, y
    una restauracion deja el informe sin fuente ni logo. Sin ruido.
    '''

    def test_las_dos_ttf_existen_y_son_estaticas(self):
        for nombre in ('IBMPlexSans-Regular.ttf', 'IBMPlexSans-Bold.ttf'):
            ruta = os.path.join(FONTS_DIR, nombre)
            self.assertTrue(os.path.isfile(ruta), 'falta la fuente ' + nombre)
            with open(ruta, 'rb') as f:
                cabecera = f.read(4)
                f.seek(0)
                entera = f.read()
            self.assertEqual(cabecera, b'\x00\x01\x00\x00',
                             nombre + ' no es una TTF valida')
            self.assertNotIn(b'fvar', entera,
                             nombre + ' es una fuente VARIABLE; ReportLab '
                             'necesita la estatica')

    def test_la_licencia_acompana_a_la_fuente(self):
        self.assertTrue(os.path.isfile(os.path.join(FONTS_DIR, 'OFL.txt')),
                        'la SIL OFL exige distribuir la licencia con la fuente')

    def test_fuentes_y_logo_estan_en_la_lista_blanca(self):
        with open(GITIGNORE, encoding='utf-8') as f:
            lineas = {l.strip() for l in f}
        for regla in ('!_SISTEMA/MOTOR/assets/fonts/*.ttf',
                      '!_SISTEMA/MOTOR/assets/fonts/OFL.txt',
                      '!_SISTEMA/MOTOR/assets/logo_sagarde.jpg'):
            self.assertIn(regla, lineas,
                          'sin esta linea el fichero no llega a git: ' + regla)


if __name__ == '__main__':
    unittest.main()
