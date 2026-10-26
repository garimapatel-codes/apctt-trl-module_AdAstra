# 011: Packaging Submission 1 and checking the zip locally

- **Status:** Accepted
- **Area:** `submission.json`, `declaration.json`, `README.md`, `evaluation/check_zip_locally.py`
- **Date:** 26 October 2026

## Context

Each team gets two submissions. The first returns only a pass/fail and a diagnostic run on 3 public
cases (012, 040, 061), with no score. We wanted that first upload to pass for certain, so that its
feedback is about our module and not about packaging.

## Packaging

- `submission.json`: team Ad_Astra, CPU, the kit's common base `apctt-base-9e7fe1324bb6`, and our
  two catalogue models, `ms-marco-minilm-l6-v2` and `deberta-v3-base-zeroshot-v2.0-c`. No weights
  of our own.
- `declaration.json`: no team training; the public sample cases are declared as our only data
  source, used for development and checking.
- `participant_module/LICENSE`: the MIT text, as the rules require.

`tools/make_submission.py` packs the zip, writes the package hash, and runs the organizer's intake
checks. Result: **VALID_WITH_REVIEW**, with one review item: the licence string of the public
sample cases. We first tried the short form "Public Domain". The policy recognises it, but still
lists it as "review". We therefore went back to the exact wording that SUBMISSION.md §3 asks for:
"U.S. public domain (USGS); some figures third-party, see the manifest's licence_note". Every team
that uses the sample cases gets this same review line.

The tool packs only the five allowed entries. `docs/`, `evaluation/`, `.git` and caches in this
repository are reported as "not packed" and are never sent.

| | Value |
|---|---|
| Package hash (declared_package_sha256) | `0875c6c382e62ba23d06db6f18dbd5af2493c8eff940d0b9930d3c30f6fcb3be` |
| Zip hash | `82e44624ec4e19a3d424f7316f91e8a90788d0042785bf0076c568a1405da26e` |

## Checking the zip itself, not our working folder

`evaluation/check_zip_locally.py` imitates the organizer's diagnostic run on our laptop:

1. It unpacks the zip into a fresh folder.
2. It starts the kit's own server with that copy and the declared hash. The server refuses to
   start if the code does not match the hash.
3. It runs the 3 diagnostic cases, each in a new worker process with the base environment and the
   model store.
4. It prints status, TRL, timings and problems, then PASS or FAIL.

## A mistake we made, and the lesson

The first two runs printed PASS, but every case had **0 criteria met** and finished in under a
millisecond. The script had followed the base environment's `bin/python` link (`Path.resolve()`)
and ended up at the bare Python 3.12, which lacks torch, transformers and pypdfium2. Our module
then used its emergency fallback: a valid but empty answer.

**Fixes:**
- keep the path as given (`os.path.abspath`, not `resolve()`);
- check that the base environment's packages import before starting;
- report FAIL when no criterion is met or the module's log says the models did not load.

**Lesson:** a valid result is not a working result. The fallback that protects us at the event
also hides problems in testing, so every check also looks at what the module actually did.

## Final local run (real models, our laptop)

| Case | Status | TRL | Criteria met | Load | Total |
|---|---|---|---|---|---|
| USGS-SDG-012 | completed | 6 | 8 | 7.5 s | 33.1 s |
| USGS-SDG-040 | completed | 7 | 8 | 7.1 s | 39.9 s |
| USGS-SDG-061 | completed | 6 | 8 | 6.9 s | 35.3 s |

The hash was verified, and the slowest case was well inside the 180 s limit.

## Follow-ups for Submission 2

- The TRL misses on 012 and 094 (note 007).
- The share of quotes on a correct page (note 009).
- Keep a change only if `evaluate.py` shows it is clearly better, then repack and re-run this
  check before uploading.
