"""participant_module/adapter.py - minimal valid AssessmentModule (always abstains)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import pypdfium2 as pdfium


def read_pages(path: str) -> list[str]:
    """Return one cleaned text string per page (index 0 is page 1)."""
    pdf = pdfium.PdfDocument(path)
    pages = []
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            textpage.close()
            page.close()
            text = text.replace("\ufffe", "").replace("\r\n", "\n")
            pages.append(text)
    finally:
        pdf.close()
    return pages


class AssessmentModule:
    def __init__(self) -> None:
        self.checklist: Mapping[str, Any] = {}
        self.settings: Mapping[str, Any] = {}

    def load(self, config: Mapping[str, Any], asset_root: Path) -> None:
        self.checklist = config["checklist"]
        self.settings = config["module"]["settings"]

    def assess(self, case: Mapping[str, Any], context: Any) -> dict[str, Any]:
        ids = [c["criterion_id"] for c in self.checklist["criteria"]]
        pages_by_doc = {}
        for doc in case["documents"]:
            pages = read_pages(doc["path"])
            pages_by_doc[doc["document_id"]] = pages
        return {
            "schema_version": case["schema_version"],
            "checklist_version": self.checklist["version"],
            "case_id": case["case_id"],
            "assessment_target": dict(case["assessment_target"]),
            "assessment_status": "abstained",
            "predicted_trl": None,
            "criterion_status": {cid: "insufficient evidence" for cid in ids},
            "evidence_reference": {cid: [] for cid in ids},
            "missing_evidence": {cid: "No evidence rule is implemented yet." for cid in ids},
            "abstention_reason": "insufficient evidence",
            "error_code": None,
        }

    def reset_case(self) -> None:
        pass

    def close(self) -> None:
        pass
