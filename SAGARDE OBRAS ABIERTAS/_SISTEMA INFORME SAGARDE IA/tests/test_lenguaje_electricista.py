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
            # día nuevo con la gente anterior marcada (rótulo) y sin gente
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
                         "ya tiene la empresa «Manueles»", "Empresa de «Mikel»: ahora «Sagarde»", "se queda sin empresa",
                         "Nombre corregido: «Mikel» ahora es «Mikel Z», empresa «Obras Z»", "con empresa.",
                         "Se le pone la empresa a 1", "Se les pone la empresa a 2", "Ya tiene otra empresa: «Mikel Z»", "Ya tienen otra empresa", "falta el nombre", "4 empresas puestas"):
            self.assertIn(esperado, texto, "el recorrido no ha llegado a este texto: «%s»" % esperado)
        self.assertGreater(len(set(recogidos)), 40)
        problemas = revisar(recogidos, "app (empresas)")
        self.assertEqual([], sorted(set(problemas)), "\n".join(sorted(set(problemas))[:30]))


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
                      "Lista de trabajadores y obras al día: 25/10/2026 15:59", "Funciona sin cobertura: sí",
                      "Es importante mirar la carpeta REVISIONES", "Nombre nuevo: «Asensio» no estaba en la base; se añade."]:
            self.assertEqual([], palabras_prohibidas(texto), texto)


if __name__ == "__main__":
    unittest.main()
