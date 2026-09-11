"""
Modulo 1 - Ingesta y Parseo (extraccion cruda) para el manual
visanet_settlement_service_vss_user_guide_volume_2_reports.

8vo manual del proyecto. Companero del Volume 1 (7mo manual), pero con una estructura
mucho mas fragmentada: 5 apendices con formas de contenido distintas dentro del mismo
documento (grids Type A limpios, tablas Code/Description Type B, tablas cross-reference,
y paginas ROTADAS a nivel de PAGINA -no de texto embebido como en el Volume 1- que mezclan
reportes de muestra descartables con tablas Field Name/Description reales). Por decision
explicita del usuario (2026-08-19), este Modulo 1 separa la extraccion POR APENDICE desde
el inicio (a diferencia de los otros 7 manuales, donde Modulo 1 siempre file generico y la
diferenciacion por forma de contenido quedaba enteramente para Modulo 2).

**Hallazgo real durante la exploracion, antes de escribir este modulo**: a diferencia del
Volume 1 (donde el contenido rotado eran lineas de texto individuales con `dir=(0.0,-1.0)`
dentro de paginas por lo demas normales), en este manual la rotacion es una propiedad de
PAGINA completa (`page.rotation == 90`, un `/Rotate 90` real del PDF). PyMuPDF aplica esa
rotacion automaticamente en `page.get_text()` (texto plano, produce lectura correcta), pero
NO la aplica a los bounding boxes de `page.get_text("dict")` -- esos bbox siguen en el
sistema de coordenadas SIN rotar (mediabox original, ej. 612x792 aun cuando la pagina "logica"
es 792x612). Por eso este modulo captura `page_rotation` (0 o 90) por linea, ademas de `dir`
(igual que el Volume 1) y bbox crudo -- Modulo 2 necesitara ambas senales para saber si debe
interpretar bbox en modo horizontal normal o en modo "columna por x0, fila por y1" como ya
establecio el Volume 1 para su reconstruccion de pares rotados.

Los limites de cada apendice (A-E) se determinan dinamicamente por edicion leyendo el TOC
embebido del PDF (bookmarks "Appendix A:".."Appendix E:", nivel 2) -- confirmado estable en
titulo mismo texto/nivel a traves de las 7 ediciones aunque el numero de pagina cambie
edicion a edicion. Nada de rangos de pagina hardcodeados.

**Campo `starts_with_space` agregado retroactivamente (2026-08-19), durante validacion de
Modulo 2**: `text` siempre se guarda ya recortado (`.strip()`), lo cual pierde si la linea
CRUDA empezaba con un espacio real -Modulo 2 necesita esa senal para el merge de columnas
"fantasma" del Apendice E (headers partidos en 2 spans de texto por una rareza de renderizado
de 3 ediciones, ver `02_normalizacion_bloques/normalize.py`) sin poder re-derivarla de `text`
una vez recortado. No se guarda el texto crudo completo (duplicaria contenido en el JSON
innecesariamente) -solo el booleano que Modulo 2 realmente necesita.

**Campo `segments` agregado (2026-08-26, resolviendo [[pending-bug-fixes]] item 15)**: mismo
bug de fusion de PyMuPDF ya visto en el manual 1 (Cook Islands) y el manual 7 (pares rotados)
-2 celdas logicas distintas fusionadas en una sola `line` por un span de puro espacio en
blanco- pero aca con una complicacion nueva: el mismo sintoma geometrico (un span de solo-
espacio dentro de una linea) tambien aparece de forma INOFENSIVA en este manual, separando
CADA PALABRA de un titulo/leyenda de una sola celda real (ej. pagina 40 rotada, "Settlement
Warehouse Returned CRS Deferred" -un unico row-label, no 5 celdas- con un span de espacio
entre cada palabra; confirmado real con datos crudos, NO es el mismo bug). Dividir a ciegas
(como en los manuales 1/7) romperia este segundo caso. La distincion real solo puede hacerse
con la geometria de COLUMNAS de la tabla activa -que Modulo 1 no conoce (es dinamica, se
calcula en Modulo 2 por pagina/tabla)-, asi que en vez de decidir aca, este modulo se limita a
exponer los segmentos candidatos (divididos SOLO por spans de puro espacio, sin fusionar
nada) con su propio bbox recalculado -Modulo 2 decide, linea por linea de tabla, si dos
segmentos caen en bandas de columna REALMENTE distintas (division real) o en la misma (una
sola celda con espacios internos, se mantiene fusionada). `segments` se omite (lista de 1
elemento implicita, el texto/bbox ya reportados) cuando no hay ningun span interno de puro
espacio -la mayoria de las lineas.
"""

import json
import re
import sys
from pathlib import Path

import fitz

MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_2_reports"
REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = REPO_ROOT / "visa" / "src" / "vss" / MANUAL_SLUG
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"

APPENDIX_RE = re.compile(r"^Appendix ([A-E]):")
APPENDIX_KEYS = {"A": "appendix_a", "B": "appendix_b", "C": "appendix_c", "D": "appendix_d", "E": "appendix_e"}

WHITESPACE_ONLY = re.compile(r"^\s+$")


def _split_whitespace_segments(spans: list) -> list:
    """Divide los spans de una linea en segmentos separados por cualquier span de puro
    espacio en blanco (descartado, no forma parte de ningun segmento) -mecanismo puramente
    mecanico, sin decidir si la division es "real" (ver docstring del modulo, esa decision
    necesita geometria de columnas que solo Modulo 2 tiene)."""
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


def _segment_bbox(spans: list) -> list:
    x0 = min(s["bbox"][0] for s in spans)
    y0 = min(s["bbox"][1] for s in spans)
    x1 = max(s["bbox"][2] for s in spans)
    y1 = max(s["bbox"][3] for s in spans)
    return [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]


def get_appendix_ranges(doc) -> dict:
    """Devuelve {appendix_key: (first_page, last_page)} (1-indexed, inclusive), mas
    "front_matter" para todo lo que precede al Apendice A (portada, indice)."""
    starts = {}
    for level, title, page in doc.get_toc():
        if level != 2:
            continue
        m = APPENDIX_RE.match(title)
        if m:
            starts[APPENDIX_KEYS[m.group(1)]] = page

    missing = [k for k in APPENDIX_KEYS.values() if k not in starts]
    if missing:
        print(f"AVISO: apendices no encontrados en el TOC: {missing}", file=sys.stderr)

    ordered = sorted(starts.items(), key=lambda kv: kv[1])
    ranges = {}
    if ordered:
        first_appendix_start = ordered[0][1]
        if first_appendix_start > 1:
            ranges["front_matter"] = (1, first_appendix_start - 1)
    for i, (key, start_page) in enumerate(ordered):
        end_page = ordered[i + 1][1] - 1 if i + 1 < len(ordered) else doc.page_count
        ranges[key] = (start_page, end_page)
    return ranges


def page_to_appendix(page_num: int, ranges: dict) -> str | None:
    for key, (start, end) in ranges.items():
        if start <= page_num <= end:
            return key
    return None


def extract_pdf_lines(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    ranges = get_appendix_ranges(doc)

    by_appendix: dict[str, list] = {key: [] for key in list(ranges.keys())}
    order = 0
    for page_index in range(len(doc)):
        page = doc[page_index]
        page_num = page_index + 1
        appendix = page_to_appendix(page_num, ranges)
        if appendix is None:
            # Pagina fuera de cualquier rango detectado (no deberia pasar dado el TOC
            # continuo A-E, pero no se descarta silenciosamente si ocurre).
            appendix = "unassigned"
            by_appendix.setdefault(appendix, [])

        page_rotation = page.rotation
        page_dict = page.get_text("dict")
        for block_no, block in enumerate(page_dict["blocks"]):
            if block.get("type") != 0:
                continue
            for line_no, line in enumerate(block["lines"]):
                spans = [s for s in line["spans"] if s["text"]]
                text_raw = "".join(s["text"] for s in spans)
                text = text_raw.strip()
                if not text:
                    continue
                x0, y0, x1, y1 = line["bbox"]
                max_font_size = round(max(s["size"] for s in spans), 1)
                fonts = sorted({s["font"] for s in spans})
                dir_x, dir_y = line.get("dir", (1.0, 0.0))
                entry = {
                    "line_id": f"p{page_num}_b{block_no}_l{line_no}",
                    "order": order,
                    "page": page_num,
                    "page_rotation": page_rotation,
                    "source_block": block_no,
                    "bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                    "text": text,
                    "starts_with_space": text_raw[:1].isspace(),
                    "max_font_size": max_font_size,
                    "fonts": fonts,
                    "dir": [round(dir_x, 3), round(dir_y, 3)],
                }
                ws_segments = _split_whitespace_segments(spans)
                if len(ws_segments) > 1:
                    entry["segments"] = [
                        {"text": "".join(s["text"] for s in seg).strip(), "bbox": _segment_bbox(seg)}
                        for seg in ws_segments
                    ]
                by_appendix[appendix].append(entry)
                order += 1

    edition_date = pdf_path.stem.split(" - ")[0]
    appendix_page_ranges = {key: list(val) for key, val in ranges.items()}
    return {
        "manual": MANUAL_SLUG,
        "edition_date": edition_date,
        "source_file": pdf_path.name,
        "num_pages": len(doc),
        "appendix_page_ranges": appendix_page_ranges,
        "sections": {
            key: {"num_lines": len(lines), "lines": lines}
            for key, lines in by_appendix.items()
        },
    }


def main():
    pdf_paths = sorted(SOURCE_DIR.glob("*.pdf"))
    if not pdf_paths:
        print(f"No se encontraron PDFs en {SOURCE_DIR}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for pdf_path in pdf_paths:
        result = extract_pdf_lines(pdf_path)
        out_path = OUTPUT_DIR / f"{result['edition_date']}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        section_summary = ", ".join(
            f"{k}={v['num_lines']}" for k, v in result["sections"].items()
        )
        print(
            f"{pdf_path.name} -> {out_path.name} "
            f"({result['num_pages']} paginas) [{section_summary}]"
        )


if __name__ == "__main__":
    main()
