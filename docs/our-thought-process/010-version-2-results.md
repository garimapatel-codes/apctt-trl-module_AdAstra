# 010: Version 2: results, timing and robustness

- **Status:** Accepted (record of the submitted version)
- **Area:** the whole module; `evaluation/evaluate.py`
- **Date:** 26 October 2026

## The pipeline as submitted

1. Read each PDF with pypdfium2 and clean the pages (note 001).
2. Cut them into cards, skipping front matter, contents, references, glossaries and empty pages
   (notes 003 and 009).
3. For each criterion, BM25 + TRL keywords shortlists 10 cards, ms-marco re-reads them with a
   plain question, and the two orders are merged (note 005).
4. TRL from the case fields; criterion statuses from the TRL plus cue sentences for C04 and C10
   (notes 006 and 007).
5. Up to 3 evidence pages per met criterion. The quote is a filtered sentence from the first page,
   picked by the NLI model (note 009).
6. A time guard throughout, and a safe fallback answer if anything fails.

## How we tested

`evaluation/evaluate.py` builds each case exactly as the server does (case fields, PDF path, page
count from pypdf). It runs a fresh module per case, as the server does, checks every result with
the kit's own validator, and scores parts A and B with the official formulas against our keys
(note 008). We ran it on our laptop with the real catalogue models, 4 cores, CPU only.

## Results

| Set | A (TRL) | B (criteria) | Quote on a correct page | Valid | Time per case |
|---|---|---|---|---|---|
| 9 studied reports | 0.833 (always-6: 0.500) | 0.816 | 33/64 | 9/9 | mean 29 s, worst 42 s |
| 3 unseen reports | 1.000 (always-6: 0.667) | 0.893 | 17/25 | 3/3 | mean 27 s, worst 28 s |
| always-abstain baseline | 0.25 | 0.333 | – | – | – |

Estimated A+B share of the score (0.45 A + 0.40 B, out of 0.85): about 0.70 on the studied reports
and 0.81 on the unseen reports. Part C (expert review of quotes) cannot be estimated by us.

**Without the models** (BM25 and cue words only, the fallback if models fail to load): A 0.833 and
B 0.816 on the studied reports, and A 1.000 and B 0.867 on the unseen ones. All results valid. The
module still scores well if the models are missing.

## Robustness tests (all passed: a valid result every time)

- a case with 3 PDFs;
- renamed criterion IDs (the module must not depend on "APCTT-C04");
- a PDF with no text;
- only 40 seconds left on the clock;
- an unreadable PDF file.

## Caveats

Our keys are not expert labels, the TRLs are the organizer's estimates, and 12 reports is a small
sample. The hidden cases may include other kinds of report. These numbers compare our versions
with each other; they do not predict the final score.
