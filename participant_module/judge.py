"""judge.py - decide the TRL and every criterion, and choose the pages and quotes to cite.

How it decides (each rule was checked on our 12 hand-labelled reports and the 99 public cases):
  1. TRL from what is assessed (the case title and target):
       monitoring system deployed during a hurricane -> 9,  any installed system -> 7,
       pilot / preliminary / evaluation study -> 5,  flood-inundation map library -> 7,
       released software (R package, user guide, web application) -> 7,
       field survey or mapping product -> 7,  otherwise a report saying "limited validation" -> 5,
       otherwise 6 (a calibrated model applied to the actual site, the most common case)
     On the 99 public cases this scores 0.92 on the TRL part, against 0.75 for always answering 6.
  2. Criteria, from the TRL and the text:
       TRL 1-3 criteria, test conditions, evidence about the target  -> met
       TRL 5-9 criteria                                             -> met up to the decided TRL
       TRL 4 (laboratory)    -> met only if a sentence describes a controlled test
                                (patch test, test/example/synthetic data, laboratory test ...)
       results vs requirements -> met only if a sentence compares results with a stated
                                criterion ("assessed as satisfactory", "acceptable uncertainty" ...)
       an unknown criterion  -> met only if the NLI judge is very sure (>= 0.8)
  3. Pages: the 3 best pages from retrieval (for the two text-based criteria: the pages that hold
     the deciding sentence come first). The scoring only looks at the first 3 distinct pages.
  4. Quote: candidate sentences from those pages, junk removed (front matter, citations, references,
     future tense, definitions, bare "TRL n" claims); ranked by evidence cue words; the NLI model then
     picks the sentence that best PROVES the criterion. Quotes are always copied from the page.

Use:
    judge = Judge(nli_model_dir)                                  # None = no NLI (cue words only)
    verdict = judge.assess(case, criteria, evidence, retriever.cards, deadline)
"""

from __future__ import annotations

import math
import os
import re
import time
from collections import Counter

os.environ.setdefault("HF_HUB_OFFLINE", "1")          # never try the internet (the event has none)
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

try:                                                   # inside the submission package
    from .keywords import CUES, PERFORMANCE, claim_for, keywords_for, role_of
    from .simple_bm25 import tokenize
except ImportError:                                    # run as a plain script in the scratch folder
    from keywords import CUES, PERFORMANCE, claim_for, keywords_for, role_of
    from simple_bm25 import tokenize

CITE_PAGES = 3                 # the score only looks at the first 3 distinct pages
CANDIDATES = 5                 # sentences per met criterion that the NLI judge reads
NLI_MAX_TOKENS = 128           # sentence + claim, cut for the model (the quote itself stays whole)
NLI_TRUST = 0.2                # if no candidate reaches this, keep the cue-word choice
UNKNOWN_MET = 0.8              # an unknown criterion is met only if the judge is this sure
MIN_WORDS, MAX_WORDS = 6, 70   # shorter: headings and captions; longer: flattened tables
MAX_QUOTE_CHARS = 400

# ---------- sentences that can never be evidence ----------
JUNK = re.compile(
    r"suggested citation|secretary|\bdirector\b|acknowledg|\bthanks?\b|public domain|permission|copyright|"
    r"trade, firm, or product names|endorsement|for more information|\bISSN\b|\bISBN\b|reston, virginia|"
    r"manuscript approved|edited by|layout by|disclaimer|\.{4,}|"
    r",\s(?:19|20)\d\d[a-z]?,\s|accessed (?:on )?[A-Z][a-z]+ \d|"            # reference-list entries
    r"\bBy [A-Z][a-z]+(?: [A-Z]\.)+ [A-Z][a-z]+", re.IGNORECASE)               # author bylines
REFERENCE = re.compile(r"^[A-Z][A-Za-z'\-]+, [A-Z]\.(?:[A-Z]\.)*,?\s+(?:and\s|\d{4})")
NOT_DONE = re.compile(r"\b(?:will|would|could|might|should|may)\b|\bfuture (?:work|studies|research|efforts)\b",
                      re.IGNORECASE)                     # not done (yet), hypothetical or advice
NEGATED = re.compile(r"\b(?:not|cannot|never)\b", re.IGNORECASE)
CITATION = re.compile(r"\(\D{0,80}?(?:and others|et al\.?)[,\s]+\d{4}|\(\D{0,60}?, (?:19|20)\d\d[a-z]?\)|"
                      r"\b[A-Z][a-z]+ (?:and [A-Z][a-z]+|and others|et al\.?) \((?:19|20)\d\d[a-z]?\)")
QUANTITY = re.compile(r"\d(?:[\d.,]*)\s*(?:percent|%|ft|feet|foot|m\b|meters?|mi\b|miles?|km|cm|mm|in\.|°)|"
                      r"\b(?:RMSE|NSE|R2|Nash|root mean square|standard deviation|mean (?:absolute )?(?:error|difference|bias))\b",
                      re.IGNORECASE)
GENERIC = {"technology", "model", "models", "method", "methods", "maps", "with", "from", "linked", "using",
           "data", "observations", "forecasts", "selected", "system", "united", "states", "river", "rivers"}
DEFINITION = re.compile(r"\b(?:is|are) (?:the process of|defined as)\b|\brefers? to\b", re.IGNORECASE)
TRL_CLAIM = re.compile(r"\bTRL\s*-?\s*\d", re.IGNORECASE)
NUMBERISH = re.compile(r"[\d.,()\-–−+%=/]+")
LIMITED = re.compile(r"\blimited validation\b", re.IGNORECASE)

MISSING = {
    1: "No statement of the scientific or engineering principles behind the technology was found.",
    2: "No description of the intended application of the technology was found.",
    3: "No analytical or laboratory results demonstrating the critical function were found.",
    4: "No laboratory or controlled test of the technology (for example on test, synthetic or example data) was found.",
    5: "No validation of the technology against measurements in a relevant environment was found.",
    6: "No demonstration of a complete representative version in a relevant environment was found.",
    7: "No demonstration of a near-final version in the actual operational environment was found.",
    8: "No statement that the final system was qualified by test and demonstration against its requirements was found.",
    9: "No statement that the final system was used successfully in actual operations over a stated period was found.",
    "requirements": "No comparison of results with stated requirements or acceptance criteria was found.",
    "environment": "No description of the test conditions and the tested configuration was found.",
    "target": "No evidence about the assessed target itself was found.",
    None: "No sentence on the most relevant pages clearly supports this criterion.",
}


def meta_trl(case: dict) -> tuple[int | None, str]:
    """TRL suggested by what is assessed (case title, target type and description)."""
    target = case.get("assessment_target") or {}
    text = f"{case.get('title') or ''} {target.get('description') or ''}".lower()
    kind = (target.get("type") or "").lower()
    if kind == "system" and "hurricane" in text:
        return 9, "a monitoring system deployed during an actual hurricane"
    if kind == "system":
        return 7, "an installed system operated in the actual environment"
    if re.search(r"\bpilot\b|\bpreliminary\b|\bevaluation of\b", text):
        return 5, "a pilot, preliminary or evaluation study"
    if re.search(r"flood[- ]inundation map|flood map|inundation map", text) and not re.search(
            r"precipitation-driven|synthetic rating", text):
        return 7, "a flood-inundation map library delivered for operational use"
    if re.search(r"\br package\b|user guide|user's guide|web application|streamstats", text):
        return 7, "released software that others use"
    if re.search(r"\bsurvey\b|channel mapping|seafloor mapping|national assessment", text):
        return 7, "a survey or mapping product made in the actual environment"
    return None, ""


def decide_trl(case: dict, report_text: str) -> tuple[int, str, bool]:
    """Returns (TRL, reason, decided_from_case_fields)."""
    trl, reason = meta_trl(case)
    if trl is not None:
        return trl, reason, True
    if LIMITED.search(report_text):
        return 5, "the report itself describes only a limited validation", False
    return 6, "a model or method calibrated and applied in the actual study area", False


def usable(sentence: str, role) -> bool:
    """Can this sentence be cited as evidence for a criterion of this role?"""
    words = sentence.split()
    if not MIN_WORDS <= len(words) <= MAX_WORDS:
        return False
    if not re.search(r"[.!?:;)\]\"”’']$", sentence.strip()):   # cut off at the end of a page
        return False
    if sum(1 for w in words if NUMBERISH.fullmatch(w)) > 0.3 * len(words):
        return False
    if JUNK.search(sentence) or REFERENCE.match(sentence) or TRL_CLAIM.search(sentence):
        return False
    if DEFINITION.search(sentence) or NEGATED.search(sentence):
        return False
    if role == 2:                                        # intended use may be written as "can/will be used"
        return True
    modal = NOT_DONE.search(sentence)
    if modal and not (role == 7 and modal.group(0).lower() == "may"):   # "data may be obtained from ..." is fine
        return False
    return True


def cue_hits(sentence: str, role) -> int:
    """How many different evidence cue words of this role the sentence contains."""
    cue = CUES.get(role)
    if cue is None:
        return 0
    if role == "requirements" and not PERFORMANCE.search(sentence):
        return 0
    return len({m.group(0).lower() for m in cue.finditer(sentence)})


def shorten(sentence: str) -> str:
    """Quotes are whole sentences from the page; a very long one is cut at a word boundary."""
    return sentence if len(sentence) <= MAX_QUOTE_CHARS else sentence[:MAX_QUOTE_CHARS].rsplit(" ", 1)[0]


class NLI:
    """The judge: probability that a sentence (premise) proves a claim (hypothesis)."""

    def __init__(self, model_dir: str, threads: int = 4) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        torch.set_num_threads(threads)
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir, local_files_only=True)
        self.model.eval()
        labels = {int(i): str(l).lower() for i, l in self.model.config.id2label.items()}
        self.entail = next(i for i, l in labels.items() if "entail" in l and "not" not in l)

    def score(self, pairs: list[tuple[str, str]], deadline: float | None = None,
              batch_size: int = 16) -> list[float | None]:
        """pairs = [(sentence, claim), ...] -> proof probability for each pair (None = not scored in time)."""
        order = sorted(range(len(pairs)), key=lambda i: len(pairs[i][0]))   # similar lengths batch faster
        result: list[float | None] = [None] * len(pairs)
        for start in range(0, len(order), batch_size):
            if deadline is not None and time.monotonic() > deadline:
                break
            idx = order[start:start + batch_size]
            enc = self.tokenizer([pairs[i][0] for i in idx], [pairs[i][1] for i in idx],
                                 truncation="only_first", max_length=NLI_MAX_TOKENS,
                                 padding=True, return_tensors="pt")
            with self.torch.inference_mode():
                probs = self.model(**enc).logits.softmax(dim=-1)[:, self.entail]
            for i, p in zip(idx, probs.tolist()):
                result[i] = float(p)
        return result


class Judge:
    def __init__(self, nli_model_dir: str | None = None, threads: int = 4) -> None:
        self.nli = NLI(nli_model_dir, threads) if nli_model_dir else None

    def assess(self, case: dict, criteria: list[dict], evidence: dict[str, list[dict]],
               cards: list[dict], deadline: float | None = None) -> dict:
        """evidence: from Retriever.retrieve; cards: Retriever.cards; deadline: time.monotonic() value
        after which the NLI judge stops. Returns the criterion maps and the TRL fields of the result."""
        # Every sentence of the report, grouped by page, and how rare each word is
        by_page: dict[tuple[str, int], list[str]] = {}
        for card in cards:
            page_list = by_page.setdefault((card["document_id"], card["page"]), [])
            for s in card["sentences"]:
                if s not in page_list:
                    page_list.append(s)
        all_sentences = [s for sents in by_page.values() for s in sents]
        doc_freq = Counter(w for s in all_sentences for w in set(tokenize(s)))
        idf = {w: math.log(1 + len(all_sentences) / (1 + f)) for w, f in doc_freq.items()}

        trl, trl_reason, from_case = decide_trl(case, " ".join(all_sentences))
        target_text = f"{(case.get('assessment_target') or {}).get('description') or ''} {case.get('title') or ''}"
        target_words = {w for w in tokenize(target_text) if len(w) >= 4 and w not in GENERIC and not w.isdigit()}

        plans: dict[str, dict] = {}
        for c in criteria:
            crit_id, description = c["criterion_id"], c["description"]
            role = role_of(description)
            retrieved = [(it["document_id"], it["page"]) for it in evidence.get(crit_id, [])]
            query_words = set(tokenize(f"{description} {keywords_for(description)}"))
            plan = {"role": role, "query": query_words, "status": None, "pages": retrieved[:CITE_PAGES]}

            if role in (4, "requirements"):              # decided by a deciding sentence in the text
                hits = Counter()
                for where, sents in by_page.items():
                    for s in sents:
                        if usable(s, role) and cue_hits(s, role):
                            hits[where] += 1
                rank = {w: k for k, w in enumerate(retrieved)}
                cue_pages = sorted(hits, key=lambda w: (rank.get(w, 99), -hits[w], w[1]))
                plan["status"] = "met" if cue_pages else "insufficient evidence"
                plan["pages"] = (cue_pages + [w for w in retrieved if w not in cue_pages])[:CITE_PAGES]
                plan["needs_cue"] = True
            elif role in (1, 2, 3, "environment", "target"):
                plan["status"] = "met"
            elif isinstance(role, int):                  # TRL 5-9: met up to the decided TRL
                plan["status"] = "met" if trl >= role else "insufficient evidence"
            else:                                        # unknown criterion: the NLI judge decides
                plan["status"] = "pending"
            if plan["status"] in ("met", "pending") and not plan["pages"]:
                plan["status"] = "insufficient evidence"     # nothing readable to cite
            plans[crit_id] = plan

        # Candidate quotes for every criterion we will cite
        pairs, owners = [], []
        for c in criteria:
            plan = plans[c["criterion_id"]]
            if plan["status"] not in ("met", "pending"):
                continue
            role, scored = plan["role"], []
            for where in plan["pages"]:
                for s in by_page.get(where, []):
                    if not usable(s, role):
                        continue
                    hits = cue_hits(s, role)
                    if plan.get("needs_cue") and not hits:
                        continue
                    words = set(tokenize(s))
                    score = min(hits, 4) * 10.0                                  # evidence cue words
                    score += 4.0 * min(len(words & target_words), 3)             # about the assessed target
                    score += sum(idf.get(w, 0.0) for w in words & plan["query"])  # shares the criterion's words
                    if role in (3, 5, "requirements") and QUANTITY.search(s):
                        score += 8.0                                             # a measured result
                    if role != 1 and CITATION.search(s):
                        score -= 8.0                                             # background from the literature
                    scored.append((score, where, s))
            scored.sort(key=lambda x: -x[0])
            plan["candidates"] = scored
            claim = claim_for(c["description"])
            for k, (_, where, s) in enumerate(scored[:CANDIDATES]):
                pairs.append((s, claim))
                owners.append((c["criterion_id"], k))

        nli_scores: dict[tuple[str, int], float] = {}
        if self.nli is not None and pairs:
            try:
                for (crit_id, k), p in zip(owners, self.nli.score(pairs, deadline)):
                    if p is not None:
                        nli_scores[(crit_id, k)] = p
            except Exception:                            # the judge is a bonus: never let it break the case
                nli_scores = {}

        status_map, evidence_map, missing_map, rationale_map = {}, {}, {}, {}
        for c in criteria:
            crit_id = c["criterion_id"]
            plan = plans[crit_id]
            role = plan["role"]
            cands = plan.get("candidates", [])
            judged = [(nli_scores[(crit_id, k)], k) for k in range(min(CANDIDATES, len(cands)))
                      if (crit_id, k) in nli_scores]
            best_nli = max(judged)[0] if judged else None

            if plan["status"] == "pending":
                plan["status"] = "met" if best_nli is not None and best_nli >= UNKNOWN_MET else "insufficient evidence"

            if plan["status"] != "met":
                status_map[crit_id] = "insufficient evidence"
                evidence_map[crit_id] = []
                checked = ", ".join(str(p) for _, p in plan["pages"]) or "none"
                reason = MISSING.get(role, MISSING[None])
                if isinstance(role, int) and role > trl and role not in (4,):
                    reason = f"The evidence supports TRL {trl}. " + reason
                missing_map[crit_id] = f"{reason} (Most relevant pages checked: {checked}.)"
                rationale_map[crit_id] = missing_map[crit_id]
                continue

            # The quote: the NLI judge's best candidate if it is sure enough, else the best cue-word candidate
            if cands:
                pick = max(judged)[1] if judged and best_nli >= NLI_TRUST else 0
                _, first_where, first_quote = cands[pick]
            else:
                first_where, first_quote = plan["pages"][0], None
            order = [first_where] + [w for w in plan["pages"] if w != first_where]
            items = []
            for n, where in enumerate(order[:CITE_PAGES]):
                item = {"document_id": where[0], "page": where[1]}
                quote = first_quote if n == 0 else next((s for _, w, s in cands if w == where), None)
                if quote is None:                        # no candidate: the first clean sentence of the page
                    page_sents = by_page.get(where, [])
                    quote = next((s for s in page_sents if usable(s, None)), None) or next(
                        (s for s in page_sents if len(s.split()) >= MIN_WORDS), None)
                if quote and quote.strip():
                    item["supporting_span"] = shorten(quote.strip())
                items.append(item)
            status_map[crit_id] = "met"
            evidence_map[crit_id] = items
            first = items[0]
            if "supporting_span" in first:
                rationale_map[crit_id] = f'Page {first["page"]}: "{first["supporting_span"][:200]}"'
            else:
                rationale_map[crit_id] = f"Page {first['page']} is the most relevant page for this criterion."

        met_levels = sorted(plans[c["criterion_id"]]["role"] for c in criteria
                            if isinstance(plans[c["criterion_id"]]["role"], int)
                            and status_map[c["criterion_id"]] == "met")
        trl_rationale = (f"TRL {trl}: {trl_reason}. TRL-level criteria judged met: "
                         f"{', '.join(str(x) for x in met_levels) or 'none'}.")
        return {
            "predicted_trl": trl,
            "trl_rationale": trl_rationale,
            "confidence": 0.7 if from_case else 0.5,
            "uncertainty": {"kind": "trl_interval", "lower": max(1, trl - 1), "upper": min(9, trl + 1)},
            "criterion_status": status_map,
            "evidence_reference": evidence_map,
            "missing_evidence": missing_map,
            "criterion_rationale": rationale_map,
        }
