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


def _generar(prioridades_garaje, historial=None, snapshot_garaje=None):
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
                historial=historial or [],
                materiales={},
                ficha=ficha,
                documentos=[],
                prioridades=_prioridades_vivienda(),
                prioridades_garaje=prioridades_garaje,
                snapshot_garaje=snapshot_garaje,
                output_path=salida,
            )
        with open(salida, encoding="utf-8") as fichero:
            return fichero.read()


def _snapshot_garaje_desde_prioridades(prioridades_garaje):
    """Mismo mapeo que usa generar_todos.py para pasar de detalle_items al
    esquema {task,floor,building,unit,status} de motor_informes. 'task'
    lleva el NOMBRE (item['trabajo']), no el id: asi lo construye tambien
    ficha_obra.snapshot_desde_ficha para vivienda, y es lo que
    generar_informe_ejecutivo.py necesita para resolver metadatos por
    nombre/alias (con el id ahi, su pagina de garaje salia vacia)."""
    return [
        {
            "task": item["trabajo"], "floor": item["planta"],
            "building": item["edificio"], "unit": item["unidad"],
            "status": item["estado"],
        }
        for item in prioridades_garaje.get("detalle_items") or []
    ]


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
            if vista == "v-riesgos":
                # Desde la pieza 3 de la integracion garaje-obra
                # (25/09/2026), v-riesgos SI cambia a proposito cuando hay
                # garaje: gana su propia seccion de riesgos. Cubierto aparte
                # en TestPanelRiesgosGaraje.
                continue
            if vista == "v-panel":
                # El grafico "Avance por planta y edificio" del Panel
                # ahora funde vivienda y garaje con icono de origen
                # (🏠/🅿️) via _combinar_matriz_planta_edificio -- SIEMPRE
                # marca tambien las series de vivienda con 🏠, haya o no
                # garaje (mismo criterio que Trabajos, pieza 5), asi que
                # v-panel cambia para CUALQUIER obra, no solo con garaje.
                # Cubierto aparte en TestPanelGraficaPlantaGaraje.
                continue
            if vista == "v-trabajos":
                # Pieza 5 (25/09/2026): v-trabajos SI cambia a proposito
                # cuando hay garaje -- a diferencia de Riesgos/Prioridades,
                # aqui las filas se FUNDEN en la misma tabla (Bixente:
                # "trabajos es una cosa, deberia de ir todo junto").
                # Cubierto aparte en TestPanelTrabajosGaraje.
                continue
            with self.subTest(vista=vista):
                self.assertEqual(vistas_con[vista], contenido)

        # v-prioridades (vivienda) NO debe llevar nada de garaje: cada
        # pestaña es autonoma (pieza 6, version corregida 25/09/2026 --
        # la primera version metia el bento de garaje pegado dentro de
        # esta pestaña, malentendido señalado por Bixente: "pestaña
        # prioridades se suponia prioridades de vivienda... pestaña de
        # garaje se suponia igual pero con los datos de garaje").
        self.assertNotIn("🅿️", vistas_con["v-prioridades"])
        # El contenido rico de garaje vive SOLO en su propia pestaña,
        # verificado en detalle en TestPanelGarajeFormatoPrioridades.
        garaje = vistas_con["v-garaje"]
        self.assertIn("Centro de mando · Prioridades", garaje)
        # 'prioridades_garaje' SI cambia a proposito (informe de obra a la
        # carta, confirmado por Bixente 26/09/2026: "por supuesto que debe
        # inclir garaje"). El resto del informe a la carta no se mueve.
        secciones_con = _secciones_informe(con_garaje)
        secciones_sin = _secciones_informe(sin_garaje)
        self.assertEqual(secciones_sin.get('prioridades_garaje'), {})
        self.assertNotEqual(secciones_con.get('prioridades_garaje'), {})
        secciones_con.pop('prioridades_garaje')
        secciones_sin.pop('prioridades_garaje')
        self.assertEqual(secciones_con, secciones_sin)

    def test_sin_base_muestra_el_aviso_y_no_un_recuento_falso(self):
        prioridades = priorizar_ficha_garaje(
            _ficha_garaje(), obra="OBRA GARAJE PRUEBA",
            hoy=date(2026, 9, 24))

        garaje = _vistas(_generar(prioridades))["v-garaje"]

        self.assertIn("banner bad", garaje)
        self.assertIn("no tiene base de datos", garaje)
        self.assertNotIn("<table", garaje)


_HISTORIAL_VIVIENDA = [("24/09/2026", [
    {"task": "T1", "floor": "PB", "building": "P1", "unit": "A", "status": "X"},
    {"task": "T1", "floor": "PB", "building": "P1", "unit": "B", "status": "M"},
    {"task": "T1", "floor": "1", "building": "P1", "unit": "A", "status": ""},
])]


class TestPanelAvanceCombinadoConGaraje(unittest.TestCase):
    """Fase de integracion 25/09/2026: el % de la cabecera del Panel debe
    contar vivienda Y garaje juntos ('si hay garaje... forma parte del
    total de la obra', decision textual de Bixente). Riesgos y
    Prioridades ganan su propia seccion aparte; Trabajos (pieza 5) funde
    las filas en la misma tabla -- ver TestPanelTrabajosGaraje."""

    def test_cabecera_combina_vivienda_y_garaje_en_una_sola_bolsa(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        snapshot_garaje = _snapshot_garaje_desde_prioridades(prioridades_garaje)
        # Vivienda sola: X,M,'' (3 celdas) -> estricto 1/3=33.3%, ponderado
        # (1.0+0.6+0)/3=53.3%. Garaje solo (del fixture de arriba): X,'','',''
        # (4 celdas) -> estricto 1/4=25%. Juntos: X,M,'',X,'','','' (7 celdas)
        # -> estricto 2/7=28.6%, ponderado (1.0+0.6+0+1.0+0+0+0)/7=37.1%
        # (verificado aparte con un script, no de cabeza).
        self.assertEqual(4, len(snapshot_garaje))
        con_garaje = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=snapshot_garaje)
        sin_garaje = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=None)

        panel_con = _vistas(con_garaje)["v-panel"]
        panel_sin = _vistas(sin_garaje)["v-panel"]
        self.assertIn(
            '<div class="value">28.6%</div><div class="hint">Solo tareas '
            '100% terminadas · incluye garaje</div>', panel_con)
        self.assertIn(
            '<div class="value">37.1%</div><div class="hint">Incluye '
            'parciales (estimación) · incluye garaje</div>', panel_con)
        # Sin snapshot_garaje, la cabecera es solo de vivienda (33.3% /
        # 53.3%) y sin la coletilla "incluye garaje" -- mismo comportamiento
        # de antes de esta fase, ningun caso existente deja de funcionar.
        self.assertIn(
            '<div class="value">33.3%</div><div class="hint">Solo tareas '
            '100% terminadas</div>', panel_sin)
        self.assertIn(
            '<div class="value">53.3%</div><div class="hint">Incluye '
            'parciales (estimación)</div>', panel_sin)
        self.assertNotIn("incluye garaje", panel_sin)

    def test_las_demas_vistas_no_cambian_aunque_cambie_la_cabecera(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        snapshot_garaje = _snapshot_garaje_desde_prioridades(prioridades_garaje)
        con_garaje = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=snapshot_garaje)
        sin_garaje = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=None)

        vistas_con = _vistas(con_garaje)
        vistas_sin = _vistas(sin_garaje)
        self.assertEqual(set(vistas_con), set(vistas_sin))
        for vista, contenido in vistas_sin.items():
            if vista == "v-panel":
                continue  # la cabecera SI cambia a proposito, ver el test de arriba
            if vista == "v-garaje":
                # El avance_pct propio del garaje en su pestaña (pieza 6,
                # version corregida) tambien sale de snapshot_garaje --
                # mismo motivo que v-panel, no una desincronizacion.
                continue
            if vista == "v-trabajos":
                # Pieza 5 (25/09/2026): v-trabajos SI cambia a proposito
                # cuando hay garaje -- a diferencia de Riesgos/Prioridades,
                # aqui las filas se FUNDEN en la misma tabla (Bixente:
                # "trabajos es una cosa, deberia de ir todo junto").
                # Cubierto aparte en TestPanelTrabajosGaraje.
                continue
            with self.subTest(vista=vista):
                self.assertEqual(vistas_con[vista], contenido)


class TestPanelRiesgosGaraje(unittest.TestCase):
    """Integracion garaje-obra, pieza 3 (25/09/2026): la vista Riesgos
    debe incluir una seccion de garaje, reutilizando bloque_riesgos tal
    cual (misma funcion que ya usa vivienda), cuando prioridades_garaje
    no es None. Sin garaje, la vista queda exactamente igual que antes."""

    def test_sin_garaje_v_riesgos_no_cambia(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))

        con_garaje = _generar(prioridades_garaje, historial=_HISTORIAL_VIVIENDA)
        sin_garaje = _generar(None, historial=_HISTORIAL_VIVIENDA)

        vistas_con = _vistas(con_garaje)
        vistas_sin = _vistas(sin_garaje)
        self.assertEqual(set(vistas_con), set(vistas_sin) | {"v-garaje"})
        for vista, contenido in vistas_sin.items():
            if vista == "v-riesgos":
                continue
            if vista == "v-trabajos":
                # Pieza 5 (25/09/2026): v-trabajos SI cambia a proposito
                # cuando hay garaje -- a diferencia de Riesgos/Prioridades,
                # aqui las filas se FUNDEN en la misma tabla (Bixente:
                # "trabajos es una cosa, deberia de ir todo junto").
                # Cubierto aparte en TestPanelTrabajosGaraje.
                continue
            with self.subTest(vista=vista):
                self.assertEqual(vistas_con[vista], contenido)

    def test_v_riesgos_sin_garaje_no_tiene_seccion_de_garaje(self):
        html = _generar(None, historial=_HISTORIAL_VIVIENDA)
        riesgos = _vistas(html)["v-riesgos"]
        self.assertNotIn("🅿️ Garaje", riesgos)

    def test_v_riesgos_con_garaje_incluye_su_propia_seccion(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        # Valores reales de esta ficha, calculados aparte con
        # priorizar_ficha_garaje antes de escribir este test (no
        # inventados): resumen listos=2, bloqueados=0, terminados=0,
        # dudas=0; un condicionante activo en 'prevision'
        # (Tubeado de viales -> desbloquea Cableado de viales).
        self.assertEqual(2, prioridades_garaje["resumen"]["listos"])
        self.assertEqual(0, prioridades_garaje["resumen"]["bloqueados"])
        self.assertEqual(1, len(prioridades_garaje["prevision"]))

        html = _generar(prioridades_garaje, historial=_HISTORIAL_VIVIENDA)
        riesgos = _vistas(html)["v-riesgos"]

        self.assertIn("🅿️ Garaje", riesgos)
        self.assertEqual(riesgos.count("Riesgos de producción Sagarde"), 2)
        # bloque_riesgos escribe su HTML con comillas simples (ver su
        # fuente real en panel_obra.py), no dobles.
        self.assertIn(
            "<div class='kpi'><div class='label'>Tajos bloqueados</div>"
            "<div class='value'>0</div>", riesgos)
        self.assertIn("Tubeado de viales", riesgos)
        self.assertIn("Cableado de viales", riesgos)


class TestPanelGarajeFormatoPrioridades(unittest.TestCase):
    """Integracion garaje-obra, pieza 6 (25/09/2026, version CORREGIDA
    tras aviso de Bixente). La pestaña propia "🅿️ Garaje" calca el
    formato completo de Prioridades de vivienda (mismo
    bloque_prioridades_partes, con sufijo='-garaje' para que sus ids no
    choquen con los de vivienda en la misma pagina -- ver _namespace_ids
    en panel_obra.py) -- son DOS PESTAÑAS SEPARADAS, cada una con su
    propio centro de mando completo, no una seccion de garaje pegada
    dentro de la pestaña de vivienda (ese fue el malentendido de la
    primera version: Bixente, textual, "pestaña prioridades se suponia
    prioridades de vivienda... pestaña de garaje se suponia igual que
    prioridades de vivienda pero con los datos de garaje. no se parecen
    en nada"). v-prioridades queda intacta, exactamente igual que antes
    de que existiera garaje."""

    def _prioridades_garaje_con_datos(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        # Mismos valores ya verificados (no inventados) que usa
        # TestPanelRiesgosGaraje.test_v_riesgos_con_garaje_incluye_su_propia_seccion:
        # resumen listos=2, bloqueados=0; un condicionante en 'prevision'.
        self.assertEqual(2, prioridades_garaje["resumen"]["listos"])
        self.assertEqual(1, len(prioridades_garaje["prevision"]))
        return prioridades_garaje

    def test_v_prioridades_nunca_lleva_nada_de_garaje(self):
        """Con garaje o sin el, v-prioridades es solo de vivienda -- es
        la pestaña "🎯 Prioridades 🏠", el icono de casita la marca como
        tal."""
        prioridades_garaje = self._prioridades_garaje_con_datos()
        con_garaje = _vistas(
            _generar(prioridades_garaje, historial=_HISTORIAL_VIVIENDA)
        )["v-prioridades"]
        sin_garaje = _vistas(
            _generar(None, historial=_HISTORIAL_VIVIENDA)
        )["v-prioridades"]
        self.assertNotIn("🅿️", con_garaje)
        self.assertEqual(con_garaje, sin_garaje)

    def test_boton_de_prioridades_lleva_el_icono_de_vivienda(self):
        html = _generar(None, historial=_HISTORIAL_VIVIENDA)
        self.assertIn(
            '<button data-view="v-prioridades">🎯 Prioridades 🏠</button>',
            html)

    def test_v_garaje_incluye_el_formato_completo_de_prioridades(self):
        prioridades_garaje = self._prioridades_garaje_con_datos()
        html = _generar(prioridades_garaje, historial=_HISTORIAL_VIVIENDA)
        garaje = _vistas(html)["v-garaje"]

        self.assertIn("Centro de mando · Prioridades", garaje)
        self.assertIn("Tubeado de viales", garaje)
        self.assertIn("Cableado de viales", garaje)
        # No lleva un <h2>🅿️ Garaje</h2> de mas: la propia pestaña ya
        # esta etiquetada "🅿️ Garaje" en su boton.
        self.assertNotIn("<h2>🅿️ Garaje</h2>", garaje)
        # Encontrado probando en navegador real (25/09/2026): el enlace
        # "Ver calculo y detalle completo" estaba fijo a
        # prioridades_trabajos.json, asi que la instancia de garaje
        # enlazaba en silencio al JSON de vivienda. Debe apuntar al suyo.
        self.assertIn('href="prioridades_trabajos_garaje.json"', garaje)
        self.assertNotIn('href="prioridades_trabajos.json"', garaje)

    def test_ids_de_garaje_llevan_sufijo_y_viven_en_su_propia_pestaña(self):
        """La prueba mas importante de esta pieza: cada id de vivienda
        aparece UNA sola vez, dentro de v-prioridades, sin sufijo; su
        version de garaje aparece UNA sola vez, con '-garaje', dentro de
        v-garaje. Si esto fallara, un document.getElementById en el
        navegador encontraria el elemento de la instancia equivocada --
        en silencio, sin ningun error."""
        prioridades_garaje = self._prioridades_garaje_con_datos()
        html = _generar(prioridades_garaje, historial=_HISTORIAL_VIVIENDA)
        vistas = _vistas(html)
        prioridades, garaje = vistas["v-prioridades"], vistas["v-garaje"]

        def _cuenta_id(texto, id_exacto):
            # id='...' e id="..." conviven en este HTML segun que helper lo
            # escribio (_envolver_plegable usa comillas simples,
            # _tarjeta_timeline_html y el filtro de ejecucion usan dobles):
            # contar con las dos, igual que _RE_ID_HTML al namespacing.
            patron = re.compile(r"""id=['"]%s['"]""" % re.escape(id_exacto))
            return len(patron.findall(texto))

        for id_base in (
            "filtro-sit", "prio-count", "timeline-prio", "sec-ejecucion",
            "sec-dudas", "sec-inv-bloqueado", "sec-inv-sin_revisar",
            "sec-inv-viable", "sec-inv-otros_gremios", "sec-inv-dudas",
            "sec-inv-terminado",
        ):
            with self.subTest(id_base=id_base):
                self.assertEqual(
                    _cuenta_id(prioridades, id_base), 1,
                    f'id {id_base!r} deberia estar en v-prioridades')
                self.assertEqual(
                    _cuenta_id(garaje, id_base + "-garaje"), 1,
                    f'id {id_base + "-garaje"!r} deberia estar en v-garaje')
                # Cada id vive en SU pestaña, no en la otra.
                self.assertEqual(_cuenta_id(garaje, id_base), 0)
                self.assertEqual(
                    _cuenta_id(prioridades, id_base + "-garaje"), 0)

        # sec-prevision solo lo pinta garaje en este dataset (vivienda no
        # tiene prevision en _prioridades_vivienda()): confirma que la
        # ausencia en vivienda no rompe el conteo de garaje.
        self.assertEqual(_cuenta_id(prioridades, "sec-prevision"), 0)
        self.assertEqual(_cuenta_id(garaje, "sec-prevision-garaje"), 1)

        # Los enlaces de navegacion del bento de garaje apuntan a su
        # propio ancla con sufijo, no al de vivienda.
        self.assertIn('href="#sec-ejecucion-garaje"', garaje)
        self.assertIn('data-abre="sec-ejecucion-garaje"', garaje)

    def test_script_indice_no_se_duplica_con_garaje(self):
        """script_indice es el mismo <script> para toda la pagina (ya
        selecciona por clase, no por lista fija de ids): la pestaña de
        garaje no debe repetirlo."""
        prioridades_garaje = self._prioridades_garaje_con_datos()
        html = _generar(prioridades_garaje, historial=_HISTORIAL_VIVIENDA)
        self.assertEqual(
            html.count("function _iniciarNavPrioridades"), 1)


class TestPanelTrabajosGaraje(unittest.TestCase):
    """Integracion garaje-obra, pieza 5 (25/09/2026): a diferencia de
    Riesgos/Prioridades (su propia seccion aparte), en Trabajos las filas
    de vivienda y garaje se FUNDEN en las mismas tablas y en la misma
    grafica -- Bixente, textual: "trabajos es una cosa, deberia de ir
    todo junto" -- cada fila marcada con su icono de origen (🏠/🅿️) para
    no perder de donde viene."""

    def _datos_garaje(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        snapshot_garaje = _snapshot_garaje_desde_prioridades(prioridades_garaje)
        return prioridades_garaje, snapshot_garaje

    def test_v_trabajos_sin_garaje_no_tiene_filas_de_garaje(self):
        html = _generar(None, historial=_HISTORIAL_VIVIENDA)
        trabajos = _vistas(html)["v-trabajos"]
        self.assertNotIn("🅿️", trabajos)
        self.assertIn("🏠", trabajos)

    def test_v_trabajos_con_garaje_funde_las_filas_con_icono_de_origen(self):
        prioridades_garaje, snapshot_garaje = self._datos_garaje()
        html = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=snapshot_garaje)
        trabajos = _vistas(html)["v-trabajos"]

        # Desviaciones de avance: valores reales de
        # motor_informes.detectar_bloqueos(), calculados aparte antes de
        # escribir esta prueba, no inventados. Con este dataset, vivienda
        # aporta 1 fila y garaje 0.
        self.assertIn(
            "<tr><td>🏠</td><td>Planta rezagada</td><td>P1</td><td>1</td>"
            "<td>-</td><td><span class='badge bad'>0.0%</span></td>"
            "<td>Planta 1 de P1 al 0% frente a una media de edificio del "
            "53%.</td></tr>",
            trabajos)
        self.assertNotIn(
            "No se detectan desviaciones de avance con la heurística "
            "actual.", trabajos)

        # Detalle por planta/edificio: valores reales de
        # motor_informes.tabla_detalle(), calculados aparte, no
        # inventados. Vivienda aporta 2 filas (PB, planta 1), garaje 1
        # (Sótano 1).
        self.assertIn(
            "<tr><td>🏠</td><td>P1</td><td>PB</td><td>50.0%</td>"
            "<td>80.0%</td><td>2</td></tr>", trabajos)
        self.assertIn(
            "<tr><td>🏠</td><td>P1</td><td>1</td><td>0.0%</td>"
            "<td>0.0%</td><td>1</td></tr>", trabajos)
        self.assertIn(
            "<tr><td>🅿️</td><td>Garaje principal</td><td>Sótano 1</td>"
            "<td>25.0%</td><td>25.0%</td><td>4</td></tr>", trabajos)

        # Grafica "Avance por tarea": el JSON incrustado en la pagina
        # (const DATA = ...) debe llevar las tareas de garaje con su
        # icono. Valores reales de
        # motor_informes.ranking_tareas_con_memoria(snapshot_garaje),
        # calculados aparte.
        self.assertIn('"🏠 T1"', html)
        self.assertIn('"🅿️ Cableado de viales"', html)
        self.assertIn('"🅿️ Tubeado de viales"', html)

    def test_cabeceras_de_tabla_llevan_columna_de_icono_nueva(self):
        html = _generar(None, historial=_HISTORIAL_VIVIENDA)
        trabajos = _vistas(html)["v-trabajos"]
        self.assertIn(
            "<thead><tr><th></th><th>Tipo</th><th>Edificio</th>"
            "<th>Planta</th><th>Unidad</th><th>Avance</th><th>Motivo</th>"
            "</tr></thead>", trabajos)
        self.assertIn(
            "<thead><tr><th></th><th>Edificio</th><th>Planta</th>"
            "<th>% estricto</th><th>% estimado</th><th>Nº registros</th>"
            "</tr></thead>", trabajos)


class TestPanelGraficaPlantaGaraje(unittest.TestCase):
    """Integracion garaje-obra, pieza extra (25/09/2026, a raiz de aviso
    de Bixente: "Panel: no hay nada de garaje"). El grafico "Avance por
    planta y edificio" del Panel funde vivienda y garaje con icono de
    origen (🏠/🅿️), igual que ya hace Trabajos con sus tablas -- por
    eso SIEMPRE marca tambien a vivienda con 🏠, haya o no garaje (mismo
    criterio de la pieza 5). "Evolución del avance" (el grafico de linea
    temporal) NO se toca: generar_panel() no recibe un historial propio
    de garaje, solo un snapshot puntual -- no hay con que construir una
    serie temporal de garaje todavia."""

    def test_sin_garaje_las_series_de_vivienda_llevan_icono_de_casita(self):
        html = _generar(None, historial=_HISTORIAL_VIVIENDA)
        self.assertIn('"\U0001f3e0 P1"', html)
        self.assertNotIn('"P1"', html.replace('"\U0001f3e0 P1"', ''))

    def test_con_garaje_el_grafico_funde_las_plantas_con_null_en_los_huecos(self):
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        snapshot_garaje = _snapshot_garaje_desde_prioridades(prioridades_garaje)
        html = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=snapshot_garaje)

        # Valores reales de motor_informes.matriz_planta_edificio() sobre
        # ambos snapshots y de panel_obra._combinar_matriz_planta_edificio(),
        # calculados aparte antes de escribir esta prueba (no inventados):
        # labels combinadas ['PB','1','Sótano 1']; vivienda [80.0,0.0,null]
        # bajo '🏠 P1'; garaje [null,null,25.0] bajo '🅿️ Garaje principal'.
        # Se comparan sin espacios porque json.dumps puede o no llevarlos
        # entre separadores segun la version de Python.
        sin_espacios = html.replace(' ', '')
        self.assertIn('"labels":["PB","1","Sótano1"]', sin_espacios)
        self.assertIn('"\U0001f3e0P1":[80.0,0.0,null]', sin_espacios)
        self.assertIn(
            '"\U0001f17f️Garajeprincipal":[null,null,25.0]',
            sin_espacios)

    def test_evolucion_del_avance_sigue_siendo_solo_de_vivienda(self):
        """No hay historial de garaje que combinar todavia -- confirma
        que DATA.serie no cambia por la presencia de garaje (a
        diferencia de DATA.por_planta, que si)."""
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
                ("z1", "garaje_cableado_vial"): "P",
                ("z2", "garaje_tubeado_vial"): "P",
                ("z2", "garaje_cableado_vial"): "P",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        snapshot_garaje = _snapshot_garaje_desde_prioridades(prioridades_garaje)
        con_garaje = _generar(
            prioridades_garaje, historial=_HISTORIAL_VIVIENDA,
            snapshot_garaje=snapshot_garaje)
        sin_garaje = _generar(
            None, historial=_HISTORIAL_VIVIENDA, snapshot_garaje=None)

        def _serie(html):
            inicio = html.index('"serie":')
            fin = html.index(', "por_planta"', inicio)
            return html[inicio:fin]

        self.assertEqual(_serie(con_garaje), _serie(sin_garaje))

    def test_obra_solo_con_garaje_no_falla_por_historial_vacio(self):
        """27/09/2026: Una obra como Olabeaga, en fase de garajes y sin
        revisiones de vivienda todavia (historial=[]), no debe lanzar
        IndexError en panel_obra por intentar acceder a historial[0][0]."""
        prioridades_garaje = priorizar_ficha_garaje(
            _ficha_garaje(estados={
                ("z1", "garaje_tubeado_vial"): "X",
            }),
            obra="OBRA GARAJE PRUEBA", hoy=date(2026, 9, 24))
        snapshot_garaje = _snapshot_garaje_desde_prioridades(prioridades_garaje)
        html = _generar(
            prioridades_garaje, historial=[], snapshot_garaje=snapshot_garaje)
        self.assertIn("Garaje 24/09/2026", html)
        self.assertIn("Solo tareas 100% terminadas · incluye garaje", html)


if __name__ == "__main__":
    unittest.main()
