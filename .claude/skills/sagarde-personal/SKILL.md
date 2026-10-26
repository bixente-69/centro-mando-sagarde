---
name: sagarde-personal
description: Operaciones sobre la BASE de trabajadores de Sagarde (Personal en obra) — ver quién hay en la base (pestaña «Base de trabajadores» del ranking), corregir un nombre, juntar dos fichas de la misma persona, separar la empresa que va dentro de un nombre y entender la suma por empresa. Siempre con vista previa y antes/después. La ENTRADA de los controles horarios de la tablet no es de esta skill: es otra clase de «hoja» y va por sagarde-actualizar-obra. Usar cuando Bixente hable de la base de trabajadores, de nombres duplicados o mal escritos, de juntar o fusionar personas, de las empresas de los trabajadores o del ranking de personal.
---

# Personal en obra: la base de trabajadores

La tablet (`generador_personal.html`) **solo aporta datos**: anota quién trabaja cada día en cada obra, viviendas y garajes
por separado, y descarga un `CONTROL HORARIO`. Ese fichero entra como entra una revisión (se deja en `REVISIONES` y se dice
«actualiza la obra»): **cómo entra está en la skill `sagarde-actualizar-obra`**, no aquí. El PC guarda y suma; la pestaña
**Personal** del panel, la sección del **Informe de obra** y el **ranking de Sagarde** (`personal_sagarde.html`, con su
pestaña **Base de trabajadores**) lo enseñan. Desde el portal se ve todo; los cambios se piden por el camino del entorno.

## Reglas fijas (decididas por Bixente)

- El trabajador se llama **«nombre»** (nunca «alias» ni «mote»). Texto libre, 1–60 caracteres.
- **Ni DNI, ni teléfono, ni correo** en ningún fichero de personal (se publican). El auditor lo mira.
- Jornada base **7,5 h de lunes a viernes**; sábado y domingo no tienen horario (todo es extra). A Bixente las horas extra
  «no le importan»: lo que cuenta es el total de horas y de días.
- Un dato que falta **no es cero**: un periodo sin jornadas dice «sin jornadas».
- Los datos **se publican** (repo público), pero **nada se publica solo**: lo hace `Actualizar_Sagarde.bat` y solo cuando
  Bixente lo pide.
- Todo lo que lee Bixente va **en lenguaje de electricista**: sin palabras de programador ni códigos internos (la lista exacta
  la vigila `tests/test_lenguaje_electricista.py`, que también revisa la pestaña «Base de trabajadores»).

## Dónde está cada cosa

Todo en `SAGARDE OBRAS ABIERTAS/` salvo lo indicado.

| Qué | Ruta |
|---|---|
| Datos de una obra (jornadas, horarios) | `<carpeta obra>/INFORME SAGARDE IA/personal_obra.json` |
| Traza de lo aplicado (se añade, no se edita; lleva el SHA256 de cada control horario) | `<carpeta obra>/INFORME SAGARDE IA/personal_jornadas.jsonl` |
| La base: personas (ids `T0001`…), empresas, nombres anteriores y fichas juntadas | `_SISTEMA INFORME SAGARDE IA/personal_catalogo.json` |
| Lo que leen la tablet y el ranking | `_SISTEMA INFORME SAGARDE IA/personal_estado.js` (lo genera el motor) |
| Datos / integración | `_SISTEMA INFORME SAGARDE IA/personal_obra.py`, `personal_integracion.py` |
| Cálculo (una sola implementación) | `_SISTEMA INFORME SAGARDE IA/personal_calculo.js` |
| Pestaña e informe de cada obra | `_SISTEMA INFORME SAGARDE IA/panel_personal.py` |
| Ranking y «Base de trabajadores» | `_SISTEMA INFORME SAGARDE IA/personal_sagarde.html` (la base se abre también con `#base`) |
| Lector de los controles horarios | `_SISTEMA INFORME SAGARDE IA/lector_control_horario.py` (ver `sagarde-actualizar-obra`) |

Las obras archivadas conservan su `personal_obra.json` (viaja con la carpeta) y el ranking las sigue contando, marcadas
`cerrada`. **Nunca borrar ese fichero al cerrar una obra** (ver `sagarde-cerrar-obra`).

## Ver la base: pestaña «Base de trabajadores»

En el ranking de Sagarde (`personal_sagarde.html`), segunda pestaña. Una fila por persona **de la base, haya trabajado ya o
no**: nombre y empresa, las obras donde ha trabajado (con sus días y horas), días y horas en total, la fecha de su última
jornada (y la obra) y los nombres de antes («Antes se llamaba…», «Se juntó con otra ficha…»). Hay buscador (nombre, empresa,
nombres de antes u obra, sin tildes ni mayúsculas) y tres órdenes (nombre, horas, última jornada). Es de **solo lectura**: ni
guarda ni cambia nada.

Las cifras salen de las mismas jornadas y con las mismas reglas que el ranking (`baseTrabajadores` en `personal_calculo.js`);
del estado publicado solo sale lo que no se puede recalcular: la empresa y el historial de nombres. Avisos que puede dar,
cada uno con su nombre: jornadas que no se cuentan (sin horas o con datos no válidos), fichas sin nombre o repetidas, un
historial que no se pudo leer, alguien con jornadas que no figura en la base, o que el fichero no trae la lista de la base.
**Un aviso aquí es un dato roto de verdad: no se ignora.**

## Cambiar algo de la base (siempre: vista previa → antes/después)

Regla común: primero la vista previa (no guarda nada), se la cuento a Bixente en llano, y si cambia nombres o cifras espero
su «sí» antes de aplicar. Después compruebo el **antes/después**: las **horas y los días totales no deben cambiar** al
corregir, juntar o separar (solo cambian nombres, empresas y el historial; al juntar baja en una el número de personas); se
mira en la pestaña «Base de trabajadores» antes y después o con `personal_obra.totales_control`.

### Corregir un nombre
Desde la tablet el cambio de nombre (lápiz ✎) viaja dentro del control horario y entra con «actualiza la obra». Para una
corrección puntual desde el PC (el nombre cambia en todas las obras):

```bash
py -3.11 personal_obra.py renombrar "Mikell" "Mikel"            # vista previa
py -3.11 personal_obra.py renombrar T0002 "Mikel" --escribir
```
Si el nombre nuevo ya es de otra persona no se cambia y dice que hay que **juntarlas**. El nombre antiguo queda como «nombre
anterior»: un control horario viejo que todavía lo traiga cae en la misma persona.

### Juntar dos fichas de la misma persona (fusionar)
Mikel / Mikell son la misma persona: se funde el **origen** en el **destino** por sus ids (`personal_catalogo.json`). Siempre
simular primero:

```bash
py -3.11 personal_obra.py fusionar T0002 T0001            # simulación
py -3.11 personal_obra.py fusionar T0002 T0001 --escribir
py -3.11 personal_integracion.py exportar-estado --escribir
```
Se niega con `conflicto_en_jornada` (los dos figuran el mismo día en la misma jornada, también en obras archivadas: sumarían
dos veces), `conflicto_en_horario_propio` (tienen horarios propios distintos: quitar uno antes) o `origen_ya_fusionado` /
`destino_fusionado`. Después, regenerar los paneles de las obras donde aparecían (`regenerar_obra.py <id>`). La ficha
juntada deja de salir como persona y su nombre queda en el historial de la persona que sigue («Se juntó con otra ficha»).

### Empresa de cada persona
Cada persona tiene **una** empresa, o «Sin empresa» (no se da por hecho que sea de Sagarde: puede ser autónomo). Un autónomo es
una empresa que acaba en «@AUT» («Javi @AUT»). La tablet la apunta (campo Empresa al crear, lápiz ✎ y «Nombre, Empresa» en
«Añadir varios nombres») y viaja en `empresas` dentro del control horario; el PC la aplica después de los cambios de nombre y
de los nombres nuevos y antes de las jornadas. Una persona, una empresa, para todas sus obras. Se compara sin tildes ni
mayúsculas y se guarda con la grafía de la primera vez.

Los nombres que ya llevan la empresa dentro («Alejo (Manueles)», «Javi @ CATERSYSTEM») se separan con vista previa; **solo se
aplica con el «sí» de Bixente** (renombra a toda la persona, el nombre viejo queda como anterior, y no toca ninguna jornada):

```bash
py -3.11 personal_obra.py separar-empresas              # vista previa: no guarda nada
py -3.11 personal_obra.py separar-empresas --aplicar    # solo tras su «sí»
```
Lo dudoso (nombre que quedaría vacío, nombre que ya existe, dos que quedarían iguales, un sufijo «@AUT», alguien que ya tiene
otra empresa) **no se toca y se enseña**; para juntar dos personas, `fusionar`.

## La suma por empresa

Sale sola, sin ningún paso aparte, en los **cuatro sitios**: pestaña Personal de cada obra, sección Personal del Informe de
obra, ranking de Sagarde (suma de todas las obras) e Informe de la tablet. Es un bloque «Por empresa» (personas, días de
trabajo de cada persona sumados, horas y % de impacto; más horas primero y «Sin empresa» siempre al final) y la empresa en
pequeño debajo de cada nombre. Cada autónomo («X @AUT») es una línea más y debajo del total va «Total autónomos (@AUT)», que ya
está contado arriba y no se suma otra vez. Una obra sin empresas puestas solo enseña la línea «Sin empresa». El cálculo y el
bloque se escriben UNA sola vez, en `personal_calculo.js` (`agregarPorEmpresa` y `htmlPorEmpresa`): no lo copies en otro sitio.
Si en un informe sale el aviso «Hay una persona con más de una empresa», es un dato incoherente (una persona, una empresa): se
corrige con `poner_empresa`.

## Publicar: la guarda del `.bat`

El paso 0 de `Actualizar_Sagarde.bat` llama al auditor. Si los datos de personal tienen un error (esquema roto, un
DNI/teléfono/correo, falta un fichero, el cálculo de pantalla no cuadra con el de Python), el auditor sale con código **3** y el
`.bat` **se detiene sin publicar nada**. Se corrige lo que diga el recuadro `[X]` y se vuelve a lanzar. Comprobarlo a mano:
`py -3.11 personal_integracion.py auditar`.

## Qué NO hacer

- Editar a mano `personal_obra.json`, el catálogo o la traza (el esquema es cerrado; los cambios van por «actualiza la obra»,
  `fusionar`, `renombrar` o `separar-empresas`). Un `.xlsx`/JSON editado a mano ya rompió una obra entera.
- Lanzar `Actualizar_Sagarde.bat` sin que Bixente lo pida (hace `git add -A` y publica en `main`).
- Pasar datos reales de personal a una IA gratuita o a un subagente: solo datos inventados.
- Usar `personal_obra.py exportar-estado --obras …` en el entorno real (ese modo es para pruebas: no pone los nombres de obra
  ni marca las cerradas).
- Montar un circuito aparte para la tablet (carpeta, `.bat`, alta manual de obras): la tablet solo aporta un fichero y el
  generador de revisiones es el modelo a copiar.
- Dar por probada la app en un iPad/iPhone: solo se ha probado en Chromium (Playwright).

## Pruebas

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```
Lo de personal: `test_personal_obra` (+ `_08a`), `test_personal_empresas_08c2a`, `test_lector_control_horario`,
`test_controles_horarios_08b`, `test_personal_integracion` (+ `_08a`), `test_publicacion_personal`, `test_personal_calculo` y
`test_empresas_suma_08c2b` y `test_base_trabajadores_08e` (necesitan `node`), `test_generador_personal` y
`test_lenguaje_electricista` (necesitan Playwright; ≈ 2–7 min; `SAGARDE_SIN_NAVEGADOR=1` los salta a propósito) y
`test_panel_personal`. Las verificaciones de navegador de la pestaña, el informe y el ranking siguen en la carpeta de trabajo
del proyecto (`PROYECTO PERSONAL EN OBRA/staging/_verificadores/`: `verificar_p4.py`, `verificar_p5.py`, `verificar_p5b.py`).
