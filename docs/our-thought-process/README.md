# Our thought process

This folder records **why** we made each technical choice in this project, and the
evidence we gathered before committing to it. The code shows *what* we built; these
notes show *how we decided*, so that we (and any reviewer) can follow the reasoning
and challenge it if the facts change.

## How to read these notes

Each note is a short decision record with the same sections:

1. **Context**: the question we faced and why it mattered.
2. **Options considered**: the alternatives, with their trade-offs.
3. **How we tested**: the method, in words (the scripts are not kept here).
4. **Results**: what we measured, with the numbers.
5. **Decision**: what we chose and what we deliberately left for later.
6. **Consequences and follow-ups**: what the choice commits us to, and what to watch.

Notes are numbered in the order they were made and are not rewritten after the fact.
If a decision changes, we add a new note that supersedes the old one and mark the old
note's status accordingly.

## Index

| # | Note | Status |
|---|------|--------|
| 001 | [Choosing the PDF text reader: pypdf vs pypdfium2](001-pdf-text-reader.md) | Accepted |

## Principle

We test before we apply. A tool is not chosen because it is familiar or because it
"should" be fine; it is chosen because we measured it on our own data and can explain
the result.
