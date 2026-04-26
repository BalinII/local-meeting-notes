import { useEffect, useMemo, useState } from "react";
import {
  archiveSession,
  createRecordingSession,
  deleteSourceAudio,
  exportReview,
  listRecentCaptures,
  loadReviewPayload,
  loadSessionDashboard,
  pauseSession,
  renameSession,
  resumeSession,
  runRetentionCleanup,
  saveRetentionSettings,
  saveReviewItem,
  startSession,
  stopSession,
  updateKeepSourceAudio,
  type ExtractedOutput,
  type ReviewPayload,
  type SessionDashboardPayload,
  type SessionOverview,
  type SummaryOutput,
  type WorkspaceActionItem,
} from "../lib/reviewApi";

export function AppShell() {
  const [captureId, setCaptureId] = useState("");
  const [payload, setPayload] = useState<ReviewPayload | null>(null);
  const [status, setStatus] = useState("Enter a capture id to review persisted notes.");
  const [isLoading, setIsLoading] = useState(false);

  async function handleLoad() {
    if (!captureId.trim()) {
      setStatus("Capture id is required.");
      return;
    }
    setIsLoading(true);
    setStatus("Loading capture outputs...");
    try {
      const nextPayload = await loadReviewPayload(captureId);
      setPayload(nextPayload);
      setStatus(`Loaded ${nextPayload.capture_id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleStopSession() {
    if (!selectedSession) return;
    setSelectedSession({ ...selectedSession, lifecycle_state: "processing" });
    await handleSessionAction(
      () => stopSession(selectedSession.capture_id),
      "Stopping recording and processing outputs...",
      "Processing complete.",
    );
  }

  async function handleExport(format: "markdown" | "html" | "json") {
    if (!selectedSession) return;
    setStatus(`Exporting ${format}...`);
    try {
      const message = await exportReview(selectedSession.capture_id, format);
      setStatus(message);
      await refreshDashboard(selectedSession.capture_id);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    }
  }

  async function handleReviewItem(
    item: ExtractedOutput,
    reviewStatus: NonNullable<ExtractedOutput["review_status"]>,
    values?: { description?: string; ownerName?: string | null },
  ) {
    if (!payload || !selectedSession) return;
    setStatus(`Saving ${reviewStatus} review state...`);
    try {
      const saved = await saveReviewItem({
        itemType: item.item_type,
        itemId: item.id,
        reviewStatus,
        description: values?.description ?? item.effective_description ?? item.description,
        ownerName: values?.ownerName ?? item.effective_owner_name ?? item.owner_name,
      });
      setPayload(updateReviewedItem(payload, { ...item, ...saved }));
      await refreshDashboard(selectedSession.capture_id);
      setStatus(`Saved ${reviewStatus} review state.`);
      await refreshRecentCaptures();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    }
  }

  async function handleSaveRetention() {
    if (!retentionSettings) return;
    setStatus("Saving retention settings...");
    try {
      const saved = await saveRetentionSettings(
        retentionSettings.raw_audio_retention_days,
        retentionSettings.delete_temp_processing_files,
      );
      setRetentionSettings(saved);
      await refreshDashboard(selectedSession?.capture_id);
      setStatus("Retention settings saved.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    }
  }

  async function handleCleanup() {
    setStatus("Running cleanup...");
    try {
      const result = await runRetentionCleanup();
      await refreshDashboard(selectedSession?.capture_id);
      setStatus(`Cleanup finished. Deleted audio for ${result.deleted_audio_sessions} sessions.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    }
  }

  const elapsedLabel = useMemo(() => formatElapsed(selectedSession, clock), [clock, selectedSession]);
  const filteredSessions = useMemo(
    () => filterSessions(dashboard?.sessions || [], workspaceQuery),
    [dashboard?.sessions, workspaceQuery],
  );
  const filteredActionItems = useMemo(
    () => filterWorkspaceItems(dashboard?.action_items || [], workspaceQuery, actionStateFilter),
    [actionStateFilter, dashboard?.action_items, workspaceQuery],
  );

  return (
    <main className="app-shell">
      <section className="hero review-hero">
        <p className="eyebrow">Local Recording Workspace</p>
        <h1>Meeting Notes Workflow</h1>
        <p className="hero-copy">
          Load a capture, review generated summaries and extracted outcomes, then export
          Markdown, HTML, or JSON for local sharing.
        </p>

        <div className="capture-picker">
          <div className="panel-heading compact capture-picker-header">
            <p className="eyebrow">Recent captures</p>
            <button
              className="secondary-button"
              onClick={() => void refreshRecentCaptures()}
              disabled={isRefreshingList}
            >
              {isRefreshingList ? "Refreshing..." : "Refresh"}
            </button>
          </div>
          {recentCaptures.length ? (
            <div className="capture-list">
              {recentCaptures.map((capture) => {
                const isSelected = capture.capture_id === selectedCaptureId;
                return (
                  <button
                    key={capture.capture_id}
                    className={`capture-row ${isSelected ? "active" : ""}`}
                    onClick={() => void loadCapture(capture.capture_id)}
                    disabled={isLoading && isSelected}
                  >
                    <div className="capture-row-title">
                      <strong>{capture.capture_id}</strong>
                      {capture.has_reviewed_items ? (
                        <span className="status-pill review-edited">Reviewed items</span>
                      ) : (
                        <span className="status-pill subtle">Not reviewed</span>
                      )}
                    </div>
                    <p className="capture-row-meta">
                      Generated: {formatDate(capture.latest_generated_at || capture.created_at)}
                    </p>
                    <div className="badge-row">
                      {capture.providers.length ? (
                        capture.providers.map((provider) => (
                          <span className="status-pill subtle" key={`${capture.capture_id}-${provider}`}>
                            {provider}
                          </span>
                        ))
                      ) : (
                        <span className="status-pill subtle">Unknown provider</span>
                      )}
                      {capture.models.map((model) => (
                        <span className="status-pill subtle" key={`${capture.capture_id}-${model}`}>
                          {model}
                        </span>
                      ))}
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="muted">No recent captures yet.</p>
          )}
        </div>

        <div className="capture-toolbar">
          <input
            aria-label="Capture id"
            placeholder="capture-id"
            value={captureId}
            onChange={(event) => setCaptureId(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void handleLoad();
            }}
          />
          <button onClick={() => void handleLoad()} disabled={isLoading}>
            {isLoading ? "Loading..." : "Load Capture"}
          </button>
        </div>
        <p className="status-line">{status}</p>
      </section>

      {payload ? (
        <section className="review-layout">
          <aside className="review-sidebar">
            <h2>{payload.capture_id}</h2>
            <p>Exported preview: {formatDate(payload.exported_at)}</p>
            <div className="badge-row">
              {payload.metadata.providers.length ? (
                payload.metadata.providers.map((provider) => (
                  <span className="status-pill subtle" key={provider}>
                    {provider}
                  </span>
                ))
              ) : (
                <span className="status-pill subtle">Unknown provider</span>
              )}
            </div>
            <div className="export-actions">
              <button onClick={() => void handleExport("markdown")}>Export Markdown</button>
              <button onClick={() => void handleExport("html")}>Export HTML</button>
              <button onClick={() => void handleExport("json")}>Export JSON</button>
            </div>
          </aside>

          <section className="review-content">
            <SummaryPanel summaries={payload.summaries} />
            <ItemPanel title="Actions" items={payload.actions} showOwner onReviewItem={handleReviewItem} />
            <ItemPanel title="Decisions" items={payload.decisions} onReviewItem={handleReviewItem} />
            <ItemPanel title="Follow-ups" items={payload.follow_ups} showOwner onReviewItem={handleReviewItem} />
            <ItemPanel
              title="Blockers / Risks"
              items={payload.blockers_risks}
              showOwner
              tone="risk"
              onReviewItem={handleReviewItem}
            />
            <ItemPanel
              title="Open Questions"
              items={payload.open_questions}
              showOwner
              tone="question"
              onReviewItem={handleReviewItem}
            />
          </section>
        </section>
      ) : (
        <section className="empty-state">
          <h2>No capture loaded</h2>
          <p>
            The desktop shell uses the local backend through Tauri. In browser-only dev mode,
            it shows demo data so the review layout remains visible.
          </p>
        </section>
      )}
    </main>
  );
}

function SummaryPanel({ summaries }: { summaries: SummaryOutput[] }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <p className="eyebrow">Summary</p>
        <h2>Current Notes</h2>
      </div>
      {summaries.length ? (
        summaries.map((summary) => (
          <article className="note-card" key={`${summary.summary_type}-${summary.title}`}>
            <div className="card-title-row">
              <h3>{summary.title}</h3>
              <div className="card-meta-actions">
                <ProviderBadge item={summary} />
                <CopyButton label="Copy summary" value={summary.content} />
              </div>
            </div>
            <TextBlock text={summary.content} />
            <Evidence text={summary.evidence_snippet} />
          </article>
        ))
      ) : (
        <p className="muted">No summaries found for this capture.</p>
      )}
    </section>
  );
}

function WorkspacePanel({
  items,
  stateFilter,
  onStateFilter,
  onOpenSession,
}: {
  items: WorkspaceActionItem[];
  stateFilter: "open" | "blocked" | "done" | "all";
  onStateFilter: (value: "open" | "blocked" | "done" | "all") => void;
  onOpenSession: (captureId: string) => void;
}) {
  const grouped = groupWorkspaceItems(items);
  return (
    <section className="panel workspace-panel">
      <div className="panel-heading compact">
        <div>
          <p className="eyebrow">Cross-session Outcomes</p>
          <h2>Action Workspace</h2>
        </div>
        <span className="count-pill">{items.length}</span>
      </div>
      <div className="segmented-control" aria-label="Action state filter">
        {(["open", "blocked", "done", "all"] as const).map((state) => (
          <button
            className={stateFilter === state ? "active" : ""}
            key={state}
            onClick={() => onStateFilter(state)}
          >
            {state}
          </button>
        ))}
      </div>
      {grouped.length ? (
        <div className="workspace-group-list">
          {grouped.map((group) => (
            <section className="workspace-group" key={group.capture_id}>
              <div className="workspace-group-heading">
                <div>
                  <h3>{group.source_display_name}</h3>
                  <p>{group.capture_id}</p>
                </div>
                <button className="secondary-button" onClick={() => onOpenSession(group.capture_id)}>
                  Open
                </button>
              </div>
              <div className="workspace-item-list">
                {group.items.map((item) => (
                  <article className="workspace-item" key={`${item.item_type}-${item.capture_id}-${item.id}`}>
                    <div>
                      <strong>{item.effective_description || item.description}</strong>
                      <div className="badge-row">
                        <span className={`status-pill action-${item.workflow_state}`}>{item.workflow_state}</span>
                        <ReviewStatusBadge status={item.review_status || "generated"} />
                        <OwnerBadge owner={item.effective_owner_name || item.owner_name} />
                        <span className="status-pill subtle">{formatItemType(item.item_type)}</span>
                      </div>
                    </div>
                    {item.evidence_snippet ? <Evidence text={item.evidence_snippet} /> : null}
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <p className="muted">No matching cross-session outcomes.</p>
      )}
    </section>
  );
}

function TextBlock({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).map((block) => block.trim()).filter(Boolean);
  if (!blocks.length) return null;
  return (
    <div className="summary-text">
      {blocks.map((block, index) => (
        <p key={index}>{block}</p>
      ))}
    </div>
  );
}

function ItemPanel({
  title,
  items,
  showOwner = false,
  tone,
  onReviewItem,
}: {
  title: string;
  items: ExtractedOutput[];
  showOwner?: boolean;
  tone?: "risk" | "question";
  onReviewItem: (
    item: ExtractedOutput,
    reviewStatus: NonNullable<ExtractedOutput["review_status"]>,
    values?: { description?: string; ownerName?: string | null },
  ) => Promise<void>;
}) {
  return (
    <section className={`panel ${tone ? `panel-${tone}` : ""}`}>
      <div className="panel-heading compact">
        <p className="eyebrow">{title}</p>
        <span className="count-pill">{items.length}</span>
      </div>
      {items.length ? (
        <div className="item-list">
          {items.map((item, index) => (
            <ReviewItemCard
              item={item}
              key={`${title}-${item.item_type}-${item.id}-${index}`}
              showOwner={showOwner}
              onReviewItem={onReviewItem}
            />
          ))}
        </div>
      ) : (
        <p className="muted">No {title.toLowerCase()} found.</p>
      )}
    </section>
  );
}

function ReviewItemCard({
  item,
  showOwner,
  onReviewItem,
}: {
  item: ExtractedOutput;
  showOwner: boolean;
  onReviewItem: (
    item: ExtractedOutput,
    reviewStatus: NonNullable<ExtractedOutput["review_status"]>,
    values?: { description?: string; ownerName?: string | null },
  ) => Promise<void>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [description, setDescription] = useState(item.effective_description || item.description);
  const [ownerName, setOwnerName] = useState(item.effective_owner_name || item.owner_name || "");
  const [isSaving, setIsSaving] = useState(false);
  const reviewStatus = item.review_status || "generated";

  useEffect(() => {
    if (isEditing) return;
    setDescription(item.effective_description || item.description);
    setOwnerName(item.effective_owner_name || item.owner_name || "");
  }, [isEditing, item.description, item.effective_description, item.effective_owner_name, item.owner_name]);

  async function runReviewUpdate(
    nextStatus: NonNullable<ExtractedOutput["review_status"]>,
    values?: { description?: string; ownerName?: string | null },
  ) {
    setIsSaving(true);
    try {
      await onReviewItem(item, nextStatus, values);
      if (nextStatus === "edited") setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <article className={`note-card item-card review-${reviewStatus}`}>
      <div className="card-title-row">
        <div>
          {isEditing ? (
            <textarea
              aria-label="Reviewed description"
              className="review-textarea"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          ) : (
            <h3>{item.effective_description || item.description}</h3>
          )}
        </div>
        <div className="card-meta-actions">
          <ProviderBadge item={item} />
          <CopyButton
            label="Copy item"
            value={`${item.effective_description || item.description}${showOwner ? `\nOwner: ${item.effective_owner_name || item.owner_name || "Unconfirmed speaker"}` : ""}`}
          />
        </div>
      </div>
      <div className="badge-row">
        <ReviewStatusBadge status={reviewStatus} />
        {showOwner && isEditing ? (
          <input
            aria-label="Reviewed owner"
            className="owner-input"
            placeholder="Unconfirmed speaker"
            value={ownerName}
            onChange={(event) => setOwnerName(event.target.value)}
          />
        ) : showOwner ? (
          <OwnerBadge owner={item.effective_owner_name || item.owner_name} />
        ) : null}
        {isUncertainOwner(item.effective_owner_name || item.owner_name) ? (
          <span className="status-pill warning">Uncertainty visible</span>
        ) : null}
        {item.start_offset_seconds != null ? (
          <span className="status-pill subtle">
            {item.start_offset_seconds}-{item.end_offset_seconds}s
          </span>
        ) : null}
      </div>
      {item.reviewed_description ? <p className="original-text">Original: {item.description}</p> : null}
      <div className="review-actions">
        {isEditing ? (
          <>
            <button
              onClick={() =>
                void runReviewUpdate("edited", {
                  description,
                  ownerName: showOwner ? ownerName : null,
                })
              }
              disabled={isSaving}
            >
              Save
            </button>
            <button className="secondary-button" onClick={() => setIsEditing(false)} disabled={isSaving}>
              Cancel
            </button>
          </>
        ) : (
          <>
            <button className="secondary-button" onClick={() => setIsEditing(true)} disabled={isSaving}>
              Edit
            </button>
            <button className="secondary-button" onClick={() => void runReviewUpdate("accepted")} disabled={isSaving}>
              Accept
            </button>
            <button className="danger-button" onClick={() => void runReviewUpdate("rejected")} disabled={isSaving}>
              Reject
            </button>
          </>
        )}
      </div>
      <Evidence text={item.evidence_snippet} />
    </article>
  );
}

function ReviewStatusBadge({ status }: { status: string }) {
  return <span className={`status-pill review-${status}`}>{status}</span>;
}

function OwnerBadge({ owner }: { owner?: string | null }) {
  const label = owner || "Unconfirmed speaker";
  const uncertain = isUncertainOwner(label);
  return <span className={`status-pill ${uncertain ? "warning" : "subtle"}`}>{label}</span>;
}

function ProviderBadge({ item }: { item: SummaryOutput | ExtractedOutput }) {
  if (!item.provider_name) return null;
  return (
    <span className="status-pill subtle">
      {item.provider_name}
      {item.model_name ? ` / ${item.model_name}` : ""}
    </span>
  );
}

function Evidence({ text }: { text?: string | null }) {
  const [isExpanded, setIsExpanded] = useState(false);
  if (!text) return null;
  return (
    <section className={`evidence ${isExpanded ? "expanded" : ""}`}>
      <div className="evidence-header">
        <button className="link-button" onClick={() => setIsExpanded((value) => !value)}>
          {isExpanded ? "Hide evidence" : "Show evidence"}
        </button>
        <CopyButton label="Copy evidence" value={text} />
      </div>
      {isExpanded ? <p>{text}</p> : null}
    </section>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "Unknown";
  return new Date(value).toLocaleString();
}

function formatElapsed(session: SessionOverview | null, clock: number) {
  if (!session) return "00:00";
  const base = session.recorded_seconds || 0;
  const startedAt = session.active_capture?.started_at;
  const extra =
    session.lifecycle_state === "recording" && startedAt
      ? Math.max(0, Math.floor((clock - Date.parse(startedAt)) / 1000))
      : 0;
  const total = base + extra;
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function filterSessions(sessions: SessionOverview[], query: string) {
  const normalized = normalizeSearch(query);
  if (!normalized) return sessions;
  return sessions.filter((session) =>
    normalizeSearch(`${session.display_name} ${session.capture_id} ${session.lifecycle_state}`).includes(normalized),
  );
}

function filterWorkspaceItems(
  items: WorkspaceActionItem[],
  query: string,
  stateFilter: "open" | "blocked" | "done" | "all",
) {
  const normalized = normalizeSearch(query);
  return items.filter((item) => {
    if (stateFilter !== "all" && item.workflow_state !== stateFilter) return false;
    if (!normalized) return true;
    return normalizeSearch(
      `${item.source_display_name} ${item.capture_id} ${item.effective_description || item.description} ${
        item.effective_owner_name || item.owner_name || ""
      } ${item.evidence_snippet || ""}`,
    ).includes(normalized);
  });
}

function groupWorkspaceItems(items: WorkspaceActionItem[]) {
  const groups: {
    capture_id: string;
    source_display_name: string;
    items: WorkspaceActionItem[];
  }[] = [];
  for (const item of items) {
    let group = groups.find((candidate) => candidate.capture_id === item.capture_id);
    if (!group) {
      group = {
        capture_id: item.capture_id,
        source_display_name: item.source_display_name,
        items: [],
      };
      groups.push(group);
    }
    if (!group.items.some((candidate) => candidate.item_type === item.item_type && candidate.id === item.id)) {
      group.items.push(item);
    }
  }
  return groups;
}

function normalizeSearch(value: string) {
  return value.trim().toLocaleLowerCase();
}

function formatItemType(value: WorkspaceActionItem["item_type"]) {
  if (value === "blocker_risk") return "Blocker / risk";
  if (value === "open_question") return "Open question";
  if (value === "follow_up") return "Follow-up";
  return "Action";
}

function updateReviewedItem(payload: ReviewPayload, item: ExtractedOutput): ReviewPayload {
  const updateItems = (items: ExtractedOutput[]) =>
    items.map((candidate) =>
      candidate.item_type === item.item_type && candidate.id === item.id ? item : candidate,
    );
  return {
    ...payload,
    actions: updateItems(payload.actions),
    decisions: updateItems(payload.decisions),
    follow_ups: updateItems(payload.follow_ups),
    blockers_risks: updateItems(payload.blockers_risks),
    open_questions: updateItems(payload.open_questions),
  };
}

function MetadataStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="meta-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CopyButton({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch (error) {
      setCopied(false);
      console.warn("Clipboard write failed", error);
    }
  }

  return (
    <button className="copy-button secondary-button" aria-label={label} onClick={() => void handleCopy()}>
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function isUncertainOwner(owner?: string | null) {
  return !owner || owner === "Unknown" || owner === "Unconfirmed speaker";
}
