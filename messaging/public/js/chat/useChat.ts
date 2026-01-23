// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Composable for managing chat state and interactions.
 * Provides reactive state management for the chat interface.
 */

import { ref, computed, watch, type Ref, type ComputedRef } from 'vue';
import type {
  CurrentUser,
  Room,
  Message,
  CommunicationMedium,
  FetchMessagesEvent,
  SendMessageEvent,
  MessageFile,
} from './types';
import {
  getCurrentUser,
  getRooms,
  getMessages,
  sendMessage,
  markMessagesSeen,
  getUnreadCount,
  uploadFile,
} from './api';

// Frappe global
declare const frappe: {
  show_alert: (options: { message: string; indicator?: string }) => void;
  realtime: {
    on: (event: string, callback: (data: unknown) => void) => void;
    off: (event: string, callback?: (data: unknown) => void) => void;
  };
};

export interface UseChatReturn {
  // State
  currentUser: Ref<CurrentUser | null>;
  rooms: Ref<Room[]>;
  currentRoom: Ref<Room | null>;
  messages: Ref<Message[]>;
  loadingRooms: Ref<boolean>;
  loadingMessages: Ref<boolean>;
  roomsLoaded: Ref<boolean>;
  messagesLoaded: Ref<boolean>;
  error: Ref<string | null>;
  searchQuery: Ref<string>;
  mediumFilter: Ref<CommunicationMedium | 'All'>;
  unreadCount: Ref<number>;

  // Computed
  filteredRooms: ComputedRef<Room[]>;
  currentRoomId: ComputedRef<string>;

  // Actions
  initialize: () => Promise<void>;
  fetchRooms: (reset?: boolean) => Promise<void>;
  fetchMessages: (event: FetchMessagesEvent) => Promise<void>;
  handleSendMessage: (event: SendMessageEvent) => Promise<void>;
  selectRoom: (room: Room) => void;
  setSearchQuery: (query: string) => void;
  setMediumFilter: (medium: CommunicationMedium | 'All') => void;
  handleUploadFile: (file: File) => Promise<MessageFile>;
  refreshUnreadCount: () => Promise<void>;
}

export function useChat(): UseChatReturn {
  // State
  const currentUser = ref<CurrentUser | null>(null);
  const rooms = ref<Room[]>([]);
  const currentRoom = ref<Room | null>(null);
  const messages = ref<Message[]>([]);
  const loadingRooms = ref(false);
  const loadingMessages = ref(false);
  const roomsLoaded = ref(false);
  const messagesLoaded = ref(false);
  const error = ref<string | null>(null);
  const searchQuery = ref('');
  const mediumFilter = ref<CommunicationMedium | 'All'>('All');
  const unreadCount = ref(0);

  // Pagination state
  const roomsPage = ref(1);
  const messagesPage = ref(1);

  // Computed
  const filteredRooms = computed(() => {
    let filtered = rooms.value;

    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase();
      filtered = filtered.filter(
        (room) =>
          room.roomName.toLowerCase().includes(query) ||
          room.lastMessage?.content?.toLowerCase().includes(query)
      );
    }

    if (mediumFilter.value !== 'All') {
      filtered = filtered.filter(
        (room) => room.communicationMedium === mediumFilter.value
      );
    }

    return filtered;
  });

  const currentRoomId = computed(() => currentRoom.value?.roomId ?? '');

  // Actions
  async function initialize(): Promise<void> {
    try {
      error.value = null;
      currentUser.value = await getCurrentUser();
      await fetchRooms(true);
      await refreshUnreadCount();

      // Set up realtime listeners for new messages
      setupRealtimeListeners();
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to initialize';
      console.error('Chat initialization failed:', err);
    }
  }

  async function fetchRooms(reset = false): Promise<void> {
    if (loadingRooms.value) return;

    try {
      loadingRooms.value = true;
      error.value = null;

      if (reset) {
        roomsPage.value = 1;
        rooms.value = [];
        roomsLoaded.value = false;
      }

      const response = await getRooms({
        page: roomsPage.value,
        limit: 20,
        search: searchQuery.value,
        medium: mediumFilter.value,
      });

      if (reset) {
        rooms.value = response.rooms;
      } else {
        rooms.value = [...rooms.value, ...response.rooms];
      }

      roomsLoaded.value = !response.hasMore;
      roomsPage.value++;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch rooms';
      console.error('Failed to fetch rooms:', err);
    } finally {
      loadingRooms.value = false;
    }
  }

  async function fetchMessages(event: FetchMessagesEvent): Promise<void> {
    if (!event.room || loadingMessages.value) return;

    const reset = event.options?.reset ?? false;

    try {
      loadingMessages.value = true;
      error.value = null;

      if (reset) {
        messagesPage.value = 1;
        messages.value = [];
        messagesLoaded.value = false;
      }

      const response = await getMessages({
        room_id: event.room.roomId,
        page: messagesPage.value,
        limit: 50,
      });

      if (reset) {
        messages.value = response.messages;
      } else {
        // Prepend older messages
        messages.value = [...response.messages, ...messages.value];
      }

      messagesLoaded.value = !response.hasMore;
      messagesPage.value++;

      // Mark messages as seen
      if (reset && response.messages.length > 0) {
        await markMessagesSeen(event.room.roomId);
        await refreshUnreadCount();

        // Update room's unread count locally
        const roomIndex = rooms.value.findIndex(
          (r) => r.roomId === event.room.roomId
        );
        if (roomIndex !== -1) {
          rooms.value[roomIndex] = {
            ...rooms.value[roomIndex],
            unreadCount: 0,
          };
        }
      }
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : 'Failed to fetch messages';
      console.error('Failed to fetch messages:', err);
    } finally {
      loadingMessages.value = false;
    }
  }

  async function handleSendMessage(data: SendMessageEvent): Promise<void> {
    // Use roomId from event (more reliable than currentRoom with Web Components)
    if (!data.roomId || !data.content?.trim()) return;

    try {
      error.value = null;

      // Extract reply_message_id from replyMessage if present
      // In vue-advanced-chat, replyMessage._id is the message identifier
      // which in our case is the Communication document name
      const replyMessageId = data.replyMessage?._id || '';

      const response = await sendMessage({
        room_id: data.roomId,
        content: data.content,
        files: data.files,
        reply_message_id: replyMessageId,
      });

      if (response.success && response.message) {
        // Add message to the list
        messages.value = [...messages.value, response.message];

        // Update room's last message
        const roomIndex = rooms.value.findIndex(
          (r) => r.roomId === data.roomId
        );
        if (roomIndex !== -1) {
          rooms.value[roomIndex] = {
            ...rooms.value[roomIndex],
            lastMessage: {
              content: data.content,
              senderId: currentUser.value?._id ?? '',
              timestamp: new Date().toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              }),
              saved: true,
              distributed: false,
              seen: false,
            },
          };
        }
      } else if (response.error) {
        frappe.show_alert({
          message: response.error,
          indicator: 'red',
        });
      }
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : 'Failed to send message';
      console.error('Failed to send message:', err);
      frappe.show_alert({
        message: 'Failed to send message',
        indicator: 'red',
      });
    }
  }

  function selectRoom(room: Room): void {
    currentRoom.value = room;
    messagesPage.value = 1;
    messages.value = [];
    messagesLoaded.value = false;
  }

  function setSearchQuery(query: string): void {
    searchQuery.value = query;
    // Debounced room fetch is handled by watcher
  }

  function setMediumFilter(medium: CommunicationMedium | 'All'): void {
    mediumFilter.value = medium;
    fetchRooms(true);
  }

  async function handleUploadFile(file: File): Promise<MessageFile> {
    return uploadFile(file);
  }

  async function refreshUnreadCount(): Promise<void> {
    try {
      unreadCount.value = await getUnreadCount();
    } catch (err) {
      console.error('Failed to get unread count:', err);
    }
  }

  // Watch for search query changes with debounce
  let searchTimeout: ReturnType<typeof setTimeout> | null = null;
  watch(searchQuery, () => {
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      fetchRooms(true);
    }, 300);
  });

  // Realtime listeners for new messages
  function setupRealtimeListeners(): void {
    // Listen for new communications
    frappe.realtime.on('new_communication', handleNewCommunication);
  }

  function handleNewCommunication(data: unknown): void {
    // Refresh rooms and unread count when new communication arrives
    fetchRooms(true);
    refreshUnreadCount();

    // If we're viewing the relevant room, also refresh messages
    if (currentRoom.value) {
      const commData = data as { phone_no?: string; sender?: string };
      const roomParts = currentRoom.value.roomId.split(':');
      const identifier = roomParts[1];

      if (
        commData.phone_no === identifier ||
        commData.sender === identifier
      ) {
        fetchMessages({ room: currentRoom.value, options: { reset: true } });
      }
    }
  }

  return {
    // State
    currentUser,
    rooms,
    currentRoom,
    messages,
    loadingRooms,
    loadingMessages,
    roomsLoaded,
    messagesLoaded,
    error,
    searchQuery,
    mediumFilter,
    unreadCount,

    // Computed
    filteredRooms,
    currentRoomId,

    // Actions
    initialize,
    fetchRooms,
    fetchMessages,
    handleSendMessage,
    selectRoom,
    setSearchQuery,
    setMediumFilter,
    handleUploadFile,
    refreshUnreadCount,
  };
}

export default useChat;
