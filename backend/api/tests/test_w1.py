"""W1 tests: auth, classes, redeem (spec scenarios E2 E3 E4 E5 E9), rate limits, sessions.
Run:  python backend\\manage.py test api -v 2"""
import datetime as dt

from django.test import TestCase, override_settings
from django.utils import timezone

from api.models import AuthToken, InvalidAttempt, Redemption, UserBadge, AuditLog
from lab_pack.verify_code import ist_today

from .helpers import (api, code_for, days_ago, load_all, make_class, make_teacher, register, token_for)

SID = "2411021061202"


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_all()
        cls.teacher = make_teacher()
        cls.klass = make_class(cls.teacher)

    def student(self, sid=SID, pin="4321", klass=None):
        r = register((klass or self.klass).join_code, sid, pin)
        self.assertEqual(r.status_code, 201, r.data)
        return api(r.data["token"])


class TestAuth(Base):
    def test_register_normalises_student_id(self):
        r = register(self.klass.join_code, " 24 11021 061202 ")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["me"]["id"], SID)
        self.assertEqual(r.data["me"]["classes"][0]["name"], "PU1-A")

    def test_register_validation(self):
        self.assertEqual(register("NOPE99").data["error"], "invalid_join_code")
        self.assertEqual(register(self.klass.join_code, pin="12").data["error"], "invalid_pin")
        self.assertEqual(register(self.klass.join_code, pin="abcd").data["error"], "invalid_pin")
        self.assertEqual(register(self.klass.join_code, student_id="a@b").data["error"], "invalid_student_id")
        self.assertEqual(register(self.klass.join_code, student_id="  ").data["error"], "invalid_student_id")
        self.assertEqual(register(self.klass.join_code, student_id="AB|C").data["error"], "invalid_student_id")

    def test_join_code_is_case_and_space_insensitive(self):
        r = register(" " + self.klass.join_code.lower() + " ")
        self.assertEqual(r.status_code, 201)

    def test_duplicate_registration_rejected(self):
        self.student()
        r = register(self.klass.join_code)
        self.assertEqual((r.status_code, r.data["error"]), (409, "already_registered"))

    def test_disabled_join_code_rejected(self):
        self.klass.join_enabled = False
        self.klass.save()
        self.assertEqual(register(self.klass.join_code).data["error"], "invalid_join_code")

    def test_login_ok_and_wrong_pin(self):
        self.student()
        ok = api().post("/api/auth/login", {"identifier": " 24 11021061202", "secret": "4321"}, format="json")
        self.assertEqual(ok.status_code, 200)
        bad = api().post("/api/auth/login", {"identifier": SID, "secret": "0000"}, format="json")
        self.assertEqual((bad.status_code, bad.data["error"]), (401, "invalid_credentials"))
        unknown = api().post("/api/auth/login", {"identifier": "NOBODY", "secret": "0000"}, format="json")
        self.assertEqual(unknown.data, bad.data)                       # no hint whether the ID exists

    def test_login_rate_limited_even_with_right_pin(self):
        self.student()
        for _ in range(5):
            api().post("/api/auth/login", {"identifier": SID, "secret": "9999"}, format="json")
        r = api().post("/api/auth/login", {"identifier": SID, "secret": "4321"}, format="json")
        self.assertEqual((r.status_code, r.data["error"]), (429, "rate_limited"))

    def test_teacher_login_and_roles(self):
        t = api().post("/api/auth/login", {"identifier": "T1@school.in", "secret": "teacher-pass-1"}, format="json")
        self.assertEqual(t.status_code, 200)
        self.assertEqual(t.data["me"]["role"], "teacher")
        teacher, student = api(t.data["token"]), self.student()
        self.assertEqual(teacher.get("/api/progress").status_code, 403)        # teacher cannot use student API
        self.assertEqual(student.get("/api/teacher/classes").status_code, 403)  # student cannot use teacher API
        self.assertEqual(api().get("/api/progress").status_code, 401)

    def test_teacher_role_protection_comprehensive(self):
        """Verify role protection contract: teacher blocked from student quiz/redeem; student blocked from teacher classes."""
        t_res = api().post("/api/auth/login", {"identifier": "t1@school.in", "secret": "teacher-pass-1"}, format="json")
        teacher = api(t_res.data["token"])
        student = self.student()

        # Teacher /api/me returns role teacher
        me_t = teacher.get("/api/me")
        self.assertEqual(me_t.status_code, 200)
        self.assertEqual(me_t.data["role"], "teacher")

        # Teacher cannot redeem codes or start quizzes
        self.assertEqual(teacher.post("/api/redeem", {"code": "VL-NA-CL-7K3Q-9F2A"}, format="json").status_code, 403)
        self.assertEqual(teacher.post("/api/quiz/start", {"item_id": "nacl"}, format="json").status_code, 403)

        # Student cannot access teacher class management
        self.assertEqual(student.get("/api/teacher/classes").status_code, 403)
        self.assertEqual(student.post("/api/teacher/classes", {"name": "Hacked"}, format="json").status_code, 403)
        self.assertEqual(student.get(f"/api/teacher/classes/{self.klass.id}/students").status_code, 403)

        # Unauthenticated blocked
        self.assertEqual(api().get("/api/teacher/classes").status_code, 401)

    def test_student_cannot_login_through_teacher_path(self):
        self.student()
        r = api().post("/api/auth/login", {"identifier": "2411021061202@x.in", "secret": "4321"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_expired_and_logged_out_sessions(self):
        c = self.student()
        AuthToken.objects.update(expires=timezone.now() - dt.timedelta(seconds=1))
        self.assertEqual(c.get("/api/me").status_code, 401)
        c2 = api(register(self.klass.join_code, "ZZ1", "1111").data["token"])
        self.assertEqual(c2.post("/api/auth/logout").status_code, 200)
        self.assertEqual(c2.get("/api/me").status_code, 401)

    def test_change_pin(self):
        c = self.student()
        self.assertEqual(c.post("/api/auth/change-pin", {"old_pin": "0000", "new_pin": "5555"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/auth/change-pin", {"old_pin": "4321", "new_pin": "55"}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/auth/change-pin", {"old_pin": "4321", "new_pin": "5555"}, format="json").status_code, 200)
        self.assertEqual(api().post("/api/auth/login", {"identifier": SID, "secret": "5555"}, format="json").status_code, 200)

    def test_student_joins_second_class(self):
        c = self.student()
        other = make_class(self.teacher, "PU1-B")
        r = c.post("/api/classes/join", {"join_code": other.join_code}, format="json")
        self.assertEqual(len(r.data["classes"]), 2)


class TestRedeem(Base):
    def test_happy_path_with_token(self):
        c = self.student()
        code = code_for(SID, "cuso4")
        r = c.post("/api/redeem", {"code": code, "token": token_for(SID, "cuso4", code)}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual((r.data["item"], r.data["token_valid"], r.data["no_lab_data"]), ("cuso4", True, False))
        self.assertEqual([b["key"] for b in r.data["new_badges"]], ["first_spark", "lab_perfectionist"])  # flawless lab run
        grid = {i["item"]: i for i in c.get("/api/progress").data["items"]}
        self.assertEqual(grid["cuso4"]["status"], "unlocked")
        self.assertEqual(grid["nacl"]["status"], "locked")
        self.assertEqual(len(grid), 12)

    def test_typing_variants_accepted(self):
        c = self.student()
        code = code_for(SID, "nacl", nonce="0000")
        sloppy = " " + code.lower().replace("-0000-", "-oooo-").replace("-", "\u2013") + " "
        r = c.post("/api/redeem", {"code": sloppy}, format="json")
        self.assertEqual(r.status_code, 201, r.data)

    def test_no_token_means_no_lab_data_E4(self):
        c = self.student()
        r = c.post("/api/redeem", {"code": code_for(SID, "nacl")}, format="json")
        self.assertEqual((r.data["token_valid"], r.data["no_lab_data"]), (False, True))
        self.assertIsNone(r.data["token_error"])

    def test_bad_token_ignored_but_logged_E5(self):
        c = self.student()
        code = code_for(SID, "nacl")
        tok = token_for(SID, "nacl", code)
        head, body, sig = tok.split(".")
        forged = ".".join([head, body[:-2] + ("AA" if body[-2:] != "AA" else "BB"), sig])
        r = c.post("/api/redeem", {"code": code, "token": forged}, format="json")
        self.assertEqual(r.status_code, 201)                       # redeem still succeeds
        self.assertEqual((r.data["token_valid"], r.data["no_lab_data"], r.data["token_error"]), (False, True, "bad_signature"))
        self.assertTrue(InvalidAttempt.objects.filter(kind="token", reason="bad_signature").exists())
        self.assertIsNone(Redemption.objects.get().token_json)      # nothing from a bad token is stored

    def test_token_for_other_student_ignored(self):
        c = self.student()
        code = code_for(SID, "nacl")
        other_tok = token_for("SOMEONEELSE", "nacl", code)
        r = c.post("/api/redeem", {"code": code, "token": other_tok}, format="json")
        self.assertFalse(r.data["token_valid"])
        self.assertTrue(r.data["no_lab_data"])
        self.assertIn(r.data["token_error"], ("wrong_student", "wrong_code"))

    def test_token_with_no_tests_counts_as_too_small(self):
        c = self.student()
        code = code_for(SID, "nacl")
        r = c.post("/api/redeem", {"code": code, "token": token_for(SID, "nacl", code, tests=[])}, format="json")
        self.assertEqual((r.data["token_valid"], r.data["no_lab_data"]), (True, True))

    def test_code_for_another_student_E2(self):
        c = self.student()
        r = c.post("/api/redeem", {"code": code_for("SOMEONEELSE", "nacl")}, format="json")
        self.assertEqual((r.status_code, r.data["error"]), (400, "invalid_code"))
        self.assertTrue(InvalidAttempt.objects.filter(kind="code", reason="invalid_code", student_id_text=SID).exists())
        self.assertTrue(AuditLog.objects.filter(action="redeem_rejected").exists())

    def test_reuse_by_another_student_E3(self):
        a = self.student()
        b = self.student("2411021061203", "1234")
        code = code_for(SID, "nacl")
        self.assertEqual(a.post("/api/redeem", {"code": code}, format="json").status_code, 201)
        r = b.post("/api/redeem", {"code": code}, format="json")
        self.assertEqual((r.status_code, r.data["error"]), (400, "already_used"))
        self.assertEqual(Redemption.objects.count(), 1)             # original untouched
        self.assertEqual(Redemption.objects.get().student.username, SID)

    def test_same_student_retry_is_idempotent(self):
        c = self.student()
        code = code_for(SID, "nacl")
        first = c.post("/api/redeem", {"code": code}, format="json")
        again = c.post("/api/redeem", {"code": code}, format="json")
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertTrue(again.data["already"])
        self.assertEqual(first.data["redemption_id"], again.data["redemption_id"])
        self.assertEqual(Redemption.objects.count(), 1)
        self.assertEqual(UserBadge.objects.count(), 1)

    def test_expired_code(self):
        c = self.student()
        r = c.post("/api/redeem", {"code": code_for(SID, "nacl", issue=days_ago(40))}, format="json")
        self.assertEqual(r.data["error"], "expired")
        ok = c.post("/api/redeem", {"code": code_for(SID, "nacl", issue=days_ago(30))}, format="json")
        self.assertEqual(ok.status_code, 201)                      # oldest allowed day

    def test_forged_and_malformed_codes(self):
        c = self.student()
        good = code_for(SID, "nacl")
        flipped = good[:-1] + ("0" if good[-1] != "0" else "1")
        self.assertEqual(c.post("/api/redeem", {"code": flipped}, format="json").data["error"], "invalid_code")
        self.assertEqual(c.post("/api/redeem", {"code": "hello"}, format="json").data["error"], "bad_format")
        self.assertEqual(c.post("/api/redeem", {"code": ""}, format="json").data["error"], "bad_format")
        self.assertEqual(c.post("/api/redeem", {"code": "VL-NA-SO4-7K3Q-9F2A"}, format="json").data["error"], "bad_format")
        self.assertEqual(c.post("/api/redeem", {}, format="json").data["error"], "bad_format")

    def test_second_code_for_same_salt_rejected(self):
        c = self.student()
        self.assertEqual(c.post("/api/redeem", {"code": code_for(SID, "nacl", nonce="AAAA")}, format="json").status_code, 201)
        r = c.post("/api/redeem", {"code": code_for(SID, "nacl", nonce="BBBB")}, format="json")
        self.assertEqual(r.data["error"], "item_already_unlocked")

    def test_rate_limit_after_five_failures(self):
        c = self.student()
        for _ in range(5):
            self.assertEqual(c.post("/api/redeem", {"code": "VL-NA-CL-AAAA-BBBB"}, format="json").status_code, 400)
        r = c.post("/api/redeem", {"code": code_for(SID, "nacl")}, format="json")      # even a valid code is held back
        self.assertEqual((r.status_code, r.data["error"]), (429, "rate_limited"))
        self.assertEqual(Redemption.objects.count(), 0)

    def test_old_failures_do_not_count(self):
        c = self.student()
        for _ in range(5):
            c.post("/api/redeem", {"code": "VL-NA-CL-AAAA-BBBB"}, format="json")
        InvalidAttempt.objects.update(ts=timezone.now() - dt.timedelta(seconds=700))
        self.assertEqual(c.post("/api/redeem", {"code": code_for(SID, "nacl")}, format="json").status_code, 201)

    @override_settings(HMAC_SECRET="")
    def test_unconfigured_secret_fails_safe(self):
        c = self.student()
        r = c.post("/api/redeem", {"code": "VL-NA-CL-AAAA-BBBB"}, format="json")
        self.assertEqual((r.status_code, r.data["error"]), (503, "server_not_configured"))

    def test_all_twelve_items_redeemable_and_badge_progress(self):
        c = self.student()
        keys = [i["item"] for i in c.get("/api/progress").data["items"]]
        for k in keys:
            self.assertEqual(c.post("/api/redeem", {"code": code_for(SID, k)}, format="json").status_code, 201, k)
        self.assertEqual(c.get("/api/progress").data["total_items"], 12)
        self.assertEqual(Redemption.objects.count(), 12)

    def test_error_shape_is_uniform(self):
        c = self.student()
        r = c.post("/api/redeem", {"code": "x"}, format="json")
        self.assertEqual(set(r.data), {"error"})


class TestTeacherIsolation(Base):
    def setUp(self):
        self.t2 = make_teacher("t2@school.in")
        self.c1 = api(api().post("/api/auth/login", {"identifier": "t1@school.in", "secret": "teacher-pass-1"}, format="json").data["token"])
        self.c2 = api(api().post("/api/auth/login", {"identifier": "t2@school.in", "secret": "teacher-pass-1"}, format="json").data["token"])
        self.student()

    def test_lists_only_own_classes(self):
        self.assertEqual(len(self.c1.get("/api/teacher/classes").data), 1)
        self.assertEqual(self.c2.get("/api/teacher/classes").data, [])

    def test_other_teacher_gets_404_everywhere_E9(self):
        cid = self.klass.id
        self.assertEqual(self.c2.get(f"/api/teacher/classes/{cid}/students").status_code, 404)
        self.assertEqual(self.c2.patch(f"/api/teacher/classes/{cid}", {"name": "hacked"}, format="json").status_code, 404)
        self.assertEqual(self.c2.post(f"/api/teacher/classes/{cid}/students/{SID}/reset-pin").status_code, 404)
        self.klass.refresh_from_db()
        self.assertEqual(self.klass.name, "PU1-A")
        self.assertEqual(api().post("/api/auth/login", {"identifier": SID, "secret": "4321"}, format="json").status_code, 200)

    def test_owner_manages_class_and_roster(self):
        r = self.c1.post("/api/teacher/classes", {"name": "PU2-B", "grade": "12", "section": "B"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["join_code"]), 6)
        old = self.klass.join_code
        rot = self.c1.patch(f"/api/teacher/classes/{self.klass.id}", {"rotate_join_code": True}, format="json")
        self.assertNotEqual(rot.data["join_code"], old)
        self.assertEqual(register(old, "NEW1", "1111").data["error"], "invalid_join_code")
        roster = self.c1.get(f"/api/teacher/classes/{self.klass.id}/students").data
        self.assertEqual([s["student_id"] for s in roster], [SID])

    def test_reset_pin_forces_change_and_logs_out(self):
        old = api(register(self.klass.join_code, "RESET1", "1111").data["token"])
        r = self.c1.post(f"/api/teacher/classes/{self.klass.id}/students/RESET1/reset-pin")
        temp = r.data["temporary_pin"]
        self.assertEqual(len(temp), 6)
        self.assertEqual(old.get("/api/me").status_code, 401)          # old sessions ended
        login = api().post("/api/auth/login", {"identifier": "RESET1", "secret": temp}, format="json")
        self.assertTrue(login.data["me"]["must_change_pin"])
        self.assertEqual(api().post("/api/auth/login", {"identifier": "RESET1", "secret": "1111"}, format="json").status_code, 401)

    def test_class_crud_and_archive_lifecycle(self):
        """Phase 3: Verify class creation, editing, join disabling, archiving, and restoration."""
        # 1. Validation: empty name rejected
        bad = self.c1.post("/api/teacher/classes", {"name": "   "}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.data["error"], "name_required")

        # 2. Create class
        res = self.c1.post("/api/teacher/classes", {"name": "Chem 101", "grade": "11", "section": "A"}, format="json")
        self.assertEqual(res.status_code, 201)
        cid = res.data["id"]
        self.assertTrue(res.data["active"])
        self.assertTrue(res.data["join_enabled"])
        join_code = res.data["join_code"]

        # 3. Edit class details
        patch_res = self.c1.patch(f"/api/teacher/classes/{cid}", {"name": "Chem 101 Advanced", "section": "A+"}, format="json")
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.data["name"], "Chem 101 Advanced")
        self.assertEqual(patch_res.data["section"], "A+")

        # 4. Disable join code
        disable_res = self.c1.patch(f"/api/teacher/classes/{cid}", {"join_enabled": False}, format="json")
        self.assertFalse(disable_res.data["join_enabled"])
        # Attempt student registration with paused join code fails
        reg_attempt = register(join_code, "JOINERR1", "1234")
        self.assertEqual(reg_attempt.data["error"], "invalid_join_code")

        # 5. Archive class
        archive_res = self.c1.patch(f"/api/teacher/classes/{cid}", {"active": False}, format="json")
        self.assertFalse(archive_res.data["active"])

        # 6. Restore class
        restore_res = self.c1.patch(f"/api/teacher/classes/{cid}", {"active": True, "join_enabled": True}, format="json")
        self.assertTrue(restore_res.data["active"])
        self.assertTrue(restore_res.data["join_enabled"])

    def test_teacher_cannot_modify_or_archive_another_teachers_class(self):
        """Phase 3: Verify teacher 2 cannot edit or archive teacher 1's class."""
        cid = self.klass.id
        # Attempt edit
        res = self.c2.patch(f"/api/teacher/classes/{cid}", {"name": "Stolen Class"}, format="json")
        self.assertEqual(res.status_code, 404)
        # Attempt archive
        res_arch = self.c2.patch(f"/api/teacher/classes/{cid}", {"active": False}, format="json")
        self.assertEqual(res_arch.status_code, 404)
        # Verify database remained unchanged
        self.klass.refresh_from_db()
        self.assertEqual(self.klass.name, "PU1-A")
        self.assertTrue(self.klass.active)

    def test_class_overview_analytics_and_isolation(self):
        """Phase 4: Verify class overview KPIs, per-salt metrics, trends, inactive students, and isolation."""
        # 1. Isolation: Teacher 2 cannot access Teacher 1's class overview (returns 404)
        res_t2 = self.c2.get(f"/api/teacher/classes/{self.klass.id}/overview")
        self.assertEqual(res_t2.status_code, 404)

        # 2. Create dedicated class for analytics verification
        cls_res = self.c1.post("/api/teacher/classes", {"name": "Analytics Class", "grade": "11", "section": "Sci"}, format="json")
        self.assertEqual(cls_res.status_code, 201)
        cid = cls_res.data["id"]
        join_code = cls_res.data["join_code"]

        # 3. Register active student and an inactive student in this dedicated class
        reg_active = register(join_code, "ACT1", "1234")
        self.assertEqual(reg_active.status_code, 201)
        reg_inactive = register(join_code, "INACT1", "5678")
        self.assertEqual(reg_inactive.status_code, 201)

        # 4. Simulate redemption and quiz attempt for ACT1
        from api.models import Item, QuizAttempt, Redemption
        from django.contrib.auth.models import User
        user_act = User.objects.get(username="ACT1")
        item_nacl = Item.objects.get(key="nacl")

        red = Redemption.objects.create(
            student=user_act,
            item=item_nacl,
            code="VL-NA-CL-9999-1111",
            token_valid=True,
            no_lab_data=False,
            status="unlocked",
        )
        from django.utils import timezone
        attempt = QuizAttempt.objects.create(
            student=user_act,
            redemption=red,
            is_practice=False,
            status="submitted",
            submitted_at=timezone.now(),
            correct_count=8,
            total=10,
            duration_ms=45000,
        )

        # 5. Fetch overview for Teacher 1
        res = self.c1.get(f"/api/teacher/classes/{cid}/overview")
        self.assertEqual(res.status_code, 200)
        data = res.data

        # Check metadata
        self.assertEqual(data["class"]["id"], cid)
        self.assertEqual(data["class"]["name"], "Analytics Class")

        # Check KPIs
        kpis = data["kpis"]
        # total students: ACT1 + INACT1 = 2
        self.assertEqual(kpis["total_students"], 2)
        self.assertEqual(kpis["active_students_7d"], 1)
        self.assertEqual(kpis["total_redemptions"], 1)
        self.assertEqual(kpis["total_valid_redemptions"], 1)
        self.assertEqual(kpis["completed_graded_quizzes"], 1)
        self.assertEqual(kpis["avg_quiz_score_percent"], 80.0)
        # 1 completed out of (2 students * 12 salts) = 1/24 = 4.2%
        self.assertEqual(kpis["overall_completion_percent"], 4.2)
        self.assertEqual(kpis["participation_percent"], 50.0)

        # Check salts table
        self.assertEqual(len(data["salts"]), 12)
        nacl_stat = next(s for s in data["salts"] if s["key"] == "nacl")
        self.assertEqual(nacl_stat["redeemed_count"], 1)
        self.assertEqual(nacl_stat["completed_count"], 1)
        self.assertEqual(nacl_stat["completion_percent"], 50.0)
        self.assertEqual(nacl_stat["avg_score_percent"], 80.0)
        self.assertEqual(nacl_stat["avg_duration_seconds"], 45.0)

        # Check 14-day trend
        self.assertEqual(len(data["trend"]), 14)
        latest_day = data["trend"][-1]
        self.assertEqual(latest_day["redemptions"], 1)
        self.assertEqual(latest_day["quizzes"], 1)
        self.assertEqual(latest_day["active_students"], 1)

        # Check inactive students: INACT1 should be listed
        inactive_ids = [s["student_id"] for s in data["inactive_students"]]
        self.assertIn("INACT1", inactive_ids)
        self.assertNotIn("ACT1", inactive_ids)

        # Check visibility notice
        self.assertIn("portal only tracks activity", data["visibility_notice"])

    def test_class_learning_insights_analytics_and_isolation(self):
        """Phase 6: Verify learning gaps, salt analytics, practical mistakes, support list, and strict teacher isolation."""
        from api.models import Answer, Item, QuizAttempt, QuizQuestion, Redemption
        from django.contrib.auth.models import User
        from django.utils import timezone

        # 1. Authorization & Isolation:
        # Teacher 2 cannot access Teacher 1's class learning insights (returns 404)
        res_t2 = self.c2.get(f"/api/teacher/classes/{self.klass.id}/learning-insights")
        self.assertEqual(res_t2.status_code, 404)

        # 2. Setup dedicated class for Phase 6
        cls_res = self.c1.post("/api/teacher/classes", {"name": "Insights Class", "grade": "12"}, format="json")
        self.assertEqual(cls_res.status_code, 201)
        cid = cls_res.data["id"]
        join_code = cls_res.data["join_code"]

        # Register two students in this class
        reg1 = register(join_code, "STU_P6_1", "1111")
        reg2 = register(join_code, "STU_P6_2", "2222")
        self.assertEqual(reg1.status_code, 201)
        self.assertEqual(reg2.status_code, 201)

        # Student cannot access teacher learning insights (403)
        stu_client = api(reg1.data["token"])
        self.assertEqual(stu_client.get(f"/api/teacher/classes/{cid}/learning-insights").status_code, 403)

        u1 = User.objects.get(username="STU_P6_1")
        u2 = User.objects.get(username="STU_P6_2")
        item_nacl = Item.objects.get(key="nacl")
        item_cuso4 = Item.objects.get(key="cuso4")

        # 3. Simulate redemption with valid token containing lab mistakes for u1
        red1 = Redemption.objects.create(
            student=u1,
            item=item_nacl,
            code="VL-NA-CL-P601-1111",
            token_valid=True,
            no_lab_data=False,
            token_json={"att": 1, "mis": ["reagent_excess", "skipped_confirmatory"], "wrong": 0},
            status="unlocked",
        )

        # Graded attempt for u1 on nacl: 10 questions with topic 'flame' (7 correct, 3 incorrect)
        att1 = QuizAttempt.objects.create(
            student=u1,
            redemption=red1,
            is_practice=False,
            status="submitted",
            submitted_at=timezone.now(),
            correct_count=7,
            total=10,
        )
        for i in range(1, 11):
            is_cor = (i <= 7)
            qq = QuizQuestion.objects.create(
                attempt=att1,
                position=i,
                source="dynamic",
                test_type="flame",
                question_json={"question": f"Q{i}", "options": ["A", "B", "C", "D"]},
                correct_answer="A",
            )
            Answer.objects.create(
                attempt=att1,
                question=qq,
                chosen="A" if is_cor else "B",
                is_correct=is_cor,
            )

        # Graded attempt for u1 on cuso4 with low score (e.g. 2/10 = 20%) to test student support indicators
        red2 = Redemption.objects.create(
            student=u1,
            item=item_cuso4,
            code="VL-CU-SO4-P602-2222",
            token_valid=True,
            no_lab_data=False,
            token_json={"att": 1, "mis": ["reagent_excess"], "wrong": 1},
            status="unlocked",
        )
        att2 = QuizAttempt.objects.create(
            student=u1,
            redemption=red2,
            is_practice=False,
            status="submitted",
            submitted_at=timezone.now(),
            correct_count=2,
            total=10,
        )
        # 5 answers on 'dilute_acid' (1 correct, 4 incorrect)
        for i in range(1, 6):
            is_cor = (i == 1)
            qq = QuizQuestion.objects.create(
                attempt=att2,
                position=i,
                source="dynamic",
                test_type="dilute_acid",
                question_json={"question": f"Q_acid_{i}", "options": ["A", "B", "C", "D"]},
                correct_answer="A",
            )
            Answer.objects.create(
                attempt=att2,
                question=qq,
                chosen="A" if is_cor else "B",
                is_correct=is_cor,
            )

        # 4. Fetch learning insights as Teacher 1
        res = self.c1.get(f"/api/teacher/classes/{cid}/learning-insights")
        self.assertEqual(res.status_code, 200)
        data = res.data

        # Check summary
        summary = data["summary"]
        self.assertEqual(summary["total_students"], 2)
        self.assertEqual(summary["total_answers_recorded"], 15)  # 10 + 5
        self.assertTrue(summary["has_telemetry"])
        self.assertEqual(summary["valid_tokens_count"], 2)

        # Check Topics
        topics = {t["topic"]: t for t in data["topics"]}
        self.assertIn("flame", topics)
        self.assertIn("dilute_acid", topics)

        # 'flame' has 10 answers -> sufficient_evidence=True
        flame_t = topics["flame"]
        self.assertTrue(flame_t["sufficient_evidence"])
        self.assertEqual(flame_t["total_answers"], 10)
        self.assertEqual(flame_t["correct_answers"], 7)
        self.assertEqual(flame_t["incorrect_answers"], 3)
        self.assertEqual(flame_t["correct_percent"], 70.0)
        self.assertEqual(flame_t["gap_score"], 0.3)  # 1 - (7/10) = 0.3

        # 'dilute_acid' has 5 answers -> sufficient_evidence=False (< 10 threshold)
        acid_t = topics["dilute_acid"]
        self.assertFalse(acid_t["sufficient_evidence"])
        self.assertEqual(acid_t["total_answers"], 5)
        self.assertEqual(acid_t["correct_answers"], 1)
        self.assertEqual(acid_t["gap_score"], 0.8)  # 1 - (1/5) = 0.8

        # Check Salts Performance (all 12 salts represented)
        self.assertEqual(len(data["salts"]), 12)
        nacl_s = next(s for s in data["salts"] if s["key"] == "nacl")
        self.assertEqual(nacl_s["students_with_quiz"], 1)
        self.assertEqual(nacl_s["valid_graded_submissions"], 1)
        self.assertEqual(nacl_s["avg_quiz_score_percent"], 70.0)
        self.assertEqual(nacl_s["practical_completed_students"], 1)

        # Check Practical Mistakes
        pm = data["practical_mistakes"]
        self.assertTrue(pm["has_telemetry"])
        self.assertEqual(pm["denominator_tokens"], 2)
        mis_dict = {c["category"]: c for c in pm["categories"]}
        # reagent_excess occurred in both red1 and red2 (2 tokens) -> 100%
        self.assertEqual(mis_dict["reagent_excess"]["occurrences"], 2)
        self.assertEqual(mis_dict["reagent_excess"]["rate_percent"], 100.0)
        # skipped_confirmatory occurred in 1 token -> 50%
        self.assertEqual(mis_dict["skipped_confirmatory"]["occurrences"], 1)
        self.assertEqual(mis_dict["skipped_confirmatory"]["rate_percent"], 50.0)

        # Check Students Needing Support: u1 should be flagged with evidence
        support_ids = [s["student_id"] for s in data["students_needing_support"]]
        self.assertIn("STU_P6_1", support_ids)
        u1_support = next(s for s in data["students_needing_support"] if s["student_id"] == "STU_P6_1")
        self.assertTrue(len(u1_support["reasons"]) > 0)
        # Check reasons include low quiz score (< 50% avg) or topic struggle or practical mistakes
        reason_text = " ".join(u1_support["reasons"])
        self.assertTrue("Low average quiz score" in reason_text or "lab run mistakes" in reason_text)

    def test_class_csv_exports_security_and_isolation(self):
        """Phase 7: Verify CSV exports (roster, quiz, practical, salts, insights), formula sanitization, BOM, audit logs, and isolation."""
        from api.models import AuditLog, Item, QuizAttempt, Redemption
        from django.contrib.auth.models import User
        from django.utils import timezone

        # 1. Authorization: Unauthenticated (401), Cross-teacher (404)
        cid = self.klass.id
        self.assertEqual(api().get(f"/api/teacher/classes/{cid}/export/roster").status_code, 401)
        self.assertEqual(self.c2.get(f"/api/teacher/classes/{cid}/export/roster").status_code, 404)

        # 2. Setup dedicated class for Phase 7 export testing
        cls_res = self.c1.post("/api/teacher/classes", {"name": "Export Class", "grade": "10"}, format="json")
        self.assertEqual(cls_res.status_code, 201)
        cid = cls_res.data["id"]
        join_code = cls_res.data["join_code"]

        # Register students: one with Kannada text, one with a formula-injection candidate name
        reg1 = register(join_code, "EXP_STU_1", "1234")
        self.assertEqual(reg1.status_code, 201)
        u1 = User.objects.get(username="EXP_STU_1")
        u1.profile.display_name = "ಆನಂದ್ ಕುಮಾರ್"  # Kannada name
        u1.profile.save()

        reg2 = register(join_code, "EXP_STU_2", "5678")
        self.assertEqual(reg2.status_code, 201)
        u2 = User.objects.get(username="EXP_STU_2")
        u2.profile.display_name = "=cmd|' /C calc'!A0"  # Malicious formula injection attempt
        u2.profile.save()

        # Student cannot access exports (403)
        stu_client = api(reg1.data["token"])
        self.assertEqual(stu_client.get(f"/api/teacher/classes/{cid}/export/roster").status_code, 403)
        self.assertEqual(stu_client.get(f"/api/teacher/classes/{cid}/export/quiz-results").status_code, 403)

        # Create activity for EXP_STU_1
        item_nacl = Item.objects.get(key="nacl")
        red1 = Redemption.objects.create(
            student=u1,
            item=item_nacl,
            code="VL-NA-CL-EXP1-1111",
            token_valid=True,
            no_lab_data=False,
            token_json={"dur_s": 120, "att": 1, "mis": ["reagent_excess"], "wrong": 0},
            status="unlocked",
        )
        QuizAttempt.objects.create(
            student=u1,
            redemption=red1,
            is_practice=False,
            status="submitted",
            submitted_at=timezone.now(),
            correct_count=9,
            total=10,
            duration_ms=50000,
            points_awarded=150,
        )

        # 3. Test Roster Export
        res_roster = self.c1.get(f"/api/teacher/classes/{cid}/export/roster")
        self.assertEqual(res_roster.status_code, 200)
        self.assertEqual(res_roster["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(f"virtulab_class_{join_code}_roster.csv", res_roster["Content-Disposition"])
        content_roster = res_roster.content.decode("utf-8-sig")
        # Verify BOM is present at raw start
        self.assertTrue(res_roster.content.startswith(b"\xef\xbb\xbf"))
        # Verify Kannada Unicode is preserved
        self.assertIn("ಆನಂದ್ ಕುಮಾರ್", content_roster)
        # Verify formula injection is sanitized: '=cmd...' becomes '=cmd...'
        self.assertIn("'=cmd|' /C calc'!A0", content_roster)
        # Verify headers
        self.assertIn("Student ID,Display Name,Enrollment Date", content_roster)
        # Verify no PIN or secrets
        self.assertNotIn("1234", content_roster)
        self.assertNotIn("password", content_roster.lower())

        # 4. Test Quiz Results Export
        res_quiz = self.c1.get(f"/api/teacher/classes/{cid}/export/quiz-results")
        self.assertEqual(res_quiz.status_code, 200)
        self.assertIn(f"virtulab_class_{join_code}_quiz_results.csv", res_quiz["Content-Disposition"])
        content_quiz = res_quiz.content.decode("utf-8-sig")
        self.assertIn("EXP_STU_1", content_quiz)
        self.assertIn("Sodium chloride", content_quiz)
        self.assertIn("90.0", content_quiz)  # 9/10 score %
        self.assertIn("50.0", content_quiz)  # duration seconds

        # 5. Test Practical Records Export
        res_prac = self.c1.get(f"/api/teacher/classes/{cid}/export/practical-records")
        self.assertEqual(res_prac.status_code, 200)
        self.assertIn(f"virtulab_class_{join_code}_practical_records.csv", res_prac["Content-Disposition"])
        content_prac = res_prac.content.decode("utf-8-sig")
        self.assertIn("EXP_STU_1", content_prac)
        self.assertIn("reagent_excess", content_prac)
        self.assertIn("120", content_prac)
        # Raw token payloads or secrets must NOT be present
        self.assertNotIn("token_codec", content_prac)

        # 6. Test Salt Performance Export
        res_salt = self.c1.get(f"/api/teacher/classes/{cid}/export/salt-performance")
        self.assertEqual(res_salt.status_code, 200)
        content_salt = res_salt.content.decode("utf-8-sig")
        self.assertIn("nacl,NaCl,Sodium chloride,NA,CL", content_salt)

        # 7. Test Learning Insights Export
        res_ins = self.c1.get(f"/api/teacher/classes/{cid}/export/learning-insights")
        self.assertEqual(res_ins.status_code, 200)
        content_ins = res_ins.content.decode("utf-8-sig")
        self.assertIn("# SECTION 1: TOPIC-WISE LEARNING GAPS", content_ins)
        self.assertIn("# SECTION 2: PRACTICAL LAB MISTAKES", content_ins)
        self.assertIn("# SECTION 3: STUDENTS WHO MAY BENEFIT FROM SUPPORT", content_ins)

        # 8. Test Audit Logging: Verify audit log entries were created for exports
        audit_logs = list(AuditLog.objects.filter(action="export_report", detail_json__classroom=cid))
        self.assertEqual(len(audit_logs), 5)
        report_types = [a.detail_json["report_type"] for a in audit_logs]
        self.assertIn("roster", report_types)
        self.assertIn("quiz_results", report_types)
        self.assertIn("practical_records", report_types)
        self.assertIn("salt_performance", report_types)
        self.assertIn("learning_insights", report_types)

        # 9. Test Empty Class produces valid CSV with headers and 0 data rows
        cls_empty = self.c1.post("/api/teacher/classes", {"name": "Empty Class"}, format="json")
        cid_empty = cls_empty.data["id"]
        res_empty_roster = self.c1.get(f"/api/teacher/classes/{cid_empty}/export/roster")
        self.assertEqual(res_empty_roster.status_code, 200)
        lines = [ln.strip() for ln in res_empty_roster.content.decode("utf-8-sig").splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1)  # Only the header line

        # 10. Direct unit verification of sanitize_csv_cell edge cases
        from api.services_export import sanitize_csv_cell
        # Dangerous formula triggers sanitized with leading quote
        self.assertEqual(sanitize_csv_cell("=1+1"), "'=1+1")
        self.assertEqual(sanitize_csv_cell("   =1+1"), "'   =1+1")
        self.assertEqual(sanitize_csv_cell("\t=cmd"), "'\t=cmd")
        self.assertEqual(sanitize_csv_cell("\tnotepad"), "'\tnotepad")
        self.assertEqual(sanitize_csv_cell("\v=cmd"), "'\v=cmd")
        self.assertEqual(sanitize_csv_cell("\f=cmd"), "'\f=cmd")
        self.assertEqual(sanitize_csv_cell("\r\n-cmd"), "'\r\n-cmd")
        self.assertEqual(sanitize_csv_cell("   -calc"), "'   -calc")
        self.assertEqual(sanitize_csv_cell("@SUM(A1:A5)"), "'@SUM(A1:A5)")
        self.assertEqual(sanitize_csv_cell("+cmd|' /C calc'!A0"), "'+cmd|' /C calc'!A0")
        self.assertEqual(sanitize_csv_cell("-2+3*cmd"), "'-2+3*cmd")
        # Legitimate numbers (integers, floats, negative numbers, and numeric strings) remain uncorrupted
        self.assertEqual(sanitize_csv_cell(42), 42)
        self.assertEqual(sanitize_csv_cell(-42), -42)
        self.assertEqual(sanitize_csv_cell("-42"), "-42")
        self.assertEqual(sanitize_csv_cell("-12.5"), "-12.5")
        self.assertEqual(sanitize_csv_cell("+100"), "+100")
        self.assertEqual(sanitize_csv_cell(85.5), 85.5)
        self.assertEqual(sanitize_csv_cell("-0.05"), "-0.05")
        # Unicode and regular text preserved
        self.assertEqual(sanitize_csv_cell("Normal Text"), "Normal Text")
        self.assertEqual(sanitize_csv_cell("ಆನಂದ್ ಕುಮಾರ್"), "ಆನಂದ್ ಕುಮಾರ್")
        self.assertEqual(sanitize_csv_cell("CuSO4"), "CuSO4")
        self.assertEqual(sanitize_csv_cell(None), "")




