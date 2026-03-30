import { expect, test } from "@playwright/test";
import { loadApiAuditRecords } from "./census";

const SAFE_GET_APIS = loadApiAuditRecords().filter((api) => {
  if (!api.methods.includes("GET")) {
    return false;
  }
  if (api.apiPath.includes(":")) {
    return false;
  }
  if (api.responseMode !== "json") {
    return false;
  }
  if (api.accessClass !== "public") {
    return false;
  }
  if (api.completionStatus !== "live_complete") {
    return false;
  }
  return api.consumerStatus !== "orphan-candidate";
});

for (const api of SAFE_GET_APIS) {
  test(`api census: ${api.apiPath} returns a non-error response`, async ({ request }) => {
    const response = await request.get(api.apiPath);
    expect(response.status(), `${api.apiPath} returned ${response.status()}`).toBeLessThan(500);
    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(typeof body).toBe("object");
  });
}
