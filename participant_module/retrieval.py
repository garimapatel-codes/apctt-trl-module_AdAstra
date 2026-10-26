"""retrieval.py - find the evidence pages for every checklist criterion.

How it works (our tests: 81% of correct pages in the top 3 on unseen reports):
  1. cut every page into cards of a few sentences (front matter, contents and references skipped)
  2. quick screen: BM25 + TRL keywords keeps the 10 best cards per criterion          (< 0.1 s)
     (for "evidence concerns the target" the search uses the case's own target description)
  3. careful reader: ms-marco reads a plain question naming the case's technology together with
     each of those 10 cards                                         (about 6 s per report, 4 cores)
  4. merge the reader's order with BM25's order (RRF): the reader nudges, it does not overrule
  5. return the 5 best distinct pages per criterion, each with its best card

Use:
    retriever = Retriever(model_dir)            # None = BM25 only (the safe fallback)
    evidence = retriever.retrieve(documents, criteria, case)
    retriever.cards                              # all cards of the case (the judge reads them)
"""

from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")          # never try the internet (the event has none)
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

try:                                                   # inside the submission package
    from .chunker import make_cards
    from .keywords import keywords_for, question_for, role_of
    from .simple_bm25 import BM25
except ImportError:                                    # run as a plain script in the scratch folder
    from chunker import make_cards
    from keywords import keywords_for, question_for, role_of
    from simple_bm25 import BM25

SHORTLIST = 10        # cards per criterion that the careful reader reads
KEEP_PAGES = 5        # pages returned per criterion
RRF_K = 60            # standard constant for Reciprocal Rank Fusion


def merge(*rankings: list) -> list:
    """Reciprocal Rank Fusion: each item earns 1/(60 + its place) from every list; sums decide the order."""
    score: dict = {}
    for ranking in rankings:
        for place, item in enumerate(ranking, start=1):
            score[item] = score.get(item, 0.0) + 1.0 / (RRF_K + place)
    return sorted(score, key=lambda item: -score[item])


class Retriever:
    def __init__(self, model_dir: str | None, threads: int = 4) -> None:
        """model_dir: folder of the ms-marco reranker. None means BM25 only."""
        self.reader = None
        self.cards: list[dict] = []
        if model_dir:
            import torch
            from sentence_transformers import CrossEncoder

            torch.set_num_threads(threads)
            self.reader = CrossEncoder(model_dir, device="cpu", local_files_only=True)

    def retrieve(self, documents: list[tuple[str, list[str]]], criteria: list[dict],
                 case: dict | None = None, use_reader: bool = True) -> dict[str, list[dict]]:
        """documents: [(document_id, [page texts...]), ...]; criteria: the checklist's criteria list;
        case: the case mapping (its assessment target and environment sharpen the search).
        Returns {criterion_id: [{document_id, page, card_text}, ... best first]}."""
        case = case or {}
        target = (case.get("assessment_target") or {}).get("description") or "the technology"
        environment = case.get("intended_environment") or ""

        cards: list[dict] = []
        for document_id, pages in documents:
            doc_cards, _ = make_cards(pages, document_id=document_id)
            cards += doc_cards
        self.cards = cards
        if not cards:                                   # no readable text at all
            return {c["criterion_id"]: [] for c in criteria}
        index = BM25([c["text"] for c in cards])

        # Quick screen: BM25 + keywords for every criterion
        bm25_order, pairs, owners = {}, [], []
        for c in criteria:
            sentence = c["description"]
            if role_of(sentence) == "target":           # pages about the assessed target itself
                query = f"{target} {environment} {keywords_for(sentence)}"
            else:
                query = f"{sentence} {keywords_for(sentence)}"
            scores = index.scores(query)
            order = sorted(range(len(cards)), key=lambda i: -scores[i])
            bm25_order[c["criterion_id"]] = order
            question = question_for(sentence, target)
            for i in order[:SHORTLIST]:
                pairs.append((question, cards[i]["text"]))
                owners.append((c["criterion_id"], i))

        # Careful reader: all criteria in one batch
        reader_order: dict[str, list[int]] = {}
        if self.reader is not None and use_reader and pairs:
            scores = self.reader.predict(pairs, batch_size=16)
            scored: dict[str, list[tuple[float, int]]] = {}
            for (crit_id, i), s in zip(owners, scores):
                scored.setdefault(crit_id, []).append((float(s), i))
            reader_order = {k: [i for _, i in sorted(v, key=lambda x: -x[0])] for k, v in scored.items()}

        evidence: dict[str, list[dict]] = {}
        for c in criteria:
            crit_id = c["criterion_id"]
            order = bm25_order[crit_id]
            short, rest = order[:SHORTLIST], order[SHORTLIST:]
            final = (merge(short, reader_order[crit_id]) if crit_id in reader_order else short) + rest
            items, seen = [], set()
            for i in final:                             # best card per distinct page, best first
                where = (cards[i]["document_id"], cards[i]["page"])
                if where in seen:
                    continue
                seen.add(where)
                items.append({"document_id": cards[i]["document_id"], "page": cards[i]["page"],
                              "card_text": cards[i]["text"]})
                if len(items) == KEEP_PAGES:
                    break
            evidence[crit_id] = items
        return evidence
