"""
lab_pack/generate_demo.py  --  make a completion code + result token for development.

  python lab_pack/generate_demo.py --student 2411021061202 --item cuso4 --use-test-secret
  python lab_pack/generate_demo.py --student 21CS045 --item nacl --att 2 \
         --mis reagent_excess,skipped_flame --wrong CU:SO4 --use-test-secret

Without --use-test-secret the secret is read from the HMAC_SECRET environment variable.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time

try:
    from .token_codec import build_token
    from .verify_code import generate_code, ist_today, load_secret, normalise_student_id
except ImportError:
    from token_codec import build_token
    from verify_code import generate_code, ist_today, load_secret, normalise_student_id


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--student", required=True)
    ap.add_argument("--item", required=True)
    ap.add_argument("--date", help="issue date YYYY-MM-DD (default: today in IST)")
    ap.add_argument("--att", type=int, default=1, help="attempts in the lab")
    ap.add_argument("--passed", type=lambda s: s.lower() != "false", default=True)
    ap.add_argument("--dur", type=int, default=600, help="seconds")
    ap.add_argument("--mis", default="", help="comma list of mistake ids")
    ap.add_argument("--wrong", default="", help="comma list of CATION:ANION wrong submissions, e.g. CU:SO4")
    ap.add_argument("--no-flame", action="store_true")
    ap.add_argument("--use-test-secret", action="store_true")
    a = ap.parse_args()

    secret = load_secret(a.use_test_secret)
    issue = dt.date.fromisoformat(a.date) if a.date else ist_today()
    code = generate_code(a.student, a.item, secret, issue)
    payload = {
        "v": 1, "student": normalise_student_id(a.student), "item": a.item, "code": code,
        "issued": int(time.time()), "att": a.att, "passed": a.passed, "dur_s": a.dur,
        "tests": [{"r": "naoh", "d": 3, "n": 1}, {"r": "nh4oh", "d": 5, "n": 2}],
        "flame": not a.no_flame, "heat": False, "gas": [],
        "mis": [m for m in a.mis.split(",") if m],
        "wrong": [{"cat": w.split(":")[0], "an": w.split(":")[1]} for w in a.wrong.split(",") if w],
    }
    print("CODE :", code)
    print("TOKEN:", build_token(payload, secret))
    print("PAYLOAD:", json.dumps(payload))


if __name__ == "__main__":
    main()
