"""Provider boundary for local summary generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SummaryDraft:
    title: str
    summary_type: str
    content: str
    evidence_snippet: str | None = None


class HeuristicSummaryProvider:
    """Conservative local summary provider based on transcript evidence."""

    def build_summaries(self, capture_id: str, transcript_segments: list[dict[str, object]]) -> list[SummaryDraft]:
        if not transcript_segments:
            return []

        executive_points = []
        detailed_sections: list[str] = []
        evidence_snippet = None

        for segment in transcript_segments[:5]:
            content = str(segment["content"]).strip()
            if not content:
                continue
            evidence_snippet = evidence_snippet or content[:180]
            executive_points.append(content)

        action_lines = [
            str(segment["content"]).strip()
            for segment in transcript_segments
            if any(keyword in str(segment["content"]).lower() for keyword in ("action", "follow up", "next step"))
        ]
        decision_lines = [
            str(segment["content"]).strip()
            for segment in transcript_segments
            if any(keyword in str(segment["content"]).lower() for keyword in ("decide", "decision", "agreed"))
        ]
        question_lines = [
            str(segment["content"]).strip()
            for segment in transcript_segments
            if "?" in str(segment["content"]) or "question" in str(segment["content"]).lower()
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
            ),
            SummaryDraft(
                title="Detailed Summary",
                summary_type="detailed",
                content=detailed_summary,
                evidence_snippet=evidence_snippet,
            ),
        ]
