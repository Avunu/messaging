# Copyright (c) 2025, Avunu LLC
# License: MIT. See LICENSE
"""
Message sending functions for the Chat API.

Functions for sending messages and updating message status.
"""

import json
from datetime import datetime
from typing import Any, Literal, cast

import frappe
from frappe import _
from frappe.query_builder import DocType, Order
from frappe.utils import get_datetime, now_datetime

from messaging.messaging.api.chat.formatting import (
	build_quoted_reply,
	html_to_plain_text,
	plain_text_to_html,
)
from messaging.messaging.api.chat.helpers import get_user_avatar, parse_room_id
from messaging.messaging.api.chat.types import (
	MarkSeenResponse,
	Message,
	RoomActionResponse,
	SendMessageResponse,
)


def get_user_email_signature(user: str) -> str:
	"""
	Get the email signature for a user.

	If the user has an email_signature set, return it.
	Otherwise, generate a default signature using their full name.

	Args:
	    user: The user ID (email)

	Returns:
	    Plain text email signature
	"""
	if not user:
		return ""

	User = DocType("User")
	result = (
		frappe.qb.from_(User)
		.select(User.email_signature, User.full_name)
		.where(User.name == user)
		.limit(1)
		.run(as_dict=True)
	)

	if not result:
		return ""

	user_doc = result[0]

	# If user has a custom email signature, use it
	email_signature = user_doc.get("email_signature")
	if email_signature:
		# Strip HTML if present
		if "<" in email_signature and ">" in email_signature:
			email_signature = html_to_plain_text(email_signature)
		return email_signature.strip()

	# Otherwise, generate a default signature with their name
	full_name = user_doc.get("full_name") or user
	return f"--\n{full_name}"


def send_message(
	room_id: str,
	content: str,
	files: str | list | None = None,
	reply_message_id: str = "",
	subject: str = "",
) -> SendMessageResponse:
	"""
	Send a new message in a conversation.

	Creates a Communication document and sends via the appropriate medium.

	Args:
	    room_id: The room identifier
	    content: Message content
	    files: List of file attachments (JSON string or list)
	    reply_message_id: Communication name of message being replied to
	    subject: Email subject (optional, auto-generated if empty)

	Returns:
	    SendMessageResponse with the created message or error
	"""
	current_user_id = frappe.session.user

	# Parse files
	if isinstance(files, str):
		try:
			files = json.loads(files) if files else []
		except json.JSONDecodeError:
			files = []
	files = files or []

	room_parts = parse_room_id(room_id)
	medium = room_parts.get("medium")
	identifier = room_parts.get("identifier")
	ref_dt = room_parts.get("reference_doctype")
	ref_name = room_parts.get("reference_name")

	if not medium or not identifier:
		return {"success": False, "message": None, "error": _("Invalid room ID")}

	try:
		Communication = DocType("Communication")

		# Variables for reply handling
		original_subject: str | None = None
		reply_content_for_quote: str | None = None
		reply_sender_for_quote: str | None = None
		reply_date_for_quote: Any = None
		latest_received_name: str | None = None

		# Get reply context
		if reply_message_id:
			reply_comm = (
				frappe.qb.from_(Communication)
				.select(
					Communication.name,
					Communication.message_id,
					Communication.subject,
					Communication.sent_or_received,
					Communication.content,
					Communication.text_content,
					Communication.sender,
					Communication.sender_full_name,
					Communication.communication_date,
				)
				.where(Communication.name == reply_message_id)
				.limit(1)
				.run(as_dict=True)
			)
			if reply_comm:
				original_subject = reply_comm[0].get("subject")
				reply_content_for_quote = reply_comm[0].get("text_content") or reply_comm[0].get("content")
				reply_sender_for_quote = reply_comm[0].get("sender_full_name") or reply_comm[0].get("sender")
				reply_date_for_quote = reply_comm[0].get("communication_date")
				if reply_comm[0].get("sent_or_received") == "Received":
					latest_received_name = reply_comm[0].get("name")
		else:
			# Find latest message in thread
			latest_in_thread = (
				frappe.qb.from_(Communication)
				.select(
					Communication.name,
					Communication.message_id,
					Communication.subject,
					Communication.sent_or_received,
					Communication.content,
					Communication.text_content,
					Communication.sender,
					Communication.sender_full_name,
					Communication.communication_date,
				)
				.where(Communication.communication_type == "Communication")
				.where(Communication.communication_medium == medium)
			)

			if medium in ("SMS", "Phone"):
				latest_in_thread = latest_in_thread.where(Communication.phone_no == identifier)
			else:
				latest_in_thread = latest_in_thread.where(
					(Communication.sender == identifier) | (Communication.recipients.like(f"%{identifier}%"))
				)

			if ref_dt and ref_name:
				latest_in_thread = latest_in_thread.where(Communication.reference_doctype == ref_dt)
				latest_in_thread = latest_in_thread.where(Communication.reference_name == ref_name)

			latest_in_thread = (
				latest_in_thread.orderby(Communication.communication_date, order=Order.desc)
				.limit(1)
				.run(as_dict=True)
			)

			if latest_in_thread:
				reply_message_id = latest_in_thread[0].get("name")
				original_subject = latest_in_thread[0].get("subject")
				reply_content_for_quote = latest_in_thread[0].get("text_content") or latest_in_thread[0].get(
					"content"
				)
				reply_sender_for_quote = latest_in_thread[0].get("sender_full_name") or latest_in_thread[
					0
				].get("sender")
				reply_date_for_quote = latest_in_thread[0].get("communication_date")
				if latest_in_thread[0].get("sent_or_received") == "Received":
					latest_received_name = latest_in_thread[0].get("name")

		# Auto-generate subject
		if not subject:
			if medium == "Email":
				if original_subject:
					if original_subject.lower().startswith("re:"):
						subject = original_subject
					else:
						subject = f"Re: {original_subject}"
				else:
					subject = f"Message to {identifier}"
			else:
				subject = f"Message to {identifier}"

		# Create and send based on medium
		if medium == "SMS":
			comm_doc = _send_sms(content, identifier, subject, ref_dt, ref_name, reply_message_id)
		else:
			# Get user's email signature
			email_signature = get_user_email_signature(str(current_user_id))

			comm_doc = _send_email(
				content,
				identifier,
				subject,
				ref_dt,
				ref_name,
				reply_message_id,
				reply_content_for_quote,
				reply_sender_for_quote,
				reply_date_for_quote,
				email_signature,
			)

		# Update original message status
		if latest_received_name:
			frappe.db.set_value("Communication", latest_received_name, "status", "Replied")

		# Handle file attachments
		file_list: list[dict] = files if isinstance(files, list) else []
		for file_data in file_list:
			if isinstance(file_data, dict) and file_data.get("name"):
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

		# Build response
		comm_name = str(comm_doc.name)
		user_fullname = str(frappe.get_value("User", current_user_id, "full_name") or current_user_id or "")
		medium_literal = cast(Literal["Email", "SMS", "Phone", "Chat", "Other"], medium or "Email")

		message: Message = {
			"_id": comm_name,
			"senderId": str(current_user_id or ""),
			"content": content,
			"username": user_fullname,
			"avatar": get_user_avatar(current_user_id),
			"date": now_datetime().strftime("%d %b %Y"),
			"timestamp": now_datetime().strftime("%-I:%M %p"),
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

		return {"success": True, "message": message, "error": None}

	except Exception as e:
		frappe.log_error(f"Send message failed: {e}")
		return {"success": False, "message": None, "error": str(e)}


def _send_sms(
	content: str,
	identifier: str,
	subject: str,
	ref_dt: str | None,
	ref_name: str | None,
	reply_message_id: str,
) -> Any:
	"""Send SMS message and return Communication doc."""
	current_user_id = frappe.session.user

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
			"in_reply_to": reply_message_id,
		}
	)
	comm_doc.insert(ignore_permissions=True)

	try:
		from frappe.core.doctype.sms_settings.sms_settings import send_sms

		send_sms([identifier], content)
		comm_doc.db_set("delivery_status", "Sent")
	except Exception as e:
		frappe.log_error(f"SMS send failed: {e}")
		comm_doc.db_set("delivery_status", "Error")

	return comm_doc


def _send_email(
	content: str,
	identifier: str,
	subject: str,
	ref_dt: str | None,
	ref_name: str | None,
	reply_message_id: str,
	reply_content_for_quote: str | None,
	reply_sender_for_quote: str | None,
	reply_date_for_quote: Any,
	email_signature: str = "",
) -> Any:
	"""Send email message and return Communication doc."""
	from frappe.email.doctype.email_account.email_account import EmailAccount
	from frappe.email.email_body import get_message_id

	current_user_id = frappe.session.user

	# Get the default incoming email account for reply-to address
	reply_to_address = None
	default_incoming = EmailAccount.find_default_incoming()
	if default_incoming:
		reply_to_address = default_incoming.email_id

	# Build email content - start with the message
	email_content = content

	# Append email signature if available
	if email_signature:
		email_content = f"{email_content}\n\n{email_signature}"

	# Add quoted reply if this is a reply
	if reply_content_for_quote and reply_sender_for_quote:
		reply_date_str = ""
		if reply_date_for_quote:
			if isinstance(reply_date_for_quote, datetime):
				reply_date_str = reply_date_for_quote.strftime("%B %d, %Y at %I:%M %p")
			else:
				try:
					dt = get_datetime(reply_date_for_quote) or reply_date_for_quote
					reply_date_str = dt.strftime("%B %d, %Y at %I:%M %p")
				except Exception:
					reply_date_str = str(reply_date_for_quote)

		# Build quoted reply and append to content (after signature)
		quoted_reply = build_quoted_reply("", reply_content_for_quote, reply_sender_for_quote, reply_date_str)
		# Remove the empty content prefix from build_quoted_reply
		quoted_reply = quoted_reply.lstrip("\n")
		email_content = f"{email_content}\n\n{quoted_reply}"

	new_message_id = get_message_id().strip("<>")
	html_content = plain_text_to_html(email_content)

	comm_doc = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Email",
			"subject": subject,
			"content": html_content,
			"text_content": email_content,
			"sender": current_user_id,
			"recipients": identifier,
			"sent_or_received": "Sent",
			"reference_doctype": ref_dt,
			"reference_name": ref_name,
			"message_id": new_message_id,
			"in_reply_to": reply_message_id,
			"status": "Linked",
		}
	)
	comm_doc.insert(ignore_permissions=True)
	comm_name = str(comm_doc.name)

	try:
		frappe.sendmail(
			recipients=[identifier],
			sender=str(current_user_id),
			subject=subject,
			message=html_content,
			reference_doctype=ref_dt,
			reference_name=ref_name,
			message_id=new_message_id,
			in_reply_to=reply_message_id,
			communication=comm_name,
			reply_to=reply_to_address,
			delayed=True,
		)
	except Exception as e:
		frappe.log_error(f"Email send failed: {e}")
		frappe.db.set_value("Communication", comm_name, "delivery_status", "Error")

	return comm_doc


def mark_messages_seen(room_id: str) -> MarkSeenResponse:
	"""
	Mark all messages in a room as seen.

	Args:
	    room_id: The room identifier

	Returns:
	    MarkSeenResponse with success status and count of updated messages
	"""
	room_parts = parse_room_id(room_id)
	medium = room_parts.get("medium")
	identifier = room_parts.get("identifier")
	ref_dt = room_parts.get("reference_doctype")
	ref_name = room_parts.get("reference_name")

	if not medium or not identifier:
		return {"success": False, "count": 0}

	Communication = DocType("Communication")

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


def archive_room(room_id: str) -> RoomActionResponse:
	"""
	Archive all messages in a room by setting status to 'Closed'.

	Args:
	    room_id: The room identifier

	Returns:
	    RoomActionResponse with success status and count of updated messages
	"""
	room_parts = parse_room_id(room_id)
	medium = room_parts.get("medium")
	identifier = room_parts.get("identifier")

	if not medium or not identifier:
		return {"success": False, "count": 0, "error": "Invalid room ID"}

	Communication = DocType("Communication")

	# Build query to find all communications in this room
	query = (
		frappe.qb.from_(Communication)
		.select(Communication.name)
		.where(Communication.communication_type == "Communication")
		.where(Communication.communication_medium == medium)
	)

	if medium in ("SMS", "Phone"):
		query = query.where(Communication.phone_no == identifier)
	else:
		query = query.where(
			(Communication.sender == identifier) | (Communication.recipients.like(f"%{identifier}%"))
		)

	comms = query.run(as_dict=True)

	count = 0
	for comm in comms:
		frappe.db.set_value("Communication", comm["name"], "status", "Closed")
		count += 1

	if count > 0:
		frappe.db.commit()

	return {"success": True, "count": count, "error": None}


def delete_room(room_id: str) -> RoomActionResponse:
	"""
	Delete all messages in a room.

	Args:
	    room_id: The room identifier

	Returns:
	    RoomActionResponse with success status and count of deleted messages
	"""
	room_parts = parse_room_id(room_id)
	medium = room_parts.get("medium")
	identifier = room_parts.get("identifier")

	if not medium or not identifier:
		return {"success": False, "count": 0, "error": "Invalid room ID"}

	Communication = DocType("Communication")

	# Build query to find all communications in this room
	query = (
		frappe.qb.from_(Communication)
		.select(Communication.name)
		.where(Communication.communication_type == "Communication")
		.where(Communication.communication_medium == medium)
	)

	if medium in ("SMS", "Phone"):
		query = query.where(Communication.phone_no == identifier)
	else:
		query = query.where(
			(Communication.sender == identifier) | (Communication.recipients.like(f"%{identifier}%"))
		)

	comms = query.run(as_dict=True)

	count = 0
	errors = []
	for comm in comms:
		try:
			frappe.delete_doc("Communication", comm["name"], force=True)
			count += 1
		except Exception as e:
			errors.append(f"{comm['name']}: {e!s}")

	if count > 0:
		frappe.db.commit()

	error_msg = "; ".join(errors) if errors else None
	return {"success": len(errors) == 0, "count": count, "error": error_msg}
