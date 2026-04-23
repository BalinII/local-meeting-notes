You are improving Phase 6C of Local Meeting Notes.

Real-world validation shows the local LLM integration is working, but output quality is still not strong enough for polished meeting notes.

Observed issues:
- ASR noise leaks into summaries and extracted decisions/actions
- some rewritten decisions are directionally right but factually off
- some follow-ups and risks are still garbled
- ownership remains appropriately cautious, but output wording needs cleanup
- local_llm is better than heuristic, but not yet trustworthy enough for clean internal notes without review

Your task:
Improve output quality for the local LLM summarization and extraction pipeline.

Goals:
- reduce ASR-noise leakage into summaries, decisions, actions, and follow-ups
- improve transcript cleaning before LLM prompting
- tighten prompts so the model drops weak/garbled items instead of rewriting them badly
- improve normalization of valid actions and decisions into cleaner meeting-note language
- preserve grounding in transcript evidence
- keep uncertainty explicit when evidence is weak

Constraints:
- keep everything local-first
- do not implement participant identity mapping
- do not implement Microsoft auth
- do not build a Teams bot
- do not remove heuristic fallback
- do not replace Ollama integration
- prefer practical transcript cleaning, prompt tuning, and output filtering over major rewrites

Implementation requirements:
- add a transcript-cleaning / normalization step before sending content to local_llm
- filter obvious ASR garbage and malformed fragments before prompt construction
- refine prompts for:
  - executive summary
  - detailed summary
  - decisions
  - actions
  - follow-ups
  - blockers / risks
  - open questions
- explicitly instruct the model to omit unclear items rather than force a rewrite
- improve post-processing and validation of model outputs
- keep evidence snippets and timestamps where practical
- add tests for:
  - ASR-noise suppression
  - malformed decision suppression
  - cleaner normalization of meeting-style transcript input
  - robust fallback when model output is weak

Output required:
1. diagnosis of the current quality issues
2. files to change
3. code changes
4. how to retest on a real capture
5. remaining limitations