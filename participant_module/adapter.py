"""participant_module/adapter.py - the class the competition server calls for each case.

Pipeline: read the PDFs -> retrieval (BM25 + TRL keywords, re-read by ms-marco) -> judge (TRL rule,
criterion rules, NLI-picked quotes) -> a result that always follows the data contract.

Time guard (the limit is 180 s for everything, loading included):
  - the careful reader runs only if at least 70 s are left after reading the PDFs
  - the NLI judge stops 35 s before the end
  - if anything unexpected fails, the module still returns a valid result (TRL from the case fields,
    criteria "insufficient evidence"), which scores better than a failed case
Models come from the organizer's read-only model store (APCTT_MODEL_STORE); if one is missing the
module carries on without it.
"""

from __future__ import annotations

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")          # before any Hugging Face import
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

try:                                                   # inside the submission package
    from .judge import Judge, meta_trl
    from .retrieval import Retriever
except ImportError:                                    # run as a plain script in the scratch folder
    from judge import Judge, meta_trl
    from retrieval import Retriever

READER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2/233902d25c440f23af6f7d6e94d2946bac0bee0a"
JUDGE_MODEL = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0-c/bddf8c5411c34ac3565e16e04384fd68b2618dda"
READER_NEEDS_S = 70.0          # use the careful reader only if this much time is left after reading
JUDGE_STOPS_S = 35.0           # the NLI judge stops when this much time is left
THREADS = 4                    # the event machine has 4 cores


def find_model(store: str | None, exact: str) -> str | None:
    """The model folder in the store (exact catalogue path first, then any revision of that model)."""
    if not store:
        return None
    root = Path(store)
    if (root / exact / "config.json").exists():
        return str(root / exact)
    parent = (root / exact).parent
    found = sorted(p for p in parent.glob("*") if (p / "config.json").exists()) if parent.exists() else []
    return str(found[0]) if found else None


def read_pages(path: str, page_count: int | None) -> list[str]:
    """Text of every page (index 0 = page 1). A page that cannot be read becomes an empty string."""
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(path)
    try:
        n = len(pdf) if not page_count else min(len(pdf), page_count)
        pages = []
        for i in range(n):
            try:
                page = pdf[i]
                textpage = page.get_textpage()
                pages.append(textpage.get_text_range())
                textpage.close()
                page.close()
            except Exception:
                pages.append("")
        return pages
    finally:
        pdf.close()


class AssessmentModule:
    def __init__(self) -> None:
        self.checklist: Mapping[str, Any] = {}
        self.criteria: list[dict] = []
        self.retriever: Retriever | None = None
        self.judge: Judge | None = None
        self.notes: list[str] = []

    def load(self, config: Mapping[str, Any], asset_root: Path) -> None:
        self.checklist = config["checklist"]
        self.criteria = [dict(c) for c in self.checklist["criteria"]]
        store = os.environ.get("APCTT_MODEL_STORE")
        reader_dir, judge_dir = find_model(store, READER_MODEL), find_model(store, JUDGE_MODEL)
        try:
            self.retriever = Retriever(reader_dir, THREADS)
        except Exception as exc:                        # reader cannot load: BM25 alone still works
            self.notes.append(f"reader not loaded: {exc!r}")
            self.retriever = Retriever(None)
        try:
            self.judge = Judge(judge_dir, THREADS)
        except Exception as exc:                        # judge cannot load: cue-word quotes still work
            self.notes.append(f"judge not loaded: {exc!r}")
            self.judge = Judge(None)
        if reader_dir is None or judge_dir is None:
            self.notes.append(f"model store {store!r}: reader={reader_dir}, judge={judge_dir}")
        for note in self.notes:
            print(note, file=sys.stderr)

    def _base(self, case: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": case["schema_version"],
            "checklist_version": self.checklist["version"],
            "case_id": case["case_id"],
            "assessment_target": dict(case["assessment_target"]),
            "abstention_reason": None,
            "error_code": None,
        }

    def _fallback(self, case: Mapping[str, Any], why: str) -> dict[str, Any]:
        """A valid result when the pipeline cannot run: TRL from the case fields, nothing claimed."""
        trl = meta_trl(dict(case))[0] or 6
        ids = [c["criterion_id"] for c in self.criteria]
        return {
            **self._base(case),
            "assessment_status": "completed",
            "predicted_trl": trl,
            "criterion_status": {cid: "insufficient evidence" for cid in ids},
            "evidence_reference": {cid: [] for cid in ids},
            "missing_evidence": {cid: f"The report could not be analysed ({why})." for cid in ids},
            "trl_rationale": f"TRL {trl} estimated from the case description only; the report could not be analysed.",
        }

    def assess(self, case: Mapping[str, Any], context: Any) -> dict[str, Any]:
        start = time.monotonic()

        def remaining_s() -> float:
            try:
                return float(context.remaining_ms()) / 1000.0
            except Exception:
                return 170.0 - (time.monotonic() - start)

        try:
            page_counts, documents = {}, []
            for doc in case["documents"]:
                page_counts[doc["document_id"]] = doc.get("page_count")
                documents.append((doc["document_id"], read_pages(doc["path"], doc.get("page_count"))))
            use_reader = remaining_s() > READER_NEEDS_S
            evidence = self.retriever.retrieve(documents, self.criteria, dict(case), use_reader=use_reader)
            deadline = time.monotonic() + max(0.0, remaining_s() - JUDGE_STOPS_S)
            verdict = self.judge.assess(dict(case), self.criteria, evidence, self.retriever.cards, deadline)
        except Exception as exc:
            print(f"pipeline failed: {exc!r}", file=sys.stderr)
            return self._fallback(case, type(exc).__name__)

        # Contract safety: cite only pages that exist; a "met" without evidence becomes insufficient
        status, refs, missing = verdict["criterion_status"], verdict["evidence_reference"], verdict["missing_evidence"]
        for cid in list(status):
            limit = page_counts.get
            refs[cid] = [it for it in refs.get(cid, [])
                         if it["document_id"] in page_counts
                         and isinstance(it["page"], int) and it["page"] >= 1
                         and (not limit(it["document_id"]) or it["page"] <= limit(it["document_id"]))]
            if status[cid] == "met" and not refs[cid]:
                status[cid] = "insufficient evidence"
                missing[cid] = "The supporting page could not be cited."
            if status[cid] != "met":
                missing.setdefault(cid, "No supporting evidence was found.")
        missing = {cid: text for cid, text in missing.items() if status.get(cid) != "met"}

        return {
            **self._base(case),
            "assessment_status": "completed",
            "predicted_trl": int(verdict["predicted_trl"]),
            "criterion_status": status,
            "evidence_reference": refs,
            "missing_evidence": missing,
            "confidence": float(verdict["confidence"]),
            "uncertainty": verdict["uncertainty"],
            "trl_rationale": verdict["trl_rationale"],
            "criterion_rationale": verdict["criterion_rationale"],
        }

    def reset_case(self) -> None:
        """No per-case state is kept beyond the cards of the last case."""
        if self.retriever is not None:
            self.retriever.cards = []

    def close(self) -> None:
        self.retriever = None
        self.judge = None
