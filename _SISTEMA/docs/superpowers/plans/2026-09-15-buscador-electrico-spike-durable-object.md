# Spike: validar búsqueda por vectores en un Durable Object gratuito — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Probar, con datos reales desplegados de verdad en Cloudflare, si un Durable Object puede cargar ~2.000 embeddings cuantizados y buscar en ellos sin salirse de los límites del plan gratuito — antes de construir el Worker completo sobre una suposición sin confirmar.

**Architecture:** Un Worker mínimo con un Durable Object (`BuscadorSpike`, backend SQLite — el único disponible en el plan gratuito) que al despertar carga un blob binario de vectores cuantizados a int8 desde **Workers KV** (no R2 — ver Global Constraints), y en cada petición HTTP calcula similitud coseno contra todos ellos y devuelve tiempos reales. Un script Python exporta el subconjunto de prueba desde el índice ya generado en la Fase 1.

**Tech Stack:** Cloudflare Workers + Durable Objects (SQLite backend) + Workers KV, JavaScript (sin frameworks), Wrangler CLI, Python 3 para el export (reutilizando `_INDEXADOR`).

## Global Constraints

- **R2 queda descartado para este proyecto: exige tarjeta.** Comprobado en vivo el 15/09/2026 (captura real del panel de Bixente): activar R2 requiere "Agregar suscripción a R2" con un método de pago registrado ("se cargará a tu método de pago registrado"; Cloudflare puede preautorizarlo), aunque el uso normal se quede en 0€. **Workers KV, comprobado también en vivo el mismo día, NO pide nada de eso** — el panel solo muestra "Crear un espacio de nombres KV" con un botón directo, sin mención de pago ni suscripción. Decisión de Bixente: usar KV, evitar la tarjeta del todo, aceptando la complejidad añadida de trocear el índice completo en fragmentos de menos de 25 MB (límite de KV por valor) cuando se implemente a escala completa — este spike, con solo 2.000 vectores (~3,9 MB), cabe en un único valor sin trocear.
- Namespace KV ya creado de verdad el 15/09/2026: `buscador_electrico_spike`, id `f354460344604744a9206fb94c7d11d4` (no es secreto, es un identificador de recurso — puede ir en `wrangler.toml` sin problema).
- Repositorio de código: `PROYECTO ELECTRICO/_WORKER/` — git local, **sin remoto, nunca debe tenerlo**, igual que `_INDEXADOR`. Nada de esto se publica en el repo de Sagarde.
- Autenticación con Cloudflare: variable de entorno de usuario de Windows `CLOUDFLARE_API_TOKEN` (ya configurada y verificada el 15/09/2026 con `wrangler whoami`). Nunca escribir su valor literal en ningún fichero ni salida.
- Durable Objects en el plan gratuito **solo admiten el backend SQLite** — usar `new_sqlite_classes` en la migración de `wrangler.toml`, nunca `new_classes` (backend antiguo, no disponible gratis).
- `nvidia/nemotron-3-embed-1b` está fijado a 2048 dimensiones — confirmado el 15/09/2026 que la API rechaza `dimensions` distinto de 2048 (`HTTP 400: dimensions must be one of 2048`). No se puede reducir sin cambiar de modelo.
- Rango real observado de valores de embedding (muestra de 200 vectores reales, 15/09/2026): min -0.130, max 0.402. La cuantización usa un rango fijo `[-0.5, 0.5]` con recorte (clamp) explícito para tener margen sobre esa muestra sin desperdiciar precisión.
- Este spike es desechable en parte (el Worker de prueba, el namespace KV de prueba) pero el script de exportación y las lecciones aprendidas alimentan directamente el plan siguiente (la implementación completa) — no tirar el código, documentar qué se reutiliza.
- Objetivo del spike: decidir con datos reales, no con suposiciones, si seguir con este diseño (Plan A) o pasar a una alternativa (Plan C: prefiltro por categoría, o Plan D: búsqueda por palabras clave en vez de vectorial) — ver sección final de este documento.

---

### Task 1: Crear el namespace KV y el repositorio del Worker

**Files:**
- Create: `PROYECTO ELECTRICO/_WORKER/` (carpeta nueva, repo git local)
- Create: `PROYECTO ELECTRICO/_WORKER/.gitignore`
- Create: `PROYECTO ELECTRICO/_WORKER/README.md`
- Create: `PROYECTO ELECTRICO/_WORKER/package.json`

**Interfaces:**
- Consumes: nada (es la base)
- Produces: namespace KV `buscador_electrico_spike` ya creado en la cuenta real de Cloudflare; carpeta de proyecto lista para el código de las siguientes tareas

- [ ] **Step 1: Crear la carpeta y el repo git local**

```bash
mkdir -p "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_WORKER/src"
cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_WORKER"
git init -q
git config user.email "sagarde@sagarde.es"
git config user.name "Sagarde"
```

- [ ] **Step 2: Escribir `.gitignore` y `README.md`**

Contenido de `.gitignore`:
```
node_modules/
.wrangler/
.dev.vars
*.bin
```

Contenido de `README.md`:
```markdown
# _WORKER (spike)

Repositorio local, sin remoto. Prueba de viabilidad del Buscador Eléctrico
con IA: ¿cabe la búsqueda por vectores en un Durable Object del plan
gratuito de Cloudflare? Nunca debe publicarse ni empujarse a ningún sitio;
vive fuera del repo de Sagarde a propósito.
```

- [ ] **Step 3: Crear `package.json`**

```json
{
  "name": "buscador-electrico-worker",
  "private": true,
  "version": "0.0.1",
  "scripts": {
    "dev": "wrangler dev",
    "deploy": "wrangler deploy"
  },
  "devDependencies": {
    "wrangler": "^4.0.0"
  }
}
```

- [ ] **Step 4: Instalar dependencias**

Run:
```bash
cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_WORKER" && npm install
```
Expected: instala `wrangler` localmente sin errores (si aparece el mismo error de caché npm corrupta que en la sesión del 15/09/2026 — `EEXIST ... sharp` —, ejecutar `npm cache clean --force` y repetir).

- [ ] **Step 5: Namespace KV — ya creado, verificar que sigue existiendo**

El namespace `buscador_electrico_spike` (id `f354460344604744a9206fb94c7d11d4`) ya se creó de verdad el 15/09/2026 contra la cuenta real. Verificar que sigue ahí:
```powershell
npx wrangler kv namespace list
```
Expected: aparece una entrada con `"title": "buscador_electrico_spike"` y `"id": "f354460344604744a9206fb94c7d11d4"`. Si por lo que sea no apareciera, crearlo de nuevo con `npx wrangler kv namespace create buscador_electrico_spike` y actualizar el id en este documento y en `wrangler.toml` (Task 4).

- [ ] **Step 6: Commit**

```bash
cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_WORKER"
git add .gitignore README.md package.json
git commit -m "Estado inicial del spike del Worker"
```

---

### Task 2: Exportar un subconjunto real de vectores cuantizados a int8

**Files:**
- Create: `PROYECTO ELECTRICO/_INDEXADOR/exportar_muestra_cuantizada.py`
- Test: `PROYECTO ELECTRICO/_INDEXADOR/tests/test_exportar_muestra_cuantizada.py`

**Interfaces:**
- Consumes: `PROYECTO ELECTRICO/_INDEXADOR/indice_biblioteca.jsonl` (14.679 fragmentos reales, ya generado en Fase 1)
- Produces: fichero binario `muestra.bin` con formato:
  - Los primeros 4 bytes: número de vectores (uint32, little-endian)
  - Después, para cada vector: 2048 bytes (int8, uno por dimensión) — sin separadores
  - `cuantizar(valor: float, minimo=-0.5, maximo=0.5) -> int` y `decuantizar(valor_int: int, minimo=-0.5, maximo=0.5) -> float` como funciones reutilizables

- [ ] **Step 1: Escribir el test (debe fallar: el módulo no existe)**

```python
# PROYECTO ELECTRICO/_INDEXADOR/tests/test_exportar_muestra_cuantizada.py
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from exportar_muestra_cuantizada import cuantizar, decuantizar, exportar_muestra


class TestCuantizacion(unittest.TestCase):
    def test_cuantizar_y_decuantizar_es_aproximadamente_reversible(self):
        for valor in [-0.5, -0.13, 0.0, 0.05, 0.4, 0.5]:
            entero = cuantizar(valor)
            recuperado = decuantizar(entero)
            self.assertAlmostEqual(valor, recuperado, delta=0.005)

    def test_cuantizar_devuelve_rango_int8(self):
        self.assertEqual(cuantizar(-0.5), -128)
        self.assertEqual(cuantizar(0.5), 127)

    def test_cuantizar_recorta_valores_fuera_de_rango(self):
        # un valor fuera del [-0.5, 0.5] esperado no debe reventar, se recorta
        self.assertEqual(cuantizar(10.0), 127)
        self.assertEqual(cuantizar(-10.0), -128)


class TestExportarMuestra(unittest.TestCase):
    def test_exporta_el_numero_pedido_de_vectores_con_formato_correcto(self):
        import tempfile
        ruta_indice_real = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "indice_biblioteca.jsonl",
        )
        with tempfile.TemporaryDirectory() as tmp:
            ruta_salida = os.path.join(tmp, "muestra.bin")
            n_exportados = exportar_muestra(ruta_indice_real, ruta_salida, n=50)
            self.assertEqual(n_exportados, 50)

            with open(ruta_salida, "rb") as f:
                contenido = f.read()

            (num_vectores,) = struct.unpack_from("<I", contenido, 0)
            self.assertEqual(num_vectores, 50)
            tamano_esperado = 4 + 50 * 2048
            self.assertEqual(len(contenido), tamano_esperado)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Ejecutar el test y comprobar que falla**

Run: `cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python -m unittest tests.test_exportar_muestra_cuantizada -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'exportar_muestra_cuantizada'`

- [ ] **Step 3: Implementar `exportar_muestra_cuantizada.py`**

```python
"""Exporta un subconjunto de vectores del indice real, cuantizados a int8,
en un formato binario compacto para el spike del Durable Object.

Formato del fichero de salida:
  - 4 bytes: numero de vectores (uint32, little-endian)
  - por cada vector: 2048 bytes int8 (uno por dimension), sin separadores

Uso:
    python exportar_muestra_cuantizada.py [n_vectores] [ruta_salida]
"""
import json
import struct
import sys

RANGO_MIN = -0.5
RANGO_MAX = 0.5
DIMENSIONES = 2048


def cuantizar(valor, minimo=RANGO_MIN, maximo=RANGO_MAX):
    valor_recortado = max(minimo, min(maximo, valor))
    normalizado = (valor_recortado - minimo) / (maximo - minimo)  # 0..1
    entero = round(normalizado * 255) - 128
    return max(-128, min(127, entero))


def decuantizar(valor_int, minimo=RANGO_MIN, maximo=RANGO_MAX):
    normalizado = (valor_int + 128) / 255
    return normalizado * (maximo - minimo) + minimo


def exportar_muestra(ruta_indice, ruta_salida, n=2000):
    vectores_exportados = 0
    with open(ruta_indice, "r", encoding="utf-8") as f_in, \
         open(ruta_salida, "wb") as f_out:
        f_out.write(struct.pack("<I", 0))  # placeholder, se corrige al final

        for linea in f_in:
            if vectores_exportados >= n:
                break
            linea = linea.strip()
            if not linea:
                continue
            fragmento = json.loads(linea)
            embedding = fragmento["embedding"]
            if len(embedding) != DIMENSIONES:
                continue
            bytes_vector = bytes(
                (cuantizar(v) + 256) % 256 for v in embedding
            )
            f_out.write(bytes_vector)
            vectores_exportados += 1

        f_out.seek(0)
        f_out.write(struct.pack("<I", vectores_exportados))

    return vectores_exportados


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    ruta_salida = sys.argv[2] if len(sys.argv) > 2 else "muestra.bin"
    ruta_indice = "indice_biblioteca.jsonl"
    total = exportar_muestra(ruta_indice, ruta_salida, n=n)
    print(f"Exportados {total} vectores a {ruta_salida}")
```

Nota sobre `bytes((cuantizar(v) + 256) % 256 for v in embedding)`: `cuantizar` devuelve un entero con signo en `[-128, 127]`; `bytes()` de Python exige valores `0..255`, así que `(x + 256) % 256` convierte el int8 con signo a su representación sin signo de un byte (equivalente a `struct.pack("b", x)` pero más directo para un generador).

- [ ] **Step 4: Ejecutar el test y comprobar que pasa**

Run: `cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python -m unittest tests.test_exportar_muestra_cuantizada -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Generar la muestra real de 2.000 vectores**

Run:
```bash
cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR" && python exportar_muestra_cuantizada.py 2000 muestra.bin
```
Expected: `Exportados 2000 vectores a muestra.bin`. Comprobar el tamaño real:
```bash
ls -la "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR/muestra.bin"
```
Expected: tamaño = 4 + 2000×2048 = 4.096.004 bytes (~3.9 MB).

- [ ] **Step 6: Añadir `*.bin` al `.gitignore` de `_INDEXADOR`**

`muestra.bin` es un dato generado, no código — igual que `indice_biblioteca.jsonl` — pero `.bin` no estaba cubierto todavía por el `.gitignore` existente (`*.jsonl`, `*.jsonl.*`, `*.pdf`, `.indexacion_en_curso.lock`, `__pycache__/`, `*.pyc`). Añadir una línea nueva `*.bin` al final de ese fichero.

- [ ] **Step 7: Commit**

```bash
cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_INDEXADOR"
git add exportar_muestra_cuantizada.py tests/test_exportar_muestra_cuantizada.py .gitignore
git commit -m "Añade exportador de muestra cuantizada a int8 para el spike de Durable Object"
```

---

### Task 3: Subir la muestra al namespace KV

**Files:**
- Ninguno (operación directa con Wrangler, sin código nuevo)

**Interfaces:**
- Consumes: `PROYECTO ELECTRICO/_INDEXADOR/muestra.bin` (Task 2)
- Produces: valor con clave `muestra` disponible en el namespace KV `buscador_electrico_spike` (id `f354460344604744a9206fb94c7d11d4`)

- [ ] **Step 1: Subir el fichero**

Run:
```powershell
cd "D:\Nueva carpeta\OneDrive\PROYECTO ELECTRICO\_WORKER"
npx wrangler kv key put --namespace-id=f354460344604744a9206fb94c7d11d4 "muestra" --path="D:\Nueva carpeta\OneDrive\PROYECTO ELECTRICO\_INDEXADOR\muestra.bin"
```
Expected: confirmación de subida correcta. `muestra.bin` (4.096.004 bytes) está comodamente por debajo del límite de 25 MB por valor de KV, así que no hace falta trocearlo para este spike.

- [ ] **Step 2: Verificar que está ahí**

Run:
```powershell
npx wrangler kv key get --namespace-id=f354460344604744a9206fb94c7d11d4 "muestra" > "D:\Nueva carpeta\OneDrive\PROYECTO ELECTRICO\_WORKER\verificacion_descarga.bin"
```
Expected: descarga sin error. Comparar tamaño con el original (deben coincidir, o muy cercano — `kv key get` sin `--text` devuelve el binario tal cual) y luego borrar `verificacion_descarga.bin` (es solo de prueba, no forma parte del proyecto).

---

### Task 4: Durable Object que carga la muestra y mide su propio rendimiento

**Files:**
- Create: `PROYECTO ELECTRICO/_WORKER/src/buscador_spike.js`
- Create: `PROYECTO ELECTRICO/_WORKER/src/index.js`
- Create: `PROYECTO ELECTRICO/_WORKER/wrangler.toml`

**Interfaces:**
- Consumes: valor KV `muestra` (Task 3), binding `INDICE_KV` declarado en `wrangler.toml`
- Produces: endpoint HTTP `GET /` que devuelve JSON con tiempos reales de carga y búsqueda

- [ ] **Step 1: Escribir `wrangler.toml`**

```toml
name = "buscador-electrico-spike"
main = "src/index.js"
compatibility_date = "2026-09-15"

[[kv_namespaces]]
binding = "INDICE_KV"
id = "f354460344604744a9206fb94c7d11d4"

[[durable_objects.bindings]]
name = "BUSCADOR_SPIKE"
class_name = "BuscadorSpike"

[[migrations]]
tag = "v1"
new_sqlite_classes = ["BuscadorSpike"]
```

- [ ] **Step 2: Escribir `src/buscador_spike.js`**

```javascript
const DIMENSIONES = 2048;
const RANGO_MIN = -0.5;
const RANGO_MAX = 0.5;

function decuantizar(valorInt8) {
  const normalizado = (valorInt8 + 128) / 255;
  return normalizado * (RANGO_MAX - RANGO_MIN) + RANGO_MIN;
}

function similitudCoseno(a, b) {
  let producto = 0;
  let normaA = 0;
  let normaB = 0;
  for (let i = 0; i < a.length; i++) {
    producto += a[i] * b[i];
    normaA += a[i] * a[i];
    normaB += b[i] * b[i];
  }
  return producto / (Math.sqrt(normaA) * Math.sqrt(normaB));
}

export class BuscadorSpike {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.vectores = null; // Float32Array[], se carga de forma perezosa
    this.numVectores = 0;
    this.msCarga = null;
  }

  async cargarSiHaceFalta() {
    if (this.vectores !== null) {
      return false; // ya estaba cargado, no hubo que recargar
    }
    const inicio = Date.now();
    const buffer = await this.env.INDICE_KV.get("muestra", "arrayBuffer");
    if (!buffer) {
      throw new Error("clave 'muestra' no encontrada en el namespace KV");
    }
    const vista = new DataView(buffer);
    this.numVectores = vista.getUint32(0, true);

    this.vectores = new Array(this.numVectores);
    let cursor = 4;
    const bytesInt8 = new Int8Array(buffer, cursor);
    for (let i = 0; i < this.numVectores; i++) {
      const vectorFloat = new Float32Array(DIMENSIONES);
      const base = i * DIMENSIONES;
      for (let d = 0; d < DIMENSIONES; d++) {
        vectorFloat[d] = decuantizar(bytesInt8[base + d]);
      }
      this.vectores[i] = vectorFloat;
    }
    this.msCarga = Date.now() - inicio;
    return true; // se cargo de verdad en esta peticion
  }

  async fetch(request) {
    const seCargoAhora = await this.cargarSiHaceFalta();

    const inicioBusqueda = Date.now();
    // vector de consulta de prueba: el primero de la propia muestra
    // (solo para medir tiempos, no busca nada semanticamente real todavia)
    const consulta = this.vectores[0];
    let mejorIndice = -1;
    let mejorPuntuacion = -Infinity;
    for (let i = 1; i < this.vectores.length; i++) {
      const puntuacion = similitudCoseno(consulta, this.vectores[i]);
      if (puntuacion > mejorPuntuacion) {
        mejorPuntuacion = puntuacion;
        mejorIndice = i;
      }
    }
    const msBusqueda = Date.now() - inicioBusqueda;

    return new Response(
      JSON.stringify({
        seCargoEnEstaPeticion: seCargoAhora,
        numVectores: this.numVectores,
        msCargaPrimeraVez: this.msCarga,
        msBusquedaEstaPeticion: msBusqueda,
        mejorIndiceEncontrado: mejorIndice,
        mejorPuntuacion: mejorPuntuacion,
      }),
      { headers: { "content-type": "application/json" } }
    );
  }
}
```

- [ ] **Step 3: Escribir `src/index.js`**

```javascript
export { BuscadorSpike } from "./buscador_spike.js";

export default {
  async fetch(request, env) {
    const id = env.BUSCADOR_SPIKE.idFromName("unico");
    const stub = env.BUSCADOR_SPIKE.get(id);
    return stub.fetch(request);
  },
};
```

- [ ] **Step 4: Commit**

```bash
cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_WORKER"
git add wrangler.toml src/buscador_spike.js src/index.js
git commit -m "Añade Durable Object del spike: carga muestra cuantizada y mide tiempos reales"
```

---

### Task 5: Desplegar de verdad y medir contra Cloudflare real

**Files:**
- Ninguno (despliegue y verificación, no código nuevo)

**Interfaces:**
- Consumes: todo lo anterior
- Produces: decisión GO/NO-GO documentada en `PROYECTO ELECTRICO/_WORKER/RESULTADO_SPIKE.md`

- [ ] **Step 1: Desplegar**

Run (con `CLOUDFLARE_API_TOKEN` en el entorno, igual que en Task 1):
```powershell
cd "D:\Nueva carpeta\OneDrive\PROYECTO ELECTRICO\_WORKER"
npx wrangler deploy
```
Expected: despliegue correcto, Wrangler imprime la URL pública del Worker (algo como `https://buscador-electrico-spike.<subdominio>.workers.dev`).

- [ ] **Step 2: Llamar al endpoint varias veces y registrar los resultados reales**

Run (repetir 5 veces seguidas, con la URL real que haya dado el Step 1):
```powershell
1..5 | ForEach-Object {
    Invoke-RestMethod -Uri "https://buscador-electrico-spike.<TU-SUBDOMINIO>.workers.dev/" -Method Get | ConvertTo-Json
    Start-Sleep -Seconds 1
}
```
Expected: 5 respuestas JSON. La primera debería traer `seCargoEnEstaPeticion: true` y un `msCargaPrimeraVez` real (puede ser varios segundos, no hay límite estricto de duración para I/O). Las siguientes, si el Durable Object sigue "despierto", deberían traer `seCargoEnEstaPeticion: false` y un `msBusquedaEstaPeticion` bajo (unos pocos milisegundos, al ser solo 2.000 vectores ya en memoria).

**Comprobar explícitamente que NINGUNA respuesta es un error de límite excedido** (mensajes tipo "Exceeded CPU Limit" o similares) — si aparece alguno, es la señal de que el Plan A no es viable tal cual y hay que pasar al Plan C o D (ver más abajo).

- [ ] **Step 3: Revisar el panel de Cloudflare**

Ir a `dash.cloudflare.com` → Workers & Pages → `buscador-electrico-spike` → pestaña de métricas/Observability. Comprobar que no hay errores marcados ni avisos de límite alcanzado tras las llamadas del Step 2.

- [ ] **Step 4: Escribir `RESULTADO_SPIKE.md` con la decisión**

Contenido (rellenar con los datos reales del Step 2/3, no estos de ejemplo):

```markdown
# Resultado del spike — Durable Object para búsqueda vectorial

Fecha: [fecha real]

- Vectores en la muestra: 2.000 (de 14.679 reales)
- Tiempo de primera carga (peticion 1): [N] ms
- Tiempo de búsqueda en peticiones siguientes: [N] ms (promedio de peticiones 2-5)
- ¿Algún error de límite excedido?: [sí/no, con el mensaje exacto si lo hubo]
- ¿El Durable Object se mantuvo "despierto" entre peticiones con 1s de espera?: [sí/no]

## Decisión

[GO: seguir con el Plan A a escala completa (14.679 vectores, ~30 MB
cuantizados) en el siguiente plan de implementación / NO-GO: pasar al
Plan C (prefiltro por categoría antes de la búsqueda vectorial) o Plan D
(búsqueda por palabras clave en vez de vectorial) — justificar con los
números de arriba].

## Si es NO-GO, qué probar después (no implementado en este spike)

- **Plan C — prefiltro por categoría:** antes de la búsqueda vectorial,
  reducir el conjunto a una sola categoría (de las 9 que ya existen:
  01_FUNDAMENTOS Y TEORIA, 02_INSTALACIONES ELECTRICAS...) usando
  coincidencia de palabras clave simple entre la pregunta y el nombre de
  categoría/libro, y solo entonces cargar y buscar por vectores dentro de
  ese subconjunto más pequeño. Menor calidad (podría no cruzar categorías
  cuando debería), pero evita cargar los 14.679 vectores de golpe.
- **Plan D — búsqueda por palabras clave, sin vectores en el Worker:**
  abandonar la búsqueda semántica en tiempo de petición. El índice ya
  generado en Fase 1 seguiría existiendo (por si se retoma Plan A/C más
  adelante), pero el Worker buscaría por coincidencia de palabras/frases
  contra el texto de los fragmentos (algo tipo BM25 simplificado), mucho
  más barato en CPU. Pierde la ventaja de encontrar contenido
  relacionado con otras palabras (sinónimos, conceptos), gana en
  sencillez y en encajar de sobra en el límite gratuito.
```

- [ ] **Step 5: Commit**

```bash
cd "/d/Nueva carpeta/OneDrive/PROYECTO ELECTRICO/_WORKER"
git add RESULTADO_SPIKE.md
git commit -m "Registra el resultado real del spike de Durable Object (GO/NO-GO)"
```

---

## Qué sigue después de este plan

Con `RESULTADO_SPIKE.md` en la mano:

- **Si GO:** escribir el plan de implementación completa (Durable Object a
  escala real con los 14.679 vectores, búsqueda semántica de verdad,
  cliente NVIDIA en JavaScript, Worker con autenticación por contraseña,
  manejo de errores de la sección G de la spec, y finalmente la pestaña
  HTML en `VARIOS/BUSCADOR ELECTRICO/` dentro del repo de Sagarde — ese
  último paso requiere confirmación explícita de Bixente antes de
  commitear, spec sección K.2).
- **Si NO-GO:** decidir con Bixente entre Plan C y Plan D antes de seguir
  — no es una decisión puramente técnica (afecta a la calidad de las
  respuestas), así que no se elige unilateralmente aunque ambas sean
  gratuitas.

No escribir ese plan siguiente todavía — depende del resultado real de este spike.
