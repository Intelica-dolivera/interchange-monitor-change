"""
Modulo 5 - Interpretacion de cambios (IA) para el manual
international_full_service_pos_online_messages_processing_specifications.

Toma la salida ya deterministica del Modulo 4 y le agrega, SOLO a los cambios de tipo
`paragraph_content_changed` (parrafos emparejados por similitud -no texto exacto- en Modulo
3), una clasificacion semantica hecha por un LLM local (Ollama, `qwen3:4b`, JSON forzado,
`think:false`, temperatura 0). El resto de los tipos de cambio (altas/bajas de seccion/
parrafo, avisos de duplicados) son decisiones estructurales ya deterministicas y pasan sin
tocar -mismo principio de separacion de responsabilidades que los otros 5 manuales.

Mismas 3 categorias que los otros manuales:
- `business_rule_change`: el significado o regla de negocio cambio de verdad.
- `editorial_reword`: mismo significado, solo cambio la redaccion/formato.
- `extraction_noise`: no es un cambio de contenido real, artefacto de extraccion del PDF.

Diferencia de diseno respecto a los manuales de campos: no hace falta `_field_name_lookup`
releyendo Modulo 3 -el contexto para el prompt (la ruta de seccion `path`) ya viene incluido
en cada `paragraph_content_changed` directo desde Modulo 4, no hay un campo separado que
resolver.

Red de seguridad deterministica (`_find_disappeared_content`), identica a los otros manuales:
si el LLM dice `editorial_reword`/`extraction_noise` pero un tramo de 5+ palabras del texto
viejo no tiene equivalente en el nuevo, se anula el veredicto del LLM y se fuerza
`business_rule_change`, registrado en `safety_net_override`.

**Filtro de "redistribucion dentro de la seccion" (agregado 2026-09-04, ver
[[dev-phase-considerations]] punto 8 residuo (b))**: investigando los `safety_net_override`
que quedaban tras el fix N:M de Modulo 3 (item 13, 2026-08-25) se encontro que 9 de 11 casos
reales NO eran contenido genuinamente desaparecido -el tramo "desaparecido" del par
emparejado seguia existiendo, intacto, en OTRO parrafo (no adyacente) de la MISMA seccion
nueva. El reflow por bloque contiguo de Modulo 3 no puede capturar esto porque el
`SequenceMatcher` alinea la secuencia completa -si un fragmento se redistribuye a un parrafo
lejano en vez del inmediato vecino, no cae en el mismo bloque `"replace"`. Fix: antes de
decidir el override, cada tramo "desaparecido" se busca (substring exacto, normalizado) en
`section_new_paragraphs` (todos los parrafos de la seccion nueva, agregado por Modulo 4 como
contexto) -si aparece ahi, NO cuenta como desaparecido para el override (se guarda aparte, en
`content_relocated_within_section`, para trazabilidad). Solo el residuo genuino (no
encontrado en ningun lado de la seccion nueva) sigue forzando `business_rule_change`.
Verificado con datos reales: de 11 overrides en el corpus completo antes del fix, 9 eran este
patron (confirmado buscando cada tramo contra la seccion completa de la edicion nueva antes de
tocar codigo), 2 eran remocion real (confirmado que no aparecen en NINGUNA seccion de toda la
edicion nueva, no solo la misma seccion).

Alcance: procesa todos los pares ya generados por el Modulo 4 en `data/04_deteccion_cambios/`.
Requiere Ollama corriendo en localhost:11434 con el modelo `qwen3:4b` ya descargado. Volumen
mucho mayor que los otros manuales (304 parrafos en los 6 pares, vs. 26-554 en los manuales de
campos) -se corre en background por el tiempo que toma la inferencia local.
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

WHITESPACE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip().casefold()


MANUAL_SLUG = "international_full_service_pos_online_messages_processing_specifications"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"
OLLAMA_TIMEOUT_SECONDS = 120

VALID_CATEGORIES = {"business_rule_change", "editorial_reword", "extraction_noise"}
MIN_DISAPPEARED_WORDS = 5

TARGET_CHANGE_TYPES = {"paragraph_content_changed"}

PROMPT_TEMPLATE = """Sos un asistente que clasifica cambios de texto en un manual de especificaciones de procesamiento de Visa (Full Service POS Online Messages Processing Specifications, International) -un documento narrativo de reglas de negocio y flujos de procesamiento de transacciones, no una grilla de campos.

Seccion: {path}

Texto en la edicion VIEJA:
\"\"\"{old}\"\"\"

Texto en la edicion NUEVA:
\"\"\"{new}\"\"\"

Clasifica este cambio en EXACTAMENTE una de estas 3 categorias:
- business_rule_change: el significado o regla de negocio cambio de verdad (ej. una condicion de procesamiento cambio, un requisito nuevo, un valor o codigo distinto).
- editorial_reword: dice lo mismo, solo cambio la redaccion, el orden de palabras o el formato.
- extraction_noise: no es un cambio de contenido real, es un artefacto de extraccion de PDF (texto cortado, fragmentos, espaciado raro -comun en fragmentos de diagramas/tablas en este manual).

Responde SOLO con este JSON, sin texto adicional: {{"category": "...", "reason": "..."}}
La razon debe ser 1 oracion corta en español."""


def _ollama_classify(path: str, old: str, new: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(path=path, old=old, new=new)
    return ollama_classify(prompt, VALID_CATEGORIES)


def _find_disappeared_content(old_text: str, new_text: str) -> list:
    return find_disappeared_content(old_text, new_text, min_words=MIN_DISAPPEARED_WORDS)


def _split_relocated(disappeared: list, section_new_paragraphs: list) -> tuple:
    """Separa los tramos "desaparecidos" que en realidad se redistribuyeron a OTRO parrafo de
    la misma seccion nueva (ver docstring del modulo) de los genuinamente ausentes. Devuelve
    (genuinamente_desaparecido, redistribuido)."""
    if not section_new_paragraphs:
        return disappeared, []
    normalized_new = [_normalize_text(p) for p in section_new_paragraphs]
    genuinely_disappeared, relocated = [], []
    for chunk in disappeared:
        chunk_norm = _normalize_text(chunk)
        if any(chunk_norm in p for p in normalized_new):
            relocated.append(chunk)
        else:
            genuinely_disappeared.append(chunk)
    return genuinely_disappeared, relocated


def classify_change(change: dict) -> dict:
    path_str = " > ".join(change["path"])
    ai = _ollama_classify(path_str, change["old"], change["new"])

    disappeared = _find_disappeared_content(change["old"], change["new"])
    genuinely_disappeared, relocated = _split_relocated(
        disappeared, change.get("section_new_paragraphs", [])
    )
    override = ai["category"] in ("editorial_reword", "extraction_noise") and bool(genuinely_disappeared)

    enriched = {k: v for k, v in change.items() if k != "section_new_paragraphs"}
    enriched["ai_category"] = "business_rule_change" if override else ai["category"]
    enriched["ai_reason"] = ai["reason"]
    enriched["disappeared_content"] = genuinely_disappeared
    if relocated:
        enriched["content_relocated_within_section"] = relocated
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
