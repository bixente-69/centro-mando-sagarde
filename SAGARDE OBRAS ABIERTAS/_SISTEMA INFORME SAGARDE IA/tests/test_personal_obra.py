# -*- coding: utf-8 -*-
"""Pruebas de personal_obra.py (P1 de «Personal en obra»): ingesta, fusiones, horarios propios,
estado para la tablet, comprobaciones y línea de comandos. unittest de la biblioteca estándar.
Las cifras esperadas están calculadas a mano. Vienen del verificador de staging (paso 06): no se
ha cambiado ninguna prueba, solo de dónde sale el módulo y dónde se crean las carpetas temporales."""
import ast
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid

import tempfile

MOTOR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # _SISTEMA INFORME SAGARDE IA
sys.path.insert(0, MOTOR)
import personal_obra as P

TMP = None  # carpeta temporal del módulo (setUpModule)
_TMP_OBJ = None
OBRAS = {'olabeaga': '2026 OLABEAGA BILBAO', 'mungia': '2026 MUNGIA ACR NEINOR'}
HOY = '2026-10-23'
AHORA = '2026-10-23T22:00:00+02:00'
H_BASE = {'lun': 7.5, 'mar': 7.5, 'mie': 7.5, 'jue': 7.5, 'vie': 7.5, 'sab': 0, 'dom': 0}


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


L1 = lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0), ('Txomin', 7.5, 0)]),
           jor('garaje', '2026-10-22', [('Andoni', 7.5, 0)])])

# escenario con cifras a mano (obra olabeaga + una jornada de mungia)
ESC = lote([jor('vivienda', '2026-10-19', [('Mikel', 7.5, 0), ('Txomin', 7.5, 0)]),
            jor('vivienda', '2026-10-20', [('Mikel', 9.5, 2)]),
            jor('garaje', '2026-10-20', [('Txomin', 7.5, 0)]),
            jor('vivienda', '2026-10-24', [('Mikel', 5, 5)])])
ESC_M = lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5, 0)])], obra='mungia')


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
            shutil.rmtree(d + '_entrada', ignore_errors=True)

    def ing(self, l, escribir=False, hoy=HOY, ahora=AHORA):
        return P.ingerir_lote(copy.deepcopy(l), self.raiz, OBRAS, hoy, escribir=escribir, ahora=ahora)

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

    def ruta_cat(self):
        return os.path.join(self.raiz, '_SISTEMA INFORME SAGARDE IA', 'personal_catalogo.json')

    def codigos(self, avisos):
        return [a['codigo'] for a in avisos]


J_MIKEL = jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])


class HorarioPropioBase(Base):
    """Paso 01b: horario propio por trabajador (`excepciones_horario` en el lote, en personal_obra.json por id y en el estado por nombre)."""

    def estado(self):
        s = P.exportar_estado(self.raiz, OBRAS, generado=AHORA)
        return json.loads(s[s.index('{'):s.rindex('}') + 1])

    def exc_est(self, obra='olabeaga'):
        return self.estado()['obras'][obra]['excepciones_horario']

    def exc_obra(self, obra='olabeaga'):
        return P.cargar_obra(self.raiz, OBRAS, obra)['excepciones_horario']

    def traza(self, obra='olabeaga'):
        with open(os.path.join(self.ruta_obra(obra), 'personal_jornadas.jsonl'), encoding='utf-8') as fh:
            return [json.loads(x) for x in fh.read().splitlines()]

    def editar_obra(self, fn, obra='olabeaga'):
        ruta = os.path.join(self.ruta_obra(obra), 'personal_obra.json')
        with open(ruta, encoding='utf-8') as fh:
            d = json.load(fh)
        fn(d)
        with open(ruta, 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False)


class TestNombres(unittest.TestCase):
    def test_limpiar(self):
        self.assertEqual(P.limpiar_nombre('  El   Gallego '), 'El Gallego')
        self.assertEqual(P.limpiar_nombre('a\t b\n c'), 'a b c')
        self.assertEqual(P.limpiar_nombre(None), '')
        self.assertEqual(P.limpiar_nombre(12), '')

    def test_valido(self):
        self.assertTrue(P.nombre_valido('Mikel'))
        self.assertTrue(P.nombre_valido('x' * 60))
        self.assertFalse(P.nombre_valido(''))
        self.assertFalse(P.nombre_valido('   '))
        self.assertFalse(P.nombre_valido('x' * 61))
        self.assertFalse(P.nombre_valido('Mi\x00kel'))
        self.assertFalse(P.nombre_valido(None))

    def test_clave(self):
        self.assertEqual(P.clave_nombre('  Iñaki '), 'inaki')
        self.assertEqual(P.clave_nombre('EL  gallego'), 'el gallego')
        self.assertEqual(P.clave_nombre('Mikel'), P.clave_nombre(' mikel  '))


class TestIngestaLimpia(Base):
    def test_dry_run_no_escribe(self):
        r = self.ing(L1)
        self.assertTrue(r['ok'], r)
        self.assertFalse(r['escrito'])
        self.assertEqual(self.hashes(), {}, 'en simulación no se debe crear ningún fichero')
        self.assertEqual(r['lote_rechazado'], [])
        self.assertEqual(len(r['jornadas']), 2)
        for j in r['jornadas']:
            self.assertEqual(j['estado'], 'aceptada')
            self.assertEqual(j['accion'], 'alta')
            self.assertEqual(j['rechazos'], [])
        self.assertEqual(r['jornadas'][0]['clave'], ['olabeaga', 'vivienda', '2026-10-22'])
        self.assertEqual(r['altas'], [{'id': 'T0001', 'nombre': 'Mikel'}, {'id': 'T0002', 'nombre': 'Txomin'},
                                      {'id': 'T0003', 'nombre': 'Andoni'}])
        self.assertEqual(self.codigos(r['jornadas'][0]['avisos']).count('alta_nueva'), 2)

    def test_escribe(self):
        r = self.ing(L1, escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)
        self.assertEqual(set(self.hashes()), {
            '_SISTEMA INFORME SAGARDE IA/personal_catalogo.json',
            '2026 OLABEAGA BILBAO/INFORME SAGARDE IA/personal_obra.json',
            '2026 OLABEAGA BILBAO/INFORME SAGARDE IA/personal_jornadas.jsonl'})
        cat = P.cargar_catalogo(self.raiz)
        self.assertEqual(cat['version'], 1)
        self.assertEqual([t['nombre'] for t in cat['trabajadores']], ['Mikel', 'Txomin', 'Andoni'])
        for t in cat['trabajadores']:
            self.assertEqual(set(t), {'id', 'nombre', 'categoria', 'empresa', 'activo', 'alta', 'fusionado_en'})
            self.assertTrue(t['activo'])
            self.assertEqual(t['alta'], HOY)
            self.assertIsNone(t['fusionado_en'])
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual(set(ob), {'version', 'obra', 'jornada_base_h', 'horario_semanal', 'excepciones_horario', 'jornadas'})
        self.assertEqual((ob['version'], ob['obra'], ob['jornada_base_h']), (1, 'olabeaga', 7.5))
        self.assertEqual(ob['horario_semanal'], H_BASE)
        self.assertEqual(ob['excepciones_horario'], {})
        self.assertEqual([(j['ambito'], j['fecha']) for j in ob['jornadas']], [('garaje', '2026-10-22'), ('vivienda', '2026-10-22')])
        viv = ob['jornadas'][1]
        self.assertEqual(set(viv), {'fecha', 'ambito', 'anulada', 'notas', 'presentes', 'registrado', 'origen'})
        self.assertEqual(viv['presentes'], [{'id': 'T0001', 'horas': 7.5, 'extra': 0}, {'id': 'T0002', 'horas': 7.5, 'extra': 0}])
        self.assertEqual((viv['anulada'], viv['notas'], viv['registrado'], viv['origen']), (False, '', AHORA, 'movil'))
        with open(os.path.join(self.ruta_obra(), 'personal_obra.json'), 'rb') as fh:
            crudo = fh.read()
        self.assertFalse(crudo.startswith(b'\xef\xbb\xbf'), 'sin BOM')
        lineas = open(os.path.join(self.ruta_obra(), 'personal_jornadas.jsonl'), encoding='utf-8').read().splitlines()
        self.assertEqual(len(lineas), 2)
        for ln in lineas:
            d = json.loads(ln)
            self.assertTrue({'ts', 'obra', 'ambito', 'fecha', 'accion', 'n_presentes', 'avisos', 'dispositivo'} <= set(d), d)

    def test_idempotente(self):
        self.ing(L1, escribir=True)
        h1 = self.hashes()
        r2 = self.ing(L1, escribir=True)
        self.assertEqual(self.hashes(), h1, 'reingerir el mismo lote no debe cambiar ni un byte')
        self.assertTrue(r2['ok'])
        self.assertEqual([j['accion'] for j in r2['jornadas']], ['sin_cambios', 'sin_cambios'])
        self.assertEqual(r2['altas'], [])
        l3 = copy.deepcopy(L1)
        for j in l3['jornadas']:
            j['registrado'] = '2026-10-23T09:00:00+02:00'
        r3 = self.ing(l3, escribir=True)
        self.assertEqual([j['accion'] for j in r3['jornadas']], ['sin_cambios', 'sin_cambios'])
        self.assertEqual(self.hashes(), h1, 'solo cambia `registrado`: sigue siendo sin_cambios')

    def test_reemplazo(self):
        self.ing(L1, escribir=True)
        l2 = lote([jor('vivienda', '2026-10-22', [('Mikel', 8, 0.5), ('Txomin', 7.5, 0)])])
        r = self.ing(l2, escribir=True)
        self.assertEqual(r['jornadas'][0]['accion'], 'reemplazo')
        self.assertIn('reemplazo', self.codigos(r['jornadas'][0]['avisos']))
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        viv = [j for j in ob['jornadas'] if j['ambito'] == 'vivienda'][0]
        self.assertEqual(viv['presentes'][0], {'id': 'T0001', 'horas': 8, 'extra': 0.5})
        self.assertEqual(len([j for j in ob['jornadas'] if j['ambito'] == 'garaje']), 1)
        lineas = open(os.path.join(self.ruta_obra(), 'personal_jornadas.jsonl'), encoding='utf-8').read().splitlines()
        self.assertEqual(len(lineas), 3)
        self.assertEqual(json.loads(lineas[-1])['accion'], 'reemplazo')

    def test_anulacion(self):
        self.ing(L1, escribir=True)
        l3 = lote([{'ambito': 'vivienda', 'fecha': '2026-10-22', 'anulada': True, 'presentes': []}])
        r = self.ing(l3, escribir=True)
        self.assertEqual(r['jornadas'][0]['accion'], 'anulacion')
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        viv = [j for j in ob['jornadas'] if j['ambito'] == 'vivienda'][0]
        self.assertTrue(viv['anulada'])
        self.assertEqual(viv['presentes'], [])
        self.assertEqual(P.aplanar(self.raiz, OBRAS, 'olabeaga'),
                         [{'fecha': '2026-10-22', 'ambito': 'garaje', 'nombre': 'Andoni', 'horas': 7.5, 'extra': 0}])
        self.assertIsNone(P.ultima_jornada(self.raiz, OBRAS, 'olabeaga', 'vivienda'))
        self.assertIsNotNone(P.ultima_jornada(self.raiz, OBRAS, 'olabeaga', 'garaje'))

    def test_orden_estable_al_guardar(self):
        self.ing(L1, escribir=True)  # Mikel T0001, Txomin T0002, Andoni T0003
        l = lote([jor('vivienda', '2026-10-21', [('Txomin', 7.5, 0), ('Mikel', 7.5, 0)]),
                  jor('vivienda', '2026-10-20', [('Andoni', 7.5, 0), ('Txomin', 7.5, 0), ('Mikel', 7.5, 0)])])
        self.assertTrue(self.ing(l, escribir=True)['ok'])
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual([(j['fecha'], j['ambito']) for j in ob['jornadas']],
                         [('2026-10-20', 'vivienda'), ('2026-10-21', 'vivienda'), ('2026-10-22', 'garaje'), ('2026-10-22', 'vivienda')])
        for j in ob['jornadas']:
            ids = [p['id'] for p in j['presentes']]
            self.assertEqual(ids, sorted(ids), 'presentes por id')
        self.assertEqual([p['id'] for p in ob['jornadas'][0]['presentes']], ['T0001', 'T0002', 'T0003'])

    def test_no_muta_la_entrada(self):
        l = copy.deepcopy(L1)
        copia = copy.deepcopy(l)
        P.ingerir_lote(l, self.raiz, OBRAS, HOY, escribir=True, ahora=AHORA)
        self.assertEqual(l, copia)

    def test_registrado_del_lote(self):
        l = lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)], registrado='2026-10-22T19:40:00+02:00')])
        self.ing(l, escribir=True)
        j = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')['jornadas'][0]
        self.assertEqual(j['registrado'], '2026-10-22T19:40:00+02:00')

    def test_horario_en_lote(self):
        h = dict(H_BASE, vie=7)
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])], horario_semanal=h), escribir=True)
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual(ob['horario_semanal'], h)
        self.assertEqual(ob['jornada_base_h'], 7.5)

    def test_traza_no_bloqueante(self):
        os.makedirs(os.path.join(self.ruta_obra(), 'personal_jornadas.jsonl'))  # un directorio donde iría el fichero
        r = self.ing(L1, escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)
        self.assertIn('traza_no_escrita', self.codigos(r['avisos_lote']))
        self.assertTrue(os.path.isfile(os.path.join(self.ruta_obra(), 'personal_obra.json')))
        self.assertTrue(os.path.isfile(self.ruta_cat()))

    def test_alta_trabajador(self):
        r = P.alta_trabajador(self.raiz, '  Mikel ', hoy=HOY, escribir=True)
        self.assertTrue(r['ok'] and r['escrito'])
        self.assertEqual((r['id'], r['error']), ('T0001', None))
        r2 = P.alta_trabajador(self.raiz, 'mikel', hoy=HOY, escribir=True)
        self.assertFalse(r2['ok'])
        self.assertEqual(r2['error'], 'nombre_duplicado')
        self.assertEqual(P.alta_trabajador(self.raiz, '  ', hoy=HOY)['error'], 'nombre_vacio')
        self.assertEqual(P.alta_trabajador(self.raiz, 'x' * 61, hoy=HOY)['error'], 'nombre_invalido')
        r3 = P.alta_trabajador(self.raiz, 'Mikell', hoy=HOY, escribir=False)
        self.assertTrue(r3['ok'])
        self.assertFalse(r3['escrito'])
        self.assertEqual(r3['parecidos'], ['Mikel'])
        self.assertEqual(P.alta_trabajador(self.raiz, 'Mi', hoy=HOY)['parecidos'], [], 'los nombres de menos de 3 letras no se comparan')
        self.assertEqual(len(P.cargar_catalogo(self.raiz)['trabajadores']), 1, 'la simulación no guarda')


class TestRechazos(Base):
    def rechaza_lote(self, l, codigo):
        r = self.ing(l, escribir=True)
        self.assertFalse(r['ok'], (codigo, r))
        self.assertIn(codigo, r['lote_rechazado'], (codigo, r))
        self.assertEqual(r['jornadas'], [], (codigo, r))
        self.assertEqual(self.hashes(), {}, 'un lote rechazado no debe escribir nada: %s' % codigo)

    def rechaza_jornada(self, l, codigo, idx=0):
        r = self.ing(l, escribir=True)
        self.assertFalse(r['ok'], (codigo, r))
        self.assertEqual(r['jornadas'][idx]['estado'], 'rechazada', (codigo, r))
        self.assertIn(codigo, r['jornadas'][idx]['rechazos'], (codigo, r))
        return r

    def test_lote_invalido(self):
        for malo in ('texto', None, [], 12):
            with self.subTest(malo=malo):
                self.rechaza_lote(malo, 'lote_invalido')
        sin_jornadas = lote([])
        del sin_jornadas['jornadas']
        self.rechaza_lote(sin_jornadas, 'lote_invalido')

    def test_tipo_version_obra(self):
        self.rechaza_lote(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])], tipo='otro'), 'tipo_desconocido')
        self.rechaza_lote(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])], version=2), 'version_desconocida')
        self.rechaza_lote(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])], version=True), 'version_desconocida')
        self.rechaza_lote(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])], obra=['x']), 'obra_invalida')
        self.rechaza_lote(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])], obra='nueva'), 'obra_invalida')

    def test_campo_desconocido(self):
        ok_j = jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])
        self.rechaza_lote(lote([ok_j], foo=1), 'campo_desconocido')
        self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)], dni='x')]), 'campo_desconocido')
        malo = jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])
        malo['presentes'][0]['telefono'] = '600'
        self.rechaza_jornada(lote([malo]), 'campo_desconocido')

    def test_horario_invalido(self):
        j = jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])
        casos = [{'lun': 7.5}, dict(H_BASE, xxx=1), dict(H_BASE, lun=25), dict(H_BASE, lun=7.555), dict(H_BASE, lun='7.5'),
                 dict(H_BASE, lun=-1), dict(H_BASE, lun=None)]
        for h in casos:
            with self.subTest(h=h):
                self.rechaza_lote(lote([j], horario_semanal=h), 'horario_invalido')

    def test_excepcion_invalida(self):
        """Paso 01b: el horario propio por trabajador va en `excepciones_horario`; esquema cerrado, rechazo del lote entero."""
        j = jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])
        casos = [[], 'x', None, 5,
                 {'  ': {'vie': 9}}, {'x' * 61: {'vie': 9}}, {'Mi\x00kel': {'vie': 9}},
                 {'Mikel': {'vie': 9}, ' mikel ': {'vie': 8}},
                 {'Mikel': 9}, {'Mikel': None}, {'Mikel': [9]}, {'Mikel': 'vie'},
                 {'Mikel': {'xxx': 9}}, {'Mikel': {'Vie': 9}}, {'Mikel': {'viernes': 9}},
                 {'Mikel': {'vie': 25}}, {'Mikel': {'vie': -1}}, {'Mikel': {'vie': 9.555}}, {'Mikel': {'vie': '9'}},
                 {'Mikel': {'vie': None}}, {'Mikel': {'vie': True}}, {'Mikel': {'vie': float('nan')}},
                 {'Mikel': {'vie': 9}, 'Txomin': {'vie': 99}}]
        for ex in casos:
            with self.subTest(ex=ex):
                self.rechaza_lote(lote([j], excepciones_horario=ex), 'excepcion_invalida')

    def test_excepcion_invalida_con_horario_invalido(self):
        j = jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])
        self.rechaza_lote(lote([j], horario_semanal={'lun': 7.5}, excepciones_horario={'Mikel': {'vie': 9}}), 'horario_invalido')

    def test_ambito_y_fecha(self):
        self.rechaza_jornada(lote([jor('sotano', '2026-10-22', [('Mikel', 7.5, 0)])]), 'ambito_invalido')
        for f in ('2026-02-30', '23/10/2026', '', '2026-13-01', None, 20261023):
            with self.subTest(fecha=f):
                self.rechaza_jornada(lote([jor('vivienda', f, [('Mikel', 7.5, 0)])]), 'fecha_invalida')

    def test_nombres(self):
        self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [('   ', 7.5, 0)])]), 'nombre_vacio')
        self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [(None, 7.5, 0)])]), 'nombre_vacio')
        self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [('x' * 61, 7.5, 0)])]), 'nombre_invalido')
        self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [('Mi\x00kel', 7.5, 0)])]), 'nombre_invalido')
        self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0), (' mikel ', 7.5, 0)])]), 'presente_duplicado')

    def test_horas(self):
        for h in (None, '7.5', -1, 24.5, 7.555, True):
            with self.subTest(horas=h):
                self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [('Mikel', h, 0)])]), 'horas_invalidas')
        sin_horas = jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])
        del sin_horas['presentes'][0]['horas']
        self.rechaza_jornada(lote([sin_horas]), 'horas_invalidas')

    def test_ruido_de_coma_flotante(self):
        r = self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.500000000001, 0)])]), escribir=True)
        self.assertTrue(r['ok'], r)
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual(ob['jornadas'][0]['presentes'][0]['horas'], 7.5)

    def test_extra(self):
        for e in (8, -1, 'x', True):
            with self.subTest(extra=e):
                self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, e)])]), 'extra_invalido')
        sin_extra = jor('vivienda', '2026-10-22', [('Mikel', 7.5)])
        r = self.ing(lote([sin_extra]), escribir=True)
        self.assertTrue(r['ok'], r)
        self.assertEqual(P.cargar_obra(self.raiz, OBRAS, 'olabeaga')['jornadas'][0]['presentes'][0]['extra'], 0)

    def test_anulada_y_vacias(self):
        self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)], anulada=True)]), 'anulada_con_presentes')
        self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [])]), 'sin_presentes')
        self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [], anulada=False)]), 'sin_presentes')

    def test_vacia_no_borra_datos(self):
        self.ing(L1, escribir=True)
        h = self.hashes()
        r = self.ing(lote([jor('vivienda', '2026-10-22', [])]), escribir=True)
        self.assertFalse(r['ok'])
        self.assertEqual(self.hashes(), h, 'una jornada vacía no anulada no debe tocar lo guardado')

    def test_jornada_repetida_en_lote(self):
        l = lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)]), jor('vivienda', '2026-10-22', [('Mikel', 8, 0)])])
        r = self.ing(l, escribir=True)
        self.assertFalse(r['ok'])
        for j in r['jornadas']:
            self.assertEqual(j['estado'], 'rechazada')
            self.assertIn('jornada_repetida_en_lote', j['rechazos'])
        self.assertEqual(self.hashes(), {})

    def test_todo_o_nada_por_jornada(self):
        l = lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)]), jor('garaje', '2026-10-22', [('Fantasma', -1, 0)])])
        r = self.ing(l, escribir=True)
        self.assertFalse(r['ok'])
        self.assertEqual([j['estado'] for j in r['jornadas']], ['aceptada', 'rechazada'])
        self.assertEqual(r['altas'], [{'id': 'T0001', 'nombre': 'Mikel'}])
        self.assertEqual([t['nombre'] for t in P.cargar_catalogo(self.raiz)['trabajadores']], ['Mikel'])
        self.assertEqual(len(P.cargar_obra(self.raiz, OBRAS, 'olabeaga')['jornadas']), 1)

    def test_suma_diaria(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 12, 0)])]), escribir=True)
        self.rechaza_jornada(lote([jor('garaje', '2026-10-22', [('Mikel', 13, 0)])]), 'suma_diaria_invalida')
        self.rechaza_jornada(lote([jor('vivienda', '2026-10-22', [('Mikel', 13, 0)])], obra='mungia'), 'suma_diaria_invalida')
        ok24 = self.ing(lote([jor('garaje', '2026-10-22', [('Mikel', 12, 0)])]), escribir=True)
        self.assertTrue(ok24['ok'], ok24)
        self.assertIn('suma_diaria_alta', self.codigos(ok24['jornadas'][0]['avisos']))

    def test_suma_diaria_dentro_del_lote_y_reemplazo(self):
        r = self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 12, 0)]), jor('garaje', '2026-10-22', [('Mikel', 13, 0)])]), escribir=True)
        self.assertEqual([j['estado'] for j in r['jornadas']], ['aceptada', 'rechazada'])
        self.assertIn('suma_diaria_invalida', r['jornadas'][1]['rechazos'])
        r2 = self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', 13, 0)])]), escribir=True)
        self.assertTrue(r2['ok'], 'al reemplazar no se cuenta la jornada que se sustituye: %s' % r2)
        self.assertEqual(r2['jornadas'][0]['accion'], 'reemplazo')
        self.assertIn('suma_diaria_alta', self.codigos(r2['jornadas'][0]['avisos']))


class TestAvisos(Base):
    def test_suma_diaria_alta(self):
        r = self.ing(lote([jor('vivienda', '2026-10-22', [('Txomin', 9.5, 2)]), jor('garaje', '2026-10-22', [('Txomin', 3, 0)])]))
        self.assertTrue(r['ok'], r)
        self.assertIn('suma_diaria_alta', self.codigos(r['jornadas'][1]['avisos']))
        r2 = self.ing(lote([jor('vivienda', '2026-10-22', [('Txomin', 9, 1.5)]), jor('garaje', '2026-10-22', [('Txomin', 3, 0)])]))
        self.assertNotIn('suma_diaria_alta', self.codigos(r2['jornadas'][1]['avisos']), 'exactamente 12 h no es aviso')

    def test_fecha_futura(self):
        r = self.ing(lote([jor('vivienda', '2026-10-24', [('Mikel', 5, 5)])]))
        self.assertTrue(r['ok'])
        self.assertIn('fecha_futura', self.codigos(r['jornadas'][0]['avisos']))
        r2 = self.ing(lote([jor('vivienda', HOY, [('Mikel', 7.5, 0)])]))
        self.assertNotIn('fecha_futura', self.codigos(r2['jornadas'][0]['avisos']))

    def test_nombres_parecidos_y_resueltos(self):
        self.ing(lote([jor('vivienda', '2026-10-20', [('Mikel', 7.5, 0), ('Iñaki', 7.5, 0)])]), escribir=True)
        l = lote([jor('vivienda', '2026-10-21', [('Mikell', 7.5, 0), ('Mikal', 7.5, 0), ('Mik', 7.5, 0), ('Mi', 7.5, 0),
                                                  ('Xabier', 7.5, 0), ('mikel ', 7.5, 0), ('Inaki', 7.5, 0)])])
        r = self.ing(l, escribir=True)
        self.assertTrue(r['ok'], r)
        self.assertEqual([a['nombre'] for a in r['altas']], ['Mikell', 'Mikal', 'Mik', 'Mi', 'Xabier'])
        av = r['jornadas'][0]['avisos']
        self.assertEqual(self.codigos(av).count('alta_nueva'), 5)
        parecidos = [a['detalle'] for a in av if a['codigo'] == 'nombre_parecido']
        self.assertEqual(sorted(d.split(' ~ ')[0] for d in parecidos), ['Mik', 'Mikal', 'Mikell'], av)
        nuevos = [a['detalle'] for a in av if a['codigo'] == 'alta_nueva']
        self.assertEqual(nuevos, ['Mikell', 'Mikal', 'Mik', 'Mi', 'Xabier'])
        ids = {t['nombre']: t['id'] for t in P.cargar_catalogo(self.raiz)['trabajadores']}
        j = [x for x in P.cargar_obra(self.raiz, OBRAS, 'olabeaga')['jornadas'] if x['fecha'] == '2026-10-21'][0]
        self.assertIn(ids['Mikel'], [p['id'] for p in j['presentes']])
        self.assertIn(ids['Iñaki'], [p['id'] for p in j['presentes']])


class TestFusion(Base):
    def base(self):
        self.ing(lote([jor('vivienda', '2026-10-19', [('Mikel', 7.5, 0)]), jor('vivienda', '2026-10-20', [('Mikell', 7.5, 0)])]), escribir=True)

    def test_fusion_normal(self):
        self.base()
        h = self.hashes()
        r0 = P.fusionar(self.raiz, 'T0002', 'T0001', escribir=False, ahora=AHORA)
        self.assertTrue(r0['ok'] and not r0['escrito'], r0)
        self.assertEqual(self.hashes(), h, 'en simulación no cambia nada')
        r = P.fusionar(self.raiz, 'T0002', 'T0001', escribir=True, ahora=AHORA)
        self.assertTrue(r['ok'] and r['escrito'], r)
        cat = {t['id']: t for t in P.cargar_catalogo(self.raiz)['trabajadores']}
        self.assertEqual(cat['T0002']['fusionado_en'], 'T0001')
        self.assertIsNone(cat['T0001']['fusionado_en'])
        self.assertEqual({f['nombre'] for f in P.aplanar(self.raiz, OBRAS, 'olabeaga')}, {'Mikel'})
        r2 = self.ing(lote([jor('vivienda', '2026-10-21', [('mikell', 7.5, 0)])]), escribir=True)
        self.assertEqual(r2['altas'], [], 'un nombre fusionado resuelve a su destino')
        j = [x for x in P.cargar_obra(self.raiz, OBRAS, 'olabeaga')['jornadas'] if x['fecha'] == '2026-10-21'][0]
        self.assertEqual(j['presentes'], [{'id': 'T0001', 'horas': 7.5, 'extra': 0}])
        est = P.exportar_estado(self.raiz, OBRAS, generado=AHORA)
        datos = json.loads(est[est.index('{'):est.rindex('}') + 1])
        self.assertEqual([t['nombre'] for t in datos['catalogo']], ['Mikel'])

    def test_errores(self):
        self.base()
        h = self.hashes()
        casos = [(('T0001', 'T0001'), 'mismo_id'), (('T0009', 'T0001'), 'id_inexistente'), (('T0001', 'T0009'), 'id_inexistente')]
        for (o, d), esperado in casos:
            r = P.fusionar(self.raiz, o, d, escribir=True, ahora=AHORA)
            self.assertFalse(r['ok'])
            self.assertEqual(r['error'], esperado)
        self.assertEqual(self.hashes(), h)
        P.fusionar(self.raiz, 'T0002', 'T0001', escribir=True, ahora=AHORA)
        self.assertEqual(P.fusionar(self.raiz, 'T0002', 'T0001', escribir=True, ahora=AHORA)['error'], 'origen_ya_fusionado')
        self.assertEqual(P.fusionar(self.raiz, 'T0001', 'T0002', escribir=True, ahora=AHORA)['error'], 'destino_fusionado')

    def test_conflicto_en_jornada(self):
        self.ing(lote([jor('vivienda', '2026-10-20', [('Mikel', 7.5, 0), ('Mikell', 7.5, 0)])]), escribir=True)
        h = self.hashes()
        r = P.fusionar(self.raiz, 'T0002', 'T0001', escribir=True, ahora=AHORA)
        self.assertFalse(r['ok'])
        self.assertEqual(r['error'], 'conflicto_en_jornada')
        self.assertEqual(self.hashes(), h)


class TestDatosDerivados(Base):
    def cargar(self):
        self.ing(ESC, escribir=True)
        self.ing(ESC_M, escribir=True)

    def test_ultima_jornada(self):
        self.cargar()
        self.assertEqual(P.ultima_jornada(self.raiz, OBRAS, 'olabeaga', 'vivienda'),
                         {'fecha': '2026-10-24', 'presentes': [{'nombre': 'Mikel', 'horas': 5, 'extra': 5}]})
        self.assertEqual(P.ultima_jornada(self.raiz, OBRAS, 'olabeaga', 'garaje'),
                         {'fecha': '2026-10-20', 'presentes': [{'nombre': 'Txomin', 'horas': 7.5, 'extra': 0}]})
        self.assertIsNone(P.ultima_jornada(self.raiz, OBRAS, 'mungia', 'garaje'))

    def test_aplanar(self):
        self.cargar()
        self.assertEqual(P.aplanar(self.raiz, OBRAS, 'olabeaga'), [
            {'fecha': '2026-10-19', 'ambito': 'vivienda', 'nombre': 'Mikel', 'horas': 7.5, 'extra': 0},
            {'fecha': '2026-10-19', 'ambito': 'vivienda', 'nombre': 'Txomin', 'horas': 7.5, 'extra': 0},
            {'fecha': '2026-10-20', 'ambito': 'garaje', 'nombre': 'Txomin', 'horas': 7.5, 'extra': 0},
            {'fecha': '2026-10-20', 'ambito': 'vivienda', 'nombre': 'Mikel', 'horas': 9.5, 'extra': 2},
            {'fecha': '2026-10-24', 'ambito': 'vivienda', 'nombre': 'Mikel', 'horas': 5, 'extra': 5}])

    def test_totales_control(self):
        self.cargar()
        self.assertEqual(P.totales_control(self.raiz, OBRAS, 'olabeaga'), {
            'horas': 37, 'extra': 7, 'dias': 3, 'trabajadores': 2,
            'por_trabajador': {'Mikel': {'horas': 22, 'extra': 7, 'dias': 3}, 'Txomin': {'horas': 15, 'extra': 0, 'dias': 2}}})
        self.assertEqual(P.totales_control(self.raiz, OBRAS), {
            'horas': 44.5, 'extra': 7, 'dias': 4, 'trabajadores': 2,
            'por_trabajador': {'Mikel': {'horas': 29.5, 'extra': 7, 'dias': 4}, 'Txomin': {'horas': 15, 'extra': 0, 'dias': 2}}})

    def test_totales_sin_datos_es_none(self):
        self.ing(ESC, escribir=True)
        self.assertIsNone(P.totales_control(self.raiz, OBRAS, 'mungia'))
        self.assertEqual(P.aplanar(self.raiz, OBRAS, 'mungia'), [])

    def test_estado(self):
        self.cargar()
        nombres = {'olabeaga': '2026 OLABEAGA BILBAO', 'mungia': '2026 MUNGIA ACR NEINOR'}
        s = P.exportar_estado(self.raiz, OBRAS, nombres_obra=nombres, cerradas={'mungia'}, generado='2026-10-23T22:07:00+02:00')
        self.assertTrue(s.startswith('window.SAGARDE_PERSONAL = '), s[:60])
        self.assertTrue(s.rstrip().endswith(';'))
        datos = json.loads(s[s.index('{'):s.rindex('}') + 1])
        self.assertEqual((datos['version'], datos['generado'], datos['jornada_base_h']), (1, '2026-10-23T22:07:00+02:00', 7.5))
        self.assertEqual([t['nombre'] for t in datos['catalogo']], ['Mikel', 'Txomin'])
        for t in datos['catalogo']:
            self.assertEqual(set(t), {'id', 'nombre', 'categoria', 'empresa', 'activo'})
        self.assertEqual(set(datos['obras']), {'olabeaga', 'mungia'})
        ola = datos['obras']['olabeaga']
        self.assertEqual((ola['nombre'], ola['cerrada']), ('2026 OLABEAGA BILBAO', False))
        self.assertTrue(datos['obras']['mungia']['cerrada'])
        self.assertEqual(ola['horario_semanal'], H_BASE)
        self.assertEqual(ola['excepciones_horario'], {})
        self.assertEqual(ola['ultima']['vivienda'], {'fecha': '2026-10-24', 'presentes': [{'nombre': 'Mikel', 'horas': 5, 'extra': 5}]})
        self.assertEqual(ola['ultima']['garaje'], {'fecha': '2026-10-20', 'presentes': [{'nombre': 'Txomin', 'horas': 7.5, 'extra': 0}]})
        self.assertIsNone(datos['obras']['mungia']['ultima']['garaje'])
        self.assertEqual(ola['jornadas'], P.aplanar(self.raiz, OBRAS, 'olabeaga'))
        self.assertEqual(P.exportar_estado(self.raiz, OBRAS, nombres_obra=nombres, cerradas={'mungia'},
                                           generado='2026-10-23T22:07:00+02:00'), s, 'determinista')

    def test_estado_escribe_utf8_sin_bom_y_excepciones(self):
        self.ing(lote([jor('vivienda', '2026-10-22', [('Iñaki', 7.5, 0), ('Mikel', 7.5, 0)])]), escribir=True)
        ruta = os.path.join(self.ruta_obra(), 'personal_obra.json')
        with open(ruta, encoding='utf-8') as fh:
            ob = json.load(fh)
        ob['excepciones_horario'] = {'T0002': {'vie': 6}}
        with open(ruta, 'w', encoding='utf-8') as fh:
            json.dump(ob, fh, ensure_ascii=False)
        s = P.exportar_estado(self.raiz, OBRAS, generado=AHORA, escribir=True)
        destino = os.path.join(self.raiz, '_SISTEMA INFORME SAGARDE IA', 'personal_estado.js')
        with open(destino, 'rb') as fh:
            crudo = fh.read()
        self.assertEqual(crudo, s.encode('utf-8'))
        self.assertFalse(crudo.startswith(b'\xef\xbb\xbf'))
        self.assertIn('Iñaki', s)
        self.assertNotIn('\\u00f1', s)
        datos = json.loads(s[s.index('{'):s.rindex('}') + 1])
        self.assertEqual(datos['obras']['olabeaga']['excepciones_horario'], {'Mikel': {'vie': 6}})


class TestComprobar(Base):
    def test_limpio_y_vacio(self):
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])
        self.ing(L1, escribir=True)
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])

    def corrompe(self, f):
        self.nuevo_raiz()
        self.ing(L1, escribir=True)
        f()
        problemas = P.comprobar(self.raiz, OBRAS)
        self.assertTrue(problemas, 'comprobar debe detectar la corrupción')

    def test_corrupciones(self):
        ruta_ob = lambda: os.path.join(self.ruta_obra(), 'personal_obra.json')  # noqa: E731

        def editar(fn, ruta):
            with open(ruta, encoding='utf-8') as fh:
                d = json.load(fh)
            fn(d)
            with open(ruta, 'w', encoding='utf-8') as fh:
                json.dump(d, fh, ensure_ascii=False)

        self.corrompe(lambda: editar(lambda d: d.update({'foo': 1}), ruta_ob()))
        self.corrompe(lambda: editar(lambda d: d['jornadas'][1]['presentes'][0].update({'id': 'T9999'}), ruta_ob()))
        self.corrompe(lambda: editar(lambda d: d['jornadas'].append(copy.deepcopy(d['jornadas'][0])), ruta_ob()))
        self.corrompe(lambda: editar(lambda d: d['jornadas'][1].update({'anulada': True}), ruta_ob()))
        self.corrompe(lambda: editar(lambda d: d['trabajadores'].append(
            {'id': 'T0099', 'nombre': 'MIKEL', 'categoria': '', 'empresa': '', 'activo': True, 'alta': HOY, 'fusionado_en': None}),
            self.ruta_cat()))


class TestComprobarHorarioPropio(HorarioPropioBase):
    def test_correcto_pasa(self):
        self.ing(lote(L1['jornadas'], excepciones_horario={'Mikel': {'vie': 9}, 'Txomin': {}}), escribir=True)
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])
        self.editar_obra(lambda d: d.update({'excepciones_horario': {'T0001': {'lun': 8, 'sab': 0}}}))
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])

    def test_corrupciones_del_horario_propio(self):
        malos = [{'T9999': {'vie': 9}}, {'T0001': {'xxx': 9}}, {'T0001': {'Vie': 9}}, {'T0001': {'vie': 25}}, {'T0001': {'vie': -1}},
                 {'T0001': {'vie': 9.555}}, {'T0001': {'vie': '9'}}, {'T0001': {'vie': True}}, {'T0001': 9}, {'T0001': [9]}, {'T0001': None}, [], 5, 'x']
        for malo in malos:
            with self.subTest(malo=malo):
                self.nuevo_raiz()
                self.ing(L1, escribir=True)
                self.editar_obra(lambda d: d.update({'excepciones_horario': malo}))
                self.assertTrue(P.comprobar(self.raiz, OBRAS), 'comprobar debe detectar excepciones_horario=%r' % (malo,))


class TestAnuladasCorruptas(Base):
    def test_aplanar_ignora_anuladas_aunque_traigan_presentes(self):
        self.ing(L1, escribir=True)
        ruta = os.path.join(self.ruta_obra(), 'personal_obra.json')
        with open(ruta, encoding='utf-8') as fh:
            d = json.load(fh)
        for j in d['jornadas']:
            if j['ambito'] == 'vivienda':
                j['anulada'] = True  # estado corrupto: anulada pero con presentes
        with open(ruta, 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False)
        self.assertEqual(P.aplanar(self.raiz, OBRAS, 'olabeaga'),
                         [{'fecha': '2026-10-22', 'ambito': 'garaje', 'nombre': 'Andoni', 'horas': 7.5, 'extra': 0}])
        self.assertIsNone(P.ultima_jornada(self.raiz, OBRAS, 'olabeaga', 'vivienda'))
        self.assertTrue(P.comprobar(self.raiz, OBRAS), 'comprobar debe señalar una jornada anulada con presentes')


class TestHorarioPropio(HorarioPropioBase):
    def test_fija_y_guarda_ordenado(self):
        l = lote(L1['jornadas'], excepciones_horario={'Txomin': {'vie': 9, 'lun': 8}, 'Mikel': {'vie': 9}})
        r = self.ing(l, escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)
        self.assertEqual(r['excepciones'], [{'nombre': 'Txomin', 'id': 'T0002', 'accion': 'fijada'},
                                            {'nombre': 'Mikel', 'id': 'T0001', 'accion': 'fijada'}], 'en el orden en que aparecen en el lote')
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual(list(ob), ['version', 'obra', 'jornada_base_h', 'horario_semanal', 'excepciones_horario', 'jornadas'])
        self.assertEqual(ob['excepciones_horario'], {'T0001': {'vie': 9}, 'T0002': {'lun': 8, 'vie': 9}})
        self.assertEqual(list(ob['excepciones_horario']), ['T0001', 'T0002'], 'ordenadas por id')
        self.assertEqual(list(ob['excepciones_horario']['T0002']), ['lun', 'vie'], 'días en el orden de la semana')
        self.assertEqual(self.exc_est(), {'Mikel': {'vie': 9}, 'Txomin': {'lun': 8, 'vie': 9}}, 'el estado las emite por nombre')
        tr = self.traza()
        self.assertEqual([t['accion'] for t in tr], ['alta', 'alta', 'horario_propio', 'horario_propio'])
        self.assertEqual([t['id'] for t in tr[2:]], ['T0002', 'T0001'])
        for t in tr[2:]:
            self.assertEqual((t['obra'], t['ambito'], t['fecha'], t['n_presentes'], t['ts']), ('olabeaga', None, None, 0, AHORA))

    def test_idempotente(self):
        l = lote([J_MIKEL], excepciones_horario={'Mikel': {'vie': 9, 'lun': 8.5}})
        self.assertTrue(self.ing(l, escribir=True)['ok'])
        h1 = self.hashes()
        r2 = self.ing(l, escribir=True)
        self.assertEqual(self.hashes(), h1, 'reingerir el mismo lote no cambia ni un byte (tampoco la traza)')
        self.assertFalse(r2['escrito'])
        self.assertEqual([e['accion'] for e in r2['excepciones']], ['sin_cambios'])
        r3 = self.ing(lote([J_MIKEL], excepciones_horario={'Mikel': {'lun': 8.5, 'vie': 9.0}}), escribir=True)
        self.assertEqual(self.hashes(), h1, 'otro orden de los días y 9.0 en vez de 9 es lo mismo')
        self.assertEqual([e['accion'] for e in r3['excepciones']], ['sin_cambios'])

    def test_sustituye_el_objeto_entero_y_quita(self):
        self.ing(lote([J_MIKEL], excepciones_horario={'Mikel': {'vie': 9, 'lun': 8}}), escribir=True)
        r = self.ing(lote([J_MIKEL], excepciones_horario={'Mikel': {'vie': 7}}), escribir=True)
        self.assertEqual(r['excepciones'], [{'nombre': 'Mikel', 'id': 'T0001', 'accion': 'fijada'}])
        self.assertEqual(self.exc_obra(), {'T0001': {'vie': 7}}, 'el objeto de la persona sustituye al anterior: el lunes ya no está')
        r = self.ing(lote([J_MIKEL], excepciones_horario={'Mikel': {}}), escribir=True)
        self.assertEqual(r['excepciones'], [{'nombre': 'Mikel', 'id': 'T0001', 'accion': 'quitada'}])
        self.assertEqual(self.exc_obra(), {})
        self.assertEqual(self.exc_est(), {})
        h = self.hashes()
        r = self.ing(lote([J_MIKEL], excepciones_horario={'Mikel': {}}), escribir=True)
        self.assertEqual(r['excepciones'], [{'nombre': 'Mikel', 'id': 'T0001', 'accion': 'sin_cambios'}])
        self.assertEqual(self.hashes(), h, 'quitar lo que no hay no cambia nada')
        self.assertEqual([t['accion'] for t in self.traza()], ['alta', 'horario_propio', 'horario_propio', 'horario_propio_quitado'])
        self.assertEqual(self.traza()[-1]['id'], 'T0001')

    def test_cada_obra_la_suya(self):
        self.ing(lote([J_MIKEL], excepciones_horario={'Mikel': {'vie': 9}}), escribir=True)
        self.ing(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5, 0)])], obra='mungia', excepciones_horario={'Mikel': {'vie': 6}}), escribir=True)
        self.assertEqual(self.exc_est('olabeaga'), {'Mikel': {'vie': 9}})
        self.assertEqual(self.exc_est('mungia'), {'Mikel': {'vie': 6}})

    def test_lote_solo_con_excepciones(self):
        self.ing(lote([J_MIKEL]), escribir=True)
        r = self.ing(lote([], excepciones_horario={'Mikel': {'vie': 9}}), escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)
        self.assertEqual(r['jornadas'], [])
        self.assertEqual(self.exc_obra(), {'T0001': {'vie': 9}})

    def test_valores_en_los_limites(self):
        r = self.ing(lote([J_MIKEL], excepciones_horario={'Mikel': {'vie': 24, 'sab': 0, 'dom': 9.5, 'lun': 9.500000000001}}), escribir=True)
        self.assertTrue(r['ok'], r)
        self.assertEqual(self.exc_obra(), {'T0001': {'lun': 9.5, 'vie': 24, 'sab': 0, 'dom': 9.5}})
        self.assertEqual(list(self.exc_obra()['T0001']), ['lun', 'vie', 'sab', 'dom'])

    def test_nombre_inexistente_se_da_de_alta(self):
        self.ing(lote([J_MIKEL]), escribir=True)
        r = self.ing(lote([J_MIKEL], excepciones_horario={'Aitor': {'vie': 9}}), escribir=True)
        self.assertTrue(r['ok'], r)
        self.assertEqual(r['altas'], [{'id': 'T0002', 'nombre': 'Aitor'}])
        self.assertIn({'codigo': 'alta_nueva', 'detalle': 'Aitor'}, r['avisos_lote'])
        self.assertEqual(r['excepciones'], [{'nombre': 'Aitor', 'id': 'T0002', 'accion': 'fijada'}])
        self.assertEqual([t['nombre'] for t in P.cargar_catalogo(self.raiz)['trabajadores']], ['Mikel', 'Aitor'])
        self.assertEqual(P.cargar_catalogo(self.raiz)['trabajadores'][1],
                         {'id': 'T0002', 'nombre': 'Aitor', 'categoria': '', 'empresa': '', 'activo': True, 'alta': HOY, 'fusionado_en': None})
        self.assertEqual(self.exc_obra(), {'T0002': {'vie': 9}})
        r2 = self.ing(lote([J_MIKEL], excepciones_horario={'  AITOR ': {'vie': 9}}), escribir=True)
        self.assertEqual(r2['altas'], [])
        self.assertEqual(r2['excepciones'], [{'nombre': 'AITOR', 'id': 'T0002', 'accion': 'sin_cambios'}], 'misma persona por clave de nombre')

    def test_nombre_inexistente_con_alta_y_aviso_de_parecido(self):
        self.ing(lote([J_MIKEL]), escribir=True)
        r = self.ing(lote([J_MIKEL], excepciones_horario={'Mikell': {'vie': 9}}))
        self.assertIn({'codigo': 'nombre_parecido', 'detalle': 'Mikell ~ Mikel'}, r['avisos_lote'])
        self.assertIn({'codigo': 'alta_nueva', 'detalle': 'Mikell'}, r['avisos_lote'])

    def test_quitar_a_un_desconocido_no_da_de_alta(self):
        self.ing(lote([J_MIKEL]), escribir=True)
        h = self.hashes()
        r = self.ing(lote([J_MIKEL], excepciones_horario={'Zuri': {}}), escribir=True)
        self.assertEqual(r['altas'], [])
        self.assertEqual(r['excepciones'], [{'nombre': 'Zuri', 'id': None, 'accion': 'sin_cambios'}])
        self.assertEqual(self.hashes(), h)

    def test_nombre_fusionado_resuelve_a_su_destino(self):
        self.ing(lote([jor('vivienda', '2026-10-19', [('Mikel', 7.5, 0)]), jor('vivienda', '2026-10-20', [('Mikell', 7.5, 0)])]), escribir=True)
        self.assertTrue(P.fusionar(self.raiz, 'T0002', 'T0001', escribir=True, ahora=AHORA)['ok'])
        r = self.ing(lote([J_MIKEL], excepciones_horario={'mikell': {'vie': 9}}), escribir=True)
        self.assertEqual(r['altas'], [])
        self.assertEqual(r['excepciones'], [{'nombre': 'mikell', 'id': 'T0001', 'accion': 'fijada'}])
        self.assertEqual(self.exc_obra(), {'T0001': {'vie': 9}})

    def test_simulacion_no_escribe(self):
        r = self.ing(lote([J_MIKEL], excepciones_horario={'Mikel': {'vie': 9}}))
        self.assertEqual(r['excepciones'], [{'nombre': 'Mikel', 'id': 'T0001', 'accion': 'fijada'}])
        self.assertEqual(self.hashes(), {}, 'en simulación no se crea ningún fichero')

    def test_no_muta_la_entrada(self):
        l = lote([J_MIKEL], excepciones_horario={'Mikel': {'vie': 9, 'lun': 8}})
        copia = copy.deepcopy(l)
        P.ingerir_lote(l, self.raiz, OBRAS, HOY, escribir=True, ahora=AHORA)
        self.assertEqual(l, copia)

    def test_lote_rechazado_trae_la_lista_vacia(self):
        r = self.ing(lote([J_MIKEL], excepciones_horario=[]))
        self.assertEqual(r['excepciones'], [])
        self.assertEqual(self.ing(lote([J_MIKEL]))['excepciones'], [])

    def test_con_horario_semanal_se_aplican_las_dos_cosas(self):
        h = dict(H_BASE, vie=7)
        r = self.ing(lote([J_MIKEL], horario_semanal=h, excepciones_horario={'Mikel': {'vie': 9}}), escribir=True)
        self.assertTrue(r['ok'], r)
        ob = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')
        self.assertEqual((ob['horario_semanal'], ob['excepciones_horario']), (h, {'T0001': {'vie': 9}}))

    def test_se_aplica_aunque_se_rechace_una_jornada(self):
        """Como el horario de la obra: no es parte de ninguna jornada, así que no cae con ellas."""
        r = self.ing(lote([jor('vivienda', '2026-10-22', [('Mikel', -1, 0)])], excepciones_horario={'Mikel': {'vie': 9}}), escribir=True)
        self.assertFalse(r['ok'])
        self.assertEqual(r['jornadas'][0]['estado'], 'rechazada')
        self.assertEqual(r['excepciones'], [{'nombre': 'Mikel', 'id': 'T0001', 'accion': 'fijada'}])
        self.assertEqual(self.exc_obra(), {'T0001': {'vie': 9}})

    def test_un_valor_danado_no_impide_guardar_otra_cosa(self):
        self.ing(lote([J_MIKEL]), escribir=True)
        self.editar_obra(lambda d: d.update({'excepciones_horario': {'T0001': 5}}))
        r = self.ing(lote([jor('vivienda', '2026-10-23', [('Mikel', 7.5, 0)])]), escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)
        self.assertEqual(self.exc_obra(), {'T0001': 5}, 'lo dañado se deja como está: lo señala comprobar, no se borra ni se rompe')
        self.assertTrue(P.comprobar(self.raiz, OBRAS))

    def test_el_orden_del_lote_no_cambia_el_fichero(self):
        self.ing(L1, escribir=True)
        self.ing(lote([], excepciones_horario={'Mikel': {'vie': 9}}), escribir=True)
        self.ing(lote([], excepciones_horario={'Txomin': {'lun': 8}}), escribir=True)
        with open(os.path.join(self.ruta_obra(), 'personal_obra.json'), 'rb') as fh:
            con_orden_a = fh.read()
        estado_a = P.exportar_estado(self.raiz, OBRAS, generado=AHORA)
        self.nuevo_raiz()
        self.ing(L1, escribir=True)
        self.ing(lote([], excepciones_horario={'Txomin': {'lun': 8}}), escribir=True)
        self.ing(lote([], excepciones_horario={'Mikel': {'vie': 9}}), escribir=True)
        with open(os.path.join(self.ruta_obra(), 'personal_obra.json'), 'rb') as fh:
            self.assertEqual(fh.read(), con_orden_a, 'mismo contenido, mismos bytes, lo ingieras en el orden que lo ingieras')
        self.assertEqual(P.exportar_estado(self.raiz, OBRAS, generado=AHORA), estado_a)


class TestHorarioPropioYFusion(HorarioPropioBase):
    def base(self, *extra):
        self.ing(lote([jor('vivienda', '2026-10-19', [('Mikel', 7.5, 0)]), jor('vivienda', '2026-10-20', [('Mikell', 7.5, 0)])] + list(extra)), escribir=True)

    def con(self, ex, obra='olabeaga'):
        self.assertTrue(self.ing(lote([], obra=obra, excepciones_horario=ex), escribir=True)['ok'])

    def fusionar(self):
        return P.fusionar(self.raiz, 'T0002', 'T0001', escribir=True, ahora=AHORA)

    def test_dos_horarios_distintos_impiden_fusionar(self):
        self.base()
        self.con({'Mikel': {'vie': 9}, 'Mikell': {'vie': 8}})
        h = self.hashes()
        r = self.fusionar()
        self.assertFalse(r['ok'])
        self.assertEqual(r['error'], 'conflicto_en_horario_propio')
        self.assertEqual(self.hashes(), h, 'si no se puede fusionar no cambia nada')

    def test_dos_horarios_iguales_si_se_fusionan(self):
        self.base()
        self.con({'Mikel': {'vie': 9}, 'Mikell': {'vie': 9}})
        self.assertTrue(self.fusionar()['ok'])
        self.assertEqual(self.exc_est(), {'Mikel': {'vie': 9}})

    def test_en_obras_distintas_no_hay_conflicto(self):
        self.base()
        self.con({'Mikel': {'vie': 9}})
        self.ing(lote([jor('vivienda', '2026-10-21', [('Mikell', 7.5, 0)])], obra='mungia', excepciones_horario={'Mikell': {'vie': 8}}), escribir=True)
        self.assertTrue(self.fusionar()['ok'])
        self.assertEqual(self.exc_est('olabeaga'), {'Mikel': {'vie': 9}})
        self.assertEqual(self.exc_est('mungia'), {'Mikel': {'vie': 8}})

    def test_el_destino_hereda_el_horario_del_origen(self):
        self.base()
        self.con({'Mikell': {'vie': 8}})
        self.assertTrue(self.fusionar()['ok'])
        self.assertEqual(self.exc_est(), {'Mikel': {'vie': 8}}, 'el horario propio no se pierde al fusionar')

    def test_fijar_al_destino_limpia_el_del_origen(self):
        self.base()
        self.con({'Mikell': {'vie': 8}})
        self.fusionar()
        r = self.ing(lote([], excepciones_horario={'Mikel': {'vie': 9}}), escribir=True)
        self.assertEqual(r['excepciones'], [{'nombre': 'Mikel', 'id': 'T0001', 'accion': 'fijada'}])
        self.assertEqual(self.exc_obra(), {'T0001': {'vie': 9}}, 'no queda la entrada vieja del nombre fusionado')
        self.assertEqual(self.exc_est(), {'Mikel': {'vie': 9}})

    def test_fijar_con_el_nombre_fusionado_tambien_limpia(self):
        self.base()
        self.con({'Mikell': {'vie': 8}})
        self.fusionar()
        self.ing(lote([], excepciones_horario={'mikell': {'vie': 7}}), escribir=True)
        self.assertEqual(self.exc_obra(), {'T0001': {'vie': 7}})

    def test_quitar_no_deja_resucitar_el_del_origen(self):
        self.base()
        self.con({'Mikell': {'vie': 8}})
        self.fusionar()
        r = self.ing(lote([], excepciones_horario={'Mikel': {}}), escribir=True)
        self.assertEqual(r['excepciones'], [{'nombre': 'Mikel', 'id': 'T0001', 'accion': 'quitada'}])
        self.assertEqual(self.exc_obra(), {})
        self.assertEqual(self.exc_est(), {})

    def test_en_el_estado_manda_el_destino_y_si_no_el_id_menor(self):
        self.base(jor('vivienda', '2026-10-21', [('Mikal', 7.5, 0)]))
        self.assertTrue(self.fusionar()['ok'])
        self.assertTrue(P.fusionar(self.raiz, 'T0003', 'T0001', escribir=True, ahora=AHORA)['ok'])
        self.editar_obra(lambda d: d.update({'excepciones_horario': {'T0002': {'vie': 8}, 'T0003': {'vie': 7}}}))
        self.assertEqual(self.exc_est(), {'Mikel': {'vie': 8}}, 'sin horario propio en el destino, manda el id menor de los fusionados')
        self.editar_obra(lambda d: d.update({'excepciones_horario': {'T0003': {'vie': 7}, 'T0001': {'vie': 9}, 'T0002': {'vie': 8}}}))
        self.assertEqual(self.exc_est(), {'Mikel': {'vie': 9}}, 'con horario propio en el destino, manda el del destino')

    def test_destino_con_id_mayor_que_el_origen(self):
        """El destino manda aunque su id sea MAYOR que el del fusionado (no basta con recorrer por id y quedarse con el primero)."""
        self.base()
        self.editar_obra(lambda d: d.update({'excepciones_horario': {'T0001': {'vie': 8}, 'T0002': {'vie': 9}}}))
        self.assertTrue(P.fusionar(self.raiz, 'T0001', 'T0002', escribir=False, ahora=AHORA)['error'] == 'conflicto_en_horario_propio')
        self.editar_obra(lambda d: d.update({'excepciones_horario': {'T0001': {'vie': 8}}}))
        self.assertTrue(P.fusionar(self.raiz, 'T0001', 'T0002', escribir=True, ahora=AHORA)['ok'])
        self.editar_obra(lambda d: d.update({'excepciones_horario': {'T0001': {'vie': 8}, 'T0002': {'vie': 9}}}))
        self.assertEqual(self.exc_est(), {'Mikell': {'vie': 9}}, 'manda el del destino (T0002 = Mikell) aunque su id sea mayor')

    def test_el_conflicto_usa_el_id_menor_de_los_heredados(self):
        self.base(jor('vivienda', '2026-10-21', [('Mikal', 7.5, 0)]), jor('vivienda', '2026-10-22', [('Xabier', 7.5, 0)]))   # T0001..T0004
        self.assertTrue(self.fusionar()['ok'])                                                    # T0002 -> T0001
        self.assertTrue(P.fusionar(self.raiz, 'T0003', 'T0001', escribir=True, ahora=AHORA)['ok'])   # T0003 -> T0001
        self.editar_obra(lambda d: d.update({'excepciones_horario': {'T0002': {'vie': 8}, 'T0003': {'vie': 7}, 'T0004': {'vie': 8}}}))
        r = P.fusionar(self.raiz, 'T0001', 'T0004', escribir=False, ahora=AHORA)
        self.assertTrue(r['ok'], 'el horario heredado de Mikel es el del id menor (T0002 = 8 h), igual que el de Xabier: no hay conflicto: %s' % r)

    def test_el_conflicto_cuenta_lo_heredado_de_fusiones_anteriores(self):
        self.base(jor('vivienda', '2026-10-21', [('Mikal', 7.5, 0)]))      # Mikel T0001, Mikell T0002, Mikal T0003
        self.con({'Mikal': {'vie': 8}})
        self.assertTrue(P.fusionar(self.raiz, 'T0003', 'T0001', escribir=True, ahora=AHORA)['ok'], 'Mikel hereda el horario de Mikal')
        self.con({'Mikell': {'vie': 9}})
        h = self.hashes()
        r = P.fusionar(self.raiz, 'T0001', 'T0002', escribir=True, ahora=AHORA)
        self.assertFalse(r['ok'], 'Mikel (con el 8 heredado de Mikal) contra Mikell (9) es un conflicto: no se puede tirar el 8 sin avisar')
        self.assertEqual(r['error'], 'conflicto_en_horario_propio')
        self.assertEqual(self.hashes(), h)


class TestCLI(Base):
    def ejecutar(self, *args):
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        p = subprocess.run([sys.executable, os.path.join(MOTOR, 'personal_obra.py')] + list(args),
                           capture_output=True, env=env, cwd=MOTOR, timeout=60)
        return p.returncode, p.stdout.decode('utf-8', 'replace') + p.stderr.decode('utf-8', 'replace')

    def fichero(self, contenido, nombre='lote.json'):
        d = self.raiz + '_entrada'
        os.makedirs(d, exist_ok=True)
        ruta = os.path.join(d, nombre)
        with open(ruta, 'w', encoding='utf-8') as fh:
            fh.write(contenido if isinstance(contenido, str) else json.dumps(contenido, ensure_ascii=False))
        return ruta

    def args(self, ruta, *extra):
        return ('ingerir', ruta, '--raiz', self.raiz, '--obras', 'olabeaga=2026 OLABEAGA BILBAO', '--hoy', HOY) + extra

    def test_simula_por_defecto_y_avisa(self):
        codigo, salida = self.ejecutar(*self.args(self.fichero(L1)))
        self.assertEqual(codigo, 0, salida)
        self.assertIn('REVISAR', salida)
        self.assertEqual(self.hashes(), {})

    def test_escribir(self):
        codigo, salida = self.ejecutar(*self.args(self.fichero(L1), '--escribir'))
        self.assertEqual(codigo, 0, salida)
        self.assertTrue(os.path.isfile(self.ruta_cat()))

    def test_horario_propio_en_la_cli(self):
        l = lote(L1['jornadas'], excepciones_horario={'Aitor': {'vie': 9}, 'Mikel': {}})
        codigo, salida = self.ejecutar(*self.args(self.fichero(l)))
        self.assertEqual(codigo, 0, salida)
        self.assertIn('HORARIO PROPIO Aitor fijada', salida)
        self.assertIn('HORARIO PROPIO Mikel sin_cambios', salida)
        self.assertIn('REVISAR alta_nueva Aitor', salida)
        self.assertEqual(self.hashes(), {}, 'sin --escribir no se guarda nada')
        codigo, salida = self.ejecutar(*self.args(self.fichero(l, 'otro.json'), '--escribir'))
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(P.cargar_obra(self.raiz, {'olabeaga': OBRAS['olabeaga']}, 'olabeaga')['excepciones_horario'], {'T0004': {'vie': 9}})

    def test_lote_rechazado_dice_por_que(self):
        l = lote(L1['jornadas'], excepciones_horario={'Mikel': {'xxx': 9}})
        codigo, salida = self.ejecutar(*self.args(self.fichero(l)))
        self.assertEqual(codigo, 2, salida)
        self.assertIn('excepcion_invalida', salida, 'un lote rechazado entero no puede salir en silencio')

    def test_codigos_de_salida(self):
        self.assertEqual(self.ejecutar(*self.args(self.fichero(lote([jor('sotano', '2026-10-22', [('Mikel', 7.5, 0)])]))))[0], 2)
        self.assertEqual(self.ejecutar(*self.args(self.fichero(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5, 0)])], obra='mungia'))))[0], 2)
        self.assertEqual(self.ejecutar(*self.args(os.path.join(self.raiz, 'no_existe.json')))[0], 1)
        self.assertEqual(self.ejecutar(*self.args(self.fichero('esto no es json', 'malo.json')))[0], 1)


class TestCodigoFuente(unittest.TestCase):
    def test_solo_biblioteca_estandar(self):
        ruta = P.__file__
        with open(ruta, 'rb') as fh:
            crudo = fh.read()
        self.assertFalse(crudo.startswith(b'\xef\xbb\xbf'), 'sin BOM')
        arbol = ast.parse(crudo.decode('utf-8'))
        permitidos = set(sys.stdlib_module_names)
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                nombres = [a.name.split('.')[0] for a in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                nombres = [(nodo.module or '').split('.')[0]]
            else:
                continue
            for n in nombres:
                if n in ('registro_obras', 'personal_integracion'):
                    continue  # permitidos solo importados al usarlos (se comprueba abajo)
                self.assertIn(n, permitidos, 'dependencia externa: %s' % n)
        for nodo in arbol.body:
            if isinstance(nodo, (ast.Import, ast.ImportFrom)):
                n = nodo.names[0].name if isinstance(nodo, ast.Import) else (nodo.module or '')
                self.assertNotIn(n.split('.')[0], ('registro_obras', 'personal_integracion'),
                                 'registro_obras y personal_integracion deben importarse dentro de una función')


def setUpModule():
    global TMP, _TMP_OBJ
    _TMP_OBJ = tempfile.TemporaryDirectory(prefix='personal_p1_')
    TMP = _TMP_OBJ.name


def tearDownModule():
    _TMP_OBJ.cleanup()


if __name__ == '__main__':
    unittest.main()
