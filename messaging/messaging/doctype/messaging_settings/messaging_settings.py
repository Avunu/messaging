# Copyright (c) 2024, Avunu LLC and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MessagingSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		all_contacts_group: DF.Link | None
		enable_number_validation: DF.Check
		twilio_account_sid: DF.Data | None
		twilio_auth_token: DF.Password | None
		twilio_phone_no: DF.Data | None
	# end: auto-generated types

	pass
