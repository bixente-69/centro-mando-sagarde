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


if __name__ == "__main__":
    unittest.main()
