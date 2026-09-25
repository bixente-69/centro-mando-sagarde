# -*- coding: utf-8 -*-
"""Regresiones de la Fase 3b: pestaña de garaje en el panel de obra."""

import json
import os
import re
import sys
import tempfile
import unittest
from datetime import date, datetime
from unittest import mock


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import panel_obra
from priorizador_trabajos import Catalogo, priorizar_ficha_garaje


def _ficha_garaje(estados=None):
    tajos = ("garaje_tubeado_vial", "garaje_cableado_vial")
    catalogo = Catalogo()
    guardados = {}
    for (zona_id, tajo_id), valor in (estados or {}).items():
        guardados["g1__s1__%s__%s" % (tajo_id, zona_id)] = {
            "v": valor,
            "f": "24/09/2026",
            "r": "rev_24092026",
        }
    return {
        "version": 1,
        "id": "garaje_panel_pruebas",
        "estructura": {
            "garajes": [{
                "id": "g1",
                "nombre": "Garaje principal",
                "plantas": [{
                    "id": "s1",
                    "nombre": "Sótano 1",
                    "zonas": [
                        {"id": "z1", "nombre": "Vial 1", "tipo": "vial"},
                        {"id": "z2", "nombre": "Vial 2", "tipo": "vial"},
                    ],
                }],
            }],
            "_meta": {},
        },
        "tajos": {
            "aplicables": list(tajos),
            "detalle": [
                {"id": tajo_id, "nombre": catalogo.meta(tajo_id)["nombre"]}
                for tajo_id in tajos
            ],
            "_meta": {},
        },
        "estados": guardados,
        "revisiones": ([{"id": "rev_24092026", "fecha": "24/09/2026"}]
                       if guardados else []),
        "dudas": [],
    }


def _prioridades_vivienda():
    return {
        "sin_base": False,
        "revision": "24/09/2026",
        "version": "4.3",
        "catalogo_version": "1.3",
        "resumen": {},
        "items": [],
        "inventario": [],
        "dudas_pendientes": [],
        "preguntas_orden": [],
        "prevision": [],
        "avisos": [],
    }


class _DatetimeFijo(datetime):
    @classmethod
    def now(cls, tz=None):
        instante = datetime(2026, 9, 24, 12, 0)
        return instante if tz is None else instante.replace(tzinfo=tz)


def _generar(prioridades_garaje, historial=None, snapshot_garaje=None):
    ficha = {
        "_disponible": True,
        "datos": {},
        "personal": [],
        "hitos": [],
        "riesgos": [],
        "plan": [],
        "tareas": [],
    }
    with tempfile.TemporaryDirectory() as carpeta:
        salida = os.path.join(carpeta, "panel.html")
        with mock.patch.object(panel_obra, "datetime", _DatetimeFijo):
            panel_obra.generar_panel(
                obra="OBRA GARAJE PRUEBA",
                subtitulo="Prueba de panel",
                historial=historial or [],
                materiales={},
                ficha=ficha,
                documentos=[],
                prioridades=_prioridades_vivienda(),
                prioridades_garaje=prioridades_garaje,
                snapshot_garaje=snapshot_garaje,
                output_path=salida,
            )
        with open(salida, encoding="utf-8") as fichero:
            return fichero.read()


def _snapshot_garaje_desde_prioridades(prioridades_garaje):
    """Mismo mapeo que usa generar_todos.py para pasar de detalle_items al
    esquema {task,floor,building,unit,status} de motor_informes. 'task'
    lleva el NOMBRE (item['trabajo']), no el id: asi lo construye tambien
    ficha_obra.snapshot_desde_ficha para vivienda, y es lo que
    generar_informe_ejecutivo.py necesita para resolver metadatos por
    nombre/alias (con el id ahi, su pagina de garaje salia vacia)."""
    return [
        {
            "task": item["trabajo"], "floor": item["planta"],
            "building": item["edificio"], "unit": item["unidad"],
            "status": item["estado"],
        }
        for item in prioridades_garaje.get("detalle_items") or []
    ]


def _vistas(html):
    patron = re.compile(r'<section id="(v-[^"]+)" class="view(?: active)?">')
    coincidencias = list(patron.finditer(html))
    resultado = {}
    for indice, coincidencia in enumerate(coincidencias):
        fin = (coincidencias[indice + 1].start()
               if indice + 1 < len(coincidencias)
               else html.index('<div class="footer">', coincidencia.end()))
        resultado[coincidencia.group(1)] = html[coincidencia.end():fin]
    return resultado


def _secciones_informe(html):
    marcador = '<script id="secciones-informe" type="application/json">'
    inicio = html.index(marcador) + len(marcador)
    fin = html.index('</script>', inicio)
    return json.loads(html[inicio:fin])


class TestPanelGaraje(unittest.TestCase):

    def test_anade_boton_seccion_e_items_sin_cambiar_las_otras_vistas(self):
        prioridades = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA",
            hoy=date(2026, 9, 24),
        )
        sin_garaje = _generar(None)
        con_garaje = _generar(prioridades)

        self.assertEqual(len(prioridades["items"]), 2)
        self.assertNotIn('data-view="v-garaje"', sin_garaje)
        self.assertNotIn('id="v-garaje"', sin_garaje)
        self.assertIn(
            '<button data-view="v-garaje">🅿️ Garaje</button>', con_garaje)
        self.assertEqual(con_garaje.count('id="v-garaje"'), 1)

        vistas_sin = _vistas(sin_garaje)
        vistas_con = _vistas(con_garaje)
        self.assertEqual(set(vistas_con), set(vistas_sin) | {"v-garaje"})
        for vista, contenido in vistas_sin.items():
            if vista == "v-riesgos":
                # Desde la pieza 3 de la integracion garaje-obra
                # (25/09/2026), v-riesgos SI cambia a proposito cuando hay
                # garaje: gana su propia seccion de riesgos. Cubierto aparte
                # en TestPanelRiesgosGaraje.
                continue
            with self.subTest(vista=vista):
                self.assertEqual(vistas_con[vista], contenido)

        garaje = vistas_con["v-garaje"]
        cuerpo = re.search(r"<tbody>(.*?)</tbody>", garaje, re.DOTALL)
        self.assertIsNotNone(cuerpo)
        self.assertEqual(cuerpo.group(1).count("<tr>"),
                         len(prioridades["items"]))
        for etiqueta in (
                "Tajos listos", "Bloqueados", "Dudas pendientes",
                "Terminados"):
            self.assertIn(etiqueta, garaje)
        for etiqueta, clave in (
                ("Tajos listos", "listos"),
                ("Bloqueados", "bloqueados"),
                ("Dudas pendientes", "dudas"),
                ("Terminados", "terminados")):
            patron = (r'<div class="label">' + re.escape(etiqueta)
                      + r'</div><div class="value">'
                      + str(prioridades["resumen"][clave]) + r'</div>')
            self.assertRegex(garaje, patron)
        self.assertNotIn("% de avance", garaje)
        self.assertEqual(
            _secciones_informe(con_garaje), _secciones_informe(sin_garaje))

    def test_sin_base_muestra_el_aviso_y_no_un_recuento_falso(self):
        prioridades = priorizar_ficha_garaje(
            _ficha_garaje(), obra="OBRA GARAJE PRUEBA",
            hoy=date(2026, 9, 24))

        garaje = _vistas(_generar(prioridades))["v-garaje"]

        self.assertIn("banner bad", garaje)
        self.assertIn("no tiene base de datos", garaje)
        self.assertNotIn("<table", garaje)


_HISTORIAL_VIVIENDA = [("24/09/2026", [
    {"task": "T1", "floor": "PB", "building": "P1", "unit": "A", "status": "X"},
    {"task": "T1", "floor": "PB", "building": "P1", "unit": "B", "status": "M"},
    {"task": "T1", "floor": "1", "building": "P1", "unit": "A", "status": ""},
])]


class TestPanelAvanceCombinadoConGaraje(unittest.TestCase):
    """Fase de integracion 25/09/2026: el % de la cabecera del Panel debe
    contar vivienda Y garaje juntos ('si hay garaje... forma parte del
    total de la obra', decision textual de Bixente), pero el resto de las
    vistas (Trabajos, Prioridades, etc.) sigue siendo solo de vivienda --
    el garaje mantiene su propia grafica, no se funden filas."""

    def test_cabecera_combina_vivienda_y_garaje_en_una_sola_bolsa(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        snapshot_garaje = _snapshot_garaje_desde_prioridades(prioridades_garaje)
        # Vivienda sola: X,M,'' (3 celdas) -> estricto 1/3=33.3%, ponderado
        # (1.0+0.6+0)/3=53.3%. Garaje solo (del fixture de arriba): X,'','',''
        # (4 celdas) -> estricto 1/4=25%. Juntos: X,M,'',X,'','','' (7 celdas)
        # -> estricto 2/7=28.6%, ponderado (1.0+0.6+0+1.0+0+0+0)/7=37.1%
        # (verificado aparte con un script, no de cabeza).
        self.assertEqual(4, len(snapshot_garaje))
        con_garaje = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=snapshot_garaje)
        sin_garaje = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=None)

        panel_con = _vistas(con_garaje)["v-panel"]
        panel_sin = _vistas(sin_garaje)["v-panel"]
        self.assertIn(
            '<div class="value">28.6%</div><div class="hint">Solo tareas '
            '100% terminadas · incluye garaje</div>', panel_con)
        self.assertIn(
            '<div class="value">37.1%</div><div class="hint">Incluye '
            'parciales (estimación) · incluye garaje</div>', panel_con)
        # Sin snapshot_garaje, la cabecera es solo de vivienda (33.3% /
        # 53.3%) y sin la coletilla "incluye garaje" -- mismo comportamiento
        # de antes de esta fase, ningun caso existente deja de funcionar.
        self.assertIn(
            '<div class="value">33.3%</div><div class="hint">Solo tareas '
            '100% terminadas</div>', panel_sin)
        self.assertIn(
            '<div class="value">53.3%</div><div class="hint">Incluye '
            'parciales (estimación)</div>', panel_sin)
        self.assertNotIn("incluye garaje", panel_sin)

    def test_las_demas_vistas_no_cambian_aunque_cambie_la_cabecera(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        snapshot_garaje = _snapshot_garaje_desde_prioridades(prioridades_garaje)
        con_garaje = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=snapshot_garaje)
        sin_garaje = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=None)

        vistas_con = _vistas(con_garaje)
        vistas_sin = _vistas(sin_garaje)
        self.assertEqual(set(vistas_con), set(vistas_sin))
        for vista, contenido in vistas_sin.items():
            if vista == "v-panel":
                continue  # la cabecera SI cambia a proposito, ver el test de arriba
            with self.subTest(vista=vista):
                self.assertEqual(vistas_con[vista], contenido)


class TestPanelRiesgosGaraje(unittest.TestCase):
    """Integracion garaje-obra, pieza 3 (25/09/2026): la vista Riesgos
    debe incluir una seccion de garaje, reutilizando bloque_riesgos tal
    cual (misma funcion que ya usa vivienda), cuando prioridades_garaje
    no es None. Sin garaje, la vista queda exactamente igual que antes."""

    def test_sin_garaje_v_riesgos_no_cambia(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))

        con_garaje = _generar(prioridades_garaje, historial=_HISTORIAL_VIVIENDA)
        sin_garaje = _generar(None, historial=_HISTORIAL_VIVIENDA)

        vistas_con = _vistas(con_garaje)
        vistas_sin = _vistas(sin_garaje)
        self.assertEqual(set(vistas_con), set(vistas_sin) | {"v-garaje"})
        for vista, contenido in vistas_sin.items():
            if vista == "v-riesgos":
                continue
            with self.subTest(vista=vista):
                self.assertEqual(vistas_con[vista], contenido)

    def test_v_riesgos_sin_garaje_no_tiene_seccion_de_garaje(self):
        html = _generar(None, historial=_HISTORIAL_VIVIENDA)
        riesgos = _vistas(html)["v-riesgos"]
        self.assertNotIn("🅿️ Garaje", riesgos)

    def test_v_riesgos_con_garaje_incluye_su_propia_seccion(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        # Valores reales de esta ficha, calculados aparte con
        # priorizar_ficha_garaje antes de escribir este test (no
        # inventados): resumen listos=2, bloqueados=0, terminados=0,
        # dudas=0; un condicionante activo en 'prevision'
        # (Tubeado de viales -> desbloquea Cableado de viales).
        self.assertEqual(2, prioridades_garaje["resumen"]["listos"])
        self.assertEqual(0, prioridades_garaje["resumen"]["bloqueados"])
        self.assertEqual(1, len(prioridades_garaje["prevision"]))

        html = _generar(prioridades_garaje, historial=_HISTORIAL_VIVIENDA)
        riesgos = _vistas(html)["v-riesgos"]

        self.assertIn("🅿️ Garaje", riesgos)
        self.assertEqual(riesgos.count("Riesgos de producción Sagarde"), 2)
        # bloque_riesgos escribe su HTML con comillas simples (ver su
        # fuente real en panel_obra.py), no dobles.
        self.assertIn(
            "<div class='kpi'><div class='label'>Tajos bloqueados</div>"
            "<div class='value'>0</div>", riesgos)
        self.assertIn("Tubeado de viales", riesgos)
        self.assertIn("Cableado de viales", riesgos)


if __name__ == "__main__":
    unittest.main()
