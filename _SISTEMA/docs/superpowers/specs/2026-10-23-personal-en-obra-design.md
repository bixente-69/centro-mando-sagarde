# Personal en obra — especificación y contrato de datos (P0)

Estado: **borrador para aprobación de Bixente** (23/10/2026). Plan de reparto: `docs/superpowers/plans/2026-10-23-personal-en-obra-plan-por-ias.md`.
Maqueta aprobada de palabra: `D:\Nueva carpeta\OneDrive\PROYECTO PERSONAL EN OBRA\maqueta\maqueta_personal.html`.

## 1. Qué se construye

Una app de campo (móvil y tablet) para anotar qué trabajadores hay cada día en cada obra, con su base de datos acumulada, la
jornada base de 7,5 h y las horas extra; y, con esos datos, listados por semana/mes/año/obra y gráfica de **% de impacto** en
la pestaña **Personal**, en el **Informe de obra** y en un **ranking global de Sagarde**. El fin: saber quién trabaja más para
Sagarde y quién tiene más impacto.

**No se toca:** `generador_revisiones.html`, las demás pestañas del panel, las fichas de obra ni ninguna obra sin datos de
personal (se ven exactamente como hoy).

## 2. Decisiones cerradas

| # | Decisión |
|---|---|
| D1 | Los datos **se publican** (uso personal de un solo usuario; informe de obra desde la tablet). El trabajador se identifica por su **nombre**, texto libre, tal como lo escribe Bixente. Sin «alias», sin avisos sobre si es mote o nombre real. |
| D2 | App = un HTML único `generador_personal.html`, sin CDN, que abre sin cobertura. Carga `personal_estado.js` publicado y, si no hay red, la última copia guardada en el aparato. |
| D3 | **Jornada base 7,5 h de lunes a viernes**; sábado y domingo sin horario (todo lo anotado es extra). Horario por obra, editable. Excepción por trabajador: ~~solo en el modelo de datos, sin pantalla en la v1~~ → **con pantalla en la v1** (cambiado por Bixente el 24/10/2026, §16 y §17). |
| D4 | % de impacto = horas del trabajador ÷ horas totales del periodo, a nivel obra y a nivel Sagarde. |
| D5 | Solo gente de Sagarde. `empresa` opcional. |
| D6 | Ranking global de Sagarde incluido (paquete P5b). |

## 3. Propuestas pendientes de tu confirmación al aprobar

| # | Propuesta | Por qué |
|---|---|---|
| A | **Corregir o anular una jornada ya guardada.** Misma clave (obra, ámbito, fecha) sustituye; `anulada: true` la borra de los cálculos y deja traza. La app tiene una pantalla «Jornadas» para abrir una anterior y corregirla. | Hoy no hay forma de arreglar un error. |
| B | **Lista inicial = última jornada + habituales** (quien estuvo ≥ 3 días en esa obra y ámbito en los últimos 30 días), todos sin marcar. | Quien faltó la última vez no desaparece. |
| C | **Safari borra los datos de una web sin uso en 7 días:** la app avisa de instalarla en la pantalla de inicio, muestra siempre cuántas jornadas están pendientes de pasar al PC y recuerda exportar al acabar el día. | Evita perder jornadas. |
| D | **Aviso** si una misma persona suma más de 12 h en un día (entre todas las obras y ámbitos); **rechazo** si pasa de 24 h. | Doble anotación. |

## 4. Ficheros y rutas

| Fichero | Ruta | Se publica | Quién lo escribe |
|---|---|---|---|
| Catálogo de trabajadores | `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/personal_catalogo.json` | sí | `personal_obra.py` |
| Datos de una obra | `SAGARDE OBRAS ABIERTAS/<carpeta obra>/INFORME SAGARDE IA/personal_obra.json` | sí | `personal_obra.py` |
| Traza de ingestas | `…/<carpeta obra>/INFORME SAGARDE IA/personal_jornadas.jsonl` (aditiva) | sí | `personal_obra.py` |
| Estado para la app y el ranking | `…/_SISTEMA INFORME SAGARDE IA/personal_estado.js` | sí | `personal_obra.py exportar-estado` |
| Cálculo compartido | `…/_SISTEMA INFORME SAGARDE IA/personal_calculo.js` | sí | **ya hecho (P2)** |
| Módulo de datos | `…/_SISTEMA INFORME SAGARDE IA/personal_obra.py` | sí | P1 |
| App de jornada | `…/_SISTEMA INFORME SAGARDE IA/generador_personal.html` | sí (`!*.html`) | P3 |
| Página del ranking | `…/_SISTEMA INFORME SAGARDE IA/personal_sagarde.html` | sí (`!*.html`) | P5b |

El `id` de obra es el del registro (`registro_obras.py`): `gernika`, `mungia`, `bolueta`, `gorliz`, `prueba`, `olabeaga`,
`barakaldo`. **Trampa conocida:** el `.gitignore` es lista blanca; los `.js`, `.json` y `.jsonl` de arriba necesitan entrada propia
(P6) y cada uno una prueba de que de verdad se publica. Las obras cerradas conservan su `personal_obra.json` y el estado las
sigue contando (marcadas `cerrada`), para que cerrar una obra no la borre del ranking.

## 5. Contrato de datos (esquemas CERRADOS: un campo fuera del esquema se rechaza con aviso, no se ignora)

**Nombre limpio:** texto sin espacios al principio ni al final y con los espacios internos colapsados a uno, 1–60 caracteres, sin
caracteres de control. **Clave de nombre** (para comparar): nombre limpio, minúsculas y sin tildes (`Iñaki` → `inaki`).
Dos nombres con la misma clave son la misma persona.

### 5.1 `personal_catalogo.json`
```json
{ "version": 1,
  "trabajadores": [
    { "id": "T0001", "nombre": "Mikel", "categoria": "", "empresa": "", "activo": true,
      "alta": "2026-10-23", "fusionado_en": null } ] }
```
`id` = `T` + 4 cifras (más si hace falta), creciente, **nunca se reutiliza**. `categoria` y `empresa`: texto libre opcional.
`activo` (por defecto `true`). `fusionado_en`: `null` o el `id` al que se fusionó (el duplicado se conserva para trazabilidad y
no sale en el desplegable; sus jornadas cuentan para el destino). Las claves de nombre de los trabajadores no fusionados son únicas.

### 5.2 `personal_obra.json`
```json
{ "version": 1, "obra": "olabeaga", "jornada_base_h": 7.5,
  "horario_semanal": { "lun": 7.5, "mar": 7.5, "mie": 7.5, "jue": 7.5, "vie": 7.5, "sab": 0, "dom": 0 },
  "excepciones_horario": { "T0001": { "vie": 6 } },
  "jornadas": [
    { "fecha": "2026-10-22", "ambito": "vivienda", "anulada": false, "notas": "",
      "presentes": [ { "id": "T0001", "horas": 7.5, "extra": 0 }, { "id": "T0003", "horas": 9.5, "extra": 2 } ],
      "registrado": "2026-10-22T19:40:00+02:00", "origen": "movil" } ] }
```
- `obra`: id del registro. `ambito` ∈ `vivienda | garaje`. **Clave de jornada = (obra, ámbito, fecha); única.**
- `fecha`: `YYYY-MM-DD`, fecha real de calendario.
- `horas`: número ≥ 0 y ≤ 24, con como mucho 2 decimales. `extra`: número, `0 ≤ extra ≤ horas`, opcional (0 si falta).
  **Se guarda lo medido:** `extra` se calcula en la app contra el horario del día y se guarda; un cambio posterior del horario
  no reescribe jornadas pasadas.
- `presentes`: sin repetir persona. `anulada: true` ⇒ `presentes: []` y la jornada no cuenta (la fila se conserva como lápida).
- `origen` ∈ `movil | pc`. `registrado`: fecha y hora ISO con zona. `notas`: ≤ 500 caracteres.
- Ordenación estable al guardar: jornadas por `(fecha, ambito)`, presentes por `id`. UTF-8 sin BOM, `ensure_ascii=False`,
  sangría de 1 espacio. Escritura atómica (fichero temporal + reemplazo) con hasta 5 reintentos con espera si OneDrive bloquea el fichero
  (`PermissionError`); si no se consigue, no deja ficheros a medias y lo avisa.

### 5.3 Lote que exporta la app (`lote_personal`) — es el único formato de entrada del PC
```json
{ "tipo": "lote_personal", "version": 1, "obra": "olabeaga",
  "horario_semanal": { "lun": 7.5, "mar": 7.5, "mie": 7.5, "jue": 7.5, "vie": 7.5, "sab": 0, "dom": 0 },
  "jornadas": [
    { "ambito": "vivienda", "fecha": "2026-10-23", "anulada": false, "notas": "",
      "presentes": [ { "nombre": "Mikel", "horas": 7.5, "extra": 0 } ],
      "registrado": "2026-10-23T18:05:00+02:00" } ],
  "dispositivo": "tablet" }
```
`horario_semanal`, `excepciones_horario` y `dispositivo` son opcionales. En el lote los presentes van **por nombre**; el PC los resuelve a `id` por
clave de nombre (los fusionados resuelven a su destino). Un nombre que no existe se **da de alta** (aviso `alta_nueva`).

**`excepciones_horario` (paso 01b, 24/10/2026; contrato cerrado en §17):** horario propio por trabajador, `{ "<nombre>": { "<día>": horas } }`, con días
`lun mar mie jue vie sab dom` (solo los que difieren) y `{}` = quitar. El objeto de la persona **sustituye** al guardado. Ejemplo:
`"excepciones_horario": { "Aitor": { "vie": 9 }, "Gorka": { "vie": 9 }, "Mikel": {} }`.

### 5.4 `personal_estado.js` (lo genera el PC; lo lee la app y la página del ranking)
```js
window.SAGARDE_PERSONAL = { "version": 1, "generado": "2026-10-23T22:07:00+02:00", "jornada_base_h": 7.5,
  "catalogo": [ { "id": "T0001", "nombre": "Mikel", "categoria": "", "empresa": "", "activo": true } ],
  "obras": { "olabeaga": { "nombre": "2026 OLABEAGA BILBAO", "cerrada": false,
     "horario_semanal": { "lun": 7.5, "...": 0 }, "excepciones_horario": { "Mikel": { "vie": 6 } },
     "ultima": { "vivienda": { "fecha": "2026-10-22", "presentes": [ { "nombre": "Mikel", "horas": 7.5, "extra": 0 } ] },
                 "garaje": null },
     "jornadas": [ { "fecha": "2026-10-22", "ambito": "vivienda", "nombre": "Mikel", "horas": 7.5, "extra": 0 } ] } } };
```
Sin los fusionados en `catalogo`; en `jornadas`, el nombre es el del destino; **sin jornadas anuladas**; `ultima` = la jornada no
anulada de fecha más reciente de cada ámbito (`null` si no hay). `jornadas` son las **filas planas** que consume
`personal_calculo.js`. Quien las consuma (la app, el panel o la página del ranking) añade el campo `obra` al cargarlas. En
`excepciones_horario` el estado usa el **nombre** canónico como clave (el PC lo resuelve desde el `id` de `personal_obra.json`),
porque la app trabaja con nombres. Determinista: mismo contenido ⇒ mismos bytes
(salvo `generado`, que se puede fijar al probar).

### 5.5 Lo que guarda la app en el aparato (`localStorage`)
`sgd_personal_estado` (copia del último `personal_estado.js`), `sgd_personal_pendientes` (jornadas guardadas aún sin ingerir),
`sgd_personal_borrador` (formulario en curso).

## 6. Validación (P1)

Todo o nada **por jornada**: si una jornada se rechaza, no cambia nada (ni jornada ni altas). Cada incidencia lleva un código.

| Código | Severidad | Cuándo |
|---|---|---|
| `lote_invalido`, `version_desconocida`, `tipo_desconocido` | rechazo del lote | JSON ilegible, `tipo` ≠ `lote_personal` o versión no soportada |
| `horario_invalido` | rechazo del lote | `horario_semanal` sin exactamente las claves `lun mar mie jue vie sab dom`, o con valores no numéricos, fuera de 0–24 o con más de 2 decimales |
| `excepcion_invalida` | rechazo del lote | `excepciones_horario` no es un diccionario; un nombre vacío, de más de 60 caracteres, con caracteres de control o repetido por clave de nombre; un valor que no es diccionario; un día que no es `lun…dom`; o una hora fuera de 0–24 / con más de 2 decimales / no numérica (§17) |
| `obra_invalida` | rechazo | el id no está en la lista de obras válidas que recibe el módulo |
| `ambito_invalido`, `fecha_invalida` | rechazo | fuera de `vivienda\|garaje`; no es fecha real |
| `campo_desconocido` | rechazo | cualquier campo fuera del esquema, a cualquier nivel |
| `nombre_vacio` | rechazo | presente sin nombre tras limpiar (o que no es texto) |
| `nombre_invalido` | rechazo | nombre limpio de más de 60 caracteres o con caracteres de control |
| `presente_duplicado` | rechazo | dos presentes con la misma clave de nombre |
| `horas_invalidas` | rechazo | `horas` ausente, no numérica, < 0, > 24 o con más de 2 decimales (el ruido de coma flotante menor de 1e-9, como `12.000000000000002`, se redondea a 2 decimales antes de validar) |
| `extra_invalido` | rechazo | `extra` no numérico, < 0 o > `horas` |
| `anulada_con_presentes` | rechazo | `anulada: true` con presentes |
| `sin_presentes` | rechazo | jornada vacía que **no** está anulada (para quitar una jornada se usa `anulada`; así un guardado vacío no borra datos por error) |
| `jornada_repetida_en_lote` | rechazo | dos jornadas del mismo lote con la misma clave (obra, ámbito, fecha): se rechazan las dos |
| `suma_diaria_invalida` | rechazo | la misma persona supera 24 h el mismo día entre todas las obras y ámbitos |
| `suma_diaria_alta` | aviso | supera 12 h (y no 24) |
| `fecha_futura` | aviso | fecha posterior a hoy (el módulo recibe `hoy` para poder probarlo) |
| `alta_nueva` | aviso | el nombre no existía: se crea |
| `nombre_parecido` | aviso | alta nueva, con ambas claves de ≥ 3 letras, que contiene a otra o dista ≤ 1 de ella: «¿es la misma persona? → `fusionar`» |
| `reemplazo` | aviso | sustituye una jornada con la misma clave |

## 7. Operaciones (P1: `personal_obra.py`, solo biblioteca estándar)

API Python (todas puras salvo las que escriben; **simulan por defecto**, `escribir=True` para guardar):
`limpiar_nombre`, `clave_nombre`, `cargar_catalogo`, `guardar_catalogo`, `alta_trabajador`, `validar_lote`, `ingerir_lote`,
`ultima_jornada`, `fusionar`, `exportar_estado`, `aplanar`, `totales_control`, `comprobar`.

CLI: `py -3.11 personal_obra.py ingerir <fichero.json>` · `fusionar <id_origen> <id_destino>` · `exportar-estado` · `comprobar`,
todos con `[--escribir]`. El fichero del lote llega por OneDrive, correo o WhatsApp y se pasa por ruta. **Raíz:** el módulo localiza
`SAGARDE OBRAS ABIERTAS` desde la ubicación del propio fichero (como `generar_todos.py`, sin depender del directorio actual) y
acepta `raiz=` para probar sobre carpetas temporales. Salida 0 = bien (aunque haya
avisos: se imprimen con «REVISAR»); 2 = alguna jornada rechazada; 1 = error de uso o de lectura.

- `ingerir_lote` devuelve `{escrito, jornadas: [{clave, estado: aceptada|rechazada, accion: alta|reemplazo|anulacion|null, rechazos: [código], avisos: [{codigo, detalle}]}], altas: [{id, nombre}]}`.
- La **reingestión del mismo lote no cambia nada** (idempotente: mismos bytes).
- `fusionar(origen, destino)`: marca el origen `fusionado_en`, no toca las jornadas (se resuelven al leer), y deja traza. No permite
  ciclos ni fusionar sobre uno ya fusionado.
- `totales_control(obra)`: horas, extra, días y por trabajador, calculados de forma **independiente y simple** (un solo bucle) para
  compararlos con `personal_calculo.js` en la guarda de P6.
- **Trazabilidad** `personal_jornadas.jsonl`: una línea por jornada ingerida `{ts, obra, ambito, fecha, accion, n_presentes, avisos, dispositivo}`. Aditiva y no bloqueante: si falla, avisa y no revierte.
- Un dato que falta **nunca** se convierte en cero.

### 7b. Firma de la API (cerrada para P1; añadida tras la aprobación al diseñar los verificadores)

Todas reciben `raiz` (carpeta `SAGARDE OBRAS ABIERTAS`) y, las que tocan obras, `obras` = `{id_obra: carpeta de la obra relativa a raiz}`.
Fechas como texto `YYYY-MM-DD`; `hoy` y `ahora` (fecha y hora ISO con zona) se inyectan para poder probar.

| Función | Devuelve |
|---|---|
| `limpiar_nombre(texto)` | texto con espacios (y tabuladores y saltos) colapsados a uno y sin espacios en los extremos; `''` si no es texto |
| `nombre_valido(texto)` | `True` si el nombre limpio tiene 1–60 caracteres y ningún carácter de control |
| `clave_nombre(texto)` | nombre limpio, sin tildes y en minúsculas |
| `cargar_catalogo(raiz)` | dict del catálogo (`{"version":1,"trabajadores":[]}` si no existe el fichero) |
| `cargar_obra(raiz, obras, obra)` | dict de `personal_obra.json` (con horario base L–V 7,5 y sin jornadas si no existe) |
| `alta_trabajador(raiz, nombre, categoria='', empresa='', hoy=None, escribir=False)` | `{ok, id, error, parecidos, escrito}`; `error` ∈ `None`, `nombre_vacio`, `nombre_invalido`, `nombre_duplicado` |
| `ingerir_lote(lote, raiz, obras, hoy, escribir=False, ahora=None)` | `{ok, escrito, lote_rechazado:[código], avisos_lote:[{codigo, detalle}], jornadas:[{clave:[obra,ambito,fecha], estado:'aceptada'\|'rechazada', accion:'alta'\|'reemplazo'\|'anulacion'\|'sin_cambios'\|None, rechazos:[código], avisos:[{codigo, detalle}]}], altas:[{id, nombre}]}`; `ok` = nada rechazado |
| `ultima_jornada(raiz, obras, obra, ambito)` | `{fecha, presentes:[{nombre, horas, extra}]}` (presentes por id) o `None` |
| `fusionar(raiz, origen, destino, escribir=False, ahora=None)` | `{ok, error, escrito}`; `error` ∈ `None`, `id_inexistente`, `mismo_id`, `origen_ya_fusionado`, `destino_fusionado`, `conflicto_en_jornada` (ambos aparecen en una misma jornada) |
| `exportar_estado(raiz, obras, nombres_obra=None, cerradas=(), generado=None, escribir=False)` | texto de `personal_estado.js` |
| `aplanar(raiz, obras, obra)` | filas `{fecha, ambito, nombre, horas, extra}` sin anuladas, ordenadas por (fecha, ámbito, nombre) |
| `totales_control(raiz, obras, obra=None)` | `{horas, extra, dias, trabajadores, por_trabajador:{nombre:{horas, extra, dias}}}`; `obra=None` = todas; **`None` si no hay filas** (nunca ceros) |
| `comprobar(raiz, obras)` | lista de textos con los problemas hallados (vacía = bien) |

Reglas de la ingesta que el contrato no decía: una jornada con **contenido idéntico** al guardado (misma fecha, ámbito, anulada,
notas y presentes; se ignora `registrado`) da `accion: 'sin_cambios'`, no escribe nada y no deja traza; así reingerir un lote no
cambia ni un byte. `origen` de lo ingerido = `movil`; `registrado` = el del lote o, si falta, `ahora`. Las jornadas de un lote se
evalúan **en orden** y cada una ve las anteriores ya aceptadas; la suma diaria de una persona cuenta las horas de las **demás**
jornadas de esa fecha (en todas las obras y ámbitos) más las de la jornada evaluada, sin contar la que va a sustituir. Un fallo al
escribir la traza **no** revierte (`avisos_lote: traza_no_escrita`). Ids nuevos: el mayor existente + 1, en orden de aparición.
`nombre_parecido`: ambas claves de **≥ 3 letras** y la nueva dista ≤ 1 (Levenshtein) de la otra o una contiene a la otra (los
nombres de 1–2 letras no se comparan: dan ruido); un aviso por alta, con el primer parecido; se compara con
el catálogo más las altas anteriores de la misma ingesta. El `detalle` de `alta_nueva` es el nombre limpio creado y el de
`nombre_parecido` es `nuevo ~ existente` (por ejemplo `Mikell ~ Mikel`). CLI: `--raiz`
(por defecto, la carpeta que contiene la del módulo), `--obras id=carpeta,id=carpeta` (por defecto, el registro de obras, importado al
usarlo), `--hoy`, `--escribir`; salida 2 también si se rechaza el lote entero; salida 1 si el fichero no existe o no es JSON.

## 8. Cálculo (hecho en P2: `personal_calculo.js`, 111 comprobaciones, 5 mutaciones detectadas)

Semana lunes–domingo (ISO), `mes`, `anio`, `obra`. Días = fechas distintas. Horas ordinarias = horas − extra. `pct` sin redondear;
se redondea solo al pintar (a 1 decimal, con la nota «pueden sumar 99,9 o 100,1»). Periodo sin jornadas ⇒ «sin jornadas»,
nunca 0. Filas sin horas o inválidas no cuentan y se avisan.

## 9. App `generador_personal.html` (P3)

Como la maqueta aprobada, más:
1. Flujo: obra → ámbito → fecha (Hoy/Ayer/Anteayer) → lista cargada (propuestas A/B) → X (fija las horas del horario del día; solo se piden a mano en un día sin horario o para ajustar, ± 0,5) → añadir del
   desplegable con buscador → nombre nuevo (limpieza de espacios y aviso «se parece a…») → guardar.
2. En un día sin horario **no se guarda 0**: las horas son obligatorias (el primer toque fija 7,5 h).
3. Horario semanal editable por obra; «Marcar/Desmarcar todos»; borrador automático; «Empezar de cero».
4. Pantalla **«Jornadas»** (propuesta A): jornadas del aparato y últimas publicadas; abrir una para corregirla o anularla.
5. Pantalla **«Informe de personal»** con `personal_calculo.js` sobre lo publicado + lo pendiente del aparato.
6. **Exportar** `lote_personal` (descarga y compartir); **Importar estado** de un fichero como alternativa si no hay red.
7. Aviso de instalación en pantalla de inicio y contador de pendientes (propuesta C).
8. Zonas táctiles ≥ 56 px (X), ≥ 48 px (±), ≥ 52 px (botones). Sin dependencias externas, < 300 KB.
9. **Carga del estado:** con `<script src="personal_estado.js?v=<marca de tiempo>">` (como `obras_revisiones.js`; nada de `fetch`,
   que `file://` bloquea) para saltarse la caché; si no carga, se usa la copia de `sgd_personal_estado`.
10. **Nombres:** antes de calcular, la app resuelve cada nombre escrito a mano contra el catálogo por clave de nombre (mismas
    reglas que el PC), para que «mikel» y «Mikel» sean uno también en las jornadas aún sin ingerir.
11. **Si se pierde el `localStorage`:** el catálogo y las jornadas publicadas se reconstruyen desde `personal_estado.js`; los
    borradores y las jornadas pendientes de ingerir no se recuperan (de ahí el contador y el recordatorio de exportar).
12. Al cambiar el horario semanal, aviso de que **no modifica las jornadas ya guardadas**.

## 10. Panel, informe, ranking, publicación (P4–P6)

- **Pestaña Personal (P4):** `panel_personal.py` devuelve el HTML de la vista, con `personal_calculo.js` y las filas planas de la obra
  **incrustados** (autocontenido). Selector Semana/Mes/Año/Obra, filtro Todo/Viviendas/Garajes, KPI, tabla y barras de impacto
  como en la maqueta. Obra sin `personal_obra.json` ⇒ lo de hoy (tabla de la hoja `Personal` o «Sin datos…»).
- **Informe de obra (P5):** el checkbox `data-seccion="personal"` incluye la matriz trabajador × columnas y las barras; funciona desde la tablet.
- **Ranking (P5b):** `personal_sagarde.html` carga `personal_estado.js` y `personal_calculo.js` con rutas relativas; tarjeta nueva en el portal.
- **Integración (P6):** `generar_todos.py`/`regenerar_obra.py` leen los datos (un fallo de personal **nunca** tumba el panel de una obra);
  entradas en la lista blanca del `.gitignore`:
  ```
  !SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/personal_estado.js
  !SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/personal_calculo.js
  !SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/personal_catalogo.json
  !SAGARDE OBRAS ABIERTAS/*/INFORME SAGARDE IA/personal_obra.json
  !SAGARDE OBRAS ABIERTAS/*/INFORME SAGARDE IA/personal_jornadas.jsonl
  ```
  con una prueba por cada una de que de verdad se publica; auditor del paso 0 del `.bat` que falla si un fichero de personal trae
  campos fuera del esquema o si los totales de `personal_calculo.js` no coinciden con `totales_control`; skill `sagarde-personal`;
  actualización del mapa mental; `cerrar_obra.py` conserva el fichero de personal.

## 11. Pruebas y criterios de aceptación

- **P1:** verificador `unittest` oculto al trabajador (`staging/_verificadores/verificar_p1.py`, movible a `tests/` en P6) con fixtures
  inventados: ingestión limpia, idempotencia, reemplazo, anulación, **un caso por cada código de §6**, fusión (con ciclo),
  `ultima_jornada` por ámbito, `exportar_estado` determinista, `totales_control` contra cifras hechas a mano, escritura atómica y
  traza no bloqueante. **Mutaciones** exigidas: idempotencia, separación vivienda/garaje, campo desconocido, suma diaria,
  resolución de fusionados, orden estable.
- **P2:** hecho (ver §8).
- **P3:** (la purga de datos de Safari no es automatizable: se prueba el aviso y el contador de pendientes) Playwright a 390 y 820 px: recorre el flujo, exporta el lote, lo pasa por `validar_lote` con 0 rechazadas, recarga y conserva
  el borrador, funciona sin red con la copia local, coincide con `personal_calculo.js`; Claude lo mira en pantalla.
- **P4/P5/P5b:** cifras de P2; obra sin datos igual que hoy; `panel.html` y portal de las **demás obras idénticos byte a byte**.
- **P6/P7:** suite completa (`python -m unittest discover -s tests`), mutación de cada guarda, antes/después de las obras no
  implicadas, piloto real con una jornada de Olabeaga **sin publicar hasta tu visto bueno**.

## 12. Fuera de alcance (v1)

(La pantalla de horario propio por trabajador **ya no está fuera de alcance**: entra en la v1, §16 y §17.) Festivos, importar nada de nóminas o vida laboral, subcontratas y otros gremios,
sincronización automática móvil→PC (el paso es un fichero), gráficas fuera de las barras de impacto.

## 13. Riesgos que quedan aceptados

Datos publicados (D1); la transferencia móvil→PC es manual; dos nombres escritos distinto pueden falsear el ranking hasta que se
fusionen (avisos y `fusionar` lo mitigan, no lo eliminan).

## 14. Revisión independiente de esta especificación (gemini, 23/10/2026; 2 rondas, 183 s)

Contrastada punto por punto contra la propia especificación y el código antes de aplicar nada.
- **Aplicado:** quién añade `obra` a las filas planas; clave de `excepciones_horario` en el estado; firma de la CLI, canal de
  transferencia y raíz de rutas; pérdida de `localStorage`; **jornadas repetidas en un lote** (`jornada_repetida_en_lote`); ruido de
  coma flotante en las horas; **jornada vacía no anulada = rechazo** (antes era un aviso y podía borrar datos); aviso al cambiar el
  horario; reintentos de escritura en OneDrive; cómo se fuerza la descarga del estado nuevo (`?v=`); la purga de Safari no se prueba;
  la app resuelve nombres por clave antes de calcular; marcar X fija las horas del horario del día.
- **Descartado por incorrecto:** que `fetch` desde `file://` bloquee la carga (el estado se carga con `<script src>`, no con
  `fetch`); que «Mikel» y «mikel» salgan como personas distintas (el PC resuelve por clave de nombre al ingerir y el estado emite
  el nombre canónico; el único hueco real eran las jornadas aún sin ingerir, ya recogido en el punto 10 de §9).
- **Rechazado con motivo:** quitar la suma diaria entre obras (es lo que detecta la doble anotación; dentro de una obra y ámbito la
  clave ya sustituye); quitar el aviso de nombre parecido (es solo un aviso y protege el ranking); bajar `notas` a 200 (sin ganancia).
- **Decisión tuya, no mía:** las propuestas A (corregir/anular con pantalla «Jornadas») y B (habituales) son lo que el revisor
  propone recortar de la v1. El modelo de datos admite la anulación y la sustitución igualmente; lo que se recorta sería solo la
  pantalla y la lista de habituales.
- **Resolución de Bixente (23/10/2026):** aprueba la especificación y las propuestas A, B, C y D tal como están (v1 completa).

## 15. Ajustes posteriores a la aprobación (23/10/2026)

Al diseñar los verificadores de P1 aparecieron huecos que no se podían dejar a interpretación del trabajador. Se cerraron sin cambiar
nada de lo aprobado: códigos nuevos `horario_invalido` y `nombre_invalido` (§6); acción `sin_cambios`, `avisos_lote` (`traza_no_escrita`),
errores de `fusionar` (incluido `conflicto_en_jornada`, que impide fusionar dos nombres que aparecen en la misma jornada y dejarían un
presente duplicado), firma de la API, orden de evaluación, regla de la suma diaria y de `nombre_parecido` y opciones de la CLI (§7b).

**Corrección tras P1 (23/10/2026):** la regla de `nombre_parecido` se escribió dos veces de forma distinta (el encargo comparaba nombres
cortos a distancia 1; el verificador exigía no avisar en ese caso). `gemini` y `agy` siguieron el encargo y fallaron 3 rondas por esa
contradicción mía; `codex:low` aplicó la regla de ≥ 3 letras en ambos nombres, que es la prudente. Es la que queda como oficial (§6 y §7b),
y la app (P3) debe usar la misma.

## 16. Cambios decididos por Bixente tras revisar P3 (24/10/2026)

Bixente vio las capturas de P3 (visto bueno) y respondió a las dudas del paso 01. Lo que cambia respecto a lo aprobado el 23/10:

1. **Horario propio por trabajador, con pantalla, en la v1** (antes D3 y §12: «solo en el modelo de datos, sin pantalla»). Ejemplo de Bixente: tres de Sagarde trabajan
   7,5 h el viernes y dos autónomos trabajan 9 h ese mismo viernes. **La app debe recordar el horario propio** de cada persona (una sola vez: «este trabaja 9 h los viernes»);
   desde entonces, al marcarlo con la X le sale su horario propio y no hay que tocar nada más.
2. **Cómo se cuenta:** para esa persona su horario propio ES su jornada normal: `extra = max(0, horas − horario propio de ese día)`; los 9 h de un autónomo son
   **9 normales y 0 extra**. El % de impacto no cambia (usa las horas totales); solo cambia el reparto normales/extra. «Se guarda lo medido»: un cambio posterior del horario propio no reescribe jornadas pasadas.
3. **Contrato (propuesta; CERRADO en §17 por el paso 01b, 24/10/2026):** el horario propio es **por obra y por día de la semana** (como ya está en `personal_obra.json.excepciones_horario`, por `id`).
   El lote `lote_personal` (§5.3) gana un campo opcional `excepciones_horario: { "<nombre>": { "lun": 9, … } }` con el **objeto completo** de la persona (solo los días que difieren; `{}` = quitar su
   horario propio); esquema cerrado como el resto (claves `lun…dom`, 0–24, máximo 2 decimales, nombre limpio). El PC resuelve el nombre a `id` por clave, valida y guarda; el estado (§5.4) ya lo emite por nombre.
   Hasta que el estado publicado lo traiga, la tablet lo recuerda en el aparato (como el horario de la obra).
4. **Cambiar el horario del día:** al cambiar el horario de la obra para el día que se está anotando, los presentes **sin horario propio** cuyas horas eran las del horario anterior pasan al nuevo.
   No se toca a quien tenga horario propio ni horas puestas a mano distintas. Si el día cambiado no es el de la fecha anotada, no se toca a nadie.
5. **Carga lenta (§9.9):** la app espera como máximo **4 s** a `personal_estado.js`; si no llega, abre con la copia guardada y lo dice.
6. **Se queda como está:** la tabla del informe en el móvil con letra pequeña (cabe entera sin deslizar); **no hay «Importar estado» en la v1** (§9.6 queda para más adelante).
7. **«Empezar de cero» pregunta antes de borrar** («¿Borrar lo que llevas a medias?», Sí / No, dentro de la página). Sigue borrando solo el borrador; las jornadas pendientes se conservan.
8. **Se dejan como están (Bixente, 24/10/2026):** el borrador viejo que podría pisar una jornada corregida en el PC (riesgo bajo, anotado en §13), y tres detalles menores: pendientes de una obra ya
   cerrada que no se pueden exportar desde la tablet, el contador de pendientes de todas las obras frente a «Exportar» de la obra elegida, y «Exportar» en la barra de pestañas.

## 17. Paso 01b: contrato cerrado del horario propio (24/10/2026)

Cierra la propuesta del punto 3 de §16. Lo decidido por Bixente está en §16; lo que sigue son las decisiones **de diseño** que tomó el paso 01b para que no quedara nada a interpretación (Bixente las ve en el informe del paso).

**Lote (§5.3).** `excepciones_horario` opcional, `{ "<nombre>": { "<día>": horas } }`. Esquema cerrado; cualquier incumplimiento rechaza el **lote entero** con el código nuevo `excepcion_invalida` (§6), igual que `horario_invalido`:
no es un diccionario; nombre vacío, de más de 60 caracteres, con caracteres de control o repetido por clave de nombre (`"Mikel"` y `" mikel "`); valor que no es diccionario; día distinto de `lun mar mie jue vie sab dom`; hora no numérica, booleana, < 0, > 24 o con más de 2 decimales.
`{}` como valor es válido y significa «quitar». Un lote puede traer **solo** `excepciones_horario` (con `jornadas: []`).

**Semántica en el PC (`ingerir_lote`).**
- Se aplica **después** de las jornadas y del `horario_semanal`, y **aunque alguna jornada del lote se rechace** (no forma parte de ninguna jornada; igual que el horario de la obra).
- El nombre se resuelve a `id` por clave de nombre (los fusionados, a su destino). El objeto de la persona **sustituye entero** al guardado; días guardados en el orden de la semana y personas por `id`, de modo que el mismo contenido da los mismos bytes.
- **Nombre que no existe:** con objeto no vacío se **da de alta** como un presente nuevo (avisos `nombre_parecido` y `alta_nueva` en `avisos_lote`; entra en `altas`). Con `{}` no hay nada que quitar: **no se da de alta**.
- Resultado: clave nueva `excepciones` = `[{nombre (limpio, como vino), id | None, accion: fijada | quitada | sin_cambios}]` en el orden del lote (siempre presente; `[]` si no hay campo o el lote se rechaza).
- **Reingerir el mismo lote no cambia ni un byte** (`9` y `9.0` son lo mismo; otro orden de días también).
- **Fusiones:** al fijar o quitar el horario de una persona se borran también los restos de ids que se fusionaron en ella (si no, un horario heredado «resucitaría» al quitarlo). `fusionar` **se niega** (`conflicto_en_horario_propio`, sin escribir nada) si, en alguna obra, origen y destino tienen
  horario propio efectivo **distinto** (efectivo = el de su id; si no, el del id menor de los fusionados en él). Si solo uno lo tiene, o son iguales, se fusiona y el destino lo hereda. En el estado, si varios ids acaban siendo la misma persona, **manda el del destino**; si no tiene, el del id menor.
- Traza: una línea por persona cambiada, `accion` `horario_propio` / `horario_propio_quitado`, con `id`, `ambito: null`, `fecha: null`.
- `comprobar`: avisa de `excepciones_horario` que no sea diccionario, de ids que no existen en el catálogo y de valores fuera del esquema.
- CLI: imprime `RECHAZADO lote <código>` (antes un lote rechazado entero salía en silencio con código 2) y `HORARIO PROPIO <nombre> <acción>`.

**Semántica en la app (P3).**
- Horario de una persona un día = su horario propio de ese día de la semana si lo tiene; si no, el de la obra. `0` = sin horario (`¿horas?`). `extra = max(0, horas − su horario de ese día)`.
- «Tiene horario propio un día» significa que su objeto trae **ese día**: quien solo lo tiene el viernes sigue el horario de la obra el lunes.
- Se recuerda en el aparato (`sgd_personal_excepciones`, por obra) hasta que el estado publicado trae lo mismo; entonces se olvida solo. Una baja de un horario publicado se recuerda como `{}`. Memoria dañada: se ignora la persona dañada entera y la app arranca.
- Al fijar/quitar el horario propio de alguien **marcado**, sus horas pasan al nuevo horario si seguían al anterior; las puestas a mano no se tocan. Las jornadas ya guardadas **nunca** se reescriben.
- Al cambiar el horario de la obra del día anotado (§16.4): se mueven los presentes con horas iguales al horario anterior **y sin horario propio ese día**; los demás no.
- Espera máxima de 4 s a `personal_estado.js` si hay copia guardada (si no hay copia, se sigue esperando); el origen dice `Usando la copia guardada en este aparato · el estado publicado tarda en llegar`.
- «Empezar de cero»: pregunta dentro de la página (`#confirmar-reset`), sin ventanas del navegador.
