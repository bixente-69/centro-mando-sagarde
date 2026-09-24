# Estudio Integral y Planning Eléctrico para Garajes y Áreas Técnicas en Edificación Residencial

**Documento:** `estudiogarajesagy.md`  
**Proyecto:** Adaptación del Sistema Sagarde IA a Garajes y Cuartos Técnicos  
**Fecha:** 24/09/2026  
**Autor:** Antigravity / Sagarde  

---

## 1. Introducción y Enfoque Metodológico

En las obras de edificación residencial, el garaje constituye un sector funcional crítico con exigencias técnicas, constructivas y normativas radicalmente distintas a las de las viviendas:

1. **Topología del espacio**: En viviendas la matriz de trabajo es simétrica y modular ($\text{Bloque} \to \text{Planta} \to \text{Mano/Vivienda} \to \text{Tajo}$). En el garaje conviven grandes áreas diáfanas (viales de maniobra y plazas), baterías modulares de trasteros, núcleos verticales de comunicación (escaleras y ascensores) y múltiples recintos técnicos con maquinaria pesada y cuadros especializados.
2. **Naturaleza de las instalaciones**: Predomina la instalación vista (tubo rígido de superficie libre de halógenos enchufado/abocardado y bandejas metálicas de rejilla o chapa perforada), alturas de gálibo estrictas ($\ge 2{,}20\text{ m}$) y coordinación espacial tridimensional con conductos de ventilación/extracción de humos (chapa $400^\circ\text{C}/2\text{h}$ o EI), tuberías colgadas de saneamiento y redes de protección contra incendios (BIEs y rociadores).
3. **Marco reglamentario exigente**:
   - **REBT ITC-BT-28**: Local de pública concurrencia (cables de alta seguridad AS libre de halógenos, doble circuito de alumbrado, alumbrado de emergencia exhaustivo).
   - **REBT ITC-BT-29**: Desclasificación de atmósfera potencialmente explosiva mediante ventilación mecánica forzada continua o controlada por CO.
   - **REBT ITC-BT-52**: Infraestructura para recarga de vehículos eléctricos (IRVE).
   - **CTE DB-SI / RIPCI**: Resistencia al fuego de cables para ventilación/sobrepresión (AS+ $90\text{ min}$), sectorización corta-fuego, iluminación específica de $5\text{ lux}$ sobre BIEs y extintores.
   - **ICT-2**: Infraestructura común de telecomunicaciones (RITI/RITU).

El presente estudio traslada la filosofía de **Sagarde IA** al garaje, estableciendo un catálogo normalizado de tajos, una secuencia de planificación optimizada y un formato de hoja de control para revisión física en obra.

---

## 2. Estructura Matricial de Control (Modelo Garaje)

Para que el motor de seguimiento e informes (`generador_revisiones.html` y `motor_informes.py`) gestione el garaje con la misma eficacia que las viviendas, el espacio se descompone en **Plantas Sótano** y **Unidades Funcionales / Sectores**:

```
GARAJE Y ÁREAS TÉCNICAS
 ├── PLANTAS SÓTANO (S-1, S-2...)
 │    ├── VIALES Y CALLES (Viales de rodadura, maniobra y plazas)
 │    ├── TRASTEROS (Pasillos comunes y baterías de trasteros)
 │    ├── RAMPAS Y ACCESOS (Puertas motorizadas, semáforos, cancelas peatonales)
 │    └── NÚCLEOS VERTICALES (Escaleras E1, E2..., Ascensores, Rellanos/Vestíbulos)
 └── CUARTOS TÉCNICOS (Macro-instalaciones y acometidas)
      ├── Centralización de Contadores y LGA (desde CGP/CPM)
      ├── RITI / RITU (Telecomunicaciones)
      ├── Sala de Calderas / Centrales de Aerotermia
      ├── Fosos y Bombas de Achique / Grupos de Presión
      └── Cuartos de Ventilación, Extracción de Humos y Sobrepresión
```

---

## 3. Catálogo Oficial de Tajos para Garaje (`CAT_GARAJE`)

Se definen los códigos de propiedad (`p`) y ámbito (`a`) acordes al estándar de Sagarde:
- **Propiedad (`p`)**:
  - `p` (**SGD**): Trabajo propio de Sagarde (electricista / instalador).
  - `e` (**EXT**): Obra / gremios externos (estructura, albañilería, conductos de chapa, soleras, pintura).
  - `c` (**COO**): Coordinación directa (climatización, ascensoristas, fontanería, protección contra incendios).
- **Ámbito (`a`)**:
  - `g`: Garaje / Viales y plazas de aparcamiento.
  - `t`: Trasteros.
  - `e`: Escaleras y Rellanos.
  - `q`: Cuartos Técnicos.
  - `r`: Rampas y Accesos.

### Tabla Maestra de Tajos

| ID Tajo | Nombre del Tajo | Grupo / Fase (`g`) | Prop. | Ámb. | Criterio y Descripción Operativa |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `obra-civil` | Desencofrado y soleras | Inicio y Previo | `e` (EXT) | `g` | Forjados libres de puntales y soleras practicables |
| `repl-coord` | Replanteo tridimensional | Inicio y Previo | `c` (COO) | `g` | Coordinación de alturas de bandejas con chapa y bajantes |
| `tabic-ct` | Tabiquería cuartos técnicos | Inicio y Previo | `e` (EXT) | `q` | RITI, Contadores, Calderas y Achique tabicados y raseados |
| `tabic-tras` | Tabicado de trasteros | Inicio y Previo | `e` (EXT) | `t` | Paredes de trasteros levantadas con huecos para tubos |
| `red-tierra` | Red equipotencial y tierras | Infraestructura | `p` (SGD) | `g` | Anillo de tierra, puestas a tierra de bandejas metálicas |
| `cgp-lga` | LGA y canalización CGP | Infraestructura | `p` (SGD) | `q` | Tubo curvable blindado / bandeja desde CGP a Contadores |
| `band-viales` | Bandejas viales principales | Canalización | `p` (SGD) | `g` | Bandeja de rejilla/chapa para fuerza y alumbrado común |
| `band-irve` | Bandeja recarga coche eléctrico | Canalización | `p` (SGD) | `g` | Bandeja exclusiva IRVE según ITC-BT-52 |
| `band-telco` | Bandejas y tubos teleco (RITI) | Canalización | `p` (SGD) | `q` | Conducción principal para cableado de telecomunicaciones |
| `tub-gar-pvc` | Tubeado PVC rígido en viales | Canalización | `p` (SGD) | `g` | Tubo rígido libre de halógenos visto en pilares y techos |
| `tub-trast` | Tubeado pasillos y trasteros | Canalización | `p` (SGD) | `t` | Distribución por pasillos y entradas a cada trastero |
| `tub-escal` | Rozas/tubeado escaleras/rellanos | Canalización | `p` (SGD) | `e` | Conducciones a apliques, downlights y detectores |
| `cabl-luz-gar` | Cableado alumbrado garaje | Cableado | `p` (SGD) | `g` | Circuitos independientes de luz permanente y temporizada |
| `cabl-emg-gar` | Cableado emergencias garaje | Cableado | `p` (SGD) | `g` | Líneas de alumbrado de seguridad y señalización |
| `cabl-emg-bie` | Cableado emergencias BIEs/PCI | Cableado | `p` (SGD) | `g` | Líneas a puntos de luz de 5 lux sobre BIEs y extintores |
| `cabl-trast` | Cableado trasteros | Cableado | `p` (SGD) | `t` | Líneas de pasillo y circuitos interiores de trasteros |
| `cabl-escal` | Cableado escaleras y rellanos | Cableado | `p` (SGD) | `e` | Alimentación de apliques, downlights y detectores |
| `cabl-fza-ct` | Cableado fuerza cuartos técnicos | Cableado | `p` (SGD) | `q` | Acometidas a bombas de achique, ventilación y RITI |
| `cabl-fza-asc` | Acometidas fuerza ascensores | Cableado | `p` (SGD) | `q` | Cuadro de maniobra de ascensor vivienda y garaje |
| `cabl-rampas` | Cableado rampa y cancelas | Cableado | `p` (SGD) | `r` | Fuerza a puertas automáticas, lazos magnéticos y semáforos |
| `ct-contad` | Centralización de contadores | Cuartos Técnicos | `p` (SGD) | `q` | Módulos, embarrado, derivaciones y barra de tierras |
| `ct-riti` | Equipamiento RITI / RITU | Cuartos Técnicos | `p` (SGD) | `q` | Cuadro estanco, bases schuko de rack y pletina de tierra |
| `ct-achique` | Cuadro y acometida achique | Cuartos Técnicos | `p` (SGD) | `q` | Cuadro de bombas con alternancia, 3 boyas y alarma |
| `ct-caldera` | Cuadro sala calderas/aerotermia | Cuartos Técnicos | `c` (COO) | `q` | Fuerza a bombas de calor, recirculadoras e interbloqueos |
| `ct-vent-sob` | Cuadro ventilación/sobrepresión | Cuartos Técnicos | `p` (SGD) | `q` | Cuadros conmutados (CO/humos) con cables AS+ |
| `cgg-mont` | Montaje Cuadro General Garaje | Cuadros Eléctricos| `p` (SGD) | `g` | Fijación física de envolvente CGG y peinado inicial |
| `cgg-mec` | Mecanizado e interconexión CGG | Cuadros Eléctricos| `p` (SGD) | `g` | Diferenciales superinmunizados, térmicos, relojes |
| `pci-central` | Centralita e interconexión PCI | Sistemas Segur. | `p` (SGD) | `g` | Detectores ópticos, pulsadores, sirenas y compuertas |
| `co-central` | Centralita y sensores de CO/NO2 | Sistemas Segur. | `p` (SGD) | `g` | Sensores de CO por calles y maniobra de ventilación |
| `inst-pant-g` | Colocación pantallas garaje | Montaje Equipos | `p` (SGD) | `g` | Montaje de pantallas estancas LED (IP65, IK08) |
| `inst-emg-g` | Colocación emergencias garaje | Montaje Equipos | `p` (SGD) | `g` | Luminarias de emergencia en rutas, salidas y BIEs |
| `inst-luz-t` | Mecanismos y luz de trasteros | Montaje Equipos | `p` (SGD) | `t` | Pantallas de pasillo, interruptores y puntos de luz |
| `inst-apliq` | Apliques LED de escalera | Montaje Equipos | `p` (SGD) | `e` | Apliques murales LED en descansillos de escalera |
| `inst-downl` | Downlights de rellanos | Montaje Equipos | `p` (SGD) | `e` | Downlights en vestíbulos y rellanos de comunicación |
| `inst-detec` | Detectores presencia escal/rell | Montaje Equipos | `p` (SGD) | `e` | Regulación de temporización, sensibilidad y crepuscular |
| `puert-auto` | Elementos de rampa y puerta | Montaje Equipos | `c` (COO) | `r` | Conexión de motor, fotocélulas, lazo y semáforos |
| `rotul-peg` | Rotulación, tapas y esquemas | Cierre y Remates| `p` (SGD) | `g` | Cajas estancas tapadas, pegatinas y unifilar en cuadro |
| `pruebas-cie` | Pruebas funcionales, REBT y CIE | Puesta en Marcha| `p` (SGD) | `g` | Ensayos de aislamiento, corte de emergencias y OCA |

---

## 4. Planning Operativo por Fases de Ejecución

```mermaid
flowchart TD
    subgraph F0["FASE 0: Replanteo y Obra Previa"]
        A1["Estructura desencofrada y solera"] --> A2["Replanteo tridimensional: Cruce bandejas vs ventilación"]
        A2 --> A3["Tabiquería y raseado de Cuartos Técnicos"]
        A2 --> A4["Tabicado perimetral de Trasteros"]
    end

    subgraph F1["FASE 1: Infraestructuras Principales"]
        B1["Puesta a tierra de garaje y bandejas metálicas"]
        B2["Canalización de LGA desde CGP a Contadores"]
        B3["Tendido de Bandeja General de Viales"]
        B4["Tendido de Bandeja Exclusiva Coche Eléctrico (IRVE)"]
        B5["Tendido de Bandeja de Telecomunicaciones"]
        B6["Tubo de PVC rígido visto en techos y pilares"]
    end

    subgraph F2["FASE 2: Núcleos Verticales y Rellanos"]
        C1["Rozas y tubos en escaleras y rellanos"]
        C2["Cableado de apliques y downlights"]
        C3["Cableado de emergencias y detectores de presencia"]
    end

    subgraph F3["FASE 3: Cuartos Técnicos e Instalaciones Especiales"]
        D1["Montaje de módulos y embarrado en Centralización"]
        D2["Equipamiento RITI: Cuadro, enchufes y pletina tierra"]
        D3["Bombas de achique: Cuadro con alternancia y boyas"]
        D4["Ventilación y Sobrepresión: Conducciones y cable AS+"]
        D5["Fuerza Climatización / Sala de Calderas / Aerotermia"]
        D6["Acometidas a cuadros de maniobra de Ascensores"]
    end

    subgraph F4["FASE 4: Cableado General y Seguridad"]
        E1["Cableado de alumbrado de garaje (fijo y temporizado)"]
        E2["Cableado de emergencias generales y BIEs (5 lux)"]
        E3["Cableado de pasillos y módulos de trasteros"]
        E4["Lazo de Detección de Incendios (PCI) y sirenas"]
        E5["Cableado de sensores y centralita de CO/NO2"]
    end

    subgraph F5["FASE 5: Montaje de Equipos y Mecanizado"]
        F1["Mecanizado y peinado de Cuadro General Garaje (CGG)"]
        F2["Fijación y conexión de pantallas LED estancas (IP65)"]
        F3["Instalación de luminarias de emergencia"]
        F4["Montaje de apliques en escaleras y downlights en rellanos"]
        F5["Mecanismos estancos y puntos de luz en trasteros"]
        F6["Conexión de puertas motorizadas, lazo y semáforos"]
    end

    subgraph F6["FASE 6: Pruebas, Legalización y Entrega"]
        G1["Pruebas de disparo diferencial y aislamiento REBT"]
        G2["Prueba funcional: CO -> Ventilación 1ª marcha"]
        G3["Prueba funcional: PCI -> Extracción humos 2ª marcha y compuertas"]
        G4["Prueba de autonomía y luminancia de emergencias"]
        G5["Rotulación normalizada, unifilares y tapas de cajas"]
        G6["Emisión de CIE y acompañamiento a Inspección OCA"]
    end

    F0 --> F1
    F1 --> F2
    F1 --> F3
    F1 --> F4
    F2 --> F5
    F3 --> F5
    F4 --> F5
    F5 --> F6
```

---

## 5. Especificaciones Técnicas y Criterios de Ejecución

### 5.1. Cuartos Técnicos y Equipos Pesados
1. **LGA y Centralización de Contadores**:
   - Conducción desde CGP/CPM exterior mediante tubo curvable en frío blindado o canal protectora cerrada (ITC-BT-14).
   - Embarrado general, bases de fusibles BTVC seccionables en carga, barra colectora de cobre para puesta a tierra y salidas hacia derivaciones individuales con tubo libre de halógenos.
2. **RITI / RITU (Telecomunicaciones)**:
   - Cuadro estanco independiente alimentado desde servicios comunes.
   - Pletina de tierra exclusiva conectada a la barra principal de tierra del edificio.
   - Bases de enchufe múltiples con toma de tierra para bastidores de telecomunicaciones (racks).
3. **Bombas de Achique / Fosos de Drenaje**:
   - Cuadro de maniobra con guardamotores y relés de alternancia automática entre 2 bombas.
   - Maniobra gobernada por 3 boyas de nivel: parada mínima, arranque 1ª bomba, refuerzo 2ª bomba y boya de alarma superior conectada a señalización óptica/acústica.
4. **Sala de Calderas / Centrales de Aerotermia**:
   - Alimentación trifásica para bombas de calor y recirculadoras.
   - Enclavamiento de seguridad con corte por seta de emergencia exterior y termostatos de seguridad.
5. **Ascensores**:
   - Diferenciación clara entre ascensores con acceso a viviendas y ascensores de uso exclusivo garaje.
   - Acometida en foso con enchufe estanco, conmutador de alumbrado de foso y seta de emergencia en foso.

### 5.2. Ventilación de Garaje y Sobrepresión
- **Extracción de humos y CO**:
  - Cuadro eléctrico con selector Manual/Automático y contactores para 2 velocidades:
    - **1ª Velocidad (Baja)**: Activada por la centralita de CO al superar los umbrales de concentración ($50\text{ ppm}$ o $100\text{ ppm}$).
    - **2ª Velocidad (Alta)**: Activada por la central de detección de incendios (PCI) para evacuación de humos ($400^\circ\text{C}/2\text{h}$).
  - Conductor resistente al fuego categoría **AS+** (norma UNE-EN 50200) sin empalmes en el interior del sector de incendio.
- **Sobrepresión de escaleras y vestíbulos**:
  - Motores de sobrepresión con compuertas de alivio alimentados con cable AS+ para mantener sobrepresión positiva ($\ge 50\text{ Pa}$) y evitar la entrada de humo a las vías de evacuación.

### 5.3. Escaleras y Rellanos
- **Escaleras**:
  - Iluminación mediante apliques murales LED antivandálicos en cada meseta y descansillo.
  - Alumbrado de emergencia en cada rellano, sobre puertas de salida y en cada tramo de escaleras ($\ge 1\text{ lux}$ a nivel de suelo según CTE DB-SUA 4).
  - Encendido temporizado con detectores de presencia infrarrojos/microondas regulados para cobertura anticipada.
- **Rellanos / Vestíbulos previos**:
  - Downlights LED empotrados o en superficie según la existencia de falso techo acústico/fuego.
  - Alumbrado de emergencia sobre la puerta corta-fuegos de acceso al garaje y sobre el acceso al ascensor.

### 5.4. Alumbrado General, Viales y Trasteros
- **Alumbrado fijo vs. temporizado en garaje**:
  - **Circuito permanente (fijo)**: $15\% - 25\%$ de las luminarias conectadas a una línea directa no temporizada para garantizar un nivel mínimo de luz de vigilancia continua en accesos, cruces y viales principales (ITC-BT-28).
  - **Circuito temporizado**: Resto de luminarias gobernadas por detectores de movimiento volumétricos o pulsadores con piloto testigo luminoso.
  - Luminarias: pantallas estancas LED de $1.200\text{ mm}$ o $1.500\text{ mm}$, IP65, difusor de policarbonato IK08.
- **Trasteros**:
  - Pasillo de distribución: pantallas estancas gobernadas por detectores de presencia o pulsadores temporizados.
  - Interior de trasteros: punto de luz estanco con interruptor de superficie junto a la puerta, alimentado desde un circuito independiente en el CGG.

### 5.5. Centralitas de CO/NO2, Detección de Incendios y BIEs
- **Centralita de CO / NO2**:
  - Detectores colocados a una altura entre $1{,}50\text{ m}$ y $1{,}80\text{ m}$ sobre el suelo terminado (zona de respiración).
  - Distribución de un sensor cada $200 - 300\text{ m}^2$ según normativa local y UNE 23300.
- **Protección Contra Incendios (PCI)**:
  - Detectores ópticos de humos en techos de viales, plazas y trasteros.
  - Pulsadores manuales junto a cada salida de evacuación.
  - Sirenas óptico-acústicas con flash visible.
- **Alumbrado de emergencia sobre BIEs y extintores**:
  - Luminaria de emergencia situada a menos de $2\text{ m}$ de distancia de cada BIE, de cada extintor y de cada cuadro eléctrico, garantizando un mínimo de **$5\text{ lux}$** en el plano vertical del equipo (RIPCI y CTE DB-SI).

### 5.6. Canalizaciones, Recarga de Vehículo Eléctrico (IRVE) y Telecomunicaciones
- **Tubo de PVC rígido visto**:
  - Tubo curvable en frío, libre de halógenos, no propagador de la llama, con resistencia al impacto pesada (grado 4, IK08). Montaje grapado cada $50\text{ cm}$.
- **Bandeja de Recarga de Coche Eléctrico (ITC-BT-52)**:
  - Bandeja metálica de rejilla o chapa perforada de gran capacidad (mínimo $150 - 200\text{ mm}$ de ancho) reservada en exclusiva para las futuras derivaciones de recarga desde la centralización de contadores hasta las plazas.
- **Bandeja de Telecomunicaciones**:
  - Separación mínima de $20 - 30\text{ cm}$ en paralelo respecto a bandejas de fuerza para evitar perturbaciones electromagnéticas.

---

## 6. Modelo de Hoja de Revisión en Campo (Plantilla A4 Sagarde)

Para su impresión y marcado a pie de obra con la simbología estándar de Sagarde ($X = 100\%$, $M = >50\%$, $/ = <50\%$, $\text{en blanco} = 0\%$, $--- = \text{No Aplica}$):

```
+-------------------------------------------------------------------------------------------------------------------------+
| SAGARDE — HOJA DE CONTROL DE AVANCE DE INSTALACIÓN ELÉCTRICA: GARAJE Y SERVICIOS                                       |
| Obra: [NOMBRE DE OBRA]    | Sótano: S-1 / S-2    | Fecha: DD/MM/AAAA    | Revisión Nº: [ ]                              |
+=========================================================================================================================+
|                                         | VIALES Y CALLES |      TRASTEROS      | NÚCLEOS ESCALERA |   CUARTOS TÉCNICOS |
| FASE / TAJO                             | Zona A | Zona B | Pasillo | Mód. Trast| Esc. 1 | Esc. 2  | RITI | Cont | Bom |
+-----------------------------------------+--------+--------+---------+-----------+--------+---------+------+------+-----+
| 1. INFRAESTRUCTURA Y CANALIZACIÓN       |        |        |         |           |        |         |      |      |     |
|   [SGD] Red equipotencial y tierras     |   [ ]  |   [ ]  |   [ ]   |    [ ]    |   [ ]  |   [ ]   |  [ ] |  [ ] | [ ] |
|   [SGD] LGA y canalización desde CGP    |   [ ]  |   [ ]  |   ---   |    ---    |   ---  |   ---   |  --- |  [ ] | --- |
|   [SGD] Bandejas viales principales     |   [ ]  |   [ ]  |   ---   |    ---    |   ---  |   ---   |  --- |  --- | --- |
|   [SGD] Bandeja exclusiva IRVE          |   [ ]  |   [ ]  |   ---   |    ---    |   ---  |   ---   |  --- |  --- | --- |
|   [SGD] Tubeado PVC visto en techos/pil.|   [ ]  |   [ ]  |   [ ]   |    [ ]    |   ---  |   ---   |  [ ] |  [ ] | [ ] |
|   [SGD] Tubeado escaleras y rellanos    |   ---  |   ---  |   ---   |    ---    |   [ ]  |   [ ]   |  --- |  --- | --- |
+-----------------------------------------+--------+--------+---------+-----------+--------+---------+------+------+-----+
| 2. CABLEADO DE FUERZA Y ALUMBRADO       |        |        |         |           |        |         |      |      |     |
|   [SGD] Cableado alumbrado fijo garaje  |   [ ]  |   [ ]  |   ---   |    ---    |   ---  |   ---   |  --- |  --- | --- |
|   [SGD] Cableado alumbrado temporizado  |   [ ]  |   [ ]  |   [ ]   |    [ ]    |   ---  |   ---   |  --- |  --- | --- |
|   [SGD] Cableado emergencias y BIEs     |   [ ]  |   [ ]  |   [ ]   |    ---    |   [ ]  |   [ ]   |  [ ] |  [ ] | [ ] |
|   [SGD] Cableado apliques y downlights  |   ---  |   ---  |   ---   |    ---    |   [ ]  |   [ ]   |  --- |  --- | --- |
|   [SGD] Acometidas bombas y ventilación |   ---  |   ---  |   ---   |    ---    |   ---  |   ---   |  --- |  --- | [ ] |
+-----------------------------------------+--------+--------+---------+-----------+--------+---------+------+------+-----+
| 3. CUARTOS TÉCNICOS Y SISTEMAS          |        |        |         |           |        |         |      |      |     |
|   [SGD] Módulos y embarrado contadores  |   ---  |   ---  |   ---   |    ---    |   ---  |   ---   |  --- |  [ ] | --- |
|   [SGD] Cuadro RITI y red de tierra     |   ---  |   ---  |   ---   |    ---    |   ---  |   ---   |  [ ] |  --- | --- |
|   [SGD] Cuadro bombas achique y boyas   |   ---  |   ---  |   ---   |    ---    |   ---  |   ---   |  --- |  --- | [ ] |
|   [SGD] Cuadro ventilación/sobrepresión |   [ ]  |   [ ]  |   ---   |    ---    |   ---  |   ---   |  --- |  --- | [ ] |
|   [SGD] Centralita y sensores CO/NO2    |   [ ]  |   [ ]  |   ---   |    ---    |   ---  |   ---   |  --- |  --- | --- |
|   [SGD] Detección de incendios y sirenas|   [ ]  |   [ ]  |   [ ]   |    ---    |   [ ]  |   [ ]   |  [ ] |  [ ] | [ ] |
+-----------------------------------------+--------+--------+---------+-----------+--------+---------+------+------+-----+
| 4. MONTAJE DE APARATOS Y MECANIZADO     |        |        |         |           |        |         |      |      |     |
|   [SGD] Pantallas LED estancas viales   |   [ ]  |   [ ]  |   ---   |    ---    |   ---  |   ---   |  --- |  --- | --- |
|   [SGD] Emergencias garaje y BIEs       |   [ ]  |   [ ]  |   [ ]   |    ---    |   [ ]  |   [ ]   |  [ ] |  [ ] | [ ] |
|   [SGD] Apliques murales escaleras      |   ---  |   ---  |   ---   |    ---    |   [ ]  |   [ ]   |  --- |  --- | --- |
|   [SGD] Downlights en rellanos          |   ---  |   ---  |   ---   |    ---    |   [ ]  |   [ ]   |  --- |  --- | --- |
|   [SGD] Detectores presencia escal/rell |   ---  |   ---  |   ---   |    ---    |   [ ]  |   [ ]   |  --- |  --- | --- |
|   [SGD] Mecanismos y luz de trasteros   |   ---  |   ---  |   [ ]   |    [ ]    |   ---  |   ---   |  --- |  --- | --- |
|   [SGD] Cuadro General Garaje (CGG) mec.|   [ ]  |   ---  |   ---   |    ---    |   ---  |   ---   |  --- |  --- | --- |
+-----------------------------------------+--------+--------+---------+-----------+--------+---------+------+------+-----+
| 5. REMATES Y LEGALIZACIÓN               |        |        |         |           |        |         |      |      |     |
|   [SGD] Rotulación, tapas y esquemas    |   [ ]  |   [ ]  |   [ ]   |    [ ]    |   [ ]  |   [ ]   |  [ ] |  [ ] | [ ] |
|   [SGD] Pruebas disparo y aislamiento   |   [ ]  |   [ ]  |   [ ]   |    [ ]    |   [ ]  |   [ ]   |  [ ] |  [ ] | [ ] |
|   [SGD] Certificado CIE y paso de OCA   |   [ ]  |   [ ]  |   [ ]   |    [ ]    |   [ ]  |   [ ]   |  [ ] |  [ ] | [ ] |
+-------------------------------------------------------------------------------------------------------------------------+
| Leyenda: [X] Terminado 100% | [M] Avanzado >50% (75%) | [/] En curso <50% (25%) | [ ] Pendiente | [---] No Aplica       |
+-------------------------------------------------------------------------------------------------------------------------+
```

---

## 7. Plan de Implementación en la Suite de Software Sagarde

1. **Ampliación de `generador_revisiones.html`**:
   - Incorporar un interruptor modal de tipo de informe: **"Viviendas"** o **"Garaje / Áreas Comunes"**.
   - En modo garaje, sustituir la matriz de letras de vivienda por la definición de zonas (`Viales Zona A`, `Viales Zona B`, `Pasillo Trasteros`, `Módulos Trasteros`, `Escalera 1`, `Escalera 2`, `RITI`, `Contadores`, `Bombas/Calderas`).
   - Cargar dinámicamente el catálogo `CAT_GARAJE` filtrando los rótulos correspondientes.
2. **Compatibilidad con `adaptadores` y `motor_informes.py`**:
   - El esquema de salida del adaptador mantendrá la estructura esperada:
     ```python
     {
         'task': 'band-irve',
         'floor': 'S-1',
         'building': 'Garaje General',
         'unit': 'Viales Zona A',
         'status': 'X'  # 'X' | 'M' | '/' | ''
     }
     ```
   - Esto permite que el motor calcule de forma inmediata el `%` de avance estricto, `%` estimado, evolución temporal y detección de bloqueos en cuartos técnicos o viales sin modificar la lógica analítica de Sagarde IA.
