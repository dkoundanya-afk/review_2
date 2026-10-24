# PHASE W1 REPORT — Auth, classes, redeem  (built and tested by Claude, not Antigravity)

## 1. Summary
Students can register with a class join code, log in with Student ID + PIN, and redeem a completion code
(with an optional result token). The server checks the code against the shared Lab Pack contract, rejects
wrong-student, reused, forged and expired codes, ignores bad tokens (but logs them), and rate-limits failures.
Teachers (created by an admin command) can make classes, rotate join codes, list their roster and reset PINs.
All 12 data tables from spec section 4 exist; quiz logic arrives in W2.

## 2. Done vs planned
| ID | Status | Note |
|---|---|---|
| S-01 register/login, join class | Done | Student ID + PIN; extra classes via /api/classes/join |
| S-02 ID normalisation | Done | lab_pack.normalise_student_id on every input; portal also bans `@` and spaces |
| S-03 redeem messages | Done | bad_format, invalid_code (not yours / forged), already_used, expired, rate_limited, item_already_unlocked |
| S-04 unlock once | Done | DB unique on code and on (student, item) |
| S-13 progress grid (data) | Done | /api/progress: 12 salts Locked / Unlocked / Completed, points, level, badges |
| S-18 change PIN, logout, expiry | Done | tokens expire after 14 days (config `auth.token_days`) |
| T-01/T-02 teacher + classes | Done | create, edit, archive, rotate / disable join code |
| T-03 roster list + reset PIN | Done | temp PIN shown once; student is logged out everywhere and must change it |
| T-18 admin basics | Done | `load_data`, `create_teacher`, Django admin |
| Badges engine | Done early | rules in virtulab_data/badges.json; First Spark and Lab Perfectionist/Comeback work now |
| Rate limiting + audit log | Done | InvalidAttempt + AuditLog tables |
| S-05..S-12, S-14, S-15 | Not yet | W2 |

## 3. Files
backend/core/{settings,urls,wsgi}.py, backend/manage.py, backend/api/{models,conf,auth,errors,services,views,urls,admin}.py,
backend/api/migrations/0001_initial.py, backend/api/management/commands/{load_data,create_teacher}.py,
backend/api/tests/{helpers,test_w1}.py, virtulab_data/badges.json, lab_pack/{verify_code,token_codec,test_lab_pack}.py (small generalisation).

## 4. CONTRACT CHECK
Code format, token format, Student ID normalisation and the question schema are unchanged.
Only change: `verify_code`, `parse_token` and `validate_payload` accept an optional item table so the portal can use
the database list of salts (new experiments = data only, scenario E12). Defaults reproduce the old behaviour (27 Lab Pack tests pass).
Portal-side additions (decisions): a second code for an already unlocked salt is rejected (`item_already_unlocked`);
Student IDs may only contain A-Z 0-9 . _ / - (no `@`); "expired" is reported when the code is valid but older than the window.

## 5. SECRETS CHECK
No secret in code or tests except the documented FAKE test secret. SECRET_KEY must come from the environment
(startup fails without it). HMAC_SECRET comes from the environment; if it is missing, redeem returns 503 instead of guessing.
PINs and passwords are hashed (Django PBKDF2); session tokens are stored only as SHA-256 hashes.

## 6. Tests
`python backend\manage.py test api` -> 33 tests, all pass (about 2 s). Lab Pack: `python -m unittest lab_pack.test_lab_pack` -> 27 tests.
Covers E2, E3, E4, E5, E9, rate limit (and that old failures expire), idempotent retry, typing variants, all 12 salts redeemable,
teacher isolation on every teacher endpoint, session expiry/logout, PIN reset.

## 7. How to run
See the chat message that came with this zip.

## 8. Manual steps
Put SECRET_KEY and HMAC_SECRET in `.env`; run migrate, load_data, create_teacher.

## 9. Acceptance (spec W1)
Valid code redeems once: PASS. Wrong student / reuse / forged / expired rejected: PASS. Failures logged: PASS.

## 10. Known issues, risks, assumptions
- "Not yours" and "forged" cannot be told apart by design (both give `invalid_code`).
- Rate limit counts failures per Student ID (and per IP at 4x). Behind a proxy the real client IP must be forwarded.
- PIN of 4-6 digits is weak by nature; protection is the rate limit (5 failures / 10 min).
- Teacher accounts only via `create_teacher` / Django admin.

## 11. Decisions needed from Sunny
None blocking. Confirm: one unlock per salt per student (second code rejected).

## 12. Next
W2: quiz engine (bank sampler, dynamic templates, freeze, autosave, grading, points, levels).
Dynamic questions need salt data files, which do not exist yet; I will draft them (unverified) in W2.
