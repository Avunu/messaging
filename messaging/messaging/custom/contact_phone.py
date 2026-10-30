# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

from frappe.contacts.doctype.contact_phone.contact_phone import ContactPhone as BaseContactPhone
from frappe.types import DF


class ContactPhone(BaseContactPhone):
	"""Contact Phone with the custom fields custom/contact_phone.json adds.

	TYPE_CHECKING comes from the module: frappe's generated base class already binds it, and
	a class-level import would override that final name.
	"""

	if TYPE_CHECKING:
		# Custom fields
		is_valid: DF.Check
		validated_number: DF.Data
		carrier_type: DF.Data
