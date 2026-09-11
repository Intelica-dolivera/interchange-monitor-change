"""
06_classify_changes.py
Stage 6 — AI classification of criteria changes.

Reads diff_results.json and classifies each criteria_change using
Ollama. When criteria text references tables (Table X-Y), their
contents are resolved and included in the AI prompt so the model
can compare actual values (MCCs, products, countries) rather than
just table reference numbers.

Labels:
  - criteria_real_change:    condition genuinely changed, impacts Excel
  - criteria_clarification:  same condition, new note/context added
  - criteria_reword:         same meaning, different wording
  - extraction_noise:        difference caused by Docling, not Visa

Usage:
    python src/guides_change_control/interpretation/06_classify_changes.py \
        --jurisdiction Interregional \
        --model qwen3:4b
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


# ---------------------------------------------------------------------------
# JSON Schema
# ---------------------------------------------------------------------------

CLASSIFICATION_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "label": {
            "type": "string",
            "enum": [
                "criteria_real_change",
                "criteria_clarification",
                "criteria_reword",
                "extraction_noise",
            ],
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
        "reason": {
            "type": "string",
            "description": "One concise sentence identifying the concrete difference in business terms.",
        },
        "business_impact": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Describe the specific business impact (e.g. which MCCs, products, countries changed). Null if no real change.",
        },
    },
    "required": ["label", "confidence", "reason", "business_impact"],
    "additionalProperties": False,
}

OLLAMA_URL = "http://localhost:11434/api/chat"

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You review diffs between two versions of a Visa interchange fee guide PDF.
Text was extracted by Docling, which may introduce artifacts.

Classify each criteria change as exactly one of:

- criteria_real_change: A condition genuinely changed — different MCCs, different
  products, different countries, different transaction types, different thresholds,
  eligibility added or removed. Requires updating the business rules Excel file.

- criteria_clarification: Same condition, but a new explanatory note, default value,
  or additional context was added. No core rule change. May need a note in
  OTHER_CRITERIA_APPLIES column.

- criteria_reword: Exactly the same meaning, different wording. Table reference
  renumbering alone (Table 5-8 → Table 5-10) is criteria_reword ONLY IF the
  table contents are the same. If table contents changed, classify as
  criteria_real_change.

- extraction_noise: Difference caused by PDF extraction artifacts only.

CRITICAL RULES:
1. When referenced table contents are provided, compare them directly.
   If table contents differ (different MCCs, products, etc.) → criteria_real_change.
   If table contents are identical → the reference change is just renumbering → criteria_reword.
2. Compare business meaning, not raw text similarity.
3. In reason and business_impact, name the specific values that changed
   (e.g. "MCC 7011 Lodging removed from exclusion list") not just
   "table reference changed".
4. Return only valid JSON matching the schema. No markdown or preamble."""


def build_prompt(change: Dict[str, Any]) -> str:
    program_name = change.get("program_name", "")
    table_title  = change.get("table_title", "")
    old_text     = change.get("old_text", "")[:1200]
    new_text     = change.get("new_text", "")[:1200]

    prompt = (
        f"Program: {program_name}\n"
        f"Criteria table: {table_title}\n\n"
        f"OLD CRITERIA TEXT:\n{old_text}\n\n"
        f"NEW CRITERIA TEXT:\n{new_text}\n"
    )

    # Include resolved table contents if available
    referenced = change.get("referenced_tables", {})
    if referenced:
        prompt += "\n\nREFERENCED TABLE CONTENTS (resolved from the guide):\n"
        for table_id, contents in referenced.items():
            old_content = contents.get("old", "")[:600]
            new_content = contents.get("new", "")[:600]
            is_unchanged = contents.get("unchanged", False)

            if is_unchanged:
                prompt += f"\n{table_id} — UNCHANGED between versions:\n{old_content}\n"
            else:
                prompt += f"\n{table_id} — CHANGED between versions:\n"
                prompt += f"  OLD: {old_content}\n"
                prompt += f"  NEW: {new_content}\n"

    prompt += f"\n\nJSON SCHEMA REQUIRED:\n{json.dumps(CLASSIFICATION_JSON_SCHEMA, separators=(',', ':'))}"
    return prompt


# ---------------------------------------------------------------------------
# Safety net
# ---------------------------------------------------------------------------

def _significant_lines(text: str) -> List[str]:
    lines = []
    for raw in (text or "").split("\n"):
        line = raw.strip().lstrip("\u00b7\u2022-").strip()
        if len(line) >= 25:
            lines.append(line)
    return lines


def _has_close_match(line: str, candidates: List[str]) -> bool:
    key_words = set(re.findall(r"[a-zA-Z]{4,}", line.lower()))
    if not key_words:
        return True
    for cand in candidates:
        cand_words = set(re.findall(r"[a-zA-Z]{4,}", cand.lower()))
        overlap = len(key_words & cand_words) / len(key_words)
        if overlap >= 0.6:
            return True
    return False


def detect_disappeared_content(old_text: str, new_text: str) -> bool:
    old_lines = _significant_lines(old_text)
    new_lines = _significant_lines(new_text)
    if not old_lines or not new_lines:
        return False
    for line in old_lines:
        if not _has_close_match(line, new_lines):
            return True
    for line in new_lines:
        if not _has_close_match(line, old_lines):
            return True
    return False


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

def call_ollama(model: str, change: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "model":    model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": build_prompt(change)},
        ],
        "stream":     False,
        "think":      False,
        "keep_alive": "30m",
        "format":     CLASSIFICATION_JSON_SCHEMA,
        "options": {
            "temperature": 0.0,
            "seed":        42,
            "num_ctx":     8192,
            "num_predict": 400,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()
        body    = response.json()
        content = body["message"]["content"]
        parsed  = json.loads(content)

        label      = parsed.get("label", "extraction_noise")
        confidence = parsed.get("confidence", "low")
        reason     = parsed.get("reason", "")
        impact     = parsed.get("business_impact")

        # Safety net
        if label == "extraction_noise" and confidence == "high":
            if detect_disappeared_content(
                change.get("old_text", ""),
                change.get("new_text", ""),
            ):
                confidence = "low"
                reason += " [auto-flagged: content disappeared]"

        return {
            "label":           label,
            "confidence":      confidence,
            "reason":          reason,
            "business_impact": impact,
        }

    except Exception as e:
        return {
            "label":           "extraction_noise",
            "confidence":      "low",
            "reason":          f"AI call failed: {str(e)[:200]}",
            "business_impact": None,
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 6: AI classification of criteria changes"
    )
    parser.add_argument("--jurisdiction", required=True)
    parser.add_argument("--backend", default="ollama", choices=["ollama"])
    parser.add_argument("--model", default="qwen3:4b")
    args = parser.parse_args()

    jurisdiction = args.jurisdiction
    output_dir   = Path("data/output") / jurisdiction
    suffix       = f"_{jurisdiction.lower()}"

    input_path  = output_dir / f"diff_results{suffix}.json"
    output_path = output_dir / f"classified_changes{suffix}.json"

    if not input_path.exists():
        print(f"[ERROR] Not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[Stage 6] Loading diff results for {jurisdiction} ...")
    with input_path.open("r", encoding="utf-8") as f:
        diff = json.load(f)

    criteria_changes = diff.get("criteria_changes", [])
    to_classify  = [c for c in criteria_changes if c.get("change_type") == "criteria_changed"]
    passthrough  = [c for c in criteria_changes if c.get("change_type") != "criteria_changed"]

    print(f"[Stage 6] To classify: {len(to_classify)} | Passthrough: {len(passthrough)}")
    print(f"[Stage 6] With resolved table refs: {sum(1 for c in to_classify if c.get('referenced_tables'))}")
    print(f"[Stage 6] Model: {args.model}")
    print()

    classified: List[Dict[str, Any]] = []

    for i, change in enumerate(to_classify):
        program_name = change.get("program_name", "")
        ratio        = change.get("ratio", 0.0)
        has_refs     = bool(change.get("referenced_tables"))

        print(f"  [{i+1}/{len(to_classify)}] {program_name[:50]} | ratio={ratio:.3f} | refs={'yes' if has_refs else 'no'}")

        result = call_ollama(args.model, change)
        classified.append({**change, **result})

        conf_str = f" ({result['confidence']})"
        print(f"           → {result['label']}{conf_str}: {result['reason'][:90]}")
        if result.get("business_impact"):
            print(f"             impact: {result['business_impact'][:90]}")
        time.sleep(0.2)

    for c in passthrough:
        classified.append({
            **c,
            "label":           c["change_type"],
            "confidence":      "high",
            "reason":          "Deterministic — table added or removed between versions",
            "business_impact": None,
        })

    output = {**diff, "criteria_changes": classified}

    label_counts: Dict[str, int] = {}
    for c in classified:
        label = c.get("label", "unknown")
        label_counts[label] = label_counts.get(label, 0) + 1

    print(f"\n[Stage 6] Classification summary:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label:<35} {count}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[Stage 6] Output written to {output_path}")


if __name__ == "__main__":
    main()