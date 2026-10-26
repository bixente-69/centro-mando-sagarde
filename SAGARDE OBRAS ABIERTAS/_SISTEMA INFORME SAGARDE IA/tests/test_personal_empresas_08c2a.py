# -*- coding: utf-8 -*-
"""Pruebas del paso 08c2a sobre el campo Empresa de P1 (personal_obra.py) y del lector (lector_control_horario.py):
`es_autonomo`, la clave `empresas` del fichero, `poner_empresa`, `separar_empresas`, la línea de comandos, `comprobar`
y los textos en llano. Datos INVENTADOS. unittest de la biblioteca estándar. Las pruebas de 08a y 08b no se tocan
(salvo la lista de códigos con frase en llano, que se amplía a propósito con los dos códigos nuevos)."""
import contextlib
import copy
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import uuid

MOTOR = os.environ.get('PERSONAL_MOTOR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MOTOR)
import lector_control_horario as L
import personal_integracion as PI
import personal_obra as P

TMP = None
_TMP_OBJ = None
OBRAS = {'olabeaga': '2026 OLABEAGA BILBAO', 'mungia': '2026 MUNGIA ACR NEINOR'}
HOY = '2026-10-26'
AHORA = '2026-10-26T20:00:00+01:00'
SHA1 = 'a' * 64
PALABRAS = re.compile(r'\b(exportar|exportad\w*|importar|importad\w*|lotes?|ingerir|ingesta|json|pendientes?|alta|altas|'
                      r'simulaci\w+|estado|base de datos)\b', re.I)


def jor(ambito, fecha, presentes, **kw):
    d = {'ambito': ambito, 'fecha': fecha,
         'presentes': [{'nombre': n, 'horas': h, 'extra': 0} for n, h in presentes]}
    d.update(kw)
    return d


def lote(jornadas, obra='olabeaga', **kw):
    d = {'tipo': 'lote_personal', 'version': 1, 'obra': obra, 'jornadas': jornadas}
    d.update(kw)
    return d


def emp(nombre, empresa):
    return {'nombre': nombre, 'empresa': empresa}


# Mikel T0001, Txomin T0002, Andoni T0003
L1 = lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5), ('Txomin', 7.5)]), jor('garaje', '2026-10-22', [('Andoni', 7.5)])])


class Base(unittest.TestCase):
    def setUp(self):
        self.raiz = os.path.join(TMP, uuid.uuid4().hex)
        os.makedirs(self.raiz)

    def tearDown(self):
        shutil.rmtree(self.raiz, ignore_errors=True)

    def ing(self, l, escribir=False, **kw):
        return P.ingerir_lote(copy.deepcopy(l), self.raiz, OBRAS, HOY, escribir=escribir, ahora=AHORA, **kw)

    def sembrar(self, l=L1):
        r = self.ing(l, escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)
        return r

    def hashes(self):
        out = {}
        for d, _, fs in os.walk(self.raiz):
            for f in fs:
                with open(os.path.join(d, f), 'rb') as fh:
                    out[os.path.relpath(os.path.join(d, f), self.raiz).replace(os.sep, '/')] = hashlib.sha256(fh.read()).hexdigest()
        return out

    def traza(self, obra='olabeaga'):
        p = os.path.join(self.raiz, OBRAS[obra], 'INFORME SAGARDE IA', 'personal_jornadas.jsonl')
        if not os.path.exists(p):
            return []
        with open(p, encoding='utf-8') as fh:
            return [json.loads(x) for x in fh.read().splitlines()]

    def lineas_empresa(self, obra='olabeaga'):
        return [x for x in self.traza(obra) if x['accion'] == 'empresa']

    def cat(self):
        return P.cargar_catalogo(self.raiz)

    def persona(self, i):
        return next(t for t in self.cat()['trabajadores'] if t['id'] == i)

    def empresas(self):
        return {t['nombre']: t.get('empresa') for t in self.cat()['trabajadores'] if t.get('fusionado_en') is None}

    def rechazado(self, l, codigo):
        antes = self.hashes()
        r = self.ing(l, escribir=True)
        self.assertFalse(r['ok'], r)
        self.assertIn(codigo, r['lote_rechazado'])
        self.assertEqual(r['jornadas'], [])
        self.assertEqual(self.hashes(), antes, 'un fichero rechazado no escribe ni un byte')


class TestAutonomoYValidez(unittest.TestCase):
    def test_es_autonomo(self):
        for si in ('Javi @AUT', 'Javi@aut', 'javi @ Aut', 'X  @AUT', '@AUT', '  Javi @AUT  ', 'Ana María @aut'):
            self.assertTrue(P.es_autonomo(si), si)
        for no in ('Javi AUT', 'Javi @AUTO', 'Manueles', '', None, 'AUT', 'Javi @AUT Obras', 7, ['@AUT'], 'AUT@'):
            self.assertFalse(P.es_autonomo(no), repr(no))

    def test_empresa_valida(self):
        for si in ('', '   ', 'Manueles', 'Javi @AUT', 'CATERSYSTEM', 'Construcciones Muñoz (Bilbao)', 'x' * 60):
            self.assertTrue(P.empresa_valida(si), repr(si))
        for no in ('x' * 61, '12345678Z', '612 345 678', 'ana@empresa.com', '<b>', 'a>b', None, 5, ['Manueles'], 'Ma\x00'):
            self.assertFalse(P.empresa_valida(no), repr(no))

    def test_claves_nuevas(self):
        self.assertIn('empresas', P.LK)
        self.assertIn('empresa', P.TK)


class TestEsquema(Base):
    def test_empresas_mal_escritas_rechazan_el_fichero_entero(self):
        malos = [
            'no es una lista', {'nombre': 'Mikel', 'empresa': 'X'}, ['Mikel'], [5], [emp('Mikel', 'X'), 'Y'],
            [{'nombre': 'Mikel'}], [{'empresa': 'X'}], [{'nombre': 'Mikel', 'empresa': 'X', 'otra': 1}],
            [emp('', 'X')], [emp('  ', 'X')], [emp(None, 'X')], [emp('Mikel', None)], [emp('Mikel', 5)],
            [emp('Mikel', ['X'])], [emp('Mikel', 'x' * 61)], [emp('Mikel', '12345678Z')], [emp('Mikel', '612 345 678')],
            [emp('Mikel', 'ana@empresa.com')], [emp('Mikel', '<b>')], [emp('12345678Z', 'X')], [emp('<i>', 'X')],
        ]
        for m in malos:
            self.rechazado(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])], empresas=m), 'empresa_invalida')

    def test_empresa_vacia_vale(self):
        self.sembrar()
        r = self.ing(lote([], empresas=[emp('Mikel', ''), emp('Txomin', '   ')]), escribir=True)
        self.assertTrue(r['ok'], r)

    def test_sin_empresas_el_fichero_se_comporta_como_antes(self):
        r = self.ing(L1, escribir=True)
        self.assertEqual(r['empresas'], [])
        self.assertEqual(r['avisos_lote'], [])
        self.assertEqual(self.lineas_empresa(), [])
        for t in self.cat()['trabajadores']:
            self.assertEqual(set(t), {'id', 'nombre', 'categoria', 'empresa', 'activo', 'alta', 'fusionado_en'})
            self.assertEqual(t['empresa'], '')
        r = self.ing(lote([], empresas=[]), escribir=True)
        self.assertTrue(r['ok'])
        self.assertFalse(r['escrito'])

    def test_fichero_rechazado_trae_la_clave_vacia(self):
        self.assertEqual(self.ing({'tipo': 'otra_cosa'})['empresas'], [])


class TestAplicar(Base):
    def test_poner_la_empresa_a_alguien_que_ya_esta(self):
        self.sembrar()
        antes = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        r = self.ing(lote([], empresas=[emp('Mikel', 'Manueles')]), escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)
        self.assertEqual(r['empresas'], [{'nombre': 'Mikel', 'id': 'T0001', 'accion': 'puesta', 'antes': '', 'despues': 'Manueles'}])
        self.assertEqual(self.persona('T0001')['empresa'], 'Manueles')
        self.assertEqual(self.persona('T0002')['empresa'], '')
        ult = self.traza()[-1]
        self.assertEqual((ult['accion'], ult['id'], ult['nombre'], ult['de'], ult['a'], ult['ts']),
                         ('empresa', 'T0001', 'Mikel', '', 'Manueles', AHORA))
        self.assertEqual(P.cargar_obra(self.raiz, OBRAS, 'olabeaga'), antes, 'no se toca ninguna jornada')
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])

    def test_cambiarla_y_quitarla(self):
        self.sembrar()
        self.ing(lote([], empresas=[emp('Mikel', 'Manueles')]), escribir=True)
        r = self.ing(lote([], empresas=[emp('Mikel', 'Catersystem')]), escribir=True)
        self.assertEqual((r['empresas'][0]['accion'], r['empresas'][0]['antes'], r['empresas'][0]['despues']),
                         ('cambiada', 'Manueles', 'Catersystem'))
        r = self.ing(lote([], empresas=[emp('Mikel', '')]), escribir=True)
        self.assertEqual((r['empresas'][0]['accion'], r['empresas'][0]['antes'], r['empresas'][0]['despues']),
                         ('quitada', 'Catersystem', ''))
        self.assertEqual(self.persona('T0001')['empresa'], '')
        self.assertEqual([(x['de'], x['a']) for x in self.lineas_empresa()],
                         [('', 'Manueles'), ('Manueles', 'Catersystem'), ('Catersystem', '')])

    def test_lo_mismo_otra_vez_no_toca_nada(self):
        self.sembrar()
        self.ing(lote([], empresas=[emp('Mikel', 'Manueles')]), escribir=True)
        h = self.hashes()
        r = self.ing(lote([], empresas=[emp('Mikel', 'Manueles'), emp('Txomin', '')]), escribir=True)
        self.assertEqual([x['accion'] for x in r['empresas']], ['sin_cambios', 'sin_cambios'])
        self.assertFalse(r['escrito'])
        self.assertEqual(self.hashes(), h)

    def test_una_empresa_se_guarda_con_la_grafia_de_la_primera_vez(self):
        self.sembrar()
        self.ing(lote([], empresas=[emp('Mikel', 'Construcciones Muñoz')]), escribir=True)
        r = self.ing(lote([], empresas=[emp('Txomin', 'CONSTRUCCIONES MUNOZ'), emp('Mikel', 'construcciones munoz')]),
                     escribir=True)
        self.assertEqual(self.persona('T0002')['empresa'], 'Construcciones Muñoz')
        self.assertEqual(self.persona('T0001')['empresa'], 'Construcciones Muñoz', 'otra grafía de la misma: sin cambios')
        self.assertEqual([x['accion'] for x in r['empresas']], ['puesta', 'sin_cambios'])
        self.assertEqual(len(self.lineas_empresa()), 2)

    def test_para_alguien_que_no_existe_se_avisa_y_no_se_crea_a_nadie(self):
        self.sembrar()
        h = self.hashes()
        r = self.ing(lote([], empresas=[emp('Fantasma', 'Manueles')]), escribir=True)
        self.assertTrue(r['ok'])
        self.assertEqual(r['empresas'][0]['accion'], 'sin_persona')
        self.assertEqual(r['empresas'][0]['id'], None)
        self.assertEqual([a['codigo'] for a in r['avisos_lote']], ['empresa_sin_persona'])
        self.assertEqual(r['avisos_lote'][0]['detalle'], 'Fantasma')
        self.assertEqual(len(self.cat()['trabajadores']), 3)
        self.assertEqual(self.hashes(), h)

    def test_orden_altas_antes_que_empresas(self):
        self.sembrar()
        r = self.ing(lote([], altas=['Nuevo'], empresas=[emp('Nuevo', 'Manueles')]), escribir=True)
        self.assertEqual(self.empresas()['Nuevo'], 'Manueles')
        self.assertEqual(r['empresas'][0]['accion'], 'puesta')

    def test_orden_renombres_antes_que_empresas(self):
        self.sembrar()
        self.ing(lote([], renombres=[{'de': 'Mikel', 'a': 'Mikel Etxeberria'}],
                      empresas=[emp('Mikel Etxeberria', 'Manueles')]), escribir=True)
        self.assertEqual(self.persona('T0001')['nombre'], 'Mikel Etxeberria')
        self.assertEqual(self.persona('T0001')['empresa'], 'Manueles')

    def test_orden_empresas_antes_que_jornadas(self):
        """Quien solo existe porque lo crea una jornada de este mismo fichero aún no está: se avisa (la tablet
        manda en `altas` a quien lleva empresa)."""
        self.sembrar()
        l = lote([jor('vivienda', '2026-10-23', [('Nuevo', 7.5)])], empresas=[emp('Nuevo', 'Manueles')])
        r = self.ing(l, escribir=True)
        self.assertEqual(r['empresas'][0]['accion'], 'sin_persona')
        self.assertEqual(self.empresas()['Nuevo'], '')

    def test_con_el_nombre_antiguo_vale_y_avisa(self):
        self.sembrar()
        self.ing(lote([], renombres=[{'de': 'Mikel', 'a': 'Mikel Etxeberria'}]), escribir=True)
        r = self.ing(lote([], empresas=[emp('Mikel', 'Manueles')]), escribir=True)
        self.assertEqual(self.persona('T0001')['empresa'], 'Manueles')
        self.assertEqual(r['empresas'][0]['nombre'], 'Mikel Etxeberria')
        self.assertEqual([(a['codigo'], a['detalle']) for a in r['avisos_lote']],
                         [('nombre_anterior_usado', 'Mikel -> Mikel Etxeberria')])

    def test_dos_lineas_para_la_misma_persona_gana_la_ultima(self):
        self.sembrar()
        r = self.ing(lote([], empresas=[emp('Mikel', 'A'), emp('Mikel', 'B')]), escribir=True)
        self.assertEqual([x['accion'] for x in r['empresas']], ['puesta', 'cambiada'])
        self.assertEqual(self.persona('T0001')['empresa'], 'B')
        self.assertEqual(len(self.lineas_empresa()), 2)

    def test_una_persona_juntada_con_otra_recibe_la_empresa_en_la_vigente(self):
        self.sembrar()
        self.assertTrue(P.fusionar(self.raiz, 'T0003', 'T0001', escribir=True)['ok'])
        r = self.ing(lote([], empresas=[emp('Andoni', 'Manueles')]), escribir=True)
        self.assertEqual(r['empresas'][0]['id'], 'T0001')
        self.assertEqual(self.persona('T0001')['empresa'], 'Manueles')
        self.assertEqual(self.persona('T0003')['empresa'], '')

    def test_la_vista_previa_no_escribe_y_en_memoria_da_lo_mismo(self):
        self.sembrar()
        h = self.hashes()
        l = lote([], empresas=[emp('Mikel', 'Manueles'), emp('Txomin', 'Manueles')])
        prev = self.ing(l)
        self.assertEqual(self.hashes(), h)
        estado = P.cargar_estado(self.raiz, OBRAS)
        mem = P.ingerir_lote(copy.deepcopy(l), self.raiz, OBRAS, HOY, ahora=AHORA, estado=estado)
        self.assertEqual(mem['empresas'], prev['empresas'])
        self.assertEqual({t['nombre']: t['empresa'] for t in estado['cat']['trabajadores']},
                         {'Mikel': 'Manueles', 'Txomin': 'Manueles', 'Andoni': ''})
        self.assertEqual(self.hashes(), h)

    def test_con_sha_un_fichero_solo_de_empresas_deja_su_linea_y_la_de_recibido(self):
        self.sembrar()
        self.ing(lote([], empresas=[emp('Mikel', 'Manueles')]), escribir=True, sha256=SHA1, fichero='CONTROL HORARIO X.json')
        acciones = [x['accion'] for x in self.traza()[-2:]]
        self.assertEqual(acciones, ['empresa', 'recibido'])
        self.assertTrue(all(x['sha256'] == SHA1 for x in self.traza()[-2:]))

    def test_se_aplica_aunque_se_rechace_una_jornada(self):
        self.sembrar()
        mala = jor('vivienda', '2026-13-45', [('Mikel', 7.5)])
        r = self.ing(lote([mala], empresas=[emp('Mikel', 'Manueles')]), escribir=True)
        self.assertFalse(r['ok'])
        self.assertEqual(self.persona('T0001')['empresa'], 'Manueles')

    def test_los_autonomos_se_guardan_tal_cual(self):
        self.sembrar()
        self.ing(lote([], empresas=[emp('Mikel', 'Mikel @AUT'), emp('Txomin', 'Txomin@aut')]), escribir=True)
        self.assertEqual(self.empresas()['Mikel'], 'Mikel @AUT')
        self.assertTrue(P.es_autonomo(self.empresas()['Txomin']))

    def test_la_empresa_sale_en_el_estado_de_la_tablet(self):
        self.sembrar()
        self.ing(lote([], empresas=[emp('Mikel', 'Manueles')]), escribir=True)
        js = P.exportar_estado(self.raiz, OBRAS, generado='x')
        datos = json.loads(js[js.index('=') + 1:].rstrip().rstrip(';'))
        self.assertEqual({t['nombre']: t['empresa'] for t in datos['catalogo']},
                         {'Mikel': 'Manueles', 'Txomin': '', 'Andoni': ''})

    def test_las_lineas_de_la_traza_las_acepta_el_auditor(self):
        self.sembrar()
        self.ing(lote([], empresas=[emp('Mikel', 'Manueles'), emp('Mikel', '')]), escribir=True,
                 sha256=SHA1, fichero='CONTROL HORARIO X.json')
        lineas = self.lineas_empresa()
        self.assertEqual(len(lineas), 2)
        for x in self.traza():
            self.assertTrue(PI._traza_valida(x), x)

    def test_dos_grafias_ya_guardadas_de_la_misma_empresa_no_provocan_cambios(self):
        self.sembrar()
        cat = self.cat()
        cat['trabajadores'][0]['empresa'] = 'MANUELES'
        cat['trabajadores'][1]['empresa'] = 'Manueles'
        P.guardar_catalogo(self.raiz, cat)
        h = self.hashes()
        r = self.ing(lote([], empresas=[emp('Txomin', 'Manueles')]), escribir=True)
        self.assertEqual(r['empresas'][0]['accion'], 'sin_cambios', 'es la misma empresa aunque la base la tenga con dos grafías')
        self.assertEqual(self.hashes(), h)

    def test_la_empresa_de_una_persona_juntada_con_otra_ya_no_cuenta_para_la_grafia(self):
        self.sembrar()
        self.ing(lote([], empresas=[emp('Andoni', 'Vieja SL')]), escribir=True)
        self.assertTrue(P.fusionar(self.raiz, 'T0003', 'T0001', escribir=True)['ok'])
        self.ing(lote([], empresas=[emp('Txomin', 'VIEJA SL')]), escribir=True)
        self.assertEqual(self.persona('T0002')['empresa'], 'VIEJA SL', 'la única que tenía «Vieja SL» ya no es una persona de la base')

    def test_una_persona_de_la_base_sin_el_campo_empresa_tambien_la_recibe(self):
        self.sembrar()
        cat = self.cat()
        del cat['trabajadores'][0]['empresa']
        P.guardar_catalogo(self.raiz, cat)
        r = self.ing(lote([], empresas=[emp('Mikel', 'Manueles')]), escribir=True)
        self.assertEqual((r['empresas'][0]['accion'], r['empresas'][0]['antes'], self.persona('T0001')['empresa']), ('puesta', '', 'Manueles'))


class TestPonerEmpresa(Base):
    def dos_obras(self):
        self.sembrar()
        self.ing(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5)])], obra='mungia'), escribir=True)

    def test_vista_previa_y_escritura(self):
        self.dos_obras()
        h = self.hashes()
        r = P.poner_empresa(self.raiz, OBRAS, 'Mikel', 'Manueles', ahora=AHORA)
        self.assertEqual((r['ok'], r['accion'], r['id'], r['nombre'], r['antes'], r['despues'], r['escrito']),
                         (True, 'puesta', 'T0001', 'Mikel', '', 'Manueles', False))
        self.assertEqual(r['trazas_en'], ['mungia', 'olabeaga'])
        self.assertEqual(self.hashes(), h)
        r = P.poner_empresa(self.raiz, OBRAS, 'Mikel', 'Manueles', escribir=True, ahora=AHORA)
        self.assertTrue(r['escrito'])
        self.assertEqual(self.persona('T0001')['empresa'], 'Manueles')
        for o in ('olabeaga', 'mungia'):
            ult = self.traza(o)[-1]
            self.assertEqual((ult['accion'], ult['id'], ult['nombre'], ult['de'], ult['a'], ult['ts'], ult['fecha']),
                             ('empresa', 'T0001', 'Mikel', '', 'Manueles', AHORA, None))

    def test_por_id_y_quitarla(self):
        self.dos_obras()
        P.poner_empresa(self.raiz, OBRAS, 'T0002', 'Catersystem', escribir=True, ahora=AHORA)
        r = P.poner_empresa(self.raiz, OBRAS, 'T0002', '', escribir=True, ahora=AHORA)
        self.assertEqual((r['accion'], r['antes'], r['despues']), ('quitada', 'Catersystem', ''))
        self.assertEqual(self.persona('T0002')['empresa'], '')

    def test_sin_cambios_no_escribe(self):
        self.dos_obras()
        P.poner_empresa(self.raiz, OBRAS, 'Mikel', 'Manueles', escribir=True, ahora=AHORA)
        h = self.hashes()
        r = P.poner_empresa(self.raiz, OBRAS, 'Mikel', 'MANUELES', escribir=True, ahora=AHORA)
        self.assertEqual((r['ok'], r['accion'], r['escrito']), (True, 'sin_cambios', False))
        self.assertEqual(self.hashes(), h)

    def test_por_nombre_antiguo_avisa(self):
        self.dos_obras()
        P.renombrar(self.raiz, OBRAS, 'Mikel', 'Mikel Etxeberria', escribir=True, ahora=AHORA)
        r = P.poner_empresa(self.raiz, OBRAS, 'Mikel', 'Manueles', ahora=AHORA)
        self.assertEqual([a['codigo'] for a in r['avisos']], ['nombre_anterior_usado'])
        self.assertEqual(r['nombre'], 'Mikel Etxeberria')

    def test_una_persona_juntada_va_a_la_vigente(self):
        self.sembrar()
        P.fusionar(self.raiz, 'T0003', 'T0001', escribir=True)
        r = P.poner_empresa(self.raiz, OBRAS, 'T0003', 'Manueles', escribir=True, ahora=AHORA)
        self.assertEqual(r['id'], 'T0001')
        self.assertEqual(self.persona('T0001')['empresa'], 'Manueles')

    def test_errores(self):
        self.dos_obras()
        h = self.hashes()
        for quien, empresa, error in (('Mikel', '12345678Z', 'empresa_invalida'), ('Mikel', None, 'empresa_invalida'),
                                      ('Mikel', 'x' * 61, 'empresa_invalida'), ('Nadie', 'X', 'persona_inexistente'),
                                      ('T0099', 'X', 'persona_inexistente')):
            r = P.poner_empresa(self.raiz, OBRAS, quien, empresa, escribir=True, ahora=AHORA)
            self.assertEqual((r['ok'], r['error'], r['escrito']), (False, error, False), (quien, empresa))
        self.assertEqual(self.hashes(), h)

    def test_quien_solo_esta_en_la_base_no_deja_traza(self):
        self.sembrar()
        self.ing(lote([], altas=['Nuevo']), escribir=True)
        r = P.poner_empresa(self.raiz, OBRAS, 'Nuevo', 'Manueles', escribir=True, ahora=AHORA)
        self.assertEqual(r['trazas_en'], [])
        self.assertEqual(self.lineas_empresa(), [])
        self.assertEqual(self.empresas()['Nuevo'], 'Manueles')


class TestPartirEmpresa(unittest.TestCase):
    def test_casos(self):
        casos = {
            'Alejo (Manueles)': ('Alejo', 'Manueles'),
            'Javi @ CATERSYSTEM': ('Javi', 'CATERSYSTEM'),
            'Chico 1 @ CATERSYSTEM': ('Chico 1', 'CATERSYSTEM'),
            'Javi@Catersystem': ('Javi', 'Catersystem'),
            'Íñigo ( Construcciones Muñoz )': ('Íñigo', 'Construcciones Muñoz'),
            'A (B) (C)': ('A (B)', 'C'),
            '(Manueles)': ('', 'Manueles'),
            '@ CATERSYSTEM': ('', 'CATERSYSTEM'),
            'Javi @': ('Javi', ''),
            'Ana ()': ('Ana', ''),
            'Javi @AUT': ('Javi', 'AUT'),
            'Asensio': None, 'Ana María': None, 'Chico 1': None, '(': None, 'Mikel )': None, '': None, None: None,
        }
        for nombre, esperado in casos.items():
            self.assertEqual(P._partir_empresa(nombre), esperado, repr(nombre))


class TestSeparar(Base):
    REALES = ['Alejo (Manueles)', 'Manuel (Manueles)', 'Nestor (Manueles)', 'Javi @ CATERSYSTEM',
              'Chico 1 @ CATERSYSTEM', 'Asensio']

    def sembrar_reales(self):
        presentes = [(n, 7.5) for n in self.REALES]
        self.sembrar(lote([jor('vivienda', '2026-10-22', presentes), jor('garaje', '2026-10-23', presentes[:3])]))

    def test_vista_previa_no_escribe_y_dice_lo_que_hara(self):
        self.sembrar_reales()
        h = self.hashes()
        r = P.separar_empresas(self.raiz, OBRAS)
        self.assertEqual([(x['id'], x['de'], x['nombre'], x['empresa']) for x in r['propuestas']], [
            ('T0001', 'Alejo (Manueles)', 'Alejo', 'Manueles'), ('T0002', 'Manuel (Manueles)', 'Manuel', 'Manueles'),
            ('T0003', 'Nestor (Manueles)', 'Nestor', 'Manueles'),
            ('T0004', 'Javi @ CATERSYSTEM', 'Javi', 'CATERSYSTEM'),
            ('T0005', 'Chico 1 @ CATERSYSTEM', 'Chico 1', 'CATERSYSTEM')])
        self.assertEqual((r['paran'], r['sin_empresa_en_el_nombre'], r['aplicadas'], r['errores'], r['escrito']),
                         ([], 1, [], [], False))
        self.assertEqual(self.hashes(), h)

    def test_aplicar_renombra_a_toda_la_persona_y_pone_la_empresa_sin_tocar_jornadas(self):
        self.sembrar_reales()
        obra_antes = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        totales_antes = sorted((v['horas'], v['dias']) for v in P.totales_control(self.raiz, OBRAS, 'olabeaga')['por_trabajador'].values())
        previa = P.separar_empresas(self.raiz, OBRAS)
        r = P.separar_empresas(self.raiz, OBRAS, aplicar=True, ahora=AHORA)
        self.assertEqual(r['aplicadas'], ['T0001', 'T0002', 'T0003', 'T0004', 'T0005'])
        self.assertEqual((r['errores'], r['escrito']), ([], True))
        self.assertEqual(r['propuestas'], previa['propuestas'], 'lo que se enseñó es lo que se hace')
        t1 = self.persona('T0001')
        self.assertEqual((t1['nombre'], t1['nombres_anteriores'], t1['empresa']), ('Alejo', ['Alejo (Manueles)'], 'Manueles'))
        self.assertEqual(self.empresas(), {'Alejo': 'Manueles', 'Manuel': 'Manueles', 'Nestor': 'Manueles',
                                           'Javi': 'CATERSYSTEM', 'Chico 1': 'CATERSYSTEM', 'Asensio': ''})
        self.assertEqual(P.cargar_obra(self.raiz, OBRAS, 'olabeaga'), obra_antes, 'ninguna jornada cambia')
        despues = sorted((v['horas'], v['dias']) for v in P.totales_control(self.raiz, OBRAS, 'olabeaga')['por_trabajador'].values())
        self.assertEqual(despues, totales_antes)
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])
        acciones = [x['accion'] for x in self.traza() if x['accion'] in ('renombre', 'empresa')]
        self.assertEqual(acciones, ['renombre', 'empresa'] * 5)

    def test_aplicar_dos_veces_no_hace_nada_la_segunda(self):
        self.sembrar_reales()
        P.separar_empresas(self.raiz, OBRAS, aplicar=True, ahora=AHORA)
        h = self.hashes()
        r = P.separar_empresas(self.raiz, OBRAS, aplicar=True, ahora=AHORA)
        self.assertEqual((r['propuestas'], r['paran'], r['aplicadas'], r['escrito']), ([], [], [], False))
        self.assertEqual(self.hashes(), h)

    def test_un_control_horario_con_el_nombre_viejo_sigue_valiendo(self):
        self.sembrar_reales()
        P.separar_empresas(self.raiz, OBRAS, aplicar=True, ahora=AHORA)
        r = self.ing(lote([jor('vivienda', '2026-10-24', [('Alejo (Manueles)', 7.5)])]), escribir=True)
        self.assertEqual([a['codigo'] for a in r['jornadas'][0]['avisos']], ['nombre_anterior_usado'])
        self.assertEqual(len(self.cat()['trabajadores']), 6, 'no aparece una persona nueva')

    def test_lo_dudoso_para_y_nunca_se_aplica(self):
        nombres = ['(Manueles)', 'Javi @AUT', 'Chico (2)', 'Ana (X)', 'Ana (Y)', 'Mikel (Z)', 'Mikel', 'Nadie @ Obra']
        self.sembrar(lote([jor('vivienda', '2026-10-22', [(n, 7.5) for n in nombres])]))
        r = P.separar_empresas(self.raiz, OBRAS)
        self.assertEqual([(x['motivo'], x['de']) for x in r['paran']], [
            ('nombre_vacio', '(Manueles)'), ('sufijo_aut', 'Javi @AUT'), ('sin_letras', 'Chico (2)'),
            ('mismo_nombre', 'Ana (X)'), ('mismo_nombre', 'Ana (Y)'), ('coincide_con_otro', 'Mikel (Z)')])
        self.assertEqual([(x['de'], x['nombre'], x['empresa']) for x in r['propuestas']], [('Nadie @ Obra', 'Nadie', 'Obra')])
        coincide = r['paran'][-1]
        self.assertEqual(coincide['orden'], 'personal_obra.py fusionar T0006 T0007')
        for x in r['paran']:
            self.assertTrue(x['texto'].startswith('«' + x['de'] + '»'), x['texto'])
        P.separar_empresas(self.raiz, OBRAS, aplicar=True, ahora=AHORA)
        self.assertEqual(sorted(self.empresas()), sorted(['(Manueles)', 'Javi @AUT', 'Chico (2)', 'Ana (X)', 'Ana (Y)',
                                                          'Mikel (Z)', 'Mikel', 'Nadie']))
        self.assertEqual(set(self.empresas().values()), {'', 'Obra'})

    def test_quien_ya_tiene_otra_empresa_para_y_con_la_misma_sigue(self):
        self.sembrar(lote([jor('vivienda', '2026-10-22', [('Rafa (Manueles)', 7.5), ('Pepe (Manueles)', 7.5)])]))
        P.poner_empresa(self.raiz, OBRAS, 'Rafa (Manueles)', 'Otra', escribir=True, ahora=AHORA)
        P.poner_empresa(self.raiz, OBRAS, 'Pepe (Manueles)', 'MANUELES', escribir=True, ahora=AHORA)
        r = P.separar_empresas(self.raiz, OBRAS)
        self.assertEqual([(x['motivo'], x['detalle']) for x in r['paran']], [('ya_tiene_empresa', 'Otra')])
        self.assertEqual([(x['nombre'], x['empresa']) for x in r['propuestas']], [('Pepe', 'MANUELES')])

    def test_la_empresa_de_dos_personas_sale_con_una_sola_grafia(self):
        self.sembrar(lote([jor('vivienda', '2026-10-22', [('Ana @ Catersystem', 7.5), ('Beto @ CATERSYSTEM', 7.5)])]))
        r = P.separar_empresas(self.raiz, OBRAS, aplicar=True, ahora=AHORA)
        self.assertEqual([x['empresa'] for x in r['propuestas']], ['Catersystem', 'Catersystem'])
        self.assertEqual(sorted(set(self.empresas().values())), ['Catersystem'])

    def test_las_personas_juntadas_con_otra_no_se_tocan(self):
        self.sembrar(lote([jor('vivienda', '2026-10-22', [('Ana (X)', 7.5)]), jor('vivienda', '2026-10-23', [('Ana', 7.5)])]))
        self.assertTrue(P.fusionar(self.raiz, 'T0001', 'T0002', escribir=True)['ok'])
        r = P.separar_empresas(self.raiz, OBRAS)
        self.assertEqual((r['propuestas'], r['paran']), ([], []))

    def test_con_tildes_y_espacios(self):
        self.sembrar(lote([jor('vivienda', '2026-10-22', [('Íñigo   (Construcciones   Muñoz)', 7.5)])]))
        r = P.separar_empresas(self.raiz, OBRAS)
        self.assertEqual([(x['nombre'], x['empresa']) for x in r['propuestas']], [('Íñigo', 'Construcciones Muñoz')])

    def test_sin_catalogo_no_hay_nada(self):
        r = P.separar_empresas(self.raiz, OBRAS)
        self.assertEqual((r['propuestas'], r['paran'], r['sin_empresa_en_el_nombre']), ([], [], 0))
        self.assertEqual(self.hashes(), {})

    def cli(self, *args):
        base = ['separar-empresas', '--raiz', self.raiz, '--obras', ','.join(k + '=' + v for k, v in OBRAS.items())]
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = P.main(base + list(args))
        return codigo, salida.getvalue()

    def test_linea_de_comandos_vista_previa_y_aplicar(self):
        self.sembrar_reales()
        h = self.hashes()
        codigo, out = self.cli()
        self.assertEqual(codigo, 0, out)
        self.assertIn('Vista previa: todavía no se guarda nada.', out)
        self.assertIn('«Alejo (Manueles)» pasa a «Alejo», empresa «Manueles»', out)
        self.assertIn('«Javi @ CATERSYSTEM» pasa a «Javi», empresa «CATERSYSTEM»', out)
        self.assertIn('1 persona no lleva empresa en el nombre: no se toca.', out)
        self.assertIn('--aplicar', out)
        self.assertEqual(self.hashes(), h)
        codigo, out = self.cli('--aplicar')
        self.assertEqual(codigo, 0, out)
        self.assertNotIn('Vista previa', out)
        self.assertIn('Se ha separado así:', out)
        self.assertEqual(self.empresas()['Alejo'], 'Manueles')
        codigo, out = self.cli('--aplicar')
        self.assertIn('No hay nombres con la empresa dentro: no hay nada que separar.', out)

    def test_linea_de_comandos_con_dudosos_sale_con_2_y_los_enseña(self):
        self.sembrar(lote([jor('vivienda', '2026-10-22', [('Javi @AUT', 7.5), ('Ana (X)', 7.5)])]))
        codigo, out = self.cli()
        self.assertEqual(codigo, 2, out)
        self.assertIn('Hay que mirarlos a mano (no se tocan):', out)
        self.assertIn('«Javi @AUT»: acaba en «@AUT»', out)
        for linea in out.splitlines():
            self.assertIsNone(PALABRAS.search(linea), linea)


class TestComprobar(Base):
    def test_empresa_mal_escrita_en_la_base(self):
        self.sembrar()
        for malo in (5, 'ana@empresa.com', 'x' * 61, ['Manueles'], '12345678Z'):
            cat = self.cat()
            cat['trabajadores'][0]['empresa'] = malo
            P.guardar_catalogo(self.raiz, cat)
            self.assertEqual([x.split(': ', 1)[1] for x in P.comprobar(self.raiz, OBRAS)], ['empresa invalida'], repr(malo))

    def test_sin_empresa_o_vacia_vale(self):
        self.sembrar()
        cat = self.cat()
        cat['trabajadores'][0]['empresa'] = None
        cat['trabajadores'][1]['empresa'] = ''
        cat['trabajadores'][2]['empresa'] = 'Javi @AUT'
        P.guardar_catalogo(self.raiz, cat)
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])


class TestTextos(unittest.TestCase):
    def test_frases_exactas(self):
        self.assertEqual(P.texto_empresa('puesta', 'Alejo', '', 'Manueles'), 'Pone la empresa «Manueles» a «Alejo».')
        self.assertEqual(P.texto_empresa('cambiada', 'Alejo', 'Manueles', 'Catersystem'),
                         'Cambia la empresa de «Alejo»: de «Manueles» a «Catersystem».')
        self.assertEqual(P.texto_empresa('quitada', 'Alejo', 'Manueles', ''), 'Quita la empresa a «Alejo» (era «Manueles»).')
        self.assertEqual(P.texto_empresa('sin_cambios', 'Alejo', 'M', 'M'), '«Alejo» ya tiene esa empresa: no hay nada que cambiar.')
        self.assertEqual(P.texto_aviso('empresa_invalida'), 'Una empresa viene mal escrita.')
        self.assertEqual(P.texto_aviso('empresa_sin_persona', 'Fantasma'),
                         '«Fantasma» no estaba en la base: no se le puede poner empresa.')
        self.assertEqual(P.texto_aviso('empresa_sin_persona'),
                         'Una empresa era para alguien que no estaba en la base: no se ha puesto.')

    def test_frases_de_lo_que_se_deja_sin_tocar(self):
        esperadas = {
            'nombre_vacio': '«(Manueles)»: quitando la empresa no quedaría ningún nombre.',
            'sin_letras': '«Chico (2)»: lo que acompaña al nombre no parece una empresa. No se toca.',
            'sufijo_aut': '«Javi @AUT»: acaba en «@AUT», que marca a un autónomo. ¿Es una persona con la empresa «AUT»? '
                          'Dímelo con este caso delante.',
            'no_vale': '«X»: la parte del nombre o la de la empresa no vale (vacía, muy larga o con signos raros).',
            'mismo_nombre': '«X»: otra persona de la lista quedaría también como «Ana». ¿Son la misma persona?',
            'ya_tiene_empresa': '«X» ya tiene la empresa «Otra»: una persona solo puede tener una.',
            'coincide_con_otro': '«X»: ya hay otro «Ana» en la base. Si son la misma persona hay que juntarlas antes.',
        }
        detalles = {'sufijo_aut': 'AUT', 'mismo_nombre': 'Ana', 'ya_tiene_empresa': 'Otra', 'coincide_con_otro': 'Ana'}
        nombres = {'nombre_vacio': '(Manueles)', 'sin_letras': 'Chico (2)', 'sufijo_aut': 'Javi @AUT'}
        for codigo, frase in esperadas.items():
            self.assertEqual(P.texto_separar(codigo, nombres.get(codigo, 'X'), detalles.get(codigo)), frase, codigo)

    def test_ninguna_frase_lleva_palabras_de_programador_ni_codigos(self):
        frases = [P.texto_empresa(a, 'Alejo', 'Manueles', 'Catersystem') for a in ('puesta', 'cambiada', 'quitada', 'x')]
        frases += [P.texto_aviso('empresa_invalida'), P.texto_aviso('empresa_sin_persona', 'Z')]
        frases += [P.texto_separar(c, 'Z', 'D') for c in ('nombre_vacio', 'sin_letras', 'sufijo_aut', 'no_vale', 'mismo_nombre',
                                                           'ya_tiene_empresa', 'coincide_con_otro', 'otro')]
        for f in frases:
            self.assertIsNone(PALABRAS.search(f), f)
            self.assertNotIn('_', f)


class TestLector(Base):
    NOM = 'CONTROL HORARIO 2026 OLABEAGA BILBAO %s.json'

    def rev(self):
        d = os.path.join(self.raiz, OBRAS['olabeaga'], 'REVISIONES')
        os.makedirs(d, exist_ok=True)
        return d

    def fichero(self, l, fecha='26102026'):
        with open(os.path.join(self.rev(), self.NOM % fecha), 'wb') as fh:
            fh.write(json.dumps(l, ensure_ascii=False, indent=1).encode('utf-8'))

    def analizar(self, aceptar=False):
        return L.analizar('olabeaga', L.listar(self.rev()), HOY, self.raiz, OBRAS, aceptar=aceptar, ahora=AHORA)

    def aplicar(self):
        return L.aplicar('olabeaga', L.listar(self.rev()), HOY, self.raiz, OBRAS, ahora=AHORA)

    def test_un_fichero_solo_de_empresas_se_ve_y_se_aplica(self):
        self.sembrar()
        self.fichero(lote([], empresas=[emp('Mikel', 'Manueles'), emp('Txomin', 'Javi @AUT')]))
        r = self.analizar()
        f = r['ficheros'][0]
        self.assertEqual((f['estado'], f['sin_efecto']), ('listo', False))
        self.assertEqual([(e['nombre'], e['accion'], e['despues']) for e in f['empresas']],
                         [('Mikel', 'puesta', 'Manueles'), ('Txomin', 'puesta', 'Javi @AUT')])
        self.assertEqual(f['resumen'], '2 empresas puestas')
        self.assertEqual(self.empresas()['Mikel'], '', 'analizar no escribe')
        ap = self.aplicar()
        self.assertEqual(len(ap['aplicados']), 1)
        self.assertEqual(self.empresas(), {'Mikel': 'Manueles', 'Txomin': 'Javi @AUT', 'Andoni': ''})
        h = self.hashes()
        self.assertEqual(self.analizar()['ficheros'][0]['estado'], 'ya_aplicado')
        self.aplicar()
        self.assertEqual(self.hashes(), h, 'aplicar dos veces no cambia ni un byte')

    def test_cambiada_y_quitada_en_el_resumen_y_en_las_lineas_en_llano(self):
        self.sembrar()
        self.ing(lote([], empresas=[emp('Mikel', 'Manueles'), emp('Txomin', 'Otra')]), escribir=True)
        self.fichero(lote([], empresas=[emp('Mikel', 'Catersystem'), emp('Txomin', ''), emp('Andoni', 'Obras')]))
        f = self.analizar()['ficheros'][0]
        self.assertEqual(f['resumen'], '2 empresas puestas, 1 empresa quitada')
        lineas = PI._lineas_ficha(f)
        self.assertIn('      · Cambia la empresa de «Mikel»: de «Manueles» a «Catersystem».', lineas)
        self.assertIn('      · Quita la empresa a «Txomin» (era «Otra»).', lineas)
        self.assertIn('      · Pone la empresa «Obras» a «Andoni».', lineas)
        for linea in lineas[1:]:
            self.assertIsNone(PALABRAS.search(linea), linea)

    def test_empresas_y_todas_las_jornadas_rechazadas_no_pierde_las_empresas(self):
        self.sembrar()
        self.fichero(lote([jor('vivienda', '2026-13-45', [('Mikel', 7.5)])], empresas=[emp('Mikel', 'Manueles')]))
        f = self.analizar()['ficheros'][0]
        self.assertEqual(f['estado'], 'listo', f['motivos'])
        self.assertEqual(f['rechazadas'], 1)
        self.aplicar()
        self.assertEqual(self.empresas()['Mikel'], 'Manueles')

    def test_empresa_de_alguien_que_no_esta_se_avisa_con_su_frase(self):
        self.sembrar()
        self.fichero(lote([], empresas=[emp('Fantasma', 'Manueles')]))
        f = self.analizar()['ficheros'][0]
        self.assertEqual(f['estado'], 'listo')
        self.assertEqual([a['texto'] for a in f['avisos']], ['«Fantasma» no estaba en la base: no se le puede poner empresa.'])
        self.assertEqual(f['empresas'], [])

    def test_datos_privados_en_una_empresa_no_se_aplican_ni_se_repiten(self):
        self.sembrar()
        self.fichero(lote([], empresas=[emp('Mikel', '612 345 678')]))
        f = self.analizar()['ficheros'][0]
        self.assertEqual(f['estado'], 'rechazado')
        self.assertEqual([m['codigo'] for m in f['motivos']], ['dato_privado'])
        self.assertIn('empresas', f['motivos'][0]['texto'])
        self.assertNotIn('612', f['motivos'][0]['texto'])
        self.aplicar()
        self.assertEqual(self.empresas()['Mikel'], '')

    def test_empresa_mal_escrita_rechaza_el_fichero(self):
        self.sembrar()
        self.fichero(lote([], empresas=[emp('Mikel', 'x' * 61)]))
        f = self.analizar()['ficheros'][0]
        self.assertEqual((f['estado'], [m['codigo'] for m in f['motivos']]), ('rechazado', ['empresa_invalida']))
        self.assertEqual(f['motivos'][0]['texto'], 'Una empresa viene mal escrita.')

    def test_ficha_vacia_lleva_la_clave(self):
        self.assertEqual(L._ficha_vacia({})['empresas'], [])

    def test_fichero_sin_empresas_igual_que_antes(self):
        self.sembrar()
        self.fichero(lote([jor('vivienda', '2026-10-23', [('Mikel', 7.5)])]))
        f = self.analizar()['ficheros'][0]
        self.assertEqual((f['empresas'], f['resumen']), ([], '1 jornada de viviendas'))


def setUpModule():
    global TMP, _TMP_OBJ
    _TMP_OBJ = tempfile.TemporaryDirectory(prefix='personal_08c2a_')
    TMP = _TMP_OBJ.name


def tearDownModule():
    _TMP_OBJ.cleanup()


if __name__ == '__main__':
    unittest.main()
