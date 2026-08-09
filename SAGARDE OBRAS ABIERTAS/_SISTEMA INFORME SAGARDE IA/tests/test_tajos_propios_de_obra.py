# -*- coding: utf-8 -*-
"""Regresion para rejilla_hoja.tabla_con_tajos_de_obra().

Orueta imprimia su hoja bien pero no se podia leer: 16 de sus 40 tajos
desglosan por zona ('Focos WC', 'Pintura Pasillos', 'Mecanismos pasillo'...)
y no existen en el catalogo comun, asi que el lector rechazaba la hoja
entera. Meter esas 16 entradas en el catalogo comun habria ensuciado el de
todas las demas obras.

La solucion no relaja la guarda, cambia de donde sale la lista de lo
conocido: se acepta lo que la FICHA DE ESA OBRA declara. Un tajo de la ficha
no es un id inventado -ya esta en el modelo de datos y en los estados-. Un
tajo que no este ni en el catalogo comun ni en la ficha se sigue rechazando,
que es lo que impide colocar una fila en el sitio equivocado.

Las tres cosas que estas pruebas fijan:
  1. que Orueta pasa a ser legible,
  2. que la guarda sigue rechazando lo que no esta declarado en ningun sitio,
  3. que la tabla comun NO se modifica y las demas obras no se contaminan.
"""
import json
import os
import sys
import unittest

SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBRAS_DIR = os.path.dirname(SISTEMA_DIR)
sys.path.insert(0, SISTEMA_DIR)

import rejilla_hoja as rejilla

ORUETA = "2025 BILBAO OBISPO ORUETA"


def _ficha(obra):
    ruta = os.path.join(OBRAS_DIR, obra, "INFORME SAGARDE IA",
                        "ficha_obra.json")
    if not os.path.isfile(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _sin_reconocer(ficha, indice):
    """Tajos aplicables de la ficha cuyo nombre impreso no resuelve."""
    detalle = {d["id"]: d for d in (ficha.get("tajos") or {}).get("detalle") or []
               if isinstance(d, dict) and d.get("id")}
    faltan = []
    for tid in (ficha.get("tajos") or {}).get("aplicables") or []:
        nombre = (detalle.get(tid) or {}).get("nombre") or tid
        if not indice.get(rejilla.fold(nombre)):
            faltan.append(tid)
    return faltan


class TestTajosPropiosDeObra(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.comun = rejilla.tabla_de_tajos()

    def test_orueta_no_era_legible_con_solo_el_catalogo_comun(self):
        """El diagnostico, fijado: sin la ficha faltan tajos de verdad.

        Si esto deja de fallar es que alguien metio los tajos de Orueta en el
        catalogo comun, que es justo lo que se queria evitar."""
        ficha = _ficha(ORUETA)
        if ficha is None:
            self.skipTest("Orueta no tiene ficha_obra.json")
        self.assertTrue(
            _sin_reconocer(ficha, self.comun),
            "Orueta ya resuelve con el catalogo comun: revisar si se le "
            "anadieron sus tajos por zona, que ensucia el catalogo comun.")

    def test_orueta_es_legible_con_su_propia_ficha(self):
        ficha = _ficha(ORUETA)
        if ficha is None:
            self.skipTest("Orueta no tiene ficha_obra.json")
        indice = rejilla.tabla_con_tajos_de_obra(ficha, self.comun)
        self.assertEqual(
            _sin_reconocer(ficha, indice), [],
            "Quedan tajos de Orueta sin resolver ni con su propia ficha.")

    def test_la_guarda_sigue_rechazando_lo_inventado(self):
        """Lo que NO puede pasar: que ampliar la tabla la vuelva permisiva."""
        ficha = _ficha(ORUETA) or {"tajos": {"detalle": []}}
        indice = rejilla.tabla_con_tajos_de_obra(ficha, self.comun)
        for inventado in ("Tajo Que No Existe En Ningun Sitio",
                          "Focos Del Tejado", ""):
            self.assertIsNone(
                indice.get(rejilla.fold(inventado)),
                f"{inventado!r} no esta ni en el catalogo ni en la ficha y "
                f"aun asi se reconoce.")

    def test_no_modifica_la_tabla_comun(self):
        """La comun es de todas las obras: ampliarla para una las tocaria a todas."""
        antes = dict(self.comun)
        ficha = _ficha(ORUETA)
        if ficha is None:
            self.skipTest("Orueta no tiene ficha_obra.json")
        rejilla.tabla_con_tajos_de_obra(ficha, self.comun)
        self.assertEqual(self.comun, antes,
                         "tabla_con_tajos_de_obra ha mutado la tabla comun.")

    def test_las_demas_obras_no_ganan_nombres(self):
        """Sus tajos ya estan todos en el catalogo comun: no deben anadir nada."""
        for obra in ("2026 MUNGIA ACR NEINOR", "2026 BOLUETA ACR",
                     "2025 GERNIKA 32V"):
            ficha = _ficha(obra)
            if ficha is None:
                continue
            extra = set(rejilla.tabla_con_tajos_de_obra(ficha, self.comun))
            self.assertEqual(
                sorted(extra - set(self.comun)), [],
                f"{obra} aporta nombres propios: o son tajos nuevos sin "
                f"declarar en el catalogo comun, o hay una errata.")

    def test_el_catalogo_comun_manda_en_caso_de_choque(self):
        """Si la ficha repite un nombre del catalogo, gana el catalogo."""
        nombre = next(iter(self.comun))
        esperado = self.comun[nombre]
        ficha = {"tajos": {"detalle": [
            {"id": "impostor", "nombre": nombre}]}}
        indice = rejilla.tabla_con_tajos_de_obra(ficha, self.comun)
        self.assertEqual(indice[nombre]["id"], esperado["id"])


if __name__ == "__main__":
    unittest.main()
