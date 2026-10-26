# Our thought process

This folder records **why** we made each technical choice in this project, and the
evidence we gathered before committing to it. The code shows *what* we built; these
notes show *how we decided*, so that we (and any reviewer) can follow the reasoning
and challenge it if the facts change.

## How to read these notes

Each note is a short decision record with the same sections:

1. **Context**: the question we faced and why it mattered.
2. **Options considered**: the alternatives, with their trade-offs.
3. **How we tested**: the method, in words. The scripts and answer keys we test with
   are in [`evaluation/`](../../evaluation/README.md).
4. **Results**: what we measured, with the numbers.
5. **Decision**: what we chose and what we deliberately left for later.
6. **Consequences and follow-ups**: what the choice commits us to, and what to watch.

Notes are numbered in the order they were made and are not rewritten after the fact.
If a decision changes, we add a new note that supersedes the old one and mark the old
note's status accordingly. Notes 002–011 were written up on 26 October 2026 from our
test logs, after the decisions were made; the numbers are the ones we measured at the
time.

## Index

| # | Note | Status |
|---|------|--------|
| 001 | [Choosing the PDF text reader: pypdf vs pypdfium2](001-pdf-text-reader.md) | Accepted |
| 002 | [First retrieval round: BM25 vs embeddings vs reranker](002-first-retrieval-round.md) | Superseded by 004, 005 |
| 003 | [A fuller answer key, cards vs whole pages, and TRL keywords](003-answer-key-cards-and-trl-keywords.md) | Accepted |
| 004 | [Models on a CPU: meaning-matcher and rerankers](004-models-on-cpu.md) | Superseded by 005 |
| 005 | [The unseen-reports test changes the retrieval choice](005-unseen-reports-exam.md) | Accepted |
| 006 | [Deciding met or not met: NLI judge vs the usual pattern](006-judging-met-or-not.md) | Accepted |
| 007 | [The TRL rule and the criterion rules](007-trl-rule-and-criterion-rules.md) | Accepted |
| 008 | [One labelling rule for our answer keys](008-answer-keys-one-rule.md) | Accepted |
| 009 | [Quote quality: what may be quoted as evidence](009-quote-quality.md) | Accepted |
| 010 | [Version 2: results, timing and robustness](010-version-2-results.md) | Accepted |
| 011 | [Packaging Submission 1 and checking the zip locally](011-packaging-and-local-check.md) | Accepted |

## The path in one paragraph

We started with plain word matching (BM25), which looked best on 3 reports (002), then
learned that the checklist's NASA wording differs from how reports talk, and added TRL
keyword lists (003). Large models were too slow on a CPU, so we let BM25 shortlist and a
small reranker re-read only the shortlist (004). A test on reports we had never opened
showed our tuned word lists overfitted, while the reranker generalised, which settled
retrieval (005). For met / not met, the scoring formula and a simple baseline showed
that a heavy NLI judge was slower and worse than starting from the usual pattern of
these reports, so the NLI model now only picks the quote (006). The TRL comes from what
is being assessed (007). We made our own answer keys consistent before trusting any
number (008), cleaned up what may be quoted (009), measured the whole module (010), and
checked the packed zip on the kit's own server before submitting (011).

## Principle

We test before we apply. A tool is not chosen because it is familiar or because it
"should" be fine; it is chosen because we measured it on our own data and can explain
the result.
