"""W2 quiz engine (spec A3/A4): build, freeze, autosave, grade, points, result. No HTTP in here."""
import hashlib
import json
import random
from functools import lru_cache

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .conf import cfg, level_for
from .errors import ApiError
from .models import Answer, BankQuestion, PointsLedger, QuizAttempt, QuizQuestion, Redemption, UserBadge
from .services import add_points, audit, evaluate_badges

RADICAL = {"NA": "Na+", "NH4": "NH4+", "CU": "Cu2+", "FE2": "Fe2+", "FE3": "Fe3+", "AL": "Al3+", "ZN": "Zn2+",
           "BA": "Ba2+", "CA": "Ca2+", "MG": "Mg2+", "PB": "Pb2+", "CL": "Cl-", "SO4": "SO4 2-", "CO3": "CO3 2-",
           "NO3": "NO3-"}
POINT_ORDER = ["correct_bank_easy", "correct_bank_medium", "correct_bank_hard", "correct_dynamic",
               "quiz_completion", "lab_flawless_bonus"]


@lru_cache(maxsize=1)
def salt_data() -> dict:
    p = settings.REPO_ROOT / "virtulab_data" / "salt_data.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _rng(seed: str) -> random.Random:
    return random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16))


# ------------------------------------------------------------------ dynamic questions (Appendix C)
def _make(rng, template, test_type, question, correct, distractors, explanation=""):
    pool = sorted({d for d in distractors if d and d != correct})
    if len(pool) < 3:
        return None
    options = [correct] + rng.sample(pool, 3)
    rng.shuffle(options)
    return {"template": template, "test_type": test_type, "question": question, "options": options,
            "correct_answer": correct, "explanation": explanation}


def _tested(tok):
    seen = []
    for t in tok.get("tests", []):
        if t["r"] not in seen:
            seen.append(t["r"])
    return seen


def dynamic_candidates(item, tok: dict, rng) -> dict:
    """Return {template_id: [question, ...]}. Templates whose data is missing are skipped (DQ-04, DQ-07: no data yet)."""
    D = salt_data()
    if not D:
        return {}
    ions, out = D["ions"], {}
    cat, an = item.cation, item.anion

    def add(q):
        if q:
            out.setdefault(q["template"], []).append(q)

    # DQ-01 observation recall
    col = ions.get(cat, {}).get("flame")
    if tok.get("flame") and col:
        add(_make(rng, "DQ-01", "flame", "In your experiment you did a flame test on your sample. What colour was the flame?",
                  col, D["flame_colours"]))
    for r in _tested(tok):
        spec = D["reagents"].get(r)
        o = spec and spec["outcomes"].get(cat if spec["applies_to"] == "cation" else an)
        if not o:
            continue
        others = [v["obs"] for v in spec["outcomes"].values()] + D["generic_observations"]
        add(_make(rng, "DQ-01", r, f"In your experiment you added {spec['label']} to your sample. What did you observe?",
                  o["obs"], others))
        # DQ-02 inference: only when this observation belongs to exactly one ion in the data
        ion = cat if spec["applies_to"] == "cation" else an
        if sum(1 for v in spec["outcomes"].values() if v["obs"] == o["obs"]) == 1:
            same_type = [v["label"] for k, v in ions.items() if v["type"] == spec["applies_to"] and k != ion]
            add(_make(rng, "DQ-02", r, f"You observed: {o['obs']}. Which ion does this support?",
                      ions[ion]["label"], same_type))
        # DQ-03 excess behaviour
        if o.get("excess"):
            texts = [v["excess"] for v in spec["outcomes"].values() if v.get("excess")] + D["excess_distractors"]
            add(_make(rng, "DQ-03", r, f"What happens when {spec['label']} is added in excess to your sample?",
                      o["excess"], texts))
    mis = set(tok.get("mis", []))
    # DQ-05 skipped test
    if "skipped_flame" in mis and col:
        add(_make(rng, "DQ-05", "flame", f"Which test would have helped confirm the {ions[cat]['label']} ion in your sample?",
                  "Flame test", D["tests_not_valid"]))
    elif "skipped_confirmatory" in mis and any(cat in s["outcomes"] for s in D["reagents"].values() if s["applies_to"] == "cation" and s["label"].startswith("sodium")):
        add(_make(rng, "DQ-05", "confirmatory", f"Which test would have helped confirm the {ions[cat]['label']} ion in your sample?",
                  D["confirm_naoh_text"], D["tests_not_valid"]))
    # DQ-06 gas identification
    for g in tok.get("gas", []):
        gd = D["gases"].get(g)
        if gd:
            add(_make(rng, "DQ-06", "gas_test", f"The gas you detected {gd['detect']}. Which gas is it?",
                      gd["name"], [v["name"] for v in D["gases"].values()]))
    # DQ-08 handling
    if "skipped_dissolve" in mis or item.key in D.get("insoluble_items", []):
        h = D["handling"]
        add(_make(rng, "DQ-08", "solubility", f"Why must {item.name.lower()} be dissolved in dilute acid before the cation tests?",
                  h["correct"], h["wrong"]))
    return out


def pick_dynamic(cands: dict, rng, want: int) -> list:
    """Spread across templates: take one from each template in turn."""
    groups = {t: list(qs) for t, qs in sorted(cands.items())}
    for qs in groups.values():
        rng.shuffle(qs)
    order = sorted(groups)
    rng.shuffle(order)
    picked = []
    while len(picked) < want and any(groups.values()):
        for t in order:
            if groups[t] and len(picked) < want:
                picked.append(groups[t].pop(0))
    return picked


# ------------------------------------------------------------------------------------ bank sampler
def _split_counts(n: int, mix: dict) -> dict:
    raw = {k: n * v for k, v in mix.items()}
    out = {k: int(v) for k, v in raw.items()}
    for k in sorted(raw, key=lambda k: raw[k] - out[k], reverse=True)[: n - sum(out.values())]:
        out[k] += 1
    return out


def sample_bank(item, student, n: int, rng) -> list:
    q = Q(item_key=item.key)
    for ion in (RADICAL.get(item.cation), RADICAL.get(item.anion)):
        if ion:
            q |= Q(radical=ion)
    pool = list(BankQuestion.objects.filter(q, active=True, lang="en").order_by("id"))
    seen = set(Answer.objects.filter(attempt__student=student, question__bank_question__isnull=False)
               .values_list("question__bank_question_id", flat=True))
    fresh = [b for b in pool if b.id not in seen]
    chosen = []
    for diff, k in _split_counts(n, cfg("quiz", "difficulty_mix", default={"easy": .4, "medium": .4, "hard": .2})).items():
        for source in (fresh, [b for b in pool if b.id in seen]):
            avail = [b for b in source if b.difficulty == diff and b not in chosen]
            take = rng.sample(avail, min(k - sum(1 for c in chosen if c.difficulty == diff), len(avail)))
            chosen += take
    for source in (fresh, pool):                                   # top up if a difficulty bucket ran short
        rest = [b for b in source if b not in chosen]
        chosen += rng.sample(rest, min(n - len(chosen), len(rest)))
    return chosen[:n]


# ------------------------------------------------------------------------------------------ start
def start_attempt(student, redemption_id, practice=False) -> QuizAttempt:
    red = Redemption.objects.select_related("item").filter(id=redemption_id, student=student).first() \
        if str(redemption_id).isdigit() else None
    if red is None:
        raise ApiError(404, "not_found")
    graded = QuizAttempt.objects.filter(redemption=red, is_practice=False).first()
    if not practice and graded:
        if graded.status == "in_progress":
            return graded
        raise ApiError(409, "already_graded", attempt_id=graded.id)
    if practice:
        if not graded or graded.status != "submitted":
            raise ApiError(409, "practice_after_graded")
        open_p = QuizAttempt.objects.filter(redemption=red, is_practice=True, status="in_progress").first()
        if open_p:
            return open_p
    n_prev = QuizAttempt.objects.filter(redemption=red, is_practice=True).count()
    seed = hashlib.sha256(f"{red.code}:{'p%d' % n_prev if practice else 'g'}".encode()).hexdigest()
    rng = _rng(seed)
    length = cfg("quiz", "length", default=10)
    want_dyn = length - round(length * cfg("quiz", "bank_share", default=0.5))
    tok = red.token_json if (red.token_valid and not red.no_lab_data) else None
    dyn = pick_dynamic(dynamic_candidates(red.item, tok, rng), rng, want_dyn) if tok else []
    bank = sample_bank(red.item, student, length - len(dyn), rng)
    plan = [("dynamic", d) for d in dyn] + [("bank", b) for b in bank]
    rng.shuffle(plan)
    try:
        with transaction.atomic():
            att = QuizAttempt.objects.create(
                student=student, redemption=red, is_practice=practice, seed=seed[:64],
                no_lab_data=tok is None, partial_dynamic=bool(tok) and len(dyn) < want_dyn, total=len(plan),
                config_json={"length": length, "dynamic": len(dyn), "bank": len(bank)})
            for pos, (src, x) in enumerate(plan, start=1):
                if src == "dynamic":
                    QuizQuestion.objects.create(
                        attempt=att, position=pos, source="dynamic", template=x["template"], test_type=x["test_type"],
                        difficulty="", question_json={"question": x["question"], "options": x["options"],
                                                       "explanation": x["explanation"]},
                        correct_answer=x["correct_answer"])
                else:
                    opts = list(x.options)
                    rng.shuffle(opts)
                    QuizQuestion.objects.create(
                        attempt=att, position=pos, source="bank", bank_question=x, test_type=x.test_type, radical=x.radical,
                        difficulty=x.difficulty, question_json={"question": x.question, "options": opts,
                                                                 "explanation": x.explanation},
                        correct_answer=x.correct_answer)
    except IntegrityError:                                          # double tap raced: return the winner
        att = QuizAttempt.objects.filter(redemption=red, is_practice=False).first()
        if att is None:
            raise
    audit(student, "quiz_start", item=red.item.key, practice=practice)
    return att


# -------------------------------------------------------------------------------------- read / save
def quiz_json(att: QuizAttempt) -> dict:
    qs = list(att.questions.order_by("position"))
    answers = {str(a.question_id): a.chosen for a in att.answers.all()}
    it = att.redemption.item
    return {"attempt_id": att.id, "item": it.key, "formula": it.formula, "name": it.name, "status": att.status,
            "is_practice": att.is_practice, "no_lab_data": att.no_lab_data, "partial_dynamic": att.partial_dynamic,
            "questions": [{"id": q.id, "position": q.position, "source": q.source, "template": q.template,
                           "question": q.question_json["question"], "options": q.question_json["options"]} for q in qs],
            "answers": answers}


def save_answers(att: QuizAttempt, items) -> int:
    if att.status != "in_progress":
        raise ApiError(409, "already_submitted")
    if not isinstance(items, list):
        raise ApiError(400, "invalid_answer")
    qmap = {q.id: q for q in att.questions.all()}
    clean = []
    for it in items:
        try:
            qid, chosen = int(it["question_id"]), it["chosen"]
        except (KeyError, TypeError, ValueError):
            raise ApiError(400, "invalid_answer")
        q = qmap.get(qid)
        if q is None or not isinstance(chosen, str) or chosen not in q.question_json["options"]:
            raise ApiError(400, "invalid_answer")
        t = it.get("time_ms")
        t = min(max(int(t), 0), 3_600_000) if isinstance(t, (int, float)) and not isinstance(t, bool) else None
        clean.append((q, chosen, t))
    with transaction.atomic():
        for q, chosen, t in clean:
            Answer.objects.update_or_create(attempt=att, question=q, defaults={"chosen": chosen, "time_ms": t})
    return len(clean)


# ------------------------------------------------------------------------------------------ submit
def _lab_flawless(red) -> bool:
    tj = red.token_json or {}
    return bool(red.token_valid and tj.get("att") == 1 and not tj.get("mis") and not tj.get("wrong"))


def submit_attempt(att: QuizAttempt, items=None) -> None:
    with transaction.atomic():
        att = QuizAttempt.objects.select_for_update().select_related("redemption", "student").get(pk=att.pk)
        if att.status == "submitted":
            return                                               # idempotent: a retry changes nothing
        if items:
            save_answers(att, items)
        correct, counts, total_ms = 0, {}, 0
        for q in att.questions.prefetch_related("answers"):
            a = next(iter(q.answers.all()), None)
            if a is None:
                continue
            a.is_correct = a.chosen == q.correct_answer
            a.save(update_fields=["is_correct", "updated_at"])
            total_ms += a.time_ms or 0
            if a.is_correct:
                correct += 1
                reason = "correct_dynamic" if q.source == "dynamic" else f"correct_bank_{q.difficulty or 'easy'}"
                counts[reason] = counts.get(reason, 0) + 1
        att.correct_count, att.status, att.submitted_at = correct, "submitted", timezone.now()
        att.duration_ms = total_ms or None
        awarded = 0
        if not att.is_practice:
            pts = cfg("points", default={})
            lines = {r: n * pts.get(r, 0) for r, n in counts.items()}
            lines["quiz_completion"] = pts.get("quiz_completion", 0)
            for reason, delta in lines.items():
                if delta and add_points(att.student, delta, reason, att.id):
                    awarded += delta
            if _lab_flawless(att.redemption) and pts.get("lab_flawless_bonus") and \
                    add_points(att.student, pts["lab_flawless_bonus"], "lab_flawless_bonus", f"red{att.redemption_id}"):
                awarded += pts["lab_flawless_bonus"]
        att.points_awarded = awarded
        att.save()
        if not att.is_practice:
            evaluate_badges(att.student, ref=f"a{att.id}")
        audit(att.student, "quiz_submit", attempt=att.id, practice=att.is_practice, correct=correct, total=att.total)


# ------------------------------------------------------------------------------------------ result
def _ledger_total(student, upto=None, exclude_refs=()):
    qs = PointsLedger.objects.filter(student=student)
    if upto:
        qs = qs.filter(created__lte=upto)
    return qs.exclude(ref_id__in=list(exclude_refs)).aggregate(s=Sum("delta"))["s"] or 0


def _insights(red) -> list:
    tj = red.token_json if red.token_valid else None
    if not tj:
        return []
    out = [{"key": f"insight.mis_{m}", "params": {}} for m in tj.get("mis", [])]
    if _lab_flawless(red):
        out.append({"key": "insight.lab_flawless", "params": {}})
    if tj.get("att", 1) > 1:
        out.append({"key": "insight.lab_attempts", "params": {"att": tj["att"]}})
    for w in tj.get("wrong", []):
        out.append({"key": "insight.wrong_guess", "params": {"cat": w.get("cat"), "an": w.get("an")}})
    return out


def build_result(att: QuizAttempt) -> dict:
    if att.status != "submitted":
        raise ApiError(409, "not_submitted")
    red = att.redemption
    review, weak = [], {}
    for q in att.questions.order_by("position").prefetch_related("answers"):
        a = next(iter(q.answers.all()), None)
        ok = bool(a and a.is_correct)
        review.append({"position": q.position, "source": q.source, "template": q.template,
                       "question": q.question_json["question"], "options": q.question_json["options"],
                       "chosen": a.chosen if a else None, "correct_answer": q.correct_answer, "is_correct": ok,
                       "explanation": q.question_json.get("explanation", "")})
        for kind, tag in (("test_type", q.test_type), ("radical", q.radical)):
            if tag and tag != "unclassified":
                w = weak.setdefault((kind, tag), [0, 0])
                w[1] += 1
                w[0] += 0 if ok else 1
    weak_topics = sorted(({"kind": k, "tag": t, "wrong": w, "total": n} for (k, t), (w, n) in weak.items() if w),
                         key=lambda x: (-x["wrong"], x["tag"]))[:5]
    pct = round(100 * att.correct_count / att.total) if att.total else 0
    lines = []
    if not att.is_practice:
        refs = {str(att.id): None, f"red{red.id}": None}
        rows = {r.reason: r.delta for r in PointsLedger.objects.filter(student=att.student, ref_id__in=list(refs))}
        lines = [{"reason": r, "delta": rows[r]} for r in POINT_ORDER if r in rows]
    gained = sum(x["delta"] for x in lines)
    before = _ledger_total(att.student, att.submitted_at, exclude_refs=(str(att.id), f"red{red.id}")) if not att.is_practice \
        else _ledger_total(att.student)
    lv_before, lv_after = level_for(before), level_for(before + gained)
    new_badges = [{"key": ub.badge.key, "name": ub.badge.name, "description": ub.badge.description}
                  for ub in UserBadge.objects.filter(student=att.student, ref=f"a{att.id}").select_related("badge")]
    key = "excellent" if pct >= 90 else "good" if pct >= 70 else "keep_practising" if pct >= 40 else "review_basics"
    feedback = [{"key": f"feedback.{key}", "params": {"percent": pct}}]
    if weak_topics:
        feedback.append({"key": "feedback.weak_topic", "params": {"kind": weak_topics[0]["kind"], "tag": weak_topics[0]["tag"]}})
    if att.no_lab_data:
        feedback.append({"key": "feedback.no_lab_data", "params": {}})
    if att.is_practice:
        feedback.append({"key": "feedback.practice", "params": {}})
    return {"score": {"correct": att.correct_count, "total": att.total, "percent": pct}, "is_practice": att.is_practice,
            "points": {"total": gained, "lines": lines}, "new_badges": new_badges,
            "level_before": {"id": lv_before["id"], "name": lv_before["name"]},
            "level_after": {"id": lv_after["id"], "name": lv_after["name"]},
            "leveled_up": lv_after["id"] != lv_before["id"], "review": review, "weak_topics": weak_topics,
            "insights": _insights(red), "feedback": feedback, "no_lab_data": att.no_lab_data,
            "partial_dynamic": att.partial_dynamic}


def history_for(student) -> dict:
    atts = QuizAttempt.objects.filter(student=student, status="submitted").select_related("redemption__item") \
        .order_by("-submitted_at")
    return {"attempts": [{"attempt_id": a.id, "item": a.redemption.item.key, "formula": a.redemption.item.formula,
                          "name": a.redemption.item.name, "submitted_at": a.submitted_at, "correct": a.correct_count,
                          "total": a.total, "percent": round(100 * a.correct_count / a.total) if a.total else 0,
                          "is_practice": a.is_practice} for a in atts],
            "ledger": [{"delta": l.delta, "reason": l.reason, "created": l.created}
                       for l in PointsLedger.objects.filter(student=student).order_by("-created", "-id")[:200]]}
