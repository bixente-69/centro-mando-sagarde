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


def _generar(prioridades_garaje):
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
                historial=[],
                materiales={},
                ficha=ficha,
                documentos=[],
                prioridades=_prioridades_vivienda(),
                prioridades_garaje=prioridades_garaje,
                output_path=salida,
            )
        with open(salida, encoding="utf-8") as fichero:
            return fichero.read()


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


if __name__ == "__main__":
    unittest.main()
