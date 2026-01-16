// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Frappe Chat View Integration
 *
 * This module integrates the vue-advanced-chat based messaging interface
 * into Frappe's routing system, providing a custom "Chat" view for
 * Communications. Follows the TreeView pattern with a Factory + View class.
 */

import { createApp, h, type Component, type App } from 'vue';
import ChatViewComponent from './chat/ChatView.vue';

// ============================================================================
// Type Declarations
// ============================================================================

// JQuery interface (minimal for our needs)
interface JQueryElement {
  find(selector: string): JQueryElement;
  remove(): JQueryElement;
  empty(): JQueryElement;
  append(element: HTMLElement | string): JQueryElement;
  addClass(className: string): JQueryElement;
  css(styles: Record<string, string>): JQueryElement;
  html(): string;
}

// Frappe Dialog interface
interface FrappeDialog {
  show(): void;
  hide(): void;
}

interface FrappeDialogOptions {
  title: string;
  fields: Array<{
    fieldtype: string;
    fieldname: string;
    label: string;
    options?: string;
    reqd?: number;
    default?: string;
  }>;
  primary_action_label: string;
  primary_action: (values: Record<string, string>) => void;
}

// Frappe Page interface
interface FrappePage {
  set_title(title: string): void;
  set_primary_action(label: string, callback: () => void, icon?: string): void;
  add_menu_item(label: string, callback: () => void): void;
  main: JQueryElement;
}

// Frappe Container interface
interface FrappeContainer {
  add_page(name: string): HTMLElement & { page: FrappePage };
  change_to(name: string): void;
}

// Factory base class interface
interface FrappeFactoryBase {
  route: string[];
  page_name: string;
  show(): void;
  make(route: string[]): void;
  on_show?(): void;
}

type FrappeFactoryConstructor = new () => FrappeFactoryBase;

interface FrappeViews {
  Factory: FrappeFactoryConstructor;
  ChatFactory?: FrappeFactoryConstructor;
  chats?: Record<string, ChatView>;
  CommunicationComposer?: new () => unknown;
  [key: string]: unknown;
}

interface FrappeModel {
  can_read(doctype: string): boolean;
  can_write(doctype: string): boolean;
  can_delete(doctype: string): boolean;
  with_doctype(doctype: string, callback: () => void): void;
}

interface FrappeBoot {
  user: {
    can_create: string[];
    in_create: string[];
  };
}

interface FrappeBreadcrumbs {
  add(module: string, doctype?: string): void;
}

interface FrappeUI {
  Dialog: new (options: FrappeDialogOptions) => FrappeDialog;
  make_app_page(options: { parent: HTMLElement; single_column: boolean }): void;
}

// Frappe global declarations
declare const frappe: {
  provide(namespace: string): void;
  views: FrappeViews;
  view_factory: Record<string, FrappeFactoryBase>;
  router: {
    factory_views: string[];
    list_views: string[];
    list_views_route: Record<string, string>;
  };
  container: FrappeContainer;
  model: FrappeModel;
  boot: FrappeBoot;
  breadcrumbs: FrappeBreadcrumbs;
  ui: FrappeUI;
  call<T>(options: {
    method: string;
    args?: Record<string, unknown>;
    async?: boolean;
    callback?: (response: { message: T }) => void;
  }): Promise<{ message: T }>;
  get_route(): string[];
  get_route_str(): string;
  get_meta(doctype: string): { module?: string } | null;
  set_route(route: string | string[]): void;
  show_alert(opts: { message: string; indicator: string }): void;
};

declare const $: (selector: string | HTMLElement) => JQueryElement;
declare const __: (text: string) => string;
declare const locals: { DocType: Record<string, { module: string }> };

// ============================================================================
// Namespaces
// ============================================================================

frappe.provide('frappe.views');
frappe.provide('frappe.views.chats');

// ============================================================================
// Chat Factory - Creates and manages ChatView instances
// ============================================================================

/**
 * ChatFactory extends frappe.views.Factory to handle routing for the Chat view.
 * Similar to TreeFactory, it creates ChatView instances for each doctype.
 */
class ChatFactory extends frappe.views.Factory {
  /**
   * Called when the route is first visited
   * Route format: /app/communication/view/chat
   */
  make(route: string[]): void {
    const doctype = route[1];

    frappe.model.with_doctype(doctype, () => {
      // Initialize the chats storage if needed
      if (!frappe.views.chats) {
        frappe.views.chats = {};
      }

      // Create new ChatView instance
      frappe.views.chats[doctype] = new ChatView({
        doctype: doctype,
      });
    });
  }

  /**
   * Called when navigating back to an existing chat view
   */
  on_show(): void {
    const route = frappe.get_route();
    const doctype = route[1];
    const chatView = frappe.views.chats?.[doctype];

    if (chatView) {
      chatView.refresh();
    }
  }

  get view_name(): string {
    return 'Chat';
  }
}

// ============================================================================
// Chat View - The actual messaging interface
// ============================================================================

interface ChatViewOptions {
  doctype: string;
}

/**
 * ChatView - Vue-based messaging interface
 * Follows the TreeView pattern: standalone class that manages its own page
 */
class ChatView {
  doctype: string;
  page_name: string;
  parent!: HTMLElement & { page: FrappePage };
  page!: FrappePage;
  vueApp: App | null = null;
  container: HTMLElement | null = null;

  // Permissions
  can_read = false;
  can_create = false;
  can_write = false;
  can_delete = false;

  constructor(opts: ChatViewOptions) {
    this.doctype = opts.doctype;
    this.page_name = frappe.get_route_str();

    this.get_permissions();
    this.make_page();
    this.set_menu_items();
    this.set_primary_action();
    this.render();
  }

  get_permissions(): void {
    this.can_read = frappe.model.can_read(this.doctype);
    this.can_create =
      frappe.boot.user.can_create.indexOf(this.doctype) !== -1 ||
      frappe.boot.user.in_create.indexOf(this.doctype) !== -1;
    this.can_write = frappe.model.can_write(this.doctype);
    this.can_delete = frappe.model.can_delete(this.doctype);
  }

  make_page(): void {
    this.parent = frappe.container.add_page(this.page_name);
    $(this.parent).addClass('chat-view');

    frappe.ui.make_app_page({
      parent: this.parent,
      single_column: true,
    });

    this.page = this.parent.page;
    frappe.container.change_to(this.page_name);

    // Add breadcrumbs
    const meta = frappe.get_meta(this.doctype);
    frappe.breadcrumbs.add(
      meta?.module || locals.DocType[this.doctype]?.module || 'Core',
      this.doctype
    );

    // Set page title
    this.page.set_title(__('Messages'));

    // Style the main area
    this.page.main.css({
      'min-height': '500px',
      padding: '0',
    });

    this.page.main.addClass('frappe-card');
  }

  set_menu_items(): void {
    // Switch to List view
    this.page.add_menu_item(__('View List'), () => {
      frappe.set_route(['List', this.doctype, 'List']);
    });

    // Refresh
    this.page.add_menu_item(__('Refresh'), () => {
      this.refresh();
    });

    // New Email (if CommunicationComposer available)
    if (frappe.views.CommunicationComposer) {
      this.page.add_menu_item(__('New Email'), () => {
        new (frappe.views.CommunicationComposer as new () => unknown)();
      });
    }
  }

  set_primary_action(): void {
    if (this.can_create) {
      this.page.set_primary_action(
        __('New Message'),
        () => {
          this.show_compose_dialog();
        },
        'add'
      );
    }
  }

  render(): void {
    // Clear any existing content
    this.page.main.empty();

    // Create Vue container
    this.container = document.createElement('div');
    this.container.id = 'chat-view-container';
    this.container.style.height = '100%';
    this.container.style.minHeight = '500px';
    this.page.main.append(this.container);

    // Mount Vue chat application
    this.vueApp = createApp({
      render: () => h(ChatViewComponent as Component),
    });

    this.vueApp.mount(this.container);
  }

  refresh(): void {
    // Unmount existing Vue app
    if (this.vueApp) {
      this.vueApp.unmount();
      this.vueApp = null;
    }

    // Re-render
    this.render();
  }

  destroy(): void {
    if (this.vueApp) {
      this.vueApp.unmount();
      this.vueApp = null;
    }
  }

  show_compose_dialog(): void {
    const dialog = new frappe.ui.Dialog({
      title: __('New Message'),
      fields: [
        {
          fieldtype: 'Select',
          fieldname: 'medium',
          label: __('Type'),
          options: 'Email\nSMS',
          reqd: 1,
          default: 'Email',
        },
        {
          fieldtype: 'Data',
          fieldname: 'recipient',
          label: __('To'),
          reqd: 1,
        },
        {
          fieldtype: 'Data',
          fieldname: 'subject',
          label: __('Subject'),
        },
        {
          fieldtype: 'Text Editor',
          fieldname: 'content',
          label: __('Message'),
          reqd: 1,
        },
      ],
      primary_action_label: __('Send'),
      primary_action: (values: Record<string, string>) => {
        this.send_new_message(values);
        dialog.hide();
      },
    });

    dialog.show();
  }

  send_new_message(values: Record<string, string>): void {
    const roomId = `${values.medium}:${values.recipient}`;

    frappe.call<{ success: boolean }>({
      method: 'messaging.messaging.api.chat.api.send_message',
      args: {
        room_id: roomId,
        content: values.content,
        subject: values.subject || '',
      },
      callback: (r) => {
        if (r.message && r.message.success) {
          frappe.show_alert({
            message: __('Message sent successfully'),
            indicator: 'green',
          });
          this.refresh();
        }
      },
    });
  }
}

// ============================================================================
// Registration
// ============================================================================

// Register the ChatFactory class
frappe.views.ChatFactory = ChatFactory as unknown as FrappeFactoryConstructor;

// Register chat in the factory_views (like tree, form, etc.)
if (!frappe.router.factory_views.includes('chat')) {
  frappe.router.factory_views.push('chat');
}

// Also register in list_views for the view switcher dropdown
if (!frappe.router.list_views.includes('chat')) {
  frappe.router.list_views.push('chat');
}
frappe.router.list_views_route['chat'] = 'Chat';

// ============================================================================
// Exports
// ============================================================================

export { ChatFactory, ChatView };
export default { ChatFactory, ChatView };
