import "server-only";

export interface PushSubscriptionRecord {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
}

// Process-local store for the single-user dashboard deployment.
const subscriptions = new Map<string, PushSubscriptionRecord>();

export function upsertPushSubscription(subscription: PushSubscriptionRecord): number {
  subscriptions.set(subscription.endpoint, subscription);
  return subscriptions.size;
}

export function removePushSubscription(endpoint: string): void {
  subscriptions.delete(endpoint);
}

export function listPushSubscriptions(): PushSubscriptionRecord[] {
  return Array.from(subscriptions.values());
}
