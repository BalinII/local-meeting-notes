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
