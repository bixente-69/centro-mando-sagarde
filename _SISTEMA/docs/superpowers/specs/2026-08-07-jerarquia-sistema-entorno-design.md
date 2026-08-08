# Jerarquía `_SISTEMA`: separar lo informático de lo visible

**Fecha:** 07/08/2026
**Estado:** aprobado por Bixente
**Línea base:** `main` en `cebce47`, árbol limpio, 191 pruebas del motor de obras en verde

---

## 1. El problema

Desde que empezó la digitalización, cada apartado y cada obra ha ido acumulando
ficheros que no son documentación de obra: scripts, JSON de trabajo, cachés de
Python, previews generados, capturas de depuración, memorias de las IA. Están
mezclados con lo que Bixente sí abre. La raíz del entorno es el caso extremo:
19 elementos, de los que él sólo usa dos.

El riesgo no es estético. Un entorno donde no se distingue lo generado de lo
real es un entorno donde una corrección se aplica al fichero equivocado.

## 2. La norma

> **Cada apartado y cada obra tiene como mucho una carpeta técnica, llamada
> `_SISTEMA`. Dentro va todo lo informático. Fuera queda sólo lo que abriría
> una persona.**

El guion bajo la ordena al final, separada de las carpetas de negocio, y
continúa la convención que el entorno ya usa (`_MOTOR_SAGARDE`,
`_SISTEMA INFORME SAGARDE IA`, `_PREVIEWS_WORD`). El `.nojekyll` de la raíz —
añadido el 07/08/2026 — ya neutraliza el descarte de carpetas `_` que hace
GitHub Pages.

**Qué es "informático"** a estos efectos: `.py`, `.bat`, `.cmd`, `.ps1`,
`__pycache__`, `.bak`, `.log`, JSON de trabajo del motor, HTML de preview
generado, memorias `.memory`, capturas de depuración, documentación técnica.

**Qué no lo es:** DOCX y PDF de revisión, planos, fotos de obra, XLSX de
materiales, catálogos, el `index.html` de navegación de cada apartado y los
paneles de obra.

### 2.1 Alias históricos de la norma

Dos carpetas **ya implementan la norma con otro nombre** y no se renombran:

| Carpeta | Dónde | Por qué no se toca |
|---|---|---|
| `_SISTEMA INFORME SAGARDE IA` | `SAGARDE OBRAS ABIERTAS\` | Es el motor de obras y sus 191 pruebas. Renombrar toca `.gitignore` en 6 sitios y `generar_todos.py` en ~10 |
| `INFORME SAGARDE IA` | dentro de cada obra | Sus `panel.html` están publicados en GitHub Pages. Renombrar rompe las URL que Bixente consulta desde el móvil |

Ambas cumplen el espíritu de la norma: una sola carpeta técnica, bien
nombrada, por contenedor. Se documentan como alias, no como excepción a
resolver algún día.

### 2.2 Lo que no puede moverse, y se oculta

Nueve elementos de la raíz están anclados ahí por requisitos de herramienta.
No se mueven: se les pone el atributo *oculto* de Windows. No se desplaza un
byte, git y las tres IA los siguen leyendo igual, y es reversible con un
comando.

| Elemento | Ancla |
|---|---|
| `.gitignore` | lista blanca de todo el repositorio |
| `.nojekyll` | GitHub Pages lo exige en la raíz |
| `CLAUDE.md` | Claude sólo lo carga automáticamente desde la raíz |
| `GEMINI.md` | ídem con Gemini |
| `.claudeignore` | ídem |
| `.claude\` | skills y configuración; `.gitignore:75` publica `.claude/skills/**` |
| `.gemini\` | configuración de Gemini |
| `.agents\` | configuración de Codex |
| `.superpowers\` | espacio de trabajo de los planes |

`.git\` ya está oculto.

La misma regla se aplica a las carpetas de herramienta anidadas dentro de
subproyectos de `VARIOS\` — `TIERRAS\.claude\`, `BATERIAS DE CONDENSADORES\
.claude\`, `MANUALES\.claude\` y `APPS SAGARDE\PROYECTO PLANTILLA TRABAJO
PERSONAL\.claude\`. Están ancladas a la raíz de *su* subproyecto exactamente
igual que las de arriba: se ocultan, no se mueven.

## 3. Estado final de la raíz

```
COPIA SEGURIDAD SAGARDE\
    APLICACIONES\            MANTENIMIENTOS\        POST-VENTAS\
    SAGARDE (OLD)\           SAGARDE OBRAS ABIERTAS\   VARIOS\
    _SISTEMA\                     <- nueva, todo lo informático
    index.html                    <- se queda
    Actualizar_Sagarde.bat        <- se queda
    (9 elementos ocultos)
```

`PARA SOBREESCRIBIR\` está vacía y desaparece.

## 4. Tres fallos latentes que este trabajo destapa

Los tres son la familia de fallos del proyecto: algo declarado que el motor
ignora en silencio. **Se arreglan antes de mover nada**, no después.

### 4.1 `postventas_index.py:20` — el índice vacío sin error

```python
ROOT = Path(__file__).resolve().parent
```

El script deduce su raíz de dónde está él mismo. Al moverlo a `_SISTEMA\`, su
raíz pasa a ser `_SISTEMA\`, no encuentra ninguna carpeta `INCIDENCIAS ...`, y
**genera un `index.html` vacío devolviendo código 0**. `Actualizar_Sagarde.bat`
sólo avisa si `errorlevel neq 0`: no se enteraría.

Idéntico en `mantenimientos_index.py:22`.

**Corrección:** `.parent.parent` más una guarda que aborte con código distinto
de cero si el recuento de carpetas de negocio es 0. Un recuento de 0 es señal
de alarma, no de "no aplica".

### 4.2 `sagarde_portal.py:19` — el portal publicaría `_SISTEMA`

```python
IGNORE_DIRS = {".git", ".memory", "__pycache__", "_PREVIEWS_WORD", "_MOTOR_SAGARDE"}
```

El portal se construye recorriendo el disco y publica como área de negocio
todo lo que encuentra. Hoy publica `docs\` y `scratch\` por eso mismo. En
cuanto exista `_SISTEMA\`, la publicaría también.

**Corrección:** añadir `_SISTEMA` a esa lista y a las de
`postventas_index.py:26` y `mantenimientos_index.py:32`.

### 4.3 `auditor_sagarde.py:58` — una guarda que hoy no casa con nada

```python
if "_SISTEMA" in f.parts or "INFORME SAGARDE IA" in str(f):
```

`in f.parts` es igualdad exacta sobre un tramo de la ruta. La carpeta real se
llama `_SISTEMA INFORME SAGARDE IA`, así que **esa primera condición no ha
filtrado nunca nada**. La auditoría funciona sólo por la segunda.

**Corrección:** dejar la primera condición operativa y documentar que a partir
de ahora sí tiene efecto, porque `_SISTEMA` pasa a existir como tramo exacto.

## 5. Plan de ejecución: siete tandas secuenciales

**No se paralelizan.** Todas escriben en el mismo repositorio, y el CLAUDE.md
ya registra el día en que cinco procesos concurrentes causaron trabajo
duplicado y una mutación publicada.

Cada tanda lleva **dos subagentes**: uno ejecuta, otro verifica sin haber
visto el trabajo del primero. Ninguna tanda empieza si la anterior no ha
cerrado en verde.

| Tanda | Contenido | Riesgo |
|---|---|---|
| **0** | Línea base congelada | — |
| **1** | Las guardas (§4), antes de mover nada | bajo |
| **2** | Lo que no referencia nadie | nulo |
| **3** | Raíz con referencias + ocultar los 9 | alto |
| **4** | POST-VENTAS y MANTENIMIENTOS | alto |
| **5** | Sidecars dentro de las obras | medio |
| **6** | La norma escrita **y con prueba** | — |

### Tanda 0 — Línea base

Congelar, en fichero, lo que no puede moverse:

- 191 pruebas en verde (`python -m unittest discover -s tests`)
- KPI: Orueta 99.7 · Mungia 80.1 · Gernika 76.3 · Bolueta 43.5 · OBRA PRUEBA 6.4
- Desglose `x` / `m` / `/` / vacío de cada obra con ficha — no sólo el
  porcentaje: en Mungia, 3 celdas sobre 2309 no mueven el `pct_ponderado`
- Inventario de las URL que el portal genera
- `git status` limpio en `cebce47`

### Tanda 1 — Las guardas primero

Aplicar §4.1, §4.2 y §4.3. Después crear `_SISTEMA\` **vacía** y regenerar el
portal: debe seguir sin aparecer. Verificar que lo declarado produce efecto
observable, no que el código parezca correcto.

### Tanda 2 — Riesgo nulo

Comprobado que no los referencia ningún `.py`, `.bat`, `.cmd`, `.ps1`, `.html`,
`.js`, `.json` ni `.md` del entorno:

- 7 capturas de la raíz (`bol_p2`, `bol_p6`, `bol_p6_zoom`, `mun_contactos`,
  `mun_p2_mec`, `mun_p3_cm`, `mun_planta1`) → `_SISTEMA\capturas\`
- 2 `plot.log` (raíz de OBRAS ABIERTAS y de VARIOS) → su `_SISTEMA\`
- 9 `__pycache__` → borrar; se regeneran solos y ya están en `.gitignore`
- 3 `.bak` de `sagarde_portal.py` → `_SISTEMA\MOTOR\_bak\`
- `PARA SOBREESCRIBIR\` (vacía) → eliminar

### Tanda 3 — Raíz con referencias

| Se mueve | Referencias a corregir |
|---|---|
| `PORTAL SAGARDE.html` | `sagarde_portal.py:571` y el enlace de app del portal |
| `Servidor_Local.bat` | añadir `cd /d "%~dp0.."` |
| `ABRIR_CLAUDE_SAGARDE.cmd`, `ABRIR_GEMINI_SAGARDE.cmd` | ídem |
| `docs\` | `.gitignore:49-50`, `CLAUDE.md:190,241`, `GEMINI.md:18` |
| `scratch\` | ninguna en código |
| `_MOTOR_SAGARDE\` → `_SISTEMA\MOTOR\` | `Actualizar_Sagarde.bat:16,38`; `sagarde_portal.py:17`; `auditor_sagarde.py:27-28`; `mantenimientos_index.py:23`; `generar_todos.py:29`; `lector_hoja_tajos_pdf.py:29`; `test_registro_obras.py:11`; `adaptador_mungia.py:177` |

Y ocultar los 9 elementos de §2.2.

`docs\` y `scratch\` dejan de aparecer como áreas del portal. **Es el efecto
buscado**, no una regresión: hay que comprobar que desaparecen esas dos
tarjetas y ninguna más.

### Tanda 4 — Apartados

POST-VENTAS: `postventas_index.py`, `postventas_sync.py`,
`postventas_resumen.json`, `Actualizar_Postventas.bat`, `.memory\`,
`_PREVIEWS_WORD\` (88 HTML) → `POST-VENTAS\_SISTEMA\`.

MANTENIMIENTOS: `mantenimientos_index.py`, `mantenimientos_resumen.json` →
`MANTENIMIENTOS\_SISTEMA\`.

El arreglo de §4.1 tiene que estar dentro desde la tanda 1. La verificación
manda: los dos `index.html` regenerados deben listar **el mismo número de
carpetas que antes**, no un número plausible.

`logo_sagarde.jpg` **no se mueve**: lo referencian todas las páginas generadas
como `../POST-VENTAS/logo_sagarde.jpg` y está en la lista blanca del
`.gitignore`. Es un activo de marca, no informática.

### Tanda 5 — Dentro de las obras

14 sidecars y 3 carpetas `.recortes` (319 archivos) pasan de mezclarse con los
DOCX y PDF de revisión a `<obra>\REVISIONES\_SISTEMA\`:

| Obra | Elementos |
|---|---|
| 2025 BILBAO OBISPO ORUETA | 1 |
| 2026 BOLUETA ACR | 4 (incl. `.recortes`, 12 archivos) |
| 2026 MUNGIA ACR NEINOR | 5 (incl. `.recortes`, 225 archivos) |
| 2026 OBRA PRUEBA | 4 (incl. `.recortes`, 82 archivos) |

Corregir `.gitignore:45-46` y las rutas de `leer_hoja_marcada.py`. La prueba
real: reproducir con `--preparar` una hoja ya procesada y obtener la misma
clasificación.

### Tanda 6 — La norma, escrita y con prueba

- `CLAUDE.md`: sección nueva con la norma y los alias históricos
- `GEMINI.md` y `docs\SAGARDE_ENTORNO_IA_Y_SKILLS.md`
- `docs\SAGARDE_MAPA_MENTAL_ENTORNO.md` y `SAGARDE_GLOSARIO_OPERATIVO.md`
- Memoria del proyecto
- **`tests\test_jerarquia_sistema.py`**: recorre el entorno y falla si
  encuentra un `.py`, un `.bat`, un `.cmd`, un `__pycache__` o un `.bak`
  fuera de un `_SISTEMA` o de sus dos alias. Excepciones declaradas en una
  lista explícita dentro de la propia prueba: `Actualizar_Sagarde.bat` (raíz,
  por decisión de Bixente) y `Actualizar_Obras.bat` (dentro de un alias). Una
  excepción nueva exige tocar la lista, que es donde se ve

La prueba no es opcional. Una norma escrita en un `.md` que nadie ejecuta es
literalmente "algo declarado que el motor ignora en silencio".

## 6. Verificación

**Después de cada tanda:**

1. 191 pruebas en verde
2. `sagarde_portal.py` + `generar_todos.py --no-pdf` + los dos índices de
   apartado, regenerados sin error
3. Desglose `x` / `m` / `/` / vacío idéntico al de la tanda 0 — comparar el
   desglose, no el porcentaje redondeado
4. Ningún enlace roto: recorrer los `href` de los HTML generados y comprobar
   que el destino existe en disco
5. `git status`: sólo lo que la tanda debía cambiar
6. Antes/después reportado a Bixente

**Prueba por mutación en la tanda 1:** romper a propósito cada una de las tres
guardas y comprobar que la verificación se entera. Una guarda que no falla al
romperla no está verificando nada — ya pasó con la del auditor.

**No se publica hasta el final.** `Actualizar_Sagarde.bat` hace `git add -A` y
push a `main`: no se ejecuta mientras haya trabajo en vuelo. Los componentes se
invocan directamente por su `.py`. Publica Bixente cuando vea el antes/después.

## 7. Fuera de alcance

- `SAGARDE (OLD)\` — 17.000 ficheros, 46 GB. No se toca
- Renombrar los dos alias históricos (§2.1)
- `logo_sagarde.jpg` y su duplicado en `_MOTOR_SAGARDE\assets\`
- El fichero `INCIDENCIAS` de 0 bytes en POST-VENTAS: se reporta, no se borra

## 8. Observación al margen

Durante la línea base, la suite de pruebas **escribió un PDF real** en
`2026 MUNGIA ACR NEINOR\INFORME SAGARDE IA\INFORME_EJECUTIVO_...pdf`. No
ensucia el repositorio porque los PDF no están en la lista blanca, pero es una
prueba con efecto sobre datos de obra. Se reporta; no se corrige aquí.
