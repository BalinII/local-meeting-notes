You are building Phase 5 of Local Meeting Notes.

Implement diarization on top of the existing captured audio and transcription pipeline.

Goals:
- add a diarization service boundary
- process captured audio for speaker turns
- persist diarization segments into SQLite
- align transcript segments with diarization output where practical
- update transcript inspection so it can show generic speaker labels such as:
  - Speaker 1
  - Speaker 2
  - Speaker 3

Constraints:
- do not implement participant identity mapping yet
- do not implement Microsoft auth
- do not build a Teams bot
- keep it local-first
- choose a practical diarization approach and justify it
- prefer an offline batch MVP over streaming complexity

Implementation requirements:
- choose concrete diarization libraries and justify them
- keep the diarization provider swappable later
- store diarization segment timing, speaker label, confidence if available, and source audio reference
- handle diarization failure cleanly
- update docs and setup instructions
- add tests where practical
- where transcript-to-speaker alignment is imperfect, prefer explicit limitations over pretending certainty

Output required:
1. plan
2. chosen libraries and why
3. files to change
4. code changes
5. how to run diarization manually
6. limitations and next steps