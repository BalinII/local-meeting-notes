Read AGENTS.md first and follow it.

You are building the next major product-readiness phase for Local Meeting Notes.

Goal:
Turn the action tracker into a more genuinely operational workflow by adding lightweight follow-through features, while keeping the app local-first and avoiding full project-management complexity.

Current state:
- global action tracker exists
- action workflow states exist
- actions can be reviewed and updated
- session library, search, memory, finalisation, and recording flow exist
- live/planned/upcoming meeting context may exist or be in progress
- the main product gap is follow-through between meetings: actions are visible, but not yet rich enough to manage meaningfully over time

Business intent:
The app should help users not only capture actions, but also carry them forward, track them over time, and stay oriented on what still matters across meetings.

Scope principle:
This phase should make actions more operational, but should not turn the app into a full project-management system.

Primary requirements:

1. Due dates
Add lightweight due-date support for actions.

Users should be able to:
- view a due date
- set or edit a due date
- clear a due date if needed

Keep this minimal and local-first.

2. Action notes / follow-through detail
Add a lightweight notes field or update field for actions so users can store:
- short follow-up notes
- clarifications
- dependency/context reminders
- next-step detail

Do not overbuild comments/threading/history unless trivial.

3. Better carry-forward behavior
Improve carried-forward workflow so it is more than just a status flag.

Support clarity around:
- action is still active
- action was carried forward from a prior session
- source/origin session remains visible
- current status remains understandable

If practical, preserve or surface “carried from” context without duplicating records unnecessarily.

4. Better action views
Improve the global action workspace so users can work more naturally across time.

Examples:
- open
- done
- carried forward
- dismissed
- due soon
- overdue
- done recently
- grouped by owner
- grouped by source session

Keep this pragmatic and avoid overbuilding.

5. Upcoming-session continuity
If low risk and practical, surface unresolved open/carried-forward actions when starting or viewing a planned/upcoming/current meeting context.

This should be lightweight and helpful, not intrusive.

6. Preserve traceability
Keep:
- source session
- content state / provenance where useful
- local-first auditability

7. Preserve current app behavior
Do not break:
- recording lifecycle
- review/edit/export
- session library
- search
- memory
- finalisation
- upcoming/planned/live meeting flows if present

Constraints:
- keep everything local-first
- do not redesign the whole app
- do not implement Outlook/Todo/Planner/Jira-style deep integrations in this phase
- do not turn this into a full task management system
- avoid unnecessary schema churn beyond what is clearly justified

Implementation requirements:
- add minimal persistence changes only where needed
- extend backend/service/API/Tauri/frontend support as needed
- keep UX lightweight and operational
- add focused tests where practical
- update docs for:
  - due dates
  - notes
  - carry-forward behavior
  - action continuity across meetings
  - current limitations

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. how due dates work
6. how action notes work
7. how carry-forward/continuity works
8. how the action workspace behaves after the change
9. tests run
10. limitations and next steps

Success criteria:
- users can manage actions more meaningfully over time
- due dates and notes work cleanly
- carried-forward actions have clearer continuity
- action workspace becomes more operational without becoming a full PM tool
- current product surfaces remain stable
- npm run build passes
- cargo check passes
- relevant tests pass or limitations are stated clearly
