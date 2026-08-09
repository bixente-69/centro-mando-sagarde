# -*- coding: utf-8 -*-
"""La paginacion se prueba ejecutando el JS real del generador, no una copia.

Copiar la aritmetica a Python la dejaria divergir del navegador en silencio,
que es justo la familia de fallos de este proyecto: algo declarado que el
motor de verdad ignora.

Node es opcional: sin el, estas pruebas se saltan en vez de fallar, porque
Bixente lanza la suite con ficheros .bat y no puede depender de un runtime
que quiza no este.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
GENERADOR = os.path.join(RAIZ, 'generador_revisiones.html')
REVISIONES_JS = os.path.join(RAIZ, 'obras_revisiones.js')

NODE = shutil.which('node')

# Un DOM de mentira con lo justo para que el script del generador cargue
# fuera del navegador. No se simula nada de la paginacion: eso se ejecuta de
# verdad.
SHIM = """
const nodo = new Proxy({}, {
  get: (t, k) => k === 'style' ? {} :
    k === 'classList' ? {add(){}, remove(){}, contains: () => false} :
    k === 'options' ? [] :
    (k === 'value' || k === 'innerHTML' || k === 'textContent' || k === 'className') ? '' :
    k === 'nextElementSibling' ? nodo :
    typeof k === 'string' ? () => {} : undefined,
  set: () => true,
});
global.localStorage = {getItem: () => null, setItem(){}, removeItem(){}};
global.document = {getElementById: () => nodo, querySelectorAll: () => [],
                   querySelector: () => nodo, createElement: () => nodo, body: nodo};
global.window = global;
"""


def script_del_generador():
    """El bloque <script> principal, extraido por posicion, no por regex.

    El HTML que genera la hoja lleva dentro otro <script> escapado, asi que
    una expresion regular sobre todo el fichero cogeria el que no es.
    """
    lineas = open(GENERADOR, encoding='utf-8').read().split('\n')
    ini = next(i for i, l in enumerate(lineas)
               if l.strip() == '<script>' and 'LOGO_URI' in '\n'.join(lineas[i:i + 8]))
    fin = next(i for i, l in enumerate(lineas) if l.strip() == '</script>' and i > ini)
    return '\n'.join(lineas[ini + 1:fin])


def ejecutar_en_node(expresion):
    """Evalua `expresion` con el script del generador y los datos ya cargados."""
    datos = open(REVISIONES_JS, encoding='utf-8').read()
    codigo = script_del_generador()
    guion = (SHIM + '\n' + datos + '\n' +
             'console.log(JSON.stringify(eval(' +
             json.dumps(codigo + '\n;(' + expresion + ')') + ')));\n')
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False,
                                     encoding='utf-8') as f:
        f.write(guion)
        ruta = f.name
    try:
        salida = subprocess.run([NODE, ruta], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=120)
        if salida.returncode:
            raise AssertionError(salida.stderr[-1500:])
        return json.loads(salida.stdout.strip().splitlines()[-1])
    finally:
        os.unlink(ruta)


def hoja_de(obra):
    return ejecutar_en_node(
        '(loadInstalledWork(%s), S.fecha="2026-08-07", '
        'generateHTML(S.importData||{}))' % json.dumps(obra))


@unittest.skipUnless(NODE, 'node no esta instalado: la paginacion no se prueba')
class AritmeticaDePaginacion(unittest.TestCase):

    def test_el_cupo_sale_de_las_medidas_reales(self):
        # 284 util - 28 de cabecera de tabla - 4 de colchon
        self.assertAlmostEqual(ejecutar_en_node('cupoFilasMM()'), 252.0, places=2)

    def test_38_tajos_con_18_fases_caben_en_una_hoja(self):
        tajos = [{'id': 't%d' % i, 'name': 'T%d' % i, 'g': 'F%d' % (i % 18)}
                 for i in range(38)]
        hojas = ejecutar_en_node('repartirTajosEnHojas(%s)' % json.dumps(tajos))
        self.assertEqual(len(hojas), 1)

    def test_55_tajos_con_17_fases_necesitan_dos_hojas_equilibradas(self):
        tajos = [{'id': 't%d' % i, 'name': 'T%d' % i, 'g': 'F%d' % (i % 17)}
                 for i in range(55)]
        hojas = ejecutar_en_node('repartirTajosEnHojas(%s)' % json.dumps(tajos))
        self.assertEqual(len(hojas), 2)
        tamanos = sorted(len(h) for h in hojas)
        self.assertLessEqual(tamanos[1] - tamanos[0], 1,
                             'reparto desequilibrado: %s' % tamanos)

    def test_no_se_pierde_ni_se_duplica_ningun_tajo(self):
        tajos = [{'id': 't%d' % i, 'name': 'T%d' % i, 'g': 'F%d' % (i % 17)}
                 for i in range(55)]
        hojas = ejecutar_en_node('repartirTajosEnHojas(%s)' % json.dumps(tajos))
        ids = [t['id'] for hoja in hojas for t in hoja]
        self.assertEqual(len(set(ids)), 55)
        self.assertEqual([t['id'] for t in tajos], ids, 'se altero el orden')

    def test_ninguna_hoja_supera_el_cupo(self):
        tajos = [{'id': 't%d' % i, 'name': 'T%d' % i, 'g': 'F%d' % (i % 17)}
                 for i in range(55)]
        alturas = ejecutar_en_node(
            'repartirTajosEnHojas(%s).map(h=>alturaFilasMM(h))' % json.dumps(tajos))
        cupo = ejecutar_en_node('cupoFilasMM()')
        for alto in alturas:
            self.assertLessEqual(alto, cupo, 'una hoja de %smm sobre %s' % (alto, cupo))


@unittest.skipUnless(NODE, 'node no esta instalado')
class HtmlEmitido(unittest.TestCase):
    """Los invariantes del contrato con la lectura, sin necesidad de imprimir."""

    def test_cada_tabla_lleva_su_fila_de_identificacion(self):
        html = hoja_de('obisporueta')
        self.assertEqual(html.count('<table class="rev-table">'),
                         html.count('class="th-ident"'),
                         'hay tablas sin fila de identificacion')

    def test_orueta_parte_cada_tabla_en_dos_hojas(self):
        html = hoja_de('obisporueta')
        self.assertEqual(html.count('<table class="rev-table">'), 16)
        self.assertIn('HOJA 1 DE 2', html)
        self.assertIn('HOJA 2 DE 2', html)

    def test_mungia_sigue_con_una_tabla_por_grupo_de_plantas(self):
        html = hoja_de('mungia')
        self.assertEqual(html.count('<table class="rev-table">'), 8)
        self.assertNotIn('HOJA 1 DE', html)

    def test_no_se_pierde_ni_se_duplica_ninguna_celda(self):
        for obra, esperadas in [('mungia', 2356), ('gernika', 1216),
                                ('bolueta', 3686), ('obisporueta', 5610),
                                ('prueba', 1178)]:
            with self.subTest(obra=obra):
                claves = re.findall(r'<td class="td-st[^"]*"[^>]*data-k="([^"]+)"',
                                    hoja_de(obra))
                self.assertEqual(len(claves), esperadas)
                self.assertEqual(len(set(claves)), esperadas, 'claves repetidas')


def _hay_playwright():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(NODE and _hay_playwright(),
                     'sin node o sin playwright no se imprime el PDF')
class PdfReal(unittest.TestCase):
    """La comprobacion que de verdad importa: el papel.

    Se imprime el A4 como lo imprime Bixente y se valida con el mismo
    rejilla_hoja que luego lee las hojas marcadas. Lenta (~10s), por eso solo
    una obra: el barrido de las cinco es `python verificar_hojas_pdf.py`.
    """

    def test_la_hoja_de_obra_prueba_sale_limpia(self):
        sys.path.insert(0, RAIZ)
        import verificar_hojas_pdf as V
        with tempfile.TemporaryDirectory() as tmp:
            html = V.generar_html('prueba', os.path.join(tmp, 'h.html'))
            pdf = V.imprimir_pdf(html, os.path.join(tmp, 'h.pdf'))
            self.assertEqual(V.validar(pdf, 1178, 'prueba'), [])


if __name__ == '__main__':
    unittest.main()
