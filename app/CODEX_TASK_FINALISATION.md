Read AGENTS.md first and follow it.

You are building the next major product phase for Local Meeting Notes.

Goal:
Improve trust and usefulness across the app by introducing a stronger finalisation workflow and making reviewed/final content the default across global views, search, and exports.

Current state:
- recording workflow exists
- review/edit/export workflow exists
- session library exists
- cross-session search exists
- global action tracker exists
- memory views exist
- global content can still be noisy because generated/raw items are often shown alongside or ahead of better reviewed content

Business intent:
Now that cross-session memory and action tracking exist, the app must prefer the best available version of information. Users should mostly see final/reviewed content, not rough generated drafts, unless they explicitly choose otherwise.

Primary requirements:

1. Stronger content state model
- clarify and consistently use content states such as:
  - generated
  - reviewed
  - final
- make the state visible where useful but not noisy
- preserve the original generated content for auditability/traceability

2. Finalisation workflow
- add a clear session-level “Finalize notes” workflow
- a finalized session should mean:
  - user has reviewed the session enough to treat it as the preferred version
  - exports and global views should prefer final content from that session
- keep this lightweight and local-first
- do not require heavy approvals or enterprise workflow complexity

3. Prefer reviewed/final content everywhere
Update the app so that the following prefer:
- final content first
- then reviewed content
- then generated content only if nothing better exists

Apply this preference to:
- session library summary previews if relevant
- cross-session search results
- global action tracker
- decisions / blockers / open questions memory views
- exports (Markdown / HTML / JSON)
- any summary snippets shown outside the main per-session review page

4. Filtering and visibility controls
Add lightweight filters/toggles where useful, for example:
- Final only
- Reviewed + Final
- All content

These should help users reduce noise without redesigning the app.

5. Search/result relevance
Improve search result preference/ranking so:
- final matches rank above reviewed matches
- reviewed matches rank above generated matches
- noisy/generated content does not dominate if a better reviewed/final version exists
- preserve traceability to source session

6. Action/memory quality hygiene
For global Actions and Memory views:
- prefer reviewed/final content when available
- reduce duplicate/noisy entries where multiple versions of the same item exist
- keep source session visible
- preserve ability to inspect provenance if needed

Constraints:
- keep everything local-first
- do not redesign the whole app
- do not implement Outlook integration
- do not implement Microsoft auth
- do not build a Teams bot
- preserve the current recording / review / export flow
- preserve auditability and source traceability
- do not remove access to generated/raw content entirely; make it secondary

Implementation requirements:
- extend persistence conservatively only if needed
- prefer pragmatic changes over a large rewrite
- add/update backend queries/services to support preferred content selection
- update Tauri/frontend wiring where needed
- add focused tests where practical
- update docs to explain:
  - generated vs reviewed vs final
  - finalisation workflow
  - how global views choose preferred content
  - how exports choose preferred content

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. how finalisation works
6. how preferred-content selection works across the app
7. how filters/toggles work
8. tests run
9. limitations and next steps

Success criteria:
- users can finalize a session clearly
- global views prefer final/reviewed content by default
- search results prefer better content over raw/generated content
- exports prefer final/reviewed content where available
- noisy generated content is less dominant in global views
- review/export/recording workflows still work
- npm run build passes
- cargo check passes
- relevant tests pass or limitations are stated clearly