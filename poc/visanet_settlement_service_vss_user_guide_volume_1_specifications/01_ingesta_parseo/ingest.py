"""
Modulo 1 - Ingesta y Parseo (extraccion cruda) para el manual
visanet_settlement_service_vss_user_guide_volume_1_specifications.

Extrae, por cada edicion del PDF, cada LINEA de texto (no bloque) con su propio bounding
box exacto. No agrupamos lineas en filas, celdas o parrafos aqui -- eso es responsabilidad
del Modulo 2 (Normalizacion de bloques).

Este es el 7mo manual del proyecto. Exploracion inicial (antes de disenar Modulo 2) muestra
una mezcla de AL MENOS 3 formas de contenido distintas dentro del mismo documento: prosa
narrativa (similar al 6to manual), tablas "Field Name/Description" de 2 columnas, y capturas
de reportes de ANCHO FIJO tipo terminal/mainframe (ej. "VSS-100-W Report", con columnas
alineadas por espacios, no por estructura de tabla real de PDF) -presentes SOLO en ediciones
viejas (92 de 204 paginas en la edicion 20220423, 0 en la edicion 20251017 -ese capitulo de
ejemplos parece haberse movido al "Volume 2, Reports", otro manual). El usuario confirmo
(2026-08-19) tratar ese contenido de forma generica en Modulo 2, sin parsear su estructura de
columnas.

**Hallazgo real durante esta exploracion, antes de decidir**: esas paginas de reportes estan
en paginas con orientacion PAISAJE (792x612 en vez de 612x792), y el texto del reporte en si
esta ROTADO 90 grados (confirmado via el vector `dir` de PyMuPDF: `(0.0, -1.0)` en vez del
`(1.0, 0.0)` horizontal normal de la prosa). Tratar esas lineas como texto horizontal normal
(el mismo mecanismo de parrafo por adyacencia geometrica X/Y usado en el resto del documento)
produciria basura ilegible, no solo "poca fidelidad" -por eso este modulo captura `dir` por
linea (ademas de bbox/texto/tamano/fuente, igual que los otros manuales), para que Modulo 2
pueda filtrar por rotacion explicitamente en vez de intentar interpretar geometria que no
aplica.

**Fix (2026-08-26, resolviendo [[pending-bug-fixes]] item 13's variante propia de este
manual)**: en las tablas rotadas `Field Name`/`Description`, PyMuPDF a veces fusiona la celda
de nombre de campo y la de descripcion en una sola `line` -mismo patron ya visto y resuelto en
el manual 1 (item 2, "Cook Islands"): 2 celdas logicamente distintas separadas por un unico
span de puro espacio en blanco, sin nada que las distinga salvo eso. Confirmado con un escaneo
completo del corpus (6 ediciones): siempre exactamente 3 spans (nombre, espacio, descripcion),
siempre 9.0pt uniforme, 9-10 instancias reales por edicion en las paginas de la tabla de
referencia real (ej. pag. 112 "CARDHOLDER BILLING AMT CUR" + "Clearing currency. On the VSS
reports..." fusionados, description vacia en Modulo 2 -exactamente el sintoma logueado en item
13). El mismo patron aparece ~47 veces mas por edicion en contenido rotado, pero SIEMPRE en
paginas que Modulo 2 ya descarta enteras (no llevan el literal "Field Name" -ver
`_extract_rotated_pairs` en normalize.py), asi que dividirlas o no es irrelevante para el
output final -no arriesga nada dividirlas tambien. **Acotado SOLO a lineas rotadas**
(`dir == ROTATED_DIR`): el mismo patron aparece tambien en texto horizontal, pero ahi son
2 casos ya conocidos y deliberadamente NO tocados por este fix -(a) lineas de tabla de
contenidos (dot-leader), que Modulo 2 ya filtra completas por texto, y (b) tablas horizontales
tipo "Report ID / Report Title" cuyo contenido fusionado es un residual ya aceptado
explicitamente (ver nota del asistente en el reporte de Modulo 7, "read as short report-name/
description table fragments... not a new bug worth chasing") -dividir lineas horizontales
arriesgaria reabrir ese scope ya cerrado sin necesidad, cuando el bug realmente logueado es
solo el de las tablas rotadas.
"""

import json
import re
import sys
from pathlib import Path

import fitz

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from stage_runners import run_ingest_main


MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_1_specifications"
REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = REPO_ROOT / "visa" / "src" / "vss" / MANUAL_SLUG
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"

ROTATED_DIR = (0.0, -1.0)
WHITESPACE_ONLY = re.compile(r"^\s+$")


def _split_rotated_line_segments(spans: list) -> list:
    """Divide los spans de una linea ROTADA en segmentos separados por cualquier span de
    solo espacio en blanco -senal de que 2 celdas logicamente distintas (nombre de campo /
    descripcion) quedaron fusionadas en una sola `line` de PyMuPDF, mismo mecanismo que
    `_split_line_segments` del manual 1 (ver docstring del modulo). Solo se llama para
    lineas rotadas -el texto horizontal no se toca."""
    segments = []
    current = []
    for span in spans:
        if WHITESPACE_ONLY.match(span["text"]):
            if current:
                segments.append(current)
                current = []
            continue
        current.append(span)
    if current:
        segments.append(current)
    return segments or [spans]


def _segment_bbox(spans: list) -> tuple:
    x0 = min(s["bbox"][0] for s in spans)
    y0 = min(s["bbox"][1] for s in spans)
    x1 = max(s["bbox"][2] for s in spans)
    y1 = max(s["bbox"][3] for s in spans)
    return x0, y0, x1, y1


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
                if not spans:
                    continue
                dir_x, dir_y = line.get("dir", (1.0, 0.0))
                is_rotated = (round(dir_x, 1), round(dir_y, 1)) == ROTATED_DIR
                segments = _split_rotated_line_segments(spans) if is_rotated else [spans]
                for seg_no, seg_spans in enumerate(segments):
                    text = "".join(s["text"] for s in seg_spans).strip()
                    if not text:
                        continue
                    x0, y0, x1, y1 = _segment_bbox(seg_spans) if is_rotated else line["bbox"]
                    max_font_size = round(max(s["size"] for s in seg_spans), 1)
                    fonts = sorted({s["font"] for s in seg_spans})
                    lines.append(
                        {
                            "line_id": f"p{page_index + 1}_b{block_no}_l{line_no}_s{seg_no}",
                            "order": order,
                            "page": page_index + 1,
                            "source_block": block_no,
                            "bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                            "text": text,
                            "max_font_size": max_font_size,
                            "fonts": fonts,
                            "dir": [round(dir_x, 3), round(dir_y, 3)],
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
