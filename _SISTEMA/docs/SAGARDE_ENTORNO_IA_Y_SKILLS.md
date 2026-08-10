# Entorno de IA y skills de SAGARDE

Fecha de actualización: 10/08/2026  
Ámbito: proyecto local SAGARDE y generador preventivo CARDIVA

Este documento es el registro central de dónde reside el contexto compartido
por Codex, Claude y Gemini. La raíz canónica del entorno es:

`D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE`

## Contexto y memoria del proyecto

| Contenido | Ruta |
|---|---|
| Instrucciones comunes y contexto de Claude | `CLAUDE.md` |
| Entrada de contexto de Gemini, con importación de las reglas comunes | `GEMINI.md` |
| Memoria funcional y técnica vigente | `_SISTEMA/docs/2026-07-28-memoria-diccionario-tajos-alertas-informes.md` |
| Mapa del entorno | `_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md` |
| Glosario operativo | `_SISTEMA/docs/SAGARDE_GLOSARIO_OPERATIVO.md` |
| Este registro de integración multi-IA | `_SISTEMA/docs/SAGARDE_ENTORNO_IA_Y_SKILLS.md` |

Los cuatro documentos pasaron de `docs/` a `_SISTEMA/docs/` con la norma
`_SISTEMA` (08/08/2026). Desde el 10/08/2026 están rastreados en git: hasta
entonces la lista blanca del `.gitignore` los ignoraba y la memoria que
`CLAUDE.md` manda leer solo existía en este disco.

Las reglas de `CLAUDE.md` se importan desde `GEMINI.md` para evitar mantener
dos memorias contradictorias. Las instrucciones exclusivas de una herramienta
solo se aplican cuando esa herramienta o una capacidad equivalente está
disponible.

## Skill canónica de CARDIVA

La única fuente que debe editarse manualmente es:

`MANTENIMIENTOS\MANTENIMIENTO CARDIVA\APP_CARDIVA\skills\generate-cardiva-report`

Contiene:

- `SKILL.md`: instrucciones y criterios de activación;
- `references/mapping.md`: mapeo de los puntos 01–06 hacia 07–09;
- `references/data-schema.md`: contrato del JSON normalizado;
- `scripts/generate_cardiva_report.ps1`: generación determinista DOCX/PDF;
- `agents/openai.yaml`: metadatos de interfaz para Codex.

## Copias de descubrimiento

| Entorno | Copia de proyecto | Copia de usuario |
|---|---|---|
| Codex | `.agents/skills/generate-cardiva-report` | `C:\Users\bixen\.codex\skills\generate-cardiva-report` |
| Claude Code | `.claude/skills/generate-cardiva-report` | `C:\Users\bixen\.claude\skills\generate-cardiva-report` |
| Gemini CLI | `.gemini/skills/generate-cardiva-report` | `C:\Users\bixen\.gemini\skills\generate-cardiva-report` |

`.agents/skills` conserva además una copia conforme al estándar abierto Agent
Skills para clientes capaces de descubrir ese alias. Las copias de proyecto
permiten trasladar el árbol SAGARDE a otro equipo; las copias de usuario
permiten encontrar la skill fuera de este proyecto. Ninguna copia es la fuente
de edición.

## Sincronización

Ejecutar desde la raíz de SAGARDE:

```powershell
& ".\MANTENIMIENTOS\MANTENIMIENTO CARDIVA\APP_CARDIVA\tools\sync_cardiva_skill_agents.ps1" -InstallUserCopies
```

El script copia todos los archivos desde la fuente canónica y compara cada
archivo mediante SHA-256. No elimina archivos ajenos.

## Activación y comprobación

- Codex: pedir `Usa $generate-cardiva-report` y proporcionar solo los archivos
  autorizados.
- Claude Code: abrir en la raíz SAGARDE, ejecutar `/skills` para comprobarla y
  llamar `/generate-cardiva-report`.
- Gemini CLI: abrir en la raíz SAGARDE, ejecutar `/skills` para comprobarla;
  la descripción de la skill permite su activación contextual. Tras cambiar
  archivos durante una sesión, ejecutar `/skills reload` y `/memory reload`.
- Accesos de doble clic: `_SISTEMA\ABRIR_CLAUDE_SAGARDE.cmd` y
  `_SISTEMA\ABRIR_GEMINI_SAGARDE.cmd`. Ambos hacen `cd /d "%~dp0.."`, así que
  la sesión sigue abriéndose en la raíz del entorno, no en `_SISTEMA`.

## Estado local comprobado el 29/07/2026

- Claude Code `2.1.132` está instalado. Las copias de proyecto y usuario de la
  skill están sincronizadas. La comprobación contra el modelo quedó aplazada
  porque la cuenta informó de límite de uso adicional hasta el 31/07/2026 a
  las 04:00 (Europe/Madrid).
- Node.js LTS `24.18.0`, npm `11.16.0` y Gemini CLI `0.53.0` están instalados.
  La primera sesión de Gemini requiere que el usuario seleccione un método de
  autenticación; no se almacenaron claves ni se eligió una cuenta sin
  autorización. npm avisó además de que el script de instalación de
  `@github/keytar` no se autoaprobó; si el inicio de sesión no puede conservar
  credenciales, esa aprobación deberá revisarse expresamente.

## Estado del entorno comprobado el 10/08/2026

Cierre de todo lo que estaba en vuelo, antes de empezar trabajo nuevo.

- **El ciclo hoja → boli → escaneo → IA → base está cerrado y usado en obra
  real.** El paso 4 (la IA lee la hoja marcada) se implementó el 05/08 y salió
  a campo el 06/08.
- **Suite del motor: 213 pruebas en verde** (eran 191 el 07/08), ejecutada con
  `python -m unittest discover -s tests` desde
  `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`.
- **Norma `_SISTEMA` aplicada, 0 violaciones**, con `tests/test_jerarquia_sistema.py`
  de trinquete. El reordenamiento no perdió nada: los 233 ficheros publicados
  el 07/08 siguen todos rastreados.
- **Orueta ya se lee.** Eran 16 tajos propios de obra fuera del catálogo común,
  no uno. Se resolvió ampliando la tabla desde la ficha de la obra, sin tocar
  el catálogo de las otras cinco.
- **El portal móvil vuelve a actualizarse**: llevaba dos semanas sirviendo los
  KPI del 25/07.
- **Los cuatro documentos de `_SISTEMA/docs/` ya se publican.** Ver el
  comentario del `.gitignore`: la lista blanca es lo que decide qué existe
  fuera de este disco, y un fichero nuevo que no se declare ahí no da error.

## Archivos CARDIVA de trabajo

| Elemento | Ruta |
|---|---|
| Guía de uso | `MANTENIMIENTOS\MANTENIMIENTO CARDIVA\APP_CARDIVA\README.md` |
| Ejemplo normalizado del 29/07/2026 | `MANTENIMIENTOS\MANTENIMIENTO CARDIVA\APP_CARDIVA\data\CARDIVA_20260729.json` |
| Plantilla autorizada | `MANTENIMIENTOS\MANTENIMIENTO CARDIVA\MANTENIMIENTO\PLANTILLA_PARTE_PREVENTIVO_CARDIVA_SAGARDE_INFORMATIZADO.docx` |
| Informe final del 29/07/2026 | `MANTENIMIENTOS\MANTENIMIENTO CARDIVA\MANTENIMIENTO\2026\PARTE_CARDIVA_29072026_FINAL.docx` y `.pdf` |

## Reglas de seguridad documental

- Trabajar únicamente con la plantilla y los partes que el usuario identifique
  expresamente como autorizados.
- No incorporar archivos en construcción ni deducir datos ausentes.
- Conservar los originales y escribir salidas nuevas salvo reemplazo
  autorizado.
- Mantener resultados y estados sin código de colores.
- Validar el DOCX renderizado y el PDF antes de declarar finalizado un informe.

## Elementos ocultos de la raíz (08/08/2026)

Nueve elementos no pueden moverse de la raíz: git busca `.gitignore` ahí,
GitHub Pages busca `.nojekyll`, y Claude, Gemini y Codex buscan `CLAUDE.md`,
`GEMINI.md`, `.claudeignore` y sus carpetas `.claude`, `.gemini`, `.agents` y
`.superpowers` en la raíz del proyecto. Moverlos rompería las herramientas.

En vez de moverlos se les puso el atributo *oculto* de Windows: no se desplaza
un solo byte y todo sigue funcionando igual — comprobado con `git status`
(sigue leyendo la lista blanca), las 6 skills rastreadas y la suite en verde.
También se ocultaron las cuatro carpetas `.claude` de los subproyectos de
`VARIOS`.

**Para volver a verlos**, cambiar `-bor` por `-bxor`:

```powershell
Set-Location "D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE"
foreach ($n in @('.gitignore','.nojekyll','CLAUDE.md','GEMINI.md','.claudeignore','.claude','.gemini','.agents','.superpowers')) {
  if (Test-Path $n) { (Get-Item $n -Force).Attributes = (Get-Item $n -Force).Attributes -bxor [IO.FileAttributes]::Hidden; "visible: $n" }
}
Get-ChildItem -Path "VARIOS" -Filter ".claude" -Directory -Recurse -Force | ForEach-Object {
  $_.Attributes = $_.Attributes -bxor [IO.FileAttributes]::Hidden
}
```

En el explorador de Windows también se ven activando *Ver → Elementos ocultos*,
sin tocar nada.
