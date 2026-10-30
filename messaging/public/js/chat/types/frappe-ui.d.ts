// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

/**
 * Type surface of `frappe-ui` as the chat view uses it.
 *
 * frappe-ui ships raw TypeScript and Vue sources that don't pass this repo's strict compiler
 * settings, so `tsconfig.json` maps the package to this declaration instead of type-checking the
 * library (as erpnext_taskview's portal does). Vite still bundles the real package: it doesn't read
 * tsconfig paths. Add an export here when the chat view starts using another component.
 */

import type { Editor } from "@tiptap/core";
import type { DefineComponent } from "vue";

/** frappe-ui's TipTap-based rich text editor; the chat footer reads its `editor` and `rootRef`. */
export const TextEditor: DefineComponent<Record<string, unknown>> & {
	new (): { editor: Editor | null; rootRef: HTMLElement | null };
};
