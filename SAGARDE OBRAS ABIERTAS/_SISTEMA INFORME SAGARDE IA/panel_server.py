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

from nota_pendiente import marcar_tarea_hecha


HOST_LOCAL = '127.0.0.1'
PUERTO_PREDETERMINADO = 8765
DIRECTORIO_OBRAS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_MARCAR_HECHO = '/api/marcar_hecho'


def _obra_carpeta_valida(obra_carpeta):
    return (isinstance(obra_carpeta, str)
            and bool(obra_carpeta)
            and '..' not in obra_carpeta
            and not os.path.isabs(obra_carpeta))


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
        if not _obra_carpeta_valida(obra_carpeta):
            self._responder_json(400, False, 'La carpeta de obra no es válida.')
            return

        ruta_xlsx = os.path.join(
            self.directory, obra_carpeta, 'FICHA DE OBRA.xlsx')
        try:
            encontrada = marcar_tarea_hecha(
                ruta_xlsx,
                tarea=datos.get('tarea'),
                origen=datos.get('origen'),
                fecha=datos.get('fecha'),
                archivo=datos.get('archivo'),
            )
        except Exception as error:
            self._responder_json(
                500, False, f'No se pudo marcar la tarea: {error}')
            return

        if encontrada:
            self._responder_json(200, True, 'Tarea marcada como Hecho.')
        else:
            self._responder_json(
                404, False, 'No se encontró la tarea pendiente.')


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
