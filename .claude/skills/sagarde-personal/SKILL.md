---
name: sagarde-personal
description: Personal en obra de Sagarde. Cómo entra un CONTROL HORARIO de la tablet (se deja en REVISIONES y se dice «actualiza la obra»), entender sus avisos (nombre parecido, más de 12 h, fecha futura, jornada que sustituye…), corregir un nombre, fusionar nombres duplicados y actualizar el estado de la tablet y el ranking. Usar cuando Bixente hable de un control horario, de quién trabajó un día, de horas, del ranking de personal o de la pestaña Personal.
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
| Lector de los controles horarios (detectar, vista previa, aplicar) | `_SISTEMA INFORME SAGARDE IA/lector_control_horario.py` |
| Dónde los deja Bixente | `<carpeta obra>/REVISIONES/CONTROL HORARIO <OBRA> <DDMMAAAA>.json` (**no se publican**) |

Las obras archivadas conservan su `personal_obra.json` (viaja con la carpeta) y el ranking las
sigue contando, marcadas `cerrada`. **Nunca borrar ese fichero al cerrar una obra.**

## Cómo entra un control horario (desde el 25/10/2026: igual que una revisión)

La tablet descarga `CONTROL HORARIO <OBRA> <DDMMAAAA>.json` (por dentro sigue siendo el «lote» de siempre).
Bixente lo deja **a mano en `<carpeta obra>/REVISIONES/`** y dice **«actualiza la obra X»**. No hay `.bat`
ni comando aparte ni alta manual de la obra: **el primer fichero crea el `personal_obra.json` de la obra**.

1. `py -3.11 _SISTEMA/MOTOR/scripts/actualizar_obra.py <id>` (vista previa; no escribe) enseña en llano lo que
   trae cada fichero: jornadas, personas nuevas, avisos y horas antes/después. Sin controles dice
   «No hay controles horarios nuevos».
2. `… --escribir` los aplica antes de regenerar la obra; el informe lleva la sección **H) CONTROL HORARIO**.
3. `Actualizar_Sagarde.bat` (solo cuando él lo pida) también aplica los controles **limpios** al generar cada
   obra; los dudosos o inválidos no se aplican y salen como `[AVISO PERSONAL]` con el nombre del fichero. El
   auditor del paso 0 avisa de cada control sin aplicar.

Cada fichero queda en una de cuatro situaciones: **ya aplicado** (su SHA256 consta en
`personal_jornadas.jsonl`; una copia con otro nombre cuenta igual), **listo**, **hay que mirarlo** (no se
aplica; código 3, y se libera con `--aceptar-controles N`) o **no vale** (no se aplica; código 2). Los
ficheros se aplican en orden de la fecha del nombre; **la última manda**.

| Lo que sale en pantalla | Qué es |
|---|---|
| «Nombre nuevo: «X» no estaba en la base; se añade.» | Informativo. Si es una errata de otro nombre, ver el siguiente. |
| «Se parecen: «A» y «B». ¿Es la misma persona?» | **Hay que mirarlo.** Si lo es, **fusionar** después de guardar. |
| «X suma más de 12 horas ese día entre todas las obras.» | **Hay que mirarlo**; preguntar a Bixente. |
| «La jornada es de una fecha que aún no ha llegado (dd/mm): ¿es una errata?» | **Hay que mirarlo.** |
| «Ya había una jornada de ese día en esa obra: la nueva la sustituye.» | **Hay que mirarlo** (es una corrección; al aceptarla manda la nueva). |
| «No se ha cambiado «A»: «B» ya es otra persona de la base…» | **Hay que mirarlo**; juntarlas con `fusionar`. |
| ««A» es un nombre antiguo de «B»: se ha tomado como la misma persona.» | Informativo (un fichero viejo con el nombre de antes). |

**No vale** (no se aplica y se dice): fichero ilegible o que no es un control horario; la obra que lleva
dentro no es la de la carpeta donde está (no se mezclan obras); un nombre que parece DNI, teléfono o correo;
datos de personal de la obra ilegibles. Una **jornada** inválida suelta (horas fuera de 0–24, más de 24 h
entre todas las obras, una persona dos veces…) se rechaza y **las demás entran**.

## Corregir un nombre

Desde la tablet el cambio de nombre viaja dentro del control horario. Para una corrección puntual desde el PC
(siempre vista previa primero; no hace falta tocar nada más, el nombre cambia en todas las obras):

```bash
py -3.11 personal_obra.py renombrar "Mikell" "Mikel"            # vista previa
py -3.11 personal_obra.py renombrar T0002 "Mikel" --escribir
```
Si el nombre nuevo ya es de otra persona no se cambia y dice que hay que **fusionar**. El nombre antiguo
queda como «nombre anterior»: un fichero viejo que todavía lo traiga cae en la misma persona.

## Empresa de cada persona (desde el 08c2a)

Cada persona tiene **una** empresa, o «Sin empresa» (no se da por hecho que sea de Sagarde: puede ser autónomo). Un
autónomo es una empresa que acaba en «@AUT» («Javi @AUT»). La tablet la apunta (campo Empresa al crear, lápiz ✎ y
«Nombre, Empresa» en «Añadir varios nombres») y viaja en `empresas` dentro del control horario; el PC la aplica
después de los cambios de nombre y de los nombres nuevos y antes de las jornadas. Una persona, una empresa, para
todas sus obras. Se compara sin tildes ni mayúsculas y se guarda con la grafía de la primera vez.

Los nombres que ya llevan la empresa dentro («Alejo (Manueles)», «Javi @ CATERSYSTEM») se separan con vista
previa; **solo se aplica con el «sí» de Bixente** (renombra a toda la persona, el nombre viejo queda como anterior,
y no toca ninguna jornada):

```bash
py -3.11 personal_obra.py separar-empresas              # vista previa: no guarda nada
py -3.11 personal_obra.py separar-empresas --aplicar    # solo tras su «sí»
```
Lo dudoso (nombre que quedaría vacío, nombre que ya existe, dos que quedarían iguales, un sufijo «@AUT», alguien que ya
tiene otra empresa) **no se toca y se enseña**; para juntar dos personas, `fusionar`.

### La suma por empresa (desde el 08c2b)

Sale sola, sin ningún paso aparte, en los **cuatro sitios**: pestaña Personal de cada obra, sección Personal del
Informe de obra, ranking de Sagarde (suma de todas las obras) e Informe de la tablet. Es un bloque «Por empresa»
(personas, días de trabajo de cada persona sumados, horas y % de impacto; más horas primero y «Sin empresa» siempre al
final) y la empresa en pequeño debajo de cada nombre. Cada autónomo («X @AUT») es una línea más y debajo del total va
«Total autónomos (@AUT)», que ya está contado arriba y no se suma otra vez. Una obra sin empresas puestas solo enseña la
línea «Sin empresa». El cálculo y el bloque se escriben UNA sola vez, en `personal_calculo.js`
(`agregarPorEmpresa` y `htmlPorEmpresa`): no lo copies en otro sitio. Si en un informe sale el aviso «Hay una persona
con más de una empresa», es un dato incoherente (una persona, una empresa): se corrige con `poner_empresa`.

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
  cambios van por «actualiza la obra», `fusionar` o `renombrar`). Un `.xlsx`/JSON editado a mano ya rompió una obra entera.
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
