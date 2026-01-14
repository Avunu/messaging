# Copyright (c) 2026, Avunu LLC and Contributors
# See license.txt

from typing import Any, cast
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.classes import IntegrationTestCase
from frappe.utils import random_string

from messaging.messaging.custom.contact import (
	Contact,
	convert_to_e164,
	is_valid_e164_number,
)
from messaging.messaging.doctype.messaging_group.messaging_group import MessagingGroup


class TestContactPhoneUtils(IntegrationTestCase):
	"""Test cases for phone number utility functions."""

	def test_is_valid_e164_number_valid(self) -> None:
		"""Test that valid E.164 numbers are recognized."""
		valid_numbers = [
			"+12025551234",  # US number
			"+442071234567",  # UK number
			"+61291234567",  # Australian number
		]
		for number in valid_numbers:
			self.assertTrue(
				is_valid_e164_number(number),
				f"Expected {number} to be valid E.164",
			)

	def test_is_valid_e164_number_invalid(self) -> None:
		"""Test that invalid E.164 numbers are rejected."""
		invalid_numbers = [
			"2025551234",  # Missing + prefix
			"+1202555123",  # Too short
			"+1-202-555-1234",  # Has dashes
			"(202) 555-1234",  # US format without +
			"",  # Empty string
		]
		for number in invalid_numbers:
			self.assertFalse(
				is_valid_e164_number(number),
				f"Expected {number} to be invalid E.164",
			)

	def test_convert_to_e164_us_number(self) -> None:
		"""Test converting US phone numbers to E.164 format."""
		test_cases = [
			("2025551234", "US", "+12025551234"),
			("(202) 555-1234", "US", "+12025551234"),
			("202-555-1234", "US", "+12025551234"),
			("1-202-555-1234", "US", "+12025551234"),
		]
		for input_number, country, expected in test_cases:
			result = convert_to_e164(input_number, country)
			self.assertEqual(
				result,
				expected,
				f"Expected {input_number} ({country}) to convert to {expected}, got {result}",
			)

	def test_convert_to_e164_already_e164(self) -> None:
		"""Test that already E.164 formatted numbers pass through."""
		number = "+12025551234"
		result = convert_to_e164(number, "US")
		self.assertEqual(result, number)

	def test_convert_to_e164_invalid_number(self) -> None:
		"""Test that invalid numbers return None."""
		invalid_numbers = [
			("123", "US"),  # Too short
			("", "US"),  # Empty
			(None, "US"),  # None
		]
		for number, country in invalid_numbers:
			result = convert_to_e164(number, country)
			self.assertIsNone(result, f"Expected {number} to return None")


class TestContactExtension(IntegrationTestCase):
	"""Test cases for the Contact extension class."""

	_all_contacts_group_patcher: Any = None

	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		# Patch add_to_all_contacts_group to prevent side effects
		cls._all_contacts_group_patcher = patch(
			"messaging.messaging.custom.contact.add_to_all_contacts_group", MagicMock()
		)
		cls._all_contacts_group_patcher.start()
		cls.addClassCleanup(cls._all_contacts_group_patcher.stop)

	def _create_test_contact(self, **kwargs: Any) -> Contact:
		"""Helper to create a test contact."""
		defaults = {
			"doctype": "Contact",
			"first_name": f"Test{random_string(6)}",
			"last_name": "Contact",
		}
		defaults.update(kwargs)
		contact = cast(Contact, frappe.get_doc(defaults))
		contact.insert(ignore_permissions=True)
		return contact

	def _create_test_messaging_group(self, title: str | None = None) -> MessagingGroup:
		"""Helper to create a test messaging group."""
		if not title:
			title = f"Test Group {random_string(6)}"
		group = cast(
			MessagingGroup,
			frappe.get_doc({"doctype": "Messaging Group", "title": title}),
		)
		group.insert(ignore_permissions=True)
		return group

	def test_contact_uses_extended_class(self) -> None:
		"""Test that frappe.get_doc returns the extended Contact class."""
		contact = self._create_test_contact()
		# Verify the contact has the add_to_group method from our extension
		self.assertTrue(
			hasattr(contact, "add_to_group"),
			"Contact should have add_to_group method from extension",
		)
		self.assertTrue(
			callable(getattr(contact, "add_to_group", None)),
			"add_to_group should be callable",
		)

	def test_contact_add_to_group(self) -> None:
		"""Test adding a contact to a messaging group."""
		contact = self._create_test_contact()
		group = self._create_test_messaging_group()

		# Add contact to group
		contact.add_to_group(str(group.name))

		# Verify contact is in group
		group.reload()
		member_contacts = [m.contact for m in group.members]
		self.assertIn(contact.name, member_contacts)

	def test_contact_remove_from_group(self) -> None:
		"""Test removing a contact from a messaging group."""
		contact = self._create_test_contact()
		group = self._create_test_messaging_group()

		# Add then remove contact
		contact.add_to_group(str(group.name))
		contact.remove_from_group(str(group.name))

		# Verify contact is not in group
		group.reload()
		member_contacts = [m.contact for m in group.members]
		self.assertNotIn(contact.name, member_contacts)

	def test_contact_deduplicate_emails(self) -> None:
		"""Test that duplicate emails are removed during validation."""
		contact = cast(
			Contact,
			frappe.get_doc(
				{
					"doctype": "Contact",
					"first_name": f"Test{random_string(6)}",
				}
			),
		)
		# Add duplicate emails
		contact.append("email_ids", {"email_id": "test@example.com", "is_primary": 1})
		contact.append("email_ids", {"email_id": "TEST@EXAMPLE.COM", "is_primary": 0})  # Same, different case
		contact.append("email_ids", {"email_id": "other@example.com", "is_primary": 0})

		# Run deduplication
		contact.deduplicate_emails()

		# Should only have 2 unique emails
		self.assertEqual(len(contact.email_ids), 2)
		emails = [e.email_id for e in contact.email_ids]
		self.assertIn("test@example.com", emails)
		self.assertIn("other@example.com", emails)

	def test_contact_deduplicate_phone_numbers(self) -> None:
		"""Test that duplicate phone numbers are removed and normalized."""
		contact = cast(
			Contact,
			frappe.get_doc(
				{
					"doctype": "Contact",
					"first_name": f"Test{random_string(6)}",
				}
			),
		)
		# Add duplicate phone numbers in different formats
		contact.append("phone_nos", {"phone": "+12025551234", "is_primary_phone": 1})
		contact.append("phone_nos", {"phone": "(202) 555-1234", "is_primary_phone": 0})  # Same number
		contact.append("phone_nos", {"phone": "+13105551234", "is_primary_phone": 0})  # Different number

		# Run deduplication with US country code
		contact.deduplicate_phone_numbers("US")

		# Should only have 2 unique numbers, both in E.164
		self.assertEqual(len(contact.phone_nos), 2)
		phones = [p.phone for p in contact.phone_nos]
		self.assertIn("+12025551234", phones)
		self.assertIn("+13105551234", phones)

	def test_contact_on_trash_removes_from_groups(self) -> None:
		"""Test that deleting a contact removes it from all messaging groups."""
		contact = self._create_test_contact()
		group = self._create_test_messaging_group()

		# Add contact to group
		contact.add_to_group(str(group.name))

		# Verify contact is in group
		group.reload()
		self.assertEqual(len(group.members), 1)

		# Delete contact
		contact.delete()

		# Verify group membership is removed
		group.reload()
		self.assertEqual(len(group.members), 0)
