# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
Chat API module for Frappe Communications.

This module provides a chat-like interface for managing email and SMS communications
in Frappe/ERPNext, powered by the vue-advanced-chat component library.
"""

from messaging.messaging.api.chat.api import (
    get_rooms,
    get_messages,
    send_message,
    mark_messages_seen,
    get_current_user,
    search_rooms,
    get_unread_count,
    notify_new_communication,
)

__all__ = [
    "get_rooms",
    "get_messages",
    "send_message",
    "mark_messages_seen",
    "get_current_user",
    "search_rooms",
    "get_unread_count",
    "notify_new_communication",
]
