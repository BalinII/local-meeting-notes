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
  id: number;
  item_type: "action" | "decision" | "follow_up";
  description: string;
  effective_description?: string | null;
  owner_name?: string | null;
  effective_owner_name?: string | null;
  status?: string | null;
  follow_up_type?: string | null;
  review_status?: "generated" | "accepted" | "edited" | "rejected";
  reviewed_description?: string | null;
  reviewed_owner_name?: string | null;
  reviewed_at?: string | null;
  is_rejected?: boolean;
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

export type RecentCapture = {
  capture_id: string;
  created_at?: string | null;
  latest_generated_at?: string | null;
  latest_reviewed_at?: string | null;
  providers: string[];
  models: string[];
  has_reviewed_items: boolean;
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

export async function listRecentCaptures(limit = 12): Promise<RecentCapture[]> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) {
    return demoRecentCaptures();
  }
  return invoke<RecentCapture[]>("list_recent_captures", { limit });
}

export async function exportReview(captureId: string, format: "markdown" | "html" | "json") {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) {
    return `Demo mode: export ${format} for ${captureId}`;
  }
  return invoke<string>("export_capture", { captureId, format });
}

export async function saveReviewItem(input: {
  itemType: ExtractedOutput["item_type"];
  itemId: number;
  reviewStatus: NonNullable<ExtractedOutput["review_status"]>;
  description?: string | null;
  ownerName?: string | null;
}): Promise<ExtractedOutput> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) {
    return {
      id: input.itemId,
      item_type: input.itemType,
      description: input.description || "Demo reviewed item",
      effective_description: input.description || "Demo reviewed item",
      owner_name: input.ownerName,
      effective_owner_name: input.ownerName,
      review_status: input.reviewStatus,
      reviewed_description: input.reviewStatus === "edited" ? input.description : null,
      reviewed_owner_name: input.reviewStatus === "edited" ? input.ownerName : null,
      reviewed_at: new Date().toISOString(),
      is_rejected: input.reviewStatus === "rejected",
      provider_name: "demo",
    };
  }
  return invoke<ExtractedOutput>("save_review_item", input);
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
        id: 1,
        item_type: "action",
        description: "Prepare a review screen for persisted meeting-note outputs.",
        effective_description: "Prepare a review screen for persisted meeting-note outputs.",
        owner_name: "Unconfirmed speaker",
        effective_owner_name: "Unconfirmed speaker",
        review_status: "generated",
        evidence_snippet: "Action item: prepare a review screen.",
        provider_name: "local_llm",
      },
    ],
    decisions: [
      {
        id: 2,
        item_type: "decision",
        description: "Keep export and review local-first.",
        effective_description: "Keep export and review local-first.",
        review_status: "accepted",
        evidence_snippet: "Decision: keep export and review local-first.",
        provider_name: "local_llm",
      },
    ],
    follow_ups: [],
    blockers_risks: [
      {
        id: 3,
        item_type: "follow_up",
        description: "Extraction quality still needs review before sharing notes.",
        effective_description: "Extraction quality still needs review before sharing notes.",
        owner_name: "Unknown",
        effective_owner_name: "Unknown",
        review_status: "generated",
        evidence_snippet: "Risk: extracted items may need manual review.",
        provider_name: "local_llm",
      },
    ],
    open_questions: [
      {
        id: 4,
        item_type: "follow_up",
        description: "Which export format should be the default for internal sharing?",
        effective_description: "Which export format should be the default for internal sharing?",
        owner_name: "Unconfirmed speaker",
        effective_owner_name: "Unconfirmed speaker",
        review_status: "generated",
        evidence_snippet: "Open question: what should the default export be?",
        provider_name: "local_llm",
      },
    ],
  };
}

function demoRecentCaptures(): RecentCapture[] {
  return [
    {
      capture_id: "capture-demo-002",
      created_at: "2026-04-24T16:00:00+00:00",
      latest_generated_at: "2026-04-24T16:08:00+00:00",
      latest_reviewed_at: "2026-04-24T16:10:00+00:00",
      providers: ["local_llm"],
      models: ["llama3.1:8b"],
      has_reviewed_items: true,
    },
    {
      capture_id: "capture-demo-001",
      created_at: "2026-04-23T11:00:00+00:00",
      latest_generated_at: "2026-04-23T11:04:00+00:00",
      latest_reviewed_at: null,
      providers: ["heuristic"],
      models: [],
      has_reviewed_items: false,
    },
  ];
}
