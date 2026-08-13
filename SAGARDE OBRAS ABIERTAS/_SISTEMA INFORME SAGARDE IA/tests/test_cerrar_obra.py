# -*- coding: utf-8 -*-
"""El cierre de una obra mueve datos reales: cada paso se prueba antes.

Cerrar a mano —mover la carpeta y ya— deja la obra en `registro_obras.py`
avisando en cada publicacion y su adaptador huerfano en `adaptadores/`. Es lo
que llevan haciendo Egurrola y Zorrozaure desde que se cerraron.

Todo se prueba sobre un arbol temporal. Ninguna prueba toca una obra real.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SISTEMA_DIR)

import cerrar_obra


def _obra_falsa(raiz, carpeta="2026 OBRA FALSA", con_ficha=True):
    """Monta una obra minima en un arbol temporal."""
    salida = raiz / "SAGARDE OBRAS ABIERTAS" / carpeta / "INFORME SAGARDE IA"
    salida.mkdir(parents=True)
    if con_ficha:
        estados = {}
        for portal in ("p1", "p2"):
            for unidad in ("A", "B"):
                for tajo in ("tabicado", "tubeado", "mecanizado"):
                    estados[f"{portal}__pb__{tajo}__{unidad}"] = {
                        "v": "X", "f": "01/06/2026", "r": "rev_01062026"}
        estados["p1__pb__tabicado__A"]["v"] = "P"
        (salida / "ficha_obra.json").write_text(json.dumps({
            "id": "falsa",
            "tajos": {"aplicables": ["tabicado", "tubeado", "mecanizado"]},
            "estados": estados,
            "revisiones": [{"fecha": "01/06/2026"}],
        }), encoding="utf-8")
    return {
        "id": "falsa",
        "nombre": "2026 OBRA FALSA",
        "carpeta_obra": carpeta,
        "adaptador": "adaptador_falsa",
    }


class TestEstadoDeCierre(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = _obra_falsa(self.raiz)
        self.addCleanup(self._tmp.cleanup)

    def test_mide_la_obra_desde_su_ficha(self):
        e = cerrar_obra.estado_de_cierre(self.raiz, self.obra)
        self.assertEqual(4, e["ubicaciones"])
        self.assertEqual(3, e["tajos"])
        self.assertEqual(12, e["celdas"])

    def test_guarda_el_desglose_y_no_solo_un_porcentaje(self):
        # El porcentaje redondeado es un criterio ciego (CLAUDE.md seccion 3).
        e = cerrar_obra.estado_de_cierre(self.raiz, self.obra)
        self.assertEqual({"X": 11, "P": 1}, e["desglose"])

    def test_una_obra_sin_ficha_no_se_inventa_cifras(self):
        obra = _obra_falsa(self.raiz, carpeta="2026 SIN FICHA", con_ficha=False)
        e = cerrar_obra.estado_de_cierre(self.raiz, obra)
        self.assertEqual({}, e["desglose"])
        self.assertIsNone(e["celdas"])


REGISTRO_DE_JUGUETE = '''# -*- coding: utf-8 -*-
import os


OBRAS = [
    {
        'id': 'una',
        'nombre': '2026 UNA',
        'carpeta_obra': '2026 UNA',
        'adaptador': 'adaptador_una',
    },
    {
        # Un comentario dentro del bloque, como el de OBRA PRUEBA.
        'id': 'otra',
        'nombre': '2026 OTRA',
        'carpeta_obra': '2026 OTRA',
        'adaptador': 'adaptador_otra',
        'materiales_rel': os.path.join('REVISIONES', 'x.xlsx'),
    },
    {
        'id': 'tercera',
        'nombre': '2026 TERCERA',
        'carpeta_obra': '2026 TERCERA',
        'adaptador': 'adaptador_tercera',
    },
]
'''


class TestRetirarDelRegistro(unittest.TestCase):
    """Se reescribe codigo: hay que demostrar que no rompe lo de al lado."""

    def test_quita_solo_esa_obra(self):
        nuevo = cerrar_obra.registro_sin_obra(REGISTRO_DE_JUGUETE, "otra")
        self.assertEqual(["una", "tercera"], cerrar_obra.ids_declarados(nuevo))

    def test_el_resultado_sigue_siendo_python_valido(self):
        nuevo = cerrar_obra.registro_sin_obra(REGISTRO_DE_JUGUETE, "otra")
        compile(nuevo, "registro_obras.py", "exec")

    def test_se_lleva_los_comentarios_de_dentro_del_bloque(self):
        nuevo = cerrar_obra.registro_sin_obra(REGISTRO_DE_JUGUETE, "otra")
        self.assertNotIn("Un comentario dentro del bloque", nuevo)
        self.assertNotIn("adaptador_otra", nuevo)

    def test_las_demas_obras_quedan_intactas(self):
        nuevo = cerrar_obra.registro_sin_obra(REGISTRO_DE_JUGUETE, "otra")
        self.assertIn("'adaptador': 'adaptador_una',", nuevo)
        self.assertIn("'adaptador': 'adaptador_tercera',", nuevo)

    def test_una_obra_que_no_esta_es_un_error_y_no_un_silencio(self):
        with self.assertRaises(cerrar_obra.CierreAbortado):
            cerrar_obra.registro_sin_obra(REGISTRO_DE_JUGUETE, "inexistente")

    def test_si_borrar_por_lineas_se_llevaria_otra_obra_por_delante_aborta(self):
        """La red de seguridad que impide corromper el registro.

        Con dos obras en la misma linea, borrar el rango de lineas del nodo se
        llevaria las dos. La comprobacion posterior tiene que darse cuenta y
        abortar, en vez de escribir un registro al que le falta una obra que
        nadie ha pedido cerrar.
        """
        compacto = (
            "OBRAS = [\n"
            "    {'id': 'una', 'nombre': 'UNA'}, {'id': 'otra', 'nombre': 'OTRA'},\n"
            "]\n"
        )
        # Sin la comprobacion, esto devolveria un registro sin ninguna de las dos.
        with self.assertRaises(cerrar_obra.CierreAbortado):
            cerrar_obra.registro_sin_obra(compacto, "una")


class TestArchivarYMover(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = _obra_falsa(self.raiz)
        adaptadores = (self.raiz / "SAGARDE OBRAS ABIERTAS"
                       / "_SISTEMA INFORME SAGARDE IA" / "adaptadores")
        adaptadores.mkdir(parents=True)
        (adaptadores / "adaptador_falsa.py").write_text("# lee sus hojas",
                                                        encoding="utf-8")
        (self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS").mkdir(parents=True)
        self.addCleanup(self._tmp.cleanup)

    def test_el_adaptador_viaja_dentro_del_SISTEMA_de_la_obra(self):
        destino = cerrar_obra.archivar_adaptador(self.raiz, self.obra)
        self.assertTrue(destino.exists())
        self.assertEqual("_SISTEMA", destino.parent.name)
        origen = (self.raiz / "SAGARDE OBRAS ABIERTAS"
                  / "_SISTEMA INFORME SAGARDE IA" / "adaptadores"
                  / "adaptador_falsa.py")
        self.assertFalse(origen.exists())

    def test_sin_adaptador_no_es_un_error(self):
        cerrar_obra.archivar_adaptador(self.raiz, self.obra)
        self.assertIsNone(cerrar_obra.archivar_adaptador(self.raiz, self.obra))

    def test_la_prueba_del_adaptador_viaja_con_el(self):
        """Descubierto cerrando Orueta de verdad.

        `test_adaptador_obisporueta.py` importa el adaptador. Al archivar solo
        el adaptador, la prueba se quedaba atras importando un modulo que ya
        no existia y tumbaba la suite entera.
        """
        pruebas = (self.raiz / "SAGARDE OBRAS ABIERTAS"
                   / "_SISTEMA INFORME SAGARDE IA" / "tests")
        pruebas.mkdir(parents=True, exist_ok=True)
        (pruebas / "test_adaptador_falsa.py").write_text(
            "import adaptadores.adaptador_falsa", encoding="utf-8")
        cerrar_obra.archivar_adaptador(self.raiz, self.obra)
        self.assertFalse((pruebas / "test_adaptador_falsa.py").exists())
        self.assertTrue((self.raiz / "SAGARDE OBRAS ABIERTAS" / "2026 OBRA FALSA"
                         / "_SISTEMA" / "test_adaptador_falsa.py").exists())

    def test_la_carpeta_acaba_en_obras_cerradas(self):
        destino = cerrar_obra.mover_a_cerradas(self.raiz, self.obra)
        self.assertTrue(
            (destino / "INFORME SAGARDE IA" / "ficha_obra.json").exists())
        self.assertFalse((self.raiz / "SAGARDE OBRAS ABIERTAS"
                          / "2026 OBRA FALSA").exists())

    def test_si_el_destino_ya_existe_aborta_sin_tocar_nada(self):
        (self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS"
         / "2026 OBRA FALSA").mkdir()
        with self.assertRaises(cerrar_obra.CierreAbortado):
            cerrar_obra.mover_a_cerradas(self.raiz, self.obra)
        self.assertTrue((self.raiz / "SAGARDE OBRAS ABIERTAS"
                         / "2026 OBRA FALSA").exists())


class TestFichaDeCierre(unittest.TestCase):
    """Cerrar no puede ser perder: la carpeta debe decir como termino."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = _obra_falsa(self.raiz)
        self.destino = self.raiz / "archivada"
        self.destino.mkdir()
        self.addCleanup(self._tmp.cleanup)

    def test_recoge_el_desglose_medido_y_no_un_resumen(self):
        estado = cerrar_obra.estado_de_cierre(self.raiz, self.obra)
        ruta = cerrar_obra.escribir_cierre(self.destino, estado, "abc1234")
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        self.assertEqual({"X": 11, "P": 1}, datos["estado_final"]["desglose"])
        self.assertEqual(12, datos["estado_final"]["celdas"])
        self.assertEqual("abc1234", datos["commit_al_cerrar"])
        self.assertIn("fecha_cierre", datos)

    def test_vive_dentro_del_SISTEMA_de_la_obra_archivada(self):
        estado = cerrar_obra.estado_de_cierre(self.raiz, self.obra)
        ruta = cerrar_obra.escribir_cierre(self.destino, estado, None)
        self.assertEqual("_SISTEMA", ruta.parent.name)
        self.assertEqual("cierre.json", ruta.name)


class TestInformeEnConsolaWindows(unittest.TestCase):
    """Bixente lo ejecuta desde ficheros .bat, en consola de Windows.

    El separador `·` salia como `?` en la primera prueba real con Orueta. Un
    informe que no se puede imprimir es un informe que no se lee.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = _obra_falsa(self.raiz)
        self.addCleanup(self._tmp.cleanup)

    def test_el_informe_se_puede_imprimir_en_la_consola_heredada(self):
        estado = cerrar_obra.estado_de_cierre(self.raiz, self.obra)
        texto = cerrar_obra._informe(estado)
        for codificacion in ("cp850", "cp1252"):
            texto.encode(codificacion)   # revienta si hay algo no imprimible


class TestOrquestador(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.obra = _obra_falsa(self.raiz)
        motor = (self.raiz / "SAGARDE OBRAS ABIERTAS"
                 / "_SISTEMA INFORME SAGARDE IA")
        (motor / "adaptadores").mkdir(parents=True)
        (motor / "adaptadores" / "adaptador_falsa.py").write_text(
            "#", encoding="utf-8")
        (motor / "registro_obras.py").write_text(
            REGISTRO_DE_JUGUETE.replace("'una'", "'falsa'")
                               .replace("2026 UNA", "2026 OBRA FALSA")
                               .replace("adaptador_una", "adaptador_falsa"),
            encoding="utf-8")
        (self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS").mkdir(parents=True)
        self.registro = motor / "registro_obras.py"
        self.motor = motor
        self.addCleanup(self._tmp.cleanup)

    def test_sin_ejecutar_no_se_mueve_ni_un_fichero(self):
        abiertas = self.raiz / "SAGARDE OBRAS ABIERTAS"
        antes = sorted(p.name for p in abiertas.iterdir())
        r = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=False)
        self.assertFalse(r["movida"])
        self.assertEqual(antes, sorted(p.name for p in abiertas.iterdir()))
        self.assertIn("falsa", cerrar_obra.ids_declarados(
            self.registro.read_text(encoding="utf-8")))

    def test_al_ejecutar_deja_el_entorno_limpio(self):
        r = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertTrue(r["movida"])
        # fuera del registro
        self.assertNotIn("falsa", cerrar_obra.ids_declarados(
            self.registro.read_text(encoding="utf-8")))
        # sin adaptador huerfano
        self.assertFalse(
            (self.motor / "adaptadores" / "adaptador_falsa.py").exists())
        # archivada, con el adaptador y el cierre dentro
        archivada = (self.raiz / "SAGARDE (OLD)" / "OBRAS CERRADAS"
                     / "2026 OBRA FALSA")
        self.assertTrue((archivada / "_SISTEMA" / "adaptador_falsa.py").exists())
        self.assertTrue((archivada / "_SISTEMA" / "cierre.json").exists())

    def test_las_rutas_que_informa_existen_despues_de_mover(self):
        """El adaptador se archiva antes de mover la carpeta.

        En el primer cierre real (Orueta) se informo de la ruta anterior al
        movimiento, que ya no existia. Una ruta que se imprime y no lleva a
        ninguna parte es exactamente lo que este proyecto persigue.
        """
        r = cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertTrue(r["destino"].exists())
        self.assertTrue(r["adaptador"].exists())
        self.assertTrue(r["cierre"].exists())

    def test_una_obra_que_no_esta_en_el_registro_aborta(self):
        with self.assertRaises(cerrar_obra.CierreAbortado):
            cerrar_obra.cerrar(self.raiz, "inexistente", ejecutar=True)

    def test_el_catalogo_de_tajos_no_se_toca(self):
        reglas = self.motor / "reglas"
        reglas.mkdir()
        catalogo = reglas / "CATALOGO_TAJOS.json"
        catalogo.write_text('{"version": "1.3"}', encoding="utf-8")
        antes = catalogo.read_bytes()
        cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertEqual(antes, catalogo.read_bytes())

    def test_con_cambios_sin_commitear_en_lo_implicado_aborta(self):
        # La guarda tiene que consultarse de verdad: una guarda declarada que
        # el codigo no mira es la familia de fallos de este proyecto.
        sucio = ["SAGARDE OBRAS ABIERTAS/2026 OBRA FALSA/x.pdf"]
        with patch.object(cerrar_obra, "cambios_pendientes", return_value=sucio):
            with self.assertRaises(cerrar_obra.CierreAbortado):
                cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertTrue((self.raiz / "SAGARDE OBRAS ABIERTAS"
                         / "2026 OBRA FALSA").exists())

    def test_la_guarda_solo_pregunta_por_lo_que_va_a_mover(self):
        # Exigir el arbol entero limpio bloquearia el primer uso: el propio
        # cerrar_obra.py estara sin publicar la primera vez que se use.
        vistas = []

        def espia(raiz, rutas):
            vistas.append(rutas)
            return []

        with patch.object(cerrar_obra, "cambios_pendientes", espia):
            cerrar_obra.cerrar(self.raiz, "falsa", ejecutar=True)
        self.assertEqual(1, len(vistas))
        rutas = vistas[0]
        self.assertTrue(any("2026 OBRA FALSA" in r for r in rutas))
        self.assertTrue(any("registro_obras.py" in r for r in rutas))
        self.assertTrue(any("adaptador_falsa.py" in r for r in rutas))
        self.assertEqual(3, len(rutas),
                         "la guarda no debe mirar el arbol entero")


if __name__ == "__main__":
    unittest.main()
