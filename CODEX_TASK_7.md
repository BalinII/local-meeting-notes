You are building Phase 7 of Local Meeting Notes.

Goal:
Make the current meeting-note outputs usable through export and a basic review experience, without changing the core backend architecture.

Current state:
- local audio capture works
- transcription works
- diarization works at a basic prototype level
- summary generation works
- action extraction works
- local_llm improves summaries, while slower extraction may still fall back to heuristic
- outputs are persisted in SQLite

Business intent:
We now need a practical way to review and export results so the product becomes usable as an internal prototype.

Primary requirements:
- improve output usability and presentation
- add clean export options for:
  - markdown
  - HTML
  - JSON
- create a basic review workflow in the desktop app shell
- display:
  - executive summary
  - detailed summary
  - actions
  - decisions
  - follow-ups
  - blockers / risks
  - open questions
  - evidence snippets where available
- keep everything local-first

Constraints:
- do not implement participant identity mapping
- do not implement Microsoft auth
- do not build a Teams bot
- do not redesign the whole app
- do not overbuild the UI
- work with the current backend outputs and persistence model
- assume diarization and extraction quality are still imperfect and design the UI accordingly

UX intent:
Build a clean, lightweight review experience consistent with a modern desktop productivity tool:
- simple
- structured
- readable
- low clutter
- obvious separation between summary and extracted items
- easy export actions
- clearly show uncertainty where ownership or meaning is weak

Implementation requirements:
- add or improve export service support for:
  - markdown
  - HTML
  - JSON
- ensure exports include:
  - capture id
  - provider metadata
  - generated timestamp where available
  - summary sections
  - extracted actions/decisions/follow-ups
  - evidence snippets where available
- add a basic review screen in the Tauri frontend that can:
  - load a capture by id
  - display summary outputs
  - display extracted items
  - display evidence snippets
  - expose export buttons/actions
- if useful, add a simple “quality/uncertainty” treatment in the UI:
  - Unknown
  - Unconfirmed speaker
  - weak evidence
- keep the UI implementation pragmatic and minimal
- do not overfocus on styling beyond a clean and professional baseline

Suggested UI structure:
- header with capture id and generation metadata
- summary panel:
  - executive summary
  - detailed summary
- extracted items panel:
  - actions
  - decisions
  - follow-ups
  - blockers / risks
  - open questions
- evidence drawer or expandable evidence lines
- export controls:
  - export markdown
  - export html
  - export json
- optional provider badge:
  - heuristic
  - local_llm

Technical requirements:
- wire the frontend to the current backend outputs with the least disruptive path
- prefer a small, maintainable API bridge between Tauri frontend and backend
- keep data fetching and rendering simple
- avoid introducing heavy frontend state complexity unless necessary
- preserve the current CLI/export paths if they exist

Testing requirements:
- add tests where practical for:
  - export payload structure
  - markdown/html/json output generation
  - basic review data loading
- do not overinvest in frontend test infrastructure if it slows the phase down too much

Docs requirements:
- update README and setup docs
- explain how to review a capture
- explain how to export results
- explain current limitations of speaker labels and extraction quality

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. how to review outputs in the app
6. how to export markdown/html/json
7. limitations and next steps

Success criteria:
- I can open a capture result in the app
- I can read the summary and extracted items clearly
- I can export results to markdown, html, and json
- uncertainty is visible rather than hidden
- the feature works with the current backend without requiring backend redesign