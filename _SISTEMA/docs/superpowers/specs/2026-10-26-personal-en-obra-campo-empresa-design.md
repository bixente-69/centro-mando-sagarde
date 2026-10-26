# Personal en obra — campo Empresa (paso 08c2)

Fecha: 26/10/2026. Diseñado con Bixente en conversación (preguntas en llano, de una en una). Complementa a `2026-10-25-personal-en-obra-repaso-integracion.md` y `…-piloto-v1-1-design.md`. **Es solo una aportación de datos al entorno Sagarde** (principio máximo): la app de la tablet no guarda datos maestros; el fichero `CONTROL HORARIO …` lleva los cambios y el PC los aplica con «actualiza la obra».

## 1. De dónde sale

En el piloto real de Olabeaga la empresa va escrita dentro del nombre: «Alejo (Manueles)», «Manuel (Manueles)», «Nestor (Manueles)», «Javi @ CATERSYSTEM», «Chico 1 @ CATERSYSTEM»; «Asensio» no lleva ninguna. El catálogo de P1 ya tiene el campo `empresa` por persona (vacío) y `exportar_estado` ya lo publica, pero nada lo escribe ni lo enseña.

## 2. Decisiones de Bixente (26/10/2026)

| # | Pregunta | Respuesta |
|---|---|---|
| E1 | ¿Para qué la empresa? | **Las dos cosas**: que salga al lado del nombre y que se **sume por empresa** (horas y días de Manueles, Catersystem, Sagarde…). |
| E2 | ¿Dónde se pone o se cambia? | **Al crear y con el lápiz ✎**: junto a «Nombre nuevo» hay un campo Empresa y el lápiz deja corregir nombre y empresa. En «Añadir varios nombres» cada línea puede ser «Alejo, Manueles». |
| E3 | ¿Escrita o elegida? | **Elegida de una lista** de las ya usadas, con «Otra empresa…» para escribir una nueva (así no se parte «Manueles» en dos). |
| E4 | ¿Quien no tiene empresa? | **«Sin empresa»** hasta que se la pongan. **No se da por hecho que sea de Sagarde: puede ser autónomo.** |
| E5 | Autónomos | Se crean como **empresa + «@AUT»**, por ejemplo «Javi @AUT». **Cada autónomo sale aparte y, además, una línea con el total de todos los @AUT.** |
| E6 | Las 5 personas de ahora con la empresa dentro del nombre | **El PC las separa y Bixente lo ve antes** (vista previa; no se aplica nada hasta su «sí»). Son las mismas personas, con sus días y horas intactos. |
| E7 | ¿Y si una persona cambia de empresa? | **Una persona, una empresa, para todo** (todas sus obras y todos sus días), igual que al corregir un nombre (D3). |
| E8 | ¿Dónde se ve? | **En los cuatro sitios**: pestaña Personal de la obra, Informe de obra, ranking de Sagarde e Informe de la tablet. |

Las demás decisiones de la fase 08 (D3–D7, el «nombre» y no «alias», nada de DNI/teléfono/correo, lenguaje de electricista, ver antes de aplicar) siguen vigentes.

## 3. Diseño (lo decide Claude; Bixente lo aprueba al ver capturas)

### 3.1 Datos (P1, `personal_obra.py`)
- **Una empresa por persona** (`catalogo.trabajadores[].empresa`, texto). Vacía = «Sin empresa» (**nunca se rellena sola**). Se compara con `clave_nombre` (sin tildes ni mayúsculas): «CATERSYSTEM» = «Catersystem»; se guarda con la grafía de la primera vez que se escribió.
- Mismas reglas que un nombre (≤ 60 letras, sin caracteres raros ni `<` `>`, **jamás DNI, NIE, teléfono ni correo**: `nombre_publicable`).
- **Autónomo** = empresa que termina en `@AUT` (mayúsculas indiferentes, con o sin espacio delante: «Javi @AUT», «Javi@aut»). Función única `es_autonomo(empresa)`.
- **Fichero**: clave nueva y opcional `empresas: [{"nombre": "Alejo", "empresa": "Manueles"}]` (empresa vacía = quitársela). Misma versión del esquema que `renombres`/`altas` (se amplía `LK`; un campo fuera del esquema sigue rechazándose). **Orden de aplicación: `renombres → altas → empresas → jornadas → horario → horarios propios`** (así «Mikel» recién creado o recién renombrado puede llevar empresa en el mismo fichero). Una empresa para alguien que no existe → aviso en llano y no se crea a nadie.
- **Traza** (`personal_jornadas.jsonl`): una línea por cada cambio de empresa (como `renombre`), con el nombre y las empresas de antes y después.
- **Sin usar nada de esto, el fichero y los datos son idénticos a los de antes.**

### 3.2 La tablet (`generador_personal.html`)
- **Lista de empresas** del desplegable = las del catálogo publicado (`catalogo[].empresa`, sin repetir) + «Sagarde» (siempre) + las nuevas del aparato. Opciones fijas: «Sin empresa» y «Otra empresa…» (esta abre un campo de texto; si lo escrito es igual —sin tildes ni mayúsculas— a una que ya está, se usa la que ya está).
- **Crear**: campo Empresa junto a «Nombre nuevo». **Lápiz ✎**: la fila deja corregir nombre y empresa. **Varios nombres**: «Nombre, Empresa» por línea (la empresa es lo que va tras la **última coma**; sin coma, sin empresa); el resumen cuenta cuántos entran con empresa.
- **En la lista de personas**: la empresa al lado del nombre, en pequeño («Javi · CATERSYSTEM»); quien no tiene, nada.
- Se apunta en el aparato (clave nueva `sgd_personal_empresas`, lista de `{nombre, empresa}`), viaja en `empresas` y **se olvida cuando el estado publicado ya la trae** (como `renombres`). Corregir un nombre arrastra su empresa. Una empresa en el borrador no se guarda hasta «Guardar»/enviar, como el resto.
- **Informe de la tablet**: tabla «Por empresa» (§3.4). La pantalla «Enviar al PC» cuenta «N empresas puestas» en la lista y en el recuadro «Listo».
- Textos nuevos en lenguaje de electricista; los vigila `tests/test_lenguaje_electricista.py` (hay que ampliarlo con los estados nuevos).

### 3.3 Separar las empresas que ya van dentro del nombre (E6)
- Operación nueva de P1 (CLI `personal_obra.py separar-empresas`, **vista previa por defecto**, `--aplicar` solo tras el «sí» de Bixente): para cada persona del catálogo cuyo nombre acabe en `(Empresa)` o en `@ Empresa`, propone **nombre limpio + empresa**. Al aplicar usa lo que ya existe: **renombrar a toda la persona** (D3; el nombre viejo queda en `nombres_anteriores`) y ponerle la empresa. **No toca ninguna jornada.**
- Casos que **paran y se enseñan** (nunca se aplican en silencio): el nombre limpio ya es de otra persona (hay que juntarlas, comando `fusionar` existente), nombre limpio vacío, o un sufijo que ya es «@AUT» (¿empresa «Javi @AUT» con nombre «Javi»?: se pregunta a Bixente con el caso real delante).
- Datos reales a la vista previa: Alejo, Manuel y Nestor → empresa «Manueles»; Javi y Chico 1 → «CATERSYSTEM»; Asensio, sin empresa.
- Hoy lo lanza Claude a petición de Bixente; **la «Base de trabajadores» del portal (08e) debe ofrecerlo** (principio: todo se controla desde el portal).

### 3.4 Qué se suma (P2, `personal_calculo.js`, fuente única)
- Función nueva `agregarPorEmpresa(filas)` (filas con su `empresa`): por empresa, **personas, días de trabajo (persona-día), horas y % de impacto**. Orden: más horas primero; **«Sin empresa» al final**.
- **Autónomos**: cada «X @AUT» es una línea como cualquier empresa y **además** una línea **«Total autónomos (@AUT)»** con la suma de todos (esa línea **no se cuenta dos veces** en el total general ni en los %).
- La misma función la usan los cuatro sitios (E8): `panel_personal.py` (pestaña Personal), la sección de Personal del Informe de obra, `personal_sagarde.html` (ranking: aquí, suma de **todas las obras**) y la tablet. Una obra sin empresas puestas se ve **exactamente como hoy** salvo una línea «Sin empresa» (comprobarlo con la foto SHA256 de las demás obras y el diff del panel/informe de Olabeaga).
- La empresa **al lado del nombre** en cada tabla de personas.

## 4. Qué NO cambia
La fórmula de horas y extras, el % de impacto, el nombre de las personas (salvo la separación aprobada de E6), el formato de `personal_obra.json` salvo el campo `empresa` por persona que ya existía, las demás obras.

## 5. Cómo se comprobará
- **P1**: pruebas con datos **inventados** para `empresas` (orden de aplicación, empresa a persona inexistente, vacía = quitar, datos privados, `@AUT`), traza, `comprobar`, `separar-empresas` (vista previa idéntica sin `--aplicar`, nombre ya existente, sufijo `@AUT`) y mutaciones de cada regla. Las pruebas de 08a/08b **no se tocan**.
- **Tablet**: escenas de Playwright (crear con empresa, lápiz, «Otra empresa…», repetida con otra grafía, varios con coma, olvidarla al publicarse, fichero idéntico si no se usa); lote validado con P1; capturas a 390 y 820 px que **Bixente ve antes de aplicar**.
- **Sumas**: pruebas con node en tres zonas horarias y cifras hechas a mano (incluido el total de @AUT sin doble cuenta); el mismo desglose en pestaña, informe, ranking y tablet.
- **Datos reales**: vista previa de la separación sobre una **copia** de Olabeaga; nada en el árbol real hasta 08f.
