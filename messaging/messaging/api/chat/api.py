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
from messaging.messaging.api.chat.send import archive_room as _archive_room
from messaging.messaging.api.chat.send import delete_room as _delete_room
from messaging.messaging.api.chat.send import mark_messages_seen as _mark_messages_seen
from messaging.messaging.api.chat.send import send_message as _send_message
from messaging.messaging.api.chat.types import (
	CurrentUser,
	MarkSeenResponse,
	MessagesResponse,
	Room,
	RoomActionResponse,
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


@frappe.whitelist()
def archive_room(room_id: str) -> RoomActionResponse:
	"""
	Archive all messages in a room by setting status to 'Closed'.

	Args:
	    room_id: The room identifier

	Returns:
	    RoomActionResponse with success status and count of updated messages
	"""
	return _archive_room(room_id=room_id)


@frappe.whitelist()
def delete_room(room_id: str) -> RoomActionResponse:
	"""
	Delete all messages in a room (moves to trash).

	Args:
	    room_id: The room identifier

	Returns:
	    RoomActionResponse with success status and count of deleted messages
	"""
	return _delete_room(room_id=room_id)


def notify_new_communication(doc: Any, method: str | None = None) -> None:
	"""
	Hook function to notify connected clients of new communications.

	Called after a Communication is inserted to trigger realtime updates
	in the chat interface, and send push notifications for received messages.

	Also handles SMS opt-out requests when a user texts "STOP".

	Args:
	    doc: The Communication document
	    method: The hook method name (unused)
	"""
	if doc.communication_type != "Communication":
		return

	# Handle SMS opt-out requests
	if doc.communication_medium == "SMS" and doc.sent_or_received == "Received" and doc.phone_no:
		_handle_sms_opt_out(doc)

	# Publish realtime event for chat updates
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

	# Send push notifications for received messages
	if doc.sent_or_received == "Received":
		frappe.enqueue(
			_send_push_for_received,
			queue="short",
			doc_name=doc.name,
			sender=doc.sender,
			phone_no=doc.phone_no,
			content=doc.text_content or doc.content or "",
			medium=doc.communication_medium,
			subject=doc.subject,
			now=frappe.flags.in_test,
		)


def _send_push_for_received(
	doc_name: str,
	sender: str,
	phone_no: str,
	content: str,
	medium: str,
	subject: str | None = None,
) -> None:
	"""
	Background job: send push notifications to all users with active subscriptions
	when a new message is received.

	Args:
	    doc_name: Communication document name
	    sender: Sender identifier (email or phone)
	    phone_no: Phone number (for SMS/Phone)
	    content: Message content
	    medium: Communication medium (Email, SMS, etc.)
	    subject: Email subject line
	"""
	# Determine sender display name via Contact lookup
	from messaging.messaging.api.chat.helpers import get_contact_from_identifier
	from messaging.messaging.api.chat.push import send_push_to_user

	identifier = phone_no if medium in ("SMS", "Phone") else sender
	room_id = f"{medium}:{identifier}"

	contact = get_contact_from_identifier(identifier, medium)
	sender_name = contact.get("contact_name") if contact else identifier

	# Truncate body for notification
	body = (content or "").strip()
	# Strip HTML tags for notification body
	import re

	body = re.sub(r"<[^>]+>", "", body)
	if len(body) > 200:
		body = body[:200] + "..."

	title = f"{sender_name}"
	if subject and medium == "Email":
		title = f"{sender_name}: {subject}"

	# Get all users with System Manager or any desk access who can read Communication
	# Only send to users who have active push subscriptions (opted-in)
	subscribed_users = frappe.get_all(
		"Push Subscription",
		fields=["user"],
		distinct=True,
	)

	for row in subscribed_users:
		user = row["user"]
		if user == "Guest":
			continue

		try:
			send_push_to_user(
				user=user,
				title=title,
				body=body,
				room_id=room_id,
				communication_name=doc_name,
				url="/app/communication/view/chat",
			)
		except Exception as e:
			frappe.log_error(
				f"Push notification failed for user {user}: {e}",
				"Push Notification Error",
			)


def _handle_sms_opt_out(doc: Any) -> None:
	"""
	Handle SMS opt-out requests.

	If the message content is "STOP" (case-insensitive), unset the consent_sms
	field for the contact associated with the phone number and send a confirmation.

	Args:
	    doc: The Communication document
	"""
	# Get message content and check if it's a stop request
	content = (doc.text_content or doc.content or "").strip().lower()

	if content != "stop":
		return

	phone_no = doc.phone_no

	# Find contacts with this phone number
	from frappe.query_builder import DocType

	Contact = DocType("Contact")
	ContactPhone = DocType("Contact Phone")

	contacts = (
		frappe.qb.from_(Contact)
		.join(ContactPhone)
		.on(Contact.name == ContactPhone.parent)
		.select(Contact.name)
		.where(ContactPhone.phone == phone_no)
		.run(as_dict=True)
	)

	if not contacts:
		# No contact found, log and return
		frappe.log_error(
			f"SMS opt-out received from {phone_no} but no matching contact found",
			"SMS Opt-Out - No Contact",
		)
		return

	# Update consent_sms for all matching contacts
	for contact in contacts:
		frappe.db.set_value("Contact", contact["name"], "unsubscribed", 1)
		frappe.log_error(
			f"SMS opt-out processed for contact {contact['name']} (phone: {phone_no})",
			"SMS Opt-Out Processed",
		)

	frappe.db.commit()

	# Send confirmation SMS
	_send_opt_out_confirmation(phone_no)


def _send_opt_out_confirmation(phone_no: str) -> None:
	"""
	Send SMS confirmation that the user has been removed from the broadcast list.

	Args:
	    phone_no: The phone number to send confirmation to
	"""
	confirmation_message = "You have been removed from our broadcast list."

	try:
		# Create Communication record for the outgoing SMS
		comm_doc = frappe.get_doc(
			{
				"doctype": "Communication",
				"communication_type": "Communication",
				"communication_medium": "SMS",
				"subject": "SMS Opt-Out Confirmation",
				"content": confirmation_message,
				"text_content": confirmation_message,
				"phone_no": phone_no,
				"sender": frappe.session.user,
				"recipients": phone_no,
				"sent_or_received": "Sent",
			}
		)
		comm_doc.insert(ignore_permissions=True)

		# Send SMS via configured provider
		from frappe.core.doctype.sms_settings.sms_settings import send_sms

		send_sms([phone_no], confirmation_message)
		comm_doc.db_set("delivery_status", "Sent")

	except Exception as e:
		frappe.log_error(
			f"Failed to send SMS opt-out confirmation to {phone_no}: {e}",
			"SMS Opt-Out Confirmation Failed",
		)
