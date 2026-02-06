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
    route?: () => Promise<void>;
    on?: (event: string, callback: () => void) => void;
  };
  set_route(...args: (string | string[])[]): void;
  show_alert(opts: { message: string; indicator: string }): void;
  boot: {
    user: {
      can_read: string[];
    };
  };
  route_options?: Record<string, unknown> | null;
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

  // Add on_hide to resume shortcuts when navigating away
  on_hide(): void {
    const route = frappe.get_route();
    const chatView = frappe.views.chats?.[route[1]];
    if (chatView) {
      chatView.hide();
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
    // Suspend Frappe keyboard shortcuts
    suspendFrappeKeyboardShortcuts();

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
    // Suspend shortcuts when showing
    suspendFrappeKeyboardShortcuts();
    frappe.container.change_to(this.page_name);
  }

  hide(): void {
    // Resume shortcuts when hiding
    resumeFrappeKeyboardShortcuts();
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
// Route Interception - Redirect Inbox to Chat View
// ============================================================================

/**
 * The exact inbox URL pattern we want to intercept:
 * /desk/communication/view/list?status=["!=","Replied"]&status=["!=","Closed"]&sent_or_received=Received
 */

// Flag to prevent redirect loops
let isRedirecting = false;

/**
 * Check if URL search params match the exact inbox pattern
 * URL: ?status=["!=","Replied"]&status=["!=","Closed"]&sent_or_received=Received
 */
function isInboxSearchParams(params: URLSearchParams): boolean {
  // Must have sent_or_received=Received for inbox
  const sentOrReceived = params.get('sent_or_received');
  if (sentOrReceived !== 'Received') {
    return false;
  }

  // Check for status filters with != operators (inbox excludes Replied/Closed)
  const statusValues = params.getAll('status');
  if (statusValues.length === 0) {
    // Has sent_or_received=Received but no status filters - still inbox-like
    return true;
  }

  for (const status of statusValues) {
    // URLSearchParams already decodes values, so status should be like: ["!=","Replied"]
    if (status.includes('!=') || status.includes('not in')) {
      return true;
    }
  }

  return true; // Has sent_or_received=Received
}

/**
 * Check if route_options indicate an inbox-like filter
 * Must match the specific inbox pattern: sent_or_received=Received AND status exclusions
 */
function isInboxRouteOptions(opts: Record<string, unknown>): boolean {
  if (!opts) return false;

  // Must have sent_or_received = Received for inbox
  const sentOrReceived = opts.sent_or_received;
  if (sentOrReceived !== 'Received') {
    return false;
  }

  // Check for status filters with != operators (inbox excludes Replied/Closed)
  const status = opts.status;
  if (status) {
    // status could be a string like '["!=","Replied"]' or an array
    const statusStr = typeof status === 'string' ? status : JSON.stringify(status);
    if (statusStr.includes('!=') || statusStr.includes('not in')) {
      return true;
    }
  }

  // Has sent_or_received=Received, consider it inbox-like
  return true;
}

/**
 * Check if current URL path is a Communication list view
 */
function isCommunicationListPath(pathname: string): boolean {
  const path = pathname.toLowerCase();
  const pathParts = path.split('/').filter(p => p && p !== 'app' && p !== 'desk');

  // Pattern 1: /communication/view/list or /communication
  if (pathParts[0] === 'communication') {
    // Just /communication - it's a list
    if (pathParts.length === 1) return true;
    // /communication/view/list
    if (pathParts[1] === 'view' && (!pathParts[2] || pathParts[2] === 'list')) return true;
    // /communication/view/something-else (report, kanban, etc.) - NOT a list
    if (pathParts[1] === 'view' && pathParts[2] && pathParts[2] !== 'list') return false;
    return false;
  }

  // Pattern 2: /list/communication or /list/communication/list
  if (pathParts[0] === 'list' && pathParts[1] === 'communication') {
    // /list/communication/something (report, kanban) - NOT a list
    if (pathParts[2] && pathParts[2] !== 'list') return false;
    return true;
  }

  return false;
}

/**
 * Check current route and redirect if it's an inbox route
 */
function checkAndRedirectInbox(): void {
  if (isRedirecting) return;

  const currentPath = window.location.pathname;
  const searchParams = new URLSearchParams(window.location.search);

  // Check if we're on a Communication list route
  if (!isCommunicationListPath(currentPath)) {
    return;
  }

  // Check route_options first (set before programmatic navigation)
  const routeOpts = frappe.route_options;
  if (routeOpts && isInboxRouteOptions(routeOpts)) {
    isRedirecting = true;
    frappe.route_options = null;
    frappe.set_route(['Chat', 'Communication']);
    setTimeout(() => { isRedirecting = false; }, 100);
    return;
  }

  // Check URL search params for direct navigation
  if (isInboxSearchParams(searchParams)) {
    isRedirecting = true;
    frappe.set_route(['Chat', 'Communication']);
    setTimeout(() => { isRedirecting = false; }, 100);
    return;
  }
}

/**
 * Intercept Communication list routes that look like "inbox" queries
 * and redirect them to the Chat view instead.
 */
function setupInboxRedirect(): void {
  // Store original set_route
  const originalSetRoute = frappe.set_route.bind(frappe);

  // Override set_route to intercept inbox-like routes
  frappe.set_route = function (...args: (string | string[])[]): void {
    if (isRedirecting) {
      originalSetRoute(...args);
      return;
    }

    // Normalize route to array
    let routeArr: string[];
    if (args.length === 1 && Array.isArray(args[0])) {
      routeArr = args[0];
    } else if (args.length === 1 && typeof args[0] === 'string' && args[0].includes('/')) {
      routeArr = args[0].split('/');
    } else {
      routeArr = args.map((arg) => (Array.isArray(arg) ? arg.join('/') : String(arg)));
    }

    // Clean up route - remove empty strings and 'desk'/'app' prefix
    const cleanedRoute = routeArr.filter((r) => r && r !== 'desk' && r !== 'app');

    // Check if this is a Communication List view route
    const isCommList =
      (cleanedRoute[0]?.toLowerCase() === 'list' &&
        cleanedRoute[1]?.toLowerCase() === 'communication' &&
        (!cleanedRoute[2] || cleanedRoute[2]?.toLowerCase() === 'list')) ||
      (cleanedRoute[0]?.toLowerCase() === 'communication' &&
        (cleanedRoute.length === 1 ||
          (cleanedRoute[1]?.toLowerCase() === 'view' &&
           (!cleanedRoute[2] || cleanedRoute[2]?.toLowerCase() === 'list'))));

    if (isCommList) {
      const routeOpts = frappe.route_options;
      if (routeOpts && isInboxRouteOptions(routeOpts)) {
        isRedirecting = true;
        frappe.route_options = null;
        originalSetRoute(['Chat', 'Communication']);
        setTimeout(() => { isRedirecting = false; }, 100);
        return;
      }
    }

    originalSetRoute(...args);
  };

  // Set up route change listener using Frappe's event system
  if (frappe.router.on && typeof frappe.router.on === 'function') {
    frappe.router.on('change', () => {
      // Small delay to let the route fully resolve
      setTimeout(checkAndRedirectInbox, 10);
    });
  }

  // Also intercept at the router level for direct navigation
  const setupRouterOverride = (): void => {
    const originalRouterRoute = frappe.router.route;
    if (originalRouterRoute && typeof originalRouterRoute === 'function') {
      frappe.router.route = async function (): Promise<void> {
        if (!isRedirecting) {
          const path = window.location.pathname;
          const searchParams = new URLSearchParams(window.location.search);

          if (isCommunicationListPath(path)) {
            const routeOpts = frappe.route_options;
            if ((routeOpts && isInboxRouteOptions(routeOpts)) || isInboxSearchParams(searchParams)) {
              isRedirecting = true;
              frappe.route_options = null;
              frappe.set_route(['Chat', 'Communication']);
              setTimeout(() => { isRedirecting = false; }, 100);
              return;
            }
          }
        }
        return originalRouterRoute.call(frappe.router);
      };
    }
  };

  // Try to set up router override immediately
  setupRouterOverride();

  // Also try after a delay in case frappe.router.route isn't ready yet
  setTimeout(setupRouterOverride, 100);
  setTimeout(setupRouterOverride, 500);

  // Check on initial page load with multiple timing attempts
  setTimeout(checkAndRedirectInbox, 0);
  setTimeout(checkAndRedirectInbox, 50);
  setTimeout(checkAndRedirectInbox, 200);

  // Check after DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(checkAndRedirectInbox, 0);
      setTimeout(checkAndRedirectInbox, 100);
    });
  }

  // Also check when Frappe is fully ready (using jQuery event)
  try {
    const $doc = $(document as unknown as HTMLElement);
    if ($doc && typeof $doc.on === 'function') {
      $doc.on('page-change', () => {
        setTimeout(checkAndRedirectInbox, 10);
      });
    }
  } catch {
    // jQuery not available or doesn't support document binding
  }

  // Use hashchange for SPA navigation
  window.addEventListener('hashchange', () => {
    setTimeout(checkAndRedirectInbox, 10);
  });

  // Use popstate for browser back/forward
  window.addEventListener('popstate', () => {
    setTimeout(checkAndRedirectInbox, 10);
  });
}

// Initialize inbox redirect
setupInboxRedirect();

// ============================================================================
// Exports
// ============================================================================

export { ChatFactory, ChatView };
export default ChatFactory;
