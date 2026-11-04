E — Extremidades y contrato de enchufe
Fecha: 04/11/2026 · Rama: nube/integracion-extremidades (base origin/main = 3415610) · Estado: auditoría y diseño en papel. No se ha modificado código ni datos, no se ha ejecutado ningún .bat ni nada que escriba en main.

Norte (Bixente): el entorno funciona «como un ente vivo»: un cuerpo (la base común de datos de obra) y extremidades (apps) que beben de él y lo alimentan; los .bat son la circulación; el centro de mando es el control. Debe servir en PC, tablet y móvil.

Principio vigente (CLAUDE.md:265-283, §7c, 25/10/2026): una app no es una app suelta, es una aportación de datos: genera un fichero → se pasa a mano a REVISIONES → «actualiza la obra» → el .bat regenera → el portal lo muestra. Sin «recibir/ingerir», sin .bat propios, sin carpetas de app propias.

Leyenda de certeza: CONFIRMADO = leído en código/datos versionados de este checkout. INFERIDO = consecuencia razonable, no ejecutada. NO VERIFICABLE = vive fuera de git (OneDrive, Cloudflare, .claude/agents, .gemini, APP_CARDIVA, Excel…): no concluyo que no exista.

Método y límites. Lectura estática del checkout (590 ficheros versionados). No ejecuté la suite ni los generadores. Contrasté el mapa mental (_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md) con el código: hay desfases (§5). No he leído nombres, teléfonos ni horas de personas concretas; donde hablo de datos personales lo hago por estructura y recuentos.

1. Resumen
El cuerpo existe y es sólido en una sola vía: revisiones de tajos (adaptador → REVISION_NORMALIZADA → validar → aplicar en memoria → doble cálculo → ficha → traza JSONL) y, copiándola, el control horario de la tablet (lector_control_horario.py: SHA256, vista previa, «a revisar», rechazo con motivo). Esas dos vías son el modelo del contrato (§3).
Todo lo demás son islas o ramas parciales: Tierras, Baterías, CARDIVA, postventa, materiales, tareas Excel, cierre de expediente, Buscador. Ninguna aporta un fichero que entre por REVISIONES; la mayoría guarda estado en localStorage de un navegador o en un Word/Excel que git no ve.
Lo más preocupante no es una isla: es privacidad. El repo es público y publica (a) nombres de pila + empresa + horas por día de 22 trabajadores (decisión consciente de Bixente, .gitignore:73-74), (b) 92 vistas previas de postventa con ≈3.400 secuencias con forma de teléfono (INFERIDO, §5.1), (c) un informe de tierras de un cliente (VARIOS/TIERRAS/PARTES DE TIERRA DE/…) pese a que .gitignore:200 dice que las «tierras de cliente» se quedan fuera (comentario :193-201).
Hay caminos paralelos vivos que el principio daba por retirados: personal_obra.py ingerir (personal_obra.py:1893), el script de Codex .agents/skills/update-sagarde-works/… (:239-266), y una segunda puerta de entrada para BASE TRABAJADORES dentro de una función llamada «exportar» (personal_integracion.py:189-201).
Crítica a la metáfora: hoy el «ente vivo» es un proceso por lotes con un corazón humano (pasar el fichero a mano, decir «actualiza», lanzar el .bat en un PC Windows). La circulación no es continua. No es un defecto si se asume; sí lo es si se vende como orgánico. Tablet y móvil leen y, solo la tablet de Personal, aporta; el traslado tablet→PC no está definido en el repo (NO VERIFICABLE).
Recomendación: no construir más extremidades hasta fijar el contrato (§3) y cerrar los caminos paralelos (§6, pasos 1-2). Orden de enchufe: materiales → caminos paralelos → Tierras → CARDIVA/Baterías (con «contrato de mantenimiento» como unidad) → postventa. Buscador y datos de nómina: no enchufar.
2. Inventario de extremidades
Clases: CUERPO = parte del motor/base; ENCHUFADA = cumple el modelo; PARCIAL = bebe o alimenta pero con huecos; DERIVADA = solo lee y publica; ISLA = estado o circuito propio.

2.1 Cuerpo y circulación (referencia, no extremidades)
Pieza	Qué es	Evidencia	Cert.
Registro de obras	Único sitio donde se da de alta una obra (id, alias, carpeta, materiales). 7 obras; Gorliz registrada sin ficha ni revisión	registro_obras.py:12-60 (Gorliz :49-60); solo 6 ficha_obra.json versionados	CONFIRMADO
Catálogo de tajos	Ids y alias de tajo, orden, dependencias (v1.3)	reglas/CATALOGO_TAJOS.json; versionado pese a .gitignore:2 (§5.2)	CONFIRMADO
Ficha por obra	ficha_obra.json (+ficha_garajes.json), esquema con version	…/INFORME SAGARDE IA/ficha_obra.json (6 obras)	CONFIRMADO
Circulación «una obra»	Detecta hojas y controles horarios, simula, aplica, regenera solo esa obra y verifica que las demás no se mueven; código 3 si hay que mirar	_SISTEMA/MOTOR/scripts/actualizar_obra.py:1-14, :245 (detectar_hojas), :1017	CONFIRMADO
Circulación «todas»	Actualizar_Sagarde.bat: auditor (:16) → generar_todos.py (:32) → postventa/mantenimientos → portal → mapa → git add -A (:100) → push origin main (:112)	Actualizar_Sagarde.bat	CONFIRMADO
Centro de mando	sagarde_portal.py escanea el árbol y los resumen_*.json; es estático	_SISTEMA/MOTOR/sagarde_portal.py:52-62, :102-103, :1433-1466	CONFIRMADO
2.2 Extremidades
#	Extremidad	Bebe de la base (qué, vía)	Alimenta la base (fichero, vía)	Clase	Evidencia fichero:línea	Cert.
E1	Generador de revisiones (generador_revisiones.html)	Registro de obras vía obras_revisiones.js, generado y publicado por el motor	REVISION <OBRA> <DDMMAAAA>.html (+_garaje) a mano a REVISIONES/; lo lee adaptar_revision_html.py. localStorage solo borrador y «recientes»	ENCHUFADA (modelo)	generador_revisiones.html:358 (carga registro), :371-387 (nombre de fichero), :1666-1671,1807 (borradores); generar_todos.py:29,990 (escribe el .js)	CONFIRMADO
E2	Tablet «Personal en obra» (generador_personal.html + personal_sw.js + manifest)	personal_estado.js (todas las obras del registro, con o sin jornadas)	CONTROL HORARIO <OBRA> <DDMMAAAA>.json (tipo: lote_personal, version: 1) a mano a REVISIONES/; lo lee lector_control_horario.py	ENCHUFADA (con matices §3.4)	generador_personal.html:7,987,1002,3651-3655,3773; lector_control_horario.py:130-137,387-418; personal_integracion.py:189-236	CONFIRMADO
E3	Ranking + «Generar personal» (personal_sagarde.html)	personal_estado.js	BASE TRABAJADORES SAGARDE <DDMMAAAA>.json (obra: sagarde): altas, empresas, oficios, bajas	ENCHUFADA con desviación: se aplica en exportar_estado_real, no solo por «actualiza la obra»	personal_sagarde.html:2210,2228,1984; personal_integracion.py:195-201; lector_control_horario.py:135	CONFIRMADO
E4	Hojas de materiales (hoja de entrega de materiales <OBRA>.xlsx)	Nada de la ficha: no cruza con tajos ni portales	Excel editado a mano o por IA; el panel lee los valores. Formato registro (Olabeaga: hoja ENTREGAS) o rejilla (Mungia, Bolueta)	PARCIAL: sin SHA, sin traza, fuente fuera de git	entregas_materiales.py:1-45; generar_todos.py:1835-1845; registro_obras.py (materiales_rel); CLAUDE.md:202-263	CONFIRMADO (el .xlsx: NO VERIFICABLE)
E5	Tareas manuales (FICHA DE OBRA.xlsx, hoja Tareas; nota_pendiente.py; panel_server.py)	Panel estático con hilos_notas.py (sanea contactos)	nota_pendiente.py escribe filas en el Excel; POST /api/marcar_hecho en servidor local cambia Pendiente⇄Hecho	PARCIAL: estado maestro de tareas en Excel no versionado; único escritor desde el portal	nota_pendiente.py:1-40; panel_server.py:15-18,65; hilos_notas.py:1-40	CONFIRMADO (el .xlsx: NO VERIFICABLE)
E6	Cierre de expediente (cierre_expediente.json)	Panel e informe ejecutivo lo leen	Datos «a mano, al margen de la rejilla»; CLI que escribe directo	PARCIAL: sin fichero de aportación ni traza	cierre_expediente.py:1-8,129-132	CONFIRMADO
E7	Informe ejecutivo PDF	ficha + historial + prioridades + cierre	PDF canónico INFORME_EJECUTIVO_<OBRA>.pdf (único fichero forzado con add -f)	DERIVADA	_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py; Actualizar_Sagarde.bat:103	CONFIRMADO
E8	Panel de obra / informe a la carta	ficha, prioridades, materiales, personal	panel.html (publicado)	DERIVADA	panel_obra.py:1977,2333	CONFIRMADO
E9	App Tierras (app_informe_tierras.html)	Nada	Estado en localStorage (tierras_v1, tierras_med_v1); exporta/importa un .json propio de copia; imprime informe. Sin id de obra	ISLA	VARIOS/TIERRAS/app_informe_tierras.html:2541-2546,2556-2557,2571,2582,2616-2625	CONFIRMADO
E10	App Baterías de condensadores (app_informes.html)	Nada	localStorage (sgd_perfiles, sgd_historial) + archivo «datos app» que el usuario guarda en OneDrive para sincronizar entre equipos	ISLA (circuito propio de sincronización)	VARIOS/BATERIAS DE CONDENSADORES/app_informes.html:1168,1270,1367,1397-1409	CONFIRMADO
E11	Buscador Eléctrico (HTML + Worker de Cloudflare)	Biblioteca de libros (fuera del repo), IA externa	Nada. Clave en localStorage; consulta por fetch POST a *.workers.dev	ISLA por diseño (legítima)	VARIOS/BUSCADOR ELECTRICO/app_buscador_electrico.html:101,120,262,283; spec …/2026-09-14-buscador-electrico-design.md	CONFIRMADO el cliente; Worker, índice y KV: NO VERIFICABLE
E12	CARDIVA (skill, plantilla, informes DOCX/PDF)	Nada de la base	Informe preventivo por JSON propio (identification, deficiencies, materials…) → DOCX/PDF a carpeta. El portal solo ve mtime	ISLA	.claude/skills/generate-cardiva-report/SKILL.md, references/data-schema.md:8-24; mantenimientos_index.py:33-38,164-183	CONFIRMADO; fuente canónica APP_CARDIVA/: NO VERIFICABLE (no versionada)
E13	Postventa: índice de incidencias (postventas_index.py)	Word matriz y PDF por carpeta (no versionados); estado por mtime	postventas_resumen.json + 92 vistas previas HTML	ISLA / DERIVADA de Word	postventas_index.py:26,305,734-795; POST-VENTAS/_SISTEMA/_PREVIEWS_WORD/ (92 ficheros)	CONFIRMADO
E14	Postventa: sincronizador y partes TYPO	Lee PDF digitales; CODE_RE extrae el código Sagarde	postventas_sync.py añade filas al Word (copia _BACKUP); generar_parte_incidencia.py JSON→PDF. Ninguno lo llama un .bat ni la skill	ISLA	postventas_sync.py:1-18,245-270; generar_parte_incidencia.py:239-240	CONFIRMADO
E15	Índice de mantenimientos	Árbol de carpetas	mantenimientos_resumen.json, index.html	DERIVADA (sin datos estructurados)	mantenimientos_index.py:164-183	CONFIRMADO
E16	Biblioteca técnica VARIOS/* (pegatinas, dudas REBT, recuento de mecanismos, centralizaciones, telecom, normativa)	—	—	ISLA documental (aceptable): son documentos, no datos de obra	.gitignore:202-216; sagarde_portal.py:320	CONFIRMADO
E17	VARIOS/PLANILLA y VARIOS/APPS SAGARDE (nómina, vida laboral)	—	Solo mtime y nº de ficheros llegan al portal	ISLA sensible, excluida de git	sagarde_portal.py:263-271; .gitignore:11	CONFIRMADO la exclusión; contenido: NO VERIFICABLE
E18	Skills y agentes versionados	Leen/ejecutan el motor	7 skills en .claude/skills/ (CARDIVA, actualizar-obra, cerrar-obra, informe-ejecutivo, nota-pendiente, personal, revisión) y .agents/skills/update-sagarde-works/scripts/… (solo script, sin SKILL.md)	CUERPO salvo .agents/…: camino paralelo (§4)	.agents/skills/update-sagarde-works/scripts/update_sagarde_works.py:239-266,338; no referenciado por ningún otro fichero (grep)	CONFIRMADO
E19	.claude/agents/* (4), .gemini/, GEMINI.md, .superpowers/, copias multi-IA de la skill CARDIVA	—	—	—	Anclados y no versionados (CLAUDE.md:312-318)	NO VERIFICABLE
E20	Adaptadores de obra (adaptadores/*.py, 9 ficheros)	historiales DOCX/PDF/HTML/JSON	historial común	CUERPO; Egurrola y Zorrozaure siguen versionados y sin uso	git ls-files …/adaptadores/; mapa :313	CONFIRMADO
3. Contrato de enchufe
Documento para toda extremidad nueva o existente. Modelo de referencia: generador de revisiones y tablet de Personal. Se entiende «obra» = id de registro_obras.py. Donde la unidad no es una obra (mantenimiento, postventa), hace falta primero un registro equivalente (§6).

3.1 Forma y nombre del fichero de aportación
Un fichero por entrega, hecho por la app, descargable. Nombre: <TIPO EN MAYÚSCULAS> <OBRA EN MAYÚSCULAS SIN TILDES> <DDMMAAAA>.<json|html> (patrón de REVISION … y CONTROL HORARIO …; copias (1), (2)). Se genera con la misma función de limpieza de nombre que el generador de revisiones (safeRevisionWorkName, generador_revisiones.html:371); no se reimplementa.
El nombre es solo para humanos: obra, fecha y contenido se leen de dentro. Si la obra interna no coincide con la carpeta donde está, se rechaza (obra_distinta, lector_control_horario.py:408-410).
Dónde se deja: <obra>/REVISIONES/, a mano. Nada de carpetas, buzones, «recibidos» ni rutas propias de la app. Si el fichero es global (no de una obra), se admite obra: "sagarde" solo para datos de la base común y debe poder dejarse en REVISIONES de cualquier obra.
Al terminar, la app dice qué hacer en 3 pasos: dónde dejar el fichero, qué decir («actualiza la obra X»), qué esperar. Sin la palabra «ingerir», «importar», «lote».
3.2 Esquema y versionado
Cabecera obligatoria: tipo (cadena registrada), version (entero), obra, generado_en (ISO con zona), dispositivo (texto libre, sin datos personales).
Esquema cerrado: un campo desconocido rechaza el fichero (campo_desconocido; modelo personal_obra.validar_lote, personal_obra.py:329-372). tipo o version desconocidos → rechazo con código (tipo_desconocido, version_desconocida).
Subir de versión = añadir una rama de lectura nueva; la antigua sigue leyéndose mientras haya ficheros viejos en disco.
Todo estado derivado persistente (<tipo>_obra.json) y toda traza llevan también version. (Hoy no es así: la traza de personal no la lleva, personal_integracion.py:69-72; el esquema de CARDIVA tampoco, data-schema.md:8-24.)
3.3 Identificadores
Dato	Se resuelve contra	Regla
Obra	registro_obras.OBRAS[].id y aliases	La app no lleva su lista de obras: lee la que el motor publica (obras_revisiones.js / <tipo>_estado.js). Obra desconocida → rechazo.
Persona	personal_catalogo.json (T####), nombre normalizado sin tildes ni mayúsculas, más nombres_anteriores	En datos de obra, solo el id. Nombre parecido, mismo nombre o empresa cambiada → «a revisar», nunca se adivina (lector_control_horario.py:38-46).
Tajo / ubicación	reglas/CATALOGO_TAJOS.json (id + alias) y claves de la ficha (portal, planta, vivienda)	Ambigüedad → confianza: dudosa, no se aplica. Tajo sin id resoluble → rechazo con motivo.
Unidad no-obra (contrato, incidencia)	Hoy no existe registro	Prerrequisito del enchufe (§6): registro propio, con la misma forma que registro_obras.py.
3.4 Validación y rechazo
Resultado por fichero: aplicado / a revisar (frena, código 3) / rechazado. Cada rechazo lleva codigo (para pruebas y auditor), texto en lenguaje llano para Bixente y detalle.
Nunca se descarta en silencio: todo lo no aplicado se cuenta y se muestra. Un fichero que falla no tumba a los demás ni a la obra (modelo _analizar_uno, lector_control_horario.py:387-418, except acotado con motivo).
Desconocido ≠ 0. Valor ausente = null/?, nunca 0. Cantidades ambiguas (1.200) y fechas ilegibles se rechazan con su fila (modelo entregas_materiales.py:32-36).
Datos privados (DNI, teléfono, correo, etiquetas HTML) en cualquier campo de texto libre → rechazo dato_privado (lector_control_horario.py:411-413; patrones en personal_obra.py:35).
Estado local de la app (localStorage): solo borrador, cola de pendientes y copia de solo lectura del estado publicado, con rótulo de «sin enviar» y fecha. Nunca el dato maestro. (La tablet de Personal guarda además altas/renombres pendientes, generador_personal.html:1038-1054: aceptable porque viajan dentro del fichero y la base no cambia hasta que el PC lo aplica.)
3.5 Idempotencia
Al aplicar, se anota el SHA256 de los bytes en la traza. Segunda vez → ya_aplicado; mismos bytes con otro nombre → copia_de (lector_control_horario.py:398-402).
Clave natural (obra + ámbito + fecha [+ persona]): «lo que se apunta en la última revisión es lo que vale»; un fichero posterior sustituye, no duplica.
Si se aplicó pero no se pudo anotar, se vuelve a ofrecer sin duplicar (no_anotado).
La traza no puede perder entradas en silencio. Hoy shas_recibidos salta las líneas ilegibles sin avisar (personal_obra.py:1160-1164): una línea dañada hace que ese fichero reaparezca como «listo». El contrato exige avisar.
3.6 Trazabilidad
<obra>/INFORME SAGARDE IA/<tipo>_aplicadas.jsonl: una línea por aplicación, aditiva, que no bloquea si falla (modelo trazabilidad_revisiones.py).
Claves mínimas: version, aplicado_en (ISO+zona), obra, tipo, sha256, fichero (nombre base, no ruta absoluta), n_aceptados, n_rechazados, avisos, dispositivo.
Sin rutas absolutas ni datos personales. (Hoy revisiones_aplicadas.jsonl guarda D:\Nueva carpeta\OneDrive\… en las 31 líneas de las 6 obras, §5.3.)
Un solo esquema de traza para todas las extremidades (hoy hay dos: aplicado_en+version en revisiones, ts sin version en personal).
3.7 Dónde viven los datos y quién escribe
Estado derivado en <obra>/INFORME SAGARDE IA/<tipo>_obra.json, esquema cerrado. Solo el lector del motor escribe. No se edita a mano (CLAUDE.md §7b: un XML/JSON editado a mano ya rompió una obra entera).
«Se guarda lo medido, se recalcula lo derivado» (CLAUDE.md §7): nada de persistir BLOQUEADO, VIABLE, totales ni rankings.
El portal es estático y no escribe. Los cambios se piden por el entorno («actualiza la obra», renombrar, fusionar). Excepción actual y única: panel_server.py para marcar tareas (E5).
3.8 Enganche al motor (sin .bat propio)
Un módulo lector_<tipo>.py con tres pasos: listar → analizar (vista previa, sin escribir) → aplicar. Sin CLI propia (el CLI paralelo personal_obra.py ingerir es justo lo que no debe repetirse).
Lo llaman actualizar_obra.py (vista previa, --escribir, sección propia en el informe de verificación, código 3 si hay «a revisar») y generar_todos.py (solo aplica los limpios; los dudosos quedan avisados). cerrar_obra.py se niega a cerrar con ficheros sin aplicar (modelo cerrar_obra.py:14). regenerar_obra.py --finalizar ejerce el camino completo.
El auditor del paso 0 (auditor_sagarde.py) avisa de ficheros sin aplicar y de rutas declaradas que no existen.
Prueba obligatoria de no colateralidad: foto SHA256 de las demás obras antes/después (modelo actualizar_obra.py:710). Obras de referencia que no deben moverse: las que cite CLAUDE.md §3 (:64-65), pero esas cifras están desfasadas (§5.2): tomar la foto «antes» en el momento, no las cifras escritas.
3.9 Pruebas unittest (stdlib; sin pytest ni dependencias)
Mínimo, en tests/test_<tipo>.py:

Fichero válido → se aplica y deja traza con SHA.
Esquema: campo desconocido, tipo y version desconocidos → rechazo con código.
Obra distinta a la carpeta; obra desconocida; id irresoluble → rechazo con motivo.
Dato privado → rechazo.
Idempotencia: aplicar dos veces ⇒ estado idéntico byte a byte; copia con otro nombre ⇒ copia_de.
«Última manda»: fichero posterior sustituye, no duplica.
Fichero ilegible/mal formado no tumba a los demás.
Dudoso ⇒ «a revisar», no se aplica ni se descarta.
Desconocido nunca se vuelve 0.
Foto SHA256 de otras obras idéntica.
Publicación (modelo tests/test_publicacion_personal.py): git check-ignore confirma que cada fichero declarado pasa por su propia regla, y que uno no declarado se queda fuera.
Jerarquía _SISTEMA (tests/test_jerarquia_sistema.py) y ruta del centro de mando (test_portal_areas.py).
Si hay lógica en JS y en Python: doble cálculo (modelo personal_calculo.js + auditar).
Si es app sin cobertura: prueba de service worker y manifest (modelo test_personal_sin_cobertura.py).
Prueba por mutación documentada: romper cada guarda y comprobar que alguna prueba se entera.
3.10 .gitignore y .bat
.gitignore (lista blanca) obligatorio, una línea por cada fichero de datos y por cada recurso de la app que no sea .html/.py (.js, .json, .png, manifest, sw): !SAGARDE OBRAS ABIERTAS/*/INFORME SAGARDE IA/<tipo>_obra.json, …/<tipo>_aplicadas.jsonl, etc. Con comentario del porqué y prueba (§3.9-11). Decidir expresamente si el fichero de entrada se publica (por defecto no: no tiene línea blanca).
Actualizar_Sagarde.bat no se toca y no se crea otro. Matiz que corrige CLAUDE.md §4: el .bat hace git add -A (:100), que respeta la lista blanca; solo el PDF ejecutivo se fuerza con add -f (:103). Un tipo nuevo normal exige tocar .gitignore, no el .bat. Si la extremidad necesita un paso nuevo, se engancha dentro de generar_todos.py.
No usar git add -f como atajo: un fichero ignorado pero ya rastreado engaña (§5.2).
3.11 Privacidad (repo público)
Cada campo se clasifica antes de escribir una línea: público / interno / prohibido. Prohibido en cualquier fichero versionado: DNI, teléfono, correo, dirección personal, nombre de cliente final, nómina o vida laboral, claves, tokens, URLs privadas, rutas absolutas del PC.
Personas: ids T#### en datos de obra; nombres solo en el catálogo, con decisión expresa de Bixente (hoy publicado, §5.1).
El auditor revisa con regex DNI/teléfono/correo los ficheros nuevos de la extremidad antes de publicar.
Para pruebas y para cualquier IA gratuita o subagente: datos inventados («Trabajador A»), nunca reales.
Lo sensible (partes manuscritos, fotos, nóminas) se queda en OneDrive; al cuerpo solo llega el resumen estructurado.
3.12 PC, tablet y móvil
App de campo = HTML estático servido desde Pages, viewport, sin servidor propio. Si debe funcionar sin cobertura: manifest + service worker + iconos (todos con línea en .gitignore) y texto de cobertura en llano (modelo generador_personal.html:7,1002).
Lee el estado publicado por el motor (<tipo>_estado.js) con todas las obras del registro, también las de 0, para que un 0 se vea (CLAUDE.md §2: un recuento de 0 es alarma).
Tablet/móvil → PC: hoy es «a mano». El repo no dice cómo (OneDrive, USB, correo): NO VERIFICABLE. El contrato obliga a escribirlo en la skill de la extremidad.
Procesar/publicar sigue siendo solo PC Windows (actualizar_obra.py:42 PYTHON = ["py","-3.11"]; los .bat). No prometer lo contrario.
3.13 Cómo aparece en el centro de mando
Declaración explícita, no heurística: hoy una app sale en «Aplicaciones» si su nombre contiene app, panel, sagarde, plantilla o generador (sagarde_portal.py:28); una app llamada de otra forma desaparece sin aviso. Declararla en APPS_OBRAS_ABIERTAS (:33-37), cuyo test ya comprueba que la ruta existe.
Contadores por obra: ficheros vistos / aplicados / a revisar / rechazados, fecha del último aplicado. Pestaña o sección en el panel y línea en el informe de verificación de «actualiza la obra».
Un 0 visible y distinguible de «no aplica».
Entrada en resumen_obras.json (tarjeta) y, si procede, en el informe a la carta.
Aviso en el auditor si hay ficheros sin aplicar.
Entrada en el mapa mental en la misma sesión (norma CLAUDE.md §5).
3.14 Checklist de aceptación (15 líneas)
[ ] 1. La app solo genera un fichero con nombre <TIPO> <OBRA> <DDMMAAAA> (misma limpieza que las revisiones); no guarda datos maestros.
[ ] 2. El fichero se deja a mano en <obra>/REVISIONES y entra con "actualiza la obra"; no hay .bat, carpeta, alta ni CLI propios.
[ ] 3. Cabecera con tipo, version, obra, generado_en, dispositivo; esquema cerrado; tipo/version desconocidos se rechazan con código.
[ ] 4. Obra, persona y tajo se resuelven contra registro_obras / catálogo de personal / CATALOGO_TAJOS; la ambigüedad frena, no adivina.
[ ] 5. Todo rechazo tiene codigo + texto llano; nada se descarta en silencio; el except no tumba a los demás ficheros ni a la obra.
[ ] 6. Desconocido nunca se convierte en 0; fechas ilegibles y cantidades ambiguas se rechazan con su fila.
[ ] 7. Idempotencia por SHA256: aplicar dos veces da el mismo estado byte a byte; copia con otro nombre = copia_de.
[ ] 8. Traza <tipo>_aplicadas.jsonl aditiva y no bloqueante, con version, sha256 y nombre base; sin rutas absolutas ni datos personales; línea ilegible se avisa.
[ ] 9. Lector listar→analizar(sin escribir)→aplicar, llamado desde actualizar_obra.py y generar_todos.py; cerrar_obra se niega con pendientes.
[ ] 10. Pruebas unittest de la lista 3.9 (incluida publicación, jerarquía, no colateralidad y una mutación documentada); sin pytest ni dependencias.
[ ] 11. .gitignore: una línea por fichero de datos y recurso declarado, con comentario y prueba de que publica y de que lo no declarado no; el .bat intacto.
[ ] 12. Privacidad: campos clasificados; ids en vez de nombres; el auditor busca DNI/teléfono/correo antes de publicar; nada sensible en git.
[ ] 13. Funciona en tablet/móvil (viewport; sin cobertura si procede); el traslado del fichero al PC está escrito en su skill.
[ ] 14. Declarada en el centro de mando (no por heurística de nombre), con contadores por obra y 0 visible; línea en el informe de verificación.
[ ] 15. Mapa mental y skill actualizados en la misma sesión; Mungia, Gernika, Bolueta y las demás obras no se mueven (antes/después reportado).
4. Cumplimiento del principio §7c (de más a menos grave)
Criterio de gravedad: riesgo de pérdida o fuga de datos, y cuánto se aleja del modelo. Las filas 1-3 son incumplimientos claros; 4-9, parciales; el último bloque cumple.

Orden	Extremidad	Qué rompe	Regla §7c	Evidencia	Cert.
1	Tierras (E9)	Estado maestro en localStorage; sin id de obra; el «copia de seguridad» es un .json propio sin traza ni lector; hay un informe de cliente publicado	1, 3, 4	app_informe_tierras.html:2541-2546,2571; VARIOS/TIERRAS/PARTES DE TIERRA DE/SERRALTA BARKALDO/…html vs .gitignore:200	CONFIRMADO
2	Baterías (E10)	Estado en localStorage + circuito propio de sincronización entre equipos por OneDrive; sin id de obra ni de contrato	1, 2, 3, 4	app_informes.html:1168,1270,1397-1409	CONFIRMADO
3	CARDIVA (E12)	Circuito propio completo: skill, plantilla, JSON propio, fuente canónica fuera de git, sincronización multi-IA por PowerShell; la base solo ve mtime	1, 3, 4	generate-cardiva-report/SKILL.md, data-schema.md:8-24, mantenimientos_index.py:164-183	CONFIRMADO / canónica NO VERIFICABLE
4	Script de Codex update_sagarde_works.py (E18)	Segundo camino para «actualizar la obra»: escribe fichas (leer_hoja_marcada --escribir) sin las guardas de actualizar_obra.py (foto SHA de otras obras, informe, código 3), ignora los CONTROL HORARIO, y lanza generar_todos.py de todas las obras; sin SKILL.md; nadie lo referencia	2, 4	.agents/skills/update-sagarde-works/scripts/update_sagarde_works.py:239-266,338	CONFIRMADO
5	Postventa (E13, E14)	El Word es la base maestra; postventas_sync.py muta el Word fuera del circuito; el estado «vencido» sale de mtime con una excepción cableada; partes TYPO sin llamada real; sin id de obra del registro	1, 2, 3, 4	postventas_index.py:305; postventas_sync.py:245-270; generar_parte_incidencia.py	CONFIRMADO
6	Materiales (E4)	Cumple lo básico (fichero a mano en carpeta de obra) pero sin SHA, sin traza, sin id de tajo/portal y con la fuente fuera de git; ya hubo una obra entera caída por editar el XML	4 (copiar al generador)	CLAUDE.md:202-263; entregas_materiales.py:1-45	CONFIRMADO (xlsx NO VERIFICABLE)
7	personal_obra.py ingerir (E2)	CLI de ingesta aún vivo que el repaso del 25/10 daba por «retirado como camino»; llama a ingerir_lote sin sha256 ni fichero, así que no anota el SHA y el fichero reaparece como «listo» (la clave natural lo deja en «sin efecto»: consecuencia INFERIDA)	2, 4	personal_obra.py:1893,1915-1921; repaso …/2026-10-25-personal-en-obra-repaso-integracion.md §2	CONFIRMADO / efecto INFERIDO
8	BASE TRABAJADORES (E3)	Dos puertas de entrada (cualquier REVISIONES y la carpeta del motor/raíz) y una función de «exportar» que aplica datos como efecto lateral. La skill describe solo la primera	2	personal_integracion.py:195-201; .claude/skills/sagarde-personal/SKILL.md:118-121	CONFIRMADO
9	Tareas Excel + panel_server (E5) y cierre de expediente (E6)	Estado maestro en Excel no versionado / JSON editado por CLI sin fichero de aportación; único escritor desde el portal. Excepción reconocida en el repaso §4	1, 3	nota_pendiente.py:8-24; panel_server.py:18; cierre_expediente.py:1-8	CONFIRMADO
—	Buscador (E11)	No es aportación de datos de obra; consulta a un servicio externo. No se evalúa contra §7c, solo se señala que su «base» (libros, vectores, KV) es invisible al entorno	—	app_buscador_electrico.html:101	CONFIRMADO / servicio NO VERIFICABLE
✔	Generador de revisiones (E1); tablet de Personal (E2) salvo punto 7; ranking (E3) salvo punto 8	Cumplen: un fichero, a mano a REVISIONES, «actualiza la obra», SHA, vista previa, traza, publicación probada	—	§2.2	CONFIRMADO
✔	Informe ejecutivo, paneles, índice de mantenimientos (E7, E8, E15)	Solo leen y publican	—	§2.2	CONFIRMADO
5. Hallazgos colaterales verificados
5.1 Privacidad (el repo es público)
Personal. personal_estado.js y personal_catalogo.json publican, de 22 trabajadores, nombre, empresa, categoría y horas por día y obra. El esquema no lleva DNI, teléfono ni correo (CONFIRMADO: claves del catálogo id, nombre, categoria, empresa, activo, alta, fusionado_en). Es decisión documentada de Bixente (.gitignore:73-74). Aun así: nombre + empresa + horas diarias identificables, en una web pública, es dato personal laboral. No es una conclusión jurídica mía; es el punto que Bixente debería decidir con asesoría, no con un comentario de .gitignore.
Postventa. POST-VENTAS/_SISTEMA/_PREVIEWS_WORD/ versiona 92 vistas previas HTML de los Word de incidencias (git ls-files). En 69 hay 3.408 secuencias de 9 dígitos que empiezan por 6-9 (patrón de teléfono español), más 4 correos y 209 menciones de «cliente». Solo 44 llevan la etiqueta «teléfono/contacto» a ≤40 caracteres, así que el recuento sobreestima. INFERIDO, no he leído nombres ni números. Aun con margen de error, no hay decisión documentada de publicarlas, y .gitignore:8 (!*.html) las deja pasar.
Informe de cliente de Tierras publicado: VARIOS/TIERRAS/PARTES DE TIERRA DE/SERRALTA BARKALDO/TIERRA SERRALTA BARKALDO.html, contradiciendo .gitignore:193-201 («tierras de cliente… se queda fuera a propósito»; :200). CONFIRMADO.
Rutas absolutas D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE\… en las 31 líneas de revisiones_aplicadas.jsonl de las 6 obras. Fuga menor de estructura local y traza no portable. CONFIRMADO.
Buscador. El HTML expone la URL pública del Worker; la clave la teclea el usuario y se guarda en localStorage del navegador (app_buscador_electrico.html:120,283). Si el Worker limita intentos: NO VERIFICABLE (no versionado).
5.2 Desfases del mapa y de CLAUDE.md
Afirmación	Realidad	Evidencia
Mapa :159: «CATALOGO_TAJOS.json no está en git… no hay git checkout que lo restaure»	Está versionado desde 78c0b3a (15/10/2026). Sigue ignorado por .gitignore:2 (git check-ignore --no-index lo confirma): rastreado por accidente, no por regla. Si cambia de ruta o se recrea, vuelve a quedar fuera sin avisar	git ls-files, git log --follow
CLAUDE.md §4: «un tipo de fichero nuevo exige tocar .gitignore y el .bat a la vez»	Solo .gitignore. El .bat hace git add -A y fuerza únicamente el PDF ejecutivo	Actualizar_Sagarde.bat:100,103
CLAUDE.md §3 (:64-65): «Mungia 79.8, Gernika 76.3, Bolueta 41.7, Obispo Orueta 80.0» como cifras de control	El mapa vivo da hoy Mungia 90.3, Gernika 94.1, Bolueta 76.7 (SAGARDE_MAPA_MENTAL_ENTORNO.md:35-42) y Orueta está cerrada (13/08/2026). Quien use esas cifras como referencia daría por «movidas» obras que no se han movido, o al revés	mapa :35-42; CLAUDE.md:64-65
Mapa :125: «siete accesos de aplicaciones»	APLICACIONES/index.html dice 6 (3 de obras abiertas + 3 herramientas)	APLICACIONES/index.html
sagarde_portal.py:1437: «se excluyen… utilidades de otras áreas (tierras, condensadores, manuales)»	Tierras y Baterías sí salen en Aplicaciones (EXCLUIR_AREAS solo excluye MANTENIMIENTOS, POST-VENTAS, OLD)	sagarde_portal.py:1435-1438; APLICACIONES/index.html
Mapa :365: «cuatro BAT»	Versionados: 2 (Actualizar_Sagarde.bat, Abrir_Panel_Local.bat). Actualizar_Obras.bat, Actualizar_Postventas.bat, Servidor_Local.bat: NO VERIFICABLE	git ls-files
Repaso 25/10: Ingerir_Personal.bat e iniciar-obra «se retiran»	Ninguno aparece en git ni en el código (grep). El CLI ingerir sí sigue (§4 fila 7). Ingerir_Personal.bat en disco: NO VERIFICABLE	grep
5.3 Otros fallos de la familia «declarado que el motor ignora»
Descubrimiento de apps por nombre (sagarde_portal.py:28,1450): sin aviso si una app nueva no encaja (§3.13).
Gorliz: registrada, con panel y prioridades, sin ficha_obra.json ni revisión (registro_obras.py:49-60); su recuento no avisa de que es 0.
shas_recibidos descarta líneas ilegibles de la traza sin aviso (personal_obra.py:1160-1164).
Dos esquemas de traza distintos (§3.6) y CARDIVA sin version (§3.2).
Postventa: el estado «reciente/vencido» deriva del mtime y el propio código reconoce que cerrar incidencias lo falsea, con una excepción cableada (postventas_index.py:300-305).
5.4 Descartado (y por qué)
«Personal tiene carpeta propia PERSONAL EN OBRA/»: descartado; la decisión D1 se anuló y no existe en git.
«El generador de revisiones guarda datos maestros en localStorage»: descartado; solo borrador y «recientes» (generador_revisiones.html:1666-1671,1807).
«personal_sagarde.html tiene almacenamiento propio»: descartado; solo un borrador de la lista de cambios (:1980-2006, con su comentario).
«Rutas absolutas en el código»: descartado salvo sembrar_ficha_obra.py:28 (script histórico no runtime) y las trazas de §5.1.
«Ingerir_Personal.bat sigue en disco»: no afirmo ni niego (no versionado).
«El Buscador filtra la clave de NVIDIA al repo»: descartado en lo visible; el cliente no contiene clave, solo la URL pública del Worker.
«Teléfonos de clientes publicados»: degradado a INFERIDO (§5.1).
6. Plan para conectar las islas
Esfuerzo: S ≤ 1 sesión, M = 2-4, L > 4 (estimación mía, sin medir). Todas las acciones requieren la aprobación de Bixente y siguen el flujo de CLAUDE.md §5 (especificación → plan → pruebas primero). Nada de esto se ejecuta hoy.

Paso	Isla / pieza	Cómo enchufarla	Esfuerzo	Riesgo	¿Enchufar?
0	Privacidad previa (decisión, no código)	Decidir si seguir publicando nombres de personal; dejar de versionar _PREVIEWS_WORD/ y el informe de cliente de Tierras; quitar rutas absolutas de las trazas. Cada cambio mueve lo publicado: pedir confirmación. Antes de cualquier enchufe nuevo	S	Alto si se ignora; bajo al hacerlo	Sí, primero
1	Caminos paralelos (.agents/…update_sagarde_works.py, personal_obra.py ingerir, puerta BASE en exportar)	Retirar o reducir a vista previa; que todo pase por actualizar_obra.py. ingerir o se borra o pasa sha256 y fichero. La puerta BASE se queda solo en REVISIONES y se aplica desde el mismo camino que los controles	S	Bajo, con pruebas ya existentes (test_controles_horarios_08b.py)	Sí
2	Materiales (E4)	Mantener el Excel como fuente (CLAUDE.md §7b), pero añadir al lector materiales_aplicadas.jsonl (SHA256 del .xlsx, filas válidas/rechazadas, avisos) y contadores en panel y verificación. Opcional, solo si Bixente lo pide: id de tajo/portal por línea. Mungia y Bolueta se quedan como están	S–M	Medio: el .xlsx no está en git y un cambio del formato rompió una obra	Sí
3	Tierras (E9)	La app exporta MEDICION TIERRAS <OBRA> <DDMMAAAA>.json (id de obra, punto de medida, valor, instrumento, fecha) a REVISIONES; lector_tierras.py → tierras_obra.json + tierras_aplicadas.jsonl; sección en panel e informe. Informes de clientes ajenos al registro no se enchufan: quedan fuera del repo. No inventar umbrales: criterio REBT/ITC solo como regla declarada y citada	M	Medio: define esquema de mediciones; mezclar obras ajenas	Sí, solo mediciones de obras del registro
4	Unidad «contrato de mantenimiento» (prerrequisito de 5 y 6)	registro_contratos.py análogo a registro_obras.py (id, alias, carpeta). Hoy mantenimientos_index.py solo escanea carpetas	M	Medio: crea registro nuevo; hay que decidir si OBRAMAT (rescindido) entra	Sí
5	CARDIVA (E12)	Versionar la fuente canónica (hoy solo la copia .claude/skills/… está en git, APP_CARDIVA/ no): decidir cuál manda. Emitir PARTE CARDIVA <AAAAMMDD>.json (el data-schema.md es ya un contrato casi listo: añadir version, id de contrato). Lector → mantenimiento_<contrato>.json: deficiencias abiertas/resueltas, materiales. La regla de la skill (duda de lectura ⇒ parar y preguntar) pasa a «a revisar». Los manuscritos y fotos se quedan en OneDrive	L	Alto: ambigüedad de lectura, datos de cliente, fuente canónica fuera de git	Sí, solo el resumen estructurado
6	Baterías (E10)	Mismo patrón que 5, contra el contrato (una batería = equipo de un contrato). Reutiliza el contrato de enchufe; sustituir el archivo OneDrive de sincronización por el fichero de aportación	M	Medio	Sí, tras 4
7	Postventa (E13, E14)	Lector de incidencias con el código Sagarde (CODE_RE) como id; estado explícito (abierta/resuelta + fecha), no por mtime. Solo guardar código, obra, portal/mano, naturaleza, fechas y estado: sin nombre ni teléfono. Dejar de publicar previews. Integrar o retirar postventas_sync.py (muta Word)	L	Alto: Word como maestro, datos de clientes, obras cerradas fuera del registro	Sí, al final, solo agregados
8	Tareas Excel y cierre de expediente (E5, E6)	Opcional: fichero TAREAS … / CIERRE … de aportación con traza. El valor es bajo y el servidor local ya está acotado	M	Bajo	Opcional / aplazar
9	Skills y agentes	Una sola ruta de actualización («actualiza la obra» → actualizar_obra.py); el script de Codex se unifica o se retira (paso 1). Versionar .claude/agents si Bixente quiere que sean parte del entorno	S	Bajo	Sí, junto al paso 1
6.1 Qué NO conviene enchufar
Buscador Eléctrico: su dato (libros con derechos de autor, vectores, índice en KV) no es de obra, vive en servicio externo y la clave no debe tocar el repo (spec 14/09, §B). Solo una tarjeta en el centro de mando. Registrar consultas en el cuerpo añadiría coste y privacidad sin beneficio.
VARIOS/PLANILLA y VARIOS/APPS SAGARDE (nómina, vida laboral, convenio): sensibles y fuera de git a propósito (.gitignore:11; sagarde_portal.py:70-72). Enchufarlos exigiría o publicarlos o crear un cuerpo privado; ninguno de los dos está pedido.
Datos personales de Personal más allá de lo actual: no ampliar el catálogo (DNI, teléfono, firma). Antes, paso 0.
Partes manuscritos, fotos y Word completos (CARDIVA, postventa): al cuerpo solo el resumen estructurado; el original queda en OneDrive (CLAUDE.md §7: conservar el original).
Informes de tierras de clientes ajenos al registro de obras.
VARIOS/* documental (pegatinas, catálogos, normativa): no tiene datos que beber ni aportar.
6.2 Orden recomendado y por qué
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7, con 8-9 sueltos. La privacidad primero porque cada fichero nuevo publicado agrava un problema que hoy ya existe y es lo único irreversible (lo publicado puede quedar en cachés e historial). Los caminos paralelos después, porque es lo más barato y reduce el riesgo de que dos IAs apliquen la misma revisión por vías distintas. Materiales antes que Tierras porque ya tiene dato real y un incidente documentado. CARDIVA y postventa al final: son las más caras y las que más dependen de una decisión previa (qué es un «contrato» y quién manda sobre el Word).

7. Decisiones que necesito de Bixente
Datos de personal en el repo público: ¿se mantiene la decisión de publicar nombre + empresa + horas, o se pasan a ids en el repo y nombres solo en la tablet/PC?
Vistas previas de postventa y el informe de cliente de Tierras: ¿se retiran del repo? (Mi inferencia sobre teléfonos no está leída nominalmente; conviene que la confirme él con una apertura rápida.)
Traslado tablet→PC: ¿cómo lo hace hoy? (OneDrive, USB, correo.) Hay que escribirlo en la skill.
Unidad «contrato de mantenimiento»: ¿se crea registro propio?
.agents/skills/update-sagarde-works y personal_obra.py ingerir: ¿se retiran?
8. No verificable (lista)
FICHA DE OBRA.xlsx y hoja de entrega de materiales *.xlsx (contenido); Actualizar_Obras.bat, Actualizar_Postventas.bat, Servidor_Local.bat, Ingerir_Personal.bat; .claude/agents/, .gemini/, GEMINI.md, .superpowers/; MANTENIMIENTOS/MANTENIMIENTO CARDIVA/APP_CARDIVA/ (fuente canónica); Worker de Cloudflare, Workers KV y límites de intentos del Buscador; VARIOS/PLANILLA y VARIOS/APPS SAGARDE; los DOCX/PDF de postventa y mantenimiento; cómo se traslada hoy el fichero desde la tablet; si el portal móvil (_SISTEMA/PORTAL SAGARDE.html) sigue estancado (el mapa lo dice, no lo he reproducido).
