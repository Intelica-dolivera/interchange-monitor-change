"""
Modulo 5 - Interpretacion de cambios (IA) para el manual base_ii_clearing_edit_package_messages.

Toma la salida ya deterministica del Modulo 4 y le agrega, SOLO a los cambios de tipo
`ficha_content_changed` (campos de una ficha que difieren por debajo del umbral de
similitud 0.98), una clasificacion semantica hecha por un LLM local (Ollama, `qwen3:4b`,
JSON forzado, `think:false`, temperatura 0). El resto de los tipos de cambio
(`ficha_added`, `ficha_removed`, `duplicate_code_warning`) son decisiones estructurales ya
deterministicas del Modulo 3/4 y pasan sin tocar -mismo principio de separacion de
responsabilidades que el Modulo 5 del otro manual y que el pipeline de referencia
(`utils_example/06_classify_changes.py`).

Mismas 3 categorias que el Modulo 5 del otro manual, sin cambios de diseno (la razon para
descartar una 4ta categoria "estructural" ya se discutio ahi y sigue aplicando igual aca:
altas/bajas de ficha ya son deterministicas, jamas llegan a este clasificador):

- `business_rule_change`: el significado o valor de negocio cambio de verdad (ej. un rango
  de valores validos se amplio, una condicion de validacion cambio, un campo se renombro
  con un significado distinto).
- `editorial_reword`: mismo significado, solo cambio la redaccion/formato/ortografia.
- `extraction_noise`: no es un cambio real de contenido -artefacto de extraccion del PDF.

Diferencia de diseno respecto al Modulo 5 del otro manual: el prompt no tiene "tabla" (no
existe ese nivel acá) -en su lugar se le da al LLM el TITULO de la ficha como contexto (útil
incluso cuando el campo que cambió es `description`/`action`/`transaction_types`, no el
titulo en si) y el nombre del campo que cambió (`title`/`description`/`action`/
`transaction_types`) en vez de "columna".

Red de seguridad deterministica (`_find_disappeared_content`), idéntica a la del otro
manual: si el LLM dice `editorial_reword`/`extraction_noise` pero un tramo de 5+ palabras
del texto viejo no tiene equivalente en el nuevo, se anula el veredicto del LLM y se fuerza
`business_rule_change`, registrado en `safety_net_override`.

Alcance: procesa todos los pares ya generados por el Modulo 4 en
`data/04_deteccion_cambios/`. Requiere Ollama corriendo en localhost:11434 con el modelo
`qwen3:4b` ya descargado (`ollama pull qwen3:4b`).
"""

import difflib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))
from ollama_client import ensure_ollama_running, find_disappeared_content, ollama_classify

MANUAL_SLUG = "base_ii_clearing_edit_package_messages"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"
OLLAMA_TIMEOUT_SECONDS = 120

VALID_CATEGORIES = {"business_rule_change", "editorial_reword", "extraction_noise"}
MIN_DISAPPEARED_WORDS = 5

# Item 7/[[pending-bug-fixes]] (residuo cerrado 2026-09-05): ficha V0407 sigue sin detectarse
# como el `min_words` general no baja de 5 (bajarlo se probo y se descarto -3-4 palabras
# cortas son mayormente renombres/abreviaturas inocuos, ver docstring de
# `_find_disappeared_content`). Señal MAS ESPECIFICA, solo para este manual: un tramo
# "replace"/"delete" corto que borra una conjuncion ("or"/"and") JUNTO a un valor corto
# (1-3 caracteres, ej. "B") es casi siempre un valor enumerado que deja de ser valido -no
# una reformulacion. Validado con un escaneo real de las 9 ediciones completas ANTES de
# implementar: de 104 tramos "replace"/"delete" bajo el umbral de 5 palabras en todo el
# corpus, la combinacion conjuncion+valor-corto aparece en EXACTAMENTE 3 (ficha V0407 y
# V1073, ambas en el campo `title`, y V1089 en `description` -esta ultima ya se detectaba
# correctamente por otro tramo mas largo en el mismo campo, asi que no es un caso nuevo).
# 0 falsos positivos en las 3 coincidencias.
ENUMERATED_VALUE_CONJUNCTION = re.compile(r"^(or|and)$", re.IGNORECASE)
SHORT_VALUE_TOKEN = re.compile(r"^[A-Z0-9]{1,3}\.?$")

FIELD_LABELS = {
    "title": "el titulo de la ficha",
    "description": "el campo Description",
    "action": "el campo Action",
    "transaction_types": "la lista de Transaction Types",
}

PROMPT_TEMPLATE = """Sos un asistente que clasifica cambios de texto en una ficha de codigo de un manual tecnico de Visa (BASE II Clearing Edit Package Messages), que documenta mensajes de validacion y log.

Codigo de la ficha: {code}
Titulo de la ficha: {title}
Campo que cambio: {field_label}

Texto en la edicion VIEJA:
\"\"\"{old}\"\"\"

Texto en la edicion NUEVA:
\"\"\"{new}\"\"\"

Clasifica este cambio en EXACTAMENTE una de estas 3 categorias:
- business_rule_change: el significado o valor de negocio cambio de verdad (ej. un rango de valores validos se amplio, una condicion de validacion cambio, un campo se renombro con un significado distinto).
- editorial_reword: dice lo mismo, solo cambio la redaccion, el orden de palabras, la ortografia o el formato.
- extraction_noise: no es un cambio de contenido real, es un artefacto de extraccion de PDF (texto cortado, fragmentos, espaciado raro).

Responde SOLO con este JSON, sin texto adicional: {{"category": "...", "reason": "..."}}
La razon debe ser 1 oracion corta en español."""


def _ollama_classify(code: str, title: str, field: str, old: str, new: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        code=code, title=title, field_label=FIELD_LABELS.get(field, field), old=old, new=new
    )
    return ollama_classify(prompt, VALID_CATEGORIES)


def _find_disappeared_content(old_text: str, new_text: str) -> list:
    """Tramos de MIN_DISAPPEARED_WORDS+ palabras del texto viejo sin equivalente en el nuevo.

    Cuenta tanto "delete" (texto viejo que desaparece sin nada en su lugar) como "replace"
    (texto viejo reemplazado por texto nuevo totalmente distinto, sin ninguna palabra en
    comun) -encontrado investigando el item 7 del TODO (ficha V0407): la causa real de esa
    misclasificacion no era el umbral de 5 palabras como se habia logueado originalmente,
    sino que el codigo NUNCA miraba los opcodes "replace" en absoluto (`'EQUALS B OR' ->
    'EQUAL TO'` es un replace de 3 palabras, no un delete). Investigando el alcance real se
    encontraron casos bastante mas grandes e importantes con el mismo problema (ej. ficha
    `V1209`: `'Fee Collection | Funds Disbursement'` desaparece de la lista de
    `transaction_types` sin dejar rastro -7 palabras; el glosario `optional issuer fee`:
    41 palabras de definicion completa reemplazadas por `"See Visa Issuer FX Calculator"`).
    El umbral de 5 palabras se mantiene sin cambios para "replace" (misma calibracion ya
    validada) -confirmado con un escaneo del corpus completo que los "replace" cortos (3-4
    palabras) que SI pasarian ese umbral mas bajo son mayormente renombres/abreviaturas
    inocuos (ej. `"Interchange Transaction File"` -> `"ITF"`), asi que bajar el umbral
    tambien habria sido inseguro -no se toco.

    Ademas del umbral general, `_removes_enumerated_value` cubre el residuo puntual de V0407
    (ver comentario junto a `ENUMERATED_VALUE_CONJUNCTION` mas arriba) -una señal MAS
    ESPECIFICA que la generica de arriba, no un reemplazo de ella.
    """
    disappeared = find_disappeared_content(old_text, new_text, min_words=MIN_DISAPPEARED_WORDS)
    for phrase in _removes_enumerated_value(old_text, new_text):
        if phrase not in disappeared:
            disappeared.append(phrase)
    return disappeared


def _removes_enumerated_value(old_text: str, new_text: str) -> list:
    """Tramos "replace"/"delete" (de cualquier largo, no solo por debajo del umbral general)
    que borran una conjuncion ("or"/"and") junto a un valor corto (`SHORT_VALUE_TOKEN`) -señal
    de que un valor enumerado dejo de ser valido, no solo una reformulacion. Ver el comentario
    junto a `ENUMERATED_VALUE_CONJUNCTION` para la validacion contra el corpus completo."""
    old_words, new_words = old_text.split(), new_text.split()
    matcher = difflib.SequenceMatcher(None, old_words, new_words)
    found = []
    for tag, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if tag not in ("replace", "delete"):
            continue
        removed = old_words[i1:i2]
        has_conjunction = any(ENUMERATED_VALUE_CONJUNCTION.match(w) for w in removed)
        has_short_value = any(SHORT_VALUE_TOKEN.match(w) for w in removed)
        if has_conjunction and has_short_value:
            found.append(" ".join(removed))
    return found


def classify_change(change: dict, title_by_code: dict) -> dict:
    ai = _ollama_classify(
        code=change["code"],
        title=title_by_code.get(change["code"], ""),
        field=change["field"],
        old=change["old"],
        new=change["new"],
    )

    disappeared = _find_disappeared_content(change["old"], change["new"])
    override = ai["category"] in ("editorial_reword", "extraction_noise") and bool(disappeared)

    enriched = dict(change)
    enriched["ai_category"] = "business_rule_change" if override else ai["category"]
    enriched["ai_reason"] = ai["reason"]
    enriched["disappeared_content"] = disappeared
    enriched["safety_net_override"] = override
    if override:
        enriched["ai_original_category"] = ai["category"]
    return enriched


def _title_by_code(match_result: dict) -> dict:
    """Titulo de cada ficha matched, para dar contexto al LLM aunque el campo que cambio
    no sea el titulo en si (usa title_b, el de la edicion nueva)."""
    return {f["code"]: f["title_b"] for f in match_result.get("fichas_matched", [])}


def classify_pair(match_result: dict, title_by_code: dict, progress_prefix: str = "") -> dict:
    changes = []
    content_changes = [c for c in match_result["changes"] if c["change_type"] == "ficha_content_changed"]
    total = len(content_changes)
    done = 0
    for change in match_result["changes"]:
        if change["change_type"] != "ficha_content_changed":
            changes.append(change)
            continue
        changes.append(classify_change(change, title_by_code))
        done += 1
        if progress_prefix:
            print(f"{progress_prefix} {done}/{total}", file=sys.stderr)

    summary = dict(match_result["summary"])
    ai_summary = {}
    for change in changes:
        if change["change_type"] == "ficha_content_changed":
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

    match_dir = Path(__file__).resolve().parents[1] / "data" / "03_emparejamiento_bloques"

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
        match_pair = json.loads((match_dir / input_path.name).read_text())
        title_by_code = _title_by_code(match_pair)

        if limit is not None:
            content_idx = [
                i for i, c in enumerate(match_result["changes"]) if c["change_type"] == "ficha_content_changed"
            ]
            drop = set(content_idx[limit:])
            match_result["changes"] = [c for i, c in enumerate(match_result["changes"]) if i not in drop]

        result = classify_pair(match_result, title_by_code, progress_prefix=f"[{input_path.stem}]")

        out_path = OUTPUT_DIR / input_path.name
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

        ai_summary_str = ", ".join(f"{k}={v}" for k, v in sorted(result["ai_summary"].items()))
        overrides = sum(
            1
            for c in result["changes"]
            if c.get("change_type") == "ficha_content_changed" and c.get("safety_net_override")
        )
        print(f"{input_path.name}: {ai_summary_str} (safety_net_override={overrides})")


if __name__ == "__main__":
    main()
