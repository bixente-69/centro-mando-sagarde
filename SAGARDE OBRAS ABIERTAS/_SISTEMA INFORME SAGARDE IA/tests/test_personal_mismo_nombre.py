# -*- coding: utf-8 -*-
"""Pruebas de MA4b (diseño de MA4a, §6.1 y §7): dos personas con el mismo nombre NO se funden en silencio en el PC.

Tres avisos nuevos de personal_obra.ingerir_lote (el lector los usa):
  · `empresa_cambiada` (frena el fichero): el fichero cambia la empresa de alguien que ya tenía otra distinta.
  · `alta_de_baja` (frena el fichero): un nombre «nuevo» es el de alguien que estaba de baja.
  · `alta_ya_existia` (solo informa): un nombre «nuevo» ya estaba en la base y se toma como la misma persona.
El resumen del lector distingue «empresa puesta» de «empresa cambiada». Datos INVENTADOS (Rafa, Pepe, Luis; empresas
«Alfa Instalaciones» y «Beta Montajes»). unittest de la biblioteca estándar. `PERSONAL_MOTOR` apunta a otra copia del motor
(para las mutaciones: se rompe una COPIA, nunca el original)."""
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

MOTOR = os.environ.get('PERSONAL_MOTOR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MOTOR)
import lector_control_horario as L
import personal_integracion as PI
import personal_obra as P

TMP = None
_TMP_OBJ = None
OBRAS = {'olabeaga': '2026 OLABEAGA BILBAO', 'mungia': '2026 MUNGIA ACR NEINOR'}
HOY = '2026-10-30'
AHORA = '2026-10-30T20:00:00+01:00'
ALFA = 'Alfa Instalaciones'
BETA = 'Beta Montajes'
PALABRAS = re.compile(r'\b(exportar|exportad\w*|importar|importad\w*|lotes?|ingerir|ingesta|json|pendientes?|alta|altas|'
                      r'simulaci\w+|estado|base de datos)\b', re.I)
FRASE_OTRA_PERSONA = 'Si es otra persona con el mismo nombre, hay que ponerle un apellido o una inicial'


def jor(fecha, presentes, ambito='vivienda'):
    return {'ambito': ambito, 'fecha': fecha, 'presentes': [{'nombre': n, 'horas': h, 'extra': 0} for n, h in presentes]}


def lote(jornadas=(), obra='olabeaga', **kw):
    d = {'tipo': 'lote_personal', 'version': 1, 'obra': obra, 'jornadas': list(jornadas)}
    d.update(kw)
    return d


def emp(nombre, empresa):
    return {'nombre': nombre, 'empresa': empresa}


class Base(unittest.TestCase):
    NOM = 'CONTROL HORARIO 2026 OLABEAGA BILBAO %s.json'

    def setUp(self):
        self.raiz = os.path.join(TMP, uuid.uuid4().hex)
        os.makedirs(self.raiz)

    def tearDown(self):
        shutil.rmtree(self.raiz, ignore_errors=True)

    def ing(self, l, escribir=False, **kw):
        return P.ingerir_lote(copy.deepcopy(l), self.raiz, OBRAS, HOY, escribir=escribir, ahora=AHORA, **kw)

    def sembrar(self, *personas):
        """Deja en la base a las personas (nombre, empresa) con un fichero de altas y empresas aplicado de verdad."""
        l = lote([], altas=[n for n, _ in personas], empresas=[emp(n, e) for n, e in personas if e])
        r = self.ing(l, escribir=True)
        self.assertTrue(r['ok'] and r['escrito'], r)

    def hashes(self):
        """Huella de todo lo que hay en disco MENOS los ficheros que se dejan en REVISIONES para el lector (esos no son datos)."""
        out = {}
        for d, _, fs in os.walk(self.raiz):
            for f in fs:
                ruta = os.path.relpath(os.path.join(d, f), self.raiz).replace(os.sep, '/')
                if '/REVISIONES/' in ruta:
                    continue
                with open(os.path.join(d, f), 'rb') as fh:
                    out[ruta] = hashlib.sha256(fh.read()).hexdigest()
        return out

    def rev(self):
        d = os.path.join(self.raiz, OBRAS['olabeaga'], 'REVISIONES')
        os.makedirs(d, exist_ok=True)
        return d

    def fichero(self, l, fecha='30102026', nombre=None):
        with open(os.path.join(self.rev(), nombre or (self.NOM % fecha)), 'wb') as fh:
            fh.write(json.dumps(l, ensure_ascii=False, indent=1).encode('utf-8'))

    def analizar(self, aceptar=False):
        return L.analizar('olabeaga', L.listar(self.rev()), HOY, self.raiz, OBRAS, aceptar=aceptar, ahora=AHORA)

    def aplicar(self, aceptar=False):
        return L.aplicar('olabeaga', L.listar(self.rev()), HOY, self.raiz, OBRAS, aceptar=aceptar, ahora=AHORA)

    def ficha(self, l, fecha='30102026', nombre=None):
        """Escribe el fichero y devuelve cómo lo ve el lector (el último fichero de la carpeta)."""
        self.fichero(l, fecha, nombre)
        return self.analizar()['ficheros'][-1]

    def cat(self):
        return P.cargar_catalogo(self.raiz)

    def empresas(self):
        return {t['nombre']: t.get('empresa') for t in self.cat()['trabajadores'] if t.get('fusionado_en') is None}

    def codigos(self, ficha):
        return [a['codigo'] for a in ficha['avisos']]

    def codigos_motivos(self, ficha):
        return [m['codigo'] for m in ficha['motivos']]

    def texto_de(self, ficha, codigo):
        return next(a['texto'] for a in ficha['avisos'] if a['codigo'] == codigo)


class TestEmpresaCambiada(Base):
    def test_cambiar_la_empresa_de_alguien_frena_el_fichero_y_no_escribe_nada(self):
        self.sembrar(('Rafa', ALFA))
        f = self.ficha(lote([], empresas=[emp('Rafa', BETA)]))
        self.assertEqual(f['estado'], L.A_REVISAR, f['motivos'])
        self.assertIn('empresa_cambiada', self.codigos(f))
        self.assertIn('empresa_cambiada', self.codigos_motivos(f))
        antes = self.hashes()
        r = self.aplicar()
        self.assertTrue(r['frena'], r)
        self.assertEqual(r['aplicados'], [])
        self.assertEqual(self.empresas()['Rafa'], ALFA, 'sin visto bueno la empresa no se toca')
        self.assertEqual(self.hashes(), antes, 'frenar no escribe ni un byte')

    def test_el_texto_dice_quien_de_que_empresa_a_cual_y_como_se_distingue(self):
        self.sembrar(('Rafa', ALFA))
        f = self.ficha(lote([], empresas=[emp('Rafa', BETA)]))
        t = self.texto_de(f, 'empresa_cambiada')
        self.assertEqual(
            t, '«Rafa» pasa de la empresa «Alfa Instalaciones» a «Beta Montajes»: todas sus horas ya apuntadas se '
               'contarán en «Beta Montajes». ' + FRASE_OTRA_PERSONA + ' en la tablet.')
        self.assertIsNone(PALABRAS.search(t), t)
        self.assertNotIn('_', t)

    def test_con_el_visto_bueno_se_aplica_como_siempre(self):
        self.sembrar(('Rafa', ALFA))
        self.fichero(lote([], empresas=[emp('Rafa', BETA)]))
        r = self.aplicar(aceptar=True)
        self.assertEqual(len(r['aplicados']), 1, r)
        self.assertEqual(self.empresas()['Rafa'], BETA)

    def test_poner_la_primera_empresa_no_frena(self):
        self.sembrar(('Rafa', ''))
        f = self.ficha(lote([], empresas=[emp('Rafa', ALFA)]))
        self.assertEqual(f['estado'], L.LISTO, f['motivos'])
        self.assertNotIn('empresa_cambiada', self.codigos(f))
        self.assertEqual([e['accion'] for e in f['empresas']], ['puesta'])

    def test_quitar_la_empresa_no_frena(self):
        self.sembrar(('Rafa', ALFA))
        f = self.ficha(lote([], empresas=[emp('Rafa', '')]))
        self.assertEqual(f['estado'], L.LISTO, f['motivos'])
        self.assertNotIn('empresa_cambiada', self.codigos(f))
        self.assertEqual([e['accion'] for e in f['empresas']], ['quitada'])

    def test_la_misma_empresa_con_otras_mayusculas_no_es_un_cambio(self):
        self.sembrar(('Rafa', ALFA))
        f = self.ficha(lote([], empresas=[emp('Rafa', 'alfa INSTALACIONES')]))
        self.assertNotIn('empresa_cambiada', self.codigos(f))
        self.assertEqual(f['estado'], L.LISTO)
        self.assertTrue(f['sin_efecto'], 'no trae nada nuevo')

    def test_el_fichero_de_generar_personal_se_frena_igual(self):
        self.sembrar(('Rafa', ALFA))
        f = self.ficha(lote([], obra='sagarde', empresas=[emp('Rafa', BETA)]),
                       nombre='BASE TRABAJADORES SAGARDE 30102026.json')
        self.assertEqual(f['estado'], L.A_REVISAR, f['motivos'])
        self.assertIn('empresa_cambiada', self.codigos(f))

    def test_un_cambio_con_jornada_dentro_tambien_frena_y_el_ranking_no_se_toca(self):
        self.sembrar(('Rafa', ALFA))
        self.fichero(lote([jor('2026-10-26', [('Rafa', 8)])]), '26102026')
        self.assertEqual(len(self.aplicar()['aplicados']), 1)
        antes = self.hashes()
        f = self.ficha(lote([jor('2026-10-27', [('Rafa', 8)])], empresas=[emp('Rafa', BETA)]), '27102026')
        self.assertEqual(f['estado'], L.A_REVISAR, f['motivos'])
        self.aplicar()
        self.assertEqual(self.hashes(), antes, 'frenado: ni la jornada ni la empresa entran')

    def test_nombre_anterior_con_otra_empresa_avisa_las_dos_cosas(self):
        self.sembrar(('Rafa', ALFA))
        self.assertEqual(self.ing(lote([], renombres=[{'de': 'Rafa', 'a': 'Rafael'}]), escribir=True)['renombres'][0]['accion'], 'renombrado')
        f = self.ficha(lote([], empresas=[emp('Rafa', BETA)]))
        self.assertEqual(f['estado'], L.A_REVISAR, f['motivos'])
        self.assertIn('nombre_anterior_usado', self.codigos(f))
        self.assertIn('empresa_cambiada', self.codigos(f))
        self.assertIn('«Rafael» pasa de la empresa', self.texto_de(f, 'empresa_cambiada'))

    def test_dos_tablets_con_el_mismo_nombre_y_empresas_distintas(self):
        l1 = lote([jor('2026-10-26', [('Pepe', 8)])], altas=['Pepe'], empresas=[emp('Pepe', ALFA)])
        self.fichero(l1, '26102026')
        self.assertEqual(len(self.aplicar()['aplicados']), 1)
        antes = self.hashes()
        f = self.ficha(lote([jor('2026-10-27', [('Pepe', 8)])], altas=['Pepe'], empresas=[emp('Pepe', BETA)]), '27102026')
        self.assertEqual(f['estado'], L.A_REVISAR, f['motivos'])
        self.assertIn('alta_ya_existia', self.codigos(f))
        self.assertIn('empresa_cambiada', self.codigos(f))
        self.aplicar()
        self.assertEqual(self.hashes(), antes)
        self.assertEqual(self.empresas()['Pepe'], ALFA)


class TestAltaDeUnNombreQueYaEstaba(Base):
    def test_un_nombre_que_ya_estaba_se_avisa_pero_no_frena(self):
        self.sembrar(('Rafa', ALFA))
        f = self.ficha(lote([jor('2026-10-26', [('Rafa', 8)])], altas=['Rafa']))
        self.assertEqual(f['estado'], L.LISTO, f['motivos'])
        self.assertIn('alta_ya_existia', self.codigos(f))
        self.assertNotIn('alta_ya_existia', self.codigos_motivos(f))
        self.assertEqual(self.texto_de(f, 'alta_ya_existia'),
                         '«Rafa» ya estaba en la base: este fichero lo daba por nuevo y se ha tomado como la misma persona.')
        r = self.ing(lote([jor('2026-10-26', [('Rafa', 8)])], altas=['Rafa']))
        self.assertEqual(r['altas_pedidas'], [{'nombre': 'Rafa', 'id': 'T0001', 'accion': 'sin_cambios'}])
        self.assertEqual(r['altas'], [])

    def test_con_espacios_y_mayusculas_distintas_es_el_mismo_nombre(self):
        self.sembrar(('Rafa', ALFA))
        for escrito in ('  rafa ', 'RAFA', 'Rafa  '):
            r = self.ing(lote([], altas=[escrito]))
            self.assertIn('alta_ya_existia', [a['codigo'] for a in r['avisos_lote']], escrito)
            self.assertEqual(r['altas_pedidas'][0]['accion'], 'sin_cambios', escrito)

    def test_dos_tablets_sin_empresa_es_una_sola_persona_y_solo_informa(self):
        self.sembrar(('Pepe', ''))
        f = self.ficha(lote([jor('2026-10-27', [('Pepe', 8)])], altas=['Pepe']))
        self.assertEqual(f['estado'], L.LISTO, f['motivos'])
        self.assertIn('alta_ya_existia', self.codigos(f))
        self.assertEqual(len(self.cat()['trabajadores']), 1)

    def test_la_misma_tablet_reenvia_las_mismas_altas_y_no_se_frena(self):
        self.sembrar(('Pepe', ALFA))
        f = self.ficha(lote([jor('2026-10-27', [('Pepe', 8)])], altas=['Pepe'], empresas=[emp('Pepe', ALFA)]))
        self.assertEqual(f['estado'], L.LISTO, f['motivos'])
        self.assertEqual([c for c in self.codigos(f) if c.startswith(('alta_', 'empresa_'))], ['alta_ya_existia'])

    def test_un_nombre_nuevo_de_verdad_sigue_igual(self):
        f = self.ficha(lote([jor('2026-10-27', [('Luis', 8)])], altas=['Luis']))
        self.assertEqual(f['estado'], L.LISTO)
        self.assertEqual(self.codigos(f), ['alta_nueva'])

    def test_alguien_de_baja_frena_y_con_el_visto_bueno_vuelve(self):
        self.sembrar(('Rafa', ALFA))
        c = self.cat()
        c['trabajadores'][0]['activo'] = False
        P.guardar_catalogo(self.raiz, c)
        f = self.ficha(lote([jor('2026-10-26', [('Rafa', 8)])], altas=['Rafa']))
        self.assertEqual(f['estado'], L.A_REVISAR, f['motivos'])
        self.assertIn('alta_de_baja', self.codigos_motivos(f))
        self.assertNotIn('alta_ya_existia', self.codigos(f), 'una baja no es «ya estaba»')
        self.assertEqual(
            self.texto_de(f, 'alta_de_baja'),
            '«Rafa» estaba de baja y este fichero lo da por nuevo: vuelve a la lista. ' + FRASE_OTRA_PERSONA + '.')
        antes = self.hashes()
        self.aplicar()
        self.assertEqual(self.hashes(), antes, 'frenado: sigue de baja')
        self.assertFalse(self.cat()['trabajadores'][0]['activo'])
        self.aplicar(aceptar=True)
        self.assertTrue(self.cat()['trabajadores'][0]['activo'])

    def test_alguien_de_baja_por_un_nombre_anterior_tambien_frena(self):
        self.sembrar(('Rafa', ALFA))
        self.ing(lote([], renombres=[{'de': 'Rafa', 'a': 'Rafael'}]), escribir=True)
        c = self.cat()
        c['trabajadores'][0]['activo'] = False
        P.guardar_catalogo(self.raiz, c)
        f = self.ficha(lote([], altas=['Rafa']))
        self.assertEqual(f['estado'], L.A_REVISAR, f['motivos'])
        self.assertIn('alta_de_baja', self.codigos_motivos(f))
        self.assertIn('nombre_anterior_usado', self.codigos(f))
        self.assertTrue(self.texto_de(f, 'alta_de_baja').startswith('«Rafael» estaba de baja'), 'con el nombre vigente')

    def test_por_un_nombre_anterior_solo_sale_el_aviso_del_nombre_anterior(self):
        self.sembrar(('Rafa', ALFA))
        self.ing(lote([], renombres=[{'de': 'Rafa', 'a': 'Rafael'}]), escribir=True)
        f = self.ficha(lote([], altas=['Rafa']))
        self.assertIn('nombre_anterior_usado', self.codigos(f))
        self.assertNotIn('alta_ya_existia', self.codigos(f))

    def test_el_mismo_fichero_dos_veces_no_vuelve_a_avisar(self):
        self.sembrar(('Rafa', ALFA))
        self.fichero(lote([jor('2026-10-26', [('Rafa', 8)])], altas=['Rafa']))
        self.assertEqual(len(self.aplicar()['aplicados']), 1)
        otra = self.analizar()['ficheros'][0]
        self.assertEqual(otra['estado'], L.YA_APLICADO)
        self.assertEqual(self.codigos(otra), [])


class TestLoQueNoCambia(Base):
    def test_renombrar_a_un_nombre_que_existe_sigue_frenando_con_la_orden_de_juntar(self):
        self.sembrar(('Rafa', ALFA), ('Pepe', BETA))
        f = self.ficha(lote([], renombres=[{'de': 'Pepe', 'a': 'Rafa'}]))
        self.assertEqual(f['estado'], L.A_REVISAR)
        self.assertIn('renombre_coincide_con_otro', self.codigos_motivos(f))
        self.assertEqual(f['renombres'][0]['orden'], 'personal_obra.py fusionar T0002 T0001')

    def test_un_catalogo_con_dos_nombres_iguales_sigue_marcado_como_error(self):
        self.sembrar(('Rafa', ALFA), ('Luis', BETA))
        c = self.cat()
        c['trabajadores'][1]['nombre'] = 'Rafa'
        P.guardar_catalogo(self.raiz, c)
        self.assertTrue([x for x in P.comprobar(self.raiz, OBRAS) if 'nombres no fusionados duplicados' in x])

    def test_una_persona_dos_veces_el_mismo_dia_sigue_rechazada_y_el_resto_se_aplica(self):
        self.sembrar(('Ander', ''))
        f = self.ficha(lote([jor('2026-10-26', [('Rafa', 8), ('Rafa', 8)])], empresas=[emp('Ander', ALFA)]))
        self.assertEqual(f['estado'], L.LISTO, f['motivos'])
        self.assertEqual(f['rechazadas'], 1)
        self.assertEqual([m['texto'] for m in f['jornadas'][0]['rechazos']], ['Una persona sale dos veces el mismo día.'])

    def test_un_fichero_corriente_sale_sin_ningun_aviso_nuevo(self):
        self.sembrar(('Rafa', ALFA), ('Pepe', BETA))
        f = self.ficha(lote([jor('2026-10-26', [('Rafa', 8), ('Pepe', 8)])], empresas=[emp('Rafa', ALFA), emp('Pepe', BETA)]))
        self.assertEqual((f['estado'], self.codigos(f)), (L.LISTO, []))
        self.assertEqual(f['resumen'], '1 jornada de viviendas')


class TestResumenYTextos(Base):
    def test_el_resumen_distingue_puesta_cambiada_y_quitada(self):
        self.sembrar(('Rafa', ALFA), ('Pepe', BETA), ('Luis', ''))
        f = self.ficha(lote([], empresas=[emp('Rafa', BETA), emp('Pepe', ''), emp('Luis', ALFA)]))
        self.assertEqual(f['resumen'], '1 empresa puesta, 1 empresa cambiada, 1 empresa quitada')

    def test_dos_cambiadas_van_en_plural_y_sin_la_palabra_puesta(self):
        self.sembrar(('Rafa', ALFA), ('Pepe', BETA))
        f = self.ficha(lote([], empresas=[emp('Rafa', BETA), emp('Pepe', ALFA)]))
        self.assertEqual(f['resumen'], '2 empresas cambiadas')

    def test_el_auditor_enseña_el_motivo_y_la_linea_del_cambio_sin_palabras_de_programador(self):
        self.sembrar(('Rafa', ALFA))
        f = self.ficha(lote([], empresas=[emp('Rafa', BETA)]))
        lineas = PI._lineas_ficha(f)
        self.assertIn('HAY QUE MIRARLO, no se aplica', lineas[0])
        self.assertIn('      · Cambia la empresa de «Rafa»: de «Alfa Instalaciones» a «Beta Montajes».', lineas)
        self.assertTrue([x for x in lineas if x.startswith('      ! ') and 'pasa de la empresa' in x], lineas)
        for linea in lineas[1:]:
            self.assertIsNone(PALABRAS.search(linea), linea)

    def test_el_auditor_enseña_lo_que_solo_informa(self):
        self.sembrar(('Rafa', ALFA))
        f = self.ficha(lote([jor('2026-10-26', [('Rafa', 8)])], altas=['Rafa']))
        lineas = PI._lineas_ficha(f)
        self.assertTrue([x for x in lineas if x.startswith('      · ') and 'ya estaba en la base' in x], lineas)

    def test_las_frases_aguantan_cualquier_detalle_y_no_llevan_palabras_de_programador(self):
        for codigo in ('empresa_cambiada', 'alta_ya_existia', 'alta_de_baja'):
            for detalle in (None, '', 'Ana', 'Ana | X', 'Ana | X | Y', 'a | b | c | d', 7):
                t = P.texto_aviso(codigo, detalle)
                self.assertTrue(t and not t.startswith('Aviso:'), (codigo, detalle, t))
                self.assertIsNone(PALABRAS.search(t), t)
                self.assertNotIn('_', t)
        self.assertEqual(P.texto_aviso('empresa_cambiada', 'Rafa | A | B'),
                         '«Rafa» pasa de la empresa «A» a «B»: todas sus horas ya apuntadas se contarán en «B». '
                         + FRASE_OTRA_PERSONA + ' en la tablet.')

    def test_el_detalle_lleva_nombre_antes_y_despues(self):
        self.sembrar(('Rafa', ALFA))
        r = self.ing(lote([], empresas=[emp('Rafa', BETA)]))
        self.assertEqual([a for a in r['avisos_lote'] if a['codigo'] == 'empresa_cambiada'],
                         [{'codigo': 'empresa_cambiada', 'detalle': 'Rafa | Alfa Instalaciones | Beta Montajes'}])

    def test_los_codigos_nuevos_frenan_o_no_segun_el_diseno(self):
        self.assertIn('empresa_cambiada', L.AVISOS_A_REVISAR)
        self.assertIn('alta_de_baja', L.AVISOS_A_REVISAR)
        self.assertNotIn('alta_ya_existia', L.AVISOS_A_REVISAR)


def setUpModule():
    global TMP, _TMP_OBJ
    _TMP_OBJ = tempfile.TemporaryDirectory(prefix='mismo_nombre_', dir=os.environ.get('P3_TMP') or None)
    TMP = _TMP_OBJ.name


def tearDownModule():
    _TMP_OBJ.cleanup()


if __name__ == '__main__':
    unittest.main()
