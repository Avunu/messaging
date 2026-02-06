// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * TypeScript type definitions for the Messaging Chat interface.
 * These types match vue-advanced-chat's expected structures and extend
 * them with Frappe-specific fields.
 */

// ====================
// vue-advanced-chat types
// ====================

export type StringNumber = string | number;

export interface UserStatus {
  state: 'online' | 'offline';
  lastChanged: string;
}

export interface RoomUser {
  _id: string;
  username: string;
  avatar: string;
  status: UserStatus;
}

export interface MessageFile {
  name: string;
  type: string;
  extension: string;
  url: string;
  localUrl?: string;
  preview?: string;
  size?: number;
  audio?: boolean;
  duration?: number;
  progress?: number;
  blob?: Blob;
}

export interface LastMessage {
  content: string;
  senderId: string;
  username?: string;
  timestamp?: string;
  saved?: boolean;
  distributed?: boolean;
  seen?: boolean;
  new?: boolean;
  files?: MessageFile[];
}

export interface MessageReactions {
  [key: string]: StringNumber[];
}

export interface ReplyMessage {
  _id: string;
  content: string;
  senderId: string;
  files?: MessageFile[];
}

// ====================
// Extended Frappe Types
// ====================

export type CommunicationMedium = 'Email' | 'SMS' | 'Phone' | 'Chat' | 'Other';
export type SentOrReceived = 'Sent' | 'Received';

/**
 * Chat room representing a conversation thread.
 * Maps to Communications grouped by sender/recipient.
 */
export interface Room {
  roomId: string;
  roomName: string;
  avatar: string;
  users: RoomUser[];
  unreadCount?: number;
  index?: StringNumber | Date;
  lastMessage?: LastMessage;
  typingUsers?: string[];
  // Frappe-specific extensions
  communicationMedium?: CommunicationMedium;
  contactName?: string | null;
  phoneNo?: string | null;
  emailId?: string | null;
  referenceDoctype?: string | null;
  referenceName?: string | null;
}

/**
 * Individual message within a conversation.
 * Maps to a Frappe Communication document.
 */
export interface Message {
  _id: string;
  senderId: string;
  indexId?: StringNumber;
  content?: string;
  username?: string;
  avatar?: string;
  date?: string;
  timestamp?: string;
  system?: boolean;
  saved?: boolean;
  distributed?: boolean;
  seen?: boolean;
  deleted?: boolean;
  edited?: boolean;
  failure?: boolean;
  disableActions?: boolean;
  disableReactions?: boolean;
  files?: MessageFile[];
  reactions?: MessageReactions;
  replyMessage?: ReplyMessage;
  // Frappe-specific extensions
  communicationName?: string;
  communicationMedium?: CommunicationMedium;
  sentOrReceived?: SentOrReceived;
  subject?: string | null;
  referenceDoctype?: string | null;
  referenceName?: string | null;
}

/**
 * Current logged-in user information.
 */
export interface CurrentUser {
  _id: string;
  username: string;
  avatar: string;
  email: string;
  fullName: string;
  status: UserStatus;
}

// ====================
// API Request/Response Types
// ====================

export interface RoomQueryParams {
  page?: number;
  limit?: number;
  search?: string;
  medium?: CommunicationMedium | 'All';
}

export interface MessageQueryParams {
  room_id: string;
  page?: number;
  limit?: number;
  before_id?: string;
}

export interface SendMessageParams {
  room_id: string;
  content: string;
  files?: MessageFile[];
  reply_message_id?: string;
  subject?: string;
}

export interface RoomsResponse {
  rooms: Room[];
  total: number;
  page: number;
  hasMore: boolean;
}

export interface MessagesResponse {
  messages: Message[];
  total: number;
  page: number;
  hasMore: boolean;
}

export interface SendMessageResponse {
  success: boolean;
  message: Message | null;
  error: string | null;
}

export interface MarkSeenResponse {
  success: boolean;
  count: number;
}

// ====================
// vue-advanced-chat Event Types
// ====================

export interface FetchMessagesEvent {
  room: Room;
  options?: {
    reset?: boolean;
  };
}

export interface SendMessageEvent {
  roomId: string;
  content: string;
  files?: MessageFile[];
  replyMessage?: {
    _id: string;
    content: string;
    senderId: string;
    files?: MessageFile[];
  };
  usersTag?: string[];
}

export interface EditMessageEvent {
  roomId: string;
  messageId: string;
  newContent: string;
}

export interface OpenFileEvent {
  message: Message;
  file: MessageFile;
}

export interface RoomActionEvent {
  roomId: string;
  action: {
    name: string;
    title: string;
  };
}

export interface MessageActionEvent {
  roomId: string;
  action: {
    name: string;
    title: string;
  };
  message: Message;
}

export interface TypingMessageEvent {
  roomId: string;
  message: string;
}

// ====================
// Custom Action Types
// ====================

export interface CustomAction {
  name: string;
  title: string;
}

export interface MessageAction {
  name: string;
  title: string;
  onlyMe?: boolean;
}

// ====================
// Component Props Types
// ====================

export interface TextFormatting {
  disabled?: boolean;
  italic?: string;
  bold?: string;
  strike?: string;
  underline?: string;
  multilineCode?: string;
  inlineCode?: string;
}

export interface LinkOptions {
  disabled?: boolean;
  target?: string;
  rel?: string;
}

export interface UsernameOptions {
  minUsers?: number;
  currentUser?: boolean;
}

export interface AutoScroll {
  send?: {
    new?: boolean;
    newAfterScrollUp?: boolean;
  };
  receive?: {
    new?: boolean;
    newAfterScrollUp?: boolean;
  };
}

// ====================
// Frappe Integration Types
// ====================

/**
 * Frappe call response wrapper.
 */
export interface FrappeCallResponse<T> {
  message: T;
  exc?: string;
  exc_type?: string;
  _server_messages?: string;
}

/**
 * Frappe session user info.
 */
export interface FrappeUser {
  name: string;
  full_name: string;
  user_image: string | null;
  email: string;
  language: string;
  time_zone: string;
}

/**
 * Frappe form document.
 */
export interface FrappeDoc {
  doctype: string;
  name: string;
  [key: string]: unknown;
}

// ====================
// Store/State Types
// ====================

export interface ChatState {
  currentUser: CurrentUser | null;
  rooms: Room[];
  currentRoom: Room | null;
  messages: Message[];
  loadingRooms: boolean;
  loadingMessages: boolean;
  roomsLoaded: boolean;
  messagesLoaded: boolean;
  error: string | null;
  filter: {
    search: string;
    medium: CommunicationMedium | 'All';
  };
}

export type ChatAction =
  | { type: 'SET_CURRENT_USER'; payload: CurrentUser }
  | { type: 'SET_ROOMS'; payload: Room[] }
  | { type: 'ADD_ROOMS'; payload: Room[] }
  | { type: 'SET_CURRENT_ROOM'; payload: Room | null }
  | { type: 'SET_MESSAGES'; payload: Message[] }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'UPDATE_MESSAGE'; payload: Partial<Message> & { _id: string } }
  | { type: 'SET_LOADING_ROOMS'; payload: boolean }
  | { type: 'SET_LOADING_MESSAGES'; payload: boolean }
  | { type: 'SET_ROOMS_LOADED'; payload: boolean }
  | { type: 'SET_MESSAGES_LOADED'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_FILTER'; payload: Partial<ChatState['filter']> }
  | { type: 'RESET' };
