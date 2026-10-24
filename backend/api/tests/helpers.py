import datetime as dt

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.test import APIClient

from api.models import ClassRoom, Profile
from api.auth import new_join_code
from lab_pack.token_codec import build_token
from lab_pack.verify_code import generate_code, ist_today, normalise_student_id


def load_all():
    call_command("load_data", verbosity=0)


def make_teacher(email="t1@school.in", password="teacher-pass-1"):
    u = User.objects.create_user(username=email, password=password, email=email)
    Profile.objects.create(user=u, role="teacher", display_name="Teacher " + email)
    return u


def make_class(teacher, name="PU1-A"):
    return ClassRoom.objects.create(teacher=teacher, name=name, join_code=new_join_code())


def api(token=None):
    c = APIClient()
    if token:
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return c


def register(join_code, student_id="2411021061202", pin="4321", name="Asha"):
    r = api().post("/api/auth/register", {"student_id": student_id, "join_code": join_code, "pin": pin,
                                           "display_name": name}, format="json")
    return r


def code_for(student_id, item, issue=None, nonce=None):
    return generate_code(student_id, item, settings.HMAC_SECRET, issue or ist_today(), nonce)


def token_for(student_id, item, code, **over):
    payload = {"v": 1, "student": normalise_student_id(student_id), "item": item, "code": code,
               "issued": 1792400000, "att": 1, "passed": True, "dur_s": 500,
               "tests": [{"r": "naoh", "d": 3, "n": 1}], "flame": True, "heat": False, "gas": [], "mis": [], "wrong": []}
    payload.update(over)
    return build_token(payload, settings.HMAC_SECRET)


def days_ago(n):
    return ist_today() - dt.timedelta(days=n)
