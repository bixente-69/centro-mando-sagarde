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
CATALOGO = os.path.join(RAIZ, 'reglas', 'CATALOGO_TAJOS.json')

NODE = shutil.which('node')

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
import registro_obras

#: Las obras que el generador conoce. Una obra cerrada sale del registro y de
#: `obras_revisiones.js`, y entonces `hoja_de()` devuelve una hoja vacia. Sin
#: esta guarda, las pruebas que cuentan tablas comparaban 0 con 0 y pasaban
#: sin verificar nada: un verde falso. Descubierto al cerrar Orueta el
#: 13/08/2026.
OBRAS_REGISTRADAS = {o['id'] for o in registro_obras.OBRAS}


def requiere_obra(obra):
    return unittest.skipUnless(
        obra in OBRAS_REGISTRADAS,
        "la obra '%s' ya no esta registrada, seguramente cerrada" % obra)

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

    @requiere_obra('bolueta')
    def test_cada_tabla_lleva_su_fila_de_identificacion(self):
        html = hoja_de('bolueta')
        self.assertGreater(html.count('<table class="rev-table">'), 0,
                           'la hoja salio vacia: la prueba no verificaba nada')
        self.assertEqual(html.count('<table class="rev-table">'),
                         html.count('class="th-ident"'),
                         'hay tablas sin fila de identificacion')

    @requiere_obra('obisporueta')
    def test_orueta_parte_cada_tabla_en_dos_hojas(self):
        html = hoja_de('obisporueta')
        self.assertEqual(html.count('<table class="rev-table">'), 16)
        self.assertIn('HOJA 1 DE 2', html)
        self.assertIn('HOJA 2 DE 2', html)

    def test_mungia_sigue_con_una_tabla_por_grupo_de_plantas(self):
        html = hoja_de('mungia')
        self.assertEqual(html.count('<table class="rev-table">'), 8)
        self.assertNotIn('HOJA 1 DE', html)

    @staticmethod
    def celdas_esperadas(obra):
        """Una celda por vivienda y por tajo de la matriz que la base OFRECE.

        Antes eran cifras fijas por obra (Bolueta 3686, Gernika 1216...), que
        habia que retocar a mano cada vez que la base dejaba de ofrecer un
        tajo. El 28/09/2026 el 'Cuarto tecnico' retirado dejo de salir cuando
        todas sus celdas estan clasificadas (Bolueta -97, Gernika -32) y
        volvera a moverse cuando se clasifique el de Mungia (62) y el de
        Prueba (31). Lo que la paginacion no puede hacer es perder o duplicar
        una celda de las que la hoja ofrece: eso es lo que se comprueba.
        """
        return ejecutar_en_node(
            '(loadInstalledWork(%s), getMatrixTajos().length * '
            'getPortalEntries().reduce((n,{portal})=>n+portal.plantas.reduce('
            '(m,pl)=>m+pl.vivs.length,0),0))' % json.dumps(obra))

    def test_no_se_pierde_ni_se_duplica_ninguna_celda(self):
        for obra in ('mungia', 'gernika', 'bolueta', 'obisporueta', 'prueba'):
            if obra not in OBRAS_REGISTRADAS:
                continue          # obra cerrada: ya no tiene hoja que emitir
            with self.subTest(obra=obra):
                esperadas = self.celdas_esperadas(obra)
                self.assertGreater(esperadas, 0,
                                   'la base no ofrece celdas: la prueba no verificaba nada')
                claves = re.findall(r'<td class="td-st[^"]*"[^>]*data-k="([^"]+)"',
                                    hoja_de(obra))
                self.assertEqual(len(claves), esperadas)
                self.assertEqual(len(set(claves)), esperadas, 'claves repetidas')

    def test_el_tajo_retirado_y_clasificado_no_sale_en_la_hoja(self):
        """28/09/2026: con todas sus celdas clasificadas el 'Cuarto tecnico'
        retirado ya no se ofrece (Bolueta y Gernika). Comprobado sobre la hoja
        emitida por el generador, no sobre el registro. Mungia y Prueba no se
        afirman aqui: siguen ofreciendolo mientras les queden celdas por
        clasificar y eso cambia en cuanto se marquen N; la regla en los dos
        sentidos esta en TestTajosRetiradosDelCatalogo (test_generar_todos)."""
        for obra, debe_salir in (('bolueta', False), ('gernika', False)):
            if obra not in OBRAS_REGISTRADAS:
                continue
            with self.subTest(obra=obra):
                claves = re.findall(r'<td class="td-st[^"]*"[^>]*data-k="([^"]+)"',
                                    hoja_de(obra))
                hay = any('__cuarto_tecnico__' in k for k in claves)
                self.assertEqual(hay, debe_salir)


@unittest.skipUnless(NODE, 'node no esta instalado')
class ZonasEspecialesVivienda(unittest.TestCase):

    CUBIERTA_IDS = {
        'fv_paneles_instalacion', 'fv_paneles_cableado',
        'fv_paneles_tierra', 'fv_strings_cableado',
        'fv_equipos_protecciones', 'fv_puesta_marcha',
        'cub_soporte_antena', 'cub_soporte_pararrayos',
        'cub_antena_instalacion', 'cub_pararrayos_instalacion',
        'cub_antena_cableado', 'cub_pararrayos_cableado',
        'cub_antena_tierra',
    }

    def test_perfiles_y_metadatos_salen_de_las_fuentes_reales(self):
        datos = ejecutar_en_node(
            '({especiales:SPECIAL_ZONE_PROFILE_TAJOS, '
            'tecnicoGaraje:GARAGE_PROFILE_TAJOS.cuarto_tecnico, '
            'ligeroGaraje:GARAGE_PROFILE_TAJOS.cuarto_ligero, catalogo:BASE_CAT})')
        self.assertEqual(datos['especiales']['cuarto_tecnico'],
                         datos['tecnicoGaraje'])
        self.assertEqual(datos['especiales']['cuarto_ligero'],
                         datos['ligeroGaraje'])
        self.assertEqual(set(datos['especiales']['cubierta']), self.CUBIERTA_IDS)

        ids = set(datos['especiales']['cuarto_tecnico'])
        ids.update(datos['especiales']['cuarto_ligero'])
        ids.update(datos['especiales']['cubierta'])
        self.assertEqual(len(ids), 35)
        en_generador = {t['id']: t for t in datos['catalogo'] if t['id'] in ids}
        self.assertEqual(set(en_generador), ids)

        with open(CATALOGO, encoding='utf-8') as f:
            reales = {t['id']: t for t in json.load(f)['tajos'] if t['id'] in ids}
        propiedad = {'propio': 'p', 'externo': 'e', 'coordinacion': 'c'}
        ambito = {'vivienda': 'v', 'zona_comun': 'z', 'edificio': 'd'}
        for tajo_id in sorted(ids):
            with self.subTest(tajo=tajo_id):
                impreso = en_generador[tajo_id]
                real = reales[tajo_id]
                self.assertEqual(impreso['name'], real['nombre'])
                self.assertEqual(impreso['g'], real['fase'])
                self.assertEqual(impreso['p'], propiedad[real['propiedad']])
                self.assertEqual(impreso['a'], ambito[real['ambito']])

    def test_alta_manual_guarda_tipo_nombre_y_funcion_en_el_portal(self):
        zonas = ejecutar_en_node("""(()=>{
          S.bloques=normaliseStructure({bloques:[{id:'b1',nombre:'Bloque 1',
            portales:[{id:'p1',nombre:'Portal 1',plantas:[{id:'f1',nombre:'PB',vivs:['A']}]}]}]});
          addPortalSpecialZone(0,0,'ct_riti');
          addPortalSpecialZone(0,0,'cl_basuras');
          addPortalSpecialZone(0,0,'cubierta');
          return S.bloques[0].portales[0].zonasEspeciales;
        })()""")
        self.assertEqual([z['tipo'] for z in zonas],
                         ['cuarto_tecnico', 'cuarto_ligero', 'cubierta'])
        self.assertEqual([z['nombre'] for z in zonas],
                         ['Cuarto RITI / Teleco', 'Basuras', 'Cubierta'])
        self.assertEqual(zonas[0]['funcion'], 'riti')
        self.assertEqual(zonas[1]['funcion'], 'basuras')
        self.assertNotIn('funcion', zonas[2])
        self.assertEqual(len({z['id'] for z in zonas}), 3)

    def test_hoja_emite_tarjetas_tabla_y_claves_zesp_de_cuatro_partes(self):
        html = ejecutar_en_node("""(()=>{
          CAT=BASE_CAT.map(t=>({...t}));
          const ids=[...new Set(Object.values(SPECIAL_ZONE_PROFILE_TAJOS).flat())];
          S.sel=new Set(ids);
          S.obra='OBRA PRUEBA ZONAS'; S.fecha='2026-09-27';
          S.bloques=normaliseStructure({bloques:[{id:'b1',nombre:'Bloque 1',
            portales:[{id:'p1',nombre:'Portal 1',plantas:[{id:'f1',nombre:'PB',vivs:['A']}],
              zonasEspeciales:[
                {id:'zt1',tipo:'cuarto_tecnico',nombre:'RITI',funcion:'riti'},
                {id:'zl1',tipo:'cuarto_ligero',nombre:'Basuras',funcion:'basuras'},
                {id:'zc1',tipo:'cubierta',nombre:'Cubierta'}]}]}]});
          return generateHTML({});
        })()""")
        claves = re.findall(r'data-k="([^"]*__zesp__[^"]*)"', html)
        self.assertEqual(len(claves), 51)
        self.assertEqual(len(set(claves)), 51)
        self.assertTrue(all(len(clave.split('__')) == 4 for clave in claves))
        self.assertTrue(all(clave.split('__')[0:2] == ['p1', 'zesp']
                            for clave in claves))
        self.assertIn('data-zone-category="cuarto_tecnico"', html)
        self.assertIn('data-zone-category="cubierta"', html)
        self.assertIn('data-zone-category="cuarto_ligero"', html)
        self.assertIn('class="tecnico-card"', html)
        self.assertIn('<table class="rev-table">', html)


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
