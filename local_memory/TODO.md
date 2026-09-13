# TODOs pendientes — bugs conocidos, no arreglados

Lista viva de bugs/gaps conocidos que quedaron identificados pero sin resolver, para retomar
cuando se priorice. El detalle completo, la evidencia y el razonamiento de cada uno están en
`NOTES.md` (buscar por fecha/título) — este archivo es solo el índice accionable, no lo dupliques
con narrativa.

Estado general al 2026-08-12: Módulos 1, 2, 3 y 4 de `poc/base_ii_clearing_data_codes/` están
implementados y validados en las 9 ediciones / 8 pares. Todos los bugs "de datos reales" encontrados
durante esa validación ya se arreglaron (ver NOTES.md). Lo que queda abajo es lo que sobrevivió a
esa limpieza.

## 1. RESUELTO (2026-08-25) — Glosario del manual no se parseaba como entradas estructuradas
- **Dónde**: `base_ii_clearing_data_codes`, Módulo 1 (`ingest.py`) + Módulo 2 (`normalize.py`).
  Últimas ~14-22 páginas de cada edición (ej. p.141-157 en `20260418`).
- **Qué pasaba**: es una lista alfabética término→definición en prosa. Colapsaba en un solo
  bloque `table_header` gigante por página porque el heurístico de "¿fila nueva?" dependía
  solo de `CODE_LIKE` (código corto), y un término de glosario nunca matchea eso.
- **Hallazgo clave**: geométricamente es el MISMO patrón de 2 columnas (término X0=72 negrita /
  definición X0=216 regular, mismo tamaño 9.0pt) que Módulo 2 ya sabe reconstruir para las
  tablas de código -no hizo falta un tipo de bloque nuevo (`definition_list`), solo una señal
  tipográfica nueva.
- **Fix**: se agrega `bold` (negrita) y `max_size` por línea en Módulo 1. En Módulo 2, un nuevo
  estado `in_glossary` (activado al ver el encabezado real "Glossary" a 26pt -`max_size`
  necesario para no confundirlo con la entrada homónima de 12pt en la tabla de contenidos, misma
  negrita) hace que cualquier celda en negrita cuente como "celda-código" -así cada entrada se
  reconstruye como su propio `table_row` de 2 celdas. Un chequeo de hueco vertical entre líneas
  en negrita (`GLOSSARY_TERM_WRAP_GAP_MAX`) distingue un término envuelto en 2+ líneas (ej.
  "Account Screen Authorization File (ASAF)") de una entrada nueva.
- **Bug colateral encontrado y arreglado en el camino**: Módulo 3 (`match.py`) solo reconoce una
  tabla lógica cuando ve un `table_header` -sin uno, cada `table_row` sin tabla activa caía en
  el mecanismo genérico de "fila huérfana" (título `"(sin titulo)"`), que además fusiona
  CUALQUIER otra fila huérfana no relacionada del resto del documento. Arreglado emitiendo un
  `table_header` sintético (`["Term","Definition"]`) una sola vez, justo antes de la 1ra entrada
  real -sin tocar el mecanismo genérico que usan las demás tablas.
- **Verificado**: Módulos 1→4 re-corridos en las 9 ediciones, ~198-201 entradas limpias por
  edición (antes: 1-2 bloques gigantes), 0 tablas `"(sin titulo)"`, la tabla "Glossary" matchea
  estable entre las 8 ediciones consecutivas (194-201 filas matcheadas por par). Ya detecta
  cambios reales antes invisibles (ej. `OPTIONAL ISSUER FEE` cuya definición completa se
  reemplaza por "See Visa Issuer FX Calculator"). Módulos 5 y 7 re-corridos también (mismo día).
- Ref: NOTES.md, sección "2026-08-25 — Fix del glosario (item 1)".

**RESUELTO también en el 2do manual (`base_ii_clearing_edit_package_messages`, 2026-08-25,
misma sesión posterior)** — ver sección propia de ese manual más abajo (item 7 renombrado /
"Glosario de `base_ii_clearing_edit_package_messages`").

## 2. RESUELTO (2026-08-20) — `"Cook Islands (the) CK"` y otras fusiones de texto a nivel de Módulo 1 (PyMuPDF)
- Alcance real, más grande que lo logueado (1 fila, 1 edición): Cook Islands corrompido en 3
  ediciones (`20220423`-`20230415`, se autocorrige desde `20231014`), más el MISMO patrón de
  fusión en `Moroccan Dirham MAD`, `Canadian DollarS CAD`, `Zimbabwe Dollar ZWL`,
  `American Samoa AS`, y 2 instancias fuera de `Country and Currency Codes` (una tabla de
  definición de código en p.60, una matriz de 2 columnas en p.135/136).
- **Causa raíz**: PyMuPDF a veces agrupa 2 celdas de columnas DISTINTAS en una sola `line` con un
  span de puro espacio en blanco entre ambas (ej. `'Cook Islands (the)'` + `' '` + `'CK'`) —
  Módulo 1 concatenaba todo sin detectar el límite de celda.
- **Fix**: `_split_line_segments()` en Módulo 1 (`ingest.py`) corta una línea de PyMuPDF en
  segmentos independientes en cada span de solo-espacio, cada uno con su propio bbox recalculado.
  Confirmado con un escaneo del corpus completo (excluyendo las líneas de "dot leader" del
  índice) que esta señal SIEMPRE separa 2 piezas de contenido distintas, nunca aparece dentro de
  una celda real.
- **1 regresión encontrada y arreglada al validar**: dividir también rompía el filtro de "dot
  leader" del índice en Módulo 2 (que matchea sobre el texto COMPLETO de la línea) -el fragmento
  "Título" solo, ya sin los puntos de relleno, se colaba como contenido real. Arreglado
  detectando el patrón de dot-leader sobre el texto CRUDO sin dividir, y saltando la división por
  completo en esas líneas.
- **Verificado**: Módulos 1-4 re-corridos, 0 regresiones estructurales, página de índice
  confirmada limpia. **Módulos 5 y 7 re-corridos también** (mismo día, a pedido del usuario):
  Módulo 5 (301 items, ~50min) terminó con 0 errores, `safety_net_override`=10; Módulo 7
  regeneró los 8 reportes -se buscó "cook island" en los 8 archivos `.md`, 0 resultados,
  confirma que el fix eliminó el ruido espurio de punta a punta, no solo lo cambió de forma.
- Ref: NOTES.md, sección "2026-08-20 (cont. 2) — Fix del bug #2...".

## 3. RESUELTO (2026-08-20) — Texto de nota al pie se colaba en el límite de una tabla y corrompía filas ya emparejadas
- El alcance real, investigado a fondo el 2026-08-20, resultó MUCHO más grande que lo
  originalmente logueado (1 sola edición, ~4 filas): Croacia estuvo corrompida en **6 ediciones
  consecutivas** (`20221015`→`20250412`), Sierra Leone en 2 (`20221015`, `20230415`), por 2 causas
  raíz distintas:
  - **(a) Módulo 1 (`ingest.py`)**: un dígito de nota al pie en superíndice (6.75pt) se
    concatenaba sin separador en la MISMA línea de PyMuPDF que el código real (9.0pt) -ej.
    `'HRK'+'1'`→`'HRK1'`. Un escaneo completo del corpus mostró que esto afectaba MUCHOS más
    códigos que solo Croacia/Sierra Leone (ej. `Merchant Mailing CRB Region Codes`, donde
    `'X'+'1'` corrompido colisionaba visualmente con el código real y distinto `'X1'`).
  - **(b) Módulo 2 (`normalize.py`)**: cuando un país tiene una moneda en transición (vieja+nueva
    apiladas, ej. Sierra Leone `SLL/694` viejo + `SLE/925` nuevo), la fila secundaria SIN nombre de
    país se procesaba como fila huérfana independiente en vez de fusionarse con la fila del país
    correcto.
- **Fix**: (a) `_line_text_or_none()` en Módulo 1 descarta spans de fuente chica que sean
  puramente dígitos/comas antes de concatenar una línea. (b) Un chequeo de "cercanía a la columna
  ancla de la fila activa" (`SECONDARY_ROW_ANCHOR_GAP_MIN`) en Módulo 2 reenruta las filas
  secundarias fuera de ancla al mecanismo existente de fusión/`pending_prefix` en vez de tratarlas
  siempre como fila nueva.
- **2 regresiones encontradas y arregladas validando (b) contra las 9 ediciones completas** (no
  solo Croacia/Sierra Leone — mismo aprendizaje que el manual 8, "un umbral calibrado contra 1
  tabla no es seguro para las demás"): rompió 2 tablas donde un encabezado o un marcador
  `(continued)` arranca ~20-30pt a la izquierda de sus propias filas de datos por alineación
  tipográfica normal (arreglado acotando el chequeo a transiciones fila-a-fila y recalibrando el
  umbral a 150.0 con un escaneo real de brechas en las 9 ediciones: falsos positivos reales tope
  78.1pt, positivos reales desde 233.9pt); y una fila secundaria de Sierra Leone se pegaba a
  Singapur (el país siguiente) porque el hueco numérico resultaba menor aunque ninguno de los 2
  lados solapaba de verdad -arreglado exigiendo solape real en Y para diferir a la fila siguiente,
  si no, fusión directa con la fila activa.
- **Verificado de punta a punta**: Módulos 1→5 y 7 re-corridos, 0 regresiones estructurales en las
  9 ediciones (0 páginas sin bloques, 0 celdas vacías, conteos de fila estables), diffs de
  Croacia/Sierra Leone/Singapur leen correctamente en el reporte final.
- Ref: NOTES.md, sección "2026-08-20 (cont.) — Investigación completa y fix del bug #3...".
  Detalle completo también en la memoria del asistente (`pending_bug_fixes.md`, item 3).

## 3b. RESUELTO COMPLETO (2026-08-25, cerrado en 2 pasadas el 2026-09-05) — Zimbabue: nota al pie en el límite de tabla arrancando en la misma columna ancla
- **Dónde**: `base_ii_clearing_data_codes`, tabla `Country and Currency Codes`, fila `Zimbabwe`
  (última fila de la tabla en su página).
- **Causa raíz confirmada**: el bloque de notas al pie (y el título de la sección SIGUIENTE,
  `Canadian Province Codes`) arranca en la MISMA X0 que la columna ancla (nombre de país) -el
  heurístico de "¿párrafo nuevo?" solo disparaba cuando arrancaba MÁS a la izquierda, así que
  nunca detectaba este caso.
- **Fix (variante de marcador numerado, `"1 From 1 January 2023..."`)**: nueva señal
  `starts_with_footnote_marker` en Módulo 1 (dígito chico como PRIMER span de la línea, seguido
  de 15+ caracteres de prosa -distinto del patrón ya cubierto por el fix del item 3, donde el
  dígito va al FINAL). En Módulo 2, esta señal fuerza el mismo corte que el chequeo de margen
  izquierdo. **Verificado limpio en 5 de las 7 ediciones originalmente afectadas**
  (`20220423`-`20250412`).
- **Residuo SIN arreglar, alcance más grande de lo logueado originalmente**: desde la edición
  `20251018`, Visa cambió el formato de la nota de Zimbabwe a un párrafo con etiqueta en negrita
  `"Note:"` (sin marcador de dígito) -esta variante sigue fusionándose (`20251018`, `20260418`).
  Se investigó y se DESCARTÓ una regla genérica "arranca con Note: = corta la tabla": un escaneo
  del corpus completo encontró ~50 apariciones de `"Note:"` por edición, la mayoría LEGÍTIMAS
  dentro de una celda de código ya activa (ej. p.80, código `80`, `"Note: Product
  Reclassification occurs in these conditions:"` es parte de la descripción del código, no debe
  cortarse). Aplicar la regla globalmente habría arreglado Zimbabwe rompiendo docenas de filas
  reales en otras tablas. Hace falta una señal más específica (ej. salto de tamaño de fuente
  hacia el título de la sección siguiente, no disponible hoy en Módulo 2).
- **Por qué seguía siendo baja prioridad hasta cerrarlo**: los valores de código de Zimbabue en
  sí (`ZW`/`716`/`Zimbabwe Gold`/`ZWG`/`924`) quedaban limpios en las 9 ediciones -solo se
  ensuciaba el nombre del país en 2 de 9.
- **CERRADO 2026-09-05, en 2 pasadas.** Primera pasada: `MAJOR_HEADING_MIN_SIZE` (cualquier
  línea negrita ≥20pt corta el bloque activo, reutilizando el mismo umbral ya validado para el
  encabezado "Glossary") — cierra el residuo al 100% en `20260418` (Visa sacó la nota de
  ZWG/ZWL ahí) y lo reduce en `20251018` (ya no traga "Canadian Province Codes", solo queda
  pegada su propia nota). Hallazgo colateral real: el mismo bug (encabezado mayor fusionado a
  la última fila de una tabla activa) NO era exclusivo de Zimbabue — 5 de 8 pares mostraron
  altas/bajas de código espurias desaparecer tras el fix (ej. una tabla fantasma "Restricted
  Ticket Indicators" que aparecía/desaparecía entre pares, y `QATARI RIAL` mal atribuida a
  "U.S. State Codes" en vez de "Settlement Currencies"). Segunda pasada (mismo día, a pedido
  del usuario): `NOTE_BEFORE_HEADING_LOOKAHEAD` + `_note_precedes_major_heading` — señal de
  "mirar hacia adelante" con 3 condiciones (no es ella misma un código real, arranca en la
  misma columna ancla que la fila activa, y un encabezado mayor aparece dentro de las próximas
  5 filas sin ningún código real de por medio), medida contra las 9 ediciones completas ANTES
  de implementar: exactamente 8 casos en todo el corpus, 0 falsos positivos. 7 de los 8 NO eran
  Zimbabue — eran la misma nota recurrente "Type D (Dispute) stopped being valid" fusionada a
  los códigos `04` y `7` de 2 tablas de disputas distintas, en las 9 ediciones. Verificado
  end-to-end (Módulos 2→5,7 re-corridos): Zimbabue queda `"Zimbabwe"` limpio (8 caracteres) en
  las 9 ediciones; en Módulo 4 las únicas entradas `code_added`/`code_removed` que cambiaron
  fueron exactamente las contaminadas, desapareciendo de AMBOS lados sin generar ninguna nueva
  (ruido puro, confirmado programáticamente); `code_content_changed` byte-idéntico en todos los
  pares afectados. Módulo 5 re-corrido con Ollama real, clasificaciones consistentes. **Sin
  residuo — item cerrado por completo.**
- Ref: NOTES.md, sección "2026-09-05 — Cierre completo del item 3b (Zimbabue)".

## 4. `CODE_LIKE` no reconoce rangos de posición con guion (nota de diseño a futuro, no bug actual)
- **Prioridad: n/a todavía — aplica recién cuando se construya Módulo 2 para un manual Tipo A.**
- **Dónde**: aplica a futuro en `base_i`/`base_ii` manuales Tipo A (grids Position/Field/Length/
  Format/Contents, ej. `base_ii_clearing_interchange_formats_tc_01_to_tc_49`), NO a
  `base_ii_clearing_data_codes` (que no tiene esta columna).
  el regex `^[A-Z0-9]{1,6}$` no matchea rangos de posición tipo `"45-69"` (el guion los rompe).
- **Por qué no es urgente**: la columna `Format` (`AN`/`N`/`ANS`/`DX`/`UN`) está presente en
  prácticamente todas las filas de este tipo de tabla y sí matchea — así que el heurístico
  "código en cualquier celda" debería generalizar sin tocar nada. Esta nota es solo por si algún
  día se necesita usar la posición misma como ancla de código.
- Ref: NOTES.md, sección "Mapeo del mismo patrón... en el resto de familias de manuales".

## 5. RESUELTO (2026-08-25) — Red de seguridad de Módulo 5 disparaba con evidencia poco útil en filas con muchas viñetas
- **Dónde**: `base_ii_clearing_data_codes`, Módulo 5 (`classify.py`), función
  `_find_disappeared_content`.
- **Fix**: se filtran tokens que sean puramente un glifo de viñeta (`"l"`/`"●"`/`"•"`) antes de
  correr la detección de contenido desaparecido.
- **Hallazgo mayor al esperado**: no era solo cosmético -en los códigos `H0`/`HZ` de
  `Return/Reclassification Reason Codes` (par `20230415→20231014`), la red de seguridad forzaba
  `business_rule_change` basándose ÚNICAMENTE en viñetas que habían cambiado de posición (no de
  contenido real -confirmado comparando old/new palabra por palabra sin viñetas: la lista de
  campos era IDÉNTICA, solo se movieron las viñetas). Con el fix, ambos casos vuelven a
  `editorial_reword` (la clasificación correcta del LLM, antes descartada por la red de
  seguridad). Corrida completa re-verificada, 0 errores.
- Ref: NOTES.md, sección "2026-08-25 — Fix de items 5 y 6".

## 6. RESUELTO (2026-08-25) — El LLM a veces "tipeaba mal" números grandes en el texto de razón (`ai_reason`)
- **Dónde**: Módulo 5 (`classify.py`), prompt de clasificación.
- **Fix**: se agregó una instrucción al prompt pidiendo que, ante un cambio con número largo
  (monto/código), el LLM se refiera a "el valor anterior"/"el valor nuevo" en la razón en vez de
  re-tipear los dígitos. Bajo riesgo: el reporte (Módulo 7) siempre muestra `Antes`/`Ahora` desde
  el dato fuente, nunca desde el texto del LLM -esta instrucción no podía perder información, solo
  evitar el typo en la prosa.
- Ref: NOTES.md, sección "2026-08-25 — Fix de items 5 y 6".

## 6. El LLM a veces "tipea mal" números grandes en el texto de razón (`ai_reason`)
- **Prioridad: muy baja, cosmético.** No afecta los datos mostrados, solo la prosa.
- **Dónde**: Módulo 5/7, cualquier `code_content_changed` cuyo valor viejo/nuevo sea un número
  largo (ej. montos en dólares).
- **Qué pasa**: al repetir el número dentro de la explicación en español, el LLM a veces omite o
  cambia algún dígito (ej. dice "USD$749,9.99" en la razón cuando el valor real es
  "USD$749,999.99"). Los campos `old`/`new` que ve el reporte SIEMPRE vienen del dato fuente, nunca
  del LLM, así que el diff mostrado (Antes/Ahora) es siempre correcto — solo la oración de
  "Razón (IA)" puede tener un typo de dígitos.
- **Por qué no se arregló**: impacto muy bajo (no afecta la exactitud de los datos, solo la prosa
  explicativa), y es una limitación conocida de usar un modelo chico (4B) para regenerar números
  largos en texto libre.
- Ref: NOTES.md, sección de Módulo 7.

## 7. RESUELTO COMPLETO (2026-08-25, V0407 cerrado el 2026-09-05) — LLM clasifica mal 1 de 2 campos que reflejan el mismo hecho de negocio (manual 2) + glosario de este manual arreglado
- **Dónde**: `base_ii_clearing_edit_package_messages`, Módulo 5, ficha `V0407` (par
  `20221015→20230415`), campo `title`.
- **Causa raíz real, más precisa que lo logueado originalmente**: no era el umbral de 5
  palabras (`MIN_DISAPPEARED_WORDS`) como se pensaba -es que `_find_disappeared_content`
  NUNCA miraba los opcodes `"replace"` de `difflib`, solo `"delete"`. El cambio real
  (`"EQUALS B OR"` → `"EQUAL TO"`) es un `replace` de 3 palabras, no un `delete` -invisible a
  la red de seguridad sin importar el umbral.
- **Investigado el alcance antes de arreglar**: un escaneo del corpus completo mostró que
  este gap NO es solo cosmético -oculta reemplazos de contenido bastante más grandes e
  importantes en otras fichas/entradas de glosario (ej. ficha `V1209`: se elimina
  `"Fee Collection | Funds Disbursement"` de `transaction_types` sin dejar rastro, 7
  palabras; entrada de glosario `optional issuer fee`: 41 palabras de definición completa
  reemplazadas por `"See Visa Issuer FX Calculator"`) -ambos casos estaban mal clasificados
  como `editorial_reword` por el LLM, sin que la red de seguridad los corrigiera.
- **Fix**: `_find_disappeared_content` ahora cuenta tanto `"delete"` como `"replace"` con el
  MISMO umbral ya validado (5+ palabras) -sin bajar el umbral, confirmado con un escaneo del
  corpus que los `replace` cortos (3-4 palabras) que sí pasarían un umbral más bajo son
  mayormente renombres/abreviaturas inocuos (ej. `"Interchange Transaction File"` → `"ITF"`),
  así que bajarlo también habría sido inseguro.
- **Se probó primero un ajuste de prompt (revertido)**: instruir al LLM a prestar atención a
  listas de valores permitidos SÍ arregló `V0407` en una prueba aislada, pero al validarlo
  contra 4 casos de `editorial_reword` ya conocidos y correctos (fichas `V1232`/`V1235`/
  `V1236`/`V1245`, renombres de campo sin cambio de valor) el modelo empezó a clasificarlos
  TAMBIÉN como `business_rule_change` -una regresión real, no solo teórica. Descartado a
  favor del fix determinístico de la red de seguridad (más seguro, no depende del criterio
  variable del modelo).
- **Residuo original: `V0407` específicamente seguía sin arreglar** (su `replace` es de solo 3
  palabras, por debajo del umbral de 5).
  **CERRADO 2026-09-05.** En vez de bajar el umbral general (ya descartado, rompe renombres
  inocuos) se midió una señal MÁS ESPECÍFICA contra el corpus completo: un `replace`/`delete`
  corto que borra una conjunción ("or"/"and") JUNTO a un valor corto (1-3 caracteres, ej. "B")
  es casi siempre un valor enumerado que deja de ser válido, no una reformulación. Escaneando
  las 9 ediciones: exactamente 3 coincidencias en TODO el corpus (`V0407`/title, `V1073`/title
  — el MISMO bug nunca antes detectado en esta ficha —, y `V1089`/description, que ya se
  clasificaba bien por otro tramo más largo en el mismo campo). Fix scoped SOLO a este manual
  (`_removes_enumerated_value()` en `classify.py`, unido al resultado de la red de seguridad
  general, NO portado al módulo compartido `poc/_shared/ollama_client.py` — no se midió su
  seguridad para los otros 6 manuales). Verificado: simulado antes de gastar Ollama (2 flips
  predichos, coincidieron exacto), corrida real de Ollama acotada al par afectado confirmó
  `safety_net_override` 0→2, ambas fichas ahora `business_rule_change` con la marca ⚠️.
- **De paso, en la misma sesión**: se arregló también el glosario de este manual (mismo bug
  ya cerrado en `base_ii_clearing_data_codes`, ver su item 1) -arquitectura de Módulo 2
  distinta (stream de 1 sola ficha por vez, no filas/tablas), así que el fix se diseñó
  reusando el vocabulario de bloques `card_header`+`field` (`label="Description"`) en vez de
  portar el mecanismo `table_row` del otro manual. 181-183 entradas término/definición
  limpias por edición (antes: colapsaba en un solo bloque `paragraph` acumulado). Encontrado
  y arreglado en el camino: 3 ediciones viejas (`20220423`-`20230415`) usan `SegoeUI-Bold` en
  vez de `OpenSans-Bold` para el término (mismo rebrand ya documentado en este módulo para
  otra señal) -sin aceptar ambas fuentes, esas 3 ediciones quedaban con 0 entradas de
  glosario reconstruidas.
- **Nota separada, no confundir con lo de arriba**: el fix general "replace"+"delete" de
  `_find_disappeared_content` (lo que arregló V1209/glosario) se descubrió en 2026-09-04 que
  NUNCA se había portado a 5 de los 7 manuales con IA (una afirmación previa de "ya portado a
  todos" resultó falsa al re-verificar código real) — ver sección nueva "Tier 1: extracción a
  `poc/_shared/` + consolidación del fix de replace" más abajo para ese arreglo, separado de
  este item.
- Ref: NOTES.md, secciones "2026-08-25 — Glosario e item 7 de `base_ii_clearing_edit_package_messages`" y "2026-09-05 — Cierre del residuo V0407".

## 8. RESUELTO COMPLETO (grilla 2026-08-26, fichas cerradas 2026-09-05) — Problema "chain-shift" (manual 3, Módulo 3)
- **Historia**: logueado 2026-08-13 tras investigación empírica (1 caso real en 2173 secciones
  comparadas, 0.05%), diferido explícitamente por el usuario 2 veces (13/08 y 25/08 -"anotalo
  para verlo mas adelante"). El usuario preguntó en esta sesión si arreglarlo podía romper otra
  lógica; se explicó que el mecanismo diseñado es puramente ADITIVO (solo actúa sobre filas que
  YA quedaron sin matchear por posición exacta, nunca le roba un match a una fila que ya
  empareja bien) -confirmado el bajo riesgo, el usuario pidió implementarlo.
- **Dónde**: `base_ii_clearing_interchange_formats_tc_01_to_tc_49`, Módulo 3 (`match.py`,
  `_match_shifted_rows`) + Módulo 4 (`detect.py`, `_diff_row_cells` ahora también diffea la
  celda `Position` para estas filas específicas).
- **Fix**: tras el emparejamiento exacto por posición, las filas sin matchear en ambos lados de
  una sección se alinean por NOMBRE (`Contents`) usando `difflib.SequenceMatcher` sobre la
  secuencia de nombres de cada lado -mismo mecanismo de reconciliación ya usado para el reflow
  de párrafos del manual 6/7, toma los tramos "equal" aunque haya altas/bajas genuinas
  intercaladas, más robusto que exigir que ambas listas de sobrantes tengan la misma longitud.
  **Exclusión crítica, confirmada ANTES de implementar**: cualquier fila nombrada exactamente
  "Reserved" queda FUERA de este mecanismo -el patrón "Reserved se parte en campo nuevo +
  Reserved más chico" TAMBIÉN corre la posición del Reserved restante y reutiliza el mismo
  nombre "Reserved" en ambos lados; sin esta exclusión, el nuevo mecanismo le hubiera robado
  filas Reserved a `_detect_reserved_splits` (el mecanismo específico que Módulo 4 ya usa para
  el caso de uso central del proyecto) antes de que pudiera verlas -una regresión silenciosa
  del camino de detección más importante del proyecto.
- **Verificado contra el caso real conocido**: `TC 33.A - CP 12 TCR 4 Gateway Data,
  continuation` (par `20240413→20241019`) ahora se reporta como 2 `row_content_changed`
  limpios (Position+Length del campo que creció, Position+Format del campo que se corrió) en
  vez de 3 bajas+altas sueltas sin relación aparente. El 3er campo afectado (un `Reserved` que
  también se corrió) queda deliberadamente excluido -sigue viéndose como baja+alta, residuo
  aceptado, bajo valor informativo.
- **Alcance real MÁS GRANDE de lo medido originalmente**: se encontraron **7 casos reales de
  chain-shift en todo el corpus** (vs. el 1 originalmente medido) una vez que el mecanismo pudo
  efectivamente capturarlos -incluye un caso nuevo y sustancial, `TC 05 - TCR 2 Colombia` (3
  campos de impuestos que crecieron de 8-9 a 12 bytes cada uno, antes invisibles como 6
  bajas+altas sueltas sin relación). Confirmado 0 fugas de filas "Reserved" hacia el nuevo
  mecanismo y 0 doble conteo entre filas movidas y las listas removed/added, en los 8 pares.
- **Originalmente NO extendido a fichas (`match_cards`)**: investigado primero -el mismo caso
  real de chain-shift también existe en la ficha correspondiente, pero el campo `name` de la
  ficha NO es siempre byte-idéntico entre ediciones para el mismo campo (ej. `"character
  Mastercard - Service Location Postal Code"` → `"character Mastercard Service Location Postal
  Code"`, se cae el guion) -un emparejamiento EXACTO (seguro para filas de grilla, donde
  `Contents` SÍ es byte-idéntico en el caso real) fallaría acá, y uno FUZZY necesitaría su
  propia calibración/validación de umbral antes de confiar en él -no investigado, fuera de
  alcance esa sesión. Fichas quedaron sin mitigación de chain-shift.
  **CERRADO 2026-09-05.** No hizo falta fuzzy-matching genuino por ratio (el enfoque riesgoso
  que necesitaba calibración propia). Se midió primero, replicando el cómputo real de fichas
  sobrantes en los 8 pares: 6 pares YA con nombre exactamente idéntico (recuperables solo con
  el mismo mecanismo `SequenceMatcher` de las filas, sin lógica nueva) + exactamente 1 caso más
  (el conocido) que solo difiere por el guion caído. La solución fue una NORMALIZACIÓN de texto
  puntual (quitar un guion usado como separador de palabras antes de comparar por igualdad
  exacta), no fuzzy-matching — misma seguridad que el mecanismo de filas, alimentado con
  nombres normalizados. Bug real encontrado en el camino: la constante `DASH_CHARS` que ya
  existía en el archivo (para normalizar rangos de posición) solo cubre variantes Unicode de
  guion, NUNCA el guion ASCII común que aparece en los nombres reales de ficha — hizo falta una
  constante nueva (`NAME_SEPARATOR_DASH`). `_match_shifted_cards()` en `match.py` (misma
  exclusión de "Reserved" que las filas, por la misma razón), `_diff_card_fields()` en
  `detect.py` gana un flag `include_positions` (espejo de `start_index` en la versión de
  filas). Verificado: exactamente 7 shift-matches recuperados en todo el corpus (coincide
  exacto con la medición), added/removed cayeron por exactamente ese número en los 3 pares
  afectados, 0 cambio en los otros 5 (confirmado programáticamente). El caso real ahora
  renderiza como UNA entrada agrupada mostrando "Grilla" y "Ficha" juntas.
- **Verificado de punta a punta**: pipeline completo (Módulos 3→5,7) re-corrido en los 8 pares.
  Módulo 5 (567 items vía Ollama) clasificó los cambios de Position/Length de las filas movidas
  como `business_rule_change` de forma sensata. El reporte final del Módulo 7 muestra el caso
  conocido como UNA sola entrada agrupada ("Mastercard - Service Location Postal Code" con
  Position y Field Length juntos, razón de IA explicando correctamente el cambio de posición/
  longitud) en vez de ruido de baja+alta sueltos. Las fichas de esa misma sección siguen
  apareciendo como "Ficha eliminada" separada (esperado, alcance deliberadamente acotado a
  filas de grilla).
- Ref: memoria del asistente, `pending_bug_fixes.md` item 8; NOTES.md, secciones "2026-08-13
  (cont.) — Investigación del problema chain-shift..." (contexto original) y "2026-09-05 —
  Chain-shift extendido a fichas" (cierre).

## 9. RESUELTO (2026-09-12) — Edición `20260418` del manual 3 le faltan ~57 etiquetas "Note:" en la capa de texto del PDF
- **Dónde**: `base_ii_clearing_interchange_formats_tc_01_to_tc_49`, edición `20260418`
  específicamente (la más nueva). Módulo 4 (`detect.py`), no Módulo 1/2.
- **Qué pasa**: el span en negrita que renderiza la palabra "Note:" está directamente ausente de la
  capa de texto extraída por PyMuPDF en esta edición puntual -el resto del texto (itálica+regular)
  se extrae bien, pero sin la etiqueta Módulo 2 lo captura como continuación de `description` en
  vez de como `note` separado. Confirmado contando `"Note:"` en las 9 ediciones completas:
  274/274/274/274/274/272/273/273 en las primeras 8, **216 en `20260418`** -caída de ~57 casos
  (~21%), única de esa edición.
- **Diagnóstico anterior (2026-08-13/2026-09-05) INCOMPLETO, corregido esta sesión**: se había
  concluido "no arreglable sin OCR" y "la red de seguridad de Módulo 5 ya compensa el efecto
  práctico". Lo segundo era falso en la práctica: la red de seguridad SÍ marcaba estos casos, pero
  como `business_rule_change` con una razón enganosa ("el texto nuevo está vacío, artefacto de
  extracción") -no "compensaba" el efecto, generaba ~59 falsos positivos indistinguibles de un
  cambio real sin leer el PDF. El usuario los encontró todos a mano comparando el reporte contra
  el manual real (ver `revision_manual_2026-09-12.md`).
- **Fix real, sin necesidad de OCR**: en `_diff_card_fields` (Módulo 4), reportar UN solo
  `card_content_changed` con `field: "contenido"` (combinado de `description+note+values+mapping`)
  en vez de diffear cada columna por separado -el corrimiento de rótulo entre ediciones deja de
  verse como "un campo se vació, otro creció" cuando en realidad es el mismo texto reordenado.
  `name`/`length`/`format` se excluyeron del combinado (se siguen diffeando por separado siempre),
  lo cual de paso destapó 2 bugs más de Módulo 2 que estaban escondidos detrás del gate combinado
  del primer intento (ver NOTES.md).
- Ref completa (6 bugs relacionados encontrados y arreglados en la misma sesión, con evidencia y
  números): NOTES.md, sección "2026-09-12 — Revisión manual guiada por el usuario de
  `tc_01_to_tc_49`...".

## 10. RESUELTO COMPLETO (2026-08-25, residuo cerrado 2026-09-05) — Sección `TC 57` con 2 layouts distintos bajo el mismo título (manual 4)
- **Dónde**: `base_ii_clearing_interchange_formats_tc_50_to_tc_92`, sección
  `"TC 57 - TCR 5 - Limited Use Data"`, confirmado en las 9 ediciones.
- **Qué pasa**: 2 tablas "Record Layout" completamente distintas comparten el mismo título de
  sección Y el mismo párrafo introductorio, sin diferenciador textual entre ambas (variante 1:
  campo `Local Tax` @ 5-13; variante 2: `Banknet Settlement Number` @ 16-24, siempre en ese
  orden en las 9 ediciones).
- **Ya estaba arreglado (2026-08-19)**: pérdida de datos mitigada emparejando por orden de
  aparición en vez de por título (dict simple).
- **Fix nuevo (2026-08-25)**: se agregó `_section_signature()` en Módulo 3 -toma el nombre del
  primer campo de la grilla que NO sea parte del preámbulo común a toda sección de este manual
  (`Transaction Code`/`Transaction Code Qualifier`/`Transaction Component Sequence Number`) ni
  `Reserved` (el campo más genérico posible, casi nunca el distintivo real). Cuando un título
  colisiona (2+ secciones), ambos lados se reordenan por esta firma de CONTENIDO antes de
  emparejar por posición -no cambia nada en las 9 ediciones actuales (el orden ya era estable),
  pero ya no depende de que el orden se mantenga estable en una edición futura. Módulo 4
  propaga la firma a cada cambio; Módulo 7 la usa para separar los 2 layouts bajo encabezados
  legibles y distintos (`"... — variante con campo «Local Tax»"` /
  `"... — variante con campo «Banknet Settlement Number»"`) SOLO cuando el título realmente
  colisiona en ese reporte puntual (no ensucia el caso común).
- **Verificado**: Módulos 1→5 y 7 re-corridos en las 9 ediciones, 0 errores. Signature confirma
  el emparejamiento correcto (`Local Tax↔Local Tax`, `Banknet Settlement Number↔Banknet
  Settlement Number`) en los 8 pares. La etiqueta desambiguadora se probó con datos sintéticos
  (ningún par real tiene un cambio de contenido en esta sección puntual para verla en un
  reporte real) -1 bug propio encontrado y arreglado en el camino: el primer intento de
  `_heading_for_group` comparaba el título contra sí mismo en vez de contar signatures
  distintas, así que nunca disparaba el sufijo -detectado con la prueba sintética antes de
  darlo por bueno.
- **Residuo original: la etiqueta seguía siendo solo un nombre de campo real (`Local Tax`),
  no una etiqueta de negocio con significado propio.**
  **CERRADO 2026-09-05** — recomendado por el asistente como el residuo de menor esfuerzo de
  toda la lista (elegido explícitamente por el usuario para arrancar por ahí). No se intentó
  fabricar una "explicación de negocio" que no existe en los datos fuente — se hizo el
  desambiguador existente accionable: ahora también muestra la POSICIÓN del campo distintivo
  (`"... — variante con campo «Banknet Settlement Number @ 16-24»"`), suficiente para que quien
  lee el reporte ubique el campo en el layout de bytes sin cruzar contra la tabla completa.
  Cambio 100% aditivo: `_section_signature()` devuelve `(nombre, posición)` en vez de solo
  nombre, propagado como campo nuevo `signature_position` en Módulos 3→4→7 junto al `signature`
  ya existente, sin tocar matching/detección. Verificado: Módulos 3→4 re-corridos en los 8
  pares, byte-idénticos al descontar el campo nuevo. Al re-correr Módulo 5 completo (necesario
  para refrescar el campo nuevo en disco) se encontró, de paso, una corrección legítima NO
  relacionada: 1 de 8 pares tenía una clasificación desactualizada del fix de "replace opcode"
  (ver Tier 1 más abajo) que nunca se había re-verificado para este par puntual — confirmado
  como corrección real, no regresión, llamando a la función determinística varias veces con el
  mismo texto exacto.

## 11. RESUELTO (2026-08-25) — Título de tabla-ficha se filtraba en la descripción del primer campo (manual 4)
- **Dónde**: `base_ii_clearing_interchange_formats_tc_50_to_tc_92`, sección "Passenger
  Itinerary Data - Leg-Specific", campo `Transaction Code` @ posición 1-2 (3 de 9 ediciones).
- **Causa raíz confirmada**: el título de la tabla-ficha, un párrafo de PROSA en 10.5pt, a
  veces se extrae partido en 2 fragmentos que comparten la MISMA banda Y (mismo
  `source_block` de PyMuPDF -confirmado, quirk de layout, no un patrón reconocible). El 2do
  fragmento (bien a la derecha) resulta geométricamente IDÉNTICO al patrón legítimo que
  `same_row_as_next_name` está diseñado para detectar -la 1ra línea de `Description:` de un
  campo real compartiendo fila con su propio nombre (patrón usado en CASI TODAS las ~1700
  fichas del documento, no un caso raro) -así que el fragmento del título se cuela como si
  fuera la descripción del PRÓXIMO campo real.
- **Fix**: se distinguen por tamaño de fuente -el nombre real de un campo siempre es 9.0pt,
  un título de tabla-ficha 10.5pt- confirmado con un escaneo completo de las 9 ediciones:
  18167 disparos legítimos de `same_row_as_next_name` a 9.0pt, exactamente 7 a 10.5pt (los 6
  del bug conocido -2 por edición en las 3 afectadas, una para el título de la grilla que no
  causa daño visible, otra para el de las fichas que sí- más 1 caso adicional no logueado
  antes, un párrafo narrativo de 2 líneas en `20230415` p.288 que probablemente tampoco
  causaba daño visible pero quedaba igual de mal capturado). Se excluye `same_row_as_next_name`
  cuando el párrafo activo es 10.5pt.
- **Verificado**: Módulos 1→5 y 7 re-corridos en las 9 ediciones, 0 regresiones (0 fichas con
  contenido totalmente vacío, `Transaction Code` limpio en las 3 ediciones antes afectadas).

## 12. RESUELTO (2026-08-25) — Ficha con lista `Values:` larga se fragmentaba en varios `field_card` entre páginas (manual 4)
- **Dónde**: `base_ii_clearing_interchange_formats_tc_50_to_tc_92`, sección
  `"TC 90 - TCR 0 - Incoming ITF"`, campo `"BASE II Customized Delivery File Type"` @ 109-113
  (1 edición, `20220423`, 3 fragmentos).
- **Fix**: en Módulo 2, cuando una ficha nueva trae el sufijo literal `"(continued)"` en su
  nombre Y su posición coincide EXACTO con la última ficha ya emitida, se reabre esa ficha
  (`blocks.pop()`) en vez de crear una nueva.
- **1 bug real encontrado y arreglado validando (no en el diseño original)**: el layout de 2
  columnas de las fichas hace que la 1ra línea de la columna derecha de la continuación
  ("Note: Values continued:") se procese ANTES que el "Positions:" de esa misma continuación
  (mismo mecanismo de reordenamiento por Y ya visto en el item 11) -sin fusionar
  explícitamente ese `pending_right` buferizado al reabrir la ficha, el contenido de la
  continuación se perdía en silencio (la ficha quedaba con solo el contenido de su 1ra
  aparición). Arreglado fusionando `pending_right` al `active_card` reabierto, igual que ya
  se hace al crear una ficha nueva.
- **No confundir con el caso similar en la sección "Outgoing ITF"** (mismo nombre de campo)
  -ese SÍ es un cambio editorial real de Visa (lista de valores removida a favor de una
  referencia cruzada), confirmado en su momento vía `safety_net_override` de Módulo 5, no
  tocado por este fix.
- **Verificado**: 0 fichas `"(continued)"` sin fusionar en las 9 ediciones; la ficha fusionada
  trae el texto completo de sus 3 fragmentos (`note` con ~1685 caracteres, todas las
  ~70 opciones de `Values:` presentes).

## 13. RESUELTO (2026-08-25, manual 6) — Re-corte de párrafos por reflow de página, generalizado a N:M
- **Dónde**: `international_full_service_pos_online_messages_processing_specifications` (6to
  manual), Módulo 3 (`match_paragraphs`).
- **7mo manual (`visanet_settlement_service_vss_user_guide_volume_1_specifications`), su
  propia variante RESUELTA (2026-08-26)** — ver detalle completo en el item 14 más abajo (se
  documenta ahí porque es exactamente el residuo que ese item ya tenía logueado). Root cause
  distinto al de este item (no era reflow de párrafos, sino fusión de 2 celdas de PyMuPDF en
  una sola `line` con un span de solo-espacio en el medio) -mismo mecanismo del item 2 (Cook
  Islands, manual 1), no el mecanismo `SequenceMatcher` de este item 13, portado a líneas
  rotadas.
- **Qué pasaba**: el fix original (2026-08-19) solo resolvía el caso "2 párrafos de un lado
  concatenados = 1 párrafo suelto del otro lado, EXACTO" (pares adyacentes 2:1/1:2). Quedaban
  sin resolver variantes más generales -confirmado con un caso real 2:2 en la sección "Card
  Verification Value (CVV) Service": una oración vive pegada al final de un párrafo largo en
  la edición vieja Y una oración totalmente distinta es su propio párrafo separado; en la
  edición nueva se reagrupan al revés -ningún sub-par de 1 contra 2 (ni al revés) alcanzaba a
  matchear solo, pero los 2 párrafos de cada lado, concatenados, eran idénticos.
- **Fix**: rediseño completo de `match_paragraphs` -en vez de un dict de texto exacto +
  búsqueda de pares adyacentes por separado, corre UN SOLO `difflib.SequenceMatcher` sobre
  las listas de texto normalizado de párrafos de cada lado (párrafo como unidad atómica de
  comparación). Sus opcodes dan gratis lo que hacía falta: `"equal"` = párrafos idénticos
  (reemplaza el emparejamiento exacto anterior, más robusto ante duplicados intercalados);
  `"replace"` (bloque de N párrafos de un lado, M del otro) = candidato a reflow -se
  concatena el texto completo de ambos bloques y, si coincide exacto, es reflow N:M puro (sin
  importar el tamaño de cada lado, el 2:1 original queda cubierto como caso particular); si no
  coincide, ambos lados del bloque caen al pool de fuzzy-matching de siempre (mismo
  comportamiento que antes para contenido que sí cambió). `"delete"`/`"insert"` = mismo pool
  de fuzzy que antes.
- **Limitación aceptada conscientemente**: un bloque `"replace"` MIXTO (parte reflow + parte
  cambio real en el mismo tramo) no se sub-divide -cae entero al pool de fuzzy, igual que
  antes de este fix. No se encontró ningún caso así en el corpus completo al validar.
- **Verificado**: Módulos 3→5 y 7 re-corridos en las 6 ediciones/7 pares. 18 casos reales de
  reflow N:M genuino encontrados más allá del 2:1 (hasta 5↔4 en una sección), incluido el caso
  CVV confirmado a mano. `safety_net_override` total bajó de 14 (baseline del fix 2:1) a 10
  -el caso CVV específicamente pasó de generar un `business_rule_change` falso a
  reconciliarse correctamente como `paragraph_reflowed`. 0 errores, 0 regresiones (el hallazgo
  ya validado del rename "Exception File"→"ASAF" sigue apareciendo igual en el reporte).
- Nota: sigue anotado en la memoria del asistente (`dev_phase_considerations.md`, items 7-8)
  como consideración cross-cutting para el desarrollo real -el 7mo manual todavía tiene su
  propio residuo sin resolver.

## 14. RESUELTO (2026-08-26, en 2 pasadas el mismo día) — Pares Field Name/Description con emparejamiento geométrico imperfecto (manual 7)
- **Dónde**: `visanet_settlement_service_vss_user_guide_volume_1_specifications`, Módulo 1
  (`ingest.py`) + Módulo 2 (`_extract_rotated_pairs`).
- **Sub-caso RESUELTO (2026-08-26)**: una fracción real de los pares con `description` vacía
  no era un fallo de la reconstrucción geométrica de Módulo 2, sino el MISMO bug que el item 2
  (Cook Islands, manual 1) -PyMuPDF fusiona la celda de `name` y la de `description` en una
  sola `line`, separadas solo por un span de puro espacio en blanco, típicamente cuando la
  descripción es corta y cabe en la misma "fila" rotada que el nombre (ej. pág. 112,
  `"CARDHOLDER BILLING AMT CUR"` + `"Clearing currency. On the VSS reports..."` fusionados en
  1 sola línea). Confirmado con un escaneo completo del corpus (6 ediciones) ANTES de tocar
  código: 9-10 instancias reales por edición, siempre exactamente 3 spans (nombre/espacio/
  descripción), siempre 9.0pt uniforme -patrón muy limpio y seguro de generalizar. Las ~47
  apariciones más del mismo patrón por edición caen en páginas que Módulo 2 ya descarta
  enteras (sin el literal `"Field Name"`) -dividirlas ahí no cambia nada. **Fix**: se portó
  `_split_line_segments`/`_segment_bbox` del manual 1 a `ingest.py` de este manual, ACOTADO
  solo a líneas rotadas (`dir == (0.0,-1.0)`) -el mismo patrón existe también en texto
  horizontal, pero ahí son 2 casos ya conocidos y deliberadamente no tocados: líneas de tabla
  de contenidos (dot-leader, ya filtradas por Módulo 2) y una tabla horizontal "Report ID /
  Report Title" cuyo residuo fusionado ya estaba aceptado explícitamente (ver nota de Módulo 7
  en la sesión 2026-08-19, "read as short report-name/description table fragments... not a new
  bug worth chasing") -tocar líneas horizontales hubiera reabierto ese scope sin necesidad.
  **Verificado end-to-end**: descripciones vacías bajaron de 109→101 (ediciones viejas) y
  82→73 (ediciones nuevas) -exactamente los casos reales fijados, 236 pares totales sin
  cambio (no se crean pares fantasma). Módulos 3→5 y 7 re-corridos en las 6 ediciones/5 pares:
  pares 236/236 matched en cada par (0 regresión), `safety_net_override` Módulo 5 = 2 (igual
  que la baseline previa al fix), reporte final confirma que los casos arreglados (ej.
  `ACCEPTED COUNT`) se clasifican correctamente como `extraction_noise`, no como falso
  `business_rule_change`. Un diff nuevo que apareció al re-correr (`"report."`→`"SMS600C
  report."` en el par `20230415→20231013`, tabla "Example 5") se investigó a fondo y se
  confirmó que es PREEXISTENTE y no relacionado a este fix (ninguna línea de esa página se
  dividió) -pertenece al residuo de abajo, no es una regresión.
- **2do sub-caso, TAMBIÉN RESUELTO el mismo día** (el usuario preguntó directamente si era
  seguro arreglarlo antes de pedir que lo implementara): el problema geométrico DISTINTO y más
  profundo encontrado investigando el diff `"SMS600C report."` de arriba -cuando una
  descripción larga ENVUELVE a una 2da sub-banda de `x0` dentro de la misma celda rotada (ej.
  `x0=157.4` para el cuerpo del texto, `x0=169.4` para la cola envuelta "SMS600C report."),
  Módulo 2 la trataba como 2 "filas" (bandas de `x0`) distintas en vez de una sola descripción
  continua -la cola quedaba huérfana o, peor, se la robaba el nombre INCORRECTO más cercano
  (ej. `"[CLEARING AMOUNT]"` en vez de completar la descripción real de `"CLEARING AMOUNT"`).
  **Investigado con el mismo rigor de evidencia de corpus completo que el item 8 (chain-shift)
  antes de implementar**: se escaneó cada gap consecutivo entre líneas de descripción (por
  `x0`) en las 6 ediciones/todas las tablas reales -el gap real de wrap-continuación es
  SIEMPRE exactamente 12.0pt (87 instancias, 0 variación, cada una completa una oración
  truncada al leerla), mientras que el gap mínimo real entre 2 filas DISTINTAS es 17.0pt -límite
  limpio, sin superposición, incluso más limpio que el del item 8. **Fix**:
  `_merge_wrapped_descriptions` (función nueva, umbral `DESC_WRAP_GAP_MAX=15.0`, mitad de
  camino) fusiona líneas de descripción consecutivas por debajo de ese gap en una sola ANTES
  de que corra el emparejamiento nombre↔descripción existente -conserva el `x0` del primer
  fragmento (el que ya matchea bien hoy), así que el mecanismo de emparejamiento no necesitó
  ningún cambio, puramente aditivo. **Verificado**: `CLEARING AMOUNT` ahora tiene su
  descripción completa; las entradas con corchetes que antes robaban el fragmento huérfano
  (`"[CLEARING AMOUNT]"`, `"[CARDHOLDER BILLING AMT CUR]"`, `"[TOTAL ISSUER INTERCHANGE]"`)
  ahora correctamente quedan con descripción vacía -mismo patrón legítimo ya establecido para
  `"Row"`/`"Column"`. 236 pares sin cambio, Módulo 3 236/236 matched sin regresión, el ruido de
  truncamiento tipo "SMS600C report." desapareció por completo del diff (`pair_content_changed`
  bajó de 41 a 21, los 21 restantes son todos el patrón ya aceptado de descripción-vacía-en-
  edición-vieja). Módulo 5 (`safety_net_override`=2, igual que antes) y Módulo 7 (mismo conteo
  de cambios de negocio, 0/2/7/2/0) re-corridos, 0 regresión.
- **Residuo restante, legítimo, no es un bug**: sub-encabezados `"Row"`/`"Column"` sin
  descripción propia (~23 apariciones cada uno) -mismo patrón siempre aceptado, no queda nada
  más por arreglar acá.

## 15. RESUELTO (2026-08-26) — Descripción se pega al `Field Name` anterior en filas puntuales (manual 8, Apéndice B)
- **Dónde**: `visanet_settlement_service_vss_user_guide_volume_2_reports`, Módulo 1
  (`ingest.py`, nuevo campo `segments`) + Módulo 2 (`normalize.py`, `_resegment_by_column`).
- **Causa raíz confirmada**: MISMO bug de fusión de PyMuPDF ya visto en el manual 1 (Cook
  Islands, item 2) y el manual 7 (item 13/14, pares rotados) -2 celdas lógicas distintas
  (`Field Name`/inicio de `Description`) fusionadas en una sola `line` de PyMuPDF separadas
  por un span de puro espacio en blanco (ej. edición `20231013`, "Net Amount Sign" + espacio +
  "This field contains the sign for the"). **Complicación nueva encontrada, no presente en los
  otros 2 manuales**: el MISMO síntoma geométrico (span de espacio interno) también separa
  cada PALABRA de un título/leyenda de una sola celda legítima en otras partes de este manual
  (ej. Apéndice A rotado, "Settlement Warehouse Returned CRS Deferred", un único row-label; o
  una leyenda "n = Numeric x = Alphanumeric..."; o una celda `Comments` con 2 oraciones unidas
  por un espacio angosto U+202F) -dividir a ciegas como en los manuales 1/7 hubiera roto esos
  casos.
- **Fix, más quirúrgico que en los otros 2 manuales**: Módulo 1 expone los segmentos
  candidatos (divididos SOLO por spans de puro espacio, sin decidir nada) vía un nuevo campo
  `segments`. Módulo 2's `_resegment_by_column` (llamado desde `_build_table_rows`, que ya
  conoce la geometría de columnas de la tabla activa) solo aplica la división cuando los
  segmentos caen en bandas de columna REALMENTE distintas (`_nearest_band`) -si todos los
  segmentos mapean a la misma columna, se mantiene fusionado tal cual (título/leyenda intacto).
- **Verificado real, no solo geometría**: 0 casos sospechosos restantes tras el fix (escaneo
  de `Field Name` con >6 palabras + puntuación en las 7 ediciones), 0 regresión en los 3 casos
  de riesgo confirmados (título rotado multi-palabra, leyenda con abreviaturas, celda envuelta
  con narrow-no-break-space). `grid_row` totales sin cambio (2601-2685, igual que baseline),
  0 filas vacías, 0 fuga de contenido descartable.

## 16. RESUELTO (2026-08-26) — Filas de tablas rotadas partidas en fragmentos espurios por un umbral de wrap mal calibrado (manual 8, Apéndices A/D)
- **Dónde**: `visanet_settlement_service_vss_user_guide_volume_2_reports`, Módulo 2
  (`normalize.py`, `ROTATED_ANCHOR_WRAP_GAP_MAX`).
- **Causa raíz real, DISTINTA de lo originalmente logueado** (se pensó que era un problema de
  salto de página real -Módulo 2 nunca lleva filas de una página a la siguiente-, pero
  investigando el caso concreto se confirmó que NO: `VSS-116`/`(Fee by Jurisdiction)` están en
  la MISMA página 25, no en páginas distintas). El umbral `ROTATED_ANCHOR_WRAP_GAP_MAX=4.0`
  (calibrado 2026-08-19 contra solo 2 tablas) no veía un SEGUNDO modo de envoltura legítima:
  cuando el valor de la columna ancla envuelve a 3+ líneas, el gap entre el 2do y 3er
  fragmento puede ser mayor (4.1-6.6pt) que el gap típico entre el 1ro y 2do (~0pt) -por
  encima del umbral original, disparando una fila nueva espuria que separaba el último
  fragmento del resto de su propio valor.
- **Recalibrado con evidencia del corpus completo** (7200 gaps reales, 7 ediciones, Apéndices
  A+D, reusando la lógica real de zonas/columnas del módulo, no una aproximación): límite
  limpio y SIN superposición -máximo gap de envoltura real 6.6pt, mínimo gap de fila nueva
  real 7.0pt. Recalibrado a 6.8 (mitad de camino).
- **Alcance real MUCHO más grande de lo originalmente logueado**: el ítem se había logueado
  como "2 instancias confirmadas" (`VSS-116`/`VSS-116-M`), pero investigando se encontró que
  las 3 ediciones más viejas (`20220423`-`20230415`) tenían el MISMO bug afectando 35 de 79
  filas (44%) de la tabla `Available VSS Reports` -el síntoma ahí era distinto y parecía un
  problema no relacionado (el ID `"VSS-100-W —"` faltaba del inicio de cada título), pero
  resultó ser la misma causa raíz, solo con más fragmentos por fila en esas ediciones. Tras el
  fix: 0 filas con el ID faltante en las 7 ediciones (antes: 35 en 3 ediciones).
- **Verificado end-to-end**: `grid_row` totales bajaron 2601-2685 → 2509-2582 en todo el
  manual (fusión de fragmentos espurios de vuelta a su fila real, no pérdida de datos),
  `unassigned_prefix` sin cambio (1-3, igual que baseline), 0 filas vacías. Reconfirmado que
  el caso ORIGINAL que motivó el umbral de 4.0 (Apéndice D p.366, V22200, 9 campos separados)
  sigue correctamente separado (10 filas, ni una fusión de más). Módulos 3/4 re-corridos:
  conteos de tablas sin cambio (solo cambian conteos de filas), `row_content_changed` total
  bajó 419→383 tras este fix (encima de los 445→419 ya logrados por items 15/17).

## 17. RESUELTO (2026-08-26) — Título `"TC 46, TCR N..."` sale con "TCR" partido en 2 palabras en 1 de ~6 re-declaraciones (manual 8, Apéndice B)
- **Dónde**: `visanet_settlement_service_vss_user_guide_volume_2_reports`, Módulo 2
  (`normalize.py`, `_clean_text`, junto al fix de NBSP ya existente).
- **Qué pasaba**: el mismo título de tabla se re-declara en cada página (~6 veces por tabla);
  en 1 sola de esas ~6 apariciones el texto extraído trae "TCR" partido en 2 palabras
  (`"TC R"`) Y con espacio normal en vez de NBSP -confirmado en edición `20240413`, `Report
  Subgroup 2`: 1 línea lee `"TC 46, TC R 0 (Report Subgroup 2)..."`, las otras 5 leen
  `"TC\xa046, TCR\xa00 (Report Subgroup 2)..."`.
- **Fix**: escaneo completo del corpus (7 ediciones, las 5 apéndices) del substring literal
  `"TC R"` (con límite de palabra) -aparece SOLO en 3 ediciones consecutivas
  (`20230415`-`20240413`, se autocorrige desde `20250412`), SIEMPRE las mismas 9 instancias (1
  por tabla "Report Subgroup"), CERO apariciones legítimas en cualquier otro lugar del corpus
  -señal perfectamente segura para una sustitución de texto. Agregado `TCR_SPLIT =
  re.compile(r"\bTC R\b")` a `_clean_text`, junto a la normalización de NBSP ya existente.
- **Verificado**: todos los títulos "Report Subgroup" ahora leen "TCR" consistente en las 9
  instancias/3 ediciones afectadas. Módulo 3: Apéndice B del par `20240413→20250412` pasó de
  `30->22 tablas (+0/-8)` a `22->22 tablas (+0/-0)` -las 8 tablas eliminadas espurias
  desaparecieron. Módulo 4: el `table_removed=8`/`table_renamed=1` de ese par desapareció del
  todo.
- Ref: memoria del asistente, `manual8-vss-vol2-progress.md`, bug 12.

**Con esto, el manual 8 (`visanet_settlement_service_vss_user_guide_volume_2_reports`) tiene
sus 3 items conocidos (15/16/17) resueltos y verificados de punta a punta** -sesión
2026-08-26. Full pipeline (Módulos 1→5,7) re-corrido con los 3 fixes juntos en las 7
ediciones/6 pares: `row_content_changed` total 445→383 (Módulo 4), `safety_net_override`
total 18→9 (Módulo 5, 383 items vía Ollama) -el par `20231013→20240413` (6 overrides
originalmente atribuidos al item 16) pasó a 0. Módulo 7 regeneró los 6 reportes: cambios de
negocio por par 86/12/29/6/7/9 (antes de estos 3 fixes: 90/12/47/11/8/9 -caídas grandes en los
pares 3 y 4, justo los más afectados por el ruido espurio de items 15/16/17). Chequeo puntual
del caso VSS-116/VSS-116-M en el reporte final: ambas ediciones extraen su título completo
limpio, confirmando que el sufijo "(Fee by Jurisdiction)" es un cambio de título REAL entre
ediciones (no un residuo de extracción), correctamente capturado como rename genuino ahora
que ambos lados parsean sin fragmentación.

**Con esto, tanto el manual 7 como el manual 8 -el orden pedido explícitamente por el usuario
para esta sesión- quedan completamente cerrados.**

## Próximo paso NO relacionado a bugs (recordatorio de roadmap, no un TODO de corrección)

**ESTADO AL 2026-08-13, para retomar en la próxima sesión:**

- **Manual 1, `base_ii_clearing_data_codes`**: pipeline completo (Módulos 1-5 y 7) implementado y
  validado de punta a punta. Módulo 6 (Validación con Plataforma STD) se salteó -sigue
  tentativo/sin definir, tal cual el plan original del usuario.
- **Manual 2, `base_ii_clearing_edit_package_messages`** (elegido explícitamente por el usuario,
  Tipo F -fichas de código de error/edición): **pipeline completo (Módulos 1-5 y 7) implementado y
  validado de punta a punta**, igual que el manual 1. Módulo 6 (Validación con Plataforma STD)
  queda deliberadamente salteado/tentativo en los 2 manuales, sin definir.
  Módulo 3 (`match.py`) empareja fichas por código exacto; Módulo 4 (`detect.py`) difea por NOMBRE
  de campo (`title`/`description`/`action`/`transaction_types`) con umbral `difflib` 0.98; Módulo 5
  (`classify.py`, Ollama + `qwen3:4b`, mismas 3 categorías que el manual 1) clasifica los
  `ficha_content_changed`; Módulo 7 (`report.py`) agrupa por ficha (no por tabla, no existe ese
  nivel acá) y arma 1 reporte Markdown por par + `index.md`.
  Durante la validación de Módulos 3-5 se encontraron y arreglaron 4 bugs reales de Módulo 2, todos
  el mismo día por tocar datos reales de campos comparados: footer y header con bandas Y mal
  calibradas, el glifo de viñeta `"l"` de 8 de las 9 ediciones nunca reconocido (los 3 detectados
  vía Módulo 3), y una etiqueta `"Action:"` pegada al final de la línea de `Description:` en la
  ficha `V0545` en 8 de las 9 ediciones (detectado vía la red de seguridad de Módulo 5). Patrón que
  se repite en los 4: la calibración/heurística rota siempre se había validado solo contra UNA
  edición (casi siempre la de referencia, la más nueva), nunca contra las 9 completas. Detalle
  completo en `NOTES.md`, secciones "2026-08-13 — Módulo 3...", "2026-08-13 (cont.) — Módulo 5..."
  y "2026-08-13 (cont.) — Módulo 7...".
  Resultado final de Módulo 5 sobre las 8 corridas: `business_rule_change`=39,
  `editorial_reword`=20, `extraction_noise`=0, `safety_net_override`=0 -limpio, sin bugs residuales
  visibles a ese nivel.
- **Manual 3, `base_ii_clearing_interchange_formats_tc_01_to_tc_49`** (elegido explícitamente por
  el usuario, Tipo A -el target central del proyecto: grids Position/Field/Length/Format, campos
  "Reserved"): **Módulos 1 y 2 implementados y CERRADOS.**
  Módulo 1 (`01_ingesta_parseo/ingest.py`) arrancó como copia del manual 1 (bbox+texto) pero
  terminó necesitando `max_font_size`/`fonts` igual que el manual 2 -decidido recién al diseñar
  Módulo 2 con datos reales, no de antemano. Documento bastante más grande que los otros 2 (883-940
  páginas, 9 ediciones).
  Módulo 2 (`02_normalizacion_bloques/normalize.py`) resultó ser el más complejo de los 3 manuales:
  CADA sección TC/TCR mezcla 2 patrones de contenido (grilla "Record Layout" Tipo B + fichas "Edit
  Criteria" con layout de 2 columnas, no una grilla) -se manejan con algoritmos distintos, no un
  único mecanismo forzado. Se encontraron y arreglaron 8 bugs reales (ver `NOTES.md`, sección
  "2026-08-13 (cont.) — Módulo 2... 8 bugs reales"): orden de columnas del header de grilla (`Field`
  +`Length` son 1 sola columna, no 2), detección de número de página por posición (asunción
  "última línea" falsa), título de tabla re-declarado colándose como fila de datos, Description que
  comparte fila con el nombre del campo SIGUIENTE (llega antes que su propio `Positions:`),
  contenido de columna derecha pegándose a la ficha vieja en vez de la nueva (bug simétrico al
  anterior, en continuaciones sin etiqueta), el ":" faltante después de `Description` en el PDF
  fuente (9 casos reales), `Description` sin ninguna etiqueta en absoluto (texto crudo), y una celda
  `Contents` envuelta que no solapa la banda Y de su fila (mismo quirk ya visto en el manual 1,
  aplicado acá a esta grilla).
  Validación final en las 9 ediciones completas: 0 filas de grilla con cantidad de celdas
  incorrecta, 0 fichas con nombre o posición vacíos, 0 celdas de posición que no matcheen el patrón
  esperado -solo 2 anomalías de contenido REAL de la fuente (label duplicado, guión de más), no
  bugs, 1 ocurrencia cada una. Detalle completo en `NOTES.md`.
  **Módulo 3 implementado y CERRADO.** Investigado empíricamente el problema de "chain-shift"
  ([[reference-pipeline-vs-technical-manuals]]) ANTES de diseñar el emparejamiento: comparando los
  8 pares de ediciones (2173 secciones comunes), aparece un chain-shift real en 1 sola sección
  (0.05%) -el resto de los cambios de posición son el patrón "Reserved se parte en campo nuevo +
  Reserved más chico", que no corre nada porque el campo nuevo se talla del INICIO del rango
  existente. Con esa evidencia, el usuario decidió explícitamente (`AskUserQuestion`) NO
  implementar la mitigación de ancla ordinal propuesta en el diseño original -emparejar por
  posición exacta alcanza para ~99.95% de los casos reales, el caso raro queda como TODO de baja
  prioridad (ver abajo, item 8).
  `match.py` reconstruye secciones TC/TCR (delimitadas por `section_heading`, ya explícito desde
  Módulo 2) con 2 listas paralelas -filas de grilla y fichas- y las empareja como 2 problemas
  INDEPENDIENTES (no se enlazan fila↔ficha dentro de este módulo: confirmado con datos reales que
  la relación no siempre es 1:1, un campo compuesto de la grilla puede tener 1 ficha padre + N
  fichas hijas por sub-componente). Clave de emparejamiento: `Position`/`Positions` normalizada.
  **1 bug real de Módulo 2 encontrado explorando datos para diseñar Módulo 3** (antes de escribir
  código de Módulo 3): faltaba un 3er nivel de encabezado de sección (20.0pt, no solo 26.0pt) usado
  cuando una sección grande engloba varios sub-registros anidados con su propia numeración de
  Position independiente -sin reconocerlos como `section_heading`, sus filas/fichas se mezclaban
  bajo la sección grande con posiciones repetidas 6-7 veces. Solo 6 apariciones en la edición de
  referencia, acotado a 1 sección. Arreglado en `normalize.py` (`SECTION_HEADING_FONT_SIZES` como
  conjunto en vez de un único umbral, continuidad de título comparada contra el tamaño exacto de
  cada instancia). Detalle completo, incluida la validación final (contenido real leído, no solo
  conteos: el caso central "Reserved se parte" confirmado en filas Y fichas en paralelo), en
  `NOTES.md`, sección "2026-08-13 (cont.) — Investigación del problema chain-shift + Módulo 3...".
  **Módulo 4 implementado y CERRADO.** `detect.py` diffea 2 listas en paralelo (filas/fichas) sin
  unificarlas, mismo criterio que Módulo 3. Categoría nueva `field_became_defined` (el caso central
  del proyecto) implementada con 2 subtypes: `"split"` (Reserved se parte en campo nuevo + Reserved
  más chico, ya visto en Módulo 3) y **`"renamed_in_place"`** (encontrado leyendo la salida real de
  la primera corrida, no en el diseño: a veces el rango Reserved se renombra ENTERO a un campo real
  sin partirse, mismo rango de posiciones -Módulo 3 ya lo empareja por posición exacta y sin este
  fix quedaba escondido como `row_content_changed`/`card_content_changed` genérico, perdiendo la
  señal central del proyecto). Agregado simétricamente `field_became_reserved` (caso inverso, campo
  real se retira a Reserved). Validación de integridad de conteos en los 8 pares: filas/fichas
  sueltas + las consumidas por cada split reconciliaron EXACTO contra los totales de Módulo 3, sin
  doble conteo ni pérdidas. 2 detalles menores corregidos en el camino (comparación por identidad
  en vez de igualdad para `remaining_reserved`, una línea muerta). Detalle completo en `NOTES.md`,
  sección "2026-08-13 (cont.) — Módulo 4 implementado... con la categoría central del proyecto".
  **Módulo 5 implementado y CERRADO.** `classify.py`, mismo diseño que los otros 2 manuales;
  contexto de nombre de campo resuelto recargando Módulo 3 (`_field_name_lookup`, mismo patrón que
  `title_by_code` del manual 2) sin tocar el esquema ya cerrado de Módulo 4. Corrida completa: 554
  items, `business_rule_change`=301, `editorial_reword`=241, `extraction_noise`=12.
  `safety_net_override` salió mucho más alto de lo normal en 2 de los 8 pares (19 y 33, vs 0-1 en
  corridas previas de otros manuales) -investigado a fondo, NINGUNO es bug de código: (1) par
  `20230415→20231014`, cambio editorial real -Visa reescribió varios campos de "Fleet Service" para
  reemplazar listas de valores enumeradas por una referencia cruzada a otro manual, confirmado en
  el PDF crudo; (2) par `20251018→20260418`, limitación real del PDF fuente de ESA edición
  puntual -el span en negrita que renderiza la palabra "Note:" está directamente ausente de la capa
  de texto extraída en `20260418` (216 apariciones de `"Note:"` vs 272-274 en las otras 8
  ediciones, confirmado contando en las 9 completas), no recuperable sin OCR. Ambos casos: la red
  de seguridad detectó contenido real desaparecido y lo marcó para revisión en vez de perderlo
  silenciosamente -funcionando como debía. Detalle completo en `NOTES.md`, sección "2026-08-13
  (cont.) — Módulo 5 implementado... con 2 patrones de safety_net_override alto investigados".
  **Módulo 7 implementado y CERRADO — PIPELINE COMPLETO (Módulos 1-5, 7) para este manual, mismo
  hito que los otros 2.** `report.py` pone `field_became_defined`/`field_became_reserved` PRIMERO
  en el reporte (el caso de uso central del proyecto, sección propia y prominente), dedupe
  fila/ficha por (título, posición) para no repetir el mismo evento 2 veces. Cambios de contenido
  agrupados por CAMPO (no por fila y ficha por separado), usando `field_name` de Módulo 5.
  Validado leyendo el reporte completo del primer par de punta a punta: hallazgo real nuevo -Visa
  modernizó terminología ("chargeback or representment" → "dispute or dispute response") en
  decenas de campos no relacionados entre sí, correctamente detectado como `business_rule_change`
  en cada instancia. Output en `data/07_reporte_cambios/` (8 reportes + `index.md`). Detalle
  completo en `NOTES.md`, sección "2026-08-13 (cont.) — Módulo 7 implementado... PIPELINE
  COMPLETO".
  **Con esto, los 3 manuales elegidos hasta ahora (Tipo B, Tipo F, Tipo A) tienen pipeline completo
  validado de punta a punta.** Módulo 6 queda deliberadamente salteado/tentativo en los 3.

**ESTADO AL 2026-08-19 (sesión larga, 4 manuales más), para retomar en la próxima sesión:**

- **Manual 4, `base_ii_clearing_interchange_formats_tc_50_to_tc_92`** (hermano directo del
  manual 3, misma serie de documento, TC 50-92 en vez de TC 01-49): **pipeline completo
  (Módulos 1-5 y 7) implementado y validado de punta a punta.** Mismo diseño que el manual 3,
  reusado con ajustes confirmados con datos reales (sin asumir que "mismo tipo de documento"
  implica "mismos quirks" -ej. NO tiene el 3er nivel de encabezado a 20pt que sí tenía el
  manual 3, confirmado buscándolo explícitamente en las 9 ediciones, 0 resultados).
  **Bug real encontrado y arreglado en Módulo 3**: la sección `TC 57 - TCR 5 - Limited Use
  Data` aparece 2 veces con título Y párrafo introductorio idénticos pero 2 layouts de campos
  completamente distintos -un dict simple de emparejamiento por título hubiera perdido una de
  las 2 tablas por colisión de clave (pérdida de datos real, no solo cosmética). Arreglado
  emparejando por orden de aparición dentro del título repetido. La ambigüedad semántica de
  "cuál layout es cuál" sigue sin resolver (item 10 de arriba).
  2 bugs más encontrados leyendo el reporte real de Módulo 5/7 (no en la exploración previa):
  título de ficha filtrándose en la descripción del primer campo (item 11), y una ficha con
  lista `Values:` larga fragmentada en varios `field_card` por salto de página (item 12) -este
  último con un caso HERMANO en la sección "Outgoing ITF" que resultó ser un cambio editorial
  real (no confundir los dos, mismo nombre de campo, causas distintas).
  Módulo 5 sobre las 8 corridas: `business_rule_change`=9, `editorial_reword`=17,
  `safety_net_override`=1 (investigado, cambio editorial real de Visa, no bug). Distintivo de
  este manual: **0 transiciones Reserved→definido** en las 8 ediciones disponibles (a
  diferencia del manual 3) -el mecanismo de emparejamiento funciona igual (confirmado con el
  caso `TC 57`), simplemente los capítulos TC 50-92 no tuvieron ese tipo de cambio en esta
  ventana de ediciones.

- **Manual 5, `base_ii_transactions_quick_reference`**: **pipeline completo (Módulos 1-5 y 7,
  con Módulo 5 como no-op deliberado) implementado y validado.** Manual NUEVO (no hermano de
  ninguno anterior), forma de contenido genuinamente distinta: listado de referencia rápida de
  2 niveles (código TC + lista de filas TCR con descripción), SIN grilla Position/Length/
  Format ni concepto de campo "Reserved".
  **Bug real encontrado y arreglado en la 1ra validación de Módulo 2**: filas TCR que cruzan
  un salto de página se fusionaban en un solo bloque ilegible -el fallback de "hueco mínimo =
  wrap" no chequeaba que las 2 líneas comparadas estuvieran en la misma página (un salto de
  página real da un hueco NEGATIVO que igual pasaba el umbral sin querer). A diferencia de los
  manuales de grilla (que evitan este problema gratis porque el título de tabla se re-declara
  por página), este manual no redeclara nada -el corte de página explícito hizo falta acá.
  **Diseño de Módulo 3 distinto, decidido con evidencia real**: la etiqueta TCR sola no es
  única (`"TCR 0"` se repite 9 veces en una misma sección con 9 descripciones distintas), y el
  fuzzy matching por descripción demostró ser INSEGURO (decenas de pares de filas genuinamente
  distintas con similitud ≥0.85 en datos reales, ej. `"Batch Disposition Code A"` vs `"...R"`
  = 0.958). Clave final: `(TCR, descripción)` compuesta, EXACTA, sin fuzzy -un rename real se
  ve como baja+alta, no como "cambio de contenido" (aceptado deliberadamente, mismo principio
  que el chain-shift del manual 3).
  Módulo 5 se dejó como archivo vacío/no-op por consistencia de estructura del pipeline (no
  hay ninguna categoría de "contenido cambiado" posible dado el diseño de la clave -confirmado
  con el usuario tras una discusión real sobre si hacía falta).
  Módulo 7 diseñado con una vista pedida explícitamente por el usuario: conteo de TCR antes→
  después por TC con el delta, siempre acompañado del detalle de filas agregadas/eliminadas
  (nunca solo el número), con un aviso ⚠️ cuando el delta neto es 0 pero hay altas Y bajas a la
  vez (posible rename no detectado como tal).

- **Manual 6, `international_full_service_pos_online_messages_processing_specifications`**
  (`base_i`): **pipeline completo (Módulos 1-5 y 7) implementado y validado.** 1er manual
  NARRATIVO del proyecto (232 páginas de prosa de reglas de negocio, casi sin tablas de
  campos -confirmado explorando el PDF antes de decidir el enfoque). El usuario eligió
  explícitamente diffear a nivel de párrafo/sección con clasificación IA (`AskUserQuestion`)
  en vez de construir una máquina de tablas para este manual.
  Jerarquía de 3 niveles de encabezado (26/20/14pt) capturada en stream plano (sin árbol
  real). Clave de emparejamiento de secciones: RUTA jerárquica completa (no título suelto),
  porque títulos de nivel 2 se repiten sistemáticamente bajo distintos capítulos padre (ej.
  "Cardholder Transactions" bajo 2 capítulos distintos).
  **Bug real encontrado tras correr Módulo 5 con un `safety_net_override` sospechosamente alto
  (18/124, 14.5%, vs 0-2 normal)**: el mismo párrafo real puede quedar cortado distinto entre
  2 ediciones -una frase corta tipo "intro de lista" a veces queda fusionada al párrafo
  anterior en una edición y separada en la otra, por dónde cae el salto de página (regla de
  paginación "keep with next" del PDF, no un cambio de contenido). Arreglado PARCIALMENTE
  (`_reflow_matches` en Módulo 3, reconcilia el caso simple 2 párrafos↔1) tras confirmar que
  un fix geométrico en Módulo 2 no serviría (el salto de página no siempre cae cerca del
  margen inferior). Mejora real: `safety_net_override` 29→14 en total. El usuario decidió
  explícitamente NO seguir invirtiendo en el residuo N:M más complejo (item 13 de arriba).
  Validado leyendo el reporte más nutrido de punta a punta: hallazgo real, 8 párrafos en 5
  secciones distintas con el mismo renombre de sistema (`"Exception File"` →
  `"Account Screen Authorization File (ASAF)"`), todos clasificados correctamente.

- **Manual 7, `visanet_settlement_service_vss_user_guide_volume_1_specifications`** (`vss`):
  **pipeline completo (Módulos 1-5 y 7) implementado y validado -el manual más complejo del
  proyecto hasta ahora.** Mezcla prosa narrativa (como el manual 6) con 2 tipos de texto
  ROTADO 90° dentro del PDF: volcados de reportes tipo mainframe (descartables, marcados
  explícitamente como datos ficticios) y tablas de referencia real `Field Name`/`Description`
  dentro de exhibits "Example N: Reconciliation of...". El usuario corrigió una hipótesis
  inicial equivocada del asistente a mitad de camino (se pensó que el contenido rotado
  desaparecía en ediciones nuevas -en realidad persiste siempre, solo cambia de empaquetado
  landscape-página-completa a bloque-rotado-en-página-retrato) y eligió explícitamente
  reconstruir los pares de referencia real en vez de descartar todo el contenido rotado.
  Geometría de texto rotado investigada con datos reales antes de programar: los ejes quedan
  transpuestos (fila = mismo `x0`, columna = banda de `y1`, calculada por página, no
  constante global).
  **3 bugs reales encontrados y arreglados en las primeras validaciones**: (1) la misma banda
  de tamaño de fuente rotada también la usaba OTRA tabla totalmente distinta y sí descartable
  -resuelto exigiendo el literal exacto `"Field Name"` (2 palabras) por página, filtro que
  bajó los pares contaminados de 484 a 236; (2) los pares quedaban mal ordenados en el stream
  entero (páginas sin ninguna línea horizontal caían al `order` default 0) -arreglado usando
  el `order` propio de cada línea rotada; (3) un salto real de jerarquía de encabezados
  (`"Related Information"` a nivel 3 directamente bajo nivel 1, sin nivel 2, confirmado en las
  6 ediciones bajo 4 capítulos distintos) -arreglado para tolerar niveles ausentes en la ruta.
  Clave de emparejamiento de pares: `(example_title, name)` compuesta y exacta (mismo
  criterio de "fuzzy inseguro" ya validado en el manual 5, no re-investigado). A diferencia de
  los manuales 5/6, un par SÍ puede tener contenido distinto tras matchear (la clave no
  consume `description`) -Módulo 4 necesitó su propio paso de diff de contenido para pares.
  Investigada una señal alta (39 `pair_content_changed` en un par) antes de validar: 26/39 son
  el residuo YA CONOCIDO de Módulo 2 (descripción vacía en la edición vieja), correctamente
  clasificado como `extraction_noise` por el LLM sin intervención de la red de seguridad.
  Residuo de emparejamiento geométrico de pares aceptado como item 14 de arriba.

**Con esto, los 7 manuales elegidos hasta entonces tenían pipeline completo validado de punta a
punta.** Módulo 6 (Validación con Plataforma STD) sigue deliberadamente salteado/tentativo en
todos.

- **Manual 8, `visanet_settlement_service_vss_user_guide_volume_2_reports`** (`vss`, hermano
  directo del manual 7): **Módulos 1-4 implementados y validados el mismo día que se empezó
  (2026-08-19); Módulo 5 programado pero su batch completo NO se corrió** (el usuario lo
  cortó a los 37/506 ítems para irse a dormir, ver NOTES.md para el detalle completo de la
  sesión). El manual más fragmentado hasta ahora: 5 apéndices, cada uno con una forma de
  contenido distinta, resueltos con UN SOLO reconstructor genérico de tabla N-columnas
  reusado en los 5 (en vez de 5 parsers a medida) -primera vez que este enfoque genérico se
  lleva tan lejos en el proyecto. Módulo 1 separado por apéndice desde el inicio (decisión
  explícita del usuario, a diferencia de los otros 7 manuales). **11 bugs reales encontrados
  y arreglados** durante la validación de Módulos 2-4 (detalle completo en NOTES.md) -el más
  importante: 2 tablas realmente distintas compartiendo una página rotada con encabezados de
  MISMO nombre colapsaban en 1 sola vía colisión de clave de diccionario, afectando ~20-30%
  de las tablas del Apéndice D (datos reales de layout de campos, el caso de uso central del
  proyecto) -arreglado detectando nombres de columna repetidos entre tiers de encabezado como
  la señal de "2 tablas distintas, no una jerarquía grupo/hoja legítima". 0 residuos abiertos
  al cierre de la sesión (2 candidatos a residuo terminaron resolviéndose como efecto
  colateral de fixes posteriores, no quedaron como TODO).
  **Módulo 5 corrido completo (2026-08-20), su salida validada, y Módulo 7 (reporte)
  implementado y corrido el mismo día.** Validando los 31 `safety_net_override` del primer
  batch de Módulo 5 se encontró y arregló un bug real más, el más importante de la sesión:
  el PDF fuente codifica el espacio entre palabras de algunos encabezados de columna/título
  como NBSP (U+00A0) en vez de espacio normal, de forma inconsistente incluso dentro de una
  misma tabla/edición -Módulo 4 (`detect.py`) comparaba nombres de columna por clave de
  diccionario CRUDA (sin normalizar), así que `"Messages and Codes"` vs
  `"Messages\xa0and\xa0Codes"` se veían como 2 columnas distintas, generando pares de diffs
  falsos: uno "contenido desapareció" (atrapado por la red de seguridad, categoría final
  correcta por razón equivocada) y uno "contenido apareció" (NO atrapado por nada, mal
  clasificado en silencio como `business_rule_change` real). Arreglado en la raíz -no en el
  sitio de comparación- agregando `_clean_text()` a Módulo 2 (`normalize.py`), que reemplaza
  NBSP por espacio normal en el texto de cada línea antes de que se use como nombre de
  columna/título. Verificado de punta a punta: Módulos 2→5 re-corridos para las 7 ediciones,
  `safety_net_override` total 31→18, `row_content_changed` total 506→445 (todos los que
  bajaron confirmados como ruido espurio, los casos genuinos se preservaron). 2 bugs más
  encontrados y logueados sin arreglar (items 15/16 arriba) más 1 hallazgo nuevo no
  relacionado al NBSP (item 17 arriba). Detalle completo en `manual8-vss-vol2-progress.md`
  (memoria del asistente).
  Módulo 7 (`07_reporte_cambios/report.py`) sigue el mismo diseño que los demás manuales
  (cambios de negocio primero, altas/bajas estructurales, apéndice de ruido, avisos de
  confiabilidad al final) pero agrupa por `(apéndice, table_title)` en vez de por `path`
  -este manual no tiene jerarquía de secciones única (ver Módulo 3). No tiene sección
  dedicada de transiciones Reserved↔definido (a diferencia del 3er/4to manual) porque Módulo
  4 acá no emite ese `change_type` -las altas/bajas de fila ya muestran el contenido
  completo, alcanza para que un lector la identifique a simple vista. 6 reportes generados
  sin errores, 90/12/47/11/8/9 cambios de negocio a revisar por par.

**Con esto, el pipeline del manual 8 llega hasta Módulo 7 (Módulo 6 sigue tentativo/sin
definir, igual que en los otros 7 manuales). SIGUIENTE PASO: decidir si se retoman los items
15/16/17 (arriba) o se elige el próximo manual.** Manuales restantes sin tocar en `visa/src/`:
`base_i/visanet-authorization_only_online_messages_technical_specifications`
(contiene 2 manuales técnicos mezclados por nombre de archivo en la misma carpeta -"VisaNet
Authorization-Only Online Messages Technical Specifications", 1 edición, y "Full Service POS
Online Messages Technical Specifications", 8 ediciones). Mastercard sigue
vacío (fuera de alcance todavía).

**Sesión también generó consideraciones arquitectónicas para cuando el proyecto pase de POC a
desarrollo real, guardadas en la memoria del asistente (`dev_phase_considerations.md`, NO
replicadas acá en detalle -son notas de proceso/arquitectura, no bugs de un manual puntual):
auditar el riesgo de fusión de bloques en saltos de página en TODOS los manuales (no solo donde
ya se encontró), la seguridad del fuzzy matching es especifica de cada manual/granularidad
(nunca asumir que "funcionó en un manual" = "es seguro en otro"), un gap de sensibilidad de
detección de renombres en el manual 5 (aceptado a proposito), y una pregunta de escalabilidad sin
decidir: parsers a medida por manual (5 formas de contenido distintas hasta ahora) vs. invertir
en un framework más general -para cuando se defina el desarrollo real, no antes.**

## Estado de cierre de sesión (2026-08-20, tarde) — retomar desde acá

Después de terminar el manual 8, el usuario preguntó por la arquitectura de producción (un
único router que identifica el tipo de PDF y despacha a 1 de 8 pipelines completamente bespoke,
sin lógica de negocio compartida -solo infraestructura común: wrapper de Ollama, parseo de
argumentos CLI, esqueleto de reporte Markdown). **Decisión explícita del usuario: cerrar deuda
de bugs conocidos primero, no diseñar el router todavía.** Eligió arrancar por el manual 1
(`base_ii_clearing_data_codes`), el primero construido y el que más tiempo lleva sin revisitar.

**Items 2 y 3 del manual 1 quedaron RESUELTOS y verificados de punta a punta esta sesión**
(Módulos 1→5 y 7 corridos juntos después de ambos fixes, 0 errores, 0 regresiones
estructurales en las 9 ediciones) -ver el detalle completo arriba en sus propias secciones, y
la narrativa día-a-día en NOTES.md.

**Quedan 4 items abiertos del manual 1, ninguno urgente** (ver sus secciones arriba para el
detalle completo):
- **Item 1** (glosario sin parsear): prioridad baja, deprioritizado explícitamente por el
  usuario el 2026-08-12 -no retomar salvo que lo pida.
- **Item 3b** (Zimbabue, mismo bug-clase que el item 3 pero mecanismo distinto): cosmético,
  usuario pidió explícitamente dejarlo anotado para más adelante.
- **Item 4** (evidencia de la red de seguridad poco útil en filas con viñetas): muy baja
  prioridad, cosmético.
- **Item 5** (LLM tipea mal números grandes en `ai_reason`): muy baja prioridad, cosmético,
  nunca afecta los datos `old`/`new` reales mostrados en el reporte.

**SIGUIENTE PASO, a elección del usuario en la próxima sesión**: (a) tomar alguno de los 4 items
restantes del manual 1 (todos de baja prioridad, sin apuro), (b) pasar a otro manual con TODO
pendiente (ver la lista de items 7-14 arriba, y 15-17/manual 8 más abajo), o (c) retomar el
diseño de arquitectura de producción (router + contrato de interfaz entre etapas) que el usuario
planteó y todavía no se empezó a diseñar.

## Estado de cierre de sesión (2026-08-25) — retomar desde acá

El usuario pidió explícitamente tomar los 4 items restantes del manual 1 en esta sesión ("para ir
levantandolo primero"), incluido el item 1 (glosario) pese a estar deprioritizado originalmente.
**Los 4 quedaron cerrados o parcialmente cerrados**:

- **Item 1 (glosario) — RESUELTO completo.** Ver su sección arriba (índice reescrito) y
  `NOTES.md` para el detalle: ~200 entradas término/definición limpias por edición, más un bug
  colateral real encontrado y arreglado en Módulo 3 (tabla huérfana `"(sin titulo)"` que hubiera
  fusionado el glosario con cualquier otra fila huérfana no relacionada del documento).
- **Item 3b (Zimbabue) — PARCIALMENTE RESUELTO.** La variante de nota numerada se arregló (5/7
  ediciones limpias). La variante `"Note:"` de las 2 ediciones más nuevas (`20251018`,
  `20260418`) sigue abierta -se investigó y se descartó deliberadamente una regla genérica por
  romper ~50 notas legítimas en otras partes del documento; hace falta una señal más específica
  (salto de tamaño de fuente hacia la sección siguiente) no disponible hoy en Módulo 2.
- **Items 5 y 6 (Módulo 5, evidencia de viñetas / typos de dígitos del LLM) — RESUELTOS.** El
  item 5 resultó tener más impacto real de lo logueado: 2 falsos positivos genuinos de la red de
  seguridad (códigos `H0`/`HZ`) se corrigieron de `business_rule_change` forzado a
  `editorial_reword` correcto.

**Verificado de punta a punta**: Módulos 1→5 y 7 re-corridos juntos después de los 4 fixes (no
por separado) en las 9 ediciones / 8 pares. 0 errores, 0 regresiones estructurales (Zimbabwe,
glosario, tablas Country/Currency, EDQP siguen íntegras). Módulo 5 completo: 356 items
clasificados (más que la corrida previa de 301 -el glosario ahora aporta items diffeables),
`safety_net_override` total = 9. Módulo 7 regeneró los 8 reportes sin errores.

**Con esto, TODOS los items conocidos del manual 1 están cerrados o documentados con causa raíz
identificada -no queda ningún item "sin investigar" en este manual.** Único residuo abierto:
item 3b en 2 de 9 ediciones (cosmético, no afecta los códigos de Zimbabue en sí).

## Estado de cierre de sesión (2026-08-25, tarde/noche) — retomar desde acá

Después de cerrar el manual 1 (items 1/3b-parcial/5/6), la misma sesión continuó manual por
manual, en orden, cerrando lo pendiente de cada uno:

- **Manual 2** (`base_ii_clearing_edit_package_messages`): glosario resuelto completo
  (reusando vocabulario de ficha `card_header`+`field`, arquitectura de Módulo 2 distinta a la
  del manual 1) + item 7 (V0407) parcialmente resuelto -causa raíz real más precisa que lo
  logueado (`_find_disappeared_content` nunca miraba opcodes `"replace"`, solo `"delete"`),
  fix en la red de seguridad que de paso arregló 2 casos más importantes que el original
  (ficha V1209, glosario `optional issuer fee`). V0407 en sí sigue sin arreglar (3 palabras,
  bajo el umbral de 5) -mismo veredicto de siempre, cosmético.
- **Manual 3** (`base_ii_clearing_interchange_formats_tc_01_to_tc_49`): NO se tocó código. Se
  aclaró que el item 8 (chain-shift) SÍ es arreglable (decisión de alcance, no limitación
  técnica) pero el usuario pidió posponerlo ("anotalo para ver más adelante"); el item 9
  (etiquetas "Note:" faltantes en `20260418`) se confirmó NO arreglable sin OCR.
- **Manual 4** (`base_ii_clearing_interchange_formats_tc_50_to_tc_92`): los 3 items pendientes
  (10/11/12) resueltos o parcialmente resueltos -ver sus secciones arriba. Pipeline completo
  re-validado.
- **Manual 5** (`base_ii_transactions_quick_reference`): confirmado que NO tiene ningún item
  pendiente logueado -pipeline cerrado limpio desde su implementación original, nada que hacer.
- **Manual 6** (`international_full_service_pos_online_messages_processing_specifications`):
  item 13 generalizado de 2:1 a N:M real (ver su sección arriba) -resuelto para este manual.

**Items abiertos que quedan, por manual, para retomar en la próxima sesión**:
- Manual 1: item 3b residual (2 de 9 ediciones, cosmético).
- Manual 2: item 7 residual (ficha V0407, cosmético).
- Manual 3: item 8 (chain-shift, pospuesto explícitamente por el usuario, arreglable si se
  pide) + item 9 (no arreglable sin OCR).
- Manual 4: item 10 residual (etiqueta desambiguadora sin significado de negocio propio).
- **Manual 7** (`visanet_settlement_service_vss_user_guide_volume_1_specifications`): **NO
  tocado esta sesión.** Tiene su propia variante del item 13 (nombre+descripción fusionados en
  un campo `name` de un par Field Name/Description, distinto al reflow de párrafo narrativo
  del manual 6 -mismo síntoma raíz, mecanismo probablemente distinto, necesita su propia
  investigación antes de decidir si el fix de `SequenceMatcher` a nivel de párrafo del manual 6
  aplica tal cual o hace falta adaptarlo) + item 14 (residuo de emparejamiento geométrico de
  pares rotados, ~35-45% con descripción vacía, aceptado como diminishing returns).
- **Manual 8** (`visanet_settlement_service_vss_user_guide_volume_2_reports`): **NO tocado esta
  sesión.** Items 15 (descripción pegada al Field Name anterior, Apéndice B), 16 (filas de
  `Available VSS Reports` partidas por salto de página, Apéndice A, misma familia que el item
  13/manual 6/7 -page-reflow, pero en tabla no en párrafo narrativo), 17 (título "TC R" partido
  en 2 palabras, Apéndice B) -ver sus secciones en `manual8-vss-vol2-progress.md` (memoria del
  asistente) para el detalle completo, no repetido acá.

**Pedido explícito del usuario para la próxima sesión: arrancar por el manual 7, después el
manual 8** (en ese orden) -pausa acá, sin tocar más código esta sesión.

**SIGUIENTE PASO**: (a) manual 7 (item 13 propio + item 14), (b) manual 8 (items 15/16/17), o
después de esos 2, retomar los residuos pendientes (item 3b/manual 1, item 7/manual 2, item
8/manual 3, item 10/manual 4) o el diseño de arquitectura de producción (router + contrato de
interfaz) que sigue sin arrancar desde el 2026-08-20.

## Estado de cierre de sesión (2026-08-26) — retomar desde acá

Sesión nueva, se siguió el orden pedido: manual 7 primero. **Item 13 propio del manual 7
RESUELTO** -ver su sección reescrita (item 14 arriba) y `NOTES.md` ("2026-08-26 — Manual 7,
item 13/14") para el detalle completo: fusión nombre+descripción en pares rotados era el mismo
mecanismo que Cook Islands (manual 1, item 2), portado a líneas rotadas únicamente. 8-9 casos
reales por edición arreglados, 236 pares sin cambio, 0 regresión en Módulos 3→5,7 (re-corridos
completos en las 6 ediciones/5 pares). El residuo restante del item 14 (wrap-a-2da-banda-de-x0
+ sub-encabezados `Row`/`Column` legítimos) sigue abierto, deliberadamente no perseguido -ver
la sección del item 14 para la causa raíz más precisa encontrada, distinta a la ya resuelta.

**Manual 8 NO se tocó todavía esta sesión** -sigue siendo el siguiente paso pedido por el
usuario (items 15/16/17, ver sus secciones arriba).

**SIGUIENTE PASO**: manual 8 (items 15/16/17), o después, los residuos pendientes de baja
prioridad (item 3b/manual 1, item 7/manual 2, item 8/manual 3, item 10/manual 4, item 14
residual/manual 7) o el diseño de arquitectura de producción (router + contrato de interfaz)
que sigue sin arrancar desde el 2026-08-20.

## Módulo 8 — Reporte web consolidado (nuevo, construido 2026-08-27)

No es un bug fix, es una pieza nueva del pipeline: `poc/08_reporte_web_consolidado/`. El usuario
pidió una mini-web local con pestañas para no tener que abrir 8 `.md` sueltos (uno por manual)
cada vez que quiere ver el estado del último par de ediciones. Ver detalle completo (evidencia,
decisiones de diseño, verificación) en `NOTES.md`, entrada "2026-08-27 — Módulo 8: reporte web
consolidado". Resumen accionable:

- **Antes de escribir código** se leyeron los 8 `07_reporte_cambios/report.py` completos y se
  confirmó que los 8 manuales NO comparten un esquema real de Módulo 5 (distintos `change_type`,
  distintos campos identificadores, distintas claves de agrupamiento; `base_ii_transactions_
  quick_reference` ni siquiera tiene `ai_category`). Por eso Módulo 8 son 7 adaptadores bespoke
  (`adapters/`, uno compartido entre los 2 manuales de grilla que sí son idénticos), no un parser
  genérico -mismo espíritu que el resto del pipeline.
- `build.py` (sin dependencias nuevas) lee el último par de cada manual, arma un JSON normalizado
  y genera `data/index.html` -autocontenido, JSON embebido en base64 inline, sin `fetch()`/
  servidor, abre con doble-click- + `data/reporte_consolidado.json` (intermedio, debug).
- Verificado: las 8 cuentas de "cambios de negocio a revisar" del HTML coinciden exactamente con
  los `index.md` ya existentes; Bulgaria/Croacia (manual 1) se ven completos; el manual sin
  `ai_category` muestra su propia métrica de TCR en vez de una sección rota; las transiciones
  Reserved↔definido (caso de uso central del proyecto) aparecen primero en los 2 manuales de
  grilla.
- Regenerar con `python3 poc/08_reporte_web_consolidado/build.py` cuando haya ediciones nuevas.
- No cubre (fuera de alcance, decisión explícita con el usuario): selector de pares históricos
  por pestaña (solo el último par), y no tiene relación con el diseño de router de producción
  pendiente desde el 2026-08-20 (líneas arriba) -es tooling de POC sobre la salida de Módulo 7,
  no la arquitectura real.

**SIGUIENTE PASO sigue siendo el mismo que antes de este agregado**: manual 8 (items 15/16/17) si
se retoma esa vía, o los residuos de baja prioridad, o el diseño de router de producción.

## 18. RESUELTO (2026-09-05) — Fila de Apéndice D misatribuida por empaquetado apretado (manual 8)

- **Dónde**: `visanet_settlement_service_vss_user_guide_volume_2_reports`, Módulo 2
  (`normalize.py`), tablas de Apéndice D con filas muy apretadas verticalmente.
- **Alcance real MUCHO más chico de lo estimado originalmente** (se había logueado
  ~150-170 de ~1550 `grid_row` afectadas en la edición más nueva) — esa estimación estaba
  desactualizada, medida antes de un fix de una sesión anterior (item 16 abajo) que ya la había
  reducido sin que nadie la re-midiera. Re-medido con un escaneo real 2026-09-05: confinado a
  las 3 ediciones más viejas.
- **2 variantes, 2 fixes**: (a) sub-viñetas con guion literal "– " — `_merge_dash_orphan_rows`,
  fila cuya celda ancla arranca con guion y el resto de columnas vacías se fusiona con la fila
  anterior; validado que ninguna de las 119 filas de nota al pie legítimas del corpus arranca
  con guion. (b) sub-viñetas con viñeta redonda "•" — investigado primero como si necesitara un
  cambio en Módulo 1 (conclusión INICIAL INCORRECTA, corregida en la misma sesión): la viñeta
  en realidad SÍ se captura bien en Módulo 1 (`text="l"`, fuente Wingdings — el truco clásico de
  PDFs generados por Word), el problema era que Módulo 2 la descartaba como bloque huérfano sin
  clasificar. Geometría contraintuitiva: la viñeta va DESPUÉS del texto asociado (~4-6.4pt), no
  antes como el guion. Señal ciega ("cualquier viñeta Wingdings cerca") era insegura -14 casos
  reales en Apéndice A donde una viñeta legítima coincide cerca de un salto de tabla grande- se
  arregló exigiendo también un hueco chico (`BULLET_SUPPRESS_GAP_MAX=10.0`; el bug real siempre
  mide exactamente 7.0pt, las coincidencias legítimas de Apéndice A miden 174.5pt+).
- **Verificado**: 0 filas huérfanas de guion/viñeta restantes en las 7 ediciones, 0 efecto
  colateral en Apéndices A/B/C/E, 0 cambio en los conteos de fila/bloque de Apéndice A. 1
  residuo pequeño aceptado (V22240, un par cuya transición entre 2 fragmentos internamente
  consistentes no tiene ni guion ni viñeta que la marque — ver la sección de investigaciones
  cerradas más abajo).
- Ref: memoria del asistente, `pending_bug_fixes.md` item 15; `manual8-vss-vol2-progress.md`.

## 19. RESUELTO (2026-08-19, mismo día del hallazgo) — Fila de tabla pegada al título de la tabla siguiente por enrutado de dirección invertido (manual 8)

- **Dónde**: `visanet_settlement_service_vss_user_guide_volume_2_reports`, Módulo 3, filas de
  cola de una tabla que sigue en una página de continuación sin re-declarar el encabezado.
- Compartía causa raíz con un bug distinto encontrado validando Módulo 4 (líneas de título
  enrutadas con la dirección invertida) — arreglar la dirección de ese enrutado resolvió esto
  como efecto colateral. Verificado: 0 mezclas cross-record en 52 matches fuzzy totales
  (antes: 2 de 51).
- Ref: `manual8-vss-vol2-progress.md`.

## 20. RESUELTO (2026-08-20) — NBSP rompe el diffing por nombre de columna (manual 8, Apéndice E)

- **Dónde**: `visanet_settlement_service_vss_user_guide_volume_2_reports`, Módulo 4, texto de
  encabezado de columna con espacio NBSP (U+00A0) en vez de espacio normal.
- Rompía el emparejamiento por nombre de columna, produciendo 15 de 31 `safety_net_override`
  falsos positivos (más un número desconocido de `business_rule_change` falsos positivos que
  nunca llegaban a la lista de overrides — la contraparte "columna apareció" del mismo bug).
  Fix en la raíz: `_clean_text` en `normalize.py` reemplaza el NBSP antes de que se convierta
  en nombre de columna/tabla. Verificado: Módulos 2→5 re-corridos en las 7 ediciones,
  `safety_net_override` 31→18, `row_content_changed` 506→445, ningún caso genuino perdido.
- Ref: `manual8-vss-vol2-progress.md`.

## 21. RESUELTO (2026-09-04) — Tier 1: extracción a `poc/_shared/` + fix real de "replace opcode" nunca portado a 5 de 7 manuales

- **Contexto**: al pasar de POC a desarrollo real, se hizo un inventario de duplicación real
  (no intuición) entre los 48 scripts de etapa de los 8 manuales (~13,144 líneas). Resultado en
  3 niveles: Tier 1 (100% mecánico, cero riesgo) = `main()` de Módulos 1 y 4 byte-idénticos en
  7 de 8 manuales, más el cliente HTTP de Ollama casi idéntico en los 7 manuales con IA; Tier 2
  (el argumento real para consolidar) = `_find_disappeared_content` (red de seguridad de
  Módulo 5) tenía la misma lógica copiada 7 veces, y 2 fixes de corrección reales cada uno
  había aterrizado en solo UNA de las 7 copias sin portarse a las demás; Tier 3 (genuinamente
  bespoke, confirmado NO consolidar) = Módulo 2/3 de cada manual, 102-727 líneas según manual,
  tamaños que por sí solos confirman que no es boilerplate disfrazado.
- **Hallazgo real, corrigiendo una afirmación previa de la memoria que resultó FALSA**: se
  creía (memoria del 2026-09-03) que el fix de "replace opcode" (contar `tag in
  ("delete","replace")`, no solo `"delete"`, en el diff de texto) ya estaba portado a todos los
  manuales con IA. Re-verificado contra el código REAL (no confiando en la nota anterior): solo
  2 de 7 lo tenían de verdad (`base_ii_clearing_data_codes`,
  `base_ii_clearing_edit_package_messages`) — los otros 5
  (`..._tc_01_to_tc_49`, `..._tc_50_to_tc_92`, `international_full_service_pos...`,
  `visanet...volume_1`, `visanet...volume_2`) seguían solo mirando `"delete"`, un bug de
  correctitud activo, no histórico: un párrafo/fila cuyo texto se REEMPLAZA por texto no
  relacionado (no solo se borra) pasaba invisible a la red de seguridad en esos 5 manuales.
- **Fix, consolidación en vez de portear a mano una 3ra/4ta/5ta/6ta/7ma vez** (el mismo patrón
  de fallo que dejó pasar el gap desapercibido dos veces): `poc/_shared/stage_runners.py`
  (`run_ingest_main`/`run_detect_main`, cuerpo de `main()` de Módulos 1/4 en 7 de 8 manuales —
  `visanet...volume_2` sigue bespoke, su propio schema por apéndice) y
  `poc/_shared/ollama_client.py` (`ollama_classify`, `ensure_ollama_running`,
  `find_disappeared_content` — con el fix de replace/delete incluido, usado por los 7 manuales
  con IA). Import vía `sys.path.insert` a `Path(__file__).resolve().parents[2] / "_shared"`,
  nunca CWD. Cada `classify.py` sigue armando su propio prompt (bespoke a propósito).
- **Medido antes de gastar Ollama**: 14 casos concretos que pasan de `editorial_reword` a
  `business_rule_change` forzado bajo la lógica corregida, en los 5 manuales previamente
  afectados. Verificado con Ollama real (no `--skip-ai`) en un par barato por manual: los 7
  clasifican limpio, los overrides nuevos son legítimos (marca ⚠️ en el reporte).
  **Efecto colateral encontrado validando (no introducido por este cambio)**: no-determinismo
  de orden real en Módulo 3 de `visanet...volume_1`/`volume_2` — ver item 22.
- **Auditoría relacionada, hecha la misma semana, verdicto "nada que consolidar"**: utilidades
  de bajo nivel de extracción (`_split_line_segments` y afines) — solo 3 de 8 manuales las
  tienen, 1 diferencia real de código entre las 3 copias (un `or [spans]` de respaldo faltante
  en el original) resultó PROVISTAMENTE inerte en los 3 manuales (corrida contra el corpus real
  de cada uno, 0 diferencia observable en el JSON final) — no se tocó nada.
- Ref: memoria del asistente, `dev-phase-considerations.md` punto 4; `pending-bug-fixes.md`
  item 21; `router-landing-progress.md` (writeup de `CONTRACT.md`).

## 22. RESUELTO (2026-09-05, extendido 2026-09-06) — No-determinismo de orden en Módulo 3 + optimalidad greedy (VSS Volumen 1 y 2)

- **Hallazgo, efecto colateral de validar el item 21, no relacionado a ese cambio**: correr el
  mismo `match.py` sin cambios 2 veces seguidas sobre el mismo input daba listas de párrafos/
  tablas/encabezados matcheados en ORDEN DISTINTO cada vez — 4 funciones en los 2 manuales
  iteran `set(dict_a) | set(dict_b)` directo hacia una lista de salida sin ordenar al final
  (dependencia de `PYTHONHASHSEED`, orden de iteración de `set()` no determinístico entre
  procesos). Funciones hermanas en los mismos archivos ya terminaban con `sorted(...)`, por eso
  solo algunas funciones por archivo estaban afectadas.
- **Fix determinismo (2026-09-05)**: ordenar la FUENTE de iteración (`sorted(set(a)|set(b))`),
  no solo el resultado final. Verificado: salida byte-idéntica entre corridas repetidas.
  **Hallazgo real al verificar, no cosmético**: en 1 sección de 1 par
  (`visanet...volume_1`, `20230415→20231013`, "Reporting Options Worksheet") el orden
  pre-fix, arbitrario, había estado eligiendo por casualidad un emparejamiento fuzzy DISTINTO
  (0.996 de similitud) al que da el orden ahora determinístico (0.907) — ambos superan el
  umbral de seguridad, pero esto confirma que el bug podía afectar CUÁL emparejamiento gana en
  casos de empate cercano, no solo el orden de la lista.
- **Extendido (2026-09-06, a pedido del usuario)**: la etapa de matching fuzzy en sí es GREEDY
  (cada elemento sin matchear reclama su mejor candidato disponible en el orden en que se
  procesa, sacándolo de la bolsa para el siguiente) — estable ahora, pero no necesariamente
  óptimo globalmente. Grepeando el mismo patrón (`best_ratio`/`best_idx`) en los 2 manuales se
  encontraron 4 funciones afectadas, no 2 como se pensaba inicialmente
  (`match_sections`/`match_paragraphs` en Volumen 1; `match_tables`/`match_headings` en
  Volumen 2). Fix: recolectar todos los candidatos `(ratio, a, b)` sobre el umbral, ordenar
  descendente por ratio, asignar greedy en ESE orden (los pares de mayor confianza reclaman
  primero) — remueve la dependencia del orden de procesamiento por completo, no solo lo
  estabiliza. Verificado: el único caso ya conocido (arriba) ahora da SIEMPRE la pareja de
  mayor confianza (0.996 en vez de alternar 0.996/0.907); los otros 10 pares de ambos manuales
  quedaron byte-idénticos (normalizados por orden). Re-corrida Módulo 5 del par afectado con
  Ollama real para mantener los datos en disco consistentes.
- Ref: memoria del asistente, `dev-phase-considerations.md` punto 9; `pending-bug-fixes.md`
  item 22.

## Router de producción (`poc/router/`) — construido y feature-complete (2026-09-03 a 2026-09-05)

El diseño de arquitectura de producción que quedaba pendiente desde el 2026-08-20 (líneas
arriba) por fin se construyó. Resumen accionable — el detalle completo con toda la evidencia
vive en la memoria del asistente, `router-landing-progress.md`, y en `poc/router/CONTRACT.md`
(la referencia técnica autoritativa y actualizada, léase esa antes que esto):

- **`run.py`** — orquestador delgado. Hallazgo clave que dio forma al diseño: los 48 entry
  points (8 manuales × 6 etapas) ya cumplían un contrato de facto sin haber sido diseñado a
  propósito (mismo patrón de carpetas `NN_<nombre>/`, invocación sin argumentos posicionales,
  rutas resueltas vía `Path(__file__)`) — el router descubre etapas por glob, no las hardcodea.
  `python3 run.py <slug|all> [--from NN] [--to NN] [--skip-ai] [--only PAR] [--limit N] [--list]`.
- **`land.py` + `detect_type.py`** — landing de PDFs nuevos. Detecta a qué manual pertenece un
  PDF por nombre de archivo (respaldo: texto de portada) usando contención de subconjunto de
  palabras normalizadas (no igualdad exacta ni substring ordenado — 2 contraejemplos reales
  encontrados validando: "International" al principio del nombre de archivo real vs. al final
  del título registrado; un sufijo extra sin registrar). **Bug real encontrado por el usuario
  en la primera corrida end-to-end con Ollama real, no por el asistente**: `land.py` re-
  clasificaba con IA el historial COMPLETO de pares del manual en cada landing (5º argumento
  `only` hardcodeado a `None`), en vez de acotarse solo al par recién llegado — arreglado en
  una línea (`only=f"{fecha_vieja}_to_{fecha_nueva}"`), 10-100x menos llamadas a Ollama por
  landing futuro.
- **Multi-par (2026-09-06)**: el inbox ya no exige exactamente 2 PDFs — agrupa por tipo
  detectado, valida cada grupo, todo-o-nada sobre el LOTE completo (decisión explícita del
  usuario, preguntada antes de implementar: prefirió consistencia con el resto del proyecto
  sobre comodidad operacional de procesar los grupos válidos y alertar solo los malos).
- **Edición única (2026-09-05)**: un grupo también puede tener 1 solo PDF — la edición vieja se
  resuelve automáticamente contra la más reciente ya presente en el corpus
  (`_latest_corpus_edition`), siempre que exista al menos 1 edición previa y la nueva sea
  estrictamente posterior. Verificado con datos reales no destructivos: camino de rechazo
  (misma fecha que la del corpus) y camino feliz (fecha ficticia posterior, pipeline completo
  corrido end-to-end, 0 diffs reales ya que era contenido idéntico bajo fecha distinta).
- **`poc/_shared/`** (ver item 21) también nació de este trabajo de paso a desarrollo real.
- **Fuera de alcance, decisión explícita, no descuido**: consolidación de la capa de reportes
  (ver auditoría abajo — se investigó y se decidió dejarla como está).

## Módulo 8 — pestaña "Cambios recientes" (2026-09-05)

El usuario propuso un modelo de 2 fases (fase 1 = aterrizar pares las veces que haga falta;
fase 2 = generar la web de "anuncio" al final del día). La fase 1 ya funcionaba como se
describía (cada manual muestra solo su último par comparado, sin acumulación histórica). Para
la fase 2, en vez de reordenar la pestaña "Resumen general", se agregó una pestaña NUEVA,
dedicada, para no tocar el comportamiento ya validado de las pestañas existentes:

- `build.py` persiste `data/estado_publicacion.json` (por manual: `edition_a`/`edition_b` del
  último par publicado) y marca cada manual con `is_new_since_last_publish` comparando contra
  ese estado — **cada corrida de `build.py` ES el evento de "publicación"**, no hay un paso de
  publicar separado. Primera corrida (sin estado previo) marca los 8 manuales como nuevos.
- `template.html`: nueva pestaña "Cambios recientes (N)", ahora la que se abre por defecto,
  muestra el detalle completo (no solo compacto) de únicamente los manuales marcados, con un
  estado vacío ("ningún manual nuevo") cuando corresponde.
- Verificado: primera corrida 8/8 nuevos, corrida idéntica siguiente 0/8, prueba con estado
  desactualizado simulado aisló exactamente 1/8 correctamente antes de autocorregirse en la
  corrida siguiente.
- Ref: memoria del asistente, `module8-web-report.md`.

## Auditoría: consolidación de la capa de reportes del router (2026-09-05) — decisión: dejar como está

Se retomó este ítem explícitamente diferido del diseño del router (Tier 3 nunca auditado). Se
midió antes de proponer nada:

- **Módulo 8 (adaptadores) ya estaba consolidado** desde que se construyó (`adapters/_common.py`
  compartido por los 7, los 2 manuales de grilla ya comparten un solo adaptador) — el "no
  auditado" de la nota original era en sí mismo un malentendido, ya estaba hecho.
- **Módulo 7 (`report.py`, 8 manuales)**: 3 fragmentos byte-idénticos confirmados por hash
  (`_fmt_date`, el chequeo de glob+exit-si-vacío, el armado de `index.md`) — ~60-70 de ~2300
  líneas totales (~3%). El resto (`main()` de cada uno, todas las funciones `_render_*`) es
  genuinamente bespoke — cada manual agrupa por una clave distinta, usa vocabulario distinto,
  algunos necesitan un lookup lateral que otros no. Mismo patrón ya documentado para `main()`
  de `classify.py` (misma forma, contenido genuinamente distinto, nunca extraído).
  **Diferencia clave con la ronda del item 21**: ahí la extracción se justificaba por
  duplicación REAL Y un bug escondido (el fix de replace opcode). Acá no hay ningún bug
  escondido en la duplicación — es mecánica pura, sin payoff de corrección.
  Único hallazgo colateral, cosmético (no arreglado): el texto del flag ⚠️ de
  `safety_net_override` tiene 2 redacciones distintas entre manuales, sin efecto en el
  comportamiento.
- **Decisión del usuario, presentada la evidencia**: dejar el Módulo 7 como está — el churn de
  tocar 8 archivos por un ahorro chico no se justifica sin un bug detrás.
- Ref: memoria del asistente, `router-landing-progress.md`.

## Manual 6 — párrafo truncado a mitad de palabra, investigado y dejado como está (2026-09-05)

Un hallazgo de una sesión anterior (`"VSDC PIN Management Service"`, logueado como "necesita su
propia investigación de Módulo 1/2 si se retoma") se investigó a fondo a pedido del usuario:

- **Confirmado que NO es un bug de Módulo 1/2** — se leyeron los spans crudos del PDF fuente
  real directamente con `fitz`: los 2 fragmentos (`"...in Fie"` / `"ld 52 52—Personal..."`) son
  genuinamente 2 spans separados EN EL PDF MISMO, con el "52" duplicado de verdad en el origen
  -un defecto real del lado de Visa (posiblemente un campo de referencia cruzada de Word mal
  actualizado), no algo recuperable en el parser.
- **Alcance real, medido escaneando las 8 ediciones completas** buscando el mismo patrón
  geométrico (líneas en la misma banda Y, hueco horizontal chico) y descartando marcadores de
  lista numerada y encabezados de tabla de 2 columnas (misma forma geométrica, pero benignos):
  ~5 casos genuinos de partición a mitad de palabra por edición, pero SOLO en las 3 ediciones
  más viejas (`20230415`, `20231015`, `20240415`) — CERO en las 4 ediciones más nuevas
  (`20241021` en adelante). El proceso de generación de PDF de Visa cambió en algún momento y
  este defecto dejó de repetirse.
- **Por qué no se justifica arreglarlo**: `paragraph_added`/`paragraph_removed` nunca pasan por
  clasificación de IA en este manual (estructurales, se muestran tal cual) -nunca produce una
  clasificación de negocio incorrecta, solo fragmentos extra cosméticos en la sección "Párrafos
  agregados/eliminados" del reporte, y solo para 3 pares ya históricos.
- **Decisión del usuario**: dejarlo como está, sin implementar ninguna mitigación.
- Ref: memoria del asistente, `dev-phase-considerations.md` punto 8 (nota actualizada).

## README del proyecto (2026-09-05)

Se escribió `poc/README.md` a pedido del usuario — documentación de cómo funciona la
aplicación completa (no un bug fix ni una feature nueva). Cubre: arquitectura general (diagrama
de las 6 etapas + las 2 capas encima), los 8 manuales soportados, requisitos previos (Python,
PyMuPDF, Ollama con `qwen3:4b`), 9 escenarios de uso reales (par clásico, edición única,
multi-manual el mismo día, forzar tipo con `--manual`, re-procesar sin landing, generar el
reporte web, correr sin IA, acotar la IA a un par/límite, PDF no reconocido), el `--help`
completo de `run.py`/`land.py`/`build.py` con ejemplos, un paso a paso operacional del día a
día, un mapa de dónde queda cada archivo/carpeta, y una sección de puntos importantes (todo-o-
nada en landing, edición única necesita historial previo, `build.py` no es incremental, el
esquema bespoke por manual es intencional, no hay "deshacer" un landing, cómo se agregaría un
9° manual). Todo el contenido se verificó contra el `--help` real de cada script y contra
`CONTRACT.md` antes de escribirse -nada por memoria/supuesto.

## Estado de cierre de sesión (2026-09-05/06) — proyecto feature-complete

Sesión extendida que cerró TODO lo que quedaba pendiente desde el 2026-08-27 (última
actualización de este archivo) hasta hoy: el diseño de router de producción completo
(orquestación + landing + multi-par + edición única), la migración POC→desarrollo (extracción
Tier 1 a `poc/_shared/`, con el bug real de "replace opcode" cerrado de una vez por todas para
los 7 manuales con IA), el módulo 8 con su pestaña de "Cambios recientes", y el cierre de TODOS
los residuos cosméticos que quedaban abiertos por manual (items 3b/manual 1, 7/manual 2, 8/
manual 3 en su forma de ficha, 10/manual 4).

**Único item que sigue genuinamente abierto en todo el proyecto**: item 9 (etiquetas "Note:"
faltantes en 1 edición del manual 3, necesita OCR) — anotado explícitamente por el usuario como
mejora futura, categoría de esfuerzo distinta (infraestructura nueva) al resto de esta lista.

**Decisiones tomadas, no pendientes**: un 9° manual técnico de BASE I (existe, es viable, el
usuario confirmó que no hace falta agregarlo); consolidación de la capa de reportes del router
(auditada, se decidió dejarla como está); el párrafo truncado del manual 6 (investigado,
confinado a 3 pares históricos, se decidió dejarlo como está). Módulo 6 (Validación con
Plataforma STD) sigue fuera de alcance en los 8 manuales, sin cambios desde el diseño original
del proyecto.

**SIGUIENTE PASO**: no queda ningún trabajo pendiente activo. Si se retoma el proyecto más
adelante, las únicas líneas abiertas son (a) el item 9 si se justifica agregar OCR, o (b)
cualquier necesidad nueva que surja una vez que el sistema esté en uso real (ver `poc/README.md`
para el manual operativo completo).

## 23. IDEA DIFERIDA (anotada 2026-09-09, no es un bug) — Instrumentar consumo de tokens en la etapa 05 (IA)

Repasando los escenarios de uso del README con el usuario y estimando cuánto tardaría aterrizar
una edición nueva, surgió la pregunta de si se puede saber cuántos tokens consume `qwen3:4b` por
clasificación — útil como dato para presentar el proyecto, y relevante si en algún momento se
evalúa migrar la etapa 05 a un modelo cloud (Gemini vía OpenRouter, charlado en la misma sesión —
ahí sí importaría el conteo real porque se factura por token, además del punto de confidencialidad
de contenido propietario de Visa/Mastercard que también se dejó anotado).

**Confirmado**: la respuesta de `/api/generate` de Ollama YA trae `prompt_eval_count` (tokens de
entrada) y `eval_count` (tokens de salida) por cada llamada — `poc/_shared/ollama_client.py`
(función `ollama_classify`) hoy solo lee `body["response"]` y descarta el resto.

**Medición real** (no estimada): se armó a mano el prompt real de 1 ítem pendiente del par
`20251018_to_20260418` de `base_ii_clearing_interchange_formats_tc_01_to_tc_49`
(`row_content_changed`/`card_content_changed`) y se llamó a Ollama directo para inspeccionar la
respuesta completa: **306 tokens de prompt + 49 de respuesta = 355 tokens para ese ítem**.
Proyectado sobre el par completo (193 ítems pendientes de clasificar en ese mismo par): **~65.000-
70.000 tokens totales** (varía según cuánto texto viejo/nuevo tenga cada cambio puntual).

**Usuario pidió explícitamente NO implementarlo todavía** — solo dejar anotada la idea y el dato
medido. Si se retoma: agregar los 2 contadores al dict que devuelve `ollama_classify()` en
`ollama_client.py` (cambio chico, mismo archivo ya identificado para el split de
`estado_publicacion`, ver README/NOTES.md 2026-09-09), y que cada `classify.py` acumule y reporte
un total por par (línea de consola y/o campo `token_usage` en el JSON de la etapa 05).

## 24. HECHO (2026-09-10) — Prueba real Qwen vs Gemini (OpenRouter) en la etapa 05, NO es una migración

Continuación directa del item 23 (ahí se había anotado la idea de mover la etapa 05 a un modelo
cloud). El usuario pidió probar Gemini de verdad y poder volver a Qwen sin fricción.

**Implementado**: toggle `LLM_BACKEND` (env var, default `"ollama"`) en `poc/_shared/ollama_client.py`.
Con `LLM_BACKEND=openrouter` + `OPENROUTER_API_KEY` seteadas, `ensure_ollama_running()` y
`ollama_classify()` despachan a `google/gemini-2.5-flash-lite` vía OpenRouter en vez de a Ollama
local. **Cero cambios en los 7 `classify.py`** — importan esas 2 funciones por nombre, no les
importa qué backend responde atrás. Sin las variables seteadas, comportamiento idéntico a siempre.

**Bug real encontrado y arreglado en la prueba**: la primera corrida completa falló en el item
16/193 con `json.decoder.JSONDecodeError: Unterminated string` — la respuesta de OpenRouter/Gemini
se cortó a mitad de un JSON en un ítem de texto largo (ficha con `old`=419 chars, `new`=2354 chars).
Reproducir el mismo prompt a mano funcionó limpio, así que parece más un corte transitorio de red
que un techo de longitud real. Como `classify.py` solo escribe el archivo de salida al final del
loop completo, la corrida fallida NO dejó nada a medio escribir (confirmado por `md5sum` — el JSON
oficial del par quedó exactamente igual que antes de la prueba). **Fix**: agregado `max_tokens: 600`
explícito + reintentos con backoff (hasta 3 intentos) a `_openrouter_classify()` únicamente — el
path de Ollama local no lo necesita (no tiene fallas transitorias de red). Segunda corrida: 0 errores.

**Comparación real completa**: par `20251018_to_20260418` de
`base_ii_clearing_interchange_formats_tc_01_to_tc_49`, los mismos 193 cambios de contenido, mismo
prompt, ambos backends.

- **Acuerdo: 84.5% (163/193)**.
- Matriz de confusión (fila=Qwen, columna=Gemini): editorial/editorial=87, business/business=72,
  **business→editorial=18** (el caso que importa — Gemini degrada cambios de negocio reales a solo
  redacción), editorial→business=7, editorial→noise=3, noise→editorial=1, business→noise=1.
- `safety_net_override`: Qwen 38, Gemini 43 — Gemini necesitó más veces que la red de seguridad
  determinística lo corrigiera.
- **Ejemplo concreto verificado en el JSON crudo**: ficha `TC 05 - TCR 0`, posición `133-136`
  (Merchant Category Code), campo `note`. El texto viejo es una nota de negocio real que desaparece
  sin reemplazo. Gemini la clasificó primero como `extraction_noise` (razonó "el texto nuevo está
  vacío, así que el viejo debía ser un artefacto de extracción de PDF" — mal) — la red de seguridad
  (`find_disappeared_content`) la corrigió a `business_rule_change` (`ai_original_category` en el
  JSON confirma el valor original). Qwen la clasificó bien de entrada, sin necesitar el override.

**Estado del proyecto restaurado y verificado**: copié aparte el JSON/reporte de Qwen antes de
correr Gemini, y después de la prueba restauré el JSON original y regeneré la etapa 07 — `md5sum`
confirma que tanto `data/05_interpretacion_cambios_ia/20251018_to_20260418.json` como
`data/07_reporte_cambios/20251018_to_20260418.md` quedaron byte-idénticos a como estaban antes de
tocar nada. El toggle existe en el código pero está inerte salvo que alguien setee
`LLM_BACKEND=openrouter` explícitamente.

**Nota de seguridad**: el usuario pegó su API key real de OpenRouter directo en el chat en vez de
correr el comando él mismo — se le avisó en el momento y se le pidió revocarla/rotarla en
openrouter.ai/keys (el asistente no tiene forma de revocarla directamente, eso requiere acceso al
dashboard o una Provisioning API Key separada).

**No es una decisión de migración** — fue una prueba puntual de comparación. Confidencialidad
(contenido propietario Visa/Mastercard saliendo a una API cloud) y costo por token (real, a
diferencia de Ollama local que es gratis) siguen siendo los puntos abiertos del item 23 si en algún
momento se evalúa una migración real.

## 25. RESUELTO (2026-09-12) — 5 bugs más de `tc_01_to_tc_49` encontrados en una revisión manual guiada por el usuario contra el PDF real (además del item 9)

Sesión distinta a todas las anteriores: por primera vez el **usuario** (no el asistente) revisó el
reporte web línea por línea contra los 2 PDFs reales y pasó ~99 hallazgos en un archivo de
revisión (`revision_manual_2026-09-12.md`, en el repo). Detalle completo, evidencia y números en
NOTES.md, sección "2026-09-12 — Revisión manual...". Resumen:

- **`_detect_reserved_splits` solo capturaba el 1er campo de un split múltiple** (Recipient Name:
  eran 3 campos nuevos, solo se veía 1). Fix: la condición de "arranca al inicio del rango" pasa a
  ser solo el disparador, no el filtro final de `new_fields`.
- **Nuevo `_detect_reserved_merges`** para cuando un campo definido pasa a Reserved con el rango
  CORRIDO por un vecino (no detectable con el mecanismo existente, que exige mismo rango). Destapó
  2 casos más en ediciones históricas previas, nunca vistos.
- **Módulo 2: `Note:`/`Values:`/`Mapping:` de un campo con nombre de 3+ líneas se atribuía al
  campo ANTERIOR** (mismo problema de fondo que items 13/14 en otros manuales, versión propia de
  este). Fix: se generalizó el buffer de columna derecha (antes solo cubría `Description:`
  compartiendo fila con el nombre).
- **Módulo 2: "Format: ... character" (wrap de 2 líneas) se pegaba como prefijo del nombre del
  PRÓXIMO campo** -afectaba 90-96 campos por edición. Fix: se usa `source_block` de Módulo 1 (señal
  exacta) en vez de un umbral de hueco en Y (ya se sabía frágil).
- **Viñetas `"l"` (edición vieja, a veces después del ítem) vs `"●"` (edición nueva) se
  neutralizan para el cálculo de similitud en Módulo 4** -mismo patrón que el item 5 (ya resuelto
  en `base_ii_clearing_data_codes`, nunca portado acá), pero resuelto con un mecanismo distinto
  (Módulo 4 en vez de la red de seguridad de Módulo 5).

**Resultado**: "Cambios de negocio a revisar" del par `20251018→20260418` bajó de 91 a 27. Se
re-corrieron Módulos 02→03→04→05→07 completos para los 8 pares históricos (los bugs de Módulo 2
afectan a todas las ediciones). Commit `d7eb95f`.

**Pendiente para otra sesión, NO bug conocido, solo una pregunta abierta**: ¿los otros manuales
que comparten el patrón de "fix no portado" del item 21 (viñetas del item 5, u otros) se
beneficiarían del mismo tratamiento a nivel de Módulo 4 (neutralizar en el cálculo de similitud)
en vez de/además de la red de seguridad de Módulo 5? No investigado, no se tocó nada fuera de
`tc_01_to_tc_49` esta sesión.

**Próximo paso indicado por el usuario**: repetir esta misma dinámica de revisión manual con otro
de los 7 manuales del proyecto en la próxima sesión (todavía sin elegir cuál).

## 26. RESUELTO (2026-09-13) — Revisión manual de `tc_50_to_tc_92`: 0 hallazgos, reporte validado limpio

El usuario revisó `revision_manual_2026-09-13.md` de
`base_ii_clearing_interchange_formats_tc_50_to_tc_92` (5 casos, todos formato `unpacked numeric` →
`alphanumeric` en el campo `4` - Transaction Component Sequence Number, en varias fichas TCR de TC
50) contra el PDF real y confirmó los 5 como "Ok" -cambios de negocio reales, bien clasificados, sin
ningún bug de pipeline. Cierra este manual como validado para el par de edición vigente. Ref:
`revision_manual_2026-09-13.md` en el repo.

## 27. RESUELTO (2026-09-13) — `base_ii_clearing_data_codes`: reordenamiento de bloques con viñetas genera ~30 falsos `business_rule_change` en el par `20251018→20260418`

- **Dónde**: `base_ii_clearing_data_codes`, tablas `Retired Chargeback Reason Codes` (columna
  *Chargeback Reason Rules*, casi todos los códigos: 30, 41, 53, 57, 60, 61, 62, 70-78, 80-83, 85,
  86, 90, 93), `Return/Reclassification Reason Codes` (códigos `01`, `HZ`, columna *Error
  Condition*), `Request for Copy Reason Codes` (códigos 33/34), y aisladamente `Usage` de los
  códigos `1`/`2`/`R` de POS Environment Codes y `Payment Mode Codes` código `61`.
- **Síntoma reportado por el usuario** (`revision_manual_2026-09-13.md`, ~30 de 47 casos): el
  reporte muestra estos códigos como `business_rule_change` con una `Razón (IA)` que describe un
  cambio de negocio (montos, orden de reglas por región, etc.), pero al comparar Antes/Ahora
  palabra por palabra el contenido es IDÉNTICO -solo cambia el glifo de viñeta (`"l"` en la edición
  vieja vs `"●"` en la nueva) y, más grave, el ORDEN en que las líneas quedaron extraídas: en la
  edición vieja el bloque sale con todas las etiquetas de región primero (`All Regions:`,
  `International:`, `U.K. Domestic:`, ...) seguidas de un bloque separado con todo el texto de las
  viñetas (aparente layout de 2 columnas: columna de glifo/etiqueta vs columna de texto, extraídas
  column-major en vez de row-major); en la edición nueva quedan mejor interleadas pero con una
  fuga menor propia (la 2da línea de una viñeta envuelta a veces queda debajo de la etiqueta de la
  SIGUIENTE región). 5 de estos casos (`61`, `82`, `93`, `01`, `HZ`) están marcados con
  `safety_net_override=True` en el reporte (⚠️ "la IA lo clasifico distinto; se corrigio por
  contenido desaparecido") -el LLM SÍ los clasificó bien (`editorial_reword`/`extraction_noise`)
  pero la red de seguridad de Módulo 5 los pisó igual; los ~25 restantes fueron clasificados
  `business_rule_change` directamente por el LLM (alucinando una razón de negocio a partir del
  ruido de reordenamiento), sin pasar por la red de seguridad.
- **Causa raíz real (confirmada con los JSON crudos, NO era Módulo 1)**: el orden de extracción de
  Módulo 1 (`ingest.py`, campo `order`) ya viene perfecto en ambas ediciones -el bug nace en Módulo 2
  (`normalize.py`, `build_blocks`). Cuando una fila de viñeta+texto envuelto no entra en
  `TABLE_ROW_GAP_MAX` (4.0pt, calibrado especificamente para la tabla "Country and Currency Codes",
  ver su propio comentario en el código), el código la difiere a `pending_prefix` para decidir si
  pertenece a la fila activa o a la siguiente -pero **nunca actualiza `active_last_y1` mientras
  sigue diferiendo**, así que la próxima comparación de "hueco" vuelve a usar el mismo ancla vieja
  (ya no representa el hueco real, que se corrió junto con lo diferido). En una lista larga con
  muchas filas envueltas seguidas (ej. "Chargeback Reason Rules", con 6-10 viñetas por código) esto
  encadena TODAS las filas restantes de la celda en un solo `pending_prefix` gigante que, al volcarse
  de una sola vez, se reordena por **X0 puro** (`sorted(row, key=lambda l: l["bbox"][0])`) -agrupando
  TODAS las etiquetas/viñetas de la columna angosta antes que TODO el texto envuelto de la columna
  ancha, exactamente el sintoma reportado. La edición nueva sufre una variante mas chica del mismo
  bug (viñeta pegada al texto en la misma línea, ej. `"●For T&E transactions..."`, en vez de en su
  propia línea) que tambien dispara diferimientos encadenados mas cortos.
- **Fix aplicado** (`02_normalizacion_bloques/normalize.py`):
  1. `_row_has_bullet_glyph()` (nueva): detecta una línea de viñeta suelta (`"l"`/`"●"`/`"•"`, estilo
     edición vieja) O una línea que EMPIEZA con `"●"`/`"•"` (estilo edición nueva, viñeta pegada al
     texto) -deliberadamente NO se usa `"l"` como prefijo (letra normal, matchearía "local"/"less"/etc).
  2. En la rama de filas multi-línea sin código activo (`elif active_kind in (table_row, table_header)`)
     y en la de línea suelta envuelta: si la fila a diferir tiene viñeta, se actualiza
     `active_last_y1` tambien AL DIFERIR (no solo al finalmente anexar) -mantiene el hueco comparado
     siempre LOCAL, así la cadena de diferimientos se corta apenas el layout vuelve a ser normal, en
     vez de crecer sin límite.
  3. El `sorted(row, key=x0)` que arma `row_sorted` en cada vuelta del loop principal se vuelve
     condicional: si la fila (ya fusionada con `pending_prefix`) tiene viñeta, se ordena por
     `(Y0, X0)` en vez de solo `X0` -evita que una etiqueta de sección (ej. "Examples of a Type A UAT
     transaction are:") que por casualidad comparte X0 con la columna de viñetas quede mezclada fuera
     de orden con el texto envuelto de al lado.
  4. **Todo acotado a `_row_has_bullet_glyph()`**: la tabla "Country and Currency Codes" (nombres de
     país envueltos en 2+ líneas, sin viñetas nunca) queda con el comportamiento ORIGINAL sin tocar
     -validado con diff exacto de las 2051 filas de la edición `20220423` contra el código pre-fix,
     0 diferencias.
- **Validado**: los 4 escenarios de prueba (Chargeback Reason Rules código 82/41, Acceptance
  Terminal Indicator código 1, Country and Currency Codes Bulgaria/Croacia del par actual, y
  Angola/Anguilla + nombres largos de la UE en la edición `20220423`) quedan con el orden de lectura
  correcto y sin ninguna fusión/pérdida de fila. Se re-corrieron Módulos 02→03→04→05→07 para los 8
  pares históricos completos (no solo el par actual). Resultado (primera pasada de este item; una
  segunda observación del usuario destapó otro bug relacionado y bajó el número más -ver item 28-)
  en el par `20251018→20260418`: "Cambios de negocio a revisar" bajó de 49 a 20 -exactamente los
  18 casos que el usuario ya había confirmado como reales ("Ok": Bulgaria/Croacia a Euro,
  definiciones de Glossary, Product ID) más los códigos `33`/`34` de "Request for Copy Reason
  Codes" (en esta primera pasada parecía texto realmente vacío -`"l\nl"`- en la edición vieja; el
  usuario sospechó que también era el bug de viñetas y tenía razón en parte -ver item 28 para el
  diagnóstico real). Los otros 7 pares históricos tambien mejoraron o se mantuvieron (ningún caso
  empeoró): varias filas de país que antes se fusionaban mal (ej. Croacia/Sierra Leona en el par
  `20220423→20221015`) ahora matchean 1:1 y revelan cambios reales de negocio que antes quedaban
  ocultos por el mal emparejamiento (business_rule_change subió de 3→6 y 16→18 en 2 pares, siempre
  por altas genuinas, verificado leyendo el contenido de cada caso nuevo).
- **Caso 15 de `revision_manual_2026-09-13.md`** (`SOURCE IDENTIFIER`, columna *Definition*):
  confirmado "Ok" por el usuario, sin acción de código.
- Ref: `revision_manual_2026-09-13.md` en el repo (casos 1, 2, 17, 18, 22-47). Archivos tocados:
  `02_normalizacion_bloques/normalize.py` (fix de raíz), `04_deteccion_cambios/detect.py` (red
  adicional: `BULLET_TOKEN_PATTERN`/`_similarity_text`, mismo mecanismo que `tc_01_to_tc_49`,
  neutraliza el glifo de viñeta puro en el cálculo de similitud de Módulo 4).

## 28. RESUELTO (2026-09-13) — `base_ii_clearing_data_codes`: `_new_cells` crea una celda de más cuando la fila ancla de un código ya trae viñeta+texto en la misma banda Y (códigos 33/34 de "Request for Copy Reason Codes")

- **Dónde**: `base_ii_clearing_data_codes`, Módulo 2 (`normalize.py`), función `_new_cells`.
- **Cómo se encontró**: después de cerrar el item 27, el usuario mandó 3 casos nuevos de
  `revision_manual_2026-09-13.md` (Caso 1: código `0150`; Caso 2: códigos `33`/`34`), sospechando
  que el mismo problema de viñetas seguía afectando. Se verificó cada uno contra el JSON crudo de
  Módulo 1:
  - **Código `0150`** ("Fee Collection/Funds Disbursement Reason Codes"): el texto de Módulo 1 en
    ambas ediciones coincide EXACTO con lo que muestra el reporte -es un cambio de negocio real
    ("AP region" → "Mexico", "direct fee" → "direct access fee"), no un bug. El usuario tenía
    parcialmente razón en la sospecha (queda un "l" residual al final de la celda, cosmético,
    mismo mecanismo ya conocido de viñeta-al-final-de-lote-diferido) pero la clasificación
    `business_rule_change` es correcta.
  - **Códigos `33`/`34`** ("Request for Copy Reason Codes"): el JSON crudo de Módulo 1 de la
    edición VIEJA (`20251018`) SÍ tiene el texto real ("Legal process or fraud analysis
    request—U.S. Domestic only", etc.) -no estaba vacío. El reporte mostraba `"l\nl"` porque
    Módulo 2 lo estaba perdiendo.
- **Causa raíz**: la fila que arranca un código nuevo vía `_new_cells` (activada por
  `has_code_cell`) agrupa lineas en celdas por hueco de X0 con tolerancia `CELL_X_MERGE_TOLERANCE`
  (3.0pt). Para la mayoría de las tablas de este manual eso alcanza porque la 1ra línea de un
  código nuevo trae solo texto normal (sin viñeta) y las viñetas recién aparecen en filas
  SIGUIENTES (que se anexan via `_nearest_cell`, ya con las celdas ya establecidas de sobra
  anchas). Pero cuando la lista de un código es tan CORTA que la viñeta+texto de su 1er item
  comparte la MISMA banda Y que el número de código (ej. códigos `33`/`34`, con solo 1-2 líneas de
  "Reason" cortas que entran junto al código en el primer renglón visual), `_new_cells` ve 3 grupos
  de X0 (código, viñeta, texto envuelto ~12pt más a la derecha) en vez de 2 (código, "Reason") -una
  celda de más que el encabezado de la tabla (`['Requests', 'Reason']`, 2 columnas). Río abajo
  (Módulo 3/4), el emparejamiento de celdas por índice compara la celda de la VIÑETA SOLA (`"l"`)
  contra la columna "Reason" de la otra edición -el texto real (que terminó en la 3ra celda,
  fuera del rango que el header declara) nunca se compara, se pierde en silencio.
- **Fix**: en `_new_cells`, si la línea INMEDIATAMENTE anterior ya agregada a la celda activa es
  una línea de viñeta (`_row_has_bullet_glyph`, mismo helper del item 27), la línea actual se
  fusiona a esa misma celda SIN IMPORTAR el hueco en X0 -una viñeta y su texto nunca son 2 columnas
  reales distintas. Acotado igual que el item 27 (solo dispara después de una línea de viñeta), así
  que no toca ninguna tabla sin viñetas.
- **Validado**: códigos `33`/`34` ahora producen 2 celdas (`['33', 'l\nLegal process...']`),
  coincidiendo con el encabezado de 2 columnas; el texto real vuelve a compararse contra la edición
  nueva y la clasificación cae a `editorial_reword`/sin cambio real (mismo contenido, solo viñeta).
  Re-validados los 4 escenarios de prueba del item 27 (Chargeback Reason Rules, Acceptance Terminal
  Indicator, Country and Currency Codes del par actual y de `20220423`) sin ninguna regresión -diff
  exacto de las 2051 filas de `20220423`, 0 diferencias. Se re-corrieron Módulos 02→03→04→05→07
  para los 8 pares históricos otra vez.
- **Resultado final** (reemplaza el del item 27): "Cambios de negocio a revisar" del par
  `20251018→20260418` bajó de 49 a **18** -exactamente los 18 casos que el usuario había confirmado
  como reales en su revisión manual original, ni uno más ni uno menos. Se regeneró el reporte web
  consolidado.
- Ref: `poc/base_ii_clearing_data_codes/02_normalizacion_bloques/normalize.py` (`_new_cells`).

## 29. RESUELTO (2026-09-13) — Revisión manual de `base_ii_clearing_edit_package_messages` y `base_ii_transactions_quick_reference`: 0 hallazgos, ambos reportes validados limpios

El usuario revisó `revision_manual_2026-09-13.md` de ambos manuales contra el PDF real y confirmó
todos los casos como "Ok" -cambios de negocio reales, bien clasificados, sin ningún bug de
pipeline:

- `base_ii_clearing_edit_package_messages` (9 casos): todos sobre el mismo patrón de negocio real
  -edits V0173/V0188/V1098 (cashback) cambiando de "must be less than" a "must be less than or
  equal to" el Source Amount, más la ampliación de Transaction Types a "Account Funding" y el
  reword de la definición de BASE II SYSTEM (mismo texto que Glossary de
  `base_ii_clearing_data_codes`, confirmado coherente entre manuales).
- `base_ii_transactions_quick_reference` (15 casos): altas/bajas de TCR 2 "National Settlement"
  por país (Argentina/Bolivia/Brasil/Colombia/Japón/Paraguay) en varias tablas de transacciones.
  Varios casos quedaron marcados ⚠️ por el reporte con "posible renombre no detectado" (cantidad
  neta de TCR sin cambio pero con altas Y bajas -ej. "National Settlement, Argentina" vs "(AR)
  National Settlement, Argentina", que agrega un prefijo de país entre paréntesis y por eso no
  matchea como el mismo TCR) -el usuario confirmó que esta el comportamiento (mostrar como alta+baja
  en vez de forzar un match) es aceptable tal cual, no pidió cambiarlo.

Cierra estos 2 manuales como validados para el par de edición vigente. Con esto, los 4 manuales
"BASE II" del proyecto (`base_ii_clearing_data_codes`, `base_ii_clearing_edit_package_messages`,
`base_ii_clearing_interchange_formats_tc_01_to_tc_49`, `base_ii_clearing_interchange_formats_tc_50_to_tc_92`)
quedan con revisión manual completa. Quedan pendientes los 3 manuales no-BASE-II:
`international_full_service_pos_online_messages_processing_specifications`,
`visanet_settlement_service_vss_user_guide_volume_1_specifications`,
`visanet_settlement_service_vss_user_guide_volume_2_reports`.
- Ref: `revision_manual_2026-09-13.md` en el repo de ambos manuales.

## 30. RESUELTO (2026-09-13) — `international_full_service_pos_online_messages_processing_specifications`: reflow de párrafo con cambio real de contenido en el mismo tramo se reportaba como "contenido agregado" falso

- **Dónde**: `international_full_service_pos_online_messages_processing_specifications`, Módulo 3
  (`match.py`), función `match_paragraphs`.
- **Síntoma reportado por el usuario** (`revision_manual_2026-09-13.md`, Caso 1): sección "Full
  Service Processing Summary > Full Service Participation Requirements > Issuer Options", el
  reporte mostraba el párrafo de "Country-to-Country Transactions" como `business_rule_change`
  con Razón (IA) "la nueva edición añade información adicional sobre los parámetros..." -pero al
  comparar contra el PDF real ambas ediciones tienen el mismo contenido, solo re-cortado
  distinto por un salto de página.
- **Causa raíz**: el mecanismo de detección de reflow (agregado 2026-08-25, ver docstring del
  módulo) ya manejaba este patrón -párrafo dividido distinto entre ediciones por reflow de
  página- pero SOLO cuando el texto concatenado de ambos lados es IDÉNTICO byte a byte. Este
  caso puntual tenía un cambio de wording real y mínimo DENTRO del mismo tramo reflow ("The
  following parameters..." edición vieja → "These parameters..." edición nueva, ratio 0.989 de
  similitud en la concatenación) -exactamente la "limitación aceptada conscientemente" que el
  docstring del módulo ya documentaba como posible pero "no encontrada en el corpus" hasta
  ahora. Al no matchear exacto, el bloque completo caía al pool de fuzzy per-párrafo, que
  terminaba comparando 1 párrafo viejo corto contra 1 párrafo nuevo más largo -dando la falsa
  impresión de "se agregó contenido" en vez de mostrar el cambio real (2 palabras).
- **Fix**: nuevo umbral `REFLOW_CONTENT_SIMILARITY_THRESHOLD=0.95` (más estricto que
  `FUZZY_PARAGRAPH_THRESHOLD=0.90`, porque acá se fusionan 2+ párrafos completos en una sola
  comparación). Cuando un bloque `"replace"` de `SequenceMatcher` a nivel de párrafo no
  concatena idéntico pero sí por encima de ese umbral, se reporta como UN solo
  `paragraph_content_changed` comparando los bloques COMPLETOS concatenados de cada lado -así
  Módulo 5 ve la comparación real, no el artefacto de re-corte. Los bloques mixtos que no
  llegan al umbral (cambio real y sustancial, no solo un ajuste de wording) siguen sin
  sub-dividirse, mismo comportamiento que antes -límite aceptado conscientemente, no perseguido
  más allá sin evidencia de que ocurra.
- **Validado**: el caso reportado ya no aparece en "Cambios de negocio a revisar" -queda
  correctamente absorbido (el cambio real de 2 palabras es tan chico que compensa el resto del
  párrafo, similitud del bloque completo por encima del umbral de "sin cambio real" de Módulo
  4). Se re-corrieron Módulos 03→04→05→07 para los 6 pares históricos del manual. El número
  total de "cambios de negocio a revisar" del par `20251015→20260420` pasó de 3 a 4 -el caso
  reportado desapareció, y aparecieron 2 casos nuevos que antes quedaban ocultos como ruido de
  altas/bajas (un typo real "filed 39"→"field 39" corregido en "Converting Over-Limit Codes", y
  un cambio real en la tabla "Purchase and Cash Disbursement" que eliminó una restricción de
  cashback solo-doméstico) -mejora, no regresión: la mejor cobertura de emparejamiento revela
  cambios reales que antes se perdían en el pool de altas/bajas. Pendiente de que el usuario
  confirme estos 2 casos nuevos en su próxima pasada de revisión. Se regeneró el reporte web
  consolidado.
- Ref: `revision_manual_2026-09-13.md` en el repo (Caso 1). Archivo tocado:
  `03_emparejamiento_bloques/match.py` (`match_paragraphs`).

## 31. RESUELTO (2026-09-13) — Revisión manual completa: los 8 manuales del proyecto quedan validados

Cierre de la iniciativa de revisión manual iniciada 2026-09-12. Los 2 manuales VSS restantes:

- `visanet_settlement_service_vss_user_guide_volume_2_reports` (9 casos en
  `revison_manual_2026-09-13.md`): todos confirmados "Ok" -cambios de negocio reales (rangos de
  posición de campo `filler` corridos, valores de `Attribute` cambiados, nuevo valor válido `0R`
  -Recycling Payout- agregado a `service processing type`). Sin hallazgos de pipeline.
- `visanet_settlement_service_vss_user_guide_volume_1_specifications`: el usuario confirmó
  directamente contra el reporte de cambios (`data/07_reporte_cambios/index.md`) que el par
  vigente (`20250412_to_20251017`) tiene **0 cambios de negocio a revisar** -nada que revisar.

Con esto, **los 8 manuales del proyecto quedan con revisión manual completa** (iniciativa
2026-09-12 → 2026-09-13, ver [[project-visa-manual-review]] en la memoria del asistente):

| Manual | Resultado |
|---|---|
| `base_ii_clearing_data_codes` | 2 bugs encontrados y arreglados (items 27/28) |
| `base_ii_clearing_edit_package_messages` | limpio (item 29) |
| `base_ii_clearing_interchange_formats_tc_01_to_tc_49` | 6 bugs encontrados y arreglados (item 25, commit `d7eb95f`) |
| `base_ii_clearing_interchange_formats_tc_50_to_tc_92` | limpio (item 26) |
| `base_ii_transactions_quick_reference` | limpio (item 29) |
| `international_full_service_pos_online_messages_processing_specifications` | 1 bug encontrado y arreglado (item 30) |
| `visanet_settlement_service_vss_user_guide_volume_1_specifications` | limpio (0 cambios en el par vigente) |
| `visanet_settlement_service_vss_user_guide_volume_2_reports` | limpio (item 31) |

**Cerrado**: el usuario validó y confirmó el commit de los cambios de código de esta sesión
(items 27/28/30) — commit `5cc44d4` (2026-09-13, sin push todavía).
- Ref: `revison_manual_2026-09-13.md` de `vss_volume_2` en el repo.
