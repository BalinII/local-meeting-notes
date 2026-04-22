You are building Phase 6 of Local Meeting Notes.

Implement summary and action extraction on top of the existing transcription and diarization pipeline.

Goals:
- generate a concise executive summary for a capture
- generate a more detailed summary by topic where practical
- extract:
  - decisions
  - actions
  - action owner
  - follow-ups
  - blockers / risks
  - open questions
- persist these outputs into SQLite
- support generic speaker ownership such as:
  - Speaker 1
  - Speaker 2
  when identity is unknown
- add CLI commands to generate and inspect summaries and actions

Constraints:
- do not implement participant identity mapping yet
- do not implement Microsoft auth
- do not build a Teams bot
- keep it local-first
- prefer explicit uncertainty over invented certainty
- where ownership is unclear, mark as unknown or unconfirmed
- do not hallucinate decisions or actions not supported by transcript evidence
- assume diarization quality is imperfect and design around that reality

Implementation requirements:
- create a summarization / extraction service boundary
- make the provider swappable later
- include transcript evidence snippets and timing references where practical
- persist summaries, actions, decisions, and follow-ups
- add tests where practical
- update docs and setup instructions
- when diarization labels are missing, allow outputs to use `Unknown` or `Unconfirmed speaker`

Output required:
1. plan
2. chosen approach and why
3. files to change
4. code changes
5. how to run summary/action extraction manually
6. limitations and next steps