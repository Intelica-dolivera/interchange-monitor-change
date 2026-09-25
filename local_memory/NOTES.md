# interchange_change_monitor — notas de diseño (2026-08-10)

Conversación en modo dialogo (sin código todavía, por pedido explícito). Resumen para retomar.

> **Bugs/gaps conocidos pendientes de retomar**: ver `TODO.md` en esta misma carpeta (índice
> accionable, corto). Este archivo (`NOTES.md`) tiene el detalle narrativo completo de cada uno.

## Objetivo del proyecto

Analizar manuales técnicos de Visa (y a futuro Mastercard) en PDF — `base_i`, `base_ii`, `vss` —
para detectar diferencias entre ediciones en las definiciones de campos de archivos/mensajes.
Caso guía: un manual dice que un archivo tiene 20 campos (18 definidos + 2 reservados); la edición
siguiente muestra 19 campos definidos → uno de los reservados pasó a estar definido. Otros tipos de
cambio: campos nuevos, cambios de valor/definición, campos que dejan de tener definición.

Estructura de datos: `visa/src/{base_i,base_ii,vss}/<manual>/<YYYYMMDD> - <Título>.pdf`, varias
ediciones fechadas por manual. `mastercard/` existe pero está vacío (scope futuro).

## Pipeline de referencia (`utils_example/`, hecho por otro equipo para "Guías de Interchange")

Documento distinto (reglas de tarifa, no specs de campos), pero el pipeline es el punto de partida
arquitectónico:

1. **Stage 1 (no compartido)** — PDF → `raw_guide.json` vía **Docling**: bloques `text`/`table` con
   `page`, `bbox`, `text`. Las tablas ya vienen en Markdown en este punto (no todo el documento).
2. **Stage 2 (`02_guide_parser.py`)** — ordena bloques, detecta jerarquía de secciones numeradas,
   pega captions `Table X-Y: Título` a su tabla, clasifica rol de bloque, filtra ruido
   (headers/footers/TOC/avisos legales), fusiona tablas partidas entre páginas comparando el header
   normalizado de la tabla.
3. **Stages 3-4 (no compartidos)** — matching Program/Fee Descriptor viejo↔nuevo (exact + fuzzy por
   nombre).
4. **Stage 5 (`05_diff_descriptors.py`)** — diff de lo emparejado: cambios de tarifa, cambios de
   texto de criterio (SequenceMatcher, umbral 0.98), renames fuzzy, altas/bajas. Resuelve contenido
   de tablas referenciadas (`Table X-Y`) en ambas versiones como contexto para IA.
5. **Stage 6 (`06_classify_changes.py`)** — LLM local (Ollama qwen3:4b, JSON schema forzado, temp 0)
   clasifica SOLO los cambios de texto libre ambiguos en 4 labels, con red de seguridad
   determinística. Decisiones estructurales (alta/baja/rename) quedan 100% determinísticas.

## Mapeo de dominio: Guías vs Manuales técnicos (este proyecto)

| Guías (referencia) | Manuales técnicos (este proyecto) |
|---|---|
| Contenedor: Program | Contenedor: Record/Message/TC (ej. TC 05, TC 15) |
| Detalle: Fee Descriptor | Detalle: Campo/Data Element (posición, longitud, nombre, formato) |
| Matching por nombre (fuzzy) | Matching por **posición/número de campo** — más estable que nombre |
| Cambios: alta/baja/rate/criteria/rename | + tipo propio: **reservado → definido** (no es rename ni alta pura, la posición ya existía) |

No conviene portar 1:1 el fuzzy-name-matching de stage 3-4; el matching acá debería basarse
primero en clave posicional/numérica estable, con nombre como señal secundaria. El patrón de
stage 2 (clasificación de bloques, filtrado de ruido, fusión de tablas entre páginas) sí es
reusable porque son PDFs de Visa con ruido similar (headers/footers/avisos).

## Pendientes / próximo paso

1. **No hay herramientas de PDF instaladas** en este entorno (ni pdftotext ni pypdf/pdfplumber/
   docling). Nunca llegamos a abrir un manual real y ver una tabla de campos real — todo el
   razonamiento sobre columnas (Posición/Field Number/Longitud/Formato/Definición) es de
   conocimiento general de las specs de Visa Base I/II/VSS, no verificado contra estos PDFs.
2. **Siguiente paso propuesto (ofrecido, no aprobado aún):** instalar herramientas de PDF (Docling
   u otra) y sacar 1-2 páginas de muestra de
   `visa/src/base_ii/base_ii_clearing_interchange_formats_tc_01_to_tc_49/` (la familia de donde
   sale el ejemplo de campos reservados) para validar el layout real de tabla antes de diseñar el
   parser.
3. **Recomendación de ingesta dada (pendiente de validar):** replicar el enfoque híbrido de Docling
   del equipo de referencia (bloques tipados con bbox/página + tablas en Markdown), en vez de texto
   plano crudo (rompe alineación de columnas en tablas de posición fija) o Markdown de todo el
   documento en una sola pasada (pierde metadata de layout por bloque, necesaria para jerarquía de
   secciones y fusión de tablas partidas entre páginas).
4. **Pregunta abierta sin responder:** ¿las tablas de campos son estructuralmente homogéneas entre
   manuales (mismas columnas siempre) o cada familia de manual tiene su propio layout? Define si
   alcanza un parser de tabla genérico o hacen falta reglas por familia de manual.

Al retomar: no re-derivar todo esto, confirmar que sigue vigente (releer utils_example / carpeta de
PDFs si cambiaron) y continuar en el punto 2, salvo que el usuario indique otra cosa.

---

## Actualización 2026-08-11 — fusión con `Claude_web_PROJECT_MEMORY.md`

El usuario corrió una sesión de diseño paralela en Claude Web (mismos recursos, sin los PDFs
completos por límite de peso — 1 PDF por manual). Esa sesión sí llegó a inspeccionar contenido real
y dejó hallazgos que esta memoria no tenía. Resumen fusionado:

### Modelo de dominio confirmado (con nombres reales)

```
Manual (versión = fecha)
 └── Transaction Code / sección funcional (ej. "TC 33.A Capture Transactions (Acquirer)")
      └── Component Record / grupo de campos (ej. "TCR 0", "CP 02 TCR 0 EMV Data")
           └── Campo: position_range, length, format, name, description, valid_values, notes
```

Leyenda de formatos (al pie de las tablas Record Layout, puede variar por manual): `AN`
Alphanumeric, `ANS` Alphanumeric Special, `DX` Display Hexadecimal, `N` Numeric, `UN` Unpacked
Numeric.

### Dos patrones de contenido, con distinto riesgo de extracción

1. **Tablas "Record Layout"** — grilla real (`Position | Field | Length | Format | Contents`), una
   fila por campo. Es la fuente de verdad estructural. **Mayor riesgo**: en tablas angostas
   (una fila por línea) la extracción cruda (`pdftotext`) linealiza bien, pero en tablas anchas,
   con celdas que envuelven o columnas lado a lado, puede mezclar texto de columnas distintas sin
   avisar — justo el peor caso para este proyecto.
2. **"Fichas de campo"** — NO son tabla PDF real, es texto corrido con patrón repetido
   (`Nombre` → `Positions:` → `Length:` → `Format:` → `Description:` → opcional `Values:`/`Note:`/
   `Mapping:`). Parseable con regex incluso desde extracción cruda. Ambos patrones describen el
   mismo campo lógico y deben enlazarse por nombre + rango de posición.

### Ejemplo real encontrado (valida el caso de uso central)

De `20260418 - BASE II Clearing Interchange Formats, TC 01 to TC 49.pdf`, sección "TC 33.A - CP 02
TCR 0 EMV Data", la tabla Record Layout termina en:
```
150       1    AN   Tap-to-Phone Indicator
151-168   18   AN   Reserved
```
Este `151-168 Reserved` es exactamente el tipo de fila que hay que vigilar entre ediciones.

### 8 categorías de cambio propuestas para la etapa de diff

`field_added`, `field_removed`, `field_redefined` (misma posición, cambia nombre/significado),
`field_resized` (cambia longitud — ver problema de corrimiento en cadena abajo),
`field_position_shifted` (mismo campo, rango corrido — típicamente consecuencia de un
`field_resized` anterior), `field_format_changed`, `field_description_changed` /
`field_values_changed`, y a nivel superior `tc_added`/`tc_removed`/`tcr_added`/`tcr_removed`.

### Problema de diseño sin resolver: "corrimiento en cadena"

Cuando un campo cambia de longitud, todos los campos siguientes del mismo TCR corren de posición
aunque no cambiaron en sí. Matching solo por rango absoluto de bytes generaría falsos pares
`field_removed`+`field_added` en cadena. Mitigación propuesta (sin validar): usar **posición
ordinal dentro del TCR** (ej. "soy el 5to campo del TCR 0") como ancla secundaria junto al rango de
bytes. Requiere validar con ediciones consecutivas reales.

### Etapa 6 — labels propuestos análogos

`structural_change`, `business_rule_change`, `editorial_reword`, `extraction_noise`. El safety net
`detect_disappeared_content` de la POC de Guías es reusable tal cual.

### Hallazgo crítico — diferencia de entorno

En la sesión de Claude Web, los PDFs del proyecto (`/mnt/project/*.pdf`) **no eran binarios PDF
reales** — eran texto plano pre-extraído con extensión `.pdf` (falló `pdfplumber.open()` y
`fitz.open()`). Nunca se pudo probar extracción real ahí.

**Verificado en ESTE entorno (2026-08-11): los PDFs SÍ son binarios reales**
(`%PDF-1.5`, confirmado con `file` y hexdump del header). Esto significa que en este entorno local
sí podemos correr pruebas reales de extracción — cosa que la sesión de Claude Web no pudo hacer.

### Pendientes actualizados

1. Instalar tooling de PDF liviano (candidatos: `pdfplumber`, `pymupdf4llm`; `docling` como opción
   más pesada si las livianas no alcanzan en tablas anchas/complejas).
2. Sacar muestras reales de `base_ii_clearing_interchange_formats_tc_01_to_tc_49` (tiene el ejemplo
   de campo reservado) y de `base_ii_transactions_quick_reference` (el manual más chico, última
   edición ~128KB, bueno para iterar rápido).
3. Comparar fidelidad de extracción específicamente en las tablas Record Layout (mayor riesgo).
4. Catalogar patrones de sub-estructura (TC, TCR, CP...) por cada una de las 7 familias de manual —
   no se hizo todavía, debería resolverse en parte como efecto secundario del muestreo del punto 2.

---

## Actualización 2026-08-11 (cont.) — resultados empíricos de la comparación de herramientas

Se instalaron `pdfplumber` + `pymupdf4llm` y se probaron sobre 3 páginas reales de 3 familias de
manual distintas. Resultados, con datos concretos:

### Caso 1 — tabla "Record Layout" angosta (una fila por línea)

`base_ii_clearing_interchange_formats_tc_01_to_tc_49`, pág. 439, tabla EMV Data Record Layout
(incluye la fila `151-168 18 AN Reserved` del caso de uso central):
- **`fitz.get_text()` crudo (PyMuPDF, sin ninguna herramienta de tablas)**: reconstruye las filas
  perfectamente, en orden correcto, sin pérdida.
- **`pymupdf4llm.to_markdown()`**: también perfecto en este caso — genera una tabla Markdown
  correcta fila por fila.
- **`pdfplumber.extract_tables()`** (estrategia default "lines" y también "text"): **falla mal** —
  la tabla no tiene líneas de grilla visibles (borderless), y la detección de columnas por
  clustering de texto arma columnas mal delimitadas, mezclando texto de columnas distintas o
  perdiendo columnas enteras (ej. devuelve solo 2 columnas en vez de 5, o filas destrozadas en
  fragmentos como `['21-35', '1', '5', 'AN', 'Message Ident', 'ifier']`).

### Caso 2 — tabla ancha de 3 columnas con texto envuelto y bullets

`base_ii_clearing_data_codes`, pág. 31, "Retired Chargeback Reason Codes" (columnas: Reason Code /
Applicable Operating Regulations / Chargeback Reason Rules, con listas de viñetas por región):
- **`fitz.get_text()` crudo**: reconstruye TODO correctamente y completo — código 82 (Duplicate
  Processing) y código 83 (Fraud - Card-Absent) ambos presentes, con todo el texto de viñetas en
  orden.
- **`pymupdf4llm.to_markdown()`**: **hallazgo crítico** — al convertir esta misma página a
  Markdown, **la fila completa del código 82 desaparece silenciosamente** (la tabla Markdown
  resultante salta directo de la última fila de la página anterior al código 83, sin rastro de 82).
  Confirmado corriendo `pages=[29,30]` juntas: el 82 no aparece atribuido a ninguna página. Esto es
  exactamente el peor escenario para este proyecto — pérdida silenciosa de una fila/campo — y
  ocurrió con la herramienta "inteligente" (reconstrucción de tabla vía heurística/ML), no con la
  extracción de texto cruda.

### Caso 3 — layout de reporte de ancho fijo (monoespaciado)

`vss_user_guide_volume_1_specifications`, pág. 61 (ejemplo de reporte VSS-100-W): texto
pre-formateado con alineación por espacios simulando un reporte impreso de ancho fijo
(`REPORT ID:`, `PAGE:`, columnas alineadas manualmente) — **un tercer tipo de contenido
completamente distinto** a los dos anteriores, no una tabla PDF en absoluto.

### Conclusión revisada sobre la herramienta de ingesta (corrige la hipótesis previa de ambas
sesiones de que haría falta algo layout-aware/ML)

En las pruebas reales, la extracción de texto cruda (`fitz.get_text()` / PyMuPDF, sin ningún
post-procesamiento de tablas) fue **más confiable que la reconstrucción "inteligente" de tablas**
de `pymupdf4llm`, la cual introdujo una pérdida silencial de fila. Y `pdfplumber.extract_tables()`
resultó directamente inutilizable en tablas sin líneas de grilla (que es el caso típico en estos
manuales).

**Recomendación de ingesta actualizada:**
- **Extracción primaria**: texto crudo ordenado por posición de lectura (`fitz.get_text()`),
  conservando página + bbox por bloque para trazabilidad — NO usar reconstrucción de tabla
  ML/heurística (`pymupdf4llm` markdown de tablas) como fuente de verdad para contenido crítico.
- **Parseo**: en vez de un parser de tablas genérico, escribir parsers basados en patrones
  (regex) específicos por cada una de las 3 formas de contenido catalogadas hasta ahora (ver
  abajo) — cada forma tiene una estructura de texto regular y predecible una vez que se sabe
  qué buscar.
- **`pdfplumber` puede conservarse** como herramienta de apoyo para geometría (bbox de palabras)
  como *chequeo cruzado* opcional (ej. contar filas esperadas por clustering de posición Y y
  comparar contra lo que devolvió el regex), no como extractor primario de tablas.
- **Docling no está justificado todavía** — la hipótesis original (herramienta ligera insuficiente,
  hay que subir a ML de layout) no se sostiene con la evidencia real: la herramienta más simple
  (texto crudo) fue la más confiable de las tres probadas.

### Respuesta parcial a la pregunta abierta #4 (¿tablas homogéneas entre manuales?)

**No, confirmado con evidencia real.** Se catalogaron 3 formas de contenido distintas en solo 3
familias de manual muestreadas:
- **Tipo A — "Record Layout" + "Field ID card"** (`base_ii_clearing_interchange_formats_tc_01_a_49`,
  probablemente también `tc_50_a_92` y los manuales de BASE I): grilla compacta de campos +
  fichas de texto corrido por campo.
- **Tipo B — tablas de código/regla** (`base_ii_clearing_data_codes`): 2-3 columnas, texto
  envuelto y viñetas, sin relación con posición/longitud de campo.
- **Tipo C — reportes de ancho fijo** (`vss_user_guide_volume_1_specifications`): texto
  pre-formateado simulando un reporte impreso, alineación manual por espacios.

**Falta muestrear** para completar el catálogo: `base_i` (mensajería ISO), `vss volume 2 reports`,
`base_ii_transactions_quick_reference`, `base_ii_clearing_edit_package_messages`,
`base_ii_clearing_interchange_formats_tc_50_to_tc_92`. Se necesitan reglas de parseo específicas
por tipo de contenido, no un parser de tabla único genérico.

---

## Actualización 2026-08-11 (cont. 2) — catálogo completo de las 7 familias de manual

Se muestrearon las 5 familias restantes. **Conclusión principal: se puede usar `fitz.get_text()`
(PyMuPDF) como única herramienta de extracción en las 7 familias** — reconstruyó correctamente el
contenido en cada caso probado, incluyendo un nuevo caso ancho con viñetas en VSS (ver abajo). Lo
que cambia entre manuales no es la herramienta de extracción sino el **patrón de parseo** (qué
regex aplicar sobre el texto ya extraído), porque cada familia tiene su propia "forma" de contenido.

### Catálogo de formas de contenido (6 tipos identificados)

- **Tipo A — Record Layout grid + Field ID card**: grilla compacta (Position/Field/Length/Format/
  Contents) + fichas de texto corrido por campo. Confirmado en
  `base_ii_clearing_interchange_formats_tc_01_to_tc_49` **y también en `tc_50_to_tc_92`**
  (mismo patrón exacto, muchísimos campos `Reserved` — buena fuente de casos de prueba para el
  caso de uso central).
- **Tipo A' — variante del Record Layout, esquema VSS**: en
  `vss_user_guide_volume_2_reports` existen tablas de layout de registros propios de VSS
  (`V23203`, `V23210`, `V23900`, etc.) con columnas `Field Name | Position | Attribute |
  Field Sources | Comments` — misma categoría estructural que el Tipo A (posición + definición de
  campo) pero con nombres de columna distintos y comentarios con viñetas. **Punto de estrés
  probado**: acá `pymupdf4llm` no perdió una fila completa (como en el Tipo B), pero **partió una
  fila con comentario envuelto en dos filas Markdown falsas** (una casi vacía) — otro defecto de
  integridad de datos, distinto al anterior pero igual de riesgoso. `fitz.get_text()` reconstruyó
  todo correctamente.
- **Tipo B — tablas de código/regla**: 2-3 columnas, texto envuelto + viñetas, sin relación con
  posición/longitud de campo. Confirmado en `base_ii_clearing_data_codes`. Variante más ancha
  (5 columnas) también en `vss_user_guide_volume_2_reports` p.23 ("Available VSS Reports").
- **Tipo C — reportes de ancho fijo (monoespaciado)**: texto pre-formateado simulando un reporte
  impreso real (`REPORT ID:`, `PAGE:`, columnas alineadas por espacios). Confirmado en
  `vss_user_guide_volume_1_specifications` **y es el contenido dominante de
  `vss_user_guide_volume_2_reports`** (es literalmente un catálogo de layouts de reporte). Estos
  bloques no son objetivo del diff de campos del proyecto — son samples de salida, no
  definiciones de estructura de archivo/mensaje.
- **Tipo D — índice/outline navegacional TC/TCR**: lista anidada de nombres de TC/TCR sin
  definición de campo (solo nombres). Confirmado en `base_ii_transactions_quick_reference`
  (manual corto, 24 páginas). Bajo riesgo, no es objetivo central del diff — es una tabla de
  contenidos funcional.
- **Tipo F — "fichas" de código de error/edición**: mismo patrón repetido de Tipo A (Label: Valor)
  pero para códigos de validación en vez de campos: `CÓDIGO` → `TÍTULO` → `Description:` →
  `Action:` → `Transaction Types:`. Confirmado en `base_ii_clearing_edit_package_messages`
  (346 páginas, catálogo de códigos `V####` y `######-I/S`). Mismo enfoque de parseo por regex que
  las fichas de campo — reusar la misma técnica, distinto vocabulario de labels.

### Hallazgo importante de alcance — `base_i` NO tiene tablas de layout de campo en este repo

`international_full_service_pos_online_messages_processing_specifications` (232 páginas) es,
verificado exhaustivamente (`grep` de "Positions:", "Field Definitions", "Data Element",
"Length"+"Format" en las 232 páginas), **narrativa de procesos de negocio y flujos de mensajes
ISO** (diagramas Acquirer/Issuer/V.I.P. como texto, reglas de negocio con viñetas), NO contiene
tablas byte-por-byte de definición de campo. Referencia explícita encontrada en el propio texto:
> "Refer to the V.I.P. System technical specifications manuals for details about the fields
> contained in advice messages."

Es decir, la definición de posición/longitud de los campos de BASE I (mensajes ISO 8583) vive en
un manual distinto ("V.I.P. System technical specifications", "VSPS Implementation Guide") que
**no está incluido en este repositorio**. Sí tiene tablas pequeñas tipo B (ej. "Stop Instruction
Types and Coded", 3 columnas) y referencias a números de campo (`Field 42`, `Field 43 (Positions
1–25)`) dentro de la prosa, pero no una tabla Record Layout completa por mensaje.

**Implicación para el alcance del proyecto**: el caso de uso central (reservado→definido) puede no
aplicar directamente a `base_i` con los archivos actuales — verificar con el usuario si falta subir
el/los manual(es) de especificación técnica de campos de BASE I, o si el alcance de este proyecto
para BASE I se limita a lo que hay (prosa de proceso, sin diff de campo binario).

### Veredicto final de herramienta (las 7 familias)

| Familia | Forma(s) de contenido | ¿`fitz.get_text()` alcanza? |
|---|---|---|
| `base_i` (`international_full_service_pos...`) | E (narrativa) + B chico | Sí — no hay grid de campo que perder |
| `base_ii_clearing_interchange_formats_tc_01_to_49` | A | Sí, confirmado con caso real (151-168 Reserved) |
| `base_ii_clearing_interchange_formats_tc_50_to_92` | A | Sí, mismo patrón confirmado |
| `base_ii_clearing_data_codes` | B | Sí — ojo, acá es donde `pymupdf4llm` perdió una fila |
| `base_ii_clearing_edit_package_messages` | F (ficha tipo A con otro vocabulario) | Sí |
| `base_ii_transactions_quick_reference` | D (índice, bajo riesgo) | Sí |
| `vss_user_guide_volume_1_specifications` | C + narrativa | Sí (Tipo C no es tabla, es texto preformateado) |
| `vss_user_guide_volume_2_reports` | C (dominante) + A' + B ancho | Sí, incluso en el caso ancho con viñetas |

**Conclusión: se puede usar `fitz.get_text()` (PyMuPDF) como ÚNICA herramienta de extracción para
las 7 familias.** No hace falta Docling ni depender de `pymupdf4llm` para reconstrucción de tabla
(de hecho, `pymupdf4llm` introdujo 2 defectos de integridad distintos en 2 manuales distintos
durante estas pruebas — perder fila completa en Tipo B, partir fila envuelta en Tipo A'). Lo que
sí hace falta es un **parser por patrón (regex) específico por tipo de contenido** (A/A'/B/C/D/F),
no un parser de tabla genérico — cada tipo tiene su propia gramática de texto plano, predecible una
vez identificada.

### Próximos pasos sugeridos

1. Confirmar con el usuario el hallazgo de alcance sobre `base_i` (¿falta un manual de specs de
   campo, o el alcance para BASE I es solo narrativo?).
2. Diseñar el parser de Etapa 1/2: extracción uniforme con `fitz.get_text()` (con página+bbox por
   bloque de texto vía `page.get_text("blocks")` o similar, para trazabilidad), seguida de
   clasificación de bloque por tipo de contenido (A/A'/B/C/D/F) y parseo específico por regex.
3. Empezar el diseño de parser por el Tipo A (es el objetivo central del proyecto), usando el
   ejemplo real de `151-168 Reserved` como caso de prueba de referencia.

---

## Actualización 2026-08-11 (cont. 3) — segundo manual de base_i agregado por el usuario, verificado

El usuario agregó un segundo manual en `base_i`:
`visa/src/base_i/authorization_only_online_messages_processing_specifications_International/`
(`Authorization-Only Online Messages Processing Specifications (International)`, 197 páginas, 2
ediciones: 20251015 y 20260420), para verificar si era el manual de specs de campo que faltaba.

**Verificado exhaustivamente (grep de regex `Position.*Field.*Length.*Format.*Contents` en las 197
páginas): NO tiene ninguna tabla Record Layout.** Es del mismo tipo narrativo que el otro manual de
`base_i` (Tipo E: prosa de proceso de negocio, referencias a campos por número dentro del texto,
p.ej. "Field 54 – Additional Amounts... Positions 1–2, Account Type, contain 00"). Tampoco tiene
el patrón de "ficha de campo" (`Positions:`/`Length:`/`Format:`) que sí existe en BASE II.

**Hallazgo adicional — séptima forma de contenido (Tipo G)**: en la página 158 hay una tabla de
**inventario de campos de archivo SIN datos de posición/longitud** — solo lista los nombres de
columna que componen cada archivo de la Cardholder Database (Activity File, Address Verification
File, ASAF), ej: `Account Number Length | Cardholder Account Number | Purge Date | Country Code |
Issuer ID Length | Issuer ID | Purchase Activity | ...`. Útil para saber QUÉ campos existen por
archivo, pero sin posición/longitud no permite el diff byte-a-byte del caso de uso central.

**Conclusión (superada, ver abajo)**: este segundo manual tampoco resolvía el vacío por sí solo,
pero llevó a encontrar los manuales correctos (ver actualización siguiente).

---

## Actualización 2026-08-11 (cont. 4) — VACÍO DE `base_i` RESUELTO: se encontraron los manuales técnicos correctos

El usuario agregó una nueva carpeta:
`visa/src/base_i/visanet-authorization_only_online_messages_technical_specifications/`, con 9
archivos:

- `20220610 - VisaNet Authorization-Only Online Messages Technical Specifications.pdf` (1242 pág.,
  única edición disponible).
- `20220610` a `20251015 - Full Service POS Online Messages Technical Specifications.pdf` (8
  ediciones, 1593–1673 páginas).

**Verificado: son manuales DISTINTOS entre sí, no una renombrada del otro** (coexisten con la misma
fecha 20220610, tamaños distintos — 1242 vs 1673 páginas). Pero ambos son exactamente los manuales
**"técnicos" (contraparte de campo/byte-level)** que faltaban junto a los narrativos de
"Processing Specifications" ya existentes:

| Narrativo (Processing, ya estaba) | Técnico (Technical, encontrado ahora) |
|---|---|
| `international_full_service_pos_online_messages_processing_specifications` ("Full Service POS Online Messages – Processing Specifications, International") | `Full Service POS Online Messages Technical Specifications` (8 ediciones) |
| `authorization_only_online_messages_processing_specifications_International` ("Authorization-Only Online Messages Processing Specifications, International") | `VisaNet Authorization-Only Online Messages Technical Specifications` (1 sola edición: 20220610) |

**Confirmado con match textual exacto**: el manual narrativo de Full Service, página 35, dice
literalmente *"...Formats chapter of **Full Service POS Online Messages Technical
Specifications**, for information..."* — coincide letra por letra con el título del manual técnico
encontrado. Esto confirma que SÍ es el manual referenciado.

**Verificado que el manual técnico "Full Service POS Online Messages Technical Specifications"
(edición 20251015, 1593 páginas) tiene el contenido necesario para el caso de uso central**:
- 258 páginas con el patrón de "ficha de campo" `Field N – Attributes / Description / Usage /
  Field Edits / Reject Codes` (variante del Tipo A/F, catalogar como **Tipo A''**: mismo concepto
  de ficha por campo, pero con vocabulario de labels propio de BASE I/ISO 8583 en vez de
  `Positions:/Length:/Format:/Description:` de BASE II).
- 19 páginas con grilla real `Field Name | Position | Attributes | Description` (Tipo A'), de las
  cuales **4 contienen filas `Reserved`** — confirma que el caso de uso central (reservado→definido)
  sí aplica a `base_i` con este manual.
- Al ser 8 ediciones (2022-04 a 2025-10... y probablemente pronto 2026), sí permite diffing
  edición-a-edición real, a diferencia del manual "VisaNet Authorization-Only..." que solo tiene
  una edición disponible (2022-06) — útil como referencia de estructura pero no para probar diffs
  de versión todavía.

También se detectó una **octava forma de contenido (Tipo H)**, presente en el manual técnico
Full Service: **matriz de uso de campo por tipo de mensaje** — filas = número+nombre de campo,
columnas = tipos de mensaje/flujo (`0100`, `0110`, `0120`, Acqr→VIC→Issr...), celdas = código de
uso (`M`=Mandatory, `C`=Conditional, `O`=Optional, `C+`, `C-`, con flechas `→` indicando
paso del dato sin cambio entre etapas). Ejemplos: "Table 237: Manual Cash or Quasi-Cash-Electronic
Terminal and No PIN (Non-CPS)", "Table 275: VSDC ATM Account Transfer Reversal". Este tipo no es
para diff de definición de campo en sí, sino para diff de **requerimiento/uso del campo por tipo de
mensaje** — un tipo de cambio adicional a considerar (ej. "el campo 42 pasó de Condicional a
Mandatorio en el mensaje 0100") que no estaba catalogado en las categorías de cambio propuestas
originalmente (ver sección 4.3 / los "8 tipos de cambio" — puede que haga falta una categoría
adicional para esto, ej. `field_usage_requirement_changed`).

**Estado final de `base_i`**: el vacío de alcance está resuelto. `base_i` tiene su propio par
narrativo+técnico igual que las otras familias, y el manual técnico de Full Service (con 8
ediciones) es apto para el caso de uso central. El manual de "VisaNet Authorization-Only..."
(1 edición) puede sumarse al catálogo de referencia pero no sirve aún para probar diffs
edición-a-edición hasta que aparezcan más ediciones.

**Pendiente**: catalogar formalmente estos 2 manuales técnicos como parte de `base_i` en el
inventario de manuales (sección 2 de este documento), y decidir si "VisaNet Authorization-Only..."
entra al alcance del proyecto solo como referencia estructural (sin diff de versión) o se excluye
hasta tener más ediciones.

### Limpieza de carpetas (2026-08-11)

Se eliminó permanentemente
`visa/src/base_i/authorization_only_online_messages_processing_specifications_International/`
(2 PDFs, narrativo "Authorization-Only Online Messages Processing Specifications", confirmado sin
contenido de Record Layout) — decisión del usuario, confirmada explícitamente antes de borrar
(la carpeta del proyecto no está bajo git, el borrado es irreversible).

**Estado final de `base_i` tras la limpieza** — 2 carpetas:
- `international_full_service_pos_online_messages_processing_specifications/` — narrativo Full
  Service (Tipo E), se conserva.
- `visanet-authorization_only_online_messages_technical_specifications/` — contiene los 2 manuales
  técnicos: `VisaNet Authorization-Only Online Messages Technical Specifications` (1 edición) y
  `Full Service POS Online Messages Technical Specifications` (8 ediciones) — estos son los que
  tienen el contenido Tipo A'/A''/H para el caso de uso central.

---

## Actualización 2026-08-11 (cont. 5) — SÍNTESIS FINAL: catálogo cerrado de las 9 familias + veredicto de herramienta

Se rehizo el muestreo de forma sistemática sobre las 9 carpetas de manual (inventario completo, ya
con `base_i` resuelto), comparando explícitamente la edición más antigua contra la más reciente de
cada una, para responder dos preguntas: (1) ¿el patrón de contenido se mantiene estable entre
ediciones dentro de una misma familia, o hay que analizar versión por versión? (2) ¿conviene una o
dos herramientas de extracción para las 9 familias?

### Chequeo de estabilidad entre ediciones (antigua vs. reciente, por conteo de páginas con cada firma de patrón)

| Familia | Ediciones | Ficha campo (vieja→nueva) | Grid posición (vieja→nueva) | Reporte ancho fijo (vieja→nueva) |
|---|---|---|---|---|
| base_i narrativa (Full Service) | 7 | 0 → 0 | 0 → 0 | 0 → 0 |
| base_i técnico (Auth-Only + Full Service Tech) | 9 | presente en ambas (258 pág. en ed. 2025 con el regex correcto de su vocabulario) | 29 → 19 | 0 → 0 |
| base_ii clearing_data_codes | 9 | 0 → 0 | 0 → 0 | 0 → 0 |
| base_ii clearing_edit_package_messages | 9 | 0 → 0 | 0 → 0 | 0 → 0 |
| base_ii tc_01_to_49 | 9 | 751 → 796 | 377 → 389 | 0 → 0 |
| base_ii tc_50_to_92 | 9 | 309 → 312 | 142 → 149 | 0 → 0 |
| base_ii quick_reference | 8 | 0 → 0 | 0 → 0 | 0 → 0 |
| vss volume_1 | 6 | 0 → 0 | 0 → 0 | 26 → 26 |
| vss volume_2 | 7 | 0 → 0 | 79 → 85 | 138 → 138 |

**Conclusión de estabilidad**: en ninguna familia el patrón aparece o desaparece entre ediciones —
los conteos se mantienen en el mismo orden de magnitud, creciendo proporcionalmente con el total de
páginas (que también crece edición a edición). **El patrón de parseo es una propiedad de la
familia de manual, no de la versión específica.** No hace falta analizar cada versión
individualmente (sería efectivamente interminable, como bien intuyó el usuario) — alcanza con
diseñar un parser por familia/tipo de contenido y aplicarlo tal cual a todas sus ediciones.

### Catálogo final — 9 manuales, 8 tipos de contenido, 1 sola herramienta

| Manual (carpeta) | Tipo(s) de contenido | ¿`fitz.get_text()` alcanza? |
|---|---|---|
| `base_i` narrativa Full Service | E (narrativa de proceso) | Sí — no hay grid que perder |
| `base_i` técnico (Auth-Only + Full Service Tech) | A' (grid Position/Attributes) + A'' (ficha de campo BASE I) + H (matriz de uso M/C/O por tipo de mensaje) | Sí, confirmado con filas `Reserved` reales |
| `base_ii` clearing_data_codes | B (código/regla, texto envuelto + viñetas) | Sí — acá es donde `pymupdf4llm` perdió una fila completa |
| `base_ii` clearing_edit_package_messages | F (ficha de código de error/validación) | Sí |
| `base_ii` tc_01_to_49 | A (grid Record Layout + ficha de campo) | Sí — caso real `151-168 Reserved` |
| `base_ii` tc_50_to_92 | A (mismo patrón) | Sí |
| `base_ii` quick_reference | D (índice navegacional TC/TCR) | Sí |
| `vss` volume_1 | C (reporte de ancho fijo) + narrativa | Sí — Tipo C no es tabla, es texto preformateado |
| `vss` volume_2 | C (dominante) + A' + B ancho | Sí, incluso con viñetas — acá `pymupdf4llm` fragmentó una fila envuelta en dos filas falsas |

### Veredicto final de herramienta

**Una sola herramienta para las 9 familias: `fitz.get_text()` (PyMuPDF, texto crudo).** No se
necesita una segunda herramienta por familia ni Docling. Evidencia acumulada en contra de depender
de reconstrucción "inteligente" de tabla:
- `pymupdf4llm` tuvo **2 defectos de integridad de datos distintos, confirmados en 2 manuales
  distintos**: pérdida silenciosa de fila completa (Tipo B, `base_ii_clearing_data_codes` p.31,
  código "82" desaparecido) y fragmentación de una fila con comentario envuelto en dos filas
  Markdown falsas (Tipo A', `vss_volume_2` p.421, registro V23203).
- `pdfplumber.extract_tables()` falla en toda tabla sin líneas de grilla — que es el caso típico de
  las tablas Record Layout de estos manuales (probado con estrategias "lines" y "text", ambas
  producen columnas rotas/mezcladas).
- `fitz.get_text()` reconstruyó correctamente TODOS los casos probados (Tipo A, A', B, D), sin
  ninguna excepción encontrada hasta ahora.

Lo único que cambia entre manuales es el **parser de patrón (regex) a aplicar sobre el texto ya
extraído**, según la firma de contenido de cada familia — no la herramienta de extracción.

### Próximo paso (no iniciado aún)

Diseñar el parser de Etapa 1/2: extracción uniforme con `fitz.get_text()`, seguida de un
clasificador de bloque por tipo de contenido (A/A'/A''/B/C/D/F/H) y un parser específico por regex
para cada tipo — empezando por el Tipo A (el objetivo central del proyecto), usando el caso real
`151-168 Reserved` de `base_ii_clearing_interchange_formats_tc_01_to_tc_49` como prueba de
referencia.

---

## Actualización 2026-08-11 (cont. 6) — Arranca la implementación: Módulo 1 (POC) para `base_ii_clearing_data_codes`

Se decidió organizar el proyecto en `poc/<manual>/<NN_modulo>/` con código, y `poc/<manual>/data/
<NN_modulo>/` con las salidas intermedias (una por edición). El plan de 7 módulos del usuario
(Ingesta y Parseo → Normalización de bloques → Emparejamiento de bloques → Detección de cambios →
Interpretación de cambios con IA → Validación con Plataforma STD (por validar) → Reporte de
cambios) se mantiene sin cambios — la reconstrucción geométrica de líneas en filas/celdas/párrafos
(ver abajo) se confirmó que es trabajo del Módulo 2 (Normalización de bloques), no un módulo nuevo,
porque coincide exactamente con su definición ("preparar la información en bloques estandarizados")
y con el patrón de la etapa 2 del pipeline de referencia (`02_guide_parser.py`, que también hacía
varias tareas de reconstrucción dentro de una sola etapa de normalización).

**Módulo 1 implementado y congelado** en
`poc/base_ii_clearing_data_codes/01_ingesta_parseo/ingest.py`. Corre sobre las 9 ediciones de
`visa/src/base_ii/base_ii_clearing_data_codes/` y escribe una salida por edición en
`poc/base_ii_clearing_data_codes/data/01_ingesta_parseo/<fecha>.json`.

**Decisión de diseño clave, descubierta durante la revisión del esquema con el usuario**:
extraer a nivel de **línea** (vía `page.get_text("dict")`), no a nivel de **bloque**
(`page.get_text("blocks")`, usado en la primera versión del script). Motivo: `get_text("blocks")`
ya aplica un heurístico interno de PyMuPDF que agrupa texto por proximidad, y ese agrupamiento
puede fusionar erróneamente texto de columnas distintas de una tabla en una sola unidad — se
confirmó exactamente con el bloque `p31_b6` de este manual (`82\nAll\nDuplicate Processing`, tres
celdas de tres columnas distintas, fusionadas porque estaban físicamente cerca en la página). Una
vez fusionadas a nivel de bloque, se pierde el bbox individual de cada línea y el Módulo 2 ya no
puede deshacer esa decisión. Verificado con `get_text("dict")` que a nivel de línea sí se preserva
el bbox individual, revelando la señal geométrica necesaria para que el Módulo 2 reconstruya
correctamente filas y columnas:
- **Mismo rango Y, distinto X** → columnas distintas de la misma fila (ej. las 3 líneas de
  `82`/`All`/`Duplicate Processing`, las tres con Y=[139.8, 152.0] pero X=91.8/158.8/209.0).
- **Y consecutivo (una línea empieza donde termina la anterior), X similar** → misma celda/columna,
  texto envuelto en varios renglones (ej. una viñeta larga, o un título de columna partido en 2
  líneas como "Operating"/"Regulations").

**Esquema final del JSON de salida del Módulo 1**:
```json
{
  "manual": "base_ii_clearing_data_codes",
  "edition_date": "20260418",
  "source_file": "20260418 - BASE II Clearing Data Codes.pdf",
  "num_pages": 157,
  "page_size": [612.0, 792.0],
  "num_lines": 9664,
  "lines": [
    {"line_id": "p31_b6_l0", "order": 1264, "page": 31, "source_block": 6,
     "bbox": [91.8, 139.8, 102.1, 152.0], "text": "82"}
  ]
}
```
Campos: `manual`/`edition_date`/`source_file` = trazabilidad y clave de comparación entre
ediciones (Módulo 3). `num_pages`/`num_lines` = control rápido de sanidad. `page_size` (verificado
uniforme en las 157-158 páginas de las 9 ediciones, siempre 612×792pt/Letter) = permite al Módulo 2
calcular posición X relativa al ancho de página en vez de coordenada absoluta, generalizando mejor
entre manuales con distinto tamaño de página. Por línea: `line_id` (legible, para debug),
`order` (índice secuencial explícito, robusto a futuros filtrados/reordenamientos en Módulo 2),
`page`, `source_block` (el número de bloque que PyMuPDF le habría asignado — se conserva como pista
débil/no autoritativa, no como agrupamiento final), `bbox`, `text`.

**Filosofía de la frontera Módulo 1 / Módulo 2** (importante para no repetir el error): el Módulo 1
debe entregar la unidad más atómica y fiel posible (línea con posición exacta), sin ninguna decisión
de agrupamiento. Toda decisión de "esto va junto con esto" (fila de tabla, párrafo envuelto,
sección, ruido de página, rol del bloque, fusión de tablas entre páginas) es responsabilidad del
Módulo 2 — así esa decisión queda bajo control explícito y verificable del diseño propio del
proyecto, en vez de heredar ciegamente un heurístico genérico de PyMuPDF que no conoce la semántica
de estas tablas.

**Pendiente**: diseñar el Módulo 2 (Normalización de bloques) para este manual, usando las reglas
geométricas de arriba como base para reconstruir filas/celdas/párrafos, más clasificación de rol de
bloque (tabla de códigos, título de sección, ruido de página, narrativa) y filtrado de ruido.

---

## Actualización 2026-08-11 (cont. 7) — Módulo 2 (Normalización de bloques) implementado para `base_ii_clearing_data_codes`

**Código**: `poc/base_ii_clearing_data_codes/02_normalizacion_bloques/normalize.py`. **Salida**:
`poc/base_ii_clearing_data_codes/data/02_normalizacion_bloques/<fecha>.json`, una por edición.

### Filtrado de ruido (antes de reconstruir nada)

Calibrado con datos reales de esta edición (157-158 páginas, tamaño 612×792pt):
- **Encabezado/pie de página**: banda superior `y1 ≤ 45` y banda inferior `y0 ≥ 745`. Calibrado
  verificando la posición Y real de "BASE II Clearing Data Codes" (aparece 254 veces, casi todas
  con `y1` entre 29-41 — hay 1 aparición aislada en `y0=635` que es contenido real, no ruido, y el
  umbral la deja pasar correctamente), "Visa Confidential" (`y0` 742.8-760.0), fecha de edición
  (`y0=758.9` siempre) y números de página sueltos (mayoría en `y0=758.9`; 5 casos aislados en
  `y0≈700-714` con `x0` no alineado a la derecha resultaron ser códigos numéricos reales de una
  tabla, no números de página — confirma que el umbral 745 los deja pasar bien, un umbral de 700
  los habría eliminado por error).
- **Tabla de contenidos**: detectada por patrón de puntos de relleno (`(\. ){4,}`, ej.
  `"Member Settlement Data Codes. . . . . . . . . . . "`), NO por rango de páginas fijo (más
  robusto entre ediciones). Verificado: sin este filtro, una entrada de TOC como
  `"Título. . . . 53"` + su número de página comparten la misma banda Y → el heurístico de "2
  líneas en la misma fila = candidato a fila de tabla" las detectaría como falsa fila de datos.
  Con el filtro, las 3 páginas de TOC (5-7 en esta edición) quedan 100% como bloques `paragraph`,
  cero `table_row`/`table_header` espurios.

### Reconstrucción de filas/columnas — el algoritmo y un bug real encontrado y corregido

Algoritmo en 2 fases:
1. **Agrupar líneas en "filas visuales"**: dos líneas están en la misma fila si su solapamiento en
   Y supera el 50% de la altura de la más chica (no un solapamiento cualquiera — un solapamiento de
   apenas 1pt entre dos líneas de texto normal consecutivas NO cuenta como misma fila; se necesitó
   este umbral porque un solapamiento mínimo de borde SÍ ocurre naturalmente entre líneas
   consecutivas de texto normal).
2. **Decidir qué es cada fila y acumular**: una fila con 2+ líneas puede ser una fila de datos real
   o parte de un encabezado de columna partido en 2 renglones — se distinguen por si la primera
   celda "parece un código corto" (regex `^[A-Z0-9]{1,6}$`, sin palabras) o no. Una fila de 1 sola
   línea se asigna a la columna más cercana en X del bloque activo (así se acumulan los bullets y
   párrafos largos de una celda ancha como "Chargeback Reason Rules").

**Bug real encontrado durante la prueba** (documentado porque revela algo importante sobre
PyMuPDF): el orden en que `get_text("dict")` entrega las líneas de una página **no es
necesariamente fila-por-fila** — para el encabezado de la tabla de la p.31, entregó primero TODAS
las líneas de la etiqueta de la columna 1 ("Reason", "Code"), luego TODAS las de la columna 2
("Applicable", "Operating", "Regulations"), luego la columna 3 — es decir, columna por columna, no
fila por fila. El algoritmo de agrupación por filas asume que dos líneas de la misma fila están
razonablemente cerca en la secuencia de entrada; con orden columna-por-columna, "Reason" y
"Applicable" (mismo Y) quedaban separados por "Code" (Y distinto) en el medio, y el agrupamiento
fallaba silenciosamente (el encabezado salía partido en 4 bloques `paragraph` de 1 celda en vez de
1 bloque `table_header` de 3 celdas). **Corrección**: ordenar explícitamente las líneas de cada
página por posición real `(y0, x0)` antes de agrupar en filas, en vez de confiar en el orden que
entrega PyMuPDF. Con esta corrección, la reconstrucción es correcta: `table_header` con 3 celdas
bien fusionadas, `table_row` con las celdas completas (incluyendo toda la narrativa acumulada de
bullets). **Limitación conocida de este fix**: asume que la página es de una sola columna de flujo
de texto (no maquetación tipo periódico a 2 columnas) — no se encontró ese caso en este manual, pero
si apareciera en otro, el ordenamiento simple por `(y0, x0)` intercalaría mal las dos columnas.

### Validación empírica

Confirmado sobre la edición 20260418 (9664 líneas → 8860 útiles tras filtrar ruido → 2073 bloques):
- Tabla de 3 columnas (p.31, "Retired Chargeback Reason Codes"): encabezado fusionado
  correctamente en 3 celdas; fila `82` reconstruida con `["82", "All", "Duplicate Processing\n
  International:\n...(narrativa completa con bullets)"]`; fila `83` igual.
- Tabla de 2 columnas (p.101, "Return/Reclassification Reason Codes"): encabezado `["Code", "Error
  Condition"]`; filas `S55`/`S60`/`S70`... con su descripción completa. Confirma que el algoritmo
  generaliza entre tablas con distinto número de columnas dentro del mismo manual, sin regex por
  tabla.
- Zona de TOC (p.5-7): 18 bloques, el 100% tipo `paragraph`, cero falsos positivos de tabla.

### Esquema de salida del Módulo 2

```json
{
  "manual": "base_ii_clearing_data_codes",
  "edition_date": "20260418",
  "source_file": "...",
  "num_lines_in": 9664,
  "num_lines_kept": 8860,
  "num_blocks": 2073,
  "blocks": [
    {"type": "table_row", "page": 31, "cells": ["82", "All", "Duplicate Processing\n..."]}
  ]
}
```
`type` puede ser `table_header`, `table_row` o `paragraph`. `cells` es una lista ordenada por
posición X (columna 0, 1, 2...) — no se guarda la coordenada X en la salida final (ya cumplió su
propósito durante la reconstrucción).

### Limitación aceptada explícitamente (no se va a resolver ahora)

Si una tabla de este manual tuviera su columna clave con texto que NO parezca "código corto" (ej.
nombres en vez de códigos de 2-3 caracteres), la regla de la fase 2 no la reconocería como "fila de
datos nueva" y la trataría como continuación del encabezado. No se encontró ese caso en el
muestreo hecho hasta ahora en este manual — queda como riesgo conocido, no como bug.

### Pendiente

Revisar visualmente más páginas/tablas de este manual (no solo las 2 usadas como referencia) para
buscar casos que rompan el heurístico de "código corto" antes de dar por cerrado el Módulo 2, y
luego seguir con el Módulo 3 (Emparejamiento de bloques) para este mismo manual.

## 2026-08-12 — Riesgo aceptado del Módulo 2 confirmado como bug real, y arreglado

Se amplió la muestra: en vez de 2 tablas, se escanearon programáticamente las 158 páginas de la
edición `20260418` buscando filas multi-celda cuya primera celda NO matchea `CODE_LIKE`
(`^[A-Z0-9]{1,6}$`), filtrando falsos positivos (viñetas `●`, fragmentos de encabezado). El riesgo
aceptado ("una tabla keyed por nombre en vez de código corto") **se confirmó como bug real**, no
solo teórico:

- **`Country and Currency Codes`** (p.119-131, 13 páginas, ~180 filas): tabla de 6 columnas keyed
  por nombre de país ("Afghanistan", "Albania"...). Cada página entera colapsaba en **un solo
  bloque `table_header` gigante** en vez de 1 `table_row` por país — la fila de datos nunca
  disparaba `looks_like_code` porque la primera celda (nombre de país) nunca es un código corto.
- **`U.S. State Codes`** (p.133-135): mismo patrón, 50 estados/territorios colapsados.
- **Bonus**: `Retained and Returned Data Elements` (p.138-140) es una matriz de uso de campo por
  categoría (Field Name × Dispute Financials/Retrieval Requests/Fraud Advices, celdas X/Y/Z) — mismo
  problema de columna-clave-por-nombre. Confirma que el "Tipo H" (matriz de uso, visto antes solo en
  `base_i`) también aparece en `base_ii_clearing_data_codes`.

Como contraste, `Product ID Values` (p.65-67, ~50 filas) parseaba perfecto porque sus códigos
(`A`, `F2`, `Q6`...) sí matchean `CODE_LIKE`.

### Fix aplicado (`normalize.py`, función `build_blocks`)

Cambio de señal: en vez de "¿la PRIMERA celda de la fila parece código?", ahora es "¿ALGUNA celda
de la fila parece código?" (`has_code_cell = any(CODE_LIKE.match(l["text"]) for l in row_sorted)`).
Funciona porque en las filas rotas, aunque la 1ra celda sea un nombre, casi siempre hay una celda
hermana que sí es código corto (ej. `['Afghanistan', 'AF', '004', 'Afghani', 'AFN', '971']` — `AF`,
`004`, `AFN`, `971` matchean). Se agregó también una rama nueva: si `active_kind == "table_row"` y
la fila no tiene celda-código, se trata como **wrap de la fila de datos activa** (ej. "Antigua and"
+ "Barbuda" en renglones separados, o "No universal" + "currency" en columnas separadas) en vez de
reabrir un header nuevo — sin esto, cada wrap cortaba la tabla en un `table_header` espurio.

Verificado por trazado manual línea a línea de la p.119 completa (fila por fila, ver el row-by-row
dump que motivó el diseño) y confirmado sin regresión en las tablas ya validadas (p.31, p.101,
`Product ID Values` p.65-67) — se re-generaron las 9 ediciones con `python3 normalize.py` y se
inspeccionaron bloques post-fix.

**Riesgo residual aceptado del fix**: si un fragmento de encabezado wrappeado cae, por casualidad,
en un token corto todo-mayúsculas (ej. la sigla "ISO" sola en su propio renglón), se clasificaría
como celda-código y cortaría el encabezado antes de tiempo. No se observó este caso en el
muestreo hecho hasta ahora.

### Validación completa: las 9 ediciones, todas las páginas (no solo la edición más nueva)

Se corrió un script de validación estructural sobre los 9 JSON de `data/02_normalizacion_bloques/`
(post-fix), cruzando contra el `num_pages` real de cada edición en `data/01_ingesta_parseo/`:

- **Cobertura de páginas**: 0 páginas sin bloques en ninguna de las 9 ediciones.
- **Bloques vacíos**: 0 en las 9 ediciones (ningún `table_header`/`table_row`/`paragraph` con celdas
  vacías o solo whitespace).
- **Conteo de bloques por tipo estable**: `table_row` entre 1857-1895 por edición, `table_header`
  entre 212-244, proporcional al contenido — sin caídas abruptas que sugieran un parseo roto en
  alguna edición puntual.
- El fix del heurístico "código en cualquier celda" se comportó **igual en las 9 ediciones**: se
  verificó que `Country and Currency Codes` / `U.S. State Codes` generan filas limpias en todas
  (los números de página cambian levemente edición a edición porque el contenido crece, pero el
  patrón es estable — consistente con el hallazgo ya cerrado de que el shape no cambia por versión).

### Dos problemas nuevos encontrados durante la validación completa (NO relacionados al fix, quedan
abiertos)

1. **Glosario final del manual no se parsea como entradas estructuradas** (siempre las últimas
   ~14-22 páginas de cada edición, ej. p.137-158 en `20220423`, p.141-157 en `20260418`). Es una
   lista alfabética término→definición en prosa (ej. "account funding source" → "Identifies the
   source of the funds..."), sin ninguna columna que sea código corto — cae en el mismo hueco que el
   bug recién arreglado, pero aquí NO hay solución con la señal "código en cualquier celda" porque
   genuinamente no hay códigos en esa tabla. Termina como 1 bloque `table_header` gigante por página
   con todos los términos y definiciones de la página pegados. Confirmado presente, con el mismo
   patrón, en las 9 ediciones. No es prioritario para el objetivo del proyecto (diffear campos/
   posiciones) porque el glosario es prosa definicional, no una tabla de códigos — pero si en algún
   momento se quiere diffear el glosario, Módulo 2 necesita un tipo de bloque nuevo (algo como
   `definition_list`) con una señal de segmentación distinta (ej. términos en negrita/orden
   alfabético, no "código corto").
2. **Bug de continuidad de tabla entre páginas** (`H0 (continued)`, `Return/Reclassification Reason
   Codes`, ~p.92-94 según edición) — **ARREGLADO el mismo día (2026-08-12), a pedido explícito del
   usuario** (el glosario del punto 1 se dejó como TODO de prioridad baja, este no). Causa raíz: el
   código de error `H0` empieza en una página y su definición continúa en la siguiente con el
   literal `"H0 (continued)"` como primera celda tras el header re-declarado — no matchea
   `CODE_LIKE` (tiene paréntesis y minúsculas) y tampoco hay celda-código hermana en esa fila
   (columna 2 es una lista de viñetas), así que caía como continuación de header. Confirmado
   presente en 5 de las 9 ediciones (`20240413`, `20241019`, `20250412`, `20251018`, `20260418` —
   las 4 más viejas no tienen el caso porque el contenido de `H0` todavía entraba en 1 sola página
   en esas ediciones), siempre en la misma tabla.

   **Fix de 2 partes en `normalize.py`:**
   - `CONTINUED_CODE = re.compile(r"^([A-Z0-9]{1,6})\s*\(continued\)$", re.IGNORECASE)` — el patrón
     `"<codigo> (continued)"` es un literal explícito que el propio manual usa para marcar
     continuaciones, así que se reconoce directamente (más preciso que intentar generalizar
     `CODE_LIKE`). Se agregó como disparador adicional de `has_code_cell` en `build_blocks()`, para
     que la fila cierre como `table_row` propio en vez de fusionarse al header.
   - `_merge_continued_rows(blocks)` — pasada final sobre TODOS los bloques del documento (ya no por
     página): para cada `table_row` cuya 1ra celda matchea `CONTINUED_CODE`, busca hacia atrás (en
     una ventana de las últimas 50 bloques, `CONTINUED_ROW_SEARCH_WINDOW`, para no fusionar con un
     código repetido en una tabla lejana no relacionada) el `table_row` más reciente con el mismo
     código sin el sufijo, y le fusiona las celdas por columna (`\n`-joined) — si el número de
     columnas no coincide, no fusiona y deja la fila de continuación como bloque separado (fallback
     seguro). Se llama una sola vez al final de `normalize_edition()`, después de recorrer todas las
     páginas — el reseteo de estado por página (que sigue existiendo, no se tocó la arquitectura)
     deja de ser un problema porque el merge pasa por encima de esa frontera.

   **Validado:** re-generadas las 9 ediciones; en las 5 afectadas ahora hay exactamente 1
   `table_row` con `cells[0]=="H0"` (antes: 0, el contenido vivía disperso dentro de un
   `table_header`) que incluye toda la descripción original + el contenido que antes era
   `"(continued)"`. `0` bloques `table_header` con la palabra "continued" residual en las 9
   ediciones. Sin regresión: `pages_without_blocks=[]` y `empty_cell_blocks=0` en las 9, y el conteo
   de "real remaining suspects" (filas >6 líneas en un `table_header`, filtrando falsos positivos de
   viñetas) bajó en exactamente 1 en cada una de las 5 ediciones afectadas — los que quedan son
   solo páginas de glosario (punto 1, TODO de prioridad baja, no tocar por ahora).

### Mapeo del mismo patrón (columna clave sin código corto) en el resto de familias de manuales

Se escaneó la edición más reciente de las 10 manuales del repo (9 carpetas, una de las cuales
contiene 2 manuales distintos) buscando líneas consecutivas "palabra capitalizada" → "código corto"
(proxy liviano del mismo patrón, sin correr Módulo 1/2 completo ya que esos módulos todavía no
existen para estos manuales):

- **Aparece en las 10.** Los 2 manuales técnicos de `base_i` (VisaNet Auth-Only, 1242p; Full Service
  POS Technical, 1593p) tienen las mayores concentraciones (8,737 y 14,280 hits) — resultó ser que
  ambos incluyen su propio apéndice "Country and Currency Codes" (p.ej. p.1114-1121 y p.1420-1427),
  **la misma tabla y el mismo bug ya arreglado acá**, solo que en otro manual.
- **Verificación importante sobre el objetivo central del proyecto**: se inspeccionó la estructura
  real de la tabla "Record Layout" (grid Position/Field/Length/Format/Contents, Tipo A, en
  `base_ii_clearing_interchange_formats_tc_01_to_tc_49` p.371 — ej. fila `41  1  AN  Unattended
  Acceptance Terminal Indicator`). La columna `Format` (`AN`/`N`/`ANS`/`DX`/`UN`) está presente en
  **prácticamente todas las filas** de este tipo de tabla y siempre matchea `CODE_LIKE` — así que la
  señal "código en cualquier celda" (el fix de hoy) debería generalizar bien cuando se construya
  Módulo 2 para estos manuales, sin necesitar otro fix ad-hoc.
- **Nota de diseño a futuro (no implementar todavía)**: los rangos de posición (ej. `"45-69"`) no
  matchean `CODE_LIKE` por el guion — no bloquea nada porque `Format` cubre la fila, pero si algún
  día se necesita usar la posición misma como ancla de código, el regex va a necesitar aceptar
  guiones.

No se tocó código de otras familias — Módulo 1/2 solo existen para `base_ii_clearing_data_codes`.
Esto es catastro para cuando les toque su turno (ver roadmap: Tipo A es el siguiente paso
planeado).

## 2026-08-12 (cont.) — Módulo 3 (Emparejamiento de bloques) implementado y validado

Implementado en `poc/base_ii_clearing_data_codes/03_emparejamiento_bloques/match.py`. Toma la
secuencia plana de bloques del Módulo 2 (que no tiene noción de "tabla", solo `paragraph`/
`table_header`/`table_row` por página) y hace lo que el nombre del módulo promete: reconstruye la
entidad real a comparar (una tabla lógica, que puede repetir su título/header en cada página en la
que continúa) y empareja tablas + filas entre 2 ediciones consecutivas.

**Diseño:**
- **Identidad de tabla** = título (el `paragraph` inmediatamente anterior al `table_header`,
  normalizado). Confirmado empíricamente que el título se re-declara al tope de cada página en la
  que una tabla continúa (ej. "Country and Currency Codes" en 119-131), así que sirve como señal de
  continuidad más estable que comparar el contenido del header en sí.
- **Identidad de fila** = el código (1ra celda de `table_row`, normalizada) — consistente con el
  principio ya establecido en el proyecto de matchear por clave estable, no por nombre difuso
  ([[reference-pipeline-vs-technical-manuals]] en la memoria del asistente).
- **Emparejamiento de tablas**: exacto por título normalizado primero, `difflib.SequenceMatcher`
  (umbral 0.85) como fallback para detectar renombres.
- **Emparejamiento de filas**: exacto por código dentro de cada tabla ya emparejada.

**3 bugs encontrados y arreglados DURANTE la validación** (antes de dar el módulo por bueno, no
después):

1. **Tablas fantasma de 0 filas**: un `table_header` que nunca junta ningún `table_row` (el mismo
   falso positivo de párrafos-con-viñetas-mal-clasificados ya documentado en el Módulo 2, ej.
   `['l', 'Draft Data: TCR 5, Positions 145-148']`) generaba entradas de tabla vacías que
   contaminaban el emparejamiento con "agregados"/"eliminados"/"renombres" espurios entre texto
   narrativo. **Fix**: filtrar tablas con `len(rows) == 0` antes de emparejar. Esto solo bajó el
   conteo de tablas "reales" de 148-154 a 74-85 por edición y bajó drásticamente el ruido de fuzzy
   matches (de 29-50 por par a 0-4).
2. **Colisión de diccionario por título duplicado dentro de la misma edición**: en la edición
   `20230415`, la tabla "Country and Currency Codes" terminó partida en 4 segmentos (73+116+5+4=198
   filas) en vez de 1 solo, porque un nombre de país largo que envuelve en varias líneas (ej.
   "Bolivia (Plurinational State of)") ocasionalmente rompe el agrupamiento geométrico del Módulo 2
   y un fragmento sale como `paragraph` huérfano, contaminando momentáneamente el título pendiente.
   `match_tables` indexaba las tablas de cada edición en un diccionario por `title_norm` — con 4
   tablas con el mismo título, el diccionario se pisaba y solo sobrevivía la ÚLTIMA (4 filas),
   descartando 194 de 198 filas antes de siquiera intentar emparejar (esto generaba ~250 "filas
   agregadas" espurias contra la edición siguiente). **Fix**: `_coalesce_same_title()` fusiona,
   dentro de una misma edición, todas las tablas que comparten `title_norm` en una sola antes de
   emparejar. Bajó "Country and Currency Codes" de 251 filas agregadas espurias a 105 (ver punto
   siguiente sobre por qué ese número sigue elevado).
3. **Validación cruzada del fix de continuidad entre páginas** (el de `H0 (continued)` del punto
   anterior): confirmado que el código `H0` aparece como `matched-ok` (una sola fila estable) en los
   8 pares de ediciones, incluyendo los pares donde antes existía como texto disperso dentro de un
   `table_header` — prueba de que el fix de Módulo 2 alimenta correctamente a Módulo 3.

**Validación de plausibilidad** (no solo estructural, sino de contenido real): la tabla `Product ID
Values` muestra una progresión de altas de códigos de producto edición a edición (`X1`, `F2`, `F3`,
`G2`, `I3`, `L1`, `W1`...) consistente con cómo Visa efectivamente va agregando product IDs con el
tiempo — buena señal de que el emparejamiento está capturando cambios reales, no ruido.

**Hallazgo nuevo, NO arreglado (localizado, no sistémico) — pendiente de decidir prioridad con el
usuario:** después de los 2 fixes de arriba, el par `20230415→20231014` todavía muestra un conteo
elevado de filas agregadas/eliminadas en `Country and Currency Codes` (105/51, contra un rango
normal de 0-15 en el resto de pares). Investigado: ~30 de esas 51 "eliminadas" tienen códigos
absurdamente largos o multilínea (ej. `'BHUTAN BOLIVIA (PLURINA\xad'`, `'AG BARBUDA'`,
`'CABO VERDE CAYMAN ISLANDS'`) — son el mismo problema geométrico del punto 2 (nombres de país
multilínea que rompen el agrupamiento en la edición `20230415`), pero en los casos donde el
fragmento huérfano contaminó el título de una tabla ENTERA (no solo una fila) con basura como
`"(the)"` (22 filas), `"Miquelon"` (20 filas), o `"...tration Mission in\nKosovo (UNMIK)"` (12
filas) — esas tablas fantasma con título distinto no las agarra el fix de coalescing del punto 2
(que solo fusiona tablas que YA comparten el título correcto "Country and Currency Codes"), así que
ese contenido queda huérfano y aparece como tablas agregadas/eliminadas sueltas en el reporte
(visible en `tables_added`/`tables_removed` de `20230415_to_20231014.json`). **No se investigó ni
arregló la causa geométrica de fondo** (por qué esta edición en particular corta nombres de país
largos de esa forma) — es localizado a 1 de las 9 ediciones y a una sola familia de tablas
(nombres largos multilínea: países/estados/provincias), y arreglarlo de raíz requiere meterse de
nuevo en el agrupamiento por bandas Y del Módulo 2 para esa edición específica. Categoría similar al
TODO del glosario (gap de extracción localizado, no bloqueante para que el módulo funcione) — pero a
diferencia del glosario, sí afecta datos de una tabla de códigos real, así que no se asume
prioridad 0 sin preguntar.

**Ruido residual esperado, NO es un bug nuevo**: los pocos `fuzzy` matches y algunas entradas en
`tables_added`/`tables_removed` en cada par vienen del glosario (TODO ya deprioritizado) — algunos
términos del glosario son siglas cortas todo-mayúsculas (`PSIRF`, `RCRF`, `STIP`, `TCR`) que sí
matchean el heurístico de "código corto" del fix de país/estado, así que se separan como
`table_row` mientras el resto del glosario sigue tragado en un `table_header` — el título de esa
"tabla" termina siendo el blob de términos del glosario, que cambia levemente edición a edición y
genera fuzzy-matches obviamente identificables (título = lista de términos en minúscula, no un
nombre de tabla real). No se filtró a propósito, ya que tocar esto es exactamente el trabajo
pendiente del TODO del glosario, no de Módulo 3.

**Salida**: `poc/base_ii_clearing_data_codes/data/03_emparejamiento_bloques/<edicion_a>_to_
<edicion_b>.json`, uno por cada uno de los 8 pares consecutivos. Estructura: `tables_matched`
(con `match_type`, `fuzzy_ratio`, `rows_matched`/`rows_added`/`rows_removed`, `duplicate_codes_a/b`),
`tables_added`, `tables_removed`.

## 2026-08-12 (cont.) — Arreglada la causa raiz del problema de nombres largos envueltos en `20230415`

A pedido explicito del usuario, se investigo y arreglo (no se dejo como TODO) el hallazgo del
Modulo 3 sobre `Country and Currency Codes` en la edicion `20230415`. Se saco la geometria cruda
(bbox exacto) de varias filas rotas directamente del JSON de Modulo 1 para entender la causa raiz
en vez de asumirla.

**Causa raiz confirmada con coordenadas reales**: en las tablas `Country and Currency Codes`/`U.S.
State Codes` de esta edicion, cuando la columna clave (nombre de pais/estado) es larga y envuelve
en 2-3 lineas, el renderizado del PDF **centra verticalmente** las celdas de 1 sola linea (codigo,
moneda, etc.) respecto al nombre envuelto. Ejemplo real (`Bolivia (Plurinational State of)`,
pagina 118): la 1ra linea del nombre vive en Y=[536.1,548.1], sus celdas hermanas (codigo/moneda/
etc.) en Y=[542.1,554.1], y la 2da linea del nombre en Y=[548.1,560.1] — cada linea del nombre se
solapa con la fila de datos en exactamente 50% de su altura (6.0pt de 12.0pt), justo en el borde
del umbral `SAME_ROW_MIN_OVERLAP_RATIO=0.5` de `group_into_rows()`, asi que ninguna de las 2 lineas
del nombre se agrupaba con la fila de datos real. El codigo viejo de `build_blocks()` para lineas
sueltas asumia ciegamente "pertenece a la fila actualmente activa" (sin chequear que tan lejos
vertical mente esta), lo cual esta bien para el SUFIJO del wrap (la ultima linea, que
efectivamente completa la fila anterior) pero mal para el PREFIJO (la primera linea, que en
realidad es el comienzo de la fila SIGUIENTE, cuyas celdas hermanas todavia no se procesaron). Se
confirmo tambien un segundo sub-caso mas dificil: cuando 2 columnas DISTINTAS envuelven al mismo
tiempo en la misma banda Y (ej. pais "Cayman Islands" Y moneda "Cayman Islands Dollar" comparten
prefijo de wrap a la misma altura), `group_into_rows()` las agrupa en una sola fila multi-celda sin
codigo, que tambien puede pertenecer a la fila anterior o a la siguiente segun el caso.

**Fix implementado en `normalize.py`** (Modulo 2, no Modulo 3 — la causa es geometrica, de
reconstruccion de filas):
- `TABLE_ROW_GAP_MAX = 4.0` (calibrado: lineas de una misma celda envuelta quedan pegadas a ~0pt de
  hueco vertical; filas de datos distintas quedan separadas ~8.5pt en este manual — 4.0 separa
  ambos casos con margen).
- `build_blocks()` ahora recibe indice (`enumerate(rows)`) para poder mirar la fila SIGUIENTE
  (`rows[i+1]`) antes de decidir. Cuando una linea suelta (o un grupo multi-celda sin codigo) esta
  por fusionarse a la fila/header activo pero el hueco hasta esa fila activa es mayor a
  `TABLE_ROW_GAP_MAX`, se compara tambien el hueco hasta la fila SIGUIENTE; si ese hueco es menor,
  la linea/grupo se guarda en un buffer (`pending_prefix`) en vez de fusionarse ahora, y se
  antepone a la proxima fila cuando se procesa (que puede o no llegar todavia — por eso el buffer
  es una lista, no un solo valor).
- `_new_cells()` se cambio para fusionar lineas consecutivas (ordenadas por X) cuyo `x0` cae dentro
  de `CELL_X_MERGE_TOLERANCE=3.0` en una sola celda (antes creaba 1 celda por linea sin excepcion)
  — necesario para que el prefijo antepuesto se una correctamente a la 1ra linea real de esa
  columna en vez de contar como una columna extra.
- Red de seguridad: si `pending_prefix` queda sin resolver al terminar la pagina (no aparecio una
  fila siguiente que lo reclame), se emite como `paragraph` suelto en vez de perderse
  silenciosamente.

**Validado por trazado manual de coordenadas ANTES de implementar** (no solo despues): se
confirmaron a mano, con los numeros Y/X reales, los 4 casos de esta edicion —
`Bolivia (Plurinational State of)` (2 lineas), `Bonaire, Sint Eustatius and Saba` (3 lineas),
`Bosnia and Herzegovina` (2 lineas), y el caso de doble-columna simultanea `Cayman Islands`
(pais + moneda). Los 4 quedan reconstruidos correctamente tras el fix — verificado leyendo el JSON
de salida real, no solo revisando que el codigo "deberia" funcionar.

**Validacion de impacto de extremo a extremo** (Modulo 1 → Modulo 2 → Modulo 3, las 9 ediciones):
- Estructural: 0 paginas sin bloques, 0 bloques con celdas vacias en las 9 ediciones (sin
  regresion). `H0`/`H0 (continued)` sigue matcheando correctamente (1 sola fila) en las ediciones
  afectadas.
- El par `20230415→20231014` de Modulo 3, que motivo esta investigacion, bajo de **292 filas
  agregadas/24 eliminadas** (numero original antes de cualquier fix de esta sesion) a **30
  agregadas/19 eliminadas** — en linea con el resto de los pares (rango normal 6-67). Aislando solo
  la tabla `Country and Currency Codes`: de 105 agregadas/51 eliminadas a **3 agregadas/5
  eliminadas**.

**Residuo aceptado, NO arreglado (2 casos distintos, ambos chicos y de una categoria diferente a
la arreglada)**:
1. `"Cook Islands (the) CK"` — el propio PyMuPDF fusiono el nombre del pais y su codigo ISO en
   **una sola linea de texto** dentro del PDF (confirmado en el JSON crudo de Modulo 1: llega como
   `text='Cook Islands (the) CK'`, ya fusionado antes de que Modulo 2 vea nada). No es un bug de
   agrupamiento geometrico — es una limitacion de la extraccion de texto de esa linea puntual en el
   PDF original, fuera del alcance de un fix en `build_blocks()`.
2. ~4 filas restantes en `Country and Currency Codes` (`20230415→20231014`) vienen de texto de
   **notas al pie con superindices numéricos** (ej. la nota sobre la transicion de Kuna Croata
   HRK→Euro y de Sierra Leone SLL) que aparece pegado al final de la tabla, justo antes de que
   empiece "Canadian Province Codes" — una categoria de problema distinta (texto narrativo en el
   limite de una tabla, no un nombre de columna clave envuelto). No investigado a fondo — es un
   residuo pequeño (~2% de la tabla) y de otra naturaleza, no se justifico seguir en la misma
   sesion.

## 2026-08-12 (cont.) — Módulo 4 (Detección de cambios) implementado y validado

Implementado en `poc/base_ii_clearing_data_codes/04_deteccion_cambios/detect.py`. Toma la salida ya
emparejada del Módulo 3 (tablas/filas matched/added/removed) y la convierte en una lista plana de
"cambios" tipados — Módulo 3 ya resolvió el trabajo difícil (qué tabla/fila es la misma entre
ediciones), Módulo 4 solo decide SI hubo un cambio real de contenido y de qué categoría es. Sigue
siendo 100% determinístico, sin IA (eso es Módulo 5, que consumirá la salida de este módulo).

**Categorías de cambio** (adaptadas del pipeline de referencia a este manual de tablas de código,
no al Tipo A de grids posición/longitud/formato): nivel tabla — `table_added`, `table_removed`,
`table_renamed` (match fuzzy de título, ratio ya calculado por Módulo 3); nivel fila —
`code_added`, `code_removed`, `code_content_changed` (el código existe en ambas ediciones pero
alguna celda de contenido cambió); más `duplicate_code_warning` (aviso, no un cambio, cuando una
tabla tiene un código repetido en alguna edición — ya detectado por Módulo 3, solo se expone acá).

**Detección de `code_content_changed`**: compara celda a celda (saltando la celda 0, el código),
normalizando espacios en blanco antes de comparar. Si difiere, calcula
`difflib.SequenceMatcher.ratio()` — mismo mecanismo y mismo umbral (0.98) que el pipeline de
referencia usa en su Stage 5 (`05_diff_descriptors.py`) para descartar diffs de solo
reformateo/espaciado. Por debajo del umbral se reporta como cambio; por encima se descarta.
Deliberadamente NO intenta clasificar el cambio en "real" vs. "solo reescritura editorial" — esa es
la frontera de responsabilidad con el Módulo 5, que va a recibir el `similarity_ratio` como señal
de entrada.

**Validación de calidad del contenido detectado** (no solo conteo, se leyeron los diffs reales):
- `Business Application IDs`, código `MI`: descripción cambió de "Merchant Initiated Money
  Transfer" a "Merchant Initiated Faster Refund" (ratio 0.708) — redefinición real de negocio.
- `Maximum Credit and Debit, Prepaid, and Account Funding POS Transaction Limits`, códigos A/B/C/D:
  montos máximos subieron (ej. `USD$249,999.99`→`USD$749,999.99`, ratio 0.929) — exactamente el
  tipo de cambio de regla de negocio real que el proyecto necesita detectar.
- Los `table_renamed` (fuzzy) detectados en todos los pares son, sin excepción, ruido ya conocido
  del gap del glosario (títulos que en realidad son listas de términos) — consistente con lo ya
  documentado en Módulo 3, no un hallazgo nuevo.
- Los `duplicate_code_warning` son legítimos (ej. tablas tipo "Member Settlement Data-Record Type
  Codes" que agrupan sub-secciones con códigos cortos reutilizados como "01"-"04" bajo el mismo
  título) — comportamiento esperado, no revela un bug.

**Resultado por par** (8 pares): entre 14 y 241 cambios totales por par, con `code_content_changed`
variando bastante segun la edicion (0 a 121) — consistente con que estas son ediciones reales de
Visa con actualizaciones de contenido variables edicion a edicion, no ruido de extraccion (el
`code_content_changed` de mayor volumen, `20250412→20251018` con 121, se inspecciono a mano arriba
y son cambios de negocio genuinos).

**Salida**: `poc/base_ii_clearing_data_codes/data/04_deteccion_cambios/<edicion_a>_to_
<edicion_b>.json`, uno por cada uno de los 8 pares. Estructura: `summary` (conteo por
`change_type`) + `changes` (lista plana, cada entrada con `change_type` y sus campos propios).

**Cambio menor a Módulo 3 para soportar esto**: se agregó `header_a`/`header_b` (las columnas de
cada tabla emparejada) a la salida de `match.py`, que antes no las exponía — Módulo 4 las necesita
para etiquetar por nombre de columna cuál celda cambió, en vez de solo por índice numérico.

## 2026-08-12 (cont.) — Ollama instalado + Módulo 5 (Interpretación de cambios con IA)

**Setup de Ollama** (entorno: WSL2 Ubuntu sobre Windows, sin GPU NVIDIA detectada, systemd
habilitado en `/etc/wsl.conf`): instalado con el script oficial
(`curl -fsSL https://ollama.com/install.sh | sh`) — requiere sudo interactivo, lo corrió el usuario
en su propia terminal (no se pudo automatizar desde esta sesión sin credenciales cacheadas). Quedó
como servicio systemd (`systemctl status ollama`), escuchando en `127.0.0.1:11434`. Modelo bajado:
`qwen3:4b` (2.5GB, el mismo que usa el pipeline de referencia). Rendimiento en CPU: ~10-11s por
llamada con el modelo ya "caliente" (~6s extra la primera carga).

**Trampa encontrada y resuelta**: `qwen3:4b` tiene modo "thinking" activado por default. Con
`format:"json"` pero sin desactivar el thinking, el JSON queda en el campo `thinking` de la
respuesta, no en `response` -rompe cualquier parser que espere `response`. Fix: pasar
`"think": false` en el payload de `/api/generate`. Con eso el JSON sale limpio en `response`.

**Módulo 5 implementado** en `poc/base_ii_clearing_data_codes/05_interpretacion_cambios_ia/
classify.py`. Solo los cambios `code_content_changed` del Módulo 4 se mandan al LLM -las
decisiones estructurales (`table_added`/`table_removed`/`table_renamed`/`code_added`/
`code_removed`) siguen siendo 100% deterministicas y pasan sin tocar, mismo principio de
separación de responsabilidades que el pipeline de referencia.

**3 categorías** (no las 4 propuestas originalmente en la memoria del proyecto -`structural_change`,
`business_rule_change`, `editorial_reword`, `extraction_noise`-, se descartó `structural_change`
para este modulo): `business_rule_change`, `editorial_reword`, `extraction_noise`. Razon: a nivel de
fila de una tabla de codigos, un cambio "estructural" (alta/baja de codigo, tabla renombrada) ya lo
detecta el Modulo 4 de forma deterministica y nunca llega a este clasificador -solo le llegan
`code_content_changed`, que por definicion ya son texto de una celda que cambio, no altas/bajas.
Puede hacer falta reintroducir esa 4ta categoria cuando se construya Modulo 5 para un manual Tipo A
(grids de posicion), donde un cambio de longitud de campo si es "estructural" en un sentido que no
aplica a una tabla de codigos.

**Red de seguridad determinística** (`_find_disappeared_content`, tomada directamente del pipeline
de referencia -`detect_disappeared_content` en `06_classify_changes.py`-): si el LLM dice
`editorial_reword`/`extraction_noise` pero un tramo de 5+ palabras consecutivas del texto viejo no
tiene equivalente en el nuevo (via `difflib.SequenceMatcher` a nivel de palabra, buscando
operaciones "delete" largas), se anula la clasificacion del LLM y se fuerza `business_rule_change`
-queda registrado en `safety_net_override`/`ai_original_category` para trazabilidad.

**Validación de calidad, probado primero en un lote chico (6 items) antes de correr los 312
completos**: el LLM clasificó bien casos reales no triviales -`China`→`Mainland China` y
`Taiwan (Province of China)`→`Taiwan` como `business_rule_change` (cambios de nomenclatura real de
Visa), y `HRK`→`HRK1` como `extraction_noise` (correcto)-, pero se EQUIVOCÓ en 2 casos: clasificó
`CROATIA` código numérico `'191'`→`'1911'` y `SIERRA LEONE` `'SLL'`/`'694'`→`'3'` como
`business_rule_change` cuando en realidad son datos corrompidos por el mismo bug de notas al pie ya
documentado como TODO #3 (ver TODO.md) -el LLM no tiene forma de saber que "1911" o "3" son
fragmentos de una nota al pie sin mas contexto, y la red de seguridad de contenido-desaparecido
tampoco lo agarra porque el texto no "desaparece", se reemplaza por otra cosa corta. **Este hallazgo
subio la prioridad del TODO #3** (ya no es solo ruido de conteo de filas, corrompe contenido real de
filas ya emparejadas) — actualizado en TODO.md.

Corrida completa (8 pares, 312 items `code_content_changed`, ~10s c/u en CPU = ~50 min) lanzada en
background. Terminó exitosamente.

### Resultado final de la corrida completa (312 items, las 9 ediciones)

Distribución total: `business_rule_change`=193 (62%), `editorial_reword`=105 (34%),
`extraction_noise`=14 (4.5%). `safety_net_override` disparó 11 veces (~3.5% de los 312).

**Validación de calidad post-corrida** (se leyeron ejemplos reales, no solo los conteos):
- Los 3 ejemplos de `editorial_reword` inspeccionados en `Retired Chargeback Reason Codes` (códigos
  30/60/62) confirman que el LLM detecta correctamente cuando el ÚNICO cambio es el glifo de viñeta
  usado (`"l"` en ediciones viejas → `"●"` en ediciones nuevas — mismo contenido, distinto caracter
  Unicode de bullet) y no lo confunde con un cambio real. Buena señal de que el LLM esta juzgando
  semantica, no solo comparando strings.
- De los 11 `safety_net_override`, ~7 son catches legitimos de contenido sustantivo que
  desaparecio sin reemplazo (ej. notas explicativas completas, oraciones de clarificacion). Pero
  ~4 (los códigos `H0`/`HZ` de `Return/Reclassification Reason Codes`, que repiten en varios pares)
  disparan el override porque el "contenido desaparecido" detectado es literalmente
  `"l l l l l l l l l"` -una cadena de 9 caracteres de viñeta sueltos, sin texto real- porque esas
  filas tienen listas de campos EDQP con muchas viñetas cortas que se desalinean en el diff palabra
  por palabra. La clasificacion final (`business_rule_change`) sigue siendo defendible en la
  practica (esas filas SI tienen listas de campos distintas entre ediciones), pero el fragmento de
  evidencia que se guarda en `disappeared_content` no es informativo para un reporte humano.
  **Mejora pendiente, no implementada** (idea, no un bug urgente): filtrar tokens que sean
  puramente un glifo de viñeta repetido (`"l"`, `"●"`) antes de correr
  `_find_disappeared_content`, para que la evidencia guardada sea siempre texto sustantivo.

Salida en `data/05_interpretacion_cambios_ia/<edicion_a>_to_<edicion_b>.json` para los 8 pares,
misma estructura que Módulo 4 pero con `ai_category`/`ai_reason`/`disappeared_content`/
`safety_net_override` agregados a cada `code_content_changed`, y un `ai_summary` (conteo por
categoria IA) a nivel de par.

## 2026-08-12 (cont.) — Módulo 7 (Reporte de cambios) implementado (Módulo 6 salteado por ahora)

Módulo 6 (Validación con Plataforma STD) se salteo -sigue tentativo/sin definir, tal cual el plan
original del usuario- y se fue directo a Módulo 7, que consume la salida del Módulo 5 directo.

Implementado en `poc/base_ii_clearing_data_codes/07_reporte_cambios/report.py`. Genera un `.md` por
cada uno de los 8 pares de ediciones + un `index.md` con links y contadores. Principio de diseño: no
todos los cambios pesan lo mismo para un humano revisando el reporte -`code_content_changed` con
`ai_category == business_rule_change` va primero y con detalle completo (texto viejo/nuevo + razón
de la IA); `editorial_reword`/`extraction_noise` van en un apéndice compacto (solo código+columna+
ratio, sin repetir texto); altas/bajas de tabla/código van en secciones propias (son eventos
binarios, no hay matiz que juzgar); `duplicate_code_warning` y los `safety_net_override` van como
"Avisos de confiabilidad" al final, marcando donde desconfiar un poco mas de la deteccion
automatica. Los titulos de tabla anormalmente largos (>80 caracteres, casi siempre el gap del
glosario ya documentado) se truncan visualmente, no se ocultan -se decidio no esconder ningun dato
real, solo hacerlo legible.

**Validación de contenido leyendo el reporte real generado** (par `20250412→20251018`, el de mayor
volumen): se confirmaron cambios de negocio genuinos y verificables contra hechos reales conocidos
-`Sierra Leone` cambió su código de moneda de `SLL` a `SLE` (la redenominación real de la leona de
Sierra Leona), `Curaçao`/`Sint Maarten (Dutch Part)` cambiaron de `ANG` a `XCG` (el reemplazo real
del florín antillano por el florín caribeño en 2025)- ambos correctamente detectados y explicados
por el LLM sin que se le haya dado ese contexto historico, solo el diff de texto.

**2 observaciones nuevas, no arregladas (hallazgos de datos, no bugs de codigo del reporte)**:
1. El código numérico de moneda de `CROATIA` aparece corrompido (`'9782'` en vez de `'978'`) en la
   edición `20250412`, resolviendose reción en `20251018` -sugiere que la corrupción del bug de
   notas al pie (TODO #3) puede persistir en MAS ediciones de las originalmente acotadas a
   `20230415`, no solo esa una. No se investigó a fondo el alcance completo -queda anotado en
   TODO.md como ampliación de ese mismo item, no como item nuevo.
2. El LLM a veces "tipea mal" numeros grandes al repetirlos dentro del texto de `ai_reason` en
   español (ej. dice "USD$749,9.99" en la razón cuando el valor real -tomado directo del dato, no
   regenerado por el LLM- es "USD$749,999.99", que se ve correcto en los campos Antes/Ahora del
   reporte). No afecta la exactitud de los datos mostrados (`old`/`new` siempre vienen de la fuente,
   nunca del LLM), solo la prosa explicativa puede tener un typo de digitos. Cosmético, muy bajo
   impacto -un lector que mire el diff real (Antes/Ahora) no se ve afectado.

**Salida**: `poc/base_ii_clearing_data_codes/data/07_reporte_cambios/<edicion_a>_to_
<edicion_b>.md` (8 archivos) + `index.md`.

Con esto, el pipeline completo (Módulos 1-5 y 7) esta implementado y validado de punta a punta para
`base_ii_clearing_data_codes` -desde el PDF crudo hasta un reporte Markdown legible por humanos.

## 2026-08-12 (cont.) — Pendiente: próximo manual todavía sin elegir

El usuario pidió explícitamente dejar anotado que el siguiente paso es arrancar el mismo pipeline
para OTRO manual, pero que todavía no decidió cuál -lo va a indicar más adelante. **No asumir que es
un manual Tipo A ni ningún manual en particular** al retomar esta conversación. Preguntar primero
qué manual antes de arrancar trabajo especifico.

El código de `poc/base_ii_clearing_data_codes/` (Módulos 1-5 y 7) queda como patrón/referencia
reutilizable para ese próximo manual, no como plantilla rígida a copiar tal cual -cada manual tiene
su propio "shape" de contenido (catálogo de 8 tipos A/A'/A''/B/C/D/F/H, ver mas arriba en este mismo
archivo y en la memoria del asistente) y casi seguro va a necesitar su propia lógica de Módulo 1/2
de parseo, igual que le paso a este.

Ver `TODO.md` en esta misma carpeta para el índice corto de bugs pendientes (no relacionados a este
próximo paso) y `open_questions.md` en la memoria del asistente para el estado completo del roadmap.

## 2026-08-12 (cont.) — Arranca el segundo manual: `base_ii_clearing_edit_package_messages`, Módulo 1

El usuario eligió el próximo manual: `base_ii_clearing_edit_package_messages` (9 ediciones, mismo
rango de fechas `20220423`-`20260418` que `base_ii_clearing_data_codes`). Pidió explícitamente ir
**módulo por módulo**, aplicando lo aprendido -no repetir la corrida automática de 1→7 seguida que
se hizo para el primer manual, sino pausar y validar en cada paso.

Ya catalogado antes (ver más arriba en este archivo, tabla "Veredicto final de herramienta"): este
manual es **Tipo F** -"fichas" de código de error/edición, mismo patrón que las "Field ID cards" del
Tipo A pero con otro vocabulario de labels: `CÓDIGO` → `TÍTULO` (mayúsculas) → `Description:` →
`Action:` → `Transaction Types:` (lista con viñetas `●`). NO es una grilla multi-columna como el
Tipo B de `base_ii_clearing_data_codes` -es texto corrido con un patrón de label repetido, en
principio parseable por regex directo sobre el texto plano sin necesitar reconstrucción geométrica
de filas/celdas (a diferencia del Tipo B, que sí la necesitó).

**Módulo 1 implementado** en
`poc/base_ii_clearing_edit_package_messages/01_ingesta_parseo/ingest.py` -código casi idéntico al
de `base_ii_clearing_data_codes` (mismo esquema de salida, misma decisión de extraer a nivel de
LINEA con `page.get_text("dict")` en vez de bloque, por la misma razón ya documentada: evitar que el
agrupamiento heurístico de PyMuPDF fusione irreversiblemente texto de partes lógicas distintas de la
página). La extracción cruda no depende del "shape" del contenido -eso es trabajo del Módulo 2- así
que reusar el mismo Módulo 1 tal cual es la decisión correcta, no una casualidad.

**Corrida y validación**: las 9 ediciones procesaron sin avisos de tamaño de página inconsistente
(612x792 en todas). Manual bastante más grande que el primero: 333-347 páginas, ~12,100-12,630
líneas por edición (vs. ~150-158 páginas / ~9,000-10,100 líneas de `base_ii_clearing_data_codes`).
Se verificó contra una página real (p.50, edición `20260418`) que el patrón Tipo F se cumple
exactamente como estaba catalogado:
```
V0027                                                          (codigo)
BUSINESS APPLICATION ID IS INVALID FOR ARGENTINA DOMESTIC ...  (titulo, mayusculas)
Description: AFT Original and Reversal transactions...         (puede envolver 2+ lineas)
Action: Enter the correct value for the field.
Transaction Types:
●  Account Funding — Originals and Reversals
```
También se confirmó el patrón de encabezado/pie de página de este manual (distinto al de
`base_ii_clearing_data_codes`, va a necesitar su propia calibración de bandas Y en Módulo 2): header
en y0≈15-41 (incluye título de sección variable, ej. "Validation Messages" -no es fijo como en el
otro manual, va a repetirse pero cambiar de texto según la sección del manual), footer en y0≈758-772
(fecha, "Visa Confidential", número de página).

**Pendiente antes de pasar a Módulo 2**: catalogar el 2do formato de código mencionado en el
catálogo original (`######-I/S`, además de `V####`) y confirmar si son el mismo patrón de ficha o
uno distinto, y muestrear más páginas para calibrar las bandas de header/footer con confianza antes
de escribir el normalizador (mismo proceso de calibración que se hizo para el primer manual).

## 2026-08-12 (cont.) — Cerrando Módulo 1: estructura del documento, señal real de "código", fix al esquema

A pedido del usuario ("cerrar un poco más el Módulo 1"), se investigó a fondo antes de pasar a
Módulo 2, en vez de asumir que alcanzaba con el mismo esquema del primer manual.

### Estructura del documento (edición `20260418`, 346 páginas)

- p.1-4: portada + aviso legal (narrativa, ya conocido este tipo de contenido).
- p.5-38: tabla de contenidos (con dot-leaders, mismo patrón `TOC_DOT_LEADER` ya usado en el primer
  manual) — es GIGANTE (34 páginas) porque lista cada código individual con su número de página.
- **Capítulo 1** (p.39-40): overview narrativo, corto.
- **Capítulo 2 "Validation Messages"** (p.41-269, ~228 páginas): las fichas `V####` → TÍTULO
  (mayúsculas) → `Description:` → `Action:` → `Transaction Types:` (viñetas `●`) ya vistas.
- **Capítulo 3 "Log Messages"** (p.270-346, ~77 páginas): fichas `######-X` (6 dígitos + letra de
  severidad `I`/`W`/`C`/`E`/`S`/`A`, confirmado contra la tabla `Message Severity Levels` en p.271)
  → TÍTULO → `Description:` → `Action:` — **mismo patrón que el Capítulo 2 pero SIN la sección
  `Transaction Types:`** (los mensajes de log no están atados a un tipo de transacción).
  - Al principio del capítulo hay una tabla chica real de 2 columnas ("Message Severity Levels",
    Severity Level | Description, 6 filas) — estructura menor tipo B aislada, no domina el capítulo.
- p.344-346 (~3 páginas): **glosario** término→definición — misma categoría ya deprioritizada en
  el primer manual (TODO #1), acá mucho más chico en proporción al documento.

### La señal real para detectar un código NO es el patrón de texto, es la TIPOGRAFÍA

Un regex ingenuo de contenido (`^[A-Z]{0,2}\d{4,6}(-[A-Z])?$`) tiene falsos positivos reales: una
lista de MCCs envuelta en un párrafo de `Description:` produce una línea suelta `"5969"` (p.211,
edición `20260418`) que coincidiría con el patrón sin ser un código real -confirmado leyendo el
contexto completo, es literalmente un número de la lista "4815 or 5960 or 5962...".

Inspeccionando los spans de PyMuPDF (`page.get_text("dict")`, campo `size`/`font` por span) se
encontró la señal real, y es **inequívoca**: las líneas de código (`V0027`, `000001-I`, etc.) usan
tamaño de fuente **20.0pt** (el resto del documento usa 9-10.5pt para cuerpo y 26/30/40pt para
títulos de capítulo/sección -ningún encabezado usa exactamente 20pt, cero colisión). Los títulos de
ficha (mayúsculas) usan la fuente monoespaciada `CourierNewPS-BoldMT` -tampoco se usa en ningún
otro lugar del documento. Validado con `max_font_size==20.0` sobre TODA la edición `20260418`:
**952 líneas, 952 matchean el patrón de código (0 falsos positivos, 0 falsos negativos)** una vez
que el regex de validación se hace case-insensitive para la `V` (ver hallazgo siguiente).

**Hallazgo secundario**: existe al menos 1 código con `v` minúscula en el texto fuente (`v0720`,
p.175, edición `20260418`) -typo real de Visa en el documento, no un artefacto de extracción. La
señal tipográfica (tamaño 20pt) lo captura igual; un regex de contenido case-sensitive lo hubiera
perdido. Refuerza la decisión de usar tipografía como señal primaria y el regex de contenido solo
como confirmación/normalización secundaria (mayusculizar al extraer).

**Hallazgo importante para las 9 ediciones**: el NOMBRE de fuente de los códigos **cambió a mitad
de las 9 ediciones** -`SegoeUI-Bold` en `20220423`/`20221015`/`20230415`, `OpenSans-Bold` desde
`20231014` en adelante (rebrand de Visa)- pero el **tamaño (20.0pt) se mantuvo idéntico en las 9**.
La fuente del título de ficha (`CourierNewPS-BoldMT`) NO cambió, se mantuvo igual en las 9. **Esto
confirma que el parser de Módulo 2 debe usar `max_font_size==20.0` como señal primaria (portable
entre ediciones a pesar del rebrand), no el nombre de fuente**, que sí varía. El conteo de códigos
por edición crece de forma proporcional (933→952), consistente con que Visa agrega codigos nuevos
periodicamente -mismo patron ya visto en el primer manual.

### Bandas de header/footer (calibradas, distintas a las del primer manual -no reusar la constante)

Confirmado muestreando 6 páginas de ambos capítulos: header en `y1<=41` (2 líneas: título del
manual + nombre de sección variable, ej. "Validation Messages"/"Log Messages" -cambia según la
sección, a diferencia del primer manual donde el header era fijo), footer en `y0>=758.9` (fecha +
"Visa Confidential" + número de página). El footer arranca mas tarde que en el primer manual (758.9
vs. 745) -no se puede reusar la constante tal cual, hay que recalibrar por manual.

Las páginas que arrancan un capítulo nuevo (ej. p.270, "Chapter 3") NO tienen el header corrido de 2
líneas -el título grande del capítulo (40pt/30pt) ocupa ese espacio en su lugar- pero como ese
título arranca en y0≈46.5 (fuera de la banda `y1<=41`), el filtro por banda Y sigue funcionando
igual, este presente o no el header.

### Fix aplicado al esquema de salida de Módulo 1

`ingest.py` de este manual ahora guarda, ademas de lo que ya guardaba el del primer manual,
`max_font_size` (el tamaño maximo entre los spans de la linea -no un promedio, porque una linea
puede mezclar un span en negrita mas grande con el resto en tamaño normal, ej. "Description:") y
`fonts` (lista ordenada de nombres de fuente distintos en la linea). Se regeneraron las 9 ediciones
con el esquema nuevo. Esta es una diferencia real y justificada respecto al Modulo 1 de
`base_ii_clearing_data_codes` (que no necesita esto, su señal es geometrica) -no una copia
automática del primer manual: cada manual guarda lo que su propia señal estructural necesita.

### Módulo 2 implementado, validado y cerrado (mismo día)

Implementado en `poc/base_ii_clearing_edit_package_messages/02_normalizacion_bloques/normalize.py`.

**Diseño**: a diferencia del otro manual (grilla multi-columna, necesitaba reconstrucción
geométrica por solapamiento de banda Y), este es texto corrido de una sola columna -el orden
natural que entrega PyMuPDF por página ya coincide con el orden de lectura real una vez
filtrado el ruido de header/footer (verificado: sin filtrar, el header/footer de cada página
aparece al FINAL de esa página en el campo `order`, no al principio -por eso hay que filtrar
antes de confiar en el orden, no reordenar por (y0,x0) como en el otro manual). **Se procesa
el documento COMPLETO como un solo stream continuo, sin resetear estado por página** -aplicando
directamente la lección del bug de continuidad `"H0 (continued)"` del primer manual: si
`Description:`/`Action:` se corta justo en un salto de página, sigue acumulándose sin
importar el número de página, porque no hay ninguna frontera de estado ahí. Evita esa clase
entera de bug de raíz, no la vuelve a introducir para arreglar después.

Tipos de bloque: `card_header` (código+título), `field` (Description/Action, con su label),
`bullet_list` (Transaction Types, items), `paragraph` (todo lo demás: TOC no filtrado, aviso
legal, encabezados de capítulo/sección, glosario, tabla chica "Message Severity Levels").

**5 casos reales encontrados y arreglados, validando contra datos reales en cada paso (no
solo "debería andar")**:

1. **Bullet_list vacías (148-184 por edición antes del fix)**: `Transaction Types:` a veces
   trae el valor INLINE en la misma línea (`"Transaction Types: All Financial Drafts"`,
   `"Transaction Types: n/a"` -195 casos confirmados en la edición de referencia) en vez de
   una lista con viñetas. El código descartaba ese texto. Fix: si hay texto después de los
   dos puntos, se agrega como el primer item.
2. **Título truncado cuando envuelve a 2+ líneas** (ej. "CARD ACCEPTOR ID MUST NOT EQUAL
   SPACES FOR US EIRF ORIGINAL PURCHASE AND" / "REVERSAL TRANSACTION"): solo se capturaba la
   1ra línea, la 2da se perdía como un `paragraph` suelto. Fix: mientras la línea siguiente
   siga en la fuente monoespaciada del título, se sigue agregando al mismo título.
3. **2 códigos de 952 con el título en `OpenSans-Bold` en vez de la fuente monoespaciada**
   (inconsistencia real del PDF fuente, no artefacto de extracción) -el fix del punto 2 los
   perdía porque exigía esa fuente para la 1ra línea también. Fix: la 1ra línea después de un
   código SIEMPRE es el título sea cual sea su fuente (no hay ambigüedad posicional ahí); la
   fuente monoespaciada solo se exige para decidir si HAY continuación.
4. **3 variantes reales de la fuente monoespaciada** (`CourierNewPS-BoldMT`,
   `-BoldItalicM`, `-ItalicMT` -esta última usada para resaltar un placeholder "XXXX" dentro
   de un título envuelto). Fix: matchear por prefijo `"CourierNewPS"`, no por nombre exacto.
5. **1 código de 952 (`V9003`) usa tamaño 26.0 en vez de 20.0** -el mismo tamaño que los
   subtítulos de sección ("Problem Resolution", "Data Entry Messages", etc.), detectado
   comparando la lista completa de códigos del Módulo 2 contra el índice (TOC) de la edición
   -el único método que hubiera encontrado esto de forma sistemática, no muestreando a mano.
   Fix: aceptar tamaño 26.0 como código SOLO si el texto también matchea el patrón de código
   (`^[vV]\d{4}$|^\d{6}-[A-Z]$`) -una sección nunca lo hace, cero riesgo de colisión real.
   Efecto secundario del mismo hallazgo: sin una regla que corte el bloque activo al ver un
   subtítulo de sección grande, "Data Entry Messages" (26pt) se fusionaba como si fuera
   continuación de la viñeta anterior (`"n/a Data Entry Messages"`). Fix: cualquier línea con
   `max_font_size > 15` que no sea un código corta el bloque activo (el cuerpo normal de una
   ficha siempre es 9-10.5pt, así que "grande" es inequívocamente un límite de sección).
6. **`"Transaction Type:"` en singular** (1 caso, `V0549`) además del plural habitual
   `"Transaction Types:"` -el regex de labels no lo reconocía y su valor se fusionaba como
   continuación del campo `Action` anterior. Fix: aceptar la `s` final como opcional.

**Caso NO arreglado, es dato real, no un bug** (`V0545`): tiene el campo `Action:` literalmente
duplicado dos veces seguidas en el texto fuente del PDF (typo/copy-paste de Visa, verificado
en el texto crudo). El parser lo captura correctamente como 2 bloques `field` con label
`Action` -reflejar fielmente el dato es lo correcto, no es trabajo de Módulo 2 deduplicar
contenido editorial.

**Validación final** (las 9 ediciones, comparando contra el índice/TOC completo de cada una,
no solo una muestra): 0 códigos del TOC sin capturar, 0 títulos faltantes, 0 campos vacíos, 0
`bullet_list` vacías, 0 códigos duplicados (normalizando mayúsculas). Los "6 códigos de más"
que aparecían capturados pero no en el TOC en cada edición resultaron ser un falso positivo
del regex de validación (no del pipeline real): esos 6 códigos en el TOC tienen un espacio
extra antes de los puntos de relleno (`"V0158 . . . ."` en vez de `"V0158. . . ."`) que el
regex de chequeo -armado rápido para esta validación, no parte del pipeline- no contemplaba.
Verificado leyendo el PDF crudo, no es un problema real.

### Conclusión: Módulo 1 y 2 cerrados para este manual

Con esto, tanto Módulo 1 (extracción cruda + señal tipográfica validada) como Módulo 2
(reconstrucción de fichas: `card_header`/`field`/`bullet_list`/`paragraph`) quedan implementados
y validados de punta a punta contra las 9 ediciones completas -no una muestra- para
`base_ii_clearing_edit_package_messages`. Siguiente paso (no arrancado todavía, a pedido explícito
del usuario de ir módulo por módulo): Módulo 3 (Emparejamiento de bloques) para este manual.

## 2026-08-13 — Módulo 3 (Emparejamiento de bloques) implementado para `base_ii_clearing_edit_package_messages`, y 2 bugs reales de Módulo 2 encontrados y arreglados durante su validación

**Diseño de Módulo 3** (`poc/base_ii_clearing_edit_package_messages/03_emparejamiento_bloques/
match.py`): mucho más simple que el del manual 1 porque este manual no tiene el nivel intermedio
"tabla" -es una lista plana de ~933-953 fichas de código por edición. `extract_fichas()` recorre el
stream de bloques de Módulo 2 en orden: un `card_header` cierra la ficha activa y arranca una nueva;
los `field` se acumulan por etiqueta en listas (no un string único -ver por qué abajo); los
`bullet_list` se acumulan igual; los `paragraph` se ignoran (verificado con datos reales que siempre
caen ENTRE dos fichas, nunca interrumpiendo una a mitad de camino). `match_fichas()` empareja por
código EXACTO únicamente entre 2 ediciones -a diferencia del Módulo 3 del otro manual, acá no hace
falta fuzzy-matching de nombres: el código ES la identidad completa de la ficha, no hay un nivel de
"tabla" con título que pueda renombrarse. Validado antes de escribir el matching: 0 códigos
duplicados dentro de una misma edición en las 9 ediciones (a diferencia del otro manual, que sí
necesitaba lógica de detección de duplicados), toda ficha tiene exactamente 1 `Description` y al
menos 1 `Action`, ninguna ficha tiene más de 1 bloque `bullet_list`. El campo `action` se guarda como
LISTA (no string) a propósito: el código `V0545` tiene el campo `Action:` literalmente duplicado en
la fuente (ya documentado en Módulo 2, dato real no arreglado) y Módulo 3 preserva esa duplicación en
vez de perderla silenciosamente.

Corrida inicial sobre los 8 pares (9 ediciones): conteos de fichas agregadas/eliminadas creíbles
(ej. par `20220423→20221015`: 16 agregadas -todas códigos nuevos de una función coherente, recurring
payments India, `V1310`-`V1320`- y 2 eliminadas -códigos de chargeback reference number
retirados-), 0 códigos duplicados en ninguna edición. Pero al leer el CONTENIDO real de las fichas
"matched" para validar (no solo los conteos), aparecieron 428 fichas con description/action/título
distintos entre la primera y segunda edición del primer par -sospechosamente alto para 2 ediciones
consecutivas de un manual estable- y al leerlas, resultaron ser 2 bugs reales de Módulo 2, no cambios
de contenido genuinos:

**Bug 1 -filtro de footer con umbral demasiado ajustado (0.1pt).** `FOOTER_Y_MIN = 758.9` filtraba
la mayoría de las líneas de footer (fecha + "Visa Confidential" + número de página) pero no todas:
en varias ediciones esas líneas tienen `y0` tan bajo como 758.8 -0.1pt por debajo del umbral- y se
colaban como texto normal, pegándose al final del bloque `field`/`bullet_list` que estuviera activo
en ese momento cuando la página cambiaba. Ejemplo real confirmado con bbox crudo (ficha `000001-I`,
edición `20220423`, p.259): la línea de fecha (`bbox y0=758.8`) y el número de página (`bbox
y0=758.8`) se pegaron al final del campo `Description`, dejando `"...return message YYYY. 23 April
2022 259"` en vez del texto real. Recalibrado contra las 9 ediciones completas (no solo la de
referencia): el contenido real de página nunca pasa de `y0=709.2`, el footer real nunca baja de
`y0=758.8` -hay una banda vacía de ~50pt entre ambos- así que se bajó el umbral a `FOOTER_Y_MIN =
750.0`, con margen de sobra en las 2 direcciones. Antes del fix, 136-131 de las 224 fichas
"cambiadas" del primer par tenían esta contaminación (fecha/página pegada al texto).

**Bug 2 -2da línea del header también con banda mal calibrada, y solo contra la edición de
referencia.** `HEADER_Y_MAX = 41` se había calibrado sólo contra la edición más nueva (`20260418`,
`y1=41.0`) y las 3 más viejas (`y1=40.6`), pero las 5 ediciones del medio (`20231014` a `20251018`)
tienen esa línea (el título de sección corriente, "Validation Messages"/"Log Messages") a `y1=42.5`
-otro cambio de formato tipo "rebrand" no capturado la primera vez. Con el umbral viejo, esa línea se
colaba en 5 de 9 ediciones y se pegaba al bloque activo al cambiar de página -ejemplo real: el último
ítem de `Transaction Types` de la ficha `V0002` en `20251018` terminaba en `"...Original Credit —
Originals and Reversals Validation Messages"`. Recalibrado: el header real nunca pasa de `y1=42.5`,
el contenido real de página nunca empieza antes de `y0=45.9` -subido `HEADER_Y_MAX` a `44.0`, margen
en las 2 direcciones verificado contra las 9 ediciones.

**Bug 3 -el glifo de viñeta "●"/"■" solo se había validado contra la edición de referencia (la más
nueva).** Las otras 8 de 9 ediciones usan un glifo distinto para las viñetas de `Transaction Types`
que PyMuPDF extrae como la letra `"l"` suelta (fuente de símbolo, tamaño 8.0pt o 6.4pt -nunca al
tamaño de cuerpo normal 10.5pt, cero riesgo real de confundirlo con texto genuino). `BULLET_GLYPHS`
solo reconocía `{"●", "■"}`, así que en esas 8 ediciones cada viñeta de `Transaction Types` no se
reconocía como tal y el código caía en la rama de "seguir acumulando en el ítem activo" -fusionando
TODOS los ítems de la lista en un solo string gigante con las "l" mezcladas adentro, en vez de una
lista de ítems separados (ej. ficha `V0002`: `["l Sales Draft — Originals and Reversals l Account
Funding — Originals and Reversals ..."]` en vez de 4 ítems separados). Fix: agregar `"l"` a
`BULLET_GLYPHS`. Este bug es el que más volumen de "cambios" falsos generaba -383 de las 428 fichas
del primer par tenían SOLO este problema (misma lista de ítems, mal fusionada de un lado o del otro).

**Los 3 fixes son en `normalize.py` de Módulo 2** (no de Módulo 3) -Módulo 3 los expuso al comparar
contenido real entre ediciones, pero la causa raíz vivía en la reconstrucción de bloques. Mismo
patrón que ya pasó con el manual 1 (el bug `"H0 (continued)"` lo encontró Módulo 3, la causa vivía en
Módulo 2) -Módulo 3 sigue siendo, en este proyecto, el punto donde los bugs de calibración de Módulo
2 salen a la luz, porque recién ahí se compara contenido real entre 2 ediciones en vez de estructura
dentro de una sola.

**Validación post-fix, las 9 ediciones**: 0 fichas con contaminación de footer/header, mismos
conteos de fichas por edición (933-953, los fixes no tocan identidad de código/título, solo contenido
de campos), 0 duplicados, 0 campos/viñetas vacías. Re-corrido Módulo 3 sobre los 8 pares: conteos de
fichas agregadas/eliminadas sin cambios (como se esperaba). Los "cambios" de contenido en fichas
matched bajaron de 428 a 4 en el primer par, y de 539 a 23 en el último (`20251018→20260418`, el par
que cruza la transición de glifo `"l"`→`"●"` -el que más se beneficiaba del fix 3). Total de fichas
con contenido distinto entre los 8 pares, después de los 3 fixes: 4, 16, 25, 2, 41, 2, 0, 23 -rango
creíble para un manual estable, sin picos sospechosos.

**Lo que queda como "cambio" después de los 3 fixes es una mezcla esperada de 2 categorías**
(confirmado leyendo contenido real, no solo conteos), la misma distinción que el Módulo 4 del manual
1 ya sabe resolver con un umbral de similitud:
1. **Ruido cosmético real, no arreglado a propósito**: viñetas EMBEBIDAS dentro de un campo
   `Description`/`Action` (no el `bullet_list` dedicado de `Transaction Types`) siguen usando el
   glifo literal de esa edición (`"l"` viejo vs `"●"` nuevo) -esto es consistente en TODAS las
   ediciones, incluida la más nueva (ej. ficha `V0144`, "Mail/Telephone Electronic Commerce
   Indicator": la sub-lista de opciones 1-9 vive fusionada dentro del texto de `Description` con el
   glifo de esa edición inline, en `20260418` también, solo que con `"●"` en vez de `"l"`). No es un
   bug -Módulo 2 nunca prometió estructurar viñetas dentro de campos, solo el bloque dedicado
   `bullet_list`- y es exactamente el tipo de diferencia puramente tipográfica que el Módulo 4 (no
   construido todavía para este manual) debe descartar con un umbral de similitud, igual que hace con
   reformateos en el manual 1.
2. **Cambios de contenido genuinos**: confirmados a simple vista, ej. ficha `V0173` ("Cashback Amount
   must be less than..." → "...less than or equal to...", con la lista de `Transaction Types`
   ampliada de 1 a 2 ítems y el título actualizado a juego), ficha `V0180` (typo real corregido,
   `"Original Credti"` → `"Original Credit"`), ficha `103434-E` (espacio de más arreglado,
   `"1- character"` → `"1-character"`).

**Conclusión: Módulo 3 implementado y validado para `base_ii_clearing_edit_package_messages`.**
Salida en `data/03_emparejamiento_bloques/<edition_a>_to_<edition_b>.json` para los 8 pares. Los 3
bugs de Módulo 2 encontrados quedan arreglados (no son items de TODO.md -a diferencia de los bugs del
manual 1 que se dejaron pendientes, estos se arreglaron el mismo día por tocar datos reales de campos
que se van a comparar, mismo criterio de priorización ya establecido). Pausado antes de Módulo 4, a
pedido explícito del usuario de ir módulo por módulo con check-in en cada paso.

## 2026-08-13 (cont.) — Módulo 4 (Detección de cambios) implementado para `base_ii_clearing_edit_package_messages`

`poc/base_ii_clearing_edit_package_messages/04_deteccion_cambios/detect.py`. Mismo principio de
separación de responsabilidades que el Módulo 4 del manual 1 (decisión estructural
agregado/eliminado ya resuelta por Módulo 3; acá solo se decide SI hubo cambio de contenido en una
ficha ya emparejada y en qué campo -sigue siendo 100% determinístico, sin IA, eso es Módulo 5).

Diferencia de diseño respecto al Módulo 4 del manual 1: ese manual difea CELDAS por índice dentro de
una tabla con columnas variables; este manual no tiene tablas ni columnas -cada ficha tiene siempre
el mismo conjunto FIJO de 4 campos con nombre (`title`, `description`, `action`,
`transaction_types`), así que acá se diffea por NOMBRE de campo. Los 3 primeros son texto libre
(listas de 1+ string -collapsadas a un string canónico con join, sin deduplicar, preservando el caso
conocido de `Action:` duplicado en la fuente); `transaction_types` es una lista de listas de items
(uno por bloque `bullet_list`, casi siempre 0 o 1) -se aplana a una lista de items y se une con
`" | "` antes de comparar como texto. Mismo mecanismo y mismo umbral que el otro manual
(`difflib.SequenceMatcher`, 0.98) para separar ruido de formato de cambio real -no hace falta un
umbral nuevo, validado antes de fijarlo contra 4 casos reales conocidos de este manual: 2 casos de
solo espaciado (`"1- character"`→`"1-character"` ratio 0.995, un guión con espacio de más en
`V0115` ratio 0.993) quedan arriba del umbral y se descartan correctamente; 2 casos de cambio real
conocidos (`V0173` "less than"→"less than or equal to" ratio 0.948, `V0180` typo "Credti"→"Credit"
dentro de un item de `transaction_types` ratio 0.927) quedan abajo y se reportan correctamente.

Corrida sobre los 8 pares, sumario de cambios creíble y sin picos raros: `ficha_added`/
`ficha_removed` iguales a los conteos ya validados en Módulo 3 (por construcción, pasan derecho);
`ficha_content_changed` va de 0 (par `20250412→20251018`, ya visto en Módulo 3 como el único par sin
ningún cambio) a 33 (par `20221015→20230415`). Cero contaminación de footer/header/glosario residual
en los `old`/`new` de los cambios reportados (chequeado programáticamente contra los 8 archivos
completos, no una muestra).

Validado leyendo contenido real, no solo el sumario -el par con más volumen (`20221015→20230415`,
33 cambios en 15 fichas distintas) resultó ser mayormente UN cambio de negocio real propagado a
través de ~9 fichas relacionadas de Argentina NNSS (`V1232`-`V1245`): "Installment Payment
Indicator" renombrado a simplemente "Payment Indicator" en título+descripción+acción de cada ficha,
más una normalización ortográfica acompañante ("zeroes"→"zeros") -exactamente el tipo de cambio
editorial-pero-real, propagado y coherente entre fichas relacionadas, que un revisor humano
esperaría poder confirmar de un vistazo. También capturados correctamente: `V0313` (rango de valores
válidos ampliado de "0,1,3,4,5" a "0,1,3,4,5,6" en título Y descripción, más un cambio de
`transaction_types` con ratio 0.137 -claramente sustantivo, no ruido, correctamente NO descartado) y
`V1008` (título y descripción reescritos casi por completo, ratio ~0.5 en ambos -correctamente
detectado como cambio grande, no false-negative por casualidad de similitud alta).

**Conclusión: Módulo 4 implementado y validado para `base_ii_clearing_edit_package_messages`.**
Salida en `data/04_deteccion_cambios/<edition_a>_to_<edition_b>.json` para los 8 pares. No aparecieron
bugs nuevos de Módulos 1-3 durante esta validación (a diferencia de Módulo 3, que sí destapó 3 bugs
reales de Módulo 2) -señal de que el fix de los 3 bugs anteriores fue efectivo y no dejó residuos
visibles en este nivel. Pausado antes de Módulo 5 (Interpretación de cambios con IA), a pedido
explícito del usuario de ir módulo por módulo con check-in en cada paso.

## 2026-08-13 (cont.) — Módulo 5 (Interpretación de cambios con IA) implementado para `base_ii_clearing_edit_package_messages`, y un 4to bug real de Módulo 2 encontrado (via la red de seguridad) y arreglado

`poc/base_ii_clearing_edit_package_messages/05_interpretacion_cambios_ia/classify.py`. Mismo diseño
que el Módulo 5 del manual 1 (Ollama local, `qwen3:4b`, JSON forzado, `think:false`, temperatura 0;
mismas 3 categorías `business_rule_change`/`editorial_reword`/`extraction_noise`; misma red de
seguridad `_find_disappeared_content` con umbral de 5+ palabras). Única diferencia de diseño real: el
prompt no tiene "tabla" (no existe ese nivel acá) -en su lugar se le da al LLM el TITULO de la ficha
como contexto fijo (tomado de `title_b` en `fichas_matched` del Módulo 3, sin importar cuál campo
cambió) y el nombre del campo (`title`/`description`/`action`/`transaction_types`) en vez de
"columna".

Corrida de humo (`--only=20221015_to_20230415 --limit=6`) antes del batch completo: 5/6
`business_rule_change` correctos (expansión de rango de valores válidos, cambio real de
`transaction_types`), 1 `editorial_reword` correcto (solo cambia "EQUALS" por "EQUAL TO"). Un caso
sospechoso detectado a simple vista en esta corrida de humo: la ficha `V0407` tiene el MISMO cambio
de negocio real (de "IND EQUALS B OR P" a "IND EQUAL TO P" -se deja de aceptar el valor B) reflejado
en 2 campos (`title` y `description`); el campo `description` lo clasificó bien
(`business_rule_change`), pero el campo `title` lo clasificó mal (`editorial_reword`, con una
justificación que describe correctamente el cambio de texto pero saca la conclusión opuesta) -la red
de seguridad no lo agarra porque el tramo de palabras que desaparece (`"EQUALS B OR"`) tiene menos de
5 palabras. No es un bug de código -es una limitación conocida de usar un modelo chico (4B) en texto
corto, misma categoría que el "digit typo" ya documentado para el manual 1- pero como el mismo hecho
de negocio SÍ queda capturado correctamente en el campo `description` de la misma ficha, no se pierde
información en la práctica; se deja como observación, no como TODO nuevo (ítem de bajo impacto,
autocorregido por redundancia entre campos).

**4to bug real de Módulo 2 encontrado, esta vez leyendo la salida de la corrida completa (61 items,
8 pares) en vez de la corrida de humo**: la ficha `V0545` disparó la red de seguridad
(`safety_net_override=true`) en el par `20251018→20260418`, con `disappeared_content =
["Action: Enter the correct numeric value for this field."]` en el campo `description`. Investigado
el bbox crudo de Módulo 1: en 8 de las 9 ediciones (todas menos la más nueva, `20260418`, donde el
layout del PDF ya lo separa en su propia línea), la etiqueta `Action:` queda pegada al FINAL de la
línea de `Description:` en el PDF fuente (layout ajustado, sin salto de línea entre ambas), sin texto
después en esa misma línea física -el valor real de `Action` arranca en la línea siguiente.
`LABEL_PATTERN.match()` solo chequea que la etiqueta esté al PRINCIPIO de la línea, así que matcheaba
`Description:` correctamente pero el `rest` capturado se tragaba el `Action:` colgado como si fuera
parte del contenido de `Description` -confirmado programáticamente como el ÚNICO caso real en las 9
ediciones completas (0 ocurrencias de una 2da etiqueta fuera de esta ficha, en ninguna edición).

Fix general (no hardcodeado al código de esta ficha, siguiendo la misma filosofía que el resto del
proyecto): nuevo `TRAILING_LABEL_PATTERN` que detecta cuando el `rest` capturado por la etiqueta
principal termina en OTRA etiqueta sin texto después; si matchea, se corta el `rest` real ahí y se
arranca un 2do bloque (`field` o `bullet_list` según corresponda) para la etiqueta colgada, en vez de
absorberla como contenido de la primera. Refactor menor: se extrajo `_new_field_or_bullet()` para
reusar la lógica de creación de bloque en ambas ramas (etiqueta simple vs. etiqueta doble en la misma
línea).

Re-corridos Módulos 2→3→4→5 completos tras el fix. Módulo 2: +1 bloque por cada una de las 8
ediciones afectadas (el `Action` que ahora se separa correctamente), 0 duplicados/campos vacíos, `V0545`
verificado con la misma forma limpia en las 9 ediciones (Description sin "Action:" colgado, 2 bloques
`Action` idénticos -el duplicado real de la fuente, sin tocar). Módulo 3: conteos de fichas
agregadas/eliminadas sin cambios (identidad no se toca). Módulo 4: `ficha_content_changed` del par
`20251018→20260418` bajó de 11 a 9 (desaparece el falso cambio de `V0545`, que antes existía solo
porque una edición tenía el `Action:` corrupto y la otra no). Módulo 5 re-corrido sobre el total ya
corregido (59 items, no 61): `safety_net_override=0` en las 8 corridas -confirma que `V0545` era la
única corrupción real que la red de seguridad estaba compensando; ya no hace falta compensar nada.

**Resultado final, las 8 corridas**: `business_rule_change`=39, `editorial_reword`=20,
`extraction_noise`=0 (a diferencia del manual 1, que sí tuvo ~4.5% de `extraction_noise` -tiene
sentido: los 4 bugs de Módulo 2 ya arreglados eliminaron el ruido de extracción antes de llegar
acá, a diferencia del manual 1 donde el bleed de notas al pie sigue sin arreglarse y sigue generando
ruido real que el LLM tiene que absorber). Validado leyendo contenido real del par de mayor volumen
(`20251018→20260418`, tras el fix): un cambio de negocio real y coherente ("cashback amount must be
less than" → "...less than or equal to...") correctamente identificado y clasificado igual en 3
fichas relacionadas (`V0173`, `V0188`, `V1098`) a través de sus campos `title`/`description`/
`action`; y el ruido cosmético de glifo embebido conocido (`V1180`, viñetas `"l"` vs `"●"` dentro de
un campo `action`, ratio 0.972) correctamente clasificado como `editorial_reword`, con una razón que
describe con precisión que es solo un cambio de presentación. Output en
`data/05_interpretacion_cambios_ia/<edition_a>_to_<edition_b>.json` para los 8 pares.

**Conclusión: Módulo 5 implementado y validado para `base_ii_clearing_edit_package_messages`.** Van
4 bugs reales de Módulo 2 encontrados y arreglados durante la validación de Módulos 3-5 de este
manual (footer, header, glifo de viñeta, etiqueta colgada) -todos arreglados el mismo día por tocar
datos reales de campos comparados, mismo criterio de priorización ya establecido. Pausado antes de
Módulo 7 (Reporte de cambios) -Módulo 6 (Validación con Plataforma STD) sigue tentativo/sin definir,
mismo criterio que el manual 1-, a pedido explícito del usuario de ir módulo por módulo con check-in
en cada paso.

## 2026-08-13 (cont.) — Módulo 7 (Reporte de cambios) implementado para `base_ii_clearing_edit_package_messages` — pipeline completo (Módulos 1-5, 7) para este manual

`poc/base_ii_clearing_edit_package_messages/07_reporte_cambios/report.py`. Mismo principio de diseño
que el Módulo 7 del manual 1 (no todos los cambios pesan lo mismo: `business_rule_change` primero
con texto completo, `editorial_reword`/`extraction_noise` en apéndice compacto, altas/bajas en
secciones propias, avisos de confiabilidad al final) -Módulo 6 sigue salteado/tentativo, este módulo
consume directo la salida del Módulo 5.

3 diferencias de diseño respecto al Módulo 7 del manual 1, todas por la misma razón de fondo (este
manual no tiene nivel "tabla"): (1) se agrupa por FICHA (código), no por tabla -una ficha puede tener
varios campos cambiados a la vez y casi siempre es la MISMA historia de negocio contada en más de un
campo (ej. `V0173`: `title`+`description`+`transaction_types` cambiaron juntos), agruparlos bajo un
encabezado de ficha es más legible que listarlos sueltos; (2) los cambios de Módulo 4/5 no traen el
título de la ficha (no lo necesitaban para su trabajo) -el reporte lo carga aparte desde la salida ya
emparejada del Módulo 3 (mismo patrón que Módulo 5 ya usa para el prompt del LLM, `title_by_code`,
reutilizado acá); fichas agregadas/eliminadas sí traen su título directo en el cambio (Módulo 4 ya lo
incluye), no hace falta el lookup para esas secciones; (3) no hay
`table_added`/`table_removed`/`table_renamed` -solo `ficha_added`/`ficha_removed`-, y
`duplicate_code_warning` es UN aviso por par de ediciones (a nivel de todo el documento), no una
lista de tablas afectadas.

Corrida sobre los 8 pares sin errores, incluido el caso borde de 0 cambios (par
`20250412→20251018`, ya conocido desde Módulo 3) -las secciones vacías renderizan limpio (`_Ninguno
en este par de ediciones._`), sin romper el formato. Validado leyendo el reporte de mayor volumen
completo (`20221015→20230415`, 19 cambios de negocio): coherente y legible de punta a punta -la
misma historia de negocio real ("Installment Payment Indicator" → "Payment Indicator") queda contada
de forma consistente a través de sus ~9 fichas relacionadas, cada una agrupando sus campos afectados
bajo un solo encabezado; el caso ya documentado de Módulo 5 (ficha `V0407`, mismo hecho de negocio
clasificado bien en `Description` -aparece en "Cambios de negocio a revisar"- y mal en `Título`
-aparece en el apéndice como `editorial_reword`, ratio 0.97-) queda visible en el reporte real tal
cual se predijo en el TODO ([[pending-bug-fixes]] item 7), no es una sorpresa nueva. Índice
(`index.md`) también verificado, formato de fecha `DD/MM/AAAA` legible y conteos consistentes con los
de cada reporte individual.

**Conclusión: Módulo 7 implementado y validado para `base_ii_clearing_edit_package_messages` —
CIERRA EL PIPELINE COMPLETO (Módulos 1-5, 7) para este manual**, igual que ya estaba cerrado para
`base_ii_clearing_data_codes`. Módulo 6 (Validación con Plataforma STD) queda deliberadamente
salteado/tentativo en ambos manuales, sin definir, tal cual el plan original del usuario. Output en
`data/07_reporte_cambios/<edition_a>_to_<edition_b>.md` (8 archivos) + `index.md`.
Resumen de los 4 bugs reales de Módulo 2 encontrados y arreglados durante todo el trabajo de este
manual (Módulos 3 y 5): footer/header con bandas Y mal calibradas -0.1pt y ~2pt respectivamente,
calibradas solo contra la edición de referencia-, glifo de viñeta `"l"` de 8 de las 9 ediciones nunca
reconocido -también calibrado solo contra la edición de referencia-, y una etiqueta `"Action:"`
pegada al final de la línea de `Description:` en la ficha `V0545` en 8 de las 9 ediciones. Patrón que
se repite en los 4: el bug siempre se escondía en una calibración/heurística validada solo contra UNA
edición (casi siempre la más nueva) y nunca contra las 9 completas -lección para cualquier manual
futuro: validar señales de extracción/normalización contra el corpus completo de ediciones antes de
confiar en ellas, no solo contra la edición de referencia.

## 2026-08-13 (cont.) — Arranca el 3er manual: `base_ii_clearing_interchange_formats_tc_01_to_tc_49` (Tipo A). Módulo 1 implementado y validado

Elegido explícitamente por el usuario -es el manual Tipo A original del plan del proyecto (grids
Position/Field/Length/Format, el target central: campos "Reserved" en rangos de posición). Fuente en
`visa/src/base_ii/base_ii_clearing_interchange_formats_tc_01_to_tc_49/`, 9 ediciones, mismo patrón de
nombre de archivo que los otros 2 manuales.

**Módulo 1** (`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/01_ingesta_parseo/ingest.py`):
copia deliberada del Módulo 1 del primer manual (extracción a nivel de LINEA vía
`page.get_text("dict")`, bbox+texto únicamente, sin `max_font_size`/`fonts`) -mismo criterio ya
aplicado con el 2do manual: no se especula qué campos va a necesitar Módulo 2, se arranca con el
mínimo y se agrega lo que haga falta recién cuando el diseño real de Módulo 2 lo pida con datos
reales. Hay una pista a favor de que este manual SI alcance con geometría pura, sin señal
tipográfica (como el primer manual, no como el segundo): el mapeo cruzado de manuales ya hecho
[[pending-bug-fixes]] item 6) confirmó que la columna `Format` (`AN`/`N`/`ANS`/`DX`/`UN`) de este
tipo de tabla matchea el patrón `CODE_LIKE` ya usado en el primer manual -pero es solo una pista, no
una decisión tomada; se confirma recién al construir Módulo 2.

Corrida limpia en las 9 ediciones: 883-940 páginas (creciendo edición a edición, igual que los otros
2 manuales), 54,591-57,960 líneas -documento bastante más grande que los otros 2 (el primero tenía
~150-158 páginas, el segundo ~333-346). Tamaño de página consistente (612×792pt, carta US) en las 9
ediciones, sin avisos de tamaños mezclados.

Validado contra contenido real conocido: la fila `41 1 AN Unattended Acceptance Terminal Indicator`
en la página 371 de la edición `20260418` -ya inspeccionada en el mapeo cruzado de manuales previo,
antes de que existiera código para este manual- aparece extraída correctamente línea por línea, una
línea por CELDA (`Position`/`Field`/`Length`/`Format`/`Contents` como header en líneas separadas;
luego `41`/`1`/`AN`/`Unattended Acceptance Terminal Indicator` como 4 líneas separadas de la misma
fila, cada una con su propio bbox) -exactamente la granularidad que Módulo 2 va a necesitar para
reconstruir filas por solapamiento de banda Y, mismo enfoque que ya funcionó en el primer manual.

**Extendido a las 9 ediciones completas (2026-08-13, a pedido explícito del usuario -"¿lo probaste en
todas las ediciones?"-), no solo la de referencia**: la MISMA fila (`41`/`1`/`AN`/`Unattended
Acceptance Terminal Indicator`) se extrae correctamente en las 9 ediciones, cambiando solo de página
(347→372, crece con el documento) como es esperable -sin corrupción de contenido en ninguna. Chequeo
de completitud adicional en las 9: 0 páginas sin ninguna línea extraída en cualquiera de las 9
ediciones (`883` a `940` páginas totales cada una). Explícitamente se evita repetir el patrón de bug
ya visto 4 veces en el manual 2 (una señal/calibración validada solo contra la edición de referencia
resultando estar rota en el resto) -acá no hay calibración todavía (Módulo 1 es extracción cruda sin
heurísticos), pero se establece la disciplina de validar contra el corpus completo desde YA, no
recién cuando aparezca un bug.

Revisado el índice (TOC, p.5-6 en la edición de referencia) para entender la macro-estructura antes
de diseñar Módulo 2: confirma la numeración de sub-estructura ya anticipada en el roadmap ([[open-
questions-technical-manuals]] item 2, todavía sin catalogar formalmente) -capítulos por Código de
Transacción (TC 01/02/03, TC 04, TC 05...), y dentro de cada uno, sub-secciones por TCR (ej. "TC 05 -
TCR 0", "TC 05 - TCR 1 Additional Data", "TC 05 - TCR 2 Argentina..."). **Nota, no bug**: algunas
líneas del TOC tienen el número de página final aparentemente truncado o partido en 2 líneas (ej.
"TC 01, 02, 03 - TCR 0-8, D, E. . . . . . . . . 2" en vez de terminar en un número de 2 dígitos
creíble, y "TC 05 - TCR 2 Argentina. . . . . ." con el número "78" aislado en su propia línea
siguiente) -mismo tipo de ruido de TOC que los otros 2 manuales ya filtran con el patrón de puntos de
relleno en Módulo 2; no se investiga la causa exacta porque el contenido del TOC se descarta por
completo de todas formas, no es dato que el proyecto necesite.

**Conclusión: Módulo 1 implementado y validado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49`.**
Output en `data/01_ingesta_parseo/<edition>.json` para las 9 ediciones. Pausado antes de Módulo 2
(Normalización de bloques), a pedido explícito del usuario de ir módulo por módulo con check-in en
cada paso -mismo ritmo que se usó para el 2do manual.

## 2026-08-13 (cont.) — Módulo 2 implementado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49` (Tipo A), 8 bugs reales encontrados y arreglados

Modulo mas complejo de los 3 manuales hasta ahora: mezcla DOS patrones de contenido dentro de
CADA sección TC/TCR (confirmado con `fitz` directo antes de escribir codigo, ver docstring de
`normalize.py` para el detalle completo de las señales tipograficas usadas):

1. **Grilla "Record Layout"** (`Position | Field Length | Format | Contents`) -mismo tipo Tipo B
   que el manual 1, reconstruida geometricamente por banda Y.
2. **Fichas "Edit Criteria"** (nombre + `Positions:`/`Length:`/`Format:` a la izquierda,
   `Description:`/`Note:`/`Values:`/`Mapping:` a la derecha) -layout de 2 columnas, procesado con
   una maquina de estados secuencial (NO por banda Y: confirmado que agrupar por Y ahi produce
   parejas arbitrarias, ver mas abajo).

Se agregó `max_font_size`/`fonts` a Módulo 1 (decision tomada DESPUES de arrancar la exploracion
con solo bbox, igual que con el manual 2) al confirmar que hacian falta 5 niveles tipograficos
distintos para separar capitulo/sección/tabla/ficha/cuerpo.

**Los 8 bugs reales, todos encontrados corriendo el parser contra datos reales (no en la
exploración previa) y arreglados el mismo día:**

1. **Header de grilla con orden de columnas mal armado.** `Field` y `Length` NO son 2 columnas
   separadas -son un header de 2 líneas para UNA sola columna (cada fila de datos solo trae UN
   número entre Position y Format, nunca dos). Se fusionan en una celda fija `"Field Length"`, con
   orden de salida hardcodeado (no por X, porque `Length` esta geometricamente a la IZQUIERDA de
   `Field` en el PDF real pese a ir despues semanticamente).
2. **Número de página detectado por "última línea de la página" -asunción falsa.** `Visa
   Confidential` a veces tiene `y0` 0.1-1.1pt más alto que la fecha/número de página del mismo pie,
   así que ordena DESPUÉS y el número de página deja de ser la última línea. Recalibrado a
   detección por contenido+posición (dígitos cortos, x0 cerca del margen derecho, banda inferior)
   en vez de por posición en la lista.
3. **El título de tabla re-declarado al tope de cada página de continuación se colaba como fila de
   datos.** El modo "grilla" no cortaba hasta ver el próximo header de columnas, así que el título
   ("Transaction Data Record Layout", 10.5pt) quedaba absorbido en el buffer de la fila activa.
   Fix: el modo grilla corta explícitamente ante cualquier línea que no sea 9.0pt (el tamaño real,
   único, de las filas de datos).
4. **La `Description` de un campo comparte banda Y con su propio NOMBRE, así que llega ANTES que
   `Positions:` en el stream** -a diferencia de `Note:`/`Values:`/`Mapping:`, que comparten banda Y
   con `Positions:`/`Length:` y llegan después. Sin manejarlo, esa Description se perdía (no había
   ficha activa todavía para recibirla). Fix: buffer `pending_right` que la retiene hasta que
   `Positions:` crea la ficha y la reclama.
5. **La Description del campo N+1 se pegaba a la Description del campo N,** porque la ficha N
   sigue "activa" (no se cierra hasta ver SU PROPIO próximo `Positions:`) justo cuando llega la
   Description del campo N+1 (que comparte fila con el nombre de N+1, ver bug 4). Fix: chequeo
   `same_row_as_next_name` (¿hay un párrafo activo -candidato a nombre del próximo campo-
   compartiendo la misma banda Y que esta línea de columna derecha?) que redirige a `pending_right`
   en vez de a la ficha vieja. Aplica tanto a líneas CON etiqueta como a sus continuaciones
   envueltas sin etiqueta (bug simétrico, encontrado por separado: `pending_right` necesitaba
   prioridad sobre `active_card` en la rama de continuación, no solo en la de detección de
   etiqueta).
6. **El ":" a veces falta después de `Description`** en el PDF fuente -real, no artefacto de
   extracción, confirmado por código de carácter (`0x20` espacio, ningún separador alternativo): 9
   casos en la edición de referencia, concentrados en la página 91. Regex del lado derecho
   relajado a aceptar ":" O espacio como separador -pero SOLO del lado derecho: del lado izquierdo
   (`Positions:`/`Length:`/`Format:`) no hay ningún caso real, y relajarlo ahí generaría un falso
   positivo real (`"Format Code"`, nombre de campo real, se leería como la etiqueta `Format:` con
   resto `"Code"`).
7. **La Description a veces no tiene NINGUNA etiqueta**, ni siquiera sin los dos puntos -texto
   crudo directo en la columna derecha (ej. "Non-Fuel Product Code 1", p.196: el texto empieza
   directo con "This field contains..."). Detectado con el mismo chequeo `same_row_as_next_name`
   del bug 5: si una línea de columna derecha sin etiqueta comparte fila con el nombre del próximo
   campo, se interpreta como su Description implícita.
8. **Una celda `Contents` envuelta a una 2da línea a veces no solapa la banda Y de su fila** (las
   celdas de 1 sola línea -Position/FieldLength/Format- quedan más arriba) -mismo quirk ya visto y
   resuelto en el Módulo 2 del manual 1 (Tipo B), esta vez para la grilla de este manual: el hueco
   entre líneas de una misma celda envuelta es mínimo (~0pt, a veces hasta solapando levemente
   negativo), mientras que el hueco entre filas de datos distintas es ~8.3pt (confirmado con datos
   reales, p.79: `"Installment Payment Interest National Net Impact in IRF Calculation – IRF" /
   "Indicator"` se estaba cortando en 2 filas). Fix: fallback por hueco (`GRID_ROW_GAP_MAX=4.0`)
   cuando el solapamiento de banda Y ya dice "no es la misma fila".

**Validación final, las 9 ediciones completas (no una muestra)**: 0 `table_row` con cantidad de
celdas distinta a 4, 0 `table_header` con celdas inesperadas, 0 `field_card` con nombre vacío, 0
con posición vacía, 0 celdas `Position` de grilla que no matcheen el patrón de posición/rango (con
guion O en-dash), cantidad de `field_card`/`table_row`/`table_header`/`section_heading` creciendo
proporcionalmente edición a edición sin saltos raros. Solo 2 anomalías residuales de contenido REAL
de la fuente, no bugs (confirmadas leyendo el PDF crudo): `"Positions: Position: 122–123"` (label
duplicado en el texto fuente, p.114) y `"Positions: 24-27-"` (guión de más en el texto fuente,
p.234) -ambas de 1 sola ocurrencia, muy bajo impacto, no arregladas (mismo criterio que otros casos
de "dato real sucio" ya aceptados en el proyecto, ej. el Action duplicado de `V0545` en el manual
2). Validado también leyendo contenido real en varias secciones distintas del documento (TC 33.A
CP01 TCR0/TCR1, TC 05 TCR2 Chile/Brazil -confirmado el caso central del proyecto, filas `Reserved`
en rangos de posición-, capítulos cercanos al final del documento TC 48/TC 49) -todo coherente con
el PDF fuente en cada caso.

Patrón que se repite del manual 2: casi todos los bugs (2, 3, 4, 5, 7, 8) son casos donde 2 tipos
de contenido comparten una señal geométrica ambigua (misma banda Y, mismo hueco pequeño) y hace
falta una señal ADICIONAL (tamaño de fuente, o "¿qué hay actualmente en el otro buffer?") para
desambiguar -ningún heurístico geométrico simple alcanza solo, hay que combinar señales.

**Conclusión: Módulo 2 implementado y validado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49`.**
Salida en `data/02_normalizacion_bloques/<edition>.json` para las 9 ediciones. Bloques:
`section_heading`/`paragraph`/`table_header`/`table_row`/`field_card`. Pausado antes de Módulo 3
(Emparejamiento de bloques), a pedido explícito del usuario de ir módulo por módulo con check-in en
cada paso.

## 2026-08-13 (cont.) — Investigación del problema "chain-shift" + Módulo 3 implementado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49`, con 1 bug real de Módulo 2 encontrado (mismo día, antes de Módulo 3)

**Investigación empírica de chain-shift** (usuario pidió aclaración de qué era el problema y si ya
se había visto en el manual 1 -no, nunca: fue anotado en la conversación de diseño inicial del
11/08, antes de que existiera código, como problema anticipado SOLO para manuales Tipo A con
campos posicionales encadenados; ni el manual 1 -Tipo B, filas por código de negocio- ni el manual
2 -Tipo F, sin layout posicional- lo tenían). Comparando posiciones de fila entre secciones
comunes en los 8 pares de ediciones consecutivas (2173 comparaciones): **2172 de 2173 sin ningún
chain-shift**, la mayoría de los cambios de posición observados siendo en realidad el patrón
"`Reserved` (siempre al final del registro) se parte en un campo nuevo + un `Reserved` más chico",
que NO corre nada porque el campo nuevo se talla del INICIO del rango Reserved existente. Encontrado
exactamente **1 caso real** de chain-shift genuino en toda la historia (`TC 33.A - CP 12 TCR 4
Gateway Data, continuation`, par `20240413→20241019`: un campo creció de 9 a 10 bytes y corrió los
2 campos siguientes). Presentada la evidencia al usuario con una pregunta explícita
(`AskUserQuestion`): dado 0.05% de frecuencia real, ¿mitigar ahora con el ancla ordinal propuesta
en el diseño original, o emparejar por posición exacta sin mitigación? **Usuario eligió la opción
recomendada: sin mitigación** -mismo criterio de match-por-clave-estable ya usado en los otros 2
manuales, el caso raro queda como TODO documentado en vez de sumar complejidad ahora.

**Bug real de Módulo 2 encontrado explorando datos para diseñar Módulo 3** (antes de escribir
`match.py`, no después): la sección `TC 33 - TCR 0 Commercial Choice Select Reference Data Record`
mostraba una duplicación masiva de posiciones (7 filas con `Position="1-2"`, etc.) al hacer un
chequeo exploratorio de duplicados. Investigado: esta sección "grande" (26pt) en realidad contiene
VARIAS sub-secciones anidadas, cada una con su propio registro completo y numeración de Position
independiente (ej. "TC 33 - TCR 0 BASE II Dispute Financial Status Advice", "TC 33 - TCR 1 ...
(Cont'd)", "TC 33 - TCR 0 V.I.P. Full Service Dispute Financial Status Advice", etc.) -pero esos
sub-encabezados usan un tamaño de fuente MÁS CHICO (20.0pt) que el umbral calibrado originalmente
(`SECTION_HEADING_FONT_MIN=26.0`), así que Módulo 2 los dejaba caer como `paragraph` genérico en
vez de reconocerlos como `section_heading` -y todo su contenido (filas/fichas de 6 registros
distintos) quedaba mezclado bajo la sección grande, con posiciones repetidas 6-7 veces. Solo 6
apariciones en toda la edición de referencia (`^TC \d` a 20.0pt, vs 269 a 26.0pt), acotado a esta
sección. Fix en `normalize.py`: `SECTION_HEADING_FONT_MIN` (un valor único) reemplazado por
`SECTION_HEADING_FONT_SIZES = {20.0, 26.0}` (un conjunto), con la continuidad de título envuelto
ahora comparando contra el tamaño EXACTO de la instancia activa (`active_heading["size"]`) en vez
de una constante global -así una sección a 20pt no confunde su continuación con una a 26pt ni
viceversa. Re-corrido Módulo 2: conteo de `section_heading` pasó de 269 a 275 (269+6, exacto),
duplicación masiva de esa sección desaparecida, verificado explícitamente. Todavía queda 1 caso
residual de duplicación real (no bug) en `TC 39 - TCR 4 VDAS Forms Data, Exhibit Y or Exhibit 3C`:
filas con `Format="Group"` que introducen sub-estructuras ALTERNATIVAS mutuamente excluyentes
(ej. "Lodging Merchant" vs "Vehicle Leasing Merchant", ambas en las posiciones 12-68 porque son
interpretaciones distintas del mismo rango de bytes según el tipo de formulario) -confirmado real
leyendo el PDF, no arreglado, mismo criterio que otros "duplicados legítimos" ya aceptados
(`duplicate_codes`/`duplicate_row_positions` existen justamente para avisar de estos casos, no para
"arreglarlos").

**Módulo 3** (`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/03_emparejamiento_bloques/
match.py`): reconstruye secciones TC/TCR (delimitadas por `section_heading`, ya explícito desde
Módulo 2 -a diferencia del manual 1, acá no hace falta re-declarar/coalescer títulos vía
`paragraph`) con DOS listas paralelas: filas de grilla y fichas. Decisión de diseño explícita: NO
se enlazan filas con fichas dentro de este módulo -confirmado con datos reales que la relación no
siempre es 1:1 (un campo compuesto de la grilla, ej. "Acquirer Reference Number" 1 fila 27-49,
puede tener 1 ficha "padre" + 5 fichas "hijas" por sub-componente con sus propias posiciones más
chicas) y vincularlas exigiría lógica extra no justificada todavía por el objetivo del proyecto. Se
emparejan como 2 problemas paralelos independientes (filas contra filas, fichas contra fichas),
mismo patrón ya usado 2 veces en el proyecto (fila por código en manual 1, ficha por código en
manual 2), aplicado ahora 2 veces dentro de un mismo módulo. Clave de emparejamiento: `Position`/
`Positions` normalizada (unifica guión/en-dash -confirmado empíricamente 0 diferencia real en las 8
ediciones, se normaliza igual como seguro barato). Secciones emparejadas por título exacto + fuzzy
(umbral 0.85, igual que el manual 1).

Corrida sobre los 8 pares sin errores: ~97-99% de secciones emparejadas por título exacto por par,
1-3 fuzzy por par (revisados a mano, todos renombres reales creíbles, ej. agregar "E" a un rango de
TCRs, "TC 33"→"TC 33.B"), pocas altas/bajas de sección. Validado leyendo contenido real, no solo
conteos: el caso central del proyecto (`Reserved` 150-168 en TC33.A CP02 TCR0 partiéndose en `Tap-
to-Phone Indicator` 150 + `Reserved` 151-168 más chico) aparece correctamente reflejado tanto en
`rows_added`/`rows_removed` COMO en `cards_added`/`cards_removed` en paralelo, con la descripción
completa del campo nuevo capturada íntegra. Duplicados detectados: mismo conjunto estable de 7
secciones en los 8 pares (no varía por edición, confirma que es un rasgo estructural real de la
fuente, no un artefacto de extracción variable).

**Conclusión: Módulo 3 implementado y validado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49`.**
Salida en `data/03_emparejamiento_bloques/<edition_a>_to_<edition_b>.json` para los 8 pares. El
problema de chain-shift queda documentado como TODO de baja prioridad (0.05% de frecuencia real,
decisión explícita del usuario de no mitigarlo ahora). Pausado antes de Módulo 4 (Detección de
cambios), a pedido explícito del usuario de ir módulo por módulo con check-in en cada paso.

## 2026-08-13 (cont.) — Módulo 4 implementado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49`, con la categoría central del proyecto (`field_became_defined`) capturada explícitamente en 2 variantes

`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/04_deteccion_cambios/detect.py`. Mismo
principio de separación que los otros 2 manuales (decisión estructural ya resuelta por Módulo 3,
Módulo 4 solo decide si hubo cambio de contenido real). Diferencia de diseño: hay que diffear 2
listas paralelas por sección (filas de grilla + fichas) -se hace 2 veces, sin intentar unificarlas
(mismo criterio ya establecido en Módulo 3).

**Categoría nueva `field_became_defined`, el caso de uso central del proyecto, con 2 subtypes
distintos** (el 2do encontrado leyendo resultados reales de la primera corrida, no en el diseño
inicial):
1. **`subtype="split"`** (el caso ya visto en Módulo 3): un rango `Reserved` se parte en un campo
   nuevo + un `Reserved` más chico, con posiciones distintas antes/después. Detectado
   deterministicamente buscando, dentro de los `rows_removed`/`rows_added` (y lo mismo para
   fichas) ya calculados por Módulo 3, una fila `Reserved` removida cuyo rango CONTIENE el rango de
   una o más filas agregadas, con al menos una empezando en la misma posición inicial y contenido
   ya no "Reserved".
2. **`subtype="renamed_in_place"`** (bug/gap encontrado leyendo la salida real de la primera
   corrida de Módulo 4, no en la exploración previa): a veces el rango `Reserved` completo se
   renombra a un campo real SIN partirse -mismo rango de posiciones en ambas ediciones (ej. "TC 05
   - TCR 2 Colombia", `5-16 Reserved` → `5-16 Tip Amount`)- así que Módulo 3 ya lo empareja por
   posición exacta y sin este fix hubiera quedado escondido como un `row_content_changed`/
   `card_content_changed` genérico más, perdiendo justo la señal central del proyecto. Detectado
   directo en `rows_matched`/`cards_matched` (`_reserved_transition`), chequeado ANTES de caer en
   el diff genérico de celda/campo.
   **Agregado simétricamente `field_became_reserved`** (el caso inverso: un campo real se retira y
   su rango pasa a `Reserved`, ej. "TC 33.A - CP 12 TCR 2 Merchant Data", `5-34 Mastercard -
   Account Level Management Service Data` → `5-34 Reserved`) -mismo mecanismo, aunque no es el
   caso de uso central que motivó el proyecto.

Validación de integridad de conteos en los 8 pares completos (no una muestra): para cada par, la
suma de `row_added`/`row_removed` sueltos MÁS los campos consumidos por cada `field_became_defined`
(`subtype="split"`) reconciliaron EXACTO contra los totales `rows_added`/`rows_removed` de Módulo 3
-mismo chequeo para fichas- confirmando que no hay doble conteo ni items perdidos al consumir los
splits. Encontrado y arreglado en el camino: una comparación `not in` (por igualdad de valor) en vez
de identidad de objeto al calcular `remaining_reserved`, con riesgo teórico de excluir mal un
elemento si 2 filas agregadas tuvieran celdas idénticas por casualidad -cambiado a comparación por
identidad (`is`) antes de correr, no se detectó ningún caso real afectado pero se corrigió por las
dudas. También se sacó una línea muerta (variable sin uso) dejada de un borrador anterior.

Validado también leyendo contenido real: los 2 ejemplos ya conocidos de Módulo 3
(`field_became_defined`/`renamed_in_place` para "TC 05 - TCR 2 Colombia" y "TC 33 - TCR 1 BASE II
Clearing and Settlement Advice") aparecen correctamente clasificados, con la representación de fila
Y de ficha coincidiendo en AMBAS qué posiciones tuvieron una transición Reserved↔definido -señal
fuerte de que ambas extracciones paralelas del Módulo 2 (grilla y fichas) son mutuamente
consistentes, ya que se matchean por procesos totalmente independientes. `card_content_changed`
revisado a mano (6 ejemplos): cambios de negocio creíbles, ej. renombre real de campo ("Token
Assurance Level"→"Token Assurance Method", "Deferred OCT Request Type"→"Service Processing Type"
con reescritura de descripción a juego).

**Conclusión: Módulo 4 implementado y validado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49`.**
Salida en `data/04_deteccion_cambios/<edition_a>_to_<edition_b>.json` para los 8 pares. Pausado
antes de Módulo 5 (Interpretación de cambios con IA), a pedido explícito del usuario de ir módulo
por módulo con check-in en cada paso.

## 2026-08-13 (cont.) — Módulo 5 implementado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49`, con 2 patrones de `safety_net_override` alto investigados y explicados (ninguno es bug de código)

`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/05_interpretacion_cambios_ia/classify.py`.
Mismo diseño que los otros 2 manuales (Ollama local, `qwen3:4b`, mismas 3 categorías, misma red de
seguridad `_find_disappeared_content`). Solo `row_content_changed`/`card_content_changed` van al
LLM -las 2 variantes de `field_became_defined`/`field_became_reserved` ya son deterministicas.
Diferencia de diseño: el cambio en si no siempre trae el NOMBRE del campo como contexto (si la
columna/campo que cambió no es `Contents`/`name`) -se resuelve recargando la salida de Módulo 3
(`_field_name_lookup`, mismo patrón que `title_by_code` del manual 2) sin tocar el esquema ya
cerrado de Módulo 4.

Corrida completa sobre los 8 pares (554 items totales). `safety_net_override` salió mucho más alto
en 2 pares (19 en `20230415→20231014`, 33 en `20251018→20260418`) que en cualquier corrida previa
de los otros 2 manuales (ahí siempre 0-1) -investigado a fondo ANTES de dar Módulo 5 por cerrado,
mismo criterio de esta sesión de no ignorar una señal rara solo porque "el mecanismo ya está
validado en otro manual".

**Caso 1 (par `20230415→20231014`, 19 overrides) -cambio editorial real, no bug.** Varios campos de
la sección "Fleet Service" (`TC 05 - TCR 3`) perdieron su lista de `Values:` enumerada (ej. "1 =
Fuel Purchase 2 = Non-Fuel Purchase..."), reemplazada por una referencia cruzada en la Description
("See BASE II Clearing Data Codes for a listing of valid codes."). Confirmado en el PDF crudo de
`20231014`: el texto fuente YA NO tiene ningún `Values:` para estos campos, solo la referencia
cruzada -Visa reescribió esta sección para dejar de duplicar la enumeración inline. La red de
seguridad hizo exactamente lo que debía: detectó contenido real desaparecido sin reemplazo directo
y lo marcó `business_rule_change` en vez de confiar en que el LLM lo llamara "reword" solo porque
hay una oración de reemplazo.

**Caso 2 (par `20251018→20260418`, 33 overrides) -limitación real del PDF fuente de UNA edición,
tampoco bug de código.** Muchos `note` de fichas en secciones no relacionadas entre sí (TC 05 TCR0,
TC 05 TCR2 Colombia/Japón, TC 20 TCR0, TC 33, TC 33.A CP01 TCR1...) aparecían vacíos en la edición
más nueva. Investigado con datos crudos de Módulo 1: el span en NEGRITA que renderiza la palabra
"Note:" (ej. `['OpenSans-Bold','OpenSans-Italic','OpenSans-Regular']` en la edición vieja) está
directamente AUSENTE de la capa de texto de la edición `20260418` -el resto del texto (itálica +
regular) SÍ se extrae bien, solo falta el prefijo "Note:" mismo, así que Módulo 2 no tiene ninguna
etiqueta para disparar la captura como campo `note` separado y el texto queda fusionado como
continuación de `description`. Cuantificado en las 9 ediciones completas: 274/274/274/274/274/
272/273/273 apariciones de `"Note:"` en las primeras 8 ediciones, **216 en la edición más nueva**
-una caída de ~57 casos (~21%), única y exclusiva de `20260418`. No es un bug de mi parser -es un
problema de generación/renderizado del PDF fuente en esa edición puntual, no recuperable con
extracción de texto normal (haría falta OCR, fuera de alcance). No afecta el dato central del
proyecto (Position/Length/Format/Contents), solo la prosa complementaria de `Note:`. La red de
seguridad sigue funcionando como red de seguridad: el contenido perdido se marca para revisión
humana en vez de perderse silenciosamente. No arreglado -no hay nada arreglable en el pipeline,
sería necesario un PDF fuente distinto- documentado como limitación conocida.

**Resultado final, las 8 corridas**: `business_rule_change`=301, `editorial_reword`=241,
`extraction_noise`=12, total 554. Validado leyendo contenido real (además de los 2 casos de
override investigados a fondo): el contexto de nombre de campo (`_field_name_lookup`) resuelto
correctamente incluso para renombres del propio campo (ej. "Token Assurance Level"→"Token Assurance
Method" muestra `field_name="Token Assurance Method"`, el nombre YA actualizado, consistente con
`title_b` del otro manual). Output en `data/05_interpretacion_cambios_ia/<edition_a>_to_<edition_b>.json`
para los 8 pares.

**Conclusión: Módulo 5 implementado y validado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49`.**
Pausado antes de Módulo 7 (Reporte de cambios) -Módulo 6 sigue tentativo/sin definir, mismo criterio
que los otros 2 manuales-, a pedido explícito del usuario de ir módulo por módulo con check-in en
cada paso.

## 2026-08-13 (cont.) — Módulo 7 implementado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49` — PIPELINE COMPLETO (Módulos 1-5, 7) para los 3 manuales del proyecto

`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/07_reporte_cambios/report.py`. Mismo
principio de diseño que los otros 2 manuales (no todos los cambios pesan igual), con una prioridad
nueva: **`field_became_defined`/`field_became_reserved` van PRIMERO en el reporte**, antes que los
cambios de negocio genéricos -es el caso de uso central del proyecto, se le da su propia sección
prominente en vez de mezclarlo. Los cambios de contenido (`row_content_changed`/
`card_content_changed`) con `ai_category == business_rule_change` se agrupan por CAMPO (sección +
posición, usando `field_name` que Módulo 5 ya resolvió), no por fila y ficha por separado -así el
lector ve de un vistazo que la grilla y la ficha describen el mismo cambio.

**Deduplicación fila/ficha para `field_became_defined`/`field_became_reserved`**: Módulo 4 emite 2
entradas por evento (`kind="row"` y `kind="card"`, detectadas en paralelo sobre las 2
representaciones del mismo campo, sin enlazarlas -ver Módulo 3/4). Mostrar ambas por separado en el
reporte sería redundante -se deduplican por (título, posición), prefiriendo la versión de grilla y
mencionando "(confirmado en grilla y ficha)" cuando ambas coinciden.

Corrida sobre los 8 pares sin errores. Leído el reporte completo del primer par
(`20220423→20221015`) de punta a punta: las 3 transiciones Reserved→definido aparecen con full
detalle (posición partida, campo nuevo, Reserved restante, confirmado en ambas representaciones);
la sección de cambios de negocio revela un hallazgo real interesante no visto antes en la
validación de módulos anteriores -Visa modernizó terminología de forma consistente en DECENAS de
campos no relacionados entre sí, cambiando "chargeback or representment" por "dispute or dispute
response" en las descripciones (ej. `TC 38`, `TC 39`, múltiples TCRs)- correctamente detectado como
`business_rule_change` en cada instancia. Los 2 casos ⚠️ (`safety_net_override`) del par
(`TC 42, 43 - TCR 0 Record 1/2`) son limpiezas editoriales reales (se sacó una referencia cruzada a
otro manual), correctamente re-clasificados. Secciones agregadas/eliminadas/renombradas,
apéndice de redacción/ruido, y avisos de confiabilidad (duplicados) todos coherentes y legibles.

**Conclusión: Módulo 7 implementado y validado para `base_ii_clearing_interchange_formats_tc_01_to_tc_49`
— CIERRA EL PIPELINE COMPLETO (Módulos 1-5, 7) para este manual**, mismo hito ya alcanzado para
`base_ii_clearing_data_codes` y `base_ii_clearing_edit_package_messages`. Módulo 6 queda
deliberadamente salteado/tentativo en los 3 manuales, sin definir. Output en
`data/07_reporte_cambios/<edition_a>_to_<edition_b>.md` (8 archivos) + `index.md`.

**Con esto, los 3 manuales elegidos hasta ahora (Tipo B, Tipo F, Tipo A) tienen pipeline completo
de punta a punta, validado con datos reales en cada paso.** Balance de bugs reales encontrados y
arreglados en este 3er manual: 8 en Módulo 2 (el más complejo hasta ahora, mezcla 2 patrones de
contenido por sección), 1 en Módulo 2 encontrado explorando datos para Módulo 3 (encabezados
anidados a 20pt), 2 correcciones menores en Módulo 4 (identidad vs igualdad, línea muerta) -y 2
investigaciones a fondo de señales raras que resultaron NO ser bugs (chain-shift, confirmado real
pero rarísimo con decisión explícita del usuario de no mitigar; y el `safety_net_override` alto de
Módulo 5, resuelto como 1 cambio editorial real + 1 limitación real del PDF fuente de una edición
puntual). Sin próximo paso concreto decidido todavía -consultar con el usuario si sigue con un 4to
manual o vuelve a algo pendiente de los 3 ya cerrados.

## 2026-08-19 — 4to manual: `base_ii_clearing_interchange_formats_tc_50_to_tc_92` (hermano directo del 3ro), pipeline completo (Módulos 1-5, 7)

Hermano directo del 3er manual: misma serie de documento "BASE II Clearing Interchange
Formats", mismos 9 ediciones/8 pares, capítulos TC 50-92 en vez de TC 01-49. Módulo 1/2
reusaron el diseño del 3er manual, confirmando con datos reales (no asumiendo) que aplicaba:
mismos tamaños de fuente (40/30/26/10.5/9.5/9.0pt), pero se confirmó explícitamente que el 3er
nivel de encabezado a 20pt (nested sub-records) del 3er manual NO existe acá (0 resultados
buscando `^TC \d` @ 20pt en las 9 ediciones) -no se copió a ciegas.

**Bug real encontrado y arreglado en Módulo 3 (data-loss, no cosmético)**: la sección
`"TC 57 - TCR 5 - Limited Use Data"` aparece 2 veces seguidas con título Y párrafo
introductorio idénticos, pero 2 tablas "Record Layout" con campos completamente distintos
(posición 168 = `Reserved` en una, `Reimbursement Attribute` en la otra). El diseño original de
`match_sections` (heredado del 3er manual) arma un dict simple `{título: sección}` -con 2
secciones de título idéntico en la misma edición, la 2da pisaría silenciosamente a la 1ra,
perdiendo un layout entero del diffing en las 8 comparaciones. Arreglado emparejando secciones
de título repetido por ORDEN DE APARICIÓN (1ra↔1ra, 2da↔2da) en vez de por título solo; se
agregó `duplicate_section_paths`/`duplicate_row_keys` (según el módulo) al output para que la
ambigüedad quede visible, nunca oculta. Confirmado el fix funciona: posición 168 matchea
`Reserved↔Reserved` en la 1ra copia y `Reimbursement Attribute↔Reimbursement Attribute` en la
2da, en las 8 comparaciones. La ambigüedad semántica de "cuál copia es cuál" sigue sin resolver
(TODO.md item 10).

Módulo 4/5/7 reusan el diseño del 3er manual sin cambios de fondo. 2 bugs cosméticos más
encontrados leyendo reportes reales de Módulo 5/7 (no en la exploración previa): el título de
la tabla-ficha filtrándose en la `description` del primer campo cuando el wrap cae justo antes
(TODO.md item 11, 3/9 ediciones, 1 campo), y una ficha con lista `Values:` larga fragmentada en
varios `field_card` por salto de página, con "(continued)" redeclarado en el PDF fuente
(TODO.md item 12, 1 edición, 1 campo -con un caso hermano en otra sección que investigado a
fondo resultó ser un cambio editorial real de Visa, no el mismo bug, no confundirlos).

Módulo 5 sobre las 8 corridas: `business_rule_change`=9, `editorial_reword`=17,
`safety_net_override`=1 (investigado, cambio editorial real, no bug). **Hallazgo distintivo de
este manual: 0 transiciones Reserved→definido** en las 8 ediciones disponibles -a diferencia
del 3er manual que tuvo varias. El mecanismo de emparejamiento por posición ya está probado
funcionando (confirmado con el caso `TC 57`), simplemente los capítulos TC 50-92 no tuvieron
ese tipo de cambio en esta ventana de tiempo. Módulo 7 leyó el reporte más nutrido de punta a
punta: encontró un hallazgo real coherente -el campo `Transaction Component Sequence Number` @
posición 4 cambió de `unpacked numeric` a `alphanumeric` SIMULTÁNEAMENTE en 5 secciones TC 50
distintas (variantes TCR 0/1/2), correctamente clasificado como cambio de negocio en las 5.

**Pipeline completo (Módulos 1-5, 7) para este 4to manual, mismo hito que los 3 anteriores.**
Módulo 6 sigue tentativo/sin definir. Detalle completo del bug de `TC 57` y su fix en
`match.py` del propio manual (docstring extenso); ver también memoria del asistente
(`open_questions.md`) para la investigación completa turno por turno.

## 2026-08-19 (cont.) — 5to manual: `base_ii_transactions_quick_reference`, pipeline completo (Módulos 1-5 con Módulo 5 no-op, y 7)

Manual NUEVO (no hermano de ninguno anterior), forma de contenido genuinamente distinta a los 4
manuales previos: un listado de referencia rápida de 2 niveles (código TC de 45 entradas +
lista de filas TCR con descripción, `"NN Nombre"` a 12pt + filas `TCR`/descripción a 10.5pt),
SIN grilla Position/Length/Format ni concepto de campo "Reserved" -confirmado explorando el PDF
antes de decidir el enfoque (documento mucho más chico, 20-24 páginas, 8 ediciones en vez de 9).

**Bug real encontrado y arreglado en la 1ra validación de Módulo 2 (data corruption)**: filas
TCR que cruzan un salto de página se fusionaban en un solo bloque ilegible (9 filas reales de
`"33 Multipurpose Message"` cruzando de la página 15 a la 16 colapsadas en una sola). Causa:
el fallback de "hueco mínimo = wrap de celda" (heredado sin cambios de los manuales de grilla)
no chequeaba que las 2 líneas comparadas estuvieran en la MISMA página -al cruzar un salto de
página, el Y de la página nueva arranca chico (~50-70pt) mientras el `ref_y1` de la última fila
de la página anterior está cerca del pie (~700-750pt), dando un hueco NEGATIVO que igual pasaba
el umbral `<= GRID_ROW_GAP_MAX` sin querer. A diferencia de los manuales de grilla (donde el
título de tabla se re-declara al tope de cada página y corta el buffer GRATIS vía el chequeo de
tamaño de fuente), este manual no redeclara nada entre páginas -el corte de página explícito
que ahí era gratis acá hizo falta agregarlo a mano. **Casi se introduce un bug nuevo al
arreglar este**: un primer intento agregó un límite inferior `gap >= 0` como "segunda
salvaguarda", que rompió un wrap LEGÍTIMO dentro de la misma página (líneas envueltas con
interlineado ajustado pueden solaparse levemente, gap negativo pero real) -detectado al
re-validar, sacado (el chequeo de página solo ya alcanza).

**Diseño de Módulo 3 distinto, decidido con evidencia real, no asumido**: comparando
similitud `difflib` entre TODAS las descripciones de una misma sección, aparecen decenas de
pares de filas GENUINAMENTE DISTINTAS con similitud ≥0.85 (ej. `"Batch Disposition Code A"`
vs `"...Code R"` = 0.958; países como Rusia vs Uruguay = 0.862) -un fuzzy matching por
descripción (el mismo mecanismo que sí funciona bien para títulos de sección en los otros 4
manuales) sería inseguro acá, arriesgando emparejar por error 2 filas que son entidades
distintas. Tampoco alcanza el TCR solo como clave (se repite, ej. `"TCR 0"` 9 veces en una
sección con 9 descripciones distintas) ni la descripción sola (mismo texto exacto aparece 2
veces bajo TCR distinto). Clave final: `(TCR, descripción)` compuesta, EXACTA, sin fuzzy -un
rename real se ve como baja+alta en vez de "cambio de contenido", aceptado deliberadamente
(mismo principio que la decisión de no mitigar el chain-shift en el 3er manual). Validado el
diseño investigando 3 diffs grandes y no obvios (renombre "Chargeback"→"Dispute" en 6 TC,
renombre "Single Message System Interface"→"Supplemental Financial Data" en 18 filas, y un
salto grande de 471→243 filas matcheadas que resultó ser un agregado real de prefijos de país a
las descripciones "National Settlement, X") -los 3 confirmados reales, no bugs.

Discutido con el usuario (con ejemplos concretos) por qué Módulo 5 no tiene ningún
`row_content_changed` que clasificar dado el diseño de la clave -el usuario propuso contar TCR
por TC como alternativa de validación, confirmado que eso YA está disponible sin mecanismo
nuevo (delta computable directo de Módulo 3/4), pero un delta de 0 puede esconder 1 baja+1 alta
(un rename). **Decisión final: Módulo 5 se deja como archivo vacío/no-op** por consistencia de
estructura del pipeline (copia el output de Módulo 4 sin tocar, con un aviso defensivo si algún
día aparece un `row_content_changed` real -no debería pasar nunca con este diseño).

Módulo 7 diseñado con la vista que pidió el usuario: por cada TC afectado, cantidad de TCR
antes→después con el delta, SIEMPRE acompañado del detalle de filas agregadas/eliminadas (nunca
solo el número), marcando ⚠️ cuando el delta neto es 0 pero hay altas Y bajas a la vez (posible
rename no detectado). Validado leyendo 2 reportes completos: el caso Chargeback→Dispute se ve
correcto a nivel TC, y los 9 casos de rename SMS-interface muestran el ⚠️ correctamente.

**Pipeline completo (Módulos 1-5 con Módulo 5 no-op deliberado, y 7) para este 5to manual.**
Único bug real quedó arreglado en el momento (no diferido). Detalle completo en `match.py`/
`normalize.py` del propio manual y en la memoria del asistente (`open_questions.md`).

## 2026-08-19 (cont.) — 6to manual: `international_full_service_pos_online_messages_processing_specifications` (`base_i`), 1er manual NARRATIVO del proyecto, pipeline completo (Módulos 1-5, 7)

Primer manual de naturaleza fundamentalmente narrativa (232 páginas de reglas de negocio y
flujos de procesamiento en prosa, casi sin tablas de campos -solo 7 de 232 páginas mencionan
"Position"/"TCR"/"Reserved", y son menciones incidentales dentro de prosa, no estructura
tabular real, confirmado leyendo el PDF antes de decidir el enfoque). El usuario eligió
explícitamente (`AskUserQuestion`) diffear a nivel de párrafo/sección con clasificación IA en
vez de tablas de campos -opción presentada junto con "pausar y elegir otro manual con tablas",
el usuario prefirió seguir con este.

Jerarquía real de 3 niveles de encabezado (26.0/20.0/14.0pt) capturada en un stream PLANO
(`section_heading` con campo `level`, sin árbol real -mismo criterio de no sobre-diseñar sin
necesidad demostrada ya aplicado en los otros manuales). Contenido bajo 9.0pt confirmado ruido
de diagrama/viñeta (glifos de vineta, fragmentos de flowchart), filtrado. Parrafos
reconstruidos por adyacencia geométrica X/Y -el mecanismo "catch-all" de los otros manuales acá
es el mecanismo PRINCIPAL, no un caso de borde.

**Clave de emparejamiento de secciones: RUTA jerárquica completa (L1>L2>L3), no título suelto**
-decidido con datos reales: títulos de nivel 2 se repiten SISTEMÁTICAMENTE bajo distintos
capítulos padre (7 de 80 títulos L2 repetidos, ej. "Cardholder Transactions" aparece bajo
"Transaction Types" Y bajo "Standard Processing", 2 secciones genuinamente distintas -a
diferencia del caso aislado `TC 57` del 4to manual, acá la repetición es un patrón estructural
esperable, no una rareza).

**Bug real encontrado tras correr Módulo 5 con un `safety_net_override` sospechosamente alto
(18/124 = 14.5% en el primer par, vs 0-2 normal en los otros manuales) -investigado a fondo en
vez de aceptar la corrida como validada**: el mismo párrafo real puede quedar cortado DISTINTO
entre 2 ediciones -una oración corta tipo "intro de lista" (termina en `:`, antecede una lista)
a veces queda fusionada al párrafo anterior en una edición y separada en la otra, no por un
cambio de contenido sino por dónde cae el salto de página (confirmado leyendo líneas crudas de
Módulo 1: "VMP accounts can be used for the following:" fluye sin corte en una edición pero
cae justo al tope de la página siguiente en la otra -probablemente una regla de paginación
"keep with next" del generador de PDF de Visa, protegiendo la intro de quedar huérfana).

Se investigó primero si un fix GEOMÉTRICO en Módulo 2 (ej. "cerca del margen inferior + cerca
del margen superior") serviría -rechazado: el caso real rompe a página nueva con y1=671.7 en
una página donde cabían ~80pt más de contenido, consistente con "keep with next" empujando la
intro ANTES de quedarse sin espacio, no por falta de espacio real -la posición Y no es una
señal confiable acá. **Arreglado en Módulo 3 en cambio** (`_reflow_matches`): antes del
emparejamiento normal exacto/fuzzy, busca pares de párrafos ADYACENTES de un lado que,
concatenados, matchean EXACTO a un párrafo suelto del otro lado -mismo contenido, solo
re-cortado distinto, nunca se reporta como cambio real (expuesto como `paragraphs_reflowed`
separado, nunca mezclado con matches reales).

Presentado el hallazgo al usuario con recomendación de fix acotado vs. dejarlo para después
(`AskUserQuestion`) -eligió el fix ahora. Validado el impacto real: 60 de 124 párrafos
previamente fuzzy/added/removed reconciliados como puro reflow en el primer par,
`safety_net_override` bajó 29→14 en total (18→7 en el primer par). Investigando el residuo
restante se encontró que el fix es real pero INCOMPLETO -quedan variantes 2↔2 (fusión+re-
división distinta) y ruido de "guion con espacio extra" de PDF (`"non-USD"` vs `"non- USD"`,
rompe el match exacto por 1 carácter). Presentado de nuevo al usuario (`AskUserQuestion`): ¿
seguir invirtiendo en un algoritmo general de realineación N:M, o aceptar la mejora ya lograda?
**El usuario eligió aceptar y seguir** -residuo documentado como TODO.md item 13, no resuelto
más en la POC.

Módulo 7 leyó el reporte más nutrido de punta a punta: hallazgo real y coherente pese al ruido
residual -8 párrafos en 5 secciones distintas muestran el mismo renombre de sistema real
(`"Exception File"` → `"Account Screen Authorization File (ASAF)"`), todos correctamente
clasificados como `business_rule_change`, ninguno afectado por el ruido de reflow (los casos
⚠️ quedan claramente separados aparte).

**Pipeline completo (Módulos 1-5, 7) para este 6to manual, 1ero de la categoría narrativa.**
Módulo 6 sigue tentativo. Único bug real quedó parcialmente arreglado por decisión explícita
del usuario (mejora real aceptada, residuo diferido -TODO.md item 13). Detalle completo en
`match.py`/`normalize.py` del propio manual y en la memoria del asistente
(`manual6_narrative_progress.md`).

## 2026-08-19 (cont.) — 7mo manual: `visanet_settlement_service_vss_user_guide_volume_1_specifications` (`vss`), el manual más complejo del proyecto hasta ahora, pipeline completo (Módulos 1-5, 7)

Mezcla prosa narrativa (como el 6to manual) con 2 tipos de contenido ROTADO 90° dentro del PDF
-descubierto investigando, no asumido: volcados de reportes tipo mainframe/terminal (marcados
explícitamente `"This Data is Fictitious and for Illustration Purposes Only."`, descartables) y
tablas de referencia real `Field Name`/`Description` dentro de exhibits `"Example N:
Reconciliation of X Report to Y Report"`.

**Corrección de hipótesis a mitad de camino, presentada al usuario antes de seguir
(`AskUserQuestion`)**: la hipótesis inicial ("el contenido rotado es un capítulo legado que
solo existe en ediciones viejas 2022-2023, landscape completo, y desaparece en 2025+") resultó
PARCIALMENTE incorrecta -es verdad que las páginas COMPLETAS en landscape desaparecen (0 en
`20251017`), pero el contenido ROTADO en sí persiste en TODAS las ediciones, solo empaquetado
distinto (páginas landscape completas en 2022, bloques rotados dentro de páginas retrato en
ediciones nuevas). El usuario, con el dato corregido, eligió reconstruir los pares de
referencia real (`Field Name`/`Description`) en vez de descartar todo el contenido rotado como
se había planeado originalmente.

**Geometría de texto rotado investigada con datos reales de 2 tablas distintas ANTES de
programar** (Módulo 2, `_extract_rotated_pairs`): para texto rotado (`dir=(0.0,-1.0)` en vez de
`(1.0,0.0)` horizontal, confirmado vía el vector de PyMuPDF) los ejes quedan efectivamente
transpuestos -"misma fila, distinta columna" (en términos sin rotar) se ve como "mismo `x0`
(banda de fila), distinto rango `y1` (banda de columna)". Columnas ("Field Name" vs
"Description") calculadas POR PÁGINA, no como constante global (confirmado que varían
levemente entre tablas: 717.0/574.5 en una, 717.0/576.3 en otra). Espaciado de fila consistente
(~20.5pt) confirmado en ambas tablas revisadas.

**3 bugs reales encontrados y arreglados en las primeras validaciones, antes de reportar cada
módulo como listo:**
1. **Contaminación entre 2 tablas rotadas distintas (Módulo 2)**: las mismas bandas de tamaño
   de fuente (9.0/9.5pt rotado) también las usaba OTRA tabla totalmente distinta y descartable
   -el listado de jerarquía de ejemplo del capítulo de reportes (ej. p.61, encabezado literal
   `"Field"` solo, mapeando ID de SRE a nombre de banco/procesador de ejemplo). Primera corrida
   produjo 484 pares con 220 descripciones vacías (45%) -investigado, encontrada la causa
   raíz, arreglado exigiendo el literal EXACTO de 2 palabras `"Field Name"` presente en la
   página antes de procesar cualquier par de ella (la tabla real SIEMPRE redeclara ese literal
   en cada página de continuación, la descartable usa `"Field"` solo). Re-corrida: 236 pares,
   con la mayoría de las descripciones vacías restantes (56%) siendo sub-encabezados
   estructurales legítimos (`"Row"`/`"Column"`, 23 apariciones cada uno), no fallos de
   emparejamiento.
2. **Orden de pares roto en todo el stream (Módulo 2)**: el primer par extraído aparecía en el
   índice 1 del stream de bloques, ANTES del primer `section_heading` -el `order` de cada par
   se calculaba buscando la 1ra línea HORIZONTAL de su misma página, pero páginas enteras
   dentro de una tabla "Example N" no tienen ninguna línea horizontal, cayendo al default `0`.
   Arreglado usando el `order` propio de la línea rotada del par (`name_line["order"]`, ya
   presente en el output de Módulo 1) en vez de un proxy que podía no existir en esa página.
3. **Salto real de jerarquía de encabezados (Módulo 3, crash en la 1ra corrida)**:
   `"Related Information"` aparece como encabezado de NIVEL 3 directamente bajo un nivel 1, SIN
   nivel 2 intermedio -confirmado el mismo patrón exacto en las 6 ediciones, bajo 4 capítulos
   distintos (`"VSS Implementation Methods"`, `"VSS Funds Transfer Point Identification"`,
   `"VSS Testing"`, `"VSS Implementation Timelines"`). `extract_sections` construía la ruta
   asumiendo la secuencia 1..N completa, crasheaba con `TypeError` al normalizar un `None`.
   Arreglado usando el ancestro que SÍ está presente en cada nivel, sin asumir continuidad.

**Diseño de Módulo 3 para pares, con clave distinta a la de párrafos/filas de otros
manuales**: `(example_title, name)` compuesta y EXACTA (sin fuzzy sobre `name` -mismo riesgo de
colisión con etiquetas cortas/genéricas ya demostrado inseguro en el 5to manual, no
re-investigado porque el mecanismo y el riesgo ya están validados ahí). `example_title` (con su
sufijo de página `"(N of M)"` separado en Módulo 2, para que la identidad de la tabla quede
estable entre sus páginas de continuación) agrupa correctamente los 236 pares en 10 tablas
reales. Incluso la clave compuesta tiene 52/236 duplicados residuales (sub-estructuras
repetidas dentro de una misma tabla, ej. bloques paralelos "ISSUER TRANSACTION DETAIL"/
"ACQUIRER TRANSACTION DETAIL") -resuelto con el mismo desempate por orden de aparición ya
probado en el 4to manual (`TC 57`) y el 5to (claves TCR).

**Módulo 4 necesitó un mecanismo nuevo**: a diferencia de los manuales 5/6 (donde la clave
consume TODO el contenido mutable, así que un match siempre es idéntico), acá la clave NO
incluye `description` -un par matcheado SÍ puede tener descripción distinta entre ediciones,
comparado con el mismo umbral de similitud 0.98 ya usado en los manuales de grilla, emitido
como `pair_content_changed`. Investigada una señal alta (39 `pair_content_changed` en un par)
antes de validar: 26/39 (67%) son el residuo YA CONOCIDO de Módulo 2 (descripción vacía en la
edición vieja → real en la nueva) -no un bug nuevo, mismo patrón ya documentado, correctamente
clasificado como `extraction_noise` por el LLM en Módulo 5 sin necesitar intervención de la red
de seguridad (24/27 casos de esa categoría en ese par). Los 2 `safety_net_override` que sí
aparecieron resultaron ser el mismo ruido de "guion con espacio extra" ya documentado en el 6to
manual, no un hallazgo nuevo.

**Pipeline completo (Módulos 1-5, 7) para este 7mo manual -por lejos el más complejo del
proyecto hasta ahora en cantidad de formas de contenido distintas manejadas en un solo Módulo
2.** Módulo 6 sigue tentativo. Los 3 bugs reales quedaron arreglados en el momento (ninguno
diferido) -solo el residuo de precisión geométrica de los pares (TODO.md item 14) y el
compartido con el 6to manual (reflow N:M, item 13) quedan como TODO. Detalle completo en
`match.py`/`normalize.py` del propio manual y en la memoria del asistente
(`manual7_vss_vol1_progress.md`).

## 2026-08-19 (cont.) — 8vo manual: `visanet_settlement_service_vss_user_guide_volume_2_reports`
(hermano del 7mo), Módulos 1-4 implementados y validados, Módulo 5 programado pero SIN correr

**El manual más fragmentado del proyecto hasta ahora**: 5 apéndices, cada uno con una forma de
contenido distinta, confirmadas con exploración real de bbox/fuente ANTES de escribir código
(444 páginas, 7 ediciones `20220423`→`20251017`): Apéndice A (`Print-Ready Formats`, rotado a
NIVEL DE PÁGINA -no texto embebido como el 7mo manual-, mezcla reportes de muestra
descartables con tablas `Field Name`/`Description` reales en la misma página), Apéndice B
(grid Tipo A limpio, `Position`/`Field Length`/`Format`/`Field Name`/`Description`, sin
rotación, misma familia que los manuales `base_ii_clearing_interchange_formats` pero más
simple -Description es columna directa del grid, sin field-card separado), Apéndice C (tablas
Código/Descripción Tipo B, algunas con encabezado de 2 niveles grupo/hoja), Apéndice D (mismo
tipo de rotación que A, pero con OTRO sub-shape: registros crudos V22xxx/V23xxx de 5 columnas
`Field Name`/`Position`/`Attribute`/`Field Sources`/`Comments`), Apéndice E (matriz
cross-reference de 6 columnas con encabezado genuino de 2 niveles).

**Decisiones de scope explícitas del usuario (`AskUserQuestion`, antes de escribir código)**:
Módulo 1 separado POR APÉNDICE desde el inicio (a diferencia de los otros 7 manuales, donde
Módulo 1 siempre fue genérico) -límites de cada apéndice detectados dinámicamente por edición
leyendo el TOC embebido del PDF (`"Appendix A:".."Appendix E:"`, nivel 2, estable en
texto/nivel a través de las 7 ediciones). Módulo 2 cubre los 5 apéndices en UN SOLO paso
grande (no incremental por apéndice como en otros manuales).

**Hallazgo real antes de programar Módulo 1**: `page.rotation == 90` es un atributo de página
GENUINO del PDF aquí (`/Rotate 90` real), no líneas individuales rotadas como en el 7mo
manual. PyMuPDF aplica esa rotación en `page.get_text()` (texto plano correcto) pero NO en los
bbox de `page.get_text("dict")` -siguen en el sistema de coordenadas SIN rotar. Módulo 1
captura `page_rotation` además de `dir` por línea para que Módulo 2 sepa qué modo de
interpretación usar.

**Diseño central de Módulo 2: UN SOLO reconstructor genérico de tabla N-columnas** (
`_detect_columns`→luego `_split_into_zones`/`_finalize_zone_leaves`, y `_build_table_rows`)
reusado para los 5 apéndices, en vez de un parser a medida por apéndice -posible porque los 5
comparten el MISMO patrón tipográfico pese a tener 2-6 columnas y distinta orientación: 26.0/
20.0pt Bold = título de sección, 10.5pt Bold = título de tabla, 9.5pt Bold = encabezados de
columna, 9.0pt Regular = contenido de fila (rotado a 14.0/12.0/10.5/9.5/9.0pt en A/D). Las
bandas de columna se calculan dinámicamente por página/tabla desde el propio encabezado
(nunca constantes globales), y la columna "ancla" (dispara fila nueva) es la de menor X0 en
horizontal o mayor Y1 en rotado (orden de lectura). Contenido descartable en A/D (capturas de
reporte tipo mainframe) se filtra por NOMBRE de fuente (`CourierNewPSMT`, monoespaciada) -el
único señal estable, ya que el TAMAÑO de esa fuente varía real y confirmadamente entre
reportes (7.3pt o 10.5pt).

**9 bugs reales encontrados y arreglados durante la validación de Módulos 2-4** (todos leyendo
contenido real reconstruido contra el PDF fuente, no solo conteos):
1. Encabezados envueltos a 2 líneas (Apéndice E, `"Transaction "`+`"Description"`) caían en
   su propia fila tipográfica en vez de fusionarse con su propio encabezado -2 columnas
   enteras desaparecían. Arreglado ampliando la tolerancia de agrupamiento de fila (6→15pt,
   calibrada entre el gap real de envoltura ~12pt y el gap real entre niveles distintos
   ~20.5pt) + arreglado un bug de "solo se guardaban las hojas del ÚLTIMO nivel" que
   descartaba hojas legítimas de niveles anteriores.
2. La fusión de las 2 líneas de UN MISMO encabezado envuelto seguía sin funcionar por un
   desplazamiento de 10.3pt en el eje secundario (alineación de texto) -tolerancia de fusión
   ampliada a 20.0pt (seguro: el gap real mínimo entre 2 encabezados GENUINAMENTE distintos en
   la misma fila es >90pt).
3. Eje de bbox equivocado en el chequeo de "fin de línea" para tablas rotadas (`bbox[1]`=Y0 en
   vez de `bbox[2]`=X1) -rompía la detección de fila nueva en TODAS las tablas rotadas,
   colapsando filas reales de Apéndice D en una sola.
4. Orden de procesamiento invertido en empates de posición primaria para tablas rotadas (el
   ancla, banda secundaria más alta, se procesaba de ÚLTIMA en vez de primera) -misma causa
   raíz que el bug 3, mismo síntoma.
5. Umbral de gap de fila nueva en rotado mal calibrado (`12.0`, derivado de un factor
   arbitrario) vs. el mínimo real observado (7.5pt, confirmado en 2 tablas distintas) -
   reemplazado por una constante propia calibrada con evidencia real.
6. Umbral de detección grupo-vs-hoja de encabezado de 2 niveles (`GROUP_HEADER_MIN_GAP`) muy
   bajo (30.0) -un grupo real del Apéndice C ("VSS Business Transaction Code") está a 48.4pt
   de su hoja más cercana, por encima del umbral viejo, así que escapaba la clasificación de
   grupo y robaba datos de la columna real vecina. Recalibrado a 65.0 con evidencia de AMBOS
   apéndices (grupo-a-hoja real 10.8-48.4pt, hoja-a-hoja real ≥90.8pt).
7. Una inconsistencia GENUINA del PDF fuente (prefijo `"Note: "` en una página, ausente en la
   de continuación de la MISMA tabla real) partía una tabla en 2 títulos -esto en cascada
   robaba el target correcto de OTRA tabla completamente distinta vía fuzzy matching entre
   ediciones (`"...Record 4"` terminaba emparejado con `"...Record 5"`). Se probó primero
   coalescer por fuzzy-similaridad dentro de la edición y se DESCARTÓ explícitamente: el mismo
   umbral fusionaría tablas realmente distintas (0.895 de similitud real entre Record 4 y
   Record 5). Arreglado con un strip preciso del prefijo `"Note: "` (el único patrón real en
   todo el corpus).
8. **El bug más importante, encontrado validando Módulo 3**: 2 tablas REALMENTE DISTINTAS
   (registros V22xxx/V23xxx consecutivos y cortos) compartiendo una página rotada declaran
   encabezados con los MISMOS 5 nombres de columna -el diccionario final de columnas
   colapsaba ambas en una sola (colisión de clave), perdiendo la posición real de una tabla y
   pegando sus títulos. Impacto medido ANTES de arreglar: 13-21 títulos pegados por edición
   solo en Apéndice D (~20-30% de sus ~66-69 tablas) -datos reales de layout de campos, el
   caso de uso central del proyecto. Arreglado con una arquitectura nueva: `_split_into_zones`
   detecta "2 tiers de encabezado comparten un nombre de columna" como la señal de que son 2
   tablas distintas (nunca pasa en un grupo/hoja legítimo, que usa nombres disjuntos) y separa
   la página en "zonas" independientes, cada una con su propio rango de posición primaria;
   `build_horizontal_blocks`/`build_rotated_blocks` reescritos para iterar sobre zonas por
   página en vez de asumir 1 tabla por página.
9. **Encontrado validando Módulo 4** (conteos sospechosos de `row_added`/`row_removed` en
   Apéndice C): el fix del bug 8 separaba bien las columnas por zona, pero el enrutamiento de
   TÍTULOS no -`_assign_zone` (pensada para datos, que siempre vienen DESPUÉS de su propio
   encabezado) asignaba el título de la 2da tabla de una página a la zona de la 1ra (su
   encabezado ya había aparecido, el de la 2da todavía no). Arreglado con una función de
   enrutamiento de títulos separada (busca hacia ADELANTE la zona más cercana). Efecto
   colateral bueno: esto también resolvió por completo un residuo que se había logueado ese
   mismo día (2 mismatches de número de registro entre 51 fuzzy matches) -quedó en 0/52 tras
   este fix, sin necesidad de tratamiento aparte.

**Módulo 3** (`match.py`): cada apéndice se procesa de forma INDEPENDIENTE (sin jerarquía de
secciones compartida entre apéndices, a diferencia de todos los otros manuales). Clave de
tabla: `(apéndice, table_title)`, exacto + fuzzy (0.85). Clave de fila: valor de
`anchor_column` (expuesto desde Módulo 2 específicamente para esto, `_build_table_rows`
devuelve `(rows, anchor_col)`), exacto, con desempate por orden de aparición para duplicados
-confirmados reales y no triviales, hasta ~33% de las filas en algunas tablas del Apéndice E.

**Módulo 4** (`detect.py`): puramente determinístico como siempre. Diffea por NOMBRE de
columna (no índice, como el 2do manual) excluyendo la columna ancla, mismo umbral 0.98. Un
hallazgo NO tratado como bug (decisión de diseño deliberada, ver docstring): Apéndice C mostró
un cambio de mayúsculas/minúsculas puro entre 2 ediciones (`"Other"`→`"OTHER"`), detectado
como `row_content_changed` con ratio muy bajo (case-sensitive) -correcto que Módulo 4 no lo
filtre, es trabajo de Módulo 5 (IA) reconocerlo como `editorial_reword`, no de este módulo
determinístico.

**Módulo 5** (`classify.py`): mismo diseño que el resto del proyecto (Ollama local `qwen3:4b`,
JSON forzado, `think:false`, temp 0, 3 categorías, red de seguridad `_find_disappeared_content`
con umbral de 5 palabras), UN SOLO prompt genérico para los 5 apéndices (cada `row_content_
changed` ya trae el mismo shape). Smoke test (6 items) confirmó buena calidad, con 1 quirk de
categoría ya conocida (valor corto de 1 palabra mal clasificado, mismo hecho capturado
correctamente en otra columna de la misma fila -no hay pérdida real).

**10mo bug real, encontrado validando la tasa de `safety_net_override` de la corrida completa
(37/487 ≈ 7.6%, elevada vs. el ~3.5% típico de otros manuales -investigado antes de aceptar,
misma disciplina de siempre)**: 14 de 15 overrides de un par apuntaban a la MISMA tabla del
Apéndice E (`"SMS (Including Interlink) Transactions..."`), con `Messages and Codes`/
`Business Transaction Type` yendo de contenido real a vacío. Verificado contra el PDF fuente
directamente: el contenido SÍ existe en la edición nueva -no era un cambio real ni una
remoción editorial, sino que en 3 de 7 ediciones (`20230415`, `20231013`, `20240413`,
autocorregido después) PyMuPDF extrae esos encabezados de 2 palabras como 2 SPANS separados en
la MISMA línea Y0 (`"Messages"` + `" and Codes"`) en vez de uno solo -confirmado real
comparando bbox exactos contra la edición limpia `20221014`. Un umbral geométrico se probó y
se DESCARTÓ: el gap espurio real (19.4-31.8pt) se superpone con el gap real mínimo entre
columnas GENUINAMENTE distintas ya validadas en el Apéndice B (`"Field Length"`→`"Format"` =
19.9pt) -ningún umbral único separa ambos casos. Arreglado con una señal de datos en vez de
geometría: una columna 100% vacía en TODAS las filas de la tabla (mínimo 2 filas), adyacente a
una columna con contenido, es con altísima confianza un fragmento fantasma -se fusiona con su
vecina (`_merge_phantom_columns`, corre después de `_build_table_rows`).

**11vo bug, encontrado arreglando el 10mo**: el nombre de columna fusionado necesitaba el
espaciado correcto (`"Messages"`+`"and Codes"`→`"Messages and Codes"` con espacio;
`"Business Tran"`+`"saction Type"`→`"Business Transaction Type"` sin espacio, corte real a
mitad de palabra) para calzar con el nombre de las ediciones limpias y que Módulo 4 diffee
por nombre de columna correctamente -pero Módulo 1 ya recorta (`.strip()`) el texto de cada
línea antes de que Módulo 2 lo vea, perdiendo esa señal. Arreglado con un cambio chico y
aditivo en Módulo 1: se agregó un booleano `starts_with_space` (calculado del texto CRUDO sin
recortar) junto al campo `text` ya existente -sin duplicar el texto completo. Módulo 1
re-corrido, propagado por `_cluster_header_tiers`→`_finalize_zone_leaves`→
`_merge_phantom_columns`.

Pipeline completo (Módulos 1-4) re-corrido tras ambos fixes: 0 regresiones en ninguna tabla ya
validada, conteos de `grid_row` sin cambios salvo en Apéndice E (baja levemente por la fusión
de columnas fantasma, esperado), `row_content_changed` de la tabla afectada bajó de 64 a 40 en
el par correspondiente (menos diffs espurios de "contenido desaparecido", la firma real de
este bug).

**Sesión pausada acá (2026-08-19, fin del día) sin correr el batch completo de Módulo 5.** El
usuario lanzó la corrida completa (506 items, ~90 min en CPU) en segundo plano, la dejó correr
un rato mientras chequeaba el progreso varias veces, y finalmente pidió cortarla (37/506
ítems) para irse a dormir sin dejar la laptop prendida toda la noche -no valía la pena el
riesgo de un estado de suspensión ambiguo por ~7 minutos de trabajo ya hecho. Los archivos
JSON parciales de `data/05_interpretacion_cambios_ia/` (de la corrida ANTERIOR al fix de los
bugs 10-11, ya obsoletos) fueron borrados para que la próxima sesión no los confunda con datos
válidos. **Próximo paso: solo correr `classify.py` desde cero (sin argumentos) -no hace falta
tocar nada de Módulos 1-4, ya están correctos y guardados en disco.** Módulo 6 sigue
tentativo/tentado, Módulo 7 (Reporte de cambios) no empezado. Detalle completo en la memoria
del asistente (`manual8_vss_vol2_progress.md`).

## 2026-08-20 — 8vo manual (cont.): Módulo 5 corrido completo, validación de `safety_net_override` encuentra y arregla un bug real de Módulo 4 (NBSP), y Módulo 7 implementado — pipeline del manual 8 llega hasta Módulo 7

Sesión retomada: primero se corrió `classify.py` (Módulo 5) desde cero, sin tocar Módulos 1-4
(506 `row_content_changed` totales, ~1h38m en CPU, 0 errores). Luego, siguiendo el mismo
criterio ya usado en TODOS los manuales anteriores ("validar los `safety_net_override`
primero, son el mayor rendimiento de bugs reales encontrados hasta ahora"), se leyeron los 31
casos de `safety_net_override` contra el PDF fuente.

**Se encontró y arregló el bug más importante de la sesión (bug 9 en la numeración de
`manual8-vss-vol2-progress.md`): NBSP (U+00A0) vs. espacio normal en el texto de encabezado de
columna/título rompía el diffeo por nombre de columna de Módulo 4, responsable de 15 de los 31
`safety_net_override` (todos concentrados en la tabla `SMS (Including Interlink) Transactions
Cross-Reference to VSS Business Transaction Types` del Apéndice E).** El PDF fuente codifica el
espacio entre palabras de algunos encabezados como NBSP en vez de espacio normal U+0020, de
forma INCONSISTENTE incluso dentro de una misma tabla/edición -confirmado con evidencia real:
en la edición `20240413`, la misma tabla tiene 6 filas con clave de columna limpia y 8 filas
con clave NBSP, repartidas entre distintas páginas de la misma tabla. `Módulo3/match.py` ya
normalizaba espacios en blanco (incluido NBSP, confirmado que `\s` de Python matchea U+00A0)
para las claves de identidad de tabla/fila vía `_norm()`, pero `Módulo4/detect.py`'s
`_diff_row` iteraba `sorted(set(cols_a) | set(cols_b))` sobre las claves CRUDAS del diccionario
de columnas, sin normalizar -así que `"Messages and Codes"` y `"Messages\xa0and\xa0Codes"` se
trataban como 2 columnas totalmente distintas. Cada mismatch generaba un PAR de diffs
espurios: uno "columna desapareció" (SÍ atrapado por la red de seguridad de Módulo 5, con
categoría final correcta -`extraction_noise`- pero por la razón equivocada) y uno "columna
apareció" (NO atrapado por nada -no hay `disappeared_content` que perseguir- y clasificado en
silencio por el LLM como `business_rule_change` real, un falso positivo peor porque no lleva
ninguna marca de revisión; confirmado con ejemplos reales pre-fix, ej. `old:"" → new:"POS
Balance Inquiry"`).

**Arreglado en la raíz, no en el sitio de comparación**: se agregó `_clean_text()` a
`Módulo2/normalize.py`, que reemplaza NBSP por espacio normal en el campo `text` de CADA línea
al inicio de `normalize_edition`, antes de que ese texto se use para construir un nombre de
columna o título de tabla -así la clave inconsistente nunca entra al pipeline. No se tocó
`match.py`/`detect.py` (con la raíz arreglada, su comportamiento ya es correcto sin cambios).
Verificado con Python que `starts_with_space` (booleano de Módulo 1 usado por
`_merge_phantom_columns`, ver el bug 10/11 del 2026-08-19) no se ve afectado -se calcula del
texto CRUDO sin recortar en Módulo 1, un campo independiente del `text` que se normaliza acá.

**Verificado de punta a punta**: Módulos 2→5 re-corridos para las 7 ediciones / 6 pares.
`safety_net_override` total 31→18 (bajó exactamente en los 2 pares afectados: `20221014→
20230415` 9→3, `20240413→20250412` 9→2; los otros 2 pares con overrides, `20230415→20231013`
7 y `20231013→20240413` 6, quedaron intactos como se esperaba -esos son bugs DISTINTOS, no
relacionados al NBSP). `row_content_changed` total 506→445 (61 menos, todos confirmados como
ruido espurio del bug -los casos genuinos, ej. los 2 trims reales de "63.0 is set to 1)" en
`preauthorization`/`preauthorization reversal`, sobrevivieron sin cambios en ambos pares).

**2 bugs más reales encontrados validando el resto de los `safety_net_override` (logueados,
NO arreglados esta sesión, ver items 15/16 en TODO.md)**:
- Apéndice B: en filas/ediciones puntuales, la primera oración de `Description` queda pegada
  al final de `Field Name` en vez de empezar su propia columna (confirmado en `Net Amount
  Sign`, edición `20231013` -limpio en `20230415`). 5 filas afectadas en el par
  `20230415→20231013`.
- Apéndice A: las filas de `Available VSS Reports` (`VSS-116`/`VSS-116-M`) se parten en 2
  `grid_row` sin fusionar en un salto de página (confirmado edición `20240413`, página 25/26)
  -el primer fragmento termina a mitad de oración, el segundo (sin ancla propia) sigue el
  texto. Módulo 3 solo empareja el primero (truncado) contra el texto completo de la edición
  previa. 6 `safety_net_override` en el par `20231013→20240413` vienen de esto -misma clase
  arquitectónica que el item 13 (reflow de página, manuales 6/7), instancia nueva en un
  apéndice nuevo.

**1 hallazgo adicional, no relacionado al NBSP, encontrado por casualidad revisando por qué el
matching de tablas de Apéndice B se veía raro (logueado, ver item 17 en TODO.md)**: el título
`"TC 46, TCR N (Report Subgroup X)..."` se re-declara en cada página de la tabla (~6 veces); en
1 sola de esas ~6 apariciones el texto sale con "TCR" partido en 2 palabras (`"TC R"`) Y con
espacio normal en vez de NBSP -confirmado en la salida CRUDA de Módulo 1 para la edición
`20240413`, `Report Subgroup 2`. Es una malformación DISTINTA a la de NBSP (acá hay un espacio
real de más entre "C" y "R", no una variante de espacio en blanco -normalizar `\s+`/NBSP no lo
arregla). Causa 8 `table_removed` espurias + 1 `table_renamed` mal fusionada en el par
`20240413→20250412`, y es visible como ruido en otros pares también (ver reporte Módulo 7 del
par `20221014→20230415`).

**Módulo 7 (`07_reporte_cambios/report.py`) implementado y corrido el mismo día.** Mismo diseño
que los demás manuales (cambios de negocio primero, altas/bajas estructurales en sus propias
secciones, apéndice de redacción/ruido, avisos de confiabilidad al final) pero adaptado a la
particularidad de este manual: sin jerarquía de secciones única (Módulo 3 procesa 5 apéndices
independientes), así que cada item se agrupa por `(apéndice, table_title)` en vez de por
`path` -con el nombre legible del apéndice (`APPENDIX_LABELS`, mismo texto usado para separar
secciones en Módulo 1) antepuesto a cada encabezado de grupo. No tiene sección dedicada de
transiciones Reserved↔definido (a diferencia del 3er/4to manual, Tipo A) porque Módulo 4 de
este manual no emite ese `change_type` -las altas/bajas de fila (`row_added`/`row_removed`) ya
muestran el contenido completo de la fila, alcanza para que un lector identifique una
transición Reserved a simple vista sin necesitar una sección aparte. 6 reportes generados sin
errores (uno por par de ediciones) + `index.md`: 90/12/47/11/8/9 cambios de negocio a revisar
por par. El bug 17 (título "TC R" partido) es visible en el reporte del par
`20221014→20230415` como ruido en las secciones de tablas agregadas/eliminadas/renombradas
-confirma el impacto real del bug sin necesidad de arreglarlo esta sesión, consistente con la
decisión de dejarlo logueado.

**Con esto, el pipeline del manual 8 llega hasta Módulo 7 (Módulo 6 sigue tentativo/sin definir,
igual que en los otros 7 manuales).** Detalle completo en la memoria del asistente
(`manual8_vss_vol2_progress.md`, bugs 9-12).

## 2026-08-20 (cont.) — Pivote a cerrar deuda de TODO: investigación completa y fix del bug #3 (nota al pie corrompiendo Croacia/Sierra Leone en `base_ii_clearing_data_codes`)

Con el manual 8 en Módulo 7, el usuario planteó la pregunta de arquitectura para producción: un
único router que identifica el tipo de PDF y despacha a 1 de 8 pipelines completamente distintos
(cada uno con sus propios 6-7 módulos, sin lógica de negocio compartida -solo infraestructura
común como el wrapper de Ollama, el parseo de argumentos CLI, y el esqueleto Markdown del
reporte). El usuario decidió no diseñar el router todavía y en cambio empezar a cerrar la deuda
de bugs conocidos del TODO, arrancando por el 1er manual (`base_ii_clearing_data_codes`).

Se repasaron los 4 items pendientes de este manual (glosario sin parsear, fusión de texto de
"Cook Islands", nota al pie en límite de tabla, nota de diseño de `CODE_LIKE`) -el único con
prioridad real era el item 3 (nota al pie corrompiendo datos de código reales), así que se
investigó su alcance completo.

**Alcance real, mucho más grande que lo logueado originalmente (1 edición, ~4 filas)**: leyendo
los spans crudos de PyMuPDF (no solo el texto ya agrupado) se confirmó que Croacia estuvo
corrompida en **6 ediciones consecutivas** (`20221015`→`20250412`) y Sierra Leone en 2
(`20221015`, `20230415`), por **2 mecanismos de causa raíz distintos**:

- **Mecanismo A (Módulo 1)**: el dígito de una nota al pie en superíndice (6.75pt, confirmado con
  `page.get_text("dict")`) se concatenaba sin separador en la MISMA línea de PyMuPDF que el código
  real (9.0pt) -ej. `'HRK'+'1'`→`'HRK1'`, `'191'+'1'`→`'1911'`. Un escaneo del corpus completo
  (buscando spans de tamaño <8.0pt con texto puramente numérico) encontró 38-63 instancias por
  edición, NO acotadas a Croacia/Sierra Leone -ej. en `Merchant Mailing CRB Region Codes`, el
  código real `'X'` corrompido a `'X1'` colisionaba visualmente con el código real y DISTINTO
  `'X1'` (región 1), que a su vez se corrompía a `'X11,2'` (nota al pie múltiple, `"1,2"` en un
  solo span).
- **Mecanismo B (Módulo 2)**: cuando un país tiene una transición de moneda documentada (valor
  viejo + nuevo apilados, ej. Sierra Leone `SLL/694`→`SLE/925`), el PDF renderiza el valor
  secundario SIN texto en la columna ancla (nombre de país) -Módulo 2 lo trataba como fila nueva
  independiente (`has_code_cell` disparaba `flush()`+fila nueva sin chequear si arrancaba en la
  columna ancla), generando fragmentos huérfanos (`['SLL','694']`, `['Leone','SLE','925']`) en vez
  de fusionarse con la fila del país correcto.

**Fix aplicado, ambos mecanismos** (a pedido explícito del usuario, "ataquemos los dos"):
- Módulo 1 (`ingest.py`): nueva función `_line_text_or_none()` -descarta, al concatenar los spans
  de una línea, cualquier span de tamaño <8.0pt (`FOOTNOTE_MARKER_MAX_SIZE`) cuyo texto matchee
  `^\d+(,\d+)*$` (uno o más dígitos, opcionalmente separados por coma) -nunca letras, para no
  tocar el marcador `S` de "moneda de liquidación" (mismo tamaño 6.75pt pero alfabético, con
  significado real que puede variar entre ediciones). Verificado contra el corpus completo antes
  de implementar: SIN excepciones, cualquier span <8.0pt puramente numérico en este documento es
  un marcador de nota al pie.
- Módulo 2 (`normalize.py`): un chequeo de "¿esta fila con celda-código arranca cerca de la
  columna ancla de la fila de DATOS activa?" antes de aceptarla como fila nueva -si no, cae en la
  rama de fusión/`pending_prefix` ya existente en vez de abrir una fila huérfana.

**2 regresiones reales encontradas y arregladas validando el fix de Módulo 2 contra las 9
ediciones completas** (mismo principio ya aprendido con el manual 8 esta sesión: un umbral
geométrico calibrado contra 1 sola tabla no es seguro asumirlo para las demás sin re-validar):

1. La primera versión del chequeo (tolerancia 15.0, reusando `TABLE_LEFT_MARGIN_TOLERANCE`)
   rompió 2 tablas DISTINTAS con un A/B directo confirmándolo: `Numeric Currency Code to Country
   Name Cross-Reference` (el label del encabezado "Currency Code", X0=84.1, arranca 26.9pt a la
   izquierda de su propia primera fila de datos "496", X0=111.0, por pura alineación tipográfica
   de un código corto de 3 dígitos) y `Merchant Mailing CRB Region Codes` (el marcador especial
   "H0 (continued)", X0=83.1, arranca 25.0pt a la izquierda de los códigos normales que le siguen,
   "H1"/"HA"/"HD", X0≈108). Aplicar el chequeo ahí fusionaba TODA la tabla en 1 encabezado gigante
   + 1 fila gigante. **Arreglado en 2 pasos**: (a) acotar el chequeo a transiciones
   `table_row`→`table_row` (nunca `table_header`→primera-fila, donde la diferencia de alineación
   entre un label y su columna de datos es normal); (b) recalibrar el umbral con un escaneo real
   de brechas en las 9 ediciones completas -falsos positivos reales van de 19.8 a 78.1pt (ej. "H0
   (continued)"→"H1", códigos alfa de país tras un header de región), positivos reales (Croacia,
   Sierra Leone, y también encontrado por este mismo escaneo: nombres de moneda envueltos como
   "Mozambique Metical" colisionando con su propio código alfa) arrancan en 233.9pt como mínimo -
   separación real de 155.7pt sin ningún caso intermedio, umbral final `SECONDARY_ROW_ANCHOR_GAP_
   MIN = 150.0`.
2. Con el umbral ya recalibrado, la fila secundaria real de Sierra Leone (`Leone/SLE/925`, su
   moneda nueva) se pegaba a **Singapur** (el país siguiente en la tabla) en vez de a Sierra
   Leone: la rama de decisión existente ("el hueco numérico más chico gana", reusada del
   mecanismo simétrico ya validado para nombres envueltos) comparó el hueco a Singapur (8.5pt) vs
   el hueco a Sierra Leone (14.5pt) y Singapur ganó por pura coincidencia de layout, aunque
   NINGUNO de los 2 lados solapaba realmente en Y. Confirmado con las coordenadas reales exactas
   (Sierra Leone Y=325.1-337.1, su fila secundaria Y=351.6-363.6, Singapur Y=372.1-384.1).
   **Arreglado con una rama dedicada, separada de la rama simétrica ya existente** (que sigue
   intacta para su propio caso de uso, nombres envueltos): una fila secundaria fuera de ancla solo
   se difiere a la fila SIGUIENTE (`pending_prefix`) si hay un SOLAPE REAL en Y con ella (no solo
   un hueco numérico menor); si no, se fusiona directo con la fila activa, sin comparar huecos.
   Verificado: Sierra Leone ahora muestra correctamente `SLL\nSLE`/`694\n925` (ambos valores,
   viejo+nuevo, en su propia fila) y Singapur queda completamente limpio en las 9 ediciones.

**Verificación de punta a punta, Módulos 1→5 y 7 re-corridos completos**: 0 páginas sin bloques,
0 celdas vacías, conteos de `table_row` estables (1862-1900, mismo rango que el baseline
original 1857-1895) en las 9 ediciones. Módulo 5 (`classify.py`, batch completo, ~50min en CPU)
terminó con 0 errores, `safety_net_override` total 11 (mismo número que la corrida original,
antes de este fix -consistente con que el fix corrigió CONTENIDO corrompido sin cambiar la
cantidad de diffs genuinos). Módulo 7 (`report.py`) regenerado: los diffs de Croacia
(`Croatian Kuna`→`Croatian Kuna+Euro`→`Euro`→`EUR`, reflejando la transición real de moneda
2022-2023 más el typo real de Visa "Euro" en vez de "EUR" en la columna de código alfa,
autocorregido recién en `20251018`) y Sierra Leone (`SLL/694`→`SLL+SLE/694+925`→`SLE/925`,
reflejando la redenominación real de 2022) se leen correctamente en el reporte final, sin ningún
rastro de corrupción.

**Hallazgo nuevo durante la investigación, logueado como item 3b (NO arreglado, a pedido
explícito del usuario -"tengo anotado para ver si podemos resolverlo más adelante")**: Zimbabue
tiene un problema de la MISMA categoría (nota al pie en el límite de tabla) pero un mecanismo
DISTINTO, no tocado por este fix -el párrafo de notas y el título de la sección siguiente
(`Canadian Province Codes`) arrancan en la MISMA posición X0 que la columna ancla (a diferencia
del item 3, donde la fila secundaria NO tenía columna ancla), así que el heurístico de "¿esto es
un párrafo nuevo?" (que solo dispara si el párrafo arranca MÁS a la izquierda que la tabla) nunca
lo detecta. Confirmado: la celda de Zimbabue llega a 1230 caracteres en las ediciones afectadas
(`20221015`-`20250412`, y de nuevo en `20260418`). Los valores de código de Zimbabue en sí quedan
limpios -solo se ensucia el nombre del país, prioridad baja.

Con el fix del item 3 cerrado, el usuario pidió seguir directo con Módulo 5 (clasificación IA) y
Módulo 7 (reporte) del mismo manual -ya cubierto arriba, corridos en la misma sesión sin
problemas nuevos.

## 2026-08-20 (cont. 2) — Fix del bug #2 (`"Cook Islands (the) CK"`, fusión de celdas a nivel de Módulo 1)

Con Módulo 5/7 del manual 1 ya regenerados, el usuario pidió retomar el item #2 del TODO (fusión
de texto de PyMuPDF en "Cook Islands (the) CK", originalmente logueado como 1 fila/1 edición).

**Alcance real, otra vez más grande que lo logueado**: leyendo los spans crudos de la fila de
Cook Islands se confirmó que PyMuPDF fusiona el nombre del país y su código alfa en UNA sola
`line` con un span de PURO espacio en blanco entre ambos (`'Cook Islands (the)'` + `' '` +
`'CK'`, los 3 spans al mismo tamaño 9.0pt -a diferencia del bug de notas al pie, acá NO hay
diferencia de tamaño de fuente que sirva de señal). Confirmado presente en 3 ediciones
(`20220423`, `20221015`, `20230415`), autocorrigiéndose desde `20231014` (esas ediciones ya
traen el nombre y el código como 2 líneas separadas de PyMuPDF).

Un escaneo del corpus completo (buscando cualquier línea con 2+ spans donde alguno sea
puramente espacio en blanco, y descartando las líneas de "dot leader" del índice que usan la
misma señal) encontró el MISMO patrón en ~6 instancias más, no acotadas a Cook Islands ni a la
tabla `Country and Currency Codes`: `'Moroccan Dirham'`+`' '`+`'MAD'`, `'Canadian DollarS'`+`'
'`+`'CAD'`, `'Zimbabwe Dollar'`+`' '`+`'ZWL'`, `'American Samoa'`+`' '`+`'AS'` (mismo problema,
nombre+código de moneda/país fusionados), más 2 instancias en tablas totalmente distintas: una
tabla de definición de código en p.60 (`'Proximity payment using magnetic stripe data
rules.'`+`' '`+`'Use to indicate...'`) y una matriz de 2 columnas en p.135/136
(`'Dispute Financial'`+`' '`+`'Dispute Response'`). En TODOS los casos verificados, el span de
puro espacio separa 2 piezas de contenido genuinamente distintas -nunca aparece dentro de una
celda real.

**Fix implementado en Módulo 1 (`ingest.py`)**: nueva función `_split_line_segments()` -corta los
spans de una `line` de PyMuPDF en 2+ segmentos independientes en cada span cuyo texto sea
puramente espacio en blanco (el span en sí se descarta), cada segmento emitido como su propia
línea de salida con su propio bbox recalculado (`_segment_bbox()`, min/max de los spans de ese
segmento) en vez de heredar el bbox completo de la línea original fusionada.

**1 regresión encontrada y arreglada de inmediato al validar** (mismo patrón de disciplina que
el resto de la sesión: correr contra el corpus completo antes de dar por bueno un fix): la
primera versión de `_split_line_segments()` dividía TAMBIÉN las líneas de "dot leader" del
índice (`"Título. . . . . . 123"`), que usan la MISMA señal (un span de puro espacio entre el
título y los puntos de relleno) -el conteo de líneas por edición saltó de ~9800 a ~11700-11900,
mucho más que las ~7 instancias reales encontradas en el escaneo. Causa: el filtro de "dot
leader" de Módulo 2 (`TOC_DOT_LEADER`, `is_noise()`) matchea sobre el texto COMPLETO de la
línea (`(\. ){4,}`) -una vez dividida, el primer fragmento ("Título" solo, sin los puntos) ya no
matchea ese patrón y se colaba como contenido real en vez de descartarse como ruido de índice.
**Arreglado** deteccionando el patrón de dot-leader sobre el texto CRUDO (sin dividir, unión
directa de todos los spans) ANTES de decidir si dividir la línea -si matchea, se preserva
completa (mismo comportamiento que antes de este fix), igual que siempre se comportó para
Módulo 2. Verificado: conteo de líneas volvió a ~9812-10136 (solo +7 respecto al baseline
pre-fix, consistente con las instancias reales encontradas), página 3 del índice (la real,
confirmada a mano) sin ninguna entrada de dot-leader colada como contenido.

**Verificación de punta a punta, Módulos 1→4 re-corridos** (no se re-corrió Módulo 5/7 esta vez,
dado que el usuario ya había cerrado esos para el fix del bug #3 y este bug #2 es de prioridad
mucho menor -pendiente decidir si vale la pena repetir los ~50min de Módulo 5 solo por este fix
cosmético): 0 páginas sin bloques, 0 celdas vacías, conteos de `table_row` IDÉNTICOS al baseline
post-fix-#3 en las 9 ediciones (1873/1888/1892/1900/1862/1881/1885/1892/1893) -confirma que
dividir una línea fusionada no crea filas nuevas, solo corrige el contenido de la celda dentro
de la fila que ya existía. Cook Islands ahora lee `['Cook Islands (the)', 'CK', '184', ...]` en
las 3 ediciones afectadas, igual que el patrón limpio de las 6 ediciones que ya se autocorregían.
Módulo 3/4 re-corridos sin errores; el par `20230415→20231014` bajó de 62 a 55
`code_content_changed` (7 diffs espurios menos, consistente con que antes esas filas fusionadas
generaban falsos "cambios" al compararse contra las ediciones ya limpias).

**Hallazgo adicional, NO relacionado, no tocado**: la página 3 del índice (TOC real) sigue
mostrando los números de página (`'6'`, `'7'`, `'15'`...) como bloques `paragraph` sueltos -
confirmado que esto es una línea de PyMuPDF completamente SEPARADA del texto+dot-leader (propio
bbox, propia posición X0=534.6), preexistente a este fix, no algo introducido hoy. No
investigado -muy bajo impacto (ruido de índice), fuera del alcance de lo pedido.

**Usuario pidió correr Módulo 5 y 7 también para este fix** (mismo día, después de validar
Módulos 1-4). Ollama confirmado corriendo; batch completo lanzado en segundo plano (301 items
`code_content_changed`, ~50min en CPU) -terminó con 0 errores, `safety_net_override` total 10
(muy cerca del 11 del baseline del fix del item 3, sin sorpresas). Módulo 7 regeneró los 8
reportes; se hizo `grep -i "cook island"` sobre los 8 archivos `.md` generados -0 resultados,
confirmando que el fix eliminó por completo el ruido espurio que antes generaba (no solo lo
desplazó a otra forma de diff).

**Cierre de sesión (2026-08-20, tarde)**: a pedido del usuario, se dejó todo documentado en
ambos sistemas de memoria (memoria del asistente + este archivo/TODO.md) para poder retomar en
otra sesión sin perder contexto. Items 2 y 3 del manual 1 quedan RESUELTOS y verificados de
punta a punta (Módulos 1→5, 7). Quedan abiertos, ninguno urgente: item 1 (glosario,
deprioritizado por el usuario), item 3b (Zimbabue, anotado para después a pedido explícito del
usuario), item 4 y 5 (ambos cosméticos, muy baja prioridad). Tampoco se empezó todavía el diseño
de arquitectura de producción (router + contrato de interfaz) que el usuario planteó antes de
pivotar a cerrar bugs -sigue pendiente, sin decisión tomada. Ver TODO.md, sección "Estado de
cierre de sesión", para el punteo completo de próximos pasos.

---

## 2026-08-25 — Fix de items 5 y 6 (Módulo 5: viñetas en evidencia / typos de dígitos del LLM)

El usuario pidió explícitamente tomar los 4 items restantes del manual 1 en esta sesión,
incluido el glosario (item 1) pese a estar deprioritizado. Se atacaron primero los 2 items más
chicos y de menor riesgo (ambos en `05_interpretacion_cambios_ia/classify.py`).

**Item 5**: se agregó `BULLET_GLYPH_TOKENS = {"l", "●", "•"}` y se filtran esos tokens de
`old_words`/`new_words` en `_find_disappeared_content` antes de correr el diff palabra por
palabra. Antes de tocar código se confirmó con datos reales que "l" es el único glifo de este
conjunto presente en la evidencia real del manual (978 apariciones en el corpus de disappeared
content vs 0 de "●"/"•"), y que "-" (guión, otro candidato visual a "viñeta") es en realidad
contenido real (`"Fraud - Card-Present"`) en TODOS los casos encontrados, no un glifo.

**Hallazgo real durante la validación** (no solo cosmético como estaba logueado): al recalcular
`_find_disappeared_content` sobre los códigos `H0`/`HZ` de `Return/Reclassification Reason
Codes` (par `20230415→20231014`), el fragmento "desaparecido" que disparaba
`safety_net_override=True` era pura secuencia de viñetas (`"l l l l l l l l l"`). Comparando
old/new palabra por palabra SIN viñetas se confirmó que la lista de campos era 100% IDÉNTICA
entre ediciones -las viñetas simplemente se habían desplazado de posición (de después de la
lista a antes de ella) por un artefacto de extracción/reflow, sin ningún cambio de contenido
real. Con el fix, `disappeared_content` queda vacío para estos 2 casos, `safety_net_override`
pasa a `False`, y la clasificación final vuelve a lo que el LLM había dicho originalmente
(`editorial_reword`) -la clasificación correcta, antes descartada por la red de seguridad.

**Item 6**: se agregó una instrucción al `PROMPT_TEMPLATE` pidiendo que, cuando el cambio
involucre un número largo, el LLM se refiera a "el valor anterior"/"el valor nuevo" en la razón
en vez de re-tipear los dígitos. Verificado que esto es seguro sin pérdida de información:
Módulo 7 (`report.py` línea 76-78) siempre imprime `Antes`/`Ahora` desde `c['old']`/`c['new']`
(el dato fuente), nunca desde el texto generado por el LLM -la instrucción solo puede evitar el
typo en la prosa, no ocultar un dato real.

Ambos fixes se dejaron pendientes de validar con una corrida completa de Módulo 5 (se hizo
junto con los items 3b y 1 más abajo, no por separado, para no correr el batch de LLM 2 veces).

## 2026-08-25 (cont.) — Investigación y fix parcial del item 3b (Zimbabue)

Se investigó la causa raíz exacta antes de tocar código. Con `fitz` directo sobre el PDF crudo
(edición `20221015`, página 129) se confirmó: la fila de Zimbabwe (tabla `Country and Currency
Codes`) queda en Y=204.6-213.6; inmediatamente después, en Y=224.5, arranca el bloque de notas
al pie (`"1 From 1 January 2023, acquirers can submit..."`) en la MISMA X0=75.0 que la columna
de nombre de país -el gap vertical (10.9pt) es parecido al gap normal entre filas de datos
(~8.5pt según la calibración ya documentada), así que un umbral de hueco vertical NO separa de
forma segura este caso de una fila de datos legítima (descartado como enfoque, coincide con lo
que ya anticipaba el TODO original).

**Señal usada en su lugar**: se escaneó el corpus completo buscando líneas cuyo PRIMER span sea
chico (<8.0pt) y matchee el patrón de marcador de nota (dígitos, mismo criterio que el fix ya
existente del item 3) seguido de 15+ caracteres de prosa. Se encontraron 10 bloques de notas
distintos en total (p.54, p.69, p.101/106, p.129/131-133 -Country and Currency-, p.134-142),
TODOS genuinos inicios de párrafo de nota, 0 falsos positivos. Se confirmó además que el
marcador de fusión ya cubierto por el item 3 (`'HRK'+'1'`) siempre tiene el dígito como ÚLTIMO
span de la línea, nunca el primero -así que la nueva señal (`starts_with_footnote_marker`,
chequea posición 0) no colisiona con el fix ya validado del item 3.

**Fix**: `starts_with_footnote_marker` (booleano por línea) en Módulo 1. En Módulo 2, dentro de
la rama de fila de 1 línea con `active_kind` en `("table_row","table_header")`, esta señal
fuerza el mismo comportamiento que ya existía para el corrimiento a la izquierda (`flush()` +
arranca `paragraph` nuevo), sin importar la posición X. Una vez que el bloque de notas entra a
la rama `paragraph`, su propia lógica de corte por hueco (`PARAGRAPH_MAX_GAP=10.0`) separa sola
el título de la sección siguiente ("Canadian Province Codes", hueco real ~28pt) -no hizo falta
tocar esa lógica.

**Verificado**: Zimbabwe limpio (`['Zimbabwe','ZW','716','Zimbabwe Dollar/Gold','ZWL/ZWG',
'932/924']`) en 5 de las 7 ediciones originalmente logueadas como afectadas (`20220423`
-`20250412`).

**Residuo encontrado, no arreglado**: en `20251018` y `20260418` la nota de Zimbabwe usa un
formato NUEVO -un párrafo con la etiqueta en negrita `"Note:"` (sin marcador de dígito),
confirmado con `fitz` directo (`"Note: Zimbabwe Gold (ZWG/924) replaces..."`, flags=16/negrita,
9.0-10.5pt, mismo tamaño que el cuerpo normal). Se evaluó seriamente una regla genérica ("toda
línea que arranca con `Note:` corta la tabla activa") pero se DESCARTÓ tras escanear el corpus
completo: ~50 apariciones de `"Note:"` por edición, la gran mayoría dentro de una celda de
código YA activa y legítima (ej. p.80, código `80` de `Return/Reclassification Reason Codes`:
`"Product Reclassification has occurred.\nNote:  Product Reclassification occurs in these
conditions:\nl The product ID submitted..."` -acá el `"Note:"` es parte real de la definición
del código 80, cortar ahí lo hubiera fragmentado en 2 bloques, perdiendo la asociación). Aplicar
la regla globalmente habría arreglado Zimbabwe rompiendo docenas de filas reales en otras
tablas -mismo principio de cautela que el resto del proyecto (un heurístico nuevo se valida
contra el corpus completo antes de generalizarlo). Queda documentado como residuo abierto, con
causa raíz identificada, para cuando se justifique invertir en una señal más específica (ej.
propagar tamaño de fuente de forma más general a Módulo 2 y detectar el salto real hacia el
título de la sección siguiente).

## 2026-08-25 (cont. 2) — Fix del glosario (item 1)

Se investigó la geometría real del glosario ANTES de decidir el enfoque (con `fitz` directo,
edición `20260418`, página 141): termino en negrita (`OpenSans-Bold`, flags=16) a X0=72.0,
definición en fuente regular a X0=216.0, ambos 9.0pt -mismo `y0` para la primera línea de cada
par. Esto es geométricamente IDÉNTICO al patrón de 2 columnas que Módulo 2 ya reconstruye para
`Country and Currency Codes` y demás tablas de código -la única razón por la que el glosario
colapsaba es que el heurístico "¿fila nueva?" dependía 100% de `CODE_LIKE` (código corto en
alguna celda), y un término de glosario (frase en minúsculas) nunca matchea eso. Esto descartó
de entrada la hipótesis original (necesitar un tipo de bloque nuevo, `definition_list`) -bastaba
con una señal tipográfica nueva para generalizar el mecanismo ya existente.

**Fix Módulo 1**: se agrega `bold` (negrita del primer span con texto real de la línea) y
`max_size` (tamaño de fuente máximo de la línea) por línea.

**Fix Módulo 2**: nuevo estado `in_glossary` (dict `state`, pasado explícitamente entre páginas
porque `build_blocks()` se llama una vez por página). Se activa al ver la fila de 1 línea con
texto exacto `"Glossary"` -pero **se descubrió, verificando con `fitz`, que el texto "Glossary"
solo NO alcanza como señal**: la tabla de contenidos tiene una entrada homónima, exacta,
TAMBIÉN en negrita (`"Glossary"`, 12.0pt, flags=16, página 5-7 según edición) -mismo texto,
misma negrita, solo cambia el tamaño (26pt el título real vs 12pt la entrada del índice). Por
eso se agregó `max_size` a Módulo 1 y se exige `max_size > GLOSSARY_HEADING_MIN_SIZE (20.0)`
además del texto exacto. Mientras `in_glossary` está activo, cualquier fila multi-línea con
alguna celda en negrita cuenta como "celda-código" a efectos de la misma lógica de decisión que
ya usan las tablas de código -así cada entrada se convierte en su propio `table_row` de 2
celdas.

**Bug real encontrado y arreglado validando el caso de términos envueltos en 2+ líneas** (ej.
"Account Screen Authorization" + "File (ASAF)"): la 2da línea del término, también en negrita,
por coincidencia geométrica comparte banda Y con una línea INTERNA (no la 1ra) de la definición
activa -se veía indistinguible de una entrada nueva, y efectivamente se estaba partiendo en 2
entradas separadas en la primera pasada del fix. Se distinguió con un chequeo de hueco vertical
dedicado (`GLOSSARY_TERM_WRAP_GAP_MAX`, calibrado con un escaneo real de las 9 ediciones
completas: el hueco entre 2 líneas en negrita de un término envuelto es SIEMPRE <=0pt -líneas
pegadas/superpuestas, min -0.9-, el hueco hasta el término de la entrada siguiente es SIEMPRE
>=9.3pt -margen amplio, 8.0 elegido a mitad de camino).

**Bug colateral encontrado validando Módulo 3 (no en el diseño original)**: Módulo 3
(`match.py`) solo reconoce una tabla lógica cuando ve un `table_header` explícito -un
`table_row` sin tabla activa (`current is None`) cae en su mecanismo genérico de "fila
huérfana", con título fijo `"(sin titulo)"`. Como el glosario ahora produce SOLO `table_row`
(nunca un `table_header` real, no hay fila de encabezado de columna en el PDF fuente), las ~200
entradas hubieran caído todas bajo ese título genérico -Y, peor, se hubieran fusionado con
CUALQUIER otra fila huérfana no relacionada del resto del documento que comparta ese mismo
título genérico (`_coalesce_same_title` fusiona por `title_norm`). Arreglado emitiendo un
`table_header` sintético (`["Term", "Definition"]`) una sola vez, justo antes de la 1ra entrada
real, sin tocar el mecanismo genérico de fila huérfana que usan las demás tablas del documento
(cambio acotado, no se tocó `match.py`).

**Verificado de punta a punta**: Módulos 1→4 re-corridos en las 9 ediciones. Conteo de entradas
por edición: 198-201 (antes: 1-2 bloques `table_header` gigantes por página). 0 tablas
`"(sin titulo)"` en los 8 pares. La tabla "Glossary" matchea establemente entre ediciones
consecutivas (194-201 filas matcheadas por par, con altas/bajas de término plausibles). Sin
duplicados de código nuevos (los `duplicate_code_warning` existentes son de otras tablas, no
relacionados). Ya está capturando cambios de contenido reales antes invisibles -ej. par
`20241019→20250412`: `OPTIONAL ISSUER FEE` cuya definición completa se reemplaza por `"See Visa
Issuer FX Calculator"` (redirección real de Visa a otro término).

## 2026-08-25 (cont. 3) — Corrida completa final (Módulos 5 y 7) con los 4 fixes juntos

Se corrieron Módulos 1→5 y 7 de punta a punta con los 4 fixes ya aplicados (items 5, 6, 3b
parcial, 1), en vez de validar cada uno por separado, para correr el batch de LLM (Ollama,
`qwen3:4b`) una sola vez. Módulo 5 procesó 356 items `code_content_changed` (vs 301 en la
corrida previa a este fix -el aumento viene del glosario, ahora diffeable) en ~100 minutos.
0 errores. `safety_net_override` total = 9 (1+0+2+0+0+0+2+4 por par). Confirmado con datos
reales que H0/HZ (el caso investigado para el item 5) efectivamente pasaron de
`safety_net_override=True`/`business_rule_change` a `safety_net_override=False`/
`editorial_reword` en la corrida real, no solo en la prueba aislada.

Módulo 7 regeneró los 8 reportes sin errores (6/6/40/14/14/1/108/42 cambios de negocio por par).
Se grepeó `"cook island"` (regresión del fix ya cerrado del item 2) sobre los 8 reportes -0
resultados, sigue limpio. Se revisó el reporte del par `20241019→20250412` para confirmar que el
cambio de `OPTIONAL ISSUER FEE` (glosario) se ve bien formado en el Markdown final, con
`Antes`/`Ahora`/`Razón (IA)` completos.

**Con esto, los 4 items pendientes del manual 1 quedaron cerrados o documentados con causa raíz
identificada -no queda ningún item "sin investigar" en este manual.** Único residuo abierto:
item 3b en 2 de 9 ediciones (cosmético). Ver TODO.md, sección "Estado de cierre de sesión
(2026-08-25)", para el resumen accionable y los próximos pasos a elección del usuario.

---

## 2026-08-25 (cont. 4) — Glosario e item 7 de `base_ii_clearing_edit_package_messages` (manual 2)

Con el manual 1 cerrado, el usuario pasó al manual 2 y pidió atacar sus 2 items pendientes:
el glosario sin parsear (mismo bug que el item 1 del manual 1) y el item 7 (LLM clasifica mal
el campo `title` de la ficha `V0407`).

### Arquitectura de Módulo 2 de este manual, distinta a la del manual 1

Antes de tocar código se leyó el Módulo 2 completo (`normalize.py`) para entender el diseño:
a diferencia de `base_ii_clearing_data_codes` (reconstrucción de filas/celdas por banda Y), este
manual procesa el documento como un STREAM LINEAL de 1 sola entidad activa (`active`) a la vez,
sin reconstrucción geométrica de filas -el contenido es de 1 sola columna (fichas de código,
`Description:`/`Action:`/`Transaction Types:`). Esto significa que el fix del glosario del manual
1 (reusar `table_row`/`table_header` con negrita como señal de fila nueva) NO se podía portar tal
cual -hacía falta un diseño distinto para esta arquitectura.

### Investigación de la geometría real del glosario (antes de diseñar)

Con `fitz` directo sobre la edición `20260418`, página 332: encabezado "BASE II Glossary" (26pt,
negrita, X0=72) -MISMO glosario, mismo contenido, misma geometría de 2 columnas (término
`OpenSans-Bold` X0=72 / definición `OpenSans-Regular` X0=216, ambos 9.0pt) que el ya resuelto en
el manual 1. Confirmado con un escaneo de gaps verticales entre líneas en negrita en las 9
ediciones: términos envueltos en 2+ líneas quedan pegados (gap ~-0.2pt), una entrada nueva
arranca a 17.3pt o más -misma separación limpia que ya se había calibrado en el manual 1, mismo
umbral (`GLOSSARY_TERM_WRAP_GAP_MAX=8.0`) reusado sin cambios.

### Diseño elegido: reusar el vocabulario de ficha (`card_header`+`field`), no un tipo de bloque nuevo

Para no tocar Módulos 3/4/5/7 (ya validados, saben diffear `ficha_content_changed` por campo con
nombre), cada entrada de glosario se emite como un `card_header` sintético (`code`=`title`=el
término completo) seguido de un `field` con `label="Description"` (la definición) -Módulo 3 ya
sabe capturar ambos bloques sin ningún cambio, mismo principio de "reusar antes que inventar" que
ya gobernó el fix del manual 1 (ahí también se descartó un tipo de bloque nuevo a favor de
generalizar `table_row`). Se usa `label="Description"` (no "Definition", que Módulo 3 ignoraría
por no estar en su whitelist de labels) -tradeoff aceptado, etiqueta levemente imprecisa en el
reporte ("**Description**" en vez de "**Definición**") a cambio de no tocar 4 módulos ya cerrados.

Mecanismo en `build_blocks()`: se activa `in_glossary=True` al ver la línea "BASE II Glossary"
(26pt, mismo chequeo de tamaño ya existente para subtítulos de sección). Mientras está activo,
una línea en negrita que arranca a X0<100 inicia una entrada nueva -salvo que el hueco vertical
hasta la última línea de término ya vista sea chico (continuación de un término envuelto). La
transición de "término acumulándose" a "definición acumulándose" ocurre en la 1ra línea que NO es
de término: ahí se cierra el `card_header` (push directo a `blocks`, no vía `active`) y arranca el
`field` de `Description`, que de ahí en más reusa sin cambios la lógica de acumulación de campo ya
existente en el módulo (incluidas las viñetas `"●"` dentro de una definición, que vienen fusionadas
en la misma línea de PyMuPDF que el texto siguiente, sin necesitar tratamiento de `bullet_list`).

### 2 bugs reales encontrados validando contra las 9 ediciones completas (no solo la de referencia)

1. **0 entradas de glosario en las 3 ediciones más viejas** (`20220423`-`20230415`): el primer
   intento del fix quedó hardcodeado a `GLOSSARY_TERM_FONT = "OpenSans-Bold"`, pero esas 3
   ediciones usan `SegoeUI-Bold` para el término -el MISMO rebrand de Visa que este módulo ya
   documentaba para otra señal (los códigos de ficha, resuelto ahí usando tamaño de fuente en vez
   de nombre). Confirmado con un escaneo de las 9 ediciones antes de aceptar el fix como completo
   -sin este chequeo, el problema original (glosario sin parsear) hubiera seguido presente en
   1/3 de las ediciones sin que nada lo advirtiera. Arreglado aceptando ambos nombres de fuente
   (`GLOSSARY_TERM_FONTS = {"OpenSans-Bold", "SegoeUI-Bold"}`).
2. **Viñeta suelta como palabra suelta dentro de la definición, solo en las 3 ediciones viejas**:
   en esas ediciones la viñeta (`"l"`, fuente `Wingdings-Regular`) viene en su PROPIA línea de
   PyMuPDF, separada del texto que sigue (a diferencia de las 6 ediciones nuevas, donde viene
   fusionada con el texto en la misma línea) -sin filtrarla, se colaba como una palabra "l" suelta
   dentro de la prosa de la definición (ej. "...responsible for: l Accepting card..."). Arreglado
   descartando líneas cuyo texto completo sea un glifo de viñeta conocido (`BULLET_GLYPHS`,
   acotado a `in_glossary` para no tocar el comportamiento ya validado de `Description`/`Action`
   reales).

**Verificado de punta a punta**: Módulos 1→4 re-corridos en las 9 ediciones. 181-183 entradas
limpias por edición (0 con celda vacía o sospechosamente larga), primera/última entrada
consistente ("account funding source"/"warehoused transactions", MISMAS que en el manual 1 -
confirma que es literalmente el mismo glosario compartido entre los 2 manuales). Módulo 3: 0
códigos duplicados, fichas totales 1114-1136 por par (incluye ~933-953 fichas reales +
~181-183 entradas de glosario). Módulo 4 ya detecta cambios reales antes invisibles, incluido
el MISMO caso "optional issuer fee" → "See Visa Issuer FX Calculator" ya visto en el manual 1
(confirma nuevamente que ambos manuales comparten el mismo glosario fuente).

### Item 7 (V0407): causa raíz real distinta a la logueada, y 1 intento descartado

Investigando antes de arreglar, se encontró que la causa raíz original logueada ("el tramo de
palabras que desaparece tiene menos de 5 palabras") no era precisa: `_find_disappeared_content`
NUNCA miraba los opcodes `"replace"` de `difflib.SequenceMatcher`, solo `"delete"` -el cambio real
de V0407 (`"EQUALS B OR"` → `"EQUAL TO"`) es un `replace` de 3 palabras, invisible a la red de
seguridad sin importar el umbral configurado.

**Primer intento (prompt engineering) probado y DESCARTADO**: se agregó una instrucción al prompt
pidiendo prestar atención a listas de valores permitidos. Probado aislado contra V0407: funcionó
(clasificó correctamente `business_rule_change`). Pero validado contra 4 casos ya conocidos de
`editorial_reword` correcto (fichas `V1232`/`V1235`/`V1236`/`V1245`, renombres de campo del tipo
"Installment Payment Indicator" → "Payment Indicator" sin cambio de valores) el modelo empezó a
clasificar TAMBIÉN esos como `business_rule_change` -una regresión real y medida, no hipotética.
Se probó una segunda redacción del prompt, más específica sobre "listas separadas por O/Y", con el
mismo resultado (el modelo alucinó "listas de valores" donde no las había, ej. "se removió
'INSTALLMENT' de la lista de valores permitidos"). Descartado -revertido al prompt original.

**Fix real, en la red de seguridad (determinístico, no depende del LLM)**: `_find_disappeared_content`
ahora cuenta `"replace"` igual que `"delete"`, con el MISMO umbral de 5 palabras (sin bajarlo).
Antes de aceptar el fix se escaneó el corpus completo buscando opcodes `replace` de 3+ palabras
para medir el riesgo de falsos positivos -se encontraron varios casos de 3-4 palabras que son
renombres/abreviaturas inocuos (`"the Edit Package"` → `"VCX"`, `"Interchange Transaction File"`
→ `"ITF"`, `"digits in length."` → `"digits."`) que NO deben dispararse -confirma que bajar el
umbral también habría sido inseguro, se dejó en 5. Con el umbral en 5, los casos que SÍ se
capturan son genuinos: ficha `V1209` (7 palabras, `"Fee Collection | Funds Disbursement"`
desaparece de `transaction_types` sin dejar rastro) y la entrada de glosario `optional issuer fee`
(41 palabras, definición completa reemplazada por una referencia cruzada) -ambos confirmados
`business_rule_change` con `safety_net_override=True` en la corrida real.

**V0407 sigue sin arreglar** (su replace es de 3 palabras, bajo el umbral de 5) -se mantiene la
evaluación original del TODO: muy baja prioridad, cosmético, el mismo hecho de negocio ya está
bien capturado en el campo `description` de la misma ficha.

### Corrida completa final

Módulos 1→5 y 7 re-corridos con los 2 fixes juntos (glosario + safety-net replace-aware) en las 9
ediciones / 8 pares. Módulo 5: 0 errores, `safety_net_override` total = 4 (1+0+1+1+0+1+0+0).
Módulo 7 regeneró los 8 reportes sin errores (3/19/5/5/6/2/0/9 cambios de negocio por par). Se
verificó el reporte de `optional issuer fee` -renderiza correctamente con la marca ⚠️ de
override. Se grepeó `"cook island"` (regresión ya conocida de otro manual, chequeo de hábito) -0
resultados en los 8 reportes de este manual (nunca aplicaba aquí, pero confirma que no se filtró
nada raro).

**Nota para cuando se retome el proyecto**: el mismo gap de `_find_disappeared_content` (solo
mira "delete", nunca "replace") probablemente existe también en `base_ii_clearing_data_codes`
(manual 1) -mismo código, casi idéntico entre los 2 manuales. NO se tocó el manual 1 esta sesión
(fuera del alcance pedido, y ya se había cerrado la sesión anterior) -queda anotado como
candidato a revisar si se retoma ese manual.

---

## 2026-08-25 (cont. 5) — Manual 3 (`tc_01_to_tc_49`): decisión sobre items 8/9

El usuario preguntó por lo pendiente del manual 3 (`base_ii_clearing_interchange_formats_
tc_01_to_tc_49`). Se le explicó la diferencia real entre los 2 items abiertos: el item 8
(chain-shift, ver TODO.md) SÍ es arreglable -es una decisión de priorización ya tomada con
evidencia (0.05% de los casos), no una limitación técnica, la mitigación de ancla ordinal ya
está diseñada- mientras que el item 9 (etiquetas "Note:" faltantes en la capa de texto del PDF
de la edición `20260418`) NO es arreglable con el enfoque actual: el texto directamente no
existe en la capa de texto extraíble, haría falta OCR (herramienta distinta, fuera de alcance).
El usuario pidió explícitamente anotar el item 8 para más adelante y pasar al manual 4 -no se
tocó código de este manual en esta sesión.

## 2026-08-25 (cont. 6) — Manual 4 (`tc_50_to_tc_92`): items 10, 11 y 12 resueltos

El usuario pidió avanzar con los 3 items pendientes del manual 4 (mismo manual "hermano" del
3, mismos 2 patrones mezclados por sección: grilla Record Layout + fichas Edit Criteria).

### Item 12 (ficha `"(continued)"` fragmentada) — investigado y arreglado primero

Se confirmó el caso real completo con `fitz` directo sobre `20220423`: el campo `"BASE II
Customized Delivery File Type"` @ 109-113 (sección `"TC 90 - TCR 0 - Incoming ITF"`) tiene su
lista `Values:` repartida en 3 páginas (354/355/356), cada continuación redeclarando la ficha
completa con el sufijo `"(continued)"` en el nombre en vez de continuar el texto inline.

**Fix inicial**: en Módulo 2 (`build_blocks`), cuando una ficha nueva trae `"(continued)"` en
el nombre Y su `Positions:` coincide EXACTO con la última ficha ya emitida (`blocks[-1]`), se
reabre esa ficha (`blocks.pop()`) en vez de crear una nueva.

**Bug real encontrado validando el fix** (no en el diseño): el primer intento dejaba la ficha
reabierta con SOLO el contenido de su 1ra página -las páginas 355/356 no aportaban nada nuevo.
Investigado con un harness de debug que reconstruye `build_blocks()` con prints inyectados
sobre los datos reales de Módulo 1: se confirmó que el layout de 2 columnas de este manual
hace que la PRIMERA línea de la columna derecha de la continuación (`"Note:  Values
continued:"`, Y=97.1) se procese ANTES que el `"Positions: 109-113"` de esa misma continuación
(Y=124.1) -mismo mecanismo de reordenamiento por banda Y que el resto del documento usa para
capturar una `Description:` que arranca en la misma fila que el nombre del campo
(`same_row_as_next_name`/`pending_right`)- así que ese contenido quedaba bufereado en
`pending_right`, y el primer fix lo descartaba silenciosamente al hacer `pending_right = {}`
sin fusionarlo antes al `active_card` reabierto. Arreglado fusionando `pending_right` en el
`active_card` reabierto, igual que ya hace el camino de "ficha nueva" un poco más abajo en el
mismo bloque de código.

**Verificado**: 0 fichas `"(continued)"` sin fusionar en las 9 ediciones completas (escaneo
explícito). La ficha fusionada de `20220423` trae las ~70 opciones de `Values:` completas
(`note` con 1685 caracteres, antes 224). 0 fichas con contenido totalmente vacío en ninguna
edición (chequeo de regresión general).

### Item 11 (título de tabla-ficha filtrado en la descripción del primer campo)

Investigado con `fitz` directo sobre `20231014` p.36: el título "Text Message Commercial Card
- Passenger Itinerary Data - Leg-Specific Edit Criteria" (10.5pt, prosa) se extrae partido en
2 fragmentos que comparten la MISMA banda Y (mismo `source_block` de PyMuPDF, confirmado con
`line_id`) -un quirk de layout, no un patrón de separador reconocible como los ya vistos en
otros fixes de este proyecto (no hay un span de solo-espacio, no hay salto de tamaño de fuente
entre los 2 fragmentos, ambos son 10.5pt Bold).

**Hallazgo clave, cambia todo el enfoque del fix**: el 2do fragmento del título (bien a la
derecha, X0=385.9) dispara la MISMA condición `same_row_as_next_name` que Módulo 2 usa como
mecanismo PRINCIPAL (no un caso raro) para capturar la 1ra línea de `Description:` de un campo
real que comparte fila con su propio nombre -confirmado con un harness de instrumentación que
corrió `build_blocks()` real sobre las 9 ediciones completas: 18167 disparos legítimos de este
mecanismo en TODO el documento. El título, al compartir accidentalmente la misma banda Y que
su propio primer fragmento (ya acumulado como `active_paragraph`), se ve geométricamente
IDÉNTICO a "nombre de campo + descripción en la misma fila" y se cuela en `pending_right`,
para terminar pegado al frente de la descripción real del PRÓXIMO campo (`Transaction Code`).

**Señal usada para distinguir, encontrada comparando tamaños de fuente reales**: nombres de
campo reales siempre son 9.0pt; el título de tabla-ficha es 10.5pt. Confirmado con el mismo
escaneo completo: de los 18174 disparos de `same_row_as_next_name` en las 9 ediciones, 18167
son a 9.0pt (legítimos), y exactamente 7 a 10.5pt -6 de ellos el bug ya conocido (2 por
edición en las 3 afectadas: uno para el título de la GRILLA que no causa daño visible porque
la grilla no usa `pending_right`, otro para el título de las FICHAS que sí lo causa), más 1
caso adicional no logueado antes (`20230415` p.288, un párrafo narrativo de 2 líneas
terminando en un guion de corte de palabra "...BASE" / "II System...", que tampoco parecía
causar daño visible en el reporte final pero de todos modos quedaba mal capturado).

**Fix**: se agrega `"size"` a `active_paragraph` en su creación (todas las instancias), y se
excluye `same_row_as_next_name` cuando `active_paragraph["size"] == TITLE_PARAGRAPH_FONT_SIZE
(10.5)`.

**Verificado**: Módulos 1→5 y 7 re-corridos en las 9 ediciones. Los 92 `field_card` de
`"Transaction Code"` (nombre repetido en muchas secciones distintas) confirmados limpios en
las 3 ediciones antes afectadas -0 con "Edit Criteria" colado. 0 fichas con contenido
totalmente vacío (mismo chequeo de regresión general que el item 12).

### Item 10 (2 layouts distintos bajo el mismo título "TC 57 - TCR 5 - Limited Use Data")

La pérdida de datos YA estaba mitigada desde el 2026-08-19 (emparejamiento por orden de
aparición). Lo que quedaba: sin forma de saber "cuál layout es cuál" ni darles una etiqueta
legible. Investigado con `fitz` directo sobre las 9 ediciones: las 2 ocurrencias tienen
siempre el mismo par de campos distintivos, en el mismo orden -variante 1 arranca con `Local
Tax` @ 5-13, variante 2 con `Reserved` @ 5-15 seguido de `Banknet Settlement Number` @ 16-24
(confirmado en TODAS las 9 ediciones, un desvío inicial del script de investigación -que
buscaba en la página equivocada por un salto de página no considerado- se corrigió antes de
aceptar el patrón como estable).

**Fix**: `_section_signature()` en Módulo 3 -toma el nombre del primer campo de la grilla
(ordenada por posición) que NO sea parte del preámbulo común a TODA sección de este manual
(`Transaction Code`/`Transaction Code Qualifier`/`Transaction Component Sequence Number`) ni
`Reserved` (el campo más genérico posible -confirmado que casi nunca es el distintivo real,
como en este mismo caso: `Reserved` @ 5-15 no distingue nada, `Banknet Settlement Number` @
16-24 sí). Cuando un título colisiona (2+ secciones en `by_title`), AMBOS lados se reordenan
por esta firma antes de emparejar por posición -reemplaza el emparejamiento por "orden de
aparición" (frágil si una edición futura reordenara las 2 ocurrencias) por uno anclado al
contenido real. Módulo 4 propaga `signature` a cada `change` de la sección (tageado post-hoc
de todos los cambios generados durante el procesamiento de esa sección, para no tocar cada
`changes.append` individual). Módulo 7 usa `(title, signature)` como clave de agrupación en
vez de solo `title`, y agrega un sufijo `"— variante con campo «X»"` al encabezado SOLO
cuando ese título realmente tiene mas de 1 signature distinta en ese render puntual (nunca
ensucia el caso común, la inmensa mayoria de titulos sin colision).

**1 bug propio encontrado y arreglado con una prueba sintética** (ningún par real de los 8
tiene un cambio de contenido en esta sección puntual para poder verlo con datos reales): el
primer intento de `_heading_for_group` comparaba el TÍTULO de cada grupo contra sí mismo en
vez de contar `signature`s distintas -nunca disparaba el sufijo desambiguador, cualquier
título con colisión real hubiera seguido mostrando el mismo encabezado ambiguo de siempre.
Detectado corriendo la función con datos sintéticos simulando la colisión real (2 items,
mismo título, `signature` distinta) antes de dar el fix por bueno -mismo hábito de "no
confiar en que compila = que funciona" ya aplicado en otros fixes de este proyecto.

**Verificado**: Módulos 1→5 y 7 re-corridos en las 9 ediciones, 0 errores, 0 cambios en los
conteos de matching (el orden ya era estable, el fix es una salvaguarda a futuro sin efecto
en los datos actuales). `signature_a`/`signature_b` confirmados como
`Local Tax`↔`Local Tax` y `Banknet Settlement Number`↔`Banknet Settlement Number` en los 8
pares -nunca cruzados. La etiqueta desambiguadora en el reporte se validó con datos
sintéticos (`_render_content_changes`/`_render_field_transitions`), no con un reporte real
(no hay contenido cambiado ahí en estas 9 ediciones).

**Residuo, no arreglado**: la etiqueta sigue siendo un nombre de campo real (`Local Tax`),
sin significado de negocio propio -alcanza para desambiguar el emparejamiento y el reporte,
no para explicar POR QUÉ existen 2 layouts bajo el mismo título (seguiría haciendo falta leer
el PDF fuente para eso). Aceptado como suficiente por el usuario implícitamente (pidió
"avancemos con los 3", no pidió más después de ver el resultado).

**Con esto, los 3 items pendientes del manual 4 quedaron resueltos** (10 parcialmente -ver
residuo arriba-, 11 y 12 completos). Pipeline completo (Módulos 1→5, 7) re-corrido y validado
de punta a punta después de los 3 fixes juntos, 0 errores en las 9 ediciones / 8 pares.

---

## 2026-08-25 (cont. 7) — Manual 6 (`international_full_service_pos...`): item 13 generalizado a N:M

El usuario preguntó por lo pendiente del manual 5 (`base_ii_transactions_quick_reference`) -se
confirmó que no tiene ningún ítem logueado, pipeline cerrado limpio sin residuos. Pasó
entonces al manual 6, que comparte el ítem 13 con el manual 7 (re-corte de párrafos por
reflow de página). Preguntó si el ítem "se puede levantar" -se le explicó que sí, es una
decisión de alcance ya tomada (no una limitación técnica como el ítem 9 del manual 3), y pidió
implementarlo.

### Investigación: encontrar un caso 2:2 real antes de diseñar

Se leyó primero el código existente (`_reflow_matches`, versión 2:1 del 2026-08-19) para
entender su alcance exacto. Se investigaron los 7 casos de `safety_net_override` del par
`20230415→20231015` (el más grande) con `fitz`/datos de Módulo 2 directos, buscando uno que
fuera un reflow genuino no cubierto. La sección "Card Verification Value (CVV) Service" lo
confirmó: en la edición vieja, el párrafo grande de la ficha termina con "...Acquirers of all
Visa card products must provide complete, unaltered magnetic stripe data...0200 financial
messages." y el SIGUIENTE párrafo es una oración totalmente distinta ("The CVV Service allows
issuers to detect invalid cards..."); en la edición nueva, esas 2 oraciones se reagrupan al
revés (la primera se separa del párrafo largo, la segunda se le pega detrás). Confirmado
programáticamente: `A[0]+A[1]` concatenado (normalizado) es IDÉNTICO a `B[0]+B[1]`
concatenado, pero ningún sub-par 1↔2 (el diseño 2:1 original) podía encontrarlo, porque no es
una simple fusión/división -es una REDISTRIBUCIÓN del contenido entre 2 párrafos que ya
existían de los 2 lados.

### Diseño validado con datos reales antes de implementar

Se probó `difflib.SequenceMatcher` a nivel de PÁRRAFO (lista de textos normalizados como
unidad atómica, no palabra ni carácter) sobre la sección más grande del corpus (471-482
párrafos, "Multicurrency Field Flows") para medir performance y comportamiento real antes de
comprometerse al diseño: 0.001s (sin problema de escala, ni con `autojunk=True` ni `False` -se
eligió `False` de todas formas, más seguro ante contenido muy repetido como los fragmentos de
tabla convertidos a párrafo). Los opcodes `"replace"` encontrados en esa sección incluyeron
un caso 2:1 real (confirmando que el nuevo diseño sigue cubriendo el caso ya resuelto) y varios
bloques con texto genuinamente distinto (correctamente NO marcados como reflow, cayendo al
fuzzy-matching de siempre) -validó el diseño ANTES de tocar el código de producción.

### Fix implementado

`match_paragraphs` rediseñado: en vez de (a) un dict de texto exacto con zip por orden de
aparición + (b) una búsqueda separada de pares adyacentes 2:1, corre UN SOLO
`SequenceMatcher(None, texts_a_norm, texts_b_norm, autojunk=False)`. Sus opcodes ya resuelven
todo: `"equal"` = párrafos idénticos en el mismo orden relativo (más robusto que el dict+zip
anterior ante duplicados intercalados, porque el alineamiento LCS ya lo resuelve).
`"replace"` (bloque de N párrafos de un lado, M del otro) = candidato a reflow -se concatena
el texto COMPLETO de ambos bloques; si coincide exacto (normalizado), es reflow N:M puro
(cubre el 2:1 original como caso particular, sin código especial para él) y se emite en
`paragraphs_reflowed`; si no coincide, ambos lados del bloque completo pasan al pool de
fuzzy-matching de siempre -mismo comportamiento que antes para contenido que sí cambió,
ninguna regresión ahí. `"delete"`/`"insert"` = mismo pool de fuzzy. Limitación aceptada
conscientemente: un bloque `"replace"` MIXTO (reflow + cambio real en el mismo tramo) no se
sub-divide, cae entero a fuzzy -no se justificó una búsqueda recursiva sin evidencia real de
que ocurra (no se encontró ningún caso así validando el fix).

### Verificación de punta a punta

Módulos 3→5 y 7 re-corridos en las 6 ediciones / 7 pares (Módulo 5 con Ollama, ~249 items,
~73 minutos por ser párrafos largos de prosa, más lento que otros manuales de tablas/fichas).
0 errores. Se encontraron 18 casos reales de reflow N:M genuino más allá del simple 2:1 (hasta
5↔4 en una sección, "Echo Test Message"), incluido el caso CVV confirmado a mano -verificado
directamente en el output que ese caso pasó de `paragraph_content_changed` (con
`safety_net_override=True`, forzando `business_rule_change` falso) a `paragraph_reflowed`
limpio. `safety_net_override` total bajó de 14 (baseline ya logrado por el fix 2:1 original)
a 10 en los 6 pares. Chequeo de regresión: el hallazgo ya validado del rename "Exception
File"→"ASAF" (8 instancias, ver progreso del manual 6) sigue apareciendo igual en el reporte
final -mismo conteo, sin cambios.

**El residuo del 7mo manual (`visanet_settlement_service_vss_user_guide_volume_1_
specifications`) NO se tocó esta sesión** -tiene su propia variante del mismo problema
(nombre+descripción fusionados en un campo `name` de un par Field Name/Description, distinto
al reflow de párrafo narrativo de este manual) que necesitaría su propia investigación antes
de decidir si este mismo mecanismo aplica ahí tal cual o hace falta algo distinto.

## 2026-08-26 — Manual 7, item 13/14: fix de fusión nombre+descripción en pares rotados

Sesión nueva, pedido explícito del usuario de retomar el orden acordado (manual 7 primero,
manual 8 después). Se investigó la variante propia de este manual del item 13 -ver nota de
arriba, "necesitaría su propia investigación"- ANTES de asumir que el mecanismo
`SequenceMatcher` del manual 6 aplicaba.

### Investigación (antes de tocar código)

Se contaron las descripciones vacías actuales: 109 (ediciones `20220423`-`20230415`) / 82
(`20231013`-`20251017`) de 236 pares totales -coincide con lo logueado en el item 14
original. Se tomó el caso más largo/claro (`"CARDHOLDER BILLING AMT CUR Clearing currency. On
the VSS reports, clearing currency is "NONE" when reporting nonfinancial transactions."`,
pág. 112, edición `20251017`) y se inspeccionaron sus spans crudos con `fitz` directamente
(sin pasar por Módulo 1): 3 spans, `'CARDHOLDER BILLING AMT CUR'` (9.0pt) + `' '` (span de
PURO espacio, 9.0pt) + `'Clearing currency. ...'` (9.0pt), los 3 en la MISMA `line` de
PyMuPDF. Exactamente el mismo patrón del item 2 (Cook Islands, manual 1) -2 celdas lógicas
distintas fusionadas por PyMuPDF con un span de solo-espacio de separador, salvo que acá pasa
en texto ROTADO (`dir=(0,-1)`) en vez de horizontal.

**Escaneo del corpus completo (6 ediciones) antes de decidir el alcance del fix**:
- Confirmado el mismo patrón (span interno de puro espacio en una línea rotada de 3+ spans)
  en 56-57 líneas por edición en total. De esas, solo 9-10 por edición caen en páginas que
  Módulo 2 ya reconoce como la tabla de referencia real (llevan el literal `"Field Name"`) -el
  resto (tabla jerárquica SRE descartable, tablas de comparación de reportes, etc.) cae en
  páginas que Módulo 2 YA descarta enteras sin ese literal, así que dividirlas o no es
  irrelevante para el output final.
- Las 9-10 instancias reales por edición son extremadamente uniformes: SIEMPRE exactamente 3
  spans (nombre/espacio/descripción), SIEMPRE 9.0pt uniforme -patrón limpio y seguro de
  generalizar sin arriesgar falsos positivos.
- Se buscó el mismo patrón en texto HORIZONTAL también (para decidir si extender el fix
  ahí): 220-224 hits por edición, pero TODOS son líneas de tabla de contenidos (dot-leader,
  patrón `"Título. . . . . 13"`, ya filtradas completas por `TOC_DOT_LEADER` en Módulo 2) salvo
  26 hits que resultaron ser una tabla horizontal "Report ID / Report Title" (págs. 46-50) cuyo
  contenido fusionado ya era un residuo ACEPTADO explícitamente en sesiones previas (nota del
  asistente en el reporte de Módulo 7, "read as short report-name/description table
  fragments... not a new bug worth chasing given the scope already invested here"). Se decidió
  NO tocar texto horizontal -dividir las líneas de TOC arriesgaría el mismo problema que en el
  manual 1 (el fragmento sin los puntos ya no matchea `TOC_DOT_LEADER` y se cuela como
  contenido real), y tocar la tabla horizontal reabriría un scope ya cerrado sin que el usuario
  lo pidiera.

### Fix implementado

En `01_ingesta_parseo/ingest.py`: se portó `_split_line_segments`/`_segment_bbox` del manual 1
(divide los spans de una línea en segmentos separados por cualquier span de puro espacio,
descartando el espacio, cada segmento con su propio bbox recalculado desde sus propios spans),
pero ACOTADO a llamarse solo cuando la línea es rotada (`dir == (0.0,-1.0)`) -el texto
horizontal sigue exactamente el camino de código original, sin cambios de comportamiento ahí.

### Verificación de punta a punta

Módulo 1 re-corrido en las 6 ediciones, 0 errores (mismos avisos preexistentes de tamaño de
página mixto, no relacionados). Módulo 2: descripciones vacías bajaron de 109→101 (ediciones
viejas) y 82→73 (ediciones nuevas) -exactamente los 8-9 casos reales por edición encontrados
en la investigación. 236 pares totales sin cambio en ninguna edición (no se crean pares
fantasma). Se confirmó a mano que los 9 casos previamente fusionados en la edición `20251017`
(`CARDHOLDER BILLING AMT CUR`, `TOTAL ISSUER TRANSACTIONS`, `ACQUIRER TRANSACTION DETAIL`,
`INTERNATIONAL SETTLEMENT SERVICE` ×4, `RECEIVED FROM VISA AND SENT TO SETTLEMENT`,
`ACCEPTED COUNT`) ahora tienen su descripción correcta y separada.

Módulo 3 (matching): 236/236 pares matcheados en las 5 comparaciones, 0 agregados/eliminados
-sin regresión, coincide con la baseline ya validada (236/236 en 4 de 5 pares).

Módulo 4 (detección): el par grande (`20230415→20231013`) subió de 39 a 41
`pair_content_changed` -investigado ANTES de asumir que era una regresión. Se verificó que
ninguna de las líneas involucradas en los 2 nuevos casos (`"CLEARING AMOUNT"` / `"[CLEARING
AMOUNT]"` en la tabla "Example 5", págs. 129/131 en `20231013`) estaba entre las líneas que mi
fix dividió en ninguna de las 2 ediciones del par -se inspeccionaron los spans crudos de esa
página directamente y se confirmó que es un problema PREEXISTENTE, no relacionado: una
descripción larga que envuelve a una 2da sub-banda de `x0` dentro de la misma celda rotada
(cuerpo del texto en `x0=157.4`, cola envuelta `"SMS600C report."` en `x0=169.4`, deltas de
~12pt) queda tratada por `_extract_rotated_pairs` como 2 "filas" (bandas de `x0`) distintas en
vez de 1 sola descripción continua -mismo residuo ya logueado en el item 14, ahora con causa
raíz más precisa (no es solo "emparejamiento imperfecto" genérico, es específicamente el
wrap-a-2da-banda-de-x0 sin manejar). Se decidió NO perseguir este mecanismo más profundo ahora
-mismo criterio de diminishing-returns para POC ya aplicado 2 veces antes en este mismo item.

Módulo 5 (LLM, Ollama, 154 items, ~50 min corrido en background): `safety_net_override` = 2
total (idéntico a la baseline previa al fix) -0 regresión. El caso `ACCEPTED COUNT` (uno de
los recién arreglados) se clasificó correctamente como `extraction_noise` en el reporte final,
no como falso `business_rule_change`.

Módulo 7 (reporte): mismos 0/2/7/2/0 cambios de negocio por par que la baseline ya validada
-sin regresión. Confirmado en el reporte final que los casos arreglados aparecen limpios en el
apéndice de ruido/redacción, no en la sección de cambios de negocio.

**Con esto, el item 13 (variante del manual 7) queda RESUELTO** -ver índice reescrito en
`TODO.md`, item 14. El residuo restante (wrap-a-2da-banda-de-x0 + sub-encabezados `Row`/
`Column` legítimos) sigue abierto, deliberadamente no perseguido, mismo criterio de siempre.

**Siguiente paso pedido por el usuario**: seguir con el manual 8 (items 15/16/17), según el
orden acordado al cierre de la sesión anterior.

## 2026-08-27 — Módulo 8: reporte web consolidado (nueva pieza del pipeline, no un bug fix)

### Pedido del usuario

El usuario quiere mejorar cómo se consumen los reportes de cambios: hoy cada uno de los 8
manuales tiene su propio `07_reporte_cambios/report.py` que genera un `.md` por par de ediciones
+ un `index.md`, y para ver el estado actual hay que abrir 8 carpetas distintas. Pidió una
mini-web local (HTML con pestañas) — una pestaña "general" con los cambios sin tanto detalle de
cada manual, y una pestaña por manual con el detalle — cubriendo siempre el ÚLTIMO par de
ediciones de cada uno. Pidió explícitamente que esto sea un "Módulo 8" nuevo, con su propio POC,
en la misma línea que el resto del pipeline.

Antes de escribir nada se hicieron 2 preguntas de alcance (vía `AskUserQuestion`, no asumidas):
(1) ¿cada pestaña de manual muestra solo el último par o necesita selector histórico? →
**solo el último par**. (2) ¿la pestaña general lleva solo conteos o conteos + destacados? →
**conteos + destacados**.

### Investigación previa (crítica para el diseño, hecha ANTES de escribir cualquier adaptador)

Se leyeron los 8 `07_reporte_cambios/report.py` completos (no solo el JSON de salida) para
portar la lógica de agrupamiento exacta, no reinventarla. Hallazgo central, confirmado archivo
por archivo:

**Los 8 manuales NO comparten un esquema real de Módulo 5.** Tabla exacta:

| Manual | `change_type` de "cambio de negocio" | identificador | agrupador |
|---|---|---|---|
| `base_ii_clearing_data_codes` | `code_content_changed` | `code`+`column` | `table` |
| `base_ii_clearing_edit_package_messages` | `ficha_content_changed` | `code`+`field` | `code` (título releído de Módulo 3, no viene en el cambio) |
| `..._interchange_formats_tc_01_to_tc_49` | `row_content_changed`/`card_content_changed` | `position`(+`column`/`field`) | `title`→`position`; `field_became_defined`/`field_became_reserved` van PRIMERO (caso de uso central del proyecto) |
| `..._interchange_formats_tc_50_to_tc_92` | ídem + `signature` (desambigua títulos duplicados, ver item 10) | ídem | `(title,signature)`→`position` |
| `base_ii_transactions_quick_reference` | **no existe** — Módulo 5 es no-op a propósito (`row_content_changed` nunca ocurre por diseño de la clave de emparejamiento de Módulo 3); `changes` es solo `row_added`/`row_removed` con `title`(TC)+`cells`(TCR+desc) | — | `title` |
| `international_full_service_pos_online_messages_...` | `paragraph_content_changed` | ninguno (párrafo completo) | `path` (ruta de sección) |
| `visanet_..._volume_1_specifications` | `paragraph_content_changed` / `pair_content_changed` | `name`+`example_title` para pares | `path` |
| `visanet_..._volume_2_reports` | anidado bajo `appendices.appendix_[a-e]` (listas planas, SIN `summary`/`changes` de nivel superior — hubo que confirmar esto con `python3 -c` antes de asumir uniformidad) | `key`+`column` | `(appendix, table_title)` |

También se confirmó con un script rápido que `ai_summary` (presente en los 8) es solo un tally
`{categoria: count}`, no un texto narrativo — no sirve como "resumen listo para usar", hay que
derivar destacados desde `changes`/`appendices` igual que hace cada `report.py`. Y que el
`index.md` de cada manual tampoco es uniforme (2 de 8 tienen la tripleta completa altas/bajas/
negocio, el resto usa vocabulario propio o le faltan campos) — no sirve como fuente única para
la pestaña general, hubo que leer el JSON de Módulo 5 directo en cada adaptador.

### Decisión de diseño

Dado que no hay esquema común real, Módulo 8 se construye igual que el resto del pipeline: un
adaptador chico y bespoke por manual (`poc/08_reporte_web_consolidado/adapters/`), no un parser
genérico único — mismo principio ya anotado en la memoria del asistente como
"bespoke-parsers-vs-framework" para el diseño de producción futuro. Los 2 manuales de grilla
(TC 01-49 y TC 50-92) SÍ comparten un adaptador (`interchange_formats_grid.py`) porque ahí el
esquema es genuinamente idéntico (confirmado leyendo ambos `report.py` lado a lado) — única
reutilización real entre manuales, el resto queda separado.

Contrato común que devuelve cada `summarize(data, manual_dir, pair_filename) -> dict`:
`{edition_a, edition_b, headline, secondary, groups, top_items}`. `headline`/`secondary` usan el
vocabulario NATIVO de cada manual (ej. "Cambios de negocio a revisar" vs. la métrica de TCR de
`quick_reference`) — no se fuerza un vocabulario uniforme que no existe. `top_items` son los
primeros 3 ítems en el orden de agrupamiento ya existente — deliberadamente NO se inventa un
score de "importancia" sin datos que lo justifiquen, queda anotado como simplificación de POC.

Página final autocontenida: el JSON de datos se embebe en base64 dentro de un `<script>` inline
(decodificado con `atob`+`TextDecoder` para sobrevivir tildes/ñ/emoji sin escapes raros) en vez
de usar `fetch()` a un JSON externo — así el archivo abre con doble-click desde el explorador de
archivos sin disparar el bloqueo CORS de `file://` que rompería un `fetch()` local.

### Implementación

- `adapters/_common.py`: 3 helpers realmente compartidos (`fmt_date`, `short_name` para truncar
  nombres de tabla largos igual que el manual 1, y `make_item`/`make_group`/`top_items`).
- 7 adaptadores (uno por manual, compartido entre los 2 de grilla), cada uno portando la función
  de agrupamiento exacta de su propio `report.py` (`_group_by_table`, `_dedupe_field_
  transitions`, `_flatten`+`_group_by_appendix_table`, etc.) en vez de reinventarla.
- `build.py`: registro de 8 entradas, toma el último JSON de `data/05_interpretacion_cambios_ia/`
  por orden alfabético de nombre (mismo criterio implícito que ya usa cada `index.md`), llama al
  adaptador, arma `{generated_at, manuals:[...]}`, escribe el JSON intermedio y renderiza
  `template.html` reemplazando `__DATA_B64__`.
- `template.html`: pestañas en JS vanilla (sin librerías), tarjetas por manual con chips de
  conteo + lista de destacados en la pestaña general, y el detalle completo (`groups`) en cada
  pestaña de manual — mismo nivel de detalle que el `.md` existente (antes/ahora/razón IA,
  marca ⚠️ para `safety_net_override`), pero navegable en vez de archivos sueltos.

### Verificación de punta a punta

`python3 build.py` corrió sin errores para los 8 manuales. Se verificó con scripts puntuales
sobre `data/reporte_consolidado.json` (no solo mirando el HTML):
- Los 8 conteos de "cambios de negocio a revisar"/métrica equivalente coinciden EXACTAMENTE con
  los que ya mostraba cada `index.md` (42/9/79/5/502 TCR/4/0/9).
- `base_ii_clearing_data_codes`: el grupo "Country and Currency Codes" trae a Bulgaria con su
  texto antes/ahora completo (`'Bulgarian Lev'`→`'EuroS'`), no truncado.
- `base_ii_transactions_quick_reference` (el único sin `ai_category`): no se rompe ni queda una
  sección vacía — muestra su propia métrica de TCR, y el caso conocido de "posible renombre no
  detectado" (delta neto 0 con altas Y bajas) sigue marcado `flagged=true` igual que en su
  `report.py`.
- Manuales de grilla: el grupo "Reserved → definido" aparece primero en la lista de grupos (antes
  que los cambios de negocio genéricos), reflejando la prioridad que el proyecto le da a esa
  transición como caso de uso central.
- HTML final: 196 KB, sin placeholder `__DATA_B64__` sin reemplazar, 1 solo `<script>` bien
  cerrado.

Entregado al usuario vía `SendUserFile` para que lo abra y confirme visualmente (paso pendiente
de su lado — esta sesión no incluyó una captura de navegador real, solo verificación de datos/
estructura).

### Fuera de alcance (decisión explícita, no descuido)

Selector de pares históricos por pestaña (el usuario eligió "solo el último par" cuando se le
preguntó). Ninguna relación con el diseño de router de producción pendiente desde el 2026-08-20
— esto es tooling de POC sobre la salida ya existente de Módulo 7, no toca los Módulos 1-5 de
ningún manual ni el diseño de arquitectura real.

**Siguiente paso**: esperar confirmación visual del usuario sobre el HTML; si aprueba, retomar
la cola pendiente (manual 8 items 15/16/17, residuos de baja prioridad, o el diseño de router de
producción) según lo que el usuario priorice.

---

# 2026-09-03 a 2026-09-06 — Sesión extendida: paso de POC a desarrollo real, router de
producción, y cierre de todos los residuos cosméticos pendientes

Este bloque cubre varias sesiones seguidas que este archivo no había registrado (última entrada
antes de esta: 2026-08-27, Módulo 8). Mientras tanto, la memoria persistente del asistente
(`~/.claude/.../memory/*.md`, sistema separado de este archivo) sí se fue actualizando en cada
sesión — ese es hoy el registro más completo y actualizado de todo lo que sigue; acá se resume
lo accionable, sin repetir cada detalle de evidencia (ver los archivos de memoria referenciados
en cada sección para el detalle completo, especialmente `pending-bug-fixes.md`,
`dev-phase-considerations.md`, `router-landing-progress.md` y `module8-web-report.md`).

## 2026-09-03/04 — Fin del POC, arranque de "desarrollo real": Tier 1 y router

El usuario declaró explícitamente el fin de la fase de POC. Dos piezas grandes:

**Tier 1 (`poc/_shared/`)**: inventario real de duplicación entre los 48 scripts de etapa de
los 8 manuales (no intuición) — confirmó que `main()` de Módulos 1 y 4 es byte-idéntico en 7 de
8 manuales, y que el cliente HTTP de Ollama es casi idéntico en los 7 manuales con IA. Al
consolidar esto, se encontró que una afirmación previa de la memoria ("el fix de replace-opcode
ya está portado a todos") era FALSA — re-verificado contra el código real, solo 2 de 7 manuales
lo tenían, un bug de correctitud activo (un párrafo/fila REEMPLAZADO por texto no relacionado
pasaba invisible a la red de seguridad en 5 manuales). Se arregló consolidando en vez de portear
a mano una vez más (`poc/_shared/stage_runners.py` + `poc/_shared/ollama_client.py`), midiendo
el impacto antes de gastar Ollama (14 reclasificaciones concretas predichas, confirmadas). Ver
`TODO.md` item 21 para el resumen accionable completo.

**Router (`poc/router/`)**: la arquitectura de producción pedida desde el 2026-08-20 por fin se
diseñó y construyó. `run.py` descubre las etapas de cada manual por glob (confirmó que un
contrato de facto ya existía sin haber sido diseñado a propósito). `land.py`+`detect_type.py`
detectan a qué manual pertenece un PDF nuevo (contención de subconjunto de palabras
normalizadas, no igualdad exacta) y lo incorporan al corpus. **Bug real encontrado por el
usuario, no por el asistente**, en la primera corrida end-to-end con Ollama real: `land.py`
re-clasificaba el historial completo de pares en cada landing en vez de acotarse al par nuevo
(un argumento hardcodeado a `None`) — arreglado en 1 línea, 10-100x menos llamadas a Ollama por
landing futuro. Documentado en `poc/router/CONTRACT.md`, la referencia técnica autoritativa
desde entonces.

## 2026-09-04/05 — Corrección de una nota de memoria errónea + no-determinismo real en Módulo 3

Validando el Tier 1 se encontró, de paso, un no-determinismo real (no relacionado al cambio que
lo expuso): 4 funciones en Módulo 3 de `visanet...volume_1`/`volume_2` iteraban `set()` sin
ordenar antes de construir la lista de salida, dando orden distinto en cada corrida —
confirmado con un diff canonicalizado que el CONTENIDO matcheado era idéntico, solo el orden
cambiaba. Fix: ordenar la fuente de iteración, no solo el resultado. Al verificar se encontró
que esto NO era solo cosmético: en 1 sección de 1 par, el orden pre-fix arbitrario había estado
eligiendo por casualidad un emparejamiento fuzzy distinto (aunque ambos superaban el umbral de
seguridad) — el usuario pidió loguearlo y decidió arreglar solo el determinismo por ahora.
Retomado el 2026-09-06 a pedido del usuario: la etapa fuzzy es greedy (no necesariamente
óptima globalmente) — se extendió el fix a las 4 funciones reales afectadas (2 más de las
originalmente identificadas), recolectando todos los candidatos y asignando en orden
descendente de similitud en vez de por orden de procesamiento. Ver `TODO.md` item 22.

## 2026-09-05/06 — Router: multi-par y edición única

**Multi-par**: el inbox de landing dejó de exigir exactamente 2 PDFs — agrupa por tipo
detectado y valida cada grupo por separado. Antes de implementar, se preguntó al usuario una
decisión de diseño real (no ya negociada): si un lote tiene varios grupos y UNO está mal
formado, ¿procesan los demás o se rechaza todo el lote? El usuario eligió explícitamente
todo-o-nada sobre el lote completo, por consistencia con el resto del proyecto, sobre la opción
más cómoda operacionalmente.

**Edición única**: el usuario pidió construir el modo que había quedado deliberadamente fuera
de alcance del diseño original del router — dejar caer 1 solo PDF (la edición nueva) y que el
sistema resuelva la edición vieja automáticamente contra la más reciente ya presente en el
corpus, sin que el usuario tenga que ir a buscarla. Implementado con la misma disciplina de
medir antes de tocar código de todo el proyecto: helper `_latest_corpus_edition`, validación
todo-o-nada preservada, verificado con datos reales no destructivos (camino de rechazo con
misma fecha, camino feliz con fecha ficticia posterior corriendo el pipeline completo end-to-end
y confirmando 0 diffs reales dado que era contenido idéntico).

## 2026-09-05 — Módulo 8: pestaña "Cambios recientes"

El usuario propuso un modelo de 2 fases (aterrizar cuantas veces haga falta / generar la web de
"anuncio" al cierre del día) y preguntó explícitamente la recomendación del asistente entre
reordenar "Resumen general" vs. agregar una pestaña dedicada — se recomendó y se construyó la
pestaña dedicada, para no arriesgar el comportamiento ya validado de las pestañas existentes.
`build.py` persiste el estado de la última publicación (`estado_publicacion.json`) y compara
contra él en cada corrida — cada corrida de `build.py` ES el evento de "publicar". Verificado:
primera corrida marca los 8 como nuevos, corrida idéntica siguiente marca 0, una prueba con
estado desactualizado simulado aisló exactamente el manual esperado.

## 2026-09-05 — Cierre de TODOS los residuos cosméticos de baja prioridad, uno por uno

El usuario pidió, en orden, listar todos los pendientes de baja prioridad que quedaban y
después atacarlos con una recomendación de por dónde arrancar (el de menor esfuerzo primero).
Los 4 se cerraron esta sesión, cada uno con la misma disciplina de "medir antes de tocar
código" ya establecida en todo el proyecto — el detalle completo, con la evidencia de cada
medición, ya está en `TODO.md` (items 3b, 7, 8, 10, actualizados in-place) y en la memoria del
asistente (`pending-bug-fixes.md`). Resumen:

- **Manual 4 (item 10), el de menor esfuerzo, elegido para arrancar**: el sufijo desambiguador
  de 2 layouts bajo el mismo título ganó la posición del campo distintivo además del nombre —
  cambio 100% aditivo, sin tocar matching. Al re-correr Módulo 5 completo se encontró, de paso,
  una clasificación desactualizada de 1 par (una corrección legítima del fix del item 21 que
  nunca se había re-verificado para ESE par puntual — no una regresión).
- **Manual 1 (item 3b, Zimbabue)**: cerrado en 2 pasadas el mismo día. Primera pasada
  (encabezado mayor de 26pt corta la tabla activa) resultó tener un alcance MUCHO más grande de
  lo pensado — el mismo bug afectaba otras 4 tablas del manual, no solo Zimbabue (una tabla
  fantasma que aparecía/desaparecía entre pares, una moneda mal atribuida a la tabla
  equivocada). Segunda pasada (señal de "mirar hacia adelante" para el residuo restante)
  encontró que 7 de los 8 casos reales en todo el corpus NO eran Zimbabue — eran la misma nota
  recurrente "Type D" fusionada en 2 tablas de disputas distintas.
- **Manual 2 (item 7, ficha V0407)**: en vez de bajar el umbral general (ya descartado antes),
  se midió una señal específica (conjunción + valor corto borrado) que dio exactamente 3
  coincidencias en todo el corpus, 0 falsos positivos, y encontró un 2do caso real
  (`V1073`) del mismo bug nunca antes detectado.
- **Manual 3 (item 8, chain-shift en fichas)**: en vez del fuzzy-matching genuino que se había
  descartado por riesgoso, la solución fue una normalización de texto puntual (quitar un guion
  usado como separador) reutilizando el mismo mecanismo `SequenceMatcher` ya validado para
  filas de grilla — encontró de paso que una constante existente en el archivo (`DASH_CHARS`)
  nunca cubría el guion ASCII común, solo variantes Unicode.

## 2026-09-05 — Investigación (sin fix): párrafo truncado a mitad de palabra, manual 6

Retomando un hallazgo de una sesión anterior logueado como "necesita su propia investigación",
se confirmó con los spans crudos del PDF fuente real (leídos directo con `fitz`) que el defecto
está en el PDF MISMO (2 spans genuinamente separados, con texto duplicado real en el origen),
no en el parser. Escaneando las 8 ediciones completas se encontró que el patrón real (~5 casos
por edición) está confinado a las 3 ediciones más viejas y desaparece por completo desde
`20241021` en adelante — el proceso de generación de PDF de Visa cambió en algún momento.
Como estos change_types nunca pasan por IA en este manual, el efecto es puramente cosmético
(fragmentos extra en un apéndice del reporte) y confinado a 3 pares ya históricos. El usuario,
con esta evidencia, decidió dejarlo como está.

## 2026-09-05 — Auditoría: consolidación de la capa de reportes del router (decisión: no tocar)

Único punto de Tier 3 del inventario original del router que quedaba sin auditar. Medido antes
de proponer nada: Módulo 8 (adaptadores) ya estaba consolidado desde que se construyó — el "sin
auditar" era en sí mismo un malentendido. Módulo 7 (`report.py`, 8 manuales) sí tiene ~60-70
líneas byte-idénticas de ~2300 totales (~3%), pero sin ningún bug escondido detrás (a
diferencia de la ronda del item 21, donde la duplicación SÍ escondía un bug real) — el resto es
genuinamente bespoke por manual. Presentada la evidencia, el usuario decidió dejarlo como está:
el churn de tocar 8 archivos por un ahorro chico no se justifica sin un bug de por medio.

## 2026-09-05 — `poc/README.md`: documentación de la aplicación completa

A pedido del usuario, se escribió el primer README del proyecto — no un fix ni una feature,
documentación de cómo funciona el sistema completo para quien lo vaya a operar. Cubre
arquitectura, los 8 manuales, requisitos, 9 escenarios de uso reales, el `--help` completo de
`run.py`/`land.py`/`build.py` con ejemplos, un paso a paso operacional del día a día, un mapa
de carpetas, y una sección de puntos importantes a tener en cuenta. Todo el contenido se
verificó contra el `--help`/código real de cada script antes de escribirse, no por memoria.

## Estado al cierre de esta sesión extendida (2026-09-05/06)

Los 8 pipelines completos, el router (landing por pares + multi-par + edición única), el
Módulo 8 con su pestaña de cambios recientes, y TODOS los residuos cosméticos que quedaban
abiertos por manual (3b/7/8/10) están cerrados y verificados de punta a punta. Único item que
sigue genuinamente abierto en todo el proyecto: item 9 (etiquetas "Note:" faltantes en 1
edición del manual 3), anotado explícitamente por el usuario como mejora futura porque necesita
infraestructura nueva (OCR), no un fix de código acotado como todo lo demás en esta lista.
Decisiones tomadas, no pendientes: un 9° manual técnico de BASE I que existe y sería viable
(el usuario confirmó que no hace falta agregarlo al alcance actual); Módulo 6 (Validación con
Plataforma STD) sigue fuera de alcance en los 8 manuales, sin cambios desde el diseño original.

**No queda ningún trabajo pendiente activo.** Ver `TODO.md` (índice accionable, actualizado en
esta misma sesión) y `poc/README.md` (manual operativo) para retomar el proyecto en el futuro.

## 2026-09-09 — Módulo 8: estado de publicación separado por manual

Repasando los escenarios de uso del README con el usuario, surgió que quería simular una
edición nueva de un manual "como si nunca hubiera existido" para probar el flujo de punta a
punta. Al explicar cómo resetear la pestaña "Cambios recientes" para ese único manual, salió a
la luz que `estado_publicacion.json` era un único archivo compartido por los 8 manuales —
borrarlo para probar 1 manual marcaba los 8 como "nuevos" de golpe (`prev is None` para
cualquier slug si el archivo entero falta). El usuario preguntó qué tan difícil sería separarlo
por manual; se evaluó como cambio chico y contenido (grep confirmó que nada más en el repo
depende de la ruta/forma del archivo) y se implementó a pedido.

`build.py` ahora persiste `data/estado_publicacion/<slug>.json` (un archivo por manual) en vez
de `data/estado_publicacion.json` (un solo diccionario con los 8 adentro). `_load_previous_state()`
lee la carpeta nueva si existe; si no, cae al archivo viejo como fallback (compatibilidad hacia
atrás, para no forzar a los 8 manuales a aparecer como "nuevos" en la primera corrida post-cambio).
`_write_state()` escribe los 8 archivos nuevos y borra el archivo viejo si todavía existe (la
migración es automática, ocurre sola la primera vez que se corre `build.py` con esta versión).

Verificado en el corpus real: 1) corrida con el `estado_publicacion.json` viejo todavía presente
→ migró sola, 0/8 nuevos (nada había cambiado de verdad) y el archivo viejo se borró; 2) corrida
idéntica siguiente → 0/8 nuevos (idempotente); 3) borrado manual de un solo archivo
(`base_ii_transactions_quick_reference.json`) → exactamente ese 1/8 salió marcado `[NUEVO]` en
la corrida siguiente, los otros 7 sin tocar. `poc/README.md` sección 7 actualizado con la ruta
nueva y el caso de uso (borrar el archivo de un manual para forzar la prueba end-to-end de ese
manual sin afectar a los demás).

## 2026-09-10 — Prueba Qwen vs Gemini (OpenRouter) en la etapa 05

El usuario quería validar si Gemini podía reemplazar a Qwen en la etapa 05, probarlo con datos
reales, y poder volver a Qwen sin fricción. Continuación directa de la idea anotada el 2026-09-09
(item 23 de `TODO.md`).

**Diseño elegido**: en vez de bifurcar `classify.py` por manual, se agregó un toggle
`LLM_BACKEND` (env var, default `"ollama"`) directamente en `poc/_shared/ollama_client.py`, el
único punto de integración real (los 7 `classify.py` con IA importan `ensure_ollama_running` y
`ollama_classify` por nombre desde ahí). Con el default, cero cambio de comportamiento. Con
`LLM_BACKEND=openrouter` + `OPENROUTER_API_KEY`, ambas funciones despachan a
`google/gemini-2.5-flash-lite` vía OpenRouter (chat completions, `temperature:0`,
`response_format: json_object`) en vez de a Ollama. Ningún `classify.py` se tocó.

**Primer intento falló** en el ítem 16/193 (`JSONDecodeError: Unterminated string`) — un JSON
cortado a mitad de string en una ficha con texto largo (2354 caracteres en el `new`). Como
`classify.py` solo escribe el JSON de salida al final del loop completo (no incrementalmente), la
corrida fallida no dejó nada a medio escribir — confirmado con `md5sum` contra la copia de
respaldo del JSON de Qwen, que seguía intacta. Reproducir el mismo prompt a mano funcionó limpio a
la primera, así que se trató como un corte transitorio de red, no un techo de longitud
determinístico. Se agregó `max_tokens: 600` explícito y reintentos con backoff exponencial (hasta
3 intentos) a `_openrouter_classify()` únicamente — Ollama local no necesita esto, nunca tuvo
fallas de este tipo. Segunda corrida completa limpia, 0 errores.

**Corrida de comparación real**: par `20251018_to_20260418` de
`base_ii_clearing_interchange_formats_tc_01_to_tc_49` (193 cambios de contenido pendientes), los
mismos ítems, mismo prompt, clasificados por ambos backends por separado. Resultado: **84.5% de
acuerdo (163/193)**. La matriz de confusión mostró la asimetría más relevante para el proyecto: 18
ítems que Qwen clasificó `business_rule_change` Gemini los bajó a `editorial_reword` (la dirección
de error costosa — cambios de negocio reales que quedarían sin flag), contra solo 7 en la
dirección contraria. `safety_net_override` (la red de seguridad determinística que fuerza
`business_rule_change` cuando desaparece contenido real sin reemplazo) se activó más veces con
Gemini (43) que con Qwen (38).

**Caso concreto verificado** (no solo inferido de la matriz): ficha `TC 05 - TCR 0`, posición
`133-136` (Merchant Category Code), campo `note`. Texto viejo real ("See the Visa Core Rules...")
desaparece sin reemplazo en la edición nueva. Gemini lo clasificó primero como `extraction_noise`,
razonando que el texto nuevo vacío sugería que el viejo "fue un artefacto de extracción de PDF" —
un error real de Gemini. La red de seguridad lo corrigió a `business_rule_change`
(`ai_original_category` en el JSON crudo confirma el valor original de Gemini antes del override).
Qwen clasificó el mismo ítem correctamente de entrada, sin necesitar el override
(`safety_net_override: false`). Es la mejor evidencia concreta de por qué la asimetría 18 vs 7
importa: es exactamente el tipo de error — confundir "contenido borrado" con "ruido de
extracción" — que el proyecto existe para no dejar pasar.

**Verificación de que el proyecto quedó intacto**: antes de correr Gemini se copiaron aparte
(fuera del repo) el JSON de la etapa 05 y el `.md` de la etapa 07 de ese par (los resultados de
Qwen). Después de la comparación se restauró el JSON original y se regeneró la etapa 07 desde ahí
— `md5sum` confirmó que ambos archivos quedaron byte-idénticos a como estaban antes de tocar
nada. El toggle sigue en el código pero está inerte salvo que alguien setee
`LLM_BACKEND=openrouter` explícitamente; correr el pipeline normal hoy usa Qwen exactamente igual
que siempre.

**Entregables de la sesión** (dos Artifacts, fuera del repo, para revisión visual): una página de
comparación ítem-a-ítem con matriz de confusión, filtros y buscador; y una página con los dos
`.md` reales de la etapa 07 (Qwen vs Gemini) en pestañas, para hojearlos uno al lado del otro sin
reescribir su contenido.

**Nota de seguridad**: el usuario pegó su API key real de OpenRouter directo en el chat (en vez de
correr el comando él mismo con `!`). Se le avisó de inmediato y se le pidió revocarla/rotarla en
openrouter.ai/keys — el asistente no tiene acceso a esa cuenta para revocarla directamente.

**No fue una decisión de migración**, fue una prueba puntual. Los puntos abiertos si se evalúa una
migración real más adelante siguen siendo los mismos que ya estaban anotados: confidencialidad
(contenido propietario Visa/Mastercard saliendo a una API cloud) y costo real por token (Ollama
local es gratis).

## 2026-09-12 — Revisión manual guiada por el usuario de `tc_01_to_tc_49`, par `20251018→20260418`: 6 causas raíz nuevas encontradas y arregladas, item 9 del TODO cerrado (y su diagnóstico anterior corregido)

Primera vez que se prueba un flujo de QA distinto: en vez de que el asistente audite el pipeline,
el **usuario** revisó el reporte web línea por línea contra los 2 PDFs reales (ediciones
`18/10/2025` y `18/04/2026`) y fue pasando sus hallazgos en un archivo
`poc/base_ii_clearing_interchange_formats_tc_01_to_tc_49/data/revision_manual_2026-09-12.md`
(convención: `Caso N: <ubicación tal como aparece en el reporte> / Antes / Ahora / Razón (de la
IA) / Obs (del usuario)`), acumulando ~99 casos antes de pasarlo. El asistente lo leyó completo,
clasificó cada caso por causa raíz probable, y solo después fue a cruzar cada patrón contra los
datos crudos de Módulos 01-04 (no contra el reporte final) para confirmar antes de tocar código.
Metodología a repetir: pedir el archivo completo de una sola vez en vez de ir caso por caso (con
~99 items, iterar 1 a 1 hubiera sido carísimo en turnos) y usar los JSON intermedios de cada etapa
como evidencia, no solo el `.md`/`index.html` final.

**Bug A — `_detect_reserved_splits` (Módulo 4) solo capturaba el primer campo de un split
múltiple.** La condición `new_fields` exigía que el campo arrancara justo en el inicio del rango
`Reserved` original; los demás campos recién definidos en el MISMO split (ej. "TC 33.A - CP 09
TCR 4 - Recipient Name": `110-168 Reserved` se partió en 3 campos nuevos —`Payee Date of Birth`,
`Payee Phone Number`, `Recipient State`— más `140-168 Reserved`) quedaban mal etiquetados como
"Reserved restante" junto con el resto verdaderamente reservado. Fix: la condición de arranque en
el inicio del rango se mantiene solo como DISPARADOR (confirma que es un split real, patrón Visa
ya documentado), pero una vez confirmado, TODOS los `contained` que no sean literalmente
`Reserved` pasan a ser `new_fields`.

**Bug B — nuevo mecanismo `_detect_reserved_merges` (Módulo 4), inverso al split, para el caso
con el rango CORRIDO.** Cuando un campo definido se retira a `Reserved` pero el límite no es el
mismo rango exacto (porque un campo vecino también cambió de posición en la misma edición —ej.
"Mastercard - Service Location Postal Code" `64-73` se retira justo cuando el campo vecino
"Mastercard Transaction Link Identifier/..." se corre de `74-109` a `73-108`, dejando el
`Reserved` nuevo en `64-72`, 1 byte más chico—), Módulo 3 ya lo tenía bien separado en
`rows_removed`/`rows_added`, pero Módulo 4 no tenía forma de conectarlos (el mecanismo existente,
`_reserved_transition`, exige el MISMO rango ya emparejado por posición). Se agregó
`_detect_reserved_merges`: busca superposición de rango entre un `removed` no-Reserved y
`added` Reserved, y lo reporta como `field_became_reserved` con `subtype: "shifted"` (nuevo, junto
al ya existente `"renamed_in_place"`). Al arreglarlo se destaparon **2 casos más** en ediciones
históricas previas que nunca se habían visto (2023-04→2023-10, 2024-04→2024-10).

**Bug C — Módulo 2 (`normalize.py`): el `Note:`/`Values:`/`Mapping:` de un campo cuyo NOMBRE
envuelve en 3+ líneas se atribuía al campo ANTERIOR.** Caso confirmado con datos crudos:
"Mail/Phone/Electronic Commerce and Payment Indicator" (nombre de 3 líneas) corre su
`Positions:` varios puntos hacia abajo, pero su `Note:` (columna derecha) mantiene su posición Y
fija; al reordenar todo por `(y0, x0)` (Módulo 2 no respeta el orden de extracción real de Módulo
1), ese `Note:` terminaba ANTES que el `Positions:` que confirma la ficha correcta, y se pegaba a
la ficha anterior (`Terminal ID`, todavía "activa" en el parser). La condición existente
(`same_row_as_next_name`, tolerancia de banda Y de 3.0pt) solo cubría el caso de `Description:`
compartiendo fila con el nombre; se generalizó a un `next_name_pending` sin tolerancia de Y
(alcanza con que haya un `active_paragraph` pendiente en la misma página) para Note/Values/Mapping
también. Efecto real verificado: `Terminal ID` (32-39) queda sin nota (correcto, nunca la tuvo),
y "Mail/Phone/..." (40) y "Unattended Acceptance Terminal Indicator" (41) recuperan sus propias
notas completas.

**Bug D — Módulo 2 (`normalize.py`): "Format: ... character" (wrap de 2 líneas) se pegaba como
prefijo del NOMBRE del próximo campo.** Hallazgo colateral al arreglar el Bug F de abajo (dejar de
esconder cambios de `name`/`length`/`format` detrás de un gate combinado reveló esto). El valor
real de `Format` en varias fichas es "alphanumeric special **character**" (3 palabras), partido en
2 líneas por ancho de columna; Módulo 2 solo capturaba la 1ra línea de `Format:` (sin mecanismo de
continuación, a diferencia de `Note`/`Description`), así que la palabra suelta "character" caía en
el catch-all genérico de párrafo/nombre-de-próximo-campo, dando `"character Sender Name"` en vez
de `"Sender Name"` (y `format` truncado a `"alphanumeric special"`, sin "character"). Afectaba
**90-96 campos por edición** (todos con este format value). Fix: se agregó `active_card_left_label`
+ `active_card_left_block` (mismo mecanismo que ya existía para columna derecha, pero para
izquierda) usando `source_block` de Módulo 1 —no un umbral de hueco en Y, que ya se sabía frágil
por el Bug C— para distinguir "es wrap de Format" (mismo `source_block` que la línea `Format:`) de
"es el nombre del próximo campo" (`source_block` nuevo). Verificado: 0 nombres con prefijo
`"character "` restantes en las 9 ediciones tras el fix, formato ahora completo
(`"alphanumeric special character"`).

**Bug E — item 9 del TODO ("~57 `Note:` faltantes en `20260418`"), CERRADO — su diagnóstico
anterior (2026-08-13/2026-09-05) estaba incompleto.** El item decía "no es arreglable sin OCR" y
"la red de seguridad de Módulo 5 ya compensa el efecto práctico". Lo segundo resultó ser
literalmente lo que el usuario tuvo que encontrar a mano: la red de seguridad SÍ marcaba estos
casos para revisión, pero como `business_rule_change` con una razón engañosa ("el texto nuevo está
vacío, artefacto de extracción") en vez de descartarlos — no "compensaba", generaba ~59 falsos
positivos que alguien tenía que revisar uno por uno para darse cuenta de que no eran nada. El fix
real no necesitaba OCR: en `_diff_card_fields` (Módulo 4), cuando Visa saca el rótulo `Note:` entre
ediciones sin cambiar el contenido, el texto se corre a `description` pero el CONTENIDO total del
campo (concatenando `description+note+values+mapping`) es casi idéntico entre ediciones. El primer
intento (2026-09-12, sesión misma) solo comparaba el combinado como GATE antes de diffear cada
columna por separado —insuficiente cuando además del corrimiento hay una edición real mínima en el
texto migrado (ej. se le sacó la palabra "Please" a "Please see BASE II Clearing Data Codes...",
ratio combinado 0.9758 < 0.98, dispara el diff de todos modos)—: seguía mostrando `note`
"vaciándose" y `description` "creciendo", el mismo relato falso con una excusa real para no
filtrarlo del todo. Fix definitivo: si el combinado difiere de verdad, se reporta **un solo**
`card_content_changed` con `field: "contenido"` y el combinado completo de cada lado, en vez de
atribuirlo a una columna específica -se pierde la etiqueta fina pero se gana no mentir sobre qué
columna "perdió"/"ganó" contenido. `name`/`length`/`format` (`CARD_STRUCTURAL_FIELDS`) se sacaron
del combinado y se siguen diffeando por separado siempre (esto es lo que reveló el Bug D).

**Bug F — viñetas extraídas como letra suelta `"l"` (a veces DESPUÉS del ítem, no antes) en la
edición vieja vs `"●"` en la nueva, mismo contenido, glifo/orden distinto.** Emparentado con el
**item 5 de este TODO** (ya resuelto 2026-08-25, pero en `base_ii_clearing_data_codes` —manual
1—, `_find_disappeared_content` de SU `classify.py`; nunca portado al `classify.py` propio de
`tc_01_to_tc_49` —mismo patrón de fix-no-portado ya documentado en el item 21 para "5 de 7
manuales"—). Acá se resolvió distinto: en vez de portar el filtro de la red de seguridad de Módulo
5, se neutralizó el glifo de viñeta (`BULLET_TOKEN_PATTERN`, token aislado `l`/`●`) para el CÁLCULO
DE SIMILITUD en Módulo 4 (`_similarity_text`, aplicado tanto en `_diff_fields` como en el combinado
del Bug E) —más robusto porque ataja el problema antes de que el cambio llegue siquiera a Módulo
5, en vez de depender de que el LLM clasifique bien o de que la red de seguridad no se equivoque.
Validado con 10 casos al azar de los 42 afectados en el par actual: los 10 eran ruido puro de
formato (confirmado palabra por palabra sin viñetas, texto 100% idéntico). **Pendiente para otra
sesión**: evaluar si conviene el mismo tratamiento en Módulo 4 para los otros manuales que
comparten el patrón del item 21 (no se tocó nada fuera de `tc_01_to_tc_49` esta sesión).

**Resultado**: "Cambios de negocio a revisar" del par `20251018→20260418` bajó de **91 a 27**
(pasando por 40 y 38 en pasadas intermedias de la misma sesión), sin perder ninguno de los
cambios genuinos que el usuario confirmó como reales durante la revisión manual (spot-checks
puntuales: rangos de posición Colombia, VDCAP→DCAP, renombres "Acquirer Reference Number—X",
"Message Text", "Transaction Component Sequence Number" — todos siguen presentes y bien
clasificados tras cada fix). Se re-corrieron Módulos 02→03→04→05→07 completos para los 8 pares
históricos del manual (no solo el par actual) porque los bugs C y D son de Módulo 2, afectan a
TODAS las ediciones por igual, no solo a la más nueva. Archivos tocados: `02_normalizacion_bloques/
normalize.py`, `04_deteccion_cambios/detect.py`, `07_reporte_cambios/report.py`,
`08_reporte_web_consolidado/adapters/interchange_formats_grid.py`. Commit `d7eb95f`. El archivo
`revision_manual_2026-09-12.md` queda en el repo como registro de la revisión (incluye 1 caso
ambiguo -Caso 32- donde el usuario pegó mal la Obs de otro caso, corregido en el chat, y 1 caso
-Caso 70- que en un principio parecía no encontrarse en el manual pero terminó siendo parte del
Bug C, ya resuelto).

**Próximo paso (indicado por el usuario)**: seguir con la misma revisión manual, próxima sesión,
para otro de los 7 manuales del proyecto (todavía sin elegir cuál).

## 2026-09-13 — Revisión manual de dos manuales más: `tc_50_to_tc_92` (limpio) y `base_ii_clearing_data_codes` (30 falsos positivos, investigado, fix pendiente)

Continuación de la dinámica de revisión manual iniciada 2026-09-12 (ver sección de arriba), esta
vez con dos manuales en la misma sesión.

**`tc_50_to_tc_92` (par vigente)**: el usuario pasó `revision_manual_2026-09-13.md` con 5 casos
(campo `4` - Transaction Component Sequence Number, `unpacked numeric` → `alphanumeric`, en varias
fichas TCR de TC 50) y los confirmó los 5 como correctos ("Ok"). Sin hallazgos, sin fixes. Ver
item 26 del TODO.

**`base_ii_clearing_data_codes` (par `20251018→20260418`)**: el usuario listó 48 casos de
`revision_manual_2026-09-13.md`. 18 confirmados correctos ("Ok", cambios de negocio reales:
Bulgaria/Croacia pasando a Euro, definiciones actualizadas de BASE II SYSTEM/CPD/ISSUING
IDENTIFIER/etc., nuevos Product ID). 1 caso (`SOURCE IDENTIFIER`, Caso 15) quedó con `Obs:` en
blanco, pendiente de que el usuario aclare. Los ~30 restantes (casi todos en
`Retired Chargeback Reason Codes` / *Chargeback Reason Rules*, más `Return/Reclassification Reason
Codes` códigos `01`/`HZ`, `Request for Copy Reason Codes` 33/34, y sueltos en `Usage` de POS
Environment Codes / Payment Mode Codes) el usuario los marcó como falsos positivos: el reporte los
muestra como `business_rule_change` con una `Razón (IA)` que inventa un cambio de negocio (montos,
orden de reglas por región), pero Antes/Ahora tienen el mismo contenido palabra por palabra -solo
difiere el glifo de viñeta (`"l"` edición vieja vs `"●"` edición nueva) y, más grave, el ORDEN en
que las líneas quedaron extraídas.

**Investigación de causa raíz (esta sesión, sin fix aplicado aún)**: se confirmó contra
`data/07_reporte_cambios/20251018_to_20260418.md` que:
- 5 de estos casos (`61`, `82`, `93`, `01`, `HZ`) tienen `safety_net_override=True` (⚠️ en el
  reporte) -el LLM (`qwen3:4b`) los había clasificado bien (`editorial_reword`/`extraction_noise`)
  pero la red de seguridad de Módulo 5 (`_find_disappeared_content`, item 5 del TODO, RESUELTO
  2026-08-25 -pero solo filtra el glifo de viñeta para la EVIDENCIA de "contenido desaparecido",
  no para el umbral de similitud de Módulo 4) los pisó igual, porque el reordenamiento de bloques
  sigue generando tramos de 5+ palabras "desaparecidas" aunque el glifo puro ya se descarte.
- Los ~25 restantes fueron clasificados `business_rule_change` directamente por el LLM, sin pasar
  por la red de seguridad -el reordenamiento por sí solo ya confunde al modelo chico y le hace
  alucinar una razón de negocio plausible mirando texto revuelto.
- A diferencia de `tc_01_to_tc_49` (Bug F, item 21/25: `_similarity_text` con
  `BULLET_TOKEN_PATTERN` neutraliza el glifo de viñeta ANTES de calcular
  `SequenceMatcher.ratio()` en Módulo 4), el `detect.py` de `base_ii_clearing_data_codes`
  (`_diff_row_cells`) no neutraliza nada -calcula el ratio sobre el texto crudo, viñeta incluida.
  Pero a diferencia de `tc_01_to_tc_49` (donde el reordenamiento validado en 10/42 casos era menor
  y neutralizar el glifo alcanzaba para subir el ratio sobre el umbral), acá el reordenamiento
  parece ser a nivel de BLOQUE completo (la edición vieja agrupa todas las etiquetas de región
  primero y todo el texto de viñetas después, en vez de interlearlos -aparenta extracción
  column-major de una tabla de 2 columnas glifo/etiqueta + texto envuelto, en vez de row-major).
  Sospecha (no confirmada con el JSON crudo de Módulo 1 todavía) es que el bug real está en el
  orden de lectura de Módulo 1/2 para este layout -mismo patrón "Tipo B" (2-3 columnas, texto
  envuelto + viñetas) ya mapeado en la sección "Mapeo del mismo patrón... en el resto de familias
  de manuales" de este archivo, donde ya se documentó que en `base_ii_clearing_data_codes`
  "`pymupdf4llm` perdió una fila completa" en este mismo tipo de tabla.
- Plan de 4 pasos propuesto al usuario (investigar Módulo 1 crudo → fix de orden de lectura si se
  confirma ahí → portar `_similarity_text`/`BULLET_TOKEN_PATTERN` a Módulo 4 como red adicional →
  re-correr Módulos 02→07 para los 8 pares históricos), **pendiente de luz verde del usuario antes
  de tocar código** -a diferencia de las sesiones anteriores, esta vez el usuario pidió
  explícitamente ver el plan de solución primero. Detalle completo del plan en item 27 del TODO.

**Caso 15 confirmado "Ok" por el usuario** en la misma sesión (sin acción de código) y **plan de
item 27 aprobado** -continúa abajo con la implementación real, hecha en la misma sesión.

## 2026-09-13 (continuación) — Bug G resuelto: `active_last_y1` obsoleto durante diferimiento en Módulo 2 de `base_ii_clearing_data_codes`

Root-cause real del item 27 del TODO, encontrado con instrumentación directa de
`build_blocks()` (prints temporales sobre copias del módulo, no tocaron el archivo real hasta
tener el diagnóstico confirmado) contra los JSON crudos de Módulo 1 de 2 ediciones.

**Primer hallazgo, descartando la hipótesis inicial**: el campo `order` de Módulo 1
(`01_ingesta_parseo/*.json`) para el código 82 de "Retired Chargeback Reason Codes" (edición
`20251018`) está PERFECTAMENTE ordenado -label, viñeta, contenido, label, viñeta, contenido...-
tanto en la edición vieja como en la nueva. El bug NO está en Módulo 1 (descarta la sospecha
inicial del item 27). Confirmado con `_new_cells`/`group_into_rows` de Módulo 2 en aislamiento:
también agrupan bien. El desorden aparece recién en `build_blocks()`.

**Mecanismo exacto** (validado con prints de `gap_to_active`/`gap_to_next` reales): la rama que
maneja filas multi-línea sin código activo (`elif active_kind in ("table_row", "table_header")`,
pensada originalmente para "2+ columnas que envuelven a la vez en la misma banda Y", ej. "Cayman
Islands" repetido en país+moneda) compara `gap_to_active = row_y0 - active_last_y1` contra
`TABLE_ROW_GAP_MAX = 4.0` -constante calibrada específicamente para la tabla "Country and Currency
Codes" (ver su propio comentario en el código: "líneas de una misma celda envuelta ~0pt, filas
distintas ~8.5pt"). El gap real entre una etiqueta de región (ej. "International:") y su primera
viñeta en "Chargeback Reason Rules" es de 6-9pt -por encima del umbral calibrado para OTRA tabla-,
así que la fila se difiere a `pending_prefix` para decidir si pertenece a la fila activa o a la
siguiente. El bug: `active_last_y1` NUNCA se actualiza mientras se sigue difiriendo (el código hace
`continue` antes de llegar a la línea que lo actualiza), así que la SIGUIENTE comparación de hueco
usa el mismo `active_last_y1` viejo -que ya no representa el hueco real, corrido hacia adelante
junto con todo lo diferido-. Con `gap_to_active` fijo en ~6pt y `gap_to_next` fluctuando en ese
mismo rango por el layout natural del documento, la condición `gap_to_next < gap_to_active` sigue
dando verdadero casi siempre, encadenando TODAS las filas restantes de la celda (10-19 líneas) en
un solo `pending_prefix` gigante. Cuando finalmente se resuelve (una comparación da falso por
casualidad, o llega una fila con celda-código que fuerza `flush()`), el lote completo se anexa de
una sola vez, ordenado por `sorted(row, key=lambda l: l["bbox"][0])` -**X0 puro**- que agrupa TODAS
las líneas de la columna angosta (etiquetas + viñetas, X0≈259) antes que TODAS las de la columna
ancha (texto envuelto, X0≈271), sin importar a qué renglón visual pertenecía cada una. Exactamente
el síntoma reportado por el usuario.

**Edición nueva, variante más chica del mismo bug**: en vez de viñeta+contenido como 2 líneas
separadas (`"l"` suelto + texto), la viñeta viene pegada al inicio del texto en la MISMA línea
PyMuPDF (`"●For T&E transactions..."`). El gap entre esta línea y su continuación envuelta
(`"than $25.00 USD."`, en otra línea por ancho de columna) suele ser ~0pt (sin problema), pero el
gap ENTRE bullets consecutivos (~6-9pt) sigue disparando el mismo mecanismo de diferimiento
encadenado, solo que con lotes más chicos (2-3 líneas en vez de 15+) -confirmado con el código 41
del par `20251018→20260418`: "than $25.00 USD." terminaba desplazado al final de la celda en vez
de justo después de su línea `"●For T&E..."`.

**3 intentos de fix antes del correcto** (documentados porque cada uno introdujo o reveló una
regresión real, no solo por prolijidad):
1. *Ordenar SIEMPRE por (Y0, X0) en vez de X0 puro*: arregla Chargeback Reason Rules
   perfectamente, pero ROMPE la tabla "Country and Currency Codes" -Bulgaria/Burkina Faso y
   varios otros países consecutivos de una sola línea terminan fusionados en una sola fila
   combinada (confirmado: 24→18 bloques en la página de Bulgaria, mismo patrón en Croacia/Cook
   Islands/Costa Rica). Causa: esa tabla tiene su propia lógica de "fila secundaria sin columna
   ancla" (punto 6 del docstring) que depende de que el orden por X0 mantenga la semántica de
   columnas dentro de una fila genuinamente simultánea; (Y0, X0) la rompe cuando hay jitter de
   línea base entre columnas.
2. *Solo actualizar `active_last_y1` al diferir (sin tocar el sort), sin acotar a ninguna tabla*:
   arregla Bulgaria/Croacia del par actual Y dejaba practicamente intacto Chargeback Reason Rules
   (mejora enorme, de 49 a 28 business_rule_change), PERO regresiona la edición `20220423`: varios
   nombres de país envueltos en 2+ líneas adyacentes (ej. "European Economic and Monetary Union" /
   "European Monetary Cooperation Fund") se mezclan entre sí -el mismo mecanismo de "hueco stale"
   que causaba el bug en Chargeback Reason Rules es, en esta OTRA tabla, la señal legítima que
   distingue una fila nueva de un nombre envuelto (por diseño, ver punto 5 del docstring); "arreglarlo"
   ahí rompe la distinción real. added/removed de Módulo 3 para el par `20220423→20221015` empeoró
   de 36/26 (baseline original) a 52/38.
3. *Fix #2 + sort (Y0,X0) condicionado a `was_deferred` (si esta fila incluye contenido de
   `pending_prefix`)*: sigue rompiendo el mismo caso de país -el problema no es CUÁNDO se ordena
   por (Y0,X0), sino que el mecanismo de diferimiento en sí sigue fusionando países que deberían
   quedar en filas separadas, independientemente del sort key usado para ordenar lo ya fusionado.

**Fix final, acotado por contenido (no por si hubo diferimiento)**: se agregó
`_row_has_bullet_glyph()`, que reconoce una viñeta suelta (`"l"`/`"●"`/`"•"` como línea completa,
estilo edición vieja) O una línea que EMPIEZA con `"●"`/`"•"` (estilo edición nueva, viñeta pegada
al texto) -deliberadamente sin incluir `"l"` como prefijo, porque es una letra normal del inglés
("local", "less", etc) y un prefijo-match ahí daría falsos positivos masivos. Tanto el fix de
`active_last_y1` (en la rama multi-línea Y en la rama de línea suelta envuelta) como el cambio de
sort key (Y0,X0 en vez de X0 puro) quedan condicionados a `_row_has_bullet_glyph()` sobre la fila
en cuestión. Como "Country and Currency Codes" nunca tiene viñetas en sus celdas, queda con el
código ORIGINAL sin ninguna modificación de comportamiento -validado con diff exacto: las 2051
filas de la edición `20220423` (antes y después del fix) son byte-idénticas, 0 diferencias.

**Validación final** (4 escenarios de prueba, cada uno aislado con datos crudos reales antes de
tocar el pipeline completo): código 82/41 de Chargeback Reason Rules (ambas ediciones), código 1
de Acceptance Terminal Indicator, Bulgaria/Croacia del par actual, y Angola/Anguilla + nombres
largos de la UE de la edición `20220423` -los 4 quedan con orden de lectura correcto y sin ninguna
fusión/pérdida de fila. Se re-corrieron Módulos 02→03→04→05→07 completos para los 8 pares
históricos (no solo el par actual, mismo criterio que items 21/25 -los bugs de Módulo 2 afectan a
todas las ediciones por igual). Se agregó también a `04_deteccion_cambios/detect.py`
`BULLET_TOKEN_PATTERN`/`_similarity_text` (mismo mecanismo ya validado en `tc_01_to_tc_49`, item
21/25 Bug F) como red adicional para neutralizar el glifo de viñeta puro en el cálculo de
similitud de Módulo 4, independientemente del fix de Módulo 2.

**Resultado**: "Cambios de negocio a revisar" del par `20251018→20260418` bajó de **49 a 20**
-exactamente los 18 casos que el usuario ya había confirmado como reales en su revisión manual
("Ok": Bulgaria/Croacia pasando a Euro, definiciones de Glossary, nuevos Product ID) más los
códigos `33`/`34` de "Request for Copy Reason Codes", que quedan pendientes de revisión de negocio
genuina (texto realmente vacío -`"l\nl"`, sin contenido real- en la edición vieja que pasa a tener
texto real en la nueva; no es ruido de extracción, no se tocó). Los otros 7 pares históricos
también mejoraron o se mantuvieron igual, sin ningún caso peor: varias filas de país que antes se
fusionaban mal (ej. Croacia/Sierra Leona en el par `20220423→20221015`) ahora matchean 1:1 y
revelan cambios reales de negocio que antes quedaban ocultos por el mal emparejamiento
(business_rule_change subió de 3→6 y de 16→18 en 2 pares, siempre por altas genuinas -verificado
leyendo el contenido de cada caso nuevo, no son falsos positivos). Se regeneró también el reporte
web consolidado (`poc/08_reporte_web_consolidado/build.py`). Archivos tocados:
`02_normalizacion_bloques/normalize.py` (fix de raíz), `04_deteccion_cambios/detect.py` (red
adicional). Pendiente de que el usuario valide y confirme el commit (`revision_manual_2026-09-13.md`
de ambos manuales queda en el repo como registro).

**Próximo paso**: esperar validación del usuario antes de confirmar el commit; después, seguir con
la misma revisión manual para los 5 manuales restantes en sesiones futuras.

## 2026-09-13 (continuación 2) — Bug H: `_new_cells` pierde el texto real de un código cuando su primera línea ya trae viñeta+contenido

Después de cerrar el Bug G (arriba), el usuario mandó 3 casos más contra el reporte ya
regenerado, sospechando que seguían siendo el mismo problema de viñetas (item 27/28 del TODO).

**Código `0150`** ("Fee Collection/Funds Disbursement Reason Codes"): se verificó contra el JSON
crudo de Módulo 1 de ambas ediciones y el texto coincide EXACTO con el reporte en las dos -es un
cambio de negocio real: "ATM Balance Inquiry acquiring direct **fee** returns... **AP region**
only" (vieja) → "**Domestic** ATM Balance Inquiry acquiring direct **access fee** returns...
**Mexico**" (nueva). El usuario tenía razón en notar un residuo de formato (queda un "l" suelto al
final de la celda vieja, el mismo patrón cosmético ya conocido de viñeta-al-final-de-lote-diferido,
sin efecto en el contenido), pero la clasificación `business_rule_change` es correcta -no se tocó
nada.

**Códigos `33`/`34`** ("Request for Copy Reason Codes"): acá SÍ había un bug real, distinto del
Bug G. El JSON crudo de Módulo 1 de la edición VIEJA (`20251018`) tiene el texto completo -"Legal
process or fraud analysis request—U.S. Domestic only" para el código `33`, etc.- en la banda Y
`p73, y0=116-148` (page 73). El reporte mostraba `"l\nl"` como si estuviera vacío. Se rastreó hasta
`data/02_normalizacion_bloques/20251018.json`: el `table_row` de código `33` tenía **3 celdas**
(`['33', 'l\nl', 'Legal process or fraud analysis request—U.S. Domestic only\nFraud analysis
request—Non-U.S. Domestic']`) en vez de las 2 que declara el `table_header` de esa tabla
(`['Requests', 'Reason']`). La edición nueva, en cambio, produce las 2 celdas correctas
(`['33', '●Legal process...\n●Fraud analysis...']`) porque ahí la viñeta viene pegada al texto en
la MISMA línea PyMuPDF (sin banda X separada).

**Causa raíz**: `_new_cells()` (la función que arranca un `table_row` nuevo, vía `has_code_cell`)
agrupa las líneas de la fila ancla en celdas usando `CELL_X_MERGE_TOLERANCE=3.0pt` de hueco en X0.
Para la mayoría de las tablas del manual esto alcanza, porque la 1ra línea de un código nuevo trae
solo texto normal -las viñetas de listas largas aparecen recién en filas SIGUIENTES, que se anexan
después vía `_nearest_cell` sobre celdas ya anchas y establecidas. Pero cuando la lista de un
código es tan CORTA que su primer ítem (viñeta + texto) comparte la MISMA banda Y que el número de
código -exactamente el caso de `33`/`34`, con solo 1-2 líneas de "Reason"-, `_new_cells` ve
`['33'(x0=111.2), 'l'(x0=164.2), 'Legal process...'(x0=176.2)]` como 3 grupos de X0 (huecos de 53pt
y 12pt, ambos > tolerancia) en vez de reconocer que la viñeta y su texto envuelto son la MISMA
columna "Reason". La celda de más queda fuera del rango que Módulo 3/4 compara (emparejamiento por
índice contra el header de 2 columnas), así que la celda 1 (`"l\nl"`, la viñeta sola) es la que se
compara como "Reason" -el texto real, en la celda 2, se pierde en silencio.

**Fix**: en `_new_cells`, si la línea que se está por agregar viene INMEDIATAMENTE después de una
línea de viñeta ya agregada a la celda activa (mismo helper `_row_has_bullet_glyph` del Bug G), se
fusiona a esa celda SIN IMPORTAR el hueco en X0 -una viñeta y su texto nunca son 2 columnas reales.
Acotado igual que el Bug G (solo dispara después de una línea de viñeta), no afecta ninguna tabla
sin viñetas.

**Validado**: códigos `33`/`34` ahora producen 2 celdas correctas
(`['33', 'l\nLegal process or fraud analysis request—U.S. Domestic only\nFraud analysis
request—Non-U.S. Domestic\nl']`), el texto real vuelve a compararse y cae a "sin cambio real" (mismo
contenido, solo viñeta). Re-validados los 4 escenarios de prueba del Bug G sin regresión -diff
exacto de las 2051 filas de `20220423`, 0 diferencias. Re-corridos Módulos 02→03→04→05→07 para los
8 pares históricos.

**Resultado final**: "Cambios de negocio a revisar" del par `20251018→20260418` bajó de 49 a
**18** -exactamente los 18 casos que el usuario había confirmado como reales en su revisión manual
original (`revision_manual_2026-09-13.md`), sin ninguno de más. Se regeneró el reporte web
consolidado. Archivo tocado: `02_normalizacion_bloques/normalize.py` (`_new_cells`).

**Próximo paso**: esperar validación final del usuario antes de confirmar el commit.

## 2026-09-13 (continuación 3) — Revisión manual limpia: `base_ii_clearing_edit_package_messages` y `base_ii_transactions_quick_reference`

El usuario revisó los `revision_manual_2026-09-13.md` de estos 2 manuales y confirmó todos los
casos como "Ok", sin hallazgos de pipeline. Ver item 29 del TODO para el detalle de los casos.

Con esto, los 4 manuales de la familia "BASE II" quedan con revisión manual completa:
`base_ii_clearing_data_codes` (2 bugs encontrados y arreglados, ver arriba),
`base_ii_clearing_edit_package_messages` (limpio), `base_ii_clearing_interchange_formats_tc_01_to_tc_49`
(6 bugs arreglados, sesión 2026-09-12), `base_ii_clearing_interchange_formats_tc_50_to_tc_92`
(limpio). Quedan pendientes los 3 manuales no-BASE-II del proyecto:
`international_full_service_pos_online_messages_processing_specifications`,
`visanet_settlement_service_vss_user_guide_volume_1_specifications`,
`visanet_settlement_service_vss_user_guide_volume_2_reports`.

**Próximo paso**: seguir con la misma revisión manual para estos 3 manuales restantes, todavía sin
elegir cuál va primero.

## 2026-09-13 (continuación 4) — Bug I: reflow de párrafo con cambio real de contenido en `international_full_service_pos_online_messages_processing_specifications`

Primer manual no-BASE-II revisado. El usuario mandó 3 casos de
`revision_manual_2026-09-13.md`; 2 confirmados "Ok" sin acción (cambio de response code a
"XA" en STIP, palabra "Adjustment" agregada en Transaction Sets). El Caso 1 sí era un bug
real, pero de una clase totalmente distinta a los de `base_ii_clearing_data_codes` -acá no hay
extracción de tablas, el manual se diffea a nivel de PÁRRAFO/SECCIÓN (decisión del usuario,
2026-08-19, ver docstring de `normalize.py`).

**El caso**: sección "Full Service Processing Summary > Full Service Participation
Requirements > Issuer Options". El reporte mostraba el párrafo de "Country-to-Country
Transactions" con `business_rule_change` y una Razón (IA) que decía que la nueva edición
"añade información adicional sobre los parámetros" -pero comparando contra el PDF real (aporte
del usuario, transcripción palabra por palabra de ambas ediciones) el contenido es el mismo,
solo dividido distinto entre 2 párrafos.

**Verificación con datos crudos**: en la edición vieja (`20251015`), "...actualiza solo Visa."
está al final de la página 29 (`y0=695.3`, cerca del pie) y "The following parameters are
involved..." arranca al principio de la página 30 (`y0=71.0`, cerca del techo) -hay un salto de
página real. En la nueva (`20260420`), ambas oraciones caen en la MISMA página 30
(`y0=362.3` y `y0=382.8`) -sin salto entre medio, por reflujo de contenido anterior en el
documento. Módulo 2 (`normalize.py`) usa `page == active_paragraph["page"]` como límite DURO
de párrafo (documentado, deliberado), así que separa correctamente en la vieja y fusiona
correctamente en la nueva -la extracción en sí no tiene ningún bug.

**Por qué el mecanismo de reflow existente no lo capturó**: Módulo 3 (`match.py`,
`match_paragraphs`) ya tiene, desde el 2026-08-25, un mecanismo N:M vía un solo
`SequenceMatcher` a nivel de párrafo que detecta bloques `"replace"` cuya concatenación
normalizada es IDÉNTICA en ambos lados y los reporta como `paragraphs_reflowed` (nunca cuenta
como cambio real). El docstring del módulo ya documentaba, como "limitación aceptada
conscientemente", que un bloque MIXTO (reflow + cambio real de contenido en el mismo tramo) no
se sub-divide y cae entero al pool de fuzzy per-párrafo -"no justificada sin evidencia real de
que ocurra (no se encontró ningún caso así en el corpus completo)". Este caso puntual es
EXACTAMENTE eso: el wording cambió de "The following parameters..." a "These parameters..."
(ratio de similitud de la concatenación completa: 0.989 -confirmado con
`difflib.SequenceMatcher` directo sobre el texto real). Al no ser idéntico byte a byte, el
bloque completo (2 párrafos viejo, 1 nuevo) caía al pool de fuzzy per-párrafo, que terminaba
emparejando el párrafo viejo CORTO (sin la parte de "parameters") contra el párrafo nuevo LARGO
(con la parte de "parameters" fusionada) -de ahí la falsa impresión de "contenido agregado".

**Fix**: nuevo umbral `REFLOW_CONTENT_SIMILARITY_THRESHOLD=0.95` en `match.py` (más estricto que
`FUZZY_PARAGRAPH_THRESHOLD=0.90`, calibrado para reescrituras de UN solo párrafo -acá se están
fusionando 2+ párrafos completos, así que el umbral para aceptar la fusión debe ser más alto).
Cuando un bloque `"replace"` no concatena idéntico pero sí por encima de ese umbral, en vez de
caer al pool de fuzzy per-párrafo, se agrega directo a `paragraphs_matched` como UN solo par
`match_type="fuzzy"` comparando los bloques COMPLETOS concatenados de cada lado -Módulo 4/5 lo
procesan exactamente igual que cualquier otro párrafo reescrito (`paragraph_content_changed`),
mostrando la comparación real (el cambio de wording puntual) en vez del artefacto de re-corte.
Los bloques mixtos que no llegan al umbral (cambio real y sustancial, no solo un ajuste menor de
wording) siguen sin sub-dividirse -mismo comportamiento que antes, límite aceptado
conscientemente, no perseguido más allá sin evidencia de que ocurra un caso así.

**Validado**: el caso reportado por el usuario ya no aparece en "Cambios de negocio a revisar"
del par `20251015→20260420`. Se re-corrieron Módulos 03→04→05→07 para los 6 pares históricos
completos del manual. El conteo de "cambios de negocio a revisar" del par actual pasó de 3 a 4:
desapareció el caso reportado, y aparecieron 2 casos NUEVOS que antes quedaban escondidos como
ruido de altas/bajas de párrafo (mejor cobertura de emparejamiento revela contenido real que
antes se perdía) -un typo real corregido ("filed 39"→"field 39" en "Converting Over-Limit
Codes") y un cambio real en la tabla "Purchase and Cash Disbursement" (se eliminó una
restricción de que el cashback es solo para transacciones domésticas). Pendiente de que el
usuario confirme estos 2 casos nuevos en su próxima pasada. Se regeneró el reporte web
consolidado. Archivo tocado: `03_emparejamiento_bloques/match.py` (`match_paragraphs`).

**Próximo paso**: esperar que el usuario confirme los 2 casos nuevos y valide antes de
confirmar el commit; después seguir con los 2 manuales VSS restantes.

## 2026-09-13 (continuación 5) — Cierre de la iniciativa: los 8 manuales quedan con revisión manual completa

El usuario revisó los 2 manuales VSS restantes: `visanet_settlement_service_vss_user_guide_
volume_2_reports` (9 casos, todos "Ok") y `visanet_settlement_service_vss_user_guide_volume_1_
specifications` (confirmó directo contra `index.md` de Módulo 7 que el par vigente tiene 0
cambios de negocio). Ninguno con hallazgos de pipeline. Ver item 31 del TODO para la tabla
resumen completa de los 8 manuales.

**Cierra la iniciativa de revisión manual** iniciada 2026-09-12 (ver sección de esa fecha,
arriba). Total de bugs reales encontrados y arreglados en las 2 sesiones: 6 en
`tc_01_to_tc_49` (2026-09-12, commit `d7eb95f`), 2 en `base_ii_clearing_data_codes` y 1 en
`international_full_service_pos_online_messages_processing_specifications` (2026-09-13,
commit `5cc44d4`). Los otros 5 manuales (incluyendo los 2 VSS) no tuvieron ningún hallazgo de
pipeline -reportes ya validados como confiables contra el PDF real.

**Commit confirmado**: el usuario pidió explícitamente "commitea todo, pero no hagas push
aun" -commit `5cc44d4` (2026-09-13), working tree limpio salvo `.claude/settings.local.json`
(config local, deliberadamente sin trackear). Sin push todavía, a la espera de que el usuario
lo pida.

**Extra de esta sesión, no relacionado a bugs**: se agregó una pestaña "Leyenda de términos"
al reporte web consolidado (`08_reporte_web_consolidado/template.html`), con la definición de
cada pill (agregados/eliminados) por manual -a pedido del usuario, que se confundía con tantos
términos distintos entre los 8 adaptadores. También quedó documentado (solo como respuesta,
sin implementar) que extender el detalle de los "*_agregados"/"*_eliminados" al reporte web
(mostrar el `groups` completo, no solo el conteo en el pill) es un cambio acotado y de bajo
riesgo -los datos ya existen completos en `04_deteccion_cambios/*.json` (Módulo 4,
determinístico, sin IA), solo falta que los adaptadores de Módulo 8 los expongan. Si se pide en
el futuro, no requiere re-correr Ollama, solo tocar los 8 adaptadores + `template.html` y
volver a correr `build.py`.

**Próximo paso**: no hay una "próxima ronda" de revisión manual pendiente -los 8 manuales ya
están cubiertos; futuras rondas dependerían de nuevas ediciones de los PDFs fuente. El usuario
decide cuándo hacer push del commit `5cc44d4`.

## 2026-09-24 — Reporte web: pills de altas/bajas ahora muestran su detalle

Implementado lo que la entrada del 2026-09-13 dejó documentado como pendiente: los pills
secundarios del Módulo 8 (altas, bajas, secciones/tablas/fichas/párrafos/pares/filas
agregados o eliminados, transiciones Reserved↔definido, TC afectados) ahora son clicables y
despliegan el contenido de cada elemento, agrupado por su contexto (tabla, sección, apéndice,
TC). Los que valen 0 siguen siendo un chip plano.

- **Adaptadores**: cada pill secundario se arma con `_common.make_pill(label, details)`, cuyo
  `value` es `len(details)` -conteo y detalle no pueden divergir. Los datos salen del mismo JSON
  de Módulo 5 que ya se leía (no hizo falta leer Módulo 4 ni re-correr Ollama).
- **Plantilla**: `renderSecondaryChips` + `renderPillDetail` en `template.html`; un panel
  abierto a la vez por tarjeta, con scroll propio (POS tiene 387/328 párrafos agregados/eliminados).
- **Verificado**: `reporte_consolidado.json` antes vs. después -todos los conteos de pills
  idénticos, headline/groups/top_items idénticos, `estado_publicacion/` idéntico (0/8 nuevos).
  No se pudo probar el clic en un navegador desde la sesión (sin navegador headless disponible);
  el JS se revisó a mano.
- **Fuera de alcance**: en los 2 manuales de grillas existen `row_added/removed` y
  `card_added/removed` sueltos (dentro de secciones que siguen existiendo) que no tienen pill
  propio -no se agregaron pills nuevos, solo detalle a los existentes.
