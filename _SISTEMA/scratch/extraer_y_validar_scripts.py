# -*- coding: utf-8 -*-
"""Extrae cada bloque <script> (sin src=) de generador_revisiones.html y lo
valida con `node --check` de forma aislada, para localizar un error de
sintaxis real sin depender de como lo cargue el navegador."""
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(
    os.path.dirname(os.path.dirname(AQUI)),
    'SAGARDE OBRAS ABIERTAS', '_SISTEMA INFORME SAGARDE IA',
    'generador_revisiones.html',
)

with open(SRC, encoding='utf-8') as f:
    contenido = f.read()

patron = re.compile(r'<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>', re.S | re.I)

bloques = []
for i, m in enumerate(patron.finditer(contenido)):
    attrs = m.group('attrs')
    if 'src=' in attrs:
        continue
    body = m.group('body')
    inicio_linea = contenido.count('\n', 0, m.start()) + 1
    bloques.append((i, inicio_linea, body))

print(f'Bloques <script> sin src encontrados: {len(bloques)}')

tmp_dir = AQUI
for i, inicio_linea, body in bloques:
    ruta_tmp = os.path.join(tmp_dir, f'_bloque_{i}.js')
    with open(ruta_tmp, 'w', encoding='utf-8') as f:
        f.write(body)
    resultado = subprocess.run(
        ['node', '--check', ruta_tmp],
        capture_output=True, text=True,
    )
    estado = 'OK' if resultado.returncode == 0 else 'ERROR'
    print(f'Bloque {i} (empieza en linea real ~{inicio_linea}, '
          f'{len(body)} caracteres): {estado}')
    if resultado.returncode != 0:
        print(resultado.stderr[:2000])
    os.remove(ruta_tmp)
