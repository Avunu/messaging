// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

import type { Action, ShotSpec } from "./shots.d.ts";

// The demo from messaging/demo.py. Group Text Messages are named by hash, so the form is opened by
// its title.
const CHAT = "/app/communication/view/chat";
const ROOM = ".vac-room-item";
// The banner that offers push notifications until a user answers it: "Not now" dismisses it.
const DISMISS_PUSH_BANNER: Action = { eval: "document.querySelector('.push-banner-dismiss')?.click();" };

// Open the thread whose name contains `name`.
function openRoom(name: string): Action[] {
	return [
		{ wait: 500 },
		DISMISS_PUSH_BANNER,
		{
			eval: `[...document.querySelectorAll(${JSON.stringify(ROOM)})].find((el) => el.textContent.includes(${JSON.stringify(name)}))?.click();`,
		},
		{ waitFor: ".vac-message-wrapper" },
		{ wait: 1000 },
	];
}

function openGroupText(title: string): Action[] {
	return [
		{
			eval: `frappe.db.get_value("Group Text Message", { message_title: ${JSON.stringify(title)} }, "name").then((r) => frappe.set_route("Form", "Group Text Message", r.message.name));`,
		},
		{ waitFor: '.frappe-control[data-fieldname="message"]' },
		{ wait: 800 },
	];
}

export default {
	demo: { date: "2026-01-15", seed: 1 },
	shots: [
		{
			name: "chat",
			route: CHAT,
			alt: "The chat view: SMS and e-mail threads with unread counts on the left, and an SMS conversation with its reply box on the right",
			waitFor: ROOM,
			actions: [...openRoom("Dana"), { eval: "document.activeElement?.blur();" }],
			readme: "hero",
			featured: true,
		},
		{
			name: "contact-panel",
			route: CHAT,
			alt: "The contact panel beside an e-mail thread, with the contact's e-mail address, mobile number and linked documents",
			waitFor: ROOM,
			actions: [
				...openRoom("Ravi"),
				{ click: ".vac-room-header .vac-info-wrapper" },
				{ waitFor: ".contact-panel" },
				{ wait: 1200 },
			],
			readme: "feature",
			featured: true,
		},
		{
			name: "group-text",
			route: "/app/group-text-message",
			alt: "A sent Group Text Message to the Volunteers group, with the comment that lists who received it",
			waitFor: ".list-row-container, .no-result",
			actions: openGroupText("Community dinner"),
			mask: [".frappe-timestamp"],
			readme: "feature",
			featured: true,
		},
		{
			name: "messaging-group",
			route: "/app/messaging-group/Volunteers",
			alt: "The Volunteers Messaging Group with its member contacts",
			waitFor: '.frappe-control[data-fieldname="members"]',
			actions: [{ wait: 800 }],
			mask: [".frappe-timestamp"],
			readme: "feature",
		},
	],
} satisfies ShotSpec;
