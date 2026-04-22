You are building Phase 6C of Local Meeting Notes.

Goal:
Add a local LLM-based summarization and extraction provider alongside the existing heuristic pipeline.

Business intent:
The current heuristic summarization and extraction pipeline works, but output quality is too literal and brittle for strong meeting notes. We want to improve readability and structured extraction quality by using a local LLM, while keeping the app fully local-first and preserving the current heuristic approach as a fallback.

Primary requirements:
- Add a new provider mode for summarization and extraction:
  - heuristic
  - local_llm
- Keep the current persistence boundaries and database schema unless a small extension is clearly justified
- Keep everything local-first
- Do not add cloud dependencies
- Do not implement participant identity mapping
- Do not implement Microsoft auth
- Do not build a Teams bot

Preferred local runtime:
- First choice: Ollama running locally on the same machine
- The implementation should be designed so another local OpenAI-compatible runtime could be swapped in later

Use cases for the local LLM:
- executive summary
- detailed summary
- decisions
- actions
- follow-ups
- blockers / risks
- open questions

Important behavioral rules:
- The model must not hallucinate facts not grounded in transcript evidence
- If ownership is unclear, use:
  - Unknown
  - Unconfirmed speaker
- If a decision or action is weakly supported, either:
  - omit it
  - or mark it uncertain
- Prefer grounded, conservative output over over-assertive output
- The system must preserve evidence snippets and timing references where practical

Architecture requirements:
- Add a provider boundary for local LLM summarization/extraction
- Use the existing transcript and diarization outputs as input
- Support strict structured output in JSON
- Validate and normalize model output before persisting it
- If the local LLM fails, times out, or returns invalid JSON, fall back cleanly to the heuristic provider
- Make the configured provider selectable from config or CLI

Preferred implementation approach:
- Use Ollama's local HTTP API
- Use a local instruct model suitable for summarization and structured extraction
- Start with a practical default model choice, but keep the model name configurable
- Build prompts that:
  - explicitly forbid hallucination
  - require evidence-based extraction
  - produce structured JSON only
- Include robust parsing, validation, and fallback behavior

Implementation details:
- Add configuration for:
  - summary provider
  - action extraction provider
  - local LLM base URL
  - model name
  - timeout
  - max transcript length or chunking behavior if needed
- Add or extend service files under:
  - summarizer
  - action_extractor
- Add a small local LLM client module if needed
- Keep the output schema aligned to current summary/action persistence as much as possible
- Where useful, store provider metadata such as:
  - provider name
  - model name
  - generation timestamp

CLI requirements:
- Existing summary and action commands should continue to work
- Add a way to select provider if practical, for example:
  - --provider heuristic
  - --provider local_llm
- Add a simple health/check command if useful, for example:
  - llm check
  to verify the local runtime is reachable

Testing requirements:
- Add tests for:
  - valid structured JSON parsing
  - invalid JSON fallback to heuristic
  - timeout/error fallback
  - persistence of local LLM outputs
  - realistic meeting-style transcript extraction
- Mock the local LLM API in tests; do not require a live Ollama instance for test execution

Docs requirements:
- Update README and local setup docs with:
  - how to install/run Ollama locally
  - what model to pull
  - how to configure the app
  - how to switch between heuristic and local_llm provider modes
  - known limitations

Output required:
1. plan
2. chosen implementation approach and why
3. files to change
4. code changes
5. setup instructions for Ollama
6. how to run summary/action extraction with local_llm
7. fallback behavior
8. limitations and next steps

Success criteria:
- I can run a local Ollama instance
- the app can call it locally
- summary and action extraction can run with provider=local_llm
- outputs are parsed as structured JSON
- invalid model output does not break the pipeline
- heuristic fallback still works