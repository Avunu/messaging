# Copyright (c) 2026, Avunu LLC and contributors
# For license information, please see license.txt

"""get_linked_documents: the documents linked to a contact, as far as the user may read them."""

from typing import cast

import frappe
from frappe.tests.classes import IntegrationTestCase

from messaging.messaging.api.chat.links import get_document_title, get_linked_documents
from messaging.messaging.doctype.messaging_group.messaging_group import MessagingGroup
from messaging.tests.utils import as_user, make_contact, make_user


class TestLinkedDocuments(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		self.contact = make_contact(phone="+12025550111")
		self.group = cast(
			MessagingGroup,
			frappe.get_doc(
				{"doctype": "Messaging Group", "title": f"Linked {frappe.generate_hash(length=6)}"}
			).insert(ignore_permissions=True),
		)
		self.group.add_contact(self.contact.name)

	def tearDown(self) -> None:
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_a_contacts_groups_are_listed_by_link_group(self) -> None:
		result = get_linked_documents("Contact", str(self.contact.name))
		docs = result["Messaging"]
		self.assertEqual(
			docs, [{"doctype": "Messaging Group", "name": self.group.name, "title": self.group.title}]
		)

	def test_nothing_is_listed_for_a_missing_document(self) -> None:
		self.assertEqual(get_linked_documents("Contact", "no such contact"), {})
		self.assertEqual(get_linked_documents("", ""), {})

	def test_a_user_who_cannot_read_the_document_is_refused(self) -> None:
		with as_user(make_user()), self.assertRaises(frappe.PermissionError):
			get_linked_documents("Contact", str(self.contact.name))

	def test_a_document_title_falls_back_to_its_name(self) -> None:
		self.assertEqual(get_document_title("Messaging Group", str(self.group.name)), self.group.title)
		self.assertEqual(get_document_title("No Such DocType", "x"), "x")
