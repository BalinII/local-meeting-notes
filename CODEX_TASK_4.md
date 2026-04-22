You are building Phase 4 of Local Meeting Notes.

Implement the first transcription pipeline on top of the existing audio capture service.

Goals:
- ingest captured audio chunks from backend/data/audio
- create a transcription service boundary
- support local transcription of chunked audio files
- persist transcript chunk metadata and transcript text into SQLite
- connect the transcription flow to the existing schema and repositories
- provide CLI commands to:
  - transcribe a capture by capture id
  - show transcription status
  - list transcript segments for a capture

Constraints:
- do not implement diarization yet
- do not implement speaker attribution yet
- do not implement Microsoft auth
- do not build a Teams bot
- keep it local-first
- choose a practical local transcription approach and justify it
- prefer a batch/offline chunk transcription MVP over streaming complexity

Implementation requirements:
- choose concrete libraries for local transcription and justify them
- make the transcription provider swappable later
- store transcript segments with timestamps, source chunk path, and status
- handle failed chunks cleanly
- update docs and setup instructions
- add tests where practical

Output required:
1. plan
2. chosen libraries and why
3. files to change
4. code changes
5. how to run transcription manually
6. limitations and next steps