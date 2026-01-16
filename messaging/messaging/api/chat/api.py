# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
Chat API endpoints for Frappe Communications.

This module provides whitelist API endpoints for the vue-advanced-chat frontend,
enabling a chat-like interface for email and SMS communications.
Uses Frappe Query Builder exclusively for database operations.
"""

from datetime import datetime, timedelta
from typing import Any, Literal, cast

import frappe
from frappe import _
from frappe.query_builder import DocType, Order
from frappe.query_builder.functions import Count
from frappe.utils import cint, get_datetime, get_url, now_datetime

from messaging.messaging.api.chat.types import (
	CurrentUser,
	LastMessage,
	MarkSeenResponse,
	Message,
	MessageFile,
	MessagesResponse,
	ReplyMessage,
	Room,
	RoomsResponse,
	RoomUser,
	SendMessageResponse,
	UserStatus,
)


def _get_user_avatar(user: str | None) -> str:
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


def _get_user_status(user: str | None) -> UserStatus:
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


def _format_room_id(
	medium: str, identifier: str, reference_doctype: str | None, reference_name: str | None
) -> str:
	"""
	Generate a unique room ID from communication details.

	For SMS: Uses phone number
	For Email: Uses email address
	If linked to a document: Includes reference

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


def _parse_room_id(room_id: str) -> dict[str, str | None]:
	"""
	Parse a room ID back into its components.

	Args:
	    room_id: The room identifier string

	Returns:
	    Dict with medium, identifier, reference_doctype, reference_name
	"""
	parts = room_id.split(":")
	result: dict[str, str | None] = {
		"medium": parts[0] if len(parts) > 0 else None,
		"identifier": parts[1] if len(parts) > 1 else None,
		"reference_doctype": parts[2] if len(parts) > 2 else None,
		"reference_name": parts[3] if len(parts) > 3 else None,
	}
	return result


def _get_contact_from_identifier(medium: str, identifier: str) -> dict[str, Any] | None:
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


def _build_room_from_thread(thread: dict[str, Any], current_user_id: str) -> Room:
	"""
	Build a Room object from a communication thread.

	Args:
	    thread: Thread data from database query
	    current_user_id: Current user's ID

	Returns:
	    Room dict matching vue-advanced-chat format
	"""
	medium = thread.get("communication_medium", "Email")

	# Choose identifier based on communication medium
	if medium in ("Phone", "SMS"):
		identifier = thread.get("phone_no") or ""
	else:
		# Email or other mediums - use sender/recipients
		identifier = thread.get("sender") or thread.get("recipients") or ""

	ref_dt = thread.get("reference_doctype")
	ref_name = thread.get("reference_name")

	room_id = _format_room_id(medium, identifier, ref_dt, ref_name)

	# Get contact info
	contact = _get_contact_from_identifier(medium, identifier)

	# Build room name
	if contact:
		room_name = contact.get("full_name", identifier)
		avatar = _get_user_avatar(contact.get("user"))
		contact_name = contact.get("name")
	else:
		room_name = thread.get("sender_full_name") or identifier
		avatar = _get_user_avatar(None)
		contact_name = None

	# Add reference to room name if exists
	if ref_dt and ref_name:
		room_name = f"{room_name} ({ref_dt}: {ref_name})"

	# Build users list - current user and the contact
	users: list[RoomUser] = [
		{
			"_id": current_user_id,
			"username": frappe.get_value("User", current_user_id, "full_name") or current_user_id,
			"avatar": _get_user_avatar(current_user_id),
			"status": _get_user_status(current_user_id),
		}
	]

	if contact and contact.get("user"):
		users.append(
			{
				"_id": contact["user"],
				"username": contact.get("full_name", identifier),
				"avatar": _get_user_avatar(contact.get("user")),
				"status": _get_user_status(contact.get("user")),
			}
		)
	else:
		# External contact (no user account)
		users.append(
			{
				"_id": identifier,
				"username": thread.get("sender_full_name") or identifier,
				"avatar": avatar,
				"status": {"state": "offline", "lastChanged": ""},
			}
		)

	# Build last message
	last_message: LastMessage = {
		"content": thread.get("content", "")[:100] or thread.get("subject", ""),
		"senderId": thread.get("sender", identifier)
		if thread.get("sent_or_received") == "Received"
		else current_user_id,
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
		"emailId": thread.get("sender") if "@" in (thread.get("sender") or "") else None,
		"referenceDoctype": ref_dt,
		"referenceName": ref_name,
	}

	return room


@frappe.whitelist()
def get_current_user() -> CurrentUser:
	"""
	Get information about the currently logged-in user.

	Returns:
	    CurrentUser dict with user details for vue-advanced-chat
	"""
	user = frappe.session.user

	User = DocType("User")
	result = (
		frappe.qb.from_(User)
		.select(
			User.name,
			User.full_name,
			User.user_image,
			User.email,
			User.last_active,
		)
		.where(User.name == user)
		.limit(1)
		.run(as_dict=True)
	)

	if not result:
		frappe.throw(_("User not found"), frappe.DoesNotExistError)

	user_data = result[0]

	return {
		"_id": user_data["name"],
		"username": user_data.get("full_name") or user_data["name"],
		"avatar": _get_user_avatar(user_data["name"]),
		"email": user_data.get("email", ""),
		"fullName": user_data.get("full_name") or user_data["name"],
		"status": _get_user_status(user_data["name"]),
	}


@frappe.whitelist()
def get_rooms(
	page: int = 1,
	limit: int = 20,
	search: str = "",
	medium: str = "All",
) -> RoomsResponse:
	"""
	Get list of chat rooms (conversation threads).

	Groups Communications by sender/recipient to create conversation threads.
	Each unique phone number or email address becomes a "room".

	Args:
	    page: Page number for pagination (1-indexed)
	    limit: Number of rooms per page
	    search: Search query for filtering rooms
	    medium: Filter by communication medium (Email, SMS, All)

	Returns:
	    RoomsResponse with list of rooms and pagination info
	"""
	page = cint(page) or 1
	limit = cint(limit) or 20
	offset = (page - 1) * limit
	current_user_id = frappe.session.user

	Communication = DocType("Communication")

	# Build base query for grouping conversations
	# Group by phone_no for SMS, or sender/recipients for Email
	base_query = (
		frappe.qb.from_(Communication)
		.select(
			Communication.name,
			Communication.subject,
			Communication.content,
			Communication.text_content,
			Communication.sender,
			Communication.sender_full_name,
			Communication.recipients,
			Communication.phone_no,
			Communication.communication_medium,
			Communication.communication_date,
			Communication.sent_or_received,
			Communication.seen,
			Communication.reference_doctype,
			Communication.reference_name,
			Communication.status,
		)
		.where(Communication.communication_type == "Communication")
		.orderby(Communication.communication_date, order=Order.desc)
	)

	# Filter by medium
	if medium and medium != "All":
		base_query = base_query.where(Communication.communication_medium == medium)

	# Search filter
	if search:
		search_pattern = f"%{search}%"
		base_query = base_query.where(
			(Communication.subject.like(search_pattern))
			| (Communication.content.like(search_pattern))
			| (Communication.sender.like(search_pattern))
			| (Communication.sender_full_name.like(search_pattern))
			| (Communication.recipients.like(search_pattern))
			| (Communication.phone_no.like(search_pattern))
		)

	# Get all matching communications
	all_comms = base_query.run(as_dict=True)

	# Group into rooms (by identifier + reference)
	room_map: dict[str, dict[str, Any]] = {}

	for comm in all_comms:
		medium_type = comm.get("communication_medium", "Email")
		if medium_type in ("SMS", "Phone"):
			identifier = comm.get("phone_no") or comm.get("sender") or ""
		else:
			# For email, use the external party's email
			if comm.get("sent_or_received") == "Received":
				identifier = comm.get("sender") or ""
			else:
				identifier = (
					comm.get("recipients", "").split(",")[0].strip() if comm.get("recipients") else ""
				)

		ref_dt = comm.get("reference_doctype")
		ref_name = comm.get("reference_name")
		room_id = _format_room_id(medium_type, identifier, ref_dt, ref_name)

		# Track the most recent communication per room
		if room_id not in room_map:
			room_map[room_id] = {
				**comm,
				"unread_count": 0,
			}

		# Count unread for received messages
		if comm.get("sent_or_received") == "Received" and not comm.get("seen"):
			room_map[room_id]["unread_count"] = room_map[room_id].get("unread_count", 0) + 1

	# Convert to room objects and paginate
	user_id_str = str(current_user_id or "")
	all_rooms = [_build_room_from_thread(thread, user_id_str) for thread in room_map.values()]

	# Sort by most recent
	all_rooms.sort(
		key=lambda r: r.get("index") or datetime.min,
		reverse=True,
	)

	total = len(all_rooms)
	paginated_rooms = all_rooms[offset : offset + limit]

	return {
		"rooms": paginated_rooms,
		"total": total,
		"page": page,
		"hasMore": offset + limit < total,
	}


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
	    room_id: The room identifier (format: medium:identifier[:ref_dt:ref_name])
	    page: Page number for pagination (1-indexed)
	    limit: Number of messages per page
	    before_id: Get messages before this message ID (for infinite scroll)

	Returns:
	    MessagesResponse with list of messages and pagination info
	"""
	page = cint(page) or 1
	limit = cint(limit) or 50
	current_user_id: str = str(frappe.session.user or "")

	# Parse room ID
	room_parts = _parse_room_id(room_id)
	medium = room_parts.get("medium")
	identifier = room_parts.get("identifier")
	ref_dt = room_parts.get("reference_doctype")
	ref_name = room_parts.get("reference_name")

	if not medium or not identifier:
		return {
			"messages": [],
			"total": 0,
			"page": page,
			"hasMore": False,
		}

	Communication = DocType("Communication")
	File = DocType("File")

	# Build query for this conversation thread
	query = (
		frappe.qb.from_(Communication)
		.select(
			Communication.name,
			Communication.subject,
			Communication.content,
			Communication.text_content,
			Communication.sender,
			Communication.sender_full_name,
			Communication.recipients,
			Communication.phone_no,
			Communication.communication_medium,
			Communication.communication_date,
			Communication.sent_or_received,
			Communication.seen,
			Communication.status,
			Communication.delivery_status,
			Communication.reference_doctype,
			Communication.reference_name,
			Communication.has_attachment,
			Communication.in_reply_to,
		)
		.where(Communication.communication_type == "Communication")
		.where(Communication.communication_medium == medium)
	)

	# Filter by identifier (phone or email)
	if medium in ("SMS", "Phone"):
		query = query.where(Communication.phone_no == identifier)
	else:
		# Email - match either sender or recipients
		query = query.where(
			(Communication.sender == identifier) | (Communication.recipients.like(f"%{identifier}%"))
		)

	# Filter by reference if provided
	if ref_dt and ref_name:
		query = query.where(Communication.reference_doctype == ref_dt)
		query = query.where(Communication.reference_name == ref_name)

	# Order by date (oldest first for chat display)
	query = query.orderby(Communication.communication_date, order=Order.asc)

	# Get total count
	count_query = (
		frappe.qb.from_(Communication)
		.select(Count(Communication.name))
		.where(Communication.communication_type == "Communication")
		.where(Communication.communication_medium == medium)
	)

	if medium in ("SMS", "Phone"):
		count_query = count_query.where(Communication.phone_no == identifier)
	else:
		count_query = count_query.where(
			(Communication.sender == identifier) | (Communication.recipients.like(f"%{identifier}%"))
		)

	if ref_dt and ref_name:
		count_query = count_query.where(Communication.reference_doctype == ref_dt)
		count_query = count_query.where(Communication.reference_name == ref_name)

	total_result = count_query.run()
	total = total_result[0][0] if total_result else 0

	# Apply pagination (for chat, we load from end)
	all_messages = query.run(as_dict=True)

	# Build message objects
	messages: list[Message] = []

	for idx, comm in enumerate(all_messages):
		# Determine sender ID based on medium (ensure it's always a string)
		if comm.get("sent_or_received") == "Sent":
			sender_id: str = current_user_id or ""
		else:
			# Use phone_no for SMS/Phone, sender email for Email
			if medium in ("SMS", "Phone"):
				sender_id = str(comm.get("phone_no") or identifier or "")
			else:
				sender_id = str(comm.get("sender") or identifier or "")

		# Get attachments
		files: list[MessageFile] = []
		if comm.get("has_attachment"):
			attachments = (
				frappe.qb.from_(File)
				.select(
					File.name,
					File.file_name,
					File.file_url,
					File.file_size,
					File.file_type,
				)
				.where(File.attached_to_doctype == "Communication")
				.where(File.attached_to_name == comm["name"])
				.run(as_dict=True)
			)

			for att in attachments:
				file_ext = (att.get("file_name") or "").split(".")[-1].lower()
				file_type = att.get("file_type") or "application/octet-stream"

				files.append(
					{
						"name": att.get("file_name", "attachment"),
						"type": file_type,
						"extension": file_ext,
						"url": f"{get_url()}{att.get('file_url', '')}",
						"size": att.get("file_size", 0),
					}
				)

		# Format date and timestamp
		comm_date = comm.get("communication_date")
		date_str = comm_date.strftime("%d %b %Y") if comm_date else ""
		time_str = comm_date.strftime("%H:%M") if comm_date else ""

		# Build message content
		content = comm.get("text_content") or comm.get("content") or ""
		# Strip HTML for cleaner display
		if "<" in content and ">" in content:
			from frappe.utils import strip_html_tags

			content = strip_html_tags(content)

		# Handle reply
		reply_message = None
		if comm.get("in_reply_to"):
			reply_comm = (
				frappe.qb.from_(Communication)
				.select(
					Communication.name,
					Communication.content,
					Communication.text_content,
					Communication.sender,
					Communication.sent_or_received,
				)
				.where(Communication.message_id == comm["in_reply_to"])
				.limit(1)
				.run(as_dict=True)
			)

			if reply_comm:
				reply_content = reply_comm[0].get("text_content") or reply_comm[0].get("content") or ""
				if "<" in reply_content and ">" in reply_content:
					from frappe.utils import strip_html_tags

					reply_content = strip_html_tags(reply_content)

				reply_message = {
					"_id": reply_comm[0]["name"],
					"content": reply_content[:200],
					"senderId": current_user_id
					if reply_comm[0].get("sent_or_received") == "Sent"
					else identifier,
				}

		# Extract values with proper types
		comm_name = str(comm.get("name", ""))
		username = str(comm.get("sender_full_name") or sender_id)
		comm_medium_raw = str(comm.get("communication_medium", "Email"))
		sent_or_recv_raw = str(comm.get("sent_or_received", "Received"))

		# Cast to literal types for TypedDict compatibility
		comm_medium = cast(Literal["Email", "SMS", "Phone", "Chat", "Other"], comm_medium_raw)
		sent_or_recv = cast(Literal["Sent", "Received"], sent_or_recv_raw)

		message: Message = {
			"_id": comm_name,
			"senderId": sender_id,
			"indexId": idx,
			"content": content,
			"username": username,
			"avatar": _get_user_avatar(sender_id if "@" in sender_id else None),
			"date": date_str,
			"timestamp": time_str,
			"system": False,
			"saved": True,
			"distributed": comm.get("delivery_status") in ("Sent", "Opened", "Read"),
			"seen": bool(comm.get("seen")),
			"deleted": False,
			"edited": False,
			"failure": comm.get("delivery_status") in ("Bounced", "Error", "Rejected"),
			"disableActions": sent_or_recv == "Received",
			"disableReactions": True,
			"files": files if files else [],
			"communicationName": comm_name,
			"communicationMedium": comm_medium,
			"sentOrReceived": sent_or_recv,
			"subject": comm.get("subject"),
			"referenceDoctype": comm.get("reference_doctype"),
			"referenceName": comm.get("reference_name"),
		}

		if reply_message:
			message["replyMessage"] = cast(ReplyMessage, reply_message)

		messages.append(message)

	# Paginate (take last N messages for chat)
	start_idx = max(0, len(messages) - (page * limit))
	end_idx = len(messages) - ((page - 1) * limit)
	paginated_messages = messages[start_idx:end_idx]

	return {
		"messages": paginated_messages,
		"total": total,
		"page": page,
		"hasMore": start_idx > 0,
	}


@frappe.whitelist()
def send_message(
	room_id: str,
	content: str,
	files: list[dict] | None = None,
	reply_message_id: str = "",
	subject: str = "",
) -> SendMessageResponse:
	"""
	Send a new message in a conversation.

	Creates a Communication document and sends via the appropriate medium.

	Args:
	    room_id: The room identifier
	    content: Message content
	    files: List of file attachments
	    reply_message_id: ID of message being replied to
	    subject: Email subject (optional, auto-generated if empty)

	Returns:
	    SendMessageResponse with the created message or error
	"""
	current_user_id = frappe.session.user
	files = files or []

	# Parse room ID
	room_parts = _parse_room_id(room_id)
	medium = room_parts.get("medium")
	identifier = room_parts.get("identifier")
	ref_dt = room_parts.get("reference_doctype")
	ref_name = room_parts.get("reference_name")

	if not medium or not identifier:
		return {
			"success": False,
			"message": None,
			"error": _("Invalid room ID"),
		}

	try:
		# Get in_reply_to message_id if replying
		in_reply_to = None
		if reply_message_id:
			Communication = DocType("Communication")
			reply_comm = (
				frappe.qb.from_(Communication)
				.select(Communication.message_id)
				.where(Communication.name == reply_message_id)
				.limit(1)
				.run(as_dict=True)
			)
			if reply_comm:
				in_reply_to = reply_comm[0].get("message_id")

		# Auto-generate subject if not provided
		if not subject:
			if ref_dt and ref_name:
				subject = f"Re: {ref_dt} {ref_name}"
			else:
				subject = f"Message to {identifier}"

		# Create communication based on medium
		if medium == "SMS":
			# Use SMS sending
			comm_doc = frappe.get_doc(
				{
					"doctype": "Communication",
					"communication_type": "Communication",
					"communication_medium": "SMS",
					"subject": subject,
					"content": content,
					"text_content": content,
					"phone_no": identifier,
					"sender": current_user_id,
					"recipients": identifier,
					"sent_or_received": "Sent",
					"reference_doctype": ref_dt,
					"reference_name": ref_name,
					"in_reply_to": in_reply_to,
				}
			)
			comm_doc.insert(ignore_permissions=True)

			# Send SMS via Twilio (if configured)
			try:
				from frappe.core.doctype.sms_settings.sms_settings import send_sms

				send_sms([identifier], content)
				comm_doc.db_set("delivery_status", "Sent")
			except Exception as e:
				frappe.log_error(f"SMS send failed: {e}")
				comm_doc.db_set("delivery_status", "Error")

		else:
			# Use email sending
			from frappe.core.doctype.communication.email import make

			result = make(
				doctype=ref_dt,
				name=ref_name,
				content=content,
				subject=subject,
				recipients=identifier,
				send_email=True,
				sender=current_user_id,
				communication_medium="Email",
				sent_or_received="Sent",
			)

			comm_doc = frappe.get_doc("Communication", result["name"])

		# Handle file attachments
		if files:
			for file_data in files:
				if file_data.get("name"):
					frappe.get_doc(
						{
							"doctype": "File",
							"file_name": file_data["name"],
							"attached_to_doctype": "Communication",
							"attached_to_name": comm_doc.name,
							"file_url": file_data.get("url"),
							"is_private": 1,
						}
					).insert(ignore_permissions=True)

		# Build response message
		comm_name = str(comm_doc.name)
		user_fullname = str(frappe.get_value("User", current_user_id, "full_name") or current_user_id or "")
		current_user_str = str(current_user_id or "")
		medium_literal = cast(Literal["Email", "SMS", "Phone", "Chat", "Other"], medium or "Email")

		message: Message = {
			"_id": comm_name,
			"senderId": current_user_str,
			"content": content,
			"username": user_fullname,
			"avatar": _get_user_avatar(current_user_id),
			"date": now_datetime().strftime("%d %b %Y"),
			"timestamp": now_datetime().strftime("%H:%M"),
			"system": False,
			"saved": True,
			"distributed": False,
			"seen": False,
			"deleted": False,
			"edited": False,
			"failure": False,
			"disableActions": False,
			"disableReactions": True,
			"files": [],
			"communicationName": comm_name,
			"communicationMedium": medium_literal,
			"sentOrReceived": "Sent",
			"subject": subject,
			"referenceDoctype": ref_dt,
			"referenceName": ref_name,
		}

		return {
			"success": True,
			"message": message,
			"error": None,
		}

	except Exception as e:
		frappe.log_error(f"Send message failed: {e}")
		return {
			"success": False,
			"message": None,
			"error": str(e),
		}


@frappe.whitelist()
def mark_messages_seen(room_id: str) -> MarkSeenResponse:
	"""
	Mark all messages in a room as seen.

	Args:
	    room_id: The room identifier

	Returns:
	    MarkSeenResponse with success status and count of updated messages
	"""
	# Parse room ID
	room_parts = _parse_room_id(room_id)
	medium = room_parts.get("medium")
	identifier = room_parts.get("identifier")
	ref_dt = room_parts.get("reference_doctype")
	ref_name = room_parts.get("reference_name")

	if not medium or not identifier:
		return {"success": False, "count": 0}

	Communication = DocType("Communication")

	# Build query for unseen messages in this thread
	query = (
		frappe.qb.from_(Communication)
		.select(Communication.name)
		.where(Communication.communication_type == "Communication")
		.where(Communication.communication_medium == medium)
		.where(Communication.sent_or_received == "Received")
		.where(Communication.seen == 0)
	)

	if medium in ("SMS", "Phone"):
		query = query.where(Communication.phone_no == identifier)
	else:
		query = query.where(Communication.sender == identifier)

	if ref_dt and ref_name:
		query = query.where(Communication.reference_doctype == ref_dt)
		query = query.where(Communication.reference_name == ref_name)

	unseen = query.run(as_dict=True)

	count = 0
	for comm in unseen:
		frappe.db.set_value("Communication", comm["name"], "seen", 1)
		count += 1

	if count > 0:
		frappe.db.commit()

	return {"success": True, "count": count}


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
	return get_rooms(page=1, limit=limit, search=query)["rooms"]


@frappe.whitelist()
def get_unread_count() -> int:
	"""
	Get total count of unread messages across all rooms.

	Returns:
	    Total unread message count
	"""
	Communication = DocType("Communication")

	result = (
		frappe.qb.from_(Communication)
		.select(Count(Communication.name))
		.where(Communication.communication_type == "Communication")
		.where(Communication.sent_or_received == "Received")
		.where(Communication.seen == 0)
		.run()
	)

	return result[0][0] if result else 0


def notify_new_communication(doc: Any, method: str | None = None) -> None:
	"""
	Hook function to notify connected clients of new communications.

	Called after a Communication is inserted to trigger realtime updates
	in the chat interface.

	Args:
	    doc: The Communication document
	    method: The hook method name (unused)
	"""
	# Only notify for actual communications (not system messages)
	if doc.communication_type != "Communication":
		return

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
