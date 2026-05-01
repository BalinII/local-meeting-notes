# Current Status

Local Meeting Notes is a working internal prototype for local meeting capture, review, and export.

It is not production-ready.

## Reasonably Ready For Internal Demo Use

- Desktop New Recording entry point.
- Optional meeting/call naming before recording.
- Microphone-only local recording flow.
- Pause, resume, stop, and process lifecycle.
- Local transcription and generic diarization.
- Summary and outcome extraction.
- Human review of actions, decisions, follow-ups, blockers/risks, and open questions.
- Markdown, HTML, and JSON export.
- Session library with local sort/filter controls, search scopes, global action workflow filters, and memory views.
- Local LLM provider option with heuristic fallback.

## Current Product Boundaries

- Local-first Windows desktop prototype.
- No Teams bot or visible meeting attendee.
- No Microsoft auth.
- No production Outlook/Teams integration.
- No participant identity mapping.
- No cloud sync or multi-user collaboration.

## Current Reliability Notes

- Microphone-only recording is the safest validated path.
- System audio / loopback capture is device-dependent and constrained.
- Parallel microphone plus loopback timelines are not yet safely mixed/aligned.
- Stop and Process can take time because processing is local.
- Transcription quality depends on audio quality and model/runtime setup.
- Diarization uses generic speaker labels and can be wrong.
- Search is useful for obvious persisted terms and now groups/deduplicates local matches, but remains basic SQLite-backed search.
- Human review is required for high-trust outputs.

## Review And Export Behavior

- Generated and reviewed values are stored separately where review applies.
- Accepted and edited items are preferred in exports.
- Rejected extracted items are omitted from Markdown and HTML.
- JSON includes more inspection detail for debugging and validation.
- Evidence snippets and provider/model metadata are preserved where available.
- Re-extraction after review is blocked or constrained to avoid silently erasing user work.

## Global Action Workflow

- The global action tracker focuses on actionable `action` and `follow_up` items.
- Workflow states are `open`, `done`, `carried_forward`, and `dismissed`.
- The default view shows active items: open and carried-forward work.
- Users can filter by workflow state and sort by recency, oldest first, owner, or source session.
- Source session, owner, review status, item type, and last-updated time remain visible for traceability.

## Local LLM Behavior

- Ollama is the current local LLM target.
- If local LLM calls fail, time out, return invalid JSON, or produce weakly grounded output, heuristic fallback remains available.
- Weak items may be omitted instead of rewritten into unsupported certainty.
- Ownership remains `Unknown` or `Unconfirmed speaker` when the evidence is weak.

## Biggest Known Limitations

1. Capture reliability varies by Windows hardware, drivers, and audio devices.
2. System audio support is not yet a fully reliable demo promise.
3. Transcription and diarization remain imperfect.
4. Speaker identity mapping is not implemented.
5. Search is practical and scoped, but not full-text ranked search.
6. Local LLM quality varies by model, hardware, and timeout settings.
7. Processing is synchronous from the desktop user's point of view.
8. Operational hardening and observability are prototype-level.

## Recommended Demo Framing

Say:

- "This is a local-first internal prototype."
- "Microphone-only is the safest current recording mode."
- "Human review is expected before sharing notes."
- "The app preserves uncertainty rather than pretending speaker ownership is known."
- "Search and memory views are useful workspace aids, not a finished knowledge product yet."
