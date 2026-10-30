# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""The Contact extension's Twilio number validation (Lookup mocked) and its group actions."""

import json
from typing import Any, cast
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.classes import IntegrationTestCase
from twilio.base.exceptions import TwilioRestException

from messaging.messaging.custom import contact as contact_module
from messaging.messaging.custom.contact import (
	Contact,
	bulk_add_to_group,
	bulk_remove_from_group,
	validate_number,
)
from messaging.tests.utils import as_user, make_contact, make_user, messaging_settings


def lookup_client(results: dict[str, Any]) -> MagicMock:
	"""A Twilio client whose Lookup answers `results[number]`: a line type, None, or an exception."""
	client = MagicMock()

	def phone_numbers(number: str) -> MagicMock:
		result = results[number]
		fetch = MagicMock()
		if isinstance(result, Exception):
			fetch.fetch.side_effect = result
		else:
			fetch.fetch.return_value = MagicMock(line_type_intelligence=result)
		return fetch

	client.lookups.v2.phone_numbers.side_effect = phone_numbers
	return client


class TestValidateNumber(IntegrationTestCase):
	def test_lookup_results(self) -> None:
		client = lookup_client(
			{
				"+12025550101": {"type": "mobile"},
				"+12025550102": {"type": ""},
				"+12025550103": "not a dict",
				"+12025550104": None,
				"+12025550105": TwilioRestException(status=404, uri="/", msg="nope", code=20404),
				"+12025550106": TwilioRestException(status=500, uri="/", msg="down", code=20500),
				"+12025550107": RuntimeError("socket"),
			}
		)
		with patch("frappe.log_error") as log_error:
			self.assertEqual(validate_number("+12025550101", client), (True, "mobile"))
			self.assertEqual(validate_number("+12025550102", client), (False, ""))
			self.assertEqual(validate_number("+12025550103", client), (True, "unknown"))
			self.assertEqual(validate_number("+12025550104", client), (True, "unknown"))
			self.assertEqual(validate_number("+12025550105", client), (False, ""))
			self.assertEqual(validate_number("+12025550106", client), (False, ""))
			self.assertEqual(validate_number("+12025550107", client), (False, ""))
		self.assertEqual(log_error.call_count, 2)


class TestContactValidation(IntegrationTestCase):
	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_saving_validates_numbers_and_picks_the_primaries(self) -> None:
		client = lookup_client(
			{
				"+12025550111": {"type": "landline"},
				"+12025550112": {"type": "mobile"},
				"+12025550113": TwilioRestException(status=404, uri="/", msg="nope", code=20404),
			}
		)
		with (
			messaging_settings(enable_number_validation=1, twilio_account_sid="AC1", twilio_auth_token="tok"),
			patch.object(contact_module, "Client", return_value=client),
		):
			contact = cast(Contact, frappe.get_doc({"doctype": "Contact", "first_name": "Val"}))
			contact.append("phone_nos", {"phone": "+12025550111", "is_primary_mobile_no": 1})
			contact.append("phone_nos", {"phone": "+12025550112"})
			contact.append("phone_nos", {"phone": "+12025550113", "is_primary_phone": 1})
			contact.insert(ignore_permissions=True)

			by_number = {p.phone: p for p in contact.phones()}
			self.assertEqual(
				(by_number["+12025550111"].is_valid, by_number["+12025550111"].carrier_type), (1, "landline")
			)
			self.assertEqual(by_number["+12025550112"].validated_number, "+12025550112")
			self.assertEqual(by_number["+12025550113"].is_valid, 0)
			# the landline is the first valid number, so it is the primary phone; the mobile is the primary mobile
			self.assertEqual(by_number["+12025550111"].is_primary_phone, 1)
			self.assertEqual(by_number["+12025550113"].is_primary_phone, 0)
			self.assertEqual(by_number["+12025550112"].is_primary_mobile_no, 1)
			self.assertEqual(by_number["+12025550111"].is_primary_mobile_no, 0)

			# a validated number is not looked up again
			client.lookups.v2.phone_numbers.reset_mock()
			contact.save(ignore_permissions=True)
			self.assertEqual(
				[c.args[0] for c in client.lookups.v2.phone_numbers.call_args_list], ["+12025550113"]
			)

	def test_no_valid_number_leaves_the_primaries_alone(self) -> None:
		contact = cast(Contact, frappe.get_doc({"doctype": "Contact", "first_name": "None"}))
		contact.append("phone_nos", {"phone": "+12025550121", "is_primary_phone": 1})
		contact.set_primary_numbers()
		self.assertEqual(contact.phones()[0].is_primary_phone, 1)

	def test_a_mobile_is_picked_when_none_is_primary(self) -> None:
		contact = cast(Contact, frappe.get_doc({"doctype": "Contact", "first_name": "Mob"}))
		contact.append("phone_nos", {"phone": "+12025550131", "is_valid": 1, "carrier_type": "mobile"})
		contact.set_primary_numbers()
		self.assertEqual(contact.phones()[0].is_primary_mobile_no, 1)

	def test_the_country_comes_from_the_address(self) -> None:
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "Office",
				"address_line1": "1 High St",
				"city": "London",
				"country": "United Kingdom",
			}
		).insert(ignore_permissions=True)
		contact = make_contact(address=address.name)
		self.assertEqual(contact.get_country_code(), "GB")


class TestGroupActions(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		self.group = frappe.get_doc(
			{"doctype": "Messaging Group", "title": f"Bulk {frappe.generate_hash(length=6)}"}
		).insert(ignore_permissions=True)
		self.contacts = [make_contact(), make_contact()]
		self.names = json.dumps([c.name for c in self.contacts])

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def members(self) -> list[str]:
		return frappe.get_all("Messaging Group Member", filters={"parent": self.group.name}, pluck="contact")

	def test_bulk_add_and_remove(self) -> None:
		self.assertEqual(bulk_add_to_group(self.names, str(self.group.name))["status"], "Success")
		self.assertEqual(sorted(self.members()), sorted(str(c.name) for c in self.contacts))
		bulk_remove_from_group(self.names, str(self.group.name))
		self.assertEqual(self.members(), [])

	def test_group_changes_need_write_on_the_group(self) -> None:
		user = make_user(roles=("Accounts User",))
		with as_user(user):
			for call in (
				lambda: bulk_add_to_group(self.names, str(self.group.name)),
				lambda: bulk_remove_from_group(self.names, str(self.group.name)),
				lambda: self.contacts[0].add_to_group(str(self.group.name)),
				lambda: self.contacts[0].remove_from_group(str(self.group.name)),
			):
				with self.assertRaises(frappe.PermissionError):
					call()

	def test_every_new_contact_joins_the_all_contacts_group(self) -> None:
		with messaging_settings(all_contacts_group=self.group.name):
			user = make_user(roles=("Sales User",))
			with as_user(user):
				contact = make_contact()
		self.assertIn(contact.name, self.members())
