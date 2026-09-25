# Fase 4 — Wizard de garaje en `generador_revisiones.html` (fichero de trabajo)

Diseño de Claude para que Codex lo implemente y pruebe. Es la fase más
grande del plan: añade un segundo modo completo al generador real
(1459 líneas hoy, de las cuales 3 son el logo en base64 — casi todo lo
demás es JS de verdad).

## Punto de partida: ya existe un prototipo validado

`_SISTEMA/scratch/garaje-wizard-demo.html` es un prototipo interactivo
completo del asistente de garaje, construido y refinado en ~15 rondas con
Bixente revisando cada versión (ver §9 del diseño,
`2026-09-24-ampliacion-garajes-design.md`). **No es un boceto en papel: es
UX y lógica ya probadas y aceptadas.** La tarea de esta fase es *portar*
ese comportamiento al fichero real, adaptado a sus convenciones exactas
(`uid()`, `escHtml()`, el objeto `S`, `showScreen`/`goStep`, las clases
CSS `PROP_LBL`/`tajo-prop`/`td-st`...) — no es diseñar la UX desde cero.
**Nunca copiar el HTML/CSS del prototipo literal**: el prototipo es JS de
demostración con datos de ejemplo, desconectado del backend; el real tiene
que seguir generando hojas que los adaptadores/ficha_garajes.py puedan
leer, con las claves y el catálogo reales de la Fase 1.

## Arquitectura de la integración — mínimo footprint sobre lo existente

Leído el fichero real completo. Decisión clave: **los paneles HTML de los
pasos 2, 3 y 4 (`step-2`, `step-3`, `step-4`) NO se duplican.** Sus
funciones de render ya existentes (`initStructure`, `renderTajos`,
`renderSummary`) pasan a mirar `S.modo` y, si es `'garaje'`, delegan en
una función nueva que rellena el MISMO contenedor HTML
(`portal-structures`, `tj-sel`, `gen-summary`) con contenido de garaje en
vez de vivienda. Solo el **paso 1** necesita HTML nuevo de verdad: un
selector de modo y un bloque de "número de garajes" paralelo al ya
existente "número de bloques".

**Consecuencia importante:** cuando `S.modo==='vivienda'` (el valor por
defecto, y el único que existe hoy), **absolutamente ningún camino de
código cambia** — es la misma guarda de "no tocar vivienda" que ya
funcionó en la Fase 3.

### Estado nuevo en `S`

```js
S.modo = 'vivienda';      // 'vivienda' | 'garaje' — default preserva TODO el comportamiento actual
S.garajes = [];           // lista de garajes, solo relevante si modo==='garaje'
S.selGaraje = new Set();  // tajos de garaje seleccionados (aparte de S.sel, que sigue siendo solo de vivienda)
```

`S.garajes[i]` = `{id, nombre, plantas: [{id, nombre, zonas: [{id, nombre, tipo}]}]}`
— tipo es uno de `vial|trastero|escalera|rellano|cuarto_tecnico|cuarto_ligero`
(§3.4/§5.9 del diseño). Mismo patrón de `uid()` que ya usan
`makeBlock`/`makePortal`/`makeFloor`.

### Catálogo de garaje: `CAT_GARAJE`

**Traducir literalmente los 42 tajos ya reales de
`reglas/CATALOGO_TAJOS.json`** (Fase 1, ya cerrada) a la forma compacta
que usa `CAT` aquí: `{id, name, g, p, a}` donde `g`=`fase`, `p`=primera
letra de `propiedad` (`p`ropio/`e`xterno/`c`oordinacion, igual que ya
hace `CAT` con `PROP_LBL={p:'SGD',e:'EXT',c:'COO'}`), `a`=`'z'` siempre
(todos los tajos de garaje son `ambito: zona_comun`, decisión ya tomada
en la Fase 1 — no hace falta el resto de letras `v`/`d`).

**A diferencia de `CAT`, no hace falta un `BASE_SOURCE_ID_GARAJE`**: los
42 tajos de garaje ya nacieron con id largo y canónico
(`garaje_tubeado_vial`, no un código corto tipo `tube-viv`) porque no
arrastran décadas de abreviaturas en papel como vivienda. El id de
`CAT_GARAJE` y el id real del catálogo son el mismo — una simplificación
real, no un descuido.

## Paso 1 — Obra (HTML nuevo, el único paso que lo necesita)

Antes del campo "Obra ya instalada con portal informático", un selector
de modo:

```html
<div class="field">
  <label class="fl">Tipo de revisión</label>
  <div class="modo-toggle">
    <button type="button" class="modo-btn active" data-modo="vivienda" onclick="setModo('vivienda')">🏠 Viviendas</button>
    <button type="button" class="modo-btn" data-modo="garaje" onclick="setModo('garaje')">🅿️ Garajes</button>
  </div>
</div>
```

(Usar la clase de botón que ya exista más parecida — mirar `.btn-sec`/
`.btn-pri`/`.wiz-step` en `ESTILOS` antes de inventar una clase CSS nueva;
si hace falta una regla nueva, que sea mínima y coherente con las
existentes — colores/tipografía ya definidos como variables CSS en
`<style>`, no colores sueltos.)

`setModo(modo)` cambia `S.modo`, y **si la obra elegida en el desplegable
de "instalada" ya tiene las dos estructuras** (necesitaría que
`window.SAGARDE_OBRAS_REVISION` trajera datos de garaje — hoy no los
trae, ninguna obra real tiene `ficha_garajes.json` todavía, así que en la
práctica esto no se puede dar aún, pero el código debe dejar el hueco:
comprobar `source.tiene_garaje` o similar sin asumir que existe) avisa
antes de continuar (§3.5 del diseño, paso 1). Con los datos de hoy, esto
es simplemente: el toggle cambia de modo y ya.

Bajo el campo "Número de bloques" (que pasa a mostrarse solo si
`S.modo==='vivienda'`), un campo paralelo visible solo en modo garaje:

```html
<div class="field w2" id="f-ngarajes-wrap" style="display:none">
  <label class="fl">Número de garajes</label>
  <input type="number" id="f-ngarajes" min="1" max="12" value="1" onchange="rebuildGarajes(+this.value)">
  <div class="hint">Mungia, por ejemplo, tiene 2 — uno por bloque. Después se nombran y se les añaden plantas y zonas.</div>
</div>
```

`rebuildGarajes(n)` — calco exacto de `rebuildBloques(n)` con
`makeGaraje` en vez de `makeBlock`.

## Paso 2 — Estructura (delega en `renderGarajeStructures()`)

`initStructure()` pasa a ser:
```js
function initStructure(){
  if(S.modo==='garaje') renderGarajeStructures();
  else renderPortalStructures();
}
```

`renderGarajeStructures()` puebla `#portal-structures` (mismo contenedor)
con, por cada garaje de `S.garajes`, sus plantas y — por planta — las DOS
mecánicas de §3.4, portadas del prototipo:

- **Lista de comprobación** (existe/no existe, sin contar cuántas):
  Escalera, Rellano/Zona común, Cuarto técnico (con su función:
  Centralización, RITI, achique, aerotermia, sala de calderas...), Cuarto
  de instalaciones generales, Cuarto ligero (Basuras/Bicicletas).
- **Zonas por conteo, como viviendas**: se pide un número y se generan
  editables una a una — Viales/alumbrado de parcelas, Trasteros.

Mismo patrón de funciones que vivienda tiene para plantas/viviendas
(`rebuildPlantas`/`addViv`/`rmViv`/`setViv`), adaptado a garajes/plantas/
zonas: `rebuildGarajePlantas`, `addZona`, `rmZona`, `setZona`, etc. — el
prototipo ya tiene el equivalente funcional completo, portar su lógica,
no reinventarla.

## Paso 3 — Tajos (delega en `renderTajosGaraje()`)

`renderTajos()` pasa a ser:
```js
function renderTajos(){
  if(S.modo==='garaje') renderTajosGaraje();
  else renderTajosVivienda();  // el cuerpo actual de renderTajos, renombrado
}
```

`renderTajosGaraje()` es un calco casi directo de la vivienda usando
`CAT_GARAJE`/`S.selGaraje` en vez de `CAT`/`S.sel`, agrupado por fase
igual que ya hace vivienda. **Es una selección plana** (qué tajos aplican
a la obra en general), no por tipo de zona — el filtrado por tipo de zona
solo entra en juego en el paso 4, al construir la hoja (§5.9 del diseño:
los perfiles por tipo de zona son de presentación, no de esta selección).

## Paso 4 — Generar (delega en `generateGarajeHTML()`)

La pieza más grande y más distinta de vivienda. `renderSummary()` se
ramifica igual que las anteriores. La función de generación de hoja
(`generateGarajeHTML()`, paralela a `generateHTML()`) implementa el
**reparto de hoja por tipo de zona** (§6.4 del diseño, ya validado en el
prototipo):

- **Zonas de conteo uniforme** (viales, trasteros y, por extensión,
  escalera/rellano): tabla ancha, igual patrón que vivienda —
  columnas=zonas, filas=tajos del perfil de esa zona (§5.9). El prototipo
  ya organiza esto por pestañas cuando hay varios tipos en la misma
  planta; portar esa organización.
- **Cuartos técnicos**: tarjeta individual vertical por cuarto (plantilla
  común de §5.7 + el tajo resaltado de su función concreta), no columnas
  en la tabla ancha — evita las casillas vacías que motivaron este diseño
  en primer lugar.

**El ciclo de marcado (`CYCLE`/`SYM`/`CLS`) de las celdas es EXACTAMENTE
el mismo que ya usa vivienda** (incluido el estado `N`, ya en producción
desde la Fase 0) — no se toca, no se duplica, la hoja de garaje generada
usa el mismo `<script>` de runtime que ya se genera para vivienda.

## Verificación — más exigente que de costumbre, y NO solo con tests de texto

Esta fase es JS puro sin cobertura de `unittest` propia salvo
`test_paginacion_generador.py` (que hace comprobaciones de texto/altura,
no de comportamiento real). **La lección ya aprendida en este proyecto
aplica aquí al pie de la letra**
(ver [[feedback_sagarde_dirigir_codex_y_verificar_de_verdad]]): *"los
tests de texto no bastan para CSS/print — abrir un navegador real".*

Verificación obligatoria, en este orden:

1. **Que el modo vivienda no cambia en absoluto.** Abrir el generador
   real en un navegador, completar el asistente en modo vivienda (el
   único que existe hoy) con una obra de prueba, generar una hoja, y
   comparar contra el mismo flujo antes del cambio — visualmente y
   comprobando que el HTML descargado es idéntico salvo por marcas de
   tiempo/ids aleatorios inevitables.
2. **El asistente de garaje completo, en el navegador real** (no en el
   pane de Claude en modo estático si se puede evitar — usar
   `preview_start`/`navigate` sobre el propio fichero): elegir modo
   Garajes, dar de alta una estructura con al menos un vial, un trastero
   y un cuarto técnico, seleccionar tajos, generar la hoja, y comprobar
   que:
   - la hoja generada tiene el reparto correcto (tabla ancha para
     viales/trasteros, tarjeta para el cuarto técnico);
   - las celdas se pueden marcar con el ciclo completo, incluido `N`, y
     el símbolo se ve bien (no un punto diminuto — ya hubo ese error una
     vez, ver el commit de hoy que lo corrigió en el prerrelleno);
   - el nombre de fichero de descarga sigue el mismo patrón que vivienda
     con el sufijo `_garaje` (§6.2 del diseño).
3. Ejecutar `tests/test_paginacion_generador.py` y la suite completa —
   necesario pero NO suficiente, no lo des por bueno solo con esto.

## Apéndice — `CAT_GARAJE` ya generado mecánicamente, listo para pegar

Generado con un script que lee directamente
`reglas/CATALOGO_TAJOS.json` (no retecleado a mano, evita el riesgo de
transcripción ya visto en la Fase 1) y escribe UTF-8 real, verificado a
nivel de bytes crudos. **Pegar tal cual, no reescribir.**

```js
const CAT_GARAJE = [
  {id:'garaje_tabicado', name:'Tabicado de garaje', g:'Obra civil garaje', p:'e', a:'z'},
  {id:'garaje_lucido', name:'Lucido de garaje', g:'Obra civil garaje', p:'e', a:'z'},
  {id:'garaje_falso_techo', name:'Falso techo de garaje', g:'Obra civil garaje', p:'e', a:'z'},
  {id:'garaje_raseado_viales', name:'Raseado/yeso de viales', g:'Obra civil garaje', p:'e', a:'z'},
  {id:'garaje_tubeado_emp', name:'Tubeado empotrado de garaje', g:'Instalación interior garaje', p:'p', a:'z'},
  {id:'garaje_cableado_emp', name:'Cableado empotrado de garaje', g:'Instalación interior garaje', p:'p', a:'z'},
  {id:'garaje_tubeado_visto', name:'Tubeado visto de garaje', g:'Instalación interior garaje', p:'p', a:'z'},
  {id:'garaje_cableado_visto', name:'Cableado visto de garaje', g:'Instalación interior garaje', p:'p', a:'z'},
  {id:'garaje_tubeado_vial', name:'Tubeado de viales', g:'Instalación interior garaje', p:'p', a:'z'},
  {id:'garaje_cableado_vial', name:'Cableado de viales', g:'Instalación interior garaje', p:'p', a:'z'},
  {id:'garaje_pintura_1_recinto', name:'Pintura de garaje (recintos) — 1ª mano', g:'Pintura garaje', p:'e', a:'z'},
  {id:'garaje_pintura_1_vial', name:'Pintura de garaje (viales) — 1ª mano', g:'Pintura garaje', p:'e', a:'z'},
  {id:'garaje_alum_fijo_coloc_recinto', name:'Colocación alumbrado fijo (recintos)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_alum_fijo_coloc_vial', name:'Colocación alumbrado fijo (viales)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_alum_temp_coloc_recinto', name:'Colocación alumbrado temporizado (recintos)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_alum_temp_coloc_vial', name:'Colocación alumbrado temporizado (viales)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_emergencia_coloc_recinto', name:'Colocación luminarias de emergencia (recintos)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_emergencia_coloc_vial', name:'Colocación luminarias de emergencia (viales)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_enchufe_coloc', name:'Colocación de enchufe de cuarto técnico', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_cuadro_tubeado_cableado', name:'Tubeado y cableado hasta cuadro secundario', g:'Cuadros garaje', p:'p', a:'z'},
  {id:'garaje_cuadro_colocacion', name:'Colocación y mecanizado de cuadro propio', g:'Cuadros garaje', p:'p', a:'z'},
  {id:'garaje_pintura_2_recinto', name:'Pintura de garaje (recintos) — 2ª mano', g:'Pintura garaje', p:'e', a:'z'},
  {id:'garaje_pintura_2_vial', name:'Pintura de garaje (viales) — 2ª mano', g:'Pintura garaje', p:'e', a:'z'},
  {id:'garaje_cuadro_embornado', name:'Embornado de cuadro propio', g:'Cuadros garaje', p:'p', a:'z'},
  {id:'garaje_cuadro_rotulacion', name:'Rotulación de cuadro propio', g:'Cuadros garaje', p:'p', a:'z'},
  {id:'garaje_cuadro_equipo_tubeado_cableado', name:'Tubeado y cableado del cuadro al equipo que controla', g:'Cuadros garaje', p:'p', a:'z'},
  {id:'garaje_alum_fijo_embornado_recinto', name:'Embornado alumbrado fijo (recintos)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_alum_fijo_embornado_vial', name:'Embornado alumbrado fijo (viales)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_alum_temp_embornado_recinto', name:'Embornado alumbrado temporizado (recintos)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_alum_temp_embornado_vial', name:'Embornado alumbrado temporizado (viales)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_emergencia_embornado_recinto', name:'Embornado luminarias de emergencia (recintos)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_emergencia_embornado_vial', name:'Embornado luminarias de emergencia (viales)', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_enchufe_embornado', name:'Embornado de enchufe de cuarto técnico', g:'Equipos garaje', p:'p', a:'z'},
  {id:'garaje_tierras_general', name:'Tierras — llegada y embornado en Centralización', g:'Cuartos técnicos garaje', p:'p', a:'z'},
  {id:'garaje_tierras_derivacion', name:'Derivación de tierra de cuarto técnico', g:'Cuartos técnicos garaje', p:'p', a:'z'},
  {id:'garaje_centralizacion_modulos', name:'Colocación de módulos de contadores', g:'Cuartos técnicos garaje', p:'p', a:'z'},
  {id:'garaje_centralizacion_derivaciones', name:'Derivaciones individuales — centralización y embornado', g:'Cuartos técnicos garaje', p:'p', a:'z'},
  {id:'garaje_centralizacion_lga', name:'Acometida LGA desde CGP de calle', g:'Cuartos técnicos garaje', p:'p', a:'z'},
  {id:'garaje_puerta_alimentacion', name:'Alimentación de cuadro de puerta de acceso', g:'Remates garaje', p:'p', a:'z'},
  {id:'garaje_puerta_mecanizado', name:'Mecanizado de puerta de acceso', g:'Remates garaje', p:'c', a:'z'},
  {id:'garaje_irve_preinstalacion', name:'Preinstalación vehículo eléctrico (IRVE)', g:'Remates garaje', p:'p', a:'z'},
  {id:'garaje_telco_transito', name:'Telecomunicaciones de tránsito', g:'Remates garaje', p:'p', a:'z'},
];
```

(42 entradas — comprobar `CAT_GARAJE.length===42` como primera verificación
mecánica antes de nada más.)

## Qué NO hace la Fase 4 (documentar en el propio código)

- No lee ni escribe `ficha_garajes.json` directamente — eso es el
  adaptador de lectura, Fase 5, aparte.
- No auto-carga estructura de garaje desde `window.SAGARDE_OBRAS_REVISION`
  (el mecanismo que sí existe para vivienda vía `worksWithDatabase()`) —
  ninguna obra real tiene `ficha_garajes.json` todavía, así que no hay
  nada que auto-cargar. Cuando lo haya, extender el generador de
  `obras_revisiones.js` para incluirlo es trabajo aparte.
- No valida `deps` reales entre tajos de garaje en la hoja (ya sabido
  desde la Fase 1: los `deps` no se prueban contra datos reales hasta la
  Fase 6).
