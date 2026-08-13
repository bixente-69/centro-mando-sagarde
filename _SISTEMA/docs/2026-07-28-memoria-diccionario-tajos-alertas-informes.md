# Memoria vigente — diccionario de tajos, alertas e informes

Fecha: 28/07/2026  
Usuario que confirmó los criterios de obra: Bixente  
Estado: implementado, regenerado y verificado

Esta memoria recoge las decisiones funcionales y técnicas tomadas durante la
revisión del diccionario de tajos. Debe leerse antes de volver a preguntar por
el significado de estados históricos o por las alertas «desapareció sin
terminar».

## Estado final del sistema

- Catálogo de tajos: versión `1.3`.
- Priorizador: versión `4.3`.
- Pruebas: 91 correctas con `unittest`.
- Los paneles, prioridades, dudas e informes ejecutivos se regeneraron.
- No se ejecutó `Actualizar_Sagarde.bat` y no se publicó nada.

Indicadores validados:

| Obra | Estricto | Ponderado | Dudas pendientes |
|---|---:|---:|---:|
| 2025 GERNIKA 32V | 76,3 % | 76,3 % | 0 |
| 2026 MUNGIA ACR NEINOR | 77,6 % | 79,8 % | 0 |
| 2026 BOLUETA ACR | 39,8 % | 41,7 % | 0 |
| 2025 BILBAO OBISPO ORUETA | 80,0 % | 80,0 % | 1 real |
| 2026 GORLIZ HOSPITAL | — | — | 0; todavía sin revisiones |

La única duda real conservada es `ALCANCE_POSTAPERTURA` en Obispo Orueta:
cuando termine el tabique separador de cocinas hay que revisar los apartamentos
1 y 2 de PB antes de decidir qué trabajos eléctricos quedan.

## Diccionario universal de estados

El criterio es idéntico para cada tajo independiente:

| Estado | Significado |
|---|---|
| vacío | pendiente |
| `/` | iniciado, por debajo del 50 % del alcance de ese tajo |
| `M` | más del 50 % del alcance de ese tajo |
| `X` | terminado según el alcance de ese tajo |

Las descripciones físicas de los hitos solo explican mejor el trabajo. No
cambian el valor numérico de `/`, `M` o `X`.

Cuando Sagarde necesita más detalle, un tajo se especializa en varios. Desde
ese momento cada parte tiene su propio `/`, `M` y `X`. Un estado histórico no
se copia automáticamente a todos los tajos nuevos: solo se traduce cuando la
equivalencia está confirmada.

## Criterios confirmados por tajo

### Tabicado

- `/`: tabicado iniciado.
- `M`: más del 50 % de la vivienda tabicada.
- `X`: vivienda completamente tabicada.

### Doblar cajas

Aproximadamente la primera mitad es hacer los agujeros y la segunda colocar
las cajas y sacar los cables. `M` sigue significando más del 50 % del tajo;
normalmente implica agujeros hechos y colocación de cajas iniciada. `X`
significa cajas colocadas y cables fuera.

### Pintura

El antiguo `Pintado` agrupaba dos manos en viviendas:

| Estado antiguo | Interpretación confirmada |
|---|---|
| vacío | ninguna mano iniciada |
| `/` | pintura/primera mano iniciada |
| `M` | primera mano terminada; mitad del tajo conjunto |
| `X` | segunda mano terminada; tajo conjunto terminado |

Ahora `Pintura primera mano` y `Pintura segunda mano` son tajos separados.
Cada mano se mide con su propia escala `/`, `M`, `X`.

En Bolueta, el adaptador desdobla todos los registros Word antiguos:

- `/` → primera mano `/`, segunda pendiente;
- `M` → primera mano `X`, segunda pendiente;
- `X` → primera y segunda mano `X`.

Las 10 revisiones de Bolueta quedan sin ningún `Pintado` crudo. En cada
revisión hay 96 posiciones para primera mano y 96 para segunda mano.

`Pintura de zonas comunes` es un tajo externo separado, añadido después.

### Agujeros y equipos de iluminación

La especialización actual separa:

1. `Agujeros de iluminación en ZZCC`: solo mide hacer los agujeros.
2. `Iluminación de rellanos / ZZCC`: solo mide colocar equipos en los
   agujeros ya preparados.

En ambos, `M` es más del 50 % de su propio trabajo y `X` es ese tajo
terminado. La secuencia es:

`Techos ZZCC → Agujeros de iluminación ZZCC → Pintura ZZCC → Equipos`

### Techos

`Techos` se refiere solo a viviendas. `Techos de zonas comunes` es una
condición externa independiente, añadida para saber cuándo Sagarde puede
hacer agujeros y, después de pintar, colocar equipos.

### Mecanizado, placas y tapas

`Mecanizado` siempre contó únicamente los mecanismos. Ni en las revisiones
antiguas ni ahora incluía placas o tapas. Por tanto, una `X` histórica en
`Mecanizado` no convierte retroactivamente `Placas y tapas` en terminado.

### Montantes

El alcance exacto de una antigua fila genérica `Montantes` no está
confirmado. Probablemente agrupaba montante eléctrica, montante de
telecomunicaciones y montante de servicios comunes, pero esto es una
inferencia, no una regla operativa. No se traduce automáticamente. Solo hay
que preguntarlo si una comparación histórica concreta depende de ello.

## Obispo Orueta

Es un hotel, no un edificio de viviendas:

- cada habitación se modela como una vivienda individual;
- los pasillos se modelan como zonas comunes.

Los tajos específicos de pasillos del catálogo tienen ámbito `zona_comun`.

Escala histórica confirmada para `Pintura Hab` y `Pintura Pasillos`:

- `1` = primera mano → `/`;
- `2` = segunda mano → `M`;
- `X` = tajo terminado.

No se extendió esta traducción a `Pintura WC` porque no fue confirmada.

En `Mecanismos WC`, uno de los símbolos `T` y `C` significaba iniciado y el
otro más del 50 %, pero no se recuerda cuál. Ambos permanecen iguales entre
15/09/2025 y 24/09/2025, así que el historial no permite ordenarlos. Se
traducen los dos a `/` de forma conservadora; `X` sigue siendo terminado.

## Alertas «desapareció sin terminar»

Antes de la corrección existían alertas falsas masivas:

| Obra | Dudas antes | Dudas falsas después |
|---|---:|---:|
| Gernika | 8 | 0 |
| Mungia | 17 | 0 |
| Bolueta | 37 | 0 |

Causa raíz: `Catalogo` registraba únicamente los alias, no el campo principal
`nombre`. Las hojas nuevas imprimían nombres principales como `Mecanizado
eléctrico`, `Techos de zonas comunes` o `Casquillos y bombillas`. El motor
creaba a la vez:

- `TAJO_NUEVO` para el nombre principal;
- `OMITIDO_SIN_X` para el alias histórico del mismo tajo.

Corrección: desde el priorizador `4.3`, el nombre principal y los alias
confirmados resuelven al mismo id. No se usa similitud ni fusión aproximada.

Estado verificado tras regenerar:

- `TAJO_NUEVO`: 0.
- `OMITIDO_SIN_X`: 0.
- Obispo conserva solo su duda funcional real.

## Fuente única para panel e informe ejecutivo eléctrico

Cuando existe `ficha_obra.json`, el flujo vigente es:

`adaptador → historial crudo → ficha/correcciones → historial validado`

Desde ese historial validado se calculan memoria, prioridades, KPI, panel e
informe ejecutivo. El informe ejecutivo ya no vuelve a leer el PDF crudo.

Este cambio corrigió Mungia:

- antes, el PDF ejecutivo mostraba 80,1 % porque releía la hoja;
- ahora muestra 79,8 %, igual que la ficha, el panel y el resumen;
- desglose actual: 1801 `X`, 86 `M`, 0 `/`, 434 pendientes, total 2321.

Actualización del 12/08/2026: el PDF pasa a ser un **informe ejecutivo
eléctrico Sagarde**. Conserva el formato A4 y la identidad visual, pero su
perímetro ya no es todo lo medido en obra:

- KPI, gráficos, fases y desglose incluyen solo tajos con
  `propiedad = propio` en la base viva de la obra;
- los tajos `externo` y `coordinacion` no contaminan el porcentaje Sagarde;
- un tajo ajeno solo aparece cuando una dependencia incumplida frena un tajo
  propio, identificado entonces como condicionante de otro gremio;
- la cabecera toma cliente y dirección de `ficha_obra.json` cuando son datos
  utilizables;
- la evolución usa revisiones reales y filtra en cada fecha el mismo alcance
  Sagarde; con menos de cuatro puntos se sustituye por una composición del
  estado actual para no mostrar una tendencia débil;
- las fases, frentes disponibles y dependencias nacen de la ficha, el catálogo
  y el priorizador, no de listas por nombre escritas dentro del informe.

Cada página contiene resumen ejecutivo, KPI Sagarde, gráficos vectoriales de
evolución/composición y avance por fase, tajos propios que requieren atención,
próximos frentes y condicionantes. Hay una página general y, si existen varios
portales, una página adicional por portal.

## Riesgos regenerados desde las bases

Actualización del 12/08/2026: la pestaña `Riesgos` del panel deja de depender
principalmente de la heurística antigua de plantas rezagadas. En cada ejecución
de `generar_todos.py` se reconstruye desde las fuentes del mismo ciclo:

- `ficha_obra.json` aporta estado, estructura y cobertura;
- `CATALOGO_TAJOS.json` aporta propiedad, secuencia y dependencias;
- `prioridades_trabajos.json` aporta tajos propios bloqueados y la previsión
  de cuántas unidades libera cada condicionante;
- el historial validado aporta antigüedad, revisiones idénticas y desviaciones
  de avance;
- `FICHA DE OBRA.xlsx` conserva el registro manual complementario.

La pantalla separa bloqueos activos, señales que requieren verificación y
riesgos manuales. Una dependencia incumplida se muestra como hecho, sin
probabilidad inventada. Probabilidad, impacto y fecha límite solo se enseñan
si alguien los declaró manualmente. Una obra sin base aparece como
`Riesgos no evaluables`, nunca como cero riesgos. El índice y el portal agregan
el número de familias Sagarde bloqueadas del priorizador; la heurística de
plantas rezagadas queda nombrada como `Desviación de avance`.

El modo directo `generar_informe_ejecutivo.py --obra` también carga primero la
ficha y sustituye el último snapshot crudo por el snapshot consolidado. El
camino recomendado es `generar_todos.py` sin `--no-pdf`, que entrega al PDF la
misma ficha, historial y prioridades usados por el panel.

Paginación histórica de referencia previa al nuevo contenido:

- Obispo: 1 página.
- Bolueta: 1 página.
- Gernika: 3 páginas = general + 2 portales.
- Mungia: 4 páginas = general + 3 portales/bloques.
- Gorliz no genera informe porque todavía no tiene revisiones.

## Archivos modificados relevantes

- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/reglas/CATALOGO_TAJOS.json`
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/reglas/CRITERIOS_PRIORIZACION_TRABAJOS.md`
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/adaptadores/adaptador_bolueta.py`
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/adaptadores/adaptador_obisporueta.py`
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py`
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py`
- `_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py`
- pruebas de Bolueta, Obispo, catálogo y generación.

## Verificación realizada

```powershell
cd "D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE\SAGARDE OBRAS ABIERTAS\_SISTEMA INFORME SAGARDE IA"
python -m unittest discover -s tests
python generar_todos.py --no-pdf
```

Resultado final: 91 pruebas correctas, catálogo JSON válido, módulos Python
compilables, alertas falsas a cero y KPI de los PDF coincidentes con los
paneles.

## Advertencias que siguen vigentes

- Obispo Orueta no tiene `ficha_obra.json`. Su revisión del 27/07/2026 cubre
  2 ubicaciones frente a 107 en la revisión histórica anterior. El 80,0 %
  publicado se calcula solo con el alcance de la hoja nueva.
- Las marcas manuscritas sin sidecar siguen tratándose como no confirmadas;
  no convertirlas automáticamente en cero ni en estados inventados.
- No ejecutar `Actualizar_Sagarde.bat` durante trabajo en curso: publica los
  cambios en `main`.
- Antes de cambiar una equivalencia histórica, distinguir siempre dato
  confirmado de inferencia.

## Cierre del punto 5: limpieza y defensas del sistema

Cerrado el 29/07/2026 sin publicar en GitHub.

### Copias antiguas de trabajo

Se auditaron las cuatro copias de `.claude/worktrees` contra su índice Git y
contra el proyecto principal:

- `cool-bardeen-fc67fd`, `keen-meitner-973ef2` y `sleepy-pare-39ab48` no
  tenían modificaciones propias pendientes;
- `stoic-cori-269f0e` contenía una mejora no comprometida para normalizar
  `PORT AL` como `PORTAL`, avisar de claves de corrección huérfanas o mal
  formadas y probar ese contrato.

La mejora de `stoic` se integró en el proyecto principal mediante
`claves_correcciones.py`, cambios en `lector_hoja_tajos_pdf.py` y
`ficha_obra.py`, y siete pruebas de regresión. Después se eliminaron las
cuatro copias y sus metadatos de `.git/worktrees`. Se conservaron las cuatro
ramas `claude/*` como respaldo recuperable. Recuento final: 0 copias de
trabajo, 0 metadatos de worktree y 4 ramas de respaldo.

### Registro único de obras

El alta de obras abiertas vive ahora únicamente en:

`SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/registro_obras.py`

`generar_todos.py` importa directamente su lista `OBRAS`. El informe
ejecutivo deriva de esa misma lista su mapa compatible `ADAPTADORES`,
incluidos los alias cortos. Añadir una obra ya no exige tocar dos registros
independientes. `_MOTOR_SAGARDE/CLAUDE.md` se actualizó con este flujo.

### Fechas defectuosas y duplicadas

- Un fichero `*.correcciones.json` sin fecha válida `DDMMAAAA` se ignora con
  un aviso visible `[AVISO FICHA]`; ya no compite silenciosamente como fecha
  cero.
- Si hay varios ficheros de correcciones del mismo día, se avisa y se usa el
  de modificación más reciente; el nombre resuelve un eventual segundo
  empate de forma determinista.
- Las fechas inválidas de la lista de revisiones ya no colapsan en una misma
  clave. Se conservan, se avisan y se ordenan por texto.
- Las revisiones con fecha duplicada se avisan y quedan ordenadas por id sin
  perder ninguna.

### Verificación final

Se ejecutaron:

```powershell
python -m unittest discover -s tests
python -m py_compile registro_obras.py claves_correcciones.py lector_hoja_tajos_pdf.py ficha_obra.py generar_todos.py ..\..\_MOTOR_SAGARDE\scripts\generar_informe_ejecutivo.py
python generar_todos.py --no-pdf
python _MOTOR_SAGARDE\sagarde_portal.py
python _MOTOR_SAGARDE\scripts\auditor_sagarde.py
```

Resultado:

- 106 pruebas correctas;
- módulos modificados compilables;
- paneles e informes ejecutivos regenerados localmente;
- portal local regenerado;
- KPI sin variaciones accidentales:
  - Gernika: 76,3 %;
  - Mungia: 79,8 % ponderado y 77,6 % estricto;
  - Bolueta: 41,7 % ponderado y 39,8 % estricto;
  - Obispo Orueta: 80,0 %;
  - Gorliz: 0 %, explicado porque aún no tiene revisiones.
- La auditoría general mantiene 67 % de salud por un único aviso ajeno a este
  trabajo: ALSA Elorrieta lleva 370 días sin partes o visitas registradas.

## Caducidad de avisos por antigüedad

Regla confirmada el 29/07/2026:

- los avisos basados en días de inactividad siguen visibles hasta 399 días;
- al cumplir 400 días desaparecen del panel de avisos;
- el elemento original no se borra: la obra o contrato continúa accesible en
  su listado, pero deja de generar un aviso accionable;
- la misma regla se aplica al portal principal, a la auditoría de salud y al
  contador de avisos de Mantenimientos.

Los umbrales iniciales no cambian: obras abiertas avisan desde el día 15 y
Mantenimientos desde el día 91. Por tanto, sus ventanas visibles son
15-399 y 91-399 días, respectivamente.

La frontera quedó protegida con ocho pruebas automáticas: 399 visible, 400
oculto, edades superiores sin reaparición y el mismo cómputo por días
naturales en portal y auditoría.

## Actualización de `sagarde-nueva-obra`

Actualizada el 29/07/2026 con autorización de Bixente.

La definición local:

`_MOTOR_SAGARDE/.claude/agents/sagarde-nueva-obra.md`

ya no aplica el protocolo antiguo que creaba manualmente `panel.html`,
`dudas_pendientes.json` y `prioridades_trabajos.json`, copiaba un adaptador
completo de otra obra y añadía una segunda lista `OBRAS` dentro de
`generar_todos.py`.

El contrato vigente de la rutina es:

- el código y los datos actuales mandan sobre la documentación y sobre la
  propia rutina;
- `registro_obras.py` es el único registro de altas;
- la obra se clasifica como `nativa`, `hibrida` o `prealta`;
- una obra nativa con estructura confirmada nace con `ficha_obra.json`,
  matriz completa y estados `?`, nunca con una revisión o avance inventados;
- una obra híbrida se siembra únicamente desde revisiones y estructura
  validadas;
- una prealta sin estructura o revisión puede quedar registrada con historial
  vacío, pero no se presenta como entorno completo;
- el adaptador reutiliza el lector común correspondiente al formato real y
  solo conserva mappings específicos de la obra;
- panel, memoria, prioridades, dudas, resúmenes y
  `obras_revisiones.js` siguen siendo salidas de los generadores oficiales;
- no se modifica el motor, el catálogo, los lectores comunes, el panel o el
  portal para hacer encajar una particularidad local sin autorización
  separada;
- `Actualizar_Sagarde.bat` y cualquier publicación requieren autorización
  expresa.

La cabecera del agente quedó normalizada con `name` y `description`. Se
validó que no permanecen las cinco instrucciones obsoletas auditadas y que el
archivo instalado coincide exactamente con el borrador revisado.

Verificación posterior:

- 106 pruebas correctas con `python -m unittest discover -s tests`;
- ningún cambio de código, motor, catálogo, lector, datos de obra o salida
  publicada;
- no se ejecutó `Actualizar_Sagarde.bat`;
- no hubo commit ni publicación porque el ejecutable `git` no está disponible
  en el entorno.

Las menciones a `sagarde-nueva-obra` como «aparentemente obsoleta» en el mapa
mental y el glosario describen la auditoría anterior a esta actualización.
Esta sección de la memoria vigente deja constancia de que esa incidencia queda
cerrada.

## Entorno IA compartido y skill CARDIVA — 29/07/2026

Se incorpora al entorno SAGARDE la Agent Skill
`generate-cardiva-report`, destinada exclusivamente a informes preventivos
CARDIVA.

La fuente canónica reside en:

`MANTENIMIENTOS\MANTENIMIENTO CARDIVA\APP_CARDIVA\skills\generate-cardiva-report`

Las copias de proyecto para descubrimiento se encuentran en:

- `.agents\skills\generate-cardiva-report`;
- `.claude\skills\generate-cardiva-report`;
- `.gemini\skills\generate-cardiva-report`.

También se instalan copias de usuario en:

- `C:\Users\bixen\.codex\skills\generate-cardiva-report`;
- `C:\Users\bixen\.claude\skills\generate-cardiva-report`;
- `C:\Users\bixen\.gemini\skills\generate-cardiva-report`.

La fuente maestra y todas las copias se sincronizan y comparan con SHA-256
mediante:

`MANTENIMIENTOS\MANTENIMIENTO CARDIVA\APP_CARDIVA\tools\sync_cardiva_skill_agents.ps1`

El registro de rutas, contexto y formas de activación está en
`docs/SAGARDE_ENTORNO_IA_Y_SKILLS.md`. Gemini carga `GEMINI.md`, que importa
las reglas comunes de `CLAUDE.md`; así se mantiene una sola memoria operativa
sin duplicar criterios.

Reglas permanentes del flujo CARDIVA:

- solo se usan los archivos que el usuario identifique expresamente como
  autorizados;
- la plantilla Word oficial determina estructura, logos y colores
  corporativos;
- el informe se prepara en A4 y Arial Narrow;
- los resultados, estados, criticidades y deficiencias no llevan código de
  colores;
- se deja una página para fotografía por cada incidencia;
- la salida DOCX/PDF se valida antes de declararse final.

Estado local comprobado en la fecha de incorporación:

- Claude Code `2.1.132` instalado; validación contra el modelo pendiente por
  límite temporal de uso de la cuenta hasta el 31/07/2026 a las 04:00;
- Node.js LTS `24.18.0`, npm `11.16.0` y Gemini CLI `0.53.0` instalados;
- Gemini requiere que el usuario elija el método de autenticación en su
  primera sesión; no se guardaron credenciales por parte del proceso de
  instalación;
- npm dejó pendiente de aprobación el script de instalación de
  `@github/keytar`; solo habrá que revisarlo si Gemini no puede conservar el
  inicio de sesión.
