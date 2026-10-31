# -*- coding: utf-8 -*-
"""Paso MA4c: la lógica que decide qué hacer con un nombre recién escrito en la tablet (clasificarNombreEscrito de
generador_personal.html). Es lógica pura: se saca del HTML tal cual está y se ejecuta con node contra más de 60 casos escritos
a mano (nombre que no está, que se parece, que ya está sin conflicto de empresa, con otra empresa, de baja, con tildes,
mayúsculas y espacios, «Nombre B.», dos iguales publicados...). P3_APP apunta a otra copia de la app (para las mutaciones: se
rompe una COPIA, nunca el original)."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

TESTS = Path(__file__).resolve().parent
APP_DIR = Path(os.environ.get("P3_APP") or TESTS.parent)

# Las tres ayudas que la función usa y que la tablet define más arriba (se comprueba que siguen siendo las mismas).
CLEAN = "const clean = (s) => (typeof s === 'string' ? s.trim().replace(/" + chr(92) + "s+/g, ' ') : '');"
KEY = "const key = (s) => clean(s).normalize('NFD').replace(/[" + chr(92) + "u0300-" + chr(92) + "u036f]/g, '').toLowerCase();"

VERIFICADOR = r'''// Verificador OCULTO de clasificarNombreEscrito (MA4c). Uso: node verif_clasificar.js <fichero.js que define clasificarNombreEscrito>
// Casos escritos a mano con nombres INVENTADOS; el esperado sale de la tabla del diseño, no de ninguna implementación.
const path = require('path');
const fs = require('fs');
const vm = require('vm');
const fuente = fs.readFileSync(path.resolve(process.argv[2]), 'utf8');
const ctx = {};
vm.createContext(ctx);
vm.runInContext(fuente + '\n;this.__f = (typeof clasificarNombreEscrito === "function") ? clasificarNombreEscrito : null;', ctx);
const f = ctx.__f;
if (typeof f !== 'function') {
  console.log('FALLO: no existe la función clasificarNombreEscrito');
  process.exit(1);
}
const B = [
  { nombre: 'Rafa', empresa: 'Alfa Instalaciones', activo: true },
  { nombre: 'Pepe', empresa: '', activo: true },
  { nombre: 'Luis', empresa: 'Beta Montajes', activo: true },
  { nombre: 'Ander', empresa: 'Gamma Electrica', activo: false },
  { nombre: 'Íñigo Prueba', empresa: 'Alfa Instalaciones', activo: true },
  { nombre: 'Dani', empresa: 'Dani @AUT', activo: true },
  { nombre: 'Rafa B.', empresa: 'Beta Montajes', activo: true },
  { nombre: 'Zoilo Fuentes', empresa: 'Sagarde', activo: true },
  { nombre: 'Electra', empresa: 'Electrónica Norte', activo: true },
];
const C = []; // [id, nombre, empresa, base, enLista, tipo, existente]
const c = (id, nombre, empresa, base, enLista, tipo, existente) =>
  C.push([id, nombre, empresa, base, enLista, tipo, existente === undefined ? null : existente]);
c(1, 'Rafa', 'Beta Montajes', B, [], 'otra_persona_posible', 'Rafa');
c(2, 'Rafa', '', B, [], 'mismo', 'Rafa');
c(3, 'Rafa', 'Alfa Instalaciones', B, [], 'mismo', 'Rafa');
c(4, 'rafa', 'alfa instalaciones', B, [], 'mismo', 'Rafa');
c(5, 'RAFÁ', 'Beta Montajes', B, [], 'otra_persona_posible', 'Rafa');
c(6, '  rafa  ', 'BETA MONTAJES', B, [], 'otra_persona_posible', 'Rafa');
c(7, 'Pepe', 'Beta Montajes', B, [], 'mismo', 'Pepe');
c(8, 'Pepe', '', B, [], 'mismo', 'Pepe');
c(9, 'Luis', 'Alfa Instalaciones', B, [], 'otra_persona_posible', 'Luis');
c(10, 'Ander', '', B, [], 'de_baja', 'Ander');
c(11, 'Ander', 'Gamma Electrica', B, [], 'de_baja', 'Ander');
c(12, 'ander', 'Alfa Instalaciones', B, [], 'de_baja', 'Ander');
c(13, 'Íñigo Prueba', 'Beta Montajes', B, [], 'otra_persona_posible', 'Íñigo Prueba');
c(14, 'inigo prueba', '', B, [], 'mismo', 'Íñigo Prueba');
c(15, 'INIGO   PRUEBA', 'Alfa Instalaciones', B, [], 'mismo', 'Íñigo Prueba');
c(16, 'Iñigo  Prueba', 'Beta Montajes', B, [], 'otra_persona_posible', 'Íñigo Prueba');
c(17, 'Dani', 'Dani @AUT', B, [], 'mismo', 'Dani');
c(18, 'Dani', 'Alfa Instalaciones', B, [], 'otra_persona_posible', 'Dani');
c(19, 'Dani', 'dani @aut', B, [], 'mismo', 'Dani');
c(20, 'Dani', 'Dani', B, [], 'otra_persona_posible', 'Dani');
c(21, 'Rafa B.', 'Beta Montajes', B, [], 'mismo', 'Rafa B.');
c(22, 'Rafa B.', 'Alfa Instalaciones', B, [], 'otra_persona_posible', 'Rafa B.');
c(23, 'Rafa B.', '', B, [], 'mismo', 'Rafa B.');
c(24, 'Marcos', 'Alfa Instalaciones', B, [], 'nuevo', null);
c(25, 'Marcos', '', B, [], 'nuevo', null);
c(26, 'Rafaa', '', B, [], 'parecido', 'Rafa');
c(27, 'Rafa Pérez', 'Beta Montajes', B, [], 'nuevo', null);
c(57, 'Rafa Pérez', '', B, [], 'parecido', 'Rafa');
c(58, 'Rafa Pérez', 'Alfa Instalaciones', B, [], 'parecido', 'Rafa');
c(59, 'Rafa B', '', [{ nombre: 'Rafa', empresa: 'Alfa Instalaciones', activo: true }], [], 'nuevo', null);
c(60, 'Rafa', '', [{ nombre: 'Rafa B.', empresa: 'Beta Montajes', activo: true }], [], 'nuevo', null);
c(61, 'Ana M', '', [{ nombre: 'Ana', empresa: '', activo: true }], [], 'nuevo', null);
c(62, 'Rafa Bl', '', [{ nombre: 'Rafa', empresa: '', activo: true }], [], 'parecido', 'Rafa');
c(63, 'Rafaa', 'Beta Montajes', B, [], 'parecido', 'Rafa');
c(64, 'Pepe García', 'Beta Montajes', [{ nombre: 'Pepe', empresa: '', activo: true }], [], 'parecido', 'Pepe');
c(65, 'Luis Gómez', 'Alfa Instalaciones', B, [], 'nuevo', null);
c(66, 'Luis Gómez', 'Beta Montajes', B, [], 'parecido', 'Luis');
c(68, 'Rafa Gómez', 'Gamma Electrica', B, ['Rafa', 'Pepe'], 'nuevo', null);
c(69, 'Rafa Gómez', 'Beta Montajes', B, ['Zoilo Fuentes'], 'nuevo', null);
c(70, 'Rafa Gómez', 'Beta Montajes', [], ['Rafa'], 'parecido', 'Rafa');
c(28, 'Pepa', '', B, [], 'parecido', 'Pepe');
c(29, 'Pe', '', B, [], 'nuevo', null);
c(30, 'Lu', '', B, [], 'nuevo', null);
c(31, 'Luisa', '', B, [], 'parecido', 'Luis');
c(32, 'Nuevo Fulano', '', B, ['Nuevo Fulano'], 'mismo', 'Nuevo Fulano');
c(33, 'nuevo fulano', 'Beta Montajes', B, ['Nuevo Fulano'], 'mismo', 'Nuevo Fulano');
c(34, 'Nuevo Fulana', '', B, ['Nuevo Fulano'], 'parecido', 'Nuevo Fulano');
c(35, 'Rafa', 'Beta Montajes', [], [], 'nuevo', null);
c(36, 'Rafa B.', '', [], ['Rafa'], 'nuevo', null);
c(67, 'Rafa Pérez', 'Beta Montajes', [], ['Rafa'], 'parecido', 'Rafa');
c(37, 'Rafa', 'Beta Montajes', B, ['Rafa'], 'otra_persona_posible', 'Rafa');
const DOS = [
  { nombre: 'Rafa', empresa: 'Alfa Instalaciones', activo: true },
  { nombre: 'Rafa', empresa: 'Beta Montajes', activo: true },
];
c(38, 'Rafa', 'Beta Montajes', DOS, [], 'mismo', 'Rafa');
c(39, 'Rafa', 'Gamma Electrica', DOS, [], 'otra_persona_posible', 'Rafa');
c(
  40,
  'Rafa',
  'Alfa Instalaciones',
  [
    { nombre: 'Rafa', empresa: 'Alfa Instalaciones', activo: false },
    { nombre: 'Rafa', empresa: 'Alfa Instalaciones', activo: true },
  ],
  [],
  'mismo',
  'Rafa',
);
c(41, 'Rafa', 'Beta Montajes', [{ nombre: 'Rafa', empresa: 'Alfa Instalaciones', activo: false }], [], 'de_baja', 'Rafa');
c(42, 'Pepe', 'Beta Montajes', [{ nombre: 'Pepe', activo: true }], [], 'mismo', 'Pepe');
c(43, 'Pepe', 'Beta Montajes', [{ nombre: 'Pepe', empresa: 'Alfa Instalaciones' }], [], 'otra_persona_posible', 'Pepe');
c(44, 'Rafa', undefined, B, [], 'mismo', 'Rafa');
c(45, '', 'Beta Montajes', B, [], 'nuevo', null);
c(46, '   ', '', B, [], 'nuevo', null);
c(47, 'ELECTRA', 'electronica norte', B, [], 'mismo', 'Electra');
c(48, 'Zoilo Fuentes', 'Sagarde', B, [], 'mismo', 'Zoilo Fuentes');
c(49, 'zoilo fuentes', 'Manueles', B, [], 'otra_persona_posible', 'Zoilo Fuentes');
c(50, 'Anders', '', B, [], 'parecido', 'Ander');
c(51, 'Rafa B', '', B, [], 'parecido', 'Rafa B.');
c(52, 'Li', 'Y', [{ nombre: 'Li', empresa: 'X', activo: true }], [], 'otra_persona_posible', 'Li');
c(53, 'Lu', '', [{ nombre: 'Li', empresa: 'X', activo: true }], [], 'nuevo', null);
c(
  54,
  'Marto',
  '',
  [
    { nombre: 'Marta', empresa: '', activo: true },
    { nombre: 'Marti', empresa: '', activo: true },
  ],
  [],
  'parecido',
  'Marta',
);
c(55, 'Rafa', 'Beta Montajes', undefined, undefined, 'nuevo', null);
c(56, 'Rafa', '', B, undefined, 'mismo', 'Rafa');
let mal = 0;
const antes = JSON.stringify([B, DOS]);
for (const [id, nombre, empresa, base, enLista, tipo, existente] of C) {
  let r;
  try {
    r = f({ nombre, empresa, base, enLista });
  } catch (e) {
    console.log('FALLO caso ' + id + ': lanza ' + e.message);
    mal++;
    continue;
  }
  const exis = r && r.existente === undefined ? null : r && r.existente;
  if (!r || r.tipo !== tipo || exis !== existente) {
    console.log(
      'FALLO caso ' + id + ' (' + JSON.stringify(nombre) + ', ' + JSON.stringify(empresa) + '): esperaba ' + tipo + '/' + existente + ' y da ' + JSON.stringify(r),
    );
    mal++;
  }
}
if (JSON.stringify([B, DOS]) !== antes) {
  console.log('FALLO: la función modifica la base que recibe');
  mal++;
}
console.log(mal ? 'HAY ' + mal + ' fallos de ' + C.length : 'OK ' + C.length + ' casos');
process.exit(mal ? 1 : 0);
'''


def funciones_del_html(texto):
    """`lev`, `masUnaInicial` y `clasificarNombreEscrito`, tal cual están en la tablet."""
    ini_lev = texto.index("function lev(x, y) {")
    fin_lev = texto.index("// Devuelve un nombre ya existente", ini_lev)
    ini = texto.index("function masUnaInicial(largo, corto) {")
    fin = texto.index("// Las personas de la base tal como las ve la tablet", ini)
    return texto[ini_lev:fin_lev] + "\n" + texto[ini:fin]


class TestClasificarNombreEscrito(unittest.TestCase):
    def setUp(self):
        self.texto = (APP_DIR / "generador_personal.html").read_text(encoding="utf-8")
        self.funciones = funciones_del_html(self.texto)

    def test_las_ayudas_de_la_tablet_son_las_que_usa_la_prueba(self):
        """`clean` y `key` los define la tablet más arriba; la prueba usa una copia: si cambian, esta prueba avisa."""
        bs = chr(92)
        for trozo in (
            "clean = (s) => (typeof s === 'string' ? s.trim().replace(/" + bs + "s+/g, ' ') : '')",
            ".normalize('NFD')",
            ".replace(/[" + bs + "u0300-" + bs + "u036f]/g, '')",
            ".toLowerCase()",
        ):
            self.assertIn(trozo, self.texto)

    def test_los_casos_de_la_funcion_pura(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("falta node: NO se ha revisado la lógica de «¿es el mismo o es otra persona?»")
        base = Path(os.environ.get("P3_TMP") or tempfile.gettempdir()) / ("clasifica_nombre_" + uuid.uuid4().hex[:8])
        base.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, str(base), True)
        (base / "clasificar.js").write_text(CLEAN + "\n" + KEY + "\n" + self.funciones, encoding="utf-8")
        (base / "verificador.js").write_text(VERIFICADOR, encoding="utf-8")
        p = subprocess.run([node, str(base / "verificador.js"), str(base / "clasificar.js")], capture_output=True, timeout=120)
        salida = p.stdout.decode("utf-8", "replace")
        self.assertEqual(0, p.returncode, salida + p.stderr.decode("utf-8", "replace"))
        m = re.search(r"OK (" + chr(92) + "d+) casos", salida)
        self.assertTrue(m and int(m.group(1)) >= 60, "se han revisado muy pocos casos: " + salida)

    def test_la_funcion_no_toca_la_pantalla_ni_el_reloj(self):
        for prohibido in ("document", "localStorage", "Date.now", "Math.random", "new Date()", "toast(", "render(", "a.list", "state"):
            self.assertNotIn(prohibido, self.funciones, "la función pura no puede llevar «%s»" % prohibido)

    def test_crear_con_la_pregunta_no_usa_el_parecido_de_la_otra_persona(self):
        """«Rafa B.» contiene a «Rafa»: si el campo de la otra persona pasara por el parecido, la pregunta no acabaría nunca."""
        cuerpo = self.texto[self.texto.index("function crearOtraPersona() {"):]
        cuerpo = cuerpo[: cuerpo.index("// Aviso de personas con el mismo nombre")]
        for prohibido in ("similar(", "clasificarNombreEscrito("):
            self.assertNotIn(prohibido, cuerpo)

    def test_crear_un_nombre_nuevo_clasifica_antes_de_escribir_nada(self):
        cuerpo = self.texto[self.texto.index("if (datos.nuevo !== undefined) {"):]
        cuerpo = cuerpo[: cuerpo.index("// Confirma el aviso de nombre parecido")]
        self.assertLess(cuerpo.index("clasificarNombreEscrito("), cuerpo.index("news.push("), "primero se clasifica, luego se crea")
        self.assertLess(cuerpo.index("a.homonimo = {"), cuerpo.index("news.push("), "la pregunta sale antes de crear nada")

    def test_la_tablet_no_lleva_nombres_de_ejemplo(self):
        for n in ("Mikel", "Rafa", "Pepe", "Luis", "Alfa Instalaciones", "Beta Montajes"):
            self.assertNotIn(n, self.texto, "la tablet no puede llevar datos incrustados («%s»)" % n)


if __name__ == "__main__":
    unittest.main()
