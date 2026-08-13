# 1. Título y alcance

## Glosario operativo verificable del entorno SAGARDE

- **Fecha:** 29/07/2026.
- **Raíz:** `D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE`.
- **Criterio de inclusión:** nombres presentes en código, configuración, interfaz, datos o documentación operativa. Los 39 tajos comunes del catálogo se incluyen individualmente o como variante explícita de una entrada inequívoca.
- **Estados de confirmación:** `CONFIRMADO POR CÓDIGO`, `CONFIRMADO POR CONFIGURACIÓN`, `CONFIRMADO POR DOCUMENTACIÓN`, `INFERIDO CON EVIDENCIA`, `PENDIENTE DE VERIFICAR`, `APARENTEMENTE OBSOLETO`, `SIN USO CONFIRMADO`.
- **Regla:** una mención exclusiva en un plan no se eleva a comportamiento implementado.
- **Abreviatura de rutas:** `_SISTEMA...` equivale exactamente a `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`.

# 2. Índice alfabético

[A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [J](#j) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [R](#r) · [S](#s) · [T](#t) · [U](#u) · [V](#v) · [X](#x) · [Z](#z)

# 3. Glosario

<a id="a"></a>

## ACTUALIZAR

- Categoría: vista / proceso.
- Definición: novena vista del panel con instrucciones para regenerar obras.
- Función dentro de SAGARDE: expone `Actualizar_Obras.bat` y su ruta.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py:424-453,485,528`.
- Forma de uso: abrir/descargar BAT, copiar ruta y recargar con F5.
- Ejemplo real: botón `↻ Actualizar`.
- Relacionado con: `Actualizar_Obras.bat`, Panel.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `panel_obra.py`, bloque `actualizar_html`.
- Observaciones: el docstring enumera ocho pestañas, pero el código implementa nueve.

## Actualizar_Sagarde.bat

- Categoría: comando / automatización.
- Definición: actualizador global y publicador.
- Función dentro de SAGARDE: auditoría, obras, postventa, mantenimiento, portal y Git.
- Ruta o ubicación: `Actualizar_Sagarde.bat`.
- Forma de uso: doble clic o ejecución BAT; `--no-open` evita abrir el portal al final.
- Ejemplo real: `git push origin main`.
- Relacionado con: auditor, `generar_todos.py`, GitHub Pages.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `Actualizar_Sagarde.bat:13-103`.
- Observaciones: ejecuta `git add -A`; requiere autorización por su alcance.

## Adaptador

- Categoría: módulo.
- Definición: traductor específico de una obra al esquema normalizado.
- Función dentro de SAGARDE: devuelve historial `(fecha, snapshot)`.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/adaptadores/`.
- Forma de uso: importación dinámica desde el registro.
- Ejemplo real: `adaptador_bolueta.cargar_historial()`.
- Relacionado con: registro, lectores, snapshot.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `generar_todos.py`, bloque de importación; siete archivos `adaptador_*.py`.
- Observaciones: cinco registrados; Egurrola y Zorrozaure sin uso confirmado.

## Agujeros de iluminación en ZZCC

- Categoría: término eléctrico / tajo.
- Definición: tajo común de iluminación final en zonas comunes.
- Función dentro de SAGARDE: unidad catalogada de seguimiento y prioridad.
- Ruta o ubicación: `reglas/CATALOGO_TAJOS.json`, id `agujeros_iluminacion_zzcc`.
- Forma de uso: estado por ubicación según ámbito `z`.
- Ejemplo real: registro publicado en `obras_revisiones.js`.
- Relacionado con: ZZCC, iluminación de rellanos.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo v1.3.
- Observaciones: distinto de los focos específicos de Obispo.

## Apliques y enchufes de terraza

- Categoría: término eléctrico / tajo.
- Definición: remate exterior catalogado.
- Función dentro de SAGARDE: seguimiento por vivienda.
- Ruta o ubicación: catálogo, id `apliques`.
- Forma de uso: celda de revisión y ficha.
- Ejemplo real: nombre publicado `Apliques y enchufes de terraza`.
- Relacionado con: placas y tapas, fachada.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: `reglas/CATALOGO_TAJOS.json`.
- Observaciones: el nombre visible abrevia a veces como “Apliques”.

## Auditoría pre-vuelo

- Categoría: proceso / script.
- Definición: escaneo de salud antes de regenerar.
- Función dentro de SAGARDE: detecta fechas, duplicados e inactividad.
- Ruta o ubicación: `_MOTOR_SAGARDE/scripts/auditor_sagarde.py`.
- Forma de uso: primer comando del BAT global.
- Ejemplo real: salud 67, 10 incidencias en `auditoria_diagnostico.json`.
- Relacionado con: avisos, mantenimiento.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `auditor_sagarde.py:44-220`.
- Observaciones: clasifica algunos sidecars como revisión duplicada.

<a id="b"></a>

## Baterías de condensadores

- Categoría: término eléctrico / vista.
- Definición: aplicación estática para informes de baterías de condensadores.
- Función dentro de SAGARDE: ofrece una de las siete entradas del índice de aplicaciones.
- Ruta o ubicación: `VARIOS/BATERIAS DE CONDENSADORES/app_informes.html`.
- Forma de uso: enlace `app informes` desde `APLICACIONES/index.html`.
- Ejemplo real: tarjeta publicada con fecha 31/05/2026.
- Relacionado con: Aplicaciones, informes, electricidad.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `APLICACIONES/index.html`; `VARIOS/BATERIAS DE CONDENSADORES/app_informes.html`.
- Observaciones: es una aplicación auxiliar independiente del motor de obras.

## BLOQUEADO

- Categoría: estado derivado.
- Definición: categoría de tajo no ejecutable por dependencia o interferencia.
- Función dentro de SAGARDE: ordena detalle e inventario de prioridades.
- Ruta o ubicación: `priorizador_trabajos.py:25-36`.
- Forma de uso: calculado; no se persiste en la ficha.
- Ejemplo real: sección `Tajos bloqueados`.
- Relacionado con: VIABLE, OTROS_GREMIOS, DUDAS.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `CATEGORIA_ORDEN`, `SECCION_NOMBRE`.
- Observaciones: no confundir con `n_bloqueos` heurístico del motor.

## Bolueta

- Categoría: obra / dato.
- Definición: alias de `2026 BOLUETA ACR`, id `bolueta`.
- Función dentro de SAGARDE: obra registrada con ficha y generador.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/2026 BOLUETA ACR`; `registro_obras.py:34-44`.
- Forma de uso: alias, adaptador, panel y ficha.
- Ejemplo real: portal único, B+23.
- Relacionado con: `adaptador_bolueta`, ficha viva.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: registro, ficha, resumen y JS.
- Observaciones: 41,7% ponderado y 10 revisiones en resumen actual.

<a id="c"></a>

## Cableado de zonas comunes

- Categoría: término eléctrico / tajo.
- Definición: cableado con ámbito de zonas comunes.
- Función dentro de SAGARDE: seguimiento separado del interior.
- Ruta o ubicación: catálogo, id `cableado_zzcc`.
- Forma de uso: estado por alcance `z`.
- Ejemplo real: catálogo común.
- Relacionado con: tubeado de zonas comunes, ZZCC.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo v1.3.
- Observaciones: no se fusiona con `cableado`.

## Cableado eléctrico

- Categoría: término eléctrico / tajo.
- Definición: cableado interior de la instalación eléctrica.
- Función dentro de SAGARDE: tajo común por vivienda.
- Ruta o ubicación: catálogo, id `cableado`.
- Forma de uso: marca de celda `X/M///vacío`.
- Ejemplo real: nombre `Cableado eléctrico`.
- Relacionado con: tubeado, embornado, telecableado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: `reglas/CATALOGO_TAJOS.json`.
- Observaciones: `cableado_zzcc` es un tajo distinto.

## cargar_historial()

- Categoría: función.
- Definición: punto de entrada común de los adaptadores registrados.
- Función dentro de SAGARDE: transforma la fuente particular de una obra en historial normalizado.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/adaptadores/`.
- Forma de uso: llamada dinámica desde `generar_todos.py` al módulo adaptador.
- Ejemplo real: `adaptador_gernika.py:220`, `adaptador_mungia.py:311`, `adaptador_bolueta.py:395`, `adaptador_obisporueta.py:462`, `adaptador_gorliz.py:285`.
- Relacionado con: adaptadores, historial normalizado, registro de obras.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: funciones homónimas en los cinco adaptadores registrados.
- Observaciones: Egurrola y Zorrozaurre también la definen, pero no están registrados.

## Casquillos y bombillas

- Categoría: término eléctrico / tajo.
- Definición: tajo de entrega de iluminación.
- Función dentro de SAGARDE: estado final por vivienda.
- Ruta o ubicación: catálogo, id `casquillos_bombillas`.
- Forma de uso: celda de ficha/revisión.
- Ejemplo real: `Casquillos y bombillas` en JS.
- Relacionado con: iluminación de rellanos.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: el adaptador histórico puede usar variante singular.

## Catalogo (clase)

- Categoría: clase.
- Definición: cargador y resolvedor del catálogo de tajos.
- Función dentro de SAGARDE: combina catálogo común y configuración específica de obra para la priorización.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py:76`, clase `Catalogo`.
- Forma de uso: instanciación interna desde el priorizador.
- Ejemplo real: resolución de metadatos y precedencia por obra.
- Relacionado con: `reglas/CATALOGO_TAJOS.json`, bloque `obras` del mismo catálogo, `priorizar_historial()`.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `priorizador_trabajos.py`, clase `Catalogo`.
- Observaciones: el nombre de clase no lleva tilde; la entrada «Catálogo de tajos» designa el dato JSON.

## Catálogo de tajos

- Categoría: configuración.
- Definición: diccionario v1.3 de IDs, nombres, alias, fases, ámbitos y dependencias.
- Función dentro de SAGARDE: normalización y priorización común.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/reglas/CATALOGO_TAJOS.json`.
- Forma de uso: `Catalogo.resolver(nombre)`.
- Ejemplo real: 39 tajos comunes y configuración específica de Obispo.
- Relacionado con: ficha, priorizador, generador.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: `priorizador_trabajos.py:76-134`.
- Observaciones: `placas_tapas` tiene override específico deliberado.

## Cuadro mecanizado

- Categoría: término eléctrico / tajo.
- Definición: cierre técnico de cuadro.
- Función dentro de SAGARDE: tajo común por vivienda.
- Ruta o ubicación: catálogo, id `cuadro_mecanizado`.
- Forma de uso: estado de revisión.
- Ejemplo real: alias corto `cuad-mec` en sidecars.
- Relacionado con: cuadros presentados, derivación individual.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo y skill revisión.
- Observaciones: distinto de `Cuadros presentados`.

## Cuadros presentados

- Categoría: término eléctrico / tajo.
- Definición: presentación física previa del cuadro.
- Función dentro de SAGARDE: seguimiento antes del mecanizado.
- Ruta o ubicación: catálogo, id `cuadros_presentados`.
- Forma de uso: celda por vivienda.
- Ejemplo real: orden 120 del catálogo.
- Relacionado con: cuadro mecanizado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: no implica cuadro mecanizado terminado.

## Cuarto técnico

- Categoría: término eléctrico / tajo.
- Definición: trabajo de cierre técnico con ámbito de edificio.
- Función dentro de SAGARDE: seguimiento no limitado a vivienda.
- Ruta o ubicación: catálogo, id `cuarto_tecnico`.
- Forma de uso: estado con ámbito `d`.
- Ejemplo real: orden 235.
- Relacionado con: montantes, derivación individual.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: ubicación concreta depende de la obra.

<a id="d"></a>

## Derivación individual

- Categoría: término eléctrico / tajo.
- Definición: tajo de cierre técnico de alimentación individual.
- Función dentro de SAGARDE: avance por vivienda.
- Ruta o ubicación: catálogo, id `derivacion_individual`.
- Forma de uso: celda de revisión/ficha.
- Ejemplo real: nombre común publicado.
- Relacionado con: montante eléctrica, cuadro mecanizado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: sin definición normativa integrada.

## Doblar cajas

- Categoría: término eléctrico / tajo.
- Definición: recuperación de cajas después del Pladur.
- Función dentro de SAGARDE: tajo común por vivienda.
- Ruta o ubicación: catálogo, id `doblar_cajas`.
- Forma de uso: celda de revisión.
- Ejemplo real: orden 190, fase `Recuperación tras Pladur`.
- Relacionado con: segundas caras de Pladur, embornado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: `reglas/CATALOGO_TAJOS.json`.
- Observaciones: la memoria vigente describe su criterio operativo; no se deduce automáticamente solo por Pladur.
## Documentos

- Categoría: pestaña / dato.
- Definición: inventario de archivos de cada obra.
- Función dentro de SAGARDE: acceso desde el panel.
- Ruta o ubicación: `panel_obra.py`, `v-docs`; `lectores.listar_documentos`.
- Forma de uso: abrir enlaces agrupados por tipo.
- Ejemplo real: contador `n_docs` en resumen.
- Relacionado con: ficha, portal.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `panel_obra.py:524-527`; `lectores.py`, función de extracción de estado.
- Observaciones: inventariar no equivale a interpretar contenido.

## DUDAS

- Categoría: estado derivado.
- Definición: categoría para ambigüedad o dato insuficiente.
- Función dentro de SAGARDE: evita declarar un tajo ejecutable.
- Ruta o ubicación: `priorizador_trabajos.py`.
- Forma de uso: calculado y serializado en `dudas_pendientes.json`.
- Ejemplo real: sección `Dudas pendientes`.
- Relacionado con: VERIFICAR, `?`.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `SECCION_NOMBRE`, `_serializar_preguntas`.
- Observaciones: no es un estado guardado de celda.

<a id="e"></a>

## Embornado eléctrico

- Categoría: término eléctrico / tajo.
- Definición: conexión eléctrica de conductores.
- Función dentro de SAGARDE: tajo común de conexiones.
- Ruta o ubicación: catálogo, id `embornado`.
- Forma de uso: celda por vivienda.
- Ejemplo real: `Embornado eléctrico`.
- Relacionado con: cableado, telembornado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: se separa de telembornado.

## Enchapado

- Categoría: término de obra / tajo.
- Definición: acabado previo externo a Sagarde según propiedad catalogada.
- Función dentro de SAGARDE: condicionante por vivienda.
- Ruta o ubicación: catálogo, id `enchapado`.
- Forma de uso: estado de revisión.
- Ejemplo real: fase `Acabados previos`.
- Relacionado con: techos, pintura.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: la propiedad exacta la define la clave `propiedad` del catálogo.

## Estado de ficha

- Categoría: estado.
- Definición: alfabeto persistente `X`, `M`, `/`, `P`, `?`, `N`.
- Función dentro de SAGARDE: distinguir hecho, avance, pendiente confirmado, desconocido y no aplicable.
- Ruta o ubicación: `ficha_obra.py:33-44,59-66`.
- Forma de uso: valor `v` de cada celda de `ficha_obra.json`.
- Ejemplo real: `P` se traduce a vacío en snapshot; `?` y `N` se excluyen.
- Relacionado con: snapshot, KPI.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `ESTADO_A_SNAPSHOT`.
- Observaciones: categorías como BLOQUEADO no se guardan aquí.

## Exportación

- Categoría: proceso.
- Definición: producción de HTML/JSON/PDF descargable.
- Función dentro de SAGARDE: sacar revisiones o sesiones de apps.
- Ruta o ubicación: generador, Tierras, Baterías.
- Forma de uso: botones `Descargar HTML`, `Exportar sesión`, `Guardar informe`.
- Ejemplo real: Tierras exporta `.json`.
- Relacionado con: importación, localStorage.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: botones y `Blob`/`download` en los HTML.
- Observaciones: el generador de revisiones exporta, pero no importa una revisión.

<a id="f"></a>

## Fachada terminada

- Categoría: término de obra / tajo.
- Definición: condición catalogada de fachada completa.
- Función dentro de SAGARDE: seguimiento a nivel de edificio.
- Ruta o ubicación: catálogo, id `fachada_terminada`.
- Forma de uso: estado con ámbito `d`.
- Ejemplo real: orden 305.
- Relacionado con: apliques, remates exteriores.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: `reglas/CATALOGO_TAJOS.json`.
- Observaciones: no hay cálculo externo de fachada.

## Ficha de obra

- Categoría: almacenamiento / módulo.
- Definición: base viva JSON de identidad, estructura, tajos y estados.
- Función dentro de SAGARDE: acumula estructura y convierte revisiones en snapshot validado.
- Ruta o ubicación: `*/INFORME SAGARDE IA/ficha_obra.json`; código `ficha_obra.py`.
- Forma de uso: carga/actualización/guardado por `generar_todos.py`.
- Ejemplo real: Gernika, Mungia y Bolueta tienen ficha v1 en modo `hibrida`.
- Relacionado con: revisión, sidecar, generador.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `ficha_obra.py:79-99,238-278,368-416`.
- Observaciones: Obispo y Gorliz no tienen ficha actual.

## Focos de Obispo

- Categoría: término eléctrico / tajo específico.
- Definición: familias `focos_habitaciones`, `focos_wc`, `focos_pasillos`.
- Función dentro de SAGARDE: seguimiento específico del hotel Obispo Orueta.
- Ruta o ubicación: configuración de obra en `reglas/CATALOGO_TAJOS.json`.
- Forma de uso: estados por apartamento/zona.
- Ejemplo real: publicados en la entrada Obispo de `obras_revisiones.js`.
- Relacionado con: agujeros de focos, cajas de techo.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo específico.
- Observaciones: no son tajos comunes de todas las obras.

<a id="g"></a>

## Generador de revisiones

- Categoría: interfaz.
- Definición: aplicación HTML que crea hojas desde la base publicada.
- Función dentro de SAGARDE: seleccionar obra/estructura/tajos y descargar hoja.
- Ruta o ubicación: `_SISTEMA.../generador_revisiones.html`.
- Forma de uso: `sc-home` → cuatro pasos → HTML/preview.
- Ejemplo real: solo ofrece Gernika, Mungia y Bolueta mediante `worksWithDatabase()`.
- Relacionado con: `obras_revisiones.js`, localStorage.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: funciones `installedWorks`, `worksWithDatabase`, `buildHTML`.
- Observaciones: bloque comentado de API/importación no es funcional.

## generar_panel()

- Categoría: función.
- Definición: generador común del HTML de panel de obra.
- Función dentro de SAGARDE: compone nueve vistas a partir de historial, materiales, ficha, documentos, informe y prioridades.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py:91`.
- Forma de uso: llamada por los adaptadores durante la generación.
- Ejemplo real: pestañas `RESUMEN`, `VIVIENDAS`, `TAJOS`, `DUDAS`, `RIESGOS`, `MATERIALES`, `DOCUMENTOS`, `INFORME`, `ACTUALIZAR`.
- Relacionado con: Panel de obra, adaptadores, `generar_todos.py`.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `panel_obra.py`, función `generar_panel`.
- Observaciones: el docstring aún habla de ocho pestañas.

## generar_todos.py

- Categoría: script / proceso.
- Definición: orquestador principal de obras.
- Función dentro de SAGARDE: adapta, valida, calcula y genera todas las salidas.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py`.
- Forma de uso: `python generar_todos.py --no-pdf` o `--solo-revisiones`.
- Ejemplo real: llamado en paso 1/4 del BAT global.
- Relacionado con: registro, ficha, motor, panel.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `main`, `publicar_registro_revisiones`.
- Observaciones: PDF móvil requiere Playwright si no se usa `--no-pdf`.

## Gernika

- Categoría: obra / dato.
- Definición: alias de `2025 GERNIKA 32V`, id `gernika`.
- Función dentro de SAGARDE: obra con adaptador JSON/HTML y ficha.
- Ruta o ubicación: carpeta homónima; `registro_obras.py:12-21`.
- Forma de uso: panel/generador/alias.
- Ejemplo real: 38 tajos, 928 estados precargados y 32 ubicaciones publicadas.
- Relacionado con: lector HTML, ficha viva.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: registro, ficha, JS, resumen.
- Observaciones: resumen actual: 76,3%, 3 revisiones.

## Gorliz

- Categoría: obra / dato.
- Definición: alias de `2026 GORLIZ HOSPITAL`, id `gorliz`.
- Función dentro de SAGARDE: obra registrada preparada para JSON estricto.
- Ruta o ubicación: carpeta y `registro_obras.py:60-71`.
- Forma de uso: panel 0% hasta primera revisión.
- Ejemplo real: error JS `sin detalle de viviendas`.
- Relacionado con: `adaptador_gorliz`.
- Estado: PENDIENTE DE VERIFICAR.
- Evidencia: adaptador, resumen y meta JS.
- Observaciones: no existe revisión oficial en el historial actual.

<a id="h"></a>

## Handoff

- Categoría: handoff.
- Definición: documento de traspaso de una sesión/bloque.
- Función dentro de SAGARDE: continuidad documental.
- Ruta o ubicación: `docs/superpowers/plans/2026-07-28-bloque-b-handoff.md`.
- Forma de uso: lectura histórica.
- Ejemplo real: próximos pasos del bloque B.
- Relacionado con: memoria vigente, planes.
- Estado: APARENTEMENTE OBSOLETO.
- Evidencia: líneas 4-5 declaran que dejó de estar vigente.
- Observaciones: único handoff explícito localizado.

## Historial normalizado

- Categoría: dato / proceso.
- Definición: lista ordenada de pares `(fecha, snapshot)`.
- Función dentro de SAGARDE: contrato entre adaptadores y motor.
- Ruta o ubicación: retornos `cargar_historial()` de adaptadores.
- Forma de uso: entrada de ficha, memoria, motor y priorizador.
- Ejemplo real: `historial[-1]` es la revisión más reciente.
- Relacionado con: snapshot, memoria.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: docstrings de adaptadores y `motor_informes.py:22-25`.
- Observaciones: sin ficha, una revisión parcial puede reducir cobertura.

<a id="i"></a>

## Iluminación de rellanos / ZZCC

- Categoría: término eléctrico / tajo.
- Definición: iluminación final de rellanos o zonas comunes.
- Función dentro de SAGARDE: tajo de entrega con ámbito `z`.
- Ruta o ubicación: catálogo, id `iluminacion_rellanos`.
- Forma de uso: celda/estado de zonas comunes.
- Ejemplo real: orden 330.
- Relacionado con: casquillos, agujeros ZZCC.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: no equivale a focos de habitación de Obispo.

## Importación

- Categoría: proceso.
- Definición: entrada de sesión JSON en apps auxiliares.
- Función dentro de SAGARDE: restaurar datos de Tierras/Baterías.
- Ruta o ubicación: `app_informe_tierras.html`, `app_informes.html`.
- Forma de uso: input `type=file` con `.json`.
- Ejemplo real: `importarSesion(this)` en Tierras.
- Relacionado con: exportación, FileReader.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: inputs y funciones `FileReader`.
- Observaciones: no se localizó importación funcional en el generador de revisiones.

## Informe ejecutivo eléctrico

- Categoría: informe / script.
- Definición: PDF A4 de producción eléctrica Sagarde, general y por portal.
- Función dentro de SAGARDE: muestra KPI, evolución, fases, frentes y
  condicionantes usando solo tajos `propio` de la base de obra.
- Ruta o ubicación: `_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py`; salida `INFORME_EJECUTIVO_*.pdf`.
- Forma de uso: importado por orquestador o `--obra`.
- Ejemplo real: botón `Informe Ejecutivo PDF` en panel.
- Relacionado con: motor, registro, ReportLab.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `generar_para_obra`, `generar_pdf_ejecutivo`.
- Observaciones: recibe la ficha, el historial validado y las prioridades del
  mismo ciclo que el panel. Los tajos externos solo aparecen si bloquean
  producción Sagarde.

<a id="j"></a>

## JSON de correcciones

- Categoría: almacenamiento.
- Definición: sidecar `<pdf>.correcciones.json` con estados por clave.
- Función dentro de SAGARDE: resolver marcas manuscritas o blancos explícitos.
- Ruta o ubicación: junto a revisiones PDF de Mungia, Bolueta y Obispo; staging en `PARA SOBREESCRIBIR`.
- Forma de uso: objeto `estados` y claves de cuatro segmentos.
- Ejemplo real: `REVISION MUNGIA 27072026.pdf.correcciones.json`.
- Relacionado con: sidecar, ficha, lector PDF.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `lector_hoja_tajos_pdf.cargar_correcciones`.
- Observaciones: el auditor puede contarlo erróneamente como revisión duplicada.

<a id="l"></a>

## Lector PDF

- Categoría: módulo.
- Definición: lector genérico de tabla/banner/celdas de revisión.
- Función dentro de SAGARDE: producir estados y dudas desde PDF.
- Ruta o ubicación: `_SISTEMA.../lector_hoja_tajos_pdf.py`.
- Forma de uso: `parsear_pdf(ruta, identificar_portal, identificar_tajo)`.
- Ejemplo real: llamado por Mungia, Bolueta y Obispo.
- Relacionado con: pdfplumber, sidecar.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: funciones `parsear_pdf`, `listar_revisiones_pdf`.
- Observaciones: si falta pdfplumber emite aviso y no lee PDF.

## LISTO

- Categoría: estado visible.
- Definición: situación de prioridad considerada ejecutable.
- Función dentro de SAGARDE: filtro del panel de prioridades.
- Ruta o ubicación: `priorizador_trabajos.py`; `panel_obra.py`.
- Forma de uso: botón/filtro `LISTO`.
- Ejemplo real: contador `resumen.listos`.
- Relacionado con: VERIFICAR, VIABLE.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: agrupación de prioridades y JS del panel.
- Observaciones: no se guarda como estado de ficha.

## localStorage

- Categoría: almacenamiento.
- Definición: almacenamiento del navegador sin servidor.
- Función dentro de SAGARDE: configuraciones, revisiones, sesiones, perfiles e historial.
- Ruta o ubicación: generador, Tierras y Baterías HTML.
- Forma de uso: `getItem/setItem/removeItem`.
- Ejemplo real: `sgd_rev_recents`, `tierras_v1`, `sgd_perfiles`.
- Relacionado con: importación/exportación.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: llamadas Web Storage en los HTML.
- Observaciones: su pérdida no se recupera desde un backend.

<a id="m"></a>

## M

- Categoría: estado / símbolo.
- Definición: más del 50% de un tajo; peso estimado 0,60.
- Función dentro de SAGARDE: avance parcial.
- Ruta o ubicación: `motor_informes.py:33-37`; `ficha_obra.py:33-36`.
- Forma de uso: valor de celda.
- Ejemplo real: `SCORE['M']=0.60`.
- Relacionado con: `/`, X, KPI ponderado.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: motor y priorizador.
- Observaciones: `LEEME.md` dice 75%; está desactualizado.

## Mantenimiento

- Categoría: concepto funcional / carpeta.
- Definición: gestión documental de cuatro contratos actuales.
- Función dentro de SAGARDE: resumen de actividad y mapa de archivos.
- Ruta o ubicación: `MANTENIMIENTOS/`.
- Forma de uso: índice → contrato → árbol.
- Ejemplo real: PC Izenea, Cardiva, Obramat, ALSA.
- Relacionado con: portal, avisos.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `mantenimientos_resumen.json`, portal.
- Observaciones: dos scripts escriben el índice.

## Materiales

- Categoría: dato / pestaña.
- Definición: hoja de entrega XLSX y vista de totales.
- Función dentro de SAGARDE: mostrar material por tipo/unidad/total.
- Ruta o ubicación: rutas `materiales_rel` del registro; `lectores.leer_materiales`; `v-materiales`.
- Forma de uso: lectura automática si el XLSX existe.
- Ejemplo real: `hoja de entrega de materiales MUNGIA.xlsx`.
- Relacionado con: ficha, panel.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `registro_obras.py`, `lectores.py`, bloque de lectura de materiales.
- Observaciones: contradice la limitación antigua de `LEEME.md`.

## Mecanizado eléctrico

- Categoría: término eléctrico / tajo.
- Definición: colocación/conexión de mecanismos eléctricos.
- Función dentro de SAGARDE: tajo común por vivienda.
- Ruta o ubicación: catálogo, id `mecanizado`.
- Forma de uso: celda de revisión.
- Ejemplo real: fase `Mecanismos`.
- Relacionado con: telemecanizado, placas y tapas.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: no convierte automáticamente placas/tapas en terminado.

## Memoria de obra

- Categoría: almacenamiento / proceso.
- Definición: acumulación de tajos vistos, activos y terminados.
- Función dentro de SAGARDE: conservar trabajos omitidos tras su cierre.
- Ruta o ubicación: `memoria_obra.py`; `*/memoria_obra.json`.
- Forma de uso: `calcular_memoria` y `guardar_memoria`.
- Ejemplo real: `ultima_revision`, `n_revisiones`, `tajos`.
- Relacionado con: historial, ranking.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `memoria_obra.py:19-110`.
- Observaciones: algunas claves solo difieren por mayúsculas.

## Montantes

- Categoría: término eléctrico/telecomunicaciones / familia de tajos.
- Definición: `montante_electrica`, `montante_teleco`, `montante_sscc`; Obispo usa además `montante_general`.
- Función dentro de SAGARDE: infraestructura vertical con ámbito de edificio.
- Ruta o ubicación: catálogo común y configuración de Obispo.
- Forma de uso: estados separados salvo regla específica.
- Ejemplo real: `Montante de telecomunicaciones`.
- Relacionado con: SSCC, derivación individual.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo y memoria vigente.
- Observaciones: una fila histórica genérica “Montantes” no se traduce automáticamente sin evidencia.

## Motor de informes

- Categoría: módulo.
- Definición: cálculo común sin lógica por obra.
- Función dentro de SAGARDE: KPI, cobertura, bloqueos, series, matrices y rankings.
- Ruta o ubicación: `_SISTEMA.../motor_informes.py`.
- Forma de uso: funciones sobre snapshot/historial.
- Ejemplo real: `kpis_snapshot`, `detectar_bloqueos`.
- Relacionado con: panel, informe ejecutivo.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `motor_informes.py:37-239`.
- Observaciones: KPI estricto solo cuenta X; ponderado usa 1/0,6/0,25/0.

## Mungia

- Categoría: obra / dato.
- Definición: alias de `2026 MUNGIA ACR NEINOR`, id `mungia`.
- Función dentro de SAGARDE: obra registrada con DOCX/PDF y ficha.
- Ruta o ubicación: carpeta; `registro_obras.py:23-32`.
- Forma de uso: alias, panel, generador.
- Ejemplo real: ZR1.1, ZR1.2 y ZR2.1 en la ficha publicada.
- Relacionado con: adaptador Mungia, confirmaciones de estructura.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: registro/ficha/JS/resumen.
- Observaciones: resumen actual 79,8%, 25 revisiones.

<a id="n"></a>

## N

- Categoría: estado / símbolo.
- Definición: no aplica a esa ubicación.
- Función dentro de SAGARDE: excluir celda del snapshot y denominador.
- Ruta o ubicación: `ficha_obra.py:33-38,231-267`.
- Forma de uso: valor persistente de ficha; el generador lo representa como punto `·` en hoja generada.
- Ejemplo real: `ESTADO_A_SNAPSHOT` no contiene N.
- Relacionado con: `?`, P.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: ficha y constante `SYM` del generador.
- Observaciones: no significa pendiente.

## Normativa

- Categoría: pestaña / concepto funcional.
- Definición: lista estática de referencias técnicas aplicables.
- Función dentro de SAGARDE: recordatorio en panel.
- Ruta o ubicación: `panel_obra.py`, `v-normativa`.
- Forma de uso: consulta visual.
- Ejemplo real: encabezado `Normativa y criterios técnicos aplicables`.
- Relacionado con: panel, electricidad, telecomunicaciones.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `panel_obra.py:520-523`.
- Observaciones: la propia vista exige verificar vigencia; no hay integración normativa externa.

<a id="o"></a>

## Obispo Orueta

- Categoría: obra / dato.
- Definición: alias de `2025 BILBAO OBISPO ORUETA`, id `obisporueta`.
- Función dentro de SAGARDE: hotel con adaptador y tajos específicos.
- Ruta o ubicación: carpeta; `registro_obras.py:46-58`.
- Forma de uso: panel e informe; no seleccionable en generador.
- Ejemplo real: 41 tajos y 2.392 estados precargados derivados de prioridades en JS.
- Relacionado con: segunda fase, configuración específica.
- Estado: CONFIRMADO POR CÓDIGO, PENDIENTE DE FICHA.
- Evidencia: registro, adaptador, prioridades, JS.
- Observaciones: no tiene `ficha_obra.json`.

## Obra abierta

- Categoría: término de obra / carpeta.
- Definición: carpeta de trabajo bajo `SAGARDE OBRAS ABIERTAS`.
- Función dentro de SAGARDE: agrupar documentación y, en cinco casos, seguimiento IA.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/`.
- Forma de uso: portal/índice/carpeta.
- Ejemplo real: 21 carpetas de obra, excluyendo `_SISTEMA...`.
- Relacionado con: obra registrada, panel.
- Estado: CONFIRMADO POR CÓDIGO Y ÁRBOL.
- Evidencia: `resumen_obras.json`.
- Observaciones: “abierta” no implica estar registrada.

## OTROS_GREMIOS

- Categoría: estado derivado.
- Definición: interferencias o condiciones de terceros.
- Función dentro de SAGARDE: separar trabajo no ejecutable por Sagarde.
- Ruta o ubicación: `priorizador_trabajos.py:25-36`.
- Forma de uso: categoría calculada.
- Ejemplo real: sección `Otros gremios e interferencias`.
- Relacionado con: BLOQUEADO, propiedad de catálogo.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: priorizador.
- Observaciones: no se guarda como estado de ficha.

<a id="p"></a>

## P

- Categoría: estado / símbolo.
- Definición: pendiente confirmado en campo.
- Función dentro de SAGARDE: afirmar “revisado y no hecho” sin confundir con desconocido.
- Ruta o ubicación: `ficha_obra.py:33-42`.
- Forma de uso: valor persistente; se traduce a vacío para el motor.
- Ejemplo real: una casilla vacía validada entra como P.
- Relacionado con: vacío, `?`.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `MAPA_ESTADO`, `ESTADO_A_SNAPSHOT`.
- Observaciones: el snapshot no conserva la letra P.

## Panel de obra

- Categoría: interfaz.
- Definición: dashboard HTML generado para cada obra registrada.
- Función dentro de SAGARDE: presentar KPI, trabajo, datos y actualización.
- Ruta o ubicación: `*/INFORME SAGARDE IA/panel.html`; fuente `panel_obra.py`.
- Forma de uso: nueve botones `data-view`.
- Ejemplo real: cinco paneles actuales.
- Relacionado con: motor, prioridades, informe ejecutivo.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `panel_obra.py:476-538`.
- Observaciones: Gorliz tiene panel sin revisión.

## Parte de incidencia

- Categoría: skill / proceso.
- Definición: agente local que estructura partes de postventa en siete secciones.
- Función dentro de SAGARDE: guía diagnóstico, normativa, materiales, secuencia, checklist y comunicación.
- Ruta o ubicación: `.claude/agents/sagarde-parte-incidencia.md`.
- Forma de uso: no se encontró una llamada ejecutada; `settings.local.json` autoriza `Skill(sagarde-parte-incidencia)`.
- Ejemplo real: permiso exacto `Skill(sagarde-parte-incidencia)`.
- Relacionado con: Postventa, checklist, normativa.
- Estado: CONFIRMADO POR DOCUMENTACIÓN; SIN USO CONFIRMADO.
- Evidencia: `.claude/agents/sagarde-parte-incidencia.md`; `.claude/settings.local.json`.
- Observaciones: no confundir la autorización de llamada con evidencia de ejecución.

## Perfilado de Pladur

- Categoría: término de obra / tajo.
- Definición: preparación de estructura de Pladur.
- Función dentro de SAGARDE: condicionante previo por vivienda.
- Ruta o ubicación: catálogo, id `perfilado_pladur`.
- Forma de uso: celda de revisión.
- Ejemplo real: fase `Pladur`.
- Relacionado con: primeras/segundas caras.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: propiedad externa según catálogo.

## Pintura de zonas comunes

- Categoría: término de obra / tajo.
- Definición: pintura específica de ZZCC.
- Función dentro de SAGARDE: condicionante externo con ámbito `z`.
- Ruta o ubicación: catálogo, id `pintura_zzcc`.
- Forma de uso: estado separado.
- Ejemplo real: orden 318.
- Relacionado con: ZZCC, pintura primera/segunda.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: añadida después como tajo independiente según memoria vigente.

## Pintura — primera mano

- Categoría: término de obra / tajo.
- Definición: primera mano separada de pintura.
- Función dentro de SAGARDE: seguimiento granular.
- Ruta o ubicación: catálogo, id `pintura_primera`.
- Forma de uso: estado independiente.
- Ejemplo real: especialización histórica Bolueta divide pintura antigua.
- Relacionado con: pintura segunda, pintura ZZCC.
- Estado: CONFIRMADO POR CONFIGURACIÓN Y CÓDIGO.
- Evidencia: catálogo, adaptador Bolueta, memoria vigente.
- Observaciones: no es el mismo tajo que la antigua fila conjunta.

## Pintura — segunda mano

- Categoría: término de obra / tajo.
- Definición: segunda mano final.
- Función dentro de SAGARDE: estado final separado.
- Ruta o ubicación: catálogo, id `pintura_segunda`.
- Forma de uso: celda independiente.
- Ejemplo real: orden 290.
- Relacionado con: pintura primera.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo/memoria.
- Observaciones: la traducción histórica conjunta está documentada, no se generaliza a todo.

## Placas y tapas

- Categoría: término eléctrico / tajo.
- Definición: remates finales de mecanismos.
- Función dentro de SAGARDE: tajo por vivienda.
- Ruta o ubicación: catálogo, id `placas_tapas`.
- Forma de uso: estado de revisión.
- Ejemplo real: override específico para Obispo.
- Relacionado con: mecanizado, telemecanizado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: mismo ID aparece en común/específico como override, no dos tajos activos.

## Plan

- Categoría: plan.
- Definición: documento de diseño/implementación o reparto futuro.
- Función dentro de SAGARDE: guiar trabajo, no confirmar runtime.
- Ruta o ubicación: `docs/superpowers/plans/`.
- Forma de uso: lectura y checklist.
- Ejemplo real: 4 planes más 1 handoff.
- Relacionado con: spec, SDD, memoria.
- Estado: CONFIRMADO POR DOCUMENTACIÓN.
- Evidencia: nombres fechados.
- Observaciones: siempre contrastar con código actual.

## Portero / videoportero

- Categoría: término de telecomunicaciones / tajo.
- Definición: instalación interior de portero.
- Función dentro de SAGARDE: estado por vivienda.
- Ruta o ubicación: catálogo, id `portero`.
- Forma de uso: celda de revisión.
- Ejemplo real: nombre `Portero / videoportero`.
- Relacionado con: telecableado, telemecanizado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: no hay integración con un sistema externo de portero.

## Postventa

- Categoría: concepto funcional / proceso.
- Definición: gestión de incidencias después de entrega.
- Función dentro de SAGARDE: contratos, pendientes, recencia y vencimiento.
- Ruta o ubicación: `POST-VENTAS/`.
- Forma de uso: índice con búsqueda y seis filtros.
- Ejemplo real: 31 contratos actuales.
- Relacionado con: previews Word, parte de incidencia.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `postventas_index.py`, resumen JSON.
- Observaciones: ventana de garantía codificada en 2 años; Garellano tiene override.

## Primeras caras de Pladur

- Categoría: término de obra / tajo.
- Definición: primera cara de cerramiento de Pladur.
- Función dentro de SAGARDE: condición previa por vivienda.
- Ruta o ubicación: catálogo, id `primera_cara_pladur`.
- Forma de uso: celda.
- Ejemplo real: orden 110.
- Relacionado con: perfilado, segundas caras.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: no equivale a tabicado completo.

## Prioridad

- Categoría: proceso / dato.
- Definición: recomendación agrupada de trabajo listo o por verificar.
- Función dentro de SAGARDE: ordenar la ejecución operativa.
- Ruta o ubicación: `priorizador_trabajos.py`; `prioridades_trabajos.json`.
- Forma de uso: pestaña Prioridades y JSON completo.
- Ejemplo real: `resumen.listos`, `verificar`, `bloqueados`.
- Relacionado con: LISTO, VERIFICAR, catálogo.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `priorizar_historial`, `escribir_json`.
- Observaciones: derivada; no sustituye estado de ficha.

## priorizar_historial()

- Categoría: función.
- Definición: función que asigna prioridad y ordena el historial normalizado.
- Función dentro de SAGARDE: produce la lista priorizada consumida por paneles e informes.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py:560`.
- Forma de uso: recibe `historial`, nombre de obra y límite.
- Ejemplo real: firma `priorizar_historial(historial, obra="", limite=200)`.
- Relacionado con: `Catalogo`, Prioridad, historial normalizado.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `priorizador_trabajos.py`, función `priorizar_historial`.
- Observaciones: sus reglas dependen del catálogo y de la configuración específica de obra.

## publicar_registro_revisiones()

- Categoría: función / exportación.
- Definición: publicador del registro consolidado de revisiones.
- Función dentro de SAGARDE: escribe el JavaScript consumido por el generador de revisiones.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py:439`.
- Forma de uso: se ejecuta dentro de la orquestación de `generar_todos.py`.
- Ejemplo real: genera `obras_revisiones.js`.
- Relacionado con: Generador de revisiones, exportación, fichas de obra.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `generar_todos.py`, función `publicar_registro_revisiones`.
- Observaciones: el registro publicado incluye una obra derivada sin ficha y un error sin detalle de Gorliz.

<a id="r"></a>

## Registro de obras

- Categoría: configuración / módulo.
- Definición: lista única de obras automatizadas y aliases.
- Función dentro de SAGARDE: alimentar panel, generador e informe.
- Ruta o ubicación: `_SISTEMA.../registro_obras.py`.
- Forma de uso: import `OBRAS`, `resolver_obra`.
- Ejemplo real: 5 entradas.
- Relacionado con: adaptador, materiales.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `registro_obras.py:2-97`.
- Observaciones: la skill nueva obra aún indica otro registro.

## resolver_obra()

- Categoría: función.
- Definición: resolución de una obra registrada por nombre o alias.
- Función dentro de SAGARDE: centraliza la selección de configuración activa.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/registro_obras.py:95`.
- Forma de uso: llamada interna con el nombre recibido.
- Ejemplo real: devuelve una entrada de `OBRAS` si coincide con nombre o alias.
- Relacionado con: Registro de obras, aliases, adaptadores.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `registro_obras.py`, función `resolver_obra`.
- Observaciones: el protocolo antiguo de alta no documenta este registro actual.

## Revisión

- Categoría: proceso / dato.
- Definición: fotografía fechada del estado de tajos.
- Función dentro de SAGARDE: actualizar historial y ficha.
- Ruta o ubicación: carpetas `REVISIONES` o `REVISIONES SAGARDE`.
- Forma de uso: nombre iniciado por `REVISION` y fecha DDMMAAAA según protocolo actual.
- Ejemplo real: `REVISION MUNGIA 27072026.pdf`.
- Relacionado con: sidecar, snapshot, ficha.
- Estado: CONFIRMADO POR CÓDIGO Y DOCUMENTACIÓN.
- Evidencia: adaptadores y skill revisión.
- Observaciones: hay nombres históricos anómalos tratados por adaptador.

## Riesgos

- Categoría: pestaña / dato.
- Definición: vista regenerada desde la base viva, el catálogo de
  dependencias, el priorizador y el historial del mismo ciclo, más el
  registro manual de FICHA DE OBRA.xlsx.
- Función dentro de SAGARDE: separar bloqueos reales de producción, señales
  de calidad/desviación y riesgos declarados manualmente.
- Ruta o ubicación: `panel_obra.py`, `v-riesgos`.
- Forma de uso: se reconstruye al ejecutar `generar_todos.py` o
  `Actualizar_Sagarde.bat`; no se mantiene una copia manual de los riesgos
  derivados.
- Ejemplo real: `Bloqueos activos que frenan trabajo Sagarde`, ordenados por
  las unidades reales que libera cada dependencia.
- Relacionado con: `ficha_obra.json`, `CATALOGO_TAJOS.json`,
  `prioridades_trabajos.json`, historial validado y ficha XLSX.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `panel_obra.py`, funciones `bloque_riesgos`,
  `_tabla_bloqueos_riesgo` y `_tabla_controles_riesgo`.
- Observaciones: un bloqueo activo es un hecho, no una probabilidad. El motor
  no inventa probabilidad, impacto, responsable ni fecha límite; esos campos
  solo aparecen cuando están declarados en la ficha manual. El panel es de
  consulta y no incluye un flujo de edición.

## Rozas de timbres

- Categoría: término eléctrico / tajo.
- Definición: roza asociada a timbres.
- Función dentro de SAGARDE: tajo común inicial.
- Ruta o ubicación: catálogo, id `rozas_timbres`.
- Forma de uso: estado por vivienda.
- Ejemplo real: orden 20.
- Relacionado con: tabicado, portero.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: la etiqueta visible es más específica que “rozas”.

<a id="s"></a>

## SAGARDE

- Categoría: concepto funcional.
- Definición: entorno local de control de obras, postventa, mantenimientos y herramientas.
- Función dentro de SAGARDE: nodo raíz y centro de mando.
- Ruta o ubicación: raíz analizada.
- Forma de uso: scripts, HTML y carpetas compartidas.
- Ejemplo real: `index.html` titulado `Sagarde | Centro de mando`.
- Relacionado con: todas las capas.
- Estado: CONFIRMADO POR CÓDIGO Y DOCUMENTACIÓN.
- Evidencia: `CLAUDE.md`, portal.
- Observaciones: no es un servicio de base de datos.

## Segundas caras de Pladur

- Categoría: término de obra / tajo.
- Definición: cierre de la segunda cara de Pladur.
- Función dentro de SAGARDE: condicionante previo a recuperación/acabados.
- Ruta o ubicación: catálogo, id `segunda_cara_pladur`.
- Forma de uso: celda.
- Ejemplo real: orden 180.
- Relacionado con: doblar cajas, perfilado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: propiedad externa según configuración.

## Sidecar

- Categoría: almacenamiento / término operativo.
- Definición: JSON de corrección asociado a un PDF.
- Función dentro de SAGARDE: guardar transcripción verificada sin modificar el PDF original.
- Ruta o ubicación: `<pdf>.correcciones.json`.
- Forma de uso: lector busca el nombre exacto derivado.
- Ejemplo real: sidecars de Mungia 25/07 y 27/07.
- Relacionado con: JSON de correcciones, revisión.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `lector_hoja_tajos_pdf.py:46-66`.
- Observaciones: blanco `""` es corrección válida.

## Skill local

- Categoría: skill.
- Definición: directorio de instrucciones especializado con un archivo
  `SKILL.md`, conforme al estándar Agent Skills.
- Función dentro de SAGARDE: encapsular un flujo repetible, sus referencias y
  sus scripts.
- Ruta o ubicación: la fuente maestra CARDIVA está en
  `MANTENIMIENTOS/MANTENIMIENTO CARDIVA/APP_CARDIVA/skills/generate-cardiva-report`.
- Forma de uso: `$generate-cardiva-report` en Codex,
  `/generate-cardiva-report` en Claude y activación contextual en Gemini.
- Ejemplo real: generación del preventivo CARDIVA del 29/07/2026.
- Relacionado con: `SKILL.md`, scripts, referencias, contexto de proyecto.
- Estado: IMPLEMENTADA Y SINCRONIZADA.
- Evidencia: `docs/SAGARDE_ENTORNO_IA_Y_SKILLS.md` y copias bajo
  `.agents/skills`, `.claude/skills` y `.gemini/skills`.
- Observaciones: los Markdown históricos bajo `.claude/agents` son agentes
  locales; no son técnicamente la misma clase de artefacto.

## Snapshot

- Categoría: dato.
- Definición: lista plana de registros de una revisión.
- Función dentro de SAGARDE: contrato del motor.
- Ruta o ubicación: memoria Python; generado por adaptador o `snapshot_desde_ficha`.
- Forma de uso: dicts `task`, `floor`, `building`, `unit`, `status`.
- Ejemplo real: `historial[-1][1]`.
- Relacionado con: historial, ficha, KPI.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `motor_informes.py:11-23`.
- Observaciones: `?` y N no entran desde ficha.

## snapshot_desde_ficha()

- Categoría: función.
- Definición: conversor de una ficha al snapshot usado por el historial.
- Función dentro de SAGARDE: permite reutilizar el estado estructurado como revisión normalizada.
- Ruta o ubicación: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/ficha_obra.py:238`.
- Forma de uso: llamada interna con el objeto de ficha.
- Ejemplo real: función `snapshot_desde_ficha(ficha)`.
- Relacionado con: Ficha de obra, Snapshot, historial normalizado.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `ficha_obra.py`, función `snapshot_desde_ficha`.
- Observaciones: no crea una revisión documental nueva.

## SSCC

- Categoría: término eléctrico / abreviatura.
- Definición: aparece en `montante_sscc` y nombre visible `Montante de servicios comunes`.
- Función dentro de SAGARDE: identificar montante específico.
- Ruta o ubicación: catálogo.
- Forma de uso: ID/nombre de tajo.
- Ejemplo real: `montante_sscc`.
- Relacionado con: montante eléctrica/teleco.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: la expansión se toma del nombre visible; no hay glosario previo formal.

## Suelo radiante

- Categoría: término de obra / tajo.
- Definición: condición de obra previa.
- Función dentro de SAGARDE: seguimiento por vivienda.
- Ruta o ubicación: catálogo, id `suelo_radiante`.
- Forma de uso: celda.
- Ejemplo real: orden 80.
- Relacionado con: suelo recrecido.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: propiedad de tercero según catálogo.

## Suelo recrecido

- Categoría: término de obra / tajo.
- Definición: recrecido del suelo posterior/análogo a condición previa.
- Función dentro de SAGARDE: seguimiento por vivienda.
- Ruta o ubicación: catálogo, id `suelo_recrecido`.
- Forma de uso: celda.
- Ejemplo real: orden 90.
- Relacionado con: suelo radiante, Pladur.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: no hay cálculo de espesor o material.

<a id="t"></a>

## Tabicado

- Categoría: término de obra / tajo.
- Definición: primer tajo común del catálogo.
- Función dentro de SAGARDE: condicionante inicial por vivienda.
- Ruta o ubicación: catálogo, id `tabicado`.
- Forma de uso: estado de revisión.
- Ejemplo real: orden 10.
- Relacionado con: rozas, Pladur.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo y memoria vigente.
- Observaciones: Obispo añade `tabique_separador_cocinas` como tajo distinto.

## Tajo

- Categoría: concepto funcional / término de obra.
- Definición: unidad de trabajo cuyo estado se mide por ubicación.
- Función dentro de SAGARDE: eje de ficha, KPI, prioridad y revisión.
- Ruta o ubicación: catálogo y estados de ficha.
- Forma de uso: ID estable + nombre/alias.
- Ejemplo real: `tubeado`, `mecanizado`.
- Relacionado con: estado, catálogo, ubicación.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: catálogo/priorizador/ficha.
- Observaciones: un tajo desconocido entra como `sin_clasificar:*`.

## Tajos específicos de Obispo

- Categoría: términos de obra/eléctricos específicos.
- Definición: `tabique_separador_cocinas`, `trabajos_electricos_tabique_cocina`, `ventilacion`, `cableado_extractor`, `lucido_paredes`, `techos_wc`, pinturas de habitaciones/WC/pasillos, agujeros/cajas/focos y mecanismos de WC/pasillo.
- Función dentro de SAGARDE: ampliar el catálogo común para el hotel.
- Ruta o ubicación: `reglas/CATALOGO_TAJOS.json`, configuración Obispo.
- Forma de uso: solo cuando resuelve esa obra.
- Ejemplo real: 41 tajos publicados para Obispo.
- Relacionado con: Obispo Orueta.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo y JS.
- Observaciones: no generalizar a viviendas.

## Techos

- Categoría: término de obra / familia de tajos.
- Definición: `techos` por vivienda y `techos_zzcc` para zonas comunes; Obispo añade `techos_wc`.
- Función dentro de SAGARDE: condición previa a acabados.
- Ruta o ubicación: catálogo.
- Forma de uso: estados separados.
- Ejemplo real: órdenes 237/240.
- Relacionado con: ZZCC, pintura, enchapado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo/memoria vigente.
- Observaciones: no fusionar variantes.

## Telecableado

- Categoría: término de telecomunicaciones / tajo.
- Definición: cableado interior de telecomunicaciones.
- Función dentro de SAGARDE: seguimiento por vivienda.
- Ruta o ubicación: catálogo, id `telecableado`.
- Forma de uso: celda.
- Ejemplo real: orden 150.
- Relacionado con: montante teleco, telembornado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: separado del cableado eléctrico.

## Telecomunicaciones

- Categoría: término de telecomunicaciones / concepto funcional.
- Definición: disciplina representada por tajos propios de cableado, embornado, mecanizado, portero y montantes.
- Función dentro de SAGARDE: separa seguimiento de telecomunicaciones del eléctrico cuando el catálogo lo distingue.
- Ruta o ubicación: `_SISTEMA.../reglas/CATALOGO_TAJOS.json`; adaptadores y fichas de obra.
- Forma de uso: IDs como `telecableado`, `telembornado`, `telemecanizado` y `montante_teleco`.
- Ejemplo real: tajo `Telemecanizado`.
- Relacionado con: Telecableado, Teleembornado, Telemecanizado, Montantes.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/reglas/CATALOGO_TAJOS.json`.
- Observaciones: no se encontró una capa de normativa telecom dinámica equivalente a una base de datos.

## Teleembornado

- Categoría: término de telecomunicaciones / tajo.
- Definición: conexión/embornado de teleco.
- Función dentro de SAGARDE: fase de conexiones.
- Ruta o ubicación: catálogo, id `telembornado`.
- Forma de uso: celda.
- Ejemplo real: orden 210.
- Relacionado con: telecableado, telemecanizado.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: la grafía visible es `Telembornado`.

## Telemecanizado

- Categoría: término de telecomunicaciones / tajo.
- Definición: instalación de mecanismos de teleco.
- Función dentro de SAGARDE: tajo por vivienda.
- Ruta o ubicación: catálogo, id `telemecanizado`.
- Forma de uso: celda.
- Ejemplo real: orden 280.
- Relacionado con: mecanizado, placas/tapas.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: algunas memorias conservan variantes de mayúsculas.

## Termostatos

- Categoría: término eléctrico / tajo.
- Definición: instalación de termostatos.
- Función dentro de SAGARDE: seguimiento interior por vivienda.
- Ruta o ubicación: catálogo, id `termostatos`.
- Forma de uso: celda.
- Ejemplo real: orden 170.
- Relacionado con: instalación interior.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: el código no define fabricante ni protocolo.

## Tierras

- Categoría: concepto eléctrico / aplicación.
- Definición: herramienta de informes y cálculo de puesta a tierra.
- Función dentro de SAGARDE: datos, métodos, equipo, sugerencias e informe.
- Ruta o ubicación: `VARIOS/TIERRAS/app_informe_tierras.html`.
- Forma de uso: cinco pestañas, JSON, fotos, cálculo e impresión.
- Ejemplo real: botón `Estimar electrodos necesarios desde ρ`.
- Relacionado con: localStorage, informe.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: HTML actual.
- Observaciones: carga Google Fonts; no la llama el motor de obras.

## Tubeado de zonas comunes

- Categoría: término eléctrico / tajo.
- Definición: tubeado de ámbito común.
- Función dentro de SAGARDE: infraestructura `z`.
- Ruta o ubicación: catálogo, id `tubeado_zzcc`.
- Forma de uso: estado de zonas comunes.
- Ejemplo real: orden 60.
- Relacionado con: cableado ZZCC.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: no se suma por vivienda necesariamente.

## Tubeado interior

- Categoría: término eléctrico / tajo.
- Definición: colocación de tubos en vivienda.
- Función dentro de SAGARDE: tajo común interior.
- Ruta o ubicación: catálogo, id `tubeado`.
- Forma de uso: celda.
- Ejemplo real: orden 130.
- Relacionado con: cableado, cuadros presentados.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo.
- Observaciones: separado de tubeado ZZCC.

<a id="u"></a>

## Ubicación

- Categoría: dato.
- Definición: combinación edificio/portal, planta y unidad.
- Función dentro de SAGARDE: ámbito donde se mide cada tajo.
- Ruta o ubicación: ficha `estructura`; snapshot `building/floor/unit`.
- Forma de uso: clave de estado junto al tajo.
- Ejemplo real: `ZR1.1 / PB / A2`.
- Relacionado con: planta, vivienda, clave sidecar.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: ficha y `_indice_ubicaciones`.
- Observaciones: unidad puede ser vivienda, local, apartamento o zona.

<a id="v"></a>

## Vacío

- Categoría: estado / símbolo.
- Definición: no iniciado en snapshot; si fue observado y validado se persiste como P en ficha.
- Función dentro de SAGARDE: peso 0 en KPI.
- Ruta o ubicación: `motor_informes.SCORE['']`; ficha `MAPA_ESTADO`.
- Forma de uso: celda sin marca.
- Ejemplo real: ciclo inicial del generador.
- Relacionado con: P, `?`.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: motor/ficha/generador.
- Observaciones: un blanco no validado puede ser ilegible; no asumir significado.

## VERIFICAR

- Categoría: estado visible.
- Definición: prioridad que requiere aclaración antes de ejecutar.
- Función dentro de SAGARDE: impedir tratar una duda como trabajo listo.
- Ruta o ubicación: priorizador y panel.
- Forma de uso: filtro/badge.
- Ejemplo real: texto `VERIFICAR nunca se considera ejecutable`.
- Relacionado con: LISTO, DUDAS.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `panel_obra.py:375` y agrupación del priorizador.
- Observaciones: no es un estado de celda.

## VIABLE

- Categoría: estado derivado.
- Definición: categoría de trabajo ejecutable según reglas.
- Función dentro de SAGARDE: priorizar tajos de Sagarde.
- Ruta o ubicación: `priorizador_trabajos.py`.
- Forma de uso: cálculo interno y sección `Tajos viables`.
- Ejemplo real: orden de categoría 0.
- Relacionado con: LISTO, BLOQUEADO.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: constantes del priorizador.
- Observaciones: puede convertirse en LISTO en la agrupación visible.

<a id="x"></a>

## X

- Categoría: estado / símbolo.
- Definición: tajo terminado al 100%.
- Función dentro de SAGARDE: único estado que suma en KPI estricto; peso 1 en ponderado.
- Ruta o ubicación: motor, ficha, generador.
- Forma de uso: marca de revisión.
- Ejemplo real: `SCORE['X']=1.0`.
- Relacionado con: M, `/`.
- Estado: CONFIRMADO POR CÓDIGO.
- Evidencia: `motor_informes.py:37,52-56`.
- Observaciones: una marca explícita M o `/` posterior puede rebajar X; un vacío se trata con cautela.

<a id="z"></a>

## ZZCC

- Categoría: término de obra / abreviatura.
- Definición: forma usada para “zonas comunes” en nombres visibles y IDs.
- Función dentro de SAGARDE: identificar ámbito `z`.
- Ruta o ubicación: catálogo: tubeado, cableado, techos, agujeros, pintura e iluminación ZZCC.
- Forma de uso: nombre de tajo/alcance.
- Ejemplo real: `Cableado de zonas comunes`.
- Relacionado con: SSCC, rellanos.
- Estado: CONFIRMADO POR CONFIGURACIÓN.
- Evidencia: catálogo y `AMBITO_NOMBRE`.
- Observaciones: no confundir con servicios comunes (SSCC).


# 4. Llamadas a skills

Solo se consideran llamadas reales las sintaxis presentes en el repositorio. Los comandos Python de una skill se reproducen porque constan literalmente en su archivo; no se propone sintaxis nueva.

| Skill | Forma exacta de llamada | Dónde se utiliza | Parámetros | Resultado esperado | Evidencia |
|---|---|---|---|---|---|
| `generate-cardiva-report` | `$generate-cardiva-report` | Codex | Plantilla y partes autorizados o JSON normalizado | Informe DOCX/PDF A4 con puntos 01–09 y anexos | skill canónica y `APP_CARDIVA/README.md` |
| `generate-cardiva-report` | `/generate-cardiva-report` | Claude Code | Los mismos archivos autorizados | Mismo flujo CARDIVA | `.claude/skills/generate-cardiva-report/SKILL.md` |
| `generate-cardiva-report` | activación por descripción; `/skills` para comprobar | Gemini CLI | Los mismos archivos autorizados | Mismo flujo CARDIVA | `.gemini/skills/generate-cardiva-report/SKILL.md` |
| `sagarde-actualizar` | `/sagarde-actualizar` | Tabla de skills del motor | Alcance solicitado | Nivel mínimo de actualización | `_MOTOR_SAGARDE/CLAUDE.md:12` |
| `sagarde-actualizar` | `python "_MOTOR_SAGARDE\scripts\regenerar_obra.py" <obra_id>` | Nivel 1 de la skill | ID corto | Ficha/memoria/prioridades/panel/PDF/caché de una obra | archivo de agente, nivel 1 |
| `sagarde-actualizar` | `cd "SAGARDE OBRAS ABIERTAS\_SISTEMA INFORME SAGARDE IA"` + `python generar_todos.py --solo-revisiones` | Nivel 2 | ninguno | `obras_revisiones.js` | archivo de agente, nivel 2 |
| `sagarde-actualizar` | `python "_MOTOR_SAGARDE\scripts\regenerar_obra.py" --finalizar` | Nivel 3 | caché válida | índices/resumen/registro | archivo de agente, nivel 3 |
| `sagarde-actualizar` | `Actualizar_Sagarde.bat` | Nivel 4 | autorización expresa | pipeline global + publicación | archivo de agente, nivel 4 |
| `sagarde-revision` | `/sagarde-revision` | Tabla del motor | Obra/revisión | protocolo de campo a memoria | `_MOTOR_SAGARDE/CLAUDE.md:13` |
| `sagarde-revision` | `sagarde-revision` | Instrucción raíz | PDF corregido | flujo completo | `CLAUDE.md:195` |
| `sagarde-revision` | `python "_MOTOR_SAGARDE\scripts\validar_revision_pdf.py" <obra_id> "<pdf_candidato>"` | Paso 1 | ID, PDF | diagnóstico sin escritura | skill revisión |
| `sagarde-revision` | `python "_MOTOR_SAGARDE\scripts\regenerar_obra.py" <obra_id>` | Paso 4 | ID | estado de obra actualizado | skill revisión |
| `sagarde-revision` | `python generar_todos.py --solo-revisiones` | Paso 5, desde `_SISTEMA...` | ninguno | registro del generador | skill revisión |
| `sagarde-nueva-obra` | `/sagarde-nueva-obra` | Tabla del motor | Nombre/ID/estructura | entorno nuevo | `_MOTOR_SAGARDE/CLAUDE.md:14` |
| `sagarde-nueva-obra` | `python generar_todos.py --no-pdf` + `python sagarde_portal.py` | Paso 6 | configuración previa | salidas/portal | skill; instrucciones parcialmente obsoletas |
| `sagarde-parte-incidencia` | **NO CONFIRMADO** | No se halló llamada nominal | — | — | búsqueda global sin coincidencias fuera de la definición |
| `sagarde-parte-incidencia` | import `generar_parte_incidencia as gp`; `gp.generar_pdf(incidents, output)` | Ejemplo interno de la definición | lista de dicts/ruta | PDF | `.claude/agents/sagarde-parte-incidencia.md`, paso 3 |
| Superpowers | `superpowers:using-superpowers` | `CLAUDE.md` | NO CONFIRMADO | Flujo externo | instrucciones raíz |
| Superpowers | `superpowers:brainstorming` | `CLAUDE.md`/planes | NO CONFIRMADO | Flujo externo | referencias documentales |
| Superpowers | `superpowers:writing-plans` | `CLAUDE.md`/planes | NO CONFIRMADO | Plan | referencias documentales |
| Superpowers | `superpowers:subagent-driven-development` | `CLAUDE.md`/SDD | NO CONFIRMADO | Ejecución con subagentes | referencias documentales |
| Superpowers | `superpowers:systematic-debugging` | `CLAUDE.md` | NO CONFIRMADO | Depuración | referencia documental |
| Superpowers | `superpowers:verification-before-completion` | `CLAUDE.md` | NO CONFIRMADO | Verificación | referencia documental |
| Superpowers | `superpowers:requesting-code-review` | `CLAUDE.md` | NO CONFIRMADO | Revisión | referencia documental |
| Superpowers | `superpowers:dispatching-parallel-agents` | `CLAUDE.md` | NO CONFIRMADO | Paralelización | referencia documental |
| Superpowers | `superpowers:executing-plans` | planes | NO CONFIRMADO | Ejecución | referencias documentales |
| `artifact-design` | `Skill(artifact-design)` | permiso local | NO CONFIRMADO | NO CONFIRMADO | `.claude/settings.local.json` |

# 5. Palabras clave de interfaz

| Palabra visible | Tipo | Pestaña o vista | Acción | Implementación | Evidencia |
|---|---|---|---|---|---|
| Inicio | pestaña | portal móvil | mostrar KPI/alertas | `tab(0)` | portal HTML/Python |
| Obras | pestaña | portal móvil | mostrar obras IA | `tab(1)` | idem |
| Post-ventas | pestaña/nav | portal | mostrar/abrir área | `tab(2)`/enlace | portal |
| Mantenimientos | pestaña/nav | portal | mostrar/abrir | `tab(3)`/enlace | portal |
| Cerradas | pestaña | portal móvil | lista/búsqueda | `tab(4)` | portal |
| Panel | pestaña | panel de obra | resumen | `v-panel` | `panel_obra.py:477` |
| Trabajos | pestaña | panel | tablas/bloqueos | `v-trabajos` | `:478` |
| Materiales | pestaña | panel | tabla material | `v-materiales` | `:479` |
| Personal | pestaña | panel | personal asignado | `v-personal` | `:480` |
| Prioridades | pestaña | panel | prioridades/dudas | `v-prioridades` | `:481` |
| Riesgos | pestaña | panel | riesgos | `v-riesgos` | `:482` |
| Normativa | pestaña | panel | referencias | `v-normativa` | `:483` |
| Documentos | pestaña | panel | enlaces | `v-docs` | `:484` |
| Actualizar | pestaña | panel | instrucciones BAT | `v-actualizar` | `:485` |
| LISTO | filtro/estado | Prioridades | mostrar listos | `data-fase` | JS panel |
| VERIFICAR | filtro/estado | Prioridades | mostrar dudas | `data-fase` | JS panel |
| Ver cálculo y detalle completo | enlace | Prioridades | abrir JSON | `prioridades_trabajos.json` | panel fuente |
| Informe Ejecutivo PDF | enlace | cabecera panel | abrir PDF | `target=_blank` | panel fuente |
| Copiar ruta completa | botón | Actualizar | clipboard | `navigator.clipboard` | panel fuente |
| Obra / Estructura / Tajos / Generar | pasos | generador | avanzar wizard | `step-1`…`step-4` | generador HTML |
| Todos / Ninguno / Solo Sagarde / Solo vivienda | botones | Tajos | selección | handlers JS | generador |
| Descargar HTML | botón | Generar | descarga Blob | código JS | generador |
| Vista previa | botón | Generar | renderizar | código JS | generador |
| Guardar config | botón | Estructura | localStorage | `saveCfg` | generador |
| Imprimir | botón | hoja generada | `window.print()` | plantilla | generador |
| Guardar revisión | botón | hoja generada | localStorage | `autoSave` | generador |
| Limpiar | botón | hoja generada | borrar estados | `doClear` | generador |
| Todas / Recientes / Vencidas / Con PDF / Con Word / Con fotos | filtros | Postventa | filtrar tarjetas | `data-filter` | `postventas_index.py:645-651` |
| VENCIDO | badge | Postventa | informar >2 años | `is_vencido` | postventa fuente |
| pendiente | badge/fila | Postventa/preview | resaltar incidencia | `row_is_pending` | postventa fuente |
| Datos Generales / Condicionantes y Métodos / Equipo / Sugerencias / Generar Informe | pestañas | Tierras | cambiar formulario | `showTab` | Tierras HTML:214-219 |
| Exportar sesión (.json) | botón | Tierras | descargar JSON | Blob | Tierras |
| Generar informe / Imprimir PDF | botón | Tierras | preview/print | JS | Tierras |
| Nueva Revisión / Historial / Perfiles | pestañas | Baterías | cambiar vista | `showTab` | Baterías HTML:190-203 |
| Guardar informe / Abrir informe | botones | Baterías | exportar/importar JSON | FileReader/Blob | Baterías |
| Todos / 2021…2026 | filtros | Nóminas | filtrar años | JS | nóminas HTML |
| Enero…Diciembre | pestañas | Registros | mostrar mes | tabs por año | 8 HTML anuales |

# 6. Estados, símbolos y códigos

| Símbolo o código | Significado | Contexto | Regla de interpretación | Evidencia |
|---|---|---|---|---|
| `X` | Terminado 100% | ficha/snapshot/revisión | 1,0 ponderado; único avance estricto | motor/ficha |
| `M` | Más del 50% | idem | 0,60 ponderado | motor/priorizador |
| `/` | Iniciado, menos del 50% | idem | 0,25 ponderado | motor/priorizador |
| vacío `""` | No iniciado en snapshot | revisión/motor | 0; si fue validado se persiste P | ficha/motor |
| `P` | Pendiente confirmado | ficha | se exporta como vacío al snapshot | ficha |
| `?` | Desconocido/no mirado | ficha | se excluye del snapshot | ficha |
| `N` | No aplicable | ficha | se excluye del denominador | ficha |
| `·` | Representación visual de N | hoja generada | `SYM.N='·'` | generador |
| `LISTO` | Prioridad ejecutable | panel/priorizador | situación agrupada | código |
| `VERIFICAR` | Requiere confirmación | panel/priorizador | nunca ejecutable hasta confirmar | panel |
| `VIABLE` | Categoría ejecutable | priorizador | categoría derivada | priorizador |
| `BLOQUEADO` | Dependencia/interferencia | priorizador | categoría derivada | priorizador |
| `OTROS_GREMIOS` | Condición de tercero | priorizador | categoría derivada | priorizador |
| `DUDAS` | Ambigüedad | priorizador | categoría derivada | priorizador |
| `TERMINADO` | Categoría cerrada | priorizador | categoría derivada | priorizador |
| `Si`, `S`, `Sí`, `Ok` | Resuelta | tabla Word postventa | comparación case-insensitive en penúltima celda | `RESOLVED_TOKENS` |
| `VENCIDO` | Postventa >2 años | índice postventa | fecha real o fallback; override Garellano | `is_vencido` |
| `recent` | Actividad ≤45 días | índice postventa | `is_recent` | fuente postventa |
| `warning` / `info` | severidad de auditoría | diagnóstico | conteo separado | auditor JSON |
| `gernika`, `mungia`, `bolueta`, `obisporueta`, `gorliz` | IDs cortos | registro/CLI | resolución case-insensitive; alias oficial | `registro_obras.py` |
| `p1__5__pint-1__A` | clave corta de celda | sidecar | portal/planta/tajo/unidad | skill revisión |
| `src_<obra>_*` | IDs publicados | JS generador | identificadores derivados de ficha/prioridades | `obras_revisiones.js` |
| `rev_DDMMAAAA` | ID de revisión | ficha | fecha de revisión | `ficha_obra.py` |
| `sgd_rev_cfg_*` | configuración generador | localStorage | una clave por obra | generador |
| `sgd_rev_recents` | recientes generador | localStorage | máximo 8 | generador |
| `sgd_rev_*` | estados de hoja | localStorage | clave por obra/fecha | plantilla generada |
| `tierras_v1`, `tierras_med_v1`, `tierras_med_v1_backup`, `tierras_dark` | estado Tierras | localStorage | sesión/medidas/backup/tema | Tierras |
| `sgd_perfiles`, `sgd_historial` | estado Baterías | localStorage | perfiles e historial | Baterías |

# 7. Sinónimos, variantes y términos ambiguos

| Término principal | Variante | ¿Equivalentes? | Diferencia | Evidencia |
|---|---|---|---|---|
| Mungia | MUNGIA | Sí en registro | Alias case-insensitive | registro |
| Mungia | MUNGUIA | NO CONFIRMADO como alias de obra | Aparece en nombres de postventa/documentos, no en aliases del registro | árbol/registro |
| Gernika | Guernica | No como alias del motor | Variante lingüística en transcripción; registro solo `GERNIKA` | registro/transcripción |
| Obispo Orueta | Obispo Orueta 2 | Relacionados, no idénticos | nombre de obra vs referencia de bloque/portal | registro |
| Bolueta | BOLUETA / 2026 BOLUETA ACR | Sí según contexto | alias corto vs nombre oficial | registro |
| Portal único | BOLUETA | Equivalentes solo por configuración Bolueta | `alias_portales_revision` | registro |
| Ficha de obra | base viva | Sí como concepto documental | fichero concreto vs descripción arquitectónica | ficha/planes |
| Estado vacío | P | No en almacenamiento; sí al snapshot | P conserva que fue comprobado | ficha |
| Estado vacío | `?` | No | vacío/P afirma pendiente; `?` desconoce | ficha |
| N | vacío | No | N no entra en denominador | ficha |
| ZZCC | SSCC | No | zonas comunes vs servicios comunes según nombres del catálogo | catálogo |
| Cableado | Cableado ZZCC | No | vivienda vs zonas comunes | catálogo |
| Tubeado | Tubeado ZZCC | No | vivienda vs zonas comunes | catálogo |
| Techos | Techos ZZCC / Techos WC | No | ámbitos/tajos distintos | catálogo |
| Mecanizado | Telemecanizado | No | electricidad vs telecomunicaciones | catálogo |
| Embornado | Telembornado | No | electricidad vs telecomunicaciones | catálogo |
| Pintura antigua | primera/segunda mano | Relación histórica, no equivalencia simple | adaptador especializa según estado antiguo | memoria/adaptador Bolueta |
| `placas_tapas` común | override Obispo | Mismo ID, metadatos específicos | precedencia de configuración de obra | catálogo |
| `Lucido Paredes` | `Lucido paredes` | Probablemente mismo texto, no normalizado en memoria | difieren por mayúsculas | memoria Obispo |
| `telemecanizado` | `Telemecanizado` | Mismo concepto probable | claves JSON distintas por caso | memorias |
| Agent Skill | agente local histórico | No | la Agent Skill tiene `SKILL.md`; los protocolos antiguos son Markdown bajo `.claude/agents` | árbol y registro multi-IA |
| Plan | comportamiento | No | plan describe intención; código confirma ejecución | planes/código |
| Postventa | mantenimiento | No | áreas, reglas y carpetas distintas | código/portal |
| `PORT AL` | `PORTAL` | Variante de extracción | normalización compartida corrige espacio espurio | tests ficha |

# 8. Términos pendientes de verificar

| Término | Posible significado | Motivo de duda | Archivos consultados | Dato necesario |
|---|---|---|---|---|
| `T` / `C` en Mecanismos WC | iniciado y >50% en algún orden | memoria dice que no se recuerda cuál | memoria vigente, adaptador Obispo | confirmación de obra/fuente original |
| Montantes (fila histórica genérica) | combinación de montantes | memoria prohíbe inferir alcance | memoria, catálogo | definición de esa hoja concreta |
| Primera revisión Gorliz | snapshot inicial | no existe archivo oficial | adaptador, carpeta, JS | revisión validada |
| Estructura completa Obispo | 57 habitaciones/posiciones posibles | no hay ficha y handoff dejó duda | handoff, prioridades, adaptador | estructura confirmada |
| Locales PB Bolueta | dos locales sin etiqueta física | handoff no confirma nombres | handoff, ficha | etiquetas oficiales |
| `artifact-design` | skill externa | solo permiso `Skill(...)` | settings | inventario de capacidades del host |
| `superpowers:*` | skills externas | solo referencias y artefactos | CLAUDE/planes/SDD | instalación fuera del repo |
| `/sagarde-parte-incidencia` | posible llamada | definición no muestra sintaxis ni referencias | agente y búsqueda global | convención real de invocación |
| `sagarde-nueva-obra` actual | protocolo de alta | definición contradice registro/esquema | skill, registro, ficha | actualización autorizada del protocolo |
| Portal móvil | interfaz vigente | launch lo ofrece, pero no se regenera | launch, Python, HTML | decisión de mantener y corrección futura |
| Egurrola/Zorrozaure | adaptadores históricos | rutas abiertas rotas y obras en OLD | adaptadores/árbol/registro | intención de conservación o reubicación |
| Dinamita | futura obra automatizada | PROCEDIMIENTO la deja pendiente; no hay adaptador | procedimiento/árbol | confirmación y adaptador |
| Propietario del componente | Bixente como único usuario | no CODEOWNERS ni responsables por módulo | CLAUDE/árbol | asignación formal |
| Versiones de dependencias | conjunto probado | no manifiesto ni pins | imports/BAT | fichero de dependencias o registro externo |




