# 006: Deciding met or not met: NLI judge vs the usual pattern

- **Status:** Accepted
- **Area:** `participant_module/judge.py`
- **Date:** 26 October 2026

## Context

Finding pages is half the job. For every criterion we must also say **met**, **not met** or
**insufficient evidence**, and quote a sentence. Our first idea was a zero-shot NLI model, which
answers "does this sentence prove this claim?". We used the catalogue model
`deberta-v3-base-zeroshot-v2.0-c` as the judge.

## How we tested

For each criterion we wrote one plain claim ("The model or method was calibrated or validated
against observed field measurements."). The judge read the top candidate sentences from retrieval
and gave each a score. We tried thresholds and compared the result with our answer key: 108
met/not-met decisions on the 9 studied reports.

## Results

1. **Far too slow:** 110–147 seconds per report. With retrieval and loading that is about 140 s
   of the 180 s, with no margin for a large report. The cause is 12 criteria × 20 sentences =
   240 readings, at about 2 readings per second on our CPU.
2. **Not accurate enough:** at its best threshold (0.60) it got 76 of 108 decisions right (70%),
   and it barely improved the page order (44 vs 43 hits).
3. **It confused neighbouring criteria.** Sentences about running a model scored 0.84–0.93 for C04
   ("tested under controlled conditions"), while real C06 evidence ("flood maps were created
   for…") scored only 0.02–0.26.
4. **Junk got through as candidates,** such as the Secretary of the Interior line, "Suggested
   citation…", contents pages and reference entries. This led to note 009.

## What the scoring rules taught us

B = (2 × met part + 1 × not-established part) / 3 (§13.3). **Missing a criterion the experts call
met costs twice as much as wrongly claiming one.** So plain accuracy was the wrong measure.

We then compared the judge with a rule that does not read the report at all: "say met for C01,
C02, C03, C05, C06 and C11, not met for the rest", the usual pattern in these USGS reports.

| On the studied reports | Estimated B |
|---|---|
| NLI judge alone (best threshold) | about 0.61 |
| "Usual pattern" rule | about 0.73 |

## Decision

Start from what a report of this kind almost always contains, and let the text change the answer
only where the evidence is specific:

- The **TRL** decides the TRL-level criteria (note 007).
- Criteria that need specific evidence (C04 laboratory validation, C10 results against
  requirements) are met only when a sentence with clear cue words is found.
- The **NLI model is kept, but only to choose the quote.** It picks the best of the 5 top-ranked
  candidate sentences for each met criterion, within a time budget, and is skipped if time runs
  short.

## Consequences and follow-ups

- This is a prior-based policy. On an unusual report (for example a pure laboratory study) the
  usual pattern can be wrong, so the TRL rule and the cue words have to carry that case.
- If the event machine's GPU is used in Stage 2, a stronger judge could become affordable. That
  would need a new test and a new note.
