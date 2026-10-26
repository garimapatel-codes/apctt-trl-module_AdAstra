"""test_keywords.py - find the best way to pick the 3 evidence pages.

All ways start from BM25 + keywords, which searches every card in under a second.
  cd-kw   BM25 + keywords on cards                         (our best so far: 37/55)
  pg-kw   BM25 + keywords on whole pages                   (38/55)
  pg+cd   pages and cards merged                           (two views of the same report)
  msm     ms-marco re-reads the 10 best cards, asked a plain question about this case's technology
  msm+bm  ms-marco merged with BM25 (it can nudge, not overrule)
  all     pages + cards + ms-marco merged
Each number is the place of the first correct page (1 = top); 3 or better is a hit.

Usage:  python test_keywords.py                                  (the main 9 reports)
        python test_keywords.py <answer-key.json> <pdf-folder>    (any other set, e.g. the holdout)
"""

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")          # never try the internet (the event has none)
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import json
import sys
import time
from pathlib import Path

import pypdfium2 as pdfium
import torch
from sentence_transformers import CrossEncoder

from chunker import clean_page, find_repeated_lines, make_cards, page_kind
from keywords import keywords_for, question_for
from simple_bm25 import BM25

# Optional: python test_keywords.py <answer-key.json> <pdf-folder>  (defaults = the main 9 reports)
KEY = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/mnt/c/Users/aeror/Documents/projects/apctt_iitb/extra_cases/answer_key.json")
PDF_DIR = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / "work/cases_pdf"
KIT = Path.home() / "work/apctt-participant-kit-0.5.0-cpu/contracts"
MODELS = Path.home() / "work/models"
SHORTLIST = 10    # how many BM25 cards per question the reranker reads
RRF_K = 60        # standard constant for Reciprocal Rank Fusion
TOP = 3
WAYS = ["cd-kw", "pg-kw", "pg+cd", "msm", "msm+bm", "all"]

torch.set_num_threads(4)                              # the event machine has 4 cores


def model_folder(pattern: str) -> str:
    found = sorted(MODELS.glob(pattern))
    if not found:
        raise SystemExit(f"model not found: {MODELS}/{pattern}")
    return str(found[0])


def read_pages(path: Path) -> list[str]:
    pdf = pdfium.PdfDocument(str(path))
    pages = [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
    pdf.close()
    return pages


def order_by(scores) -> list[int]:
    """Positions of the pieces, best score first."""
    return sorted(range(len(scores)), key=lambda i: -scores[i])


def pages_in_order(piece_order: list[int], page_numbers: list[int]) -> list[int]:
    """Turn an order of pieces into a list of distinct pages, best first."""
    pages: list[int] = []
    for i in piece_order:
        if page_numbers[i] not in pages:
            pages.append(page_numbers[i])
    return pages


def merge(*rankings: list) -> list:
    """Reciprocal Rank Fusion of several best-first lists (of pages or of cards).
    Each item earns 1/(60 + its place) from every list it appears in; the sums give the merged order."""
    score: dict = {}
    for ranking in rankings:
        for place, item in enumerate(ranking, start=1):
            score[item] = score.get(item, 0.0) + 1.0 / (RRF_K + place)
    return sorted(score, key=lambda item: -score[item])


def place_of(gold_pages: list[int], ranking: list[int]):
    found = [ranking.index(p) + 1 for p in gold_pages if p in ranking]
    return min(found) if found else None


print(f"answer key: {KEY}")
print(f"PDF folder: {PDF_DIR}")
key = json.loads(KEY.read_text())
criteria = {c["criterion_id"]: c["description"]
            for c in json.loads((KIT / "checklist.official.json").read_text())["criteria"]}
targets = {c["case_id"]: c["assessment_target"]["description"]
           for c in json.loads((KIT / "public-cases.json").read_text())["cases"]}

t0 = time.perf_counter()
reranker = CrossEncoder(model_folder("cross-encoder/ms-marco*/*"), device="cpu", local_files_only=True)
print(f"loaded ms-marco in {time.perf_counter() - t0:.1f} s")

rows = []
rerank_time, n_pairs, n_reports = 0.0, 0, 0
for case_id, gold in key.items():
    if case_id.startswith("_"):
        continue
    n_reports += 1
    raw = read_pages(PDF_DIR / f"{case_id}.pdf")
    repeated = find_repeated_lines(raw)
    page_texts, page_nos = [], []
    for i, text in enumerate(raw):
        clean = clean_page(text, repeated)
        if page_kind(text, clean) == "normal":
            page_texts.append(clean)
            page_nos.append(i + 1)
    cards, _ = make_cards(raw)
    card_nos = [c["page"] for c in cards]
    page_index = BM25(page_texts)
    card_index = BM25([c["text"] for c in cards])
    target = targets.get(case_id, "the technology")

    # Shortlist and rerank ALL checklist questions (as the real module must), for a realistic time
    bm25_cards, pairs, owners = {}, [], []
    for crit_id, sentence in criteria.items():
        order = order_by(card_index.scores(sentence + " " + keywords_for(sentence)))
        bm25_cards[crit_id] = order
        question = question_for(sentence, target)
        for i in order[:SHORTLIST]:
            pairs.append((question, cards[i]["text"]))
            owners.append((crit_id, i))
    t1 = time.perf_counter()
    scores = reranker.predict(pairs, batch_size=16)
    rerank_time += time.perf_counter() - t1
    n_pairs += len(pairs)
    reranked: dict[str, list[tuple[float, int]]] = {}
    for (crit_id, i), s in zip(owners, scores):
        reranked.setdefault(crit_id, []).append((float(s), i))
    print(f"{case_id}: {len(cards)} cards, {len(pairs)} pairs reranked")

    for crit_id, entry in gold.items():
        sentence = criteria[crit_id]
        bm25_order = bm25_cards[crit_id]
        short = bm25_order[:SHORTLIST]
        rest = bm25_order[SHORTLIST:]
        msm_short = [i for s, i in sorted(reranked[crit_id], key=lambda x: -x[0])]

        cd_kw = pages_in_order(bm25_order, card_nos)
        pg_kw = pages_in_order(order_by(page_index.scores(sentence + " " + keywords_for(sentence))), page_nos)
        msm = pages_in_order(msm_short + rest, card_nos)
        msm_bm = pages_in_order(merge(short, msm_short) + rest, card_nos)
        rankings = [cd_kw, pg_kw, merge(pg_kw, cd_kw), msm, msm_bm, merge(pg_kw, cd_kw, msm_bm)]

        in_shortlist = any(p in {card_nos[i] for i in short} for p in entry["pages"])
        rows.append((case_id, crit_id, entry["pages"], [place_of(entry["pages"], r) for r in rankings],
                     in_shortlist))

print()
print(f"{'report':14s} {'question':10s} {'correct':10s} " + " ".join(f"{w:>6s}" for w in WAYS))
for case_id, crit_id, gold_pages, places, _ in rows:
    print(f"{case_id:14s} {crit_id:10s} {str(gold_pages):10s} " + " ".join(f"{str(p):>6s}" for p in places))

print()
results = []
for k, way in enumerate(WAYS):
    col = [r[3][k] for r in rows]
    hits = sum(1 for p in col if p is not None and p <= TOP)
    firsts = sum(1 for p in col if p == 1)
    total = sum(p if p is not None else 99 for p in col)
    results.append((hits, -total, way))
    print(f"{way:7s}: hits (top {TOP}) {hits}/{len(col)}   first place {firsts}   sum of places {total}")
print(f"correct page inside the BM25 shortlist: {sum(1 for r in rows if r[4])}/{len(rows)}")
print(f"ms-marco: {n_pairs} pairs in {rerank_time:.1f} s (about {rerank_time / n_reports:.1f} s per report)")
best = max(results)
print(f"\nBEST: {best[2]}  ({best[0]}/{len(rows)} hits)")