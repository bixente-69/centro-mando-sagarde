# -*- coding: utf-8 -*-
"""MA8 · pruebas para las zonas del código de agy (tablet y «Generar personal») que NINGUNA prueba vigilaba.

Cómo se encontraron: se rompió a propósito, una a una y sobre copias, cada función que agy dejó en `main` sin repaso
(`save`, `addName`, `ultimoHorarioDe`, `buscarCoincidenciasOtrasObras`, `armarFichero`, `descargarFicheroControlHorario`,
`intentarAnadirTrabajadores`) y se miró si algo se enteraba. Los supervivientes de esa pasada son lo que cubre este fichero:
  · `ultimoHorarioDe` (la búsqueda «Por horas» de «Añadir de la base») y la memoria de las últimas horas que escribe `save`.
  · `addName` con alguien que ya estaba en la lista (vuelve a las horas de su horario de ese día).
  · «Añadir igualmente» (nombre parecido) de «Generar personal».
Datos INVENTADOS, navegador de verdad (Chromium), fecha fija: viernes 23/10/2026. `P3_APP` apunta a otra copia de la app (para
las mutaciones: se rompe una COPIA, nunca el original). unittest de la biblioteca estándar."""
import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import datos_base_trabajadores as D  # noqa: E402
import ayudante_generar as AG  # noqa: E402

APP_DIR = Path(os.environ.get("P3_APP") or TESTS.parent)
TMP_BASE = Path(os.environ.get("P3_TMP") or tempfile.gettempdir())
FECHA_FIJA = """(() => { const fijo = new Date('2026-10-23T10:00:00+02:00').valueOf(); const Real = Date;
  class Falsa extends Real { constructor(...a) { if (a.length === 0) { super(fijo); } else { super(...a); } } static now() { return fijo; } }
  window.Date = Falsa; })();"""
OLA = "2026 OLABEAGA"
MUN = "2026 MUNGIA"


def _hay_chromium():
    return AG.hay_chromium()


_OK, _MOTIVO = _hay_chromium()


def estado_horas():
    """Seis personas y dos obras con las jornadas elegidas para que cada respuesta de `ultimoHorarioDe` se calcule a mano."""
    catalogo = [
        D.ficha(1, "Ana"), D.ficha(2, "Beto"), D.ficha(3, "Carla"), D.ficha(4, "Dani"),
        D.ficha(5, "Eli", horario_preferido={"vie": 6}), D.ficha(6, "Fran"),
    ]
    ola = D.obra(OLA, [
        D.fila("2026-10-14", "vivienda", "Ana", 6), D.fila("2026-10-20", "vivienda", "Ana", 8),
        D.fila("2026-10-26", "vivienda", "Ana", 3),                      # POSTERIOR a la fecha que se pregunta: no cuenta
        D.fila("2026-10-20", "vivienda", "Fran", 5),
        D.fila("2026-10-22", "vivienda", "Gus", 7.5),                    # ese día ya tiene gente publicada: una anulada sin enviar NO queda redundante
    ])
    mun = D.obra(MUN, [
        D.fila("2026-10-19", "vivienda", "Beto", 4), D.fila("2026-10-27", "vivienda", "Beto", 2),   # el 27 es posterior
        D.fila("2026-10-21", "vivienda", "Fran", 9),                     # Fran ya tiene jornada en SU obra: manda esa
    ])
    return D.estado(catalogo, {"olabeaga": ola, "mungia": mun})


class Tablet:
    """La tablet en Chromium, con un personal_estado.js dado y, si se pide, cosas ya guardadas en el aparato."""

    def __init__(self, browser, estado, guardado=None, ancho=820, alto=1000):
        self.dir = TMP_BASE / ("ma8_" + uuid.uuid4().hex[:8])
        self.dir.mkdir(parents=True)
        shutil.copy2(APP_DIR / "generador_personal.html", self.dir / "generador_personal.html")
        shutil.copy2(APP_DIR / "personal_calculo.js", self.dir / "personal_calculo.js")
        (self.dir / "personal_estado.js").write_text("window.SAGARDE_PERSONAL = " + json.dumps(estado, ensure_ascii=False) + ";\n", encoding="utf-8")
        self.ctx = browser.new_context(viewport={"width": ancho, "height": alto}, timezone_id="Europe/Madrid", locale="es-ES")
        self.ctx.add_init_script(FECHA_FIJA)
        if guardado:
            # solo la PRIMERA vez que se abre la página (si no, cada recarga borraría lo que la tablet acaba de guardar)
            self.ctx.add_init_script(
                "if (!sessionStorage.getItem('__ma8')) { sessionStorage.setItem('__ma8', '1'); const g = %s;"
                " Object.keys(g).forEach(k => localStorage.setItem(k, JSON.stringify(g[k]))); }" % json.dumps(guardado, ensure_ascii=False))
        self.pg = self.ctx.new_page()
        self.pg.set_default_timeout(4000)
        self.errores = []
        self.pg.on("pageerror", lambda e: self.errores.append(str(e)))
        self.url = (self.dir / "generador_personal.html").resolve().as_uri()

    def ir(self):
        self.pg.goto(self.url)
        self.pg.wait_for_selector("#obra")
        return self

    def cerrar(self):
        self.ctx.close()
        shutil.rmtree(str(self.dir), ignore_errors=True)

    def ls(self, clave):
        return self.pg.evaluate("k => JSON.parse(localStorage.getItem(k) || 'null')", "sgd_personal_" + clave)

    def horas_de(self, nombre):
        return self.pg.inner_text('#v-app .row[data-nombre="%s"] .step output' % nombre).strip()

    def marcados(self):
        return self.pg.eval_on_selector_all('#v-app .row', 'e=>e.filter(r=>r.querySelector(".x.on")).map(r=>r.dataset.nombre)')

    def marcar(self, nombre):
        """Marca a alguien: con su X si ya sale en la lista; si no, lo añade de la base."""
        if self.pg.query_selector('#v-app .row[data-nombre="%s"]' % nombre):
            if nombre not in self.marcados():
                self.pg.click('#v-app .row[data-nombre="%s"] .x' % nombre)
        else:
            self.pg.select_option("#addsel", nombre)
            self.pg.click("button[data-add]")

    def pulsar(self, nombre, veces, d):
        self.pg.evaluate(
            """([n, d, k]) => { for (let i = 0; i < k; i++) { const b = document.querySelector('#v-app .row[data-nombre="' + n + '"] .step button[data-d="' + d + '"]'); if (b) b.click(); } }""",
            [nombre, d, veces])


@unittest.skipUnless(_OK, "NO se ha comprobado la tablet en el navegador: %s" % _MOTIVO)
class TestUltimoHorarioYBusquedaPorHoras(unittest.TestCase):
    """`ultimoHorarioDe`: de dónde sale el horario que la tablet recuerda de cada persona (y, con él, la búsqueda «Por horas»)."""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def uh(self, t, nombre, obra="olabeaga", fecha="2026-10-23"):
        return t.pg.evaluate("([n, o, f]) => ultimoHorarioDe(n, o, f)", [nombre, obra, fecha])

    def test_de_donde_sale_el_horario_recordado(self):
        t = Tablet(self.browser, estado_horas()).ir()
        try:
            casos = [
                ("Ana", "olabeaga", "2026-10-23", 8, "la jornada MÁS RECIENTE anterior de su obra (el 20/10), no la más antigua ni la posterior del 26/10"),
                ("Ana", "olabeaga", "2026-10-15", 6, "con fecha el 15/10 solo cuenta lo anterior: el 14/10"),
                ("Ana", "olabeaga", "2026-10-14", 7.5, "el propio día no cuenta como «anterior»: cae al horario de la obra (miércoles, 7,5)"),
                ("Beto", "olabeaga", "2026-10-23", 4, "sin jornadas en esta obra, la más reciente anterior de las demás (Mungia, 19/10), no la del 27/10"),
                ("Fran", "olabeaga", "2026-10-23", 5, "lo de SU obra (5 h) manda sobre lo de otra obra (9 h)"),
                ("Fran", "mungia", "2026-10-23", 9, "en Mungia manda lo de Mungia"),
                ("Carla", "olabeaga", "2026-10-23", 7.5, "sin historial: el horario de la obra (viernes, 7,5)"),
                ("Carla", "olabeaga", "2026-10-24", None, "sábado sin horario en la obra: nada (null), no 0"),
                ("Eli", "olabeaga", "2026-10-23", 6, "su horario propio del viernes (6) manda sobre el de la obra"),
                ("Eli", "olabeaga", "2026-10-26", 7.5, "el lunes no tiene horario propio: el de la obra"),
            ]
            for nombre, obra, fecha, esperado, motivo in casos:
                self.assertEqual(esperado, self.uh(t, nombre, obra, fecha), "%s en %s el %s: %s" % (nombre, obra, fecha, motivo))
        finally:
            t.cerrar()

    def test_las_ultimas_horas_guardadas_en_el_aparato_mandan(self):
        t = Tablet(self.browser, estado_horas(), guardado={"sgd_personal_ultimas_horas": {"carla": 5, "ana": 9, "beto": 0}}).ir()
        try:
            self.assertEqual(5, self.uh(t, "Carla"), "lo recordado en el aparato (5) manda sobre el horario de la obra (7,5)")
            self.assertEqual(9, self.uh(t, "Ana"), "lo recordado (9) manda sobre su historial (8)")
            self.assertEqual(4, self.uh(t, "Beto"), "un 0 recordado no cuenta: sigue el historial (Mungia, 4)")
        finally:
            t.cerrar()

    def test_las_jornadas_sin_enviar_cuentan_salvo_las_anuladas(self):
        # Una anulada normal lleva presentes vacíos; esta conserva gente (datos de una versión vieja) para comprobar que NO cuenta, y va en un
        # día con gente publicada (si no, al abrir la tablet la descarta por redundante y la prueba no probaría nada).
        pend_anulada = {"obra": "olabeaga", "ambito": "vivienda", "fecha": "2026-10-22", "presentes": [{"nombre": "Ana", "horas": 3, "extra": 0}],
                        "anulada": True, "notas": "", "registrado": "2026-10-22T10:00:00.000Z"}
        pend_valida = {"obra": "olabeaga", "ambito": "vivienda", "fecha": "2026-10-21", "presentes": [{"nombre": "Ana", "horas": 9, "extra": 1.5}],
                       "anulada": False, "notas": "", "registrado": "2026-10-21T10:00:00.000Z"}
        t = Tablet(self.browser, estado_horas(), guardado={"sgd_personal_pendientes": [pend_anulada]}).ir()
        try:
            self.assertEqual(8, self.uh(t, "Ana"), "una jornada ANULADA sin enviar (3 h el 22/10) no cuenta: sigue el 20/10 (8 h)")
        finally:
            t.cerrar()
        t = Tablet(self.browser, estado_horas(), guardado={"sgd_personal_pendientes": [pend_anulada, pend_valida]}).ir()
        try:
            self.assertEqual(9, self.uh(t, "Ana"), "una jornada sin enviar vale más que lo publicado de antes (9 h el 21/10 frente a 8 h el 20/10)")
        finally:
            t.cerrar()

    def test_buscar_por_horas_encuentra_a_quien_trabajo_esas_horas_la_ultima_vez(self):
        t = Tablet(self.browser, estado_horas()).ir()
        try:
            def quien(filtro):
                html = t.pg.evaluate("f => opcionesHTML(f, 'horas')", filtro)
                return [n for n in ("Ana", "Beto", "Carla", "Dani", "Eli", "Fran") if 'value="%s"' % n in html]
            self.assertEqual(["Ana"], quien("8"), "«8» solo lo recuerda Ana (su última jornada fue de 8 h)")
            self.assertEqual(["Beto"], quien("4"), "«4» solo lo recuerda Beto (Mungia, 4 h)")
            self.assertEqual([], quien("9"), "«9» solo está en Fran en OTRA obra: no vale, porque Fran tiene jornada en esta")
        finally:
            t.cerrar()

    def test_guardar_una_jornada_recuerda_las_horas_de_cada_persona(self):
        t = Tablet(self.browser, estado_horas()).ir()
        try:
            t.marcar("Ana")
            t.marcar("Beto")
            self.assertEqual(["Ana", "Beto"], sorted(t.marcados()))
            t.pulsar("Ana", 3, "-0.5")
            self.assertEqual("6", t.horas_de("Ana").replace(" h", "").replace(",", ".").replace(".0", ""), "Ana se ha dejado en 6 h")
            self.assertIsNone(t.ls("ultimas_horas"), "antes de guardar no se ha recordado nada")
            t.pg.click("button[data-guardar]")
            t.pg.wait_for_selector("#toast")
            ultimas = t.ls("ultimas_horas")
            self.assertEqual({"ana": 6, "beto": 7.5}, ultimas, "al guardar se recuerdan las horas de cada una (Ana 6; Beto, las de su horario del viernes, 7,5)")
            # y se nota: sin tocar nada más, la búsqueda por horas ya encuentra a Ana por las 6 h de hoy
            self.assertIn('value="Ana"', t.pg.evaluate("() => opcionesHTML('6', 'horas')"))
            self.assertEqual([], t.errores)
        finally:
            t.cerrar()

    def test_guardar_no_recuerda_las_horas_de_quien_no_estaba_marcado(self):
        t = Tablet(self.browser, estado_horas()).ir()
        try:
            t.marcar("Ana")
            t.pg.click("button[data-guardar]")
            t.pg.wait_for_selector("#toast")
            self.assertEqual({"ana": 7.5}, t.ls("ultimas_horas"), "solo se recuerda a quien se guardó")
        finally:
            t.cerrar()


@unittest.skipUnless(_OK, "NO se ha comprobado la tablet en el navegador: %s" % _MOTIVO)
class TestAnadirAlguienQueYaEstabaEnLaLista(unittest.TestCase):
    """`addName` con una persona que ya sale en la lista: se marca y vuelve a las horas de su horario de ese día."""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def estado(self):
        catalogo = [D.ficha(1, "Ana"), D.ficha(2, "Beto")]
        ola = D.obra(OLA, [D.fila("2026-10-22", "vivienda", "Ana", 7.5), D.fila("2026-10-22", "vivienda", "Beto", 7.5)])
        e = D.estado(catalogo, {"olabeaga": ola})
        e["obras"]["olabeaga"]["ultima"] = {"vivienda": {"fecha": "2026-10-22", "presentes": [
            {"nombre": "Ana", "horas": 7.5, "extra": 0}, {"nombre": "Beto", "horas": 7.5, "extra": 0}]}, "garaje": None}
        return e

    def test_volver_a_escribir_a_alguien_de_la_lista_le_devuelve_las_horas_del_dia(self):
        t = Tablet(self.browser, self.estado()).ir()
        try:
            self.assertIn("Ana", t.pg.eval_on_selector_all("#v-app .row", "e=>e.map(r=>r.dataset.nombre)"), "Ana sale en la lista (jornada anterior)")
            t.pg.click('#v-app .row[data-nombre="Ana"] .x')
            t.pulsar("Ana", 3, "-0.5")
            self.assertEqual("6", t.horas_de("Ana").replace(" h", "").replace(",", ".").replace(".0", ""), "Ana se deja en 6 h")
            t.pg.click('#v-app .row[data-nombre="Ana"] .x')          # la desmarca (queda en la lista con 6 h)
            self.assertNotIn("Ana", t.marcados())
            t.pg.fill("#nuevo", "ana")
            t.pg.click("button[data-nuevo]")
            self.assertIn("Ana", t.marcados(), "escribir su nombre la vuelve a marcar")
            self.assertEqual(1, t.pg.eval_on_selector_all('#v-app .row[data-nombre="Ana"]', "e=>e.length"), "y no se duplica en la lista")
            self.assertEqual("7,5", t.horas_de("Ana").replace(" h", ""), "con las horas de su horario del viernes (7,5), no con las 6 de antes")
        finally:
            t.cerrar()


@unittest.skipUnless(_OK, "NO se ha comprobado la tablet en el navegador: %s" % _MOTIVO)
class TestElFicheroQueSaleDeLaTablet(unittest.TestCase):
    """`armarFichero`: lo que viaja en el fichero, campo a campo, comparado con lo que se hizo en la pantalla."""

    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def fichero(self, t, obra="olabeaga"):
        """Pulsa «Preparar el fichero para el PC» de esa obra y devuelve (nombre de la descarga, contenido ya leído)."""
        t.pg.click('nav button[data-v="enviar"]')
        with t.pg.expect_download(timeout=5000) as d:
            t.pg.click('button[data-preparar="%s"]' % obra)
        ruta = t.dir / "descarga.json"
        d.value.save_as(str(ruta))
        return d.value.suggested_filename, json.loads(ruta.read_text(encoding="utf-8"))

    def test_el_horario_semanal_viaja_dia_a_dia_y_en_su_sitio(self):
        t = Tablet(self.browser, estado_horas()).ir()
        try:
            # data-hor: 1 = lunes … 6 = sábado, 0 = domingo. Un valor distinto por día: si dos se cruzan, se nota.
            t.pg.click("#horario summary")
            for dia, horas in (("1", "8"), ("2", "7"), ("3", "6.5"), ("4", "6"), ("5", "5"), ("6", "4"), ("0", "3")):
                t.pg.fill('input[data-hor="%s"]' % dia, horas)
                t.pg.dispatch_event('input[data-hor="%s"]' % dia, "change")
            nombre, lote = self.fichero(t)
            self.assertEqual({"lun": 8, "mar": 7, "mie": 6.5, "jue": 6, "vie": 5, "sab": 4, "dom": 3}, lote.get("horario_semanal"),
                             "cada día va con SUS horas (sábado 4, domingo 3)")
            self.assertEqual("olabeaga", lote["obra"])
            self.assertTrue(nombre.startswith("CONTROL HORARIO ") and nombre.endswith(".json"), nombre)
        finally:
            t.cerrar()

    def test_todo_lo_que_hay_sin_enviar_viaja_cada_cosa_en_su_campo_y_en_su_orden(self):
        normal = {"obra": "olabeaga", "ambito": "vivienda", "fecha": "2026-10-21", "presentes": [{"nombre": "Ana", "horas": 9, "extra": 1.5}],
                  "anulada": False, "notas": "", "registrado": "2026-10-21T10:00:00.000Z"}
        guardado = {
            "sgd_personal_pendientes": [normal],
            "sgd_personal_renombres": [{"de": "Ana", "a": "Anna"}],
            "sgd_personal_altas": ["Zeta"],
            "sgd_personal_empresas": [{"nombre": "Zeta", "empresa": "Alfa Instalaciones"}, {"nombre": "Yeti", "empresa": "Beta Montajes"}],
            "sgd_personal_excepciones": {"olabeaga": {"Beto": {"vie": 6}}},
        }
        t = Tablet(self.browser, estado_horas(), guardado=guardado).ir()
        try:
            _, lote = self.fichero(t)
            self.assertEqual(
                ["tipo", "version", "obra", "excepciones_horario", "renombres", "altas", "empresas", "jornadas"], list(lote),
                "los campos van todos y en el orden de siempre (sin horario semanal: no se tocó)")
            self.assertEqual({"Beto": {"vie": 6}}, lote["excepciones_horario"], "el horario propio de Beto")
            self.assertEqual([{"de": "Ana", "a": "Anna"}], lote["renombres"], "el nombre corregido: de Ana a Anna, no al revés")
            self.assertEqual(["Zeta", "Yeti"], lote["altas"],
                             "los nombres nuevos: el apuntado (Zeta) y el que solo tenía empresa apuntada (Yeti), porque el PC pone las empresas después de los nombres")
            self.assertEqual([{"nombre": "Zeta", "empresa": "Alfa Instalaciones"}, {"nombre": "Yeti", "empresa": "Beta Montajes"}], lote["empresas"])
            self.assertEqual(1, len(lote["jornadas"]))
        finally:
            t.cerrar()

    def test_una_jornada_anulada_viaja_sin_gente_aunque_la_conserve_en_el_aparato(self):
        anulada = {"obra": "olabeaga", "ambito": "vivienda", "fecha": "2026-10-22", "presentes": [{"nombre": "Ana", "horas": 3, "extra": 0}],
                   "anulada": True, "notas": "obra parada", "registrado": "2026-10-22T10:00:00.000Z"}
        normal = {"obra": "olabeaga", "ambito": "vivienda", "fecha": "2026-10-21", "presentes": [{"nombre": "Ana", "horas": 9, "extra": 1.5}],
                  "anulada": False, "notas": "", "registrado": "2026-10-21T10:00:00.000Z"}
        t = Tablet(self.browser, estado_horas(), guardado={"sgd_personal_pendientes": [anulada, normal]}).ir()
        try:
            _, lote = self.fichero(t)
            por_fecha = {j["fecha"]: j for j in lote["jornadas"]}
            self.assertEqual(["2026-10-21", "2026-10-22"], sorted(por_fecha))
            self.assertEqual({"ambito": "vivienda", "fecha": "2026-10-22", "presentes": [], "anulada": True, "notas": "obra parada",
                              "registrado": "2026-10-22T10:00:00.000Z"}, por_fecha["2026-10-22"], "la anulada: sin gente, anulada y con su nota y su fecha de registro")
            self.assertEqual({"ambito": "vivienda", "fecha": "2026-10-21", "presentes": [{"nombre": "Ana", "horas": 9, "extra": 1.5}], "anulada": False,
                              "notas": "", "registrado": "2026-10-21T10:00:00.000Z"}, por_fecha["2026-10-21"], "la normal: con su gente, horas y extra")
        finally:
            t.cerrar()


@unittest.skipUnless(_OK, "NO se ha comprobado «Generar personal» en el navegador: %s" % _MOTIVO)
class TestGenerarPersonalAvisosAntesDePreparar(unittest.TestCase):
    """`intentarAnadirTrabajadores`: lo que no se puede publicar o no está completo se frena con su aviso y no prepara NADA."""

    def frena(self, hacer, texto_aviso):
        def escena(page, carpeta):
            hacer(page)
            self.assertIn(texto_aviso, AG.texto(page, "#gen-error"), "el aviso dice qué falta")
            self.assertEqual([], AG.filas(page), "y no se ha preparado nada")
        self.assertEqual([], AG.con_pagina(escena))

    def test_empresa_nueva_sin_escribir_su_nombre(self):
        self.frena(lambda p: AG.anadir(p, "Zeta", "__nueva__"), "Escribe el nombre de la empresa nueva o elige otra del desplegable.")

    def test_empresa_que_parece_un_correo(self):
        def hacer(p):
            p.select_option("#gen-empresa", "__nueva__")
            p.fill("#gen-empresa-nueva", "info@empresa.es")
            p.fill("#gen-nombre", "Zeta")
            p.click("#btn-gen-anadir")
        self.frena(hacer, "parece un DNI, un teléfono o un correo")

    def test_nombre_que_parece_un_telefono(self):
        self.frena(lambda p: AG.anadir(p, "Zeta 944123456", AG.ALFA), "parece un DNI, un teléfono o un correo")

    def test_una_pregunta_sin_contestar_se_quita_cuando_se_intenta_otra_cosa(self):
        def escena(page, carpeta):
            AG.anadir(page, "Rafa", AG.BETA)                    # Rafa está en Alfa: pregunta «¿es el mismo?»
            self.assertIsNotNone(page.query_selector("#gen-pregunta"), "sale la pregunta")
            # sin contestarla, cambia solo el nombre (si tocara un desplegable la pregunta se quitaría por otro camino) por uno que no vale
            page.fill("#gen-nombre", "Zeta 944123456")
            page.click("#btn-gen-anadir")
            self.assertIn("parece un DNI", AG.texto(page, "#gen-error"))
            self.assertIsNone(page.query_selector("#gen-pregunta"), "la pregunta vieja ya no está: ni se contesta ni queda colgada")
            self.assertEqual([], AG.filas(page))
        self.assertEqual([], AG.con_pagina(escena))

    def test_varios_con_un_nombre_que_parece_un_telefono(self):
        def escena(page, carpeta):
            page.click('[data-gen-modo="varios"]')
            page.select_option("#gen-empresa", AG.ALFA)
            page.fill('[data-gen-var-nom="0"]', "Zeta 944123456")
            page.click("#btn-gen-anadir")
            self.assertIn("parece un DNI, un teléfono o un correo", AG.texto(page, "#gen-error"))
            self.assertIn("«Zeta 944123456»", AG.texto(page, "#gen-error"), "dice cuál es el nombre que no vale")
            self.assertEqual([], AG.filas(page))
        self.assertEqual([], AG.con_pagina(escena))

    def test_quien_ya_esta_en_la_base_no_avisa_de_parecido_con_otro_de_la_base(self):
        """«Marta» y «Marti» están los dos en la base y se parecen entre sí: añadir cambios a Marta no es crear a nadie nuevo."""
        fichas = [D.ficha(1, "Marta", AG.ALFA), D.ficha(2, "Marti", AG.ALFA)]

        def escena(page, carpeta):
            AG.anadir(page, "Marta", AG.ALFA, oficio="Oficial 2ª")
            self.assertIsNone(page.query_selector("#gen-aviso-parecido"), "no avisa: Marta ya está en la base")
            self.assertEqual(["Marta"], [f[0] for f in AG.filas(page)])
        self.assertEqual([], AG.con_pagina(escena, e=AG.estado(fichas=fichas)))

    def test_varios_con_todas_las_casillas_de_nombre_vacias(self):
        def hacer(p):
            p.click('[data-gen-modo="varios"]')
            p.click("#btn-gen-anadir")
        self.frena(hacer, "Escribe al menos el nombre de un trabajador en la lista.")

    def test_oficio_que_parece_un_correo(self):
        def hacer(p):
            p.select_option("#gen-empresa", AG.ALFA)
            p.fill("#gen-nombre", "Zeta")
            p.select_option("#gen-categoria", "__otra__")
            p.fill("#gen-categoria-otra", "a@b.es")
            p.click("#btn-gen-anadir")
        self.frena(hacer, "el oficio o categoría")

    def test_un_nombre_que_ya_esta_se_aplica_a_esa_persona_aunque_se_escriba_distinto(self):
        def escena(page, carpeta):
            AG.anadir(page, "  rAFA ", AG.ALFA, oficio="Oficial 2ª")      # es Rafa, con otras mayúsculas y espacios de más
            self.assertEqual(["Rafa"], [f[0] for f in AG.filas(page)], "queda preparado con el nombre EXACTO de la base")
            _, f = AG.descargar(page)
            self.assertEqual([{"nombre": "Rafa", "categoria": "Oficial 2ª"}], f["categorias"])
            self.assertNotIn("altas", f, "no es nadie nuevo")
        self.assertEqual([], AG.con_pagina(escena))


@unittest.skipUnless(_OK, "NO se ha comprobado «Generar personal» en el navegador: %s" % _MOTIVO)
class TestGenerarPersonalAnadirIgualmente(unittest.TestCase):
    """Un nombre parecido a otro de la base frena con un aviso; «Añadir igualmente» tiene que dejar pasar, y «No añadir», no."""

    def preparar(self, page):
        AG.anadir(page, "Rafaa", AG.ALFA)       # parecido a «Rafa»
        page.wait_for_selector("#gen-aviso-parecido")

    def test_el_aviso_frena_y_anadir_igualmente_deja_pasar(self):
        def escena(page, carpeta):
            self.preparar(page)
            self.assertIn("«Rafaa» se parece a «Rafa»", AG.texto(page, "#gen-aviso-parecido"))
            self.assertEqual([], AG.filas(page), "mientras no responde no se ha preparado nada")
            page.click("#btn-gen-confirmar-parecido")
            self.assertIsNone(page.query_selector("#gen-aviso-parecido"), "tras confirmar ya no queda el aviso")
            self.assertEqual(1, len(AG.filas(page)), "queda UNA persona preparada")
            self.assertIn("Rafaa", AG.filas(page)[0][1])
        errores = AG.con_pagina(escena)
        self.assertEqual([], errores)

    def test_no_anadir_descarta_el_nombre_sin_preparar_nada(self):
        def escena(page, carpeta):
            self.preparar(page)
            page.click("#btn-gen-cancelar-parecido")
            self.assertIsNone(page.query_selector("#gen-aviso-parecido"))
            self.assertEqual([], AG.filas(page), "no se ha preparado nada")
        self.assertEqual([], AG.con_pagina(escena))


@unittest.skipUnless(_OK, "NO se ha comprobado «Generar personal» en el navegador: %s" % _MOTIVO)
class TestElFicheroQueSaleDeGenerarPersonal(unittest.TestCase):
    """`descargarFicheroControlHorario`: nombre, forma y contenido exactos del `BASE TRABAJADORES SAGARDE <DDMMAAAA>.json`."""

    def test_sin_nada_preparado_no_hay_boton_para_descargar(self):
        """Por eso la guarda «lista vacía» de la función es inalcanzable desde la pantalla (mutante d09 equivalente)."""
        def escena(page, carpeta):
            self.assertIsNone(page.query_selector("#btn-gen-descargar"))
            AG.anadir(page, "Zeta", AG.ALFA)
            self.assertIsNotNone(page.query_selector("#btn-gen-descargar"))
        self.assertEqual([], AG.con_pagina(escena))

    def test_nombre_y_contenido_exactos(self):
        esperado = {
            "tipo": "lote_personal", "version": 1, "obra": "sagarde", "jornadas": [], "dispositivo": "Personal Sagarde PC",
            "altas": ["Zeta"], "bajas": ["Luis"],
            "empresas": [{"nombre": "Zeta", "empresa": AG.ALFA}],
            "categorias": [{"nombre": "Zeta", "categoria": "Oficial 2ª"}],
            "horarios_preferidos": {"Zeta": {"lun": 8, "mar": 8, "mie": 8, "jue": 8, "vie": 8, "sab": 0, "dom": 0}},
        }

        def escena(page, carpeta):
            AG.anadir(page, "Zeta", AG.ALFA, oficio="Oficial 2ª", horario="8h")
            page.select_option("#gen-empresa", AG.BETA)
            page.click('[data-gen-baja="Luis"]')
            with page.expect_download() as d:
                page.click("#btn-gen-descargar")
            self.assertEqual("BASE TRABAJADORES SAGARDE 23102026.json", d.value.suggested_filename,
                             "el día, el mes (octubre = 10, no 09) y el año con cuatro cifras, con el reloj en el 23/10/2026")
            texto = Path(d.value.path()).read_text(encoding="utf-8")
            self.assertEqual(esperado, json.loads(texto))
            self.assertEqual(json.dumps(esperado, indent=2, ensure_ascii=False) + chr(10), texto,
                             "mismo orden de campos, sangría de 2 espacios y salto de línea al final (como el resto de ficheros)")
            self.assertIn("23102026", AG.texto(page, "#gen-fichero-guardado"), "el recuadro «Fichero guardado» dice el nombre exacto")
        self.assertEqual([], AG.con_pagina(escena, init=FECHA_FIJA))


if __name__ == "__main__":
    unittest.main()
