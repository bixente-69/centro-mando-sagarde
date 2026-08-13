# Carácter visual del informe ejecutivo — Plan de ejecución

> **Para agentes:** SUB-SKILL OBLIGATORIA: usar `superpowers:subagent-driven-development`
> (recomendada) o `superpowers:executing-plans` para ejecutar este plan tarea a
> tarea. Los pasos usan casillas (`- [ ]`) para seguimiento.

**Objetivo:** que el informe ejecutivo deje de parecer hecho por un script —
tipografía propia, color que describe en vez de juzgar, y logo sin deformar—
sin mover ni una cifra.

**Arquitectura:** todo ocurre dentro de `generar_informe_ejecutivo.py`. Se
añaden dos activos (las TTF de IBM Plex Sans) y se dan de alta en la lista
blanca del `.gitignore`. Las pruebas nuevas viven junto a las del informe y se
apoyan en `pdfplumber`, que ya es dependencia del proyecto.

**Stack:** Python 3, ReportLab, `unittest` de la biblioteca estándar,
`pdfplumber` (ya presente). **No se introducen dependencias nuevas.**

**Especificación:** `_SISTEMA/docs/superpowers/specs/2026-08-13-informe-ejecutivo-caracter-design.md`

## Restricciones globales

- **Ninguna cifra del informe puede cambiar.** Mungia debe seguir en
  **80.7 % / 1159 de 1528** y sus cuatro páginas.
- Las demás obras no se mueven: Gernika 76.3, Bolueta 43.5, OBRA PRUEBA 6.4.
- Nada de dependencias nuevas. Bixente lo ejecuta todo con ficheros `.bat`.
- Pruebas con `unittest`. **Nunca `pytest`.**
- **Nunca `git add -A`.** Cada commit nombra sus ficheros.
- No se toca `_filtrar_snapshot_sagarde`, ni la jerarquía, ni el contenido, ni
  el resto de generadores del entorno.
- Rutas: `MOTOR = _SISTEMA/MOTOR`, `SISTEMA_IA = SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA`.

---

### Tarea 1: Traer las fuentes y publicarlas

**Ficheros:**
- Crear: `_SISTEMA/MOTOR/assets/fonts/IBMPlexSans-Regular.ttf`
- Crear: `_SISTEMA/MOTOR/assets/fonts/IBMPlexSans-Bold.ttf`
- Crear: `_SISTEMA/MOTOR/assets/fonts/OFL.txt`
- Modificar: `.gitignore`
- Crear prueba: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_caracter.py`

**Interfaces:**
- Produce: la carpeta `assets/fonts/` con dos TTF **estáticas** y la licencia.
  Las tareas 2 y 3 dependen de que existan.

**Por qué el `.gitignore`:** es lista blanca (`*` ignora todo y luego se
permite). Sin dar de alta estos ficheros, una restauración desde git deja el
informe sin fuente. Hoy le pasa ya al logo: la línea 14 publica
`!POST-VENTAS/logo_sagarde.jpg`, pero el que usa el informe,
`_SISTEMA/MOTOR/assets/logo_sagarde.jpg`, **no está en git**.

- [ ] **Paso 1: Descargar las fuentes**

Las de `google/fonts` **no sirven**: son variables y ReportLab no las maneja.
Estas son estáticas (196 KB cada una), comprobado el 13/08/2026.

```bash
mkdir -p "_SISTEMA/MOTOR/assets/fonts"
curl -L -o "_SISTEMA/MOTOR/assets/fonts/IBMPlexSans-Regular.ttf" \
  "https://github.com/IBM/plex/raw/master/packages/plex-sans/fonts/complete/ttf/IBMPlexSans-Regular.ttf"
curl -L -o "_SISTEMA/MOTOR/assets/fonts/IBMPlexSans-Bold.ttf" \
  "https://github.com/IBM/plex/raw/master/packages/plex-sans/fonts/complete/ttf/IBMPlexSans-Bold.ttf"
curl -L -o "_SISTEMA/MOTOR/assets/fonts/OFL.txt" \
  "https://github.com/google/fonts/raw/main/ofl/ibmplexsans/OFL.txt"
```

La SIL OFL exige que la licencia acompañe a la fuente: `OFL.txt` no es opcional.

- [ ] **Paso 2: Escribir la prueba que falla**

Crear `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_caracter.py`:

```python
# -*- coding: utf-8 -*-
'''Caracter visual del informe ejecutivo: tipografia, color y logo.'''
import os
import sys
import unittest


SISTEMA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.dirname(SISTEMA_DIR))
sys.path.insert(0, SISTEMA_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'scripts'))

FONTS_DIR = os.path.join(ROOT_DIR, '_SISTEMA', 'MOTOR', 'assets', 'fonts')
GITIGNORE = os.path.join(ROOT_DIR, '.gitignore')


class TestActivosDelInforme(unittest.TestCase):
    '''Los activos existen y estan publicados.

    El .gitignore es lista blanca: lo que no se da de alta no llega a git, y
    una restauracion deja el informe sin fuente ni logo. Sin ruido.
    '''

    def test_las_dos_ttf_existen_y_son_estaticas(self):
        for nombre in ('IBMPlexSans-Regular.ttf', 'IBMPlexSans-Bold.ttf'):
            ruta = os.path.join(FONTS_DIR, nombre)
            self.assertTrue(os.path.isfile(ruta), 'falta la fuente ' + nombre)
            with open(ruta, 'rb') as f:
                cabecera = f.read(4)
                f.seek(0)
                entera = f.read()
            self.assertEqual(cabecera, b'\x00\x01\x00\x00',
                             nombre + ' no es una TTF valida')
            self.assertNotIn(b'fvar', entera,
                             nombre + ' es una fuente VARIABLE; ReportLab '
                             'necesita la estatica')

    def test_la_licencia_acompana_a_la_fuente(self):
        self.assertTrue(os.path.isfile(os.path.join(FONTS_DIR, 'OFL.txt')),
                        'la SIL OFL exige distribuir la licencia con la fuente')

    def test_fuentes_y_logo_estan_en_la_lista_blanca(self):
        with open(GITIGNORE, encoding='utf-8') as f:
            lineas = {l.strip() for l in f}
        for regla in ('!_SISTEMA/MOTOR/assets/fonts/*.ttf',
                      '!_SISTEMA/MOTOR/assets/fonts/OFL.txt',
                      '!_SISTEMA/MOTOR/assets/logo_sagarde.jpg'):
            self.assertIn(regla, lineas,
                          'sin esta linea el fichero no llega a git: ' + regla)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Paso 3: Ejecutarla y ver que falla**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_informe_ejecutivo_caracter -v
```

Esperado: `test_fuentes_y_logo_estan_en_la_lista_blanca` FALLA (las reglas aún
no existen). Las otras dos ya pasan si el paso 1 se hizo bien.

- [ ] **Paso 4: Dar de alta los activos en el `.gitignore`**

Añadir tras la línea 18 (`!Actualizar_Sagarde.bat`):

```gitignore
# Activos del informe ejecutivo. El .gitignore es lista blanca: sin estas
# lineas, la tipografia y el logo se quedan fuera de git y una restauracion
# produce un informe sin fuente. El logo de POST-VENTAS (linea 14) es OTRA
# copia: la que usa generar_informe_ejecutivo.py es esta.
!_SISTEMA/MOTOR/assets/logo_sagarde.jpg
!_SISTEMA/MOTOR/assets/fonts/*.ttf
!_SISTEMA/MOTOR/assets/fonts/OFL.txt
```

- [ ] **Paso 5: Ejecutar y ver que pasa**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_informe_ejecutivo_caracter -v
```

Esperado: los tres tests PASAN.

- [ ] **Paso 6: Comprobar con git que de verdad entran**

```bash
git status --porcelain "_SISTEMA/MOTOR/assets"
```

Esperado: `?? _SISTEMA/MOTOR/assets/` — git los ve como nuevos, o sea **no
ignorados**. Si no aparece nada, la lista blanca no surte efecto.

**No usar `git check-ignore -v` para esto:** con `-v` git imprime también las
reglas de negación y devuelve 0, así que parece que los está ignorando cuando
en realidad los está admitiendo. Confunde más que ayuda.

- [ ] **Paso 7: Commit**

```bash
git add ".gitignore" "_SISTEMA/MOTOR/assets/fonts/IBMPlexSans-Regular.ttf" "_SISTEMA/MOTOR/assets/fonts/IBMPlexSans-Bold.ttf" "_SISTEMA/MOTOR/assets/fonts/OFL.txt" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_caracter.py"
git commit -m "Informe ejecutivo: traer IBM Plex Sans y publicar sus activos

El .gitignore es lista blanca y no publicaba ni las fuentes ni el logo que
usa el informe -- solo la copia de POST-VENTAS. Una restauracion desde git
producia un informe sin tipografia. La prueba lo vigila leyendo el propio
.gitignore, asi que quitar la linea vuelve a poner el test en rojo.

Fuentes estaticas de IBM/plex: las de google/fonts son variables y ReportLab
no las maneja. Se incluye OFL.txt porque la licencia lo exige."
```

---

### Tarea 2: Registrar la fuente, y que falte sea un error ruidoso

**Ficheros:**
- Modificar: `_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py` (imports ~línea 25-34, constantes ~línea 41)
- Modificar prueba: `SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_caracter.py`

**Interfaces:**
- Consume: `assets/fonts/*.ttf` de la Tarea 1.
- Produce: `gie.FUENTE` (`'IBMPlexSans'`), `gie.FUENTE_BOLD`
  (`'IBMPlexSans-Bold'`), `gie.FONTS_DIR` (`Path`) y
  `gie._registrar_fuentes() -> None`. La Tarea 3 usa los dos primeros.

**El fallo silencioso que se desactiva aquí:** en ReportLab, si registras la
fuente pero **no** declaras la familia con `registerFontFamily`, las etiquetas
`<b>` del informe dejan de tener efecto. El PDF se genera igual, plano, sin una
sola queja. Y si la fuente falta, la tentación es volver a Helvetica: eso es
justo lo que hace hoy el logo, y es lo que no queremos heredar.

- [ ] **Paso 1: Escribir las pruebas que fallan**

Añadir a `tests/test_informe_ejecutivo_caracter.py`:

```python
import tempfile
from pathlib import Path

from reportlab.pdfbase import pdfmetrics

import generar_informe_ejecutivo as gie


class TestRegistroDeFuente(unittest.TestCase):

    def setUp(self):
        gie._registrar_fuentes()

    def test_registra_las_dos_variantes(self):
        registradas = pdfmetrics.getRegisteredFontNames()
        self.assertIn(gie.FUENTE, registradas)
        self.assertIn(gie.FUENTE_BOLD, registradas)

    def test_la_familia_resuelve_la_negrita(self):
        '''Sin registerFontFamily los <b> del informe dejan de funcionar y
        NO da error. Mutacion: quitar la llamada a registerFontFamily y este
        test tiene que ponerse en rojo.'''
        self.assertEqual(
            pdfmetrics.getFont(gie.FUENTE).face.familyName,
            pdfmetrics.getFont(gie.FUENTE_BOLD).face.familyName)
        from reportlab.lib.fonts import tt2ps
        self.assertEqual(tt2ps(gie.FUENTE, 1, 0), gie.FUENTE_BOLD)

    def test_si_falta_la_fuente_falla_con_mensaje_legible(self):
        '''Un informe en Helvetica sin avisar es peor que un informe que no
        sale. Mutacion: sustituir el raise por un return y esto se pone rojo.'''
        original = gie.FONTS_DIR
        try:
            gie.FONTS_DIR = Path(tempfile.gettempdir()) / 'no_existe_sagarde'
            pdfmetrics._fonts.pop(gie.FUENTE, None)
            pdfmetrics._fonts.pop(gie.FUENTE_BOLD, None)
            with self.assertRaises(RuntimeError) as ctx:
                gie._registrar_fuentes()
            self.assertIn('IBMPlexSans-Regular.ttf', str(ctx.exception))
        finally:
            gie.FONTS_DIR = original
            gie._registrar_fuentes()
```

- [ ] **Paso 2: Ejecutar y ver que fallan**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_informe_ejecutivo_caracter.TestRegistroDeFuente -v
```

Esperado: FALLAN con `AttributeError: module ... has no attribute '_registrar_fuentes'`.

- [ ] **Paso 3: Implementar el registro**

En `generar_informe_ejecutivo.py`, añadir a los imports de ReportLab (junto a
la línea 34):

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
```

Y tras `LOGO_PATH` (línea 41):

```python
FONTS_DIR = ASSETS_DIR / "fonts"
FUENTE = 'IBMPlexSans'
FUENTE_BOLD = 'IBMPlexSans-Bold'


def _registrar_fuentes() -> None:
    '''Registra IBM Plex Sans para el informe.

    Falla a gritos si falta la tipografia. Volver a Helvetica en silencio
    produciria un informe con el aspecto de siempre y nadie se enteraria:
    es exactamente el fallo que este trabajo viene a quitar.
    '''
    if FUENTE in pdfmetrics.getRegisteredFontNames():
        return
    ficheros = {
        FUENTE: FONTS_DIR / 'IBMPlexSans-Regular.ttf',
        FUENTE_BOLD: FONTS_DIR / 'IBMPlexSans-Bold.ttf',
    }
    faltan = [str(ruta) for ruta in ficheros.values() if not ruta.is_file()]
    if faltan:
        raise RuntimeError(
            'Falta la tipografia del informe ejecutivo: ' + ', '.join(faltan) +
            '. Se descarga segun la Tarea 1 de _SISTEMA/docs/superpowers/'
            'plans/2026-08-13-informe-ejecutivo-caracter.md')
    for nombre, ruta in ficheros.items():
        pdfmetrics.registerFont(TTFont(nombre, str(ruta)))
    # Sin esta linea los <b> del informe dejan de tener efecto SIN dar error.
    pdfmetrics.registerFontFamily(
        FUENTE, normal=FUENTE, bold=FUENTE_BOLD,
        italic=FUENTE, boldItalic=FUENTE_BOLD)
```

Y llamarla al principio de `generar_pdf_ejecutivo()` (línea 958), como primera
sentencia del cuerpo:

```python
    _registrar_fuentes()
```

- [ ] **Paso 4: Ejecutar y ver que pasan**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_informe_ejecutivo_caracter -v
```

Esperado: todos PASAN.

- [ ] **Paso 5: Commit**

```bash
git add "_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_caracter.py"
git commit -m "Informe ejecutivo: registrar IBM Plex Sans, y fallar si no esta

Registra las dos variantes y declara la familia. Lo segundo importa mas de lo
que parece: sin registerFontFamily, las etiquetas <b> que el informe usa por
todas partes dejan de tener efecto y el PDF sale plano, sin dar ningun error.

Si falta el .ttf se lanza RuntimeError con la ruta que falta. No se vuelve a
Helvetica en silencio: ese patron es el que tiene hoy el logo y el que este
trabajo viene a quitar."
```

---

### Tarea 3: Cambiar Helvetica por Plex en los siete sitios

**Ficheros:**
- Modificar: `_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py` líneas 297, 336, 354, 360, 388, 402, 410
- Modificar prueba: `tests/test_informe_ejecutivo_caracter.py`

**Interfaces:**
- Consume: `gie.FUENTE` y `gie.FUENTE_BOLD` de la Tarea 2.

**Cuidado:** `_style()` (línea 297) cubre todos los párrafos, pero los tres
gráficos escriben la fuente a mano en cada `String()` y **no pasan por
`_style()`**. Si solo se cambia la fábrica, el informe sale con dos
tipografías. Además, **ninguna `TableStyle` del fichero declara `FONTNAME`**,
así que cualquier celda de texto plano caería en la Helvetica por defecto de
ReportLab. Por eso la prueba mira las fuentes **dentro del PDF generado**: caza
el caso venga de donde venga.

- [ ] **Paso 1: Escribir la prueba que falla**

Añadir a `tests/test_informe_ejecutivo_caracter.py`:

```python
import pdfplumber


def _pdf_de_prueba(destino):
    '''Genera un informe minimo pero real, con las funciones de produccion.'''
    snapshot = [
        {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
         'unit': 'A', 'status': 'X'},
        {'task': 'Tubeado interior', 'building': 'P1', 'floor': '1',
         'unit': 'B', 'status': 'M'},
        {'task': 'Cuadro mecanizado', 'building': 'P1', 'floor': '1',
         'unit': 'A', 'status': ''},
    ]
    gie.generar_pdf_ejecutivo(
        'OBRA DE PRUEBA', '01/08/2026', snapshot, destino,
        historial=[('01/08/2026', snapshot)])
    return destino


class TestTipografiaEnElPDF(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.pdf = _pdf_de_prueba(Path(cls.tmp.name) / 'informe.pdf')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _fuentes_del_pdf(self):
        with pdfplumber.open(str(self.pdf)) as doc:
            return {c['fontname'] for p in doc.pages for c in p.chars}

    def test_no_queda_helvetica_en_el_pdf(self):
        '''Caza tambien las celdas de texto plano, que no pasan por _style().
        Mutacion: devolver 'Helvetica' en _style() y esto se pone rojo.'''
        rastro = [f for f in self._fuentes_del_pdf() if 'Helvetica' in f]
        self.assertEqual(rastro, [], 'queda Helvetica en el PDF: ' + str(rastro))

    def test_la_fuente_incrustada_es_plex(self):
        fuentes = self._fuentes_del_pdf()
        self.assertTrue(any('IBMPlexSans' in f for f in fuentes),
                        'el PDF no incrusta IBM Plex Sans: ' + str(fuentes))

    def test_sigue_habiendo_negrita(self):
        '''Mutacion: quitar registerFontFamily y esto se pone rojo, porque
        todos los <b> caerian a la variante normal.'''
        fuentes = self._fuentes_del_pdf()
        self.assertTrue(any('Bold' in f for f in fuentes),
                        'no hay ni una negrita en el PDF: ' + str(fuentes))
```

- [ ] **Paso 2: Ejecutar y ver que falla**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_informe_ejecutivo_caracter.TestTipografiaEnElPDF -v
```

Esperado: `test_no_queda_helvetica_en_el_pdf` FALLA listando fuentes Helvetica.

- [ ] **Paso 3: Sustituir en los siete sitios**

En `_style()`, línea 297:

```python
        fontName=FUENTE_BOLD if bold else FUENTE,
```

En `_grafico_tendencia`, líneas 336, 354 y 360: cambiar `fontName='Helvetica'`
por `fontName=FUENTE` y `fontName='Helvetica-Bold'` por `fontName=FUENTE_BOLD`.

En `_grafico_distribucion`, línea 388: `fontName='Helvetica'` → `fontName=FUENTE`.

En `_grafico_fases`, líneas 402 y 410: `fontName='Helvetica'` → `fontName=FUENTE`
y `fontName='Helvetica-Bold'` → `fontName=FUENTE_BOLD`.

Comprobar que no queda ninguna:

```bash
grep -n "Helvetica" "_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py"
```

Esperado: **sin resultados**.

- [ ] **Paso 4: Ejecutar y ver que pasa**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_informe_ejecutivo_caracter -v
```

Esperado: todos PASAN.

- [ ] **Paso 5: Commit**

```bash
git add "_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_caracter.py"
git commit -m "Informe ejecutivo: IBM Plex Sans en los siete sitios

_style() cubre los parrafos, pero los tres graficos llevaban la fuente escrita
a mano en cada String() y no pasan por ahi: cambiar solo la fabrica dejaba el
informe con dos tipografias.

La prueba no mira el codigo, mira las fuentes DENTRO del PDF generado. Asi
caza tambien las celdas de texto plano, que no pasan por _style() y caerian a
la Helvetica por defecto de ReportLab -- ninguna TableStyle del fichero
declara FONTNAME."
```

---

### Tarea 4: Que el color describa en vez de juzgar

**Ficheros:**
- Modificar: `_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py` líneas 305, 317-322, y las llamadas de 411, 463, 465, 555
- Modificar prueba: `tests/test_informe_ejecutivo_caracter.py`

**Interfaces:**
- Produce: `gie._color_estado(pct) -> colors.Color`. Sustituye a `_color_pct`,
  que desaparece.

**La duplicación:** la regla del semáforo está escrita **dos veces**.
`_color_pct` (317-322) y una copia a mano dentro de `_make_mini_bar`
(línea 305, un ternario en línea). Cambiar solo una deja las barras de los KPI
con el semáforo viejo. Es el «arreglar un camino y dejar roto su hermano» que
avisa el `CLAUDE.md`.

**Decisión de la especificación (§5.3):** la regla se aplica **a todo**,
incluidos los dos números grandes de cabecera. El `78.7 %` de Mungia pasa de
verde a azul marino. Bixente lo sabe y lo aprobó así; si cambia de opinión, es
darle a los KPI de cabecera su propia función.

- [ ] **Paso 1: Escribir la prueba que falla**

Añadir a `tests/test_informe_ejecutivo_caracter.py`:

```python
class TestColorDescriptivo(unittest.TestCase):
    '''El color describe el estado, no lo juzga.

    Con el semaforo viejo, la pagina 1 de Mungia enseñaba tres lineas rojas
    -- "Remates finales 0 %" entre ellas -- en una obra al 80 %. Esas fases
    no van mal: es que todavia no tocan.
    '''

    def test_terminado_es_verde(self):
        self.assertEqual(gie._color_estado(100), gie.COL_OK)

    def test_sin_empezar_es_gris_no_rojo(self):
        self.assertEqual(gie._color_estado(0), gie.COL_GRIS)
        self.assertNotEqual(gie._color_estado(0), gie.COL_WARN)

    def test_en_marcha_es_azul_sea_alto_o_bajo(self):
        for pct in (1, 22, 59, 92, 99):
            self.assertEqual(gie._color_estado(pct), gie.COL_ACCENT,
                             'el %d %% deberia ser azul' % pct)

    def test_la_barra_mini_no_tiene_su_propia_regla(self):
        '''La regla estaba escrita dos veces: en _color_pct y copiada a mano
        en un ternario dentro de _make_mini_bar. Mutacion: volver a poner ahi
        un color literal y este test tiene que enterarse.'''
        import inspect
        fuente = inspect.getsource(gie._make_mini_bar)
        self.assertIn('_color_estado(pct)', fuente)
        for literal in ('#2E9E5B', '#E07B1A', '#D9483C'):
            self.assertNotIn(literal, fuente,
                             'vuelve a haber una regla de color propia aqui')

    def test_la_barra_mini_se_construye_sin_reventar(self):
        for pct in (0, 50, 100):
            self.assertIsNotNone(gie._make_mini_bar(pct))

    def test_ya_no_existe_la_funcion_vieja(self):
        self.assertFalse(hasattr(gie, '_color_pct'),
                         '_color_pct debe desaparecer, no convivir')
```

- [ ] **Paso 2: Ejecutar y ver que falla**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_informe_ejecutivo_caracter.TestColorDescriptivo -v
```

Esperado: FALLAN con `AttributeError: ... '_color_estado'`.

- [ ] **Paso 3: Implementar la regla única**

Añadir junto a las constantes de color (tras la línea 291):

```python
COL_GRIS   = colors.HexColor('#98A2B3')
```

Sustituir `_color_pct` (líneas 317-322) por:

```python
def _color_estado(pct: float):
    '''El color describe el estado; no lo juzga.

    Verde terminado, azul en marcha, gris todavia sin empezar. El rojo se
    reserva para la tabla de condicionantes, que es donde hay un problema de
    verdad: un tajo al 0 % que es del final de obra no va mal, es que aun no
    toca, y pintarlo de rojo afirmaba algo falso sobre la obra.
    '''
    if pct >= 100:
        return COL_OK
    if pct <= 0:
        return COL_GRIS
    return COL_ACCENT
```

En `_make_mini_bar`, sustituir la línea 305 por:

```python
    col = _color_estado(pct)
```

Y renombrar las cuatro llamadas restantes: líneas 411, 463, 465 y 555 pasan de
`_color_pct(...)` a `_color_estado(...)`.

Comprobar que no queda ninguna:

```bash
grep -n "_color_pct" "_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py"
```

Esperado: **sin resultados**.

- [ ] **Paso 4: Ejecutar y ver que pasa**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_informe_ejecutivo_caracter -v
```

Esperado: todos PASAN.

- [ ] **Paso 5: Commit**

```bash
git add "_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_caracter.py"
git commit -m "Informe ejecutivo: el color describe el estado, no lo juzga

El semaforo por porcentaje pintaba de rojo lo que solo es que aun no toca. La
pagina 1 de Mungia enseñaba tres lineas rojas -- Remates finales, Remates
exteriores, Entrega -- en una obra que va al 80 %. Un promotor abria eso y leia
una obra con problemas. El color afirmaba algo falso.

Ahora: verde terminado, azul en marcha, gris sin empezar, y el rojo reservado
para condicionantes, que es donde hay un problema real.

La regla estaba escrita dos veces, en _color_pct y copiada a mano dentro de
_make_mini_bar. Cambiar solo una habria dejado las barras de los KPI con el
semaforo viejo. Ahora hay una sola funcion y una prueba que lo vigila."
```

---

### Tarea 5: El logo, sin deformar y sin fallar en silencio

**Ficheros:**
- Modificar: `_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py` líneas 423-425 y 760
- Modificar prueba: `tests/test_informe_ejecutivo_caracter.py`

**Interfaces:**
- Produce: `gie._logo_flowable(ancho_mm: float) -> Image`. La usan las dos
  cabeceras.

**El defecto:** el logo mide 2732×751 (ratio **3.638**) y se coloca a 48×14 mm
(3.429) en la línea 423 y a 52×15 mm (3.467) en la 760. Va aplastado, y con
distinta deformación en cada página.

La altura se calcula desde el ancho leyendo el tamaño real con `ImageReader`,
que ya viene con ReportLab. Así el arreglo sobrevive a que algún día se
sustituya el logo.

**Se quita también el respaldo mudo** de las líneas 423-425: hoy, si el fichero
falta, el informe sale con la palabra «SAGARDE» en texto y nadie se entera. Se
hace por coherencia con la Tarea 2 — no tiene sentido dejar en pie el mismo
fallo que acabamos de quitarle a la fuente, en las líneas que ya estamos
reescribiendo.

- [ ] **Paso 1: Escribir la prueba que falla**

Añadir a `tests/test_informe_ejecutivo_caracter.py`:

```python
class TestLogo(unittest.TestCase):

    def test_respeta_la_proporcion_nativa(self):
        '''Iba aplastado, y distinto en cada pagina: 3.429 en la 1 y 3.467 en
        la 2, sobre un nativo de 3.638.'''
        from reportlab.lib.utils import ImageReader
        ancho_px, alto_px = ImageReader(str(gie.LOGO_PATH)).getSize()
        nativo = ancho_px / alto_px
        for ancho_mm in (48, 52):
            img = gie._logo_flowable(ancho_mm)
            self.assertAlmostEqual(img.drawWidth / img.drawHeight, nativo,
                                   places=2)

    def test_todas_las_paginas_usan_la_misma_proporcion(self):
        a, b = gie._logo_flowable(48), gie._logo_flowable(52)
        self.assertAlmostEqual(a.drawWidth / a.drawHeight,
                               b.drawWidth / b.drawHeight, places=3)

    def test_si_falta_el_logo_falla_con_mensaje_legible(self):
        '''Hoy caia a la palabra "SAGARDE" en texto sin avisar. Mutacion:
        devolver un Paragraph en vez de lanzar y esto se pone rojo.'''
        original = gie.LOGO_PATH
        try:
            gie.LOGO_PATH = Path(tempfile.gettempdir()) / 'no_hay_logo.jpg'
            with self.assertRaises(RuntimeError) as ctx:
                gie._logo_flowable(48)
            self.assertIn('logo', str(ctx.exception).lower())
        finally:
            gie.LOGO_PATH = original
```

- [ ] **Paso 2: Ejecutar y ver que falla**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_informe_ejecutivo_caracter.TestLogo -v
```

Esperado: FALLAN con `AttributeError: ... '_logo_flowable'`.

- [ ] **Paso 3: Implementar**

Añadir al import de utilidades de ReportLab:

```python
from reportlab.lib.utils import ImageReader
```

Y una función junto a `_style()`:

```python
def _logo_flowable(ancho_mm: float) -> Image:
    '''El logo a un ancho dado, con su proporcion real.

    La altura se calcula, no se escribe: estaba a 48x14 mm en una cabecera y a
    52x15 en la otra, sobre un nativo de 2732x751, asi que salia aplastado y
    distinto en cada pagina.

    Si falta el fichero se lanza un error. Antes caia a la palabra "SAGARDE"
    escrita en texto y el informe salia sin logo sin que nadie se enterase.
    '''
    if not LOGO_PATH.is_file():
        raise RuntimeError(
            'Falta el logo del informe ejecutivo: ' + str(LOGO_PATH))
    ancho_px, alto_px = ImageReader(str(LOGO_PATH)).getSize()
    ancho = ancho_mm * mm
    return Image(str(LOGO_PATH), width=ancho, height=ancho * alto_px / ancho_px)
```

Sustituir las líneas 423-425 por:

```python
    logo = _logo_flowable(48)
```

Y la línea 760 por:

```python
    logo_cell = _logo_flowable(52)
```

- [ ] **Paso 4: Ejecutar y ver que pasa**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest tests.test_informe_ejecutivo_caracter -v
```

Esperado: todos PASAN.

- [ ] **Paso 5: Limpiar el fondo del logo**

El JPEG tiene fondo azul pálido —esquinas `(232,245,253)` y `(194,230,246)`—
y por eso parece un recuadro pegado sobre la hoja. Generar una versión con
fondo blanco, conservando el original:

```bash
cp "_SISTEMA/MOTOR/assets/logo_sagarde.jpg" "_SISTEMA/MOTOR/assets/logo_sagarde.ORIGINAL.jpg"
```

```python
from PIL import Image as PILImage

ruta = '_SISTEMA/MOTOR/assets/logo_sagarde.jpg'
im = PILImage.open('_SISTEMA/MOTOR/assets/logo_sagarde.ORIGINAL.jpg').convert('RGB')
pixels = im.load()
# Todo pixel casi-blanco o azul palido de fondo pasa a blanco puro.
# El azul del logotipo es (55, 59, 122) en el centro: queda muy por debajo
# del umbral y no se toca.
for y in range(im.size[1]):
    for x in range(im.size[0]):
        r, g, b = pixels[x, y]
        if r > 180 and g > 210 and b > 225:
            pixels[x, y] = (255, 255, 255)
im.save(ruta, quality=95)
print('guardado', ruta)
```

Comprobar las esquinas después:

```bash
python -c "from PIL import Image; im=Image.open('_SISTEMA/MOTOR/assets/logo_sagarde.jpg').convert('RGB'); w,h=im.size; print([im.getpixel(p) for p in [(2,2),(w-3,2),(2,h-3),(w-3,h-3)]])"
```

Esperado: las cuatro esquinas en `(255, 255, 255)` o muy cerca.

**Revisar el resultado a ojo antes de seguir.** Si el umbral se ha comido parte
del logo, ajustarlo y repetir desde el original conservado.

- [ ] **Paso 6: Commit**

```bash
git add "_SISTEMA/MOTOR/scripts/generar_informe_ejecutivo.py" "_SISTEMA/MOTOR/assets/logo_sagarde.jpg" "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA/tests/test_informe_ejecutivo_caracter.py"
git commit -m "Informe ejecutivo: logo sin deformar y sin respaldo mudo

El logo mide 2732x751 (ratio 3.638) y se colocaba a 48x14 mm en una cabecera
y a 52x15 en la otra: aplastado, y con distinta deformacion en cada pagina.
Ahora la altura se calcula del tamaño real con ImageReader, asi que el arreglo
sobrevive a que algun dia se cambie el logo.

Tambien tenia fondo azul palido y parecia un recuadro pegado sobre la hoja.

Y se quita el respaldo mudo: si faltaba el fichero, el informe salia con la
palabra SAGARDE escrita en texto y nadie se enteraba. Ahora falla."
```

---

### Tarea 6: Verificar que no se ha movido ni una cifra

**Ficheros:**
- Ninguno que modificar. Es la comprobación de cierre.

**Por qué existe como tarea:** el `CLAUDE.md` del proyecto pide comprobar que
las obras no implicadas no se mueven y reportar el antes/después. El porcentaje
redondeado es un criterio ciego, así que se comparan los números del PDF.

- [ ] **Paso 1: Guardar el estado de partida**

Antes de nada, con el código **ya modificado** pero desde el último informe
publicado en disco, extraer los números del PDF actual de Mungia:

```bash
python - <<'PY'
import pdfplumber, re, json
p = ("SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/"
     "INFORME_EJECUTIVO_2026_MUNGIA_ACR_NEINOR.pdf")
with pdfplumber.open(p) as d:
    txt = "\n".join(pg.extract_text() or "" for pg in d.pages)
    print(json.dumps({"paginas": len(d.pages),
                      "numeros": re.findall(r"\d+[.,]?\d*\s*%|\d+\s*/\s*\d+", txt)},
                     ensure_ascii=False, indent=1))
PY
```

Guardar la salida.

- [ ] **Paso 2: Regenerar Mungia**

```bash
python "_SISTEMA/MOTOR/scripts/regenerar_obra.py" "2026 MUNGIA ACR NEINOR"
```

**No usar `--finalizar`** y **no lanzar `Actualizar_Sagarde.bat`**: aquí no se
publica nada.

- [ ] **Paso 3: Comparar**

Repetir el script del Paso 1 y comparar las dos salidas. **Deben ser
idénticas**: mismas páginas (4) y mismos números, incluidos `80.7 %` y
`1159/1528`. Si algo difiere, parar e investigar antes de seguir.

- [ ] **Paso 4: Comprobar que las demás obras no se mueven**

```bash
python -c "import json;d=json.load(open('SAGARDE OBRAS ABIERTAS/resumen_obras.json',encoding='utf-8'));print([(o['nombre'],o.get('pct_ponderado')) for o in d['obras'] if o.get('pct_ponderado') is not None])"
```

Esperado: Gernika 76.3, Bolueta 43.5, OBRA PRUEBA 6.4, Mungia 80.1.

- [ ] **Paso 5: Las dos suites en verde**

```bash
cd "SAGARDE OBRAS ABIERTAS/_SISTEMA INFORME SAGARDE IA" && python -m unittest discover -s tests
```

```bash
cd "_SISTEMA/MOTOR" && python -m unittest discover -s tests
```

Esperado: motor 48 y obras 329 más las nuevas, sin fallos ni errores nuevos.

- [ ] **Paso 6: Comparación visual y reporte a Bixente**

Renderizar las cuatro páginas antes y después y mirarlas:

```bash
python - <<'PY'
import fitz
p = ("SAGARDE OBRAS ABIERTAS/2026 MUNGIA ACR NEINOR/INFORME SAGARDE IA/"
     "INFORME_EJECUTIVO_2026_MUNGIA_ACR_NEINOR.pdf")
doc = fitz.open(p)
for i, page in enumerate(doc):
    page.get_pixmap(dpi=110).save(f"despues_p{i+1}.png")
print("paginas:", doc.page_count)
PY
```

Reportar a Bixente: el antes/después visual, la confirmación de que los números
no se han movido, y el estado de las dos suites. **Aplicar en silencio un
cambio que mueve cifras es el problema desde el otro lado.**

- [ ] **Paso 7: Actualizar el mapa mental**

El inventario de ficheros ha cambiado: hay una carpeta `assets/fonts/` nueva y
un fichero de pruebas nuevo. Reflejarlo en
`_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md` — la prosa se escribe a mano;
los bloques `AUTO:` los regenera el `.bat`.

```bash
git add "_SISTEMA/docs/SAGARDE_MAPA_MENTAL_ENTORNO.md"
git commit -m "Mapa mental: la carpeta assets/fonts del informe ejecutivo

Un mapa desfasado es peor que no tenerlo."
```

---

## Notas para quien ejecute

- **Publicar es decisión de Bixente.** Ninguna tarea lanza
  `Actualizar_Sagarde.bat`. Hay además trabajo de Codex sin commitear en el
  árbol (`verificar_hojas_pdf.py` y su prueba): el `git add -A` del `.bat` lo
  arrastraría.
- **`regenerar_obra.py` no ejercita todo el flujo:** sustituye
  `publicar_registro_revisiones` por una función vacía. Para esta verificación
  vale, porque no tocamos el camino de publicación.
- Si una prueba parece verificar algo, **rómpela a propósito** y comprueba que
  se entera. Cada test de este plan lleva escrita su mutación.
