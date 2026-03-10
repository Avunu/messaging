import json
from typing import cast
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import now
from twilio.request_validator import RequestValidator

from messaging.messaging.doctype.messaging_settings.messaging_settings import (
	MessagingSettings,
)


@frappe.whitelist(allow_guest=True)
def sms():
	"""Handle incoming SMS webhook from Twilio"""
	if frappe.request.method != "POST":
		frappe.throw(_("Only POST requests allowed"), frappe.ValidationError)

	# Get Twilio settings
	settings = cast(MessagingSettings, frappe.get_doc("Messaging Settings"))
	if not settings.twilio_auth_token:
		frappe.throw(_("Twilio auth token not configured"), frappe.ValidationError)

	# Get original HTTPS scheme from Cloudflare headers
	cf_visitor = frappe.request.headers.get("Cf-Visitor", "{}")
	cf_scheme = json.loads(cf_visitor).get("scheme", False)

	# Normalize URL - use original HTTPS scheme
	url_parts = urlparse(frappe.request.url)
	url = f"{cf_scheme or url_parts.scheme}://{url_parts.netloc}{url_parts.path}"

	# Validate request is from Twilio
	validator = RequestValidator(settings.get_password("twilio_auth_token"))
	request_valid = validator.validate(
		url,
		frappe.request.form,
		frappe.request.headers.get("X-Twilio-Signature", ""),
	)

	if not request_valid:
		frappe.throw(_("Invalid request signature"), frappe.ValidationError)

	sender_full_name = ""
	sender_user = ""
	sender_contact = ""
	sender_number = frappe.request.form.get("From")
	body = (frappe.request.form.get("Body") or "").strip()
	sender_is_contact = frappe.db.exists("Contact Phone", {"phone": sender_number})
	if sender_is_contact:
		sender_contact = str(frappe.db.get_value("Contact Phone", sender_is_contact, "parent") or "")
		sender_full_name = frappe.db.get_value("Contact", sender_contact, "full_name")
		sender_user = frappe.db.get_value("Contact", sender_contact, "user")

	# Handle SMS subscription keywords (Twilio opt-out/opt-in)
	if sender_contact and body:
		_handle_subscription_keywords(body, sender_contact)

	# Create communication
	communication = frappe.get_doc(
		{
			"communication_date": now(),
			"communication_medium": "SMS",
			"communication_type": "Communication",
			"content": body,
			"doctype": "Communication",
			"message_id": frappe.request.form.get("MessageSid"),
			"phone_no": sender_number,
			"recipients": frappe.request.form.get("To"),
			"sender": sender_full_name or sender_number,
			"sender_full_name": sender_full_name,
			"sent_or_received": "Received",
			"status": "Open",
			"subject": f"SMS from {sender_number}",
			"text_content": body,
			"user": sender_user,
		}
	)
	communication.insert(ignore_permissions=True)

	# Return 204 No Content status code
	frappe.response.http_status_code = 204
	return None


# Twilio standard opt-out / opt-in keywords
# https://www.twilio.com/docs/messaging/guides/opt-out-keywords
_OPT_OUT_KEYWORDS = {"stop", "stopall", "unsubscribe", "cancel", "end", "quit"}
_OPT_IN_KEYWORDS = {"start", "yes", "unstop"}


def _handle_subscription_keywords(body: str, contact_name: str) -> None:
	"""Update Contact consent flags based on standard SMS opt-out/opt-in keywords."""
	keyword = body.strip().upper()

	if keyword.lower() in _OPT_OUT_KEYWORDS:
		frappe.db.set_value("Contact", contact_name, "consent_sms", 0)
		frappe.db.set_value("Contact", contact_name, "unsubscribed", 1)
		frappe.get_doc("Contact", contact_name).add_comment(
			"Info", f"SMS opt-out received (keyword: {keyword})"
		)
	elif keyword.lower() in _OPT_IN_KEYWORDS:
		frappe.db.set_value("Contact", contact_name, "consent_sms", 1)
		frappe.db.set_value("Contact", contact_name, "unsubscribed", 0)
		frappe.get_doc("Contact", contact_name).add_comment(
			"Info", f"SMS opt-in received (keyword: {keyword})"
		)
