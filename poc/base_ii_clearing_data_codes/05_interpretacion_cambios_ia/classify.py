"""
Modulo 5 - Interpretacion de cambios (IA) para el manual base_ii_clearing_data_codes.

Toma la salida ya deterministica del Modulo 4 y le agrega, SOLO a los cambios de tipo
`code_content_changed` (celdas de contenido que difieren por debajo del umbral de similitud
0.98), una clasificacion semantica hecha por un LLM local (Ollama, `qwen3:4b`, JSON
forzado, `think:false`, temperatura 0). El resto de los tipos de cambio (`table_added`,
`table_removed`, `table_renamed`, `code_added`, `code_removed`, `duplicate_code_warning`)
son decisiones estructurales ya deterministicas del Modulo 3/4 y pasan sin tocar -el mismo
principio de separacion de responsabilidades que usa el pipeline de referencia
(`utils_example/06_classify_changes.py`): la IA solo interpreta matices de texto libre,
nunca decide altas/bajas estructurales.

Categorias (adaptadas para este manual de tablas de codigo; ver nota de diseno abajo sobre
por que difieren de las 4 propuestas originalmente en la memoria del proyecto):

- `business_rule_change`: el significado o valor de negocio cambio de verdad (ej. un monto
  maximo subio, la definicion de un codigo paso a significar otra cosa).
- `editorial_reword`: mismo significado, solo cambio la redaccion/formato/orden de palabras.
- `extraction_noise`: no es un cambio real de contenido -es un artefacto de extraccion del
  PDF (fragmentos de linea, espaciado, orden de palabras roto por el layout) que paso el
  umbral de similitud del Modulo 4 por casualidad.

Nota de diseno: la memoria del proyecto (sesion de diseno inicial, antes de que existiera
el Modulo 4 real) proponia 4 categorias -`structural_change`, `business_rule_change`,
`editorial_reword`, `extraction_noise`- en lugar de las 4 del pipeline de referencia. Se
descarto `structural_change` para este modulo: a nivel de fila de una tabla de codigos, un
cambio "estructural" (alta/baja de codigo, tabla renombrada) ya lo detecta el Modulo 4 de
forma 100% deterministica y JAMAS llega a este clasificador (solo le llegan
`code_content_changed`, que por definicion ya son texto de una celda que cambio, no altas/
bajas). Meter una 4ta categoria "estructural" ahi generaria ambiguedad sin un caso real que
la use. Si mas adelante se agrega Modulo 2/3/4 para un manual Tipo A (grids de posicion),
ahi si puede hacer falta -un cambio de longitud de campo es "estructural" en un sentido que
no aplica a una tabla de codigos.

Red de seguridad deterministica (`_find_disappeared_content`, tomada del pipeline de
referencia: `detect_disappeared_content` en `utils_example/06_classify_changes.py`): si el
LLM clasifica un cambio como `editorial_reword` o `extraction_noise` (osea "no cambio nada
importante") pero un tramo de 5+ palabras consecutivas del texto viejo no tiene ningun
equivalente en el texto nuevo (via `difflib.SequenceMatcher` a nivel de palabra, buscando
operaciones "delete"/"replace" largas), se anula la clasificacion del LLM y se fuerza
`business_rule_change` -contenido que desaparece sin reemplazo casi nunca es un simple
reformateo. Esto corre SIEMPRE, sin importar lo que diga el LLM, y queda registrado en la
salida (`safety_net_override`) para que quede trazable cuando el LLM se equivoco.

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

MANUAL_SLUG = "base_ii_clearing_data_codes"
INPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "04_deteccion_cambios"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "05_interpretacion_cambios_ia"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"
OLLAMA_TIMEOUT_SECONDS = 120

VALID_CATEGORIES = {"business_rule_change", "editorial_reword", "extraction_noise"}
MIN_DISAPPEARED_WORDS = 5
BULLET_GLYPH_TOKENS = {"l", "●", "•"}

PROMPT_TEMPLATE = """Sos un asistente que clasifica cambios de texto en una tabla de codigos de un manual tecnico de Visa (BASE II Clearing Data Codes).

Tabla: {table}
Codigo: {code}
Columna que cambio: {column}

Texto en la edicion VIEJA:
\"\"\"{old}\"\"\"

Texto en la edicion NUEVA:
\"\"\"{new}\"\"\"

Clasifica este cambio en EXACTAMENTE una de estas 3 categorias:
- business_rule_change: el significado o valor de negocio cambio de verdad (ej. un monto, un limite, una condicion, el significado de un codigo).
- editorial_reword: dice lo mismo, solo cambio la redaccion, el orden de palabras o el formato.
- extraction_noise: no es un cambio de contenido real, es un artefacto de extraccion de PDF (texto cortado, fragmentos, espaciado raro).

Responde SOLO con este JSON, sin texto adicional: {{"category": "...", "reason": "..."}}
La razon debe ser 1 oracion corta en español. Si el cambio involucra un numero largo (monto,
codigo, cantidad de digitos), NO lo vuelvas a escribir en la razon -referite a el como "el valor
anterior"/"el valor nuevo" en vez de repetir los digitos, para evitar errores de transcripcion."""


def _ollama_classify(table: str, code: str, column: str, old: str, new: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(table=table, code=code, column=column, old=old, new=new)
    return ollama_classify(prompt, VALID_CATEGORIES)


def _find_disappeared_content(old_text: str, new_text: str) -> list:
    """Tramos de MIN_DISAPPEARED_WORDS+ palabras del texto viejo sin equivalente en el nuevo.

    Los glifos de vinieta que PyMuPDF extrae como palabra suelta (ej. "l" en filas EDQP con
    listas largas) se descartan antes de diffear: su posicion entre viñeta y campo cambia de
    edicion a edicion por reflow de pagina, sin ningun cambio de contenido real, y contaminaban
    tanto el conteo del umbral como el texto de evidencia guardado.

    Cuenta tanto "delete" (texto viejo que desaparece sin nada en su lugar) como "replace"
    (texto viejo reemplazado por texto nuevo totalmente distinto, sin ninguna palabra en
    comun) -gap real encontrado en un inventario de duplicacion entre los 8 pipelines
    (2026-09-03): este manual es copia casi textual del `classify.py` de
    `base_ii_clearing_edit_package_messages`, que ya tenia este fix (item 7 del TODO,
    ficha V0407/V1209/glosario "optional issuer fee") desde 2026-08-25 -la propia nota de
    ese fix ya marcaba "aplica probablemente a este manual tambien" como pendiente de
    verificar, sin portarlo. El umbral de 5 palabras se mantiene sin cambios para "replace"
    (misma calibracion ya validada alla): un escaneo del corpus de ese otro manual encontro
    que los "replace" cortos (3-4 palabras) que pasarian un umbral mas bajo son mayormente
    renombres/abreviaturas inocuos, asi que no se toco aca tampoco.
    """
    return find_disappeared_content(
        old_text, new_text, min_words=MIN_DISAPPEARED_WORDS, bullet_glyph_tokens=BULLET_GLYPH_TOKENS
    )


def classify_change(change: dict) -> dict:
    ai = _ollama_classify(
        table=change["table"],
        code=change["code"],
        column=change["column"],
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


def classify_pair(match_result: dict, progress_prefix: str = "") -> dict:
    changes = []
    content_changes = [c for c in match_result["changes"] if c["change_type"] == "code_content_changed"]
    total = len(content_changes)
    done = 0
    for change in match_result["changes"]:
        if change["change_type"] != "code_content_changed":
            changes.append(change)
            continue
        changes.append(classify_change(change))
        done += 1
        if progress_prefix:
            print(f"{progress_prefix} {done}/{total}", file=sys.stderr)

    summary = dict(match_result["summary"])
    ai_summary = {}
    for change in changes:
        if change["change_type"] == "code_content_changed":
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
        if limit is not None:
            content_idx = [
                i for i, c in enumerate(match_result["changes"]) if c["change_type"] == "code_content_changed"
            ]
            drop = set(content_idx[limit:])
            match_result["changes"] = [c for i, c in enumerate(match_result["changes"]) if i not in drop]

        result = classify_pair(match_result, progress_prefix=f"[{input_path.stem}]")

        out_path = OUTPUT_DIR / input_path.name
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))

        ai_summary_str = ", ".join(f"{k}={v}" for k, v in sorted(result["ai_summary"].items()))
        overrides = sum(
            1
            for c in result["changes"]
            if c.get("change_type") == "code_content_changed" and c.get("safety_net_override")
        )
        print(f"{input_path.name}: {ai_summary_str} (safety_net_override={overrides})")


if __name__ == "__main__":
    main()
