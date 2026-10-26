"""chunker.py - cut report pages into small "cards" for searching.

Input:  a list of page texts (index 0 = PDF page 1), as the PDF reader gives them.
Output: a list of cards. Each card is a few sentences from ONE page, plus its page number,
        so whatever we find later can be cited as (document, page) and quoted exactly.
"""

from __future__ import annotations

import re
from collections import Counter

MAX_WORDS = 180          # a card holds at most about 180 words (fits the models' 512-token limit)
MIN_PAGE_CHARS = 50      # a page with less text than this is treated as empty (figure or scan)
HEADER_MIN_PAGES = 3     # a top/bottom line seen on this many pages is a running header or footer

# Abbreviations whose full stop does NOT end a sentence. USGS reports use "U.S.", "Mo.", "St." a lot.
ABBREVIATIONS = [
    "U.S.", "et al.", "e.g.", "i.e.", "Fig.", "Figs.", "fig.", "figs.", "No.", "no.", "Nos.",
    "Eq.", "eq.", "vs.", "approx.", "Dr.", "Mr.", "Ms.", "St.", "Mt.", "Co.", "Inc.", "Jr.",
    "Mo.", "Ill.", "Ind.", "Wis.", "Mich.", "Minn.", "Calif.", "Colo.", "Ariz.", "Ark.", "Ala.",
    "Fla.", "Ga.", "Ky.", "Kans.", "La.", "Md.", "Mass.", "Miss.", "Mont.", "Nebr.", "Nev.",
    "Okla.", "Oreg.", "Pa.", "Tenn.", "Tex.", "Va.", "Vt.", "Wash.", "Wyo.", "Conn.", "Del.",
]
DOT = "\x00"             # a stand-in for "a full stop that does not end a sentence"


# ---------- 1. Clean the pages ----------

def _line_key(line: str) -> str:
    """The same running header with a different page number should look identical: drop digits."""
    return re.sub(r"\d+", "#", line.strip().lower())


def find_repeated_lines(pages: list[str]) -> set[str]:
    """Running headers/footers: short lines at the top or bottom of a page that repeat on many pages."""
    counts: Counter[str] = Counter()
    for text in pages:
        lines = [l for l in text.splitlines() if l.strip()]
        edge = lines[:2] + lines[-2:]                      # first 2 and last 2 lines of the page
        counts.update({_line_key(l) for l in edge if len(l.strip()) < 100})
    return {key for key, n in counts.items() if n >= HEADER_MIN_PAGES}


def clean_page(text: str, repeated: set[str]) -> str:
    """Remove headers/footers and lone page numbers, then rejoin the page into one flowing text."""
    text = text.replace("\ufffe", "")                     # pdfium marks a word hyphenated at line end
    lines = [l.strip() for l in text.splitlines()]
    kept = []
    for i, line in enumerate(lines):
        at_edge = i < 2 or i >= len(lines) - 2
        if not line or re.fullmatch(r"\d{1,4}", line):     # empty line or a bare page number
            continue
        if at_edge and _line_key(line) in repeated:        # running header or footer
            continue
        kept.append(line)
    joined = " ".join(kept)
    return re.sub(r"\s+", " ", joined).strip()             # one space everywhere (also odd unicode spaces)


def page_kind(raw: str, clean: str) -> str:
    """Label a page so we can skip pages that cannot hold evidence about the technology itself."""
    if len(clean) < MIN_PAGE_CHARS:
        return "empty"
    head = raw[:300].lower()
    dot_leaders = len(re.findall(r"\.{4,}", raw))         # "Introduction ........ 3"
    if "contents" in head and dot_leaders >= 3:
        return "contents"
    # Reference lists: many lines that start like "Smith, J.A., 2015," or "Smith, J., and Lee, K."
    ref_lines = len(re.findall(r"(?m)^\s*[A-Z][A-Za-z'\-]+, [A-Z]\.", raw))
    if ref_lines >= 5:
        return "references"
    return "normal"


# ---------- 2. Split into sentences ----------

def split_sentences(text: str) -> list[str]:
    """Split at '. ', '? ' or '! ' followed by a capital letter, but not after an abbreviation."""
    protected = text
    for abbr in ABBREVIATIONS:
        protected = protected.replace(abbr, abbr.replace(".", DOT))
    protected = re.sub(r"\b([A-Z])\.", r"\1" + DOT, protected)   # initials: "Benjamin J. Dietsch"
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", protected)
    return [p.replace(DOT, ".").strip() for p in parts if p.strip()]


def _cap_long(sentences: list[str]) -> list[str]:
    """A 'sentence' longer than a card (usually a flattened table) is cut into card-sized pieces."""
    out = []
    for s in sentences:
        words = s.split()
        for start in range(0, len(words), MAX_WORDS):
            out.append(" ".join(words[start:start + MAX_WORDS]))
    return out


# ---------- 3. Group sentences into cards ----------

def make_cards(pages: list[str], document_id: str = "D001") -> tuple[list[dict], dict[int, str]]:
    """Return (cards, page_kinds). Cards never cross a page boundary, so the page number is exact.
    Neighbouring cards share one sentence, so a statement split across two cards is still whole in one."""
    repeated = find_repeated_lines(pages)
    cards: list[dict] = []
    kinds: dict[int, str] = {}
    for index, raw in enumerate(pages):
        page_no = index + 1
        clean = clean_page(raw, repeated)
        kinds[page_no] = page_kind(raw, clean)
        if kinds[page_no] != "normal":
            continue
        sents = _cap_long(split_sentences(clean))
        i = 0
        while i < len(sents):
            j, words = i, 0
            while j < len(sents) and (j == i or words + len(sents[j].split()) <= MAX_WORDS):
                words += len(sents[j].split())
                j += 1
            cards.append({
                "document_id": document_id,
                "page": page_no,
                "sentences": sents[i:j],
                "text": " ".join(sents[i:j]),
            })
            if j >= len(sents):
                break
            i = j - 1 if j - i > 1 else j        # overlap: start the next card on the last sentence
    return cards, kinds
