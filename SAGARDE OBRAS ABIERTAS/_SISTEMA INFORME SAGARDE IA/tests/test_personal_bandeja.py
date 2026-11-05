# -*- coding: utf-8 -*-
"""Pestaña «Bandeja» de la app de jornada (generador_personal.html): ver TODO lo que está sin enviar al PC y quitarlo.

Nace el 05/11/2026 de dos casos reales de Bixente: (1) en el PC la lista «Enviar al PC» no se vaciaba porque las jornadas
apuntadas con nombres antiguos nunca coinciden con lo que el PC ya tiene; (2) en la tablet quedaban dos jornadas de garaje de
Bolueta mal apuntadas y no había dónde quitarlas. «Quitar» solo borra de este aparato: no manda nada al PC.

Chromium de verdad (Playwright), datos INVENTADOS (Ana, Beto, Carla…), la app y sus datos copiados a una carpeta temporal.
P3_APP apunta a otra copia de la app (para las mutaciones: se rompe una COPIA, nunca el original). Se SALTA, diciendo por qué,
si no hay Chromium; SAGARDE_SIN_NAVEGADOR=1 la salta a propósito."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from ayudante_generar import hay_chromium

TESTS = Path(__file__).resolve().parent
APP_DIR = Path(os.environ.get("P3_APP") or TESTS.parent)
TMP_BASE = Path(os.environ.get("P3_TMP") or tempfile.gettempdir())
_OK, _MOTIVO = hay_chromium()

H7 = {"lun": 7.5, "mar": 7.5, "mie": 7.5, "jue": 7.5, "vie": 7.5, "sab": 0, "dom": 0}
H8 = {"lun": 8, "mar": 8, "mie": 8, "jue": 8, "vie": 8}


def fila(fecha, ambito, nombre, horas=8, empresa="Uno"):
    return {"fecha": fecha, "ambito": ambito, "nombre": nombre, "horas": horas, "extra": 0, "empresa": empresa}


def persona(i, nombre, empresa="Uno", antes=None):
    d = {"id": "T%04d" % i, "nombre": nombre, "categoria": "", "empresa": empresa, "activo": True}
    if antes:
        d["nombres_anteriores"] = antes
    return d


ESTADO = {
    "version": 1,
    "generado": "2026-11-05T12:00:00+01:00",
    "jornada_base_h": 7.5,
    "catalogo": [persona(1, "Ana", antes=["Ana @ Uno"]), persona(2, "Beto"), persona(3, "Carla"), persona(4, "Zeta")],
    "obras": {
        "obra1": {"nombre": "2026 OBRA UNO", "cerrada": False, "horario_semanal": H7, "excepciones_horario": {}, "ultima": {},
                  "jornadas": [fila("2026-10-20", "vivienda", "Ana"), fila("2026-10-20", "vivienda", "Beto")]},
        "obra2": {"nombre": "2026 OBRA DOS", "cerrada": False, "horario_semanal": H7, "excepciones_horario": {}, "ultima": {},
                  "jornadas": [fila("2026-10-21", "garaje", "Carla")]},
    },
}


def jornada(obra, ambito, fecha, nombres, horas=8, anulada=False):
    return {"obra": obra, "ambito": ambito, "fecha": fecha, "anulada": anulada, "notas": "",
            "presentes": [] if anulada else [{"nombre": n, "horas": horas, "extra": 0} for n in nombres],
            "registrado": "2026-11-05T09:00:00.000Z"}


# Lo que hay sin enviar en el aparato de la prueba. J1 lleva nombres ANTIGUOS (el caso real): el PC ya tiene lo mismo.
SEMILLA = {
    "pendientes": [
        jornada("obra1", "vivienda", "2026-10-20", ["Ana @ Uno", "Beto"]),   # J1: igual que el PC, con nombre antiguo
        jornada("obra1", "garaje", "2026-11-04", ["Beto"], horas=9),        # J2: el PC no tiene nada de ese día
        jornada("obra2", "garaje", "2026-10-21", [], anulada=True),         # J3: anulada; el PC SÍ tiene gente ese día
        jornada("obra1", "vivienda", "2026-11-05", ["Fran"]),               # J4: la lleva el nombre nuevo «Fran»
    ],
    "excepciones": {"obra1": {"Ana @ Uno": H8, "Beto": H8}},
    "horarios": {"obra2": [0, 8, 8, 8, 8, 8, 0]},
    "renombres": [{"de": "Chico 1", "a": "Ana @ Uno"}, {"de": "Zeta", "a": "Zeta Nuevo"}],
    "altas": ["Elena", "Fran"],
    "nuevos": ["Elena", "Fran"],
    "empresas": [{"nombre": "Elena", "empresa": "Uno"}, {"nombre": "Beto", "empresa": "Dos"}],
}
OTRAS = {"borrador": {"control": "no tocar"}}  # algo ajeno a la bandeja que NUNCA debe borrarse


def _semilla_js(claves):
    sets = "".join(
        "localStorage.setItem(%s,%s);" % (json.dumps("sgd_personal_" + k), json.dumps(json.dumps(v))) for k, v in claves.items()
    )
    # solo la primera vez de cada pestaña: una recarga NO vuelve a sembrar (lo guardado manda)
    return "if(!sessionStorage.getItem('__sembrado')){%ssessionStorage.setItem('__sembrado','1');}" % sets


@unittest.skipUnless(_OK, "NO se ha probado la pestaña «Bandeja»: %s" % _MOTIVO)
class TestBandeja(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright

        cls.dir = Path(tempfile.mkdtemp(prefix="bandeja_", dir=str(TMP_BASE)))
        for nombre in ("generador_personal.html", "personal_calculo.js"):
            shutil.copy(APP_DIR / nombre, cls.dir / nombre)
        (cls.dir / "personal_estado.js").write_text("window.SAGARDE_PERSONAL = %s;\n" % json.dumps(ESTADO), encoding="utf-8")
        cls.url = (cls.dir / "generador_personal.html").as_uri()
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        shutil.rmtree(cls.dir, ignore_errors=True)

    def abrir(self, semilla=None, ancho=900, alto=900):
        ctx = self.browser.new_context(viewport={"width": ancho, "height": alto}, accept_downloads=True)
        self.addCleanup(ctx.close)
        ctx.add_init_script(_semilla_js(dict(OTRAS, **(SEMILLA if semilla is None else semilla))))
        page = ctx.new_page()
        page.set_default_timeout(6000)  # si algo no existe, que falle pronto
        self.errores = []
        page.on("pageerror", lambda e: self.errores.append(str(e)))
        self.descargas = []
        page.on("download", lambda d: self.descargas.append(d.suggested_filename))
        page.goto(self.url)
        page.wait_for_function("window.__pub === 1 && document.querySelector('.seg button.on')")
        return page

    def bandeja(self, **kw):
        page = self.abrir(**kw)
        page.click('button[data-v="bandeja"]')
        page.wait_for_selector("#v-bandeja:not([hidden])")
        return page

    def ls(self, page, clave):
        return json.loads(page.evaluate("(k) => localStorage.getItem('sgd_personal_' + k)", clave) or "null")

    def texto(self, page):
        return page.inner_text("#v-bandeja")

    def quitar(self, page, tipo, **attrs):
        sel = 'button[data-quitar="%s"]' % tipo + "".join('[data-%s="%s"]' % (k, v) for k, v in attrs.items())
        page.click(sel)

    # ───────────────────────────────── la pestaña ─────────────────────────────────
    def test_la_pestana_es_la_ultima_de_la_barra(self):
        page = self.abrir()
        botones = page.eval_on_selector_all(".tabs .seg button", "bs => bs.map(b => [b.dataset.v, b.innerText.trim()])")
        self.assertEqual(["app", "jornadas", "informe", "enviar", "bandeja"], [b[0] for b in botones])
        self.assertEqual("Bandeja", botones[-1][1])
        self.assertEqual([], self.errores)

    def test_la_bandeja_no_usa_la_clase_de_la_pantalla_enviar(self):
        # Las escenas de «Enviar al PC» buscan «.envio[data-obra] li» en TODA la página: si la Bandeja usara esa clase, sus
        # líneas (y sus botones «Quitar») se colarían en esas cuentas (pasó el 05/11/2026 y rompió la escena T93).
        page = self.bandeja()
        self.assertEqual(0, page.locator("#v-bandeja .envio").count())
        self.assertEqual(0, page.locator(".envio[data-obra] li:has(button[data-quitar])").count())

    def test_vacia_dice_que_esta_vacia_y_no_ofrece_nada_que_quitar(self):
        page = self.bandeja(semilla={})
        self.assertIn("La bandeja está vacía", page.inner_text("#bandeja-vacia"))
        self.assertEqual(0, page.locator('#v-bandeja button[data-quitar]').count())
        self.assertEqual(0, page.locator('#v-bandeja button[data-vaciar]').count())

    def test_enseña_todo_lo_que_hay_sin_enviar_y_marca_lo_que_el_pc_ya_tiene(self):
        page = self.bandeja()
        t = self.texto(page)
        for esperado in ("2026 OBRA UNO", "2026 OBRA DOS", "Ana @ Uno", "Horario especial", "Cambio del horario semanal",
                         "«Chico 1» → «Ana @ Uno»", "Nombre nuevo: «Elena»", "Nombre nuevo: «Fran»",
                         "Empresa de «Beto»: «Dos»", "Empresa de «Elena»: «Uno»"):
            self.assertIn(esperado, t, esperado)
        self.assertEqual(4, page.locator('li[data-tipo="jornada"]').count())
        # El PC ya tiene la J1 igual aunque lleve el nombre antiguo («Ana @ Uno» = «Ana»): solo esa lleva la marca.
        marcadas = page.eval_on_selector_all('li[data-tipo="jornada"]:has(.band-igual)', "ls => ls.map(l => l.innerText)")
        self.assertEqual(1, len(marcadas), marcadas)
        self.assertIn("Ana @ Uno", marcadas[0])
        self.assertIn("El PC ya tiene esto igual", marcadas[0])
        self.assertEqual([], self.errores)

    # ───────────────────────────────── quitar una a una ─────────────────────────────────
    def test_quitar_una_jornada_la_borra_del_aparato_y_no_toca_las_demas(self):
        page = self.bandeja()
        self.quitar(page, "jornada", clave="obra1|garaje|2026-11-04")
        antes = {"obra1|vivienda|2026-10-20", "obra2|garaje|2026-10-21", "obra1|vivienda|2026-11-05"}
        ahora = {"%s|%s|%s" % (j["obra"], j["ambito"], j["fecha"]) for j in self.ls(page, "pendientes")}
        self.assertEqual(antes, ahora)
        self.assertEqual(3, page.locator('li[data-tipo="jornada"]').count())
        # sigue quitado tras recargar (se guardó de verdad) y la pantalla «Enviar al PC» lo refleja
        page.reload()
        page.wait_for_function("window.__pub === 1 && document.querySelector('.seg button.on')")
        self.assertEqual(antes, {"%s|%s|%s" % (j["obra"], j["ambito"], j["fecha"]) for j in self.ls(page, "pendientes")})
        page.click('button[data-v="enviar"]')
        self.assertIn("Tienes 3 jornadas sin enviar", page.inner_text("#resumen-envio"))

    def test_quitar_no_manda_nada_ni_crea_anulaciones(self):
        page = self.bandeja()
        n = len(self.ls(page, "pendientes"))
        self.quitar(page, "jornada", clave="obra1|garaje|2026-11-04")
        self.assertEqual(n - 1, len(self.ls(page, "pendientes")))  # no se añade ninguna jornada anulada
        self.assertEqual([], self.descargas)
        self.assertEqual(0, sum(1 for j in self.ls(page, "pendientes") if j["fecha"] == "2026-11-04"))

    def test_quitar_un_horario_especial_deja_los_otros(self):
        page = self.bandeja()
        self.quitar(page, "horario", obra="obra1", nombre="Beto")
        self.assertEqual({"obra1": {"Ana @ Uno": H8}}, self.ls(page, "excepciones"))
        self.assertNotIn("Horario especial: Beto", self.texto(page))

    def test_quitar_el_ultimo_horario_especial_de_una_obra_quita_la_obra(self):
        page = self.bandeja()
        self.quitar(page, "horario", obra="obra1", nombre="Beto")
        self.quitar(page, "horario", obra="obra1", nombre="Ana @ Uno")
        self.assertEqual({}, self.ls(page, "excepciones"))

    def test_quitar_el_cambio_de_horario_de_la_obra(self):
        page = self.bandeja()
        self.quitar(page, "horario-obra", obra="obra2")
        self.assertEqual({}, self.ls(page, "horarios"))
        self.assertNotIn("Cambio del horario semanal", self.texto(page))

    def test_quitar_una_empresa_apuntada(self):
        page = self.bandeja()
        self.quitar(page, "empresa", nombre="Beto")
        self.assertEqual([{"nombre": "Elena", "empresa": "Uno"}], self.ls(page, "empresas"))

    # ───────────────────────── lo que lleva otra cosa no se quita a medias ─────────────────────────
    def test_un_nombre_corregido_que_llevan_jornadas_no_se_puede_quitar_hasta_quitarlas(self):
        page = self.bandeja()
        boton = page.locator('button[data-quitar="renombre"][data-a="Ana @ Uno"]')
        self.assertTrue(boton.is_disabled())
        self.assertIn("primero", self.texto(page))  # dice por qué no se puede y qué quitar antes
        # el otro cambio de nombre, que nadie lleva, sí se quita
        self.quitar(page, "renombre", a="Zeta Nuevo")
        self.assertEqual([{"de": "Chico 1", "a": "Ana @ Uno"}], self.ls(page, "renombres"))
        # quitando lo que lo lleva (jornada J1 y su horario especial) ya se puede
        self.quitar(page, "jornada", clave="obra1|vivienda|2026-10-20")
        self.quitar(page, "horario", obra="obra1", nombre="Ana @ Uno")
        self.assertFalse(page.locator('button[data-quitar="renombre"][data-a="Ana @ Uno"]').is_disabled())
        self.quitar(page, "renombre", a="Ana @ Uno")
        self.assertEqual([], self.ls(page, "renombres"))

    def test_un_nombre_nuevo_que_lleva_una_jornada_no_se_puede_quitar_y_el_libre_si(self):
        page = self.bandeja()
        self.assertTrue(page.locator('button[data-quitar="alta"][data-nombre="Fran"]').is_disabled())
        self.quitar(page, "alta", nombre="Elena")
        self.assertEqual(["Fran"], self.ls(page, "altas"))
        self.assertEqual(["Fran"], self.ls(page, "nuevos"))
        # su empresa apuntada se va con el nombre; la de Beto se queda
        self.assertEqual([{"nombre": "Beto", "empresa": "Dos"}], self.ls(page, "empresas"))
        self.quitar(page, "jornada", clave="obra1|vivienda|2026-11-05")
        self.assertFalse(page.locator('button[data-quitar="alta"][data-nombre="Fran"]').is_disabled())

    # ───────────────────────────────── vaciar todo ─────────────────────────────────
    def test_vaciar_pide_confirmacion_y_si_se_dice_que_no_no_borra_nada(self):
        page = self.bandeja()
        page.click("button[data-vaciar]")
        self.assertIn("¿Vaciar toda la bandeja?", page.inner_text("#band-confirmar"))
        page.click("button[data-vaciar-no]")
        self.assertEqual(4, len(self.ls(page, "pendientes")))
        self.assertEqual(0, page.locator("#band-confirmar").count())

    def test_vaciar_borra_solo_la_bandeja_y_deja_lo_demas(self):
        page = self.bandeja()
        estado_antes = page.evaluate("localStorage.getItem('sgd_personal_estado')")
        page.click("button[data-vaciar]")
        page.click("button[data-vaciar-si]")
        for clave, vacio in (("pendientes", []), ("horarios", {}), ("excepciones", {}), ("renombres", []), ("altas", []),
                             ("empresas", []), ("nuevos", [])):
            self.assertEqual(vacio, self.ls(page, clave), clave)
        self.assertEqual({"control": "no tocar"}, self.ls(page, "borrador"))
        self.assertEqual(estado_antes, page.evaluate("localStorage.getItem('sgd_personal_estado')"))
        self.assertIn("La bandeja está vacía", page.inner_text("#bandeja-vacia"))
        self.assertEqual([], self.descargas)
        page.click('button[data-v="enviar"]')
        self.assertIn("No hay nada por enviar", page.inner_text("#nada-que-enviar"))
        self.assertEqual([], self.errores)

    # ───────────────────────────────── cómo se ve ─────────────────────────────────
    def test_el_texto_va_en_lenguaje_de_electricista(self):
        import test_lenguaje_electricista as lenguaje

        page = self.bandeja()
        textos = [self.texto(page)]
        page.click("button[data-vaciar]")
        textos.append(self.texto(page))
        page.click("button[data-vaciar-si]")
        textos.append(self.texto(page))
        problemas = lenguaje.revisar(textos, "Bandeja")
        self.assertEqual([], problemas)

    def test_cinco_pestañas_caben_en_el_movil_y_en_la_tablet(self):
        for ancho in (360, 390, 768):
            page = self.abrir(ancho=ancho, alto=800)
            r = page.evaluate(
                """() => ({ pagina: document.documentElement.scrollWidth <= window.innerWidth,
                   botones: [...document.querySelectorAll('.tabs .seg button')].map(b => { const r = b.getBoundingClientRect();
                     return [b.dataset.v, Math.round(r.left), Math.round(r.right), Math.round(r.width)]; }), ancho: window.innerWidth })"""
            )
            self.assertTrue(r["pagina"], "la página se desborda a %d px" % ancho)
            for v, izq, der, w in r["botones"]:
                self.assertGreaterEqual(izq, 0, "%s a %d px" % (v, ancho))
                self.assertLessEqual(der, r["ancho"], "%s se sale por la derecha a %d px" % (v, ancho))
                self.assertGreater(w, 30, "%s demasiado estrecho a %d px" % (v, ancho))


if __name__ == "__main__":
    unittest.main()
