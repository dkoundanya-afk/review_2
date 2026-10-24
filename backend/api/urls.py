from django.urls import path

from . import views as v
from . import views_quiz as vq

urlpatterns = [
    path("health/", v.health),
    path("auth/register", v.register),
    path("auth/login", v.login),
    path("auth/logout", v.logout),
    path("auth/change-pin", v.change_pin),
    path("me", v.me),
    path("me/language", v.set_language),
    path("progress", v.progress),
    path("classes/join", v.join_class),
    path("redeem", v.redeem),
    path("quiz/start", vq.quiz_start),
    path("quiz/<int:pk>", vq.quiz_detail),
    path("quiz/<int:pk>/answers", vq.quiz_answers),
    path("quiz/<int:pk>/submit", vq.quiz_submit),
    path("quiz/<int:pk>/result", vq.quiz_result),
    path("history", vq.history),
    path("teacher/classes", v.teacher_classes),
    path("teacher/classes/<int:pk>", v.teacher_class_detail),
    path("teacher/classes/<int:pk>/overview", v.teacher_class_overview),
    path("teacher/classes/<int:pk>/learning-insights", v.teacher_class_learning_insights),
    path("teacher/classes/<int:pk>/students", v.teacher_students),
    path("teacher/classes/<int:pk>/students/<str:sid>/reset-pin", v.teacher_reset_pin),
    path("teacher/classes/<int:pk>/export/roster", v.teacher_export_roster),
    path("teacher/classes/<int:pk>/export/quiz-results", v.teacher_export_quiz_results),
    path("teacher/classes/<int:pk>/export/practical-records", v.teacher_export_practical_records),
    path("teacher/classes/<int:pk>/export/salt-performance", v.teacher_export_salt_performance),
    path("teacher/classes/<int:pk>/export/learning-insights", v.teacher_export_learning_insights),
]
