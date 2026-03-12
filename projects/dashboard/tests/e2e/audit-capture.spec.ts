import fs from "node:fs";
import path from "node:path";
import { test } from "@playwright/test";
import { loadRouteAuditRecords } from "./census";
import { gotoRoute, resetBrowserState } from "./helpers";

const ROUTES = loadRouteAuditRecords();
const REPORT_ROOT = path.resolve(__dirname, "../../../reports/completion-audit/latest/fixture-screenshots");

function routeSlug(routePath: string) {
  if (routePath === "/") {
    return "root";
  }
  return routePath.replace(/^\//, "").replace(/[/:*?]+/g, "-");
}

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

for (const route of ROUTES) {
  test(`audit capture: ${route.routePath}`, async ({ page }, testInfo) => {
    const projectDir = path.join(REPORT_ROOT, testInfo.project.name);
    fs.mkdirSync(projectDir, { recursive: true });

    await gotoRoute(page, route.routePath, route.title);
    await page.screenshot({
      path: path.join(projectDir, `${routeSlug(route.routePath)}.png`),
      fullPage: true,
    });
  });
}
