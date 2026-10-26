# -*- coding: utf-8 -*-
"""Datos INVENTADOS y resultados esperados (calculados a mano) de la pestaña «Base de trabajadores» (paso 08e).

Lo usa tests/verificar_base_trabajadores.py. NO se cambia: los números de aquí no salen de ningún código.
"""

H = {'lun': 7.5, 'mar': 7.5, 'mie': 7.5, 'jue': 7.5, 'vie': 7.5, 'sab': 0, 'dom': 0}


def fila(fecha, ambito, nombre, horas, extra=0, empresa=None):
    f = {'fecha': fecha, 'ambito': ambito, 'nombre': nombre, 'horas': horas, 'extra': extra}
    if empresa:
        f['empresa'] = empresa
    return f


def ficha(i, nombre, empresa='', activo=True, **otras):
    d = {'id': 'T%04d' % i, 'nombre': nombre, 'categoria': '', 'empresa': empresa, 'activo': activo}
    d.update(otras)
    return d


def obra(nombre, jornadas, cerrada=False):
    return {'nombre': nombre, 'cerrada': cerrada, 'horario_semanal': H, 'excepciones_horario': {},
            'ultima': {'vivienda': None, 'garaje': None}, 'jornadas': jornadas}


def estado(catalogo, obras):
    return {'version': 1, 'generado': '2026-10-26T20:00:00+01:00', 'jornada_base_h': 7.5, 'catalogo': catalogo, 'obras': obras}


OLA = '2026 OLABEAGA BILBAO'
MUN = '2026 MUNGIA ACR NEINOR'
ZOE = 'Zoe & <i>Co</i>'   # un nombre con «HTML»: la página tiene que escribirlo tal cual, sin interpretarlo

# ---------------------------------------------------------------- escenario principal
ESTADO_PRINCIPAL = estado(
    [ficha(1, 'Ana', 'Manueles', nombres_anteriores=['Anita']),
     ficha(2, 'Beto', fusionados=['Beto B']),
     ficha(3, 'Carla Ruiz', 'CATERSYSTEM', nombres_anteriores=['Carla']),
     ficha(4, 'Dani', 'Dani @AUT'),
     ficha(5, 'Eli', activo=False),
     ficha(6, ZOE, nombres_anteriores=['<b>vieja</b>'])],
    {'olabeaga': obra(OLA, [
        fila('2026-10-19', 'vivienda', 'Ana', 7.5, empresa='Manueles'),
        fila('2026-10-19', 'vivienda', 'Beto', 7.5),
        fila('2026-10-19', 'vivienda', 'Carla Ruiz', 8, empresa='CATERSYSTEM'),
        fila('2026-10-20', 'vivienda', 'Ana', 7.5, empresa='Manueles'),
        fila('2026-10-20', 'vivienda', 'Carla Ruiz', 8, empresa='CATERSYSTEM'),
        fila('2026-10-20', 'garaje', 'Ana', 2, empresa='Manueles'),
        fila('2026-10-22', 'vivienda', ZOE, 4)]),
     'mungia': obra(MUN, [
         fila('2026-10-21', 'vivienda', 'Ana', 4, empresa='Manueles'),
         fila('2026-10-21', 'vivienda', 'Beto', 4)], cerrada=True)})

NOMBRES = ['Ana', 'Beto', 'Carla Ruiz', 'Dani', 'Eli', ZOE]   # por orden alfabético (el de la página al abrirla)

# Cabecera de la tabla (textContent de cada <th>, en este orden)
CABECERA = ['Nombre', 'Obras donde ha trabajado', 'Días', 'Horas', 'Última jornada', 'Nombres de antes']

# Cifras generales: (número, rótulo) de cada .kpi
# horas totales = 21 (Ana) + 11,5 (Beto) + 16 (Carla Ruiz) + 4 (Zoe) = 52,5
KPIS = [('6', 'personas en la base'), ('4', 'con jornadas'), ('2', 'sin jornadas todavía'), ('52,5 h', 'horas en total')]

# Una fila por persona. Claves (todas en texto tal y como se ve en pantalla de escritorio, `inner_text`):
#   nombre  = el nombre (primera línea de la celda .b-nom)        empresa  = el <span class="nom-emp"> (o '')
#   etiquetas = los .chip de la celda .b-nom                        chips    = los .chip de la celda .b-obras
#   sin_jornadas = la celda .b-obras tiene un .sinj «Sin jornadas todavía» y ningún .chip
#   dias = celda .b-d     horas = celda .b-h     ultima = líneas de la celda .b-ult     historia = celda .b-hist
FILAS = {
    'Ana': {'nombre': 'Ana', 'empresa': 'Manueles', 'etiquetas': [], 'sin_jornadas': False,
            'chips': [OLA + ' · 2 días · 17 h', MUN + ' · 1 día · 4 h'],
            'dias': '3', 'horas': '21', 'ultima': ['21/10/2026', MUN], 'historia': 'Antes se llamaba: «Anita».'},
    'Beto': {'nombre': 'Beto', 'empresa': '', 'etiquetas': [], 'sin_jornadas': False,
             'chips': [OLA + ' · 1 día · 7,5 h', MUN + ' · 1 día · 4 h'],
             'dias': '2', 'horas': '11,5', 'ultima': ['21/10/2026', MUN], 'historia': 'Se juntó con otra ficha: «Beto B».'},
    'Carla Ruiz': {'nombre': 'Carla Ruiz', 'empresa': 'CATERSYSTEM', 'etiquetas': [], 'sin_jornadas': False,
                   'chips': [OLA + ' · 2 días · 16 h'],
                   'dias': '2', 'horas': '16', 'ultima': ['20/10/2026', OLA], 'historia': 'Antes se llamaba: «Carla».'},
    'Dani': {'nombre': 'Dani', 'empresa': 'Dani @AUT', 'etiquetas': [], 'sin_jornadas': True, 'chips': [],
             'dias': '–', 'horas': '–', 'ultima': ['–'], 'historia': '–'},
    'Eli': {'nombre': 'Eli', 'empresa': '', 'etiquetas': ['De baja'], 'sin_jornadas': True, 'chips': [],
            'dias': '–', 'horas': '–', 'ultima': ['–'], 'historia': '–'},
    ZOE: {'nombre': ZOE, 'empresa': '', 'etiquetas': [], 'sin_jornadas': False,
          'chips': [OLA + ' · 1 día · 4 h'],
          'dias': '1', 'horas': '4', 'ultima': ['22/10/2026', OLA], 'historia': 'Antes se llamaba: «<b>vieja</b>».'},
}

# En el móvil (390 px de ancho) lo que se lee en esas celdas de Ana es «21 h» y «3 días» (el «h» y el «días» de las celdas)
MOVIL_ANA = {'horas': '21 h', 'dias': '3 días'}

# Orden (botón data-o): nombres que salen, de arriba abajo.
#   horas: 21 / 16 / 11,5 / 4 y al final los que no tienen jornadas (por nombre)
#   ultima: 22/10 (Zoe), 21/10 (Ana y Beto: con la misma fecha, por nombre), 20/10 (Carla Ruiz) y al final los que no tienen jornadas
ORDENES = {
    'nombre': NOMBRES,
    'horas': ['Ana', 'Carla Ruiz', 'Beto', ZOE, 'Dani', 'Eli'],
    'ultima': [ZOE, 'Ana', 'Beto', 'Carla Ruiz', 'Dani', 'Eli'],
}

# Buscador: (lo que se escribe, nombres que quedan por orden alfabético, texto de .cuenta)
# El buscador no distingue tildes ni mayúsculas y busca en el nombre, la empresa, los nombres de antes, los juntados y las obras.
BUSQUEDAS = [
    ('olabeaga', ['Ana', 'Beto', 'Carla Ruiz', ZOE], 'Se ven 4 de 6 personas'),
    ('mungia', ['Ana', 'Beto'], 'Se ven 2 de 6 personas'),
    ('ANITA', ['Ana'], 'Se ven 1 de 6 personas'),
    ('carla', ['Carla Ruiz'], 'Se ven 1 de 6 personas'),
    ('caters', ['Carla Ruiz'], 'Se ven 1 de 6 personas'),
    ('beto b', ['Beto'], 'Se ven 1 de 6 personas'),
    ('ana mungia', ['Ana'], 'Se ven 1 de 6 personas'),
    ('aut', ['Dani'], 'Se ven 1 de 6 personas'),
    ('ZOE', [ZOE], 'Se ven 1 de 6 personas'),
    ('<i>', [ZOE], 'Se ven 1 de 6 personas'),
    ('   ', NOMBRES, '6 personas'),
]
BUSQUEDA_SIN_RESULTADOS = ('zzz', 'Se ven 0 de 6 personas', 'Nadie coincide con «zzz».')
# Buscar «olabeaga» y luego ordenar por horas:
BUSQUEDA_Y_ORDEN = ('olabeaga', 'horas', ['Ana', 'Carla Ruiz', 'Beto', ZOE])

# ---------------------------------------------------------------- escenarios con avisos y mensajes
#   estado: dict (se escribe como personal_estado.js), None (no se escribe ningún fichero) o str (se escribe tal cual)
#   con_calculo: False = no se copia personal_calculo.js
#   ranking / base: textos que deben salir en #contenido / #contenido-base dentro de .empty y .aviso (en este orden);
#       None = no se comprueba.   filas = nombres de la tabla de la base, por orden.
SIN_FICHERO = ('Todavía no hay datos de personal publicados (no se encontró personal_estado.js). '
               'Cuando se pase el primer control horario a una obra, %s aparecerá aquí.')
FORMATO = '⚠ El fichero personal_estado.js no tiene el formato esperado: versión 2 no soportada.'
ALFA = lambda jornadas: {'alfa': obra('ALFA', jornadas)}   # noqa: E731

ESCENARIOS = [
    {'id': 'sin fichero', 'estado': None, 'con_calculo': True,
     'ranking': {'empty': [SIN_FICHERO % 'el ranking'], 'aviso': []},
     'base': {'empty': [SIN_FICHERO % 'la base de trabajadores'], 'aviso': [], 'filas': []}},
    {'id': 'versión 2', 'estado': {'version': 2, 'obras': {}, 'catalogo': []}, 'con_calculo': True,
     'ranking': {'empty': [], 'aviso': [FORMATO]}, 'base': {'empty': [], 'aviso': [FORMATO], 'filas': []}},
    {'id': 'sin personal_calculo.js', 'estado': ESTADO_PRINCIPAL, 'con_calculo': False,
     'ranking': {'empty': [], 'aviso': ['⚠ No se pudo cargar personal_calculo.js: la página no puede calcular el ranking.']},
     'base': {'empty': [], 'aviso': ['⚠ No se pudo cargar personal_calculo.js: '
                                     'la página no puede calcular la base de trabajadores.'], 'filas': []}},
    {'id': 'base vacía', 'estado': estado([], {}), 'con_calculo': True,
     'ranking': {'empty': ['Todavía no hay jornadas anotadas en ninguna obra.'], 'aviso': []},
     'base': {'empty': ['Todavía no hay nadie en la base de trabajadores.'], 'aviso': [], 'filas': []}},
    {'id': 'personas sin jornadas',
     'estado': estado([ficha(1, 'Ana'), ficha(2, 'Beto')], ALFA([])), 'con_calculo': True,
     'ranking': {'empty': ['Todavía no hay jornadas anotadas en ninguna obra.'], 'aviso': []},
     'base': {'empty': [], 'aviso': [], 'filas': ['Ana', 'Beto'],
              'kpis': [('2', 'personas en la base'), ('0', 'con jornadas'), ('2', 'sin jornadas todavía'), ('–', 'horas en total')]}},
    {'id': 'sin lista de la base',
     'estado': {'version': 1, 'obras': ALFA([fila('2026-10-19', 'vivienda', 'Ana', 7.5), fila('2026-10-20', 'vivienda', 'Beto', 8)])},
     'con_calculo': True, 'ranking': None,
     'base': {'empty': [], 'aviso': ['⚠ El fichero no trae la lista de la base: solo se ven las personas que tienen jornadas.'],
              'filas': ['Ana', 'Beto'], 'sin_etiqueta_aviso': True}},
    {'id': 'jornadas de alguien que no está en la base',
     'estado': estado([ficha(1, 'Ana')], ALFA([fila('2026-10-19', 'vivienda', 'Ana', 7.5), fila('2026-10-21', 'vivienda', 'Nadie', 6)])),
     'con_calculo': True, 'ranking': None,
     'base': {'empty': [], 'aviso': ['⚠ Esta persona tiene jornadas pero no figura en la lista de la base: «Nadie».'],
              'filas': ['Ana', 'Nadie'], 'etiquetas': {'Ana': [], 'Nadie': ['No está en la lista de la base']}}},
    {'id': 'dos jornadas que no se cuentan',
     'estado': estado([ficha(1, 'Ana')], ALFA([fila('2026-10-19', 'vivienda', 'Ana', 7.5), fila('2026-10-20', 'vivienda', 'Ana', None),
                                               fila('2026-10-21', 'vivienda', 'Ana', 30)])),
     'con_calculo': True, 'ranking': None,
     'base': {'empty': [], 'aviso': ['⚠ Hay 2 jornadas que no se cuentan en las horas de la base: '
                                     '1 sin horas y 1 con datos no válidos.'], 'filas': ['Ana']}},
    {'id': 'una jornada que no se cuenta',
     'estado': estado([ficha(1, 'Ana')], ALFA([fila('2026-10-19', 'vivienda', 'Ana', 7.5), fila('2026-10-20', 'vivienda', 'Ana', None)])),
     'con_calculo': True, 'ranking': None,
     'base': {'empty': [], 'aviso': ['⚠ Hay 1 jornada que no se cuenta en las horas de la base: '
                                     '1 sin horas y 0 con datos no válidos.'], 'filas': ['Ana']}},
    {'id': 'una ficha sin nombre',
     'estado': estado([ficha(1, 'Ana'), {'id': 'T0009', 'empresa': '', 'activo': True}], ALFA([])),
     'con_calculo': True, 'ranking': None,
     'base': {'empty': [], 'aviso': ['⚠ Hay 1 ficha de la base sin nombre; no se enseña.'], 'filas': ['Ana']}},
    {'id': 'dos fichas sin nombre',
     'estado': estado([ficha(1, 'Ana'), {'id': 'T0008', 'empresa': ''}, {'id': 'T0009', 'nombre': '   '}], ALFA([])),
     'con_calculo': True, 'ranking': None,
     'base': {'empty': [], 'aviso': ['⚠ Hay 2 fichas de la base sin nombre; no se enseñan.'], 'filas': ['Ana']}},
    {'id': 'nombre repetido',
     'estado': estado([ficha(1, 'Ana'), ficha(2, 'ana')], ALFA([])), 'con_calculo': True, 'ranking': None,
     'base': {'empty': [], 'aviso': ['⚠ Hay nombres repetidos en la base: «ana». Solo se enseña una ficha de cada nombre.'],
              'filas': ['Ana']}},
    {'id': 'historial ilegible',
     'estado': estado([ficha(1, 'Fede', nombres_anteriores='Fedor')], ALFA([])), 'con_calculo': True, 'ranking': None,
     'base': {'empty': [], 'aviso': ['⚠ No se pudo leer el historial de nombres de «Fede».'], 'filas': ['Fede']}},
    {'id': 'obra con jornadas ilegibles',
     'estado': estado([ficha(1, 'Ana')], {'alfa': {'nombre': 'ALFA', 'jornadas': 'roto'}}), 'con_calculo': True, 'ranking': None,
     'base': {'empty': [], 'aviso': ['⚠ No se pudieron leer las jornadas de la obra «ALFA»; no se cuentan.'], 'filas': ['Ana']}},
]

ZONAS_HORARIAS = ['Europe/Madrid', 'Pacific/Auckland', 'America/Los_Angeles']
