# 007: The TRL rule and the criterion rules

- **Status:** Accepted
- **Area:** `participant_module/judge.py` (`meta_trl`, `decide_trl`, criterion statuses)
- **Date:** 26 October 2026

## Context

The TRL is 45% of the score (part A: exact = 1, off by one = 0.5, abstain = 0.25, otherwise 0).
Every public sample case comes with the organizer's estimated TRL and a short reason. Most
reports describe a calibrated model, map or survey applied to a real site, so most estimates are
6 or 7.

## Options considered

| Option | Idea |
|---|---|
| Always 6 | The most common value; a strong baseline because off by one still earns 0.5 |
| Judge the text | Read each report for evidence of each TRL step (slow and noisy, note 006) |
| **Rule from the case fields** | What is assessed (a system? a pilot? a delivered web tool?) tells a lot about the TRL |

## The rule

From the case fields (the target's `type`, and the title plus target description), checked in
this order; the first match wins:

| If… | TRL |
|---|---|
| the target type is `system` and the text mentions a hurricane | 9 |
| the target type is `system` | 7 |
| the title or description says pilot, preliminary or "evaluation of" | 5 |
| it is a flood-inundation map library (not precipitation-driven, no synthetic rating) | 7 |
| it is an R package, user guide, web application or StreamStats | 7 |
| it is a survey, channel or seafloor mapping, or a national assessment | 7 |
| otherwise, if the report text says "limited validation" | 5 |
| anything else (a calibrated model or method applied to the site) | 6 |

## How we tested

Part A against the organizer's estimated TRL on the public cases: always-6 scores 0.75, and the
rule scores 0.92. **This is optimistic,** because the rule was written while reading those same
cases. On our 9 studied reports A is 0.833 (always-6: 0.500), and on the 3 unseen reports it is
1.000 (always-6: 0.667).

## The criterion rules

| Criterion | Met when |
|---|---|
| C01–C03 (principles, concept, proof of concept) | always (nearly every report states them) |
| C05–C09 (TRL 5–9 steps) | the decided TRL is at least that level |
| C04 (laboratory validation) | a sentence describes controlled testing: a laboratory test, a flume, a bench test, synthetic, test or example data sets, a patch test, a quality-control check… |
| C10 (results against requirements) | a sentence compares results with a **stated** criterion and gives a verdict (satisfactory, acceptable, met or exceeded the criteria, within the allowable…), and is about results, not input data |
| C11 (test conditions), C12 (evidence about the target) | always |

Criteria are recognised by their **title** or "(TRL n)" tag, never by their ID.

## Known misses

- USGS-SDG-012: the organizer estimates 4, we say 6.
- USGS-SDG-094: the organizer estimates 5, we say 6.

Both are off by one (0.5 each), and they are the first things to look at for Submission 2.

## Consequences and follow-ups

The rule is only as good as the variety of reports we have seen. A report type we never saw goes
to the default 6, which is still at most one level off for most real reports.
