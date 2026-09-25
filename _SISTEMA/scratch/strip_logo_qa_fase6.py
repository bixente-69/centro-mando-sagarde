# -*- coding: utf-8 -*-
"""Copia de generador_revisiones.html sin el logo base64, solo para poder
cargarlo en el navegador integrado (limite de tamano). Uso exclusivo de QA
de la Fase 6; no es un fichero de produccion."""
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(
    os.path.dirname(os.path.dirname(AQUI)),
    'SAGARDE OBRAS ABIERTAS', '_SISTEMA INFORME SAGARDE IA',
    'generador_revisiones.html',
)
DST = os.path.join(AQUI, 'generador_revisiones_QA_fase6.html')

PLACEHOLDER_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUB"
    "AScY42YAAAAASUVORK5CYII="
)

with open(SRC, encoding='utf-8') as f:
    lines = f.readlines()

huge = [i for i, linea in enumerate(lines) if len(linea) > 5000]
print('lineas enormes encontradas:', huge)

for i in huge:
    linea = lines[i]
    marca = 'base64,'
    inicio = linea.find(marca)
    if inicio == -1:
        raise SystemExit(f'linea {i}: no se encontro "{marca}" en una linea enorme')
    fin_datos = inicio + len(marca)
    apertura = linea.rfind('data:', 0, inicio)
    comilla = linea[apertura - 1] if apertura > 0 else '"'
    cierre = linea.find(comilla, fin_datos)
    if cierre == -1:
        raise SystemExit(f'linea {i}: no se encontro la comilla de cierre ({comilla!r})')
    lines[i] = linea[:fin_datos] + PLACEHOLDER_B64 + linea[cierre:]

with open(DST, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('escrito:', DST, 'tamano:', os.path.getsize(DST))
