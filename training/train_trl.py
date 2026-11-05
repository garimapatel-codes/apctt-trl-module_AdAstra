"""train_trl.py - learn the TRL "points sheet" from the clue table, and test it honestly.

Two modes:

  --mode cv     Mock exams on the OPEN reports only (everything except training/lockbox.json):
                5-fold cross-validation, repeated 20 times with different shuffles. Every report is
                predicted by a model that never saw it. Prints the TRL score (official part-A points)
                of: always 6, our hand-written rule, and the trained model in a few settings.

  --mode final  1. trains the chosen setting on the open reports and opens the lockbox ONCE:
                   prints the score on the 29 locked reports (the honest number);
                2. trains the same setting on all 99 reports and writes the points sheet to
                   --model-out (a small JSON file for assets/).

The trained model: standardise each clue (subtract its average, divide by its spread), then a
multinomial logistic regression (one points sheet per TRL level, softmax into percentages).
Decision: the TRL with the highest EXPECTED points under the official scoring
(exact 1, off by one 0.5, otherwise 0), not simply the most likely TRL. When the model is torn
between 5 and 6, this can answer the safer level automatically.

Usage:
    python training/train_trl.py --features training/features.csv --mode cv
    python training/train_trl.py --features training/features.csv --mode final --C 0.3 \
        --model-out ../my_submission/assets/trl_model.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold

HERE = Path(__file__).resolve().parent
TRLS = np.arange(1, 10)


def points(pred: int, truth: int) -> float:
    """Official part-A points when a TRL is determinable."""
    d = abs(pred - truth)
    return 1.0 if d == 0 else 0.5 if d == 1 else 0.0


# points table: POINTS[p-1, t-1] = points for predicting p when the truth is t
POINTS = np.array([[points(p, t) for t in TRLS] for p in TRLS])


def load(path: str, feature_names: list[str] | None):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    names = feature_names or [k for k in rows[0] if k not in ("case_id", "organizer_trl", "pages")]
    X = np.array([[float(r[n]) for n in names] for r in rows])
    y = np.array([int(r["organizer_trl"]) for r in rows])
    ids = [r["case_id"] for r in rows]
    return ids, X, y, names


class TRLModel:
    """Standardise -> multinomial logistic regression -> expected-points decision."""

    def __init__(self, C: float = 0.3, decision: str = "expected", class_weight=None):
        self.C, self.decision, self.class_weight = C, decision, class_weight

    def fit(self, X, y):
        self.mean = X.mean(axis=0)
        self.std = X.std(axis=0)
        self.std[self.std == 0] = 1.0
        self.lr = LogisticRegression(C=self.C, max_iter=5000, class_weight=self.class_weight)
        self.lr.fit((X - self.mean) / self.std, y)
        return self

    def proba_all_trls(self, X):
        """Probabilities over TRL 1..9 (levels never seen in training get 0)."""
        p = self.lr.predict_proba((X - self.mean) / self.std)
        full = np.zeros((len(X), 9))
        for j, c in enumerate(self.lr.classes_):
            full[:, int(c) - 1] = p[:, j]
        return full

    def predict(self, X):
        p = self.proba_all_trls(X)
        if self.decision == "argmax":
            return TRLS[p.argmax(axis=1)]
        expected = p @ POINTS.T                    # expected points of answering each TRL
        return TRLS[expected.argmax(axis=1)]

    def to_json(self, names, note: str) -> dict:
        return {
            "format": "apctt-adastra-trl-logreg-v1",
            "note": note,
            "feature_names": list(names),
            "mean": self.mean.round(6).tolist(),
            "std": self.std.round(6).tolist(),
            "classes": [int(c) for c in self.lr.classes_],
            "coef": self.lr.coef_.round(6).tolist(),
            "intercept": self.lr.intercept_.round(6).tolist(),
            "decision": self.decision,
            "C": self.C,
        }


def score(pred, y) -> float:
    return float(np.mean([points(int(p), int(t)) for p, t in zip(pred, y)]))


def cross_validate(make, X, y, repeats=20, folds=5):
    """Mean part-A points over repeated k-fold; each report predicted by a model that never saw it."""
    totals = []
    for r in range(repeats):
        pred = np.zeros_like(y)
        for train, test in KFold(folds, shuffle=True, random_state=r).split(X):
            pred[test] = make().fit(X[train], y[train]).predict(X[test])
        totals.append(score(pred, y))
    return float(np.mean(totals)), float(np.std(totals))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default=str(HERE / "features.csv"))
    ap.add_argument("--lockbox", default=str(HERE / "lockbox.json"))
    ap.add_argument("--mode", choices=["cv", "final"], default="cv")
    ap.add_argument("--C", type=float, default=0.3)
    ap.add_argument("--decision", choices=["expected", "argmax"], default="expected")
    ap.add_argument("--model-out", default=None)
    ap.add_argument("--drop", nargs="*", default=[], help="clue columns to leave out")
    args = ap.parse_args()

    ids, X, y, names = load(args.features, None)
    keep = [i for i, n in enumerate(names) if n not in set(args.drop)]
    X, names = X[:, keep], [names[i] for i in keep]
    lock = set(json.load(open(args.lockbox))["case_ids"])
    is_open = np.array([i not in lock for i in ids])
    rule_col = names.index("rule_trl")

    if args.mode == "cv":
        Xo, yo = X[is_open], y[is_open]
        print(f"open reports: {len(yo)}  (lockbox {int((~is_open).sum())} kept sealed)")
        print(f"  always 6            : {score(np.full_like(yo, 6), yo):.3f}")
        print(f"  hand-written rule   : {score(Xo[:, rule_col].astype(int), yo):.3f}  (written while reading these reports: optimistic)")
        for C in (0.03, 0.1, 0.3, 1.0):
            for decision in ("expected", "argmax"):
                m, s = cross_validate(lambda: TRLModel(C, decision), Xo, yo)
                print(f"  model C={C:<4} {decision:8s}: {m:.3f} ± {s:.3f}")
        return

    # final
    model = TRLModel(args.C, args.decision).fit(X[is_open], y[is_open])
    locked_pred = model.predict(X[~is_open])
    yl = y[~is_open]
    print("LOCKBOX (opened once):")
    print(f"  always 6          : {score(np.full_like(yl, 6), yl):.3f}")
    print(f"  hand-written rule : {score(X[~is_open][:, rule_col].astype(int), yl):.3f}")
    print(f"  trained model     : {score(locked_pred, yl):.3f}")
    for cid, p, t, r in zip([i for i in ids if i in lock], locked_pred, yl, X[~is_open][:, rule_col]):
        if p != t or int(r) != t:
            print(f"    {cid}: organizer {t}, rule {int(r)}, model {p}")
    if args.model_out:
        full = TRLModel(args.C, args.decision).fit(X, y)
        note = (f"Trained by team Ad_Astra on the 99 APCTT public sample cases (organizer's estimated TRL), "
                f"clues from participant_module/trl_features.py; C={args.C}, decision={args.decision}.")
        Path(args.model_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.model_out).write_text(json.dumps(full.to_json(names, note), indent=1), encoding="utf-8")
        print(f"wrote {args.model_out}; on all 99 (seen in training): {score(full.predict(X), y):.3f}")


if __name__ == "__main__":
    sys.exit(main())
