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

# Pulsa (cambia de estado) la primera o segunda celda de las viviendas pedidas, por orden de aparicion.
MARCAR_JS = """(pares) => {
  const cs=[...document.querySelectorAll('.td-st[data-k]')];
  pares.forEach(([viv,n])=>cs.filter(c=>c.dataset.k.endsWith('__'+viv))[n].click());
}"""

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

    def hoja(self, pg, vivs):
        """Genera la hoja con esas viviendas, la guarda en una carpeta temporal y la abre en una pagina nueva."""
        html = pg.evaluate(HOJA_JS, vivs)
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


if __name__ == "__main__":
    unittest.main()
