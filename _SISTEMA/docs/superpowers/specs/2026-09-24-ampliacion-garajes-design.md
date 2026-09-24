# Ampliación de revisiones a garajes — Diseño

**Fecha:** 24/09/2026 (diseño) — actualizado 24/09/2026 (prototipo probado)
**Estado:** diseño cerrado y validado contra un prototipo interactivo
navegable (ver §9); listo para implementación real. El único cambio ya
aplicado al entorno real es el estado `N` en el ciclo de marcado de
`generador_revisiones.html` (§6.3) — el resto de este documento sigue sin
tocar ningún fichero de producción.
**Alcance:** solo garajes. Locales particulares (otra ampliación ya prometida
por Bixente en su día) quedan fuera, análisis aparte.
**Obra de prueba real:** Mungia o Gernika (a elegir según cuál visite Bixente
primero en obra — ambas sirven igual para validar el flujo).

---

## 1. Objetivo y contexto

Bixente ya había anunciado en su día que las revisiones se ampliarían tanto a
garajes como a locales particulares. Como punto de partida se encargaron dos
estudios preliminares:

- `_SISTEMA/docs/estudiogarajesagy.md` (Antigravity/agy, 24/09/2026).
- Un estudio equivalente de ChatGPT, aportado por Bixente desde
  `D:\Descargas\estudiogarajeschatgpt.md` (fuera del repositorio; si se quiere
  conservar como referencia permanente habría que copiarlo a `_SISTEMA/docs/`).

Ninguno de los dos estudios había visto el código real. Este documento es el
resultado de contrastarlos con `ficha_obra.py`, `CATALOGO_TAJOS.json`,
`priorizador_trabajos.py`, `alta_obra_desde_hoja.py` y
`generador_revisiones.html`, y de una sesión larga de preguntas y respuestas
con Bixente (24/09/2026) para resolver con criterio real de obra lo que
ninguno de los dos estudios acertaba del todo: sobre todo, que **el garaje es
antes una obra civil que una instalación eléctrica**, y que la estructura
física de un garaje no es uniforme como la de una planta de viviendas.

## 2. Principios rectores

Aparecieron varias veces a lo largo de la conversación y deben gobernar
cualquier decisión posterior que no esté ya escrita aquí:

1. **El garaje tiene que ser sencillo.** Palabras textuales de Bixente: *"no
   quiero complicar mucho el garaje"*. Ante una disyuntiva entre precisión y
   simplicidad, por defecto se elige la opción simple, y se deja constancia de
   qué se sacrificó.
2. **Reutilizar lo que ya existe, no inventar mecanismos nuevos.** Cada pieza
   de este diseño se apoya en algo que el motor ya hace hoy para vivienda
   (ver §3 y §5): listas de tamaño variable, el estado `N`, tajo no aplicable
   a una obra, agregación de varios bloques en una sola lectura.
3. **Empezar básico, ampliar después.** Un catálogo pequeño y genérico ahora;
   las especializaciones por función de cuarto técnico (centralización, RITI,
   achique, aerotermia, sala de calderas) se añaden más adelante, cuando haga
   falta de verdad.
4. **De otros gremios solo nos importa la puerta de paso.** Tabicado, lucido,
   falso techo, raseado/yeso: tajos genéricos, sin distinguir la técnica o el
   material del otro gremio. Palabras de Bixente: *"basta con algo genérico,
   somos los electricistas"*.
5. **No inventar ni dar por bueno sin probar.** Antes de tocar una obra real,
   validar contra `OBRA PRUEBA`.

## 3. Estructura de datos

### 3.1 Por qué el garaje no es un portal más de la ficha de vivienda

Primera idea (descartada): meter el garaje como un `portal` más dentro de
`ficha_obra.json`, colgado de un `bloque` de vivienda. Bixente la descartó con
un caso real: **Mungia tiene 2 bloques (uno con 1 portal, otro con 2) y cada
bloque tiene debajo su propio garaje — 2 garajes independientes en la misma
obra.** En otras obras puede darse el caso contrario, un único garaje
compartido por varios bloques. Colgar el garaje de un bloque concreto sería
conceptualmente falso en ambos casos.

### 3.2 Decisión

- Cada obra tiene una **lista de garajes** (0, 1 o varios), independiente de
  la lista de bloques de vivienda. Es el mismo patrón que ya usan bloques,
  portales y viviendas (listas de tamaño variable) — no es mecanismo nuevo.
- Vive en **ficha propia**, dentro de la misma carpeta de obra, no en
  `ficha_obra.json` de vivienda ni como entrada nueva en `registro_obras.py`.
  Fichero propuesto: `ficha_garajes.json` en `INFORME SAGARDE IA/`.
- Cada garaje de la lista es **más plano** que la ficha de vivienda: no hay
  nivel de bloque ni de portal. `garaje → planta → zona → tajo`. Coincide con
  cómo lo describió Bixente desde el principio ("dividimos para empezar en
  plantas, y dentro de cada planta añadiremos zonas").

Borrador ilustrativo (no definitivo):

```json
{
  "garajes": [
    {
      "id": "garaje_b1",
      "nombre": "Garaje Bloque 1",
      "plantas": [
        {
          "id": "s1",
          "nombre": "S-1",
          "zonas": [
            {"id": "zona_a", "tipo": "vial", "nombre": "Zona A"},
            {"id": "rampa_1", "tipo": "vial", "nombre": "Rampa acceso"},
            {"id": "trasteros_1", "tipo": "trastero", "nombre": "Trasteros zona 1"},
            {"id": "escalera_1", "tipo": "escalera", "nombre": "Escalera 1"},
            {"id": "rellano_1", "tipo": "rellano", "nombre": "Rellano Escalera 1 / S-1"},
            {"id": "ct_riti", "tipo": "cuarto_tecnico_riti", "nombre": "Cuarto RITI"},
            {"id": "ct_general", "tipo": "cuarto_instalaciones_generales", "nombre": "Cuarto de instalaciones generales"}
          ]
        }
      ]
    }
  ]
}
```

**Aviso técnico** (para cuando se implemente, no bloquea el diseño): hoy
`generar_todos.py`, `panel_obra.py`, `motor_informes.py` y
`priorizador_trabajos.py` asumen una sola ficha por obra. Con ficha aparte,
cada uno de esos módulos tiene que aprender a leer una segunda fuente para
esa obra. Bixente ya conoce y acepta este coste, dada la razón de §3.1.

### 3.3 Panel: una lectura combinada por categoría, no por garaje

Decisión explícita de Bixente ante el ejemplo de Mungia (2 garajes): **NO**
una gráfica por cada garaje físico. Igual que hoy Mungia ya combina sus 2
bloques × 3 portales en una sola lectura de vivienda, cada obra tiene
exactamente **dos** lecturas combinadas — una de vivienda, una de garaje —
ambas dentro de la misma página de la obra. El desglose por garaje concreto
(Bloque 1 vs Bloque 2) sigue disponible donde ya vive hoy el detalle: las
tablas de Trabajos/Prioridades, no el gráfico resumen. Es la misma agregación
que ya hace `motor_informes.py` sobre los bloques de vivienda, aplicada otra
vez sobre la lista de garajes.

### 3.4 Cómo se puebla una planta (wizard)

Al añadir una planta a un garaje, dos mecánicas conviven, ambas ya usadas hoy
en el asistente de vivienda con otro nombre:

| Mecánica | Cómo funciona | Tipos |
|---|---|---|
| **Lista de comprobación** | Existe o no en esa planta; si no se marca, no se genera nada — no hay que marcar "N/A" para lo que no existe | Escalera, Rellano, Cuarto técnico completo (desglosado desde el principio por función: RITI/teleco, achique/bombas, aerotermia, sala de calderas, centralización...), Cuarto de instalaciones generales (cuadros), Cuarto ligero (Basuras, Bicicletas — ver §5.7) |
| **Zonas por conteo, como viviendas** | Se pide "cuántas zonas" (el número depende de los circuitos asignados en esa planta, no es fijo) y se generan editables una a una, igual que hoy con las viviendas | Viales / alumbrado de parcelas, Trasteros |

**Rampa no es un tipo de estructura propio.** Es una zona más dentro del
conteo de viales — civil y constructivamente es "parte del vial" (sin
tabicar, instalación vista) — pero cuenta como su propia zona porque tiene un
circuito de alumbrado + emergencia independiente del vial general, y ese es
el criterio real que decide cuántas zonas hay ("dependerá de los circuitos
que tengamos asignados por planta").

**Rellano se renombra a "Rellanos / Zonas comunes"** en las vistas de
resumen: cubre también pasillos internos y pasillos de trasteros, cualquier
zona de circulación peatonal que comparta el mismo perfil de obra civil e
instalación (§4.2). El botón de añadir en el asistente se queda corto
("+ Rellano", para que el nombre autogenerado de la zona no sea kilométrico)
pero lleva un texto de ayuda con el alcance completo.

### 3.5 Las 4 pantallas del asistente (probado en prototipo, ver §9)

1. **Obra** — se elige la obra de una lista; si no existe, "+ Obra nueva…"
   la crea con un campo de texto en línea (sin `prompt()` ni diálogos, todo
   inline). Después se elige **Viviendas** o **Garajes**; si la obra
   seleccionada ya tiene las dos estructuras dadas de alta, aparece un aviso
   explícito ("hay que preguntar cuál de las dos") antes de dejar continuar.
2. **Estructura** — el mecanismo de §3.4, con una lista de garajes de la obra
   (añadir/renombrar/quitar) y, dentro de cada uno, sus plantas y zonas.
3. **Tajos** — catálogo agrupado por fase (obra civil, canalización,
   alumbrado, equipos, cuadros, otros), con casillas y las etiquetas SGD/EXT
   ya existentes en la app real. Lleva un botón "↺ Restablecer" que repone la
   selección de partida sin tocar la estructura ya construida — necesario
   porque el navegador recuerda la última selección entre sesiones
   (`localStorage`), y un cambio en qué viene marcado por defecto no
   actualiza solo las sesiones que ya tenían algo guardado.
4. **Generar** — resumen (obra, garajes, plantas, zonas, tajos activos,
   nombre de fichero) y la vista previa real de cómo se repartiría la hoja
   (§6). El botón "Generar hoja de campo" es donde en la app real se
   guardaría/descargaría el HTML, igual que ya hace hoy para viviendas.

## 4. Obra civil — la columna vertebral

Corrección central de Bixente a mitad de la sesión: *"hay que dar una vuelta
a todo, al final es una obra civil"*. Ninguno de los dos estudios de partida
modela esto — agy solo trae `obra-civil`/`tabic-ct`/`tabic-tras` sueltos (sin
lucido, techos ni pintura); ChatGPT no trae ni un solo tajo de obra civil en
sus 43 grupos. Pero **ya es exactamente así como funciona vivienda**:
`tabicado` es el tajo raíz de toda la cadena (orden 10, cero dependencias), y
el resto —incluido lo eléctrico— cuelga de sus huecos (tabicado → rozas →
Pladur cierra 1ª cara → **entra SGD** → Pladur cierra 2ª cara → techos →
pintura 1ª → **entra SGD (mecanizado)** → pintura 2ª → placas/tapas).

### 4.1 Dos rutas de instalación, decidida zona a zona

En cualquier recinto cerrado hay dos formas reales de instalar, con
consecuencias de orden distintas:

- **Empotrada** (tubo corrugado): tabicado → tubeado empotrado (SGD) → lucido
  → cableado (SGD) → falso techo si aplica → pintura 1ª → mecanizado /
  downlights (SGD) → pintura 2ª.
- **Vista** (tubo PVC de superficie): tabicado → lucido → tubeado visto (SGD)
  → cableado (SGD) → pintura 1ª → mecanizado / apliques (SGD) → pintura 2ª.
  Sin falso techo.

La diferencia real entre las dos no es solo qué tubo se usa: **el orden
relativo entre Sagarde y el gremio que lucha/cierra se invierte** según la
ruta. Es "bastante normal en los garajes" que las dos convivan incluso dentro
de lo que a simple vista parece una sola escalera (ver §4.3).

**Decisión de simplicidad (24/09/2026, aplicando el principio 1 de §2):**
`Lucido` depende siempre solo de `Tabicado`, nunca del tubeado de Sagarde, en
las dos rutas. El orden real de quién va primero se refleja solo en el número
de `orden` del catálogo (posición en las listas), no como dependencia que
bloquea. Se sacrifica algo de precisión (si Sagarde se retrasa tubeando en la
ruta empotrada, el motor no avisará de que está bloqueando al gremio que
luce) a cambio de mantener el garaje simple.

**Motivo técnico de por qué las dos rutas no pueden compartir un paso
intermedio** (p. ej. un solo "cableado" genérico): una celda marcada `N` (no
aplica) no libera a quien dependa de ella — en `priorizador_trabajos.py`,
`_buscar_dep` la trata como "no empezada" y bloquearía para siempre la ruta
que sí aplica en esa zona. Por eso cada ruta tiene que ser una cadena
paralela y completa de principio a fin (tubeado→cableado→mecanizado→
luminaria), nunca cruzada.

**Qué ruta aplica a cada zona** se decide zona a zona marcando `N` en la que
no corresponda — el mismo mecanismo que ya existe hoy para "tajo no
aplicable a esta obra" (Gernika ya excluye suelo radiante y termostatos),
solo que aquí opera a nivel de zona en vez de obra entera. No hace falta
mecanismo nuevo.

### 4.2 Qué ruta lleva cada tipo de zona

| Zona | Ruta | Techo | Luminaria | Notas |
|---|---|---|---|---|
| Trasteros | Empotrada o vista, a elegir por obra/zona | Falso techo si aplica (Pladur o escayola, genérico) | Según ruta | Se tabican y se lucen primero |
| Cuartos técnicos | Empotrada o vista, a elegir por obra/zona | Falso techo si aplica (genérico) | Según ruta | Se tabican y se lucen primero |
| Escalera (tramo puro) | **Siempre vista** | Nunca falso techo | Apliques | Pared sí se luce y pinta; el techo queda el forjado visto |
| Rellano / Zona común | **Siempre empotrada** | Casi siempre falso techo (Pladur o escayola, genérico) | Downlights | Puede convivir con una Escalera vista en el mismo acceso — son zonas distintas. Incluye pasillos internos y de trasteros |
| Viales / zonas de aparcamiento | Siempre vista | Sin falso techo — el forjado visto lleva **raseado o yeso genérico + pintura** | — | Sin tabicado ni lucido de pared; bandejas y canaletas también de superficie |
| Rampa | Como vial (vista, sin tabicar) | Como vial | — | Circuito propio de alumbrado + emergencia; ver §4.3 |

Principio transversal: para cualquier trabajo de obra civil (tabicado,
lucido, falso techo, raseado/yeso) el tajo es genérico, sin distinguir
técnica ni material del otro gremio — solo interesa como puerta de paso.

### 4.3 Rampas y puertas de acceso

- La rampa no es estructura civil distinta del vial (sin tabicar, instalación
  vista), pero sí es su propia zona: tiene un circuito independiente de
  alumbrado + emergencia, separado del vial general.
- La puerta motorizada de acceso se instala normalmente al final de la fase
  (orden alto en el catálogo).
- Dos tajos separados:
  - **Alimentación del cuadro de la puerta** — siempre propio de Sagarde.
  - **Mecanizado de la puerta** (semáforo, llaves, detectores/lazo) — puede
    ser del instalador de la puerta, no obligatoriamente Sagarde →
    `propiedad: coordinacion` (la misma categoría que ya usa el catálogo para
    climatización/ascensoristas).

## 5. Catálogo de tajos — alcance y estado

### 5.1 Dónde viven los tajos nuevos

Al catálogo **común** (`CATALOGO_TAJOS.json`), no como tajos propios de una
obra (el mecanismo que ya existe para los 18 tajos exclusivos de Obispo
Orueta). Motivo: aquello fue una excepción de una sola obra; esto no —
Bixente ya había prometido la ampliación a garajes en general, y la propia
ficha de obra de Mungia/Gernika ya anticipaba "añadirán garajes en el
futuro".

### 5.2 v1 — básico, ya cerrado en esta sesión

Tajos genéricos compartidos por cualquier zona que los necesite, con sus dos
variantes de ruta donde aplica (§4.1): tabicado, tubeado (empotrado/visto),
cableado (empotrado/visto), mecanizado/cuadros (empotrado/visto), alumbrado,
emergencias — más los tajos de obra civil descritos en §4 (lucido, falso
techo, raseado/yeso, pintura 1ª/2ª).

### 5.3 Pospuesto a propósito

- "Sistema" (ventilación, PCI, CO...) cruzando varias zonas de una misma
  planta: no es necesidad de v1. Si hace falta más adelante (p. ej. "qué
  falta para poder probar la ventilación de S-2"), candidato natural es
  tratarlo **fuera de la rejilla**, como ya hace `cierre_expediente.py` con
  ensayos/OCA/CIE, en vez de forzar al motor de dependencias a cruzar zonas
  (`_buscar_dep` hoy solo mira dentro de la misma ubicación).

Las ampliaciones específicas por función de cuarto técnico que en la primera
vuelta de esta sesión se dejaron pospuestas ("de momento lo básico") **ya se
diseñaron** en una segunda vuelta — ver §5.4 a §5.8. Sigue pendiente solo la
traducción a `id`/`orden`/`deps` concretos de `CATALOGO_TAJOS.json` (§7).

### 5.4 Alumbrado

Se divide en **fijo** (circuito permanente, vigilancia) y **temporizado**
(detector/reloj), como exige REBT ITC-BT-28. Los dos pueden coexistir en la
misma zona — no es una elección excluyente, es un tajo por zona para cada
uno. El catálogo los lleva siempre los dos disponibles; que una zona use uno,
otro o ambos es cuestión de qué se marque, no de qué exista.

**Trasteros, por defecto, sin alumbrado fijo.** Decisión explícita de
Bixente sobre el perfil de partida de esa zona (no sobre el catálogo:
alumbrado fijo sigue existiendo como tajo y se puede marcar si un proyecto
concreto lo lleva) — un trastero normal va con temporizado solo. Ver §5.9
sobre cómo el prototipo separa "qué tajos existen" de "qué tajos trae
marcados cada tipo de zona por defecto".

### 5.5 Patrón de equipo simple

Para cualquier equipo propio de Sagarde que no sea un cuadro (pantalla de
alumbrado fijo, pantalla temporizada, luminaria de emergencia, detector,
downlight, aplique...): **Cableado → Colocación (depende de Cableado +
Pintura 1ª) → Embornado (depende de Colocación + Pintura 2ª)**. Tajos
independientes por tipo de equipo y por zona — nunca uno genérico que cubra
"todo lo que haya en la zona". El tajo se llama **"Embornado"**, sin
"de equipos": cubre también cajas de registro, pulsadores y detectores de
esa parte de la instalación, no solo el equipo final (corrección de Bixente,
24/09/2026).

### 5.6 Cuadros

Cada cuadro concreto tiene su propio tajo, nunca uno genérico compartido.
Regla fija (24/09/2026):

- **Todo cuadro**, sea o no nuestro por dentro, lleva siempre **Tubeado +
  Cableado propio desde el Cuadro General de Garaje** hasta ese cuadro
  secundario.
- **Cuando el cuadro es nuestro por dentro** (ejemplo dado por Bixente: RITI;
  también el Cuadro Eléctrico General): además, Colocación + Mecanizado +
  Embornado del propio cuadro, y la cadena completa hasta el equipo terminal
  que controla — Tubeado + Cableado también del cuadro hacia el equipo
  (bomba, ventilador...).
- **Cuando el cuadro NO es nuestro por dentro** (Ventilación, Bombas/Achique,
  Aerotermia, CO2, Incendios/PCI, Ascensor si lo hay): solo la pata de
  alimentación desde el Cuadro General — nada del cuadro hacia adentro ni
  hacia el equipo que controla, eso es del instalador especialista de ese
  sistema (o del ascensorista).
- **Puerta de acceso**, excepción ya vista en §4.3: alimentación siempre
  nuestra; mecanizado de puerta se queda en el catálogo pero no aplicable
  por defecto, por si algún proyecto concreto nos lo asigna.
- **Rotulación**: un tajo por cuadro, solo si el cuadro es nuestro por
  dentro. Si no lo es, no procede.

### 5.7 Cuartos técnicos — plantilla común

Cuando un cuarto técnico (Centralización de Contadores, RITI, Ventilación,
Bombas, Aerotermia, Sala de Calderas, PCI...) existe como recinto
independiente, comparte esta base, sea cual sea su función específica:

- Obra civil: tabicado + lucido/raseado, como cualquier recinto cerrado (§4).
- Alumbrado + Emergencia + Enchufe propios del cuarto.
- Tubeado + Cableado del Cuadro General hasta el cuadro de ese cuarto (§5.6).
- Si el cuadro de ese cuarto es nuestro por dentro, se añade su
  colocación/mecanizado/embornado (§5.6).
- **Derivación de tierra**, un tajo propio por cada cuarto técnico (achique,
  ventilación, aerotermia, sala de calderas...) — distinto del tajo general
  de tierras de §5.8, que es único para todo el garaje. Palabras de Bixente:
  *"tierras en este caso es una para todo independientemente de las zonas
  que haya, luego tiene que haber una derivación por cada cuarto técnico"*.
  En el prototipo es el tajo que se resalta como "específico" en la tarjeta
  de cada cuarto técnico (§5.9), salvo en Centralización, donde el resaltado
  es el propio tajo general de tierras (ahí nace la derivación, no hace
  falta una aparte).

**Centralización de Contadores** añade, sobre esa base: colocación de los
módulos, centralización de las derivaciones individuales + su embornado, y
la acometida de la LGA desde el CGP de la calle (tubeado + cableado +
embornado, por viales hasta el cuarto). A veces comparte cuarto con un
Cuadro de Servicios Generales del portal, que sigue el mismo patrón de
cuadro que cualquier otro (§5.6).

**Cuartos ligeros** (Basuras, Bicicletas): mismo recinto cerrado, pero sin
cuadro propio — solo la parte de obra civil (tabicado + lucido) y Alumbrado
+ Emergencia + Enchufe. Más parecidos a un trastero que a un cuarto técnico
completo.

### 5.8 Otros tajos identificados

- **Vehículo eléctrico (IRVE)**: en básico, un único tajo de
  preinstalación — bandeja o canaleta reservada desde el Cuadro General o la
  Centralización, por los viales, hasta la última plaza. Cargadores
  concretos quedan fuera del básico, caso aparte si un proyecto los pide.
- **Telecomunicaciones de tránsito**: cuando el garaje sirve de paso de
  telecomunicaciones entre dos edificios, o de entrada desde la calle, dos
  tajos de tubo/bandeja, tratados igual que cualquier tajo de vial.
- **Tierras**: tajo general único para todo el garaje (llegar a la
  Centralización de Contadores + embornar ahí), más una **Derivación de
  tierra** independiente por cada cuarto técnico — ver §5.7, que es donde
  vive la regla completa por tratarse de un tajo de cuarto técnico, no de
  vial.

### 5.9 Perfiles de tajos por tipo de zona (hallazgo del prototipo)

El catálogo de §5.2–§5.8 define **qué tajos existen**. Construir el
prototipo (§9) obligó a resolver un problema distinto que el diseño inicial
no cubría: **qué subconjunto de ese catálogo tiene sentido ofrecer marcado
por defecto según el tipo de zona** — no todos los tajos aplican a todas las
zonas por igual, y mostrarlos todos en cada zona generaba ruido (ver §6.4).

Solución adoptada, validada en el prototipo:

- Un **perfil por tipo de zona** (vial, trastero, escalera, rellano, cuarto
  técnico, cuarto ligero) fija qué tajos del catálogo aplican a ese tipo. Es
  la traducción operativa de la tabla de §4.2 y de las reglas de §5.4–§5.8.
- Dentro de los cuartos técnicos, cada **función concreta** (Centralización,
  RITI, achique, aerotermia...) puede añadir un tajo **específico resaltado**
  encima de la plantilla común de §5.7 — por ejemplo, la Derivación de tierra
  en un cuarto de aerotermia, o el propio tajo general de tierras en
  Centralización.
- Este mecanismo es de **presentación** (qué se ofrece premarcado y cómo se
  agrupa en pantalla), no cambia el catálogo ni el motor de dependencias:
  cualquier tajo se puede marcar o desmarcar a mano en cualquier zona si un
  caso real lo pide.

## 6. Generador de revisiones — flujo de uso

### 6.1 Elegir Viviendas o Garajes al generar

Confirmado por Bixente (24/09/2026):

- Al generar una hoja **nueva** desde `generador_revisiones.html`, se elige
  explícitamente si es de **Viviendas** o de **Garajes**.
- Si la obra elegida **ya tiene las dos** estructuras dadas de alta, el
  generador pregunta cuál de las dos generar.

### 6.2 Guardado con sufijo `_garaje`

Al guardar (hoja en blanco para alta, o revisión rellena), se guarda en la
**misma carpeta `REVISIONES`** que las de vivienda, añadiendo `_garaje` al
nombre del fichero para distinguirlas.

### 6.3 Estado `N` ("no aplica") — ya aplicado al entorno real

Idea de Bixente surgida durante la iteración del prototipo, pero **no es
mecanismo nuevo**: es el estado `N` que el alfabeto del proyecto ya define
para vivienda (§7 del CLAUDE.md del proyecto — "no aplica a esa ubicación"),
extendido aquí a un **cuarto click más** en el ciclo de marcado de
`generador_revisiones.html`, disponible para **todas** las revisiones, no
solo garaje.

- Ciclo anterior: vacío → `/` → `M` → `X` (3 clics para completar). Ciclo
  nuevo: vacío → `/` → `M` → `X` → `N` (un clic más para volver a vacío desde
  `N`).
- Marcar `N` una casilla la excluye del todo — ni pendiente ni ejecutada, no
  cuenta en el porcentaje de obra. Mismo comportamiento que `N` ya tiene hoy
  en el resto del sistema (Gernika excluye así suelo radiante y termostatos
  a nivel de obra entera; aquí opera a nivel de celda individual).
- Bixente evaluó el riesgo de marcar por error con el pulgar en tablet y
  decidió aceptarlo explícitamente: *"debería ser un clic más, es muy cómodo
  con la tablet en obra. Si hubiera error en la siguiente revisión me daría
  cuenta y lo arreglaría"* — la propia norma de "la última revisión es la
  que vale" (§7 del CLAUDE.md del proyecto) ya cubre la corrección.
- **Ya aplicado a producción real** (24/09/2026), no solo al prototipo: 3
  cambios exactos en `generador_revisiones.html` (el array `CYCLE`, el mapa
  de símbolos `SYM`, y la leyenda visual con su color `.leg-dot.ext`).
  Verificado con la suite completa del proyecto antes de darlo por bueno:
  `python -m unittest discover -s tests` → **604 tests, 0 fallos**
  (`Ran 604 tests in 43.733s / OK (skipped=4)`). El resto de este documento
  (estructura de garaje, catálogo, wizard) sigue sin tocar ningún fichero de
  producción.

### 6.4 Reparto de la hoja por tipo de zona (hallazgo del prototipo)

El diseño inicial no preveía cómo se vería la hoja de campo generada. Probar
el prototipo con datos de ejemplo destapó un problema real de legibilidad:
una sola tabla ancha (zonas en columna × todos los tajos en fila) deja
huecos enormes para los cuartos técnicos, porque cada función de cuarto usa
solo un subconjunto pequeño del catálogo — Bixente lo describió como
*"muchas casillas vacías... hasta no llegar a la columna de su cuadro"*.

Solución validada en el prototipo, a aplicar también en
`generador_revisiones.html`:

- **Zonas de conteo uniforme** (viales, trasteros, y por extensión escalera
  y rellano/zona común): tabla ancha como hoy en vivienda — cada columna una
  zona, cada fila un tajo del perfil de §5.9. Agrupadas por pestañas cuando
  hay varios tipos en la misma planta.
- **Cuartos técnicos**: tarjeta individual por cuarto, lista vertical de sus
  tajos (plantilla común de §5.7 + el resaltado específico de su función),
  en vez de columnas en la misma tabla ancha. Evita el hueco: un cuarto no
  comparte fila con zonas que no tienen nada que ver con él.

Pendiente de detallar: mecánica concreta de la lista de comprobación y las
zonas por conteo dentro del propio HTML/JS del generador real (el prototipo
lo resuelve en JS de demostración, no en el fichero de producción); y el
adaptador que traduzca esas hojas de garaje a `REVISION_NORMALIZADA` (análogo
a `adaptar_revision_html.py` / `adaptar_revision_pdf_digital.py`, o extensión
de los existentes).

## 7. Pendiente / abierto

- Catálogo tajo a tajo con `id`, `orden` y `deps` exactos — el borrador de
  §4.1 está a nivel de nombre, falta traducirlo a `CATALOGO_TAJOS.json`.
- **Los `deps` reales nunca se modelaron.** El prototipo (§9) demuestra la
  estructura, el catálogo agrupado y el ciclo de marcado, pero no implementa
  bloqueo por dependencia — cada zona muestra su perfil de tajos (§5.9) como
  lista plana, sin encadenar "esto bloquea a aquello". La cadena de
  dependencias real (tabicado → tubeado → lucido → cableado → ... de §4.1)
  sigue pendiente de traducirse a `deps` de `CATALOGO_TAJOS.json` y de
  probarse contra `priorizador_trabajos.py`.
- Ampliaciones específicas por tipo de cuarto técnico más allá de la
  plantilla común (§5.7): de momento cubre lo básico de cada función, no
  cada una en detalle (p. ej. particularidades de PCI o de una sala de
  calderas concreta).
- Implementación del wizard de 4 pantallas (§3.5) en `generador_revisiones.html`,
  incluyendo el reparto de la hoja por tipo de zona (§6.4).
- Adaptador de lectura de revisiones de garaje (§6).
- Locales particulares — fuera de alcance, análisis aparte.
- **Obra de prueba real decidida: Mungia o Gernika**, a elegir según cuál
  visite Bixente primero (mañana 25/09, si no el lunes o martes siguiente).
  Sustituye cualquier mención anterior a Olabeaga u OBRA PRUEBA como destino
  final — `OBRA PRUEBA` sigue siendo el paso previo recomendado para probar
  el catálogo/wizard antes de tocar una obra con datos reales, pero ya no es
  el destino, es un escalón intermedio.
- Reparto de trabajo detallado por fases: ver el plan de trabajo aparte,
  `2026-09-24-ampliacion-garajes-plan.md` (misma carpeta), que incluye la
  propuesta de reparto Claude/Codex/agy fase a fase. Principio general ya
  fijado: catálogo JSON y documentación con valores ya decididos → agy;
  cambios de `generador_revisiones.html` / ficha nueva / tests (necesitan
  ejecutarse para comprobarse) → Codex; diseño, dirección y verificación
  independiente → Claude. Nunca dos trabajadores a la vez sobre el mismo
  árbol.

## 8. Fuentes

- `_SISTEMA/docs/estudiogarajesagy.md`
- Estudio de ChatGPT aportado por Bixente (`D:\Descargas\estudiogarajeschatgpt.md`, fuera del repositorio)
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/ficha_obra.py`
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/reglas/CATALOGO_TAJOS.json`
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py`
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/alta_obra_desde_hoja.py`
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generador_revisiones.html`
  (incluye los 3 cambios reales del estado `N`, §6.3)
- `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/adaptadores/adaptador_olabeaga.py`
- Prototipo interactivo construido y validado en esta sesión (§9)
- Memoria: Olabeaga alta en modo Gorliz; tajos propios de obra (Orueta);
  ficha de obra; sesión de diseño 24/09/2026 (este documento)

## 9. Prototipo interactivo

Construido y refinado en ~15 rondas de cambios en vivo durante esta misma
sesión, con Bixente revisando cada versión en el navegador (Artifact +
Microsoft Edge sobre el fichero local en paralelo).

- **Artifact publicado:** https://claude.ai/artifact/TKc74kuhSoykLidgbgJnbD
- **Copia local:**
  `_SISTEMA/scratch/garaje-wizard-demo.html` (fuera de `INFORME SAGARDE IA/`
  a propósito — es material de exploración, no el generador real).

Qué demuestra (todo lo citado en §3.5, §5.9, §6.3 y §6.4 viene de aquí):
el asistente de 4 pantallas completo, alta de obra nueva en línea, el
mecanismo de lista de comprobación vs. zonas por conteo (§3.4), el catálogo
agrupado por fase con casillas, el botón "↺ Restablecer" y por qué hace
falta, el ciclo de marcado con `N` incluido, y la vista previa de hoja
repartida por tipo de zona.

Qué **no** demuestra, a propósito (queda para la implementación real): los
`deps` reales entre tajos (ver aviso en §7), el guardado/generación real de
HTML descargable, el adaptador de lectura, ni ninguna escritura contra
`ficha_garajes.json` — es JS de demostración con datos de ejemplo
(`OBRAS_DEMO`), no conectado al backend Python del proyecto.
