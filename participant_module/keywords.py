"""keywords.py - all the wording the module uses, in one place.

Each checklist criterion is recognised by its ROLE: its TRL level (1-9) or one of the three evidence
criteria ("requirements", "environment", "target"). The role comes from the title at the start of the
description ("Laboratory validation (TRL 4): ...") or from the "(TRL n)" tag, never from the criterion
ID, so the module still works if the hidden checklist numbers its criteria differently.

For every role there are:
  KEYWORDS   everyday words a report uses for it (added to the BM25 search question)
  QUESTIONS  a plain question for the careful reader (ms-marco); {target} = the case's technology
  CLAIMS     a plain statement for the judge (NLI): "does this sentence PROVE this?"
  CUES       word patterns that mark a sentence as likely evidence (used to pick the quote)
"""

from __future__ import annotations

import re

TITLE_ROLES = {
    "basic principles": 1,
    "concept formulated": 2,
    "proof of concept": 3,
    "laboratory validation": 4,
    "relevant-environment validation": 5,
    "prototype in relevant environment": 6,
    "prototype in operational environment": 7,
    "system qualified": 8,
    "proven in operation": 9,
    "quantified results against requirements": "requirements",
    "environment and test article defined": "environment",
    "evidence matches the assessment target": "target",
}


def title_of(description: str) -> str:
    """'Laboratory validation (TRL 4): the report states ...' -> 'laboratory validation'."""
    return description.split("(")[0].split(":")[0].strip().lower()


def role_of(description: str):
    """The role of a criterion: 1-9, 'requirements', 'environment', 'target', or None if unknown."""
    title = title_of(description)
    if title in TITLE_ROLES:
        return TITLE_ROLES[title]
    tag = re.search(r"\(TRL\s*(\d)\)", description)
    if tag:
        return int(tag.group(1))
    text = description.lower()
    if "requirement" in text or "acceptance criteri" in text:
        return "requirements"
    if "test condition" in text or "test article" in text:
        return "environment"
    if "assessment target" in text or "assessed target" in text:
        return "target"
    return None


KEYWORDS = {
    1: "principle principles theory theoretical physical law equation equations governing empirical relation mechanism process processes based on previous studies literature known observed",
    2: "purpose objective application intended designed to approach method methods framework concept developed to provide used to estimate tool",
    3: "results demonstrated demonstrate analysis analytical simulation simulated model results accuracy performance feasibility showed indicate",
    4: "laboratory lab bench benchtop breadboard controlled conditions test tested testing example dataset quality control instrument check",
    5: "calibrated calibration validated validation observed measured measurements field data comparison compared simulated versus observed error accuracy representative conditions",
    6: "prototype pilot demonstration demonstrated application applied model application implemented full scale system case study generated produced",
    7: "operational operation field deployed real-time in use delivered available online website users forecast public operated active network",
    8: "qualified qualification certified certification acceptance test requirements met approved standard standards compliance",
    9: "in service routine use years of operation operational use long-term used since adopted production continuous operation",
    "requirements": "criteria requirement requirements acceptance target threshold satisfactory met exceeded within compared goodness of fit statistics",
    "environment": "test conditions period configuration setup conditions during version equipment study area data collection site",
    "target": "this study this report the model developed the method study area target",
}

QUESTIONS = {
    1: "What scientific principles, physical laws, equations or earlier studies is {target} based on?",
    2: "What is the purpose of {target}, and how is it intended to be used?",
    3: "What results show that {target} works, such as simulation results, analysis or accuracy statistics?",
    4: "Was {target} tested under controlled conditions, for example with example data, benchmark tests or instrument quality-control checks?",
    5: "Was {target} calibrated or validated against measurements collected at the study site, and how accurate was it?",
    6: "Was the complete {target} applied to the actual study area to produce its final results?",
    7: "Is {target} used in real operations, for example published online, linked to real-time gages or forecasts, or carried out by field crews?",
    8: "Was {target} certified, qualified or approved against a standard or acceptance requirements?",
    9: "Has {target} been in routine operational use for a long period?",
    "requirements": "Did the results of {target} meet stated criteria or requirements, such as satisfactory performance statistics?",
    "environment": "Under what conditions, time period, site and equipment was {target} tested or calibrated?",
    "target": "Which study area and data does this report use for {target}?",
}

CLAIMS = {
    1: "The method is based on established scientific principles, physical equations or published studies.",
    2: "The text states the purpose of the product and how it is intended to be used.",
    3: "The results show that the method or model works, for example with accuracy statistics or comparisons.",
    4: "The method, software or instrument was tested under controlled conditions, for example with test data or quality-control checks.",
    5: "The model or method was calibrated or validated against observed field measurements.",
    6: "The complete method was applied to the actual study area to produce the final maps, models or data products.",
    7: "The product is used in real operations, for example published online or linked to real-time data or forecasts.",
    8: "The final system was certified, qualified or approved against its requirements.",
    9: "The system has been used successfully in routine operations for years.",
    "requirements": "The results were compared with stated criteria or requirements and judged acceptable or satisfactory.",
    "environment": "The text describes the test conditions, time period, site or equipment that were used.",
    "target": "The text describes the specific study area and product that this report developed.",
}

_C = re.IGNORECASE
CUES = {
    1: re.compile(r"principle|equation|\blaws?\b|theor|based on|govern|physically|empirical|mechanism|relation|derived|algorithm|one-dimensional|two-dimensional|step-backwater", _C),
    2: re.compile(r"purpose|objective|intended|designed to|this report (?:describes|documents|presents)|to provide|can be used|used to (?:estimate|determine|assess|predict|evaluate)|application|developed (?:to|for)", _C),
    3: re.compile(r"result|showed|\bshows?\b|demonstrat|indicat|accura|RMSE|root mean|\bNSE\b|Nash|error|percent|agree|compar|within|statistic|success rate", _C),
    4: re.compile(r"laboratory (?:test|experiment|setting|condition|environment)|\bflume\b|bench[- ]?(?:scale|top|test)|controlled (?:conditions|experiment|setting|test)|synthetic data|simulated data|test data ?sets?|example data ?sets?|quality[- ]control check|patch test|performance test|benchmark (?:test|problem|data)", _C),
    5: re.compile(r"calibrat|validat|compar|observed|measured|measurements|high-water|RMSE|root mean|\bNSE\b|Nash|error|agree|difference|verif", _C),
    6: re.compile(r"(?:maps?|grids?|profiles?|models?|DEMs?|datasets?|offsets?|librar(?:y|ies)|estimates?|boundaries) (?:were|was) (?:created|produced|developed|prepared|generated|computed|applied|used|delineated)|(?:was|were) used to (?:compute|generate|produce|simulate|estimate|create|develop|delineate|map)|applied to (?:the|each|all)|final (?:maps?|grids?|model|DEM|products?)|application of the (?:calibrated )?(?:model|method)", _C),
    7: re.compile(r"website|web site|web-based|web mapping|online (?:map|mapping|application|tool)|available (?:online|on the internet|through|from the|at http)|internet|real[- ]time|National Weather Service|\bNWS\b|AHPS|forecast|warning system|early warning|operational|StreamStats|decision[- ]support|\bCRAN\b|data release|field crews|deployed", _C),
    8: re.compile(r"certif|qualif|approv|accredit|accepted by|compliance|released", _C),
    9: re.compile(r"years of operation|in operation since|routine|operational use|deployed during|continuous(?:ly)? (?:operated|recorded)|mission|used successfully", _C),
    "requirements": re.compile(
        r"satisfactor|acceptab|encapsulat|evaluation criteri|acceptance criteri|performance criteri|"
        r"\b(?:met|meet|meets|exceeded|exceeds|did not meet|failed to meet)\s+(?:the\s+)?(?:\w+\s+){0,2}(?:criteria|requirements?|standards?|targets?|goals?)\b|"
        r"within (?:the )?(?:acceptable|allowable|target|required|specified)", _C),
    "environment": re.compile(r"condition|period|during|from \d{4}|\bsites?\b|equipment|configuration|events?\b|flood of|study area|reach|instrument|receivers?|sensors?|deployed|surveyed", _C),
    "target": re.compile(r"this report (?:describes|documents|presents)|purposes? of this (?:report|study)|objectives? of this|the purpose|this study (?:was|is|used|developed|combines)|in this study|study area|(?:was|were) developed", _C),
}

# A requirements sentence must also be about results (not, say, about the input data).
PERFORMANCE = re.compile(r"model|simulat|calibrat|performance|result|uncertaint|difference|error", _C)


def keywords_for(description: str) -> str:
    """Everyday words for a criterion; empty for an unknown criterion (the sentence alone is searched)."""
    return KEYWORDS.get(role_of(description), "")


def question_for(description: str, target: str = "the technology") -> str:
    """The plain question for the careful reader, naming the case's technology."""
    question = QUESTIONS.get(role_of(description))
    return question.format(target=target) if question else description


def claim_for(description: str) -> str:
    """The plain claim the judge checks; falls back to the checklist sentence itself."""
    return CLAIMS.get(role_of(description), description)
