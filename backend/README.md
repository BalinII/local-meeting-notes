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
- future diarization pipelines

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
