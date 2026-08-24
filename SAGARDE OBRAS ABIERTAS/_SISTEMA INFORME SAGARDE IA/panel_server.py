# -*- coding: utf-8 -*-
"""Sirve los paneles de obra y permite marcar tareas en el Excel local."""
import argparse
import functools
import json
import os
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from nota_pendiente import desmarcar_tarea_hecha, marcar_tarea_hecha


HOST_LOCAL = '127.0.0.1'
PUERTO_PREDETERMINADO = 8765
DIRECTORIO_OBRAS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_MARCAR_HECHO = '/api/marcar_hecho'
ACCIONES = {
    'Hecho': marcar_tarea_hecha,
    'Pendiente': desmarcar_tarea_hecha,
}


def _ruta_ficha_contenida(directorio_base, obra_carpeta):
    """Resuelve FICHA DE OBRA.xlsx para obra_carpeta y exige que quede
    dentro de directorio_base.

    No basta con rechazar '..' o rutas absolutas: en Windows una ruta
    "relativa a unidad" como 'C:evil' no es absoluta según os.path.isabs
    ni contiene '..', pero os.path.join('base', 'C:evil', 'x') descarta
    'base' por completo (comportamiento documentado de ntpath.join) y
    devuelve 'C:evil\\x'. Por eso aquí se valida el resultado FINAL ya
    resuelto, no el texto de entrada.
    """
    if not isinstance(obra_carpeta, str) or not obra_carpeta:
        return None
    base = os.path.realpath(directorio_base)
    candidato = os.path.realpath(
        os.path.join(base, obra_carpeta, 'FICHA DE OBRA.xlsx'))
    try:
        comun = os.path.commonpath(
            [os.path.normcase(base), os.path.normcase(candidato)])
    except ValueError:
        return None
    if comun != os.path.normcase(base):
        return None
    return candidato


class ManejadorPanel(SimpleHTTPRequestHandler):
    """Sirve los archivos de Obras Abiertas y su escritura local acotada."""

    def _responder_json(self, estado, ok, mensaje):
        contenido = json.dumps(
            {'ok': ok, 'mensaje': mensaje}, ensure_ascii=False
        ).encode('utf-8')
        self.send_response(estado)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)

    def do_POST(self):
        if urlsplit(self.path).path != RUTA_MARCAR_HECHO:
            self._responder_json(404, False, 'Endpoint no encontrado.')
            return

        try:
            longitud = int(self.headers.get('Content-Length', '0'))
            datos = json.loads(self.rfile.read(longitud).decode('utf-8'))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._responder_json(400, False, 'El cuerpo JSON no es válido.')
            return
        if not isinstance(datos, dict):
            self._responder_json(400, False, 'El cuerpo JSON no es válido.')
            return

        obra_carpeta = datos.get('obra_carpeta')
        ruta_xlsx = _ruta_ficha_contenida(self.directory, obra_carpeta)
        if ruta_xlsx is None:
            self._responder_json(400, False, 'La carpeta de obra no es válida.')
            return

        objetivo = datos.get('objetivo', 'Hecho')
        accion = ACCIONES.get(objetivo)
        if accion is None:
            self._responder_json(
                400, False, "El objetivo debe ser 'Hecho' o 'Pendiente'.")
            return

        try:
            encontrada = accion(
                ruta_xlsx,
                tarea=datos.get('tarea'),
                origen=datos.get('origen'),
                fecha=datos.get('fecha'),
                archivo=datos.get('archivo'),
            )
        except Exception as error:
            self._responder_json(
                500, False, f'No se pudo cambiar la tarea: {error}')
            return

        if encontrada:
            self._responder_json(200, True, f'Tarea marcada como {objetivo}.')
        else:
            origen_esperado = 'Pendiente' if objetivo == 'Hecho' else 'Hecho'
            self._responder_json(
                404, False,
                f'No se encontró la tarea en estado {origen_esperado}.')


def crear_servidor(puerto=PUERTO_PREDETERMINADO,
                   directorio_obras=DIRECTORIO_OBRAS):
    """Crea el servidor ligado exclusivamente a la interfaz local."""
    manejador = functools.partial(
        ManejadorPanel, directory=os.path.abspath(directorio_obras))
    return ThreadingHTTPServer((HOST_LOCAL, puerto), manejador)


def main(argv=None):
    argumentos = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(
        description='Abre los paneles Sagarde con escritura local de tareas.')
    parser.add_argument('--puerto', type=int, default=PUERTO_PREDETERMINADO)
    args = parser.parse_args(argumentos)

    servidor = crear_servidor(puerto=args.puerto)
    url = f'http://{HOST_LOCAL}:{args.puerto}/index.html'
    print(f'Panel local disponible en {url}')
    if not argumentos:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido.')
    finally:
        servidor.server_close()


if __name__ == '__main__':
    main()
