"""
Modulo 2 - Normalizacion de bloques para el manual
base_ii_clearing_interchange_formats_tc_01_to_tc_49.

Toma las lineas atomicas del Modulo 1 (bbox + tamano/fuente maxima por linea) y las
reconstruye en bloques con sentido. A diferencia de los otros 2 manuales (un solo "shape"
de contenido cada uno), este mezcla DOS patrones distintos dentro de cada seccion TC/TCR:

1. **Grilla "Record Layout"** (`Position | Field | Length | Format | Contents`, un row por
   campo, compacta) -mismo tipo de tabla Tipo B que `base_ii_clearing_data_codes`, misma
   tecnica de reconstruccion geometrica por banda Y (`group_into_rows`).
2. **Fichas "Edit Criteria"** (nombre de campo + `Positions:`/`Length:`/`Format:` a la
   izquierda, `Description:`/`Note:`/`Values:`/`Mapping:` a la derecha) -describen los
   MISMOS campos que la grilla, con mas detalle. Layout de 2 columnas (izquierda ~x0=75,
   derecha ~x0=231), NO una grilla N-columna -- confirmado con datos reales que agrupar por
   banda Y ac치 produce parejas arbitrarias (ej. "Format: alphanumeric" quedaria en la misma
   fila que la mitad de una nota de OTRO campo, solo porque coinciden en Y por casualidad).
   Por eso las fichas se procesan con una maquina de estados SECUENCIAL separada por columna
   (izquierda/derecha via umbral de X), no con agrupamiento por banda Y como la grilla.

Ambos patrones describen los mismos campos (ver reference_pipeline-vs-technical-manuals en
la memoria del asistente) -Modulo 2 los deja como bloques separados (`table_row` / `field_card`),
sin enlazarlos todavia; enlazarlos por nombre+posicion es trabajo del Modulo 3 (mismo criterio
de separacion de responsabilidades ya usado en los otros 2 manuales: Modulo 2 reconstruye
bloques con sentido, Modulo 3 reconstruye/empareja entidades logicas).

Documento procesado como un solo stream continuo, sin resetear estado por pagina -misma
leccion aplicada en el 2do manual (evita de raiz la clase de bug "H0 (continued)" del primer
manual): tanto la grilla como las fichas pueden abarcar varias paginas, con su titulo
re-declarado al tope de cada pagina en la que continuan (mismo patron ya visto en los otros
2 manuales).

**Senales tipograficas reales usadas** (confirmadas con `fitz` directo antes de escribir el
parser, ver local_memory/NOTES.md): 40.0pt = numero de capitulo, 30.0pt = titulo de
capitulo, 26.0pt = encabezado de seccion (TC/CP/TCR, o un subtitulo narrativo generico -se
distinguen por texto, no por tamano: el encabezado de seccion real matchea `^TC \\d`), 10.5pt
Bold = titulo de tabla/ficha ("... Record Layout", "... Edit Criteria") o subtitulo, 9.5pt
Bold = header de columna de la grilla (las 5 palabras exactas `Position`/`Field`/`Length`/
`Format`/`Contents` -389 apariciones en la edicion de referencia, 0 falsos positivos/negativos
confirmados), 9.0pt = contenido de grilla y de fichas (mismo tamano para ambos, se
distinguen por CONTEXTO -modo activo- y por REGEX de etiqueta, no por tamano).

**Quirk real del header de grilla**: `Length` aparece en su PROPIA banda Y, debajo de
`Field`, no alineado con `Position`/`Field`/`Format`/`Contents` (layout real del PDF, no un
artefacto de extraccion) -por eso el header de grilla NO se arma por banda Y sino
recolectando, en orden de stream, las 5 palabras exactas a 9.5pt Bold hasta juntar las 5,
sea cual sea su Y individual.

**Filtrado de ruido por CONTENIDO+ADYACENCIA, no por banda Y ciega** (decision tomada
DESPUES de encontrar una colision real con datos reales, ver local_memory/NOTES.md): en
paginas con celdas muy envueltas (ej. una tabla `Values:` con columnas angostas), el
contenido real de la ultima fila puede imprimirse mas abajo que donde normalmente empieza el
pie de pagina (confirmado: contenido real a y0=789.6 en una pagina cuyo pie arranca a
y0=759.6 -un simple corte "y0 >= 750 es ruido" hubiera descartado esas celdas reales). En vez
de eso, el pie se filtra por CONTENIDO+POSICION (texto de fecha via regex, `"Visa
Confidential"` exacto, numero de pagina = digitos cortos cerca del margen derecho en la
banda inferior de la pagina -NO "la ultima linea de la pagina": confirmado con datos reales
que "Visa Confidential" a veces tiene `y0` 0.1-1.1pt mas alto que la fecha/numero de pagina
y por eso ordena despues, asi que asumir "es la ultima linea" fallaba) y el header por el
texto EXACTO de su 1ra linea (`"BASE II Clearing Interchange Formats, TC 01 to TC 49"`,
unico e inconfundible) mas la linea que la sigue inmediatamente en orden de pagina (el
subtitulo de seccion corriente, variable en texto pero siempre justo despues de la 1ra
linea).

**Quirk real 2 (encontrado corriendo el parser contra datos reales, no en la exploracion
previa)**: `Field` y `Length` NO son 2 columnas separadas -son un header de 2 lineas para
UNA sola columna ("cantidad de bytes del campo"): cada fila de datos solo trae UN numero
entre `Position` y `Format`, nunca dos. Se colapsan en una sola celda de salida
`"Field Length"`.

**Quirk real 3**: el titulo de la tabla se re-declara al tope de cada pagina en la que la
grilla continua (`"Transaction Data Record Layout"`, igual que en el manual 1) ANTES de que
se re-declare el header de columnas -no inmediatamente despues del ultimo row de la pagina
anterior. El modo "grilla" no puede asumir que la siguiente linea es siempre una fila de
datos o un header nuevo: se corta explicitamente en cuanto aparece una linea que no sea de
tamano 9.0pt (el tamano real, unico, de las filas de datos), dejando que esa linea (el
titulo re-declarado) caiga en el manejo generico de parrafo.
"""

import json
import re
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_interchange_formats_tc_01_to_tc_49"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"

HEADER_LINE1 = "BASE II Clearing Interchange Formats, TC 01 to TC 49"
TOC_DOT_LEADER = re.compile(r"(\. ){4,}")
DATE_LINE = re.compile(r"^\d{1,2} [A-Za-z]+ 20\d{2}$")
PAGE_NUMBER_X_MIN = 500.0

GRID_HEADER_WORDS = ["Position", "Field", "Length", "Format", "Contents"]
GRID_HEADER_FONT_SIZE = 9.5
# "Field" y "Length" son un header de 2 lineas para UNA sola columna (ver docstring,
# "Quirk real 2") -se emiten fusionados bajo esta etiqueta.
GRID_HEADER_OUTPUT_CELLS = ["Position", "Field Length", "Format", "Contents"]
GRID_ROW_FONT_SIZE = 9.0

# Bug real (encontrado disenando Modulo 3, no en la exploracion previa de Modulo 2): hay un
# 3er nivel de encabezado, mas chico, 20.0pt -no solo el 26.0pt calibrado originalmente-
# usado quando una seccion "grande" (26pt) engloba varios sub-registros distintos con su
# propia numeracion de Position independiente (ej. "TC 33 - TCR 0 Commercial Choice Select
# Reference Data Record" contiene adentro "TC 33 - TCR 0 BASE II Dispute Financial Status
# Advice", "TC 33 - TCR 1 ... (Cont'd)", "TC 33 - TCR 0 V.I.P. Full Service...", etc., cada
# uno a 20pt). Solo 6 apariciones en toda la edicion de referencia -acotado a esta seccion-
# pero cada una es una entidad real a emparejar por separado (mismo criterio: cada
# "TC N - TCR M ..." es su propia unidad, sin importar el tamano exacto del encabezado). El
# patron de texto (`^TC \d`) ya es suficientemente especifico como para no necesitar acotar
# el tamano a un valor unico -alcanza con exigir que sea uno de los tamanos de encabezado
# conocidos, no cualquier texto a cualquier tamano.
SECTION_HEADING_FONT_SIZES = {20.0, 26.0}
SECTION_HEADING_PATTERN = re.compile(r"^TC \d")

GRID_LEGEND_PATTERN = re.compile(r"^Format:\s*AN\s*=")

CARD_LABEL_PATTERN = re.compile(r"^(Positions?|Length|Format):\s*(.*)$")
# El ":" a veces falta en el PDF fuente (confirmado real, no artefacto de extraccion -sin
# ningun caracter de separacion alternativo, ni siquiera un espacio de mas: "Description
# The field must..." en vez de "Description: The field must...", 9 casos reales solo en la
# edicion de referencia, concentrados en 1 pagina -ej. p.91-). Solo se relajo del lado
# DERECHO (Description/Note/Values/Mapping): del lado IZQUIERDO (Positions/Length/Format)
# no hay ningun caso real, y relajarlo ahi generaria un falso positivo real -el campo
# `"Format Code"` (nombre de campo real, 7 apariciones) se leeria como la etiqueta
# `Format:` con resto "Code". La alternancia exige o bien ":" (con o sin espacio despues,
# permite `"Values:"` sola con resto vacio) o bien un espacio sin ":" (nunca ambos
# ausentes, evita matchear un prefijo de palabra por casualidad).
CARD_RIGHT_LABEL_PATTERN = re.compile(r"^(Description|Note|Values|Mapping)(?::\s*|\s+)(.*)$")
CARD_X_SPLIT = 150.0

SAME_ROW_MIN_OVERLAP_RATIO = 0.5
CELL_X_MERGE_TOLERANCE = 3.0
# Cuando la celda `Contents` envuelve a una 2da linea, esa linea a veces NO solapa la
# banda Y de la fila (las celdas de 1 sola linea -Position/FieldLength/Format- quedan mas
# arriba) -mismo quirk ya visto y resuelto en el Modulo 2 del manual 1 (Tipo B): el hueco
# entre lineas de una misma celda envuelta es minimo (~0pt, a veces hasta solapando
# levemente), mientras que el hueco entre filas de datos distintas es ~8.3pt (confirmado
# con datos reales de este manual, ej. p.79). Se usa como fallback cuando el solapamiento
# de banda Y ya dice "no es la misma fila".
GRID_ROW_GAP_MAX = 4.0


def _filter_noise(lines_by_page: dict) -> list:
    """Filtra header/pie/TOC por contenido+adyacencia (no por banda Y ciega, ver docstring
    del modulo) y devuelve la lista plana de lineas limpias, pagina por pagina en orden."""
    clean = []
    for page in sorted(lines_by_page):
        page_lines = sorted(lines_by_page[page], key=lambda l: (l["bbox"][1], l["bbox"][0]))
        noise_idx = set()

        for i, line in enumerate(page_lines):
            text = line["text"].strip()
            x0, y0 = line["bbox"][0], line["bbox"][1]
            if text == HEADER_LINE1:
                noise_idx.add(i)
                if i + 1 < len(page_lines) and page_lines[i + 1]["bbox"][3] < 50:
                    noise_idx.add(i + 1)
            elif text == "Visa Confidential" or DATE_LINE.match(text):
                noise_idx.add(i)
            elif TOC_DOT_LEADER.search(text):
                noise_idx.add(i)
            elif y0 > 700 and x0 >= PAGE_NUMBER_X_MIN and re.match(r"^\d{1,4}$", text):
                # Numero de pagina: NO siempre es la ultima linea en orden (y0,x0) de la
                # pagina -"Visa Confidential" a veces tiene un y0 0.1-1.1pt mas alto que la
                # fecha/numero de pagina, y ordena despues- asi que se detecta por
                # contenido+posicion (digitos cortos, cerca del margen derecho, banda
                # inferior de la pagina), no por ser el ultimo elemento de la lista.
                noise_idx.add(i)

        clean.extend(page_lines[i] for i in range(len(page_lines)) if i not in noise_idx)
    return clean


def group_into_rows(lines: list) -> list:
    """Agrupa lineas consecutivas que comparten banda Y (misma fila visual) -usado solo
    para las filas de datos de la grilla, no para las fichas (ver docstring)."""
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


def _row_cells(row_lines: list) -> list:
    row_sorted = sorted(row_lines, key=lambda l: l["bbox"][0])
    cells = []
    for line in row_sorted:
        x0 = line["bbox"][0]
        if cells and abs(cells[-1]["x0"] - x0) <= CELL_X_MERGE_TOLERANCE:
            cells[-1]["text"].append(line["text"])
        else:
            cells.append({"x0": x0, "text": [line["text"]]})
    return cells


def build_blocks(lines: list) -> tuple:
    blocks = []
    mode = None  # None | "grid_header" | "grid_rows" | "card"

    grid_header_cells = []  # acumulador de las 5 palabras del header de grilla
    grid_row_buffer = []  # lineas pendientes de la fila de grilla activa (banda Y)
    # Guarda [[dev-phase-considerations]] punto 1: este manual procesa el documento como un
    # solo stream continuo (ver docstring del modulo), confiando en que el header de grilla
    # se re-declara al tope de cada pagina de continuacion para cortar `grid_row_buffer`
    # antes de llegar a la comparacion de huecos de abajo. Confirmado con un escaneo
    # instrumentado de las 9 ediciones actuales que esto nunca falla hoy (0 casos), pero es
    # una casualidad de formato del PDF, no una garantia estructural del codigo -si alguna
    # vez una tabla continua sin re-declarar el header, el hueco Y entre la ultima fila de
    # una pagina (~pie, Y grande) y la primera de la siguiente (~tope, Y chico) da un numero
    # NEGATIVO de cientos de puntos que igual pasaria `<= GRID_ROW_GAP_MAX` sin querer (mismo
    # bug ya encontrado y arreglado en el 5to manual, `base_ii_transactions_quick_reference`).
    # Este contador queda en el JSON de salida (`page_boundary_grid_guard_hits`) e impreso
    # por `main()` para que, si algun dia se dispara, sea visible en la corrida normal del
    # pipeline en vez de fusionar filas en silencio.
    page_boundary_grid_guard_hits = 0

    active_heading = None
    active_card = None
    active_card_right_label = None  # ultima etiqueta de columna derecha activa (Description/Note/Values/Mapping)
    active_card_left_label = None  # ultima etiqueta de columna izquierda activa (Length/Format)
    active_card_left_block = None  # source_block de esa etiqueta, para reconocer sus lineas de wrap
    # "Length:"/"Format:" pueden envolver en 2+ lineas (ej. "Format: alphanumeric special" +
    # "character" -confirmado con datos reales, ver NOTES.md: el valor real es "alphanumeric
    # special character", partido en 2 lineas por ancho de columna). La linea de wrap no
    # tiene ninguna etiqueta que la identifique como tal (mismo problema que las
    # continuaciones de columna derecha sin "Note:"/etc., ver `active_card_right_label`), asi
    # que sin este chequeo caía en el catch-all de parrafo generico y se pegaba como prefijo
    # del NOMBRE del PROXIMO campo ("character Sender Name" en vez de "Sender Name"). Se
    # distingue una linea de wrap real de "es el nombre del proximo campo, tambien columna
    # izquierda sin etiqueta" por `source_block`: Modulo 1 ya agrupa el wrap dentro del MISMO
    # bloque fisico que su "Length:"/"Format:", mientras que el nombre del proximo campo es
    # necesariamente un bloque nuevo -señal exacta, no una heuristica de hueco en Y que puede
    # fallar por unos pocos puntos entre ediciones.
    # La 1ra linea de `Description:` de una ficha comparte banda Y con el nombre del campo
    # (misma "fila" visual) y por eso aparece en el stream ANTES de "Positions:" -a
    # diferencia de Note/Values/Mapping, que siempre llegan DESPUES (comparten banda Y con
    # Positions/Length, que ya activaron la ficha). Se bufferea aca hasta que "Positions:"
    # crea la ficha, y recien ahi se vuelca adentro.
    pending_right = {}
    pending_right_label = None

    active_paragraph = None  # {"page":, "x0":, "last_y1":, "text": [...]}
    PARAGRAPH_MAX_GAP = 10.0
    PARAGRAPH_MAX_X_SHIFT = 20.0
    # Hueco maximo entre el ultimo parrafo (nombre de campo, posiblemente envuelto en 2+
    # lineas) y la linea "Positions:" que lo confirma como tal -calibrado contra datos
    # reales: ~4.8-11.4pt entre el nombre y "Positions:" en los casos vistos.
    CARD_NAME_MAX_GAP = 20.0

    def flush_grid_row():
        nonlocal grid_row_buffer
        if grid_row_buffer:
            blocks.append(
                {
                    "type": "table_row",
                    "page": grid_row_buffer[0]["page"],
                    "cells": ["\n".join(c["text"]) for c in _row_cells(grid_row_buffer)],
                }
            )
        grid_row_buffer = []

    def flush_grid_header():
        nonlocal grid_header_cells
        if grid_header_cells:
            blocks.append(
                {
                    "type": "table_header",
                    "page": grid_header_cells[0]["page"],
                    "cells": GRID_HEADER_OUTPUT_CELLS,
                }
            )
        grid_header_cells = []

    def flush_heading():
        nonlocal active_heading
        if active_heading:
            blocks.append(
                {"type": "section_heading", "page": active_heading["page"], "text": active_heading["text"]}
            )
        active_heading = None

    def flush_card():
        nonlocal active_card, active_card_right_label, active_card_left_label, active_card_left_block
        if active_card:
            blocks.append(
                {
                    "type": "field_card",
                    "page": active_card["page"],
                    "name": active_card["name"],
                    "positions": active_card["positions"],
                    "length": active_card["length"],
                    "format": active_card["format"],
                    "description": active_card["description"],
                    "note": active_card["note"],
                    "values": active_card["values"],
                    "mapping": active_card["mapping"],
                }
            )
        active_card = None
        active_card_right_label = None
        active_card_left_label = None
        active_card_left_block = None

    def flush_paragraph():
        nonlocal active_paragraph
        if active_paragraph:
            blocks.append(
                {
                    "type": "paragraph",
                    "page": active_paragraph["page"],
                    "text": " ".join(active_paragraph["text"]).strip(),
                }
            )
        active_paragraph = None

    def flush_all():
        nonlocal pending_right, pending_right_label
        flush_grid_row()
        flush_grid_header()
        flush_heading()
        flush_card()
        flush_paragraph()
        # Defensivo: si quedo contenido buffereado sin que una ficha lo reclamara (ej. un
        # cambio de seccion/tabla inesperado a mitad de camino), no debe filtrarse a una
        # ficha futura no relacionada.
        pending_right = {}
        pending_right_label = None

    for line in lines:
        text = line["text"].strip()
        page = line["page"]
        size = line["max_font_size"]
        x0, y0, y1 = line["bbox"][0], line["bbox"][1], line["bbox"][3]
        source_block = line.get("source_block")

        # --- Encabezado de seccion (TC/CP/TCR) ---
        if size in SECTION_HEADING_FONT_SIZES and SECTION_HEADING_PATTERN.match(text):
            flush_all()
            mode = None
            active_heading = {"page": page, "text": text, "size": size}
            continue
        if active_heading is not None and size == active_heading["size"]:
            # Continuacion del titulo envuelto (ej. "... TCR 1 Additional" / "Data") -mismo
            # tamano EXACTO que el de esta instancia de encabezado, no un tamano global fijo
            # (hay 2 tamanos de encabezado validos, ver SECTION_HEADING_FONT_SIZES).
            active_heading["text"] += " " + text
            continue
        if active_heading is not None:
            flush_heading()

        # --- Header de grilla: las 5 palabras exactas, recolectadas por texto+tamano ---
        if text in GRID_HEADER_WORDS and size == GRID_HEADER_FONT_SIZE:
            if mode != "grid_header":
                flush_all()
                mode = "grid_header"
                grid_header_cells = []
            grid_header_cells.append({"x0": x0, "page": page, "text": text})
            if len(grid_header_cells) == len(GRID_HEADER_WORDS):
                flush_grid_header()
                mode = "grid_rows"
            continue

        # --- Fin de grilla: leyenda "Format: AN = Alphanumeric, ..." ---
        if GRID_LEGEND_PATTERN.match(text):
            flush_grid_row()
            mode = None
            flush_paragraph()
            active_paragraph = {"page": page, "x0": x0, "last_y0": y0, "last_y1": y1, "text": [text]}
            continue

        if mode == "grid_rows" and size == GRID_ROW_FONT_SIZE:
            if grid_row_buffer and grid_row_buffer[-1]["page"] != page:
                # Guarda punto 1 (ver docstring de build_blocks): corte explicito de pagina
                # ANTES del fallback de hueco, para que un salto de pagina nunca pueda colarse
                # como "mismo renglon" via un hueco negativo casual.
                page_boundary_grid_guard_hits += 1
                flush_grid_row()
            elif grid_row_buffer:
                ref_y0 = min(l["bbox"][1] for l in grid_row_buffer)
                ref_y1 = max(l["bbox"][3] for l in grid_row_buffer)
                overlap = min(ref_y1, y1) - max(ref_y0, y0)
                min_height = min(ref_y1 - ref_y0, y1 - y0)
                same_row = overlap > SAME_ROW_MIN_OVERLAP_RATIO * min_height
                if not same_row and (y0 - ref_y1) <= GRID_ROW_GAP_MAX:
                    # No solapa banda Y, pero el hueco es minimo -es el wrap de una celda
                    # `Contents`, no una fila nueva (ver GRID_ROW_GAP_MAX).
                    same_row = True
                if not same_row:
                    flush_grid_row()
            grid_row_buffer.append(line)
            continue
        if mode == "grid_rows":
            # Cualquier linea que no sea del tamano real de una fila de datos (9.0pt)
            # cierra la grilla -tipicamente el titulo de tabla re-declarado al tope de la
            # proxima pagina, ANTES de que se re-declare el header de columnas (ver
            # "Quirk real 3" en el docstring). Se deja caer al manejo generico de parrafo
            # en vez de asumir que es otra fila de datos.
            flush_grid_row()
            mode = None

        # --- Fichas "Edit Criteria" ---
        left_label = CARD_LABEL_PATTERN.match(text) if x0 < CARD_X_SPLIT else None
        right_label = CARD_RIGHT_LABEL_PATTERN.match(text) if x0 >= CARD_X_SPLIT else None
        # Si hay un parrafo activo compartiendo la misma fila visual (banda Y), es el
        # nombre del PROXIMO campo -contenido de columna derecha en esa misma fila le
        # pertenece a EL (con o sin etiqueta "Description:" -ver mas abajo, a veces falta
        # del todo, no solo el ":"), no a la ficha que sigue tecnicamente "activa" (no se
        # cierra hasta ver su propio "Positions:"). Sin este chequeo, el contenido del
        # campo N+1 se pegaba al de la ficha N -confirmado con datos reales de 2 formas
        # distintas: "Transaction Code"/"Transaction Code Qualifier" mezclando
        # descripciones etiquetadas, y "Customer Code.../Non-Fuel Product Code 1"
        # mezclando descripcion SIN etiqueta (ver abajo).
        same_row_as_next_name = (
            x0 >= CARD_X_SPLIT
            and active_paragraph is not None
            and page == active_paragraph["page"]
            and abs(y0 - active_paragraph["last_y0"]) < 3.0
        )
        # Mismo problema que arriba pero para Note/Values/Mapping (etiquetados), sin el
        # limite estrecho de banda Y: confirmado con datos reales (TC 33.A - CP 01 TCR 1,
        # "Mail/Phone/Electronic Commerce and Payment Indicator", nombre envuelto en 3
        # lineas) que cuando el nombre del PROXIMO campo se envuelve en varias lineas,
        # "Positions:" se corre varios puntos hacia abajo, pero el "Note:" de columna
        # derecha del proximo campo mantiene su posicion Y fija -terminando, tras el
        # ordenamiento por Y de este modulo, ANTES que el propio "Positions:" del campo al
        # que pertenece. Sin este chequeo generico, ese "Note:" se pegaba a la ficha
        # anterior (todavia "activa" porque no se cierra hasta ver su propio "Positions:"),
        # dejando la ficha correcta sin su nota y la anterior con una nota ajena.
        next_name_pending = (
            x0 >= CARD_X_SPLIT and active_paragraph is not None and page == active_paragraph["page"]
        )

        if left_label:
            label, rest = left_label.group(1), left_label.group(2)
            if label.startswith("Position"):
                flush_card()
                mode = "card"
                # El nombre del campo es el parrafo que se estaba acumulando justo antes
                # de esta linea (puede envolver en 2+ lineas, ej. "Additional
                # Authorization" / "Indicator") -no un buffer especulativo aparte: se
                # reusa el mecanismo general de parrafo (con su propio corte por hueco/
                # corrimiento en X), y solo se toma como nombre si esta lo bastante cerca
                # en Y de esta linea "Positions:". Si no hay parrafo activo cerca (caso
                # raro/inesperado), el nombre queda vacio en vez de corromperse con texto
                # no relacionado.
                name = ""
                if (
                    active_paragraph is not None
                    and page == active_paragraph["page"]
                    and (y0 - active_paragraph["last_y1"]) <= CARD_NAME_MAX_GAP
                ):
                    name = " ".join(active_paragraph["text"]).strip()
                active_paragraph = None
                active_card = {
                    "page": page,
                    "name": name,
                    "positions": rest,
                    "length": "",
                    "format": "",
                    "description": pending_right.get("description", ""),
                    "note": pending_right.get("note", ""),
                    "values": pending_right.get("values", ""),
                    "mapping": pending_right.get("mapping", ""),
                }
                active_card_right_label = pending_right_label
                pending_right = {}
                pending_right_label = None
            elif active_card is not None:
                if label == "Length":
                    active_card["length"] = rest
                    active_card_left_label = "length"
                elif label == "Format":
                    active_card["format"] = rest
                    active_card_left_label = "format"
                active_card_left_block = source_block
            continue

        if right_label:
            label, rest = right_label.group(1), right_label.group(2)
            key = label.lower()
            if active_card is not None and not next_name_pending:
                active_card[key] = (active_card[key] + " " + rest).strip()
                active_card_right_label = key
            else:
                # Llega antes que "Positions:" (comparte banda Y con el nombre del campo,
                # ver docstring) -se bufferea hasta que la ficha se cree.
                pending_right[key] = (pending_right.get(key, "") + " " + rest).strip()
                pending_right_label = key
            continue

        if same_row_as_next_name:
            # Descripcion SIN ninguna etiqueta -ni "Description:" ni "Description " sin
            # dos puntos, directamente texto crudo en la columna derecha (confirmado real,
            # ej. "Non-Fuel Product Code 1", p.196: el texto "This field contains a code
            # for the non-fuel product..." empieza sin ningun prefijo de etiqueta). Al
            # compartir fila con el nombre del proximo campo, se interpreta como su
            # Description implicita.
            pending_right["description"] = (pending_right.get("description", "") + " " + text).strip()
            pending_right_label = "description"
            continue

        # `pending_right` tiene prioridad sobre la ficha activa: si esta seteado, es que
        # ya empezamos a acumular contenido del PROXIMO campo (todavia sin su propio
        # "Positions:") y las continuaciones sin etiqueta le pertenecen a el, no a lo que
        # tecnicamente sigue activo en `active_card` -mismo caso que la Description misma
        # (ver arriba), pero para sus lineas de continuacion envueltas.
        if x0 >= CARD_X_SPLIT and pending_right_label:
            pending_right[pending_right_label] += " " + text
            continue

        if x0 >= CARD_X_SPLIT and active_card is not None and active_card_right_label:
            active_card[active_card_right_label] += " " + text
            continue

        # Wrap de "Length:"/"Format:" (ver `active_card_left_label` mas arriba): misma
        # `source_block` que la linea que puso la etiqueta -asi se distingue de el nombre del
        # PROXIMO campo, que es necesariamente un bloque nuevo aunque tambien sea columna
        # izquierda sin etiqueta.
        if (
            x0 < CARD_X_SPLIT
            and active_card is not None
            and active_card_left_label
            and source_block is not None
            and source_block == active_card_left_block
        ):
            active_card[active_card_left_label] = (active_card[active_card_left_label] + " " + text).strip()
            continue

        # --- Catch-all: parrafo narrativo (titulos de tabla/ficha, subtitulos, intro,
        # y el nombre de campo de la PROXIMA ficha, todavia no confirmado como tal hasta
        # que aparezca su "Positions:" -ver arriba). Un solo mecanismo para todo, sin
        # distinguir "columna izquierda"/"columna derecha" aca -esa distincion solo
        # importa dentro de una ficha ya activa (manejado arriba).
        flush_grid_row()
        if (
            active_paragraph is not None
            and page == active_paragraph["page"]
            and abs(x0 - active_paragraph["x0"]) <= PARAGRAPH_MAX_X_SHIFT
            and (y0 - active_paragraph["last_y1"]) <= PARAGRAPH_MAX_GAP
        ):
            active_paragraph["text"].append(text)
            active_paragraph["last_y0"] = y0
            active_paragraph["last_y1"] = y1
        else:
            flush_paragraph()
            active_paragraph = {"page": page, "x0": x0, "last_y0": y0, "last_y1": y1, "text": [text]}

    flush_all()
    return blocks, page_boundary_grid_guard_hits


def normalize_edition(edition_json_path: Path) -> dict:
    data = json.loads(edition_json_path.read_text())
    lines_by_page = {}
    for line in data["lines"]:
        lines_by_page.setdefault(line["page"], []).append(line)

    clean_lines = _filter_noise(lines_by_page)
    blocks, page_boundary_grid_guard_hits = build_blocks(clean_lines)

    return {
        "manual": data["manual"],
        "edition_date": data["edition_date"],
        "source_file": data["source_file"],
        "num_lines_in": data["num_lines"],
        "num_lines_kept": len(clean_lines),
        "num_blocks": len(blocks),
        "page_boundary_grid_guard_hits": page_boundary_grid_guard_hits,
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
        guard_hits = result["page_boundary_grid_guard_hits"]
        guard_note = f" [!] guarda de salto de pagina disparada {guard_hits} vez(es)" if guard_hits else ""
        print(
            f"{input_path.name}: {result['num_lines_in']} lineas -> "
            f"{result['num_lines_kept']} utiles -> {result['num_blocks']} bloques{guard_note}"
        )


if __name__ == "__main__":
    main()
