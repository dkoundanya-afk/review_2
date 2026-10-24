# PHASE 7 REPORT: CSV Export & Teacher Reports — Code Review & Verification

## 1. Summary of Implemented Features
Phase 7 implements secure, production-grade **CSV Exports & Teacher Reports** for the VirtuLab portal. The feature allows authenticated educators to download comprehensive, spreadsheet-compatible academic records for their classrooms.

Key elements verified:
- **5 Dedicated Backend CSV Export Endpoints**:
  1. Class Roster (`/api/teacher/classes/<id>/export/roster`)
  2. Student Quiz Results (`/api/teacher/classes/<id>/export/quiz-results`)
  3. Student Practical Records (`/api/teacher/classes/<id>/export/practical-records`)
  4. Salt Performance Matrix (`/api/teacher/classes/<id>/export/salt-performance`)
  5. Learning Gaps & Insights (`/api/teacher/classes/<id>/export/learning-insights`)
- **CSV Formula Injection (DDE) Protection**: Sanitizes any cell starting with formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`, `\n`, `\v`, `\f`) directly or after stripping leading whitespace/control chars by prepending a single quote (`'`), while strictly preserving valid numeric values (integers, floats, negative values like `-42`, `-12.5`, `-0.05`, `+100`).
- **UTF-8 with BOM Support**: Outputs the standard UTF-8 Byte Order Mark (`\xef\xbb\xbf`) so Microsoft Excel (Windows/Mac), LibreOffice, and Google Sheets render Unicode and Kannada characters (`ಆನಂದ್ ಕುಮಾರ್`) cleanly without mojibake.
- **Audit Logging**: Logs every export download event to `AuditLog` with teacher ID, classroom ID, report type, and timestamp, recording zero sensitive student data or CSV payloads.
- **Frontend Export Section on Dashboard**: Responsive cards on `/teacher/classes/:id` providing one-click CSV downloads with active loading states, error alerts, and success confirmations.
- **Zero Heavy Dependencies**: Pure standard library Python (`csv`, `io`) and browser-native fetch/blob downloads.
- **Bilingual Translations**: Complete English (`en.json`) and Kannada (`kn.json`) support.

---

## 2. Review Checklist & Code Verification Results (12 Mandatory Items)

### 1. Endpoint Verification & Isolation Controls
- All five export endpoints are decorated with `@api_view(["GET"])` and `@permission_classes([IsTeacher])`.
- Class ownership is strictly enforced via `_own_class(request, pk)`. Querying an invalid classroom ID or a classroom belonging to another teacher returns HTTP 404 (`not_found`). Unauthenticated requests receive HTTP 401, and student accounts receive HTTP 403.

### 2. Enrolled Student Scoping
- All 5 exports query only students enrolled in the teacher's selected classroom (`student_id__in=classroom.enrollments.values_list("student_id")`). Students enrolled in other classes never leak into any export.

### 3. Formula Injection Protection & Numeric Preservation
- `sanitize_csv_cell()` handles:
  - Dangerous formula prefixes: `=1+1` $\rightarrow$ `'=1+1`, `+cmd...` $\rightarrow$ `'+cmd...`, `@SUM(...)` $\rightarrow$ `'@SUM(...)`.
  - Leading whitespace and control characters before formula characters: `   =1+1` $\rightarrow$ `'   =1+1`, `   -calc` $\rightarrow$ `'   -calc`, `\r\n-cmd` $\rightarrow$ `'\r\n-cmd`, `\v=cmd` $\rightarrow$ `'\v=cmd`, `\f=cmd` $\rightarrow$ `'\f=cmd`.
  - Control characters alone or with commands: `\t=cmd` $\rightarrow$ `'\t=cmd`, `\tnotepad` $\rightarrow$ `'\tnotepad`.
  - Legitimate numbers remain untouched: `-42` $\rightarrow$ `-42`, `-12.5` $\rightarrow$ `-12.5`, `-0.05` $\rightarrow$ `"-0.05"`, `+100` $\rightarrow$ `+100`, `85.5` $\rightarrow$ `85.5`.

### 4. Unicode & Kannada Preservation
- Every export response prepends the UTF-8 BOM (`b"\xef\xbb\xbf"`) and encodes the content in `utf-8`.
- Verified in automated tests that Kannada display names (e.g., `ಆನಂದ್ ಕುಮಾರ್`) and chemical formulas (e.g., `NaCl`, `CuSO4`, `FeSO4`, `(NH4)2CO3`) are completely preserved.

### 5. Learning-Insights Consistency & Minimum Evidence
- `generate_learning_insights_csv()` and `generate_salt_performance_csv()` call `class_learning_insights_for()` directly.
- The 10-answer minimum evidence threshold ($n \ge 10$) and gap score formula $1 - (\text{correct}/\text{total})$ are identical between the dashboard and exports. Topics with $< 10$ answers are clearly tagged `Insufficient (n<10)`.

### 6. Quiz Attempts: Graded vs Practice Separation
- Only submitted attempts (`status="submitted"`) are exported.
- In roster, salt performance, and learning-gap exports, only graded attempts (`is_practice=False`) contribute to scores and gap metrics.
- In the detailed quiz results export, each attempt explicitly indicates its `Attempt Type` ("Graded" or "Practice").

### 7. Missing Lab Data vs Student Mistakes
- Practical mistakes are evaluated strictly from verified tokens (`token_valid=True, no_lab_data=False`).
- Redemptions with `no_lab_data=True` are counted separately in `Missing Lab Data` and are never misclassified as procedural mistakes.

### 8. Data Minimization & Security
- Passwords, PINs, authentication tokens, session secrets, HMAC keys, and raw cryptographic token strings are 100% excluded from all exports.

### 9. Audit Logging
- Every download records `AuditLog(action="export_report", detail_json={"classroom": c.id, "report_type": ...})`.
- No student records, personal info, or CSV file contents are logged.

### 10. Edge Cases, Empty Classes & Filenames
- Empty classes produce a valid CSV file with standard headers and 0 data rows (HTTP 200).
- Invalid class IDs return HTTP 404.
- Filenames follow the standardized pattern `virtulab_class_<join_code>_<report_type>.csv` with proper quoting in the `Content-Disposition` header.
- Frontend download utility handles HTTP errors, token expiration, blob lifecycle, and dynamic filename extraction.

### 11. Test Execution & Build Verification
- Backend Unit Tests: **53 executed, 53 passed (0 failures, 0 errors)**.
- Lab Pack Suite: **27 executed, 27 passed (0 failures, 0 errors)**.
- Frontend Linter (`oxlint`): **0 errors** across 32 files.
- Frontend Production Build: **Built cleanly in 342ms**.

### 12. Fixes & Defensive Improvements Applied
- Enhanced `sanitize_csv_cell` to include vertical tab (`\v`) and form feed (`\f`) in initial character evaluation, ensuring all leading whitespace and control character vectors before formula triggers are sanitized.
- Added defensive parsing in `generate_practical_records_csv` for `mis` in `token_json` to safely handle non-list representations.
- Expanded automated unit test suite in `test_w1.py` with explicit test cases for `\v`, `\f`, `\r\n-cmd`, `   -calc`, `-0.05`, and chemical formula preservation.
- Preserved all frozen contracts, student features, chemistry bank questions, and dashboard definitions.

---

## 3. CSV Columns for Each Report

1. **Roster (`virtulab_class_<join_code>_roster.csv`)**:
   `Student ID`, `Display Name`, `Enrollment Date`, `Recent Activity Date`, `Practical Redemptions Count`, `Completed Graded Quizzes`, `Average Graded Quiz Score %`, `Total Points`, `Level Name`.
2. **Quiz Results (`virtulab_class_<join_code>_quiz_results.csv`)**:
   `Student ID`, `Display Name`, `Attempt ID`, `Salt Key`, `Salt Name`, `Salt Formula`, `Attempt Type`, `Submission Date`, `Correct Answers`, `Total Questions`, `Score %`, `Duration Seconds`, `Points Awarded`.
3. **Practical Records (`virtulab_class_<join_code>_practical_records.csv`)**:
   `Student ID`, `Display Name`, `Salt Key`, `Salt Formula`, `Salt Name`, `Redemption Date`, `Lab Token Valid`, `Recorded Duration Seconds`, `Recorded Mistakes`, `Missing Lab Data`.
4. **Salt Performance (`virtulab_class_<join_code>_salt_performance.csv`)**:
   `Salt Key`, `Salt Formula`, `Salt Name`, `Cation`, `Anion`, `Active Quiz Students`, `Valid Graded Submissions`, `Average Quiz Score %`, `Correct Answer %`, `Practical Completion Count`, `Missing Lab Data Count`.
5. **Learning Insights (`virtulab_class_<join_code>_learning_insights.csv`)**:
   - *Section 1 (Topics)*: `Topic Tag`, `Topic Name`, `Total Valid Answers`, `Correct Answers`, `Incorrect Answers`, `Accuracy %`, `Learning Gap Score`, `Evidence Status`.
   - *Section 2 (Mistakes)*: `Mistake Identifier`, `Mistake Name`, `Occurrences`, `Affected Students Count`, `Mistake Rate %`, `Affected Salts`.
   - *Section 3 (Students)*: `Student ID`, `Display Name`, `Enrollment Date`, `Evidence Observations`.

---

## 4. Automated Tests & Actual Execution Results

- **Backend Unit Tests**:
  Ran: `.\backend\.venv\Scripts\python.exe backend\manage.py test api`
  - **53 tests executed, 53 passed (0 errors, 0 failures)** in 4.573s.
- **Lab Pack Suite**:
  Ran: `.\backend\.venv\Scripts\python.exe -m unittest discover -s lab_pack`
  - **27 tests executed, 27 passed (0 errors, 0 failures)** in 0.032s.
- **Frontend Linter (`oxlint`)**:
  Ran: `npm.cmd run lint`
  - **0 errors** across all 32 files.
- **Frontend Production Build**:
  Ran: `npm.cmd run build`
  - **Vite production bundle built cleanly in 342ms**.

---

## 5. Review Conclusion & Next Steps
Phase 7 has passed all 12 review checkpoints. No regressions were introduced into student or teacher features.
Awaiting user approval before proceeding to Phase 8.
