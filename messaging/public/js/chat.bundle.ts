// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Frappe Chat View Integration
 *
 * This module integrates the vue-advanced-chat based messaging interface
 * into Frappe's routing system, providing a custom "Chat" view for
 * Communications that replaces the default list view.
 */

import { createApp, h } from 'vue';
import ChatView from './chat/ChatView.vue';

// Frappe global declarations
declare const frappe: {
  provide: (namespace: string) => void;
  views: {
    ListView: new () => FrappeListView;
    ListViewSelect: new () => FrappeListViewSelect;
    [key: string]: unknown;
  };
  router: {
    list_views: string[];
    list_views_route: Record<string, string>;
  };
  call: <T>(options: {
    method: string;
    args?: Record<string, unknown>;
    async?: boolean;
    callback?: (response: { message: T }) => void;
  }) => Promise<{ message: T }>;
  _: (text: string) => string;
  new_doc: (doctype: string) => void;
};

declare const __: (text: string) => string;

interface FrappeListView {
  doctype: string;
  page_title: string;
  page_name: string;
  method: string;
  data: unknown[];
  $result: JQuery;
  page: {
    set_primary_action: (label: string, callback: () => void) => void;
    add_menu_item: (label: string, callback: () => void) => void;
  };
  setup_defaults: () => void;
  setup_page: () => void;
  render_header: (refresh?: boolean) => void;
  render_list: () => void;
  prepare_data: (r: { message: unknown[] }) => void;
  show_skeleton: () => void;
  hide_skeleton: () => void;
}

interface FrappeListViewSelect {
  doctype: string;
  setup_views: () => void;
  add_view_to_menu: (name: string, callback: () => void) => void;
  set_route: (view: string) => void;
}

// Ensure frappe namespaces exist
frappe.provide('frappe.views');
frappe.provide('frappe.router');

/**
 * Extended ListViewSelect that adds Chat view option for Communications
 */
frappe.views.ChatViewSelect = class ChatViewSelect extends frappe.views.ListViewSelect {
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
};

// Register chat view in router
frappe.router.list_views.push('chat');
frappe.router.list_views_route['chat'] = 'Chat';

/**
 * Chat View - Vue-based messaging interface for Communications
 */
frappe.views.ChatView = class ChatView extends frappe.views.ListView {
  data: unknown[] = [];

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
      new (frappe.views as unknown as { CommunicationComposer: new () => unknown }).CommunicationComposer();
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
      render: () => h(ChatView as unknown as Parameters<typeof h>[0]),
    });

    app.mount(container);
  }

  show_compose_dialog(): void {
    // Show a dialog to choose communication type
    const dialog = new (frappe as unknown as { 
      ui: { 
        Dialog: new (options: {
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
        }) => { show: () => void };
      };
    }).ui.Dialog({
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
      primary_action: (values) => {
        this.send_new_message(values);
        dialog.hide();
      },
    });

    dialog.show();
  }

  send_new_message(values: Record<string, string>): void {
    // Create room ID for new conversation
    const roomId = `${values.medium}:${values.recipient}`;

    frappe.call({
      method: 'messaging.messaging.api.chat.api.send_message',
      args: {
        room_id: roomId,
        content: values.content,
        subject: values.subject || '',
      },
      callback: (r) => {
        if (r.message && r.message.success) {
          (frappe as unknown as { 
            show_alert: (opts: { message: string; indicator: string }) => void;
          }).show_alert({
            message: __('Message sent successfully'),
            indicator: 'green',
          });
          // Refresh the chat view
          this.render_list();
        }
      },
    });
  }
};

// Override ListViewSelect for Communication doctype
frappe.views.ListViewSelect = frappe.views.ChatViewSelect;

// Export for module usage
export default {
  ChatView: frappe.views.ChatView,
  ChatViewSelect: frappe.views.ChatViewSelect,
};
