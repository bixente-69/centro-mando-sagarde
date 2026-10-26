# -*- coding: utf-8 -*-
"""Pruebas del paso 08c2b: la suma por empresa. Datos INVENTADOS. unittest de la biblioteca estándar.

Qué cubre (la suma en sí y su cálculo con cifras a mano la prueba `verificar_personal_empresas.js` con node; el navegador, las
escenas T140–T146 de `verificar_generador_personal.py` y el script de los cuatro sitios del paso):
  · P2: el verificador de node (tres zonas horarias) y que la regla de «autónomo» de JS y de P1 coincide caso a caso.
  · Los datos: `aplanar` y el estado que se publica llevan la empresa de cada persona, y solo si la tiene (sin empresas
    puestas, las filas son idénticas a las de antes).
  · La pestaña y el informe aceptan filas con empresa (y rechazan una que no sea texto).
  · Los cuatro sitios usan la MISMA función de cálculo y el MISMO bloque; ninguno escribe su propia suma por empresa."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

MOTOR = os.environ.get('PERSONAL_MOTOR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MOTOR)
import panel_personal as PP
import personal_obra as P

NODE = shutil.which('node')
OBRAS = {'olabeaga': '2026 OLABEAGA BILBAO', 'mungia': '2026 MUNGIA ACR NEINOR'}
HOY = '2026-10-26'
AHORA = '2026-10-26T20:00:00+01:00'


def leer(nombre):
    with open(os.path.join(MOTOR, nombre), encoding='utf-8') as fh:
        return fh.read()


def jor(ambito, fecha, presentes):
    return {'ambito': ambito, 'fecha': fecha, 'presentes': [{'nombre': n, 'horas': h, 'extra': 0} for n, h in presentes]}


def lote(jornadas, obra='olabeaga', **kw):
    d = {'tipo': 'lote_personal', 'version': 1, 'obra': obra, 'jornadas': jornadas}
    d.update(kw)
    return d


@unittest.skipUnless(NODE, 'falta node en el PATH: NO se ha probado la suma por empresa de personal_calculo.js')
class TestCalculoDeLaSumaPorEmpresa(unittest.TestCase):
    def test_verificador_de_node_en_tres_zonas_horarias(self):
        p = subprocess.run([NODE, os.path.join(MOTOR, 'tests', 'verificar_personal_empresas.js')], cwd=MOTOR,
                           capture_output=True, timeout=300)
        salida = (p.stdout + p.stderr).decode('utf-8', 'replace')
        self.assertEqual(0, p.returncode, '\n'.join(salida.splitlines()[-25:]))
        self.assertNotIn('FALLO', salida)
        self.assertEqual(3, len(re.findall(r'comprobaciones, 0 fallos', salida)), 'tres pasadas (local y dos zonas extremas):\n' + salida[-600:])

    def test_la_regla_de_autonomo_es_la_misma_en_js_y_en_p1(self):
        casos = ['Javi @AUT', 'Javi@aut', 'JAVI @ AUT ', 'Javi @AuT', '@AUT', 'AUT', 'Autónomos SL', '@AUT SL', 'Javi AUT',
                 'Javi @AUTO', '', 'Sin empresa', 'Manueles', 'CATERSYSTEM', 'a @aut', 'a @a ut', 'x@aut@aut', '  @  aut  ']
        script = ("const C=require('./personal_calculo.js');const c=JSON.parse(process.argv[1]);"
                  "console.log(JSON.stringify(c.map(x=>C.esAutonomo(x))));")
        p = subprocess.run([NODE, '-e', script, json.dumps(casos)], cwd=MOTOR, capture_output=True, timeout=60)
        self.assertEqual(0, p.returncode, p.stderr.decode('utf-8', 'replace'))
        js = json.loads(p.stdout.decode('utf-8'))
        self.assertEqual([P.es_autonomo(x) for x in casos], js, dict(zip(casos, js)))


class TestLosDatosLlevanLaEmpresa(unittest.TestCase):
    def setUp(self):
        self.raiz = os.path.join(tempfile.mkdtemp(prefix='emp08c2b_', dir=os.environ.get('P3_TMP') or None), uuid.uuid4().hex)
        os.makedirs(self.raiz)

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.raiz), ignore_errors=True)

    def ing(self, l):
        r = P.ingerir_lote(l, self.raiz, OBRAS, HOY, escribir=True, ahora=AHORA)
        self.assertTrue(r['ok'] and r['escrito'], r)
        return r

    def test_sin_empresas_las_filas_son_identicas_a_las_de_antes(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5), ('Txomin', 7.5)])]))
        filas = P.aplanar(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual(2, len(filas))
        for fila in filas:
            self.assertEqual({'fecha', 'ambito', 'nombre', 'horas', 'extra'}, set(fila), 'sin empresa no hay clave «empresa»')

    def test_con_empresa_la_fila_la_lleva_y_quien_no_la_tiene_no(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5), ('Txomin', 7.5)]), jor('garaje', '2026-10-22', [('Mikel', 2)])],
                      altas=['Mikel'], empresas=[{'nombre': 'Mikel', 'empresa': 'Manueles'}]))
        por = {}
        for fila in P.aplanar(self.raiz, OBRAS, 'olabeaga'):
            por.setdefault(fila['nombre'], []).append(fila.get('empresa'))
        self.assertEqual({'Mikel': ['Manueles', 'Manueles'], 'Txomin': [None]}, por, 'la empresa va en TODAS las filas de la persona (vivienda y garaje)')

    def test_la_empresa_sale_en_todas_las_obras_de_la_persona(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])], altas=['Mikel'], empresas=[{'nombre': 'Mikel', 'empresa': 'Manueles'}]))
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 4)])], obra='mungia'))
        self.assertEqual(['Manueles'], [f.get('empresa') for f in P.aplanar(self.raiz, OBRAS, 'mungia')], 'la empresa es de la persona, no de la obra')

    def test_cambiar_la_empresa_cambia_todas_sus_filas_antiguas(self):
        self.ing(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5)]), jor('vivienda', '2026-10-22', [('Mikel', 7.5)])],
                      altas=['Mikel'], empresas=[{'nombre': 'Mikel', 'empresa': 'Manueles'}]))
        self.ing(lote([], empresas=[{'nombre': 'Mikel', 'empresa': 'CATERSYSTEM'}]))
        self.assertEqual(['CATERSYSTEM', 'CATERSYSTEM'], [f.get('empresa') for f in P.aplanar(self.raiz, OBRAS, 'olabeaga')])
        self.ing(lote([], empresas=[{'nombre': 'Mikel', 'empresa': ''}]))
        self.assertTrue(all('empresa' not in f for f in P.aplanar(self.raiz, OBRAS, 'olabeaga')), 'quitar la empresa quita la clave')

    def test_el_estado_que_se_publica_lleva_la_empresa_en_las_jornadas(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5), ('Txomin', 7.5)])], altas=['Mikel'], empresas=[{'nombre': 'Mikel', 'empresa': 'Manueles'}]))
        js = P.exportar_estado(self.raiz, OBRAS, generado='2026-10-26T20:00:00+01:00')
        datos = json.loads(js[len('window.SAGARDE_PERSONAL = '):].rstrip(';\n'))
        jornadas = datos['obras']['olabeaga']['jornadas']
        self.assertEqual({'Mikel': 'Manueles', 'Txomin': None}, {f['nombre']: f.get('empresa') for f in jornadas})

    def test_el_estado_sin_empresas_no_cambia_ni_un_byte_en_las_jornadas(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5), ('Txomin', 7.5)])]))
        js = P.exportar_estado(self.raiz, OBRAS, generado='2026-10-26T20:00:00+01:00')
        self.assertNotIn('"empresa": "', js.split('"jornadas"')[1], 'las jornadas no llevan empresa si nadie la tiene')


class TestLaPestanaYElInformeAceptanLaEmpresa(unittest.TestCase):
    FILA = {'fecha': '2026-10-22', 'ambito': 'vivienda', 'nombre': 'Ana', 'horas': 7.5, 'extra': 0}

    def test_una_fila_con_empresa_se_acepta_y_va_en_los_datos(self):
        for funcion in (PP.vista_personal, PP.informe_personal):
            html = funcion('olabeaga', [dict(self.FILA, empresa='Manueles'), dict(self.FILA, nombre='Beto', empresa=None)])
            self.assertIn('"empresa":"Manueles"', html)
            self.assertIn('htmlPorEmpresa', html, 'el cálculo del bloque va dentro de la página')

    def test_una_empresa_que_no_es_texto_se_rechaza_con_su_fila(self):
        for malo in (5, ['Manueles'], True, {'a': 1}):
            with self.assertRaises(ValueError) as cm:
                PP.vista_personal('olabeaga', [dict(self.FILA, empresa=malo)])
            self.assertIn('Fila 1', str(cm.exception))
            self.assertIn('empresa', str(cm.exception))

    def test_una_clave_desconocida_se_sigue_rechazando(self):
        with self.assertRaises(ValueError):
            PP.informe_personal('olabeaga', [dict(self.FILA, empres='Manueles')])

    def test_la_empresa_con_html_no_rompe_el_script(self):
        html = PP.informe_personal('olabeaga', [dict(self.FILA, empresa='</script><b>x</b>')])
        self.assertNotIn('</script><b>', html)
        self.assertIn('\\u003c/script\\u003e', html)


class TestLosCuatroSitiosUsanLoMismo(unittest.TestCase):
    """Un sitio con su propia suma por empresa sería el fallo de siempre: dos sitios que dicen cosas distintas."""
    SITIOS = ('panel_personal.py', 'personal_sagarde.html', 'generador_personal.html')

    def test_cada_sitio_llama_al_mismo_calculo_y_al_mismo_bloque(self):
        for nombre in self.SITIOS:
            texto = leer(nombre)
            self.assertIn('agregarPorEmpresa(', texto, nombre)
            self.assertIn('htmlPorEmpresa(', texto, nombre)
        self.assertEqual(2, leer('panel_personal.py').count('htmlPorEmpresa('), 'la pestaña y el informe')

    def test_ningun_sitio_escribe_su_propio_bloque(self):
        for nombre in self.SITIOS:
            texto = leer(nombre)
            self.assertNotRegex(texto, r'>Por empresa<', nombre + ': el título «Por empresa» solo vive en personal_calculo.js')
            self.assertNotIn('Total autónomos', texto, nombre + ': la línea de autónomos solo vive en personal_calculo.js')
            self.assertNotRegex(texto, r'<\w+[^>]*data-por-empresa', nombre + ': el bloque lo escribe personal_calculo.js')
        calculo = leer('personal_calculo.js')
        self.assertIn('Por empresa', calculo)
        self.assertIn('Total autónomos (@AUT)', calculo)

    def test_la_pestana_y_el_informe_dan_las_clases_de_cada_uno(self):
        texto = leer('panel_personal.py')
        self.assertIn("bloque: 'pers-bloque-empresa'", texto)
        self.assertIn("bloque: 'pinf-bloque-empresa'", texto)

    def test_el_ranking_suma_las_filas_de_todas_las_obras_del_periodo(self):
        texto = leer('personal_sagarde.html')
        self.assertIn("PersonalCalculo.filtrar(filas, { periodo: periodo, ref: ref })", texto,
                      'el bloque del ranking parte de las mismas filas que el ranking de personas (todas las obras)')

    def test_el_calculo_publica_las_funciones_nuevas(self):
        calculo = leer('personal_calculo.js')
        for nombre in ('agregarPorEmpresa', 'esAutonomo', 'textoAvisoEmpresas', 'htmlPorEmpresa'):
            self.assertRegex(calculo, r'\n\s+' + nombre + r'[,\r\n]', nombre + ' va en la API')

    def test_las_dos_reglas_de_autonomo_dicen_lo_mismo_en_el_codigo(self):
        self.assertIn(r'@\s*aut$', leer('personal_obra.py'))
        self.assertIn(r'@\s*aut$', leer('personal_calculo.js'))


def _hay_chromium():
    if os.environ.get('SAGARDE_SIN_NAVEGADOR') == '1':
        return False, 'saltada a propósito (SAGARDE_SIN_NAVEGADOR=1)'
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True, ''
    except Exception as exc:  # noqa: BLE001
        return False, 'Playwright no puede abrir Chromium (%s)' % type(exc).__name__


_OK, _MOTIVO = _hay_chromium()


@unittest.skipUnless(_OK, 'NO se ha comprobado el desglose por empresa en el navegador: %s' % _MOTIVO)
class TestLosCuatroSitiosDicenLoMismoEnElNavegador(unittest.TestCase):
    def test_pestana_informe_ranking_y_tablet_coinciden_con_el_calculo_a_mano(self):
        env = dict(os.environ, PYTHONUTF8='1')
        p = subprocess.run([sys.executable, os.path.join(MOTOR, 'tests', 'verificar_empresas_cuatro_sitios.py'), MOTOR],
                           cwd=MOTOR, capture_output=True, timeout=600, env=env)
        salida = (p.stdout + p.stderr).decode('utf-8', 'replace')
        self.assertEqual(0, p.returncode, chr(10).join(salida.splitlines()[-25:]))
        self.assertIn('OK: pestaña, informe, ranking y tablet', salida)


if __name__ == '__main__':
    unittest.main()
