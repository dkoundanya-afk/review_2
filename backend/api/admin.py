from django.contrib import admin

from . import models

for m in (models.Experiment, models.Item, models.Profile, models.ClassRoom, models.Enrollment, models.Redemption,
          models.BankQuestion, models.Badge, models.UserBadge, models.PointsLedger, models.QuizAttempt,
          models.InvalidAttempt, models.AuditLog):
    admin.site.register(m)
