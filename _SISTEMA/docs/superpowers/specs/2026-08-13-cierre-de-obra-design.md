# Cierre de una obra — diseño

**Fecha:** 13/08/2026 · **Estado:** aprobado por Bixente

## El problema

Cerrar una obra hoy es mover su carpeta a `SAGARDE (OLD)/OBRAS CERRADAS` a
mano. Parece que funciona: `generar_todos.py:844` la salta con un aviso y
`sagarde_portal.py:218` la recoge sola en el índice de cerradas, porque ese
escáner solo lista directorios y no exige nada dentro.

Pero deja restos, y ya ha pasado dos veces:

- La obra **sigue en `registro_obras.py`**, así que cada publicación imprime
  «Saltada: la carpeta de obra no existe en esta ubicación», para siempre, y
  el registro miente.
- Su **adaptador queda huérfano** en `adaptadores/`. Egurrola y Zorrozaure
  llevan así desde que se cerraron, y el mapa del entorno los tiene fichados
  como problema.
- Las reglas de lista blanca del `.gitignore` están ancladas a
  `SAGARDE OBRAS ABIERTAS/*/INFORME SAGARDE IA/…`. Al mover la carpeta **dejan
  de casar sin dar ningún error** y los ficheros de la obra salen de la
  versión publicada.

Ese último punto es deliberado y deseado —una obra cerrada no pinta nada en el
seguimiento— pero hoy ocurre por accidente, no por decisión, y nadie deja
constancia de cómo terminó la obra.

## Qué significa «cerrada», según Bixente

> «El panel es solo para control de seguimiento de actividades en curso. Una
> vez que se cierra o acaba la obra pasa a obras cerradas. La obra se cierra y
> desaparece del panel por completo, a no ser que la busques como carpeta
> individual desde obras cerradas.»

El seguimiento posterior de esa obra existe, pero vive en **postventa**, que es
otro apartado y queda fuera de este diseño.

**Los ficheros no se pierden:** viajan con la carpeta, siguen en disco, y como
ya están commiteados permanecen en el historial de git. Lo único que cambia es
que dejan de estar en la versión publicada.

## Qué se construye

Un script con pruebas, más una skill fina que lo invoque. No una skill sola: en
este proyecto un procedimiento escrito en Markdown se puede saltar en silencio;
un script con pruebas, no.

```
SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/cerrar_obra.py
                                              tests/test_cerrar_obra.py
.claude/skills/sagarde-cerrar-obra/SKILL.md
```

Misma forma que `leer_hoja_marcada.py` y `alta_obra_desde_hoja.py`.

## Interfaz

```bash
python cerrar_obra.py <id_obra>              # informa, no toca nada
python cerrar_obra.py <id_obra> --ejecutar   # lo hace
```

Sin `--ejecutar` no se mueve ni un byte, igual que `leer_hoja_marcada.py` exige
`--escribir`.

## Comportamiento

### 1. Comprobaciones previas — abortan el cierre

| Comprobación | Por qué |
|---|---|
| La obra está en `registro_obras.py` | si no, no hay nada que cerrar |
| Su carpeta existe donde dice `carpeta_obra` | evita cerrar dos veces o cerrar un fantasma |
| **Lo que el cierre va a tocar** no tiene cambios sin commitear: la carpeta de la obra, su adaptador y `registro_obras.py` | no mover encima de trabajo a medias, y dejar `git status` legible para revertir |
| La carpeta destino no existe ya en Obras cerradas | nunca sobrescribir una obra archivada |

### 2. Informe del antes

KPI ponderado, ubicaciones, tajos, celdas, desglose `X/M///P/?/N`, fecha de la
última revisión, qué ficheros suyos están hoy publicados en git y cuántos
ficheros tiene la carpeta en total.

### 3. Ejecución

1. Mueve `adaptador_<id>.py` a `<carpeta_obra>/_SISTEMA/`.
2. Saca la obra de `registro_obras.py`.
3. Mueve la carpeta entera a `SAGARDE (OLD)/OBRAS CERRADAS/`.
4. Escribe `<obra cerrada>/_SISTEMA/cierre.json`: fecha de cierre, KPI final,
   desglose completo, última revisión y el commit desde el que se cierra.
5. Imprime el comando exacto para deshacer el movimiento.

El paso 4 es lo que hace que cerrar no sea perder. Dentro de dos años la
carpeta dice cómo acabó la obra sin bucear en el historial de git.

### 4. Verificación posterior

El script la enuncia y la skill la recoge: lanzar `Actualizar_Sagarde.bat` y
comprobar que la obra ya no está en `resumen_obras.json`, que aparece en el
índice de cerradas, y que las dos suites siguen verdes.

**El script no regenera ni publica.** Publicar es cosa del BAT que lanza
Bixente.

## Qué no se toca, a propósito

| No se toca | Por qué |
|---|---|
| `reglas/CATALOGO_TAJOS.json` | los 18 tajos propios de Orueta viven ahí y tres ficheros de prueba dependen de esa entrada. **El fichero no está en git**: si se estropea, no hay `git checkout` que lo devuelva |
| `.gitignore` | sus reglas dejan de casar solas al moverse la carpeta, que es el efecto buscado. `panel.html` se sigue publicando por la línea global `!*.html`, igual que Zorrozaure y Egurrola |
| Postventa | otro apartado. El script lo recuerda por pantalla; no actúa |

## Pruebas

Sobre un árbol temporal, nunca sobre obras reales:

1. Una obra que no está en el registro aborta.
2. Sin `--ejecutar` no se mueve ni un fichero.
3. Tras ejecutar: la obra sale del registro, el adaptador está dentro de la
   carpeta de la obra, y la carpeta está en Obras cerradas.
4. El `cierre.json` recoge el desglose real de la ficha, no un resumen.
5. Si la carpeta destino ya existe, aborta sin tocar nada.
6. El catálogo de tajos queda intacto byte a byte.
7. Con cambios sin commitear **en la obra, su adaptador o el registro**,
   aborta.
8. Con cambios sin commitear **en cualquier otro sitio**, NO aborta. Una
   guarda de «árbol entero limpio» bloquearía el primer uso, porque el propio
   `cerrar_obra.py` y sus pruebas estarán sin publicar la primera vez.

## Riesgo principal

Es una operación difícil de deshacer: mueve una carpeta con miles de ficheros
no rastreados. Se cubre con el informe previo, el `--ejecutar` explícito, la
guarda sobre los ficheros implicados y el comando de reversión impreso.

## Fuera de alcance

- **Reabrir** una obra cerrada.
- **Recolocar los dos adaptadores huérfanos** de Egurrola y Zorrozaure. Se
  propondrá aparte cuando esto funcione.
