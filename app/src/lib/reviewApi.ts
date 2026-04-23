export type SummaryOutput = {
  title: string;
  summary_type: string;
  content: string;
  evidence_snippet?: string | null;
  provider_name?: string | null;
  model_name?: string | null;
  generated_at?: string | null;
};

export type ExtractedOutput = {
  description: string;
  owner_name?: string | null;
  status?: string | null;
  follow_up_type?: string | null;
  evidence_snippet?: string | null;
  start_offset_seconds?: number | null;
  end_offset_seconds?: number | null;
  provider_name?: string | null;
  model_name?: string | null;
  generated_at?: string | null;
};

export type ReviewPayload = {
  capture_id: string;
  exported_at: string;
  metadata: {
    providers: string[];
    latest_generated_at?: string | null;
    summary_count: number;
    action_count: number;
    decision_count: number;
    follow_up_count: number;
  };
  summaries: SummaryOutput[];
  actions: ExtractedOutput[];
  decisions: ExtractedOutput[];
  follow_ups: ExtractedOutput[];
  blockers_risks: ExtractedOutput[];
  open_questions: ExtractedOutput[];
};

type TauriGlobal = {
  core?: {
    invoke: <T>(command: string, args?: Record<string, unknown>) => Promise<T>;
  };
};

declare global {
  interface Window {
    __TAURI__?: TauriGlobal;
  }
}

export async function loadReviewPayload(captureId: string): Promise<ReviewPayload> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) {
    return demoPayload(captureId);
  }
  return invoke<ReviewPayload>("review_capture", { captureId });
}

export async function exportReview(captureId: string, format: "markdown" | "html" | "json") {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) {
    return `Demo mode: export ${format} for ${captureId}`;
  }
  return invoke<string>("export_capture", { captureId, format });
}

function demoPayload(captureId: string): ReviewPayload {
  return {
    capture_id: captureId || "demo-capture",
    exported_at: new Date().toISOString(),
    metadata: {
      providers: ["local_llm"],
      latest_generated_at: new Date().toISOString(),
      summary_count: 2,
      action_count: 1,
      decision_count: 1,
      follow_up_count: 2,
    },
    summaries: [
      {
        title: "Executive Summary",
        summary_type: "executive",
        content: "The team aligned on a local-first meeting notes workflow and identified review/export as the next usability milestone.",
        evidence_snippet: "Decision: keep the prototype local-first and add clean export paths.",
        provider_name: "local_llm",
        model_name: "llama3.1:8b",
      },
      {
        title: "Detailed Summary",
        summary_type: "detailed",
        content: "Discussion focused on making persisted summaries, decisions, and follow-ups easier to review before sharing internally.",
        evidence_snippet: "Action item: prepare a review screen and export options.",
        provider_name: "local_llm",
        model_name: "llama3.1:8b",
      },
    ],
    actions: [
      {
        description: "Prepare a review screen for persisted meeting-note outputs.",
        owner_name: "Unconfirmed speaker",
        evidence_snippet: "Action item: prepare a review screen.",
        provider_name: "local_llm",
      },
    ],
    decisions: [
      {
        description: "Keep export and review local-first.",
        evidence_snippet: "Decision: keep export and review local-first.",
        provider_name: "local_llm",
      },
    ],
    follow_ups: [],
    blockers_risks: [
      {
        description: "Extraction quality still needs review before sharing notes.",
        owner_name: "Unknown",
        evidence_snippet: "Risk: extracted items may need manual review.",
        provider_name: "local_llm",
      },
    ],
    open_questions: [
      {
        description: "Which export format should be the default for internal sharing?",
        owner_name: "Unconfirmed speaker",
        evidence_snippet: "Open question: what should the default export be?",
        provider_name: "local_llm",
      },
    ],
  };
}
