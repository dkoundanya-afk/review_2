"""W2: quiz engine. Run: python backend/manage.py test api"""
from django.test import TestCase

from api.models import Answer, PointsLedger, QuizAttempt, QuizQuestion, UserBadge
from .helpers import api, code_for, load_all, make_class, make_teacher, register, token_for

SID = "2411021061202"


class QuizBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_all()
        cls.klass = make_class(make_teacher())

    def setUp(self):
        r = register(self.klass.join_code, SID)
        self.c = api(r.data["token"])

    def redeem(self, item="cuso4", with_token=True, sid=SID, client=None, **tok):
        code = code_for(sid, item)
        body = {"code": code}
        if with_token:
            body["token"] = token_for(sid, item, code, **tok)
        r = (client or self.c).post("/api/redeem", body, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["redemption_id"]

    def start(self, rid, practice=False, client=None):
        r = (client or self.c).post("/api/quiz/start", {"redemption_id": rid, "practice": practice}, format="json")
        return r

    def answer_all(self, aid, right=True):
        q = self.c.get(f"/api/quiz/{aid}").data["questions"]
        out = []
        for x in q:
            qq = QuizQuestion.objects.get(pk=x["id"])
            pick = qq.correct_answer if right else next(o for o in x["options"] if o != qq.correct_answer)
            out.append({"question_id": x["id"], "chosen": pick, "time_ms": 1500})
        return out


class TestStartAndFreeze(QuizBase):
    def test_token_quiz_is_5_bank_5_dynamic_and_hides_answers(self):
        rid = self.redeem(tests=[{"r": "naoh", "d": 3, "n": 1}, {"r": "nh4oh", "d": 3, "n": 2}], flame=True,
                          gas=["co2"], mis=["skipped_flame"])
        r = self.start(rid)
        self.assertEqual(r.status_code, 201)
        d = self.c.get(f"/api/quiz/{r.data['attempt_id']}").data
        self.assertEqual(len(d["questions"]), 10)
        self.assertEqual(sum(1 for q in d["questions"] if q["source"] == "dynamic"), 5)
        self.assertEqual(sum(1 for q in d["questions"] if q["source"] == "bank"), 5)
        self.assertFalse(d["no_lab_data"])
        self.assertFalse(d["partial_dynamic"])
        for q in d["questions"]:
            self.assertEqual(len(q["options"]), 4)
            self.assertEqual(len(set(q["options"])), 4)
            self.assertNotIn("correct_answer", q)
        self.assertNotIn("correct_answer", str(d))

    def test_same_code_same_quiz_after_refresh_and_start_is_idempotent(self):
        rid = self.redeem()
        a1 = self.start(rid).data["attempt_id"]
        self.assertEqual(self.start(rid).data["attempt_id"], a1)               # double tap / second device
        before = [(q["question"], q["options"]) for q in self.c.get(f"/api/quiz/{a1}").data["questions"]]
        QuizAttempt.objects.get(pk=a1).delete()                                 # rebuild from the same seed
        a2 = self.start(rid).data["attempt_id"]
        after = [(q["question"], q["options"]) for q in self.c.get(f"/api/quiz/{a2}").data["questions"]]
        self.assertEqual(before, after)

    def test_no_token_falls_back_to_10_bank(self):
        rid = self.redeem(with_token=False)
        d = self.c.get(f"/api/quiz/{self.start(rid).data['attempt_id']}").data
        self.assertEqual(len(d["questions"]), 10)
        self.assertTrue(all(q["source"] == "bank" for q in d["questions"]))
        self.assertTrue(d["no_lab_data"])

    def test_thin_token_tops_up_from_bank_and_flags_partial(self):
        rid = self.redeem(tests=[{"r": "naoh", "d": 3, "n": 1}], flame=False)   # only naoh -> fewer than 5 dynamic
        d = self.c.get(f"/api/quiz/{self.start(rid).data['attempt_id']}").data
        self.assertEqual(len(d["questions"]), 10)
        self.assertTrue(d["partial_dynamic"])
        self.assertFalse(d["no_lab_data"])

    def test_distractors_never_equal_correct(self):
        rid = self.redeem(tests=[{"r": "naoh", "d": 3, "n": 1}], flame=True, gas=["co2"])
        aid = self.start(rid).data["attempt_id"]
        for q in QuizQuestion.objects.filter(attempt_id=aid, source="dynamic"):
            self.assertEqual(q.question_json["options"].count(q.correct_answer), 1)

    def test_other_students_attempt_is_404(self):
        rid = self.redeem()
        aid = self.start(rid).data["attempt_id"]
        other = api(register(self.klass.join_code, "OTHER1", "1234", "B").data["token"])
        self.assertEqual(other.get(f"/api/quiz/{aid}").status_code, 404)
        self.assertEqual(other.get(f"/api/quiz/{aid}/result").status_code, 404)
        self.assertEqual(self.start(rid, client=other).status_code, 404)


class TestAnswersAndSubmit(QuizBase):
    def test_autosave_validates_and_survives(self):
        aid = self.start(self.redeem()).data["attempt_id"]
        q = self.c.get(f"/api/quiz/{aid}").data["questions"][0]
        ok = self.c.put(f"/api/quiz/{aid}/answers", {"answers": [{"question_id": q["id"], "chosen": q["options"][1],
                                                                  "time_ms": 900}]}, format="json")
        self.assertEqual((ok.status_code, ok.data), (200, {"saved": 1}))
        self.assertEqual(self.c.get(f"/api/quiz/{aid}").data["answers"], {str(q["id"]): q["options"][1]})
        bad = self.c.put(f"/api/quiz/{aid}/answers", {"answers": [{"question_id": q["id"], "chosen": "nope"}]}, format="json")
        self.assertEqual((bad.status_code, bad.data["error"]), (400, "invalid_answer"))
        self.assertEqual(Answer.objects.count(), 1)

    def test_perfect_submit_points_badges_level_and_idempotent(self):
        rid = self.redeem(tests=[{"r": "naoh", "d": 3, "n": 1}, {"r": "nh4oh", "d": 3, "n": 2}], flame=True, gas=["co2"],
                          mis=["skipped_flame"])
        aid = self.start(rid).data["attempt_id"]
        r = self.c.post(f"/api/quiz/{aid}/submit", {"answers": self.answer_all(aid)}, format="json")
        self.assertEqual(r.status_code, 200, r.data)
        d = r.data
        self.assertEqual(d["score"], {"correct": 10, "total": 10, "percent": 100})
        lines = {x["reason"]: x["delta"] for x in d["points"]["lines"]}
        self.assertEqual(lines["correct_dynamic"], 50)
        self.assertEqual(lines["quiz_completion"], 20)
        self.assertEqual(d["points"]["total"], sum(lines.values()))
        self.assertNotIn("lab_flawless_bonus", lines)                           # token has a mistake
        keys = {b["key"] for b in d["new_badges"]}
        self.assertTrue({"flawless", "sharp_observer"} <= keys, keys)
        self.assertTrue(d["leveled_up"] and d["level_after"]["id"] != d["level_before"]["id"] or d["points"]["total"] < 150)
        self.assertTrue(all(x["is_correct"] for x in d["review"]))
        ledger_n = PointsLedger.objects.count()
        again = self.c.post(f"/api/quiz/{aid}/submit", {"answers": self.answer_all(aid, right=False)}, format="json")
        self.assertEqual(again.data["score"]["correct"], 10)                    # second submit changes nothing
        self.assertEqual(PointsLedger.objects.count(), ledger_n)
        put = self.c.put(f"/api/quiz/{aid}/answers", {"answers": []}, format="json")
        self.assertEqual((put.status_code, put.data["error"]), (409, "already_submitted"))
        self.assertEqual(self.c.get(f"/api/quiz/{aid}/result").data["points"], d["points"])
        prog = self.c.get("/api/progress").data
        self.assertEqual(prog["points"], d["points"]["total"])
        self.assertEqual(next(i for i in prog["items"] if i["item"] == "cuso4")["status"], "completed")

    def test_lab_flawless_bonus_and_wrong_answers_have_weak_topics(self):
        aid = self.start(self.redeem()).data["attempt_id"]                      # default token: 1 attempt, no mistakes
        d = self.c.post(f"/api/quiz/{aid}/submit", {"answers": self.answer_all(aid, right=False)}, format="json").data
        self.assertEqual(d["score"]["correct"], 0)
        lines = {x["reason"]: x["delta"] for x in d["points"]["lines"]}
        self.assertEqual(lines, {"quiz_completion": 20, "lab_flawless_bonus": 10})
        self.assertTrue(d["weak_topics"])
        self.assertEqual(d["feedback"][0]["key"], "feedback.review_basics")
        self.assertTrue(any(i["key"] == "insight.lab_flawless" for i in d["insights"]))

    def test_unanswered_questions_count_as_wrong_and_result_before_submit_is_409(self):
        aid = self.start(self.redeem()).data["attempt_id"]
        self.assertEqual(self.c.get(f"/api/quiz/{aid}/result").status_code, 409)
        d = self.c.post(f"/api/quiz/{aid}/submit", {}, format="json").data
        self.assertEqual(d["score"]["correct"], 0)
        self.assertTrue(all(x["chosen"] is None for x in d["review"]))


class TestPracticeAndHistory(QuizBase):
    def test_practice_needs_graded_first_gives_no_points_and_is_new_each_time(self):
        rid = self.redeem()
        self.assertEqual(self.start(rid, practice=True).data["error"], "practice_after_graded")
        aid = self.start(rid).data["attempt_id"]
        self.c.post(f"/api/quiz/{aid}/submit", {"answers": self.answer_all(aid)}, format="json")
        self.assertEqual(self.start(rid).status_code, 409)                      # graded attempt is final
        ledger = PointsLedger.objects.count()
        pid = self.start(rid, practice=True).data["attempt_id"]
        self.assertNotEqual(pid, aid)
        self.assertEqual(self.start(rid, practice=True).data["attempt_id"], pid)  # resume the open practice
        d = self.c.post(f"/api/quiz/{pid}/submit", {"answers": self.answer_all(pid)}, format="json").data
        self.assertTrue(d["is_practice"])
        self.assertEqual(d["points"], {"total": 0, "lines": []})
        self.assertEqual(d["new_badges"], [])
        self.assertEqual(PointsLedger.objects.count(), ledger)
        pid2 = self.start(rid, practice=True).data["attempt_id"]
        self.assertNotEqual(pid2, pid)

    def test_history_lists_attempts_and_ledger(self):
        aid = self.start(self.redeem()).data["attempt_id"]
        self.c.post(f"/api/quiz/{aid}/submit", {"answers": self.answer_all(aid)}, format="json")
        h = self.c.get("/api/history").data
        self.assertEqual(h["attempts"][0]["attempt_id"], aid)
        self.assertEqual(h["attempts"][0]["percent"], 100)
        self.assertTrue(h["ledger"] and {"delta", "reason", "created"} <= set(h["ledger"][0]))

    def test_badge_chloride_detective_needs_all_four(self):
        for item in ("nacl", "nh4cl", "fecl3", "bacl2"):
            aid = self.start(self.redeem(item)).data["attempt_id"]
            r = self.c.post(f"/api/quiz/{aid}/submit", {"answers": self.answer_all(aid)}, format="json").data
            got = "chloride_detective" in {b["key"] for b in r["new_badges"]}
            self.assertEqual(got, item == "bacl2")

    def test_all_12_salts_can_start_a_quiz(self):
        for item in ("nacl", "nh4cl", "cuso4", "feso4", "fecl3", "al2so43", "znso4", "bacl2", "caco3", "mgso4", "pbno32", "nh42co3"):
            aid = self.start(self.redeem(item, mis=["skipped_dissolve"], gas=["co2"])).data["attempt_id"]
            self.assertEqual(self.c.get(f"/api/quiz/{aid}").data["questions"].__len__(), 10, item)
