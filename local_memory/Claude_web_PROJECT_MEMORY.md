# Memoria de proyecto: Detección de cambios en manuales técnicos de Visa (BASE I, BASE II, VSS)

> Este documento es un resumen de contexto para retomar el proyecto con Claude Code.
> No contiene código todavía — es el resultado de una sesión de análisis/diseño previa.
> Fecha de la sesión: 2026-08-10.

---

## 1. Objetivo del proyecto

Construir un sistema que compare **dos versiones consecutivas de un manual técnico de Visa (PDF)**
y detecte automáticamente qué cambió entre ellas, para que un Data Engineer sepa si necesita
actualizar la configuración de la plataforma de procesamiento de transacciones.

### Caso de uso motivador (el que dispara todo el diseño)

Un manual describe el layout de un registro de transacción. En la versión N, un campo dice:

```
151-168  18  AN  Reserved
```

En la versión N+1, ese mismo rango de bytes pasa a estar parcialmente definido:

```
151-160  10  AN  Reserved
161-168  8   AN  Merchant Category Code Extension
```

Es decir: un campo que antes era "reservado" (sin uso) ahora tiene una definición de negocio real.
Este tipo de cambio —silencioso, fácil de pasar por alto en una revisión manual de cientos de
páginas— es exactamente lo que el sistema debe detectar y reportar. También aplica al revés
(un campo definido que pasa a reservado), a cambios de longitud/formato, a cambios de
descripción/valores válidos sin tocar el layout, etc.

### Diferencia con el dominio de "Guías de Interchange" (proyecto hermano ya existente)

Otro equipo ya construyó una POC para un problema similar pero de **otro tipo de documento**:
las Guías de Interchange (reglas de tarifas que deben cumplir las transacciones para que se les
asigne determinada tarifa). Compartieron 3 scripts de esa POC como referencia de arquitectura
(ver sección 3). Es importante no confundir los dos dominios:

| | Guías de Interchange (POC existente) | Manuales técnicos (este proyecto) |
|---|---|---|
| Unidad central | Programa → Fee Descriptor → Criteria (texto) → Rate | TC (Transaction Code) → TCR (Component Record) → Campo |
| Qué cambia | Tarifa, texto de condición/criterio, MCCs/países/productos en tablas referenciadas | Definición de campo, posición, longitud, formato, valores válidos |
| Matching entre versiones | Por nombre (exacto o fuzzy) de programa/descriptor | Debe ser por **posición de bytes** primero, nombre como fallback (ver sección 4) |
| Ejemplo de cambio típico | Cambia el % de interchange de un programa, o cambia el rango de MCC excluido | Un campo "Reserved" se convierte en un campo con nombre y definición de negocio |

---

## 2. Inventario de archivos disponibles en el proyecto

### Manuales técnicos (PDFs), organizados en `visa/src/{base_i, base_ii, vss}/<nombre_manual>/<fecha>_-_<titulo>.pdf`

La fecha en el nombre del archivo es la versión de la edición del manual.

**base_i**
- `international_full_service_pos_online_messages_processing_specifications` — 7 versiones (2023-04-15 → 2026-04-20)

**base_ii**
- `base_ii_clearing_data_codes` — 9 versiones (2022-04-23 → 2026-04-18)
- `base_ii_clearing_edit_package_messages` (Reference Guide, Release 4) — 9 versiones
- `base_ii_clearing_interchange_formats_tc_01_to_tc_49` — 9 versiones
- `base_ii_clearing_interchange_formats_tc_50_to_tc_92` — 9 versiones
- `base_ii_transactions_quick_reference` — 8 versiones

**vss** (VisaNet Settlement Service — liquidación)
- `visanet_settlement_service_vss_user_guide_volume_1_specifications` — 6 versiones
- `visanet_settlement_service_vss_user_guide_volume_2_reports` — 7 versiones

En total, ~7 familias de manuales, cada una con entre 6 y 9 ediciones históricas disponibles para
probar el diff entre versiones consecutivas.

### Scripts de referencia (POC de Guías de Interchange, NO de este proyecto)

Solo se compartieron 3 de las ~7 etapas del pipeline original. **Faltan las etapas 1, 3 y 4**
(no existen o no se compartieron todavía — confirmado por el usuario).

- `02_guide_parser.py` — Etapa 2: Normalización de bloques
- `05_diff_descriptors.py` — Etapa 5: Detección de cambios
- `06_classify_changes.py` — Etapa 6: Interpretación de cambios con IA

Detalle de cada uno en la sección 3.

### Diagrama de proceso esperado (compartido como imagen, `diagramapng.png`)

7 pasos:
1. **Ingesta y Parseo**: extraer todo el texto de ambos manuales (procesado y nuevo)
2. **Normalización de bloques**: preparar la información en bloques estandarizados
3. **Emparejamiento de bloques**: relacionar los bloques equivalentes entre versiones
4. **Detección de cambios**: identificar diferencias (nuevos, modificados, eliminados, sin cambios)
5. **Interpretación de cambios (IA)**: el motor interpreta el impacto y tipo de cambio detectado
6. **Validación con Plataforma STD**: compara los cambios detectados con la configuración actual
   de la plataforma
7. **Reporte de cambios**: consolida todos los cambios encontrados, tipo y relación con la
   plataforma actual

Nota del diagrama (importante, citada del brief original): *"El reporte de cambios contendrá
todos los tipos de cambios que se encontraron en la nueva versión del manual, incluso aquellos
que probablemente no afecten al procesamiento de la información. Es por ello que se compara con
las configuraciones que se tienen en la plataforma actual. De esta manera, es responsabilidad de
los DE's identificar si alguno de nuestros procesos sería afectado y dar la opción de evaluar si
alguno de los cambios no son configuraciones que utilicemos en la plataforma para los procesos
cotidianos o si son necesarias las configuraciones."*

Responsabilidad del Data Engineer (según el diagrama): revisar el reporte, evaluar el impacto
real en procesos/reportes propios, decidir qué cambios requieren configuración en la plataforma,
implementar las configuraciones necesarias si aplica.

---

## 3. Arquitectura de referencia (POC de Guías de Interchange) — resumen técnico

### `02_guide_parser.py` — Normalización de bloques

- **Input**: `data/output/raw_{old|new}_guide{_suffix}.json` — lista de bloques físicos con
  `block_id`, `source_file`, `page`, `type` (`"text"` o `"table"`), `text`, `bbox` (con clave `t`
  para posición vertical). Esto viene de una etapa 1 (extracción, no compartida) que aparentemente
  usa un extractor tipo Docling.
- **Output**: `data/output/structured_{old|new}_guide{_suffix}.json`.
- **Lógica clave**:
  - Ordena bloques por `(page, -bbox.t)` (orden de lectura top-to-bottom por página).
  - `is_noise(text)`: filtra "Visa Confidential", "Contents", números de página (árabes y
    romanos), notice de propiedad intelectual, footers de "Mes Año".
  - `detect_section(text)`: regex `^(\d+(?:\.\d+)*)\s+(.+)$` para detectar encabezados
    numerados tipo `1.2.3 Título`.
  - `is_valid_section_transition(candidate, current)`: valida que un encabezado numerado
    detectado sea una transición plausible en la jerarquía (mismo nivel +1, hijo directo,
    hermano, o hermano de un ancestro) — esto es clave para **rechazar falsos positivos**
    como notas al pie numeradas que parecen encabezados pero no lo son.
  - Mantiene un `section_stack: Dict[nivel, label]` para reconstruir `section_path`
    (breadcrumb completo) en cada bloque.
  - `detect_table_caption(text)`: regex `^(Table\s+\d+[-–]\d+):?\s*(.+)$` — detecta captions
    tipo "Table 4-8: Título" que preceden a una tabla, y los guarda como "pending" para
    adjuntarlos al próximo bloque `type == "table"`.
  - `classify_block_role(...)`: asigna rol a cada bloque: `section_heading`, `paragraph`,
    `business_table`, `navigation`, `local_heading`, `unknown`.
  - `_merge_table_continuations(...)`: fusiona tablas partidas entre páginas consecutivas
    (función truncada en el archivo compartido, pero el nombre indica que reconoce cuando
    una tabla continúa en la página siguiente, probablemente por mismo `table_id`/ausencia
    de nuevo caption + misma estructura de columnas).
  - CLI: `--jurisdiction` (ej. Interregional, Europe, Romania) — procesa `old` y `new` en el
    mismo run.

### `05_diff_descriptors.py` — Detección de cambios

- **Input**: `matched_descriptors.json` (de una etapa 3-4 no compartida) +
  `structured_{old|new}_guide{_suffix}.json`.
- **Output**: `diff_results.json` con 8 categorías: `rate_changes`, `criteria_changes`,
  `program_renames`, `descriptor_renames`, `added_descriptors`, `removed_descriptors`,
  `added_programs`, `removed_programs`.
- **Lógica clave**:
  - `build_table_index(structured_guide)`: indexa todas las tablas del documento por
    `table_id` (ej. "Table 4-8") → texto completo (con título). Esto permite luego
    **resolver referencias cruzadas**: si un texto de criterio dice "ver Table 4-8", se
    puede ir a buscar el contenido real de esa tabla en ambas versiones.
  - `diff_rates(...)`: compara campos de tarifa (`fee_rate_raw`) normalizados
    (whitespace, lowercase) — simple comparación de igualdad, no fuzzy.
  - `diff_criteria(...)`: empareja bloques de criterio por `table_title` (¡ojo! empareja
    por título de tabla, no por posición ni ID — esto es específico del dominio de Guías,
    donde el título es estable entre versiones). Si el texto normalizado es idéntico, no
    hay cambio. Si difiere, calcula `fuzzy_ratio` con `SequenceMatcher`; si el ratio cae
    debajo de `CRITERIA_CHANGE_THRESHOLD = 0.98`, se marca como cambio real.
  - `enrich_criteria_change(...)`: para cada cambio de criterio, extrae las referencias
    `Table X-Y` mencionadas en el texto (viejo y nuevo), resuelve su contenido real en
    ambas versiones, y arma un diff de "tablas referenciadas" — esto es lo que después
    se le pasa al LLM en la etapa 6 para que compare **valores reales** (MCCs, países,
    productos) en vez de solo comparar el número de referencia a la tabla.
  - `normalize_criteria_text(...)`: quita boilerplate específico de Visa (nombre del
    documento, "Visa Confidential", copyright, etc.) antes de comparar.

### `06_classify_changes.py` — Interpretación de cambios con IA

- **Input**: `diff_results.json`. Solo clasifica los `criteria_changes` cuyo
  `change_type == "criteria_changed"` (los `added`/`removed` ya son deterministas y no
  necesitan IA — pasan directo con `confidence: high`).
- **Output**: `classified_changes.json`.
- **Motor**: Ollama local (`http://localhost:11434/api/chat`), modelo por defecto
  `qwen3:4b`. Usa `format` con JSON Schema estricto para forzar salida estructurada,
  `temperature: 0.0`, `seed: 42` para reproducibilidad.
- **Labels de clasificación**:
  - `criteria_real_change` — condición realmente cambió (MCCs, productos, países,
    umbrales, elegibilidad). Requiere actualizar el Excel de reglas de negocio.
  - `criteria_clarification` — misma condición, se agregó nota/contexto/valor por
    defecto. Puede requerir nota en columna `OTHER_CRITERIA_APPLIES`.
  - `criteria_reword` — mismo significado, distinta redacción. Caso especial: una
    renumeración de tabla referenciada (Table 5-8 → Table 5-10) es `criteria_reword`
    **solo si** el contenido de la tabla es idéntico; si el contenido cambió, es
    `criteria_real_change`.
  - `extraction_noise` — diferencia causada por artefactos de extracción (Docling), no
    por un cambio real de Visa.
- **Prompt**: incluye texto viejo/nuevo (truncado a 1200 chars) + contenido resuelto de
  tablas referenciadas (marcado explícitamente como "UNCHANGED" o "CHANGED" entre
  versiones) + el JSON Schema esperado.
- **Safety net determinístico** (`detect_disappeared_content`): si el LLM dice
  `extraction_noise` con confianza `high`, igual se corre una heurística de respaldo que
  compara líneas significativas (≥25 chars) entre texto viejo y nuevo por solapamiento de
  palabras clave (≥60%). Si detecta que hubo contenido que "desapareció" sin equivalente
  en el otro texto, **degrada la confianza a `low`** y anota
  `"[auto-flagged: content disappeared]"` — para no confiar ciegamente en el LLM cuando
  dice que no pasó nada.

---

## 4. Diseño propuesto para ESTE proyecto (manuales técnicos)

> Esto es una propuesta de diseño discutida en la sesión, todavía no implementada.
> Sirve como punto de partida, no como decisión final — debe validarse con los PDFs reales.

### 4.1 Jerarquía / modelo de datos

En vez de `Programa → Fee Descriptor → Criteria → Rate`, usar:

```
Manual (ej. "BASE II Clearing Interchange Formats, TC 01 to TC 49", versión = fecha)
 └── Transaction Code / sección funcional
      (ej. "TC 33.A Capture Transactions (Acquirer)")
 └── Component Record / grupo de campos
      (ej. "TCR 0", "TCR 1", "CP 02 TCR 0 EMV Data")
      └── Campo
           ├── position_range      (ej. "151-168", o inicio/fin numéricos separados)
           ├── length              (ej. 18)
           ├── format              (AN, N, UN, ANS, DX — ver leyenda de formatos abajo)
           ├── name                (ej. "Reserved" / "Merchant Category Code Extension")
           ├── description         (texto libre bajo "Description:")
           ├── valid_values        (si existen, bajo "Values:" o "Valid values:")
           └── notes / mapping     (si existen, bajo "Note:")
```

Nota sobre formatos vistos en los PDFs: `AN` = Alphanumeric, `ANS` = Alphanumeric Special,
`DX` = Display Hexadecimal, `N` = Numeric, `UN` = Unpacked Numeric. Esta leyenda aparece
explícita al pie de las tablas de Record Layout — conviene parsearla también porque puede
variar de manual a manual.

### 4.2 Dos tipos de contenido con distinto patrón de extracción (evidencia real, ver sección 5)

1. **Tablas resumen "Record Layout"** (grilla real: `Position | Field | Length | Format |
   Contents`) — una fila por campo, compacta. Es la fuente de verdad estructural: acá se
   detectan altas/bajas/cambios de longitud/formato/posición.
2. **Fichas de campo individuales** (texto corrido, NO tabla PDF real, patrón repetido
   `Nombre de campo` → `Positions:` → `Length:` → `Format:` → `Description:` → opcional
   `Values:` / `Note:`) — esta es la fuente de la descripción de negocio, valores válidos,
   mapeos a otros sistemas (ej. "Mapping: Field 104 DS66 T0D => AMEX DF60").

Ambas se refieren al mismo campo lógico y deberían enlazarse (por nombre + rango de
posición) al construir el bloque final.

### 4.3 Categorías de cambio propuestas para la etapa 5 (diff), análogas a las de Guías

- `field_added` — antes era `Reserved` (o no existía), ahora tiene nombre/definición.
- `field_removed` — antes tenía definición, ahora es `Reserved` (o desapareció).
- `field_redefined` — mismo rango de posición, cambia el nombre/significado del campo.
- `field_resized` — cambia `length`, lo cual puede correr las posiciones de todos los
  campos siguientes dentro del mismo TCR (¡esto es un caso especialmente delicado para el
  matching por posición, ver 4.4!).
- `field_position_shifted` — mismo campo (mismo nombre), pero su rango de posición cambió
  (consecuencia típica de un `field_resized` en un campo anterior).
- `field_format_changed` — cambia `AN` → `N`, etc., sin cambiar posición/longitud.
- `field_description_changed` / `field_values_changed` — cambia la descripción de negocio
  o la lista de valores válidos, sin tocar el layout físico.
- Categorías estructurales de nivel superior, análogas a `added_programs`/`removed_programs`:
  `tc_added`, `tc_removed`, `tcr_added`, `tcr_removed`.

### 4.4 Estrategia de matching entre versiones (etapa 3-4, a diseñar)

Diferencia clave frente al proyecto de Guías: ahí emparejan por **nombre** (exacto o
fuzzy). Acá se propone invertir la prioridad:

1. **Matching primario por posición**: dentro del mismo TC + TCR/grupo, comparar rangos de
   bytes que se solapan entre versión vieja y nueva. Esto captura el caso central del
   proyecto (un campo Reserved que se subdivide y una parte se define).
2. **Matching secundario por nombre** (fuzzy, tipo `SequenceMatcher` como ya usa
   `05_diff_descriptors.py`): para detectar renombres cuando la posición se mantiene
   igual pero el nombre cambió sutilmente.
3. **Caso difícil a resolver en diseño**: cuando un campo cambia de longitud, todos los
   campos posteriores dentro del mismo TCR corren de posición aunque no hayan cambiado en
   sí mismos. Hay que decidir si el matching por posición usa rangos absolutos (byte X-Y)
   o si conviene usar **posición ordinal dentro del TCR** (soy el 5to campo del TCR 0)
   como ancla adicional, para no generar falsos "field_removed + field_added" en cadena
   cuando en realidad todo se corrió por un solo campo que cambió de tamaño más arriba.
   Esto requiere pruebas con casos reales de ediciones consecutivas para validar el
   heurístico.

### 4.5 Etapa 6 (clasificación IA) — labels propuestos análogos

Mismo patrón que `06_classify_changes.py` (Ollama + JSON Schema + safety net
determinístico), pero con labels de dominio propio, por ejemplo:
- `structural_change` (impacta el layout binario, siempre requiere revisión del DE)
- `business_rule_change` (cambia valores válidos/descripción, sin tocar layout)
- `editorial_reword` (mismo significado, redacción distinta)
- `extraction_noise` (artefacto del extractor, no cambio real de Visa)

El "safety net" de `detect_disappeared_content` (detectar contenido que desapareció sin
equivalente aunque el LLM diga que no cambió nada) es directamente reutilizable tal cual.

---

## 5. Hallazgos empíricos de esta sesión (evidencia real inspeccionando los PDFs)

### 5.1 Ejemplo real que valida el caso de uso central

Extraído de `20260418_-_BASE_II_Clearing_Interchange_Formats__TC_01_to_TC_49.pdf`,
sección "TC 33.A - CP 02 TCR 0 EMV Data":

```
EMV Data Record Layout
Position  Field Length  Format  Contents
1-2       2             UN      Transaction Code
3         1             UN      Transaction Code Qualifier
4         1             AN      Transaction Component Sequence Number
5-10      6             UN      Destination Identifier
11-16     6             UN      Source Identifier
17-20     4             AN      TC 33 Application Code
21-35     15            AN      Message Identifier
36-37     2             AN      Transaction Type
38-40     3             AN      Card Sequence Number
41-46     6             AN      Terminal Transaction Date
47-52     6             AN      Terminal Capability Profile
53-55     3             AN      Terminal Country Code
56-63     8             AN      Unpredictable Number
64-67     4             AN      Application Transaction Counter
68-71     4             AN      Application Interchange Profile
72-87     16            AN      Application Cryptogram
88-97     10            AN      Terminal Verification Results
98-109    12            AN      Amount, Authorized
110-117   8             AN      Form Factor Indicator
118-149   32            AN      Dedicated File Name - Application ID (AID)
150       1             AN      Tap-to-Phone Indicator
151-168   18            AN      Reserved
```

Este `151-168 Reserved` es exactamente el patrón que el proyecto necesita vigilar entre
ediciones consecutivas.

Después de la tabla resumen viene la sección "EMV Data Edit Criteria" con la ficha
detallada de cada campo, patrón texto corrido:

```
Transaction Code
Positions: 1-2
Length: 2
Format: unpacked numeric
Description: This field contains the value 33.
```

### 5.2 Hallazgo crítico sobre el acceso a los PDFs en este entorno

Los archivos del proyecto (`/mnt/project/*.pdf`) **NO son binarios PDF reales** en este
entorno — son texto plano ya pre-extraído, servido con extensión `.pdf` para que la
herramienta `view` los muestre paginados. Verificado con:
- `head -c 20 archivo.pdf` → devuelve texto legible (`BASE II Clearing Int...`), no la
  cabecera estándar `%PDF-1.x`.
- `pdfplumber.open(...)` → `PDFSyntaxError: No /Root object! - Is this really a PDF?`
- `fitz.open(...)` (PyMuPDF) → `Failed to open file ... as type pdf`.

**Consecuencia práctica**: en esta sesión no fue posible correr una prueba real de
conversión a Markdown (Docling / pymupdf4llm) sobre los PDFs del proyecto, porque no son
binarios reales. Se dejó instalado `pymupdf4llm` en el entorno de prueba pero no se pudo
usar contra estos archivos.

**Acción pendiente**: para poder decidir con evidencia (no solo con la inspección del
texto ya aplanado) si conviene pre-procesar a Markdown antes de la ingesta, se necesita
subir un PDF real (binario) — idealmente uno de los manuales más chicos, como
`base_ii_transactions_quick_reference`, para no cargar con las ~940 páginas del TC 01-49.

**Advertencia de diseño derivada de este hallazgo**: si en el pipeline real de este
proyecto el PDF pasa en algún punto por un sistema que lo aplana a texto plano (por
ejemplo, un indexador de conocimiento) antes de llegar a la etapa de ingesta, se pierde
toda la información de layout/columnas necesaria para reconstruir bien las tablas de
Record Layout. Hay que garantizar que la etapa 1 (ingesta) trabaje siempre sobre el PDF
binario original.

### 5.3 Recomendación de ingesta (pendiente de validar empíricamente con PDF real)

Conclusión preliminar de la sesión, **a confirmar con la prueba del punto 5.2**:

- Las "fichas de campo" (texto corrido: Positions/Length/Format/Description) se extraen
  bien incluso con extracción cruda simple (`pdftotext`) — no son tablas PDF reales, son
  párrafos con un patrón regular, parseables con regex.
- Las tablas resumen "Record Layout" (grilla real con columnas) son las que están en
  riesgo con extracción cruda: en tablas angostas de una fila por línea (como el ejemplo
  de 5.1) `pdftotext` las linealiza razonablemente bien, pero en tablas más anchas, con
  celdas que envuelven varias líneas, o columnas dispuestas lado a lado, la extracción
  cruda puede mezclar texto de columnas distintas en una misma línea, rompiendo el
  parseo silenciosamente — que es justo el peor escenario para este proyecto: perder de
  vista el campo que cambió.
- Por eso se recomienda (con reserva, pendiente de prueba real) un **preprocesamiento a
  Markdown con una herramienta layout-aware** (Docling, pymupdf4llm, u otra) al menos
  para las tablas de Record Layout, preservando el texto corrido de las fichas de campo
  tal cual (no hace falta convertirlo, ya es limpio).
- Esto es coherente con el diseño ya existente en la POC de Guías: `05_diff_descriptors.py`
  indexa y compara el contenido de tablas como texto (`build_table_index`), lo cual
  implica que la etapa 1 de esa POC ya entregaba las tablas razonablemente bien
  estructuradas (probablemente vía Docling, aunque el script de esa etapa no fue
  compartido y no se pudo confirmar el formato exacto de salida).
- **Riesgos a tener en cuenta**: costo/tiempo de correr un modelo de layout sobre
  documentos de hasta ~940 páginas × ~9 versiones × 7 familias de manuales (conviene
  cachear el Markdown por versión de PDF, procesar una sola vez); fidelidad no
  garantizada al 100% incluso con herramientas layout-aware, especialmente en tablas que
  cruzan de página (la propia POC de Guías tuvo que resolver ese caso con
  `_merge_table_continuations`).

### 5.4 Estructura de secciones/patrones a relevar por manual (pendiente)

Los manuales de Visa no usan un único patrón de numeración de secciones. El
`02_guide_parser.py` de la POC de Guías asume `\d+(\.\d+)*` (`1.2.3`). Pero además de esa
numeración estándar de capítulo, los manuales técnicos tienen sub-estructuras propias del
dominio de mensajería, como:
- `TC 33.A Capture Transactions (Acquirer)` (Transaction Code, a veces con sufijo de letra)
- `CP 02 TCR 0 EMV Data` (Component/Processing group + Transaction Component Record)

Estos patrones habría que catalogarlos por cada uno de los 7 manuales antes de escribir el
parser de estructura, porque probablemente no es el mismo patrón en BASE I, BASE II y VSS.
No se hizo este relevamiento todavía — queda como tarea pendiente.

---

## 6. Estado actual / próximos pasos concretos

- [ ] **Conseguir un PDF binario real** de al menos un manual (recomendado:
      `base_ii_transactions_quick_reference`, es el más chico) para poder correr pruebas
      reales de extracción.
- [ ] **Probar extracción cruda vs Markdown layout-aware** sobre 2-3 páginas con tablas de
      Record Layout "difíciles" (anchas, con wrap, o que crucen de página) de distintos
      manuales, y comparar fidelidad. Con esa evidencia, decidir la herramienta de ingesta
      (candidatas: Docling, pymupdf4llm — ya instalado en un entorno de prueba de esta
      sesión pero no probado contra un PDF real).
- [ ] **Pedir/reconstruir las etapas 1, 3 y 4** de la POC de Guías si en algún momento
      aparecen, para no reinventar decisiones ya tomadas por el otro equipo (formato
      exacto del `raw_guide.json`, cómo serializan las tablas dentro de los bloques,
      lógica de matching de programas/descriptores que podría dar ideas para el matching
      de campos).
- [ ] **Relevar los patrones de sub-estructura** (TC, TCR, CP, etc.) por cada uno de los 7
      manuales, antes de escribir el parser de estructura.
- [ ] **Diseñar el esquema de datos** (JSON) para bloques de campo, análogo al
      `structured_guide.json` pero con la jerarquía Manual → TC → TCR → Campo.
- [ ] **Diseñar el algoritmo de matching por posición** con manejo del caso de "corrimiento
      en cadena" quando un campo cambia de longitud (ver 4.4).
- [ ] Recién después de lo anterior, empezar a escribir código de ingesta (etapa 1) y
      normalización (etapa 2, adaptando `02_guide_parser.py`).

---

## 7. Archivos de referencia disponibles en el proyecto (para cargar en el nuevo entorno)

- `tree.txt` — árbol completo de manuales y versiones disponibles.
- `02_guide_parser.py`, `05_diff_descriptors.py`, `06_classify_changes.py` — scripts de
  referencia de la POC de Guías (dominio distinto, ver sección 3).
- `diagramapng.png` — diagrama de las 7 etapas del proceso esperado.
- Los 7 manuales técnicos en PDF (múltiples versiones cada uno) — ver sección 2. **Nota**:
  según el punto 5.2, verificar en el nuevo entorno si estos PDFs están disponibles como
  binarios reales o si hace falta re-subirlos.
