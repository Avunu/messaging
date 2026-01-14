from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import frappe
import phonenumbers
from frappe.contacts.doctype.contact.contact import Contact as BaseContact
from frappe.query_builder import DocType
from frappe.types import DF
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

if TYPE_CHECKING:
	from messaging.messaging.doctype.messaging_group.messaging_group import MessagingGroup
	from messaging.messaging.doctype.messaging_settings.messaging_settings import (
		MessagingSettings,
	)
	from messaging.overrides.contact_phone import ContactPhone


class Contact(BaseContact):
	"""Extended Contact class with messaging group and phone validation functionality."""

	if TYPE_CHECKING:
		consent_sms: DF.Check
		phone_nos: DF.Table[ContactPhone]

	# core frappe hooks

	def on_update(self) -> None:
		"""Add contact to the all contacts messaging group on update."""
		add_to_all_contacts_group(self)

	def validate(self, method: str | None = None) -> None:
		"""Validate and normalize contact data including email and phone deduplication."""
		settings = cast("MessagingSettings", frappe.get_doc("Messaging Settings"))
		country_code: str = self.get_country_code()

		# Process and deduplicate email addresses
		self.deduplicate_emails()

		# Process and deduplicate phone numbers
		self.deduplicate_phone_numbers(country_code)

		# Only proceed with Twilio validation if enabled in settings
		validate_numbers: bool = bool(
			settings.enable_number_validation and settings.twilio_account_sid and settings.twilio_auth_token
		)

		if validate_numbers:
			client = Client(settings.twilio_account_sid, str(settings.get_password("twilio_auth_token")))
			self.validate_phone_numbers(client)
			self.set_primary_numbers()

	def on_trash(self) -> None:
		"""Remove contact from all messaging groups on deletion."""
		MessagingGroupMembers = DocType("Messaging Group Member")
		frappe.qb.from_(MessagingGroupMembers).delete().where(
			MessagingGroupMembers.contact == self.name
		).run()

	# email methods

	def deduplicate_emails(self) -> None:
		"""Remove duplicate email entries, keeping the first occurrence."""
		seen_emails: dict[str, int] = {}
		to_remove: list[int] = []

		for i, email_entry in enumerate(self.email_ids):
			email: str = email_entry.email_id.lower().strip()
			if email in seen_emails:
				to_remove.append(i)
			else:
				seen_emails[email] = i
				email_entry.email_id = email

		for i in reversed(to_remove):
			self.email_ids.pop(i)

	# phone number methods

	def deduplicate_phone_numbers(self, country_code: str) -> None:
		"""Normalize to E.164 format and remove duplicate phone entries."""
		seen_numbers: dict[str, int] = {}
		to_remove: list[int] = []

		for i, phone_entry in enumerate(self.phone_nos):
			if not is_valid_e164_number(phone_entry.phone):
				e164_number: str | None = convert_to_e164(phone_entry.phone, country_code)
				if e164_number:
					phone_entry.phone = e164_number
				else:
					continue  # Skip invalid numbers

			if phone_entry.phone in seen_numbers:
				to_remove.append(i)
			else:
				seen_numbers[phone_entry.phone] = i

		for i in reversed(to_remove):
			self.phone_nos.pop(i)

	def validate_phone_numbers(self, client: Client) -> None:
		"""Validate phone numbers using Twilio Lookup API."""
		for phone_entry in self.phone_nos:
			# Only validate if number changed or not yet validated
			if not phone_entry.validated_number or phone_entry.validated_number != phone_entry.phone:
				phone_entry.is_valid, phone_entry.carrier_type = validate_number(phone_entry.phone, client)
				if phone_entry.is_valid:
					phone_entry.validated_number = phone_entry.phone
					if phone_entry.is_primary_mobile_no and phone_entry.carrier_type != "mobile":
						phone_entry.is_primary_mobile_no = 0
				else:
					phone_entry.validated_number = ""
					phone_entry.carrier_type = ""

	def set_primary_numbers(self) -> None:
		"""Set primary phone and mobile numbers from valid numbers."""
		valid_numbers: list[ContactPhone] = [p for p in self.phone_nos if p.is_valid]
		if not valid_numbers:
			return

		# Handle primary phone
		current_primary: ContactPhone | None = next((p for p in self.phone_nos if p.is_primary_phone), None)
		if not current_primary or not current_primary.is_valid:
			# Reset all primary phone flags
			for phone in self.phone_nos:
				phone.is_primary_phone = 0
			# Set first valid number as primary
			valid_numbers[0].is_primary_phone = 1

		# Handle primary mobile
		current_mobile: ContactPhone | None = next(
			(p for p in self.phone_nos if p.is_primary_mobile_no), None
		)
		valid_mobiles: list[ContactPhone] = [p for p in valid_numbers if p.carrier_type == "mobile"]

		if current_mobile:
			if not current_mobile.is_valid or current_mobile.carrier_type != "mobile":
				# Reset mobile flags if current primary is invalid/not mobile
				for phone in self.phone_nos:
					phone.is_primary_mobile_no = 0
				# Set first valid mobile as primary if available
				if valid_mobiles:
					valid_mobiles[0].is_primary_mobile_no = 1
		elif valid_mobiles:  # No current primary mobile, but valid mobiles exist
			valid_mobiles[0].is_primary_mobile_no = 1

	def get_country_code(self) -> str:
		"""Get the ISO country code for phone number parsing."""
		country: str | None = None
		if self.address:
			country = frappe.get_value("Address", self.address, "country")
		if not country:
			country = cast(str | None, frappe.db.get_single_value("System Settings", "country"))
		country_code: str = str(frappe.get_value("Country", country, "code") or "").upper()
		return country_code

	# messaging group methods

	@frappe.whitelist()
	def add_to_group(self, group_name: str) -> None:
		"""Add this contact to a messaging group.

		Args:
			group_name: The name of the messaging group to add this contact to.
		"""
		mg = cast("MessagingGroup", frappe.get_doc("Messaging Group", group_name))
		mg.add_contact(self.name)

	@frappe.whitelist()
	def remove_from_group(self, group_name: str) -> None:
		"""Remove this contact from a messaging group.

		Args:
			group_name: The name of the messaging group to remove this contact from.
		"""
		mg = cast("MessagingGroup", frappe.get_doc("Messaging Group", group_name))
		mg.remove_contact(self.name)


# Module-level functions for bulk operations and validation


@frappe.whitelist()
def bulk_add_to_group(doc_names: str, group_name: str) -> dict[str, str]:
	"""Add multiple contacts to a messaging group.

	Args:
		doc_names: JSON-encoded list of contact names.
		group_name: The name of the messaging group.

	Returns:
		A dict with status and message keys.
	"""
	doc_names_list: list[str] = json.loads(doc_names)
	mg = cast("MessagingGroup", frappe.get_doc("Messaging Group", group_name))
	mg.add_contacts(doc_names_list)
	return {
		"status": "Success",
		"message": frappe._("Added contacts to group"),
	}


@frappe.whitelist()
def bulk_remove_from_group(doc_names: str, group_name: str) -> dict[str, str]:
	"""Remove multiple contacts from a messaging group.

	Args:
		doc_names: JSON-encoded list of contact names.
		group_name: The name of the messaging group.

	Returns:
		A dict with status and message keys.
	"""
	doc_names_list: list[str] = json.loads(doc_names)
	mg = cast("MessagingGroup", frappe.get_doc("Messaging Group", group_name))
	mg.remove_contacts(doc_names_list)
	return {
		"status": "Success",
		"message": frappe._("Removed contacts from group"),
	}


def add_to_all_contacts_group(doc: Contact, method: str | None = None) -> None:
	"""Add contact to the default all contacts group on creation.

	Args:
		doc: The Contact document being saved.
		method: The hook method name (unused, for Frappe hook compatibility).
	"""
	all_contacts_group = cast(
		str | None, frappe.db.get_single_value("Messaging Settings", "all_contacts_group")
	)
	if all_contacts_group:
		doc.add_to_group(all_contacts_group)


# Phone number utility functions


def is_valid_e164_number(number: str) -> bool:
	"""Check if a phone number is in valid E.164 format.

	Args:
		number: The phone number string to validate.

	Returns:
		True if the number is valid E.164 format, False otherwise.
	"""
	# if the number does not begin with a +, it is not E.164
	if not number.startswith("+"):
		return False
	try:
		numobj = phonenumbers.parse(number, "")
	except phonenumbers.NumberParseException:
		return False
	if phonenumbers.is_valid_number(numobj):
		return phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.E164) == number
	return False


def convert_to_e164(number: str | None, country_code: str) -> str | None:
	"""Convert a phone number to E.164 format.

	Args:
		number: The phone number to convert.
		country_code: The ISO country code for parsing (e.g., "US", "GB").

	Returns:
		The E.164 formatted number, or None if conversion fails.
	"""
	if not number:
		return None
	try:
		numobj = phonenumbers.parse(number, country_code)
	except phonenumbers.NumberParseException:
		return None
	if phonenumbers.is_valid_number(numobj):
		return phonenumbers.format_number(numobj, phonenumbers.PhoneNumberFormat.E164)
	return None


def validate_number(e164_number: str, client: Client) -> tuple[bool, str]:
	"""Validate a phone number using Twilio Lookup API.

	Args:
		e164_number: The phone number in E.164 format.
		client: An authenticated Twilio REST client.

	Returns:
		A tuple of (is_valid, carrier_type) where carrier_type is one of
		"mobile", "landline", "voip", "unknown", or empty string if invalid.
	"""
	is_valid: bool = False
	carrier_type: str = ""
	try:
		lookup = client.lookups.v2.phone_numbers(e164_number).fetch(fields=["line_type_intelligence"])

		# The line_type_intelligence is a PhoneNumberInstance property
		line_type_info = getattr(lookup, "line_type_intelligence", None)
		if line_type_info and isinstance(line_type_info, dict):
			carrier_type = str(line_type_info.get("type", ""))
			is_valid = bool(carrier_type)  # Explicitly convert to boolean
		elif line_type_info is not None:
			# If we got a response but no line type dict, consider it valid but unknown type
			is_valid = True
			carrier_type = "unknown"
		else:
			# No line type intelligence available
			is_valid = True
			carrier_type = "unknown"

	except TwilioRestException as e:
		if e.code == 20404:  # Number not found
			is_valid = False
			frappe.logger().info(f"Number not found: {e164_number}")
		else:
			is_valid = False
			frappe.log_error("Twilio Lookup Error", f"Number: {e164_number}, Error: {e!s}")
	except Exception as e:
		is_valid = False
		frappe.log_error("Phone Validation Error", f"Number: {e164_number}, Error: {e!s}")

	frappe.logger().debug(f"Validation result for {e164_number}: valid={is_valid}, type={carrier_type}")
	return is_valid, carrier_type
