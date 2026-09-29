---
name: sagarde-informe-ejecutivo
description: Generar y verificar el informe ejecutivo PDF de una o todas las obras de Sagarde, usando siempre el pipeline completo y comprobando que la salida está completa y coherente antes de darla por buena. Usar cuando Bixente pida generar, regenerar o revisar el informe ejecutivo de una obra, o pregunte qué contiene.
---

# Generar y verificar el informe ejecutivo

Existe por un error real (29/09/2026, obra 2026 BOLUETA ACR): invocar
`generar_informe_ejecutivo.py --obra "<obra>"` directamente da un PDF
INCOMPLETO — 2 páginas en vez de 5, sin Garaje ni Zonas Especiales — porque
ese camino no construye `snapshot_garaje`/`prioridades_garaje`/
`snapshot_zonas_especiales`/`prioridades_zonas_especiales`, y
`generar_pdf_ejecutivo` omite esas páginas en silencio cuando faltan. No se
detectó hasta releer el PDF a mano. Esta skill evita repetir esa pérdida de
tiempo y tokens.

## 1. Generar — un único camino válido

Siempre desde `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`:

```bash
python generar_todos.py --no-pdf
```

`--no-pdf` es un nombre heredado que ya no evita nada: el generador actual
regenera igualmente los PDF ejecutivos de todas las obras con revisiones
(confirmado en el log: `[OK] Informe ejecutivo creado con exito` por obra).
No existe un atajo seguro para "solo una obra": el pipeline completo es el
único camino que arma bien los snapshots de garaje y zonas especiales antes
de llamar a `generar_pdf_ejecutivo`. No usar el script
`generar_informe_ejecutivo.py` suelto salvo para depuración puntual, sabiendo
que el resultado será parcial.

## 2. Verificar SIEMPRE antes de dar el PDF por bueno

Un `exit 0` no certifica nada — el propio caso que motivó esta skill terminó
en `exit 0` con la mitad del informe ausente. Por cada obra que interese:

1. Leer el PDF con `Read` (sin `pages=`: así se extrae el texto de todas las
   páginas en una sola llamada).
2. Contar páginas reales contra las esperadas: 1 (Resumen General) + 1 por
   cada portal/bloque si la obra tiene 2 o más + 1 si tiene
   `ficha_garajes.json` con zonas + 1 si alguna ubicación vive en la planta
   `zesp` de `ficha_obra.json` + 1 (Cierre de Expediente). Si no coincide,
   algo se generó a medias — no reportar éxito todavía.
3. Ojo a una página con solo el pie o casi en blanco ("un par de líneas
   sueltas"): es indicio de que el bloque `KeepTogether` del pie de página
   (`_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py`,
   `_construir_bloque_electrico`) no está absorbiendo el desbordamiento. No
   debería reaparecer tras el fix del 29/09/2026 — si aparece, es un bug
   real, no ruido de maquetación.
4. Recalcular los KPI de cabecera de forma independiente en vez de fiarte
   del propio PDF: `motor_informes.kpis_snapshot(snapshot)` sobre el mismo
   snapshot que usó el generador, comparado contra el % que muestra la
   página.

## 3. Reportar en texto plano, no remitir al PDF

Al hablar con Bixente de una obra, da tú el resumen ya extraído en el paso
2 — KPI de cabecera, tajos que requieren atención, bloqueos — en vez de
decirle "ábrelo y mira". Así no hace falta reabrir ni reinterpretar el PDF
cada vez que se hable de esa obra.

## Qué NO hace esta skill

No decide cambios de diseño del informe (qué tablas añadir, cómo agrupar
los datos, qué agregados mostrar). Eso sigue siendo una decisión conjunta de
Bixente y Claude, acordada explícitamente antes de tocar
`generar_informe_ejecutivo.py` — es el mismo criterio que el resto del
proyecto aplica a cualquier cambio de UI/presentación.

## Antecedente

29/09/2026: en la misma sesión que destapó el error del punto 1, se
encontró y arregló un bug real de fondo — el informe agrupa siempre por
fase de producción y por tajo, nunca por nombre de zona/ubicación, así que
en obras con Zonas Especiales solo "Cubierta" resulta reconocible (coincide
por casualidad con un nombre de fase); el resto de zonas con nombre propio
aportan datos reales pero quedan disueltas sin etiqueta. Ver memoria de
sesión para el diseño propuesto (tabla "Detalle por zona") — todavía sin
implementar, pendiente de maqueta aprobada.
