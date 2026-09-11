"""
Modulo 1 - Ingesta y Parseo (extraccion cruda) para el manual
base_ii_clearing_interchange_formats_tc_01_to_tc_49.

Extrae, por cada edicion del PDF, cada LINEA de texto (no bloque) con su propio bounding
box exacto. No agrupamos lineas en filas, celdas o parrafos aqui -- eso es responsabilidad
del Modulo 2 (Normalizacion de bloques). Mismo diseno y misma razon que el Modulo 1 de
`base_ii_clearing_data_codes` (ver docstring de ese modulo para el detalle completo de por
que se usa `page.get_text("dict")` a nivel de linea en vez de `page.get_text("blocks")`):
la extraccion cruda no depende de la forma del contenido, solo de como PyMuPDF entrega el
texto, asi que arranca identica al Modulo 1 del primer manual.

Este es el 3er manual del proyecto (Tipo A -grids Position/Field/Length/Format, el target
central del proyecto: campos "Reserved" en rangos de posicion). Arranco igual que el primer
manual (solo bbox+texto, sin senal tipografica) por el mismo criterio de no especular ya
aplicado en el 2do manual -pero la investigacion real de Modulo 2 para ESTE manual encontro
que hace falta: a diferencia de los otros 2 manuales (un solo "shape" de contenido cada
uno), este mezcla DOS patrones distintos dentro de la MISMA seccion -una grilla "Record
Layout" (Position/Field/Length/Format/Contents, igual al Tipo B del primer manual) seguida
de "fichas" de campo "Edit Criteria" (Positions:/Length:/Format:/Description:/Note:/Values:,
similar en espiritu al Tipo F del 2do manual) que describen los MISMOS campos con mas
detalle. Distinguir seccion/tabla/ficha/cuerpo necesita mas de 2 niveles de tamano de letra
(confirmado con datos reales via `fitz` directo: 40pt numero de capitulo, 30pt titulo de
capitulo, 26pt encabezado de seccion TC/TCR, 10.5pt titulo de tabla/ficha, 9.5pt header de
grilla, 9.0pt contenido) -la altura del bbox usada para explorar antes de este fix era un
proxy impreciso (depende de ascendentes/descendentes, no del tamano real de fuente). Por eso
este Modulo 1 SI guarda `max_font_size`/`fonts` por linea, igual que el 2do manual -decision
tomada con datos reales, no de antemano.
"""

import json
import sys
from pathlib import Path

import fitz

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from stage_runners import run_ingest_main


MANUAL_SLUG = "base_ii_clearing_interchange_formats_tc_01_to_tc_49"
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
                # Igual que en base_ii_clearing_edit_package_messages: maximo (no promedio)
                # porque una linea puede mezclar un span en negrita mas grande con el resto
                # en tamano normal -el maximo es la senal mas fuerte y estable.
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
