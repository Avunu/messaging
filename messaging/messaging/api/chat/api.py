# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
Chat API endpoints for Frappe Communications.

This module provides whitelist API endpoints for the vue-advanced-chat frontend,
enabling a chat-like interface for email and SMS communications.

The implementation is split across several modules:
- helpers.py: Shared utility functions
- formatting.py: Content parsing and formatting
- retrieve.py: Data retrieval (rooms, messages, users)
- send.py: Message sending and status updates
"""

from typing import Any

import frappe

from messaging.messaging.api.chat.retrieve import get_current_user as _get_current_user
from messaging.messaging.api.chat.retrieve import get_messages as _get_messages
from messaging.messaging.api.chat.retrieve import get_rooms as _get_rooms
from messaging.messaging.api.chat.retrieve import get_unread_count as _get_unread_count
from messaging.messaging.api.chat.send import mark_messages_seen as _mark_messages_seen
from messaging.messaging.api.chat.send import send_message as _send_message
from messaging.messaging.api.chat.types import (
	CurrentUser,
	MarkSeenResponse,
	MessagesResponse,
	Room,
	RoomsResponse,
	SendMessageResponse,
)


@frappe.whitelist()
def get_current_user() -> CurrentUser:
	"""
	Get information about the currently logged-in user.

	Returns:
	    CurrentUser dict with user details for vue-advanced-chat
	"""
	return _get_current_user()


@frappe.whitelist()
def get_rooms(
	page: int = 1,
	limit: int = 20,
	search: str = "",
	medium: str = "All",
) -> RoomsResponse:
	"""
	Get list of chat rooms (conversation threads).

	Args:
	    page: Page number for pagination (1-indexed)
	    limit: Number of rooms per page
	    search: Search query for filtering rooms
	    medium: Filter by communication medium (Email, SMS, All)

	Returns:
	    RoomsResponse with list of rooms and pagination info
	"""
	return _get_rooms(page=page, limit=limit, search=search, medium=medium)


@frappe.whitelist()
def get_messages(
	room_id: str,
	page: int = 1,
	limit: int = 50,
	before_id: str = "",
) -> MessagesResponse:
	"""
	Get messages for a specific room (conversation thread).

	Args:
	    room_id: The room identifier (format: medium:identifier)
	    page: Page number for pagination (1-indexed)
	    limit: Number of messages per page
	    before_id: Get messages before this message ID (for infinite scroll)

	Returns:
	    MessagesResponse with list of messages and pagination info
	"""
	return _get_messages(room_id=room_id, page=page, limit=limit, before_id=before_id)


@frappe.whitelist()
def send_message(
	room_id: str,
	content: str,
	files: str | list | None = None,
	reply_message_id: str = "",
	subject: str = "",
) -> SendMessageResponse:
	"""
	Send a new message in a conversation.

	Args:
	    room_id: The room identifier
	    content: Message content
	    files: List of file attachments (JSON string or list)
	    reply_message_id: Communication name of message being replied to
	    subject: Email subject (optional, auto-generated if empty)

	Returns:
	    SendMessageResponse with the created message or error
	"""
	return _send_message(
		room_id=room_id,
		content=content,
		files=files,
		reply_message_id=reply_message_id,
		subject=subject,
	)


@frappe.whitelist()
def mark_messages_seen(room_id: str) -> MarkSeenResponse:
	"""
	Mark all messages in a room as seen.

	Args:
	    room_id: The room identifier

	Returns:
	    MarkSeenResponse with success status and count of updated messages
	"""
	return _mark_messages_seen(room_id=room_id)


@frappe.whitelist()
def search_rooms(query: str, limit: int = 10) -> list[Room]:
	"""
	Search for rooms matching a query.

	Args:
	    query: Search string
	    limit: Maximum results to return

	Returns:
	    List of matching Room objects
	"""
	return _get_rooms(page=1, limit=limit, search=query)["rooms"]


@frappe.whitelist()
def get_unread_count() -> int:
	"""
	Get total count of unread messages across all rooms.

	Returns:
	    Total unread message count
	"""
	return _get_unread_count()


def notify_new_communication(doc: Any, method: str | None = None) -> None:
	"""
	Hook function to notify connected clients of new communications.

	Called after a Communication is inserted to trigger realtime updates
	in the chat interface.

	Args:
	    doc: The Communication document
	    method: The hook method name (unused)
	"""
	if doc.communication_type != "Communication":
		return

	frappe.publish_realtime(
		"new_communication",
		{
			"name": doc.name,
			"phone_no": doc.phone_no,
			"sender": doc.sender,
			"recipients": doc.recipients,
			"communication_medium": doc.communication_medium,
			"sent_or_received": doc.sent_or_received,
		},
		after_commit=True,
	)
