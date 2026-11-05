"""build_features.py - turn the 99 public sample reports into one table of clues (a CSV file).

For each case in the kit's contracts/public-cases.json it:
  1. builds the case as the server passes it (case fields + page count),
  2. reads the PDF with the module's own reader (adapter.read_pages),
  3. cuts it into cards with the module's own card cutter (chunker.make_cards),
  4. measures the clues with training/trl_features.py,
  5. writes one row: case_id, the organizer's estimated TRL (the "answer"), then the clues.

Usage (from the folder that contains participant_module/, or give --module-root):
    ~/work/apctt-env/base/bin/python training/build_features.py \
        --kit ~/work/apctt-participant-kit-0.5.0-cpu --pdfs ~/work/public_cases/pdf --out training/features.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE if (HERE / "participant_module").is_dir() else HERE.parent

parser = argparse.ArgumentParser()
parser.add_argument("--kit", default=str(Path.home() / "work/apctt-participant-kit-0.5.0-cpu"))
parser.add_argument("--pdfs", default=str(Path.home() / "work/public_cases/pdf"))
parser.add_argument("--out", default=str(HERE / "features.csv"))
parser.add_argument("--module-root", default=str(DEFAULT_ROOT))
parser.add_argument("--only", nargs="*", help="only these case IDs (for a quick test)")
args = parser.parse_args()

sys.path.insert(0, args.module_root)
sys.path.insert(0, str(HERE))                                 # trl_features.py lives next to this script
from participant_module.adapter import read_pages            # noqa: E402  (the module's own reader)
from participant_module.chunker import make_cards            # noqa: E402  (the module's own card cutter)
from trl_features import FEATURE_NAMES, report_features  # noqa: E402

from pypdf import PdfReader                                   # noqa: E402  (the server counts pages with pypdf)

cases = json.loads((Path(args.kit) / "contracts/public-cases.json").read_text(encoding="utf-8"))["cases"]
if args.only:
    cases = [c for c in cases if c["case_id"] in set(args.only)]

rows, missing, start = [], [], time.monotonic()
for n, meta in enumerate(cases, 1):
    pdf = Path(args.pdfs) / f"{meta['case_id']}.pdf"
    if not pdf.is_file():
        missing.append(meta["case_id"])
        continue
    case = {
        "case_id": meta["case_id"],
        "title": meta["title"],
        "assessment_target": meta["assessment_target"],
        "intended_application": meta["intended_application"],
        "intended_environment": meta["intended_environment"],
        "documents": [{**meta["document"], "page_count": len(PdfReader(str(pdf)).pages), "path": str(pdf)}],
    }
    t0 = time.monotonic()
    cards = []
    for doc in case["documents"]:
        doc_cards, _ = make_cards(read_pages(doc["path"], doc["page_count"]), document_id=doc["document_id"])
        cards.extend(doc_cards)
    clues = report_features(case, cards)
    rows.append({"case_id": meta["case_id"],
                 "organizer_trl": meta["reference_labels"]["estimated_trl"],
                 "pages": case["documents"][0]["page_count"],
                 **clues})
    print(f"{n:3d}/{len(cases)} {meta['case_id']}  TRL {rows[-1]['organizer_trl']}  rule {int(clues['rule_trl'])}  "
          f"{rows[-1]['pages']:4d} pages  {time.monotonic() - t0:5.1f} s", flush=True)

out = Path(args.out)
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["case_id", "organizer_trl", "pages", *FEATURE_NAMES])
    writer.writeheader()
    writer.writerows(rows)

print(f"\nwrote {len(rows)} rows to {out}  ({time.monotonic() - start:.0f} s)")
if missing:
    print(f"MISSING PDFs ({len(missing)}): {' '.join(missing)}")
