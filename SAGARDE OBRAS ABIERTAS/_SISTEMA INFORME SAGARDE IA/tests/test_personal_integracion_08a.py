# -*- coding: utf-8 -*-
"""Auditor de Personal tras el paso 08a: las claves nuevas de la traza (sha256, fichero, de, a, nombre, rechazadas),
el SHA256 en hexadecimal, el lector como fichero declarado y la lista única de patrones privados.
Datos inventados sobre un árbol temporal; ninguna prueba toca una obra real."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_personal_integracion import Base, L_A, pi, po  # noqa: E402

SHA = "ab" * 32
LOTE_AB = {"tipo": "lote_personal", "version": 1, "obra": "obraa", "jornadas": [],
           "renombres": [{"de": "Mikel", "a": "Mikel Etxeberria"}], "altas": ["Rafa"]}


class TestAuditorTraza(Base):
    def traza(self, oid="obraa"):
        return self.ruta_obra(oid, "personal_jornadas.jsonl")

    def anadir(self, linea):
        with open(self.traza(), "ab") as f:
            f.write((json.dumps(linea, ensure_ascii=False) + "\n").encode("utf-8"))

    def traza_incidencias(self):
        return [i for i in pi.auditar(self.raiz) if i["codigo"] == "PERSONAL_TRAZA"]

    def base(self, **extra):
        d = {"ts": "2026-10-25T10:00:00+02:00", "obra": "obraa", "ambito": None, "fecha": None, "accion": "recibido",
             "n_presentes": 0, "avisos": [], "dispositivo": None}
        d.update(extra)
        return d

    def test_el_flujo_completo_con_sha_no_da_ninguna_incidencia(self):
        r = po.ingerir_lote(dict(L_A), str(self.raiz), pi.obras_registro()[0], "2026-10-23", escribir=True,
                            ahora="2026-10-23T22:00:00+02:00", sha256=SHA, fichero="CONTROL HORARIO 2026 OBRA A 23102026.json")
        self.assertTrue(r["ok"] and r["recibido"], r)
        r = po.ingerir_lote(dict(LOTE_AB), str(self.raiz), pi.obras_registro()[0], "2026-10-24", escribir=True,
                            ahora="2026-10-24T08:00:00+02:00", sha256="cd" * 32, fichero="CONTROL HORARIO 2026 OBRA A 24102026.json")
        self.assertTrue(r["ok"] and r["escrito"], r)
        acciones = {json.loads(x)["accion"] for x in self.traza().read_text(encoding="utf-8").splitlines()}
        self.assertTrue({"obra_creada", "recibido", "renombre", "alta_persona"} <= acciones, acciones)
        self.assertEqual([], [i for i in pi.auditar(self.raiz) if i["codigo"] != "PERSONAL_NODE_AUSENTE"])

    def test_las_lineas_nuevas_son_validas(self):
        self.ingerir(L_A)
        self.anadir(self.base(sha256=SHA, fichero="x.json", rechazadas=2))
        self.anadir(self.base(accion="renombre", id="T0001", de="Mikel", a="Mikel B", sha256=SHA))
        self.anadir(self.base(accion="alta_persona", id="T0009", nombre="Rafa"))
        self.assertEqual([], self.traza_incidencias())

    def test_un_sha256_mal_formado_es_un_error(self):
        self.ingerir(L_A)
        original = self.traza().read_bytes()
        for malo in ("abc", "zz" * 32, "ab" * 33, "", None, 5, ["ab" * 32]):
            with self.subTest(sha=malo):
                self.traza().write_bytes(original)
                self.anadir(self.base(sha256=malo))
                self.assertEqual(1, len(self.traza_incidencias()))
                self.assertEqual("error", self.traza_incidencias()[0]["nivel"])

    def test_tipos_danados_en_las_claves_nuevas(self):
        self.ingerir(L_A)
        original = self.traza().read_bytes()
        casos = [{"fichero": 5}, {"de": ["x"]}, {"a": None}, {"nombre": 1}, {"rechazadas": -1}, {"rechazadas": "2"},
                 {"rechazadas": True}, {"rechazadas": 1.5}]
        for extra in casos:
            with self.subTest(extra=extra):
                self.traza().write_bytes(original)
                self.anadir(self.base(**extra))
                self.assertEqual(1, len(self.traza_incidencias()), extra)

    def test_una_clave_desconocida_sigue_siendo_un_error(self):
        self.ingerir(L_A)
        self.anadir(self.base(sha=SHA))
        self.assertEqual(1, len(self.traza_incidencias()))

    def test_el_lector_es_un_fichero_declarado(self):
        self.assertIn("lector_control_horario.py", pi.FICHEROS_DECLARADOS)
        self.ingerir(L_A)
        (self.motor / "lector_control_horario.py").unlink()
        inc = [i for i in pi.auditar(self.raiz) if i["codigo"] == "PERSONAL_FICHERO_FALTA"]
        self.assertEqual(1, len(inc))
        self.assertIn("lector_control_horario.py", inc[0]["mensaje"])

    def test_la_lista_de_patrones_privados_es_una_sola(self):
        self.assertIs(pi.PATRONES_PRIVADOS, po.PATRONES_PRIVADOS)


if __name__ == "__main__":
    unittest.main()
