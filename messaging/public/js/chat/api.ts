// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * API client for the Messaging Chat interface.
 * Provides typed wrappers around Frappe API calls.
 */

import type {
  CurrentUser,
  MarkSeenResponse,
  MessagesResponse,
  Room,
  RoomsResponse,
  SendMessageResponse,
  CommunicationMedium,
  MessageFile,
} from './types';

// Frappe global type declaration
declare const frappe: {
  call: <T>(options: {
    method: string;
    args?: Record<string, unknown>;
    async?: boolean;
    freeze?: boolean;
    freeze_message?: string;
    callback?: (response: { message: T }) => void;
    error?: (error: Error) => void;
  }) => Promise<{ message: T }>;
  xcall: <T>(method: string, args?: Record<string, unknown>) => Promise<T>;
  throw: (message: string) => never;
  show_alert: (options: { message: string; indicator?: string }) => void;
  msgprint: (message: string) => void;
  session: {
    user: string;
  };
  boot: {
    user: {
      name: string;
      full_name: string;
      user_image: string | null;
      email: string;
    };
  };
};

const API_BASE = 'messaging.messaging.api.chat.api';

/**
 * Make a Frappe API call with error handling.
 */
async function apiCall<T>(
  method: string,
  args: Record<string, unknown> = {}
): Promise<T> {
  try {
    const response = await frappe.call<T>({
      method: `${API_BASE}.${method}`,
      args,
    });
    return response.message;
  } catch (error) {
    console.error(`API call failed: ${method}`, error);
    throw error;
  }
}

/**
 * Get current logged-in user information.
 */
export async function getCurrentUser(): Promise<CurrentUser> {
  return apiCall<CurrentUser>('get_current_user');
}

/**
 * Get list of chat rooms (conversation threads).
 */
export async function getRooms(options: {
  page?: number;
  limit?: number;
  search?: string;
  medium?: CommunicationMedium | 'All';
} = {}): Promise<RoomsResponse> {
  return apiCall<RoomsResponse>('get_rooms', {
    page: options.page ?? 1,
    limit: options.limit ?? 20,
    search: options.search ?? '',
    medium: options.medium ?? 'All',
  });
}

/**
 * Get messages for a specific room.
 */
export async function getMessages(options: {
  room_id: string;
  page?: number;
  limit?: number;
  before_id?: string;
}): Promise<MessagesResponse> {
  return apiCall<MessagesResponse>('get_messages', {
    room_id: options.room_id,
    page: options.page ?? 1,
    limit: options.limit ?? 50,
    before_id: options.before_id ?? '',
  });
}

/**
 * Send a new message in a conversation.
 */
export async function sendMessage(options: {
  room_id: string;
  content: string;
  files?: MessageFile[];
  reply_message_id?: string;
  subject?: string;
}): Promise<SendMessageResponse> {
  return apiCall<SendMessageResponse>('send_message', {
    room_id: options.room_id,
    content: options.content,
    files: options.files ?? [],
    reply_message_id: options.reply_message_id ?? '',
    subject: options.subject ?? '',
  });
}

/**
 * Mark all messages in a room as seen.
 */
export async function markMessagesSeen(
  room_id: string
): Promise<MarkSeenResponse> {
  return apiCall<MarkSeenResponse>('mark_messages_seen', { room_id });
}

/**
 * Search for rooms matching a query.
 */
export async function searchRooms(
  query: string,
  limit: number = 10
): Promise<Room[]> {
  return apiCall<Room[]>('search_rooms', { query, limit });
}

/**
 * Get total count of unread messages.
 */
export async function getUnreadCount(): Promise<number> {
  return apiCall<number>('get_unread_count');
}

/**
 * Upload a file attachment.
 */
export async function uploadFile(
  file: File,
  doctype?: string,
  docname?: string
): Promise<MessageFile> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);
    if (doctype) formData.append('doctype', doctype);
    if (docname) formData.append('docname', docname);
    formData.append('is_private', '1');

    fetch('/api/method/upload_file', {
      method: 'POST',
      body: formData,
      headers: {
        'X-Frappe-CSRF-Token': (window as unknown as { csrf_token: string }).csrf_token,
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.message) {
          const fileData = data.message;
          resolve({
            name: fileData.file_name,
            type: fileData.file_type || 'application/octet-stream',
            extension: fileData.file_name?.split('.').pop() || '',
            url: fileData.file_url,
            size: file.size,
          });
        } else {
          reject(new Error('Upload failed'));
        }
      })
      .catch(reject);
  });
}

export default {
  getCurrentUser,
  getRooms,
  getMessages,
  sendMessage,
  markMessagesSeen,
  searchRooms,
  getUnreadCount,
  uploadFile,
};
