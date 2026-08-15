# Tesis de prioridades — qué cambia en Sagarde y qué no — diseño

**Fecha:** 15/08/2026 · **Estado:** aprobado por Bixente

## El problema

Bixente entregó una tesis externa (`tesis-prioridades-instalacion-electrica.md`,
`D:\Descargas\`) que documenta secuenciación física, matriz de interferencias de
gremios y reglas algorítmicas de prioridad para instalaciones eléctricas y de
ICT2. Había que decidir, contra el sistema real y no de oídas, qué de eso ya
existe, qué lo contradice y qué añade valor en generar revisiones, informes,
prioridades y riesgos — sin aplicar nada a ciegas.

## Contraste realizado

- El catálogo de 39 tajos común (`reglas/CATALOGO_TAJOS.json`) coincide casi
  1:1 con el listado de la tesis: buena señal externa de que el catálogo está
  bien construido.
- El pseudocódigo del §6 de la tesis (función Python `evaluar_prioridad_tajo`
  con un `if/elif` por tajo) **no se adopta**. El priorizador real
  (`_clasificar_detalle`, `priorizador_trabajos.py:477`) ya es genérico y
  data-driven: lee `deps`/`minimo` del catálogo para cualquier tajo, sin
  código específico por tajo. Hardcodear reglas en Python duplicaría la
  fuente de verdad (catálogo JSON + código Python) y reabriría la familia de
  fallos "declarado pero ignorado en silencio" que ya ha costado caro en este
  proyecto. Se descarta explícitamente como enfoque, no solo como detalle de
  implementación.

## Hallazgo 1 — contradicción resuelta: cableado vs. Pladur

La tesis (§4, fila "Cableado Interior / DIs / Telecableado") afirma que el
cableado no puede empezar hasta cerrar la segunda cara de Pladur.

El catálogo real dice lo contrario: `segunda_cara_pladur` depende de
`cableado` y `telecableado`. Es decir, se cablea primero y se cierra después.
Confirmado textualmente el 12/08/2026 citando a Bixente: *"si ya hay un
levantamiento de primeras caras de pladur, todo lo demás... tiene que estar
hecho"* antes de cerrar.

**Decisión (15/08/2026, Bixente):** el catálogo actual es el correcto. La
tesis se equivoca en este punto. No se toca ni código ni catálogo.

## Hallazgo 2 — falsa alarma: el umbral de Pintura 1ª mano

Se preguntó inicialmente si había que exigir Pintura 1ª mano en `X` (no solo
iniciada) antes de Mecanizado/Telemecanizado, partiendo de una lectura
equivocada de `"minimo": 1`. Verificado en código:

```python
ESTADO_VALOR = {"": 0.0, "/": 0.25, "M": 0.60, "X": 1.0}
minimo = float(dep.get("minimo", 1.0))
# dep_valor >= minimo decide si la dependencia está cumplida
```

`"minimo": 1` compara contra la escala 0–1, donde solo `X` vale `1.0`. Es
decir, **ya exige X, no "iniciado"**. Las 73 dependencias del catálogo usan
`"minimo": 1` sin excepción. El catálogo ya hace lo que se pedía. No se
necesita ningún cambio aquí; se deja constancia para no repreguntarlo.

## Hallazgo 3 — dependencia inerte, sin acción

`segunda_cara_pladur` (tajo `"propiedad": "externo"`) declara `deps` sobre
`cableado` y `telecableado`, pero `_clasificar_detalle` solo recorre `deps`
para tajos `"propiedad": "propio"` — la rama `elif propiedad in ("externo",
"coordinacion"): categoria = "OTROS_GREMIOS"` se resuelve antes y nunca llega
al bucle de dependencias. Esa dependencia declarada **nunca se evalúa**: es un
caso real de "algo declarado que el motor ignora en silencio", la familia de
fallos central de este proyecto.

**Decisión (15/08/2026, Bixente): no se implementa ningún aviso para esto**
("no hace falta"). Queda documentado aquí para no repreguntarlo si vuelve a
salir en una auditoría futura.

## Cambio 1 — nuevo tajo del catálogo: Fotovoltaica

Gap real: el Cocoplan (Last Planner) de Mungia programa fotovoltaica (ID 69 /
78), y el catálogo común no tiene ningún tajo de fotovoltaica. Verificado que
hoy no es un fallo activo — lo único que existe con ese nombre en Mungia es
una carpeta de documentación; ninguna revisión de campo la ha mencionado
todavía.

```json
{
  "id": "fotovoltaica",
  "nombre": "Fotovoltaica",
  "aliases": ["Fotovoltaica", "FV", "Placas solares"],
  "propiedad": "propio",
  "ambito": "edificio",
  "orden": 306,
  "fase": "Cubierta",
  "deps": [],
  "estado_m": "Más del 50 %",
  "estado_x": "Instalación fotovoltaica terminada",
  "impacto": "Se ejecuta cuando procede la cubierta; no espera a ningún otro tajo y nada espera a él, igual que Cuarto técnico."
}
```

Sin dependencia a propósito (Bixente, 15/08/2026): igual que Cuarto técnico,
"se ejecuta cuando procede". Al ser tajo común se siembra en las 5 obras
registradas; en las que no tengan instalación fotovoltaica se marcará `N`
como cualquier otro tajo que no aplica ahí.

## Cambio 2 — cierre de expediente (dato nuevo, fuera de la rejilla de revisiones)

Restricción explícita de Bixente: *"la hoja tiene que ser sencilla... no se
pueden revisar 110 tajos de cada pasada"*. Nada de este apartado entra en
`generador_revisiones.html` ni en la rejilla ubicaciones×tajos.

4 hitos a seguir, todos (decisión de Bixente): ensayos instrumentales,
inspección OCA, CIE/Boletín eléctrico, Libro del Edificio.

Fichero nuevo por obra, `cierre_expediente.json`, mismo directorio que
`memoria_obra.json` y `prioridades_trabajos.json`:

```json
{
  "obra": "<id>",
  "actualizado": "DD/MM/AAAA",
  "hitos": {
    "ensayos_instrumentales": {"estado": "pendiente|hecho|no_aplica", "fecha": null, "nota": ""},
    "inspeccion_oca":         {"estado": "pendiente|favorable|condicionada|negativa|no_aplica", "fecha": null, "nota": ""},
    "cie_boletin":            {"estado": "pendiente|hecho|no_aplica", "fecha": null, "nota": ""},
    "libro_edificio":         {"estado": "pendiente|hecho|no_aplica", "fecha": null, "nota": ""}
  }
}
```

Se edita a mano (o con un script mínimo de actualización). No lo toca ningún
adaptador, no lo siembra `sembrar_reglas`, no lo lee el generador de hojas ni
el priorizador.

Consumidores:

- `panel_obra.py`: pestaña nueva `v-cierre` ("Cierre de expediente"), junto a
  Riesgos / Normativa / Documentos.
- `generar_informe_ejecutivo.py`: sección final del PDF, después del resto
  del contenido.

Aplica a las 5 obras registradas por igual — vive fuera de `ficha_obra.json`,
así que no depende de si la obra tiene ficha nativa o va en modo legado.

### Enfoques descartados para el cierre de expediente

- **Dentro de `ficha_obra.json`**: mezclaría la rejilla de estados medidos en
  campo con papeleo editado a mano, y dos de las cinco obras no tienen ficha
  nativa. Descartado.
- **Dentro de `registro_obras.py`**: ese fichero es configuración Python (qué
  adaptador usa cada obra), no estado mutable con fechas y resultados que
  cambian con el tiempo. Descartado.

## Qué no se toca, a propósito

| No se toca | Por qué |
|---|---|
| `priorizador_trabajos.py` (lógica de `deps`/`minimo`) | ya es correcta en los dos puntos que la tesis cuestionaba (hallazgos 1 y 2) |
| `generador_revisiones.html` / hoja de revisión semanal | el cierre de expediente y los ensayos son datos de obra, no tajos revisables vivienda por vivienda |
| Riesgos (`panel_obra.py` v-riesgos, `motor_informes.py`) | los dos avisos posibles (mecanizado/pintura, pladur/cableado) se descartan explícitamente (hallazgos 2 y 3) |
| Matriz completa de interferencias (§4 tesis) y protocolo de ensayos (§7.1) | quedan como referencia documental de apoyo; no se convierten en código más allá del catálogo y el cierre de expediente |

## Aparcado — no entra en este ciclo

- "Preinstalación para vehículo eléctrico" en garaje (bandejas portacables):
  posible tajo futuro si algún día hace falta seguirlo; no se ha preguntado a
  fondo.
- Contenido de referencia normativa (umbrales de megado, resistencia de
  tierra, diferenciales) en la vista Normativa del panel: idea anotada, no
  pedida por Bixente.

## Pruebas

1. `CATALOGO_TAJOS.json` sigue siendo JSON válido tras añadir `fotovoltaica`;
   ningún otro tajo cambia.
2. `fotovoltaica` se siembra correctamente en una obra de prueba: aparece por
   edificio, no por vivienda; sin marca en campo sale como pendiente/`?`
   igual que cualquier tajo nuevo, y nunca bloquea nada (deps vacías).
3. Un tajo `fotovoltaica` en estado `X` se computa como `TERMINADO` en
   `_clasificar_detalle`, igual que cualquier tajo `"propio"` sin deps.
4. `cierre_expediente.json` ausente no rompe la generación del panel ni del
   informe: se trata como "sin datos de cierre todavía" (los 4 hitos en
   pendiente), nunca lanza excepción sin capturar.
5. `cierre_expediente.json` con un hito con `estado` fuera de la lista
   permitida se reporta como aviso legible, no tumba la generación del panel.
6. La pestaña `v-cierre` no aparece en la hoja de revisión ni afecta a
   `obras_revisiones.js`.
7. Regenerar las 4 obras abiertas (Mungia, Gernika, Bolueta, Obra Prueba)
   mantiene su `%`, su desglose `X/M///P/?/N` y su cuenta de bloqueos
   exactamente igual que antes de este cambio, salvo la fila nueva de
   `fotovoltaica` en `?` o `N`.

## Riesgo principal

`CATALOGO_TAJOS.json` no está en git (decisión del 11/08/2026): su única
copia es el historial de versiones de OneDrive. La edición para añadir
`fotovoltaica` debe hacerse con cuidado y verificarse antes de darla por
buena; no hay `git checkout` que la deshaga si algo sale mal.

## Fuera de alcance

- Cualquier cambio en la lógica de bloqueo/dependencias existente (confirmada
  correcta en los hallazgos 1 y 2).
- Reglas de Riesgos nuevas (descartadas en el hallazgo 3).
- Vista Normativa.
- Tajo de preinstalación para vehículo eléctrico.
