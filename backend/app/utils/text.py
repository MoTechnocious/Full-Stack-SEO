"""Text / lightweight NLP helpers: tokenization, density, readability, term extraction."""
from __future__ import annotations

import re
from collections import Counter

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_SENT_RE = re.compile(r"[.!?]+")

STOPWORDS: frozenset[str] = frozenset(
    """a an and are as at be but by for if in into is it no not of on or such that the
    their then there these they this to was will with we you your our from has have had
    can could should would may might will do does did been being about above after again
    all am any because before below between both during each few more most other some
    than too very who whom what which when where why how i he she his her them us""".split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens (alphanumeric, apostrophes kept)."""
    return [m.group(0).lower() for m in _WORD_RE.finditer(text or "")]


def word_count(text: str) -> int:
    return len(tokenize(text))


def sentence_count(text: str) -> int:
    parts = [p for p in _SENT_RE.split(text or "") if p.strip()]
    return max(1, len(parts))


def _syllables(word: str) -> int:
    word = word.lower()
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def flesch_reading_ease(text: str) -> float:
    """Flesch Reading Ease (0-100+, higher = easier). Clamped to [0, 100]."""
    words = tokenize(text)
    if not words:
        return 0.0
    sentences = sentence_count(text)
    syllables = sum(_syllables(w) for w in words)
    score = 206.835 - 1.015 * (len(words) / sentences) - 84.6 * (syllables / len(words))
    return round(max(0.0, min(100.0, score)), 1)


def ngrams(tokens: list[str], n: int) -> list[str]:
    if n <= 1:
        return list(tokens)
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def phrase_count(text: str, phrase: str) -> int:
    """Count case-insensitive whole-phrase occurrences (word-boundary aware)."""
    phrase = (phrase or "").strip().lower()
    if not phrase:
        return 0
    pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
    return len(pattern.findall(text or ""))


def keyword_density(text: str, phrase: str) -> float:
    total = word_count(text)
    if total == 0:
        return 0.0
    phrase_words = max(1, len(tokenize(phrase)))
    occurrences = phrase_count(text, phrase)
    return round((occurrences * phrase_words) / total * 100, 2)


def extract_terms(text: str, top_k: int = 30, max_n: int = 2) -> list[tuple[str, int]]:
    """Return the most frequent uni-/bi-/tri-grams excluding stopword-only grams."""
    tokens = [t for t in tokenize(text)]
    counter: Counter[str] = Counter()
    for n in range(1, max_n + 1):
        for gram in ngrams(tokens, n):
            parts = gram.split()
            if all(p in STOPWORDS for p in parts):
                continue
            if n == 1 and (parts[0] in STOPWORDS or len(parts[0]) < 3):
                continue
            counter[gram] += 1
    return counter.most_common(top_k)
