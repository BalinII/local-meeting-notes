Read AGENTS.md first and follow it.

You are building the next major product-readiness phase for Local Meeting Notes.

Goal:
Add lightweight meeting continuity and pre-meeting briefing so the app helps users understand what still matters before a meeting starts, while preserving the current local-first workflow and avoiding project-management bloat.

Current state:
- recording workflow exists
- review/edit/export exists
- session library, search, actions, and memory exist
- finalisation/preferred-content behavior exists
- planned/upcoming/session-creation work exists or is in progress
- action workflow maturity exists or is in progress
- the next product gap is continuity between meetings:
  - unresolved actions from prior meetings are not surfaced clearly enough when starting a related session
  - users do not yet get a lightweight “briefing” before a meeting
  - prior decisions, blockers, and open questions are not pulled together into a compact, useful pre-meeting view

Business intent:
The app should now help users prepare for a meeting, not just capture and process it. Before a meeting begins, users should be able to see the most relevant unresolved context from prior meetings.

Scope principle:
This phase should provide lightweight continuity and briefing. It should not become a full meeting-prep, project-management, or analytics system.

Primary requirements:

1. Pre-meeting briefing
Add a lightweight briefing view/surface for a planned/upcoming/current session that can show, where relevant:
- unresolved open actions
- carried-forward actions
- recent key decisions
- active blockers / risks
- open questions still unresolved
- optionally a short prior-session summary if low risk and already easy to derive

Keep this concise and scannable.

2. Related-session continuity
Provide a pragmatic way to determine related context for a session.

Examples:
- prior sessions with the same title or linked meeting context
- sessions connected via planned/upcoming/calendar-aware metadata
- carried-forward action source sessions

Do not build a complex relationship engine. Use the simplest reliable linkage already available or a conservative heuristic.

3. Start-session continuity surface
When starting or opening a planned/upcoming/current session, surface helpful continuity context in a non-intrusive way.

Examples:
- a compact “Before you start” panel
- a continuity/briefing section
- unresolved actions carried from prior related sessions

This should help, not overwhelm.

4. Carry-forward continuity visibility
Make it clearer when an action shown in briefing or current context came from a prior session.

Preserve:
- source session visibility
- due date / notes if already supported
- workflow state clarity

5. Briefing behavior rules
The briefing should:
- prefer final/reviewed content where available
- suppress rejected/noisy content
- stay focused on what is still relevant
- avoid showing too much old/duplicate information

6. Preserve current workflows
Do not break:
- ad hoc recording
- planned/upcoming session creation
- review/edit/export
- library/search/actions/memory
- finalisation/preferred-content behavior

7. Local-first and low-risk design
Keep this:
- local-first
- lightweight
- explainable
- easy to maintain

Do not add:
- a new search engine
- full project-management workflows
- reminder systems
- analytics dashboards
- Teams bot behavior
- broad Outlook/Microsoft workflow complexity beyond what already exists

Constraints:
- keep everything local-first
- do not redesign the whole app
- do not implement deep calendar/productivity semantics
- do not add unnecessary schema churn unless clearly justified
- preserve manual control and clarity
- prefer pragmatic reuse of existing actions/memory/search/session-linkage data over new heavy abstractions

Testing / CI guardrails:
- Assume this repo has active CI and branch protection.
- Your changes must preserve existing required checks:
  - Backend tests
  - Frontend build and smoke tests
  - Tauri cargo check
- Add or update focused pytest coverage for any new continuity/briefing logic, especially:
  - briefing selection logic
  - related-session determination
  - carry-forward visibility
  - preference for reviewed/final content
  - suppression of rejected/noisy content
- Extend lightweight frontend smoke coverage where practical if important UI visibility/entry points change.
- Do not bypass, weaken, or remove existing checks.
- Treat automated testing as a merge gate.
- If some behavior cannot be fully validated end-to-end in the container, add the strongest practical automated coverage and clearly state what still requires manual smoke testing.
- In the final report, list:
  1. exact tests added/updated
  2. exact test/build/check commands run
  3. what still needs manual validation

Implementation requirements:
- add conservative backend/service support for generating a session briefing
- use existing data sources where practical:
  - actions
  - decisions
  - blockers / risks
  - open questions
  - session metadata / related-session context
- add Tauri/frontend support for surfacing briefing in the right places
- keep UI low-clutter
- add focused tests where practical
- update docs for:
  - what briefing shows
  - how related context is chosen
  - current limitations
  - how this fits planned/upcoming/current sessions

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. how briefing works
6. how related-session continuity is determined
7. how carry-forward actions appear in briefing/current-session context
8. exact tests added/updated
9. exact test/build/check commands run
10. what still needs manual validation
11. limitations and next steps

Success criteria:
- users can see a concise, useful briefing before or when opening a relevant session
- unresolved actions and relevant prior context are surfaced more clearly
- source-session continuity remains visible
- briefing prefers better reviewed/final content
- the app becomes more useful before the meeting starts
- current product surfaces remain stable
- relevant pytest coverage is added/updated for new behavior
- frontend build and smoke checks remain green
- cargo check remains green
- any remaining manual-only validation gaps are called out clearly
