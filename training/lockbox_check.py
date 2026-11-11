"""lockbox_check.py - open the lockbox ONCE: old TRL rule vs new TRL rule on the 29 sealed reports.

Old rule = Submission 1 (its answers are the "rule_trl" column of training/features.csv, built on 5 Nov
with the Submission 1 module). New rule = participant_module/judge.py as it is now (groups B and C,
note 013). Both are scored with the official part-A points against the organizer's estimated TRL.

It also re-scores the 70 open reports, to check that the laptop reproduces the numbers measured during
design (old 0.914, new 0.943).

Usage (from final_code/ or the repository root):
    ~/work/apctt-env/base/bin/python training/lockbox_check.py --kit ~/work/apctt-participant-kit-0.5.0-cpu
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE if (HERE / "participant_module").is_dir() else HERE.parent

ap = argparse.ArgumentParser()
ap.add_argument("--kit", default=str(Path.home() / "work/apctt-participant-kit-0.5.0-cpu"))
ap.add_argument("--texts", default=str(HERE / "texts"))
args = ap.parse_args()

sys.path.insert(0, str(ROOT))
from participant_module.judge import decide_trl            # noqa: E402  (the NEW rule)


def points(p: int, t: int) -> float:
    return 1.0 if p == t else 0.5 if abs(p - t) == 1 else 0.0


def report_text(case_id: str) -> str:
    """The saved cleaned text; a sentence that contained a line break continues on the next line."""
    sentences: list[str] = []
    for line in (Path(args.texts) / f"{case_id}.txt").read_text(encoding="utf-8").splitlines():
        head, sep, rest = line.partition("\t")
        if sep and head.isdigit():
            sentences.append(rest)
        elif sentences:
            sentences[-1] += " " + line
    return " ".join(sentences)


cases = {c["case_id"]: c for c in json.loads((Path(args.kit) / "contracts/public-cases.json").read_text())["cases"]}
old = {r["case_id"]: int(float(r["rule_trl"])) for r in csv.DictReader(open(HERE / "features.csv"))}
lock = set(json.loads((HERE / "lockbox.json").read_text())["case_ids"])

for name, ids in (("OPEN (70, used for design)", [i for i in old if i not in lock]),
                  ("LOCKBOX (29, sealed until now)", sorted(lock))):
    o_pts = n_pts = 0.0
    changes = []
    for cid in ids:
        truth = cases[cid]["reference_labels"]["estimated_trl"]
        new, reason, _ = decide_trl(cases[cid], report_text(cid))
        o_pts += points(old[cid], truth)
        n_pts += points(new, truth)
        if new != old[cid]:
            verdict = "FIX" if points(new, truth) > points(old[cid], truth) else \
                      "BREAK" if points(new, truth) < points(old[cid], truth) else "same"
            changes.append(f"    {cid}: organizer {truth}, old {old[cid]}, new {new}  {verdict}  ({reason[:70]})")
    print(f"\n{name}: old rule {o_pts / len(ids):.3f}   new rule {n_pts / len(ids):.3f}")
    print("\n".join(changes) if changes else "    (no report changed)")
