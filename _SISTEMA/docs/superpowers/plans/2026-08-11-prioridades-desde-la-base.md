# Prioridades desde la base de obra — plan de implementación

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `superpowers:subagent-driven-development`
> (recomendada) o `superpowers:executing-plans` para ejecutar este plan tarea a
> tarea. Los pasos usan casillas (`- [ ]`) para el seguimiento.

**Objetivo:** que la pestaña Prioridades lea el estado de la base de cada obra
(`ficha_obra.json`) en vez de reconstruirlo desde el historial crudo, con el
orden y las dependencias saliendo siempre del catálogo, y que prevea qué se
desbloquea al terminar cada tajo.

**Arquitectura:** la base es el estado; el catálogo es la regla. Se sustituye
`_construir_estado()` por un lector de la base y se conserva intacta la cascada
de clasificación, la resolución por catálogo y el agrupado. En cada regeneración
el catálogo siembra `orden` y `deps` sobre la base, y lo que el catálogo no
conoce sale como pregunta en pantalla.

**Especificación:** `_SISTEMA/docs/superpowers/specs/2026-08-11-prioridades-desde-la-base-design.md`

**Stack:** Python 3 con biblioteca estándar. Pruebas con `unittest`.

---

## Restricciones globales

Se aplican a **todas** las tareas.

- **Pruebas con `unittest` de la biblioteca estándar. No introducir `pytest` ni
  ninguna dependencia nueva.** Bixente ejecuta todo con ficheros `.bat`.
- Suite completa:
  ```
  cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
  ```
  **Línea base medida el 11/08/2026: `Ran 213 tests` · `OK`.** Ninguna tarea
  puede dejar la suite por debajo de eso.
- **No ejecutar `Actualizar_Sagarde.bat` ni `Actualizar_Obras.bat`** durante la
  implementación: hacen `git add -A` y publican en `main`. Cualquier fichero
  mutado para una verificación se restaura antes de terminar la tarea.
- **El `.gitignore` es lista blanca** (`*` ignora todo y luego se permite). Un
  tipo de fichero nuevo exige tocar `.gitignore` y el `.bat` a la vez. Los
  `.md` de `_SISTEMA/docs/superpowers/plans/` y `specs/` ya están permitidos
  (líneas 57–58).
- **Norma `_SISTEMA`:** todo lo informático vive dentro de una carpeta
  `_SISTEMA`. `tests/test_jerarquia_sistema.py` falla si aparece un fichero
  técnico fuera.
- **No inventar datos de obra.** Toda dependencia, orden o equivalencia que no
  esté confirmada se queda sin declarar y sale como pregunta.
- **Estados:** `/` = tajo empezado · `M` = mínimo 50 % del tajo · `X` = tajo
  zanjado · `P` = pendiente confirmado · `?` = nadie lo ha mirado · `N` = no
  aplica. Los tres primeros miden el **mismo** trabajo a distinto porcentaje de
  su propio alcance. Si un estado significaría otro trabajo, es **otro tajo**.
- **Los KPIs no se mueven.** Al terminar, estas cifras deben ser idénticas:
  **Mungia 80.1 · Gernika 76.3 · Bolueta 43.5 · Orueta 99.7 · OBRA PRUEBA 6.4.**
- **Reportar siempre el antes/después a Bixente.** Aplicar en silencio una
  corrección que mueve cifras es repetir el problema desde el otro lado.
- **Trabajar en una rama**, no en `main`.

### Rutas

| | |
|---|---|
| Motor | `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/` |
| Catálogo | `<motor>/reglas/CATALOGO_TAJOS.json` |
| Pruebas | `<motor>/tests/` |
| Base de una obra | `SAGARDE OBRAS ABIERTAS/<OBRA>/INFORME SAGARDE IA/ficha_obra.json` |

---

## Tarea 1: Arnés de verificación y línea base

Sin esto no se puede demostrar el antes/después que exige el proyecto. Es lo
primero porque captura el estado actual **antes** de tocar nada.

**Ficheros:**
- Crear: `<motor>/tests/linea_base_prioridades.py`
- Crear: `<motor>/tests/test_linea_base_prioridades.py`

**Interfaces:**
- Produce: `medir_obra(ruta_prioridades) -> dict` con las claves
  `preguntas`, `unidades_verificar`, `ubicaciones`, `tajos_9999`,
  `unidades_no_vivienda`, `pct_por_obra`.

- [ ] **Paso 1: Escribir la prueba que falla**

```python
# tests/test_linea_base_prioridades.py
# -*- coding: utf-8 -*-
"""La linea base tiene que medir lo mismo que se midio a mano el 11/08/2026."""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from linea_base_prioridades import medir_prioridades


class TestLineaBase(unittest.TestCase):

    def test_cuenta_preguntas_unidades_y_ubicaciones(self):
        datos = {
            'resumen': {'preguntas_pendientes': 3},
            'items': [
                {'situacion': 'VERIFICAR', 'n_unidades': 4, 'ambito': 'vivienda'},
                {'situacion': 'LISTO', 'n_unidades': 7, 'ambito': 'edificio'},
            ],
            'detalle_items': [
                {'planta': 'PB', 'unidad': 'A'},
                {'planta': 'PB', 'unidad': 'A'},
                {'planta': '1', 'unidad': 'B'},
            ],
        }
        medida = medir_prioridades(datos)
        self.assertEqual(medida['preguntas'], 3)
        self.assertEqual(medida['unidades_verificar'], 4)
        self.assertEqual(medida['ubicaciones'], 2)
        self.assertEqual(medida['unidades_no_vivienda'], 7)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Paso 2: Ejecutarla y comprobar que falla**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_linea_base_prioridades -v
```
Esperado: `ModuleNotFoundError: No module named 'tests.linea_base_prioridades'`.

- [ ] **Paso 3: Implementar lo mínimo**

```python
# tests/linea_base_prioridades.py
# -*- coding: utf-8 -*-
"""Mide una salida de prioridades para poder comparar antes/despues.

No es una prueba: es la regla con la que se demuestra que un cambio hace lo
que dice. Se usa desde test_linea_base_prioridades.py y a mano.
"""
import json


def medir_prioridades(datos):
    items = datos.get('items') or []
    detalle = datos.get('detalle_items') or []
    ubicaciones = {(d.get('planta'), d.get('unidad')) for d in detalle}
    return {
        'preguntas': (datos.get('resumen') or {}).get('preguntas_pendientes', 0),
        'unidades_verificar': sum(
            i.get('n_unidades', 0) for i in items
            if i.get('situacion') == 'VERIFICAR'),
        'unidades_listas': sum(
            i.get('n_unidades', 0) for i in items
            if i.get('situacion') == 'LISTO'),
        'unidades_no_vivienda': sum(
            i.get('n_unidades', 0) for i in items
            if i.get('ambito') != 'vivienda'),
        'ubicaciones': len(ubicaciones),
        'celdas': len(detalle),
    }


def medir_fichero(ruta):
    with open(ruta, encoding='utf-8') as f:
        return medir_prioridades(json.load(f))


def tajos_sin_orden(ruta_ficha):
    """Tajos de la base con el centinela 9999 (sin posicion confirmada)."""
    with open(ruta_ficha, encoding='utf-8') as f:
        ficha = json.load(f)
    detalle = (ficha.get('tajos') or {}).get('detalle') or []
    return sorted(t['id'] for t in detalle if (t.get('orden') or 9999) >= 9999)
```

- [ ] **Paso 4: Ejecutar y comprobar que pasa**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_linea_base_prioridades -v
```
Esperado: `OK`.

- [ ] **Paso 5: Capturar la línea base real y guardarla en el plan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -c "
import json, sys
sys.path.insert(0, 'tests')
from linea_base_prioridades import medir_fichero, tajos_sin_orden
OBRAS = ['2025 GERNIKA 32V', '2026 MUNGIA ACR NEINOR', '2026 BOLUETA ACR',
         '2025 BILBAO OBISPO ORUETA', '2026 OBRA PRUEBA']
for o in OBRAS:
    p = '../%s/INFORME SAGARDE IA/prioridades_trabajos.json' % o
    fh = '../%s/INFORME SAGARDE IA/ficha_obra.json' % o
    print(o, json.dumps(medir_fichero(p), ensure_ascii=False))
    print('   9999:', tajos_sin_orden(fh))
"
```

Valores esperados (medidos el 11/08/2026 — si no coinciden, **parar y avisar**):
Bolueta `preguntas 26`, `unidades_verificar 104`, `ubicaciones 96`,
`unidades_no_vivienda 370`; Orueta 18 tajos en 9999.

- [ ] **Paso 6: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/linea_base_prioridades.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_linea_base_prioridades.py"
git commit -m "Medir la linea base de Prioridades antes de tocar el motor

Sin una medida previa no se puede demostrar que un cambio hace lo que dice.
Deja por escrito las cifras del 11/08/2026 para el antes/despues."
```

---

## Tarea 2: Invariantes del catálogo

El catálogo pasa a ser base de datos de primer orden. Estas pruebas son el
trinquete que impide que crezca mal, y **hoy una de ellas falla**: `orden 50`
está duplicado.

**Ficheros:**
- Crear: `<motor>/tests/test_catalogo_invariantes.py`
- Modificar: `<motor>/reglas/CATALOGO_TAJOS.json`

**Interfaces:**
- Consume: `Catalogo` de `priorizador_trabajos`.
- Produce: nada de código; fija invariantes que las tareas siguientes asumen.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
# tests/test_catalogo_invariantes.py
# -*- coding: utf-8 -*-
"""El catalogo de tajos es una base de datos: SIEMPRE AMPLIABLE, nunca
ambigua. Estas pruebas son el trinquete que lo mantiene sano al crecer."""
import json
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CATALOGO = os.path.join(_BASE, 'reglas', 'CATALOGO_TAJOS.json')
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)


def _todos_los_tajos(catalogo):
    tajos = list(catalogo.get('tajos') or [])
    for cfg in (catalogo.get('obras') or {}).values():
        tajos.extend(cfg.get('tajos') or [])
    return tajos


class TestInvariantesCatalogo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(_CATALOGO, encoding='utf-8') as f:
            cls.catalogo = json.load(f)
        cls.comunes = cls.catalogo['tajos']
        cls.todos = _todos_los_tajos(cls.catalogo)

    def test_todo_tajo_declara_orden_propiedad_y_ambito(self):
        for tajo in self.todos:
            with self.subTest(tajo=tajo['id']):
                self.assertIsInstance(tajo.get('orden'), int)
                self.assertIn(tajo.get('propiedad'),
                              {'propio', 'externo', 'coordinacion'})
                self.assertIn(tajo.get('ambito'),
                              {'vivienda', 'zona_comun', 'edificio', 'dinamico'})

    def test_ningun_orden_duplicado_entre_tajos_comunes(self):
        vistos = {}
        for tajo in self.comunes:
            vistos.setdefault(tajo['orden'], []).append(tajo['id'])
        duplicados = {o: ids for o, ids in vistos.items() if len(ids) > 1}
        self.assertEqual(
            duplicados, {},
            'dos tajos con el mismo orden compiten y el desempate acaba '
            'siendo alfabetico: %r' % duplicados)

    def test_ninguna_dependencia_apunta_a_un_tajo_inexistente(self):
        ids = {t['id'] for t in self.todos}
        for tajo in self.todos:
            for dep in tajo.get('deps') or []:
                with self.subTest(tajo=tajo['id'], dep=dep['id']):
                    self.assertIn(dep['id'], ids)

    def test_ninguna_dependencia_apunta_hacia_delante(self):
        orden = {t['id']: t['orden'] for t in self.todos}
        for tajo in self.todos:
            for dep in tajo.get('deps') or []:
                if dep['id'] not in orden:
                    continue
                with self.subTest(tajo=tajo['id'], dep=dep['id']):
                    self.assertLess(
                        orden[dep['id']], tajo['orden'],
                        'una dependencia posterior en la secuencia no se '
                        'puede cumplir nunca')

    def test_ningun_alias_resuelve_a_dos_tajos_distintos(self):
        from priorizador_trabajos import Catalogo
        catalogo = Catalogo()
        self.assertEqual(catalogo.errores, [])

    def test_el_minimo_de_una_dependencia_es_un_estado_valido(self):
        from priorizador_trabajos import ESTADO_VALOR
        validos = set(ESTADO_VALOR.values())
        for tajo in self.todos:
            for dep in tajo.get('deps') or []:
                with self.subTest(tajo=tajo['id'], dep=dep['id']):
                    self.assertIn(float(dep.get('minimo', 1.0)), validos)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Paso 2: Ejecutarlas y comprobar que falla exactamente una**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_catalogo_invariantes -v
```
Esperado: `test_ningun_orden_duplicado_entre_tajos_comunes` FALLA con
`{50: ['montante_sscc', 'montante_general']}`. Las otras cinco pasan.

- [ ] **Paso 3: CHECKPOINT — preguntar a Bixente antes de tocar el dato**

**No inventar la respuesta.** `montante_general` ("Montantes") es el agregado
histórico que los criterios marcan explícitamente como no confirmado. Preguntar:

> El catálogo tiene `montante_sscc` y `montante_general` compartiendo el orden
> 50. `montante_general` es la fila genérica antigua, que probablemente
> agrupaba montante eléctrica, de telecomunicaciones y de servicios comunes,
> pero esa equivalencia nunca se confirmó. ¿Le damos orden propio (por ejemplo
> 45, antes de los tres específicos) o lo retiramos del catálogo común?

Aplicar lo que responda. Si no responde, dejar la prueba fallando con un
`self.skipTest` documentado **no** es aceptable: se espera la respuesta.

- [ ] **Paso 4: Ejecutar y comprobar que pasan las seis**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_catalogo_invariantes -v
```
Esperado: `OK`.

- [ ] **Paso 5: Probar por mutación**

Cambiar a mano el `orden` de `tabicado` de 10 a 9999 en el catálogo y
comprobar que `test_ninguna_dependencia_apunta_hacia_delante` se entera.
**Restaurar el fichero después.**

- [ ] **Paso 6: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_catalogo_invariantes.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/reglas/CATALOGO_TAJOS.json"
git commit -m "Poner trinquete a los invariantes del catalogo de tajos

El catalogo pasa a ser base de datos de primer orden y tiene que poder
crecer sin volverse ambiguo. Destapa el orden 50 duplicado entre
montante_sscc y montante_general."
```

---

## Tarea 3: `estado_desde_ficha` — leer el estado de la base

El núcleo. Sustituye la reconstrucción del historial por una lectura directa.

**Ficheros:**
- Modificar: `<motor>/priorizador_trabajos.py`
- Crear: `<motor>/tests/test_prioridades_desde_base.py`

**Interfaces:**
- Consume: `Catalogo` (existente), `fixtures.ficha_minima()` (existente).
- Produce: `estado_desde_ficha(ficha, catalogo) -> (estados, ultima_fecha)`.
  `estados` es `{((edificio, planta, unidad), task_id): dict}` con las claves
  `estado`, `estado_base`, `originales`, `meta`, `desconocido`, `loc`,
  `task_id`, `primera_fecha`, `ultima_fecha`, `forzado_entregado` — la misma
  forma que producía `_construir_estado`, más `estado_base`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
# tests/test_prioridades_desde_base.py
# -*- coding: utf-8 -*-
"""Prioridades leyendo de la base de obra en vez del historial crudo."""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from priorizador_trabajos import Catalogo, estado_desde_ficha
import fixtures


def _ficha_con_estados(pares):
    """pares: {(planta_id, tajo_id, ubicacion_id): estado}"""
    ficha = fixtures.ficha_minima()
    ficha['revisiones'] = [{'id': 'rev_28072026', 'fecha': '28/07/2026'}]
    for (planta, tajo, ubi), valor in pares.items():
        clave = 'p1__%s__%s__%s' % (planta, tajo, ubi)
        ficha['estados'][clave] = {'v': valor, 'f': '28/07/2026',
                                   'r': 'rev_28072026'}
    return ficha


class TestEstadoDesdeFicha(unittest.TestCase):

    def test_traduce_los_estados_medidos(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'X',
            ('pb', 'tubeado', 'B'): 'M',
            ('1', 'tubeado', 'A'): '/',
            ('1', 'tubeado', 'B'): 'P',
        })
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(estados[(('P1', 'PB', 'A'), 'tubeado')]['estado'], 'X')
        self.assertEqual(estados[(('P1', 'PB', 'B'), 'tubeado')]['estado'], 'M')
        self.assertEqual(estados[(('P1', '1', 'A'), 'tubeado')]['estado'], '/')
        self.assertEqual(estados[(('P1', '1', 'B'), 'tubeado')]['estado'], '')

    def test_conserva_el_estado_crudo_de_la_base(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): '?'})
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        celda = estados[(('P1', 'PB', 'A'), 'tubeado')]
        self.assertEqual(celda['estado_base'], '?')
        self.assertEqual(celda['estado'], '')

    def test_una_ubicacion_fuera_del_arbol_no_aparece(self):
        """Las excluidas no estan en estructura.bloques: recorrer el arbol es,
        por si solo, respetar estructura.exclusiones. Es el caso de las 4
        viviendas fantasma de PB en Bolueta."""
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        ficha['estados']['p1__pb__tubeado__FANTASMA'] = {
            'v': 'X', 'f': '28/07/2026', 'r': 'rev_28072026'}
        estados, _fecha = estado_desde_ficha(ficha, Catalogo())
        unidades = {loc[2] for loc, _tid in estados}
        self.assertNotIn('FANTASMA', unidades)

    def test_la_fecha_es_la_de_la_ultima_revision_registrada(self):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'X'})
        ficha['revisiones'] = [
            {'id': 'rev_26072026', 'fecha': '26/07/2026'},
            {'id': 'rev_28072026', 'fecha': '28/07/2026'},
        ]
        _estados, fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(fecha, '28/07/2026')

    def test_una_base_sin_celdas_no_revienta(self):
        ficha = fixtures.ficha_minima()
        estados, fecha = estado_desde_ficha(ficha, Catalogo())
        self.assertEqual(estados, {})
        self.assertIsNone(fecha)


class TestRejillaCompleta(unittest.TestCase):
    """La base tiene que ser una rejilla densa: ubicaciones x tajos. Si falta
    una celda, calcular sobre datos parciales es peor que avisar."""

    def test_una_rejilla_completa_no_avisa(self):
        pares = {(p, t, u): 'P'
                 for p in ('pb', '1') for u in ('A', 'B')
                 for t in ('tabicado', 'tubeado', 'cableado')}
        ficha = _ficha_con_estados(pares)
        self.assertEqual(verificar_rejilla(ficha), [])

    def test_una_celda_que_falta_se_reporta_con_cifras(self):
        pares = {(p, t, u): 'P'
                 for p in ('pb', '1') for u in ('A', 'B')
                 for t in ('tabicado', 'tubeado', 'cableado')}
        ficha = _ficha_con_estados(pares)
        del ficha['estados']['p1__pb__tubeado__A']
        avisos = verificar_rejilla(ficha)
        self.assertEqual(len(avisos), 1)
        self.assertIn('11', avisos[0])   # celdas encontradas
        self.assertIn('12', avisos[0])   # celdas esperadas


if __name__ == '__main__':
    unittest.main()
```

Añadir `verificar_rejilla` al import de la cabecera del fichero:

```python
from priorizador_trabajos import (Catalogo, estado_desde_ficha,
                                  verificar_rejilla)
```

- [ ] **Paso 2: Ejecutarlas y comprobar que fallan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base -v
```
Esperado: `ImportError: cannot import name 'estado_desde_ficha'`.

- [ ] **Paso 3: Implementar**

Añadir en `priorizador_trabajos.py`, junto a `ESTADO_VALOR`:

```python
# Estado guardado en la base -> estado que entiende el motor.
# '?' (nadie lo ha mirado) y 'N' (no aplica) NO tienen equivalente: se
# conservan en 'estado_base' y los clasifica _clasificar_detalle.
ESTADO_BASE_A_MOTOR = {'X': 'X', 'M': 'M', '/': '/', 'P': ''}
```

Y la función:

```python
def _ultima_revision_ficha(ficha):
    """La fecha mas reciente registrada en la base, o None si no hay ninguna."""
    fechas = [r.get('fecha') for r in (ficha.get('revisiones') or [])
              if r.get('fecha')]
    if not fechas:
        return None
    return max(fechas, key=_fecha)


def estado_desde_ficha(ficha, catalogo):
    """Construye el estado por celda leyendo la base de la obra.

    Sustituye a _construir_estado. La base YA es el estado resuelto: trae la
    norma de la ultima revision aplicada, la fecha y la revision de origen de
    cada celda, y las ubicaciones descartadas fuera del arbol de estructura.
    Recorrer el arbol es, por si solo, respetar estructura.exclusiones: por eso
    aqui no hay ninguna comprobacion de exclusiones. Reconstruir esto desde el
    historial crudo es lo que metia 4 viviendas inexistentes en Bolueta.
    """
    estructura = ficha.get('estructura') or {}
    alias = estructura.get('alias_historico') or {}
    tajos = (ficha.get('tajos') or {}).get('detalle') or []
    guardados = ficha.get('estados') or {}

    estados = {}
    for bloque in estructura.get('bloques') or []:
        for portal in bloque.get('portales') or []:
            edificio = (portal.get('referencia') or portal.get('nombre')
                        or portal['id'])
            for planta in portal.get('plantas') or []:
                planta_nom = planta.get('nombre') or planta['id']
                for ubi in planta.get('ubicaciones') or []:
                    clave_alias = '%s__%s__%s' % (portal['id'], planta['id'],
                                                  ubi['id'])
                    unidad = alias.get(clave_alias, ubi['id'])
                    loc = (edificio, planta_nom, unidad)
                    for tajo in tajos:
                        clave = '%s__%s__%s__%s' % (
                            portal['id'], planta['id'], tajo['id'], ubi['id'])
                        dato = guardados.get(clave)
                        if not dato:
                            continue
                        nombre = tajo.get('nombre') or tajo['id']
                        # El id de la base manda si el catalogo lo conoce; si
                        # no, se resuelve por nombre para pillar los alias.
                        meta = catalogo.meta(tajo['id'])
                        if meta:
                            task_id, desconocido = tajo['id'], False
                        else:
                            task_id, meta, desconocido = catalogo.resolver(nombre)
                        valor = str(dato.get('v') or '')
                        estados[(loc, task_id)] = {
                            'estado': ESTADO_BASE_A_MOTOR.get(valor, ''),
                            'estado_base': valor,
                            'originales': {nombre},
                            'meta': meta,
                            'desconocido': desconocido,
                            'loc': loc,
                            'task_id': task_id,
                            'primera_fecha': dato.get('f'),
                            'ultima_fecha': dato.get('f'),
                            'forzado_entregado': False,
                        }
    return estados, _ultima_revision_ficha(ficha)


def verificar_rejilla(ficha):
    """La base debe ser una rejilla densa: ubicaciones x tajos.

    Si falta alguna celda, calcular sobre datos parciales es peor que avisar
    con las cifras. Las cinco bases lo cumplian el 11/08/2026.
    """
    estructura = ficha.get('estructura') or {}
    tajos = (ficha.get('tajos') or {}).get('detalle') or []
    ubicaciones = sum(
        len(planta.get('ubicaciones') or [])
        for bloque in estructura.get('bloques') or []
        for portal in bloque.get('portales') or []
        for planta in portal.get('plantas') or []
    )
    esperadas = ubicaciones * len(tajos)
    encontradas = len(ficha.get('estados') or {})
    if not esperadas or encontradas == esperadas:
        return []
    return ["La base no es una rejilla completa: %d celdas encontradas frente "
            "a %d esperadas (%d ubicaciones x %d tajos). Los tajos que falten "
            "no se pueden priorizar."
            % (encontradas, esperadas, ubicaciones, len(tajos))]
```

- [ ] **Paso 4: Ejecutar y comprobar que pasan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base -v
```
Esperado: `OK`, 7 pruebas.

- [ ] **Paso 5: Probar por mutación**

Quitar la línea `if not dato: continue` y comprobar que
`test_una_base_sin_celdas_no_revienta` falla. Restaurar.

- [ ] **Paso 6: Suite completa y commit**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```
Esperado: `OK`, al menos 218 pruebas.

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_prioridades_desde_base.py"
git commit -m "Leer el estado de la base en vez de reconstruirlo

La base ya es el estado resuelto, con fecha y revision por celda y con las
ubicaciones descartadas fuera del arbol. Recorrer el arbol respeta
estructura.exclusiones por construccion."
```

---

## Tarea 4: `?` y `N` en la clasificación

**Ficheros:**
- Modificar: `<motor>/priorizador_trabajos.py`
- Modificar: `<motor>/tests/test_prioridades_desde_base.py`

**Interfaces:**
- Consume: `estado_desde_ficha` de la Tarea 3.
- Produce: categoría `SIN_REVISAR` en `_clasificar_detalle`; las celdas `N` no
  aparecen en `detalle`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

Añadir a `tests/test_prioridades_desde_base.py`:

```python
from priorizador_trabajos import _clasificar_detalle


class TestDesconocidoYNoAplica(unittest.TestCase):

    def _clasificar(self, pares):
        ficha = _ficha_con_estados(pares)
        catalogo = Catalogo()
        estados, fecha = estado_desde_ficha(ficha, catalogo)
        detalle, _edad, _cad = _clasificar_detalle(
            estados, catalogo, fecha, {})
        return detalle

    def test_no_aplica_no_entra_en_el_calculo(self):
        detalle = self._clasificar({('pb', 'tubeado', 'A'): 'N'})
        self.assertEqual(detalle, [])

    def test_nunca_revisado_tiene_categoria_propia(self):
        detalle = self._clasificar({('pb', 'tubeado', 'A'): '?'})
        self.assertEqual(len(detalle), 1)
        self.assertEqual(detalle[0]['categoria'], 'SIN_REVISAR')

    def test_nunca_revisado_no_se_confunde_con_pendiente(self):
        detalle = self._clasificar({
            ('pb', 'tubeado', 'A'): '?',
            ('pb', 'tubeado', 'B'): 'P',
        })
        por_unidad = {d['unidad']: d['categoria'] for d in detalle}
        self.assertEqual(por_unidad['A'], 'SIN_REVISAR')
        self.assertNotEqual(por_unidad['B'], 'SIN_REVISAR')

    def test_nunca_revisado_gana_a_la_propiedad_del_tajo(self):
        """Un tajo de otro gremio que nadie ha mirado es 'sin revisar', no
        'otros gremios': la pregunta es ir a mirarlo."""
        detalle = self._clasificar({('pb', 'tabicado', 'A'): '?'})
        self.assertEqual(detalle[0]['categoria'], 'SIN_REVISAR')
```

Añadir `tabicado` a la ficha de juguete: en `tests/fixtures.py`, dentro de
`ficha_minima()`, cambiar `'aplicables'` a
`['tabicado', 'tubeado', 'cableado']` y añadir al principio de `'detalle'`:

```python
{'id': 'tabicado', 'nombre': 'Tabicado', 'ambito': 'vivienda',
 'propiedad': 'externo', 'fase': 'Inicio de obra', 'orden': 5},
```

- [ ] **Paso 2: Ejecutar y comprobar que fallan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base.TestDesconocidoYNoAplica -v
```
Esperado: las cuatro fallan (`N` y `?` salen como pendiente).

- [ ] **Paso 3: Implementar**

En `priorizador_trabajos.py`, añadir la sección a las tablas de orden y nombre:

```python
SECCION_ORDEN = {
    "VIABLE": 0,
    "BLOQUEADO": 1,
    "OTROS_GREMIOS": 2,
    "DUDAS": 3,
    "SIN_REVISAR": 4,
    "TERMINADO": 5,
}
SECCION_NOMBRE = {
    "VIABLE": "Tajos viables",
    "BLOQUEADO": "Tajos bloqueados",
    "OTROS_GREMIOS": "Otros gremios e interferencias",
    "DUDAS": "Dudas pendientes",
    "SIN_REVISAR": "Sin revisar nunca",
    "TERMINADO": "Tajos terminados",
}
```

En `_clasificar_detalle`, dentro del bucle `for item in estados.values():`,
justo después de leer `estado = item["estado"]`, insertar **antes** de
cualquier otra rama:

```python
        estado_base = item.get('estado_base', '')
        # 'N' no aplica a esta ubicacion: no es trabajo pendiente ni
        # terminado, simplemente no existe. No entra en el calculo.
        if estado_base == 'N':
            continue
```

Y en la cascada, como **primera** condición del `if`:

```python
        if estado_base == '?':
            categoria = "SIN_REVISAR"
            motivo = ("Nadie lo ha mirado nunca. Hay que ir a comprobarlo "
                      "antes de poder decidir.")
        elif item.get("conflicto"):
            ...
```

En `_agrupar_inventario`, la sección de un grupo se decide por sus categorías;
añadir la rama antes de `TERMINADO`:

```python
        elif cats.get("SIN_REVISAR"):
            seccion = "SIN_REVISAR"
```

En `priorizar_historial`/`priorizar_ficha`, añadir al `resumen`:

```python
        "sin_revisar": secciones.get("SIN_REVISAR", 0),
        "unidades_sin_revisar": sum(
            1 for x in detalle if x["categoria"] == "SIN_REVISAR"),
```

- [ ] **Paso 4: Ejecutar y comprobar que pasan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base -v
```
Esperado: `OK`, 11 pruebas.

- [ ] **Paso 5: Probar por mutación**

Cambiar `if estado_base == 'N': continue` por `pass` y comprobar que
`test_no_aplica_no_entra_en_el_calculo` falla. Restaurar.

- [ ] **Paso 6: Suite y commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_prioridades_desde_base.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/fixtures.py"
git commit -m "Distinguir 'no aplica' de 'nadie lo ha mirado' en Prioridades

'N' sale del calculo y '?' pasa a tener seccion propia. Antes los dos se
caian antes de llegar: en Bolueta eso dejaba 5 ubicaciones reales
invisibles (Local 1, Local 2, Txoko, Gim., Multiusos)."
```

---

## Tarea 5: Contar según el ámbito del tajo

**Ficheros:**
- Modificar: `<motor>/priorizador_trabajos.py`
- Modificar: `<motor>/tests/test_prioridades_desde_base.py`

**Interfaces:**
- Produce: `_agrupar_prioridades` devuelve `n_unidades` contado por ámbito y
  añade `n_celdas` con el recuento crudo.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
from priorizador_trabajos import _agrupar_prioridades


class TestConteoPorAmbito(unittest.TestCase):

    def _item(self, ambito, planta, unidad, tarea='cuarto_tecnico'):
        return {
            'tarea_id': tarea, 'trabajo': 'Cuarto técnico',
            'trabajos_originales': ['Cuarto técnico'], 'propiedad': 'propio',
            'ambito': ambito, 'ambito_nombre': 'Edificio general',
            'orden_ejecucion': 235, 'fase_nombre': 'Cierre técnico',
            'display_group': tarea, 'edificio': 'P1', 'planta': planta,
            'unidad': unidad, 'estado': '', 'estado_actual': 'Pendiente',
            'categoria': 'VIABLE', 'motivo': 'Viable.',
            'dependencias_cumplidas': [], 'dependencias_bloqueantes': [],
            'dependencias_sin_dato': [], 'omitido_ultima': False,
            'forzado_entregado': False, 'ultima_fecha': '28/07/2026',
        }

    def test_un_tajo_de_edificio_cuenta_una_sola_unidad(self):
        detalle = [self._item('edificio', p, u)
                   for p in ('PB', '1', '2') for u in ('A', 'B')]
        grupos = _agrupar_prioridades(detalle)
        self.assertEqual(len(grupos), 1)
        self.assertEqual(grupos[0]['n_unidades'], 1)
        self.assertEqual(grupos[0]['n_celdas'], 6)

    def test_un_tajo_de_zona_comun_cuenta_una_por_planta(self):
        detalle = [self._item('zona_comun', p, u, 'tubeado_zzcc')
                   for p in ('PB', '1', '2') for u in ('A', 'B')]
        grupos = _agrupar_prioridades(detalle)
        self.assertEqual(grupos[0]['n_unidades'], 3)
        self.assertEqual(grupos[0]['n_celdas'], 6)

    def test_un_tajo_de_vivienda_cuenta_una_por_vivienda(self):
        detalle = [self._item('vivienda', p, u, 'tubeado')
                   for p in ('PB', '1', '2') for u in ('A', 'B')]
        grupos = _agrupar_prioridades(detalle)
        self.assertEqual(grupos[0]['n_unidades'], 6)
        self.assertEqual(grupos[0]['n_celdas'], 6)
```

- [ ] **Paso 2: Ejecutar y comprobar que fallan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base.TestConteoPorAmbito -v
```
Esperado: los dos primeros fallan con `n_unidades == 6`.

- [ ] **Paso 3: Implementar**

En `priorizador_trabajos.py`, añadir junto a `AMBITO_ORDEN`:

```python
def _clave_unidad(item):
    """Que cuenta como 'una unidad' segun el ambito del tajo.

    La hoja repite cada tajo en todas las ubicaciones, tambien los que son
    unicos del edificio. Contar celdas daba '92 cuartos tecnicos' donde hay
    uno: 370 de las 851 unidades de Bolueta estaban infladas asi.
    """
    ambito = item["ambito"]
    if ambito == "edificio":
        return (item["edificio"],)
    if ambito == "zona_comun":
        return (item["edificio"], item["planta"])
    return (item["edificio"], item["planta"], item["unidad"])
```

En `_agrupar_prioridades`, sustituir el contador. Donde hoy pone
`g["n_unidades"] += 1`, usar un conjunto:

```python
        g["unidades_reales"].add(_clave_unidad(item))
        g["n_celdas"] += 1
```

Inicializar en el `setdefault`: `"unidades_reales": set(), "n_celdas": 0,` y
retirar `"n_unidades": 0`. En el bucle de salida, antes de `salida.append(g)`:

```python
        g["n_unidades"] = len(g.pop("unidades_reales"))
```

- [ ] **Paso 4: Ejecutar y comprobar que pasan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base -v
```
Esperado: `OK`, 14 pruebas.

- [ ] **Paso 5: Probar por mutación**

Hacer que `_clave_unidad` devuelva siempre la tupla de tres y comprobar que
fallan las dos primeras pruebas. Restaurar.

- [ ] **Paso 6: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_prioridades_desde_base.py"
git commit -m "Contar unidades segun el ambito del tajo

Hay un cuarto tecnico en Bolueta, no 92. El recuento por celdas inflaba el
KPI de carga de trabajo un 43%."
```

---

## Tarea 6: `sembrar_reglas` — el catálogo manda sobre orden y dependencias

**Ficheros:**
- Modificar: `<motor>/priorizador_trabajos.py`
- Modificar: `<motor>/tests/test_prioridades_desde_base.py`

**Interfaces:**
- Produce: `sembrar_reglas(ficha, catalogo) -> list` de preguntas, cada una
  `{'codigo': 'ORDEN_SIN_CONFIRMAR'|'TAJO_FUERA_DEL_CATALOGO', 'tarea_id',
  'nombre', 'parecidos': [ids]}`. Modifica `ficha['tajos']['detalle']` en sitio.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
from priorizador_trabajos import sembrar_reglas


class TestSembrarReglas(unittest.TestCase):

    def test_el_catalogo_manda_sobre_el_orden(self):
        ficha = fixtures.ficha_minima()
        ficha['tajos']['detalle'] = [
            {'id': 'tubeado', 'nombre': 'Tubeado interior', 'orden': 9999},
        ]
        sembrar_reglas(ficha, Catalogo())
        self.assertEqual(ficha['tajos']['detalle'][0]['orden'], 130)

    def test_siembra_tambien_propiedad_ambito_fase_y_deps(self):
        ficha = fixtures.ficha_minima()
        ficha['tajos']['detalle'] = [
            {'id': 'cableado', 'nombre': 'Cableado eléctrico', 'orden': 9999},
        ]
        sembrar_reglas(ficha, Catalogo())
        tajo = ficha['tajos']['detalle'][0]
        self.assertEqual(tajo['propiedad'], 'propio')
        self.assertEqual(tajo['ambito'], 'vivienda')
        self.assertEqual([d['id'] for d in tajo['deps']], ['tubeado'])

    def test_un_tajo_que_el_catalogo_no_conoce_sale_como_pregunta(self):
        ficha = fixtures.ficha_minima()
        ficha['tajos']['detalle'] = [
            {'id': 'placas_tps_cuadro', 'nombre': 'Placas tapas cuadro',
             'orden': 9999},
        ]
        preguntas = sembrar_reglas(ficha, Catalogo())
        codigos = {p['codigo'] for p in preguntas}
        self.assertIn('TAJO_FUERA_DEL_CATALOGO', codigos)

    def test_nunca_se_inventa_un_orden(self):
        ficha = fixtures.ficha_minima()
        ficha['tajos']['detalle'] = [
            {'id': 'inventado_xyz', 'nombre': 'Inventado', 'orden': 9999},
        ]
        sembrar_reglas(ficha, Catalogo())
        self.assertEqual(ficha['tajos']['detalle'][0]['orden'], 9999)

    def test_la_pregunta_sugiere_ids_parecidos(self):
        ficha = fixtures.ficha_minima()
        ficha['tajos']['detalle'] = [
            {'id': 'pintura_hab', 'nombre': 'Pintura Hab', 'orden': 9999},
        ]
        preguntas = sembrar_reglas(ficha, Catalogo('2025 BILBAO OBISPO ORUETA'))
        parecidos = preguntas[0]['parecidos']
        self.assertIn('pintura_habitaciones', parecidos)

    def test_una_dependencia_que_la_obra_no_tiene_se_avisa(self):
        """Hoy vale 0 y bloquea para siempre en silencio: 'Dependencias
        pendientes: Tabicado' sin que Tabicado exista en esa obra."""
        ficha = fixtures.ficha_minima()
        ficha['tajos']['detalle'] = [
            {'id': 'cableado', 'nombre': 'Cableado eléctrico', 'orden': 9999},
        ]
        preguntas = sembrar_reglas(ficha, Catalogo())
        codigos = {p['codigo'] for p in preguntas}
        self.assertIn('DEPENDENCIA_AUSENTE_EN_LA_OBRA', codigos)
        aviso = [p for p in preguntas
                 if p['codigo'] == 'DEPENDENCIA_AUSENTE_EN_LA_OBRA'][0]
        self.assertEqual(aviso['tarea_id'], 'cableado')
        self.assertIn('tubeado', aviso['parecidos'])

    def test_si_la_dependencia_esta_en_la_obra_no_se_avisa(self):
        ficha = fixtures.ficha_minima()
        ficha['tajos']['detalle'] = [
            {'id': 'tubeado', 'nombre': 'Tubeado interior', 'orden': 9999},
            {'id': 'cableado', 'nombre': 'Cableado eléctrico', 'orden': 9999},
        ]
        preguntas = sembrar_reglas(ficha, Catalogo())
        codigos = {p['codigo'] for p in preguntas}
        self.assertNotIn('DEPENDENCIA_AUSENTE_EN_LA_OBRA', codigos)
```

- [ ] **Paso 2: Ejecutar y comprobar que fallan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base.TestSembrarReglas -v
```
Esperado: `ImportError: cannot import name 'sembrar_reglas'`.

- [ ] **Paso 3: Implementar**

```python
import difflib

CAMPOS_SEMBRADOS = ('orden', 'propiedad', 'ambito', 'fase', 'deps')


def sembrar_reglas(ficha, catalogo):
    """Vuelca orden, propiedad, ambito, fase y deps del catalogo sobre la base.

    DECISION: el catalogo manda. La base guarda el estado; el catalogo guarda
    la regla. Un tajo que el catalogo no conoce NO recibe orden inventado: sale
    como pregunta para ampliar el catalogo, que es SIEMPRE AMPLIABLE.

    En Orueta habia 18 tajos con orden 9999 y 14 tenian orden real en el
    catalogo: el orden estaba declarado y el motor lo ignoraba.
    """
    preguntas = []
    ids_catalogo = list(catalogo.tajos)
    for tajo in (ficha.get('tajos') or {}).get('detalle') or []:
        meta = catalogo.meta(tajo['id'])
        if not meta:
            nombre = tajo.get('nombre') or tajo['id']
            resuelto, meta_alias, desconocido = catalogo.resolver(nombre)
            if not desconocido:
                meta = meta_alias
            else:
                preguntas.append({
                    'codigo': 'TAJO_FUERA_DEL_CATALOGO',
                    'tarea_id': tajo['id'],
                    'nombre': nombre,
                    'parecidos': difflib.get_close_matches(
                        tajo['id'], ids_catalogo, n=3, cutoff=0.6),
                })
                continue
        for campo in CAMPOS_SEMBRADOS:
            if campo in meta:
                tajo[campo] = meta[campo]
        if (tajo.get('orden') or 9999) >= 9999:
            preguntas.append({
                'codigo': 'ORDEN_SIN_CONFIRMAR',
                'tarea_id': tajo['id'],
                'nombre': tajo.get('nombre') or tajo['id'],
                'parecidos': [],
            })

    # Una dependencia que apunta a un tajo que esta obra no tiene vale 0 y
    # bloquea para siempre en silencio: 'Dependencias pendientes: Tabicado'
    # sin que Tabicado exista en la obra. Se avisa en vez de callar.
    presentes = {t['id'] for t in (ficha.get('tajos') or {}).get('detalle') or []}
    for tajo in (ficha.get('tajos') or {}).get('detalle') or []:
        ausentes = [d['id'] for d in (tajo.get('deps') or [])
                    if d['id'] not in presentes]
        if ausentes:
            preguntas.append({
                'codigo': 'DEPENDENCIA_AUSENTE_EN_LA_OBRA',
                'tarea_id': tajo['id'],
                'nombre': tajo.get('nombre') or tajo['id'],
                'parecidos': sorted(ausentes),
            })
    return preguntas
```

- [ ] **Paso 4: Ejecutar y comprobar que pasan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base -v
```
Esperado: `OK`, 21 pruebas.

- [ ] **Paso 5: Probar por mutación**

Poner `tajo['orden'] = 9999 if ... else 500` como valor por defecto inventado y
comprobar que `test_nunca_se_inventa_un_orden` falla. Restaurar.

- [ ] **Paso 6: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_prioridades_desde_base.py"
git commit -m "Sembrar orden y dependencias del catalogo sobre la base

El catalogo manda sobre la regla; lo que no conoce sale como pregunta y
nunca recibe un orden inventado."
```

---

## Tarea 7: La antigüedad como aviso, no como interruptor

**Ficheros:**
- Modificar: `<motor>/priorizador_trabajos.py`
- Modificar: `<motor>/tests/test_prioridades_desde_base.py`

**Interfaces:**
- Produce: `_clasificar_detalle(estados, catalogo, ultima_fecha, preguntas, hoy=None)`.
  `hoy` es un `datetime.date`; si es `None` usa `date.today()`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
from datetime import date


class TestAntiguedadEsAviso(unittest.TestCase):

    def _clasificar(self, fecha_revision, hoy):
        ficha = _ficha_con_estados({('pb', 'tubeado', 'A'): 'P'})
        ficha['revisiones'] = [{'id': 'r', 'fecha': fecha_revision}]
        catalogo = Catalogo()
        estados, fecha = estado_desde_ficha(ficha, catalogo)
        return _clasificar_detalle(estados, catalogo, fecha, {}, hoy=hoy)

    def test_una_revision_vieja_ya_no_tumba_la_clasificacion(self):
        detalle, edad, _cad = self._clasificar('01/01/2026', date(2026, 8, 11))
        self.assertEqual(detalle[0]['categoria'], 'VIABLE')
        self.assertEqual(edad, 222)

    def test_el_resultado_no_depende_del_dia_en_que_se_genera(self):
        d1, _e1, _c1 = self._clasificar('01/07/2026', date(2026, 7, 20))
        d2, _e2, _c2 = self._clasificar('01/07/2026', date(2026, 12, 31))
        self.assertEqual([x['categoria'] for x in d1],
                         [x['categoria'] for x in d2])
```

- [ ] **Paso 2: Ejecutar y comprobar que fallan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base.TestAntiguedadEsAviso -v
```
Esperado: `TypeError: _clasificar_detalle() got an unexpected keyword argument 'hoy'`.

- [ ] **Paso 3: Implementar**

Cambiar la firma y el cálculo de edad:

```python
def _clasificar_detalle(estados, catalogo, ultima_fecha, preguntas, hoy=None):
    ...
    edad_dias = None
    referencia = hoy or datetime.now().date()
    try:
        edad_dias = (referencia - _fecha(ultima_fecha).date()).days
    except Exception:
        pass
    # DECISION: la antiguedad es un aviso, no un interruptor. Volcar toda la
    # obra a DUDAS a los 30 dias apagaba cuatro obras el mismo dia, y calcular
    # la edad con la fecha de generacion hacia que el mismo dato produjera
    # paneles distintos segun cuando se lanzara.
    caducada = edad_dias is None or edad_dias > 30
```

Y **eliminar** de la cascada la rama:

```python
        elif caducada and not ignorar_caducidad:
            categoria = "DUDAS"
            motivo = f"La revisión tiene {edad_dias} días; actualizar antes de ejecutar."
```

`caducada` se sigue devolviendo para el aviso, pero ya no cambia ninguna
categoría. Retirar también la variable `ignorar_caducidad`, que queda sin uso.

- [ ] **Paso 4: Ejecutar y comprobar que pasan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base -v
```
Esperado: `OK`, 23 pruebas.

- [ ] **Paso 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_prioridades_desde_base.py"
git commit -m "La antiguedad de la revision avisa, no apaga la obra

A los 30 dias el motor volcaba todo a DUDAS de golpe, y con la fecha de
generacion dentro del calculo el mismo dato daba paneles distintos."
```

---

## Tarea 8: Enganchar la base y retirar `_construir_estado`

La tarea con más riesgo. Aquí se mide el antes/después de verdad.

**Ficheros:**
- Modificar: `<motor>/priorizador_trabajos.py`
- Modificar: `<motor>/generar_todos.py:930-933`
- Modificar: `<motor>/tests/test_prioridades_desde_base.py`

**Interfaces:**
- Produce: `priorizar_ficha(ficha, obra="", limite=200, hoy=None) -> dict`, con
  la misma forma que devolvía `priorizar_historial`, más
  `resumen['sin_revisar']` y `preguntas_orden`.
- Produce: `sin_base(obra) -> dict` con `resumen` a cero y
  `avisos = ["Esta obra no tiene base de datos todavía…"]`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
from priorizador_trabajos import priorizar_ficha, sin_base


class TestPuntoDeEntrada(unittest.TestCase):

    def test_una_obra_sin_base_no_calcula_nada(self):
        resultado = sin_base('2026 GORLIZ HOSPITAL')
        self.assertEqual(resultado['resumen']['inventario_total'], 0)
        self.assertTrue(resultado['avisos'])
        self.assertIn('no tiene base de datos', resultado['avisos'][0])
        self.assertIs(resultado['sin_base'], True)

    def test_priorizar_ficha_devuelve_la_forma_de_siempre(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'X',
            ('pb', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        for clave in ('version', 'catalogo_version', 'revision', 'resumen',
                      'items', 'detalle_items', 'inventario',
                      'dudas_pendientes', 'avisos'):
            self.assertIn(clave, resultado)

    def test_cableado_es_viable_con_el_tubeado_terminado(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'X',
            ('pb', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        cableado = [d for d in resultado['detalle_items']
                    if d['tarea_id'] == 'cableado']
        self.assertEqual(cableado[0]['categoria'], 'VIABLE')

    def test_cableado_esta_bloqueado_sin_tubeado(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'P',
            ('pb', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        cableado = [d for d in resultado['detalle_items']
                    if d['tarea_id'] == 'cableado']
        self.assertEqual(cableado[0]['categoria'], 'BLOQUEADO')
        self.assertIn('Tubeado interior',
                      cableado[0]['dependencias_bloqueantes'])
```

- [ ] **Paso 2: Ejecutar y comprobar que fallan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base.TestPuntoDeEntrada -v
```
Esperado: `ImportError: cannot import name 'priorizar_ficha'`.

- [ ] **Paso 3: Implementar**

```python
def sin_base(obra=""):
    """DECISION: una obra sin base no calcula prioridades.

    Un recuento vacio es senal de alarma, no de 'no aplica'. Asi se ve de un
    vistazo que obras faltan por dar de alta.
    """
    return {
        "version": VERSION, "catalogo_version": Catalogo(obra).version,
        "obra": obra, "revision": None, "sin_base": True,
        "resumen": {"listos": 0, "verificar": 0, "bloqueados": 0,
                    "sin_revisar": 0, "inventario_total": 0,
                    "preguntas_pendientes": 0},
        "items": [], "detalle_items": [], "inventario": [],
        "dudas_pendientes": [], "preguntas_orden": [],
        "avisos": ["Esta obra no tiene base de datos todavía. "
                   "Sembrarla con sembrar_ficha_obra.py habilita las "
                   "prioridades."],
    }


def priorizar_ficha(ficha, obra="", limite=200, hoy=None):
    """Prioriza leyendo la base de la obra. Sustituye a priorizar_historial."""
    preguntas = {}
    catalogo = Catalogo(obra)
    for error in catalogo.errores:
        _pregunta(preguntas, "ERROR_CATALOGO", error)

    preguntas_orden = sembrar_reglas(ficha, catalogo)
    avisos_rejilla = verificar_rejilla(ficha)
    estados, ultima_fecha = estado_desde_ficha(ficha, catalogo)
    if not estados:
        return sin_base(obra)

    _aplicar_excepciones_obra(estados, catalogo, preguntas)
    detalle, edad_dias, caducada = _clasificar_detalle(
        estados, catalogo, ultima_fecha, preguntas, hoy=hoy)
    items = _agrupar_prioridades(detalle, limite=limite)
    inventario = _agrupar_inventario(detalle)
    dudas = _serializar_preguntas(preguntas)

    listos = [x for x in items if x["situacion"] == "LISTO"]
    verificar = [x for x in items if x["situacion"] == "VERIFICAR"]
    secciones = Counter(x["seccion"] for x in inventario)
    resumen = {
        "listos": len(listos), "verificar": len(verificar),
        "unidades_listas": sum(x["n_unidades"] for x in listos),
        "unidades_verificar": sum(x["n_unidades"] for x in verificar),
        "bloqueados": secciones.get("BLOQUEADO", 0),
        "otros_gremios": secciones.get("OTROS_GREMIOS", 0),
        "dudas": secciones.get("DUDAS", 0),
        "sin_revisar": secciones.get("SIN_REVISAR", 0),
        "unidades_sin_revisar": sum(
            1 for x in detalle if x["categoria"] == "SIN_REVISAR"),
        "terminados": secciones.get("TERMINADO", 0),
        "inventario_total": len(inventario),
        "detalle_total": len(detalle),
        "preguntas_pendientes": len(dudas) + len(preguntas_orden),
        "viviendas": sum(1 for x in listos if x["ambito"] == "vivienda"),
        "zonas_comunes": sum(1 for x in listos if x["ambito"] == "zona_comun"),
        "edificio": sum(1 for x in listos if x["ambito"] == "edificio"),
    }
    avisos = [
        "El inventario incluye todos los tajos de la base; los terminados "
        "aparecen al final.",
        "Los nombres nuevos no se fusionan: quedan SIN CLASIFICAR hasta "
        "confirmación.",
        "El orden sigue la secuencia lógica definida en CATALOGO_TAJOS.json.",
    ]
    avisos = avisos_rejilla + avisos
    if catalogo.config_obra.get("estado_obra"):
        avisos.insert(0, catalogo.config_obra["estado_obra"] + ".")
    if caducada:
        avisos.append(
            "La revisión es del %s (%s días). Los tajos pendientes conservan "
            "su clasificación; confirmar en obra antes de ejecutar."
            % (ultima_fecha, edad_dias))

    return {
        "version": VERSION, "catalogo_version": catalogo.version,
        "obra": obra, "revision": ultima_fecha, "sin_base": False,
        "edad_revision_dias": edad_dias, "revision_caducada": caducada,
        "estado_obra": catalogo.config_obra.get("estado_obra"),
        "generado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "resumen": resumen, "items": items,
        "detalle_items": detalle, "inventario": inventario,
        "dudas_pendientes": dudas, "preguntas_orden": preguntas_orden,
        "avisos": avisos,
    }
```

Borrar `_construir_estado()` y `priorizar_historial()` completas.

En `generar_todos.py`, sustituir las líneas 930-933:

```python
            if ficha_actual:
                prioridades = priorizador_trabajos.priorizar_ficha(
                    ficha_actual, obra=obra['nombre'])
                fichas.guardar(carpeta_abs, ficha_actual)
            else:
                prioridades = priorizador_trabajos.sin_base(obra['nombre'])
            priorizador_trabajos.escribir_json(prioridades, salida_prioridades)
```

- [ ] **Paso 4: Ejecutar la suite completa**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```
Arreglar lo que rompa. `test_catalogo_tajos.test_cambio_de_alias_a_nombre_no_genera_desaparicion`
usa `priorizar_historial` y hay que reescribirla contra `priorizar_ficha`
usando `fixtures.ficha_minima()`. **No borrarla:** el invariante que comprueba
—que renombrar un alias no genera `TAJO_NUEVO`— sigue vigente.

- [ ] **Paso 5: Regenerar y medir el antes/después**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python generar_todos.py --no-pdf
```

Luego repetir la medición del Paso 5 de la Tarea 1 y comparar con la línea base.

| | Antes | Después esperado |
|---|---|---|
| Preguntas de Bolueta | 26 | 0 |
| Unidades `VERIFICAR` Bolueta | 104 | 0 |
| Ubicaciones Bolueta | 96 | 97 |
| Celdas `SIN_REVISAR` Bolueta | 0 | 190 |
| Unidades no-vivienda Bolueta | 370 | mucho menor |
| Tajos de Orueta en 9999 | 18 | 4 |

Y los KPIs del panel: **Mungia 80.1 · Gernika 76.3 · Bolueta 43.5 · Orueta 99.7
· OBRA PRUEBA 6.4, sin moverse.**

**Si Orueta se mueve, parar.** Significa que el cierre por fecha del 24/09/2025
no estaba materializado en la base y hay que resolverlo antes de seguir.

- [ ] **Paso 6: Reportar a Bixente y commitear**

Reportar el antes/después completo **antes** de commitear.

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/generar_todos.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/"
git commit -m "Prioridades leen de la base y se retira la reconstruccion cruda

_construir_estado reconstruia el estado desde N revisiones del adaptador
mientras solo la ultima se sustituia por la base. Por eso Bolueta priorizaba
4 viviendas que estructura.exclusiones declara inexistentes y callaba sobre
5 que nadie ha mirado. Una obra sin base ya no calcula: lo dice."
```

---

## Tarea 9: Previsión de desbloqueos

**Ficheros:**
- Modificar: `<motor>/priorizador_trabajos.py`
- Modificar: `<motor>/tests/test_prioridades_desde_base.py`

**Interfaces:**
- Produce: `prevision_desbloqueos(detalle) -> list` ordenada de mayor a menor
  `desbloquea`, cada entrada
  `{'tarea_id', 'trabajo', 'estado_actual', 'desbloquea', 'tajos_afectados'}`.
- Produce: cada item `BLOQUEADO` de `detalle` gana
  `dependencias_detalle: [{'id', 'nombre', 'estado', 'minimo'}]`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
from priorizador_trabajos import prevision_desbloqueos


class TestPrevision(unittest.TestCase):

    def test_dice_cuantas_unidades_libera_cada_tajo(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'P', ('pb', 'cableado', 'A'): 'P',
            ('pb', 'tubeado', 'B'): 'P', ('pb', 'cableado', 'B'): 'P',
            ('1', 'tubeado', 'A'): 'X', ('1', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        prevision = prevision_desbloqueos(resultado['detalle_items'])
        por_tajo = {p['tarea_id']: p for p in prevision}
        self.assertEqual(por_tajo['tubeado']['desbloquea'], 2)
        self.assertIn('cableado', por_tajo['tubeado']['tajos_afectados'])

    def test_ordena_por_lo_que_mas_libera(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'P', ('pb', 'cableado', 'A'): 'P',
            ('pb', 'tubeado', 'B'): 'P', ('pb', 'cableado', 'B'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        prevision = prevision_desbloqueos(resultado['detalle_items'])
        valores = [p['desbloquea'] for p in prevision]
        self.assertEqual(valores, sorted(valores, reverse=True))

    def test_la_fila_bloqueada_dice_cuanto_falta(self):
        ficha = _ficha_con_estados({
            ('pb', 'tubeado', 'A'): 'M', ('pb', 'cableado', 'A'): 'P',
        })
        resultado = priorizar_ficha(ficha, hoy=date(2026, 8, 11))
        cableado = [d for d in resultado['detalle_items']
                    if d['tarea_id'] == 'cableado'][0]
        dep = cableado['dependencias_detalle'][0]
        self.assertEqual(dep['id'], 'tubeado')
        self.assertEqual(dep['estado'], 'M')
        self.assertEqual(dep['minimo'], 1.0)
```

- [ ] **Paso 2: Ejecutar y comprobar que fallan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base.TestPrevision -v
```
Esperado: `ImportError: cannot import name 'prevision_desbloqueos'`.

- [ ] **Paso 3: Implementar**

En `_clasificar_detalle`, dentro del bucle de dependencias, recoger el detalle:

```python
            deps_detalle = []
            for dep in meta.get("deps", []):
                dep_id = dep["id"]
                dep_estado = _buscar_dep(por_loc[loc], dep_id)
                dep_meta = catalogo.meta(dep_id, {"nombre": dep_id})
                nombre_dep = dep_meta.get("nombre", dep_id)
                dep_valor = ESTADO_VALOR.get(dep_estado, 0.0)
                minimo = float(dep.get("minimo", 1.0))
                deps_detalle.append({
                    "id": dep_id, "nombre": nombre_dep,
                    "estado": dep_estado if dep_estado else "Pendiente",
                    "minimo": minimo,
                })
                if dep_valor < minimo:
                    bloqueos.append(nombre_dep)
                else:
                    cumplidas.append(nombre_dep)
```

Y añadir `"dependencias_detalle": deps_detalle,` al `detalle.append({...})`.
Inicializar `deps_detalle = []` junto a `bloqueos = []` para que exista también
en las ramas que no evalúan dependencias.

La función nueva:

```python
def prevision_desbloqueos(detalle):
    """Que se libera al terminar cada tajo.

    Es el valor del apartado en una obra de meses: saber que acabar el suelo
    de tres plantas libera 40 viviendas de tubeado.
    """
    estado_por_celda = {
        (tuple([d["edificio"], d["planta"], d["unidad"]]), d["tarea_id"]): d
        for d in detalle
    }
    libera = defaultdict(lambda: {"unidades": set(), "tajos": set()})
    for item in detalle:
        if item["categoria"] != "BLOQUEADO":
            continue
        loc = (item["edificio"], item["planta"], item["unidad"])
        for dep in item.get("dependencias_detalle") or []:
            if dep["nombre"] not in item["dependencias_bloqueantes"]:
                continue
            registro = libera[dep["id"]]
            registro["unidades"].add((loc, item["tarea_id"]))
            registro["tajos"].add(item["tarea_id"])

    salida = []
    for dep_id, registro in libera.items():
        muestra = next(
            (v for (l, t), v in estado_por_celda.items() if t == dep_id), None)
        salida.append({
            "tarea_id": dep_id,
            "trabajo": muestra["trabajo"] if muestra else dep_id,
            "estado_actual": muestra["estado_actual"] if muestra else "—",
            "desbloquea": len(registro["unidades"]),
            "tajos_afectados": sorted(registro["tajos"]),
        })
    salida.sort(key=lambda x: (-x["desbloquea"], x["trabajo"].casefold()))
    return salida
```

Añadir `"prevision": prevision_desbloqueos(detalle),` al `return` de
`priorizar_ficha`, y `"prevision": []` al de `sin_base`.

- [ ] **Paso 4: Ejecutar y comprobar que pasan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base -v
```
Esperado: `OK`.

- [ ] **Paso 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_prioridades_desde_base.py"
git commit -m "Prever que se desbloquea al terminar cada tajo

Una obra dura meses: saber que acabar el suelo de tres plantas libera 40
viviendas de tubeado es lo que permite llevar el orden hasta el final."
```

---

## Tarea 10: Pintar las secciones nuevas en el panel

**Ficheros:**
- Modificar: `<motor>/panel_obra.py:202-389`
- Crear: `<motor>/tests/test_panel_prioridades.py`

**Interfaces:**
- Consume: `prioridades['resumen']['sin_revisar']`, `prioridades['prevision']`,
  `prioridades['preguntas_orden']`, `prioridades['sin_base']`.

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
# tests/test_panel_prioridades.py
# -*- coding: utf-8 -*-
"""El panel tiene que ensenar lo que el motor calcula. Un dato que se calcula
y no se pinta es lo mismo que no calcularlo."""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import panel_obra


class TestPanelPrioridades(unittest.TestCase):

    def test_una_obra_sin_base_lo_dice_en_pantalla(self):
        html = panel_obra.bloque_prioridades({
            'sin_base': True, 'resumen': {}, 'items': [], 'inventario': [],
            'dudas_pendientes': [], 'preguntas_orden': [], 'prevision': [],
            'avisos': ['Esta obra no tiene base de datos todavía.'],
        })
        self.assertIn('no tiene base de datos', html)
        self.assertNotIn('Bloques viables', html)

    def test_sin_revisar_aparece_con_su_kpi(self):
        html = panel_obra.bloque_prioridades({
            'sin_base': False,
            'resumen': {'sin_revisar': 3, 'unidades_sin_revisar': 190},
            'items': [], 'inventario': [], 'dudas_pendientes': [],
            'preguntas_orden': [], 'prevision': [], 'avisos': [],
        })
        self.assertIn('Sin revisar nunca', html)
        self.assertIn('190', html)

    def test_un_tajo_sin_orden_confirmado_sale_como_pregunta(self):
        html = panel_obra.bloque_prioridades({
            'sin_base': False, 'resumen': {}, 'items': [], 'inventario': [],
            'dudas_pendientes': [], 'prevision': [], 'avisos': [],
            'preguntas_orden': [{
                'codigo': 'TAJO_FUERA_DEL_CATALOGO',
                'tarea_id': 'placas_tps_cuadro', 'nombre': 'Placas tapas',
                'parecidos': ['placas_tapas'],
            }],
        })
        self.assertIn('placas_tps_cuadro', html)
        self.assertIn('placas_tapas', html)

    def test_la_prevision_se_pinta_ordenada(self):
        html = panel_obra.bloque_prioridades({
            'sin_base': False, 'resumen': {}, 'items': [], 'inventario': [],
            'dudas_pendientes': [], 'preguntas_orden': [], 'avisos': [],
            'prevision': [
                {'tarea_id': 'tabicado', 'trabajo': 'Tabicado',
                 'estado_actual': 'Pendiente', 'desbloquea': 40,
                 'tajos_afectados': ['tubeado']},
            ],
        })
        self.assertIn('Tabicado', html)
        self.assertIn('40', html)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Paso 2: Ejecutar y comprobar que fallan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_panel_prioridades -v
```
Esperado: `AttributeError: module 'panel_obra' has no attribute 'bloque_prioridades'`.

- [ ] **Paso 3: Implementar**

Extraer el bloque de las líneas 202-389 de `panel_obra.py` a una función
`bloque_prioridades(prioridades)` de nivel de módulo que devuelve el HTML, y
llamarla desde `generar_panel`. Es la refactorización que permite probar el
panel sin generar una obra entera.

Dentro de la función, al principio:

```python
def bloque_prioridades(prioridades):
    """HTML de la pestana Prioridades. Separado de generar_panel para poder
    probarlo sin montar una obra entera."""
    prioridades = prioridades or {}
    if prioridades.get('sin_base'):
        avisos = prioridades.get('avisos') or [
            'Esta obra no tiene base de datos todavía.']
        return ('<div class="banner bad">⚠ ' + html_lib.escape(avisos[0])
                + '</div>')
```

Añadir el KPI de sin revisar a la fila de KPIs:

```python
      <div class="kpi"><div class="label">Sin revisar nunca</div>
      <div class="value">{resumen_prio.get('sin_revisar', 0)}</div>
      <div class="hint">{resumen_prio.get('unidades_sin_revisar', 0)} celdas que nadie ha mirado</div></div>
```

Añadir la sección `SIN_REVISAR` a la lista `secciones`, entre `DUDAS` y
`TERMINADO`:

```python
        ('SIN_REVISAR', '5. Sin revisar nunca',
         'Nadie los ha mirado todavía. No son trabajo pendiente: son trabajo '
         'por comprobar.'),
```
y renumerar `TERMINADO` a `'6. Tajos terminados'`.

Añadir el bloque de preguntas de orden y el de previsión (tablas simples con
`table-scroll`, siguiendo el patrón de las tablas existentes del fichero).

- [ ] **Paso 4: Ejecutar y comprobar que pasan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```
Esperado: `OK`.

- [ ] **Paso 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/panel_obra.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_panel_prioridades.py"
git commit -m "Pintar sin revisar, preguntas de orden y prevision en el panel

Un dato que se calcula y no se pinta es lo mismo que no calcularlo."
```

---

## Tarea 11: Correcciones menores con su prueba

**Ficheros:**
- Modificar: `<motor>/priorizador_trabajos.py`
- Modificar: `<motor>/tests/test_prioridades_desde_base.py`

- [ ] **Paso 1: Escribir las pruebas que fallan**

```python
from priorizador_trabajos import _scope


class TestCorreccionesMenores(unittest.TestCase):

    def test_zonas_comunes_en_plural_se_reconoce(self):
        meta = {'ambito': 'dinamico'}
        self.assertEqual(
            _scope(meta, 'Tubeado de zonas comunes', 'A'), 'zona_comun')

    def test_el_recorte_a_200_avisa(self):
        detalle = []
        for i in range(260):
            detalle.append({
                'tarea_id': 'tajo_%d' % i, 'trabajo': 'Tajo %d' % i,
                'trabajos_originales': [], 'propiedad': 'propio',
                'ambito': 'vivienda', 'ambito_nombre': 'Viviendas',
                'orden_ejecucion': i, 'fase_nombre': 'F',
                'display_group': 'tajo_%d' % i, 'edificio': 'P1',
                'planta': 'PB', 'unidad': 'A', 'estado': '',
                'estado_actual': 'Pendiente', 'categoria': 'VIABLE',
                'motivo': 'Viable.', 'dependencias_cumplidas': [],
                'dependencias_bloqueantes': [], 'dependencias_sin_dato': [],
                'dependencias_detalle': [], 'omitido_ultima': False,
                'forzado_entregado': False, 'ultima_fecha': '28/07/2026',
            })
        grupos, recortados = _agrupar_prioridades(detalle, limite=200,
                                                  con_recorte=True)
        self.assertEqual(len(grupos), 200)
        self.assertEqual(recortados, 60)
```

- [ ] **Paso 2: Ejecutar y comprobar que fallan**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_prioridades_desde_base.TestCorreccionesMenores -v
```

- [ ] **Paso 3: Implementar**

En `_scope`, corregir la comparación:

```python
    if "zona comun" in texto or "zonas comunes" in texto or "zzcc" in texto:
        return "zona_comun"
```

En `_agrupar_prioridades`, añadir el parámetro y devolver el recorte:

```python
def _agrupar_prioridades(detalle, limite=200, con_recorte=False):
    ...
    recortados = max(0, len(salida) - limite)
    salida = salida[:limite]
    for i, item in enumerate(salida, 1):
        item["orden"] = i
    if con_recorte:
        return salida, recortados
    return salida
```

En `priorizar_ficha`, llamar con `con_recorte=True` y añadir el aviso:

```python
    items, recortados = _agrupar_prioridades(detalle, limite=limite,
                                             con_recorte=True)
    ...
    if recortados:
        avisos.append(
            "La lista se ha recortado a %d bloques; hay %d más sin mostrar."
            % (limite, recortados))
```

- [ ] **Paso 4: Ejecutar, suite completa y commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/priorizador_trabajos.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_prioridades_desde_base.py"
git commit -m "Arreglar la guarda muerta de _scope y avisar del recorte a 200

_scope buscaba 'zona comun' y el catalogo escribe 'zonas comunes': esa
mitad de la condicion no se cumplia nunca."
```

---

## Tarea 12: CHECKPOINT — la cadena de otros gremios

**Esta tarea es datos, no código, y no se puede hacer sin Bixente.**

**Ficheros:**
- Modificar: `<motor>/reglas/CATALOGO_TAJOS.json`
- Modificar: `<motor>/reglas/CRITERIOS_PRIORIZACION_TRABAJOS.md`

- [ ] **Paso 1: Preparar la lista para preguntar**

```
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -c "
import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
d = json.load(open('reglas/CATALOGO_TAJOS.json', encoding='utf-8'))
for t in sorted(d['tajos'], key=lambda x: x['orden']):
    if not t.get('deps'):
        print('%-5s %-13s %s' % (t['orden'], t['propiedad'], t['nombre']))
"
```
Esperado: 19 tajos, 12 de ellos de otros gremios.

- [ ] **Paso 2: Preguntar a Bixente, tajo a tajo**

Punto de partida ya confirmado el 11/08/2026:

> En obra moderna el ladrillo se usa solo para las separaciones entre viviendas
> distintas y con las zonas comunes; el pladur para los interiores de cada
> vivienda.

Por tanto: un tajo de **zona común** lo bloquea `tabicado`; un tajo de
**interior de vivienda** lo bloquea `primera_cara_pladur`.

Dos reasignaciones concretas a confirmar **por separado**:

- `tubeado` (vivienda, orden 130) depende hoy de `tabicado`; por la regla
  debería depender de `primera_cara_pladur`.
- `tubeado_zzcc` (zona común, orden 60) no declara ninguna dependencia; por la
  regla debería depender de `tabicado`.

Y la cadena de gremios entre sí, cada eslabón por separado:
`tabicado → suelo`, `primera_cara_pladur → perfilado_pladur`,
`segunda_cara_pladur → primera_cara_pladur`,
`pintura_primera → techos` y `pintura_segunda → pintura_primera`.

**La que no se confirme se queda sin declarar.** No se inventa ninguna.

- [ ] **Paso 3: Aplicar solo lo confirmado y medir**

Tras cada bloque de cambios, regenerar y comparar contra la línea base. Una
reasignación de dependencia mueve la clasificación de muchas celdas a la vez:
reportar el antes/después por obra antes de commitear.

- [ ] **Paso 4: Actualizar los criterios escritos**

Añadir a `reglas/CRITERIOS_PRIORIZACION_TRABAJOS.md` la sección de tabiquería
con la regla ladrillo/pladur y las dependencias confirmadas.

- [ ] **Paso 5: Commit**

```bash
git add "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/reglas/"
git commit -m "Declarar la cadena de otros gremios que nos condiciona la entrada

Sin ella no hay prevision posible: el motor sabia que el tubeado espera al
tabique pero no que el tabique espera al suelo. Solo lo confirmado por
Bixente; el resto queda como pregunta."
```

---

## Tarea 13: Actualizar el mapa mental de datos

**Ficheros:**
- Modificar: `_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md`

- [ ] **Paso 1: Corregir el inventario desfasado**

Línea 42: dice *"tres `ficha_obra.json` (Gernika, Mungia y Bolueta)… Obispo
opera sin ficha"*. Hoy hay **cinco** bases: Gernika (32 ubicaciones), Mungia
(62), Bolueta (97), Obispo Orueta (102) y OBRA PRUEBA (31). Gorliz sigue
registrado sin revisión ni base.

- [ ] **Paso 2: Añadir el ciclo completo del dato**

Documentar el ciclo de la sección 5.3 de la especificación:
catálogo + base → `generar_todos.py` → `obras_revisiones.js` → generador →
hoja A4 → boli en obra → escaneo → `leer_hoja_marcada.py` → base →
priorizador → Prioridades.

Dejar escrito que **el generador consume la salida del priorizador**
(`crear_registro_revision(obra, prioridades)`), no el catálogo directamente.

- [ ] **Paso 3: Registrar que el catálogo es SIEMPRE AMPLIABLE**

Añadir a la ficha de `reglas/CATALOGO_TAJOS.json` (línea 302) que es la base de
tajos del entorno, ampliable por diseño, con el bucle de ampliación de la
sección 8.2 de la especificación y sus invariantes probados.

- [ ] **Paso 4: Commit**

```bash
git add "_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md"
git commit -m "Actualizar el mapa mental: cinco bases y el ciclo del dato

Decia tres ficha_obra.json y que Obispo operaba sin ficha. Añade el ciclo
catalogo -> hoja -> campo -> base -> prioridades y deja escrito que el
generador consume la salida del priorizador."
```

---

## Verificación final

- [ ] Suite completa en verde, con más pruebas que la línea base de 213.
- [ ] Las cinco obras regeneradas y medidas contra la línea base de la Tarea 1.
- [ ] **KPIs sin moverse:** Mungia 80.1 · Gernika 76.3 · Bolueta 43.5 ·
      Orueta 99.7 · OBRA PRUEBA 6.4.
- [ ] Gorliz sigue saliendo como "Sin revisiones" en el `index.html` generado,
      no como 0 %.
- [ ] `python -m unittest tests.test_paginacion_generador -v` en verde: la hoja
      A4 mantiene sus invariantes pese a que el generador lee del priorizador.
- [ ] `python -m unittest tests.test_jerarquia_sistema -v` en verde: ningún
      fichero técnico fuera de `_SISTEMA`.
- [ ] Ningún fichero mutado para una verificación se ha quedado sin restaurar
      (`git status` limpio salvo lo que se quiera commitear).
- [ ] Antes/después reportado a Bixente.
