"""Pragmatic quality gates for generated meeting-note content."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .local_llm.transcript_cleaning import (
    clean_transcript_text,
    evidence_supports_output,
    is_useful_transcript_text,
)


LOW_CONFIDENCE_SUMMARY_MESSAGE = (
    "Summary confidence is low for this section. Review the transcript before relying on generated notes."
)

_COMMON_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "we",
    "will",
    "with",
}

_ASR_ARTIFACTS = {
    "background",
    "crosstalk",
    "inaudible",
    "noise",
    "silence",
    "static",
}


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    status: str
    reasons: tuple[str, ...] = ()

    @property
    def is_acceptable(self) -> bool:
        return self.status == "ok"


def assess_summary_text(content: object, evidence: object | None = None) -> QualityAssessment:
    """Catch obvious bad summary output without trying to solve semantic evaluation."""

    text = clean_transcript_text(content)
    reasons = _basic_text_reasons(text, min_words=8)
    words = _words(text)
    if len(words) >= 12 and _unique_word_ratio(words) < 0.42:
        reasons.append("repetitive wording")
    if _repeated_ngram_ratio(words, size=3) > 0.3 and _unique_word_ratio(words) < 0.35:
        reasons.append("repeated phrases")
    if _artifact_ratio(words) > 0.12:
        reasons.append("transcript artifacts")
    if _sentence_fragment_ratio(text) > 0.55:
        reasons.append("fragmented wording")
    if _contains_obvious_word_salad(text):
        reasons.append("low-coherence wording")

    evidence_text = clean_transcript_text(evidence)
    if evidence_text and is_useful_transcript_text(evidence_text) and not _summary_has_minimum_grounding(text, evidence_text):
        reasons.append("weak transcript support")

    return QualityAssessment("low_confidence", tuple(dict.fromkeys(reasons))) if reasons else QualityAssessment("ok")


def assess_extracted_item(description: object, evidence: object | None = None) -> QualityAssessment:
    text = clean_transcript_text(description)
    reasons = _basic_text_reasons(text, min_words=4)
    words = _words(text)
    if len(words) >= 8 and _unique_word_ratio(words) < 0.45:
        reasons.append("repetitive wording")
    if _repeated_ngram_ratio(words, size=2) > 0.2:
        reasons.append("repeated phrases")
    if _contains_obvious_word_salad(text):
        reasons.append("low-coherence wording")

    evidence_text = clean_transcript_text(evidence)
    if evidence_text and not evidence_supports_output(text, evidence_text):
        reasons.append("weak transcript support")

    return QualityAssessment("low_confidence", tuple(dict.fromkeys(reasons))) if reasons else QualityAssessment("ok")


def _basic_text_reasons(text: str, *, min_words: int) -> list[str]:
    reasons: list[str] = []
    if not text:
        return ["empty output"]
    words = _words(text)
    if len(words) < min_words:
        reasons.append("too little usable content")
    if not is_useful_transcript_text(text):
        reasons.append("not enough useful language")
    alpha_chars = sum(1 for char in text if char.isalpha())
    if text and alpha_chars / max(len(text), 1) < 0.45:
        reasons.append("too many non-language characters")
    return reasons


def _words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", clean_transcript_text(text).lower())


def _meaningful_words(text: str) -> set[str]:
    return {
        word
        for word in _words(text)
        if len(word) > 2 and word not in _COMMON_STOP_WORDS
    }


def _unique_word_ratio(words: list[str]) -> float:
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def _repeated_ngram_ratio(words: list[str], *, size: int) -> float:
    if len(words) < size * 2:
        return 0.0
    ngrams = [tuple(words[index : index + size]) for index in range(len(words) - size + 1)]
    if not ngrams:
        return 0.0
    repeated = len(ngrams) - len(set(ngrams))
    return repeated / len(ngrams)


def _artifact_ratio(words: list[str]) -> float:
    if not words:
        return 0.0
    return sum(1 for word in words if word in _ASR_ARTIFACTS) / len(words)


def _sentence_fragment_ratio(text: str) -> float:
    sentences = [part.strip() for part in re.split(r"[.!?;\n]+", text) if part.strip()]
    if len(sentences) < 3:
        return 0.0
    fragments = 0
    for sentence in sentences:
        words = _words(sentence)
        if len(words) <= 3:
            fragments += 1
    return fragments / len(sentences)


def _summary_has_minimum_grounding(content: str, evidence: str) -> bool:
    content_words = _meaningful_words(content)
    evidence_words = _meaningful_words(evidence)
    if not content_words or not evidence_words:
        return False
    overlap = content_words & evidence_words
    return len(overlap) >= 2 or len(overlap) / max(len(content_words), 1) >= 0.18


def _contains_obvious_word_salad(text: str) -> bool:
    lowered = clean_transcript_text(text).lower()
    suspicious_patterns = (
        r"\bwhat can \w+ only remains?\b",
        r"\bsurface to fault\b",
        r"\bcross procession\b",
        r"\bsource processing is still constrained\b",
        r"\bwork for them\b$",
    )
    return any(re.search(pattern, lowered) for pattern in suspicious_patterns)
