"""Provider boundary for local action/decision extraction."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from ..config import AppConfig
from ..local_llm import LocalLlmClientError, build_local_llm_client


def _now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _normalize_text(value: object, *, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _normalize_owner(value: object) -> str:
    owner = _normalize_text(value, default="Unconfirmed speaker")
    if owner.lower() in {"unknown", "unconfirmed", "unconfirmed speaker"}:
        return "Unconfirmed speaker"
    return owner


def _normalize_int(value: object, *, default: int = 0) -> int:
    if value is None or value == "":
        return default
    return int(float(value))


def _normalize_evidence(value: object) -> str:
    text = _normalize_text(value)
    return text[:220] if text else ""


def _format_transcript_context(
    transcript_segments: list[dict[str, object]], *, max_chars: int
) -> str:
    lines: list[str] = []
    total = 0
    for segment in transcript_segments:
        content = _normalize_text(segment.get("content"))
        if not content:
            continue
        speaker = _normalize_text(segment.get("speaker_label"), default="Unknown")
        start = int(segment.get("start_offset_seconds", 0))
        end = int(segment.get("end_offset_seconds", start))
        line = f"[{start}-{end}s] {speaker}: {content}"
        if total + len(line) + 1 > max_chars:
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)


@dataclass(slots=True)
class ExtractedAction:
    description: str
    owner_name: str
    evidence_snippet: str
    start_offset_seconds: int
    end_offset_seconds: int
    provider_name: str = "heuristic"
    model_name: str | None = None
    generated_at: str | None = None


@dataclass(slots=True)
class ExtractedDecision:
    description: str
    evidence_snippet: str
    start_offset_seconds: int
    end_offset_seconds: int
    provider_name: str = "heuristic"
    model_name: str | None = None
    generated_at: str | None = None


@dataclass(slots=True)
class ExtractedFollowUp:
    description: str
    follow_up_type: str
    owner_name: str
    evidence_snippet: str
    start_offset_seconds: int
    end_offset_seconds: int
    provider_name: str = "heuristic"
    model_name: str | None = None
    generated_at: str | None = None


class HeuristicActionExtractionProvider:
    """Conservative extractor that only emits items supported by transcript cues."""

    provider_name = "heuristic"
    model_name = "heuristic-v1"

    def _owner_from_segment(self, speaker_label: str) -> str:
        if not speaker_label or speaker_label == "Unknown":
            return "Unconfirmed speaker"
        return speaker_label

    def extract(
        self, transcript_segments: list[dict[str, object]]
    ) -> tuple[list[ExtractedAction], list[ExtractedDecision], list[ExtractedFollowUp]]:
        actions: list[ExtractedAction] = []
        decisions: list[ExtractedDecision] = []
        follow_ups: list[ExtractedFollowUp] = []
        generated_at = _now_timestamp()

        for segment in transcript_segments:
            content = _normalize_text(segment.get("content"))
            if not content:
                continue
            lowered = content.lower()
            owner = self._owner_from_segment(_normalize_text(segment.get("speaker_label"), default="Unknown"))
            start = _normalize_int(segment.get("start_offset_seconds"))
            end = _normalize_int(segment.get("end_offset_seconds"), default=start)

            if any(keyword in lowered for keyword in ("action item", "next step", "follow up", "please")):
                actions.append(
                    ExtractedAction(
                        description=content,
                        owner_name=owner,
                        evidence_snippet=content[:220],
                        start_offset_seconds=start,
                        end_offset_seconds=end,
                        provider_name=self.provider_name,
                        model_name=self.model_name,
                        generated_at=generated_at,
                    )
                )

            if any(keyword in lowered for keyword in ("decision", "decide", "agreed", "we will")):
                decisions.append(
                    ExtractedDecision(
                        description=content,
                        evidence_snippet=content[:220],
                        start_offset_seconds=start,
                        end_offset_seconds=end,
                        provider_name=self.provider_name,
                        model_name=self.model_name,
                        generated_at=generated_at,
                    )
                )

            if any(keyword in lowered for keyword in ("blocker", "risk", "open question", "question", "follow up")):
                follow_up_type = "follow_up"
                if "blocker" in lowered or "risk" in lowered:
                    follow_up_type = "blocker_risk"
                elif "question" in lowered:
                    follow_up_type = "open_question"
                follow_ups.append(
                    ExtractedFollowUp(
                        description=content,
                        follow_up_type=follow_up_type,
                        owner_name=owner,
                        evidence_snippet=content[:220],
                        start_offset_seconds=start,
                        end_offset_seconds=end,
                        provider_name=self.provider_name,
                        model_name=self.model_name,
                        generated_at=generated_at,
                    )
                )

        return actions, decisions, follow_ups


class LocalLlmActionExtractionProvider:
    """Ollama-backed extraction provider with heuristic fallback."""

    provider_name = "local_llm"

    def __init__(
        self,
        config: AppConfig,
        *,
        logger: logging.Logger | None = None,
        client=None,
        fallback_provider: HeuristicActionExtractionProvider | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("local_meeting_notes.action_extractor")
        self.client = client or build_local_llm_client(config)
        self.fallback_provider = fallback_provider or HeuristicActionExtractionProvider()

    def extract(
        self, transcript_segments: list[dict[str, object]]
    ) -> tuple[list[ExtractedAction], list[ExtractedDecision], list[ExtractedFollowUp]]:
        if not transcript_segments:
            return [], [], []

        prompt = self._build_prompt(
            _format_transcript_context(
                transcript_segments, max_chars=self.config.local_llm_max_transcript_chars
            )
        )
        try:
            payload = self.client.generate_json(prompt)
            return self._normalize_payload(payload)
        except (LocalLlmClientError, ValueError, TypeError) as exc:
            self.logger.warning("Falling back to heuristic action extractor: %s", exc)
            return self.fallback_provider.extract(transcript_segments)

    def _build_prompt(self, transcript_context: str) -> str:
        return f"""
You are extracting meeting outcomes for a local-first notes app.

Rules:
- Use only transcript-supported evidence.
- Do not invent facts, owners, or decisions.
- If ownership is unclear, use "Unknown" or "Unconfirmed speaker".
- If an action or decision is weakly supported, omit it.
- Return JSON only.

Output schema:
{{
  "actions": [
    {{
      "description": "clear action",
      "owner_name": "Speaker 1",
      "evidence_snippet": "supporting transcript text",
      "start_offset_seconds": 0,
      "end_offset_seconds": 8
    }}
  ],
  "decisions": [
    {{
      "description": "clear decision",
      "evidence_snippet": "supporting transcript text",
      "start_offset_seconds": 0,
      "end_offset_seconds": 8
    }}
  ],
  "follow_ups": [
    {{
      "description": "open issue or follow-up",
      "follow_up_type": "follow_up",
      "owner_name": "Unconfirmed speaker",
      "evidence_snippet": "supporting transcript text",
      "start_offset_seconds": 9,
      "end_offset_seconds": 16
    }}
  ]
}}

Allowed follow_up_type values:
- follow_up
- blocker_risk
- open_question

Transcript:
{transcript_context}
""".strip()

    def _normalize_payload(
        self, payload: dict[str, object]
    ) -> tuple[list[ExtractedAction], list[ExtractedDecision], list[ExtractedFollowUp]]:
        generated_at = _now_timestamp()
        actions = self._normalize_actions(payload.get("actions"), generated_at)
        decisions = self._normalize_decisions(payload.get("decisions"), generated_at)
        follow_ups = self._normalize_follow_ups(payload.get("follow_ups"), generated_at)
        return actions, decisions, follow_ups

    def _normalize_actions(
        self, raw_items: object, generated_at: str
    ) -> list[ExtractedAction]:
        if raw_items is None:
            return []
        if not isinstance(raw_items, list):
            raise ValueError("Local LLM actions payload must be a list.")
        items: list[ExtractedAction] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise ValueError("Local LLM action items must be objects.")
            description = _normalize_text(raw.get("description"))
            evidence = _normalize_evidence(raw.get("evidence_snippet"))
            if not description or not evidence:
                continue
            start = _normalize_int(raw.get("start_offset_seconds"))
            end = _normalize_int(raw.get("end_offset_seconds"), default=start)
            items.append(
                ExtractedAction(
                    description=description,
                    owner_name=_normalize_owner(raw.get("owner_name")),
                    evidence_snippet=evidence,
                    start_offset_seconds=start,
                    end_offset_seconds=end,
                    provider_name=self.provider_name,
                    model_name=self.config.local_llm_model,
                    generated_at=generated_at,
                )
            )
        return items

    def _normalize_decisions(
        self, raw_items: object, generated_at: str
    ) -> list[ExtractedDecision]:
        if raw_items is None:
            return []
        if not isinstance(raw_items, list):
            raise ValueError("Local LLM decisions payload must be a list.")
        items: list[ExtractedDecision] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise ValueError("Local LLM decision items must be objects.")
            description = _normalize_text(raw.get("description"))
            evidence = _normalize_evidence(raw.get("evidence_snippet"))
            if not description or not evidence:
                continue
            start = _normalize_int(raw.get("start_offset_seconds"))
            end = _normalize_int(raw.get("end_offset_seconds"), default=start)
            items.append(
                ExtractedDecision(
                    description=description,
                    evidence_snippet=evidence,
                    start_offset_seconds=start,
                    end_offset_seconds=end,
                    provider_name=self.provider_name,
                    model_name=self.config.local_llm_model,
                    generated_at=generated_at,
                )
            )
        return items

    def _normalize_follow_ups(
        self, raw_items: object, generated_at: str
    ) -> list[ExtractedFollowUp]:
        if raw_items is None:
            return []
        if not isinstance(raw_items, list):
            raise ValueError("Local LLM follow_ups payload must be a list.")
        items: list[ExtractedFollowUp] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise ValueError("Local LLM follow-up items must be objects.")
            description = _normalize_text(raw.get("description"))
            evidence = _normalize_evidence(raw.get("evidence_snippet"))
            follow_up_type = _normalize_text(raw.get("follow_up_type"), default="follow_up")
            if follow_up_type not in {"follow_up", "blocker_risk", "open_question"}:
                follow_up_type = "follow_up"
            if not description or not evidence:
                continue
            start = _normalize_int(raw.get("start_offset_seconds"))
            end = _normalize_int(raw.get("end_offset_seconds"), default=start)
            items.append(
                ExtractedFollowUp(
                    description=description,
                    follow_up_type=follow_up_type,
                    owner_name=_normalize_owner(raw.get("owner_name")),
                    evidence_snippet=evidence,
                    start_offset_seconds=start,
                    end_offset_seconds=end,
                    provider_name=self.provider_name,
                    model_name=self.config.local_llm_model,
                    generated_at=generated_at,
                )
            )
        return items


def build_action_extraction_provider(
    config: AppConfig,
    *,
    provider_name: str,
    logger: logging.Logger | None = None,
    client=None,
):
    if provider_name == "heuristic":
        return HeuristicActionExtractionProvider()
    if provider_name == "local_llm":
        return LocalLlmActionExtractionProvider(config, logger=logger, client=client)
    raise ValueError(f"Unsupported action extraction provider: {provider_name}")
