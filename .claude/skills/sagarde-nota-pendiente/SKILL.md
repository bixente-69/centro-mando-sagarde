---
name: sagarde-nota-pendiente
description: Registrar temas pendientes recibidos por correo reenviado, WhatsApp, captura o imagen en una obra abierta de Sagarde, dejando una nota humana trazable y una única tarea pendiente en su FICHA DE OBRA.xlsx. Usar cuando Bixente entregue o reenvíe información que deba quedar anotada para revisar, resolver o ejecutar en una obra.
---

# Registrar una nota pendiente de obra

Este flujo conserva el contenido recibido como documento humano y añade una
sola acción al panel de prioridades. No convierte cada punto del mensaje en
una tarea distinta ni interpreta como confirmado lo que no se puede leer con
fiabilidad.

## Antes de escribir

1. Identificar sin ambigüedad una carpeta bajo `SAGARDE OBRAS ABIERTAS`. Si
   varias obras pueden casar, preguntar a Bixente; no elegir por similitud.
2. Extraer el origen, la fecha del mensaje y un resumen fiel. Si falta una
   fecha necesaria, pedirla: no sustituirla por la fecha actual.
3. Redactar una única `Tarea` breve que abarque el seguimiento del contenido
   recibido. Aunque el resumen tenga varios puntos, este flujo añade **una
   sola fila** al Excel.

## 1. Guardar la nota humana

Crear el `.txt` en la raíz de la carpeta de la obra, nunca dentro de
`_SISTEMA` ni de `INFORME SAGARDE IA`. Usar por defecto el nombre:

`TEMAS PENDIENTES DD-MM-AAAA.txt`

Si ya existe, no sobrescribirlo. Añadir al nombre una referencia breve al
origen o un ordinal y usar ese mismo nombre exacto en la columna `Archivo`.

Seguir este formato:

```text
TEMAS PENDIENTES — OBRA <NOMBRE DE LA OBRA>
Origen: <quién lo envió, por qué canal y quién lo reenvió>
Fecha: DD/MM/AAAA

Resumen:

- <tema pendiente, conservando nombres, medidas y matices de la fuente>
- <otro tema, si lo hay>

---
AVISO: <solo cuando proceda: indicar que es un resumen de una captura de
pantalla o una transcripción no literal, qué partes pueden no ser exactas y
qué fuente original debe comprobarse antes de actuar>.
```

Omitir el bloque `AVISO` únicamente cuando el texto fuente sea literal y
legible. No inventar remitentes, fechas, medidas, decisiones ni estados. Si
una imagen no permite leer una parte, señalarlo en vez de completarla.

## 2. Añadir una única tarea al Excel

Después de guardar la nota, ejecutar una sola vez:

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python nota_pendiente.py "../<CARPETA DE OBRA>/FICHA DE OBRA.xlsx" --tarea "<RESUMEN BREVE>" --origen "<ORIGEN>" --fecha "DD/MM/AAAA" --archivo "<NOMBRE EXACTO DE LA NOTA.txt>"
```

El script crea `Tareas` si falta y añade al final:

`Tarea | Origen | Fecha | Archivo | Pendiente`

No editar otras hojas, no borrar ni reescribir filas existentes y no crear
un Excel nuevo si falta `FICHA DE OBRA.xlsx`. Si el comando da error después
de crear la nota, conservarla y reportar el estado parcial. Antes de reintentar
un comando dudoso, comprobar si la fila ya quedó añadida para no duplicarla.

## Comprobación y cierre

1. Confirmar que la nota está en la raíz de la obra y que su contenido refleja
   la fuente y el aviso de fidelidad cuando corresponda.
2. Abrir la hoja `Tareas` y comprobar que la última fila contiene exactamente
   la tarea, el origen, la fecha, el nombre de la nota y `Pendiente`.
3. Reportar a Bixente la ruta de la nota y la fila añadida. No ejecutar
   `Actualizar_Sagarde.bat`, comitear ni publicar salvo autorización expresa.
