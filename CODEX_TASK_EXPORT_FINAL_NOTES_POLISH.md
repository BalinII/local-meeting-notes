Read AGENTS.md first and follow it.

You are building the next major product-readiness phase for Local Meeting Notes.

Goal:
Make exports and finalized notes feel substantially more production-ready, polished, and shareable without redesigning the app or changing core local-first architecture.

Current state:
- recording workflow exists
- review/edit/export workflow exists
- finalisation/preferred-content behavior exists
- session library, search, actions, and memory exist
- outputs are usable, but still feel too much like internal/generated artifacts rather than polished final meeting notes

Business intent:
The app should now produce cleaner, more trustworthy final notes that are suitable for internal sharing and daily use. This phase should improve the last-mile quality of the product.

Primary requirements:

1. Final notes export mode
- introduce a cleaner “final notes” export path or mode
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
- better handling of empty sections
- better readability and printability for HTML
- better pasteability for Markdown

3. Finalised session behavior
- finalized sessions should clearly export the best available version of content
- reviewed/final content should be preferred consistently
- generated/raw content should be secondary and only included when appropriate

4. Export choices
If low risk and practical, support a clearer distinction such as:
- Final Notes
- Full Detail / Audit View

Keep this lightweight and avoid overbuilding.

5. Share-readiness
Make the exported output feel suitable for:
- internal team sharing
- project follow-up
- meeting outcome tracking
without looking like a prototype dump

6. Optional low-risk UX improvements
If practical and low risk:
- copy final notes to clipboard
- cleaner export file names
- improved export button labels/copy
- better confirmation after export

Constraints:
- keep everything local-first
- do not redesign the whole app
- do not implement Outlook integration
- do not implement Microsoft auth
- do not build a Teams bot
- preserve current recording/review/library/search/actions/memory behavior
- do not remove auditability entirely; keep it available where useful

Implementation requirements:
- prefer pragmatic improvements over a big export subsystem rewrite
- touch backend/frontend only where needed
- add focused regression tests where practical
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
8. tests run
9. limitations and next steps

Success criteria:
- final exports feel more polished and shareable
- finalized/reviewed content is clearly preferred
- HTML and Markdown output quality improves materially
- export UX becomes clearer
- app behavior outside export remains stable
- npm run build passes
- cargo check passes
- relevant tests pass or limitations are stated clearly