# VirtuLab Companion Portal — Requirements Spec
## Part A: Student Portal · Part B: Teacher Portal

> **Audience:** ChatGPT (writes one Antigravity prompt per phase) and Antigravity (builds it).
> **Owner:** Sunny (Desai Srikoundinya). **Reviewer:** Claude rates each phase report.
> **Sister document:** `VirtuLab_Chem_Build_Plan.md` (the offline Unity lab). The two projects share contracts defined in Section 3.

---

## 0. How to use this document

**ChatGPT:** Read the whole file. For each phase in Section 9, write ONE self-contained prompt for Antigravity using the template in Section 9.3. Always paste the *Hard Rules* (Section 9.2) verbatim. Never combine phases. Tell Sunny which manual steps are needed before each prompt.

**Antigravity:** Read this file first. Build only the phase you are given. If a requirement is unclear or a contract would have to change, STOP and ask. End every phase with the Phase Report (Section 9.4).

**Review loop:** Sunny pastes each phase report to Claude, who rates it Green / Amber / Red and raises issues before the next phase starts.

---

## 1. Context and goals

VirtuLab is a two-part gamified learning platform for rural STEM students (grades 6–12, PU level for the pilot):

1. **VirtuLab (offline Unity lab):** the student does a real practical. For this deadline: **Chemistry salt analysis, 12 salts**. Physics and Biology come later.
2. **This portal (online website):** the assessment, gamification and teacher-analytics layer.

**The core loop:**
`Student finishes a salt in the lab → lab shows a completion code (+ a result token) → student logs in to the portal and redeems it → the quiz for that salt unlocks → score, points, badges → teacher sees class results and learning gaps.`

**Why this is different from a normal quiz site (and must stay that way):**
- A quiz can only be unlocked by a **verifiable code from a completed offline practical**.
- **50% of every quiz is fixed theory; 50% is generated from how the student actually did the experiment.**
- Teacher analytics trace gaps back to **specific hands-on steps and tests**, not just quiz totals.

---

## 2. Where requirements come from

Every requirement carries a source tag:

| Tag | Meaning |
|---|---|
| **[SUNNY]** | Stated by Sunny in this project's conversations |
| **[BRIEF]** | From the official brief / the approved slides (STEM content, gamification, offline access, multilingual-ready, teacher analytics) |
| **[PROPOSED]** | Added by Claude as a sensible default so the spec is buildable. Sunny may change or drop these |

Requirements Sunny stated directly (kept verbatim in meaning):
- The portal needs a **special key that can only be accessed after the student finishes the experiment offline in the lab**, after which he can **answer quizzes**. **[SUNNY]**
- The **same website provides analytics and the teacher side**. **[SUNNY]**
- Finishing a salt in Assignment Mode gives a **code that unlocks that salt's quiz** (e.g. NaCl → NaCl quiz). A finished salt is never assigned again. **[SUNNY]**
- Quiz = **50% prefixed theory questions + the rest built from data collected on how the student did the experiment**. **[SUNNY]**
- Scoring/assignment features may use a **real online AI API key** (the portal is online, the lab is offline). **[SUNNY]**
- It should be **vibe-codable (Antigravity) in about 2 days**. **[SUNNY]**
- Covers **all three subjects eventually** (Physics, Chemistry, Biology), Chemistry first. **[SUNNY]**

Approved slide requirements: key/code validation, quiz unlock per completed experiment, scoring and feedback, badges/points/levels, teacher dashboard and analytics, multilingual-ready content structure, class-wide trends and learning gaps, participation trends. **[BRIEF]**

---

## 3. Shared foundations (apply to both parts)

### 3.1 Roles
| Role | Can do |
|---|---|
| Student | Log in, redeem codes, take quizzes, see own progress/badges |
| Teacher | Create classes, see only their own classes' students and analytics, export, reset PINs |
| Admin | Seed teachers, import question bank/salt data, view audit log, rotate secrets (use Django admin) |

### 3.2 Recommended stack **[BRIEF + PROPOSED]**
- **Frontend:** React (Vite) + Bootstrap, mobile-first, small bundle.
- **Backend:** Python **Django + Django REST Framework** (chosen over Flask because auth, ORM and the admin site come free, which saves most of a day). Flask is acceptable if Sunny prefers.
- **DB:** SQLite for development; PostgreSQL (or MySQL) for deployment.
- **Charts:** a light library (e.g. Chart.js or Recharts). Ask before adding anything heavy.
- **AI:** one provider, called **server-side only** (see 3.8).
- **Tools:** Git/GitHub, VS Code, Postman.

### 3.3 Identity rules
- **Student ID** = roll/registration number typed in the lab and on the portal. **Normalise** everywhere: trim spaces, uppercase, remove inner spaces. The code checksum depends on this exact string.
- Students log in with **Student ID + PIN** (4–6 digits, set at first login, teacher can reset). No email/phone for students. **[PROPOSED]**
- Students join a class once using a **class join code** created by the teacher. **[PROPOSED]**

### 3.4 Item model (built for 3 subjects now)
Use generic names so Physics/Biology need no schema change:
`subject` → `experiment` → `item`. For Chemistry salt analysis: subject `chemistry`, experiment `salt_analysis`, items = the 12 salts.

| Item ID | Salt | Quiz code | Cation | Anion |
|---|---|---|---|---|
| `nacl` | NaCl | NACL | Na⁺ | Cl⁻ |
| `nh4cl` | NH₄Cl | NH4CL | NH₄⁺ | Cl⁻ |
| `cuso4` | CuSO₄ | CUSO4 | Cu²⁺ | SO₄²⁻ |
| `feso4` | FeSO₄ | FESO4 | Fe²⁺ | SO₄²⁻ |
| `fecl3` | FeCl₃ | FECL3 | Fe³⁺ | Cl⁻ |
| `al2so43` | Al₂(SO₄)₃ | AL2SO43 | Al³⁺ | SO₄²⁻ |
| `znso4` | ZnSO₄ | ZNSO4 | Zn²⁺ | SO₄²⁻ |
| `bacl2` | BaCl₂ | BACL2 | Ba²⁺ | Cl⁻ |
| `caco3` | CaCO₃ | CACO3 | Ca²⁺ | CO₃²⁻ |
| `mgso4` | MgSO₄ | MGSO4 | Mg²⁺ | SO₄²⁻ |
| `pbno32` | Pb(NO₃)₂ | PBNO32 | Pb²⁺ | NO₃⁻ |
| `nh42co3` | (NH₄)₂CO₃ | NH42CO3 | NH₄⁺ | CO₃²⁻ |

### 3.5 Completion code (contract with the lab) **[SUNNY + PROPOSED]**
Format: `VL-<QUIZCODE>-<NONCE>-<CHK>` e.g. `VL-NACL-7K3Q-9F2A`

- `NONCE`: 4 random Crockford-base32 characters.
- `CHK`: first 4 characters (Crockford base32) of `HMAC-SHA256(secret, STUDENTID|ITEMID|NONCE|YYYYMMDD)`.
- **Validation (server):**
  1. Parse and upper-case the code; reject bad format.
  2. Recompute `CHK` for the logged-in student for each date in a window (default: today back 30 days, IST; also today+1 for clock drift). Match on any date.
  3. Reject if already redeemed (single-use, enforced by a unique DB constraint on the code).
  4. Rate-limit failures per student and per IP (default 5 per 10 minutes) and log every failure in `invalid_attempts`.
- **Known limit (state it in every security review):** the secret is also inside the lab APK, so a determined person can extract it and forge codes. Mitigations: single-use, student binding, rate limits, teacher audit of anomalies (quiz taken without a token, impossible durations). A later version should use server-issued challenges.
- Deliver a **Python reference verifier** (`tools/verify_code.py`) plus **test vectors** (JSON) so the Unity side can prove it generates matching codes.

### 3.6 Result token (how "how he did the experiment" reaches the server) **[SUNNY requirement; transport PROPOSED]**
The lab is offline, so the dynamic half of the quiz needs a transfer method. Default: the lab shows, next to the code, a **result token** the student copies (copy button) or scans (QR is COULD) into the portal.

Format: `VLR1.<base64url(zlib(json))>.<sig>` where `sig` = base64url of first 16 bytes of `HMAC-SHA256(secret, payload_bytes)`.

Payload (compact JSON, version `v:1`):
```json
{
  "v": 1,
  "student": "2411021061202",
  "item": "cuso4",
  "code": "VL-CUSO4-7K3Q-9F2A",
  "issued": 1761300000,
  "att": 2,
  "passed": true,
  "dur_s": 612,
  "tests": [ {"r": "naoh", "d": 3, "n": 1}, {"r": "nh4oh", "d": 12, "n": 2} ],
  "flame": true,
  "heat": false,
  "gas": ["co2"],
  "mis": ["reagent_excess", "skipped_confirmatory"],
  "wrong": [ {"cat": "Zn2+", "an": "SO4^2-"} ]
}
```
- `tests[].r` = reagent id, `d` = drops added, `n` = order in which it was done.
- **Mistake enum (proposed, must match the lab's EventLog):** `order_wrong`, `reagent_excess`, `skipped_flame`, `skipped_confirmatory`, `skipped_dissolve` (insoluble salt not dissolved first), `repeated_same_test`, `wrong_reagent_for_goal`, `wrong_submission`.
- No free text and no personal data other than the normalised student ID.
- Server checks: signature valid, `student` equals logged-in student, `code` equals the redeemed code, `v` supported. If any check fails the token is ignored (see fallback in A-Quiz rules).
- Target size ≤ 1.5 KB after compression.

### 3.7 Shared chemistry data package
One folder, `virtulab_data/`, used **identically** by the lab and the portal (the lab plan's `Assets/VirtuLab/Data` is the source; copy, don't fork):
- `salts/*.json` (observations per reagent; see lab plan 5.6). **Data requirement for this portal:** each reaction entry should carry an optional `supports` list (ions the observation points to) so the portal can build inference questions.
- `reagents/reagents.json`
- `quiz_map.json` (item id → quiz code)
- `question_bank.json` (the theory bank, see 3.9)

**The portal never invents chemistry.** All correct answers and distractors come from these files.

### 3.8 AI usage **[SUNNY + PROPOSED guardrails]**
Allowed: a short **feedback paragraph** on the result page and an optional **class-summary paragraph** on the teacher dashboard.
Rules:
- Server-side call only; key in an environment variable; never in the frontend or the repo.
- **AI never writes, changes or grades quiz questions.** Grading is a plain comparison with the stored answer.
- Prompts get **anonymised aggregates** (no names, no student IDs).
- The prompt includes the relevant facts from the data package; the reply is labelled "AI-generated".
- Cache results; if the API fails, times out or the quota is hit, fall back to **rule-based feedback text**. The portal must work fully with AI switched off.

### 3.9 Question schema
Theory bank questions (the existing bank will be converted to this):
```json
{
  "id": "sa_cuso4_014",
  "source": "bank",
  "subject": "chemistry",
  "experiment": "salt_analysis",
  "item": "cuso4",
  "radical": "Cu2+",
  "test_type": "confirmatory",
  "difficulty": "easy",
  "lang": "en",
  "question": "…",
  "options": ["…", "…", "…", "…"],
  "correct_answer": "…",
  "explanation": "…",
  "active": true
}
```
- `test_type` values: `flame, dry_heating, dilute_acid, conc_acid, group_reagent, wet_precipitation, solubility, gas_test, confirmatory, error_check, salt_identification`.
- `correct_answer` must equal one option exactly. 4 options, one correct.
- Dynamic questions use the same shape with `source: "dynamic"` and a `template` id; they are frozen into the attempt when generated.

### 3.10 i18n **[BRIEF]**
All student/teacher-visible UI strings in a message catalogue (e.g. react-i18next). Questions carry a `lang` field and the bank can hold several languages per question id later. **Ship English only**; prove the switch works with one stub language.

### 3.11 Configuration (one file, no magic numbers)
`config.json`/settings: quiz length (10), bank share (0.5), difficulty mix (40/40/20), points table, level thresholds, code date window (30), rate limits, attempts rules, AI on/off.

---

# PART A — STUDENT PORTAL

## A1. Student user journey
1. First visit: enter Student ID + class join code → set a PIN → home.
2. Returning: Student ID + PIN.
3. In the lab, after finishing a salt, copy the code and result token.
4. Portal → **Redeem** → paste code (+ token) → success shows the unlocked salt.
5. **Start quiz** → 10 questions → submit.
6. **Result:** score, points, new badges/level, per-question review with explanations, weak topics, experiment-linked insights.
7. Home grid updates; repeat for the next salt.

## A2. Requirements

| ID | Requirement | Priority | Source |
|---|---|---|---|
| S-01 | Register/login with Student ID + PIN; join a class with a join code | MUST | PROPOSED |
| S-02 | Normalise Student ID exactly as in 3.3 on every input | MUST | SUNNY |
| S-03 | Redeem screen accepts a code and an optional result token; clear error messages (bad format / not yours / already used / expired / rate-limited) | MUST | SUNNY |
| S-04 | A valid code unlocks exactly that salt's quiz, once | MUST | SUNNY |
| S-05 | Quiz of 10 questions: 5 from the theory bank + 5 dynamic from the result token, shown one per screen with a progress bar; dynamic questions carry a small "From your experiment" tag | MUST | SUNNY |
| S-06 | If the token is missing/invalid/too small, fill dynamic slots with extra theory questions, show "lab data not available", and flag the attempt `no_lab_data` (teacher can see it). Never block the quiz | MUST | PROPOSED |
| S-07 | Autosave answers on every selection (local + server); resume an unfinished attempt; queue submission and retry if the connection drops | MUST | PROPOSED |
| S-08 | One graded attempt per code. Grading is deterministic against stored answers | MUST | SUNNY |
| S-09 | Result page: score, points breakdown, correct/incorrect with explanation for every question, weak topics (by `test_type` and `radical`) | MUST | BRIEF |
| S-10 | Rule-based feedback text on the result page; optional AI feedback paragraph (3.8) | MUST / SHOULD (AI) | SUNNY |
| S-11 | Experiment-linked insights from the token, e.g. "You skipped the confirmatory test; here is what it would have shown" | SHOULD | SUNNY |
| S-12 | Points, levels, badges (A4) with level-up and badge toasts | MUST | BRIEF |
| S-13 | Home: grid of all 12 salts with status **Locked / Unlocked / Completed (score)**, points, level bar, badges strip, Redeem button | MUST | BRIEF |
| S-14 | Progress history (points ledger, past quizzes, review any past attempt) | SHOULD | BRIEF |
| S-15 | Ungraded **practice quiz** for completed salts (new random questions, no points, so points cannot be farmed) | SHOULD | PROPOSED |
| S-16 | Language selector wired to the i18n catalogue (English only) | MUST (wiring) | BRIEF |
| S-17 | Mobile-first, large touch targets, readable fonts, works on low-end Android Chrome; no heavy images | MUST | BRIEF |
| S-18 | Change PIN; logout; session expiry | SHOULD | PROPOSED |
| S-19 | Optional class leaderboard, **off by default**, teacher-controlled | COULD | PROPOSED |
| S-20 | QR scanner to read the code/token | COULD | PROPOSED |

## A3. Quiz engine rules (server-side)

**Composition (default 10 questions):**
- **Bank half (5):** sampled from `question_bank` where `item` is this salt, or its cation/anion radical, or `salt_identification`; difficulty mix 40/40/20 (easy/medium/hard); never repeat a question this student has already answered until the pool is exhausted; `active=true` only.
- **Dynamic half (5):** generated from the verified token using the templates in Appendix C. Select up to 5, spreading across different templates. If fewer than 5 can be generated, top up from the bank and mark the attempt `partial_dynamic`.
- Shuffle question order and option order. Freeze the exact questions and correct answers into the attempt record when the quiz starts.

**Dynamic generation principles:**
1. Correct answer comes only from the shared data package.
2. Distractors come from the same data (other salts' outcomes for the same reagent, other ions in scope). A distractor must never equal the correct answer or be chemically valid for this salt.
3. Deterministic: same token produces the same set (seed from the code) so a refresh does not change the quiz.
4. No student-identifying text inside a question.

**Scoring:** see A4. No pass/fail; scores unlock badges. No timer by default (flaky rural connectivity). Optional per-question time is recorded for analytics only.

**Edge cases the engine must handle:** token for a different student or code; token with unknown reagent ids; duplicate redeem requests (idempotent response); quiz abandoned and reopened on another device; submission after a reconnect; bank with fewer than 5 eligible questions (use what exists and report).

## A4. Gamification defaults (all configurable)

**Points**
| Event | Points |
|---|---|
| Correct bank question | Easy 5 · Medium 10 · Hard 15 |
| Correct dynamic question | 10 |
| Quiz completed (graded) | +20 |
| Lab flawless bonus (token: 1 attempt and no mistakes) | +10 |

(About 125 per salt, about 1,500 for all 12.)

**Levels:** L1 Beginner 0 · L2 Apprentice 150 · L3 Analyst 400 · L4 Chemist 800 · L5 Master 1200.

**Badges**
| Badge | Rule |
|---|---|
| First Spark | First code redeemed |
| Flawless | 100% on a graded quiz |
| Lab Perfectionist | Token shows 1 attempt and no mistakes |
| Sharp Observer | All dynamic questions correct in one quiz |
| Chloride Detective | Completed all 4 chloride salts (NaCl, NH₄Cl, FeCl₃, BaCl₂) |
| Sulphate Sleuth | Completed all 5 sulphate salts (CuSO₄, FeSO₄, Al₂(SO₄)₃, ZnSO₄, MgSO₄) |
| Carbonate Cracker | Completed both carbonate salts (CaCO₃, (NH₄)₂CO₃) |
| Comeback | Passed in the lab after a wrong submission (token `wrong` not empty) |
| Salt Master | All 12 salts completed |

Badge rules live in data (`rule_json`), not in view code.

## A5. Student screens
1. **Login / Join class**
2. **Home** (grid, points, level, badges, Redeem)
3. **Redeem** (code + token, validation messages)
4. **Quiz** (question, options, progress, save indicator, submit confirmation)
5. **Result** (score, points, badges, review, insights, feedback)
6. **Progress / History**
7. **Badges**
8. **Settings** (language, change PIN, logout)

---

# PART B — TEACHER PORTAL

## B1. Teacher user journey
1. Admin creates the teacher account → teacher logs in.
2. Creates a **class** (name, grade, section) → gets a **join code** to give students.
3. Students join; teacher sees the roster fill up.
4. As students redeem codes and take quizzes, the **class dashboard** updates.
5. Teacher opens **Learning gaps** to see what the class is weak at and which hands-on steps were the problem.
6. Drills into a **student** who is struggling; resets a PIN or fixes a roster entry if needed.
7. Exports results as CSV.

## B2. Requirements

| ID | Requirement | Priority | Source |
|---|---|---|---|
| T-01 | Teacher login; teacher sees only their own classes and students | MUST | PROPOSED |
| T-02 | Create/edit/archive classes; generate, rotate and disable a join code | MUST | PROPOSED |
| T-03 | Roster: list students, add one manually, bulk add via CSV, remove, move class, **reset PIN** | MUST (list, reset) / SHOULD (CSV, move) | PROPOSED |
| T-04 | **Class overview:** enrolled, active in last 7 days, codes redeemed, quizzes completed, average score, overall completion % | MUST | BRIEF |
| T-05 | **Per-salt table/heatmap:** students completed, average score, average time, no-lab-data count | MUST | BRIEF |
| T-06 | **Participation trend:** redemptions and quizzes per day/week (line chart) and a list of students with no activity | MUST | BRIEF |
| T-07 | **Learning gaps (quiz):** ranking of weak topics by `test_type` and `radical` using class-wide answers (B3) | MUST | BRIEF |
| T-08 | **Learning gaps (hands-on):** most common lab mistakes and skipped tests from tokens (e.g. "42% skipped the confirmatory test"), per salt and overall | MUST | SUNNY |
| T-09 | **Item analysis:** hardest questions (lowest % correct) with the most-chosen wrong option | SHOULD | PROPOSED |
| T-10 | **Student drill-down:** timeline of salts done, attempts, duration, quiz scores, mistakes, badges, `no_lab_data` flags | MUST | BRIEF |
| T-11 | Rule-based "suggested focus" text for the class from the top gaps; optional AI summary (3.8, anonymised) | SHOULD | SUNNY |
| T-12 | **Code audit:** invalid-code attempts, repeated failures, tokens that fail verification, implausible quiz durations, quizzes taken with no token | SHOULD | PROPOSED |
| T-13 | **CSV export** of class results (one row per student per salt) | SHOULD | PROPOSED |
| T-14 | Assignments: mark required salts and a due date; overdue/not-started flags | COULD | PROPOSED |
| T-15 | Leaderboard toggle for a class (default off) | COULD | PROPOSED |
| T-16 | Question bank viewer; enable/disable a question; add own questions | COULD | PROPOSED |
| T-17 | Printable PDF class summary | COULD | PROPOSED |
| T-18 | Admin (via Django admin): create teachers, import `question_bank.json` and `virtulab_data/`, view audit log, rotate the HMAC secret with a grace period | MUST (basic) | PROPOSED |
| T-19 | Seeded **demo dataset** (synthetic class of about 30 students with realistic spread) so the dashboard can be demonstrated | MUST | PROPOSED |

## B3. Analytics definitions (so numbers mean one thing)

- **Active student:** any redemption, quiz start or submit in the last 7 days.
- **Completion (per salt):** students with a graded quiz ÷ students enrolled.
- **Participation:** active students ÷ enrolled.
- **Topic gap score:** for each tag (`test_type`, `radical`, or the pair), `gap = 1 − (correct answers ÷ total answers)` across the class in the selected period. Show only tags with at least **10 answers**; rank descending.
- **Lab-mistake rate:** students whose token contains a mistake type ÷ students with a valid token for that salt.
- **Item difficulty:** % correct per question (bank questions only, minimum 8 answers).
- **Visibility limit (state it on the dashboard):** the portal only sees activity from **redeemed codes and tokens**. A student who tried and failed in the lab without redeeming is invisible. (COULD: the lab issues a "progress token" on failed attempts so struggling students appear. This needs a lab-side task.)

## B4. Teacher screens
1. **Login**
2. **My classes** (create, join code, archive)
3. **Class dashboard** (KPIs, per-salt table, participation trend)
4. **Learning gaps** (quiz gaps, hands-on gaps, hardest questions, suggested focus)
5. **Students** (roster, status chips) → **Student detail**
6. **Code audit**
7. **Export**
8. **(COULD)** Assignments, question bank

---

# 4. Data model (summary)

| Table | Key fields |
|---|---|
| `users` | id, role, display_name, student_id_norm (students), email (teachers), credential_hash, lang, created |
| `classes` | id, teacher_id, name, grade, section, join_code, active |
| `enrollments` | class_id, student_id, joined_at |
| `experiments` | id, subject, title |
| `items` | id, experiment_id, key (e.g. `nacl`), quiz_code, cation, anion, group_tag |
| `redemptions` | id, student_id, item_id, code (unique), redeemed_at, token_valid, token_json, no_lab_data, status |
| `quiz_attempts` | id, redemption_id, student_id, started_at, submitted_at, score, max_score, status, partial_dynamic, config_json |
| `quiz_questions` | id, attempt_id, position, source, template, question_json (frozen), correct_answer |
| `answers` | id, attempt_id, question_id, chosen, is_correct, time_ms |
| `points_ledger` | id, student_id, delta, reason, ref_id, created |
| `badges` / `user_badges` | key, name, rule_json / student_id, badge_id, earned_at |
| `question_bank` | the 3.9 schema |
| `invalid_attempts` | id, student_id, code_text, reason, ip, ts |
| `audit_log` | id, actor, action, detail_json, ts |

Add indexes on `student_id`, `class_id`, `item_id`, `(student_id, item_id)`.

# 5. API (summary)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login`, `/api/auth/register` | Student/teacher auth; register uses class join code |
| GET | `/api/me`, `/api/progress` | Profile, 12-salt grid, points, level, badges |
| POST | `/api/redeem` | `{code, token?}` → validate, unlock |
| POST | `/api/quiz/start` | `{redemption_id}` → creates/resumes attempt |
| GET / PUT | `/api/quiz/{id}`, `/api/quiz/{id}/answers` | Fetch quiz; autosave answers |
| POST | `/api/quiz/{id}/submit` | Grade, award points/badges |
| GET | `/api/quiz/{id}/result` | Result, review, insights, feedback |
| GET / POST | `/api/teacher/classes` | List/create classes |
| GET | `/api/teacher/classes/{id}/overview` | KPIs, per-salt table, trend |
| GET | `/api/teacher/classes/{id}/gaps` | Quiz gaps, hands-on gaps, item analysis |
| GET | `/api/teacher/classes/{id}/students`, `/students/{sid}` | Roster, drill-down |
| POST | `/api/teacher/classes/{id}/roster/import`, `/students/{sid}/reset-pin` | Roster management |
| GET | `/api/teacher/classes/{id}/export.csv` | CSV export |
| GET | `/api/teacher/audit` | Code audit |

All teacher endpoints enforce "own classes only". All list endpoints paginate.

---

# 6. Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | First load ≤ ~500 KB transferred, usable on 3G; no external font/CDN dependency; quiz question fetch ≤ 1 s on a normal connection |
| Resilience | Autosave + retry queue for quiz answers and submit; idempotent redeem/submit endpoints |
| Security | HTTPS only; password/PIN hashing; HMAC secret and AI key only in environment variables; rate limiting; teacher data isolation tested; no secrets in the frontend bundle |
| Privacy | Minimum personal data (student ID, display name, class); nothing public; synthetic data only in demos. Pilot with school students (minors): get school/teacher consent and check data-protection obligations with the mentor before real use |
| Accessibility | Large tap targets, high contrast, plain language; works at 360 px width |
| Compatibility | Last 2 versions of Chrome on Android; desktop Chrome/Edge for teachers |
| Maintainability | Config file (3.11); badge rules in data; one catalogue for UI strings; tests for the code verifier, token parser and quiz generator |
| Extensibility | Adding a Physics or Biology experiment = adding data files and bank questions, **no schema or code change** (verified by a dummy experiment) |

---

# 7. Out of scope for this build

Payments, parent portal, real-time lab-to-server sync, LLM-written or LLM-graded questions, native mobile app, VR, Physics/Biology content (structure only), SMS/email notifications, full LMS features, server-issued challenge codes (listed as a future hardening step).

---

# 8. Cross-document dependencies (the lab must provide these)

Tell the lab project's Antigravity prompts about these, otherwise the portal cannot deliver the 50% dynamic quiz:

1. **Result token output** in the lab (Phase 5): the `VLR1` token in 3.6, shown with the code and a copy button. This **changes lab decision D8** (previously "log stays on the device").
2. **Same code algorithm and Student ID normalisation** as 3.3 and 3.5, validated against the shared test vectors.
3. **EventLog mistake enum** matching 3.6.
4. **`supports` field** in the salt data (3.7).
5. **Wrong submissions recorded** in the log (needed for the `wrong` field and the Comeback badge).
6. **Shared `virtulab_data/` folder** kept in sync between the two projects.
7. *(COULD)* A "progress token" on failed assignments so the teacher can see struggling students.

---

# 9. Build plan

**Reality check:** about 2 days is plausible for the **MUST** items only, and only if the question bank is already converted to JSON and the salt data exists. If the result token is not ready from the lab, build the portal against the **test vectors and a token generator script** (so the two sides can progress in parallel). If time runs out, cut SHOULD/COULD first, then the AI feedback, then the audit page. Never cut the code check, the 50/50 quiz, or the teacher gap views.

## 9.1 Phases

| Phase | Goal | Key tasks | Acceptance |
|---|---|---|---|
| **W0** Contracts and scaffold (Day 1 AM) | Everything agreed and runnable | Repo, Django + DRF, React + Bootstrap, env files, `config.json`, `virtulab_data/` loader, `tools/verify_code.py` + test vectors, token generator script, question-bank importer | Verifier passes all test vectors; bank imports with zero errors; app boots |
| **W1** Auth, classes, redeem (Day 1) | Students can join and redeem | Models, auth, class join code, redeem endpoint (3.5), token verifier (3.6), rate limiting, audit logging | Valid code redeems once; wrong student, reuse, forged and expired codes all rejected; failures logged |
| **W2** Quiz engine and gamification (Day 1 PM) | Server can build and grade the 50/50 quiz | Bank sampler, dynamic templates (Appendix C), freeze-on-start, autosave, grade, points ledger, levels, badges | A sample token yields 5 + 5 questions; same token yields the same quiz; scoring matches A4; fallback works with no token |
| **W3** Student UI (Day 1 late) | Student side usable on a phone | Screens A5, i18n catalogue, offline retry queue | Full journey S-01 to S-13 works at 360 px width |
| **W4** Teacher APIs and analytics (Day 2 AM) | Numbers are right | Overview, per-salt, trend, gaps (quiz + hands-on), roster, reset PIN, student detail, CSV | Analytics match hand-computed values on the demo seed |
| **W5** Teacher UI and demo seed (Day 2) | Teacher side usable and demoable | Screens B4, charts, synthetic class generator (30 students, varied scores, realistic lab mistakes) | Dashboard shows believable data; isolation test passes (teacher A cannot see teacher B) |
| **W6** QA, hardening, deploy (Day 2 PM) | Safe to show and hand over | End-to-end scenarios (Section 10), security checks, deploy to a free host, README, known-issues list | All MUST scenarios pass; no secrets in the repo or bundle |

## 9.2 HARD RULES (paste verbatim into every Antigravity prompt)

```
HARD RULES — VirtuLab Portal
1. CONTRACTS ARE FROZEN: code format, result token format, question schema,
   Student ID normalisation and the virtulab_data folder structure are defined
   in the spec. Do not change them. If one must change, STOP and ask.
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
12. END EVERY PHASE with the Phase Report (Section 9.4).
```

## 9.3 Prompt template for ChatGPT → Antigravity

```
ROLE: You are the coding agent for the VirtuLab Companion Portal.
READ FIRST: VirtuLab_Portal_Requirements.md (repo root).

CURRENT PHASE: <W# — name>
GOAL: <copy from Section 9.1>
TASKS: <MUST tasks only unless I say SHOULD>
REQUIREMENT IDS IN SCOPE: <e.g. S-01..S-04, SH contracts 3.3, 3.5>
INPUTS I WILL PROVIDE: <question_bank file, salt data folder, test vectors>

<PASTE HARD RULES FROM SECTION 9.2 VERBATIM>

DELIVERABLES: code + tests + Phase Report.
ACCEPTANCE CRITERIA: <copy from Section 9.1>
IF BLOCKED OR UNSURE: stop and ask. Do not guess chemistry or change a contract.
```

## 9.4 Phase Report (end of every phase; save as `docs/PHASE_<n>_REPORT.md` and print in chat)

```
# PHASE <n> REPORT — <name>
1. Summary (3–5 lines, plain language)
2. Done vs planned (table: requirement ID | status | note)
3. Files created / modified
4. CONTRACT CHECK: statement that code format, token format, schema,
   ID normalisation and data folder structure are unchanged (or list the
   exceptions and why)
5. SECRETS CHECK: confirm no secret appears in the repo, bundle or logs
6. Tests run (names, results, how to rerun)
7. How to run and test (numbered steps)
8. MANUAL STEPS needed from Sunny (numbered, minimal)
9. Acceptance criteria result (each: Pass/Fail + evidence)
10. Known issues, risks, assumptions
11. Decisions needed from Sunny
12. Next phase and anything that changed the plan
```

**Reviewer rubric (Claude):** Requirement coverage · Contract integrity · Security and privacy · Chemistry correctness · Test evidence · Usability on a phone · Schedule risk — each Green / Amber / Red with a reason.

---

# 10. End-to-end acceptance scenarios

| # | Scenario | Pass condition |
|---|---|---|
| E1 | Happy path: valid code + token → redeem → quiz → submit | 5 bank + 5 dynamic questions; points and badge awarded; teacher dashboard shows it after refresh |
| E2 | Code typed by a different student | Rejected as "not yours"; logged |
| E3 | Reuse of a redeemed code | Rejected; original attempt untouched |
| E4 | Valid code, no token | Quiz opens with theory fill, `no_lab_data` flag visible to teacher |
| E5 | Token with a bad signature or wrong student | Ignored; quiz falls back as in E4; logged |
| E6 | Connection lost mid-quiz and mid-submit | Answers preserved; submit succeeds after reconnect; no double scoring |
| E7 | Forged code / many wrong codes | Rejected; rate limit triggers; appears in code audit |
| E8 | Same token regenerated | Identical quiz |
| E9 | Teacher A requests Teacher B's class or student | 403/404; isolation test passes |
| E10 | Demo seed gaps | Top 3 gaps and top lab mistakes on the dashboard match the seed's known design |
| E11 | CSV export | Opens in Excel with correct columns and counts |
| E12 | Add a dummy Physics experiment via data files only | Appears in the grid and quiz engine with no code or schema change |
| E13 | AI switched off or failing | Rule-based feedback shown; no error to the user |
| E14 | Completing all 12 salts | Salt Master badge and level update correct |

---

# 11. Open decisions (defaults apply unless Sunny changes them)

| # | Decision | Default |
|---|---|---|
| P1 | Backend framework | Django + DRF (Flask acceptable) |
| P2 | Hosting | Free-tier host; decide at W6 |
| P3 | How the token reaches the portal | Copy/paste string (QR is COULD) |
| P4 | Quiz length and split | 10 questions, 5 bank + 5 dynamic |
| P5 | Quiz attempts | 1 graded per code; ungraded practice retakes |
| P6 | Leaderboard | Off by default |
| P7 | AI provider and feedback scope | One provider; feedback paragraph only |
| P8 | Student onboarding | Self-register with class join code + PIN |
| P9 | Code date window | 30 days back (IST) |
| P10 | Languages at launch | English; i18n wired |
| P11 | Who builds Teacher vs Student side | Same agent, sequential (Student first) |

---

# Appendix C — Dynamic question templates

Each template lists: trigger (what must be in the token), question, correct answer source, distractor source. Generate up to 5 per quiz, spread across templates.

| ID | Trigger | Question (pattern) | Correct answer from | Distractors from |
|---|---|---|---|---|
| DQ-01 Observation recall | `tests[]` has reagent R with an outcome for this salt | "In your experiment you added {reagent} to your sample. What did you observe?" | Salt data: outcome text for R | Outcome texts for R on 3 other salts (must differ) |
| DQ-02 Inference | An outcome with a `supports` list | "You observed {observation}. Which ion does this support?" | `supports` entry | Other ions in scope |
| DQ-03 Excess behaviour | Tested reagent has a "dissolves in excess" stage | "What happens when {reagent} is added in excess?" | Stage data | Other stage outcomes from data |
| DQ-04 Procedure order | `mis` contains `order_wrong` | "Which step should come first?" | Procedure rules in data | Plausible wrong orders |
| DQ-05 Skipped test | `mis` contains `skipped_flame` or `skipped_confirmatory` | "Which test would have helped confirm {ion}?" | Salt's confirmatory/flame entry | Other tests not valid for this ion |
| DQ-06 Gas identification | `gas` not empty | "The gas you detected {detection}. Which gas is it?" | Gas data | Other gases from data |
| DQ-07 Wrong-guess contrast | `wrong` not empty | "You first suggested {wrong ion} but the answer was {right ion}. Which observation separates them?" | Salt data | Observations that do not separate them |
| DQ-08 Handling | `mis` contains `skipped_dissolve`, or the salt is insoluble in water | "Why must {salt} be dissolved in dilute acid before the cation tests?" | Data note | Plausible wrong reasons |

If a template lacks the data it needs, skip it and report which data field was missing.

---

# Appendix D — Demo seed specification

Create `tools/seed_demo.py` (synthetic only):
- 1 teacher, 1 class of 30 students, IDs `DEMO001`–`DEMO030`.
- Each student has 2–9 completed salts with scores drawn from a plausible distribution (mean about 62%, a few strong and a few weak students).
- **Planted patterns** so the dashboard proves itself: a class-wide weakness in `confirmatory` questions for Zn²⁺/Al³⁺, about 40% skipping the confirmatory test, `reagent_excess` common on NaOH/NH₄OH tests, 3 students with no activity in 10 days, 2 `no_lab_data` attempts, 1 invalid-code burst for the audit page.
- Activity spread across the last 21 days to make the participation trend meaningful.
