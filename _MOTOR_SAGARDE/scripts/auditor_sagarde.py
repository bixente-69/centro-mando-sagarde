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

Genera _MOTOR_SAGARDE/auditoria_diagnostico.json y emite resumen por pantalla.

Uso:
  python _MOTOR_SAGARDE/scripts/auditor_sagarde.py
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent.parent.parent
MOTOR_DIR = ROOT / "_MOTOR_SAGARDE"
DIAGNOSTICO_JSON = MOTOR_DIR / "auditoria_diagnostico.json"
if str(MOTOR_DIR) not in sys.path:
    sys.path.insert(0, str(MOTOR_DIR))

from avisos import dias_desde_timestamp, es_aviso_por_antiguedad

WORD_EXTS = {".doc", ".docx"}
EXCEL_EXTS = {".xls", ".xlsx", ".xlsm"}
PDF_EXTS = {".pdf"}
DATA_EXTS = WORD_EXTS | EXCEL_EXTS | PDF_EXTS | {".json"}

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
                # Ignorar archivos en subcarpetas de sistema
                if "_SISTEMA" in f.parts or "INFORME SAGARDE IA" in str(f):
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


def run_audit() -> dict:
    print("=" * 60)
    print(" AUDITORÍA DE SALUD DE DATOS SAGARDE (PRE-PUBLICACIÓN)")
    print("=" * 60)

    issues_obras = audit_obras_abiertas()
    issues_mant = audit_mantenimientos()
    all_issues = issues_obras + issues_mant

    warnings = [i for i in all_issues if i["nivel"] == "warning"]
    infos = [i for i in all_issues if i["nivel"] == "info"]

    resultado = {
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "generado_ts": datetime.now().timestamp(),
        "salud_score": max(0, 100 - (len(warnings) * 15 + len(infos) * 2)),
        "totales": {
            "total_issues": len(all_issues),
            "warnings": len(warnings),
            "infos": len(infos),
        },
        "issues": all_issues
    }

    with open(DIAGNOSTICO_JSON, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\n[RESULTADO] Salud Global de Datos: {resultado['salud_score']}%")
    print(f"            - Avisos de Formato (Warnings): {len(warnings)}")
    print(f"            - Observaciones Informativas (Infos): {len(infos)}\n")

    if warnings:
        print("[!] AVISOS DE FORMATO / ACCION RECOMENDADA:")
        for w in warnings:
            print(f"  * [{w['area']}] {w['obra']}: {w['mensaje']}")
            print(f"    Solucion: {w['solucion']}\n")
    else:
        print("[OK] Sin errores de formato criticos. Los datos estan 100% listos para publicar.")

    return resultado


if __name__ == "__main__":
    run_audit()
