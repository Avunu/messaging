# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""The `bench execute` maintenance helpers."""

import frappe
from frappe.tests.classes import IntegrationTestCase

from messaging import maintenance
from messaging.tests.utils import make_contact, unique_phone


class TestMaintenance(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")

	def tearDown(self) -> None:
		frappe.db.rollback()

	def test_clean_number_and_country_code(self) -> None:
		self.assertEqual(maintenance.clean_number("+1 (202) 555-0101"), "2025550101")
		self.assertEqual(maintenance.clean_number("ext."), "")
		self.assertIsNone(maintenance.clean_number(None))
		self.assertEqual(maintenance.prefix_usa_country_code("2025550101"), "+12025550101")
		self.assertEqual(maintenance.prefix_usa_country_code("+442071234567"), "+442071234567")

	def test_clean_phone_numbers_and_email_addresses(self) -> None:
		contact = make_contact(phone=unique_phone(), email=f"{frappe.generate_hash(length=8)}@example.com")
		phone = frappe.db.get_value("Contact Phone", {"parent": contact.name}, "name")
		email = frappe.db.get_value("Contact Email", {"parent": contact.name}, "name")
		frappe.db.set_value("Contact Phone", phone, "phone", "(202) 555-0199")
		frappe.db.set_value("Contact Email", email, "email_id", "  Mixed@Example.COM ")

		maintenance.clean_phone_numbers()
		maintenance.clean_email_addresses()

		self.assertEqual(frappe.db.get_value("Contact Phone", phone, "phone"), "2025550199")
		self.assertEqual(frappe.db.get_value("Contact Email", email, "email_id"), "mixed@example.com")

	def test_duplicates_are_merged_into_the_latest_contact(self) -> None:
		phone = unique_phone()
		email = f"{frappe.generate_hash(length=8)}@example.com"
		older = make_contact(phone=phone, designation="Owner")
		newer = make_contact(phone=phone, email=email)
		by_email = make_contact(email=email)
		frappe.db.set_value("Contact", newer.name, "modified", frappe.utils.add_days(frappe.utils.now(), 1))

		maintenance.consolidate_duplicate_contacts()

		self.assertTrue(frappe.db.exists("Contact", newer.name))
		self.assertFalse(frappe.db.exists("Contact", older.name))
		self.assertFalse(frappe.db.exists("Contact", by_email.name))

	def test_links_are_deduplicated_and_primaries_refreshed(self) -> None:
		contact = make_contact(phone=unique_phone(), email=f"{frappe.generate_hash(length=8)}@example.com")
		group = frappe.get_doc(
			{"doctype": "Messaging Group", "title": f"Dup {frappe.generate_hash(length=6)}"}
		).insert(ignore_permissions=True)
		for _ in range(2):
			frappe.get_doc(
				{
					"doctype": "Dynamic Link",
					"parenttype": "Contact",
					"parentfield": "links",
					"parent": contact.name,
					"link_doctype": "Messaging Group",
					"link_name": group.name,
				}
			).db_insert()
		frappe.db.set_value("Contact", contact.name, "email_id", "")

		maintenance.deduplicate_contact_links()
		maintenance.refresh_primary_contact_fields()

		self.assertEqual(
			frappe.db.count("Dynamic Link", {"parent": contact.name, "link_name": group.name}), 1
		)
		self.assertTrue(frappe.db.get_value("Contact", contact.name, "email_id"))
