# Auditoría del sistema de actualización de revisiones — Fase 0

Fecha de verificación: 25/08/2026. Alcance: repositorio SAGARDE, excluyendo por instrucción `_SISTEMA/MOTOR/`. Auditoría de solo lectura salvo por este entregable.

## 1. Confirmaciones y desviaciones del contexto previo

| Afirmación auditada | Estado | Evidencia actual y observaciones |
|---|---|---|
| `generador_revisiones.html` es una única app que exporta PDF y HTML desde el mismo estado editado. | **confirmado** | La celda se genera con `data-k`/`data-st` en `generador_revisiones.html:1076-1080`; el mismo DOM cicla `'' → / → M → X` y se autoguarda en `generador_revisiones.html:1173-1190`. `doSave()` serializa `document.documentElement.outerHTML` en `generador_revisiones.html:1191-1203`; `printRevision()` llama a `window.print()` en `generador_revisiones.html:1205-1208`. No ha cambiado respecto del diseño. |
| `leer_hoja_marcada.py` es un escritor directo de la ficha para tinta (`--preparar`/`--aplicar`) y PDF digital (`--digital`). | **confirmado, con precisión de fase** | Los flags actuales están en `leer_hoja_marcada.py:568-586`. En digital, la simulación termina antes de escribir (`:621-623`) y `--escribir` acaba en `fichas.guardar(...)` (`:625-650`). En tinta, `--preparar` solo produce candidatas/recortes (`:655-683`); la ficha se escribe únicamente después de `--aplicar ... --escribir` (`:685-765`). Por tanto, `--preparar` por sí solo **no** escribe `ficha_obra.json`. |
| `generar_todos.py` es el segundo escritor: obtiene el historial del adaptador y llama a `fichas.actualizar_desde_snapshot()` alrededor de la línea 902. | **confirmado** | Importa `ficha_obra as fichas` y `OBRAS` en `generar_todos.py:37-38`; carga dinámicamente el módulo y ejecuta `adaptador.cargar_historial()` en `:841-850`; llama exactamente a `fichas.actualizar_desde_snapshot()` en `:900-906` y persiste mediante `fichas.guardar()` en `:907-910`. La línea indicada sigue siendo la 902. |
| Gernika fusiona JSON legado y HTML; el HTML se lee con `lector_hoja_tajos_html.py` por `data-k`/`data-st` y gana si coincide la fecha. | **confirmado** | `adaptador_gernika.py` importa el lector en `:38` y llama a `listar_revisiones_html()` en `:155-162`. `cargar_historial()` declara y ejecuta la fusión JSON/HTML en `:220-265`; la precedencia del HTML está documentada en `:226-227` y aplicada en `:253-259`. El lector extrae los atributos mediante regex en `lector_hoja_tajos_html.py:40-44` y los normaliza en `:47-88`. |
| La skill `sagarde-revision` documenta tinta y `--digital`, pero no el camino de ingestión HTML. | **confirmado, con matiz literal** | El flujo de tinta está en `.claude/skills/sagarde-revision/SKILL.md:50-69` y el flujo PDF digital en `:73-89`. La skill **sí menciona** el `.html` gemelo como señal en `:21-26` y `:131-133`, pero no menciona `lector_hoja_tajos_html`, `parsear_html` ni `listar_revisiones_html`, ni explica que el adaptador de Gernika ingiera ese HTML. Es correcto decir que falta el *camino HTML*, no que no aparezca la palabra/formato HTML. |

La afirmación de “dos escritores” queda confirmada para **actualizaciones procedentes de revisiones**. No debe generalizarse a toda creación de fichas: `alta_obra_desde_hoja.py:408-418` crea el `ficha_obra.json` inicial, pero no es una tercera vía de actualización de una revisión existente. El escritor común final es `ficha_obra.guardar()` (`ficha_obra.py:98-103`).

## 2. Adaptadores y enganche real

`generar_todos.py` no contiene el nombre literal de ninguno de los siete módulos. Importa `OBRAS` (`generar_todos.py:38`) y ejecuta `__import__(obra['adaptador'])` (`:841-850`); por ello el criterio de actividad real es la presencia del módulo en `registro_obras.OBRAS`.

| Adaptador existente | Punto de entrada | Nombre literal en `generar_todos.py` | Presente en `registro_obras.OBRAS` | Uso real por `generar_todos.py` |
|---|---:|---|---|---|
| `adaptador_bolueta` | `adaptador_bolueta.py:395` | No; carga dinámica | Sí, `registro_obras.py:34-39` | **Activo** |
| `adaptador_egurrola` | `adaptador_egurrola.py:188` | No; carga dinámica | No | **No enganchado** |
| `adaptador_gernika` | `adaptador_gernika.py:220` | No; carga dinámica | Sí, `registro_obras.py:11-17` | **Activo** |
| `adaptador_gorliz` | `adaptador_gorliz.py:285` | No; carga dinámica | Sí, `registro_obras.py:46-51` | **Activo** |
| `adaptador_mungia` | `adaptador_mungia.py:311` | No; carga dinámica | Sí, `registro_obras.py:23-28` | **Activo** |
| `adaptador_prueba` | `adaptador_prueba.py:53` | No; carga dinámica | Sí, `registro_obras.py:58-69` | **Activo** (obra de pruebas) |
| `adaptador_zorrozaure` | `adaptador_zorrozaure.py:163` | No; carga dinámica | No | **No enganchado** |

Resultado: la fila A07 de `_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md:287` está **confirmada**: hay siete módulos, cinco activos y dos sin uso. Los no enganchados son `adaptador_egurrola` y `adaptador_zorrozaure`.

## 3. Llamadores de las funciones y entradas auditadas

La búsqueda fue global, con exclusión de `_SISTEMA/MOTOR/`. Se separan llamadas ejecutables de ejemplos históricos en documentación. El conteo de pruebas directas se hizo por caso `test_*` que contiene una llamada al símbolo; no se duplica `actualizar()` por el hecho de que el wrapper de snapshot lo invoque internamente.

| Función o entrada | Llamadores ejecutables actuales | Invocaciones documentadas | Pruebas que la ejercitan directamente |
|---|---|---|---:|
| `ficha_obra.actualizar()` (nombre real; definición en `ficha_obra.py:437`) | En producción solo la llama internamente `actualizar_desde_snapshot()` en `ficha_obra.py:388-434` (llamada en `:433`). No hay llamada directa desde `generar_todos.py` ni desde `leer_hoja_marcada.py`. | Ejemplos/planes, no runtime: `_SISTEMA/docs/superpowers/plans/2026-07-27-ficha-obra-base-viva.md:218-417` y `2026-07-27-fase-A-inversion-del-flujo.md:101`. | **36**, todas en `tests/test_ficha_obra.py` (`:34-528`). |
| `ficha_obra.actualizar_desde_snapshot()` (definición en `ficha_obra.py:388`) | `generar_todos.py:902`; después guarda en `:910`. | Diseño actual en `_SISTEMA/docs/superpowers/specs/2026-08-25-unificacion-revisiones-design.md:52`; plan histórico en `_SISTEMA/docs/superpowers/plans/2026-07-27-fase-A-inversion-del-flujo.md:277-312,459`. | **8**, en `tests/test_ficha_obra.py:380-419,651-715`. |
| CLI `leer_hoja_marcada.py` (`main()` en `leer_hoja_marcada.py:562-771`) | No hay llamador Python de producción: se ejecuta como CLI externa. | Comandos en `leer_hoja_marcada.py:53-55`, `CLAUDE.md:269-271`, `.claude/skills/sagarde-revision/SKILL.md:56-64,83-86` y `_SISTEMA/docs/superpowers/plans/2026-08-07-jerarquia-sistema-entorno.md:1464`. | **0** invocaciones CLI/subprocess. `tests/test_leer_hoja_marcada.py:16` importa el módulo como `lector` y sus **28** casos (`:38-299`) ejercitan funciones puras de tinta, claves y digital. |
| `lector_hoja_tajos_html.parsear_html()` (definición en `lector_hoja_tajos_html.py:47`) | `listar_revisiones_html()` lo llama en `lector_hoja_tajos_html.py:129-133`. No hay otro llamador. | Solo menciones descriptivas en el diseño auditado; no hay comando independiente. | **0**. |
| `lector_hoja_tajos_html.listar_revisiones_html()` (definición en `lector_hoja_tajos_html.py:106`) | `adaptadores/adaptador_gernika.py:155-162`. No hay otro adaptador conectado al lector HTML. | Solo menciones descriptivas en el diseño auditado. | **0**. |

Conclusión de cobertura de llamadores: la cadena HTML viva es única: `adaptador_gernika.cargar_historial()` → `listar_revisiones_html()` → `parsear_html()`. No existe ninguna prueba directa del último tramo.

## 4. Reglas existentes que debe reutilizar la futura Capa de Validación

### Alfabeto de estados

- `ficha_obra.py:59-71` define `MAPA_ESTADO`: `x → X`, `m → M`, `/ → /`, `pendiente`/`p`/cadena vacía → `P`, y `n → N`; la normalización previa está en `:130-133`.
- Un valor no reconocido cae a `?` durante la actualización (`ficha_obra.py:498-505`). Por tanto, `?` forma parte del estado almacenado, pero **no** es una entrada explícita de `MAPA_ESTADO`.
- La distinción semántica existente es esencial: `P` significa pendiente confirmado, `?` no revisado y `N` no aplicable. La futura capa debe importar/centralizar esta semántica, no reconstruir otro mapa.

### “Blanco no baja un estado conocido”

- En el camino snapshot, `ficha_obra.actualizar()` conserva cualquier estado previo cuando `estado_norm` está vacío (`ficha_obra.py:507-516`); un `Pendiente` explícito sí puede bajar el estado.
- En tinta, `marcar_no_empezados()` solo convierte `? → P` y conserva `X`, `M`, `/`, `P` y `N` (`leer_hoja_marcada.py:485-510`).
- La regla está probada, entre otros, por `tests/test_ficha_obra.py:72-131`; hoy aparece implementada en más de un punto y debe converger sin cambiar su significado.

### “Sin tinta no hay cambio”

- El principio está declarado en `leer_hoja_marcada.py:8-13`; `preparar()` solo crea candidatas a partir de trazos asignados a celdas (`:242-328`).
- `aplicar()` aborta si la clasificación contiene una clave que no estaba entre las candidatas con tinta (`leer_hoja_marcada.py:513-526`) y exige resolver cada candidata (`:515-521`).
- En el flujo digital equivalente, una celda sin marca impresa no se toca (`aplicar_digital()`, `:460-480`). La guarda de tinta está cubierta específicamente por `tests/test_leer_hoja_marcada.py:62-87`.

### `CATALOGO_TAJOS.json`

- `reglas/CATALOGO_TAJOS.json:2-17` es el catálogo central versión **1.3**; declara descripción, semántica resumida de estados, orden de inventario y la lista canónica.
- Contiene **40 tajos** comunes. Cada entrada aporta `id`, nombre, aliases exactos, propiedad, ámbito, orden, fase, dependencias y criterios `M`/`X` (primer modelo en `:18-40`); los nombres no reconocidos deben quedar sin clasificar (`:3`).
- Además contiene personalización por obra bajo `obras` (`:852`), actualmente para `2025 BILBAO OBISPO ORUETA`, con tajos propios desde `:869`.
- Ya existen pruebas de contrato e invariantes en `tests/test_catalogo_tajos.py` y `tests/test_catalogo_invariantes.py`; la capa futura debe consumir este JSON como fuente, no copiar su contenido.

## 5. Suite y cobertura actual

Comando ejecutado desde `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`:

```text
python -B -m unittest discover -s tests -p test*.py -v
```

Se fijó también `PYTHONDONTWRITEBYTECODE=1` para no crear bytecode.

| Métrica | Resultado |
|---|---:|
| Módulos `test*.py` descubiertos | 32 |
| Tests ejecutados | 445 |
| Pasan | **441** |
| Fallos (`failures`) | **0** |
| Errores (`errors`) | **0** |
| Omitidos (`skipped`) | 4 |
| Duración informada por `unittest` | 41.108 s |

Los cuatro omitidos son casos de Orueta ya archivada o sin `ficha_obra.json`: uno en `test_paginacion_generador.py` y tres en `test_tajos_propios_de_obra.py`. Hubo dos `ResourceWarning` por lecturas sin cierre explícito en `test_paginacion_generador.py:71,80`; no produjeron fallo. La suite regeneró dos veces un PDF ejecutivo, pero `git diff` quedó vacío: no hubo cambio de contenido versionado.

### Casos de prueba que ejercitan directamente los caminos

| Camino | Casos directos | Ubicación |
|---|---:|---|
| `ficha_obra.actualizar()` | 36 | `tests/test_ficha_obra.py` |
| `ficha_obra.actualizar_desde_snapshot()` | 8 | `tests/test_ficha_obra.py` |
| Funciones de `leer_hoja_marcada` | 28 | `tests/test_leer_hoja_marcada.py` |
| `parsear_html()` / `listar_revisiones_html()` | **0** | Sin fichero de test |
| **Total de casos con llamada explícita a alguno de estos caminos** | **72** | Sin contar llamadas internas del wrapper como un caso adicional |

### Conteo literal solicitado por nombre o contenido de fichero de test

| Texto buscado | Ficheros de test que lo mencionan | Ficheros |
|---|---:|---|
| `leer_hoja_marcada` | 1 | `test_leer_hoja_marcada.py` |
| `actualizar_desde_snapshot` | 1 | `test_ficha_obra.py` |
| `lector_hoja_tajos_html` | **0** | — |
| `ficha_obra` | 7 | `test_cerrar_obra.py`, `test_ficha_obra.py`, `test_generar_todos.py`, `test_lector_hoja_tajos_pdf.py`, `test_prioridades_desde_base.py`, `test_sembrar_ficha_obra.py`, `test_tajos_propios_de_obra.py` |

La unión del conteo literal son ocho ficheros de test: los siete de `ficha_obra` más `test_leer_hoja_marcada.py`. `test_lector_hoja_tajos_pdf.py` prueba el lector PDF, no el lector HTML.

## Resultado ejecutivo

No se encontró deriva de líneas en los puntos centrales del diseño: `generar_todos.py:902`, las funciones de exportación `:1191/:1205` y la fusión de Gernika `:220-265` siguen vigentes. El inventario “7 adaptadores; 5 activos; 2 sin uso” es correcto. La discrepancia práctica más importante no está en el flujo productivo descrito, sino en su cobertura: el camino HTML activo de Gernika tiene cero tests directos. Los demás cambios respecto de una lectura literal del contexto son matices de alcance: `--preparar` no escribe la ficha, la skill sí menciona el fichero HTML aunque no su ingestión, y existe un creador inicial de fichas fuera de las dos vías de actualización de revisiones.
