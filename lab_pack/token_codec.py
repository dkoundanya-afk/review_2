"""
lab_pack/token_codec.py  --  VirtuLab result token (VLR1): reference implementation.

Token:  VLR1.<base64url(zlib(json))>.<sig>        (base64url WITHOUT '=' padding)
  sig = base64url( first 16 bytes of HMAC-SHA256(secret, COMPRESSED_BYTES) )
  COMPRESSED_BYTES = exactly the bytes that sit (base64url-encoded) in the middle part.
  The signature is checked BEFORE anything is decompressed or parsed.

Different zlib builds produce different compressed bytes for the same JSON, so two
implementations never compare compressed bytes. They verify each other's tokens.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import zlib

try:                                    # works as a package or as a plain script folder
    from .verify_code import ITEM_PAIRS, CodeError, normalise_student_id, parse_code
except ImportError:
    from verify_code import ITEM_PAIRS, CodeError, normalise_student_id, parse_code

PREFIX = "VLR1"
SUPPORTED_VERSION = 1
SIG_BYTES = 16
MAX_COMPRESSED_BUILD = 1536        # spec: <= 1.5 KB after compression
MAX_COMPRESSED_PARSE = 4096        # parser tolerance
MAX_JSON_BYTES = 8192              # decompression-bomb guard

MISTAKES = (
    "order_wrong", "reagent_excess", "skipped_flame", "skipped_confirmatory",
    "skipped_dissolve", "repeated_same_test", "wrong_reagent_for_goal", "wrong_submission",
)

_B64U_RE = re.compile(r"^[A-Za-z0-9_-]*$")
_REAGENT_RE = re.compile(r"^[a-z0-9_]{1,32}$")
_GAS_RE = re.compile(r"^[a-z0-9_]{1,16}$")
_ION_RE = re.compile(r"^[A-Z0-9]{1,4}$")
_ALLOWED_KEYS = {"v", "student", "item", "code", "issued", "att", "passed",
                 "dur_s", "tests", "flame", "heat", "gas", "mis", "wrong"}


class TokenError(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64u_decode(text: str) -> bytes:
    if not _B64U_RE.match(text) or len(text) % 4 == 1:
        raise TokenError("bad_encoding")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sig(secret: str, compressed: bytes) -> bytes:
    return hmac.new(secret.encode("utf-8"), compressed, hashlib.sha256).digest()[:SIG_BYTES]


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _need(cond: bool, reason: str = "bad_payload") -> None:
    if not cond:
        raise TokenError(reason)


def validate_payload(p: dict, items: dict | None = None) -> dict:
    """Strict v1 schema. Returns a copy with defaults filled. Raises TokenError.
    items: optional {item_id: (CATION, ANION)}; defaults to the built-in table."""
    items = ITEM_PAIRS if items is None else items
    _need(isinstance(p, dict))
    _need(set(p) <= _ALLOWED_KEYS, "unknown_field")
    _need(_is_int(p.get("v")) and p["v"] == SUPPORTED_VERSION, "unsupported_version")
    for key in ("student", "item", "code", "issued", "att", "passed"):
        _need(key in p)
    out = {"v": 1}
    _need(isinstance(p["student"], str))
    try:
        out["student"] = normalise_student_id(p["student"])
    except ValueError:
        raise TokenError("bad_payload")
    _need(isinstance(p["item"], str) and p["item"] in items)
    out["item"] = p["item"]
    _need(isinstance(p["code"], str))
    try:
        parsed = parse_code(p["code"])
    except CodeError:
        raise TokenError("bad_payload")
    _need((parsed.cation, parsed.anion) == tuple(items[p["item"]]), "item_code_mismatch")
    out["code"] = parsed.canonical
    _need(_is_int(p["issued"]) and p["issued"] >= 0)
    out["issued"] = p["issued"]
    _need(_is_int(p["att"]) and 1 <= p["att"] <= 99)
    out["att"] = p["att"]
    _need(isinstance(p["passed"], bool))
    out["passed"] = p["passed"]
    dur = p.get("dur_s", 0)
    _need(_is_int(dur) and 0 <= dur <= 86400)
    out["dur_s"] = dur
    tests = p.get("tests", [])
    _need(isinstance(tests, list) and len(tests) <= 40)
    for t in tests:
        _need(isinstance(t, dict) and set(t) == {"r", "d", "n"})
        _need(isinstance(t["r"], str) and _REAGENT_RE.match(t["r"]))
        _need(_is_int(t["d"]) and 0 <= t["d"] <= 999)
        _need(_is_int(t["n"]) and 1 <= t["n"] <= 99)
    out["tests"] = [dict(t) for t in tests]
    for flag in ("flame", "heat"):
        val = p.get(flag, False)
        _need(isinstance(val, bool))
        out[flag] = val
    gas = p.get("gas", [])
    _need(isinstance(gas, list) and len(gas) <= 10)
    _need(all(isinstance(g, str) and _GAS_RE.match(g) for g in gas))
    out["gas"] = list(gas)
    mis = p.get("mis", [])
    _need(isinstance(mis, list) and len(mis) <= 20)
    _need(all(isinstance(m, str) and m in MISTAKES for m in mis), "unknown_mistake")
    out["mis"] = list(mis)
    wrong = p.get("wrong", [])
    _need(isinstance(wrong, list) and len(wrong) <= 20)
    for w in wrong:
        _need(isinstance(w, dict) and set(w) == {"cat", "an"})
        _need(all(isinstance(w[k], str) and _ION_RE.match(w[k]) for k in ("cat", "an")))
    out["wrong"] = [dict(w) for w in wrong]
    return out


def build_token(payload: dict, secret: str, validate: bool = True) -> str:
    if validate:
        payload = validate_payload(payload)
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True).encode("ascii")
    compressed = zlib.compress(raw, 9)
    if validate and len(compressed) > MAX_COMPRESSED_BUILD:
        raise TokenError("too_large")
    return f"{PREFIX}.{b64u_encode(compressed)}.{b64u_encode(_sig(secret, compressed))}"


def parse_token(token: str, secret: str, expected_student: str | None = None,
                expected_code: str | None = None, items: dict | None = None) -> dict:
    """Verify and decode. Raises TokenError(reason) on ANY problem; the portal then
    ignores the token and falls back to a bank-only quiz."""
    _need(isinstance(token, str), "bad_format")
    parts = "".join(token.split()).split(".")
    _need(len(parts) == 3 and parts[0] == PREFIX, "bad_format")
    compressed = b64u_decode(parts[1])
    sig = b64u_decode(parts[2])
    _need(len(compressed) <= MAX_COMPRESSED_PARSE, "too_large")
    _need(hmac.compare_digest(sig, _sig(secret, compressed)), "bad_signature")
    d = zlib.decompressobj()
    try:
        raw = d.decompress(compressed, MAX_JSON_BYTES + 1)
        _need(len(raw) <= MAX_JSON_BYTES and not d.unconsumed_tail, "too_large")
        raw += d.flush()
    except zlib.error:
        raise TokenError("bad_compression")
    _need(d.eof and len(raw) <= MAX_JSON_BYTES, "bad_compression")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise TokenError("bad_json")
    payload = validate_payload(payload, items)
    if expected_student is not None:
        try:
            ok = normalise_student_id(expected_student) == payload["student"]
        except ValueError:
            ok = False
        _need(ok, "wrong_student")
    if expected_code is not None:
        try:
            ok = parse_code(expected_code).canonical == payload["code"]
        except CodeError:
            ok = False
        _need(ok, "wrong_code")
    return payload
