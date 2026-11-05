# Training: the TRL-model experiment

These files are **not** part of the submission. `tools/make_submission.py` packs only
`participant_module/`, `assets/`, `submission.json`, `declaration.json` and `README.md`.
They record an experiment: can a model trained on the 99 public sample cases predict the TRL better
than our hand-written rule? The answer was no. The full story is in
[`docs/our-thought-process/012-trained-trl-model.md`](../docs/our-thought-process/012-trained-trl-model.md).

| File | What it is |
|---|---|
| `trl_features.py` | Measures the "clues" of a report as numbers (clue set version 2). |
| `build_features.py` | Reads the 99 public PDFs with the module's own reader and card cutter and writes one row of clues per report to a CSV. |
| `dump_texts.py` | Saves the cleaned text of every report (one sentence per line) to design clues quickly. |
| `train_trl.py` | Mock exams (repeated 5-fold cross-validation) on the open reports; `--mode final` opens the lockbox once and writes a model file. |
| `lockbox.json` | 29 reports chosen at random before any clue design, kept sealed for one final honest test. **Still sealed.** |
| `features.csv` | The clue table (clue set version 1) for all 99 reports, as built on our laptop. |

The PDFs and the saved texts are not stored here (download them with the kit's
`tools/get_public_cases.py --download --all --dir <folder>`).

```bash
# from the repository root, with the base environment's Python
~/work/apctt-env/base/bin/python training/build_features.py --kit ~/work/apctt-participant-kit-0.5.0-cpu --pdfs ~/work/public_cases/pdf --out training/features.csv
~/work/apctt-env/base/bin/python training/train_trl.py --features training/features.csv --mode cv --drop type_subsystem type_component type_technology
```
