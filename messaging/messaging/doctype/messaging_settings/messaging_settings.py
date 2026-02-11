# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MessagingSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		all_contacts_group: DF.Link | None
		enable_number_validation: DF.Check
		enable_push_notifications: DF.Check
		twilio_account_sid: DF.Data | None
		twilio_auth_token: DF.Password | None
		twilio_phone_no: DF.Data | None
		vapid_contact_email: DF.Data | None
		vapid_private_key_secret: DF.Password | None
		vapid_public_key: DF.SmallText | None
	# end: auto-generated types

	@frappe.whitelist()
	def generate_vapid_keys(self) -> None:
		"""Generate a new VAPID key pair for push notifications."""
		from messaging.messaging.api.chat.push import _generate_vapid_keys

		_generate_vapid_keys(self)
		frappe.msgprint("VAPID keys generated successfully.", indicator="green")
