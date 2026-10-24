# VirtuLab Lab Pack  (portal -> lab contract, version 1)

For the Unity lab team. The portal owns this contract; the lab matches it.
Reference code is Python (standard library only). **Do not copy the Python — copy the
behaviour, then prove it with `test_vectors.json`.**

Files
- `test_vectors.json`  expected inputs/outputs. Your code must agree on every row.
- `verify_code.py`, `token_codec.py`  reference implementation (read these for exact behaviour).
- `generate_demo.py`  makes a real-looking code + token so the portal can be built in parallel.
- `../virtulab_data/quiz_map.json`  item id -> cation / anion / names (shared data folder).

The vectors use a FAKE secret. The real secret is agreed privately and never goes in Git.

---
## 1. Student ID  (both sides, everywhere)
`normalised = remove ALL whitespace from the typed text, then UPPER-CASE`
`"  24 11021 061202 " -> "2411021061202"`, `"21cs045" -> "21CS045"`.
Rejected: empty, contains `|`, longer than 40, contains control characters.

## 2. Completion code  `VL-<CATION>-<ANION>-<NONCE>-<CHK>`   e.g. `VL-CU-SO4-7K3Q-GCG6`
1. `CATION` / `ANION` come from the table below (they also identify the salt).
2. `NONCE` = 4 random characters from the alphabet `0123456789ABCDEFGHJKMNPQRSTVWXYZ`
   (Crockford base32: no I, L, O, U).
3. `date` = the day the code is issued, in **IST = UTC + 5h30m**, written `YYYYMMDD`.
   Compute it from UTC time + 5:30. **Do not use the phone's own time zone.**
4. `message` = `STUDENTID|ITEMID|NONCE|YYYYMMDD` as UTF-8 text, with the **normalised**
   student id and the item id from the table, e.g. `2411021061202|cuso4|7K3Q|20261019`.
5. `digest` = HMAC-SHA256(key = secret as UTF-8 bytes, data = message as UTF-8 bytes) -> 32 bytes.
6. `CHK` = the first **20 bits** of the digest as 4 characters of the same alphabet,
   5 bits per character, most significant bit first.
   (Same as: base32-encode the first 5 bytes and keep 4 characters, in this alphabet.)

| item id | CATION | ANION | | item id | CATION | ANION |
|---|---|---|---|---|---|---|
| nacl | NA | CL | | znso4 | ZN | SO4 |
| nh4cl | NH4 | CL | | bacl2 | BA | CL |
| cuso4 | CU | SO4 | | caco3 | CA | CO3 |
| feso4 | FE2 | SO4 | | mgso4 | MG | SO4 |
| fecl3 | FE3 | CL | | pbno32 | PB | NO3 |
| al2so43 | AL | SO4 | | nh42co3 | NH4 | CO3 |

**Debug trick:** every row in `test_vectors.json -> chk` shows the message, the full HMAC
in hex and the CHK. If your final code differs, compare message first, then hex, then CHK.

The portal accepts a code whose issue date is between 30 days ago and 1 day ahead of its own
IST date. The portal (not the lab) enforces single use and rate limits.

## 3. Result token  `VLR1.<payload>.<sig>`
1. Build the JSON (below) and compress it with **zlib** (the format with the 2-byte header, i.e.
   .NET `ZLibStream`, not raw `DeflateStream`).
2. `payload` = base64url of the compressed bytes, **no `=` padding** (`-` and `_`, not `+` and `/`).
3. `sig` = base64url (no padding) of the **first 16 bytes** of
   HMAC-SHA256(secret, **the compressed bytes**). Sign the compressed bytes, not the JSON.
4. Keep the compressed size under 1.5 KB.

Different zlib builds give different compressed bytes for the same JSON. That is fine: the
portal checks the signature on whatever bytes you send. Never compare compressed output
between implementations; check that the **other side's token verifies and decodes**.

```json
{"v":1,"student":"2411021061202","item":"cuso4","code":"VL-CU-SO4-7K3Q-GCG6",
 "issued":1792400000,"att":1,"passed":true,"dur_s":540,
 "tests":[{"r":"naoh","d":3,"n":1}],"flame":true,"heat":false,"gas":[],
 "mis":[],"wrong":[]}
```
Required: `v`(=1) `student`(normalised) `item` `code` `issued`(unix seconds) `att`(>=1) `passed`.
Optional (defaults empty/false/0): `dur_s` `tests` `flame` `heat` `gas` `mis` `wrong`.
`tests[]`: `r` reagent id (`a-z0-9_`), `d` drops, `n` order (starts at 1).
`gas[]`: ids like `co2`. No other fields, no free text — **unknown fields make the token invalid**.
The portal rejects the whole token if anything is wrong and falls back to a bank-only quiz.

### Mistake ids (`mis[]`) — the portal accepts only these 8
| id | proposed meaning (lab team: please confirm or correct) |
|---|---|
| order_wrong | tests done in an order that breaks the standard scheme |
| reagent_excess | more reagent added than the procedure allows |
| skipped_flame | submitted without doing the flame test |
| skipped_confirmatory | submitted without a confirmatory test |
| skipped_dissolve | insoluble salt not dissolved first |
| repeated_same_test | same test repeated with no new purpose |
| wrong_reagent_for_goal | reagent used does not serve the current test goal |
| wrong_submission | cation or anion submitted wrongly (also list it in `wrong[]`) |

### Wrong submissions (`wrong[]`) — CHANGED from the first spec
Each entry is `{"cat": "<ion id>", "an": "<ion id>"}`, where an ion id is **the same short id used
in the code table**: cations NA NH4 CU FE2 FE3 AL ZN BA CA MG PB; anions CL SO4 CO3 NO3.
(The first spec used `"SO4^2-"`; plain ids avoid superscript problems.) If the lab offers other
ions as answer choices (e.g. K, AG, BR), tell us the ids you use; they must match `[A-Z0-9]{1,4}`.

---
## 4. Prove you match
1. Student-ID rows in `test_vectors.json` produce the expected strings.
2. Every row of `chk`: same message, same hex, same CHK, same code.
3. Every row of `code_accept` verifies; every `code_reject` row fails.
4. Every `token_accept` token verifies with your code and decodes to the listed payload.
5. A token **you** make verifies in the portal: run
   `python lab_pack/generate_demo.py ...` to see a portal-made one, and send us one of yours.

## Contract decisions made while writing this pack (portal side, flag if you disagree)
- Code keeps the md's HMAC input `STUDENTID|ITEMID|NONCE|YYYYMMDD`; only the printed segments changed.
- Date is IST computed from UTC, not the device zone.
- Token signature covers the compressed bytes (so it can be checked before decompressing).
- Strict token schema: unknown fields or unknown mistake ids invalidate the token.
- Typed-code leniency lives only in the portal: case, spaces, phone dashes, and O/I/L typed
  for 0/1/1 inside NONCE and CHK are accepted. The lab always prints the canonical form.
