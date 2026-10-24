# AGENTS.md — VirtuLab Companion Portal

Read this file first, then `VirtuLab_Portal_Requirements.md` (repo root).
Where this file and the spec disagree, **this file wins** (see OVERRIDES).

## OVERRIDES TO THE SPEC (agreed with the project owner)

1. **Completion code format (replaces 3.5 format).**
   `VL-<CATION>-<ANION>-<NONCE>-<CHK>`   e.g. `VL-NA-CL-7K3Q-9F2A`
   - NONCE and CHK are unchanged: 4 Crockford-base32 characters each.
   - CHK = first 4 chars of HMAC-SHA256(secret, STUDENTID|ITEMID|NONCE|YYYYMMDD). Unchanged.
   - The CATION and ANION segments are display/lookup labels. The server maps the
     pair to an ITEMID using the table below, and rejects any code whose pair is
     not in the table. Only iron carries a digit to separate Fe2+ from Fe3+.

   | ITEMID | CATION | ANION |
   |---|---|---|
   | nacl | NA | CL |
   | nh4cl | NH4 | CL |
   | cuso4 | CU | SO4 |
   | feso4 | FE2 | SO4 |
   | fecl3 | FE3 | CL |
   | al2so43 | AL | SO4 |
   | znso4 | ZN | SO4 |
   | bacl2 | BA | CL |
   | caco3 | CA | CO3 |
   | mgso4 | MG | SO4 |
   | pbno32 | PB | NO3 |
   | nh42co3 | NH4 | CO3 |

2. **The portal owns the contracts; the Unity lab team matches them.**
   Produce a "Lab Pack" folder (`lab_pack/`) containing: code format spec,
   result-token spec, the list of recordable mistakes, `verify_code.py`,
   test vectors (JSON), and a token generator script. The lab must reproduce the
   test vectors exactly.

3. **The question bank source is a .txt file**, not JSON:
   `virtulab_data/source/Salt_Analysis_Question_Bank.txt`
   Write `tools/import_bank.py` to convert it to `question_bank.json` (schema 3.9).
   - Line format: `Q1. [Easy] [Na+] question text`, options `A) ...`, then `Answer: B) text`.
   - Tag `[Whole salt]` means radical = null. Normalise ion tags (e.g. `SO4^2-` to `SO4 2-`).
   - The bank has no `test_type`. Guess it from keywords, use `unclassified` when unsure,
     and list every unclassified question in an import report. Never silently guess.
   - Validate: 600 questions, 4 options each, correct answer equals exactly one option,
     difficulty counts 240 Easy / 240 Medium / 120 Hard.

4. **Salt data (virtulab_data/salts/*.json) does not exist yet.**
   Draft it ONLY from facts in the question bank. Mark every file `"status": "unverified"`.
   A chemistry teacher will verify later. Never present unverified data as final.
   Any placeholder must carry `"_mock": true`.

5. **Build order:** Student side first (W0 to W3). Teacher side (W4 to W6) only after
   the student side passes its acceptance criteria.

6. **No ChatGPT in the loop.** The owner pastes prompts and reports directly.
   Write plain-language reports; the owner is a student, not a senior developer.

7. **Salt cards on the UI:** show formula, plain name, and ion chips. Cations use the
   blue style, anions use the orange style, always. Show Fe(II)/Fe(III) names for iron.
   The redeem screen decodes the code into formula, name and both ions.

8. **Leave clear notes and tests.** A different model may continue this work later.
   Keep a `docs/DECISIONS.md` log and make every phase re-runnable from the README.

## HARD RULES — VirtuLab Portal
1. CONTRACTS ARE FROZEN: code format, result token format, question schema,
   Student ID normalisation and the virtulab_data folder structure are defined
   in the spec (as amended by OVERRIDES above). Do not change them. If one must
   change, STOP and ask.
2. NO INVENTED CHEMISTRY: every correct answer and distractor comes from
   virtulab_data/ or the question bank. If data is missing or conflicts,
   FLAG it; never guess.
3. AI NEVER WRITES OR GRADES QUESTIONS. Grading is a deterministic comparison.
   AI is optional, server-side, anonymised, and the portal works with it off.
4. SECRETS: HMAC secret and AI key only in environment variables. Never in the
   repo, the frontend bundle, logs or reports.
5. SYNTHETIC DATA ONLY in seeds and demos. No real student information.
6. NO HEAVY DEPENDENCIES without asking. Keep the frontend small.
7. EVERY student/teacher-visible string goes through the i18n catalogue.
8. TEACHER ISOLATION: every teacher query is scoped to that teacher's classes.
   Write a test for it.
9. TESTS are required for: code verifier, token parser, quiz generator,
   scoring/badges, teacher isolation.
10. DO NOT TOUCH the Unity lab project or its files.
11. SCOPE: do only the current phase. No extras, no refactors of finished
    phases unless fixing a bug (then report it).
12. END EVERY PHASE with the Phase Report (spec Section 9.4), saved as
    docs/PHASE_<n>_REPORT.md and printed in chat.

## WORKING STYLE
- Show a plan first and wait for approval before large changes.
- Ask before running any command that deletes files or installs many packages.
- If unsure, stop and ask. Do not guess chemistry or change a contract.
