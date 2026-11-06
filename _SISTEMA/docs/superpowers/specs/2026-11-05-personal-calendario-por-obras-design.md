# Personal en obra — Calendario por obras (05/11/2026)

**Estado:** implementado y verificado en la rama `personal-calendario-obras` (sin fusionar ni publicar). Aprobado en la
conversación del 05/11/2026 con la respuesta «Primero lo seguro» de Bixente.

## Petición (Bixente, 05/11/2026)

> «Creo necesario un sitio donde poder ver un calendario en grande, de manera que, como ya hacemos, vea qué días tienen
> registro, pero este, a diferencia del otro, me va a decir **qué obras** son las que tienen registro ese día. Por norma
> general deberían tenerlo todas las que siguen el control digital. En esa lista, que puede ser un desplegable si es más de
> una, yendo a la correspondiente veo los que han estado en esa obra ese día.»

## Qué es

Una pestaña nueva, **«Calendario»**, en la página de Sagarde del portal (`personal_sagarde.html`, junto a Ranking, Base de
trabajadores, Empresas y Generar personal; se abre también con `#calendario`). **No es una app suelta ni lleva datos propios**
(regla del 25/10/2026): lee el mismo `personal_estado.js` que el ranking y la tablet, que ya trae todas las jornadas de todas las
obras. Es de solo lectura.

- **Rejilla del mes en grande**, semanas completas de lunes a domingo. Cada día enseña `n/m` (obras con registro entre las que
  debían tenerlo) y, en pantalla ancha, el nombre corto de cada obra (`BOLUETA`, `OLABEAGA`…). Se mueve con ‹ › y «Hoy».
- **Tres colores, siempre con el número al lado** (el color solo no basta): verde = todas las obras con registro; ámbar = falta
  alguna; borde discontinuo = ninguna obra con registro en un día laborable.
- **Al pinchar un día:** cuántas obras tienen registro; si hay más de una, un **desplegable de obras**; al elegir una, la tabla
  de quién estuvo (nombre con su empresa debajo, zona —Viviendas/Garajes— y horas); y una línea ámbar «Sin registro este día:
  …» con las obras que faltan.
- **Móvil:** casillas pequeñas con solo el recuento; el detalle sale en tarjetas.

## Qué obras «debían» tener registro (decisión mía, sin confirmar con Bixente — ver «Abierto»)

Una obra se exige en un día solo si: está **abierta**; el día es **laborable** (lunes a viernes); es **anterior a hoy** (hoy aún
se puede estar anotando); y es **igual o posterior a su primer día con registro** (una obra que empezó el 04/11 no «falta» el
02/11). Una obra abierta que nunca tuvo jornadas (Gorliz) no se exige nunca. Los fines de semana con registro cuentan como
completos; sin registro, quedan vacíos y no acusan a nadie. Las obras cerradas con jornadas salen en los días en que las tuvieron.
**Un dato que falta no es 0:** unas horas sin dato salen como «–» y el total del día-obra dice «hay jornadas sin horas».

## Dónde vive cada cosa

| Qué | Dónde |
|---|---|
| Cálculo (UNA sola implementación) | `personal_calculo.js` → `calendarioMes(filas, {anio, mes, obrasAbiertas, hoy})` |
| Dibujo (no decide nada) | `personal_sagarde.html` → sección `PESTAÑA: CALENDARIO` (`pintarCalendario`, `detalleCalendario`…) |
| Verificador del cálculo (cifras a mano, 3 zonas horarias) | `tests/verificar_personal_calendario.js` (en la lista blanca del `.gitignore`) |
| Verificador del navegador (contra un cálculo independiente en Python) | `tests/verificar_calendario_obras.py` |
| Lanzador con el resto de la suite | `tests/test_calendario_obras.py` |

## Lo que cumple y cómo se probó

- Pruebas primero: el verificador de `node` se escribió antes de la función y falló como debía.
- **Por mutación** (regla del proyecto): el cálculo con 22 mutaciones y la página con 33; las que sobrevivieron destaparon
  huecos de los verificadores, que se cerraron (anotado en la memoria del proyecto).
- La página no repite la regla de «obras esperadas» (una prueba lo vigila) y no guarda ni descarga nada.
- Todo texto que pega datos en la página pasa por `escaparHtml` (hay una escena con un nombre `<img onerror>` que no se ejecuta).
- Ningún texto de la pestaña lleva palabras de programador (`test_lenguaje_electricista.palabras_prohibidas`).
- Verificado con los datos reales publicados el 05/11/2026 en escritorio (1100 px) y móvil (390 px): sin errores de consola.
- Suite completa del motor en la rama (05/11/2026): 2.042 pruebas, 1 error —`TestCasoRealMungia`, ambiental: lee un fichero real de
  Mungia que no está en git y por eso no existe en el worktree; comprobado que existe en el árbol real—, 6 saltadas a propósito.

## Interconexión con la app de jornada (06/11/2026)

Petición de Bixente (06/11/2026): «pincho en el día 3, para ver quién estuvo en obra, y no me hace nada»; «los enlaces tienen que
ser al pinchar el día: si está vacío, poder generar; si ya tiene, poder generar o editar alguno de los que están; y al revés, desde
el generador poder pinchar el calendario… sin que haya más calendarios en generar que puedan ocasionar líos».

- **El detalle del día se ve.** Sale al lado del calendario (pantalla de 1.000 px o más); en pantalla estrecha se desplaza solo a la
  vista y trae «↑ Volver al calendario». Antes salía debajo, fuera de pantalla, y parecía que no hacía nada.
- **«Anotar este día».** Cada obra abierta con su botón: **Editar** si ese día tiene registro (uno por zona si tiene viviendas y
  garajes) o **Generar** si no (también en días futuros). Las obras cerradas con registro ese día salen sin botón («obra cerrada»):
  la app solo trabaja con las abiertas.
- **Ida: calendario → app.** El botón abre `generador_personal.html#obra=<id>&fecha=AAAA-MM-DD[&amb=vivienda|garaje]` (el id va
  codificado). La app solo acepta valores válidos —obra abierta, fecha que existe, zona conocida—; lo demás se ignora. Enseña lo
  guardado de ese día y deja la dirección limpia. **Nunca pisa una jornada a medias:** si hay alguien marcado que no coincide con lo
  guardado, avisa y no cambia nada. También funciona con la app ya abierta.
- **Vuelta: app → calendario.** La app lleva, en la misma fila que la fecha, el enlace corto «📅 Calendario ›» (nombre completo: «Calendario y ranking de todas las obras»), que abre
  `personal_sagarde.html#calendario&dia=AAAA-MM-DD` (calendario con ese día elegido; una fecha que no existe se ignora). La cabecera
  de la página de Sagarde lleva «✎ Anotar la jornada en la app de la tablet ›».
- **Limitación conocida:** la página de Sagarde necesita internet; la app de jornada funciona sin cobertura (su *service worker*
  solo cubre `generador_personal.html`). Sin cobertura, el enlace al calendario no abre.
- **Decidido por Bixente (06/11/2026, «Solo Varios días»):** el calendario propio de la app solo sale con «Varios días» (marcar su
  semana entera de golpe), que además funciona sin internet. Sin «Varios días» no hay calendario en la app: el día se elige con el
  campo de la fecha (con un rótulo que lo dice con palabras: «Fecha: Hoy · viernes 23/10») o desde el calendario de Sagarde, y en la
  misma fila de la fecha va el enlace corto «📅 Calendario ›». Con «Varios días» el calendario sale siempre abierto, debajo de los
  botones «Copiar el último día» / «Varios días» (el botón no se mueve al encenderlo). Se descartaron quitarlo del todo (la semana
  entera habría que marcarla con internet) y sustituirlo por una tira de la semana.
- **Pruebas:** escenas 11–16 de `tests/verificar_calendario_obras.py` (721 comprobaciones, con el recorrido de ida y vuelta entre
  las dos páginas) y T246–T254 de `tests/verificar_generador_personal.py`. **Por mutación:** página 17 (16 detectadas; la que queda es
  equivalente: el escapado se aplica sobre una dirección que ya va codificada con `encodeURIComponent`, no hay valor que lo distinga) y
  app 15 (15 detectadas; dos sobrevivieron al principio —aceptar cualquier obra o cualquier zona— porque el desplegable de obras
  enseña la primera de la lista cuando el valor no existe, así que T250 mira también el estado interno y lo que se guarda en el aparato).

## Abierto (decisiones de Bixente)

1. **¿Qué obras se exigen?** (**Resuelto el 05/11/2026**) Todas las abiertas desde su primer registro. En los datos reales eso
   marca **Mungia** como «falta» desde el 02/11 (sus últimos registros son del 27–29/10); Bixente confirmó que Mungia **sigue con
   control horario** («Sí, que falte»), así que es correcto. Si una obra deja de seguirse, la forma limpia de dejar de exigirla
   es **cerrarla** (`sagarde-cerrar-obra`); si hiciera falta «pausar» sin cerrar, sería otra decisión.
2. **Días festivos**: no se conocen; un festivo entre semana sale como «ninguna obra» (ámbar discontinuo), que es un aviso, no
   una acusación. Si estorba, se podría añadir una lista de festivos.
3. El calendario solo refleja lo **ya aplicado**: un control horario que está en `REVISIONES` sin aplicar no sale hasta
   «actualiza la obra» o el `.bat` (hoy pasa con Olabeaga 04–05/11 y Mungia 05/11).

## Fuera de esta pieza (siguen abiertos, ver la memoria del proyecto)

Hecho después, el 05/11/2026 (ver la memoria del proyecto): arreglo de las pestañas de la tablet que se pisan, nombre del aparato en
cada fichero y aviso con las horas en el PC (decidido «solo avisar»: no se ignoran los ficheros viejos). Sigue abierto:
el buzón automático (decidido: **primero lo seguro, el buzón después**).
