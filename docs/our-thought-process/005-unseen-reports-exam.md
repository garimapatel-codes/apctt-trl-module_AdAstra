# 005: The unseen-reports test changes the retrieval choice

- **Status:** Accepted (this is the retrieval in the submitted module)
- **Area:** `participant_module/retrieval.py`
- **Date:** 26 October 2026

## Context

Our keyword lists and choices were made while looking at 9 reports. The hidden evaluation uses
reports we will never see, so we needed a fair test: reports nobody had used for tuning.

## How we tested

- **Data:** 3 public sample reports we had not opened before: USGS-SDG-013, -033 and -099.
- **Answer key:** written by reading these reports page by page, **without running our search
  or looking at our keyword lists**. It has 27 entries, and every quote was checked to be on its
  page (`evaluation/keys/history/answer_key_holdout_v1.json`).
- **Measure:** a correct page in the top 3. The pass mark was 19 of 27 (70%), close to what the
  methods scored on the studied reports.

## Results

| Method | Unseen reports (27) | Studied reports (55) | Both (82) | First place (both) |
|---|---|---|---|---|
| pg-kw: BM25 + keywords, pages | **17 (63%)**: failed | 44 | 61 (74%) | 32 |
| cd-kw: BM25 + keywords, cards | 19 (70%) | 44 | 63 (77%) | 29 |
| **msm+bm: BM25 + ms-marco merged** | **22 (81%)** | 43 | **65 (79%)** | **36** |
| all | 20 | 45 | 65 (79%) | 32 |
| msm alone | 20 | 40 | 60 | 30 |

- **The method we had chosen failed on new reports.** It dropped from about 80% to 63%, the
  classic sign of overfitting: our keyword lists fitted the studied reports too well. Whole pages
  made it worse, because a long page full of generic words like "model", "data" and "results"
  can win on bulk.
- **The reranker generalises.** It understands the plain question naming the technology, and
  that understanding carries over to new reports better than our word lists do.
- By our own rule (a model must win by 3 or more hits), msm+bm qualifies: it beats pg-kw by 5 on
  the unseen reports and by 4 overall.
- The shortlist still works: 26 of the 27 correct pages are in BM25's top 10 cards.

## Decision: the final retrieval

1. Cut each report into cards (`chunker.py`).
2. **Quick screen:** BM25 + TRL keywords on cards keeps the 10 best cards per criterion
   (under 0.1 s).
3. **Careful reader:** ms-marco-MiniLM-L6-v2 reads each shortlisted card with a plain question
   naming the case's technology.
4. **Merge** the two orders by RRF (k = 60), so the reader nudges and BM25 keeps its say.
5. Return the best pages, each with its best card.

**Cost:** about 6.5 s per report, whatever its length (12 criteria × 10 cards).

**Safety switch:** if time is short, the module skips the reader and uses BM25 alone, which takes
under a second.

## Consequences and follow-ups

- 27 entries is still a small test; 22 vs 20 among the leaders could be luck. The main finding,
  that the tuned method fell 17 points while the general one did not, is clear.
- C12 ("evidence concerns the assessment target") is an idea, not a set of words, so for C12 the
  search uses the case's own target description and intended environment.
