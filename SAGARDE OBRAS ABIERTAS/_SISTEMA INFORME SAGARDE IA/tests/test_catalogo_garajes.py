# -*- coding: utf-8 -*-
"""Invariantes de los tajos de garaje declarados en el catalogo."""
import json
import os
import unittest


_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CATALOGO = os.path.join(_BASE, 'reglas', 'CATALOGO_TAJOS.json')
_CAMPOS_OBLIGATORIOS = {
    'id',
    'nombre',
    'aliases',
    'propiedad',
    'ambito',
    'orden',
    'fase',
    'deps',
    'estado_m',
    'estado_x',
    'impacto',
}
_GARAJES_SIN_DEPS = {
    'garaje_tabicado',
    'garaje_raseado_viales',
    'garaje_tubeado_vial',
}


def _cargar_catalogo():
    with open(_CATALOGO, encoding='utf-8') as fichero:
        return json.load(fichero)


def _tajos_garaje(catalogo):
    return [
        tajo
        for tajo in catalogo['tajos']
        if isinstance(tajo.get('id'), str)
        and tajo['id'].startswith('garaje_')
    ]


class TestCatalogoGarajes(unittest.TestCase):

    def test_01_catalogo_es_json_valido(self):
        self.assertIsInstance(_cargar_catalogo(), dict)

    def test_02_hay_exactamente_42_tajos_garaje_en_la_raiz(self):
        garajes = _tajos_garaje(_cargar_catalogo())
        ids = [tajo['id'] for tajo in garajes]
        self.assertEqual(
            (len(garajes), len(set(ids))),
            (42, 42),
            'se esperaban 42 entradas de garaje y 42 ids distintos en '
            "catalogo['tajos']; encontrados %d y %d"
            % (len(garajes), len(set(ids))),
        )

    def test_03_ids_de_garaje_no_colisionan_con_ids_de_vivienda(self):
        catalogo = _cargar_catalogo()
        garajes = _tajos_garaje(catalogo)
        ids_existentes = {}

        for tajo in catalogo['tajos']:
            tajo_id = tajo.get('id')
            if isinstance(tajo_id, str) and not tajo_id.startswith('garaje_'):
                ids_existentes.setdefault(tajo_id, []).append("tajos raiz")

        for obra, configuracion in (catalogo.get('obras') or {}).items():
            for tajo in configuracion.get('tajos') or []:
                tajo_id = tajo.get('id')
                if isinstance(tajo_id, str):
                    ids_existentes.setdefault(tajo_id, []).append(
                        "obras[%r]" % obra
                    )

        colisiones = {
            tajo['id']: ids_existentes[tajo['id']]
            for tajo in garajes
            if tajo['id'] in ids_existentes
        }
        self.assertEqual(
            colisiones,
            {},
            'ids de garaje que ya existen como tajos de vivienda: %r'
            % colisiones,
        )

    def test_04_deps_de_garaje_apuntan_a_tajos_de_la_raiz(self):
        catalogo = _cargar_catalogo()
        ids_raiz = {
            tajo.get('id')
            for tajo in catalogo['tajos']
            if isinstance(tajo.get('id'), str)
        }
        colgantes = []

        for tajo in _tajos_garaje(catalogo):
            for dependencia in tajo.get('deps') or []:
                dependencia_id = (
                    dependencia.get('id')
                    if isinstance(dependencia, dict)
                    else None
                )
                if dependencia_id not in ids_raiz:
                    colgantes.append({
                        'tajo': tajo['id'],
                        'dependencia': dependencia_id,
                        'valor': dependencia,
                    })

        self.assertEqual(
            colgantes,
            [],
            'dependencias de garaje que no existen en catalogo[\'tajos\']: %r'
            % colgantes,
        )

    def test_05_todos_los_tajos_de_garaje_son_zona_comun(self):
        ambitos_incorrectos = {
            tajo['id']: tajo.get('ambito')
            for tajo in _tajos_garaje(_cargar_catalogo())
            if tajo.get('ambito') != 'zona_comun'
        }
        self.assertEqual(
            ambitos_incorrectos,
            {},
            "tajos de garaje cuyo ambito no es 'zona_comun': %r"
            % ambitos_incorrectos,
        )

    def test_06_solo_los_tres_tajos_declarados_tienen_deps_vacio(self):
        ids_sin_deps = {
            tajo['id']
            for tajo in _tajos_garaje(_cargar_catalogo())
            if tajo.get('deps') == []
        }
        self.assertEqual(
            ids_sin_deps,
            _GARAJES_SIN_DEPS,
            'tajos con deps vacio: %r; esperados: %r'
            % (sorted(ids_sin_deps), sorted(_GARAJES_SIN_DEPS)),
        )

    def test_07_ningun_tajo_de_garaje_omite_campos_obligatorios(self):
        campos_ausentes = {
            tajo['id']: sorted(_CAMPOS_OBLIGATORIOS - set(tajo))
            for tajo in _tajos_garaje(_cargar_catalogo())
            if _CAMPOS_OBLIGATORIOS - set(tajo)
        }
        self.assertEqual(
            campos_ausentes,
            {},
            'campos obligatorios ausentes en tajos de garaje: %r'
            % campos_ausentes,
        )


if __name__ == '__main__':
    unittest.main()
