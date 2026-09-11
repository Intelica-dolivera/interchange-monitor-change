"""
Modulo 1 - Ingesta y Parseo (extraccion cruda) para el manual base_ii_clearing_data_codes.

Extrae, por cada edicion del PDF, cada LINEA de texto (no bloque) con su propio bounding
box exacto. No agrupamos lineas en filas, celdas o parrafos aqui -- eso es responsabilidad
del Modulo 2 (Normalizacion de bloques), que decide como combinarlas usando la posicion
geometrica de cada linea (mismo rango Y = misma fila / distinto Y consecutivo = mismo
parrafo envuelto).

Usamos page.get_text("dict") en vez de page.get_text("blocks") porque este ultimo ya
agrupa texto en "bloques" con un heuristico interno de PyMuPDF que puede fusionar, en una
sola unidad, texto de columnas distintas de una tabla que estan fisicamente cerca (ej.
"82\\nAll\\nDuplicate Processing" -- tres celdas distintas de tres columnas distintas,
fusionadas por PyMuPDF en un solo bloque porque estan cerca en la pagina). Ese
agrupamiento es irreversible una vez hecho: se pierde el bbox individual de cada linea.
Extrayendo a nivel de linea, esa decision de agrupamiento queda para el Modulo 2, con
reglas explicitas y verificables en vez de heredar un heuristico generico que no conoce
la semantica de estas tablas.

**Filtro de marcador de nota al pie (agregado 2026-08-20, investigando el alcance real del
bug #3 del TODO)**: en varias tablas de codigos de este manual (Country and Currency Codes,
Merchant Mailing CRB Region Codes, y otras -no es exclusivo de una sola tabla), un codigo con
nota al pie se renderiza como 2 SPANS en la MISMA linea de PyMuPDF: el codigo real a 9.0pt y el
digito de la nota (o una lista `"1,2"` para codigos con mas de una nota) a 6.75pt, sin ningun
separador entre ambos -confirmado con datos reales (`page.get_text("dict")`) en decenas de
casos a lo largo de las 9 ediciones: `'HRK'+'1'` -> `'HRK1'`, `'X'+'1'` -> `'X1'` (que ademas
colisiona visualmente con el codigo real y distinto `'X1'`, el de la nota `'1,2'` -> `'X11,2'`),
`'7'+'1'` -> `'71'`, etc. Modulo 1 anterior concatenaba todos los spans de una linea sin mirar
tamano de fuente, asi que el digito de nota quedaba fusionado al codigo real de forma
indistinguible para Modulo 2/3/4/5 -corrompiendo el valor del codigo, no solo un detalle
cosmetico (ver [[pending-bug-fixes]] item 3 / manual8 progress para el analisis completo).
Filtro: un span se descarta de la concatenacion de su linea si su tamano es menor a
`FOOTNOTE_MARKER_MAX_SIZE` (8.0, entre el 6.75pt real de la nota y el 9.0pt real del cuerpo,
confirmado sin excepciones en toda la muestra) Y su texto (sin espacios) matchea
`FOOTNOTE_MARKER_TEXT` (uno o mas digitos, opcionalmente separados por coma, ej. `"1"` o
`"1,2"`) -nunca letras, para no tocar el marcador `S` de "moneda de liquidacion" (alfabetico,
mismo tamano 6.75pt pero con significado real que puede variar entre ediciones). Si despues de
filtrar la linea queda vacia, se descarta la linea entera (ver `_segment_text`).

**Filtro de celdas fusionadas por un span de solo-espacio (agregado 2026-08-20, resolviendo
[[pending-bug-fixes]] item 2, "Cook Islands (the) CK")**: en varias tablas de este manual (no
solo `Country and Currency Codes`), PyMuPDF a veces agrupa 2 celdas de columnas DISTINTAS en una
sola `line` cuando quedan visualmente cerca en la misma fila -ej. `'Cook Islands (the)'` (nombre
de pais) + `' '` (span de solo espacio en blanco) + `'CK'` (codigo alfa), o `'Moroccan Dirham'` +
`' '` + `'MAD'` (nombre+codigo de moneda), o (fuera de esta tabla) `'Dispute Financial'` + `' '`
+ `'Dispute Response'` (2 celdas de una matriz), o un termino de glosario + su definicion.
Confirmado con un escaneo del corpus completo (`page.get_text("dict")`, filtrando las lineas de
"dot leader" del indice, que tambien usan un span de solo-espacio pero ya se descartan aparte en
Modulo 2): en TODOS los casos encontrados fuera del indice, un span cuyo texto es puro espacio en
blanco (no vacio, pero `.strip()` da string vacio) separa 2 piezas de contenido genuinamente
distintas -nunca aparece dentro de una sola celda real. Fix: `_split_line_segments()` corta los
spans de una `line` de PyMuPDF en 2+ segmentos independientes en cada span de solo-espacio (que
se descarta, no se incluye en ningun segmento) -cada segmento se emite como su propia linea, con
su propio bbox recalculado a partir de sus propios spans, en vez de la fusion original.

**Flag de negrita por linea (agregado 2026-08-25, resolviendo [[pending-bug-fixes]] item 1,
glosario sin parsear)**: se agrega el campo `bold` a cada linea de salida (ver
`_segment_is_bold`). Necesario porque el glosario de este manual es geometricamente el MISMO
patron de 2 columnas (termino a X0=72 / definicion a X0=216, ambos 9.0pt) que Modulo 2 ya sabe
reconstruir en fila+celdas para las tablas de codigos -la unica razon por la que colapsaba en
un bloque gigante es que el heuristico "¿es esto una fila nueva?" de Modulo 2 se basaba
solo en `CODE_LIKE` (un codigo corto en alguna celda), y un termino de glosario nunca matchea
eso. La negrita del termino (unica diferencia tipografica real entre columna clave y
definicion) es la señal que faltaba para generalizar el mismo mecanismo sin inventar un tipo
de bloque nuevo. Se agrega tambien `max_size` (tamano de fuente maximo entre los spans de la
linea) por la misma razon que Modulo 2 necesita distinguir el titulo de seccion real
"Glossary" (26pt) de su entrada homonima en la tabla de contenidos (12pt, mismo texto exacto y
misma negrita -no alcanzaba con texto+negrita solos para diferenciarlos).
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


MANUAL_SLUG = "base_ii_clearing_data_codes"
REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = REPO_ROOT / "visa" / "src" / "base_ii" / MANUAL_SLUG
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_ingesta_parseo"

FOOTNOTE_MARKER_MAX_SIZE = 8.0
FOOTNOTE_MARKER_TEXT = re.compile(r"^\d+(,\d+)*$")
WHITESPACE_ONLY = re.compile(r"^\s+$")
# Mismo patron que `TOC_DOT_LEADER` en Modulo 2 (normalize.py) -las lineas del indice
# ("Titulo. . . . . . 123") tambien traen un span de solo-espacio entre el titulo y los
# puntos de relleno, pero Modulo 2 filtra estas lineas COMPLETAS por este patron -si se
# dividieran aca, el fragmento "Titulo" solo ya no lo matchea y se cuela como contenido
# real. Se detecta ANTES de dividir (sobre el texto crudo completo, sin fusion de notas al
# pie) para preservarlas intactas, igual que antes de este fix.
TOC_DOT_LEADER = re.compile(r"(\. ){4,}")


def _split_line_segments(line: dict) -> list:
    """Divide los spans de una linea de PyMuPDF en segmentos separados por cualquier span
    de solo espacio en blanco -senal de que 2 celdas de columnas distintas quedaron
    fusionadas en una sola linea (ver docstring del modulo). Las lineas de indice (dot
    leader) se preservan sin dividir -ver comentario de `TOC_DOT_LEADER` arriba."""
    raw_text = "".join(span["text"] for span in line["spans"])
    if TOC_DOT_LEADER.search(raw_text):
        return [line["spans"]]

    segments = []
    current = []
    for span in line["spans"]:
        if WHITESPACE_ONLY.match(span["text"]):
            if current:
                segments.append(current)
                current = []
            continue
        current.append(span)
    if current:
        segments.append(current)
    return segments


def _segment_text(spans: list) -> str | None:
    kept = [
        span["text"]
        for span in spans
        if not (span["size"] < FOOTNOTE_MARKER_MAX_SIZE and FOOTNOTE_MARKER_TEXT.match(span["text"].strip()))
    ]
    text = "".join(kept).strip()
    return text or None


def _starts_with_footnote_marker(spans: list) -> bool:
    """True si el primer span de la linea es un marcador de nota al pie (mismo criterio de
    tamano/patron que `_segment_text`) seguido de prosa real -la forma en que este documento
    codifica el INICIO de un parrafo de definicion de nota (ej. '1' + ' From 1 January 2023,
    acquirers can submit...'). Distinto del caso ya cubierto por `_segment_text` de un digito
    de nota FUSIONADO al final de un codigo corto (ej. 'HRK'+'1') -ese vive en la ULTIMA
    posicion del span, no en la primera, asi que no dispara esta señal. Confirmado con un
    escaneo del corpus completo (9 ediciones): este patron (marcador chico al inicio + 15+
    caracteres de prosa a continuacion) aparece SIEMPRE en el arranque real de un bloque de
    nota al pie, nunca en un fragmento corto no relacionado -ver [[pending-bug-fixes]] item 3b.
    Usado por Modulo 2 para forzar el cierre de una tabla/encabezado activo antes de que el
    texto de la nota se fusione con la fila de datos vigente (ej. Zimbabwe, ultima fila de
    'Country and Currency Codes' antes del bloque de notas al pie de la tabla)."""
    if len(spans) < 2:
        return False
    first = spans[0]
    if not (first["size"] < FOOTNOTE_MARKER_MAX_SIZE and FOOTNOTE_MARKER_TEXT.match(first["text"].strip())):
        return False
    rest_text = "".join(s["text"] for s in spans[1:]).strip()
    return len(rest_text) >= 15


def _segment_is_bold(spans: list) -> bool:
    """True si el primer span con texto real de la linea es negrita (bit 16 de `flags`,
    convencion de PyMuPDF). Usado por Modulo 2 para reconocer el termino de una entrada de
    glosario (ver [[pending-bug-fixes]] item 1): en ese layout el termino se renderiza en
    negrita (`OpenSans-Bold`) y la definicion en fuente regular, mismo tamano (9.0pt) para
    ambos -asi que el tamano de fuente no sirve para distinguirlos, pero el flag de negrita
    si, sin excepciones confirmadas en la muestra."""
    for span in spans:
        if span["text"].strip():
            return bool(span["flags"] & 16)
    return False


def _segment_max_size(spans: list) -> float:
    return max(span["size"] for span in spans)


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
                for seg_no, segment in enumerate(_split_line_segments(line)):
                    text = _segment_text(segment)
                    if text is None:
                        continue
                    x0, y0, x1, y1 = _segment_bbox(segment)
                    lines.append(
                        {
                            "line_id": f"p{page_index + 1}_b{block_no}_l{line_no}_s{seg_no}",
                            "order": order,
                            "page": page_index + 1,
                            "source_block": block_no,
                            "bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                            "text": text,
                            "starts_with_footnote_marker": _starts_with_footnote_marker(segment),
                            "bold": _segment_is_bold(segment),
                            "max_size": round(_segment_max_size(segment), 2),
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
