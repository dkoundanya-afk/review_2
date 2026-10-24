# PHASE 1 REPORT — Codebase Inspection & Teacher-Side Foundation Analysis

**Audience:** Project Owner & Reviewers  
**Author:** Antigravity  
**Date:** 2026-10-22  
**Status:** Complete — Ready for Review  

---

## 1. Existing Frontend and Backend Architecture

### Backend Architecture
- **Framework:** Django 6.1.2 + Django REST Framework (DRF) 3.18.3.
- **Python Version:** Python 3.14.7.
- **Database:** SQLite (`backend/db.sqlite3`), with `BigAutoField` default auto field.
- **Core Structure:**
  - `backend/core/`: Project configuration (`settings.py`, `urls.py`, `wsgi.py`). Settings load environment variables via `python-dotenv`. Default timezone is `Asia/Kolkata` (IST) per spec.
  - `backend/api/models.py`: 14 relational models implementing spec §4:
    - Core domain: `Experiment`, `Item` (12 salts with cation/anion pairs, formula, plain name, and group tag).
    - User management: `Profile` (role: `student` or `teacher`, display name, language, PIN status flags), `AuthToken` (expiring Bearer tokens stored as SHA-256 hashes).
    - Class management: `ClassRoom` (teacher FK, name, grade, section, unique 6-char Crockford join code, active/archive, join_enabled, leaderboard toggle), `Enrollment` (unique student-classroom link).
    - Progress & Redemption: `Redemption` (single-use unlock per student-salt, token validation, `no_lab_data` flag), `BankQuestion` (schema 3.9 theory bank).
    - Quiz & Assessment: `QuizAttempt` (attempt status, seed, points awarded, `no_lab_data`), `QuizQuestion` (frozen questions & correct answers), `Answer` (chosen answer, correctness, time_ms).
    - Gamification: `PointsLedger` (idempotent delta entries), `Badge`, `UserBadge`.
    - Security & Audit: `InvalidAttempt` (rate limiting and failed attempt tracking), `AuditLog` (action audit trail).
  - `backend/api/auth.py`: Token authentication (`TokenAuth`), role permissions (`IsStudent`, `IsTeacher`), Crockford base32 join code generation and normalization, Student ID cleaning (`A-Z0-9._/-`).
  - `backend/api/services.py`: Encapsulates business logic: rate limiting (5 failures / 10 min window), audit logging, points ledger calculation, rule-based badge engine (`badges.json`), code verification (`redeem_code`), and student progress grid aggregation.
  - `backend/api/quiz.py`: 50/50 quiz engine combining theory questions from `question_bank.json` with dynamic questions generated from offline experiment tokens using Appendix C templates (DQ-01, DQ-02, DQ-03, DQ-05, DQ-06, DQ-08).
  - `backend/api/views.py` & `backend/api/views_quiz.py`: Thin HTTP view handlers.
  - `lab_pack/`: Shared contract library containing `verify_code.py` (canonical code validation `VL-<CATION>-<ANION>-<NONCE>-<CHK>`), `token_codec.py` (`VLR1` token parser), and unit test vectors.

### Frontend Architecture
- **Framework & Tooling:** React 19 (`react` 19.2.8, `react-dom` 19.2.8) built with Vite 8 (`vite` 8.3.0).
- **Routing:** React Router DOM v7 (`react-router-dom` 7.18.4).
- **Styling:** Vanilla CSS (`frontend/src/index.css`) layered over Bootstrap 5 (`bootstrap` 5.3.8). Mobile-first design optimized for 360 px viewport, touch targets >= 44 px, custom chemistry tokens (blue cation `#0d6efd`, orange anion `#fd7e14`).
- **State & Session Management:** React Context (`frontend/src/session.jsx`) persisting Bearer token (`vl_token`) and profile (`vl_me`) in `localStorage`. Central fetch wrapper (`frontend/src/api.js`) handles Bearer header injection, JSON serialization, and global 401 session clearing.
- **Localization:** `react-i18next` 17.1.0 with catalog at `frontend/src/locales/en.json`.
- **Chemistry Helpers:** `frontend/src/utils/chemistry.js` and `frontend/src/components/IonDisplay.jsx` format formulas with subscripts and ion charges with superscripts.

---

## 2. Student-Side Features Already Implemented

| ID | Requirement / Feature | Status | Implementation Details |
|---|---|---|---|
| **S-01** | Student Register & Login | **Done** | `RegisterScreen.jsx`, `LoginScreen.jsx`, backend `/api/auth/register`, `/api/auth/login`. |
| **S-02** | Student ID Normalization | **Done** | Strips whitespace, forces uppercase, validated against `^[A-Z0-9][A-Z0-9._/-]{0,39}$`. |
| **S-03** | Code & Token Redemption | **Done** | `RedeemScreen.jsx`, backend `/api/redeem`. Rejects forged, expired, mismatched, and already-used codes. |
| **S-04** | Single-Use Unlock per Salt | **Done** | Unique constraint on `(student, item)` and globally unique `code`. Re-submitting returns existing unlock idempotently. |
| **S-05** | 10-Question 50/50 Quiz | **Done** | `QuizScreen.jsx`, backend `/api/quiz/start`, `/api/quiz/<id>`. 5 bank questions + up to 5 dynamic questions tagged "From your experiment". |
| **S-06** | Lab Data Fallback | **Done** | When token is missing or invalid, dynamic questions are replaced with bank questions, flagged `no_lab_data`. |
| **S-07** | Autosave Answers | **Done** | Answers saved to local storage on choice and synced to backend via `PUT /api/quiz/<id>/answers`. |
| **S-08** | Graded Attempt Finality | **Done** | Exactly one graded attempt per redemption. Practice quizzes available only after graded completion. |
| **S-09** | Result Review & Explanations | **Done** | `ResultScreen.jsx`, backend `/api/quiz/<id>/result`. Shows points breakdown, score, question review, and weak topics. |
| **S-10** | Result Feedback | **Done** | Rule-based feedback generated based on performance and mistake tags. |
| **S-11** | Experiment Insights | **Done** | Insights highlighting skipped flame or confirmatory tests displayed on result screen. |
| **S-12** | Gamification (Points & Badges) | **Done** | Points ledger, 5 levels (Beginner to Master), 9 badges evaluated in `services.py` from `badges.json`. |
| **S-13** | 12-Salt Dashboard Grid | **Done** | `HomeScreen.jsx`, `SaltCard.jsx`, 2-column mobile grid showing Locked / Unlocked / Completed status with ion chips. |
| **S-14** | Progress History | **Done** | `HistoryScreen.jsx`, backend `/api/history`. Full log of past quiz attempts and point awards. |
| **S-15** | Ungraded Practice Quiz | **Done** | Completed salts can be practiced without awarding extra points or badges. |
| **S-16** | Language Switching | **Done** | `LanguageSelector.jsx` wired to i18n and synced to backend user profile (`PATCH /api/me/language`). |
| **S-17** | Mobile-First UI (360px) | **Done** | Large touch targets, responsive bottom navigation (`BottomNav.jsx`), accessible typography. |
| **S-18** | PIN Management & Logout | **Done** | `ChangePinScreen.jsx`, `SettingsScreen.jsx`, token revocation via `/api/auth/logout`. |

---

## 3. Existing Teacher-Related Functionality and Exact Files

The existing backend was constructed during Phase W1 with core teacher data structures and endpoints. However, **no frontend teacher UI exists yet**.

### A. Database Models (`backend/api/models.py`)
- **`Profile` (lines 37–48):** Supports `role="teacher"`.
- **`ClassRoom` (lines 50–63):** Stores `teacher` (FK to `auth.User`), `name`, `grade`, `section`, `join_code` (unique 6-character Crockford alphanumeric string), `join_enabled`, `active` (for archiving), `leaderboard` (disabled by default), and creation timestamp.
- **`Enrollment` (lines 65–73):** Connects students to `ClassRoom` records (`unique_together` constraint on `classroom` and `student`).

### B. Authentication & Permissions (`backend/api/auth.py`)
- **`IsTeacher` (lines 56–59):** DRF permission class verifying `request.user.is_authenticated and request.user.profile.role == 'teacher'`.
- **`new_join_code()` (lines 74–80):** Generates non-confusing join codes using Crockford alphabet `23456789ABCDEFGHJKMNPQRSTUVWXYZ`.

### C. Backend API Endpoints (`backend/api/views.py` & `backend/api/urls.py`)
- **`POST /api/auth/login` (lines 79–99):** Teacher login logic already exists. If `identifier` contains `@`, the backend treats it as an email address, sets `role="teacher"`, verifies the password hash, and issues a Bearer token.
- **`POST /api/auth/change-pin` (lines 114–130):** Enforces an 8+ character password for teachers (unlike 4–6 digit numeric PINs for students).
- **`_own_class(request, pk)` (lines 172–178):** Enforces **Teacher Isolation (HARD RULE 8)**. Classes not owned by the teacher raise `ApiError(404, "not_found")`.
- **`GET /api/teacher/classes` (lines 186–199):** Returns list of active and archived classes owned by the authenticated teacher, with student count.
- **`POST /api/teacher/classes` (lines 186–199):** Creates a new classroom with auto-generated join code.
- **`PATCH /api/teacher/classes/<int:pk>` (lines 201–216):** Updates class name, grade, section, toggles `join_enabled`, `active`, or `leaderboard`, and rotates join code.
- **`GET /api/teacher/classes/<int:pk>/students` (lines 218–229):** Returns class roster with `student_id`, `display_name`, `joined_at`, `pin_set`, `redeemed` count, total `points`, and current `level`.
- **`POST /api/teacher/classes/<int:pk>/students/<str:sid>/reset-pin` (lines 231–246):** Generates temporary 6-digit PIN, sets `must_change_pin=True`, terminates all active student sessions, and audits the action.

### D. Management Commands
- **`backend/api/management/commands/create_teacher.py`:** CLI tool to create teacher accounts:
  ```powershell
  backend\.venv\Scripts\python.exe backend\manage.py create_teacher --email teacher@school.in --name "Demo Teacher" --password "TeacherPass123!"
  ```

### E. Existing Automated Tests (`backend/api/tests/test_w1.py`)
- **`TestTeacherIsolation` (lines 249–284):** Validates teacher login, role separation (student blocked from teacher APIs with 403, teacher blocked from student APIs with 403), strict isolation between teachers (Teacher 2 receives 404 for Teacher 1's classes and students), class creation, join code rotation, roster inspection, and student PIN resets.

---

## 4. Missing Teacher-Side Functionality

The following items are missing and must be developed in subsequent phases:

### A. Backend Endpoints (Spec §5 & Part B)
1. **Class Analytics Overview (T-04, T-05, T-06):**
   - `GET /api/teacher/classes/<int:pk>/overview`
   - Class KPIs (enrolled count, active in 7 days, codes redeemed, quizzes completed, average score, completion %).
   - 12-salt summary table/heatmap (completions, avg score, avg duration, `no_lab_data` count).
   - Participation trends (daily/weekly redemptions and quiz submissions).
2. **Learning Gap Analytics (T-07, T-08, T-09, T-11):**
   - `GET /api/teacher/classes/<int:pk>/gaps`
   - Theory quiz learning gaps ranked by `test_type` and `radical` with >=10 response threshold.
   - Hands-on lab mistake rates from tokens (e.g. % skipped confirmatory, % excess reagent).
   - Item analysis for hardest questions and top wrong options.
   - Rule-based suggested focus text for the teacher.
3. **Student Drill-Down (T-10):**
   - `GET /api/teacher/classes/<int:pk>/students/<str:sid>`
   - Detailed history of individual student's salt progress, quiz scores, attempt duration, token mistakes, and badges.
4. **Roster Import & Export (T-03, T-13):**
   - `POST /api/teacher/classes/<int:pk>/roster/import` (CSV bulk add).
   - `GET /api/teacher/classes/<int:pk>/export.csv` (CSV export of student results).
5. **Code & Integrity Audit (T-12):**
   - `GET /api/teacher/audit` (Invalid codes, repeated failures, suspicious durations).

### B. Frontend Architecture & UI
1. **Teacher Login Flow:** `LoginScreen.jsx` currently forces uppercase input, restricts length to 6 characters, and only accepts digits (`inputMode="numeric"`), preventing teachers from typing email addresses and passwords.
2. **Role-Aware Navigation & Routing:** `ProtectedRoute.jsx` and `PublicOnlyRoute.jsx` automatically route all authenticated users to `/` (student home), which crashes for teachers because `/api/progress` returns 403 for `role="teacher"`.
3. **Teacher Layout & Navigation:** Missing desktop-oriented header/sidebar (`TeacherLayout.jsx`) with class selector and tabs (Overview, Gaps, Roster).
4. **Teacher Screens:** No screens exist for My Classes, Class Dashboard, Learning Gaps, Student Roster, or Student Details.
5. **i18n Catalogue:** `frontend/src/locales/en.json` has zero teacher keys.

---

## 5. Recommended Teacher-Side Route and Component Structure

To protect the student side while maintaining a clean separation of concerns, the following structure is recommended:

### A. Routing & Navigation Strategy
1. **Dual-Mode Login on `/login`:**
   - Update `LoginScreen.jsx` with a toggle tab: **"Student"** (Student ID + PIN) vs **"Teacher"** (Email + Password).
   - Keeps login at the single URL `/login`, leaving student bookmarks and workflows intact.
2. **Role Protection Component (`TeacherRoute.jsx`):**
   - Verifies `isAuthenticated && me?.role === "teacher"`.
   - If not authenticated -> redirect to `/login`.
   - If authenticated as student -> redirect to `/`.
3. **Update Existing `ProtectedRoute.jsx`:**
   - If `me?.role === "teacher"`, redirect away from student routes to `/teacher/classes`.
4. **Teacher Route Map:**
   ```
   /teacher/classes                   -> TeacherClassesScreen (My Classes)
   /teacher/classes/:id               -> TeacherDashboardScreen (Class Overview & KPIs)
   /teacher/classes/:id/gaps          -> TeacherGapsScreen (Quiz & Hands-on Gaps)
   /teacher/classes/:id/students      -> TeacherRosterScreen (Roster, PIN Reset, CSV)
   /teacher/classes/:id/students/:sid -> TeacherStudentDetailScreen (Drill-down)
   ```

### B. Component Breakdown
- **Layout:** `TeacherLayout.jsx` featuring top bar, active class selector, navigation links, teacher display name, language selector, and logout.
- **Shared Chemistry Display:** Re-use `IonChip` and `FormattedFormula` from `frontend/src/components/IonDisplay.jsx` so that blue cation `#0d6efd` and orange anion `#fd7e14` styling remains completely uniform.
- **Analytics Visuals:** Vanilla CSS and Bootstrap progress bars, lightweight SVG/Canvas charts (no heavy dependencies per HARD RULE 6).

---

## 6. Authentication and Data-Isolation Risks

1. **Query Leakage in Multi-Table Analytics (HARD RULE 8 Risk):**
   - *Risk:* In W4 analytics, aggregating `QuizQuestion` or `Answer` rows without joining through `ClassRoom.enrollments` could disclose answers from students in other teachers' classes.
   - *Mitigation:* Define a reusable helper query `enrollments.filter(classroom_id=cid, classroom__teacher=request.user).values_list('student_id', flat=True)` and base all analytics solely on students in that list.
2. **Information Disclosure on 404 vs 403:**
   - *Risk:* Returning 403 when a teacher accesses another teacher's class reveals that the class ID exists.
   - *Mitigation:* Adhere to `_own_class()` convention: any foreign or non-existent class MUST return `404 not_found`.
3. **Session Token Expiry & PIN Reset:**
   - Temporary PINs generated during teacher reset are shown only once in the API response and hashed in the database; all existing student sessions are deleted immediately.

---

## 7. Tests and Startup Checks Performed

| Check / Test Suite | Command Executed | Result | Notes |
|---|---|---|---|
| **Question Bank Importer Tests** | `python -m unittest tools.tests.test_import_bank -v` | **PASS** (24/24) | 0.148s runtime. |
| **Lab Pack Contract Tests** | `python -m unittest lab_pack.test_lab_pack -v` | **PASS** (27/27) | 0.045s runtime. Tests code verifier and token parser against frozen vectors. |
| **Django Unit Tests** | `backend\.venv\Scripts\python.exe backend\manage.py test api` | **PASS** (47/47) | 7.207s runtime. 33 W1 tests (including `TestTeacherIsolation`) + 14 W2 quiz tests. |
| **Django System Check** | `backend\.venv\Scripts\python.exe backend\manage.py check` | **PASS** | 0 issues identified. |
| **Database Migrations** | `backend\.venv\Scripts\python.exe backend\manage.py migrate` | **PASS** | 19 migrations applied cleanly to SQLite. |
| **Initial Data Loader** | `backend\.venv\Scripts\python.exe backend\manage.py load_data` | **PASS** | 12 salt items, 9 badges, 600 bank questions loaded. |
| **Teacher Creation Command** | `backend\manage.py create_teacher ...` | **PASS** | Successfully provisioned `teacher@school.in`. |
| **Backend Live Server** | `backend\manage.py runserver 8000` | **PASS** | `/api/health/` returned `{"status":"ok"}`. |
| **Teacher Auth & Class APIs** | Live HTTP requests | **PASS** | Teacher login returned token; `POST /api/teacher/classes` created class; `GET /api/teacher/classes` listed classes. |
| **Frontend Node.js Check** | `node --version`, `npm --version` | **FAILED (Missing)** | Node.js and npm are not installed in the Windows environment. |

*Total automated tests executed:* **98 tests, 98 passed, 0 failed.**

---

## 8. Files Changed During Phase 1

1. **`.env` (Created):**
   - *Reason:* Django settings require `SECRET_KEY` and `HMAC_SECRET` in environment variables (HARD RULE 4). Generated a secure key and test secret to run migrations, tests, and local server. This file is gitignored.
2. **`backend/.venv/` (Created):**
   - *Reason:* Standard virtual environment installed with exact requirements from `backend/requirements.txt` (`django==6.1.2`, `djangorestframework==3.18.3`, `python-dotenv==1.1.1`). This folder is gitignored.
3. **`docs/PHASE_1_REPORT.md` (Created):**
   - *Reason:* Phase 1 deliverable documentation per HARD RULE 12.

*No existing student source code, tests, contracts, or data files were modified.*

---

## 9. Blockers & Decisions Before Proceeding to Phase W4/W5

### Blocker 1: Node.js and npm Installation
- Node.js is required to install frontend dependencies (`npm install --prefix frontend`) and launch Vite (`npm run dev --prefix frontend`).
- **Recommended Action:** Please install Node.js 24 LTS (or approve running `winget install OpenJS.NodeJS.LTS`).

### Decision 1: Teacher Login UI Approach
- **Option A (Recommended):** Add a tab/toggle on `LoginScreen.jsx` ("Student Login" | "Teacher Login"). Student mode retains numeric keypad and student ID formatting; Teacher mode enables standard email and password inputs.
- **Option B:** Separate `/teacher/login` page.

---
*End of Phase 1 Report. Awaiting user review and further instructions before proceeding.*
