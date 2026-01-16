// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Frappe Chat View Integration
 *
 * Standalone Chat view using Factory pattern (like TreeView).
 * Route: /Chat/Communication - completely bypasses ListView/BaseList.
 */

import { createApp, h, type Component, type App } from 'vue';
import ChatViewComponent from './ChatView.vue';

// ============================================================================
// Type Declarations
// ============================================================================

interface JQueryElement {
  find(selector: string): JQueryElement;
  remove(): JQueryElement;
  empty(): JQueryElement;
  append(element: HTMLElement | string): JQueryElement;
  appendTo(target: JQueryElement | HTMLElement): JQueryElement;
  addClass(className: string): JQueryElement;
  removeClass(className: string): JQueryElement;
  css(styles: Record<string, string>): JQueryElement;
  html(content?: string): string | JQueryElement;
  hide(): JQueryElement;
  show(): JQueryElement;
  on(event: string, handler: (e: Event) => void): JQueryElement;
}

interface FrappePage {
  set_title(title: string): void;
  set_primary_action(label: string, callback: () => void, icon?: string): JQueryElement;
  add_menu_item(label: string, callback: () => void): void;
  main: JQueryElement;
  wrapper: JQueryElement;
}

interface FrappeContainer {
  add_page(label: string): HTMLElement & { page: FrappePage };
  change_to(label: string): void;
}

interface FrappeUI {
  make_app_page(opts: { parent: HTMLElement; single_column?: boolean }): void;
}

interface FrappeModel {
  with_doctype(doctype: string, callback: () => void): void;
  can_read(doctype: string): boolean;
}

interface FrappeBreadcrumbs {
  add(module: string, doctype?: string): void;
}

// Factory base class type
interface FactoryBase {
  make(route: string[]): void;
  show(): void;
  on_show?(): void;
}

type FactoryConstructor = new () => FactoryBase;

// ListViewSelect type
interface ListViewSelectBase {
  doctype: string;
  setup_views(): void;
  add_view_to_menu(view: string, action: () => void): void;
}

type ListViewSelectConstructor = new (opts: unknown) => ListViewSelectBase;

interface FrappeViews {
  Factory: FactoryConstructor;
  ChatFactory?: FactoryConstructor;
  ListViewSelect?: ListViewSelectConstructor;
  chats?: Record<string, ChatView>;
  CommunicationComposer?: new () => unknown;
  [key: string]: unknown;
}

declare const frappe: {
  provide(namespace: string): void;
  views: FrappeViews;
  container: FrappeContainer;
  ui: FrappeUI;
  model: FrappeModel;
  breadcrumbs: FrappeBreadcrumbs;
  get_route(): string[];
  get_route_str(): string;
  router: {
    factory_views: string[];
    list_views: string[];
    list_views_route: Record<string, string>;
  };
  set_route(route: string | string[]): void;
  show_alert(opts: { message: string; indicator: string }): void;
  boot: {
    user: {
      can_read: string[];
    };
  };
};

declare const locals: {
  DocType: Record<string, { module: string }>;
};

declare const $: {
  (selector: string | HTMLElement): JQueryElement;
};

declare const __: (text: string, args?: unknown[]) => string;

// ============================================================================
// Namespaces
// ============================================================================

frappe.provide('frappe.views');
frappe.provide('frappe.views.chats');
frappe.provide('frappe.router');

// ============================================================================
// ChatFactory - Handles /Chat/Communication routes (like TreeFactory)
// ============================================================================

/**
 * ChatFactory handles routing for /Chat/{doctype} routes.
 * Completely bypasses ListFactory and BaseList.
 */
class ChatFactory extends frappe.views.Factory {
  make(route: string[]): void {
    const doctype = route[1];

    frappe.model.with_doctype(doctype, () => {
      // Only allow Chat view for Communication doctype
      if (doctype !== 'Communication') {
        frappe.show_alert({
          message: __('Chat view is only available for Communications'),
          indicator: 'orange',
        });
        frappe.set_route(['List', doctype, 'List']);
        return;
      }

      // Create or reuse ChatView instance
      if (!frappe.views.chats) {
        frappe.views.chats = {};
      }

      if (!frappe.views.chats[doctype]) {
        frappe.views.chats[doctype] = new ChatView({ doctype });
      } else {
        // Show existing view
        frappe.views.chats[doctype].show();
      }
    });
  }

  on_show(): void {
    // Called when navigating back to the view
    const route = frappe.get_route();
    const chatView = frappe.views.chats?.[route[1]];
    if (chatView) {
      chatView.show();
    }
  }
}

// ============================================================================
// ChatView - Standalone view class (like TreeView)
// ============================================================================

/**
 * ChatView creates its own page and renders the Vue chat component.
 * No ListView/BaseList inheritance - completely standalone.
 */
class ChatView {
  doctype: string;
  page_name: string;
  parent!: HTMLElement & { page: FrappePage };
  page!: FrappePage;
  body!: JQueryElement;
  vueApp: App | null = null;
  container: HTMLElement | null = null;

  constructor(opts: { doctype: string }) {
    this.doctype = opts.doctype;
    this.page_name = frappe.get_route_str();

    this.make_page();
    this.set_menu_items();
    this.render();
  }

  make_page(): void {
    // Create a new page in the container
    this.parent = frappe.container.add_page(this.page_name);
    $(this.parent).addClass('chat-view');

    // Create app page structure
    frappe.ui.make_app_page({
      parent: this.parent,
      single_column: true,
    });

    this.page = this.parent.page;
    frappe.container.change_to(this.page_name);

    // Set breadcrumbs
    frappe.breadcrumbs.add(
      locals.DocType[this.doctype]?.module || 'Core',
      this.doctype
    );

    // Set page title
    this.page.set_title(__('Messages'));

    // Style the main area - no padding, full height
    this.page.main.css({
      'min-height': '500px',
      padding: '0',
    });

    // Add frappe-card class for consistent styling
    this.page.main.addClass('frappe-card');

    this.body = this.page.main;
  }

  set_menu_items(): void {
    // View List menu item
    this.page.add_menu_item(__('View List'), () => {
      frappe.set_route(['List', this.doctype, 'List']);
    });

    // New Email option if CommunicationComposer is available
    if (frappe.views.CommunicationComposer) {
      this.page.add_menu_item(__('New Email'), () => {
        new (frappe.views.CommunicationComposer as new () => unknown)();
      });
    }

    // Refresh
    this.page.add_menu_item(__('Refresh'), () => {
      this.refresh();
    });
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
    this.container = document.createElement('div');
    this.container.id = 'chat-view-container';
    this.container.style.height = 'calc(100vh - 120px)';
    this.container.style.minHeight = '500px';
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
    frappe.container.change_to(this.page_name);
  }
}

// ============================================================================
// ListViewSelect Extension - Adds Chat to dropdown for Communication
// ============================================================================

/**
 * Extends ListViewSelect to add Chat view option.
 * Routes to /Chat/Communication instead of /communication/view/chat
 */
function extendListViewSelect(): void {
  const OriginalListViewSelect = frappe.views.ListViewSelect;

  if (OriginalListViewSelect) {
    const ChatViewSelect = class extends OriginalListViewSelect {
      setup_views(): void {
        super.setup_views();

        // Add Chat view for Communication doctype
        if (this.doctype === 'Communication') {
          // Use add_view_to_menu but with custom routing
          this.add_view_to_menu(__('Chat'), () => {
            // Route to /Chat/Communication (factory route, not list view route)
            frappe.set_route(['Chat', 'Communication']);
          });
        }
      }
    };

    frappe.views.ListViewSelect = ChatViewSelect as unknown as ListViewSelectConstructor;
  }
}

// ============================================================================
// Registration
// ============================================================================

// Register ChatFactory
frappe.views.ChatFactory = ChatFactory as unknown as FactoryConstructor;

// Register 'chat' in factory_views - this makes /Chat/... routes use ChatFactory
// (similar to how 'tree' makes /Tree/... routes use TreeFactory)
if (!frappe.router.factory_views.includes('chat')) {
  frappe.router.factory_views.push('chat');
}

// Extend ListViewSelect to add Chat option in the dropdown
extendListViewSelect();

// ============================================================================
// Exports
// ============================================================================

export { ChatFactory, ChatView };
export default ChatFactory;
