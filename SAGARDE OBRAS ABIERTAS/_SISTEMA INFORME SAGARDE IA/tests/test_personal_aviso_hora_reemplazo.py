# -*- coding: utf-8 -*-
"""Aviso con las HORAS cuando un fichero sustituye o anula un día que ya estaba guardado (05/11/2026). Datos INVENTADOS.

Decisión de Bixente: «solo avisar». El PC sigue frenando y preguntando como siempre (nada cambia en lo que se aplica); lo único
nuevo es que el aviso enseña a qué hora se apuntó cada versión del día y dice si el fichero es MÁS ANTIGUO que lo guardado.
Un fichero viejo que reaparece (los «(1)», «(2)»…) ya no se confunde con una corrección. NO se ignora nada solo: la hora de un
aparato mal puesta haría pasar por viejo un cambio bueno.

Cifras a mano: noviembre es hora de invierno (Madrid = UTC+1) y julio de verano (UTC+2)."""
import copy
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import uuid

MOTOR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # _SISTEMA INFORME SAGARDE IA
sys.path.insert(0, MOTOR)
import lector_control_horario as L
import personal_obra as P

TMP = None
_TMP_OBJ = None
OBRAS = {'olabeaga': '2026 OLABEAGA BILBAO'}
HOY = '2026-11-05'
AHORA = '2026-11-05T22:00:00+01:00'
NOM = 'CONTROL HORARIO 2026 OLABEAGA BILBAO %s.json'
FRASE_DE_SIEMPRE = 'Ya había una jornada de ese día en esa obra: la nueva la sustituye.'
PALABRAS = re.compile(r'\b(exportar|exportad\w*|importar|importad\w*|lotes?|ingerir|ingesta|json|pendientes?|alta|altas|'
                      r'simulaci\w+|estado|base de datos)\b', re.I)

# Dos momentos en que se pudo apuntar el mismo día
VIEJO = '2026-11-02T08:10:00.000Z'    # lun 02/11, 09:10 en Madrid
NUEVO = '2026-11-04T17:40:00.000Z'    # mié 04/11, 18:40 en Madrid


def jor(fecha, presentes, registrado=None, ambito='vivienda', **kw):
    d = {'ambito': ambito, 'fecha': fecha, 'presentes': [{'nombre': n, 'horas': h, 'extra': 0} for n, h in presentes]}
    if registrado is not None:
        d['registrado'] = registrado
    d.update(kw)
    return d


def lote(jornadas, obra='olabeaga', **kw):
    d = {'tipo': 'lote_personal', 'version': 1, 'obra': obra, 'jornadas': jornadas}
    d.update(kw)
    return d


class TestCompararRegistro(unittest.TestCase):
    """La función pura que compara a qué hora se apuntó lo guardado y a qué hora el fichero."""

    def test_el_fichero_es_mas_antiguo(self):
        sentido, frase = P.comparar_registro(NUEVO, VIEJO)
        self.assertEqual('antiguo', sentido)
        self.assertEqual('Ojo: este fichero es MÁS ANTIGUO que lo guardado (el fichero se apuntó el lun 02/11 a las 09:10; '
                         'lo guardado, el mié 04/11 a las 18:40).', frase)

    def test_el_fichero_es_mas_nuevo(self):
        sentido, frase = P.comparar_registro(VIEJO, NUEVO)
        self.assertEqual('nuevo', sentido)
        self.assertEqual('Este fichero es más nuevo que lo guardado (el fichero se apuntó el mié 04/11 a las 18:40; '
                         'lo guardado, el lun 02/11 a las 09:10).', frase)

    def test_la_hora_se_da_en_la_de_madrid_tambien_en_verano(self):
        # 10:00 UTC de julio = 12:00 en Madrid (UTC+2); de noviembre = 11:00 (UTC+1)
        _, frase = P.comparar_registro('2026-07-01T10:00:00Z', '2026-06-30T10:00:00Z')
        self.assertIn('mar 30/06 a las 12:00', frase)
        self.assertIn('mié 01/07 a las 12:00', frase)
        _, frase = P.comparar_registro('2026-11-02T10:00:00Z', '2026-11-01T10:00:00Z')
        self.assertIn('dom 01/11 a las 11:00', frase)

    def test_cruzar_la_medianoche_cambia_el_dia(self):
        # 23:30 UTC del lunes ya es martes 00:30 en Madrid
        _, frase = P.comparar_registro('2026-11-03T23:30:00Z', '2026-11-02T23:30:00Z')
        self.assertIn('mar 03/11 a las 00:30', frase)
        self.assertIn('mié 04/11 a las 00:30', frase)

    def test_el_mismo_instante_escrito_de_otra_forma_es_igual(self):
        self.assertEqual(('igual', ''), P.comparar_registro('2026-11-02T08:10:00Z', '2026-11-02T09:10:00+01:00'))
        self.assertEqual(('igual', ''), P.comparar_registro(VIEJO, VIEJO))

    def test_lo_que_no_se_puede_comparar_no_inventa_nada(self):
        for malo in (None, '', '   ', 'ayer', 5, 1.5, [], {}, '2026-11-02', '2026-11-02T08:10:00', '2026-13-45T00:00:00Z'):
            self.assertEqual((None, ''), P.comparar_registro(malo, VIEJO), 'guardado ilegible: %r' % (malo,))
            self.assertEqual((None, ''), P.comparar_registro(VIEJO, malo), 'fichero ilegible: %r' % (malo,))
        self.assertEqual((None, ''), P.comparar_registro(None, None))

    def test_las_palabras_son_de_electricista(self):
        for g, f in ((NUEVO, VIEJO), (VIEJO, NUEVO)):
            _, frase = P.comparar_registro(g, f)
            self.assertIsNone(PALABRAS.search(frase), frase)


class TestTextoDelAviso(unittest.TestCase):
    def test_sin_detalle_es_la_frase_de_siempre(self):
        self.assertEqual(FRASE_DE_SIEMPRE, P.texto_aviso('reemplazo'))
        self.assertEqual(FRASE_DE_SIEMPRE, P.texto_aviso('reemplazo', None))

    def test_un_detalle_que_no_se_entiende_tambien(self):
        for raro in ('', 'x', 'a | b', 5, ['a', 'b'], 'solo una parte', ' | '):
            self.assertEqual(FRASE_DE_SIEMPRE, P.texto_aviso('reemplazo', raro), repr(raro))

    def test_con_las_dos_horas_se_añade_la_comparacion(self):
        texto = P.texto_aviso('reemplazo', NUEVO + ' | ' + VIEJO)
        self.assertTrue(texto.startswith(FRASE_DE_SIEMPRE + ' Ojo: este fichero es MÁS ANTIGUO'), texto)
        self.assertIn('lun 02/11 a las 09:10', texto)
        self.assertIn('mié 04/11 a las 18:40', texto)
        texto = P.texto_aviso('reemplazo', VIEJO + ' | ' + NUEVO)
        self.assertTrue(texto.startswith(FRASE_DE_SIEMPRE + ' Este fichero es más nuevo'), texto)


class Base(unittest.TestCase):
    def setUp(self):
        self.raiz = os.path.join(TMP, uuid.uuid4().hex)
        os.makedirs(self.raiz)

    def tearDown(self):
        shutil.rmtree(self.raiz, ignore_errors=True)

    def ing(self, l, escribir=False):
        return P.ingerir_lote(copy.deepcopy(l), self.raiz, OBRAS, HOY, escribir=escribir, ahora=AHORA)

    def rev(self):
        d = os.path.join(self.raiz, OBRAS['olabeaga'], 'REVISIONES')
        os.makedirs(d, exist_ok=True)
        return d

    def fichero(self, nombre, contenido):
        with open(os.path.join(self.rev(), nombre), 'wb') as fh:
            fh.write(json.dumps(contenido, ensure_ascii=False, indent=1).encode('utf-8'))

    def analizar(self, aceptar=False):
        return L.analizar('olabeaga', L.listar(self.rev()), HOY, self.raiz, OBRAS, aceptar=aceptar, ahora=AHORA)

    def aplicar(self, aceptar=False):
        return L.aplicar('olabeaga', L.listar(self.rev()), HOY, self.raiz, OBRAS, aceptar=aceptar, ahora=AHORA)

    def gente(self, fecha='2026-11-03'):
        return sorted(f['nombre'] for f in P.aplanar(self.raiz, OBRAS, 'olabeaga') if f['fecha'] == fecha and f['ambito'] == 'vivienda')

    def aviso_de(self, r, codigo='reemplazo'):
        avisos = [a for a in r['jornadas'][0]['avisos'] if a['codigo'] == codigo]
        self.assertEqual(1, len(avisos), r['jornadas'][0]['avisos'])
        return avisos[0]


class TestEnLaIngesta(Base):
    DIA = '2026-11-03'

    def guardado(self, registrado):
        r = self.ing(lote([jor(self.DIA, [('Mikel', 8), ('Txomin', 7.5)], registrado)]), escribir=True)
        self.assertTrue(r['ok'], r)

    def test_fichero_mas_antiguo_dice_las_dos_horas(self):
        self.guardado(NUEVO)
        r = self.ing(lote([jor(self.DIA, [('Mikel', 8), ('Txomin', 7.5), ('Beto', 8)], VIEJO)]))
        self.assertEqual('reemplazo', r['jornadas'][0]['accion'])
        a = self.aviso_de(r)
        self.assertEqual(NUEVO + ' | ' + VIEJO, a['detalle'], 'primero lo guardado y luego lo del fichero')
        texto = P.texto_aviso(a['codigo'], a['detalle'])
        self.assertIn('MÁS ANTIGUO', texto)
        self.assertIn('lun 02/11 a las 09:10', texto)
        self.assertIn('mié 04/11 a las 18:40', texto)

    def test_fichero_mas_nuevo_lo_dice(self):
        self.guardado(VIEJO)
        r = self.ing(lote([jor(self.DIA, [('Mikel', 8)], NUEVO)]))
        a = self.aviso_de(r)
        self.assertEqual(VIEJO + ' | ' + NUEVO, a['detalle'])
        self.assertIn('más nuevo', P.texto_aviso(a['codigo'], a['detalle']))
        self.assertNotIn('ANTIGUO', P.texto_aviso(a['codigo'], a['detalle']))

    def test_sin_hora_en_el_fichero_no_se_compara_con_la_de_hoy(self):
        # Un fichero sin `registrado` recibe la hora de AHORA al entrar: compararla diría «más nuevo» sin ser verdad
        self.guardado(NUEVO)
        r = self.ing(lote([jor(self.DIA, [('Mikel', 8)])]))
        self.assertEqual('reemplazo', r['jornadas'][0]['accion'])
        self.assertIsNone(self.aviso_de(r)['detalle'])
        self.assertEqual(FRASE_DE_SIEMPRE, P.texto_aviso('reemplazo', None))

    def test_con_la_misma_hora_no_hay_comparacion(self):
        self.guardado(VIEJO)
        r = self.ing(lote([jor(self.DIA, [('Mikel', 8)], VIEJO)]))
        self.assertEqual('reemplazo', r['jornadas'][0]['accion'])
        self.assertIsNone(self.aviso_de(r)['detalle'])

    def test_un_dia_nuevo_no_lleva_aviso_de_reemplazo(self):
        r = self.ing(lote([jor(self.DIA, [('Mikel', 8)], VIEJO)]))
        self.assertEqual('alta', r['jornadas'][0]['accion'])
        self.assertEqual([], [a for a in r['jornadas'][0]['avisos'] if a['codigo'] == 'reemplazo'])

    def test_el_registro_sigue_guardando_solo_los_codigos(self):
        self.guardado(NUEVO)
        self.ing(lote([jor(self.DIA, [('Mikel', 8)], VIEJO)]), escribir=True)
        ruta = os.path.join(self.raiz, OBRAS['olabeaga'], 'INFORME SAGARDE IA', 'personal_jornadas.jsonl')
        with open(ruta, encoding='utf-8') as fh:
            ultima = json.loads(fh.read().splitlines()[-1])
        self.assertEqual('reemplazo', ultima['accion'])
        self.assertIn('reemplazo', ultima['avisos'])
        self.assertTrue(all(isinstance(x, str) and '|' not in x for x in ultima['avisos']), ultima['avisos'])


class TestEnElLector(Base):
    DIA = '2026-11-03'

    def previo(self, registrado):
        r = self.ing(lote([jor(self.DIA, [('Mikel', 8), ('Txomin', 7.5)], registrado)]), escribir=True)
        self.assertTrue(r['ok'], r)

    def test_un_fichero_viejo_se_frena_y_dice_que_es_viejo(self):
        self.previo(NUEVO)
        self.fichero(NOM % '02112026', lote([jor(self.DIA, [('Mikel', 8), ('Txomin', 7.5), ('Beto', 8)], VIEJO)]))
        r = self.analizar()
        f = r['ficheros'][0]
        self.assertEqual('a_revisar', f['estado'], 'sigue frenando y preguntando, como siempre')
        motivo = [m for m in f['motivos'] if m['codigo'] == 'reemplazo']
        self.assertEqual(1, len(motivo))
        self.assertIn('MÁS ANTIGUO', motivo[0]['texto'])
        self.assertIn('lun 02/11 a las 09:10', motivo[0]['texto'])
        self.assertIn('mié 04/11 a las 18:40', motivo[0]['texto'])
        self.assertIsNone(PALABRAS.search(motivo[0]['texto']), motivo[0]['texto'])

    def test_sin_aceptar_no_se_aplica_nada(self):
        self.previo(NUEVO)
        self.fichero(NOM % '02112026', lote([jor(self.DIA, [('Beto', 8)], VIEJO)]))
        r = self.aplicar(aceptar=False)
        self.assertEqual([], r['aplicados'], 'nada se aplica solo, ni siquiera siendo viejo')
        self.assertEqual(['Mikel', 'Txomin'], self.gente(), 'lo guardado se queda como estaba')

    def test_un_fichero_nuevo_dice_que_es_nuevo_y_tambien_se_frena(self):
        self.previo(VIEJO)
        self.fichero(NOM % '04112026', lote([jor(self.DIA, [('Mikel', 8)], NUEVO)]))
        f = self.analizar()['ficheros'][0]
        self.assertEqual('a_revisar', f['estado'])
        texto = [m['texto'] for m in f['motivos'] if m['codigo'] == 'reemplazo'][0]
        self.assertIn('más nuevo', texto)

    def test_una_anulacion_vieja_tambien_lo_dice(self):
        self.previo(NUEVO)
        self.fichero(NOM % '02112026', lote([jor(self.DIA, [], VIEJO, anulada=True)]))
        f = self.analizar()['ficheros'][0]
        self.assertEqual('a_revisar', f['estado'])
        texto = [m['texto'] for m in f['motivos'] if m['codigo'] == 'anulacion'][0]
        self.assertIn('Anula una jornada que ya tenía gente apuntada (viviendas del 03/11)', texto)
        self.assertIn('MÁS ANTIGUO', texto)
        self.assertIn('lun 02/11 a las 09:10', texto)
        self.assertIsNone(PALABRAS.search(texto), texto)

    def test_en_un_fichero_con_varias_jornadas_se_toma_la_hora_de_la_que_se_anula(self):
        # La primera jornada del fichero es de OTRO día y MÁS NUEVA que lo guardado; la que anula es de las 09:10 del lunes
        self.previo(NUEVO)
        self.fichero(NOM % '02112026', lote([
            jor('2026-11-02', [('Mikel', 8)], '2026-11-05T10:00:00.000Z'),
            jor(self.DIA, [], VIEJO, anulada=True)]))
        f = self.analizar()['ficheros'][0]
        texto = [m['texto'] for m in f['motivos'] if m['codigo'] == 'anulacion'][0]
        self.assertIn('MÁS ANTIGUO', texto)
        self.assertIn('lun 02/11 a las 09:10', texto)
        self.assertNotIn('11:00', texto, 'no debe usar la hora de la otra jornada del fichero')

    def test_una_anulacion_sin_hora_queda_como_siempre(self):
        self.previo(NUEVO)
        self.fichero(NOM % '02112026', lote([jor(self.DIA, [], anulada=True)]))
        texto = [m['texto'] for m in self.analizar()['ficheros'][0]['motivos'] if m['codigo'] == 'anulacion'][0]
        self.assertEqual('Anula una jornada que ya tenía gente apuntada (viviendas del 03/11).', texto)


def setUpModule():
    global TMP, _TMP_OBJ
    _TMP_OBJ = tempfile.TemporaryDirectory(prefix='aviso_hora_', dir=os.environ.get('P3_TMP') or None)
    TMP = _TMP_OBJ.name


def tearDownModule():
    _TMP_OBJ.cleanup()


if __name__ == '__main__':
    unittest.main()
