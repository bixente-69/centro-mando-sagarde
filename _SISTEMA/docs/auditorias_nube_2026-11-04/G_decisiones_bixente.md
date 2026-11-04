# G · Decisiones de Bixente tras las auditorías del 04/11/2026

**Fecha:** 04/11/2026 · **Dónde se decidió:** conversación «Pruebas por mutación», una a una, tras leer las auditorías A–F (PR 1, 3, 4, 5, 6) y el informe B.
**Para quién es:** la sesión que implemente esto. **Léelo antes de preguntar a Bixente**: ya contestó. Si falta algo que no está aquí, es que no se decidió: pregúntalo.

Reglas que valen para todo lo de abajo (`CLAUDE.md`): pruebas primero (`unittest`, sin pytest ni dependencias nuevas), probar por mutación, reportar el antes/después, un fichero nuevo exige línea `!` en el `.gitignore`, no ejecutar `Actualizar_Sagarde.bat` con trabajo en vuelo, y actualizar el mapa mental en la misma sesión si cambia el entorno. Bixente es electricista, no programador: se le explica todo en llano y **una pregunta cada vez**.

## Estado

| # | Asunto | Decisión | Estado |
|---|---|---|---|
| 1 | KPI «Avance medio» del inicio | Excluir OBRA PRUEBA y Gorliz de la media | **Pendiente de implementar** |
| 2 | Nombres de personal en el repo público | Mantener como está | Decidido; nada que hacer ahora |
| 3 | Plazos de «dato viejo» | Ver la tabla de abajo | **Pendiente de implementar** (junto con el 4) |
| 4 | Pantalla de salud | **No** crear página nueva: ampliar el aviso del inicio | **Pendiente de implementar** |
| 5 | Mapa mental desfasado | Corregido (PR 8) | Hecho |
| 6 | `CLAUDE.md` desfasado | Corregido (PR 9) | Hecho |
| 7 | Dar de baja OBRA PRUEBA | Quitarla bien, no borrar la carpeta a mano | **Pendiente** |
| 8 | Marcas guardadas en el aparato (generador de revisiones) | Se quedan como están: al reabrir una hoja vuelven las marcas guardadas de esa obra y fecha. Las copias «(2)»/«(3)» de seguridad son a propósito | Decidido el 04/11/2026; fijado con prueba |
| 9 | Aparato lleno de copias automáticas de hojas | Opción B: borrar solo copias de hojas de más de 30 días, la más vieja primero y solo las necesarias, y avisar | Decidido e implementado el 04/11/2026 (rama `claude/blissful-cannon-o3by6q`) |

## 1 · KPI «Avance medio»

- **Hoy:** el inicio muestra «42 % avance medio»: media simple de las 7 obras con seguimiento. Incluye OBRA PRUEBA (obra de ensayo) y Gorliz, que cuenta como 0 % porque no tiene base (desconocido convertido en cero, contra `CLAUDE.md` §7).
- **Cifras de referencia** (tabla «Estado de hoy» del mapa mental del 02/11/2026, no recalculadas): con las 7 obras sale 41,8; sin OBRA PRUEBA ni Gorliz sale 55,2. Verificar con datos del día al implementar.
- **Decidido:**
  - OBRA PRUEBA no cuenta (se dará de baja, ver 7).
  - Gorliz **no cuenta hasta que tenga su primera revisión; en cuanto la tenga entra sola.** Su tarjeta debe decir «sin datos», no 0 %. (Interpretación de lo que dijo Bixente: «gorliz de momento sigue ahí, cuando me toque tendrá su informe y revisión».)
  - Barakaldo (0,1 %, trabajo aún no empezado) **sí cuenta**: es un dato real.
- **Cómo comprobarlo:** prueba que fije la media con y sin esas obras; comparar el desglose, no el redondeado.
- **No decidido:** si además se retira o se cambia la media simple por otra cosa, y si se muestra el desglose (informe F, §4.7 punto 3, H-04 y G9). Solo se decidió quién entra en la media.

## 2 · Nombres de personal en el repo público

- **Decidido:** mantener la publicación actual de `personal_catalogo.json` y demás ficheros de personal.
- **Razones de Bixente:** los nombres y empresas están abreviados o cambiados (no completos ni reales); la app es de uso particular; necesita verlo desde cualquier sitio.
- **Pendiente de él (1 minuto):** abrir `personal_catalogo.json` en GitHub y comprobar que nada es identificable por un desconocido.
- **Condición escrita:** si algún día se amplía a un control horario «serio», **se privatiza antes**. Alcance actual: boceto para saber qué gente pasa por la obra y cuánto, para sacar medias; sin horas extra y sin exactitud de fichaje.
- **Nota:** lo que más pesa es publicar horas por día y obra por persona; revisar si cambia el alcance. Las auditorías no leyeron nombres reales.

## 3 · Plazos

| Dato | Amarillo | Rojo |
|---|---|---|
| Última subida del portal (`Actualizar_Sagarde.bat` → GitHub) | **> 8 días** | **> 14 días** |
| Obra sin archivos nuevos | los que ya existen (aviso entre 15 y 399 días) | — |
| Revisión vieja | los que ya existen (aviso > 30 días, no apaga nada) | — |
| Mantenimiento sin movimiento | los que ya existen (aviso entre 91 y 399 días) | — |
| Aviso caducado | desaparece a los 400 días (`avisos.py`) | — |
| Control horario del personal | **sin plazo por ahora** | — |

- **Por qué 8 y 14:** Bixente quiere acabar subiendo **una vez por semana, los viernes desde la oficina**. Con ese ritmo el portal tiene normalmente entre 0 y 7 días; un amarillo a 3 días estaría siempre encendido. El día de margen evita falsas alarmas si un viernes sube por la mañana y el siguiente por la tarde. **Hoy está en pruebas y sube más a menudo**: no deben saltar.
- **Los números van en un solo sitio** y se podrán endurecer a medida que se automatice.
- Control horario: se pondrá plazo cuando la rutina semanal esté asentada y se vea cuánto pasa entre un control y otro.

## 4 · Pantalla de salud: sin página nueva

- **Decidido:** **no** crear `SALUD.html`. Ampliar el bloque de avisos que ya hay al inicio (`index.html`, generado por `sagarde_portal.py`: bloqueos, obras sin archivos nuevos, mantenimientos parados, post-venta, «Salud de Datos»).
- **Falta añadir** (informe F, §1.4, G1–G4):
  1. **Antigüedad viva de la última subida**, calculada en el navegador con la fecha de generación incrustada (hoy solo sale pequeña y gris: «datos del 04/11/2026 16:31»), con los umbrales de la tabla del punto 3.
  2. **Estado de la subida** (si el `.bat` falló a medias o el push no llegó): hoy solo se ve en la ventana negra.
  3. **Pendientes sin aplicar en `REVISIONES`** (hojas y controles horarios): es el eslabón manual donde más se pierde. El auditor del paso 0 (`auditor_sagarde.py`) es el sitio natural donde engancharlo, pero **hoy no lo hace**: solo avisa de `REVISIONES_DUPLICADAS` (misma revisión con la misma fecha), no de hojas o controles pendientes.
- **Por comprobar al implementar** (no se ha verificado): cómo genera exactamente el inicio ese bloque, si sirve igual en móvil y tablet, y si basta con JavaScript embebido.
- **Cualquier fichero nuevo** necesita su línea `!` en el `.gitignore` y su prueba de que se publica (modelo `tests/test_publicacion_personal.py`).
- Del informe F, los pasos P0–P9 que creaban `SALUD.html` ya **no aplican tal cual**; sí valen el cálculo puro del estado y las pruebas.

## 7 · Dar de baja OBRA PRUEBA

- **Decidido por Bixente:** es solo para probar la app y se va a suprimir («después elimino la carpeta»).
- **No borrar la carpeta a mano.** Está dada de alta en `registro_obras.py` (id `prueba`) y **al menos 12 ficheros de prueba la usan como obra de ensayo** (garajes, generar todo, cerrar obra, paneles, informe a la carta…). Borrarla rompería esas pruebas y el registro seguiría creyendo que existe.
- **Trabajo:** primero dotar a esas pruebas de datos de ensayo propios (fixtures), después darla de baja del registro, después quitar la carpeta. Pruebas por mutación al terminar.
- Al darla de baja desaparece también del aviso «obras sin archivos nuevos» del inicio y de la media del punto 1.

## 8 · Marcas guardadas en el aparato: se quedan como están

- **Decidido por Bixente (04/11/2026):** *«dejarlo como está»*. Al reabrir una hoja, el aparato vuelve a poner las marcas que tenía guardadas de esa obra y fecha, también en una hoja nueva.
- **Razón de campo, textual:** *«imagínate Bolueta, edificio de 23 plantas, subes andando planta a planta y mirando vivienda por vivienda, escalera, rellanos, todo, con la tablet en la mano. Es facilísimo que se te resbale y te salgas de la pantalla. Hay veces que hasta guardo por si acaso hojas de seguridad por si se me apaga o borra, por eso a veces sale la revisión con un 2 o un 3 la última. Tiene que ser así. Comprobado con trabajo de campo.»*
- **Consecuencias:** las copias `(2)`/`(3)` en `REVISIONES` son **copias de seguridad a propósito**, no una anomalía. El auditor las reporta como `REVISIONES_DUPLICADAS` de nivel `info` y el motor se queda con la de modificación más reciente. **No «arreglar» esta recuperación.**
- **Matiz comprobado:** las marcas solo vuelven a una hoja nueva si portal y planta tienen los mismos identificadores (obra de la base). Con una estructura montada a mano no casan y ahora se avisa.
- **Fijado con pruebas:** `test_decision_de_bixente_…` en `tests/test_generador_revisiones_auditoria.py`.

## 9 · Aparato lleno: política B

- **Decidido por Bixente (04/11/2026), opción B:** las copias automáticas que guarda la tablet al marcar (`sgd_rev_<obra>_<fecha>`, más la variante `_garaje`) nunca se borraban y acaban llenando el aparato (una hoja grande de Bolueta ocupa ~224.000 caracteres; caben unas 23 en el aparato). Cuando se llena, se borran **solo** las de **más de 30 días**, la más vieja primero y solo las necesarias, y **se avisa**.
- **Nunca se borra:** la hoja que se está escribiendo, las configuraciones (`sgd_rev_cfg_*`), la lista de recientes, nada de otra aplicación ni ninguna copia de 30 días o menos (las de 30 exactos se quedan; las de 31 sí se borran).
- **Si todo lo que ocupa es reciente:** no se borra nada y sale el aviso «No se está guardando en este aparato… Pulsa «Guardar revisión»». La descarga no depende del almacenamiento.
- **Implementado en:** `escribirHaciendoSitio` de `generador_revisiones.html`. Detalle y pruebas en el informe H (H8, H9).

## No decidido (siguen abiertos en los informes)

Todo lo demás de los informes A–F: enlaces muertos fuera del PC, revisiones HTML duplicadas, panel móvil sin enlace, avisos de controles horarios con etiqueta falsa y un paso de retraso, el informe ejecutivo con otro alcance, etc. Cada cosa requiere decisión suya y especificación aprobada antes de programar (`CLAUDE.md` §5).
