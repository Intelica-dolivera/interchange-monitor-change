"""Cliente Ollama compartido para la etapa 05 (interpretacion de cambios via IA), extraido
tras confirmar que el nucleo HTTP (payload/request/parsing/fallback de categoria invalida) y el
chequeo de conectividad son identicos en los 7 manuales que usan un LLM
(base_ii_transactions_quick_reference es 100% deterministico, sin IA, y no importa este modulo).

Cada manual sigue armando su propio prompt (PROMPT_TEMPLATE + argumentos distintos por manual)
-- eso sigue siendo bespoke a proposito, ver CONTRACT.md.

Incluye tambien find_disappeared_content, la red de seguridad deterministica de Modulo 5. Al
consolidarla aca se corrige un bug real encontrado el 2026-09-04: 5 de los 7 manuales solo
contaban operaciones "delete" (texto que desaparece sin reemplazo), no "replace" (texto
reemplazado por otro totalmente distinto sin palabras en comun) -- un reemplazo real de
contenido de negocio podia pasar inadvertido en esos 5. Medido contra el corpus real antes de
este fix: 14 casos concretos que pasan de "editorial_reword" (sin cambio real) a
"business_rule_change" forzado bajo la logica corregida.

Backend configurable via LLM_BACKEND (2026-09-10, prueba puntual con Gemini): default "ollama"
(qwen3:4b local, comportamiento de siempre). Con LLM_BACKEND=openrouter + OPENROUTER_API_KEY
seteada, ensure_ollama_running/ollama_classify despachan a OpenRouter (Gemini) en su lugar, sin
que los 7 classify.py que importan estas funciones por nombre se enteren. Volver a qwen es no
setear esas 2 variables de entorno -- cero cambios de codigo.
"""
import difflib
import json
import os
import sys
import time
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:4b"
OLLAMA_TIMEOUT_SECONDS = 120

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "google/gemini-2.5-flash-lite"
OPENROUTER_TIMEOUT_SECONDS = 120
OPENROUTER_MAX_TOKENS = 600
OPENROUTER_MAX_RETRIES = 3

LLM_BACKEND = os.environ.get("LLM_BACKEND", "ollama")


def ensure_ollama_running() -> None:
    """Aborta con exit code 1 si el backend activo (Ollama por defecto, u OpenRouter si
    LLM_BACKEND=openrouter) no esta disponible. El mensaje de error ya es estandar en los 7
    manuales."""
    if LLM_BACKEND == "openrouter":
        if not os.environ.get("OPENROUTER_API_KEY"):
            print("LLM_BACKEND=openrouter pero falta OPENROUTER_API_KEY.", file=sys.stderr)
            sys.exit(1)
        return
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5)
    except (urllib.error.URLError, ConnectionRefusedError) as exc:
        print(f"No se pudo conectar a Ollama en localhost:11434: {exc}", file=sys.stderr)
        print("Verifica que el servicio este corriendo: systemctl status ollama", file=sys.stderr)
        sys.exit(1)


def _resolve_category(parsed: dict, valid_categories: set) -> dict:
    category = parsed.get("category")
    reason = parsed.get("reason", "")
    if category not in valid_categories:
        return {
            "category": "extraction_noise",
            "reason": f"[categoria invalida del LLM: {category!r}] {reason}",
        }
    return {"category": category, "reason": reason}


def _ollama_classify(prompt: str, valid_categories: set) -> dict:
    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {"temperature": 0},
        }
    ).encode()

    request = urllib.request.Request(
        OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=OLLAMA_TIMEOUT_SECONDS) as response:
        body = json.loads(response.read())

    parsed = json.loads(body["response"])
    return _resolve_category(parsed, valid_categories)


def _openrouter_classify(prompt: str, valid_categories: set) -> dict:
    """A diferencia de Ollama local, OpenRouter es una API de red: puede devolver una respuesta
    truncada/incompleta de forma transitoria (visto en la practica: JSON cortado a mitad de
    string en un item con prompt largo, que en un reintento identico salio limpio). Reintenta
    con backoff antes de propagar el error."""
    payload = json.dumps(
        {
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": OPENROUTER_MAX_TOKENS,
            "response_format": {"type": "json_object"},
        }
    ).encode()

    request = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        },
    )

    last_error = None
    for attempt in range(OPENROUTER_MAX_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=OPENROUTER_TIMEOUT_SECONDS) as response:
                body = json.loads(response.read())
            parsed = json.loads(body["choices"][0]["message"]["content"])
            return _resolve_category(parsed, valid_categories)
        except (json.JSONDecodeError, KeyError, IndexError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < OPENROUTER_MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    raise last_error


def ollama_classify(prompt: str, valid_categories: set) -> dict:
    """Payload + request + parsing + fallback de categoria invalida -- identico en los 7
    manuales con IA salvo el prompt en si, que cada uno arma con su propio PROMPT_TEMPLATE.
    Despacha a Ollama u OpenRouter segun LLM_BACKEND (ver docstring del modulo)."""
    if LLM_BACKEND == "openrouter":
        return _openrouter_classify(prompt, valid_categories)
    return _ollama_classify(prompt, valid_categories)


def find_disappeared_content(
    old_text: str,
    new_text: str,
    min_words: int = 5,
    bullet_glyph_tokens: frozenset = frozenset(),
) -> list:
    """Tramos de min_words+ palabras del texto viejo sin equivalente en el nuevo. Cuenta tanto
    "delete" (desaparece sin nada en su lugar) como "replace" (reemplazado por texto nuevo
    totalmente distinto, sin ninguna palabra en comun) -- ver docstring del modulo para el bug
    que este fix cierra. bullet_glyph_tokens filtra glifos de vinieta que PyMuPDF extrae como
    palabra suelta (hoy solo lo necesita base_ii_clearing_data_codes)."""
    old_words = [w for w in old_text.split() if w not in bullet_glyph_tokens]
    new_words = [w for w in new_text.split() if w not in bullet_glyph_tokens]
    matcher = difflib.SequenceMatcher(None, old_words, new_words)
    deleted = []
    for tag, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if tag in ("delete", "replace") and (i2 - i1) >= min_words:
            deleted.append(" ".join(old_words[i1:i2]))
    return deleted
