# Base de datos de obras Sagarde — Diseño

**Fecha:** 27/07/2026
**Estado:** aprobado para implementar
**Alcance:** mínimo invasivo + limpieza de duplicados

---

## 1. Problema

El entorno Sagarde no puede responder preguntas puntuales sobre una obra
("¿está cableada la vivienda B del 2º del portal 3?") ni generar una hoja de
revisión para llevar a campo sabiendo cómo está la obra. La causa no es que
falte una base de datos: es que **la estructura de la obra no es un dato
almacenado, sino un efecto secundario de las revisiones**.

### 1.1 La estructura se infiere, no se declara

En `generar_todos.py`, la función `crear_registro_revision()` construye el
edificio como la unión de las tuplas `(edificio, planta, unidad)` que aparecen
en `prioridades_trabajos.json → detalle_items`:

```python
if edificio and planta and unidad and unidad not in {'—', '-'}:
    ubicaciones.setdefault(edificio, {}).setdefault(planta, set()).add(unidad)
```

Consecuencia: **si una ubicación nunca se marcó en una revisión, no existe**.

Caso real verificado en Mungia, portal ZR1.2: la planta 1 registra `A2` y `B3`,
mientras las plantas 2 a 5 registran `A2`, `B3` y `C3`. La C3 de la planta 1 no
falta porque el piso no exista, sino porque nunca se rellenó esa celda. El
sistema lo resolvió parcheándolo a mano dentro de `adaptador_mungia.py`
("descarte de la vivienda fantasma planta 1-C", documentado en la Hoja de Ruta).
**La verdad estructural de la obra vive hoy como una condición en código Python.**

### 1.2 El pez que se muerde la cola

`obras_revisiones.js` registra este error:

```
"errores":["2026 GORLIZ HOSPITAL: sin detalle de viviendas"]
```

Gorliz no puede generar hoja de campo porque no tiene revisiones, y no tendrá
revisiones hasta que alguien lleve una hoja al campo.

### 1.3 Solo se persiste el último snapshot, y filtrado

```python
if ids and tarea_id and unidad and estado in {'X', 'M', '/'}:
```

De las 2318 celdas de Mungia se guardan 1841 y se descartan 477 "Pendiente".
Los estados `N` (no aplica) se descartan antes. El sistema no puede distinguir
entre: pendiente de hacer / no aplica / nunca comprobado / no existe. Las cuatro
son ausencia.

### 1.4 Representaciones duplicadas

| Concepto | Dónde vive | Nº |
|---|---|---|
| Catálogo de tajos | `reglas/CATALOGO_TAJOS.json` (con `deps`, `fase`, `impacto`) | 39 |
| Catálogo de tajos | `TAJO_NOMBRE` copiado en cada adaptador | ~38 |
| Catálogo de tajos | `catalog` derivado en `obras_revisiones.js` | 38 |
| Registro de obras | `OBRAS` en `generar_todos.py` | 5 |
| Registro de obras | `ADAPTADORES` en `generar_informe_ejecutivo.py` | 5 |
| Formato de clave | `p1__pb__mecanizado__A2` (JSON, correcciones) | — |
| Formato de clave | `src_gernika_p1__src_gernika_p1_f1__tabicado__A` (HTML) | — |

---

## 2. Objetivo

El ciclo de trabajo a conseguir:

```
   CASA/OFICINA                    OBRA (tablet)              CASA/OFICINA
1. Meto archivos nuevos      3. Abro y veo el estado      5. Digitalizo la hoja
2. Un comando:                  exacto de ayer:              → la base absorbe
   · base actualizada           portal/planta/viv/tajo         SOLO los cambios
   · git push                4. Pinto a boli sobre el      6. git push → vuelta a 3
                                PDF de la última revisión
```

Propiedad crítica: **la hoja que se lleva a campo la genera la base, no un
documento**.

Frecuencia real de trabajo: ~2 pases por semana; pocos cambios entre revisiones.
Esto hace viable que el digitalizador solo busque diferencias y que las
anomalías se supervisen una a una.

---

## 3. Decisiones tomadas

| Decisión | Elegido | Motivo |
|---|---|---|
| Alcance | Mínimo invasivo + limpiar duplicados | No romper lo que funciona |
| Almacenamiento | `ficha_obra.json` por obra + bundle publicado | La tablet lee del sitio publicado; git muestra cada cambio línea a línea; SQLite binario rompería ambas cosas |
| Ubicación | `{obra}/INFORME SAGARDE IA/ficha_obra.json` | Junto a los JSON que ya existen |
| Granularidad temporal | Último valor + fecha | Lo pedido; sin historial completo por celda |
| Sin dato | Distinguir `P` (pendiente) de `?` (desconocido) | "Comprobado que no" ≠ "nadie lo ha mirado" |
| No aplica | Guardar `N` explícito | Hoy se descarta y ensucia porcentajes |
| Formato de clave | Mantener `portal__planta__tajo__unidad` | Cambiarlo rompería los `revision_*.json` y `correcciones.json` existentes |
| Apartados | Todos, bien estructurados | Cada uno con su propio `_meta.actualizado` |

### 3.1 Estados

Lo que se escribe en papel no cambia. Lo que se **guarda** gana tres valores:

| Guardado | Significa | En la hoja |
|---|---|---|
| `X` | Terminado | X |
| `M` | Más del 50% | M |
| `/` | Iniciado | / |
| `P` | Pendiente confirmado (se comprobó, no está hecho) | casilla vacía |
| `?` | Desconocido (nunca comprobado) | no se imprime como vacío |
| `N` | No aplica a esa ubicación | no se imprime |

**No se guardan `BLOQUEADO`, `DUDAS`, `VIABLE` ni `OTROS_GREMIOS`.** Son
categorías que calcula `priorizador_trabajos.py` a partir de las dependencias.
Persistirlas congelaría un dato que caduca al día siguiente.

> **Regla:** la base guarda solo lo **medido en campo**. Lo **derivado** se
> recalcula al vuelo. Nunca se persiste lo que se puede recalcular.

### 3.2 Procedencia de cada ubicación

La tensión entre proyecto y realidad ("en proyecto es una cosa y luego en la
realidad otra aunque se le parezca mucho") se resuelve marcando cada ubicación
con su origen, en vez de eligiendo entre declarar o inferir:

- `origen: "proyecto"` — deducida de presupuestos, partidas o planos. Hipótesis.
- `origen: "campo"` — confirmada por una revisión real, con fecha.

La obra nace del proyecto y se corrige sola conforme las revisiones confirman
la realidad. Nada muta en silencio.

---

## 4. Modelo de datos

```json
{
  "version": 1,
  "id": "mungia",
  "modo": "hibrida",
  "fecha_entrada_digital": "01/08/2026",
  "actualizado": "27/07/2026 16:00",

  "identidad": {
    "nombre": "2026 MUNGIA ACR NEINOR",
    "carpeta": "2026 MUNGIA ACR NEINOR",
    "tipo_obra": "viviendas",
    "promotora": "NEINOR",
    "constructora": "ACR",
    "_meta": { "actualizado": "27/07/2026", "origen": "manual" }
  },

  "estructura": {
    "bloques": [{
      "id": "b1", "nombre": "ZR1",
      "portales": [{
        "id": "p2", "nombre": "ZR1.2", "referencia": "ZR1.2",
        "plantas": [{
          "id": "1", "nombre": "1", "orden": 1,
          "ubicaciones": [
            { "id": "A2", "tipo": "vivienda", "origen": "campo",
              "confirmado": "27/07/2026" },
            { "id": "C3", "tipo": "vivienda", "origen": "proyecto",
              "confirmado": null,
              "nota": "Hueco detectado: existe en 4 de 6 plantas tipo" }
          ]
        }]
      }]
    }],
    "_meta": { "actualizado": "27/07/2026" }
  },

  "tajos": {
    "plantilla": "viviendas_v1",
    "aplicables": ["tabicado", "rozas", "..."],
    "excepciones": [],
    "_meta": { "actualizado": "27/07/2026" }
  },

  "estados": {
    "p2__1__cableado__A2": { "v": "X", "f": "27/07/2026", "r": "rev_27072026" },
    "p2__1__cableado__C3": { "v": "?", "f": null, "r": null }
  },

  "revisiones": [
    { "id": "rev_27072026", "fecha": "27/07/2026",
      "fuente": "REVISION MUNGIA 27072026.pdf", "cambios": 50 }
  ],

  "dudas": [], "materiales": {}, "documentos": {}, "contactos": []
}
```

### 4.1 Modos de obra

| Modo | Significa | Obras |
|---|---|---|
| `nativa` | Nace y evoluciona en la base | Gorliz, Amurrio, Berango |
| `hibrida` | Sembrada desde datos existentes, continúa en la base | Mungia, Gernika, Bolueta |
| `legado` | Sigue con adaptadores hasta cerrar | Obispo Orueta |
| `cerrada` | Entregada, solo postventa | Urduliz |
| — | Fuera del modelo matriz ubicación×tajo | Megapark (solo cuadros y papeleo) |

Cada consumidor (`generar_todos.py`, panel, informes) lee `modo` y se comporta
en consecuencia. Una obra sin ficha se comporta exactamente como hoy.

### 4.2 Requisito de extensibilidad

Mungia y Gernika incorporarán **garajes** en el futuro. La ficha debe admitir
añadir un grupo de ubicaciones nuevo **sin invalidar ningún estado ya
guardado**. Hoy esto rompe el sistema: los garajes aparecerían en una hoja y la
estructura mutaría en silencio.

---

## 5. Flujo de datos

```
HOY
  revisiones ──[infiere estructura]──> obras_revisiones.js ──> generador
                                                  ↑
                                     (sin revisión no hay obra → Gorliz)

DISEÑADO
                    ┌──> obras_revisiones.js ──> generador ──> hoja PDF
  ficha_obra.json ──┤                                              │
    (LA FUENTE)     └──> priorizador ──> panel · informes          │
         ↑                                                          ▼
         └────────── Digitalizador <──── PDF pintado a boli ────────┘
```

**Cambio de papel de los componentes existentes:**

| Componente | Hoy | Diseñado |
|---|---|---|
| Adaptadores | Construyen el modelo de la obra | Solo leen estados |
| `lector_hoja_tajos_pdf.py` | Interpreta 2318 celdas a ciegas | Valida ~50 diferencias contra estado conocido |
| `crear_registro_revision()` | Infiere la estructura | Lee la estructura de la ficha |
| `obras_revisiones.js` | Fuente de facto | Bundle derivado y publicable |

---

## 6. Plan por fases

| # | Paso | Criterio de aceptación |
|---|---|---|
| 1 | Esquema + sembrar ficha de **Mungia** | 67 ubicaciones y 2546 celdas; los huecos detectados se revisan y confirman uno a uno |
| 2 | `generar_todos.py` lee la ficha si existe | **Mungia da porcentaje idéntico al actual.** Sin ficha → comportamiento actual sin cambios |
| 3 | El generador consume la ficha | Hoja de Mungia con estructura correcta y estados del día anterior |
| 4 | Digitalizador escribe deltas | Una revisión nueva solo toca las celdas cambiadas |
| 5 | Alta de obra nueva + lector de carpeta | **Gorliz genera su primera hoja sin ninguna revisión previa** |
| 6 | Gernika y Bolueta; garajes | Ídem paso 2 para cada una |
| 7 | Limpiar duplicados | Un solo catálogo, un solo registro de obras, un solo formato de clave |

El paso 2 es la red de seguridad: si Mungia no reproduce exactamente su
porcentaje actual, el diseño está mal y se detecta de inmediato.

---

## 7. Validación ya realizada

Se sembró la ficha real de Mungia desde los datos existentes (prototipo):

```
portales: 3 · plantas: 20 · ubicaciones: 67 · tajos: 38 · celdas: 2546
estados: X=1789  P=477  M=50  /=2  ?=228
```

El sembrador detectó 6 huecos estructurales que requieren confirmación humana,
**incluida la "vivienda fantasma" que estaba parcheada a mano en el adaptador**:

```
ZR1.1 planta 4 -> hay A2,B2,C3, pero FALTA C2 (existe en 3 de 6 plantas tipo)
ZR1.1 planta 5 -> hay A2,B2,C3, pero FALTA C2
ZR1.1 planta 6 -> hay A2,B2,   pero FALTA C2
ZR1.2 planta 1 -> hay A2,B3,   pero FALTA C3 (existe en 4 de 6)   ← la fantasma
ZR1.2 planta 6 -> hay A2,B2,   pero FALTA B3 (existe en 5 de 6)
ZR1.2 planta 6 -> hay A2,B2,   pero FALTA C3 (existe en 4 de 6)
```

La consulta que motivó el proyecto quedó resuelta:

```
p3__2__cableado__B  ->  { "v": "X", "f": "27/07/2026", "r": "rev_27072026" }
```

### 7.1 Limitación detectada en el prototipo

El sembrador dedujo el `tipo` de cada ubicación a partir del `ambito` del tajo,
y son propiedades ortogonales: una vivienda quedó etiquetada `zona_comun`. **El
tipo de ubicación debe declararse, no deducirse.** Refuerza que la ficha
sembrada requiere validación humana antes de sellarse.

---

## 8. Fuera de alcance

- Historial completo por celda (se guarda último valor + fecha).
- Reescribir adaptadores, priorizador, panel o informes.
- Cambiar el formato de clave de celda.
- Lectura automática de planos PDF para deducir estructura.
- Megapark y obras que no siguen el modelo matriz ubicación × tajo.
- Las 14 obras dormidas, hasta que les toque su primera hoja.
