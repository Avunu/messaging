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
  removeRoom: (roomId: string) => void;
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
  // Separate guard for "load more" appends so we don't block on loadingRooms
  let fetchingMoreRooms = false;

  // Computed
  const filteredRooms = computed(() => {
    let filtered = rooms.value;

    if (searchQuery.value) {
      // Fuzzy local filter: split query into tokens, each token must match
      // at least one searchable field on the room
      const tokens = searchQuery.value
        .toLowerCase()
        .split(/\s+/)
        .filter((t) => t.length > 0);

      if (tokens.length > 0) {
        filtered = filtered.filter((room) => {
          const haystack = [
            room.roomName,
            room.lastMessage?.content,
            room.roomId,
          ]
            .filter(Boolean)
            .join(' ')
            .toLowerCase();

          return tokens.every((token) => haystack.includes(token));
        });
      }
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
    // Prevent concurrent fetches — use separate guards for reset vs. append
    if (reset && loadingRooms.value) return;
    if (!reset && fetchingMoreRooms) return;

    try {
      error.value = null;

      if (reset) {
        // Only set loadingRooms for initial/reset fetches.
        // This is critical because upstream RoomsList wraps its entire list
        // in v-if="!loadingRooms" — setting it true destroys the DOM and
        // kills scroll position. ChatWindow also clears the current room
        // when loadingRooms becomes true.
        loadingRooms.value = true;
        roomsPage.value = 1;
        rooms.value = [];
        roomsLoaded.value = false;
      } else {
        fetchingMoreRooms = true;
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
        // Append new rooms, avoiding duplicates by roomId
        const existingIds = new Set(rooms.value.map((r) => r.roomId));
        const newRooms = response.rooms.filter((r) => !existingIds.has(r.roomId));
        if (newRooms.length > 0) {
          rooms.value = [...rooms.value, ...newRooms];
        }
      }

      roomsLoaded.value = !response.hasMore;
      roomsPage.value++;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch rooms';
      console.error('Failed to fetch rooms:', err);
    } finally {
      loadingRooms.value = false;
      fetchingMoreRooms = false;
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
          const now = new Date();
          rooms.value[roomIndex] = {
            ...rooms.value[roomIndex],
            lastMessage: {
              content: data.content,
              senderId: currentUser.value?._id ?? '',
              timestamp: `${now.getMonth() + 1}/${now.getDate()}/${now.getFullYear() % 100} ${now.toLocaleTimeString([], {
                hour: 'numeric',
                minute: '2-digit',
                hour12: true,
              })}`,
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

  function removeRoom(roomId: string): void {
    // Remove the room from local state without refetching
    // This preserves the scroll position in the rooms list
    rooms.value = rooms.value.filter((r) => r.roomId !== roomId);

    // If the deleted room was the current room, clear the selection
    if (currentRoom.value?.roomId === roomId) {
      currentRoom.value = null;
      messages.value = [];
    }
  }

  // Watch for search query changes with debounce
  let searchTimeout: ReturnType<typeof setTimeout> | null = null;
  watch(searchQuery, () => {
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      // Don't use reset=true for search-triggered fetches because that
      // sets loadingRooms=true, which destroys/hides the rooms list DOM
      // (including the search input). Instead, fetch quietly and swap.
      fetchRoomsQuiet();
    }, 300);
  });

  /**
   * Fetch rooms without setting loadingRooms, so the DOM (search bar,
   * room list) stays intact. Replaces the rooms array in-place.
   */
  async function fetchRoomsQuiet(): Promise<void> {
    try {
      error.value = null;
      roomsPage.value = 1;

      const response = await getRooms({
        page: roomsPage.value,
        limit: 20,
        search: searchQuery.value,
        medium: mediumFilter.value,
      });

      rooms.value = response.rooms;
      roomsLoaded.value = !response.hasMore;
      roomsPage.value++;
    } catch (err) {
      error.value =
        err instanceof Error ? err.message : 'Failed to fetch rooms';
      console.error('Failed to fetch rooms:', err);
    }
  }

  // Realtime listeners for new messages
  function setupRealtimeListeners(): void {
    // Listen for new communications
    frappe.realtime.on('new_communication', handleNewCommunication);
  }

  function handleNewCommunication(data: unknown): void {
    // Update unread count
    refreshUnreadCount();

    // Parse the incoming communication data
    const commData = data as {
      name?: string;
      phone_no?: string;
      sender?: string;
      recipients?: string;
      communication_medium?: string;
      sent_or_received?: string;
    };

    // Determine the room identifier for this communication
    const medium = commData.communication_medium || 'Email';
    let identifier = '';

    if (medium === 'SMS' || medium === 'Phone') {
      identifier = commData.phone_no || '';
    } else {
      if (commData.sent_or_received === 'Received') {
        identifier = commData.sender || '';
      } else {
        identifier = commData.recipients?.split(',')[0]?.trim() || '';
      }
    }

    const roomId = `${medium}:${identifier}`;

    // Check if this room already exists in our list
    const existingRoomIndex = rooms.value.findIndex((r) => r.roomId === roomId);

    if (existingRoomIndex !== -1) {
      // Room exists - we could update it in place, but for simplicity
      // just move it to the top by removing and re-fetching the first page
      // This will bring the updated room to the top without losing other rooms
      // For now, just trigger a soft refresh of just the room's data
      // We'll update this room's unread count and last message when the user clicks it
    } else {
      // New room - fetch just the first page to get it, but don't reset existing rooms
      // This is a compromise - we prepend new rooms without losing scroll position
      getRooms({ page: 1, limit: 1, search: '', medium: 'All' }).then((response) => {
        if (response.rooms.length > 0) {
          const newRoom = response.rooms.find((r) => r.roomId === roomId);
          if (newRoom && !rooms.value.some((r) => r.roomId === roomId)) {
            // Prepend the new room to the list
            rooms.value = [newRoom, ...rooms.value];
          }
        }
      }).catch((err) => {
        console.error('Failed to fetch new room:', err);
      });
    }

    // If we're viewing the relevant room, also refresh messages
    if (currentRoom.value) {
      const currentRoomParts = currentRoom.value.roomId.split(':');
      const currentIdentifier = currentRoomParts[1];

      if (
        commData.phone_no === currentIdentifier ||
        commData.sender === currentIdentifier ||
        commData.recipients?.includes(currentIdentifier)
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
    removeRoom,
  };
}

export default useChat;
