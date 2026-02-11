// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Service Worker for Messaging push notifications.
 *
 * Handles push events from the server and displays native OS notifications
 * for incoming messages. Clicking a notification navigates to the chat view.
 */

/* eslint-env serviceworker */
/* global clients */

const NOTIFICATION_TAG_PREFIX = "messaging-chat-";

/**
 * Handle incoming push events from the server.
 */
self.addEventListener("push", (event) => {
	if (!event.data) return;

	let payload;
	try {
		payload = event.data.json();
	} catch {
		payload = { title: "New Message", body: event.data.text() };
	}

	const title = payload.title || "New Message";
	const options = {
		body: payload.body || "",
		icon: payload.icon || "/assets/messaging/images/message-icon.png",
		badge: payload.badge || "/assets/messaging/images/badge-icon.png",
		tag:
			payload.tag ||
			NOTIFICATION_TAG_PREFIX + (payload.room_id || "general"),
		renotify: true,
		requireInteraction: false,
		data: {
			room_id: payload.room_id || "",
			communication_name: payload.communication_name || "",
			url: payload.url || "/app/communication/view/chat",
		},
		actions: [
			{ action: "open", title: "Open" },
			{ action: "dismiss", title: "Dismiss" },
		],
	};

	event.waitUntil(self.registration.showNotification(title, options));
});

/**
 * Handle notification click — open or focus the chat view.
 */
self.addEventListener("notificationclick", (event) => {
	event.notification.close();

	if (event.action === "dismiss") return;

	const targetUrl =
		event.notification.data?.url || "/app/communication/view/chat";

	event.waitUntil(
		clients
			.matchAll({ type: "window", includeUncontrolled: true })
			.then((windowClients) => {
				// Try to focus an existing tab with the app open
				for (const client of windowClients) {
					if (client.url.includes("/app") && "focus" in client) {
						client.focus();
						client.postMessage({
							type: "NAVIGATE_TO_CHAT",
							room_id: event.notification.data?.room_id || "",
						});
						return;
					}
				}
				// No existing tab — open a new one
				if (clients.openWindow) {
					return clients.openWindow(targetUrl);
				}
			}),
	);
});

/**
 * Handle push subscription change (e.g. browser rotates keys).
 */
self.addEventListener("pushsubscriptionchange", (event) => {
	event.waitUntil(
		self.registration.pushManager
			.subscribe(event.oldSubscription.options)
			.then((subscription) => {
				// Re-register with the server
				return fetch(
					"/api/method/messaging.messaging.api.chat.push.save_push_subscription",
					{
						method: "POST",
						headers: { "Content-Type": "application/json" },
						body: JSON.stringify({
							subscription: JSON.stringify(subscription),
						}),
					},
				);
			}),
	);
});
