# -*- coding: utf-8 -*-
"""Pruebas del orquestador acotado ``actualizar_obra.py``.

Todos los archivos de prueba viven en ``TemporaryDirectory``. Los procesos
externos se parchean: ninguna prueba lee o escribe una obra real.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RAIZ = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SCRIPTS = os.path.join(RAIZ, "_SISTEMA", "MOTOR", "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import actualizar_obra as ao  # noqa: E402


SALIDA_OK = """HOJA: REVISION OBRA 10102026.html   obra: OBRA   fecha: 10/10/2026   (rellenada en el generador, sin tinta)
  celdas impresas con marca: 100   cambios: 10
  de ellos, casillas en blanco -> tajo no empezado (P): 3
  por valor: {'X': 7, 'P': 3}
    'P' -> 'X': 7
    '?' -> 'P': 3

[SIMULACION] no se ha escrito nada.
"""


def _salida(marcas, cambios, blancos, transiciones=None):
    """Salida del CLI con el mismo contrato que ``SALIDA_OK``."""
    if transiciones is None:
        transiciones = "    'P' -> 'X': 7\n    '?' -> 'P': 3\n"
    return (
        "HOJA: REVISION OBRA 10102026.html   obra: OBRA   fecha: 10/10/2026"
        "   (rellenada en el generador, sin tinta)\n"
        f"  celdas impresas con marca: {marcas}   cambios: {cambios}\n"
        f"  de ellos, casillas en blanco -> tajo no empezado (P): {blancos}\n"
        "  por valor: {'X': 7, 'P': 3}\n"
        f"{transiciones}\n"
        "[SIMULACION] no se ha escrito nada.\n"
    )


def _escribir(path, contenido):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(contenido)


def _ficha(*fechas, origen_alta=None):
    ficha = {
        "revisiones": [
            {"id": "rev_" + fecha.replace("/", ""), "fecha": fecha}
            for fecha in fechas
        ],
        "estados": {},
        "estructura": {},
    }
    if origen_alta:
        ficha["estructura"]["_meta"] = {"origen": origen_alta}
    return ficha


class TestDeteccionHojas(unittest.TestCase):
    def test_fecha_aplicada_no_es_pendiente(self):
        with tempfile.TemporaryDirectory() as tmp:
            _escribir(Path(tmp) / "REVISION OBRA 01012026.html", b"aplicada")
            _escribir(Path(tmp) / "REVISION OBRA 02012026.html", b"nueva")

            deteccion = ao.detectar_hojas(
                tmp, _ficha("01/01/2026"), None
            )

        self.assertEqual([h.fecha for h in deteccion.vivienda], ["02/01/2026"])
        self.assertEqual([h.fecha for h in deteccion.ya_aplicadas], ["01/01/2026"])

    def test_copia_identica_a_hoja_aplicada_se_ignora_por_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            aplicada = Path(tmp) / "REVISION OBRA 01012026.html"
            copia = Path(tmp) / "REVISION OBRA 02012026 copia.html"
            _escribir(aplicada, b"mismos bytes")
            _escribir(copia, b"mismos bytes")

            deteccion = ao.detectar_hojas(
                tmp, _ficha("01/01/2026"), None
            )

        self.assertEqual(deteccion.vivienda, [])
        self.assertEqual(len(deteccion.copias_identicas), 1)
        ignorada, referencia = deteccion.copias_identicas[0]
        self.assertEqual(ignorada.ruta.name, copia.name)
        self.assertEqual(referencia.ruta.name, aplicada.name)
        self.assertEqual(ignorada.sha256, referencia.sha256)

    def test_ordena_cronologicamente_y_separa_garaje_de_vivienda(self):
        with tempfile.TemporaryDirectory() as tmp:
            _escribir(Path(tmp) / "REVISION OBRA 03102026.html", b"v3")
            _escribir(Path(tmp) / "REVISION OBRA 01102026.html", b"v1")
            _escribir(Path(tmp) / "REVISION OBRA 02102026_garaje.html", b"g2")
            _escribir(Path(tmp) / "REVISION OBRA 04102026_garaje.html", b"g4")

            deteccion = ao.detectar_hojas(tmp, _ficha(), _ficha())

        self.assertEqual(
            [h.fecha for h in deteccion.vivienda],
            ["01/10/2026", "03/10/2026"],
        )
        self.assertEqual(
            [h.fecha for h in deteccion.garaje],
            ["02/10/2026", "04/10/2026"],
        )

    def test_fecha_de_una_ficha_no_se_aplica_al_otro_tipo(self):
        with tempfile.TemporaryDirectory() as tmp:
            _escribir(Path(tmp) / "REVISION OBRA 01102026.html", b"vivienda")
            _escribir(
                Path(tmp) / "REVISION OBRA 01102026_garaje.html", b"garaje"
            )

            deteccion = ao.detectar_hojas(
                tmp, _ficha("01/10/2026"), _ficha()
            )

        self.assertEqual(deteccion.vivienda, [])
        self.assertEqual([h.fecha for h in deteccion.garaje], ["01/10/2026"])

    def test_hoja_de_alta_declarada_en_la_ficha_no_es_revision_pendiente(self):
        nombre = "REVISION OBRA 27092026.html"
        with tempfile.TemporaryDirectory() as tmp:
            _escribir(Path(tmp) / nombre, b"estructura inicial")

            deteccion = ao.detectar_hojas(
                tmp,
                _ficha(origen_alta="hoja de alta " + nombre),
                None,
            )

        self.assertEqual(deteccion.vivienda, [])
        self.assertEqual([h.ruta.name for h in deteccion.hojas_de_alta], [nombre])

    def test_forzar_fecha_reincluye_una_fecha_aplicada_una_sola_vez(self):
        with tempfile.TemporaryDirectory() as tmp:
            _escribir(Path(tmp) / "REVISION OBRA 01102026.html", b"misma")
            _escribir(Path(tmp) / "REVISION OBRA 01102026 copia.html", b"misma")

            deteccion = ao.detectar_hojas(
                tmp,
                _ficha("01/10/2026"),
                None,
                forzar_fecha="01/10/2026",
            )

        self.assertEqual(len(deteccion.vivienda), 1)
        self.assertEqual(deteccion.vivienda[0].fecha, "01/10/2026")
        self.assertEqual(len(deteccion.copias_identicas), 1)

    def test_garaje_con_sufijo_de_descarga_duplicada_sigue_siendo_garaje(self):
        # El navegador renombra una segunda descarga como «..._garaje (1).html»
        # (Olabeaga 21/10/2026): seguía siendo una hoja de garaje.
        with tempfile.TemporaryDirectory() as tmp:
            _escribir(Path(tmp) / "REVISION OBRA 21102026.html", b"v")
            _escribir(Path(tmp) / "REVISION OBRA 21102026_garaje (1).html", b"g")

            deteccion = ao.detectar_hojas(tmp, _ficha(), _ficha())

        self.assertEqual(
            [h.ruta.name for h in deteccion.vivienda],
            ["REVISION OBRA 21102026.html"],
        )
        self.assertEqual(
            [h.ruta.name for h in deteccion.garaje],
            ["REVISION OBRA 21102026_garaje (1).html"],
        )

    def test_filtro_solo_vivienda_no_detecta_garajes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _escribir(Path(tmp) / "REVISION OBRA 01102026.html", b"v")
            _escribir(Path(tmp) / "REVISION OBRA 01102026_garaje.html", b"g")

            deteccion = ao.detectar_hojas(
                tmp,
                _ficha(),
                _ficha(),
                incluir_garaje=False,
            )

        self.assertEqual([h.fecha for h in deteccion.vivienda], ["01/10/2026"])
        self.assertEqual(deteccion.garaje, [])


class TestParseoYGuardas(unittest.TestCase):
    def test_parsea_resumen_y_transiciones(self):
        analisis = ao.analizar_salida_simulacion(SALIDA_OK)

        self.assertEqual(analisis.marcas, 100)
        self.assertEqual(analisis.cambios, 10)
        self.assertEqual(analisis.blancos_a_p, 3)
        self.assertEqual(
            analisis.transiciones,
            [("P", "X", 7), ("?", "P", 3)],
        )
        self.assertEqual(analisis.guardas, [])

    def test_guarda_estructura_nueva_y_aceptacion_explicita(self):
        salida = """ESTRUCTURA NUEVA EN LA HOJA (se incorpora a la base):
  + Portal 3 / planta 1 / unidad C (47 tajos)
  celdas nuevas en '?': 47
""" + SALIDA_OK

        bloqueada = ao.analizar_salida_simulacion(salida)
        aceptada = ao.analizar_salida_simulacion(
            salida, aceptar_estructura=True
        )

        self.assertEqual([g.codigo for g in bloqueada.guardas], ["estructura_nueva"])
        self.assertIn("unidad C", bloqueada.guardas[0].seccion)
        self.assertEqual(aceptada.guardas, [])
        self.assertEqual(aceptada.estructuras_aceptadas, ["estructura_nueva"])

    def test_guarda_estructura_retirada_y_aceptacion_explicita(self):
        salida = """ESTRUCTURA QUE YA NO ESTA EN LA HOJA (la ultima hoja manda; se retira de la base):
  - Portal 2 / 4 / unidad D (vivienda): 47 celdas
  celdas retiradas: 47
""" + SALIDA_OK

        bloqueada = ao.analizar_salida_simulacion(salida)
        aceptada = ao.analizar_salida_simulacion(
            salida, aceptar_estructura=True
        )

        self.assertEqual(
            [g.codigo for g in bloqueada.guardas], ["estructura_retirada"]
        )
        self.assertIn("47 celdas", bloqueada.guardas[0].seccion)
        self.assertEqual(aceptada.guardas, [])

    def test_marca_sin_aplicar_nunca_se_acepta(self):
        salida = "  [MARCA SIN APLICAR] p1__1__tabicado__C: X\n" + SALIDA_OK

        analisis = ao.analizar_salida_simulacion(
            salida, aceptar_estructura=True
        )

        self.assertEqual([g.codigo for g in analisis.guardas], ["marca_sin_aplicar"])

    def test_abortado_nunca_se_acepta(self):
        salida = "[ABORTADO] La REVISION_NORMALIZADA no es aplicable.\n" + SALIDA_OK

        analisis = ao.analizar_salida_simulacion(
            salida, aceptar_estructura=True
        )

        self.assertEqual([g.codigo for g in analisis.guardas], ["abortado"])

    def test_aviso_sin_resolver_bloquea(self):
        salida = (
            "  [AVISO] 2 clave(s) de la hoja sin resolver: no se retira nada "
            "de la base\n" + SALIDA_OK
        )

        analisis = ao.analizar_salida_simulacion(salida)

        self.assertEqual([g.codigo for g in analisis.guardas], ["sin_resolver"])

    def test_formato_sin_resumen_esperado_bloquea(self):
        analisis = ao.analizar_salida_simulacion(
            "HOJA: formato nuevo\n  total: 10\n"
        )

        self.assertEqual([g.codigo for g in analisis.guardas], ["formato_cambiado"])

    def test_mas_de_400_cambios_medidos_bloquea(self):
        # 404 cambios, 3 de ellos casillas en blanco -> P: 401 cambios medidos.
        salida = SALIDA_OK.replace("marca: 100", "marca: 4000").replace(
            "cambios: 10", "cambios: 404"
        )

        analisis = ao.analizar_salida_simulacion(salida)

        self.assertEqual([g.codigo for g in analisis.guardas], ["hoja_anormal"])
        self.assertIn("401", analisis.guardas[0].motivo)

    def test_mas_del_15_por_ciento_de_marcas_cambiadas_bloquea(self):
        # 19 cambios, 3 en blanco -> P: 16 cambios medidos sobre 100 marcas.
        salida = SALIDA_OK.replace("cambios: 10", "cambios: 19")

        analisis = ao.analizar_salida_simulacion(salida)

        self.assertEqual([g.codigo for g in analisis.guardas], ["hoja_anormal"])
        self.assertIn("16.0%", analisis.guardas[0].motivo)

    def test_simulacion_invoca_cli_con_subprocess_parcheado(self):
        completado = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=SALIDA_OK, stderr=""
        )
        with tempfile.TemporaryDirectory() as tmp:
            hoja = Path(tmp) / "REVISION OBRA 10102026.html"
            _escribir(hoja, b"html")
            with mock.patch.object(
                ao.subprocess, "run", return_value=completado
            ) as ejecutar:
                analisis = ao.simular_vivienda(
                    hoja, "obra", "10/10/2026"
                )

        comando = ejecutar.call_args.args[0]
        self.assertEqual(comando[:2], ["py", "-3.11"])
        self.assertIn("leer_hoja_marcada.py", comando[2])
        self.assertEqual(comando[-4:], ["obra", "--digital", "--fecha", "10/10/2026"])
        self.assertEqual(analisis.cambios, 10)


class TestHojaGrande(unittest.TestCase):
    """Guarda ``hoja_anormal`` replanteada (15/10/2026, Olabeaga).

    Antes contaba TODOS los cambios, incluidas las casillas en blanco -> P,
    contra las celdas con marca. En una obra joven casi todo son blancos que
    pasan a P (el trabajo no empezado que la hoja confirma), asi que 97 cambios
    sobre 153 marcas bloqueaban una hoja correcta y ``--aceptar-estructura`` no
    la saltaba: no habia salida salvo el plan B manual.
    """

    def test_blancos_a_p_no_cuentan_como_hoja_anormal(self):
        # 97 cambios sobre 153 marcas, pero 85 son blancos -> P: 12 medidos.
        analisis = ao.analizar_salida_simulacion(_salida(153, 97, 85))

        self.assertEqual(analisis.guardas, [])
        self.assertEqual(analisis.cambios, 97)
        self.assertEqual(analisis.cambios_medidos, 12)

    def test_caso_real_olabeaga_14_10_se_libera_solo_con_la_cifra_exacta(self):
        """97 cambios sobre 153 marcas: 36 eran ?->P de las zonas nuevas y 61
        cambios medidos de verdad. Medir bien no basta para una obra joven
        (61/153 = 39,9 %): la salida es la bandera con la cifra de la guarda."""
        salida = _salida(153, 97, 36)

        bloqueada = ao.analizar_salida_simulacion(salida)
        liberada = ao.analizar_salida_simulacion(
            salida, aceptar_hoja_grande=[61])

        self.assertEqual([g.codigo for g in bloqueada.guardas], ["hoja_anormal"])
        self.assertEqual(bloqueada.cambios_medidos, 61)
        self.assertIn("--aceptar-hoja-grande 61", bloqueada.guardas[0].motivo)
        self.assertEqual(liberada.guardas, [])
        self.assertEqual(liberada.hoja_grande_aceptada, 61)

    def test_una_obra_joven_con_muchos_cambios_medidos_sigue_bloqueada(self):
        analisis = ao.analizar_salida_simulacion(_salida(153, 97, 0))

        self.assertEqual([g.codigo for g in analisis.guardas], ["hoja_anormal"])
        motivo = analisis.guardas[0].motivo
        self.assertIn("97", motivo)
        self.assertIn("63.4%", motivo)
        # La salida dice como proceder, con el numero exacto de la simulacion.
        self.assertIn("--aceptar-hoja-grande 97", motivo)

    def test_la_guarda_lista_antes_y_despues_para_poder_decidir(self):
        transiciones = "    'P' -> 'X': 60\n    '/' -> 'M': 37\n"
        analisis = ao.analizar_salida_simulacion(
            _salida(153, 97, 0, transiciones))

        seccion = analisis.guardas[0].seccion
        self.assertIn("'P' -> 'X': 60", seccion)
        self.assertIn("'/' -> 'M': 37", seccion)
        self.assertIn("celdas impresas con marca: 153", seccion)

    def test_aceptar_hoja_grande_exige_el_numero_exacto_de_la_simulacion(self):
        salida = _salida(153, 97, 0)

        aceptada = ao.analizar_salida_simulacion(
            salida, aceptar_hoja_grande=[97])
        otra_cifra = ao.analizar_salida_simulacion(
            salida, aceptar_hoja_grande=[96, 98])
        sin_aceptar = ao.analizar_salida_simulacion(
            salida, aceptar_hoja_grande=[])

        self.assertEqual(aceptada.guardas, [])
        self.assertEqual(aceptada.hoja_grande_aceptada, 97)
        self.assertEqual([g.codigo for g in otra_cifra.guardas],
                         ["hoja_anormal"])
        self.assertIsNone(otra_cifra.hoja_grande_aceptada)
        self.assertEqual([g.codigo for g in sin_aceptar.guardas],
                         ["hoja_anormal"])

    def test_aceptar_hoja_grande_no_salta_ninguna_otra_guarda(self):
        salida = ("  [MARCA SIN APLICAR] p1__1__tabicado__C: X\n"
                  + _salida(153, 97, 0))

        analisis = ao.analizar_salida_simulacion(
            salida, aceptar_estructura=True, aceptar_hoja_grande=[97])

        self.assertEqual([g.codigo for g in analisis.guardas],
                         ["marca_sin_aplicar"])
        self.assertEqual(analisis.hoja_grande_aceptada, 97)

    def test_hoja_normal_no_registra_aceptacion_aunque_se_pase_la_bandera(self):
        analisis = ao.analizar_salida_simulacion(
            SALIDA_OK, aceptar_hoja_grande=[10])

        self.assertEqual(analisis.guardas, [])
        self.assertIsNone(analisis.hoja_grande_aceptada)

    def test_el_tope_absoluto_cuenta_solo_cambios_medidos(self):
        # 2000 blancos -> P en una obra grande: normal, no es una hoja rara.
        self.assertEqual(
            ao.analizar_salida_simulacion(_salida(4000, 2100, 2000)).guardas,
            [])
        # 401 cambios medidos sobre 40000 marcas: pasa del tope absoluto.
        analisis = ao.analizar_salida_simulacion(_salida(40000, 401, 0))
        self.assertEqual([g.codigo for g in analisis.guardas], ["hoja_anormal"])

    def test_hoja_sin_marcas_solo_con_blancos_no_es_anormal(self):
        analisis = ao.analizar_salida_simulacion(_salida(0, 12, 12))

        self.assertEqual(analisis.guardas, [])

    def test_parser_acepta_la_bandera_repetida_y_por_defecto_ninguna(self):
        parser = ao.construir_parser()

        self.assertEqual(parser.parse_args(["obra"]).aceptar_hoja_grande, [])
        args = parser.parse_args([
            "obra", "--aceptar-hoja-grande", "97",
            "--aceptar-hoja-grande", "120"])
        self.assertEqual(args.aceptar_hoja_grande, [97, 120])
        with self.assertRaises(SystemExit):
            parser.parse_args(["obra", "--aceptar-hoja-grande", "muchas"])

    def test_simular_y_aplicar_propagan_la_aceptacion_al_analisis(self):
        completado = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=_salida(153, 97, 0), stderr="")
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "REVISION OBRA 10102026.html"
            _escribir(ruta, b"html")
            hoja = ao.Hoja(ruta, "10/10/2026", "20261010", "vivienda", "x" * 64)
            with mock.patch.object(ao.subprocess, "run",
                                   return_value=completado):
                bloqueada = ao.simular_vivienda(ruta, "obra", "10/10/2026")
                simulada = ao.simular_vivienda(
                    ruta, "obra", "10/10/2026", aceptar_hoja_grande=[97])
                with self.assertRaises(ao.RequiereRevisionHumana):
                    ao._aplicar_vivienda(
                        hoja, "obra", aceptar_estructura=False,
                        reemplazar=False)
                aplicada, _salida_cli = ao._aplicar_vivienda(
                    hoja, "obra", aceptar_estructura=False,
                    reemplazar=False, aceptar_hoja_grande=[97])

        self.assertEqual([g.codigo for g in bloqueada.guardas], ["hoja_anormal"])
        self.assertEqual(simulada.guardas, [])
        self.assertEqual(simulada.hoja_grande_aceptada, 97)
        self.assertEqual(aplicada.hoja_grande_aceptada, 97)

    def test_informe_de_hoja_grande_aceptada_lista_antes_y_despues(self):
        transiciones = "    'P' -> 'X': 60\n    '/' -> 'M': 37\n"
        analisis = ao.analizar_salida_simulacion(
            _salida(153, 97, 0, transiciones), aceptar_hoja_grande=[97])
        hoja = ao.Hoja(Path("REVISION OBRA 10102026.html"), "10/10/2026",
                       "20261010", "vivienda", "x" * 64)

        lineas = ao._lineas_hoja_grande(hoja, analisis)

        texto = "\n".join(lineas)
        self.assertIn("--aceptar-hoja-grande 97", texto)
        self.assertIn("REVISION OBRA 10102026.html", texto)
        self.assertIn("'P' -> 'X': 60", texto)
        self.assertIn("'/' -> 'M': 37", texto)
        self.assertEqual(ao._lineas_hoja_grande(
            hoja, ao.analizar_salida_simulacion(SALIDA_OK)), [])


class TestRetrocesos(unittest.TestCase):
    def test_lista_bajadas_retiradas_y_pasos_a_n_con_fecha_anterior(self):
        antes = {
            "estados": {
                "p1__1__a__A": {"v": "X", "f": "01/10/2026"},
                "p1__1__b__A": {"v": "M", "f": "02/10/2026"},
                "p1__1__c__A": {"v": "/", "f": "03/10/2026"},
                "p1__1__d__A": {"v": "P", "f": "04/10/2026"},
            }
        }
        despues = {
            "estados": {
                "p1__1__a__A": {"v": "M", "f": "10/10/2026"},
                "p1__1__b__A": {"v": "N", "f": "10/10/2026"},
                "p1__1__d__A": {"v": "N", "f": "10/10/2026"},
            }
        }

        resultado = ao.calcular_retrocesos(antes, despues)

        self.assertEqual(
            [(r.clave, r.de, r.a, r.fecha_anterior) for r in resultado.bajadas],
            [
                ("p1__1__a__A", "X", "M", "01/10/2026"),
                ("p1__1__b__A", "M", "N", "02/10/2026"),
            ],
        )
        self.assertEqual(
            [(r.clave, r.de, r.a) for r in resultado.retiradas],
            [("p1__1__c__A", "/", "<RETIRADA>")],
        )
        self.assertEqual(
            [(r.clave, r.de) for r in resultado.a_n],
            [("p1__1__b__A", "M"), ("p1__1__d__A", "P")],
        )

    def test_las_bajadas_se_avisan_pero_no_piden_confirmacion(self):
        """Norma de Bixente (15/10/2026): la ultima revision manda, siempre.

        Una marca explicita que baja de X a M ya esta aplicada; el informe la
        enseña como AVISO informativo, nunca como algo que haya que confirmar.
        """
        retro = ao.calcular_retrocesos(
            {"estados": {"p1__1__a__A": {"v": "X", "f": "01/10/2026"}}},
            {"estados": {"p1__1__a__A": {"v": "M", "f": "10/10/2026"}}},
        )

        lineas = ao._lineas_retrocesos(retro)

        self.assertTrue(lineas[0].startswith("E) AVISO"), lineas[0])
        self.assertNotIn("CONFIRMAR", "\n".join(lineas).upper())
        self.assertTrue(any("p1__1__a__A: X -> M" in l for l in lineas))


def _tarjeta(nombre, dato, actualizado, ultimo):
    return (
        f'<a class="obra" href="{nombre}/panel.html"><h2>{nombre}</h2>'
        f'<div class="dato">{dato}</div>'
        f'<div class="row"><span>Actualizado</span><span>{actualizado}</span></div>'
        f'<div class="row"><span>Último archivo</span><span>{ultimo}</span></div>'
        '</a>'
    )


class TestTarjetasIndice(unittest.TestCase):
    def test_solo_permite_cambiar_la_tarjeta_objetivo_e_ignora_horas_y_ultimo(self):
        antes = "<html>" + _tarjeta("OBRA A", "10%", "10:00", "a.pdf") + _tarjeta(
            "OBRA B", "20%", "10:00", "b.pdf"
        ) + "</html>"
        despues = "<html>" + _tarjeta("OBRA A", "11%", "11:00", "a2.pdf") + _tarjeta(
            "OBRA B", "20%", "11:00", "b2.pdf"
        ) + "</html>"

        comparacion = ao.comparar_tarjetas_indice(antes, despues, "OBRA A")

        self.assertEqual(comparacion.cambiadas_ajenas, [])
        self.assertTrue(comparacion.objetivo_cambio)

    def test_detecta_cambio_de_otra_tarjeta(self):
        antes = "<html>" + _tarjeta("OBRA A", "10%", "10:00", "a.pdf") + _tarjeta(
            "OBRA B", "20%", "10:00", "b.pdf"
        ) + "</html>"
        despues = "<html>" + _tarjeta("OBRA A", "11%", "11:00", "a2.pdf") + _tarjeta(
            "OBRA B", "19%", "11:00", "b2.pdf"
        ) + "</html>"

        comparacion = ao.comparar_tarjetas_indice(antes, despues, "OBRA A")

        self.assertEqual(comparacion.cambiadas_ajenas, ["OBRA B"])

    def test_reordenar_tarjetas_en_indice_real_no_es_un_cambio(self):
        def indice(tarjetas, hora):
            return (
                '<div class="grid" id="grid">'
                + "".join(tarjetas)
                + '</div><p class="footer">Actualizado '
                + hora
                + "</p>"
            )

        tarjeta_a = _tarjeta("OBRA A", "10%", "10:00", "a.pdf")
        tarjeta_b = _tarjeta("OBRA B", "20%", "10:00", "b.pdf")
        antes = indice([tarjeta_a, tarjeta_b], "10:00")
        despues = indice([tarjeta_b, tarjeta_a], "11:00")

        comparacion = ao.comparar_tarjetas_indice(antes, despues, "OBRA A")

        self.assertEqual(comparacion.cambiadas_ajenas, [])
        self.assertFalse(comparacion.objetivo_cambio)


class TestShaOtrasObras(unittest.TestCase):
    def test_detecta_efecto_colateral_y_no_omite_ficha_ausente(self):
        obras = [
            {"id": "actual", "carpeta_obra": "ACTUAL"},
            {"id": "otra", "carpeta_obra": "OTRA"},
            {"id": "sin_ficha", "carpeta_obra": "SIN FICHA"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            ficha_otra = Path(tmp) / "OTRA" / "INFORME SAGARDE IA" / "ficha_obra.json"
            _escribir(ficha_otra, b'{"version": 1}')
            antes = ao.sha_fichas_otras_obras(obras, "actual", tmp)
            _escribir(ficha_otra, b'{"version": 2}')
            despues = ao.sha_fichas_otras_obras(obras, "actual", tmp)

        comparacion = ao.comparar_sha_otras(antes, despues)
        self.assertEqual(comparacion.cambiadas, ["otra"])
        self.assertEqual(antes["sin_ficha"], ao.FICHA_AUSENTE)
        self.assertEqual(despues["sin_ficha"], ao.FICHA_AUSENTE)


if __name__ == "__main__":
    unittest.main()
