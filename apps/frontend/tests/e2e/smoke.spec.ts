import { expect, test } from "@playwright/test";

test("auth screen loads", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByText("Вход в дневник")).toBeVisible();
  await expect(page.getByRole("button", { name: "Войти" })).toBeVisible();
});
