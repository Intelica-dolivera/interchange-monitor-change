"""
Modulo 3 - Emparejamiento de bloques para el manual base_ii_clearing_data_codes.

Toma los bloques planos del Modulo 2 (secuencia de `paragraph`/`table_header`/`table_row`
por pagina) y hace dos cosas que el Modulo 2 no hace: (a) reconstruye la entidad real que
hay que comparar edicion a edicion -una "tabla" logica, que puede repetir su titulo y su
header en cada pagina en la que continua- y (b) empareja esas tablas y sus filas entre dos
ediciones consecutivas.

Diseno (ver discusion completa en local_memory/NOTES.md):

1. Reconstruccion de tablas (`extract_tables`): se recorre la lista de bloques en orden de
   documento. Cada `paragraph` se guarda como "titulo pendiente" (se sobreescribe con el
   ultimo visto, no se acumulan). Cuando aparece un `table_header`, se compara su titulo
   pendiente (normalizado) contra el de la tabla activa: si coincide, es la MISMA tabla
   continuando en una pagina nueva (confirmado empiricamente: el titulo y el header de una
   tabla se re-declaran al tope de cada pagina en la que continua, ej. "Country and
   Currency Codes" en las paginas 119-131); si no coincide (o no hay tabla activa), se
   cierra la tabla anterior y arranca una nueva. Los `table_row` se acumulan en la tabla
   activa. El titulo es la senal primaria de continuidad (no el contenido del header en
   si), porque es mas estable frente a diferencias menores de extraccion entre paginas.

1b. Filtro de tablas fantasma: un `table_header` que nunca junta ninguna `table_row` antes
   del siguiente limite se descarta (no es una tabla real, es el mismo falso positivo de
   parrafos con viñetas mal clasificados como header de tabla que ya se documento en el
   Modulo 2 -ej. `['l', 'Draft Data: TCR 5, Positions 145-148']`-). Sin este filtro estas
   entradas fantasma (0 filas) generaban ruido real en el emparejamiento: tablas
   "agregadas"/"eliminadas"/"renombradas" espurias entre parrafos narrativos que por
   casualidad tienen texto parecido de una edicion a otra.

1c. Fusion de segmentos con el mismo titulo dentro de una misma edicion
   (`_coalesce_same_title`): en ediciones mas viejas (confirmado en `20230415`), un nombre
   de pais largo que envuelve en varias lineas (ej. "Bolivia (Plurinational State of)")
   ocasionalmente rompe el agrupamiento geometrico del Modulo 2 y un fragmento de esa
   linea sale como `paragraph` huerfano en vez de fusionarse a la fila activa. Como
   `pending_title` se sobreescribe con CUALQUIER parrafo visto (no solo titulos reales),
   ese fragmento ("(the)", "Herzegovina", "Miquelon"...) contamina momentaneamente el
   titulo pendiente y la tabla "Country and Currency Codes" se corta en 2-4 segmentos
   separados aunque el titulo real siga apareciendo correctamente pagina a pagina despues.
   Los datos en si NO se pierden (los ~190-200 paises siguen ahi, solo repartidos en varios
   objetos de tabla) — el problema es que `match_tables` los indexa en un diccionario por
   `title_norm`, y con 2+ tablas con el mismo titulo en la misma edicion, el diccionario se
   pisa y solo sobrevive la ULTIMA (en `20230415`, eso descartaba 194 de 198 filas antes de
   emparejar, generando ~250 "filas agregadas" espurias contra la edicion siguiente). Fix:
   antes de emparejar, se fusionan todas las tablas de una misma edicion que comparten
   `title_norm` en una sola (concatenando filas en orden de documento). No se investigo ni
   se arreglo la causa geometrica de fondo (por que ese pais en particular se corta) porque
   no hace falta para que el emparejamiento sea correcto — coalescer por titulo alcanza.

2. Identidad de fila dentro de una tabla (`_row_code`): la primera celda de cada
   `table_row`, normalizada (upper + strip). Es el equivalente, para tablas de codigos, al
   principio ya establecido en el proyecto de matchear por clave estable (posicion/numero
   de campo) en vez de por nombre difuso (ver reference_pipeline-vs-technical-manuals en la
   memoria del asistente) - el codigo es la clave estable de esta familia de tablas.
   Codigos duplicados dentro de la misma tabla/edicion (no deberian existir, pero si
   aparecen por algun caso de extraccion no visto) se detectan y se reportan aparte en vez
   de sobreescribirse silenciosamente.

3. Emparejamiento de tablas entre 2 ediciones (`match_tables`): primero exacto por titulo
   normalizado; los titulos que no matchean exacto se intentan por similitud de texto
   (`difflib.SequenceMatcher`, umbral 0.85) para detectar tablas renombradas, siguiendo el
   mismo patron que el pipeline de referencia usa para nombres de Program/Descriptor. Lo
   que no matchea ni exacto ni fuzzy queda como tabla agregada/eliminada.

4. Emparejamiento de filas dentro de cada tabla emparejada (`match_rows`): por codigo
   exacto. Codigos presentes en ambas ediciones son "matched" (Modulo 4 decide si su
   contenido cambio); solo en la edicion vieja = removido; solo en la nueva = agregado.
   Se incluye `header_a`/`header_b` de cada tabla emparejada en la salida (no solo las
   filas) para que Modulo 4 pueda etiquetar por nombre de columna cual celda cambio, en
   vez de solo por indice numerico.

Alcance: procesa pares de ediciones CONSECUTIVAS (las 9 ediciones de este manual dan 8
pares). Se puede llamar `match_edition_pair()` directamente con cualquier par si se necesita
comparar ediciones no consecutivas.
"""

import difflib
import json
import re
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_data_codes"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"

FUZZY_TITLE_THRESHOLD = 0.85
WHITESPACE = re.compile(r"\s+")


def _normalize_title(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip().casefold()


def _row_code(row_cells: list) -> str:
    return WHITESPACE.sub(" ", row_cells[0]).strip().upper()


def extract_tables(blocks: list) -> list:
    """Reconstruye tablas logicas (titulo + header + filas) a partir de bloques planos."""
    tables = []
    pending_title = None
    current = None

    def close_current():
        nonlocal current
        if current is not None:
            tables.append(current)
        current = None

    for block in blocks:
        if block["type"] == "paragraph":
            pending_title = block["cells"][0]
            continue

        if block["type"] == "table_header":
            title = pending_title
            title_norm = _normalize_title(title) if title else None
            same_table = (
                current is not None
                and title_norm is not None
                and title_norm == current["title_norm"]
            )
            if not same_table:
                close_current()
                current = {
                    "title": title if title else " | ".join(block["cells"]),
                    "title_norm": title_norm if title_norm else _normalize_title(
                        " | ".join(block["cells"])
                    ),
                    "header": block["cells"],
                    "first_page": block["page"],
                    "rows": [],
                }
            pending_title = None
            continue

        if block["type"] == "table_row":
            if current is None:
                # Fila huerfana (sin header/titulo previo detectado): arranca una tabla
                # sin nombre en vez de descartar el dato.
                current = {
                    "title": "(sin titulo)",
                    "title_norm": "(sin titulo)",
                    "header": None,
                    "first_page": block["page"],
                    "rows": [],
                }
            current["rows"].append({"code": _row_code(block["cells"]), "cells": block["cells"]})
            pending_title = None
            continue

    close_current()

    # Un table_header sin ninguna table_row antes del siguiente limite no es una tabla real
    # -es el mismo falso positivo de viñetas-como-tabla que ya se documento en el Modulo 2
    # (ej. 'l' + "Draft Data: TCR 5, Positions 145-148" clasificado como table_header de 1
    # fila con 0 filas de datos abajo). Sin este filtro, cada uno de esos fantasmas entra al
    # emparejamiento de tablas y genera ruido (agregados/eliminados/fuzzy-matches espurios
    # entre parrafos narrativos que por casualidad tienen texto parecido en 2 ediciones).
    tables = [t for t in tables if t["rows"]]
    tables = _coalesce_same_title(tables)

    for table in tables:
        seen = {}
        duplicates = set()
        for row in table["rows"]:
            seen[row["code"]] = seen.get(row["code"], 0) + 1
            if seen[row["code"]] > 1:
                duplicates.add(row["code"])
        table["duplicate_codes"] = sorted(duplicates)

    return tables


def _coalesce_same_title(tables: list) -> list:
    """Fusiona, dentro de una misma edicion, tablas distintas que comparten title_norm."""
    by_title = {}
    order = []
    for table in tables:
        key = table["title_norm"]
        if key not in by_title:
            by_title[key] = table
            order.append(key)
        else:
            by_title[key]["rows"].extend(table["rows"])
    return [by_title[key] for key in order]


def match_tables(tables_a: list, tables_b: list) -> dict:
    by_title_a = {t["title_norm"]: t for t in tables_a}
    by_title_b = {t["title_norm"]: t for t in tables_b}

    matched = []
    unmatched_a = dict(by_title_a)
    unmatched_b = dict(by_title_b)

    for title_norm, table_a in by_title_a.items():
        table_b = by_title_b.get(title_norm)
        if table_b is not None:
            matched.append((table_a, table_b, "exact", 1.0))
            unmatched_a.pop(title_norm, None)
            unmatched_b.pop(title_norm, None)

    for title_norm_a, table_a in list(unmatched_a.items()):
        best_ratio = 0.0
        best_title_norm_b = None
        for title_norm_b in unmatched_b:
            ratio = difflib.SequenceMatcher(None, title_norm_a, title_norm_b).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_title_norm_b = title_norm_b
        if best_title_norm_b is not None and best_ratio >= FUZZY_TITLE_THRESHOLD:
            table_b = unmatched_b.pop(best_title_norm_b)
            matched.append((table_a, table_b, "fuzzy", round(best_ratio, 3)))
            unmatched_a.pop(title_norm_a, None)

    return {
        "matched": matched,
        "tables_removed": list(unmatched_a.values()),
        "tables_added": list(unmatched_b.values()),
    }


def match_rows(table_a: dict, table_b: dict) -> dict:
    rows_a = {r["code"]: r for r in table_a["rows"]}
    rows_b = {r["code"]: r for r in table_b["rows"]}

    codes_matched = sorted(set(rows_a) & set(rows_b))
    codes_removed = sorted(set(rows_a) - set(rows_b))
    codes_added = sorted(set(rows_b) - set(rows_a))

    return {
        "rows_matched": [
            {"code": code, "cells_a": rows_a[code]["cells"], "cells_b": rows_b[code]["cells"]}
            for code in codes_matched
        ],
        "rows_removed": [{"code": code, "cells": rows_a[code]["cells"]} for code in codes_removed],
        "rows_added": [{"code": code, "cells": rows_b[code]["cells"]} for code in codes_added],
    }


def match_edition_pair(data_a: dict, data_b: dict) -> dict:
    tables_a = extract_tables(data_a["blocks"])
    tables_b = extract_tables(data_b["blocks"])

    table_match = match_tables(tables_a, tables_b)

    tables_matched = []
    for table_a, table_b, match_type, ratio in table_match["matched"]:
        row_match = match_rows(table_a, table_b)
        tables_matched.append(
            {
                "title_a": table_a["title"],
                "title_b": table_b["title"],
                "header_a": table_a["header"],
                "header_b": table_b["header"],
                "match_type": match_type,
                "fuzzy_ratio": ratio,
                "duplicate_codes_a": table_a["duplicate_codes"],
                "duplicate_codes_b": table_b["duplicate_codes"],
                **row_match,
            }
        )

    return {
        "manual": MANUAL_SLUG,
        "edition_a": data_a["edition_date"],
        "edition_b": data_b["edition_date"],
        "num_tables_a": len(tables_a),
        "num_tables_b": len(tables_b),
        "tables_matched": tables_matched,
        "tables_removed": [
            {"title": t["title"], "num_rows": len(t["rows"])} for t in table_match["tables_removed"]
        ],
        "tables_added": [
            {"title": t["title"], "num_rows": len(t["rows"])} for t in table_match["tables_added"]
        ],
    }


def main():
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if len(input_paths) < 2:
        print(f"Se necesitan al menos 2 ediciones en {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path_a, path_b in zip(input_paths, input_paths[1:]):
        data_a = json.loads(path_a.read_text())
        data_b = json.loads(path_b.read_text())
        result = match_edition_pair(data_a, data_b)

        out_name = f"{result['edition_a']}_to_{result['edition_b']}.json"
        (OUTPUT_DIR / out_name).write_text(json.dumps(result, ensure_ascii=False, indent=2))

        rows_matched = sum(len(t["rows_matched"]) for t in result["tables_matched"])
        rows_added = sum(len(t["rows_added"]) for t in result["tables_matched"])
        rows_removed = sum(len(t["rows_removed"]) for t in result["tables_matched"])
        fuzzy = sum(1 for t in result["tables_matched"] if t["match_type"] == "fuzzy")
        print(
            f"{out_name}: tablas {result['num_tables_a']}->{result['num_tables_b']} "
            f"(matched={len(result['tables_matched'])} [fuzzy={fuzzy}], "
            f"added={len(result['tables_added'])}, removed={len(result['tables_removed'])}) | "
            f"filas matched={rows_matched} added={rows_added} removed={rows_removed}"
        )


if __name__ == "__main__":
    main()
