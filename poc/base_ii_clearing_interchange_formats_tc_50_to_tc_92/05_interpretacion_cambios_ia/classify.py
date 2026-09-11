"""
Modulo 5 - Interpretacion de cambios (IA) para el manual
base_ii_clearing_interchange_formats_tc_50_to_tc_92.

Mismo diseno que el Modulo 5 del 3er manual, su hermano directo: clasifica SOLO los cambios
`row_content_changed`/`card_content_changed` con un LLM local (Ollama, `qwen3:4b`, JSON
forzado, `think:false`, temperatura 0) en 3 categorias (`business_rule_change`/
`editorial_reword`/`extraction_noise`). Las decisiones estructurales (altas/bajas,
Reserved<->definido) ya las resuelve Modulo 3/4 de forma deterministica y pasan sin tocar.

Sin cambios de diseno respecto al 3er manual -mismo mecanismo de contexto (`_field_name_lookup`
recargando el Modulo 3 para dar nombre de campo cuando la columna que cambio no es `Contents`/
`name`) y misma red de seguridad deterministica (`_find_disappeared_content`, override a
`business_rule_change` si desaparecen 5+ palabras sin equivalente).

Alcance esperado mucho menor que el 3er manual: Modulo 4 encontro solo 26
`card_content_changed` y 0 `row_content_changed` en los 8 pares (vs. cientos en el 3er
manual) -este manual resulto mas estable en esta ventana de ediciones (ver
[[open-questions-technical-manuals]]).

Requiere Ollama corriendo en localhost:11434 con el modelo `qwen3:4b` ya descargado.
"""

import difflib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from ollama_client import ensure_ollama_running, find_disappeared_content, ollama_classify

MANUAL_SLUG = "base_ii_clearing_interchange_formats_tc_50_to_tc_92"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"
MATCH_DIR = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"
OLLAMA_TIMEOUT_SECONDS = 120

VALID_CATEGORIES = {"business_rule_change", "editorial_reword", "extraction_noise"}
MIN_DISAPPEARED_WORDS = 5

TARGET_CHANGE_TYPES = {"row_content_changed", "card_content_changed"}

PROMPT_TEMPLATE = """Sos un asistente que clasifica cambios de texto en un manual tecnico de Visa (BASE II Clearing Interchange Formats, TC 50 to TC 92) que documenta el layout de bytes de mensajes de intercambio (posicion, longitud, formato y contenido de cada campo).

Seccion: {title}
Campo: {field_name} (posicion {position})
{context_label} que cambio: {column}

Texto en la edicion VIEJA:
\"\"\"{old}\"\"\"

Texto en la edicion NUEVA:
\"\"\"{new}\"\"\"

Clasifica este cambio en EXACTAMENTE una de estas 3 categorias:
- business_rule_change: el significado o valor de negocio cambio de verdad (ej. un rango de valores validos cambio, una condicion cambio, el campo se redefinio).
- editorial_reword: dice lo mismo, solo cambio la redaccion, el orden de palabras o el formato.
- extraction_noise: no es un cambio de contenido real, es un artefacto de extraccion de PDF (texto cortado, fragmentos, espaciado raro).

Responde SOLO con este JSON, sin texto adicional: {{"category": "...", "reason": "..."}}
La razon debe ser 1 oracion corta en español."""


def _ollama_classify(title: str, field_name: str, position: str, column: str, context_label: str, old: str, new: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        title=title, field_name=field_name, position=position, column=column,
        context_label=context_label, old=old, new=new,
    )
    return ollama_classify(prompt, VALID_CATEGORIES)


def _find_disappeared_content(old_text: str, new_text: str) -> list:
    return find_disappeared_content(old_text, new_text, min_words=MIN_DISAPPEARED_WORDS)


def _field_name_lookup(match_pair: dict) -> dict:
    """(titulo_seccion, posicion) -> nombre del campo (Contents de la fila, o nombre de la
    ficha si la fila no matcheo) -contexto para el prompt, ver docstring del modulo."""
    lookup = {}
    for section in match_pair.get("sections_matched", []):
        title = section["title_b"]
        for row in section.get("rows_matched", []):
            lookup[(title, row["position"])] = row["cells_b"][3]
        for card in section.get("cards_matched", []):
            lookup.setdefault((title, card["position"]), card["card_b"]["name"])
    return lookup


def classify_change(change: dict, field_name_lookup: dict) -> dict:
    is_row = change["change_type"] == "row_content_changed"
    field_name = field_name_lookup.get((change["title"], change["position"]), "")
    column = change["column"] if is_row else change["field"]
    context_label = "Columna" if is_row else "Campo de la ficha"

    ai = _ollama_classify(
        title=change["title"],
        field_name=field_name,
        position=change["position"],
        column=column,
        context_label=context_label,
        old=change["old"],
        new=change["new"],
    )

    disappeared = _find_disappeared_content(change["old"], change["new"])
    override = ai["category"] in ("editorial_reword", "extraction_noise") and bool(disappeared)

    enriched = dict(change)
    enriched["field_name"] = field_name
    enriched["ai_category"] = "business_rule_change" if override else ai["category"]
    enriched["ai_reason"] = ai["reason"]
    enriched["disappeared_content"] = disappeared
    enriched["safety_net_override"] = override
    if override:
        enriched["ai_original_category"] = ai["category"]
    return enriched


def classify_pair(match_result: dict, field_name_lookup: dict, progress_prefix: str = "") -> dict:
    changes = []
    content_changes = [c for c in match_result["changes"] if c["change_type"] in TARGET_CHANGE_TYPES]
    total = len(content_changes)
    done = 0
    for change in match_result["changes"]:
        if change["change_type"] not in TARGET_CHANGE_TYPES:
            changes.append(change)
            continue
        changes.append(classify_change(change, field_name_lookup))
        done += 1
        if progress_prefix:
            print(f"{progress_prefix} {done}/{total}", file=sys.stderr)

    ai_summary = {}
    for change in changes:
        if change["change_type"] in TARGET_CHANGE_TYPES:
            ai_summary[change["ai_category"]] = ai_summary.get(change["ai_category"], 0) + 1

    result = dict(match_result)
    result["changes"] = changes
    result["ai_summary"] = ai_summary
    return result


def main():
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if not input_paths:
        print(f"No se encontraron cambios detectados en {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    limit = None
    only = None
    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])
        elif arg.startswith("--only="):
            only = arg.split("=", 1)[1]

    if only:
        input_paths = [p for p in input_paths if p.stem == only]
        if not input_paths:
            print(f"No se encontro el par {only!r} en {INPUT_DIR}", file=sys.stderr)
            sys.exit(1)

    ensure_ollama_running()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for input_path in input_paths:
        match_result = json.loads(input_path.read_text())
        match_pair = json.loads((MATCH_DIR / input_path.name).read_text())
        field_name_lookup = _field_name_lookup(match_pair)

        if limit is not None:
            content_idx = [
                i for i, c in enumerate(match_result["changes"]) if c["change_type"] in TARGET_CHANGE_TYPES
            ]
            drop = set(content_idx[limit:])
            match_result["changes"] = [c for i, c in enumerate(match_result["changes"]) if i not in drop]

        result = classify_pair(match_result, field_name_lookup, progress_prefix=f"[{input_path.stem}]")

        out_path = OUTPUT_DIR / input_path.name
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

        ai_summary_str = ", ".join(f"{k}={v}" for k, v in sorted(result["ai_summary"].items()))
        overrides = sum(
            1
            for c in result["changes"]
            if c.get("change_type") in TARGET_CHANGE_TYPES and c.get("safety_net_override")
        )
        print(f"{input_path.name}: {ai_summary_str} (safety_net_override={overrides})")


if __name__ == "__main__":
    main()
