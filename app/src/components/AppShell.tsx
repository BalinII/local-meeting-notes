import { useEffect, useMemo, useState } from "react";
import {
  createRecordingSession,
  exportReview,
  finaliseCapture,
  listGlobalActions,
  listMemoryItems,
  listRecentCaptures,
  listSessionLibrary,
  loadReviewPayload,
  pauseRecordingSession,
  resumeRecordingSession,
  saveReviewItem,
  searchAcrossSessions,
  startRecordingSession,
  stopRecordingSession,
  updateActionWorkflow,
  type ActionTrackerItem,
  type ExtractedOutput,
  type RecentCapture,
  type ReviewPayload,
  type SessionLibraryEntry,
  type SessionOverview,
  type SummaryOutput,
} from "../lib/reviewApi";

type WorkspaceTab = "review" | "library" | "search" | "actions" | "memory";

export function AppShell() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("review");
  const [captureId, setCaptureId] = useState("");
  const [selectedCaptureId, setSelectedCaptureId] = useState("");
  const [recentCaptures, setRecentCaptures] = useState<RecentCapture[]>([]);
  const [payload, setPayload] = useState<ReviewPayload | null>(null);
  const [status, setStatus] = useState("Load a session to review persisted notes.");
  const [isLoading, setIsLoading] = useState(false);

  const [library, setLibrary] = useState<SessionLibraryEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<{ total_matches: number; sessions: { capture_id: string; display_name: string; lifecycle_state?: string | null; matches: { item_type: string; field_name: string; snippet: string }[] }[] }>({ total_matches: 0, sessions: [] });
  const [actionItems, setActionItems] = useState<ActionTrackerItem[]>([]);
  const [memoryType, setMemoryType] = useState<"decisions" | "blockers_risks" | "open_questions">("decisions");
  const [memoryItems, setMemoryItems] = useState<ActionTrackerItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchMessage, setSearchMessage] = useState("Run a search across sessions.");
  const [isUpdatingWorkflowId, setIsUpdatingWorkflowId] = useState<string | null>(null);
  const [recordingSession, setRecordingSession] = useState<SessionOverview | null>(null);
  const [isRecordingBusy, setIsRecordingBusy] = useState(false);

  useEffect(() => {
    void refreshAll();
  }, []);

  useEffect(() => {
    void refreshMemory();
  }, [memoryType]);

  async function refreshAll() {
    await Promise.all([refreshRecentCaptures(), refreshLibrary(), refreshActions()]);
  }

  async function refreshRecentCaptures() {
    setRecentCaptures(await listRecentCaptures());
  }

  async function refreshLibrary() {
    setLibrary(await listSessionLibrary());
  }

  async function refreshActions() {
    setActionItems(await listGlobalActions());
  }

  async function refreshMemory() {
    setMemoryItems(await listMemoryItems(memoryType));
  }

  async function loadCapture(nextCaptureId: string) {
    const trimmed = nextCaptureId.trim();
    if (!trimmed) return;
    setIsLoading(true);
    try {
      const nextPayload = await loadReviewPayload(trimmed);
      setPayload(nextPayload);
      setCaptureId(trimmed);
      setSelectedCaptureId(trimmed);
      setStatus(`Loaded ${nextPayload.capture_id}`);
      setActiveTab("review");
    } finally {
      setIsLoading(false);
    }
  }

  async function runSearch() {
    if (!searchQuery.trim()) {
      setSearchResults({ total_matches: 0, sessions: [] });
      setSearchMessage("Enter text to search.");
      return;
    }
    setIsSearching(true);
    setSearchMessage("Searching...");
    try {
      const next = await searchAcrossSessions(searchQuery);
      setSearchResults(next);
      setSearchMessage(next.total_matches ? `Found ${next.total_matches} matches.` : "No matches found.");
    } catch (error) {
      setSearchMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setIsSearching(false);
    }
  }

  async function handleExport(format: "markdown" | "html" | "json") {
    if (!payload) return;
    const message = await exportReview(payload.capture_id, format);
    setStatus(message);
    await refreshAll();
  }

  async function handleReviewItem(item: ExtractedOutput, reviewStatus: NonNullable<ExtractedOutput["review_status"]>, values?: { description?: string; ownerName?: string | null }) {
    if (!payload) return;
    const saved = await saveReviewItem({
      itemType: item.item_type,
      itemId: item.id,
      reviewStatus,
      description: values?.description ?? item.effective_description ?? item.description,
      ownerName: values?.ownerName ?? item.effective_owner_name ?? item.owner_name,
    });
    setPayload(updateReviewedItem(payload, { ...item, ...saved }));
    await refreshAll();
  }

  async function handleFinalise() {
    if (!payload) return;
    await finaliseCapture(payload.capture_id);
    setStatus(`Session ${payload.capture_id} marked final.`);
    await refreshLibrary();
    await loadCapture(payload.capture_id);
  }

  async function handleWorkflow(item: ActionTrackerItem, workflowStatus: ActionTrackerItem["workflow_state"]) {
    if (item.item_type !== "action" && item.item_type !== "follow_up") return;
    const key = `${item.item_type}-${item.id}`;
    setIsUpdatingWorkflowId(key);
    setStatus(`Updating workflow state to ${workflowStatus}...`);
    try {
      await updateActionWorkflow({ itemType: item.item_type, itemId: item.id, workflowStatus });
      setStatus(`Saved workflow state: ${workflowStatus}.`);
      await refreshActions();
      await refreshMemory();
    } finally {
      setIsUpdatingWorkflowId(null);
    }
  }

  async function handleNewRecording() {
    setIsRecordingBusy(true);
    setStatus("Creating and starting microphone recording...");
    try {
      const created = await createRecordingSession();
      setRecordingSession({ ...created, lifecycle_state: "starting" });
      const started = await startRecordingSession(created.capture_id);
      setRecordingSession(started);
      setSelectedCaptureId(started.capture_id);
      setCaptureId(started.capture_id);
      setPayload(null);
      setStatus(`Recording ${started.display_name || started.capture_id}.`);
      await refreshLibrary();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setIsRecordingBusy(false);
    }
  }

  async function handlePauseRecording() {
    if (!recordingSession) return;
    setIsRecordingBusy(true);
    try {
      const paused = await pauseRecordingSession(recordingSession.capture_id);
      setRecordingSession(paused);
      setStatus(`Paused ${paused.display_name || paused.capture_id}.`);
      await refreshLibrary();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setIsRecordingBusy(false);
    }
  }

  async function handleResumeRecording() {
    if (!recordingSession) return;
    setIsRecordingBusy(true);
    try {
      const resumed = await resumeRecordingSession(recordingSession.capture_id);
      setRecordingSession(resumed);
      setStatus(`Recording ${resumed.display_name || resumed.capture_id}.`);
      await refreshLibrary();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setIsRecordingBusy(false);
    }
  }

  async function handleStopRecording() {
    if (!recordingSession) return;
    setIsRecordingBusy(true);
    setStatus("Stopping and processing recording...");
    try {
      const stopped = await stopRecordingSession(recordingSession.capture_id);
      setRecordingSession(stopped);
      await refreshAll();
      if (stopped.lifecycle_state === "review_ready" || stopped.lifecycle_state === "reviewed" || stopped.lifecycle_state === "exported") {
        await loadCapture(stopped.capture_id);
      } else {
        setStatus(stopped.last_error || `${stopped.display_name || stopped.capture_id} is ${stopped.lifecycle_state}.`);
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setIsRecordingBusy(false);
    }
  }

  const filteredLibrary = useMemo(() => library, [library]);

  return (
    <main className="app-shell">
      <section className="hero review-hero">
        <p className="eyebrow">Local Meeting Memory Workspace</p>
        <h1>Session Library + Search</h1>
        <p className="hero-copy">Browse every session, search outcomes across meeting history, and track carry-forward actions locally.</p>
        <div className="segmented-control">
          <button className="active" onClick={() => void handleNewRecording()} disabled={isRecordingBusy}>New Recording</button>
          {(["review", "library", "search", "actions", "memory"] as WorkspaceTab[]).map((tab) => (
            <button key={tab} className={tab === activeTab ? "active" : ""} onClick={() => setActiveTab(tab)}>{tab}</button>
          ))}
        </div>
        {recordingSession && (
          <div className="capture-picker recording-strip">
            <div>
              <p className="eyebrow">Current recording</p>
              <strong>{recordingSession.display_name || recordingSession.capture_id}</strong>
              <p className="capture-row-meta">{recordingSession.capture_id}</p>
            </div>
            <div className="badge-row">
              <span className={`status-pill session-${recordingSession.lifecycle_state}`}>{recordingSession.lifecycle_state}</span>
              <span className="status-pill subtle">Microphone only</span>
            </div>
            {recordingSession.last_error ? <p className="error-text">{recordingSession.last_error}</p> : null}
            <div className="recording-controls">
              {recordingSession.lifecycle_state === "recording" && (
                <button className="secondary-button" onClick={() => void handlePauseRecording()} disabled={isRecordingBusy}>Pause</button>
              )}
              {recordingSession.lifecycle_state === "paused" && (
                <button onClick={() => void handleResumeRecording()} disabled={isRecordingBusy}>Resume</button>
              )}
              {(recordingSession.lifecycle_state === "recording" || recordingSession.lifecycle_state === "paused") && (
                <button onClick={() => void handleStopRecording()} disabled={isRecordingBusy}>Stop and Process</button>
              )}
            </div>
          </div>
        )}
        <p className="status-line">{status}</p>
      </section>

      {activeTab === "review" && (
        <section>
          <div className="capture-toolbar">
            <input placeholder="capture-id" value={captureId} onChange={(event) => setCaptureId(event.target.value)} />
            <button onClick={() => void loadCapture(captureId)} disabled={isLoading}>{isLoading ? "Loading..." : "Load Capture"}</button>
          </div>
          <div className="capture-list" style={{ marginTop: 12 }}>
            {recentCaptures.map((capture) => (
              <button key={capture.capture_id} className={`capture-row ${capture.capture_id === selectedCaptureId ? "active" : ""}`} onClick={() => void loadCapture(capture.capture_id)}>
                <div className="capture-row-title"><strong>{capture.capture_id}</strong></div>
                <p className="capture-row-meta">{formatDate(capture.latest_generated_at || capture.created_at)}</p>
              </button>
            ))}
          </div>
          {payload && (
            <section className="review-layout" style={{ marginTop: 14 }}>
              <aside className="review-sidebar">
                <h2>{payload.metadata.display_name || payload.capture_id}</h2>
                <p>{payload.capture_id}</p>
                <div className="export-actions">
                  <button onClick={() => void handleExport("markdown")}>Export Markdown</button>
                  <button onClick={() => void handleExport("html")}>Export HTML</button>
                  <button onClick={() => void handleExport("json")}>Export JSON</button>
                  <button className="secondary-button" onClick={() => void handleFinalise()}>Finalise Notes</button>
                </div>
              </aside>
              <section className="review-content">
                <SummaryPanel summaries={payload.summaries} />
                <ItemPanel title="Actions" items={payload.actions} showOwner onReviewItem={handleReviewItem} />
                <ItemPanel title="Decisions" items={payload.decisions} onReviewItem={handleReviewItem} />
                <ItemPanel title="Follow-ups" items={payload.follow_ups} showOwner onReviewItem={handleReviewItem} />
                <ItemPanel title="Blockers / Risks" items={payload.blockers_risks} showOwner tone="risk" onReviewItem={handleReviewItem} />
                <ItemPanel title="Open Questions" items={payload.open_questions} showOwner tone="question" onReviewItem={handleReviewItem} />
              </section>
            </section>
          )}
        </section>
      )}

      {activeTab === "library" && (
        <section className="panel workspace-panel">
          <div className="panel-heading compact"><h2>Session Library</h2><button className="secondary-button" onClick={() => void refreshLibrary()}>Refresh</button></div>
          <div className="session-list">
            {filteredLibrary.map((session) => (
              <button className="session-row" key={session.capture_id} onClick={() => void loadCapture(session.capture_id)}>
                <strong>{session.display_name}</strong>
                <span>{session.capture_id}</span>
                <div className="badge-row"><span className={`status-pill session-${session.lifecycle_state}`}>{session.lifecycle_state}</span>{session.reviewed_items_exist ? <span className="status-pill review-edited">reviewed</span> : null}{session.exported_at ? <span className="status-pill subtle">exported</span> : null}</div>
              </button>
            ))}
          </div>
        </section>
      )}

      {activeTab === "search" && (
        <section className="panel workspace-panel">
          <div className="capture-toolbar compact-grid">
            <input className="workspace-search" placeholder="Search summaries, actions, decisions, follow-ups..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void runSearch(); }} />
            <button onClick={() => void runSearch()} disabled={isSearching}>{isSearching ? "Searching..." : "Search"}</button>
          </div>
          <p className="muted">{searchMessage} Matches: {searchResults.total_matches}</p>
          <div className="workspace-group-list">
            {searchResults.sessions.map((session) => (
              <div className="workspace-group" key={session.capture_id}>
                <div className="workspace-group-heading"><div><h3>{session.display_name}</h3><p>{session.capture_id}</p></div><button className="secondary-button" onClick={() => void loadCapture(session.capture_id)}>Open Session</button></div>
                <div className="workspace-item-list">
                  {session.matches.map((match, index) => (
                    <article className="workspace-item" key={`${session.capture_id}-${index}`}>
                      <strong>{match.field_name}</strong>
                      <p>{match.snippet}</p>
                    </article>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {activeTab === "actions" && (
        <section className="panel workspace-panel">
          <div className="panel-heading compact"><h2>Global Action Tracker</h2><button className="secondary-button" onClick={() => void refreshActions()}>Refresh</button></div>
          <div className="workspace-item-list">
            {actionItems.map((item) => (
              <article className="workspace-item" key={`${item.item_type}-${item.id}`}>
                <strong>{item.effective_description}</strong>
                <p>{item.source_display_name} · {item.capture_id} · {item.effective_owner_name || "Unknown"}</p>
                <div className="badge-row"><span className={`status-pill action-${item.workflow_state}`}>{item.workflow_state}</span><span className={`status-pill review-${item.review_status}`}>{item.review_status}</span></div>
                {(item.item_type === "action" || item.item_type === "follow_up") && (
                  <div className="review-actions">
                    <button className="secondary-button" disabled={isUpdatingWorkflowId === `${item.item_type}-${item.id}`} onClick={() => void handleWorkflow(item, "open")}>Open</button>
                    <button className="secondary-button" disabled={isUpdatingWorkflowId === `${item.item_type}-${item.id}`} onClick={() => void handleWorkflow(item, "done")}>Done</button>
                    <button className="secondary-button" disabled={isUpdatingWorkflowId === `${item.item_type}-${item.id}`} onClick={() => void handleWorkflow(item, "carried_forward")}>Carry Forward</button>
                    <button className="danger-button" disabled={isUpdatingWorkflowId === `${item.item_type}-${item.id}`} onClick={() => void handleWorkflow(item, "dismissed")}>Dismiss</button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

      {activeTab === "memory" && (
        <section className="panel workspace-panel">
          <div className="panel-heading compact"><h2>Cross-session Memory</h2></div>
          <div className="segmented-control">
            <button className={memoryType === "decisions" ? "active" : ""} onClick={() => setMemoryType("decisions")}>decisions</button>
            <button className={memoryType === "blockers_risks" ? "active" : ""} onClick={() => setMemoryType("blockers_risks")}>blockers/risks</button>
            <button className={memoryType === "open_questions" ? "active" : ""} onClick={() => setMemoryType("open_questions")}>open questions</button>
          </div>
          <div className="workspace-item-list">
            {memoryItems.map((item) => (
              <article className="workspace-item" key={`${item.item_type}-${item.id}`}>
                <strong>{item.effective_description}</strong>
                <p>{item.source_display_name} · {item.capture_id}</p>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

function SummaryPanel({ summaries }: { summaries: SummaryOutput[] }) {
  return <section className="panel">{summaries.map((summary) => <article className="note-card" key={summary.title}><h3>{summary.title}</h3><p>{summary.content}</p></article>)}</section>;
}

function ItemPanel({ title, items, showOwner = false, tone, onReviewItem }: { title: string; items: ExtractedOutput[]; showOwner?: boolean; tone?: "risk" | "question"; onReviewItem: (item: ExtractedOutput, reviewStatus: NonNullable<ExtractedOutput["review_status"]>, values?: { description?: string; ownerName?: string | null }) => Promise<void>; }) {
  return (
    <section className={`panel ${tone ? `panel-${tone}` : ""}`}>
      <div className="panel-heading compact"><p className="eyebrow">{title}</p><span className="count-pill">{items.length}</span></div>
      {items.map((item, index) => <ReviewItemCard item={item} key={`${title}-${index}`} showOwner={showOwner} onReviewItem={onReviewItem} />)}
    </section>
  );
}

function ReviewItemCard({ item, showOwner, onReviewItem }: { item: ExtractedOutput; showOwner: boolean; onReviewItem: (item: ExtractedOutput, reviewStatus: NonNullable<ExtractedOutput["review_status"]>, values?: { description?: string; ownerName?: string | null }) => Promise<void>; }) {
  const description = item.effective_description || item.description;
  const ownerName = item.effective_owner_name || item.owner_name || "";
  return (
    <article className={`note-card item-card review-${item.review_status || "generated"}`}>
      <p>{description}</p>
      {showOwner && <p className="original-text">Owner: {ownerName || "Unknown"}</p>}
      <div className="review-actions">
        <button className="secondary-button" onClick={() => void onReviewItem(item, "accepted")}>Accept</button>
        <button className="secondary-button" onClick={() => void onReviewItem(item, "edited", { description, ownerName })}>Edit as-is</button>
        <button className="danger-button" onClick={() => void onReviewItem(item, "rejected")}>Reject</button>
      </div>
    </article>
  );
}

function updateReviewedItem(payload: ReviewPayload, updated: ExtractedOutput): ReviewPayload {
  const replace = (items: ExtractedOutput[]) => items.map((item) => (item.id === updated.id && item.item_type === updated.item_type ? updated : item));
  return {
    ...payload,
    actions: replace(payload.actions),
    decisions: replace(payload.decisions),
    follow_ups: replace(payload.follow_ups),
    blockers_risks: replace(payload.blockers_risks),
    open_questions: replace(payload.open_questions),
  };
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "Unknown";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}
