from __future__ import annotations

import os
import shutil
import sys
from copy import copy
from datetime import datetime

import openpyxl

ROOT = r"D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE"
SYSTEM_DIR = os.path.join(ROOT, "SAGARDE OBRAS ABIERTAS", "_SISTEMA INFORME SAGARDE IA")
sys.path.insert(0, SYSTEM_DIR)
import entregas_materiales  # noqa: E402

SOURCE = os.path.join(
    ROOT, "SAGARDE OBRAS ABIERTAS", "2026 BARAKALDO 104V OBRAS ESPECIALES",
    "REVISIONES", "hoja de entrega de materiales BARAKALDO.xlsx")
OUTPUT_DIR = os.path.join(ROOT, "outputs", "barakaldo_regleta_10mm_20261112")
OUTPUT = os.path.join(OUTPUT_DIR, "hoja de entrega de materiales BARAKALDO.xlsx")
os.makedirs(OUTPUT_DIR, exist_ok=True)
shutil.copy2(SOURCE, OUTPUT)

wb = openpyxl.load_workbook(OUTPUT)
ws = wb["ENTREGAS"]
exists = any(
    str(ws.cell(row, 5).value or "").strip().upper() == "REGLETA BLANCA PP"
    and str(ws.cell(row, 6).value or "").upper().replace(" ", "") in {"10MM²", "10MM2"}
    for row in range(2, ws.max_row + 1)
)

if exists:
    print("La regleta blanca PP de 10 mm² ya estaba registrada; no se duplica.")
else:
    source_row = ws.max_row
    new_row = source_row + 1
    for col in range(1, 11):
        source_cell = ws.cell(source_row, col)
        target_cell = ws.cell(new_row, col)
        if source_cell.has_style:
            target_cell._style = copy(source_cell._style)
    values = [
        datetime(2026, 11, 12), "Sagarde", None, "CONEXIÓN",
        "REGLETA BLANCA PP", "10 MM²", "WURTH", "PAQ. 10", 1,
        "1 paquete (10 unidades)",
    ]
    for col, value in enumerate(values, start=1):
        ws.cell(new_row, col, value)
    ws.cell(new_row, 1).number_format = "DD/MM/YYYY"
    ws.row_dimensions[new_row].height = ws.row_dimensions[source_row].height
    ws.auto_filter.ref = f"A1:J{new_row}"
    temp = OUTPUT + ".editando.tmp"
    wb.save(temp)
    os.replace(temp, OUTPUT)
    print(f"Añadida ENTREGAS fila {new_row}: REGLETA BLANCA PP 10 MM².")

warnings = entregas_materiales.regenerar_hojas(OUTPUT)
print(f"OUTPUT={OUTPUT}")
print(f"AVISOS={warnings}")
