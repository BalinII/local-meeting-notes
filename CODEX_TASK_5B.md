You are improving Phase 5 of Local Meeting Notes.

Real-world validation shows the current diarization output is not yet operationally useful.

Observed issues from real capture testing:
- diarization creates too many short fragmented speaker segments
- multiple speaker labels appear across tiny overlapping windows in the same short chunk
- confidence values are flat and not meaningful
- transcript alignment remains weak, with many transcript segments still labelled `Unknown`
- diarization technically runs, but speaker turns are not stable enough to support useful meeting notes

Your task:
Tune and harden diarization quality and transcript alignment.

Goals:
- reduce over-fragmentation of speaker turns
- improve stability of generic speaker labels across adjacent windows
- improve transcript-to-speaker alignment
- avoid assigning multiple conflicting speakers within tiny overlapping spans unless clearly justified
- keep labels generic only:
  - Speaker 1
  - Speaker 2
  - Speaker 3
- prefer fewer, more stable speaker turns over aggressive over-segmentation
- keep uncertainty explicit where alignment is weak

Constraints:
- do not implement participant identity mapping
- do not implement Microsoft auth
- do not build a Teams bot
- keep it local-first
- do not replace the whole architecture unless clearly necessary
- prefer targeted tuning and post-processing over a full rewrite

Implementation requirements:
- inspect and tune window sizing / hop length / segmentation parameters
- improve clustering logic and post-processing
- merge adjacent same-speaker segments where reasonable
- suppress obviously spurious micro-segments
- improve transcript overlap matching so speaker labels propagate more usefully to transcript segments
- if confidence is not meaningful, either improve it or make that explicit instead of emitting fake precision
- add tests for:
  - reduction of tiny fragmented segments
  - adjacent same-speaker merge behaviour
  - transcript label propagation
- update docs with practical limitations

Output required:
1. diagnosis of why the current diarization is too fragmented
2. files to change
3. code changes
4. how to retest on a real capture
5. remaining limitations