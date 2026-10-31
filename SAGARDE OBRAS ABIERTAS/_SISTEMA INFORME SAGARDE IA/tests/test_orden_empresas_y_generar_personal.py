# -*- coding: utf-8 -*-
"""Pruebas de las mejoras en Personal Sagarde (personal_sagarde.html, personal_calculo.js, personal_obra.py,
lector_control_horario.py y generador_personal.html):
  1. Ordenación al pinchar en las cabeceras de columna (<th>) en Ranking, Por empresa, Base de trabajadores y Empresas.
  2. Columna separada de Empresa, filtro por empresa y nueva pestaña «Empresas» con desglose de plantilla y obras.
  3. Nueva pestaña «Generar personal» (un trabajador o varios, empresa existente/nueva/@AUT, oficio y horario
     particular preferido) y flujo completo hacia el Control Horario.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SISTEMA = Path(__file__).resolve().parent.parent
if str(SISTEMA) not in sys.path:
    sys.path.insert(0, str(SISTEMA))

import lector_control_horario as lc  # noqa: E402
import personal_obra as po  # noqa: E402


class TestCalculoOrdenYEmpresasJS(unittest.TestCase):
    """Comprueba en Node las funciones nuevas de personal_calculo.js."""

    def test_ordenar_ranking_base_y_resumen_empresas(self):
        script = r"""
const C = require('./personal_calculo.js');
const assert = require('assert');

const catalogo = [
  { id: 'T0001', nombre: 'Ana', empresa: 'Manueles', categoria: 'Oficial 1ª', activo: true,
    horario_preferido: { lun: 8, mar: 8, mie: 8, jue: 8, vie: 8, sab: 0, dom: 0 } },
  { id: 'T0002', nombre: 'Beto', empresa: '', categoria: 'Ayudante', activo: true },
  { id: 'T0003', nombre: 'Carla', empresa: 'CATERSYSTEM', categoria: 'Oficial 2ª', activo: true },
  { id: 'T0004', nombre: 'Dani', empresa: 'Dani @AUT', categoria: '', activo: true }
];

const filas = [
  { fecha: '2026-10-20', ambito: 'vivienda', obra: 'olabeaga', nombre: 'Ana', empresa: 'Manueles', horas: 8, extra: 0.5 },
  { fecha: '2026-10-21', ambito: 'vivienda', obra: 'mungia', nombre: 'Ana', empresa: 'Manueles', horas: 8, extra: 0.5 },
  { fecha: '2026-10-21', ambito: 'vivienda', obra: 'olabeaga', nombre: 'Carla', empresa: 'CATERSYSTEM', horas: 10, extra: 2.5 },
  { fecha: '2026-10-22', ambito: 'garaje', obra: 'olabeaga', nombre: 'Beto', horas: 7.5, extra: 0 }
];

// 1. ordenarRanking por todas las columnas en asc y desc
const rk = C.agregar(filas).trabajadores;
assert.deepStrictEqual(C.ordenarRanking(rk, 'nombre', 'asc').map(x => x.nombre), ['Ana', 'Beto', 'Carla']);
assert.deepStrictEqual(C.ordenarRanking(rk, 'nombre', 'desc').map(x => x.nombre), ['Carla', 'Beto', 'Ana']);
assert.deepStrictEqual(C.ordenarRanking(rk, 'horas', 'desc').map(x => x.nombre), ['Ana', 'Carla', 'Beto']);
assert.deepStrictEqual(C.ordenarRanking(rk, 'horas', 'asc').map(x => x.nombre), ['Beto', 'Carla', 'Ana']);
assert.deepStrictEqual(C.ordenarRanking(rk, 'empresa', 'asc').map(x => x.nombre), ['Carla', 'Ana', 'Beto']);
assert.deepStrictEqual(C.ordenarRanking(rk, 'empresa', 'desc').map(x => x.nombre), ['Ana', 'Carla', 'Beto']);
assert.deepStrictEqual(C.ordenarRanking(rk, 'obras', 'desc').map(x => x.nombre), ['Ana', 'Carla', 'Beto']);
assert.deepStrictEqual(C.ordenarRanking(rk, 'obras', 'asc').map(x => x.nombre), ['Beto', 'Carla', 'Ana']);

// 2. ordenarBase por todas las columnas en asc y desc (sin jornadas siempre al final en columnas de actividad)
const base = C.baseTrabajadores(filas, catalogo).personas;
assert.deepStrictEqual(C.ordenarBase(base, 'empresa', 'asc').map(x => x.nombre), ['Carla', 'Dani', 'Ana', 'Beto']);
assert.deepStrictEqual(C.ordenarBase(base, 'empresa', 'desc').map(x => x.nombre), ['Ana', 'Dani', 'Carla', 'Beto']);
assert.deepStrictEqual(C.ordenarBase(base, 'dias', 'desc').map(x => x.nombre), ['Ana', 'Carla', 'Beto', 'Dani']);
assert.deepStrictEqual(C.ordenarBase(base, 'dias', 'asc').map(x => x.nombre), ['Beto', 'Carla', 'Ana', 'Dani']);
assert.deepStrictEqual(C.ordenarBase(base, 'horas', 'asc').map(x => x.nombre), ['Beto', 'Carla', 'Ana', 'Dani']);

// 3. resumenEmpresas
const empRes = C.resumenEmpresas(filas, catalogo);
assert.strictEqual(empRes.totales.empresas, 2);
assert.strictEqual(empRes.totales.autonomos, 1);
assert.strictEqual(empRes.totales.enBaseConEmpresa, 3);
assert.strictEqual(empRes.totales.enBaseSinEmpresa, 1);
const manueles = empRes.empresas.find(e => e.nombre === 'Manueles');
assert(manueles);
assert.strictEqual(manueles.enBase, 1);
assert.strictEqual(manueles.horas, 16);
assert.strictEqual(manueles.trabajadores[0].categoria, 'Oficial 1ª');
assert.strictEqual(manueles.trabajadores[0].horarioPreferido.lun, 8);
"""
        proc = subprocess.run(
            ["node", "-e", script],
            cwd=str(SISTEMA),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)


class TestIngestaCategoriasYHorariosPreferidos(unittest.TestCase):
    """Comprueba que personal_obra y lector_control_horario aceptan categorias y horarios_preferidos."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sagarde_gen_pers_"))
        self.obras = {"olabeaga": "2026 OLABEAGA BILBAO"}
        (self.tmp / "2026 OLABEAGA BILBAO" / "REVISIONES").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_flujo_completo_generar_personal_a_control_horario(self):
        lote = {
            "tipo": "lote_personal",
            "version": 1,
            "obra": "olabeaga",
            "jornadas": [],
            "dispositivo": "Personal Sagarde PC",
            "altas": ["Iker Etxebarria", "Unai Bilbao"],
            "empresas": [
                {"nombre": "Iker Etxebarria", "empresa": "Electrovizcaya"},
                {"nombre": "Unai Bilbao", "empresa": "Unai Bilbao @AUT"},
            ],
            "categorias": [
                {"nombre": "Iker Etxebarria", "categoria": "Oficial 1ª"},
                {"nombre": "Unai Bilbao", "categoria": "Encargado"},
            ],
            "horarios_preferidos": {
                "Iker Etxebarria": {"lun": 8, "mar": 8, "mie": 8, "jue": 8, "vie": 8, "sab": 0, "dom": 0},
            },
            "excepciones_horario": {
                "Iker Etxebarria": {"lun": 8, "mar": 8, "mie": 8, "jue": 8, "vie": 8, "sab": 0, "dom": 0},
            },
        }
        ruta_fichero = self.tmp / "2026 OLABEAGA BILBAO" / "REVISIONES" / "CONTROL HORARIO 2026 OLABEAGA BILBAO 28102026.json"
        ruta_fichero.write_text(json.dumps(lote, ensure_ascii=False, indent=2), encoding="utf-8")

        candidatos = lc.listar(ruta_fichero.parent)
        self.assertEqual(len(candidatos), 1)

        analisis = lc.analizar("olabeaga", candidatos, "2026-10-28", self.tmp, self.obras)
        self.assertEqual(analisis["ficheros"][0]["estado"], lc.LISTO, analisis["ficheros"][0])
        self.assertIn("2 personas nuevas", analisis["ficheros"][0]["resumen"])
        self.assertIn("2 empresas puestas", analisis["ficheros"][0]["resumen"])
        self.assertIn("2 oficios puestos", analisis["ficheros"][0]["resumen"])
        self.assertIn("1 horario preferido", analisis["ficheros"][0]["resumen"])

        aplicado = lc.aplicar("olabeaga", candidatos, "2026-10-28", self.tmp, self.obras)
        self.assertFalse(aplicado["frena"], aplicado)
        self.assertEqual(len(aplicado["aplicados"]), 1)

        # Comprobar integridad del esquema con `po.comprobar`
        errores = po.comprobar(self.tmp, self.obras)
        self.assertEqual(errores, [])

        # Comprobar que exportar_estado publica el trabajador con su empresa, categoría y horario_preferido
        js = po.exportar_estado(self.tmp, self.obras, incluir_vacias=True)
        payload = json.loads(js.split("window.SAGARDE_PERSONAL = ", 1)[1].rstrip(";\n"))
        iker = next(c for c in payload["catalogo"] if c["nombre"] == "Iker Etxebarria")
        self.assertEqual(iker["empresa"], "Electrovizcaya")
        self.assertEqual(iker["categoria"], "Oficial 1ª")
        self.assertEqual(iker["horario_preferido"]["lun"], 8)
        self.assertTrue(iker["activo"])

        # Comprobar baja de empleado con fichero BASE TRABAJADORES SAGARDE (sin nombre de obra ni carpeta de obra)
        lote_baja = {
            "tipo": "lote_personal",
            "version": 1,
            "obra": "sagarde",
            "jornadas": [],
            "dispositivo": "Personal Sagarde PC",
            "bajas": ["Unai Bilbao"],
        }
        ruta_baja = self.tmp / "BASE TRABAJADORES SAGARDE 29102026.json"
        ruta_baja.write_text(json.dumps(lote_baja, ensure_ascii=False, indent=2), encoding="utf-8")

        candidatos2 = lc.listar(self.tmp)
        analisis2 = lc.analizar("sagarde", candidatos2, "2026-10-29", self.tmp, self.obras)
        ficha_baja = next(f for f in analisis2["ficheros"] if f["nombre"].startswith("BASE TRABAJADORES SAGARDE"))
        self.assertEqual(ficha_baja["estado"], lc.LISTO, ficha_baja)
        self.assertIn("1 persona quitada", ficha_baja["resumen"])

        aplicado2 = lc.aplicar("sagarde", candidatos2, "2026-10-29", self.tmp, self.obras)
        self.assertFalse(aplicado2["frena"], aplicado2)
        js2 = po.exportar_estado(self.tmp, self.obras, incluir_vacias=True)
        payload2 = json.loads(js2.split("window.SAGARDE_PERSONAL = ", 1)[1].rstrip(";\n"))
        unai = next(c for c in payload2["catalogo"] if c["nombre"] == "Unai Bilbao")
        self.assertFalse(unai["activo"])


class TestNavegadorPersonalSagardeNuevasFunciones(unittest.TestCase):
    """Comprueba en Chromium real las 4 pestañas, la ordenación por columnas y la generación de personal."""

    def test_columnas_ordenables_pestana_empresas_y_generar_personal(self):
        from playwright.sync_api import sync_playwright
        import datos_base_trabajadores as D

        with tempfile.TemporaryDirectory(prefix="sagarde_ui_pers_") as tmp:
            tmp_path = Path(tmp)
            for nombre in ("personal_sagarde.html", "personal_calculo.js"):
                shutil.copy2(SISTEMA / nombre, tmp_path / nombre)
            (tmp_path / "personal_estado.js").write_text(
                "window.SAGARDE_PERSONAL = " + json.dumps(D.ESTADO_PRINCIPAL, ensure_ascii=False) + ";\n",
                encoding="utf-8",
            )

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto((tmp_path / "personal_sagarde.html").resolve().as_uri())
                page.wait_for_selector("table.data tbody tr")

                # 1. Ranking: comprobar columna Empresa y ordenación por clic en <th>
                ths_rk = page.eval_on_selector_all("table.data thead th", "els => els.map(e => e.textContent.trim())")
                self.assertEqual(ths_rk, ["#", "Nombre", "Empresa", "Total h", "Días", "% de Sagarde", "Obras"])

                page.click('table.data thead th[data-col="nombre"]')
                nombres_asc = page.eval_on_selector_all("table.data tbody td.nom", "els => els.map(e => e.textContent.trim())")
                self.assertEqual(nombres_asc, sorted(nombres_asc))

                page.click('table.data thead th[data-col="nombre"]')
                nombres_desc = page.eval_on_selector_all("table.data tbody td.nom", "els => els.map(e => e.textContent.trim())")
                self.assertEqual(nombres_desc, list(reversed(nombres_asc)))

                # Filtro por empresa en Ranking
                page.select_option("#filtro-empresa-ranking", "Manueles")
                visibles_rk = page.eval_on_selector_all("table.data tbody td.nom", "els => els.map(e => e.textContent.trim())")
                self.assertEqual(visibles_rk, ["Ana"])
                page.select_option("#filtro-empresa-ranking", "todas")

                # 2. Base de trabajadores: ordenar por cabeceras <th>
                page.click('#pestanas [data-v="base"]')
                page.wait_for_selector("table.base tbody tr")
                page.click('table.base thead th[data-col="horas"]')
                horas_desc = page.eval_on_selector_all("table.base tbody td.b-nom", "els => els.map(e => e.firstChild.textContent.trim())")
                self.assertEqual(horas_desc[0], "Ana")
                page.click('table.base thead th[data-col="horas"]')
                horas_asc = page.eval_on_selector_all("table.base tbody td.b-nom", "els => els.map(e => e.firstChild.textContent.trim())")
                self.assertEqual(horas_asc[0], D.ZOE)

                # 3. Pestaña Empresas: tabla ordenable y desglose por empresa
                page.click('#pestanas [data-v="empresas"]')
                page.wait_for_selector("#tabla-empresas-detalle tbody tr")
                emp_nombres = page.eval_on_selector_all(
                    "#tabla-empresas-detalle tbody tr td:first-child",
                    "els => els.map(e => e.textContent.trim())",
                )
                self.assertIn("Manueles", emp_nombres)
                self.assertIn("CATERSYSTEM", emp_nombres)
                self.assertIn("Dani @AUT", emp_nombres)

                page.click('#tabla-empresas-detalle thead th[data-col-empdet="nombre"]')
                emp_asc = page.eval_on_selector_all(
                    "#tabla-empresas-detalle tbody tr td:first-child",
                    "els => els.map(e => e.textContent.trim())",
                )
                self.assertEqual(emp_asc[0], "CATERSYSTEM")

                # 4. Pestaña Generar personal: sin selector de obra, muestra los trabajadores de la empresa y permite quitar o añadir
                page.click('#pestanas [data-v="generar"]')
                page.wait_for_selector("#gen-empresa")
                self.assertIsNone(page.query_selector("#gen-obra"))

                # Al elegir Manueles aparecen los trabajadores ya almacenados en Manueles (Ana)
                page.select_option("#gen-empresa", "Manueles")
                almacenados_manueles = page.eval_on_selector_all(
                    "#tabla-empresa-actual tbody tr td.b-nom",
                    "els => els.map(e => e.textContent.trim())",
                )
                self.assertEqual(almacenados_manueles, ["Ana"])

                # Quitar empleado almacenado (Ana)
                page.click('#tabla-empresa-actual [data-gen-baja="Ana"]')

                # Añadir trabajador nuevo en una empresa nueva con horario 8h
                page.select_option("#gen-empresa", "__nueva__")
                page.fill("#gen-empresa-nueva", "Montajes Norte")
                page.select_option("#gen-horario-tipo", "8h")
                page.fill("#gen-nombre", "Koldo Agirre")
                page.select_option("#gen-categoria", "Oficial 1ª")
                page.click("#btn-gen-anadir")

                prep = page.eval_on_selector_all(
                    "#tabla-generar tbody tr td.b-nom",
                    "els => els.map(e => e.textContent.trim())",
                )
                self.assertEqual(prep, ["Ana", "Koldo Agirre"])

                with page.expect_download() as dl_info:
                    page.click("#btn-gen-descargar")
                dl = dl_info.value
                self.assertTrue(dl.suggested_filename.startswith("BASE TRABAJADORES SAGARDE "))
                contenido_descargado = json.loads(Path(dl.path()).read_text(encoding="utf-8"))
                self.assertEqual(contenido_descargado["obra"], "sagarde")
                self.assertEqual(contenido_descargado["altas"], ["Koldo Agirre"])
                self.assertEqual(contenido_descargado["bajas"], ["Ana"])
                self.assertEqual(
                    contenido_descargado["empresas"],
                    [{"nombre": "Koldo Agirre", "empresa": "Montajes Norte"}],
                )
                self.assertEqual(
                    contenido_descargado["categorias"],
                    [{"nombre": "Koldo Agirre", "categoria": "Oficial 1ª"}],
                )
                self.assertEqual(contenido_descargado["horarios_preferidos"]["Koldo Agirre"]["lun"], 8)

                # Comprobar que ningún texto de Generar personal usa palabras de programador (incluido «base de datos»)
                from test_lenguaje_electricista import JS_TEXTOS, revisar
                textos_gen = page.evaluate(JS_TEXTOS)
                self.assertEqual(revisar(textos_gen, "Generar personal"), [])

                browser.close()


class TestGenerarPersonalConPersonasDelMismoNombre(unittest.TestCase):
    """MA4c: en «Generar personal» un nombre que ya existe con otra empresa, o de baja, se pregunta («¿es el mismo o es otra
    persona?») antes de preparar nada; nunca se dice «se ha añadido» cuando en realidad se mueve a otra persona. Chromium real,
    datos INVENTADOS. El fichero que sale se pasa por el lector del PC de verdad."""

    ALFA, BETA, GAMMA = "Alfa Instalaciones", "Beta Montajes", "Gamma Electrica"

    def estado(self, catalogo=None):
        import datos_base_trabajadores as D
        fichas = catalogo if catalogo is not None else [
            D.ficha(1, "Rafa", self.ALFA, categoria="Oficial 1ª"),
            D.ficha(2, "Pepe", ""),
            D.ficha(3, "Luis", self.BETA),
            D.ficha(4, "Ander", self.GAMMA, activo=False),
            D.ficha(5, "Zoilo", "Sagarde"),
        ]
        return D.estado(fichas, {"olabeaga": D.obra("OBRA UNO", [
            D.fila("2026-10-22", "vivienda", "Rafa", 7.5, empresa=self.ALFA),
            D.fila("2026-10-22", "vivienda", "Luis", 7.5, empresa=self.BETA),
        ])})

    def con_pagina(self, fn, estado=None, ancho=390):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory(prefix="sagarde_gen_hom_") as tmp:
            carpeta = Path(tmp)
            for nombre in ("personal_sagarde.html", "personal_calculo.js"):
                shutil.copy2(SISTEMA / nombre, carpeta / nombre)
            (carpeta / "personal_estado.js").write_text(
                "window.SAGARDE_PERSONAL = " + json.dumps(estado or self.estado(), ensure_ascii=False) + ";\n", encoding="utf-8")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": ancho, "height": 900})
                errores = []
                page.on("pageerror", lambda e: errores.append(str(e)))
                page.goto((carpeta / "personal_sagarde.html").resolve().as_uri())
                page.wait_for_selector("table.data tbody tr")
                page.click('#pestanas [data-v="generar"]')
                page.wait_for_selector("#gen-empresa")
                try:
                    fn(page, carpeta)
                finally:
                    browser.close()
                self.assertEqual(errores, [], "errores de JavaScript en la página")

    # ----------------------------------------------------------------- ayudantes de la pestaña
    def anadir(self, page, nombre, empresa, oficio=None):
        page.select_option("#gen-empresa", empresa)
        page.fill("#gen-nombre", nombre)
        if oficio is not None:
            page.select_option("#gen-categoria", oficio)
        page.click("#btn-gen-anadir")

    def texto(self, page, sel):
        el = page.query_selector(sel)
        return " ".join(el.inner_text().split()) if el else ""

    def filas(self, page):
        return page.eval_on_selector_all("#tabla-generar tbody tr", "els => els.map(e => [e.dataset.genPreparado, e.innerText.replace(/\\s+/g,' ').trim()])")

    def descargar(self, page):
        with page.expect_download() as d:
            page.click("#btn-gen-descargar")
        return json.loads(Path(d.value.path()).read_text(encoding="utf-8"))

    def sin_desborde(self, page, donde):
        ancho = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        self.assertLessEqual(ancho[0], ancho[1], "a 390 px no debe desbordar (%s): %s" % (donde, ancho))

    def pc_con_la_base(self, tmp):
        """Un PC de pruebas que ya tiene a Rafa (Alfa), Luis (Beta) y a Ander de baja, como el estado de la página."""
        raiz = Path(tmp)
        obras = {"olabeaga": "2026 OLABEAGA BILBAO"}
        (raiz / "2026 OLABEAGA BILBAO" / "REVISIONES").mkdir(parents=True, exist_ok=True)
        previo = {"tipo": "lote_personal", "version": 1, "obra": "sagarde", "jornadas": [],
                  "altas": ["Rafa", "Pepe", "Luis", "Ander", "Zoilo"],
                  "empresas": [{"nombre": "Rafa", "empresa": self.ALFA}, {"nombre": "Luis", "empresa": self.BETA},
                               {"nombre": "Ander", "empresa": self.GAMMA}, {"nombre": "Zoilo", "empresa": "Sagarde"}]}
        r = po.ingerir_lote(previo, raiz, obras, "2026-10-22", escribir=True, ahora="2026-10-22T22:00:00+02:00")
        self.assertTrue(r["ok"], r)
        r = po.ingerir_lote({"tipo": "lote_personal", "version": 1, "obra": "sagarde", "jornadas": [], "bajas": ["Ander"]},
                            raiz, obras, "2026-10-22", escribir=True, ahora="2026-10-22T22:30:00+02:00")
        self.assertTrue(r["ok"], r)
        return raiz, obras

    def analiza(self, raiz, obras, fichero):
        """Pasa el fichero por el lector del PC (vista previa, no escribe) y devuelve su estado y los textos de sus avisos."""
        ruta = raiz / "BASE TRABAJADORES SAGARDE 31102026.json"
        ruta.write_text(json.dumps(fichero, ensure_ascii=False, indent=2), encoding="utf-8")
        candidatos = lc.listar(raiz)
        analisis = lc.analizar("sagarde", candidatos, "2026-10-31", raiz, obras)
        ficha = next(f for f in analisis["ficheros"] if f["nombre"].startswith("BASE TRABAJADORES SAGARDE"))
        ruta.unlink()
        return ficha

    # ----------------------------------------------------------------- las escenas
    def test_rafa_a_otra_empresa_pregunta_y_el_si_lo_mueve_diciendolo(self):
        def fn(page, carpeta):
            self.anadir(page, "Rafa", self.BETA)
            self.assertEqual(self.texto(page, "#gen-pregunta [data-texto]"),
                             "Ya hay un «Rafa» en la base (Alfa Instalaciones). ¿Es el mismo, que pasa a «Beta Montajes»?")
            self.assertEqual([self.texto(page, s) for s in ("#btn-gen-hom-si", "#btn-gen-hom-no", "#btn-gen-hom-cancelar")],
                             ["Sí, es el mismo: pasa a «Beta Montajes»", "No, es otra persona", "Cancelar"])
            self.assertEqual(self.filas(page), [], "mientras no responde no se prepara nada")
            self.assertIsNone(page.query_selector("#gen-ok"), "ni mensaje de éxito")
            self.sin_desborde(page, "pregunta")
            page.click("#btn-gen-hom-si")
            self.assertIsNone(page.query_selector("#gen-pregunta"))
            self.assertEqual(self.texto(page, "#gen-ok"),
                             "✓ «Rafa» pasa de «Alfa Instalaciones» a «Beta Montajes» (queda preparado; todavía no se ha enviado).")
            filas = self.filas(page)
            self.assertEqual(len(filas), 1)
            self.assertIn("Cambia de empresa", filas[0][1])
            self.assertIn("antes: Alfa Instalaciones", filas[0][1])
            fichero = self.descargar(page)
            self.assertNotIn("altas", fichero, "es la misma persona: no se envía como nombre nuevo")
            self.assertEqual(fichero["empresas"], [{"nombre": "Rafa", "empresa": self.BETA}])
            # el PC y la pestaña de acuerdo: el fichero sale «a revisar» con el cambio de empresa
            with tempfile.TemporaryDirectory(prefix="sagarde_pc_hom_") as tmp:
                raiz, obras = self.pc_con_la_base(tmp)
                ficha = self.analiza(raiz, obras, fichero)
                self.assertEqual(ficha["estado"], lc.A_REVISAR, ficha)
                self.assertIn("empresa", json.dumps(ficha["avisos"], ensure_ascii=False).lower())
                self.assertIn("Beta Montajes", json.dumps(ficha["avisos"], ensure_ascii=False))
        self.con_pagina(fn)

    def test_otra_persona_con_apellido_entra_como_nueva_y_rafa_no_se_toca(self):
        def fn(page, carpeta):
            self.anadir(page, "Rafa", self.BETA)
            page.click("#btn-gen-hom-no")
            self.assertEqual(self.texto(page, "#gen-otra-persona [data-texto]"),
                             "Ponle algo que lo distinga del otro «Rafa»: un apellido o una inicial. Por ejemplo «Rafa B.» o «Rafa Pérez».")
            self.assertEqual(page.input_value("#gen-hom-campo"), "Rafa ")
            self.sin_desborde(page, "otra persona")
            for malo in ("", "Rafa", "rafa", " RAFÁ "):
                page.fill("#gen-hom-campo", malo)
                page.click("#btn-gen-hom-crear")
                self.assertEqual(self.texto(page, "#gen-hom-error"), "Tiene que ser distinto de «Rafa»: añade un apellido o una inicial.", malo)
            page.fill("#gen-hom-campo", "Luis")
            page.click("#btn-gen-hom-crear")
            self.assertEqual(self.texto(page, "#gen-hom-error"), "Ya hay un «Luis». Elige otro.")
            page.fill("#gen-hom-campo", "Rafa B.")
            page.click("#btn-gen-hom-crear")
            self.assertEqual(self.texto(page, "#gen-ok"), "✓ «Rafa B.» se ha añadido a la empresa.")
            self.assertEqual([f[0] for f in self.filas(page)], ["Rafa B."])
            self.assertIn("Trabajador nuevo", self.filas(page)[0][1])
            fichero = self.descargar(page)
            self.assertEqual(fichero["altas"], ["Rafa B."])
            self.assertEqual(fichero["empresas"], [{"nombre": "Rafa B.", "empresa": self.BETA}])
            with tempfile.TemporaryDirectory(prefix="sagarde_pc_hom_") as tmp:
                raiz, obras = self.pc_con_la_base(tmp)
                ficha = self.analiza(raiz, obras, fichero)
                self.assertEqual(ficha["estado"], lc.LISTO, ficha)
                avisos = json.dumps(ficha["avisos"], ensure_ascii=False)
                self.assertNotIn("empresa", avisos.lower().replace("empresas puestas", ""), avisos)
        self.con_pagina(fn)

    def test_cancelar_no_prepara_nada_ni_dice_que_se_ha_hecho(self):
        def fn(page, carpeta):
            self.anadir(page, "Rafa", self.BETA)
            page.click("#btn-gen-hom-cancelar")
            self.assertIsNone(page.query_selector("#gen-pregunta"))
            self.assertIsNone(page.query_selector("#gen-ok"))
            self.assertEqual(self.filas(page), [])
            self.anadir(page, "Rafa", self.BETA)
            page.click("#btn-gen-hom-no")
            page.fill("#gen-hom-campo", "Rafa B.")
            page.click("#btn-gen-hom-cancelar")
            self.assertIsNone(page.query_selector("#gen-otra-persona"))
            self.assertIsNone(page.query_selector("#gen-ok"))
            self.assertEqual(self.filas(page), [])
        self.con_pagina(fn)

    def test_misma_empresa_no_hace_falta_anadirlo_y_con_otro_oficio_prepara_el_cambio(self):
        def fn(page, carpeta):
            self.anadir(page, "Rafa", self.ALFA, oficio="Oficial 1ª")
            self.assertIsNone(page.query_selector("#gen-pregunta"))
            self.assertEqual(self.texto(page, "#gen-ok"), "✓ «Rafa» ya está en «Alfa Instalaciones»: no hace falta añadirlo.")
            self.assertEqual(self.filas(page), [])
            self.anadir(page, "Rafa", self.ALFA, oficio="Encargado")
            self.assertEqual(self.texto(page, "#gen-ok"),
                             "✓ «Rafa» ya estaba en «Alfa Instalaciones»: queda preparado el cambio de su oficio u horario (todavía no se ha enviado).")
            self.assertIn("Actualiza ficha", self.filas(page)[0][1])
        self.con_pagina(fn)

    def test_sin_empresa_se_completa_sin_preguntar_y_la_baja_pregunta(self):
        def fn(page, carpeta):
            self.anadir(page, "Pepe", self.BETA)
            self.assertIsNone(page.query_selector("#gen-pregunta"))
            self.assertEqual(self.texto(page, "#gen-ok"), "✓ «Pepe» pasa a «Beta Montajes» (queda preparado; todavía no se ha enviado).")
            self.anadir(page, "Ander", self.GAMMA)
            self.assertEqual(self.texto(page, "#gen-pregunta [data-texto]"), "«Ander» estaba de baja. ¿Es el mismo, que vuelve?")
            self.assertEqual(self.texto(page, "#btn-gen-hom-si"), "Sí, es el mismo: vuelve")
            page.click("#btn-gen-hom-si")
            self.assertEqual(self.texto(page, "#gen-ok"), "✓ «Ander» vuelve a la base (queda preparado; todavía no se ha enviado).")
            self.assertTrue(any("Vuelve a la base" in f[1] for f in self.filas(page)))
            fichero = self.descargar(page)
            self.assertEqual(fichero["altas"], ["Ander"], "el que vuelve viaja como nombre nuevo y el PC lo frena para mirarlo")
            with tempfile.TemporaryDirectory(prefix="sagarde_pc_hom_") as tmp:
                raiz, obras = self.pc_con_la_base(tmp)
                ficha = self.analiza(raiz, obras, {"tipo": "lote_personal", "version": 1, "obra": "sagarde", "jornadas": [],
                                                   "altas": ["Ander"], "empresas": [{"nombre": "Ander", "empresa": self.GAMMA}]})
                self.assertEqual(ficha["estado"], lc.A_REVISAR, ficha)
        self.con_pagina(fn)

    def test_la_baja_con_otra_persona_deja_al_de_baja_como_estaba(self):
        def fn(page, carpeta):
            self.anadir(page, "Ander", self.GAMMA)
            page.click("#btn-gen-hom-no")
            page.fill("#gen-hom-campo", "Ander G.")
            page.click("#btn-gen-hom-crear")
            fichero = self.descargar(page)
            self.assertEqual(fichero["altas"], ["Ander G."])
            self.assertEqual([e["nombre"] for e in fichero["empresas"]], ["Ander G."])
        self.con_pagina(fn)

    def test_varios_pregunta_linea_por_linea_y_el_mensaje_final_dice_lo_que_paso_con_cada_una(self):
        def fn(page, carpeta):
            page.select_option("#gen-empresa", self.GAMMA)
            page.click('[data-gen-modo="varios"]')
            page.fill('[data-gen-var-nom="0"]', "Rafa")
            page.fill('[data-gen-var-nom="1"]', "Luis")
            page.fill('[data-gen-var-nom="2"]', "Nuevo Uno")
            page.click("#btn-gen-anadir")
            self.assertEqual(self.texto(page, "#gen-pregunta [data-texto]"),
                             "Ya hay un «Rafa» en la base (Alfa Instalaciones). ¿Es el mismo, que pasa a «Gamma Electrica»?")
            page.click("#btn-gen-hom-si")
            self.assertEqual(self.texto(page, "#gen-pregunta [data-texto]"),
                             "Ya hay un «Luis» en la base (Beta Montajes). ¿Es el mismo, que pasa a «Gamma Electrica»?")
            self.assertEqual(self.filas(page), [], "hasta que no responde a las dos no se prepara nada")
            page.click("#btn-gen-hom-no")
            page.fill("#gen-hom-campo", "Luis M.")
            page.click("#btn-gen-hom-crear")
            self.assertIsNone(page.query_selector("#gen-pregunta"))
            self.assertEqual(sorted(f[0] for f in self.filas(page)), ["Luis M.", "Nuevo Uno", "Rafa"])
            ok = self.texto(page, "#gen-ok")
            self.assertIn("«Rafa» pasa de «Alfa Instalaciones» a «Gamma Electrica»", ok)
            self.assertIn("«Luis M.» se ha añadido a la empresa.", ok)
            self.assertIn("«Nuevo Uno» se ha añadido a la empresa.", ok)
            self.assertNotIn("Luis»", ok.replace("«Luis M.»", ""), "«Luis» no se toca")
            fichero = self.descargar(page)
            self.assertEqual(sorted(fichero["altas"]), ["Luis M.", "Nuevo Uno"])
            self.assertIn({"nombre": "Rafa", "empresa": self.GAMMA}, fichero["empresas"])
            self.assertNotIn("Luis", [e["nombre"] for e in fichero["empresas"]])
        self.con_pagina(fn)

    def test_los_avisos_de_antes_siguen_igual_y_un_nombre_mas_una_inicial_no_es_un_parecido(self):
        def fn(page, carpeta):
            self.anadir(page, "Rafaa", self.ALFA)
            self.assertIsNotNone(page.query_selector("#gen-aviso-parecido"), "una errata sigue avisando de que se parece")
            self.assertIsNone(page.query_selector("#gen-pregunta"))
            page.click("#btn-gen-cancelar-parecido")
            self.anadir(page, "Rafa B.", self.BETA)
            self.assertIsNone(page.query_selector("#gen-aviso-parecido"), "«Nombre B.» es justo cómo se distingue a otra persona")
            self.assertIsNone(page.query_selector("#gen-pregunta"))
            self.assertEqual(self.texto(page, "#gen-ok"), "✓ «Rafa B.» se ha añadido a la empresa.")
            # con la MISMA empresa que «Rafa» ya no basta la empresa distinta: es la inicial la que lo distingue
            self.anadir(page, "Rafa C.", self.ALFA)
            self.assertIsNone(page.query_selector("#gen-aviso-parecido"), "«Rafa C.» con la misma empresa tampoco se toma por errata")
            self.assertEqual(self.texto(page, "#gen-ok"), "✓ «Rafa C.» se ha añadido a la empresa.")
        self.con_pagina(fn)

    def test_cambiar_la_empresa_con_la_pregunta_abierta_la_quita(self):
        def fn(page, carpeta):
            self.anadir(page, "Rafa", self.BETA)
            self.assertIsNotNone(page.query_selector("#gen-pregunta"))
            page.select_option("#gen-empresa", self.ALFA)
            self.assertIsNone(page.query_selector("#gen-pregunta"), "una pregunta sobre otra empresa ya no vale")
        self.con_pagina(fn)

    def test_dos_veces_el_mismo_nombre_preparado_con_otra_empresa_tambien_pregunta(self):
        def fn(page, carpeta):
            self.anadir(page, "Nuevo Dos", self.ALFA)
            self.assertEqual(self.texto(page, "#gen-ok"), "✓ «Nuevo Dos» se ha añadido a la empresa.")
            self.anadir(page, "Nuevo Dos", self.BETA)
            self.assertEqual(self.texto(page, "#gen-pregunta [data-texto]"),
                             "Ya has preparado a «Nuevo Dos» (Alfa Instalaciones). ¿Es el mismo, que pasa a «Beta Montajes»?")
        self.con_pagina(fn)

    def test_ningun_texto_nuevo_usa_palabras_de_programador(self):
        from test_lenguaje_electricista import JS_TEXTOS, revisar

        def fn(page, carpeta):
            recogidos = []
            self.anadir(page, "Rafa", self.BETA)
            recogidos += page.evaluate(JS_TEXTOS)
            page.click("#btn-gen-hom-no")
            page.fill("#gen-hom-campo", "Rafa")
            page.click("#btn-gen-hom-crear")
            recogidos += page.evaluate(JS_TEXTOS)
            page.fill("#gen-hom-campo", "Rafa B.")
            page.click("#btn-gen-hom-crear")
            recogidos += page.evaluate(JS_TEXTOS)
            self.anadir(page, "Rafa", self.ALFA, oficio="Oficial 1ª")
            recogidos += page.evaluate(JS_TEXTOS)
            self.anadir(page, "Pepe", self.BETA)
            recogidos += page.evaluate(JS_TEXTOS)
            self.anadir(page, "Ander", self.GAMMA)
            recogidos += page.evaluate(JS_TEXTOS)
            page.click("#btn-gen-hom-si")
            recogidos += page.evaluate(JS_TEXTOS)
            self.assertEqual(revisar(recogidos, "Generar personal: pregunta de dos personas con el mismo nombre"), [])
        self.con_pagina(fn)


if __name__ == "__main__":
    unittest.main()
