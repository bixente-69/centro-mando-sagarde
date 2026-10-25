---
name: sagarde-personal
description: Personal en obra de Sagarde. Ingerir las jornadas que exporta la tablet (lote_personal_*.json), dar de alta una obra en Personal, fusionar nombres duplicados, entender los avisos (alta_nueva, nombre_parecido, suma_diaria_alta…) y actualizar el estado de la tablet y el ranking. Usar cuando Bixente pase un fichero lote_personal, hable de quién trabajó un día, de horas extra, del ranking de personal o de la pestaña Personal.
---

# Personal en obra (jornadas, trabajadores, ranking)

La tablet (`generador_personal.html`) anota quién trabaja cada día en cada obra, viviendas y
garajes por separado. El PC guarda y suma; la pestaña **Personal** del panel, la sección del
**Informe de obra** y el **ranking de Sagarde** (`personal_sagarde.html`) lo enseñan.

## Reglas fijas (decididas por Bixente)

- El trabajador se llama **«nombre»** (nunca «alias» ni «mote»). Texto libre, 1–60 caracteres.
- **Ni DNI, ni teléfono, ni correo** en ningún fichero de personal (se publican). El auditor lo mira.
- Jornada base **7,5 h de lunes a viernes**; sábado y domingo no tienen horario (todo es extra).
- Un dato que falta **no es cero**: un periodo sin jornadas dice «sin jornadas».
- Los datos **se publican** (repo público), pero **nada se publica solo**: lo hace
  `Actualizar_Sagarde.bat` y solo cuando Bixente lo pide.

## Dónde está cada cosa

Todo en `SAGARDE OBRAS ABIERTAS/` salvo lo indicado.

| Qué | Ruta |
|---|---|
| Datos de una obra (jornadas, horarios) | `<carpeta obra>/INFORME SAGARDE IA/personal_obra.json` |
| Traza de ingestas (se añade, no se edita) | `<carpeta obra>/INFORME SAGARDE IA/personal_jornadas.jsonl` |
| Catálogo de trabajadores (ids `T0001`…) | `_SISTEMA INFORME SAGARDE IA/personal_catalogo.json` |
| Estado para la tablet y el ranking | `_SISTEMA INFORME SAGARDE IA/personal_estado.js` (lo genera el motor) |
| Módulo de datos / integración | `_SISTEMA INFORME SAGARDE IA/personal_obra.py`, `personal_integracion.py` |
| Cálculo (una sola implementación) | `_SISTEMA INFORME SAGARDE IA/personal_calculo.js` |
| Pestaña e informe | `_SISTEMA INFORME SAGARDE IA/panel_personal.py` |
| Para Bixente (arrastrar el lote) | `_SISTEMA INFORME SAGARDE IA/Ingerir_Personal.bat` |

Las obras archivadas conservan su `personal_obra.json` (viaja con la carpeta) y el ranking las
sigue contando, marcadas `cerrada`. **Nunca borrar ese fichero al cerrar una obra.**

## Primera vez en una obra: darla de alta en Personal

La tablet solo ofrece las obras que figuran en `personal_estado.js`, y una obra figura si ya tiene
su `personal_obra.json`. Sin este paso no se puede anotar la primera jornada:

```bash
py -3.11 "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/personal_integracion.py" iniciar-obra olabeaga --escribir
```
(sin `--escribir` solo simula; si ya existe no lo toca). El estado se actualiza solo la siguiente
vez que se genera o se ingiere; para tenerlo ya: `… personal_integracion.py exportar-estado --escribir`.

## Ingerir una jornada

1. La tablet exporta `lote_personal_<obra>.json`. Bixente lo **arrastra encima de
   `Ingerir_Personal.bat`** (o: `py -3.11 personal_integracion.py ingerir <fichero>`).
2. Hace una **simulación** y enseña los avisos. Escribe **S** + Intro para guardar; cualquier otra
   cosa cancela sin tocar nada.
3. Guarda, actualiza `personal_estado.js` y **regenera solo el panel de esa obra** (si el lote no
   trae datos nuevos, no regenera). **No publica.**

| Aviso | Qué significa y qué hacer |
|---|---|
| `alta_nueva <nombre>` | El nombre no estaba en la base y se da de alta. Si es una errata de otro, ver el siguiente. |
| `nombre_parecido A ~ B` | Parecido a uno que ya existe. Si es la misma persona, **fusionar** después de guardar. |
| `suma_diaria_alta` | Alguien suma más de 12 h ese día entre todas las obras y ámbitos. Preguntar a Bixente. |
| `fecha_futura <fecha>` | La jornada es posterior a hoy: casi seguro una errata de fecha. |
| `reemplazo` | La jornada ya existía (misma obra, ámbito y fecha) y se sustituye: es una corrección. |
| `traza_no_escrita` | Lo guardado está bien; solo falló añadir la línea al `.jsonl`. |

Se **rechaza una jornada** (las demás del lote entran) por `suma_diaria_invalida` (> 24 h por
persona y día), `horas_invalidas`, `presente_duplicado`, `nombre_invalido`, `sin_presentes` o
`jornada_repetida_en_lote`. Se **rechaza el lote entero** por `obra_invalida` (no es una obra
abierta del registro), `tipo_desconocido`, `version_desconocida`, `horario_invalido` o
`excepcion_invalida`: la consola lo dice (`RECHAZADO lote <código>`) y no se escribe nada.

## Fusionar nombres duplicados

Mikel / Mikell son la misma persona: se funde el **origen** en el **destino** por sus ids
(`personal_catalogo.json`). Siempre simular primero:

```bash
py -3.11 personal_obra.py fusionar T0002 T0001            # simulación
py -3.11 personal_obra.py fusionar T0002 T0001 --escribir
py -3.11 personal_integracion.py exportar-estado --escribir
```
Se niega con `conflicto_en_jornada` (los dos figuran el mismo día en la misma jornada, también en
obras archivadas: sumarían dos veces), `conflicto_en_horario_propio` (tienen horarios propios
distintos: quitar uno antes) o `origen_ya_fusionado` / `destino_fusionado`. Después, regenerar los
paneles de las obras donde aparecían (`regenerar_obra.py <id>`).

## Publicar: la guarda del `.bat`

El paso 0 de `Actualizar_Sagarde.bat` llama al auditor. Si los datos de personal tienen un error
(esquema roto, un DNI/teléfono/correo, falta un fichero, el cálculo de pantalla no cuadra con el de
Python), el auditor sale con código **3** y el `.bat` **se detiene sin publicar nada**. Se corrige
lo que diga el recuadro `[X]` y se vuelve a lanzar. Comprobarlo a mano:
`py -3.11 personal_integracion.py auditar`.

## Qué NO hacer

- Editar a mano `personal_obra.json`, el catálogo o la traza (el esquema es cerrado; los
  cambios van por `ingerir`/`fusionar`). Un `.xlsx`/JSON editado a mano ya rompió una obra entera.
- Lanzar `Actualizar_Sagarde.bat` sin que Bixente lo pida (hace `git add -A` y publica en `main`).
- Pasar datos reales de personal a una IA gratuita o a un subagente: solo datos inventados.
- Usar `personal_obra.py exportar-estado --obras …` en el entorno real (ese modo es para pruebas:
  no pone los nombres de obra ni marca las cerradas).
- Dar por probada la app en un iPad/iPhone: solo se ha probado en Chromium (Playwright).

## Pruebas

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```
Lo de personal: `test_personal_obra`, `test_personal_integracion`, `test_publicacion_personal`,
`test_personal_calculo` (necesita `node`), `test_generador_personal` (necesita Playwright;
≈ 2–7 min; `SAGARDE_SIN_NAVEGADOR=1` lo salta a propósito) y `test_panel_personal`. Las verificaciones de
navegador de la pestaña, el informe y el ranking siguen en la carpeta de trabajo del proyecto
(`PROYECTO PERSONAL EN OBRA/staging/_verificadores/`).
