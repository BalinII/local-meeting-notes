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
    display_name?: string | null;
    providers: string[];
    latest_generated_at?: string | null;
    summary_count: number;
    persisted_summary_count?: number;
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
  display_name?: string | null;
  created_at?: string | null;
  latest_generated_at?: string | null;
  latest_reviewed_at?: string | null;
  providers: string[];
  models: string[];
  has_reviewed_items: boolean;
};

export type SessionLibraryEntry = {
  capture_id: string;
  display_name: string;
  lifecycle_state: string;
  created_at?: string | null;
  updated_at?: string | null;
  reviewed_at?: string | null;
  exported_at?: string | null;
  reviewed_items_exist?: boolean;
  providers: string[];
  models: string[];
  last_error?: string | null;
};

export type SessionOverview = SessionLibraryEntry & {
  id?: number;
  started_at?: string | null;
  ended_at?: string | null;
  recorded_seconds?: number;
  latest_provider_name?: string | null;
  latest_model_name?: string | null;
  last_error?: string | null;
  session_type?: "ad_hoc" | "planned";
  planned_start_at?: string | null;
  planning_notes?: string | null;
  source_type?: "ad_hoc" | "planned" | "calendar_imported";
  external_meeting_id?: string | null;
  imported_title?: string | null;
  active_capture?: {
    capture_id?: string | null;
    status?: string | null;
    last_error?: string | null;
  } | null;
};
export type CalendarStatus = {
  available: boolean;
  provider?: string | null;
  message: string;
};

export type SearchMatch = {
  item_type: string;
  field_name: string;
  snippet: string;
  rank_weight?: number | null;
};

export type SearchSessionGroup = {
  capture_id: string;
  display_name: string;
  lifecycle_state?: string | null;
  match_count?: number;
  matches: SearchMatch[];
};

export type LibrarySort = "newest" | "oldest";
export type LibraryFilter = "all" | "review-ready" | "finalised" | "exported" | "needs-attention";
export type SearchScope = "all" | "sessions" | "summaries" | "actions" | "decisions" | "blockers-risks" | "open-questions";
export type ActionWorkflowFilter = "active" | "all" | "open" | "done" | "carried-forward" | "dismissed" | "overdue" | "due-soon";
export type ActionWorkflowSort = "recent" | "oldest" | "owner" | "session";

export type ActionTrackerItem = {
  id: number;
  item_type: string;
  capture_id: string;
  source_display_name: string;
  effective_description: string;
  effective_owner_name?: string | null;
  review_status: string;
  workflow_state: "open" | "done" | "dismissed" | "carried_forward";
  reviewed_at?: string | null;
  last_updated_at?: string | null;
  due_at?: string | null;
  notes?: string | null;
  carry_source_capture_id?: string | null;
  carry_count?: number;
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
    return [
      {
        capture_id: "capture-demo-001",
        display_name: "Demo Capture",
        created_at: new Date().toISOString(),
        latest_generated_at: new Date().toISOString(),
        latest_reviewed_at: null,
        providers: ["local_llm"],
        models: ["llama3.1:8b"],
        has_reviewed_items: true,
      },
    ];
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

export async function listSessionLibrary(sort: LibrarySort = "newest", filter: LibraryFilter = "all"): Promise<SessionLibraryEntry[]> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) return [];
  const payload = await invoke<{ sessions: SessionLibraryEntry[] }>("session_library", { sort, filter });
  return payload.sessions || [];
}

export async function createRecordingSession(title?: string | null): Promise<SessionOverview> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new Error("New Recording is available in Tauri desktop mode.");
  return invoke<SessionOverview>("create_session", { title: title?.trim() || null });
}
export async function createPlannedSession(input: { title: string; plannedStartAt?: string | null; notes?: string | null }): Promise<SessionOverview> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new Error("Planned sessions are available in Tauri desktop mode.");
  return invoke<SessionOverview>("create_planned_session", input);
}
export async function listPlannedSessions(limit = 20): Promise<SessionOverview[]> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) return [];
  const payload = await invoke<{ sessions: SessionOverview[] }>("list_planned_sessions", { limit });
  return payload.sessions || [];
}
export async function listUpcomingSessions(limit = 20): Promise<{ sessions: SessionOverview[]; calendar_status?: CalendarStatus }> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) return { sessions: [] };
  const payload = await invoke<{ sessions: SessionOverview[]; calendar_status?: CalendarStatus }>("list_upcoming_sessions", { limit });
  return { sessions: payload.sessions || [], calendar_status: payload.calendar_status };
}
export async function createSessionFromUpcoming(input: { title: string; plannedStartAt?: string | null; externalMeetingId?: string | null }): Promise<SessionOverview> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new Error("Upcoming-meeting session creation is available in Tauri desktop mode.");
  return invoke<SessionOverview>("create_session_from_upcoming", input);
}

export async function startRecordingSession(captureId: string): Promise<SessionOverview> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new Error("Recording is available in Tauri desktop mode.");
  return invoke<SessionOverview>("start_session", {
    captureId,
    includeLoopback: false,
    includeMicrophone: true,
  });
}

export async function pauseRecordingSession(captureId: string): Promise<SessionOverview> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new Error("Recording is available in Tauri desktop mode.");
  return invoke<SessionOverview>("pause_session", { captureId });
}

export async function resumeRecordingSession(captureId: string): Promise<SessionOverview> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new Error("Recording is available in Tauri desktop mode.");
  return invoke<SessionOverview>("resume_session", {
    captureId,
    includeLoopback: false,
    includeMicrophone: true,
  });
}

export async function stopRecordingSession(captureId: string): Promise<SessionOverview> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) throw new Error("Recording is available in Tauri desktop mode.");
  return invoke<SessionOverview>("stop_session", { captureId });
}

export async function searchAcrossSessions(query: string, scope: SearchScope = "all"): Promise<{ query: string; scope?: string; total_matches: number; raw_matches?: number; sessions: SearchSessionGroup[] }> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) return { query, total_matches: 0, sessions: [] };
  return invoke("session_search", { query: query.trim(), scope, limit: 120 });
}

export async function finaliseCapture(captureId: string): Promise<void> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) return;
  await invoke("finalise_session", { captureId });
}

export async function listGlobalActions(filter: ActionWorkflowFilter = "active", sort: ActionWorkflowSort = "recent"): Promise<ActionTrackerItem[]> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) return [];
  const payload = await invoke<{ items: ActionTrackerItem[] }>("list_action_tracker_items", { limit: 200, filter, sort });
  return payload.items || [];
}

export async function updateActionWorkflow(input: {
  itemType: "action" | "follow_up";
  itemId: number;
  workflowStatus: ActionTrackerItem["workflow_state"];
  dueAt?: string | null;
  notes?: string | null;
}): Promise<void> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) return;
  await invoke("update_action_workflow", {
    itemType: input.itemType,
    item_type: input.itemType,
    itemId: input.itemId,
    item_id: input.itemId,
    workflowStatus: input.workflowStatus,
    workflow_status: input.workflowStatus,
    dueAt: input.dueAt,
    due_at: input.dueAt,
    notes: input.notes,
  });
}

export async function listMemoryItems(itemType: "decisions" | "blockers_risks" | "open_questions"): Promise<ActionTrackerItem[]> {
  const invoke = window.__TAURI__?.core?.invoke;
  if (!invoke) return [];
  const payload = await invoke<{ items: ActionTrackerItem[] }>("list_memory_items", { itemType, limit: 200 });
  return payload.items || [];
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
    capture_id: captureId || "capture-demo-001",
    exported_at: new Date().toISOString(),
    metadata: {
      display_name: "Demo Capture",
      providers: ["local_llm"],
      latest_generated_at: new Date().toISOString(),
      summary_count: 2,
      persisted_summary_count: 2,
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
