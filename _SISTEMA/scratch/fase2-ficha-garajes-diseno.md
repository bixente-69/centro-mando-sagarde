# Fase 2 — Diseño de `ficha_garajes.py` (fichero de trabajo)

Diseño de Claude para que Codex lo implemente y pruebe (ver
`2026-09-24-ampliacion-garajes-plan.md`, Fase 2). Basado en la lectura
completa de `ficha_obra.py` (843 líneas, real, 24/09/2026).

## Qué reutiliza literalmente de `ficha_obra.py` y qué no

**Se importa sin copiar** (son puras, sin estado, sin significado propio de
vivienda): `MAPA_ESTADO`, `ESTADO_A_SNAPSHOT`, `_fold`, `_ahora`,
`_normalizar_estado`. Import directo:
`from ficha_obra import MAPA_ESTADO, ESTADO_A_SNAPSHOT, _fold, _ahora, _normalizar_estado`
— evita duplicar el alfabeto de estados en dos sitios (el riesgo real: si
algún día cambia en uno y no en el otro, es exactamente la familia de fallo
"guarda compartida ignorada en silencio" que este proyecto existe para
evitar). **No se toca `ficha_obra.py` ni una línea.**

**No se reutiliza, es genuinamente distinto:**
- No hay nivel de bloque/portal. `ficha['estructura']['garajes']` es una
  lista plana (cada uno con su propio `plantas[].zonas[]`), directamente
  análoga a lo que en vivienda son "bloques con sus portales" combinados —
  ver §3.2 del diseño ("más plano... no hay nivel de bloque ni de portal").
- No hay `_indice_ubicaciones`/`_localizar`/`_alta_ubicacion` (la maquinaria
  de casar texto difuso "edificio/planta/unidad" contra la estructura). Esa
  complejidad existe en vivienda porque el adaptador histórico lee PDFs con
  nombres inconsistentes. La entrada de garaje en v1 viene del asistente
  (Fase 4), que siempre va a dar `garaje_id`/`planta_id`/`zona_id`
  canónicos — no hace falta adivinar. Si una revisión de garaje menciona un
  trío que la ficha no conoce, **se descarta con aviso, no se inventa**
  (mismo principio que "portal entero desconocido: no se inventa" de
  vivienda, aplicado sin la maquinaria de reintento por nombre).
- **`_completar_matriz` NO se implementa en v1.** En vivienda tiene sentido
  porque toda vivienda es estructuralmente igual: cada ubicación lleva
  todos los tajos conocidos. En garaje NO: un vial nunca lleva "lucido", un
  cuarto técnico sí. Qué tajos aplican a qué tipo de zona es exactamente el
  concepto de "perfil por tipo de zona" (§5.9 del diseño), que hoy solo
  existe validado en JS del prototipo (`PERFIL_TAJOS`). Duplicarlo aquí en
  Python antes de que el asistente real (Fase 4) decida su forma final
  sería inventar un mecanismo sin validar y arriesgarse a que diverjan.
  **Consecuencia real:** `ficha_garajes.json` en v1 solo tiene celdas para
  lo que una revisión ha reportado de verdad — no nace con '?' especulativos
  para cada combinación posible. Anotado como pendiente en §7 del diseño
  cuando se cierre esta fase.

## Constantes

```python
VERSION = 1
NOMBRE_FICHERO = 'ficha_garajes.json'
APARTADOS = ('estructura', 'tajos', 'estados', 'revisiones', 'dudas')
VACIO_POR_APARTADO = {
    'estructura': dict, 'tajos': dict, 'estados': dict,
    'revisiones': list, 'dudas': list,
}
```

Deliberadamente sin `identidad`/`materiales`/`documentos`/`contactos`: son
propiedades de la OBRA entera (cliente, promotora, jefe de obra...), no de
"garaje" frente a "vivienda" — viven solo en `ficha_obra.json`, no se
duplican aquí. Si algún día hiciera falta cruzarlos, se lee de ahí.

## Forma de `ficha['estructura']`

```json
{
  "garajes": [
    {
      "id": "garaje_b1",
      "nombre": "Garaje Bloque 1",
      "plantas": [
        {
          "id": "s1",
          "nombre": "S-1",
          "zonas": [
            {"id": "zona_a", "tipo": "vial", "nombre": "Zona A",
             "origen": "asistente", "confirmado": true}
          ]
        }
      ]
    }
  ],
  "_meta": {}
}
```

`tipo` es uno de: `vial`, `trastero`, `escalera`, `rellano`,
`cuarto_tecnico`, `cuarto_ligero` (ver §3.4/§5.9 del diseño). No se valida
contra una lista cerrada en este módulo — eso es responsabilidad de quien
escribe la estructura (el asistente, Fase 4); aquí solo se guarda y se lee.

## Funciones a implementar (firma y comportamiento)

### `ruta_ficha(carpeta_obra_abs)` / `cargar(carpeta_obra_abs)` / `guardar(carpeta_obra_abs, ficha)`

Idénticas en forma a las de `ficha_obra.py` (mismo patrón: JSON en
`{obra}/INFORME SAGARDE IA/ficha_garajes.json`, UTF-8, `indent=2`,
`ensure_ascii=False`), pero escritas de cero aquí (no se importan de
`ficha_obra.py`: son tan cortas que copiar el patrón es más simple y más
seguro que parametrizar el nombre de fichero en el módulo compartido).

### `asegurar_apartados(ficha)`

Igual patrón que vivienda: crea los apartados de `APARTADOS` que falten,
más `_meta` en `estructura` y `tajos`. Devuelve la lista de los creados.

### `snapshot_desde_ficha(ficha)`

Recorre `ficha['estructura']['garajes'][].plantas[].zonas[]`, cruza contra
`ficha['tajos']['detalle']` (misma forma que en vivienda: lista de
`{id, nombre, ...}`) y `ficha['estados']` (misma forma
`{clave: {'v','f','r'}}`), con clave
`f"{garaje_id}__{planta_id}__{tajo_id}__{zona_id}"` (mismo patrón de 4
partes que vivienda, sustituyendo portal por garaje). Traduce estado vía
`ESTADO_A_SNAPSHOT` (excluye `'?'`/`'N'` igual que vivienda). Cada fila:

```python
{
    'task': nombre_tajo, 'floor': nombre_planta,
    'garaje': nombre_garaje, 'zona': nombre_zona, 'status': estado,
    'garaje_id': garaje_id, 'planta_id': planta_id, 'zona_id': zona_id,
}
```

Nombres de campo deliberadamente distintos de los de vivienda
(`garaje`/`zona`, no `building`/`unit`): son conceptos distintos y llamarlos
igual confundiría a quien lea el snapshot sin más contexto. Cómo se
combinan los dos snapshots (vivienda y garaje) para el panel es decisión de
la Fase 3, no de esta.

### `actualizar_desde_snapshot(ficha, snapshot, revision, mapa_tajos_cortos=None)` y `actualizar(ficha, datos, mapa_tajos_cortos=None)`

Mismo espíritu que vivienda (`actualizar_desde_snapshot` traduce a la forma
de `actualizar`, que hace el trabajo real), simplificado:

- Da de alta tajos nuevos en `ficha['tajos']['detalle']` si el snapshot trae
  un `task` que la ficha no conoce todavía (`origen: 'revision_sin_confirmar'`,
  igual que vivienda) — esto SÍ se mantiene, no es la parte compleja.
- Para cada fila del snapshot, busca `(garaje_id, planta_id, zona_id)`
  DIRECTAMENTE en `ficha['estructura']['garajes']` (sin buscar por nombre
  difuso). Si no existe, **se descarta con aviso** en `cambios['zonas_desconocidas']`
  — no se crea nada. No hay `_alta_ubicacion` equivalente en v1.
- Aplica la misma norma de obra que vivienda: un estado vacío/no reconocido
  NUNCA baja un estado ya guardado (solo actualiza la fecha); un estado
  reconocido explícito se acepta siempre, incluso si baja el anterior.
- Registra la revisión en `ficha['revisiones']` igual que vivienda (mismo
  `rev_id`, mismos campos `id/fecha/procesada/celdas/cambios`).
- Devuelve `(ficha, cambios)` con al menos:
  `apartados_creados, tajos_nuevos, estados_nuevos, estados_cambiados,
  zonas_desconocidas, estados_no_reconocidos, revision_registrada`.

### `esta_rancia(ficha, datos)` y `resumen_cambios(cambios)`

Mismo propósito que en vivienda (avisar si la ficha se queda atrás de la
revisión más reciente; imprimir el resumen de cambios en líneas legibles).
Adaptar solo lo necesario para los nombres de campo de `cambios` de arriba.

## Tests que debe escribir Codex

Mínimo, usando `unittest` (nada de pytest):

1. Ficha vacía: `asegurar_apartados` crea los 5 apartados y `_meta` donde
   toca; llamarlo dos veces no duplica nada.
2. `guardar`/`cargar` hacen un viaje de ida y vuelta idéntico (mismo dict).
3. Poblar una estructura mínima (1 garaje, 1 planta, 2 zonas de tipos
   distintos) y aplicar un snapshot con estados para ambas zonas — los
   estados quedan bien guardados con la clave de 4 partes correcta.
4. Marcar una celda `N`: `snapshot_desde_ficha` la excluye del todo (no
   aparece en la lista de filas).
5. Norma de obra: aplicar un estado vacío sobre una celda que ya tenía `X`
   NO la baja (solo actualiza fecha); aplicar `P` explícito SÍ la baja.
6. Snapshot con un trío `(garaje_id, planta_id, zona_id)` que la ficha NO
   conoce: se descarta, aparece en `cambios['zonas_desconocidas']`, y NO se
   crea ninguna zona nueva en la estructura (a diferencia de vivienda).
7. Dos revisiones seguidas con la misma `revision` (fecha) no duplican el
   registro en `ficha['revisiones']`.
8. `esta_rancia` devuelve motivo si la fecha de la revisión no está
   registrada, `None` si sí.

## Qué NO hace v1 (documentar en el docstring del módulo)

- No auto-completa celdas `?` para combinaciones zona×tajo no reportadas
  (sin mecanismo de "perfil por tipo de zona" en Python todavía).
- No da de alta zonas nuevas automáticamente desde una revisión — deben
  existir ya en la estructura.
- No sabe nada de `identidad`/`materiales`/`documentos`/`contactos` de la
  obra — eso sigue siendo solo de `ficha_obra.py`.
- No integra con `generar_todos.py`/`panel_obra.py`/`motor_informes.py`/
  `priorizador_trabajos.py` — eso es la Fase 3, ninguno de esos ficheros se
  toca aquí.
