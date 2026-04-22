# Local Meeting Notes Backend

Backend package for the Local Meeting Notes desktop application.

This package contains:
- configuration loading
- logging setup
- SQLite bootstrap
- storage and repositories
- CLI entrypoints
- audio capture services
- future transcription and diarization pipelines

## Windows Loopback Notes

- System loopback capture uses the `soundcard` library's loopback microphone API, not the speaker object directly.
- On Windows, loopback can still fail on some devices because of driver quirks, exclusive-mode settings, Bluetooth audio routing, or unsupported sample rates.
- The capture worker now forces an explicit startup transition:
  - `starting -> running` after the stream opens and the first loopback frames are read
  - `starting -> failed` with a clear reason if startup times out or the stream open fails
