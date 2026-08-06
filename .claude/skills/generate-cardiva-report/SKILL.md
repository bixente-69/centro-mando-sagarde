---
name: generate-cardiva-report
description: Generar informes preventivos CARDIVA en DOCX y PDF a partir de partes autorizados de los puntos 01–06, incluidos PDF digitales, partes manuscritos y datos normalizados. Usar cuando se necesite extraer, ordenar y validar el mantenimiento de CARDIVA, derivar deficiencias, materiales, cierre y anexos fotográficos de los puntos 07–09, o regenerar un informe con la plantilla oficial de SAGARDE.
---

# Generar informe preventivo CARDIVA

## Flujo obligatorio

1. Trabajar exclusivamente con la plantilla y los partes que el usuario autorice expresamente.
2. Extraer los puntos 01–06 sin completar por intuición ningún dato ausente.
3. Ante cualquier duda de lectura —cifra, letra, abreviatura, tachadura, sobrescritura, marca o relación entre anotaciones— detener la normalización y preguntar siempre al usuario. No elegir una interpretación ni generar el informe hasta recibir respuesta.
4. Registrar como `N/R` lo no registrado y como `N/A` lo que no aplique.
5. Normalizar los datos según `references/data-schema.md`.
6. Derivar los puntos 07–09 siguiendo `references/mapping.md`.
7. Crear un archivo JSON UTF-8 conforme al esquema.
8. Ejecutar `scripts/generate_cardiva_report.ps1` con la plantilla, el JSON y los destinos DOCX/PDF.
9. Renderizar el DOCX final y revisar todas las páginas antes de entregarlo.

## Reglas de formato

- Conservar la estructura, logos, cuadrícula y colores corporativos de la plantilla.
- Usar Arial Narrow y papel A4.
- Mostrar los resultados únicamente mediante texto negro sobre fondo blanco: `OK`, `DEF`, `N/R`, `N/A`, `PENDIENTE`, `ABIERTA` o `RESUELTA`.
- No aplicar semáforos, rellenos de color ni colores de fuente a estados, criticidades o resultados.
- Crear exactamente una hoja de fotografía por cada deficiencia abierta, con una referencia `F-xx`, un espacio grande para la imagen y un área de observaciones.
- Mantener los colores corporativos solo en títulos, cabeceras, cuadrícula y logos.

## Ejecución

```powershell
powershell -ExecutionPolicy Bypass -File scripts/generate_cardiva_report.ps1 `
  -TemplatePath "PLANTILLA.docx" `
  -DataPath "datos-cardiva.json" `
  -OutputDocx "PARTE_CARDIVA_AAAAMMDD_FINAL.docx" `
  -OutputPdf "PARTE_CARDIVA_AAAAMMDD_FINAL.pdf"
```

Usar `-Force` únicamente cuando el usuario autorice sobrescribir los destinos.

## Comprobaciones finales

- Confirmar que los puntos 01–06 coinciden con las fuentes.
- Confirmar que cada `DEF` se relaciona con una `D-xx`.
- Confirmar que materiales y evidencias apuntan a la deficiencia correcta.
- Confirmar que el número de anexos coincide con el número de incidencias.
- Confirmar que no existe codificación por colores en resultados.
- Confirmar que no hay páginas vacías, tablas cortadas ni texto solapado.
