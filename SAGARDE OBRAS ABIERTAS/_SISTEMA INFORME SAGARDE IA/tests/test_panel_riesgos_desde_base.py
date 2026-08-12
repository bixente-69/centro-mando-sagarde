# -*- coding: utf-8 -*-
"""La pestaña Riesgos se reconstruye con las bases en cada actualización."""
import os
import sys
import unittest

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

import panel_obra


def _prioridades(**extra):
    base = {
        'sin_base': False,
        'revision': '28/07/2026',
        'revision_caducada': False,
        'edad_revision_dias': 15,
        'resumen': {
            'bloqueados': 0,
            'unidades_sin_revisar': 0,
            'preguntas_pendientes': 0,
        },
        'prevision': [],
        'avisos': [],
    }
    base.update(extra)
    return base


class TestBloqueosDesdeLaBase(unittest.TestCase):

    def test_muestra_dependencias_y_magnitud_real(self):
        html = panel_obra.bloque_riesgos(
            _prioridades(
                resumen={
                    'bloqueados': 3,
                    'unidades_sin_revisar': 0,
                    'preguntas_pendientes': 0,
                },
                prevision=[{
                    'tarea_id': 'pintura_segunda',
                    'trabajo': 'Pintura — segunda mano',
                    'estado_actual': 'Pendiente',
                    'propiedad': 'externo',
                    'desbloquea': 104,
                    'tajos_afectados': [
                        'Casquillos y bombillas', 'Placas y tapas'],
                }],
            ),
            bloqueos=[],
            riesgos_manual=[],
        )
        self.assertIn('Bloqueos activos que frenan trabajo Sagarde', html)
        self.assertIn('Pintura — segunda mano', html)
        self.assertIn('Otro gremio', html)
        self.assertIn('104', html)
        self.assertIn('Casquillos y bombillas', html)
        self.assertNotIn('<th>Prob.</th>', html)

    def test_distingue_un_bloqueo_interno_sagarde(self):
        html = panel_obra.bloque_riesgos(
            _prioridades(prevision=[{
                'trabajo': 'Cuadro mecanizado',
                'estado_actual': 'M',
                'propiedad': 'propio',
                'desbloquea': 66,
                'tajos_afectados': ['Placas y tapas'],
            }]),
            bloqueos=[],
            riesgos_manual=[],
        )
        self.assertIn('Sagarde', html)
        self.assertIn('Priorizar dentro de Sagarde', html)


class TestRiesgosDeControl(unittest.TestCase):

    def test_sin_base_es_no_evaluable_y_no_sin_riesgos(self):
        html = panel_obra.bloque_riesgos(
            _prioridades(
                sin_base=True,
                revision=None,
                avisos=['Esta obra no tiene base de datos todavía.'],
            ),
            bloqueos=[],
            riesgos_manual=[],
        )
        self.assertIn('Riesgos no evaluables', html)
        self.assertIn('no tiene base de datos', html)
        self.assertNotIn('Sin riesgos registrados', html)

    def test_muestra_revision_caducada_sin_inventar_probabilidad(self):
        html = panel_obra.bloque_riesgos(
            _prioridades(
                revision='01/06/2026',
                edad_revision_dias=72,
                revision_caducada=True,
            ),
            bloqueos=[],
            riesgos_manual=[],
        )
        self.assertIn('Revisión desactualizada', html)
        self.assertIn('72 días', html)
        self.assertIn('Actualizar la revisión de campo', html)

    def test_muestra_sin_revisar_preguntas_y_revisiones_identicas(self):
        html = panel_obra.bloque_riesgos(
            _prioridades(resumen={
                'bloqueados': 0,
                'unidades_sin_revisar': 190,
                'preguntas_pendientes': 5,
            }),
            bloqueos=[],
            riesgos_manual=[],
            sin_cambios=True,
        )
        self.assertIn('190', html)
        self.assertIn('5 decisiones', html)
        self.assertIn('Dos revisiones idénticas', html)

    def test_una_planta_rezagada_se_presenta_como_desviacion(self):
        html = panel_obra.bloque_riesgos(
            _prioridades(),
            bloqueos=[{
                'tipo': 'Planta rezagada',
                'edificio': 'BOLUETA',
                'planta': '23',
                'unidad': '-',
                'avance': 0.7,
                'referencia': 43.5,
                'motivo': 'Planta 23 al 1% frente al 43%.',
            }],
            riesgos_manual=[],
        )
        self.assertIn('Desviación de avance', html)
        self.assertIn('Planta 23 al 1%', html)
        self.assertNotIn('Impacto</th><th>Acción', html)


class TestRiesgosManuales(unittest.TestCase):

    def test_acepta_las_dos_variantes_de_cabeceras_y_escapa_html(self):
        html = panel_obra.bloque_riesgos(
            _prioridades(),
            bloqueos=[],
            riesgos_manual=[{
                'Riesgo': '<Revisar OCA>',
                'Tipo': 'Documentación',
                'Prob.': 'Baja',
                'Impacto': 'Medio',
                'Acción': 'Confirmar expediente',
                'Fecha límite': '20/08/2026',
                'Estado': 'Abierto',
            }],
        )
        self.assertIn('Registro manual', html)
        self.assertIn('&lt;Revisar OCA&gt;', html)
        self.assertNotIn('<Revisar OCA>', html)
        self.assertIn('Confirmar expediente', html)
        self.assertIn('20/08/2026', html)


if __name__ == '__main__':
    unittest.main()
