"""
Modulo 1 - Ingesta y Parseo (extraccion cruda) para el manual
international_full_service_pos_online_messages_processing_specifications.

Extrae, por cada edicion del PDF, cada LINEA de texto (no bloque) con su propio bounding
box exacto. No agrupamos lineas en filas, celdas o parrafos aqui -- eso es responsabilidad
del Modulo 2 (Normalizacion de bloques).

Este es el 6to manual del proyecto y el primero de naturaleza NARRATIVA -no tiene grillas
Position/Length/Format ni tablas de codigos como los 5 manuales anteriores (confirmado
explorando el PDF antes de decidir el enfoque: 232 paginas, solo 7 mencionan "Position"/
"TCR"/"Reserved" y son menciones incidentales dentro de prosa, no estructura tabular real).
Es un documento de especificacion de reglas de negocio/flujos de procesamiento, organizado en
secciones/subsecciones con parrafos -el usuario eligio explicitamente (2026-08-19) diffear a
nivel de parrafo/seccion con clasificacion IA en vez de tablas de campos. Modulo 1 arranca
igual que los otros 5 manuales (bbox+texto+tamano/fuente maxima por linea, sin asumir la
jerarquia de encabezados todavia) -esa jerarquia se investiga con datos reales al construir
el Modulo 2.
"""

import json
import sys
from pathlib import Path

import fitz

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from stage_runners import run_ingest_main


MANUAL_SLUG = "international_full_service_pos_online_messages_processing_specifications"
REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = REPO_ROOT / "visa" / "src" / "base_i" / MANUAL_SLUG
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"


def extract_pdf_lines(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    page_sizes = {(round(p.rect.width, 1), round(p.rect.height, 1)) for p in doc}
    if len(page_sizes) > 1:
        print(f"AVISO: {pdf_path.name} tiene tamanos de pagina distintos: {page_sizes}", file=sys.stderr)
    page_size = list(next(iter(page_sizes))) if page_sizes else None

    lines = []
    order = 0
    for page_index in range(len(doc)):
        page = doc[page_index]
        page_dict = page.get_text("dict")
        for block_no, block in enumerate(page_dict["blocks"]):
            if block.get("type") != 0:
                continue
            for line_no, line in enumerate(block["lines"]):
                spans = [s for s in line["spans"] if s["text"]]
                text = "".join(s["text"] for s in spans).strip()
                if not text:
                    continue
                x0, y0, x1, y1 = line["bbox"]
                max_font_size = round(max(s["size"] for s in spans), 1)
                fonts = sorted({s["font"] for s in spans})
                lines.append(
                    {
                        "line_id": f"p{page_index + 1}_b{block_no}_l{line_no}",
                        "order": order,
                        "page": page_index + 1,
                        "source_block": block_no,
                        "bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                        "text": text,
                        "max_font_size": max_font_size,
                        "fonts": fonts,
                    }
                )
                order += 1
    edition_date = pdf_path.stem.split(" - ")[0]
    return {
        "manual": MANUAL_SLUG,
        "edition_date": edition_date,
        "source_file": pdf_path.name,
        "num_pages": len(doc),
        "page_size": page_size,
        "num_lines": len(lines),
        "lines": lines,
    }


def main():
    run_ingest_main(SOURCE_DIR, OUTPUT_DIR, extract_pdf_lines)


if __name__ == "__main__":
    main()
