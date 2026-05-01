export type RecordingConfidence = {
  label: string;
  headline: string;
  detail: string;
  tone: "neutral" | "active" | "waiting" | "ready" | "error";
  active: boolean;
};

export function recordingConfidenceForState(
  lifecycleState: string | null | undefined,
  lastError?: string | null,
): RecordingConfidence {
  const state = (lifecycleState || "draft").trim();
  if (lastError || state === "processing_failed") {
    return {
      label: "Needs attention",
      headline: "Recording or processing needs attention",
      detail: lastError || "Processing did not finish. Check the session error and retry with a known-good capture if needed.",
      tone: "error",
      active: false,
    };
  }
  if (state === "starting") {
    return {
      label: "Starting",
      headline: "Opening the local microphone capture",
      detail: "The app is creating the session and starting the microphone stream.",
      tone: "waiting",
      active: true,
    };
  }
  if (state === "recording") {
    return {
      label: "Recording active",
      headline: "Microphone recording is active",
      detail: "Audio chunks are being written locally. Keep this window open while the meeting is running.",
      tone: "active",
      active: true,
    };
  }
  if (state === "pausing") {
    return {
      label: "Pausing",
      headline: "Pausing after the current chunk closes",
      detail: "Pause is cooperative, so the app may wait briefly for the active audio chunk to finish writing.",
      tone: "waiting",
      active: true,
    };
  }
  if (state === "paused") {
    return {
      label: "Paused",
      headline: "Recording is paused",
      detail: "No new audio is being captured. Resume when the meeting continues, or stop and process the saved chunks.",
      tone: "neutral",
      active: false,
    };
  }
  if (state === "resuming") {
    return {
      label: "Resuming",
      headline: "Reopening the local microphone capture",
      detail: "The app is reconnecting to the microphone and will show recording once capture is active.",
      tone: "waiting",
      active: true,
    };
  }
  if (state === "stopping") {
    return {
      label: "Stopping",
      headline: "Closing the current chunk before processing",
      detail: "The app is stopping capture cooperatively, then will process the saved audio locally.",
      tone: "waiting",
      active: true,
    };
  }
  if (state === "processing") {
    return {
      label: "Processing locally",
      headline: "Processing saved audio on this machine",
      detail: "Transcription, diarization, summaries, and extraction can take a little while. The app has not joined the meeting or sent audio to a cloud service.",
      tone: "waiting",
      active: false,
    };
  }
  if (state === "review_ready" || state === "reviewed" || state === "final" || state === "exported") {
    return {
      label: "Ready for review",
      headline: "Notes are ready to review",
      detail: "Open the session to review summaries, extracted outcomes, and exports.",
      tone: "ready",
      active: false,
    };
  }
  return {
    label: "Ready",
    headline: "Ready to start microphone recording",
    detail: "Microphone-only is the supported default path. System audio remains constrained and is not used for this desktop flow.",
    tone: "neutral",
    active: false,
  };
}
