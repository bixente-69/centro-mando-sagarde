# Auditoría final independiente — Unificación del sistema de revisiones SAGARDE

Autor: Claude, como auditor independiente del trabajo producido por Codex
a lo largo de las Fases 0 a 12 del 25-26/08/2026. Fecha de cierre:
26/08/2026.

Esta auditoría no repite lo ya verificado fase a fase durante el propio
proyecto (cada fase fue auditada por Claude en el momento, con lectura
directa de código, no solo de los informes de Codex — ver bitácora en
`_SISTEMA/docs/superpowers/specs/2026-08-25-unificacion-revisiones-design.md`).
Es una comprobación final, de cierre, hecha de forma independiente:
`git diff` completo de la sesión, ejecución propia de la suite completa,
y contraste contra los doce criterios de éxito del encargo original.

## Verificación de cierre, hecha ahora mismo por Claude

- **`git diff --stat` de toda la sesión**: 3 ficheros de código existentes
  modificados (`leer_hoja_marcada.py` +277/-, `generar_todos.py` +284/-,
  `.gitignore` +4), 14 ficheros Python nuevos (6 módulos + 8 tests), y la
  documentación (mapa mental, skill, guía rápida, 11 informes de fase, el
  documento de diseño). Ningún fichero fuera de esta lista cambió.
- **Ninguna `ficha_obra.json` real cambió** en toda la sesión —
  `git diff` sobre `SAGARDE OBRAS ABIERTAS/*/INFORME SAGARDE IA/ficha_obra.json`
  vacío, comprobado ahora mismo.
- **Suite completa ejecutada de forma independiente por Claude** (no solo
  leído en un informe de Codex): `551 tests, 0 fallos, 0 errores, 4
  omitidos` — limpio, sin necesidad del rodeo de temporal que hizo falta
  durante la Fase 7 por el disco lleno de aquel momento.
- **Mecanismo de autocomprobación del mapa mental**: `test_mapa_mental.py`
  pasó (36/36, según el informe de Fase 12); confirmado además leyendo el
  `git diff` real del documento — los bloques `<!-- AUTO:... -->` se
  regeneraron con el script canónico (`actualizar_mapa_mental.py`), no se
  tocaron a mano, respetando su propia instrucción "no editar a mano".
- **Código de las dos salvaguardas de doble cálculo leído línea a línea
  por Claude** (no solo el resumen de Codex), en la Fase 7
  (`leer_hoja_marcada.py`) y la Fase 8 (`generar_todos.py`): ambas
  calculan el camino antiguo y el nuevo de forma independiente, comparan
  el valor `v` de cada clave, y solo persisten si coinciden. La de
  `generar_todos.py` además aísla el bloqueo por obra sin abortar el
  resto del proceso — confirmado en el propio código
  (`generar_todos.py:1163,1186-1187`).

## A. Arquitectura

**Sin duplicidades nuevas.** El motor común (`validar_revision.py` +
`aplicar_revision.py`) es el único punto que decide y escribe estados.
Los tres adaptadores de revisión (`adaptar_revision_tinta.py`,
`adaptar_revision_pdf_digital.py`, `adaptar_revision_html.py`) solo
traducen; no escriben. Reutilizan la lectura geométrica y de texto ya
existente (`rejilla_hoja.py`, `estados_impresos`, `aplicar()`,
`aplicar_digital()`) en vez de duplicarla — verificado en cada fase por
`import` directo, no por reimplementación.

**Modularidad y mantenibilidad**: cada pieza nueva es un fichero con una
responsabilidad, siguiendo el estilo ya establecido del proyecto (dicts y
funciones, sin jerarquías de clases). El `.gitignore` sigue su propio
patrón de lista blanca con una excepción estrecha añadida, no una regla
amplia.

## B. Funcionalidad

Los tres caminos de entrada llegan al mismo motor y fueron verificados
contra casos reales, no solo sintéticos:

| Camino | Verificado contra | Resultado |
|---|---|---|
| PDF escaneado / tinta | Bolueta 26/07, Mungia 27/07 (con las 12 correcciones reales, incluida la `P` explícita) | 0 discrepancias tras la Fase 6b |
| PDF digital | Bolueta 24/08 | 0 discrepancias |
| HTML digital | Gernika, Mungia, Bolueta, generalizado a cualquier obra | 0 discrepancias, incluida la comparación cruzada PDF↔HTML |
| Historial consolidado (`generar_todos.py`) | Gernika, Mungia, Bolueta, Obra Prueba | 0 discrepancias en las 4 obras con ficha |

## C. Integridad

- **Cero pérdida de datos observada**: todas las verificaciones empíricas
  se hicieron en memoria, con `git show` para estados históricos, sin
  `dry_run=False` sobre datos reales salvo detrás de una salvaguarda que
  ya había demostrado paridad.
- **Cero sobrescrituras indebidas**: la salvaguarda de doble cálculo es
  precisamente el mecanismo contra esto — una discrepancia bloquea la
  escritura, nunca la fuerza.
- **Revisiones fuera de orden**: sin cambios respecto del comportamiento
  ya validado (`P`/`?`, retroceso aceptado a la primera, blanco no baja
  un estado conocido) — todas las reglas existentes se preservaron por
  diseño explícito de paridad, no se reinventaron.
- **Riesgo residual documentado, no oculto**: la divergencia `antes=None`
  (el código antiguo aborta si una clave no tiene registro previo en
  `estados`; el motor nuevo la crearía) sigue sin resolverse. Bajo riesgo
  real porque toda ficha se siembra con `?` en todas las combinaciones
  válidas (verificado en `ficha_obra.py:689-696`), pero es una guarda que
  el motor nuevo no replica. Queda como pendiente explícito, no como
  hallazgo nuevo de esta auditoría.

## D. Compatibilidad

**Los métodos antiguos no se rompieron** — es la prioridad más alta del
encargo y la que más se ha verificado: cada cutover (Fases 7 y 8) se hizo
detrás de una comparación obligatoria contra el camino antiguo, nunca a
ciegas. `leer_hoja_marcada.py --preparar` (que nunca escribe) no se tocó.
La skill pública documentada para Bixente, Claude, Codex y Gemini sigue
usando exactamente los mismos comandos.

**Interfaz HTML del generador**: `generador_revisiones.html` (la app que
usa Bixente en el navegador) **no se modificó en ningún momento de este
proyecto** — el trabajo fue enteramente del lado de la lectura/escritura
en Python. Por tanto, no aplica una verificación de compatibilidad de
navegador/dispositivo (Chrome, Edge, móvil, táctil) como parte de esta
auditoría: no hay superficie nueva que probar ahí. Si en el futuro se
decide tocar esa interfaz, sí haría falta esa verificación específica.

## E. Errores

- **Errores de Python**: ninguno encontrado en la suite (0 fallos, 0
  errores) ni en la revisión manual de código.
- **Rutas incorrectas / dependencias rotas**: el propio mecanismo de
  autocomprobación del mapa mental (0 rutas muertas) y la comprobación
  manual de imports (`from generar_todos import _clave_natural,
  _clave_planta, _slug`, etc.) descartan esto.
- **Código muerto**: no se detectó — cada módulo nuevo tiene consumidor
  real (el CLI o `generar_todos.py`) salvo, deliberadamente, en las Fases
  2-6b donde el aislamiento era el objetivo explícito de esa fase.

## Criterios de éxito del encargo original (punto 22), uno a uno

1. **Único sistema conceptual de actualización** — ✅ cumplido.
2. **Entradas desacopladas de la actualización de la base** — ✅ los tres
   adaptadores solo traducen, nunca escriben.
3. **Representación común de revisión** — ✅ `REVISION_NORMALIZADA`.
4. **Validaciones comunes** — ✅ `validar_revision.py`, 10 reglas, un solo
   sitio.
5. **Sistema HTML plenamente integrado** — ✅ generalizado a cualquier
   obra (no solo Gernika) y preferido automáticamente cuando existe el
   gemelo del PDF.
6. **Los sistemas anteriores siguen funcionando** — ✅ verificado con
   salvaguarda activa y datos reales en los dos cutovers.
7. **Trazabilidad** — ✅ `revisiones_aplicadas.jsonl`, aditivo, no
   bloqueante.
8. **Mecanismos contra pérdida de datos** — ✅ salvaguarda de doble
   cálculo, aislamiento por obra, dry-run por defecto en los tres
   caminos.
9. **Tests** — ✅ 551 tests totales, más de 100 nuevos específicos de este
   proyecto, con pruebas de paridad y pruebas por mutación en cada fase.
10. **Funciona en ordenador, tablet y móvil** — ⚠️ **no aplica a este
    proyecto tal como se ejecutó**: no se tocó la interfaz del navegador.
    El motor nuevo es una capa de Python del lado del servidor/CLI, sin
    superficie de UI propia que verificar en distintos dispositivos.
11. **Arquitectura documentada** — ✅ documento de diseño completo, mapa
    mental actualizado, guía rápida nueva, skill actualizada.
12. **Auditoría final independiente de Claude** — ✅ este documento.

## Pendientes explícitos para después de este proyecto (no bloquean el cierre)

1. **Retirar la salvaguarda de doble cálculo cuando haya suficiente
   histórico real limpio.** Es deliberadamente temporal — sigue activa a
   propósito hasta que Bixente y una futura sesión decidan que hay
   confianza suficiente acumulada en producción.
2. **Decidir la guarda `antes=None`** (sección Integridad, arriba) antes
   de confiar en el motor nuevo con una ficha que no esté completamente
   sembrada.
3. **`_SISTEMA/MOTOR/CLAUDE.md` y sus tres agentes siguen sin
   actualizar**, con rutas muertas y sin mencionar nada de lo construido
   hoy — decisión de Bixente del 25/08/2026 de no tocarlo sin volver a
   preguntar. Sigue en pie.
4. **Revisar la política conservadora** de que una ubicación o tajo
   nuevo no representable en `REVISION_NORMALIZADA` bloquea la obra
   entera vía la salvaguarda (Fase 8) — funciona hoy porque no se ha dado
   ningún caso real, pero conviene decidir el comportamiento deseado
   antes de que ocurra.

## Conclusión

El proyecto cumple 11 de los 12 criterios de éxito planteados por
Bixente; el duodécimo (multi-dispositivo) no aplica porque el proyecto,
correctamente, no tocó la interfaz que ese criterio protege. No se
encontró en esta auditoría de cierre ningún hallazgo nuevo que no
estuviera ya documentado y decidido durante las fases — las
verificaciones independientes de hoy (diff completo, suite propia,
lectura directa del código de las dos salvaguardas) confirman lo que
cada informe de fase ya afirmaba. El sistema queda con tres pendientes
explícitos, ninguno bloqueante, documentados arriba para que no se
pierdan.
