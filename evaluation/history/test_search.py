"""test_search.py - does BM25 find the answer-key pages better on whole pages or on cards?

For every (report, question) in the answer key, it prints at which place the first correct page
appears: 1 = top. Place 3 or better is a hit (the competition only looks at our first 3 pages).
"""

import json
import time
from pathlib import Path

import pypdfium2 as pdfium

from chunker import clean_page, find_repeated_lines, make_cards, page_kind
from simple_bm25 import BM25

PDF_DIR = Path.home() / "work/cases_pdf"
KEY = Path("/mnt/c/Users/aeror/Documents/projects/apctt_iitb/extra_cases/answer_key.json")
CHECKLIST = Path.home() / "work/apctt-participant-kit-0.5.0-cpu/contracts/checklist.official.json"
TOP = 3


def read_pages(path: Path) -> list[str]:
    pdf = pdfium.PdfDocument(str(path))
    pages = [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
    pdf.close()
    return pages


def ranked_pages(page_numbers: list[int], scores: list[float]) -> list[int]:
    """Turn the scores of pieces into a list of distinct pages, best first."""
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    pages: list[int] = []
    for i in order:
        if page_numbers[i] not in pages:
            pages.append(page_numbers[i])
    return pages


key = json.loads(KEY.read_text())
criteria = {c["criterion_id"]: c["description"]
            for c in json.loads(CHECKLIST.read_text())["criteria"]}

rows = []
times = {"pages": 0.0, "cards": 0.0}
for case_id, gold in key.items():
    if case_id.startswith("_"):                       # skip the "_note" entry
        continue
    raw = read_pages(PDF_DIR / f"{case_id}.pdf")

    # Way 1: whole pages, cleaned, with the same junk pages removed (so only the piece size differs)
    repeated = find_repeated_lines(raw)
    page_texts, page_nos = [], []
    for i, text in enumerate(raw):
        clean = clean_page(text, repeated)
        if page_kind(text, clean) == "normal":
            page_texts.append(clean)
            page_nos.append(i + 1)

    # Way 2: cards
    cards, _ = make_cards(raw)
    ways = {
        "pages": (page_texts, page_nos),
        "cards": ([c["text"] for c in cards], [c["page"] for c in cards]),
    }

    places = {}
    for way, (texts, nos) in ways.items():
        t0 = time.perf_counter()
        index = BM25(texts)
        for crit_id, entry in gold.items():
            ranking = ranked_pages(nos, index.scores(criteria[crit_id]))
            found = [ranking.index(p) + 1 for p in entry["pages"] if p in ranking]
            places[(way, crit_id)] = min(found) if found else None
        times[way] += time.perf_counter() - t0

    for crit_id, entry in gold.items():
        rows.append((case_id, crit_id, entry["pages"],
                     places[("pages", crit_id)], places[("cards", crit_id)]))

print(f"{'report':14s} {'question':10s} {'correct pages':14s} {'pages':>6s} {'cards':>6s}")
for case_id, crit_id, gold_pages, p, c in rows:
    print(f"{case_id:14s} {crit_id:10s} {str(gold_pages):14s} {str(p):>6s} {str(c):>6s}")

print()
for col, way in ((3, "pages"), (4, "cards")):
    hits = sum(1 for r in rows if r[col] is not None and r[col] <= TOP)
    total = sum(r[col] if r[col] is not None else 99 for r in rows)
    print(f"{way:6s}: hits (top {TOP}) {hits}/{len(rows)}   sum of places {total}   "
          f"search time {times[way]:.2f} s for all reports")