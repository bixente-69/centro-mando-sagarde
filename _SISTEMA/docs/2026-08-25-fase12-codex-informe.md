# Informe de documentación final — Fase 12 de unificación de revisiones

Fecha de cierre: 26/08/2026.

## Alcance

La documentación del entorno refleja ya el motor común construido y verificado
en las Fases 2–11. Esta fase no ha modificado código, datos de obra ni ningún
fichero bajo `_SISTEMA/MOTOR/`. Las únicas escrituras de la fase son:

- `_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`;
- `_SISTEMA/docs/SAGARDE_MOTOR_REVISIONES_GUIA_RAPIDA.md`;
- `_SISTEMA/docs/2026-08-25-fase12-codex-informe.md` (este informe).

No se copió ningún árbol de directorios.

## Secciones actualizadas del mapa mental

| Sección | Cambio |
|---|---|
| §1, metadatos y «Estado de hoy» | Fecha y resumen manual actualizados al 26/08/2026. El actualizador canónico refrescó solo los bloques `AUTO:` y dejó el inventario en 99 `.py`, 5 `.bat` y 0 rutas muertas. |
| §2, resumen ejecutivo y ciclo del dato | Se añadieron los tres adaptadores de revisión, la preferencia por HTML gemelo, `REVISION_NORMALIZADA`, validación/aplicación común, salvaguarda previa al guardado y trazabilidad posterior. El diagrama ASCII muestra la convergencia tinta/PDF/HTML. |
| §3, mapas principales | El mindmap incorpora contrato, validador, aplicador y trazabilidad. El flowchart general distingue revisión individual e historial consolidado y muestra el bloqueo sin escritura cuando falla la paridad. |
| §4, arquitectura por capas | Se precisaron A07/A08 y el nuevo papel de A14. Se añadieron A26–A31 para `validar_revision.py`, `aplicar_revision.py`, los tres adaptadores de origen y `trazabilidad_revisiones.py`, con capa, tipo, ruta, entrada, salida, dependencias, consumidores, estado y evidencia `fichero:línea`. |
| §5.1, skills | `sagarde-revision` apunta ya a `.claude/skills/sagarde-revision/SKILL.md` y describe tinta, HTML preferente, PDF fallback, salvaguarda y JSONL. |
| §5.2, scripts y lectores/adaptadores | Se añadieron filas para los seis módulos nuevos y para `leer_hoja_marcada.py`. La fila de `generar_todos.py` refleja el origen `historial_consolidado`, la salvaguarda y el aislamiento por obra; el lector HTML deja constancia de que la vía normalizada ya no está limitada a Gernika. |
| §5.3–§5.4, documentación y configuración | Se inventariaron el diseño completo y la guía rápida. `.gitignore` documenta la excepción estrecha que permite versionar solo `revisiones_aplicadas.jsonl` por obra. |
| §6, relaciones | Tabla y Mermaid actualizados para mostrar los productores de `REVISION_NORMALIZADA`, el motor común, ambos comportamientos de salvaguarda, el guardado por el llamador y el append posterior de trazabilidad. |
| §7.2, revisión de campo a memoria | Flujo operativo reescrito: entradas por origen, normalización, dry-run, paridad, persistencia autorizada y actuación ante `[ABORTADO]` o `[AVISO CUTOVER FICHA]`. |
| §8–§10, árbol comentado, convenciones y madurez | Se añadieron las piezas nuevas al árbol resumido, el ID normalizado y el JSONL a las convenciones, y el motor común como bloque operativo con salvaguarda. |
| §11 y §13, riesgos y evidencias | La dispersión de tres métodos, los dos cálculos escritores y el HTML general antes limitado a Gernika quedan marcados como resueltos, con enlace al diseño completo. Se añadieron los módulos y documentos nuevos a las fuentes. |

No se reescribieron secciones ajenas al proyecto de revisiones ni los bloques
automáticos a mano.

## Autocomprobación del mapa mental

Sí existe un mecanismo documentado y se ejecutó:

1. `_SISTEMA/MOTOR/scripts/actualizar_mapa_mental.py --comprobar` valida los
   bloques `AUTO:`, recalcula el estado y comprueba las rutas sin escribir.
2. `_SISTEMA/MOTOR/tests/test_mapa_mental.py` fija el contrato de extracción de
   rutas, bloques automáticos, recuentos, no reescritura innecesaria y el
   trinquete de 0 rutas muertas.

La primera pasada detectó dos referencias al JSONL redactadas como rutas reales
aunque todavía no existe un log en una obra viva. Se corrigieron usando la
convención de plantilla `<obra>/…` del propio mapa. Después:

```text
python -B _SISTEMA/MOTOR/tests/test_mapa_mental.py -v
Ran 36 tests
OK
```

El actualizador se ejecutó una vez en su modo normal para refrescar
exclusivamente los bloques `AUTO:` del mapa. La comprobación inmediatamente
posterior devolvió `Mapa mental ya estaba al dia.`, código 0 y ninguna ruta
muerta. No se modificó el script ni ningún otro fichero de `_SISTEMA/MOTOR/`.

## Guía rápida nueva

`SAGARDE_MOTOR_REVISIONES_GUIA_RAPIDA.md` es una entrada autocontenida de
3–5 minutos para una futura sesión de Claude, Codex o Gemini. Resume:

- el problema original de los tres métodos dispersos y el HTML huérfano fuera
  de Gernika;
- la arquitectura origen → adaptador → `REVISION_NORMALIZADA` → validar →
  aplicar en memoria → salvaguarda → ficha → trazabilidad;
- la ubicación y responsabilidad de cada pieza;
- el uso actual mediante el CLI y la skill, sin duplicar sus comandos;
- la diferencia entre el aborto global del CLI, el bloqueo aislado por obra de
  `generar_todos.py` y el aviso no bloqueante de trazabilidad;
- los pasos de diagnóstico que deben seguirse sin forzar una discrepancia.

La guía remite a la skill para la operación exacta y al documento maestro para
el detalle de diseño, paridad y resultados fase por fase.
