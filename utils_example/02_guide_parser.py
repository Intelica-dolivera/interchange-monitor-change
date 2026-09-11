"""
Transforms raw extracted blocks (raw_guide.json) into structured,
section-aware guide objects (structured_guide.json).

Sorts blocks by page and vertical position. Detects numbered section
headings and builds the full section_path hierarchy for every block.
Attaches table captions (Table X-Y: Title) to their corresponding
table block. Classifies each block role: section_heading, paragraph,
business_table, or navigation. Merges tables that are split across
consecutive pages into a single logical table. Filters document noise
such as page numbers, running headers, footers, and front-matter
navigation (Contents, List of Tables, List of Figures).

Input:  data/output/raw_guide.json
Output: data/output/structured_guide.json
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import argparse
import sys


INPUT_JSON = Path(
    "data/output/raw_old_guide.json"
)

OUTPUT_JSON = Path(
    "data/output/structured_guide.json"
)


def load_json(
    path: Path,
) -> List[Dict[str, Any]]:
    """
    Loads raw extracted guide blocks from JSON.
    """

    if not path.exists():
        raise FileNotFoundError("Input JSON not found: {path}")

    with path.open("r",encoding="utf-8",) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Expected JSON root to be a list.")

    return data


def save_json(
    path: Path,
    data: Any,
) -> None:
    """
    Saves data as formatted UTF-8 JSON.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def parse_guide_blocks(
    raw_blocks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Converts raw physical Docling blocks into structured
    logical guide objects.
    """

    sorted_blocks = _sort_blocks(raw_blocks)

    structured_blocks = _structure_blocks(sorted_blocks)

    structured_blocks = _merge_table_continuations(structured_blocks)

    return structured_blocks


def _structure_blocks(
    blocks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Adds section and table metadata to extracted blocks.
    """

    structured_blocks: List[Dict[str, Any]] = []

    current_section_number: Optional[str] = None
    current_section_title: Optional[str] = None
    current_section_path: List[str] = []
    section_stack: Dict[int, str] = {}

    pending_table_id: Optional[str] = None
    pending_table_title: Optional[str] = None

    for block in blocks:
        text = block.get("text", "")
        block_type = block.get("type")

        # -----------------------------------------------------
        # Remove common text noise
        # -----------------------------------------------------

        if (
            block_type == "text"
            and is_noise(text)
        ):
            continue

        # -----------------------------------------------------
        # Detect numbered section headings
        # -----------------------------------------------------

        if block_type == "text":
            section_number, section_title = detect_section(
                text
            )

            if (
                section_number is not None
                and is_valid_section_transition(
                    candidate_section=section_number,
                    current_section=current_section_number,
                )
            ):
                is_section_heading = True

                current_section_number = section_number
                current_section_title = section_title

                section_level = get_section_level(
                    section_number
                )

                section_label = (
                    f"{section_number} {section_title}"
                )

                section_stack[
                    section_level
                ] = section_label

                section_stack = {
                    level: label
                    for level, label
                    in section_stack.items()
                    if level <= section_level
                }

                current_section_path = [
                    section_stack[level]
                    for level in sorted(
                        section_stack.keys()
                    )
                ]

        # -----------------------------------------------------
        # Detect table captions
        # -----------------------------------------------------

        if block_type == "text":
            table_id, table_title = detect_table_caption(
                text
            )

            if table_id is not None:
                pending_table_id = table_id
                pending_table_title = table_title

                # Caption metadata will be attached
                # to the next table.
                continue

        # -----------------------------------------------------
        # Build structured block
        # -----------------------------------------------------

        block_role = classify_block_role(
            block_type=block_type,
            text=text,
            section_number=current_section_number,
            section_title=current_section_title,
        )

        structured_block = {
            "block_id": block.get("block_id"),
            "source_file": block.get("source_file"),
            "page": block.get("page"),
            "type": block_type,
            "block_role": block_role,
            "include_for_matching": should_include_for_matching(
                block_role
            ),
            "section_number": current_section_number,
            "section_title": current_section_title,
            "section_path": current_section_path,
            "table_id": None,
            "table_title": None,
            "text": text,
            "bbox": block.get("bbox"),
        }

        # -----------------------------------------------------
        # Attach pending table caption metadata
        # -----------------------------------------------------

        if block_type == "table":
            structured_block["table_id"] = pending_table_id
            structured_block["table_title"] = pending_table_title

            structured_block["block_role"] = classify_table_role(
                table_id=structured_block["table_id"],
                table_title=structured_block["table_title"],
                section_number=structured_block["section_number"],
                section_title=structured_block["section_title"],
                text=structured_block["text"],
            )

            structured_block["include_for_matching"] = (
                should_include_for_matching(
                    structured_block["block_role"]
                )
            )

            pending_table_id = None
            pending_table_title = None

        structured_blocks.append(
            structured_block
        )

    return structured_blocks




def get_section_level(
    section_number: str,
) -> int:
    """
    Returns the hierarchy level of a numbered section.

    Examples:
    1       -> 1
    1.2     -> 2
    1.2.3   -> 3
    """

    return len(
        section_number.split(".")
    )


def classify_block_role(
    block_type: Optional[str],
    text: str,
    section_number: Optional[str],
    section_title: Optional[str],
) -> str:
    """
    Assigns a structural role to a block before table metadata
    is attached.
    """

    if block_type == "table":
        return "business_table"

    if block_type != "text":
        return "unknown"

    detected_section_number, _ = detect_section(
        text
    )

    if detected_section_number is not None:
        return "section_heading"

    if is_navigation_text(text):
        return "navigation"

    if is_local_heading(text):
        return "local_heading"

    return "paragraph"


def classify_table_role(
    table_id: Optional[str],
    table_title: Optional[str],
    section_number: Optional[str],
    section_title: Optional[str],
    text: str,
) -> str:
    """
    Assigns a structural role to a table.
    """

    if is_navigation_table(
        section_number=section_number,
        section_title=section_title,
        text=text,
    ):
        return "navigation"

    combined_context = clean_text(
        " ".join(
            value
            for value in [
                section_title,
                table_title,
            ]
            if value
        )
    ).lower()

    schema = _get_normalized_table_schema(
        text
    )

    # ---------------------------------------------------------
    # Summary of Changes
    # ---------------------------------------------------------

    if "summary of changes" in combined_context:
        return "summary_of_changes"

    if schema:
        schema_set = set(
            schema
        )

        summary_columns = {
            "section",
            "status",
            "description of change",
        }

        if summary_columns.issubset(
            schema_set
        ):
            return "summary_of_changes"

    return "business_table"


def should_include_for_matching(
    block_role: str,
) -> bool:
    """
    Indicates whether a block should be exposed to the
    future old-vs-new matcher.
    """

    return block_role not in {
        "navigation",
        "header_footer",
        "summary_of_changes",
    }


def is_navigation_text(
    text: str,
) -> bool:
    """
    Detects navigation-related text labels.
    """

    lower = clean_text(
        text
    ).lower()

    return lower in {
        "contents",
        "tables",
        "figures",
        "table of contents",
        "list of tables",
        "list of figures",
    }


def is_local_heading(
    text: str,
) -> bool:
    """
    Detects common short business headings used inside
    interchange guide sections.

    The list is intentionally conservative.
    """

    normalized = clean_text(
        text
    ).lower()

    local_headings = {
        "fee rate",
        "fee descriptor",
        "fee program",
        "fee program indicator",
        "fee program indicators",
        "fpi",
        "product",
        "products",
        "eligible products",
        "transaction type",
        "transaction types",
        "merchant category code",
        "merchant category codes",
        "mcc",
        "mccs",
        "jurisdiction",
        "key data elements",
        "data elements",
        "fee edit criteria",
        "fee edit and reclassification criteria",
        "reclassification criteria",
        "requirements",
        "exceptions",
        "notes",
        "note",
    }

    return normalized in local_headings


def is_navigation_table(
    section_number: Optional[str],
    section_title: Optional[str],
    text: str,
) -> bool:
    """
    Detects tables that belong to front-matter navigation,
    such as Contents, Tables and Figures.

    This first version uses conservative signals from the guide.
    """

    if section_number is not None:
        return False

    schema = _get_normalized_table_schema(
        text
    )

    if not schema:
        return False

    joined_schema = " | ".join(
        schema
    )

    navigation_markers = {
        "tables",
        "figures",
    }

    if any(
        marker == joined_schema
        or joined_schema.startswith(marker)
        for marker in navigation_markers
    ):
        return True

    first_rows = [
        clean_text(line).lower()
        for line in text.splitlines()[:6]
        if clean_text(line)
    ]

    navigation_patterns = [
        r"\.{5,}\s*\d+$",
        r"^table\s+\d+[-–]\d+:",
        r"^\d+(?:\.\d+)+\s+.+\d+$",
    ]

    match_count = 0

    for row in first_rows:
        row_without_pipes = clean_text(
            row.replace("|", " ")
        )

        if any(
            re.search(
                pattern,
                row_without_pipes,
                re.IGNORECASE,
            )
            for pattern in navigation_patterns
        ):
            match_count += 1

    return match_count >= 2



def _merge_table_continuations(
    blocks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merges logical table continuations even when text blocks
    appear between table fragments.
    """

    merged_blocks: List[Dict[str, Any]] = []

    for block in blocks:
        if block.get("type") != "table":
            merged_blocks.append(block)
            continue

        previous_table_index = _find_previous_table_index(
            merged_blocks
        )

        if previous_table_index is None:
            merged_blocks.append(block)
            continue

        previous_table = merged_blocks[
            previous_table_index
        ]

        if not _is_table_continuation(
            previous_table=previous_table,
            current_table=block,
        ):
            merged_blocks.append(block)
            continue

        previous_table["text"] = _merge_table_markdown(
            previous_table.get("text", ""),
            block.get("text", ""),
        )

        previous_table.setdefault(
            "pages",
            [previous_table.get("page")],
        )

        if (
            block.get("page") is not None
            and block.get("page")
            not in previous_table["pages"]
        ):
            previous_table["pages"].append(
                block.get("page")
            )

        previous_table["pages"] = sorted(
            page
            for page in previous_table["pages"]
            if page is not None
        )

        if previous_table["pages"]:
            previous_table["page_end"] = max(
                previous_table["pages"]
            )

    return merged_blocks


def _find_previous_table_index(
    blocks: List[Dict[str, Any]],
) -> Optional[int]:
    """
    Finds the nearest previous table while ignoring
    text blocks between table fragments.
    """

    for index in range(
        len(blocks) - 1,
        -1,
        -1,
    ):
        if blocks[index].get("type") == "table":
            return index

    return None


def _is_table_continuation(
    previous_table: Dict[str, Any],
    current_table: Dict[str, Any],
) -> bool:
    """
    Determines whether the current table is probably
    a continuation of the previous logical table.
    """

    previous_pages = previous_table.get(
        "pages",
        [previous_table.get("page")],
    )

    previous_pages = [
        page
        for page in previous_pages
        if page is not None
    ]

    current_page = current_table.get("page")

    if (
        not previous_pages
        or current_page is None
    ):
        return False

    previous_page_end = max(
        previous_pages
    )

    # Continuation must begin on the next page.
    if current_page != previous_page_end + 1:
        return False

    # A table with its own caption is treated as a new table.
    if current_table.get("table_id"):
        return False

    # Avoid merging tables across sections.
    if (
        previous_table.get("section_number")
        != current_table.get("section_number")
    ):
        return False

    previous_schema = _get_normalized_table_schema(
        previous_table.get("text", "")
    )

    current_schema = _get_normalized_table_schema(
        current_table.get("text", "")
    )

    if (
        previous_schema is None
        or current_schema is None
    ):
        return False

    return (
        previous_schema
        == current_schema
    )


def _get_normalized_table_schema(
    markdown: str,
) -> Optional[List[str]]:
    """
    Extracts and normalizes the table header.

    Empty columns are ignored so that logically equivalent
    schemas can still match.

    Example:
    | Fee Program |  | Fee Descriptor | FPI | Rate |

    becomes:
    ["fee program", "fee descriptor", "fpi", "rate"]
    """

    lines = [
        line.strip()
        for line in markdown.splitlines()
        if line.strip()
    ]

    if not lines:
        return None

    header = lines[0]

    columns = [
        clean_text(column).lower()
        for column in header.strip("|").split("|")
    ]

    normalized_columns = [
        column
        for column in columns
        if column
    ]

    if not normalized_columns:
        return None

    return normalized_columns


def _merge_table_markdown(
    previous_markdown: str,
    current_markdown: str,
) -> str:
    """
    Merges two Markdown tables and removes the repeated
    header and Markdown separator from the continuation.
    """

    previous_lines = [
        line
        for line in previous_markdown.splitlines()
        if line.strip()
    ]

    current_lines = [
        line
        for line in current_markdown.splitlines()
        if line.strip()
    ]

    if len(current_lines) >= 2:
        current_lines = current_lines[2:]

    return "\n".join(
        previous_lines + current_lines
    )


def clean_text(
    text: str,
) -> str:
    """
    Normalizes repeated whitespace.
    """

    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()


def is_noise(
    text: str,
) -> bool:
    """
    Detects common headers, footers and repeated document noise.
    """

    text = clean_text(text)
    lower = text.lower()

    if not text:
        return True

    if lower in {
        "visa confidential",
        "visa public",
        "contents",
        "tables",
        "figures",
    }:
        return True

    # Page numbers
    if re.fullmatch(
        r"\d+",
        text,
    ):
        return True

    # Roman page numbers
    if re.fullmatch(
        r"[ivxlcdm]+",
        lower,
    ):
        return True

    # Visa proprietary notice
    if lower.startswith(
        "notice: this information is proprietary"
    ):
        return True

    month_pattern = (
        r"(january|february|march|april|may|june|"
        r"july|august|september|october|november|december)"
        r"\s+\d{4}"
    )

    # Month + year footer
    if re.fullmatch(
        month_pattern,
        lower,
    ):
        return True

    # Combined confidentiality footer
    if (
        "visa confidential" in lower
        and "notice: this information is proprietary" in lower
    ):
        return True

    return False


def detect_section(
    text: str,
) -> tuple[Optional[str], Optional[str]]:
    """
    Detects candidate numbered section headings.

    This function only validates the textual pattern.
    Structural hierarchy validation is handled separately.
    """

    text = clean_text(
        text
    )

    match = re.match(
        r"^(\d+(?:\.\d+)*)\s+(.+)$",
        text,
    )

    if not match:
        return None, None

    section_number = match.group(1)

    section_title = (
        match
        .group(2)
        .strip()
    )

    if not section_title:
        return None, None

    if len(section_title) > 250:
        return None, None

    return (
        section_number,
        section_title,
    )

def detect_table_caption(
    text: str,
) -> tuple[Optional[str], Optional[str]]:
    """
    Detects table captions.

    Examples:
    Table 1-1: List of Visa Product IDs...
    Table 4–8: Visa Money Load Fee Program...
    """

    text = clean_text(text)

    match = re.match(
        r"^(Table\s+\d+[-–]\d+):?\s*(.+)$",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None, None

    table_id = (
        match
        .group(1)
        .replace("–", "-")
        .strip()
    )

    table_title = (
        match
        .group(2)
        .strip()
    )

    return (
        table_id,
        table_title,
    )


def _sort_blocks(
    blocks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Sorts blocks by page and vertical position.
    """

    def sort_key(
        block: Dict[str, Any],
    ) -> tuple:
        page = block.get("page") or 0
        bbox = block.get("bbox") or {}

        top = bbox.get("t", 0)

        return (
            page,
            -top,
        )

    return sorted(
        blocks,
        key=sort_key,
    )


def is_valid_section_transition(
    candidate_section: str,
    current_section: Optional[str],
) -> bool:
    """
    Validates whether a candidate numbered heading is a plausible
    section transition in the current document hierarchy.

    Helps reject numbered footnotes that resemble section headings.
    """

    if current_section is None:
        return True

    candidate_parts = [
        int(part)
        for part in candidate_section.split(".")
    ]

    current_parts = [
        int(part)
        for part in current_section.split(".")
    ]

    candidate_level = len(
        candidate_parts
    )

    current_level = len(
        current_parts
    )

    # ---------------------------------------------------------
    # Same section repeated
    # ---------------------------------------------------------

    if candidate_section == current_section:
        return True

    # ---------------------------------------------------------
    # Root section transition
    #
    # 1.x -> 2
    # 2.x -> 3
    #
    # This MUST be evaluated before ancestor transitions.
    # ---------------------------------------------------------

    if candidate_level == 1:
        current_root = current_parts[0]
        candidate_root = candidate_parts[0]

        return candidate_root == (
            current_root + 1
        )

    # ---------------------------------------------------------
    # Direct child
    #
    # 3.1 -> 3.1.1
    # ---------------------------------------------------------

    if (
        candidate_level
        == current_level + 1
        and candidate_parts[:-1]
        == current_parts
    ):
        return True

    # ---------------------------------------------------------
    # Sibling
    #
    # 3.1.1 -> 3.1.2
    # 3.1.1.1 -> 3.1.1.2
    # ---------------------------------------------------------

    if (
        candidate_level == current_level
        and candidate_parts[:-1]
        == current_parts[:-1]
        and candidate_parts[-1]
        == current_parts[-1] + 1
    ):
        return True

    # ---------------------------------------------------------
    # Move to sibling of an ancestor
    #
    # 3.1.1.3 -> 3.1.2
    # 6.5.1.4.3 -> 6.5.1.5
    #
    # Root sections are already handled above.
    # ---------------------------------------------------------

    if (
        1 < candidate_level < current_level
    ):
        candidate_parent = (
            candidate_parts[:-1]
        )

        current_parent_prefix = current_parts[
            :candidate_level - 1
        ]

        if (
            candidate_parent
            == current_parent_prefix
            and candidate_parts[-1]
            == (
                current_parts[
                    candidate_level - 1
                ]
                + 1
            )
        ):
            return True

    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 2: Parse raw blocks into structured guide"
    )
    parser.add_argument("--jurisdiction", required=True,
                        help="Jurisdiction folder name e.g. Interregional, Europe, Romania")
    args = parser.parse_args()

    jurisdiction = args.jurisdiction
    output_dir   = Path("data/output") / jurisdiction
    suffix       = f"_{jurisdiction.lower()}"

    for label in ("new", "old"):
        input_path  = output_dir / f"raw_{label}_guide{suffix}.json"
        output_path = output_dir / f"structured_{label}_guide{suffix}.json"

        if not input_path.exists():
            print(f"[INFO] {input_path} not found — skipping")
            continue

        print(f"\n[Stage 2] Processing {label} guide ...")
        raw_blocks        = load_json(input_path)
        structured_blocks = parse_guide_blocks(raw_blocks)
        save_json(output_path, structured_blocks)
        print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
