#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auditor_sagarde.py — Módulo de Auditoría de Salud de Datos y Pre-Publicación SAGARDE

Analiza la salud del repositorio de datos (Obras Abiertas, Post-Ventas y Mantenimientos)
para detectar proactivamente:
  - Ficheros de revisión Word/Excel sin fecha válida DD/MM/AAAA en el nombre
  - Fechas duplicadas de revisión en la misma obra
  - Obras abiertas sin revisión reciente (31-399 días)
  - Documentos o planos enlazados rotos / faltantes
  - Anomalías en contratos de mantenimiento o post-ventas
  - Datos de «Personal en obra»: esquema, DNI/teléfono/correo, ficheros declarados y
    doble cálculo (Python contra personal_calculo.js con node)

Genera _SISTEMA/MOTOR/auditoria_diagnostico.json y emite resumen por pantalla.

Uso:
  python _SISTEMA/MOTOR/scripts/auditor_sagarde.py

Código de salida: 0 si no hay errores; 3 si hay incidencias de nivel «error» (por ahora
solo las de Personal). Actualizar_Sagarde.bat para ahí y NO publica. Los avisos
(«warning») y las observaciones («info») nunca frenan nada.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import sys

# _SISTEMA/MOTOR/scripts/auditor_sagarde.py -> cuatro niveles hasta la raiz.
ROOT = Path(__file__).resolve().parent.parent.parent.parent
MOTOR_DIR = ROOT / "_SISTEMA" / "MOTOR"
DIAGNOSTICO_JSON = MOTOR_DIR / "auditoria_diagnostico.json"

# Carpetas tecnicas reconocidas en todo el entorno.
CARPETAS_SISTEMA = {"_SISTEMA", "_SISTEMA INFORME SAGARDE IA",
                    "INFORME SAGARDE IA"}
if str(MOTOR_DIR) not in sys.path:
    sys.path.insert(0, str(MOTOR_DIR))

from avisos import (contrato_sin_aviso, dias_desde_timestamp, es_aviso_por_antiguedad,
                    CODIGO_HOJAS_SIN_APLICAR, CODIGO_CONTROLES_SIN_APLICAR,
                    CODIGO_PENDIENTES_NO_COMPROBADO, CODIGOS_PENDIENTES)

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import materiales_xlsx

WORD_EXTS = {".doc", ".docx"}
EXCEL_EXTS = {".xls", ".xlsx", ".xlsm"}
PDF_EXTS = {".pdf"}
DATA_EXTS = WORD_EXTS | EXCEL_EXTS | PDF_EXTS | {".json"}

# Carpetas de una obra cuyo contenido NO son hojas de revision aunque el nombre
# del fichero lleve "Parte" o "Revision": los planos del proyecto (p. ej.
# "P.06 PLANOS INSTALACIONES_rev01_Parte3.pdf") y los informes tecnicos de
# visitas o reuniones. Sin esto salian como "fecha invalida" (22/10/2026).
# Se compara por nombre de carpeta, en mayusculas.
CARPETAS_NO_REVISION = {"DOCUMENTACION INICIAL",
                        "INFORMES TECNICOS DE VISITAS O REUNIONES"}

# Patrón estándar para detectar fechas DDMMYYYY o DD_MM_YYYY en nombres de archivo
DATE_PATTERN = re.compile(r"(\d{2})[-_/\.]?(\d{2})[-_/\.]?(\d{4})")


def audit_obras_abiertas() -> list[dict]:
    issues = []
    base = ROOT / "SAGARDE OBRAS ABIERTAS"
    if not base.is_dir():
        return issues

    obras_dirs = [p for p in base.iterdir() if p.is_dir() and not p.name.startswith("_")]

    for obra_dir in obras_dirs:
        nombre_obra = obra_dir.name
        rev_files = []
        for f in obra_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in DATA_EXTS and not f.name.startswith("~$"):
                # Carpetas tecnicas: la norma "_SISTEMA" (07/08/2026) y sus
                # dos alias historicos. Hasta hoy la primera condicion no
                # casaba con nada: '_SISTEMA' in f.parts es igualdad exacta
                # y la carpeta se llama '_SISTEMA INFORME SAGARDE IA'.
                # Funcionaba solo por la segunda.
                if CARPETAS_SISTEMA & set(f.parts):
                    continue
                carpetas = {p.upper() for p in f.relative_to(obra_dir).parts[:-1]}
                if CARPETAS_NO_REVISION & carpetas:
                    continue
                if "REVISION" in f.name.upper() or "PARTE" in f.name.upper():
                    rev_files.append(f)

        # 1. Chequeo de fechas válidas en nombres de archivos de revisión
        fechas_encontradas = {}
        for rf in rev_files:
            match = DATE_PATTERN.search(rf.name)
            if not match:
                issues.append({
                    "nivel": "warning",
                    "area": "Obras Abiertas",
                    "obra": nombre_obra,
                    "codigo": "NOMBRE_FECHA_INVALIDA",
                    "mensaje": f"Archivo de revisión '{rf.name}' no contiene una fecha DD/MM/AAAA válida en el nombre.",
                    "archivo": str(rf.relative_to(ROOT)),
                    "solucion": "Renombrar el archivo incluyendo la fecha de inspección (ej. REVISION 25072026.docx)"
                })
            else:
                day, month, year = match.groups()
                fecha_str = f"{day}/{month}/{year}"
                try:
                    dt = datetime(int(year), int(month), int(day))
                    if dt.year < 2020 or dt.year > 2030:
                        issues.append({
                            "nivel": "warning",
                            "area": "Obras Abiertas",
                            "obra": nombre_obra,
                            "codigo": "FECHA_FUERA_DE_RANGO",
                            "mensaje": f"Archivo '{rf.name}' tiene un año de revisión inusual: {dt.year}.",
                            "archivo": str(rf.relative_to(ROOT)),
                            "solucion": "Verificar la fecha en el nombre del fichero."
                        })
                    else:
                        if fecha_str in fechas_encontradas:
                            fechas_encontradas[fecha_str].append(rf.name)
                        else:
                            fechas_encontradas[fecha_str] = [rf.name]
                except ValueError:
                    issues.append({
                        "nivel": "warning",
                        "area": "Obras Abiertas",
                        "obra": nombre_obra,
                        "codigo": "FECHA_CALENDARIO_INVALIDA",
                        "mensaje": f"Archivo '{rf.name}' tiene números de fecha no válidos ({day}/{month}/{year}).",
                        "archivo": str(rf.relative_to(ROOT)),
                        "solucion": "Corregir el día o mes en el nombre del archivo."
                    })

        # 2. Chequeo de duplicados en la misma fecha
        for fecha_str, files in fechas_encontradas.items():
            if len(files) > 1:
                issues.append({
                    "nivel": "info",
                    "area": "Obras Abiertas",
                    "obra": nombre_obra,
                    "codigo": "REVISIONES_DUPLICADAS",
                    "mensaje": f"Existen {len(files)} revisiones para la misma fecha ({fecha_str}): {', '.join(files)}.",
                    "archivo": str(obra_dir.relative_to(ROOT)),
                    "solucion": "El motor seleccionará automáticamente el archivo con modificación más reciente."
                })

        # 3. Inactividad en obra abierta: aviso desde 31 hasta 399 días.
        if rev_files:
            latest_mtime = max(rf.stat().st_mtime for rf in rev_files)
            dias_sin_rev = dias_desde_timestamp(latest_mtime)
            if es_aviso_por_antiguedad(dias_sin_rev, desde_dias=30):
                issues.append({
                    "nivel": "info",
                    "area": "Obras Abiertas",
                    "obra": nombre_obra,
                    "codigo": "OBRA_SIN_REVISION_RECIENTE",
                    "dias_antiguedad": dias_sin_rev,
                    "mensaje": f"La obra no registra nuevos partes de revisión desde hace {dias_sin_rev} días.",
                    "archivo": str(obra_dir.relative_to(ROOT)),
                    "solucion": "Añadir la última hoja de revisión actualizada al visitar la obra."
                })

    return issues


def audit_pendientes_revisiones(raiz=None, obras=None) -> list[dict]:
    """Hojas y controles horarios que esperan sin aplicar en `<obra>/REVISIONES`.

    Es el eslabon manual donde mas se pierde: lo que se deja en la carpeta y nadie
    aplica no da error en ningun sitio (decision 4 de Bixente, 04/11/2026). No se
    inventa ninguna regla: se reutilizan las que ya decide «actualiza la obra»:
    - hojas: `actualizar_obra.detectar_hojas` (fecha + huella SHA256, vivienda y garaje);
    - controles horarios: `cerrar_obra.controles_sin_aplicar` (huella SHA256 contra la traza).
    Si una obra no se puede comprobar se AVISA (PENDIENTES_NO_COMPROBADO): un cero por
    haber fallado la comprobacion seria el fallo de siempre.
    """
    raiz = Path(raiz or ROOT)
    motor = raiz / "SAGARDE OBRAS ABIERTAS" / "_SISTEMA INFORME SAGARDE IA"
    try:
        if str(motor) not in sys.path:
            sys.path.insert(0, str(motor))
        import actualizar_obra
        import cerrar_obra
        if obras is None:
            import registro_obras
            obras = registro_obras.OBRAS
    except Exception as exc:  # que la comprobacion no arranque se dice, no se calla
        return [_issue_no_comprobado("(todas)", f"no se pudo cargar el codigo: {type(exc).__name__}: {exc}")]

    issues = []
    for obra in obras:
        carpeta = raiz / "SAGARDE OBRAS ABIERTAS" / obra["carpeta_obra"]
        if not (carpeta / "REVISIONES").is_dir():
            continue
        try:
            def leer(nombre):
                ruta = carpeta / "INFORME SAGARDE IA" / nombre
                if not ruta.is_file():
                    return None
                return json.loads(ruta.read_text(encoding="utf-8"))
            det = actualizar_obra.detectar_hojas(
                carpeta / "REVISIONES", leer("ficha_obra.json"), leer("ficha_garajes.json"))
            hojas = [h.ruta.name for h in det.vivienda + det.garaje]
            ctl = cerrar_obra.controles_sin_aplicar(raiz, obra)
        except Exception as exc:  # noqa: BLE001
            issues.append(_issue_no_comprobado(obra["nombre"], f"{type(exc).__name__}: {exc}"))
            continue
        if ctl.get("error"):
            issues.append(_issue_no_comprobado(obra["nombre"], f"controles horarios: {ctl['error']}"))
        controles = [p["nombre"] for p in ctl.get("pendientes", [])]
        if hojas:
            issues.append({
                "nivel": "warning", "area": "Obras Abiertas", "obra": obra["nombre"],
                "codigo": CODIGO_HOJAS_SIN_APLICAR, "n": len(hojas), "ficheros": hojas,
                "mensaje": f"{len(hojas)} hoja(s) de revision en REVISIONES sin aplicar: {', '.join(hojas)}.",
                "archivo": str(carpeta.relative_to(raiz) / "REVISIONES"),
                "solucion": f"Decir «actualiza la obra {obra['id']}», o sacar de la carpeta las hojas que no valgan.",
            })
        if controles:
            issues.append({
                "nivel": "warning", "area": "Obras Abiertas", "obra": obra["nombre"],
                "codigo": CODIGO_CONTROLES_SIN_APLICAR, "n": len(controles), "ficheros": controles,
                "mensaje": f"{len(controles)} control(es) horario(s) en REVISIONES sin aplicar: {', '.join(controles)}.",
                "archivo": str(carpeta.relative_to(raiz) / "REVISIONES"),
                "solucion": f"Decir «actualiza la obra {obra['id']}», o sacar de la carpeta los que no valgan.",
            })
    return issues


def _issue_no_comprobado(obra: str, motivo: str) -> dict:
    return {
        "nivel": "warning", "area": "Obras Abiertas", "obra": obra,
        "codigo": CODIGO_PENDIENTES_NO_COMPROBADO,
        "mensaje": f"No se pudo comprobar si hay hojas o controles sin aplicar: {motivo}",
        "solucion": "Mirar a mano la carpeta REVISIONES de la obra y avisar si el fallo se repite.",
    }


def audit_materiales() -> list[dict]:
    """Hojas de entrega de materiales que el panel no podra leer.

    Un Excel danado (o guardado sin recalcular) no da error en ningun sitio
    visible: el panel de la obra sale sin materiales, o la obra desaparece del
    portal movil (Olabeaga, 20/10/2026, tras editar agy el XML a mano)."""
    try:
        fallos = materiales_xlsx.diagnosticar_todas()
    except Exception as exc:  # que la comprobacion falle se dice, no se calla
        return [{
            "nivel": "warning",
            "area": "Materiales",
            "obra": "(todas)",
            "codigo": "MATERIALES_XLSX_NO_COMPROBADO",
            "mensaje": f"No se pudo comprobar las hojas de materiales: {type(exc).__name__}: {exc}",
            "solucion": "Ejecutar: py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py comprobar --todas",
        }]
    return [{
        "nivel": "warning",
        "area": "Materiales",
        "obra": obra,
        "codigo": "MATERIALES_XLSX",
        "mensaje": "La hoja de entrega de materiales no se podra leer bien: " + "; ".join(defectos),
        "solucion": "Ejecutar: py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py reparar <obra>",
    } for obra, defectos in fallos.items()]


def audit_personal() -> list[dict]:
    """Datos de «Personal en obra» antes de publicar (esquema, datos privados, ficheros
    declarados, doble cálculo). Sin ningún personal_obra.json no hace nada.

    Es la única auditoría con nivel «error»: esos ficheros se publican tal cual y un
    esquema roto o un total que no cuadra acabaría en el ranking sin aviso."""
    base = ROOT / "SAGARDE OBRAS ABIERTAS"
    motor = base / "_SISTEMA INFORME SAGARDE IA"
    if not motor.is_dir():
        return []
    if str(motor) not in sys.path:
        sys.path.insert(0, str(motor))
    try:
        import personal_integracion
        return personal_integracion.auditar(base)
    except ImportError as exc:
        hay_datos = any(base.glob("*/INFORME SAGARDE IA/personal_obra.json")) or any(
            (ROOT / "SAGARDE (OLD)" / "OBRAS CERRADAS").glob("*/INFORME SAGARDE IA/personal_obra.json"))
        if not hay_datos:
            return []
        return [{
            "nivel": "error",
            "area": "Personal",
            "obra": "(personal)",
            "codigo": "PERSONAL_FICHERO_FALTA",
            "mensaje": f"Hay datos de personal pero no se puede cargar su código: {exc}",
            "solucion": "Restaurar los ficheros de personal desde git.",
        }]
    except Exception as exc:  # que la comprobacion falle se dice, no se calla
        return [{
            "nivel": "warning",
            "area": "Personal",
            "obra": "(personal)",
            "codigo": "PERSONAL_NO_COMPROBADO",
            "mensaje": f"No se pudo comprobar los datos de personal: {type(exc).__name__}: {exc}",
            "solucion": "Ejecutar: py -3.11 \"SAGARDE OBRAS ABIERTAS\\_SISTEMA INFORME SAGARDE IA\\personal_integracion.py\" auditar",
        }]


def audit_mantenimientos() -> list[dict]:
    issues = []
    base = ROOT / "MANTENIMIENTOS"
    if not base.is_dir():
        return issues

    contratos = [p for p in base.iterdir() if p.is_dir() and not p.name.startswith("_")]
    for c in contratos:
        files = [f for f in c.rglob("*") if f.is_file() and f.name.lower() != "index.html" and not f.name.startswith("~$")]
        if not files:
            issues.append({
                "nivel": "warning",
                "area": "Mantenimientos",
                "obra": c.name,
                "codigo": "CONTRATO_VACIO",
                "mensaje": f"El contrato de mantenimiento '{c.name}' está completamente vacío.",
                "archivo": str(c.relative_to(ROOT)),
                "solucion": "Añadir partes o documentación de mantenimiento."
            })
            continue

        latest_mtime = max(f.stat().st_mtime for f in files)
        dias_inactivo = dias_desde_timestamp(latest_mtime)
        if contrato_sin_aviso(c.name.replace("MANTENIMIENTO ", "").strip()):
            continue  # declarado sin aviso en avisos.py (p. ej. rescindido)
        if es_aviso_por_antiguedad(dias_inactivo, desde_dias=90):
            issues.append({
                "nivel": "warning",
                "area": "Mantenimientos",
                "obra": c.name.replace("MANTENIMIENTO ", "").strip(),
                "codigo": "MANTENIMIENTO_DESACTUALIZADO",
                "dias_antiguedad": dias_inactivo,
                "mensaje": f"Contrato sin partes o visitas registradas en {dias_inactivo} días.",
                "archivo": str(c.relative_to(ROOT)),
                "solucion": "Realizar la inspección periódica y registrar la hoja de mantenimiento."
            })

    return issues


def _totales_y_nota(issues: list[dict]) -> tuple[dict, int]:
    """Totales por nivel y nota de salud: una sola fórmula para la auditoría completa y para el refresco de pendientes."""
    errores = sum(1 for i in issues if i["nivel"] == "error")
    avisos = sum(1 for i in issues if i["nivel"] == "warning")
    infos = sum(1 for i in issues if i["nivel"] == "info")
    totales = {"total_issues": len(issues), "errors": errores, "warnings": avisos, "infos": infos}
    return totales, max(0, 100 - (errores * 30 + avisos * 15 + infos * 2))


def refrescar_pendientes(ruta=None) -> dict | None:
    """Vuelve a mirar lo que espera sin aplicar en REVISIONES y lo deja en el diagnóstico.

    Defecto del 05/11/2026 (reparado el 06/11/2026): el paso 0 del .bat calculaba los pendientes, el paso 1
    aplicaba los controles limpios y el portal (paso 3) pintaba el aviso con lo calculado ANTES, así que un control
    que el propio .bat acababa de aplicar seguía saliendo como «sin aplicar» hasta la pasada siguiente. Este refresco
    se llama entre aplicar y pintar y reescribe SOLO los avisos de pendientes (los demás, los totales por nivel y la
    nota se conservan o se recalculan con la misma fórmula; la hora de la auditoría no se toca).
    Si no hay diagnóstico no se inventa ninguno (devuelve None); uno ilegible lanza ValueError; si la comprobación
    falla se AVISA (PENDIENTES_NO_COMPROBADO): un cero por haber fallado sería el fallo de siempre."""
    ruta = Path(ruta or DIAGNOSTICO_JSON)
    if not ruta.is_file():
        return None
    diagnostico = json.loads(ruta.read_text(encoding="utf-8"))
    try:
        nuevos = audit_pendientes_revisiones()
    except Exception as exc:  # noqa: BLE001 — se dice, no se calla
        nuevos = [_issue_no_comprobado("(todas)", f"{type(exc).__name__}: {exc}")]
    resto = [i for i in diagnostico.get("issues", []) if i.get("codigo") not in CODIGOS_PENDIENTES]
    diagnostico["issues"] = resto + nuevos
    diagnostico["totales"], diagnostico["salud_score"] = _totales_y_nota(diagnostico["issues"])
    diagnostico["pendientes_refrescados"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    ruta.write_text(json.dumps(diagnostico, ensure_ascii=False, indent=2), encoding="utf-8")
    return diagnostico


def run_audit() -> dict:
    print("=" * 60)
    print(" AUDITORÍA DE SALUD DE DATOS SAGARDE (PRE-PUBLICACIÓN)")
    print("=" * 60)

    issues_obras = audit_obras_abiertas()
    issues_mant = audit_mantenimientos()
    issues_mat = audit_materiales()
    issues_personal = audit_personal()
    issues_pendientes = audit_pendientes_revisiones()
    all_issues = issues_obras + issues_mant + issues_mat + issues_personal + issues_pendientes

    errors = [i for i in all_issues if i["nivel"] == "error"]
    warnings = [i for i in all_issues if i["nivel"] == "warning"]
    infos = [i for i in all_issues if i["nivel"] == "info"]
    totales, salud_score = _totales_y_nota(all_issues)

    resultado = {
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "generado_ts": datetime.now().timestamp(),
        "salud_score": salud_score,
        "totales": totales,
        "issues": all_issues
    }

    with open(DIAGNOSTICO_JSON, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\n[RESULTADO] Salud Global de Datos: {resultado['salud_score']}%")
    print(f"            - Errores que frenan la publicación: {len(errors)}")
    print(f"            - Avisos de Formato (Warnings): {len(warnings)}")
    print(f"            - Observaciones Informativas (Infos): {len(infos)}\n")

    if errors:
        print("[X] ERRORES: NO SE PUBLICA hasta corregirlos:")
        for e in errors:
            print(f"  * [{e['area']}] {e['mensaje']}")
            print(f"    Solucion: {e['solucion']}\n")
    if warnings:
        print("[!] AVISOS DE FORMATO / ACCION RECOMENDADA:")
        for w in warnings:
            print(f"  * [{w['area']}] {w['obra']}: {w['mensaje']}")
            print(f"    Solucion: {w['solucion']}\n")
    elif not errors:
        print("[OK] Sin errores de formato criticos. Los datos estan 100% listos para publicar.")

    return resultado


def main(argv=None) -> int:
    """Código de salida para Actualizar_Sagarde.bat: 3 si hay errores que frenan la publicación.

    Con `--solo-pendientes` (paso entre aplicar y pintar el portal) solo vuelve a mirar lo que queda sin aplicar:
    sale con 0 aunque el diagnóstico tenga errores (el que frena la publicación es el paso 0) y con 1 si no pudo."""
    argumentos = sys.argv[1:] if argv is None else list(argv)
    if "--solo-pendientes" in argumentos:
        try:
            diagnostico = refrescar_pendientes()
        except Exception as exc:  # noqa: BLE001
            print(f"[AVISO] No se pudo volver a mirar lo que queda sin aplicar: {type(exc).__name__}: {exc}")
            return 1
        if diagnostico is None:
            print("[AVISO] No hay diagnostico de la auditoria: no hay nada que refrescar.")
            return 0
        pendientes = [i for i in diagnostico["issues"] if i.get("codigo") in (CODIGO_HOJAS_SIN_APLICAR, CODIGO_CONTROLES_SIN_APLICAR)]
        print(f"[OK] Vuelto a mirar REVISIONES tras aplicar: {sum(int(i.get('n') or 0) for i in pendientes)} fichero(s) sin aplicar "
              f"en {len({i.get('obra') for i in pendientes})} obra(s).")
        return 0
    return 3 if run_audit()["totales"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
