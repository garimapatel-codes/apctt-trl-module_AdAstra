# 003: A fuller answer key, cards vs whole pages, and TRL keywords

- **Status:** Accepted (cards and keywords are in the final module)
- **Area:** `participant_module/chunker.py`, `participant_module/keywords.py`, answer keys
- **Date:** 25 October 2026

## Context

After note 002 we added more public sample reports, for 9 in total: USGS-SDG-005, 012, 027, 028,
040, 045, 061, 081 and 094. We also asked two questions:

1. Does cutting pages into small pieces ("cards") help the search?
2. The checklist uses NASA-style wording ("prototype demonstrated in a relevant environment"),
   while reports say "the model was applied", "maps were created" or "calibrated against observed
   data". Can we close that gap cheaply?

## A problem with our own answer key first

Our first key for the 9 reports (`evaluation/keys/history/answer_key_main_v1.json`, 34 entries)
had **no entries at all for C04–C09**, the criteria that actually set the TRL. So we were choosing
a search method by how well it found the easy background criteria (C01–C03). We added the
C04–C07 evidence and got 55 entries (`answer_key_main_v2.json`). We also checked by script that
every quoted sentence is really on its page.

## Cards

A card is a piece of one page of at most 180 words, cut at sentence boundaries and overlapping its
neighbour by one sentence. Running headers, page numbers, contents pages, reference lists and
empty pages are removed first. Cards matter for the models later, because the rerankers read only
about 512 tokens (roughly a third of a page) at a time. A card also gives us the exact sentence to
quote.

## TRL keywords

For each criterion we wrote a list of everyday words a report uses for it. For example,
relevant-environment validation gets *calibrated, validated, observed, measured, field data,
compared, error, accuracy*. The search question becomes the official sentence **plus** these words.

The lists are looked up by the criterion's **title** ("Laboratory validation (TRL 4): …"), or by
its "(TRL n)" tag, and never by its ID. The rules warn that the hidden checklist may number
criteria differently.

## How we tested

The same search on the 55 entries, measuring whether a correct page is in the top 3.

## Results

| | Official sentence only | + TRL keywords |
|---|---|---|
| BM25 on whole pages | 30/55 (55%) | **38/55** |
| BM25 on cards | 27/55 | **37/55** |

- Cards alone did not help BM25 (27 vs 30). Line by line, 10 entries were better, 13 worse and
  11 the same. Piece size was not BM25's problem; the words were.
- The keywords helped a lot and cost nothing. They fixed exactly the cases where a report uses
  different words from the checklist. SDG-061 C06 went from 11th to 3rd, SDG-061 C11 from 9th to
  3rd, and SDG-005 C06/C07 from 6th–7th to 1st–3rd.
- A few got worse. SDG-027 C05 went from 4th to 8th, and SDG-094 C11 from 8th to 13th. General
  words like "compared", "error" and "data" also appear on wrong pages.
- About 1 in 3 entries was still missed, for example "evidence concerns the assessed target"
  (SDG-061 C12), which is an idea rather than a set of words.

**Timing of the worst case:** two long reports totalling 300 pages (the case limit), SDG-075 plus
SDG-017, give 861 cards. Reading and cutting take about 10.5 s, almost all of it PDF reading.

## Decision

Keep the cards and the TRL keywords.

## Consequences and follow-ups

We wrote the keyword lists after reading these 9 reports, so part of the gain might not carry over
to new reports. We had to test that on reports we had never opened (note 005).
