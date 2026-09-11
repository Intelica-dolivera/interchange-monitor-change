"""
Modulo 2 - Normalizacion de bloques para el manual base_ii_transactions_quick_reference.

Toma las lineas atomicas del Modulo 1 (bbox + tamano/fuente maxima por linea) y las
reconstruye en bloques con sentido. Forma de contenido de ESTE manual (investigada con
datos reales antes de escribir este modulo, no asumida por ser "otro manual BASE II" -mismo
criterio de no especular de siempre): es un LISTADO de referencia rapida, mucho mas simple
que los otros 4 manuales -no hay grilla Position/Length/Format ni fichas "Edit Criteria",
solo 2 niveles:

1. **Entrada de TC** (`section_heading`, reusa el mismo nombre de tipo que los manuales 3/4
   por consistencia de vocabulario en el pipeline, aunque aca no hay grilla+ficha adentro -
   solo filas): 12.0pt, x0=72, texto `"NN Nombre"` (2 digitos + espacio + nombre, ej.
   `"33 Multipurpose Message"`). Confirmado: exactamente 45 en las 8 ediciones (los 45 codigos
   TC/TCR de la tabla), consistente en toda la historia de ediciones disponible.
2. **Fila TCR** (`table_row`, 2 celdas): 10.5pt, layout de 2 columnas fijas -etiqueta TCR a
   x0=90 (ej. `"TCR 0"`, `"TCR 1-7"`, a veces vacio del lado descripcion) y descripcion a
   x0=144 (a veces ausente del todo -ej. TC 40 "Fraud Advice" en la edicion de referencia
   tiene 5 filas TCR sin ninguna descripcion). Reconstruccion geometrica por banda Y
   (`group_into_rows`, identica a la de los manuales 3/4 -incluido el mismo fallback de hueco
   minimo para wraps de la celda descripcion, confirmado con un caso real: TC 39 TCR 3 "VDAS
   Forms Data... Optional Representment/Second" envuelve a una 2da linea "Chargeback" con
   overlap de banda Y casi nulo pero hueco negativo/minimo, mismo patron ya visto y resuelto
   en los otros manuales).

**Separacion de tamanos de fuente confirmada limpia** (sin colisiones, verificado con datos
reales): el contenido real (TC/TCR) usa EXCLUSIVAMENTE 12.0pt/10.5pt; portada, aviso legal y
header/footer usan 30.0/16.0/10.0/9.0pt -ningun solapamiento en ninguna de las 8 ediciones. A
diferencia de los otros 4 manuales, no hace falta un titulo de tabla re-declarado por pagina
ni manejo especial de continuidad entre paginas para las entradas TC -son independientes.

**No hay clave de posicion/byte-offset en este manual** (a diferencia de los otros 4) -el
`Position`/`Positions` que servia de clave estable de emparejamiento en Modulo 3 de los otros
manuales no existe aca. Ademas, la etiqueta TCR NO es unica dentro de una entrada TC
(confirmado real: TC 33 "Multipurpose Message" tiene "TCR 0" repetido 9 veces con
descripciones distintas cada vez -son 9 tipos de mensaje distintos que comparten el mismo
TCR). Esto es un problema de diseno de MODULO 3 (que clave usar para emparejar filas entre
ediciones), no de Modulo 2 -Modulo 2 solo reconstruye los bloques tal cual aparecen, en
orden, sin resolver todavia como emparejarlos.

Filtrado de ruido por CONTENIDO+ADYACENCIA (mismo principio que los otros 4 manuales): texto
de header (2 lineas FIJAS, sin subtitulo de seccion variable -a diferencia de los otros
manuales, aca ambas lineas del header son literales constantes en las 8 ediciones, confirmado
con datos reales), fecha de pie, numero de pagina (digitos cerca del margen derecho en la
banda inferior), "Visa Confidential".

Cualquier linea que no matchee TC heading/TCR row cae a un `paragraph` generico (catch-all,
mismo principio de no descartar nada en silencio ya usado en los otros manuales) -no se
espera contenido asi en este manual (confirmado: 0 lineas a 10.5/12.0pt en las paginas de
portada/aviso legal en las 8 ediciones), pero sirve de red de seguridad visible si alguna
edicion futura o mas vieja rompe la asuncion.

**Bug real encontrado y arreglado en la 1ra validacion (2026-08-19), antes de reportar el
modulo como listo**: el fallback de "hueco minimo = wrap de celda" (`group_into_rows`,
heredado sin cambios de los otros 3 manuales) no chequeaba que las 2 lineas comparadas
estuvieran en la MISMA pagina. Al cruzar un salto de pagina, el Y de la pagina nueva arranca
chico (~50-70pt) mientras el `ref_y1` de la ultima fila de la pagina anterior esta cerca del
pie (~700-750pt) -el hueco resultante es NEGATIVO, que igual pasaba el umbral `<= 4.0` sin
querer, fusionando TODAS las filas siguientes de la seccion en un solo bloque ilegible hasta
el proximo TC heading. Confirmado real con un caso concreto: las 9 filas TCR de
`"33 Multipurpose Message"` que cruzan de la pagina 15 a la 16 se fusionaron en una sola,
perdiendo la fila/columna real de cada una. A diferencia de los manuales 3/4 (donde el titulo
de tabla se re-declara al tope de cada pagina y corta el buffer de grilla GRATIS via el
chequeo de tamano de fuente), este manual no redeclara nada entre paginas -el corte de pagina
explicito que aca hacia falta ahi no. Fix: `row_buffer` se corta SIEMPRE que la pagina cambie,
antes de siquiera evaluar el fallback de hueco.
"""

import json
import re
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_transactions_quick_reference"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"

HEADER_LINE1 = "BASE II Transactions – Quick-Reference"
HEADER_LINE2 = "BASE II Transactions Quick-Reference"
DATE_LINE = re.compile(r"^\d{1,2} [A-Za-z]+ 20\d{2}$")
PAGE_NUMBER_X_MIN = 500.0

TC_HEADING_FONT_SIZE = 12.0
TC_HEADING_PATTERN = re.compile(r"^\d{2}\s")
TCR_ROW_FONT_SIZE = 10.5

SAME_ROW_MIN_OVERLAP_RATIO = 0.5
CELL_X_MERGE_TOLERANCE = 3.0
GRID_ROW_GAP_MAX = 4.0


def _filter_noise(lines_by_page: dict) -> list:
    """Filtra header/pie por contenido+adyacencia (no por banda Y ciega) y devuelve la
    lista plana de lineas limpias, pagina por pagina en orden."""
    clean = []
    for page in sorted(lines_by_page):
        page_lines = sorted(lines_by_page[page], key=lambda l: (l["bbox"][1], l["bbox"][0]))
        noise_idx = set()

        for i, line in enumerate(page_lines):
            text = line["text"].strip()
            x0, y0 = line["bbox"][0], line["bbox"][1]
            if text in (HEADER_LINE1, HEADER_LINE2):
                noise_idx.add(i)
            elif text == "Visa Confidential" or DATE_LINE.match(text):
                noise_idx.add(i)
            elif y0 > 700 and x0 >= PAGE_NUMBER_X_MIN and re.match(r"^\d{1,4}$", text):
                noise_idx.add(i)

        clean.extend(page_lines[i] for i in range(len(page_lines)) if i not in noise_idx)
    return clean


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


def build_blocks(lines: list) -> list:
    blocks = []
    mode = None  # None | "tcr_rows"

    row_buffer = []
    active_paragraph = None
    PARAGRAPH_MAX_GAP = 10.0
    PARAGRAPH_MAX_X_SHIFT = 20.0

    def flush_row():
        nonlocal row_buffer
        if row_buffer:
            blocks.append(
                {
                    "type": "table_row",
                    "page": row_buffer[0]["page"],
                    "cells": ["\n".join(c["text"]) for c in _row_cells(row_buffer)],
                }
            )
        row_buffer = []

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

    for line in lines:
        text = line["text"].strip()
        page = line["page"]
        size = line["max_font_size"]
        x0, y0, y1 = line["bbox"][0], line["bbox"][1], line["bbox"][3]

        if size == TC_HEADING_FONT_SIZE and TC_HEADING_PATTERN.match(text):
            flush_row()
            flush_paragraph()
            mode = None
            blocks.append({"type": "section_heading", "page": page, "text": text})
            continue

        if size == TCR_ROW_FONT_SIZE:
            flush_paragraph()
            mode = "tcr_rows"
            if row_buffer:
                if row_buffer[-1]["page"] != page:
                    # Bug real encontrado validando este modulo (2026-08-19): sin este
                    # chequeo, el fallback de hueco mostraba "same_row=True" al cruzar un
                    # salto de pagina -el Y de la pagina nueva arranca chico (~50-70pt)
                    # mientras que `ref_y1` de la ultima fila de la pagina anterior esta
                    # cerca del pie (~700-750pt), dando un hueco NEGATIVO que igual pasaba
                    # el umbral `<= GRID_ROW_GAP_MAX` sin querer, fusionando filas de
                    # secciones enteras en un solo bloque ilegible (confirmado real: 9 filas
                    # TCR de "33 Multipurpose Message" fusionadas en una). A diferencia de
                    # los manuales 3/4, aca no hay titulo de tabla re-declarado por pagina
                    # que corte el buffer de forma natural -este manual necesita el corte de
                    # pagina explicito que alli era gratis.
                    flush_row()
                else:
                    ref_y0 = min(l["bbox"][1] for l in row_buffer)
                    ref_y1 = max(l["bbox"][3] for l in row_buffer)
                    overlap = min(ref_y1, y1) - max(ref_y0, y0)
                    min_height = min(ref_y1 - ref_y0, y1 - y0)
                    same_row = overlap > SAME_ROW_MIN_OVERLAP_RATIO * min_height
                    if not same_row and (y0 - ref_y1) <= GRID_ROW_GAP_MAX:
                        # No solapa banda Y, pero el hueco es minimo (o incluso levemente
                        # negativo -lineas envueltas con interlineado ajustado a veces se
                        # solapan un poco, confirmado real) -es el wrap de la celda
                        # descripcion, no una fila nueva (ver docstring). IMPORTANTE: este
                        # umbral por si solo NO distingue un salto de pagina real (hueco
                        # negativo de cientos de puntos, igual pasaria `<= GRID_ROW_GAP_MAX`
                        # sin querer -ese fue el bug real encontrado y arreglado, ver
                        # docstring del modulo) -lo que lo hace seguro aca es el chequeo de
                        # pagina de arriba, que ya corto el buffer ANTES de llegar a este
                        # fallback si la pagina cambio.
                        same_row = True
                    if not same_row:
                        flush_row()
            row_buffer.append(line)
            continue

        # Cualquier otra linea cierra el modo "tcr_rows" activo (no se espera contenido asi
        # en este manual, ver docstring) y cae al catch-all de parrafo generico.
        flush_row()
        mode = None
        if (
            active_paragraph is not None
            and page == active_paragraph["page"]
            and abs(x0 - active_paragraph["x0"]) <= PARAGRAPH_MAX_X_SHIFT
            and (y0 - active_paragraph["last_y1"]) <= PARAGRAPH_MAX_GAP
        ):
            active_paragraph["text"].append(text)
            active_paragraph["last_y1"] = y1
        else:
            flush_paragraph()
            active_paragraph = {"page": page, "x0": x0, "last_y1": y1, "text": [text]}

    flush_row()
    flush_paragraph()
    return blocks


def normalize_edition(edition_json_path: Path) -> dict:
    data = json.loads(edition_json_path.read_text())
    lines_by_page = {}
    for line in data["lines"]:
        lines_by_page.setdefault(line["page"], []).append(line)

    clean_lines = _filter_noise(lines_by_page)
    blocks = build_blocks(clean_lines)

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
