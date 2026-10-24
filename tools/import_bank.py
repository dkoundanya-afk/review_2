#!/usr/bin/env python
"""
tools/import_bank.py
--------------------
Converts virtulab_data/source/Salt_Analysis_Question_Bank.txt
into virtulab_data/question_bank.json (schema §3.9).

Usage:
    python tools/import_bank.py [--src PATH] [--out PATH] [--report PATH]

OVERRIDE 3 rules applied here:
  - Line format: Q<n>. [Difficulty] [IonTag] question text
  - Options: A) ... through D) ...
  - Answer: X) text
  - [Whole salt] tag  →  radical = null
  - Ion tag normalisation e.g. SO4^2- → SO4 2-
  - test_type guessed from keywords; "unclassified" when unsure
  - Validates: 600 questions, 4 options each, correct answer matches one
    option exactly, difficulty counts 240 Easy / 240 Medium / 120 Hard
  - Every unclassified question is listed in the import report; nothing
    is silently guessed.
  - radical comes from the question's own tag ONLY (not from the salt header).
  - item, subject, experiment come from the salt header.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Salt header → item metadata (spec §3.4, OVERRIDE 1 table)
# ─────────────────────────────────────────────────────────────────────────────
SALT_HEADERS: dict[str, dict[str, str]] = {
    "SALT 1: NaCl":           {"item": "nacl",     "formula": "NaCl"},
    "SALT 2: NH4Cl":          {"item": "nh4cl",    "formula": "NH4Cl"},
    "SALT 3: CuSO4":          {"item": "cuso4",    "formula": "CuSO4"},
    "SALT 4: FeSO4":          {"item": "feso4",    "formula": "FeSO4"},
    "SALT 5: FeCl3":          {"item": "fecl3",    "formula": "FeCl3"},
    "SALT 6: Al2(SO4)3":      {"item": "al2so43",  "formula": "Al2(SO4)3"},
    "SALT 7: ZnSO4":          {"item": "znso4",    "formula": "ZnSO4"},
    "SALT 8: BaCl2":          {"item": "bacl2",    "formula": "BaCl2"},
    "SALT 9: CaCO3":          {"item": "caco3",    "formula": "CaCO3"},
    "SALT 10: MgSO4":         {"item": "mgso4",    "formula": "MgSO4"},
    "SALT 11: Pb(NO3)2":      {"item": "pbno32",   "formula": "Pb(NO3)2"},
    "SALT 12: (NH4)2CO3":     {"item": "nh42co3",  "formula": "(NH4)2CO3"},
}

# Normalised short key used in question IDs
SALT_SHORT: dict[str, str] = {
    "nacl": "nacl", "nh4cl": "nh4cl", "cuso4": "cuso4", "feso4": "feso4",
    "fecl3": "fecl3", "al2so43": "al2so4", "znso4": "znso4", "bacl2": "bacl2",
    "caco3": "caco3", "mgso4": "mgso4", "pbno32": "pbno3", "nh42co3": "nh4co3",
}

# Valid test_type values (spec §3.9)
VALID_TEST_TYPES = {
    "flame", "dry_heating", "dilute_acid", "conc_acid", "group_reagent",
    "wet_precipitation", "solubility", "gas_test", "confirmatory",
    "error_check", "salt_identification", "unclassified",
}

# ─────────────────────────────────────────────────────────────────────────────
# Keyword → test_type heuristics
# IMPORTANT: these are classification hints only. "unclassified" is the honest
# fallback when no keyword matches. The chemistry is NOT invented — keywords
# come from NCERT practical terminology.
# ─────────────────────────────────────────────────────────────────────────────
KEYWORD_RULES: list[tuple[list[str], str]] = [
    (["flame test", "flame colour", "flame is", "flame gives", "wire", "flame test",
      "golden yellow", "brick red", "lilac", "apple green", "crimson", "pale violet",
      "nichrome", "platinum wire", "flame", "bunsen burner flame"],
     "flame"),
    (["dry heating", "heated in a dry", "dry test tube", "crackling", "crackle",
      "heated strongly", "on ignition", "on heating", "sublime", "sublimes",
      "sublimation", "turns black", "charcoal", "residue on heating",
      "smells of ammonia on heating"],
     "dry_heating"),
    (["dilute h2so4", "dilute hcl", "dilute hno3", "dilute acid",
      "dilute sulphuric", "dilute hydrochloric", "dilute nitric",
      "effervescence with dilute", "brisk effervescence"],
     "dilute_acid"),
    (["concentrated h2so4", "conc. h2so4", "conc h2so4",
      "concentrated hcl", "concentrated hno3", "concentrated sulphuric",
      "conc. hno3", "warm with concentrated"],
     "conc_acid"),
    (["group i reagent", "group ii reagent", "group iii reagent",
      "group iv reagent", "group v reagent", "group vi reagent",
      "group reagent", "nh4cl and nh4oh", "(nh4)2co3",
      "h2s gas", "nh4oh", "nh4cl", "ammoniacal medium",
      "na2hpo4", "group separation"],
     "group_reagent"),
    (["precipitate with", "gives a precipitate", "white precipitate",
      "curdy white", "pale yellow precipitate", "yellow precipitate",
      "cream precipitate", "red-brown precipitate", "reddish-brown precipitate",
      "dirty green precipitate", "gelatinous", "blue precipitate",
      "agno3", "bacl2", "pb(no3)2", "fecl3 solution"],
     "wet_precipitation"),
    (["soluble in", "insoluble in", "solubility", "dissolves in",
      "does not dissolve", "sparingly soluble"],
     "solubility"),
    (["gas evolved", "gas produced", "gas is", "gas test",
      "turns lime water", "lime water", "moist litmus", "smells",
      "pungent smell", "rotten egg", "co2", "so2", "h2s", "nh3",
      "no2", "hcl gas", "colourless gas", "brown fumes", "white fumes",
      "damp red litmus", "damp blue litmus"],
     "gas_test"),
    (["confirmatory test", "confirms", "confirm the presence",
      "final confirmation", "confirmed by", "confirmatory",
      "brown ring", "ring test"],
     "confirmatory"),
    (["mistake", "error", "incorrect", "wrong step", "precaution",
      "should not", "avoid", "why must", "reason for", "handled carefully",
      "safety"],
     "error_check"),
    (["identify the salt", "identify the unknown", "which salt",
      "identify the compound", "the salt is", "the unknown salt",
      "salt identification", "which of the following salts"],
     "salt_identification"),
]


def _guess_test_type(question_text: str) -> tuple[str, bool]:
    """Return (test_type, is_unclassified). Never raises."""
    lower = question_text.lower()
    for keywords, test_type in KEYWORD_RULES:
        if any(kw in lower for kw in keywords):
            return test_type, False
    return "unclassified", True


# ─────────────────────────────────────────────────────────────────────────────
# Ion tag normalisation  (OVERRIDE 3)
# e.g.  "SO4^2-"  →  "SO4 2-"
#       "Na+"      →  "Na+"       (unchanged — already clean)
#       "NH4+"     →  "NH4+"
#       "Whole salt" → None
# ─────────────────────────────────────────────────────────────────────────────
_SUPER_RE = re.compile(r"\^(\d+[+-]|[+-])")

def normalise_ion_tag(raw: str) -> str | None:
    """Return a normalised radical string, or None for [Whole salt]."""
    raw = raw.strip()
    if raw.lower() == "whole salt":
        return None
    # Replace ^2- or ^3+ etc. with a space then the charge: "SO4 2-"
    normalised = _SUPER_RE.sub(lambda m: " " + m.group(1), raw)
    return normalised


# ─────────────────────────────────────────────────────────────────────────────
# Parser
# ─────────────────────────────────────────────────────────────────────────────

# Matches:  Q1. [Easy] [Na+] What colour ...
_Q_HEADER = re.compile(
    r"^Q(\d+)\.\s+\[(\w+)\]\s+\[([^\]]+)\]\s+(.+)$"
)
# Matches:  A) Some option text
_OPTION = re.compile(r"^([A-D])\)\s+(.+)$")
# Matches:  Answer: B) Some text
_ANSWER = re.compile(r"^Answer:\s+([A-D])\)\s+(.+)$")

# Salt section header patterns — we try key matching after stripping decoration
_SALT_DIVIDER = re.compile(r"^=+$")
_SALT_HEADER_RE = re.compile(r"^SALT\s+\d+\s*:", re.IGNORECASE)


def _find_salt_key(line: str) -> str | None:
    """Return the matching SALT_HEADERS key for a header line, or None."""
    line = line.strip()
    for key in SALT_HEADERS:
        # Flexible: allow extra spaces around colon, trailing whitespace
        if line.upper().startswith(key.upper()):
            return key
    return None


class ParseError(Exception):
    pass


def parse_bank(src: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Parse the question bank text file.

    Returns:
        questions  — list of dicts in schema §3.9 (without explanation field;
                     bank has none).
        warnings   — non-fatal notes logged to the report.
    """
    lines = src.read_text(encoding="utf-8").splitlines()

    questions: list[dict[str, Any]] = []
    warnings: list[str] = []
    unclassified_ids: list[str] = []

    current_salt_key: str | None = None
    current_salt_meta: dict[str, str] = {}
    # per-salt question counter (1-based, restarts for each salt)
    salt_q_counter: dict[str, int] = {}

    # State machine: "idle" | "in_question" | "in_options" | "awaiting_answer"
    state = "idle"

    # Accumulator for current question
    q_num: int = 0
    q_difficulty: str = ""
    q_ion_tag: str = ""
    q_text: str = ""
    q_options: dict[str, str] = {}
    q_option_order: list[str] = []

    def flush_question(lineno: int) -> None:
        """Validate and save the accumulated question."""
        nonlocal state
        # Called when we have all 4 options but no Answer yet — this is an error
        # We only call this from the answer handler, so this path means the file
        # ended mid-question.
        warnings.append(f"Line {lineno}: question Q{q_num} under '{current_salt_key}' ended without an Answer line — SKIPPED")
        state = "idle"

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        lineno = i + 1

        # ── Salt header detection ──────────────────────────────────────────
        if _SALT_HEADER_RE.match(line):
            key = _find_salt_key(line)
            if key:
                current_salt_key = key
                current_salt_meta = SALT_HEADERS[key]
                state = "idle"
                i += 1
                continue
            else:
                warnings.append(f"Line {lineno}: unrecognised salt header '{line}' — ignored")
                i += 1
                continue

        # ── Divider lines ──────────────────────────────────────────────────
        if _SALT_DIVIDER.match(line) or line.strip() == "":
            i += 1
            continue

        # ── Question header ────────────────────────────────────────────────
        m = _Q_HEADER.match(line)
        if m:
            if state == "in_question":
                warnings.append(f"Line {lineno}: new question started before previous Q{q_num} completed — SKIPPED previous")

            if current_salt_key is None:
                warnings.append(f"Line {lineno}: question found before any salt header — SKIPPED")
                i += 1
                continue

            q_num = int(m.group(1))
            q_difficulty = m.group(2).lower()
            q_ion_tag = m.group(3)
            q_text = m.group(4).strip()
            q_options = {}
            q_option_order = []
            state = "in_question"
            i += 1
            continue

        # ── Continuation of question text (indented lines before options) ──
        if state == "in_question" and line.startswith("   ") and not _OPTION.match(line.strip()):
            q_text += " " + line.strip()
            i += 1
            continue

        # ── Option lines ───────────────────────────────────────────────────
        m = _OPTION.match(line.strip())
        if m and state in ("in_question", "in_options"):
            letter = m.group(1)
            text = m.group(2).strip()
            q_options[letter] = text
            if letter not in q_option_order:
                q_option_order.append(letter)
            state = "in_options"
            i += 1
            continue

        # ── Answer line ────────────────────────────────────────────────────
        m = _ANSWER.match(line.strip())
        if m and state == "in_options":
            correct_letter = m.group(1)
            correct_text = m.group(2).strip()

            # Validation: must have exactly 4 options
            if len(q_options) != 4:
                warnings.append(
                    f"Line {lineno}: Q{q_num} under '{current_salt_key}' has "
                    f"{len(q_options)} options (expected 4) — SKIPPED"
                )
                state = "idle"
                i += 1
                continue

            # Validation: correct answer must match one option exactly
            if correct_letter not in q_options:
                warnings.append(
                    f"Line {lineno}: Q{q_num} under '{current_salt_key}' answer "
                    f"letter '{correct_letter}' not in options — SKIPPED"
                )
                state = "idle"
                i += 1
                continue

            stored_option = q_options[correct_letter]
            if stored_option != correct_text:
                # Try case-insensitive match; if close enough, keep with a warning
                if stored_option.lower() == correct_text.lower():
                    warnings.append(
                        f"Line {lineno}: Q{q_num} under '{current_salt_key}' answer "
                        f"text case mismatch (answer line vs option) — using option text"
                    )
                    correct_text = stored_option
                else:
                    warnings.append(
                        f"Line {lineno}: Q{q_num} under '{current_salt_key}' answer "
                        f"text '{correct_text}' does not match option '{stored_option}' — SKIPPED"
                    )
                    state = "idle"
                    i += 1
                    continue

            # Build the question record
            item_id = current_salt_meta["item"]
            salt_q_counter[item_id] = salt_q_counter.get(item_id, 0) + 1
            seq = salt_q_counter[item_id]
            short = SALT_SHORT.get(item_id, item_id)
            qid = f"sa_{short}_{seq:03d}"

            radical = normalise_ion_tag(q_ion_tag)
            test_type, is_unclassified = _guess_test_type(q_text)

            if is_unclassified:
                unclassified_ids.append(qid)

            if q_difficulty not in ("easy", "medium", "hard"):
                warnings.append(
                    f"Line {lineno}: Q{q_num} under '{current_salt_key}' has "
                    f"unknown difficulty '{q_difficulty}' — stored as-is"
                )

            record: dict[str, Any] = {
                "id":             qid,
                "source":         "bank",
                "subject":        "chemistry",
                "experiment":     "salt_analysis",
                "item":           item_id,
                "radical":        radical,
                "test_type":      test_type,
                "difficulty":     q_difficulty,
                "lang":           "en",
                "question":       q_text,
                "options":        [q_options[k] for k in q_option_order],
                "correct_answer": correct_text,
                "explanation":    "",
                "active":         True,
            }
            questions.append(record)
            state = "idle"
            i += 1
            continue

        # ── Anything else we don't recognise ──────────────────────────────
        i += 1

    return questions, unclassified_ids, warnings


# ─────────────────────────────────────────────────────────────────────────────
# Validation (OVERRIDE 3)
# ─────────────────────────────────────────────────────────────────────────────

EXPECTED_TOTAL = 600
EXPECTED_DIFFICULTY = {"easy": 240, "medium": 240, "hard": 120}
EXPECTED_PER_SALT = 50  # 20 easy + 20 medium + 10 hard


def validate(questions: list[dict[str, Any]]) -> list[str]:
    """Return a list of validation error strings (empty = all pass)."""
    errors: list[str] = []

    # Total count
    if len(questions) != EXPECTED_TOTAL:
        errors.append(
            f"Total question count: expected {EXPECTED_TOTAL}, got {len(questions)}"
        )

    # Option count per question (must be 4)
    bad_options = [q["id"] for q in questions if len(q["options"]) != 4]
    if bad_options:
        errors.append(f"Questions with ≠4 options: {bad_options}")

    # Correct answer must equal exactly one option
    bad_answers = [
        q["id"] for q in questions
        if q["correct_answer"] not in q["options"]
    ]
    if bad_answers:
        errors.append(f"Questions where correct_answer ∉ options: {bad_answers}")

    # Difficulty counts
    diff_counts: dict[str, int] = {}
    for q in questions:
        diff_counts[q["difficulty"]] = diff_counts.get(q["difficulty"], 0) + 1
    for diff, expected in EXPECTED_DIFFICULTY.items():
        got = diff_counts.get(diff, 0)
        if got != expected:
            errors.append(
                f"Difficulty '{diff}': expected {expected}, got {got}"
            )

    # Duplicate IDs
    ids = [q["id"] for q in questions]
    seen: set[str] = set()
    dupes = []
    for qid in ids:
        if qid in seen:
            dupes.append(qid)
        seen.add(qid)
    if dupes:
        errors.append(f"Duplicate question IDs: {dupes}")

    return errors


# ─────────────────────────────────────────────────────────────────────────────
# Report builder
# ─────────────────────────────────────────────────────────────────────────────

def build_report(
    questions: list[dict[str, Any]],
    unclassified_ids: list[str],
    warnings: list[str],
    errors: list[str],
    src: Path,
    out: Path,
) -> str:
    total = len(questions)

    # Per-difficulty counts
    diff_counts: dict[str, int] = {}
    for q in questions:
        diff_counts[q["difficulty"]] = diff_counts.get(q["difficulty"], 0) + 1

    # Per-salt counts
    salt_counts: dict[str, int] = {}
    for q in questions:
        salt_counts[q["item"]] = salt_counts.get(q["item"], 0) + 1

    lines = [
        "VirtuLab Question Bank — Import Report",
        "=" * 60,
        f"Source : {src}",
        f"Output : {out}",
        "",
        "── Counts ──────────────────────────────────────────────────",
        f"  Total questions  : {total}  (expected {EXPECTED_TOTAL})",
        f"  Easy             : {diff_counts.get('easy',0)}  (expected {EXPECTED_DIFFICULTY['easy']})",
        f"  Medium           : {diff_counts.get('medium',0)}  (expected {EXPECTED_DIFFICULTY['medium']})",
        f"  Hard             : {diff_counts.get('hard',0)}  (expected {EXPECTED_DIFFICULTY['hard']})",
        f"  Unclassified     : {len(unclassified_ids)}",
        "",
        "── Per-salt counts ─────────────────────────────────────────",
    ]
    for key, meta in SALT_HEADERS.items():
        item = meta["item"]
        n = salt_counts.get(item, 0)
        flag = "  ✓" if n == EXPECTED_PER_SALT else f"  ✗ (expected {EXPECTED_PER_SALT})"
        lines.append(f"  {item:<12}  {n}{flag}")

    lines += [
        "",
        "── Validation ──────────────────────────────────────────────",
    ]
    if errors:
        lines.append("  FAILED — errors below:")
        for e in errors:
            lines.append(f"    ✗ {e}")
    else:
        lines.append("  PASSED — all checks green.")

    if warnings:
        lines += ["", "── Parser warnings ────────────────────────────────────────"]
        for w in warnings:
            lines.append(f"  ! {w}")

    lines += [
        "",
        "── Unclassified questions (test_type = 'unclassified') ─────",
        f"  Count: {len(unclassified_ids)}",
    ]
    if unclassified_ids:
        lines.append("  IDs (review and assign a test_type manually):")
        # Find full records for context
        id_map = {q["id"]: q for q in questions}
        for qid in unclassified_ids:
            q = id_map.get(qid)
            if q:
                preview = q["question"][:80] + ("…" if len(q["question"]) > 80 else "")
                lines.append(f"    {qid}  [{q['item']}] [{q['difficulty']}]  {preview}")
    else:
        lines.append("  (none)")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import Salt Analysis Question Bank txt → question_bank.json"
    )
    repo_root = Path(__file__).resolve().parent.parent
    parser.add_argument(
        "--src",
        default=str(repo_root / "virtulab_data" / "source" / "Salt_Analysis_Question_Bank.txt"),
        help="Path to the source .txt file",
    )
    parser.add_argument(
        "--out",
        default=str(repo_root / "virtulab_data" / "question_bank.json"),
        help="Path to write question_bank.json",
    )
    parser.add_argument(
        "--report",
        default=str(repo_root / "virtulab_data" / "import_report.txt"),
        help="Path to write the import report",
    )
    args = parser.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    report_path = Path(args.report)

    if not src.exists():
        print(f"ERROR: source file not found: {src}", file=sys.stderr)
        return 1

    print(f"Parsing {src} …")
    questions, unclassified_ids, warnings = parse_bank(src)
    print(f"  Parsed {len(questions)} questions.")

    errors = validate(questions)

    report_text = build_report(questions, unclassified_ids, warnings, errors, src, out)

    # Always write the report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Report written to {report_path}")
    # Print to terminal safely (Windows cp1252 may not handle Unicode symbols)
    report_bytes = report_text.encode(sys.stdout.encoding or "utf-8", errors="replace")
    sys.stdout.buffer.write(b"\n" + report_bytes + b"\n")
    sys.stdout.buffer.flush()

    if errors:
        print("\nIMPORT FAILED — validation errors above.", file=sys.stderr)
        return 1

    # Write question_bank.json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nWrote {len(questions)} questions to {out}")
    return 0


def _safe_print(text: str) -> None:
    """Print text to stdout, replacing unencodable characters (Windows cp1252 safety)."""
    encoded = text.encode(sys.stdout.encoding or "utf-8", errors="replace")
    sys.stdout.buffer.write(encoded + b"\n")
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    sys.exit(main())
