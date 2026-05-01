# Roadmap

This roadmap reflects practical next steps for the local-first prototype. It intentionally avoids Outlook integration, Microsoft auth, Teams bot behavior, cloud sync, and participant identity mapping until the core workflow is stable.

## Guiding Priorities

1. capture reliability
2. transcription reliability
3. diarization usefulness
4. summary and extraction quality
5. review workflow clarity
6. export usability
7. real-meeting validation
8. optional metadata integration
9. optional identity mapping

## Near-Term Stabilization

- Keep recording lifecycle states clear and minimal.
- Continue validating pause/resume/stop behavior on real Windows hardware.
- Improve processing feedback without adding a complex job system too early.
- Keep microphone-only as the recommended demo mode.
- Document system audio constraints honestly.
- Preserve source session traceability in search, actions, memory, review, and export.

## Search And Workspace Quality

- Make search reliable for obvious persisted terms.
- Keep content-state filters understandable: all, reviewed/final, final only.
- Avoid noisy dashboards.
- Prefer simple session-grouped results with clear source links.
- Keep global actions focused on practical workflow states.
- Avoid duplicate action records unless there is a clear source reason.

## Review And Export

- Keep generated, reviewed, and effective values inspectable.
- Continue surfacing uncertainty and evidence.
- Maintain Markdown and HTML as readable internal artifacts.
- Keep JSON structured for debugging and validation.
- Protect reviewed user work from destructive reprocessing.

## Audio And Processing

- Validate microphone capture across more devices.
- Decide the smallest safe path for system audio:
  - explicitly constrain it, or
  - implement mixing/alignment before presenting it as a trusted transcript source.
- Improve failure messages when capture or processing cannot proceed.
- Keep batch processing predictable before introducing more complex background orchestration.

## Local LLM Quality

- Keep heuristic fallback reliable.
- Improve prompt and validation rules only when output quality clearly benefits.
- Favor omission of weak extracted items over confident unsupported statements.
- Continue preserving evidence snippets and provider/model metadata.

## Out Of Scope For Now

- Microsoft auth
- Outlook calendar integration
- Teams bot or meeting attendee
- cloud storage or cloud inference
- enterprise admin controls
- multi-user collaboration
- participant identity mapping

These can be revisited only after local capture, review, export, and real-meeting validation are consistently reliable.
