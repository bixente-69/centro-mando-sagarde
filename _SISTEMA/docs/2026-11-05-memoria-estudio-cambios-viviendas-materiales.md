# Memoria · estudio de mejoras, pestañas «Cambios» y «Viviendas», materiales (05/11/2026)

**Qué es:** memoria vigente de la sesión en la nube del 04–05/11/2026 (PR #16 a #20, todas fusionadas en `main`). Léela **antes de volver a preguntar a Bixente** o de tocar `panel_viviendas.py`, `cambios_revision.py`, `viviendas_tajos.py`, `viviendas_calculo.js` o la agrupación de `entregas_materiales.py`. Lo de aquí está medido, probado o dicho por Bixente; lo que es suposición va marcado. Bixente seguirá trabajando **desde el PC directamente**.

Documento hermano con el análisis completo y las fuentes: `_SISTEMA/docs/2026-11-04-estudio-mejoras-sagarde.md` (inventario con cifras, fricciones, 14 ideas puntuadas, 3 propuestas, 33 fuentes).

---

## 1. Decisiones de Bixente (no se vuelven a preguntar)

| Asunto | Decisión |
|---|---|
| Pestaña «Cambios» | Va **entre Prioridades y Tareas**. Dice **siempre las dos fechas** entre las que se hacen los cambios («Cambios entre el 30/10/2026 y el 02/11/2026»). Compara con la **revisión anterior**. |
| Marca en materiales (05/11) | **La marca informa, no divide.** El total se agrupa por categoría + material + tipo + unidad; el mismo cable de dos marcas es un total y su celda de marca las lista. Otro **tipo** (p. ej. libre de halógenos) sí abre otro total. El tipo de aislante se escribe en la columna TIPO como texto libre, siempre igual escrito (Bixente no sabía el nombre oficial del libre de halógenos). Vale para **todo** el material, no solo cable. |
| Tajos eléctricos de vivienda | `rozas_timbres, tubeado, doblar_cajas, cableado, embornado, cuadro_mecanizado, derivacion_individual, cuadros_presentados, placas_tapas, apliques, casquillos_bombillas`. **Fuera:** telecableado, telembornado, telemecanizado, portero, termostatos. Lista en `viviendas_tajos.TAJOS_ELECTRICOS` (una prueba exige que existan en el catálogo, sean de vivienda y propios). |
| Periodos | **Naturales:** semana lunes–domingo, mes día 1–fin, año 1 ene–31 dic. El periodo en curso llega **solo hasta hoy** (el día 5 de noviembre, «noviembre» son 5 días). Si dice «octubre», es octubre entero. Disponibles: esta semana, semana pasada, este mes, mes anterior, este año, año anterior, un mes concreto, desde el principio, entre fechas. |
| Dónde se consulta | **Dos sitios con el mismo contenido:** pestañas («Viviendas» y consulta rápida de «Cambios») **y** selector del «Informe de obra», con los desplegables de periodo y casillas de tajos **también dentro del informe**, sincronizados con la pestaña (estado único). |
| Cálculo | **En la página** (JavaScript), no en el `.bat`: así «hoy» es el día real de apertura. Si pregunta el día 25, cuenta hasta el 25. El `.bat` solo incrusta los datos en bruto. |
| Qué cuenta | Solo **viviendas** (no locales, trasteros ni garajes). N y celdas inexistentes no entran en el total. Se enseñan X, M, `/` y pendientes. «Para facturar»: X terminadas en el periodo, M y `/` aparte. |
| Consulta rápida de «Cambios» | Un **tajo + un periodo → una frase** («Tubeado interior — Esta semana (del 02/11 al 05/11): 4 viviendas terminadas de 30…»). Ejemplos de Bixente: tubeadas la última semana, cableadas el último mes, embornadas desde el principio. |

## 2. Qué hay implementado (todo en `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/`)

| Pieza | Para qué |
|---|---|
| `trazabilidad_revisiones.py` | El log `revisiones_aplicadas.jsonl` guarda ahora `transiciones` = `[clave, antes, después]` por celda cambiada (`null` = no se sabe, **nunca** lista vacía). Antes el motor calculaba esto (`ficha_obra.py:611`) y lo tiraba. **Las revisiones anteriores al 05/11 no lo llevan y no se pueden reconstruir**; desde la primera revisión nueva sí. |
| `cambios_revision.py` | Lee el log: última revisión de campo con su fecha y la **fecha anterior** (del log y de `ficha['revisiones']`), resumen de subidas/bajadas por tajo y planta. `historial_consolidado` no cuenta como revisión de campo. |
| `viviendas_tajos.py` | Referencia en Python: datos por vivienda y tajo `[estado, fecha ISO, fiable]`, `contar`, `periodo_natural`. **Fecha fiable** = viene de una revisión de campo (origen que empieza por «hoja»); si viene de una carga de historial (origen vacío o «historial…») es **dudosa**: no cuenta como hecha en el periodo y se enseña aparte. |
| `viviendas_calculo.js` | El mismo cálculo en el navegador. **Una prueba exige paridad Python/JS** en cientos de casos. Lleva su línea `!` en `.gitignore` (sin ella no se publica). |
| `panel_viviendas.py` | Pestaña «🏠 Viviendas» (después de Trabajos), controles del informe, consulta rápida. Estado único compartido entre pestaña e informe. |
| `panel_obra.py` / `generar_todos.py` | `generar_panel(cambios=…, viviendas=…)`; `_cambios_para_panel` y `_viviendas_para_panel` **nunca tumban el panel** (avisan `[AVISO CAMBIOS]` / `[AVISO VIVIENDAS]`). |
| `entregas_materiales.py` | Clave de total sin marca; marca en columna propia en todas las tablas; hojas Excel generadas con la marca unida. |

## 3. Lo que se midió (cifras del 04–05/11/2026; envejecen, ver el estudio)

- **Fechas fiables en las X de vivienda eléctrica:** Olabeaga 30/30, Bolueta 283/689, Mungia 59/595, Gernika 38/319, Barakaldo 0/0. Lo anterior a las hojas digitales lleva la fecha de la carga de historial (p. ej. 28/07: 1.410 celdas en Mungia, 1.314 en Bolueta). Por eso «terminadas en el periodo» es fiable para lo reciente y no para lo antiguo.
- **Control horario:** 140 persona-día y 1.154 h en 4 obras desde el 12/10; lleva ámbito (vivienda/garaje), **no tajo**. «Horas por tajo» no se puede calcular hoy.
- **Archivo histórico de 128 obras cerradas:** en git hay 6 ficheros. Comparar con ellas no es posible con lo versionado.
- **Materiales:** solo existe «entregado»; no hay cantidad necesaria ni instalada. Las hojas `.xlsx` no están en git.
- **Postventa:** 2.786 incidencias en las vistas previas (mediana de resolución 7 días, p90 50), texto libre, 71 % en 2022. Los ficheros públicos contienen datos de clientes: no reproducirlos.
- **Previsión de fin de obra (backtest propio):** errores de −28 a +41 días a umbrales del 70–85 %; Mungia lleva 4 meses entre el 80 % y el 90 %. **No se promete fecha de fin.**

## 4. Pendiente (en orden de utilidad; nada empezado salvo lo marcado)

1. **Verificar en pantalla real** (PC, tablet, Edge): Bixente aún no había confirmado ver los desplegables tras la PR #19/#20 cuando se cerró la sesión. Si «Periodo» no aparece en «Viviendas», es un fallo que hay que mirar. Todo se probó solo en Chromium de pruebas.
2. **Decisiones suyas ya aprobadas y sin implementar:** G1 (media del inicio sin OBRA PRUEBA ni Gorliz), G3 (plazos de dato viejo 8/14 días), G4 (aviso de pendientes en `REVISIONES` y estado de la subida). G4 ataca el eslabón manual donde más se pierde y es más barata que cualquier propuesta nueva.
3. **Garajes no registran transiciones** (no pasan por `registrar_trazabilidad`) ni entran en Viviendas ni en la consulta rápida.
4. **P2 estadística de postventa** (tiempos, abiertas, antigüedad; sin clasificar por IA; salida agregada, sin nombres).
5. **P3 materiales «necesario frente a entregado»:** bloqueado hasta que Bixente aporte cantidades por tajo o vivienda tipo. Sin eso sería inventar ratios. Un aviso barato: «sin entregas desde hace N días» (Mungia: última entrada 08/05/2026).
6. **Serie histórica con denominadores mezclados** (Olabeaga 1295→1461; Mungia 88 %→43,5 % el 25/07): hay que arreglarla antes de cualquier gráfica de tendencia.
7. La **primera carga de una obra nueva** guarda todas sus celdas en una sola línea del log (grande, no se pierde nada).

## 5. Trampas conocidas (ya pasaron)

- **`.gitignore` es lista blanca:** el `.js` nuevo se habría quedado sin publicar. Un tipo de fichero nuevo exige su línea `!` y una prueba con `git check-ignore --no-index` (modelo en `test_viviendas_tajos.py`).
- **Una prueba que se salta en silencio cuenta como correcta.** La de navegador de `test_panel_viviendas.py` solo se salta si no hay Node/Playwright/Chromium; cualquier otro fallo del guion la hace fallar. En el PC de Bixente (Windows) puede saltarse entera si no hay Node: eso **no** es «verde».
- **Pruebas por mutación sobre una copia**, nunca el original. Para el panel hace falta replicar la ruta `_SISTEMA/MOTOR/assets` (el logo se busca relativo). Un criterio mal puesto (contar «saltada» como OK) dio una tanda de mutaciones inválida: comprobar siempre que **la base limpia pasa** antes de dar valor a «detectada».
- **`test_panel_server`** falla ya antes de estos cambios (unidad de Windows); no es regresión.
- Tres pruebas antiguas fijaban el diseño anterior y se actualizaron a propósito con la razón escrita: «Tareas justo después de Prioridades» → solo «Cambios» entre medias; «once claves del informe» → doce; cabeceras de materiales con la columna «Marca».
- Cualquier cambio en lo que ve Bixente de materiales requiere después `py -3.11 _SISTEMA/MOTOR/scripts/materiales_xlsx.py generar olabeaga` (debe acabar en `OK`).
- El `.bat` hace `git add -A` y **no hace pull**: traer `main` con *Repository → Pull* antes de lanzarlo.

## 6. Cómo trabaja Bixente (confirmado en esta sesión)

Es electricista, no programador: **una pregunta cada vez, en llano, con recomendación**. Aprobó cada cambio con «si abre y fusiona» (PR #16–#20). Sin esa petición expresa, no se abre ni se fusiona nada. Le importa poder **contestar rápido desde la tablet** («¿cuántas viviendas cableadas tenemos?» para facturar a fin de mes) o mandar un informe; no le interesan las fechas de fin de obra inventadas.
