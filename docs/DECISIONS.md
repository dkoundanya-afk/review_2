# docs/DECISIONS.md — VirtuLab Portal Decision Log

This file records every significant technical decision and the reason for it.
A different model or developer reading this later should understand *why*, not
just *what*.

| # | Decision | Chosen | Alternatives considered | Reason |
|---|---|---|---|---|
| D1 | Backend framework | Django 6.1.2 + DRF 3.18.3 | Flask | Spec §3.2 preference; auth, ORM, admin come free |
| D2 | Python requirement | 3.14 | 3.12, 3.13 | User's installed version; both Django 6.1.2 and DRF 3.18.3 officially support it |
| D3 | DRF version pinned to 3.18.3 (not 3.16.x) | 3.18.3 | 3.16.1 | 3.18.3 is the first DRF release to officially list Python 3.14 in its trove classifiers |
| D4 | Frontend build tool | Vite 6 | Create React App | CRA is unmaintained; Vite is faster and the spec recommends it |
| D5 | Bootstrap delivery | npm package | CDN | CDN creates an external dependency; npm bundle works offline (spec §6 performance req) |
| D6 | i18n library | react-i18next | Custom | Approved explicitly; wires the i18n catalogue per HARD RULE 7 |
| D7 | question radical field | From each question's own tag only | Copied from salt header | User note 2: "radical comes from its own tag only" |
| D8 | test_type inference | Keyword heuristics → unclassified fallback | Silence / guess | OVERRIDE 3: never silently guess; every unclassified question is listed in the report |
| D9 | Report encoding | UTF-8 to file; cp1252-safe to terminal | Always UTF-8 | Windows PowerShell terminal is cp1252; the report file itself is UTF-8 |
| D10 | SECRET_KEY in settings | `os.environ["SECRET_KEY"]` — raises if missing | Default fallback | HARD RULE 4: secrets only in env vars; a missing key should fail loudly, not silently |
| D11 | TIME_ZONE | Asia/Kolkata (IST) | UTC | Code date-window is calculated in IST per spec §3.5 |
| D12 | Teacher Login UX | Dual-mode tab on /login | Separate /teacher/login | Keeps a single login entrypoint, zero disruption to student bookmarks, clean toggle between PIN and password |
| D13 | Teacher Analytics Scoping | Strict filter via classroom enrollments | Global aggregations with class filters | Guarantees HARD RULE 8 (isolation); students not in teacher's class never leak into analytics |
| D14 | Role-Aware Routing & Guards | Separate TeacherRoute and role checks in ProtectedRoute/PublicOnlyRoute | Single mixed layout | Shields teachers from student /api/progress 403, shields students from teacher management screens, and keeps layouts decoupled |
| D15 | Class Analytics Overview & Scoping | `GET /api/teacher/classes/<id>/overview` using real database queries (`QuizAttempt`, `Redemption`, `Enrollment`) scoped via `_own_class` | Client-side aggregation or mock counters | Guarantees HARD RULE 8 (isolation), zero invented statistics, handles 0-student edge cases cleanly |
| D16 | Lightweight Participation Trend Visualization | Pure CSS/SVG bar chart for 14-day activity | Heavy chart libraries (Chart.js / Recharts) | Adheres to HARD RULE 6 (no heavy dependencies) and spec performance requirements, keeps bundle size small and snappy |
| D17 | Learning Gap Score & Thresholding | `Gap Score = 1 - (correct / total)` with `n >= 10` minimum evidence rule | Silent inference or no threshold | Spec §T-08 compliance; guarantees high-confidence topic gaps and marks small-sample topics as insufficient data |
| D18 | Lab Mistakes Telemetry & Denominators | Frequency and percentage over verified tokens (`token_valid=True, no_lab_data=False`) using 8-mistake enum | Inferring errors without tokens | Spec §3.6; prevents false claims regarding offline lab runs when tokens are absent |
| D19 | CSV Export Encoding & Injection Protection | UTF-8 with BOM (`\xef\xbb\xbf`) + formula sanitization (`'`, while preserving numeric types) | Raw string concatenation / ASCII | Ensures Excel on Windows renders Kannada & Unicode without mojibake; neutralizes DDE/formula injection attacks |


