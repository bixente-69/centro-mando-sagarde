# -*- coding: utf-8 -*-
"""Regresiones de la Fase 3a: cálculo separado de prioridades de garaje."""

import copy
import json
import os
import sys
import tempfile
import types
import unittest
from datetime import date, datetime
from unittest import mock


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import ficha_garajes
import ficha_obra
import generar_todos
import generar_informe_ejecutivo
import priorizador_trabajos
from priorizador_trabajos import (
    Catalogo,
    _agrupar_prioridades,
    _clave_unidad,
    estado_desde_ficha_garaje,
    prevision_desbloqueos,
    priorizar_ficha,
    priorizar_ficha_garaje,
)
from registro_obras import OBRAS


OBRAS_ABIERTAS = os.path.dirname(_BASE)


def _detalle_item(unidad, ambito="zona_comun", categoria="VIABLE",
                  tarea_id="garaje_tubeado_vial", edificio="Garaje 1",
                  planta="Sótano 1", dependencia=None):
    dependencias = []
    if dependencia:
        dependencias.append({
            "id": dependencia,
            "cumplida": False,
            "estado": "Pendiente",
            "minimo": 1.0,
        })
    return {
        "tarea_id": tarea_id,
        "trabajo": tarea_id,
        "trabajos_originales": [],
        "propiedad": "propio",
        "ambito": ambito,
        "ambito_nombre": "Zonas comunes",
        "orden_ejecucion": 540,
        "fase_nombre": "Instalación interior garaje",
        "display_group": tarea_id,
        "edificio": edificio,
        "planta": planta,
        "unidad": unidad,
        "estado": "",
        "estado_actual": "Pendiente",
        "categoria": categoria,
        "motivo": "Viable." if categoria == "VIABLE" else "Bloqueado.",
        "dependencias_cumplidas": [],
        "dependencias_bloqueantes": [dependencia] if dependencia else [],
        "dependencias_detalle": dependencias,
        "dependencias_sin_dato": [],
        "omitido_ultima": False,
        "forzado_entregado": False,
        "ultima_fecha": "24/09/2026",
    }


def _ficha_garaje(zonas=("Vial 1",), tajos=("garaje_tubeado_vial",),
                   estados=None):
    catalogo = Catalogo()
    detalle_tajos = []
    for tajo_id in tajos:
        meta = catalogo.meta(tajo_id)
        detalle_tajos.append({"id": tajo_id, "nombre": meta["nombre"]})

    estructura_zonas = [
        {"id": "z%d" % indice, "nombre": nombre, "tipo": "vial"}
        for indice, nombre in enumerate(zonas, 1)
    ]
    guardados = {}
    for (zona_id, tajo_id), valor in (estados or {}).items():
        clave = "g1__s1__%s__%s" % (tajo_id, zona_id)
        guardados[clave] = {
            "v": valor,
            "f": "24/09/2026",
            "r": "rev_24092026",
        }

    return {
        "version": 1,
        "id": "garaje_pruebas",
        "estructura": {
            "garajes": [{
                "id": "g1",
                "nombre": "Garaje principal",
                "plantas": [{
                    "id": "s1",
                    "nombre": "Sótano 1",
                    "zonas": estructura_zonas,
                }],
            }],
            "_meta": {},
        },
        "tajos": {
            "aplicables": list(tajos),
            "detalle": detalle_tajos,
            "_meta": {},
        },
        "estados": guardados,
        "revisiones": ([{"id": "rev_24092026", "fecha": "24/09/2026"}]
                       if guardados else []),
        "dudas": [],
    }


def _reloj_fijo(instante):
    class RelojFijo(datetime):
        @classmethod
        def now(cls, tz=None):
            return instante

    return RelojFijo


class TestClaveUnidadGaraje(unittest.TestCase):

    def test_el_valor_por_defecto_conserva_el_conteo_de_vivienda(self):
        edificio = _detalle_item("A", ambito="edificio")
        zona = _detalle_item("Rellano A", ambito="zona_comun")
        vivienda = _detalle_item("A", ambito="vivienda")

        self.assertEqual(_clave_unidad(edificio), ("Garaje 1",))
        self.assertEqual(
            _clave_unidad(zona), ("Garaje 1", "Sótano 1"))
        self.assertEqual(
            _clave_unidad(vivienda), ("Garaje 1", "Sótano 1", "A"))

    def test_sin_colapso_dos_zonas_de_la_misma_planta_son_dos_unidades(self):
        detalle = [_detalle_item("Vial 1"), _detalle_item("Vial 2")]

        grupos = _agrupar_prioridades(
            detalle, colapsar_zona_comun=False)

        self.assertEqual(grupos[0]["n_unidades"], 2)
        self.assertNotEqual(
            _clave_unidad(detalle[0], colapsar_zona_comun=False),
            _clave_unidad(detalle[1], colapsar_zona_comun=False),
        )

    def test_la_prevision_tambien_respeta_el_no_colapso(self):
        detalle = [
            _detalle_item("Vial 1", categoria="BLOQUEADO",
                          tarea_id="garaje_cableado_vial",
                          dependencia="garaje_tubeado_vial"),
            _detalle_item("Vial 2", categoria="BLOQUEADO",
                          tarea_id="garaje_cableado_vial",
                          dependencia="garaje_tubeado_vial"),
        ]

        actual = prevision_desbloqueos(
            detalle, colapsar_zona_comun=False)

        self.assertEqual(actual[0]["desbloquea"], 2)


class TestEstadoDesdeFichaGaraje(unittest.TestCase):

    def test_recorre_garaje_planta_zona_y_omite_celdas_sin_dato(self):
        ficha = _ficha_garaje(
            zonas=("Vial 1", "Vial 2"),
            tajos=("garaje_tubeado_vial", "garaje_cableado_vial"),
            estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "M",
            },
        )

        estados, fecha = estado_desde_ficha_garaje(ficha, Catalogo())

        self.assertEqual(fecha, "24/09/2026")
        self.assertEqual(len(estados), 3)
        loc = ("Garaje principal", "Sótano 1", "Vial 1")
        self.assertEqual(
            estados[(loc, "garaje_tubeado_vial")]["estado"], "X")
        self.assertNotIn(
            (("Garaje principal", "Sótano 1", "Vial 2"),
             "garaje_cableado_vial"),
            estados,
        )


class TestPriorizarFichaGaraje(unittest.TestCase):

    def test_una_ficha_sin_estados_declara_sin_base(self):
        resultado = priorizar_ficha_garaje(_ficha_garaje())

        self.assertIs(resultado["sin_base"], True)
        self.assertEqual(resultado["detalle_items"], [])

    def test_distingue_dependencia_cumplida_y_pendiente_por_zona(self):
        ficha = _ficha_garaje(
            zonas=("Vial listo", "Vial bloqueado"),
            tajos=("garaje_tubeado_vial", "garaje_cableado_vial"),
            estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            },
        )

        resultado = priorizar_ficha_garaje(
            ficha, hoy=date(2026, 9, 24))
        cableado = {
            item["unidad"]: item["categoria"]
            for item in resultado["detalle_items"]
            if item["tarea_id"] == "garaje_cableado_vial"
        }

        self.assertEqual(cableado["Vial listo"], "VIABLE")
        self.assertEqual(cableado["Vial bloqueado"], "BLOQUEADO")

    def test_tres_viales_pendientes_cuentan_como_tres_unidades(self):
        ficha = _ficha_garaje(
            zonas=("Vial 1", "Vial 2", "Vial 3"),
            estados={
                ("z1", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z3", "garaje_tubeado_vial"): "P",
            },
        )

        resultado = priorizar_ficha_garaje(
            ficha, hoy=date(2026, 9, 24))

        self.assertEqual(resultado["resumen"]["unidades_listas"], 3)
        self.assertEqual(resultado["items"][0]["n_unidades"], 3)


class TestNoRegresionVivienda(unittest.TestCase):

    def _recalcular_obra(self, obra, esperado):
        instante = datetime.strptime(esperado["generado"], "%d/%m/%Y %H:%M")
        carpeta = os.path.join(OBRAS_ABIERTAS, obra["carpeta_obra"])
        ficha = ficha_obra.cargar(carpeta)
        with mock.patch.object(
                priorizador_trabajos, "datetime", _reloj_fijo(instante)):
            if ficha:
                return priorizar_ficha(
                    copy.deepcopy(ficha), obra=obra["nombre"])
            return priorizador_trabajos.sin_base(obra["nombre"])

    def test_todas_las_obras_registradas_conservan_sus_bytes(self):
        for obra in OBRAS:
            with self.subTest(obra=obra["nombre"]):
                ruta = os.path.join(
                    OBRAS_ABIERTAS, obra["carpeta_obra"],
                    "INFORME SAGARDE IA", "prioridades_trabajos.json")
                with open(ruta, "rb") as fichero:
                    bytes_esperados = fichero.read()
                esperado = json.loads(bytes_esperados.decode("utf-8"))

                actual = self._recalcular_obra(obra, esperado)
                serializado = json.dumps(
                    actual, ensure_ascii=False, indent=2)
                bytes_actuales = serializado.replace(
                    "\n", os.linesep).encode("utf-8")

                self.assertEqual(bytes_actuales, bytes_esperados)

    def test_priorizar_ficha_conserva_el_dict_completo_de_una_obra_real(self):
        obra = next(item for item in OBRAS if item["id"] == "gernika")
        ruta = os.path.join(
            OBRAS_ABIERTAS, obra["carpeta_obra"],
            "INFORME SAGARDE IA", "prioridades_trabajos.json")
        with open(ruta, encoding="utf-8") as fichero:
            esperado = json.load(fichero)

        actual = self._recalcular_obra(obra, esperado)

        self.assertEqual(actual, esperado)


class TestIntegracionGenerarTodos(unittest.TestCase):

    def test_main_escribe_prioridades_de_garaje_y_las_entrega_al_panel(self):
        ficha = _ficha_garaje(
            estados={("z1", "garaje_tubeado_vial"): "P"})
        obra = {
            "id": "garaje_test",
            "nombre": "OBRA GARAJE TEST",
            "subtitulo": "Prueba",
            "adaptador": "adaptador_garaje_test",
            "carpeta_obra": "OBRA GARAJE TEST",
            "materiales_rel": "materiales.xlsx",
        }
        adaptador = types.ModuleType("adaptador_garaje_test")
        adaptador.cargar_historial = lambda: []

        with tempfile.TemporaryDirectory() as temporal:
            carpeta = os.path.join(temporal, obra["carpeta_obra"])
            os.makedirs(carpeta)
            ficha_garajes.guardar(carpeta, ficha)
            panel = mock.Mock(return_value={
                "kpis": {}, "bloqueos": [], "n_docs": 0,
                "sin_cambios": False,
            })

            parches = [
                mock.patch.object(generar_todos, "OBRAS", [obra]),
                mock.patch.object(
                    generar_todos, "OBRAS_ABIERTAS_DIR", temporal),
                mock.patch.dict(sys.modules, {
                    "adaptador_garaje_test": adaptador,
                }),
                mock.patch.object(
                    generar_todos.lectores, "leer_materiales", return_value={}),
                mock.patch.object(
                    generar_todos.lectores, "leer_ficha", return_value={}),
                mock.patch.object(
                    generar_todos.lectores, "listar_documentos", return_value=[]),
                mock.patch.object(
                    generar_todos.mem, "calcular_memoria", return_value={}),
                mock.patch.object(
                    generar_todos.mem, "guardar_memoria", return_value={
                        "total_tajos": 0, "activos": 0, "terminados": 0,
                    }),
                mock.patch.object(
                    generar_todos.panel_obra, "generar_panel", panel),
                mock.patch.object(
                    generar_todos.cierre_expediente, "cargar",
                    return_value=({}, [])),
                mock.patch.object(
                    generar_todos.cierre_expediente, "guardar"),
                mock.patch.object(
                    generar_informe_ejecutivo, "generar_para_obra"),
                mock.patch.object(generar_todos, "generar_index"),
                mock.patch.object(generar_todos, "escribir_resumen_json"),
                mock.patch.object(
                    generar_todos, "publicar_registro_revisiones"),
            ]
            for parche in parches:
                parche.start()
            self.addCleanup(lambda: [parche.stop() for parche in parches])

            generar_todos.main(hacer_pdf=False)

            ruta = os.path.join(
                carpeta, "INFORME SAGARDE IA",
                "prioridades_trabajos_garaje.json")
            with open(ruta, encoding="utf-8") as fichero:
                prioridades = json.load(fichero)
            self.assertIs(prioridades["sin_base"], False)
            self.assertEqual(prioridades["resumen"]["unidades_listas"], 1)
            self.assertEqual(
                panel.call_args.kwargs["prioridades_garaje"], prioridades)


if __name__ == "__main__":
    unittest.main()
