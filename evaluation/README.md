# Evaluation: how we test the module

These files are **not** part of the submission. `tools/make_submission.py` packs only
`participant_module/`, `assets/`, `submission.json`, `declaration.json` and `README.md`.
They are here so anyone can repeat our measurements. The reasoning behind each choice is in
[`docs/our-thought-process/`](../docs/our-thought-process/README.md).

## Files

| File | What it is |
|---|---|
| `evaluate.py` | Runs the real module on every report in our answer keys, the way the server does (fresh module per case, page count from pypdf), checks each result with the kit's validator, and scores A (TRL) and B (criteria) with the official formulas. Writes `evaluation_quotes.txt` and `results/` for reading. |
| `check_zip_locally.py` | Unpacks the submission zip and runs it on the kit's own server on the 3 diagnostic cases (012, 040, 061), like the organizer's Submission 1 run. Prints PASS or FAIL. |
| `keys/answer_key_main_v4.json` | Our answer key for 9 studied public reports (64 entries). |
| `keys/answer_key_holdout_v2.json` | Our answer key for 3 reports never used for tuning (25 entries). |
| `keys/history/` | Earlier versions of the keys (main v1: 34 entries, v2: 55 entries; holdout v1: 27 entries). |
| `history/` | Early scripts as they were run (the first card cutter and its test). Paths inside may need adjusting. |

Answer-key format: `{"USGS-SDG-012": {"APCTT-C01": {"pages": [5, 6], "quote": "…"}, …}, …}`.
Pages are 1-based PDF pages. A criterion that is not listed counts as "not established". These are
**our** labels, not the experts'.

## How to run

From WSL, with the participant kit, the base environment and the catalogue models set up as in the
kit's README (steps 3–5):

```bash
# score the module on both answer keys (about 30 s per report on 4 CPU cores)
~/work/apctt-env/base/bin/python evaluation/evaluate.py \
    --kit ~/work/apctt-participant-kit-0.5.0-cpu --models ~/work/models \
    --main-pdfs <folder with USGS-SDG-xxx.pdf> --holdout-pdfs <folder with the 3 holdout PDFs>

# check the packed zip on the kit's own server
~/work/apctt-participant-kit-0.5.0-cpu/.venv/bin/python evaluation/check_zip_locally.py
```

The PDFs are the kit's public sample cases. Download them with the kit's
`tools/get_public_cases.py --download <IDs> --dir <folder>`; they are not stored here.
