"""trl_features.py - measure the "clues" about a report's maturity, as numbers.

Used by the TRL-model experiment in this folder (see docs/our-thought-process/012). The experiment
showed the trained model does not beat the hand-written TRL rule, so this file is NOT part of the
submitted module; it stays here so the experiment can be repeated. If a model is ever shipped, this
file must move into participant_module/ so training and the event measure clues with the same code.

Input: the case (its fields) and the module's cards (cleaned report text: front matter, contents
pages, reference lists and glossaries are already removed by chunker.make_cards, so a word in a
cited paper's title does not count).

Most clues are "how often does this kind of phrase appear, per 10,000 words", so a 300-page report
and a 20-page report are comparable.
"""

from __future__ import annotations

import math
import re

from participant_module.judge import decide_trl        # the module's own TRL rule (module root on sys.path)

_C = re.IGNORECASE

# Each clue: a name and the phrases that count for it.
PHRASES = {
    # tested against real data
    "calibration": re.compile(
        r"\bcalibrat\w*|\bvalidat\w*|\bverif(?:y|ied|ication)\b|compared (?:with|to) (?:the )?(?:observed|measured)"
        r"|observed (?:and|versus|vs\.?) simulated|simulated (?:and|versus|vs\.?) observed|high-water marks?", _C),
    # measured accuracy numbers
    "accuracy": re.compile(
        r"\bRMSE\b|root[- ]mean[- ]square|Nash[- ]Sutcliffe|\bNSE\b|\bR2\b|\bR²|coefficient of determination"
        r"|percent (?:error|bias|difference)|\bPBIAS\b|mean (?:absolute )?error|standard error|\bbias\b", _C),
    # weak results, stated as such (general talk about "uncertainty" is NOT counted: mature
    # flood-map reports have whole uncertainty sections, so it pointed the wrong way in version 1)
    "weak_results": re.compile(
        r"\bvaried (?:markedly|widely|considerably|greatly|substantially)\b"
        r"|\bpoor(?:ly)? (?:fit|agreement|performance|match|correlation|calibrat\w*|simulat\w*|represent\w*)"
        r"|\bdid not (?:match|agree|capture|reproduce|simulate)\b|\bless accurate\b"
        r"|\bweak(?:er|ly)? (?:fit|agreement|correlation)\b|\bunderestimat\w*|\boverestimat\w*", _C),
    # parts of the validation that could not be done
    "validation_gaps": re.compile(
        r"\b(?:could|can) not be (?:calibrated|verified|validated|evaluated)\b"
        r"|\b(?:was|were) not (?:verified|validated)\b|\bcalibrated,? but not (?:verified|validated)\b", _C),
    # built on data that already existed rather than new tests
    "existing_data": re.compile(
        r"\b(?:existing|available|previously collected|historical) (?:data|information|records)\b", _C),
    # results judged against a stated criterion
    "criteria_met": re.compile(
        r"\bsatisfactor\w*|\bacceptab\w*|\bwithin (?:the )?(?:acceptable|allowable|target|required|specified)"
        r"|\b(?:met|meet|meets|exceeded) (?:the )?(?:\w+ ){0,2}(?:criteria|requirements?|standards?|targets?|goals?)\b", _C),
    # in operational use
    "operational": re.compile(
        r"\bwebsite\b|\bweb site\b|\bweb[- ]based\b|\bonline\b|\breal[- ]time\b|\bforecast\w*|National Weather Service|\bNWS\b"
        r"|\bAHPS\b|\boperational\w*|\bend users?\b|\bdecision[- ]makers?\b|\bdeployed\b|\bwarning system", _C),
    # early stage
    "early_stage": re.compile(
        r"\bpilot\b|\bpreliminary\b|\bfeasibility\b|\bproof[- ]of[- ]concept\b|\bprototype\b|\bexploratory\b|\bfirst step\b", _C),
    # software, shown on example or test data
    "software_examples": re.compile(
        r"\bsource code\b|\binstallation\b|\binstall\w*|\bexample (?:data|data ?sets?|files?|applications?|problems?)"
        r"|\btest (?:data ?sets?|problems?|cases?)\b|\bsample (?:data|input) files?\b|\bexecutable\b|\bsoftware\b", _C),
    # laboratory or controlled tests
    "laboratory": re.compile(
        r"\blaborator\w*|\bflume\b|\bbench[- ]?(?:scale|top|test)\w*|\bcontrolled (?:conditions|experiments?|settings?|tests?)"
        r"|\bsynthetic (?:data|tests?|cases?)\b", _C),
    # not finished yet
    "future_work": re.compile(
        r"\bfuture (?:work|studies|research|versions?)\b|\bfurther (?:testing|work|study|research|validation|development)\b"
        r"|\bis (?:being|currently being) developed\b|\bwill be (?:developed|tested|added|extended|improved)\b", _C),
}

TARGET_TYPES = ("system",)            # subsystem / component never occur in the public cases; technology = not system

# Clue set version 2 (5 Nov 2026), designed on the 70 open public reports only (training/lockbox.json).
CLUE_VERSION = 2

# The column order of the clue table (and of the model's points sheet). Never reorder without retraining.
FEATURE_NAMES = (
    ["rule_trl", "rule_from_case_fields"]
    + [f"type_{t}" for t in TARGET_TYPES]
    + [f"per10k_{name}" for name in PHRASES]
    + ["log_pages"]
)


def report_sentences(cards: list[dict]) -> list[str]:
    """Every sentence of the cleaned report once (neighbouring cards share one sentence)."""
    seen: dict[tuple[str, int], list[str]] = {}
    for card in cards:
        page_list = seen.setdefault((card["document_id"], card["page"]), [])
        for sentence in card["sentences"]:
            if sentence not in page_list:
                page_list.append(sentence)
    return [s for sentences in seen.values() for s in sentences]


def report_features(case: dict, cards: list[dict]) -> dict[str, float]:
    """The clues of one case, in FEATURE_NAMES order (as a name -> number mapping)."""
    sentences = report_sentences(cards)
    text = " ".join(sentences)
    words = max(1, len(text.split()))

    rule_trl, _reason, from_case = decide_trl(case, text)
    target_type = ((case.get("assessment_target") or {}).get("type") or "").lower()
    pages = sum(int(d.get("page_count") or 0) for d in case.get("documents") or [])

    clues: dict[str, float] = {
        "rule_trl": float(rule_trl),
        "rule_from_case_fields": 1.0 if from_case else 0.0,
    }
    for t in TARGET_TYPES:
        clues[f"type_{t}"] = 1.0 if target_type == t else 0.0
    for name, pattern in PHRASES.items():
        clues[f"per10k_{name}"] = round(10000.0 * len(pattern.findall(text)) / words, 3)
    clues["log_pages"] = round(math.log(1 + pages), 4)
    return {name: clues[name] for name in FEATURE_NAMES}
