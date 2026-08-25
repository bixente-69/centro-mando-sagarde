# Comprobador de enlaces publicados

**Fecha:** 25/08/2026
**Estado:** aprobado por Bixente
**Línea base:** `main` en `3eabc05`, 445 pruebas del motor de obras en verde (4 saltadas, tajos propios de Orueta)
**Origen:** recomendación nº5 de la auditoría del entorno Sagarde del 25/08/2026 (paneles, skills, enlaces, carpetas, mapa mental)

---

## 1. El problema

El mapa mental del entorno (`_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`) ya
comprueba, en cada `Actualizar_Sagarde.bat`, que ninguna ruta que **él mismo**
declara en su prosa apunte a la nada. No existe el equivalente para el
**portal publicado**: nada comprueba que los `href`/`src` de `index.html`, del
índice de obras, de postventa, de mantenimientos o de los paneles de obra
sigan apuntando a un archivo real después de una regeneración.

Hoy no hay ningún enlace roto conocido — se comprobó a mano en la auditoría —
pero es exactamente la familia de fallos que este proyecto ya sabe que sale
cara: algo que se publica y nadie vuelve a mirar.

## 2. Alcance

**Páginas que se recorren** (fijas, sin crawling — se listan los enlaces que
salen de ellas, no se sigue esos enlaces a su vez):

- `index.html` (raíz)
- `SAGARDE OBRAS ABIERTAS/index.html`
- `POST-VENTAS/index.html`
- `MANTENIMIENTOS/index.html`
- `APLICACIONES/index.html`
- `SAGARDE (OLD)/index.html`
- `panel.html` de cada obra de `registro_obras.OBRAS` — la misma fuente de
  verdad que ya usan `auditor_sagarde.py` y el mapa mental, para no duplicar
  con una segunda lista que se pueda desincronizar

**Qué se comprueba de cada página:** los `href`/`src` cuyo esquema no sea
`http`, `https`, `mailto`, `tel` ni `javascript:`, y que no empiecen por `#`.
La ruta se decodifica (`%20`, `%28`...) y se resuelve relativa a la carpeta
del propio HTML, no al directorio de ejecución.

**Explícitamente fuera de alcance** (decisión de Bixente, 25/08/2026):

- Enlaces externos (CDN de Chart.js, Google Fonts) — comprobarlos exige red,
  no disco, y depende de que haya internet en el momento de publicar.
- Anclas internas (`#seccion`) — no se comprueba que el `id` de destino
  exista dentro de la página.
- El resto del árbol publicado: las 128 obras cerradas, los ~90 previews de
  postventa, los mapas de mantenimiento. Se puede ampliar más adelante; hoy
  el coste de recorrerlo no compensa frente a lo poco que cambia.
- Persistencia en JSON: el resultado sólo se imprime por consola, igual que
  el chequeo de rutas del mapa mental. Sin fichero nuevo que mantener.

## 3. Diseño

**Extracción:** `html.parser.HTMLParser` de la biblioteca estándar — tokeniza
las etiquetas de verdad (comillas, atributos con caracteres raros) en vez de
un regex frágil sobre el texto. Sin dependencias nuevas.

**Salida y códigos**, igual contrato que `actualizar_mapa_mental.py`:

| Código | Significa | Efecto en el BAT |
|---|---|---|
| `0` | todos los enlaces resuelven | continúa |
| `1` | hay enlaces rotos | aviso en pantalla, **la publicación sigue** |
| `2` | una página fija de la lista no existe | error — probablemente el portal no se generó bien en el paso anterior |

El aviso de cada enlace roto imprime `archivo.html → destino_roto (línea N)`,
para poder localizarlo sin abrir el HTML a mano.

**Ubicación:** `_SISTEMA/MOTOR/scripts/comprobar_enlaces.py`, un script con
una sola responsabilidad — valida el portal publicado, no el documento del
mapa mental ni los datos de obra.

## 4. Dónde engancha en el pipeline

El portal (paso `[3/5]` de `Actualizar_Sagarde.bat`) tiene que existir antes
de poder comprobar sus enlaces — por eso el nuevo paso va **después** de él,
junto al paso del mapa mental:

```
[0/6] Auditoría Pre-Vuelo de Salud de Datos       (auditor_sagarde.py)
[1/6] Informe Sagarde IA (Obras abiertas)         (generar_todos.py)
[2/6] Post-ventas y Mantenimientos
[3/6] Portal principal                            (sagarde_portal.py)
[4/6] Enlaces del portal publicado                 (comprobar_enlaces.py)  <- nuevo
[5/6] Mapa mental del entorno                      (actualizar_mapa_mental.py)
[6/6] Subir a la nube (GitHub Pages)
```

Se numeran los pasos existentes `[4/5]` y `[5/5]` a `[5/6]` y `[6/6]`. El
tratamiento de `errorlevel` en el `.bat` copia literalmente el bloque ya
existente para el mapa mental (líneas 47-55 de `Actualizar_Sagarde.bat`):
`errorlevel 2` → error visible; `errorlevel 1` → aviso, se publica igual;
si no, sigue en silencio.

## 5. Pruebas (antes que el código)

`unittest`, árbol temporal, sin red — mismo patrón que
`tests/test_mapa_mental.py`:

1. Extrae correctamente `href`/`src` con comillas simples, dobles y con
   atributos adicionales en la misma etiqueta.
2. Ignora `http://`, `https://`, `mailto:`, `tel:`, `javascript:` y anclas
   (`#...`).
3. Decodifica `%20` y otros escapes antes de comprobar en disco.
4. Resuelve la ruta relativa a la carpeta del HTML que la contiene, no al
   directorio desde el que se ejecuta el script.
5. Detecta un enlace roto real (apunta a un archivo que no existe).
6. No marca como roto un enlace correcto — incluida una ruta con espacios
   codificados, como las que ya usa `index.html` hoy.
7. La lista de paneles de obra a comprobar sale de `registro_obras.OBRAS`,
   no de una lista repetida a mano en el script nuevo.
8. Los tres códigos de salida (`0`, `1`, `2`), incluido el caso de una página
   fija ausente.

## 6. Verificación de aceptación

- Ejecutado sobre el árbol real de hoy: código `0`, cero enlaces rotos —
  coincide con lo comprobado a mano en la auditoría del 25/08/2026.
- Roto a propósito un enlace de una copia temporal del `index.html` real:
  el script lo detecta y devuelve `1` (prueba por mutación, no basta con que
  el código "parezca" correcto).
- `Actualizar_Sagarde.bat` completo, de punta a punta, sobre el árbol real:
  termina en el paso `[6/6]` sin abortar la publicación por este paso nuevo.
- 445 pruebas del motor siguen en verde tras el cambio.

## 7. Fuera de alcance de este trabajo

- Reparar el portal móvil independiente (decisión ya tomada por Bixente el
  25/08/2026: se retira formalmente — es un trabajo aparte, no se mezcla
  aquí).
- Las tres skills de host sin versionar en el repo (`sagarde-parte-postventa`
  y las otras dos) — investigación y decisión aparte.
- Comprobar enlaces dentro de las 128 obras cerradas o los previews de
  postventa (§2).
