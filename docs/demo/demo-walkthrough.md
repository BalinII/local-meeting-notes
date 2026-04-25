# Demo Walkthrough (Local Meeting Notes)

This guide is designed for a **realistic internal demo** of the current prototype.

## Demo objective

Show an end-to-end local workflow:

1. start the app
2. create/load a capture
3. process transcript + diarization
4. generate summaries/extracted items
5. review/edit results
6. export outputs

## Pre-demo checklist (10-15 minutes before)

- Confirm Python venv activates successfully.
- Confirm backend package is installed (`pip install -e .\backend`).
- Confirm database bootstrap ran at least once.
- Confirm Node modules are installed in `app/`.
- If using local LLM path, confirm Ollama is running and model is available.
- Confirm audio input/output devices are visible on the demo machine.

Recommended quick checks:

```powershell
python -m local_meeting_notes.app init
python -m local_meeting_notes.app db bootstrap
python -m local_meeting_notes.app audio devices
python -m local_meeting_notes.app llm check
```

## Start the application

### Option A: Desktop-first demo (recommended)

```powershell
cd .\app
npm run tauri:dev
```

### Option B: Backend CLI-only prep

Use CLI to prep a capture and processed outputs before opening the desktop shell.

## Create or load a capture

### Create a fresh capture

```powershell
python -m local_meeting_notes.app session start --title "Q2 Planning Demo"
python -m local_meeting_notes.app audio start
```

Let audio run 1-3 minutes while you read the script below, then stop:

```powershell
python -m local_meeting_notes.app audio stop
python -m local_meeting_notes.app session stop
```

### Load an existing capture

If you already have a known-good `capture_id`, skip capture and continue with processing steps.

## Process capture (transcription, diarization, summary, extraction)

```powershell
python -m local_meeting_notes.app transcript transcribe --capture-id "<capture-id>"
python -m local_meeting_notes.app diarize run --capture-id "<capture-id>"
python -m local_meeting_notes.app summary generate --capture-id "<capture-id>"
python -m local_meeting_notes.app actions extract --capture-id "<capture-id>"
```

Optional explicit local LLM provider run:

```powershell
python -m local_meeting_notes.app summary generate --capture-id "<capture-id>" --provider local_llm
python -m local_meeting_notes.app actions extract --capture-id "<capture-id>" --provider local_llm
```

## Review / edit / export flow (what to click and narrate)

In the review UI:

1. enter `capture_id`
2. load generated outputs
3. open evidence snippets for at least one action/decision
4. accept one item as-is
5. edit one item for clarity
6. reject one weak item
7. export markdown (and optionally HTML/JSON)

CLI export equivalent:

```powershell
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format markdown
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format html
python -m local_meeting_notes.app export run --capture-id "<capture-id>" --format json
```

## Realistic demo meeting script (read aloud)

Use this short script while recording so extracted items are easier to validate:

- "Let's decide to ship the internal beta on May 20 if testing passes by May 15."
- "Alex will finalize the onboarding checklist by Friday."
- "Priya will validate export formatting and share results next Tuesday."
- "Open question: do we need a longer retention window for local exports?"
- "Risk: diarization quality may drop when two people overlap heavily."
- "Follow-up: review model choice after next week's real-meeting pilot."

## Honest callouts during demo (important)

Say these explicitly to set expectations:

- "This is a local prototype, not a production service."
- "Speaker labels are generic and can be imperfect."
- "Transcription quality varies by audio setup and overlap."
- "Local LLM output quality depends on model/runtime health."
- "When confidence is weak, the app preserves uncertainty instead of pretending certainty."

## Suggested 8-10 minute demo agenda

1. **1 min**: Product framing and local-first privacy stance.
2. **2 min**: Start/load capture and show transcript artifacts exist.
3. **2 min**: Generate summary + extraction.
4. **2 min**: Review/edit/accept/reject with evidence snippets.
5. **1 min**: Export markdown/html/json.
6. **1-2 min**: Known limitations and next priorities.

## If something fails during demo

- Use a pre-recorded known-good capture ID.
- Run heuristic provider explicitly if local LLM is unstable.
- Show existing exported markdown/json artifacts from a prior run.
- Use troubleshooting guide: [`../troubleshooting.md`](../troubleshooting.md).
