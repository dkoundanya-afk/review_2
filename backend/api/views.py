"""HTTP layer (spec section 5). Thin: validation + calls into services.py."""
import secrets

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Max
from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .auth import (PIN_RE, IsStudent, IsTeacher, clean_student_id, client_ip, issue_token, new_join_code,
                   norm_join_code)
from .errors import ApiError
from .models import AuthToken, ClassRoom, Enrollment, Profile, Redemption
from .services import (audit, check_rate_limit, class_learning_insights_for, class_overview_for, evaluate_badges, log_invalid,
                       progress_for, redeem_code, total_points)
from .services_export import (generate_learning_insights_csv, generate_practical_records_csv, generate_quiz_results_csv,
                              generate_roster_csv, generate_salt_performance_csv)
from .conf import level_for


def _me(user) -> dict:
    p = user.profile
    classes = [{"id": e.classroom_id, "name": e.classroom.name} for e in
               user.enrollments.select_related("classroom").filter(classroom__active=True)] if p.role == "student" else []
    return {"role": p.role, "id": user.username, "display_name": p.display_name, "lang": p.lang,
            "must_change_pin": p.must_change_pin, "classes": classes}


# ------------------------------------------------------------------------------ public
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def register(request):
    """First visit: Student ID + class join code + new PIN (S-01)."""
    d, ip = request.data, client_ip(request)
    check_rate_limit("join", ip=ip, ip_factor=2)
    try:
        sid = clean_student_id(d.get("student_id"))
    except ValueError:
        raise ApiError(400, "invalid_student_id")
    pin = str(d.get("pin", ""))
    if not PIN_RE.match(pin):
        raise ApiError(400, "invalid_pin")
    classroom = ClassRoom.objects.filter(join_code=norm_join_code(d.get("join_code")), join_enabled=True, active=True).first()
    if classroom is None:
        log_invalid("join", "invalid_join_code", None, sid, "", ip)
        raise ApiError(400, "invalid_join_code")
    name = str(d.get("display_name", "")).strip()[:60]
    with transaction.atomic():
        user = User.objects.filter(username=sid).first()
        if user:
            if not hasattr(user, "profile") or user.profile.role != "student":
                raise ApiError(400, "invalid_student_id")
            if user.profile.pin_set:
                raise ApiError(409, "already_registered")
            user.set_password(pin)
            user.save()
            user.profile.pin_set, user.profile.must_change_pin = True, False
            if name:
                user.profile.display_name = name
            user.profile.save()
        else:
            user = User.objects.create_user(username=sid, password=pin)
            Profile.objects.create(user=user, role="student", display_name=name or sid)
        Enrollment.objects.get_or_create(classroom=classroom, student=user)
    audit(user, "register", classroom=classroom.id)
    return Response({"token": issue_token(user), "me": _me(user)}, status=201)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    """Student: Student ID + PIN.  Teacher: email + password (an '@' means teacher)."""
    ident, secret, ip = str(request.data.get("identifier", "")).strip(), str(request.data.get("secret", "")), client_ip(request)
    if "@" in ident:
        username, role = ident.lower()[:60], "teacher"
    else:
        try:
            username, role = clean_student_id(ident), "student"
        except ValueError:
            log_invalid("login", "invalid_credentials", None, ident[:60], "", ip)
            raise ApiError(401, "invalid_credentials")
    check_rate_limit("login", student_id_text=username, ip=ip)
    user = User.objects.filter(username=username, is_active=True).first()
    ok = bool(user and hasattr(user, "profile") and user.profile.role == role
              and user.has_usable_password() and user.check_password(secret))
    if not ok:
        log_invalid("login", "invalid_credentials", user, username, "", ip)
        raise ApiError(401, "invalid_credentials")
    audit(user, "login")
    return Response({"token": issue_token(user), "me": _me(user)})


# ---------------------------------------------------------------------------- any user
@api_view(["POST"])
def logout(request):
    request.auth.delete()
    return Response({"ok": True})


@api_view(["GET"])
def me(request):
    return Response(_me(request.user))


@api_view(["POST"])
def change_pin(request):
    d = request.data
    new = str(d.get("new_pin", ""))
    if not request.user.check_password(str(d.get("old_pin", ""))):
        raise ApiError(400, "wrong_current_pin")
    if not PIN_RE.match(new) and request.user.profile.role == "student":
        raise ApiError(400, "invalid_pin")
    if request.user.profile.role == "teacher" and len(new) < 8:
        raise ApiError(400, "weak_password")
    request.user.set_password(new)
    request.user.save()
    request.user.profile.must_change_pin = False
    request.user.profile.save()
    AuthToken.objects.filter(user=request.user).exclude(pk=request.auth.pk).delete()   # other sessions end
    audit(request.user, "change_pin")
    return Response({"ok": True})


@api_view(["PATCH"])
def set_language(request):
    lang = str(request.data.get("lang", ""))[:8]
    if not lang.isalpha():
        raise ApiError(400, "invalid_language")
    request.user.profile.lang = lang
    request.user.profile.save()
    return Response({"lang": lang})


# -------------------------------------------------------------------------------- student
@api_view(["GET"])
@permission_classes([IsStudent])
def progress(request):
    return Response(progress_for(request.user))


@api_view(["POST"])
@permission_classes([IsStudent])
def join_class(request):
    ip = client_ip(request)
    check_rate_limit("join", ip=ip, ip_factor=2)
    classroom = ClassRoom.objects.filter(join_code=norm_join_code(request.data.get("join_code")),
                                         join_enabled=True, active=True).first()
    if classroom is None:
        log_invalid("join", "invalid_join_code", request.user, request.user.username, "", ip)
        raise ApiError(400, "invalid_join_code")
    Enrollment.objects.get_or_create(classroom=classroom, student=request.user)
    audit(request.user, "join_class", classroom=classroom.id)
    return Response(_me(request.user))


@api_view(["POST"])
@permission_classes([IsStudent])
def redeem(request):
    out = redeem_code(request.user, request.data.get("code"), request.data.get("token"), client_ip(request))
    return Response(out, status=200 if out.get("already") else 201)


# -------------------------------------------------------------------------------- teacher
def _own_class(request, pk) -> ClassRoom:
    """Teacher isolation (HARD RULE 8): a class that is not yours simply does not exist."""
    c = ClassRoom.objects.filter(pk=pk, teacher=request.user).first()
    if c is None:
        raise ApiError(404, "not_found")
    return c


def _class_json(c: ClassRoom) -> dict:
    return {"id": c.id, "name": c.name, "grade": c.grade, "section": c.section, "join_code": c.join_code,
            "join_enabled": c.join_enabled, "active": c.active, "leaderboard": c.leaderboard,
            "students": c.enrollments.count()}


@api_view(["GET", "POST"])
@permission_classes([IsTeacher])
def teacher_classes(request):
    if request.method == "GET":
        qs = ClassRoom.objects.filter(teacher=request.user).order_by("-active", "name")
        return Response([_class_json(c) for c in qs])
    name = str(request.data.get("name", "")).strip()[:80]
    if not name:
        raise ApiError(400, "name_required")
    c = ClassRoom.objects.create(teacher=request.user, name=name, grade=str(request.data.get("grade", ""))[:10],
                                 section=str(request.data.get("section", ""))[:10], join_code=new_join_code())
    audit(request.user, "class_create", classroom=c.id)
    return Response(_class_json(c), status=201)


@api_view(["PATCH"])
@permission_classes([IsTeacher])
def teacher_class_detail(request, pk):
    c, d = _own_class(request, pk), request.data
    for f, n in (("name", 80), ("grade", 10), ("section", 10)):
        if f in d:
            setattr(c, f, str(d[f]).strip()[:n])
    for f in ("join_enabled", "active", "leaderboard"):
        if f in d:
            setattr(c, f, bool(d[f]))
    if d.get("rotate_join_code"):
        c.join_code = new_join_code()
    c.save()
    audit(request.user, "class_update", classroom=c.id)
    return Response(_class_json(c))


@api_view(["GET"])
@permission_classes([IsTeacher])
def teacher_students(request, pk):
    c = _own_class(request, pk)
    rows = []
    for e in c.enrollments.select_related("student", "student__profile").order_by("student__username"):
        s = e.student
        rows.append({"student_id": s.username, "display_name": s.profile.display_name, "joined_at": e.joined_at,
                     "pin_set": s.profile.pin_set, "redeemed": s.redemptions.count(),
                     "points": total_points(s), "level": level_for(total_points(s))["name"]})
    return Response(rows)


@api_view(["POST"])
@permission_classes([IsTeacher])
def teacher_reset_pin(request, pk, sid):
    c = _own_class(request, pk)
    e = c.enrollments.select_related("student__profile").filter(student__username=sid).first()
    if e is None:
        raise ApiError(404, "not_found")
    temp = "".join(secrets.choice("0123456789") for _ in range(6))
    e.student.set_password(temp)
    e.student.save()
    e.student.profile.pin_set, e.student.profile.must_change_pin = True, True
    e.student.profile.save()
    AuthToken.objects.filter(user=e.student).delete()          # log them out everywhere
    audit(request.user, "reset_pin", student=sid, classroom=c.id)
    return Response({"student_id": sid, "temporary_pin": temp})      # shown to the teacher once


@api_view(["GET"])
@permission_classes([IsTeacher])
def teacher_class_overview(request, pk):
    c = _own_class(request, pk)
    return Response(class_overview_for(c))


@api_view(["GET"])
@permission_classes([IsTeacher])
def teacher_class_learning_insights(request, pk):
    c = _own_class(request, pk)
    return Response(class_learning_insights_for(c))


# ------------------------------------------------------------------------------ CSV exports
def _csv_response(csv_text: str, filename: str) -> HttpResponse:
    """Returns downloadable CSV response with UTF-8 BOM for spreadsheet compatibility."""
    res = HttpResponse(b"\xef\xbb\xbf" + csv_text.encode("utf-8"), content_type="text/csv; charset=utf-8")
    res["Content-Disposition"] = f'attachment; filename="{filename}"'
    return res


@api_view(["GET"])
@permission_classes([IsTeacher])
def teacher_export_roster(request, pk):
    c = _own_class(request, pk)
    audit(request.user, "export_report", classroom=c.id, report_type="roster")
    filename = f"virtulab_class_{c.join_code}_roster.csv"
    return _csv_response(generate_roster_csv(c), filename)


@api_view(["GET"])
@permission_classes([IsTeacher])
def teacher_export_quiz_results(request, pk):
    c = _own_class(request, pk)
    audit(request.user, "export_report", classroom=c.id, report_type="quiz_results")
    filename = f"virtulab_class_{c.join_code}_quiz_results.csv"
    return _csv_response(generate_quiz_results_csv(c), filename)


@api_view(["GET"])
@permission_classes([IsTeacher])
def teacher_export_practical_records(request, pk):
    c = _own_class(request, pk)
    audit(request.user, "export_report", classroom=c.id, report_type="practical_records")
    filename = f"virtulab_class_{c.join_code}_practical_records.csv"
    return _csv_response(generate_practical_records_csv(c), filename)


@api_view(["GET"])
@permission_classes([IsTeacher])
def teacher_export_salt_performance(request, pk):
    c = _own_class(request, pk)
    audit(request.user, "export_report", classroom=c.id, report_type="salt_performance")
    filename = f"virtulab_class_{c.join_code}_salt_performance.csv"
    return _csv_response(generate_salt_performance_csv(c), filename)


@api_view(["GET"])
@permission_classes([IsTeacher])
def teacher_export_learning_insights(request, pk):
    c = _own_class(request, pk)
    audit(request.user, "export_report", classroom=c.id, report_type="learning_insights")
    filename = f"virtulab_class_{c.join_code}_learning_insights.csv"
    return _csv_response(generate_learning_insights_csv(c), filename)



