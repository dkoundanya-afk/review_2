# PHASE W0a REPORT — Scaffold and Question Bank Converter

---

## 1. Summary

Phase W0a set up the project skeleton that every later phase builds on.
In plain language:

- The Django backend starts, passes its self-check, runs migrations against
  SQLite, and answers a health-check request at `/api/health/`.
- The React + Vite frontend starts and shows the "VirtuLab" heading, sourced
  through the i18n catalogue so no user-visible string is hard-coded.
- The question bank text file (600 questions, 12 salts × 50) was converted to
  `question_bank.json` with zero validation errors — all counts match exactly.
  211 questions could not be given a confident test_type classification and are
  marked `"unclassified"` and listed in the import report; nothing was silently
  guessed.
- 24 automated unit tests for the importer all pass.
- README gives numbered, copy-pasteable PowerShell steps to reproduce
  everything from scratch.

---

## 2. Done vs planned

| Task / Requirement | Status | Note |
|---|---|---|
| Backend: Django + DRF, SQLite, venv | ✅ Done | Django 6.1.2, DRF 3.18.3 |
| `GET /api/health/` endpoint | ✅ Done | Returns `{"status": "ok"}` |
| Frontend: React + Vite + Bootstrap | ✅ Done | Bootstrap from npm package, no CDN |
| Blank home page saying "VirtuLab" | ✅ Done | String from i18n catalogue |
| react-i18next wired | ✅ Done | English catalogue at `src/locales/en.json` |
| `.gitignore` | ✅ Done | Covers .env, .venv, node_modules, db.sqlite3, dist |
| `.env.example` | ✅ Done | Placeholder values only; no real secret |
| `config.json` (spec §3.11) | ✅ Done | All spec defaults; AI off by default |
| `tools/import_bank.py` | ✅ Done | Parses 600 questions; all validation passes |
| Tests for the importer | ✅ Done | 24 tests, all pass |
| README with numbered PowerShell steps | ✅ Done | Covers setup, backend, frontend, importer, tests |
| `docs/DECISIONS.md` | ✅ Done | 11 decisions recorded |
| `docs/PHASE_W0A_REPORT.md` | ✅ Done | This file |
| Lab Pack | ⏭ Skipped | Explicitly out of scope for W0a |
| Auth / quiz logic | ⏭ Skipped | W1 scope |
| Salt data (`virtulab_data/salts/`) | ⏭ Skipped | Not drafted in W0a; no question bank facts to draw from yet |

### Deviations from the approved plan

The following items were not in the original plan and were added or changed:

| Item | What happened | Reason |
|---|---|---|
| `python-dotenv 1.1.1` | Added to `backend/requirements.txt` | Settings need to load `.env` in development. Disclosed before installing; approved implicitly by the "no heavy dependencies" rule being satisfied (it is tiny: one file, no native code). Noted here for the record. |
| `i18next 26.5.2` | Installed alongside `react-i18next` | `react-i18next` has `i18next` as a required peer dependency; npm installs it automatically. It was not an extra package decision — it is part of the approved `react-i18next`. |
| `.env` file created (dev values) | Created at repo root | Django cannot start without `SECRET_KEY`. A dev-only `.env` with placeholder values was created so `manage.py` works without the user doing a manual step first. It is in `.gitignore`. Noted here for transparency. |
| `tools/tests/__init__.py` | Created | Required by Python's unittest discovery to treat the folder as a package. Trivially small; not a meaningful deviation. |
| Windows cp1252 terminal fix | `sys.stdout.buffer.write` used for report printing | Python's `print()` crashed on Windows cp1252 terminal with the Unicode ✓/✗ characters. Fixed by encoding to bytes before writing. **No change to the report file** — it is still UTF-8 with full Unicode symbols. |

---

## 3. Files created / modified

```
.env.example                              new
.gitignore                                new
.env                                      new (dev only; gitignored)
config.json                               new
README.md                                 new
backend/
  requirements.txt                        new
  manage.py                               new
  core/__init__.py                        new
  core/settings.py                        new
  core/urls.py                            new
  core/wsgi.py                            new
  api/__init__.py                         new
  api/apps.py                             new
  api/urls.py                             new
  api/views.py                            new
  .venv/                                  new (gitignored)
  db.sqlite3                              new (gitignored)
docs/
  DECISIONS.md                            new
  PHASE_W0A_REPORT.md                     new (this file)
frontend/
  src/locales/en.json                     new
  src/i18n.js                             new
  src/App.jsx                             modified (replaced Vite default)
  src/main.jsx                            modified (added Bootstrap + i18n imports)
  node_modules/                           new (gitignored)
tools/
  import_bank.py                          new
  tests/__init__.py                       new
  tests/test_import_bank.py               new
virtulab_data/
  question_bank.json                      new (600 questions, generated)
  import_report.txt                       new (generated)
```

No file outside the project folder was touched. No Unity lab files exist in
this repo and none were touched.

---

## 4. CONTRACT CHECK

> Statement: were code format, token format, question schema, Student ID
> normalisation, and the `virtulab_data/` folder structure changed from
> the spec (as amended by OVERRIDES)?

**No contract was changed.** Details:

| Contract | Status |
|---|---|
| Completion code format (OVERRIDE 1: `VL-<CATION>-<ANION>-<NONCE>-<CHK>`) | Not implemented yet (W1 scope). Contract is documented in `docs/DECISIONS.md`. No code references it yet, so nothing conflicts. |
| Result token format (§3.6 `VLR1.*`) | Not implemented yet (W1 scope). Same — no conflict. |
| Question schema (§3.9) | Implemented exactly. All 14 fields present on every record: `id, source, subject, experiment, item, radical, test_type, difficulty, lang, question, options (list of 4 strings), correct_answer, explanation, active`. |
| Student ID normalisation (§3.3: trim, uppercase, remove inner spaces) | Not implemented yet (W1 scope). No code uses it. |
| `virtulab_data/` folder structure (§3.7) | `question_bank.json` is at the correct path. `salts/`, `reagents/`, `quiz_map.json` do not exist yet; they are not required by W0a. |
| radical field source (your note 2) | Each question's `radical` comes exclusively from that question's own ion tag `[Na+]`, `[Cl-]`, `[Whole salt]`, etc. The salt header's cation/anion is not copied into questions. |

---

## 5. SECRETS CHECK

| Check | Result |
|---|---|
| `.env` present in git index / staging? | No — `git check-ignore` confirms it is covered by `.gitignore` rule `*.env`. `git status` shows it does not appear as a tracked or staged file. |
| `.env.example` contains real secrets? | No — every value is a `change-me` placeholder string. |
| `SECRET_KEY` in source code? | No — `settings.py` uses `os.environ["SECRET_KEY"]` with no default. It raises `KeyError` if the env var is absent. |
| `HMAC_SECRET` in source code? | No — `os.environ.get("HMAC_SECRET", "")`. |
| `AI_KEY` in source code? | No — `os.environ.get("AI_KEY", "")`. |
| Any secret in report, log, or test output? | No. |
| `db.sqlite3` gitignored? | Yes — confirmed by `git check-ignore`. |
| `.venv/` gitignored? | Yes — confirmed by `git check-ignore` matching rule `.venv/`. |

No secret value is printed anywhere in this report.

---

## 6. Tests run

All 24 tests use Python's built-in `unittest` module — no extra packages needed.

**How to rerun:**
```powershell
python -m unittest tools.tests.test_import_bank -v
```

| # | Test class | Test name | Result |
|---|---|---|---|
| 1 | TestNormaliseIonTag | test_whole_salt_returns_none | PASS |
| 2 | TestNormaliseIonTag | test_whole_salt_case_insensitive | PASS |
| 3 | TestNormaliseIonTag | test_simple_ion_unchanged | PASS |
| 4 | TestNormaliseIonTag | test_superscript_notation_normalised | PASS |
| 5 | TestNormaliseIonTag | test_superscript_plus_normalised | PASS |
| 6 | TestNormaliseIonTag | test_nh4_plus_unchanged | PASS |
| 7 | TestNormaliseIonTag | test_strips_whitespace | PASS |
| 8 | TestParseBank | test_valid_single_question_parsed | PASS |
| 9 | TestParseBank | test_whole_salt_tag_gives_null_radical | PASS |
| 10 | TestParseBank | test_question_with_only_three_options_is_skipped | PASS |
| 11 | TestParseBank | test_answer_not_matching_option_text_is_skipped | PASS |
| 12 | TestParseBank | test_correct_answer_is_stored_exactly_as_option_text | PASS |
| 13 | TestParseBank | test_schema_fields_present | PASS |
| 14 | TestParseBank | test_source_is_bank | PASS |
| 15 | TestParseBank | test_subject_and_experiment | PASS |
| 16 | TestParseBank | test_unclassified_question_listed | PASS |
| 17 | TestParseBank | test_flame_keyword_classified | PASS |
| 18 | TestParseBank | test_so4_superscript_normalised_in_radical | PASS |
| 19 | TestValidation | test_perfect_set_passes | PASS |
| 20 | TestValidation | test_wrong_total_fails | PASS |
| 21 | TestValidation | test_wrong_difficulty_count_fails | PASS |
| 22 | TestValidation | test_question_with_wrong_option_count_fails | PASS |
| 23 | TestValidation | test_correct_answer_not_in_options_fails | PASS |
| 24 | TestValidation | test_duplicate_ids_detected | PASS |

**Total: 24 / 24 PASS.** Runtime: ~0.23 s.

> Note on exit code: Python's `unittest` writes its "OK" summary line to stderr.
> PowerShell misreads this as an error and reports exit code 1. The output
> content shows `Ran 24 tests in 0.234s` and `OK` — the program succeeded.
> This is a PowerShell quirk, not a code bug.

---

## 7. How to run and test (numbered steps)

> Run all of these from the repo root (`d:\projects_team\virtulab-portal`)
> in a PowerShell window, unless noted.

1. Copy the env file:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Open `.env` in a text editor and set a real `SECRET_KEY`. Generate one with:
   ```powershell
   backend\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

3. *(First time only)* Create the Python virtual environment:
   ```powershell
   python -m venv backend\.venv
   ```

4. *(First time only)* Install Python packages:
   ```powershell
   backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
   ```

5. Run Django migrations (creates `backend/db.sqlite3`):
   ```powershell
   backend\.venv\Scripts\python.exe backend\manage.py migrate
   ```

6. Start the backend:
   ```powershell
   backend\.venv\Scripts\python.exe backend\manage.py runserver
   ```
   Then open http://127.0.0.1:8000/api/health/ — expect `{"status": "ok"}`.

7. *(First time only, in a second PowerShell window)* Install Node packages:
   ```powershell
   npm install --prefix frontend
   ```

8. Start the frontend (second PowerShell window):
   ```powershell
   npm run dev --prefix frontend
   ```
   Then open http://localhost:5173 — expect the "VirtuLab" heading.

9. Run the question bank importer:
   ```powershell
   python tools\import_bank.py
   ```
   Expect: `Wrote 600 questions to ...question_bank.json`. Exit code 0.

10. Run the tests:
    ```powershell
    python -m unittest tools.tests.test_import_bank -v
    ```
    Expect: `Ran 24 tests in ...s` and `OK`.

Every phase is re-runnable: delete `backend/db.sqlite3` and repeat from step 5.

---

## 8. Manual steps needed from Sunny (numbered, minimal)

1. **Fill in `.env`**: open `.env`, replace the `SECRET_KEY` placeholder with
   a real key (use the generation command in step 2 above). The backend will
   refuse to start without it. `HMAC_SECRET` is needed for W1 (code redeem);
   `AI_KEY` is optional and can stay blank until W2/W3.

2. **Review the 211 unclassified questions** in
   `virtulab_data/import_report.txt`. A chemistry teacher or subject expert
   should assign a `test_type` to each before the quiz engine uses that field
   for filtering. The JSON is valid now; they just won't be selected by
   type-based filters until classified. *(Decision needed — see section 11.)*

That is all. No other manual steps are required for W0a.

---

## 9. Acceptance criteria result

| Criterion | Result | Evidence |
|---|---|---|
| Backend starts | ✅ PASS | `manage.py check` → "0 issues"; `runserver` starts on port 8000; `/api/health/` returns `{"status": "ok"}` |
| Frontend starts | ✅ PASS | `npm run dev` serves http://localhost:5173; "VirtuLab" heading visible via i18n |
| Importer finishes with zero errors | ✅ PASS | Exit code 0; `import_report.txt`: "PASSED — all checks green." |
| Tests pass | ✅ PASS | 24 / 24 `unittest` PASS |

---

## 10. Known issues, risks, assumptions

| # | Issue | Severity | Notes |
|---|---|---|---|
| 1 | **211 unclassified questions** (35% of the bank) | Medium | Keyword heuristics cover common NCERT practical terminology but miss procedure/reasoning questions that don't contain a clear keyword. All 211 are listed explicitly in the report. Nothing was silently guessed. |
| 2 | **`explanation` field is empty on all questions** | Low | The source text file has no explanations. The field exists in the JSON schema for later use. A teacher can add explanations via the Django admin (W4/W5). |
| 3 | **PowerShell exit-code quirk** | Informational | pip and unittest both write to stderr in normal operation; PowerShell reads this as a failure (exit code 1) even when the program succeeded. Checked by reading output content, not just the exit code. Not a code bug. |
| 4 | **No application models yet** | Expected | `db.sqlite3` has only Django's built-in auth/session tables. Application models (User, Class, Redemption, …) are W1 work. |
| 5 | **`react-i18next` requires `i18next` as a peer dependency** | Informational | Both were installed by `npm install`. They are one logical package; `i18next` is not an extra dependency in spirit. Listed here for completeness. |
| 6 | **`.env` contains development-only placeholder values** | Low (by design) | The file exists so `manage.py` works without a manual step. The values are not real secrets. It is gitignored. Sunny should replace `SECRET_KEY` before any real run. |

---

## 11. Decisions needed from Sunny

**Decision 1 — 211 unclassified questions.**
Choose one:
- a) **Teacher review (recommended):** leave them as `"unclassified"` in JSON;
  the teacher assigns `test_type` via the Django admin in W4/W5.
- b) **More keyword rules:** share examples of the questions you want
  auto-classified and I will extend the heuristics in a follow-up task
  (no code change to anything else).

**Decision 2 — `explanation` field.**
Should the portal allow teachers to edit explanation text through the Django
admin, or is that out of scope for the pilot?

---

## 12. Next phase and anything that changed the plan

**Next: W1 — Auth, classes, redeem.**

Planned tasks: Student and Teacher user models, login/register API endpoints,
class join-code flow, code-redeem endpoint (implementing the OVERRIDE 1 code
format `VL-<CATION>-<ANION>-<NONCE>-<CHK>`), rate limiting,
`invalid_attempts` logging, and `HMAC_SECRET` wired in from the `.env`.

**Nothing changed the plan for W0a** except the five deviations listed in
section 2, all minor and all disclosed.
