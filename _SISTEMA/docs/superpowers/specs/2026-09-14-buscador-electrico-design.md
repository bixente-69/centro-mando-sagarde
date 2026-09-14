# Buscador con IA sobre la biblioteca de PROYECTO ELECTRICO — diseño

Fecha: 14/09/2026. Autor: Claude (diseño, sin programar nada todavía).

Encargo de Bixente: quiere, dentro de Sagarde, una pestaña/aplicación que
responda preguntas técnicas combinando el conocimiento general de la IA con
su propia biblioteca de PDFs/manuales de
`D:\Nueva carpeta\OneDrive\PROYECTO ELECTRICO` (de momento solo un almacén de
libros y normativa que va guardando, sin nada generado todavía). No es
urgente ("trabajo de fondo, no hay que acabarlo hoy") pero el listón de
calidad es alto: "que sea perfecto cuando acabe y no genere problemas de
ningún tipo" (cita textual, 14/09/2026).

**Fin al que sirve todo esto (releer antes de cada fase, para no perder el
rumbo):** que Bixente pueda preguntar algo técnico de electricidad desde el
PC o desde el móvil — incluida una obra sin wifi de casa — y reciba una
respuesta que combine lo que sabe la IA con lo que dicen sus propios libros,
citando cuándo viene de un libro y cuándo es conocimiento general, sin que
la clave de NVIDIA ni el contenido de los libros queden expuestos en el
repositorio público de Sagarde. Prioridad, en este orden: no exponer
secretos > no dar información inventada como si fuera de un libro > que
funcione desde el móvil sin depender del PC encendido > sencillez de uso.

---

## A. Alcance de esta primera fase

**Sí, en esta fase:**
- Una pregunta suelta → una respuesta (sin memoria de conversación).
- Responde combinando los PDFs de PROYECTO ELECTRICO + conocimiento general
  de la IA, dejando claro de dónde viene cada parte.
- Funciona igual desde el PC que desde el móvil, con o sin wifi de casa.
- La clave de NVIDIA y el contenido de los libros nunca se publican en el
  repo público `centro-mando-sagarde`.

**No, todavía no (ver sección J, Fase 2):**
- Memoria de conversación / preguntas de seguimiento tipo chat. Bixente pidió
  explícitamente (14/09/2026) que quede anotado como ampliación natural una
  vez que esta primera fase demuestre que las respuestas son útiles — no
  olvidarlo ni hay que preguntarlo otra vez cuando llegue el momento.

**Corrección de un malentendido inicial, para que no se repita:** la clave
de NVIDIA que tiene Bixente no es "de Kimi" — es universal, da acceso a 81
modelos del catálogo de Build by NVIDIA con la misma clave.

---

## B. Por qué no puede ser "todo en la web pública de Sagarde"

Comprobado el 14/09/2026: el repositorio `bixente-69/centro-mando-sagarde`
es **público** (`gh repo view` → `"visibility":"PUBLIC"`), y se publica
literalmente con `git push` a `main` vía `Actualizar_Sagarde.bat`. Cualquier
cosa en ese repo —incluido código JavaScript "escondido" en un HTML— es
visible para cualquiera en internet, y hay programas automáticos que
rastrean GitHub buscando claves de API filtradas. Además, varios libros de
PROYECTO ELECTRICO parecen manuales con autor/editorial (no solo normativa
pública tipo BOE), así que tampoco deben subirse completos a un repo
público.

Por eso la clave y el contenido de los libros viven en un sitio aparte,
privado, y la web pública de Sagarde solo habla con ese sitio — nunca
directamente con NVIDIA ni con los PDFs.

---

## C. Arquitectura — 3 piezas independientes

1. **Indexador** (Python, se ejecuta en el PC de Bixente, de vez en cuando —
   cuando añade libros nuevos). Lee los PDFs de PROYECTO ELECTRICO (mismo
   truco `page.chars` que ya usa el patrón Quiz App para evitar problemas de
   encoding), los trocea en fragmentos manejables, y genera un embedding de
   cada fragmento con `nvidia/nemotron-3-embed-1b`. Sube el índice resultante
   al almacén privado de Cloudflare (pieza 2).
2. **El ayudante privado** (Cloudflare Worker, JavaScript). Guarda en
   privado: la clave de NVIDIA, una contraseña propia de acceso (distinta de
   la clave de NVIDIA), y el índice de embeddings. Expone un único endpoint:
   recibe una pregunta + la contraseña, verifica la contraseña, embebe la
   pregunta, busca los fragmentos de libro más parecidos, se los pasa al
   modelo de chat (`openai/gpt-oss-20b`, el verificado fiable el 14/09/2026 —
   si al implementar esto ha pasado mucho tiempo, re-comprobar con
   `--list-models` antes de asumir que sigue disponible, igual que con
   cualquier otro modelo de este catálogo) junto con la pregunta, y devuelve
   la respuesta.
3. **La pestaña en Sagarde** (`VARIOS/BUSCADOR ELECTRICO/`, HTML autocontenido
   siguiendo el mismo estilo visual que `VARIOS/TIERRAS/app_informe_tierras.html`
   — cabecera `#1a3a5c`, tipografía Inter, tarjetas redondeadas, sin
   frameworks nuevos). Una caja de texto, un botón, la respuesta debajo.
   Guarda la contraseña propia en `localStorage` del navegador tras
   introducirla una vez por dispositivo. Habla solo con la pieza 2.

---

## D. Dónde vive cada dato

| Dato | Dónde | ¿En el repo público? |
|---|---|---|
| PDFs originales | `PROYECTO ELECTRICO` (sin mover ni tocar) | No, ni falta que hace |
| Índice de embeddings | Almacén privado de Cloudflare (R2 o KV — se decide en la fase de planificación según el tamaño real del índice una vez generado, no antes) | **No** |
| Clave de NVIDIA | Variable de entorno del Worker de Cloudflare | **No** |
| Contraseña propia de acceso | Variable de entorno del Worker + `localStorage` del navegador | **No** (el valor no; el hecho de que exista un campo de contraseña sí es visible, es normal) |
| Página de la pestaña (HTML/CSS/JS de interfaz) | `VARIOS/BUSCADOR ELECTRICO/` en el repo de Sagarde | Sí — pero no contiene ningún secreto, solo la interfaz |

---

## E. Flujo de una pregunta

1. Bixente escribe la pregunta en la pestaña y pulsa el botón.
2. La pestaña manda la pregunta + la contraseña propia al Worker (HTTPS).
3. El Worker comprueba la contraseña. Si no coincide, responde "no
   autorizado" y para ahí.
4. El Worker convierte la pregunta en un embedding (misma familia de modelo
   que el índice, para que sean comparables).
5. El Worker busca en el índice los fragmentos de libro más parecidos a la
   pregunta.
6. El Worker arma un mensaje para la IA: la pregunta + los fragmentos
   encontrados + instrucciones de citar cuándo la respuesta viene de un
   libro y cuándo es conocimiento general.
7. El Worker llama a `openai/gpt-oss-20b` y devuelve la respuesta a la
   pestaña.
8. La pestaña la muestra.

---

## F. Seguridad — qué protege esto, y qué no promete

**Protege:**
- La clave de NVIDIA nunca sale del Worker ni pasa por el navegador.
- El contenido de los libros y el índice nunca se publican en el repo
  público — solo lo hace la interfaz, que no tiene secretos dentro.
- Una contraseña propia impide que un desconocido que encuentre la URL del
  Worker la use gratis a costa de Bixente.

**No promete (honestidad, no exageración):** ningún sistema conectado a
internet es invulnerable al 100%. Esto no es una caja fuerte bancaria: es un
nivel de protección razonable y estándar para una herramienta personal de
un solo usuario, sin datos de terceros ni dinero de por medio. El riesgo
real residual es bajo, pero no cero, y así se lo decimos a Bixente en vez de
prometer algo absoluto.

---

## G. Manejo de errores

- **NVIDIA no responde o tarda demasiado** (ya pasó hoy con un modelo
  saturado, `moonshotai/kimi-k3`): mensaje claro en español, nunca una
  pantalla en blanco ni un cuelgue silencioso. Un solo reintento automático
  como mucho.
- **No se encuentra nada relevante en los libros para la pregunta:**
  responder igualmente con conocimiento general de la IA, pero indicando
  explícitamente "esto no lo he encontrado en tus libros, es conocimiento
  general" — nunca fingir que una respuesta viene de la biblioteca cuando
  no es así (coherente con la norma de Sagarde de no inventar ni disfrazar
  datos).
- **Contraseña incorrecta o ausente:** rechazar sin dar pistas de cuál es la
  correcta.
- **Índice vacío o corrupto:** avisar explícitamente en vez de responder
  como si la biblioteca no existiera o estuviera vacía de verdad.

---

## H. Pruebas antes de dar esto por terminado

- Un juego de preguntas de prueba con respuesta conocida, sacadas de libros
  concretos de PROYECTO ELECTRICO, para comprobar que el sistema encuentra
  y cita el libro correcto (no solo que "responde algo").
- Prueba por mutación (igual que ya se hace en Sagarde): romper el índice o
  la contraseña a propósito y comprobar que el sistema avisa en vez de
  fallar en silencio o devolver una respuesta que parece correcta sin serlo.
- Verificación manual de extremo a extremo: una pregunta real, desde el PC y
  desde el móvil (con wifi y sin wifi de casa), antes de decir que está
  terminado.

---

## I. Nombre y ubicación

`VARIOS/BUSCADOR ELECTRICO/` dentro del repo de Sagarde — mismo patrón que
`VARIOS/TIERRAS/` y `VARIOS/BATERIAS DE CONDENSADORES/` (subproyecto
autocontenido con su propia raíz, exento de la norma `_SISTEMA` según el
propio CLAUDE.md de Sagarde, sección 8).

No confundir con `VARIOS/APPS SAGARDE/`, que es zona personal de Bixente
(nóminas, convenio) excluida del repositorio — nada que ver con esto.

---

## J. Fase 2 (no ahora — anotado para cuando llegue el momento)

Memoria de conversación / preguntas de seguimiento tipo chat ("¿y para
trifásico?"). Bixente pidió explícitamente que se le recuerde esta opción
en cuanto la Fase 1 demuestre que merece la pena — no hace falta que lo
vuelva a pedir él, el recordatorio es responsabilidad de quien retome esto.

---

## K. Cómo se ejecuta esto — importante, léase antes de tocar nada

A diferencia de otras specs de este repo, **este proyecto NO se ejecuta en
modo autónomo de principio a fin.** Bixente ha insistido (14/09/2026, y
antes) en que es totalmente nuevo en programación y quiere ser guiado, no
que se le presenten cosas ya hechas de golpe. Parar siempre, sin excepción,
en estos puntos:

1. **Creación de la cuenta de Cloudflare.** Bixente la crea él mismo — nadie
   puede crear cuentas ni introducir contraseñas en su lugar. Quien ejecute
   esta fase debe guiarle **paso a paso, con capturas o instrucciones muy
   concretas**, sin dar por hecho que sabe dónde hacer clic. **Antes de que
   Bixente escriba ningún dato**, comprobar en la propia web de Cloudflare
   que el plan gratuito de Workers sigue sin pedir tarjeta de crédito ni
   tener cargos automáticos — si eso hubiera cambiado desde el 14/09/2026,
   parar y contarlo, no dar por buena esta suposición sin comprobarla.
2. **Antes de cualquier `git commit` o publicación en `main`** que afecte al
   repo público de Sagarde — confirmar explícitamente con Bixente antes,
   aunque parezca un cambio trivial (recordar: `Actualizar_Sagarde.bat`
   publica automáticamente todo lo que haya en disco).
3. **Cualquier ambigüedad real**, o cualquier decisión de coste o cuenta
   nueva no cubierta ya en este documento.

Fuera de esos tres puntos, se puede avanzar con normalidad, tarea por tarea,
con revisión entre cada una (`superpowers:subagent-driven-development`,
como marca el CLAUDE.md de Sagarde, sección 5).

---

## L. Ya verificado — para no repetir trabajo

- `nvidia/nemotron-3-embed-1b` genera embeddings correctamente para esta
  cuenta (2048 dimensiones, ~0.3s). Otros modelos de embeddings probados
  (`nvidia/embed-qa-4`, `nvidia/nv-embedqa-mistral-7b-v2`,
  `snowflake/arctic-embed-l`) dan 404 "not found for account" — no
  reintentarlos sin comprobar antes con `--list-models`.
- `openai/gpt-oss-20b` responde rápido y fiable (~2s) como modelo de chat.
  `moonshotai/kimi-k3` y `deepseek-ai/deepseek-v4-flash-0731` no respondieron
  en las pruebas del 14/09/2026 (probable saturación puntual de NVIDIA).
- `APLICACIONES/index.html` está vacío — no es un patrón real a seguir.
- El catálogo de skills de NVIDIA (`build.nvidia.com/skills`) no aplica
  aquí: es infraestructura de nivel empresarial (CUDA, Omniverse, DeepStream,
  cuOpt...), no encaja con una herramienta personal de un solo usuario.
