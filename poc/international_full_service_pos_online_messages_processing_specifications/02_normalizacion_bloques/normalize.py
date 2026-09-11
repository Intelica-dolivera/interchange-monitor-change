"""
Modulo 2 - Normalizacion de bloques para el manual
international_full_service_pos_online_messages_processing_specifications.

Toma las lineas atomicas del Modulo 1 y las reconstruye en bloques con sentido. Forma de
contenido de ESTE manual (investigada con datos reales antes de escribir el modulo, ver
docstring de `ingest.py`): documento NARRATIVO de reglas de negocio/flujos de procesamiento,
sin grillas Position/Length/Format -el usuario eligio explicitamente (2026-08-19) diffear a
nivel de PARRAFO/SECCION con clasificacion IA (Modulo 5) en vez de construir una maquina de
extraccion de tablas para este manual.

**Jerarquia de encabezados confirmada con datos reales**: 5 tamanos de fuente en juego -40.0pt
numero de capitulo ("Chapter N"), 30.0pt titulo de capitulo (tambien usado en portada y en el
titulo "Contents" de la TOC), 26.0pt/20.0pt/14.0pt tres niveles reales de encabezado de
seccion anidados (confirmado 0 colisiones con contenido de la TOC, que usa 10.0/12.0pt). Solo
los 3 niveles reales (26/20/14pt) se capturan como `section_heading` (con un campo `level`
1/2/3 para contexto) -igual que en los otros manuales, el stream queda FLAT (sin arbol de
verdad, ver Modulo 3 de los otros manuales: nunca se construyo jerarquia real, solo texto de
titulo unico + orden de aparicion) por el mismo criterio de no sobre-disenar sin necesidad
demostrada. `Chapter N`/titulo de capitulo (40/30pt) NO se capturan como heading propio -caen
al parrafo generico (ver mas abajo), consistente con como los otros manuales tratan esas 2
lineas como principio de capitulo, no como seccion diffeable en si misma.

**Contenido bajo 9.0pt es RUIDO de diagrama/glifo de vineta, no prosa real** -confirmado
leyendo muestras reales: 8.3pt/7.3pt/6.4-6.9pt son fragmentos de flowcharts/diagramas
("Merchant", "Acquirer", "(0100 or 0200)", "0100 Auth Request") dispersos por la pagina, no
oraciones; 8.0pt es EXCLUSIVAMENTE el glifo de vineta ("l"/"n", 698 apariciones, el texto real
de cada item de la lista esta en una linea separada a 10.5pt). Se descarta como ruido -es
ruido puramente decorativo/estructural, no contenido a rastrear.

**Limitacion aceptada, consecuencia directa de la decision del usuario (2026-08-19)**: hay
contenido REAL con forma tabular en 9.0-9.7pt (ej. una matriz "Transaction Type" x "Message
Type" con celdas Yes/No, y listas de reglas de conversion de campo tipo "Fld 49 = 392") que
este modulo NO reconstruye como tabla -se captura con el MISMO mecanismo generico de parrafo
por adyacencia geometrica que el resto de la prosa, lo que puede producir texto entreverado
(columnas de una tabla ancha mezclandose en una sola "oracion") en vez de una tabla legible.
Aceptado a proposito: el usuario eligio explicitamente diffear a nivel de parrafo/seccion, no
construir una maquina de extraccion de tablas para este manual -el contenido real NO se pierde
(sigue estando en el bloque de parrafo), solo puede leerse desprolijo en casos puntuales.

Filtrado de ruido por CONTENIDO+ADYACENCIA (mismo principio que los otros 5 manuales): header
de 2 lineas (1ra constante, 2da variable -subtitulo de capitulo actual, filtrada por
adyacencia), fecha de pie, numero de pagina, "Visa Confidential", TOC (dot-leader).

Parrafos reconstruidos por adyacencia geometrica (mismo mecanismo "catch-all" ya usado en los
otros 5 manuales, aca es el mecanismo PRINCIPAL en vez de un caso de borde): mismo x0 (dentro
de tolerancia) y hueco vertical chico entre lineas consecutivas = mismo parrafo: distinto x0 o
hueco grande = parrafo nuevo.
"""

import json
import re
import sys
from pathlib import Path

MANUAL_SLUG = "international_full_service_pos_online_messages_processing_specifications"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"

HEADER_LINE1 = "Full Service POS Online Messages – Processing Specifications (International)"
TOC_DOT_LEADER = re.compile(r"(\. ){4,}")
DATE_LINE = re.compile(r"^\d{1,2} [A-Za-z]+ 20\d{2}$")
PAGE_NUMBER_X_MIN = 500.0

HEADING_LEVELS = {26.0: 1, 20.0: 2, 14.0: 3}
HEADING_FONT_SIZES = set(HEADING_LEVELS)
MIN_CONTENT_FONT_SIZE = 9.0  # por debajo: ruido de diagrama/glifo de vineta, ver docstring

PARAGRAPH_MAX_GAP = 10.0
PARAGRAPH_MAX_X_SHIFT = 20.0


def _filter_noise(lines_by_page: dict) -> list:
    """Filtra header/pie/TOC por contenido+adyacencia y devuelve la lista plana de lineas
    limpias, pagina por pagina en orden."""
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
            elif line["max_font_size"] < MIN_CONTENT_FONT_SIZE:
                noise_idx.add(i)

        clean.extend(page_lines[i] for i in range(len(page_lines)) if i not in noise_idx)
    return clean


def build_blocks(lines: list) -> list:
    blocks = []
    active_heading = None
    active_paragraph = None

    def flush_heading():
        nonlocal active_heading
        if active_heading:
            blocks.append(
                {
                    "type": "section_heading",
                    "page": active_heading["page"],
                    "level": HEADING_LEVELS[active_heading["size"]],
                    "text": active_heading["text"],
                }
            )
        active_heading = None

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

        if size in HEADING_FONT_SIZES:
            if active_heading is not None and size == active_heading["size"] and page == active_heading["page"]:
                # Continuacion de un titulo envuelto en 2+ lineas -mismo tamano EXACTO,
                # misma pagina.
                active_heading["text"] += " " + text
                continue
            flush_heading()
            flush_paragraph()
            active_heading = {"page": page, "size": size, "text": text}
            continue

        if active_heading is not None:
            flush_heading()

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

    flush_heading()
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
