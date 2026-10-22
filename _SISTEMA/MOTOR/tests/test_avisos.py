# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

MOTOR_DIR = Path(__file__).resolve().parent.parent
ROOT = MOTOR_DIR.parent
sys.path.insert(0, str(MOTOR_DIR))
sys.path.insert(0, str(MOTOR_DIR / "scripts"))
# _SISTEMA/MOTOR -> _SISTEMA -> raiz del proyecto.
RAIZ_PROYECTO = ROOT.parent
sys.path.insert(0, str(RAIZ_PROYECTO / "MANTENIMIENTOS" / "_SISTEMA"))
sys.path.insert(0, str(RAIZ_PROYECTO / "POST-VENTAS" / "_SISTEMA"))

import avisos
import auditor_sagarde
import sagarde_portal
import mantenimientos_index
import postventas_index


def _timestamp_hace(dias):
    return (datetime.now() - timedelta(days=dias)).timestamp()


class TestCaducidadAvisos(unittest.TestCase):

    def test_un_aviso_de_399_dias_sigue_visible(self):
        self.assertTrue(avisos.es_aviso_por_antiguedad(399, desde_dias=90))

    def test_un_aviso_de_400_dias_desaparece(self):
        self.assertFalse(avisos.es_aviso_por_antiguedad(400, desde_dias=90))

    def test_un_aviso_mas_antiguo_tampoco_reaparece(self):
        self.assertFalse(avisos.es_aviso_por_antiguedad(800, desde_dias=90))

    def test_el_umbral_inicial_sigue_siendo_estricto(self):
        self.assertFalse(avisos.es_aviso_por_antiguedad(90, desde_dias=90))
        self.assertTrue(avisos.es_aviso_por_antiguedad(91, desde_dias=90))


class TestPortalAvisos(unittest.TestCase):

    def _alertas_mantenimiento(self, dias):
        contrato = {
            "nombre": "CONTRATO PRUEBA",
            "sub_url": "CONTRATO/index.html",
            "ultima_ts": _timestamp_hace(dias),
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sagarde_portal, "ROOT", Path(tmp)):
                return sagarde_portal.construir_alertas(mant=[contrato])

    def test_el_portal_muestra_399_dias(self):
        alertas = self._alertas_mantenimiento(399)
        self.assertTrue(any("CONTRATO PRUEBA" in texto for _, texto in alertas))

    def test_el_portal_oculta_400_dias(self):
        alertas = self._alertas_mantenimiento(400)
        self.assertFalse(any("CONTRATO PRUEBA" in texto for _, texto in alertas))


class TestAuditoriaAvisos(unittest.TestCase):

    def _auditar_contrato(self, dias):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            contrato = raiz / "MANTENIMIENTOS" / "MANTENIMIENTO PRUEBA"
            contrato.mkdir(parents=True)
            parte = contrato / "parte.pdf"
            parte.write_bytes(b"prueba")
            ts = _timestamp_hace(dias)
            os.utime(parte, (ts, ts))
            with patch.object(auditor_sagarde, "ROOT", raiz):
                return auditor_sagarde.audit_mantenimientos()

    def test_la_auditoria_mantiene_399_dias(self):
        issues = self._auditar_contrato(399)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["dias_antiguedad"], 399)

    def test_la_auditoria_descarta_400_dias(self):
        self.assertEqual(self._auditar_contrato(400), [])


class TestContratoSinAviso(unittest.TestCase):
    """Un contrato rescindido no debe avisar de inactividad en ningun sitio.

    Lo declarado tiene que producir efecto observable (la familia de fallos de
    este proyecto es 'declarado pero ignorado en silencio'): se prueba en el
    portal, en la auditoria y en el indice de mantenimientos."""

    SILENCIADO = {"PRUEBA RESCINDIDO": "rescindido en la prueba"}

    def test_el_nombre_se_reconoce_sin_importar_mayusculas_ni_espacios(self):
        with patch.dict(avisos.CONTRATOS_SIN_AVISO_INACTIVIDAD, self.SILENCIADO):
            self.assertTrue(avisos.contrato_sin_aviso("prueba rescindido "))
            self.assertFalse(avisos.contrato_sin_aviso("OTRO CONTRATO"))
            self.assertFalse(avisos.contrato_sin_aviso(None))

    def test_cada_contrato_declarado_existe_de_verdad(self):
        # Un nombre mal escrito no silenciaria nada y nadie lo notaria.
        for nombre in avisos.CONTRATOS_SIN_AVISO_INACTIVIDAD:
            carpeta = RAIZ_PROYECTO / "MANTENIMIENTOS" / f"MANTENIMIENTO {nombre}"
            self.assertTrue(
                carpeta.is_dir(),
                f"'{nombre}' esta declarado sin aviso pero no existe {carpeta}: "
                "quitalo de avisos.CONTRATOS_SIN_AVISO_INACTIVIDAD o corrige el nombre.",
            )

    def test_obramat_esta_declarado_hasta_que_bixente_diga_otra_cosa(self):
        self.assertTrue(avisos.contrato_sin_aviso("OBRAMAT"))

    def _contrato(self, nombre, dias):
        return {
            "nombre": nombre,
            "sub_url": f"{nombre}/index.html",
            "ultima_ts": _timestamp_hace(dias),
        }

    def test_el_portal_no_avisa_de_un_contrato_rescindido(self):
        contratos = [self._contrato("PRUEBA RESCINDIDO", 143),
                     self._contrato("ACTIVO", 143)]
        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict(avisos.CONTRATOS_SIN_AVISO_INACTIVIDAD, self.SILENCIADO), \
                patch.object(sagarde_portal, "ROOT", Path(tmp)):
            alertas = sagarde_portal.construir_alertas(mant=contratos)
        texto = " ".join(t for _, t in alertas)
        self.assertNotIn("PRUEBA RESCINDIDO", texto)
        self.assertIn("ACTIVO", texto)
        self.assertIn("1 contrato(s) de mantenimiento", texto)

    def test_si_solo_hay_contratos_rescindidos_no_sale_ningun_aviso(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.dict(avisos.CONTRATOS_SIN_AVISO_INACTIVIDAD, self.SILENCIADO), \
                patch.object(sagarde_portal, "ROOT", Path(tmp)):
            alertas = sagarde_portal.construir_alertas(
                mant=[self._contrato("PRUEBA RESCINDIDO", 143)])
        self.assertEqual(alertas, [])

    def _auditar(self, carpeta, dias):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            contrato = raiz / "MANTENIMIENTOS" / carpeta
            contrato.mkdir(parents=True)
            parte = contrato / "parte.pdf"
            parte.write_bytes(b"prueba")
            ts = _timestamp_hace(dias)
            os.utime(parte, (ts, ts))
            with patch.dict(avisos.CONTRATOS_SIN_AVISO_INACTIVIDAD, self.SILENCIADO), \
                    patch.object(auditor_sagarde, "ROOT", raiz):
                return auditor_sagarde.audit_mantenimientos()

    def test_la_auditoria_no_avisa_de_un_contrato_rescindido(self):
        self.assertEqual(self._auditar("MANTENIMIENTO PRUEBA RESCINDIDO", 143), [])

    def test_la_auditoria_sigue_avisando_de_los_demas(self):
        issues = self._auditar("MANTENIMIENTO ACTIVO", 143)
        self.assertEqual([i["obra"] for i in issues], ["ACTIVO"])

    def _escanear_indice(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            for carpeta in ("MANTENIMIENTO PRUEBA RESCINDIDO", "MANTENIMIENTO ACTIVO"):
                (raiz / carpeta).mkdir()
                parte = raiz / carpeta / "parte.pdf"
                parte.write_bytes(b"prueba")
                ts = _timestamp_hace(143)
                os.utime(parte, (ts, ts))
            with patch.dict(avisos.CONTRATOS_SIN_AVISO_INACTIVIDAD, self.SILENCIADO), \
                    patch.object(mantenimientos_index, "ROOT", raiz):
                contratos = mantenimientos_index.scan_mantenimientos()
        return {c["nombre"]: c for c in contratos}

    def test_el_indice_de_mantenimientos_no_marca_aviso_pero_lo_dice(self):
        contratos = self._escanear_indice()
        rescindido = contratos["PRUEBA RESCINDIDO"]
        self.assertFalse(rescindido["aviso_activo"])
        self.assertEqual(rescindido["estado_actividad"], "sin_aviso")
        # Se ve POR QUE no avisa: no se oculta en silencio.
        self.assertIn("rescindido", rescindido["estado_label"].lower())
        self.assertEqual(rescindido["dias_inactivo"], 143)

    def test_el_indice_de_mantenimientos_sigue_marcando_a_los_demas(self):
        activo = self._escanear_indice()["ACTIVO"]
        self.assertTrue(activo["aviso_activo"])
        self.assertEqual(activo["estado_actividad"], "revision_pendiente")


class TestAvisoPostventaSoloSinSolucionar(unittest.TestCase):
    """El aviso de post-venta debe decir solo lo que hay sin solucionar.

    Antes salia 'incidencias activas recientemente' por haber tocado un
    archivo hace poco, aunque todas estuvieran resueltas: daba a malentendido."""

    def _alertas(self, contratos):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(sagarde_portal, "ROOT", Path(tmp)):
            alertas = sagarde_portal.construir_alertas(rp={"contratos": contratos})
        return [(nivel, texto) for nivel, texto in alertas if "post-venta" in texto]

    def _contrato(self, nombre, pendientes, reciente=False):
        return {
            "nombre": nombre,
            "href": f"POST-VENTAS/{nombre}/",
            "reciente": reciente,
            "pendientes": pendientes,
            "ultimo_archivo_ts": _timestamp_hace(3),
        }

    def test_un_contrato_reciente_pero_sin_pendientes_no_avisa(self):
        self.assertEqual(self._alertas([self._contrato("TODO RESUELTO", 0, reciente=True)]), [])

    def test_un_contrato_con_pendientes_avisa_aunque_no_sea_reciente(self):
        alertas = self._alertas([self._contrato("CON PENDIENTES", 3, reciente=False)])
        self.assertEqual(len(alertas), 1)
        texto = alertas[0][1]
        self.assertIn("CON PENDIENTES", texto)
        self.assertIn("3 pendientes", texto)
        self.assertIn("sin solucionar", texto)

    def test_un_solo_pendiente_va_en_singular(self):
        texto = self._alertas([self._contrato("UNO", 1)])[0][1]
        self.assertIn("1 pendiente)", texto)
        self.assertNotIn("1 pendientes", texto)

    def test_pendientes_desconocidos_no_se_cuentan_como_cero_ni_como_aviso(self):
        # Word ausente o con tabla no estandar: no se sabe, y no se inventa.
        self.assertEqual(self._alertas([self._contrato("SIN LEER", None, reciente=True)]), [])

    def test_solo_se_nombran_los_que_tienen_pendientes_y_el_recuento_cuadra(self):
        alertas = self._alertas([
            self._contrato("RESUELTO", 0, reciente=True),
            self._contrato("UNO", 1),
            self._contrato("TRES", 3),
        ])
        texto = alertas[0][1]
        self.assertNotIn("RESUELTO", texto)
        self.assertIn("2 contrato(s)", texto)
        # Primero el que mas pendientes tiene.
        self.assertLess(texto.index("TRES"), texto.index("UNO"))


class TestResumenPostventaPendientes(unittest.TestCase):
    """El portal solo puede avisar de lo que el resumen JSON le cuenta."""

    def _docx(self, ruta, filas, columnas=10):
        from docx import Document
        doc = Document()
        tabla = doc.add_table(rows=0, cols=columnas)
        for fila in filas:
            celdas = tabla.add_row().cells
            for i, valor in enumerate(fila[:columnas]):
                celdas[i].text = valor
        doc.save(str(ruta))

    def _fila(self, cliente, resuelta):
        # Esquema estandar de 10 columnas: 'Resuelta' es la penultima.
        return [cliente, "1", "A", "", "123 Algo no funciona", "01/01/2026",
                "Tec", "", resuelta, ""]

    def _resumir(self, contenidos):
        """contenidos: {nombre_carpeta: filas | None (sin Word) | ('estrecha', filas)}"""
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            (raiz / "_SISTEMA").mkdir()
            previews = raiz / "_SISTEMA" / "_PREVIEWS_WORD"
            resumen = raiz / "_SISTEMA" / "postventas_resumen.json"
            for carpeta, filas in contenidos.items():
                (raiz / carpeta).mkdir()
                if filas is None:
                    (raiz / carpeta / "foto.jpg").write_bytes(b"x")
                elif isinstance(filas, tuple):
                    self._docx(raiz / carpeta / "INCIDENCIAS.docx", filas[1], columnas=3)
                else:
                    self._docx(raiz / carpeta / "INCIDENCIAS.docx", filas)
            with patch.object(postventas_index, "ROOT", raiz), \
                    patch.object(postventas_index, "PREVIEW_DIR", previews), \
                    patch.object(postventas_index, "RESUMEN_JSON", resumen):
                obras = postventas_index.scan_obras()
                postventas_index.attach_word_previews(obras)
                postventas_index.escribir_resumen_json(obras)
                datos = json.loads(resumen.read_text(encoding="utf-8"))
        return {c["carpeta"]: c for c in datos["contratos"]}

    def test_el_resumen_cuenta_solo_las_incidencias_sin_resolver(self):
        contratos = self._resumir({
            "INCIDENCIAS A": [self._fila("Ana", "Si"),
                              self._fila("Beatriz", ""),
                              self._fila("Carlos", "No")],
            "INCIDENCIAS B": [self._fila("Dani", "SI")],
        })
        self.assertEqual(contratos["INCIDENCIAS A"]["pendientes"], 2)
        # Todo resuelto es un 0 CONOCIDO, distinto de 'no se pudo leer' (None).
        self.assertEqual(contratos["INCIDENCIAS B"]["pendientes"], 0)

    def test_sin_word_o_con_tabla_no_estandar_los_pendientes_son_desconocidos(self):
        contratos = self._resumir({
            "INCIDENCIAS SIN WORD": None,
            "INCIDENCIAS ESTRECHA": ("estrecha", [["a", "b", "c"], ["d", "e", ""]]),
        })
        self.assertIsNone(contratos["INCIDENCIAS SIN WORD"]["pendientes"])
        self.assertIsNone(contratos["INCIDENCIAS ESTRECHA"]["pendientes"])


class TestAuditoriaNoTomaPorRevisionLoQueNoLoEs(unittest.TestCase):
    """Planos del proyecto e informes tecnicos de visita no son hojas de revision.

    Los daba como 'fecha invalida' solo porque su nombre lleva 'Parte' o
    'Revision' (Barakaldo y Mungia, 22/10/2026)."""

    def _auditar(self, ficheros):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            obra = raiz / "SAGARDE OBRAS ABIERTAS" / "2026 OBRA X"
            for rel in ficheros:
                ruta = obra / rel
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_bytes(b"x")
            with patch.object(auditor_sagarde, "ROOT", raiz):
                issues = auditor_sagarde.audit_obras_abiertas()
        return [i for i in issues if i["codigo"] == "NOMBRE_FECHA_INVALIDA"]

    def test_un_plano_de_la_documentacion_inicial_no_es_una_revision(self):
        self.assertEqual(self._auditar([
            "DOCUMENTACION INICIAL/P.06 PLANOS INSTALACIONES_rev01_Parte3_pdfa.pdf",
        ]), [])

    def test_un_informe_tecnico_de_visita_no_es_una_hoja_de_revision(self):
        self.assertEqual(self._auditar([
            "REVISIONES/INFORMES TECNICOS DE VISITAS O REUNIONES/Informe_Revision_Detallada_X.pdf",
        ]), [])

    def test_una_revision_de_verdad_sin_fecha_sigue_dando_aviso(self):
        # Control: la exclusion no puede haber apagado el aviso para todos.
        issues = self._auditar(["REVISIONES/REVISION OBRA X sin fecha.docx"])
        self.assertEqual(len(issues), 1)
        self.assertIn("sin fecha", issues[0]["mensaje"])

    def test_una_revision_sin_fecha_junto_a_un_informe_tecnico_se_sigue_viendo(self):
        issues = self._auditar([
            "REVISIONES/REVISION OBRA X sin fecha.docx",
            "REVISIONES/INFORMES TECNICOS DE VISITAS O REUNIONES/Informe_Revision_Y.pdf",
        ])
        self.assertEqual([Path(i["archivo"]).name for i in issues],
                         ["REVISION OBRA X sin fecha.docx"])


if __name__ == "__main__":
    unittest.main()
