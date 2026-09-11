"""
Modulo 1 - Ingesta y Parseo (extraccion cruda) para el manual base_ii_clearing_edit_package_messages.

Identico en diseno al Modulo 1 de `base_ii_clearing_data_codes` (mismo esquema de salida,
mismo criterio de extraccion) -- la extraccion cruda no depende del "shape" de contenido de
cada manual, solo el parseo del Modulo 2 lo hace (ver catalogo de 8 tipos A/A'/A''/B/C/D/F/H
en local_memory/NOTES.md). Este manual es Tipo F ("fichas" de codigo de
error/edicion: `CODIGO` -> `TITULO` -> `Description:` -> `Action:` -> `Transaction Types:`,
mismo patron que las "Field ID cards" del Tipo A pero con otro vocabulario de labels), no
una grilla multi-columna como el Tipo B de `base_ii_clearing_data_codes` -- pero igual se
extrae a nivel de LINEA, no de bloque, por la misma razon documentada ahi: dejar la decision
de como agrupar lineas (en este caso, en fichas ficha por ficha, no en filas de tabla) para
el Modulo 2, con reglas explicitas y verificables, en vez de heredar el agrupamiento
generico e irreversible de `page.get_text("blocks")`.

Usamos page.get_text("dict") en vez de page.get_text("blocks") por la misma razon que en
`base_ii_clearing_data_codes`: el agrupamiento en bloques de PyMuPDF puede fusionar texto de
distintas partes logicas de la pagina que estan fisicamente cerca, y esa fusion es
irreversible (se pierde el bbox individual de cada linea).

Diferencia real con el Modulo 1 de `base_ii_clearing_data_codes` (encontrada muestreando este
manual antes de escribir el Modulo 2, ver local_memory/NOTES.md): en aquel manual la senal
estructural para reconstruir filas/celdas era puramente geometrica (posicion X/Y). Acá la
senal principal para distinguir un "codigo" real (ej. `V0027`, `000001-I`) de una linea de
texto cualquiera que por casualidad matchea el mismo patron de regex (confirmado: un
listado de MCCs envuelto en un parrafo produce una linea suelta `"5969"` que coincidiria
con un regex ingenuo de "codigo") es TIPOGRAFICA, no geometrica: las lineas de codigo real
usan tamano 20pt en `OpenSans-Bold` (el resto del texto usa 10-10.5pt), y las lineas de
titulo de ficha (todo mayusculas) usan la fuente monoespaciada `CourierNewPS-BoldMT` -ninguna
otra parte del documento usa esas combinaciones. Por eso este Modulo 1 SI guarda tamano y
nombre de fuente por linea (el de `base_ii_clearing_data_codes` no lo necesitaba y no lo
guarda) -sin este dato, el Modulo 2 de este manual no tendria como distinguir un codigo real
de un falso positivo de contenido.
"""

import json
import sys
from pathlib import Path

import fitz

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from stage_runners import run_ingest_main


MANUAL_SLUG = "base_ii_clearing_edit_package_messages"
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
                # Tamano maximo de fuente en la linea (senal de "es un codigo/titulo
                # grande" vs texto de cuerpo) y el set de fuentes usadas (senal de
                # "es el titulo en monoespaciada" vs cuerpo en OpenSans). Se guarda el
                # maximo, no un promedio, porque una linea puede mezclar un span en
                # negrita mas grande (ej. "Description:") con el resto en tamano normal
                # -el maximo es la senal mas fuerte y estable para clasificar la linea.
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
