"""dump_texts.py - save the cleaned text of every public sample report, one file per report.

The text is exactly what the module sees: read with the module's PDF reader and cleaned by its card
cutter (no front matter, contents pages, reference lists or glossaries), one sentence per line,
each line starting with its page number. We use these files to design and check new clues quickly,
without reading the PDFs again for every try.

Usage:
    ~/work/apctt-env/base/bin/python training/dump_texts.py \
        --kit ~/work/apctt-participant-kit-0.5.0-cpu --pdfs ~/work/public_cases/pdf --out training/texts
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE if (HERE / "participant_module").is_dir() else HERE.parent

parser = argparse.ArgumentParser()
parser.add_argument("--kit", default=str(Path.home() / "work/apctt-participant-kit-0.5.0-cpu"))
parser.add_argument("--pdfs", default=str(Path.home() / "work/public_cases/pdf"))
parser.add_argument("--out", default=str(HERE / "texts"))
parser.add_argument("--module-root", default=str(DEFAULT_ROOT))
args = parser.parse_args()

sys.path.insert(0, args.module_root)
sys.path.insert(0, str(HERE))                                 # trl_features.py lives next to this script
from participant_module.adapter import read_pages            # noqa: E402
from participant_module.chunker import make_cards            # noqa: E402
from trl_features import report_sentences  # noqa: E402

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
cases = json.loads((Path(args.kit) / "contracts/public-cases.json").read_text(encoding="utf-8"))["cases"]
done = 0
for meta in cases:
    pdf = Path(args.pdfs) / f"{meta['case_id']}.pdf"
    if not pdf.is_file():
        print("missing", pdf)
        continue
    cards, _ = make_cards(read_pages(str(pdf), None), document_id="D001")
    page_of = {}
    for card in cards:
        for s in card["sentences"]:
            page_of.setdefault(s, card["page"])
    lines = [f"{page_of[s]}\t{s}" for s in report_sentences(cards)]
    (out / f"{meta['case_id']}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    done += 1
print(f"wrote {done} text files to {out}")
