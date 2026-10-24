# PHASE W2 REPORT: Quiz engine (built and tested by Claude, not Antigravity)

## Summary
Server builds, freezes, autosaves, grades and scores the 10-question quiz (5 theory-bank + up to 5 dynamic from the lab result
token). No token or a bad token -> 10 bank questions and `no_lab_data`. Thin token -> topped up from the bank and `partial_dynamic`.
Same code + same seed -> same quiz. Points ledger is idempotent; levels and badges are evaluated after each graded submit.

## Endpoints (exactly as in the U3 contract)
POST /api/quiz/start, GET /api/quiz/<id>, PUT /api/quiz/<id>/answers, POST /api/quiz/<id>/submit, GET /api/quiz/<id>/result, GET /api/history.
Errors: not_found(404) invalid_answer(400) already_submitted(409) already_graded(409, attempt_id) practice_after_graded(409) not_submitted(409).

## Files
backend/api/quiz.py, backend/api/views_quiz.py, backend/api/urls.py (6 new routes), backend/api/tests/test_w2.py,
virtulab_data/salt_data.json (DRAFT chemistry data, see below), docs/W2_KEYS.md. No migrations (tables came with W1).

## Tests
`python backend\manage.py test api` -> 47 tests pass (33 W1 + 14 W2): 5+5 split, answers never leak, determinism, fallbacks,
autosave validation, points/badge/level maths, idempotent submit, practice rules (no points, no badges), history, all 12 salts.

## CONTRACT CHECK
Unchanged: code format, token format, question schema, config.json numbers (points, levels, 10 questions, 40/40/20 mix).

## SECRETS CHECK
No secrets added. Correct answers are stored server-side and only sent in the result after submit.

## Known issues / assumptions (please read)
- **salt_data.json is a DRAFT** from standard school-level qualitative analysis. Not verified by a chemistry teacher. The
  correct answers of dynamic questions come only from this file. Have it checked before real students use it.
- Reagent ids in the file (naoh, nh4oh, bacl2, agno3, dil_hcl) and gas ids (co2, nh3, ...) are guesses except naoh/co2 that
  appear in the Lab Pack examples. A reagent id not in the file is skipped (no question, no error). The Unity team must send
  their real reagent ids so the file can be matched.
- Templates DQ-01, 02, 03, 05, 06, 08 are built. **DQ-04 (order) and DQ-07 (wrong-guess contrast) are skipped**: the data they need
  does not exist yet.
- Bank pool = this salt's questions + questions about its cation/anion radical. The spec's extra "salt_identification" pool is not added
  (those questions are about specific salts).
- The bank has no explanations yet, so `explanation` is empty in the review.
- Graded attempt is final (one per code). Practice only after the graded attempt is submitted.
