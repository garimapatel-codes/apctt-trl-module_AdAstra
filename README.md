# Ad_Astra — TRL assessment module

Reads the PDF reports of a case, decides every checklist criterion with the evidence pages and a
quoted sentence, and gives a TRL from 1 to 9. CPU only; about 30 s per case on 4 cores.

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
     applied to the site → 6; a system deployed during an actual hurricane → 9).
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
No model was trained.

## Documentation
- [Our thought process](docs/our-thought-process/README.md): why we chose each tool, with the tests behind it.
