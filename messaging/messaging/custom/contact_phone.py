# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

from frappe.contacts.doctype.contact_phone.contact_phone import ContactPhone as BaseContactPhone
from frappe.types import DF


class ContactPhone(BaseContactPhone):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	# Temporary, removed in PR B: the generated block re-imports TYPE_CHECKING inside the class.
	from typing import TYPE_CHECKING  # ty: ignore[override-of-final-variable]

	if TYPE_CHECKING:
		# Custom fields
		is_valid: DF.Check
		validated_number: DF.Data
		carrier_type: DF.Data

	# end: auto-generated types
