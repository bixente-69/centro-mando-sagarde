# Esquema de datos normalizado

El generador recibe un único JSON UTF-8. Las claves se mantienen estables para que una entrada manuscrita, un PDF o una futura interfaz puedan producir el mismo informe.

## Raíz

```json
{
  "identification": {},
  "battery": {},
  "grounding": {},
  "panels": [],
  "analyzer": {},
  "ups": {},
  "general_observation": "",
  "zones": [],
  "lighting": [],
  "deficiencies": [],
  "materials": [],
  "evidence": [],
  "closure": {},
  "signatures": {}
}
```

## Identificación

```json
{
  "identification": {
    "sagarde_code": "CARDIVA_PREV_29072026",
    "work_order": "",
    "client": "CARDIVA",
    "site": "Centro Lezama",
    "date": "29/07/2026",
    "period": "Preventivo",
    "entry_time": "08:00",
    "exit_time": "",
    "technicians": "Eneko / Vicente Trancón",
    "cardiva_contact": ""
  }
}
```

## Punto 01: batería de condensadores

`controls` debe contener B-01…B-04. `steps` contiene los escalones existentes.

```json
{
  "battery": {
    "controls": [
      {"id": "B-01", "status": "OK", "observation": ""}
    ],
    "readings": {
      "voltage": "407 V",
      "current": "49,5 A",
      "wpf": "0,88",
      "capacitor_current": "102 %",
      "temperature": "27 °C",
      "kvar": "-2,00 kVAr",
      "ind": "0,95 CAP",
      "thdi": "18,0 %",
      "thdv": "1,30 %"
    },
    "steps": [
      {"id": "E1", "nominal": "5 kVAr", "measured": "Prueba manual", "status": "OK", "observation": ""}
    ]
  }
}
```

## Punto 02: pararrayos y puesta a tierra

`elements` debe contener P-01…P-04. Si el parte no registra un control, usar `N/R`; si no aplica, `N/A`.

```json
{
  "grounding": {
    "elements": [
      {"id": "P-01", "status": "N/R", "observation": "No registrado en el parte de entrada"}
    ],
    "meter": "HT GSC-53",
    "serial": "03102018",
    "calibration": "SGS · 19/09/2023 · Cert. 110420",
    "limit": "≤ 10 Ω",
    "result": "9,3 Ω estimados",
    "status": "OK*",
    "observation": "..."
  }
}
```

## Punto 03: cuadros, analizador y SAI

Cada cuadro aporta los seis estados de control y las siete lecturas. Los códigos de cuadro deben coincidir con los de la plantilla.

```json
{
  "panels": [
    {
      "code": "QG",
      "controls": {
        "cleaning": "OK",
        "terminals": "OK",
        "identification": "OK",
        "ground": "OK",
        "differential": "OK",
        "temperature": "OK"
      },
      "observation": "",
      "measurements": {
        "v12": "397",
        "v23": "403",
        "v31": "396",
        "v1n": "232",
        "v2n": "235",
        "v3n": "235",
        "ground_ohm": "7"
      }
    }
  ],
  "analyzer": {
    "v12": "397",
    "v23": "403",
    "v31": "396",
    "pf_l1": "0,97",
    "pf_l2": "0,82",
    "pf_l3": "0,92",
    "i_l1": "57,20",
    "i_l2": "26,70",
    "i_l3": "27,40",
    "kwh": "962809",
    "status": "OK"
  },
  "ups": {
    "model": "Liebert GXT4",
    "v_out": "230",
    "v_in": "234",
    "battery": "100",
    "autonomy": "62,6",
    "status": "OK",
    "observation": ""
  }
}
```

## Punto 04: zonas

Debe haber una entrada por Z01…Z18.

```json
{
  "zones": [
    {
      "id": "Z01",
      "sockets": "OK",
      "voltage": "OK",
      "ground": "OK",
      "automation": "N/A",
      "observation": ""
    }
  ]
}
```

## Puntos 05 y 06: alumbrado

Debe haber una entrada por L01…L22. `units` puede dejarse vacío cuando el estado sea `OK`.

```json
{
  "lighting": [
    {
      "id": "L03",
      "status": "DEF",
      "units": "2",
      "model": "1 empotrable LED + 1 panel LED 60×60",
      "observation": "Fundidas · D-01 · F-01"
    }
  ]
}
```

## Derivados 07, 08 y 09

Una fila `DEF` en los puntos 01–06 debe tener una deficiencia `D-xx`. Cada deficiencia genera una evidencia `F-xx` y una página de fotografía, aunque la fotografía quede pendiente.

```json
{
  "deficiencies": [
    {
      "id": "D-01",
      "location": "PB · Logística",
      "description": "Dos luminarias fundidas",
      "criticality": "B",
      "action": "Sustituir luminarias · SAGARDE",
      "date": "Pendiente",
      "status": "ABIERTA"
    }
  ],
  "materials": [
    {
      "id": "M-01",
      "material": "Empotrable LED",
      "quantity": "1",
      "destination": "D-01",
      "status": "PENDIENTE"
    }
  ],
  "evidence": [
    {
      "id": "F-01",
      "file": "Pendiente de insertar",
      "location": "PB · Logística",
      "deficiency": "D-01",
      "caption": "D-01 · Dos luminarias fundidas"
    }
  ],
  "closure": {
    "general_result": "CONDICIONADO: ...",
    "report_status": "CERRADO CON 1 DEFICIENCIA ABIERTA",
    "technical_summary": "...",
    "related_reports": "...",
    "next_action": "..."
  },
  "signatures": {
    "technician": "Eneko / Vicente Trancón",
    "seal": ""
  }
}
```

## Estados y color

Estados admitidos: `OK`, `DEF`, `N/R`, `N/A`, `PEND`, `PENDIENTE`, `ABIERTA`, `TERCERO`, `PROGRAMADA`, `RESUELTA`.

El generador escribe todos los resultados y estados con texto negro sobre fondo blanco. Los colores corporativos se reservan a los encabezados, títulos, bordes y logotipos.
