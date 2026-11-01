# -*- coding: utf-8 -*-
"""MA5 · «Generar personal» (pestaña de personal_sagarde.html): que no engañe, que no pierda lo preparado y que se vea en el móvil.

F8  el final del flujo dice el nombre exacto del fichero y los tres pasos (fichero → carpeta REVISIONES → «actualiza la obra»)
F9  «Quitar oficio» y «Volver a horario normal» se envían de verdad y el PC (lector real) los aplica; un oficio en blanco NO quita nada
F10 lo preparado sobrevive a recargar (localStorage con try/catch), «Empezar de cero» pregunta, lo ya aplicado se quita solo
F11 los horarios salen de una sola fuente (la jornada base que publica el PC y una única lista), no de números escritos a mano
F12 a 360–820 px: sin desborde, sin desplazamiento lateral en las tablas, objetos táctiles de al menos 44 px
F15 el código no trocea cadenas para esquivar una guarda
Chromium real, datos INVENTADOS. El fichero que sale se pasa por el lector del PC de verdad."""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

SISTEMA = Path(__file__).resolve().parent.parent
if str(SISTEMA) not in sys.path:
    sys.path.insert(0, str(SISTEMA))

import ayudante_generar as A  # noqa: E402
import datos_base_trabajadores as D  # noqa: E402
import lector_control_horario as lc  # noqa: E402
import personal_obra as po  # noqa: E402

_OK, _MOTIVO = A.hay_chromium()
APP = A.APP_DIR


def _pc_con_la_base(tmp):
    """Un PC de pruebas con la misma base que la página: Rafa (Alfa, Oficial 1ª y horario de 8 h), Pepe, Luis (Beta), Ander de baja y Zoilo."""
    raiz = Path(tmp)
    obras = {"olabeaga": "2026 OLABEAGA BILBAO", "mungia": "2026 MUNGIA"}
    for o in obras.values():
        (raiz / o / "REVISIONES").mkdir(parents=True, exist_ok=True)
    previo = {"tipo": "lote_personal", "version": 1, "obra": "sagarde", "jornadas": [],
              "altas": ["Rafa", "Pepe", "Luis", "Ander", "Zoilo"],
              "empresas": [{"nombre": "Rafa", "empresa": A.ALFA}, {"nombre": "Luis", "empresa": A.BETA},
                           {"nombre": "Ander", "empresa": A.GAMMA}, {"nombre": "Zoilo", "empresa": "Sagarde"}],
              "categorias": [{"nombre": "Rafa", "categoria": "Oficial 1ª"}],
              "horarios_preferidos": {"Rafa": dict(A.HORARIO_8H)}}
    r = po.ingerir_lote(previo, raiz, obras, "2026-10-22", escribir=True, ahora="2026-10-22T22:00:00+02:00")
    assert r["ok"], r
    r = po.ingerir_lote({"tipo": "lote_personal", "version": 1, "obra": "sagarde", "jornadas": [], "bajas": ["Ander"]},
                        raiz, obras, "2026-10-22", escribir=True, ahora="2026-10-22T22:30:00+02:00")
    assert r["ok"], r
    return raiz, obras


@unittest.skipUnless(_OK, "NO se ha probado «Generar personal»: %s" % _MOTIVO)
class TestGenerarPersonalMA5(unittest.TestCase):
    def pagina(self, fn, **kw):
        errores = A.con_pagina(fn, **kw)
        self.assertEqual(errores, [], "errores de JavaScript en la página")

    # ------------------------------------------------------------------ F9
    def test_quitar_oficio_y_volver_a_horario_normal_se_envian_y_el_pc_los_aplica(self):
        def fn(page, carpeta):
            page.select_option("#gen-empresa", A.ALFA)
            self.assertEqual(A.texto(page, '[data-gen-quitar-oficio="Rafa"]'), "Quitar oficio")
            self.assertEqual(A.texto(page, '[data-gen-quitar-horario="Rafa"]'), "Volver a horario normal")
            page.click('[data-gen-quitar-oficio="Rafa"]')
            self.assertEqual(A.texto(page, "#gen-ok"), "✓ «Rafa» se queda sin oficio (queda preparado; todavía no se ha enviado).")
            self.assertIsNone(page.query_selector('[data-gen-quitar-oficio="Rafa"]'), "sin oficio ya no hay nada que quitar")
            self.assertIn("Quita el oficio", A.filas(page)[0][1])
            page.click('[data-gen-quitar-horario="Rafa"]')
            self.assertEqual(A.texto(page, "#gen-ok"), "✓ «Rafa» vuelve al horario normal (queda preparado; todavía no se ha enviado).")
            self.assertIsNone(page.query_selector('[data-gen-quitar-horario="Rafa"]'))
            self.assertEqual(len(A.filas(page)), 1, "las dos órdenes van en la misma fila")
            self.assertIn("Quita oficio y horario", A.filas(page)[0][1])
            fila_lista = A.texto(page, 'tr[data-emp-trabajador="Rafa"]')
            self.assertNotIn("Oficial 1ª", fila_lista, "la lista de la empresa ya enseña cómo quedará")
            self.assertIn("Normal de la obra (7,5 h L–V)", fila_lista)
            nombre, f = A.descargar(page)
            self.assertNotIn("altas", f, "es la misma persona: no es un nombre nuevo")
            self.assertEqual(f["categorias"], [{"nombre": "Rafa", "categoria": ""}])
            self.assertEqual(f["horarios_preferidos"], {"Rafa": {}})
            self.assertEqual(f["empresas"], [{"nombre": "Rafa", "empresa": A.ALFA}])
            # el PC de verdad, con el fichero en la carpeta REVISIONES de una obra cualquiera: lo entiende, lo dice y lo aplica
            for obra_id in ("olabeaga", "mungia"):
                with tempfile.TemporaryDirectory(prefix="ma5_pc_", dir=str(A.TMP_BASE)) as tmp:
                    raiz, obras = _pc_con_la_base(tmp)
                    ruta = raiz / obras[obra_id] / "REVISIONES" / nombre
                    ruta.write_text(json.dumps(f, ensure_ascii=False, indent=2), encoding="utf-8")
                    candidatos = lc.listar(ruta.parent)
                    self.assertEqual(len(candidatos), 1)
                    an = lc.analizar(obra_id, candidatos, "2026-10-31", raiz, obras)
                    ficha = an["ficheros"][0]
                    self.assertEqual(ficha["estado"], lc.LISTO, ficha)
                    self.assertIn("1 oficio quitado", ficha["resumen"])
                    self.assertIn("1 horario preferido quitado", ficha["resumen"])
                    self.assertFalse(ficha.get("sin_efecto"), "quitar cambia la base: no es «no trae nada nuevo»")
                    ap = lc.aplicar(obra_id, candidatos, "2026-10-31", raiz, obras)
                    self.assertFalse(ap["frena"], ap)
                    rafa = next(t for t in po.cargar_catalogo(raiz)["trabajadores"] if t["nombre"] == "Rafa")
                    self.assertEqual(rafa["categoria"], "")
                    self.assertNotIn("horario_preferido", rafa)
                    self.assertEqual(rafa["empresa"], A.ALFA, "la empresa no se toca")
                    self.assertEqual(po.comprobar(raiz, obras), [])
        self.pagina(fn)

    def test_un_oficio_en_blanco_y_el_horario_normal_del_formulario_no_quitan_nada(self):
        def fn(page, carpeta):
            A.anadir(page, "Rafa", A.ALFA)   # «Sin oficio indicado» y «Horario normal»: quieren decir «no lo toques»
            self.assertEqual(A.texto(page, "#gen-ok"), "✓ «Rafa» ya está en «Alfa Instalaciones»: no hace falta añadirlo.")
            self.assertEqual(A.filas(page), [], "no se prepara nada: Rafa conserva su oficio y su horario")
            self.assertIn("Oficial 1ª", A.texto(page, 'tr[data-emp-trabajador="Rafa"]'))
        self.pagina(fn)

    def test_lo_preparado_antes_no_se_pierde_al_preparar_otra_cosa_de_la_misma_persona(self):
        def fn(page, carpeta):
            A.anadir(page, "Rafa", A.ALFA, oficio="Oficial 2ª")
            A.anadir(page, "Rafa", A.ALFA, oficio="", horario="intensiva")
            fs = A.filas(page)
            self.assertEqual(len(fs), 1)
            self.assertIn("Oficial 2ª", fs[0][1], "el oficio preparado sigue en la fila")
            self.assertIn("Lun 8 h", fs[0][1])
            _, f = A.descargar(page)
            self.assertEqual(f["categorias"], [{"nombre": "Rafa", "categoria": "Oficial 2ª"}])
            self.assertEqual(f["horarios_preferidos"]["Rafa"]["vie"], 6)
        self.pagina(fn)

    def test_la_fila_de_lo_preparado_enseña_el_oficio_que_tendra_aunque_solo_se_cambie_el_horario(self):
        def fn(page, carpeta):
            A.anadir(page, "Rafa", A.ALFA, horario="intensiva")   # Rafa ya es Oficial 1ª: seguirá siéndolo
            fs = A.filas(page)
            self.assertEqual(len(fs), 1)
            self.assertIn("Oficial 1ª", fs[0][1], "antes la fila decía «–» y el fichero no lo quitaba: engañaba")
            _, f = A.descargar(page)
            self.assertNotIn("categorias", f, "el oficio no se toca y no viaja")
        self.pagina(fn)

    def test_cambiar_solo_el_oficio_no_toca_el_horario(self):
        def fn(page, carpeta):
            A.anadir(page, "Rafa", A.ALFA, oficio="Oficial 2ª")   # Rafa tiene horario propio: seguirá teniéndolo
            _, f = A.descargar(page)
            self.assertEqual(f["categorias"], [{"nombre": "Rafa", "categoria": "Oficial 2ª"}])
            self.assertNotIn("horarios_preferidos", f, "el horario no se toca y no viaja (ni vacío)")
        self.pagina(fn)

    def test_quitar_a_quien_tiene_un_cambio_de_empresa_preparado_no_pierde_ese_cambio(self):
        def fn(page, carpeta):
            A.anadir(page, "Rafa", A.BETA)
            page.click("#btn-gen-hom-si")                      # el mismo: pasa de Alfa a Beta
            page.select_option("#gen-empresa", A.BETA)
            page.click('[data-gen-quitar-horario="Rafa"]')
            page.click('[data-gen-quitar-oficio="Rafa"]')
            fs = A.filas(page)
            self.assertEqual(len(fs), 1)
            self.assertIn("Cambia de empresa", fs[0][1])
            self.assertIn("antes: " + A.ALFA, fs[0][1])
            _, f = A.descargar(page)
            self.assertEqual(f["empresas"], [{"nombre": "Rafa", "empresa": A.BETA}], "sigue yendo a Beta")
            self.assertEqual(f["categorias"], [{"nombre": "Rafa", "categoria": ""}])
            self.assertEqual(f["horarios_preferidos"], {"Rafa": {}})
        self.pagina(fn)

    def test_pulsar_el_texto_de_autonomo_marca_la_casilla(self):
        def fn(page, carpeta):
            page.click(".gen-chk", position={"x": 200, "y": 20})   # en el texto, no en la casilla
            self.assertTrue(page.is_checked("#gen-autonomo"), "antes, pulsar el texto abría el desplegable de la empresa")
            A.anadir(page, "Nuevo Uno", A.ALFA)
            self.assertIn(A.ALFA + " @AUT", A.filas(page)[0][1])
        self.pagina(fn)

    # ------------------------------------------------------------------ F8
    def test_al_guardar_el_fichero_se_dice_su_nombre_exacto_y_los_tres_pasos(self):
        def fn(page, carpeta):
            A.anadir(page, "Nuevo Uno", A.ALFA)
            self.assertEqual(A.texto(page, "#gen-sin-enviar"), "Tienes 1 cambio sin enviar. Se guardan en este aparato aunque cierres o recargues la página.")
            self.assertIsNone(page.query_selector("#gen-fichero-guardado"))
            nombre, _ = A.descargar(page)
            sin_ext = nombre[:-len(".json")]
            self.assertRegex(sin_ext, r"^BASE TRABAJADORES SAGARDE \d{8}$")
            caja = A.texto(page, "#gen-fichero-guardado")
            self.assertIn("«" + sin_ext + "»", caja, "el nombre exacto del fichero")
            self.assertIn("REVISIONES", caja)
            self.assertIn("actualiza la obra", caja)
            self.assertIn("la base no cambia", caja)
            pasos = page.eval_on_selector_all("#gen-pasos li", "els => els.map(e => e.innerText.trim())")
            self.assertEqual(len(pasos), 3)
            self.assertTrue(pasos[0].startswith("Se ha guardado el fichero"))
            self.assertIn("carpeta REVISIONES de cualquier obra", pasos[1])
            self.assertIn("actualiza la obra", pasos[2])
            self.assertIsNone(page.query_selector("#gen-sin-enviar"))
            # si luego se toca la lista, el fichero guardado ya no vale: la caja vuelve a decir «sin enviar»
            A.anadir(page, "Otro Dos", A.ALFA)
            self.assertIsNone(page.query_selector("#gen-fichero-guardado"))
            self.assertIn("Tienes 2 cambios sin enviar", A.texto(page, "#gen-sin-enviar"))
        self.pagina(fn)

    # ------------------------------------------------------------------ F10
    def _tres_cambios(self, page):
        A.anadir(page, "Nuevo Uno", A.ALFA)
        A.anadir(page, "Pepe", A.BETA)
        page.select_option("#gen-empresa", A.ALFA)
        page.click('[data-gen-quitar-oficio="Rafa"]')

    def test_lo_preparado_sobrevive_a_recargar_la_pagina(self):
        def fn(page, carpeta):
            self._tres_cambios(page)
            antes = A.filas(page)
            self.assertEqual(len(antes), 3)
            A.recargar(page, carpeta)
            self.assertEqual(A.filas(page), antes, "las mismas filas, tal cual")
            self.assertEqual(A.texto(page, "#gen-sin-enviar"), "Tienes 3 cambios sin enviar. Se guardan en este aparato aunque cierres o recargues la página.")
            self.assertTrue(A.texto(page, "#gen-recuperado").startswith("Se han recuperado 3 cambios que dejaste preparados"))
            _, f = A.descargar(page)
            self.assertEqual(f["altas"], ["Nuevo Uno"])
            self.assertEqual(f["categorias"], [{"nombre": "Rafa", "categoria": ""}])
            # tras guardar el fichero y recargar, la caja de los tres pasos sigue ahí hasta que el PC lo aplique
            A.recargar(page, carpeta)
            self.assertIn("Fichero guardado con 3 cambios", A.texto(page, "#gen-fichero-guardado"))
        self.pagina(fn)

    def test_empezar_de_cero_pregunta_antes_y_vacia_tambien_lo_guardado(self):
        def fn(page, carpeta):
            self._tres_cambios(page)
            page.click("#btn-gen-vaciar")
            self.assertEqual(A.texto(page, "#gen-confirmar-vaciar > p"), "Vas a borrar los 3 cambios que tienes preparados. Después no se pueden recuperar. ¿Seguro?")
            self.assertEqual(len(A.filas(page)), 3, "mientras no contesta no se borra nada")
            page.click("#btn-gen-vaciar-no")
            self.assertEqual(len(A.filas(page)), 3)
            self.assertIsNone(page.query_selector("#gen-confirmar-vaciar"))
            page.click("#btn-gen-vaciar")
            page.click('[data-gen-modo="varios"]')   # tocar otra cosa cierra la pregunta
            self.assertIsNone(page.query_selector("#gen-confirmar-vaciar"))
            page.click("#btn-gen-vaciar")
            page.click("#btn-gen-vaciar-si")
            self.assertEqual(A.filas(page), [])
            self.assertIsNone(page.query_selector("#gen-sin-enviar"))
            self.assertIsNone(page.evaluate("window.localStorage.getItem(%s)" % json.dumps(A.CLAVE_BORRADOR)), "lo guardado también se borra")
            A.recargar(page, carpeta)
            self.assertEqual(A.filas(page), [])
            self.assertEqual(A.texto(page, "#gen-recuperado"), "")
        self.pagina(fn)

    def test_lo_que_el_pc_ya_aplico_se_quita_solo_de_la_lista(self):
        def fn(page, carpeta):
            A.anadir(page, "Nuevo Uno", A.ALFA)
            A.anadir(page, "Pepe", A.BETA)
            # el PC publica: ya está «Nuevo Uno» en Alfa; Pepe sigue sin empresa
            e = A.estado()
            e["catalogo"].append(D.ficha(6, "Nuevo Uno", A.ALFA))
            A.recargar(page, carpeta, e)
            self.assertEqual([f[0] for f in A.filas(page)], ["Pepe"])
            self.assertEqual(A.texto(page, "#gen-ya-aplicados"), "1 cambio que habías preparado ya está aplicado en la base y se ha quitado de la lista.")
            self.assertEqual(A.texto(page, "#gen-sin-enviar").split(".")[0], "Tienes 1 cambio sin enviar")
        self.pagina(fn)

    def test_una_baja_ya_aplicada_tambien_se_quita_y_una_pendiente_sigue(self):
        def fn(page, carpeta):
            page.select_option("#gen-empresa", A.BETA)
            page.click('[data-gen-baja="Luis"]')
            page.select_option("#gen-empresa", "Sagarde")
            page.click('[data-gen-baja="Zoilo"]')
            self.assertEqual(len(A.filas(page)), 2)
            e = A.estado()
            for t in e["catalogo"]:
                if t["nombre"] == "Luis":
                    t["activo"] = False   # el PC ya dio de baja a Luis
            A.recargar(page, carpeta, e)
            self.assertEqual([f[0] for f in A.filas(page)], ["Zoilo"])
            self.assertIn("Quitar de la base", A.filas(page)[0][1])
            self.assertIn("ya está aplicado", A.texto(page, "#gen-ya-aplicados"))
        self.pagina(fn)

    def test_si_el_navegador_no_deja_guardar_lo_dice_y_la_pagina_sigue_funcionando(self):
        bloqueo = ("(() => { const t = () => { throw new DOMException('bloqueado', 'SecurityError'); };"
                   " Object.defineProperty(window, 'localStorage', { get: t, configurable: true }); })();")

        def fn(page, carpeta):
            self.assertEqual(A.texto(page, "#gen-memoria-falla"), "", "sin nada preparado no hay de qué avisar")
            A.anadir(page, "Nuevo Uno", A.ALFA)
            self.assertIn("no deja guardar lo preparado", A.texto(page, "#gen-memoria-falla"))
            self.assertNotIn("Se guardan en este aparato", A.texto(page, "#gen-sin-enviar"), "no se promete lo que no se puede")
            self.assertEqual(len(A.filas(page)), 1)
            nombre, f = A.descargar(page)
            self.assertEqual(f["altas"], ["Nuevo Uno"])
        self.pagina(fn, init=bloqueo)

    def test_lo_guardado_ilegible_o_con_trozos_malos_se_dice_y_no_tumba_la_pagina(self):
        def sembrar(valor):
            return ("(() => { try { if (!window.sessionStorage.getItem('sembrado')) { window.localStorage.setItem(%s, %s);"
                    " window.sessionStorage.setItem('sembrado', '1'); } } catch (e) {} })();" % (json.dumps(A.CLAVE_BORRADOR), json.dumps(valor)))

        def fn_ilegible(page, carpeta):
            self.assertIn("no se ha podido leer", A.texto(page, "#gen-borrador-ilegible"))
            self.assertEqual(A.filas(page), [])
            A.anadir(page, "Nuevo Uno", A.ALFA)   # y se puede seguir trabajando: lo siguiente se guarda bien
            A.recargar(page, carpeta)
            self.assertEqual([f[0] for f in A.filas(page)], ["Nuevo Uno"])
        self.pagina(fn_ilegible, init=sembrar("esto no es un texto guardado"))

        malo = {"version": 1, "guardado": "2026-10-31T09:15:00.000Z", "descargado": None, "bajas": [{"nombre": "Luis"}, {"nombre": "<b>x</b>"}],
                "preparados": [{"nombre": "Bien Uno", "empresa": A.ALFA, "categoria": "", "horario": None},
                               {"nombre": "<b>malo</b>", "empresa": ""},
                               {"nombre": "Con Horas", "empresa": A.ALFA, "horario": {"lun": 99}},
                               {"nombre": 5}]}

        def fn_malo(page, carpeta):
            self.assertEqual(sorted(f[0] for f in A.filas(page)), ["Bien Uno", "Luis"])
            self.assertEqual(A.texto(page, "#gen-borrador-perdidos"), "⚠ 4 cambios guardados no se han podido recuperar: revisa la lista.")
            self.assertTrue(A.texto(page, "#gen-recuperado").startswith("Se han recuperado 2 cambios"))
        self.pagina(fn_malo, init=sembrar(json.dumps(malo)))

    # ------------------------------------------------------------------ F11
    def test_el_horario_normal_sale_de_la_jornada_base_publicada(self):
        def fn(page, carpeta):
            opciones = page.eval_on_selector_all("#gen-horario-tipo option", "els => els.map(e => [e.value, e.textContent.trim()])")
            self.assertEqual(opciones, [["normal", "Horario normal de la obra (8 h L–V)"],
                                        ["8h", "8 horas de lunes a viernes (40 h)"],
                                        ["intensiva", "8 h de lunes a jueves y 6 h el viernes (38 h)"],
                                        ["personalizado", "Personalizado por día (L–D)"]])
            page.select_option("#gen-empresa", A.BETA)
            self.assertIn("Normal de la obra (8 h L–V)", A.texto(page, 'tr[data-emp-trabajador="Luis"]'))
            page.select_option("#gen-horario-tipo", "personalizado")
            valores = page.eval_on_selector_all("[data-gen-dia]", "els => els.map(e => e.value)")
            self.assertEqual(valores, ["8", "8", "8", "8", "8", "0", "0"], "los días salen de la jornada base, no de un 7.5 escrito")
        self.pagina(fn, e=A.estado(jornada_base=8))

    def test_si_no_se_sabe_la_jornada_base_no_se_inventa(self):
        def fn(page, carpeta):
            self.assertEqual(page.eval_on_selector("#gen-horario-tipo option[value=normal]", "e => e.textContent.trim()"), "Horario normal de la obra")
            page.select_option("#gen-horario-tipo", "personalizado")
            self.assertEqual(page.eval_on_selector_all("[data-gen-dia]", "els => els.map(e => e.value)"), ["", "", "", "", "", "0", "0"])
            for dia in ("sab", "dom"):
                page.fill('[data-gen-dia="%s"]' % dia, "")
            page.fill("#gen-nombre", "Nuevo Uno")
            page.click("#btn-gen-anadir")
            self.assertIn("Revisa las horas del horario personalizado", A.texto(page, "#gen-error"), "sin ninguna hora no es «normal»: se dice")
            self.assertEqual(A.filas(page), [])
        self.pagina(fn, e=A.estado(jornada_base=None))

    def test_los_horarios_fijos_estan_en_una_sola_lista_en_el_codigo(self):
        html = (APP / "personal_sagarde.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("var HORARIOS_FIJOS = ["), 1)
        self.assertEqual(len(re.findall(r"vie: 6", html)), 1, "el horario de 38 h está escrito una sola vez")
        self.assertEqual(len(re.findall(r"lun: 8, mar: 8, mie: 8, jue: 8, vie: 8", html)), 1)
        self.assertNotIn("7,5", html, "la jornada base no está escrita en el código")
        self.assertNotRegex(html, r"'7\.5'", "ni como texto de un campo")

    def test_elegir_un_horario_fijo_y_editar_a_quien_lo_tiene_usa_la_misma_lista(self):
        def fn(page, carpeta):
            page.select_option("#gen-empresa", A.ALFA)
            page.click('[data-gen-editar-emp="Rafa"]')
            self.assertEqual(page.eval_on_selector("#gen-horario-tipo", "e => e.value"), "8h", "su horario de 40 h es uno de la lista")
            A.anadir(page, "Pepe", A.BETA, horario="intensiva")
            _, f = A.descargar(page)
            self.assertEqual(f["horarios_preferidos"]["Pepe"], {"lun": 8, "mar": 8, "mie": 8, "jue": 8, "vie": 6, "sab": 0, "dom": 0})
            page.select_option("#gen-empresa", A.BETA)
            page.click('[data-gen-editar-emp="Pepe"]')
            self.assertEqual(page.eval_on_selector("#gen-horario-tipo", "e => e.value"), "intensiva")
        self.pagina(fn)

    # ------------------------------------------------------------------ F15
    def test_el_codigo_no_trocea_cadenas_para_esquivar_una_guarda(self):
        for nombre in ("personal_sagarde.html", "generador_personal.html"):
            html = (APP / nombre).read_text(encoding="utf-8")
            trozos = re.findall(r"'[A-Za-z.]{1,6}'\s*\+\s*'[A-Za-z.]{1,6}'", html)
            self.assertEqual(trozos, [], nombre + ": dos palabras cortas pegadas con «+» (un texto troceado para que no lo vea una guarda)")
        html = (APP / "personal_sagarde.html").read_text(encoding="utf-8")
        for claro in ("paquete.altas = ", "paquete.bajas = ", "nombreBase + '.json'"):
            self.assertIn(claro, html, "escrito con todas sus letras: " + claro)

    # ------------------------------------------------------------------ F12
    def test_en_el_movil_sin_desborde_ni_botones_pequenos_en_ninguna_pestana(self):
        problemas = []

        def mirar(page, ancho, donde):
            m = page.evaluate(A.JS_MEDIDAS)
            if m["doc"][0] > m["doc"][1]:
                problemas.append("%d px · %s: la página mide %d y la pantalla %d (fuera: %s)" % (ancho, donde, m["doc"][0], m["doc"][1], m["fuera"]))
            if m["chicos"]:
                problemas.append("%d px · %s: objetos de menos de 44 px: %s" % (ancho, donde, m["chicos"][:4]))
            if m["recortes"]:
                problemas.append("%d px · %s: botones agrupados con el texto recortado: %s" % (ancho, donde, m["recortes"]))
            if ancho <= 640 and m["scrolls"]:
                problemas.append("%d px · %s: tabla con barra de desplazamiento lateral: %s" % (ancho, donde, m["scrolls"]))

        recorridos = [0]
        for ancho in A.ANCHOS:
            def principal(page, carpeta, ancho=ancho):
                for v in ("ranking", "base", "empresas"):
                    page.click('#pestanas [data-v="%s"]' % v)
                    if v == "empresas":
                        page.wait_for_selector("#tabla-empresas-detalle tbody tr")
                        mirar(page, ancho, "empresas (todas)")
                        page.click("#tabla-empresas-detalle tbody tr")
                        mirar(page, ancho, "empresas (una elegida)")
                    else:
                        mirar(page, ancho, v)
                    recorridos[0] += 1
            self.pagina(principal, e=D.ESTADO_PRINCIPAL, ancho=ancho, ir_a_generar=False)

            def generar(page, carpeta, ancho=ancho):
                mirar(page, ancho, "generar (vacío)")
                page.select_option("#gen-empresa", A.ALFA)
                mirar(page, ancho, "generar (lista de la empresa)")
                page.select_option("#gen-horario-tipo", "personalizado")
                mirar(page, ancho, "generar (horario por día)")
                page.fill("#gen-nombre", "Nuevo Uno")
                page.click("#btn-gen-anadir")
                page.click('[data-gen-baja="Rafa"]')
                mirar(page, ancho, "generar (cambios preparados)")
                A.descargar(page)
                mirar(page, ancho, "generar (fichero guardado)")
                page.click("#btn-gen-vaciar")
                mirar(page, ancho, "generar (¿seguro?)")
                page.click("#btn-gen-vaciar-no")
                A.anadir(page, "Luis", A.ALFA)
                mirar(page, ancho, "generar (pregunta)")
                page.click("#btn-gen-hom-no")
                mirar(page, ancho, "generar (otra persona)")
                page.click("#btn-gen-hom-cancelar")
                page.click('[data-gen-modo="varios"]')
                mirar(page, ancho, "generar (varios)")
                recorridos[0] += 8
            self.pagina(generar, ancho=ancho)
        self.assertGreaterEqual(recorridos[0], 6 * (3 + 8), "se recorrieron todas las pestañas a todos los anchos")
        self.assertEqual(problemas, [])


class TestElResumenDelPCDiceLoQuitado(unittest.TestCase):
    """El lector del PC cuenta lo que el fichero hace; un fichero que solo quita no puede decir «no trae nada nuevo»."""

    def ficha(self, **kw):
        base = {"jornadas": [], "renombres": [], "personas_nuevas": [], "empresas": [], "horarios_propios": [], "categorias": [],
                "horarios_preferidos": [], "bajas": [], "rechazadas": 0}
        base.update(kw)
        return base

    def test_oficios_y_horarios_quitados_se_cuentan_aparte(self):
        r = lc._resumen_texto(self.ficha(categorias=[{"accion": "quitada"}, {"accion": "quitada"}],
                                         horarios_preferidos=[{"accion": "quitada"}]))
        self.assertEqual(r, "2 oficios quitados, 1 horario preferido quitado")

    def test_puestos_y_quitados_juntos(self):
        r = lc._resumen_texto(self.ficha(categorias=[{"accion": "puesta"}, {"accion": "quitada"}],
                                         horarios_preferidos=[{"accion": "fijada"}, {"accion": "quitada"}]))
        self.assertEqual(r, "1 oficio puesto, 1 oficio quitado, 1 horario preferido, 1 horario preferido quitado")

    def test_sin_nada_sigue_diciendo_que_no_trae_nada(self):
        self.assertEqual(lc._resumen_texto(self.ficha()), "no trae nada nuevo")


if __name__ == "__main__":
    unittest.main()
