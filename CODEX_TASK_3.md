You are building Phase 3 of Local Meeting Notes.

Implement the first real MVP capability: local audio capture on Windows.

Goals:
- add a Windows-oriented audio capture service
- support manual start and stop of capture
- support:
  - system audio loopback capture
  - microphone capture
- write timestamped audio chunks locally into backend/data/audio
- add basic device enumeration
- add clear logging around selected devices, start, stop, and failures
- integrate with the existing CLI so I can manually trigger capture

Constraints:
- do not implement Teams bot behaviour
- do not join meetings
- do not implement real transcription yet
- do not implement Microsoft Graph auth yet
- keep it local-first
- be explicit where Windows audio capture is fragile
- prefer the fastest viable MVP approach over an abstract design

Implementation requirements:
- choose concrete Python libraries for Windows audio capture and justify them
- create a service boundary that can later feed transcription
- handle chunked recording with timestamps
- create placeholder metadata records if needed
- add tests where practical, but do not fake full audio hardware integration
- document setup requirements clearly in README or docs

Output required:
1. plan
2. chosen libraries and why
3. files to change
4. code changes
5. how to run manual capture
6. limitations and next steps