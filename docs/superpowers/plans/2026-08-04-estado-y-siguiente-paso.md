# Dónde está el entorno Sagarde y qué viene ahora

Redactado el 04/08/2026 al cerrar la sesión. Sustituye como referencia de
estado a `2026-07-28-trabajo-restante-y-reparto.md`, que queda como histórico.

---

## El plan principal, con las palabras de Bixente

> *"Queríamos organizar una base de datos estándar por obra para que se fuera
> rellenando con las revisiones y sacar luego todas las apps y resultados a
> partir de ella. Ese era el plan principal."*

**Esa parte está hecha para las cuatro obras con seguimiento.** La base es
`ficha_obra.json` y de ella salen ya el panel, los KPI, el priorizador, el
informe ejecutivo, el Centro de Mando y el generador de hojas.

| obra | ubicaciones | avance | fuente |
|---|---|---|---|
| Obispo Orueta | 102 | 99.6 % | `ficha_obra.json` |
| Mungia | 62 | 79.8 % | `ficha_obra.json` |
| Bolueta | 97 | 43.5 % | `ficha_obra.json` |
| Gernika | 32 | 76.3 % | `ficha_obra.json` |
| Gorliz | — | sin revisiones | sin adaptador |

## El ciclo completo: 4 de 5 pasos

| paso | estado |
|---|---|
| 1 · La app genera la hoja **desde la base** | ✅ las 4 obras |
| 2 · Bixente marca en obra | ✅ |
| 3 · Escanea, o marca con pen digital | ✅ |
| 4 · **La IA traduce lo marcado** | ⛔ **es lo siguiente** |
| 5 · Eso alimenta la base | ✅ funciona con el sidecar |

---

## Lo siguiente: el paso 4

Diseño acordado y escrito en
`docs/superpowers/specs/2026-08-04-lectura-hojas-revision-design.md`.

**Idea central:** como la hoja se genera desde la base, ya sabemos qué se
imprimió. Sólo hay que leer **la diferencia**. La clave de cada celda la pone la
geometría; la IA sólo dice qué letra hay en un recorte de un centímetro.

### Orden de trabajo acordado

1. **Dar de alta `OBRA PRUEBA`** — obra ficticia, para no tocar datos reales.
2. **Generar su primera revisión** con el generador, que fija su distribución.
3. **Fabricar una segunda revisión con cambios conocidos.**
4. **Construir el lector** y comprobar que encuentra exactamente esos cambios.
5. **Contrastar con tinta real**: `REVISION MUNGIA 27072026.pdf` tiene 56
   trazos de pen y un sidecar de 213 celdas transcrito a mano — verdad conocida.

Los puntos 1 a 3 son la conversación siguiente.

---

## Deuda abierta, por si sale al paso

- **17 de 21 obras sin adaptador ni ficha.** Cada una pide su adaptador y una
  ronda corta de confirmación de estructura. Gorliz es la candidata natural.
- **La skill `sagarde-revision` que declara el `CLAUDE.md` no existe** en
  `.claude/skills/`. La del paso 4 tapará ese hueco.
- **La tarjeta del índice muestra `pct_estricto` y el panel `pct_ponderado`.**
  Por eso Mungia sale 77.6 fuera y 79.8 dentro. Viene de antes; unificarlo es
  decisión de Bixente.
- **El commit `7d91628`** (rama `claude/cool-bardeen-fc67fd`) haría el commit
  del `.bat` selectivo y quitaría el riesgo de publicar trabajo a medias. **No
  se fusionó**: cambiaría el flujo, porque el código `.py` dejaría de
  publicarse solo. Decisión pendiente.
- **`main` no tiene upstream configurado**, así que `git log origin/main..HEAD`
  sale vacío tanto si está publicado como si no. Hay que comparar contra
  `FETCH_HEAD`. Es un comando de comprobación que falla en silencio.

## Lo que se cerró el 04/08/2026

Seis commits, `c4af237`..`5ba14da`:

- La estructura confirmada gana sobre el adaptador — Bolueta 101 → 97
- Obispo Orueta entra en la base — 102 ubicaciones, 99.6 %
- Una casilla en blanco no baja un estado conocido — Mungia vuelve a 79.8
- Una obra sin revisiones no es una obra al 0 % — Gorliz
- Los avisos del Centro de Mando caducan a los 400 días
- El registro del entorno IA compartido y la skill de CARDIVA
