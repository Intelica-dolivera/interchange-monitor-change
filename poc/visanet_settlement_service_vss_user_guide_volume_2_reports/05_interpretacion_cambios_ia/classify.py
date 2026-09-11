"""
Modulo 5 - Interpretacion de cambios (IA) para el manual
visanet_settlement_service_vss_user_guide_volume_2_reports.

Clasifica con un LLM local (Ollama, `qwen3:4b`, JSON forzado, `think:false`, temperatura 0)
los cambios `row_content_changed` que produjo Modulo 4 -unico tipo de cambio de contenido en
este manual (a diferencia del 7mo manual, que tenia parrafos Y pares; aca los parrafos solo se
agregan/quitan, nunca se diffean por contenido, ver Modulo 3). Mismas 3 categorias que el
resto del proyecto (business_rule_change/editorial_reword/extraction_noise) y misma red de
seguridad deterministica (`_find_disappeared_content`, override a business_rule_change si
desaparecen 5+ palabras sin reemplazo).

**Un solo prompt generico para los 5 apendices**, a diferencia del 7mo manual (que necesito 2
prompts distintos para parrafo vs. par) -aca CADA cambio ya trae exactamente el mismo shape
(apendice + tabla + fila + columna + texto viejo/nuevo, ver Modulo 4), asi que un solo
template parametrizado alcanza sin perder contexto especifico por apendice.

Alcance: procesa todos los pares ya generados por Modulo 4 en `data/04_deteccion_cambios/`.
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

MANUAL_SLUG = "visanet_settlement_service_vss_user_guide_volume_2_reports"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"

APPENDICES = ["appendix_a", "appendix_b", "appendix_c", "appendix_d", "appendix_e"]

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"
OLLAMA_TIMEOUT_SECONDS = 120

VALID_CATEGORIES = {"business_rule_change", "editorial_reword", "extraction_noise"}
MIN_DISAPPEARED_WORDS = 5

APPENDIX_LABELS = {
    "appendix_a": "Apendice A: VSS Reports - Formatos Listos para Imprimir",
    "appendix_b": "Apendice B: VSS Reports - Formatos de Lectura por Maquina",
    "appendix_c": "Apendice C: Codigos VSS",
    "appendix_d": "Apendice D: Reportes SMS y Datos Crudos",
    "appendix_e": "Apendice E: Referencia Cruzada de Tipos de Transaccion",
}

PROMPT = """Sos un asistente que clasifica cambios de contenido en una tabla de referencia de un manual de settlement de Visa (VisaNet Settlement Service (VSS) User Guide, Volume 2, Reports).

Seccion: {appendix_label}
Tabla: {table_title}
Fila (identificador): {key}
Columna que cambio: {column}

Valor en la edicion VIEJA:
\"\"\"{old}\"\"\"

Valor en la edicion NUEVA:
\"\"\"{new}\"\"\"

Clasifica este cambio en EXACTAMENTE una de estas 3 categorias:
- business_rule_change: el significado, valor o regla de negocio cambio de verdad.
- editorial_reword: dice lo mismo, solo cambio la redaccion, el formato, mayusculas/minusculas o el orden de palabras.
- extraction_noise: no es un cambio de contenido real, es un artefacto de extraccion de PDF (texto cortado, fragmentos, espaciado raro, valores vacios sin razon aparente).

Responde SOLO con este JSON, sin texto adicional: {{"category": "...", "reason": "..."}}
La razon debe ser 1 oracion corta en español."""


def _ollama_classify(prompt: str) -> dict:
    return ollama_classify(prompt, VALID_CATEGORIES)


def _find_disappeared_content(old_text: str, new_text: str) -> list:
    return find_disappeared_content(old_text, new_text, min_words=MIN_DISAPPEARED_WORDS)


def classify_change(appendix: str, change: dict) -> dict:
    prompt = PROMPT.format(
        appendix_label=APPENDIX_LABELS[appendix],
        table_title=change["table_title"],
        key=change["key"],
        column=change["column"],
        old=change["old"],
        new=change["new"],
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


def classify_edition_pair(detect_result: dict, progress_prefix: str = "") -> dict:
    total = sum(
        1 for a in detect_result["appendices"].values() for c in a if c["change_type"] == "row_content_changed"
    )
    done = 0

    appendices_out = {}
    for appendix in APPENDICES:
        changes = []
        for change in detect_result["appendices"].get(appendix, []):
            if change["change_type"] != "row_content_changed":
                changes.append(change)
                continue
            changes.append(classify_change(appendix, change))
            done += 1
            if progress_prefix:
                print(f"{progress_prefix} {done}/{total}", file=sys.stderr)
        appendices_out[appendix] = changes

    ai_summary = {}
    for changes in appendices_out.values():
        for change in changes:
            if change["change_type"] == "row_content_changed":
                ai_summary[change["ai_category"]] = ai_summary.get(change["ai_category"], 0) + 1

    result = dict(detect_result)
    result["appendices"] = appendices_out
    result["ai_summary"] = ai_summary
    return result


def main():
    input_paths = sorted(INPUT_DIR.glob("*.json"))
    if not input_paths:
        print(f"No se encontraron cambios detectados en {INPUT_DIR}", file=sys.stderr)
        sys.exit(1)

    only = None
    limit = None
    for arg in sys.argv[1:]:
        if arg.startswith("--only="):
            only = arg.split("=", 1)[1]
        elif arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])

    if only:
        input_paths = [p for p in input_paths if p.stem == only]
        if not input_paths:
            print(f"No se encontro el par {only!r} en {INPUT_DIR}", file=sys.stderr)
            sys.exit(1)

    ensure_ollama_running()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for input_path in input_paths:
        detect_result = json.loads(input_path.read_text())

        if limit is not None:
            for appendix in APPENDICES:
                changes = detect_result["appendices"].get(appendix, [])
                kept, remaining = 0, []
                for c in changes:
                    if c["change_type"] == "row_content_changed" and kept < limit:
                        remaining.append(c)
                        kept += 1
                    elif c["change_type"] != "row_content_changed":
                        remaining.append(c)
                detect_result["appendices"][appendix] = remaining

        result = classify_edition_pair(detect_result, progress_prefix=f"[{input_path.stem}]")

        out_path = OUTPUT_DIR / input_path.name
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

        ai_summary_str = ", ".join(f"{k}={v}" for k, v in sorted(result["ai_summary"].items()))
        overrides = sum(
            1
            for changes in result["appendices"].values()
            for c in changes
            if c.get("change_type") == "row_content_changed" and c.get("safety_net_override")
        )
        print(f"{input_path.name}: {ai_summary_str} (safety_net_override={overrides})")


if __name__ == "__main__":
    main()
