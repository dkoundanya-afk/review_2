"""Data model = spec section 4. All tables are defined now so later phases only add logic."""
from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Experiment(models.Model):
    key = models.SlugField(unique=True)                 # e.g. salt_analysis
    subject = models.CharField(max_length=30)           # chemistry / physics / biology
    title = models.CharField(max_length=120)

    def __str__(self):
        return self.key


class Item(models.Model):
    """One unlockable thing inside an experiment (a salt). Loaded from virtulab_data/quiz_map.json."""
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name="items")
    key = models.SlugField(unique=True)                 # nacl
    quiz_code = models.CharField(max_length=10)         # NA-CL
    cation = models.CharField(max_length=3)
    anion = models.CharField(max_length=3)
    group_tag = models.CharField(max_length=20, blank=True)   # chloride / sulphate / carbonate / nitrate
    formula = models.CharField(max_length=30)
    name = models.CharField(max_length=80)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "key"]
        constraints = [models.UniqueConstraint(fields=["cation", "anion"], name="uniq_item_pair")]

    def __str__(self):
        return self.key


class Profile(models.Model):
    ROLES = [("student", "student"), ("teacher", "teacher")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLES)
    display_name = models.CharField(max_length=60, blank=True)
    lang = models.CharField(max_length=8, default="en")
    pin_set = models.BooleanField(default=True)          # False = teacher added the student, PIN not chosen yet
    must_change_pin = models.BooleanField(default=False)  # True after a teacher reset

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class ClassRoom(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="classes")
    name = models.CharField(max_length=80)
    grade = models.CharField(max_length=10, blank=True)
    section = models.CharField(max_length=10, blank=True)
    join_code = models.CharField(max_length=8, unique=True)
    join_enabled = models.BooleanField(default=True)
    active = models.BooleanField(default=True)           # False = archived
    leaderboard = models.BooleanField(default=False)     # off by default (P6)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Enrollment(models.Model):
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["classroom", "student"], name="uniq_enrollment")]
        indexes = [models.Index(fields=["student"]), models.Index(fields=["classroom"])]


class AuthToken(models.Model):
    """Login session. Only a SHA-256 hash of the key is stored."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="auth_tokens")
    key_hash = models.CharField(max_length=64, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField()


class Redemption(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="redemptions")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="redemptions")
    code = models.CharField(max_length=40, unique=True)  # canonical form, globally single-use
    redeemed_at = models.DateTimeField(auto_now_add=True)
    code_issue_date = models.DateField(null=True)
    token_valid = models.BooleanField(default=False)
    token_error = models.CharField(max_length=30, blank=True)
    token_json = models.JSONField(null=True, blank=True)
    no_lab_data = models.BooleanField(default=True)
    status = models.CharField(max_length=12, default="unlocked")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "item"], name="uniq_student_item")]
        indexes = [models.Index(fields=["student", "item"])]


class BankQuestion(models.Model):
    """Theory bank (schema 3.9), imported from virtulab_data/question_bank.json."""
    qid = models.CharField(max_length=40, unique=True)
    experiment = models.CharField(max_length=40)
    subject = models.CharField(max_length=30)
    item_key = models.CharField(max_length=40, db_index=True)
    radical = models.CharField(max_length=12, null=True, blank=True, db_index=True)
    test_type = models.CharField(max_length=30)
    difficulty = models.CharField(max_length=10)
    lang = models.CharField(max_length=8, default="en")
    question = models.TextField()
    options = models.JSONField()
    correct_answer = models.TextField()
    explanation = models.TextField(blank=True)
    active = models.BooleanField(default=True)


class QuizAttempt(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attempts")
    redemption = models.ForeignKey(Redemption, on_delete=models.CASCADE, related_name="attempts")
    is_practice = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, default="in_progress")   # in_progress / submitted
    correct_count = models.PositiveSmallIntegerField(default=0)
    total = models.PositiveSmallIntegerField(default=0)
    points_awarded = models.IntegerField(default=0)
    partial_dynamic = models.BooleanField(default=False)
    no_lab_data = models.BooleanField(default=False)
    seed = models.CharField(max_length=64, blank=True)
    config_json = models.JSONField(default=dict, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["student"]), models.Index(fields=["redemption"])]
        constraints = [models.UniqueConstraint(fields=["redemption"], condition=models.Q(is_practice=False),
                                               name="one_graded_attempt_per_redemption")]


class QuizQuestion(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="questions")
    position = models.PositiveSmallIntegerField()
    source = models.CharField(max_length=10)                # bank / dynamic
    template = models.CharField(max_length=10, blank=True)  # DQ-01 ...
    bank_question = models.ForeignKey(BankQuestion, null=True, blank=True, on_delete=models.SET_NULL)
    test_type = models.CharField(max_length=30, blank=True)
    radical = models.CharField(max_length=12, null=True, blank=True)
    difficulty = models.CharField(max_length=10, blank=True)
    question_json = models.JSONField()                      # frozen at quiz start (question, options, explanation)
    correct_answer = models.TextField()                     # never sent to the client before submit

    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "position"], name="uniq_attempt_position")]


class Answer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="answers")
    chosen = models.TextField()
    is_correct = models.BooleanField(default=False)
    time_ms = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "question"], name="uniq_answer")]


class PointsLedger(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ledger")
    delta = models.IntegerField()
    reason = models.CharField(max_length=30)
    ref_id = models.CharField(max_length=40)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "reason", "ref_id"], name="uniq_ledger_entry")]  # idempotent
        indexes = [models.Index(fields=["student"])]


class Badge(models.Model):
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=200, blank=True)
    rule_json = models.JSONField()
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "key"]


class UserBadge(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    ref = models.CharField(max_length=40, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "badge"], name="uniq_user_badge")]


class InvalidAttempt(models.Model):
    """Failed codes, bad tokens, failed logins and join codes. Feeds rate limiting and the audit page."""
    kind = models.CharField(max_length=10)                  # code / token / login / join
    student = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    student_id_text = models.CharField(max_length=60, blank=True)
    code_text = models.CharField(max_length=80, blank=True)
    reason = models.CharField(max_length=30)
    ip = models.CharField(max_length=45, blank=True)
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["kind", "ts"]), models.Index(fields=["student_id_text"])]


class AuditLog(models.Model):
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    actor_text = models.CharField(max_length=60, blank=True)
    action = models.CharField(max_length=40)
    detail_json = models.JSONField(default=dict, blank=True)
    ts = models.DateTimeField(auto_now_add=True)
