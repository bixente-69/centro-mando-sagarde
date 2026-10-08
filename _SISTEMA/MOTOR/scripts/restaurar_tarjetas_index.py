"""RESTAURAR TARJETAS DEL INDICE tras `regenerar_obra.py --finalizar`.

PARCHE PROVISIONAL (08/10/2026) hasta que `--finalizar` se arregle de raiz.

Por que existe: `--finalizar` reconstruye TODAS las tarjetas de
`SAGARDE OBRAS ABIERTAS/index.html` desde `_cache_resultados_regen.json`, cuya
entrada de cada obra solo se refresca cuando ESA obra se regenera. Las obras
que no se han tocado salen con porcentaje, revisiones y ultima revision
desfasados (visto el 05/10 y el 08/10/2026: Mungia 85,5 % -> 83,8 %, OBRA
PRUEBA 14,2 % -> 5,9 %, Gernika con una revision menos).

Que hace: deja la tarjeta NUEVA solo de las obras que se le indican (las que
se acaban de actualizar) y devuelve todas las demas a como estaban en `HEAD`.
La fila «Ultimo archivo» de cada tarjeta restaurada se conserva la nueva
porque es un dato real de disco. El orden de las tarjetas lo sigue decidiendo
el generador. Una obra sin tarjeta en `HEAD` (obra nueva) se queda como esta.

Uso (desde la raiz del repo):
    py -3.11 _SISTEMA/MOTOR/scripts/restaurar_tarjetas_index.py "2026 OLABEAGA BILBAO" "2026 BOLUETA ACR"

No toca `resumen_obras.json` (ignorado por git, no hay copia a la que volver):
queda desfasado para las obras no tocadas hasta la proxima actualizacion
completa. No hace commit ni publica nada.
"""
import io
import os
import re
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(
    BASE_DIR, os.pardir, os.pardir, os.pardir))  # scripts -> MOTOR -> _SISTEMA -> raiz
INDEX_REL = "SAGARDE OBRAS ABIERTAS/index.html"
INDEX = os.path.join(RAIZ, *INDEX_REL.split("/"))
MARCA = '<div class="grid" id="grid">'
FILA_ULTIMO = re.compile(
    r'<div class="row"><span>Último archivo</span><span>[^<]*</span></div>')


def _trocear(html):
    i0 = html.index(MARCA) + len(MARCA)
    pie = html.index('<p class="footer"')
    i1 = html.rindex('</div>', i0, pie)
    partes = re.split(r'(?=<a class="obra" |<div class="obra disabled")',
                      html[i0:i1])
    return html[:i0], [p for p in partes if p], html[i1:]


def _nombre(tarjeta):
    m = re.search(r'<h2>(.*?)</h2>', tarjeta)
    if not m:
        raise SystemExit("Tarjeta sin <h2>: el formato del indice cambio; "
                         "no se toca nada.")
    return m.group(1)


def main(conservar_nuevas):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    with open(INDEX, encoding="utf-8", newline="") as f:
        actual = f.read()
    cab, partes_nuevas, pie = _trocear(actual)
    nombres_nuevos = [_nombre(p) for p in partes_nuevas]
    desconocidas = [n for n in conservar_nuevas if n not in nombres_nuevos]
    if desconocidas:
        raise SystemExit("Obra(s) sin tarjeta en el indice actual: {}. "
                         "Nombres validos: {}".format(
                             desconocidas, nombres_nuevos))

    head = subprocess.run(
        ["git", "show", "HEAD:" + INDEX_REL], cwd=RAIZ, check=True,
        capture_output=True).stdout.decode("utf-8")
    _, partes_head, _ = _trocear(head)
    por_nombre_head = {_nombre(p): p for p in partes_head}

    # `git show` devuelve LF aunque el fichero de trabajo este en CRLF
    # (autocrlf): se adapta cada tarjeta restaurada al formato del fichero.
    usa_crlf = "\r\n" in actual

    def _al_formato(texto):
        texto = texto.replace("\r\n", "\n")
        return texto.replace("\n", "\r\n") if usa_crlf else texto

    salida, restauradas = [], []
    for nombre, tarjeta in zip(nombres_nuevos, partes_nuevas):
        previa = por_nombre_head.get(nombre)
        if nombre in conservar_nuevas or previa is None:
            salida.append(tarjeta)
            continue
        previa = _al_formato(previa)
        fila_nueva = FILA_ULTIMO.search(tarjeta)
        if fila_nueva and FILA_ULTIMO.search(previa):
            previa = FILA_ULTIMO.sub(lambda _m: fila_nueva.group(0),
                                     previa, count=1)
        salida.append(previa)
        if previa != tarjeta:
            restauradas.append(nombre)

    with open(INDEX, "w", encoding="utf-8", newline="") as f:
        f.write(cab + "".join(salida) + pie)
    print("Tarjetas nuevas conservadas:", ", ".join(conservar_nuevas) or "(ninguna)")
    print("Tarjetas restauradas desde HEAD:",
          ", ".join(restauradas) or "(ninguna: ya estaban igual)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    main(sys.argv[1:])
