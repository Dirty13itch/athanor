import { expect, test } from "@playwright/test";
import { gotoRoute, resetBrowserState } from "./helpers";

test.beforeEach(async ({ page }) => {
  await resetBrowserState(page);
});

test("opens the command palette from the keyboard shortcut", async ({ page }) => {
  await gotoRoute(page, "/", "Command Center");

  await page.keyboard.press("Control+K");
  await expect(page.getByRole("dialog", { name: "Command palette" })).toBeAttached();
  await expect(page.getByPlaceholder("Jump to a route, tool, or priority item")).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Command palette" })).not.toBeVisible();
});

test("registers the service worker and completes the push subscription round-trip", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const state = {
      registeredUrl: "",
      currentSubscription: null as null | {
        endpoint: string;
        keys: { p256dh: string; auth: string };
        toJSON: () => {
          endpoint: string;
          keys: { p256dh: string; auth: string };
        };
        unsubscribe: () => Promise<boolean>;
      },
    };

    const registration = {
      pushManager: {
        getSubscription: async () => state.currentSubscription,
        subscribe: async () => {
          state.currentSubscription = {
            endpoint: "https://push.example.test/subscription",
            keys: {
              p256dh: "fixture-p256dh",
              auth: "fixture-auth",
            },
            toJSON() {
              return {
                endpoint: this.endpoint,
                keys: this.keys,
              };
            },
            unsubscribe: async () => {
              state.currentSubscription = null;
              return true;
            },
          };
          return state.currentSubscription;
        },
      },
    };

    Object.defineProperty(window, "__athanorPushState", {
      configurable: true,
      value: state,
    });

    Object.defineProperty(window, "PushManager", {
      configurable: true,
      value: class MockPushManager {},
    });

    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: {
        ready: Promise.resolve(registration),
        register: async (url: string) => {
          state.registeredUrl = url;
          return registration;
        },
      },
    });
  });

  await gotoRoute(page, "/preferences", "Preferences");

  await expect
    .poll(() =>
      page.evaluate(() => (window as typeof window & { __athanorPushState?: { registeredUrl: string } }).__athanorPushState?.registeredUrl ?? "")
    )
    .toBe("/sw.js");

  const subscribeRequest = page.waitForRequest("**/api/push/subscribe");
  await page.getByRole("button", { name: "Enable" }).click();
  const request = await subscribeRequest;

  expect(request.method()).toBe("POST");
  expect(request.postDataJSON()).toMatchObject({
    endpoint: "https://push.example.test/subscription",
    keys: {
      p256dh: "fixture-p256dh",
      auth: "fixture-auth",
    },
  });

  await expect(page.getByRole("button", { name: "Disable" })).toBeVisible();
});
