# -*- coding: utf-8 -*-
"""Guarda de lenguaje de «Personal en obra» (paso 08d): todo lo que lee Bixente va en lenguaje de electricista.

Falla si en un texto que él lee aparece una palabra de programador (exportar, importar, lote, ingerir, fichero JSON,
pendiente(s), alta, base de datos, estado, simulación) o un código interno (alta_nueva, nombre_parecido…).
Mira dos sitios:
  · la app de la tablet, en un navegador de verdad: cada pantalla y cada estado (avisos, errores, recuadro «Listo»…);
  · lo que imprime el PC: los avisos de personal_obra/lector_control_horario, las líneas de personal_integracion,
    la guarda y el informe de actualizar_obra.py y el gancho de generar_todos.py.
Los códigos internos siguen existiendo para las pruebas y el auditor: aquí solo se comprueba lo que se le enseña.
Una lista vacía de textos es una alarma, no un «no aplica»: cada bloque exige un mínimo de textos revisados."""
import ast
import copy
import importlib.util
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unicodedata
import uuid
from pathlib import Path

TESTS = Path(__file__).resolve().parent
# P3_MOTOR / P3_SCRIPTS / P3_APP apuntan a otra copia del motor, de los scripts o de la app (para las mutaciones: se rompe una COPIA, nunca el original).
MOTOR_IA = Path(os.environ.get("P3_MOTOR") or TESTS.parent)
RAIZ_REPO = TESTS.parent.parents[1]
SCRIPTS = Path(os.environ.get("P3_SCRIPTS") or RAIZ_REPO / "_SISTEMA" / "MOTOR" / "scripts")
APP_DIR = Path(os.environ.get("P3_APP") or TESTS.parent)
if str(MOTOR_IA) not in sys.path:
    sys.path.insert(0, str(MOTOR_IA))

import datos_base_trabajadores as D  # noqa: E402
import lector_control_horario as lector  # noqa: E402
import personal_integracion as pi  # noqa: E402
import personal_obra as po  # noqa: E402

# Cada regla: (nombre para el mensaje, patrón sobre el texto sin tildes y en minúsculas).
REGLAS = [
    ("exportar", r"\bexport\w*"),
    ("importar", r"\bimportar\b|\bimportad[oa]s?\b|\bimportacion\w*"),
    ("lote", r"\blotes?\b"),
    ("ingerir", r"\bingerir\b|\bingerid\w*|\bingest\w*"),
    ("fichero JSON", r"\bjson\b"),
    ("pendiente(s)", r"\bpendientes?\b"),
    ("alta", r"\baltas?\b"),
    ("base de datos", r"base de datos"),
    ("estado", r"\bestados?\b"),
    ("simulación", r"simulaci\w*"),
    ("código interno (con guion bajo)", r"\b[a-z]+(?:_[a-z]+)+\b(?!\.(?:py|js|json|jsonl|html|bat|md)\b)"),
    ("jornada(s) / nombre(s)", r"\b\w+\((?:s|es)\)"),
]


def _sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)).lower()


def palabras_prohibidas(texto):
    """Lista de (regla, trozo) que aparecen en el texto; vacía si está limpio."""
    limpio = _sin_tildes(texto or "")
    out = []
    for nombre, patron in REGLAS:
        for m in re.finditer(patron, limpio):
            out.append((nombre, m.group(0)))
    return out


def revisar(textos, donde):
    """Lista de problemas legibles: «dónde: 'texto' lleva exportar (exportadas)»."""
    problemas = []
    for t in textos:
        for nombre, trozo in palabras_prohibidas(t):
            problemas.append("%s: «%s» lleva «%s» (%s)" % (donde, " ".join(t.split())[:140], nombre, trozo))
    return problemas


# ─────────────────────────────── textos del PC ───────────────────────────────
def _constantes(ruta, funciones):
    """Textos literales (sin docstrings) de esas funciones de un fichero Python; las partes fijas de las f-strings también."""
    arbol = ast.parse(Path(ruta).read_text(encoding="utf-8"))
    out = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.FunctionDef) or nodo.name not in funciones:
            continue
        doc = nodo.body[0].value if nodo.body and isinstance(nodo.body[0], ast.Expr) else None
        for hijo in ast.walk(nodo):
            if hijo is doc:
                continue
            if isinstance(hijo, ast.Constant) and isinstance(hijo.value, str) and " " in hijo.value.strip():
                out.append(hijo.value)
    return out


def _mensajes_de_incidencias(ruta):
    """Mensaje y solución de cada `_incidencia(...)` del auditor de personal (lo que lee Bixente si frena el .bat)."""
    arbol = ast.parse(Path(ruta).read_text(encoding="utf-8"))
    out = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call) and getattr(nodo.func, "id", "") == "_incidencia" and len(nodo.args) >= 4:
            for arg in nodo.args[2:4]:
                for hijo in ast.walk(arg):
                    if isinstance(hijo, ast.Constant) and isinstance(hijo.value, str) and " " in hijo.value.strip():
                        out.append(hijo.value)
    return out


def _codigos_de_texto_aviso():
    """Todos los códigos que entiende po.texto_aviso: las claves de su diccionario y los «if codigo == …»."""
    codigo = inspect.getsource(po.texto_aviso)
    return sorted(set(re.findall(r'^\s+"([a-z_]+)":', codigo, re.M)) | set(re.findall(r'codigo == "([a-z_]+)"', codigo)))


def textos_del_pc():
    textos = list(lector.TEXTOS.values()) + list(pi._ETIQUETAS_PREVIA.values())
    for codigo in _codigos_de_texto_aviso():
        for detalle in (None, "", "Ana", "Ana ~ Ane", "Ana: 13 h", "Ana, Ane", "13,5"):
            textos.append(po.texto_aviso(codigo, detalle))
    textos += _constantes(MOTOR_IA / "personal_integracion.py", {"_lineas_ficha", "lineas_controles", "aplicar_controles_limpios", "_resumen_totales"})
    textos += _mensajes_de_incidencias(MOTOR_IA / "personal_integracion.py")
    textos += _constantes(
        SCRIPTS / "actualizar_obra.py",
        {"_controles", "_guarda_controles", "_seccion_h", "_lineas_resumen_controles", "_controles_aplicables", "_plural"},
    )
    textos += _constantes(MOTOR_IA / "generar_todos.py", {"_controles_horarios_de_obra"})
    # Campo Empresa (08c2a): las frases de cada cambio de empresa, las de lo que se deja sin separar y lo que imprime `separar-empresas`.
    for accion in ("puesta", "cambiada", "quitada", "sin_cambios"):
        textos.append(po.texto_empresa(accion, "Ana", "Manueles", "Catersystem"))
    for codigo in ("nombre_vacio", "sin_letras", "sufijo_aut", "no_vale", "mismo_nombre", "ya_tiene_empresa", "coincide_con_otro", "otro"):
        textos.append(po.texto_separar(codigo, "Javi @AUT", "AUT"))
    textos += _constantes(MOTOR_IA / "personal_obra.py", {"_cli_separar_empresas"})
    return textos


# ─────────────────────────────── la app en un navegador ───────────────────────────────
def _hay_chromium():
    if importlib.util.find_spec("playwright") is None:
        return False, "falta Playwright"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            p.chromium.launch().close()
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, "Playwright no puede abrir Chromium (%s)" % type(exc).__name__


_SALTAR = os.environ.get("SAGARDE_SIN_NAVEGADOR") == "1"
_OK, _MOTIVO = (False, "saltada a propósito (SAGARDE_SIN_NAVEGADOR=1)") if _SALTAR else _hay_chromium()

H = {"lun": 7.5, "mar": 7.5, "mie": 7.5, "jue": 7.5, "vie": 7.5, "sab": 0, "dom": 0}
FECHA_FIJA = """(() => { const fijo = new Date('2026-10-23T10:00:00+02:00').valueOf(); const Real = Date;
  class Falsa extends Real { constructor(...a) { if (a.length === 0) { super(fijo); } else { super(...a); } } static now() { return fijo; } }
  window.Date = Falsa; })();"""
# Todo el texto que ve el usuario, UN TROZO POR NODO DE TEXTO (juntar el contenido de varios botones seguidos pegaba «Informe» con
# «Exportar» en «InformeExportar» y la palabra prohibida no se veía), en cada pantalla (también las ocultas), el aviso flotante y los
# textos de los atributos que se leen en voz alta o se ven al escribir.
JS_TEXTOS = """() => {
  const out = [];
  const paseo = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (paseo.nextNode()) {
    const nodo = paseo.currentNode;
    if (['SCRIPT', 'STYLE'].includes(nodo.parentElement.tagName)) continue;
    if (nodo.nodeValue.trim()) out.push(nodo.nodeValue.trim());
  }
  document.querySelectorAll('[aria-label],[placeholder],[title],[alt]').forEach(e =>
    ['aria-label', 'placeholder', 'title', 'alt'].forEach(a => { if (e.getAttribute(a)) out.push(e.getAttribute(a)); }));
  return out;
}"""


def _fila(fecha, ambito, nombre, horas, extra=0):
    return {"fecha": fecha, "ambito": ambito, "nombre": nombre, "horas": horas, "extra": extra}


def _trab(i, nombre):
    return {"id": "T%04d" % i, "nombre": nombre, "categoria": "", "empresa": "", "activo": True}


def _estado():
    filas = [_fila("2026-10-21", "vivienda", "Mikel", 7.5), _fila("2026-10-21", "vivienda", "Txomin", 7.5),
             _fila("2026-10-22", "vivienda", "Mikel", 7.5), _fila("2026-10-22", "vivienda", "Txomin", 7.5)]
    obra = {"nombre": "2026 OLABEAGA BILBAO", "cerrada": False, "horario_semanal": H, "excepciones_horario": {},
            "ultima": {"vivienda": {"fecha": "2026-10-22", "presentes": [{"nombre": "Mikel", "horas": 7.5, "extra": 0},
                                                                        {"nombre": "Txomin", "horas": 7.5, "extra": 0}]}, "garaje": None},
            "jornadas": filas}
    otra = {"nombre": "2026 MUNGIA", "cerrada": False, "horario_semanal": H, "excepciones_horario": {},
            "ultima": {"vivienda": None, "garaje": None}, "jornadas": []}
    return {"version": 1, "generado": "2026-10-23T08:00:00+02:00", "jornada_base_h": 7.5,
            "catalogo": [_trab(1, "Mikel"), _trab(2, "Txomin"), _trab(3, "Rafa")], "obras": {"olabeaga": obra, "mungia": otra}}


def _estado_empresas():
    """El estado de la tablet con empresas en la base: Mikel de Manueles, Txomin sin empresa y Rafa autónomo."""
    estado = _estado()
    for persona, empresa in zip(estado["catalogo"], ("Manueles", "", "Rafa @AUT")):
        persona["empresa"] = empresa
    return estado


@unittest.skipUnless(_OK, "NO se ha revisado el lenguaje de las pantallas de la tablet: %s" % _MOTIVO)
class TestLenguajeDeLaApp(unittest.TestCase):
    def test_ninguna_pantalla_ni_aviso_usa_palabras_de_programador(self):
        from playwright.sync_api import sync_playwright

        base = Path(os.environ.get("P3_TMP") or tempfile.gettempdir()) / ("lenguaje_" + uuid.uuid4().hex[:8])
        base.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(base), True)
        for nombre in ("generador_personal.html", "personal_calculo.js"):
            shutil.copy(APP_DIR / nombre, base / nombre)

        def poner_estado(datos):
            (base / "personal_estado.js").write_text("window.SAGARDE_PERSONAL = " + json.dumps(datos, ensure_ascii=False) + ";\n", encoding="utf-8")

        url = "file:///" + str(base).replace(os.sep, "/").replace(" ", "%20") + "/generador_personal.html"
        recogidos = []
        with sync_playwright() as p:
            nav = p.chromium.launch()
            ctx = nav.new_context(viewport={"width": 390, "height": 844}, timezone_id="Europe/Madrid", locale="es-ES", accept_downloads=True)
            ctx.add_init_script(FECHA_FIJA)
            pg = ctx.new_page()
            pg.set_default_timeout(4000)
            errores = []
            pg.on("pageerror", lambda e: errores.append(str(e)))

            def mirar():
                recogidos.extend(pg.evaluate(JS_TEXTOS))

            def clic(sel):
                pg.click(sel, timeout=4000)
                mirar()

            def toast_de(accion):
                accion()
                mirar()

            # 0) sin lista guardada ni publicada: la pantalla de «todavía no hay…»
            pg.goto(url)
            pg.wait_for_timeout(4600)
            mirar()
            # 1) con la lista publicada: pantallas y estados
            poner_estado(_estado())
            pg.goto(url)
            pg.wait_for_selector("#obra")
            mirar()
            for vista in ("jornadas", "informe", "enviar", "app"):
                clic('nav button[data-v="%s"]' % vista)
            # día nuevo sin nada guardado (rótulo), copiar el último día (rótulo), «Varios días» encendido y apagado, y sin gente
            clic("button[data-copiar-ultimo]")
            clic("button[data-multi-dias]")
            clic("button[data-multi-dias]")
            clic("button[data-todos='0']")
            clic("button[data-guardar]")                       # «No hay ninguna persona presente»
            clic("button[data-todos='1']")
            clic("button[data-guardar]")                       # jornada guardada
            clic("button[data-reset]")                         # pregunta de borrar
            clic("button[data-reset-no]")
            # lápiz: error de nombre vacío, pregunta de «ya hay un…», cambio hecho
            clic("button[data-ren='0']")
            pg.fill("#ren-campo", "")
            clic("button[data-ren-guardar]")
            pg.fill("#ren-campo", "Txomin")
            clic("button[data-ren-guardar]")
            clic("button[data-ren-no]")
            pg.fill("#ren-campo", "Mikell")
            clic("button[data-ren-guardar]")
            # nombre nuevo con error y con parecido, y varios nombres con todos los resúmenes
            pg.fill("#nuevo", "12345678Z")
            clic("button[data-nuevo]")
            pg.fill("#nuevo", "Txomi")
            clic("button[data-nuevo]")
            clic("button[data-crear]")
            clic("button[data-varios]")
            pg.fill("#varios-texto", "Nerea\nRafa\n12345678Z\nTxomin2\nNerea")
            clic("button[data-varios-ok]")
            clic("button[data-varios-cerrar]")
            # horario especial: editor, guardar y quitar
            clic('.row[data-nombre="Rafa"] button[data-hp-abrir], .row .hpb')
            clic("button[data-hp-guardar]")
            clic(".row .hpb")
            clic("button[data-hp-quitar]")
            # pantalla de enviar con cosas, y tras preparar el fichero
            clic('nav button[data-v="enviar"]')
            with pg.expect_download(timeout=5000):
                pg.click("button[data-preparar]")
            mirar()
            clic('nav button[data-v="app"]')
            # horas que no valen, 24 h y más de 12 h entre obras
            clic("button[data-amb='garaje']")
            clic("button[data-todos='1']")
            clic("button[data-guardar]")
            # sin lista nueva (el fichero ya no está): abre con la lista guardada en este aparato
            (base / "personal_estado.js").unlink()
            pg2 = ctx.new_page()
            pg2.on("pageerror", lambda e: errores.append(str(e)))
            pg2.goto(url)
            pg2.wait_for_selector("#obra", timeout=8000)
            self.assertIn("lista guardada", pg2.evaluate("document.querySelector('#estado-origen').textContent"))
            recogidos.extend(pg2.evaluate(JS_TEXTOS))
            nav.close()
        self.assertEqual([], errores, "errores de JavaScript mientras se recorría la app")
        self.assertGreater(len(set(recogidos)), 40, "se han revisado muy pocos textos de la app: el recorrido no ha llegado a las pantallas")
        problemas = revisar(recogidos, "app")
        self.assertEqual([], sorted(set(problemas)), "\n".join(sorted(set(problemas))[:30]))

    def test_los_avisos_de_antes_de_guardar_no_usan_palabras_de_programador(self):
        """Paso MA2: el aviso de antes de guardar (día con gente, fin de semana, día futuro, 0 horas), sus tres respuestas y el
        resumen de lo guardado, sustituido y saltado se escriben en lenguaje de electricista."""
        from playwright.sync_api import sync_playwright

        base = Path(os.environ.get("P3_TMP") or tempfile.gettempdir()) / ("lenguaje_avisos_" + uuid.uuid4().hex[:8])
        base.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(base), True)
        for nombre in ("generador_personal.html", "personal_calculo.js"):
            shutil.copy(APP_DIR / nombre, base / nombre)
        (base / "personal_estado.js").write_text("window.SAGARDE_PERSONAL = " + json.dumps(_estado(), ensure_ascii=False) + ";\n", encoding="utf-8")
        url = "file:///" + str(base).replace(os.sep, "/").replace(" ", "%20") + "/generador_personal.html"
        recogidos = []
        with sync_playwright() as p:
            nav = p.chromium.launch()
            ctx = nav.new_context(viewport={"width": 390, "height": 844}, timezone_id="Europe/Madrid", locale="es-ES")
            ctx.add_init_script(FECHA_FIJA)
            pg = ctx.new_page()
            pg.set_default_timeout(4000)
            errores = []
            pg.on("pageerror", lambda e: errores.append(str(e)))

            def mirar():
                recogidos.extend(pg.evaluate(JS_TEXTOS))

            def clic(sel):
                pg.click(sel, timeout=4000)
                mirar()

            def preparar(dias, principal):
                # días marcados con la lista de siempre, solo Mikel y con las horas sin tocar (siguen el horario de cada día)
                pg.evaluate("([d, p]) => { a.fechas = d; a.fecha = p; a.calMes = p.slice(0, 7); a.list.forEach((x) => { x.on = x.nombre === 'Mikel'; x.horas = null; }); render(); }", [dias, principal])

            pg.goto(url)
            pg.wait_for_selector("#obra")
            todos = ["2026-10-21", "2026-10-22", "2026-10-24", "2026-10-25"]
            # 1) los cuatro avisos a la vez; se salta lo que ya tenía gente
            preparar(todos, "2026-10-21")
            clic("button[data-guardar]")
            self.assertTrue(pg.query_selector("#aviso-guardar"), "no ha salido el aviso de antes de guardar")
            clic('#aviso-guardar button[data-guardar-modo="saltar"]')
            # 2) los mismos días otra vez: ahora se sustituye lo que había
            preparar(["2026-10-21", "2026-10-22"], "2026-10-21")
            pg.evaluate("a.list.forEach((x) => { x.on = x.nombre === 'Txomin'; x.horas = null; }); render()")
            clic("button[data-guardar]")
            clic('#aviso-guardar button[data-guardar-modo="seguir"]')
            clic("#resumen-guardado button[data-cerrar-resumen]")
            # 3) un aviso y «No guardar nada»
            preparar(["2026-10-21", "2026-10-22"], "2026-10-21")
            clic("button[data-guardar]")
            clic('#aviso-guardar button[data-guardar-modo="cancelar"]')
            # 4) todos los días ocupados y «saltar» a mano: no se guarda ninguno
            preparar(["2026-10-21"], "2026-10-22")
            pg.evaluate("a.list.forEach((x) => { x.on = x.nombre === 'Mikel'; x.horas = null; }); a.listaDe = null; render()")
            clic("button[data-guardar]")
            pg.evaluate("save({ modo: 'saltar', firma: a.aviso.firma })")
            mirar()
            nav.close()
        self.assertEqual([], errores, "errores de JavaScript mientras se recorrían los avisos")
        todo = " ".join(recogidos)
        for frase in ("Todavía no se ha guardado nada", "ya hay 2 personas (ya en el PC)", "son fin de semana", "todavía no han llegado", "se guardaría con 0 horas",
                      "Si no quieres 0 horas", "Sustituir y guardar", "Saltar los días que ya tienen gente", "No guardar nada", "Así ha quedado",
                      "jornadas guardadas", "sustituida", "sin guardar porque ya tenía", "No se ha guardado nada.", "No se ha guardado ningún día"):
            self.assertIn(frase, todo, "falta en lo revisado: " + frase)
        problemas = revisar(recogidos, "avisos de antes de guardar")
        self.assertEqual([], sorted(set(problemas)), "\n".join(sorted(set(problemas))[:30]))

    def test_el_campo_empresa_de_la_app_tampoco_usa_palabras_de_programador(self):
        """Recorre todos los estados del campo Empresa (08c2a): desplegables, errores, avisos, resúmenes y «Enviar al PC»."""
        from playwright.sync_api import sync_playwright

        base = Path(os.environ.get("P3_TMP") or tempfile.gettempdir()) / ("lenguaje_emp_" + uuid.uuid4().hex[:8])
        base.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(base), True)
        for nombre in ("generador_personal.html", "personal_calculo.js"):
            shutil.copy(APP_DIR / nombre, base / nombre)
        (base / "personal_estado.js").write_text(
            "window.SAGARDE_PERSONAL = " + json.dumps(_estado_empresas(), ensure_ascii=False) + ";\n", encoding="utf-8")
        url = "file:///" + str(base).replace(os.sep, "/").replace(" ", "%20") + "/generador_personal.html"
        recogidos = []
        with sync_playwright() as p:
            nav = p.chromium.launch()
            ctx = nav.new_context(viewport={"width": 390, "height": 844}, timezone_id="Europe/Madrid", locale="es-ES", accept_downloads=True)
            ctx.add_init_script(FECHA_FIJA)
            pg = ctx.new_page()
            pg.set_default_timeout(4000)
            errores = []
            pg.on("pageerror", lambda e: errores.append(str(e)))

            def mirar():
                recogidos.extend(pg.evaluate(JS_TEXTOS))

            def clic(sel):
                pg.click(sel, timeout=4000)
                mirar()

            pg.goto(url)
            pg.wait_for_selector("#obra")
            mirar()
            # nombre nuevo: «Otra empresa…» sin escribir, con un teléfono, y bien; el nombre de alguien que ya está con otra empresa
            pg.select_option("#nuevo-empresa", "__otra__")
            mirar()
            pg.fill("#nuevo", "Nerea")
            clic("button[data-nuevo]")
            pg.fill("#nuevo", "Nerea")
            pg.select_option("#nuevo-empresa", "__otra__")
            pg.fill("#nuevo-empresa-otra", "612 345 678")
            clic("button[data-nuevo]")
            pg.fill("#nuevo", "Nerea")
            pg.select_option("#nuevo-empresa", "Manueles")
            clic("button[data-nuevo]")
            pg.fill("#nuevo", "mikel")
            pg.select_option("#nuevo-empresa", "Rafa @AUT")
            clic("button[data-nuevo]")
            clic("button[data-hom-si]")             # MA4c: «Ya hay un «Mikel» (Manueles). ¿Es el mismo?» → «Sí»
            pg.fill("#nuevo", "Txomi")
            clic("button[data-nuevo]")
            clic("button[data-usar]")
            # lápiz: solo la empresa, sin empresa, y nombre + empresa nueva con sus errores
            clic("button[data-ren='0']")
            pg.select_option("#ren-empresa", "Sagarde")
            mirar()
            clic("button[data-ren-guardar]")
            clic("button[data-ren='0']")
            pg.select_option("#ren-empresa", "")
            clic("button[data-ren-guardar]")
            clic("button[data-ren='0']")
            pg.fill("#ren-campo", "Mikel Z")
            pg.select_option("#ren-empresa", "__otra__")
            clic("button[data-ren-guardar]")
            pg.fill("#ren-empresa-otra", "Obras Z")
            clic("button[data-ren-guardar]")
            # varios nombres con empresa: entran, ya estaban, se les pone, ya tienen otra, no valen y parecidos
            clic("button[data-varios]")
            pg.fill("#varios-texto", "Iker, Manueles\nMikel Z, Sagarde\nTxomin, Sagarde\nRafa, Manueles\n, Ona\nLuz, 612345678\nTxomi, Sagarde")
            clic("button[data-varios-ok]")
            # las mismas frases en singular y en plural: uno que ya tiene otra empresa, y dos a los que se les pone la empresa
            pg.fill("#varios-texto", "Mikel Z, Sagarde\nUno\nDos")
            clic("button[data-varios-ok]")
            pg.fill("#varios-texto", "Uno, Manueles\nDos, Manueles")
            clic("button[data-varios-ok]")
            clic("button[data-varios-cerrar]")
            # enviar al PC con empresas y el recuadro «Listo»
            clic('nav button[data-v="enviar"]')
            with pg.expect_download(timeout=5000):
                pg.click("button[data-preparar]")
            mirar()
            nav.close()
        self.assertEqual([], errores, "errores de JavaScript mientras se recorría el campo Empresa")
        texto = "\n".join(recogidos)
        # Un recuento de cero es una alarma: el recorrido tiene que haber pasado de verdad por cada estado nuevo.
        for esperado in ("Sin empresa", "Otra empresa…", "Escribe la empresa.", "Esa empresa no vale: parece un teléfono.",
                         "Ya hay un «Mikel» (Manueles). ¿Es el mismo?", "Se ha apuntado a «Mikel» (Manueles). Su empresa no se cambia", "Empresa de «Mikel»: ahora «Sagarde»", "se queda sin empresa",
                         "Nombre corregido: «Mikel» ahora es «Mikel Z», empresa «Obras Z»", "con empresa.",
                         "Se le pone la empresa a 1", "Se les pone la empresa a 2", "Ya hay un «Mikel Z» (Obras Z): «Mikel Z» no entra", "Ya hay estos nombres con otra empresa", "falta el nombre", "4 empresas puestas"):
            self.assertIn(esperado, texto, "el recorrido no ha llegado a este texto: «%s»" % esperado)
        self.assertGreater(len(set(recogidos)), 40)
        problemas = revisar(recogidos, "app (empresas)")
        self.assertEqual([], sorted(set(problemas)), "\n".join(sorted(set(problemas))[:30]))

    def test_las_preguntas_de_dos_personas_con_el_mismo_nombre_no_usan_palabras_de_programador(self):
        """MA4c: recorre la pregunta «¿es el mismo o es otra persona?» de la tablet (sí, no, errores, cancelar, de baja), la ayuda del
        lápiz, «Añadir varios nombres» con un nombre que ya existe y el recuadro de dos iguales publicados."""
        from playwright.sync_api import sync_playwright

        base = Path(os.environ.get("P3_TMP") or tempfile.gettempdir()) / ("lenguaje_hom_" + uuid.uuid4().hex[:8])
        base.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(base), True)
        for nombre in ("generador_personal.html", "personal_calculo.js"):
            shutil.copy(APP_DIR / nombre, base / nombre)
        estado = _estado_empresas()
        estado["catalogo"].append({"id": "T0090", "nombre": "Zuri", "categoria": "", "empresa": "Manueles", "activo": False})
        (base / "personal_estado.js").write_text("window.SAGARDE_PERSONAL = " + json.dumps(estado, ensure_ascii=False) + ";" + chr(10), encoding="utf-8")
        url = "file:///" + str(base).replace(os.sep, "/").replace(" ", "%20") + "/generador_personal.html"
        recogidos = []
        with sync_playwright() as p:
            nav = p.chromium.launch()
            ctx = nav.new_context(viewport={"width": 390, "height": 844}, timezone_id="Europe/Madrid", locale="es-ES")
            ctx.add_init_script(FECHA_FIJA)
            pg = ctx.new_page()
            pg.set_default_timeout(4000)
            errores = []
            pg.on("pageerror", lambda e: errores.append(str(e)))

            def mirar():
                recogidos.extend(pg.evaluate(JS_TEXTOS))

            def clic(sel):
                pg.click(sel, timeout=4000)
                mirar()

            pg.goto(url)
            pg.wait_for_selector("#obra")
            mirar()
            # nombre nuevo con otra empresa: pregunta, «No», errores, «Cancelar», «No» + apellido
            pg.fill("#nuevo", "Mikel")
            pg.select_option("#nuevo-empresa", "Rafa @AUT")
            clic("button[data-nuevo]")
            clic("button[data-hom-no]")
            for malo in ("Mikel", "Txomin", "x@y.es"):
                pg.fill("#homonimo-campo", malo)
                clic("button[data-hom-crear]")
            clic("button[data-hom-cancelar]")
            pg.fill("#nuevo", "Mikel")
            pg.select_option("#nuevo-empresa", "Rafa @AUT")
            clic("button[data-nuevo]")
            clic("button[data-hom-no]")
            pg.fill("#homonimo-campo", "Mikel B.")
            clic("button[data-hom-crear]")
            # sin conflicto: lo apunta y dice cómo crear a otro; de baja: pregunta y «Sí»
            pg.fill("#nuevo", "txomin")
            clic("button[data-nuevo]")
            pg.fill("#nuevo", "Zuri")
            clic("button[data-nuevo]")
            clic("button[data-hom-si]")
            # lápiz: «Ya hay un… ¿Son la misma persona?» y «No» con su ayuda
            clic("button[data-ren='0']")
            pg.fill("#ren-campo", "Txomin")
            clic("button[data-ren-guardar]")
            clic("button[data-ren-no]")
            # varios: uno que ya existe con otra empresa (singular) y dos (plural)
            clic("button[data-varios]")
            pg.fill("#varios-texto", "Mikel, Sagarde")
            clic("button[data-varios-ok]")
            pg.fill("#varios-texto", "Mikel, Sagarde" + chr(10) + "Rafa, Manueles")
            clic("button[data-varios-ok]")
            nav.close()
        self.assertEqual([], errores, "errores de JavaScript mientras se recorría la pregunta de dos personas con el mismo nombre")
        texto = chr(10).join(recogidos)
        for esperado in ("¿Es el mismo?", "Sí, es el mismo", "No, es otra persona", "Ponle algo que lo distinga del otro «Mikel»",
                         "Tiene que ser distinto de «Mikel»: añade un apellido o una inicial.", "Ya hay un «Txomin». Elige otro.",
                         "Ese nombre no vale: parece un correo.", "ya estaba en la base: lo he apuntado en la lista",
                         "estaba de baja. ¿Es el mismo, que vuelve?", "Se ha apuntado a «Zuri»",
                         "y estás corrigiendo a «Mikel»", "Si son dos personas distintas, ponle un apellido o una inicial",
                         "no entra. Si es otra persona, escríbela con un apellido o una inicial",
                         "Ya hay estos nombres con otra empresa"):
            self.assertIn(esperado, texto, "el recorrido no ha llegado a este texto: «%s»" % esperado)
        problemas = revisar(recogidos, "app (dos personas con el mismo nombre)")
        self.assertEqual([], sorted(set(problemas)), chr(10).join(sorted(set(problemas))[:30]))

    def test_el_aviso_de_dos_iguales_publicados_no_usa_palabras_de_programador(self):
        from playwright.sync_api import sync_playwright

        base = Path(os.environ.get("P3_TMP") or tempfile.gettempdir()) / ("lenguaje_dos_" + uuid.uuid4().hex[:8])
        base.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(base), True)
        for nombre in ("generador_personal.html", "personal_calculo.js"):
            shutil.copy(APP_DIR / nombre, base / nombre)
        estado = _estado_empresas()
        estado["catalogo"] += [{"id": "T0092", "nombre": "Rafa", "categoria": "", "empresa": "Sagarde", "activo": True},
                               {"id": "T0093", "nombre": "Rafa", "categoria": "", "empresa": "Manueles", "activo": True},
                               {"id": "T0094", "nombre": "Rafa", "categoria": "", "empresa": "", "activo": True}]
        (base / "personal_estado.js").write_text("window.SAGARDE_PERSONAL = " + json.dumps(estado, ensure_ascii=False) + ";" + chr(10), encoding="utf-8")
        url = "file:///" + str(base).replace(os.sep, "/").replace(" ", "%20") + "/generador_personal.html"
        with sync_playwright() as p:
            nav = p.chromium.launch()
            ctx = nav.new_context(viewport={"width": 390, "height": 844}, timezone_id="Europe/Madrid", locale="es-ES")
            ctx.add_init_script(FECHA_FIJA)
            pg = ctx.new_page()
            pg.set_default_timeout(4000)
            pg.goto(url)
            pg.wait_for_selector("#obra")
            recogidos = pg.evaluate(JS_TEXTOS)
            nav.close()
        texto = chr(10).join(recogidos)
        self.assertIn("En la lista del PC hay personas con el mismo nombre", texto)
        self.assertEqual([], sorted(set(revisar(recogidos, "app (dos iguales)"))))


class TestLenguajeDeLaSumaPorEmpresa(unittest.TestCase):
    """Paso 08c2b: el bloque «Por empresa» se escribe una sola vez (personal_calculo.js) y lo enseñan los cuatro sitios, así que se
    revisan todos sus estados: con autónomos, sin empresas, con alguien que sale con dos empresas, y su nota y su aviso."""

    GUION = """
const C = require(process.argv[2]);
const f = (nombre, empresa, horas, fecha) => ({ fecha: fecha || '2026-10-19', ambito: 'vivienda', nombre, horas: horas || 7.5, extra: 0, empresa });
const casos = [
  [f('Ana', 'Manueles'), f('Beto', 'CATERSYSTEM'), f('Dani', 'Dani @AUT'), f('Eli', 'Eli@aut'), f('Fran', '')],
  [f('Ana', ''), f('Beto', '')],
  [f('Ana', 'Manueles'), f('Ana', 'CATERSYSTEM', 7.5, '2026-10-20')],
  [f('Ana', 'Manueles', 7.5), f('Beto', 'Manueles', 7.5)],
  [],
];
const salida = casos.map(c => C.htmlPorEmpresa(C.agregarPorEmpresa(c), {}));
salida.push(C.textoAvisoEmpresas(C.agregarPorEmpresa(casos[2])));
console.log(JSON.stringify(salida));
"""

    def test_el_bloque_por_empresa_no_usa_palabras_de_programador(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("falta node: NO se ha revisado el lenguaje del bloque «Por empresa»")
        base = Path(os.environ.get("P3_TMP") or tempfile.gettempdir()) / ("lenguaje_suma_" + uuid.uuid4().hex[:8])
        base.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(base), True)
        guion = base / "bloques.js"
        guion.write_text(self.GUION, encoding="utf-8")
        p = subprocess.run([node, str(guion), str(APP_DIR / "personal_calculo.js")], capture_output=True, timeout=60)
        self.assertEqual(0, p.returncode, p.stderr.decode("utf-8", "replace"))
        bloques = json.loads(p.stdout.decode("utf-8"))
        textos = []
        for bloque in bloques:
            textos.extend(t.strip() for t in re.findall(r">([^<>]+)<", bloque) if t.strip())
        textos.append(bloques[-1])
        self.assertGreater(len(textos), 40, "se han revisado muy pocos textos del bloque «Por empresa»: la guarda no está mirando lo que debe")
        todo = " ".join(textos)
        for frase in ("Por empresa", "Sin empresa", "Total autónomos (@AUT)", "no se suman otra vez", "con más de una empresa"):
            self.assertIn(frase, todo, "falta en lo revisado: " + frase)
        problemas = revisar(textos, "suma por empresa")
        self.assertEqual([], sorted(set(problemas)), chr(10).join(sorted(set(problemas))[:30]))


class TestLenguajeDelPC(unittest.TestCase):
    def test_los_avisos_y_las_lineas_del_pc_no_usan_palabras_de_programador(self):
        textos = textos_del_pc()
        self.assertGreater(len(textos), 80, "se han revisado muy pocos textos del PC: la guarda no está mirando lo que debe")
        problemas = revisar(textos, "PC")
        self.assertEqual([], sorted(set(problemas)), "\n".join(sorted(set(problemas))[:30]))

    def test_los_codigos_de_aviso_se_encuentran_todos(self):
        codigos = _codigos_de_texto_aviso()
        self.assertGreater(len(codigos), 25, "no se han encontrado los códigos de personal_obra.texto_aviso: %s" % codigos)
        for esperado in ("alta_nueva", "nombre_parecido", "suma_diaria_alta", "fecha_futura", "reemplazo", "traza_no_escrita",
                         "renombre_coincide_con_otro", "empresa_invalida", "empresa_sin_persona"):
            self.assertIn(esperado, codigos)


class TestLenguajeSinCobertura(unittest.TestCase):
    """MA3: los textos de cobertura (etiquetas y avisos) que Bixente lee en un garaje sin red, en lenguaje de electricista."""

    def _textos(self):
        html = (APP_DIR / "generador_personal.html").read_text(encoding="utf-8")
        bloque = re.search(r"const COB = \{(.*?)\n      \};", html, re.S)
        self.assertIsNotNone(bloque, "no se encuentra el bloque «const COB» con los textos de cobertura")
        pares = re.findall(r'^\s+(\w+): ("(?:[^"\\]|\\.)*"),$', bloque.group(1), re.M)
        return {nombre: json.loads(valor) for nombre, valor in pares}

    def test_los_textos_de_cobertura_no_usan_palabras_de_programador(self):
        textos = self._textos()
        self.assertEqual(8, len(textos), "una lista vacía o corta de textos es una alarma, no «no aplica»: %s" % sorted(textos))
        problemas = revisar([t.replace("{fecha}", "28/10").replace("{n}", "3") for t in textos.values()], "cobertura")
        self.assertEqual([], problemas, problemas)

    def test_las_tres_etiquetas_dicen_lo_que_toca(self):
        t = self._textos()
        self.assertTrue(t["con"].startswith("Con cobertura:"), t["con"])
        self.assertTrue(t["sin"].startswith("Sin cobertura:") and "{fecha}" in t["sin"], t["sin"])
        self.assertTrue(t["nada"].startswith("Sin datos todavía:") and "cobertura" in t["nada"], t["nada"])
        self.assertIn("{n}", t["sinLista"])
        self.assertIn("a salvo", t["sinLista"])
        self.assertIn("primera vez", t["informe"])


class TestLenguajeEnviarCon(unittest.TestCase):
    """MA7: los textos de «Enviar con…» (la explicación de las dos maneras, el «Listo» y los dos avisos) en lenguaje de electricista."""

    def _textos(self):
        html = (APP_DIR / "generador_personal.html").read_text(encoding="utf-8")
        bloque = re.search(r"const COMP = \{(.*?)\n      \};", html, re.S)
        self.assertIsNotNone(bloque, "no se encuentra el bloque «const COMP» con los textos de «Enviar con…»")
        textos = {}
        for nombre, cuerpo in re.findall(r"^\s+(\w+):\s*((?:'(?:[^'\\]|\\.)*'(?:\s*\+\s*)?\s*)+),$", bloque.group(1), re.M):
            textos[nombre] = "".join(json.loads('"' + t.replace('"', '\\"') + '"') for t in re.findall(r"'((?:[^'\\]|\\.)*)'", cuerpo))
        return textos

    def test_los_textos_de_enviar_con_no_usan_palabras_de_programador(self):
        textos = self._textos()
        self.assertEqual(["denegado", "error", "listo", "vias"], sorted(textos), "una lista vacía o corta de textos es una alarma, no «no aplica»: %s" % sorted(textos))
        problemas = revisar([t.replace("{nombre}", "CONTROL HORARIO X 23102026").replace("{contenido}", "2 jornadas") for t in textos.values()], "enviar con")
        self.assertEqual([], problemas, problemas)

    def test_dicen_lo_que_toca(self):
        t = self._textos()
        self.assertIn("«Enviar con…»", t["vias"])
        self.assertIn("«Preparar el fichero para el PC»", t["vias"])
        self.assertIn("REVISIONES", t["vias"])
        self.assertIn("OneDrive", t["vias"])
        self.assertIn("mismo fichero", t["vias"])
        self.assertTrue(t["listo"].startswith("Listo."), t["listo"])
        self.assertIn("{nombre}", t["listo"])
        self.assertIn("{contenido}", t["listo"])
        self.assertIn("REVISIONES", t["listo"])
        for clave in ("denegado", "error"):
            self.assertIn("«Preparar el fichero para el PC»", t[clave])
            self.assertIn("no se pierde nada", t[clave])


@unittest.skipUnless(_OK, "NO se ha revisado el lenguaje de «Generar personal»: %s" % _MOTIVO)
class TestLenguajeDeGenerarPersonal(unittest.TestCase):
    """MA5: la guarda mira la pestaña «Generar personal» de personal_sagarde.html en un navegador de verdad, como hace con la tablet.
    Recorre cada estado (vacío, empresa nueva, añadir, errores, parecidos, preguntas, bajas, editar, quitar oficio y horario, lista
    preparada, fichero guardado y sus tres pasos, «¿seguro?», lo recuperado al recargar, lo ya aplicado, almacenamiento bloqueado,
    lo guardado que no se puede leer, página sin datos o sin cálculo). Una lista vacía de textos es una alarma, no un «no aplica»:
    se exige un mínimo de textos distintos y que hayan salido las frases que cada estado tiene que enseñar."""

    # Frases que TIENEN que haber salido en el recorrido: si falta una, la guarda no ha pasado por ese estado.
    ESPERADOS = [
        "Tienes 3 cambios sin enviar", "¿Seguro?", "carpeta REVISIONES de cualquier obra", "actualiza la obra", "Quitar oficio",
        "Volver a horario normal", "se ha marcado para quitar de la base de trabajadores", "¿Es el mismo, que", "Ponle algo que lo distinga",
        "Se han recuperado", "ya está aplicado", "no deja guardar lo preparado", "no se ha podido leer", "Escribe al menos el nombre",
        "parece un DNI, un teléfono o un correo", "Revisa las horas del horario personalizado", "Todavía no hay datos de personal publicados",
        "No se pudo cargar personal_calculo.js", "no se han podido recuperar", "se parece a", "Cambio preparado", "Se quitará de la base",
        "Trabajador nuevo", "Cambia de empresa", "Quita el oficio", "Fichero guardado con", "Escribe el nombre de la empresa nueva",
        "no tiene el formato esperado", "se queda sin oficio", "vuelve al horario normal", "Datos de «", "Todavía no has añadido ni quitado",
    ]
    MINIMO_DE_TEXTOS = 200

    def test_ningun_estado_de_generar_personal_usa_palabras_de_programador(self):
        import ayudante_generar as A

        recogidos = []

        def ver(page):
            recogidos.extend(page.evaluate(JS_TEXTOS))

        def recorrido(page, carpeta):
            ver(page)                                                      # vacío
            page.select_option("#gen-empresa", "__nueva__")
            ver(page)                                                      # empresa nueva sin nombre
            page.click("#btn-gen-anadir")
            ver(page)                                                      # error: falta la empresa nueva
            page.fill("#gen-empresa-nueva", "Montajes Norte")
            page.select_option("#gen-categoria", "__otra__")
            page.fill("#gen-categoria-otra", "Peón")
            page.select_option("#gen-horario-tipo", "personalizado")
            ver(page)                                                      # horario por día
            page.fill("#gen-nombre", "Koldo Agirre")
            page.click("#btn-gen-anadir")
            ver(page)                                                      # añadido + lista + «sin enviar»
            for malo in ("", "12345678Z", "Ana <b>", "Ana ana@correo.es"):  # errores de nombre
                page.fill("#gen-nombre", malo)
                page.click("#btn-gen-anadir")
                ver(page)
            for dia in ("lun", "mar", "mie", "jue", "vie", "sab", "dom"):
                page.fill('[data-gen-dia="%s"]' % dia, "")
            page.fill("#gen-nombre", "Ione Sasia")
            page.click("#btn-gen-anadir")
            ver(page)                                                      # horario sin horas
            page.fill('[data-gen-dia="lun"]', "99")
            page.click("#btn-gen-anadir")
            ver(page)                                                      # horas fuera de 0 a 24
            page.select_option("#gen-horario-tipo", "normal")
            page.select_option("#gen-empresa", A.ALFA)
            page.select_option("#gen-categoria", "")
            page.fill("#gen-nombre", "Rafaa")
            page.click("#btn-gen-anadir")
            ver(page)                                                      # se parece a otro
            page.click("#btn-gen-confirmar-parecido")
            ver(page)
            page.click('[data-gen-modo="varios"]')
            page.click("#btn-gen-anadir")
            ver(page)                                                      # varios, lista vacía
            page.fill('[data-gen-var-nom="0"]', "Uno Dos")
            page.fill('[data-gen-var-nom="1"]', "Rafa")
            page.click("#btn-gen-mas-lineas")
            ver(page)
            page.click("#btn-gen-anadir")
            ver(page)                                                      # varios: ya está / añadido
            page.click('[data-gen-modo="uno"]')
            A.anadir(page, "Luis", A.ALFA)
            ver(page)                                                      # pregunta: ¿es el mismo?
            page.click("#btn-gen-hom-no")
            ver(page)
            page.fill("#gen-hom-campo", "Luis")
            page.click("#btn-gen-hom-crear")
            ver(page)                                                      # error: tiene que ser distinto
            page.fill("#gen-hom-campo", "Luis B.")
            page.click("#btn-gen-hom-crear")
            ver(page)
            A.anadir(page, "Luis", A.ALFA)
            page.click("#btn-gen-hom-si")
            ver(page)                                                      # el mismo: pasa de Beta a Alfa
            A.anadir(page, "Ander", A.ALFA)
            ver(page)                                                      # de baja
            page.click("#btn-gen-hom-cancelar")
            ver(page)
            page.click('[data-gen-quitar-oficio="Rafa"]')
            ver(page)
            page.click('[data-gen-quitar-horario="Rafa"]')
            ver(page)
            page.click('[data-gen-editar-emp="Rafa"]')
            ver(page)                                                      # Editar
            page.select_option("#gen-empresa", "Sagarde")
            page.click('[data-gen-baja="Zoilo"]')
            ver(page)                                                      # baja
            page.click('[data-gen-deshacer-baja="Zoilo"]')
            ver(page)
            page.click('[data-gen-baja="Zoilo"]')
            A.descargar(page)
            ver(page)                                                      # fichero guardado y sus tres pasos
            page.click("#btn-gen-vaciar")
            ver(page)                                                      # ¿seguro?
            page.click("#btn-gen-vaciar-no")
            A.recargar(page, carpeta)
            ver(page)                                                      # recuperado al recargar
            e = A.estado()
            e["catalogo"].append(D.ficha(6, "Koldo Agirre", "Montajes Norte", categoria="Peón",
                                         horario_preferido={"lun": 7.5, "mar": 7.5, "mie": 7.5, "jue": 7.5, "vie": 7.5, "sab": 0, "dom": 0}))
            A.recargar(page, carpeta, e)
            ver(page)                                                      # lo que el PC ya aplicó
            page.click("#btn-gen-vaciar")
            page.click("#btn-gen-vaciar-si")
            ver(page)                                                      # vacío otra vez

        errores = A.con_pagina(recorrido)
        self.assertEqual(errores, [], "errores de JavaScript en la página")

        def memoria_bloqueada(page, carpeta):
            A.anadir(page, "Nuevo Uno", A.ALFA)
            ver(page)
        bloqueo = ("(() => { const t = () => { throw new DOMException('bloqueado', 'SecurityError'); };"
                   " Object.defineProperty(window, 'localStorage', { get: t, configurable: true }); })();")
        self.assertEqual(A.con_pagina(memoria_bloqueada, init=bloqueo), [])

        def sembrar(valor):
            return ("(() => { try { if (!window.sessionStorage.getItem('sembrado')) { window.localStorage.setItem(%s, %s);"
                    " window.sessionStorage.setItem('sembrado', '1'); } } catch (e) {} })();" % (json.dumps(A.CLAVE_BORRADOR), json.dumps(valor)))
        self.assertEqual(A.con_pagina(lambda page, carpeta: ver(page), init=sembrar("esto no es un texto guardado")), [])
        malo = {"version": 1, "guardado": "2026-10-31T09:15:00.000Z", "descargado": None, "bajas": [{"nombre": "<b>x</b>"}],
                "preparados": [{"nombre": "Bien Uno", "empresa": A.ALFA}, {"nombre": 5}]}
        self.assertEqual(A.con_pagina(lambda page, carpeta: ver(page), init=sembrar(json.dumps(malo))), [])

        # Páginas que no llegan a enseñar la pestaña: sin datos, con datos de otra versión, sin el cálculo
        def esperar_texto(page, carpeta):
            page.wait_for_selector("#contenido-generar .empty, #contenido-generar .aviso", state="attached")
            ver(page)
        A.con_pagina(esperar_texto, con_estado=False, ir_a_generar=False)
        A.con_pagina(esperar_texto, e={"version": 2}, ir_a_generar=False, esperar=False)
        A.con_pagina(esperar_texto, con_calculo=False, ir_a_generar=False)

        texto = chr(10).join(recogidos)
        distintos = sorted(set(recogidos))
        self.assertGreaterEqual(len(distintos), self.MINIMO_DE_TEXTOS, "la guarda de «Generar personal» ha revisado muy pocos textos: %d" % len(distintos))
        faltan = [f for f in self.ESPERADOS if f not in texto]
        self.assertEqual(faltan, [], "la guarda no ha pasado por estos estados de «Generar personal»")
        self.assertEqual([], sorted(set(revisar(recogidos, "Generar personal"))))

    def test_la_guarda_de_generar_lee_la_pagina_que_se_publica(self):
        self.assertTrue((APP_DIR / "personal_sagarde.html").exists())
        fuente = Path(__file__).read_text(encoding="utf-8")
        self.assertIn("personal_sagarde", fuente, "esta guarda tiene que nombrar la página que vigila")


class TestElDetectorDeLenguaje(unittest.TestCase):
    """El detector tiene que saltar con lo que se prohíbe (si no, la guarda que «no encuentra nada» no prueba nada)."""

    def test_salta_con_las_palabras_prohibidas(self):
        for texto, regla in [
            ("Exportar pendientes", "exportar"), ("Exportadas 1 jornada", "exportar"), ("2 jornada(s) pendiente(s)", "pendiente"),
            ("Importar el lote", "importar"), ("Ingerir el fichero", "ingerir"), ("un fichero JSON", "fichero JSON"),
            ("alta nueva", "alta"), ("la base de datos", "base de datos"), ("Estado publicado", "estado"),
            ("una simulación", "simulación"), ("alta_nueva Asensio", "código interno"), ("3 horario(s) propio(s)", "jornada(s)"),
        ]:
            self.assertTrue([r for r, _ in palabras_prohibidas(texto) if regla in r], "el detector no salta con «%s»" % texto)

    def test_no_salta_con_lenguaje_de_electricista(self):
        for texto in ["Enviar al PC", "Sin enviar al PC: 3 jornadas", "Borrar lo que llevo a medias", "horario especial 9 h",
                      "Lista de trabajadores y obras al día: 25/10/2026 15:59", "Con cobertura: datos al día",
                      "Sin cobertura: usando la lista del 28/10",
                      "Es importante mirar la carpeta REVISIONES", "Nombre nuevo: «Asensio» no estaba en la base; se añade.",
                      "Por empresa", "Sin empresa", "Total autónomos (@AUT)", "Hay una persona con más de una empresa (Ana)"]:
            self.assertEqual([], palabras_prohibidas(texto), texto)


if __name__ == "__main__":
    unittest.main()
