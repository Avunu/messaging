import json
from urllib.parse import urlparse

import frappe
from frappe import _
from twilio.request_validator import RequestValidator


@frappe.whitelist(allow_guest=True)
def sms():
	"""Handle incoming SMS webhook from Twilio"""
	if frappe.request.method != "POST":
		frappe.throw(_("Only POST requests allowed"), frappe.ValidationError)

	# Get Twilio settings
	settings = frappe.get_doc("Messaging Settings")
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
	sender_number = frappe.request.form.get("From")
	sender_is_contact = frappe.db.exists("Contact Phone", {"phone": sender_number})
	if sender_is_contact:
		sender_contact = frappe.db.get_value("Contact Phone", sender_is_contact, "parent")
		sender_full_name = frappe.db.get_value("Contact", sender_contact, "full_name")
		sender_user = frappe.db.get_value("Contact", sender_contact, "user")

	# Create communication
	communication = frappe.get_doc(
		{
			"communication_date": frappe.utils.now(),
			"communication_medium": "SMS",
			"communication_type": "Communication",
			"content": frappe.request.form.get("Body"),
			"doctype": "Communication",
			"message_id": frappe.request.form.get("MessageSid"),
			"phone_no": sender_number,
			"recipients": frappe.request.form.get("To"),
			"sender": sender_full_name or sender_number,
			"sender_full_name": sender_full_name,
			"sent_or_received": "Received",
			"status": "Open",
			"subject": f"SMS from {sender_number}",
			"text_content": frappe.request.form.get("Body"),
			"user": sender_user,
		}
	)
	communication.insert(ignore_permissions=True)

	# Return 204 No Content status code
	frappe.response.http_status_code = 204
	return None
