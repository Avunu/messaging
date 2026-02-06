# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
Data retrieval functions for the Chat API.

Functions for fetching rooms, messages, and user information.
"""

from datetime import datetime
from typing import Any, Literal, cast

import frappe
from frappe import _
from frappe.query_builder import DocType, Order
from frappe.query_builder.functions import Count
from frappe.utils import cint, get_url

from messaging.messaging.api.chat.formatting import strip_quoted_replies
from messaging.messaging.api.chat.helpers import (
	build_room_from_thread,
	get_user_avatar,
	get_user_status,
	parse_room_id,
)
from messaging.messaging.api.chat.types import (
	CurrentUser,
	Message,
	MessageFile,
	MessagesResponse,
	ReplyMessage,
	Room,
	RoomsResponse,
)


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
		.select(User.name, User.full_name, User.user_image, User.email, User.last_active)
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
		"avatar": get_user_avatar(user_data["name"]),
		"email": user_data.get("email", ""),
		"fullName": user_data.get("full_name") or user_data["name"],
		"status": get_user_status(user_data["name"]),
	}


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
	page = cint(page) or 1
	limit = cint(limit) or 20
	offset = (page - 1) * limit
	current_user_id = frappe.session.user

	Communication = DocType("Communication")

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
			Communication.user,
		)
		.where(Communication.communication_type == "Communication")
		.orderby(Communication.communication_date, order=Order.desc)
	)

	if medium and medium != "All":
		base_query = base_query.where(Communication.communication_medium == medium)

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

	all_comms = base_query.run(as_dict=True)

	# Group into rooms by external party identifier
	room_map: dict[str, dict[str, Any]] = {}

	for comm in all_comms:
		medium_type = comm.get("communication_medium", "Email")

		if medium_type in ("SMS", "Phone"):
			identifier = comm.get("phone_no") or ""
			external_name = None
		else:
			if comm.get("sent_or_received") == "Received":
				identifier = comm.get("sender") or ""
				external_name = comm.get("sender_full_name")
			else:
				recipients = comm.get("recipients") or ""
				identifier = recipients.split(",")[0].strip() if recipients else ""
				external_name = None

		room_id = f"{medium_type}:{identifier}"

		if room_id not in room_map:
			room_map[room_id] = {
				**comm,
				"unread_count": 0,
				"_external_identifier": identifier,
				"_external_name": external_name,
				"_has_unreplied": False,
				"_last_received_status": None,
			}

		# Track unreplied status - a room is "open" if the last received message
		# is not Replied or Closed
		if comm.get("sent_or_received") == "Received":
			status = comm.get("status") or ""
			if not room_map[room_id].get("_last_received_status"):
				room_map[room_id]["_last_received_status"] = status
				if status not in ("Replied", "Closed"):
					room_map[room_id]["_has_unreplied"] = True

		if external_name and not room_map[room_id].get("_external_name"):
			room_map[room_id]["_external_name"] = external_name

		if comm.get("sent_or_received") == "Received" and not comm.get("seen"):
			room_map[room_id]["unread_count"] = room_map[room_id].get("unread_count", 0) + 1

	user_id_str = str(current_user_id or "")
	all_rooms = [build_room_from_thread(thread, user_id_str) for thread in room_map.values()]

	# Sort rooms: unreplied first, then by date (most recent first)
	def get_sort_key(r: Room) -> tuple[int, float]:
		room_data = room_map.get(r.get("roomId", ""), {})
		has_unreplied = 0 if room_data.get("_has_unreplied", False) else 1

		index_val = r.get("index")
		if isinstance(index_val, datetime):
			ts = index_val.timestamp()
		else:
			ts = 0.0

		return (has_unreplied, -ts)

	all_rooms.sort(key=get_sort_key)

	total = len(all_rooms)
	paginated_rooms = all_rooms[offset : offset + limit]

	return {
		"rooms": paginated_rooms,
		"total": total,
		"page": page,
		"hasMore": offset + limit < total,
	}


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
	page = cint(page) or 1
	limit = cint(limit) or 50
	current_user_id: str = str(frappe.session.user or "")

	room_parts = parse_room_id(room_id)
	medium = room_parts.get("medium")
	identifier = room_parts.get("identifier")

	if not medium or not identifier:
		return {"messages": [], "total": 0, "page": page, "hasMore": False}

	Communication = DocType("Communication")
	File = DocType("File")

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
			Communication.user,
		)
		.where(Communication.communication_type == "Communication")
		.where(Communication.communication_medium == medium)
	)

	if medium in ("SMS", "Phone"):
		query = query.where(Communication.phone_no == identifier)
	else:
		query = query.where(
			(Communication.sender == identifier) | (Communication.recipients.like(f"%{identifier}%"))
		)

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

	total_result = count_query.run()
	total = total_result[0][0] if total_result else 0

	all_messages = query.run(as_dict=True)

	# Build message objects
	messages: list[Message] = []
	user_name_cache: dict[str, str] = {}

	def get_user_display_name(user_email: str) -> str:
		if not user_email:
			return ""
		if user_email in user_name_cache:
			return user_name_cache[user_email]
		full_name = frappe.db.get_value("User", user_email, "full_name")
		display_name = str(full_name) if full_name else user_email
		user_name_cache[user_email] = display_name
		return display_name

	for idx, comm in enumerate(all_messages):
		if comm.get("sent_or_received") == "Sent":
			sender_id: str = str(comm.get("user") or comm.get("sender") or current_user_id or "")
		else:
			if medium in ("SMS", "Phone"):
				sender_id = str(comm.get("phone_no") or identifier or "")
			else:
				sender_id = str(comm.get("sender") or identifier or "")

		# Get attachments
		files: list[MessageFile] = []
		if comm.get("has_attachment"):
			attachments = (
				frappe.qb.from_(File)
				.select(File.name, File.file_name, File.file_url, File.file_size, File.file_type)
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

		comm_date = comm.get("communication_date")
		date_str = comm_date.strftime("%d %b %Y") if comm_date else ""
		time_str = comm_date.strftime("%-I:%M %p") if comm_date else ""

		# Build message content
		raw_content = comm.get("text_content") or comm.get("content") or ""
		if "<" in raw_content and ">" in raw_content:
			from frappe.utils import strip_html_tags

			raw_content = strip_html_tags(raw_content)

		raw_content = strip_quoted_replies(raw_content)

		# For emails, prepend subject as a header
		subject = comm.get("subject", "")
		if medium == "Email" and subject:
			content = f"**{subject}**\n\n{raw_content}"
		else:
			content = raw_content

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

				reply_sender = str(reply_comm[0].get("sender") or "")
				if not reply_sender:
					if reply_comm[0].get("sent_or_received") == "Received":
						reply_sender = identifier or ""
					else:
						reply_sender = current_user_id

				reply_message = {
					"_id": reply_comm[0]["name"],
					"content": reply_content[:200],
					"senderId": reply_sender,
				}

		comm_name = str(comm.get("name", ""))

		if comm.get("sent_or_received") == "Sent":
			username = get_user_display_name(sender_id)
		else:
			username = str(comm.get("sender_full_name") or sender_id)

		comm_medium = cast(
			Literal["Email", "SMS", "Phone", "Chat", "Other"], str(comm.get("communication_medium", "Email"))
		)
		sent_or_recv = cast(Literal["Sent", "Received"], str(comm.get("sent_or_received", "Received")))

		message: Message = {
			"_id": comm_name,
			"senderId": sender_id,
			"indexId": idx,
			"content": content,
			"username": username,
			"avatar": get_user_avatar(sender_id if "@" in sender_id else None),
			"date": date_str,
			"timestamp": time_str,
			"system": False,
			"saved": True,
			"distributed": comm.get("delivery_status") in ("Sent", "Opened", "Read"),
			"seen": bool(comm.get("seen")),
			"deleted": False,
			"edited": False,
			"failure": comm.get("delivery_status") in ("Bounced", "Error", "Rejected"),
			"disableActions": False,
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

	# Paginate
	start_idx = max(0, len(messages) - (page * limit))
	end_idx = len(messages) - ((page - 1) * limit)
	paginated_messages = messages[start_idx:end_idx]

	return {
		"messages": paginated_messages,
		"total": total,
		"page": page,
		"hasMore": start_idx > 0,
	}


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
