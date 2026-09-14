# Indexador de PROYECTO ELECTRICO — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the local Python indexer that reads every PDF in `PROYECTO ELECTRICO`, chunks the text, generates an embedding per chunk via the NVIDIA API, and writes a resumable local index — the artifact Fase 2 (Cloudflare Worker + pestaña) will need, and whose real size decides R2 vs KV.

**Architecture:** Three small modules — PDF extraction/chunking, an NVIDIA embeddings client, and a CLI orchestrator that walks the library and writes a JSONL index — living entirely under `PROYECTO ELECTRICO/_INDEXADOR/`, **outside the Sagarde git repo**, so the index and the books can never be swept into `Actualizar_Sagarde.bat`'s `git add -A`. This is Fase 1 of `_SISTEMA/docs/superpowers/specs/2026-09-14-buscador-electrico-design.md`; it stops before touching Cloudflare or the Sagarde repo.

**Tech Stack:** Python 3, `pdfplumber` (already installed, confirmed `0.11.9`), stdlib `urllib` for the NVIDIA API (same zero-dependency pattern as `nvidia_chat.py`), `unittest` for tests.

## Global Constraints

- El contenido de los libros y el índice de embeddings **nunca** deben poder acabar en el repositorio público de Sagarde. Por eso todo el código y los datos de este plan viven en `PROYECTO ELECTRICO/_INDEXADOR/`, fuera de `COPIA SEGURIDAD SAGARDE`.
- Extracción de texto de PDF: usar `pagina.chars` char a char, nunca `extract_text()` — es el truco ya validado en el patrón Quiz App para evitar errores de encoding con caracteres especiales.
- Sin pytest ni dependencias nuevas más allá de `pdfplumber` (ya instalada). Pruebas con `unittest` de la biblioteca estándar, siguiendo la convención del resto de Sagarde.
- Clave `NVIDIA_API_KEY` ya configurada como variable de entorno de usuario en Windows — reutilizar el mismo patrón de lectura (con respaldo al registro) que `nvidia_chat.py`.
- Modelo de embeddings verificado el 14/09/2026 para esta cuenta: `nvidia/nemotron-3-embed-1b`, 2048 dimensiones. Verificado en esta misma sesión que acepta `input_type: "passage"` (para texto indexado) sin error — usar siempre ese parámetro explícito, nunca omitirlo, para que sea comparable con las preguntas (`input_type: "query"`) que generará el Worker en Fase 2.
- Ningún fallo debe tumbar la indexación completa: un PDF que falla se reporta y se salta: el resto de la biblioteca se indexa igual (mismo principio que "un except no debe tumbar la generación del panel" en Sagarde).
- No tocar nada dentro de `COPIA SEGURIDAD SAGARDE` en este plan salvo este propio documento. Ningún `git commit`/publicación sin confirmarlo antes con Bixente explícitamente (regla explícita de la spec, sección K).

---

### Task 1: Extracción de texto y troceado en fragmentos

**Files:**
- Create: `PROYECTO ELECTRICO/_INDEXADOR/extraer_pdf.py`
- Create: `PROYECTO ELECTRICO/_INDEXADOR/requirements.txt`
- Test: `PROYECTO ELECTRICO/_INDEXADOR/tests/test_extraer_pdf.py`

**Interfaces:**
- Consumes: nada (es la base del pipeline)
- Produces:
  - `extraer_texto_por_pagina(ruta_pdf: str) -> list[dict]` — cada dict `{'pagina': int, 'texto': str}`
  - `trocear_texto(paginas: list[dict], tamano_chunk: int = 1500, solape: int = 200) -> list[dict]` — cada dict `{'texto': str, 'paginas': list[int]}`

- [ ] **Step 1: Crear la carpeta del indexador y `requirements.txt`**

```bash
mkdir -p "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR/tests"
```

Contenido de `PROYECTO ELECTRICO/_INDEXADOR/requirements.txt`:
```
pdfplumber
```

Contenido de `PROYECTO ELECTRICO/_INDEXADOR/.gitignore` (red de seguridad: esta carpeta no debería estar nunca en un repo git, pero por si acaso alguna vez lo estuviera, que el índice nunca se trackee):
```
indice_biblioteca.jsonl
*.jsonl.tmp
__pycache__/
```

- [ ] **Step 2: Escribir el test de extracción (debe fallar: el módulo no existe todavía)**

```python
# PROYECTO ELECTRICO/_INDEXADOR/tests/test_extraer_pdf.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extraer_pdf import extraer_texto_por_pagina, trocear_texto

RUTA_PDF_PRUEBA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "05_PUESTA A TIERRA", "00337-VIA CHISPAS.pdf",
)


class TestExtraerTextoPorPagina(unittest.TestCase):
    def test_extrae_texto_no_vacio_de_pdf_real(self):
        paginas = extraer_texto_por_pagina(RUTA_PDF_PRUEBA)
        self.assertGreater(len(paginas), 0)
        self.assertIn('pagina', paginas[0])
        self.assertIn('texto', paginas[0])
        self.assertTrue(paginas[0]['texto'].strip())

    def test_numeros_de_pagina_son_positivos(self):
        paginas = extraer_texto_por_pagina(RUTA_PDF_PRUEBA)
        for p in paginas:
            self.assertGreaterEqual(p['pagina'], 1)


class TestTrocearTexto(unittest.TestCase):
    def test_trocea_respetando_tamano_maximo(self):
        paginas = [{'pagina': 1, 'texto': 'x' * 4000}]
        fragmentos = trocear_texto(paginas, tamano_chunk=1500, solape=200)
        self.assertGreater(len(fragmentos), 1)
        for f in fragmentos:
            self.assertLessEqual(len(f['texto']), 1500)

    def test_fragmentos_consecutivos_se_solapan(self):
        texto = 'abcdefghij' * 200  # 2000 caracteres
        paginas = [{'pagina': 1, 'texto': texto}]
        fragmentos = trocear_texto(paginas, tamano_chunk=1500, solape=200)
        self.assertEqual(fragmentos[0]['texto'][-200:], fragmentos[1]['texto'][:200])

    def test_conserva_que_paginas_cubre_cada_fragmento(self):
        paginas = [
            {'pagina': 1, 'texto': 'A' * 1000},
            {'pagina': 2, 'texto': 'B' * 1000},
        ]
        fragmentos = trocear_texto(paginas, tamano_chunk=1500, solape=200)
        self.assertIn(1, fragmentos[0]['paginas'])

    def test_paginas_vacias_no_generan_fragmentos(self):
        self.assertEqual(trocear_texto([]), [])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Ejecutar el test y comprobar que falla**

Run: `cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python -m unittest tests.test_extraer_pdf -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'extraer_pdf'`

- [ ] **Step 4: Implementar `extraer_pdf.py`**

```python
"""Extrae texto de PDFs de la biblioteca y lo trocea en fragmentos para indexar.

Usa pagina.chars (no extract_text()) para evitar errores de encoding con
caracteres especiales - mismo truco ya validado en el patron Quiz App.
"""
import pdfplumber


def extraer_texto_por_pagina(ruta_pdf):
    paginas = []
    with pdfplumber.open(ruta_pdf) as pdf:
        for indice, pagina in enumerate(pdf.pages):
            chars = pagina.chars
            texto = ''.join(
                c.get('text', '') for c in chars
                if ord(c.get('text', 'x')) < 0x10000
            ).strip()
            if texto:
                paginas.append({'pagina': indice + 1, 'texto': texto})
    return paginas


def trocear_texto(paginas, tamano_chunk=1500, solape=200):
    if not paginas:
        return []

    texto_partes = [p['texto'] for p in paginas]
    texto_unido = '\n'.join(texto_partes)

    mapa_paginas = []  # (inicio_caracter, fin_caracter, numero_pagina)
    cursor = 0
    for p in paginas:
        inicio = cursor
        fin = inicio + len(p['texto'])
        mapa_paginas.append((inicio, fin, p['pagina']))
        cursor = fin + 1  # +1 por el separador '\n'

    fragmentos = []
    inicio = 0
    while inicio < len(texto_unido):
        fin = min(inicio + tamano_chunk, len(texto_unido))
        trozo = texto_unido[inicio:fin].strip()
        if trozo:
            paginas_cubiertas = sorted({
                pag for (ini_p, fin_p, pag) in mapa_paginas
                if ini_p < fin and fin_p > inicio
            })
            fragmentos.append({'texto': trozo, 'paginas': paginas_cubiertas})
        if fin == len(texto_unido):
            break
        inicio = fin - solape
    return fragmentos
```

- [ ] **Step 5: Ejecutar el test y comprobar que pasa**

Run: `cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python -m unittest tests.test_extraer_pdf -v`
Expected: PASS (6 tests)

- [ ] **Step 6: Commit**

Este commit es **local a `PROYECTO ELECTRICO`, fuera del repo de Sagarde** — no afecta a `COPIA SEGURIDAD SAGARDE` ni requiere confirmación de Bixente (esa regla es solo para el repo público de Sagarde). Si `PROYECTO ELECTRICO` no es un repositorio git, omitir este paso: no hace falta crear uno solo para esto.

---

### Task 2: Cliente de embeddings de NVIDIA

**Files:**
- Create: `PROYECTO ELECTRICO/_INDEXADOR/embeddings_nvidia.py`
- Test: `PROYECTO ELECTRICO/_INDEXADOR/tests/test_embeddings_nvidia.py`

**Interfaces:**
- Consumes: nada de Task 1 directamente (módulo independiente)
- Produces: `generar_embeddings(textos: list[str], tipo: str = "passage", clave_api: str | None = None, intentos: int = 3) -> list[list[float]]` — un vector de 2048 floats por texto de entrada, mismo orden

- [ ] **Step 1: Escribir el test (debe fallar: el módulo no existe)**

```python
# PROYECTO ELECTRICO/_INDEXADOR/tests/test_embeddings_nvidia.py
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from embeddings_nvidia import generar_embeddings, obtener_clave_api


class TestGenerarEmbeddings(unittest.TestCase):
    def test_hay_clave_api_configurada(self):
        self.assertTrue(obtener_clave_api())

    def test_genera_un_vector_de_2048_dimensiones(self):
        vectores = generar_embeddings(["Un texto de prueba sobre instalaciones electricas"])
        self.assertEqual(len(vectores), 1)
        self.assertEqual(len(vectores[0]), 2048)

    def test_respeta_el_orden_de_entrada(self):
        vectores = generar_embeddings(["primer texto", "segundo texto bien distinto"])
        self.assertEqual(len(vectores), 2)
        self.assertNotEqual(vectores[0], vectores[1])

    def test_lista_vacia_no_llama_a_la_api(self):
        self.assertEqual(generar_embeddings([]), [])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

Run: `cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python -m unittest tests.test_embeddings_nvidia -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'embeddings_nvidia'`

- [ ] **Step 3: Implementar `embeddings_nvidia.py`**

```python
"""Cliente minimo para generar embeddings con la API de Build by NVIDIA.

Mismo patron de autenticacion que nvidia_chat.py: variable de entorno
NVIDIA_API_KEY, con respaldo al registro de Windows si la sesion actual
no la ha heredado todavia.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

BASE_URL = "https://integrate.api.nvidia.com/v1"
MODELO_EMBEDDINGS = "nvidia/nemotron-3-embed-1b"


def _leer_clave_del_registro_windows():
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            valor, _ = winreg.QueryValueEx(k, "NVIDIA_API_KEY")
            return valor or None
    except (ImportError, FileNotFoundError, OSError):
        return None


def obtener_clave_api():
    return os.environ.get("NVIDIA_API_KEY") or _leer_clave_del_registro_windows()


def generar_embeddings(textos, tipo="passage", clave_api=None, intentos=3):
    """tipo: 'passage' para texto que se indexa, 'query' para una pregunta
    de busqueda (el Worker de Fase 2 usara 'query')."""
    if not textos:
        return []

    clave_api = clave_api or obtener_clave_api()
    if not clave_api:
        sys.exit("ERROR: falta la variable de entorno NVIDIA_API_KEY.")

    body = {"input": textos, "model": MODELO_EMBEDDINGS, "input_type": tipo}
    data = json.dumps(body).encode("utf-8")

    ultimo_error = None
    for intento in range(1, intentos + 1):
        req = urllib.request.Request(f"{BASE_URL}/embeddings", data=data, method="POST")
        req.add_header("Authorization", f"Bearer {clave_api}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            payload = json.load(resp)
            return [item["embedding"] for item in payload["data"]]
        except urllib.error.HTTPError as e:
            ultimo_error = f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}"
        except (urllib.error.URLError, TimeoutError) as e:
            ultimo_error = str(e)
        if intento < intentos:
            time.sleep(2 * intento)
    sys.exit(f"ERROR generando embeddings tras {intentos} intentos: {ultimo_error}")
```

- [ ] **Step 4: Ejecutar el test y comprobar que pasa**

Run: `cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python -m unittest tests.test_embeddings_nvidia -v`
Expected: PASS (4 tests). Esto hace 2 llamadas reales a la API (coste mínimo, ya verificado que la cuenta tiene acceso).

- [ ] **Step 5: Commit**

Local a `PROYECTO ELECTRICO`, mismo criterio que Task 1 Step 6.

---

### Task 3: CLI orquestador de indexación

**Files:**
- Create: `PROYECTO ELECTRICO/_INDEXADOR/indexar_biblioteca.py`
- Test: `PROYECTO ELECTRICO/_INDEXADOR/tests/test_indexar_biblioteca.py`

**Interfaces:**
- Consumes: `extraer_texto_por_pagina`, `trocear_texto` (Task 1); `generar_embeddings` (Task 2)
- Produces:
  - `listar_pdfs_biblioteca(carpeta_biblioteca: str, carpeta_indexador: str) -> list[str]`
  - `ejecutar_indexacion(carpeta_biblioteca: str, carpeta_indexador: str, ruta_indice: str, forzar: bool = False) -> list[dict]` — cada dict del índice: `{id, libro, carpeta, ruta_relativa, paginas, texto, embedding}`
  - CLI: `python indexar_biblioteca.py [--forzar]`, escribe `indice_biblioteca.jsonl`

- [ ] **Step 1: Escribir el test (debe fallar: el módulo no existe)**

```python
# PROYECTO ELECTRICO/_INDEXADOR/tests/test_indexar_biblioteca.py
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indexar_biblioteca import ejecutar_indexacion, listar_pdfs_biblioteca

CARPETA_BIBLIOTECA_REAL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF_PRUEBA = os.path.join(CARPETA_BIBLIOTECA_REAL, "05_PUESTA A TIERRA", "00337-VIA CHISPAS.pdf")


class TestIndexarBiblioteca(unittest.TestCase):
    def setUp(self):
        self.carpeta_temporal = tempfile.mkdtemp()
        self.carpeta_categoria = os.path.join(self.carpeta_temporal, "01_CATEGORIA_PRUEBA")
        os.makedirs(self.carpeta_categoria)
        shutil.copy(PDF_PRUEBA, self.carpeta_categoria)
        self.carpeta_indexador = os.path.join(self.carpeta_temporal, "_INDEXADOR")
        os.makedirs(self.carpeta_indexador)
        self.ruta_indice = os.path.join(self.carpeta_indexador, "indice_biblioteca.jsonl")

    def tearDown(self):
        shutil.rmtree(self.carpeta_temporal, ignore_errors=True)

    def test_listar_pdfs_encuentra_el_pdf_de_prueba(self):
        pdfs = listar_pdfs_biblioteca(self.carpeta_temporal, self.carpeta_indexador)
        self.assertEqual(len(pdfs), 1)
        self.assertTrue(pdfs[0].endswith("00337-VIA CHISPAS.pdf"))

    def test_indexa_un_pdf_real_de_principio_a_fin(self):
        indice = ejecutar_indexacion(self.carpeta_temporal, self.carpeta_indexador, self.ruta_indice)
        self.assertGreater(len(indice), 0)
        primero = indice[0]
        for campo in ('id', 'libro', 'carpeta', 'ruta_relativa', 'paginas', 'texto', 'embedding'):
            self.assertIn(campo, primero)
        self.assertEqual(len(primero['embedding']), 2048)
        self.assertTrue(os.path.exists(self.ruta_indice))

    def test_segunda_ejecucion_no_reindexa_lo_ya_hecho(self):
        indice_1 = ejecutar_indexacion(self.carpeta_temporal, self.carpeta_indexador, self.ruta_indice)
        indice_2 = ejecutar_indexacion(self.carpeta_temporal, self.carpeta_indexador, self.ruta_indice)
        self.assertEqual(len(indice_1), len(indice_2))

    def test_forzar_reindexa_incluso_lo_ya_hecho(self):
        ejecutar_indexacion(self.carpeta_temporal, self.carpeta_indexador, self.ruta_indice)
        indice_forzado = ejecutar_indexacion(
            self.carpeta_temporal, self.carpeta_indexador, self.ruta_indice, forzar=True)
        self.assertGreater(len(indice_forzado), 0)

    def test_indice_persistido_es_jsonl_valido(self):
        ejecutar_indexacion(self.carpeta_temporal, self.carpeta_indexador, self.ruta_indice)
        with open(self.ruta_indice, 'r', encoding='utf-8') as f:
            lineas = [json.loads(l) for l in f if l.strip()]
        self.assertGreater(len(lineas), 0)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

Run: `cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python -m unittest tests.test_indexar_biblioteca -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'indexar_biblioteca'`

- [ ] **Step 3: Implementar `indexar_biblioteca.py`**

```python
"""Indexa la biblioteca de PROYECTO ELECTRICO: extrae texto de cada PDF, lo
trocea en fragmentos y genera un embedding por fragmento. Escribe el
resultado en indice_biblioteca.jsonl.

Uso:
    python indexar_biblioteca.py              # indexa solo los PDF nuevos
    python indexar_biblioteca.py --forzar      # reindexa todo desde cero
"""
import argparse
import json
import os
import time

from extraer_pdf import extraer_texto_por_pagina, trocear_texto
from embeddings_nvidia import generar_embeddings

CARPETA_INDEXADOR = os.path.dirname(os.path.abspath(__file__))
CARPETA_BIBLIOTECA = os.path.dirname(CARPETA_INDEXADOR)
RUTA_INDICE = os.path.join(CARPETA_INDEXADOR, "indice_biblioteca.jsonl")
TAMANO_LOTE_EMBEDDINGS = 20


def listar_pdfs_biblioteca(carpeta_biblioteca, carpeta_indexador):
    rutas = []
    for raiz, _carpetas, ficheros in os.walk(carpeta_biblioteca):
        if os.path.abspath(raiz).startswith(os.path.abspath(carpeta_indexador)):
            continue
        for f in ficheros:
            if f.lower().endswith('.pdf'):
                ruta_abs = os.path.join(raiz, f)
                rutas.append(os.path.relpath(ruta_abs, carpeta_biblioteca))
    return sorted(rutas)


def cargar_indice_existente(ruta_indice):
    if not os.path.exists(ruta_indice):
        return []
    fragmentos = []
    with open(ruta_indice, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if linea:
                fragmentos.append(json.loads(linea))
    return fragmentos


def guardar_indice(fragmentos, ruta_indice):
    ruta_temporal = ruta_indice + '.tmp'
    with open(ruta_temporal, 'w', encoding='utf-8') as f:
        for frag in fragmentos:
            f.write(json.dumps(frag, ensure_ascii=False) + '\n')
    os.replace(ruta_temporal, ruta_indice)


def indexar_pdf(ruta_relativa, carpeta_biblioteca):
    ruta_absoluta = os.path.join(carpeta_biblioteca, ruta_relativa)
    carpeta = ruta_relativa.split(os.sep)[0]
    libro = os.path.basename(ruta_relativa)

    paginas = extraer_texto_por_pagina(ruta_absoluta)
    fragmentos = trocear_texto(paginas)
    if not fragmentos:
        print(f"  [AVISO] sin texto extraible: {ruta_relativa}")
        return []

    resultado = []
    for inicio_lote in range(0, len(fragmentos), TAMANO_LOTE_EMBEDDINGS):
        lote = fragmentos[inicio_lote:inicio_lote + TAMANO_LOTE_EMBEDDINGS]
        textos_lote = [f['texto'] for f in lote]
        vectores = generar_embeddings(textos_lote, tipo="passage")
        if len(vectores) != len(textos_lote):
            raise RuntimeError(
                f"La API devolvio {len(vectores)} embeddings para {len(textos_lote)} "
                f"textos enviados al indexar {ruta_relativa} (deberian coincidir)"
            )
        for frag, vector in zip(lote, vectores):
            resultado.append({
                'id': f"{ruta_relativa}::{frag['paginas'][0] if frag['paginas'] else 0}::{len(resultado)}",
                'libro': libro,
                'carpeta': carpeta,
                'ruta_relativa': ruta_relativa,
                'paginas': frag['paginas'],
                'texto': frag['texto'],
                'embedding': vector,
            })
    return resultado


def ejecutar_indexacion(carpeta_biblioteca, carpeta_indexador, ruta_indice, forzar=False):
    indice = [] if forzar else cargar_indice_existente(ruta_indice)
    ya_indexados = {frag['ruta_relativa'] for frag in indice}

    pdfs = listar_pdfs_biblioteca(carpeta_biblioteca, carpeta_indexador)
    pdfs_pendientes = [p for p in pdfs if p not in ya_indexados]

    print(f"PDFs en la biblioteca: {len(pdfs)}")
    print(f"Ya indexados: {len(ya_indexados)}")
    print(f"Pendientes de indexar: {len(pdfs_pendientes)}")

    for i, ruta_relativa in enumerate(pdfs_pendientes, 1):
        print(f"[{i}/{len(pdfs_pendientes)}] {ruta_relativa}")
        try:
            nuevos_fragmentos = indexar_pdf(ruta_relativa, carpeta_biblioteca)
        except Exception as e:
            print(f"  [ERROR] no se pudo indexar: {e}")
            continue
        indice.extend(nuevos_fragmentos)
        guardar_indice(indice, ruta_indice)
        print(f"  {len(nuevos_fragmentos)} fragmentos anadidos (total acumulado: {len(indice)})")

    return indice


def main():
    parser = argparse.ArgumentParser(description="Indexa la biblioteca de PROYECTO ELECTRICO")
    parser.add_argument('--forzar', action='store_true',
                         help="Reindexa todos los PDF, incluso los ya presentes en el indice")
    args = parser.parse_args()

    inicio = time.time()
    indice = ejecutar_indexacion(CARPETA_BIBLIOTECA, CARPETA_INDEXADOR, RUTA_INDICE, forzar=args.forzar)
    duracion = time.time() - inicio

    tamano_mb = os.path.getsize(RUTA_INDICE) / (1024 * 1024) if os.path.exists(RUTA_INDICE) else 0
    num_pdfs = len(set(f['ruta_relativa'] for f in indice))
    print(f"\nTerminado en {duracion:.0f}s. Indice total: {len(indice)} fragmentos, "
          f"{num_pdfs} PDFs, {tamano_mb:.1f} MB.")


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Ejecutar el test y comprobar que pasa**

Run: `cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python -m unittest tests.test_indexar_biblioteca -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

Local a `PROYECTO ELECTRICO`, mismo criterio que Task 1 Step 6.

---

### Task 4: Ejecución real sobre la biblioteca completa

**Files:**
- Modify (generado, no código): `PROYECTO ELECTRICO/_INDEXADOR/indice_biblioteca.jsonl`
- Create: `PROYECTO ELECTRICO/_INDEXADOR/RESULTADO_INDEXACION.md`

**Interfaces:**
- Consumes: `ejecutar_indexacion` (Task 3), vía `python indexar_biblioteca.py`
- Produces: el índice real completo + un informe de tamaño/cobertura que decide R2 vs KV en Fase 2

- [ ] **Step 1: Ejecutar la indexación completa**

Run: `cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python indexar_biblioteca.py`

117 PDF, 1.7 GB en total (muchos son manuales técnicos con diagramas — el texto extraíble real puede ser mucho menor que el peso del PDF). Esto puede tardar varios minutos y consume cuota de la API de NVIDIA; dejar que termine y no interrumpirlo a mitad — el guardado es incremental (tras cada PDF), así que interrumpirlo no corrompe el índice, solo lo deja a medias para la próxima vez.

- [ ] **Step 2: Revisar la salida en busca de `[ERROR]` o `[AVISO]`**

Cada `[AVISO] sin texto extraible` es normal si ese PDF es solo imágenes escaneadas sin OCR — anotarlo, no es un fallo del indexador. Cada `[ERROR]` sí merece mirar por qué (PDF corrupto, protegido con contraseña, etc.) — si aparece alguno, abrir ese PDF concreto y confirmar la causa antes de continuar.

- [ ] **Step 3: Verificar el índice generado**

Run:
```bash
cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python -c "
import json
fragmentos = [json.loads(l) for l in open('indice_biblioteca.jsonl', encoding='utf-8') if l.strip()]
libros = sorted(set(f['ruta_relativa'] for f in fragmentos))
print(f'Fragmentos: {len(fragmentos)}')
print(f'PDFs con al menos un fragmento: {len(libros)}')
print(f'Ejemplo de fragmento: libro={fragmentos[0][\"libro\"]!r} paginas={fragmentos[0][\"paginas\"]} texto[:120]={fragmentos[0][\"texto\"][:120]!r}')
"
```
Expected: `Fragmentos` es un número mayor que cero y del orden de miles (117 PDFs troceados en fragmentos de ~1500 caracteres); `PDFs con al menos un fragmento` debería acercarse a 117 salvo los que salieron `[AVISO]` en el Step 2.

- [ ] **Step 4: Escribir `RESULTADO_INDEXACION.md` con las cifras reales**

Contenido (rellenar con los números reales del Step 1/3, no estos de ejemplo):

```markdown
# Resultado de la indexación — PROYECTO ELECTRICO

Fecha: [fecha real de ejecución]

- PDFs en la biblioteca: [N]
- PDFs indexados con éxito: [N]
- PDFs sin texto extraíble (solo imagen, ver AVISO): [lista o "ninguno"]
- PDFs con error (ver causa antes de continuar): [lista o "ninguno"]
- Fragmentos totales: [N]
- Tamaño de `indice_biblioteca.jsonl`: [N] MB
- Tiempo de ejecución: [N] min

## Para la Fase 2 (decisión R2 vs KV)

Con estas cifras reales, aplicar el criterio: si el índice completo pesa
por debajo de ~20 MB y cabe cómodo en un único valor, KV es más simple.
Si es mayor, o si el Worker necesita leerlo por partes, usar R2 (sin
límite de tamaño por objeto y sin coste de salida). Decisión tomada:
[R2 / KV] porque [razón basada en las cifras de arriba].
```

- [ ] **Step 5: Commit**

Local a `PROYECTO ELECTRICO`, mismo criterio que Task 1 Step 6. `indice_biblioteca.jsonl` nunca debe subirse a ningún repositorio público — si `PROYECTO ELECTRICO` tuviera algún día un remoto, confirmarlo antes de cualquier push.

---

## Qué sigue después de este plan

Con `RESULTADO_INDEXACION.md` en la mano, el siguiente paso es un **plan nuevo y separado** para Fase 2 (Worker de Cloudflare + pestaña `VARIOS/BUSCADOR ELECTRICO/` dentro del repo de Sagarde), que:
- Empieza parando para que Bixente cree la cuenta de Cloudflare paso a paso (spec, sección K.1) — comprobando antes que el plan gratuito de Workers sigue sin pedir tarjeta.
- Usa el `R2`/`KV` decidido en el Step 4 de arriba, ya con datos reales en vez de una suposición.
- Termina con un `git commit`/publicación en el repo de Sagarde que **requiere confirmación explícita de Bixente antes**, aunque parezca trivial (spec, sección K.2).

No escribir ese plan todavía — depende de las cifras reales que solo existen después de ejecutar este.
