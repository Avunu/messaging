// Copyright (c) 2025, Avunu LLC
// License: MIT. See LICENSE

/**
 * Chat module exports.
 *
 * This module provides a chat-like messaging interface for Frappe Communications,
 * built with vue-advanced-chat.
 *
 * - bundle.ts: Main Vite entry point with Frappe integration (ChatView, ChatViewSelect)
 * - index.ts: Re-exports for module consumers
 */

// Re-export the Frappe integration from bundle
export * from './bundle';

// Also export component parts for potential reuse
export { default as ChatViewComponent } from './ChatView.vue';
export { useChat } from './useChat';
export * from './types';
export * as api from './api';
