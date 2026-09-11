"""
05_diff_descriptors.py
Stage 5 — Detect changes between matched old and new guide descriptors.

Reads matched_descriptors.json and produces diff_results.json with:
  - rate_changes:        fee rate changed for a matched descriptor
  - criteria_changes:    criteria text changed for a matched program
                         (enriched with referenced table contents for AI)
  - program_renames:     program name changed between versions (fuzzy match)
  - descriptor_renames:  descriptor name changed between versions (fuzzy match)
  - added_descriptors:   descriptor present only in new
  - removed_descriptors: descriptor present only in old
  - added_programs:      program present only in new
  - removed_programs:    program present only in old

Usage:
    python src/guides_change_control/change_detection/05_diff_descriptors.py \
        --jurisdiction Interregional
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CRITERIA_CHANGE_THRESHOLD = 0.98
RATE_FIELDS = ["fee_rate_raw"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_rate(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def normalize_criteria_text(text: str) -> str:
    boilerplate = [
        r"visa confidential",
        r"all rights reserved",
        r"interregional interchange guide",
        r"europe intraregional interchange fee guide",
        r"romania interchange fee guide",
        r"visa supplemental requirements",
        r"interchange processing",
        r"©\s*\d{4}\s*visa",
    ]
    result = text
    for pattern in boilerplate:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", result).strip()


def extract_table_refs(text: str) -> List[str]:
    """Extract all Table X-Y references from a criteria text."""
    refs = re.findall(r"Table\s+\d+[-–]\d+", text, re.IGNORECASE)
    return [re.sub(r"[-–]", "-", r).strip() for r in refs]


def build_table_index(structured_guide: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Build a dict {table_id: markdown_text} from a structured guide.
    Only includes tables with a table_id.
    """
    index: Dict[str, str] = {}
    for block in structured_guide:
        table_id = block.get("table_id")
        text     = block.get("text", "")
        title    = block.get("table_title", "")
        if table_id and text:
            # Include title in the text for context
            full = f"{table_id}: {title}\n{text}" if title else text
            index[table_id] = full
    return index


def resolve_table_refs(
    refs: List[str],
    table_index: Dict[str, str],
) -> Dict[str, str]:
    """
    Returns {table_id: content} for each ref found in the index.
    Missing refs get a placeholder.
    """
    resolved: Dict[str, str] = {}
    for ref in refs:
        if ref in table_index:
            resolved[ref] = table_index[ref]
        else:
            resolved[ref] = f"[Table {ref} not found in extracted guide]"
    return resolved


def enrich_criteria_change(
    change: Dict[str, Any],
    old_table_index: Dict[str, str],
    new_table_index: Dict[str, str],
) -> Dict[str, Any]:
    """
    Parse criteria text for Table X-Y references, resolve their contents
    from both old and new structured guides, and add to the change dict.
    """
    old_text = change.get("old_text", "")
    new_text = change.get("new_text", "")

    old_refs = extract_table_refs(old_text)
    new_refs = extract_table_refs(new_text)
    all_refs = sorted(set(old_refs + new_refs))

    if not all_refs:
        return change

    old_resolved = resolve_table_refs(all_refs, old_table_index)
    new_resolved = resolve_table_refs(all_refs, new_table_index)

    # Build a comparison dict only for tables that changed
    table_diffs: Dict[str, Dict[str, str]] = {}
    for ref in all_refs:
        old_content = old_resolved.get(ref, "")
        new_content = new_resolved.get(ref, "")
        if old_content != new_content:
            table_diffs[ref] = {
                "old": old_content,
                "new": new_content,
            }
        else:
            table_diffs[ref] = {
                "old": old_content,
                "new": new_content,
                "unchanged": True,
            }

    return {
        **change,
        "referenced_tables": table_diffs,
    }


# ---------------------------------------------------------------------------
# Diff logic
# ---------------------------------------------------------------------------

def diff_rates(
    old_desc: Dict[str, Any],
    new_desc: Dict[str, Any],
    program_name: str,
    descriptor_name: str,
    descriptor_match_type: str,
) -> Optional[Dict[str, Any]]:
    changes: Dict[str, Any] = {}

    for field in RATE_FIELDS:
        old_val = normalize_rate(old_desc.get(field))
        new_val = normalize_rate(new_desc.get(field))
        if old_val != new_val:
            changes[field] = {"old": old_val, "new": new_val}

    if not changes:
        return None

    return {
        "program_name":          program_name,
        "fee_descriptor":        descriptor_name,
        "descriptor_match_type": descriptor_match_type,
        "rate_changes":          changes,
        "old_fpi":               old_desc.get("fpi", ""),
        "new_fpi":               new_desc.get("fpi", ""),
    }


def diff_criteria(
    old_criteria: List[Dict[str, Any]],
    new_criteria: List[Dict[str, Any]],
    program_name: str,
    old_table_index: Dict[str, str],
    new_table_index: Dict[str, str],
) -> List[Dict[str, Any]]:
    changes = []

    old_by_title = {c.get("table_title", ""): c for c in old_criteria}
    new_by_title = {c.get("table_title", ""): c for c in new_criteria}
    all_titles   = set(old_by_title.keys()) | set(new_by_title.keys())

    for title in all_titles:
        old_c = old_by_title.get(title)
        new_c = new_by_title.get(title)

        if old_c is None and new_c is not None:
            change = {
                "program_name": program_name,
                "table_title":  title,
                "change_type":  "criteria_table_added",
                "old_text":     "",
                "new_text":     new_c.get("text", ""),
                "ratio":        0.0,
            }
            changes.append(enrich_criteria_change(
                change, old_table_index, new_table_index
            ))
            continue

        if new_c is None and old_c is not None:
            change = {
                "program_name": program_name,
                "table_title":  title,
                "change_type":  "criteria_table_removed",
                "old_text":     old_c.get("text", ""),
                "new_text":     "",
                "ratio":        0.0,
            }
            changes.append(enrich_criteria_change(
                change, old_table_index, new_table_index
            ))
            continue

        old_text = normalize_criteria_text(old_c.get("text", ""))
        new_text = normalize_criteria_text(new_c.get("text", ""))

        if old_text == new_text:
            continue

        ratio = fuzzy_ratio(old_text, new_text)
        if ratio < CRITERIA_CHANGE_THRESHOLD:
            change = {
                "program_name": program_name,
                "table_title":  title,
                "change_type":  "criteria_changed",
                "old_text":     old_text,
                "new_text":     new_text,
                "ratio":        round(ratio, 4),
            }
            changes.append(enrich_criteria_change(
                change, old_table_index, new_table_index
            ))

    return changes


# ---------------------------------------------------------------------------
# Main diff
# ---------------------------------------------------------------------------

def run_diff(
    match_result: Dict[str, Any],
    old_table_index: Dict[str, str],
    new_table_index: Dict[str, str],
) -> Dict[str, Any]:
    rate_changes:        List[Dict[str, Any]] = []
    criteria_changes:    List[Dict[str, Any]] = []
    program_renames:     List[Dict[str, Any]] = []
    descriptor_renames:  List[Dict[str, Any]] = []
    added_descriptors:   List[Dict[str, Any]] = []
    removed_descriptors: List[Dict[str, Any]] = []
    added_programs:      List[Dict[str, Any]] = []
    removed_programs:    List[Dict[str, Any]] = []

    for program in match_result.get("matched", []):
        program_name     = program["program_name"]
        program_name_old = program.get("program_name_old", program_name)
        program_match    = program.get("match_type", "exact")

        if program_match == "fuzzy":
            program_renames.append({
                "old_name":    program_name_old,
                "new_name":    program_name,
                "fuzzy_ratio": program.get("fuzzy_ratio", 0.0),
            })

        for match in program.get("matched_descriptors", []):
            old_desc        = match.get("old", {})
            new_desc        = match.get("new", {})
            descriptor_name = match.get("fee_descriptor", "")
            desc_match_type = match.get("match_type", "exact")
            desc_old_name   = match.get("fee_descriptor_old", descriptor_name)

            if desc_match_type == "fuzzy":
                descriptor_renames.append({
                    "program_name":       program_name,
                    "old_fee_descriptor": desc_old_name,
                    "new_fee_descriptor": descriptor_name,
                    "fuzzy_ratio":        match.get("fuzzy_ratio", 0.0),
                })

            rate_change = diff_rates(
                old_desc, new_desc,
                program_name, descriptor_name, desc_match_type,
            )
            if rate_change:
                rate_changes.append(rate_change)

        for item in program.get("added_descriptors", []):
            added_descriptors.append({
                "program_name":   program_name,
                "fee_descriptor": item.get("fee_descriptor", ""),
                "descriptor":     item.get("descriptor", {}),
            })

        for item in program.get("removed_descriptors", []):
            removed_descriptors.append({
                "program_name":   program_name,
                "fee_descriptor": item.get("fee_descriptor", ""),
                "descriptor":     item.get("descriptor", {}),
            })

        crit_changes = diff_criteria(
            program.get("old_criteria", []),
            program.get("new_criteria", []),
            program_name,
            old_table_index,
            new_table_index,
        )
        criteria_changes.extend(crit_changes)

    for program in match_result.get("added", []):
        added_programs.append({
            "program_name": program["program_name"],
            "descriptors":  program.get("descriptors", []),
            "criteria":     program.get("criteria", []),
        })

    for program in match_result.get("removed", []):
        removed_programs.append({
            "program_name": program["program_name"],
            "descriptors":  program.get("descriptors", []),
            "criteria":     program.get("criteria", []),
        })

    return {
        "rate_changes":        rate_changes,
        "criteria_changes":    criteria_changes,
        "program_renames":     program_renames,
        "descriptor_renames":  descriptor_renames,
        "added_descriptors":   added_descriptors,
        "removed_descriptors": removed_descriptors,
        "added_programs":      added_programs,
        "removed_programs":    removed_programs,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 5: Detect changes between matched guide versions"
    )
    parser.add_argument("--jurisdiction", required=True)
    args = parser.parse_args()

    jurisdiction = args.jurisdiction
    output_dir   = Path("data/output") / jurisdiction
    suffix       = f"_{jurisdiction.lower()}"

    input_path      = output_dir / f"matched_descriptors{suffix}.json"
    old_guide_path  = output_dir / f"structured_old_guide{suffix}.json"
    new_guide_path  = output_dir / f"structured_new_guide{suffix}.json"
    output_path     = output_dir / f"diff_results{suffix}.json"

    for p in [input_path, old_guide_path, new_guide_path]:
        if not p.exists():
            print(f"[ERROR] Not found: {p}", file=sys.stderr)
            sys.exit(1)

    print(f"[Stage 5] Loading matched descriptors for {jurisdiction} ...")
    with input_path.open("r", encoding="utf-8") as f:
        match_result = json.load(f)

    print(f"[Stage 5] Building table indexes from structured guides ...")
    with old_guide_path.open("r", encoding="utf-8") as f:
        old_table_index = build_table_index(json.load(f))
    with new_guide_path.open("r", encoding="utf-8") as f:
        new_table_index = build_table_index(json.load(f))

    print(f"  Old guide tables indexed: {len(old_table_index)}")
    print(f"  New guide tables indexed: {len(new_table_index)}")

    result = run_diff(match_result, old_table_index, new_table_index)

    r  = result["rate_changes"]
    c  = result["criteria_changes"]
    pr = result["program_renames"]
    dr = result["descriptor_renames"]
    ad = result["added_descriptors"]
    rd = result["removed_descriptors"]
    ap = result["added_programs"]
    rp = result["removed_programs"]

    print(f"\n[Stage 5] Results:")
    print(f"  Rate changes:           {len(r)}")
    print(f"  Criteria changes:       {len(c)}")
    print(f"  Program renames:        {len(pr)}")
    print(f"  Descriptor renames:     {len(dr)}")
    print(f"  Added descriptors:      {len(ad)}")
    print(f"  Removed descriptors:    {len(rd)}")
    print(f"  Added programs:         {len(ap)}")
    print(f"  Removed programs:       {len(rp)}")

    enriched = sum(1 for ch in c if ch.get("referenced_tables"))
    print(f"\n  Criteria changes with resolved table refs: {enriched}/{len(c)}")

    if r:
        print(f"\n  Rate changes:")
        for ch in r:
            for field, vals in ch.get("rate_changes", {}).items():
                print(f"    [{ch['program_name'][:40]:<40}] {ch['fee_descriptor']:<25} {vals['old']} → {vals['new']}")

    if pr:
        print(f"\n  Program renames:")
        for p in pr:
            print(f"    [{p['fuzzy_ratio']:.2f}] '{p['old_name']}' → '{p['new_name']}'")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n[Stage 5] Output written to {output_path}")


if __name__ == "__main__":
    main()