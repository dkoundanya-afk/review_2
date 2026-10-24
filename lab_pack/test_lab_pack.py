"""
lab_pack/test_lab_pack.py -- run from the project root:
    python -m unittest lab_pack.test_lab_pack -v
Standard library only.
"""
import base64
import datetime as dt
import json
import re
import sys
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lab_pack.token_codec import MISTAKES, TokenError, b64u_encode, build_token, parse_token, validate_payload
from lab_pack.verify_code import (CROCKFORD, ITEM_PAIRS, PAIR_TO_ITEM, CodeError, compute_chk, generate_code,
                                  hmac_digest, hmac_message, ist_today, normalise_student_id, parse_code,
                                  verify_code)

VEC = json.loads((Path(__file__).parent / "test_vectors.json").read_text(encoding="utf-8"))
SECRET = VEC["test_secret"]
TODAY = dt.date.fromisoformat(VEC["today_ist"])
D = dt.date.fromisoformat


class TestStudentId(unittest.TestCase):
    def test_vectors(self):
        for row in VEC["student_id_normalisation"]:
            self.assertEqual(normalise_student_id(row["raw"]), row["normalised"], row)

    def test_invalid(self):
        for raw in VEC["student_id_invalid"]:
            with self.assertRaises(ValueError, msg=repr(raw)):
                normalise_student_id(raw)


class TestChecksum(unittest.TestCase):
    def test_independent_derivation(self):
        """Re-derive CHK a different way: standard RFC4648 base32 of the digest, translated
        to the Crockford alphabet. Must equal the module's own bit-twiddling."""
        rfc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
        table = str.maketrans(rfc, CROCKFORD)
        for row in VEC["chk"]:
            digest = bytes.fromhex(row["hmac_sha256_hex"])
            expected = base64.b32encode(digest[:5]).decode().translate(table)[:4]
            self.assertEqual(row["chk"], expected, row["hmac_message"])

    def test_vectors_match_code(self):
        for row in VEC["chk"]:
            msg = hmac_message(normalise_student_id(row["student_raw"]), row["item"], row["nonce"], D(row["date"]))
            self.assertEqual(msg, row["hmac_message"])
            self.assertEqual(hmac_digest(SECRET, msg).hex(), row["hmac_sha256_hex"])
            self.assertEqual(compute_chk(SECRET, row["student_raw"], row["item"], row["nonce"], D(row["date"])), row["chk"])
            self.assertEqual(generate_code(row["student_raw"], row["item"], SECRET, D(row["date"]), row["nonce"]), row["code"])

    def test_known_value_is_frozen(self):
        """Fails if anyone changes the algorithm by accident."""
        self.assertEqual(
            generate_code("2411021061202", "cuso4", SECRET, D("2026-10-19"), "7K3Q"), "VL-CU-SO4-7K3Q-GCG6")


class TestVerify(unittest.TestCase):
    def test_accept_vectors(self):
        for row in VEC["code_accept"]:
            r = verify_code(row["code"], row["student"], SECRET, D(row["today"]))
            self.assertTrue(r.ok, row)
            self.assertEqual(r.item_id, row["item"], row)

    def test_reject_vectors(self):
        for row in VEC["code_reject"]:
            r = verify_code(row["code"], row["student"], SECRET, TODAY)
            self.assertFalse(r.ok, row)
            self.assertEqual(r.reason, row["reason"], row)

    def test_window_edges(self):
        for offset, ok in [(-31, False), (-30, True), (0, True), (1, True), (2, False)]:
            c = generate_code("S1", "nacl", SECRET, TODAY + dt.timedelta(days=offset), "ABCD")
            self.assertEqual(verify_code(c, "S1", SECRET, TODAY).ok, ok, offset)

    def test_wrong_secret_fails(self):
        c = generate_code("S1", "nacl", SECRET, TODAY, "ABCD")
        self.assertFalse(verify_code(c, "S1", "other-secret", TODAY).ok)

    def test_code_is_bound_to_student_and_item(self):
        c = generate_code("S1", "nacl", SECRET, TODAY, "ABCD")
        self.assertFalse(verify_code(c, "S2", SECRET, TODAY).ok)
        swapped = c.replace("-NA-CL-", "-NH4-CL-")            # a different, valid pair
        self.assertFalse(verify_code(swapped, "S1", SECRET, TODAY).ok)

    def test_random_nonces_are_valid_and_differ(self):
        codes = {generate_code("S1", "nacl", SECRET, TODAY) for _ in range(50)}
        self.assertGreater(len(codes), 40)
        for c in codes:
            self.assertTrue(verify_code(c, "S1", SECRET, TODAY).ok)

    def test_ist_date_not_device_zone(self):
        # 20:00 UTC on 18 Oct is already 01:30 IST on 19 Oct
        self.assertEqual(ist_today(dt.datetime(2026, 10, 18, 20, 0, tzinfo=dt.timezone.utc)), D("2026-10-19"))
        self.assertEqual(ist_today(dt.datetime(2026, 10, 18, 18, 29, tzinfo=dt.timezone.utc)), D("2026-10-18"))


class TestPairTable(unittest.TestCase):
    def test_twelve_unique_pairs(self):
        self.assertEqual(len(ITEM_PAIRS), 12)
        self.assertEqual(len(PAIR_TO_ITEM), 12)

    def test_segments_parse(self):
        for item, (c, a) in ITEM_PAIRS.items():
            p = parse_code(f"VL-{c}-{a}-0000-0000")
            self.assertEqual((p.cation, p.anion), (c, a))
            self.assertTrue(re.fullmatch(r"[A-Z0-9]{2,3}", c) and re.fullmatch(r"[A-Z0-9]{2,3}", a))

    def test_quiz_map_matches_code_table(self):
        qm = json.loads((ROOT / "virtulab_data" / "quiz_map.json").read_text(encoding="utf-8"))
        self.assertEqual(set(qm), set(ITEM_PAIRS))
        for item, row in qm.items():
            self.assertEqual((row["cation"], row["anion"]), ITEM_PAIRS[item])
            self.assertEqual(row["quiz_code"], f"{row['cation']}-{row['anion']}")

    def test_no_O_I_L_confusion_in_generated_parts(self):
        for _ in range(200):
            c = generate_code("S1", "nacl", SECRET, TODAY)
            _, _, _, nonce, chk = c.split("-")
            for ch in nonce + chk:
                self.assertIn(ch, CROCKFORD)
                self.assertNotIn(ch, "ILOU")


class TestTokens(unittest.TestCase):
    def test_accept_vectors(self):
        for row in VEC["token_accept"]:
            got = parse_token(row["token"], SECRET, row["student"], row["code"])
            self.assertEqual(got, validate_payload(row["payload"]), row["why"])

    def test_reject_vectors(self):
        for row in VEC["token_reject"]:
            with self.assertRaises(TokenError, msg=row["why"]) as cm:
                parse_token(row["token"], SECRET, row["student"], row["code"])
            self.assertEqual(cm.exception.reason, row["reason"], row["why"])

    def test_roundtrip_and_size(self):
        p = VEC["token_accept"][1]["payload"]
        tok = build_token(p, SECRET)
        self.assertLess(len(tok), 1500)
        self.assertEqual(parse_token(tok, SECRET), validate_payload(p))

    def test_signature_is_over_compressed_bytes(self):
        import hashlib, hmac
        head, body, sig = VEC["token_accept"][0]["token"].split(".")
        comp = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        want = hmac.new(SECRET.encode(), comp, hashlib.sha256).digest()[:16]
        self.assertEqual(sig, b64u_encode(want))
        self.assertEqual(len(base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))), 16)

    def test_decompression_bomb_rejected(self):
        bomb = zlib.compress(b" " * 5_000_000, 9)
        tok = f"VLR1.{b64u_encode(bomb)}.{b64u_encode(__import__('lab_pack.token_codec', fromlist=['_sig'])._sig(SECRET, bomb))}"
        with self.assertRaises(TokenError) as cm:
            parse_token(tok, SECRET)
        self.assertEqual(cm.exception.reason, "too_large")

    def test_garbage_never_crashes(self):
        for junk in ["", "VLR1", "VLR1..", "VLR1.!!.!!", "VLR1.AAAA.AAAA", "x" * 5000, None]:
            with self.assertRaises(TokenError):
                parse_token(junk, SECRET)

    def test_bool_is_not_int(self):
        base = dict(VEC["token_accept"][0]["payload"])
        for key, val in [("att", True), ("v", True), ("dur_s", False)]:
            with self.assertRaises(TokenError, msg=key):
                validate_payload({**base, key: val})

    def test_every_mistake_in_enum_accepted(self):
        base = dict(VEC["token_accept"][0]["payload"])
        validate_payload({**base, "mis": list(MISTAKES)})


class TestCustomItemTable(unittest.TestCase):
    """The portal passes a table loaded from its database (new experiments = data only)."""
    TABLE = {"dummy_pendulum": ("PHY", "PEN")}

    def test_verify_with_custom_pair_table(self):
        from lab_pack.verify_code import ParsedCode, compute_chk
        chk = compute_chk(SECRET, "S1", "dummy_pendulum", "ABCD", TODAY)
        code = ParsedCode("PHY", "PEN", "ABCD", chk).canonical
        r = verify_code(code, "S1", SECRET, TODAY, pair_to_item={("PHY", "PEN"): "dummy_pendulum"})
        self.assertTrue(r.ok)
        self.assertEqual(r.item_id, "dummy_pendulum")
        self.assertEqual(verify_code(code, "S1", SECRET, TODAY).reason, "unknown_pair")  # default table

    def test_token_with_custom_item_table(self):
        from lab_pack.verify_code import ParsedCode, compute_chk
        code = ParsedCode("PHY", "PEN", "ABCD", compute_chk(SECRET, "S1", "dummy_pendulum", "ABCD", TODAY)).canonical
        payload = {"v": 1, "student": "S1", "item": "dummy_pendulum", "code": code, "issued": 1, "att": 1, "passed": True}
        with self.assertRaises(TokenError):
            validate_payload(payload)
        validate_payload(payload, self.TABLE)


class TestNoRealSecrets(unittest.TestCase):
    def test_secret_is_fake_and_not_hard_coded_in_modules(self):
        self.assertIn("NOT-REAL", SECRET)
        for name in ("verify_code.py", "token_codec.py", "generate_demo.py"):
            text = (Path(__file__).parent / name).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"secret\s*=\s*[\"\']", text, re.I), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
