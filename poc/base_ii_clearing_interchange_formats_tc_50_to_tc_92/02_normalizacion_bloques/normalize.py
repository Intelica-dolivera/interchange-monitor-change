"""
Modulo 2 - Normalizacion de bloques para el manual
base_ii_clearing_interchange_formats_tc_50_to_tc_92.

Toma las lineas atomicas del Modulo 1 (bbox + tamano/fuente maxima por linea) y las
reconstruye en bloques con sentido. Mismo diseno que el 3er manual (`base_ii_clearing_
interchange_formats_tc_01_to_tc_49`), su hermano directo -misma serie de documento, mismos
DOS patrones mezclados dentro de cada seccion TC/TCR:

1. **Grilla "Record Layout"** (`Position | Field | Length | Format | Contents`, un row por
   campo) -reconstruccion geometrica por banda Y (`group_into_rows`).
2. **Fichas "Edit Criteria"** (nombre de campo + `Positions:`/`Length:`/`Format:` a la
   izquierda, `Description:`/`Note:`/`Values:`/`Mapping:` a la derecha) -maquina de estados
   secuencial por columna (izquierda/derecha via umbral de X), no agrupamiento por banda Y.

Todas las senales tipograficas y quirks del diseno del 3er manual se RE-VERIFICARON contra
datos reales de este 4to manual antes de escribir este modulo (no se copio a ciegas, mismo
criterio de no especular aplicado en todo el proyecto):

- Header/footer/TOC: `HEADER_LINE1` exacto confirmado (373 apariciones en la edicion mas
  reciente), formato de fecha de pie, "Visa Confidential", numero de pagina y dot-leader de
  TOC -todos identicos en forma a los del 3er manual.
- Encabezado de seccion (`^TC \\d`) a 26.0pt: 104 apariciones reales en la edicion mas
  reciente, todas genuinas. El 3er tamano de encabezado del 3er manual (20.0pt, secciones
  anidadas) se busco explicitamente en las 9 ediciones de ESTE manual (`^TC \\d` a 20.0pt) y
  dio CERO resultados en las 9 -no se incluye ese tamano aca, a diferencia del 3er manual
  (confirma que "mismo tipo de documento" no implica "mismos quirks", cada manual se valida
  por separado).
- Header de grilla: exactamente 150 apariciones de cada una de las 5 palabras a 9.5pt Bold
  en la edicion mas reciente, con el mismo quirk de `Length` en su propia banda Y debajo de
  `Field` (confirmado leyendo el layout real de una tabla, p.20).
- Fichas: labels izquierdos (`Positions?/Length/Format`) casi siempre a x0=75 (5308/5311 en
  la edicion mas reciente); labels derechos (`Description/Note/Values/Mapping`) a x0 en el
  rango 231-296, siempre >= `CARD_X_SPLIT`. Un x0=180.9 aislado (3 lineas, p.18) resulto ser
  una FIGURA ilustrativa de ejemplo ("Field Edit Criteria Example") en la introduccion, a
  8.1pt (no 9.0pt real) -no una ficha real; su contenido nunca activa `mode="card"` (el
  `Position:` de esa figura esta a x0=180.9, no matchea `x0 < CARD_X_SPLIT`) y cualquier
  `pending_right` que alcance a bufferear se limpia por el encabezado de seccion real (26pt)
  que sigue pocas lineas despues, antes de que exista una ficha real que pudiera
  contaminarse -confirmado leyendo el stream completo entre esa figura y la 1ra ficha real.
- Variante `"Values are:"` (en vez de `"Values:"`) confirmada real en ambos manuales (12
  apariciones en las 9 ediciones del 3er manual, presente tambien en este) -mismo
  comportamiento heredado sin cambios: el regex igual matchea `"Values"` como label y deja
  `"are:"` como resto, perdiendo cosmeticamente la palabra "Values" pero preservando integra
  la lista de valores enumerados que sigue (mismo caso ya aceptado en el 3er manual, no
  corrompe Position/Length/Format/Contents).

Documento procesado como un solo stream continuo, sin resetear estado por pagina.
"""

import json
import re
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_interchange_formats_tc_50_to_tc_92"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"

HEADER_LINE1 = "BASE II Clearing Interchange Formats, TC 50 to TC 92"
TOC_DOT_LEADER = re.compile(r"(\. ){4,}")
DATE_LINE = re.compile(r"^\d{1,2} [A-Za-z]+ 20\d{2}$")
PAGE_NUMBER_X_MIN = 500.0

GRID_HEADER_WORDS = ["Position", "Field", "Length", "Format", "Contents"]
GRID_HEADER_FONT_SIZE = 9.5
GRID_HEADER_OUTPUT_CELLS = ["Position", "Field Length", "Format", "Contents"]
GRID_ROW_FONT_SIZE = 9.0

# A diferencia del 3er manual, ESTE no tiene el 3er nivel de encabezado anidado a 20.0pt
# (buscado explicitamente `^TC \d` @ 20.0pt en las 9 ediciones, cero resultados en las 9 -
# ver docstring del modulo). Solo el tamano de seccion real, 26.0pt.
SECTION_HEADING_FONT_SIZES = {26.0}
SECTION_HEADING_PATTERN = re.compile(r"^TC \d")

GRID_LEGEND_PATTERN = re.compile(r"^Format:\s*AN\s*=")

CARD_LABEL_PATTERN = re.compile(r"^(Positions?|Length|Format):\s*(.*)$")
CARD_RIGHT_LABEL_PATTERN = re.compile(r"^(Description|Note|Values|Mapping)(?::\s*|\s+)(.*)$")
CARD_X_SPLIT = 150.0
# Tamano de fuente de un titulo de tabla-ficha (ej. "... Edit Criteria") -distinto del
# tamano real de nombre de campo (9.0pt, ver `GRID_ROW_FONT_SIZE`). Usado para excluir el
# item 11/[[pending-bug-fixes]] de `same_row_as_next_name` (ver su comentario mas abajo).
TITLE_PARAGRAPH_FONT_SIZE = 10.5
# Ficha redeclarada por salto de pagina en vez de continuar su `Values:`/`Note:` inline (ver
# item 12/[[pending-bug-fixes]], resuelto 2026-08-25). El nombre trae el sufijo literal
# "(continued)" del PDF fuente.
CARD_CONTINUATION_PATTERN = re.compile(r"\(continued\)\s*$", re.IGNORECASE)

SAME_ROW_MIN_OVERLAP_RATIO = 0.5
CELL_X_MERGE_TOLERANCE = 3.0
GRID_ROW_GAP_MAX = 4.0


def _filter_noise(lines_by_page: dict) -> list:
    """Filtra header/pie/TOC por contenido+adyacencia (no por banda Y ciega) y devuelve la
    lista plana de lineas limpias, pagina por pagina en orden."""
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
                noise_idx.add(i)

        clean.extend(page_lines[i] for i in range(len(page_lines)) if i not in noise_idx)
    return clean


def group_into_rows(lines: list) -> list:
    """Agrupa lineas consecutivas que comparten banda Y (misma fila visual) -usado solo
    para las filas de datos de la grilla, no para las fichas."""
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

    grid_header_cells = []
    grid_row_buffer = []
    # Guarda [[dev-phase-considerations]] punto 1: este manual procesa el documento como un
    # solo stream continuo, confiando en que el header de grilla se re-declara al tope de
    # cada pagina de continuacion para cortar `grid_row_buffer` antes de llegar al fallback
    # de hueco de abajo. Confirmado con un escaneo instrumentado de las 9 ediciones actuales
    # que esto nunca falla hoy (0 casos), pero es casualidad de formato del PDF, no una
    # garantia estructural -si alguna vez una tabla continua sin re-declarar el header, el
    # hueco Y entre la ultima fila de una pagina (~pie, Y grande) y la primera de la
    # siguiente (~tope, Y chico) da un numero NEGATIVO de cientos de puntos que igual pasaria
    # `<= GRID_ROW_GAP_MAX` sin querer (mismo bug ya encontrado y arreglado en el 5to manual,
    # `base_ii_transactions_quick_reference`). Contador expuesto en el JSON de salida
    # (`page_boundary_grid_guard_hits`) e impreso por `main()` para que, si algun dia se
    # dispara, sea visible en la corrida normal en vez de fusionar filas en silencio.
    page_boundary_grid_guard_hits = 0

    active_heading = None
    active_card = None
    active_card_right_label = None
    pending_right = {}
    pending_right_label = None

    active_paragraph = None
    PARAGRAPH_MAX_GAP = 10.0
    PARAGRAPH_MAX_X_SHIFT = 20.0
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
        nonlocal active_card, active_card_right_label
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
        pending_right = {}
        pending_right_label = None

    for line in lines:
        text = line["text"].strip()
        page = line["page"]
        size = line["max_font_size"]
        x0, y0, y1 = line["bbox"][0], line["bbox"][1], line["bbox"][3]

        # --- Encabezado de seccion (TC/CP/TCR) ---
        if size in SECTION_HEADING_FONT_SIZES and SECTION_HEADING_PATTERN.match(text):
            flush_all()
            mode = None
            active_heading = {"page": page, "text": text, "size": size}
            continue
        if active_heading is not None and size == active_heading["size"]:
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
            active_paragraph = {"page": page, "x0": x0, "last_y0": y0, "last_y1": y1, "text": [text], "size": size}
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
                    same_row = True
                if not same_row:
                    flush_grid_row()
            grid_row_buffer.append(line)
            continue
        if mode == "grid_rows":
            flush_grid_row()
            mode = None

        # --- Fichas "Edit Criteria" ---
        left_label = CARD_LABEL_PATTERN.match(text) if x0 < CARD_X_SPLIT else None
        right_label = CARD_RIGHT_LABEL_PATTERN.match(text) if x0 >= CARD_X_SPLIT else None
        # Item 11/[[pending-bug-fixes]] (resuelto 2026-08-25): un titulo de tabla-ficha (ej.
        # "Text Message Commercial Card - Passenger Itinerary Data - Leg-Specific Edit
        # Criteria") a veces se extrae partido en 2 fragmentos que comparten la MISMA banda Y
        # (mismo `source_block` de PyMuPDF, quirk de layout -confirmado, no un patron de
        # separador reconocible como el de otros fixes de este proyecto). Sin exclusion, el
        # 2do fragmento (a X0 bien a la derecha) se ve IDENTICO al caso legitimo que este
        # mecanismo detecta -la 1ra linea de `Description:` de un campo real compartiendo
        # fila con su propio nombre- y contamina la descripcion del campo siguiente. Se
        # distinguen por tamano de fuente: los titulos de tabla-ficha son 10.5pt, el nombre
        # real de un campo siempre es 9.0pt -confirmado con un escaneo completo de las 9
        # ediciones (18167 disparos legitimos a 9.0pt, 0 a 10.5pt que no sean este bug).
        same_row_as_next_name = (
            x0 >= CARD_X_SPLIT
            and active_paragraph is not None
            and page == active_paragraph["page"]
            and abs(y0 - active_paragraph["last_y0"]) < 3.0
            and active_paragraph.get("size") != TITLE_PARAGRAPH_FONT_SIZE
        )

        if left_label:
            label, rest = left_label.group(1), left_label.group(2)
            if label.startswith("Position"):
                flush_card()
                mode = "card"
                name = ""
                if (
                    active_paragraph is not None
                    and page == active_paragraph["page"]
                    and (y0 - active_paragraph["last_y1"]) <= CARD_NAME_MAX_GAP
                ):
                    name = " ".join(active_paragraph["text"]).strip()
                active_paragraph = None

                # Continuacion de una ficha ya cerrada por salto de pagina (item 12): el
                # nombre trae "(continued)" Y la posicion coincide EXACTO con la ultima
                # ficha ya emitida -se reabre esa ficha en vez de crear una nueva, para que
                # Modulo 3 la vea como 1 sola entidad (nunca coliciona por clave de
                # posicion). Si cualquiera de las 2 condiciones no se cumple, se cae al
                # camino normal (fila nueva) -mismo criterio de seguridad que el resto del
                # proyecto: la señal tiene que ser inequivoca, no se asume.
                is_continuation = (
                    CARD_CONTINUATION_PATTERN.search(name)
                    and blocks
                    and blocks[-1]["type"] == "field_card"
                    and blocks[-1]["positions"] == rest
                )
                if is_continuation:
                    active_card = blocks.pop()
                    # `pending_right` puede traer contenido REAL de la columna derecha (ej.
                    # "Note:  Values continued:" y las primeras lineas de valores) que llego
                    # ANTES que este "Positions:" en el orden de lineas del documento -el
                    # layout de 2 columnas hace que una linea de la columna derecha, mas
                    # arriba en Y que el nombre/Positions de la ficha, se procese primero
                    # (ver `same_row_as_next_name`). Sin fusionar esto se pierde en silencio
                    # -mismo tratamiento que ya recibe una ficha nueva mas abajo.
                    for key in ("description", "note", "values", "mapping"):
                        if pending_right.get(key):
                            active_card[key] = (active_card[key] + " " + pending_right[key]).strip()
                    active_card_right_label = pending_right_label
                else:
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
                elif label == "Format":
                    active_card["format"] = rest
            continue

        if right_label:
            label, rest = right_label.group(1), right_label.group(2)
            key = label.lower()
            if active_card is not None and not same_row_as_next_name:
                active_card[key] = (active_card[key] + " " + rest).strip()
                active_card_right_label = key
            else:
                pending_right[key] = (pending_right.get(key, "") + " " + rest).strip()
                pending_right_label = key
            continue

        if same_row_as_next_name:
            pending_right["description"] = (pending_right.get("description", "") + " " + text).strip()
            pending_right_label = "description"
            continue

        if x0 >= CARD_X_SPLIT and pending_right_label:
            pending_right[pending_right_label] += " " + text
            continue

        if x0 >= CARD_X_SPLIT and active_card is not None and active_card_right_label:
            active_card[active_card_right_label] += " " + text
            continue

        # --- Catch-all: parrafo narrativo ---
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
            active_paragraph = {"page": page, "x0": x0, "last_y0": y0, "last_y1": y1, "text": [text], "size": size}

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
