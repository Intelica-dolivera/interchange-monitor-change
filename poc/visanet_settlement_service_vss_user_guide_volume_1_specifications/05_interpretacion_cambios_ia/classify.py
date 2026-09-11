"""
Modulo 5 - Interpretacion de cambios (IA) para el manual
visanet_settlement_service_vss_user_guide_volume_1_specifications.

Clasifica con un LLM local (Ollama, `qwen3:4b`, JSON forzado, `think:false`, temperatura 0)
los cambios `paragraph_content_changed` (parrafos, ver 6to manual) Y `pair_content_changed`
(descripcion de un par Field Name/Description que cambio, ver Modulo 4 -unico entre los
manuales de este proyecto en tener 2 tipos de contenido distintos llegando a este modulo).
Mismas 3 categorias que los otros manuales (business_rule_change/editorial_reword/
extraction_noise), mismo prompt adaptado por tipo (contexto de ruta de seccion para
parrafos, contexto de tabla+campo para pares) y misma red de seguridad deterministica
(`_find_disappeared_content`, override a business_rule_change si desaparecen 5+ palabras sin
reemplazo -no deberia dispararse en los casos de par con `old` vacio, ver Modulo 4 docstring:
no hay nada que "desaparecer" de una cadena vacia).

Alcance: procesa todos los pares ya generados por el Modulo 4 en `data/04_deteccion_cambios/`.
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

MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_1_specifications"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"
OLLAMA_TIMEOUT_SECONDS = 120

VALID_CATEGORIES = {"business_rule_change", "editorial_reword", "extraction_noise"}
MIN_DISAPPEARED_WORDS = 5

TARGET_CHANGE_TYPES = {"paragraph_content_changed", "pair_content_changed"}

PARAGRAPH_PROMPT = """Sos un asistente que clasifica cambios de texto en un manual de especificaciones de settlement de Visa (VisaNet Settlement Service (VSS) User Guide, Volume 1, Specifications) -un documento narrativo de reglas de negocio, no una grilla de campos.

Seccion: {context}

Texto en la edicion VIEJA:
\"\"\"{old}\"\"\"

Texto en la edicion NUEVA:
\"\"\"{new}\"\"\"

Clasifica este cambio en EXACTAMENTE una de estas 3 categorias:
- business_rule_change: el significado o regla de negocio cambio de verdad.
- editorial_reword: dice lo mismo, solo cambio la redaccion, el orden de palabras o el formato.
- extraction_noise: no es un cambio de contenido real, es un artefacto de extraccion de PDF (texto cortado, fragmentos, espaciado raro).

Responde SOLO con este JSON, sin texto adicional: {{"category": "...", "reason": "..."}}
La razon debe ser 1 oracion corta en español."""

PAIR_PROMPT = """Sos un asistente que clasifica cambios en la DESCRIPCION de un campo dentro de una tabla de referencia "Field Name/Description" de un manual de settlement de Visa (VisaNet Settlement Service (VSS) User Guide, Volume 1, Specifications). Estas tablas documentan el significado de cada campo de un reporte de reconciliacion.

Tabla: {context}
Campo: {field_name}

Descripcion en la edicion VIEJA:
\"\"\"{old}\"\"\"

Descripcion en la edicion NUEVA:
\"\"\"{new}\"\"\"

Clasifica este cambio en EXACTAMENTE una de estas 3 categorias:
- business_rule_change: el significado del campo cambio de verdad.
- editorial_reword: dice lo mismo, solo cambio la redaccion o el formato.
- extraction_noise: no es un cambio de contenido real, es un artefacto de extraccion de PDF -MUY COMUN cuando la descripcion vieja esta vacia o es mucho mas corta que la nueva sin razon aparente (texto que no se extrajo bien de una tabla rotada en el PDF, no una edicion real de Visa).

Responde SOLO con este JSON, sin texto adicional: {{"category": "...", "reason": "..."}}
La razon debe ser 1 oracion corta en español."""


def _ollama_classify(prompt: str) -> dict:
    return ollama_classify(prompt, VALID_CATEGORIES)


def _find_disappeared_content(old_text: str, new_text: str) -> list:
    return find_disappeared_content(old_text, new_text, min_words=MIN_DISAPPEARED_WORDS)


def classify_change(change: dict) -> dict:
    if change["change_type"] == "paragraph_content_changed":
        context = " > ".join(change["path"])
        prompt = PARAGRAPH_PROMPT.format(context=context, old=change["old"], new=change["new"])
    else:
        context = f"{change['example_title']} ({' > '.join(change['path'])})"
        prompt = PAIR_PROMPT.format(
            context=context, field_name=change["name"], old=change["old"], new=change["new"]
        )

    ai = _ollama_classify(prompt)

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


def classify_pair(match_result: dict, progress_prefix: str = "") -> dict:
    changes = []
    content_changes = [c for c in match_result["changes"] if c["change_type"] in TARGET_CHANGE_TYPES]
    total = len(content_changes)
    done = 0
    for change in match_result["changes"]:
        if change["change_type"] not in TARGET_CHANGE_TYPES:
            changes.append(change)
            continue
        changes.append(classify_change(change))
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

    only = None
    for arg in sys.argv[1:]:
        if arg.startswith("--only="):
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
        result = classify_pair(match_result, progress_prefix=f"[{input_path.stem}]")

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
