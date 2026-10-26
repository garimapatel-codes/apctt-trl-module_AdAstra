# 009: Quote quality: what may be quoted as evidence

- **Status:** Accepted
- **Area:** `participant_module/chunker.py`, `participant_module/judge.py` (`usable`, candidate ranking)
- **Date:** 26 October 2026

## Context

Part C (15%): experts read the **first** evidence item of 6 randomly sampled met claims. A quote
that supports the criterion earns 1, a weak one 0, and text that is not on the cited page −1. A
sentence that only states a TRL number is never accepted (§13.4). So every quote has to be a
real, complete sentence from the cited page that actually says something about the criterion.

Reading our first outputs showed junk being quoted: the Secretary of the Interior line, "Suggested
citation…", contents lines, reference-list entries, author bylines, sentences cut off at the end
of a page, and sentences like "the model should not be used for…".

## Decisions

**1. Skip pages that are never evidence.** These are the front matter (everything before the
abstract), contents pages (with or without dotted lines), reference lists, glossaries and
near-empty pages.

**2. Only quote a sentence that passes all of these checks:**
- 6 to 70 words, ending with punctuation, and not mostly numbers;
- not a citation, byline, "accessed on…" line, acknowledgment or reference entry;
- not a sentence that only states a TRL, and not a definition;
- not negated ("not", "cannot", "never");
- not future or advice ("will", "would", "could", "should", "future work"), except for the
  concept criterion, and "may" for operational use.

**3. Rank the remaining sentences.** Points go for criterion cue words, for words from the
assessed target, and for measured numbers (results, calibration, requirements). Points are taken
off for literature citations (outside C01, where citing earlier work is the evidence). The NLI
model then picks the best of the top 5 (note 006).

## Two bugs we found by reading outputs, and fixed

- **The abstract search window was too small.** We looked for the abstract in the first 40% of
  pages. In SDG-045 the abstract is on page 9 of 20 (45%), so the whole report counted as front
  matter and the cover page got quoted. **Fix:** search the first max(10 pages, 40%).
- **A running header looked like front matter.** On SDG-013 page 21, the header line
  "Acknowledgments 13" marked a content page as front matter. **Fix:** front-matter headings
  count only in the first 40% of the report.

## How we check

`evaluation/evaluate.py` writes every quote, with its page and the correct pages, to
`evaluation_quotes.txt`, so we can read them all after each change. It also counts how often the
first quote is on a correct page.

## Consequences and follow-ups

The quote lands on a correct page only about half the time on the studied reports (33 of 64) and
two thirds on the unseen reports (17 of 25). This is the main thing to improve for Submission 2.
