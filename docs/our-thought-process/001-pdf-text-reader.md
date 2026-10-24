# 001: Choosing the PDF text reader (pypdf vs pypdfium2)

- **Status:** Accepted
- **Area:** PDF reading inside `participant_module/adapter.py`

## Context

Our module has to read technical reports (PDFs) and judge evidence from them, inside
a fixed time budget of about three minutes per report. Scoring rewards correct
results, evidence cited on the correct pages, and quotes that genuinely appear in the
report. That last point matters here: a quote is only genuine if the text we extract
matches what is really on the page.

So the reader affects us in two ways: **speed** (time left for the judging step) and
**text fidelity** (clean, faithful text we can quote and cite by page number).

The base environment provided for the challenge already includes several PDF readers
(pypdf, pdfplumber, pdfminer-six, pypdfium2), so nothing extra has to be installed
for either option below.

## Options considered

| | pypdf | pypdfium2 |
|---|---|---|
| What it is | Pure-Python library that parses the PDF and decodes fonts itself | Python wrapper around PDFium, the C++ PDF engine used in Chrome |
| In its favour | Simple, easy to read and debug | Mature engine, usually faster and more tolerant of unusual fonts; can also render a page as an image, which OCR would need |
| Against | Slower; odd fonts can give wrong characters (we saw a `fontTools` warning) | Less familiar; line-break and spacing details differ |

## How we started, and the correction

We first leaned towards **pypdf** because it was familiar and had already worked on
all three sample reports. That was a preference, not a measurement. We had not shown
it was the better reader, and we said so before building anything on it.

One more fact tipped us towards testing: if we later add OCR for scanned pages, we
need pypdfium2 anyway, because OCR works on page images and pypdfium2 is the tool
that produces them. A ten-minute comparison was cheap next to the cost of building
on the wrong foundation.

We also agreed on scope: for now we handle **text-based PDFs only**. All three
sample reports are text-based. Whether any hidden reports are scans is unknown, so
OCR stays a possible later fallback and nothing we write now blocks it.

## How we tested

- **Data:** the same three real sample reports (USGS publications) for both tools:
  SDG-012 (24 pages), SDG-040 (22 pages) and SDG-061 (36 pages).
- **What we measured for each tool and report:** wall-clock time to read every page,
  total characters extracted, and how many pages were near-empty (under 200
  characters, as a cheap way to spot pages with no real text).
- **Qualitative check:** we printed the first 500 characters of the same page
  (page 5 of SDG-040) from both tools and compared them by eye.
- **Sanity check beforehand:** we ran the pypdfium2 calls on a tiny generated PDF
  first, to make sure the commands worked before asking anyone to run the full
  comparison.
- **Fairness:** both tools were wrapped in the same shape of function (PDF path in,
  list of page texts out, page 1 at index 0), so the comparison measured the
  readers and nothing else.

## Results

| Report | Pages | pypdf time | pypdfium2 time | Characters found (pypdf → pypdfium2) |
|---|---|---|---|---|
| SDG-012 | 24 | 1.0 s | 0.1 s | 42,488 → 42,797 |
| SDG-040 | 22 | 0.9 s | 0.1 s | 63,794 → 64,748 |
| SDG-061 | 36 | 3.1 s | 0.2 s | 103,643 → 105,535 |

What the numbers say:

- **Speed:** pypdfium2 was roughly 10 to 15 times faster on every report. Extrapolating
  (an estimate, not a measurement), a 200-page report would take about 2 seconds
  instead of about 20, leaving more of the three-minute budget for the judging step.
- **Completeness:** pypdfium2 found about 1 to 2 percent *more* text, and both tools
  agreed on which pages were near-empty. It also did not raise the `fontTools`
  warning that pypdf did.
- **A difference we had to handle:** where a word is hyphenated across a line break
  (for example "Metro-politan" on page 5 of SDG-040), pypdfium2 leaves a hidden marker
  character that displays as `￾`, while pypdf writes a plain hyphen. If that marker
  stayed in a quoted sentence, a reviewer comparing our quote to the real page would
  see a mismatch. This is a quote-fidelity risk, and it is easy to remove.

## Decision

1. Use **pypdfium2 as the main reader**, because it is much faster and slightly more
   complete on our data.
2. Add a small **cleanup step** that removes the hidden hyphenation marker from every
   page before the text is used for quoting.
3. Keep **pypdf as a backup** in case pypdfium2 ever fails on an unusual file.
4. Keep the reading inside one small function (`read_pages`), so changing the reader
   later is a one-place change.
5. **Not now:** OCR for scanned pages. If a page has almost no text we note it and
   move on. We revisit OCR only once the main pipeline works and if there is evidence
   that hidden reports include scans.

This was implemented in the commit "Read PDF pages with pypdfium2 inside assess".

## Consequences and follow-ups

- The cleanup step is now part of quote correctness. If we ever see other odd
  characters in extracted text, they belong in the same step.
- Our evidence is three text-based reports. If hidden reports behave differently
  (scans, unusual layouts), re-run the comparison and add a new note rather than
  editing this one.
- Reading time is small, but the three-minute limit is a hard constraint, so keep an
  eye on total time per report as the judging logic grows.
- Search terms for learning more: "PDF content stream text extraction", "PDFium",
  "Unicode soft hyphen".
