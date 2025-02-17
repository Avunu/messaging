from frappe.contacts.doctype.contact_phone.contact_phone import ContactPhone as BaseContactPhone
from frappe.types import DF

class ContactPhone(BaseContactPhone):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        # Custom fields
        is_valid: DF.Check
        validated_number: DF.Data
        carrier_type: DF.Data

    # end: auto-generated types
