"""Business rules: rate limiting, audit, redeem, points, badges. No HTTP in here."""
import datetime as dt

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from lab_pack.token_codec import TokenError, parse_token
from lab_pack.verify_code import CodeError, ist_today, normalise_student_id, parse_code, verify_code

from .conf import cfg, level_for
from .errors import ApiError
from .models import (Answer, AuditLog, Badge, InvalidAttempt, Item, PointsLedger, QuizAttempt, Redemption, UserBadge)


# ------------------------------------------------------------------ audit & limits
def audit(actor, action, **detail):
    AuditLog.objects.create(actor=actor if getattr(actor, "pk", None) else None,
                            actor_text=getattr(actor, "username", "")[:60], action=action, detail_json=detail)


def log_invalid(kind, reason, student=None, student_id_text="", code_text="", ip=""):
    InvalidAttempt.objects.create(kind=kind, reason=reason, student=student if getattr(student, "pk", None) else None,
                                  student_id_text=student_id_text[:60], code_text=code_text[:80], ip=ip[:45])


def _window_start():
    return timezone.now() - dt.timedelta(seconds=cfg("rate_limit", "window_seconds", default=600))


def check_rate_limit(kind, student_id_text=None, ip=None, ip_factor=4):
    """Raise ApiError(429) if too many recent failures for this student id or ip."""
    limit = cfg("rate_limit", "max_failures", default=5)
    qs = InvalidAttempt.objects.filter(kind=kind, ts__gte=_window_start())
    over = bool(student_id_text) and qs.filter(student_id_text=student_id_text).count() >= limit
    over = over or (bool(ip) and qs.filter(ip=ip).count() >= limit * ip_factor)
    if over:
        raise ApiError(429, "rate_limited", retry_after=cfg("rate_limit", "window_seconds", default=600))


# --------------------------------------------------------------------------- points
def add_points(student, delta, reason, ref_id):
    """Idempotent: the same (student, reason, ref) can only ever be recorded once."""
    try:
        with transaction.atomic():
            PointsLedger.objects.create(student=student, delta=delta, reason=reason, ref_id=str(ref_id))
        return True
    except IntegrityError:
        return False


def total_points(student) -> int:
    from django.db.models import Sum
    return PointsLedger.objects.filter(student=student).aggregate(s=Sum("delta"))["s"] or 0


# ---------------------------------------------------------------------------- badges
def _graded(student):
    return QuizAttempt.objects.filter(student=student, is_practice=False, status="submitted")


def _rule_met(rule, student) -> bool:
    kind = rule.get("type")
    if kind == "first_redeem":
        return Redemption.objects.filter(student=student).exists()
    if kind == "perfect_score":
        return any(a.total > 0 and a.correct_count == a.total for a in _graded(student))
    if kind == "lab_flawless":
        return any(r.token_valid and (r.token_json or {}).get("att") == 1 and not (r.token_json or {}).get("mis")
                   and not (r.token_json or {}).get("wrong") for r in Redemption.objects.filter(student=student))
    if kind == "all_dynamic_correct":
        need = rule.get("min_dynamic", 1)
        for a in _graded(student):
            dyn = list(a.questions.filter(source="dynamic").prefetch_related("answers"))
            if len(dyn) >= need and all(any(x.is_correct for x in q.answers.all()) for q in dyn):
                return True
        return False
    if kind == "complete_items":
        done = set(_graded(student).values_list("redemption__item__key", flat=True))
        return set(rule.get("items", [])) <= done and bool(rule.get("items"))
    if kind == "complete_experiment":
        keys = set(Item.objects.filter(experiment__key=rule.get("experiment")).values_list("key", flat=True))
        done = set(_graded(student).values_list("redemption__item__key", flat=True))
        return bool(keys) and keys <= done
    if kind == "comeback":
        return any(r.token_valid and (r.token_json or {}).get("passed") and (r.token_json or {}).get("wrong")
                   for r in Redemption.objects.filter(student=student))
    return False


def evaluate_badges(student, ref="") -> list:
    """Award every badge whose rule is now met. Rules live in the database (loaded from badges.json)."""
    have = set(UserBadge.objects.filter(student=student).values_list("badge__key", flat=True))
    new = []
    for badge in Badge.objects.all():
        if badge.key in have or not _rule_met(badge.rule_json, student):
            continue
        try:
            with transaction.atomic():
                UserBadge.objects.create(student=student, badge=badge, ref=str(ref))
            new.append({"key": badge.key, "name": badge.name, "description": badge.description})
        except IntegrityError:
            pass
    return new


# ---------------------------------------------------------------------------- redeem
def _item_maps():
    items = list(Item.objects.all())
    return ({(i.cation, i.anion): i.key for i in items}, {i.key: (i.cation, i.anion) for i in items})


def redemption_payload(r: Redemption, already=False) -> dict:
    return {"redemption_id": r.id, "item": r.item.key, "formula": r.item.formula, "name": r.item.name,
            "cation": r.item.cation, "anion": r.item.anion, "token_valid": r.token_valid,
            "no_lab_data": r.no_lab_data, "token_error": r.token_error or None, "already": already}


def redeem_code(student, raw_code: str, raw_token: str | None, ip: str, today: dt.date | None = None) -> dict:
    """Spec 3.5 / 3.6 / S-03 / S-04. Raises ApiError with a reason code on any rejection."""
    if not settings.HMAC_SECRET:
        raise ApiError(503, "server_not_configured")
    sid = student.username
    check_rate_limit("code", student_id_text=sid, ip=ip)

    def reject(reason, status=400):
        log_invalid("code", reason, student, sid, str(raw_code), ip)
        audit(student, "redeem_rejected", reason=reason)
        raise ApiError(status, reason)

    try:
        parsed = parse_code(str(raw_code or ""))
    except CodeError:
        reject("bad_format")
    canonical = parsed.canonical

    existing = Redemption.objects.select_related("item").filter(code=canonical).first()
    if existing:
        if existing.student_id == student.id:
            return redemption_payload(existing, already=True)          # double click / retry: idempotent
        reject("already_used")

    pair_to_item, item_pairs = _item_maps()
    today = today or ist_today()
    window = cfg("code", "date_window_days", default=30)
    drift = cfg("code", "clock_drift_days", default=1)
    res = verify_code(canonical, sid, settings.HMAC_SECRET, today, window, drift, pair_to_item=pair_to_item)
    if not res.ok:
        if res.reason == "checksum_mismatch":
            wide = verify_code(canonical, sid, settings.HMAC_SECRET, today, 3650, drift, pair_to_item=pair_to_item)
            reject("expired" if wide.ok else "invalid_code")             # "not yours" cannot be told apart from forged
        reject("bad_format" if res.reason in ("unknown_pair", "bad_format") else res.reason)

    item = Item.objects.get(key=res.item_id)
    if Redemption.objects.filter(student=student, item=item).exists():
        reject("item_already_unlocked")

    token_valid, token_error, token_json = False, "", None
    if raw_token and str(raw_token).strip():
        try:
            token_json = parse_token(str(raw_token), settings.HMAC_SECRET, expected_student=sid,
                                     expected_code=canonical, items=item_pairs)
            token_valid = True
        except TokenError as e:
            token_error = e.reason
            log_invalid("token", e.reason, student, sid, canonical, ip)   # E5: ignored, but logged
    usable = token_valid and len((token_json or {}).get("tests", [])) >= 1
    try:
        with transaction.atomic():
            r = Redemption.objects.create(student=student, item=item, code=canonical, code_issue_date=res.issue_date,
                                          token_valid=token_valid, token_error=token_error,
                                          token_json=token_json if token_valid else None, no_lab_data=not usable)
    except IntegrityError:                                               # two requests raced: return the winner
        r = Redemption.objects.select_related("item").get(code=canonical)
        if r.student_id != student.id:
            reject("already_used")
        return redemption_payload(r, already=True)
    audit(student, "redeem_ok", item=item.key, token_valid=token_valid, no_lab_data=r.no_lab_data)
    out = redemption_payload(r)
    out["new_badges"] = evaluate_badges(student, ref=r.id)
    return out


# --------------------------------------------------------------------------- progress
def progress_for(student) -> dict:
    items = list(Item.objects.select_related("experiment").all())
    reds = {r.item_id: r for r in Redemption.objects.filter(student=student)}
    graded = {a.redemption_id: a for a in _graded(student)}
    open_attempts = {a.redemption_id: a for a in QuizAttempt.objects.filter(student=student, is_practice=False,
                                                                             status="in_progress")}
    grid = []
    for it in items:
        r = reds.get(it.id)
        status, score, attempt_id = "locked", None, None
        if r:
            status = "unlocked"
            a = graded.get(r.id)
            if a:
                status, score = "completed", {"correct": a.correct_count, "total": a.total,
                                              "percent": round(100 * a.correct_count / a.total) if a.total else 0}
                attempt_id = a.id
            elif r.id in open_attempts:
                attempt_id = open_attempts[r.id].id
        grid.append({"item": it.key, "formula": it.formula, "name": it.name, "cation": it.cation, "anion": it.anion,
                     "group": it.group_tag, "status": status, "score": score,
                     "redemption_id": r.id if r else None, "attempt_id": attempt_id,
                     "no_lab_data": bool(r and r.no_lab_data)})
    pts = total_points(student)
    earned = {ub.badge.key: ub.earned_at for ub in UserBadge.objects.filter(student=student).select_related("badge")}
    badges = [{"key": b.key, "name": b.name, "description": b.description, "earned": b.key in earned,
               "earned_at": earned.get(b.key)} for b in Badge.objects.all()]
    return {"points": pts, "level": level_for(pts), "items": grid, "badges": badges,
            "completed": sum(1 for g in grid if g["status"] == "completed"), "total_items": len(grid)}


# ----------------------------------------------------------------------- analytics
def class_overview_for(classroom) -> dict:
    """Computes real class analytics KPIs, per-salt metrics, participation trends, and inactive student list."""
    enrollments = list(classroom.enrollments.select_related("student", "student__profile").order_by("student__username"))
    total_students = len(enrollments)
    student_ids = [e.student_id for e in enrollments]

    cutoff_7d = timezone.now() - dt.timedelta(days=7)

    all_redemptions = Redemption.objects.filter(student_id__in=student_ids)
    all_graded_attempts = QuizAttempt.objects.filter(student_id__in=student_ids, is_practice=False, status="submitted")

    # Active in last 7 days (distinct students)
    active_redemp_ids = set(all_redemptions.filter(redeemed_at__gte=cutoff_7d).values_list("student_id", flat=True))
    active_attempt_ids = set(QuizAttempt.objects.filter(student_id__in=student_ids, started_at__gte=cutoff_7d).values_list("student_id", flat=True))
    active_students_7d = len(active_redemp_ids | active_attempt_ids)

    # Redemptions stats
    total_redemptions = all_redemptions.count()
    total_valid_redemptions = all_redemptions.filter(token_valid=True).count()
    total_no_lab_data = all_redemptions.filter(no_lab_data=True).count()

    # Quizzes stats
    completed_graded_quizzes = all_graded_attempts.count()
    attempt_scores = [round((a.correct_count / a.total) * 100, 1) for a in all_graded_attempts if a.total > 0]
    avg_quiz_score_percent = round(sum(attempt_scores) / len(attempt_scores), 1) if attempt_scores else None

    # Overall completion and participation
    total_items = Item.objects.count()
    distinct_completed_pairs = all_graded_attempts.values_list("student_id", "redemption__item_id").distinct().count()
    max_possible_completions = total_students * total_items
    overall_completion_percent = round((distinct_completed_pairs / max_possible_completions) * 100, 1) if max_possible_completions > 0 else 0.0
    participation_percent = round((active_students_7d / total_students) * 100, 1) if total_students > 0 else 0.0

    # Per-salt breakdown
    items = list(Item.objects.all().order_by("position", "key"))
    salts_data = []
    for it in items:
        item_reds = all_redemptions.filter(item_id=it.id)
        item_attempts = all_graded_attempts.filter(redemption__item_id=it.id)

        redeemed_count = item_reds.values_list("student_id", flat=True).distinct().count()
        completed_count = item_attempts.values_list("student_id", flat=True).distinct().count()
        completion_percent = round((completed_count / total_students) * 100, 1) if total_students > 0 else 0.0

        scores = [round((a.correct_count / a.total) * 100, 1) for a in item_attempts if a.total > 0]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        durations = [a.duration_ms for a in item_attempts if a.duration_ms is not None]
        avg_duration_sec = round((sum(durations) / len(durations)) / 1000, 1) if durations else None

        no_lab_count = item_reds.filter(no_lab_data=True).count()

        salts_data.append({
            "key": it.key,
            "formula": it.formula,
            "name": it.name,
            "cation": it.cation,
            "anion": it.anion,
            "group_tag": it.group_tag,
            "redeemed_count": redeemed_count,
            "completed_count": completed_count,
            "completion_percent": completion_percent,
            "avg_score_percent": avg_score,
            "avg_duration_seconds": avg_duration_sec,
            "no_lab_data_count": no_lab_count,
        })

    # Participation trend (last 14 days)
    today = timezone.now().date()
    trend = []
    redemp_dates = list(all_redemptions.values_list("student_id", "redeemed_at"))
    attempt_dates = [(sid, sub or start) for sid, sub, start in all_graded_attempts.values_list("student_id", "submitted_at", "started_at")]

    for offset in range(13, -1, -1):
        target_day = today - dt.timedelta(days=offset)
        day_redemps = [sid for sid, ts in redemp_dates if ts and ts.date() == target_day]
        day_quizzes = [sid for sid, ts in attempt_dates if ts and ts.date() == target_day]
        active_day_students = set(day_redemps) | set(day_quizzes)
        trend.append({
            "date": target_day.isoformat(),
            "redemptions": len(day_redemps),
            "quizzes": len(day_quizzes),
            "active_students": len(active_day_students),
        })

    # Inactive students list (enrolled with no redemptions and no attempts)
    students_with_any_activity = set(all_redemptions.values_list("student_id", flat=True)) | set(all_graded_attempts.values_list("student_id", flat=True))
    inactive_students = [
        {
            "student_id": e.student.username,
            "display_name": e.student.profile.display_name or e.student.username,
            "joined_at": e.joined_at.isoformat(),
        }
        for e in enrollments
        if e.student_id not in students_with_any_activity
    ]

    return {
        "class": {
            "id": classroom.id,
            "name": classroom.name,
            "grade": classroom.grade,
            "section": classroom.section,
            "join_code": classroom.join_code,
            "join_enabled": classroom.join_enabled,
            "active": classroom.active,
            "leaderboard": classroom.leaderboard,
        },
        "kpis": {
            "total_students": total_students,
            "active_students_7d": active_students_7d,
            "total_redemptions": total_redemptions,
            "total_valid_redemptions": total_valid_redemptions,
            "completed_graded_quizzes": completed_graded_quizzes,
            "avg_quiz_score_percent": avg_quiz_score_percent,
            "overall_completion_percent": overall_completion_percent,
            "participation_percent": participation_percent,
            "no_lab_data_count": total_no_lab_data,
        },
        "salts": salts_data,
        "trend": trend,
        "inactive_students": inactive_students,
        "visibility_notice": "The portal only tracks activity from redeemed completion codes and lab result tokens.",
    }


def class_learning_insights_for(classroom) -> dict:
    """Computes evidence-based learning gaps, salt performance, lab mistake rates, and support indicators."""
    enrollments = list(classroom.enrollments.select_related("student", "student__profile").order_by("student__username"))
    student_ids = [e.student_id for e in enrollments]
    total_students = len(enrollments)

    # 1. Graded quiz attempts and answers for enrolled students
    graded_attempts = QuizAttempt.objects.filter(student_id__in=student_ids, is_practice=False, status="submitted")
    answers = list(Answer.objects.filter(attempt__in=graded_attempts).select_related("question", "attempt"))

    # Group answers by topic (question.test_type)
    topic_stats = {}
    for a in answers:
        tt = a.question.test_type or "unclassified"
        if tt not in topic_stats:
            topic_stats[tt] = {"total": 0, "correct": 0, "incorrect": 0, "students": set()}
        topic_stats[tt]["total"] += 1
        if a.is_correct:
            topic_stats[tt]["correct"] += 1
        else:
            topic_stats[tt]["incorrect"] += 1
        topic_stats[tt]["students"].add(a.attempt.student_id)

    TOPIC_LABELS = {
        "dilute_acid": "Dilute Acid Action",
        "conc_acid": "Concentrated Acid Action",
        "flame": "Flame Test",
        "dry_heating": "Dry Heating Test",
        "group_reagent": "Group Reagent & Cation Separation",
        "wet_precipitation": "Wet Precipitation Test",
        "confirmatory": "Confirmatory Test",
        "gas_test": "Gas Evolution & Identification",
        "solubility": "Solubility & Physical Properties",
        "error_check": "Experimental Precautions & Errors",
        "salt_identification": "Systematic Salt Identification",
        "unclassified": "General Chemistry & Theory",
    }

    topics_list = []
    MIN_EVIDENCE_ANSWERS = 10
    for tt, stat in topic_stats.items():
        tot = stat["total"]
        cor = stat["correct"]
        incor = stat["incorrect"]
        cor_pct = round((cor / tot) * 100, 1) if tot > 0 else 0.0
        gap_score = round(1.0 - (cor / tot), 3) if tot > 0 else 0.0
        suff = tot >= MIN_EVIDENCE_ANSWERS
        topics_list.append({
            "topic": tt,
            "label": TOPIC_LABELS.get(tt, tt.replace("_", " ").title()),
            "total_answers": tot,
            "correct_answers": cor,
            "incorrect_answers": incor,
            "correct_percent": cor_pct,
            "gap_score": gap_score,
            "sufficient_evidence": suff,
            "students_count": len(stat["students"]),
        })

    # Sort topics: first those with sufficient evidence by gap_score desc, then by total_answers desc
    topics_list.sort(key=lambda x: (x["sufficient_evidence"], x["gap_score"]), reverse=True)

    # 2. Salt-wise performance
    all_redemptions = Redemption.objects.filter(student_id__in=student_ids)
    items = list(Item.objects.all().order_by("position", "key"))
    salts_data = []
    for it in items:
        item_reds = all_redemptions.filter(item_id=it.id)
        item_attempts = graded_attempts.filter(redemption__item_id=it.id)

        stu_with_quiz = item_attempts.values_list("student_id", flat=True).distinct().count()
        valid_submissions = item_attempts.count()

        scores = [round((a.correct_count / a.total) * 100, 1) for a in item_attempts if a.total > 0]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        sum_correct = sum(a.correct_count for a in item_attempts)
        sum_total = sum(a.total for a in item_attempts)
        correct_pct = round((sum_correct / sum_total) * 100, 1) if sum_total > 0 else None

        practical_completions = item_reds.filter(token_valid=True).values_list("student_id", flat=True).distinct().count()
        no_lab_count = item_reds.filter(no_lab_data=True).count()

        salts_data.append({
            "key": it.key,
            "formula": it.formula,
            "name": it.name,
            "cation": it.cation,
            "anion": it.anion,
            "group_tag": it.group_tag,
            "students_with_quiz": stu_with_quiz,
            "valid_graded_submissions": valid_submissions,
            "avg_quiz_score_percent": avg_score,
            "correct_answer_percent": correct_pct,
            "practical_completed_students": practical_completions,
            "no_lab_data_count": no_lab_count,
        })

    # 3. Practical mistake analysis (from token_json in valid redemptions)
    valid_tokens = all_redemptions.filter(token_valid=True, no_lab_data=False).select_related("item", "student")
    valid_tokens_count = valid_tokens.count()
    has_telemetry = valid_tokens_count > 0

    from lab_pack.token_codec import MISTAKES
    MISTAKE_LABELS = {
        "order_wrong": "Wrong Test Order",
        "reagent_excess": "Excess Reagent Added",
        "skipped_flame": "Skipped Flame Test",
        "skipped_confirmatory": "Skipped Confirmatory Test",
        "skipped_dissolve": "Skipped Insoluble Salt Dissolution",
        "repeated_same_test": "Repeated Identical Test",
        "wrong_reagent_for_goal": "Wrong Reagent For Test Goal",
        "wrong_submission": "Incorrect Radical Identified",
    }

    mistakes_data = []
    for mis_key in MISTAKES:
        occurrences = 0
        affected_stus = set()
        affected_salts = set()
        for r in valid_tokens:
            tj = r.token_json or {}
            mis_list = tj.get("mis", [])
            if mis_key in mis_list:
                occurrences += 1
                affected_stus.add(r.student_id)
                affected_salts.add(r.item.formula)
        rate_pct = round((occurrences / valid_tokens_count) * 100, 1) if valid_tokens_count > 0 else 0.0
        mistakes_data.append({
            "category": mis_key,
            "label": MISTAKE_LABELS.get(mis_key, mis_key.replace("_", " ").title()),
            "occurrences": occurrences,
            "affected_students_count": len(affected_stus),
            "rate_percent": rate_pct,
            "affected_salts": sorted(list(affected_salts)),
        })

    mistakes_data.sort(key=lambda m: (m["occurrences"], m["affected_students_count"]), reverse=True)

    # 4. Students who may benefit from support
    cutoff_7d = timezone.now() - dt.timedelta(days=7)
    students_support = []

    stu_attempts = {}
    for a in graded_attempts:
        stu_attempts.setdefault(a.student_id, []).append(a)

    stu_redemptions = {}
    for r in all_redemptions:
        stu_redemptions.setdefault(r.student_id, []).append(r)

    stu_topic_answers = {}
    for a in answers:
        tt = a.question.test_type or "unclassified"
        stu_topic_answers.setdefault((a.attempt.student_id, tt), []).append(a)

    for e in enrollments:
        sid = e.student_id
        username = e.student.username
        display_name = e.student.profile.display_name or username
        reasons = []
        indicators = []

        my_att = stu_attempts.get(sid, [])
        my_red = stu_redemptions.get(sid, [])

        # Check 1: Low average score on graded quizzes (at least 2 quizzes attempted and avg < 50%)
        if len(my_att) >= 2:
            scores = [(a.correct_count / a.total) * 100 for a in my_att if a.total > 0]
            if scores:
                avg_s = round(sum(scores) / len(scores), 1)
                if avg_s < 50.0:
                    reasons.append(f"Low average quiz score: {avg_s}% across {len(my_att)} graded quizzes")
                    indicators.append({"type": "low_quiz_score", "avg_score": avg_s, "quizzes": len(my_att)})

        # Check 2: Topic struggle (>= 4 answers in a topic with <= 25% accuracy)
        for (st_id, tt), t_answers in stu_topic_answers.items():
            if st_id == sid and len(t_answers) >= 4:
                cor_cnt = sum(1 for ans in t_answers if ans.is_correct)
                tot_cnt = len(t_answers)
                acc = round((cor_cnt / tot_cnt) * 100, 1)
                if acc <= 25.0:
                    topic_name = TOPIC_LABELS.get(tt, tt)
                    reasons.append(f"Topic difficulty in {topic_name}: {cor_cnt}/{tot_cnt} correct ({acc}%)")
                    indicators.append({"type": "topic_struggle", "topic": tt, "accuracy": acc})

        # Check 3: Repeated practical mistakes in valid tokens (>= 2 recorded mistakes)
        my_mistakes = []
        for r in my_red:
            if r.token_valid and not r.no_lab_data and r.token_json:
                for m in r.token_json.get("mis", []):
                    my_mistakes.append(MISTAKE_LABELS.get(m, m))
        if len(my_mistakes) >= 2:
            reasons.append(f"Recorded {len(my_mistakes)} lab run mistakes ({', '.join(my_mistakes[:3])})")
            indicators.append({"type": "practical_mistakes", "count": len(my_mistakes), "mistakes": my_mistakes})

        # Check 4: Inactivity in the last 7 days (enrolled >= 7 days ago, but 0 activity in last 7 days)
        enrolled_days_ago = (timezone.now() - e.joined_at).days
        if enrolled_days_ago >= 7:
            recent_red = any(r.redeemed_at >= cutoff_7d for r in my_red)
            recent_att = any(a.started_at >= cutoff_7d for a in my_att)
            if not recent_red and not recent_att:
                reasons.append(f"No practical or quiz activity in the last 7 days (enrolled {e.joined_at.strftime('%Y-%m-%d')})")
                indicators.append({"type": "inactive_7d", "joined_at": e.joined_at.isoformat()})

        if reasons:
            students_support.append({
                "student_id": username,
                "display_name": display_name,
                "joined_at": e.joined_at.isoformat(),
                "reasons": reasons,
                "indicators": indicators,
            })

    gaps_count = sum(1 for t in topics_list if t["sufficient_evidence"] and t["gap_score"] >= 0.4)
    salts_with_data = sum(1 for s in salts_data if s["valid_graded_submissions"] > 0)
    total_mistakes = sum(m["occurrences"] for m in mistakes_data)

    return {
        "class": {
            "id": classroom.id,
            "name": classroom.name,
            "grade": classroom.grade,
            "section": classroom.section,
            "join_code": classroom.join_code,
            "active": classroom.active,
        },
        "summary": {
            "total_students": total_students,
            "total_answers_recorded": len(answers),
            "topics_with_gaps_count": gaps_count,
            "salts_with_data_count": salts_with_data,
            "has_telemetry": has_telemetry,
            "valid_tokens_count": valid_tokens_count,
            "total_mistakes_recorded": total_mistakes,
            "students_needing_support_count": len(students_support),
            "min_evidence_threshold": MIN_EVIDENCE_ANSWERS,
        },
        "topics": topics_list,
        "salts": salts_data,
        "practical_mistakes": {
            "has_telemetry": has_telemetry,
            "denominator_tokens": valid_tokens_count,
            "categories": mistakes_data,
            "notice": None if has_telemetry else "No lab result tokens with telemetry have been submitted yet. Practical mistakes will populate when students redeem valid lab tokens.",
        },
        "students_needing_support": students_support,
        "notice": "All insights are computed strictly from real graded quiz answers and verified lab result tokens. Topics require at least 10 valid responses to qualify as confirmed learning gaps.",
    }

