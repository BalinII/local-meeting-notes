import { expect, test } from "@playwright/test";

test("app shell exposes core local review workspace affordances", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });

  await expect(page.getByRole("heading", { name: "Session Library + Search" })).toBeVisible();
  await expect(page.getByRole("button", { name: "New Recording" })).toBeVisible();
  await expect(page.getByRole("button", { name: "library" })).toBeVisible();
  await expect(page.getByRole("button", { name: "search" })).toBeVisible();
});

test("library and search navigation render stable workspace panels", async ({ page }) => {
  await page.goto("/", { waitUntil: "domcontentloaded" });

  await page.getByRole("button", { name: "library" }).click();
  await expect(page.getByRole("heading", { name: "Session Library", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "search" }).click();
  await expect(page.getByRole("heading", { name: "Search", exact: true })).toBeVisible();
  await expect(page.getByPlaceholder("Search summaries, actions, decisions, follow-ups...")).toBeVisible();
});

test("opening a named session makes the review target obvious", async ({ page }) => {
  await page.setViewportSize({ width: 1000, height: 520 });
  await page.addInitScript(() => {
    const sessions = [
      {
        capture_id: "capture-alpha",
        display_name: "Sprint Planning",
        lifecycle_state: "review_ready",
        created_at: "2026-05-01T09:00:00+10:00",
        updated_at: "2026-05-01T10:00:00+10:00",
        reviewed_at: null,
        exported_at: null,
        reviewed_items_exist: false,
        providers: ["local_llm"],
        models: ["llama3.1:8b"],
        last_error: null,
      },
      {
        capture_id: "capture-beta",
        display_name: "Design Review",
        lifecycle_state: "reviewed",
        created_at: "2026-04-30T09:00:00+10:00",
        updated_at: "2026-04-30T10:00:00+10:00",
        reviewed_at: null,
        exported_at: null,
        reviewed_items_exist: true,
        providers: ["local_llm"],
        models: ["llama3.1:8b"],
        last_error: null,
      },
    ];
    const reviewPayload = {
      capture_id: "capture-alpha",
      exported_at: "2026-05-01T10:00:00+10:00",
      metadata: {
        display_name: "Sprint Planning",
        providers: ["local_llm"],
        latest_generated_at: "2026-05-01T10:00:00+10:00",
        summary_count: 1,
        persisted_summary_count: 1,
        action_count: 0,
        decision_count: 0,
        follow_up_count: 0,
      },
      summaries: [
        {
          title: "Executive Summary",
          summary_type: "executive",
          content: "The planning session is ready for review.",
          provider_name: "local_llm",
          model_name: "llama3.1:8b",
        },
      ],
      actions: [],
      decisions: [],
      follow_ups: [],
      blockers_risks: [],
      open_questions: [],
    };

    window.__TAURI__ = {
      core: {
        invoke: async (command: string) => {
          if (command === "list_recent_captures") return sessions;
          if (command === "session_library") return { sessions };
          if (command === "review_capture") return reviewPayload;
          if (command === "list_planned_sessions" || command === "list_upcoming_sessions") return { sessions: [] };
          if (command === "list_action_tracker_items" || command === "list_memory_items") return { items: [] };
          if (command === "session_search") return { query: "", total_matches: 0, sessions: [] };
          return null;
        },
      },
    };
  });

  await page.goto("/");
  await page.getByRole("button", { name: "library" }).click();

  const sessionRow = page.locator(".session-row").filter({ hasText: "Sprint Planning" });
  await expect(sessionRow.locator("strong")).toHaveText("Sprint Planning");
  await expect(sessionRow.getByText("Capture ID: capture-alpha")).toBeVisible();

  await sessionRow.getByRole("button", { name: "Open Session" }).click();

  await expect(page.getByRole("heading", { name: "Reviewing: Sprint Planning" })).toBeVisible();
  await expect(page.getByText("Opened Sprint Planning. Review section is ready.")).toBeVisible();
  const activeRecentSession = page.locator(".capture-row.active").filter({ hasText: "Sprint Planning" });
  await expect(activeRecentSession).toBeVisible();
  await expect(activeRecentSession.getByText("Currently reviewing")).toBeVisible();
  await expect(activeRecentSession.getByText("Capture ID: capture-alpha")).toBeVisible();
  await expect.poll(async () => page.evaluate(() => Math.round(window.scrollY))).toBeGreaterThan(100);
});
