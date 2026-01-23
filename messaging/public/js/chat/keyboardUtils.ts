// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Utility to temporarily suspend Frappe's global keyboard shortcuts
 * to prevent interference with chat input.
 */

declare const frappe: {
	ui: {
		keys: {
			handlers: Record<string, Array<(e: KeyboardEvent) => unknown>>;
			standard_shortcuts: Array<{ shortcut: string }>;
		};
	};
};

// Store original handlers when suspended
let suspendedHandlers: Record<string, Array<(e: KeyboardEvent) => unknown>> | null = null;
let isSuspended = false;

/**
 * Suspend all Frappe keyboard shortcuts.
 * Call this when the chat view becomes active.
 */
export function suspendFrappeKeyboardShortcuts(): void {
	if (isSuspended) return;

	// Store current handlers
	suspendedHandlers = { ...frappe.ui.keys.handlers };

	// Clear all handlers
	for (const key of Object.keys(frappe.ui.keys.handlers)) {
		frappe.ui.keys.handlers[key] = [];
	}

	isSuspended = true;
	console.log("[Chat] Frappe keyboard shortcuts suspended");
}

/**
 * Resume all Frappe keyboard shortcuts.
 * Call this when leaving the chat view.
 */
export function resumeFrappeKeyboardShortcuts(): void {
	if (!isSuspended || !suspendedHandlers) return;

	// Restore handlers
	for (const [key, handlers] of Object.entries(suspendedHandlers)) {
		frappe.ui.keys.handlers[key] = handlers;
	}

	suspendedHandlers = null;
	isSuspended = false;
	console.log("[Chat] Frappe keyboard shortcuts resumed");
}

/**
 * Check if shortcuts are currently suspended.
 */
export function areShortcutsSuspended(): boolean {
	return isSuspended;
}

/**
 * Stop propagation of keyboard events from chat inputs.
 * Attach this to the chat container to prevent events from reaching Frappe's handlers.
 */
export function createKeyboardBlocker(): (e: KeyboardEvent) => void {
	return (e: KeyboardEvent) => {
		const target = e.target as HTMLElement;
		const isInput =
			target.tagName === "INPUT" ||
			target.tagName === "TEXTAREA" ||
			target.isContentEditable ||
			target.closest('[contenteditable="true"]') ||
			target.closest(".vac-textarea") ||
			target.closest(".vac-room-footer");

		if (isInput) {
			// Stop the event from bubbling up to Frappe's window listener
			e.stopPropagation();
		}
	};
}
