"""
Modulo 1 - Ingesta y Parseo (extraccion cruda) para el manual
base_ii_clearing_interchange_formats_tc_50_to_tc_92.

Extrae, por cada edicion del PDF, cada LINEA de texto (no bloque) con su propio bounding
box exacto. No agrupamos lineas en filas, celdas o parrafos aqui -- eso es responsabilidad
del Modulo 2 (Normalizacion de bloques).

Este es el 4to manual del proyecto, hermano directo del 3ro (`base_ii_clearing_interchange_
formats_tc_01_to_tc_49`): misma serie de documento "BASE II Clearing Interchange Formats",
misma estructura esperada (grillas Position/Field/Length/Format/Contents + fichas "Edit
Criteria"), solo que cubre los capitulos TC 50 a TC 92 en vez de TC 01 a TC 49. Arranca
identico al Modulo 1 de ese 3er manual -incluyendo capturar `max_font_size`/`fonts` por
linea, ya que el Modulo 2 de ese manual necesito esa senal tipografica para distinguir
seccion/tabla/ficha/cuerpo- pero sin asumir que los tamanos de fuente exactos ni el resto
del diseno de Modulo 2 se trasladan sin verificar: eso se confirma con datos reales recien
al construir el Modulo 2 de este manual (mismo criterio de no especular ya aplicado en los
3 manuales anteriores).
"""

import json
import sys
from pathlib import Path

import fitz

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from stage_runners import run_ingest_main


MANUAL_SLUG = "base_ii_clearing_interchange_formats_tc_50_to_tc_92"
REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = REPO_ROOT / "visa" / "src" / "base_ii" / MANUAL_SLUG
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
                # Igual que en los manuales 2 y 3: maximo (no promedio) porque una linea
                # puede mezclar un span en negrita mas grande con el resto en tamano
                # normal -el maximo es la senal mas fuerte y estable.
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
