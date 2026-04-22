"""Provider boundary for local summary generation."""

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


def _normalize_evidence(value: object) -> str | None:
    text = _normalize_text(value)
    return text[:220] if text else None


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
class SummaryDraft:
    title: str
    summary_type: str
    content: str
    evidence_snippet: str | None = None
    provider_name: str = "heuristic"
    model_name: str | None = None
    generated_at: str | None = None


class HeuristicSummaryProvider:
    """Conservative local summary provider based on transcript evidence."""

    provider_name = "heuristic"
    model_name = "heuristic-v1"

    def build_summaries(
        self, capture_id: str, transcript_segments: list[dict[str, object]]
    ) -> list[SummaryDraft]:
        del capture_id
        if not transcript_segments:
            return []

        executive_points = []
        detailed_sections: list[str] = []
        evidence_snippet = None
        generated_at = _now_timestamp()

        for segment in transcript_segments[:5]:
            content = _normalize_text(segment.get("content"))
            if not content:
                continue
            evidence_snippet = evidence_snippet or content[:180]
            executive_points.append(content)

        action_lines = [
            _normalize_text(segment.get("content"))
            for segment in transcript_segments
            if any(
                keyword in _normalize_text(segment.get("content")).lower()
                for keyword in ("action", "follow up", "next step")
            )
        ]
        decision_lines = [
            _normalize_text(segment.get("content"))
            for segment in transcript_segments
            if any(
                keyword in _normalize_text(segment.get("content")).lower()
                for keyword in ("decide", "decision", "agreed")
            )
        ]
        question_lines = [
            _normalize_text(segment.get("content"))
            for segment in transcript_segments
            if "?" in _normalize_text(segment.get("content"))
            or "question" in _normalize_text(segment.get("content")).lower()
        ]

        if executive_points:
            detailed_sections.append("Discussion Highlights:")
            detailed_sections.extend(f"- {line}" for line in executive_points[:5])
        if decision_lines:
            detailed_sections.append("Decisions:")
            detailed_sections.extend(f"- {line}" for line in decision_lines[:3])
        if action_lines:
            detailed_sections.append("Actions and Follow-ups:")
            detailed_sections.extend(f"- {line}" for line in action_lines[:5])
        if question_lines:
            detailed_sections.append("Open Questions:")
            detailed_sections.extend(f"- {line}" for line in question_lines[:3])

        executive_summary = " ".join(executive_points[:3]).strip()
        if not executive_summary:
            executive_summary = "No transcript evidence was available to build an executive summary."

        detailed_summary = "\n".join(detailed_sections).strip()
        if not detailed_summary:
            detailed_summary = "No detailed summary sections could be derived from the transcript evidence."

        return [
            SummaryDraft(
                title="Executive Summary",
                summary_type="executive",
                content=executive_summary,
                evidence_snippet=evidence_snippet,
                provider_name=self.provider_name,
                model_name=self.model_name,
                generated_at=generated_at,
            ),
            SummaryDraft(
                title="Detailed Summary",
                summary_type="detailed",
                content=detailed_summary,
                evidence_snippet=evidence_snippet,
                provider_name=self.provider_name,
                model_name=self.model_name,
                generated_at=generated_at,
            ),
        ]


class LocalLlmSummaryProvider:
    """Ollama-backed summary provider with heuristic fallback."""

    provider_name = "local_llm"

    def __init__(
        self,
        config: AppConfig,
        *,
        logger: logging.Logger | None = None,
        client=None,
        fallback_provider: HeuristicSummaryProvider | None = None,
    ) -> None:
        self.config = config
        self.logger = logger or logging.getLogger("local_meeting_notes.summarizer")
        self.client = client or build_local_llm_client(config)
        self.fallback_provider = fallback_provider or HeuristicSummaryProvider()

    def build_summaries(
        self, capture_id: str, transcript_segments: list[dict[str, object]]
    ) -> list[SummaryDraft]:
        if not transcript_segments:
            return []

        transcript_context = _format_transcript_context(
            transcript_segments, max_chars=self.config.local_llm_max_transcript_chars
        )
        prompt = self._build_prompt(capture_id, transcript_context)

        try:
            payload = self.client.generate_json(prompt)
            return self._normalize_payload(payload)
        except (LocalLlmClientError, ValueError, TypeError) as exc:
            self.logger.warning(
                "Falling back to heuristic summary provider for capture %s: %s",
                capture_id,
                exc,
            )
            return self.fallback_provider.build_summaries(capture_id, transcript_segments)

    def _build_prompt(self, capture_id: str, transcript_context: str) -> str:
        return f"""
You are generating grounded meeting summaries for a local-first notes app.

Rules:
- Use only facts supported by the transcript.
- Do not hallucinate decisions, actions, owners, or outcomes.
- If the transcript is weak, stay conservative.
- Return JSON only.

Output schema:
{{
  "summaries": [
    {{
      "title": "Executive Summary",
      "summary_type": "executive",
      "content": "short grounded summary",
      "evidence_snippet": "short quoted or paraphrased evidence"
    }},
    {{
      "title": "Detailed Summary",
      "summary_type": "detailed",
      "content": "multi-sentence grounded summary grouped by topic where practical",
      "evidence_snippet": "short quoted or paraphrased evidence"
    }}
  ]
}}

Capture ID: {capture_id}

Transcript:
{transcript_context}
""".strip()

    def _normalize_payload(self, payload: dict[str, object]) -> list[SummaryDraft]:
        summaries = payload.get("summaries")
        if not isinstance(summaries, list) or not summaries:
            raise ValueError("Local LLM summary payload must contain a non-empty 'summaries' list.")

        drafts: list[SummaryDraft] = []
        generated_at = _now_timestamp()
        for item in summaries:
            if not isinstance(item, dict):
                raise ValueError("Local LLM summary items must be objects.")
            summary_type = _normalize_text(item.get("summary_type")).lower()
            if summary_type not in {"executive", "detailed"}:
                continue
            content = _normalize_text(item.get("content"))
            title = _normalize_text(
                item.get("title"),
                default="Executive Summary" if summary_type == "executive" else "Detailed Summary",
            )
            if not content:
                continue
            drafts.append(
                SummaryDraft(
                    title=title,
                    summary_type=summary_type,
                    content=content,
                    evidence_snippet=_normalize_evidence(item.get("evidence_snippet")),
                    provider_name=self.provider_name,
                    model_name=self.config.local_llm_model,
                    generated_at=generated_at,
                )
            )

        summary_types = {draft.summary_type for draft in drafts}
        if "executive" not in summary_types or "detailed" not in summary_types:
            raise ValueError("Local LLM summary payload must include executive and detailed summaries.")
        return drafts


def build_summary_provider(
    config: AppConfig,
    *,
    provider_name: str,
    logger: logging.Logger | None = None,
    client=None,
):
    if provider_name == "heuristic":
        return HeuristicSummaryProvider()
    if provider_name == "local_llm":
        return LocalLlmSummaryProvider(config, logger=logger, client=client)
    raise ValueError(f"Unsupported summary provider: {provider_name}")
