"""
backend/api/services_export.py
Phase 7: CSV export generation and data sanitization for teacher reports.
Includes:
- Formula injection protection (sanitizes =, +, -, @ while preserving real numbers)
- Class roster export
- Student quiz results export
- Student practical records export
- 12-Salt class performance export
- Learning gaps and insights export
- UTF-8 with BOM support for seamless Kannada & English spreadsheet compatibility
"""
import csv
import io

from api.models import Item, QuizAttempt, Redemption
from api.services import class_learning_insights_for, level_for, total_points


def sanitize_csv_cell(value):
    """
    Sanitizes untrusted text fields to prevent CSV formula injection (DDE / CSV injection).
    If a string starts with =, +, -, @, \\t, \\r, \\n (directly or after stripping leading whitespace/control chars),
    prepend a single quote (') to force spreadsheet software to treat it as a literal string.
    Leaves real numeric values (int, float, and strings representing valid numbers) untouched.
    """
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return value
    val_str = str(value)
    if not val_str:
        return ""
    stripped = val_str.lstrip(" \t\r\n\v\f")
    is_formula_candidate = (
        val_str[0] in ("=", "+", "-", "@", "\t", "\r", "\n", "\v", "\f")
        or (bool(stripped) and stripped[0] in ("=", "+", "-", "@"))
    )
    if is_formula_candidate:
        try:
            float(stripped)
            return val_str
        except ValueError:
            return f"'{val_str}"
    return val_str


def generate_roster_csv(classroom) -> str:
    """Exports class roster with enrollment, activity, quizzes, practicals, points, and level."""
    enrollments = list(classroom.enrollments.select_related("student", "student__profile").order_by("student__username"))
    student_ids = [e.student_id for e in enrollments]

    all_redemptions = Redemption.objects.filter(student_id__in=student_ids)
    all_graded_attempts = QuizAttempt.objects.filter(student_id__in=student_ids, is_practice=False, status="submitted")

    stu_redemptions = {}
    for r in all_redemptions:
        stu_redemptions.setdefault(r.student_id, []).append(r)

    stu_attempts = {}
    for a in all_graded_attempts:
        stu_attempts.setdefault(a.student_id, []).append(a)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    headers = [
        "Student ID",
        "Display Name",
        "Enrollment Date",
        "Recent Activity Date",
        "Practical Redemptions Count",
        "Completed Graded Quizzes",
        "Average Graded Quiz Score %",
        "Total Points",
        "Level Name",
    ]
    writer.writerow(headers)

    for e in enrollments:
        s = e.student
        reds = stu_redemptions.get(s.id, [])
        atts = stu_attempts.get(s.id, [])

        activity_dates = [r.redeemed_at for r in reds if r.redeemed_at] + [
            a.submitted_at for a in atts if a.submitted_at
        ]
        recent_date_str = max(activity_dates).strftime("%Y-%m-%d %H:%M:%S") if activity_dates else "None"

        scores = [(a.correct_count / a.total) * 100 for a in atts if a.total > 0]
        avg_score_str = f"{round(sum(scores) / len(scores), 1)}" if scores else "None"

        pts = total_points(s)
        lvl = level_for(pts)["name"]

        row = [
            sanitize_csv_cell(s.username),
            sanitize_csv_cell(s.profile.display_name or s.username),
            sanitize_csv_cell(e.joined_at.strftime("%Y-%m-%d %H:%M:%S")),
            sanitize_csv_cell(recent_date_str),
            len(reds),
            len(atts),
            avg_score_str,
            pts,
            sanitize_csv_cell(lvl),
        ]
        writer.writerow(row)

    return output.getvalue()


def generate_quiz_results_csv(classroom) -> str:
    """Exports all submitted quiz attempts for enrolled students with scores, durations, and points."""
    student_ids = list(classroom.enrollments.values_list("student_id", flat=True))
    attempts = (
        QuizAttempt.objects.filter(student_id__in=student_ids, status="submitted")
        .select_related("student", "student__profile", "redemption__item")
        .order_by("-submitted_at")
    )

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    headers = [
        "Student ID",
        "Display Name",
        "Attempt ID",
        "Salt Key",
        "Salt Name",
        "Salt Formula",
        "Attempt Type",
        "Submission Date",
        "Correct Answers",
        "Total Questions",
        "Score %",
        "Duration Seconds",
        "Points Awarded",
    ]
    writer.writerow(headers)

    for a in attempts:
        item = a.redemption.item
        score_pct = round((a.correct_count / a.total) * 100, 1) if a.total > 0 else 0.0
        dur_sec = round(a.duration_ms / 1000, 1) if a.duration_ms is not None else "None"
        sub_date = a.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if a.submitted_at else "None"

        row = [
            sanitize_csv_cell(a.student.username),
            sanitize_csv_cell(a.student.profile.display_name or a.student.username),
            a.id,
            sanitize_csv_cell(item.key),
            sanitize_csv_cell(item.name),
            sanitize_csv_cell(item.formula),
            "Practice" if a.is_practice else "Graded",
            sanitize_csv_cell(sub_date),
            a.correct_count,
            a.total,
            score_pct,
            dur_sec,
            a.points_awarded,
        ]
        writer.writerow(row)

    return output.getvalue()


def generate_practical_records_csv(classroom) -> str:
    """Exports practical redemption records, token validity, mistake categories, and durations."""
    student_ids = list(classroom.enrollments.values_list("student_id", flat=True))
    redemptions = (
        Redemption.objects.filter(student_id__in=student_ids)
        .select_related("student", "student__profile", "item")
        .order_by("-redeemed_at")
    )

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    headers = [
        "Student ID",
        "Display Name",
        "Salt Key",
        "Salt Formula",
        "Salt Name",
        "Redemption Date",
        "Lab Token Valid",
        "Recorded Duration Seconds",
        "Recorded Mistakes",
        "Missing Lab Data",
    ]
    writer.writerow(headers)

    for r in redemptions:
        tj = r.token_json or {}
        dur_s = tj.get("dur_s")
        dur_str = f"{dur_s}" if dur_s is not None else "None"
        mis = tj.get("mis", [])
        mis_str = ", ".join(mis) if isinstance(mis, list) and mis else str(mis) if mis else "None"

        row = [
            sanitize_csv_cell(r.student.username),
            sanitize_csv_cell(r.student.profile.display_name or r.student.username),
            sanitize_csv_cell(r.item.key),
            sanitize_csv_cell(r.item.formula),
            sanitize_csv_cell(r.item.name),
            sanitize_csv_cell(r.redeemed_at.strftime("%Y-%m-%d %H:%M:%S")),
            "Yes" if r.token_valid else "No",
            sanitize_csv_cell(dur_str),
            sanitize_csv_cell(mis_str),
            "Yes" if r.no_lab_data else "No",
        ]
        writer.writerow(row)

    return output.getvalue()


def generate_salt_performance_csv(classroom) -> str:
    """Exports 12-salt performance metrics matching existing class dashboard definitions."""
    insights = class_learning_insights_for(classroom)
    salts = insights["salts"]

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    headers = [
        "Salt Key",
        "Salt Formula",
        "Salt Name",
        "Cation",
        "Anion",
        "Active Quiz Students",
        "Valid Graded Submissions",
        "Average Quiz Score %",
        "Correct Answer %",
        "Practical Completion Count",
        "Missing Lab Data Count",
    ]
    writer.writerow(headers)

    for s in salts:
        avg_score_str = f"{s['avg_quiz_score_percent']}" if s["avg_quiz_score_percent"] is not None else "None"
        correct_pct_str = f"{s['correct_answer_percent']}" if s["correct_answer_percent"] is not None else "None"

        row = [
            sanitize_csv_cell(s["key"]),
            sanitize_csv_cell(s["formula"]),
            sanitize_csv_cell(s["name"]),
            sanitize_csv_cell(s["cation"]),
            sanitize_csv_cell(s["anion"]),
            s["students_with_quiz"],
            s["valid_graded_submissions"],
            avg_score_str,
            correct_pct_str,
            s["practical_completed_students"],
            s["no_lab_data_count"],
        ]
        writer.writerow(row)

    return output.getvalue()


def generate_learning_insights_csv(classroom) -> str:
    """Exports learning gaps (topics, practical mistakes, students needing support) in structured CSV sections."""
    data = class_learning_insights_for(classroom)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Section 1: Topics
    writer.writerow(["# SECTION 1: TOPIC-WISE LEARNING GAPS (Minimum Evidence Threshold: 10 Answers)"])
    writer.writerow([
        "Topic Tag",
        "Topic Name",
        "Total Valid Answers",
        "Correct Answers",
        "Incorrect Answers",
        "Accuracy %",
        "Learning Gap Score",
        "Evidence Status",
    ])
    for t in data["topics"]:
        writer.writerow([
            sanitize_csv_cell(t["topic"]),
            sanitize_csv_cell(t["label"]),
            t["total_answers"],
            t["correct_answers"],
            t["incorrect_answers"],
            t["correct_percent"],
            t["gap_score"],
            "Sufficient (n>=10)" if t["sufficient_evidence"] else "Insufficient (n<10)",
        ])

    writer.writerow([])
    # Section 2: Practical Mistakes
    pm = data["practical_mistakes"]
    writer.writerow([f"# SECTION 2: PRACTICAL LAB MISTAKES (Denominator: {pm['denominator_tokens']} Verified Tokens)"])
    writer.writerow([
        "Mistake Identifier",
        "Mistake Name",
        "Occurrences",
        "Affected Students Count",
        "Mistake Rate %",
        "Affected Salts",
    ])
    for m in pm["categories"]:
        writer.writerow([
            sanitize_csv_cell(m["category"]),
            sanitize_csv_cell(m["label"]),
            m["occurrences"],
            m["affected_students_count"],
            m["rate_percent"],
            sanitize_csv_cell(", ".join(m["affected_salts"]) if m["affected_salts"] else "None"),
        ])

    writer.writerow([])
    # Section 3: Students Needing Support
    writer.writerow(["# SECTION 3: STUDENTS WHO MAY BENEFIT FROM SUPPORT"])
    writer.writerow([
        "Student ID",
        "Display Name",
        "Enrollment Date",
        "Evidence Observations",
    ])
    for st in data["students_needing_support"]:
        writer.writerow([
            sanitize_csv_cell(st["student_id"]),
            sanitize_csv_cell(st["display_name"]),
            sanitize_csv_cell(st["joined_at"]),
            sanitize_csv_cell(" | ".join(st["reasons"])),
        ])

    return output.getvalue()
