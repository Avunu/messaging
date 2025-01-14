import frappe
from frappe import _
import phonenumbers

def validate(doc, method=None):
	country = ""
	if doc.address:
		country = frappe.get_value("Address", doc.address, "country")
	if not country:
		country = frappe.db.get_single_value("System Settings", "country")
	country_code = frappe.get_value("Country", country, "code").upper()
	# convert all phone numbers to E.164 format
	for phone_entry in doc.phone_nos:
		try:
			no = phonenumbers.parse(phone_entry.phone, country_code)
		except:
			frappe.throw(_("Invalid phone number: {0}").format(phone_entry.phone))
		phone_entry.phone = phonenumbers.format_number(no, phonenumbers.PhoneNumberFormat.E164)