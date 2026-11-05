# 012: A trained TRL model vs our hand-written rule

- **Status:** Accepted (decision: keep the hand-written rule; the trained model is not shipped)
- **Area:** TRL decision (`participant_module/judge.py`); experiment in `training/`
- **Date:** 5 November 2026

## Context

Submission 1 passed the organizer's diagnostic run (all three cases completed, 24–34 s each, no
output issues, hashes matched). Its TRLs were 6, 7 and 6 for USGS-SDG-012, 040 and 061. Against
the organizer's estimates (4, 7, 6), two are exact.

**A correction to note 007.** Note 007 says the two known misses (012 and 094) are "both off by
one (0.5 each)". That is wrong for 012: the organizer estimates 4 and we say 6, which is off by
**two** and scores **0**. 094 (5 vs 6) is off by one. Our `evaluate.py` scored both correctly; only
that sentence was wrong.

Our TRL comes from rules we wrote by hand (note 007). We asked whether a model **trained** on the
99 public sample cases (with the organizer's estimated TRLs as answers) could predict the TRL better,
especially the reports the organizer rates 5 where the rule says 6.

## What the data looks like

Organizer estimates over the 99 cases: TRL 4: 1, 5: 12, 6: 54, 7: 29, 8: 1, 9: 2. From the case
fields alone, the rule gets 51 of 54 TRL 6, 28 of 29 TRL 7 and 3 of 12 TRL 5. Most lost points come
from **9 TRL-5 reports where it says 6** (0.5 each). Report 012 is the **only** TRL 4 among the 99,
so no model could learn TRL 4 from this data.

## Method

1. **Clues (features).** For each report, about 15 numbers measured from the module's own cleaned
   text (front matter, contents, references removed):
   - what the rule says, and whether it decided from the case fields;
   - whether the target is a system;
   - how often the report uses each kind of phrase per 10,000 words: calibration/validation,
     accuracy statistics, "criteria met", operational use, early stage (pilot, preliminary),
     software and example data, laboratory tests, future work;
   - report length.
2. **Lockbox.** Before designing any new clue, 29 reports (30% of each of TRL 5, 6, 7) were chosen
   at random (seed 20261105) and sealed (`training/lockbox.json`). Clues were designed, and models
   compared, on the other 70 only.
3. **Model.** Each clue is standardised, then a multinomial logistic regression is fitted. The
   answer is the TRL with the highest **expected points** under the official scoring; argmax was
   also tried.
4. **Mock exams.** 5-fold cross-validation on the 70 open reports, repeated 20 times. Every report
   is predicted by a model that never saw it.

## What we learned about the clues

- "In use" phrases strongly mark TRL 7 (44.6 per 10k words, vs 7.3 for TRL 6 and 3.6 for TRL 5).
  "Early stage" leans towards 5 (3.6 vs 1.0 vs 0.2).
- Calibration, accuracy and "criteria met" phrases look the **same** for TRL 5 and 6.
- Our "mixed results" clue pointed the **wrong way** (highest for TRL 7). It counted general talk
  about uncertainty, which mature flood-map reports have a whole section on. Clue set version 2
  replaced it with narrower "weak results", and added "validation gaps" ("could not be
  calibrated") and "existing data".
- What makes the organizer say 5 is a judgement about **how well** validation went: "acceptable
  accuracy at only 36% and 26% of streamgages", "Honeybrook could not be calibrated", "success
  rates varied markedly by region". Phrases like "only N percent" also fire on unrelated statistics
  ("only 4 percent of non-native fish…"). Of the 5 open TRL-5 reports the rule misses, 3 contain
  none of the candidate phrases.

## Results (part-A points, open reports)

| Contestant | Score |
|---|---|
| Always 6 | 0.743 |
| Hand-written rule (written while reading these reports, so optimistic) | **0.914** |
| Trained model, clue set 1, several settings (C 0.03–1.0) | 0.828–0.859 |
| Trained model, clue set 2 | 0.832–0.865 (approximate, see below) |
| Model only allowed to change the rule's default 6 into 5 | 0.906–0.915; switched only 0.1–2.5 reports per run |

The full model is worse than the rule: with this little data it overrides correct answers. The
restricted model almost never switches, and its score equals the rule's within noise. Among the 42
open reports where the rule says 6 by default, only 5 are TRL 5. The clues cannot pick them out.

Clue set 2 was measured from the saved texts, where a sentence containing a line break was partly
cut. Those numbers are approximate. Clue set 1 was measured from the PDFs on our laptop.

## Decision

- **Keep the hand-written TRL rule.** The trained model is not shipped.
- The **lockbox stays sealed**, because no final model was chosen. It remains available for one
  honest test of any later TRL change.
- `trl_features.py` was moved from `participant_module/` to `training/`, so the submitted package
  holds no unused code. The submitted module is unchanged by this experiment.

## Consequences and follow-ups

- This is a negative result, recorded so the work is not repeated blindly. With more labelled TRL-5
  reports, or clues that read validation **results** (for example the share of gauges meeting a
  criterion in a table), a model could become worthwhile.
- Hedging (answering 5 when torn between 4 and 6) remains a possible rule-level change. It would be
  tested on the lockbox.
- Next: improve the quotes (part C and the evidence pages of part B), where we know there is room
  to gain.
