"""
lab_pack/verify_code.py  --  VirtuLab completion code: reference implementation.

This is the REFERENCE. The Unity lab must produce byte-identical results for the
vectors in test_vectors.json. Standard library only (Python 3.11+).

Code format:   VL-<CATION>-<ANION>-<NONCE>-<CHK>      e.g. VL-NA-CL-7K3Q-9F2A
  CATION, ANION : 2-3 chars of A-Z0-9, looked up in ITEM_PAIRS (below)
  NONCE         : 4 random Crockford base32 characters
  CHK           : first 4 Crockford base32 characters of
                  HMAC-SHA256(secret, STUDENTID|ITEMID|NONCE|YYYYMMDD)
                  (= the first 20 bits of the digest, 5 bits per character)
The date is the ISSUE date in IST (UTC+05:30), NOT the device's local time zone.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path

CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # no I, L, O, U
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
MAX_STUDENT_ID_LEN = 40

# item id -> (CATION, ANION).  Must equal virtulab_data/quiz_map.json (tested).
ITEM_PAIRS: dict[str, tuple[str, str]] = {
    "nacl":    ("NA",  "CL"),
    "nh4cl":   ("NH4", "CL"),
    "cuso4":   ("CU",  "SO4"),
    "feso4":   ("FE2", "SO4"),
    "fecl3":   ("FE3", "CL"),
    "al2so43": ("AL",  "SO4"),
    "znso4":   ("ZN",  "SO4"),
    "bacl2":   ("BA",  "CL"),
    "caco3":   ("CA",  "CO3"),
    "mgso4":   ("MG",  "SO4"),
    "pbno32":  ("PB",  "NO3"),
    "nh42co3": ("NH4", "CO3"),
}
PAIR_TO_ITEM = {pair: item for item, pair in ITEM_PAIRS.items()}
assert len(PAIR_TO_ITEM) == len(ITEM_PAIRS), "each cation/anion pair must be unique"


class CodeError(ValueError):
    """Raised for a malformed code. .reason is a short machine-readable string."""
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ParsedCode:
    cation: str
    anion: str
    nonce: str
    chk: str

    @property
    def canonical(self) -> str:
        return f"VL-{self.cation}-{self.anion}-{self.nonce}-{self.chk}"


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    reason: str                       # "ok" or a failure reason
    item_id: str | None = None
    issue_date: dt.date | None = None
    canonical_code: str | None = None


# ---------------------------------------------------------------- student ID
def normalise_student_id(raw: str) -> str:
    """Trim, remove ALL whitespace, upper-case. Raises ValueError if unusable."""
    s = "".join(raw.split()).upper()
    if not s:
        raise ValueError("empty_student_id")
    if "|" in s or len(s) > MAX_STUDENT_ID_LEN or any(ord(c) < 32 or ord(c) == 127 for c in s):
        raise ValueError("invalid_student_id")
    return s


# ----------------------------------------------------------------- checksum
def hmac_message(student_norm: str, item_id: str, nonce: str, issue_date: dt.date) -> str:
    return f"{student_norm}|{item_id}|{nonce}|{issue_date:%Y%m%d}"


def hmac_digest(secret: str, message: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).digest()


def crockford4(digest: bytes) -> str:
    """First 20 bits of the digest as 4 Crockford base32 characters."""
    n = int.from_bytes(digest[:3], "big") >> 4          # keep the top 20 of 24 bits
    return "".join(CROCKFORD[(n >> shift) & 31] for shift in (15, 10, 5, 0))


def compute_chk(secret: str, student_id: str, item_id: str, nonce: str, issue_date: dt.date) -> str:
    msg = hmac_message(normalise_student_id(student_id), item_id, nonce, issue_date)
    return crockford4(hmac_digest(secret, msg))


# ------------------------------------------------------------------ generate
def new_nonce() -> str:
    return "".join(secrets.choice(CROCKFORD) for _ in range(4))


def generate_code(student_id: str, item_id: str, secret: str,
                  issue_date: dt.date | None = None, nonce: str | None = None) -> str:
    if item_id not in ITEM_PAIRS:
        raise CodeError("unknown_item")
    issue_date = issue_date or ist_today()
    nonce = nonce or new_nonce()
    if len(nonce) != 4 or any(c not in CROCKFORD for c in nonce):
        raise CodeError("bad_nonce")
    cation, anion = ITEM_PAIRS[item_id]
    chk = compute_chk(secret, student_id, item_id, nonce, issue_date)
    return ParsedCode(cation, anion, nonce, chk).canonical


# --------------------------------------------------------------------- parse
_DASHES = {ord(c): "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2212"}   # phone auto-correct
_CONFUSABLE = {ord("O"): "0", ord("I"): "1", ord("L"): "1"}              # Crockford decoding


def parse_code(raw: str) -> ParsedCode:
    s = "".join(raw.split()).translate(_DASHES).upper()
    parts = s.split("-")
    if len(parts) != 5 or parts[0] != "VL":
        raise CodeError("bad_format")
    _, cation, anion, nonce, chk = parts
    for seg in (cation, anion):
        if not (2 <= len(seg) <= 3 and seg.isascii() and seg.isalnum()):
            raise CodeError("bad_format")
    # O/I/L are mapped ONLY in NONCE and CHK (a real anion is called NO3).
    nonce, chk = nonce.translate(_CONFUSABLE), chk.translate(_CONFUSABLE)
    for seg in (nonce, chk):
        if len(seg) != 4 or any(c not in CROCKFORD for c in seg):
            raise CodeError("bad_format")
    return ParsedCode(cation, anion, nonce, chk)


# -------------------------------------------------------------------- verify
def ist_today(now_utc: dt.datetime | None = None) -> dt.date:
    now_utc = now_utc or dt.datetime.now(dt.timezone.utc)
    return now_utc.astimezone(IST).date()


def verify_code(code: str, student_id: str, secret: str, today: dt.date | None = None,
                window_days: int = 30, drift_days: int = 1,
                pair_to_item: dict | None = None) -> VerifyResult:
    """Check a code for the logged-in student. Accepts issue dates from
    (today - window_days) to (today + drift_days), inclusive.
    Single use and rate limiting are the PORTAL's job (database), not done here.
    pair_to_item: optional {(CATION, ANION): item_id}; defaults to the built-in table.
    The portal passes the table it loaded from the database so new experiments need no code."""
    today = today or ist_today()
    pair_to_item = PAIR_TO_ITEM if pair_to_item is None else pair_to_item
    try:
        p = parse_code(code)
    except CodeError as e:
        return VerifyResult(False, e.reason)
    item_id = pair_to_item.get((p.cation, p.anion))
    if item_id is None:
        return VerifyResult(False, "unknown_pair")
    try:
        student = normalise_student_id(student_id)
    except ValueError as e:
        return VerifyResult(False, str(e))
    for offset in range(-window_days, drift_days + 1):
        d = today + dt.timedelta(days=offset)
        expected = crockford4(hmac_digest(secret, hmac_message(student, item_id, p.nonce, d)))
        if hmac.compare_digest(expected, p.chk):
            return VerifyResult(True, "ok", item_id, d, p.canonical)
    return VerifyResult(False, "checksum_mismatch")   # wrong student, forged, or expired


# ----------------------------------------------------------------------- CLI
def load_secret(use_test_secret: bool) -> str:
    if use_test_secret:
        vec = json.loads((Path(__file__).parent / "test_vectors.json").read_text(encoding="utf-8"))
        return vec["test_secret"]
    secret = os.environ.get("HMAC_SECRET")
    if not secret:
        sys.exit("Set the HMAC_SECRET environment variable, or pass --use-test-secret (test data only).")
    return secret


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify a VirtuLab completion code.")
    ap.add_argument("--code", required=True)
    ap.add_argument("--student", required=True)
    ap.add_argument("--today", help="YYYY-MM-DD (default: today in IST)")
    ap.add_argument("--use-test-secret", action="store_true")
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today) if a.today else None
    r = verify_code(a.code, a.student, load_secret(a.use_test_secret), today)
    print(f"ok={r.ok} reason={r.reason} item={r.item_id} issued={r.issue_date}")
    sys.exit(0 if r.ok else 1)


if __name__ == "__main__":
    main()
