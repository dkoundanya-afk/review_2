# PHASE 6 REPORT: Learning Gaps & Student Performance Insights

## 1. Summary of Implemented Features
Implemented the teacher-facing **Learning Gaps & Student Performance Insights** module for the VirtuLab portal. The feature empowers educators with actionable, evidence-based analytics regarding theory misunderstandings, hands-on laboratory procedural errors, curriculum salt mastery, and students requiring pedagogical intervention.

Key elements built:
- **Backend Analytics Endpoint (`GET /api/teacher/classes/<int:pk>/learning-insights`)**: Computes topic accuracy, learning gap scores, 12-salt quiz and practical matrices, laboratory mistake error rates, and support indicators using real database records scoped strictly via `_own_class`.
- **Teacher Insights Interface (`/teacher/classes/:id/insights` & `/teacher/classes/:id/gaps`)**: Responsive dashboard featuring 4 overview metric cards, topic performance tables with gap score meters, complete 12-salt progress breakdowns with Blue cation and Orange anion chips, practical mistake category tables, and evidence-based student support recommendations.
- **Direct Navigation Integration**: Added a prominent "💡 Learning Insights" button to the teacher class dashboard (`TeacherDashboardScreen.jsx`).
- **Data Transparency & Minimum Evidence Enforcement**: Enforces a strict threshold of $n \ge 10$ valid recorded responses before flagging confirmed topic learning gaps. Clearly distinguishes low-evidence topics and handles classes without lab result tokens gracefully.
- **Bilingual Internationalization**: Complete English (`en.json`) and Kannada (`kn.json`) translation coverage across all analytics sections, table headers, and error states.

---

## 2. Existing Database Models & Relationships Used
Zero database migrations or schema modifications were made. The implementation leveraged the existing frozen models:
- **`ClassRoom` & `Enrollment`**: Used to identify enrolled students and enforce strict multi-tenant teacher isolation.
- **`QuizAttempt` & `QuizQuestion`**: Filtered for submitted graded attempts (`is_practice=False`, `status="submitted"`) to evaluate performance on real quiz questions. Extracted question topic tags (`test_type`) and salt references (`redemption__item`).
- **`Answer`**: Queried `is_correct` and `chosen` to compute exact topic and salt accuracy metrics.
- **`Redemption`**: Extracted practical completion status, missing lab data flags (`no_lab_data`), and telemetry payload (`token_json`).
- **`Item`**: Rendered all 12 curriculum salts with cations, anions, formulas, and plain names.

---

## 3. Backend Endpoints Created or Modified
- **`GET /api/teacher/classes/<int:pk>/learning-insights`**:
  - Authenticated teacher only (`@permission_classes([IsTeacher])`).
  - Class ownership verified via `_own_class(request, pk)`. Returns HTTP 404 if the classroom does not belong to the authenticated teacher.
  - Returns structured JSON containing:
    - `summary`: Overview KPI counters (`total_students`, `total_answers_recorded`, `topics_with_gaps_count`, `salts_with_data_count`, `has_telemetry`, `valid_tokens_count`, `total_mistakes_recorded`, `students_needing_support_count`, `min_evidence_threshold`).
    - `topics`: Sorted array of topic-level metrics (topic tag, friendly label, total answers, correct, incorrect, accuracy %, gap score, sufficient evidence boolean).
    - `salts`: Performance matrix across all 12 salts (name, formula, ions, active students, submissions count, avg score %, correct %, practical completions, missing lab data count).
    - `practical_mistakes`: Telemetry status, denominator token count, and frequencies of the 8 standard laboratory error categories.
    - `students_needing_support`: List of students flagged with specific, evidence-based observation reasons.
    - `notice`: Data transparency disclaimer.

---

## 4. Frontend Files Created or Modified
- **`frontend/src/screens/TeacherGapsScreen.jsx`** *(New)*: Full-featured teacher learning insights screen with loading, error, empty states, topic tables, salt matrices, mistake breakdowns, and student support lists.
- **`frontend/src/screens/TeacherDashboardScreen.jsx`** *(Modified)*: Added the prominent "💡 Learning Insights" action button in the class dashboard top bar.
- **`frontend/src/App.jsx`** *(Modified)*: Registered protected routes `/teacher/classes/:id/insights` and alias `/teacher/classes/:id/gaps` mapped to `TeacherGapsScreen`.
- **`frontend/src/locales/en.json`** *(Modified)*: Added `teacher_insights` translation dictionary and `learning_insights_btn`.
- **`frontend/src/locales/kn.json`** *(Modified)*: Added Kannada translations for `teacher_insights` and `learning_insights_btn`.

---

## 5. Topic Learning-Gap Calculation & Minimum Evidence Rules
- **Topic Definition**: Grouped by question `test_type` (e.g. `dilute_acid`, `flame`, `group_reagent`, `confirmatory`, `gas_test`, `solubility`, etc.).
- **Formula**:
  $$\text{Learning-Gap Score} = 1 - \frac{\text{Correct Answers}}{\text{Total Valid Graded Answers}}$$
  A score of $0.0$ represents perfect mastery, while $1.0$ indicates total inaccuracy.
- **Minimum Evidence Requirement**:
  Per the project specification, a minimum of **10 valid recorded answers** ($n \ge 10$) is required for a topic to qualify as confirmed evidence of a learning gap. Topics with $< 10$ answers are categorized with `sufficient_evidence: false` and can be toggled in the UI to prevent false conclusions on small sample sizes.
- **Scoping**: Derived exclusively from submitted graded quizzes (`is_practice=False`, `status="submitted"`). Practice attempts are excluded to prevent skewed metrics.

---

## 6. Salt Performance Calculation Definitions
For all 12 curriculum salts:
- **Active Students**: Count of distinct students enrolled in the class with submitted graded quiz attempts for that salt.
- **Valid Graded Submissions**: Total count of submitted graded attempts.
- **Average Quiz Score %**: Arithmetic mean of $(a.correct\_count / a.total) \times 100$ across all valid submissions. Displayed as `—` if no submissions exist (never falsely reported as 0%).
- **Correct Answer %**: Aggregate correct questions divided by aggregate questions answered across that salt's quizzes.
- **Practical Completed Students**: Count of distinct students with verified redemptions (`token_valid=True`).
- **Missing Lab Data**: Count of redemptions where `no_lab_data=True` (code entered without a lab result token).

---

## 7. Practical Mistake Analysis Methodology
- **Source**: Evaluated from verified lab result tokens (`token_valid=True, no_lab_data=False`) stored in `Redemption.token_json`.
- **Enum Conformance**: Checked against the 8 official laboratory mistake identifiers from `lab_pack/token_codec.py`:
  1. `order_wrong` (Wrong Test Order)
  2. `reagent_excess` (Excess Reagent Added)
  3. `skipped_flame` (Skipped Flame Test)
  4. `skipped_confirmatory` (Skipped Confirmatory Test)
  5. `skipped_dissolve` (Skipped Insoluble Salt Dissolution)
  6. `repeated_same_test` (Repeated Identical Test)
  7. `wrong_reagent_for_goal` (Wrong Reagent For Test Goal)
  8. `wrong_submission` (Incorrect Radical Identified)
- **Denominator**: Total verified tokens in the class (`valid_tokens_count`).
- **Zero-Telemetry Handling**: If no students have submitted lab tokens with telemetry, `has_telemetry` is `false`, and an explanatory notice is displayed. Offline activity is never fabricated.

---

## 8. Criteria Used to Identify Students Needing Support
Students are flagged based strictly on concrete, recorded evidence:
1. **Low Average Graded Quiz Score**: Enrolled student has completed $\ge 2$ graded quizzes with an overall average score $< 50.0\%$.
2. **Topic Difficulty**: Student answered $\ge 4$ questions in a single topic category and achieved $\le 25.0\%$ accuracy.
3. **Repeated Practical Mistakes**: Student accumulated $\ge 2$ procedural mistakes across their verified laboratory runs.
4. **Recent Inactivity**: Student enrolled $\ge 7$ days ago, but has 0 practical redemptions and 0 quiz attempts in the last 7 days.
Every recommendation displays the exact, non-judgmental observation string (e.g. *"Low average quiz score: 45.0% across 2 graded quizzes"* or *"Recorded 2 lab run mistakes (Excess Reagent Added, Skipped Confirmatory Test)"*).

---

## 9. Teacher and Class Isolation
- **Authentication**: `IsTeacher` permission class blocks all unauthenticated and student users (returning 401 and 403 respectively).
- **Ownership Scoping**: Evaluated via `_own_class(request, pk)`. Querying a class owned by another teacher immediately raises HTTP 404 (`not_found`).
- **Student Scoping**: All database queries (`QuizAttempt`, `Answer`, `Redemption`) are strictly filtered via `student_id__in=classroom.enrollments.values_list("student_id")`. Students in other classrooms never leak into aggregate calculations.

---

## 10. Data Limitations and Unavailable Insights
1. **Offline Lab Activity**: When students perform experiments in the offline Unity lab without exporting/redeeming a VLR1 result token (or using completion code only), procedural errors cannot be observed by the server. The portal reports `has_telemetry: false` and counts `no_lab_data` redemptions.
2. **Unclassified Question Bank Topics**: 211 questions in `question_bank.json` carry `test_type: "unclassified"` per OVERRIDE 3 and DECISION D8. These are grouped transparently under "General Chemistry & Theory" rather than guessing tags.
3. **Practice Attempts**: Practice quizzes allow multiple retries with answer reveals; thus they are intentionally excluded from learning gap statistics to avoid distorting diagnostic data.

---

## 11. Verification & Automated Tests
- **Backend Test Suite**:
  Ran: `.\backend\.venv\Scripts\python.exe backend\manage.py test api`
  - **52 tests executed, 52 passed (0 errors, 0 failures)**.
  - Added `test_class_learning_insights_analytics_and_isolation` in `backend/api/tests/test_w1.py` validating:
    - Teacher isolation (404 on cross-teacher class access).
    - Role protection (403 for students).
    - Topic accuracy and $1 - (\text{correct}/\text{total})$ gap score calculation.
    - Minimum evidence threshold ($n \ge 10$ flagged as sufficient, $n < 10$ flagged as insufficient).
    - 12-salt matrix counts and score averages.
    - Practical mistake occurrence counts, rate percentages, and affected salts.
    - Student support flagging criteria.
- **Lab Pack Suite**:
  Ran: `.\backend\.venv\Scripts\python.exe -m unittest discover -s lab_pack`
  - **27 tests executed, 27 passed (0 errors, 0 failures)**.
- **Frontend Linter (`oxlint`)**:
  Ran: `npm.cmd run lint`
  - **0 errors** across all 32 files.
- **Frontend Production Build**:
  Ran: `npm.cmd run build`
  - **Vite production bundle built cleanly in 304ms**.

---

## 12. Known Issues & Remaining Work
- Zero regressions introduced; student and teacher workflows remain intact.
- Phase 6 is complete. Awaiting review before proceeding to Phase 7.
