# Copyright (c) 2025, Avunu LLC and contributors
# For license information, please see license.txt

"""
Twilio-native SMS sending with per-recipient error handling.

Registered as the ``send_sms`` hook so every outbound SMS (group broadcasts,
chat replies, etc.) goes through Twilio directly and errors are handled
gracefully instead of raising blanket 400 exceptions.
"""

from __future__ import annotations

import json
from typing import TypedDict, cast

import frappe
from frappe import _
from frappe.core.doctype.sms_log.sms_log import SMSLog
from frappe.core.doctype.sms_settings.sms_settings import validate_receiver_nos
from frappe.utils import nowdate
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

# ── Twilio error codes ──────────────────────────────────────────────────────
UNSUBSCRIBED_RECIPIENT = 21610
INVALID_TO_NUMBER = 21211
NOT_MOBILE_NUMBER = 21614
UNREACHABLE_HANDSET = 30003
MESSAGE_BLOCKED = 30004
UNKNOWN_HANDSET = 30005
LANDLINE_UNREACHABLE = 30006
CARRIER_VIOLATION = 30007


# ── Result types ─────────────────────────────────────────────────────────────
class SendResult(TypedDict, total=False):
	status: str  # "success" | "error"
	number: str
	sid: str | None
	code: int | None
	message: str


class SendSmsResult(TypedDict):
	success: list[str]
	errors: list[SendResult]


# ── Helpers ──────────────────────────────────────────────────────────────────
def get_twilio_client() -> tuple[Client, str]:
	"""Return a configured ``(Client, from_number)`` pair."""
	from messaging.messaging.doctype.messaging_settings.messaging_settings import (
		MessagingSettings,
	)

	settings = cast(MessagingSettings, frappe.get_doc("Messaging Settings"))

	if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_phone_no:
		frappe.throw(_("Twilio credentials not configured in Messaging Settings"))

	client = Client(
		settings.twilio_account_sid,
		str(settings.get_password("twilio_auth_token")),
	)
	return client, str(settings.twilio_phone_no)


def get_contact_from_phone(phone_number: str) -> str | None:
	"""Look up the Contact name that owns *phone_number*."""
	return frappe.db.get_value("Contact Phone", {"phone": phone_number}, "parent")  # type: ignore[return-value]


# ── Per-recipient sending ────────────────────────────────────────────────────
def send_single_sms(client: Client, from_number: str, to_number: str, message: str) -> SendResult:
	"""Send one SMS via Twilio and return a result dict."""
	try:
		msg = client.messages.create(body=message, from_=from_number, to=to_number)
		return SendResult(status="success", number=to_number, sid=msg.sid)
	except TwilioRestException as exc:
		handle_twilio_error(exc, to_number)
		return SendResult(status="error", number=to_number, code=exc.code, message=str(exc))
	except Exception as exc:
		frappe.log_error(title=f"SMS send error: {to_number}", message=str(exc))
		return SendResult(status="error", number=to_number, code=None, message=str(exc))


def handle_twilio_error(error: TwilioRestException, phone_number: str) -> None:
	"""Inspect a Twilio error code and take corrective action on the Contact."""

	if error.code == UNSUBSCRIBED_RECIPIENT:
		contact_name = get_contact_from_phone(phone_number)
		if contact_name:
			frappe.db.set_value("Contact", contact_name, "consent_sms", 0)
			frappe.log_error(
				title=f"SMS unsubscribe: {phone_number}",
				message=(
					f"Contact {contact_name} auto-unsubscribed (Twilio {UNSUBSCRIBED_RECIPIENT}). "
					f"Set consent_sms=0."
				),
			)
		else:
			frappe.log_error(
				title=f"SMS unsubscribe: {phone_number}",
				message=f"Twilio {UNSUBSCRIBED_RECIPIENT} for {phone_number} but no matching Contact found.",
			)

	elif error.code == INVALID_TO_NUMBER:
		contact_phone = frappe.db.exists("Contact Phone", {"phone": phone_number})
		if contact_phone and isinstance(contact_phone, str):
			frappe.db.set_value("Contact Phone", contact_phone, "is_valid", 0)
		frappe.log_error(
			title=f"Invalid number: {phone_number}",
			message=f"Twilio {INVALID_TO_NUMBER}: {phone_number} marked invalid.",
		)

	elif error.code in (
		NOT_MOBILE_NUMBER,
		UNREACHABLE_HANDSET,
		MESSAGE_BLOCKED,
		UNKNOWN_HANDSET,
		LANDLINE_UNREACHABLE,
		CARRIER_VIOLATION,
	):
		frappe.log_error(
			title=f"Twilio error {error.code}: {phone_number}",
			message=str(error),
		)

	else:
		frappe.log_error(
			title=f"Twilio error {error.code}: {phone_number}",
			message=str(error),
		)


# ── SMS Log ──────────────────────────────────────────────────────────────────
def create_sms_log(message: str, receiver_list: list[str], sent_to: list[str]) -> None:
	"""Create an SMS Log record (mirrors frappe core behaviour)."""
	sl = cast(SMSLog, frappe.new_doc("SMS Log"))
	sl.sent_on = nowdate()
	sl.message = message if isinstance(message, str) else message.decode("utf-8")
	sl.no_of_requested_sms = len(receiver_list)
	sl.requested_numbers = "\n".join(receiver_list)
	sl.no_of_sent_sms = len(sent_to)
	sl.sent_to = "\n".join(sent_to)
	sl.flags.ignore_permissions = True
	sl.save()


# ── Fallback: core SMS Settings gateway ──────────────────────────────────────
def _send_via_core_gateway(
	receiver_list: list[str],
	msg: str,
	success_msg: bool = True,
) -> SendSmsResult:
	"""
	Forward to the frappe core ``send_via_gateway`` when Twilio is not enabled.

	We call ``send_via_gateway`` directly (not core ``send_sms``) to avoid
	infinite recursion through the ``send_sms`` hook.
	"""
	from frappe.core.doctype.sms_settings.sms_settings import send_via_gateway

	arg = {
		"receiver_list": receiver_list,
		"message": frappe.safe_decode(msg).encode("utf-8"),
		"success_msg": success_msg,
	}

	if not frappe.db.get_single_value("SMS Settings", "sms_gateway_url"):
		frappe.msgprint(_("Please Update SMS Settings"))
		return SendSmsResult(success=[], errors=[])

	# send_via_gateway handles its own SMS Log creation and success message
	send_via_gateway(arg)

	# Core gateway doesn't return per-recipient results, so we optimistically
	# report all as successful (errors would have raised an exception).
	return SendSmsResult(success=receiver_list, errors=[])


# ── Public API / hook entry-point ────────────────────────────────────────────
def send_sms(
	receiver_list: list[str] | str,
	msg: str,
	sender_name: str = "",
	success_msg: bool = True,
) -> SendSmsResult:
	"""
	Drop-in replacement for ``frappe.core.doctype.sms_settings.sms_settings.send_sms``.

	Registered as a ``send_sms`` hook in *hooks.py* so **all** outbound SMS
	traffic is routed through this function.

	When *Messaging Settings → Send via Twilio* is enabled, messages are sent
	through the Twilio SDK with per-recipient error handling.  Otherwise the
	core SMS Settings gateway (``send_via_gateway``) is used as a fallback.
	"""
	if isinstance(receiver_list, str):
		receiver_list = json.loads(receiver_list)
		if not isinstance(receiver_list, list):
			receiver_list = [receiver_list]

	receiver_list = validate_receiver_nos(receiver_list)

	# Check whether Twilio sending is enabled
	send_via_twilio = frappe.db.get_single_value("Messaging Settings", "send_via_twilio")
	if not send_via_twilio:
		return _send_via_core_gateway(receiver_list, msg, success_msg)

	client, from_number = get_twilio_client()

	success_list: list[str] = []
	error_list: list[SendResult] = []

	for number in receiver_list:
		result = send_single_sms(client, from_number, number, msg)
		if result.get("status") == "success":
			success_list.append(number)
		else:
			error_list.append(result)

	if success_list:
		create_sms_log(msg, receiver_list, success_list)

	if success_msg and success_list:
		frappe.msgprint(_("SMS sent to {0} of {1} recipients").format(len(success_list), len(receiver_list)))

	return SendSmsResult(success=success_list, errors=error_list)
