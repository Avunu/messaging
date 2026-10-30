# Copyright (c) 2023, Avunu LLC and Contributors
# See license.txt

"""Messaging Group: its members, their contacts' links to it, and its mirrored Email Group."""

from typing import Any, cast

import frappe
from frappe.tests.classes import IntegrationTestCase

from messaging.messaging.doctype.messaging_group.messaging_group import MessagingGroup
from messaging.tests.utils import make_contact


def linked(contact: str, group: str) -> bool:
	return bool(
		frappe.db.exists(
			"Dynamic Link",
			{
				"parenttype": "Contact",
				"parent": contact,
				"link_doctype": "Messaging Group",
				"link_name": group,
			},
		)
	)


class TestMessagingGroup(IntegrationTestCase):
	def setUp(self) -> None:
		frappe.set_user("Administrator")
		self.group = cast(
			MessagingGroup,
			frappe.get_doc(
				{"doctype": "Messaging Group", "title": f"Group {frappe.generate_hash(length=6)}"}
			).insert(ignore_permissions=True),
		)

	def tearDown(self) -> None:
		frappe.db.rollback()

	def test_members_get_a_link_to_the_group_and_lose_it_when_removed(self) -> None:
		a, b = make_contact(), make_contact()
		self.group.add_contacts([a.name, b.name])
		self.assertTrue(linked(str(a.name), str(self.group.name)))

		self.group.reload()
		self.group.members = [m for m in self.group.members if m.contact != a.name]
		self.group.save()
		self.assertFalse(linked(str(a.name), str(self.group.name)))
		self.assertTrue(linked(str(b.name), str(self.group.name)))

		self.group.remove_contacts([b.name])
		self.assertFalse(linked(str(b.name), str(self.group.name)))
		self.group.reload()
		self.assertEqual(self.group.members, [])

	def test_a_member_whose_contact_is_gone_is_pruned_on_save(self) -> None:
		gone = make_contact()
		kept = make_contact()
		self.group.add_contacts([gone.name, kept.name])
		frappe.db.delete("Contact", gone.name)

		self.group.reload()
		self.group.title = "Renamed"
		self.group.save()

		self.assertEqual([m.contact for m in self.group.members], [kept.name])

	def test_the_email_group_mirrors_the_members(self) -> None:
		email_group = frappe.get_doc(
			{"doctype": "Email Group", "title": f"Mirror {frappe.generate_hash(length=6)}"}
		).insert(ignore_permissions=True)
		stale = frappe.get_doc(
			{"doctype": "Email Group Member", "email_group": email_group.name, "email": "left@example.com"}
		).insert(ignore_permissions=True)
		member = make_contact(email=f"{frappe.generate_hash(length=8)}@example.com")

		self.group.email_group = email_group.name
		self.group.append("members", {"contact": member.name})
		self.group.save()

		emails = frappe.get_all(
			"Email Group Member", filters={"email_group": email_group.name}, pluck="email"
		)
		self.assertEqual(emails, [member.email_id])
		self.assertFalse(frappe.db.exists("Email Group Member", stale.name))

	def test_deleting_the_group_unlinks_its_contacts(self) -> None:
		member: Any = make_contact()
		self.group.add_contact(member.name)
		self.group.reload()
		self.group.delete()
		self.assertFalse(linked(str(member.name), str(self.group.name)))

	def test_an_empty_group_can_be_deleted(self) -> None:
		self.group.delete()
		self.assertFalse(frappe.db.exists("Messaging Group", self.group.name))
