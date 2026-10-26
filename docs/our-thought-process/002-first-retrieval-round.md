# 002: First retrieval round (BM25 vs embeddings vs reranker)

- **Status:** Superseded by [004](004-models-on-cpu.md) and [005](005-unseen-reports-exam.md)
- **Area:** finding the evidence pages for each checklist criterion
- **Date:** 24 October 2026

## Context

For every checklist criterion the module has to cite the pages that support it. The score
looks only at the **first 3 distinct pages** we cite (problem description §13.3), so the
question was: which method puts a correct page into our top 3 most often, inside the time
limit of 3 minutes per case (model loading included), on a CPU?

## Options considered

| Option | Idea | Cost |
|---|---|---|
| Plain BM25 | Classic word matching between the criterion and each page | Almost free |
| Improved BM25 | BM25 plus light stemming, and skipping reference lists, contents and blank pages | Almost free |
| BM25 + all-MiniLM-L6-v2 embeddings | Add a "meaning" match and merge both rankings (reciprocal rank fusion, RRF) | Seconds |
| + ms-marco-MiniLM reranker | A small model re-reads the best pages with the criterion | Seconds |
| granite-embedding-english-r2 | A larger embedding model on whole pages | Much more |

## How we tested

- **Data:** the 3 public sample reports USGS-SDG-012, -040 and -061.
- **Answer key:** 12 (report, criterion) entries with the correct pages, written by hand from
  reading the reports. These are our labels, not the experts'.
- **Query:** the official checklist sentence of each criterion.
- **Measure:** is a correct page in the top 3? Plus the sum of the best correct rank per entry
  (lower is better), and the time per case.
- **Machine:** our laptop (Ryzen 5 7530U), WSL limited to 4 cores, CPU only.

## Results

| Configuration | Correct page in top 3 | Sum of ranks | Time per case |
|---|---|---|---|
| Plain BM25 | 8/12 | 50 | about 0.1–0.3 s |
| **Improved BM25** | **9/12** | **46** | **0.10–0.26 s** |
| Improved BM25 + all-MiniLM (RRF) | 7/12 | 60 | 4–9 s |
| + ms-marco reranker (top 6 per criterion) | 6/12 | 65 | 9–19 s |
| granite-embedding-english-r2, whole pages | not finished | – | over 77 s for 24 pages |

Two smaller findings:

- Removing stop words made BM25 **worse** (6–7/12), so we left it out.
- Counting years on a page to detect reference lists failed: normal prose pages cite years
  just as often. We detect reference lists by counting lines that look like "Surname, A." instead.

## Decision (at the time)

Use improved BM25. The models cost 40–100 times more time and did not help on this sample.

## Why this was not the end

- 12 test entries is tiny: one entry is 8 percentage points.
- The models were fed badly. all-MiniLM reads only 256 tokens, but our pages had 500–800, so
  it saw about a third of each page. The reranker was given formal checklist sentences, not
  questions.
- Soon after, BM25 failed on new reports, because it only matches words and new reports use
  different words. That led to notes 003–005.
