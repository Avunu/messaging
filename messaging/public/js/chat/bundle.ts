// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Frappe Chat View Integration
 *
 * Registers ChatView as a standard Frappe list view that works at:
 * /desk/communication/view/chat
 *
 * This follows the same pattern as KanbanView, CalendarView, etc.
 */

import { createApp, h, type Component, type App } from 'vue';
import ChatViewComponent from './ChatView.vue';
import {
  suspendFrappeKeyboardShortcuts,
  resumeFrappeKeyboardShortcuts,
} from './keyboardUtils';

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
  get(index: number): HTMLElement;
}

interface FrappePage {
  set_title(title: string): void;
  set_primary_action(label: string, callback: () => void, icon?: string): JQueryElement;
  add_menu_item(label: string, callback: () => void): void;
  clear_menu(): void;
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

// ListViewSelect type
interface ListViewSelectBase {
  doctype: string;
  setup_views(): void;
  add_view_to_menu(view: string, action: () => void): void;
  set_current_view(): void;
  current_view?: string;
}

type ListViewSelectConstructor = new (opts: unknown) => ListViewSelectBase;

interface FrappeViews {
  ChatView?: new (opts: BaseListOptions) => ChatView;
  ListViewSelect?: ListViewSelectConstructor;
  CommunicationComposer?: new () => unknown;
  [key: string]: unknown;
}

interface BaseListOptions {
  doctype: string;
  parent: HTMLElement;
}

interface GenerateRouteItem {
  type: string;
  name: string;
  doctype?: string;
  link?: string;
  doc_view?: string;
  filters?: Record<string, unknown>;
  kanban_board?: string;
  tab?: string;
  is_query_report?: boolean;
  report_ref_doctype?: string;
  route?: string;
  route_options?: Record<string, string>;
}

declare const frappe: {
  provide(namespace: string): void;
  views: FrappeViews;
  model: FrappeModel;
  container: FrappeContainer;
  ui: FrappeUI;
  breadcrumbs: FrappeBreadcrumbs;
  get_route(): string[];
  get_route_str(): string;
  router: {
    slug(doctype: string): string;
    factory_views: string[];
    list_views: string[];
    list_views_route: Record<string, string>;
    route?: () => Promise<void>;
    on?: (event: string, callback: () => void) => void;
  };
  utils: {
    generate_route(item: GenerateRouteItem): string;
  };
  set_route(...args: (string | string[])[]): void;
  show_alert(opts: { message: string; indicator: string }): void;
  boot: {
    user: {
      can_read: string[];
    };
  };
  route_options?: Record<string, unknown> | null;
  get_meta(doctype: string): { module: string } | null;
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
frappe.provide('frappe.router');

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
  parent!: HTMLElement & { page: FrappePage };
  page!: FrappePage;
  body!: JQueryElement;
  vueApp: App | null = null;
  container: HTMLElement | null = null;
  menu_items: Array<{ label: string; action: () => void; standard?: boolean }> = [];

  // Required by ListFactory/BaseList pattern
  start = 0;
  method = '';
  data: Record<string, unknown> = {};

  constructor(opts: BaseListOptions) {
    this.doctype = opts.doctype;
    this.page_name = frappe.get_route_str();

    // Create our own page with single_column layout (like TreeView)
    this.make_page();
    this.set_breadcrumbs();
    this.set_menu_items();
    this.render();
  }

  /**
   * Create page structure with single_column layout.
   * This follows the TreeView pattern for a clean, sidebar-free layout.
   */
  make_page(): void {
    // Create a new page in the container (like TreeView does)
    this.parent = frappe.container.add_page(this.page_name);
    $(this.parent).addClass('chat-view');

    // Create app page with single_column layout
    frappe.ui.make_app_page({
      parent: this.parent,
      single_column: true,
    });

    this.page = this.parent.page;
    frappe.container.change_to(this.page_name);

    // Set page title
    this.page.set_title(__('Messages'));

    // Style the main area - no padding, full height
    this.page.main.css({
      'min-height': '300px',
    });

    // Add frappe-card class for consistent styling
    this.page.main.addClass('frappe-card');

    this.body = this.page.main;
  }

  set_breadcrumbs(): void {
    const meta = frappe.get_meta(this.doctype);
    frappe.breadcrumbs.add(
      meta?.module || locals.DocType[this.doctype]?.module || 'Core',
      this.doctype
    );
  }

  set_menu_items(): void {
    // View List menu item
    this.page.add_menu_item(__('View List'), () => {
      frappe.set_route('List', this.doctype, 'List');
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
    this.container.style.height = 'calc(100vh - 46px)';
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
    // Suspend Frappe keyboard shortcuts when showing chat view
    suspendFrappeKeyboardShortcuts();

    // Switch to our page
    frappe.container.change_to(this.page_name);
  }

  hide(): void {
    // Resume Frappe keyboard shortcuts when hiding
    resumeFrappeKeyboardShortcuts();

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
  before_show(): Promise<void> { return Promise.resolve(); }
  before_render(): void {}
  after_render(): void {}
  on_filter_change(): void {}
  toggle_result_area(): void {}
  before_refresh(): void {}
  get_args(): Record<string, unknown> { return {}; }
  call_for_data(): Promise<unknown> { return Promise.resolve([]); }
  prepare_data(): void {}
  get_count_str(): string { return ''; }
  freeze(): void {}
  init(): Promise<void> { return Promise.resolve(); }
}

// ============================================================================
// Registration - Register Chat as a standard list view
// ============================================================================

// Register ChatView class so ListFactory can find it
frappe.views.ChatView = ChatView as unknown as new (opts: BaseListOptions) => ChatView;

// Register 'chat' in list_views array (lowercase)
if (!frappe.router.list_views.includes('chat')) {
  frappe.router.list_views.push('chat');
}

// Register 'chat' -> 'Chat' mapping in list_views_route
// This maps /communication/view/chat to ['List', 'Communication', 'Chat']
frappe.router.list_views_route['chat'] = 'Chat';

// ============================================================================
// Override generate_route to support Chat view
// ============================================================================

/**
 * Override frappe.utils.generate_route to handle Chat doc_view
 */
const originalGenerateRoute = frappe.utils.generate_route;

frappe.utils.generate_route = function (item: GenerateRouteItem): string {
  // Handle Chat doc_view for doctype items
  if (item.type?.toLowerCase() === 'doctype' && item.doc_view === 'Chat') {
    const doctype_slug = frappe.router.slug(item.doctype || item.name);
    let route = `${doctype_slug}/view/chat`;
    if (item.tab) {
      route += `#${item.tab}`;
    }
    if (item.route_options) {
      route +=
        '?' +
        Object.entries(item.route_options)
          .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
          .join('&');
    }
    return `/desk/${route}`;
  }

  // Fall back to original implementation
  return originalGenerateRoute.call(this, item);
};

// ============================================================================
// ListViewSelect Extension - Ensure Chat appears in view dropdown
// ============================================================================

/**
 * Extends ListViewSelect to ensure Chat view appears in the view selector
 * dropdown for Communication doctype.
 */
function extendListViewSelect(): void {
  const OriginalListViewSelect = frappe.views.ListViewSelect;

  if (OriginalListViewSelect) {
    const ChatViewSelect = class extends OriginalListViewSelect {
      setup_views(): void {
        super.setup_views();

        // Add Chat view for Communication doctype if not already added
        if (this.doctype === 'Communication') {
          this.add_view_to_menu('Chat', () => {
            frappe.set_route('List', this.doctype, 'Chat');
          });
        }
      }

      set_current_view(): void {
        super.set_current_view();

        // Handle Chat view in the current view display
        const route = frappe.get_route();
        if (route[2]?.toLowerCase() === 'chat') {
          this.current_view = 'Chat';
        }
      }
    };

    frappe.views.ListViewSelect = ChatViewSelect as unknown as ListViewSelectConstructor;
  }
}

// Initialize ListViewSelect extension
extendListViewSelect();

// ============================================================================
// Exports
// ============================================================================

export { ChatView };
export default ChatView;
