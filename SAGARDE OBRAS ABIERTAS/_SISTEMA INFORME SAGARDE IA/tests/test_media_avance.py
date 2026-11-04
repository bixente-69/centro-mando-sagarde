# -*- coding: utf-8 -*-
"""KPI «Avance medio» del inicio (decision 1 del 04/11/2026).

Quien entra en la media: las obras con datos reales. No entran OBRA PRUEBA
(obra de ensayo) ni una obra sin base (Gorliz hoy): un desconocido no es 0 %.
Barakaldo, con 0,1 %, SI entra: es un dato real.
"""
import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, "..", "..", ".."))
for ruta in (os.path.dirname(AQUI), os.path.join(RAIZ, "_SISTEMA", "MOTOR", "scripts")):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

import generar_todos as gt  # noqa: E402
import registro_obras  # noqa: E402
import regenerar_obra as ro  # noqa: E402


def obra(carpeta, ponderado, estricto=None, **extra):
    d = {"nombre": carpeta, "carpeta": carpeta, "con_panel": True,
         "pct_ponderado": ponderado, "pct_estricto": estricto}
    d.update(extra)
    return d


PRUEBA = next(o["carpeta_obra"] for o in registro_obras.OBRAS if o["id"] == "prueba")


class EntraEnMedia(unittest.TestCase):
    def test_obra_real_con_datos_entra(self):
        self.assertTrue(gt.entra_en_media(obra("2026 BOLUETA ACR", 60.0, 50.0)))

    def test_barakaldo_con_0_1_entra(self):
        self.assertTrue(gt.entra_en_media(obra("2026 BARAKALDO", 0.1, 0.1)))

    def test_obra_sin_datos_no_entra_aunque_traiga_cero(self):
        self.assertFalse(gt.entra_en_media(
            obra("2026 GORLIZ HOSPITAL", 0, 0, sin_datos=True)))

    def test_pct_desconocido_no_entra(self):
        self.assertFalse(gt.entra_en_media(obra("X", None, None)))

    def test_obra_de_ensayo_no_entra_aunque_tenga_datos(self):
        self.assertFalse(gt.entra_en_media(obra(PRUEBA, 80.0, 70.0)))

    def test_el_registro_marca_prueba_como_ensayo_y_gorliz_no(self):
        por_id = {o["id"]: o for o in registro_obras.OBRAS}
        self.assertTrue(por_id["prueba"].get("ensayo"))
        self.assertFalse(por_id["gorliz"].get("ensayo"))


class MediaDeLasObras(unittest.TestCase):
    OBRAS = [obra("A", 60.0), obra("B", 40.0), obra("C", 0.1, 0.1),
             obra("2026 GORLIZ HOSPITAL", None, None, sin_datos=True),
             obra(PRUEBA, 100.0)]

    def test_media_cuenta_solo_las_que_tienen_datos(self):
        n, media = gt.media_avance(self.OBRAS)
        self.assertEqual(n, 3)
        self.assertEqual(media, round((60.0 + 40.0 + 0.1) / 3, 1))

    def test_sin_ninguna_obra_con_datos_la_media_es_none_no_cero(self):
        n, media = gt.media_avance([obra("G", None, sin_datos=True)])
        self.assertEqual((n, media), (0, None))

    def test_regenerar_obra_recalcula_con_la_misma_regla(self):
        resumen = {"obras": list(self.OBRAS), "totales": {}}
        ro._recalcular_totales_resumen(resumen)
        t = resumen["totales"]
        self.assertEqual(t["n_con_datos_frescos"], 3)
        self.assertEqual(t["avance_medio_ponderado"],
                         gt.media_avance(self.OBRAS)[1])


class ResumenEscritoAlDisco(unittest.TestCase):
    """El JSON que lee el inicio: lo declarado tiene que producir efecto."""

    def test_resumen_real_excluye_gorliz_y_prueba_y_conserva_barakaldo(self):
        import json
        import tempfile
        from unittest import mock

        def res(carpeta, pct, **extra):
            d = {"carpeta_obra": carpeta, "nombre": carpeta, "href": carpeta + "/p.html",
                 "pct": pct, "pct_ponderado": pct, "ultima": "01/11/2026", "n_rev": 1,
                 "n_docs": 1, "sin_cambios": False, "n_bloqueos": 0}
            d.update(extra)
            return d

        resultados = [res("BOL", 60.0), res("BAR", 0.1), res(PRUEBA, 90.0),
                      res("GOR", 0, sin_datos=True, n_rev=0)]
        carpetas = [{"nombre": r["carpeta_obra"], "ultima_ts": 1.0} for r in resultados]
        with tempfile.TemporaryDirectory() as tmp:
            destino = os.path.join(tmp, "resumen.json")
            with mock.patch.object(gt, "carpetas_obra", return_value=carpetas), \
                    mock.patch.object(gt, "RESUMEN_JSON", destino), \
                    mock.patch.object(gt, "OBRAS_ABIERTAS_DIR", tmp):
                gt.escribir_resumen_json(resultados)
            with open(destino, encoding="utf-8") as f:
                datos = json.load(f)
        t = datos["totales"]
        self.assertEqual(t["n_con_datos_frescos"], 2)
        self.assertEqual(t["avance_medio_ponderado"], round((60.0 + 0.1) / 2, 1))
        gor = next(o for o in datos["obras"] if o["carpeta"] == "GOR")
        self.assertIsNone(gor["pct_ponderado"])
        self.assertTrue(gor["sin_datos"])


class TarjetasSinDatos(unittest.TestCase):
    """Gorliz sin base: su tarjeta dice «sin datos», no 0 % ni cae el portal."""

    def _ro(self):
        gorliz = {"nombre": "2026 GORLIZ HOSPITAL", "con_panel": True,
                  "panel_actualizado": True, "pct_ponderado": None,
                  "sin_datos": True, "n_rev": 0,
                  "n_docs": 3, "n_bloqueos": 0, "href": "g/panel.html"}
        real = {"nombre": "2026 BOLUETA ACR", "con_panel": True,
                "panel_actualizado": True, "pct_ponderado": 55.0, "n_rev": 24,
                "n_docs": 9, "n_bloqueos": 0, "href": "b/panel.html"}
        return {"generado": "04/11/2026 10:00",
                "totales": {"n_obras": 2, "n_con_panel": 2,
                            "avance_medio_ponderado": 55.0, "bloqueos_totales": 0},
                "obras": [gorliz, real]}

    def test_pct_tarjeta(self):
        sagarde_portal = _portal()
        self.assertEqual(sagarde_portal.pct_tarjeta({"pct_ponderado": None}),
                         ("pending", "sin datos"))
        self.assertEqual(sagarde_portal.pct_tarjeta({"pct_ponderado": 0.1})[1], "0%")

    def test_portal_movil_no_pinta_0_por_ciento(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        sp = _portal()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sp, "ROOT", Path(tmp)):
                sp.generar_portal_movil(self._ro(), None, [], [])
            html_ = (Path(tmp) / "_SISTEMA" / "PORTAL SAGARDE.html").read_text(encoding="utf-8")
        self.assertIn("Sin revisiones", html_)
        self.assertNotIn(">0%<", html_)
        self.assertIn(">55%<", html_)

    def test_inicio_dice_sin_datos_y_kpi_55(self):
        sp = _portal()
        html_ = sp.build_html([], [], self._ro(), None, [], None, [])
        self.assertIn(">sin datos<", html_)
        self.assertIn("55%", html_)


def _portal():
    motor = os.path.join(RAIZ, "_SISTEMA", "MOTOR")
    if motor not in sys.path:
        sys.path.insert(0, motor)
    import sagarde_portal
    return sagarde_portal


if __name__ == "__main__":
    unittest.main()
