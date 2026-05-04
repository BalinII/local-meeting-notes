Read AGENTS.md first and follow it.

You are building the next major product-readiness phase for Local Meeting Notes.

Goal:
Add real live calendar integration so users can see upcoming meetings and create/start sessions from actual calendar items, while keeping the app local-first and avoiding broad calendar-product scope.

Current state:
- ad hoc recording exists
- planned sessions / upcoming session structure exists
- session enrichment model support exists or is being added
- review/edit/export exists
- session library, search, actions, memory, and finalisation exist
- the current gap is that upcoming meeting/session context is still manual or mock-like rather than coming from a live calendar source

Business intent:
The app should feel more production-ready by reducing manual setup and letting users create/start sessions from real upcoming meetings.

Scope principle:
This phase is about lightweight read integration for upcoming meetings and session enrichment. It is not a full calendar/scheduling product.

Primary requirements:

1. Live calendar provider integration
Add a provider path for reading upcoming meetings from a real calendar source.

Target:
- Outlook / Microsoft 365 calendar is preferred if practical
- if a provider boundary already exists or should exist, use it
- integration should focus on reading upcoming meetings only

2. Upcoming meetings surface
Replace or enrich the current upcoming/planned surface with real upcoming meetings where available.

The UI should allow users to:
- view upcoming meetings
- understand which meetings came from calendar vs manual planned session flow
- create or start a session from an upcoming meeting

3. Session creation from live calendar items
Support creating a session from a real meeting item so that the session inherits useful context such as:
- title/subject
- planned start time
- source type
- external meeting id if needed
- any lightweight metadata already justified by the current model

4. Manual control remains authoritative
Preserve:
- ad hoc recording
- manual planned-session creation
- manual renaming/editing
- manual user changes must always win over imported calendar defaults

5. Conservative integration design
Keep this phase narrow:
- read upcoming meetings
- create/start session from a meeting
- do not build recurrence
- do not build reminders
- do not build attendee management workflows
- do not build a Teams bot
- do not turn this into a calendar application

6. Local-first behavior and safe degradation
If live calendar access is unavailable or not configured:
- the app should fail gracefully
- manual/planned paths should still work
- the UI should make the limitation understandable

7. UX clarity
Make the front door clearer with three paths:
- Ad hoc recording
- Planned session
- From upcoming meeting

Keep ad hoc recording the simplest/default path.

Constraints:
- keep everything local-first in spirit
- do not redesign the whole app
- do not implement Teams bot behavior
- do not add broad Microsoft-product workflows
- avoid unnecessary schema churn
- prefer a staged/provider-boundary design if helpful

Implementation requirements:
- add minimal integration/provider/service code needed to fetch upcoming meetings
- add conservative session enrichment/linkage fields only if clearly needed
- update backend/API/Tauri/frontend wiring as needed
- preserve current recording/review/export/library/search/actions/memory/finalisation behavior
- add focused tests where practical
- update docs for:
  - how calendar integration works
  - what is required/configured
  - fallback behavior when unavailable
  - current limitations

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. how live upcoming meetings work
6. how session creation from calendar items works
7. fallback behavior when calendar access is unavailable
8. tests run
9. limitations and next steps

Success criteria:
- users can see real upcoming meetings when configured
- users can create or start a session from a live calendar item
- session naming/context improves
- ad hoc and manual planned flows still work
- the app moves meaningfully closer to production-ready front-door workflow
- npm run build passes
- cargo check passes
- relevant tests pass or limitations are stated clearly
