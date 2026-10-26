# -*- coding: utf-8 -*-
"""Pruebas del paso 08a sobre personal_obra.py (P1): renombres, altas, nombres anteriores, SHA256 en la
traza, alta automática de la obra, estado en memoria, operación `renombrar` y textos en llano.
Datos INVENTADOS. unittest de la biblioteca estándar. Las 82 pruebas de test_personal_obra.py no se tocan."""
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
import personal_obra as P

TMP = None
_TMP_OBJ = None
OBRAS = {'olabeaga': '2026 OLABEAGA BILBAO', 'mungia': '2026 MUNGIA ACR NEINOR'}
HOY = '2026-10-23'
AHORA = '2026-10-23T22:00:00+02:00'
H_BASE = {'lun': 7.5, 'mar': 7.5, 'mie': 7.5, 'jue': 7.5, 'vie': 7.5, 'sab': 0, 'dom': 0}
SHA1 = 'a' * 64
SHA2 = 'b' * 64
FICH1 = 'CONTROL HORARIO 2026 OLABEAGA BILBAO 23102026.json'


def pres(*items):
    out = []
    for it in items:
        d = {'nombre': it[0], 'horas': it[1]}
        if len(it) > 2:
            d['extra'] = it[2]
        out.append(d)
    return out


def jor(ambito, fecha, presentes, **kw):
    d = {'ambito': ambito, 'fecha': fecha, 'presentes': pres(*presentes)}
    d.update(kw)
    return d


def lote(jornadas, obra='olabeaga', **kw):
    d = {'tipo': 'lote_personal', 'version': 1, 'obra': obra, 'jornadas': jornadas}
    d.update(kw)
    return d


# Mikel T0001, Txomin T0002, Andoni T0003 (por orden de aparición)
L1 = lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0), ('Txomin', 7.5, 0)]),
           jor('garaje', '2026-10-22', [('Andoni', 7.5, 0)])])


def ren(de, a):
    return {'de': de, 'a': a}


class Base(unittest.TestCase):
    def setUp(self):
        self._dirs = []
        self.nuevo_raiz()

    def nuevo_raiz(self):
        self.raiz = os.path.join(TMP, uuid.uuid4().hex)
        os.makedirs(self.raiz)
        self._dirs.append(self.raiz)
        return self.raiz

    def tearDown(self):
        for d in self._dirs:
            shutil.rmtree(d, ignore_errors=True)

    def ing(self, l, escribir=False, hoy=HOY, ahora=AHORA, **kw):
        return P.ingerir_lote(copy.deepcopy(l), self.raiz, OBRAS, hoy, escribir=escribir, ahora=ahora, **kw)

    def hashes(self):
        out = {}
        for d, _, fs in os.walk(self.raiz):
            for f in fs:
                p = os.path.join(d, f)
                with open(p, 'rb') as fh:
                    out[os.path.relpath(p, self.raiz).replace(os.sep, '/')] = hashlib.sha256(fh.read()).hexdigest()
        return out

    def ruta_obra(self, obra='olabeaga'):
        return os.path.join(self.raiz, OBRAS[obra], 'INFORME SAGARDE IA')

    def traza(self, obra='olabeaga'):
        p = os.path.join(self.ruta_obra(obra), 'personal_jornadas.jsonl')
        if not os.path.exists(p):
            return []
        with open(p, encoding='utf-8') as fh:
            return [json.loads(x) for x in fh.read().splitlines()]

    def cat(self):
        return P.cargar_catalogo(self.raiz)

    def persona(self, i):
        return next(t for t in self.cat()['trabajadores'] if t['id'] == i)

    def codigos(self, avisos):
        return [a['codigo'] for a in avisos]

    def rechazado(self, l, codigo, **kw):
        antes = self.hashes()
        r = self.ing(l, escribir=True, **kw)
        self.assertFalse(r['ok'], r)
        self.assertIn(codigo, r['lote_rechazado'])
        self.assertEqual(r['jornadas'], [], 'un lote rechazado no procesa nada')
        self.assertEqual(self.hashes(), antes, 'un lote rechazado no escribe ni un byte')
        return r

    def sembrar(self):
        r = self.ing(L1, escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)
        return r


class TestEsquema(Base):
    def test_claves_nuevas(self):
        self.assertIn('renombres', P.LK)
        self.assertIn('altas', P.LK)
        self.assertIn('nombres_anteriores', P.TK)

    def test_nombre_publicable(self):
        for bueno in ('Mikel', 'Javi @ CATERSYSTEM', 'Pepe (Contrata X)', 'Ana @ EMPRESA Y', 'Chico 1 @ CATERSYSTEM',
                      'Manuel (Manueles)', 'Íñigo Ibarra', 'x' * 60):
            self.assertTrue(P.nombre_publicable(bueno), bueno)
        for malo in ('', '   ', 'x' * 61, 'Mikel<b>', '<script>', 'a>b', 'a<b', '12345678Z', '12345678-Z', 'X1234567L',
                     '612 345 678', '612345678', '+34 612 345 678', 'ana@empresa.com', None, 7, ['Mikel'],
                     'Mi\x00kel'):
            self.assertFalse(P.nombre_publicable(malo), repr(malo))

    def test_renombre_invalido_rechaza_el_lote_entero(self):
        malos = [
            'no es una lista', {'de': 'A', 'a': 'B'}, ['A'], [ren('A', 'B'), 'C'], [{'de': 'A'}], [{'a': 'B'}],
            [{'de': 'A', 'a': 'B', 'x': 1}], [ren('', 'B')], [ren('A', '')], [ren('A', ' ')], [ren('A', 'x' * 61)],
            [ren('A', 'B<i>')], [ren('<b>', 'B')], [ren('A', '12345678Z')], [ren('A', '612 345 678')],
            [ren('A', 'ana@empresa.com')], [ren(None, 'B')], [ren('A', 5)],
        ]
        for m in malos:
            self.nuevo_raiz()
            self.rechazado(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])], renombres=m), 'renombre_invalido')

    def test_alta_invalida_rechaza_el_lote_entero(self):
        malos = ['Mikel', {'a': 'Mikel'}, ['Mikel', 5], ['Mikel', None], ['Mikel', ''], ['  '], ['x' * 61], ['A<b>'],
                 ['12345678Z'], ['612345678'], ['ana@empresa.com'], [['Mikel']], [{'nombre': 'Mikel'}]]
        for m in malos:
            self.nuevo_raiz()
            self.rechazado(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])], altas=m), 'alta_invalida')

    def test_nombres_con_empresa_valen(self):
        r = self.ing(lote([], altas=['Javi @ CATERSYSTEM', 'Pepe (Contrata X)', 'Ana @ EMPRESA Y']), escribir=True)
        self.assertTrue(r['ok'], r)
        self.assertEqual([t['nombre'] for t in self.cat()['trabajadores']],
                         ['Javi @ CATERSYSTEM', 'Pepe (Contrata X)', 'Ana @ EMPRESA Y'])

    def test_lote_sin_claves_nuevas_se_comporta_como_antes(self):
        r = self.ing(L1)
        self.assertEqual((r['renombres'], r['altas_pedidas'], r['obra_creada'], r['recibido']), ([], [], False, False))
        r = self.ing(lote([], renombres=[], altas=[]), escribir=True)
        self.assertTrue(r['ok'])
        self.assertFalse(r['escrito'])
        self.assertEqual(self.hashes(), {})

    def test_claves_nuevas_en_lote_rechazado(self):
        r = self.ing({'tipo': 'otra_cosa'})
        self.assertFalse(r['ok'])
        self.assertEqual((r['renombres'], r['altas_pedidas'], r['obra_creada'], r['recibido']), ([], [], False, False))


class TestRenombres(Base):
    def test_renombre_libre(self):
        self.sembrar()
        r = self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)
        self.assertEqual(r['renombres'], [{'de': 'Mikel', 'a': 'Mikel Etxeberria', 'accion': 'renombrado', 'id': 'T0001',
                                           'id_otro': None, 'orden': None}])
        t = self.persona('T0001')
        self.assertEqual((t['nombre'], t['nombres_anteriores']), ('Mikel Etxeberria', ['Mikel']))
        self.assertEqual(set(t), set(P.TK))
        self.assertEqual(self.codigos(r['avisos_lote']), [])
        filas = P.aplanar(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual(sorted({f['nombre'] for f in filas}), ['Andoni', 'Mikel Etxeberria', 'Txomin'])
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual(ob['jornadas'][1]['presentes'][0]['id'], 'T0001', 'las jornadas siguen colgando del id')
        ult = self.traza()[-1]
        self.assertEqual((ult['accion'], ult['id'], ult['de'], ult['a']), ('renombre', 'T0001', 'Mikel', 'Mikel Etxeberria'))
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])

    def test_renombre_sin_cambios_no_toca_nada(self):
        self.sembrar()
        h = self.hashes()
        r = self.ing(lote([], renombres=[ren('Mikel', 'Mikel')]), escribir=True)
        self.assertEqual(r['renombres'][0]['accion'], 'sin_cambios')
        self.assertEqual(r['renombres'][0]['id'], 'T0001')
        self.assertFalse(r['escrito'])
        self.assertEqual(self.hashes(), h)

    def test_renombre_solo_grafia(self):
        self.sembrar()
        r = self.ing(lote([], renombres=[ren('mikel', 'MIKEL')]), escribir=True)
        self.assertEqual(r['renombres'][0]['accion'], 'renombrado')
        t = self.persona('T0001')
        self.assertEqual((t['nombre'], t['nombres_anteriores']), ('MIKEL', []), 'misma clave: no es un nombre anterior')
        self.assertEqual(self.traza()[-1]['accion'], 'renombre')

    def test_renombre_a_nombre_de_otra_persona_no_se_aplica(self):
        self.sembrar()
        h = self.hashes()
        r = self.ing(lote([jor('vivienda', '2026-10-23', [('Txomin', 7.5, 0)])], renombres=[ren('Mikel', 'Txomin')]))
        e = r['renombres'][0]
        self.assertEqual((e['accion'], e['id'], e['id_otro']), ('coincide_con_otro', 'T0001', 'T0002'))
        self.assertIn('fusionar T0001 T0002', e['orden'])
        self.assertEqual(r['avisos_lote'], [{'codigo': 'renombre_coincide_con_otro', 'detalle': 'Mikel -> Txomin (T0001, T0002)'}])
        self.assertTrue(r['ok'], 'no es un error: el lote sigue valiendo')
        self.assertEqual(r['jornadas'][0]['accion'], 'alta', 'la jornada cae en la persona que ya existe')
        r2 = self.ing(lote([], renombres=[ren('Mikel', 'Txomin')]), escribir=True)
        self.assertFalse(r2['escrito'])
        self.assertEqual(self.hashes(), h)

    def test_renombre_a_nombre_de_otra_persona_con_tildes_o_mayusculas(self):
        self.sembrar()
        r = self.ing(lote([], renombres=[ren('Mikel', 'TXOMÍN')]))
        self.assertEqual(r['renombres'][0]['accion'], 'coincide_con_otro')

    def test_renombre_sin_origen(self):
        self.sembrar()
        h = self.hashes()
        r = self.ing(lote([], renombres=[ren('Fantasma', 'Nuevo')]), escribir=True)
        self.assertTrue(r['ok'], 'no es un error')
        e = r['renombres'][0]
        self.assertEqual((e['accion'], e['id']), ('sin_origen', None))
        self.assertEqual(r['avisos_lote'], [{'codigo': 'renombre_sin_origen', 'detalle': 'Fantasma'}])
        self.assertFalse(r['escrito'])
        self.assertEqual(self.hashes(), h)

    def test_renombre_sin_origen_y_jornada_con_el_nombre_nuevo(self):
        r = self.ing(lote([jor('vivienda', '2026-10-22', [('Nuevo', 7.5, 0)])], renombres=[ren('Fantasma', 'Nuevo')]),
                     escribir=True)
        self.assertEqual(r['renombres'][0]['accion'], 'sin_origen')
        self.assertEqual(self.codigos(r['jornadas'][0]['avisos']), ['alta_nueva'])
        self.assertEqual([t['nombre'] for t in self.cat()['trabajadores']], ['Nuevo'])

    def test_renombre_repetido_es_idempotente_por_nombre_anterior(self):
        self.sembrar()
        l = lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')])
        self.ing(l, escribir=True)
        h = self.hashes()
        r = self.ing(l, escribir=True)
        self.assertEqual(r['renombres'][0]['accion'], 'sin_cambios')
        self.assertEqual(r['renombres'][0]['id'], 'T0001')
        self.assertEqual(r['avisos_lote'], [])
        self.assertFalse(r['escrito'])
        self.assertEqual(self.hashes(), h)

    def test_renombre_desde_nombre_anterior_a_otro_nombre(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        r = self.ing(lote([], renombres=[ren('Mikel', 'Mikel E.')]), escribir=True)
        self.assertEqual(r['renombres'][0]['accion'], 'renombrado')
        self.assertEqual(r['avisos_lote'], [{'codigo': 'nombre_anterior_usado', 'detalle': 'Mikel -> Mikel Etxeberria'}])
        t = self.persona('T0001')
        self.assertEqual((t['nombre'], t['nombres_anteriores']), ('Mikel E.', ['Mikel', 'Mikel Etxeberria']))

    def test_renombres_encadenados_en_un_lote(self):
        self.sembrar()
        r = self.ing(lote([], renombres=[ren('Mikel', 'Mikel B'), ren('Mikel B', 'Mikel C')]), escribir=True)
        self.assertEqual([e['accion'] for e in r['renombres']], ['renombrado', 'renombrado'])
        t = self.persona('T0001')
        self.assertEqual((t['nombre'], t['nombres_anteriores']), ('Mikel C', ['Mikel', 'Mikel B']))
        self.assertEqual([x['accion'] for x in self.traza() if x['accion'] == 'renombre'], ['renombre', 'renombre'])

    def test_intercambio_de_nombres_no_se_aplica(self):
        self.sembrar()
        h = self.hashes()
        r = self.ing(lote([], renombres=[ren('Mikel', 'Txomin'), ren('Txomin', 'Mikel')]), escribir=True)
        self.assertEqual([e['accion'] for e in r['renombres']], ['coincide_con_otro', 'coincide_con_otro'])
        self.assertEqual(self.hashes(), h)

    def test_volver_a_un_nombre_antiguo(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        r = self.ing(lote([], renombres=[ren('Mikel Etxeberria', 'Mikel')]), escribir=True)
        self.assertEqual(r['renombres'][0]['accion'], 'renombrado')
        t = self.persona('T0001')
        self.assertEqual((t['nombre'], t['nombres_anteriores']), ('Mikel', ['Mikel Etxeberria']))
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])

    def test_el_renombre_vale_para_todas_las_obras(self):
        self.sembrar()
        self.ing(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5, 0)])], obra='mungia'), escribir=True)
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        self.assertEqual([f['nombre'] for f in P.aplanar(self.raiz, OBRAS, 'mungia')], ['Mikel Etxeberria'])

    def test_renombre_de_una_persona_fusionada_renombra_al_destino(self):
        self.sembrar()
        self.assertTrue(P.fusionar(self.raiz, 'T0001', 'T0003', escribir=True)['ok'])
        r = self.ing(lote([], renombres=[ren('Mikel', 'Andoni Largo')]), escribir=True)
        self.assertEqual((r['renombres'][0]['accion'], r['renombres'][0]['id']), ('renombrado', 'T0003'))
        self.assertEqual(self.persona('T0003')['nombre'], 'Andoni Largo')
        self.assertEqual(self.persona('T0001')['nombre'], 'Mikel')

    def test_renombre_a_nombre_de_una_fusionada_coincide_con_su_destino(self):
        self.sembrar()
        self.assertTrue(P.fusionar(self.raiz, 'T0001', 'T0003', escribir=True)['ok'])
        r = self.ing(lote([], renombres=[ren('Txomin', 'Mikel')]))
        self.assertEqual((r['renombres'][0]['accion'], r['renombres'][0]['id_otro']), ('coincide_con_otro', 'T0003'))

    def test_renombre_se_aplica_aunque_se_rechace_una_jornada(self):
        self.sembrar()
        mala = jor('vivienda', '2026-10-24', [('Mikel', 99, 0)])
        r = self.ing(lote([mala], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        self.assertFalse(r['ok'])
        self.assertEqual(r['jornadas'][0]['estado'], 'rechazada')
        self.assertEqual(self.persona('T0001')['nombre'], 'Mikel Etxeberria')

    def test_simulacion_no_escribe(self):
        self.sembrar()
        h = self.hashes()
        r = self.ing(lote([], renombres=[ren('Mikel', 'Otro')], altas=['Rafa']))
        self.assertEqual(r['renombres'][0]['accion'], 'renombrado')
        self.assertFalse(r['escrito'])
        self.assertEqual(self.hashes(), h)


class TestAltas(Base):
    def test_altas_nuevas(self):
        r = self.ing(lote([], altas=['Mikel', 'Rafa']), escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)
        self.assertEqual(r['altas'], [{'id': 'T0001', 'nombre': 'Mikel'}, {'id': 'T0002', 'nombre': 'Rafa'}])
        self.assertEqual(r['altas_pedidas'], [{'nombre': 'Mikel', 'id': 'T0001', 'accion': 'alta'},
                                              {'nombre': 'Rafa', 'id': 'T0002', 'accion': 'alta'}])
        self.assertEqual(r['avisos_lote'], [{'codigo': 'alta_nueva', 'detalle': 'Mikel'},
                                            {'codigo': 'alta_nueva', 'detalle': 'Rafa'}])
        cat = self.cat()['trabajadores']
        self.assertEqual([(t['id'], t['nombre'], t['alta'], t['activo'], t['fusionado_en']) for t in cat],
                         [('T0001', 'Mikel', HOY, True, None), ('T0002', 'Rafa', HOY, True, None)])
        tr = [x for x in self.traza() if x['accion'] == 'alta_persona']
        self.assertEqual([(x['id'], x['nombre']) for x in tr], [('T0001', 'Mikel'), ('T0002', 'Rafa')])
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])

    def test_altas_existentes_no_cambian_nada(self):
        self.sembrar()
        h = self.hashes()
        r = self.ing(lote([], altas=['Mikel', 'andoni', 'TXOMÍN']), escribir=True)
        self.assertEqual([(e['id'], e['accion']) for e in r['altas_pedidas']],
                         [('T0001', 'sin_cambios'), ('T0003', 'sin_cambios'), ('T0002', 'sin_cambios')])
        self.assertEqual(r['avisos_lote'], [])
        self.assertFalse(r['escrito'])
        self.assertEqual(self.hashes(), h)

    def test_alta_con_nombre_anterior(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        r = self.ing(lote([], altas=['Mikel']), escribir=True)
        self.assertEqual((r['altas_pedidas'][0]['id'], r['altas_pedidas'][0]['accion']), ('T0001', 'sin_cambios'))
        self.assertEqual(r['avisos_lote'], [{'codigo': 'nombre_anterior_usado', 'detalle': 'Mikel -> Mikel Etxeberria'}])
        self.assertEqual(len(self.cat()['trabajadores']), 3, 'no se abre una persona fantasma')

    def test_alta_con_nombre_parecido(self):
        self.sembrar()
        r = self.ing(lote([], altas=['Mikell']), escribir=True)
        self.assertEqual(r['altas_pedidas'][0]['accion'], 'alta')
        self.assertEqual(self.codigos(r['avisos_lote']), ['nombre_parecido', 'alta_nueva'])
        self.assertEqual(r['avisos_lote'][0]['detalle'], 'Mikell ~ Mikel')

    def test_altas_repetidas_en_la_lista(self):
        r = self.ing(lote([], altas=['Rafa', 'rafa', ' RAFA ']), escribir=True)
        self.assertEqual([e['accion'] for e in r['altas_pedidas']], ['alta', 'sin_cambios', 'sin_cambios'])
        self.assertEqual(len(self.cat()['trabajadores']), 1)

    def test_un_lote_solo_con_altas_es_valido(self):
        r = self.ing(lote([], altas=['Rafa']), escribir=True)
        self.assertTrue(r['ok'])
        self.assertEqual(r['jornadas'], [])


class TestOrden(Base):
    def test_renombre_antes_que_las_jornadas(self):
        self.sembrar()
        l = lote([jor('vivienda', '2026-10-23', [('Mikel Etxeberria', 7.5, 0), ('Txomin', 8, 0.5)]),
                  jor('garaje', '2026-10-21', [('Mikel', 7.5, 0)])], renombres=[ren('Mikel', 'Mikel Etxeberria')])
        r = self.ing(l, escribir=True)
        self.assertEqual(len(self.cat()['trabajadores']), 3, 'nadie nuevo: caen en la persona que ya existe')
        self.assertEqual(r['jornadas'][0]['avisos'], [])
        self.assertEqual(r['jornadas'][1]['avisos'],
                         [{'codigo': 'nombre_anterior_usado', 'detalle': 'Mikel -> Mikel Etxeberria'}])
        por_dia = {j['fecha']: sorted(p['id'] for p in j['presentes'])
                   for j in P.cargar_obra(self.raiz, OBRAS, 'olabeaga')['jornadas'] if j['fecha'] != '2026-10-22'}
        self.assertEqual(por_dia, {'2026-10-23': ['T0001', 'T0002'], '2026-10-21': ['T0001']})

    def test_dos_nombres_de_la_misma_persona_en_una_jornada(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        r = self.ing(lote([jor('vivienda', '2026-10-21', [('Mikel Etxeberria', 7.5, 0), ('Mikel', 7.5, 0)])]))
        self.assertEqual((r['jornadas'][0]['estado'], r['jornadas'][0]['rechazos']), ('rechazada', ['presente_duplicado']))
        self.assertEqual(r['jornadas'][0]['avisos'], [], 'una jornada rechazada no avisa de personas que no se crean')

    def test_altas_antes_que_las_jornadas(self):
        l = lote([jor('vivienda', '2026-10-22', [('Nuevo', 7.5, 0)])], altas=['Nuevo'])
        r = self.ing(l, escribir=True)
        self.assertEqual(self.codigos(r['avisos_lote']), ['alta_nueva'])
        self.assertEqual(self.codigos(r['jornadas'][0]['avisos']), [], 'la jornada ya lo encuentra dado de alta')
        self.assertEqual(len(self.cat()['trabajadores']), 1)

    def test_horario_propio_con_nombre_nuevo_tras_renombre(self):
        self.sembrar()
        horario = {'lun': 8, 'mar': 8, 'mie': 8, 'jue': 8, 'vie': 8}
        r = self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')], excepciones_horario={'Mikel Etxeberria': horario}),
                     escribir=True)
        self.assertEqual((r['excepciones'][0]['id'], r['excepciones'][0]['accion']), ('T0001', 'fijada'))
        self.assertEqual(len(self.cat()['trabajadores']), 3)

    def test_horario_propio_con_nombre_antiguo(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        horario = {'lun': 8, 'mar': 8, 'mie': 8, 'jue': 8, 'vie': 8}
        r = self.ing(lote([], excepciones_horario={'Mikel': horario}), escribir=True)
        self.assertEqual((r['excepciones'][0]['id'], r['excepciones'][0]['accion']), ('T0001', 'fijada'))
        self.assertEqual(r['avisos_lote'], [{'codigo': 'nombre_anterior_usado', 'detalle': 'Mikel -> Mikel Etxeberria'}])
        self.assertEqual(len(self.cat()['trabajadores']), 3)


class TestNombresAnteriores(Base):
    def test_lote_viejo_con_el_nombre_antiguo(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        h = self.hashes()
        r = self.ing(L1, escribir=True)
        self.assertEqual(self.hashes(), h, 'el mismo lote de antes no cambia nada')
        self.assertEqual([j['accion'] for j in r['jornadas']], ['sin_cambios', 'sin_cambios'])
        self.assertEqual(r['jornadas'][0]['avisos'], [{'codigo': 'nombre_anterior_usado', 'detalle': 'Mikel -> Mikel Etxeberria'}])
        self.assertEqual(r['jornadas'][1]['avisos'], [])
        self.assertEqual(len(self.cat()['trabajadores']), 3)

    def test_lote_viejo_con_otra_hora_se_asigna_a_la_misma_persona(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        r = self.ing(lote([jor('vivienda', '2026-10-21', [('Mikel', 6, 0)])]), escribir=True)
        self.assertEqual(r['jornadas'][0]['accion'], 'alta')
        self.assertEqual(self.codigos(r['jornadas'][0]['avisos']), ['nombre_anterior_usado'])
        self.assertEqual(len(self.cat()['trabajadores']), 3)
        self.assertEqual([f['nombre'] for f in P.aplanar(self.raiz, OBRAS, 'olabeaga') if f['fecha'] == '2026-10-21'],
                         ['Mikel Etxeberria'])

    def test_el_nombre_actual_manda_sobre_el_anterior(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        r = self.ing(lote([], renombres=[ren('Txomin', 'Mikel')]), escribir=True)
        self.assertEqual(r['renombres'][0]['accion'], 'renombrado', '«Mikel» era solo un nombre antiguo de otra persona')
        self.assertEqual(self.persona('T0002')['nombre'], 'Mikel')
        r2 = self.ing(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5, 0)])]))
        self.assertEqual(self.codigos(r2['jornadas'][0]['avisos']), [], 'sin aviso: es el nombre actual de T0002')

    def test_alta_con_un_nombre_actual_de_uno_y_anterior_de_otro_va_al_actual(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        self.ing(lote([], renombres=[ren('Txomin', 'Mikel')]), escribir=True)
        r = self.ing(lote([], altas=['Mikel']))
        self.assertEqual((r['altas_pedidas'][0]['id'], r['altas_pedidas'][0]['accion']), ('T0002', 'sin_cambios'))
        self.assertEqual(r['avisos_lote'], [])

    def test_comprobar_nombres_anteriores(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])
        malos = [None, 'Mikel', [5], [''], ['Mikel', 'mikel'], ['Mikel Etxeberria'], ['Mikel<b>']]
        for m in malos:
            c = self.cat()
            for t in c['trabajadores']:
                if t['id'] == 'T0001':
                    t['nombres_anteriores'] = m
            P.guardar_catalogo(self.raiz, c)
            self.assertTrue(any('nombres_anteriores' in x for x in P.comprobar(self.raiz, OBRAS)), repr(m))

    def test_el_estado_de_la_tablet_solo_lleva_el_historial_de_quien_lo_tiene(self):
        # 08e: antes (08a) exigia EXACTAMENTE 5 claves en cada persona. Ahora el estado publica tambien nombres_anteriores
        # (y fusionados) para la pestana «Base de trabajadores», pero SOLO de quien tiene historial: el resto sigue con
        # las 5 claves de siempre y la tablet ignora las claves que no conoce (lo prueba test_base_trabajadores_08e).
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel Etxeberria')]), escribir=True)
        s = P.exportar_estado(self.raiz, OBRAS, generado=AHORA)
        d = json.loads(s[s.index('{'):s.rindex('}') + 1])
        base = {'id', 'nombre', 'categoria', 'empresa', 'activo'}
        con_historial = [t for t in d['catalogo'] if set(t) != base]
        self.assertEqual(['Mikel Etxeberria'], [t['nombre'] for t in con_historial])
        self.assertEqual(base | {'nombres_anteriores'}, set(con_historial[0]))
        self.assertEqual(['Mikel'], con_historial[0]['nombres_anteriores'])
        self.assertTrue(all(set(t) == base for t in d['catalogo'] if t not in con_historial))
        self.assertIn('Mikel Etxeberria', [t['nombre'] for t in d['catalogo']])


class TestSha(Base):
    def test_traza_con_sha_y_linea_recibido(self):
        r = self.ing(L1, escribir=True, sha256=SHA1, fichero=FICH1)
        self.assertTrue(r['ok'] and r['escrito'] and r['recibido'], r)
        tr = self.traza()
        self.assertEqual([x['accion'] for x in tr], ['obra_creada', 'alta', 'alta', 'recibido'])
        for x in tr:
            self.assertEqual((x['sha256'], x['fichero']), (SHA1, FICH1))
        rec = tr[-1]
        self.assertEqual((rec['obra'], rec['ambito'], rec['fecha'], rec['n_presentes'], rec['rechazadas']),
                         ('olabeaga', None, None, 0, 0))
        self.assertIn('alta_nueva', rec['avisos'])
        self.assertEqual(len(rec['avisos']), len(set(rec['avisos'])), 'los códigos del resumen no se repiten')
        self.assertEqual(P.shas_recibidos(self.raiz, OBRAS, 'olabeaga'), {SHA1})
        self.assertEqual(P.shas_recibidos(self.raiz, OBRAS, 'mungia'), set())

    def test_mismo_fichero_dos_veces_no_cambia_ni_un_byte(self):
        self.ing(L1, escribir=True, sha256=SHA1, fichero=FICH1)
        h = self.hashes()
        r = self.ing(L1, escribir=True, sha256=SHA1, fichero=FICH1)
        self.assertFalse(r['escrito'])
        self.assertFalse(r['recibido'])
        self.assertEqual(self.hashes(), h)

    def test_sin_sha_todo_como_antes(self):
        self.ing(L1, escribir=True)
        tr = self.traza()
        self.assertEqual([x['accion'] for x in tr], ['alta', 'alta'])
        for x in tr:
            self.assertFalse({'sha256', 'fichero', 'rechazadas'} & set(x), x)
        self.assertEqual(P.shas_recibidos(self.raiz, OBRAS, 'olabeaga'), set())

    def test_fichero_sin_novedades_solo_deja_la_linea_recibido(self):
        self.ing(L1, escribir=True)
        antes = self.hashes()
        r = self.ing(L1, escribir=True, sha256=SHA2, fichero='otro.json')
        self.assertTrue(r['escrito'] and r['recibido'])
        despues = self.hashes()
        cambiados = [k for k in despues if antes.get(k) != despues[k]]
        self.assertEqual(cambiados, ['2026 OLABEAGA BILBAO/INFORME SAGARDE IA/personal_jornadas.jsonl'])
        self.assertEqual([x['accion'] for x in self.traza()][-1], 'recibido')
        h = self.hashes()
        self.ing(L1, escribir=True, sha256=SHA2, fichero='otro.json')
        self.assertEqual(self.hashes(), h)

    def test_jornadas_rechazadas_se_cuentan_en_recibido(self):
        l = lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)]), jor('garaje', '2026-10-22', [('Andoni', 99, 0)])])
        r = self.ing(l, escribir=True, sha256=SHA1, fichero=FICH1)
        self.assertFalse(r['ok'])
        rec = self.traza()[-1]
        self.assertEqual((rec['accion'], rec['rechazadas']), ('recibido', 1))
        self.assertEqual(P.shas_recibidos(self.raiz, OBRAS, 'olabeaga'), {SHA1})

    def test_la_primera_vez_crea_la_obra_aunque_todo_se_rechace(self):
        l = lote([jor('vivienda', '2026-10-22', [('Mikel', 99, 0)])])
        r = self.ing(l, escribir=True, sha256=SHA1, fichero=FICH1)
        self.assertFalse(r['ok'])
        self.assertTrue(r['obra_creada'])
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        self.assertTrue(os.path.exists(os.path.join(self.ruta_obra(), 'personal_obra.json')))
        self.assertEqual((ob['obra'], ob['jornada_base_h'], ob['horario_semanal'], ob['jornadas']), ('olabeaga', 7.5, H_BASE, []))
        self.assertEqual([x['accion'] for x in self.traza()], ['obra_creada', 'recibido'])
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])

    def test_sin_sha_un_lote_todo_rechazado_no_crea_nada(self):
        r = self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 99, 0)])]), escribir=True)
        self.assertFalse(r['ok'] or r['escrito'] or r['obra_creada'])
        self.assertEqual(self.hashes(), {})

    def test_obra_creada_solo_una_vez(self):
        self.ing(L1, escribir=True, sha256=SHA1, fichero=FICH1)
        self.assertEqual([x['accion'] for x in self.traza()].count('obra_creada'), 1)
        r = self.ing(lote([jor('vivienda', '2026-10-24', [('Mikel', 7.5, 0)])]), escribir=True, sha256=SHA2, fichero='b.json')
        self.assertFalse(r['obra_creada'])
        self.assertEqual([x['accion'] for x in self.traza()].count('obra_creada'), 1)

    def test_lote_rechazado_no_deja_sha(self):
        r = self.ing({'tipo': 'otra_cosa'}, escribir=True, sha256=SHA1, fichero=FICH1)
        self.assertFalse(r['ok'])
        self.assertEqual(self.hashes(), {})
        self.assertEqual(P.shas_recibidos(self.raiz, OBRAS, 'olabeaga'), set())

    def test_un_sha256_mal_formado_se_rechaza_antes_de_tocar_nada(self):
        for malo in ('abc', 'zz' * 32, 'a' * 63, 'a' * 65, 5, ['a' * 64]):
            with self.assertRaises(ValueError, msg=repr(malo)):
                self.ing(L1, escribir=True, sha256=malo)
        self.assertEqual(self.hashes(), {})

    def test_simulacion_con_sha_no_escribe(self):
        r = self.ing(L1, escribir=False, sha256=SHA1, fichero=FICH1)
        self.assertFalse(r['escrito'])
        self.assertEqual(self.hashes(), {})

    def test_las_lineas_de_renombre_y_alta_llevan_el_sha(self):
        self.sembrar()
        self.ing(lote([], renombres=[ren('Mikel', 'Mikel B')], altas=['Rafa']), escribir=True, sha256=SHA1, fichero=FICH1)
        tr = [x for x in self.traza() if x.get('sha256')]
        self.assertEqual([x['accion'] for x in tr], ['renombre', 'alta_persona', 'recibido'])

    def test_shas_recibidos_tolera_lineas_malas_pero_no_un_fichero_ilegible(self):
        self.ing(L1, escribir=True, sha256=SHA1, fichero=FICH1)
        p = os.path.join(self.ruta_obra(), 'personal_jornadas.jsonl')
        with open(p, 'ab') as fh:
            fh.write(b'esto no es json\n\n[1,2]\n{"sha256": 5}\n')
        self.assertEqual(P.shas_recibidos(self.raiz, OBRAS, 'olabeaga'), {SHA1})
        os.remove(p)
        os.makedirs(p)
        with self.assertRaises(OSError):
            P.shas_recibidos(self.raiz, OBRAS, 'olabeaga')


class TestAltaObra(Base):
    def test_alta_obra(self):
        r = P.alta_obra(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual((r['creada'], bool(r['ruta'])), (False, True))
        self.assertEqual(self.hashes(), {})
        r = P.alta_obra(self.raiz, OBRAS, 'olabeaga', escribir=True)
        self.assertTrue(r['creada'])
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual((ob['horario_semanal'], ob['jornadas'], ob['excepciones_horario']), (H_BASE, [], {}))
        h = self.hashes()
        r = P.alta_obra(self.raiz, OBRAS, 'olabeaga', escribir=True)
        self.assertFalse(r['creada'])
        self.assertEqual(self.hashes(), h)
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])
        with self.assertRaises(ValueError):
            P.alta_obra(self.raiz, OBRAS, 'no_existe', escribir=True)


class TestEstadoEnMemoria(Base):
    L2 = lote([jor('vivienda', '2026-10-22', [('Mikel', 8, 0.5), ('Aitor', 7.5, 0)]),
               jor('vivienda', '2026-10-23', [('Mikel', 7.5, 0)])], renombres=[ren('Txomin', 'Txomin Zubia')], altas=['Rafa'])
    L3 = lote([{'ambito': 'garaje', 'fecha': '2026-10-22', 'anulada': True, 'presentes': []}],
              excepciones_horario={'Rafa': {'lun': 8, 'mar': 8, 'mie': 8, 'jue': 8, 'vie': 8}})

    def sin_escrito(self, r):
        r = copy.deepcopy(r)
        r.pop('escrito')
        return r

    def test_simulacion_en_memoria_no_toca_el_disco_y_da_lo_mismo(self):
        est = P.cargar_estado(self.raiz, OBRAS)
        h = self.hashes()
        r_mem = P.ingerir_lote(copy.deepcopy(L1), self.raiz, OBRAS, HOY, ahora=AHORA, estado=est)
        self.assertEqual(self.hashes(), h)
        self.assertEqual(self.sin_escrito(r_mem), self.sin_escrito(self.ing(L1)))
        self.assertEqual(len(est['cat']['trabajadores']), 3, 'el estado en memoria sí cambia')
        self.assertTrue(est['ods']['olabeaga']['jornadas'])

    def test_cadena_en_memoria_igual_que_cadena_en_disco(self):
        est = P.cargar_estado(self.raiz, OBRAS)
        en_mem = [P.ingerir_lote(copy.deepcopy(l), self.raiz, OBRAS, HOY, ahora=AHORA, estado=est) for l in (L1, self.L2, self.L3)]
        self.assertEqual(self.hashes(), {})
        en_disco = [self.ing(l, escribir=True) for l in (L1, self.L2, self.L3)]
        for a, b in zip(en_mem, en_disco):
            self.assertEqual(self.sin_escrito(a), self.sin_escrito(b))
        self.assertEqual(est['cat']['trabajadores'], self.cat()['trabajadores'])
        self.assertEqual(P.aplanar(self.raiz, OBRAS, 'olabeaga', estado=est), P.aplanar(self.raiz, OBRAS, 'olabeaga'))
        self.assertEqual(P.totales_control(self.raiz, OBRAS, 'olabeaga', estado=est),
                         P.totales_control(self.raiz, OBRAS, 'olabeaga'))
        self.assertEqual(P.totales_control(self.raiz, OBRAS, estado=est), P.totales_control(self.raiz, OBRAS))
        self.assertEqual(est['ods']['olabeaga']['excepciones_horario'], P.cargar_obra(self.raiz, OBRAS, 'olabeaga')['excepciones_horario'])

    def test_lote_rechazado_no_cambia_el_estado(self):
        est = P.cargar_estado(self.raiz, OBRAS)
        P.ingerir_lote(copy.deepcopy(L1), self.raiz, OBRAS, HOY, ahora=AHORA, estado=est)
        antes = copy.deepcopy(est)
        r = P.ingerir_lote({'tipo': 'otra_cosa'}, self.raiz, OBRAS, HOY, ahora=AHORA, estado=est)
        self.assertFalse(r['ok'])
        self.assertEqual(est, antes)

    def test_escribir_y_estado_son_incompatibles(self):
        est = P.cargar_estado(self.raiz, OBRAS)
        with self.assertRaises(ValueError):
            P.ingerir_lote(copy.deepcopy(L1), self.raiz, OBRAS, HOY, escribir=True, ahora=AHORA, estado=est)
        self.assertEqual(self.hashes(), {})

    def test_cargar_estado_lee_el_disco(self):
        self.sembrar()
        est = P.cargar_estado(self.raiz, OBRAS)
        self.assertEqual(est['cat'], self.cat())
        self.assertEqual(sorted(est['ods']), ['mungia', 'olabeaga'])
        self.assertEqual(est['ods']['olabeaga'], P.cargar_obra(self.raiz, OBRAS, 'olabeaga'))
        est['cat']['trabajadores'].clear()
        self.assertEqual(len(self.cat()['trabajadores']), 3, 'el estado es una copia')


class TestRenombrar(Base):
    def dos_obras(self):
        self.sembrar()
        self.ing(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5, 0)])], obra='mungia'), escribir=True)

    def test_vista_previa_y_escritura_por_nombre(self):
        self.dos_obras()
        h = self.hashes()
        r = P.renombrar(self.raiz, OBRAS, 'Mikel', 'Mikel Etxeberria', ahora=AHORA)
        self.assertTrue(r['ok'], r)
        self.assertEqual((r['accion'], r['id'], r['de'], r['a'], r['escrito']), ('renombrado', 'T0001', 'Mikel', 'Mikel Etxeberria', False))
        self.assertEqual(r['trazas_en'], ['mungia', 'olabeaga'])
        self.assertEqual(self.hashes(), h)
        r = P.renombrar(self.raiz, OBRAS, 'Mikel', 'Mikel Etxeberria', escribir=True, ahora=AHORA)
        self.assertTrue(r['escrito'])
        t = self.persona('T0001')
        self.assertEqual((t['nombre'], t['nombres_anteriores']), ('Mikel Etxeberria', ['Mikel']))
        for o in ('olabeaga', 'mungia'):
            ult = self.traza(o)[-1]
            self.assertEqual((ult['accion'], ult['id'], ult['de'], ult['a'], ult['ts']),
                             ('renombre', 'T0001', 'Mikel', 'Mikel Etxeberria', AHORA))
        self.assertEqual(self.traza('olabeaga')[-1]['fecha'], None)
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])

    def test_por_id(self):
        self.dos_obras()
        r = P.renombrar(self.raiz, OBRAS, 'T0002', 'Txomin Zubia', escribir=True, ahora=AHORA)
        self.assertTrue(r['ok'], r)
        self.assertEqual(self.persona('T0002')['nombre'], 'Txomin Zubia')
        self.assertEqual(r['trazas_en'], ['olabeaga'])

    def test_por_nombre_anterior(self):
        self.dos_obras()
        P.renombrar(self.raiz, OBRAS, 'Mikel', 'Mikel B', escribir=True, ahora=AHORA)
        r = P.renombrar(self.raiz, OBRAS, 'Mikel', 'Mikel C', escribir=True, ahora=AHORA)
        self.assertTrue(r['ok'], r)
        self.assertEqual(self.persona('T0001')['nombres_anteriores'], ['Mikel', 'Mikel B'])
        self.assertEqual(self.codigos(r['avisos']), ['nombre_anterior_usado'])

    def test_sin_cambios(self):
        self.dos_obras()
        h = self.hashes()
        r = P.renombrar(self.raiz, OBRAS, 'T0001', 'Mikel', escribir=True, ahora=AHORA)
        self.assertEqual((r['ok'], r['accion'], r['escrito']), (True, 'sin_cambios', False))
        self.assertEqual(self.hashes(), h)

    def test_errores(self):
        self.dos_obras()
        h = self.hashes()
        casos = [
            (('Fulano', 'Otro'), 'persona_inexistente'), (('T0099', 'Otro'), 'persona_inexistente'),
            (('Mikel', ''), 'nombre_invalido'), (('Mikel', 'x' * 61), 'nombre_invalido'), (('Mikel', '12345678Z'), 'nombre_invalido'),
            (('Mikel', 'Mi<b>'), 'nombre_invalido'), (('Mikel', 'Txomin'), 'coincide_con_otro'),
        ]
        for args, error in casos:
            r = P.renombrar(self.raiz, OBRAS, *args, escribir=True, ahora=AHORA)
            self.assertEqual((r['ok'], r['error'], r['escrito']), (False, error, False), (args, r))
        r = P.renombrar(self.raiz, OBRAS, 'Mikel', 'Txomin', ahora=AHORA)
        self.assertEqual((r['id'], r['id_otro']), ('T0001', 'T0002'))
        self.assertIn('fusionar T0001 T0002', r['orden'])
        self.assertEqual(self.hashes(), h)

    def test_persona_fusionada_por_id(self):
        self.dos_obras()
        self.assertTrue(P.fusionar(self.raiz, 'T0001', 'T0003', escribir=True)['ok'])
        h = self.hashes()
        r = P.renombrar(self.raiz, OBRAS, 'T0001', 'Otro', escribir=True, ahora=AHORA)
        self.assertEqual((r['ok'], r['error']), (False, 'persona_fusionada'))
        self.assertEqual(self.hashes(), h)

    def test_una_persona_que_solo_tiene_horario_propio_deja_traza_en_esa_obra(self):
        horario = {'lun': 8, 'mar': 8, 'mie': 8, 'jue': 8, 'vie': 8}
        self.ing(lote([], obra='mungia', excepciones_horario={'Rafa': horario}), escribir=True)
        r = P.renombrar(self.raiz, OBRAS, 'Rafa', 'Rafael', escribir=True, ahora=AHORA)
        self.assertEqual((r['ok'], r['trazas_en']), (True, ['mungia']))
        self.assertEqual(self.traza('mungia')[-1]['accion'], 'renombre')

    def test_persona_sin_jornadas_solo_cambia_la_base(self):
        self.ing(lote([], altas=['Rafa']), escribir=True)
        r = P.renombrar(self.raiz, OBRAS, 'Rafa', 'Rafael', escribir=True, ahora=AHORA)
        self.assertTrue(r['ok'] and r['escrito'], r)
        self.assertEqual(r['trazas_en'], [])
        self.assertEqual(self.persona('T0001')['nombre'], 'Rafael')

    def test_linea_de_comandos(self):
        self.dos_obras()
        base = ['--raiz', self.raiz, '--obras', ','.join('%s=%s' % kv for kv in OBRAS.items())]

        def correr(*a):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cod = P.main(list(a))
            return cod, buf.getvalue()

        h = self.hashes()
        cod, out = correr('renombrar', 'Mikel', 'Mikel Etxeberria', *base)
        self.assertEqual(cod, 0, out)
        self.assertIn('Vista previa', out)
        self.assertEqual(self.hashes(), h)
        cod, out = correr('renombrar', 'Mikel', 'Mikel Etxeberria', '--escribir', *base)
        self.assertEqual(cod, 0, out)
        self.assertEqual(self.persona('T0001')['nombre'], 'Mikel Etxeberria')
        cod, out = correr('renombrar', 'Fulano', 'Otro', '--escribir', *base)
        self.assertEqual(cod, 2, out)
        self.assertNotIn('persona_inexistente', out)
        cod, out = correr('renombrar', 'Txomin', 'Mikel Etxeberria', *base)
        self.assertEqual(cod, 2, out)
        self.assertIn('fusionar T0002 T0001', out)


class TestTextos(unittest.TestCase):
    PALABRAS = re.compile(r'\b(exportar|exportad\w*|importar|importad\w*|lotes?|ingerir|ingesta|json|pendientes?|alta|altas|'
                          r'simulaci\w+|estado|base de datos)\b', re.I)
    EJEMPLOS = [
        ('alta_nueva', 'Asensio', 'Nombre nuevo: «Asensio» no estaba en la base; se añade.'),
        ('nombre_parecido', 'Mikell ~ Mikel', 'Se parecen: «Mikell» y «Mikel». ¿Es la misma persona?'),
        ('suma_diaria_alta', 'Rafa', 'Rafa suma más de 12 horas ese día entre todas las obras.'),
        ('suma_diaria_alta', 'Rafa, Mikel', 'Rafa, Mikel suman más de 12 horas ese día entre todas las obras.'),
        ('suma_diaria_alta', None, 'Alguien suma más de 12 horas ese día entre todas las obras.'),
        ('fecha_futura', '2026-10-30', 'La jornada es de una fecha que aún no ha llegado (30/10): ¿es una errata?'),
        ('reemplazo', None, 'Ya había una jornada de ese día en esa obra: la nueva la sustituye.'),
        ('traza_no_escrita', 'PermissionError', 'Guardado bien, pero no se pudo anotar en el registro.'),
        ('renombre_coincide_con_otro', 'Mikel -> Txomin (T0001, T0002)',
         'No se ha cambiado «Mikel»: «Txomin» ya es otra persona de la base. Si son la misma persona hay que juntarlas.'),
        ('renombre_sin_origen', 'Fantasma', '«Fantasma» no estaba en la base: no hay nada que cambiar de nombre.'),
        ('nombre_anterior_usado', 'Mikel -> Mikel Etxeberria',
         '«Mikel» es un nombre antiguo de «Mikel Etxeberria»: se ha tomado como la misma persona.'),
        # 08c2a: el campo Empresa
        ('empresa_sin_persona', 'Fantasma', '«Fantasma» no estaba en la base: no se le puede poner empresa.'),
    ]
    RECHAZOS = {
        'lote_invalido': 'El fichero no tiene el formato esperado.',
        'tipo_desconocido': 'Este fichero no es un control horario.',
        'version_desconocida': 'Este control horario es de una versión que este PC no conoce.',
        'obra_invalida': 'La obra que figura en el fichero no existe en Sagarde.',
        'campo_desconocido': 'El fichero trae algo que no se esperaba.',
        'horario_invalido': 'El horario de la obra viene mal escrito.',
        'excepcion_invalida': 'Un horario especial viene mal escrito.',
        'renombre_invalido': 'Un cambio de nombre viene mal escrito.',
        'alta_invalida': 'Un nombre de la lista de nuevos viene mal escrito.',
        'empresa_invalida': 'Una empresa viene mal escrita.',
        'ambito_invalido': 'Una jornada no dice si es de viviendas o de garajes.',
        'fecha_invalida': 'Una jornada tiene una fecha que no existe.',
        'sin_presentes': 'Una jornada no tiene a nadie apuntado.',
        'nombre_vacio': 'Hay un trabajador sin nombre.',
        'nombre_invalido': 'Hay un nombre que no vale (vacío, demasiado largo o con signos raros).',
        'horas_invalidas': 'Hay unas horas que no valen (deben estar entre 0 y 24).',
        'extra_invalido': 'Hay unas horas extra que no valen.',
        'presente_duplicado': 'Una persona sale dos veces el mismo día.',
        'anulada_con_presentes': 'Una jornada anulada no puede llevar gente.',
        'jornada_repetida_en_lote': 'El mismo día y el mismo ámbito aparece dos veces en el fichero.',
        'suma_diaria_invalida': 'Alguien suma más de 24 horas ese día entre todas las obras.',
        'persona_inexistente': 'No hay nadie en la base con ese nombre ni con ese número.',
        'persona_fusionada': 'Esa persona ya está juntada con otra: cambia el nombre de la otra.',
        'coincide_con_otro': 'Ese nombre ya es de otra persona. Si son la misma persona hay que juntarlas.',
    }

    def test_ejemplos_exactos(self):
        for codigo, detalle, esperado in self.EJEMPLOS:
            self.assertEqual(P.texto_aviso(codigo, detalle), esperado, codigo)

    def test_rechazos_exactos(self):
        for codigo, esperado in self.RECHAZOS.items():
            self.assertEqual(P.texto_aviso(codigo), esperado, codigo)
            self.assertEqual(P.texto_aviso(codigo, 'lo que sea'), esperado, codigo)

    def test_ningun_texto_lleva_palabras_de_programador_ni_el_codigo(self):
        todos = [(c, d) for c, d, _ in self.EJEMPLOS] + [(c, None) for c in self.RECHAZOS]
        for codigo, detalle in todos:
            t = P.texto_aviso(codigo, detalle)
            self.assertIsInstance(t, str)
            self.assertTrue(t.strip())
            self.assertIsNone(self.PALABRAS.search(t), (codigo, t))
            self.assertNotIn(codigo, t)
            self.assertNotIn('_', t)

    def test_sin_detalle_no_falla(self):
        for codigo in [c for c, _, _ in self.EJEMPLOS] + list(self.RECHAZOS):
            self.assertIsInstance(P.texto_aviso(codigo, None), str)
            self.assertIsInstance(P.texto_aviso(codigo), str)
            self.assertIsInstance(P.texto_aviso(codigo, 'sin el formato esperado'), str)

    def test_sin_detalle_o_con_un_detalle_raro_tampoco_se_cuela_el_codigo(self):
        for codigo in [c for c, _, _ in self.EJEMPLOS] + list(self.RECHAZOS):
            for detalle in (None, '', 'sin el formato esperado'):
                t = P.texto_aviso(codigo, detalle)
                self.assertNotIn(codigo, t, (codigo, detalle))
                self.assertNotIn('_', t, (codigo, detalle))
                self.assertIsNone(self.PALABRAS.search(t), (codigo, t))

    def test_codigo_desconocido_no_falla(self):
        self.assertIn('inventado_x', P.texto_aviso('inventado_x', None))

    def test_cada_codigo_que_emite_p1_tiene_texto(self):
        fuente = open(P.__file__, encoding='utf-8').read()
        emitidos = set(re.findall(r'"codigo":\s*"([a-z_]+)"', fuente))
        emitidos |= {c for c in re.findall(r'e\.append\("([a-z_]+)"\)', fuente)}
        conocidos = {c for c, _, _ in self.EJEMPLOS} | set(self.RECHAZOS)
        self.assertGreaterEqual(len(emitidos), 15, emitidos)
        self.assertEqual(sorted(emitidos - conocidos), [], 'códigos que P1 emite y no tienen texto en llano')


class TestSumaDiariaDetalle(Base):
    def test_el_aviso_nombra_a_quien_pasa_de_12_horas(self):
        l = lote([jor('vivienda', '2026-10-22', [('Mikel', 8, 0), ('Txomin', 7, 0)]),
                  jor('garaje', '2026-10-22', [('Mikel', 5, 0), ('Txomin', 4, 0)])])
        r = self.ing(l)
        self.assertNotIn('suma_diaria_alta', self.codigos(r['jornadas'][0]['avisos']))
        self.assertEqual(r['jornadas'][1]['avisos'], [{'codigo': 'suma_diaria_alta', 'detalle': 'Mikel'}])

    def test_varios_nombres_ordenados(self):
        l = lote([jor('vivienda', '2026-10-22', [('Txomin', 13, 0), ('Mikel', 12.5, 0)])])
        r = self.ing(l)
        av = [a for a in r['jornadas'][0]['avisos'] if a['codigo'] == 'suma_diaria_alta']
        self.assertEqual(av, [{'codigo': 'suma_diaria_alta', 'detalle': 'Mikel, Txomin'}])


def setUpModule():
    global TMP, _TMP_OBJ
    _TMP_OBJ = tempfile.TemporaryDirectory(prefix='personal_08a_')
    TMP = _TMP_OBJ.name


def tearDownModule():
    _TMP_OBJ.cleanup()


if __name__ == '__main__':
    unittest.main()
