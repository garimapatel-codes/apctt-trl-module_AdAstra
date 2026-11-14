# Ad_Astra — TRL assessment module

**Start here:** [one-page summary with the pipeline diagram](docs/summary.md).

Reads the PDF reports of a case, decides every checklist criterion with the evidence pages and a
quoted sentence, and gives a TRL from 1 to 9. CPU only; about 30–75 s per case on 4 cores (limit 180 s).

## How it works
1. **Read and clean** (`chunker.py`): text of every page with pypdfium2; running headers, page
   numbers, front matter, contents, reference lists and glossaries are removed; each page is cut
   into "cards" of a few sentences.
2. **Find evidence pages** (`retrieval.py`): BM25 word matching with TRL keywords for each
   criterion keeps the 10 best cards; the ms-marco cross-encoder re-reads them with a plain
   question naming the assessed technology; the two orders are merged (reciprocal rank fusion).
3. **Decide** (`judge.py`):
   - TRL from what is assessed (an installed system, a flood-map library delivered online,
     released software, a field survey → 7; a pilot or limited validation → 5; a calibrated model
     applied to the site → 6; a system deployed during an actual hurricane → 9). Each "→ 7"
     shortcut must also show real use in the report, else 6 (version 1.1.0).
   - Criteria: TRL 1–3, test conditions and target evidence are met; TRL 5–9 criteria are met up to
     the decided TRL; laboratory validation and results-versus-requirements are met only when a
     sentence in the report states them.
   - Evidence: the 3 best pages; the quote is a sentence copied from the page, chosen by the
     DeBERTa zero-shot NLI model among evidence-like candidates.
4. **Safety** (`adapter.py`): time guard well inside the 3-minute limit; if anything fails the
   module still returns a valid result.

## How it was built and tested
Tested on 12 public sample reports with hand-labelled evidence pages (9 for development, 3 unseen)
and the organizer's estimated TRLs of all 99 public cases, scored with the official formulas.
No trained model is shipped: a trained TRL model was tested and did not beat the rule
([note 012](docs/our-thought-process/012-trained-trl-model.md)).

## Version 1.1.0 (Submission 2)
Only `judge.py` changed; reading, retrieval and the models are the same as in 1.0.0.
- **"Is it really in use?"** Before answering TRL 7, the rule checks the report for real use:
  flood maps must be linked to official flood forecasts; StreamStats delivery must be described as
  done rather than planned; a survey or assessment tested mainly by re-running past storms
  (hindcasts) is 6, not 7.
- **"Answer the middle when unsure."** New software shown only on example data, with no accuracy
  statistics against real measurements, gets TRL 5: it could honestly be a 4 or a 6, and the
  middle earns half a point either way.
- **C10 negative verdicts.** Following the organizers' clarification of 10 November, a sentence such
  as "the model did not meet the criteria for satisfactory fit" now counts as C10 evidence.
- **Effect:** TRL score on 70 open public reports 0.914 → 0.943 (4 reports fixed, none broken);
  29 sealed reports unchanged at 0.948. Details: [Submission 1 vs Submission 2](docs/submission-1-vs-2.md).

## Documentation
- [Summary](docs/summary.md): what the module does, the pipeline diagram and the results.
- [Design document](docs/design-document.md): the parts and how one case runs, with diagrams.
- [Our thought process](docs/our-thought-process/README.md): why we chose each tool, with the tests behind it.
