// Copyright (c) 2025, Avunu LLC
// License: MIT. See license.txt

/**
 * Frappe Chat View Integration
 *
 * Registers ChatView as a standard Frappe list view that works at:
 * /desk/communication/view/chat
 *
 * This follows the same pattern as KanbanView, CalendarView, etc.
 */

import type {
	FrappeGenerateRouteItem,
	FrappeViewName,
	ListViewSelect as FrappeListViewSelect,
	ListViewSelectView,
	Page,
	PageContainerElement,
} from "frappe-types";
import { createApp, h, type Component, type App } from "vue";
import ChatViewComponent from "./ChatView.vue";

// frappe-ui Tailwind styles (processed by PostCSS/Tailwind pipeline, scoped under .messaging-chat-root).
// The editor's own styles come with `frappe-ui/editor`, which ChatFooter imports.
import "frappe-ui/style.css";
import {
	isPushSupported,
	getPermissionState,
	registerServiceWorker,
	subscribeToPush,
	unsubscribeFromPush,
	isSubscribed,
} from "./pushNotifications";

// ============================================================================
// Type Declarations
// ============================================================================

/** What frappe's ListFactory passes a list view's constructor. */
interface BaseListOptions {
	doctype: string;
	parent: HTMLElement;
}

/**
 * The "Chat" view mode: routed as `/desk/communication/view/chat` (registered with the router
 * below) and offered by the view switcher on Communication. frappe-types closes
 * `FrappeViewName` over frappe's own views, so the app's view is cast into it once, here.
 */
const CHAT_VIEW = "Chat" as FrappeViewName;

/** generate_route's item, with the Chat view a workspace shortcut can name. */
type ChatRouteItem = Omit<FrappeGenerateRouteItem, "doc_view"> & {
	doc_view?: FrappeGenerateRouteItem["doc_view"] | "Chat";
	route_options?: Record<string, string>;
};

// ============================================================================
// Namespaces
// ============================================================================

frappe.provide("frappe.views");
frappe.provide("frappe.router");

// ============================================================================
// ChatView - Standard Frappe List View (like KanbanView, CalendarView)
// ============================================================================

/**
 * ChatView is a standard Frappe list view that can be loaded via ListFactory.
 * Route: /desk/communication/view/chat
 *
 * This follows the TreeView pattern - creating its own page with single_column
 * layout for a clean, full-width chat interface.
 */
class ChatView {
	doctype: string;
	page_name: string;
	parent!: PageContainerElement;
	page!: Page;
	body!: JQuery<HTMLElement>;
	/** The composer the "New Email" menu item opened last. */
	composer: unknown = null;
	vueApp: App | null = null;
	container: HTMLElement | null = null;
	menu_items: Array<{ label: string; action: () => void; standard?: boolean }> = [];

	// Required by ListFactory/BaseList pattern
	start = 0;
	method = "";
	data: Record<string, unknown> = {};

	constructor(opts: BaseListOptions) {
		this.doctype = opts.doctype;
		this.page_name = frappe.get_route_str();

		// Create our own page with single_column layout (like TreeView)
		this.make_page();
		this.set_breadcrumbs();
		this.set_menu_items();
		this.render();

		// Set up push notification button in the page header (async)
		this.setup_push_notifications();
	}

	/**
	 * Create page structure with single_column layout.
	 * This follows the TreeView pattern for a clean, sidebar-free layout.
	 */
	make_page(): void {
		// Create a new page in the container (like TreeView does)
		this.parent = frappe.container.add_page(this.page_name);
		$(this.parent).addClass("chat-view");

		// Create app page with single_column layout
		frappe.ui.make_app_page({
			parent: this.parent,
			single_column: true,
		});

		this.page = this.parent.page as Page;
		frappe.container.change_to(this.page_name);

		// Set page title
		this.page.set_title(__("Messages"));

		// Style the main area - no padding, full height
		this.page.main.css({
			"min-height": "300px",
		});

		// Add frappe-card class for consistent styling
		this.page.main.addClass("frappe-card");

		this.body = this.page.main;
	}

	set_breadcrumbs(): void {
		const meta = frappe.get_meta(this.doctype);
		frappe.breadcrumbs.add(meta?.module || locals.DocType[this.doctype]?.module || "Core", this.doctype);
	}

	set_menu_items(): void {
		// View List menu item
		this.page.add_menu_item(__("View List"), () => {
			frappe.set_route("List", this.doctype, "List");
		});

		// New Email option if CommunicationComposer is available (frappe's composer opens its
		// dialog from the constructor)
		const Composer = frappe.views.CommunicationComposer as (new () => unknown) | undefined;
		if (Composer) {
			this.page.add_menu_item(__("New Email"), () => {
				this.composer = new Composer();
			});
		}

		// Refresh
		this.page.add_menu_item(__("Refresh"), () => {
			this.refresh();
		});
	}

	// -----------------------------------------------------------------------
	// Push notification button in the page header
	// -----------------------------------------------------------------------

	private pushBtn: JQuery<HTMLElement> | null = null;
	private pushSubscribed = false;
	private pushSubscribing = false;
	private readonly BANNER_DISMISSED_KEY = "messaging_push_banner_dismissed";

	/** Set up push notification button in the page header actions area. */
	async setup_push_notifications(): Promise<void> {
		if (!isPushSupported()) return;

		// Register the service worker early
		await registerServiceWorker();
		this.pushSubscribed = await isSubscribed();

		this.render_push_button();

		// If user has never been asked, show a one-time Frappe alert prompt
		if (
			!this.pushSubscribed &&
			getPermissionState() === "default" &&
			!localStorage.getItem(this.BANNER_DISMISSED_KEY)
		) {
			this.show_push_banner();
		}
	}

	/** Render or update the push notification toggle button in the page header. */
	private render_push_button(): void {
		// Remove existing button if present
		if (this.pushBtn) {
			this.pushBtn.remove();
			this.pushBtn = null;
		}

		const wrapper = $(this.parent).find(".custom-actions");
		wrapper.removeClass("hide").removeClass("hidden-xs").removeClass("hidden-md");

		const btn = document.createElement("button");
		btn.className = this.pushSubscribed
			? "btn btn-xs btn-success push-notification-btn"
			: "btn btn-xs btn-default push-notification-btn";
		btn.innerHTML = this.pushSubscribed
			? `<span>\uD83D\uDD15 ${__("Notifications On")}</span>`
			: `<span>\uD83D\uDD14 ${__("Enable Notifications")}</span>`;

		if (this.pushSubscribing) {
			btn.setAttribute("disabled", "true");
			btn.innerHTML = `<span>\uD83D\uDD14 ${__("Enabling...")}</span>`;
		}

		btn.addEventListener("click", () => {
			if (this.pushSubscribed) {
				this.disable_push();
			} else {
				this.enable_push();
			}
		});

		wrapper.append(btn);
		this.pushBtn = $(btn);
	}

	/** Show a one-time Frappe alert prompting the user to enable notifications. */
	private show_push_banner(): void {
		const banner = document.createElement("div");
		banner.className = "push-notification-banner";
		banner.style.cssText =
			"display:flex; align-items:center; justify-content:center; gap:12px; " +
			"padding:10px 16px; background:var(--alert-bg-info); " +
			"border-bottom:1px solid var(--border-color); font-size:var(--text-md); color:var(--alert-text-info);";
		banner.innerHTML =
			`<span>\uD83D\uDD14 ${__("Get notified when new messages arrive.")}</span>` +
			`<button class="btn btn-xs btn-primary push-banner-enable">${__("Enable")}</button>` +
			`<button class="btn btn-xs btn-default push-banner-dismiss">${__("Not now")}</button>`;

		// Insert before the page main content
		$(this.parent).find(".page-body").get(0)?.prepend(banner);

		banner.querySelector(".push-banner-enable")?.addEventListener("click", () => {
			banner.remove();
			this.enable_push();
		});

		banner.querySelector(".push-banner-dismiss")?.addEventListener("click", () => {
			banner.remove();
			localStorage.setItem(this.BANNER_DISMISSED_KEY, "1");
		});
	}

	private async enable_push(): Promise<void> {
		this.pushSubscribing = true;
		this.render_push_button();
		try {
			const success = await subscribeToPush();
			this.pushSubscribed = success;
			if (success) {
				frappe.show_alert({ message: __("Notifications enabled!"), indicator: "green" });
			} else {
				frappe.show_alert({
					message: __("Could not enable notifications. Check browser permissions."),
					indicator: "orange",
				});
			}
		} catch (err) {
			console.error("Failed to enable push:", err);
			frappe.show_alert({ message: __("Failed to enable notifications."), indicator: "red" });
		} finally {
			this.pushSubscribing = false;
			this.render_push_button();
		}
	}

	private async disable_push(): Promise<void> {
		const success = await unsubscribeFromPush();
		this.pushSubscribed = !success;
		if (success) {
			frappe.show_alert({ message: __("Notifications disabled."), indicator: "blue" });
		}
		this.render_push_button();
	}

	render(): void {
		// Clear body
		this.body.empty();

		// Unmount existing Vue app if present
		if (this.vueApp) {
			this.vueApp.unmount();
			this.vueApp = null;
		}

		// Create Vue container
		this.container = document.createElement("div");
		this.container.id = "chat-view-container";
		this.container.classList.add("messaging-chat-root");
		this.container.style.height = "calc(100vh - 46px)";
		this.container.style.minHeight = "500px";
		this.body.append(this.container);

		// Mount Vue chat application
		this.vueApp = createApp({
			render: () => h(ChatViewComponent as Component),
		});

		this.vueApp.mount(this.container);
	}

	refresh(): void {
		this.render();
	}

	show(): void {
		// Switch to our page
		frappe.container.change_to(this.page_name);
	}

	hide(): void {
		// Unmount Vue app when hiding to clean up
		if (this.vueApp) {
			this.vueApp.unmount();
			this.vueApp = null;
		}
	}

	// Required stubs for BaseList compatibility
	setup_defaults(): void {}
	setup_page(): void {}
	setup_page_head(): void {}
	set_primary_action(): void {}
	render_header(): void {}
	before_show(): Promise<void> {
		return Promise.resolve();
	}
	before_render(): void {}
	after_render(): void {}
	on_filter_change(): void {}
	toggle_result_area(): void {}
	before_refresh(): void {}
	get_args(): Record<string, unknown> {
		return {};
	}
	call_for_data(): Promise<unknown> {
		return Promise.resolve([]);
	}
	prepare_data(): void {}
	get_count_str(): string {
		return "";
	}
	freeze(): void {}
	init(): Promise<void> {
		return Promise.resolve();
	}
}

// ============================================================================
// Registration - Register Chat as a standard list view
// ============================================================================

// Register ChatView class so ListFactory can find it
frappe.views.ChatView = ChatView;

// Register 'chat' in list_views array (lowercase)
if (!frappe.router.list_views.includes("chat")) {
	frappe.router.list_views.push("chat");
}

// Register 'chat' -> 'Chat' mapping in list_views_route
// This maps /communication/view/chat to ['List', 'Communication', 'Chat']
frappe.router.list_views_route["chat"] = "Chat";

// ============================================================================
// Override generate_route to support Chat view
// ============================================================================

/**
 * Override frappe.utils.generate_route to handle Chat doc_view
 */
const originalGenerateRoute = frappe.utils.generate_route;

frappe.utils.generate_route = function (this: unknown, routeItem: FrappeGenerateRouteItem): string {
	const item = routeItem as ChatRouteItem;
	// Handle Chat doc_view for doctype items
	if (item.type?.toLowerCase() === "doctype" && item.doc_view === "Chat") {
		const doctype_slug = frappe.router.slug(item.doctype || item.name || "");
		let route = `${doctype_slug}/view/chat`;
		if (item.tab) {
			route += `#${item.tab}`;
		}
		if (item.route_options) {
			route +=
				"?" +
				Object.entries(item.route_options)
					.map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
					.join("&");
		}
		return `/desk/${route}`;
	}

	// Fall back to original implementation
	return originalGenerateRoute.call(this, routeItem);
};

// ============================================================================
// The view switcher - offer Chat on Communication
// ============================================================================

/**
 * Offers the Chat view in frappe's view switcher.
 *
 * frappe 16's switcher lists the views `get_views()` returns, in the order of
 * `frappe.views.view_modes`, and marks the one the route names as current, so the Chat view
 * mode is registered in both, with its icon and label. (frappe 15's `setup_views` hook,
 * which this used to override, no longer exists.) It extends whichever ListViewSelect is
 * installed when this bundle loads, so another app's switcher keeps its own views.
 */
function extendListViewSelect(): void {
	const BaseListViewSelect = frappe.views.ListViewSelect;
	if (!BaseListViewSelect) return;

	class ChatViewSelect extends BaseListViewSelect {
		override set_current_view(): void {
			// The constructor calls this first, before it builds the switcher from the label map.
			this.label_map[CHAT_VIEW] = __("Chat View");
			super.set_current_view();
		}

		override get_views(): ReturnType<FrappeListViewSelect["get_views"]> {
			const chat: ListViewSelectView = {
				condition: this.doctype === "Communication",
				action: () => this.set_route("chat"),
			};
			return { ...super.get_views(), [CHAT_VIEW]: chat };
		}
	}

	frappe.views.ListViewSelect = ChatViewSelect;
}

if (!frappe.views.view_modes?.includes(CHAT_VIEW)) {
	frappe.views.view_modes?.push(CHAT_VIEW);
}
if (frappe.views.view_icon_map) frappe.views.view_icon_map[CHAT_VIEW] = "message-circle";

// Initialize ListViewSelect extension
extendListViewSelect();

// ============================================================================
// Exports
// ============================================================================

export { ChatView };
export default ChatView;
