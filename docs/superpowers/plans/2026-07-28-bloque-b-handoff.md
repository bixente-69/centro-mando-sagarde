# Traspaso de sesión — Bloque B del entorno SAGARDE

Fecha del traspaso: 28/07/2026

## Alcance acordado

Trabajar exclusivamente en el **bloque B** del plan:

- leer las revisiones de Gernika, Bolueta y Obispo Orueta;
- extraer bloque, portal, planta, etiquetas de vivienda/ubicación y tajos;
- comparar revisiones y declarar discrepancias;
- entregar una propuesta documental.

Restricción expresa del usuario: **sin interferencias**. No tocar código,
`ficha_obra.json`, datos del repositorio, generación, commits ni los bloques
C–F. Todo el trabajo realizado hasta ahora ha sido de solo lectura. No se ha
sembrado ninguna ficha.

Plan de origen:

`docs/superpowers/plans/2026-07-28-trabajo-restante-y-reparto.md`

## Estado del trabajo

- Localización de revisiones: completada.
- Extracción de estructura: prácticamente completada.
- Comparación histórica: completada en Gernika y Bolueta; avanzada en Obispo
  Orueta.
- Entrega documental final: pendiente.

## Gernika

### Estructura observada

Fuente principal más reciente:

`SAGARDE OBRAS ABIERTAS/2025 GERNIKA 32V/REVISIONES/REVISION 2025 GERNIKA 32V 25072026.pdf`

La hoja dice:

- 1 bloque.
- 2 portales: `PORTAL 1` y `PORTAL 2`.
- En cada portal: plantas `PB`, `1`, `2`, `3`.
- En todas las plantas: viviendas `A`, `B`, `C`, `D`.
- Total: 32 viviendas.

Propuesta estructural observada:

```text
BLOQUE: BLOQUE 1
  PORTAL PORTAL 1
    PLANTA PB: viviendas A, B, C, D
    PLANTA 1: viviendas A, B, C, D
    PLANTA 2: viviendas A, B, C, D
    PLANTA 3: viviendas A, B, C, D
  PORTAL PORTAL 2
    PLANTA PB: viviendas A, B, C, D
    PLANTA 1: viviendas A, B, C, D
    PLANTA 2: viviendas A, B, C, D
    PLANTA 3: viviendas A, B, C, D
```

### Comparación histórica

Los HTML del 22/07/2026 y 23/07/2026 contienen exactamente la misma
estructura: dos portales, cuatro plantas por portal y `A/B/C/D` en todas.
El PDF del 25/07/2026 conserva esa estructura.

No se ha detectado deriva estructural.

### Tajos

- 22/07 y 23/07: 36 tajos.
- 25/07: 38 tajos.
- Los dos añadidos son `Techos ZZCC` y `Pintura ZZCC`.

Lista exacta impresa el 25/07:

1. Tabicado
2. Rozas de timbres
3. Montante eléctrica
4. Montante de telecomunicaciones
5. Montante de servicios comunes
6. Tubeado de zonas comunes
7. Cableado de zonas comunes
8. Suelo recrecido
9. Suelo radiante
10. Perfilado de Pladur
11. Primeras caras de Pladur
12. Segundas caras de Pladur
13. Cuadros presentados
14. Tubeado interior
15. Cableado eléctrico
16. Telecableado
17. Portero / videoportero
18. Termostatos
19. Doblar cajas
20. Embornado eléctrico
21. Telembornado
22. Derivación individual
23. Cuadro mecanizado
24. Cuarto técnico
25. Techos
26. Enchapado
27. Techos ZZCC
28. Pintura — primera mano
29. Pintura ZZCC
30. Mecanizado eléctrico
31. Telemecanizado
32. Pintura — segunda mano
33. Placas y tapas
34. Fachada terminada
35. Apliques y enchufes de terraza
36. Agujeros de iluminación en ZZCC
37. Casquillos y bombillas
38. Iluminación de rellanos / ZZCC

Conclusión provisional: Gernika está lista para propuesta, sin dudas
estructurales relevantes.

## Bolueta

### Estructura de las hojas de revisión

Todas las revisiones Word inspeccionadas, desde 10/04/2026 hasta 21/07/2026,
mantienen la misma forma:

- 1 portal/edificio.
- Plantas `PB`, `1`, `2`, ... `23`.
- En todas las plantas, columnas `A`, `B`, `C`, `D`.
- Las 8 revisiones Word tienen 6 tablas y 12 bloques de dos plantas.

El PDF nuevo:

`SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/REVISIONES/REVISION BOLUETA 26072026.pdf`

también imprime `PB`–`23`, con cuatro viviendas `A/B/C/D` en cada planta.
La fecha interna del PDF es 25/07/2026 aunque el nombre termina en 26072026.

### Contraste documental crítico

Fuente:

`SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR/Proyecto teleco Bolueta 92.pdf`

Evidencia:

- Página PDF 1: 1 portal, `B+23`, 92 viviendas, 2 locales y 3 locales
  comunitarios.
- Páginas PDF 41–42: plantas 1–23 con 4 viviendas por planta = 92.
- Planta 1: además de las 4 viviendas, aparecen 3 locales comunitarios.
- Planta 0/PB: aparecen 2 locales, no cuatro viviendas.

Por tanto, las hojas de revisión ofrecen 96 posiciones residenciales
aparentes (`PB`–`23` × `A/B/C/D`), pero el proyecto confirma únicamente
92 viviendas (plantas 1–23) y dos locales en PB.

Esto es una discrepancia **alta y bloqueante para sembrar**:

- No se debe sembrar PB como cuatro viviendas.
- Las hojas no proporcionan las etiquetas físicas de los dos locales de PB;
  sólo muestran las columnas genéricas `A/B/C/D`.
- Hay que confirmar con Bixente cómo se llaman esos dos locales y si las
  cuatro columnas de PB son simples posiciones de seguimiento.

### Tajos

- Revisiones Word iniciales: 29 tajos.
- Desde 14/07/2026: 30 tajos; se añade `Escaleras agujeros ilum`.
- PDF nuevo del 25/07: 38 tajos.

La deriva afecta al catálogo, no a las plantas/columnas de las hojas.

## Obispo Orueta

### Primera fase histórica — Word

No se observa división en varios portales en las hojas históricas. El
adaptador y las cabeceras usan un único edificio: `Obispo Orueta 2`.

Estructura estable de plantas 1–6:

- `PLANTA 1`, `2`, `3`, `4`, `5`, `6`.
- Sección `APARTAMENTO`: columnas `1`–`10`.
- Sección `ZONAS COMUNES`: columnas `1`, `2`.
- Sección `MONTANTES`: columnas `1`, `2`, `3`.

Las revisiones antiguas sólo incluían plantas 1–6. Las plantas especiales
aparecen en septiembre:

- `PLANTA BAJA`
- `PLANTA -1`

En la revisión corregida del 08/09/2025:

- PB todavía aparece con `1`–`10`.
- Planta -1 aparece con `V1`, `V2`, `V3`, `WC1`, `WC2`, `H1`, `H2`, `H3`,
  `GYM`.

En 15/09/2025 y 24/09/2025:

- PB cambia a `1`, `2`, `C1`, `C2`, `C3`, `OF`.
- Planta -1 conserva `V1`, `V2`, `V3`, `WC1`, `WC2`, `H1`, `H2`, `H3`,
  `GYM`.

Hay un error documental conocido:

- `REVISION 08092025 .docx` llama `PLANTA 1 AITOR` a la última tabla.
- `REVISION 08092025 -LAPTOP-63ISJ7TU.docx` corrige esa cabecera a
  `PLANTA -1`.

La versión `-LAPTOP` es coherente con las revisiones posteriores.

### Tajos históricos más recientes

La revisión `REVISION 24092025.docx` contiene:

Apartamentos:

1. Pintura Hab
2. Focos Hab
3. Techos WC
4. Agujeros focos WC
5. Pintura WC
6. Focos WC
7. Pintura Pasillos
8. Agujero Focos Pasillo
9. Focos Pasillos
10. Mecanismos WC
11. Mecanismos pasillo
12. Placas + Tps. Cuadro
13. Techos
14. Enchapado
15. Mecanizado
16. Telemecanizado

Zonas comunes:

1. Cajas TECHO pasillo
2. Tubeado
3. Cableado
4. Telecableado
5. Cuarto técnico

Son 21 tajos lógicos. La palabra `Telemecanizado` aparece con mayúscula
inicial en planta 6 y con minúscula inicial en otras plantas; es una
variación de escritura, no otro tajo confirmado.

### Segunda fase nueva — PDF

Fuente:

`SAGARDE OBRAS ABIERTAS/2025 BILBAO OBISPO ORUETA/REVISIONES SAGARDE/REVISION OBISPO ORUETA 2A FASE 27072026.pdf`

La hoja dice exactamente:

- Obra/fase: `OBISPO ORUETA 2A FASE`.
- 1 bloque.
- 1 portal.
- `PLANTA PB`.
- 2 viviendas: `A`, `B`.
- 20 tajos.

Esta hoja no debe sustituir ni reinterpretarse como la estructura completa de
la primera fase histórica. Debe quedar separada como alcance `2A FASE`.

### Contraste con planos

El plano:

`28832_D2_A0401-10_ESTADO PROYECTADO_R6 CON MODI.pdf`

confirma páginas separadas para:

- planta -1;
- planta baja;
- plantas 1–6;
- bajocubierta;
- cubierta.

El texto extraíble no permite confirmar de forma segura el número real de
apartamentos de cada planta. Existe además un indicio en el nombre
`PEGATINA DE CUADRO BASE 57VIV.docx`, pero **no se ha aceptado como prueba**.

Duda pendiente antes de sembrar:

- las hojas muestran 10 columnas de apartamento en cada planta 1–6
  (60 posiciones), mientras existe el indicio “57VIV”;
- hay que contar/confirmar en los planos cuáles tres posiciones no son
  apartamentos reales o si las columnas son sólo una plantilla de
  seguimiento.

## Próximos pasos estrictos del bloque B

1. Terminar el contraste visual de las plantas 1–6 de Obispo Orueta para
   resolver, o dejar formalmente abierta, la diferencia 60/57.
2. Preparar el informe final de las tres obras con severidad y confianza.
3. Pedir a Bixente únicamente las confirmaciones estructurales necesarias:
   - nombres/uso de los dos locales de PB en Bolueta;
   - estructura real 57/60 y relación de `2A FASE` con la primera fase en
     Obispo Orueta.
4. No aplicar ninguna ficha ni cambio de repositorio.

## Herramienta temporal

Se creó fuera del repositorio, sólo para lectura:

`C:\Windows\System32\sagarde_bloque_b_audit.py`

Usa `python-docx` y `pdfplumber` para perfilar cabeceras y tablas. No modifica
los documentos fuente.

## Cómo reanudar

Iniciar Codex con SAGARDE como workspace:

```powershell
codex -C "D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE" -s workspace-write -a never
```

Después pedir:

> Lee `docs/superpowers/plans/2026-07-28-bloque-b-handoff.md` y continúa
> exclusivamente con el bloque B en modo solo lectura.
