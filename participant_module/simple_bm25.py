"""simple_bm25.py - the word-matcher (BM25).

Scores how well each text matches a question by shared words:
rare words count more, repeats count less and less, and long texts get a small penalty.
"""

from __future__ import annotations

import math
import re
from collections import Counter

# Endings we trim so that "tested", "testing" and "tests" all become "test".
SUFFIXES = ("ations", "ation", "ings", "ing", "ed", "es", "s")


def stem(word: str) -> str:
    """Trim one common ending, but keep at least 4 letters ("uses" stays "uses")."""
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    """Lower-case, keep only letters and digits, and trim each word to its root."""
    return [stem(w) for w in re.findall(r"[a-z0-9]+", text.lower())]


class BM25:
    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        # k1: how fast repeats stop helping.  b: how strongly long texts are penalised.
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(t)) for t in texts]          # word counts of each text
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / max(1, len(self.lengths))
        doc_freq: Counter[str] = Counter()                          # in how many texts each word appears
        for d in self.docs:
            doc_freq.update(d.keys())
        n = len(self.docs)
        # IDF: a word found in few texts is worth a lot; one found everywhere is worth little.
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in doc_freq.items()}

    def scores(self, query: str) -> list[float]:
        """One score per text, in the same order as the texts given to BM25()."""
        words = tokenize(query)
        out = []
        for d, length in zip(self.docs, self.lengths):
            s = 0.0
            for w in words:
                f = d.get(w, 0)                                     # how often this word is in the text
                if f:
                    s += self.idf[w] * f * (self.k1 + 1) / (
                        f + self.k1 * (1 - self.b + self.b * length / self.avg_len))
            out.append(s)
        return out
