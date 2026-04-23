import { useEffect, useState } from "react";
import {
  exportReview,
  loadReviewPayload,
  saveReviewItem,
  type ExtractedOutput,
  type ReviewPayload,
  type SummaryOutput,
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
      const nextPayload = await loadReviewPayload(captureId.trim());
      setPayload(nextPayload);
      setStatus(`Loaded ${nextPayload.capture_id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleExport(format: "markdown" | "html" | "json") {
    if (!payload) {
      setStatus("Load a capture before exporting.");
      return;
    }
    setStatus(`Exporting ${format}...`);
    try {
      const message = await exportReview(payload.capture_id, format);
      setStatus(message);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    }
  }

  async function handleReviewItem(
    item: ExtractedOutput,
    reviewStatus: NonNullable<ExtractedOutput["review_status"]>,
    values?: { description?: string; ownerName?: string | null },
  ) {
    if (!payload) return;
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
      setStatus(`Saved ${reviewStatus} review state.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    }
  }

  return (
    <main className="app-shell">
      <section className="hero review-hero">
        <p className="eyebrow">Local Review Workspace</p>
        <h1>Meeting Notes Review</h1>
        <p className="hero-copy">
          Load a capture, review generated summaries and extracted outcomes, then export
          Markdown, HTML, or JSON for local sharing.
        </p>
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
              <ProviderBadge item={summary} />
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

function TextBlock({ text }: { text: string }) {
  const blocks = text
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);

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
    <article className={`note-card item-card ${reviewStatus === "rejected" ? "is-rejected" : ""}`}>
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
        <ProviderBadge item={item} />
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
            <button
              className="secondary-button"
              onClick={() => void runReviewUpdate("accepted")}
              disabled={isSaving}
            >
              Accept
            </button>
            <button
              className="danger-button"
              onClick={() => void runReviewUpdate("rejected")}
              disabled={isSaving}
            >
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
  const uncertain = label === "Unknown" || label === "Unconfirmed speaker";
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
  if (!text) return null;
  return (
    <details className="evidence">
      <summary>Evidence</summary>
      <p>{text}</p>
    </details>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "Unknown";
  return value;
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
