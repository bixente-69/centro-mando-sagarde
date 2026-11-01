"""Escenas de navegador para la tablet de personal sin cobertura."""

import copy
import hashlib
import json
import mimetypes
import os
import re
import shutil
import struct
import tempfile
import threading
import time
import unittest
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

from playwright.sync_api import sync_playwright


RUTA_WEB = "/SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/"
ARCHIVOS_APP = (
    "generador_personal.html",
    "personal_calculo.js",
    "personal_sw.js",
    "personal_manifest.json",
    "personal_icono_192.png",
    "personal_icono_512.png",
    "personal_icono_apple.png",
)
RELOJ_FIJO = """
(() => {
  const fijo = new Date('2026-10-23T10:00:00+02:00').valueOf();
  const Real = Date;
  class Falsa extends Real {
    constructor(...a) {
      if (a.length === 0) { super(fijo); } else { super(...a); }
    }
    static now() { return fijo; }
  }
  window.Date = Falsa;
})();
"""


def crear_estado(generado="2026-10-23T08:00:00+02:00"):
    """Crea un estado publicado pequeño y válido para una escena."""
    estado = {
        "version": 1,
        "generado": generado,
        "jornada_base_h": 7.5,
        "catalogo": [
            {
                "id": "T0001",
                "nombre": "Mikel",
                "categoria": "",
                "empresa": "",
                "activo": True,
            },
            {
                "id": "T0002",
                "nombre": "Txomin",
                "categoria": "",
                "empresa": "",
                "activo": True,
            },
        ],
        "obras": {
            "olabeaga": {
                "nombre": "2026 OLABEAGA BILBAO",
                "cerrada": False,
                "horario_semanal": {
                    "lun": 7.5,
                    "mar": 7.5,
                    "mie": 7.5,
                    "jue": 7.5,
                    "vie": 7.5,
                    "sab": 0,
                    "dom": 0,
                },
                "excepciones_horario": {},
                "ultima": {
                    "vivienda": {
                        "fecha": "2026-10-22",
                        "presentes": [
                            {"nombre": "Mikel", "horas": 7.5, "extra": 0}
                        ],
                    },
                    "garaje": None,
                },
                "jornadas": [
                    {
                        "fecha": "2026-10-22",
                        "ambito": "vivienda",
                        "nombre": "Mikel",
                        "horas": 7.5,
                        "extra": 0,
                    }
                ],
            }
        },
    }
    if generado is None:
        del estado["generado"]
    return estado


def texto_estado(estado):
    """Serializa el estado como el único renglón JavaScript publicado."""
    datos = json.dumps(estado, ensure_ascii=False, separators=(",", ":"))
    return ("window.SAGARDE_PERSONAL = " + datos + ";").encode("utf-8")


def jornada_pendiente(nombre="Mikel"):
    """Crea una jornada que satisface jornadaOk en la aplicación."""
    return {
        "obra": "olabeaga",
        "ambito": "vivienda",
        "fecha": "2026-10-23",
        "presentes": [{"nombre": nombre, "horas": 7.5, "extra": 0}],
        "anulada": False,
        "notas": "",
        "registrado": "2026-10-23T08:05:00.000Z",
    }


def borrador_guardado():
    """Crea un borrador válido y distinguible para comprobar su conservación."""
    return {
        "obra": "olabeaga",
        "ambito": "vivienda",
        "fecha": "2026-10-23",
        "lista": [{"nombre": "Txomin", "on": True, "horas": 7.5}],
        "prefill": None,
        "marca_prueba": "no tocar",
    }


def json_seguro(texto):
    """Devuelve un JSON o una marca legible de que no se pudo analizar."""
    try:
        return json.loads(texto)
    except (TypeError, json.JSONDecodeError) as error:
        return {"error_json": str(error)}


def dimensiones_png(datos):
    """Lee las dimensiones PNG sin depender de bibliotecas externas."""
    firma = b"\x89PNG\r\n\x1a\n"
    if len(datos) < 24 or datos[:8] != firma or datos[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", datos[16:24])


class AnalizadorEnlaces(HTMLParser):
    """Recoge los enlaces declarados en la cabecera HTML."""

    def __init__(self):
        """Inicializa una lista vacía de atributos de enlaces."""
        super().__init__()
        self.enlaces = []

    def handle_starttag(self, etiqueta, atributos):
        """Guarda los atributos de cada etiqueta link encontrada."""
        if etiqueta.lower() == "link":
            self.enlaces.append(dict(atributos))

    def href_para(self, relacion):
        """Devuelve el href cuya relación coincide con la solicitada."""
        for enlace in self.enlaces:
            relaciones = enlace.get("rel", "").lower().split()
            if relacion in relaciones:
                return enlace.get("href")
        return None


class HTTPDePruebas(ThreadingHTTPServer):
    """Servidor de hilos silencioso para respuestas que el cliente abandona."""

    daemon_threads = True

    def handle_error(self, request, client_address):
        """Silencia desconexiones deliberadas de las escenas sin red."""


class ServidorEnMemoria:
    """Sirve la carpeta web desde un diccionario mutable por escena."""

    def __init__(self):
        """Arranca un servidor local en un puerto libre."""
        self.archivos = {}
        self.retrasos = {}
        self.codigos = {}
        self.red_caida = False
        self.cerrojo = threading.RLock()
        manejador = self._crear_manejador()
        self.http = HTTPDePruebas(("127.0.0.1", 0), manejador)
        self.hilo = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.hilo.start()

    @property
    def origen(self):
        """Devuelve el origen HTTP asignado al servidor."""
        puerto = self.http.server_address[1]
        return f"http://127.0.0.1:{puerto}"

    def reiniciar(self, archivos):
        """Restaura contenido y controles antes de cada escena."""
        with self.cerrojo:
            self.archivos = dict(archivos)
            self.retrasos = {}
            self.codigos = {}
            self.red_caida = False

    def poner_archivo(self, nombre, contenido):
        """Cambia un fichero servido sin tocar el disco de la aplicación."""
        with self.cerrojo:
            self.archivos[nombre] = contenido

    def poner_estado(self, estado):
        """Publica personal_estado.js en memoria para la escena actual."""
        self.poner_archivo("personal_estado.js", texto_estado(estado))

    def poner_codigo(self, nombre, codigo):
        """Fuerza un código HTTP para un fichero concreto."""
        with self.cerrojo:
            if codigo is None:
                self.codigos.pop(nombre, None)
            else:
                self.codigos[nombre] = codigo

    def poner_retraso(self, nombre, segundos):
        """Fija el retraso de respuesta de un fichero concreto."""
        with self.cerrojo:
            self.retrasos[nombre] = segundos

    def poner_red_caida(self, caida):
        """Activa o desactiva el cierre de conexiones sin respuesta."""
        with self.cerrojo:
            self.red_caida = caida

    def cerrar(self):
        """Detiene el servidor y espera brevemente a su hilo principal."""
        self.http.shutdown()
        self.http.server_close()
        self.hilo.join(timeout=5)

    def _crear_manejador(self):
        """Crea un manejador ligado a esta instancia del servidor."""
        servicio = self

        class Manejador(BaseHTTPRequestHandler):
            """Atiende GET con caché, ETag y fallos controlables."""

            protocol_version = "HTTP/1.1"

            def do_GET(self):
                """Entrega un recurso o simula la condición de la escena."""
                with servicio.cerrojo:
                    if servicio.red_caida:
                        self.close_connection = True
                        return
                    ruta = unquote(urlsplit(self.path).path)
                    nombre = ruta[len(RUTA_WEB) :] if ruta.startswith(RUTA_WEB) else None
                    retraso = servicio.retrasos.get(nombre, 0)
                if retraso:
                    time.sleep(retraso)
                with servicio.cerrojo:
                    if servicio.red_caida:
                        self.close_connection = True
                        return
                    codigo = servicio.codigos.get(nombre)
                    contenido = servicio.archivos.get(nombre)
                if codigo is not None:
                    self._enviar(codigo, f"Error {codigo}".encode("ascii"), nombre)
                    return
                if nombre is None or contenido is None or "/" in nombre:
                    self._enviar(404, b"No encontrado", nombre)
                    return
                etag = '"' + hashlib.sha256(contenido).hexdigest() + '"'
                if self.headers.get("If-None-Match") == etag:
                    self._enviar(304, b"", nombre, etag)
                    return
                self._enviar(200, contenido, nombre, etag)

            def _enviar(self, codigo, contenido, nombre, etag=None):
                """Escribe una respuesta con las cabeceras de GitHub Pages."""
                try:
                    self.send_response(codigo)
                    self.send_header("Cache-Control", "max-age=600")
                    if etag:
                        self.send_header("ETag", etag)
                    tipo = mimetypes.guess_type(nombre or "")[0]
                    if nombre and nombre.endswith(".js"):
                        tipo = "text/javascript"
                    if nombre and nombre.endswith(".json"):
                        tipo = "application/manifest+json"
                    self.send_header("Content-Type", (tipo or "text/plain") + "; charset=utf-8")
                    self.send_header("Content-Length", str(len(contenido)))
                    self.end_headers()
                    if contenido and self.command != "HEAD":
                        self.wfile.write(contenido)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    self.close_connection = True

            def log_message(self, format, *args):
                """Evita ruido HTTP en la salida de unittest."""

        return Manejador


class TabletPersonalSinCobertura(unittest.TestCase):
    """Comprueba las trece escenas funcionales de la tablet."""

    @classmethod
    def setUpClass(cls):
        """Carga APP, crea el temporal y abre un único Chromium."""
        app_indicada = os.environ.get("P3_APP")
        cls.app = Path(app_indicada).resolve() if app_indicada else Path(__file__).resolve().parents[1]
        cls.archivos_base = {}
        for nombre in ARCHIVOS_APP:
            ruta = cls.app / nombre
            if ruta.is_file():
                cls.archivos_base[nombre] = ruta.read_bytes()
        base_temporal = os.environ.get("P3_TMP") or None
        cls.temporal = Path(
            tempfile.mkdtemp(prefix="personal_sin_cobertura_", dir=base_temporal)
        )
        cls.servidor = ServidorEnMemoria()
        cls.base_web = cls.servidor.origen + quote(RUTA_WEB, safe="/")
        cls.url_tablet = cls.base_web + "generador_personal.html"
        cls.playwright = sync_playwright().start()
        cls.navegador = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        """Cierra navegador y servidor, y elimina el temporal único."""
        cls.navegador.close()
        cls.playwright.stop()
        cls.servidor.cerrar()
        shutil.rmtree(cls.temporal, ignore_errors=True)

    def setUp(self):
        """Restaura los recursos y el estado publicado antes de una escena."""
        archivos = dict(self.archivos_base)
        archivos["generador_revisiones.html"] = (
            b"<!doctype html><title>Revisiones de prueba</title><p id='revisiones'>ok</p>"
        )
        self.servidor.reiniciar(archivos)
        self.servidor.poner_estado(crear_estado())

    def _igual(self, visto, esperado, asunto):
        """Compara valores con un fallo castellano de una sola línea."""
        mensaje = f"Se esperaba {asunto}: {esperado!r}; se vio {visto!r}"
        self.assertTrue(visto == esperado, msg=mensaje)

    def _verdad(self, condicion, esperado, visto):
        """Exige una condición con expectativa y observación explícitas."""
        mensaje = f"Se esperaba {esperado}; se vio {visto}"
        self.assertTrue(bool(condicion), msg=mensaje)

    def _contiene(self, texto, fragmento, asunto):
        """Exige un fragmento con un fallo castellano de una sola línea."""
        mensaje = f"Se esperaba {asunto} con {fragmento!r}; se vio {texto!r}"
        self.assertTrue(fragmento in texto, msg=mensaje)

    def _sin_errores(self, errores):
        """Comprueba que la página no produjo errores JavaScript."""
        vistos = [str(error).replace("\n", " ") for error in errores]
        self._igual(vistos, [], "ningún error JavaScript")

    def _contexto(self):
        """Crea un contexto limpio con reloj, zona y locale fijados."""
        contexto = self.navegador.new_context(
            timezone_id="Europe/Madrid",
            locale="es-ES",
            accept_downloads=True,
        )
        contexto.add_init_script(script=RELOJ_FIJO)
        self.addCleanup(contexto.close)
        return contexto

    def _pagina(self, contexto):
        """Crea una página y empieza a recoger sus errores JavaScript."""
        errores = []
        pagina = contexto.new_page()
        pagina.on("pageerror", lambda error: errores.append(str(error)))
        return pagina, errores

    def _abrir_tablet(self, pagina, timeout=10_000):
        """Abre la tablet y espera a que aparezca el selector de obra."""
        pagina.goto(self.url_tablet, wait_until="load", timeout=timeout)
        pagina.wait_for_selector("#obra", state="visible", timeout=timeout)

    def _primera_visita(self, contexto):
        """Prepara en un contexto una visita inicial completa con red."""
        pagina, errores = self._pagina(contexto)
        self._abrir_tablet(pagina)
        pagina.wait_for_function("window.__sw === 'listo'", timeout=10_000)
        pagina.wait_for_function(
            "navigator.serviceWorker.controller !== null", timeout=10_000
        )
        return pagina, errores

    def _texto(self, pagina, selector):
        """Obtiene el texto visible normalizado de un único elemento."""
        cantidad = pagina.locator(selector).count()
        self._igual(cantidad, 1, f"un elemento {selector}")
        return " ".join(pagina.locator(selector).inner_text().split())

    def _href(self, pagina, selector):
        """Obtiene la URL absoluta de un enlace único."""
        cantidad = pagina.locator(selector).count()
        self._igual(cantidad, 1, f"un enlace {selector}")
        return pagina.eval_on_selector(selector, "elemento => elemento.href")

    def _caches_personal(self, pagina):
        """Devuelve las cachés de la tablet y las URL que contienen."""
        return pagina.evaluate(
            """async () => {
              const salida = {};
              for (const nombre of await caches.keys()) {
                if (!nombre.startsWith('sgd-personal-')) continue;
                const cache = await caches.open(nombre);
                salida[nombre] = (await cache.keys()).map(p => p.url).sort();
              }
              return salida;
            }"""
        )

    def _comprobar_cache(self, pagina, nombre):
        """Comprueba nombre y tres entradas limpias de una caché."""
        caches = self._caches_personal(pagina)
        self._igual(sorted(caches), [nombre], "solo la caché vigente")
        urls = caches.get(nombre, [])
        esperadas = sorted(
            self.base_web + fichero
            for fichero in (
                "generador_personal.html",
                "personal_calculo.js",
                "personal_estado.js",
            )
        )
        self._igual(urls, esperadas, "las tres URL exactas de la caché")
        self._verdad(
            all("?" not in url for url in urls),
            "URL de caché sin parámetros",
            urls,
        )

    def _borrar_de_cache(self, pagina, fichero):
        """Borra de la caché v1 un recurso y devuelve el resultado."""
        return pagina.evaluate(
            """async fichero => {
              const cache = await caches.open('sgd-personal-v1');
              return cache.delete(new URL(fichero, location.href).href);
            }""",
            fichero,
        )

    def _anotar_guardar_descargar(self, pagina, nombre="Mikel"):
        """Marca, guarda y descarga una jornada de la persona indicada."""
        fila = pagina.locator(f'#v-app .row[data-nombre="{nombre}"]')
        self._igual(fila.count(), 1, f"una fila para {nombre}")
        boton = fila.locator("button.x")
        if "on" in (boton.get_attribute("class") or "").split():
            boton.click()
        boton.click()
        self._verdad(
            "on" in (boton.get_attribute("class") or "").split(),
            f"{nombre} marcado como presente",
            boton.get_attribute("class"),
        )
        pagina.locator("button[data-guardar]").click()
        pagina.wait_for_function(
            "document.querySelector('#pendientes')?.dataset.n === '1'"
        )
        pagina.locator('nav button[data-v="enviar"]').click()
        preparar = pagina.locator('button[data-preparar="olabeaga"]')
        self._igual(preparar.count(), 1, "el botón de preparar olabeaga")
        with pagina.expect_download(timeout=10_000) as descarga_esperada:
            preparar.click()
        ruta = descarga_esperada.value.path()
        lote = json_seguro(Path(ruta).read_text(encoding="utf-8"))
        self._igual(lote.get("tipo"), "lote_personal", "tipo lote_personal")
        self._igual(lote.get("obra"), "olabeaga", "obra olabeaga")
        jornadas = lote.get("jornadas", [])
        self._igual(len(jornadas), 1, "una jornada descargada")
        presentes = jornadas[0].get("presentes", []) if jornadas else []
        nombres = [persona.get("nombre") for persona in presentes]
        self._verdad(nombre in nombres, f"la jornada de {nombre}", nombres)
        return lote

    def _poner_local_antes(self, contexto, clave, valor):
        """Prepara un valor de localStorage antes de cargar el documento."""
        script = (
            "if (location.protocol === 'http:') {"
            f"localStorage.setItem({json.dumps(clave)}, {json.dumps(valor)});"
            "}"
        )
        contexto.add_init_script(script=script)

    def _ruta_app(self, referencia):
        """Resuelve una referencia solo cuando permanece dentro de APP."""
        if not isinstance(referencia, str):
            return None
        partes = urlsplit(referencia)
        if partes.scheme or partes.netloc or Path(unquote(partes.path)).is_absolute():
            return None
        candidata = (self.app / unquote(partes.path)).resolve()
        try:
            candidata.relative_to(self.app)
        except ValueError:
            return None
        return candidata

    def test_01_primera_visita_con_red_prepara_la_tablet(self):
        """La primera visita carga datos y deja página, cálculo y estado listos."""
        contexto = self._contexto()
        pagina, errores = self._primera_visita(contexto)
        self._igual(
            self._texto(pagina, "#estado-cobertura"),
            "Con cobertura: datos al día",
            "la etiqueta con cobertura",
        )
        self._igual(pagina.evaluate("window.__sw"), "listo", "el worker listo")
        self._verdad(
            pagina.evaluate("navigator.serviceWorker.controller !== null"),
            "la página controlada sin recargar",
            "ningún controlador",
        )
        alcance = pagina.evaluate(
            "navigator.serviceWorker.getRegistration().then(r => r.scope)"
        )
        self._verdad(
            alcance.endswith("/generador_personal.html"),
            "un alcance terminado en /generador_personal.html",
            alcance,
        )
        self._contiene(alcance, "%20", "el alcance codificado")
        self._comprobar_cache(pagina, "sgd-personal-v1")

        manifest_url = self._href(pagina, 'link[rel="manifest"]')
        apple_url = self._href(pagina, 'link[rel="apple-touch-icon"]')
        manifest_respuesta = contexto.request.get(manifest_url)
        self._igual(manifest_respuesta.status, 200, "manifest servido con HTTP 200")
        manifest = json_seguro(manifest_respuesta.text())
        self._igual(manifest.get("name"), "Personal en obra", "nombre del manifest")
        apple_respuesta = contexto.request.get(apple_url)
        self._igual(apple_respuesta.status, 200, "icono Apple servido con HTTP 200")
        iconos = manifest.get("icons", [])
        self._verdad(iconos, "al menos un icono en el manifest", iconos)
        for icono in iconos:
            url = self.base_web + icono.get("src", "")
            respuesta = contexto.request.get(url)
            self._igual(
                respuesta.status,
                200,
                f"icono {icono.get('src')} servido con HTTP 200",
            )
        self._sin_errores(errores)

    def test_02_segunda_visita_sin_cobertura_sigue_operativa(self):
        """La recarga sin red permite anotar, guardar y preparar el lote."""
        contexto = self._contexto()
        pagina, errores = self._primera_visita(contexto)
        self.servidor.poner_red_caida(True)
        pagina.reload(wait_until="load", timeout=10_000)
        pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
        self._igual(
            self._texto(pagina, "#estado-cobertura"),
            "Sin cobertura: usando la lista del 23/10",
            "la etiqueta de la copia guardada",
        )
        origen = self._texto(pagina, "#estado-origen").lower()
        self._contiene(origen, "lista guardada", "el origen de datos")
        self._anotar_guardar_descargar(pagina)
        self._sin_errores(errores)

    def test_03_al_volver_la_cobertura_recibe_datos_al_dia(self):
        """La tablet abandona la copia guardada cuando vuelve la red."""
        contexto = self._contexto()
        pagina, _ = self._primera_visita(contexto)
        self.servidor.poner_red_caida(True)
        pagina.reload(wait_until="load", timeout=10_000)
        pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
        self._igual(
            self._texto(pagina, "#estado-cobertura"),
            "Sin cobertura: usando la lista del 23/10",
            "la etiqueta mientras no hay red",
        )
        self.servidor.poner_red_caida(False)
        pagina.reload(wait_until="load", timeout=10_000)
        pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
        self._igual(
            self._texto(pagina, "#estado-cobertura"),
            "Con cobertura: datos al día",
            "la etiqueta al volver la red",
        )
        origen = self._texto(pagina, "#estado-origen").lower()
        self._contiene(origen, "al día", "el origen actualizado")

    def test_04_sin_calculo_guardado_solo_falta_el_informe(self):
        """La ausencia offline del cálculo no impide el trabajo diario."""
        contexto = self._contexto()
        pagina, errores = self._primera_visita(contexto)
        borrado = self._borrar_de_cache(pagina, "personal_calculo.js")
        self._verdad(borrado, "personal_calculo.js borrado de la caché", borrado)
        self.servidor.poner_red_caida(True)
        pagina.reload(wait_until="load", timeout=10_000)
        pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
        pagina.locator('nav button[data-v="informe"]').click()
        aviso = self._texto(pagina, "#informe-sin-calculo p.aviso")
        self._igual(
            aviso,
            "Informe necesita cobertura la primera vez. Lo demás sigue funcionando: "
            "puedes anotar y enviar.",
            "el aviso del informe sin cálculo",
        )
        pagina.locator('nav button[data-v="app"]').click()
        self._anotar_guardar_descargar(pagina)
        self._sin_errores(errores)

    def test_05_sin_estado_en_cache_usa_la_copia_local(self):
        """La copia local basta aunque la caché del worker pierda el estado."""
        contexto = self._contexto()
        pagina, _ = self._primera_visita(contexto)
        borrado = self._borrar_de_cache(pagina, "personal_estado.js")
        self._verdad(borrado, "personal_estado.js borrado de la caché", borrado)
        self.servidor.poner_red_caida(True)
        pagina.reload(wait_until="load", timeout=10_000)
        pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
        self._igual(
            self._texto(pagina, "#estado-cobertura"),
            "Sin cobertura: usando la lista del 23/10",
            "la etiqueta basada en localStorage",
        )
        pagina.evaluate(
            """() => {
              const clave = 'sgd_personal_estado';
              const estado = JSON.parse(localStorage.getItem(clave));
              delete estado.generado;
              localStorage.setItem(clave, JSON.stringify(estado));
            }"""
        )
        pagina.reload(wait_until="load", timeout=10_000)
        pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
        self._igual(
            self._texto(pagina, "#estado-cobertura"),
            "Sin cobertura: usando la lista guardada",
            "la etiqueta de una copia sin fecha de generación",
        )

    def test_06_version_nueva_renueva_cache_y_conserva_datos(self):
        """La versión v2 aparece al primer reload sin borrar localStorage."""
        contexto = self._contexto()
        pagina, _ = self._primera_visita(contexto)
        pendientes = json.dumps(
            [jornada_pendiente()], ensure_ascii=False, separators=(",", ":")
        )
        borrador = json.dumps(
            borrador_guardado(), ensure_ascii=False, separators=(",", ":")
        )
        pagina.evaluate(
            """valores => {
              localStorage.setItem('sgd_personal_pendientes', valores.pendientes);
              localStorage.setItem('sgd_personal_borrador', valores.borrador);
            }""",
            {"pendientes": pendientes, "borrador": borrador},
        )
        html = self.archivos_base.get("generador_personal.html", b"").decode(
            "utf-8", errors="replace"
        )
        sw = self.archivos_base.get("personal_sw.js", b"").decode(
            "utf-8", errors="replace"
        )
        html_nuevo = html.replace(
            "<title>Personal en obra</title>",
            "<title>Personal en obra v2</title>",
            1,
        )
        sw_nuevo = sw.replace("const VERSION = 'v1';", "const VERSION = 'v2';", 1)
        self._verdad(html_nuevo != html, "un título de página reemplazable", html[:80])
        self._verdad(sw_nuevo != sw, "la línea VERSION v1 reemplazable", sw[:80])
        self.servidor.poner_archivo("generador_personal.html", html_nuevo.encode("utf-8"))
        pagina.reload(wait_until="load", timeout=10_000)
        self._igual(pagina.title(), "Personal en obra v2", "la página nueva al primer reload")
        pagina.wait_for_function("window.__sw === 'listo'", timeout=10_000)
        pagina.evaluate(
            """() => {
              window.__cambiosControlador = 0;
              navigator.serviceWorker.addEventListener('controllerchange', () => {
                window.__cambiosControlador += 1;
              });
            }"""
        )
        self.servidor.poner_archivo("personal_sw.js", sw_nuevo.encode("utf-8"))

        pagina.evaluate(
            "navigator.serviceWorker.getRegistration().then(r => r.update())"
        )
        pagina.wait_for_function("window.__cambiosControlador >= 1", timeout=15_000)
        pagina.evaluate(
            """() => {
              window.__cacheV2Estable = false;
              let estableDesde = performance.now();
              const revisar = async () => {
                const nombres = (await caches.keys()).filter(
                  nombre => nombre.startsWith('sgd-personal-'));
                const soloV2 = nombres.length === 1 &&
                  nombres[0] === 'sgd-personal-v2';
                if (!soloV2) estableDesde = performance.now();
                if (soloV2 && performance.now() - estableDesde >= 1000) {
                  window.__cacheV2Estable = true;
                  return;
                }
                setTimeout(revisar, 50);
              };
              revisar();
            }"""
        )
        pagina.wait_for_function(
            "window.__cacheV2Estable === true",
            timeout=15_000,
        )
        self._comprobar_cache(pagina, "sgd-personal-v2")
        guardado = pagina.evaluate(
            """() => ({
              pendientes: localStorage.getItem('sgd_personal_pendientes'),
              borrador: localStorage.getItem('sgd_personal_borrador')
            })"""
        )
        self._igual(guardado["pendientes"], pendientes, "pendientes idénticos")
        self._igual(guardado["borrador"], borrador, "borrador idéntico")
        self.servidor.poner_red_caida(True)
        pagina.reload(wait_until="load", timeout=10_000)
        pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
        self._igual(pagina.title(), "Personal en obra v2", "la versión nueva sin red")

    def test_07_estado_lento_arranca_con_la_copia_en_cuatro_segundos(self):
        """Un estado que tarda ocho segundos no bloquea la copia local."""
        contexto = self._contexto()
        pagina, _ = self._primera_visita(contexto)
        self.servidor.poner_retraso("personal_estado.js", 8)
        inicio = time.perf_counter()
        pagina.reload(wait_until="load", timeout=10_000)
        pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
        transcurrido = time.perf_counter() - inicio
        self._verdad(
            3 <= transcurrido <= 6.8,
            "una apertura entre 3 y 6,8 segundos",
            f"{transcurrido:.2f} segundos",
        )
        self._igual(
            self._texto(pagina, "#estado-cobertura"),
            "Sin cobertura: usando la lista del 23/10",
            "la etiqueta de la lista guardada ante lentitud",
        )

    def test_08_estado_404_o_500_recupera_copia_y_luego_novedad(self):
        """Los errores HTTP usan la copia y una respuesta posterior la reemplaza."""
        for codigo in (404, 500):
            with self.subTest(codigo=codigo):
                self.servidor.reiniciar(self.archivos_base)
                self.servidor.poner_estado(crear_estado())
                contexto = self._contexto()
                pagina, _ = self._primera_visita(contexto)
                pagina.evaluate(
                    "localStorage.removeItem('sgd_personal_estado')"
                )
                self.servidor.poner_codigo("personal_estado.js", codigo)
                pagina.reload(wait_until="load", timeout=10_000)
                pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
                self._igual(
                    self._texto(pagina, "#estado-cobertura"),
                    "Sin cobertura: usando la lista del 23/10",
                    f"la copia ante HTTP {codigo}",
                )
                generado_nuevo = "2026-10-24T09:15:00+02:00"
                self.servidor.poner_codigo("personal_estado.js", None)
                self.servidor.poner_estado(crear_estado(generado_nuevo))
                pagina.reload(wait_until="load", timeout=10_000)
                pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
                self._igual(
                    self._texto(pagina, "#estado-cobertura"),
                    "Con cobertura: datos al día",
                    f"la recuperación tras HTTP {codigo}",
                )
                generado_local = pagina.evaluate(
                    "JSON.parse(localStorage.getItem('sgd_personal_estado')).generado"
                )
                self._igual(
                    generado_local,
                    generado_nuevo,
                    f"el estado nuevo tras HTTP {codigo}",
                )
                sesion = contexto.new_cdp_session(pagina)
                sesion.send("Network.clearBrowserCache")
                sesion.detach()
                self.servidor.poner_codigo("personal_estado.js", 500)
                pagina.reload(wait_until="load", timeout=10_000)
                pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
                self._igual(
                    self._texto(pagina, "#estado-cobertura"),
                    "Sin cobertura: usando la lista del 24/10",
                    f"la copia actualizada tras HTTP {codigo}",
                )
                contexto.close()

    def test_09_primera_vez_sin_lista_protege_las_jornadas(self):
        """Sin estado se explica la falta y se cuentan solo pendientes reales."""
        self.servidor.poner_codigo("personal_estado.js", 404)
        contexto_vacio = self._contexto()
        pagina_vacia, errores_vacio = self._pagina(contexto_vacio)
        pagina_vacia.goto(self.url_tablet, wait_until="load", timeout=10_000)
        pagina_vacia.wait_for_selector("#sin-estado", state="visible", timeout=10_000)
        self._igual(
            self._texto(pagina_vacia, "#sin-estado .card > p"),
            "Sin datos todavía: abre la tablet una vez con cobertura",
            "la etiqueta de primera visita sin datos",
        )
        self._igual(
            pagina_vacia.locator("#sin-estado-jornadas").count(),
            0,
            "ningún aviso de jornadas cuando no las hay",
        )
        self._sin_errores(errores_vacio)
        contexto_vacio.close()

        contexto_pendiente = self._contexto()
        pendientes = json.dumps(
            [jornada_pendiente()], ensure_ascii=False, separators=(",", ":")
        )
        self._poner_local_antes(
            contexto_pendiente, "sgd_personal_pendientes", pendientes
        )
        pagina_pendiente, errores_pendiente = self._pagina(contexto_pendiente)
        pagina_pendiente.goto(self.url_tablet, wait_until="load", timeout=10_000)
        pagina_pendiente.wait_for_selector(
            "#sin-estado-jornadas", state="visible", timeout=10_000
        )
        self._igual(
            self._texto(pagina_pendiente, "#sin-estado-jornadas"),
            "Jornadas sin enviar: 1. Están a salvo en la tablet. Necesitas cobertura "
            "para cargar la lista y poder seguir.",
            "el aviso que protege una jornada pendiente",
        )
        self._sin_errores(errores_pendiente)

    def test_10_si_falla_el_registro_avisa_y_permite_anotar(self):
        """Un worker 404 se anuncia sin inutilizar el formulario."""
        self.servidor.poner_codigo("personal_sw.js", 404)
        contexto = self._contexto()
        pagina, _ = self._pagina(contexto)
        self._abrir_tablet(pagina)
        pagina.wait_for_function("window.__sw === 'error'", timeout=10_000)
        pagina.wait_for_selector("#aviso-sin-preparar", state="visible", timeout=10_000)
        self._igual(pagina.evaluate("window.__sw"), "error", "el estado de registro error")
        self._igual(
            self._texto(pagina, "#aviso-sin-preparar"),
            "Para usar la tablet sin cobertura, primero tienes que abrirla una vez con cobertura.",
            "el aviso de tablet no preparada",
        )
        boton = pagina.locator('#v-app .row[data-nombre="Mikel"] button.x')
        antes = boton.get_attribute("class")
        boton.click()
        despues = boton.get_attribute("class")
        self._verdad(antes != despues, "el botón de asistencia cambiando estado", despues)

    def test_11_desde_file_funciona_sin_worker_ni_aviso(self):
        """La apertura file carga los datos sin intentar registrar un worker."""
        carpeta = Path(tempfile.mkdtemp(prefix="file_", dir=self.temporal))
        for nombre in (
            "generador_personal.html",
            "personal_calculo.js",
            "personal_manifest.json",
            "personal_icono_apple.png",
        ):
            contenido = self.archivos_base.get(nombre)
            if contenido is not None:
                (carpeta / nombre).write_bytes(contenido)
        (carpeta / "personal_estado.js").write_bytes(texto_estado(crear_estado()))
        contexto = self._contexto()
        pagina, errores = self._pagina(contexto)
        pagina.goto((carpeta / "generador_personal.html").as_uri(), wait_until="load")
        pagina.wait_for_selector("#obra", state="visible", timeout=10_000)
        self._igual(
            pagina.evaluate("typeof window.__sw"),
            "undefined",
            "ningún estado de service worker en file",
        )
        self._igual(
            pagina.locator("#aviso-sin-preparar").count(),
            0,
            "ningún aviso de preparación en file",
        )
        self._igual(
            self._texto(pagina, "#estado-cobertura"),
            "Con cobertura: datos al día",
            "la etiqueta con datos cargados desde file",
        )
        self._sin_errores(errores)

    def test_12_enlaces_manifest_e_iconos_son_coherentes(self):
        """Los recursos enlazados existen y sus rutas y tamaños concuerdan."""
        html_ruta = self.app / "generador_personal.html"
        self._verdad(html_ruta.is_file(), "generador_personal.html dentro de APP", html_ruta)
        html = html_ruta.read_text(encoding="utf-8")
        analizador = AnalizadorEnlaces()
        analizador.feed(html)
        coincidencia = re.search(
            r"serviceWorker\.register\(\s*['\"]([^'\"]+)['\"]", html
        )
        referencias = {
            "service worker": coincidencia.group(1) if coincidencia else None,
            "manifest": analizador.href_para("manifest"),
            "icono Apple": analizador.href_para("apple-touch-icon"),
        }
        rutas = {}
        for asunto, referencia in referencias.items():
            ruta = self._ruta_app(referencia)
            self._verdad(
                ruta is not None,
                f"una ruta relativa segura para {asunto}",
                referencia,
            )
            self._verdad(ruta.is_file(), f"el fichero de {asunto} en APP", ruta)
            rutas[asunto] = ruta

        manifest = json_seguro(rutas["manifest"].read_text(encoding="utf-8"))
        inicio = self._ruta_app(manifest.get("start_url"))
        self._igual(inicio, html_ruta.resolve(), "start_url apuntando a la propia página")
        iconos = manifest.get("icons", [])
        self._verdad(iconos, "iconos declarados por el manifest", iconos)
        for icono in iconos:
            ruta = self._ruta_app(icono.get("src"))
            self._verdad(ruta is not None, "una ruta segura para icono", icono.get("src"))
            self._verdad(ruta.is_file(), "un icono del manifest existente", ruta)
            dimensiones = dimensiones_png(ruta.read_bytes())
            declaradas = re.findall(r"(\d+)x(\d+)", icono.get("sizes", ""))
            esperadas = [tuple(map(int, medida)) for medida in declaradas]
            self._igual(
                esperadas,
                [dimensiones] if dimensiones else [],
                f"el tamaño declarado de {ruta.name}",
            )
        apple = dimensiones_png(rutas["icono Apple"].read_bytes())
        self._igual(apple, (180, 180), "el icono Apple de 180x180")

    def test_13_otras_paginas_no_quedan_controladas(self):
        """El alcance de la tablet no controla una página hermana."""
        contexto = self._contexto()
        self._primera_visita(contexto)
        revisiones = contexto.new_page()
        revisiones.goto(self.base_web + "generador_revisiones.html", wait_until="load")
        revisiones.wait_for_selector("#revisiones", state="visible")
        controlador = revisiones.evaluate("navigator.serviceWorker.controller")
        self._igual(controlador, None, "ningún controlador en generador_revisiones.html")


if __name__ == "__main__":
    unittest.main(verbosity=2)
