You are building Phase 2 of Local Meeting Notes.

Implement the Python backend skeleton only.

Goals:
- add config loading
- add logging
- add SQLite connection and schema bootstrap
- add base models for:
  - meetings
  - participants
  - transcript_segments
  - summaries
  - actions
  - decisions
- add a simple CLI entrypoint to:
  - initialise the app
  - bootstrap the database
  - start a mock meeting session
  - stop a mock meeting session
- keep the implementation local-first and minimal

Constraints:
- do not implement real transcription yet
- do not implement real Microsoft Graph auth yet
- do not implement a Teams bot
- use mocked transcript segments where needed
- keep imports and project structure aligned with backend/src/local_meeting_notes
- include tests for:
  - config loading
  - database bootstrap
  - basic model persistence or schema presence

Output required:
1. plan
2. files to change
3. code changes
4. setup/run instructions
5. limitations and next steps