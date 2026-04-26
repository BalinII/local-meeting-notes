# Local Meeting Notes Backend

Backend package for the Local Meeting Notes desktop application.

This package contains:
- configuration loading
- logging setup
- SQLite bootstrap
- storage and repositories
- CLI entrypoints
- audio capture services
- local chunk transcription
- local diarization
- local summary generation
- local action and decision extraction
- local LLM-backed summary and extraction providers
- Markdown, HTML, and JSON exports

## Windows Loopback Notes

- System loopback capture uses the `soundcard` library's loopback microphone API, not the speaker object directly.
- On Windows, loopback can still fail on some devices because of driver quirks, exclusive-mode settings, Bluetooth audio routing, or unsupported sample rates.
- The capture worker now forces an explicit startup transition:
  - `starting -> running` after the stream opens and the first loopback frames are read
  - `starting -> failed` with a clear reason if startup times out or the stream open fails

## Local Transcription Notes

- Phase 4 uses `faster-whisper` as the first local batch transcription backend because it is practical for offline chunk transcription and easy to wrap behind a provider boundary.
- Transcript segments are persisted in SQLite with:
  - `capture_id`
  - `source_chunk_path`
  - `transcription_status`
  - offsets
  - transcript text
  - provider/model metadata
  - failure details when a chunk fails
- CLI commands:
  - `python -m local_meeting_notes.app transcript transcribe --capture-id <capture-id>`
  - `python -m local_meeting_notes.app transcript status --capture-id <capture-id>`
  - `python -m local_meeting_notes.app transcript list --capture-id <capture-id>`

## Local Diarization Notes

- Phase 5 uses a swappable diarization provider boundary.
- The default MVP provider uses `librosa` features plus `scikit-learn` clustering for offline generic speaker-turn segmentation.
- This tuning pass prefers fewer, more stable speaker turns over aggressive short-window segmentation.
- Diarization segments are stored in SQLite with:
  - `capture_id`
  - `source_audio_path`
  - `diarization_status`
  - `speaker_label`
  - offsets
  - provider metadata
  - confidence when it is actually meaningful
  - failure details
- Transcript speaker labels are updated by best-effort timing overlap with diarization segments.
- If confidence is not meaningful for the current provider, it is left unset instead of emitting fake precision.
- Transcript speaker propagation still remains heuristic and may stay `Unknown` when overlap is weak.
- CLI commands:
  - `python -m local_meeting_notes.app diarize run --capture-id <capture-id>`
  - `python -m local_meeting_notes.app diarize status --capture-id <capture-id>`
  - `python -m local_meeting_notes.app diarize list --capture-id <capture-id>`

## Local Summary And Extraction Notes

- Phase 6 adds swappable service boundaries for:
  - summary generation
  - action and decision extraction
- The default implementations are local and heuristic, designed to work on top of imperfect diarization rather than assuming strong speaker identity.
- Outputs are persisted in SQLite for each `capture_id`:
  - `summaries`
  - `actions`
  - `decisions`
  - `follow_ups`
- Evidence is stored alongside outputs where practical so the CLI can show why an item was generated.
- Ownership remains intentionally conservative:
  - `Speaker 1`, `Speaker 2`, and similar generic labels are allowed
  - `Unknown` or `Unconfirmed speaker` is preferred over invented certainty
- Follow-ups include open questions and blockers or risks so unresolved items are still inspectable even when they are not clear action items.
- CLI commands:
  - `python -m local_meeting_notes.app summary generate --capture-id <capture-id>`
  - `python -m local_meeting_notes.app summary show --capture-id <capture-id>`
  - `python -m local_meeting_notes.app actions extract --capture-id <capture-id>`
  - `python -m local_meeting_notes.app actions list --capture-id <capture-id>`

## Local LLM Notes

- Phase 6C adds a `local_llm` provider mode alongside the existing `heuristic` mode.
- The first implementation targets Ollama's local HTTP API.
- Prompts require JSON-only output and explicitly forbid unsupported claims.
- Model output is validated and normalized before persistence.
- Transcript input is cleaned before prompting to suppress ASR noise, filler-only fragments, repeated words, and common inaudible/noise markers.
- Output filtering rejects weakly grounded or malformed summaries, decisions, actions, and follow-ups.
- If the local runtime fails, times out, or returns invalid JSON, the service falls back to the heuristic provider.
- Summary, action, decision, and follow-up rows now store:
  - `provider_name`
  - `model_name`
  - `generated_at`
- CLI additions:
  - `python -m local_meeting_notes.app llm check`
  - `python -m local_meeting_notes.app summary generate --capture-id <capture-id> --provider local_llm`
  - `python -m local_meeting_notes.app actions extract --capture-id <capture-id> --provider local_llm`

Quality retest flow:
- Run `summary generate` and `actions extract` with `--provider local_llm` on a real capture.
- Inspect `summary show` and `actions list`.
- Confirm garbled ASR fragments are omitted, evidence snippets still point back to transcript text, and uncertain ownership remains generic.

## Review And Export Notes

- Phase 7 adds a review payload and export service on top of existing SQLite outputs.
- Phase 8 adds local review state for extracted items. Generated descriptions stay intact; reviewed descriptions, reviewed owner text, review status, and review timestamps are stored separately.
- Phase 9 adds a persisted session workflow around the existing local pipeline: named sessions, lifecycle state, recent-session listing, raw-audio retention, and cleanup helpers.
- Export formats:
  - Markdown: `python -m local_meeting_notes.app export run --capture-id <capture-id> --format markdown`
  - HTML: `python -m local_meeting_notes.app export run --capture-id <capture-id> --format html`
  - JSON: `python -m local_meeting_notes.app export run --capture-id <capture-id> --format json`
- Review payload command:
  - `python -m local_meeting_notes.app review show --capture-id <capture-id> --format json`
  - `python -m local_meeting_notes.app review show --capture-id <capture-id> --format markdown`
- Review update command:
  - `python -m local_meeting_notes.app review update-item --item-type action --item-id <id> --review-status accepted`
  - `python -m local_meeting_notes.app review update-item --item-type follow_up --item-id <id> --review-status edited --description "Reviewed text" --owner-name "Reviewed owner"`
- Session workflow commands:
  - `python -m local_meeting_notes.app session create --title "Weekly Product Sync"`
  - `python -m local_meeting_notes.app session record-start --capture-id <capture-id>`
  - `python -m local_meeting_notes.app session pause --capture-id <capture-id>`
  - `python -m local_meeting_notes.app session resume --capture-id <capture-id>`
  - `python -m local_meeting_notes.app session record-stop --capture-id <capture-id>`
  - `python -m local_meeting_notes.app session list`
  - `python -m local_meeting_notes.app session retention-show`
  - `python -m local_meeting_notes.app session retention-update --raw-audio-retention-days 14 --delete-temp-processing-files true`
  - `python -m local_meeting_notes.app session cleanup`
- Exported files are written to `backend/data/exports/<capture-id>/`.
- The payload separates follow-ups, blockers/risks, and open questions for cleaner review.
- Markdown and HTML exports use reviewed text where available and omit rejected extracted items. JSON exports keep the full review payload, including original and reviewed fields.
- Recording pause/resume stays inside one immutable `capture_id`; new audio chunks are appended into the same capture directory with deterministic chunk prefixes so later transcription and diarization preserve order across resumed recordings.
