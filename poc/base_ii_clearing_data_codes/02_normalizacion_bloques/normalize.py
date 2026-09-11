"""
Modulo 2 - Normalizacion de bloques para el manual base_ii_clearing_data_codes.

Toma las lineas atomicas del Modulo 1 (cada una con su bbox exacto, sin agrupar) y las
reconstruye en bloques con sentido: filas de tabla de codigos (con sus celdas separadas
por columna), encabezados de tabla, y parrafos narrativos. Filtra antes el ruido de
pagina (encabezado/pie repetido, tabla de contenidos).

Idea central del algoritmo (ver discusion de diseno en local_memory/NOTES.md):

1. Dos lineas estan en la misma "fila visual" si sus rangos Y se solapan mas del 50% de
   la altura de la mas chica. Esto agrupa lineas que comparten renglon (columnas de una
   misma fila de tabla) sin fusionar lineas consecutivas de texto normal que solo se
   tocan en el borde.

2. Una fila con 2+ lineas puede ser (a) una fila de datos real de la tabla, o (b) parte de
   un encabezado de columna partido en 2 renglones (ej. "Reason/Code" seguido de
   "Applicable/Operating"). Ambas se ven geometricamente iguales. La senal que las
   distingue es si ALGUNA celda de la fila (no solo la primera) parece un codigo corto
   (mayusculas y/o digitos, sin espacios/minusculas): un titulo de columna en texto
   normal nunca matchea ese patron, pero una fila de datos casi siempre tiene al menos
   una celda-codigo aunque la columna clave (primera celda) sea un nombre en vez de un
   codigo (ej. `['Afghanistan', 'AF', '004', 'Afghani', 'AFN', '971']` no matchea en la
   1ra celda pero si en la 2da/3ra/5ta/6ta). Si ninguna celda matchea y ya hay una fila de
   datos activa, se asume que es el wrap de esa misma fila (ej. "Antigua and" + "Barbuda"
   en renglones separados) y se fusiona por columna; si no hay fila activa, es
   continuacion del encabezado en curso.

3. Una fila con 1 sola linea es una continuacion: se asigna a la columna mas cercana en X
   del bloque activo (asi los bullets y parrafos de una celda ancha como "Chargeback
   Reason Rules" se van acumulando hasta que aparece la proxima fila de datos real).

4. Bug de continuidad entre paginas (encontrado y arreglado 2026-08-12): cuando una fila de
   codigo es tan larga que su descripcion sigue en la pagina siguiente, este manual la
   reintroduce con el literal `"<codigo> (continued)"` (ej. `"H0 (continued)"`) despues del
   encabezado de tabla que se re-declara al tope de cada pagina. Como `build_blocks()`
   procesa pagina por pagina y el estado se resetea en cada salto, esa fila caia como
   continuacion del encabezado recien declarado (ni el codigo con sufijo ni sus celdas
   vecinas matcheaban `CODE_LIKE`). Fix en dos partes: (a) `CONTINUED_CODE` reconoce el
   patron `"<codigo> (continued)"` como celda-codigo, asi la fila se cierra como
   `table_row` propio en vez de fusionarse al header; (b) `_merge_continued_rows()` hace un
   pasada final sobre TODOS los bloques del documento (no por pagina) que busca, para cada
   `table_row` cuya 1ra celda matchea ese patron, la fila `table_row` mas reciente con el
   mismo codigo (sin el sufijo) y le fusiona las celdas por columna — asi "H0" y "H0
   (continued)" terminan siendo una sola fila logica, en vez de dos bloques separados.

5. Bug de nombres largos envueltos en 2+ lineas dentro de una fila de datos (encontrado y
   arreglado 2026-08-12, localizado a la edicion `20230415` de este manual): en tablas como
   "Country and Currency Codes"/"U.S. State Codes", cuando el nombre de la columna clave es
   largo y envuelve en 2-3 lineas (ej. "Bolivia (Plurinational State of)"), el renderizado
   de este PDF centra verticalmente las celdas de 1 sola linea (codigo/moneda/etc) respecto
   al nombre envuelto — asi que la 1ra y ultima linea del nombre quedan geometricamente
   "huerfanas": no se solapan lo suficiente en Y con la fila de datos (que queda alineada
   con la linea del medio) como para agruparse en `group_into_rows()`, y tampoco tienen
   forma de saber si pertenecen a la fila ANTERIOR (ya activa) o a la fila SIGUIENTE (que
   todavia no se proceso). El codigo viejo asumia ciegamente "pertenece a la fila activa",
   lo cual esta bien para el sufijo (linea final del wrap) pero mal para el prefijo (linea
   inicial), que en realidad es el comienzo de una fila nueva -confirmado con datos reales:
   "Bolivia (Plurina-" se pegaba a la fila de "Bhutan" en vez de a la fila de "Bolivia" en
   si, y asi sucesivamente, produciendo columnas clave corruptas
   (`"Bhutan\nBolivia (Plurina..."`) y filas de datos sin nombre de pais (solo codigo).

   **Fix**: se agrega vision hacia adelante (`rows[i+1]`) a `build_blocks()`. Cuando una
   linea suelta esta por fusionarse a la fila de tabla activa pero el hueco vertical hasta
   esa fila activa (`gap_to_active`) es mayor a `TABLE_ROW_GAP_MAX` (4pt — calibrado contra
   datos reales: lineas de una misma celda envuelta quedan pegadas a ~0pt, filas distintas
   quedan separadas ~8.5pt en este manual) Y el hueco hasta la fila SIGUIENTE es menor que
   el hueco hasta la activa, la linea se guarda en un buffer (`pending_prefix`) en vez de
   fusionarse ahora; se antepone a la proxima fila cuando esta se procesa. `_new_cells()` se
   actualizo para fusionar lineas consecutivas con `x0` casi identico (`CELL_X_MERGE_
   TOLERANCE`) en una sola celda, para que ese prefijo antepuesto se una correctamente con
   la 1ra linea real de la fila siguiente en vez de contar como una columna extra. Validado
   contra los 3 casos reales de la edicion `20230415` (Bolivia 2 lineas, Bonaire, Sint
   Eustatius and Saba 3 lineas, Bosnia and Herzegovina 2 lineas) trazando las coordenadas
   crudas a mano antes de implementar — los 3 quedan con su nombre completo en 1 sola celda
   y su fila de datos correcta.

Limitacion conocida (aceptable para esta prueba de concepto, riesgo residual del fix del
2026-08-12): si un fragmento de encabezado wrappeado cae, por casualidad, en un token corto
todo-mayusculas (ej. la sigla "ISO" sola en su propio renglon), se clasificaria como celda-
codigo y cortaria el encabezado antes de tiempo. No se observo este caso en el muestreo
hecho hasta ahora (los titulos de columna de este manual siempre son palabras normales o
frases de 2+ palabras).

6. **Fila secundaria de moneda en transicion, sin columna clave, tratada como fila nueva por
   error (encontrado y arreglado 2026-08-20, investigando el alcance real del bug #3 del
   TODO).** Confirmado con datos reales: en `Country and Currency Codes`, cuando un pais
   tiene una transicion de moneda documentada (Croacia HRK->Euro, Sierra Leone SLL->SLE), el
   PDF fuente muestra el valor VIEJO y/o NUEVO como una linea adicional apilada dentro de la
   misma fila visual del pais, pero SIN texto en la columna ancla (nombre de pais, X0~75) -
   solo en las columnas de moneda (X0>=300). Antes del fix de Modulo 1 (ver su docstring,
   filtro de marcador de nota al pie), estas lineas ademas traian un digito de nota al pie
   fusionado, agravando el problema. La logica anterior de `build_blocks()` solo miraba
   "¿tiene esta fila multi-linea alguna celda tipo codigo?" para decidir si es una fila
   NUEVA -sin chequear si esa fila realmente arranca en la columna ancla de la tabla activa-
   asi que estas filas secundarias (`['SLL','694']`, `['Leone','SLE','925']`, sin nombre de
   pais) se procesaban como filas de datos propias e independientes, huerfanas, en vez de
   fusionarse con la fila del pais al que realmente pertenecen.

   **Fix**: se agrega un chequeo de "¿arranca cerca de la columna ancla de la fila de DATOS
   activa?" (`SECONDARY_ROW_ANCHOR_GAP_MIN`, umbral propio y mas amplio que
   `TABLE_LEFT_MARGIN_TOLERANCE` -ver su comentario para la calibracion real, la brecha de
   este caso es un orden de magnitud mayor que la de una fila normal) ANTES de decidir si una
   fila multi-linea con celda-codigo es una fila nueva -pero SOLO
   quando la fila activa es otra `table_row` (no un `table_header`, ver nota de alcance mas
   abajo). Si NO arranca cerca del ancla, ya no dispara `flush()`+fila nueva -cae en la MISMA
   rama de decision por hueco vertical (activa vs siguiente) que ya existia para filas sin
   celda-codigo, reusando el mecanismo de `pending_prefix` sin duplicar logica. Esto cubre
   los 2 sub-casos reales encontrados: (a) la fila secundaria aparece ANTES de que la fila
   del pais se abra (Sierra Leone: el fragmento `SLL/694` esta geometricamente mas cerca de
   la fila SIGUIENTE que de la activa -Seychelles-, asi que se buferea y se antepone
   correctamente cuando se procesa la fila real de Sierra Leone); (b) aparece DESPUES, con la
   fila del pais ya activa (el fragmento `Leone/SLE/925` esta mas cerca de la fila activa que
   de la siguiente -Singapore-, asi que se fusiona directo). Verificado leyendo el JSON
   reconstruido real: Croacia y Sierra Leone terminan con sus 6 celdas completas y limpias en
   todas las ediciones afectadas, sin filas huerfanas con nombres como
   `'SLL'`/`'Leone'`/`'Euro'` en la columna de pais.

   **Alcance acotado a `table_row`->`table_row`, encontrado ajustando este mismo fix**: la
   primera version del chequeo tambien se aplicaba a la transicion encabezado->primera-fila,
   y rompio una tabla DISTINTA ("Numeric Currency Code to Country Name Cross-Reference",
   mismo documento, columnas Codigo Numerico/Nombre de Pais): ahi el label del encabezado
   ("Currency Code", X0=84.1) y su propia primera fila de datos ("496", X0=111.0, alineado
   distinto por ser un codigo corto de 3 digitos) difieren 26.9pt -por encima de la
   tolerancia- por pura alineacion tipografica normal, sin ninguna fila huerfana de verdad.
   Aplicar el chequeo ahi fusionaba TODA la tabla en 1 encabezado gigante + 1 fila gigante
   (confirmado con un A/B directo comparando la salida con y sin el chequeo, misma pagina).
   Entre 2 filas de DATOS de una misma tabla la alineacion es estable (todas comparten
   columna ancla), asi que acotar el chequeo a `active_kind == "table_row"` (nunca
   `"table_header"`) preserva el fix de Croacia/Sierra Leone sin tocar el comportamiento ya
   validado de encabezado->primera-fila en ninguna tabla -mismo principio ya aprendido en
   otros manuales de este proyecto: un umbral geometrico calibrado contra 1 tabla no es
   seguro asumirlo valido para las demas sin volver a validar (ver [[dev-phase-considerations]]
   punto 2/6, mismo hallazgo, otro proyecto de la misma cuenta).

7. **Bloque de notas al pie al final de una tabla se fusionaba con la ultima fila de datos,
   cuando arranca en la MISMA columna ancla que la tabla (encontrado y arreglado 2026-08-25,
   resolviendo [[pending-bug-fixes]] item 3b -bug de la MISMA clase que el punto 6, mecanismo
   distinto).** Confirmado con datos reales: en `Country and Currency Codes`, el bloque de
   notas al pie que define las notas 1/2/3 (transicion de moneda de Croacia/Sierra
   Leone/Zimbabwe) aparece DESPUES de la ultima fila de la tabla (Zimbabwe, alfabeticamente
   ultimo) y ANTES del titulo de la seccion siguiente, arrancando en el mismo X0 que la
   columna de nombre de pais (75.0) -a diferencia del punto 6, esta fila NO tiene celda-codigo
   (es prosa larga) asi que nunca entra a esa rama, y el chequeo de "¿arranca mas a la
   izquierda que la tabla?" (`TABLE_LEFT_MARGIN_TOLERANCE`) tampoco dispara porque no hay
   corrimiento a la izquierda -asi que caia en la rama de "nombre envuelto" (punto 5), que
   solo sabe fusionar con la fila activa o diferir a la siguiente, nunca "cerrar la tabla e
   iniciar un bloque nuevo". Resultado real observado: la celda de nombre de Zimbabwe llegaba
   a 1230 caracteres (nombre + 3 notas completas + titulo y parrafo intro de la seccion
   siguiente).

   **Fix**: se agrega una señal positiva e independiente de la geometria X -
   `starts_with_footnote_marker`, calculada en Modulo 1 (`ingest.py`)- que detecta si una
   linea arranca con el mismo marcador de nota al pie chico (6.75pt, solo digitos) que ya se
   filtraba de las celdas de codigo (ver docstring de Modulo 1), pero en la PRIMERA posicion
   del span (no la ultima) seguido de 15+ caracteres de prosa real -la forma en que este
   documento codifica el INICIO de un parrafo de nota, confirmada sin excepciones escaneando
   las 9 ediciones completas (10 bloques de notas distintos, no solo el de esta tabla). Cuando
   una linea trae esta señal en Modulo 2, se fuerza el mismo comportamiento que el chequeo de
   margen izquierdo (`flush()` + arranca `paragraph` nuevo) sin importar la posicion X. Una
   vez que el bloque de notas entra a la rama de `paragraph` (que ya tenia su propia logica de
   corte por hueco/corrimiento, puntos no numerados de mas arriba), el titulo de la seccion
   siguiente ("Canadian Province Codes", 26pt) se separa solo -el hueco real hasta el (~28pt)
   supera `PARAGRAPH_MAX_GAP`, asi que nunca hizo falta tocar esa logica.

   **Por que las DEMAS notas al pie del documento (p.54, p.101, p.106, p.134-142, confirmadas
   con el mismo escaneo) no mostraban este bug**: en esos casos el bloque activo antes de la
   nota ya era `paragraph` (narrativa, no una tabla de codigos de columnas fijas), asi que la
   logica de corte por hueco de esa rama ya las separaba correctamente -el bug era especifico
   de la transicion `table_row` -> nota al pie, que no tenia ninguna via de salida a
   `paragraph`.

   **Residuo, CERRADO por completo 2026-09-05 en 2 pasadas (ver `MAJOR_HEADING_MIN_SIZE` y
   `NOTE_BEFORE_HEADING_LOOKAHEAD` mas abajo)**: desde la edicion `20251018`, Visa cambio el
   formato de la nota de Zimbabwe de lista numerada a un unico parrafo con la etiqueta
   `"Note:"` (verificado con datos reales: NO esta en negrita, una nota anterior de este mismo
   docstring lo decia mal). Una regla ciega "cualquier linea que arranque con 'Note:' corta la
   tabla" fue investigada y descartada: un escaneo del corpus completo encontro ~50 apariciones
   de `"Note:"` por edicion, la mayoria (ej. p.80, codigo `"80"` de `Return/Reclassification
   Reason Codes": "Note: Product Reclassification occurs in these conditions:"`) son contenido
   LEGITIMO dentro de la celda de un codigo ya activo.

   **Primera pasada** (`MAJOR_HEADING_MIN_SIZE`): el titulo de 26pt de la seccion siguiente
   ("Canadian Province Codes") ya no se fusiona -cierra el residuo por completo en `20260418`
   (Visa saco la nota de ZWG/ZWL ahi, sin nota de por medio el fix alcanza) y lo reduce en
   `20251018` (ya no se traga la seccion siguiente, solo queda pegada la propia nota).

   **Segunda pasada** (`NOTE_BEFORE_HEADING_LOOKAHEAD`, `_note_precedes_major_heading`): la
   señal que faltaba para distinguir "esta 'Note:' cierra la tabla" de "esta 'Note:' es
   contenido real dentro de una celda abierta" resulto ser "mirar hacia adelante" en vez de
   inspeccionar solo la linea misma -3 condiciones juntas (no es ella misma un codigo real,
   arranca en la MISMA columna ancla que la fila activa, y dentro de las proximas
   `NOTE_BEFORE_HEADING_LOOKAHEAD` filas aparece un encabezado mayor sin ningun codigo real de
   por medio), validadas con un escaneo real de las 9 ediciones completas ANTES de implementar:
   exactamente 8 casos en todo el corpus, 0 falsos positivos (una version sin la condicion
   "no es ella misma un codigo real" colaba el codigo real `"X"` de una fila que arranca sola
   en la misma columna; sin la condicion de columna ancla colaban envolturas normales de
   descripciones largas). **Hallazgo real, no solo Zimbabwe**: los otros 7 casos son la MISMA
   nota recurrente sobre "Type D (Dispute) stopped being valid" fusionada con los codigos `04`
   y `7` de 2 tablas de disputas distintas, en TODAS las 9 ediciones -un bug identico, mas
   extendido de lo que sugeria el nombre "residuo de Zimbabwe". **Verificado end-to-end**:
   Modulos 2->5,7 re-corridos, Zimbabwe queda limpio (`"Zimbabwe"`, 8 caracteres) en las 9
   ediciones, las notas `04`/`7` tambien quedan como bloques propios; en Modulo 4, las unicas
   entradas `code_added`/`code_removed` que cambiaron fueron exactamente las contaminadas (3
   pares en `20250412_to_20251018`, 1 par en `20251018_to_20260418`) desapareciendo de AMBOS
   lados sin generar ninguna nueva -confirma que eran ruido puro, no perdida de datos reales;
   `code_content_changed` byte-identico en los 2 pares afectados (117 y 114). Modulo 5 re-corrido
   con Ollama real para esos 2 pares: clasificaciones identicas a la corrida anterior (mismo
   `business_rule_change`/`editorial_reword`/`safety_net_override`), confirmando que el fix solo
   afecto conteos estructurales, nunca el contenido ya clasificado. [[pending-bug-fixes]] item 3b
   queda resuelto por completo.

8. **Glosario del manual, colapsado en 1 solo bloque `table_header` gigante por pagina en vez
   de una entrada (termino + definicion) por fila (encontrado y arreglado 2026-08-25,
   resolviendo [[pending-bug-fixes]] item 1).** El glosario (ultima seccion del documento en
   las 9 ediciones) usa geometricamente el MISMO patron de 2 columnas que ya reconstruyen los
   puntos 1-7 de este docstring (termino a X0=72, definicion a X0=216, ambos comparten el Y0
   de su primera linea) -la unica razon por la que fallaba es que el heuristico de "¿esta
   fila arranca una entrada NUEVA?" dependia exclusivamente de `CODE_LIKE` (celda-codigo
   corta), y un termino de glosario (frase en minusculas, varias palabras) nunca matchea eso
   -asi que cada entrada se procesaba como continuacion de la anterior via la rama de
   "encabezado partido en 2 renglones", fusionando todo el glosario de la pagina en 1 bloque.

   **Fix**: se agrega el flag `bold` por linea en Modulo 1 (`ingest.py`,
   `_segment_is_bold`) -unica señal tipografica real que distingue columna clave
   (`OpenSans-Bold`) de columna de definicion (`OpenSans-Regular`), dado que ambas comparten
   tamano de fuente (9.0pt). Un nuevo estado `in_glossary` (dict `state`, pasado explicitamente
   entre paginas porque `build_blocks()` se llama una vez por pagina desde
   `normalize_edition()`) se activa al ver la fila de 1 sola linea con texto exacto
   `"Glossary"` (encabezado de seccion, 26pt, confirmado identico en las 9 ediciones) y dura
   el resto del documento -no hace falta desactivarlo, el glosario es la ultima seccion en
   las 9 ediciones. Mientras `in_glossary` esta activo, cualquier fila multi-linea con AL
   MENOS una celda en negrita cuenta como "celda-codigo" a efectos de la misma logica de
   decision que ya usan las tablas de codigo (puntos 1-7) -asi cada entrada se convierte en su
   propio `table_row` de 2 celdas (`[termino, definicion]`), reusando sin cambios toda la
   logica de fusion de lineas envueltas (nombre de termino en 2+ lineas, definicion en 2+
   lineas) que ya estaba validada para las demas tablas.

   **Por que se acota a `in_glossary`, no una regla global de "negrita = fila nueva"**: los
   encabezados de columna de otras tablas tambien pueden traer negrita (no verificado a fondo,
   no hacia falta -el mismo principio de cautela que el resto de este docstring: un heuristico
   nuevo se acota al contexto real donde se confirmo, no se generaliza sin validar).
"""

import json
import re
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_data_codes"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"

# Bandas de encabezado/pie de pagina, calibradas con datos reales de este manual
# (ver local_memory/NOTES.md: "BASE II Clearing Data Codes" como header vive en
# y1<=41, "Visa Confidential"/fecha/numero de pagina como footer viven en y0>=743).
HEADER_Y_MAX = 45
FOOTER_Y_MIN = 745

TOC_DOT_LEADER = re.compile(r"(\. ){4,}")
CODE_LIKE = re.compile(r"^[A-Z0-9]{1,6}$")
CONTINUED_CODE = re.compile(r"^([A-Z0-9]{1,6})\s*\(continued\)$", re.IGNORECASE)

# Ventana de bloques hacia atras en la que _merge_continued_rows() busca la fila original
# a fusionar. Una continuacion real ocurre a lo sumo 1 salto de pagina despues (unas pocas
# decenas de bloques); acotar la busqueda evita fusionar con un codigo repetido en una
# tabla lejana no relacionada.
CONTINUED_ROW_SEARCH_WINDOW = 50

SAME_ROW_MIN_OVERLAP_RATIO = 0.5
PARAGRAPH_MAX_GAP = 10.0
PARAGRAPH_MAX_X_SHIFT = 20.0
TABLE_LEFT_MARGIN_TOLERANCE = 15.0

# Calibrado con datos reales de la tabla "Country and Currency Codes" en la edicion
# 20230415 (ver discusion en el docstring del modulo, punto 5): lineas de una misma celda
# envuelta quedan pegadas verticalmente (~0pt de hueco); filas de datos distintas quedan
# separadas ~8.5pt. 4.0 separa ambos casos con margen.
TABLE_ROW_GAP_MAX = 4.0
CELL_X_MERGE_TOLERANCE = 3.0

# Umbral de "fila secundaria sin columna ancla" (punto 6 del docstring), calibrado con un
# escaneo real de las 9 ediciones completas (no solo Croacia/Sierra Leone): la brecha X0
# real entre una fila de datos normal y la columna ancla de la fila activa -por pura
# alineacion tipografica de codigos cortos/etiquetas mas anchas, SIN ninguna fila huerfana
# de verdad- va de 19.8 a 78.1pt (ej. "H0 (continued)"->"H1", codigos alfa de pais tras un
# header de region). Las filas secundarias REALES (Croacia, Sierra Leone, y el mismo patron
# encontrado tambien en nombres de moneda envueltos como "Mozambique Metical") arrancan en
# 233.9pt como minimo. Separacion real de 155.7pt entre ambos grupos, sin ningun caso
# intermedio en las 9 ediciones -umbral a mitad de camino, con margen amplio en ambos lados.
SECONDARY_ROW_ANCHOR_GAP_MIN = 150.0

# Umbral para distinguir, dentro del glosario, un termino envuelto en 2+ lineas (punto 8 del
# docstring) de una entrada nueva. Calibrado con un escaneo real de las 9 ediciones completas
# (no solo 1): el hueco vertical entre la ultima linea en negrita de un termino y su propia
# continuacion envuelta es SIEMPRE <=0pt (lineas pegadas/superpuestas, min -0.9); el hueco
# hasta el termino de la entrada SIGUIENTE es SIEMPRE >=9.3pt. 8.0 separa ambos grupos con
# margen amplio en las 9 ediciones.
GLOSSARY_TERM_WRAP_GAP_MAX = 8.0

# Tamano de fuente minimo para aceptar la fila de 1 linea "Glossary" como el encabezado real
# de seccion (26pt en las 9 ediciones) y no la entrada homonima de la tabla de contenidos
# (12pt, mismo texto exacto y misma negrita -no alcanzaba con texto+negrita para distinguirlos).
GLOSSARY_HEADING_MIN_SIZE = 20.0

# Umbral para reconocer CUALQUIER titulo de seccion/tabla en negrita como corte duro, no solo
# "Glossary" (punto 7 del docstring, residuo de Zimbabwe -[[pending-bug-fixes]] item 3b).
# Escaneo real de las 9 ediciones completas: 83-93 lineas negrita+tamano>=20pt por edicion,
# TODAS titulos de seccion/tabla genuinos (ej. "Canadian Province Codes", "Chapter 1", los
# mismos ~84 titulos repetidos en cada edicion) -ninguna es contenido real de una celda de
# tabla (esas son siempre 9-9.5pt). Mismo umbral que GLOSSARY_HEADING_MIN_SIZE, generalizado.
MAJOR_HEADING_MIN_SIZE = 20.0

# Cuantas filas mirar hacia adelante para decidir si una linea suelta (ej. "Note:", sin
# marcador de digito) es el ARRANQUE de un bloque de notas al pie que termina la tabla activa,
# en vez de contenido real de celda (punto 7 del docstring, cierre del residuo de Zimbabwe
# -[[pending-bug-fixes]] item 3b). Calibrado con un escaneo real de las 9 ediciones completas
# usando `_note_precedes_major_heading`: 5 satura el resultado (K=5, 10 y 20 dan exactamente
# los mismos 8 casos en todo el corpus -ninguno nuevo al agrandar la ventana), K=3 pierde 7 de
# los 8 (los bloques de nota reales tienen hasta 3 lineas de prosa antes del encabezado).
NOTE_BEFORE_HEADING_LOOKAHEAD = 5


def is_noise(line: dict) -> bool:
    y0, y1 = line["bbox"][1], line["bbox"][3]
    if y1 <= HEADER_Y_MAX or y0 >= FOOTER_Y_MIN:
        return True
    if TOC_DOT_LEADER.search(line["text"]):
        return True
    return False


def group_into_rows(lines: list) -> list:
    """Agrupa lineas consecutivas que comparten banda Y (misma fila visual)."""
    rows = []
    current = []
    ref_y0 = ref_y1 = None
    for line in lines:
        y0, y1 = line["bbox"][1], line["bbox"][3]
        if current:
            overlap = min(ref_y1, y1) - max(ref_y0, y0)
            min_height = min(ref_y1 - ref_y0, y1 - y0)
            if overlap > SAME_ROW_MIN_OVERLAP_RATIO * min_height:
                current.append(line)
                continue
            rows.append(current)
        current = [line]
        ref_y0, ref_y1 = y0, y1
    if current:
        rows.append(current)
    return rows


def _new_cells(row_lines: list) -> list:
    row_sorted = sorted(row_lines, key=lambda l: l["bbox"][0])
    cells = []
    for line in row_sorted:
        x0 = line["bbox"][0]
        if cells and abs(cells[-1]["x0"] - x0) <= CELL_X_MERGE_TOLERANCE:
            cells[-1]["text"].append(line["text"])
        else:
            cells.append({"x0": x0, "text": [line["text"]]})
    return cells


def _nearest_cell(cells: list, x0: float) -> dict:
    return min(cells, key=lambda c: abs(c["x0"] - x0))


def _row_min_y0(row: list) -> float:
    return min(l["bbox"][1] for l in row)


def _row_max_y1(row: list) -> float:
    return max(l["bbox"][3] for l in row)


def _note_precedes_major_heading(rows: list, i: int, min_cell_x0: float, line: dict) -> bool:
    """¿Esta linea suelta (ej. "Note:") arranca un bloque de notas al pie que termina la tabla
    activa? Señal de "mirar hacia adelante" (residuo del punto 7 del docstring, cierre de
    [[pending-bug-fixes]] item 3b): sin marcador de digito ni negrita+tamano grande (esas ya
    tienen su propia señal, ver los otros 2 chequeos donde se llama a esta funcion), la unica
    forma segura de distinguir "Note: cierra la tabla" de "Note: es contenido real dentro de
    una celda de codigo ya abierta" (~50 apariciones/edicion, la mayoria legitimas) es revisar
    que decision es CONSISTENTE con lo que viene despues.

    3 condiciones, las 3 necesarias (validado con datos reales de las 9 ediciones completas:
    sin la primera, "X" -codigo real de una fila que arranca sola en la misma columna ancla
    que la anterior- se cuela como falso positivo; sin la segunda o la tercera, se cuelan
    envolturas de descripcion multi-linea de una celda ya activa que casualmente terminan cerca
    de un encabezado. Con las 3 juntas: exactamente 8 casos en todo el corpus, los 7 de una
    nota recurrente sobre "Type D" en otras tablas + Zimbabwe, 0 falsos positivos):
    1. La linea NO es ella misma un codigo real (`CODE_LIKE`) -si lo fuera, es el ancla de la
       fila SIGUIENTE, no una nota (ej. el codigo "X" de "Visa B2B Virtual Payments").
    2. La linea arranca en la MISMA columna ancla que la fila activa (`min_cell_x0`, con la
       misma tolerancia que ya usa `_nearest_cell`/`CELL_X_MERGE_TOLERANCE` para fusionar
       celdas) -una envoltura real de la descripcion de un codigo arranca en la columna de
       DESCRIPCION, no en la del codigo.
    3. Dentro de las proximas `NOTE_BEFORE_HEADING_LOOKAHEAD` filas de la MISMA pagina aparece
       un encabezado mayor (`MAJOR_HEADING_MIN_SIZE`), sin ninguna fila con un codigo real
       (`CODE_LIKE`) de por medio -si aparece un codigo real antes, la tabla sigue viva y esta
       linea es contenido normal de una celda, no el cierre de la tabla.
    """
    if CODE_LIKE.match(line["text"]):
        return False
    if abs(line["bbox"][0] - min_cell_x0) > CELL_X_MERGE_TOLERANCE:
        return False
    for row in rows[i + 1 : i + 1 + NOTE_BEFORE_HEADING_LOOKAHEAD]:
        if len(row) == 1 and row[0].get("bold") and row[0].get("max_size", 0) >= MAJOR_HEADING_MIN_SIZE:
            return True
        if any(CODE_LIKE.match(l["text"]) for l in row):
            return False
    return False


def build_blocks(rows: list, page: int, state: dict) -> list:
    blocks = []
    active_kind = None
    active_cells = None
    active_last_y1 = None
    paragraph_last_y1 = None
    # Y1 de la ULTIMA linea en negrita de la entrada de glosario activa (distinto de
    # `active_last_y1`, que sigue el final de TODAS las celdas incluida la definicion) -ver
    # punto 8 del docstring, necesario para distinguir un termino envuelto en 2+ lineas de una
    # entrada nueva.
    active_term_last_y1 = None
    pending_prefix = []  # lineas huerfanas que pertenecen a la PROXIMA fila, no a la activa

    def flush():
        nonlocal active_kind, active_cells, active_last_y1, paragraph_last_y1, active_term_last_y1
        if active_cells:
            blocks.append(
                {
                    "type": active_kind,
                    "page": page,
                    "cells": ["\n".join(c["text"]) for c in active_cells],
                }
            )
        active_kind, active_cells, active_last_y1, paragraph_last_y1 = None, None, None, None
        active_term_last_y1 = None

    for i, row in enumerate(rows):
        if pending_prefix:
            row = pending_prefix + row
            pending_prefix = []

        row_sorted = sorted(row, key=lambda l: l["bbox"][0])
        is_multi = len(row_sorted) >= 2

        # Encabezado de seccion "Glossary" (punto 8 del docstring): dispara el modo
        # `in_glossary`, que dura el resto del documento (es la ultima seccion en las 9
        # ediciones). Se maneja ANTES que cualquier otra rama -inclusive la de 1 sola linea-
        # porque el titulo mismo es una fila de 1 linea que de otra forma se fusionaria como
        # texto suelto a lo que estuviera activo.
        if (
            not is_multi
            and row_sorted[0]["text"].strip() == "Glossary"
            and row_sorted[0].get("max_size", 0) > GLOSSARY_HEADING_MIN_SIZE
        ):
            flush()
            state["in_glossary"] = True
            active_kind = "paragraph"
            active_cells = [{"x0": row_sorted[0]["bbox"][0], "text": [row_sorted[0]["text"]]}]
            paragraph_last_y1 = row_sorted[0]["bbox"][3]
            continue

        if is_multi:
            has_code_cell = any(
                CODE_LIKE.match(line["text"]) or CONTINUED_CODE.match(line["text"])
                for line in row_sorted
            )
            # Termino de glosario en negrita (punto 8 del docstring): equivalente a
            # "celda-codigo" para el proposito de decidir si esta fila arranca una entrada
            # nueva -el glosario no tiene ninguna celda tipo codigo, pero SI tiene una unica
            # senal tipografica real (negrita) que distingue termino de definicion.
            glossary_bold_line = None
            if state["in_glossary"] and not has_code_cell:
                glossary_bold_line = next((line for line in row_sorted if line.get("bold")), None)
            if glossary_bold_line is not None:
                # Un termino puede envolver en 2+ lineas (ej. "Account Screen Authorization"
                # + "File (ASAF)") -la 2da linea sigue en negrita y por casualidad geometrica
                # puede compartir banda Y con una linea INTERNA (no la 1ra) de la definicion
                # activa, asi que se ve igual a una entrada nueva. Se distingue por el hueco
                # vertical hasta la ULTIMA linea en negrita ya vista: un termino envuelto
                # queda pegado (<=0pt en las 9 ediciones), una entrada nueva empieza muy
                # despues (>=9.3pt) -ver calibracion real en `GLOSSARY_TERM_WRAP_GAP_MAX`.
                is_wrap = (
                    active_kind == "table_row"
                    and active_term_last_y1 is not None
                    and glossary_bold_line["bbox"][1] - active_term_last_y1 < GLOSSARY_TERM_WRAP_GAP_MAX
                )
                if not is_wrap:
                    has_code_cell = True
            # Una fila con celda-codigo solo se acepta como fila NUEVA si arranca cerca de
            # la columna ancla de la fila de DATOS activa -ver punto 6 del docstring. Chequeo
            # acotado a la transicion fila-a-fila (`active_kind == "table_row"`), NO a la
            # transicion encabezado-a-primera-fila: en algunas tablas (ej. "Numeric Currency
            # Code to Country Name Cross-Reference", codigo numerico angosto/alineado
            # distinto al label del encabezado "Currency Code") el propio encabezado arranca
            # mas a la izquierda que su primera fila de datos por simple alineacion tipografica
            # (26.9pt de diferencia real, por encima de la tolerancia) -bug real encontrado
            # validando este fix contra las 9 ediciones completas, no solo Croacia/Sierra
            # Leone: aplicar el chequeo tambien ahi fusionaba TODA la tabla en 1 encabezado +
            # 1 fila gigante. Entre filas de datos reales de la MISMA tabla la alineacion es
            # estable (todas las filas comparten columna ancla), asi que acotar el chequeo a
            # table_row preserva el fix original sin romper esta otra tabla.
            row_x0 = row_sorted[0]["bbox"][0]
            is_near_anchor = (
                active_kind != "table_row"
                or row_x0 - active_cells[0]["x0"] < SECONDARY_ROW_ANCHOR_GAP_MIN
            )
            if has_code_cell and is_near_anchor:
                flush()
                if state["in_glossary"] and not state.get("glossary_header_emitted"):
                    # Modulo 3 solo reconoce una tabla logica cuando ve un `table_header`
                    # -sin uno, cada `table_row` sin tabla activa cae en su mecanismo
                    # generico de "fila huerfana" (titulo "(sin titulo)"), que ademas fusiona
                    # CUALQUIER otra fila huerfana no relacionada del resto del documento que
                    # comparta ese mismo titulo generico. El glosario no tiene una fila de
                    # encabezado de columna real que extraer, asi que se emite una sintetica
                    # una sola vez (justo antes de la 1ra entrada real) para que las ~200
                    # entradas se reconstruyan como una tabla propia y estable, sin tocar el
                    # mecanismo generico de filas huerfanas que usan las demas tablas.
                    blocks.append(
                        {"type": "table_header", "page": page, "cells": ["Term", "Definition"]}
                    )
                    state["glossary_header_emitted"] = True
                active_kind = "table_row"
                active_cells = _new_cells(row_sorted)
                active_last_y1 = _row_max_y1(row_sorted)
                bold_line = next((line for line in row_sorted if line.get("bold")), None)
                active_term_last_y1 = bold_line["bbox"][3] if bold_line is not None else None
            elif has_code_cell:
                # Fila secundaria fuera de ancla (punto 6): a diferencia del caso simetrico
                # SIN celda-codigo (rama de abajo, decide por el hueco numerico mas chico -
                # valido ahi porque una linea de nombre envuelto puede pertenecer
                # genuinamente a cualquiera de los 2 lados), esta fila SOLO puede pertenecer
                # a una fila que YA tenga su columna ancla abierta -nunca a una fila futura
                # que todavia no declaro la suya- asi que "el hueco mas chico gana" es
                # inseguro aca. Bug real encontrado validando este fix: Sierra Leone
                # (Y=325.1-337.1) tiene una fila secundaria propia "Leone/SLE/925"
                # (Y=351.6-363.6) que NO se solapa con ninguna fila vecina -el hueco
                # numerico a Singapur (8.5pt, la fila siguiente) resulta MENOR que el hueco
                # a Sierra Leone (14.5pt) por pura coincidencia de layout, pero Singapur no
                # tiene ninguna relacion real con esta fila- y terminaba fusionada ahi en
                # vez de en Sierra Leone. Fix: solo se difiere a la fila SIGUIENTE
                # (`pending_prefix`) si hay un SOLAPE REAL en Y con ella (asi se comporta el
                # sub-caso que SI necesita diferirse: la propia fila secundaria de Sierra
                # Leone frente a Seychelles, Y=319.1-331.1, solapa 6.0pt con la fila
                # principal de Sierra Leone que arranca despues, Y=325.1-337.1, mientras
                # todavia sigue activa la fila de OTRO pais). Si no hay solape real, se
                # fusiona directo con la fila activa, sin comparar huecos numericos.
                row_y0, row_y1 = _row_min_y0(row_sorted), _row_max_y1(row_sorted)
                next_row = rows[i + 1] if i + 1 < len(rows) else None
                overlaps_next = next_row is not None and min(row_y1, _row_max_y1(next_row)) > max(
                    row_y0, _row_min_y0(next_row)
                )
                if overlaps_next:
                    pending_prefix.extend(row_sorted)
                    continue
                if active_kind in ("table_row", "table_header"):
                    for line in row_sorted:
                        _nearest_cell(active_cells, line["bbox"][0])["text"].append(line["text"])
                    active_last_y1 = max(active_last_y1, row_y1) if active_last_y1 is not None else row_y1
                else:
                    pending_prefix.extend(row_sorted)
                continue
            elif active_kind in ("table_row", "table_header"):
                # Caso simetrico al de una sola linea (ver punto 5 del docstring), pero
                # con 2+ columnas envolviendo a la vez en la misma banda Y (ej. "Cayman
                # Islands" repetido en la columna de nombre de pais Y en la de nombre de
                # moneda al mismo tiempo) -group_into_rows() las agrupa en una sola fila
                # multi-celda sin codigo, que geometricamente podria ser sufijo de la fila
                # activa o prefijo de la fila siguiente. Misma decision: el hueco mas
                # chico gana.
                row_y0, row_y1 = _row_min_y0(row_sorted), _row_max_y1(row_sorted)
                gap_to_active = row_y0 - active_last_y1 if active_last_y1 is not None else 0.0
                next_row = rows[i + 1] if i + 1 < len(rows) else None
                if gap_to_active > TABLE_ROW_GAP_MAX and next_row is not None:
                    gap_to_next = _row_min_y0(next_row) - row_y1
                    if gap_to_next < gap_to_active:
                        pending_prefix.extend(row_sorted)
                        continue
                for line in row_sorted:
                    _nearest_cell(active_cells, line["bbox"][0])["text"].append(line["text"])
                active_last_y1 = max(active_last_y1, row_y1)
                bold_line = next((line for line in row_sorted if line.get("bold")), None)
                if bold_line is not None:
                    active_term_last_y1 = bold_line["bbox"][3]
            else:
                flush()
                active_kind = "table_header"
                active_cells = _new_cells(row_sorted)
                active_last_y1 = _row_max_y1(row_sorted)
            continue

        line = row_sorted[0]
        x0, y0, y1 = line["bbox"][0], line["bbox"][1], line["bbox"][3]

        if active_kind in ("table_row", "table_header"):
            min_cell_x0 = min(c["x0"] for c in active_cells)
            is_major_heading = bool(line.get("bold")) and line.get("max_size", 0) >= MAJOR_HEADING_MIN_SIZE
            if (
                x0 < min_cell_x0 - TABLE_LEFT_MARGIN_TOLERANCE
                or line.get("starts_with_footnote_marker")
                or is_major_heading
                or _note_precedes_major_heading(rows, i, min_cell_x0, line)
            ):
                # El caso "starts_with_footnote_marker" (punto 7 del docstring) cubre el
                # arranque de un bloque de notas al pie que empieza EXACTAMENTE en la misma
                # columna ancla que la tabla activa (ej. Zimbabwe) -ahi el chequeo de X de
                # arriba nunca dispara porque no hay corrimiento a la izquierda, asi que hace
                # falta esta señal independiente para no fusionar la nota con la fila vigente.
                # "is_major_heading" cubre el residuo de ese mismo bug (item 3b): cuando NO hay
                # nota de por medio (ej. edicion 20260418, donde Visa saco la nota de ZWG/ZWL),
                # el titulo de 26pt de la seccion siguiente ("Canadian Province Codes") caia
                # directo en esta misma rama sin ningun corte -se fusionaba entero (titulo +
                # parrafo intro) a la celda de pais de la ultima fila (Zimbabwe).
                flush()
                active_kind = "paragraph"
                active_cells = [{"x0": x0, "text": [line["text"]]}]
                paragraph_last_y1 = y1
                continue

            # Nombre largo envuelto en 2+ lineas (ver punto 5 del docstring): esta linea
            # suelta puede ser el sufijo de la fila activa O el prefijo de la fila
            # SIGUIENTE, que geometricamente se ven igual. Se decide comparando el hueco
            # vertical hasta cada lado -las lineas de una misma celda envuelta quedan
            # pegadas (~0pt), las filas distintas quedan separadas (~8.5pt en este manual)-
            # y quedandose con el lado mas cercano.
            gap_to_active = y0 - active_last_y1 if active_last_y1 is not None else 0.0
            next_row = rows[i + 1] if i + 1 < len(rows) else None
            if gap_to_active > TABLE_ROW_GAP_MAX and next_row is not None:
                gap_to_next = _row_min_y0(next_row) - y1
                if gap_to_next < gap_to_active:
                    pending_prefix.append(line)
                    continue

            _nearest_cell(active_cells, x0)["text"].append(line["text"])
            active_last_y1 = y1
            continue

        if active_kind == "paragraph":
            cell = active_cells[0]
            gap = y0 - paragraph_last_y1
            x_shift = abs(x0 - cell["x0"])
            if gap <= PARAGRAPH_MAX_GAP and x_shift <= PARAGRAPH_MAX_X_SHIFT:
                cell["text"].append(line["text"])
                paragraph_last_y1 = y1
            else:
                flush()
                active_kind = "paragraph"
                active_cells = [{"x0": x0, "text": [line["text"]]}]
                paragraph_last_y1 = y1
            continue

        active_kind = "paragraph"
        active_cells = [{"x0": x0, "text": [line["text"]]}]
        paragraph_last_y1 = y1

    if pending_prefix:
        # Red de seguridad: si quedo una linea diferida sin una fila siguiente que la
        # reclame (fin de pagina), no se descarta -se emite como parrafo suelto- aunque no
        # se pudo determinar a que fila pertenecia.
        flush()
        blocks.append(
            {
                "type": "paragraph",
                "page": page,
                "cells": ["\n".join(l["text"] for l in pending_prefix)],
            }
        )
    else:
        flush()
    return blocks


def _merge_continued_rows(blocks: list) -> list:
    """Fusiona filas '<codigo> (continued)' con la fila original del mismo codigo."""
    merged = []
    for block in blocks:
        if block["type"] == "table_row" and block["cells"]:
            m = CONTINUED_CODE.match(block["cells"][0].strip())
            if m:
                code = m.group(1).upper()
                target = next(
                    (
                        b
                        for b in reversed(merged[-CONTINUED_ROW_SEARCH_WINDOW:])
                        if b["type"] == "table_row"
                        and b["cells"]
                        and b["cells"][0].strip().upper() == code
                    ),
                    None,
                )
                if target is not None and len(target["cells"]) == len(block["cells"]):
                    for i in range(1, len(target["cells"])):
                        target["cells"][i] = target["cells"][i] + "\n" + block["cells"][i]
                    continue
        merged.append(block)
    return merged


def normalize_edition(edition_json_path: Path) -> dict:
    data = json.loads(edition_json_path.read_text())
    clean_lines = [line for line in data["lines"] if not is_noise(line)]

    blocks = []
    lines_by_page = {}
    for line in clean_lines:
        lines_by_page.setdefault(line["page"], []).append(line)

    # Estado que persiste ENTRE paginas (punto 8 del docstring de `build_blocks`): una vez
    # que se cruza al Glosario no hay vuelta atras, es la ultima seccion del documento en
    # las 9 ediciones.
    state = {"in_glossary": False, "glossary_header_emitted": False}
    for page in sorted(lines_by_page):
        # El orden de PyMuPDF sigue su propio agrupamiento interno de bloques, que no
        # siempre es fila-por-fila (ej. puede entregar una etiqueta de columna completa
        # -todas sus lineas- antes de pasar a la siguiente columna). Para que
        # group_into_rows() detecte bien que lineas comparten renglon, hace falta
        # reordenar explicitamente por posicion real en la pagina (Y primero, X despues).
        page_lines = sorted(lines_by_page[page], key=lambda l: (l["bbox"][1], l["bbox"][0]))
        rows = group_into_rows(page_lines)
        blocks.extend(build_blocks(rows, page, state))

    blocks = _merge_continued_rows(blocks)

    return {
        "manual": data["manual"],
        "edition_date": data["edition_date"],
        "source_file": data["source_file"],
        "num_lines_in": data["num_lines"],
        "num_lines_kept": len(clean_lines),
        "num_blocks": len(blocks),
        "blocks": blocks,
    }


def main():
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if not input_paths:
        print(f"No se encontraron JSON de entrada en {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for input_path in input_paths:
        result = normalize_edition(input_path)
        out_path = OUTPUT_DIR / input_path.name
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(
            f"{input_path.name}: {result['num_lines_in']} lineas -> "
            f"{result['num_lines_kept']} utiles -> {result['num_blocks']} bloques"
        )


if __name__ == "__main__":
    main()
