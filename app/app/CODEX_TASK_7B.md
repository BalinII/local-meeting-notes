You are improving Phase 7 of Local Meeting Notes.

Observed issue from real UI validation:
- the review screen is working
- exports are working
- however, the app is rendering multiple separate "Detailed Summary" cards
- this makes the review experience feel fragmented and harder to scan
- the product should present one coherent executive summary and one coherent detailed summary, followed by structured extracted sections

Your task:
Improve review presentation and summary consolidation.

Goals:
- present exactly one Executive Summary section where available
- present exactly one Detailed Summary section where available
- avoid rendering multiple fragmented detailed summary cards unless there is a strong product reason
- consolidate multiple persisted detailed summary rows into one readable review section
- keep extracted sections separate:
  - Actions
  - Decisions
  - Follow-ups
  - Risks / blockers
  - Open questions
- preserve provider metadata and evidence access
- keep the UI clean and easy to scan

Constraints:
- do not redesign the whole app
- do not change the core capture/transcription/diarization architecture
- do not implement participant identity mapping
- do not implement Microsoft auth
- do not build a Teams bot
- prefer a pragmatic fix that works with the current persistence model

Implementation guidance:
- decide whether consolidation should happen:
  - in backend review payload generation
  - or in frontend presentation
- prefer backend consolidation if it also improves export consistency
- if multiple detailed summary rows exist, combine them into one coherent detailed summary block in a sensible order
- avoid duplicate headings
- preserve evidence snippets and provider/model metadata where practical
- keep uncertainty visible where relevant

Output required:
1. diagnosis of why multiple detailed summaries are appearing
2. chosen fix and why
3. files to change
4. code changes
5. how to retest in the UI
6. limitations and next steps