"""Provider boundary for local action/decision extraction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExtractedAction:
    description: str
    owner_name: str
    evidence_snippet: str
    start_offset_seconds: int
    end_offset_seconds: int


@dataclass(slots=True)
class ExtractedDecision:
    description: str
    evidence_snippet: str
    start_offset_seconds: int
    end_offset_seconds: int


@dataclass(slots=True)
class ExtractedFollowUp:
    description: str
    follow_up_type: str
    owner_name: str
    evidence_snippet: str
    start_offset_seconds: int
    end_offset_seconds: int


class HeuristicActionExtractionProvider:
    """Conservative extractor that only emits items supported by transcript cues."""

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

        for segment in transcript_segments:
            content = str(segment["content"]).strip()
            if not content:
                continue
            lowered = content.lower()
            owner = self._owner_from_segment(str(segment.get("speaker_label", "Unknown")))
            start = int(segment["start_offset_seconds"])
            end = int(segment["end_offset_seconds"])

            if any(keyword in lowered for keyword in ("action item", "next step", "follow up", "please")):
                actions.append(
                    ExtractedAction(
                        description=content,
                        owner_name=owner,
                        evidence_snippet=content[:220],
                        start_offset_seconds=start,
                        end_offset_seconds=end,
                    )
                )

            if any(keyword in lowered for keyword in ("decision", "decide", "agreed", "we will")):
                decisions.append(
                    ExtractedDecision(
                        description=content,
                        evidence_snippet=content[:220],
                        start_offset_seconds=start,
                        end_offset_seconds=end,
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
                        owner_name=owner if owner != "Unknown" else "Unconfirmed speaker",
                        evidence_snippet=content[:220],
                        start_offset_seconds=start,
                        end_offset_seconds=end,
                    )
                )

        return actions, decisions, follow_ups
