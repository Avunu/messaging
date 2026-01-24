# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
Helper utilities for the Chat API.

Shared functions used across retrieve, send, and formatting modules.
"""

from datetime import datetime, timedelta
from typing import Any

import frappe
from frappe.query_builder import DocType
from frappe.utils import get_datetime, get_url, now_datetime

from messaging.messaging.api.chat.types import LastMessage, Room, RoomUser, UserStatus


def get_user_avatar(user: str | None) -> str:
	"""
	Get avatar URL for a user.

	Args:
	    user: The user ID or email

	Returns:
	    URL to the user's avatar or a default gravatar
	"""
	if not user:
		return f"{get_url()}/assets/frappe/images/default-avatar.png"

	User = DocType("User")
	result = frappe.qb.from_(User).select(User.user_image).where(User.name == user).limit(1).run(as_dict=True)

	if result and result[0].get("user_image"):
		image = result[0]["user_image"]
		if image.startswith("http"):
			return image
		return f"{get_url()}{image}"

	return f"{get_url()}/assets/frappe/images/default-avatar.png"


def get_user_status(user: str | None) -> UserStatus:
	"""
	Get online/offline status for a user.

	Args:
	    user: The user ID or email

	Returns:
	    UserStatus dict with state and lastChanged
	"""
	if not user:
		return {"state": "offline", "lastChanged": ""}

	User = DocType("User")
	result = (
		frappe.qb.from_(User).select(User.last_active).where(User.name == user).limit(1).run(as_dict=True)
	)

	if result and result[0].get("last_active"):
		last_active = get_datetime(result[0]["last_active"])
		if last_active is None:
			return {"state": "offline", "lastChanged": ""}
		# Consider online if active in last 5 minutes
		if last_active > now_datetime() - timedelta(minutes=5):
			return {
				"state": "online",
				"lastChanged": last_active.strftime("%Y-%m-%d %H:%M:%S"),
			}
		return {
			"state": "offline",
			"lastChanged": last_active.strftime("%Y-%m-%d %H:%M:%S"),
		}

	return {"state": "offline", "lastChanged": ""}


def format_room_id(
	medium: str, identifier: str, reference_doctype: str | None = None, reference_name: str | None = None
) -> str:
	"""
	Generate a unique room ID from communication details.

	Args:
	    medium: Communication medium (Email, SMS, etc.)
	    identifier: Phone number or email address
	    reference_doctype: Linked document type
	    reference_name: Linked document name

	Returns:
	    Unique room identifier string
	"""
	base = f"{medium}:{identifier}"
	if reference_doctype and reference_name:
		base = f"{base}:{reference_doctype}:{reference_name}"
	return base


def parse_room_id(room_id: str) -> dict[str, str | None]:
	"""
	Parse a room ID back into its components.

	Args:
	    room_id: The room identifier string
	    Format: medium:identifier

	Returns:
	    Dict with medium, identifier
	"""
	parts = room_id.split(":")
	result: dict[str, str | None] = {
		"medium": parts[0] if len(parts) > 0 else None,
		"identifier": parts[1] if len(parts) > 1 else None,
		"reference_doctype": parts[2] if len(parts) > 2 else None,
		"reference_name": parts[3] if len(parts) > 3 else None,
	}
	return result


def get_contact_from_identifier(medium: str, identifier: str) -> dict[str, Any] | None:
	"""
	Look up contact information from phone/email.

	Args:
	    medium: Communication medium (Email, SMS)
	    identifier: Phone number or email address

	Returns:
	    Contact dict or None if not found
	"""
	Contact = DocType("Contact")

	if medium == "SMS" or medium == "Phone":
		ContactPhone = DocType("Contact Phone")
		result = (
			frappe.qb.from_(Contact)
			.join(ContactPhone)
			.on(Contact.name == ContactPhone.parent)
			.select(
				Contact.name,
				Contact.full_name,
				Contact.image,
				Contact.user,
				Contact.email_id,
			)
			.where(ContactPhone.phone == identifier)
			.limit(1)
			.run(as_dict=True)
		)
	else:
		ContactEmail = DocType("Contact Email")
		result = (
			frappe.qb.from_(Contact)
			.join(ContactEmail)
			.on(Contact.name == ContactEmail.parent)
			.select(
				Contact.name,
				Contact.full_name,
				Contact.image,
				Contact.user,
				Contact.email_id,
			)
			.where(ContactEmail.email_id == identifier)
			.limit(1)
			.run(as_dict=True)
		)

	return result[0] if result else None


def build_room_from_thread(thread: dict[str, Any], current_user_id: str) -> Room:
	"""
	Build a Room object from a communication thread.

	Args:
	    thread: Thread data from database query
	    current_user_id: Current user's ID

	Returns:
	    Room dict matching vue-advanced-chat format
	"""
	medium = thread.get("communication_medium", "Email")

	# Get the external party identifier from the thread data
	identifier = thread.get("_external_identifier") or ""

	# Build simple room ID: just medium:identifier
	room_id = f"{medium}:{identifier}"

	# Get contact info for the external party
	contact = get_contact_from_identifier(medium, identifier)

	# Build room name
	if contact:
		room_name = contact.get("full_name") or contact.get("name") or identifier
		avatar = get_user_avatar(contact.get("user"))
		contact_name = contact.get("name")
	else:
		room_name = thread.get("_external_name") or thread.get("sender_full_name") or identifier or "Unknown"
		avatar = get_user_avatar(None)
		contact_name = None

	# Build users list
	users: list[RoomUser] = [
		{
			"_id": current_user_id,
			"username": frappe.get_value("User", current_user_id, "full_name") or current_user_id,
			"avatar": get_user_avatar(current_user_id),
			"status": get_user_status(current_user_id),
		}
	]

	# Build status text showing medium and address
	status_text = f"{medium}: {identifier}" if identifier else medium

	if contact and contact.get("user"):
		users.append(
			{
				"_id": contact["user"],
				"username": contact.get("full_name", identifier),
				"avatar": get_user_avatar(contact.get("user")),
				"status": {"state": "offline", "lastChanged": status_text},
			}
		)
	else:
		users.append(
			{
				"_id": identifier,
				"username": thread.get("sender_full_name") or identifier,
				"avatar": avatar,
				"status": {"state": "offline", "lastChanged": status_text},
			}
		)

	# Build last message
	if medium == "Email":
		last_message_content = thread.get("subject", "") or "(No subject)"
	else:
		from frappe.utils import strip_html_tags

		raw_content = thread.get("text_content") or thread.get("content", "")
		if "<" in raw_content and ">" in raw_content:
			raw_content = strip_html_tags(raw_content)
		last_message_content = raw_content[:100] if raw_content else "(No content)"

	if thread.get("sent_or_received") == "Received":
		last_message_sender = thread.get("sender", identifier)
	else:
		last_message_sender = thread.get("user") or thread.get("sender") or current_user_id

	# Check if this room has unreplied messages (for visual indicator)
	has_unreplied = thread.get("_has_unreplied", False)

	last_message: LastMessage = {
		"content": last_message_content,
		"senderId": last_message_sender,
		"timestamp": thread.get("communication_date", "").strftime("%H:%M")
		if thread.get("communication_date")
		else "",
		"seen": bool(thread.get("seen")),
		"new": not bool(thread.get("seen")) and thread.get("sent_or_received") == "Received",
	}

	room: Room = {
		"roomId": room_id,
		"roomName": room_name,
		"avatar": avatar,
		"users": users,
		"unreadCount": thread.get("unread_count", 0),
		"index": thread.get("communication_date", datetime.now()),
		"lastMessage": last_message,
		"typingUsers": [],
		"communicationMedium": medium,
		"contactName": contact_name,
		"phoneNo": thread.get("phone_no"),
		"emailId": identifier if "@" in identifier else None,
		"referenceDoctype": None,
		"referenceName": None,
		"hasUnreplied": has_unreplied,  # Add unreplied status to room
	}

	return room
