// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Frappe Chat View Integration
 *
 * This module integrates the vue-advanced-chat based messaging interface
 * into Frappe's routing system, providing a custom "Chat" view for
 * Communications that replaces the default list view.
 */

import { createApp, h, type Component } from 'vue';
import ChatViewComponent from './chat/ChatView.vue';

// JQuery interface (minimal for our needs)
interface JQueryElement {
  find(selector: string): JQueryElement;
  remove(): JQueryElement;
  empty(): JQueryElement;
  append(element: HTMLElement | string): JQueryElement;
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
  set_primary_action(label: string, callback: () => void): void;
  add_menu_item(label: string, callback: () => void): void;
}

// Base class interfaces - use function signatures to allow override
interface FrappeListViewBase {
  doctype: string;
  page_title: string;
  page_name: string;
  method: string;
  data: unknown[];
  $result: JQueryElement;
  page: FrappePage;
}

interface FrappeListViewSelectBase {
  doctype: string;
}

// Constructor types for Frappe classes
type FrappeListViewConstructor = new () => FrappeListViewBase & {
  setup_defaults(): void;
  setup_page(): void;
  render_header(refresh?: boolean): void;
  render_list(): void;
  prepare_data(r: { message: unknown[] }): void;
  show_skeleton(): void;
  hide_skeleton(): void;
};

type FrappeListViewSelectConstructor = new () => FrappeListViewSelectBase & {
  setup_views(): void;
  add_view_to_menu(name: string, callback: () => void): void;
  set_route(view: string): void;
};

interface FrappeViews {
  ListView: FrappeListViewConstructor;
  ListViewSelect: FrappeListViewSelectConstructor;
  ChatView?: FrappeListViewConstructor;
  ChatViewSelect?: FrappeListViewSelectConstructor;
  CommunicationComposer?: new () => unknown;
  [key: string]: unknown;
}

// Frappe global declarations
declare const frappe: {
  provide(namespace: string): void;
  views: FrappeViews;
  router: {
    list_views: string[];
    list_views_route: Record<string, string>;
  };
  call<T>(options: {
    method: string;
    args?: Record<string, unknown>;
    async?: boolean;
    callback?: (response: { message: T }) => void;
  }): Promise<{ message: T }>;
  _: (text: string) => string;
  new_doc(doctype: string): void;
  show_alert(opts: { message: string; indicator: string }): void;
  ui: {
    Dialog: new (options: FrappeDialogOptions) => FrappeDialog;
  };
};

declare const __: (text: string) => string;

// Ensure frappe namespaces exist
frappe.provide('frappe.views');
frappe.provide('frappe.router');

/**
 * Extended ListViewSelect that adds Chat view option for Communications
 */
class ChatViewSelect extends frappe.views.ListViewSelect {
  setup_views(): void {
    // Call parent setup
    super.setup_views();

    // Add Chat view for Communication doctype
    if (this.doctype === 'Communication') {
      this.add_view_to_menu('Chat', () => {
        this.set_route('chat');
      });
    }

    // Add List view to allow switching back
    this.add_view_to_menu('List', () => {
      this.set_route('List');
    });
  }
}

// Register the ChatViewSelect class
frappe.views.ChatViewSelect = ChatViewSelect as unknown as FrappeListViewSelectConstructor;

// Register chat view in router
frappe.router.list_views.push('chat');
frappe.router.list_views_route['chat'] = 'Chat';

/**
 * Chat View - Vue-based messaging interface for Communications
 */
class ChatView extends frappe.views.ListView {
  declare data: unknown[];

  prepare_data(r: { message: unknown[] }): void {
    // Chat view manages its own data loading
    this.data = r.message || [];
  }

  setup_defaults(): void {
    super.setup_defaults();
    this.page_title = __('Messages');
    this.page_name = 'chat-view';
    // We don't use the standard list method
    this.method = 'messaging.messaging.api.chat.api.get_rooms';
  }

  setup_page(): void {
    super.setup_page();

    // Primary action - compose new message
    this.page.set_primary_action(__('New Message'), () => {
      this.show_compose_dialog();
    });

    // Menu items
    this.page.add_menu_item(__('New Email'), () => {
      if (frappe.views.CommunicationComposer) {
        new frappe.views.CommunicationComposer();
      }
    });

    this.page.add_menu_item(__('Refresh'), () => {
      this.render_list();
    });
  }

  show_skeleton(): void {
    // No skeleton for chat view
  }

  hide_skeleton(): void {
    // No skeleton for chat view
  }

  render_header(_refresh_header = false): void {
    // Remove default header
    this.$result.find('.list-row-head').remove();
  }

  render_list(): void {
    // Clear result area
    this.$result.empty();

    // Create Vue container
    const container = document.createElement('div');
    container.id = 'chat-view-container';
    this.$result.append(container);

    // Mount Vue chat application
    const app = createApp({
      render: () => h(ChatViewComponent as Component),
    });

    app.mount(container);
  }

  show_compose_dialog(): void {
    // Show a dialog to choose communication type
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
    // Create room ID for new conversation
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
          // Refresh the chat view
          this.render_list();
        }
      },
    });
  }
}

// Register the ChatView class
frappe.views.ChatView = ChatView as unknown as FrappeListViewConstructor;

// Override ListViewSelect for Communication doctype
frappe.views.ListViewSelect = ChatViewSelect as unknown as FrappeListViewSelectConstructor;

// Export for module usage
export { ChatView, ChatViewSelect };
export default { ChatView, ChatViewSelect };
