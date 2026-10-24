"""
tools/tests/test_import_bank.py
--------------------------------
Unit tests for tools/import_bank.py.

Run with:
    python -m pytest tools/tests/  -v
    or
    python -m unittest tools/tests/test_import_bank.py -v

No extra packages required — uses stdlib unittest only.
"""

import sys
import textwrap
import unittest
from pathlib import Path

# Make the tools package importable regardless of where pytest is invoked from.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.import_bank import (
    EXPECTED_DIFFICULTY,
    EXPECTED_TOTAL,
    normalise_ion_tag,
    parse_bank,
    validate,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_bank(blocks: str, tmp_path) -> Path:
    """Write a minimal bank text file and return its Path."""
    header = textwrap.dedent("""\
        SALT ANALYSIS QUESTION BANK (Revised)
        ================================================================================

        SALT 1: NaCl (Sodium chloride)
        ================================================================================

    """)
    content = header + textwrap.dedent(blocks)
    p = tmp_path / "bank.txt"
    p.write_text(content, encoding="utf-8")
    return p


def _valid_question(n: int = 1, diff: str = "Easy", ion: str = "Na+",
                    text: str = "What colour is the flame?",
                    options: tuple = ("Red", "Yellow", "Blue", "Green"),
                    answer_idx: int = 1) -> str:
    """Return a well-formed question block string."""
    letters = ("A", "B", "C", "D")
    opts = "\n".join(f"   {letters[i]}) {options[i]}" for i in range(4))
    ans_letter = letters[answer_idx]
    ans_text = options[answer_idx]
    return (
        f"Q{n}. [{diff}] [{ion}] {text}\n"
        f"{opts}\n"
        f"   Answer: {ans_letter}) {ans_text}\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Ion normalisation tests
# ─────────────────────────────────────────────────────────────────────────────

class TestNormaliseIonTag(unittest.TestCase):

    def test_whole_salt_returns_none(self):
        self.assertIsNone(normalise_ion_tag("Whole salt"))

    def test_whole_salt_case_insensitive(self):
        self.assertIsNone(normalise_ion_tag("WHOLE SALT"))
        self.assertIsNone(normalise_ion_tag("whole salt"))

    def test_simple_ion_unchanged(self):
        self.assertEqual(normalise_ion_tag("Na+"), "Na+")
        self.assertEqual(normalise_ion_tag("Cl-"), "Cl-")

    def test_superscript_notation_normalised(self):
        # SO4^2-  →  SO4 2-
        self.assertEqual(normalise_ion_tag("SO4^2-"), "SO4 2-")

    def test_superscript_plus_normalised(self):
        # Fe^3+  →  Fe 3+
        self.assertEqual(normalise_ion_tag("Fe^3+"), "Fe 3+")

    def test_nh4_plus_unchanged(self):
        self.assertEqual(normalise_ion_tag("NH4+"), "NH4+")

    def test_strips_whitespace(self):
        self.assertEqual(normalise_ion_tag("  Na+  "), "Na+")


# ─────────────────────────────────────────────────────────────────────────────
# Parser tests
# ─────────────────────────────────────────────────────────────────────────────

class TestParseBank(unittest.TestCase):

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_valid_single_question_parsed(self):
        block = _valid_question(1)
        src = _make_bank(block, self.tmp_path)
        questions, unclassified, warnings = parse_bank(src)
        self.assertEqual(len(questions), 1)
        q = questions[0]
        self.assertEqual(q["item"], "nacl")
        self.assertEqual(q["difficulty"], "easy")
        self.assertEqual(q["radical"], "Na+")
        self.assertEqual(len(q["options"]), 4)
        self.assertIn(q["correct_answer"], q["options"])

    def test_whole_salt_tag_gives_null_radical(self):
        block = _valid_question(1, ion="Whole salt")
        src = _make_bank(block, self.tmp_path)
        questions, _, _ = parse_bank(src)
        self.assertEqual(len(questions), 1)
        self.assertIsNone(questions[0]["radical"])

    def test_question_with_only_three_options_is_skipped(self):
        # Manually craft a question missing option D
        bad = (
            "Q1. [Easy] [Na+] What colour?\n"
            "   A) Red\n"
            "   B) Yellow\n"
            "   C) Blue\n"
            "   Answer: B) Yellow\n"
        )
        src = _make_bank(bad, self.tmp_path)
        questions, _, warnings = parse_bank(src)
        self.assertEqual(len(questions), 0)
        self.assertTrue(any("options" in w or "SKIPPED" in w for w in warnings))

    def test_answer_not_matching_option_text_is_skipped(self):
        # Answer text differs from option text and is not a case difference
        bad = (
            "Q1. [Easy] [Na+] What colour?\n"
            "   A) Red\n"
            "   B) Yellow\n"
            "   C) Blue\n"
            "   D) Green\n"
            "   Answer: B) Completely wrong text\n"
        )
        src = _make_bank(bad, self.tmp_path)
        questions, _, warnings = parse_bank(src)
        self.assertEqual(len(questions), 0)
        self.assertTrue(any("SKIPPED" in w for w in warnings))

    def test_correct_answer_is_stored_exactly_as_option_text(self):
        block = _valid_question(1, options=("Brick red", "Golden yellow", "Lilac", "Apple green"), answer_idx=1)
        src = _make_bank(block, self.tmp_path)
        questions, _, _ = parse_bank(src)
        self.assertEqual(questions[0]["correct_answer"], "Golden yellow")
        self.assertIn("Golden yellow", questions[0]["options"])

    def test_schema_fields_present(self):
        block = _valid_question(1)
        src = _make_bank(block, self.tmp_path)
        questions, _, _ = parse_bank(src)
        required_fields = {
            "id", "source", "subject", "experiment", "item",
            "radical", "test_type", "difficulty", "lang",
            "question", "options", "correct_answer", "explanation", "active",
        }
        self.assertTrue(required_fields.issubset(questions[0].keys()))

    def test_source_is_bank(self):
        block = _valid_question(1)
        src = _make_bank(block, self.tmp_path)
        questions, _, _ = parse_bank(src)
        self.assertEqual(questions[0]["source"], "bank")

    def test_subject_and_experiment(self):
        block = _valid_question(1)
        src = _make_bank(block, self.tmp_path)
        questions, _, _ = parse_bank(src)
        self.assertEqual(questions[0]["subject"], "chemistry")
        self.assertEqual(questions[0]["experiment"], "salt_analysis")

    def test_unclassified_question_listed(self):
        # A question with no keyword matching any test_type
        block = _valid_question(1, text="Xyzzy this question matches nothing at all in the heuristics table")
        src = _make_bank(block, self.tmp_path)
        questions, unclassified, _ = parse_bank(src)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["test_type"], "unclassified")
        self.assertIn(questions[0]["id"], unclassified)

    def test_flame_keyword_classified(self):
        block = _valid_question(1, text="What colour does the flame test give for this salt?")
        src = _make_bank(block, self.tmp_path)
        questions, unclassified, _ = parse_bank(src)
        self.assertEqual(questions[0]["test_type"], "flame")
        self.assertNotIn(questions[0]["id"], unclassified)

    def test_so4_superscript_normalised_in_radical(self):
        block = _valid_question(1, ion="SO4^2-")
        src = _make_bank(block, self.tmp_path)
        questions, _, _ = parse_bank(src)
        self.assertEqual(questions[0]["radical"], "SO4 2-")


# ─────────────────────────────────────────────────────────────────────────────
# Validation tests
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation(unittest.TestCase):

    def _make_questions(self, n_easy=240, n_medium=240, n_hard=120) -> list:
        """Build a synthetic list of minimal question dicts."""
        questions = []
        seq = 0
        for diff, count in [("easy", n_easy), ("medium", n_medium), ("hard", n_hard)]:
            for _ in range(count):
                seq += 1
                questions.append({
                    "id": f"sa_nacl_{seq:03d}",
                    "source": "bank",
                    "subject": "chemistry",
                    "experiment": "salt_analysis",
                    "item": "nacl",
                    "radical": "Na+",
                    "test_type": "flame",
                    "difficulty": diff,
                    "lang": "en",
                    "question": f"Question {seq}",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": "",
                    "active": True,
                })
        return questions

    def test_perfect_set_passes(self):
        questions = self._make_questions()
        errors = validate(questions)
        self.assertEqual(errors, [])

    def test_wrong_total_fails(self):
        questions = self._make_questions(n_easy=239)  # 599 total
        errors = validate(questions)
        self.assertTrue(any("Total" in e for e in errors))

    def test_wrong_difficulty_count_fails(self):
        questions = self._make_questions(n_easy=241, n_medium=239)  # totals 600 but mix is wrong
        errors = validate(questions)
        self.assertTrue(any("easy" in e or "medium" in e for e in errors))

    def test_question_with_wrong_option_count_fails(self):
        questions = self._make_questions()
        questions[0]["options"] = ["A", "B", "C"]  # only 3 options
        errors = validate(questions)
        self.assertTrue(any("option" in e.lower() for e in errors))

    def test_correct_answer_not_in_options_fails(self):
        questions = self._make_questions()
        questions[0]["correct_answer"] = "X"  # not in options
        errors = validate(questions)
        self.assertTrue(any("correct_answer" in e for e in errors))

    def test_duplicate_ids_detected(self):
        questions = self._make_questions()
        questions[1]["id"] = questions[0]["id"]  # force duplicate
        errors = validate(questions)
        self.assertTrue(any("Duplicate" in e for e in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
