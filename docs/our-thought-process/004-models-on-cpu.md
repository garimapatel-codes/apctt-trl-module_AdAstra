# 004: Models on a CPU: meaning-matcher and rerankers

- **Status:** Superseded by [005](005-unseen-reports-exam.md) (its final choice changed after the unseen-reports test)
- **Area:** `participant_module/retrieval.py`
- **Date:** 25 October 2026

## Context

Word matching (BM25 plus keywords) still missed about 1 in 3 entries (note 003). Two kinds of
catalogue model could help:

- an **embedding model** (a "meaning-matcher": texts with similar meaning get similar vectors);
- a **reranker** (a "careful reader": it reads the question and one text together and scores
  how well the text answers it).

## Test 1: the meaning-matcher (bge-base-en-v1.5) on every card

| | Correct page in top 3 (of 55) |
|---|---|
| BM25 + keywords on cards | **37** |
| bge-base alone | 18 |
| Both merged (RRF) | 34 |

It was also **very slow**: 8.5 minutes for 633 cards, and 12 minutes for the 861-card worst case.
The whole case is allowed 3 minutes.

**Was our laptop the problem?** We measured it. Raw matrix speed was 216 GFLOPS, with 7.3 GB of
free memory, no swapping and float32. That's healthy. With 4 threads it fingerprinted 4.2 cards per
second; with 1 thread, 2.0. PyTorch used only 2 threads by default, so our code sets 4. The real
cause is arithmetic: a 200-word card costs about 40–50 billion multiplications in this model, so a
CPU cannot read a whole report this way.

**Lesson:** let the cheap method search widely, and give a model only a short list.

## Test 2: rerankers on a shortlist

BM25 + keywords keeps the **10 best cards per criterion**. A reranker re-orders only those:
12 criteria × 10 cards = 120 readings per report, whatever its length.

| | Top 3 (of 55) | Time per report |
|---|---|---|
| BM25 + keywords, cards | 37 | under 0.1 s |
| + granite-embedding-reranker-english-r2 | 31 | **66 s** |
| + ms-marco-MiniLM-L6-v2 | 32 | 7.6 s |
| Best possible from the shortlist | 47 | – |

Both rerankers made the order worse. They were trained on web-search **questions**, and we gave
them formal checklist **rules**. Granite was also too slow.

## Test 3: plain questions, and merging instead of replacing

- **Plain questions:** for each criterion, one question the way a report would answer it, naming
  the case's technology from the case field `assessment_target`. For example: "Was *Meramec River
  inundation maps* calibrated or validated against measurements collected at the study site, and
  how accurate was it?"
- **Merging:** the reranker's order and BM25's order are combined by RRF, so the reranker can only
  nudge BM25, not overrule it.

We fixed the answer key at the same time: some entries were missing pages that are equally valid.
That raised every method, so these numbers can't be compared directly with Tests 1–2.

| Method | Top 3 (of 55) | First place | Time per report |
|---|---|---|---|
| **pg-kw: BM25 + keywords, whole pages** | **44** | 25 | about 0.1 s |
| cd-kw: BM25 + keywords, cards | 44 | 21 | about 0.1 s |
| all: pages + cards + ms-marco, merged | 45 | 24 | about 6.5 s |
| msm+bm: ms-marco merged with BM25 | 43 | 26 | about 6.5 s |
| msm: ms-marco alone | 40 | 19 | about 6.5 s |
| Correct page in the shortlist | 52 | | |

**Our rule against fooling ourselves:** with 6 methods on 55 entries, one can win by luck. A method
that adds a model must beat the simple one by **3 or more hits**.

## Decision (at the time)

`pg-kw`, BM25 + keywords on whole pages. "all" was only 1 hit better, which is not enough under
our rule.

## What changed it

We had tuned everything on these 9 reports. The next test, on reports we had never opened,
reversed this choice (note 005).
