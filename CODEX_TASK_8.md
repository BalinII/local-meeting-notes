You are building Phase 8 of Local Meeting Notes.

Goal:
Add a practical human review workflow so generated meeting-note outputs can be edited, accepted, rejected, and saved locally before export.

Current state:
- local capture works
- transcription works
- diarization works at a basic level
- summary and extraction work
- local_llm improves summaries
- the review UI works
- markdown/html/json exports work
- outputs are persisted locally

Business intent:
The product now needs a lightweight human-in-the-loop workflow so imperfect generated outputs can be corrected and finalized.

Primary requirements:
- allow editing of extracted items in the review UI
- allow accept/reject of generated items
- persist reviewed state locally
- preserve original generated content alongside reviewed content
- allow exports to use reviewed content where available

Scope:
- actions
- decisions
- follow-ups
- blockers / risks
- open questions
- optionally summaries if practical, but extracted items are the priority

Constraints:
- do not redesign the whole app
- do not implement participant identity mapping
- do not implement Microsoft auth
- do not build a Teams bot
- keep everything local-first
- work with the current persistence model unless a small extension is clearly justified

Workflow intent:
Each generated item should be able to move through states such as:
- generated
- accepted
- edited
- rejected

Implementation requirements:
- extend persistence to support reviewed state
- preserve original generated text
- store reviewed/edited text separately
- add UI controls for:
  - edit
  - save
  - accept
  - reject
- make reviewed status visible in the UI
- update exports so they prefer reviewed content over raw generated content where available
- keep the UI simple and readable
- add tests where practical
- update docs

Suggested data treatment:
- keep immutable/generated value
- keep reviewed value if edited
- keep review status
- keep timestamps for review updates if practical

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. how to review/edit items in the app
6. how exports behave with reviewed content
7. limitations and next steps

Success criteria:
- I can load a capture in the review UI
- I can edit generated items
- I can accept or reject them
- reviewed state is persisted locally
- exports use reviewed values where present
- the feature works without changing the core backend architecture