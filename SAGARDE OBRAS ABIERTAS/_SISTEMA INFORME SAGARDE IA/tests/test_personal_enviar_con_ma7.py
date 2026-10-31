# -*- coding: utf-8 -*-
"""MA7 · «Enviar con…» en la pantalla «Enviar al PC» de la tablet (generador_personal.html): el MISMO fichero por la hoja de compartir del aparato.

Dos partes, datos INVENTADOS y fecha fija 23/10/2026:
  1) La lógica pura (archivoParaCompartir, sabeCompartir, compartirFichero) se saca del HTML tal cual y se ejecuta con node contra los casos de
     abajo (sin soporte, canShare falso o que lanza, la hoja que acepta, la que se cancela, la que rechaza el tipo de fichero, errores raros).
  2) La pantalla, en Chromium de verdad, con `navigator.share` y `navigator.canShare` SIMULADOS (init script): acepta, cancela, rechaza,
     falla, sin soporte, nada que enviar, doble toque, tamaños de botón en seis anchos, y que el fichero compartido es, byte a byte, el que
     baja la descarga de siempre.
P3_APP apunta a otra copia de la app (para las mutaciones: se rompe una COPIA, nunca el original).
OJO (medido en la lista de Chromium, FILE_TYPES.md): Chrome NO admite el tipo .json en la hoja de compartir; allí `share()` rechaza con
NotAllowedError y la tablet avisa y esconde el botón 30 días. Lo que haga el aparato de Bixente se ve en la prueba de campo (MA8)."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

from ayudante_generar import hay_chromium
import test_personal_pantallas_ma6 as ma6

TESTS = Path(__file__).resolve().parent
APP_DIR = Path(os.environ.get("P3_APP") or TESTS.parent)
TMP_BASE = Path(os.environ.get("P3_TMP") or tempfile.gettempdir())

# ───────────────────────────── 1) la lógica pura, con node ─────────────────────────────
VERIFICADOR = r'''// Verificador OCULTO de la lógica de «Enviar con…» (MA7). Uso: node verif.js <ruta a compartir.js>
const fs = require('fs'), vm = require('vm');
const texto = fs.readFileSync(process.argv[2], 'utf8');
const ctx = { File };
vm.createContext(ctx);
try { vm.runInContext(texto + '\n;this.__f={archivoParaCompartir,sabeCompartir,compartirFichero};', ctx, { timeout: 5000 }); }
catch (e) { console.log('FALLO no se puede cargar el fichero: ' + e.message); process.exit(1); }
const { archivoParaCompartir, sabeCompartir, compartirFichero } = ctx.__f;
let fallos = 0, total = 0;
async function caso(nombre, f) {
  total++;
  try { const r = await f(); if (r !== true && r !== undefined) { fallos++; console.log('FALLO ' + nombre + ' -> ' + r); } }
  catch (e) { fallos++; console.log('FALLO ' + nombre + ' -> excepción: ' + e.message); }
}
const erra = (nombre, mensaje) => { const e = new Error(mensaje || nombre); e.name = nombre; return e; };
// Un navegador de mentira que apunta lo que le piden.
function nav(o) {
  o = o || {};
  const n = { llamadasCan: [], llamadasShare: [] };
  n.canShare = o.sinCan ? undefined : function (d) { n.llamadasCan.push(d); if (o.canLanza) throw erra('TypeError'); return o.can === undefined ? true : o.can; };
  n.share = o.sinShare ? undefined : function (d) {
    n.llamadasShare.push(d);
    if (o.shareLanza) throw erra(o.shareLanza);
    if (o.rechaza !== undefined) return Promise.reject(o.rechaza === 'raro' ? 'texto suelto' : o.rechaza === 'nada' ? undefined : erra(o.rechaza));
    return Promise.resolve();
  };
  return n;
}
const TXT = '{\n "tipo": "lote_personal",\n "obra": "olabeaga",\n "nota": "ñandú, año, «comillas»"\n}';
(async () => {
  await caso('archivo: nombre con .json, tipo application/json y el contenido tal cual', async () => {
    const f = archivoParaCompartir(File, 'CONTROL HORARIO X 23102026', TXT);
    if (f.name !== 'CONTROL HORARIO X 23102026.json') return 'nombre ' + f.name;
    if (f.type !== 'application/json') return 'tipo ' + f.type;
    if ((await f.text()) !== TXT) return 'contenido distinto';
    const b = Buffer.from(await f.arrayBuffer());
    if (!b.equals(Buffer.from(TXT, 'utf8'))) return 'bytes distintos de UTF-8 sin marca';
  });
  // sabeCompartir
  await caso('sabe: sin navegador', () => sabeCompartir(null, File, 'X') === false || 'dijo true');
  await caso('sabe: navegador sin share', () => sabeCompartir(nav({ sinShare: true }), File, 'X') === false || 'dijo true');
  await caso('sabe: navegador sin canShare', () => sabeCompartir(nav({ sinCan: true }), File, 'X') === false || 'dijo true');
  await caso('sabe: canShare dice que no', () => sabeCompartir(nav({ can: false }), File, 'X') === false || 'dijo true');
  await caso('sabe: canShare lanza', () => sabeCompartir(nav({ canLanza: true }), File, 'X') === false || 'dijo true');
  await caso('sabe: la clase File lanza', () => sabeCompartir(nav(), function () { throw new Error('no hay File'); }, 'X') === false || 'dijo true');
  await caso('sabe: canShare dice que sí', () => sabeCompartir(nav(), File, 'X') === true || 'dijo false');
  await caso('sabe: pregunta por UN fichero con el nombre y el tipo de la descarga, y solo por «files»', () => {
    const n = nav(); sabeCompartir(n, File, 'CONTROL HORARIO Y 01012027');
    if (n.llamadasCan.length !== 1) return 'llamó a canShare ' + n.llamadasCan.length + ' veces';
    const d = n.llamadasCan[0];
    if (JSON.stringify(Object.keys(d)) !== '["files"]') return 'claves ' + Object.keys(d);
    if (d.files.length !== 1 || d.files[0].name !== 'CONTROL HORARIO Y 01012027.json' || d.files[0].type !== 'application/json') return 'fichero ' + d.files.map((f) => f.name + '/' + f.type);
    if (n.llamadasShare.length) return 'abrió la hoja solo por preguntar';
  });
  // compartirFichero
  const r = async (o, nombre, texto) => compartirFichero(nav(o), File, nombre || 'X', texto === undefined ? TXT : texto);
  await caso('comparte: sin navegador → sin_soporte', async () => (await compartirFichero(null, File, 'X', TXT)).resultado === 'sin_soporte' || 'otro resultado');
  await caso('comparte: sin share → sin_soporte', async () => (await r({ sinShare: true })).resultado === 'sin_soporte' || 'otro resultado');
  await caso('comparte: sin canShare → sin_soporte y no abre la hoja', async () => { const n = nav({ sinCan: true }); const x = await compartirFichero(n, File, 'X', TXT); return (x.resultado === 'sin_soporte' && n.llamadasShare.length === 0) || x.resultado; });
  await caso('comparte: canShare falso → sin_soporte y NO abre la hoja', async () => { const n = nav({ can: false }); const x = await compartirFichero(n, File, 'X', TXT); return (x.resultado === 'sin_soporte' && n.llamadasShare.length === 0) || (x.resultado + ' share=' + n.llamadasShare.length); });
  await caso('comparte: canShare lanza → sin_soporte (no revienta)', async () => (await r({ canLanza: true })).resultado === 'sin_soporte' || 'otro resultado');
  await caso('comparte: la clase File lanza → sin_soporte (no revienta)', async () => (await compartirFichero(nav(), function () { throw new Error('x'); }, 'X', TXT)).resultado === 'sin_soporte' || 'otro resultado');
  await caso('comparte: acepta → compartido, UNA vez, con el nombre, el tipo y los bytes exactos', async () => {
    const n = nav(); const x = await compartirFichero(n, File, 'CONTROL HORARIO Z 05062026', TXT);
    if (x.resultado !== 'compartido') return x.resultado;
    if (n.llamadasShare.length !== 1) return 'share llamado ' + n.llamadasShare.length + ' veces';
    const d = n.llamadasShare[0];
    if (JSON.stringify(Object.keys(d)) !== '["files"]') return 'claves ' + Object.keys(d);
    const f = d.files[0];
    if (d.files.length !== 1 || f.name !== 'CONTROL HORARIO Z 05062026.json' || f.type !== 'application/json') return 'fichero ' + f.name + '/' + f.type;
    if ((await f.text()) !== TXT) return 'contenido distinto';
    if (n.llamadasCan.length < 1) return 'no preguntó antes con canShare';
    if (n.llamadasCan[n.llamadasCan.length - 1].files[0] !== f) return 'canShare y share no recibieron el mismo fichero';
  });
  await caso('comparte: AbortError (cerró la hoja) → cancelado', async () => (await r({ rechaza: 'AbortError' })).resultado === 'cancelado' || 'otro resultado');
  await caso('comparte: NotAllowedError (el tipo no se admite) → denegado', async () => (await r({ rechaza: 'NotAllowedError' })).resultado === 'denegado' || 'otro resultado');
  for (const nombre of ['TypeError', 'DataError', 'InvalidStateError', 'SecurityError', 'Error'])
    await caso('comparte: ' + nombre + ' → error', async () => (await r({ rechaza: nombre })).resultado === 'error' || 'otro resultado');
  await caso('comparte: rechaza con un texto suelto → error', async () => (await r({ rechaza: 'raro' })).resultado === 'error' || 'otro resultado');
  await caso('comparte: rechaza sin nada → error', async () => (await r({ rechaza: 'nada' })).resultado === 'error' || 'otro resultado');
  await caso('comparte: share lanza en seco (sin promesa) → error y no revienta', async () => (await r({ shareLanza: 'TypeError' })).resultado === 'error' || 'otro resultado');
  await caso('comparte: share lanza AbortError en seco → cancelado', async () => (await r({ shareLanza: 'AbortError' })).resultado === 'cancelado' || 'otro resultado');
  await caso('comparte: nunca devuelve otra cosa que esas cinco palabras', async () => {
    const buenas = ['compartido', 'cancelado', 'denegado', 'sin_soporte', 'error'];
    for (const o of [{}, { can: false }, { canLanza: true }, { rechaza: 'AbortError' }, { rechaza: 'NotAllowedError' }, { rechaza: 'TypeError' }, { shareLanza: 'Error' }, { sinCan: true }, { sinShare: true }]) {
      const x = await r(o); if (!buenas.includes(x.resultado)) return 'devolvió ' + JSON.stringify(x);
    }
  });
  await caso('comparte: el contenido llega SIN tocar (acentos, eñes, comillas)', async () => {
    const n = nav(); await compartirFichero(n, File, 'X', TXT);
    return (await n.llamadasShare[0].files[0].text()) === TXT || 'cambió';
  });
  console.log(fallos ? ('RESUMEN ' + fallos + ' de ' + total + ' fallan') : ('OK ' + total + ' casos'));
  process.exit(fallos ? 1 : 0);
})();
'''


def funciones_del_html(texto):
    m = re.search(r"// COMPARTIR: inicio\n(.*?)// COMPARTIR: fin", texto, re.S)
    if not m:
        raise AssertionError("no encuentro el bloque «COMPARTIR» en generador_personal.html")
    return m.group(1)


class TestLogicaPura(unittest.TestCase):
    def setUp(self):
        self.html = (APP_DIR / "generador_personal.html").read_text(encoding="utf-8")

    def test_los_casos_de_la_funcion_pura(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("falta node: NO se ha revisado la lógica de «Enviar con…»")
        base = TMP_BASE / ("ma7_" + uuid.uuid4().hex[:8])
        base.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(base), True)
        (base / "compartir.js").write_text(funciones_del_html(self.html), encoding="utf-8")
        (base / "verificador.js").write_text(VERIFICADOR, encoding="utf-8")
        p = subprocess.run([node, str(base / "verificador.js"), str(base / "compartir.js")], capture_output=True, timeout=120)
        salida = (p.stdout + p.stderr).decode("utf-8", "replace")
        self.assertEqual(p.returncode, 0, "la lógica de «Enviar con…» falla:\n" + salida)
        self.assertIn("OK", salida)

    def test_la_logica_no_toca_la_pantalla_ni_el_reloj_ni_el_almacen(self):
        codigo = funciones_del_html(self.html)
        sin_comentarios = "\n".join(l for l in codigo.splitlines() if not l.strip().startswith("//"))
        for prohibido in ("document", "window", "localStorage", "Date", "render(", "toast(", "navigator", "setTimeout", "a.", "set(", "get("):
            self.assertNotIn(prohibido, sin_comentarios, "la lógica pura de «Enviar con…» no puede usar «%s»" % prohibido)

    def test_la_descarga_y_el_compartir_sacan_el_contenido_de_un_solo_sitio(self):
        usos = self.html.count("textoDelFichero(")
        self.assertGreaterEqual(usos, 3, "textoDelFichero tiene que usarse en la descarga y en compartir (y definirse una vez)")
        self.assertEqual(self.html.count("function textoDelFichero("), 1)
        self.assertNotIn("JSON.stringify(fichero.lote", self.html, "el contenido del fichero no se arma por otro camino")

    def test_compartir_se_llama_desde_el_toque_sin_esperar(self):
        # La hoja del sistema solo se abre con un toque reciente: nada que espere antes de llamar a compartirFichero.
        m = re.search(r"async function compartirObra\(id\) \{(.*?)\n      \}\n", self.html, re.S)
        self.assertIsNotNone(m, "no encuentro compartirObra")
        cuerpo = m.group(1)
        antes = cuerpo.split("await compartirFichero(")[0]
        self.assertNotIn("await", antes, "no se puede esperar nada antes de abrir la hoja de compartir")
        self.assertNotIn("setTimeout", cuerpo)


# ───────────────────────────── 2) la pantalla, con el navegador simulado ─────────────────────────────
STUB = """(() => {
  window.__llamadas = []; window.__rechazos = []; window.__modo = %s;
  window.addEventListener('unhandledrejection', (e) => window.__rechazos.push(String(e.reason)));
  const nuevo = (nombre) => { const e = new Error(nombre); e.name = nombre; return e; };
  navigator.canShare = (d) => { if (window.__modo === 'sin_permiso') return false; return !!(d && d.files && d.files.length); };
  navigator.share = async (d) => {
    const f = d.files[0];
    window.__llamadas.push({ claves: Object.keys(d), n: d.files.length, nombre: f.name, tipo: f.type, texto: await f.text(), activo: navigator.userActivation.isActive });
    if (window.__modo === 'cancela') throw nuevo('AbortError');
    if (window.__modo === 'deniega') throw nuevo('NotAllowedError');
    if (window.__modo === 'falla') throw nuevo('TypeError');
    if (window.__modo === 'espera') await new Promise((r) => { window.__soltar = r; });
  };
})();"""


def fecha_fija(iso):
    return """(() => { const fijo = new Date('%sT10:00:00+01:00').valueOf(); const Real = Date;
  class Falsa extends Real { constructor(...a) { if (a.length === 0) { super(fijo); } else { super(...a); } } static now() { return fijo; } }
  window.Date = Falsa; })();""" % iso


def pend(obra, fecha, ambito, nombres):
    return {"obra": obra, "ambito": ambito, "fecha": fecha, "anulada": False,
            "presentes": [{"nombre": n, "horas": 7.5, "extra": 0} for n in nombres], "notas": "", "registrado": fecha + "T18:00:00.000Z"}


PENDIENTES = [pend("olabeaga", "2026-10-23", "vivienda", ["Mikel", "Txomin", "Rafa"]), pend("olabeaga", "2026-10-23", "garaje", ["Andoni", "Josu"]),
              pend("mungia", "2026-10-22", "vivienda", ["Pepe"])]
NOMBRE_OLA = "CONTROL HORARIO 2026 OLABEAGA BILBAO 23102026"
NOMBRE_MUN = "CONTROL HORARIO 2026 MUNGIA ACR NEINOR 23102026"
TEXTO_LISTO_OLA = "Listo. Has pasado el fichero «%s» con 2 jornadas a la aplicación que has elegido. Comprueba que ha llegado a la carpeta REVISIONES de la obra." % NOMBRE_OLA
TEXTO_VIAS = ("Hay dos maneras de llevar el fichero al PC. «Preparar el fichero para el PC» lo guarda en las descargas de este aparato (los pasos de abajo). "
              "«Enviar con…» abre la lista de aplicaciones de este aparato: elige OneDrive (o la que uses para pasar cosas al PC) y la carpeta REVISIONES de la obra. "
              "Es el mismo fichero en las dos.")
TEXTO_DENEGADO = ("Este aparato no deja pasar este fichero con «Enviar con…». Usa «Preparar el fichero para el PC»: guarda el mismo fichero y no se pierde nada.")
TEXTO_ERROR = ("No se ha podido abrir «Enviar con…». Vuelve a probar o usa «Preparar el fichero para el PC»: guarda el mismo fichero y no se pierde nada.")


def sembrar(claves):
    ordenes = "".join("localStorage.setItem('%s',%s);" % (k, json.dumps(json.dumps(v))) for k, v in claves.items())
    return "if(!localStorage.getItem('_s')){localStorage.setItem('_s','1');%s}" % ordenes


def _norm(t):
    return " ".join((t or "").split())


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

    def carpeta(self):
        c = TMP_BASE / ("ma7_" + uuid.uuid4().hex[:8])
        c.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(c), True)
        for n in ("generador_personal.html", "personal_calculo.js"):
            shutil.copy2(APP_DIR / n, c / n)
        (c / "personal_estado.js").write_text("window.SAGARDE_PERSONAL = " + json.dumps(ma6.estado(), ensure_ascii=False) + ";\n", encoding="utf-8")
        self.dir = c
        return c

    def abrir(self, modo="acepta", pendientes=PENDIENTES, ancho=390, alto=844, claves=None, fecha="2026-10-23", ir_a_enviar=True, carpeta=None, ctx=None):
        """Abre la tablet con el navegador de compartir simulado en ese modo (None = el navegador no sabe compartir). Devuelve (página, errores)."""
        carpeta = carpeta or self.carpeta()
        if ctx is None:
            ctx = self.navegador.new_context(viewport={"width": ancho, "height": alto}, timezone_id="Europe/Madrid", locale="es-ES", has_touch=True, accept_downloads=True)
            self.addCleanup(ctx.close)
            ctx.add_init_script(fecha_fija(fecha))
            todo = {"sgd_personal_aviso_instalar": True}
            if pendientes:
                todo["sgd_personal_pendientes"] = pendientes
            todo.update(claves or {})
            ctx.add_init_script(sembrar(todo))
            if modo is not None and modo != "sin_share":
                ctx.add_init_script(STUB % json.dumps(modo))
        pg = ctx.new_page()
        pg.set_default_timeout(5000)
        errores = []
        pg.on("pageerror", lambda x: errores.append(str(x)))
        pg.goto((carpeta / "generador_personal.html").resolve().as_uri())
        pg.wait_for_selector("#obra")
        if ir_a_enviar:
            pg.click('nav button[data-v="enviar"]')
        self.ctx = ctx
        return pg, errores

    def descargar(self, pg, obra):
        with pg.expect_download(timeout=5000) as d:
            pg.click('button[data-preparar="%s"]' % obra)
        ruta = self.dir / ("d_" + uuid.uuid4().hex[:6] + ".json")
        d.value.save_as(str(ruta))
        return d.value.suggested_filename, ruta.read_bytes()

    def pendientes_guardados(self, pg):
        return pg.evaluate("JSON.parse(localStorage.getItem('sgd_personal_pendientes') || '[]')")

    def llamadas(self, pg):
        return pg.evaluate("window.__llamadas || []")

    def sin_fallos(self, pg, errores):
        self.assertEqual(errores, [], "errores de JavaScript: %s" % errores)
        self.assertEqual(pg.evaluate("window.__rechazos || []"), [], "promesas rechazadas sin atender")


class TestElBotonYLoQueComparte(Base):
    def test_acepta_comparte_el_fichero_exacto_y_la_descarga_sigue_igual(self):
        pg, errores = self.abrir("acepta")
        self.assertEqual(pg.locator("button[data-compartir]").count(), 2, "un «Enviar con…» por obra con algo que enviar")
        self.assertEqual(pg.locator("button[data-preparar]").count(), 2, "la descarga de siempre sigue ahí")
        self.assertEqual(_norm(pg.inner_text('button[data-compartir="olabeaga"]')), "Enviar con…")
        self.assertEqual(_norm(pg.inner_text("#envio-vias")), TEXTO_VIAS)
        antes = self.pendientes_guardados(pg)
        pg.click('button[data-compartir="olabeaga"]')
        pg.wait_for_selector("#listo")
        ll = self.llamadas(pg)
        self.assertEqual(len(ll), 1, "la hoja de compartir se abre UNA vez")
        c = ll[0]
        self.assertEqual((c["claves"], c["n"], c["nombre"], c["tipo"]), (["files"], 1, NOMBRE_OLA + ".json", "application/json"))
        self.assertTrue(c["activo"], "la hoja tiene que abrirse dentro del toque del dedo (el navegador no la abre si no)")
        lote = json.loads(c["texto"])
        self.assertEqual((lote["tipo"], lote["obra"], len(lote["jornadas"])), ("lote_personal", "olabeaga", 2))
        self.assertEqual(c["texto"], json.dumps(lote, indent=1, ensure_ascii=False), "el contenido tiene el formato de siempre (sangría de un espacio, sin escapar acentos)")
        self.assertEqual(_norm(pg.inner_text("#listo")), TEXTO_LISTO_OLA)
        self.assertEqual(pg.locator("#envio-fallo").count(), 0)
        self.assertEqual(self.pendientes_guardados(pg), antes, "compartir no marca nada como enviado: las jornadas siguen apuntadas, como tras la descarga")
        self.assertEqual(_norm(pg.inner_text("#resumen-envio")), "Tienes 3 jornadas sin enviar:")
        # el fichero compartido es, byte a byte, el que baja la descarga de siempre
        nombre, datos = self.descargar(pg, "olabeaga")
        self.assertEqual(nombre, NOMBRE_OLA + ".json")
        self.assertEqual(hashlib.sha256(datos).hexdigest(), hashlib.sha256(c["texto"].encode("utf-8")).hexdigest(), "el fichero compartido difiere del descargado")
        self.assertEqual(datos, c["texto"].encode("utf-8"))
        self.assertFalse(datos.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Se ha guardado el fichero", _norm(pg.inner_text("#listo")), "tras la descarga, el recuadro dice lo de siempre")
        self.sin_fallos(pg, errores)

    def test_cada_obra_comparte_su_fichero(self):
        pg, errores = self.abrir("acepta")
        pg.click('button[data-compartir="mungia"]')
        pg.wait_for_selector("#listo")
        c = self.llamadas(pg)[0]
        self.assertEqual(c["nombre"], NOMBRE_MUN + ".json")
        lote = json.loads(c["texto"])
        self.assertEqual((lote["obra"], [p["nombre"] for j in lote["jornadas"] for p in j["presentes"]]), ("mungia", ["Pepe"]))
        _, datos = self.descargar(pg, "mungia")
        self.assertEqual(datos, c["texto"].encode("utf-8"))
        self.sin_fallos(pg, errores)

    def test_el_fichero_con_nombres_empresas_y_cambios_tambien_es_igual(self):
        claves = {"sgd_personal_altas": ["Nerea Nueva"], "sgd_personal_renombres": [{"de": "Rafa", "a": "Rafael"}],
                  "sgd_personal_empresas": [{"nombre": "Mikel", "empresa": "Alfa Instalaciones"}]}
        pg, errores = self.abrir("acepta", claves=claves)
        pg.click('button[data-compartir="olabeaga"]')
        pg.wait_for_selector("#listo")
        c = self.llamadas(pg)[0]
        lote = json.loads(c["texto"])
        self.assertTrue(lote.get("altas") and lote.get("renombres") and lote.get("empresas"), "el fichero lleva los nombres: %s" % list(lote))
        self.assertEqual(c["texto"], json.dumps(lote, indent=1, ensure_ascii=False))
        _, datos = self.descargar(pg, "olabeaga")
        self.assertEqual(datos, c["texto"].encode("utf-8"))
        self.sin_fallos(pg, errores)

    def test_un_dia_sin_jornadas_pero_con_nombres_comparte_el_de_la_obra_que_se_ve(self):
        pg, errores = self.abrir("acepta", pendientes=None, claves={"sgd_personal_altas": ["Nerea Nueva"]})
        self.assertEqual(pg.locator("button[data-compartir]").count(), 1)
        pg.click("button[data-compartir]")
        pg.wait_for_selector("#listo")
        c = self.llamadas(pg)[0]
        self.assertEqual(json.loads(c["texto"])["altas"], ["Nerea Nueva"])
        _, datos = self.descargar(pg, json.loads(c["texto"])["obra"])
        self.assertEqual(datos, c["texto"].encode("utf-8"))
        self.sin_fallos(pg, errores)

    def test_doble_toque_no_abre_dos_hojas(self):
        pg, errores = self.abrir("espera")
        pg.evaluate("document.querySelector('button[data-compartir=\"olabeaga\"]').click(); document.querySelector('button[data-compartir=\"olabeaga\"]').click();")
        pg.wait_for_function("window.__llamadas.length >= 1 && typeof window.__soltar === 'function'")
        pg.wait_for_timeout(200)
        self.assertEqual(len(self.llamadas(pg)), 1, "un segundo toque con la hoja abierta no abre otra")
        pg.evaluate("window.__soltar()")
        pg.wait_for_selector("#listo")
        pg.evaluate("window.__soltar = null")
        pg.evaluate("document.querySelector('button[data-compartir=\"olabeaga\"]').click()")
        pg.wait_for_function("window.__llamadas.length === 2")
        self.assertEqual(len(self.llamadas(pg)), 2, "cuando la hoja se cierra se puede volver a abrir")
        pg.evaluate("window.__soltar()")
        self.sin_fallos(pg, errores)


class TestCancelarRechazarYFallar(Base):
    def test_cancelar_no_es_un_fallo_y_no_cambia_nada(self):
        pg, errores = self.abrir("cancela")
        self.descargar(pg, "olabeaga")      # ya hay un recuadro «Listo» de la descarga: cancelar no lo toca
        listo = _norm(pg.inner_text("#listo"))
        antes = self.pendientes_guardados(pg)
        html_antes = pg.inner_html("#v-enviar")
        pg.click('button[data-compartir="olabeaga"]')
        pg.wait_for_function("window.__llamadas.length === 1")
        pg.wait_for_timeout(300)
        self.assertEqual(pg.locator("#envio-fallo").count(), 0, "cancelar no enseña ningún aviso")
        self.assertEqual(_norm(pg.inner_text("#listo")), listo)
        self.assertEqual(self.pendientes_guardados(pg), antes)
        self.assertEqual(pg.inner_html("#v-enviar"), html_antes, "cancelar deja la pantalla exactamente como estaba")
        self.assertEqual(pg.locator("button[data-compartir]").count(), 2, "el botón sigue ahí")
        self.assertIsNone(pg.evaluate("localStorage.getItem('sgd_personal_sin_compartir')"), "cancelar no esconde el botón")
        pg.click('button[data-compartir="olabeaga"]')
        pg.wait_for_function("window.__llamadas.length === 2")
        self.sin_fallos(pg, errores)

    def test_cancelar_sin_haber_descargado_no_deja_el_recuadro_listo(self):
        pg, errores = self.abrir("cancela")
        pg.click('button[data-compartir="olabeaga"]')
        pg.wait_for_function("window.__llamadas.length === 1")
        pg.wait_for_timeout(300)
        self.assertEqual(pg.locator("#listo").count(), 0, "cancelar no marca nada como enviado")
        self.assertEqual(pg.locator("#envio-fallo").count(), 0)
        self.assertEqual(len(self.pendientes_guardados(pg)), 3)
        self.sin_fallos(pg, errores)

    def test_si_el_aparato_rechaza_el_fichero_avisa_en_llano_y_esconde_el_boton(self):
        pg, errores = self.abrir("deniega")
        pg.click('button[data-compartir="olabeaga"]')
        pg.wait_for_selector("#envio-fallo")
        self.assertEqual(_norm(pg.inner_text("#envio-fallo")), TEXTO_DENEGADO)
        self.assertEqual(pg.locator("#listo").count(), 0, "no dice «Listo» si no se envió nada")
        self.assertEqual(pg.locator("button[data-compartir]").count(), 0, "el botón se esconde en este aparato")
        self.assertEqual(pg.locator("#envio-vias").count(), 0)
        self.assertEqual(pg.locator("button[data-preparar]").count(), 2, "la descarga sigue ahí")
        self.assertEqual(pg.evaluate("JSON.parse(localStorage.getItem('sgd_personal_sin_compartir'))"), {"desde": "2026-10-23"})
        self.assertEqual(len(self.pendientes_guardados(pg)), 3)
        # la descarga funciona y quita el aviso
        nombre, datos = self.descargar(pg, "olabeaga")
        self.assertEqual(nombre, NOMBRE_OLA + ".json")
        self.assertEqual(pg.locator("#envio-fallo").count(), 0)
        self.assertIn("Se ha guardado el fichero", _norm(pg.inner_text("#listo")))
        # al volver a abrir la tablet sigue sin botón
        pg2, e2 = self.abrir("deniega", ctx=self.ctx, carpeta=self.dir)
        self.assertEqual(pg2.locator("button[data-compartir]").count(), 0, "recuerda el rechazo al volver a abrir")
        self.assertEqual(pg2.locator("button[data-preparar]").count(), 2)
        self.sin_fallos(pg, errores)

    def test_el_rechazo_se_olvida_a_los_30_dias(self):
        # el rechazo es del 23/10; el último día escondido es el 22/11 y el 23/11 vuelve a probar
        for fecha, hay in (("2026-11-22", 0), ("2026-11-23", 2)):
            with self.subTest(fecha=fecha):
                pg, errores = self.abrir("acepta", fecha=fecha, claves={"sgd_personal_sin_compartir": {"desde": "2026-10-23"}})
                self.assertEqual(pg.locator("button[data-compartir]").count(), hay)
                self.assertEqual(pg.locator("#envio-vias").count(), 1 if hay else 0)
                self.sin_fallos(pg, errores)

    def test_un_rechazo_guardado_roto_no_esconde_nada_ni_revienta(self):
        for roto in ("basura", 7, {"desde": 5}, {"desde": "no es fecha"}, {}):
            with self.subTest(roto=roto):
                pg, errores = self.abrir("acepta", claves={"sgd_personal_sin_compartir": roto})
                self.assertEqual(pg.locator("button[data-compartir]").count(), 2)
                self.sin_fallos(pg, errores)

    def test_otro_fallo_avisa_pero_el_boton_sigue(self):
        pg, errores = self.abrir("falla")
        pg.click('button[data-compartir="olabeaga"]')
        pg.wait_for_selector("#envio-fallo")
        self.assertEqual(_norm(pg.inner_text("#envio-fallo")), TEXTO_ERROR)
        self.assertEqual(pg.locator("#listo").count(), 0)
        self.assertEqual(pg.locator("button[data-compartir]").count(), 2, "un fallo suelto no esconde el botón")
        self.assertIsNone(pg.evaluate("localStorage.getItem('sgd_personal_sin_compartir')"))
        self.assertEqual(len(self.pendientes_guardados(pg)), 3)
        pg.click('button[data-compartir="olabeaga"]')
        pg.wait_for_function("window.__llamadas.length === 2")
        self.sin_fallos(pg, errores)

    def test_tras_un_fallo_compartir_bien_quita_el_aviso(self):
        pg, errores = self.abrir("falla")
        pg.click('button[data-compartir="olabeaga"]')
        pg.wait_for_selector("#envio-fallo")
        pg.evaluate("window.__modo = 'acepta'")
        pg.click('button[data-compartir="olabeaga"]')
        pg.wait_for_selector("#listo")
        self.assertEqual(pg.locator("#envio-fallo").count(), 0)
        self.sin_fallos(pg, errores)


class TestSinSoporteYSinNadaQueEnviar(Base):
    def _sin_boton(self, pg):
        self.assertEqual(pg.locator("button[data-compartir]").count(), 0, "sin soporte no sale «Enviar con…»")
        self.assertEqual(pg.locator("#envio-vias").count(), 0)
        self.assertEqual(pg.locator("button[data-preparar]").count(), 2)
        pasos = pg.eval_on_selector_all("#pasos li", "e=>e.map(l=>l.textContent.trim())")
        self.assertEqual(len(pasos), 3, "los tres pasos de siempre")
        self.assertNotIn("Enviar con", pg.inner_text("#enviar"))

    def test_el_navegador_no_sabe_compartir(self):
        pg, errores = self.abrir(None)
        self.assertEqual(pg.evaluate("typeof navigator.share + '/' + typeof navigator.canShare"), "undefined/undefined")
        self._sin_boton(pg)
        nombre, _ = self.descargar(pg, "olabeaga")
        self.assertEqual(nombre, NOMBRE_OLA + ".json")
        self.sin_fallos(pg, errores)

    def test_share_sin_canshare(self):
        pg, errores = self.abrir(None, ir_a_enviar=False)
        pg.evaluate("navigator.share = async () => {}; 0")
        pg.click('nav button[data-v="enviar"]')
        self._sin_boton(pg)
        self.sin_fallos(pg, errores)

    def test_canshare_dice_que_no(self):
        pg, errores = self.abrir("sin_permiso")
        self._sin_boton(pg)
        self.sin_fallos(pg, errores)

    def test_canshare_lanza(self):
        pg, errores = self.abrir(None, ir_a_enviar=False)
        pg.evaluate("navigator.share = async () => {}; navigator.canShare = () => { throw new TypeError('no'); }; 0")
        pg.click('nav button[data-v="enviar"]')
        self._sin_boton(pg)
        self.sin_fallos(pg, errores)

    def test_sin_nada_que_enviar_no_hay_boton_ni_explicacion(self):
        pg, errores = self.abrir("acepta", pendientes=None)
        self.assertEqual(pg.locator("button[data-compartir]").count(), 0)
        self.assertEqual(pg.locator("#envio-vias").count(), 0)
        self.assertEqual(_norm(pg.inner_text("#nada-que-enviar")), "No hay nada por enviar: todas las jornadas ya están en el PC.")
        self.assertEqual(len(self.llamadas(pg)), 0)
        self.sin_fallos(pg, errores)

    def test_la_pantalla_sin_soporte_es_la_de_siempre(self):
        # con soporte la pantalla solo SUMA (la explicación y los botones); quitándolos queda lo mismo que sin soporte
        pg1, _ = self.abrir(None)
        sin = pg1.inner_html("#v-enviar")
        pg2, _ = self.abrir("acepta")
        con = pg2.inner_html("#v-enviar")
        quitado = re.sub(r'<button class="btn sec full" data-compartir="[^"]*">Enviar con…</button>', "", con)
        quitado = re.sub(r'<p id="envio-vias">.*?</p>', "", quitado, flags=re.S)
        self.assertEqual(quitado, sin)


class TestLenguajeDeLaPantalla(Base):
    def test_todo_lo_que_se_lee_en_enviar_esta_en_llano(self):
        from test_lenguaje_electricista import revisar
        for modo in ("acepta", "cancela", "deniega", "falla"):
            with self.subTest(modo=modo):
                pg, errores = self.abrir(modo)
                textos = [pg.inner_text("#enviar")]
                pg.click('button[data-compartir="olabeaga"]')
                pg.wait_for_function("window.__llamadas.length === 1")
                pg.wait_for_timeout(300)
                textos.append(pg.inner_text("#enviar"))
                self.assertEqual(revisar(textos, "pantalla Enviar al PC (%s)" % modo), [])
                self.assertIn("Enviar con", textos[0])
                self.sin_fallos(pg, errores)


class TestTamanoDelBoton(Base):
    def test_el_boton_se_pulsa_bien_en_seis_anchos(self):
        for ancho, alto in ma6.ANCHOS:
            with self.subTest(ancho=ancho):
                pg, errores = self.abrir("acepta", ancho=ancho, alto=alto)
                m = pg.evaluate(ma6.JS_MEDIDAS)
                self.assertLessEqual(m["doc"][0], m["doc"][1], "la pantalla se sale de ancho: %s" % m["doc"])
                self.assertEqual(m["fuera"], [])
                self.assertEqual(m["chicos"], [], "hay botones o campos de menos de 44 px: %s" % m["chicos"])
                self.assertEqual(m["letra"], [])
                self.assertEqual(m["propios"], [])
                caja = pg.eval_on_selector('button[data-compartir="olabeaga"]', "b=>{const r=b.getBoundingClientRect();return [r.width,r.height]}")
                self.assertGreaterEqual(caja[1], 48, "el botón es grande para el dedo: %s" % caja)
                self.assertGreaterEqual(caja[0], 150)
                hermano = pg.eval_on_selector('button[data-compartir="olabeaga"]', "b=>{const p=b.previousElementSibling.getBoundingClientRect(), r=b.getBoundingClientRect();return [r.top-p.bottom, p.left-r.left, p.width-r.width]}")
                self.assertGreaterEqual(hermano[0], 6, "los dos botones no se pegan: %s" % hermano)
                self.assertEqual((round(hermano[1]), round(hermano[2])), (0, 0), "los dos botones tienen el mismo ancho")
                self.sin_fallos(pg, errores)


if __name__ == "__main__":
    unittest.main()
