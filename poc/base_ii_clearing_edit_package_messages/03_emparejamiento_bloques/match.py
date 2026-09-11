"""
Modulo 3 - Emparejamiento de bloques para el manual base_ii_clearing_edit_package_messages.

Toma el stream plano de bloques del Modulo 2 (`card_header`/`field`/`bullet_list`/
`paragraph`, documento completo sin reset por pagina) y hace lo mismo que el Modulo 3 del
otro manual en espiritu -reconstruir la entidad real a comparar y emparejarla entre 2
ediciones- pero con una estructura mas simple, porque este manual no tiene el nivel
intermedio "tabla": es una lista plana de ~933-953 fichas de codigo por edicion, sin
agrupamiento en tablas con su propio titulo/header. Por eso ac치 no hay equivalente a
`match_tables` (con matching exacto + fuzzy de titulos) del otro Modulo 3 -alcanza con
emparejar fichas directamente.

Diseno (ver discusion completa en local_memory/NOTES.md):

1. Reconstruccion de fichas (`extract_fichas`): se recorre la lista de bloques en orden de
   documento. Un `card_header` cierra la ficha activa (si hay) y arranca una nueva. Los
   bloques `field` que le siguen se agregan por etiqueta (`Description`/`Action`) a listas,
   no a un string unico -confirmado con datos reales que el codigo `V0545` tiene el campo
   `Action:` literalmente duplicado en el PDF fuente (mismo texto 2 veces), y el Modulo 2
   decidio explicitamente no deduplicar contenido real de la fuente aunque sea repetitivo;
   el Modulo 3 sigue el mismo criterio y preserva la lista completa en vez de quedarse solo
   con el primer valor. Los `bullet_list` (solo Capitulo 2, "Transaction Types:") se
   acumulan de la misma forma como lista de listas de items -por si alguna vez aparece mas
   de un bloque de este tipo en una misma ficha, aunque no se encontro ningun caso real en
   las 9 ediciones. Los `paragraph` (avisos legales, encabezados de capitulo/seccion,
   glosario, TOC no filtrado) se ignoran para la reconstruccion de fichas: se verifico con
   datos reales que siempre caen ENTRE dos fichas, nunca interrumpiendo un `card_header` a
   medio camino de sus campos (ej. p.268 de la edicion `20260418`: el parrafo "Data Entry
   Messages" -subtitulo de seccion- aparece justo despues de que la ficha `V9999` ya cerro
   su `bullet_list`, antes de que arranque `V9003`).

   Validado en las 9 ediciones antes de escribir el matching: 0 codigos duplicados dentro
   de una misma edicion (a diferencia del otro manual, que si necesito logica de deteccion/
   reporte de duplicados porque su fuente si los tenia), toda ficha tiene exactamente 1
   `Description` y al menos 1 `Action` (0 fichas sin ninguno de los dos), y ninguna ficha
   tiene mas de 1 bloque `bullet_list`.

2. Identidad de ficha (`code`): a diferencia del otro manual, donde la fila necesitaba
   normalizarse (upper+strip de una celda de texto libre), ac치 el codigo ya viene limpio
   desde el Modulo 1/2 (senal tipografica, no regex de contenido) - se usa tal cual como
   clave estable. Mismo principio ya establecido en el proyecto (matchear por clave
   estable, no por nombre/titulo fuzzy) pero aplicado de forma aun mas directa: el codigo
   ES la identidad de la ficha completa, no de una fila dentro de una tabla mas grande.

3. Emparejamiento entre 2 ediciones (`match_fichas`): por codigo exacto unicamente. No hay
   fuzzy-matching de codigos (a diferencia del fuzzy de TITULOS de tabla del otro manual) -
   un codigo de error/validacion no se "renombra" de forma reconocible por similitud de
   texto como si puede pasar con el nombre de una tabla; si el codigo cambia, es un codigo
   distinto. Fichas presentes en ambas ediciones son "matched" (el Modulo 4 decide si su
   contenido cambio); solo en la edicion vieja = removida; solo en la nueva = agregada.

Alcance: procesa pares de ediciones CONSECUTIVAS (las 9 ediciones de este manual dan 8
pares), igual que el otro manual. Se puede llamar `match_edition_pair()` directamente con
cualquier par si se necesita comparar ediciones no consecutivas.
"""

import json
import sys
from pathlib import Path

MANUAL_SLUG = "base_ii_clearing_edit_package_messages"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "02_normalizacion_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"


def extract_fichas(blocks: list) -> list:
    """Reconstruye fichas (codigo + titulo + campos + tipos de transaccion) a partir del
    stream plano de bloques del Modulo 2."""
    fichas = []
    current = None

    def close_current():
        if current is not None:
            fichas.append(current)

    for block in blocks:
        if block["type"] == "card_header":
            close_current()
            current = {
                "code": block["code"],
                "title": block["title"],
                "page": block["page"],
                "description": [],
                "action": [],
                "transaction_types": [],
            }
            continue

        if current is None:
            # paragraph/field/bullet_list fuera de toda ficha (portada, aviso legal,
            # encabezados de capitulo/seccion antes de la primera ficha, glosario final).
            continue

        if block["type"] == "field":
            if block["label"] == "Description":
                current["description"].append(block["text"])
            elif block["label"].startswith("Action"):
                current["action"].append(block["text"])
            continue

        if block["type"] == "bullet_list":
            current["transaction_types"].append(block["items"])
            continue

        # paragraph entre fichas (subtitulo de seccion, glosario, etc.): no pertenece a
        # ninguna ficha, se ignora aca a proposito (ver docstring del modulo).

    close_current()

    # No deberia haber codigos duplicados dentro de una misma edicion (validado en las 9
    # ediciones), pero se detecta y reporta en vez de asumirlo silenciosamente, mismo
    # criterio de robustez que el otro Modulo 3.
    codes_seen = {}
    duplicate_codes = set()
    for ficha in fichas:
        codes_seen[ficha["code"]] = codes_seen.get(ficha["code"], 0) + 1
        if codes_seen[ficha["code"]] > 1:
            duplicate_codes.add(ficha["code"])

    return fichas, sorted(duplicate_codes)


def match_fichas(fichas_a: list, fichas_b: list) -> dict:
    by_code_a = {f["code"]: f for f in fichas_a}
    by_code_b = {f["code"]: f for f in fichas_b}

    codes_matched = sorted(set(by_code_a) & set(by_code_b))
    codes_removed = sorted(set(by_code_a) - set(by_code_b))
    codes_added = sorted(set(by_code_b) - set(by_code_a))

    return {
        "fichas_matched": [
            {
                "code": code,
                "title_a": by_code_a[code]["title"],
                "title_b": by_code_b[code]["title"],
                "description_a": by_code_a[code]["description"],
                "description_b": by_code_b[code]["description"],
                "action_a": by_code_a[code]["action"],
                "action_b": by_code_b[code]["action"],
                "transaction_types_a": by_code_a[code]["transaction_types"],
                "transaction_types_b": by_code_b[code]["transaction_types"],
            }
            for code in codes_matched
        ],
        "fichas_removed": [
            {"code": code, "title": by_code_a[code]["title"]} for code in codes_removed
        ],
        "fichas_added": [
            {"code": code, "title": by_code_b[code]["title"]} for code in codes_added
        ],
    }


def match_edition_pair(data_a: dict, data_b: dict) -> dict:
    fichas_a, duplicates_a = extract_fichas(data_a["blocks"])
    fichas_b, duplicates_b = extract_fichas(data_b["blocks"])

    result = match_fichas(fichas_a, fichas_b)

    return {
        "manual": MANUAL_SLUG,
        "edition_a": data_a["edition_date"],
        "edition_b": data_b["edition_date"],
        "num_fichas_a": len(fichas_a),
        "num_fichas_b": len(fichas_b),
        "duplicate_codes_a": duplicates_a,
        "duplicate_codes_b": duplicates_b,
        **result,
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

        print(
            f"{out_name}: fichas {result['num_fichas_a']}->{result['num_fichas_b']} "
            f"(matched={len(result['fichas_matched'])}, "
            f"added={len(result['fichas_added'])}, removed={len(result['fichas_removed'])}) "
            f"dup_a={result['duplicate_codes_a']} dup_b={result['duplicate_codes_b']}"
        )


if __name__ == "__main__":
    main()
