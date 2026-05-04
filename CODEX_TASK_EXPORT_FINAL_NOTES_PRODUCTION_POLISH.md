Read AGENTS.md first and follow it.

You are building the next major product-readiness phase for Local Meeting Notes.

Goal:
Make exports and finalized notes feel substantially more production-ready, polished, and shareable without redesigning the app or changing core local-first architecture.

Current state:
- recording workflow exists
- review/edit/export workflow exists
- finalisation/preferred-content behavior exists
- session library, search, actions, memory, and briefing/continuity may exist
- outputs are usable, but still risk feeling too much like internal/generated artifacts rather than polished final meeting notes

Business intent:
The app should produce cleaner, more trustworthy final notes suitable for internal sharing and daily use. This phase should improve the last-mile quality of the product.

Primary requirements:

1. Final notes export mode
- support or refine a cleaner “final notes” export path or mode
- finalized/reviewed content should be preferred
- raw/generated/audit-heavy content should not dominate by default
- preserve provenance and traceability where useful, but keep it secondary

2. Export presentation quality
Improve Markdown and HTML exports so they feel more polished and intentional.

Focus on:
- better title/header presentation
- clearer metadata hierarchy
- cleaner section ordering
- better formatting of:
  - executive summary
  - detailed summary
  - actions
  - decisions
  - follow-ups
  - blockers / risks
  - open questions
  - pre-meeting briefing if relevant and low-risk
- better handling of empty sections
- better readability and printability for HTML
- better pasteability for Markdown

3. Finalized session behavior
- finalized sessions should clearly export the best available version of content
- reviewed/final content should be preferred consistently
- generated/raw content should be secondary and only included when appropriate

4. Export choices
If low risk and practical, support or refine a clear distinction such as:
- Final Notes
- Full Detail / Audit View

Keep this lightweight and avoid overbuilding.

5. Share-readiness
Make exported output feel suitable for:
- internal team sharing
- project follow-up
- meeting outcome tracking
without looking like a prototype dump

6. Lightweight export UX improvements
If practical and low risk:
- clearer export button labels/copy
- better confirmation after export
- cleaner export filenames
- copy final notes to clipboard if already easy and safe

Constraints:
- keep everything local-first
- do not redesign the whole app
- do not implement Outlook integration
- do not implement Microsoft auth
- do not build a Teams bot
- preserve current recording/review/library/search/actions/memory/briefing behavior
- do not remove auditability entirely; keep it available where useful

Testing / CI guardrails:
- Assume this repo has active CI and branch protection.
- Your changes must preserve existing required checks:
  - Backend tests
  - Frontend build and smoke tests
  - Tauri cargo check
- Add or update focused pytest coverage for export selection and presentation behavior, especially:
  - final/reviewed content preference
  - export mode behavior
  - non-rejected content handling
  - filename / metadata expectations where practical
- Extend frontend smoke coverage where practical if export labels/entry points change.
- Do not bypass, weaken, or remove existing checks.
- Treat automated testing as a merge gate.
- If some behavior cannot be fully validated end-to-end in the container, add the strongest practical automated coverage and clearly state what still requires manual smoke testing.
- In the final report, list:
  1. exact tests added/updated
  2. exact test/build/check commands run
  3. what still needs manual validation

Implementation requirements:
- prefer pragmatic improvements over a big export subsystem rewrite
- touch backend/frontend only where needed
- update docs for:
  - final notes export behavior
  - preferred-content usage in exports
  - any export mode distinctions
  - current limitations

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. how final notes export works
6. how finalized/reviewed content is selected in exports
7. any new export options or UX changes
8. exact tests added/updated
9. exact test/build/check commands run
10. what still needs manual validation
11. limitations and next steps

Success criteria:
- final exports feel more polished and shareable
- finalized/reviewed content is clearly preferred
- HTML and Markdown output quality improves materially
- export UX becomes clearer
- current app behavior outside export remains stable
- relevant pytest coverage is added/updated
- frontend build and smoke checks remain green
- cargo check remains green
- any remaining manual-only validation gaps are called out clearly
