# Buscador Eléctrico — Fase 2, implementación completa — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el Worker de Cloudflare real (búsqueda semántica sobre los 14.679 fragmentos de PROYECTO ELECTRICO + respuesta con IA citando el libro) y la pestaña HTML en Sagarde que habla con él, cerrando así el diseño aprobado en `_SISTEMA/docs/superpowers/specs/2026-09-14-buscador-electrico-design.md`.

**Architecture:** Durable Object con backend SQLite (gratis, sin límite de 10ms de CPU porque se factura por duración) que mantiene en memoria, entre peticiones, los 14.679 embeddings cuantizados (`Int8Array`, no descomprimidos — lección del spike) más sus textos y citas, cargados una vez desde Workers KV (troceado en 5 partes porque el índice completo no cabe en un único valor de 25 MB). Cada pregunta: contraseña → embedding de la pregunta (NVIDIA) → similitud coseno contra los 14.679 vectores en memoria → mejores fragmentos → respuesta de IA citando el libro → JSON de vuelta a la pestaña HTML.

**Tech Stack:** Cloudflare Workers + Durable Objects (SQLite backend) + Workers KV, JavaScript sin frameworks, API de NVIDIA (`nvidia/nemotron-3-embed-1b` para embeddings, `openai/gpt-oss-20b` para el chat), HTML autocontenido sin frameworks para la pestaña.

## Global Constraints

- **Nunca exponer la clave de NVIDIA ni el contenido de los libros en el repo público `centro-mando-sagarde`** — viven solo en secretos del Worker y en Workers KV (spec sección B, D).
- **Nunca dar una respuesta inventada como si viniera de un libro** — si no hay fragmentos relevantes, decirlo explícitamente y responder solo con conocimiento general (spec sección G).
- Todo el código de esta fase que NO sea la pestaña HTML vive en `D:\Nueva carpeta\OneDrive\PROYECTO ELECTRICO\_WORKER\` e `_INDEXADOR\` — repos git locales, **sin remoto, nunca lo tendrán**.
- **Antes de cualquier `git commit` que afecte al repo de Sagarde** (la pestaña HTML), parar y confirmar explícitamente con Bixente — sin excepción, aunque parezca trivial (spec sección K.2, y regla general de esta sesión).
- La pestaña HTML sigue el estilo visual de `VARIOS/TIERRAS/app_informe_tierras.html`: cabecera `#1a3a5c`, tipografía Inter, tarjetas redondeadas, sin frameworks nuevos (spec sección C.3).
- Antes de construir el resto (cliente NVIDIA, contraseña, pestaña) sobre el Durable Object, **medir de verdad contra Cloudflare con el índice completo de 14.679 vectores** — no basta con la proyección del spike (condición explícita de `PROYECTO ELECTRICO/_WORKER/RESULTADO_SPIKE.md`).
- Modelos verificados el 14-15/09/2026: `nvidia/nemotron-3-embed-1b` (embeddings, 2048 dims), `openai/gpt-oss-20b` (chat). Si al ejecutar esta fase ha pasado mucho tiempo, re-comprobar con `--list-models` antes de asumir que siguen disponibles.
- Base URL de la API de NVIDIA: `https://integrate.api.nvidia.com/v1`, autenticación `Authorization: Bearer <clave>`.

---

## Contexto que el ejecutor necesita y no está en el código

**El índice real** vive en `D:\Nueva carpeta\OneDrive\PROYECTO ELECTRICO\_INDEXADOR\indice_biblioteca.jsonl` (415,7 MB, no tocar ni mover). Cada línea es un JSON con esta forma exacta (confirmado leyendo `indexar_biblioteca.py`):

```json
{"id": "01_FUNDAMENTOS Y TEORIA/libro.pdf::12::3", "libro": "libro.pdf", "carpeta": "01_FUNDAMENTOS Y TEORIA", "ruta_relativa": "01_FUNDAMENTOS Y TEORIA/libro.pdf", "paginas": [12, 13], "texto": "...", "embedding": [2048 floats]}
```

Medido de verdad sobre el índice completo real (15/09/2026): **14.679 fragmentos**, texto total 21,4 MB (media 1.525 bytes/fragmento, máximo 2.410), metadatos (`libro`+`paginas`+`id`) 2,3 MB. Estas cifras son la base de todo el troceado de esta fase — no son una estimación.

**El spike ya resuelto** (`_SISTEMA/docs/superpowers/plans/2026-09-15-buscador-electrico-spike-durable-object.md`, resultado en `PROYECTO ELECTRICO/_WORKER/RESULTADO_SPIKE.md`) demostró que un Durable Object mantiene datos en memoria entre peticiones sin recargar, y encontró 2 condiciones obligatorias que este plan resuelve directamente: memoria (usar `Int8Array`, no `Float32Array`) y almacenamiento (trocear en KV, límite 25 MB por valor). El código del spike (`buscador_spike.js`) queda superado por este plan y se elimina en la Task 2 — su commit sigue en el historial de `_WORKER` por si hace falta consultarlo.

**Cuenta de Cloudflare ya operativa**: `CLOUDFLARE_API_TOKEN` en el entorno del controller (verificado con `wrangler whoami`). Namespace KV real ya existe: `buscador_electrico_spike`, id `f354460344604744a9206fb94c7d11d4` (se reutiliza, el nombre "spike" en el id ya no describe su contenido pero cambiarlo no aporta nada).

**Formato de los ficheros que sube esta fase a KV** (diseñado en esta sesión de planificación, a partir de las cifras reales de arriba):

- Clave `manifiesto` → texto JSON: `{"numVectores": 14679, "dimensiones": 2048, "numTrozos": 5}`.
- Claves `embeddings_0` .. `embeddings_4` → binario: 4 bytes uint32 little-endian con el nº de vectores DE ESE TROZO, seguido de esa cantidad × 2048 bytes int8 (mismo formato que el spike, uno por trozo). Trozos de 3.000 vectores (el último, 2.679) — cada uno pesa como mucho 3000×2048 = 6.144.000 bytes (5,9 MB), muy por debajo del límite de 25 MB de Workers KV.
- Claves `metadatos_0` .. `metadatos_4` → texto JSON: array de `{"id": "...", "libro": "...", "paginas": [...], "texto": "..."}`, en el MISMO ORDEN que los vectores del `embeddings_N` correspondiente (el índice `i` de un trozo identifica el mismo fragmento en ambas claves). Cada trozo pesa como mucho ~4,8 MB de media, muy por debajo de 25 MB.

**Memoria del Durable Object a escala completa, calculada con las cifras reales de arriba** (no la cifra del spike, que era solo memoria de embeddings): `Int8Array` de embeddings ≈ 28,7 MB + metadatos (parseados a objetos JS) ≈ 24-30 MB con margen generoso de overhead ≈ **59 MB de un límite de 128 MB por Durable Object** — margen amplio, no hace falta ninguna estrategia de carga bajo demanda para el texto.

---

### Task 1: Exportar el índice completo troceado y subirlo a Workers KV

**Files:**
- Create: `_INDEXADOR/exportar_indice_completo.py`
- Create: `_INDEXADOR/tests/test_exportar_indice_completo.py`
- Modify: `_INDEXADOR/.gitignore` (añadir `export_kv/` al final)

**Interfaces:**
- Consumes: `_INDEXADOR/indice_biblioteca.jsonl` (formato de arriba, ya existe)
- Produces: ficheros locales en `_INDEXADOR/export_kv/` (`manifiesto.json`, `embeddings_N.bin`, `metadatos_N.json`) y los mismos datos subidos de verdad a Workers KV bajo las claves de arriba

- [ ] **Step 1: Escribir el test (debe fallar: el módulo no existe)**

Crear `_INDEXADOR/tests/test_exportar_indice_completo.py`:

```python
import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exportar_indice_completo import cuantizar, decuantizar, trocear_indice, DIMENSIONES


class TestCuantizacion(unittest.TestCase):
    def test_cuantizar_decuantizar_ida_vuelta(self):
        for valor in [-0.5, -0.13, 0.0, 0.130, 0.402, 0.5]:
            entero = cuantizar(valor)
            self.assertGreaterEqual(entero, -128)
            self.assertLessEqual(entero, 127)
            recuperado = decuantizar(entero)
            self.assertAlmostEqual(recuperado, valor, delta=0.005)

    def test_cuantizar_recorta_fuera_de_rango(self):
        self.assertEqual(cuantizar(10.0), 127)
        self.assertEqual(cuantizar(-10.0), -128)


class TestTroceadoIndice(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.ruta_indice = os.path.join(self.carpeta, "indice_prueba.jsonl")
        # 7 fragmentos falsos, embedding de DIMENSIONES ceros salvo un valor
        with open(self.ruta_indice, "w", encoding="utf-8") as f:
            for i in range(7):
                frag = {
                    "id": f"libro.pdf::{i}::0",
                    "libro": "libro.pdf",
                    "carpeta": "01_FUNDAMENTOS Y TEORIA",
                    "ruta_relativa": "01_FUNDAMENTOS Y TEORIA/libro.pdf",
                    "paginas": [i],
                    "texto": f"fragmento numero {i}",
                    "embedding": [0.1 * (i % 5)] * DIMENSIONES,
                }
                f.write(json.dumps(frag, ensure_ascii=False) + "\n")

    def test_trocea_en_el_tamano_pedido(self):
        carpeta_salida = os.path.join(self.carpeta, "export_kv")
        manifiesto = trocear_indice(self.ruta_indice, carpeta_salida, tamano_trozo=3)

        self.assertEqual(manifiesto["numVectores"], 7)
        self.assertEqual(manifiesto["dimensiones"], DIMENSIONES)
        self.assertEqual(manifiesto["numTrozos"], 3)  # 3 + 3 + 1

        # Trozo 0: 3 vectores
        with open(os.path.join(carpeta_salida, "embeddings_0.bin"), "rb") as f:
            contenido = f.read()
        n_trozo0 = struct.unpack("<I", contenido[:4])[0]
        self.assertEqual(n_trozo0, 3)
        self.assertEqual(len(contenido), 4 + 3 * DIMENSIONES)

        # Trozo 2 (el ultimo, parcial): 1 vector
        with open(os.path.join(carpeta_salida, "embeddings_2.bin"), "rb") as f:
            contenido2 = f.read()
        n_trozo2 = struct.unpack("<I", contenido2[:4])[0]
        self.assertEqual(n_trozo2, 1)

        # Metadatos del trozo 0 tienen 3 entradas, en el mismo orden que el jsonl
        with open(os.path.join(carpeta_salida, "metadatos_0.json"), "r", encoding="utf-8") as f:
            metas0 = json.load(f)
        self.assertEqual(len(metas0), 3)
        self.assertEqual(metas0[0]["texto"], "fragmento numero 0")
        self.assertEqual(metas0[1]["texto"], "fragmento numero 1")
        self.assertEqual(metas0[0]["libro"], "libro.pdf")
        self.assertEqual(metas0[0]["paginas"], [0])
        self.assertNotIn("embedding", metas0[0])  # los metadatos NO llevan el vector


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

Run: `cd "_INDEXADOR" && python -m unittest tests.test_exportar_indice_completo -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'exportar_indice_completo'`

- [ ] **Step 3: Implementar `exportar_indice_completo.py`**

```python
"""Exporta el indice_biblioteca.jsonl COMPLETO, troceado en varias partes
para caber en el limite de 25 MB por valor de Workers KV, con los
embeddings cuantizados a int8 y los textos/citas en JSON aparte.

Formato de salida (en carpeta_salida):
  manifiesto.json      -> {"numVectores": N, "dimensiones": 2048, "numTrozos": T}
  embeddings_<i>.bin   -> 4 bytes uint32 LE (num. vectores de este trozo) +
                          esa cantidad * 2048 bytes int8
  metadatos_<i>.json   -> array de {id, libro, paginas, texto}, mismo orden
                          que los vectores de embeddings_<i>.bin

Uso:
    python exportar_indice_completo.py [tamano_trozo]
"""
import json
import os
import struct
import sys

RANGO_MIN = -0.5
RANGO_MAX = 0.5
DIMENSIONES = 2048
TAMANO_TROZO_DEFECTO = 3000

CARPETA_INDEXADOR = os.path.dirname(os.path.abspath(__file__))
RUTA_INDICE_DEFECTO = os.path.join(CARPETA_INDEXADOR, "indice_biblioteca.jsonl")
CARPETA_SALIDA_DEFECTO = os.path.join(CARPETA_INDEXADOR, "export_kv")


def cuantizar(valor, minimo=RANGO_MIN, maximo=RANGO_MAX):
    valor_recortado = max(minimo, min(maximo, valor))
    normalizado = (valor_recortado - minimo) / (maximo - minimo)
    entero = round(normalizado * 255) - 128
    return max(-128, min(127, entero))


def decuantizar(valor_int, minimo=RANGO_MIN, maximo=RANGO_MAX):
    normalizado = (valor_int + 128) / 255
    return normalizado * (maximo - minimo) + minimo


def _escribir_trozo(carpeta_salida, indice_trozo, fragmentos):
    ruta_bin = os.path.join(carpeta_salida, f"embeddings_{indice_trozo}.bin")
    ruta_json = os.path.join(carpeta_salida, f"metadatos_{indice_trozo}.json")

    with open(ruta_bin, "wb") as f_bin:
        f_bin.write(struct.pack("<I", len(fragmentos)))
        for frag in fragmentos:
            embedding = frag["embedding"]
            f_bin.write(bytes((cuantizar(v) + 256) % 256 for v in embedding))

    metadatos = [
        {"id": frag["id"], "libro": frag["libro"], "paginas": frag["paginas"], "texto": frag["texto"]}
        for frag in fragmentos
    ]
    with open(ruta_json, "w", encoding="utf-8") as f_json:
        json.dump(metadatos, f_json, ensure_ascii=False)

    return len(fragmentos)


def trocear_indice(ruta_indice, carpeta_salida, tamano_trozo=TAMANO_TROZO_DEFECTO):
    os.makedirs(carpeta_salida, exist_ok=True)

    total_vectores = 0
    num_trozos = 0
    trozo_actual = []

    with open(ruta_indice, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            fragmento = json.loads(linea)
            if len(fragmento.get("embedding", [])) != DIMENSIONES:
                continue
            trozo_actual.append(fragmento)
            if len(trozo_actual) >= tamano_trozo:
                n = _escribir_trozo(carpeta_salida, num_trozos, trozo_actual)
                total_vectores += n
                num_trozos += 1
                trozo_actual = []

    if trozo_actual:
        n = _escribir_trozo(carpeta_salida, num_trozos, trozo_actual)
        total_vectores += n
        num_trozos += 1

    manifiesto = {"numVectores": total_vectores, "dimensiones": DIMENSIONES, "numTrozos": num_trozos}
    with open(os.path.join(carpeta_salida, "manifiesto.json"), "w", encoding="utf-8") as f:
        json.dump(manifiesto, f)

    return manifiesto


if __name__ == "__main__":
    tamano = int(sys.argv[1]) if len(sys.argv) > 1 else TAMANO_TROZO_DEFECTO
    resultado = trocear_indice(RUTA_INDICE_DEFECTO, CARPETA_SALIDA_DEFECTO, tamano_trozo=tamano)
    print(f"Exportados {resultado['numVectores']} vectores en {resultado['numTrozos']} trozos "
          f"a {CARPETA_SALIDA_DEFECTO}")
```

- [ ] **Step 4: Ejecutar el test y comprobar que pasa**

Run: `cd "_INDEXADOR" && python -m unittest tests.test_exportar_indice_completo -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Ejecutar de verdad contra el índice real completo**

Run:
```bash
cd "_INDEXADOR"
python exportar_indice_completo.py
```
Expected: imprime `Exportados 14679 vectores en 5 trozos a .../_INDEXADOR/export_kv`. Comprobar con `ls -la export_kv/` que hay `manifiesto.json`, `embeddings_0.bin`..`embeddings_4.bin`, `metadatos_0.json`..`metadatos_4.json`, y que `embeddings_4.bin` y `metadatos_4.json` son más pequeños que los demás (el trozo parcial). Pegar el listado real en el informe.

- [ ] **Step 6: Añadir `export_kv/` al `.gitignore` de `_INDEXADOR`**

Añadir esta línea al final de `_INDEXADOR/.gitignore`:
```
export_kv/
```
(Son datos derivados y regenerables del índice real, igual que `*.bin` y `*.jsonl` ya excluidos — no aportan nada versionados y serían 30+ MB extra en un repo que ya pesa 415 MB.)

- [ ] **Step 7: Commit en `_INDEXADOR`**

```bash
cd "_INDEXADOR"
git add exportar_indice_completo.py tests/test_exportar_indice_completo.py .gitignore
git commit -m "Exporta el indice completo troceado (14679 vectores, 5 trozos) listo para subir a KV"
```

- [ ] **Step 8: Subir los 11 ficheros a Workers KV de verdad**

Requiere `CLOUDFLARE_API_TOKEN` en el entorno (igual que en el spike). Desde `_WORKER` (donde vive `wrangler.toml` con el binding `INDICE_KV`):

```bash
cd "_WORKER"
CARPETA_EXPORT="/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR/export_kv"
npx wrangler kv key put --remote --binding=INDICE_KV "manifiesto" --path="$CARPETA_EXPORT/manifiesto.json"
for i in 0 1 2 3 4; do
  npx wrangler kv key put --remote --binding=INDICE_KV "embeddings_$i" --path="$CARPETA_EXPORT/embeddings_$i.bin"
  npx wrangler kv key put --remote --binding=INDICE_KV "metadatos_$i" --path="$CARPETA_EXPORT/metadatos_$i.json"
done
```

Expected: 11 confirmaciones "Uploaded" (o el mensaje equivalente actual de wrangler), una por clave.

- [ ] **Step 9: Verificar contra el KV real (no el simulado local)**

```bash
npx wrangler kv key get --remote --binding=INDICE_KV "manifiesto"
```
Expected: `{"numVectores": 14679, "dimensiones": 2048, "numTrozos": 5}` — el mismo manifiesto que Step 5 generó localmente. Si difiere, hay un fallo real de subida, no dar el paso por bueno sin este número exacto.

No hay commit en este Step 8/9 (no es código, es una operación directa contra Cloudflare — igual que la Task 3 del spike).

---

### Task 2: Durable Object corregido (Int8Array, normas precalculadas) y medición diagnóstica

**Files:**
- Create: `_WORKER/src/buscador_electrico.js`
- Delete: `_WORKER/src/buscador_spike.js`
- Modify: `_WORKER/src/index.js`
- Modify: `_WORKER/wrangler.toml`

**Interfaces:**
- Consumes: claves KV `manifiesto`, `embeddings_0..4`, `metadatos_0..4` (Task 1)
- Produces: clase `BuscadorElectrico` con método interno `buscar(vectorConsulta, topK)` que devuelve `[{indice, puntuacion}]` ordenado de mayor a menor puntuación — la usará la Task 5 para la búsqueda real. Endpoint HTTP GET de diagnóstico (temporal, se sustituye en la Task 5) que carga el índice completo y compara el vector 0 contra el resto, igual que hacía el spike, para medir tiempos reales a escala completa.

- [ ] **Step 1: Escribir `buscador_electrico.js`**

```javascript
const DIMENSIONES = 2048;
const RANGO_MIN = -0.5;
const RANGO_MAX = 0.5;

function decuantizar(valorInt8) {
  const normalizado = (valorInt8 + 128) / 255;
  return normalizado * (RANGO_MAX - RANGO_MIN) + RANGO_MIN;
}

export class BuscadorElectrico {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.cargado = false;
    this.embeddings = null; // Int8Array unico: numVectores * DIMENSIONES
    this.normas = null; // Float32Array: una norma L2 precalculada por vector
    this.metadatos = null; // array de {id, libro, paginas, texto}, indice = mismo indice que embeddings
    this.numVectores = 0;
    this.msCarga = null;
  }

  async cargarSiHaceFalta() {
    if (this.cargado) {
      return false; // ya estaba cargado, no hubo que recargar
    }
    const inicio = Date.now();

    const manifiestoTexto = await this.env.INDICE_KV.get("manifiesto");
    if (!manifiestoTexto) {
      throw new Error("indice_vacio: no se encontro la clave 'manifiesto' en KV");
    }
    const manifiesto = JSON.parse(manifiestoTexto);
    if (!manifiesto.numVectores || manifiesto.dimensiones !== DIMENSIONES) {
      throw new Error("indice_corrupto: manifiesto con forma inesperada");
    }

    const embeddingsTotales = new Int8Array(manifiesto.numVectores * DIMENSIONES);
    const metadatosTotales = new Array(manifiesto.numVectores);

    // Pedir TODOS los trozos a la vez (10 lecturas de KV en paralelo, no 5
    // secuenciales) - es espera de red, no cuenta contra el limite de CPU,
    // y en paralelo el tiempo total de carga es el del trozo mas lento, no
    // la suma de los 5.
    const indicesDeTrozos = Array.from({ length: manifiesto.numTrozos }, (_, t) => t);
    const trozos = await Promise.all(
      indicesDeTrozos.map(async (t) => {
        const [bufferEmb, textoMeta] = await Promise.all([
          this.env.INDICE_KV.get(`embeddings_${t}`, "arrayBuffer"),
          this.env.INDICE_KV.get(`metadatos_${t}`, "text"),
        ]);
        if (!bufferEmb || !textoMeta) {
          throw new Error(`indice_corrupto: falta el trozo ${t} (embeddings o metadatos)`);
        }
        return { t, bufferEmb, textoMeta };
      })
    );
    // Promise.all conserva el orden de entrada (garantizado por el estandar
    // JS), asi que 'trozos' ya viene ordenado t=0..numTrozos-1 sin reordenar.

    let cursorVector = 0;
    for (const { t, bufferEmb, textoMeta } of trozos) {
      const vista = new DataView(bufferEmb);
      const numVectoresTrozo = vista.getUint32(0, true);
      const bytesInt8Trozo = new Int8Array(bufferEmb, 4);
      embeddingsTotales.set(
        bytesInt8Trozo.subarray(0, numVectoresTrozo * DIMENSIONES),
        cursorVector * DIMENSIONES
      );

      const metasTrozo = JSON.parse(textoMeta);
      if (metasTrozo.length !== numVectoresTrozo) {
        throw new Error(`indice_corrupto: el trozo ${t} tiene ${numVectoresTrozo} vectores pero ${metasTrozo.length} metadatos`);
      }
      for (let i = 0; i < metasTrozo.length; i++) {
        metadatosTotales[cursorVector + i] = metasTrozo[i];
      }

      cursorVector += numVectoresTrozo;
    }

    if (cursorVector !== manifiesto.numVectores) {
      throw new Error(`indice_corrupto: el manifiesto dice ${manifiesto.numVectores} vectores pero se cargaron ${cursorVector}`);
    }

    // Precalcular la norma L2 de cada vector UNA vez, en vez de recalcularla
    // en cada busqueda futura (los vectores guardados no cambian entre peticiones).
    const normas = new Float32Array(manifiesto.numVectores);
    for (let i = 0; i < manifiesto.numVectores; i++) {
      let suma = 0;
      const base = i * DIMENSIONES;
      for (let d = 0; d < DIMENSIONES; d++) {
        const v = decuantizar(embeddingsTotales[base + d]);
        suma += v * v;
      }
      normas[i] = Math.sqrt(suma);
    }

    this.embeddings = embeddingsTotales;
    this.metadatos = metadatosTotales;
    this.normas = normas;
    this.numVectores = manifiesto.numVectores;
    this.msCarga = Date.now() - inicio;
    this.cargado = true;
    return true; // se cargo de verdad en esta peticion
  }

  /** vectorConsulta: array/Float32Array normal (SIN cuantizar) de DIMENSIONES numeros,
   * tal cual lo devuelve la API de embeddings de NVIDIA. Devuelve los topK mejores
   * como [{indice, puntuacion}], de mayor a menor puntuacion. */
  buscar(vectorConsulta, topK) {
    let normaConsulta = 0;
    for (let d = 0; d < DIMENSIONES; d++) {
      normaConsulta += vectorConsulta[d] * vectorConsulta[d];
    }
    normaConsulta = Math.sqrt(normaConsulta);

    const resultados = new Array(this.numVectores);
    for (let i = 0; i < this.numVectores; i++) {
      const base = i * DIMENSIONES;
      let producto = 0;
      for (let d = 0; d < DIMENSIONES; d++) {
        producto += vectorConsulta[d] * decuantizar(this.embeddings[base + d]);
      }
      const puntuacion = producto / (normaConsulta * this.normas[i]);
      resultados[i] = { indice: i, puntuacion };
    }
    resultados.sort((a, b) => b.puntuacion - a.puntuacion);
    return resultados.slice(0, topK);
  }

  /** Endpoint temporal de diagnostico: carga el indice completo y compara el
   * vector 0 contra el resto, igual que hacia el spike, para medir tiempos
   * reales a escala completa antes de construir el resto encima. La Task 5
   * lo sustituye por el endpoint real de busqueda semantica. */
  async fetch(request) {
    const seCargoAhora = await this.cargarSiHaceFalta();

    const inicioBusqueda = Date.now();
    const vectorPrueba = [];
    for (let d = 0; d < DIMENSIONES; d++) {
      vectorPrueba.push(decuantizar(this.embeddings[d])); // el propio vector 0, descuantizado
    }
    const resultados = this.buscar(vectorPrueba, 5);
    const msBusqueda = Date.now() - inicioBusqueda;

    return new Response(
      JSON.stringify({
        seCargoEnEstaPeticion: seCargoAhora,
        numVectores: this.numVectores,
        msCargaPrimeraVez: this.msCarga,
        msBusquedaEstaPeticion: msBusqueda,
        top5: resultados,
      }),
      { headers: { "content-type": "application/json" } }
    );
  }
}
```

- [ ] **Step 2: Actualizar `index.js` para usar la nueva clase**

```javascript
export { BuscadorElectrico } from "./buscador_electrico.js";

export default {
  async fetch(request, env) {
    const id = env.BUSCADOR_ELECTRICO.idFromName("unico");
    const stub = env.BUSCADOR_ELECTRICO.get(id);
    return stub.fetch(request);
  },
};
```

- [ ] **Step 3: Actualizar `wrangler.toml`**

```toml
name = "buscador-electrico-spike"
main = "src/index.js"
compatibility_date = "2026-09-15"

[[kv_namespaces]]
binding = "INDICE_KV"
id = "f354460344604744a9206fb94c7d11d4"

[[durable_objects.bindings]]
name = "BUSCADOR_ELECTRICO"
class_name = "BuscadorElectrico"

[[migrations]]
tag = "v1"
new_sqlite_classes = ["BuscadorSpike"]

[[migrations]]
tag = "v2"
renamed_classes = [{ from = "BuscadorSpike", to = "BuscadorElectrico" }]
```

(El nombre del Worker en sí, `buscador-electrico-spike`, se deja tal cual en esta tarea — cambiarlo de nombre en Cloudflare es una operación aparte sin código, y no aporta nada crítico para el spike de rendimiento de esta tarea. Se puede renombrar más adelante si Bixente lo pide.)

- [ ] **Step 4: Eliminar el código del spike, ya superado**

```bash
cd "_WORKER"
git rm src/buscador_spike.js
```

- [ ] **Step 5: Comprobar la sintaxis de los ficheros JS**

Run:
```bash
cd "_WORKER"
node --check src/buscador_electrico.js
node --check src/index.js
```
Expected: exit code 0 en ambos, sin salida de error.

- [ ] **Step 6: Commit**

```bash
cd "_WORKER"
git add src/buscador_electrico.js src/index.js wrangler.toml
git commit -m "Sustituye el Durable Object del spike por la version corregida (Int8Array, normas precalculadas, indice completo troceado)"
```

---

### Task 3: Desplegar y medir de verdad contra Cloudflare con el índice completo (GO/NO-GO)

**Files:**
- Ninguno de código — despliegue y medición real, igual que la Task 5 del spike

**Interfaces:**
- Consumes: todo lo anterior
- Produces: decisión GO/NO-GO documentada en `PROYECTO ELECTRICO/_WORKER/RESULTADO_MEDICION_ESCALA_COMPLETA.md`

Ejecuta el controller directamente (no un subagente) — es la decisión central de esta fase, igual que la Task 5 del spike.

- [ ] **Step 1: Desplegar**

```bash
cd "_WORKER"
npx wrangler deploy
```
Expected: despliegue correcto, imprime la URL pública del Worker.

- [ ] **Step 2: Llamar al endpoint 5 veces con esperas y registrar los resultados reales**

No usar PowerShell (`>` corrompe binarios, y `Invoke-RestMethod` no siempre manda cabeceras de navegador) ni `curl`/`wget` directo. Usar este script Python real (lección de esta sesión: Cloudflare bloquea peticiones sin cabeceras de navegador con `403 error code 1010`):

```python
import json
import time
import urllib.request
import urllib.error

URL = "URL_REAL_QUE_DIO_WRANGLER_DEPLOY_EN_EL_STEP_1"

CABECERAS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

for i in range(1, 6):
    inicio = time.monotonic()
    peticion = urllib.request.Request(URL, headers=CABECERAS)
    try:
        with urllib.request.urlopen(peticion, timeout=60) as resp:
            cuerpo = json.loads(resp.read().decode("utf-8"))
            print(f"--- llamada {i} (status {resp.status}, {round((time.monotonic()-inicio)*1000)}ms round-trip) ---")
            print(json.dumps(cuerpo, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"--- llamada {i}: HTTPError {e.code} ---")
        print(e.read().decode("utf-8", errors="replace"))
    except urllib.error.URLError as e:
        print(f"--- llamada {i}: URLError {e.reason} ---")
    if i < 5:
        time.sleep(1)
```

Sustituir `URL_REAL_QUE_DIO_WRANGLER_DEPLOY_EN_EL_STEP_1` por la URL real del Step 1 antes de ejecutar. Registrar literalmente la salida de las 5 llamadas: `seCargoEnEstaPeticion`, `numVectores` (debe ser exactamente 14679), `msCargaPrimeraVez`, `msBusquedaEstaPeticion` de cada una.

**Comprobar explícitamente que ninguna respuesta es un error de límite excedido ni un error 5xx.**

- [ ] **Step 3: Revisar el panel de Cloudflare (opcional si el Step 2 ya es concluyente)**

`dash.cloudflare.com` → Workers & Pages → el Worker → Observability. Si las 5 llamadas del Step 2 devolvieron 200 con JSON válido y tiempos por debajo de los límites, esto es una confirmación opcional, no bloqueante (mismo razonamiento que en `RESULTADO_SPIKE.md`).

- [ ] **Step 4: Escribir `RESULTADO_MEDICION_ESCALA_COMPLETA.md`**

En `PROYECTO ELECTRICO/_WORKER/RESULTADO_MEDICION_ESCALA_COMPLETA.md`, con esta estructura (rellenar con datos reales, no proyecciones):

```markdown
# Medición real a escala completa (14.679 vectores) — Durable Object

Fecha: [fecha real]
Worker desplegado: [URL real] — Version ID [real]

- Vectores cargados: [N, debe ser 14679]
- Tiempo de primera carga: [N] ms
- Tiempo de búsqueda en peticiones siguientes (promedio 2-5): [N] ms
- ¿Algún error de límite excedido o 5xx?: [sí/no]
- Memoria: [confirmar que no hubo ningún error de memoria — Cloudflare mata el Durable Object con un error concreto si excede los 128 MB, no falla en silencio]

## Decisión

[GO: continuar con la Task 4 en adelante / NO-GO: parar y consultar con
Bixente Plan C o Plan D — spec y detalle en RESULTADO_SPIKE.md — antes de
seguir. No es decisión unilateral.]
```

- [ ] **Step 5: Commit**

```bash
cd "_WORKER"
git add RESULTADO_MEDICION_ESCALA_COMPLETA.md
git commit -m "Registra la medicion real a escala completa (14679 vectores) y la decision GO/NO-GO"
```

**Si NO-GO: parar el plan aquí y consultar con Bixente antes de ejecutar la Task 4 en adelante.**

---

### Task 4: Cliente de NVIDIA en JavaScript (embeddings + chat)

**Files:**
- Create: `_WORKER/src/nvidia.js`
- Test: `_WORKER/test/nvidia.test.mjs`

**Interfaces:**
- Consumes: `fetch` global de Workers, `NVIDIA_API_KEY` como parámetro (viene del secreto del Worker, Task 6)
- Produces: `generarEmbedding(texto, tipoEntrada, claveApi)` → `Promise<number[]>` (2048 floats), `generarRespuestaChat(mensajes, claveApi)` → `Promise<string>` — ambas usadas por la Task 5

- [ ] **Step 1: Escribir `nvidia.js`**

```javascript
const BASE_URL = "https://integrate.api.nvidia.com/v1";
const MODELO_EMBEDDINGS = "nvidia/nemotron-3-embed-1b";
const MODELO_CHAT = "openai/gpt-oss-20b";

async function llamarConReintento(url, opciones, timeoutMs, maxIntentos = 2) {
  let ultimoError;
  for (let intento = 1; intento <= maxIntentos; intento++) {
    const controlador = new AbortController();
    const temporizador = setTimeout(() => controlador.abort(), timeoutMs);
    try {
      const resp = await fetch(url, { ...opciones, signal: controlador.signal });
      clearTimeout(temporizador);
      if (!resp.ok) {
        const cuerpo = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${cuerpo.slice(0, 300)}`);
      }
      return await resp.json();
    } catch (error) {
      clearTimeout(temporizador);
      ultimoError = error;
      // un solo reintento automatico como mucho (spec seccion G)
    }
  }
  throw new Error(`nvidia_no_responde: ${ultimoError.message}`);
}

/** tipoEntrada: "passage" para texto indexado, "query" para una pregunta. */
export async function generarEmbedding(texto, tipoEntrada, claveApi) {
  const payload = await llamarConReintento(
    `${BASE_URL}/embeddings`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${claveApi}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ input: [texto], model: MODELO_EMBEDDINGS, input_type: tipoEntrada }),
    },
    15000
  );
  const datos = payload.data;
  if (!datos || datos.length === 0) {
    throw new Error("nvidia_respuesta_invalida: sin datos de embedding");
  }
  // reordenar por 'index' por seguridad, igual que el cliente Python (Fase 1)
  const ordenados = [...datos].sort((a, b) => a.index - b.index);
  return ordenados[0].embedding;
}

export async function generarRespuestaChat(mensajes, claveApi) {
  const payload = await llamarConReintento(
    `${BASE_URL}/chat/completions`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${claveApi}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        model: MODELO_CHAT,
        messages: mensajes,
        temperature: 0.6,
        max_tokens: 1024,
        stream: false,
      }),
    },
    30000
  );
  const contenido = payload.choices?.[0]?.message?.content;
  if (!contenido) {
    throw new Error("nvidia_respuesta_invalida: sin contenido en la respuesta de chat");
  }
  return contenido;
}
```

- [ ] **Step 2: Escribir un test real contra la API de verdad (no simulado)**

Crear `_WORKER/test/nvidia.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { generarEmbedding, generarRespuestaChat } from "../src/nvidia.js";

const claveApi = process.env.NVIDIA_API_KEY;
if (!claveApi) {
  console.error("SALTADO: falta NVIDIA_API_KEY en el entorno para el test real");
  process.exit(1);
}

async function main() {
  const embedding = await generarEmbedding("cuadro de proteccion electrica", "query", claveApi);
  assert.equal(embedding.length, 2048, `esperaba 2048 dimensiones, obtuvo ${embedding.length}`);
  assert.ok(embedding.every((v) => typeof v === "number"), "todos los valores deben ser numeros");
  console.log("OK generarEmbedding: 2048 dimensiones recibidas");

  const respuesta = await generarRespuestaChat(
    [{ role: "user", content: "Responde solo con la palabra OK." }],
    claveApi
  );
  assert.ok(typeof respuesta === "string" && respuesta.length > 0, "la respuesta de chat debe ser texto no vacio");
  console.log(`OK generarRespuestaChat: recibido "${respuesta.slice(0, 50)}"`);

  console.log("TODOS LOS TESTS REALES PASARON");
}

main().catch((error) => {
  console.error("FALLO:", error);
  process.exit(1);
});
```

- [ ] **Step 3: Ejecutar el test real y pegar la salida completa**

Run (con `NVIDIA_API_KEY` en el entorno — el mismo patrón de lectura del registro de Windows que usa `nvidia_chat.py` si la sesión actual no la ha heredado):
```bash
cd "_WORKER"
node test/nvidia.test.mjs
```
Expected: `OK generarEmbedding: 2048 dimensiones recibidas`, `OK generarRespuestaChat: recibido "..."`, `TODOS LOS TESTS REALES PASARON`, exit code 0. Si falla, diagnosticar la causa raíz real (¿clave no llega al proceso? ¿modelo caído? — usar `--list-models` de `nvidia_chat.py` para comprobar) antes de continuar.

- [ ] **Step 4: Commit**

```bash
cd "_WORKER"
git add src/nvidia.js test/nvidia.test.mjs
git commit -m "Añade el cliente de NVIDIA en JS (embeddings + chat) con reintento, probado contra la API real"
```

---

### Task 5: Endpoint real de búsqueda semántica en el Durable Object

**Files:**
- Modify: `_WORKER/src/buscador_electrico.js`
- Modify: `_WORKER/src/index.js`

**Interfaces:**
- Consumes: `buscar()` y carga (Task 2), `generarEmbedding`/`generarRespuestaChat` (Task 4), secretos `env.NVIDIA_API_KEY` y `env.ACCESO_PASSWORD` (Task 6)
- Produces: contrato HTTP real que consumirá la pestaña HTML (Task 7): `POST /` con body `{"pregunta": "...", "clave": "..."}` → `200 {"respuesta": "...", "encontradoEnLibros": bool, "fuentes": [{"libro","paginas","puntuacion"}]}` en éxito; `403 {"error"}` si la clave no coincide; `502 {"error"}` si NVIDIA no responde tras el reintento; `500 {"error"}` si el índice está vacío o corrupto

**Umbral de relevancia**: 0,35 de similitud coseno como valor de partida (no hay forma de derivarlo con precisión sin preguntas reales — la Task 8 lo calibra con el juego de preguntas de prueba). Por debajo de ese umbral en el mejor resultado, se considera que no hay nada relevante en los libros.

- [ ] **Step 1: Reemplazar el método `fetch` de `BuscadorElectrico` por el endpoint real**

En `buscador_electrico.js`, añadir el import al principio del fichero:
```javascript
import { generarEmbedding, generarRespuestaChat } from "./nvidia.js";
```

Y sustituir el método `fetch` completo (el de diagnóstico de la Task 2) por:

```javascript
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CABECERAS_CORS });
    }
    if (request.method !== "POST") {
      return respuestaJson({ error: "metodo_no_permitido" }, 405);
    }

    let cuerpo;
    try {
      cuerpo = await request.json();
    } catch {
      return respuestaJson({ error: "cuerpo_invalido" }, 400);
    }

    const { pregunta, clave } = cuerpo;
    if (!clave || clave !== this.env.ACCESO_PASSWORD) {
      return respuestaJson({ error: "no_autorizado" }, 403);
    }
    if (!pregunta || typeof pregunta !== "string" || !pregunta.trim()) {
      return respuestaJson({ error: "falta_la_pregunta" }, 400);
    }

    try {
      await this.cargarSiHaceFalta();
    } catch (error) {
      return respuestaJson(
        { error: "indice_no_disponible", detalle: "El índice de libros no está disponible ahora mismo. Avisa a Bixente para revisarlo." },
        500
      );
    }

    let vectorPregunta;
    try {
      vectorPregunta = await generarEmbedding(pregunta, "query", this.env.NVIDIA_API_KEY);
    } catch (error) {
      return respuestaJson(
        { error: "ia_no_responde", detalle: "El servicio de IA no responde ahora mismo. Prueba de nuevo en unos minutos." },
        502
      );
    }

    const UMBRAL_RELEVANCIA = 0.35;
    const TOP_K = 5;
    const mejores = this.buscar(vectorPregunta, TOP_K);
    const encontradoEnLibros = mejores.length > 0 && mejores[0].puntuacion >= UMBRAL_RELEVANCIA;
    const relevantes = encontradoEnLibros ? mejores.filter((r) => r.puntuacion >= UMBRAL_RELEVANCIA) : [];

    const mensajes = construirMensajes(pregunta, relevantes, this.metadatos, encontradoEnLibros);

    let respuestaIA;
    try {
      respuestaIA = await generarRespuestaChat(mensajes, this.env.NVIDIA_API_KEY);
    } catch (error) {
      return respuestaJson(
        { error: "ia_no_responde", detalle: "El servicio de IA no responde ahora mismo. Prueba de nuevo en unos minutos." },
        502
      );
    }

    return respuestaJson({
      respuesta: respuestaIA,
      encontradoEnLibros,
      fuentes: relevantes.map((r) => ({
        libro: this.metadatos[r.indice].libro,
        paginas: this.metadatos[r.indice].paginas,
        puntuacion: r.puntuacion,
      })),
    });
  }
```

Y añadir, fuera de la clase, en el mismo fichero:

```javascript
const CABECERAS_CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function respuestaJson(objeto, status = 200) {
  return new Response(JSON.stringify(objeto), {
    status,
    headers: { "content-type": "application/json", ...CABECERAS_CORS },
  });
}

function construirMensajes(pregunta, relevantes, metadatos, encontradoEnLibros) {
  const sistema =
    "Eres un asistente técnico de electricidad para un instalador electricista en España. " +
    "Responde siempre en español, de forma clara y práctica. " +
    "Cuando uses información de los FRAGMENTOS DE LIBROS de abajo, dilo explícitamente citando el libro. " +
    "Si los fragmentos no contienen la respuesta, dilo explícitamente y responde solo con tu conocimiento general — " +
    "nunca finjas que una respuesta viene de un libro cuando no es así.";

  if (!encontradoEnLibros) {
    return [
      { role: "system", content: sistema },
      {
        role: "user",
        content:
          `${pregunta}\n\n` +
          "(No se ha encontrado ningún fragmento relevante en la biblioteca de libros para esta pregunta. " +
          "Indícalo explícitamente al principio de tu respuesta y responde solo con conocimiento general.)",
      },
    ];
  }

  const contexto = relevantes
    .map((r, i) => {
      const meta = metadatos[r.indice];
      return `[Fragmento ${i + 1} — libro "${meta.libro}", página(s) ${meta.paginas.join(", ")}]\n${meta.texto}`;
    })
    .join("\n\n");

  return [
    { role: "system", content: sistema },
    {
      role: "user",
      content:
        `FRAGMENTOS DE LIBROS ENCONTRADOS:\n\n${contexto}\n\n` +
        `PREGUNTA: ${pregunta}\n\n` +
        "Responde usando estos fragmentos cuando sean relevantes, citando el libro y la página. " +
        "Si necesitas añadir conocimiento general que no está en los fragmentos, dilo explícitamente.",
    },
  ];
}
```

- [ ] **Step 2: Actualizar `index.js` para pasar CORS también en la ruta del Worker principal**

```javascript
export { BuscadorElectrico } from "./buscador_electrico.js";

export default {
  async fetch(request, env) {
    const id = env.BUSCADOR_ELECTRICO.idFromName("unico");
    const stub = env.BUSCADOR_ELECTRICO.get(id);
    return stub.fetch(request);
  },
};
```

(Sin cambios reales respecto a la Task 2 — las cabeceras CORS ya las pone `buscador_electrico.js`. Se deja este Step para dejar constancia de que se revisó, no hay un segundo sitio donde también haga falta.)

- [ ] **Step 3: Comprobar sintaxis**

Run:
```bash
cd "_WORKER"
node --check src/buscador_electrico.js
node --check src/index.js
```
Expected: exit code 0 en ambos.

- [ ] **Step 4: Commit**

```bash
cd "_WORKER"
git add src/buscador_electrico.js src/index.js
git commit -m "Implementa el endpoint real de busqueda semantica: contrasena, busqueda vectorial, respuesta de IA con citas"
```

(El despliegue y la prueba real end-to-end de este endpoint, con la contraseña real ya configurada, se hacen en la Task 6 y la Task 8 — hace falta el secreto `ACCESO_PASSWORD`, que todavía no existe.)

---

### Task 6: Secretos del Worker (clave de NVIDIA y contraseña de acceso)

**Files:**
- Ninguno de código — configuración de Cloudflare vía `wrangler secret put`

**Interfaces:**
- Consumes: `NVIDIA_API_KEY` ya existente en el entorno de Windows (mismo patrón de lectura que `nvidia_chat.py`)
- Produces: secretos `NVIDIA_API_KEY` y `ACCESO_PASSWORD` disponibles como `env.NVIDIA_API_KEY`/`env.ACCESO_PASSWORD` dentro del Worker (usados por la Task 5)

Ejecuta el controller directamente (operación de Cloudflare con el token ya autorizado, mismo patrón que la Task 3 del spike — no requiere que Bixente inicie sesión en ningún sitio nuevo, ya lo autorizó al crear el token).

- [ ] **Step 1: Subir la clave de NVIDIA como secreto**

```bash
cd "_WORKER"
printf '%s' "$NVIDIA_API_KEY" | npx wrangler secret put NVIDIA_API_KEY
```
(Si `$NVIDIA_API_KEY` no está en el entorno de esta sesión de shell, leerla primero igual que hace `nvidia_chat.py`: `[System.Environment]::GetEnvironmentVariable("NVIDIA_API_KEY","User")` desde PowerShell, o el registro desde Python, e inyectarla en el mismo comando.)

Expected: confirmación de wrangler de que el secreto se ha subido.

- [ ] **Step 2: Generar una contraseña de acceso y confirmarla con Bixente**

Generar una contraseña aleatoria razonable (ej. `python -c "import secrets; print(secrets.token_urlsafe(12))"`), y **preguntarle a Bixente en el chat si la quiere usar tal cual o prefiere elegir la suya** — es una decisión suya, no algo que se fije en silencio (spec sección K.3, "cualquier ambigüedad real"). Guardar la que él confirme.

- [ ] **Step 3: Subir la contraseña de acceso como secreto**

```bash
printf '%s' "LA_CONTRASENA_QUE_CONFIRME_BIXENTE" | npx wrangler secret put ACCESO_PASSWORD
```

- [ ] **Step 4: Desplegar y probar el endpoint real de punta a punta**

```bash
npx wrangler deploy
```

Con un script Python real (con cabeceras de navegador, misma lección que antes), hacer una pregunta de prueba real:
```python
import json, urllib.request

datos = json.dumps({"pregunta": "¿Qué es un diferencial?", "clave": "LA_CONTRASENA_REAL"}).encode("utf-8")
peticion = urllib.request.Request(
    "https://<URL-REAL-DEL-WORKER>/",
    data=datos,
    method="POST",
    headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    },
)
with urllib.request.urlopen(peticion, timeout=30) as resp:
    print(json.dumps(json.loads(resp.read()), indent=2, ensure_ascii=False))
```
Expected: `200`, JSON con `respuesta` (texto real de la IA), `encontradoEnLibros`, `fuentes` con al menos un libro real de PROYECTO ELECTRICO. Pegar la respuesta real completa en el informe — es la primera prueba real de que todo el flujo (contraseña → embedding → búsqueda → IA → cita) funciona de punta a punta.

No hay commit en esta tarea (son operaciones de Cloudflare, no cambios de código).

---

### Task 7: Pestaña HTML en Sagarde (sin commitear todavía)

**Files:**
- Create: `VARIOS/BUSCADOR ELECTRICO/index.html` (en el repo de Sagarde — **solo escribir el fichero en disco, NO hacer `git add` ni `git commit` en esta tarea**, eso es la Task 9)

**Interfaces:**
- Consumes: el endpoint real `POST /` del Worker (Task 5/6): body `{"pregunta", "clave"}`, respuesta `{"respuesta","encontradoEnLibros","fuentes"}` o `{"error"}`

- [ ] **Step 1: Escribir la pestaña**

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Buscador Eléctrico</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',system-ui,-apple-system,'Segoe UI',Arial,sans-serif;background:#f0f4f8;color:#222;min-height:100vh}
h1{background:#1a3a5c;color:#fff;padding:14px 20px;font-size:1.1em}
.contenido{padding:18px;max-width:720px;margin:0 auto}
.caja-pregunta{background:#fff;border:1px solid #dce8f5;border-radius:8px;padding:16px;margin-bottom:16px}
textarea{width:100%;padding:10px;border:1px solid #bcd;border-radius:6px;font-size:.95em;font-family:inherit;height:80px;resize:vertical}
.btn-preguntar{background:#1a3a5c;color:#fff;border:none;padding:11px 24px;border-radius:6px;cursor:pointer;font-size:.95em;font-weight:700;margin-top:10px}
.btn-preguntar:disabled{background:#8fa8c0;cursor:wait}
.caja-clave{background:#fff8e1;border:1px solid #f0c040;border-radius:8px;padding:14px;margin-bottom:16px}
.caja-clave input{width:100%;padding:8px;border:1px solid #bcd;border-radius:6px;font-size:.9em;margin-top:6px}
.caja-clave.oculta{display:none}
.respuesta{background:#fff;border:1px solid #dce8f5;border-radius:8px;padding:18px;line-height:1.65;white-space:pre-wrap}
.respuesta.oculta{display:none}
.aviso-general{background:#f0f4ff;border-left:4px solid #6690c4;padding:10px 14px;font-size:.85em;margin-bottom:12px;border-radius:0 6px 6px 0}
.fuentes{margin-top:14px;padding-top:12px;border-top:1px solid #dce8f5}
.fuente{display:inline-block;background:#eaf1fb;color:#1a3a5c;padding:4px 10px;border-radius:12px;font-size:.78em;font-weight:700;margin:2px 4px 2px 0}
.error{background:#fdedec;color:#b03a2e;border:1px solid #f1948a;border-radius:8px;padding:14px;margin-bottom:16px}
.cargando{color:#666;font-style:italic}
</style>
</head>
<body>
<h1>Buscador Eléctrico</h1>
<div class="contenido">

  <div class="caja-clave" id="cajaClave">
    <label for="inputClave"><strong>Contraseña de acceso</strong> (se guarda en este dispositivo, no hace falta escribirla cada vez)</label>
    <input type="password" id="inputClave" placeholder="Contraseña">
  </div>

  <div class="caja-pregunta">
    <label for="inputPregunta">Pregunta técnica</label>
    <textarea id="inputPregunta" placeholder="Ej: ¿Qué sección de cable necesito para una línea de 25A?"></textarea>
    <button class="btn-preguntar" id="btnPreguntar">Preguntar</button>
  </div>

  <div class="error oculta" id="cajaError"></div>
  <div class="respuesta oculta" id="cajaRespuesta"></div>

</div>

<script>
const URL_WORKER = "URL_REAL_DEL_WORKER_AQUI"; // se rellena con la URL real desplegada en la Task 6

const inputClave = document.getElementById("inputClave");
const cajaClave = document.getElementById("cajaClave");
const inputPregunta = document.getElementById("inputPregunta");
const btnPreguntar = document.getElementById("btnPreguntar");
const cajaError = document.getElementById("cajaError");
const cajaRespuesta = document.getElementById("cajaRespuesta");

const claveGuardada = localStorage.getItem("buscadorElectricoClave");
if (claveGuardada) {
  inputClave.value = claveGuardada;
  cajaClave.classList.add("oculta");
}

function mostrarError(mensaje) {
  cajaError.textContent = mensaje;
  cajaError.classList.remove("oculta");
  cajaRespuesta.classList.add("oculta");
}

function mostrarRespuesta(datos) {
  cajaError.classList.add("oculta");
  let html = "";
  if (!datos.encontradoEnLibros) {
    html += '<div class="aviso-general">Esto no lo he encontrado en tus libros — es conocimiento general de la IA.</div>';
  }
  html += datos.respuesta.replace(/</g, "&lt;");
  if (datos.fuentes && datos.fuentes.length > 0) {
    html += '<div class="fuentes">';
    for (const f of datos.fuentes) {
      html += `<span class="fuente">${f.libro} (pág. ${f.paginas.join(", ")})</span>`;
    }
    html += "</div>";
  }
  cajaRespuesta.innerHTML = html;
  cajaRespuesta.classList.remove("oculta");
}

async function preguntar() {
  const pregunta = inputPregunta.value.trim();
  const clave = inputClave.value.trim();

  if (!clave) {
    mostrarError("Escribe la contraseña de acceso primero.");
    return;
  }
  if (!pregunta) {
    mostrarError("Escribe una pregunta.");
    return;
  }

  btnPreguntar.disabled = true;
  btnPreguntar.textContent = "Pensando...";
  cajaError.classList.add("oculta");
  cajaRespuesta.classList.add("oculta");

  try {
    const resp = await fetch(URL_WORKER, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta, clave }),
    });
    const datos = await resp.json();

    if (!resp.ok) {
      if (datos.error === "no_autorizado") {
        mostrarError("Contraseña incorrecta.");
      } else if (datos.error === "ia_no_responde") {
        mostrarError(datos.detalle || "El servicio de IA no responde ahora mismo. Prueba de nuevo en unos minutos.");
      } else if (datos.error === "indice_no_disponible") {
        mostrarError(datos.detalle || "El índice de libros no está disponible ahora mismo. Avisa a Bixente para revisarlo.");
      } else {
        mostrarError("Ha ocurrido un error inesperado: " + (datos.error || resp.status));
      }
      return;
    }

    localStorage.setItem("buscadorElectricoClave", clave);
    cajaClave.classList.add("oculta");
    mostrarRespuesta(datos);
  } catch (error) {
    mostrarError("No se ha podido conectar con el buscador. Comprueba tu conexión a internet.");
  } finally {
    btnPreguntar.disabled = false;
    btnPreguntar.textContent = "Preguntar";
  }
}

btnPreguntar.addEventListener("click", preguntar);
inputPregunta.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) preguntar();
});
</script>
</body>
</html>
```

- [ ] **Step 2: Sustituir `URL_REAL_DEL_WORKER_AQUI` por la URL real**

Editar la línea `const URL_WORKER = "..."` con la URL real que dio `wrangler deploy` en la Task 6.

- [ ] **Step 3: Probar en local antes de tocar el repo de Sagarde**

Abrir el fichero directamente en un navegador (doble clic, o `file://`) y probar una pregunta real contra el Worker real ya desplegado. Confirmar que aparece la respuesta, las fuentes citadas, y que tras la primera pregunta la caja de contraseña desaparece (quedó en `localStorage`). Esto es la primera mitad de la Task 8 (pruebas) — no hay commit todavía, sigue siendo un fichero suelto en disco.

---

### Task 8: Pruebas (juego de preguntas, mutación, y checklist móvil para Bixente)

**Files:**
- Ninguno nuevo — pruebas sobre lo ya construido

**Interfaces:**
- Consumes: el sistema completo (Tasks 1-7)
- Produces: confianza verificada de que responde de verdad citando libros reales, y de que avisa en vez de fallar en silencio (spec sección H)

- [ ] **Step 1: Elegir 5 preguntas de prueba con respuesta conocida**

Elegir 5 preguntas técnicas cuya respuesta esté claramente en libros concretos de PROYECTO ELECTRICO (mirar los nombres de carpeta/categoría de `_INDEXADOR` para elegir temas representados de verdad — no inventar preguntas sobre temas que la biblioteca no cubre). Para cada una, hacer la pregunta real contra el Worker desplegado y comprobar:
- Que `encontradoEnLibros` es `true`.
- Que el libro citado en `fuentes` es un libro real y plausible para esa pregunta (comprobar el nombre contra la carpeta real de PROYECTO ELECTRICO, no solo que "cite algo").
- Que la respuesta de texto realmente usa esa información, no solo cita el libro de adorno.

Si alguna de las 5 falla en encontrar lo esperado, ajustar el `UMBRAL_RELEVANCIA` de `buscador_electrico.js` (Task 5) y repetir — es un valor de partida, no un número final.

- [ ] **Step 2: Prueba por mutación — contraseña**

Hacer una petición real con una contraseña incorrecta a propósito. Confirmar `403 {"error":"no_autorizado"}`, sin ninguna pista de cuál es la correcta.

- [ ] **Step 3: Prueba por mutación — índice corrupto**

Con un script de prueba (no contra el KV real de producción — usar `wrangler kv key put` **sin** `--remote`, es decir, contra el almacén local simulado, para no tocar el índice real): sobrescribir temporalmente `manifiesto` con un JSON con `numVectores` erróneo o eliminar una clave `embeddings_N`, y comprobar que el Worker responde `500 {"error":"indice_no_disponible", ...}` con el mensaje explícito, en vez de responder como si la biblioteca estuviera vacía o fallar en silencio. Confirmar después que el índice real remoto no se ha tocado (`wrangler kv key get --remote` del manifiesto real sigue devolviendo `14679`).

- [ ] **Step 4: Pregunta sin relación con ningún libro**

Preguntar algo deliberadamente ajeno a electricidad (p.ej. "¿cuál es la capital de Francia?"). Confirmar `encontradoEnLibros: false`, `fuentes: []`, y que la respuesta dice explícitamente que no viene de los libros.

- [ ] **Step 5: Comprobar la llamada real desde origen cruzado (no solo curl/Python)**

Servir `VARIOS/BUSCADOR ELECTRICO/index.html` desde un servidor local simple (`python -m http.server` en esa carpeta) y abrirlo en un navegador real — esto reproduce la petición `fetch()` cross-origin real que hará la pestaña ya publicada (origen distinto al del propio Worker), a diferencia de las pruebas anteriores por script. Confirmar que NO aparece el bloqueo `403 error code 1010` visto durante el spike — si aparece, hay que revisar la configuración de Cloudflare (Bot Fight Mode u otra regla) antes de continuar, es un hallazgo real pendiente desde `RESULTADO_SPIKE.md`.

- [ ] **Step 6: Checklist para que Bixente pruebe de verdad desde el móvil**

Esto NO lo puede hacer el ejecutor — pedir a Bixente, en el chat, que abra el fichero HTML (con la URL real, no en local) desde su móvil y compruebe:
- [ ] Con wifi de casa: hace una pregunta real y recibe respuesta.
- [ ] Sin wifi de casa (datos móviles, o wifi de una obra): hace una pregunta real y recibe respuesta.
- [ ] La contraseña, una vez metida, no hay que volver a escribirla en ese móvil.

Reportar los 3 resultados reales antes de dar esta tarea por cerrada.

---

### Task 9: Confirmar con Bixente y commitear la pestaña en Sagarde

**Files:**
- Add (en el repo de Sagarde): `VARIOS/BUSCADOR ELECTRICO/index.html`

**Interfaces:**
- Consumes: Task 7 (fichero ya escrito y probado), Task 8 (pruebas ya pasadas)

**Esta tarea NO se delega a un subagente ni se ejecuta sin supervisión — parar aquí y pedir confirmación explícita a Bixente antes de tocar el repo de Sagarde, sin excepción (spec sección K.2, regla general de esta sesión).**

- [ ] **Step 1: Mostrar a Bixente el resultado de la Task 8 y pedir confirmación explícita**

Resumir en el chat, en lenguaje sencillo: las 5 preguntas de prueba y si encontraron el libro correcto, que la contraseña incorrecta se rechaza, que un índice roto avisa en vez de fallar en silencio, y (si ya están) los 3 resultados del checklist móvil. Preguntar explícitamente: **"¿Confirmas que puedo publicar la pestaña en el repo de Sagarde?"** — no proceder sin un "sí" claro.

- [ ] **Step 2: Commit (solo tras confirmación)**

```bash
cd "COPIA SEGURIDAD SAGARDE"
git add "VARIOS/BUSCADOR ELECTRICO/index.html"
git commit -m "Añade la pestaña Buscador Eléctrico: pregunta técnica combinando IA con la biblioteca de PROYECTO ELECTRICO"
```

(**No** ejecutar `Actualizar_Sagarde.bat` ni hacer push en esta tarea salvo que Bixente lo pida explícitamente también — commitear localmente y confirmar con él antes de publicar en `main`, por si hay otro trabajo a medias en el repo que ese `.bat` publicaría de golpe — regla del propio `CLAUDE.md` de Sagarde, sección 4.)

- [ ] **Step 3: Informar del cierre**

Confirmar a Bixente que la Fase 2 está completa: indexador + Worker + pestaña, con los números reales de las Tasks 3 y 8, y qué falta (solo publicar en `main` cuando él quiera, con el `.bat` o como prefiera).
