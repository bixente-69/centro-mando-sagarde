# -*- coding: utf-8 -*-
'''Caracter visual del informe ejecutivo: tipografia, color y logo.'''
import os
import sys
import tempfile
import unittest
from pathlib import Path


SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(SISTEMA_DIR))
sys.path.insert(0, SISTEMA_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'scripts'))

from reportlab.pdfbase import pdfmetrics

import generar_informe_ejecutivo as gie

FONTS_DIR = os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'assets', 'fonts')
GITIGNORE = os.path.join(ROOT_DIR, '.gitignore')


class TestActivosDelInforme(unittest.TestCase):
    '''Los activos existen y estan publicados.

    El .gitignore es lista blanca: lo que no se da de alta no llega a git, y
    una restauracion deja el informe sin fuente ni logo. Sin ruido.
    '''

    def test_las_cuatro_ttf_existen_y_son_estaticas(self):
        '''Cuatro, no dos: el informe usa <i> en los mensajes de "no hay nada
        que enseñar", y sin la cursiva real esas frases se quedaban redondas
        sin que saltara nada.'''
        for nombre in ('IBMPlexSans-Regular.ttf', 'IBMPlexSans-Bold.ttf',
                       'IBMPlexSans-Italic.ttf', 'IBMPlexSans-BoldItalic.ttf'):
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


class TestRegistroDeFuente(unittest.TestCase):

    def setUp(self):
        gie._registrar_fuentes()

    def test_registra_las_dos_variantes(self):
        registradas = pdfmetrics.getRegisteredFontNames()
        self.assertIn(gie.FUENTE, registradas)
        self.assertIn(gie.FUENTE_BOLD, registradas)

    def test_la_familia_resuelve_la_negrita(self):
        '''Sin registerFontFamily los <b> del informe dejan de funcionar y
        NO da error. Mutacion: quitar la llamada a registerFontFamily y este
        test tiene que ponerse en rojo.'''
        from reportlab.lib.fonts import tt2ps
        self.assertEqual(tt2ps(gie.FUENTE, 1, 0), gie.FUENTE_BOLD)

    def test_la_familia_resuelve_la_cursiva(self):
        '''El informe usa <i> en cinco sitios. Mutacion: mapear italic al
        FUENTE normal y este test se pone rojo.'''
        from reportlab.lib.fonts import tt2ps
        self.assertEqual(tt2ps(gie.FUENTE, 0, 1), gie.FUENTE_ITALIC)
        self.assertEqual(tt2ps(gie.FUENTE, 1, 1), gie.FUENTE_BOLD_ITALIC)

    def test_si_falta_la_fuente_falla_con_mensaje_legible(self):
        '''Un informe en Helvetica sin avisar es peor que un informe que no
        sale. Mutacion: sustituir el raise por un return y esto se pone rojo.'''
        original = gie.FONTS_DIR
        try:
            gie.FONTS_DIR = Path(tempfile.gettempdir()) / 'no_existe_sagarde'
            pdfmetrics._fonts.pop(gie.FUENTE, None)
            pdfmetrics._fonts.pop(gie.FUENTE_BOLD, None)
            with self.assertRaises(RuntimeError) as ctx:
                gie._registrar_fuentes()
            self.assertIn('IBMPlexSans-Regular.ttf', str(ctx.exception))
        finally:
            gie.FONTS_DIR = original
            gie._registrar_fuentes()


def _pdf_de_prueba(destino):
    '''Genera un informe minimo pero real, con las funciones de produccion.'''
    snapshot = [
        {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
         'unit': 'A', 'status': 'X'},
        {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
         'unit': 'B', 'status': 'M'},
        {'task': 'Cuadro mecanizado', 'building': 'P1', 'floor': '1',
         'unit': 'A', 'status': ''},
    ]
    gie.generar_pdf_ejecutivo(
        'OBRA DE PRUEBA', '01/08/2026', snapshot, destino,
        historial=[('01/08/2026', snapshot)])
    return destino


class TestTipografiaEnElPDF(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pdf = _pdf_de_prueba(Path(cls.tmp.name) / 'informe.pdf')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _fuentes_del_pdf(self):
        import pdfplumber
        with pdfplumber.open(str(self.pdf)) as doc:
            return {c['fontname'] for p in doc.pages for c in p.chars}

    def test_no_queda_helvetica_en_el_pdf(self):
        '''Caza tambien las celdas de texto plano, que no pasan por _style().
        Ninguna TableStyle del fichero declara FONTNAME, asi que caerian a la
        Helvetica por defecto de ReportLab y revisando el fuente no se ve.
        Mutacion: devolver 'Helvetica' en _style() y esto se pone rojo.'''
        rastro = sorted(f for f in self._fuentes_del_pdf() if 'Helvetica' in f)
        self.assertEqual(rastro, [], 'queda Helvetica en el PDF: ' + str(rastro))

    def test_la_fuente_incrustada_es_plex(self):
        fuentes = self._fuentes_del_pdf()
        self.assertTrue(any('IBMPlexSans' in f for f in fuentes),
                        'el PDF no incrusta IBM Plex Sans: ' + str(fuentes))

    def test_sigue_habiendo_negrita(self):
        '''Mutacion: quitar registerFontFamily y esto se pone rojo, porque
        todos los <b> caerian a la variante normal.'''
        fuentes = self._fuentes_del_pdf()
        self.assertTrue(any('Bold' in f for f in fuentes),
                        'no hay ni una negrita en el PDF: ' + str(fuentes))

    def test_sigue_habiendo_cursiva(self):
        '''El PDF anterior llevaba Helvetica-Oblique: hay <i> de verdad en el
        informe y no pueden perderse por el camino.'''
        fuentes = self._fuentes_del_pdf()
        self.assertTrue(any('Italic' in f for f in fuentes),
                        'se ha perdido la cursiva del informe: ' + str(fuentes))


class TestColorDescriptivo(unittest.TestCase):
    '''El color describe el estado, no lo juzga.

    Con el semaforo viejo, la pagina 1 de Mungia enseñaba tres lineas rojas
    -- "Remates finales 0 %" entre ellas -- en una obra al 80 %. Esas fases
    no van mal: es que todavia no tocan.
    '''

    def test_terminado_es_verde(self):
        self.assertEqual(gie._color_estado(100), gie.COL_OK)

    def test_sin_empezar_es_gris_no_rojo(self):
        self.assertEqual(gie._color_estado(0), gie.COL_GRIS)
        self.assertNotEqual(gie._color_estado(0), gie.COL_WARN)

    def test_en_marcha_es_azul_sea_alto_o_bajo(self):
        for pct in (1, 22, 59, 92, 99):
            self.assertEqual(gie._color_estado(pct), gie.COL_ACCENT,
                             'el %d %% deberia ser azul' % pct)

    def test_la_barra_mini_no_tiene_su_propia_regla(self):
        '''La regla estaba escrita dos veces: en _color_pct y copiada a mano
        en un ternario dentro de _make_mini_bar. Mutacion: volver a poner ahi
        un color literal y este test tiene que enterarse.'''
        import inspect
        fuente = inspect.getsource(gie._make_mini_bar)
        self.assertIn('_color_estado(pct)', fuente)
        for literal in ('#2E9E5B', '#E07B1A', '#D9483C'):
            self.assertNotIn(literal, fuente,
                             'vuelve a haber una regla de color propia aqui')

    def test_la_barra_mini_se_construye_sin_reventar(self):
        for pct in (0, 50, 100):
            self.assertIsNotNone(gie._make_mini_bar(pct))

    def test_ya_no_existe_la_funcion_vieja(self):
        self.assertFalse(hasattr(gie, '_color_pct'),
                         '_color_pct debe desaparecer, no convivir')


class TestLogo(unittest.TestCase):

    def test_respeta_la_proporcion_nativa(self):
        '''Iba aplastado, y distinto en cada pagina: 3.429 en la 1 y 3.467 en
        la 2, sobre un nativo de 3.638.'''
        from reportlab.lib.utils import ImageReader
        ancho_px, alto_px = ImageReader(str(gie.LOGO_PATH)).getSize()
        nativo = ancho_px / alto_px
        for ancho_mm in (48, 52):
            img = gie._logo_flowable(ancho_mm)
            self.assertAlmostEqual(img.drawWidth / img.drawHeight, nativo,
                                   places=2)

    def test_todas_las_paginas_usan_la_misma_proporcion(self):
        a, b = gie._logo_flowable(48), gie._logo_flowable(52)
        self.assertAlmostEqual(a.drawWidth / a.drawHeight,
                               b.drawWidth / b.drawHeight, places=3)

    def test_si_falta_el_logo_falla_con_mensaje_legible(self):
        '''Hoy caia a la palabra "SAGARDE" en texto sin avisar. Mutacion:
        devolver un Paragraph en vez de lanzar y esto se pone rojo.'''
        original = gie.LOGO_PATH
        try:
            gie.LOGO_PATH = Path(tempfile.gettempdir()) / 'no_hay_logo.jpg'
            with self.assertRaises(RuntimeError) as ctx:
                gie._logo_flowable(48)
            self.assertIn('logo', str(ctx.exception).lower())
        finally:
            gie.LOGO_PATH = original

    def test_el_fondo_del_logo_es_blanco(self):
        '''Tenia fondo azul palido -- (232,245,253) y (194,230,246) en las
        esquinas -- y por eso parecia un recuadro pegado sobre la hoja.'''
        from PIL import Image as PILImage
        im = PILImage.open(str(gie.LOGO_PATH)).convert('RGB')
        w, h = im.size
        for punto in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)):
            r, g, b = im.getpixel(punto)
            self.assertTrue(min(r, g, b) >= 250,
                            'la esquina %s no es blanca: %s'
                            % (punto, (r, g, b)))


if __name__ == '__main__':
    unittest.main()
