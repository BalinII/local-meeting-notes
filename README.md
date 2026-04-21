# Local Meeting Notes

Local-first Windows desktop application for capturing meeting audio, generating transcripts, diarizing speakers, and producing summaries, actions, and follow-ups without joining the meeting as a bot.

## MVP Goal

Build a private desktop app that:
- runs locally on Windows
- captures system audio and microphone input
- transcribes meetings
- separates speakers
- generates summary notes, actions, decisions, and follow-ups
- stores everything locally first

## Initial Tech Direction

- Frontend/Desktop shell: Tauri
- Backend pipeline: Python
- Database: SQLite
- Meeting metadata: Microsoft Graph
- Audio capture: Windows loopback + mic capture

## Non-goals for MVP

- No Teams bot
- No visible joining of meetings
- No assumption of perfect speaker identity attribution
- No polished enterprise-grade UI in phase 1

## Top Risks

- Reliable Windows system audio capture
- Speaker diarization quality
- Accurate speaker-to-person attribution
- Microsoft auth and meeting detection edge cases