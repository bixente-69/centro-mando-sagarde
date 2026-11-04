# B · Auditoría por mutación de la suite de pruebas

**Fecha:** 04/11/2026 · **Rama:** `nube/mutaciones-suite` · **Alcance:** solo pruebas; **no se ha tocado código de producción** (`git diff` de ficheros versionados vacío; solo hay ficheros nuevos).
**Método:** `CLAUDE.md` §3 («probar por mutación»): romper el código a propósito y comprobar que alguna prueba se entera.

## 1. Resumen (hechos)

- Se aplicaron **173 mutaciones** simples a 8 módulos que determinan las cifras de obra. **Sobrevivieron 50 (29 %)**: la suite siguió en verde. Los 50 se **reconfirmaron contra la suite completa** (1726 pruebas), no solo contra las pruebas relacionadas.
- **47 de las 50 mueren con pruebas nuevas** (58 pruebas en 6 ficheros `tests/test_mutaciones_*.py`). Las 3 restantes no se pueden matar: 2 son mutantes equivalentes (`CC03`, `CC05`) y 1 necesita un PDF real (`RH01`).
- Reparto: `motor_informes.py` **21 de 30**, `rejilla_hoja.py` 10 de 26, `priorizador_trabajos.py` 6 de 24, `ficha_obra.py` 5 de 24, `entregas_materiales.py` 5 de 27, `claves_correcciones.py` 3 de 7, `validar_revision.py` **0 de 25**, `aplicar_revision.py` **0 de 10**.
- Interpretación mía (no medida): la validación y aplicación de revisiones está bien blindada; el hueco serio está en **el cálculo de los KPI y los bloqueos** (`motor_informes.py`), que es precisamente lo que `CLAUDE.md` §3 manda comparar («el porcentaje redondeado es un criterio ciego; comparar el desglose»). Ninguna prueba existente fijaba el desglose `x/m/slash/vacio` de `kpis_snapshot` ni los umbrales de `detectar_bloqueos`.

## 2. La suite en la nube: qué corre y qué no

| Suite | Pruebas | Tiempo real | Resultado |
|---|---:|---:|---|
| `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests` | 1726 | 72,7 s (1 min 15 s con arranque) | 1 fallo, 34 errores, 74 omitidas |
| `_SISTEMA/MOTOR/tests` | 99 | 0,3 s | 1 fallo |
| Misma suite principal **con** las 58 pruebas nuevas | 1784 | 72,8 s | **idéntico**: los mismos 35 fallos/errores y 74 omitidas |

Los 35 fallos/errores de la suite principal son todos de entorno, ninguno de los módulos auditados:

| Nº | Prueba(s) | Causa |
|---:|---|---|
| 20 | `test_sembrar_ficha_obra` | `sembrar_ficha_obra.py:28` fija `RAIZ = r'D:\Nueva carpeta\OneDrive\COPIA SEGURIDAD SAGARDE'`; en la nube esa ruta no existe. Consecuencia: **ese módulo no es auditable por mutación fuera del PC de Bixente**. |
| 13 | `test_orden_empresas_y_generar_personal` (12) y `test_personal_sin_cobertura` (1, falla al importar) | Falta el módulo Python `playwright`. No se instaló (norma: sin dependencias nuevas). Es la causa también de 67 de las 74 omitidas. |
| 1 | `test_adaptar_revision_tinta` (caso real Mungia 27/07) | Ejecuta `git show 5c90dec:…`; el clon de la nube es superficial (`git rev-parse --is-shallow-repository` = `true`) y ese commit no existe. |
| 1 | `test_panel_server` (ruta «relativa a unidad de Windows») | Devuelve 500 en vez de 400. La prueba modela `ntpath.join` de Windows; **parece** dependiente de plataforma, pero no lo he investigado. |

`_SISTEMA/MOTOR/tests`: 1 fallo, `test_mapa_mental…rutas_muertas`: el mapa declara rutas (p. ej. `.claude/launch.json`) que la lista blanca no versiona y que no existen en el clon.

Omitidas (74): 67 por Playwright; el resto: 3 «Orueta no tiene ficha_obra.json», 2 «el .bat solo corre en Windows», 1 «no existe una hoja PDF real de Bolueta», y 1 más sin motivo legible en el modo detallado.

## 3. Método

1. **Arnés fuera del repo** (80 líneas, `unittest` + biblioteca estándar; no versionado): copia el fichero con `cp -p` fuera del repo, cambia **una** línea, ejecuta las pruebas relacionadas, restaura con `cp -p` desde la copia y comprueba que el fichero queda byte a byte idéntico. Nunca se usó `git checkout --`. `git status` se comprobó entre tandas y al final: ningún fichero versionado modificado.
2. **Una mutación está muerta si falla alguna prueba que no fallaba en la línea base.** Se compara el *conjunto* de pruebas que fallan, no el código de salida, para no confundir los fallos de entorno de la nube con muertes.
3. **Pruebas relacionadas por módulo** (línea base, todas en verde salvo lo ya dicho): `motor_informes` 349 pruebas (`test_motor_informes`, `test_informe_ejecutivo*`, `test_panel*`, `test_adaptadores_garaje`, `test_prioridades*`, `test_snapshot_zesp_informe`; 36 s por mutación) · `ficha_obra` 174 · `validar_revision` 122 · `aplicar_revision` 65 · `rejilla_hoja` 19 · `claves_correcciones` 140 · `entregas_materiales` 90 · `priorizador_trabajos` 195.
4. **Confirmación con la suite completa** de los 50 supervivientes (1726 pruebas, sin mis ficheros nuevos, ~76 s por mutación): 6 de `motor_informes` (`MI03`, `MI04`, `MI09`, `MI10`, `MI16`, `MI24`) sobre el propio repo, y los otros 44 en cuatro copias del árbol hechas fuera del repo y ejecutadas en paralelo (el repo no se tocó en esa fase). **Los 50 siguen vivos: ninguna prueba existente, en ningún fichero, los detecta.** Las ocho tandas restauraron el fichero idéntico.
5. **Para cada superviviente matable** se escribió una prueba en fichero nuevo y se demostró: pasa con el código original (58/58) y **falla con su mutación** (47/47; resultado en las tablas del §8).
6. `.gitignore`: `git check-ignore -v` sobre los 6 ficheros nuevos casa con la regla `!*.py` (línea 157), es decir, **no** quedan ignorados.

## 4. Supervivientes que importan

Ordenados por el daño que harían en silencio. La prueba nueva que mata cada uno está en el §8.

1. **`motor_informes.kpis_snapshot` — el desglose no lo fijaba nadie** (`MI09`, `MI10`, `MI03`, `MI04`, `MI06`). Contar las `M` como `/`, calcular los «vacíos» sin restar las iniciadas, pesar la `/` al 0,5 en vez de 0,25, devolver 100 % ante un snapshot vacío o puntuar un estado desconocido como terminado: la suite seguía verde. Es exactamente el caso del que avisa `CLAUDE.md` §3 (3 celdas sobre 2309 no mueven el `pct_ponderado`). El fichero `test_motor_informes.py` solo cubre `cobertura_encogida`.
2. **`motor_informes.detectar_bloqueos` entero** (`MI16`–`MI24`, 9 de 9 sobreviven). Umbrales (60/15 por planta, 15/30 por vivienda), `and`→`or` y hasta el orden de salida: nada. Lo que se publica como «planta rezagada» o «vivienda sin iniciar» no tenía ninguna comprobación. Igual: `sin_cambios_entre_ultimas`, `ranking_tareas`, `ranking_tareas_con_memoria`, `serie_tiempo` (`MI25`–`MI30`).
3. **`priorizador_trabajos`: una dependencia declarada sin `minimo` dejaba de bloquear** (`PT16`, `dep.get("minimo", 1.0)`→`0.0`). Es la familia de fallos de este proyecto (`CLAUDE.md` §2): lo declarado que el motor ignora en silencio. También sobrevivían el peso de `M` (`PT02`) y de `/` (`PT01`), y que ambos ficheros (`ESTADO_VALOR` y `SCORE`) pesen igual: un comentario lo exige en los dos y no había prueba que lo hiciera cumplir (ahora la hay).
4. **`rejilla_hoja`: la celda no heredaba la planta de su columna sin que nadie lo notara** (`RH23`) y la tolerancia en x de ±0,5 pt (`RH14`, `RH15`) no estaba probada. Es «poner la marca en la fila equivocada», lo que `CLAUDE.md` §9 llama el error caro.
5. **`entregas_materiales`**: dos líneas del mismo material en la misma entrega se pisaban en vez de sumarse (`EM17`: el mes publicaría la última cantidad, sin aviso); el aviso de «más de 30 días sin entregas» no tenía umbral ni signo comprobados (`EM22`, `EM23`); un `VERDADERO` de Excel contaba como 1 unidad (`EM04`); y una serie de fecha de Excel no se comprobaba (`EM01`).
6. **`ficha_obra`** (5 supervivientes; 19 de 24 mutaciones muertas). `FO20` es el más instructivo: existe una prueba cuyo nombre promete «una planta que se queda sin unidades se conserva vacía y marcada», y **pasa por casualidad**: la marca se pone al quitar la *primera* unidad, y como la prueba quita las dos, el resultado final sale igual. Una planta que conserva una unidad también se marcaba como retirada y nadie lo veía. Es el tipo de prueba que «parece verificar algo y no verifica».

## 5. Límites y cautelas

- **Las mutaciones las elegí yo a mano** (173), no con una herramienta automática ni con medida de cobertura. Que un módulo salga con 0 supervivientes (`validar_revision`, `aplicar_revision`) significa que *mis* 35 mutaciones murieron, no que sea inmutable.
- **Dos mutantes equivalentes** (`CC03`, `CC05`) y uno que exige un PDF real (`RH01`, `CELDAS_MINIMAS` solo actúa en `leer_pdf`): sin prueba nueva y sin hacer pasar por hecho lo contrario.
- **Pruebas de constantes**: `test_los_pesos_son_los_acordados` fija `0.25 / 0.60 / 1.0` literalmente. Es deliberado (cambiar un peso mueve todos los porcentajes de todas las obras y debe ser una decisión explícita), pero hará fallar la prueba cuando Bixente quiera cambiarlos; entonces se edita la prueba junto con los dos ficheros.
- **No se ha medido el efecto sobre datos reales**: no se regeneró ninguna obra ni se ejecutó `Actualizar_Sagarde.bat`. Como no se tocó producción, las cifras de obra no se mueven por construcción; no las he recalculado para confirmarlo. **Corrección (04/11/2026, tarde):** la primera versión de este informe citaba como cifras de control las de `CLAUDE.md` §3 (Mungia 79,8 · Gernika 76,3 · Bolueta 41,7 · Obispo Orueta 80,0). Están obsoletas: lo señalan los informes A (`A_fallos_silenciosos.md`) y E (`E_extremidades_y_enchufe.md` §5.2), y Obispo Orueta está cerrada. Las cifras vigentes son las de «Estado de hoy» del mapa mental. Aquí no se usan como referencia.
- `sembrar_ficha_obra.py` quedó **sin auditar** (sus pruebas no corren en la nube, ver §2).

## 6. Observaciones colaterales (no tocadas)

- **El mapa mental está desfasado en un punto:** dice que `reglas/CATALOGO_TAJOS.json` «no está en git» y que no hay `git checkout` que lo restaure. `git ls-files reglas` lo lista y `git check-ignore` no lo ignora. (Conviene corregir el mapa; no lo he hecho porque la tarea era solo de pruebas.)
- `sembrar_ficha_obra.py:28` con la ruta `D:\…` fija impide ejecutar su suite en cualquier otro sitio; si Bixente quiere auditarlo en la nube, habría que parametrizar la ruta (cambio de producción, no hecho).
- Para repetir la medida basta el arnés (80 líneas); si se quiere, se versiona en `_SISTEMA/MOTOR/scripts/` como herramienta aparte. Las pruebas nuevas se ejecutan con:

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests -p "test_mutaciones_*.py"
```

## 7. Resumen por módulo

| Módulo | Mutaciones | Sobreviven | Matadas por prueba nueva | Fichero de prueba nuevo |
|---|---:|---:|---:|---|
| `motor_informes.py` | 30 | 21 | 21 | `test_mutaciones_motor_informes.py` |
| `ficha_obra.py` | 24 | 5 | 5 | `test_mutaciones_ficha_obra.py` |
| `validar_revision.py` | 25 | 0 | 0 | — |
| `aplicar_revision.py` | 10 | 0 | 0 | — |
| `rejilla_hoja.py` | 26 | 10 | 9 | `test_mutaciones_rejilla_hoja.py` |
| `claves_correcciones.py` | 7 | 3 | 1 | `test_mutaciones_claves_correcciones.py` |
| `entregas_materiales.py` | 27 | 5 | 5 | `test_mutaciones_entregas_materiales.py` |
| `priorizador_trabajos.py` | 24 | 6 | 6 | `test_mutaciones_priorizador_trabajos.py` |
| **Total** | **173** | **50** | **47** | 6 ficheros, 58 pruebas |

## 8. Tablas completas por módulo

"Muere" = la mata alguna prueba que ya existía (se indica la primera). "SOBREVIVE" = ninguna de las 1726 pruebas existentes la detectó; la columna final dice qué prueba nueva la mata.

### `motor_informes.py`

| ID | Línea | Mutación | ¿Sobrevivió? | Prueba añadida / quién la mata |
|---|---:|---|---|---|
| MI01 | 37 | `'M': 0.60` → `'M': 0.75` | muere | — (ya la mata `TestAdaptadoresGaraje.test_cada_revision_acumula_un_punto_de_historico_pct` y 3 más) |
| MI02 | 37 | `'X': 1.0` → `'X': 0.9` | muere | — (ya la mata `TestAdaptadoresGaraje.test_cada_revision_acumula_un_punto_de_historico_pct` y 9 más) |
| MI03 | 37 | `'/': 0.25` → `'/': 0.5` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestDetectarBloqueos.test_los_bloqueos_salen_del_menos_avanzado_al_mas_avanzado` |
| MI04 | 48 | `return 0.0` → `return 100.0` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestKpisSnapshotDesglose.test_un_snapshot_vacio_no_inventa_avance` |
| MI05 | 49 | `* 100` → `* 10` | muere | — (ya la mata `TestAdaptadoresGaraje.test_cada_revision_acumula_un_punto_de_historico_pct` y 9 más) |
| MI06 | 49 | `r['status'], 0)` → `r['status'], 1)` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestKpisSnapshotDesglose.test_un_estado_desconocido_no_suma_avance` |
| MI07 | 56 | `r['status'] == 'X'` → `r['status'] in ('X', 'M')` | muere | — (ya la mata `TestPanelAvanceCombinadoConGaraje.test_cabecera_combina_vivienda_y_garaje_en_una_sola_bolsa` y 1 más) |
| MI08 | 78 | `== 'X'` → `!= 'X'` | muere | — (ya la mata `TestOrdenYAgrupacionDePlantas.test_agrupa_terminadas_consecutivas_y_suma_sus_mediciones` y 4 más) |
| MI09 | 79 | `== 'M'` → `== '/'` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestKpisSnapshotDesglose.test_cada_estado_se_cuenta_en_su_propia_casilla` |
| MI10 | 81 | `total - x - m - s` → `total - x - m` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestKpisSnapshotDesglose.test_cada_estado_se_cuenta_en_su_propia_casilla` |
| MI11 | 84 | `_pct_estricto(snapshot), 1)` → `_pct_estricto(snapshot), 0)` | muere | — (ya la mata `TestPanelAvanceCombinadoConGaraje.test_cabecera_combina_vivienda_y_garaje_en_una_sola_bolsa` y 1 más) |
| MI12 | 85 | `_pct_ponderado(snapshot)` → `_pct_estricto(snapshot)` | muere | — (ya la mata `TestPanelAvanceCombinadoConGaraje.test_cabecera_combina_vivienda_y_garaje_en_una_sola_bolsa`) |
| MI13 | 112 | `< 2` → `<= 2` | muere | — (ya la mata `TestCoberturaEncogida.test_avisa_cuando_la_ultima_hoja_cubre_mucho_menos` y 1 más) |
| MI14 | 123 | `>= len(antes)` → `> len(antes)` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestCoberturaEncogidaEnElUmbral.test_justo_en_el_umbral_no_avisa` |
| MI15 | 123 | `if not antes or` → `if antes or` | muere | — (ya la mata `TestCoberturaEncogida.test_avisa_cuando_la_ultima_hoja_cubre_mucho_menos` y 1 más) |
| MI16 | 153 | `p < 60` → `p <= 60` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestDetectarBloqueos.test_planta_justo_en_el_60_no_es_rezagada` |
| MI17 | 153 | `> 15` → `>= 15` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestDetectarBloqueos.test_planta_con_diferencia_justo_de_15_no_es_rezagada` |
| MI18 | 153 | `> 15` → `> 5` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestDetectarBloqueos.test_planta_con_diferencia_justo_de_15_no_es_rezagada` |
| MI19 | 153 | ` and ` → ` or ` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestDetectarBloqueos.test_planta_con_diferencia_justo_de_15_no_es_rezagada` |
| MI20 | 172 | `p < 15` → `p <= 15` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestDetectarBloqueos.test_vivienda_justo_en_el_15_no_esta_sin_iniciar` |
| MI21 | 172 | `> 30` → `> 20` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestDetectarBloqueos.test_vivienda_con_diferencia_justo_de_30_no_esta_sin_iniciar` |
| MI22 | 172 | ` and ` → ` or ` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestDetectarBloqueos.test_vivienda_con_avance_normal_no_se_marca_aunque_la_otra_vaya_muy_por_delante` |
| MI23 | 167 | `< 2` → `<= 2` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestDetectarBloqueos.test_vivienda_sin_iniciar_se_detecta_con_sus_cifras` |
| MI24 | 180 | `key=lambda b: b['avance'])` → `key=lambda b: b['avance'], reverse=True)` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestDetectarBloqueos.test_los_bloqueos_salen_del_menos_avanzado_al_mas_avanzado` |
| MI25 | 185 | `< 2` → `<= 2` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestSinCambiosEntreUltimas.test_dos_revisiones_identicas_no_tienen_cambios` |
| MI26 | 189 | `} == {` → `} != {` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestSinCambiosEntreUltimas.test_dos_revisiones_identicas_no_tienen_cambios` |
| MI27 | 232 | ` and nombre not in activos` → ` and nombre in activos` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestRankingsYSeries.test_ranking_con_memoria_anade_solo_lo_terminado_y_ausente` |
| MI28 | 234 | `100.0` → `0.0` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestRankingsYSeries.test_ranking_con_memoria_anade_solo_lo_terminado_y_ausente` |
| MI29 | 217 | `x[1])` → `x[1], reverse=True)` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestRankingsYSeries.test_ranking_de_tareas_va_de_menos_a_mas_avanzada` |
| MI30 | 199 | `len(recs)` → `len(recs) + 1` | **SOBREVIVE** | **sí** → mata `test_mutaciones_motor_informes.py`: `TestRankingsYSeries.test_serie_de_tiempo_lleva_total_y_porcentajes_de_cada_revision` |

### `ficha_obra.py`

| ID | Línea | Mutación | ¿Sobrevivió? | Prueba añadida / quién la mata |
|---|---:|---|---|---|
| FO01 | 87 | `'pendiente': 'P', 'p': 'P', '': 'P'` → `'pendiente': 'P', 'p': 'P', '': '?'` | muere | — (ya la mata `TestParidadConFlujoDigital.test_blanco_digital_usado_sobre_interrogacion_aplica_P` y 9 más) |
| FO02 | 87 | `'n': 'N'` → `'n': 'P'` | muere | — (ya la mata `TestAplicacionPura.test_varias_celdas_combinan_actualizar_conservar_y_n_explicita` y 3 más) |
| FO03 | 86 | `'m': 'M'` → `'m': 'X'` | muere | — (ya la mata `TestDiscrepanciaDeClavesExistentes.test_paridad_exacta_con_clave_de_fixture_en_mayuscula` y 13 más) |
| FO04 | 150 | `.strip().lower()` → `.lower()` | **SOBREVIVE** | **sí** → mata `test_mutaciones_ficha_obra.py`: `TestNormalizarEstado.test_quita_espacios_y_pasa_a_minusculas` |
| FO05 | 278 | `'M': 'M'` → `'M': 'X'` | muere | — (ya la mata `TestSnapshotDesdeFicha.test_ids_canonicos_distinguen_portales_homonimos_al_reimportar`) |
| FO06 | 278 | `'P': ''` → `'P': 'X'` | muere | — (ya la mata `TestSnapshotDesdeFicha.test_pendiente_confirmado_viaja_como_vacio` y 1 más) |
| FO07 | 299 | `len(grupo) > 1` → `len(grupo) >= 1` | muere | — (ya la mata `TestSnapshotDesdeFicha.test_devuelve_las_claves_que_espera_el_motor` y 1 más) |
| FO08 | 337 | `if not dato:` → `if dato:` | muere | — (ya la mata `TestSnapshotDesdeFicha.test_devuelve_el_nombre_del_tajo_no_su_id` y 8 más) |
| FO09 | 340 | `estado is None` → `estado is not None` | muere | — (ya la mata `TestSnapshotDesdeFicha.test_desconocido_se_excluye_del_snapshot` y 7 más) |
| FO10 | 590 | `MAPA_ESTADO.get(estado_norm, '?')` → `MAPA_ESTADO.get(estado_norm, 'P')` | muere | — (ya la mata `TestEstados.test_estado_desconocido_se_guarda_como_desconocido`) |
| FO11 | 592 | `nuevo == '?' and estado_norm` → `nuevo == '?' and not estado_norm` | muere | — (ya la mata `TestEstados.test_estado_desconocido_se_guarda_como_desconocido`) |
| FO12 | 603 | `if not estado_norm and anterior is not None:` → `if not estado_norm and anterior is None:` | muere | — (ya la mata `TestParidadConFichaObra.test_blanco_digital_sobre_interrogacion_se_conserva_como_actualizar` y 8 más) |
| FO13 | 603 | `if not estado_norm and` → `if estado_norm and` | muere | — (ya la mata `TestParidadConFichaObra.test_blanco_digital_sobre_interrogacion_se_conserva_como_actualizar` y 8 más) |
| FO14 | 610 | `anterior.get('v') != nuevo` → `anterior.get('v') == nuevo` | muere | — (ya la mata `TestEstados.test_la_ultima_revision_manda_aunque_baje_de_X` y 3 más) |
| FO15 | 616 | `anterior['r'] = rev_id` → `pass` | **SOBREVIVE** | **sí** → mata `test_mutaciones_ficha_obra.py`: `TestMismoEstadoEnOtraRevision.test_confirmar_el_mismo_estado_actualiza_fecha_y_revision` |
| FO16 | 628 | `if revision and not any` → `if revision and any` | muere | — (ya la mata `TestActualizarDesdeSnapshot.test_registra_la_revision` y 1 más) |
| FO17 | 994 | `{'X', 'M', '/'}` → `{'X', 'M'}` | muere | — (ya la mata `TestRetirarEstructuraAusenteEnHoja.test_si_lo_retirado_guarda_avance_no_se_retira_nada`) |
| FO18 | 1029 | `if con_avance:` → `if not con_avance:` | muere | — (ya la mata `TestRetirarEstructuraAusenteEnHoja.test_retira_unidad_y_tajo_y_deja_exclusion` y 4 más) |
| FO19 | 1034 | `if clave in estados:` → `if clave not in estados:` | muere | — (ya la mata `TestRetirarEstructuraAusenteEnHoja.test_retira_unidad_y_tajo_y_deja_exclusion` y 1 más) |
| FO20 | 1056 | `if not planta['ubicaciones']:` → `if planta['ubicaciones']:` | **SOBREVIVE** | **sí** → mata `test_mutaciones_ficha_obra.py`: `TestRetirarEstructuraCasosLimite.test_una_planta_que_conserva_una_unidad_no_se_marca_retirada` |
| FO21 | 1064 | `bool(unidades or informe['celdas_retiradas'])` → `bool(unidades)` | **SOBREVIVE** | **sí** → mata `test_mutaciones_ficha_obra.py`: `TestRetirarEstructuraCasosLimite.test_retirar_solo_un_tajo_cuenta_como_retirado` |
| FO22 | 566 | `t.get('orden') or 9999` → `t.get('orden') or 0` | **SOBREVIVE** | **sí** → mata `test_mutaciones_ficha_obra.py`: `TestTajoNuevoSinOrden.test_un_tajo_sin_orden_se_coloca_el_ultimo` |
| FO23 | 1043 | `!= u['portal_id']` → `== u['portal_id']` | muere | — (ya la mata `TestRetirarEstructuraAusenteEnHoja.test_retira_unidad_y_tajo_y_deja_exclusion` y 2 más) |
| FO24 | 1050 | `!= u['unidad']` → `== u['unidad']` | muere | — (ya la mata `TestRetirarEstructuraAusenteEnHoja.test_retira_unidad_y_tajo_y_deja_exclusion` y 1 más) |

### `validar_revision.py`

| ID | Línea | Mutación | ¿Sobrevivió? | Prueba añadida / quién la mata |
|---|---:|---|---|---|
| VR01 | 28 | `('X', 'M', '/', '', 'N')` → `('X', 'M', '/', '')` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_el_codigo_corto_antiguo_del_cuarto_tecnico_tambien_se_traduce` y 9 más) |
| VR02 | 31 | `(*ALFABETO_HOJA_DIGITAL, 'P')` → `(*ALFABETO_HOJA_DIGITAL,)` | muere | — (ya la mata `TestCutoverGenerarTodos.test_paridad_exacta_guarda_el_resultado_del_motor_nuevo` y 3 más) |
| VR03 | 75 | `not in CONFIANZAS_VALIDAS` → `in CONFIANZAS_VALIDAS` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_alias_historico_impreso_vuelve_al_id_canonico` y 92 más) |
| VR04 | 170 | `strftime('%d/%m/%Y') == fecha` → `strftime('%d/%m/%Y') != fecha` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas` y 70 más) |
| VR05 | 179 | `len(partes) != 4` → `len(partes) != 3` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas` y 69 más) |
| VR06 | 179 | `not all(partes)` → `all(partes)` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas` y 69 más) |
| VR07 | 180 | `any(parte != parte.lower() for parte in partes[:3])` → `any(parte != parte.lower() for parte in partes[:2])` | muere | — (ya la mata `TestRegla2FormatoClave.test_regla_2_falla_con_formas_incorrectas`) |
| VR08 | 189 | `!= portal_id` → `== portal_id` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas` y 66 más) |
| VR09 | 199 | `vivienda_id in viviendas` → `vivienda_id not in viviendas` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas` y 68 más) |
| VR10 | 301 | `not resultado['errores'] and not` → `not resultado['errores'] or not` | muere | — (ya la mata `TestAplicacionPura.test_revision_no_aplicable_no_muta_aunque_no_sea_dry_run` y 6 más) |
| VR11 | 347 | `revision['obra'] != ficha_actual.get('id')` → `revision['obra'] == ficha_actual.get('id')` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas` y 71 más) |
| VR12 | 397 | `tajo not in ids_tajo` → `tajo in ids_tajo` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas` y 65 más) |
| VR13 | 405 | `estado_leido not in alfabeto_hoja` → `estado_leido in alfabeto_hoja` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas` y 63 más) |
| VR14 | 416 | `and estado_leido != ''` → `and estado_leido == ''` | muere | — (ya la mata `TestAplicacionPura.test_revision_no_aplicable_no_muta_aunque_no_sea_dry_run` y 3 más) |
| VR15 | 417 | `and not hoja_usada` → `and hoja_usada` | muere | — (ya la mata `TestAplicacionPura.test_aplicacion_no_muta_ficha_actual_y_devuelve_copia_profunda` y 26 más) |
| VR16 | 425 | `== 'dudosa'` → `== 'cierta'` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas` y 1 más) |
| VR17 | 431 | `== 'historial_consolidado'` → `!= 'historial_consolidado'` | muere | — (ya la mata `TestParidadConFichaObra.test_blanco_sin_estado_previo_produce_P_como_actualizar` y 9 más) |
| VR18 | 437 | `and not hoja_usada` → `and hoja_usada` | muere | — (ya la mata `TestParidadConFlujoDigital.test_blanco_digital_usado_sobre_interrogacion_aplica_P` y 3 más) |
| VR19 | 442 | `if not hoja_usada:` → `if hoja_usada:` | muere | — (ya la mata `TestParidadConFichaObra.test_blanco_sin_estado_previo_produce_P_como_actualizar` y 9 más) |
| VR20 | 449 | `antes not in (None, '?')` → `antes not in (None, '?', 'X')` | muere | — (ya la mata `TestParidadConFichaObra.test_blanco_no_baja_X_como_actualizar` y 5 más) |
| VR21 | 449 | `antes not in (None, '?')` → `antes not in (None,)` | muere | — (ya la mata `TestParidadConFlujoDigital.test_blanco_digital_usado_sobre_interrogacion_aplica_P` y 5 más) |
| VR22 | 467 | `estado_leido.lower()` → `estado_leido` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_claves_sin_resolver_generan_avisos_y_no_abortan_las_validas` y 46 más) |
| VR23 | 468 | `antes == despues` → `antes != despues` | muere | — (ya la mata `TestAdaptarRevisionHtml.test_n_se_conserva_para_que_la_aplique_el_validador` y 20 más) |
| VR24 | 298 | `acciones.count('conservar')` → `acciones.count('actualizar')` | muere | — (ya la mata `TestResultadoYAislamiento.test_resultado_es_consumible_y_resume_acciones`) |
| VR25 | 372 | `== 'historial_consolidado'` → `!= 'historial_consolidado'` | muere | — (ya la mata `TestCutoverGenerarTodos.test_discrepancia_de_una_obra_no_impide_actualizar_la_siguiente` y 11 más) |

### `aplicar_revision.py`

| ID | Línea | Mutación | ¿Sobrevivió? | Prueba añadida / quién la mata |
|---|---:|---|---|---|
| AR01 | 26 | `dry_run or not resultado['aplicable']` → `dry_run and not resultado['aplicable']` | muere | — (ya la mata `TestAplicacionPura.test_dry_run_por_defecto_no_muta_ni_devuelve_ficha_actualizada` y 3 más) |
| AR02 | 26 | `dry_run or` → `not dry_run or` | muere | — (ya la mata `TestAdaptarRevisionPdfDigital.test_discrepancia_documentada_si_falta_el_registro_de_estado` y 44 más) |
| AR03 | 29 | `copy.deepcopy(ficha_actual)` → `ficha_actual` | muere | — (ya la mata `TestAplicacionPura.test_aplicacion_no_muta_ficha_actual_y_devuelve_copia_profunda` y 2 más) |
| AR04 | 31 | `if estados is None:` → `if estados is not None:` | muere | — (ya la mata `TestAdaptarRevisionPdfDigital.test_lo_que_no_imprime_marca_no_se_toca_en_ningun_camino` y 17 más) |
| AR05 | 36 | `!= 'actualizar'` → `== 'actualizar'` | muere | — (ya la mata `TestAdaptarRevisionPdfDigital.test_discrepancia_documentada_si_falta_el_registro_de_estado` y 34 más) |
| AR06 | 39 | `celda['despues']` → `celda['antes']` | muere | — (ya la mata `TestAdaptarRevisionPdfDigital.test_discrepancia_documentada_si_falta_el_registro_de_estado` y 34 más) |
| AR07 | 40 | `revision['fecha']` → `''` | muere | — (ya la mata `TestAplicacionPura.test_aplicacion_no_muta_ficha_actual_y_devuelve_copia_profunda` y 2 más) |
| AR08 | 41 | `revision['revision_id']` → `''` | muere | — (ya la mata `TestAplicacionPura.test_aplicacion_no_muta_ficha_actual_y_devuelve_copia_profunda` y 3 más) |
| AR09 | 44 | `= True` → `= False` | muere | — (ya la mata `TestAplicacionPura.test_aplicacion_no_muta_ficha_actual_y_devuelve_copia_profunda` y 29 más) |
| AR10 | 24 | `= False` → `= True` | muere | — (ya la mata `TestAplicacionPura.test_dry_run_por_defecto_no_muta_ni_devuelve_ficha_actualizada` y 3 más) |

### `rejilla_hoja.py`

| ID | Línea | Mutación | ¿Sobrevivió? | Prueba añadida / quién la mata |
|---|---:|---|---|---|
| RH01 | 52 | `= 50` → `= 5` | **SOBREVIVE** | **no** (necesita un PDF real (`CELDAS_MINIMAS` solo actúa en `leer_pdf`); sin prueba nueva) |
| RH02 | 60 | `r'\s+', ' '` → `r'\s', ' '` | **SOBREVIVE** | **sí** → mata `test_mutaciones_rejilla_hoja.py`: `TestLimpio.test_colapsa_cualquier_racha_de_espacios_en_uno` |
| RH03 | 115 | `clave not in indice` → `clave in indice` | muere | — (ya la mata `TestTajosPropiosDeObra.test_las_demas_obras_no_ganan_nombres`) |
| RH04 | 144 | `clave not in indice` → `clave in indice` | muere | — (ya la mata `TestTajosPropiosDeObra.test_el_catalogo_comun_manda_en_caso_de_choque` y 1 más) |
| RH05 | 165 | `filas[:-2]` → `filas[:-1]` | **SOBREVIVE** | **sí** → mata `test_mutaciones_rejilla_hoja.py`: `TestIdentificacionDeLaTabla.test_dos_filas_no_bastan_para_ser_una_tabla_de_revision` |
| RH06 | 166 | `len(celdas) != 1` → `len(celdas) == 1` | muere | — (ya la mata `TestCabeceraDeGrupoNoEsUnTajo.test_la_cabecera_de_grupo_no_produce_un_tajo` y 4 más) |
| RH07 | 169 | `'·' not in candidato` → `'·' in candidato` | muere | — (ya la mata `TestCabeceraDeGrupoNoEsUnTajo.test_la_cabecera_de_grupo_no_produce_un_tajo` y 4 más) |
| RH08 | 171 | `< 2` → `< 1` | **SOBREVIVE** | **sí** → mata `test_mutaciones_rejilla_hoja.py`: `TestIdentificacionDeLaTabla.test_la_fila_siguiente_a_la_identificacion_debe_ser_la_de_plantas` |
| RH09 | 185 | `len(cabeza) < 2` → `len(cabeza) < 1` | **SOBREVIVE** | **sí** → mata `test_mutaciones_rejilla_hoja.py`: `TestIdentificacionDeLaTabla.test_una_identificacion_con_una_sola_etiqueta_se_para` |
| RH10 | 194 | `len(etiquetas) > 2` → `len(etiquetas) >= 2` | **SOBREVIVE** | **sí** → mata `test_mutaciones_rejilla_hoja.py`: `TestIdentificacionDeLaTabla.test_con_dos_etiquetas_no_hay_obra_y_son_bloque_y_portal` |
| RH11 | 195 | `etiquetas[-2], etiquetas[-1]` → `etiquetas[-1], etiquetas[-2]` | muere | — (ya la mata `TestUnaCeldaPorTajoYVivienda.test_se_genera_la_celda_con_su_clave_completa`) |
| RH12 | 201 | `if t.upper().startswith('TAJO'):` → `if not t.upper().startswith('TAJO'):` | muere | — (ya la mata `TestCabeceraDeGrupoNoEsUnTajo.test_la_cabecera_de_grupo_no_produce_un_tajo` y 3 más) |
| RH13 | 215 | `if not t or` → `if t or` | muere | — (ya la mata `TestCabeceraDeGrupoNoEsUnTajo.test_la_cabecera_de_grupo_no_produce_un_tajo` y 2 más) |
| RH14 | 219 | `p['x0'] - 0.5 <= centro` → `p['x0'] + 0.5 <= centro` | **SOBREVIVE** | **sí** → mata `test_mutaciones_rejilla_hoja.py`: `TestToleranciaEnX.test_centro_dentro_de_la_tolerancia_por_la_izquierda_se_acepta` |
| RH15 | 219 | `centro <= p['x1'] + 0.5` → `centro < p['x1'] - 0.5` | **SOBREVIVE** | **sí** → mata `test_mutaciones_rejilla_hoja.py`: `TestToleranciaEnX.test_centro_dentro_de_la_tolerancia_por_la_derecha_se_acepta` |
| RH16 | 220 | `destino is None` → `destino is not None` | muere | — (ya la mata `TestCabeceraDeGrupoNoEsUnTajo.test_la_cabecera_de_grupo_no_produce_un_tajo` y 3 más) |
| RH17 | 230 | `p['declara'] != len(p['vivs'])` → `p['declara'] == len(p['vivs'])` | muere | — (ya la mata `TestCabeceraDeGrupoNoEsUnTajo.test_la_cabecera_de_grupo_no_produce_un_tajo` y 3 más) |
| RH18 | 230 | `is not None and` → `is None and` | muere | — (ya la mata `TestColumnaEnSuPlanta.test_si_la_cabecera_no_cuadra_con_la_rejilla_se_para`) |
| RH19 | 239 | `len(cs) < 2` → `len(cs) < 1` | muere | — (ya la mata `TestCabeceraDeGrupoNoEsUnTajo.test_la_cabecera_de_grupo_no_produce_un_tajo`) |
| RH20 | 242 | `crudo.startswith('Obs')` → `crudo.startswith('OBS')` | **SOBREVIVE** | **sí** → mata `test_mutaciones_rejilla_hoja.py`: `TestFilaDeObservaciones.test_una_fila_obs_no_se_toma_por_un_tajo` |
| RH21 | 244 | `DISTINTIVOS.sub('', crudo).strip()` → `crudo.strip()` | muere | — (ya la mata `TestCabeceraDeGrupoNoEsUnTajo.test_la_cabecera_de_grupo_no_produce_un_tajo` y 1 más) |
| RH22 | 246 | `destino is None` → `destino is not None` | muere | — (ya la mata `TestCabeceraDeGrupoNoEsUnTajo.test_la_cabecera_de_grupo_no_produce_un_tajo` y 2 más) |
| RH23 | 256 | `col['planta']` → `plantas[0]['nombre']` | **SOBREVIVE** | **sí** → mata `test_mutaciones_rejilla_hoja.py`: `TestCeldaDeCadaPlanta.test_las_celdas_de_la_segunda_planta_no_se_atribuyen_a_la_primera` |
| RH24 | 256 | `col['viv']` → `columnas[0]['viv']` | muere | — (ya la mata `TestUnaCeldaPorTajoYVivienda.test_se_genera_la_celda_con_su_clave_completa`) |
| RH25 | 206 | `forma.group(1) if forma else t` → `t` | muere | — (ya la mata `TestColumnaEnSuPlanta.test_las_viviendas_van_a_la_planta_que_las_contiene` y 1 más) |
| RH26 | 208 | `'x0': bbox[0], 'x1': bbox[2]` → `'x0': bbox[2], 'x1': bbox[0]` | muere | — (ya la mata `TestCabeceraDeGrupoNoEsUnTajo.test_la_cabecera_de_grupo_no_produce_un_tajo` y 3 más) |

### `claves_correcciones.py`

| ID | Línea | Mutación | ¿Sobrevivió? | Prueba añadida / quién la mata |
|---|---:|---|---|---|
| CC01 | 10 | `TRAMOS = 4` → `TRAMOS = 3` | muere | — (ya la mata `TestActualizarDesdeSnapshot.test_reclama_las_correcciones_manuales` y 12 más) |
| CC02 | 11 | `'__'` → `'_'` | muere | — (ya la mata `TestActualizarDesdeSnapshot.test_reclama_las_correcciones_manuales` y 11 más) |
| CC03 | 16 | `r'\s+'` → `r'\s'` | **SOBREVIVE** | **no** (equivalente: el sustituto es `''`, quitar la racha o cada blanco da el mismo texto) |
| CC04 | 16 | `str(unidad or '')` → `str(unidad)` | **SOBREVIVE** | **sí** → mata `test_mutaciones_claves_correcciones.py`: `TestNormalizarUnidad.test_una_unidad_ausente_es_texto_vacio_no_la_palabra_None` |
| CC05 | 21 | `clave or ''` → `clave` | **SOBREVIVE** | **no** (equivalente: `str(None)` da `'None'`, que tampoco tiene cuatro tramos) |
| CC06 | 22 | `!= TRAMOS` → `== TRAMOS` | muere | — (ya la mata `TestActualizarDesdeSnapshot.test_reclama_las_correcciones_manuales` y 12 más) |
| CC07 | 25 | `normalizar_unidad(unidad)` → `unidad` | muere | — (ya la mata `TestCorrecciones.test_recompone_una_unidad_partida_por_el_extractor` y 3 más) |

### `entregas_materiales.py`

| ID | Línea | Mutación | ¿Sobrevivió? | Prueba añadida / quién la mata |
|---|---:|---|---|---|
| EM01 | 134 | `30000 < v < 80000` → `30000 < v < 8000` | **SOBREVIVE** | **sí** → mata `test_mutaciones_entregas_materiales.py`: `TestCantidadYFechaDeCelda.test_una_serie_de_excel_dentro_del_rango_es_una_fecha` |
| EM02 | 164 | `\d{3}` → `\d{4}` | muere | — (ya la mata `TestLecturaDelRegistro.test_cantidad_en_texto_ambigua_se_rechaza_y_la_clara_se_acepta`) |
| EM03 | 167 | `s.replace(',', '.')` → `s` | muere | — (ya la mata `TestLecturaDelRegistro.test_cantidad_en_texto_ambigua_se_rechaza_y_la_clara_se_acepta`) |
| EM04 | 159 | `isinstance(v, bool) or v is None` → `v is None` | **SOBREVIVE** | **sí** → mata `test_mutaciones_entregas_materiales.py`: `TestCantidadYFechaDeCelda.test_una_casilla_booleana_no_es_una_cantidad` |
| EM05 | 193 | `if not s:` → `if s:` | muere | — (ya la mata `TestInformeDeMateriales.test_por_albaran_distingue_la_entrega_en_mano_y_la_que_no_tiene_numero` y 5 más) |
| EM06 | 195 | `s in _EN_MANO or bool(_clave_texto(albaran))` → `s in _EN_MANO and bool(_clave_texto(albaran))` | muere | — (ya la mata `TestInformeDeMateriales.test_por_albaran_distingue_la_entrega_en_mano_y_la_que_no_tiene_numero` y 5 más) |
| EM07 | 195 | `or bool(` → `or not bool(` | muere | — (ya la mata `TestInformeDeMateriales.test_por_albaran_distingue_la_entrega_en_mano_y_la_que_no_tiene_numero` y 4 más) |
| EM08 | 205 | `f.month - 1` → `f.month` | muere | — (ya la mata `TestAgrupacion.test_acumulado_recoge_todo_lo_entregado_por_mes_y_total` y 11 más) |
| EM09 | 243 | `all(x in (None, '') for x in valores)` → `any(x in (None, '') for x in valores)` | muere | — (ya la mata `TestAgrupacion.test_acumulado_recoge_todo_lo_entregado_por_mes_y_total` y 53 más) |
| EM10 | 246 | `f is None` → `f is not None` | muere | — (ya la mata `TestAgrupacion.test_acumulado_recoge_todo_lo_entregado_por_mes_y_total` y 53 más) |
| EM11 | 250 | `if not material:` → `if material:` | muere | — (ya la mata `TestAgrupacion.test_acumulado_recoge_todo_lo_entregado_por_mes_y_total` y 50 más) |
| EM12 | 257 | `cant == 0` → `cant != 0` | muere | — (ya la mata `TestAgrupacion.test_acumulado_recoge_todo_lo_entregado_por_mes_y_total` y 51 más) |
| EM13 | 260 | `f > hoy` → `f < hoy` | muere | — (ya la mata `TestHerramientaMaterialesXlsx.test_comprobar_un_libro_de_entregas_al_dia_esta_ok` y 8 más) |
| EM14 | 269 | `if firma in vistas:` → `if firma not in vistas:` | muere | — (ya la mata `TestAgrupacion.test_acumulado_recoge_todo_lo_entregado_por_mes_y_total` y 62 más) |
| EM15 | 282 | `e.get('fila', 0)))` → `e.get('fila', 0)), reverse=True)` | muere | — (ya la mata `TestCompatibilidadConElLectorDeSiempre.test_resumen_con_las_mismas_claves_que_leer_materiales` y 3 más) |
| EM16 | 307 | `sk and sk not in` → `sk and sk in` | muere | — (ya la mata `TestAgrupacion.test_misma_fecha_distinto_albaran_son_dos_columnas` y 12 más) |
| EM17 | 367 | `(fila[i] or 0) + e['cantidad']` → `e['cantidad']` | **SOBREVIVE** | **sí** → mata `test_mutaciones_entregas_materiales.py`: `TestVariasLineasDeLaMismaEntrega.test_dos_lineas_del_mismo_material_y_albaran_se_suman` |
| EM18 | 374 | `ant + total` → `total` | muere | — (ya la mata `TestAgrupacion.test_totales_y_arrastre_entre_meses`) |
| EM19 | 376 | `previo.get(k, 0) + sum` → `sum` | muere | — (ya la mata `TestAgrupacion.test_acumulado_recoge_todo_lo_entregado_por_mes_y_total` y 2 más) |
| EM21 | 397 | `ent[-1]['fecha']` → `ent[0]['fecha']` | muere | — (ya la mata `TestCompatibilidadConElLectorDeSiempre.test_resumen_con_las_mismas_claves_que_leer_materiales`) |
| EM22 | 412 | `(hoy - g['ultima_fecha']).days` → `(g['ultima_fecha'] - hoy).days` | **SOBREVIVE** | **sí** → mata `test_mutaciones_entregas_materiales.py`: `TestAvisoDeEntregasAntiguas.test_cuarenta_dias_sin_entregas_avisa_con_los_dias_en_positivo` |
| EM23 | 421 | `> 30` → `> 300` | **SOBREVIVE** | **sí** → mata `test_mutaciones_entregas_materiales.py`: `TestAvisoDeEntregasAntiguas.test_cuarenta_dias_sin_entregas_avisa_con_los_dias_en_positivo` |
| EM24 | 372 | `previo.get(k, 0)` → `previo.get(k, 1)` | muere | — (ya la mata `TestAgrupacion.test_totales_y_arrastre_entre_meses` y 2 más) |
| EM20 | 381 | `if not entrega_completa` → `if entrega_completa` | muere | — (ya la mata `TestSuministradorYAlbaran.test_cuenta_las_lineas_incompletas_por_mes` y 1 más) |
| EM25 | 131 | `return v.date()` → `return v` | muere | — (ya la mata `TestAgrupacion.test_acumulado_recoge_todo_lo_entregado_por_mes_y_total` y 63 más) |
| EM26 | 410 | `g['meses'][-1]['etiqueta']` → `g['meses'][0]['etiqueta']` | muere | — (ya la mata `TestCompatibilidadConElLectorDeSiempre.test_resumen_con_las_mismas_claves_que_leer_materiales`) |
| EM27 | 414 | `f['total']` → `f['total'] + 1` | muere | — (ya la mata `TestCompatibilidadConElLectorDeSiempre.test_resumen_con_las_mismas_claves_que_leer_materiales`) |

### `priorizador_trabajos.py`

| ID | Línea | Mutación | ¿Sobrevivió? | Prueba añadida / quién la mata |
|---|---:|---|---|---|
| PT01 | 18 | `"/": 0.25` → `"/": 0.5` | **SOBREVIVE** | **sí** → mata `test_mutaciones_priorizador_trabajos.py`: `TestPesosDeEstado.test_los_pesos_son_los_acordados` |
| PT02 | 18 | `"M": 0.60` → `"M": 0.40` | **SOBREVIVE** | **sí** → mata `test_mutaciones_priorizador_trabajos.py`: `TestDependencias.test_con_minimo_de_M_basta_una_M_pero_no_una_barra` |
| PT03 | 18 | `"X": 1.0` → `"X": 0.9` | muere | — (ya la mata `TestInvariantesCatalogo.test_el_minimo_de_una_dependencia_es_un_estado_valido` y 7 más) |
| PT04 | 24 | `"P": ""` → `"P": "X"` | muere | — (ya la mata `TestFiltradoZonasEspeciales.test_recalcula_todos_los_derivados_sin_mutar_las_prioridades` y 14 más) |
| PT05 | 57 | `.upper()` → `.lower()` | **SOBREVIVE** | **sí** → mata `test_mutaciones_priorizador_trabajos.py`: `TestPesosDeEstado.test_el_estado_se_normaliza_antes_de_pesarlo` |
| PT06 | 246 | `if not dato:` → `if dato:` | muere | — (ya la mata `TestCatalogoTajosConfirmado.test_un_alias_resuelve_igual_que_el_nombre_principal` y 47 más) |
| PT07 | 265 | `ESTADO_BASE_A_MOTOR.get(valor, "")` → `ESTADO_BASE_A_MOTOR.get(valor, "X")` | muere | — (ya la mata `TestEstadoDesdeFicha.test_conserva_el_estado_crudo_de_la_base` y 2 más) |
| PT08 | 550 | `edad_dias > 30` → `edad_dias > 3` | muere | — (ya la mata `TestAntiguedadEsAviso.test_la_edad_se_calcula_contra_la_fecha_que_se_pasa` y 2 más) |
| PT09 | 550 | `edad_dias is None or` → `edad_dias is None and` | muere | — (ya la mata `TestAntiguedadEsAviso.test_una_revision_vieja_ya_no_tumba_la_clasificacion` y 1 más) |
| PT10 | 567 | `estado_base == "N"` → `estado_base != "N"` | muere | — (ya la mata `TestCicloCompletoGarajeObraPrueba.test_alta_revision_y_priorizador_encadenados` y 26 más) |
| PT11 | 570 | `estado_base == "?"` → `estado_base == "P"` | muere | — (ya la mata `TestFiltradoZonasEspeciales.test_recalcula_todos_los_derivados_sin_mutar_las_prioridades` y 16 más) |
| PT12 | 587 | `estado == "X"` → `estado != "X"` | muere | — (ya la mata `TestCicloCompletoGarajeObraPrueba.test_alta_revision_y_priorizador_encadenados` y 15 más) |
| PT13 | 590 | `("externo", "coordinacion")` → `("externo",)` | muere | — (ya la mata `TestNoRegresionVivienda.test_todas_las_obras_registradas_conservan_sus_bytes`) |
| PT14 | 615 | `dep_id not in tajos_de_la_obra` → `dep_id in tajos_de_la_obra` | muere | — (ya la mata `TestCicloCompletoGarajeObraPrueba.test_alta_revision_y_priorizador_encadenados` y 10 más) |
| PT15 | 630 | `ESTADO_VALOR.get(dep_estado, 0.0)` → `ESTADO_VALOR.get(dep_estado, 1.0)` | muere | — (ya la mata `TestCicloCompletoGarajeObraPrueba.test_alta_revision_y_priorizador_encadenados`) |
| PT16 | 631 | `dep.get("minimo", 1.0)` → `dep.get("minimo", 0.0)` | **SOBREVIVE** | **sí** → mata `test_mutaciones_priorizador_trabajos.py`: `TestDependencias.test_una_dependencia_sin_minimo_exige_terminado` |
| PT17 | 637 | `dep_valor >= minimo` → `dep_valor > minimo` | muere | — (ya la mata `TestNoRegresionVivienda.test_priorizar_ficha_conserva_el_dict_completo_de_una_obra_real` y 1 más) |
| PT18 | 639 | `dep_valor < minimo` → `dep_valor <= minimo` | muere | — (ya la mata `TestFiltradoZonasEspeciales.test_recalcula_todos_los_derivados_sin_mutar_las_prioridades` y 4 más) |
| PT19 | 643 | `if bloqueos:` → `if not bloqueos:` | muere | — (ya la mata `TestCicloCompletoGarajeObraPrueba.test_alta_revision_y_priorizador_encadenados` y 13 más) |
| PT20 | 657 | `meta.get("orden", 9999)` → `meta.get("orden", 0)` | **SOBREVIVE** | **sí** → mata `test_mutaciones_priorizador_trabajos.py`: `TestOrdenPorDefecto.test_un_tajo_sin_orden_se_ordena_el_ultimo` |
| PT21 | 662 | `"Pendiente" if estado == "" else estado` → `estado` | muere | — (ya la mata `TestNoRegresionVivienda.test_priorizar_ficha_conserva_el_dict_completo_de_una_obra_real` y 1 más) |
| PT22 | 675 | `x["orden_ejecucion"], AMBITO_ORDEN` → `-x["orden_ejecucion"], AMBITO_ORDEN` | muere | — (ya la mata `TestNoRegresionVivienda.test_priorizar_ficha_conserva_el_dict_completo_de_una_obra_real` y 1 más) |
| PT23 | 593 | `propiedad == "desconocido" or item.get("desconocido")` → `propiedad == "desconocido" and item.get("desconocido")` | **SOBREVIVE** | **sí** → mata `test_mutaciones_priorizador_trabajos.py`: `TestTajoDesconocido.test_un_tajo_de_propiedad_desconocida_va_a_dudas` |
| PT24 | 604 | `item.get("omitido_ultima")` → `not item.get("omitido_ultima")` | muere | — (ya la mata `TestCicloCompletoGarajeObraPrueba.test_alta_revision_y_priorizador_encadenados` y 14 más) |

