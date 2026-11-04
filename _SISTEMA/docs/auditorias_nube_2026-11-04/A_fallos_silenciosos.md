# Auditoría A — «Algo declarado que el motor ignora en silencio»

Fecha: 04/11/2026 · Rama `nube/auditoria-fallos-silenciosos` · Solo lectura (ningún `.py` ni dato modificado).
Ámbito: los `.py` de `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/` y de `_SISTEMA/MOTOR/`.

Abreviatura de rutas: **`M/`** = `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/`.

## Cómo se hizo y qué límites tiene

- Escaneo AST de los 128 `except` del ámbito (fuera de `tests/`) → se leyó el código real de cada candidato.
- Cruce de las claves de `reglas/CATALOGO_TAJOS.json` y de las 6 `ficha_obra.json` con `grep` de todos los usos.
- Cotejo de los datos reales versionados (fichas, sidecars `.correcciones.json`, revisiones HTML) contra la lógica que los lee.
- Dos comprobaciones ejecutadas **en memoria** (hallazgos 4 y 8), sin escribir nada. Comprobado después: `git status` limpio y ningún `__pycache__` nuevo.
- **No se ejecutó** la suite, `regenerar_obra.py` ni el `.bat`. **No se aplicó prueba por mutación** (exige modificar código). Los esquemas de prueba de abajo son propuestas sin ejecutar.
- Distinción de certeza: *medido* = comprobado con datos reales; *demostrado en memoria* = mecanismo ejecutado con datos sintéticos; *latente* = el mecanismo existe pero los datos actuales no lo disparan.
- No hay nombres de trabajadores ni datos personales en este informe.

## Resumen

| # | Gravedad | Hallazgo | Certeza |
|---|---|---|---|
| 1 | Alta | Dos revisiones HTML con la misma fecha: gana una en silencio; HTML sin fecha en el nombre se ignora; el auditor no mira `.html` | **Medido** (Bolueta: 156 celdas difieren) |
| 2 | Alta | Correcciones manuales cuya clave no casa se descartan sin contar | **Medido** (3 claves reales, efecto numérico hoy 0) |
| 3 | Media-alta | Si el informe ejecutivo falla, la obra no se marca fallida y se sigue enlazando el PDF viejo | Leído en código |
| 4 | Media | Una letra fuera del alfabeto de estados da dos desgloses distintos según el consumidor | **Demostrado en memoria** (latente: 0 casos reales) |
| 5 | Media | `verificar_rejilla` da alarma permanente en 3 de 6 obras (falsa) → una pérdida real de celdas no se distinguiría | **Medido** |
| 6 | Media | Clave del catálogo `forzar_historial_terminado_hasta` sin lector; código que la citaba ya no existe | Medido (grep) |
| 7 | Media-baja | Ficha ilegible → se degrada a «estructura deducida de celdas» sin marcar la obra fallida | Leído en código |
| 8 | Baja | Guarda de «edad de la revisión» inalcanzable; sin fecha sale «None (739923 días)» | **Demostrado en memoria** |
| 9 | Baja | Claves del catálogo que ningún código lee (`estado_m`, `estado_x`, `orden_inventario`, `estados`, `descripcion`) | Medido (grep) |
| 10 | Baja | `except … pass/continue` en portal y en la guarda de fusión de personal | Leído en código |
| 11 | Baja | Los números de referencia de `CLAUDE.md` §3 están obsoletos y no existe línea base automática | Medido |
| 12 | Baja | Parser HTML: estados fuera de `X/M//` pasan a pendiente (incluye `?` y `P`); claves mal formadas se saltan | Leído en código (latente) |

---

## 1. [Alta] Revisiones HTML con igual fecha: gana una sin aviso; HTML sin fecha se ignora

**Dónde**
- `M/adaptar_revision_html.py:719-723` — `except ValueError: continue` **sin mensaje** si el nombre no trae `DDMMAAAA` válido. Igual en `M/lector_hoja_tajos_html.py:292` (`if clave:`).
- `M/adaptar_revision_html.py:725` — `candidatos.sort(key=fecha)` es estable: el orden entre ficheros de la misma fecha es el de `os.listdir`, que no está garantizado.
- Fusión «último gana» por clave de fecha, sin comparar ni avisar: `M/adaptadores/adaptador_bolueta.py:471-479`, `adaptador_mungia.py:375-381`, `adaptador_olabeaga.py:~405-411`, `adaptador_barakaldo.py:~405`.
- Contraste: la rama JSON del mismo adaptador **sí** lanza error si hay dos con la misma fecha (`adaptador_olabeaga.py:372-376`, `adaptador_barakaldo.py:~370`: «deje una sola por día»). La rama HTML, que es la vía digital preferente, no.
- `_SISTEMA/MOTOR/scripts/auditor_sagarde.py:54` — `DATA_EXTS` no incluye `.html`: el auditor no ve revisiones HTML (ni sin fecha ni duplicadas). Y su mensaje de duplicadas (`:149`) afirma «El motor seleccionará automáticamente el archivo con modificación más reciente», que no es lo que hace este camino (no hay lógica de `mtime`).

**Declarado vs ignorado**: el auditor y la documentación prometen que las duplicadas se resuelven por modificación más reciente y que las revisiones sin fecha se detectan; para HTML ninguna de las dos cosas ocurre.

**Medido** (revisiones HTML versionadas, sin los `_garaje`):

| Obra | Fecha | Ficheros | Celdas que difieren |
|---|---|---|---|
| Olabeaga | 05/10/2026 | `…05102026.html` y `… (1).html` | 0 |
| Mungia | 04/09/2026 | `… (3).html` y `… 3.html` | 0 |
| **Bolueta** | **28/09/2026** | `… (1).html` y `….html` | **156** |

En Bolueta el `(1)` trae 3825 celdas (X 2271 · M 120 · / 56 · N 179 · vacío 1199) y el otro 3772 (X 2271 · M 121 · / 62 · N 90 · vacío 1228). Con el orden de `os.listdir` de este clon Linux, en Bolueta gana el fichero sin sufijo y en Olabeaga gana el `(1)`: **el ganador cambia de una obra a otra y de un sistema de ficheros a otro**.

**Impacto probable**: el snapshot de esa fecha del historial (serie `historico_pct`, última fecha si fuera la última) sale de un solo fichero elegido al azar. No se ha cuantificado el efecto en `pct_ponderado` (exige ejecutar el adaptador); con 156 celdas y diferencias en `M` y `/`, el redondeado puede no moverse — criterio ciego, comparar desglose.

**Prueba (`unittest`)**
1. Parchear `_cargar_historial_html` del adaptador para devolver `[(f, reg1), (f, reg2)]` con la misma fecha y registros distintos; exigir que `cargar_historial()` lance error o emita aviso. Hoy devuelve una sola entrada sin ruido.
2. Directorio temporal con un `.html` cuyo nombre no lleva fecha; exigir un aviso de «ignorado». Hoy no hay salida.
3. Auditor: `audit_obras_abiertas` sobre un directorio con dos `.html` de la misma fecha debe emitir `REVISIONES_DUPLICADAS`. Hoy no.

---

## 2. [Alta] Correcciones manuales que no casan: descartadas sin contador

**Dónde**: `M/ficha_obra.py:1078-1086` (`_reclamar_correcciones`):
```
if partes is None: continue        # clave con != 4 tramos
...
if destino is None: continue       # no casa ni con alias
```
`cambios` solo tiene `correcciones_reclamadas` (las que sí se aplican) y `estados_no_reconocidos` (letras raras). **No existe contador de claves sin casar**, así que no se imprime nada (el resumen de `:1153-1158` no puede hablar de lo que nunca se cuenta). El aviso equivalente de `lector_hoja_tajos_pdf.py:273-281` solo cubre el camino PDF, no el de sidecars HTML ni el de la ficha.

Es exactamente la clase de `CLAUDE.md` §2 («Correcciones manuales con clave que no casa — 6 marcas escritas a boli»).

**Medido**: se reprodujo la lógica (`partir_clave` + `_mapa_tajos_cortos` + `_con_alias`) con el sidecar más reciente de cada obra contra su ficha. Cinco obras: 0 claves sin casar. **Olabeaga, sidecar del 02/11/2026: 3 de 82 sin casar** — `p2__pb__montante_teleco__TRAST 1/2/3`.

Causa: `partir_clave` quita los espacios de la unidad (`TRAST 1` → `TRAST1`), pero la ficha guarda el id **con espacio** (`'TRAST 1'`, sembrado en `alta_obra_desde_hoja.py:246-248`) y no hay alias. `_reclamar_correcciones` compara texto exacto; la norma que ya existe en el mismo fichero (`_fold_unidad`, `:359`) se aplica en `_localizar`, no aquí. El comentario de `:359-369` documenta el mismo fallo para `Local 1` de Bolueta.

**Impacto**: hoy **0 celdas** — la revisión principal (camino `html_digital`) ya dejó esas 3 celdas en `/`, igual que la corrección. Es **latente**: la primera corrección *distinta* que se escriba sobre un trastero se perderá sin rastro. Cualquier unidad con espacio en el id está expuesta.

**Prueba**: ficha mínima con ubicación `'TRAST 1'`; `correcciones={'p1__pb__t__TRAST 1': 'X'}`; llamar a `_reclamar_correcciones` y exigir (a) que la celda pase a `X`, o (b) que `cambios` registre la clave como no casada. Hoy ocurre ninguna. Mutación: quitar el `continue` del `destino is None` por un `cambios[...]+=` y comprobar que la prueba (b) lo detecta.

---

## 3. [Media-alta] Informe ejecutivo que falla: ni obra fallida ni PDF viejo retirado

**Dónde**: `M/generar_todos.py:2124-2143`:
```
except Exception as e_exec:
    print(f"  [AVISO INFORME EJECUTIVO] {e_exec}")
```
`fallidas.append` solo aparece en `:1817` y `:2112` (lectura de la obra y panel). Tras el aviso el flujo sigue: `pdf_ejecutivo_rel` se calcula con `os.path.isfile` (`:2176-2178`), así que se enlaza el PDF **anterior** como si fuera el vigente, y el código de salida es 0 (`:2217` solo devuelve 1 si hay `fallidas`) → el `.bat` publica.

Además `generar_informe_ejecutivo.generar_para_obra` devuelve `None` (con un `print [ERROR]`) en vez de lanzar si la obra no se resuelve (`_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py:3030-3032`) o no hay historial (`:3066-3068`): ese camino ni siquiera entra en el `except`.

Lo que sí hay: `_SISTEMA/MOTOR/scripts/actualizar_obra.py:796` (`verificar_pdf`, llamada en `:1498`) comprueba que el `Datos:` de cada página coincida con la fecha de la ficha. Pero **solo en el camino «actualiza la obra X»**, no en `generar_todos`/`Actualizar_Sagarde.bat`.

**Impacto**: informe ejecutivo con cifras de una pasada anterior publicado junto a un panel nuevo, sin ninguna señal visible. No verificado: si `doc.build` escribe directo a la ruta final (`generar_informe_ejecutivo.py:2939`), un fallo a medias podría dejar un PDF truncado; habría que ejecutarlo para confirmarlo.

**Prueba**: sobre una obra fixture (`tests/ayudante_generar.py`), parchear `generar_informe_ejecutivo.generar_para_obra` para que lance; exigir que la obra figure en el retorno de `main` (o que el PDF previo se marque/retire). Y otra con retorno `None`.

---

## 4. [Media] Letra fuera del alfabeto: KPI y priorizador cuentan distinto

**Dónde**
- `M/ficha_obra.py:339-341`: `ESTADO_A_SNAPSHOT.get(dato.get('v'))` → cualquier valor que no sea `X/M//P` (incluye `x` minúscula, `v` ausente, `Z`) hace `continue  # '?' o 'N': fuera del cálculo` — **excluido** de los KPI.
- `M/priorizador_trabajos.py:265` y `:310`: `ESTADO_BASE_A_MOTOR.get(valor, "")` → el mismo valor pasa a `""` = **pendiente** (cuenta, pesa 0).

El comentario del código (`'?' o 'N'`) da por hecho que solo llegan esas dos letras; nada valida el alfabeto al **cargar la ficha**. (Al ingerir una revisión sí hay validación: `validar_revision.py:27-35, 371-373` y `adaptar_revision_html.py:578`; el hueco está entre la ficha guardada y sus consumidores.)

**Demostrado en memoria** (ficha sintética, una ubicación, 4 tajos con valores `'x'`, `'X'`, sin `v`, `'Z'`): `snapshot_desde_ficha` devuelve **1 celda** (la `X`); `priorizar_ficha` devuelve **4**: la `X` terminada y las otras 3 como «Pendiente». Es el «mismo desglose en todos los consumidores» que `CLAUDE.md` §3 exige comprobar.

**Medido**: las 6 `ficha_obra.json` solo contienen `X, M, /, P, N` → **latente**, 0 casos hoy. Se activaría con una edición manual de la ficha o una letra nueva en un adaptador.

**Prueba**: ficha con los valores anteriores; exigir que `snapshot_desde_ficha` y `estado_desde_ficha` produzcan el mismo conjunto de celdas, o que una validación previa rechace/avise el valor. Hoy discrepan.

---

## 5. [Media] `verificar_rejilla`: alarma permanente en 3 obras (falsa) → alarma sin valor

**Dónde**: `M/priorizador_trabajos.py:451-457`: avisa si `celdas != ubicaciones × tajos` («La base no es una rejilla completa… Los tajos que falten no se pueden priorizar»).

**Medido** (están en `prioridades_trabajos.json` publicados):

| Obra | Celdas | «Esperadas» | Relación |
|---|---|---|---|
| Barakaldo | 4140 | 8160 (120 × 68) | 51 % |
| Bolueta | 3837 | 7738 (106 × 73) | 50 % |
| Olabeaga | 1519 | 3528 (49 × 72) | 43 % |

En esas obras cada tajo tiene entre 1–2 celdas (tajos de edificio) y ~100 (tajos de vivienda): la base **no es una rejilla densa por diseño** (tajos por ámbito, zonas especiales). La premisa «rejilla densa ubicaciones × tajos» (`CLAUDE.md`, mapa mental §2) quedó obsoleta, pero la guarda sigue vigente.

**Impacto**: Mungia, Gernika y Obra Prueba no avisan; las tres obras nuevas avisan siempre. Un aviso que está encendido siempre se aprende a ignorar: una pérdida *real* de celdas (la clase «una vivienda entera invisible») ya no se distinguiría. Interpretación: no he podido demostrar que *ninguna* de las celdas ausentes sea una pérdida; lo que sí es seguro es que el aviso no discrimina.

**Prueba**: ficha con 2 ubicaciones y un tajo de ámbito `edificio` (1 celda legítima) → no debe avisar; borrar una celda de un tajo de vivienda → debe avisar. Hoy el primero avisa y el segundo no se distingue del primero.

---

## 6. [Media] Bloque «Orueta» del catálogo: dos mecanismos sin efecto

**Dónde**
- `M/reglas/CATALOGO_TAJOS.json:1959` `"forzar_historial_terminado_hasta": "24/09/2025"`. Único rastro en código: un **comentario** (`M/priorizador_trabajos.py:481-483`) que dice que «ese cierre ya se aplica revisión a revisión en `_construir_estado`». `_construir_estado` **ya no existe** (`priorizador_trabajos.py:217`: «Sustituye a `_construir_estado`»). Ningún `.py` lee la clave.
- `priorizador_trabajos.py:500-501`: `edificio = edificios_pb[0] if edificios_pb else "Obispo Orueta 2"` (nombre de obra incrustado) y `:503` ignora en silencio cualquier `excepciones[].tipo` distinto de `pendiente_especial`.

**Impacto hoy**: ninguno — Orueta está cerrada y archivada. Pero es exactamente «declarado que el motor ignora»: si la obra se reabriera (o una obra nueva copiara la receta), el cierre por fecha no se aplicaría y nada lo diría. Además el comentario engaña al siguiente lector.

**Prueba**: test de catálogo: para cada clave de `config_obra` (`obras.*`), exigir que figure en una lista de claves conocidas que el motor consume; una clave desconocida debe fallar la prueba. Hoy pasaría `forzar_historial_terminado_hasta` sin que nadie la lea.

---

## 7. [Media-baja] Ficha ilegible → se degrada a «estructura deducida de celdas»

**Dónde**
- `M/generar_todos.py:413-419` (`cargar_ficha_obra`): `except Exception` → `print AVISO` + `return None` («Se deduce la estructura de las revisiones, como antes»). No se añade a `fallidas`.
- Adaptadores, mismo patrón: `adaptador_bolueta.py:408-416`, `adaptador_olabeaga.py:316-324`, `adaptador_barakaldo.py:310-318`, `adaptador_mungia.py:324-332`, `adaptador_gorliz.py:303-311` → `return []`: se **ignoran todos los HTML** de la obra.

**Declarado vs ignorado**: la ficha es la fuente de la estructura; sin ella la obra vuelve al modo que dejaba viviendas sin marcar invisibles («Estructura deducida de celdas rellenas», `CLAUDE.md` §2). Un `ficha_obra.json` a medio escribir (OneDrive, disco lleno) produce ese modo, con un `print` perdido entre cientos de líneas. En Bolueta, además, el historial caería al último PDF/Word (agosto) mientras los HTML llegan hasta 27/10.

**Impacto**: no medido (requiere forzar el fallo). Contrasta con `_correcciones_mas_recientes`, que sí avisa con detalle, y con `_bloque_obras_fallidas`, pensado justo para que estos casos no queden perdidos.

**Prueba**: copia temporal de una obra con `ficha_obra.json` truncado; exigir que la obra aparezca en el bloque de obras fallidas (o que la generación se detenga para esa obra) en vez de continuar con la estructura deducida.

---

## 8. [Baja] Guarda de «edad de la revisión» inalcanzable

**Dónde**: `M/priorizador_trabajos.py:545-550`:
```
try: edad_dias = (referencia - _fecha(ultima_fecha).date()).days
except Exception: pass
caducada = edad_dias is None or edad_dias > 30
```
`_fecha` (`:61-65`) ya captura `TypeError/ValueError` y devuelve `datetime.min`, así que el `except` y la rama `edad_dias is None` **nunca se ejecutan**.

**Demostrado en memoria**: con `ultima_fecha` = `None`, `'31/13/2026'` o `'no es fecha'`, la edad sale 739 923 días. Una ficha sin revisiones da `revision_caducada=True`, `edad_revision_dias=739923` y el aviso literal «La revisión es del None (739923 días)» (`:965-969`, `:1046-1050`).

**Impacto**: bajo y visible (el texto es absurdo, no engaña), pero «desconocido» queda convertido en un número enorme, no en «sin fecha». Con `hoy` tipo `datetime` la resta sí lanzaría `TypeError` y entonces sí se ejecutaría el `pass`.

**Prueba**: `priorizar_ficha` con ficha sin `revisiones` → exigir `edad_revision_dias is None` y un aviso «sin fecha de revisión».

---

## 9. [Baja] Claves del catálogo que ningún código lee

Medido con `grep` en `.py`, `.js`, `.html`, `.bat` (sin tests):

| Clave | Dónde | Lectores |
|---|---|---|
| `estado_m`, `estado_x` | 93 tajos comunes + 19 propios (p. ej. `CATALOGO_TAJOS.json:29`) | solo el valor por defecto de un tajo desconocido (`priorizador_trabajos.py:142-143`) |
| `orden_inventario` (raíz, `:10`) | lista de 5 secciones | ninguno. El orden real es `SECCION_ORDEN` (`priorizador_trabajos.py:31-38`), de **6** secciones: el catálogo no incluye `SIN_REVISAR` y el código la coloca antes de `TERMINADO` |
| `estados` (raíz, `:4`) | diccionario de etiquetas | ninguno (el código usa `ESTADO_VALOR`) |
| `descripcion` (raíz, `:3`) | texto | ninguno |

**Impacto**: nulo en cifras hoy; es documentación presentada como configuración. Editar `orden_inventario` creyendo que reordena el inventario no hace nada, y si algún día se leyera sin actualizar fallaría con `SIN_REVISAR`. `estado_m/estado_x` describen qué significa `M` y `X` por tajo: si se pretendía enseñarlo en panel o informe, no se enseña.

**Prueba**: la misma de §6 (lista de claves consumidas).

---

## 10. [Baja] `except … pass/continue` en portal y en fusión de personal

- `_SISTEMA/MOTOR/sagarde_portal.py:1427`: `except Exception: pass` al leer `auditoria_diagnostico.json`. Un diagnóstico corrupto hace desaparecer el banner «Salud de Datos» y se lee como «0 avisos». `:140` (`load_json_safe`) devuelve `None` ante JSON corrupto sin mensaje; quien lo llame debe tratar `None` como «ilegible», no como «vacío» (no se revisaron todos sus usos).
- `M/personal_obra.py:1447-1451`: la guarda de fusión que comprueba, en **todas** las obras, que origen y destino no coinciden el mismo día salta con `continue` cualquier `personal_obra.json` ilegible. La comprobación queda incompleta sin aviso (riesgo: una persona suma dos veces un día).

**Prueba**: portal con `auditoria_diagnostico.json` corrupto → exigir una alerta de «diagnóstico ilegible». Fusión con un `personal_obra.json` roto → exigir `ok: False` o aviso.

---

## 11. [Baja] Línea base de verificación obsoleta y no automática

`CLAUDE.md` §3 fija «Mungia 79.8, Gernika 76.3, Bolueta 41.7, Obispo Orueta 80.0» como cifras que no deben moverse. El mapa mental (tabla automática del 02/11/2026) da hoy **Mungia 90.3 · Gernika 94.1 · Bolueta 76.7**; Orueta está cerrada (`SAGARDE (OLD)`). Barakaldo y Olabeaga, que sí se retocan, no figuran. `M/tests/linea_base_prioridades.py` dice de sí mismo «No es una prueba»: no hay línea base legible por máquina.

**Impacto**: la regla «las obras no implicadas no se mueven» depende de que alguien recuerde cifras que ya no valen; un efecto colateral puede pasar por «es lo normal».

**Prueba/propuesta**: fichero de línea base (por obra: X/M//P/?/N) generado desde el historial validado y una prueba que lo compare, con actualización explícita al cambiar una obra.

---

## 12. [Baja, latente] Parser HTML: lo no reconocido pasa a «pendiente»

- `M/lector_hoja_tajos_html.py:242` y `M/adaptar_revision_html.py:771`: `status = estado if estado in ('X','M','/') else ''`. Cualquier otra cosa (`P`, **`?`**, minúscula, errata) se convierte en pendiente: un desconocido cuenta como `P`, la confusión que `CLAUDE.md` §7 llama «causa de casi todo lo que ha fallado».
- `lector_hoja_tajos_html.py:231`: `len(partes) != 4: continue` salta claves mal formadas sin contarlas (las no resueltas por portal/planta/tajo sí se avisan, `:250`).

**Impacto**: hoy la app solo exporta `X/M//N` y vacío → 0 casos. Es el historial *crudo*; la ficha usa el camino normalizado, que sí valida contra `ALFABETOS_HOJA` (`validar_revision.py:27-35, 371-373`; `adaptar_revision_html.py:578`).

**Prueba**: HTML con `data-st="?"` y `data-st="x"`; exigir aviso o estado `?`, no pendiente.

---

## Descartados o dudosos (y por qué)

| Candidato | Motivo |
|---|---|
| `ficha_garajes.json` con «huérfanos» | Artefacto de mi escáner: la estructura de garaje (`garajes/plantas/zonas`) difiere de la de vivienda. Las 6 `ficha_obra.json` tienen 0 estados huérfanos. |
| `memoria_obra.py:89` (`cargar_memoria` → `{}` ante corrupción) | Sin llamadores en el ámbito (solo la definición). Código muerto, sin efecto. |
| `generar_todos.py:~2191` `pct = 0` si `kpis` vacío | No demostrado que se vea: Gorliz (sin revisiones) sale en el índice como «Sin revisiones», no como 0 %. Revisar si se añade una obra con ficha solo `?`/`N`. |
| PDF ejecutivo truncado por fallo a medias de `doc.build` | Plausible pero no verificable sin ejecutar (§3). |
| `adaptador_zorrozaure.py:98`, `cache_pdf.py:161` | Zorrozaure es adaptador huérfano (obra no registrada); `cache_pdf` es una caché cuyo fallo solo cuesta tiempo. |
| `lector_control_horario.py` (395-416, 509), `personal_integracion.py` (175, 497, 548) | Devuelven un motivo/incidencia (`RECHAZADO`, `PERSONAL_*`), no callan. |
| `except ValueError: return None` de parseo de fechas (`generar_todos.py:228,265`, `ficha_obra.py:129,648`) | Fallback documentado, con consecuencia visible o solo de ordenación. |
| `_SISTEMA/MOTOR/CLAUDE.md` con rutas `_MOTOR_SAGARDE/…` | Documentación desfasada; el comando fallaría con ruido, no en silencio. No es de esta familia. |
| `generar_todos.py:1200` `except OSError: continue` | Cálculo de «última actividad» de una carpeta; no afecta a cifras. |

## Nota adicional (documentación desfasada, no es fallo de código)

El mapa mental (§2) y `CLAUDE.md` afirman que `reglas/CATALOGO_TAJOS.json` **no está en git** («no hay `git checkout` que lo restaure»). `git ls-files` lo lista hoy en `M/reglas/CATALOGO_TAJOS.json`. Conviene corregir el aviso: si la afirmación estuviera en la memoria de alguien, evitará mutar un fichero que sí se puede restaurar — o, peor, hará creer que no hay copia.

## Orden de ataque recomendado

1. Hallazgos 1 y 2 (únicos con casos reales medidos): contador y aviso de claves sin casar; error o aviso por revisiones HTML de la misma fecha; que el auditor mire `.html`.
2. Hallazgo 3: que el fallo del informe ejecutivo cuente como obra fallida.
3. Hallazgos 4 y 5: validar el alfabeto al cargar la ficha; sustituir la «rejilla densa» por una comprobación por ámbito.
4. Resto: limpieza de catálogo y documentación.

Cada corrección que mueva cifras debe reportar antes/después a Bixente con el desglose `X/M//P/?/N`, no solo el porcentaje.
