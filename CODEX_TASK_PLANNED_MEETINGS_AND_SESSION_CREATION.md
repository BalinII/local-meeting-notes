Read AGENTS.md first and follow it.

You are building the next major product-readiness phase for Local Meeting Notes.

Goal:
Move the app closer to a production-ready meeting workflow by introducing planned meeting/session creation and richer session setup, while preserving the current local-first architecture.

Current state:
- recording workflow exists
- meeting naming exists
- review/edit/export exists
- session library, search, actions, memory, and finalisation exist
- the app is still too manual at the front of the workflow:
  - users must create ad hoc recordings manually
  - meeting context is lightweight
  - session naming and structure still rely too much on manual setup

Business intent:
The app should feel more like a real meeting product by making it easier to create, name, and manage sessions before recording begins.

Primary requirements:

1. Planned session creation
Add support for creating a planned meeting/session before recording begins.

Support:
- ad hoc recording
- planned session creation
- starting recording from a planned session

2. Session metadata improvements
Extend session data model conservatively to support useful meeting/session setup fields such as:
- display title
- planned start datetime
- created_at
- updated_at
- session type or source if useful (e.g. ad_hoc / planned)
- optional notes/context field if low risk

3. Upcoming / planned sessions UI
Add a lightweight UI surface for planned sessions.

Examples:
- Upcoming meetings
- Planned sessions
- Quick start area

Users should be able to:
- create a planned session
- see planned sessions
- start recording from a planned session
- still create an ad hoc session easily

4. Preserve current recording flow
Do not break:
- New Recording
- pause/resume/stop/process
- review/export
- library/search/actions/memory

5. Local-first staged design
Do not require Outlook integration in this phase.
Build the product structure first so a future calendar integration can slot in cleanly later.

6. UX quality
Make the front-door workflow clearer:
- ad hoc vs planned
- better naming at creation time
- clearer current/upcoming context
- stronger session identity in library and review flow

Constraints:
- keep everything local-first
- do not implement Outlook integration in this phase
- do not implement Microsoft auth
- do not build a Teams bot
- do not redesign the whole app
- prefer pragmatic schema changes only if needed

Implementation requirements:
- add conservative backend persistence changes if required
- add service/API/Tauri wiring as needed
- update frontend to support planned-session creation and launch
- add focused tests where practical
- update docs for the new planned-session workflow and limitations

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. how planned sessions work
6. how ad hoc vs planned workflows differ
7. tests run
8. limitations and next steps

Success criteria:
- users can create a planned session before recording
- users can start a recording from a planned session
- current ad hoc recording still works
- session identity and naming improve
- the app moves meaningfully closer to later calendar integration
- npm run build passes
- cargo check passes
- relevant tests pass or limitations are stated clearly
