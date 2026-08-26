# Motor común de revisiones SAGARDE — guía rápida

Fecha: 26/08/2026. Esta guía explica el sistema operativo actual sin obligar a
releer los informes de cada fase. Para decisiones, pruebas de paridad y
hallazgos históricos, consultar el
[documento de diseño completo](superpowers/specs/2026-08-25-unificacion-revisiones-design.md).

## Qué problema resolvió

La misma actualización de una obra podía llegar por tres métodos dispersos:
una hoja marcada con tinta, el PDF rellenado en el generador o el HTML exportado
por ese mismo generador. Cada camino resolvía claves y reglas por su cuenta;
además, el publicador actualizaba `ficha_obra.json` desde el historial de los
adaptadores. El HTML exacto mediante `data-k/data-st` solo estaba conectado a
Gernika, incluso cuando otras obras tenían un HTML gemelo más fiable que releer
el PDF por geometría.

Desde el 26/08/2026 esos caminos conservan sus lectores, pero convergen antes de
decidir el estado que se guarda. El código histórico sigue calculándose en
memoria como red de seguridad: no es la ficha que se persiste.

## Arquitectura en seis líneas

```text
tinta clasificada ─────────────→ adaptar_revision_tinta.py ───────────┐
PDF digital (fallback) ─────────→ adaptar_revision_pdf_digital.py ────┤
HTML digital (preferente) ──────→ adaptar_revision_html.py ───────────┤
historial de generar_todos.py ──→ origen historial_consolidado ───────┤
                                      ↓ REVISION_NORMALIZADA          │
                           validar_revision.py → aplicar_revision.py → salvaguarda → ficha → trazabilidad
```

`REVISION_NORMALIZADA` contiene identidad, obra, fecha explícita, origen,
fuente, celdas y metadatos. La clave de celda sigue siendo
`portal__planta__tajo__vivienda`. `aplicar_revision.py` es puro respecto al
disco: devuelve una copia de la ficha en memoria; los llamadores deciden si la
guardan después de comparar ambos cálculos.

## Dónde vive cada pieza

Todo el código siguiente está en
`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/`:

| Pieza | Responsabilidad |
|---|---|
| `leer_hoja_marcada.py` | CLI operativo para tinta y revisión digital; prefiere el HTML gemelo y ejecuta la salvaguarda antes de escribir. |
| `adaptar_revision_tinta.py` | Convierte candidatas y clasificación ya resuelta; no hace visión ni escribe. |
| `adaptar_revision_pdf_digital.py` | Convierte las marcas recuperadas del PDF; es el fallback si no hay HTML o se pide expresamente. |
| `adaptar_revision_html.py` | Lee `data-k/data-st` y resuelve IDs para cualquier obra; es la vía digital preferente. |
| `validar_revision.py` | Define el contrato y centraliza reglas, alfabetos, catálogo, ubicación y antes/después. |
| `aplicar_revision.py` | Aplica solo cambios aceptados sobre una copia profunda, con `dry_run` por defecto. |
| `generar_todos.py` | Traduce el último historial consolidado, usa el mismo motor y aísla una discrepancia por obra. |
| `trazabilidad_revisiones.py` | Añade el evento común a `INFORME SAGARDE IA/revisiones_aplicadas.jsonl` después del guardado. |

El JSONL complementa los sidecars y `ficha['revisiones']`; no los sustituye.
Un fallo de trazabilidad avisa, pero no revierte una ficha que ya se guardó.

## Cómo se invoca hoy

No se llaman directamente el validador, el aplicador ni los adaptadores. Se usa
el mismo CLI y los mismos flags que antes, siguiendo la
[skill `sagarde-revision`](../../.claude/skills/sagarde-revision/SKILL.md):

- En tinta se conserva la frontera de dos pasos: preparar la geometría y los
  recortes, resolver la clasificación, simular y solo después autorizar la
  escritura.
- En digital se simula y aplica con el flujo `--digital`. Si existe un `.html`
  con el mismo nombre base que el PDF, se selecciona automáticamente; el PDF
  queda como fallback y `--forzar-pdf` sirve para una comprobación deliberada.
- Después de una escritura se regenera con `generar_todos.py --no-pdf` y se
  comprueban ficha, prioridades, panel, portal y obras no implicadas, tal como
  detalla la skill.

Sin `--escribir`, el CLI es simulación. En `generar_todos.py`, los dos caminos
se calculan siempre en memoria por cada obra antes de autorizar su ficha.

## Si aparece `[ABORTADO]` o una discrepancia

No forzar la ficha, no editar un estado a mano para hacer desaparecer el aviso
y no tratarlo como un reintento rutinario.

1. Conservar el mensaje completo, especialmente cada clave con
   `antiguo=...; nuevo=...` y cualquier celda rechazada.
2. Confirmar obra, fecha explícita y origen real. En digital, comprobar que el
   HTML sea el gemelo correcto; `--forzar-pdf` cambia el lector, pero nunca
   desactiva la salvaguarda.
3. En tinta, revisar candidatas, clasificación y `--sin-marca`; una clave sin
   tinta, una clasificación incompleta o una ubicación inexistente debe parar.
4. Revisar los avisos del adaptador: una ambigüedad de portal, planta, vivienda
   o tajo no debe resolverse por aproximación.
5. Escalar el caso a Claude, Codex o Gemini con la fuente y el mensaje. La
   corrección debe explicar el patrón completo y demostrar paridad antes de
   volver a escribir.

En el CLI, `[ABORTADO]` termina con código 2 antes de crear sidecar o guardar la
ficha. En `generar_todos.py`, `[AVISO CUTOVER FICHA]` bloquea solo la ficha de
esa obra —incluido el guardado posterior del priorizador— y permite continuar
las demás. `[AVISO TRAZABILIDAD]` es distinto: indica que la ficha ya estaba
guardada y falló únicamente el log aditivo.

## Regla mental

Los lectores descubren qué se observó; los adaptadores lo expresan con un
contrato común; el validador decide si es admisible; el aplicador calcula; la
salvaguarda autoriza; el llamador guarda; la trazabilidad registra. Ninguna capa
debe saltarse la anterior.
