Read AGENTS.md first and follow it.

You are building the next major product-readiness phase for Local Meeting Notes.

Goal:
Move the app closer to a real production meeting workflow by adding lightweight calendar-aware session enrichment and upcoming-meeting creation paths, without overbuilding or redesigning the app.

Current state:
- ad hoc recording exists
- planned sessions / session creation framework is in progress or completed
- review/edit/export exists
- session library, search, actions, memory, and finalisation exist
- the main remaining front-door friction is that sessions still rely too much on manual setup and naming

Business intent:
The app should feel more like a real meeting product by letting users create sessions from upcoming meeting context instead of relying only on ad hoc/manual setup.

Important scope rule:
This phase should introduce the product structure for calendar-aware sessions, but should not become a full calendar/scheduling product.

Primary requirements:

1. Calendar-aware session enrichment structure
Add the minimal structure needed so a session can be associated with calendar/upcoming-meeting context.

Support fields such as:
- source_type (e.g. ad_hoc / planned / calendar_imported)
- external_meeting_id if needed
- imported_title if useful
- planned_start_at
- optional imported metadata needed for display

Keep this conservative.

2. Upcoming meetings / upcoming sessions surface
Add a lightweight UI surface for upcoming meeting-based starts.

The user should be able to see:
- planned sessions
- upcoming meeting-derived sessions (or placeholder/mock imported meetings if live integration is not available yet)

3. Create/start session from calendar context
Support creating a session from meeting context so that:
- title is auto-filled from meeting subject/context
- planned start is carried through
- resulting session has stronger identity in library/review/export/search

4. Preserve manual control
Manual naming/editing should still win.
The user must still be able to:
- create ad hoc recording
- create planned session manually
- start recording from planned/upcoming session
- rename/edit session title as needed

5. Local-first staged design
If live Outlook/M365 integration is not yet practical in this phase, implement the product structure and mock/local pathway cleanly so future integration can slot in with minimal redesign.

This means:
- okay to build the metadata model and UI using a local/mock/provider boundary
- not okay to overbuild auth/integration complexity in this phase

6. UX clarity
Make the front door clearer:
- Ad hoc recording
- Planned session
- From upcoming meeting

Users should understand the difference and choose the right path without clutter.

7. Preserve current app behavior
Do not break:
- recording lifecycle
- review/edit/export
- session library
- search
- actions
- memory
- finalisation/preferred-content behavior

Constraints:
- keep everything local-first
- do not redesign the whole app
- do not implement full Microsoft auth unless the current repo already has a very lightweight safe path
- do not build a Teams bot
- do not turn this into a calendar application
- avoid recurrence/reminders/attendee management complexity
- prefer a provider boundary or staged integration pattern if needed

Implementation requirements:
- keep schema changes conservative
- add backend/session metadata only where clearly justified
- add service/API/Tauri/frontend support for upcoming/calendar-aware session creation
- preserve ad hoc recording as the simplest/default path
- add focused tests where practical
- update docs for:
  - ad hoc vs planned vs calendar-aware session creation
  - current limitations of the enrichment path
  - what is local/mock vs truly integrated

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. how calendar-aware session enrichment works
6. how ad hoc vs planned vs upcoming-meeting creation differs
7. tests run
8. limitations and next steps

Success criteria:
- users can create or start a session from richer meeting context
- session identity/naming improves
- the product moves meaningfully closer to future calendar integration
- ad hoc recording still works
- current product surfaces remain stable
- npm run build passes
- cargo check passes
- relevant tests pass or limitations are stated clearly
