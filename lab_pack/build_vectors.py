"""
lab_pack/build_vectors.py  --  (re)generate test_vectors.json and virtulab_data/quiz_map.json.
Only needed if the contract changes. The vectors use a FAKE test secret.
"""
import datetime as dt
import json
from pathlib import Path

try:
    from .token_codec import build_token
    from .verify_code import (ITEM_PAIRS, compute_chk, generate_code, hmac_digest, hmac_message,
                              normalise_student_id)
except ImportError:
    from token_codec import build_token
    from verify_code import (ITEM_PAIRS, compute_chk, generate_code, hmac_digest, hmac_message,
                             normalise_student_id)

SECRET = "VIRTULAB-TEST-SECRET-NOT-REAL"
TODAY = dt.date(2026, 10, 19)
D = lambda s: dt.date.fromisoformat(s)

SALT_NAMES = {
    "nacl": ("NaCl", "Sodium chloride"), "nh4cl": ("NH4Cl", "Ammonium chloride"),
    "cuso4": ("CuSO4", "Copper sulphate"), "feso4": ("FeSO4", "Iron(II) sulphate"),
    "fecl3": ("FeCl3", "Iron(III) chloride"), "al2so43": ("Al2(SO4)3", "Aluminium sulphate"),
    "znso4": ("ZnSO4", "Zinc sulphate"), "bacl2": ("BaCl2", "Barium chloride"),
    "caco3": ("CaCO3", "Calcium carbonate"), "mgso4": ("MgSO4", "Magnesium sulphate"),
    "pbno32": ("Pb(NO3)2", "Lead nitrate"), "nh42co3": ("(NH4)2CO3", "Ammonium carbonate"),
}


def chk_row(student, item, nonce, date):
    s = normalise_student_id(student)
    msg = hmac_message(s, item, nonce, D(date))
    return {"student_raw": student, "student": s, "item": item, "nonce": nonce, "date": date,
            "hmac_message": msg, "hmac_sha256_hex": hmac_digest(SECRET, msg).hex(),
            "chk": compute_chk(SECRET, student, item, nonce, D(date)),
            "code": generate_code(student, item, SECRET, D(date), nonce)}


def main():
    here = Path(__file__).parent
    quiz_map = {i: {"salt": SALT_NAMES[i][0], "name": SALT_NAMES[i][1],
                    "cation": c, "anion": a, "quiz_code": f"{c}-{a}"} for i, (c, a) in ITEM_PAIRS.items()}
    (here.parent / "virtulab_data").mkdir(exist_ok=True)
    (here.parent / "virtulab_data" / "quiz_map.json").write_text(
        json.dumps(quiz_map, indent=2) + "\n", encoding="utf-8")

    chk = [
        chk_row("2411021061202", "cuso4", "7K3Q", "2026-10-19"),
        chk_row("2411021061202", "nacl", "0000", "2026-10-19"),
        chk_row("21CS045", "feso4", "ZZZZ", "2026-10-01"),
        chk_row("21CS045", "fecl3", "A1B2", "2026-10-01"),
        chk_row("  24 11021 061202 ", "nh4cl", "9F2A", "2026-10-18"),
        chk_row("abc-123/x", "pbno32", "R8T5", "2026-10-20"),
        chk_row("2411021061202", "nh42co3", "QWER", "2026-09-19"),
        chk_row("2411021061202", "al2so43", "H4J5", "2026-10-19"),
        chk_row("2411021061202", "znso4", "K6M7", "2026-10-19"),
        chk_row("2411021061202", "bacl2", "N8P9", "2026-10-19"),
        chk_row("2411021061202", "caco3", "S2V3", "2026-10-19"),
        chk_row("2411021061202", "mgso4", "W4X5", "2026-10-19"),
    ]
    code = {r["item"] + "@" + r["date"]: r["code"] for r in chk}
    good = chk[0]
    other = chk[2]

    def flip(c):  # change one character of the CHK part
        return c[:-1] + ("0" if c[-1] != "0" else "1")

    reject = [
        {"why": "wrong student", "code": good["code"], "student": "2411021061203", "reason": "checksum_mismatch"},
        {"why": "tampered checksum", "code": flip(good["code"]), "student": good["student"], "reason": "checksum_mismatch"},
        {"why": "expired (issued 31 days ago)", "code": chk_row("2411021061202", "nacl", "E1E1", "2026-09-18")["code"],
         "student": "2411021061202", "reason": "checksum_mismatch"},
        {"why": "too far in the future (2 days ahead)", "code": chk_row("2411021061202", "nacl", "F2F2", "2026-10-21")["code"],
         "student": "2411021061202", "reason": "checksum_mismatch"},
        {"why": "pair not in table", "code": "VL-NA-SO4-7K3Q-9F2A", "student": "2411021061202", "reason": "unknown_pair"},
        {"why": "missing a part", "code": "VL-NA-CL-7K3Q", "student": "2411021061202", "reason": "bad_format"},
        {"why": "wrong prefix", "code": "XX-NA-CL-7K3Q-9F2A", "student": "2411021061202", "reason": "bad_format"},
        {"why": "letter U is not in the alphabet", "code": "VL-NA-CL-7U3Q-9F2A", "student": "2411021061202", "reason": "bad_format"},
        {"why": "empty student", "code": good["code"], "student": "   ", "reason": "empty_student_id"},
        {"why": "pipe in student id", "code": good["code"], "student": "AB|C", "reason": "invalid_student_id"},
    ]
    zero = chk[1]["code"]                      # nonce 0000
    accept = [
        {"why": "plain", "code": good["code"], "student": good["student_raw"], "item": "cuso4", "today": "2026-10-19"},
        {"why": "lower case + spaces + student id with spaces", "code": " " + good["code"].lower() + " ",
         "student": " 24110 21061202", "item": "cuso4", "today": "2026-10-19"},
        {"why": "en-dashes from phone auto-correct", "code": good["code"].replace("-", "\u2013"),
         "student": good["student"], "item": "cuso4", "today": "2026-10-19"},
        {"why": "letter O typed for zero in NONCE", "code": zero.replace("-0000-", "-OOOO-"),
         "student": "2411021061202", "item": "nacl", "today": "2026-10-19"},
        {"why": "oldest allowed date (today - 30 days)", "code": chk[6]["code"], "student": "2411021061202",
         "item": "nh42co3", "today": "2026-10-19"},
        {"why": "newest allowed date (today + 1 day, clock drift)", "code": chk[5]["code"], "student": "abc-123/x",
         "item": "pbno32", "today": "2026-10-19"},
        {"why": "iron(II) vs iron(III) are different items", "code": other["code"], "student": "21CS045",
         "item": "feso4", "today": "2026-10-19"},
    ]
    for r in chk:
        if r["item"] not in {a["item"] for a in accept}:
            accept.append({"why": "every item resolves", "code": r["code"], "student": r["student_raw"],
                           "item": r["item"], "today": "2026-10-19"})

    stu = "2411021061202"
    c1 = generate_code(stu, "cuso4", SECRET, D("2026-10-19"), "7K3Q")
    c2 = generate_code("21CS045", "feso4", SECRET, D("2026-10-19"), "M3M3")
    flawless = {"v": 1, "student": stu, "item": "cuso4", "code": c1, "issued": 1792400000, "att": 1,
                "passed": True, "dur_s": 540, "tests": [{"r": "naoh", "d": 3, "n": 1}, {"r": "nh4oh", "d": 4, "n": 2}],
                "flame": True, "heat": False, "gas": [], "mis": [], "wrong": []}
    messy = {"v": 1, "student": "21CS045", "item": "feso4", "code": c2, "issued": 1792400500, "att": 3,
             "passed": True, "dur_s": 1320, "tests": [{"r": "naoh", "d": 12, "n": 1}, {"r": "kmno4", "d": 2, "n": 2}],
             "flame": False, "heat": True, "gas": ["so2"], "mis": ["reagent_excess", "skipped_flame", "wrong_submission"],
             "wrong": [{"cat": "FE3", "an": "SO4"}, {"cat": "CU", "an": "SO4"}]}
    t1, t2 = build_token(flawless, SECRET), build_token(messy, SECRET)

    def tamper(t):
        head, body, sig = t.split(".")
        return ".".join([head, body[:-2] + ("AA" if body[-2:] != "AA" else "BB"), sig])

    bad_ver = build_token({**flawless, "v": 2}, SECRET, validate=False)
    bad_mis = build_token({**flawless, "mis": ["made_up_mistake"]}, SECRET, validate=False)
    bad_pair = build_token({**flawless, "item": "nacl"}, SECRET, validate=False)
    extra = build_token({**flawless, "note": "free text"}, SECRET, validate=False)
    token_accept = [
        {"why": "flawless run", "token": t1, "student": stu, "code": c1, "payload": flawless},
        {"why": "mistakes + wrong submissions; student typed with spaces/lower case",
         "token": t2, "student": " 21cs 045", "code": c2.lower(), "payload": messy},
    ]
    token_reject = [
        {"why": "one character of the payload changed", "token": tamper(t1), "student": stu, "code": c1, "reason": "bad_signature"},
        {"why": "signed with a different secret", "token": build_token(flawless, "ANOTHER-SECRET"), "student": stu, "code": c1, "reason": "bad_signature"},
        {"why": "token belongs to another student", "token": t1, "student": "2411021061203", "code": c1, "reason": "wrong_student"},
        {"why": "token does not match the redeemed code", "token": t1, "student": stu, "code": c2, "reason": "wrong_code"},
        {"why": "unsupported version", "token": bad_ver, "student": stu, "code": c1, "reason": "unsupported_version"},
        {"why": "mistake id not in the enum", "token": bad_mis, "student": stu, "code": c1, "reason": "unknown_mistake"},
        {"why": "item does not match the code", "token": bad_pair, "student": stu, "code": c1, "reason": "item_code_mismatch"},
        {"why": "extra field (free text is not allowed)", "token": extra, "student": stu, "code": c1, "reason": "unknown_field"},
        {"why": "wrong prefix", "token": t1.replace("VLR1", "VLR2", 1), "student": stu, "code": c1, "reason": "bad_format"},
    ]

    out = {
        "vector_version": 1,
        "WARNING": "test_secret is FAKE. Never use it for real students. The real secret is shared privately and is never committed.",
        "test_secret": SECRET,
        "today_ist": TODAY.isoformat(),
        "window": {"days_back": 30, "days_forward": 1},
        "student_id_normalisation": [
            {"raw": "2411021061202", "normalised": "2411021061202"},
            {"raw": "  24 11021 061202  ", "normalised": "2411021061202"},
            {"raw": "21cs045", "normalised": "21CS045"},
            {"raw": "a b\tc", "normalised": "ABC"},
            {"raw": "abc-123/x", "normalised": "ABC-123/X"},
        ],
        "student_id_invalid": ["", "   ", "AB|C", "A" * 41],
        "chk": chk,
        "code_accept": accept,
        "code_reject": reject,
        "token_accept": token_accept,
        "token_reject": token_reject,
    }
    (here / "test_vectors.json").write_text(json.dumps(out, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print("wrote test_vectors.json and ../virtulab_data/quiz_map.json")


if __name__ == "__main__":
    main()
