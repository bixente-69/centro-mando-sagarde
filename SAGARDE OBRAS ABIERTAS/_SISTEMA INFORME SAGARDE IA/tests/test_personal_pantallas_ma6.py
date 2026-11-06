# -*- coding: utf-8 -*-
"""MA6 · la tablet de Personal (generador_personal.html) en el móvil y en la tablet: Chromium de verdad, datos INVENTADOS, fecha fija 23/10/2026.

Mide (en 360, 390, 414, 768, 820 y 1180 px de ancho): que la página no se sale de ancho, que no hay botones ni campos de menos de 44 px,
que la cabecera es de una fila y baja, que la lista de gente se ve al abrir en el móvil (la app no tiene calendario propio hasta «Varios días»), que «Guardar jornada»
está siempre a la vista (también con el teclado puesto) y no tapa el último nombre, que a partir de 768 px hay dos columnas, que los campos
no hacen zoom (16 px) y que la obra de prueba no sale en los desplegables y la tablet se abre en una obra con gente.
P3_APP apunta a otra copia de los tres ficheros de la tablet (para las mutaciones: se rompe una COPIA, nunca el original)."""
import json
import os
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from ayudante_generar import hay_chromium

SISTEMA = Path(__file__).resolve().parent.parent
APP_DIR = Path(os.environ.get("P3_APP") or SISTEMA)
TMP_BASE = Path(os.environ.get("P3_TMP") or tempfile.gettempdir())

ANCHOS = [(360, 780), (390, 844), (414, 896), (768, 1024), (820, 1180), (1180, 820)]
MOVILES = [a for a in ANCHOS if a[0] < 768]
TABLETS = [a for a in ANCHOS if a[0] >= 768]
FECHA_FIJA = """(() => { const fijo = new Date('2026-10-23T10:00:00+02:00').valueOf(); const Real = Date;
  class Falsa extends Real { constructor(...a) { if (a.length === 0) { super(fijo); } else { super(...a); } } static now() { return fijo; } }
  window.Date = Falsa; })();"""
H = {"lun": 7.5, "mar": 7.5, "mie": 7.5, "jue": 7.5, "vie": 7.5, "sab": 0, "dom": 0}
NOMBRES = ["Mikel", "Txomin", "Rafa", "Andoni", "Josu", "Pepe", "Iker", "Unai", "Gorka", "Aitor", "Beñat", "Xabier", "Ander", "Koldo"]
EMPRESAS = {"Rafa": "Alfa Instalaciones", "Pepe": "Alfa Instalaciones", "Iker": "Beta Montajes", "Unai": "Beta Montajes", "Koldo": "Gamma Electrica"}


def _trab(i, n):
    return {"id": "T%04d" % i, "nombre": n, "categoria": "", "empresa": EMPRESAS.get(n, ""), "activo": True}


def _fila(fecha, ambito, nombre, horas):
    f = {"fecha": fecha, "ambito": ambito, "nombre": nombre, "horas": horas, "extra": 0}
    if EMPRESAS.get(nombre):
        f["empresa"] = EMPRESAS[nombre]
    return f


def _obra(nombre, jornadas=(), ultima_viv=None, cerrada=False):
    return {"nombre": nombre, "cerrada": cerrada, "horario_semanal": H, "excepciones_horario": {},
            "ultima": {"vivienda": ultima_viv, "garaje": None}, "jornadas": list(jornadas)}


def estado(con_historia=True):
    """Gernika (la primera de la lista) sin gente; Mungia con una jornada vieja; Olabeaga con 12 personas anotadas el 22/10; una obra de pruebas."""
    pres = NOMBRES[:12]
    obras = {
        "gernika": _obra("2025 GERNIKA 32V"),
        "mungia": _obra("2026 MUNGIA ACR NEINOR", [_fila("2026-10-21", "vivienda", "Pepe", 7.5)],
                        {"fecha": "2026-10-21", "presentes": [{"nombre": "Pepe", "horas": 7.5, "extra": 0}]}),
        "prueba": _obra("2026 OBRA PRUEBA"),
        "olabeaga": _obra("2026 OLABEAGA BILBAO", [_fila("2026-10-22", "vivienda", n, 7.5) for n in pres],
                          {"fecha": "2026-10-22", "presentes": [{"nombre": n, "horas": 7.5, "extra": 0} for n in pres]}),
        "vieja": _obra("2024 OBRA CERRADA", cerrada=True),
    }
    if not con_historia:
        for o in obras.values():
            o["ultima"] = {"vivienda": None, "garaje": None}
            o["jornadas"] = []
    return {"version": 1, "generado": "2026-10-23T08:00:00+02:00", "jornada_base_h": 7.5,
            "catalogo": [_trab(i + 1, n) for i, n in enumerate(NOMBRES)], "obras": obras}


# Medidas de la página tal como está: desborde de ancho, objetos táctiles de menos de 44 px, campos de menos de 16 px y barras de desplazamiento propias.
JS_MEDIDAS = """() => {
  const vw = window.innerWidth;
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !e.closest('[hidden]'); };
  const nombre = e => e.tagName + (e.id ? '#' + e.id : '') + ':' + (e.textContent || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 20);
  const out = { doc: [document.documentElement.scrollWidth, vw], fuera: [], chicos: [], letra: [], propios: [] };
  document.querySelectorAll('body *').forEach(e => {
    if (!vis(e)) return; const r = e.getBoundingClientRect();
    if (r.right > vw + 1) out.fuera.push(e.tagName + (e.id ? '#' + e.id : '') + '.' + String(e.className || '').slice(0, 20) + ':' + Math.round(r.right));
    const s = getComputedStyle(e);
    if ((s.overflowX === 'auto' || s.overflowX === 'scroll') && e.scrollWidth > e.clientWidth + 1) out.propios.push(nombre(e) + ' ' + e.scrollWidth + '>' + e.clientWidth);
  });
  document.querySelectorAll('button, a[href], select, input:not([type=hidden]), summary, textarea').forEach(e => {
    if (!vis(e)) return;
    const r = e.getBoundingClientRect();
    if (r.height < 43.5 || r.width < 43.5) out.chicos.push(nombre(e) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
  });
  document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select, textarea').forEach(e => {
    if (!vis(e)) return;
    if (parseFloat(getComputedStyle(e).fontSize) < 16) out.letra.push(nombre(e) + ' ' + getComputedStyle(e).fontSize);
  });
  document.querySelectorAll('.seg').forEach(e => { if (vis(e) && e.scrollWidth > e.clientWidth + 1) out.propios.push('seg recortado ' + e.scrollWidth + '>' + e.clientWidth); });
  out.fuera = out.fuera.slice(0, 5); out.chicos = out.chicos.slice(0, 8);
  return out; }"""

JS_GUARDAR = """() => {
  const g = document.querySelector('[data-guardar]'); if (!g) return null;
  const r = g.getBoundingClientRect(); let fija = false;
  for (let x = g; x; x = x.parentElement) if (getComputedStyle(x).position === 'fixed') fija = true;
  return { arriba: Math.round(r.top), abajo: Math.round(r.bottom), alto: innerHeight, fija: fija }; }"""


def _hacer_carpeta(con_historia=True, e=None):
    carpeta = TMP_BASE / ("ma6_" + uuid.uuid4().hex[:8])
    carpeta.mkdir(parents=True)
    for n in ("generador_personal.html", "personal_calculo.js"):
        shutil.copy2(APP_DIR / n, carpeta / n)
    datos = e if e is not None else estado(con_historia)
    (carpeta / "personal_estado.js").write_text("window.SAGARDE_PERSONAL = " + json.dumps(datos, ensure_ascii=False) + ";\n", encoding="utf-8")
    return carpeta


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

    def abrir(self, ancho, alto, query="", con_historia=True, init=None, e=None, cerrar_aviso=False):
        """Abre la tablet con datos inventados y devuelve (página, errores de JavaScript). Se limpia sola al acabar el test."""
        carpeta = _hacer_carpeta(con_historia, e)
        self.addCleanup(shutil.rmtree, str(carpeta), True)
        ctx = self.navegador.new_context(viewport={"width": ancho, "height": alto}, timezone_id="Europe/Madrid", locale="es-ES", has_touch=True)
        self.addCleanup(ctx.close)
        ctx.add_init_script(FECHA_FIJA)
        if init:
            ctx.add_init_script(init)
        pg = ctx.new_page()
        pg.set_default_timeout(5000)
        errores = []
        pg.on("pageerror", lambda x: errores.append(str(x)))
        pg.goto((carpeta / "generador_personal.html").resolve().as_uri() + query)
        pg.wait_for_selector("#obra")
        if cerrar_aviso:
            pg.click("#aviso-instalar button")
        return pg, errores


class TestMedidasEnSeisAnchos(Base):
    def _revisar(self, pg, donde, ancho):
        m = pg.evaluate(JS_MEDIDAS)
        self.assertLessEqual(m["doc"][0], m["doc"][1], "%s (%s px): la página se sale de ancho: %s" % (donde, ancho, m["doc"]))
        self.assertEqual(m["fuera"], [], "%s (%s px): hay cosas fuera de la pantalla: %s" % (donde, ancho, m["fuera"]))
        self.assertEqual(m["chicos"], [], "%s (%s px): botones o campos de menos de 44 px: %s" % (donde, ancho, m["chicos"]))
        self.assertEqual(m["letra"], [], "%s (%s px): campos con letra de menos de 16 px (el móvil hace zoom): %s" % (donde, ancho, m["letra"]))
        self.assertEqual(m["propios"], [], "%s (%s px): algo tiene su propia barra de desplazamiento o está recortado: %s" % (donde, ancho, m["propios"]))

    def test_anotar_en_todos_los_estados(self):
        for ancho, alto in ANCHOS:
            with self.subTest(ancho=ancho):
                pg, errores = self.abrir(ancho, alto)
                self._revisar(pg, "Anotar", ancho)
                self.assertIsNone(pg.query_selector("#cal-box"), "sin «Varios días» no hay calendario en la app (el de verdad es el de Sagarde)")
                pg.click("button[data-multi-dias]")
                self.assertTrue(pg.is_visible("#cal-box"), "«Varios días» saca el calendario a la vista")
                self._revisar(pg, "Anotar con «Varios días» encendido (calendario abierto)", ancho)
                pg.click("button[data-multi-dias]")
                pg.click("#horario summary")
                self._revisar(pg, "Anotar con el horario semanal abierto", ancho)
                pg.click("button[data-varios]")
                self._revisar(pg, "Anotar con «Añadir varios nombres» abierto", ancho)
                pg.click("button[data-varios-cerrar]")
                pg.click(".lap >> nth=0")
                self._revisar(pg, "Anotar con el lápiz abierto", ancho)
                pg.click("button[data-ren-cancelar]")
                # un lunes de futuro (en esta fecha de prueba): al guardar sale el aviso con sus botones
                pg.evaluate("v => { const f = document.getElementById('fecha'); f.value = v; f.dispatchEvent(new Event('change', { bubbles: true })); }", "2026-10-26")
                pg.click("button[data-copiar-ultimo]")   # un día nuevo sale sin marcar: se copia a la gente del 22/10
                pg.click("button[data-guardar]")
                pg.wait_for_selector("#aviso-guardar")
                self._revisar(pg, "Anotar con el aviso de guardar", ancho)
                self.assertEqual(errores, [], "errores de JavaScript: %s" % errores)

    def test_las_otras_pantallas(self):
        for ancho, alto in ANCHOS:
            with self.subTest(ancho=ancho):
                pg, errores = self.abrir(ancho, alto)
                for v, nombre in (("jornadas", "Jornadas"), ("informe", "Informe"), ("enviar", "Enviar al PC")):
                    pg.click('button[data-v="%s"]' % v)
                    self._revisar(pg, nombre, ancho)
                self.assertEqual(errores, [], "errores de JavaScript: %s" % errores)


class TestCabeceraListaYGuardar(Base):
    def test_la_cabecera_es_una_fila_y_ocupa_poco(self):
        for ancho, alto in ANCHOS:
            with self.subTest(ancho=ancho):
                pg, _ = self.abrir(ancho, alto)
                c = pg.evaluate("""() => { const t = document.querySelector('.tabs').getBoundingClientRect();
                  const v = document.querySelector('.btn-volver-portal').getBoundingClientRect(), s = document.querySelector('.tabs .seg').getBoundingClientRect();
                  return {alto: t.height, pantalla: innerHeight, mismaFila: Math.abs((v.top + v.height / 2) - (s.top + s.height / 2)) < 3, pos: getComputedStyle(document.querySelector('.tabs')).position}; }""")
                self.assertTrue(c["mismaFila"], "la cabecera tiene que ser UNA fila (volver y las cuatro pestañas juntos): %s" % c)
                self.assertLessEqual(c["alto"] / c["pantalla"], 0.15, "la cabecera ocupa más del 15 %% de la pantalla: %s" % c)
                self.assertLessEqual(c["alto"], 64, "la cabecera de una fila no pasa de 64 px: %s" % c)
                self.assertEqual(c["pos"], "sticky")
                self.assertEqual(pg.get_attribute(".btn-volver-portal", "aria-label"), "Volver al Portal Sagarde")

    def test_en_el_movil_la_lista_se_ve_al_abrir_y_no_hay_calendario_hasta_varios_dias(self):
        for ancho, alto in MOVILES:
            with self.subTest(ancho=ancho):
                pg, _ = self.abrir(ancho, alto)   # con el aviso de «añadir a la pantalla de inicio» puesto: el peor caso
                self.assertIsNone(pg.query_selector("#cal-box"), "sin «Varios días» no hay calendario en la app")
                self.assertIsNone(pg.query_selector("#cal-toggle"), "ni botón de plegarlo: ya no hay nada que plegar")
                # el rótulo de la fecha dice qué día está elegido (la hoja de estilos lo escribe en mayúsculas)
                texto = " ".join(pg.inner_text("#fecha-rotulo").split()).lower()
                self.assertEqual(texto, "fecha: hoy · viernes 23/10", "el rótulo dice qué día está elegido")
                # el enlace al calendario de Sagarde va en la misma fila que la fecha: no gasta una fila más
                fila = pg.evaluate("""() => { const i = document.getElementById('fecha').getBoundingClientRect(), l = document.getElementById('enlace-calendario').getBoundingClientRect();
                  return {mismaFila: Math.abs(i.top - l.top) < 3, alto: l.height}; }""")
                self.assertTrue(fila["mismaFila"], "el enlace al calendario tiene que ir en la misma fila que la fecha: %s" % fila)
                self.assertGreaterEqual(fila["alto"], 44, "el enlace tiene que poder pulsarse con el dedo: %s" % fila)
                primera = pg.evaluate("document.querySelector('#lista .row').getBoundingClientRect().top")
                self.assertLessEqual(primera, alto - 56, "la primera persona de la lista tiene que verse sin bajar (empieza a %s de %s px)" % (round(primera), alto))
                # «Varios días»: el calendario sale abierto, marcar un día no lo pliega y apagarlo lo quita
                pg.click("button[data-multi-dias]")
                self.assertTrue(pg.is_visible("#cal-box"), "«Varios días» saca el calendario")
                pg.click('button[data-cal-dia="2026-10-21"]')
                self.assertTrue(pg.is_visible("#cal-box"), "marcar un día con «Varios días» no pliega el calendario")
                self.assertEqual(" ".join(pg.inner_text("#fecha-rotulo").split()).lower(), "fecha: 2 días marcados")
                pg.click("button[data-multi-dias]")
                self.assertIsNone(pg.query_selector("#cal-box"), "apagar «Varios días» quita el calendario")

    def test_en_la_tablet_sin_varios_dias_no_hay_calendario_y_con_varios_dias_se_ve(self):
        for ancho, alto in TABLETS:
            with self.subTest(ancho=ancho):
                pg, _ = self.abrir(ancho, alto)
                self.assertIsNone(pg.query_selector("#cal-box"), "en la tablet tampoco hay calendario propio sin «Varios días»")
                self.assertTrue(pg.is_visible("#enlace-calendario"), "el enlace al calendario de Sagarde se ve")
                pg.click("button[data-multi-dias]")
                self.assertTrue(pg.is_visible("#cal-box"), "con «Varios días» el calendario sale a la vista")

    def test_guardar_esta_siempre_a_la_vista_tambien_con_el_teclado(self):
        for ancho, alto in ANCHOS:
            with self.subTest(ancho=ancho):
                pg, _ = self.abrir(ancho, alto)
                g = pg.evaluate(JS_GUARDAR)
                self.assertTrue(g["fija"], "«Guardar jornada» tiene que ir en una barra fija: %s" % g)
                self.assertTrue(0 <= g["arriba"] and g["abajo"] <= g["alto"], "«Guardar jornada» tiene que verse sin bajar: %s" % g)
                self.assertEqual(" ".join(pg.inner_text("button[data-guardar]").split()), "Guardar jornada")
                pg.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                g = pg.evaluate(JS_GUARDAR)
                self.assertTrue(0 <= g["arriba"] and g["abajo"] <= g["alto"], "al final de la página también: %s" % g)
                # teclado puesto: la ventana pierde 300 px de alto (en Android el navegador achica la página)
                pg.set_viewport_size({"width": ancho, "height": max(320, alto - 300)})
                g = pg.evaluate(JS_GUARDAR)
                self.assertTrue(0 <= g["arriba"] and g["abajo"] <= g["alto"], "con el teclado puesto «Guardar jornada» tiene que verse: %s" % g)
                self.assertGreaterEqual(pg.evaluate("document.querySelector('button[data-guardar]').getBoundingClientRect().height"), 52)

    def test_la_barra_no_tapa_ni_el_ultimo_nombre_ni_lo_ultimo_de_la_pagina(self):
        for ancho, alto in ANCHOS:
            with self.subTest(ancho=ancho):
                pg, _ = self.abrir(ancho, alto)
                barra_arriba = lambda: pg.evaluate("document.querySelector('#barra-guardar').getBoundingClientRect().top")  # noqa: E731
                pg.evaluate("document.querySelector('#lista .row:last-child').scrollIntoView({block: 'end'})")
                ultima = pg.evaluate("document.querySelector('#lista .row:last-child').getBoundingClientRect().bottom")
                self.assertLessEqual(ultima, barra_arriba() + 1, "la barra tapa el último nombre de la lista (%s px)" % ancho)
                pg.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                ultimo = pg.evaluate("""() => { const c = document.querySelectorAll('#v-app .col-der > *'); return c[c.length - 1].getBoundingClientRect().bottom; }""")
                self.assertLessEqual(ultimo, barra_arriba() + 1, "la barra tapa lo último de la página (%s px)" % ancho)

    def test_el_aviso_flotante_sale_por_encima_de_la_barra(self):
        for ancho, alto in ((390, 844), (820, 1180)):
            with self.subTest(ancho=ancho):
                pg, _ = self.abrir(ancho, alto)
                pg.evaluate("toast('Aviso de prueba')")
                r = pg.evaluate("""() => ({toast: document.querySelector('#toast').getBoundingClientRect().bottom,
                                           barra: document.querySelector('#barra-guardar').getBoundingClientRect().top})""")
                self.assertLessEqual(r["toast"], r["barra"], "el aviso flotante queda detrás de la barra de guardar: %s" % r)

    def test_el_resumen_y_el_guardado_siguen_igual(self):
        pg, errores = self.abrir(390, 844)
        pg.click("button[data-copiar-ultimo]")   # el viernes 23/10 sale sin marcar: se copia a la gente del 22/10
        self.assertEqual(" ".join(pg.inner_text("#resumen").split()), "12 presentes · 90 h")
        pg.click("button[data-guardar]")
        pg.wait_for_function("(JSON.parse(localStorage.getItem('sgd_personal_pendientes') || '[]')).length === 1")
        pendientes = pg.evaluate("JSON.parse(localStorage.getItem('sgd_personal_pendientes') || '[]')")
        self.assertTrue(pendientes and pendientes[0]["obra"] == "olabeaga" and len(pendientes[0]["presentes"]) == 12, pendientes)
        self.assertEqual(errores, [])


class TestDosColumnas(Base):
    def test_a_partir_de_768_hay_dos_columnas_y_en_el_movil_una(self):
        for ancho, alto in ANCHOS:
            with self.subTest(ancho=ancho):
                pg, _ = self.abrir(ancho, alto)
                c = pg.evaluate("""() => { const o = document.querySelector('#obra').getBoundingClientRect(), l = document.querySelector('#lista').getBoundingClientRect(),
                  m = document.querySelector('main').getBoundingClientRect(), i = document.querySelector('.col-izq').getBoundingClientRect(), d = document.querySelector('.col-der').getBoundingClientRect();
                  return {obraDcha: o.right, listaIzq: l.left, listaDcha: l.right, main: m.width, izq: i.width, der: d.width, ancho: innerWidth}; }""")
                if ancho >= 768:
                    self.assertGreaterEqual(c["listaIzq"], c["obraDcha"] - 1, "en la tablet la lista de gente va en la 2.ª columna: %s" % c)
                    self.assertGreaterEqual(c["main"], min(ancho, 1100) - 24, "la tablet aprovecha el ancho (hasta 1100 px): %s" % c)
                    self.assertGreaterEqual(c["der"], 330, "la columna de la lista es ancha de verdad: %s" % c)
                else:
                    self.assertLess(c["listaIzq"], c["obraDcha"], "en el móvil todo va en una columna: %s" % c)

    def test_la_columna_de_la_lista_llega_hasta_el_final_con_su_scroll(self):
        for ancho, alto in TABLETS:
            with self.subTest(ancho=ancho):
                pg, _ = self.abrir(ancho, alto)
                pg.click("button[data-copiar-ultimo]")   # un día nuevo sale sin marcar: se copia a la gente del 22/10
                altura = pg.evaluate("document.documentElement.scrollHeight")
                self.assertGreater(altura, alto, "con 12 personas la página tiene que poder bajarse (%s de %s)" % (altura, alto))
                pg.evaluate("document.querySelector('#lista .row:last-child').scrollIntoView({block: 'end'})")
                pg.click("button[data-guardar]")   # llega y se puede pulsar
                pg.wait_for_function("(JSON.parse(localStorage.getItem('sgd_personal_pendientes') || '[]')).length === 1")

    def test_la_columna_de_la_izquierda_se_queda_y_tiene_su_scroll_si_la_pantalla_es_baja(self):
        # (sin el calendario propio, que ya solo sale con «Varios días», la columna de la izquierda mide ~344 px: la pantalla de la
        # prueba tiene que ser más baja que eso para que haga falta su scroll)
        pg, _ = self.abrir(1180, 420)
        c = pg.evaluate("""() => { const e = document.querySelector('.col-izq'), s = getComputedStyle(e);
          return {pos: s.position, oy: s.overflowY, alto: e.clientHeight, contenido: e.scrollHeight, pantalla: innerHeight}; }""")
        self.assertEqual(c["pos"], "sticky", c)
        self.assertIn(c["oy"], ("auto", "scroll"), "con la pantalla baja la columna de la izquierda tiene que poder bajarse sola: %s" % c)
        self.assertLess(c["alto"], c["pantalla"], "la columna de la izquierda no es más alta que la pantalla: %s" % c)
        self.assertGreater(c["contenido"], c["alto"], "(la prueba necesita una pantalla más baja que la columna) %s" % c)
        pg.evaluate("document.querySelector('.col-izq').scrollTop = 99999")
        r = pg.evaluate("""() => ({boton: document.querySelector('[data-multi-dias]').getBoundingClientRect().bottom, col: document.querySelector('.col-izq').getBoundingClientRect().bottom})""")
        self.assertLessEqual(r["boton"], r["col"] + 1, "lo último de la columna de la izquierda se alcanza: %s" % r)

    def test_las_otras_pantallas_no_se_estiran_de_mas(self):
        pg, _ = self.abrir(1180, 820)
        for v in ("jornadas", "informe", "enviar"):
            pg.click('button[data-v="%s"]' % v)
            ancho = pg.evaluate("document.querySelector('#v-%s').getBoundingClientRect().width" % v)
            self.assertLessEqual(ancho, 761, "%s: la pantalla se estira demasiado: %s" % (v, ancho))
            self.assertGreaterEqual(ancho, 600, "%s: la pantalla es demasiado estrecha en una tablet: %s" % (v, ancho))


class TestObraPorDefectoYDePrueba(Base):
    def obras(self, pg, sel="#obra"):
        return pg.evaluate("[...document.querySelector('%s').options].map(o => o.textContent)" % sel)

    def elegida(self, pg):
        return pg.evaluate("document.querySelector('#obra').selectedOptions[0].textContent")

    def test_la_obra_de_prueba_no_sale_y_con_pruebas_uno_si(self):
        pg, _ = self.abrir(390, 844)
        self.assertEqual(self.obras(pg), ["2025 GERNIKA 32V", "2026 MUNGIA ACR NEINOR", "2026 OLABEAGA BILBAO"])
        pg.click('button[data-v="jornadas"]')
        self.assertEqual(self.obras(pg, "#obra-j"), ["2025 GERNIKA 32V", "2026 MUNGIA ACR NEINOR", "2026 OLABEAGA BILBAO"])
        pg2, _ = self.abrir(390, 844, query="?pruebas=1")
        self.assertIn("2026 OBRA PRUEBA", self.obras(pg2))
        pg2.click('button[data-v="jornadas"]')
        self.assertIn("2026 OBRA PRUEBA", self.obras(pg2, "#obra-j"))
        pg3, _ = self.abrir(390, 844, query="?pruebas=0")
        self.assertNotIn("2026 OBRA PRUEBA", self.obras(pg3))

    def test_se_abre_en_la_obra_con_la_jornada_mas_reciente_y_no_en_la_primera(self):
        pg, errores = self.abrir(390, 844)
        self.assertEqual(self.elegida(pg), "2026 OLABEAGA BILBAO")
        self.assertEqual(pg.evaluate("document.querySelectorAll('#lista .row').length"), 12, "y trae su gente")
        self.assertEqual(errores, [])

    def test_sin_ninguna_jornada_se_abre_en_la_primera_visible_nunca_en_la_de_prueba(self):
        pg, _ = self.abrir(390, 844, con_historia=False)
        self.assertEqual(self.elegida(pg), "2025 GERNIKA 32V")
        e = estado(False)
        e["obras"] = {"prueba": e["obras"]["prueba"], "mungia": e["obras"]["mungia"]}
        pg2, _ = self.abrir(390, 844, e=e)
        self.assertEqual(self.elegida(pg2), "2026 MUNGIA ACR NEINOR", "la obra de pruebas no se elige sola aunque sea la primera")

    def test_se_acuerda_de_la_ultima_que_se_uso(self):
        pg, _ = self.abrir(390, 844)
        pg.select_option("#obra", "mungia")
        self.assertEqual(pg.evaluate("localStorage.getItem('sgd_personal_ultima_obra')"), '"mungia"')
        pg.evaluate("localStorage.removeItem('sgd_personal_borrador')")   # como «Borrar lo que llevo a medias»: solo queda la obra
        pg.reload()
        pg.wait_for_selector("#obra")
        self.assertEqual(self.elegida(pg), "2026 MUNGIA ACR NEINOR")
        # lo guardado de una obra que ya no existe o que es la de pruebas no vale
        pg.evaluate("localStorage.setItem('sgd_personal_ultima_obra', JSON.stringify('prueba')); localStorage.removeItem('sgd_personal_borrador')")
        pg.reload()
        pg.wait_for_selector("#obra")
        self.assertEqual(self.elegida(pg), "2026 OLABEAGA BILBAO")
        pg.evaluate("localStorage.setItem('sgd_personal_ultima_obra', JSON.stringify('vieja')); localStorage.removeItem('sgd_personal_borrador')")
        pg.reload()
        pg.wait_for_selector("#obra")
        self.assertEqual(self.elegida(pg), "2026 OLABEAGA BILBAO")

    def test_una_obra_de_prueba_que_ya_se_estaba_usando_no_desaparece_del_desplegable(self):
        pg, _ = self.abrir(390, 844, query="?pruebas=1")
        pg.select_option("#obra", "prueba")
        pg.evaluate("document.querySelectorAll('[data-add]').length")   # (la tablet ya tiene el borrador de la obra de pruebas)
        pg2 = pg.context.new_page()
        pg2.goto(pg.url.split("?")[0])   # sin ?pruebas=1 pero con el borrador de la obra de pruebas
        pg2.wait_for_selector("#obra")
        self.assertEqual(self.elegida(pg2), "2026 OBRA PRUEBA", "el desplegable enseña la obra con la que se está trabajando")


class TestTeclado(Base):
    def test_la_pagina_pide_pantalla_completa_y_no_se_tapa_con_el_teclado(self):
        pg, _ = self.abrir(390, 844)
        v = pg.get_attribute('meta[name="viewport"]', "content")
        self.assertIn("viewport-fit=cover", v)
        self.assertIn("interactive-widget=resizes-content", v)
        reglas = pg.evaluate("""() => { let t = ''; for (const h of document.styleSheets) for (const r of h.cssRules) t += r.cssText + '\\n'; return t; }""")
        for clase in (".barra-guardar", ".tabs"):
            trozo = [l for l in reglas.split("\n") if l.startswith(clase + " ")]
            self.assertTrue(trozo and "safe-area-inset" in " ".join(trozo), "%s no respeta la zona segura del aparato" % clase)
        self.assertIn("safe-area-inset-bottom", " ".join(l for l in reglas.split("\n") if l.startswith(".barra-guardar ")))

    def test_cada_campo_tiene_el_teclado_que_toca(self):
        pg, _ = self.abrir(390, 844)
        pg.click("#horario summary")
        c = pg.evaluate("""() => { const q = s => document.querySelector(s);
          return { nuevo: [q('#nuevo').autocomplete, q('#nuevo').getAttribute('enterkeyhint'), q('#nuevo').getAttribute('autocapitalize')],
                   filtro: [q('#filtro').autocomplete, q('#filtro').getAttribute('enterkeyhint'), q('#filtro').getAttribute('inputmode')],
                   horas: [...document.querySelectorAll('[data-hor]')].map(e => e.getAttribute('inputmode') + '/' + e.autocomplete) }; }""")
        self.assertEqual(c["nuevo"], ["off", "done", "words"])
        self.assertEqual(c["filtro"], ["off", "search", "search"])
        self.assertEqual(c["horas"], ["decimal/off"] * 7)


class TestPorEmpresaDelRanking(Base):
    """El bloque «Por empresa» del Ranking (personal_sagarde.html) tenía en el móvil una barra de desplazamiento propia (397 > 335 px)."""

    def test_la_tabla_cabe_sin_barra_en_el_movil(self):
        import datos_base_trabajadores as D
        for ancho, alto in MOVILES:
            with self.subTest(ancho=ancho):
                carpeta = TMP_BASE / ("ma6r_" + uuid.uuid4().hex[:8])
                carpeta.mkdir(parents=True)
                self.addCleanup(shutil.rmtree, str(carpeta), True)
                for n in ("personal_sagarde.html", "personal_calculo.js"):
                    shutil.copy2(APP_DIR / n, carpeta / n)
                (carpeta / "personal_estado.js").write_text("window.SAGARDE_PERSONAL = " + json.dumps(D.ESTADO_PRINCIPAL, ensure_ascii=False) + ";\n", encoding="utf-8")
                ctx = self.navegador.new_context(viewport={"width": ancho, "height": alto})
                self.addCleanup(ctx.close)
                pg = ctx.new_page()
                pg.goto((carpeta / "personal_sagarde.html").resolve().as_uri())
                pg.wait_for_selector("table.emp-tabla")
                r = pg.evaluate("""() => { const s = document.querySelector('.emp-scroll'); return {caja: s.clientWidth, tabla: s.scrollWidth,
                    pagina: [document.documentElement.scrollWidth, innerWidth]}; }""")
                self.assertLessEqual(r["tabla"], r["caja"] + 1, "la tabla «Por empresa» tiene barra de desplazamiento propia a %s px: %s" % (ancho, r))
                self.assertLessEqual(r["pagina"][0], r["pagina"][1])


if __name__ == "__main__":
    unittest.main()
