__version__ = "0.0.1"

from typing import cast

import frappe
from frappe.core.doctype.dynamic_link.dynamic_link import deduplicate_dynamic_links
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count

from messaging.overrides.contact import Contact


def clean_phone_numbers() -> None:
	# Fetch all Contact Phone entries
	contact_phones = frappe.get_all("Contact Phone", fields=["name", "phone"])

	for entry in contact_phones:
		# Clean the phone number
		phone_cleaned = clean_number(entry.get("phone"))

		# Update the Contact Phone entry if the number has changed
		if phone_cleaned != entry.get("phone"):
			frappe.db.set_value("Contact Phone", entry.get("name"), "phone", phone_cleaned)

	frappe.db.commit()


def clean_number(number: str | None) -> str | None:
	if not number:
		return None
	# Remove spaces, dashes, and parentheses
	number = "".join(filter(lambda x: x.isdigit(), number))
	# remove any 1 at the beginning
	if number[0] == "1":
		number = number[1:]
	return number


def prefix_usa_country_code(number: str) -> str:
	if number[0] != "+":
		number = f"+1{number}"
	return number


def clean_email_addresses() -> None:
	# Fetch all Contact Email entries
	contact_emails = frappe.get_all("Contact Email", fields=["name", "email_id"])

	for entry in contact_emails:
		# Clean the email address
		email_cleaned = entry.get("email_id").strip()
		# make it lowercase
		email_cleaned = email_cleaned.lower()

		# Update the Contact Email entry if the email has changed
		if email_cleaned != entry.get("email_id"):
			frappe.db.set_value("Contact Email", entry.get("name"), "email_id", email_cleaned)

	frappe.db.commit()


# consolidate duplicate contacts
def consolidate_duplicate_contacts() -> None:
	ContactPhones = DocType("Contact Phone")
	duplicate_phone_numbers = (
		frappe.qb.from_(ContactPhones)
		.select(ContactPhones.phone)
		.groupby(ContactPhones.phone)
		.having(Count(ContactPhones.phone) > 1)
		.run(as_list=True)
	)

	for phone_number_tuple in duplicate_phone_numbers:
		phone_number = phone_number_tuple[0]
		print(f"Consolidating contacts for phone number: {phone_number}")
		contacts = frappe.get_all(
			"Contact Phone",
			filters={"phone": phone_number},
			pluck="parent",
			group_by="parent",
			order_by="modified desc",
		)

		if contacts and len(contacts) > 1:
			first_contact = contacts[0].parent
			consolidate_contact_data(first_contact, contacts[1:])

	frappe.db.commit()

	ContactEmail = DocType("Contact Email")
	duplicate_emails = (
		frappe.qb.from_(ContactEmail)
		.select(ContactEmail.email_id)
		.groupby(ContactEmail.email_id)
		.having(Count(ContactEmail.email_id) > 1)
		.run(as_list=True)
	)

	for email_tuple in duplicate_emails:
		email = email_tuple[0]
		print(f"Consolidating contacts for email: {email}")
		contacts = frappe.get_all(
			"Contact Email",
			filters={"email_id": email},
			pluck="parent",
			group_by="parent",
			order_by="modified desc",
		)

		if contacts and len(contacts) > 1:
			first_contact = contacts[0].parent
			consolidate_contact_data(first_contact, contacts[1:])

	frappe.db.commit()


def consolidate_contact_data(primary_contact_name: str, other_contact_entries: list[str]) -> None:
	primary_contact = cast(Contact, frappe.get_doc("Contact", primary_contact_name))
	fields_to_update = [
		"phone_nos",
		"email_ids",
		"first_name",
		"middle_name",
		"last_name",
		"designation",
	]

	for contact_entry in other_contact_entries:
		other_contact = cast(Contact, frappe.get_doc("Contact", contact_entry))
		for field in fields_to_update:
			# Update primary_contact fields if they are empty and other_contact has data
			if not getattr(primary_contact, field) and getattr(other_contact, field):
				setattr(primary_contact, field, getattr(other_contact, field))

	primary_contact.save(ignore_permissions=True)

	# Now, merge the contacts
	for contact_entry in other_contact_entries:
		frappe.rename_doc("Contact", contact_entry, primary_contact_name, merge=True)


def deduplicate_contact_links() -> None:
	contacts = frappe.get_all("Contact", fields=["name"])
	for contact in contacts:
		contact_doc = frappe.get_doc("Contact", contact.get("name"))
		deduplicate_dynamic_links(contact_doc)
		contact_doc.save(ignore_permissions=True)

	frappe.db.commit()


def refresh_primary_contact_fields() -> None:
	contacts = frappe.get_all("Contact", fields=["name"])
	for contact in contacts:
		contact_doc = cast(Contact, frappe.get_doc("Contact", contact.get("name")))
		contact_doc.set_primary_email()
		contact_doc.set_primary("phone")
		contact_doc.set_primary("mobile_no")
		contact_doc.save(ignore_permissions=True)

	frappe.db.commit()
