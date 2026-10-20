#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
materiales_xlsx.py - comprobar y reparar la hoja de entrega de materiales

Cada obra tiene un Excel ``hoja de entrega de materiales <OBRA>.xlsx`` (en ``MATERIALES/``
para Olabeaga; en ``REVISIONES/`` en las obras que no se han movido)
que el panel lee con ``lectores.leer_materiales``. El panel lee los VALORES
guardados en el fichero (no recalcula formulas), asi que un Excel solo es
valido si se abre con openpyxl Y trae calculado el TOTAL.

Por que existe (20/10/2026): agy anadio material a Olabeaga editando a mano el
XML interno del Excel y lo dejo con dos defectos que no daban error en ningun
sitio visible:
  - declaracion ``encoding="utf-16"`` sobre bytes UTF-8 (no se abre);
  - 505 formulas con el valor en cache en blanco (revienta al leer).
El generador descarto la obra entera y el portal movil dejo de mostrarla.

Uso (desde la raiz del repositorio):

  py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py comprobar olabeaga
  py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py comprobar --todas
  py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py reparar olabeaga
  py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py generar olabeaga
  py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py migrar  olabeaga

``<obra>`` es el id/alias de ``registro_obras.py`` o la ruta a un .xlsx.
Codigos de salida: 0 todo bien · 1 quedan defectos · 2 error de uso.

Dos formatos de libro (ver ``entregas_materiales.py``):
  * REJILLA (Mungia, Bolueta): catalogo x fechas con TOTAL; se comprueba que se
    abra y que el TOTAL traiga valor calculado.
  * REGISTRO DE ENTREGAS (Olabeaga, piloto): hoja ENTREGAS = una fila por linea
    entregada; el resto se genera. ``generar`` rehace las hojas de mes y
    ACUMULADO desde ENTREGAS (equivale a ``reparar`` para este formato);
    ``migrar`` convierte una rejilla en registro, con copia y sin perder
    cantidad.

``reparar`` hace una copia en ``REVISIONES/_SISTEMA/`` ANTES de tocar nada,
corrige el XML (sin tocar ningun dato) y, si el TOTAL queda sin calcular, deja
que Excel recalcule y guarde. Si Excel no esta disponible lo dice y devuelve 1:
nunca da por bueno un fichero que no lo es.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date, datetime

# _SISTEMA/MOTOR/scripts/materiales_xlsx.py -> tres niveles hasta la raiz.
RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     os.pardir, os.pardir, os.pardir))
OBRAS_ABIERTAS = os.path.join(RAIZ, "SAGARDE OBRAS ABIERTAS")
MOTOR_IA = os.path.join(OBRAS_ABIERTAS, "_SISTEMA INFORME SAGARDE IA")

for _p in (MOTOR_IA, os.path.join(MOTOR_IA, "adaptadores")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import entregas_materiales  # noqa: E402

DECLARACION = b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
_RE_DECLARACION = re.compile(rb'^\s*<\?xml[^>]*\?>\s*')
_RE_CODIFICACION = re.compile(rb'^\s*<\?xml[^>]*encoding\s*=\s*["\']([^"\']+)["\']')
_RE_V_EN_BLANCO = re.compile(rb'<v>\s+</v>')
COLUMNA_TOTAL = ("TOTAL", "T.SUMINISTRADO")


class RecalculoNoDisponible(RuntimeError):
    """No se pudo recalcular con Excel (no instalado, bloqueado, tiempo agotado)."""


# --------------------------------------------------------------- diagnostico

def _codificacion_real(datos: bytes) -> str:
    """'utf-16' si los bytes son UTF-16, 'utf-8' si decodifican como UTF-8,
    'otra' en cualquier otro caso."""
    if datos[:2] in (b'\xff\xfe', b'\xfe\xff') or b'\x00' in datos[:4]:
        return 'utf-16'
    try:
        datos.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        return 'otra'


def _codificacion_declarada(datos: bytes):
    m = _RE_CODIFICACION.match(datos)
    return m.group(1).decode('ascii', 'replace').lower() if m else None


def _partes_xml(zf: zipfile.ZipFile):
    return [i.filename for i in zf.infolist()
            if i.filename.endswith(('.xml', '.rels'))]


def _hojas(zf: zipfile.ZipFile):
    return [n for n in _partes_xml(zf) if n.startswith('xl/worksheets/') and n.endswith('.xml')]


def diagnosticar(ruta: str) -> list[str]:
    """Lista de defectos del Excel de materiales. Vacia = el panel lo leera bien."""
    if not os.path.isfile(ruta):
        return [f"No existe el fichero: {ruta}"]
    try:
        zf = zipfile.ZipFile(ruta)
    except zipfile.BadZipFile:
        return ["El fichero no es un .xlsx valido (zip danado)."]

    defectos: list[str] = []
    with zf:
        for nombre in _partes_xml(zf):
            datos = zf.read(nombre)
            declarada = _codificacion_declarada(datos)
            real = _codificacion_real(datos)
            if declarada and declarada.startswith('utf-16') and real != 'utf-16':
                defectos.append(f"{nombre}: declara codificacion {declarada} pero los bytes son {real}.")
            elif declarada == 'utf-8' and real == 'utf-16':
                defectos.append(f"{nombre}: declara codificacion utf-8 pero los bytes son utf-16.")
        for nombre in _hojas(zf):
            n = len(_RE_V_EN_BLANCO.findall(zf.read(nombre)))
            if n:
                defectos.append(f"{nombre}: {n} valor(es) <v> en blanco (celdas con solo espacios).")

    try:
        import openpyxl
    except ImportError:
        return defectos + ["openpyxl no esta instalado: no se puede comprobar el contenido."]
    try:
        # Desde memoria: si openpyxl falla a medias deja el fichero abierto y en
        # Windows eso impide despues sustituirlo (os.replace) o borrarlo.
        with open(ruta, 'rb') as f:
            contenido = f.read()
        con_formulas = openpyxl.load_workbook(io.BytesIO(contenido))
        con_valores = openpyxl.load_workbook(io.BytesIO(contenido), data_only=True)
    except Exception as exc:  # fichero danado: se dice por que, no se traga
        causa = (str(exc).splitlines() or [''])[0]
        return defectos + [f"openpyxl no puede abrirlo ({type(exc).__name__}: {causa})."]

    if entregas_materiales.HOJA_ENTREGAS in con_valores.sheetnames:
        return defectos + _diagnosticar_registro(con_valores)

    for ws_f in con_formulas.worksheets:
        ws_v = con_valores[ws_f.title]
        columna = next((c.column for c in ws_f[1]
                        if isinstance(c.value, str) and c.value.strip().upper() in COLUMNA_TOTAL), None)
        if columna is None:
            if ws_f.title == con_formulas.worksheets[-1].title:
                defectos.append(f"Hoja '{ws_f.title}': no tiene columna TOTAL; "
                                "el panel no podra leer los materiales.")
            continue
        sin_valor = sum(1 for fila in range(2, ws_f.max_row + 1)
                        if isinstance(ws_f.cell(fila, columna).value, str)
                        and ws_f.cell(fila, columna).value.startswith('=')
                        and ws_v.cell(fila, columna).value is None)
        if sin_valor:
            defectos.append(f"Hoja '{ws_f.title}': {sin_valor} formula(s) de la columna TOTAL sin valor "
                            "calculado (el Excel se guardo sin recalcular; el panel las ignora).")
    return defectos


def _diagnosticar_registro(wb) -> list[str]:
    """Defectos de un libro con hoja ENTREGAS: filas que no se cuentan y hojas
    generadas que no coinciden con lo que hay en ENTREGAS."""
    _, avisos = entregas_materiales.leer_registro(wb)
    defectos = list(avisos)
    desfases = entregas_materiales.hojas_desactualizadas(wb)
    if desfases:
        defectos.append("Las hojas generadas no estan al dia con ENTREGAS ("
                        + "; ".join(desfases[:4]) + (" ..." if len(desfases) > 4 else "")
                        + "). Ejecuta: " + entregas_materiales.COMANDO_GENERAR)
    return defectos


def es_registro(ruta: str) -> bool:
    """True si el libro tiene hoja ENTREGAS (formato registro de entregas)."""
    try:
        with zipfile.ZipFile(ruta) as zf:
            wbxml = zf.read("xl/workbook.xml").decode("utf-8", "replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return False
    return bool(re.search(r'<sheet [^>]*name="%s"' % entregas_materiales.HOJA_ENTREGAS, wbxml))


# ------------------------------------------------------------------ reparacion

def reparar_xml(ruta: str) -> list[str]:
    """Corrige las declaraciones de codificacion que no coinciden con los bytes
    y quita los <v> en blanco. No toca ningun dato. Devuelve lo hecho."""
    acciones: list[str] = []
    tmp = ruta + ".reparando.tmp"
    with zipfile.ZipFile(ruta) as zin, zipfile.ZipFile(tmp, "w") as zout:
        hojas = set(_hojas(zin))
        xml = set(_partes_xml(zin))
        for info in zin.infolist():
            datos = zin.read(info.filename)
            if info.filename in xml:
                declarada = _codificacion_declarada(datos)
                real = _codificacion_real(datos)
                desajuste = ((declarada or '').startswith('utf-16') and real != 'utf-16') or \
                            (declarada == 'utf-8' and real == 'utf-16')
                if desajuste and real in ('utf-8', 'utf-16'):
                    if real == 'utf-16':
                        datos = datos.decode('utf-16').encode('utf-8')
                    datos = DECLARACION + b'\r\n' + _RE_DECLARACION.sub(b'', datos)
                    acciones.append(f"{info.filename}: declaracion de codificacion corregida a UTF-8.")
            if info.filename in hojas:
                datos, n = _RE_V_EN_BLANCO.subn(b'', datos)
                if n:
                    acciones.append(f"{info.filename}: {n} valor(es) <v> en blanco eliminados.")
            zout.writestr(info, datos, compress_type=info.compress_type)
    if acciones:
        os.replace(tmp, ruta)
    else:
        os.remove(tmp)
    return acciones


_PS_RECALCULAR = r"""
$ErrorActionPreference = 'Stop'
$ruta = $env:MATERIALES_XLSX_RUTA
$xl = $null; $wb = $null
try {
  $xl = New-Object -ComObject Excel.Application
  $xl.Visible = $false; $xl.DisplayAlerts = $false; $xl.AskToUpdateLinks = $false
  $wb = $xl.Workbooks.Open($ruta, 0, $false)
  $xl.CalculateFull()
  $wb.Save()
} finally {
  if ($wb) { $wb.Close($false) | Out-Null; [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wb) }
  if ($xl) { $xl.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($xl) }
  [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
"""


def recalcular_con_excel(ruta: str, tiempo_max: int = 180) -> None:
    """Abre el .xlsx en Excel, recalcula todo y lo guarda. Trabaja sobre una
    copia y solo la sustituye si el resultado se lee bien."""
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        raise RecalculoNoDisponible("No se encontro PowerShell para llamar a Excel.")
    copia = os.path.splitext(ruta)[0] + ".recalculando.xlsx"
    shutil.copy2(ruta, copia)
    try:
        entorno = dict(os.environ, MATERIALES_XLSX_RUTA=copia)
        try:
            proc = subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-Command", _PS_RECALCULAR],
                env=entorno, capture_output=True, text=True, timeout=tiempo_max)
        except subprocess.TimeoutExpired:
            raise RecalculoNoDisponible(f"Excel no respondio en {tiempo_max} s.")
        if proc.returncode != 0:
            causa = (proc.stderr or proc.stdout or '').strip().splitlines()
            raise RecalculoNoDisponible(
                "No se pudo recalcular con Excel: " + (causa[0] if causa else f"codigo {proc.returncode}"))
        resto = [d for d in diagnosticar(copia) if "sin valor calculado" in d or "no puede abrirlo" in d]
        if resto:
            raise RecalculoNoDisponible("Excel guardo el fichero pero siguen faltando valores: " + resto[0])
        os.replace(copia, ruta)
        copia = None
    finally:
        if copia and os.path.exists(copia):
            os.remove(copia)


def _hacer_copia(ruta: str, motivo: str = "reparar") -> str:
    carpeta = os.path.join(os.path.dirname(os.path.abspath(ruta)), "_SISTEMA")
    os.makedirs(carpeta, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(carpeta, f"{os.path.basename(ruta)}.antes_{motivo}_{marca}.bak")
    shutil.copy2(ruta, destino)
    return destino


def reparar(ruta: str, recalcular=recalcular_con_excel) -> dict:
    """Devuelve ``{'ok', 'acciones', 'pendientes', 'copia'}``. ``ok`` solo es
    verdadero si tras reparar ``diagnosticar`` no encuentra nada."""
    defectos = diagnosticar(ruta)
    if not defectos:
        return {'ok': True, 'acciones': [], 'pendientes': [], 'copia': None}
    if not os.path.isfile(ruta) or any("zip danado" in d for d in defectos):
        return {'ok': False, 'acciones': [], 'pendientes': defectos, 'copia': None}

    copia = _hacer_copia(ruta)
    acciones = reparar_xml(ruta)
    pendientes = diagnosticar(ruta)
    if any("no estan al dia" in d for d in pendientes):
        try:
            entregas_materiales.regenerar_hojas(ruta)
        except Exception as exc:  # se dice por que no pudo, no se calla
            pendientes = pendientes + [f"No se pudieron rehacer las hojas generadas ({type(exc).__name__}: {exc})."]
            return {'ok': False, 'acciones': acciones, 'pendientes': pendientes, 'copia': copia}
        acciones.append("Hojas de mes y ACUMULADO rehechas desde ENTREGAS.")
        pendientes = diagnosticar(ruta)
    if any("sin valor calculado" in d for d in pendientes):
        try:
            recalcular(ruta)
            acciones.append("Totales recalculados con Excel.")
        except RecalculoNoDisponible as exc:
            pendientes = diagnosticar(ruta) + [
                f"{exc} Abre el fichero en Excel y guarda (Ctrl+G) para que calcule los totales."]
            return {'ok': False, 'acciones': acciones, 'pendientes': pendientes, 'copia': copia}
        pendientes = diagnosticar(ruta)
    return {'ok': not pendientes, 'acciones': acciones, 'pendientes': pendientes, 'copia': copia}


def _suma_rejilla(wb) -> float:
    """Suma independiente de todas las cantidades de las columnas con fecha de una
    rejilla antigua: sirve para comprobar que la migracion no pierde nada."""
    total = 0
    for ws in wb.worksheets:
        filas = list(ws.iter_rows(values_only=True))
        if not filas:
            continue
        cols = [i for i, h in enumerate(filas[0]) if isinstance(h, (datetime, date))]
        for fila in filas[1:]:
            for i in cols:
                if i < len(fila) and isinstance(fila[i], (int, float)) and not isinstance(fila[i], bool):
                    total += fila[i]
    return total


def migrar(ruta: str) -> dict:
    """Convierte una rejilla antigua en libro de registro de entregas (hoja
    ENTREGAS + hojas generadas). Copia antes, no pierde cantidad (se comprueba
    con una suma independiente) y no toca nada si algo no cuadra."""
    def falla(*mensajes):
        return {'ok': False, 'acciones': [], 'pendientes': list(mensajes), 'copia': None}

    if not os.path.isfile(ruta):
        return falla(f"No existe el fichero: {ruta}")
    if es_registro(ruta):
        return falla("El libro ya es un registro de entregas (tiene hoja ENTREGAS): no se migra.")
    try:
        wb = entregas_materiales._abrir(ruta, data_only=True)
    except Exception as exc:
        return falla(f"No se pudo abrir el libro ({type(exc).__name__}). Repara antes con: "
                     "py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py reparar <obra>")
    entregas = entregas_materiales.entregas_desde_rejilla(wb)
    if not entregas:
        return falla("No se encontro ninguna entrega con cantidad en las columnas con fecha.")
    esperado, obtenido = _suma_rejilla(wb), sum(e['cantidad'] for e in entregas)
    if abs(esperado - obtenido) > 1e-6:
        return falla(f"La migracion no cuadra (rejilla {esperado} frente a {obtenido} migrado): "
                     "alguna fila con cantidad no se pudo convertir. No se ha tocado nada.")
    tmp = os.path.splitext(ruta)[0] + ".migrando.xlsx"
    try:
        entregas_materiales.crear_libro(entregas, tmp)
        defectos = diagnosticar(tmp)
        if defectos:
            return falla("El libro nuevo no pasa la comprobacion; no se ha tocado nada:", *defectos)
        copia = _hacer_copia(ruta, "migrar")
        os.replace(tmp, ruta)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
    return {'ok': True, 'copia': copia, 'pendientes': diagnosticar(ruta),
            'acciones': [f"{len(entregas)} entrega(s) pasadas a la hoja ENTREGAS ({esperado} unidades en total, "
                         "las mismas que tenia la rejilla). Suministrador y albaran quedan vacios: no constaban."]}


# ------------------------------------------------------------------------- CLI

def ruta_materiales(obra: str) -> str:
    """Ruta del Excel de materiales a partir de un id/alias de obra o una ruta .xlsx."""
    if obra.lower().endswith(".xlsx") or os.path.isfile(obra):
        return os.path.abspath(obra)
    for p in (MOTOR_IA, os.path.join(MOTOR_IA, "adaptadores")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import registro_obras
    cfg = registro_obras.resolver_obra(obra) or next(
        (o for o in registro_obras.OBRAS if o.get('id') == obra.lower()), None)
    if not cfg or not cfg.get('materiales_rel'):
        raise KeyError(f"Obra desconocida o sin hoja de materiales declarada: {obra}")
    return os.path.join(OBRAS_ABIERTAS, cfg['carpeta_obra'], cfg['materiales_rel'])


def _todas_las_hojas() -> list[tuple[str, str]]:
    for p in (MOTOR_IA, os.path.join(MOTOR_IA, "adaptadores")):
        if p not in sys.path:
            sys.path.insert(0, p)
    import registro_obras
    return [(o['nombre'], os.path.join(OBRAS_ABIERTAS, o['carpeta_obra'], o['materiales_rel']))
            for o in registro_obras.OBRAS if o.get('materiales_rel')]


def diagnosticar_todas() -> dict[str, list[str]]:
    """{nombre de obra: defectos} solo para las obras cuyo Excel existe y falla."""
    return {nombre: d for nombre, ruta in _todas_las_hojas()
            if os.path.isfile(ruta) and (d := diagnosticar(ruta))}


def _imprimir(titulo: str, defectos: list[str]) -> None:
    if not defectos:
        print(f"OK  {titulo}")
        return
    print(f"MAL {titulo}")
    for d in defectos:
        print(f"      - {d}")


def _aviso_incompletas(ruta: str) -> None:
    """Informa (sin cambiar el codigo de salida) de las entregas a las que les
    falta suministrador o albaran: es un dato que solo puede dar quien tiene el albaran."""
    if not os.path.isfile(ruta) or not es_registro(ruta):
        return
    try:
        n = entregas_materiales.contar_incompletas(ruta)
    except Exception:
        return           # el diagnostico principal ya habra contado lo que no se pueda leer
    if n:
        print()
        print(f"Aviso: {n} línea(s) sin suministrador o albarán (entrega en mano: suministrador "
              f"«Sagarde»). Complétalas en la hoja {entregas_materiales.HOJA_ENTREGAS}.")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] not in ("comprobar", "reparar", "generar", "migrar"):
        print(__doc__)
        return 2
    orden, destino = argv[0], argv[1]
    try:
        if orden == "comprobar" and destino == "--todas":
            fallos = diagnosticar_todas()
            hojas = [(n, r) for n, r in _todas_las_hojas() if os.path.isfile(r)]
            for nombre, _ in hojas:
                _imprimir(nombre, fallos.get(nombre, []))
            return 1 if fallos else 0
        ruta = ruta_materiales(destino)
    except KeyError as exc:
        print(f"ERROR: {exc.args[0]}")
        return 2

    if orden == "comprobar":
        defectos = diagnosticar(ruta)
        _imprimir(ruta, defectos)
        _aviso_incompletas(ruta)
        if defectos:
            print("\nRepara con: py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py reparar " + destino)
        return 1 if defectos else 0

    if orden == "migrar":
        res = migrar(ruta)
    elif orden == "generar":
        if not es_registro(ruta):
            _imprimir(ruta, ["No es un libro de registro de entregas (no tiene hoja ENTREGAS). "
                             "Para una rejilla antigua usa 'reparar'; para convertirla, 'migrar'."])
            return 1
        res = reparar(ruta)
        if res['ok'] and not res['acciones']:
            # Contenido al dia, pero el LEEME y las listas de ayuda de ENTREGAS pueden ser
            # de una version anterior (el libro se creo antes): se refrescan siempre.
            entregas_materiales.regenerar_hojas(ruta)
            print("Las hojas generadas ya estaban al dia con ENTREGAS; se han refrescado el LEEME "
                  "y las listas de ayuda.")
    else:
        res = reparar(ruta)
    if res['copia']:
        print(f"Copia de seguridad: {res['copia']}")
    for a in res['acciones']:
        print(f"  hecho: {a}")
    _imprimir(ruta, res['pendientes'])
    _aviso_incompletas(ruta)
    return 0 if res['ok'] else 1


if __name__ == "__main__":
    sys.exit(main())
