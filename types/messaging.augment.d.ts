// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

// What this app adds to frappe's desk namespaces, and the frappe members frappe-types 16.5.0
// does not declare yet. frappe's own globals come from frappe-types; nothing here redeclares them.

import type { Container } from "frappe-types";

declare module "frappe-types" {
	interface FrappeViewsNamespace {
		// app-owned: the Chat list view class chat/bundle.ts sets, routed as `communication/view/chat` (typed by its constructor, so desk scripts need not load the bundle's sources)
		ChatView?: new (opts: { doctype: string; parent: HTMLElement }) => object;
	}

	interface Form<DT extends string = string> {
		// app-owned: frappe's own Form.savesubmit (form/form.js:929), missing from frappe-types 16.5.0; DT is Form's own parameter
		savesubmit(btn?: HTMLElement | JQuery, callback?: () => void, on_error?: () => void): Promise<Form<DT>>;
	}

	interface Frappe {
		// app-owned: frappe's own page container (views/container.js), missing from frappe-types 16.5.0, which types only its class
		container: Container;
		// app-owned: frappe's own breadcrumbs (views/breadcrumbs.js), missing from frappe-types 16.5.0
		breadcrumbs: { add(module: string, doctype?: string, type?: string): void };
	}
}
