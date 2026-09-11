"""Deteccion de a que manual conocido pertenece un PDF, por nombre de archivo primero y
contenido de portada como respaldo. Logica pura (sin efectos secundarios) -- land.py decide
que hacer con el resultado.

Algoritmo (validado con datos reales, ver poc/router/CONTRACT.md y NOTES.md del repo): compara
sets de palabras normalizadas por CONTENCION DE SUBCONJUNTO, no por igualdad ni substring
ordenado -- el nombre de archivo y el texto de portada real no siempre preservan el orden ni la
puntuacion exacta del titulo registrado (ej. "International" aparece al principio del nombre de
archivo mismo cuando el titulo registrado lo tiene al final), y a veces el nombre de archivo
tiene palabras extra alrededor del titulo real (ej. "(Reference Guide - Release 4)"). La
contencion de subconjunto tolera ambos casos sin perder precision entre los 2 pares de titulos
casi-identicos del corpus (TC 01-49 vs TC 50-92, VSS Volumen 1 vs Volumen 2), porque exige que
TODOS los tokens distintivos del titulo (ej. "01"/"49" vs "50"/"92") esten presentes.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from run import MANUALS

# slug -> lista de variantes de titulo aceptadas. Arranca con 1 sola variante por slug (el
# MANUAL_TITLE ya usado en run.py/report.py). Si una edicion futura trae un formato de portada
# nuevo que no matchea ninguna variante existente, agregar la variante nueva a la lista de su
# slug es la forma prevista de extender la deteccion sin tocar la logica de matching.
TITLE_VARIANTS: dict[str, list[str]] = {slug: [title] for slug, title in MANUALS.items()}

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_tokens(text: str) -> set[str]:
    return set(_NON_ALNUM.sub(" ", text.lower()).split())


def match_registry(tokens: set[str]) -> list[str]:
    return [
        slug
        for slug, variants in TITLE_VARIANTS.items()
        if any(normalize_tokens(variant) <= tokens for variant in variants)
    ]


def detect_from_filename(pdf_path: Path) -> list[str]:
    stem = pdf_path.stem
    parts = stem.split(" - ", 1)
    title_part = parts[1] if len(parts) == 2 else stem
    return match_registry(normalize_tokens(title_part))


def detect_from_content(pdf_path: Path, max_pages: int = 3) -> list[str]:
    import fitz

    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return []
    text = "".join(doc[i].get_text() for i in range(min(max_pages, len(doc))))
    return match_registry(normalize_tokens(text))


@dataclass
class DetectionResult:
    slug: Optional[str]
    method: Optional[str]  # "filename" | "content" | None
    candidates: list[str] = field(default_factory=list)


def detect_manual(pdf_path: Path) -> DetectionResult:
    filename_candidates = detect_from_filename(pdf_path)
    if len(filename_candidates) == 1:
        return DetectionResult(filename_candidates[0], "filename", filename_candidates)

    content_candidates = detect_from_content(pdf_path)
    if len(content_candidates) == 1:
        return DetectionResult(content_candidates[0], "content", content_candidates)

    # Preferir mostrar los candidatos de contenido en la alerta (suele tener mas contexto que
    # el nombre de archivo), si no hubo ninguno mostrar los de nombre de archivo.
    candidates = content_candidates or filename_candidates
    return DetectionResult(None, None, candidates)
