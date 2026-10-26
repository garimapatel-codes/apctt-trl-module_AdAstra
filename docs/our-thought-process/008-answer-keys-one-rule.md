# 008: One labelling rule for our answer keys

- **Status:** Accepted
- **Area:** `evaluation/keys/`
- **Date:** 26 October 2026

## Context

Every number in these notes comes from comparing the module with our own answer keys. When we
looked at the judge's "mistakes" (note 006), many turned out to be our key's mistakes. On the
unseen reports we had labelled C10 and C12 whenever the evidence was there, but on the 9 studied
reports we mostly had not. With an inconsistent key, we would be tuning towards noise.

## Decision: one rule for every report

- **C01–C03:** when the report states them.
- **C04:** laboratory-like or controlled testing.
- **C05:** calibrated or validated against measurements at the site.
- **C06:** the complete product applied to the actual site. **Not** for reports the organizer
  rates TRL 5.
- **C07:** delivered or in operational use.
- **C10:** only when results are compared with a **stated** requirement or acceptance criterion,
  with a verdict.
- **C11:** test conditions described.
- **C12:** every report (the pages that describe the assessed target).
- A criterion not listed has no correct page (it counts as "not established").

## What changed

- C12 was added for every report.
- C10 was kept only where a stated requirement and a verdict exist (061, 045, 099) and removed
  from 033 and 013.
- C06 was removed for the TRL 5 reports (028, 081).
- Missing evidence was added: 027 C01, 028 C03 and 028 C11.
- Every quote was checked again to be on its page.

This gives `answer_key_main_v4.json` (9 reports, 64 entries) and `answer_key_holdout_v2.json`
(3 unseen reports, 25 entries). Earlier versions are kept in `evaluation/keys/history/`.

## Limits

These keys are **our** reading, not the experts' labels, and the TRLs are the organizer's rough
estimates. The real score will differ. We use the keys to compare our own versions with each
other, not to predict the final score.
