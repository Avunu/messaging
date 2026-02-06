# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
Chat API module for Frappe Communications.

This module provides a chat-like interface for managing email and SMS communications
in Frappe/ERPNext, powered by the vue-advanced-chat component library.
"""

from messaging.messaging.api.chat.api import (
	get_current_user,
	get_messages,
	get_rooms,
	get_unread_count,
	mark_messages_seen,
	notify_new_communication,
	search_rooms,
	send_message,
)

__all__ = [
	"get_current_user",
	"get_messages",
	"get_rooms",
	"get_unread_count",
	"mark_messages_seen",
	"notify_new_communication",
	"search_rooms",
	"send_message",
]
