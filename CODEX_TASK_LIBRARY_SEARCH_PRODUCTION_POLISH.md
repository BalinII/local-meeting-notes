Read AGENTS.md first and follow it.

You are building the next product-readiness phase for Local Meeting Notes.

Goal:
Make the Session Library and Search experience feel more production-ready, cleaner, and more dependable for everyday use without redesigning the app or changing the local-first architecture.

Current state:
- session library exists
- cross-session search exists
- global actions and memory views exist
- preferred/final content behavior exists
- recording/review/export flows exist
- the product is now broadly usable, but the library/search experience still has prototype-level roughness:
  - session library hierarchy can be stronger
  - search quality and result presentation can be cleaner
  - duplication/noise can still reduce trust
  - browsing/opening sessions should feel more deliberate and polished

Business intent:
Users should be able to confidently browse, find, and reopen useful content from past meetings without the app feeling like a rough internal tool.

Primary requirements:

1. Session library polish
Make the library feel like a real session browser.

Focus on:
- display name primary, capture ID secondary
- stronger session card hierarchy
- cleaner metadata presentation:
  - date/time
  - lifecycle state
  - reviewed/final/exported status
  - provider/model only if useful and not noisy
- clearer selected/open session state
- clearer affordance to open a session
- stronger empty/loading/no-session states

2. Library filters and sorting
Refine and polish the existing controls so they feel production-ready.

Support and improve behavior for:
- newest first
- oldest first
- review-ready
- finalised
- exported
- needs attention / failed if relevant

Make sure controls are understandable and the resulting list changes are obvious.

3. Search result quality
Improve search output quality without introducing a new search engine.

Focus on:
- reduce duplicate or near-duplicate matches from the same session
- prefer better content where useful:
  - final > reviewed > generated
- improve grouping by session/content type
- make snippets cleaner, more readable, and less noisy
- avoid poor-quality matches dominating the result set
- keep results traceable to source sessions

4. Search result interaction
Make search results more clearly actionable.

Focus on:
- stronger “Open Session” interaction
- clicking a result or result card should feel intentional
- current/open session feedback after navigation
- better no-results and loading states
- visible result counts and scope explanation where useful

5. Search scopes/filters polish
Refine the existing scope controls:
- all
- sessions
- summaries
- actions
- decisions
- blockers / risks
- open questions

Make sure the scopes are understandable, behave clearly, and improve result trust.

6. Consistency across Library / Search / Actions / Memory
Improve consistency of:
- badges
- metadata language
- open-session actions
- content-state visibility
- hierarchy and spacing

Do this without redesigning the whole app.

7. Optional low-risk refinements
If practical and low-risk:
- clearer session-preview snippets in the library
- stronger visual treatment for finalised sessions
- slight improvement to match highlighting
- better “what matched” labeling

Constraints:
- keep everything local-first
- do not redesign the whole app
- do not implement Outlook integration
- do not implement Microsoft auth
- do not build a Teams bot
- preserve recording / review / export behavior
- do not add a new search engine or vector search system

Implementation requirements:
- prefer pragmatic UX and query improvements over architectural changes
- extend backend/frontend only where needed
- add focused regression tests where practical
- update docs for:
  - session library behavior
  - sorting/filter behavior
  - search scopes and limitations
  - how preferred/final content affects search and browsing

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. how session library works after polish
6. how search works after polish
7. filters/sorts/scopes changes
8. tests run
9. limitations and next steps

Success criteria:
- session library feels materially clearer and more polished
- search results are cleaner and more trustworthy
- duplicate/noisy matches are reduced
- opening sessions from library/search feels more intentional
- consistency across library/search/actions/memory improves
- npm run build passes
- cargo check passes
- relevant tests pass or limitations are stated clearly