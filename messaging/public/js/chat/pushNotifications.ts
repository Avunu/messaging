// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Push notification client module.
 *
 * Handles:
 * - Service worker registration
 * - Notification permission requests
 * - Push subscription management (subscribe / unsubscribe)
 * - VAPID public key retrieval from server
 */

// Frappe global
declare const frappe: {
  call: <T>(options: {
    method: string;
    args?: Record<string, unknown>;
  }) => Promise<{ message: T }>;
  xcall: <T>(method: string, args?: Record<string, unknown>) => Promise<T>;
  show_alert: (options: { message: string; indicator?: string }) => void;
};

const PUSH_API = 'messaging.messaging.api.chat.push';

// ---------------------------------------------------------------------------
// Feature detection
// ---------------------------------------------------------------------------

/** Check if the browser supports push notifications. */
export function isPushSupported(): boolean {
  return (
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  );
}

/** Current notification permission state. */
export function getPermissionState(): NotificationPermission {
  if (!('Notification' in window)) return 'denied';
  return Notification.permission;
}

// ---------------------------------------------------------------------------
// Service Worker
// ---------------------------------------------------------------------------

let swRegistration: ServiceWorkerRegistration | null = null;

/**
 * Register (or retrieve) the messaging service worker.
 * The SW file is served as a static asset from /assets/messaging/js/chat/sw-messaging.js
 */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) return null;

  try {
    swRegistration = await navigator.serviceWorker.register(
      '/assets/messaging/js/chat/sw-messaging.js',
      { scope: '/app/' }
    );
    console.log('[Messaging] Service worker registered:', swRegistration.scope);

    // Listen for messages from the SW (e.g. navigate-to-room)
    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data?.type === 'NAVIGATE_TO_CHAT' && event.data.room_id) {
        // Dispatch a custom event so ChatView can react
        window.dispatchEvent(
          new CustomEvent('messaging:navigate', {
            detail: { room_id: event.data.room_id },
          })
        );
      }
    });

    return swRegistration;
  } catch (err) {
    console.error('[Messaging] Service worker registration failed:', err);
    return null;
  }
}

// ---------------------------------------------------------------------------
// VAPID key
// ---------------------------------------------------------------------------

let cachedVapidKey: string | null = null;

async function getVapidPublicKey(): Promise<string> {
  if (cachedVapidKey) return cachedVapidKey;

  const key = await frappe.xcall<string>(`${PUSH_API}.get_vapid_public_key`);
  cachedVapidKey = key;
  return key;
}

/**
 * Convert a base64url-encoded string to a Uint8Array
 * (needed for PushManager.subscribe applicationServerKey).
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

// ---------------------------------------------------------------------------
// Subscribe / Unsubscribe
// ---------------------------------------------------------------------------

/**
 * Request notification permission and subscribe for push.
 * Returns true if the subscription was successful.
 */
export async function subscribeToPush(): Promise<boolean> {
  if (!isPushSupported()) {
    console.warn('[Messaging] Push notifications are not supported in this browser.');
    return false;
  }

  // 1. Request permission
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    console.log('[Messaging] Notification permission denied.');
    return false;
  }

  // 2. Register SW if needed
  if (!swRegistration) {
    swRegistration = await registerServiceWorker();
  }
  if (!swRegistration) return false;

  // 3. Get VAPID key from server
  const vapidKey = await getVapidPublicKey();
  if (!vapidKey) {
    console.error('[Messaging] VAPID public key not available.');
    return false;
  }

  // 4. Subscribe to push
  try {
    const subscription = await swRegistration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey) as BufferSource,
    });

    // 5. Send subscription to server
    await frappe.xcall(`${PUSH_API}.save_push_subscription`, {
      subscription: JSON.stringify(subscription.toJSON()),
    });

    console.log('[Messaging] Push subscription saved.');
    return true;
  } catch (err) {
    console.error('[Messaging] Push subscribe failed:', err);
    return false;
  }
}

/**
 * Unsubscribe from push notifications.
 */
export async function unsubscribeFromPush(): Promise<boolean> {
  if (!swRegistration) {
    swRegistration =
      (await navigator.serviceWorker?.getRegistration('/')) ?? null;
  }
  if (!swRegistration) return true;

  try {
    const subscription = await swRegistration.pushManager.getSubscription();
    if (subscription) {
      await subscription.unsubscribe();
      // Tell the server to remove the subscription
      await frappe.xcall(`${PUSH_API}.remove_push_subscription`, {
        endpoint: subscription.endpoint,
      });
    }
    console.log('[Messaging] Push unsubscribed.');
    return true;
  } catch (err) {
    console.error('[Messaging] Push unsubscribe failed:', err);
    return false;
  }
}

/**
 * Check if the user currently has an active push subscription.
 */
export async function isSubscribed(): Promise<boolean> {
  if (!isPushSupported()) return false;
  if (getPermissionState() !== 'granted') return false;

  if (!swRegistration) {
    swRegistration =
      (await navigator.serviceWorker?.getRegistration('/')) ?? null;
  }
  if (!swRegistration) return false;

  const subscription = await swRegistration.pushManager.getSubscription();
  return subscription !== null;
}

export default {
  isPushSupported,
  getPermissionState,
  registerServiceWorker,
  subscribeToPush,
  unsubscribeFromPush,
  isSubscribed,
};
