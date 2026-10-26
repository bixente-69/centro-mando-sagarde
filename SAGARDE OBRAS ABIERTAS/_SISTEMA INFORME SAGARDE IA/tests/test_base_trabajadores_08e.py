# -*- coding: utf-8 -*-
"""Pruebas del paso 08e: la pestaña «Base de trabajadores» del ranking. Datos INVENTADOS. unittest de la biblioteca estándar.

Qué cubre:
  · Los datos: el estado que se publica (personal_estado.js) lleva el historial de nombres de cada persona (renombres y
    fusiones) SOLO si lo hay; quien nunca cambió de nombre se publica exactamente igual que antes.
  · El cálculo (personal_calculo.js): el verificador de node con cifras a mano, en tres zonas horarias.
  · La página: usa el cálculo compartido (no suma nada por su cuenta) y es de solo lectura.
  · El navegador: el script `verificar_base_trabajadores.py` (tabla, buscador, orden, pestañas, móvil, avisos y mensajes),
    que la tablet —que lee el mismo personal_estado.js— sigue funcionando con los campos nuevos, y que ningún texto de la
    pestaña lleva palabras de programador."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

TESTS = os.path.dirname(os.path.abspath(__file__))
MOTOR = os.environ.get('PERSONAL_MOTOR') or os.path.dirname(TESTS)
sys.path.insert(0, MOTOR)
sys.path.insert(0, TESTS)
import datos_base_trabajadores as D  # noqa: E402
import personal_obra as P  # noqa: E402

NODE = shutil.which('node')
OBRAS = {'olabeaga': '2026 OLABEAGA BILBAO', 'mungia': '2026 MUNGIA ACR NEINOR'}
HOY = '2026-10-26'
AHORA = '2026-10-26T20:00:00+01:00'
FICHA = ['id', 'nombre', 'categoria', 'empresa', 'activo']


def leer(nombre):
    with open(os.path.join(MOTOR, nombre), encoding='utf-8') as fh:
        return fh.read()


def jor(ambito, fecha, presentes):
    return {'ambito': ambito, 'fecha': fecha, 'presentes': [{'nombre': n, 'horas': h, 'extra': 0} for n, h in presentes]}


def lote(jornadas, obra='olabeaga', **kw):
    d = {'tipo': 'lote_personal', 'version': 1, 'obra': obra, 'jornadas': jornadas}
    d.update(kw)
    return d


class TestElEstadoLlevaElHistorialDeNombres(unittest.TestCase):
    def setUp(self):
        self.raiz = os.path.join(tempfile.mkdtemp(prefix='base08e_', dir=os.environ.get('P3_TMP') or None), uuid.uuid4().hex)
        os.makedirs(self.raiz)

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.raiz), ignore_errors=True)

    def ing(self, datos):
        r = P.ingerir_lote(datos, self.raiz, OBRAS, HOY, escribir=True, ahora=AHORA)
        self.assertTrue(r['ok'] and r['escrito'], r)
        return r

    def juntar(self, origen, destino):
        r = P.fusionar(self.raiz, origen, destino, escribir=True, ahora=AHORA)
        self.assertTrue(r['ok'], r)

    def catalogo(self):
        js = P.exportar_estado(self.raiz, OBRAS, generado=AHORA)
        return json.loads(js[len('window.SAGARDE_PERSONAL = '):].rstrip(';\n'))['catalogo']

    def test_quien_nunca_cambio_de_nombre_se_publica_como_siempre(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        cat = self.catalogo()
        self.assertEqual(1, len(cat))
        self.assertEqual(FICHA, list(cat[0]), 'ni nombres_anteriores ni fusionados si no hay historial (la tablet lee este mismo fichero)')

    def test_un_renombre_publica_los_nombres_de_antes(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        self.ing(lote([], renombres=[{'de': 'Mikel', 'a': 'Mikel Etxeberria'}]))
        ficha = self.catalogo()[0]
        self.assertEqual(('Mikel Etxeberria', ['Mikel']), (ficha['nombre'], ficha['nombres_anteriores']))
        self.assertNotIn('fusionados', ficha)
        self.assertEqual(FICHA + ['nombres_anteriores'], list(ficha))

    def test_dos_renombres_seguidos_los_publican_todos(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        self.ing(lote([], renombres=[{'de': 'Mikel', 'a': 'Mikel E.'}]))
        self.ing(lote([], renombres=[{'de': 'Mikel E.', 'a': 'Mikel Etxeberria'}]))
        self.assertEqual(['Mikel', 'Mikel E.'], self.catalogo()[0]['nombres_anteriores'])

    def test_una_fusion_publica_el_nombre_de_la_ficha_juntada_y_ya_no_sale_como_persona(self):
        self.ing(lote([], altas=['Beto', 'Beto B']))
        self.juntar('T0002', 'T0001')
        cat = self.catalogo()
        self.assertEqual(['Beto'], [x['nombre'] for x in cat], 'la ficha fusionada no es una persona más')
        self.assertEqual(['Beto B'], cat[0]['fusionados'])
        self.assertNotIn('nombres_anteriores', cat[0])
        self.assertEqual(FICHA + ['fusionados'], list(cat[0]))

    def test_fusiones_en_cadena_van_a_la_persona_que_sigue_vigente(self):
        self.ing(lote([], altas=['A', 'B', 'C']))
        self.juntar('T0003', 'T0002')    # C dentro de B
        self.juntar('T0002', 'T0001')    # B dentro de A (y con ella, C)
        cat = self.catalogo()
        self.assertEqual(['A'], [x['nombre'] for x in cat])
        self.assertEqual(['B', 'C'], cat[0]['fusionados'], 'por orden de ficha; C también cuenta aunque se juntara antes con B')

    def test_renombrada_y_con_fichas_juntadas_lleva_las_dos_cosas(self):
        self.ing(lote([], altas=['Beto', 'Beto B']))
        self.ing(lote([], renombres=[{'de': 'Beto', 'a': 'Alberto'}]))
        self.juntar('T0002', 'T0001')
        ficha = self.catalogo()[0]
        self.assertEqual(FICHA + ['nombres_anteriores', 'fusionados'], list(ficha))
        self.assertEqual((['Beto'], ['Beto B']), (ficha['nombres_anteriores'], ficha['fusionados']))

    def test_el_resto_del_estado_no_cambia(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5), ('Txomin', 7.5)])]))
        antes = json.loads(P.exportar_estado(self.raiz, OBRAS, generado=AHORA)[len('window.SAGARDE_PERSONAL = '):].rstrip(';\n'))
        self.ing(lote([], renombres=[{'de': 'Mikel', 'a': 'Mikel E.'}]))
        despues = json.loads(P.exportar_estado(self.raiz, OBRAS, generado=AHORA)[len('window.SAGARDE_PERSONAL = '):].rstrip(';\n'))
        for clave in ('version', 'jornada_base_h'):
            self.assertEqual(antes[clave], despues[clave])
        self.assertEqual([x['nombre'] for x in antes['obras']['olabeaga']['jornadas']], ['Mikel', 'Txomin'])
        self.assertEqual([x['nombre'] for x in despues['obras']['olabeaga']['jornadas']], ['Mikel E.', 'Txomin'],
                         'las jornadas llevan el nombre de ahora (el historial va aparte, en el catálogo)')


@unittest.skipUnless(NODE, 'falta node en el PATH: NO se ha probado el cálculo de la base (personal_calculo.js)')
class TestCalculoDeLaBase(unittest.TestCase):
    def test_verificador_de_node_en_tres_zonas_horarias(self):
        p = subprocess.run([NODE, os.path.join(TESTS, 'verificar_personal_base.js')], cwd=MOTOR, capture_output=True, timeout=300)
        salida = (p.stdout + p.stderr).decode('utf-8', 'replace')
        self.assertEqual(0, p.returncode, '\n'.join(salida.splitlines()[-25:]))
        self.assertNotIn('FALLO', salida)
        self.assertEqual(3, len(re.findall(r'comprobaciones, 0 fallos', salida)), 'tres pasadas (local y dos zonas extremas):\n' + salida[-600:])

    def test_el_cuadro_no_se_cae_con_datos_rotos(self):
        script = ("const C=require('./personal_calculo.js');"
                  "const raros=[undefined,null,5,'x',{},[null],[{}],[5],[[]]];let n=0;"
                  "for(const f of raros)for(const c of raros){const r=C.baseTrabajadores(f,c);"
                  "if(!r||!Array.isArray(r.personas)||!r.total||!r.avisos)throw new Error('forma rota');n++;}"
                  "console.log(n);")
        p = subprocess.run([NODE, '-e', script], cwd=MOTOR, capture_output=True, timeout=60)
        self.assertEqual(0, p.returncode, p.stderr.decode('utf-8', 'replace'))
        self.assertEqual('81', p.stdout.decode('utf-8').strip(), 'se probaron las 81 combinaciones')


class TestLaPaginaUsaElCalculoCompartido(unittest.TestCase):
    def test_la_pagina_llama_al_calculo_y_no_suma_nada_por_su_cuenta(self):
        pagina = leer('personal_sagarde.html')
        for llamada in ('PersonalCalculo.baseTrabajadores(', 'PersonalCalculo.ordenarBase(', 'PersonalCalculo.claveNombre('):
            self.assertIn(llamada, pagina)
        self.assertNotRegex(pagina, r'\.horas\s*\+=|\.dias\s*\+=|\.reduce\(', 'las cifras de la base salen de personal_calculo.js')

    def test_es_de_solo_lectura(self):
        pagina = leer('personal_sagarde.html')
        self.assertNotRegex(pagina, r'fetch\(|XMLHttpRequest|sendBeacon|localStorage|sessionStorage|<form|<textarea|contenteditable',
                            'la base se mira, no se cambia desde el portal (los cambios entran con «actualiza la obra»)')

    def test_el_calculo_publica_las_funciones_nuevas(self):
        calculo = leer('personal_calculo.js')
        for nombre in ('claveNombre', 'baseTrabajadores', 'ordenarBase'):
            self.assertRegex(calculo, r'\n\s+' + nombre + r'[,\r\n]', nombre + ' va en la API')

    def test_ya_no_queda_la_palabra_ingerir_en_lo_que_se_lee(self):
        self.assertNotRegex(leer('personal_sagarde.html').lower(), r'ingier|ingest|ingerir')


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


@unittest.skipUnless(_OK, 'NO se ha comprobado la pestaña en el navegador: %s' % _MOTIVO)
class TestLaPestanaEnElNavegador(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.join(tempfile.mkdtemp(prefix='base08e_nav_', dir=os.environ.get('P3_TMP') or None), uuid.uuid4().hex)
        os.makedirs(self.tmp)

    def tearDown(self):
        shutil.rmtree(os.path.dirname(self.tmp), ignore_errors=True)

    def carpeta(self, estado, pagina):
        d = os.path.join(self.tmp, uuid.uuid4().hex[:6])
        os.makedirs(d)
        for nombre in (pagina, 'personal_calculo.js'):
            shutil.copy(os.path.join(MOTOR, nombre), d)
        with open(os.path.join(d, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
            fh.write('window.SAGARDE_PERSONAL = ' + json.dumps(estado, ensure_ascii=False) + ';\n')
        return 'file:///' + os.path.join(d, pagina).replace('\\', '/').replace(' ', '%20')

    def test_el_script_de_navegador_de_la_base_pasa(self):
        script = os.path.join(TESTS, 'verificar_base_trabajadores.py')
        self.assertTrue(os.path.isfile(script), 'falta tests/verificar_base_trabajadores.py')
        p = subprocess.run([sys.executable, script, MOTOR], cwd=MOTOR, capture_output=True, timeout=600,
                           env=dict(os.environ, PYTHONUTF8='1'))
        salida = (p.stdout + p.stderr).decode('utf-8', 'replace')
        self.assertEqual(0, p.returncode, '\n'.join(salida.splitlines()[-25:]))
        self.assertTrue(salida.strip().splitlines()[-1].startswith('OK: base de trabajadores'), salida[-300:])

    def test_la_tablet_sigue_funcionando_con_los_campos_nuevos_del_estado(self):
        """La tablet lee el mismo personal_estado.js: las claves nombres_anteriores y fusionados no la rompen."""
        from playwright.sync_api import sync_playwright
        estado = json.loads(json.dumps(D.ESTADO_PRINCIPAL))
        estado['catalogo'] = [x for x in estado['catalogo'] if x['nombre'] != D.ZOE]
        for o in estado['obras'].values():
            o['jornadas'] = [x for x in o['jornadas'] if x['nombre'] != D.ZOE]
        self.assertTrue(any('nombres_anteriores' in x for x in estado['catalogo']) and any('fusionados' in x for x in estado['catalogo']))
        url = self.carpeta(estado, 'generador_personal.html')
        with sync_playwright() as p:
            nav = p.chromium.launch()
            pg = nav.new_page(viewport={'width': 820, 'height': 1000})
            errores = []
            pg.on('pageerror', lambda e: errores.append(str(e)))
            pg.on('console', lambda m: errores.append(m.text) if m.type == 'error' else None)
            pg.goto(url)
            pg.wait_for_selector('#obra', timeout=5000)
            pg.select_option('#obra', 'olabeaga')
            opciones = pg.eval_on_selector_all('#addsel option', 'o=>o.map(x=>x.textContent.trim().replace(/ \\(ya está\\)$/, ""))')
            nav.close()
        self.assertEqual([], errores, 'la tablet no debe dar errores con claves de más en el catálogo')
        self.assertEqual(['Ana', 'Beto', 'Carla Ruiz', 'Dani'], sorted(opciones),
                         'sale toda la base activa, sin la persona de baja ni la ficha juntada («Beto B»)')

    def test_ningun_texto_de_la_pestana_lleva_palabras_de_programador(self):
        from playwright.sync_api import sync_playwright
        from test_lenguaje_electricista import revisar
        textos = []
        with sync_playwright() as p:
            nav = p.chromium.launch()
            casos = [(D.ESTADO_PRINCIPAL, True)] + [(e['estado'], e['con_calculo']) for e in D.ESCENARIOS if e['estado'] is not None]
            for estado, con_calculo in casos:
                d = os.path.join(self.tmp, uuid.uuid4().hex[:6])
                os.makedirs(d)
                shutil.copy(os.path.join(MOTOR, 'personal_sagarde.html'), d)
                if con_calculo:
                    shutil.copy(os.path.join(MOTOR, 'personal_calculo.js'), d)
                with open(os.path.join(d, 'personal_estado.js'), 'w', encoding='utf-8') as fh:
                    fh.write('window.SAGARDE_PERSONAL = ' + json.dumps(estado, ensure_ascii=False) + ';\n')
                pg = nav.new_page(viewport={'width': 1000, 'height': 900})
                pg.goto('file:///' + os.path.join(d, 'personal_sagarde.html').replace('\\', '/').replace(' ', '%20'))
                pg.wait_for_function("!document.getElementById('contenido-base').textContent.includes('Cargando')", timeout=5000)
                textos += pg.eval_on_selector_all('#pestanas button, #vista-base h2, #vista-base .intro, #contenido-base th, '
                                                  '#contenido-base .aviso, #contenido-base .empty, #contenido-base .nota, '
                                                  '#contenido-base .kpi span, #contenido-base .chip, #contenido-base .sinj, '
                                                  '#contenido-base button, #contenido-base .cuenta, #contenido-base .b-hist',
                                                  'e=>e.map(x=>x.textContent)')
                textos += [pg.get_attribute('#buscar', 'placeholder') or ''] if pg.query_selector('#buscar') else []
                pg.close()
            nav.close()
        textos = [t for t in textos if t.strip()]
        self.assertGreater(len(set(textos)), 25, 'un recuento bajo de textos revisados es una alarma, no un «no aplica»')
        self.assertEqual([], revisar(textos, 'Base de trabajadores'))


if __name__ == '__main__':
    unittest.main()
