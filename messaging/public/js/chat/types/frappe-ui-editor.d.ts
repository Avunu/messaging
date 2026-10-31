// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

/**
 * Type surface of `frappe-ui/editor` as the chat view uses it.
 *
 * frappe-ui ships raw TypeScript and Vue sources that don't pass this repo's strict compiler
 * settings, so `tsconfig.json` maps the package to this declaration instead of type-checking the
 * library (as ui_text_editor does). Vite still bundles the real package: it doesn't read tsconfig
 * paths. Add an export here when the chat view starts using another part of the editor.
 */

import type { Editor as TiptapEditor, Extension } from "@tiptap/core";
import type { DefineComponent } from "vue";

export type { TiptapEditor };

/**
 * The renderless editor: owns the TipTap instance and v-model, and exposes `editor` (the live
 * instance, null until it is created) and `isEmpty` to a template ref.
 */
export const Editor: DefineComponent<Record<string, unknown>> & {
	new (): { editor: TiptapEditor | null; isEmpty: boolean };
};

/** The editable area; inside `<Editor>` it renders that editor without an `editor` prop. */
export const EditorContent: DefineComponent<Record<string, unknown>>;

/** frappe-ui's StarterKit: TipTap's, without code, code blocks and links (see `Link`). */
export const StarterKit: Extension<{ heading?: false; [member: string]: unknown }>;

/** Placeholder text, which `<Editor>` fills in from its `placeholder` prop. */
export const Placeholder: Extension;

/** Links, with frappe-ui's autolinking and paste handling. */
export const Link: Extension;
