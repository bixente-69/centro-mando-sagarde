# Proyecto Sagarde — instrucciones de trabajo

Sistema de control de obras eléctricas y de telecomunicaciones de Montajes
Eléctricos Sagarde. Usuario único: Bixente.

## 1. Para qué sirve el proyecto

- Controlar obras por obra, portal, planta, vivienda y tajo.
- Planificar trabajos y detectar bloqueos.
- Controlar materiales entregados, instalados, pendientes y necesarios.
- Estimar consumos y anticipar pedidos.
- Generar informes verificables y analizar históricos de revisiones.
- Gestionar incidencias y postventa.
- Mantener trazabilidad de datos y decisiones.
- Aplicar REBT, ICT y criterios de distribuidora cuando corresponda.

**No se inventan datos, estados, cantidades, avances, fechas ni requisitos.**
Cuando falte información imprescindible, decirlo.

---

## 2. La regla que gobierna este proyecto

Todos los fallos graves encontrados aquí pertenecen a **una sola familia**:

> **Algo declarado que el motor ignora en silencio.**

Casos reales, todos del 27/07/2026:

| Qué se ignoraba | Coste medido |
|---|---|
| Etiquetas de tajo desincronizadas | 244 celdas y 41 correcciones por revisión |
| Correcciones manuales con clave que no casa | 6 marcas escritas a boli |
| Excepciones del catálogo tras una guarda obsoleta | 4 tajos inexistentes durante meses |
| Estructura deducida de celdas rellenas | una vivienda entera invisible |
| Corrección X→M revertida por el motor | 22 celdas por revisión |

**Por eso:** un JSON de configuración que nadie lee no da error. Un recuento de
0 es señal de alarma, no de "no aplica". Verificar siempre que lo declarado
produce efecto observable.

---

## 3. Cómo verificar en este proyecto

**El porcentaje redondeado es un criterio ciego.** En Mungia, 3 celdas sobre
2309 no mueven el `pct_ponderado`. Comparar siempre el desglose:

```
x = terminadas   m = más del 50%   slash = iniciadas   vacio = pendientes
```

**Los KPI salen del historial validado por la ficha cuando existe.** El flujo
vigente es adaptador → historial crudo → ficha/correcciones → historial
validado. Memoria, prioridades, KPI, panel e informe ejecutivo leen ese mismo
historial. En obras sin `ficha_obra.json`, se usa la última hoja del adaptador.
Comprobar siempre que todos los consumidores muestran el mismo desglose.

**Probar por mutación.** Romper el código a propósito y comprobar que la
prueba se entera. Hoy eso destapó 3 pruebas que parecían verificar algo y no
verificaban nada.

**Antes de dar nada por bueno:**
- Que las obras no implicadas no se mueven (Mungia 79.8, Gernika 76.3,
  Bolueta 41.7, Obispo Orueta 80.0). Si se mueven, hay efecto colateral.
- Reportar el antes/después a Bixente. Aplicar en silencio una corrección que
  mueve cifras es repetir el problema desde el otro lado.

---

## 4. Peligros operativos concretos

**`Actualizar_Sagarde.bat` hace `git add -A` y publica en main.** Desde que el
código Python está versionado, cualquier trabajo a medias que haya en disco
acaba publicado. Ha ocurrido dos veces en un día con mutaciones de prueba
abandonadas. No lanzarlo mientras haya trabajo en vuelo, y restaurar siempre
cualquier fichero mutado para una verificación.

**`regenerar_obra.py <obra>` no ejercita todo el flujo:** sustituye
`publicar_registro_revisiones` por una función vacía. Para el camino de
publicación, usar `--finalizar` o `--solo-revisiones`.

**El `.gitignore` es lista blanca** (`*` ignora todo, luego se permite). Un
tipo de fichero nuevo exige tocar `.gitignore` y el `.bat` a la vez, o se
genera pero nunca se publica.

---

## 5. Elegir skill según la tarea

La skill debe responder a la necesidad concreta. Evitar tanto no usar las
herramientas como usarlas de forma desproporcionada.

**Al empezar sesión:** `superpowers:using-superpowers`. Consultar la memoria
del proyecto antes de asumir que algo es nuevo.

**Tarea trivial** (un texto, una etiqueta, un campo): hacerla directamente.
No montar estructura de planificación para un cambio de una línea.

**Tarea compleja o con fases** (funcionalidad nueva, cambio de estructura de
datos, módulo completo):

1. `superpowers:brainstorming` — intención, requisitos, riesgos, alternativas
2. Escribir la especificación y que Bixente la apruebe
3. `superpowers:writing-plans` — convertirla en tareas ejecutables
4. `superpowers:subagent-driven-development` — ejecutarlas con revisión entre
   cada una

**No empezar a programar con ambigüedades relevantes sin resolver.**

**Ante un fallo:** `superpowers:systematic-debugging`. No proponer la primera
solución intuitiva: reproducir, aislar la causa raíz, distinguir síntoma de
causa, escribir la prueba que lo demuestra, corregir, verificar que no hay
regresión.

**Antes de dar por terminado:** `superpowers:verification-before-completion`.

**Para revisar código:** `superpowers:requesting-code-review`, y aplicar
especialmente el enfoque de *silent-failure-hunter* — es la familia de fallos
de este proyecto. Las observaciones de una revisión no se aplican ciegamente:
comprobar cada una y rechazar razonadamente las incorrectas.

**Para tareas independientes:** `superpowers:dispatching-parallel-agents`.
**No paralelizar tareas que compartan ficheros o estado.** Hoy cinco procesos
escribiendo en el mismo repo causaron trabajo duplicado y una mutación
publicada.

---

## 6. Desarrollo

- Pruebas primero. Después el código mínimo. Después ejecutarlas.
- No modificar partes no relacionadas con la petición.
- Commits pequeños y comprensibles, que expliquen **por qué**, no solo qué.
- Si tocas algo compartido, busca con `grep -n` **todos** sus usos antes de
  darlo por bueno. Dos veces en un día se arregló un camino y se dejó roto su
  hermano, perdiendo datos en silencio.
- Un `except` demasiado estrecho convierte un aviso en una caída. Un `except`
  demasiado amplio se traga el error. Ninguno de los dos debe tumbar la
  generación del panel de una obra.
- Pruebas con `unittest` de la biblioteca estándar. **No introducir pytest ni
  dependencias nuevas**: Bixente ejecuta todo con ficheros `.bat`.

Ejecutar la suite:

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

---

## 7. Datos de obra

- Conservar siempre el archivo original. Registrar nombre y fecha de revisión.
- Identificar obra, portal, planta, vivienda y tajo. No mezclar obras.
- No reinterpretar símbolos ni estados sin una regla definida.
- **No sustituir valores desconocidos por cero.**
- Distinguir dato real, estimación, inferencia y predicción. Mostrar las
  hipótesis de los cálculos.
- Avisar cuando la calidad del dato no permita una conclusión fiable.

**Alfabeto de estados guardados en la ficha:**

| | Significa |
|---|---|
| `X` | terminado |
| `M` | más del 50% |
| `/` | iniciado |
| `P` | **pendiente confirmado**: se comprobó en campo y no está hecho, o la hoja se revisó y esa casilla salió en blanco. Pesa 0 y **cuenta** en el porcentaje |
| `?` | **desconocido**: nadie lo ha mirado nunca |
| `N` | no aplica a esa ubicación |

`P` y `?` son distintos a propósito. Confundirlos es la causa de casi todo lo
que ha fallado aquí.

**No se persisten** `BLOQUEADO`, `DUDAS`, `VIABLE` ni `OTROS_GREMIOS`: son
categorías que calcula el priorizador desde las dependencias. **Se guarda lo
medido, se recalcula lo derivado.**

**Norma de obra de Bixente, textual:** *"lo que se apunta en la última
revisión es lo que vale"*. Una marca explícita que baja de `X` se acepta a la
primera: ha ido y ha visto que faltaba algo. Solo la **ausencia** de marca
(`?`, el lector no supo leer) no puede bajar una `X`.

---

## 8. Memoria

**Memoria funcional y técnica vigente (28/07/2026):**
`docs/2026-07-28-memoria-diccionario-tajos-alertas-informes.md`.
Contiene el diccionario confirmado, las traducciones históricas, la
especialización de tajos, la corrección de falsas alertas y el contrato del
informe ejecutivo. Leerla antes de volver a preguntar por esos asuntos.

**Revisiones de campo a la base (paso 4 del ciclo, implementado el
05/08/2026).** Cuando Bixente entregue una hoja marcada a boli:

```bash
python leer_hoja_marcada.py "<hoja.pdf>" <id_obra> --preparar
# la IA mira los recortes de <hoja>.recortes/ y escribe <hoja>.clasificacion.json
python leer_hoja_marcada.py "<hoja.pdf>" <id_obra> --aplicar <clasificacion> --fecha DD/MM/AAAA --escribir
```

Son **dos fases a propósito**: el código pone la clave de cada celda por
geometría y la vista pone la letra. El error caro no es confundir `X` con `M`,
es poner la marca en la fila equivocada.

- **Sin tinta no hay cambio.** Clasificar una celda sin tinta aborta.
- **Nada se descarta solo:** una celda con poca tinta sale como DUDOSA y hay
  que resolverla a mano, aunque sea marcándola `descartada`.
- **La fecha no se deduce de la hoja**: la de la cabecera es la de generación.
- **Las casillas en blanco de una hoja usada pasan a `P`**, no se quedan en
  `?`. Norma de Bixente, textual: *"el no tener ninguna marca no significa que
  no se haya revisado, es que ni siquiera existe [ese tajo todavía]"*. Una
  obra dura meses y muchos tajos son casi del final. Solo asciende `?`→`P`:
  un blanco **nunca** baja una `X`, `M` o `/`. Con `--sin-marca desconocido`
  se desactiva, para una hoja que no cubra la obra entera.
- Para dar de alta una obra nueva desde su hoja **en blanco**:
  `alta_obra_desde_hoja.py`. La distribución la manda la hoja: si trae 15
  bloques, se registran 15.
- La lectura de rejilla es común: `rejilla_hoja.py`. **No reescribirla.**

No cerrar con fechas o recuentos discordantes, y reportar siempre el
antes/después.

Guardar en memoria: reglas de interpretación de hojas, estructura de cada
obra, nombres de tajos, criterios de cálculo, dependencias entre gremios,
normas internas confirmadas, errores ya resueltos, decisiones de arquitectura.

**No guardar como regla permanente una deducción provisional.** Y al recordar
algo, verificar que sigue siendo cierto antes de actuar: la memoria refleja lo
que era verdad cuando se escribió.

### Entorno IA compartido y CARDIVA

El registro central de contexto, memoria y skills compartidas por Codex,
Claude y Gemini es `docs/SAGARDE_ENTORNO_IA_Y_SKILLS.md`.

Para informes preventivos CARDIVA:

- usar la skill de proyecto
  `.claude/skills/generate-cardiva-report/SKILL.md`;
- invocarla como `/generate-cardiva-report`;
- considerar fuente canónica únicamente
  `MANTENIMIENTOS/MANTENIMIENTO CARDIVA/APP_CARDIVA/skills/generate-cardiva-report`;
- trabajar solo con los documentos que el usuario declare autorizados;
- mantener resultados y estados sin código de colores;
- sincronizar las copias multi-IA mediante
  `MANTENIMIENTOS/MANTENIMIENTO CARDIVA/APP_CARDIVA/tools/sync_cardiva_skill_agents.ps1`.

---

## 9. Reglas que no se saltan

- No inventar datos ni rellenar huecos sin autorización.
- No declarar terminada una tarea sin pruebas.
- No modificar archivos no relacionados.
- No eliminar información histórica sin copia ni trazabilidad.
- No mezclar datos reales con estimaciones sin diferenciarlos.
- No aplicar sugerencias de revisión sin comprobarlas.
- No usar subagentes para tareas pequeñas.
- **No ocultar errores, advertencias ni limitaciones.**

Prioridad: exactitud, trazabilidad y utilidad real para gestionar las obras.
