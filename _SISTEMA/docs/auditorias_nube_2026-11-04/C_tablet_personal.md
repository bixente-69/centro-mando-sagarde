# Auditoría C — App de tablet «Personal en obra» (control horario)

**Fecha:** 04/11/2026 · **Alcance:** solo lectura. No se ha modificado código ni datos del repo, no se ha lanzado `Actualizar_Sagarde.bat` ni se ha publicado nada en `main`.
**Nombres:** todos los nombres de este informe (Trabajador A/B/C, Empresa X/Y) son inventados. No se ha copiado ningún dato personal.

Ficheros revisados (rutas bajo `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/`): `generador_personal.html` (4565 líneas), `personal_sw.js`, `personal_manifest.json`, `personal_calculo.js`, `personal_obra.py`, `lector_control_horario.py`, y de refuerzo `personal_integracion.py` (auditor) y `lectores.py`.

---

## 0. Cómo se ha verificado (y qué no)

| Qué | Resultado real |
|---|---|
| Pruebas JS del repo (`node`, v22): `tests/verificar_personal_base.js`, `verificar_personal_calculo.js`, `verificar_personal_empresas.js` | **0 fallos** en las tres (60, 111 y 84 comprobaciones; cada una se repite en `Pacific/Auckland` y `America/Los_Angeles`). Código de salida 0. |
| Reproducción de los fallos de la tablet | Chromium real (Playwright de Node) contra **una copia** de la app en el directorio temporal de la sesión, con un estado inventado (sin datos reales). Cada fallo «verificado» abajo se ha visto ocurrir. |
| Reproducción de los fallos del lado Python | Árbol sintético (catálogo y obra inventados) en el directorio temporal, llamando al lector y a `personal_obra` reales. |
| Arreglos propuestos | Aplicados **solo a copias** y comprobados con la misma reproducción: el fallo desaparece. Los diffs de este informe son los de esas copias. |
| Pruebas Python existentes sobre las copias (con y sin los arreglos de Python) | Con los arreglos de Python + 3 líneas de ejemplo en `test_personal_obra_08a.py`: `test_lector_control_horario` (40), `test_personal_obra` (82), `test_personal_obra_08a` (78), `test_personal_mismo_nombre` (34), `test_personal_empresas_08c2a` (60), `test_personal_integracion_08a` (7), `test_personal_guardado_sin_pisar` (3): **todas OK**. |
| **No se pudo** | (a) Las pruebas de pantalla en Python (`verificar_generador_personal.py`, `test_personal_pantallas_ma6.py`, `test_personal_enviar_con_ma7.py`, `test_personal_sin_cobertura.py`) necesitan el paquete `playwright` de **Python**, que aquí no está. Los cambios propuestos en HTML/SW pueden afectar a lo que fijan (se indica en cada hallazgo). (b) `test_controles_horarios_08b`, `test_personal_integracion` y `test_lenguaje_electricista` ya **fallan igual sin ningún arreglo** al correrlas en una copia fuera del árbol real; no lo he investigado. (c) **Edge en Android**: no hay aparato; lo de «Enviar con…» es lectura de código + lo que dice la prueba MA7, no medición. |

**Distinción hecho / suposición:** «Verificado» = lo he visto ocurrir en ejecución. «Leído» = sale del código pero no lo he ejecutado. «Suposición» = lo digo sin poder comprobarlo aquí.

---

## 1. Resumen

| # | Gravedad | Hallazgo | Verificado |
|---|---|---|---|
| 1 | **Alta** | Dos pestañas/ventanas se pisan las jornadas pendientes (la segunda borra lo que guardó la primera) | Sí |
| 2 | Media-alta | App abierta de un día para otro: la fecha no cambia y guardar **sustituye en silencio** la jornada de ayer; además el borrador reabre en la fecha vieja | Sí |
| 3 | Media | Cambiar Viviendas↔Garajes, de día o de obra **tira sin avisar** lo marcado y no guardado | Sí |
| 4 | Media | «Copiar el último día» **desmarca y borra las horas** de lo que ya estaba marcado a mano | Sí |
| 5 | Media | El PC acepta «0 horas» sin avisar y lo cuenta como **día trabajado** (desconocido → cero) | Sí |
| 6 | Media (latente) | Una persona **de baja** que sale en una jornada entra sin avisar y sigue de baja; por `altas` sí se frena | Sí |
| 7 | Baja-media | «Anular» no comprueba que se haya guardado: con la memoria llena se pierde sin aviso | Sí |
| 8 | Baja-media | El service worker guarda cualquier respuesta 200 (portal cautivo) y deja la tablet sin cálculo sin cobertura | Sí |
| 9 | Baja | «Enviar con…» no funciona en Edge/Chrome de Android (Chromium no deja compartir `.json`); no pierde datos | Parcial (Chromium real no es Android) |
| 10 | Baja (latente) | Dos fichas vivas con el mismo nombre: el PC elige una en silencio (la última) | Sí |

Datos reales hoy (solo recuentos, sin nombres): 22 fichas vivas, **0** nombres repetidos, **0** bajas, **0** filas con 0 horas en las 4 obras con personal. Los hallazgos 5, 6 y 10 son **latentes**: no han ocurrido, pero nada los impide.

---

## 2. Hallazgos

### 1 · Dos pestañas se pisan las jornadas — **Alta** (verificado)

- **Dónde:** `generador_personal.html:1197` (`pending = get(K.p, [])` se lee **una sola vez** al cargar); escrituras que reescriben la lista **entera** desde esa memoria: `:1508` (`reconcile`), `:3443` (`guardarSinNadie`), `:3564` (`save`), `:4362` (anular), `:3063` (`renombrar`). No hay ningún `addEventListener('storage', …)` (la búsqueda de `storage` en minúscula da 0 resultados en todo el fichero).
- **Escenario:**
  1. Abrir la tablet en dos pestañas del mismo origen (visto así). *Suposición no comprobada:* en Edge de Android, la pestaña y la app instalada comparten el mismo `localStorage` y darían el mismo fallo. Las dos cargan `pending = []`.
  2. En la pestaña 1: guardar la jornada del lunes (Trabajador A). `localStorage` = {lunes}.
  3. En la pestaña 2 (sin recargar): guardar la del martes (Trabajador B). Escribe su memoria completa = {martes}.
  4. Resultado visto: `localStorage` = **{martes}**. El lunes ha desaparecido, sin aviso, y la pestaña 1 sigue enseñándolo hasta recargar.
- **Gravedad:** alta (pérdida silenciosa de trabajo ya guardado). La probabilidad depende de que haya dos contextos abiertos a la vez; es el «problema ya conocido».
- **Arreglo** (verificado: con él la pestaña 2 guarda {lunes, martes}). Cada pestaña relee lo que escribe la otra para que su próximo guardado parta de lo último. No se propone «mezclar al escribir» porque resucitaría días que se acaban de vaciar o anular. Queda un hueco de milisegundos (dos guardados simultáneos): `localStorage` no tiene transacciones.

```diff
--- a/generador_personal.html
+++ b/generador_personal.html
@@ -1089,6 +1089,25 @@
           localStorage.removeItem(k);
         } catch (e) {}
       }
+      // Otra pestaña, o la app instalada, ha escrito en este mismo aparato: se relee lo suyo para que el próximo
+      // guardado de ESTA pestaña parta de lo último y no pise sus jornadas (cada guardado reescribe la lista entera).
+      window.addEventListener('storage', (evento) => {
+        if (evento.storageArea !== localStorage || typeof iniciada === 'undefined' || !iniciada) return;
+        let lista = (clave) => {
+          let valor = get(clave, []);
+          return Array.isArray(valor) ? valor : [];
+        };
+        if (evento.key === K.p) pending = lista(K.p).filter((j) => jornadaOk(j));
+        else if (evento.key === K.n) news = lista(K.n).filter((x) => typeof x === 'string');
+        else if (evento.key === K.al) altas = lista(K.al).filter((x) => typeof x === 'string' && clean(x));
+        else if (evento.key === K.rn)
+          renombres = lista(K.rn).filter((r) => r && typeof r.de === 'string' && typeof r.a === 'string');
+        else if (evento.key === K.em)
+          empresas = lista(K.em).filter((e) => e && typeof e.nombre === 'string' && typeof e.empresa === 'string');
+        else return;
+        // No repinta si se está escribiendo en un campo: se perdería lo tecleado.
+        if (!/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement?.tagName || '')) render();
+      });
       // ---------------------------------------------------------------------------
       // Utilidades: funciones de formato, fechas, redondeo y validadores
       // ---------------------------------------------------------------------------
```

### 2 · La fecha «hoy» se queda congelada: sustituye en silencio el día de ayer — **Media-alta** (verificado)

- **Dónde:** `generador_personal.html:1281` (`fecha: today()` solo en el estado inicial; sin `visibilitychange`/`pageshow`/`focus` en todo el fichero); `:3385-3405` (`abierta`/`esLaAbierta` → `existente: null`: el día que se está viendo no cuenta como «ya hay gente»); `:1678-1694` (`restore()` reabre en la fecha del borrador).
- **Escenario A (app viva de un día para otro):**
  1. Martes por la tarde: se guarda el 03/11 (Trabajador A y B). La app queda en segundo plano.
  2. Miércoles: se abre la misma app (sigue en memoria), con **03/11** en pantalla. Se marca la cuadrilla de hoy (Trabajador C) y se pulsa Guardar.
  3. Visto: **no sale ningún aviso** y la jornada del 03/11 pasa de «A, B» a «C». La del miércoles no existe.
- **Escenario B (se cierra y se abre al día siguiente):** `restore()` abre en la fecha del borrador (03/11) con las marcas de ayer, sin decir nada. Aquí sí protege el aviso «ocupado» si el contenido difiere, pero la pantalla no explica por qué está en el día anterior. Visto con reloj simulado.
- **Gravedad:** media-alta. Corrompe un día ya guardado sin ruido; requiere dejar la app abierta de un día para otro, algo normal en una tablet.
- **Arreglo** (verificado: A pasa a pedir confirmación «ocupado» y no sustituye; B enseña «Se ha recuperado lo que dejaste a medias del mar 03/11. Hoy es mié 04/11.»). No cambia la fecha sola (Bixente carga días pasados a propósito): avisa y quita el «día abierto» como excepción.

```diff
@@ -4549,6 +4591,8 @@
         a.obra = obraPorDefecto();
         if (!restore()) loadList();
         render();
+        // Si lo que se recupera es de otro día, se dice (la pantalla abre en esa fecha, no en hoy).
+        if (a.fecha !== today()) toast('Se ha recuperado lo que dejaste a medias del ' + fdia(a.fecha) + '. Hoy es ' + fdia(today()) + '.');
         if (rotos > 0)
@@ -4558,6 +4602,21 @@
       // Arranque en carga de página y temporizador de seguridad de 4 s por si el script tarda en
       // responder
+      // Al volver a la app otro día, la fecha de la pantalla es la de antes: se avisa y el día que se estaba viendo
+      // deja de ser «el que se está corrigiendo» (así guardar encima de un día con gente vuelve a pedir confirmación).
+      let diaAbierto = today();
+      function avisarSiCambioElDia() {
+        if (!iniciada || today() === diaAbierto) return;
+        diaAbierto = today();
+        a.listaDe = null;
+        render();
+        toast('Ha cambiado el día. La fecha de la pantalla sigue siendo la de antes: elígela antes de guardar.');
+      }
+      document.addEventListener('visibilitychange', () => {
+        if (!document.hidden) avisarSiCambioElDia();
+      });
+      window.addEventListener('pageshow', avisarSiCambioElDia);
+      window.addEventListener('focus', avisarSiCambioElDia);
       window.addEventListener('load', () => setTimeout(init, 0));
```

### 3 · Cambiar de ámbito, día u obra tira lo marcado sin avisar — **Media** (verificado)

- **Dónde:** `:2940-2952` (`changed()` → `loadList()` reemplaza `a.list`, y `draft()` **sobrescribe el borrador** con la lista nueva); disparadores sin ninguna guarda: `:3959-3963` (Viviendas/Garajes), `:3991-4001` (día del calendario), `:4404-4408` (obra), `:4420-4431` (fecha).
- **Escenario:** en Viviendas se marcan 2 personas y **no** se pulsa Guardar; se toca «Garajes» (o un día del calendario, o la obra). Visto: 0 marcadas, 0 jornadas guardadas, borrador en disco con 0 marcadas. Volver atrás no las recupera. Además, **volver a pulsar el ámbito que ya está activo** (`datos.amb === a.amb`) también recarga la lista y tira las marcas (visto).
- **Gravedad:** media. Se pierde trabajo en curso (no guardado) en un gesto muy habitual (Viviendas ↔ Garajes cada día).
- **Arreglo** (verificado: con «no cambiar» se conservan las 2 marcas; con «cambiar» se descartan a propósito). Alternativa más cara y más robusta: un borrador **por** obra/ámbito/fecha en lugar de uno solo.
- **Ojo:** las pruebas de pantalla que cambian de ámbito con gente marcada necesitarán aceptar el diálogo (`page.on('dialog', …accept)`); no he podido correrlas.

```diff
@@ -2935,6 +2959,15 @@
+      // ¿Hay gente marcada en pantalla que no está guardada tal cual? Sirve para no tirarla al cambiar de ámbito, obra o día.
+      function hayMarcasSinGuardar() {
+        let marcados = a.list.filter((x) => x.on).map((x) => key(x.nombre)).sort();
+        if (!marcados.length) return false;
+        let guardada = jornadaGuardada();
+        let guardados = guardada ? guardada.nombres.map(key).sort() : [];
+        return JSON.stringify(marcados) !== JSON.stringify(guardados);
+      }
+      const AVISO_PERDER = 'Hay gente marcada que no has guardado. Si cambias, se pierde. ¿Cambiar de todas formas?';
       // Notifica un cambio en obra, ámbito o fecha: recarga la lista, guarda el borrador automático
@@ -3957,6 +3992,9 @@
         if (datos.amb) {
+          // Pulsar el ámbito en el que ya estás recargaba la lista y tiraba lo marcado: no hace nada.
+          if (datos.amb === a.amb) return;
+          if (hayMarcasSinGuardar() && !confirm(AVISO_PERDER)) return;
           a.amb = datos.amb;
@@ -3992,6 +4030,7 @@
             let mismo = dia === a.fecha;
+            if (!mismo && hayMarcasSinGuardar() && !confirm(AVISO_PERDER)) return;
             a.fecha = dia;
@@ -4402,6 +4443,7 @@
         if (campo.id === 'obra' || campo.id === 'obra-j') {
+          if (campo.value !== a.obra && hayMarcasSinGuardar() && !confirm(AVISO_PERDER)) return render();
           a.obra = campo.value;
@@ -4418,7 +4460,7 @@
         if (campo.id === 'fecha') {
-          if (!fechaOk(campo.value)) {
+          if (!fechaOk(campo.value) || (campo.value !== a.fecha && hayMarcasSinGuardar() && !confirm(AVISO_PERDER))) {
             render();
             return;
```

### 4 · «Copiar el último día» desmarca lo que ya estaba marcado — **Media** (verificado)

- **Dónde:** `generador_personal.html:1665`: `a.list = nombres.map((nombre) => ({ nombre, on: marcados.has(key(nombre)), horas: null }))`. El comentario de `:1651-1654` dice que «conserva los nombres», pero las **marcas y horas** de cada fila se recalculan solo desde el día anterior.
- **Escenario:** en el día nuevo se marca a Trabajador C a mano con 4 h; se pulsa «Copiar el último día» (el último día lo tenía A). Visto: C pasa a `on=false`, `horas=null`; A queda marcado. Una hora puesta a mano (media jornada, horario especial) se pierde sin aviso y, si C se vuelve a marcar, vuelve a 7,5 h.
- **Gravedad:** media. Es un dato escrito a mano que desaparece; las pruebas que he leído (`verificar_generador_personal.py` T1, T16, T201) parten de una lista **sin marcar** al pulsar, así que no protegen este caso.
- **Arreglo** (verificado: C se queda `on=true`, 4 h). El botón pasa a **añadir** marcas, no a repartirlas de nuevo. No he podido correr las pruebas de pantalla que lo rodean.

```diff
@@ -1662,7 +1681,12 @@
-        a.list = nombres.map((nombre) => ({ nombre, on: marcados.has(key(nombre)), horas: null }));
+        // Lo que ya estaba marcado a mano se queda como estaba (con sus horas): el último día solo AÑADE marcas.
+        a.list = nombres.map((nombre) => {
+          let ya = a.list.find((x) => key(x.nombre) === key(nombre));
+          if (ya && ya.on) return { nombre, on: true, horas: ya.horas };
+          return { nombre, on: marcados.has(key(nombre)), horas: null };
+        });
         a.prefill = anterior.fecha;
```

### 5 · «0 horas» entra sin avisar en el PC y cuenta como día trabajado — **Media** (verificado)

- **Dónde:** PC: `personal_obra.py:278-288` (`_num` acepta 0) y `:583-589` (`_norm` no lo trata como aviso); `:1514-1545` (`totales_control` suma el día aunque `horas == 0`); JS: `personal_calculo.js:64-80` (`clasificarFila` da 0 por `valida`). Tablet: lo permite **a propósito** con aviso (`:2244-2251`, y `verificar_generador_personal.py` T154: «si sigue lo guarda con 0 horas a la vista»).
- **Escenario:**
  1. «Varios días»: viernes y sábado, Trabajador A marcado sin tocar las horas. El sábado no tiene horario → `horasPersona = 0` (`:3366`). Sale el aviso «fin de semana / 0 horas»; la persona pulsa «Guardar así».
  2. El fichero lleva `horas: 0` el sábado. `lector_control_horario` lo marca **«listo»** sin ningún aviso (visto).
  3. Totales vistos (PC y JS, mismo resultado): A con 7,5 h el viernes y **0 h** el sábado → **2 días**, 7,5 h. Los «días» y lo que se derive de ellos (asistencia, ranking) suben con un día sin horas.
- **Por qué es el problema de este proyecto:** una hora **desconocida** (no se pusieron) se convierte en **cero** y se cuenta. Lo que digan las horas está bien (0 no suma); lo que se infla son los días.
- **Gravedad:** media. Hoy hay **0 filas con 0 h** en los datos reales, así que no ha ocurrido.
- **Arreglo** (verificado): el PC no lo deja pasar en silencio, sino que **frena el fichero para mirarlo** (como `fecha_futura` o `suma_diaria_alta`); si Bixente lo acepta a propósito, entra. No toca el criterio de la tablet (T154 lo fija). Si Bixente prefiere que 0 h **nunca** entre, la decisión es otra (rechazar en `_norm` y bloquear en la tablet); la dejo para él.
- **Aparte, una incoherencia menor en la misma pantalla (leída; solo ejecuté el caso con el viernes en pantalla):** `save()` solo comprueba «Faltan las horas» para la **fecha en pantalla** (`:3465-3469`), no para cada día de «Varios días», y la fecha en pantalla es la última pinchada (`:4010-4011`). Por código, pinchando viernes→sábado bloquea con «Faltan las horas» y pinchando sábado→viernes pasa y llega al aviso de 0 horas. No lo toco en el arreglo propuesto porque T154 fija el comportamiento; se lo dejo a Bixente.

```diff
--- a/personal_obra.py
+++ b/personal_obra.py
@@ -976,6 +987,9 @@
         # Aviso si alguien suma más de 12 h el mismo día (con sus nombres) o si la fecha aún no ha llegado.
+        ceros = sorted(mp[p["id"]]["nombre"] for p in presentes if p["horas"] == 0)
+        if ceros:
+            avisos.append({"codigo": "cero_horas", "detalle": ", ".join(ceros)})
         altos = sorted(mp[i]["nombre"] for i, horas in totales.items() if horas > 12)
@@ -1764,6 +1778,14 @@
         return f"Una persona cambia de empresa: todas sus horas ya apuntadas se contarán en la nueva. {otra}"
+    if codigo == "cero_horas":
+        return (f"Con 0 horas: {detalle}. Una persona apuntada sin horas cuenta como día trabajado: corrígelo en la "
+                "tablet, o acéptalo si es a propósito.")
     if codigo == "alta_ya_existia":
--- a/lector_control_horario.py
+++ b/lector_control_horario.py
@@ -43,6 +43,8 @@
     "alta_de_baja",
+    "cero_horas",
+    "presente_de_baja",
 )
```

(El `presente_de_baja` de esta lista es del hallazgo 6. Pruebas: ver «Housekeeping» al final del hallazgo 6.)

### 6 · Una persona de baja con jornada entra sin avisar y sigue de baja — **Media, latente** (verificado)

- **Dónde:** `personal_obra.py:920-948` (en `presentes`, el nombre se resuelve con `actuales[...]` aunque `activo is False`; no se mira `activo`), frente a `:734-744` (en `altas` sí: `alta_de_baja`, reactiva y **frena**).
- **Escenario:** Trabajador A figura de baja (`activo: false`). La tablet lo ofrece igualmente (`indiceNombres()` incluye todo el catálogo) y se le apunta una jornada. Visto: el fichero queda **«listo»**, la jornada se publica y A sigue `activo: false`; `comprobar` no dice nada. Con el mismo A en `altas` el fichero queda **«a revisar»** (`alta_de_baja`). Mismo nombre, dos caminos, dos respuestas.
- **Gravedad:** media por incoherencia (alguien «de baja» con horas nuevas, y sin la pregunta «¿es otra persona con el mismo nombre?» que el proyecto sí hace en `altas`). Latente: hoy 0 bajas.
- **Arreglo** (verificado: el fichero pasa a «a revisar» con `presente_de_baja`; al aceptarlo, A queda `activo: true` y su jornada entra; con ficha activa no cambia nada):

```diff
--- a/personal_obra.py
+++ b/personal_obra.py
@@ -916,6 +920,7 @@
         altas = []
+        reactivadas = []
         presentes = []
@@ -945,6 +950,12 @@
                 })
+            if mp[identificador].get("activo") is False:
+                # Alguien de baja con una jornada nueva: puede ser una vuelta o otra persona con el mismo nombre.
+                # Vuelve a la lista (como en `altas`) pero el lector frena el fichero para mirarlo.
+                mp[identificador]["activo"] = True
+                reactivadas.append(identificador)
+                avisos.append({"codigo": "presente_de_baja", "detalle": mp[identificador]["nombre"]})
             presentes.append({"id": identificador, "horas": p["horas"], "extra": p["extra"]})
@@ -1001,7 +1015,7 @@
             res["altas"] += altas
-            cambio_cat |= bool(altas)
+            cambio_cat |= bool(altas) or bool(reactivadas)
@@ -1764,6 +1778,9 @@
+    if codigo == "presente_de_baja":
+        return (f"«{detalle}» estaba de baja y sale en una jornada: vuelve a la lista. Si es otra persona con el mismo "
+                "nombre, hay que ponerle un apellido o una inicial.")
     if codigo == "alta_ya_existia":
```

**Housekeeping de las pruebas** (comprobado que con esto pasan las 7 suites de Python indicadas arriba): `tests/test_personal_obra_08a.py` exige que todo código que emite `personal_obra.py` tenga frase en `EJEMPLOS`/`RECHAZOS`:

```diff
--- a/tests/test_personal_obra_08a.py
+++ b/tests/test_personal_obra_08a.py
@@ -824,6 +824,12 @@
          'Si es otra persona con el mismo nombre, hay que ponerle un apellido o una inicial.'),
+        ('cero_horas', 'Mikel',
+         'Con 0 horas: Mikel. Una persona apuntada sin horas cuenta como día trabajado: corrígelo en la tablet, '
+         'o acéptalo si es a propósito.'),
+        ('presente_de_baja', 'Mikel',
+         '«Mikel» estaba de baja y sale en una jornada: vuelve a la lista. '
+         'Si es otra persona con el mismo nombre, hay que ponerle un apellido o una inicial.'),
         # MA5: los de oficios, horarios preferidos y bajas ya tenían su frase en P1, pero esta lista no los recorría
@@ -831,6 +837,7 @@
     RECHAZOS = {
+        'catalogo_con_nombres_repetidos': 'En la base hay dos personas con el mismo nombre: no se aplica nada hasta juntarlas o ponerles apellido.',
         'baja_invalida': 'Un nombre de la lista de personas a quitar viene mal escrito.',
```

### 7 · «Anular» no comprueba que se haya guardado — **Baja-media** (verificado)

- **Dónde:** `generador_personal.html:4352-4366`: `set(K.p, pending)` sin mirar el resultado; `render()` enseña la jornada como anulada.
- **Escenario:** el aparato rechaza escrituras (memoria llena o navegación privada). Se anula una jornada: en pantalla queda anulada (memoria `anulada=true`), en disco sigue `anulada=false`, y **no sale ningún aviso**. Al cerrar la app la anulación se pierde y la jornada vuelve. Los demás caminos (`save`, `guardarSinNadie`, `renombrar`…) sí avisan con «No se pudo guardar en este aparato…».
- **Misma familia, sin reproducir (leído):** `:1217-1219` borra de las pendientes las jornadas ilegibles aunque `set(K.r, …)` (donde se «apartan») falle. Solo afecta a datos que ya no se pueden leer.
- **Gravedad:** baja-media (exige almacenamiento roto), pero es exactamente «algo que se declara y no tiene efecto».
- **Arreglo** (verificado: sale «No se pudo guardar la anulación en este aparato (¿memoria llena?)…»):

```diff
@@ -4359,9 +4398,11 @@
           pending.push(jornada);
-          set(K.p, pending);
+          let anuladaGuardada = set(K.p, pending);
           a.confirm = null;
           render();
+          if (!anuladaGuardada)
+            toast('No se pudo guardar la anulación en este aparato (¿memoria llena?). Envía ya las jornadas al PC.');
           return;
```

### 8 · El service worker guarda cualquier 200 (portal cautivo) — **Baja-media** (verificado)

- **Dónde:** `personal_sw.js:18-27` (`guardarDesdeRed`), `:62-73` (`guardarRespuesta`), `:121` (`responder`): solo miran `respuesta.ok`.
- **Escenario:** con wifi de pago/obra con portal cautivo, la red contesta **200 con la página del portal** en lugar de `personal_calculo.js`. El SW la guarda como si fuera el cálculo. Al perder cobertura, la tablet abre «desde copia» pero con `PersonalCalculo` **indefinido** (visto: `typeof PersonalCalculo === 'undefined'`) y la app no funciona hasta volver a tener cobertura y una carga buena que la reescriba.
- **Gravedad:** baja-media. No pierde datos (las jornadas siguen en `localStorage`), pero deja la tablet inútil justo sin cobertura.
- **Arreglo** (verificado: tras portal cautivo y luego sin cobertura, `PersonalCalculo` sigue definido; la app abre en ~50 ms desde copia). Sube `VERSION` a `v2` por la norma de la skill; **ojo:** `tests/test_personal_sin_cobertura.py` fija `sgd-personal-v1` en las líneas 457 y 543: habría que actualizarlo a `v2`.

```diff
--- a/personal_sw.js
+++ b/personal_sw.js
@@ -1,4 +1,4 @@
-const VERSION = 'v1';
+const VERSION = 'v2';
@@ -15,10 +15,20 @@
   return url.href;
 }
 
+// ¿Vale esta respuesta como copia de la app? Un portal cautivo (wifi de pago, hotel) contesta 200 con su propia
+// página en vez de nuestro fichero: si se guardara, la tablet se quedaría sin cálculo hasta volver a tener cobertura.
+function esUtil(url, respuesta) {
+  if (!respuesta.ok || respuesta.redirected) {
+    return false;
+  }
+  const tipo = (respuesta.headers.get('Content-Type') || '').toLowerCase();
+  return url === PAGINA ? tipo.includes('text/html') : tipo.includes('javascript');
+}
+
 async function guardarDesdeRed(cache, url) {
   try {
     const respuesta = await fetch(url, { cache: 'no-cache' });
-    if (respuesta.ok) {
+    if (esUtil(url, respuesta)) {
       await cache.put(url, respuesta);
@@ -60,7 +70,7 @@
 async function guardarRespuesta(clave, respuesta) {
-  if (!respuesta.ok) {
+  if (!esUtil(clave, respuesta)) {
     return;
@@ -118,7 +128,7 @@
-  if (primero.tipo === 'red' && primero.respuesta.ok) {
+  if (primero.tipo === 'red' && esUtil(clave, primero.respuesta)) {
     return primero.respuesta;
```

### 9 · «Enviar con…» en Edge/Chrome de Android — **Baja** (parcial: sin aparato)

- **Hechos leídos:** `generador_personal.html:3842-3843` comparte un `File` `*.json` de tipo `application/json`; `:3846-3853` y `:3861-3878` ocultan el botón si `canShare` falla y, si `share()` rechaza con `NotAllowedError`, enseñan «Este aparato no deja pasar este fichero…» y **esconden el botón 30 días** (`:3933`, `:3899-3902`). La prueba `test_personal_enviar_con_ma7.py` (cabecera) dice, citando la lista de Chromium `FILE_TYPES.md`, que **Chrome no admite `.json`** en la hoja de compartir. Edge para Android es Chromium. **No he podido consultar esa lista desde aquí; es lo que dice la prueba**.
- **Conclusión (suposición razonable, no medida):** en el Edge de Bixente el botón o no sale o falla al primer toque y se esconde un mes. **No pierde nada**: «Preparar el fichero para el PC» descarga el mismo fichero (`:3818-3833`). Verificado en Chromium de escritorio: baja `CONTROL HORARIO OBRA A 04112026.json` (fecha en DDMMAAAA) y el lector real de Python lo clasifica **«listo»** («1 jornada de viviendas»), es decir, el contrato tablet→PC de extremo a extremo funciona.
- **Matiz:** `NotAllowedError` también salta si caduca la activación del usuario; hoy eso también esconde el botón 30 días.
- **Arreglo propuesto (SIN verificar en Edge Android):** compartir el mismo contenido como **texto** con el nombre `…​.json.txt` (Chromium sí admite texto) y que el PC lea `.json.txt` igual que `.json`. Lo verificado de esta propuesta es **solo el lado PC** (`es_control_horario('CONTROL HORARIO X 04112026 (1).json.txt')` es verdadero y la fecha/copia se leen bien). Antes de adoptarlo: **2 minutos de prueba en el aparato** (abrir la tablet en Edge, «Enviar con…», comprobar que llega a OneDrive/REVISIONES). Si no funciona, lo honesto es quitar el botón en Chromium/Android y dejar solo «Preparar…». La prueba MA7 fija `.json` y `application/json`; habría que cambiarla.

```diff
--- a/generador_personal.html
+++ b/generador_personal.html
@@ -3840,7 +3873,9 @@
       function archivoParaCompartir(ClaseFile, nombre, texto) {
-        return new ClaseFile([texto], nombre + '.json', { type: 'application/json' });
+        // Chromium (Edge/Chrome en Android) no deja compartir .json: se comparte como texto, con el mismo nombre + «.txt».
+        // El lector del PC reconoce «.json.txt» igual que «.json».
+        return new ClaseFile([texto], nombre + '.json.txt', { type: 'text/plain' });
       }
--- a/lector_control_horario.py
+++ b/lector_control_horario.py
@@ -68,7 +70,7 @@
-_FECHA_NOMBRE = re.compile(r"(\d{2})(\d{2})(\d{4})(?:\s*\((\d+)\))?\s*\.json$", re.I)
+_FECHA_NOMBRE = re.compile(r"(\d{2})(\d{2})(\d{4})(?:\s*\((\d+)\))?\s*\.json(?:\.txt)?$", re.I)
@@ -133,7 +135,7 @@
-        and minuscula.endswith(".json")
+        and (minuscula.endswith(".json") or minuscula.endswith(".json.txt"))
```

(`es_control_horario` es la regla única: la usan `listar` y `lectores.py:235-246`, así que no hay que tocar nada más para que `REVISIONES` ignore el `.json.txt` como documento de obra.)

### 10 · Dos fichas vivas con el mismo nombre: el PC elige una en silencio — **Baja, latente** (verificado)

- **Dónde:** `personal_obra.py:419-429` (`_indices_nombres`: `actuales[clave] = vigente` → **gana la última**). `comprobar` (`:1666-1667`) sí detecta «nombres no fusionados duplicados», pero solo en el auditor del `.bat`, no al aplicar.
- **Escenario:** el catálogo trae (dato heredado o editado a mano) dos fichas vivas «Trabajador A», empresa X y empresa Y. Llega una jornada con «Trabajador A». Visto: el fichero queda **«listo»**, la fila sale con la **empresa Y** (la última); nada avisa en ese momento (`comprobar` sí lo diría después).
- **Por qué no es peor:** por las vías normales no se pueden crear duplicados (`_buscar_nombre` antes de `_persona_nueva`, `_aplicar_renombre` rechaza `coincide_con_otro`, la tablet pregunta por el homónimo). Hoy hay **0** duplicados. Y el caso «mismo nombre en otra empresa» desde la tablet **sí** frena: `empresa_cambiada` (visto en el lector: `a_revisar`).
- **Arreglo** (verificado: con duplicados el lote queda «rechazado» con la frase `catalogo_con_nombres_repetidos`). Efecto a conocer: como el catálogo es global, **frena la entrada de personal de todas las obras** hasta que se junten o se les ponga apellido (lo mismo que ya hace el auditor antes de publicar).

```diff
--- a/personal_obra.py
+++ b/personal_obra.py
@@ -656,6 +656,10 @@
         ods = copy.deepcopy(estado["ods"])
+    vivos = Counter(clave_nombre(t["nombre"]) for t in cat["trabajadores"] if t.get("fusionado_en") is None)
+    if any(v > 1 for v in vivos.values()):
+        res.update({"ok": False, "lote_rechazado": ["catalogo_con_nombres_repetidos"]})
+        return res
     od = (
@@ -1764,6 +1778,9 @@
+    if codigo == "catalogo_con_nombres_repetidos":
+        return "En la base hay dos personas con el mismo nombre: no se aplica nada hasta juntarlas o ponerles apellido."
     if codigo == "alta_ya_existia":
```

---

## 3. Descartados o dudosos (y por qué)

| Candidato | Veredicto |
|---|---|
| **«Quitar la empresa» no frena el fichero** (`empresas` con `empresa: ""`: la persona se queda sin empresa, visto «listo») | **Descartado: decisión de diseño.** La spec `2026-10-30-personal-misma-persona-mismo-nombre-design.md` §6.1 dice que `empresa_cambiada` no sale en `quitada`, y `test_personal_mismo_nombre.py::test_quitar_la_empresa_no_frena` lo fija. Queda en la traza (`de`/`a`), así que es recuperable. Mi parche lo frenaba y esa prueba falló: lo retiré. |
| **`VERSION` del service worker sin subir** | **Descartado como fallo.** Solo hay un commit de `personal_sw.js` (`v1`). Las tres piezas (página, cálculo, estado) van por **red primero** y se reescriben en cada carga buena, así que la caché no queda vieja aunque no se suba. La `VERSION` solo sirve para borrar cachés antiguas. Nada obliga a subirla (la prueba solo comprueba que subirla limpia la anterior). Si se aplica el hallazgo 8, súbase a `v2` y actualícese la prueba. |
| **La app no abre sin cobertura** | **Descartado: funciona.** Verificado con SW real: primera visita → caché `sgd-personal-v1` con las 3 piezas → sin red, abre en ~50 ms con «Se usa la lista guardada en este aparato» y el botón Guardar presente. Requisito conocido: abrirla una vez con cobertura. |
| **Fechas: zona horaria, cambio de hora, medianoche, DDMMAAAA, 30 de febrero** | **Sin fallo.** `add/dow/fechaOk` probadas día a día en 2026-2027 en `Europe/Madrid`, `Atlantic/Canary` y `UTC` (730 días, 0 fallos, el 30/02 se rechaza). Las pruebas del repo repiten en Auckland y Los Ángeles. DDMMAAAA: `nombreFichero` (`:3653-3656`) y `_FECHA_NOMBRE` coinciden. Lo que sí falla en medianoche es la fecha congelada (hallazgo 2). Días futuros: tablet avisa (`futuro`) y el PC frena (`fecha_futura`). Fines de semana: avisa la tablet; el PC no tiene regla (correcto, el fichero lleva horas explícitas). |
| **Cuota de `localStorage` llena** | **No es riesgo a corto plazo.** La copia del estado pesa hoy **~31 KB** (`personal_estado.js`); extrapolando unas ~100 B por fila y ~13.000 filas al año (suposición mía) serían ~1,3 MB/año frente a ~5 M de caracteres de cuota. `set()` devuelve `false` y la mayoría de caminos avisan (la excepción es el hallazgo 7). Endurecimiento opcional de una línea (no verificado): pedir `navigator.storage.persist()` al iniciar para que el navegador no borre los datos de la tablet si se queda sin espacio; hoy no se pide (`grep navigator.storage` = nada). |
| **Notas libres con teléfono entran en el lote** (`_norm` no revisa `notas`; visto «listo») | **Descartado:** el auditor del `.bat` busca DNI/teléfono/correo en el **texto crudo** de `personal_obra.json` y la traza (`personal_integracion.py:74-80, 405-440`) y bloquea la publicación. Llega tarde (después de aplicar en local) pero llega. La tablet siempre manda `notas: ''`. |
| **Orden de aplicación por la fecha del nombre**: un fichero sin `DDMMAAAA` (p. ej. conflicto de OneDrive «…-PC.json») se aplica **primero** (visto `(None, 0)`) | **Acotado:** cualquier jornada que sustituya a otra distinta queda «a revisar» (`reemplazo`, visto), y los duplicados idénticos se descartan por SHA256. |
| **Escritura no transaccional** (`guardar_catalogo` → `_saveobra` → traza) y **dos procesos a la vez** sin bloqueo | **Leído, no reproducido.** Un corte a medias es seguro: sin SHA en la traza el fichero se vuelve a ofrecer y es idempotente. Dos procesos a la vez (p. ej. «actualiza la obra» y `generar_todos`) sí podrían pisarse el catálogo: ya lo avisa `CLAUDE.md` (§5); no he intentado provocarlo. |
| **Mismo nombre en dos empresas desde la tablet** | **Cubierto en lo normal:** la tablet pregunta (`clasificarNombreEscrito`), el PC trata el nombre como identidad y frena `empresa_cambiada` (visto). Lo que queda es el caso heredado del hallazgo 10. |
| **Campos vacíos / «desconocido no es cero»** | Bien en lo general: `horas` ausente o no numérica → `horas_invalidas` (rechaza, no pone 0); `nombre` vacío → `nombre_vacio`; `ambito`/`fecha` mal → rechazo de esa jornada sin tumbar el resto. Excepciones: la de 0 horas (hallazgo 5) y `extra` ausente = 0 (aceptable: la tablet siempre lo manda). |

---

## 4. Respuesta directa a los cinco puntos del encargo

1. **Pérdida de datos:** hallazgos 1 (alta), 2, 3, 4 y 7. Lo que **no** pierde: enviar el fichero (las jornadas siguen pendientes hasta que el estado publicado las iguala) ni guardar con la memoria llena (avisa, salvo «anular»).
2. **Fechas:** sin fallo de zona horaria/cambio de hora/DDMMAAAA. Fallo real: fecha congelada de un día para otro (hallazgo 2). 0 horas: hallazgo 5.
3. **Edge Android, «Enviar con…»:** hallazgo 9 (probable, sin aparato). No pierde datos.
4. **Service worker:** abre sin cobertura (verificado). `VERSION` no es un riesgo hoy. Fallo real: portal cautivo (hallazgo 8).
5. **Lado Python:** mismo nombre en dos empresas (frena si hay conflicto de empresa; latente si hay duplicados heredados: hallazgo 10); bajas reactivadas (hallazgo 6: por `altas` frena, por jornada no); campos vacíos (bien salvo 0 horas: hallazgo 5).

## 5. Orden sugerido si se aplican

1 → 2 → 3/4 (tablet, mismo fichero; se prueban juntas) → 5/6/10 (Python + 3 líneas de prueba) → 8 → 7 → 9 (solo tras probar en el aparato). Todos los diffs de arriba son de **copias** de trabajo, no del repo; ninguno está aplicado. Al aplicar los de tablet: `verificar_generador_personal.py` y las pruebas MA6/MA7/sin cobertura deben pasarse con `playwright` de Python (aquí no estaba).
