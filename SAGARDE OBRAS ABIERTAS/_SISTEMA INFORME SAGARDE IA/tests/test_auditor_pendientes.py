# -*- coding: utf-8 -*-
"""El auditor avisa de lo que espera sin aplicar en `REVISIONES` (decision 4, 04/11/2026).

Es el eslabon manual donde mas se pierde: una hoja o un control horario que se deja en la
carpeta y nadie aplica no da error en ningun sitio. Reglas reutilizadas, no inventadas:
- hojas: `actualizar_obra.detectar_hojas` (la misma que usa «actualiza la obra»);
- controles horarios: `cerrar_obra.controles_sin_aplicar` (huella SHA256 contra la traza).
Todo en carpetas temporales: nunca se toca ninguna obra real.
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

AQUI = os.path.dirname(os.path.abspath(__file__))
SISTEMA = os.path.dirname(AQUI)
RAIZ = os.path.normpath(os.path.join(SISTEMA, "..", ".."))
for ruta in (SISTEMA, os.path.join(RAIZ, "_SISTEMA", "MOTOR"),
             os.path.join(RAIZ, "_SISTEMA", "MOTOR", "scripts")):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

import auditor_sagarde as aud  # noqa: E402
import avisos  # noqa: E402

OBRA = {"id": "demo", "nombre": "2026 DEMO", "carpeta_obra": "2026 DEMO"}


class ObraTemporal:
    """Arbol minimo: <raiz>/SAGARDE OBRAS ABIERTAS/2026 DEMO/{REVISIONES,INFORME SAGARDE IA}."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = self.raiz / "SAGARDE OBRAS ABIERTAS" / OBRA["carpeta_obra"]
        self.rev = self.obra / "REVISIONES"
        self.inf = self.obra / "INFORME SAGARDE IA"
        self.rev.mkdir(parents=True)
        self.inf.mkdir(parents=True)

    def ficha(self, fechas, nombre="ficha_obra.json"):
        (self.inf / nombre).write_text(
            json.dumps({"revisiones": [{"fecha": f} for f in fechas]}), encoding="utf-8")

    def hoja(self, nombre, contenido="<html>%s</html>"):
        (self.rev / nombre).write_text(contenido % nombre, encoding="utf-8")

    def control(self, nombre, contenido='{"x": 1}', aplicado=False):
        datos = contenido.encode("utf-8")
        (self.rev / nombre).write_bytes(datos)
        if aplicado:
            linea = json.dumps({"obra": OBRA["id"], "sha256": hashlib.sha256(datos).hexdigest(),
                                "fichero": nombre})
            with open(self.inf / "personal_jornadas.jsonl", "a", encoding="utf-8") as f:
                f.write(linea + "\n")

    def auditar(self):
        return aud.audit_pendientes_revisiones(self.raiz, [OBRA])

    def cerrar(self):
        self._tmp.cleanup()


class HojasSinAplicar(unittest.TestCase):
    def setUp(self):
        self.o = ObraTemporal()
        self.addCleanup(self.o.cerrar)

    def test_hoja_con_fecha_nueva_se_avisa(self):
        self.o.ficha(["01/10/2026"])
        self.o.hoja("REVISION 2026 DEMO 01102026.html")   # aplicada
        self.o.hoja("REVISION 2026 DEMO 08102026.html")   # nueva
        (issue,) = self.o.auditar()
        self.assertEqual(issue["codigo"], avisos.CODIGO_HOJAS_SIN_APLICAR)
        self.assertEqual(issue["nivel"], "warning")
        self.assertEqual(issue["obra"], "2026 DEMO")
        self.assertEqual(issue["n"], 1)
        self.assertEqual(issue["ficheros"], ["REVISION 2026 DEMO 08102026.html"])

    def test_sin_hojas_nuevas_no_hay_aviso(self):
        self.o.ficha(["01/10/2026"])
        self.o.hoja("REVISION 2026 DEMO 01102026.html")
        self.assertEqual(self.o.auditar(), [])

    def test_hoja_de_garaje_nueva_tambien_cuenta(self):
        self.o.ficha(["01/10/2026"])
        self.o.ficha(["01/10/2026"], nombre="ficha_garajes.json")
        self.o.hoja("REVISION 2026 DEMO 09102026_garaje.html")
        (issue,) = self.o.auditar()
        self.assertEqual(issue["n"], 1)

    def test_obra_sin_carpeta_revisiones_no_rompe(self):
        import shutil
        shutil.rmtree(self.o.rev)
        self.assertEqual(self.o.auditar(), [])


class ControlesSinAplicar(unittest.TestCase):
    def setUp(self):
        self.o = ObraTemporal()
        self.addCleanup(self.o.cerrar)
        self.o.ficha(["01/10/2026"])

    def test_control_cuya_huella_no_esta_en_la_traza_se_avisa(self):
        self.o.control("CONTROL HORARIO 2026 DEMO 20102026.json")
        (issue,) = self.o.auditar()
        self.assertEqual(issue["codigo"], avisos.CODIGO_CONTROLES_SIN_APLICAR)
        self.assertEqual(issue["n"], 1)
        self.assertEqual(issue["ficheros"], ["CONTROL HORARIO 2026 DEMO 20102026.json"])

    def test_control_ya_aplicado_no_se_avisa(self):
        self.o.control("CONTROL HORARIO 2026 DEMO 20102026.json", aplicado=True)
        self.assertEqual(self.o.auditar(), [])

    def test_hojas_y_controles_dan_un_aviso_cada_uno(self):
        self.o.hoja("REVISION 2026 DEMO 08102026.html")
        self.o.control("CONTROL HORARIO 2026 DEMO 20102026.json")
        codigos = sorted(i["codigo"] for i in self.o.auditar())
        self.assertEqual(codigos, sorted([avisos.CODIGO_HOJAS_SIN_APLICAR,
                                          avisos.CODIGO_CONTROLES_SIN_APLICAR]))


class SiNoSePuedeComprobarSeDice(unittest.TestCase):
    """Un recuento de 0 por haber fallado la comprobacion es la familia de fallos de este proyecto."""

    def test_error_al_detectar_hojas_no_se_traga(self):
        o = ObraTemporal()
        self.addCleanup(o.cerrar)
        (o.inf / "ficha_obra.json").write_text("{esto no es json", encoding="utf-8")
        o.hoja("REVISION 2026 DEMO 08102026.html")
        issues = o.auditar()
        self.assertEqual([i["codigo"] for i in issues], [avisos.CODIGO_PENDIENTES_NO_COMPROBADO])
        self.assertEqual(issues[0]["nivel"], "warning")


class LlegaAlDiagnostico(unittest.TestCase):
    def test_run_audit_incluye_los_pendientes(self):
        falso = [{"nivel": "warning", "area": "Obras Abiertas", "obra": "X",
                  "codigo": avisos.CODIGO_HOJAS_SIN_APLICAR, "mensaje": "m", "solucion": "s",
                  "n": 1, "ficheros": ["a.html"]}]
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "diag.json"
            with mock.patch.object(aud, "audit_pendientes_revisiones", return_value=falso), \
                    mock.patch.object(aud, "audit_obras_abiertas", return_value=[]), \
                    mock.patch.object(aud, "audit_mantenimientos", return_value=[]), \
                    mock.patch.object(aud, "audit_materiales", return_value=[]), \
                    mock.patch.object(aud, "audit_personal", return_value=[]), \
                    mock.patch.object(aud, "DIAGNOSTICO_JSON", destino):
                aud.run_audit()
            datos = json.loads(destino.read_text(encoding="utf-8"))
        self.assertEqual([i["codigo"] for i in datos["issues"]], [avisos.CODIGO_HOJAS_SIN_APLICAR])


if __name__ == "__main__":
    unittest.main()
