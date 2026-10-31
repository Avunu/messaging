# Copyright (c) 2023, Avunu LLC and Contributors
# See license.txt

"""Messaging Group: its members, their contacts' links to it, and its mirrored Email Group."""

from typing import Any, cast
from unittest.mock import patch

import frappe
from frappe.tests.classes import IntegrationTestCase

from messaging.messaging.doctype.messaging_group.messaging_group import (
	MessagingGroup,
	delete_messaging_groups,
)
from messaging.tests.utils import as_user, make_contact, make_user


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
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def email_group(self, title: str | None = None) -> str:
		return str(
			frappe.get_doc(
				{"doctype": "Email Group", "title": title or f"Mailing {frappe.generate_hash(length=6)}"}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def linked_group(self) -> tuple[str, str]:
		"""A Messaging Group with a linked Email Group of another name; returns both names."""
		email_group = self.email_group()
		self.group.email_group = email_group
		self.group.save()
		return str(self.group.name), email_group

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

	def test_the_email_group_gains_the_members_and_keeps_its_own(self) -> None:
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
		self.assertEqual(sorted(emails), sorted([str(member.email_id), "left@example.com"]))
		# a subscriber the Email Group has of its own is never removed by the sync
		self.assertTrue(frappe.db.exists("Email Group Member", stale.name))

		# saving again adds nobody twice
		self.group.save()
		self.assertEqual(frappe.db.count("Email Group Member", {"email_group": email_group.name}), 2)

	def test_deleting_the_group_unlinks_its_contacts(self) -> None:
		member: Any = make_contact()
		self.group.add_contact(member.name)
		self.group.reload()
		self.group.delete()
		self.assertFalse(linked(str(member.name), str(self.group.name)))

	def test_an_empty_group_can_be_deleted(self) -> None:
		self.group.delete()
		self.assertFalse(frappe.db.exists("Messaging Group", self.group.name))

	def test_deleting_keeps_the_linked_email_group_by_default(self) -> None:
		name, email_group = self.linked_group()
		# an Email Group named like the Messaging Group is never touched either
		same_name = self.email_group(title=name)

		self.assertEqual(delete_messaging_groups(frappe.as_json([name])), [])

		self.assertFalse(frappe.db.exists("Messaging Group", name))
		self.assertTrue(frappe.db.exists("Email Group", email_group))
		self.assertTrue(frappe.db.exists("Email Group", same_name))

	def test_frappes_own_delete_keeps_the_linked_email_group(self) -> None:
		name, email_group = self.linked_group()
		frappe.delete_doc("Messaging Group", name)
		self.assertTrue(frappe.db.exists("Email Group", email_group))

	def test_asked_to_it_deletes_the_linked_email_groups_only(self) -> None:
		name, email_group = self.linked_group()
		frappe.get_doc(
			{"doctype": "Email Group Member", "email_group": email_group, "email": "a@example.com"}
		).insert(ignore_permissions=True)
		unlinked = cast(
			MessagingGroup,
			frappe.get_doc(
				{"doctype": "Messaging Group", "title": f"Plain {frappe.generate_hash(length=6)}"}
			).insert(),
		)
		same_name = self.email_group(title=str(unlinked.name))

		with patch("frappe.msgprint") as msgprint:
			deleted = delete_messaging_groups([name, str(unlinked.name)], delete_email_group=True)

		self.assertEqual(deleted, [email_group])
		msgprint.assert_called_once()
		for doctype, doc in (
			("Messaging Group", name),
			("Messaging Group", unlinked.name),
			("Email Group", email_group),
		):
			self.assertFalse(frappe.db.exists(doctype, doc), (doctype, doc))
		self.assertFalse(frappe.db.exists("Email Group Member", {"email_group": email_group}))
		self.assertTrue(frappe.db.exists("Email Group", same_name))

	def test_the_email_group_delete_needs_its_own_permission(self) -> None:
		name, email_group = self.linked_group()
		# Marketing Manager may delete a Messaging Group, but not an Email Group
		user = make_user(roles=("Marketing Manager",))
		with as_user(user):
			with self.assertRaises(frappe.PermissionError):
				delete_messaging_groups([name], delete_email_group=True)
			self.assertTrue(frappe.db.exists("Messaging Group", name))
			self.assertTrue(frappe.db.exists("Email Group", email_group))

			delete_messaging_groups([name], delete_email_group=False)
		self.assertFalse(frappe.db.exists("Messaging Group", name))
		self.assertTrue(frappe.db.exists("Email Group", email_group))

	def test_the_group_delete_needs_delete_permission(self) -> None:
		with as_user(make_user(roles=("Accounts User",))), self.assertRaises(frappe.PermissionError):
			delete_messaging_groups([str(self.group.name)])
		self.assertTrue(frappe.db.exists("Messaging Group", self.group.name))

	def test_the_delete_is_post_only(self) -> None:
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[delete_messaging_groups], ["POST"])
