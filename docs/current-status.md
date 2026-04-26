# Current Status: Prototype Maturity and Limits

## Maturity summary

Local Meeting Notes is a **working internal prototype** intended for local testing and stakeholder demos.

It is **not production-ready**.

## What is reasonably ready for internal demo use

- Local capture to filesystem artifacts, with device-dependent reliability limits.
- Offline transcription and generic diarization flow.
- Summary and extracted outcomes generation.
- Review/edit/accept/reject workflow for extracted items.
- Markdown/HTML/JSON export from persisted records.

## What is prototype-only / not production-ready

- No robust speaker identity mapping (generic labels only).
- No enterprise auth, cloud sync, or multi-user collaboration.
- No production Microsoft/Outlook/Teams integration.
- No guarantee of stable quality across all hardware/audio setups.
- Limited operational hardening and observability expected from production systems.
- Parallel microphone plus loopback processing is currently constrained: captured files can exist, but transcription expects one source timeline until mixing/alignment is implemented.

## Biggest known limitations

1. Audio capture reliability varies by Windows device/driver combination.
2. Transcription quality depends on recording conditions.
3. Diarization is heuristic and can mis-assign speaker turns.
4. Local LLM quality depends on model/runtime health and prompt-fit.
5. Human review remains required for high-trust outputs.
6. Re-running extraction after review is blocked to avoid erasing accepted/edited/rejected work.

## Fallback behavior

- If local LLM summary/extraction fails (connectivity, timeout, invalid output, weak grounding), workflow falls back to heuristic provider behavior.
- When speaker ownership is uncertain, outputs preserve uncertainty (`Unknown` / `Unconfirmed speaker`) rather than over-claiming.
- Weak extracted items may be omitted instead of rewritten into confident but unsupported claims.

## Near-term roadmap priorities

1. capture reliability
2. transcription reliability
3. diarization usefulness
4. summary/extraction quality
5. review workflow polish
6. export usability
7. real-meeting validation
