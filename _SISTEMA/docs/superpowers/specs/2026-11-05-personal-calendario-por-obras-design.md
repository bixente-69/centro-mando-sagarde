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

Fusión sin pisar en el PC (que un día de un aparato no borre al de otro), arreglo de las pestañas de la tablet que se pisan,
nombre del aparato en cada fichero, y el buzón automático (decidido: **primero lo seguro, el buzón después**).
