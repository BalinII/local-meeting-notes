"""Transcript cleaning helpers for local LLM prompting and output validation."""

from __future__ import annotations

import re
from dataclasses import dataclass


FILLER_WORDS = {
    "ah",
    "erm",
    "hmm",
    "like",
    "okay",
    "right",
    "uh",
    "um",
    "yeah",
}

NOISE_PHRASES = {
    "background noise",
    "inaudible",
    "music",
    "noise",
    "silence",
    "static",
}

OUTCOME_KEYWORDS = {
    "action",
    "agreed",
    "blocker",
    "decide",
    "decision",
    "follow",
    "next step",
    "open question",
    "please",
    "question",
    "risk",
    "todo",
    "we will",
}


@dataclass(slots=True)
class CleanTranscriptSegment:
    speaker_label: str
    content: str
    start_offset_seconds: int
    end_offset_seconds: int


def clean_transcript_text(value: object) -> str:
    """Normalize common ASR artifacts without trying to infer missing meaning."""

    text = str(value or "")
    text = re.sub(r"\[[^\]]*(?:inaudible|music|noise|silence|crosstalk)[^\]]*\]", " ", text, flags=re.I)
    text = re.sub(r"\([^)]*(?:inaudible|music|noise|silence|crosstalk)[^)]*\)", " ", text, flags=re.I)
    text = re.sub(r"\b(?:uh|um|erm|hmm|ah)\b[,\s]*", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" -:\t\r\n")
    text = _collapse_repeated_words(text)
    text = _collapse_repeated_phrases(text)
    return text.strip()


def clean_transcript_segments(
    transcript_segments: list[dict[str, object]],
) -> list[CleanTranscriptSegment]:
    cleaned: list[CleanTranscriptSegment] = []
    seen: set[tuple[str, str]] = set()
    for segment in transcript_segments:
        content = clean_transcript_text(segment.get("content"))
        if not is_useful_transcript_text(content):
            continue
        speaker = clean_transcript_text(segment.get("speaker_label")) or "Unknown"
        start = _normalize_int(segment.get("start_offset_seconds"))
        end = _normalize_int(segment.get("end_offset_seconds"), default=start)
        dedupe_key = (speaker, content.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        cleaned.append(
            CleanTranscriptSegment(
                speaker_label=speaker,
                content=content,
                start_offset_seconds=start,
                end_offset_seconds=end,
            )
        )
    return cleaned


def format_clean_transcript_context(
    transcript_segments: list[dict[str, object]], *, max_chars: int
) -> str:
    lines: list[str] = []
    total = 0
    for segment in clean_transcript_segments(transcript_segments):
        line = (
            f"[{segment.start_offset_seconds}-{segment.end_offset_seconds}s] "
            f"{segment.speaker_label}: {segment.content}"
        )
        if total + len(line) + 1 > max_chars:
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)


def is_useful_transcript_text(text: str) -> bool:
    normalized = clean_transcript_text(text)
    if len(normalized) < 12:
        return False
    lowered = normalized.lower()
    if lowered in NOISE_PHRASES:
        return False
    words = re.findall(r"[a-zA-Z']+", lowered)
    if len(words) < 4:
        return False
    filler_count = sum(1 for word in words if word in FILLER_WORDS)
    if words and filler_count / len(words) > 0.45:
        return False
    unique_words = set(words)
    if len(words) >= 6 and len(unique_words) <= 2:
        return False
    return True


def is_outcome_candidate(text: str) -> bool:
    lowered = clean_transcript_text(text).lower()
    return any(keyword in lowered for keyword in OUTCOME_KEYWORDS)


def evidence_supports_output(description: str, evidence: str) -> bool:
    """Require some lexical overlap so polished text stays grounded."""

    description_words = _meaningful_words(description)
    evidence_words = _meaningful_words(evidence)
    if not description_words or not evidence_words:
        return False
    overlap = description_words & evidence_words
    return len(overlap) >= 2 or bool(overlap & OUTCOME_KEYWORDS)


def normalize_meeting_note_sentence(text: str) -> str:
    cleaned = clean_transcript_text(text)
    cleaned = re.sub(r"^(?:so|okay|right|yeah)[,\s]+", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    if not cleaned:
        return ""
    return cleaned[0].upper() + cleaned[1:]


def _meaningful_words(text: str) -> set[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "by",
        "for",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "to",
        "we",
        "will",
    }
    words = re.findall(r"[a-zA-Z']+", clean_transcript_text(text).lower())
    return {word for word in words if len(word) > 2 and word not in stop_words}


def _collapse_repeated_words(text: str) -> str:
    words = text.split()
    collapsed: list[str] = []
    previous = None
    repeat_count = 0
    for word in words:
        comparable = word.lower().strip(".,!?;:")
        if comparable == previous:
            repeat_count += 1
            if repeat_count > 1:
                continue
        else:
            repeat_count = 0
        collapsed.append(word)
        previous = comparable
    return " ".join(collapsed)


def _collapse_repeated_phrases(text: str) -> str:
    pattern = re.compile(r"\b(.{8,60}?)\s+\1\b", re.I)
    previous = None
    while previous != text:
        previous = text
        text = pattern.sub(r"\1", text)
    return text


def _normalize_int(value: object, *, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
