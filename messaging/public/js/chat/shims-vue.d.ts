// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Vue component type declarations for TypeScript.
 */

declare module '*.vue' {
  import type { DefineComponent } from 'vue';
  const component: DefineComponent<
    Record<string, unknown>,
    Record<string, unknown>,
    unknown
  >;
  export default component;
}

declare module 'vue-advanced-chat' {
  export function register(): void;

  export interface Room {
    roomId: string;
    roomName: string;
    avatar: string;
    users: RoomUser[];
    unreadCount?: number;
    index?: string | number | Date;
    lastMessage?: LastMessage;
    typingUsers?: string[];
  }

  export interface RoomUser {
    _id: string;
    username: string;
    avatar: string;
    status: UserStatus;
  }

  export interface UserStatus {
    state: 'online' | 'offline';
    lastChanged: string;
  }

  export interface Message {
    _id: string;
    senderId: string;
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
    files?: MessageFile[];
    replyMessage?: ReplyMessage;
  }

  export interface MessageFile {
    name: string;
    type: string;
    extension: string;
    url: string;
    size?: number;
  }

  export interface LastMessage {
    content: string;
    senderId: string;
    timestamp?: string;
    seen?: boolean;
    new?: boolean;
  }

  export interface ReplyMessage {
    _id: string;
    content: string;
    senderId: string;
  }
}
