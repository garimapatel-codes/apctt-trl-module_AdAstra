"""evaluate.py - run the real module on every hand-labelled report and score it like the organizer.

For each report it:
  1. builds the case exactly as the server passes it (case fields, PDF path, page count by pypdf)
  2. creates a fresh AssessmentModule, calls load() and assess() (like the server: cold per case)
  3. checks the result with the kit's own validator (an invalid result would score 0)
  4. scores it:  A = TRL part  (exact 1, off by one 0.5, else 0; against the organizer's estimate)
                 B = criteria part = (2 x met part + 1 x not-met part) / 3   (official formula)
                 quote check = share of met claims whose FIRST cited page is a correct page
It prints one line per report, the totals, and writes every quote to evaluation_quotes.txt
and every result to results/<case>.json so you can read them.

Usage (defaults = our two answer keys):
    python evaluate.py
    python evaluate.py --only holdout
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
HOME = Path.home()
WIN = Path("/mnt/c/Users/aeror/Documents/projects/apctt_iitb")

parser = argparse.ArgumentParser()
DEFAULT_ROOT = HERE if (HERE / "participant_module").is_dir() else HERE.parent   # final_code/ or the repo
parser.add_argument("--module-root", default=str(DEFAULT_ROOT), help="folder that contains participant_module/")
parser.add_argument("--kit", default=str(HOME / "work/apctt-participant-kit-0.5.0-cpu"))
parser.add_argument("--models", default=os.environ.get("APCTT_MODEL_STORE", str(HOME / "work/models")))
parser.add_argument("--main-key", default=str(HERE / "keys/answer_key_main_v4.json"))
parser.add_argument("--main-pdfs", default=str(HOME / "work/cases_pdf"))
parser.add_argument("--holdout-key", default=str(HERE / "keys/answer_key_holdout_v2.json"))
parser.add_argument("--holdout-pdfs", default=str(WIN / "holdout"))
parser.add_argument("--only", choices=["main", "holdout"], default=None)
args = parser.parse_args()

os.environ["APCTT_MODEL_STORE"] = args.models
sys.path.insert(0, args.module_root)
sys.path.insert(0, str(Path(args.kit) / "src"))

from pypdf import PdfReader                                   # the server counts pages with pypdf

from apctt_contracts.config import Checklist                  # the kit's own result checker
from apctt_contracts.results import validate_result
from participant_module.adapter import AssessmentModule

KIT = Path(args.kit)
checklist_json = json.loads((KIT / "contracts/checklist.official.json").read_text())
checklist = Checklist(**checklist_json)
cases_meta = {c["case_id"]: c for c in json.loads((KIT / "contracts/public-cases.json").read_text())["cases"]}
config = {
    "checklist": {"version": checklist_json["version"], "criteria": checklist_json["criteria"]},
    "module": {"settings": {}},
    "compute": {"device": "cpu", "seed": 42},
}

sets = []
if args.only in (None, "main"):
    sets.append(("main", Path(args.main_key), Path(args.main_pdfs)))
if args.only in (None, "holdout"):
    sets.append(("holdout", Path(args.holdout_key), Path(args.holdout_pdfs)))

out_dir = HERE / "results"
out_dir.mkdir(exist_ok=True)
quotes_file = open(HERE / "evaluation_quotes.txt", "w", encoding="utf-8")

totals = {}
for set_name, key_path, pdf_dir in sets:
    key = json.loads(key_path.read_text())
    a_scores, a_six, met_hits, not_hits, quote_hits, n_valid, n_cases, times = [], [], [], [], [], 0, 0, []
    print(f"\n=== {set_name}: {key_path.name}")
    print(f"{'report':14s} {'TRL':>4s} {'org':>4s} {'A':>4s}  {'met part':>9s} {'not part':>9s}  {'valid':5s} {'load':>5s} {'assess':>6s}")
    for case_id, gold in key.items():
        if case_id.startswith("_"):
            continue
        meta = cases_meta[case_id]
        pdf_path = pdf_dir / f"{case_id}.pdf"
        case = {
            "schema_version": "apctt-pdf-example-v1",
            "input_profile": "pdf_report",
            "checklist_version": checklist_json["version"],
            "case_id": case_id,
            "title": meta["title"],
            "assessment_as_of": None,
            "assessment_target": meta["assessment_target"],
            "intended_application": meta["intended_application"],
            "intended_environment": meta["intended_environment"],
            "sdg_targets": meta.get("sdg_targets", []),
            "documents": [{**meta["document"], "page_count": len(PdfReader(str(pdf_path)).pages),
                           "path": str(pdf_path)}],
        }
        t0 = time.monotonic()
        module = AssessmentModule()
        module.load(config, HERE)
        t1 = time.monotonic()
        load_s = t1 - t0
        context = SimpleNamespace(remaining_ms=lambda: (180.0 - load_s - (time.monotonic() - t1)) * 1000.0)
        result = module.assess(case, context)
        module.reset_case()
        module.close()
        t2 = time.monotonic()
        times.append((load_s, t2 - t1))
        issues = validate_result(json.loads(json.dumps(result)), case=case, checklist=checklist)
        valid = not issues
        n_valid += valid
        n_cases += 1
        (out_dir / f"{case_id}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))

        org = meta["reference_labels"]["estimated_trl"]
        trl = result.get("predicted_trl")
        d = abs(trl - org) if isinstance(trl, int) else 9
        a_scores.append(1.0 if d == 0 else 0.5 if d == 1 else 0.0)
        a_six.append(1.0 if org == 6 else 0.5 if abs(org - 6) == 1 else 0.0)

        mh = nh = mn = nn = 0
        quotes_file.write(f"\n##### {case_id}  predicted TRL {trl} (organizer {org})\n")
        for crit in checklist_json["criteria"]:
            cid = crit["criterion_id"]
            status = result["criterion_status"].get(cid)
            items = result["evidence_reference"].get(cid, [])
            pages = []
            for it in items:
                if (it["document_id"], it["page"]) not in pages:
                    pages.append((it["document_id"], it["page"]))
            first3 = [p for _, p in pages[:3]]
            if cid in gold:                                   # experts would say met
                mn += 1
                hit = status == "met" and any(p in gold[cid]["pages"] for p in first3)
                mh += hit
                met_hits.append(hit)
                if status == "met":
                    q_ok = bool(items) and items[0]["page"] in gold[cid]["pages"]
                    quote_hits.append(q_ok)
            else:                                             # experts would say not met
                nn += 1
                nh += status != "met"
                not_hits.append(status != "met")
            mark = ("KEY-MET " if cid in gold else "key-not ") + (status or "?")
            span = items[0].get("supporting_span", "") if items else result["missing_evidence"].get(cid, "")
            page = f"p{items[0]['page']}" if items else "-"
            gold_pages = gold[cid]["pages"] if cid in gold else []
            quotes_file.write(f"  {cid} [{mark}] {page} pages {first3} gold {gold_pages}\n      {span[:300]}\n")
        print(f"{case_id:14s} {str(trl):>4s} {org:>4d} {a_scores[-1]:4.1f}  {mh:>4d}/{mn:<4d} {nh:>4d}/{nn:<4d}  "
              f"{'yes' if valid else 'NO':5s} {load_s:5.1f} {t2 - t1:6.1f}")
        if issues:
            for issue in issues[:5]:
                print(f"      invalid: {issue.path} {issue.rule}")

    A = sum(a_scores) / len(a_scores)
    met_part = sum(met_hits) / max(1, len(met_hits))
    not_part = sum(not_hits) / max(1, len(not_hits))
    B = (2 * met_part + not_part) / 3
    totals[set_name] = (A, B)
    print(f"--- {set_name}: valid {n_valid}/{n_cases} | A (TRL) {A:.3f}  [always-6 {sum(a_six) / len(a_six):.3f}] | "
          f"B (criteria) {B:.3f}  [met part {met_part:.2f}, not part {not_part:.2f}; always-abstain baseline 0.333] | "
          f"quote on a correct page {sum(quote_hits)}/{len(quote_hits)}")
    worst = max(l + a for l, a in times)
    print(f"    time per case (load + assess): mean {sum(l + a for l, a in times) / len(times):.1f} s, worst {worst:.1f} s (limit 180 s)")

quotes_file.close()
print("\nEstimated A + B part of the score (0.45 A + 0.40 B, out of 0.85; C needs the experts):")
for name, (A, B) in totals.items():
    print(f"  {name:8s}: {0.45 * A + 0.40 * B:.3f}")
print(f"Quotes: {HERE / 'evaluation_quotes.txt'}   Results: {out_dir}")
