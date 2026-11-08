// Copyright (c) 2026, Avunu LLC and contributors
// For license information, please see license.txt

// What this app adds to frappe's desk namespaces. frappe's own globals come from frappe-types;
// nothing here redeclares them.

import type { ListFactoryViewOptions } from "frappe-types";

declare module "frappe-types" {
	interface FrappeViewsNamespace {
		// app-owned: the Chat list view class chat/bundle.ts sets, routed as `communication/view/chat` (typed by its constructor, so desk scripts need not load the bundle's sources)
		ChatView?: new (opts: ListFactoryViewOptions) => object;
	}

	interface FrappeViewModes {
		// app-owned: the Chat view mode chat/bundle.ts adds to frappe.views.view_modes and the view switcher
		Chat: true;
	}

	interface FrappeGenerateRouteDocViews {
		// app-owned: the Chat doc_view chat/bundle.ts's generate_route wrapper routes to `<doctype>/view/chat`
		Chat: true;
	}
}
