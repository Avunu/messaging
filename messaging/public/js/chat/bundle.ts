// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Frappe Chat View Integration
 *
 * This module integrates the vue-advanced-chat based messaging interface
 * into Frappe's routing system, providing a custom "Chat" view for
 * Communications. Uses the ListView extension pattern (like InboxView).
 */

import { createApp, h, type Component, type App } from 'vue';
import ChatViewComponent from './ChatView.vue';

// ============================================================================
// Type Declarations
// ============================================================================

// JQuery interface
interface JQueryElement {
  find(selector: string): JQueryElement;
  remove(): JQueryElement;
  empty(): JQueryElement;
  append(element: HTMLElement | string): JQueryElement;
  prepend(element: HTMLElement | string): JQueryElement;
  addClass(className: string): JQueryElement;
  css(styles: Record<string, string>): JQueryElement;
  html(): string;
  hide(): JQueryElement;
  show(): JQueryElement;
}

// Frappe Page interface
interface FrappePage {
  set_title(title: string): void;
  set_primary_action(label: string, callback: () => void, icon?: string): void;
  add_menu_item(label: string, callback: () => void): void;
  main: JQueryElement;
}

// ListView base interface
interface ListViewBase {
  doctype: string;
  parent: { page: FrappePage };
  $result: JQueryElement;
  page: FrappePage;
  page_title: string;
  data: unknown[];
  meta: { title_field?: string; fields: unknown[] };
  columns: unknown[];
  fields: unknown[];
  list_view_settings: Record<string, unknown>;
  settings: Record<string, unknown>;

  // Methods we may need to call via super
  setup_defaults(): Promise<void>;
  setup_columns(): void;
  setup_fields(): Promise<void>;
  render_header(refresh?: boolean): void;
  render_list(): void;
  get_header_html(): string;
  refresh(): Promise<void>;
  before_refresh(): void;
  show(): void;
}

type ListViewConstructor = new (opts: { doctype: string; parent: unknown }) => ListViewBase;

interface FrappeViews {
  ListView: ListViewConstructor;
  ChatView?: ListViewConstructor;
  CommunicationComposer?: new () => unknown;
  [key: string]: unknown;
}

// Frappe global declarations
declare const frappe: {
  provide(namespace: string): void;
  views: FrappeViews;
  router: {
    factory_views: string[];
    list_views: string[];
    list_views_route: Record<string, string>;
  };
  call<T>(options: {
    method: string;
    args?: Record<string, unknown>;
    async?: boolean;
    callback?: (response: { message: T }) => void;
  }): Promise<{ message: T }>;
  set_route(route: string | string[]): void;
  show_alert(opts: { message: string; indicator: string }): void;
};

declare const __: (text: string) => string;

// ============================================================================
// Namespaces
// ============================================================================

frappe.provide('frappe.views');

// ============================================================================
// Chat View - Extends ListView to render Vue chat component
// ============================================================================

/**
 * ChatView extends ListView to provide a chat-like interface for Communications.
 * Similar to InboxView, it overrides list rendering to use a custom UI.
 */
class ChatView extends frappe.views.ListView {
  vueApp: App | null = null;
  container: HTMLElement | null = null;

  get view_name(): string {
    return 'Chat';
  }

  setup_defaults(): Promise<void> {
    // Call parent to set up basic defaults
    const result = super.setup_defaults();

    // Override page title
    this.page_title = __('Messages');

    return result;
  }

  // Override setup_columns to provide minimal columns
  // This prevents the "Cannot read properties of undefined (reading 'fields')" error
  setup_columns(): void {
    this.columns = [];
    // We don't need columns since we're rendering a custom Vue component
  }

  // Override setup_fields to provide minimal fields
  async setup_fields(): Promise<void> {
    this.fields = [
      ['name', this.doctype],
      ['subject', this.doctype],
      ['content', this.doctype],
      ['communication_medium', this.doctype],
      ['sender', this.doctype],
      ['recipients', this.doctype],
      ['communication_date', this.doctype],
    ];
  }

  // Override render_header to hide the standard list header
  render_header(_refresh_header = false): void {
    this.$result.find('.list-row-head').remove();
  }

  // Override before_refresh to skip standard list refresh behavior
  before_refresh(): void {
    // Don't do standard refresh - we manage our own data
  }

  // Override refresh to just re-render our Vue component
  async refresh(): Promise<void> {
    this.render_list();
  }

  // Override render_list to mount our Vue component
  render_list(): void {
    // Clear result area
    this.$result.empty();

    // Unmount existing Vue app if present
    if (this.vueApp) {
      this.vueApp.unmount();
      this.vueApp = null;
    }

    // Create Vue container
    this.container = document.createElement('div');
    this.container.id = 'chat-view-container';
    this.container.style.height = 'calc(100vh - 180px)';
    this.container.style.minHeight = '500px';
    this.$result.append(this.container);

    // Mount Vue chat application
    this.vueApp = createApp({
      render: () => h(ChatViewComponent as Component),
    });

    this.vueApp.mount(this.container);
  }

  // Add menu items
  setup_view_menu(): void {
    // Add menu item to switch to standard List view
    this.page.add_menu_item(__('View List'), () => {
      frappe.set_route(['List', this.doctype, 'List']);
    });

    // New Email option if CommunicationComposer is available
    if (frappe.views.CommunicationComposer) {
      this.page.add_menu_item(__('New Email'), () => {
        new (frappe.views.CommunicationComposer as new () => unknown)();
      });
    }
  }
}

// ============================================================================
// Registration
// ============================================================================

// Register the ChatView class - this is what ListFactory looks for
frappe.views.ChatView = ChatView as unknown as ListViewConstructor;

// Register in list_views for the view switcher dropdown
if (!frappe.router.list_views.includes('chat')) {
  frappe.router.list_views.push('chat');
}
frappe.router.list_views_route['chat'] = 'Chat';

// ============================================================================
// Exports
// ============================================================================

export { ChatView };
export default ChatView;
