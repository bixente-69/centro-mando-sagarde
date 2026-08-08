# La ficha como centro del entorno Sagarde — Diseño

**Fecha:** 27/07/2026
**Estado:** aprobado para planificar
**Sustituye en alcance a:** `2026-07-27-base-datos-obras-sagarde-design.md`, que
construyó los cimientos pero dejó la ficha fuera del sistema.

---

## 1. Qué falló en el diseño anterior

El plan anterior construyó `ficha_obra.json`: esquema de 9 apartados,
actualización incremental, 44 pruebas, estados `P`/`?`/`N`, y recuperación de
63 correcciones manuales que se perdían. Todo eso funciona.

**Pero la ficha quedó al lado del sistema, no dentro.** Comprobado el
27/07/2026: los únicos ficheros que la mencionan son el propio módulo, sus
pruebas, el sembrador y `generar_todos.py`. **Ninguna aplicación la lee.**

```
HOY
  adaptador → historial → motor_informes (KPIs) → priorizador → panel · informes
                                                       │
                                                       └→ ficha_obra   ← hoja muerta
                                                              └→ obras_revisiones.js → generador
```

Consecuencia práctica: el sistema se comporta exactamente igual que antes de
construirla. Los porcentajes que se publican se calculan desde
`prioridades_trabajos.json`, **antes** de que la ficha corrija nada, así que
lo publicado puede ser peor que la realidad conocida.

## 2. Qué se pide de verdad

Palabras de Bixente:

> *"una base de datos para cada obra en la que tuviera todos los datos de ella
> de manera que en cualquier momento cualquiera de las apps desarrolladas
> pudiera hacer uso de ella, que se actualizara por medio de las diversas
> entradas que tiene y que se actualizara junto con el entorno Sagarde. Se
> tenía que poder generar informes y revisiones a partir de los últimos
> datos."*

```
OBJETIVO
  ENTRADAS                      FICHA                    CONSUMIDORES
  ─────────                     ─────                    ────────────
  revisiones PDF/HTML/Word ─┐                        ┌→ panel de obra
  generador de revisiones  ─┤                        ├→ informe ejecutivo
  entrada manual puntual   ─┼→  FICHA DE OBRA  ──────┼→ generador de revisiones
  albaranes y materiales   ─┘   (fuente única)       ├→ Centro de Mando
                                                     └→ postventa
```

## 3. La ficha es un árbol de bases anidadas

Precisión de Bixente que cambia el modelo:

> *"se pueden generar árboles de contenido. Por ejemplo hay una base de datos
> de material entregado en una obra, pero eso es una base dentro de otra que
> es la obra en sí, el apartado materiales, y así sucesivamente."*

La ficha no es un documento plano de 9 secciones. Cada apartado puede contener
sus propias bases:

```
obra/
├── identidad/            campos simples
├── estructura/           bloques → portales → plantas → ubicaciones
├── tajos/                catálogo aplicable a esta obra
├── estados/              matriz ubicación × tajo
├── revisiones/           registro de cada hoja procesada
├── materiales/
│   ├── entregado/        base propia: albaranes, fechas, cantidades
│   ├── instalado/        derivado de estados × consumo por tajo
│   ├── pendiente/
│   └── necesario/        estimación, marcada como tal
├── documentos/
├── contactos/
├── dudas/
└── incidencias/          postventa
```

**Regla del árbol:** un nodo hoja guarda valor + fecha + procedencia. Un nodo
rama guarda sus hijos más su propio `_meta.actualizado`. Cualquier apartado
puede crecer en sub-bases sin tocar los demás.

## 4. Protocolo de entrada — "abre campo y actualiza"

Bixente:

> *"todo el entorno Sagarde que genere entradas abre campo y actualiza; en
> duda de si el campo ya está, preguntar comparando."*

Cuando una fuente trae un dato que la ficha no tiene:

| Situación | Qué hace el sistema |
|---|---|
| Campo claramente nuevo | Lo crea, marcado `origen: sin_confirmar`, y **avisa** |
| Parecido a uno existente | **No adivina**: presenta la comparación y pregunta |
| Campo conocido, valor nuevo | Actualiza, guardando fecha y procedencia |
| Campo conocido, valor vacío | **No pisa** lo que había: la ficha es acumulativa |

Es el mismo patrón ya construido y probado para ubicaciones y tajos nuevos
(`origen: revision_sin_confirmar`). Se extiende a cualquier campo del árbol.

## 5. La inversión del flujo

El cambio central. Hoy el adaptador alimenta al motor y la ficha es un
subproducto. Debe ser al revés:

```
ANTES   adaptador → historial → motor_informes → priorizador → panel
                                                     └→ ficha (subproducto)

DESPUÉS adaptador → historial → FICHA → motor_informes → priorizador → panel
                                  ↑                          └→ informes
        otras entradas ───────────┘
```

**Por qué importa y no es cosmético:** medido el 27/07/2026 con los mismos
datos de entrada, el lector de PDF degradaba 3 celdas y la ficha las
rescataba. Resultado: `ficha_obra.json` correcto, **KPIs publicados
incorrectos** (`x=1798` en vez de `1799`). Mientras el cálculo ocurra antes de
la ficha, corregir la ficha no corrige lo que ves.

## 6. Decisiones tomadas

| Decisión | Elegido |
|---|---|
| Arquitectura | La ficha alimenta al motor, no al revés |
| Entradas | Las cuatro: revisiones, generador, manual, materiales |
| Modelo | Árbol de bases anidadas, no documento plano |
| Campos nuevos | Se crean marcados y avisando; en duda, preguntar comparando |
| Alcance del primer plan | Mungia de punta a punta antes de tocar las demás |
| Ejecución | Esperar a que terminen las 4 sesiones en vuelo |

## 7. Criterio de verificación

**El porcentaje redondeado es ciego** (3 celdas sobre 2309 no lo mueven).
Comparar siempre el desglose. Línea base a 27/07/2026:

| Obra | x | m | / | vacío | pct |
|---|---|---|---|---|---|
| Mungia | 1798 | 84 | 0 | 436 | 80.1 |
| Gernika | 928 | 0 | 0 | 288 | 76.3 |
| Bolueta | 1265 | 76 | 20 | 2287 | 36.1 |
| Obispo Orueta | 2392 | 0 | 0 | 12 | 80.0 |

**Criterio de aceptación de la inversión:** tras invertir el flujo, Mungia debe
dar `x=1799, m=85` (los valores correctos, no los degradados), y las otras tres
obras deben quedar **exactamente igual** mientras no tengan ficha.

Ese cambio de 1798 a 1799 es la prueba de que la inversión funciona: es el dato
corregido llegando por fin al número publicado.

## 8. Fases

| # | Fase | Entrega |
|---|---|---|
| **A** | Inversión del flujo en Mungia | El panel y el informe de Mungia salen de la ficha |
| **B** | Entrada manual puntual | Corregir una celda sin montar una revisión entera |
| **C** | Árbol de materiales | Entregado / instalado / pendiente / necesario |
| **D** | Escritura desde el generador | Marcar en la app escribe en la ficha sin PDF |
| **E** | Resto de obras | Gernika, Bolueta, Gorliz, y las 16 dormidas |
| **F** | Limpiar duplicados | Un catálogo, un registro de obras, un formato de clave |

Cada fase tendrá su propio plan. Este documento cubre el diseño de todas; la
fase A se planifica y ejecuta primero.

## 9. Fuera de alcance

- Migrar las 16 obras sin panel: entran cuando les toque su primera hoja.
- Megapark: solo cuadros y papeleo, no encaja en el modelo ubicación × tajo.
- Historial completo por celda: se mantiene último valor + fecha + procedencia.
- Cambiar el formato de clave de celda mientras la fase F no lo aborde.
