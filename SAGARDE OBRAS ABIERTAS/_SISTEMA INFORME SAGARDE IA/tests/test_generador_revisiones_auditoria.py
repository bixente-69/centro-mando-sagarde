# -*- coding: utf-8 -*-
"""Auditoria del generador de revisiones (04/11/2026): cuatro fallos silenciosos, cada uno con su prueba.

Se ejecuta el HTML REAL en Chromium con datos inventados. Copiar la logica a Python la dejaria
divergir del navegador en silencio, que es justo la familia de fallos de este proyecto.

Los cuatro fallos (reproducidos antes de corregirlos):

* H1  La hoja recupera las marcas guardadas con un `querySelector` armado a mano. Una vivienda con
      comillas en el nombre lo rompe, el `try/catch` vacio se lo traga y se pierden TODAS las marcas
      que venian despues de esa. Ademas, una marca guardada que no encuentra celda se descartaba sin
      decir nada. Medido: 5 marcas guardadas, 1 recuperada.
* H2  `setViv` dejaba renombrar una vivienda con un nombre ya usado en la misma planta: dos columnas
      con la misma clave `data-k` (37 claves repetidas en una hoja de prueba). `addViv` ya lo evitaba.
* H3  «Recientes» pintaba `onclick="loadConfig('<clave>')"` sin escapar: una obra con apostrofo
      (D'ARCY) no se podia volver a abrir (SyntaxError al pulsar) y el nombre se interpretaba como HTML.
* H4  La fecha por defecto salia de `toISOString()` (UTC): a las 00:30 locales de Madrid daba el dia
      de ayer, y con la pestana abierta de un dia para otro «Nueva revision» seguia con la fecha vieja.

* H7  (garaje) `addZona` e `incGarageCount` ponian nombre contando las zonas que habia y sumando uno: al
      quitar una del medio salian nombres repetidos en la misma planta (Trasteros 3 x2, Zona C x2,
      Basuras 2 x2) y en la hoja impresa dos columnas con el mismo rotulo.

* H8  Con el aparato lleno el autoguardado de la hoja fallaba en silencio (`catch(e){}`): la celda se marcaba en
      pantalla y no se guardaba nada, justo la red de seguridad de campo (tablet en la mano, 23 plantas). Medido:
      una hoja de Bolueta con todo marcado ocupa 223.690 caracteres y caben unas 23 en los ~5,2 millones del
      aparato; ademas `saveConfig` dejaba huerfanas las configuraciones que salen de «Recientes» y tampoco
      avisaba si fallaba.

* H9  DECISION de Bixente (04/11/2026, opcion B): cuando el aparato se llena, se borran SOLO las copias automaticas
      de hojas de mas de 30 dias, la mas vieja primero y solo las necesarias, y se avisa. Nunca la clave que se
      esta escribiendo, ni configuraciones, ni la lista de recientes, ni nada de otra aplicacion.

* H10 El contador del paso 3 («N tajos · H hojas por tabla») calculaba las hojas con TODOS los tajos, incluidos los de
      zonas especiales que no entran en la matriz de viviendas. Con datos reales (Bolueta, Olabeaga, Mungia,
      Gernika) decia «2 hojas por tabla» en aviso de desbordamiento y el paso 4 y la impresion daban 1.
* H11 El resumen del paso 4 decia «N de zonas especiales» contando todo lo seleccionado, aunque el portal no tuviera
      ninguna zona (35 de 35 sin imprimir) o solo un cuarto ligero (imprime 12).
* H12 La lista de tajos del paso 3 no escapaba el nombre del tajo ni el de la fase (la de garaje si): inyectaba HTML.
* H7b Las zonas especiales de vivienda tenian el mismo fallo de nombres repetidos que las de garaje.

Sin Playwright o sin Chromium las pruebas se saltan (no fallan): Bixente lo lanza todo con .bat.
"""
import json
import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from ayudante_generar import hay_chromium

SISTEMA = Path(__file__).resolve().parent.parent
GENERADOR = Path(os.environ.get("P3_GENERADOR") or (SISTEMA / "generador_revisiones.html"))
TMP_BASE = Path(os.environ.get("P3_TMP") or tempfile.gettempdir())

# Estructura inventada: un portal con dos plantas iguales. Devuelve el HTML de la hoja de vivienda.
HOJA_JS = """(vivs) => {
  S.obra='OBRA T'; S.fecha='2026-11-04';
  S.bloques=normaliseStructure({bloques:[{nombre:'B1',portales:[{nombre:'P1',
    plantas:[{nombre:'1',vivs:vivs},{nombre:'2',vivs:vivs}]}]}]});
  S.sel=new Set(CAT.map(t=>t.id));
  return generateHTML({});
}"""

# Igual, pero con identificadores FIJOS de bloque, portal y planta, como los que trae una obra de la base (ficha).
# Sin ids, cada generacion inventa unos nuevos (uid) y las claves de las celdas ya no casan entre una hoja y otra.
HOJA_ESTABLE_JS = """(vivs) => {
  S.obra='OBRA T'; S.fecha='2026-11-04';
  S.bloques=normaliseStructure({bloques:[{id:'b1',nombre:'B1',portales:[{id:'p1',nombre:'P1',
    plantas:[{id:'f1',nombre:'1',vivs:vivs},{id:'f2',nombre:'2',vivs:vivs}]}]}]});
  S.sel=new Set(CAT.map(t=>t.id));
  return generateHTML({});
}"""

# Pulsa (cambia de estado) la primera o segunda celda de las viviendas pedidas, por orden de aparicion.
MARCAR_JS = """(pares) => {
  const cs=[...document.querySelectorAll('.td-st[data-k]')];
  pares.forEach(([viv,n])=>cs.filter(c=>c.dataset.k.endsWith('__'+viv))[n].click());
}"""

# Llena el almacenamiento del aparato hasta el ultimo caracter. `grande` es el prefijo de los trozos de 100.000
# caracteres (`sufijo` va al final del nombre) y `chico` el de los trozos pequenos que rematan hasta el ultimo.
def llenar_js(grande="relleno_g", chico="relleno_c", sufijo=""):
    return """() => {
  const trozo='x'.repeat(100000); let n=0;
  try{ for(;;){ localStorage.setItem('%s'+(n++)+'%s', trozo); } }catch(e){}
  for(const tam of [10000,1000,100,10,1]){ let m=0;
    try{ for(;;){ localStorage.setItem('%s'+tam+'_'+(m++), 'x'.repeat(tam)); } }catch(e){} }
}""" % (grande, sufijo, chico)


# Aparato lleno de cosas que NO se pueden borrar: el aviso de «no se esta guardando» tiene que salir.
LLENAR_JS = llenar_js()
# Aparato lleno de copias automaticas de hojas MUY viejas (se pueden borrar) y relleno que no.
LLENAR_VIEJAS_JS = llenar_js("sgd_rev_VIEJA", "relleno_c", "_2025-01-01")

AVISOS_JS = "[...document.querySelectorAll('.sheet-toast')].map(d=>d.textContent)"

MARCADAS_JS = "[...document.querySelectorAll('.td-st[data-k]')].filter(c=>c.dataset.st).length"

# ¿Hay un aviso en pantalla que cuente cuantas marcas no se pudieron colocar?
AVISO_JS = """(re) => [...document.querySelectorAll('body > div')]
  .some(d => new RegExp(re).test(d.textContent))"""


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ok, motivo = hay_chromium()
        if not ok:
            raise unittest.SkipTest(motivo)
        from playwright.sync_api import sync_playwright
        cls._pw = sync_playwright().start()
        cls.navegador = cls._pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.navegador.close()
        finally:
            cls._pw.stop()

    def contexto(self, **kw):
        kw.setdefault("timezone_id", "Europe/Madrid")
        kw.setdefault("locale", "es-ES")
        ctx = self.navegador.new_context(**kw)
        self.addCleanup(ctx.close)
        return ctx

    def generador(self, ctx=None, antes=None):
        """Abre el generador real. Devuelve (pagina, errores de JavaScript)."""
        ctx = ctx or self.contexto()
        pg = ctx.new_page()
        pg.set_default_timeout(5000)
        errores = []
        pg.on("pageerror", lambda e: errores.append(str(e)))
        if antes:
            antes(pg)
        pg.goto(GENERADOR.resolve().as_uri())
        return pg, errores

    def hoja(self, pg, vivs, js=HOJA_JS):
        """Genera la hoja con esas viviendas, la guarda en una carpeta temporal y la abre en una pagina nueva."""
        html = pg.evaluate(js, vivs)
        carpeta = TMP_BASE / ("gen_aud_" + uuid.uuid4().hex[:8])
        carpeta.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(carpeta), True)
        f = carpeta / "hoja.html"
        f.write_text(html, encoding="utf-8")
        h = pg.context.new_page()
        h.set_default_timeout(5000)
        h.goto(f.as_uri())
        return h


class TestH1RecuperarMarcas(Base):
    def test_recupera_todas_las_marcas_aunque_una_vivienda_lleve_comillas(self):
        pg, _ = self.generador()
        h = self.hoja(pg, ['A', 'B"C', 'D'])
        h.evaluate(MARCAR_JS, [['A', 0], ['B"C', 0], ['D', 0], ['A', 1], ['D', 1]])
        guardadas = h.evaluate("Object.keys(JSON.parse(localStorage.getItem(KEY)||'{}')).length")
        self.assertEqual(guardadas, 5)
        h.reload()
        self.assertEqual(h.evaluate(MARCADAS_JS), 5,
                         "las marcas que venian despues de la vivienda con comillas se perdian en silencio")

    def test_la_marca_de_la_vivienda_con_comillas_vuelve_a_su_celda(self):
        pg, _ = self.generador()
        h = self.hoja(pg, ['A', 'B"C'])
        h.evaluate(MARCAR_JS, [['B"C', 0]])
        h.reload()
        estado = h.evaluate("""() => { const c=[...document.querySelectorAll('.td-st[data-k]')]
            .filter(c=>c.dataset.k.endsWith('__B"C'))[0]; return c.dataset.st + '|' + c.textContent; }""")
        self.assertEqual(estado, "/|/")

    def test_avisa_de_la_marca_guardada_que_ya_no_tiene_celda(self):
        pg, _ = self.generador()
        h = self.hoja(pg, ['A', 'B'])
        h.evaluate(MARCAR_JS, [['A', 0]])
        h.evaluate("""() => { const d=JSON.parse(localStorage.getItem(KEY)||'{}');
            d['p_x__f_x__tabicado__ZZ']='X'; localStorage.setItem(KEY, JSON.stringify(d)); }""")
        h.reload()
        self.assertEqual(h.evaluate(MARCADAS_JS), 1, "la marca que si encaja debe recuperarse igualmente")
        h.wait_for_function(AVISO_JS, arg=r"1 marca guardada.*no se ha recuperado", timeout=3000)

    def test_el_aviso_dura_lo_bastante_para_leerse(self):
        """Los avisos normales de la hoja duran 1,6 s; este habla de datos que no se han recuperado."""
        pg, _ = self.generador()
        h = self.hoja(pg, ['A'])
        h.evaluate("""() => { localStorage.setItem(KEY, JSON.stringify({'p_x__f_x__tabicado__ZZ':'X'})); }""")
        h.reload()
        h.wait_for_function(AVISO_JS, arg=r"no se ha recuperado", timeout=3000)
        h.wait_for_timeout(2500)
        self.assertTrue(h.evaluate(AVISO_JS, r"no se ha recuperado"),
                        "el aviso se apago antes de poder leerlo")

    def test_el_aviso_cuenta_en_plural(self):
        pg, _ = self.generador()
        h = self.hoja(pg, ['A'])
        h.evaluate("""() => { localStorage.setItem(KEY, JSON.stringify(
            {'p_x__f_x__tabicado__ZZ':'X','p_x__f_x__rozas__YY':'M'})); }""")
        h.reload()
        h.wait_for_function(AVISO_JS, arg=r"2 marcas guardadas.*no se han recuperado", timeout=3000)

    def test_no_avisa_si_todas_las_marcas_encajan(self):
        pg, _ = self.generador()
        h = self.hoja(pg, ['A', 'B'])
        h.evaluate(MARCAR_JS, [['A', 0], ['B', 1]])
        h.reload()
        h.wait_for_timeout(400)
        self.assertEqual(h.evaluate(MARCADAS_JS), 2)
        self.assertFalse(h.evaluate(AVISO_JS, r"no se (ha|han) recuperado"))

    def test_decision_de_bixente_las_marcas_guardadas_vuelven_aunque_la_hoja_sea_nueva(self):
        """DECIDIDO el 04/11/2026 (Bixente, trabajo de campo): NO se toca.

        En un edificio de 23 plantas con la tablet en la mano es facil que se resbale y se salga de la pantalla,
        o que se apague: las marcas guardadas en el aparato para esa obra y fecha vuelven al reabrir, incluso
        en una hoja recien generada y en blanco, y las copias de seguridad «(2)», «(3)» son a proposito.
        Esta prueba impide que alguien lo «arregle» creyendo que es un fallo."""
        pg, _ = self.generador()
        a = self.hoja(pg, ['A', 'B'], HOJA_ESTABLE_JS)
        a.evaluate(MARCAR_JS, [['A', 0], ['B', 1]])
        b = self.hoja(pg, ['A', 'B'], HOJA_ESTABLE_JS)   # hoja nueva, en blanco, misma obra y misma fecha
        self.assertEqual(b.evaluate(MARCADAS_JS), 2,
                         "las marcas de campo guardadas en el aparato deben volver (decision de Bixente)")

    def test_con_estructura_nueva_sin_ids_las_marcas_viejas_no_casan_y_se_avisa(self):
        """El otro lado: una obra montada a mano inventa ids nuevos en cada generacion, asi que las marcas viejas
        NO encajan. Antes se descartaban sin decir nada; ahora se cuentan y se avisa."""
        pg, _ = self.generador()
        a = self.hoja(pg, ['A', 'B'])
        a.evaluate(MARCAR_JS, [['A', 0], ['B', 1]])
        b = self.hoja(pg, ['A', 'B'])
        self.assertEqual(b.evaluate(MARCADAS_JS), 0)
        b.wait_for_function(AVISO_JS, arg=r"2 marcas guardadas.*no se han recuperado", timeout=3000)

    def test_el_aviso_no_sale_en_el_pdf(self):
        pg, _ = self.generador()
        h = self.hoja(pg, ['A'])
        h.evaluate("""() => { localStorage.setItem(KEY, JSON.stringify({'p_x__f_x__tabicado__ZZ':'X'})); }""")
        h.reload()
        h.wait_for_function(AVISO_JS, arg=r"no se ha recuperado", timeout=3000)
        h.emulate_media(media="print")
        visible = h.evaluate("""() => [...document.querySelectorAll('body > div')]
            .filter(d => /no se ha recuperado/.test(d.textContent))
            .some(d => getComputedStyle(d).display !== 'none')""")
        self.assertFalse(visible, "el aviso saldria impreso en cada pagina del PDF")

    def test_un_almacenamiento_corrupto_no_tumba_la_hoja_y_se_dice(self):
        pg, errores = self.generador()
        h = self.hoja(pg, ['A'])
        h.evaluate("() => localStorage.setItem(KEY, '{esto no es json')")
        h.reload()
        self.assertEqual(h.evaluate("document.querySelectorAll('.td-st[data-k]').length > 0"), True)
        h.wait_for_function(AVISO_JS, arg=r"No se pudieron recuperar", timeout=3000)


class TestH2ViviendasRepetidas(Base):
    PREPARAR = """() => { S.bloques=normaliseStructure({bloques:[{nombre:'B1',portales:[{nombre:'P1',
        plantas:[{nombre:'1',vivs:['A','B','C']}]}]}]}); }"""

    def test_no_se_acepta_renombrar_a_un_nombre_ya_usado(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        pg.evaluate("setViv(0,0,0,1,'A')")
        self.assertEqual(pg.evaluate("S.bloques[0].portales[0].plantas[0].vivs"), ['A', 'B', 'C'])

    def test_la_comparacion_no_distingue_mayusculas(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        pg.evaluate("setViv(0,0,0,2,'a')")
        self.assertEqual(pg.evaluate("S.bloques[0].portales[0].plantas[0].vivs"), ['A', 'B', 'C'])

    def test_renombrar_a_un_nombre_libre_sigue_funcionando(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        pg.evaluate("setViv(0,0,0,1,'  Atico ')")
        self.assertEqual(pg.evaluate("S.bloques[0].portales[0].plantas[0].vivs"), ['A', 'Atico', 'C'])

    def test_conservar_el_propio_nombre_no_cuenta_como_repetido(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        pg.evaluate("setViv(0,0,0,1,'B')")
        self.assertEqual(pg.evaluate("S.bloques[0].portales[0].plantas[0].vivs"), ['A', 'B', 'C'])
        # El estado final es el mismo con o sin el fallo: lo que cambia es el aviso falso de «ya hay una vivienda B».
        self.assertFalse(pg.evaluate(AVISO_JS, r"Ya hay una vivienda"))
        pg.evaluate("setViv(0,0,0,1,'  B  ')")
        self.assertFalse(pg.evaluate(AVISO_JS, r"Ya hay una vivienda"))

    def test_dejar_el_nombre_en_blanco_conserva_el_de_antes_y_la_caja_lo_muestra(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        pg.evaluate("renderPortalStructures()")
        pg.evaluate("""() => { const i=document.querySelectorAll('.floor-viv-row input')[1];
            i.value='   '; i.dispatchEvent(new Event('change')); }""")
        self.assertEqual(pg.evaluate("S.bloques[0].portales[0].plantas[0].vivs"), ['A', 'B', 'C'])
        valores = pg.evaluate("[...document.querySelectorAll('.floor-viv-row input')].map(i=>i.value)")
        self.assertEqual(valores, ['A', 'B', 'C'], "la caja se quedaba en blanco aunque el dato seguia siendo B")

    def test_misma_vivienda_en_otra_planta_si_vale(self):
        pg, _ = self.generador()
        pg.evaluate("""() => { S.bloques=normaliseStructure({bloques:[{nombre:'B1',portales:[{nombre:'P1',
            plantas:[{nombre:'1',vivs:['A','B']},{nombre:'2',vivs:['C','D']}]}]}]}); }""")
        pg.evaluate("setViv(0,0,1,0,'A')")
        self.assertEqual(pg.evaluate("S.bloques[0].portales[0].plantas[1].vivs"), ['A', 'D'])

    def test_la_pantalla_vuelve_al_nombre_anterior_y_lo_dice(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        pg.evaluate("renderPortalStructures()")
        pg.evaluate("""() => { const i=document.querySelectorAll('.floor-viv-row input')[1];
            i.value='A'; i.dispatchEvent(new Event('change')); }""")
        valores = pg.evaluate("[...document.querySelectorAll('.floor-viv-row input')].map(i=>i.value)")
        self.assertEqual(valores, ['A', 'B', 'C'], "la caja no puede quedarse enseñando un nombre que no se guardo")
        self.assertTrue(pg.evaluate(AVISO_JS, r"Ya hay una vivienda .A. en esta planta"))

    def test_la_hoja_generada_no_repite_claves(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        pg.evaluate("setViv(0,0,0,1,'A')")
        claves = pg.evaluate("""() => [...generateHTML({}).matchAll(/data-k="([^"]+)"/g)].map(m=>m[1])""")
        self.assertGreater(len(claves), 0)
        self.assertEqual(len(claves), len(set(claves)))


class TestH3Recientes(Base):
    GUARDAR = """(obra) => { S.obra=obra; S.fecha='2026-11-04';
        S.bloques=normaliseStructure({bloques:[{nombre:'B1',portales:[{nombre:'P1',plantas:[{nombre:'1',vivs:['A']}]}]}]});
        saveConfig(); S.obra='OTRA'; renderRecent(); }"""

    def test_se_puede_reabrir_una_obra_con_apostrofo(self):
        pg, errores = self.generador()
        pg.evaluate(self.GUARDAR, "D'ARCY")
        pg.click(".recent-item")
        self.assertEqual(pg.evaluate("S.obra"), "D'ARCY")
        self.assertEqual(errores, [])

    def test_el_nombre_no_se_interpreta_como_html(self):
        pg, errores = self.generador()
        pg.evaluate(self.GUARDAR, '<i id="intruso">X</i>')
        self.assertEqual(pg.evaluate("document.getElementById('intruso')"), None)
        self.assertIn('<i id="intruso">X</i>', pg.inner_text(".ri-name"))
        pg.click(".recent-item")
        self.assertEqual(pg.evaluate("S.obra"), '<i id="intruso">X</i>')
        self.assertEqual(errores, [])

    def test_se_puede_borrar_una_obra_con_apostrofo(self):
        pg, errores = self.generador()
        pg.evaluate(self.GUARDAR, "D'ARCY")
        pg.click(".ri-del")
        self.assertEqual(pg.evaluate("JSON.parse(localStorage.getItem('sgd_rev_recents')||'[]').length"), 0)
        # Sin recientes el bloque entero se oculta: lo que importa es lo que ve la persona.
        self.assertEqual(pg.evaluate("getComputedStyle(document.getElementById('recent-wrap')).display"), "none")
        self.assertEqual(errores, [])

    def test_borrar_no_abre_la_obra(self):
        pg, errores = self.generador()
        pg.evaluate(self.GUARDAR, "OBRA UNO")
        pg.click(".ri-del")
        self.assertEqual(pg.evaluate("S.obra"), "OTRA", "borrar no puede cargar la obra que se borra")

    def test_una_obra_normal_sigue_abriendose(self):
        pg, errores = self.generador()
        pg.evaluate(self.GUARDAR, "2026 OLABEAGA BILBAO")
        pg.click(".recent-item")
        self.assertEqual(pg.evaluate("S.obra"), "2026 OLABEAGA BILBAO")
        self.assertEqual(errores, [])

    def test_con_varias_obras_abre_la_pulsada(self):
        pg, errores = self.generador()
        pg.evaluate(self.GUARDAR, "OBRA UNO")
        pg.evaluate(self.GUARDAR, "D'ARCY")
        self.assertEqual(pg.evaluate("document.querySelectorAll('.recent-item').length"), 2)
        pg.locator(".recent-item").nth(1).click()
        self.assertEqual(pg.evaluate("S.obra"), "OBRA UNO")


class TestH4FechaLocal(Base):
    def _con_reloj(self, instante, tz="Europe/Madrid"):
        ctx = self.contexto(timezone_id=tz)
        return self.generador(ctx, antes=lambda pg: pg.clock.set_fixed_time(instante))

    def test_pasada_la_medianoche_en_invierno_es_el_dia_local(self):
        # 00:30 en Madrid (UTC+1) = 23:30 UTC del dia anterior
        pg, _ = self._con_reloj("2026-11-05T00:30:00+01:00")
        self.assertEqual(pg.evaluate("S.fecha"), "2026-11-05")

    def test_pasada_la_medianoche_en_verano_es_el_dia_local(self):
        # 00:30 en Madrid (UTC+2) = 22:30 UTC del dia anterior
        pg, _ = self._con_reloj("2026-07-05T00:30:00+02:00")
        self.assertEqual(pg.evaluate("S.fecha"), "2026-07-05")

    def test_a_las_23_30_sigue_siendo_el_mismo_dia(self):
        pg, _ = self._con_reloj("2026-11-04T23:30:00+01:00")
        self.assertEqual(pg.evaluate("S.fecha"), "2026-11-04")

    def test_el_nombre_del_fichero_lleva_la_fecha_local(self):
        pg, _ = self._con_reloj("2026-11-05T00:30:00+01:00")
        self.assertEqual(pg.evaluate("revisionFileBase('Obra T', S.fecha)"), "REVISION OBRA T 05112026")

    def test_sin_fecha_el_nombre_usa_la_fecha_local_de_ahora(self):
        pg, _ = self._con_reloj("2026-11-05T00:30:00+01:00")
        self.assertEqual(pg.evaluate("revisionDateToken('')"), "05112026")

    def test_una_fecha_ilegible_cae_en_la_fecha_local_de_ahora(self):
        pg, _ = self._con_reloj("2026-11-05T00:30:00+01:00")
        self.assertEqual(pg.evaluate("revisionDateToken('esto no es una fecha')"), "05112026")
        self.assertEqual(pg.evaluate("revisionDateToken('2026-11-04')"), "04112026", "una fecha buena no se toca")

    def test_con_la_pestana_abierta_de_un_dia_para_otro_nueva_revision_usa_hoy(self):
        pg, _ = self._con_reloj("2026-11-04T10:00:00+01:00")
        self.assertEqual(pg.evaluate("S.fecha"), "2026-11-04")
        pg.clock.set_fixed_time("2026-11-05T09:00:00+01:00")
        pg.evaluate("startWizard()")
        self.assertEqual(pg.evaluate("S.fecha"), "2026-11-05")
        self.assertEqual(pg.evaluate("document.getElementById('f-fecha').value"), "2026-11-05")

    def test_continuar_una_revision_guardada_conserva_su_fecha(self):
        pg, _ = self._con_reloj("2026-11-04T10:00:00+01:00")
        pg.evaluate("""() => { S.obra='OBRA T'; S.fecha='2026-11-04'; saveConfig(); }""")
        pg.clock.set_fixed_time("2026-11-05T09:00:00+01:00")
        pg.evaluate("renderRecent()")
        pg.click(".recent-item")
        self.assertEqual(pg.evaluate("S.fecha"), "2026-11-04")


class TestH5Descarga(Base):
    """Endurecimiento, NO fallo reproducido: en Chromium la descarga funciona aunque se libere la URL al instante.
    Se fija el mismo gesto que ya usa doSave() de la hoja (enlace dentro del documento y URL liberada un segundo despues)
    porque Safari/iPad y Firefox pueden anular la descarga. La tablet real sigue sin probarse."""

    def test_la_url_del_blob_no_se_libera_en_el_mismo_instante_del_clic(self):
        pg, _ = self.generador()
        pg.on("dialog", lambda d: d.dismiss())
        pg.evaluate("""() => {
          window.__rev=[]; window.__clic=null;
          const orig=URL.revokeObjectURL.bind(URL);
          URL.revokeObjectURL=u=>{ window.__rev.push(performance.now()); orig(u); };
          HTMLAnchorElement.prototype.click=function(){
            window.__clic={t:performance.now(), enDom:document.body.contains(this), nombre:this.download}; };
          S.obra='OBRA T'; S.fecha='2026-11-04'; S.modo='vivienda';
          S.bloques=normaliseStructure({bloques:[{nombre:'B1',portales:[{nombre:'P1',plantas:[{nombre:'1',vivs:['A']}]}]}]});
          S.sel=new Set(CAT.slice(0,3).map(t=>t.id));
          doDownload();
        }""")
        clic = pg.evaluate("window.__clic")
        self.assertIsNotNone(clic, "doDownload no llego a pulsar el enlace")
        self.assertEqual(clic["nombre"], "REVISION OBRA T 04112026.html")
        self.assertTrue(clic["enDom"], "el enlace debe estar dentro del documento al pulsarlo")
        self.assertEqual(pg.evaluate("window.__rev.length"), 0, "la URL se libero en el mismo instante del clic")
        pg.wait_for_function("window.__rev.length===1", timeout=3000)
        self.assertGreaterEqual(pg.evaluate("window.__rev[0] - window.__clic.t"), 900)


class TestH7NombresDeZonaDeGaraje(Base):
    """Nombres automaticos de zona: nunca repetidos en la misma planta (sin distinguir mayusculas)."""

    PREPARAR = """() => { S.modo='garaje'; S.obra='OBRA T';
        S.garajes=normaliseGarajeStructure({garajes:[{nombre:'G1',plantas:[{nombre:'S-1',zonas:[]}]}]}); }"""
    NOMBRES = "S.garajes[0].plantas[0].zonas.map(z=>z.nombre)"

    def _pg(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        return pg

    def test_trasteros_sin_huecos_salen_en_orden(self):
        pg = self._pg()
        pg.evaluate("() => { for(let i=0;i<3;i++) incGarageCount(0,0,'trastero'); }")
        self.assertEqual(pg.evaluate(self.NOMBRES), ["Trasteros 1", "Trasteros 2", "Trasteros 3"])

    def test_viales_sin_huecos_salen_en_orden(self):
        pg = self._pg()
        pg.evaluate("() => { for(let i=0;i<3;i++) incGarageCount(0,0,'vial'); }")
        self.assertEqual(pg.evaluate(self.NOMBRES), ["Zona A", "Zona B", "Zona C"])

    def test_el_noveno_vial_usa_numero_cuando_se_acaban_las_letras(self):
        pg = self._pg()
        pg.evaluate("() => { for(let i=0;i<9;i++) incGarageCount(0,0,'vial'); }")
        self.assertEqual(pg.evaluate(self.NOMBRES)[-2:], ["Zona H", "Zona 9"])

    def test_zonas_con_funcion_sin_huecos_salen_en_orden(self):
        pg = self._pg()
        pg.evaluate("() => { addZona(0,0,'cl_basuras'); addZona(0,0,'cl_basuras'); addZona(0,0,'cl_basuras'); }")
        self.assertEqual(pg.evaluate(self.NOMBRES), ["Basuras", "Basuras 2", "Basuras 3"])

    def test_quitar_un_trastero_del_medio_y_anadir_no_repite_nombre(self):
        pg = self._pg()
        nombres = pg.evaluate("""() => {
            for(let i=0;i<3;i++) incGarageCount(0,0,'trastero');
            rmZona(0,0,S.garajes[0].plantas[0].zonas[1].id);
            incGarageCount(0,0,'trastero');
            return S.garajes[0].plantas[0].zonas.map(z=>z.nombre); }""")
        self.assertEqual(len(nombres), 3)
        self.assertEqual(len(set(nombres)), 3, "nombres repetidos: %r" % nombres)
        self.assertEqual(set(nombres), {"Trasteros 1", "Trasteros 2", "Trasteros 3"})

    def test_quitar_el_primer_vial_y_anadir_no_repite_nombre(self):
        pg = self._pg()
        nombres = pg.evaluate("""() => {
            for(let i=0;i<3;i++) incGarageCount(0,0,'vial');
            rmZona(0,0,S.garajes[0].plantas[0].zonas[0].id);
            incGarageCount(0,0,'vial');
            return S.garajes[0].plantas[0].zonas.map(z=>z.nombre); }""")
        self.assertEqual(len(set(nombres)), 3, "nombres repetidos: %r" % nombres)
        self.assertEqual(set(nombres), {"Zona A", "Zona B", "Zona C"})

    def test_quitar_la_primera_zona_con_funcion_y_anadir_no_repite_nombre(self):
        pg = self._pg()
        nombres = pg.evaluate("""() => {
            addZona(0,0,'cl_basuras'); addZona(0,0,'cl_basuras');
            rmZona(0,0,S.garajes[0].plantas[0].zonas[0].id);
            addZona(0,0,'cl_basuras');
            return S.garajes[0].plantas[0].zonas.map(z=>z.nombre); }""")
        self.assertEqual(len(set(nombres)), 2, "nombres repetidos: %r" % nombres)
        self.assertEqual(set(nombres), {"Basuras", "Basuras 2"})

    def test_la_comparacion_no_distingue_mayusculas(self):
        pg = self._pg()
        nombres = pg.evaluate("""() => {
            incGarageCount(0,0,'trastero'); incGarageCount(0,0,'trastero');
            setZona(0,0,S.garajes[0].plantas[0].zonas[1].id,'trasteros 2');
            incGarageCount(0,0,'trastero');
            return S.garajes[0].plantas[0].zonas.map(z=>z.nombre); }""")
        self.assertEqual(nombres, ["Trasteros 1", "trasteros 2", "Trasteros 3"])

    def test_el_nombre_libre_se_busca_en_toda_la_planta_no_solo_en_su_tipo(self):
        pg = self._pg()
        nombres = pg.evaluate("""() => {
            incGarageCount(0,0,'vial');
            setZona(0,0,S.garajes[0].plantas[0].zonas[0].id,'Trasteros 1');
            incGarageCount(0,0,'trastero');
            return S.garajes[0].plantas[0].zonas.map(z=>z.nombre); }""")
        self.assertEqual(len(set(n.upper() for n in nombres)), 2, "nombres repetidos: %r" % nombres)

    def test_en_otra_planta_el_mismo_nombre_si_vale(self):
        pg = self._pg()
        nombres = pg.evaluate("""() => {
            S.garajes[0].plantas.push(makeGarajePlanta(1));
            incGarageCount(0,0,'trastero'); incGarageCount(0,1,'trastero');
            return S.garajes[0].plantas.map(p=>p.zonas.map(z=>z.nombre)); }""")
        self.assertEqual(nombres, [["Trasteros 1"], ["Trasteros 1"]])


class TestImpresionDeLaHojaDeGaraje(Base):
    """Guarda de algo que ya funciona (comprobado el 04/11/2026): elegir una pestaña no recorta el PDF."""

    def test_con_una_pestana_elegida_se_imprimen_todas_las_secciones(self):
        pg, _ = self.generador()
        html = pg.evaluate("""() => {
          S.modo='garaje'; S.obra='OBRA T'; S.fecha='2026-11-04';
          S.garajes=normaliseGarajeStructure({garajes:[{nombre:'G1',plantas:[{nombre:'S-1',zonas:[
            {nombre:'Zona A',tipo:'vial'},{nombre:'Trastero 1',tipo:'trastero'}]}]}]});
          S.selGaraje=new Set(CAT_GARAJE.map(t=>t.id));
          return generateGarajeHTML({}); }""")
        carpeta = TMP_BASE / ("gen_aud_" + uuid.uuid4().hex[:8])
        carpeta.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(carpeta), True)
        (carpeta / "g.html").write_text(html, encoding="utf-8")
        h = pg.context.new_page()
        h.goto((carpeta / "g.html").as_uri())
        h.evaluate("document.querySelectorAll('.hoja-tab')[2].click()")
        self.assertEqual(h.evaluate("[...document.querySelectorAll('.hoja-section')].map(s=>s.hidden)"), [True, False])
        h.emulate_media(media="print")
        self.assertEqual(h.evaluate("[...document.querySelectorAll('.hoja-section')].map(s=>getComputedStyle(s).display)"),
                         ["block", "block"])


class TestH8RedDeSeguridad(Base):
    """Lo que protege al que sube 23 plantas con la tablet en la mano: si no se esta guardando, que lo diga."""

    def _hoja_llena(self):
        pg, _ = self.generador()
        h = self.hoja(pg, ['A', 'B'])
        h.evaluate(LLENAR_JS)
        return pg, h

    def test_con_el_aparato_lleno_el_autoguardado_avisa(self):
        pg, h = self._hoja_llena()
        h.evaluate("() => document.querySelector('.td-st[data-k]').click()")
        self.assertEqual(h.evaluate("document.querySelector('.td-st[data-k]').dataset.st"), "/",
                         "la celda debe marcarse en pantalla aunque no se pueda guardar")
        self.assertIsNone(h.evaluate("localStorage.getItem(KEY)"))
        avisos = h.evaluate(AVISOS_JS)
        self.assertTrue(any("no se esta guardando" in a.lower().replace("á", "a") for a in avisos), avisos)
        self.assertTrue(any("Guardar revisi" in a for a in avisos), "tiene que decir que hacer: pulsar Guardar revision")

    def test_el_aviso_de_no_guardado_sale_una_vez_no_en_cada_clic(self):
        pg, h = self._hoja_llena()
        h.evaluate("() => document.querySelectorAll('.td-st[data-k]').forEach((c,i)=>{ if(i<4) c.click(); })")
        avisos = [a for a in h.evaluate(AVISOS_JS) if "guardando" in a]
        self.assertEqual(len(avisos), 1, avisos)

    def test_el_aviso_de_no_guardado_dura_lo_bastante_para_leerse(self):
        pg, h = self._hoja_llena()
        h.evaluate("() => document.querySelector('.td-st[data-k]').click()")
        h.wait_for_timeout(2500)
        self.assertTrue(any("guardando" in a for a in h.evaluate(AVISOS_JS)), "se apago antes de poder leerlo")

    def test_con_espacio_el_autoguardado_no_avisa_de_nada(self):
        pg, _ = self.generador()
        h = self.hoja(pg, ['A', 'B'])
        h.evaluate("() => document.querySelector('.td-st[data-k]').click()")
        self.assertEqual(h.evaluate("Object.keys(JSON.parse(localStorage.getItem(KEY))).length"), 1)
        self.assertEqual(h.evaluate(AVISOS_JS), [])

    def test_guardar_revision_con_el_aparato_lleno_sigue_descargando(self):
        """La descarga es la salvaguarda real: no puede depender del almacenamiento."""
        pg, h = self._hoja_llena()
        h.evaluate("() => document.querySelector('.td-st[data-k]').click()")
        with h.expect_download() as d:
            h.evaluate("doSave()")
        self.assertTrue(d.value.suggested_filename.startswith("REVISION OBRA T 04112026"))

    GUARDAR_N = """(n) => { for(let i=0;i<n;i++){ S.obra='OBRA '+i; S.fecha='2026-11-04';
        S.bloques=normaliseStructure({bloques:[{id:'b',nombre:'B1',portales:[{id:'p',nombre:'P1',plantas:[{id:'f',nombre:'1',vivs:['A']}]}]}]});
        saveConfig(); } }"""
    CLAVES_CFG = "Object.keys(localStorage).filter(k=>k.startsWith('sgd_rev_cfg_')).sort()"

    def test_las_configuraciones_que_salen_de_recientes_no_se_acumulan(self):
        pg, _ = self.generador()
        pg.evaluate(self.GUARDAR_N, 11)
        self.assertEqual(pg.evaluate("JSON.parse(localStorage.getItem('sgd_rev_recents')).length"), 8)
        self.assertEqual(len(pg.evaluate(self.CLAVES_CFG)), 8, "las 3 que salieron de la lista se quedaban huerfanas")

    def test_se_conservan_las_configuraciones_de_las_8_ultimas(self):
        pg, _ = self.generador()
        pg.evaluate(self.GUARDAR_N, 11)
        claves = pg.evaluate(self.CLAVES_CFG)
        esperadas = sorted("sgd_rev_cfg_OBRA_%d" % i for i in range(3, 11))
        self.assertEqual(claves, esperadas)

    def test_una_configuracion_huerfana_de_antes_se_limpia(self):
        pg, _ = self.generador()
        pg.evaluate("() => localStorage.setItem('sgd_rev_cfg_VIEJA_HUERFANA', JSON.stringify({obra:'VIEJA'}))")
        pg.evaluate(self.GUARDAR_N, 1)
        self.assertEqual(pg.evaluate(self.CLAVES_CFG), ["sgd_rev_cfg_OBRA_0"])

    def test_no_se_tocan_las_marcas_guardadas_de_las_hojas(self):
        pg, _ = self.generador()
        pg.evaluate("() => localStorage.setItem('sgd_rev_OBRA%20T_2026-11-04', '{\"a\":\"X\"}')")
        pg.evaluate(self.GUARDAR_N, 11)
        self.assertEqual(pg.evaluate("localStorage.getItem('sgd_rev_OBRA%20T_2026-11-04')"), '{"a":"X"}')

    def test_guardar_la_configuracion_con_el_aparato_lleno_avisa_y_no_revienta(self):
        pg, errores = self.generador()
        pg.evaluate("""() => { S.obra='OBRA T'; S.fecha='2026-11-04'; }""")
        pg.evaluate(LLENAR_JS)
        pg.evaluate("saveConfig()")
        self.assertEqual(errores, [], "saveConfig lanzaba QuotaExceededError sin control")
        avisos = pg.evaluate("[...document.querySelectorAll('body > div')].map(d=>d.textContent)")
        self.assertTrue(any("No se pudo guardar la configuraci" in a for a in avisos), avisos)
        self.assertFalse(any("Configuraci" in a and "guardada" in a for a in avisos), "no puede decir que guardo lo que no guardo")

    def test_si_el_aparato_esta_lleno_de_configuraciones_huerfanas_guardar_las_limpia_y_funciona(self):
        pg, errores = self.generador()
        pg.evaluate("""() => { S.obra='OBRA T'; S.fecha='2026-11-04'; }""")
        pg.evaluate(llenar_js("sgd_rev_cfg_HUERFANA_", "sgd_rev_cfg_RELLENO_"))
        pg.evaluate("saveConfig()")
        self.assertEqual(errores, [])
        avisos = pg.evaluate("[...document.querySelectorAll('body > div')].map(d=>d.textContent)")
        self.assertFalse(any("No se pudo guardar" in a for a in avisos), avisos)
        self.assertEqual(pg.evaluate(self.CLAVES_CFG), ["sgd_rev_cfg_OBRA_T"])

    def test_guardar_la_configuracion_con_espacio_sigue_diciendo_guardada(self):
        pg, errores = self.generador()
        pg.evaluate("""() => { S.obra='OBRA T'; S.fecha='2026-11-04'; saveConfig(); }""")
        avisos = pg.evaluate("[...document.querySelectorAll('body > div')].map(d=>d.textContent)")
        self.assertTrue(any("guardada" in a for a in avisos), avisos)
        self.assertEqual(errores, [])


class TestH9HacerSitio(Base):
    """Politica B de Bixente: al llenarse el aparato se borran copias automaticas de hojas de mas de 30 dias."""

    SEMBRAR = """(semillas) => { localStorage.clear();
        for(const [k,tam] of semillas) localStorage.setItem(k,'x'.repeat(tam)); }"""
    ESCRIBIR = """([clave,tam,y,m,d]) => { const r=escribirHaciendoSitio(clave,'x'.repeat(tam),new Date(y,m,d));
        return {ok:r.ok, borradas:r.borradas, aviso:r.aviso, quedan:Object.keys(localStorage).filter(k=>!k.startsWith('relleno_')).sort()}; }"""
    HOY = (2026, 10, 4)          # 04/11/2026 (los meses de Date van de 0 a 11)
    G = 100000

    def _caso(self, semillas, clave="sgd_rev_NUEVA_2026-11-04", tam=50, hoy=HOY, llenar=True):
        pg, _ = self.generador()
        pg.evaluate(self.SEMBRAR, semillas)
        if llenar:
            pg.evaluate(llenar_js())
        return pg.evaluate(self.ESCRIBIR, [clave, tam, *hoy])

    V1 = ("sgd_rev_OBRA1_2026-08-01", G)      # 95 dias
    V2 = ("sgd_rev_OBRA2_2026-09-15", G)      # 50 dias
    V3 = ("sgd_rev_OBRA3_2026-10-04", G)      # 31 dias: ya es «mas de 30»
    K1 = ("sgd_rev_OBRA4_2026-10-05", G)      # 30 dias exactos: NO se borra
    K2 = ("sgd_rev_OBRA5_2026-11-03", G)      # 1 dia

    def test_borra_la_copia_mas_vieja_y_solo_lo_necesario(self):
        r = self._caso([self.V1, self.V2, self.V3, self.K1, self.K2])
        self.assertTrue(r["ok"])
        self.assertEqual(r["borradas"], 1)
        self.assertEqual(r["quedan"], sorted(["sgd_rev_OBRA2_2026-09-15", "sgd_rev_OBRA3_2026-10-04",
                                              "sgd_rev_OBRA4_2026-10-05", "sgd_rev_OBRA5_2026-11-03",
                                              "sgd_rev_NUEVA_2026-11-04"]))

    def test_si_una_no_basta_borra_la_siguiente_mas_vieja(self):
        r = self._caso([self.V1, self.V2, self.V3, self.K1, self.K2], tam=150000)
        self.assertTrue(r["ok"])
        self.assertEqual(r["borradas"], 2)
        self.assertNotIn("sgd_rev_OBRA1_2026-08-01", r["quedan"])
        self.assertNotIn("sgd_rev_OBRA2_2026-09-15", r["quedan"])
        self.assertIn("sgd_rev_OBRA3_2026-10-04", r["quedan"])

    def test_borra_primero_la_mas_vieja_aunque_se_guardara_despues(self):
        """El orden de las claves en el aparato es el de insercion: el criterio tiene que ser la fecha, no ese orden."""
        for semillas in ([self.V1, self.V2], [self.V2, self.V1]):
            r = self._caso(semillas)
            self.assertEqual(r["borradas"], 1)
            self.assertNotIn("sgd_rev_OBRA1_2026-08-01", r["quedan"], "debia borrarse la de 95 dias, no la de 50")
            self.assertIn("sgd_rev_OBRA2_2026-09-15", r["quedan"])

    def test_31_dias_se_borra_y_30_dias_no(self):
        r = self._caso([self.V3])
        self.assertEqual((r["ok"], r["borradas"]), (True, 1))
        r = self._caso([self.K1])
        self.assertEqual((r["ok"], r["borradas"]), (False, 0))
        self.assertIn("sgd_rev_OBRA4_2026-10-05", r["quedan"])

    def test_nunca_borra_lo_que_no_es_copia_de_hoja(self):
        r = self._caso([("sgd_rev_cfg_X_2025-01-01", self.G),     # configuracion con fecha en el nombre
                        ("sgd_rev_recents", 1000),
                        ("otra_app_2020-01-01", self.G),          # de otra aplicacion
                        self.K2])
        self.assertEqual((r["ok"], r["borradas"]), (False, 0))
        for k in ("sgd_rev_cfg_X_2025-01-01", "sgd_rev_recents", "otra_app_2020-01-01", "sgd_rev_OBRA5_2026-11-03"):
            self.assertIn(k, r["quedan"])

    def test_nunca_borra_la_clave_que_se_esta_escribiendo(self):
        # La clave actual es MAS vieja que V1: si entrara entre las candidatas se borraria la primera.
        r = self._caso([("sgd_rev_ACTUAL_2026-07-01", 10), self.V1], clave="sgd_rev_ACTUAL_2026-07-01", tam=50000)
        self.assertTrue(r["ok"])
        self.assertEqual(r["borradas"], 1)
        self.assertIn("sgd_rev_ACTUAL_2026-07-01", r["quedan"])
        self.assertNotIn("sgd_rev_OBRA1_2026-08-01", r["quedan"])

    def test_reconoce_la_copia_de_hoja_de_garaje(self):
        r = self._caso([("sgd_rev_OBRA_2026-08-01_garaje", self.G)])
        self.assertEqual((r["ok"], r["borradas"]), (True, 1))

    def test_la_fecha_de_hoy_es_un_parametro(self):
        r = self._caso([self.V1], hoy=(2026, 7, 2))          # 02/08/2026: V1 tiene 1 dia
        self.assertEqual((r["ok"], r["borradas"]), (False, 0))

    def test_con_sitio_no_borra_nada(self):
        r = self._caso([self.V1], llenar=False)
        self.assertEqual((r["ok"], r["borradas"]), (True, 0))
        self.assertIn("sgd_rev_OBRA1_2026-08-01", r["quedan"])

    def test_el_aviso_dice_cuantas_se_borraron(self):
        uno = self._caso([self.V1, self.V2])
        self.assertRegex(uno["aviso"], r"^Memoria llena: se ha borrado 1 copia autom.tica de una hoja de m.s de 30 d.as para hacer sitio\.$")
        dos = self._caso([self.V1, self.V2], tam=150000)
        self.assertRegex(dos["aviso"], r"^Memoria llena: se han borrado 2 copias autom.ticas de hojas de m.s de 30 d.as para hacer sitio\.$")
        self.assertEqual(self._caso([self.K2], llenar=False)["aviso"], "")

    # ---- integracion: la hoja y «Guardar configuracion» usan la politica ----
    def _contexto_con_reloj(self):
        ctx = self.contexto()
        ctx.clock.set_fixed_time("2026-11-04T10:00:00+01:00")
        return ctx

    def test_la_hoja_borra_copias_viejas_para_seguir_guardando_y_lo_dice(self):
        pg, _ = self.generador(self._contexto_con_reloj())
        h = self.hoja(pg, ['A', 'B'])
        h.evaluate(LLENAR_VIEJAS_JS)
        antes = h.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('sgd_rev_VIEJA')).length")
        h.evaluate("() => document.querySelector('.td-st[data-k]').click()")
        self.assertIsNotNone(h.evaluate("localStorage.getItem(KEY)"), "con copias viejas que borrar tiene que guardar")
        self.assertEqual(h.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('sgd_rev_VIEJA')).length"), antes - 1)
        avisos = h.evaluate(AVISOS_JS)
        self.assertTrue(any("Memoria llena: se ha borrado 1 copia" in a for a in avisos), avisos)
        self.assertFalse(any("No se est" in a for a in avisos), avisos)

    def test_la_hoja_sin_nada_borrable_sigue_avisando_y_no_borra(self):
        pg, _ = self.generador(self._contexto_con_reloj())
        h = self.hoja(pg, ['A', 'B'])
        h.evaluate(llenar_js("sgd_rev_RECIENTE", "relleno_c", "_2026-11-03"))
        antes = h.evaluate("Object.keys(localStorage).length")
        h.evaluate("() => document.querySelector('.td-st[data-k]').click()")
        self.assertEqual(h.evaluate("Object.keys(localStorage).length"), antes, "no debe borrar copias de ayer")
        self.assertTrue(any("No se est" in a for a in h.evaluate(AVISOS_JS)))

    def test_guardar_la_configuracion_borra_copias_viejas_y_lo_dice(self):
        pg, errores = self.generador(self._contexto_con_reloj())
        pg.evaluate("() => { S.obra='OBRA T'; S.fecha='2026-11-04'; }")
        pg.evaluate(LLENAR_VIEJAS_JS)
        antes = pg.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('sgd_rev_VIEJA')).length")
        pg.evaluate("saveConfig()")
        self.assertEqual(errores, [])
        self.assertIsNotNone(pg.evaluate("localStorage.getItem('sgd_rev_cfg_OBRA_T')"))
        self.assertLess(pg.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('sgd_rev_VIEJA')).length"), antes)
        avisos = pg.evaluate("[...document.querySelectorAll('body > div')].map(d=>d.textContent)")
        self.assertTrue(any("guardada" in a and "Memoria llena: se ha" in a for a in avisos), avisos)


class TestH10ContadorDelPaso3(Base):
    """El contador del paso 3 y el resumen del paso 4 tienen que decir lo mismo que sale por la impresora."""

    PREPARAR = "() => { S.modo='vivienda'; S.sel=new Set(CAT.map(t=>t.id)); }"
    LEER = """() => { goStep(3); const c=document.getElementById('tj-count');
        return {texto:c.textContent, clase:c.className,
                act:repartirTajosEnHojas(getActiveTajos()).length, mat:repartirTajosEnHojas(getMatrixTajos()).length,
                nAct:getActiveTajos().length, nMat:getMatrixTajos().length}; }"""
    # 30 tajos de matriz mas: la matriz ya no cabe en una hoja
    DESBORDAR = """() => { for(let i=0;i<30;i++){ CAT.push({id:'zz_extra_'+i,name:'Extra '+i,g:'Fase extra '+(i%6),p:'p',a:'v'});
        S.sel.add('zz_extra_'+i); } }"""

    def _pg(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        return pg

    def test_con_todos_los_tajos_el_contador_no_avisa_de_un_desbordamiento_falso(self):
        r = self._pg().evaluate(self.LEER)
        self.assertGreater(r["act"], 1, "la prueba no ejercita el fallo: con todos los tajos ya cabria en una hoja")
        self.assertEqual(r["mat"], 1)
        self.assertIn("1 hoja por tabla", r["texto"])
        self.assertNotIn("over", r["clase"], "avisaba de un desbordamiento que no existe")

    def test_el_contador_dice_cuantos_tajos_son_de_la_matriz(self):
        r = self._pg().evaluate(self.LEER)
        self.assertIn("%d tajos" % r["nAct"], r["texto"])
        self.assertIn("%d en la matriz" % r["nMat"], r["texto"])

    def test_si_la_matriz_si_desborda_el_contador_avisa(self):
        pg = self._pg()
        pg.evaluate(self.DESBORDAR)
        r = pg.evaluate(self.LEER)
        self.assertEqual(r["mat"], 2)
        self.assertIn("2 hojas por tabla", r["texto"])
        self.assertIn("over", r["clase"])

    def test_el_contador_y_el_resumen_dan_las_mismas_hojas(self):
        import re
        for desbordar in (False, True):
            pg = self._pg()
            if desbordar:
                pg.evaluate(self.DESBORDAR)
            texto = pg.evaluate(self.LEER)["texto"]
            hojas_contador = int(re.search(r"(\d+) hojas? por tabla", texto).group(1))
            resumen = pg.evaluate("() => { goStep(4); return document.getElementById('gen-summary').innerText.replace(/\\s+/g,' '); }")
            m = re.search(r"repartida en (\d+) hojas", resumen)
            hojas_resumen = int(m.group(1)) if m else 1
            self.assertEqual(hojas_contador, hojas_resumen, (texto, resumen[:300]))

    def test_en_modo_garaje_el_contador_no_cambia(self):
        pg, _ = self.generador()
        pg.evaluate("() => { setModo('garaje'); }")
        texto = pg.evaluate("() => { goStep(3); return document.getElementById('tj-count').textContent; }")
        self.assertRegex(texto, r"^\d+ de \d+ tajos de garaje$")


class TestH11ResumenDeZonasEspeciales(Base):
    PREPARAR = """() => { S.modo='vivienda'; S.obra='OBRA T';
        S.bloques=normaliseStructure({bloques:[{id:'b',nombre:'B1',portales:[{id:'p',nombre:'P1',plantas:[{id:'f',nombre:'1',vivs:['A']}]}]}]});
        S.sel=new Set(CAT.map(t=>t.id)); }"""
    CONTENIDO = """() => { goStep(4); const t=document.getElementById('gen-summary').innerText.replace(/\\s+/g,' ');
        return (t.match(/Contenido (.*?) en \\d+ tabla/)||[])[1]||t; }"""

    def _pg(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        return pg

    def test_sin_zonas_especiales_no_dice_que_se_imprima_ninguna(self):
        pg = self._pg()
        contenido = pg.evaluate(self.CONTENIDO)
        self.assertNotIn("zonas especiales", contenido)
        self.assertIn("tajos de matriz", contenido)

    def test_con_un_cuarto_ligero_cuenta_solo_los_tajos_que_ese_cuarto_imprime(self):
        pg = self._pg()
        pg.evaluate("addPortalSpecialZone(0,0,'cl_basuras')")
        esperado = pg.evaluate("""() => SPECIAL_ZONE_PROFILE_TAJOS.cuarto_ligero
            .filter(id=>S.sel.has(id)&&CAT.some(t=>t.id===id)).length""")
        self.assertGreater(esperado, 0)
        contenido = pg.evaluate(self.CONTENIDO)
        self.assertIn("%d de zonas especiales" % esperado, contenido)

    def test_con_varios_tipos_de_zona_cuenta_cada_tajo_una_sola_vez(self):
        pg = self._pg()
        pg.evaluate("() => { addPortalSpecialZone(0,0,'cl_basuras'); addPortalSpecialZone(0,0,'ct_riti'); addPortalSpecialZone(0,0,'cubierta'); }")
        esperado = pg.evaluate("""() => { const ids=new Set(); const z=S.bloques[0].portales[0].zonasEspeciales;
            z.forEach(zona=>specialTajosForZone(zona).forEach(t=>ids.add(t.id))); return ids.size; }""")
        contenido = pg.evaluate(self.CONTENIDO)
        self.assertIn("%d de zonas especiales" % esperado, contenido)

    def test_lo_que_dice_el_resumen_es_lo_que_imprime_la_hoja(self):
        import re
        pg = self._pg()
        pg.evaluate("() => { addPortalSpecialZone(0,0,'cl_basuras'); addPortalSpecialZone(0,0,'ct_riti'); }")
        contenido = pg.evaluate(self.CONTENIDO)
        dicho = int(re.search(r"(\d+) de zonas especiales", contenido).group(1))
        impreso = pg.evaluate("""() => { const h=generateHTML({}); const ks=new Set();
            for(const m of h.matchAll(/data-k="[^"]*__zesp__([^_"][^"]*?)__[^_"][^"]*"/g)) ks.add(m[1]); return ks.size; }""")
        self.assertEqual(dicho, impreso, "el resumen y la hoja impresa no coinciden")

    def test_cuenta_las_zonas_de_todos_los_portales(self):
        pg, _ = self.generador()
        pg.evaluate("""() => { S.modo='vivienda'; S.obra='OBRA T';
            S.bloques=normaliseStructure({bloques:[{id:'b',nombre:'B1',portales:[
              {id:'p1',nombre:'P1',plantas:[{id:'f1',nombre:'1',vivs:['A']}]},{id:'p2',nombre:'P2',plantas:[{id:'f2',nombre:'1',vivs:['A']}]}]}]});
            S.sel=new Set(CAT.map(t=>t.id)); addPortalSpecialZone(0,0,'cl_basuras'); addPortalSpecialZone(0,1,'cubierta'); }""")
        esperado = pg.evaluate("""() => new Set([...SPECIAL_ZONE_PROFILE_TAJOS.cuarto_ligero, ...SPECIAL_ZONE_PROFILE_TAJOS.cubierta]
            .filter(id=>S.sel.has(id)&&CAT.some(t=>t.id===id))).size""")
        solo_el_primero = pg.evaluate("""() => SPECIAL_ZONE_PROFILE_TAJOS.cuarto_ligero.filter(id=>S.sel.has(id)&&CAT.some(t=>t.id===id)).length""")
        self.assertGreater(esperado, solo_el_primero)
        self.assertIn("%d de zonas especiales" % esperado, pg.evaluate(self.CONTENIDO))

    def test_los_tajos_de_matriz_se_siguen_contando_igual(self):
        pg = self._pg()
        n = pg.evaluate("getMatrixTajos().length")
        self.assertIn("%d tajos de matriz" % n, pg.evaluate(self.CONTENIDO))


class TestH12EscapadoDeLaListaDeTajos(Base):
    def test_los_nombres_de_tajo_y_de_fase_no_inyectan_html(self):
        pg, errores = self.generador()
        r = pg.evaluate("""() => { S.modo='vivienda';
            CAT.push({id:'zz_prueba',name:'Cable <i id="intruso">x</i> & tubo',g:'Fase <b id="intruso2">Y</b>',p:'p',a:'v'});
            S.sel.add('zz_prueba'); renderTajosVivienda();
            const out={intruso:!!document.getElementById('intruso'), intruso2:!!document.getElementById('intruso2'),
                       texto:document.getElementById('cb-zz_prueba').parentElement.innerText,
                       fase:[...document.querySelectorAll('.tj-gname')].map(e=>e.textContent).find(t=>t.includes('Fase <b'))};
            CAT.pop(); return out; }""")
        self.assertFalse(r["intruso"] or r["intruso2"], "el nombre se interpreto como HTML")
        self.assertIn('Cable <i id="intruso">x</i> & tubo', r["texto"])
        self.assertEqual(r["fase"], 'Fase <b id="intruso2">Y</b>')
        self.assertEqual(errores, [])

    def test_un_nombre_normal_se_ve_igual(self):
        pg, _ = self.generador()
        pg.evaluate("() => { S.modo='vivienda'; renderTajosVivienda(); }")
        self.assertIn("Pintura — 1ª mano", pg.inner_text("#tj-sel"))
        self.assertIn("Cubierta — Fotovoltaica", pg.inner_text("#tj-sel"))

    def test_la_lista_de_garaje_ya_escapaba_y_sigue_escapando(self):
        pg, _ = self.generador()
        r = pg.evaluate("""() => { setModo('garaje'); CAT_GARAJE.push({id:'zz_g',name:'G <i id="gintruso">x</i>',g:'Fase G',p:'p',a:'z'});
            S.selGaraje.add('zz_g'); renderTajosGaraje(); const o=!!document.getElementById('gintruso'); CAT_GARAJE.pop(); return o; }""")
        self.assertFalse(r)


class TestH7bNombresDeZonaEspecial(Base):
    PREPARAR = """() => { S.modo='vivienda';
        S.bloques=normaliseStructure({bloques:[{id:'b',nombre:'B1',portales:[{id:'p',nombre:'P1',plantas:[{id:'f',nombre:'1',vivs:['A']}]}]}]}); }"""
    NOMBRES = "S.bloques[0].portales[0].zonasEspeciales.map(z=>z.nombre)"

    def _pg(self):
        pg, _ = self.generador()
        pg.evaluate(self.PREPARAR)
        return pg

    def test_sin_huecos_salen_en_orden(self):
        pg = self._pg()
        pg.evaluate("() => { for(let i=0;i<3;i++) addPortalSpecialZone(0,0,'cl_basuras'); }")
        self.assertEqual(pg.evaluate(self.NOMBRES), ["Basuras", "Basuras 2", "Basuras 3"])

    def test_quitar_la_primera_y_anadir_no_repite_nombre(self):
        pg = self._pg()
        nombres = pg.evaluate("""() => { for(let i=0;i<3;i++) addPortalSpecialZone(0,0,'cl_basuras');
            rmPortalSpecialZone(0,0,S.bloques[0].portales[0].zonasEspeciales[0].id);
            addPortalSpecialZone(0,0,'cl_basuras'); return S.bloques[0].portales[0].zonasEspeciales.map(z=>z.nombre); }""")
        self.assertEqual(len(nombres), 3)
        self.assertEqual(len(set(nombres)), 3, "nombres repetidos: %r" % nombres)
        self.assertEqual(set(nombres), {"Basuras", "Basuras 2", "Basuras 3"})

    def test_no_distingue_mayusculas_y_mira_todo_el_portal(self):
        pg = self._pg()
        nombres = pg.evaluate("""() => { addPortalSpecialZone(0,0,'cl_basuras');
            setPortalSpecialZone(0,0,S.bloques[0].portales[0].zonasEspeciales[0].id,'basuras 2');
            addPortalSpecialZone(0,0,'cl_basuras'); return S.bloques[0].portales[0].zonasEspeciales.map(z=>z.nombre); }""")
        self.assertEqual(nombres, ["basuras 2", "Basuras"])

    def test_otro_portal_puede_repetir_el_nombre(self):
        pg, _ = self.generador()
        nombres = pg.evaluate("""() => { S.modo='vivienda';
            S.bloques=normaliseStructure({bloques:[{id:'b',nombre:'B1',portales:[
              {id:'p1',nombre:'P1',plantas:[{id:'f1',nombre:'1',vivs:['A']}]},{id:'p2',nombre:'P2',plantas:[{id:'f2',nombre:'1',vivs:['A']}]}]}]});
            addPortalSpecialZone(0,0,'cl_basuras'); addPortalSpecialZone(0,1,'cl_basuras');
            return S.bloques[0].portales.map(p=>p.zonasEspeciales.map(z=>z.nombre)); }""")
        self.assertEqual(nombres, [["Basuras"], ["Basuras"]])


if __name__ == "__main__":
    unittest.main()
