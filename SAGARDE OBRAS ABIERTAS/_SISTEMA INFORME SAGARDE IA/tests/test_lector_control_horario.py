# -*- coding: utf-8 -*-
"""Pruebas de lector_control_horario.py (paso 08a de «Personal en obra»): listar, analizar (vista previa) y aplicar
los CONTROL HORARIO de la carpeta REVISIONES de una obra. Datos INVENTADOS. unittest de la biblioteca estándar."""
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import uuid
from unittest import mock

MOTOR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # _SISTEMA INFORME SAGARDE IA
sys.path.insert(0, MOTOR)
import lector_control_horario as L
import personal_obra as P

TMP = None
_TMP_OBJ = None
OBRAS = {'olabeaga': '2026 OLABEAGA BILBAO', 'mungia': '2026 MUNGIA ACR NEINOR', 'bolueta': '2026 BOLUETA'}
HOY = '2026-10-25'
AHORA = '2026-10-25T22:00:00+02:00'
NOM = 'CONTROL HORARIO 2026 OLABEAGA BILBAO %s.json'
PALABRAS = re.compile(r'\b(exportar|exportad\w*|importar|importad\w*|lotes?|ingerir|ingesta|json|pendientes?|alta|altas|'
                      r'simulaci\w+|estado|base de datos)\b', re.I)


def jor(ambito, fecha, presentes, **kw):
    d = {'ambito': ambito, 'fecha': fecha, 'presentes': [{'nombre': n, 'horas': h, 'extra': 0} for n, h in presentes]}
    d.update(kw)
    return d


def lote(jornadas, obra='olabeaga', **kw):
    d = {'tipo': 'lote_personal', 'version': 1, 'obra': obra, 'jornadas': jornadas}
    d.update(kw)
    return d


H8 = {'lun': 8, 'mar': 8, 'mie': 8, 'jue': 8, 'vie': 8}


class Base(unittest.TestCase):
    def setUp(self):
        self.raiz = os.path.join(TMP, uuid.uuid4().hex)
        os.makedirs(self.raiz)

    def tearDown(self):
        shutil.rmtree(self.raiz, ignore_errors=True)

    def rev(self, obra='olabeaga'):
        d = os.path.join(self.raiz, OBRAS[obra], 'REVISIONES')
        os.makedirs(d, exist_ok=True)
        return d

    def fichero(self, nombre, contenido, obra='olabeaga'):
        """Deja un fichero en REVISIONES: un lote (dict) se escribe como JSON; bytes tal cual."""
        ruta = os.path.join(self.rev(obra), nombre)
        if isinstance(contenido, (dict, list)):
            contenido = json.dumps(contenido, ensure_ascii=False, indent=1).encode('utf-8')
        elif isinstance(contenido, str):
            contenido = contenido.encode('utf-8')
        with open(ruta, 'wb') as fh:
            fh.write(contenido)
        return ruta

    def listar(self, obra='olabeaga'):
        return L.listar(self.rev(obra))

    def analizar(self, obra='olabeaga', aceptar=False, hoy=HOY):
        return L.analizar(obra, self.listar(obra), hoy, self.raiz, OBRAS, aceptar=aceptar, ahora=AHORA)

    def aplicar(self, obra='olabeaga', aceptar=False, hoy=HOY):
        return L.aplicar(obra, self.listar(obra), hoy, self.raiz, OBRAS, aceptar=aceptar, ahora=AHORA)

    def previo(self, l, **kw):
        """Datos que ya estaban (camino antiguo, sin SHA)."""
        r = P.ingerir_lote(copy.deepcopy(l), self.raiz, OBRAS, kw.get('hoy', HOY), escribir=True, ahora=AHORA)
        self.assertTrue(r['ok'], r)

    def hashes(self):
        out = {}
        for d, _, fs in os.walk(self.raiz):
            for f in fs:
                p = os.path.join(d, f)
                with open(p, 'rb') as fh:
                    out[os.path.relpath(p, self.raiz).replace(os.sep, '/')] = hashlib.sha256(fh.read()).hexdigest()
        return out

    def estados(self, r):
        return {f['nombre']: f['estado'] for f in r['ficheros']}

    def codigos(self, f):
        return [m['codigo'] for m in f['motivos']]

    def uno(self, r):
        self.assertEqual(len(r['ficheros']), 1, r['ficheros'])
        return r['ficheros'][0]

    def filas(self, obra='olabeaga'):
        return P.aplanar(self.raiz, OBRAS, obra)


class TestListar(Base):
    def test_detecta_solo_los_control_horario(self):
        self.fichero(NOM % '25102026', lote([]))
        self.fichero(NOM % '25102026 (1)', lote([]))
        self.fichero('control horario otro 24102026.JSON', lote([]))
        self.fichero('REVISION 2026 OLABEAGA BILBAO 21102026.html', '<html></html>')
        self.fichero('otro.json', lote([]))
        self.fichero('CONTROL HORARIO notas.txt', 'hola')
        os.makedirs(os.path.join(self.rev(), 'CONTROL HORARIO carpeta.json'))
        nombres = [f['nombre'] for f in self.listar()]
        self.assertEqual(nombres, ['control horario otro 24102026.JSON', NOM % '25102026', NOM % '25102026 (1)'])

    def test_sha_fecha_y_copia(self):
        ruta = self.fichero(NOM % '25102026 (2)', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        f = self.listar()[0]
        with open(ruta, 'rb') as fh:
            crudo = fh.read()
        self.assertEqual((f['sha256'], f['bytes'], f['ruta']), (hashlib.sha256(crudo).hexdigest(), len(crudo), ruta))
        self.assertEqual((f['fecha_nombre'], f['copia'], f['error']), ('2026-10-25', 2, None))

    def test_sin_fecha_o_con_fecha_imposible(self):
        self.fichero('CONTROL HORARIO 2026 OLABEAGA BILBAO.json', lote([]))
        self.fichero(NOM % '31022026', lote([]))
        self.fichero(NOM % '25102026', lote([]))
        fs = self.listar()
        self.assertEqual([f['fecha_nombre'] for f in fs], [None, None, '2026-10-25'])

    def test_orden_por_fecha_copia_y_nombre(self):
        for n in ('26102026', '25102026 (1)', '25102026', '24102026', '25102026 (10)', '25102026 (2)'):
            self.fichero(NOM % n, lote([]))
        esperado = ['24102026', '25102026', '25102026 (1)', '25102026 (2)', '25102026 (10)', '26102026']
        self.assertEqual([f['nombre'][len('CONTROL HORARIO 2026 OLABEAGA BILBAO '):-5] for f in self.listar()], esperado)

    def test_carpeta_inexistente_o_vacia(self):
        self.assertEqual(L.listar(os.path.join(self.raiz, 'no_existe')), [])
        self.assertEqual(L.listar(self.rev('mungia')), [])


class TestAnalizar(Base):
    def test_un_fichero_limpio_esta_listo_y_no_escribe_nada(self):
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5), ('Txomin', 8)]),
                                             jor('garaje', '2026-10-22', [('Andoni', 7.5)])]))
        antes = self.hashes()
        r = self.analizar()
        self.assertEqual(self.hashes(), antes, 'la vista previa no escribe NADA')
        f = self.uno(r)
        self.assertEqual((f['estado'], f['motivos'], f['rechazadas']), ('listo', [], 0))
        self.assertEqual(r['cuenta'], {'ya_aplicado': 0, 'listo': 1, 'a_revisar': 0, 'rechazado': 0})
        self.assertEqual((r['pendientes'], r['frena']), (1, False))
        self.assertEqual((r['antes'], r['despues']), (None, {'horas': 23.0, 'dias': 1, 'trabajadores': 3}))
        viv = next(j for j in f['jornadas'] if j['ambito'] == 'vivienda')
        self.assertEqual((viv['accion'], viv['personas'], viv['horas'], viv['antes']), ('alta', ['Mikel', 'Txomin'], 15.5, None))
        self.assertEqual([p['nombre'] for p in f['personas_nuevas']], ['Mikel', 'Txomin', 'Andoni'])
        self.assertEqual(f['resumen'], '2 jornadas de garajes y viviendas, 3 personas nuevas')
        self.assertTrue(all(a['codigo'] == 'alta_nueva' and a['texto'] for a in f['avisos']))

    def test_antes_y_despues_de_las_horas(self):
        self.previo(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5)])]))
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5), ('Txomin', 8)])]))
        r = self.analizar()
        self.assertEqual(r['antes'], {'horas': 7.5, 'dias': 1, 'trabajadores': 1})
        self.assertEqual(r['despues'], {'horas': 23.0, 'dias': 2, 'trabajadores': 2})

    def test_los_avisos_que_obligan_a_mirar(self):
        self.previo(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5), ('Txomin', 7.5)])]))
        casos = {
            'nombre_parecido': lote([jor('vivienda', '2026-10-22', [('Mikell', 7.5)])]),
            'suma_diaria_alta': lote([jor('vivienda', '2026-10-22', [('Mikel', 13)])]),
            'fecha_futura': lote([jor('vivienda', '2026-10-30', [('Mikel', 7.5)])]),
            'reemplazo': lote([jor('vivienda', '2026-10-21', [('Mikel', 8), ('Txomin', 7.5)])]),
            'renombre_coincide_con_otro': lote([], renombres=[{'de': 'Mikel', 'a': 'Txomin'}]),
            'anulacion': lote([{'ambito': 'vivienda', 'fecha': '2026-10-21', 'anulada': True, 'presentes': []}]),
        }
        for codigo, l in casos.items():
            for viejo in os.listdir(self.rev()):
                os.remove(os.path.join(self.rev(), viejo))
            self.fichero(NOM % '23102026', l)
            antes = self.hashes()
            f = self.uno(self.analizar())
            self.assertEqual(f['estado'], 'a_revisar', codigo)
            self.assertIn(codigo, self.codigos(f), codigo)
            self.assertEqual(self.hashes(), antes)
            self.assertTrue(all(m['texto'] for m in f['motivos']))

    def test_lo_informativo_no_para_nada(self):
        self.previo(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5)])]))
        self.fichero(NOM % '22102026', lote([], renombres=[{'de': 'Mikel', 'a': 'Mikel Etxeberria'}]))
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-20', [('Mikel', 7.5), ('Aitor', 7.5)])],
                                            renombres=[{'de': 'Fantasma', 'a': 'Nuevo'}], altas=['Rafa']))
        r = self.analizar()
        self.assertEqual(self.estados(r), {NOM % '22102026': 'listo', NOM % '23102026': 'listo'})
        codigos = [a['codigo'] for f in r['ficheros'] for a in f['avisos']]
        self.assertIn('renombre_sin_origen', codigos)
        self.assertIn('nombre_anterior_usado', codigos)
        self.assertIn('alta_nueva', codigos)
        self.assertFalse(r['frena'])

    def test_rechazados(self):
        casos = {
            'json roto': (b'{"tipo": ', 'ilegible'),
            'vacio': (b'', 'ilegible'),
            'bytes que no son utf8': (b'\xff\xfe\x00\x01', 'ilegible'),
            'no es un objeto': ('[1, 2]', 'tipo_desconocido'),
            'otro tipo': (dict(lote([]), tipo='otra_cosa'), 'tipo_desconocido'),
            'version 2': (dict(lote([]), version=2), 'version_desconocida'),
            'campo extra': (dict(lote([]), dni='x'), 'campo_desconocido'),
            'obra que no existe': (lote([], obra='zzz'), 'obra_invalida'),
            'cambio de nombre mal escrito': (lote([], renombres=[{'de': 'A'}]), 'renombre_invalido'),
            'nombre nuevo mal escrito': (lote([], altas=['']), 'alta_invalida'),
        }
        for nombre, (contenido, codigo) in casos.items():
            for viejo in os.listdir(self.rev()):
                os.remove(os.path.join(self.rev(), viejo))
            self.fichero(NOM % '23102026', contenido)
            antes = self.hashes()
            r = self.analizar()
            f = self.uno(r)
            self.assertEqual(f['estado'], 'rechazado', nombre)
            self.assertIn(codigo, self.codigos(f), nombre)
            self.assertTrue(r['frena'], nombre)
            self.assertEqual(self.hashes(), antes, nombre)

    def test_obra_distinta_a_la_de_la_carpeta(self):
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])], obra='mungia'))
        f = self.uno(self.analizar())
        self.assertEqual((f['estado'], self.codigos(f)), ('rechazado', ['obra_distinta']))
        self.assertIn('2026 MUNGIA ACR NEINOR', f['motivos'][0]['texto'])
        r = self.aplicar()
        self.assertEqual(r['aplicados'], [])
        self.assertFalse(any('personal_obra.json' in k for k in self.hashes()), 'no se crea nada en ninguna obra')

    def test_datos_privados_se_rechazan_sin_repetir_el_valor(self):
        casos = [
            lote([jor('vivienda', '2026-10-22', [('12345678Z', 7.5)])]),
            lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])], excepciones_horario={'612 345 678': H8}),
            lote([], altas=['ana@empresa.com']),
            lote([], renombres=[{'de': 'Mikel', 'a': 'Mikel<b>'}]),
            lote([jor('garaje', '2026-10-22', [('Mikel <script>', 7.5)])]),
        ]
        for l in casos:
            for viejo in os.listdir(self.rev()):
                os.remove(os.path.join(self.rev(), viejo))
            self.fichero(NOM % '23102026', l)
            f = self.uno(self.analizar())
            self.assertEqual((f['estado'], self.codigos(f)[-1]), ('rechazado', 'dato_privado'), l)
            t = f['motivos'][-1]['texto']
            for valor in ('12345678Z', '612 345 678', 'ana@empresa.com', 'script'):
                self.assertNotIn(valor, t)

    def test_una_jornada_mala_no_tumba_el_fichero(self):
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)]),
                                             jor('garaje', '2026-10-22', [('Andoni', 99)])]))
        f = self.uno(self.analizar())
        self.assertEqual((f['estado'], f['rechazadas']), ('listo', 1))
        mala = next(j for j in f['jornadas'] if j['estado'] == 'rechazada')
        self.assertEqual([m['codigo'] for m in mala['rechazos']], ['horas_invalidas'])
        self.assertIn('1 jornada que no vale', f['resumen'])

    def test_si_todas_las_jornadas_se_rechazan_el_fichero_se_rechaza(self):
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 99)])]))
        f = self.uno(self.analizar())
        self.assertEqual((f['estado'], self.codigos(f)), ('rechazado', ['todo_rechazado']))

    def test_ya_aplicado_por_sha_aunque_cambie_el_nombre(self):
        l = lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])])
        self.fichero(NOM % '23102026', l)
        self.aplicar()
        self.fichero(NOM % '23102026 (1)', l)
        self.fichero('CONTROL HORARIO copia a mano.json', l)
        r = self.analizar()
        self.assertEqual(set(self.estados(r).values()), {'ya_aplicado'})
        self.assertEqual((r['pendientes'], r['frena']), (0, False))

    def test_dos_copias_en_la_misma_tanda_cuentan_una_sola_vez(self):
        l = lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])])
        self.fichero(NOM % '23102026', l)
        self.fichero(NOM % '23102026 (1)', l)
        r = self.analizar()
        self.assertEqual(self.estados(r), {NOM % '23102026': 'listo', NOM % '23102026 (1)': 'ya_aplicado'})
        self.assertEqual(r['ficheros'][1]['motivos'][0]['codigo'], 'copia_de')

    def test_un_fichero_con_bom_se_lee(self):
        crudo = '\ufeff'.encode('utf-8') + json.dumps(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])])).encode('utf-8')
        self.fichero(NOM % '23102026', crudo)
        self.assertEqual(self.uno(self.analizar())['estado'], 'listo')
        self.assertEqual(len(self.aplicar()['aplicados']), 1)
        self.assertEqual([f['nombre'] for f in self.filas()], ['Mikel'])

    def test_el_orden_de_aplicacion_no_depende_del_orden_en_que_se_pasan(self):
        self.fichero(NOM % '25102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 8)])]))
        self.fichero(NOM % '24102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        desordenados = list(reversed(self.listar()))
        r = L.analizar('olabeaga', desordenados, HOY, self.raiz, OBRAS, ahora=AHORA)
        self.assertEqual([f['estado'] for f in r['ficheros']], ['listo', 'a_revisar'])
        self.assertEqual([f['nombre'][-13:-5] for f in r['ficheros']], ['24102026', '25102026'])

    def test_un_fallo_inesperado_al_simular_se_cuenta_y_no_tumba_a_los_demas(self):
        self.fichero(NOM % '22102026', lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5)])]))
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Txomin', 7.5)])]))
        self.fichero(NOM % '24102026', lote([jor('vivienda', '2026-10-23', [('Andoni', 7.5)])]))
        original = L.po.ingerir_lote
        llamadas = []

        def falla_la_segunda(*a, **kw):
            llamadas.append(1)
            if len(llamadas) == 2:
                raise RuntimeError('algo imprevisto')
            return original(*a, **kw)
        with mock.patch.object(L.po, 'ingerir_lote', side_effect=falla_la_segunda):
            r = self.analizar()
        self.assertEqual([f['estado'] for f in r['ficheros']], ['listo', 'rechazado', 'listo'])
        self.assertEqual(self.codigos(r['ficheros'][1]), ['error_interno'])
        self.assertIn('algo imprevisto', r['ficheros'][1]['motivos'][0]['texto'])
        self.assertTrue(r['frena'])

    def test_un_personal_obra_corrupto_no_tumba_nada_y_no_aplica_nada(self):
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        carpeta = os.path.join(self.raiz, OBRAS['olabeaga'], 'INFORME SAGARDE IA')
        os.makedirs(carpeta)
        with open(os.path.join(carpeta, 'personal_obra.json'), 'w', encoding='utf-8') as fh:
            fh.write('{"version": ')
        antes = self.hashes()
        r = self.analizar()
        self.assertEqual(self.codigos(self.uno(r)), ['datos_ilegibles'])
        self.assertEqual((r['antes'], r['despues'], r['frena']), (None, None, True))
        r2 = self.aplicar()
        self.assertEqual((r2['aplicados'], len(r2['no_aplicados']), r2['antes'], r2['despues']), ([], 1, None, None))
        self.assertEqual(self.hashes(), antes)

    def test_traza_ilegible_no_aplica_nada(self):
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        os.makedirs(os.path.join(self.raiz, OBRAS['olabeaga'], 'INFORME SAGARDE IA', 'personal_jornadas.jsonl'))
        antes = self.hashes()
        r = self.analizar()
        self.assertEqual(self.codigos(self.uno(r)), ['datos_ilegibles'])
        self.assertTrue(r['frena'])
        r2 = self.aplicar()
        self.assertEqual((r2['aplicados'], len(r2['no_aplicados'])), ([], 1))
        self.assertEqual(self.hashes(), antes)

    def test_aceptar_no_libera_a_un_rechazado(self):
        self.fichero(NOM % '23102026', b'{"tipo": ')
        f = self.uno(self.analizar(aceptar=True))
        self.assertEqual(f['estado'], 'rechazado')

    def test_obra_desconocida(self):
        with self.assertRaises(ValueError):
            L.analizar('zzz', [], HOY, self.raiz, OBRAS)

    def test_los_textos_no_llevan_palabras_de_programador_ni_codigos(self):
        self.previo(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5), ('Txomin', 7.5)])]))
        self.fichero(NOM % '20102026', lote([jor('vivienda', '2026-10-22', [('Mikell', 13), ('Aitor', 7.5)]),
                                             jor('garaje', '2026-10-30', [('Mikel', 99)])],
                                            renombres=[{'de': 'Mikel', 'a': 'Txomin'}, {'de': 'Fantasma', 'a': 'Otro'}],
                                            altas=['Rafa']))
        self.fichero(NOM % '21102026', b'{"tipo": ')
        self.fichero(NOM % '22102026', lote([], obra='mungia'))
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('12345678Z', 7.5)])]))
        self.fichero(NOM % '24102026', lote([jor('vivienda', '2026-10-21', [('Mikel', 8), ('Txomin', 7.5)])]))
        r = self.analizar()
        textos = []

        def recoger(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k in ('texto', 'resumen') and isinstance(v, str):
                        if v or k == 'texto':  # el resumen va vacío en los ficheros que no se aplican
                            textos.append(v)
                    else:
                        recoger(v)
            elif isinstance(x, list):
                for v in x:
                    recoger(v)
        recoger(r)
        self.assertGreater(len(textos), 10)
        for t in textos:
            self.assertTrue(t.strip())
            self.assertIsNone(PALABRAS.search(t), t)
            self.assertNotRegex(t, r'[a-z]+_[a-z]+', t)


class TestAplicar(Base):
    def test_aplica_deja_el_sha_y_es_idempotente(self):
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5), ('Txomin', 8)])]))
        self.fichero(NOM % '24102026', lote([jor('garaje', '2026-10-23', [('Andoni', 7.5)])]))
        r = self.aplicar()
        self.assertEqual([f['nombre'] for f in r['aplicados']], [NOM % '23102026', NOM % '24102026'])
        self.assertEqual((r['frena'], r['antes'], r['despues']), (False, None, {'horas': 23.0, 'dias': 2, 'trabajadores': 3}))
        self.assertEqual([p['nombre'] for p in r['personas_nuevas']], ['Mikel', 'Txomin', 'Andoni'])
        shas = {f['sha256'] for f in self.listar()}
        self.assertEqual(P.shas_recibidos(self.raiz, OBRAS, 'olabeaga'), shas)
        despues = self.hashes()
        r2 = self.aplicar()
        self.assertEqual((r2['aplicados'], len(r2['ya_aplicados']), r2['frena']), ([], 2, False))
        self.assertEqual(self.hashes(), despues, 'aplicar dos veces no cambia ni un byte')

    def test_los_a_revisar_solo_entran_con_aceptar(self):
        self.previo(lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        self.fichero(NOM % '24102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 8)])]))
        antes = self.hashes()
        r = self.aplicar()
        self.assertEqual((r['aplicados'], len(r['no_aplicados']), r['frena']), ([], 1, True))
        self.assertEqual(self.hashes(), antes, 'sin aceptar no se toca nada')
        self.assertEqual(self.filas()[0]['horas'], 7.5)
        r = self.aplicar(aceptar=True)
        self.assertEqual((len(r['aplicados']), r['frena']), (1, False))
        self.assertEqual(self.filas()[0]['horas'], 8)
        self.assertEqual((r['antes'], r['despues']), ({'horas': 7.5, 'dias': 1, 'trabajadores': 1},
                                                     {'horas': 8, 'dias': 1, 'trabajadores': 1}))

    def test_un_fichero_malo_entre_buenos_no_tumba_a_los_demas(self):
        self.fichero(NOM % '22102026', lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5)])]))
        self.fichero(NOM % '23102026', b'{"tipo": ')
        self.fichero(NOM % '24102026', lote([jor('vivienda', '2026-10-23', [('Txomin', 7.5)])]))
        r = self.aplicar(aceptar=True)
        self.assertEqual([f['nombre'] for f in r['aplicados']], [NOM % '22102026', NOM % '24102026'])
        self.assertEqual([f['nombre'] for f in r['no_aplicados']], [NOM % '23102026'])
        self.assertTrue(r['frena'])
        self.assertEqual(sorted({f['nombre'] for f in self.filas()}), ['Mikel', 'Txomin'])

    def test_la_ultima_manda_por_fecha_del_nombre(self):
        self.fichero(NOM % '25102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 8)])]))
        self.fichero(NOM % '24102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        r = self.analizar()
        self.assertEqual([f['nombre'][-13:-5] for f in r['ficheros']], ['24102026', '25102026'])
        self.assertEqual([f['estado'] for f in r['ficheros']], ['listo', 'a_revisar'])
        self.aplicar(aceptar=True)
        self.assertEqual(self.filas()[0]['horas'], 8)

    def test_el_orden_dentro_del_fichero_no_importa(self):
        js = [jor('vivienda', '2026-10-22', [('Mikel', 7.5)]), jor('vivienda', '2026-10-20', [('Txomin', 7.5)]),
              jor('garaje', '2026-10-21', [('Andoni', 7.5)]), jor('vivienda', '2026-10-21', [('Mikel', 8)])]
        resultados = []
        for orden in (js, list(reversed(js)), js[2:] + js[:2]):
            self.setUp()
            self.fichero(NOM % '23102026', lote(copy.deepcopy(orden)))
            self.aplicar()
            resultados.append((self.filas(), sorted(t['nombre'] for t in P.cargar_catalogo(self.raiz)['trabajadores'])))
        self.assertEqual(resultados[0][0], resultados[1][0])
        self.assertEqual(resultados[0][0], resultados[2][0])
        self.assertEqual(len(resultados[0][0]), 4)

    def test_nombres_con_empresa_y_tildes(self):
        nombres = ['Javi @ CATERSYSTEM', 'Ana @ EMPRESA Y', 'Pepe (Contrata X)', 'Íñigo Ibarra', 'Chico 1 @ CATERSYSTEM']
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [(n, 7.5) for n in nombres])],
                                            excepciones_horario={'Javi @ CATERSYSTEM': H8}))
        r = self.aplicar()
        self.assertEqual((len(r['aplicados']), r['frena']), (1, False))
        self.assertEqual(sorted(f['nombre'] for f in self.filas()), sorted(nombres))
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])
        self.assertEqual(len(r['aplicados'][0]['horarios_propios']), 1)

    def test_renombres_y_altas_viajan_en_el_fichero(self):
        self.previo(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5)])]))
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel Etxeberria', 7.5)])],
                                            renombres=[{'de': 'Mikel', 'a': 'Mikel Etxeberria'}], altas=['Rafa']))
        r = self.aplicar()
        self.assertEqual((len(r['aplicados']), r['frena']), (1, False))
        cat = P.cargar_catalogo(self.raiz)['trabajadores']
        self.assertEqual([(t['nombre'], t.get('nombres_anteriores')) for t in cat], [('Mikel Etxeberria', ['Mikel']), ('Rafa', None)])
        self.assertEqual({f['nombre'] for f in self.filas()}, {'Mikel Etxeberria'})
        self.assertEqual(r['aplicados'][0]['resumen'], '1 jornada de viviendas, 1 cambio de nombre, 1 persona nueva')

    def test_la_primera_vez_crea_la_obra_sola(self):
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        self.assertFalse(os.path.exists(os.path.join(self.raiz, OBRAS['olabeaga'], 'INFORME SAGARDE IA', 'personal_obra.json')))
        self.aplicar()
        self.assertTrue(os.path.exists(os.path.join(self.raiz, OBRAS['olabeaga'], 'INFORME SAGARDE IA', 'personal_obra.json')))
        self.assertEqual(P.comprobar(self.raiz, OBRAS), [])

    def test_un_fichero_sin_novedades_solo_se_anota(self):
        l = lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])])
        self.previo(l)
        self.fichero(NOM % '23102026', l)
        f = self.uno(self.analizar())
        self.assertEqual((f['estado'], f['sin_efecto'], self.codigos(f)), ('listo', True, ['sin_efecto']))
        antes = self.hashes()
        self.aplicar()
        despues = self.hashes()
        cambiados = [k for k in despues if antes.get(k) != despues[k]]
        self.assertEqual(cambiados, ['2026 OLABEAGA BILBAO/INFORME SAGARDE IA/personal_jornadas.jsonl'])
        self.assertEqual(len(P.shas_recibidos(self.raiz, OBRAS, 'olabeaga')), 1)

    def test_las_otras_obras_y_revisiones_no_se_mueven(self):
        self.previo(lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5)])], obra='mungia'))
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Txomin', 7.5)])]))
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-20', [('Rafa', 7.5)])], obra='bolueta'), obra='bolueta')
        antes = self.hashes()
        self.aplicar()
        despues = self.hashes()
        cambiados = {k.split('/')[0] + '/' + k.split('/')[-1] for k in despues if antes.get(k) != despues[k]}
        self.assertEqual(cambiados, {'2026 OLABEAGA BILBAO/personal_obra.json', '2026 OLABEAGA BILBAO/personal_jornadas.jsonl',
                                     '_SISTEMA INFORME SAGARDE IA/personal_catalogo.json'})
        for k in antes:
            if '/REVISIONES/' in k:
                self.assertEqual(antes[k], despues[k], 'el original se conserva en REVISIONES')

    def test_lo_simulado_es_lo_aplicado(self):
        self.previo(lote([jor('vivienda', '2026-10-22', [('Pepe', 7.5)])]))
        self.fichero(NOM % '24102026', lote([jor('vivienda', '2026-10-21', [('Pepe', 7.5), ('Ana @ EMPRESA Y', 8)]),
                                             jor('vivienda', '2026-10-22', [('Pepe', 7.5)])]))
        self.fichero(NOM % '25102026', lote([jor('vivienda', '2026-10-21', [('Pepe', 7.5), ('Ana @ EMPRESA Y', 8)]),
                                             jor('vivienda', '2026-10-22', [('Pepe', 7.5), ('Íñigo', 8)])],
                                            excepciones_horario={'Ana @ EMPRESA Y': H8}))
        previsto = self.analizar(aceptar=True)
        real = self.aplicar(aceptar=True)
        self.assertEqual([f['estado'] for f in previsto['ficheros']], ['listo', 'a_revisar'])
        self.assertTrue(previsto['ficheros'][1]['aceptado'])
        for a, b in zip(previsto['ficheros'], real['aplicados']):
            self.assertEqual([(j['ambito'], j['fecha'], j['accion'], j['horas']) for j in a['jornadas']],
                             [(j['ambito'], j['fecha'], j['accion'], j['horas']) for j in b['jornadas']])
        self.assertEqual(previsto['despues'], real['despues'])

    def test_si_el_fichero_cambia_antes_de_aplicarse_no_se_aplica(self):
        ruta = self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        ficha = self.analizar()['ficheros'][0]
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 9)])]))
        antes = self.hashes()
        f = L._aplicar_uno('olabeaga', ficha, HOY, self.raiz, OBRAS, AHORA)
        self.assertEqual((f['estado'], self.codigos(f)[-1]), ('rechazado', 'cambio_en_disco'))
        self.assertEqual(self.hashes(), antes)

    def test_si_no_se_puede_anotar_se_dice(self):
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Mikel', 7.5)])]))
        with mock.patch.object(L.po, 'shas_recibidos', return_value=set()):
            r = self.aplicar()
        self.assertEqual(self.codigos(r['aplicados'][0])[-1], 'no_anotado')

    def test_un_fallo_inesperado_se_cuenta_y_no_tumba_a_los_demas(self):
        self.fichero(NOM % '22102026', lote([jor('vivienda', '2026-10-21', [('Mikel', 7.5)])]))
        self.fichero(NOM % '23102026', lote([jor('vivienda', '2026-10-22', [('Txomin', 7.5)])]))
        original = L.po.ingerir_lote
        llamadas = []

        def falla_la_primera(*a, **kw):
            llamadas.append(1)
            if kw.get('escribir') and len(llamadas) == 3:
                raise RuntimeError('disco lleno')
            return original(*a, **kw)
        with mock.patch.object(L.po, 'ingerir_lote', side_effect=falla_la_primera):
            r = self.aplicar()
        self.assertEqual(len(r['errores']), 1)
        self.assertIn('error_interno', self.codigos(r['errores'][0]))
        self.assertTrue(r['frena'])
        self.assertEqual(len(r['aplicados']), 1)


class TestPilotoInventado(Base):
    """Copias del mismo fichero acumulativo, jornada ya registrada por el camino antiguo y horarios propios."""

    def preparar(self):
        self.previo(lote([jor('vivienda', '2026-10-23', [('Pepe', 7.5)])]))
        a = lote([jor('vivienda', '2026-10-21', [('Pepe', 7.5), ('Ana @ EMPRESA Y', 8)]),
                  jor('vivienda', '2026-10-22', [('Pepe', 7.5), ('Ana @ EMPRESA Y', 8)]),
                  jor('vivienda', '2026-10-23', [('Pepe', 7.5)])])
        b = lote([jor('vivienda', '2026-10-23', [('Pepe', 7.5), ('Ana @ EMPRESA Y', 8), ('Íñigo (Contrata X)', 8)]),
                  jor('vivienda', '2026-10-22', [('Pepe', 7.5), ('Ana @ EMPRESA Y', 8)]),
                  jor('vivienda', '2026-10-21', [('Pepe', 7.5), ('Ana @ EMPRESA Y', 8)])],
                 excepciones_horario={'Ana @ EMPRESA Y': H8})
        self.fichero(NOM % '24102026', a)
        for n in ('25102026', '25102026 (1)', '25102026 (2)'):
            self.fichero(NOM % n, b)

    def test_vista_previa(self):
        self.preparar()
        r = self.analizar()
        self.assertEqual([f['estado'] for f in r['ficheros']], ['listo', 'a_revisar', 'a_revisar', 'a_revisar'])
        self.assertEqual(r['cuenta'], {'ya_aplicado': 0, 'listo': 1, 'a_revisar': 3, 'rechazado': 0})
        self.assertIn('reemplazo', self.codigos(r['ficheros'][1]))
        self.assertEqual(r['antes'], {'horas': 7.5, 'dias': 1, 'trabajadores': 1})
        self.assertEqual(r['despues'], {'horas': 38.5, 'dias': 3, 'trabajadores': 2}, 'sin aceptar, solo entra el primero')

    def test_aceptando_entra_uno_y_las_copias_se_reconocen(self):
        self.preparar()
        r = self.aplicar(aceptar=True)
        self.assertEqual([f['nombre'][len('CONTROL HORARIO 2026 OLABEAGA BILBAO '):-5] for f in r['aplicados']],
                         ['24102026', '25102026'])
        self.assertEqual([f['nombre'][len('CONTROL HORARIO 2026 OLABEAGA BILBAO '):-5] for f in r['ya_aplicados']],
                         ['25102026 (1)', '25102026 (2)'])
        self.assertEqual(len(r['ya_aplicados']), 2)
        self.assertEqual({m['codigo'] for f in r['ya_aplicados'] for m in f['motivos']}, {'copia_de'})
        self.assertEqual((r['antes'], r['despues']), ({'horas': 7.5, 'dias': 1, 'trabajadores': 1},
                                                     {'horas': 54.5, 'dias': 3, 'trabajadores': 3}))
        self.assertEqual(len(P.shas_recibidos(self.raiz, OBRAS, 'olabeaga')), 2)
        despues = self.hashes()
        r2 = self.aplicar(aceptar=True)
        self.assertEqual((r2['aplicados'], len(r2['ya_aplicados'])), ([], 4))
        self.assertEqual(self.hashes(), despues)
        horario = P.cargar_obra(self.raiz, OBRAS, 'olabeaga')['excepciones_horario']
        self.assertEqual(list(horario.values()), [H8])


def setUpModule():
    global TMP, _TMP_OBJ
    _TMP_OBJ = tempfile.TemporaryDirectory(prefix='lector_ch_')
    TMP = _TMP_OBJ.name


def tearDownModule():
    _TMP_OBJ.cleanup()


if __name__ == '__main__':
    unittest.main()
