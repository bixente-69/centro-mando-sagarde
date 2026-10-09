# -*- coding: utf-8 -*-
"""Regresiones del agregado parcial de ``regenerar_obra.py``.

Todos los ficheros usados por estas pruebas viven en TemporaryDirectory.
Nunca se escriben el índice, el resumen ni la caché reales.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock


RAIZ = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCRIPTS = os.path.join(RAIZ, "_SISTEMA", "MOTOR", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import regenerar_obra as ro  # noqa: E402


def tarjeta(nombre, dato, ultimo_archivo, href=True, eol="\n"):
    apertura = (
        '<a class="obra" href="{0}/panel.html" data-search="{1}">'.format(
            nombre, nombre.lower()
        )
        if href
        else '<div class="obra disabled" data-search="{}">'.format(nombre.lower())
    )
    cierre = "</a>" if href else "</div>"
    lineas = [
        apertura + "<h2>{}</h2>".format(nombre),
        '<div class="dato">{}</div>'.format(dato),
        '<div class="row"><span>Último archivo</span><span>{}</span></div>'.format(
            ultimo_archivo
        ),
        cierre,
    ]
    return eol.join(lineas)


def indice(tarjetas, generado="01/01/2026 10:00", eol="\n"):
    return eol.join(
        [
            "<!doctype html>",
            "<html><body>",
            '<div class="grid" id="grid">' + "".join(tarjetas) + "</div>",
            '<p class="footer">Actualizado {}</p>'.format(generado),
            "</body></html>",
        ]
    )


def resumen(entradas, generado="01/01/2026 10:00"):
    return {
        "generado": generado,
        "generado_ts": 1.0,
        "totales": {
            "n_obras": len(entradas),
            "n_con_panel": sum(1 for e in entradas if e.get("con_panel")),
            "n_con_datos_frescos": sum(
                1 for e in entradas if "pct_ponderado" in e or "pct_estricto" in e
            ),
            "avance_medio_ponderado": None,
            "bloqueos_totales": sum(e.get("n_bloqueos", 0) for e in entradas),
            "obras_sin_cambios": sum(bool(e.get("sin_cambios")) for e in entradas),
        },
        "obras": entradas,
    }


class EntornoFinalizar:
    def __init__(self, caso, cache, previo_html, previo_resumen, obras):
        self.caso = caso
        self.cache_inicial = cache
        self.previo_html = previo_html
        self.previo_resumen = previo_resumen
        self.obras = obras

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.caso.addCleanup(self.tmp.cleanup)
        self.index_path = os.path.join(self.tmp.name, "index.html")
        self.resumen_path = os.path.join(self.tmp.name, "resumen_obras.json")
        self.cache_path = os.path.join(self.tmp.name, "_cache_resultados_regen.json")
        with open(self.index_path, "w", encoding="utf-8", newline="") as f:
            f.write(self.previo_html)
        with open(self.resumen_path, "w", encoding="utf-8") as f:
            json.dump(self.previo_resumen, f, ensure_ascii=False, indent=2)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache_inicial, f, ensure_ascii=False, indent=2)

        self.parches = contextlib.ExitStack()
        self.parches.enter_context(mock.patch.object(ro, "CACHE_PATH", self.cache_path))
        self.parches.enter_context(
            mock.patch.object(ro, "INDEX_PATH", self.index_path, create=True)
        )
        self.parches.enter_context(
            mock.patch.object(ro, "RESUMEN_PATH", self.resumen_path, create=True)
        )
        self.parches.enter_context(mock.patch.object(ro.gt, "OBRAS", self.obras))
        self.publicar = self.parches.enter_context(
            mock.patch.object(ro, "_publicar_registro_revisiones_original")
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.parches.close()

    def leer_index(self):
        with open(self.index_path, encoding="utf-8", newline="") as f:
            return f.read()

    def leer_resumen(self):
        with open(self.resumen_path, encoding="utf-8") as f:
            return json.load(f)

    def leer_cache(self):
        with open(self.cache_path, encoding="utf-8") as f:
            return json.load(f)


class TestFusionarTarjetas(unittest.TestCase):
    def test_conserva_no_pendiente_actualiza_ultimo_archivo_y_respeta_crlf(self):
        eol = "\r\n"
        previo = indice(
            [
                tarjeta("OBRA VIEJA", "85.5% / 29 revisiones", "10/09", eol=eol),
                tarjeta("OBRA FRESCA", "10.0% / 1 revisión", "01/09", eol=eol),
            ],
            eol=eol,
        )
        nuevo = indice(
            [
                tarjeta("OBRA FRESCA", "20.0% / 2 revisiones", "09/10", eol=eol),
                tarjeta("OBRA VIEJA", "83.8% / 28 revisiones", "09/10", eol=eol),
                tarjeta("OBRA NUEVA", "1.0% / 1 revisión", "09/10", eol=eol),
            ],
            generado="09/10/2026 14:00",
            eol=eol,
        )

        fusionado = ro.fusionar_tarjetas(previo, nuevo, {"OBRA FRESCA"})

        self.assertIn("85.5% / 29 revisiones", fusionado)
        self.assertNotIn("83.8% / 28 revisiones", fusionado)
        self.assertIn("20.0% / 2 revisiones", fusionado)
        self.assertIn("OBRA NUEVA", fusionado)
        bloque_vieja = fusionado.split("OBRA VIEJA", 1)[1].split("</a>", 1)[0]
        self.assertIn("<span>09/10</span>", bloque_vieja)
        self.assertEqual(fusionado.count("\n"), fusionado.count("\r\n"))


class TestRegenerarUnaObra(unittest.TestCase):
    def test_anota_pendiente_fuera_del_resultado(self):
        obra = {"id": "fresca", "nombre": "OBRA FRESCA", "carpeta_obra": "OBRA FRESCA"}
        resultado = {
            "nombre": "OBRA FRESCA",
            "carpeta_obra": "OBRA FRESCA",
            "pct": 20.0,
        }
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = os.path.join(tmp, "cache.json")

            def main_falso(hacer_pdf=False):
                ro.gt.generar_index([dict(resultado)])

            with (
                mock.patch.object(ro, "CACHE_PATH", cache_path),
                mock.patch.object(ro.gt, "OBRAS", [obra]),
                mock.patch.object(ro.gt, "main", side_effect=main_falso),
            ):
                ro.regenerar_una_obra("fresca")

            with open(cache_path, encoding="utf-8") as f:
                cache = json.load(f)

        self.assertEqual(cache["_pendientes_finalizar"], ["fresca"])
        self.assertEqual(cache["fresca"], resultado)
        self.assertNotIn("_pendientes_finalizar", cache["fresca"])


class TestFinalizar(unittest.TestCase):
    def setUp(self):
        self.obras = [
            {"id": "vieja", "nombre": "OBRA VIEJA", "carpeta_obra": "OBRA VIEJA"},
            {"id": "fresca", "nombre": "OBRA FRESCA", "carpeta_obra": "OBRA FRESCA"},
        ]
        self.resultado_viejo = {
            "id_prueba": "cache-vieja",
            "nombre": "OBRA VIEJA",
            "carpeta_obra": "OBRA VIEJA",
            "pct": 83.8,
        }
        self.resultado_fresco = {
            "id_prueba": "cache-fresca",
            "nombre": "OBRA FRESCA",
            "carpeta_obra": "OBRA FRESCA",
            "pct": 20.0,
        }
        self.previo_html = indice(
            [
                tarjeta("OBRA VIEJA", "85.5% / 29 revisiones", "10/09"),
                tarjeta("OBRA FRESCA", "10.0% / 1 revisión", "01/09"),
            ]
        )
        self.previo_resumen = resumen(
            [
                {
                    "nombre": "OBRA VIEJA",
                    "carpeta": "OBRA VIEJA",
                    "con_panel": True,
                    "pct_ponderado": 85.5,
                    "n_rev": 29,
                    "n_bloqueos": 3,
                },
                {
                    "nombre": "OBRA FRESCA",
                    "carpeta": "OBRA FRESCA",
                    "con_panel": True,
                    "pct_ponderado": 10.0,
                    "n_rev": 1,
                    "n_bloqueos": 1,
                },
            ]
        )

    @staticmethod
    def generadores_falsos(entorno):
        def generar_index(resultados):
            por_nombre = {r["nombre"]: r for r in resultados}
            tarjetas = []
            if "OBRA FRESCA" in por_nombre:
                tarjetas.append(
                    tarjeta("OBRA FRESCA", "20.0% / 2 revisiones", "09/10")
                )
            if "OBRA VIEJA" in por_nombre:
                tarjetas.append(
                    tarjeta("OBRA VIEJA", "83.8% / 28 revisiones", "09/10")
                )
            with open(entorno.index_path, "w", encoding="utf-8", newline="") as f:
                f.write(indice(tarjetas, generado="09/10/2026 14:00"))

        def escribir_resumen(resultados):
            entradas = []
            por_nombre = {r["nombre"]: r for r in resultados}
            if "OBRA FRESCA" in por_nombre:
                entradas.append(
                    {
                        "nombre": "OBRA FRESCA",
                        "carpeta": "OBRA FRESCA",
                        "con_panel": True,
                        "pct_ponderado": 20.0,
                        "n_rev": 2,
                        "n_bloqueos": 2,
                    }
                )
            if "OBRA VIEJA" in por_nombre:
                entradas.append(
                    {
                        "nombre": "OBRA VIEJA",
                        "carpeta": "OBRA VIEJA",
                        "con_panel": True,
                        "pct_ponderado": 83.8,
                        "n_rev": 28,
                        "n_bloqueos": 9,
                    }
                )
            with open(entorno.resumen_path, "w", encoding="utf-8") as f:
                json.dump(
                    resumen(entradas, generado="09/10/2026 14:00"),
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        return generar_index, escribir_resumen

    def test_cache_vieja_no_cambia_tarjeta_y_pendiente_si(self):
        cache = {
            "_pendientes_finalizar": ["fresca"],
            "vieja": self.resultado_viejo,
            "fresca": self.resultado_fresco,
        }
        with EntornoFinalizar(
            self, cache, self.previo_html, self.previo_resumen, self.obras
        ) as entorno:
            gen_index, gen_resumen = self.generadores_falsos(entorno)
            with (
                mock.patch.object(ro, "_generar_index_original", side_effect=gen_index),
                mock.patch.object(
                    ro, "_escribir_resumen_json_original", side_effect=gen_resumen
                ),
            ):
                ro.finalizar()

            final = entorno.leer_index()
            cache_final = entorno.leer_cache()

        self.assertIn("85.5% / 29 revisiones", final)
        self.assertNotIn("83.8% / 28 revisiones", final)
        self.assertIn("20.0% / 2 revisiones", final)
        self.assertEqual(cache_final["_pendientes_finalizar"], [])

    def test_sin_pendientes_conserva_todas_las_tarjetas(self):
        cache = {
            "_pendientes_finalizar": [],
            "vieja": self.resultado_viejo,
            "fresca": self.resultado_fresco,
        }
        with EntornoFinalizar(
            self, cache, self.previo_html, self.previo_resumen, self.obras
        ) as entorno:
            gen_index, gen_resumen = self.generadores_falsos(entorno)
            salida = io.StringIO()
            with (
                mock.patch.object(ro, "_generar_index_original", side_effect=gen_index),
                mock.patch.object(
                    ro, "_escribir_resumen_json_original", side_effect=gen_resumen
                ),
                contextlib.redirect_stdout(salida),
            ):
                ro.finalizar()
            final = entorno.leer_index()

        self.assertIn("85.5% / 29 revisiones", final)
        self.assertIn("10.0% / 1 revisión", final)
        self.assertNotIn("83.8% / 28 revisiones", final)
        self.assertNotIn("20.0% / 2 revisiones", final)
        self.assertIn(
            "nada pendiente: se conservan todas las tarjetas", salida.getvalue().lower()
        )

    def test_resumen_se_fusiona_por_obra(self):
        cache = {
            "_pendientes_finalizar": ["fresca"],
            "vieja": self.resultado_viejo,
            "fresca": self.resultado_fresco,
        }
        with EntornoFinalizar(
            self, cache, self.previo_html, self.previo_resumen, self.obras
        ) as entorno:
            gen_index, gen_resumen = self.generadores_falsos(entorno)
            with (
                mock.patch.object(ro, "_generar_index_original", side_effect=gen_index),
                mock.patch.object(
                    ro, "_escribir_resumen_json_original", side_effect=gen_resumen
                ),
            ):
                ro.finalizar()
            final = entorno.leer_resumen()

        por_carpeta = {o["carpeta"]: o for o in final["obras"]}
        self.assertEqual(por_carpeta["OBRA VIEJA"]["pct_ponderado"], 85.5)
        self.assertEqual(por_carpeta["OBRA VIEJA"]["n_rev"], 29)
        self.assertEqual(por_carpeta["OBRA FRESCA"]["pct_ponderado"], 20.0)
        self.assertEqual(por_carpeta["OBRA FRESCA"]["n_rev"], 2)
        self.assertEqual(final["totales"]["bloqueos_totales"], 5)

    def test_fallo_intermedio_restaura_index_y_resumen_previos(self):
        cache = {
            "_pendientes_finalizar": ["fresca"],
            "vieja": self.resultado_viejo,
            "fresca": self.resultado_fresco,
        }
        with EntornoFinalizar(
            self, cache, self.previo_html, self.previo_resumen, self.obras
        ) as entorno:
            def escribir_index_corrupto(_resultados):
                with open(entorno.index_path, "w", encoding="utf-8") as f:
                    f.write("INDEX A MEDIAS")

            with (
                mock.patch.object(
                    ro, "_generar_index_original", side_effect=escribir_index_corrupto
                ),
                mock.patch.object(
                    ro,
                    "_escribir_resumen_json_original",
                    side_effect=RuntimeError("fallo simulado del resumen"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "fallo simulado del resumen"):
                    ro.finalizar()

            self.assertEqual(entorno.leer_index(), self.previo_html)
            self.assertEqual(entorno.leer_resumen(), self.previo_resumen)
            self.assertEqual(
                entorno.leer_cache()["_pendientes_finalizar"], ["fresca"]
            )
            entorno.publicar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
