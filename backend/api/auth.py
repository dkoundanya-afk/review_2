"""Sessions (expiring bearer tokens), role permissions and small helpers."""
import hashlib
import re
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from lab_pack.verify_code import normalise_student_id

from .conf import cfg
from .models import AuthToken

STUDENT_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._/-]{0,39}$")   # portal-side rule: no '@', no spaces, no '|'
PIN_RE = re.compile(r"^\d{4,6}$")
JOIN_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def issue_token(user) -> str:
    key = secrets.token_hex(24)
    days = cfg("auth", "token_days", default=14)
    AuthToken.objects.create(user=user, key_hash=_hash(key), expires=timezone.now() + timedelta(days=days))
    return key


class TokenAuth(BaseAuthentication):
    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        key = header[7:].strip()
        tok = AuthToken.objects.select_related("user", "user__profile").filter(key_hash=_hash(key)).first()
        if tok is None or tok.expires <= timezone.now() or not tok.user.is_active:
            raise AuthenticationFailed("invalid_token")
        if not hasattr(tok.user, "profile"):
            raise AuthenticationFailed("no_profile")
        return tok.user, tok

    def authenticate_header(self, request):
        return "Bearer"


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.profile.role == "student")


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.profile.role == "teacher")


def client_ip(request) -> str:
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR", ""))[:45]


def clean_student_id(raw) -> str:
    """Lab normalisation (spec 3.3) + the portal's stricter character rule. Raises ValueError."""
    sid = normalise_student_id(str(raw or ""))
    if not STUDENT_ID_RE.match(sid):
        raise ValueError("invalid_student_id")
    return sid


def new_join_code() -> str:
    from .models import ClassRoom
    while True:
        code = "".join(secrets.choice(JOIN_ALPHABET) for _ in range(6))
        if not ClassRoom.objects.filter(join_code=code).exists():
            return code


def norm_join_code(raw) -> str:
    return "".join(str(raw or "").split()).upper()
