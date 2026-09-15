"""Voice search readiness audit.

Rates content for voice/assistant responses: assistants read answers aloud, so
they prefer short conversational sentences, simple words, and a direct answer
inside the first paragraph. Reuses the shared Flesch/word/sentence helpers
from ``app.utils.text``; the syllable counter mirrors the one used there for
Flesch scoring so the two metrics never disagree.
"""
from __future__ import annotations

from app.models.aeo import VoiceAuditRequest, VoiceAuditResult, VoiceCheck
from app.models.common import grade_from_score
from app.utils.text import STOPWORDS, flesch_reading_ease, sentence_count, tokenize, word_count

# Thresholds (voice assistants read ~40-50 word answers, ~2 sentences).
_MIN_FLESCH = 60.0
_MAX_AVG_SENTENCE_LENGTH = 20.0
_MAX_SYLLABLE_DENSITY = 1.7

_CONVERSATIONAL_MARKERS: frozenset[str] = frozenset(
    ("you", "your", "yours", "we", "our", "us", "let's")
)

_FIXES: dict[str, str] = {
    "flesch_easy": "Simplify wording: aim for a Flesch reading ease of 60+ so answers read aloud naturally.",
    "short_sentences": "Shorten sentences to 20 words or fewer; assistants truncate long spoken sentences.",
    "low_syllable_density": "Swap multi-syllable jargon for plain words (target under 1.7 syllables per word).",
    "concise_answer": "Move a complete, self-contained answer into the first paragraph within the word limit.",
    "direct_answer": "Restate the target question's key terms in the opening paragraph so assistants match it.",
    "conversational_tone": "Address the reader directly (you/your/we) to match how voice queries are phrased.",
}


def _syllables(word: str) -> int:
    """Vowel-group syllable estimate (mirrors ``app.utils.text`` Flesch internals)."""
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


def _first_paragraph(content: str) -> str:
    for block in content.replace("\r\n", "\n").split("\n\n"):
        if block.strip():
            return block.strip()
    return content.strip()


def voice_audit(req: VoiceAuditRequest) -> VoiceAuditResult:
    """Score ``req.content`` for voice-assistant answer readiness (0-100).

    Weighted checks: readability (Flesch), sentence length, syllable density,
    first-paragraph answer conciseness, direct-answer coverage of the target
    question (when supplied), and conversational phrasing.
    """
    content = req.content or ""
    tokens = tokenize(content)
    wc = len(tokens)
    sc = sentence_count(content)
    flesch = flesch_reading_ease(content)
    avg_sentence_length = round(wc / sc, 2) if sc else 0.0
    syllable_density = round(sum(_syllables(t) for t in tokens) / wc, 2) if wc else 0.0
    first_para = _first_paragraph(content)
    first_para_words = word_count(first_para)

    checks: list[VoiceCheck] = [
        VoiceCheck(
            code="flesch_easy",
            label="Reads easily aloud (Flesch 60+)",
            passed=flesch >= _MIN_FLESCH,
            weight=3,
            message=f"Flesch reading ease is {flesch}.",
        ),
        VoiceCheck(
            code="short_sentences",
            label="Average sentence length is 20 words or fewer",
            passed=0 < avg_sentence_length <= _MAX_AVG_SENTENCE_LENGTH,
            weight=2,
            message=f"Average sentence length is {avg_sentence_length} words.",
        ),
        VoiceCheck(
            code="low_syllable_density",
            label="Plain wording (under 1.7 syllables per word)",
            passed=0 < syllable_density <= _MAX_SYLLABLE_DENSITY,
            weight=1,
            message=f"Syllable density is {syllable_density} per word.",
        ),
        VoiceCheck(
            code="concise_answer",
            label=f"First paragraph answers within {req.answer_word_limit} words",
            passed=0 < first_para_words <= req.answer_word_limit,
            weight=3,
            message=f"First paragraph has {first_para_words} words.",
        ),
    ]

    if req.question:
        question_terms = [t for t in tokenize(req.question) if t not in STOPWORDS]
        para_tokens = set(tokenize(first_para))
        covered = [t for t in question_terms if t in para_tokens]
        checks.append(
            VoiceCheck(
                code="direct_answer",
                label="First paragraph addresses the target question",
                passed=bool(question_terms) and len(covered) >= max(1, len(question_terms) // 2),
                weight=2,
                message=f"Covers {len(covered)}/{len(question_terms)} question terms.",
            )
        )

    token_set = set(tokens)
    conversational = bool(token_set & _CONVERSATIONAL_MARKERS) or "?" in content
    checks.append(
        VoiceCheck(
            code="conversational_tone",
            label="Uses conversational, second-person phrasing",
            passed=conversational,
            weight=1,
            message="Second-person or question phrasing detected." if conversational
            else "No second-person or question phrasing found.",
        )
    )

    total_weight = sum(c.weight for c in checks)
    passed_weight = sum(c.weight for c in checks if c.passed)
    score = round(100 * passed_weight / total_weight) if total_weight else 0
    fixes = [_FIXES[c.code] for c in checks if not c.passed]

    return VoiceAuditResult(
        score=score,
        grade=grade_from_score(score),
        flesch=flesch,
        avg_sentence_length=avg_sentence_length,
        syllable_density=syllable_density,
        first_paragraph_words=first_para_words,
        checks=checks,
        fixes=fixes,
    )
