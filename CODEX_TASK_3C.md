You are debugging the Windows loopback audio capture path in Local Meeting Notes.

Observed behaviour from real local testing:
- microphone-only capture works
- microphone-only status becomes `running`
- microphone-only writes `.wav` files correctly
- loopback-only capture does NOT work
- loopback-only remains stuck at `starting`
- loopback-only writes no `.wav` files
- logs show loopback device selection but no successful transition to recording and no first chunk write

Conclusion:
- the bug is isolated to the system loopback capture path
- the microphone path and file writing path are already proven to work

Your task:
Debug and harden the loopback capture startup path only.

Goals:
- make loopback capture either:
  - transition to `running` and write chunk files
  - or transition to `failed` with a clear reason
- add detailed logging around:
  - selected loopback device
  - loopback stream open attempt
  - first frame read
  - first chunk write
  - startup timeout
  - exception details
- prevent the capture state from getting stuck at `starting`
- improve `audio status` so it shows a failure reason when loopback startup fails
- add targeted tests for loopback startup failure handling

Constraints:
- do not touch transcription
- do not implement Microsoft auth
- do not build a Teams bot
- do not redesign unrelated parts of the app
- keep the current architecture unless there is a compelling reason to change it
- if the current loopback library/API usage is incorrect for Windows, fix that directly and explain why

Implementation requirements:
- inspect how the soundcard library is being used for loopback capture
- verify the correct use of default speaker / loopback device APIs on Windows
- add startup timeout/failure handling
- ensure state transitions are explicit: starting -> running / failed / stopped
- document Windows-specific limitations and likely causes if loopback still fails on some devices

Output required:
1. diagnosis of the likely root cause
2. exact files to change
3. code changes
4. how to retest loopback-only
5. remaining limitations